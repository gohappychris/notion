"""
컵&핸들 (Cup with Handle) 전략
- 윌리엄 오닐 / 미너비니 공통 매수 패턴
- 돌파 시 평균 거래량 1.5배 이상 확인
"""
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from config import config
from analysis.pattern import PatternDetector, CupHandleResult
from utils.logger import logger


@dataclass
class CupHandleSignal:
    code: str
    name: str
    action: str          # "BUY" | "WATCH" | "NONE"
    pivot: float = 0.0
    current_price: float = 0.0
    distance_to_pivot: float = 0.0  # 피봇까지 거리 비율
    cup_depth: float = 0.0
    handle_depth: float = 0.0
    volume_ratio: float = 0.0       # 현재 거래량 / 50일 평균
    message: str = ""


class CupHandleStrategy:
    """컵&핸들 패턴 기반 매수/관찰 신호 생성"""

    def analyze(self, code: str, name: str, df: pd.DataFrame) -> CupHandleSignal:
        if len(df) < 50:
            return CupHandleSignal(code, name, "NONE", message="데이터 부족")

        pattern = PatternDetector.find_cup_and_handle(
            df,
            cup_min_weeks=config.cup_min_weeks,
            cup_max_weeks=config.cup_max_weeks,
            cup_max_depth=config.cup_max_depth_ratio,
            handle_max_depth=config.handle_max_depth_ratio,
        )

        if not pattern.found:
            return CupHandleSignal(code, name, "NONE", message=pattern.message)

        last = df.iloc[-1]
        current_price = last["close"]
        vol_ma50 = df["vol_ma50"].iloc[-1] if "vol_ma50" in df.columns else df["volume"].rolling(50).mean().iloc[-1]
        volume_ratio = last["volume"] / vol_ma50 if vol_ma50 > 0 else 0

        distance = (pattern.pivot - current_price) / pattern.pivot

        # 이미 돌파했거나 너무 멀면 제외
        if distance < -0.02:
            return CupHandleSignal(
                code, name, "NONE",
                pivot=pattern.pivot,
                current_price=current_price,
                message="피봇 이미 돌파(진입 늦음)",
            )

        # 돌파 조건: 현재가 >= 피봇 * 0.99 이상이고 거래량 급증
        if distance <= 0.05 and volume_ratio >= config.breakout_volume_ratio:
            action = "BUY"
            msg = f"컵&핸들 돌파! {pattern.message} 거래량비={volume_ratio:.1f}x"
            logger.info(f"[컵&핸들 매수신호] {name}({code}) {msg}")
        elif distance <= 0.05:
            action = "WATCH"
            msg = f"컵&핸들 피봇 근접 ({distance:.1%}) - 거래량 확인 대기. {pattern.message}"
        else:
            action = "NONE"
            msg = f"컵&핸들 패턴 탐지, 피봇까지 {distance:.1%}. {pattern.message}"

        return CupHandleSignal(
            code=code,
            name=name,
            action=action,
            pivot=pattern.pivot,
            current_price=current_price,
            distance_to_pivot=distance,
            cup_depth=pattern.cup_depth,
            handle_depth=pattern.handle_depth,
            volume_ratio=volume_ratio,
            message=msg,
        )
