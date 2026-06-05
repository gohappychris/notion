"""모든 증권사 응답을 통일하는 공통 스키마.

키움/미래에셋/신한 각 수집기는 자기 응답을 이 Holding/AccountSummary 로
정규화해서 내보낸다. 이후 계산·저장·알림 단계는 이 스키마만 다룬다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Holding:
    """개별 보유 종목 1건."""

    broker: str          # "키움" | "미래에셋" | "신한"
    market: str          # "KR" | "US"
    symbol: str          # 종목코드 (예: "005930", "NVDA")
    name: str            # 종목명
    quantity: float      # 보유수량
    avg_price: float     # 평균매입단가 (해당 통화)
    current_price: float # 현재가 (해당 통화)
    currency: str = "KRW"          # "KRW" | "USD"
    eval_amount_native: float = 0.0  # 평가금액 (원통화)
    eval_amount_krw: float = 0.0     # 평가금액 (원화환산)
    pnl_amount_native: Optional[float] = None  # 평가손익(원통화)
    pnl_rate: Optional[float] = None           # 수익률 %

    @property
    def key(self) -> str:
        """전일 대비/신규매매 감지를 위한 고유키."""
        return f"{self.broker}:{self.market}:{self.symbol}"


@dataclass
class AccountSummary:
    """한 증권사 계좌의 요약. 총자산 = 순자산 − 미수/신용 기준."""

    broker: str
    total_eval_krw: float = 0.0     # 주식 총평가금액(원화환산)
    deposit_krw: float = 0.0        # 예수금(현금)
    receivable_krw: float = 0.0     # 미수금
    credit_loan_krw: float = 0.0    # 신용융자 등 차입
    currency_cash: dict = field(default_factory=dict)  # {"USD": 1234.5} 외화현금

    @property
    def net_asset_krw(self) -> float:
        """순자산 = 주식평가 + 예수금/현금 − 미수 − 신용."""
        return (
            self.total_eval_krw
            + self.deposit_krw
            - self.receivable_krw
            - self.credit_loan_krw
        )


@dataclass
class Snapshot:
    """한 시점에 수집한 전체 결과(여러 증권사 합산)."""

    taken_at: datetime
    kind: str                       # "한국장마감" | "미국장마감" 등
    holdings: list[Holding] = field(default_factory=list)
    accounts: list[AccountSummary] = field(default_factory=list)

    @property
    def total_net_asset_krw(self) -> float:
        return sum(a.net_asset_krw for a in self.accounts)
