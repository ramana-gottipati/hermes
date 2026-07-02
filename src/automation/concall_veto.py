"""CCI forensic veto gate (debate rank #1) — the un-spinnable spine.

Credibility cannot be scored from the suspect's own testimony: a glib fraud runs
a smooth, confident, numeric call right up to collapse (Manpasand, Vakrangee,
DHFL, Yes Bank, Coffee Day...). So an EXOGENOUS integrity gate sits IN FRONT of
the credibility engine and can force tier=D regardless of how good the call
sounded. We do NOT build a new forensic platform — we WIRE the disqualifiers the
pt14 engine already computes (resources/patearn/SKILL.md) plus the directly-held
promoter pledge:

  - promoter pledge >= PLEDGE_VETO  -> UNIVERSAL hard veto (even for financials). Read from
                                        the PRIMARY source (NSE-XBRL-SHP → research.db
                                        shareholding_history, metric 'Promoter Pledge', latest
                                        quarter). The old hermes.db fundamentals.promoter_pledge
                                        is a STALE Screener-era snapshot (NULL/absent for most
                                        names — it silently let JPPOWER at ~73% pledged PASS
                                        this veto) kept only as a last-resort fallback when the
                                        SHP feed has nothing (guardrail #8: primary-source-first).
  - pt14 hard_disqualified           -> veto, EXCEPT cash-flow/leverage reasons are
                                        sector-SUPPRESSED for banks/NBFCs and heavy-
                                        capex cyclicals (negative CFO is structural
                                        there, not a fraud tell) — Ramana's A3 ruling.

SQL over hermes.db (`fundamentals`, `stock_signals`, `pattern_scores`) plus a read-only,
crash-proof cross-DB peek at research.db for the primary-source pledge. No LLM. Degrades
gracefully (never raises, never blocks the scorer) if research.db is absent or write-locked
— the D82c DB-lock hazard means the integrity gate can never crash the nightly scorer.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

PLEDGE_VETO = 20.0          # promoter pledge % at/above which the name is vetoed (universal)

# sectors where cash-flow / leverage disqualifiers are SUPPRESSED (structural, not fraud)
_FIN_SECTORS = ("bank", "financ", "nbfc", "housing finance", "insurance", "capital market", "broking")
_HEAVY_CAPEX = ("cement", "steel", "power", "metal", "infrastructure", "construction",
                "oil", "gas", "mining", "shipping", "telecom", "realty", "real estate")
_CASHFLOW_REASON = ("cfo", "cash flow", "cash-flow", "operating cash", "cfo/pat",
                    "negative cash", "debt", "leverage", "d/e", "working capital")


def _sector_suppresses_cashflow(sector: Optional[str]) -> bool:
    s = (sector or "").lower()
    return any(k in s for k in _FIN_SECTORS) or any(k in s for k in _HEAVY_CAPEX)


# --- primary-source promoter pledge (NSE-XBRL-SHP) --------------------------------
# The authentic pledge lives in research.db.shareholding_history (metric 'Promoter Pledge',
# source NSE-XBRL-SHP). hermes.db.fundamentals.promoter_pledge is a stale Screener-era
# snapshot (NULL for most names) — read here ONLY when the SHP feed has nothing.
_RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")


def _research_ro():
    """research.db opened READ-ONLY, or None if absent (laptop / fresh box). Never raises.
    Mirrors provenance._research_ro() / fundamentals_asof._hermes_ro()."""
    if not os.path.exists(_RESEARCH_DB):
        return None
    try:
        return sqlite3.connect(f"file:{_RESEARCH_DB}?mode=ro", uri=True, timeout=20)
    except sqlite3.Error:
        return None


def _shp_pledge(symbol: str, research_conn=None) -> Optional[float]:
    """Latest primary-source promoter-pledge % for ``symbol`` from the NSE-XBRL-SHP feed
    (research.db.shareholding_history, metric 'Promoter Pledge', newest period_end — stored
    as an ISO quarter-end, so ``ORDER BY period_end DESC`` is chronological).

    Returns None when research.db is absent/locked, the table/rows don't exist, or the value
    is null — the caller then falls back to the stale hermes.db column. NEVER raises: a read
    failure here must never crash or stall the veto/scorer (D82c DB-lock hazard). Pass a shared
    read-only ``research_conn`` in the batch path (else one is opened+closed per call)."""
    own = research_conn is None
    conn = research_conn or _research_ro()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT value FROM shareholding_history "
            "WHERE symbol=? AND metric='Promoter Pledge' AND value IS NOT NULL "
            "ORDER BY period_end DESC LIMIT 1", (symbol.upper().strip(),)
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None
    except (sqlite3.Error, TypeError, ValueError):
        return None
    finally:
        if own:
            try:
                conn.close()
            except sqlite3.Error:
                pass


def compute_veto(conn, symbol: str, sector: Optional[str] = None, *, research_conn=None) -> tuple[bool, Optional[str]]:
    """Return (veto_active, veto_reason) for a symbol from exogenous integrity signals.

    Sector (for the cash-flow suppression rule) is auto-resolved from
    stock_signals.primary_sector when not supplied — this reference to the
    price-derived table lives HERE (the integrity gate), never in the credibility
    scorer, so the scorer's price↔credibility firewall stays clean.

    ``research_conn`` is an optional shared read-only research.db handle for the pledge
    read (the batch path passes one so N symbols share a single open); when omitted a
    connection is opened+closed per call. Either way the pledge read degrades to None on
    any error, so the veto never crashes the scorer.
    """
    reasons: list[str] = []
    if sector is None:
        srow = conn.execute(
            "SELECT primary_sector FROM stock_signals WHERE symbol=? AND primary_sector IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 1", (symbol,)
        ).fetchone()
        sector = srow["primary_sector"] if srow else None

    # 1. Promoter pledge — the highest-precision, un-spinnable India signal (universal).
    #    PRIMARY source first: NSE-XBRL-SHP (research.db). The old hermes.db
    #    fundamentals.promoter_pledge is a STALE Screener snapshot (NULL/absent for most
    #    names — it silently let JPPOWER at ~73% pledged PASS this hard veto) and is used
    #    only when the SHP feed has nothing for the symbol (guardrail #8: primary-first).
    pledge = _shp_pledge(symbol, research_conn)
    if pledge is None:
        fu = conn.execute(
            "SELECT promoter_pledge FROM fundamentals WHERE symbol=?", (symbol,)
        ).fetchone()
        pledge = fu["promoter_pledge"] if fu else None
    if pledge is not None and pledge >= PLEDGE_VETO:
        reasons.append(f"promoter pledge {pledge:.0f}%")

    # 2. pt14's existing hard disqualifiers (auditor exit, CFO/PAT, RPT, ...).
    ps = conn.execute(
        "SELECT hard_disqualified, disqualifier_reasons FROM pattern_scores "
        "WHERE symbol=? ORDER BY scored_at DESC LIMIT 1", (symbol,)
    ).fetchone()
    if ps and ps["hard_disqualified"]:
        dr = (ps["disqualifier_reasons"] or "").strip()
        drl = dr.lower()
        is_cashflow = any(k in drl for k in _CASHFLOW_REASON)
        if is_cashflow and _sector_suppresses_cashflow(sector):
            pass                       # structural negative CFO for a lender/heavy-capex name — not a veto
        else:
            reasons.append(f"pt14: {dr or 'hard-disqualified'}")

    active = bool(reasons)
    return active, ("; ".join(reasons) if active else None)


def veto_map(conn, symbols: list[str], sectors: Optional[dict] = None) -> dict[str, tuple[bool, Optional[str]]]:
    """Batch compute_veto for the scorer. sectors maps symbol -> sector (optional).

    Opens ONE shared read-only research.db connection for the whole batch (so the pledge
    read costs a single open, and any lock stall is paid at most once) and closes it after.
    """
    sectors = sectors or {}
    research_conn = _research_ro()
    try:
        return {s: compute_veto(conn, s, sectors.get(s), research_conn=research_conn) for s in symbols}
    finally:
        if research_conn is not None:
            try:
                research_conn.close()
            except sqlite3.Error:
                pass


# --- selftest (synthetic, in-memory; no real DB, no network) --------------------

def _selftest() -> int:
    """Hermetic checks: the primary SHP pledge drives the veto and overrides the stale
    column both ways, the newest quarter wins, the stale column is used only as a fallback,
    a broken/absent research.db degrades without crashing, and the pt14 path is intact."""
    import sqlite3 as _sql

    # synthetic hermes.db — what compute_veto reads for the stale fallback + pt14 + sector
    h = _sql.connect(":memory:")
    h.row_factory = _sql.Row
    h.executescript(
        "CREATE TABLE fundamentals(symbol TEXT, promoter_pledge REAL);"
        "CREATE TABLE stock_signals(symbol TEXT, primary_sector TEXT, trade_date TEXT);"
        "CREATE TABLE pattern_scores(symbol TEXT, hard_disqualified INT, disqualifier_reasons TEXT, scored_at TEXT);")
    h.executemany("INSERT INTO fundamentals VALUES (?,?)", [
        ("RELIANCE", None),        # stale col NULL (the live bug)
        ("STALEHIGH", 55.0),       # stale says 55, but SHP will say 0.0 → must NOT veto
        ("FALLBACKONLY", 30.0),    # not in SHP → fallback fires (veto)
        ("CLEANFALL", 5.0),        # not in SHP → fallback, no veto
    ])
    h.executemany("INSERT INTO pattern_scores VALUES (?,?,?,datetime('now'))", [
        ("BADRPT", 1, "auditor resignation; RPT"),        # non-cashflow → veto
        ("BANKCFO", 1, "negative CFO / high leverage"),   # cashflow + bank sector → suppressed
    ])
    h.execute("INSERT INTO stock_signals VALUES ('BANKCFO','Private Sector Bank','2026-07-01')")

    # synthetic research.db (primary NSE-XBRL-SHP feed), passed as research_conn
    r = _sql.connect(":memory:")
    r.execute("CREATE TABLE shareholding_history"
              "(symbol TEXT, period_type TEXT, period_end TEXT, report_date TEXT, metric TEXT, value REAL, source TEXT)")
    r.executemany(
        "INSERT INTO shareholding_history VALUES (?, 'Q', ?, ?, 'Promoter Pledge', ?, 'NSE-XBRL-SHP')", [
            ("JPPOWER",    "2026-03-31", "2026-04-20", 72.99),   # textbook >20% → veto
            ("VIKRAMSOLR", "2026-03-31", "2026-04-20", 6.77),    # <20 → no veto
            ("RELIANCE",   "2026-03-31", "2026-04-20", 0.0),     # 0 → no veto
            ("STALEHIGH",  "2026-03-31", "2026-04-20", 0.0),     # SHP 0.0 beats stale 55 → no veto
            ("LATESTTEST", "2024-03-31", "2024-04-20", 80.0),    # OLD high
            ("LATESTTEST", "2026-03-31", "2026-04-20", 3.0),     # NEW low → latest wins → no veto
        ])

    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        ok = ok and bool(cond)

    def veto(sym, rc=r):
        return compute_veto(h, sym, research_conn=rc)

    # primary-source pledge drives the veto
    a, why = veto("JPPOWER")
    check("JPPOWER 73% pledged -> VETO (was silently passing)", a and "73%" in (why or ""))
    check("VIKRAMSOLR 6.77% -> no pledge veto", not veto("VIKRAMSOLR")[0])
    check("RELIANCE 0.0% -> no veto", not veto("RELIANCE")[0])
    # the crux: the SHP value overrides the stale column, and the newest quarter wins
    check("STALEHIGH: SHP 0.0 overrides stale 55 -> no veto", not veto("STALEHIGH")[0])
    check("LATESTTEST: latest quarter (3.0) wins over old 80.0 -> no veto", not veto("LATESTTEST")[0])
    # stale column used ONLY as a fallback when SHP has nothing
    check("FALLBACKONLY: SHP empty, stale 30 -> veto via fallback", veto("FALLBACKONLY")[0])
    check("CLEANFALL: SHP empty, stale 5 -> no veto", not veto("CLEANFALL")[0])
    # graceful degradation — a broken/absent research.db must never raise
    broken = _sql.connect(":memory:")   # has NO shareholding_history table
    check("_shp_pledge on broken research.db -> None (no raise)", _shp_pledge("JPPOWER", broken) is None)
    check("_shp_pledge symbol absent from feed -> None", _shp_pledge("NOSUCH", r) is None)
    check("broken research.db still falls back to stale column", compute_veto(h, "FALLBACKONLY", research_conn=broken)[0])
    check("broken research.db + no stale row -> no crash, no veto", not compute_veto(h, "JPPOWER", research_conn=broken)[0])
    # pt14 path unchanged
    check("pt14 non-cashflow disqualifier -> veto", veto("BADRPT")[0])
    check("pt14 cashflow disqualifier + bank sector -> suppressed", not veto("BANKCFO")[0])

    for c in (h, r, broken):
        c.close()
    print("concall_veto selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="CCI forensic veto gate")
    ap.add_argument("--selftest", action="store_true", help="run hermetic synthetic checks (no real DB)")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(_selftest())
    ap.error("give --selftest")
