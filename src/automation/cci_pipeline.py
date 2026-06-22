"""CCI pipeline runner — the whole chain in the correct order, one command:

    ingest(optional) → results → extract(optional, bounded) → settle → diff → score

Honors the D59 contract by construction: settle + score ALWAYS follow extract, so a
`--extract` (even a --force re-extract) can never leave the score reading stale
settlement. FREE except the `--extract` step (Gemini, `--max-calls` guarded for the
20/day free tier). Designed for the weekly `hermes-concalls.timer` (P7).

CLI:
  python -m src.automation.cci_pipeline --pilot                     # results→settle→diff→score (free)
  python -m src.automation.cci_pipeline --symbol IDEA --ingest --extract --max-calls 18
  python -m src.automation.cci_pipeline --all                       # free chain over every ingested symbol
  python -m src.automation.cci_pipeline --targets --ingest --no-results   # P7: queue the names that matter
  python -m src.automation.cci_pipeline --all --extract --oldest --max-calls 18  # then drain oldest-first
"""

import argparse
import logging
from typing import Optional

from src.core.db import get_conn
from src.automation import (concalls, concall_results, concall_extract,
                            concall_settle, concall_diff, concall_scores)
from src.automation.concalls import PILOT

log = logging.getLogger("hermes.cci_pipeline")


def cci_targets(limit: int = 160) -> list:
    """The high-value ingest set the nightly drain should cover: the names Ramana
    actually watches/owns + the strategy-surfaced shortlists + the pilot floor —
    so coverage tracks attention, not just whatever was seeded. Order = priority:
    portfolio/tracker ∪ patearn watchlist ∪ conviction shortlist ∪ RS leaders
    (pillar-surfaced) ∪ PILOT/golden. Deduped (first-seen wins), capped. Every
    source is best-effort so a missing table/module never breaks the nightly job."""
    out, seen = [], set()

    def add(syms):
        for s in syms or []:
            s = (s or "").upper().strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)

    try:
        with get_conn() as conn:
            add([r["symbol"] for r in conn.execute(
                "SELECT DISTINCT symbol FROM stocks_in_play").fetchall()])           # portfolio + tracker
            add([r["symbol"] for r in conn.execute(
                "SELECT symbol FROM watchlist").fetchall()])                          # patearn watchlist
    except Exception:
        pass
    try:
        from src.automation.stock_rs import conviction_shortlist, leaders_laggards
        add([r["symbol"] for r in (conviction_shortlist(limit=60) or [])])           # cross-pillar conviction
        add([r["symbol"] for r in (leaders_laggards("leaders", limit=60) or [])])    # RS leaders (pillar-surfaced)
    except Exception:
        pass
    try:
        add(PILOT)                                                                   # golden floor
    except Exception:
        pass
    return out[:limit]


def _symbols(args) -> list:
    if args.symbol:
        return [args.symbol.upper()]
    if getattr(args, "targets", False):
        return cci_targets()
    if args.pilot:
        return PILOT
    with get_conn() as conn:
        return [r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concalls ORDER BY symbol").fetchall()]


def _bounded_extract(max_calls: int, oldest: bool = False) -> dict:
    rows = concall_extract.pending_rows(None, None, False, oldest=oldest)
    tot = {"DONE": 0, "FAIL": 0}
    made, consec_fail = 0, 0
    for row in rows:
        if max_calls and made >= max_calls:
            log.info("extract: hit --max-calls %d; stopping", max_calls)
            break
        r = concall_extract.extract_row(row)
        made += 1
        if r["status"] == "DONE":
            tot["DONE"] += 1
            consec_fail = 0
        else:
            tot["FAIL"] += 1
            if r["status"] in ("FAIL_failed", "FAIL"):
                consec_fail += 1
                if consec_fail >= 3:
                    log.warning("extract: 3 consecutive call failures (likely quota) — stopping")
                    break
    log.info("extract: %s (%d calls)", tot, made)
    return tot


def run(symbols, *, ingest=False, results=True, extract=False, max_calls=18,
        min_year=2019, limit=None, oldest=False) -> None:
    log.info("CCI pipeline over %d symbols (ingest=%s extract=%s)", len(symbols), ingest, extract)
    if ingest:
        for s in symbols:
            concalls.ingest_symbol(s, min_year=min_year, fetch_ai=False, limit=limit)
    if results:
        for s in symbols:
            concall_results.ingest_symbol(s, min_year=min_year)
    if extract:
        _bounded_extract(max_calls, oldest=oldest)
    # settle → diff (the D59 ordering); then score once over the whole set
    with get_conn() as conn:
        for s in symbols:
            concall_settle.settle_symbol(conn, s)
            concall_diff.diff_symbol(conn, s)
    concall_scores.run(rank_all=True)
    log.info("CCI pipeline done.")


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI pipeline runner (ingest→results→extract→settle→diff→score)")
    ap.add_argument("--symbol")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--targets", action="store_true",
                    help="operate over cci_targets() — portfolio ∪ watchlist ∪ conviction ∪ RS leaders ∪ pilot")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ingest", action="store_true", help="also fetch new concalls/transcripts first")
    ap.add_argument("--extract", action="store_true", help="also run the bounded Gemini extraction")
    ap.add_argument("--no-results", action="store_true", help="skip the Screener results refresh")
    ap.add_argument("--max-calls", type=int, default=18)
    ap.add_argument("--min-year", type=int, default=2019)
    ap.add_argument("--limit", type=int, help="per-symbol transcript download cap (with --ingest)")
    ap.add_argument("--oldest", action="store_true",
                    help="with --extract: drain OLDEST concalls first (backfill order)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not (args.symbol or args.pilot or args.all or args.targets):
        ap.error("give --symbol SYM, --pilot, --targets, or --all")
    run(_symbols(args), ingest=args.ingest, results=not args.no_results, extract=args.extract,
        max_calls=args.max_calls, min_year=args.min_year, limit=args.limit, oldest=args.oldest)


if __name__ == "__main__":
    main()
