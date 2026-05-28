"""
신고가 돌파 (New High Breakout) 전략
- 52주 신고가 또는 역사적 신고가 돌파 시 매수
- 거래량 동반 필수
"""
import pandas as pd
from dataclasses import dataclass
from config import config
from utils.logger import logger


@dataclass
class NewHighSignal:
    code: str
    name: str
    action: str           # "BUY" | "WATCH" | "NONE"
    current_price: float = 0.0
    high_52w: float = 0.0
    distance_to_high: float = 0.0
    volume_ratio: float = 0.0
    is_all_time_high: bool = False
    message: str = ""


class NewHighStrategy:
    """52주/역사적 신고가 돌파 전략"""

    def analyze(self, code: str, name: str, df: pd.DataFrame) -> NewHighSignal:
        if len(df) < 60:
            return NewHighSignal(code, name, "NONE", message="데이터 부족")

        last = df.iloc[-1]
        current = last["close"]
        current_high = last["high"]

        # 52주 신고가 (252 거래일)
        lookback = min(config.new_high_lookback_days, len(df) - 1)
        high_52w = df["high"].iloc[-lookback:-1].max()  # 당일 제외한 최고점

        # 역사적 신고가 여부
        all_time_high = df["high"].iloc[:-1].max()
        is_ath = current_high >= all_time_high * 0.99

        # 거래량 비율
        vol_ma50 = df["volume"].rolling(50).mean().iloc[-1]
        volume_ratio = last["volume"] / vol_ma50 if vol_ma50 > 0 else 0

        distance = (current - high_52w) / high_52w

        # 신고가 돌파 + 거래량 동반
        if current_high >= high_52w * (1 - config.new_high_buffer_ratio):
            if volume_ratio >= config.breakout_volume_ratio:
                action = "BUY"
                msg = (
                    f"{'역사적 신고가' if is_ath else '52주 신고가'} 돌파! "
                    f"현재={current:,.0f} 52주고={high_52w:,.0f} "
                    f"거래량={volume_ratio:.1f}x"
                )
                logger.info(f"[신고가 매수신호] {name}({code}) {msg}")
            else:
                action = "WATCH"
                msg = f"신고가 근접 ({distance:+.1%}), 거래량 부족 ({volume_ratio:.1f}x)"
        else:
            action = "NONE"
            msg = f"신고가까지 {abs(distance):.1%} 남음"

        return NewHighSignal(
            code=code,
            name=name,
            action=action,
            current_price=current,
            high_52w=high_52w,
            distance_to_high=distance,
            volume_ratio=volume_ratio,
            is_all_time_high=is_ath,
            message=msg,
        )
