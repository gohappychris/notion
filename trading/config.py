"""
자동매매 설정 파일
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class TradingConfig:
    # 계좌 설정
    account_no: str = ""           # 키움증권 계좌번호 (환경변수로 주입 권장)
    account_password: str = ""     # 계좌 비밀번호

    # 자금 관리
    total_capital: float = 10_000_000   # 총 운용 자금 (원)
    max_position_ratio: float = 0.20    # 종목당 최대 비중 (20%)
    max_positions: int = 5              # 최대 보유 종목 수
    cash_reserve_ratio: float = 0.10   # 현금 예비 비율 (10%)

    # 리스크 관리
    stop_loss_ratio: float = 0.07      # 손절선 (7% - 미너비니 기본)
    trailing_stop_ratio: float = 0.10  # 트레일링 스탑 (10%)
    max_daily_loss_ratio: float = 0.02 # 일일 최대 손실 한도 (2%)

    # 매수 조건
    min_volume: int = 100_000           # 최소 일일 거래량
    min_price: int = 5_000             # 최소 주가
    max_price: int = 500_000           # 최대 주가
    breakout_volume_ratio: float = 1.5  # 돌파 시 최소 거래량 비율 (평균 대비)

    # 미너비니 추세 템플릿 설정
    ma50_period: int = 50
    ma150_period: int = 150
    ma200_period: int = 200
    rs_min_rating: float = 70.0         # 상대강도 최소값

    # 컵&핸들 설정
    cup_min_weeks: int = 7
    cup_max_weeks: int = 65
    cup_max_depth_ratio: float = 0.33   # 컵 최대 깊이 (33%)
    handle_max_depth_ratio: float = 0.12 # 핸들 최대 깊이 (12%)
    handle_min_weeks: int = 1
    handle_max_weeks: int = 6

    # Pre-breakout (VCP) 설정
    vcp_max_distance_ratio: float = 0.05  # 피봇에서 최대 거리 (5%)
    vcp_tight_range_days: int = 3         # 타이트 구간 일수

    # 신고가 설정
    new_high_lookback_days: int = 252   # 52주 신고가 기준
    new_high_buffer_ratio: float = 0.03 # 신고가 근접 허용 범위 (3%)

    # 스케줄링
    screening_time: str = "08:50"       # 장 시작 전 스크리닝 시간
    market_open: str = "09:00"
    market_close: str = "15:30"

    # 유니버스 (스크리닝 대상)
    target_markets: List[str] = field(default_factory=lambda: ["0", "10"])  # 0:코스피, 10:코스닥


# 싱글톤 인스턴스
config = TradingConfig()
