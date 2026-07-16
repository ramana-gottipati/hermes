"""Bounded, prioritized batch pt14 scoring (B6 / Decision D46).

Lights up the QUALITY pillar (pattern_scores / fundamentals) for the names the
system actually SURFACES — the Conviction shortlist, RS leaders, the watchlist,
and recent news-driven screen_candidates — so /dash/conviction, the stock page's
pt14 card, and the Strategies-hub quality count stop showing "unscored".

🔴 NO NETWORK, NO SCREENER (S148 / Guardrail #8). This used to scrape Screener for
each stale symbol; since 3.4 it scores entirely from the PRIMARY-SOURCE archive via
`scoring.score_symbol` → `fundamentals_asof` (research.db.fundamentals_history —
NSE-XBRL where migrated, labeled Screener-era legacy before ~2022 — plus
shareholding_history, and the bhav copy for the PE/PB price). The scrape budget,
the polite throttle and the 7-day scrape cache are all GONE with the network call.

Still HONORS D8 ("build fundamentals over time, not bulk"):
  - PRIORITIZED — only the surfaced universe (a few hundred names at most), not
    the whole ~2,400-symbol equity list.
  - INCREMENTAL — skips names already scored within the TTL; each run does only
    the outstanding work.
  - BOUNDED — at most `limit` symbols scored per run (now a pure runtime bound).

No LLM, no HTTP — the scorer is rule-based Python over local SQLite. ₹0 marginal.

Usage:
    python -m src.automation.score_batch                 # default: <=40 symbols
    python -m src.automation.score_batch --limit 60      # raise the per-run cap
    python -m src.automation.score_batch --dry-run       # print the plan, do nothing
"""

import argparse
import logging
from datetime import datetime, timedelta

from src.automation import scoring
from src.core.db import get_conn

log = logging.getLogger("hermes.score_batch")

_DEFAULT_LIMIT = 40       # max symbols scored per run (runtime bound — no network any more)
_DEFAULT_TTL_DAYS = 7     # re-score window (was screener.SCREENER_CACHE_DAYS)
_MAX_TARGETS = 300        # hard ceiling on the prioritized set (D8 guardrail)


def _prioritized_symbols(max_total: int = _MAX_TARGETS) -> list[str]:
    """The surfaced universe whose QUALITY actually matters, in priority order:
    watchlist → recent news-driven candidates → Conviction shortlist → RS
    leaders. Deduped, capped. (Deliberately NOT the full equity list — D8.)"""
    syms: list[str] = []
    seen: set[str] = set()

    def add(s) -> None:
        s = (s or "").upper().strip()
        if s and s not in seen:
            seen.add(s)
            syms.append(s)

    with get_conn() as conn:
        for r in conn.execute("SELECT symbol FROM watchlist ORDER BY symbol"):
            add(r["symbol"])
        for r in conn.execute(
            "SELECT DISTINCT symbol FROM screen_candidates "
            "ORDER BY screened_at DESC LIMIT 100"
        ):
            add(r["symbol"])

    # The RS/Positioning-surfaced names (the ones the Quality pillar should
    # confirm). Imported lazily to avoid any import cycle.
    try:
        from src.automation.stock_rs import conviction_shortlist, leaders_laggards
        for r in conviction_shortlist(limit=60):
            add(r["symbol"])
        for r in leaders_laggards("leaders", limit=120):
            add(r["symbol"])
    except Exception as e:  # pragma: no cover - defensive
        log.warning("could not load RS-surfaced symbols: %s", e)

    return syms[:max_total]


def _recently_scored(conn, symbol: str, ttl_days: int) -> bool:
    """True if there's a pattern_scores row for the symbol within the TTL — i.e.
    the Quality pillar is already lit for it, so this run can skip it."""
    row = conn.execute(
        "SELECT scored_at FROM pattern_scores WHERE symbol = ? "
        "ORDER BY scored_at DESC LIMIT 1", (symbol,)
    ).fetchone()
    if not row or not row["scored_at"]:
        return False
    try:
        scored = datetime.fromisoformat(str(row["scored_at"]).replace(" ", "T"))
    except ValueError:
        return False
    return (datetime.utcnow() - scored) <= timedelta(days=ttl_days)


def run_batch(limit: int = _DEFAULT_LIMIT, ttl_days: int | None = None,
              dry_run: bool = False) -> dict:
    """Score the outstanding surfaced names from the archive (no network). Summary dict."""
    ttl_days = ttl_days if ttl_days is not None else _DEFAULT_TTL_DAYS
    symbols = _prioritized_symbols()

    with get_conn() as conn:
        todo = [s for s in symbols if not _recently_scored(conn, s, ttl_days)]

    log.info("batch: %d surfaced · %d already scored (skip) · %d outstanding "
             "(archive-only, no network; cap %d this run)",
             len(symbols), len(symbols) - len(todo), len(todo), limit)

    if dry_run:
        return {"surfaced": len(symbols), "outstanding": len(todo),
                "scored": 0, "dry_run": True}

    scored = failed = 0
    for sym in todo[:limit]:
        try:
            score = scoring.score_symbol(sym)
        except Exception as e:  # noqa: BLE001 — one bad symbol must not abort the batch
            log.warning("batch score failed for %s: %s", sym, e)
            score = {"error": str(e)}
        if score.get("error"):
            failed += 1
        else:
            scored += 1

    log.info("batch complete: %d scored, %d failed (archive-only, zero Screener hits)",
             scored, failed)
    return {"surfaced": len(symbols), "outstanding": len(todo),
            "scored": scored, "failed": failed, "dry_run": False}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=_DEFAULT_LIMIT,
                   help=f"max symbols scored this run (default {_DEFAULT_LIMIT})")
    p.add_argument("--throttle", type=float, default=0.0,
                   help="DEPRECATED no-op (kept for call-site compat; the scrape is gone)")
    p.add_argument("--ttl-days", type=int, default=None,
                   help=f"re-score window in days (default {_DEFAULT_TTL_DAYS})")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan (counts) without scoring")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    summary = run_batch(limit=args.limit, ttl_days=args.ttl_days, dry_run=args.dry_run)
    log.info("summary: %s", summary)


if __name__ == "__main__":
    main()
