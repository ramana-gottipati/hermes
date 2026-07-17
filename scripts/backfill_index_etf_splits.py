"""Heal the three 2026-06/07 INDEX-ETF unit subdivisions the S184 `chk_split_cliffs`
nightly guard caught on its first live run (the 16AQ class recurring beyond gold).

Each event was verified on the raw tape before entering this seed (S184, ledger 16AT):
a one-day close drop to the ~10:1 level that PERSISTS with genuine traded value on both
sides, and ZERO corporate_actions rows for the symbol ever:

    HEALTHADD  2026-07-03  162.94 -> 16.72   (10:1)
    MIDQ50ADD  2026-07-03  247.99 -> 24.76   (10:1)
    PSUBANK    2026-07-10  822.75 -> 85.31   (10:1; a +3.7% sector day at the new level)

Deliberately a SIBLING of `scripts/backfill_etf_splits.py` (S182, gold-scoped by name and
frozen selftest): this script reuses that module's FROZEN `_details()` idempotency text,
`SOURCE_TAG`, and the canonical `store_actions` write path by importing it by path — so the
two seeds stay separately owned while every inserted row is shape-identical. The FULL
remediation of the ~184-event full-history orphan-cliff backlog (old-equity splits predating
CA coverage + the rest of the ETF class) is a separate task — do NOT bulk-insert unverified
ratios here; a wrong ratio corrupts worse than a missing one.

Usage (box, app venv, repo root):
    python scripts/backfill_index_etf_splits.py            # dry-run (default)
    python scripts/backfill_index_etf_splits.py --apply    # idempotent insert
"""
from __future__ import annotations

import importlib.util
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

INDEX_ETF_SPLITS = [
    ("HEALTHADD", "2026-07-03", 10, 1),
    ("MIDQ50ADD", "2026-07-03", 10, 1),
    ("PSUBANK",   "2026-07-10", 10, 1),
]


def _load_gold_module():
    path = os.path.join(REPO_ROOT, "scripts", "backfill_etf_splits.py")
    spec = importlib.util.spec_from_file_location("backfill_etf_splits", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_rows(gold) -> list[dict]:
    return [{
        "symbol": sym, "action_type": "SPLIT", "ex_date": ex,
        "record_date": None, "ratio_from": float(rf), "ratio_to": float(rt),
        "details": gold._details(rf, rt), "source": gold.SOURCE_TAG,
    } for sym, ex, rf, rt in INDEX_ETF_SPLITS]


def main() -> int:
    gold = _load_gold_module()
    rows = build_rows(gold)
    apply = "--apply" in sys.argv
    from src.core.db import get_conn
    with get_conn() as conn:
        for r in rows:
            n = conn.execute(
                "SELECT COUNT(*) FROM corporate_actions WHERE symbol=? AND action_type='SPLIT' "
                "AND ex_date=?", (r["symbol"], r["ex_date"])).fetchone()[0]
            print(f"  {'PRESENT' if n else 'GAP':8} {r['symbol']:11} {r['ex_date']}  "
                  f"{int(r['ratio_from'])}:{int(r['ratio_to'])}")
        if not apply:
            print("dry-run only — pass --apply to insert")
            return 0
        from src.automation.corp_actions import store_actions
        before = conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
        inserted = store_actions(rows, conn=conn)
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
        print(f"inserted {inserted} row(s) (table {before} -> {after}); "
              f"{len(rows) - inserted} already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
