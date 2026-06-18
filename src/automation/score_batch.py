"""Bounded, prioritized batch pt14 scoring (B6 / Decision D46).

Lights up the QUALITY pillar (pattern_scores / fundamentals) for the names the
system actually SURFACES — the Conviction shortlist, RS leaders, the watchlist,
and recent news-driven screen_candidates — so /dash/conviction, the stock page's
pt14 card, and the Strategies-hub quality count stop showing "unscored".

⚠ HONORS D8 ("build fundamentals over time, not bulk — don't pre-scrape Screener
for 5,000 stocks"). This is NOT a bulk scraper:
  - PRIORITIZED — only the surfaced universe (a few hundred names at most), not
    the whole ~2,400-symbol equity list.
  - INCREMENTAL — skips names already scored within the TTL; each run only does
    the work still outstanding, so coverage grows over days and then just
    refreshes on the 7-day cache. "Natural incremental growth" (D8's words).
  - BOUNDED — at most `limit` real Screener scrapes per run (the network-expensive
    part); the rest wait for the next run.
  - THROTTLED — a polite sleep after every real scrape (anti-rate-limit).
A symbol with fresh cached fundamentals is re-scored locally (no network).

No LLM — the scorer is pure rule-based Python (scoring.score_fundamentals) and
the fetch is HTML parsing (screener). ₹0 marginal.

Usage:
    python -m src.automation.score_batch                 # default: <=40 scrapes
    python -m src.automation.score_batch --limit 60      # raise the scrape cap
    python -m src.automation.score_batch --throttle 3.0  # seconds between scrapes
    python -m src.automation.score_batch --dry-run       # print the plan, do nothing
"""

import argparse
import logging
import time
from datetime import datetime, timedelta

from src.automation import scoring, screener
from src.core.db import get_conn

log = logging.getLogger("hermes.score_batch")

_DEFAULT_LIMIT = 40       # max real Screener scrapes per run
_DEFAULT_THROTTLE = 2.5   # seconds to sleep after each real scrape
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


def _is_fundamentals_fresh(conn, symbol: str, ttl_days: int) -> bool:
    """True if cached fundamentals exist and are within the TTL (so scoring this
    symbol needs NO network). Mirrors screener._read_cache's freshness check."""
    row = conn.execute(
        "SELECT fetched_at FROM fundamentals WHERE symbol = ?", (symbol,)
    ).fetchone()
    if not row or not row["fetched_at"]:
        return False
    try:
        fetched = datetime.fromisoformat(str(row["fetched_at"]).replace(" ", "T"))
    except ValueError:
        return False
    return (datetime.utcnow() - fetched) <= timedelta(days=ttl_days)


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


def run_batch(limit: int = _DEFAULT_LIMIT, throttle: float = _DEFAULT_THROTTLE,
              ttl_days: int | None = None, dry_run: bool = False) -> dict:
    """Score the outstanding surfaced names. Returns a summary dict."""
    ttl_days = ttl_days if ttl_days is not None else screener.SCREENER_CACHE_DAYS
    symbols = _prioritized_symbols()

    with get_conn() as conn:
        todo = [s for s in symbols if not _recently_scored(conn, s, ttl_days)]
        fresh = {s: _is_fundamentals_fresh(conn, s, ttl_days) for s in todo}

    n_fresh = sum(1 for s in todo if fresh[s])
    n_stale = len(todo) - n_fresh
    log.info("batch: %d surfaced · %d already scored (skip) · %d outstanding "
             "(%d cached/no-network, %d need scrape; cap %d this run)",
             len(symbols), len(symbols) - len(todo), len(todo), n_fresh, n_stale, limit)

    if dry_run:
        return {"surfaced": len(symbols), "outstanding": len(todo),
                "cached": n_fresh, "need_scrape": n_stale, "scraped": 0,
                "scored": 0, "dry_run": True}

    scraped = scored = failed = 0
    for sym in todo:
        if not fresh[sym] and scraped >= limit:
            break  # scrape budget spent — remaining stale names wait for next run
        try:
            score = scoring.score_symbol(sym, force_refresh=not fresh[sym])
        except Exception as e:
            log.warning("batch score failed for %s: %s", sym, e)
            score = {"error": str(e)}
        if not fresh[sym]:
            scraped += 1
            time.sleep(throttle)  # polite gap after a real Screener hit
        if score.get("error"):
            failed += 1
        else:
            scored += 1

    log.info("batch complete: %d scored (%d scraped, %d cached-rescored, %d failed)",
             scored, scraped, scored - max(0, scraped - failed), failed)
    return {"surfaced": len(symbols), "outstanding": len(todo),
            "cached": n_fresh, "need_scrape": n_stale,
            "scraped": scraped, "scored": scored, "failed": failed, "dry_run": False}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=_DEFAULT_LIMIT,
                   help=f"max real Screener scrapes this run (default {_DEFAULT_LIMIT})")
    p.add_argument("--throttle", type=float, default=_DEFAULT_THROTTLE,
                   help=f"seconds to sleep after each scrape (default {_DEFAULT_THROTTLE})")
    p.add_argument("--ttl-days", type=int, default=None,
                   help="freshness window; default = screener.SCREENER_CACHE_DAYS (7)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan (counts) without scraping or scoring")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    summary = run_batch(limit=args.limit, throttle=args.throttle,
                        ttl_days=args.ttl_days, dry_run=args.dry_run)
    log.info("summary: %s", summary)


if __name__ == "__main__":
    main()
