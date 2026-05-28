"""
키움 OpenAPI+ 래퍼 클래스
- Windows + 키움 OpenAPI+ 설치 환경에서 동작
- PyQt5 이벤트 루프 기반 비동기 응답 처리
"""
import time
from typing import Optional, Dict, List, Callable
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop

from utils.logger import logger
from .constants import TR, FID, SCREEN, ORDER_TYPE, PRICE_TYPE


class KiwoomAPI(QAxWidget):
    """키움 OpenAPI+ COM 객체 래퍼"""

    CLSID = "{A1574A0D-6BFA-4BD7-9020-DED88711818D}"  # 키움 OpenAPI OCX

    def __init__(self):
        super().__init__()
        self.setControl(self.CLSID)

        self._login_event = QEventLoop()
        self._tr_event = QEventLoop()
        self._tr_data: Dict = {}
        self._real_callbacks: Dict[str, Callable] = {}

        self._connect_signals()

    # ------------------------------------------------------------------ #
    # 연결/로그인
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self.OnEventConnect.connect(self._on_event_connect)
        self.OnReceiveTrData.connect(self._on_receive_tr_data)
        self.OnReceiveRealData.connect(self._on_receive_real_data)
        self.OnReceiveMsg.connect(self._on_receive_msg)
        self.OnReceiveChejanData.connect(self._on_receive_chejan_data)

    def login(self) -> bool:
        """키움 자동 로그인 (로그인 설정 필요)"""
        self.dynamicCall("CommConnect()")
        self._login_event.exec_()
        state = self.dynamicCall("GetConnectState()")
        connected = state == 1
        if connected:
            logger.info("키움 OpenAPI 로그인 성공")
        else:
            logger.error("키움 OpenAPI 로그인 실패")
        return connected

    def get_login_info(self, tag: str) -> str:
        return self.dynamicCall("GetLoginInfo(QString)", tag)

    # ------------------------------------------------------------------ #
    # TR 요청 (동기식 래퍼)
    # ------------------------------------------------------------------ #

    def request_tr(
        self,
        tr_code: str,
        inputs: Dict[str, str],
        screen_no: str,
        prev_next: int = 0,
        timeout: float = 10.0,
    ) -> Optional[Dict]:
        """TR 요청 후 응답을 동기적으로 반환"""
        for key, value in inputs.items():
            self.dynamicCall("SetInputValue(QString, QString)", key, value)

        ret = self.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            tr_code, tr_code, prev_next, screen_no,
        )
        if ret != 0:
            logger.error(f"TR 요청 실패: {tr_code} (코드: {ret})")
            return None

        self._tr_data = {}
        ok = self._tr_event.exec_() == 0
        return self._tr_data if ok else None

    def _finish_tr(self):
        if self._tr_event.isRunning():
            self._tr_event.exit(0)

    # ------------------------------------------------------------------ #
    # 시세 데이터
    # ------------------------------------------------------------------ #

    def get_daily_ohlcv(
        self, code: str, start_date: str, end_date: str, adj_price: bool = True
    ) -> List[Dict]:
        """
        일봉 OHLCV 조회 (opt10081)
        start_date / end_date: "YYYYMMDD"
        """
        inputs = {
            "종목코드": code,
            "기준일자": end_date,
            "수정주가구분": "1" if adj_price else "0",
        }
        all_rows = []
        prev_next = 0

        while True:
            data = self.request_tr(TR.DAILY_CHART, inputs, SCREEN.DAILY_CHART, prev_next)
            if not data:
                break

            rows = data.get("rows", [])
            all_rows.extend(rows)

            # 조회 시작일보다 이전 데이터면 종료
            if rows and rows[-1]["date"] <= start_date:
                break
            if not data.get("has_next"):
                break
            prev_next = 2
            time.sleep(0.2)  # API 호출 제한 준수

        # start_date 이후 데이터만 필터링
        return [r for r in all_rows if r["date"] >= start_date]

    def get_stock_basic_info(self, code: str) -> Dict:
        """주식 기본정보 조회 (opt10001)"""
        data = self.request_tr(
            TR.STOCK_INFO,
            {"종목코드": code},
            SCREEN.STOCK_INFO,
        )
        return data.get("info", {}) if data else {}

    def get_market_codes(self, market: str) -> List[str]:
        """
        시장 전체 종목코드 반환
        market: "0" (코스피), "10" (코스닥)
        """
        raw = self.dynamicCall("GetCodeListByMarket(QString)", market)
        return [c.strip() for c in raw.split(";") if c.strip()]

    def get_stock_name(self, code: str) -> str:
        return self.dynamicCall("GetMasterCodeName(QString)", code)

    # ------------------------------------------------------------------ #
    # 주문
    # ------------------------------------------------------------------ #

    def send_order(
        self,
        rq_name: str,
        screen_no: str,
        account_no: str,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        price_type: str,
        orig_order_no: str = "",
    ) -> int:
        """주문 전송 (0: 성공)"""
        ret = self.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            rq_name, screen_no, account_no, order_type,
            code, qty, price, price_type, orig_order_no,
        )
        if ret != 0:
            logger.error(f"주문 실패: {code} qty={qty} type={order_type} (코드: {ret})")
        return ret

    def buy(self, account_no: str, code: str, qty: int, price: int = 0) -> int:
        price_type = PRICE_TYPE.MARKET if price == 0 else PRICE_TYPE.LIMIT
        return self.send_order(
            "매수", SCREEN.ORDER, account_no,
            ORDER_TYPE.BUY, code, qty, price, price_type,
        )

    def sell(self, account_no: str, code: str, qty: int, price: int = 0) -> int:
        price_type = PRICE_TYPE.MARKET if price == 0 else PRICE_TYPE.LIMIT
        return self.send_order(
            "매도", SCREEN.ORDER, account_no,
            ORDER_TYPE.SELL, code, qty, price, price_type,
        )

    # ------------------------------------------------------------------ #
    # 계좌 정보
    # ------------------------------------------------------------------ #

    def get_account_balance(self, account_no: str) -> Dict:
        """예수금/평가금액 조회"""
        data = self.request_tr(
            TR.ACCOUNT_INFO,
            {"계좌번호": account_no, "비밀번호": "", "비밀번호입력매체구분": "00", "조회구분": "2"},
            SCREEN.ACCOUNT,
        )
        return data.get("balance", {}) if data else {}

    def get_positions(self, account_no: str) -> List[Dict]:
        """보유 종목 조회"""
        data = self.request_tr(
            TR.POSITIONS,
            {"계좌번호": account_no, "비밀번호": "", "비밀번호입력매체구분": "00", "조회구분": "1"},
            SCREEN.ACCOUNT,
        )
        return data.get("positions", []) if data else []

    # ------------------------------------------------------------------ #
    # 실시간 시세 등록
    # ------------------------------------------------------------------ #

    def register_realtime(self, codes: List[str], fids: List[int], callback: Callable):
        """실시간 시세 구독"""
        code_str = ";".join(codes)
        fid_str = ";".join(map(str, fids))
        self.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            SCREEN.REALTIME, code_str, fid_str, "1",
        )
        for code in codes:
            self._real_callbacks[code] = callback

    def unregister_realtime(self, codes: List[str]):
        code_str = ";".join(codes)
        self.dynamicCall("SetRealRemove(QString, QString)", SCREEN.REALTIME, code_str)
        for code in codes:
            self._real_callbacks.pop(code, None)

    # ------------------------------------------------------------------ #
    # 이벤트 핸들러
    # ------------------------------------------------------------------ #

    def _on_event_connect(self, err_code: int):
        if self._login_event.isRunning():
            self._login_event.exit(err_code)

    def _on_receive_tr_data(
        self,
        screen_no: str,
        rq_name: str,
        tr_code: str,
        record_name: str,
        prev_next: str,
        *args,
    ):
        has_next = prev_next == "2"
        self._tr_data = self._parse_tr(tr_code, rq_name, has_next)
        self._finish_tr()

    def _parse_tr(self, tr_code: str, rq_name: str, has_next: bool) -> Dict:
        """TR 코드별 응답 파싱"""
        data = {"has_next": has_next}

        if tr_code == TR.DAILY_CHART:
            count = self.dynamicCall("GetRepeatCnt(QString, QString)", tr_code, rq_name)
            rows = []
            for i in range(count):
                rows.append({
                    "date": self._get_comm_data(tr_code, rq_name, i, "일자").strip(),
                    "open": abs(int(self._get_comm_data(tr_code, rq_name, i, "시가") or 0)),
                    "high": abs(int(self._get_comm_data(tr_code, rq_name, i, "고가") or 0)),
                    "low": abs(int(self._get_comm_data(tr_code, rq_name, i, "저가") or 0)),
                    "close": abs(int(self._get_comm_data(tr_code, rq_name, i, "현재가") or 0)),
                    "volume": abs(int(self._get_comm_data(tr_code, rq_name, i, "거래량") or 0)),
                })
            data["rows"] = rows

        elif tr_code == TR.STOCK_INFO:
            data["info"] = {
                "name": self._get_comm_data(tr_code, rq_name, 0, "종목명").strip(),
                "current_price": abs(int(self._get_comm_data(tr_code, rq_name, 0, "현재가") or 0)),
                "volume": abs(int(self._get_comm_data(tr_code, rq_name, 0, "거래량") or 0)),
                "market_cap": self._get_comm_data(tr_code, rq_name, 0, "시가총액").strip(),
                "per": self._get_comm_data(tr_code, rq_name, 0, "PER").strip(),
                "eps": self._get_comm_data(tr_code, rq_name, 0, "EPS").strip(),
            }

        elif tr_code == TR.ACCOUNT_INFO:
            data["balance"] = {
                "deposit": int(self._get_comm_data(tr_code, rq_name, 0, "예수금") or 0),
                "orderable": int(self._get_comm_data(tr_code, rq_name, 0, "주문가능금액") or 0),
                "total_eval": int(self._get_comm_data(tr_code, rq_name, 0, "총평가금액") or 0),
            }

        elif tr_code == TR.POSITIONS:
            count = self.dynamicCall("GetRepeatCnt(QString, QString)", tr_code, rq_name)
            positions = []
            for i in range(count):
                positions.append({
                    "code": self._get_comm_data(tr_code, rq_name, i, "종목번호").strip().replace("A", ""),
                    "name": self._get_comm_data(tr_code, rq_name, i, "종목명").strip(),
                    "qty": int(self._get_comm_data(tr_code, rq_name, i, "보유수량") or 0),
                    "avg_price": int(self._get_comm_data(tr_code, rq_name, i, "매입가") or 0),
                    "current_price": abs(int(self._get_comm_data(tr_code, rq_name, i, "현재가") or 0)),
                    "profit_loss": int(self._get_comm_data(tr_code, rq_name, i, "평가손익") or 0),
                    "profit_ratio": float(self._get_comm_data(tr_code, rq_name, i, "수익률(%)") or 0),
                })
            data["positions"] = positions

        return data

    def _get_comm_data(self, tr_code, rq_name, index, field_name) -> str:
        return self.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            tr_code, rq_name, index, field_name,
        )

    def _on_receive_real_data(self, code: str, real_type: str, real_data: str):
        callback = self._real_callbacks.get(code)
        if not callback:
            return

        def get_real(fid: int) -> str:
            return self.dynamicCall("GetCommRealData(QString, int)", code, fid)

        price_data = {
            "code": code,
            "price": abs(int(get_real(FID.CURRENT_PRICE) or 0)),
            "change_ratio": float(get_real(FID.CHANGE_RATIO) or 0),
            "volume": abs(int(get_real(FID.VOLUME) or 0)),
            "high": abs(int(get_real(FID.HIGH) or 0)),
            "low": abs(int(get_real(FID.LOW) or 0)),
        }
        callback(price_data)

    def _on_receive_msg(self, screen_no: str, rq_name: str, tr_code: str, msg: str):
        logger.debug(f"[{tr_code}] {msg}")

    def _on_receive_chejan_data(self, gubun: str, item_cnt: int, fid_list: str):
        # "0": 주문체결, "1": 잔고
        if gubun == "0":
            code = self.dynamicCall("GetChejanData(int)", 9001).strip().replace("A", "")
            order_type = self.dynamicCall("GetChejanData(int)", 906).strip()
            qty = int(self.dynamicCall("GetChejanData(int)", 911) or 0)
            price = int(self.dynamicCall("GetChejanData(int)", 910) or 0)
            logger.info(f"체결: {code} {order_type} {qty}주 @ {price:,}원")
