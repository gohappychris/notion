"""키움 REST API 수집기.

인증(토큰 발급) → 계좌평가잔고내역 / 계좌평가현황 조회 → 공통 스키마 정규화.

⚠️ 검증 필요(첫 실행 때 --raw 로 실제 응답을 찍어 확인):
  - TR(api-id) 코드와 엔드포인트 경로
  - 응답 JSON 의 필드명(아래 FIELD_* 상수)
키움 REST 는 TR 별로 응답 키가 다르므로, 키 발급 후 실제 응답에 맞춰
이 파일 상단의 상수만 고치면 된다. 나머지 로직은 그대로 동작한다.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import requests

from config import KiwoomConfig, require_kiwoom
from core.models import AccountSummary, Holding

# ----------------------------------------------------------------------------
# 엔드포인트 / TR 코드  (※ 키움 공식 API 문서로 최종 확인)
# ----------------------------------------------------------------------------
TOKEN_PATH = "/oauth2/token"          # 접근토큰 발급
ACCOUNT_PATH = "/api/dostk/acnt"      # 계좌 관련 TR 공통 경로

TR_DOMESTIC_BALANCE = "kt00018"       # 계좌평가잔고내역요청 (국내 보유종목)
TR_ACCOUNT_STATUS = "kt00004"         # 계좌평가현황요청 (총평가/예수금 등)
TR_DEPOSIT_DETAIL = "kt00001"         # 예수금상세현황요청 (미수/신용 등)

# 해외주식 잔고: 키움 REST 의 해외 커버리지는 계정/문서로 확인 후 채운다.
TR_OVERSEAS_BALANCE = ""              # TODO: 해외주식 잔고 TR (확인 후 입력)
OVERSEAS_PATH = ""                    # TODO: 해외 엔드포인트 경로

# ----------------------------------------------------------------------------
# 응답 필드명  (첫 실행 --raw 결과로 검증/수정)
# ----------------------------------------------------------------------------
# kt00018 보유종목 배열 키 후보(문서/응답에 맞게 1개로 확정)
FIELD_BALANCE_LIST = "acnt_evlt_remn_indv_tot"
F_SYMBOL = "stk_cd"      # 종목코드
F_NAME = "stk_nm"        # 종목명
F_QTY = "rmnd_qty"       # 보유수량
F_AVG = "pur_pric"       # 매입단가
F_CUR = "cur_prc"        # 현재가
F_EVAL = "evlt_amt"      # 평가금액
F_PNL = "evltv_prft"     # 평가손익
F_RATE = "prft_rt"       # 수익률


def _to_float(v: Any) -> float:
    """키움 숫자필드는 문자열/부호/콤마가 섞여 올 수 있어 안전 변환."""
    if v is None:
        return 0.0
    s = str(v).strip().replace(",", "")
    if not s or s in {"-", "+"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


class KiwoomClient:
    def __init__(self, cfg: KiwoomConfig, *, timeout: int = 15):
        require_kiwoom(cfg)
        self.cfg = cfg
        self.timeout = timeout
        self._token: Optional[str] = None
        self._session = requests.Session()

    # --- 인증 --------------------------------------------------------------
    def authenticate(self) -> str:
        url = self.cfg.base_url + TOKEN_PATH
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.cfg.app_key,
            "secretkey": self.cfg.secret_key,
        }
        resp = self._session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # 키움 토큰 응답 키는 'token' (문서로 확인). 호환 위해 폴백.
        token = data.get("token") or data.get("access_token")
        if not token:
            raise RuntimeError(f"토큰 발급 실패: {data}")
        self._token = token
        return token

    def _headers(self, api_id: str, *, cont_yn: str = "N", next_key: str = "") -> dict:
        if not self._token:
            self.authenticate()
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {self._token}",
            "api-id": api_id,
            "cont-yn": cont_yn,
            "next-key": next_key,
        }

    def _request(self, path: str, api_id: str, body: dict) -> dict:
        """단일 TR 요청. 연속조회(cont-yn) 페이지를 모두 모아 반환.

        반환: {"items": [...합쳐진 리스트...], "last": <마지막 응답 원본>}
        리스트 키를 모르는 호출자를 위해 첫 응답 원본도 함께 돌려준다.
        """
        url = self.cfg.base_url + path
        merged: list[dict] = []
        cont_yn, next_key = "N", ""
        last: dict = {}
        for _ in range(50):  # 안전 상한
            headers = self._headers(api_id, cont_yn=cont_yn, next_key=next_key)
            resp = self._session.post(url, headers=headers, json=body, timeout=self.timeout)
            resp.raise_for_status()
            last = resp.json()
            rows = last.get(FIELD_BALANCE_LIST)
            if isinstance(rows, list):
                merged.extend(rows)
            # 연속조회 여부는 응답 헤더로 전달됨
            cont_yn = resp.headers.get("cont-yn", "N")
            next_key = resp.headers.get("next-key", "")
            if cont_yn != "Y":
                break
            time.sleep(0.3)
        return {"items": merged, "last": last}

    # --- 조회 --------------------------------------------------------------
    def fetch_domestic_balance_raw(self, account_no: str = "") -> dict:
        """국내 보유종목 원본 응답(필드명 검증용)."""
        body = {"qry_tp": "1", "dmst_stex_tp": "KRX"}  # 조회구분 등 - 문서로 확인
        if account_no:
            body["acnt_no"] = account_no
        return self._request(ACCOUNT_PATH, TR_DOMESTIC_BALANCE, body)

    def get_domestic_holdings(self, account_no: str = "") -> list[Holding]:
        raw = self.fetch_domestic_balance_raw(account_no)
        holdings: list[Holding] = []
        for row in raw["items"]:
            qty = _to_float(row.get(F_QTY))
            if qty == 0:
                continue
            eval_amt = _to_float(row.get(F_EVAL))
            holdings.append(
                Holding(
                    broker="키움",
                    market="KR",
                    symbol=str(row.get(F_SYMBOL, "")).lstrip("A"),  # 'A005930' → '005930'
                    name=str(row.get(F_NAME, "")).strip(),
                    quantity=qty,
                    avg_price=_to_float(row.get(F_AVG)),
                    current_price=_to_float(row.get(F_CUR)),
                    currency="KRW",
                    eval_amount_native=eval_amt,
                    eval_amount_krw=eval_amt,
                    pnl_amount_native=_to_float(row.get(F_PNL)),
                    pnl_rate=_to_float(row.get(F_RATE)),
                )
            )
        return holdings

    def get_overseas_holdings(self, account_no: str = "") -> list[Holding]:
        """미국 등 해외주식 보유종목.

        TODO(Phase 0 후속): 키움 해외 TR/경로 확정 후 구현.
        지금은 빈 리스트를 반환해 파이프라인이 끊기지 않게 한다.
        """
        if not TR_OVERSEAS_BALANCE or not OVERSEAS_PATH:
            return []
        # raw = self._request(OVERSEAS_PATH, TR_OVERSEAS_BALANCE, {...})
        # ... 정규화 ...
        return []

    def get_account_summary(self, account_no: str = "") -> AccountSummary:
        """총평가/예수금/미수/신용을 모아 순자산 계산용 요약 생성.

        TODO: kt00004/kt00001 응답 필드명 확정 후 매핑. 우선 잔고합으로 근사.
        """
        return AccountSummary(broker="키움")


def collect_kiwoom(cfg: KiwoomConfig, account_no: str = "") -> tuple[list[Holding], AccountSummary]:
    """키움 한 계좌의 (보유종목, 계좌요약)을 수집하는 진입점."""
    client = KiwoomClient(cfg)
    client.authenticate()
    holdings = client.get_domestic_holdings(account_no) + client.get_overseas_holdings(account_no)
    summary = client.get_account_summary(account_no)
    # 요약이 비어 있으면 보유종목 평가합으로 최소 채움
    if summary.total_eval_krw == 0:
        summary.total_eval_krw = sum(h.eval_amount_krw for h in holdings)
    return holdings, summary
