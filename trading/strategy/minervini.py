"""
마크 미너비니 추세 템플릿 (Trend Template) 스크리너
- SEPA (Specific Entry Point Analysis) 기반
"""
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Tuple
from config import config
from utils.logger import logger


@dataclass
class TrendTemplateResult:
    code: str
    name: str
    passed: bool
    score: int = 0              # 통과 기준 수 (최대 8)
    current_price: float = 0.0
    ma50: float = 0.0
    ma150: float = 0.0
    ma200: float = 0.0
    from_52w_high: float = 0.0
    from_52w_low: float = 0.0
    failed_criteria: List[str] = field(default_factory=list)


class MinerviniScreener:
    """
    미너비니 추세 템플릿 8가지 조건 확인
    (출처: 'Trade Like a Stock Market Wizard')
    """

    def screen(self, code: str, name: str, df: pd.DataFrame) -> TrendTemplateResult:
        result = TrendTemplateResult(code=code, name=name, passed=False)

        if len(df) < 210:
            result.failed_criteria.append("데이터 부족 (210일 미만)")
            return result

        last = df.iloc[-1]
        result.current_price = last["close"]
        result.ma50 = last.get("ma50", 0)
        result.ma150 = last.get("ma150", 0)
        result.ma200 = last.get("ma200", 0)
        result.from_52w_high = last.get("from_52w_high", -1)
        result.from_52w_low = last.get("from_52w_low", 0)

        checks = self._run_checks(df, last)
        result.score = sum(1 for _, ok in checks if ok)
        result.failed_criteria = [name for name, ok in checks if not ok]
        result.passed = result.score >= 7  # 8개 중 7개 이상

        return result

    def _run_checks(self, df: pd.DataFrame, last: pd.Series) -> List[Tuple[str, bool]]:
        price = last["close"]
        ma50 = last.get("ma50", 0)
        ma150 = last.get("ma150", 0)
        ma200 = last.get("ma200", 0)
        high_52w = last.get("high_52w", price)
        low_52w = last.get("low_52w", price)

        # 200일선 기울기 확인 (최근 20일 vs 20일 전)
        ma200_now = df["ma200"].iloc[-1] if "ma200" in df.columns else 0
        ma200_prev = df["ma200"].iloc[-22] if len(df) > 22 else ma200_now
        ma200_rising = ma200_now > ma200_prev

        return [
            # 1. 현재가 > 150일선 & 200일선
            ("현재가 > MA150, MA200", price > ma150 and price > ma200),

            # 2. 150일선 > 200일선
            ("MA150 > MA200", ma150 > ma200),

            # 3. 200일선이 최소 1개월 이상 상승 추세
            ("MA200 상승 중", ma200_rising),

            # 4. 50일선 > 150일선 & 200일선
            ("MA50 > MA150, MA200", ma50 > ma150 and ma50 > ma200),

            # 5. 현재가 > 50일선
            ("현재가 > MA50", price > ma50),

            # 6. 현재가가 52주 저점 대비 +25% 이상
            ("52주 저점 +25%", (price - low_52w) / low_52w >= 0.25 if low_52w > 0 else False),

            # 7. 현재가가 52주 고점 대비 -25% 이내 (고점 근처)
            ("52주 고점 -25% 이내", (high_52w - price) / high_52w <= 0.25 if high_52w > 0 else False),

            # 8. 거래량 조건 (평균 거래량 충족)
            ("거래량 충분", last.get("volume", 0) >= config.min_volume or
             df["volume"].tail(20).mean() >= config.min_volume),
        ]

    def batch_screen(
        self, stock_list: List[Tuple[str, str, pd.DataFrame]], min_score: int = 6
    ) -> List[TrendTemplateResult]:
        """
        여러 종목을 한번에 스크리닝
        stock_list: [(code, name, df), ...]
        """
        results = []
        for code, name, df in stock_list:
            try:
                r = self.screen(code, name, df)
                if r.score >= min_score:
                    results.append(r)
                    logger.debug(
                        f"[추세템플릿] {name}({code}) score={r.score}/8 "
                        f"{'✓' if r.passed else '△'}"
                    )
            except Exception as e:
                logger.warning(f"스크리닝 오류 {code}: {e}")

        results.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"추세 템플릿 통과: {sum(1 for r in results if r.passed)}종목")
        return results
