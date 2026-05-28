"""
기술적 지표 계산 모듈
"""
import pandas as pd
import numpy as np
from typing import Optional


class TechnicalIndicators:
    """pandas DataFrame 기반 기술적 지표 계산"""

    @staticmethod
    def add_moving_averages(df: pd.DataFrame, periods: list = [10, 20, 50, 150, 200]) -> pd.DataFrame:
        for p in periods:
            df[f"ma{p}"] = df["close"].rolling(p).mean()
        return df

    @staticmethod
    def add_volume_ma(df: pd.DataFrame, periods: list = [10, 50]) -> pd.DataFrame:
        for p in periods:
            df[f"vol_ma{p}"] = df["volume"].rolling(p).mean()
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        df["atr"] = tr.rolling(period).mean()
        df["atr_ratio"] = df["atr"] / df["close"]
        return df

    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        ma = df["close"].rolling(period).mean()
        sd = df["close"].rolling(period).std()
        df["bb_upper"] = ma + std * sd
        df["bb_lower"] = ma - std * sd
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / ma
        return df

    @staticmethod
    def add_52week_stats(df: pd.DataFrame) -> pd.DataFrame:
        df["high_52w"] = df["high"].rolling(252).max()
        df["low_52w"] = df["low"].rolling(252).min()
        df["from_52w_high"] = (df["close"] - df["high_52w"]) / df["high_52w"]
        df["from_52w_low"] = (df["close"] - df["low_52w"]) / df["low_52w"]
        return df

    @staticmethod
    def add_relative_strength(df: pd.DataFrame, market_df: pd.DataFrame, period: int = 63) -> pd.DataFrame:
        """
        상대강도(RS) 계산: 종목 수익률 / 시장 수익률
        period: 약 3개월(63거래일)
        """
        stock_ret = df["close"].pct_change(period)
        market_ret = market_df["close"].pct_change(period)
        df["rs"] = stock_ret / market_ret.abs().replace(0, np.nan)
        return df

    @staticmethod
    def add_vcp_tightness(df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """VCP(변동성 수축 패턴) - 최근 N일 가격 변동 범위"""
        df["vcp_range"] = (df["high"].rolling(period).max() - df["low"].rolling(period).min()) / df["close"]
        return df

    @classmethod
    def prepare_dataframe(cls, rows: list) -> pd.DataFrame:
        """API 응답 rows -> 분석용 DataFrame 변환"""
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df = df.sort_values("date").reset_index(drop=True)

        df = cls.add_moving_averages(df)
        df = cls.add_volume_ma(df)
        df = cls.add_rsi(df)
        df = cls.add_atr(df)
        df = cls.add_52week_stats(df)
        df = cls.add_vcp_tightness(df)
        return df
