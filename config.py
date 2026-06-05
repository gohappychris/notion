"""환경설정 로더.

.env(로컬) 또는 환경변수(GitHub Actions Secrets)에서 설정을 읽는다.
값이 비어 있어도 import 자체는 실패하지 않게 하고, 실제로 필요할 때
require_kiwoom() 등으로 검증한다(키가 없어도 골격은 돌려볼 수 있도록).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()  # 로컬 .env 가 있으면 로드. 없으면 무시.
except ImportError:  # python-dotenv 미설치 환경(예: 최소 CI)에서도 동작
    pass


# 키움 운영/모의 서버 base URL
KIWOOM_BASE_URLS = {
    "real": "https://api.kiwoom.com",
    "mock": "https://mockapi.kiwoom.com",
}


@dataclass(frozen=True)
class KiwoomConfig:
    app_key: str
    secret_key: str
    env: str  # "real" | "mock"

    @property
    def base_url(self) -> str:
        return KIWOOM_BASE_URLS[self.env]


def load_kiwoom_config() -> KiwoomConfig:
    env = (os.getenv("KIWOOM_ENV") or "mock").strip().lower()
    if env not in KIWOOM_BASE_URLS:
        raise ValueError(f"KIWOOM_ENV 는 'real' 또는 'mock' 이어야 합니다 (현재: {env!r})")
    return KiwoomConfig(
        app_key=os.getenv("KIWOOM_APP_KEY", "").strip(),
        secret_key=os.getenv("KIWOOM_SECRET_KEY", "").strip(),
        env=env,
    )


def require_kiwoom(cfg: KiwoomConfig) -> None:
    """키움 키가 채워졌는지 검증. 없으면 친절한 에러."""
    missing = [
        name
        for name, val in (("KIWOOM_APP_KEY", cfg.app_key), ("KIWOOM_SECRET_KEY", cfg.secret_key))
        if not val
    ]
    if missing:
        raise RuntimeError(
            "키움 API 키가 설정되지 않았습니다: "
            + ", ".join(missing)
            + "\n.env 파일(또는 GitHub Secrets)에 값을 채워주세요. (.env.example 참고)"
        )


# --- 알림/저장소 설정 (Phase 1 에서 사용) ---------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_SNAPSHOTS_DB_ID = os.getenv("NOTION_SNAPSHOTS_DB_ID", "").strip()
NOTION_SUMMARY_DB_ID = os.getenv("NOTION_SUMMARY_DB_ID", "").strip()
