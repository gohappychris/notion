#!/usr/bin/env python3
"""Korean stock Telegram briefing CLI."""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from fetcher import fetch_messages
from summarizer import summarize
from formatter import print_briefing, briefing_to_text

KST = ZoneInfo("Asia/Seoul")
SESSION_FILE = ".telegram_session"


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="한국 주식 텔레그램 채널 새벽 브리핑 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py                          # 오늘 날짜로 터미널 출력
  python main.py --date 2025-05-18        # 특정 날짜 브리핑
  python main.py --output file            # 파일로 저장
  python main.py --channels @ch1 @ch2    # 채널 직접 지정
        """,
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="브리핑 기준 날짜 (YYYY-MM-DD, 기본값: 오늘)",
    )
    parser.add_argument(
        "--channels",
        nargs="+",
        default=None,
        metavar="@username",
        help="분석할 채널 목록 (config.yaml 대신 사용)",
    )
    parser.add_argument(
        "--output",
        choices=["terminal", "file"],
        default="terminal",
        help="출력 방식 (기본값: terminal)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="설정 파일 경로 (기본값: config.yaml)",
    )
    return parser.parse_args()


def resolve_date(date_str: str | None) -> datetime:
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
        except ValueError:
            print(f"[오류] 날짜 형식이 잘못되었습니다: {date_str} (올바른 형식: YYYY-MM-DD)")
            sys.exit(1)
    return datetime.now(tz=KST)


def resolve_channels(args_channels: list[str] | None, config: dict) -> list[dict]:
    if args_channels:
        return [
            {"name": u, "username": u, "priority": "medium"}
            for u in args_channels
        ]
    channels = config.get("channels", [])
    if not channels:
        print("[오류] config.yaml에 채널이 설정되어 있지 않습니다.")
        sys.exit(1)
    return channels


async def run(args: argparse.Namespace) -> None:
    load_dotenv()

    api_id_str = os.getenv("TELEGRAM_API_ID", "")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    phone = os.getenv("TELEGRAM_PHONE", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    missing = []
    if not api_id_str:
        missing.append("TELEGRAM_API_ID")
    if not api_hash:
        missing.append("TELEGRAM_API_HASH")
    if not phone:
        missing.append("TELEGRAM_PHONE")
    if not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"[오류] .env 파일에 다음 값이 설정되어 있지 않습니다: {', '.join(missing)}")
        print("  .env.example 파일을 참고하여 .env를 작성해주세요.")
        sys.exit(1)

    try:
        api_id = int(api_id_str)
    except ValueError:
        print("[오류] TELEGRAM_API_ID는 숫자여야 합니다.")
        sys.exit(1)

    config = load_config(args.config)
    target_date = resolve_date(args.date)
    channels = resolve_channels(args.channels, config)

    time_cfg = config.get("time_window", {})
    start_hour = time_cfg.get("start_hour", 22)
    end_hour = time_cfg.get("end_hour", 8)

    output_cfg = config.get("output", {})
    max_tokens = output_cfg.get("max_tokens_per_summary", 2000)

    date_str = target_date.strftime("%Y-%m-%d")
    print(f"[정보] {date_str} 브리핑 생성 시작 (전날 {start_hour}:00 ~ 당일 {end_hour}:00 KST)")

    client = TelegramClient(SESSION_FILE, api_id, api_hash)

    async with client:
        if not await client.is_user_authorized():
            print(f"[인증] {phone} 번호로 인증 코드를 전송합니다...")
            await client.send_code_request(phone)
            code = input("[인증] Telegram에서 받은 인증 코드를 입력하세요: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("[인증] 2단계 인증 비밀번호를 입력하세요: ").strip()
                await client.sign_in(password=password)
            print("[인증] 로그인 성공. 세션이 저장되었습니다.")

        print(f"[정보] {len(channels)}개 채널에서 메시지 수집 중...")
        messages = await fetch_messages(client, channels, target_date, start_hour, end_hour)

    if not messages:
        print(f"[경고] 수집된 메시지가 없습니다. 채널 설정 및 시간 범위를 확인하세요.")

    channel_count = len({m["channel_name"] for m in messages})
    message_count = len(messages)
    print(f"[정보] 총 {message_count}개 메시지 수집 완료. Claude API로 요약 중...")

    briefing_text = summarize(messages, date_str, anthropic_key, max_tokens)

    if args.output == "file":
        filename = f"briefing_{target_date.strftime('%Y%m%d')}.txt"
        plain = briefing_to_text(briefing_text, date_str, channel_count, message_count)
        Path(filename).write_text(plain, encoding="utf-8")
        print(f"[완료] 브리핑이 {filename}에 저장되었습니다.")
    else:
        print_briefing(briefing_text, date_str, channel_count, message_count)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 종료되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"[오류] 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
