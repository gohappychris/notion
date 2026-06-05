"""Notion 적재 (Phase 1).

DB 2개에 기록:
  - Snapshots DB : 스냅샷마다 종목 1행
  - Daily Summary DB : 하루 총자산 1행

구현 예정:
  - upsert_snapshot(snapshot): notion-client 로 종목행 생성
  - upsert_daily_summary(date, totals): 총자산/전일대비/증권사별 소계 기록
DB ID 는 config.NOTION_SNAPSHOTS_DB_ID / NOTION_SUMMARY_DB_ID 사용.
(DB 자체는 Notion MCP 로 생성 예정 - 스키마는 README 참고)
"""
from __future__ import annotations

# TODO(Phase 1): notion-client 연동 구현
