# 증권 통합 잔고 대시보드 & 알림

키움·미래에셋·신한투자증권 계좌의 주식 잔고를 한국/미국 장 전·후로 수집해
**종목별 변동·전일대비 총자산·추이**를 Notion 대시보드와 텔레그램으로 알려줍니다.

## 설계 요약

| 항목 | 결정 |
|------|------|
| 수집 — 키움 | 공식 REST API, **완전 자동** (국내 + 미국) |
| 수집 — 미래/신한 | **반자동** (Phase 3: Notion 수동입력 or CODEF 간편인증) |
| 대시보드 | Notion DB 2개 |
| 알림 | 텔레그램 봇 (핵심 요약 + 큰 변동 강조) |
| 실행 | GitHub Actions cron |
| 총자산 정의 | **순자산 = 주식평가 + 현금 − 미수 − 신용** |

> 미래에셋·신한은 개인용 공식 REST API가 없어( [미래에셋 AnyLink 중단](https://securities.miraeasset.com/imf/200/imf401.do) ), 키움만 [공식 REST API](https://openapi.kiwoom.com/) 로 자동화하고 두 곳은 반자동으로 합칩니다.

## 디렉토리

```
collectors/kiwoom.py   키움 인증·잔고 조회 → 공통 스키마
core/models.py         공통 스키마(Holding/AccountSummary/Snapshot)
core/calculate.py      전일대비·수익률·신규매매·환율분리 (Phase 2)
core/fx.py             환율 (Phase 2)
sinks/notion_sink.py   Notion 적재 (Phase 1)
sinks/telegram.py      텔레그램 알림 (Phase 1)
main.py                실행 진입점
.github/workflows/     스케줄러
```

## 빠른 시작 (Phase 0)

```bash
pip install -r requirements.txt
cp .env.example .env      # 키움 키를 채운다 (먼저 KIWOOM_ENV=mock 권장)

python main.py --raw      # ① 키움 원본 응답 출력 → 필드명 검증
python main.py            # ② 보유종목/순자산 요약 출력
```

### 첫 실행 시 필드 검증
키움 REST 는 TR별 응답 키가 다릅니다. `python main.py --raw` 로 실제 응답을
보고, 다르면 `collectors/kiwoom.py` 상단의 `TR_*` / `FIELD_*` / `F_*` 상수만
실제 키에 맞게 고치면 됩니다. (나머지 로직은 그대로 동작)

## 사전 준비물

- [ ] **키움** REST API 사용 등록 → App Key/Secret ([포털](https://openapi.kiwoom.com/))
- [ ] **텔레그램** BotFather 봇 토큰 + 내 chat_id   *(Phase 1)*
- [ ] **Notion** Integration 토큰 + DB 2개   *(Phase 1, DB는 MCP로 생성 예정)*
- [ ] 위 값들을 GitHub **Secrets** 에 등록 (자동 실행용)

## Notion DB 스키마 (생성 예정)

**Snapshots** (종목 1행/스냅샷): Date, 증권사, 시장(KR/US), 종목명, 수량,
평균단가, 현재가, 평가금액(원), 전일대비 평가액, 수익률%, 스냅샷종류

**Daily Summary** (하루 1행): Date, 총자산(원), 전일대비, 전일대비%,
키움/미래에셋/신한 소계, KR소계, US소계

## 로드맵

- **Phase 0** ✅ 골격 + 키움 잔고 콘솔 출력
- **Phase 1** 키움 → Notion 적재 + 텔레그램 마감 알림, 전일대비
- **Phase 2** 신규매매 감지·종목별 수익률·환율분리·비중, 미국장 스케줄
- **Phase 3** 미래/신한 반자동 병합 + 7/30일 추이 리포트
