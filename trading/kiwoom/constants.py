"""
키움 OpenAPI TR 코드 및 FID 상수 정의
"""

# TR 코드
class TR:
    DAILY_CHART = "opt10081"      # 주식일봉차트조회
    MINUTE_CHART = "opt10080"     # 주식분봉차트조회
    STOCK_INFO = "opt10001"       # 주식기본정보
    STOCK_PRICE = "opt10003"      # 주식현재가일별요청
    MULTI_STOCK = "optkwfid"      # 관심종목정보요청
    MARKET_STOCKS = "opt20006"    # 업종포함종목
    ACCOUNT_INFO = "opw00001"     # 예수금상세현황
    POSITIONS = "opw00018"        # 계좌평가잔고내역
    ORDER_HISTORY = "opt10076"    # 주문체결내역
    COND_SEARCH = "opt10028"      # 조건검색


# FID 코드 (실시간)
class FID:
    CURRENT_PRICE = 10   # 현재가
    CHANGE = 11          # 전일대비
    CHANGE_RATIO = 12    # 등락율
    VOLUME = 13          # 누적거래량
    AMOUNT = 14          # 누적거래대금
    OPEN = 16            # 시가
    HIGH = 17            # 고가
    LOW = 18             # 저가
    MARKET_CAP = 311     # 시가총액


# 화면번호 (스크린 넘버)
class SCREEN:
    STOCK_INFO = "0001"
    DAILY_CHART = "0002"
    REALTIME = "0100"
    ORDER = "0200"
    ACCOUNT = "0300"
    SCREENER = "0400"


# 주문 타입
class ORDER_TYPE:
    BUY = 1
    SELL = 2
    CANCEL_BUY = 3
    CANCEL_SELL = 4
    MODIFY_BUY = 5
    MODIFY_SELL = 6


# 호가 구분
class PRICE_TYPE:
    LIMIT = "00"          # 지정가
    MARKET = "03"         # 시장가
    BEST_LIMIT = "05"     # 최우선지정가
    PRE_MARKET = "61"     # 장전시간외
    POST_MARKET = "62"    # 장후시간외


# 시장 구분
class MARKET:
    KOSPI = "0"
    KOSDAQ = "10"
    KONEX = "20"
