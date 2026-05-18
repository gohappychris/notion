import re
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich import box

console = Console()

SECTION_STYLES = {
    "① 핵심 테마/섹터 동향": ("bold cyan", "cyan"),
    "② 언급 급증 종목": ("bold green", "green"),
    "③ 매크로/글로벌 이슈": ("bold yellow", "yellow"),
    "④ 증권사/기관 리포트": ("bold blue", "blue"),
    "⑤ 주의 신호": ("bold red", "red"),
}

SECTION_HEADERS = list(SECTION_STYLES.keys())


def _parse_sections(briefing_text: str) -> dict[str, str]:
    """Split briefing text into {section_header: content} dict."""
    sections: dict[str, str] = {}
    pattern = re.compile(
        r"([①②③④⑤][^\n]+)",
    )
    parts = pattern.split(briefing_text)

    current_header = None
    for part in parts:
        stripped = part.strip()
        if pattern.fullmatch(stripped):
            # Match against known section headers (fuzzy: startswith circled number)
            for known in SECTION_HEADERS:
                if stripped.startswith(known[0]):  # match on circled number
                    current_header = known
                    sections[current_header] = ""
                    break
        elif current_header is not None:
            sections[current_header] = stripped

    return sections


def print_briefing(
    briefing_text: str,
    date_str: str,
    channel_count: int,
    message_count: int,
) -> None:
    """Render the full briefing to the terminal using Rich."""
    # Header
    console.print()
    console.rule(
        Text(f"  한국 주식 새벽 브리핑  {date_str}  ", style="bold white on dark_blue"),
        style="dark_blue",
    )
    console.print(
        f"  분석 채널: [bold]{channel_count}개[/bold]  |  총 메시지: [bold]{message_count}개[/bold]",
        style="dim",
        justify="center",
    )
    console.print()

    sections = _parse_sections(briefing_text)

    for header in SECTION_HEADERS:
        title_style, border_style = SECTION_STYLES[header]
        content = sections.get(header, "해당 내용 없음")
        if not content:
            content = "해당 내용 없음"

        console.print(
            Panel(
                content,
                title=f"[{title_style}]{header}[/{title_style}]",
                border_style=border_style,
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        console.print()

    # Footer
    console.rule(style="dim")
    console.print(
        "⚠️  이 브리핑은 투자 참고용이며 독립적 판단이 필요함",
        style="bold yellow",
        justify="center",
    )
    console.print()


def briefing_to_text(
    briefing_text: str,
    date_str: str,
    channel_count: int,
    message_count: int,
) -> str:
    """Return plain-text version for file output."""
    lines = [
        "=" * 60,
        f"한국 주식 새벽 브리핑 — {date_str}",
        f"분석 채널: {channel_count}개  |  총 메시지: {message_count}개",
        "=" * 60,
        "",
        briefing_text,
        "",
        "-" * 60,
        "⚠️  이 브리핑은 투자 참고용이며 독립적 판단이 필요함",
    ]
    return "\n".join(lines)
