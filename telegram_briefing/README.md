# 한국 주식 텔레그램 새벽 브리핑

매일 아침 텔레그램 주식 채널의 밤새 메시지를 Claude AI로 요약하여 구조화된 투자 브리핑을 출력합니다.

---

## 목차

1. [Telegram API 키 발급](#1-telegram-api-키-발급)
2. [환경 설정 (.env)](#2-환경-설정-env)
3. [config.yaml 채널 추가](#3-configyaml-채널-추가)
4. [설치 및 최초 실행](#4-설치-및-최초-실행)
5. [cron 자동 실행 등록](#5-cron-자동-실행-등록)
6. [CLI 옵션](#6-cli-옵션)

---

## 1. Telegram API 키 발급

1. 브라우저에서 [https://my.telegram.org](https://my.telegram.org) 접속
2. 본인 전화번호로 로그인 (국가 코드 포함, 예: +82 10-xxxx-xxxx)
3. **API development tools** 메뉴 클릭
4. App title, Short name 입력 후 **Create application** 클릭
5. 발급된 **`api_id`** (숫자)와 **`api_hash`** (문자열) 복사

---

## 2. 환경 설정 (.env)

프로젝트 폴더에 `.env` 파일 생성 (`.env.example` 참고):

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+821012345678
ANTHROPIC_API_KEY=sk-ant-...
```

| 변수명 | 설명 |
|---|---|
| `TELEGRAM_API_ID` | my.telegram.org에서 발급받은 숫자 ID |
| `TELEGRAM_API_HASH` | my.telegram.org에서 발급받은 해시 문자열 |
| `TELEGRAM_PHONE` | 텔레그램 가입 전화번호 (국가 코드 포함) |
| `ANTHROPIC_API_KEY` | Anthropic Console에서 발급한 API 키 |

---

## 3. config.yaml 채널 추가

`config.yaml`을 열어 구독 중인 채널을 추가합니다:

```yaml
channels:
  - name: "채널 표시명"      # 브리핑에 표시될 이름
    username: "@채널아이디"   # 텔레그램 채널 username (@ 포함)
    priority: high           # high / medium / low

time_window:
  start_hour: 22  # 수집 시작: 전날 밤 10시 KST
  end_hour: 8     # 수집 종료: 당일 오전 8시 KST
```

**priority 우선순위:**
- `high` — 토큰 한도 초과 시 마지막까지 유지
- `medium` — 중간 우선순위
- `low` — 토큰 한도 초과 시 먼저 제거

채널 username은 채널 링크 `t.me/username` 에서 확인할 수 있습니다.

---

## 4. 설치 및 최초 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 최초 실행 (전화번호 인증 필요)
python main.py
```

**최초 실행 시 인증 과정:**

1. 등록된 전화번호로 Telegram 인증 코드 전송
2. 터미널에 코드 입력
3. 2단계 인증이 설정된 경우 비밀번호 추가 입력
4. 인증 성공 시 `.telegram_session` 파일 생성 → 이후 자동 로그인

> `.telegram_session` 파일을 삭제하면 재인증이 필요합니다.

---

## 5. cron 자동 실행 등록

매일 평일 오전 8시에 자동으로 브리핑을 생성하고 파일로 저장:

```bash
# crontab 편집
crontab -e
```

아래 줄 추가 (`/path/to/telegram_briefing`을 실제 경로로 변경):

```cron
0 8 * * 1-5 cd /path/to/telegram_briefing && python main.py --output file >> briefing.log 2>&1
```

| 필드 | 값 | 의미 |
|---|---|---|
| 분 | `0` | 0분 |
| 시 | `8` | 오전 8시 |
| 일 | `*` | 매일 |
| 월 | `*` | 매월 |
| 요일 | `1-5` | 월~금 |

파일 출력 시 `briefing_YYYYMMDD.txt` 형식으로 저장됩니다.

---

## 6. CLI 옵션

```
python main.py [옵션]

옵션:
  --date YYYY-MM-DD       특정 날짜 브리핑 (기본값: 오늘)
  --channels @ch1 @ch2    채널 직접 지정 (config.yaml 대신)
  --output terminal|file  출력 방식 (기본값: terminal)
  --config PATH           설정 파일 경로 (기본값: config.yaml)
```

**사용 예시:**

```bash
# 오늘 브리핑 터미널 출력
python main.py

# 특정 날짜 브리핑
python main.py --date 2025-05-18

# 파일로 저장
python main.py --output file

# 채널 직접 지정
python main.py --channels @stockchannel1 @stockchannel2
```

---

## 브리핑 구성

| 섹션 | 내용 |
|---|---|
| ① 핵심 테마/섹터 동향 | 새벽 주목받은 섹터 흐름 2~3개 |
| ② 언급 급증 종목 | 종목명(코드) + 맥락 + 긍부정 |
| ③ 매크로/글로벌 이슈 | 환율, 미국시장, 원자재 |
| ④ 증권사/기관 리포트 | 목표가 변경, 업종 리포트 |
| ⑤ 주의 신호 | 과열 징후, 루머, 뇌동 유발 글 |

---

> ⚠️ 이 브리핑은 투자 참고용이며 독립적 판단이 필요함
