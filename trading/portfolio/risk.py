"""
리스크 관리 모듈
- 포지션 사이징 (Position Sizing)
- 손절가 계산
- 일일 손실 한도
"""
import pandas as pd
from dataclasses import dataclass
from config import config
from utils.logger import logger


@dataclass
class OrderPlan:
    code: str
    name: str
    entry_price: float
    stop_loss: float
    qty: int
    invest_amount: float
    risk_amount: float          # 손절 시 예상 손실액
    risk_ratio: float           # 손실액 / 총 자본 비율
    pivot: float = 0.0


class RiskManager:

    def __init__(self, total_capital: float):
        self.total_capital = total_capital
        self.daily_loss = 0.0
        self.daily_loss_limit = total_capital * config.max_daily_loss_ratio

    # ------------------------------------------------------------------ #
    # 포지션 사이징
    # ------------------------------------------------------------------ #

    def calc_position_size(
        self,
        code: str,
        name: str,
        entry_price: float,
        pivot: float,
        stop_loss_price: Optional[float] = None,
    ) -> Optional[OrderPlan]:
        """
        미너비니식 리스크 기반 포지션 사이징
        - 1회 거래 최대 손실 = 총자본의 1~2%
        - 포지션 크기 = 종목당 최대 비중 이내
        """
        if stop_loss_price is None:
            stop_loss_price = entry_price * (1 - config.stop_loss_ratio)

        risk_per_share = entry_price - stop_loss_price
        if risk_per_share <= 0:
            logger.warning(f"{code} 손절가 계산 오류")
            return None

        # 총 자본의 1.5%를 리스크로 설정
        max_risk_amount = self.total_capital * 0.015
        qty_by_risk = int(max_risk_amount / risk_per_share)

        # 종목당 최대 비중 제한
        max_invest = self.total_capital * config.max_position_ratio
        qty_by_capital = int(max_invest / entry_price)

        qty = min(qty_by_risk, qty_by_capital)
        if qty <= 0:
            logger.warning(f"{name}({code}) 최소 수량 0 - 포지션 제외")
            return None

        invest_amount = qty * entry_price
        risk_amount = qty * risk_per_share

        return OrderPlan(
            code=code,
            name=name,
            entry_price=entry_price,
            stop_loss=stop_loss_price,
            qty=qty,
            invest_amount=invest_amount,
            risk_amount=risk_amount,
            risk_ratio=risk_amount / self.total_capital,
            pivot=pivot,
        )

    # ------------------------------------------------------------------ #
    # 손절가 계산
    # ------------------------------------------------------------------ #

    def calc_stop_loss(self, entry_price: float, df: pd.DataFrame) -> float:
        """
        ATR 기반 손절가 (시장 노이즈 반영)
        최소 손절 = 진입가 - 7% (미너비니 규칙)
        """
        atr = df["atr"].iloc[-1] if "atr" in df.columns else entry_price * 0.02
        atr_stop = entry_price - (2.5 * atr)  # ATR 2.5배 아래
        fixed_stop = entry_price * (1 - config.stop_loss_ratio)
        return max(atr_stop, fixed_stop)

    # ------------------------------------------------------------------ #
    # 트레일링 스탑
    # ------------------------------------------------------------------ #

    def calc_trailing_stop(self, current_price: float, highest_price: float) -> float:
        """트레일링 스탑: 최고점 대비 N% 하락 시 손절"""
        return highest_price * (1 - config.trailing_stop_ratio)

    # ------------------------------------------------------------------ #
    # 일일 손실 한도
    # ------------------------------------------------------------------ #

    def register_loss(self, amount: float):
        """실현 손실 기록"""
        if amount < 0:
            self.daily_loss += abs(amount)

    def is_daily_limit_hit(self) -> bool:
        """일일 손실 한도 초과 여부"""
        if self.daily_loss >= self.daily_loss_limit:
            logger.warning(
                f"일일 최대 손실 도달: {self.daily_loss:,.0f}원 "
                f"(한도: {self.daily_loss_limit:,.0f}원) - 신규 매수 중단"
            )
            return True
        return False

    def reset_daily_stats(self):
        self.daily_loss = 0.0


# Optional import for calc_position_size return type hint
from typing import Optional
