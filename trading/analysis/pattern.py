"""
차트 패턴 감지 모듈
- 컵&핸들, VCP(변동성 수축), 플랫 베이스 등
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Tuple
from utils.logger import logger


@dataclass
class CupHandleResult:
    found: bool
    pivot: float = 0.0           # 돌파 기준가
    cup_high: float = 0.0        # 컵 최고점
    cup_low: float = 0.0         # 컵 최저점
    cup_depth: float = 0.0       # 컵 깊이 비율
    handle_high: float = 0.0     # 핸들 최고점
    handle_low: float = 0.0      # 핸들 최저점
    handle_depth: float = 0.0    # 핸들 깊이 비율
    cup_start_idx: int = 0
    handle_end_idx: int = 0
    message: str = ""


@dataclass
class VCPResult:
    found: bool
    pivot: float = 0.0
    contractions: int = 0   # 변동성 수축 횟수
    tightness: float = 0.0  # 최근 변동 범위 (낮을수록 타이트)
    message: str = ""


class PatternDetector:

    # ------------------------------------------------------------------ #
    # 컵&핸들 패턴
    # ------------------------------------------------------------------ #

    @staticmethod
    def find_cup_and_handle(
        df: pd.DataFrame,
        cup_min_weeks: int = 7,
        cup_max_weeks: int = 65,
        cup_max_depth: float = 0.33,
        handle_max_depth: float = 0.12,
    ) -> CupHandleResult:
        """
        컵&핸들 패턴 감지
        - 최근 데이터 기준으로 역방향 탐색
        - 핸들은 컵 최고점의 상위 50% 안에서 형성
        """
        if len(df) < cup_min_weeks * 5:
            return CupHandleResult(False, message="데이터 부족")

        close = df["close"].values
        high = df["high"].values
        n = len(close)

        cup_min_bars = cup_min_weeks * 5
        cup_max_bars = cup_max_weeks * 5

        # 핸들 탐색: 최근 1~6주
        for handle_len in range(5, 31):
            if n - handle_len < cup_min_bars:
                break

            handle_start = n - handle_len
            handle_end = n - 1
            handle_high = high[handle_start:handle_end + 1].max()
            handle_low = close[handle_start:handle_end + 1].min()
            handle_depth = (handle_high - handle_low) / handle_high

            if handle_depth > handle_max_depth:
                continue

            # 컵 탐색: 핸들 이전
            for cup_len in range(cup_min_bars, min(cup_max_bars + 1, handle_start)):
                cup_start = handle_start - cup_len
                cup_data_close = close[cup_start:handle_start]
                cup_data_high = high[cup_start:handle_start]

                cup_left_high = cup_data_high[:5].max()   # 컵 왼쪽 최고점
                cup_right_high = cup_data_high[-5:].max()  # 컵 오른쪽 최고점
                cup_high = max(cup_left_high, cup_right_high)
                cup_low = cup_data_close.min()
                cup_depth = (cup_high - cup_low) / cup_high

                if cup_depth > cup_max_depth:
                    continue
                if cup_depth < 0.12:  # 너무 얕은 컵 제외
                    continue

                # 핸들이 컵 상위 50% 안에 있어야 함
                midpoint = cup_low + (cup_high - cup_low) * 0.5
                if handle_low < midpoint:
                    continue

                # 컵 오른쪽 고점과 왼쪽 고점이 유사해야 함 (±10%)
                if abs(cup_right_high - cup_left_high) / cup_left_high > 0.10:
                    continue

                pivot = handle_high

                return CupHandleResult(
                    found=True,
                    pivot=pivot,
                    cup_high=cup_high,
                    cup_low=cup_low,
                    cup_depth=cup_depth,
                    handle_high=handle_high,
                    handle_low=handle_low,
                    handle_depth=handle_depth,
                    cup_start_idx=cup_start,
                    handle_end_idx=handle_end,
                    message=f"컵깊이={cup_depth:.1%} 핸들깊이={handle_depth:.1%} 피봇={pivot:,.0f}",
                )

        return CupHandleResult(False, message="컵&핸들 패턴 없음")

    # ------------------------------------------------------------------ #
    # VCP (변동성 수축 패턴) / Pre-breakout
    # ------------------------------------------------------------------ #

    @staticmethod
    def find_vcp(df: pd.DataFrame, lookback_weeks: int = 26) -> VCPResult:
        """
        Volatility Contraction Pattern (VCP) 감지
        - 미너비니 대표 전략
        - 가격 변동폭이 점점 줄어드는 패턴
        """
        lookback = min(lookback_weeks * 5, len(df) - 1)
        if lookback < 20:
            return VCPResult(False, message="데이터 부족")

        sub = df.iloc[-lookback:].copy()
        base_high = sub["high"].max()
        base_low = sub["low"].min()

        # 베이스 전체 깊이
        base_depth = (base_high - base_low) / base_high
        if base_depth > 0.5:
            return VCPResult(False, message=f"베이스 너무 깊음 ({base_depth:.1%})")

        # 변동성 수축 횟수 측정 (각 구간의 고저 범위가 점점 좁아지는지)
        segment_size = max(10, lookback // 4)
        segments = []
        for i in range(0, lookback, segment_size):
            seg = sub.iloc[i:i + segment_size]
            if len(seg) < 5:
                break
            seg_range = (seg["high"].max() - seg["low"].min()) / seg["close"].mean()
            segments.append(seg_range)

        if len(segments) < 2:
            return VCPResult(False, message="구간 부족")

        # 수축 횟수 (이전 구간보다 좁아진 횟수)
        contractions = sum(
            1 for i in range(1, len(segments)) if segments[i] < segments[i - 1]
        )

        # 최근 10일 타이트함
        recent = df.iloc[-10:]
        tightness = (recent["high"].max() - recent["low"].min()) / recent["close"].mean()

        # VCP 조건: 최소 2회 수축 + 최근 타이트함 < 10%
        pivot = base_high  # 베이스 최고점이 돌파 기준
        recent_high = df.iloc[-5:]["high"].max()

        if contractions >= 2 and tightness < 0.10:
            return VCPResult(
                found=True,
                pivot=pivot,
                contractions=contractions,
                tightness=tightness,
                message=f"수축횟수={contractions} 타이트함={tightness:.1%} 피봇={pivot:,.0f}",
            )

        return VCPResult(False, contractions=contractions, tightness=tightness, message="VCP 조건 미충족")

    # ------------------------------------------------------------------ #
    # 플랫 베이스
    # ------------------------------------------------------------------ #

    @staticmethod
    def find_flat_base(df: pd.DataFrame) -> Tuple[bool, float, str]:
        """
        플랫 베이스 패턴 (최소 5주, 깊이 15% 이내)
        returns: (found, pivot, message)
        """
        if len(df) < 25:
            return False, 0.0, "데이터 부족"

        sub = df.iloc[-35:] if len(df) >= 35 else df
        base_high = sub["high"].max()
        base_low = sub["low"].min()
        depth = (base_high - base_low) / base_high

        if depth <= 0.15:
            return True, base_high, f"플랫베이스 깊이={depth:.1%} 피봇={base_high:,.0f}"
        return False, 0.0, f"플랫베이스 아님 (깊이={depth:.1%})"
