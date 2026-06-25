"""Forward ingest hook — REAL first-seen ``knowable_at`` for fundamentals, going forward.

``fundamentals_history`` stores a MODELED ``report_date = period_end + 90d/50d`` — the only
"PIT" date back-history has. This wrapper captures the **real** date a period first appears
in our scrape: the first time WE can prove the number existed. For data ingested from now on,
that first-seen timestamp ``S`` is a REAL (non-modeled) upper bound on the true filing date
``F`` (``F ≤ S``) — equivalently, the earliest date a no-look-ahead backtest may use the datum.
Gating on ``S`` can never inject look-ahead (the modeled ``period_end+lag`` can, for late
filers). With a regular scrape cadence ``S ≈ F + cadence`` → a TIGHT real bound.

Complement, not replacement, of ``fundamentals_filing_dates.py``: the BSE backfill de-models
HISTORY (real exchange dates since 2006); this de-models the FUTURE (real first-seen from
switch-on). Together they cover the whole archive going both directions.

Isolation (house pattern): a NEW module that WRAPS ``fundamentals_history.collect()`` with
ZERO edits to it. The scheduler calls ``collect_with_provenance`` instead of ``collect``.

Two correctness points baked in:
  * **Cross-DB.** ``collect()`` writes ``fundamentals_history`` in research.db (its ``con``),
    but ``provenance_knowable`` is read by ``provenance_for``/``lag_audit`` from the MAIN db.
    So we ``observe()`` on the hermes connection (``hermes_con`` / default ``get_conn()``),
    NEVER on the research ``con``.
  * **Recency gate = the honesty guard.** A period is stamped ``knowable=now`` only if its
    ``period_end`` is within ``recency_gate_days`` of today. On a symbol's INITIAL backfill
    every deep-history period looks "new"; stamping a 2015 period with a 2026 ``now`` is a
    misleading upper bound (the red-team's forward-only principle). The gate keeps only the
    just-filed period(s) and leaves deep history honestly MODELED — the BSE backfill is what
    reaches back for it.

Pure stdlib + the project's provenance API; NO LLM, NO network of its own (the wrapped
collector does the scraping). Defensive + offline ``--selftest`` (dependency-injected
collector + in-memory DBs, no network / no research.db).

CLI:
    python -m src.automation.fundamentals_provenance --selftest     # offline, synthetic
    python -m src.automation.fundamentals_provenance --run          # universe pass (VPS: research.db)
    python -m src.automation.fundamentals_provenance --run --limit 50
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import time
from datetime import date
from typing import Callable, Optional

from src.automation import provenance

log = logging.getLogger("hermes.fund_provenance")

DATA_CLASS = "fundamentals_history"
DEFAULT_RECENCY_GATE_DAYS = 150       # ~one quarter's filing window + scrape-cadence slack
SOURCE_NOTE = "screener-first-seen"


def _periods(con, symbol: str) -> set:
    """The (period_type, period_end) set stored for ``symbol`` (empty/None-safe)."""
    if con is None:
        return set()
    try:
        return {(r[0], r[1]) for r in con.execute(
            "SELECT DISTINCT period_type, period_end FROM fundamentals_history WHERE symbol=?", (symbol,))}
    except sqlite3.Error:
        return set()


def collect_with_provenance(symbol: str, research_con, *, hermes_con=None,
                            collect_fn: Optional[Callable] = None,
                            recency_gate_days: int = DEFAULT_RECENCY_GATE_DAYS,
                            today: Optional[date] = None,
                            knowable_at: Optional[str] = None) -> dict:
    """Scrape ``symbol`` (via the wrapped collector) AND capture real first-seen for any
    genuinely-new, recent period. Returns a stats dict; never raises on the provenance side.

    ``collect_fn`` defaults to ``fundamentals_history.collect`` (injectable for offline tests).
    ``hermes_con`` is the MAIN-db connection for ``observe()`` (defaults to ``get_conn()``).
    ``knowable_at`` defaults to now (the scrape clock); override only for tests/backfill-from-log."""
    symbol = symbol.upper().strip()
    today = today or date.today()
    if collect_fn is None:
        from src.automation import fundamentals_history
        collect_fn = fundamentals_history.collect

    before = _periods(research_con, symbol)
    n_rows = collect_fn(symbol, research_con)          # the unchanged collector: scrape + upsert + commit
    after = _periods(research_con, symbol)

    fresh = []
    for (pt, pe) in (after - before):
        try:
            gap = (today - date.fromisoformat(pe)).days
        except (ValueError, TypeError):
            continue
        if 0 <= gap <= recency_gate_days:             # genuinely-new AND recent → real tight bound
            fresh.append((pt, pe))

    captured = 0
    if fresh:
        keys = [(provenance.period_key(symbol, pt, pe), symbol) for pt, pe in fresh]
        # one shared knowable_at (this scrape's clock) across the batch; INSERT-OR-IGNORE keeps earliest.
        captured = provenance.observe_batch(DATA_CLASS, keys, conn=hermes_con,
                                            knowable_at=knowable_at, source_note=SOURCE_NOTE)
    return {"symbol": symbol, "rows": n_rows, "new_periods": len(after - before),
            "fresh_recent": len(fresh), "captured": captured}


def collect_universe_with_provenance(symbols, *, delay: float = 2.5,
                                     recency_gate_days: int = DEFAULT_RECENCY_GATE_DAYS) -> dict:
    """Scheduler entry point: the ``collect_universe`` loop with the provenance hook (VPS path).
    Opens research.db (the collector's store) + a MAIN-db conn for observe(). Resumes via the
    collector's own ``fundamentals_done``. Degrades to a no-op if research.db is absent."""
    from src.automation import fundamentals_history
    import os
    if not os.path.exists(fundamentals_history.RESEARCH_DB):
        log.warning("research.db absent (%s) — nothing to ingest here.", fundamentals_history.RESEARCH_DB)
        return {"status": "research_db_absent"}

    rcon = sqlite3.connect(fundamentals_history.RESEARCH_DB, timeout=60)
    fundamentals_history._init(rcon)
    done = {r[0] for r in rcon.execute("SELECT symbol FROM fundamentals_done")}
    todo = [s for s in symbols if s not in done]
    totals = {"symbols": 0, "rows": 0, "captured": 0}
    with provenance.get_conn() as hcon:
        provenance.ensure_schema(hcon)
        for i, s in enumerate(todo, 1):
            st = collect_with_provenance(s, rcon, hermes_con=hcon, recency_gate_days=recency_gate_days)
            totals["symbols"] += 1
            totals["rows"] += max(0, st["rows"])
            totals["captured"] += st["captured"]
            hcon.commit()
            if i % 25 == 0:
                log.info("ingest %d/%d: %s", i, len(todo), totals)
            time.sleep(delay)
    rcon.close()
    return totals


# ── offline selftest (no network, no research.db) ─────────────────────────────
def _selftest() -> None:
    # research.db stand-in (the collector's store) + main-db stand-in (provenance_knowable)
    rcon = sqlite3.connect(":memory:")
    rcon.execute("""CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, period_end TEXT,
        report_date TEXT, metric TEXT, value REAL,
        PRIMARY KEY(symbol,period_type,period_end,metric))""")
    hcon = sqlite3.connect(":memory:")
    hcon.row_factory = sqlite3.Row
    provenance.ensure_schema(hcon)

    def fake_collect(rows):
        """Build a collect_fn that 'scrapes' the given (pt, pe) periods into rcon."""
        def _c(symbol, con):
            payload = [(symbol, pt, pe, pe, "Sales", 100.0) for pt, pe in rows]
            con.executemany("INSERT OR REPLACE INTO fundamentals_history VALUES (?,?,?,?,?,?)", payload)
            con.commit()
            return len(payload)
        return _c

    # 1. INITIAL backfill at 2024-08-15: deep history (A 2015) must be REJECTED by the gate;
    #    only the just-filed Q (2024-06-30, gap ~46d) is captured. (A 2024-03-31 ~137d also in-gate.)
    st = collect_with_provenance(
        "RELIANCE", rcon, hermes_con=hcon,
        collect_fn=fake_collect([("A", "2015-03-31"), ("A", "2024-03-31"), ("Q", "2024-06-30")]),
        today=date(2024, 8, 15), knowable_at="2024-08-15")
    assert st["new_periods"] == 3 and st["fresh_recent"] == 2 and st["captured"] == 2, st
    got = {r[0] for r in hcon.execute("SELECT key FROM provenance_knowable")}
    assert provenance.period_key("RELIANCE", "Q", "2024-06-30") in got
    assert provenance.period_key("RELIANCE", "A", "2024-03-31") in got
    assert provenance.period_key("RELIANCE", "A", "2015-03-31") not in got, "deep history must stay MODELED"

    # 2. INCREMENTAL: a NEW quarter appears; only it is captured (prior periods are in `before`).
    st2 = collect_with_provenance(
        "RELIANCE", rcon, hermes_con=hcon,
        collect_fn=fake_collect([("A", "2015-03-31"), ("A", "2024-03-31"),
                                 ("Q", "2024-06-30"), ("Q", "2024-09-30")]),
        today=date(2024, 11, 5), knowable_at="2024-11-05")
    assert st2["new_periods"] == 1 and st2["captured"] == 1, st2
    assert provenance.period_key("RELIANCE", "Q", "2024-09-30") in \
        {r[0] for r in hcon.execute("SELECT key FROM provenance_knowable")}

    # 3. IDEMPOTENT: re-seeing Q1 keeps the EARLIEST knowable_at (2024-08-15), not a later one.
    assert collect_with_provenance(
        "RELIANCE", rcon, hermes_con=hcon,
        collect_fn=fake_collect([("Q", "2024-06-30")]),
        today=date(2025, 1, 1), knowable_at="2025-01-01")["captured"] == 0
    assert provenance._scalar(hcon, "SELECT knowable_at FROM provenance_knowable WHERE key=?",
                              (provenance.period_key("RELIANCE", "Q", "2024-06-30"),)) == "2024-08-15"

    # 4. provenance_for() flips MODELED → real (ptype-keyed, no annual/quarterly collision)
    pq = provenance.provenance_for(DATA_CLASS, symbol="RELIANCE", period_type="Q",
                                   as_of="2024-06-30", conn=hcon)
    assert pq["basis"] == provenance.INGESTED and pq["as_of"] == "2024-08-15", pq

    print("fund_provenance selftest: OK  (recency gate rejects deep history; incremental + idempotent; "
          "cross-DB observe on main; ptype-keyed round-trip)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Forward ingest hook: real first-seen knowable_at for fundamentals.")
    ap.add_argument("--selftest", action="store_true", help="offline synthetic validation (no network / research.db)")
    ap.add_argument("--run", action="store_true", help="universe ingest pass with the provenance hook (VPS)")
    ap.add_argument("--limit", type=int, help="cap symbols for --run")
    ap.add_argument("--gate-days", type=int, default=DEFAULT_RECENCY_GATE_DAYS, help="recency gate (days)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.selftest:
        _selftest(); return
    if args.run:
        import os
        from src.automation import fundamentals_history
        mc = sqlite3.connect(f"file:{fundamentals_history.RESEARCH_DB.replace('research.db','hermes.db')}?mode=ro", uri=True) \
            if os.path.exists(fundamentals_history.RESEARCH_DB) else None
        # universe = the liquid EQ set the collector uses; reuse its own selection if available
        try:
            from src.core.db import get_conn
            with get_conn() as c:
                syms = [r[0] for r in c.execute(
                    "SELECT DISTINCT symbol FROM bhavcopy_rows WHERE series='EQ' AND trade_date>='2025-01-01'")]
        except Exception as e:  # noqa: BLE001
            log.warning("universe query failed (%s) — pass symbols explicitly on the VPS.", e)
            syms = []
        if mc:
            mc.close()
        print(collect_universe_with_provenance(sorted(syms)[: args.limit] if args.limit else sorted(syms),
                                               recency_gate_days=args.gate_days))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
