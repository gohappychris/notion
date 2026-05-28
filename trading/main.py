"""
자동매매 메인 진입점
- 키움 OpenAPI+ 기반 미너비니 추세추종 자동매매
- Windows 환경 전용 (키움 HTS 설치 필요)

실행 방법:
  python main.py

사전 준비:
  1. 키움증권 계좌 및 OpenAPI+ 신청
  2. 키움 HTS(영웅문4) 설치 및 OpenAPI+ 모듈 설치
  3. .env 파일에 ACCOUNT_NO, ACCOUNT_PW 설정
  4. pip install -r requirements.txt
"""
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Windows 전용 체크
if sys.platform != "win32":
    print("[경고] 키움 OpenAPI+는 Windows 전용입니다.")
    print("       현재 환경에서는 백테스트 모드로 실행하세요.")
    sys.exit(1)

from PyQt5.QtWidgets import QApplication

from config import config
from kiwoom import KiwoomAPI, ORDER_TYPE
from screener import Screener
from portfolio import PortfolioManager
from portfolio.risk import RiskManager
from utils.logger import logger

import schedule


def is_market_hours() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:  # 토/일
        return False
    open_h, open_m = map(int, config.market_open.split(":"))
    close_h, close_m = map(int, config.market_close.split(":"))
    open_time = now.replace(hour=open_h, minute=open_m, second=0)
    close_time = now.replace(hour=close_h, minute=close_m, second=0)
    return open_time <= now <= close_time


class TradingBot:

    def __init__(self):
        self.api = KiwoomAPI()
        self.screener = Screener(self.api)
        self.portfolio: PortfolioManager = None
        self.signals = []

    def initialize(self) -> bool:
        """로그인 및 초기화"""
        if not self.api.login():
            return False

        account_no = os.getenv("ACCOUNT_NO", config.account_no)
        if not account_no:
            logger.error("계좌번호가 설정되지 않았습니다. .env 파일의 ACCOUNT_NO를 확인하세요.")
            return False

        balance = self.api.get_account_balance(account_no)
        total_eval = balance.get("total_eval", config.total_capital)
        logger.info(f"계좌: {account_no} | 총평가금액: {total_eval:,.0f}원")

        self.portfolio = PortfolioManager(self.api, account_no, total_eval)
        config.account_no = account_no
        return True

    def morning_screening(self):
        """장 시작 전 스크리닝 (08:50)"""
        logger.info("=== 아침 스크리닝 시작 ===")
        try:
            self.signals = self.screener.run()
            self._log_signals()
        except Exception as e:
            logger.exception(f"스크리닝 중 오류: {e}")

    def trading_loop(self):
        """장중 매수 실행 (09:00~15:00)"""
        if not is_market_hours():
            return
        if not self.signals:
            return

        risk_mgr = self.portfolio.risk_manager
        buy_signals = [s for s in self.signals if s["action"] == "BUY"]

        for signal in buy_signals:
            code = signal["code"]
            if code in self.portfolio.positions:
                continue

            # 현재 보유 종목 수 확인
            if len(self.portfolio.positions) >= config.max_positions:
                logger.info("최대 포지션 수 도달 - 신규 매수 중단")
                break

            if risk_mgr.is_daily_limit_hit():
                break

            entry_price = signal["current_price"]
            stop_loss = signal.get("stop_loss", entry_price * (1 - config.stop_loss_ratio))

            plan = risk_mgr.calc_position_size(
                code=code,
                name=signal["name"],
                entry_price=entry_price,
                pivot=signal["pivot"],
                stop_loss_price=stop_loss,
            )
            if plan:
                self.portfolio.buy(plan, strategy=signal["strategy"])

    def eod_routine(self):
        """장 마감 후 처리 (15:35)"""
        logger.info("=== 장 마감 루틴 ===")
        self.portfolio.print_status()
        self.portfolio.risk_manager.reset_daily_stats()

        # 실시간 구독 해제
        if self.portfolio.positions:
            self.api.unregister_realtime(self.portfolio.get_position_codes())

    def start_realtime(self):
        """보유 종목 실시간 시세 구독"""
        codes = self.portfolio.get_position_codes()
        if codes:
            from kiwoom import FID
            self.api.register_realtime(
                codes,
                [FID.CURRENT_PRICE, FID.HIGH, FID.LOW, FID.VOLUME],
                self.portfolio.on_price_update,
            )
            logger.info(f"실시간 시세 구독: {len(codes)}종목")

    def _log_signals(self):
        buy = [s for s in self.signals if s["action"] == "BUY"]
        watch = [s for s in self.signals if s["action"] == "WATCH"]

        logger.info(f"매수 신호 {len(buy)}개:")
        for s in buy:
            logger.info(
                f"  [{s['strategy']}] {s['name']}({s['code']}) "
                f"현재={s['current_price']:,.0f} 피봇={s['pivot']:,.0f} "
                f"추세점수={s['trend_score']}/8"
            )

        logger.info(f"관찰 종목 {len(watch)}개:")
        for s in watch[:10]:  # 상위 10개만 출력
            logger.info(
                f"  [{s['strategy']}] {s['name']}({s['code']}) "
                f"현재={s['current_price']:,.0f} | {s['message']}"
            )

    def run(self):
        """메인 루프"""
        if not self.initialize():
            sys.exit(1)

        # 스케줄 등록
        schedule.every().day.at(config.screening_time).do(self.morning_screening)
        schedule.every().day.at(config.market_open).do(self.start_realtime)
        schedule.every(1).minutes.do(self.trading_loop)
        schedule.every().day.at("15:35").do(self.eod_routine)

        logger.info("자동매매 봇 시작. Ctrl+C로 종료.")
        logger.info(f"스크리닝: {config.screening_time} | 장: {config.market_open}~{config.market_close}")

        # 당일 장중이면 즉시 스크리닝 실행
        if is_market_hours():
            self.morning_screening()

        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("봇 종료")
            self.eod_routine()


def main():
    app = QApplication(sys.argv)
    bot = TradingBot()
    bot.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
