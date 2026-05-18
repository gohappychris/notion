import asyncio
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameNotOccupiedError
from telethon.tl.types import MessageService, MessageMediaPhoto, MessageMediaDocument

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")

BOT_SPAM_PATTERNS = [
    re.compile(r"^[\U0001F300-\U0001FFFF\s]+$"),  # emoji-only
    re.compile(r"(t\.me/|https?://\S+)\s*$"),       # bare link-only
    re.compile(r"^[가-힣]{1,5}$"),                   # single short Korean word
]


def _is_spam(text: str) -> bool:
    if len(text.strip()) < 10:
        return True
    for pat in BOT_SPAM_PATTERNS:
        if pat.match(text.strip()):
            return True
    return False


def _build_window(date: datetime, start_hour: int, end_hour: int) -> tuple[datetime, datetime]:
    """Return (window_start, window_end) as UTC datetimes for the given KST date."""
    # window_start = previous day at start_hour KST
    window_start_kst = datetime(date.year, date.month, date.day, end_hour, 0, 0, tzinfo=KST)
    # The "overnight" window: yesterday start_hour → today end_hour
    # e.g. 2025-05-18 08:00 KST target date → window is 2025-05-17 22:00 ~ 2025-05-18 08:00 KST
    prev_day = date - timedelta(days=1)
    window_start_kst = datetime(prev_day.year, prev_day.month, prev_day.day, start_hour, 0, 0, tzinfo=KST)
    window_end_kst = datetime(date.year, date.month, date.day, end_hour, 0, 0, tzinfo=KST)
    return window_start_kst.astimezone(UTC), window_end_kst.astimezone(UTC)


async def fetch_messages(
    client: TelegramClient,
    channels: list[dict],
    date: datetime,
    start_hour: int,
    end_hour: int,
) -> list[dict]:
    """Fetch and filter messages from all channels within the overnight window."""
    window_start, window_end = _build_window(date, start_hour, end_hour)
    all_messages: list[dict] = []

    for channel in channels:
        username = channel["username"]
        channel_name = channel["name"]
        priority = channel.get("priority", "medium")

        try:
            messages = await _fetch_channel(
                client, username, channel_name, priority, window_start, window_end
            )
            all_messages.extend(messages)
        except FloodWaitError as e:
            print(f"[경고] {channel_name}: Telegram 요청 제한. {e.seconds}초 대기 후 재시도...")
            await asyncio.sleep(e.seconds)
            try:
                messages = await _fetch_channel(
                    client, username, channel_name, priority, window_start, window_end
                )
                all_messages.extend(messages)
            except Exception as retry_err:
                print(f"[오류] {channel_name} 재시도 실패: {retry_err}")
        except ChannelPrivateError:
            print(f"[오류] {channel_name} ({username}): 비공개 채널이거나 접근 권한이 없음.")
        except UsernameNotOccupiedError:
            print(f"[오류] {channel_name} ({username}): 존재하지 않는 채널 이름.")
        except Exception as e:
            print(f"[오류] {channel_name} ({username}): {e}")

    all_messages.sort(key=lambda m: m["timestamp"])
    return all_messages


async def _fetch_channel(
    client: TelegramClient,
    username: str,
    channel_name: str,
    priority: str,
    window_start: datetime,
    window_end: datetime,
) -> list[dict]:
    results = []
    async for msg in client.iter_messages(username, offset_date=window_end, reverse=False):
        if isinstance(msg, MessageService):
            continue

        msg_time = msg.date.replace(tzinfo=UTC) if msg.date.tzinfo is None else msg.date

        if msg_time > window_end:
            continue
        if msg_time < window_start:
            break

        text = msg.text or ""

        # Skip media without caption
        if not text and (
            isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument))
        ):
            continue

        if not text:
            continue

        if _is_spam(text):
            continue

        results.append({
            "channel_name": channel_name,
            "username": username,
            "priority": priority,
            "timestamp": msg_time.astimezone(KST).isoformat(),
            "text": text.strip(),
            "views": getattr(msg, "views", 0) or 0,
        })

    return results
