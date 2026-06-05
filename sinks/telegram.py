"""텔레그램 알림 (Phase 1).

핵심 요약 + 큰 변동(±임계치) 강조 메시지를 발송.

구현 예정:
  - send_message(text): Bot API sendMessage 호출
  - format_summary(snapshot, diff): 총자산/전일대비 + 강조 종목 메시지 구성
config.TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 사용.
"""
from __future__ import annotations

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str) -> None:
    """텔레그램으로 메시지 발송(Phase 1 에서 포맷터와 연결)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 설정되지 않았습니다.")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()
