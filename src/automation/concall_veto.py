"""CCI forensic veto gate (debate rank #1) — the un-spinnable spine.

Credibility cannot be scored from the suspect's own testimony: a glib fraud runs
a smooth, confident, numeric call right up to collapse (Manpasand, Vakrangee,
DHFL, Yes Bank, Coffee Day...). So an EXOGENOUS integrity gate sits IN FRONT of
the credibility engine and can force tier=D regardless of how good the call
sounded. We do NOT build a new forensic platform — we WIRE the disqualifiers the
pt14 engine already computes (resources/patearn/SKILL.md) plus the directly-held
promoter pledge:

  - promoter pledge >= PLEDGE_VETO  -> UNIVERSAL hard veto (even for financials)
  - pt14 hard_disqualified           -> veto, EXCEPT cash-flow/leverage reasons are
                                        sector-SUPPRESSED for banks/NBFCs and heavy-
                                        capex cyclicals (negative CFO is structural
                                        there, not a fraud tell) — Ramana's A3 ruling.

Pledge comes from the PRIMARY source: the NSE SHP XBRL feed (research.db
``shareholding_history``, metric 'Promoter Pledge'). hermes.db
``fundamentals.promoter_pledge`` is the frozen Screener-era snapshot and is only
a per-symbol fallback (S76: JPPOWER 73% pledged had no row there and sailed
through this veto). Pure SQL over existing tables (`shareholding_history`,
`fundamentals`, `pattern_scores`). No LLM.
"""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Optional

PLEDGE_VETO = 20.0          # promoter pledge % at/above which the name is vetoed (universal)

# research.db path override (selftest only); None -> provenance.RESEARCH_DB.
RESEARCH_DB_OVERRIDE: Optional[str] = None
_SHP_TTL_S = 900.0          # re-read the SHP pledge map at most every 15 min
# (loaded_monotonic, {symbol: latest pledge %} | False when unavailable | None never loaded)
_shp_cache: tuple = (0.0, None)


def _shp_pledge_map() -> Optional[dict]:
    """Latest primary-source promoter pledge % per symbol, from research.db
    shareholding_history (NSE SHP XBRL, metric 'Promoter Pledge'). One bulk
    read-only query, cached for _SHP_TTL_S. Returns None when research.db is
    absent/locked (also cached, so a locked DB costs ONE wait per TTL, not one
    per symbol) — the caller then falls back to the legacy fundamentals column.
    NEVER raises: the veto must not be able to crash the scorer."""
    global _shp_cache
    loaded, cached = _shp_cache
    if cached is not None and (time.monotonic() - loaded) < _SHP_TTL_S:
        return cached or None
    try:
        from src.automation import provenance
        path = RESEARCH_DB_OVERRIDE or provenance.RESEARCH_DB
        if not os.path.exists(path):
            m: object = False
        else:
            rc = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)
            try:
                rows = rc.execute(
                    "SELECT symbol, value FROM shareholding_history "
                    "WHERE metric='Promoter Pledge' AND value IS NOT NULL "
                    "ORDER BY period_end").fetchall()
            finally:
                rc.close()
            m = {sym: val for sym, val in rows}   # ordered by period_end -> latest wins
    except Exception:
        m = False
    _shp_cache = (time.monotonic(), m)
    return m or None

# sectors where cash-flow / leverage disqualifiers are SUPPRESSED (structural, not fraud)
_FIN_SECTORS = ("bank", "financ", "nbfc", "housing finance", "insurance", "capital market", "broking")
_HEAVY_CAPEX = ("cement", "steel", "power", "metal", "infrastructure", "construction",
                "oil", "gas", "mining", "shipping", "telecom", "realty", "real estate")
_CASHFLOW_REASON = ("cfo", "cash flow", "cash-flow", "operating cash", "cfo/pat",
                    "negative cash", "debt", "leverage", "d/e", "working capital")


def _sector_suppresses_cashflow(sector: Optional[str]) -> bool:
    s = (sector or "").lower()
    return any(k in s for k in _FIN_SECTORS) or any(k in s for k in _HEAVY_CAPEX)


