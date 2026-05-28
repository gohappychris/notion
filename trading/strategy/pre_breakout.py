"""
Pre-breakout / VCP (Volatility Contraction Pattern) 전략
- 미너비니의 핵심 전략
- 변동성 수축 후 피봇 근처에서 진입
"""
import pandas as pd
from dataclasses import dataclass
from config import config
from analysis.pattern import PatternDetector
from utils.logger import logger


@dataclass
class PreBreakoutSignal:
    code: str
    name: str
    action: str           # "BUY" | "WATCH" | "NONE"
    pivot: float = 0.0
    current_price: float = 0.0
    distance_to_pivot: float = 0.0
    contractions: int = 0
    tightness: float = 0.0
    volume_ratio: float = 0.0
    message: str = ""


class PreBreakoutStrategy:
    """VCP 기반 Pre-breakout 진입 전략"""

    def analyze(self, code: str, name: str, df: pd.DataFrame) -> PreBreakoutSignal:
        if len(df) < 60:
            return PreBreakoutSignal(code, name, "NONE", message="데이터 부족")

        vcp = PatternDetector.find_vcp(df)
        if not vcp.found:
            return PreBreakoutSignal(
                code, name, "NONE",
                contractions=vcp.contractions,
                tightness=vcp.tightness,
                message=vcp.message,
            )

        last = df.iloc[-1]
        current = last["close"]
        vol_ma50 = df["volume"].rolling(50).mean().iloc[-1]
        volume_ratio = last["volume"] / vol_ma50 if vol_ma50 > 0 else 0

        distance = (vcp.pivot - current) / vcp.pivot

        # 피봇의 5% 이내 + 거래량 감소(수축 중) 또는 급증(돌파)
        if distance < 0:
            # 이미 피봇 위: 돌파 확인
            if abs(distance) <= 0.03 and volume_ratio >= config.breakout_volume_ratio:
                action = "BUY"
                msg = f"VCP 돌파! {vcp.message} 거래량={volume_ratio:.1f}x"
                logger.info(f"[VCP 매수신호] {name}({code}) {msg}")
            else:
                action = "NONE"
                msg = f"피봇 돌파했으나 거래량 부족 ({volume_ratio:.1f}x)"

        elif distance <= config.vcp_max_distance_ratio:
            # 피봇 5% 이내: 관찰 또는 매수 준비
            if volume_ratio < 0.8:
                # 거래량 줄어드는 타이트 구간 - 이상적인 진입 대기 상태
                action = "WATCH"
                msg = f"VCP 피봇 근접 ({distance:.1%}) - 거래량 수축 중 ({volume_ratio:.1f}x) {vcp.message}"
            else:
                action = "WATCH"
                msg = f"VCP 피봇 근접 ({distance:.1%}) {vcp.message}"
        else:
            action = "NONE"
            msg = f"VCP 패턴 있음, 피봇까지 {distance:.1%} {vcp.message}"

        return PreBreakoutSignal(
            code=code,
            name=name,
            action=action,
            pivot=vcp.pivot,
            current_price=current,
            distance_to_pivot=distance,
            contractions=vcp.contractions,
            tightness=vcp.tightness,
            volume_ratio=volume_ratio,
            message=msg,
        )
