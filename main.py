"""증권 통합 잔고 대시보드 - 실행 진입점.

Phase 0: 키움 잔고를 조회해 콘솔에 출력(파이프라인 검증).
  python main.py              # 보유종목/순자산 요약 출력
  python main.py --raw        # 키움 원본 JSON 출력(응답 필드명 검증용)
  python main.py --account 12345678  # 특정 계좌번호 지정

Phase 1 이후: --sink notion / --notify 옵션으로 적재·알림 추가 예정.
"""
from __future__ import annotations

import argparse
import json
import sys

from collectors.kiwoom import KiwoomClient, collect_kiwoom
from config import load_kiwoom_config


def cmd_raw(account_no: str) -> int:
    cfg = load_kiwoom_config()
    client = KiwoomClient(cfg)
    client.authenticate()
    print("=== 키움 국내 잔고 원본 응답 (필드명 검증용) ===")
    raw = client.fetch_domestic_balance_raw(account_no)
    print(json.dumps(raw["last"], ensure_ascii=False, indent=2))
    print(f"\n(합쳐진 보유종목 행 수: {len(raw['items'])})")
    return 0


def cmd_show(account_no: str) -> int:
    cfg = load_kiwoom_config()
    print(f"[키움/{cfg.env}] 잔고 조회 중...\n")
    holdings, summary = collect_kiwoom(cfg, account_no)

    if not holdings:
        print("보유종목이 없습니다(또는 응답 필드명 매핑 확인 필요 → --raw 로 점검).")
    else:
        print(f"{'종목명':<16}{'시장':<6}{'수량':>10}{'평가금액(원)':>16}{'수익률%':>10}")
        print("-" * 60)
        for h in sorted(holdings, key=lambda x: -x.eval_amount_krw):
            rate = f"{h.pnl_rate:+.2f}" if h.pnl_rate is not None else "-"
            print(
                f"{h.name[:14]:<16}{h.market:<6}{h.quantity:>10,.0f}"
                f"{h.eval_amount_krw:>16,.0f}{rate:>10}"
            )
        print("-" * 60)

    print(f"\n주식 총평가금액 : {summary.total_eval_krw:>16,.0f} 원")
    print(f"순자산(−미수/신용): {summary.net_asset_krw:>16,.0f} 원")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="증권 통합 잔고 대시보드")
    parser.add_argument("--raw", action="store_true", help="키움 원본 JSON 출력(필드 검증)")
    parser.add_argument("--account", default="", help="계좌번호(미지정 시 기본계좌)")
    args = parser.parse_args(argv)

    try:
        return cmd_raw(args.account) if args.raw else cmd_show(args.account)
    except RuntimeError as e:  # 키 미설정 등 사용자 입력 문제
        print(f"\n[설정 필요] {e}", file=sys.stderr)
        return 2
    except Exception as e:  # 네트워크/응답 오류
        print(f"\n[오류] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
