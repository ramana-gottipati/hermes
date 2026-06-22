"""CCI deterioration diff (FREE, deterministic) — the MEASURABLE avoid-tape feeder.

Diffs a symbol's consecutive concall periods' promise ledger and emits objective
deterioration red-flags:
  - guidance_walkback        a quantified target for a statement_type was LOWERED
  - promise_quietly_dropped  a prior quantified capex/expansion/revenue/margin promise
                             is not reaffirmed in the next call

These are FACTS (a diff of structured numbers), so they are allowed to drive the
rank (unlike the LLM 0-100 reads). Emitted into concall_redflags tagged
model_version='cci-diff-v1' and re-run-safe (its own rows are wiped first).

CLI: python -m src.automation.concall_diff --symbol IDEA | --all
"""

import argparse
import logging
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.concall_diff")

DIFF_VER = "cci-diff-v1"
# only diff HOMOGENEOUS, comparable statement types — never the heterogeneous 'other'
# bucket (mixing ₹-amounts with x-multiples produced garbage "12000000→3" walkbacks).
_COMPARABLE = ("revenue", "margin", "capex", "expansion", "volume", "debt_reduction", "cost_savings")
_DROP_TYPES = ("capex", "expansion", "revenue", "margin", "debt_reduction")   # promises whose disappearance matters


def _flag(conn, symbol, period, flag_type, severity, evidence, prior):
    conn.execute(
        "INSERT INTO concall_redflags (symbol, period_label, flag_type, severity, evidence, "
        "period_first_seen, prior_period, model_version) VALUES (?,?,?,?,?,?,?,?)",
        (symbol, period, flag_type, severity, evidence, period, prior, DIFF_VER))


def diff_symbol(conn, symbol: str) -> int:
    order = {r["period_label"]: (r["concall_year"] or 0, r["concall_month"] or 0)
             for r in conn.execute("SELECT period_label, concall_year, concall_month FROM concalls WHERE symbol=?", (symbol,)).fetchall()}
    periods = sorted({r["source_period"] for r in conn.execute(
        "SELECT DISTINCT source_period FROM concall_guidance WHERE symbol=?", (symbol,)).fetchall()},
        key=lambda p: order.get(p, (0, 0)))
    if len(periods) < 2:
        return 0
    conn.execute("DELETE FROM concall_redflags WHERE symbol=? AND model_version=?", (symbol, DIFF_VER))

    def by_type(period):
        d: dict[str, list] = {}
        for r in conn.execute(
            "SELECT statement_type, quantified_target FROM concall_guidance WHERE symbol=? AND source_period=?",
            (symbol, period)).fetchall():
            d.setdefault(r["statement_type"], []).append(r["quantified_target"])
        return d

    flags = 0
    for prev, cur in zip(periods, periods[1:]):
        pg, cg = by_type(prev), by_type(cur)
        for st, ptargets in pg.items():
            if st not in _COMPARABLE:        # skip 'other'/narrative buckets — not unit-comparable
                continue
            pmax = max([t for t in ptargets if t is not None], default=None)
            crows = cg.get(st)
            cmax = max([t for t in (crows or []) if t is not None], default=None)
            if pmax is not None and cmax is not None and cmax < pmax * 0.9:
                _flag(conn, symbol, cur, "guidance_walkback", 4,
                      f"{st} target lowered {pmax:g}→{cmax:g} ({prev}→{cur})", prev)
                flags += 1
            elif pmax is not None and not crows and st in _DROP_TYPES:
                _flag(conn, symbol, cur, "promise_quietly_dropped", 3,
                      f"{st} guidance from {prev} not reaffirmed in {cur}", prev)
                flags += 1
    if flags:
        log.info("%s: %d deterioration flags", symbol, flags)
    return flags


def run(symbol: Optional[str] = None) -> int:
    with get_conn() as conn:
        syms = [symbol.upper()] if symbol else [
            r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concall_guidance").fetchall()]
        return sum(diff_symbol(conn, s) for s in syms)


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI deterioration diff (free, deterministic)")
    ap.add_argument("--symbol")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not (args.symbol or args.all):
        ap.error("give --symbol SYM or --all")
    log.info("emitted %d deterioration flags", run(args.symbol if args.symbol else None))


if __name__ == "__main__":
    main()
