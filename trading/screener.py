"""
종목 스크리너
- 전체 시장 종목에 미너비니 추세 템플릿 적용
- 통과 종목에 컵&핸들, VCP, 신고가 전략 적용
"""
from __future__ import annotations
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, TYPE_CHECKING

import pandas as pd

from config import config
from analysis.indicators import TechnicalIndicators
from strategy import MinerviniScreener, CupHandleStrategy, NewHighStrategy, PreBreakoutStrategy
from portfolio.risk import RiskManager
from utils.logger import logger

if TYPE_CHECKING:
    from kiwoom.api import KiwoomAPI


class Screener:

    def __init__(self, api: "KiwoomAPI"):
        self.api = api
        self.screener = MinerviniScreener()
        self.cup_handle = CupHandleStrategy()
        self.new_high = NewHighStrategy()
        self.pre_breakout = PreBreakoutStrategy()

    def run(self) -> List[Dict]:
        """
        전체 스크리닝 파이프라인 실행
        returns: 매수 신호 리스트 (우선순위 정렬)
        """
        logger.info("=== 스크리닝 시작 ===")

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=600)).strftime("%Y%m%d")

        # 1단계: 전 종목 코드 수집
        all_codes = []
        for market in config.target_markets:
            codes = self.api.get_market_codes(market)
            all_codes.extend(codes)
        logger.info(f"전체 종목 수: {len(all_codes)}")

        # 2단계: 추세 템플릿 스크리닝 (1차 필터)
        trend_candidates = []
        for i, code in enumerate(all_codes):
            try:
                rows = self.api.get_daily_ohlcv(code, start_date, end_date)
                if len(rows) < 210:
                    continue

                df = TechnicalIndicators.prepare_dataframe(rows)

                # 가격/거래량 기본 필터
                last = df.iloc[-1]
                if not (config.min_price <= last["close"] <= config.max_price):
                    continue
                if df["volume"].tail(20).mean() < config.min_volume:
                    continue

                name = self.api.get_stock_name(code)
                result = self.screener.screen(code, name, df)

                if result.score >= 6:
                    trend_candidates.append((code, name, df, result.score))

                if (i + 1) % 100 == 0:
                    logger.info(f"  진행: {i + 1}/{len(all_codes)} 통과: {len(trend_candidates)}")

                time.sleep(0.1)  # API 제한

            except Exception as e:
                logger.debug(f"종목 {code} 처리 오류: {e}")

        logger.info(f"추세 템플릿 통과: {len(trend_candidates)}종목")

        # 3단계: 패턴 전략 적용 (2차 필터)
        signals = []
        for code, name, df, trend_score in trend_candidates:
            try:
                signal = self._apply_strategies(code, name, df, trend_score)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"패턴 분석 오류 {code}: {e}")

        # 우선순위 정렬: 전략 우선순위 > 추세 점수
        priority_order = {"BUY": 0, "WATCH": 1}
        signals.sort(key=lambda x: (priority_order.get(x["action"], 2), -x["trend_score"]))

        logger.info(f"=== 스크리닝 완료: 매수신호 {sum(1 for s in signals if s['action'] == 'BUY')}개 ===")
        return signals

    def _apply_strategies(
        self, code: str, name: str, df: pd.DataFrame, trend_score: int
    ) -> Optional[Dict]:
        """3가지 전략 순서대로 적용, 첫 번째 신호 반환"""

        # VCP/Pre-breakout (최우선 - 가장 정밀한 진입)
        vcp = self.pre_breakout.analyze(code, name, df)
        if vcp.action != "NONE":
            return {
                "code": code, "name": name,
                "action": vcp.action,
                "strategy": "VCP",
                "trend_score": trend_score,
                "pivot": vcp.pivot,
                "current_price": vcp.current_price,
                "stop_loss": vcp.current_price * (1 - config.stop_loss_ratio),
                "message": vcp.message,
            }

        # 컵&핸들
        ch = self.cup_handle.analyze(code, name, df)
        if ch.action != "NONE":
            return {
                "code": code, "name": name,
                "action": ch.action,
                "strategy": "컵&핸들",
                "trend_score": trend_score,
                "pivot": ch.pivot,
                "current_price": ch.current_price,
                "stop_loss": ch.current_price * (1 - config.stop_loss_ratio),
                "message": ch.message,
            }

        # 신고가 돌파
        nh = self.new_high.analyze(code, name, df)
        if nh.action != "NONE":
            return {
                "code": code, "name": name,
                "action": nh.action,
                "strategy": "신고가",
                "trend_score": trend_score,
                "pivot": nh.high_52w,
                "current_price": nh.current_price,
                "stop_loss": nh.current_price * (1 - config.stop_loss_ratio),
                "message": nh.message,
            }

        return None
