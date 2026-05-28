"""
로거 설정 (loguru 기반)
"""
import sys
from loguru import logger

logger.remove()

# 콘솔 출력 (INFO 이상)
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
    colorize=True,
)

# 파일 로그 (DEBUG 이상, 일별 롤링)
logger.add(
    "logs/trading_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="1 day",
    retention="30 days",
    encoding="utf-8",
)

# 주문/체결 전용 로그
logger.add(
    "logs/orders_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
    level="INFO",
    filter=lambda r: "체결" in r["message"] or "주문" in r["message"] or "매수" in r["message"] or "매도" in r["message"],
    rotation="1 day",
    retention="90 days",
    encoding="utf-8",
)
