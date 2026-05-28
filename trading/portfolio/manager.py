"""
포트폴리오 관리자
- 포지션 추적, 매수/매도 실행, 손절/익절 관리
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from config import config
from utils.logger import logger
from .risk import RiskManager, OrderPlan

if TYPE_CHECKING:
    from kiwoom.api import KiwoomAPI


@dataclass
class Position:
    code: str
    name: str
    qty: int
    entry_price: float
    stop_loss: float
    pivot: float
    highest_price: float = 0.0
    strategy: str = ""

    @property
    def current_stop(self) -> float:
        """트레일링 스탑 적용 현재 손절가"""
        trailing = RiskManager(0).calc_trailing_stop(self.highest_price, self.highest_price)
        return max(self.stop_loss, trailing)


class PortfolioManager:

    def __init__(self, api: "KiwoomAPI", account_no: str, total_capital: float):
        self.api = api
        self.account_no = account_no
        self.risk_manager = RiskManager(total_capital)
        self.positions: Dict[str, Position] = {}  # code -> Position

    # ------------------------------------------------------------------ #
    # 매수
    # ------------------------------------------------------------------ #

    def buy(self, plan: OrderPlan, strategy: str = "") -> bool:
        """
        매수 실행
        - 포지션 수 / 자금 제한 확인 후 시장가 매수
        """
        if len(self.positions) >= config.max_positions:
            logger.info(f"최대 포지션 수 도달 ({config.max_positions}) - {plan.name} 매수 보류")
            return False

        if self.risk_manager.is_daily_limit_hit():
            return False

        if plan.code in self.positions:
            logger.info(f"{plan.name}({plan.code}) 이미 보유 중 - 중복 매수 방지")
            return False

        logger.info(
            f"[매수 주문] {plan.name}({plan.code}) "
            f"{plan.qty}주 @ {plan.entry_price:,.0f}원 "
            f"손절={plan.stop_loss:,.0f}원 "
            f"전략={strategy}"
        )

        ret = self.api.buy(self.account_no, plan.code, plan.qty)
        if ret != 0:
            logger.error(f"매수 주문 실패: {plan.code} (오류={ret})")
            return False

        self.positions[plan.code] = Position(
            code=plan.code,
            name=plan.name,
            qty=plan.qty,
            entry_price=plan.entry_price,
            stop_loss=plan.stop_loss,
            pivot=plan.pivot,
            highest_price=plan.entry_price,
            strategy=strategy,
        )
        return True

    # ------------------------------------------------------------------ #
    # 매도
    # ------------------------------------------------------------------ #

    def sell(self, code: str, reason: str = "") -> bool:
        pos = self.positions.get(code)
        if not pos:
            logger.warning(f"{code} 보유 포지션 없음")
            return False

        logger.info(
            f"[매도 주문] {pos.name}({code}) "
            f"{pos.qty}주 사유={reason}"
        )

        ret = self.api.sell(self.account_no, code, pos.qty)
        if ret != 0:
            logger.error(f"매도 주문 실패: {code} (오류={ret})")
            return False

        del self.positions[code]
        return True

    # ------------------------------------------------------------------ #
    # 실시간 가격 업데이트 및 손절/익절 체크
    # ------------------------------------------------------------------ #

    def on_price_update(self, price_data: dict):
        """실시간 가격 수신 시 호출 (KiwoomAPI 실시간 콜백)"""
        code = price_data["code"]
        current_price = price_data["price"]

        pos = self.positions.get(code)
        if not pos:
            return

        # 최고가 갱신
        if current_price > pos.highest_price:
            pos.highest_price = current_price

        # 트레일링 스탑 계산
        trailing_stop = self.risk_manager.calc_trailing_stop(current_price, pos.highest_price)
        effective_stop = max(pos.stop_loss, trailing_stop)

        # 손절
        if current_price <= effective_stop:
            loss = (current_price - pos.entry_price) * pos.qty
            self.risk_manager.register_loss(loss)
            self.sell(code, reason=f"손절 (현재={current_price:,} 손절선={effective_stop:,})")

    # ------------------------------------------------------------------ #
    # 포지션 현황
    # ------------------------------------------------------------------ #

    def print_status(self):
        if not self.positions:
            logger.info("보유 포지션 없음")
            return
        logger.info("=== 현재 포지션 ===")
        for pos in self.positions.values():
            logger.info(
                f"  {pos.name}({pos.code}) "
                f"{pos.qty}주 진입={pos.entry_price:,} "
                f"손절={pos.stop_loss:,} 전략={pos.strategy}"
            )

    def get_position_codes(self) -> List[str]:
        return list(self.positions.keys())
