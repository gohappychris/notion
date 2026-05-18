import anthropic

SYSTEM_PROMPT = (
    "당신은 한국 주식 투자 리서치 전문가입니다. "
    "텔레그램 주식 채널들의 메시지를 분석하여 투자에 실질적으로 도움이 되는 브리핑을 생성합니다. "
    "모든 응답은 한국어로 작성하며, ~임/~함 종결어미 스타일을 사용합니다. "
    "존재하지 않는 내용을 지어내지 않으며, 해당 섹션에 내용이 없으면 '해당 내용 없음'으로 표기합니다."
)

SUMMARY_SECTIONS = [
    "① 핵심 테마/섹터 동향",
    "② 언급 급증 종목",
    "③ 매크로/글로벌 이슈",
    "④ 증권사/기관 리포트",
    "⑤ 주의 신호",
]

# Priority weight for truncation: high > medium > low
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
# Approximate chars per token (conservative estimate for Korean text)
CHARS_PER_TOKEN = 2
MAX_INPUT_CHARS = 100_000 * CHARS_PER_TOKEN  # ~100k tokens


def _build_message_block(msg: dict) -> str:
    kst_time = msg["timestamp"][11:16]  # HH:MM
    views = f" [조회 {msg['views']}]" if msg["views"] else ""
    return f"[{msg['channel_name']} {kst_time}{views}]\n{msg['text']}"


def _truncate_to_limit(messages: list[dict]) -> list[dict]:
    """Remove low-priority messages first until total chars fit within limit."""
    sorted_msgs = sorted(messages, key=lambda m: (PRIORITY_ORDER.get(m["priority"], 1), m["timestamp"]))

    total_chars = sum(len(m["text"]) for m in sorted_msgs)
    if total_chars <= MAX_INPUT_CHARS:
        return sorted_msgs

    kept: list[dict] = []
    running = 0
    for msg in sorted_msgs:
        chunk = len(msg["text"])
        if running + chunk > MAX_INPUT_CHARS:
            continue
        kept.append(msg)
        running += chunk

    # Re-sort by timestamp for coherent reading
    kept.sort(key=lambda m: m["timestamp"])
    return kept


def _build_user_prompt(messages: list[dict], date_str: str) -> str:
    truncated = _truncate_to_limit(messages)
    blocks = [_build_message_block(m) for m in truncated]
    joined = "\n\n".join(blocks)

    channel_stats = {}
    for m in truncated:
        channel_stats[m["channel_name"]] = channel_stats.get(m["channel_name"], 0) + 1
    stats_lines = "\n".join(f"  - {name}: {cnt}개" for name, cnt in sorted(channel_stats.items()))

    return f"""분석 날짜: {date_str}
총 메시지 수: {len(truncated)}개

채널별 메시지 수:
{stats_lines}

=== 메시지 원문 ===
{joined}

=== 브리핑 요청 ===
위 텔레그램 채널 메시지들을 분석하여 아래 5개 섹션으로 구성된 한국 주식 투자 브리핑을 작성해주세요.
각 섹션은 헤더(예: ① 핵심 테마/섹터 동향)로 시작하고, 내용이 없으면 "해당 내용 없음"으로 표기하세요.
~임/~함 종결어미 스타일을 사용하며, 실제 메시지에 근거한 내용만 작성하세요.

① 핵심 테마/섹터 동향
오늘 새벽 주목받은 섹터 흐름 2~3개를 요약

② 언급 급증 종목
종목명(코드) + 언급 맥락 + 긍정/부정 여부 포함

③ 매크로/글로벌 이슈
환율, 미국시장, 원자재 등 언급된 내용

④ 증권사/기관 리포트
목표가 변경, 업종 리포트 언급 요약

⑤ 주의 신호
과열 징후, 루머성 글, 뇌동 유발 가능성 있는 내용"""


def summarize(
    messages: list[dict],
    date_str: str,
    api_key: str,
    max_tokens: int = 2000,
) -> str:
    """Call Claude once with all messages and return the 5-section briefing text."""
    if not messages:
        return "\n\n".join(
            f"{section}\n해당 내용 없음" for section in SUMMARY_SECTIONS
        )

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_user_prompt(messages, date_str)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text