def compute_veto(conn, symbol: str, sector: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """Return (veto_active, veto_reason) for a symbol from exogenous integrity signals.

    Sector (for the cash-flow suppression rule) is auto-resolved from
    stock_signals.primary_sector when not supplied — this reference to the
    price-derived table lives HERE (the integrity gate), never in the credibility
    scorer, so the scorer's price↔credibility firewall stays clean.
    """
    reasons: list[str] = []
    if sector is None:
        srow = conn.execute(
            "SELECT primary_sector FROM stock_signals WHERE symbol=? AND primary_sector IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 1", (symbol,)
        ).fetchone()
        sector = srow["primary_sector"] if srow else None

    # 1. Promoter pledge — the highest-precision, un-spinnable India signal (universal).
    #    SHP primary source first; the legacy Screener-era column only when the feed
    #    has no row for the symbol (a 0.0 from SHP is an answer, not a miss).
    shp = _shp_pledge_map()
    pledge = shp.get(symbol) if shp else None
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
    """Batch compute_veto for the scorer. sectors maps symbol -> sector (optional)."""
    sectors = sectors or {}
    return {s: compute_veto(conn, s, sectors.get(s)) for s in symbols}


# ── selftest (no network, no live DBs) ────────────────────────────────────────

def _selftest() -> int:
    """Fixture DBs prove: SHP primary read, latest-period-wins, 0.0-is-an-answer,
    legacy fallback, absent-research.db degrade, pt14 cash-flow suppression."""
    global RESEARCH_DB_OVERRIDE, _shp_cache
    import tempfile

    tmp = tempfile.mkdtemp(prefix="veto_selftest_")
    shp_path = os.path.join(tmp, "research.db")
    rdb = sqlite3.connect(shp_path)
    rdb.executescript(
        "CREATE TABLE shareholding_history(symbol TEXT, period_type TEXT, period_end TEXT,"
        " report_date TEXT, metric TEXT, value REAL, PRIMARY KEY(symbol, period_end, metric));")
    rdb.executemany(
        "INSERT INTO shareholding_history VALUES (?,?,?,?,?,?)", [
            ("JPPOWER", "Q", "2025-12-31", "2026-01-30", "Promoter Pledge", 80.0),
            ("JPPOWER", "Q", "2026-03-31", "2026-04-30", "Promoter Pledge", 72.99),
            ("RELIANCE", "Q", "2026-03-31", "2026-04-30", "Promoter Pledge", 0.0),
            ("VIKRAMSOLR", "Q", "2026-03-31", "2026-04-30", "Promoter Pledge", 6.77),
        ])
    rdb.commit(); rdb.close()

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE fundamentals(symbol TEXT PRIMARY KEY, promoter_pledge REAL);"
        "CREATE TABLE pattern_scores(symbol TEXT, hard_disqualified INTEGER,"
        " disqualifier_reasons TEXT, scored_at TEXT);"
        "CREATE TABLE stock_signals(symbol TEXT, primary_sector TEXT, trade_date TEXT);")
    conn.executemany("INSERT INTO fundamentals VALUES (?,?)", [
        ("RELIANCE", None),          # live shape: legacy column is NULL
        ("LEGACYCO", 45.0),          # no SHP row -> must veto via the fallback
    ])
    conn.executemany("INSERT INTO pattern_scores VALUES (?,?,?,?)", [
        ("BANKCO", 1, "negative CFO 3y", "2026-06-01"),
        ("INDUSTCO", 1, "negative CFO 3y", "2026-06-01"),
    ])
    conn.executemany("INSERT INTO stock_signals VALUES (?,?,?)", [
        ("BANKCO", "Private Sector Bank", "2026-07-01"),
        ("INDUSTCO", "Specialty Chemicals", "2026-07-01"),
    ])

    failures: list[str] = []

    def check(name, got, want):
        ok = got == want
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: got={got!r} want={want!r}")
        if not ok:
            failures.append(name)

    RESEARCH_DB_OVERRIDE, _shp_cache = shp_path, (0.0, None)
    a, r = compute_veto(conn, "JPPOWER")
    check("JPPOWER vetoed from SHP (latest period 72.99, not 80.0)", (a, r), (True, "promoter pledge 73%"))
    check("RELIANCE clean (SHP 0.0 is an answer; no fallback)", compute_veto(conn, "RELIANCE"), (False, None))
    check("VIKRAMSOLR clean (6.77 < 20)", compute_veto(conn, "VIKRAMSOLR"), (False, None))
    check("LEGACYCO vetoed via legacy fallback (no SHP row)",
          compute_veto(conn, "LEGACYCO"), (True, "promoter pledge 45%"))
    check("bank CFO disqualifier suppressed", compute_veto(conn, "BANKCO"), (False, None))
    check("non-bank CFO disqualifier vetoes",
          compute_veto(conn, "INDUSTCO"), (True, "pt14: negative CFO 3y"))

    # research.db absent -> degrade to the legacy column only, never crash.
    RESEARCH_DB_OVERRIDE, _shp_cache = os.path.join(tmp, "missing.db"), (0.0, None)
    check("degrade: fallback still vetoes LEGACYCO", compute_veto(conn, "LEGACYCO"), (True, "promoter pledge 45%"))
    check("degrade: JPPOWER invisible without SHP (documents the gap)",
          compute_veto(conn, "JPPOWER"), (False, None))

    RESEARCH_DB_OVERRIDE, _shp_cache = None, (0.0, None)
    print(f"selftest: {'PASS' if not failures else 'FAIL'} ({8 - len(failures)}/8)")
    return 1 if failures else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="CCI forensic veto gate (see compute_veto)")
    ap.add_argument("--selftest", action="store_true", help="run the fixture-DB selftest")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    ap.error("give --selftest")
