"""전일대비 / 수익률 / 신규매매 감지 / 비중 계산 (Phase 2).

입력: 오늘 Snapshot + 어제 Snapshot(또는 Notion 에서 읽은 직전 스냅샷)
출력: 알림/대시보드에 쓸 가공 결과(dict 또는 dataclass).

구현 예정:
  - diff_holdings(today, yesterday): 종목별 평가액·수량 변화, 신규/청산 감지
  - asset_change(today, yesterday): 총자산 증감(원/%)
  - split_us_change(...): 미국주식 변동을 '주가요인' vs '환율요인'으로 분리
  - allocation(snapshot): 증권사별·시장별 비중
"""
from __future__ import annotations

# TODO(Phase 2): 위 함수들 구현
