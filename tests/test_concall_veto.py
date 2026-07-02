"""Regression tests for the CCI forensic veto's promoter-pledge SOURCE (queue #3 fix).

Provenance: compute_veto's UNIVERSAL hard veto used to read the STALE Screener-era
hermes.db.fundamentals.promoter_pledge column (NULL / no-row for most names), so a
textbook >20%-pledged hard-disqualifier (JPPOWER ~73%) SILENTLY PASSED the veto. The fix
(landed via 6e2160b -> 07aca8d, adopting the live-deployed implementation) reads the
PRIMARY source first (NSE-XBRL-SHP -> research.db.shareholding_history, metric 'Promoter
Pledge', latest quarter), falls back to the stale column ONLY when the feed has nothing,
and degrades gracefully (never raises) if research.db is absent / write-locked.

These pin that contract so it can't silently regress. In-memory SQLite only -- no real DB,
no network (gate-0 anywhere).
"""
import sqlite3

from src.automation import concall_veto


def _hermes(rows_fund=(), rows_ps=(), rows_ss=()):
    """A synthetic hermes.db (what compute_veto reads for the stale fallback + pt14 + sector)."""
    h = sqlite3.connect(":memory:")
    h.row_factory = sqlite3.Row
    h.executescript(
        "CREATE TABLE fundamentals(symbol TEXT, promoter_pledge REAL);"
        "CREATE TABLE stock_signals(symbol TEXT, primary_sector TEXT, trade_date TEXT);"
        "CREATE TABLE pattern_scores(symbol TEXT, hard_disqualified INT, disqualifier_reasons TEXT, scored_at TEXT);")
    h.executemany("INSERT INTO fundamentals VALUES (?,?)", rows_fund)
    h.executemany("INSERT INTO pattern_scores VALUES (?,?,?,datetime('now'))", rows_ps)
    h.executemany("INSERT INTO stock_signals VALUES (?,?,?)", rows_ss)
    return h


def _research(rows=()):
    """A synthetic research.db shareholding_history (the primary NSE-XBRL-SHP feed)."""
    r = sqlite3.connect(":memory:")
    r.execute("CREATE TABLE shareholding_history"
              "(symbol TEXT, period_type TEXT, period_end TEXT, report_date TEXT, metric TEXT, value REAL, source TEXT)")
    r.executemany(
        "INSERT INTO shareholding_history VALUES (?, 'Q', ?, ?, 'Promoter Pledge', ?, 'NSE-XBRL-SHP')", rows)
    return r


def test_primary_pledge_fires_veto():
    # JPPOWER 72.99% in the primary feed -> the universal hard veto fires. Note the stale
    # fundamentals table has NO row for it (the live reality) -- the old code saw None here.
    h = _hermes()
    r = _research([("JPPOWER", "2026-03-31", "2026-04-20", 72.99)])
    active, reason = concall_veto.compute_veto(h, "JPPOWER", research_conn=r)
    assert active is True and "73%" in (reason or "")


def test_primary_overrides_stale_column():
    # Stale column says 55 (would wrongly veto), but the primary feed says 0.0 -> NO veto.
    h = _hermes(rows_fund=[("X", 55.0)])
    r = _research([("X", "2026-03-31", "2026-04-20", 0.0)])
    assert concall_veto.compute_veto(h, "X", research_conn=r)[0] is False


def test_latest_quarter_wins():
    # An old 80% must not outvote the latest 3% (ISO period_end DESC ordering).
    h = _hermes()
    r = _research([("X", "2024-03-31", "2024-04-20", 80.0), ("X", "2026-03-31", "2026-04-20", 3.0)])
    assert concall_veto.compute_veto(h, "X", research_conn=r)[0] is False


def test_stale_column_used_only_as_fallback():
    # Symbol absent from the primary feed -> fall back to the stale column (>=20 -> veto).
    h = _hermes(rows_fund=[("X", 30.0)])
    assert concall_veto.compute_veto(h, "X", research_conn=_research())[0] is True


def test_degrades_when_research_db_broken():
    # A research.db with no shareholding_history (~ absent / write-locked) must never raise;
    # _shp_pledge returns None and compute_veto falls back to the stale column.
    h = _hermes(rows_fund=[("X", 30.0)])
    broken = sqlite3.connect(":memory:")
    assert concall_veto._shp_pledge("X", broken) is None
    assert concall_veto.compute_veto(h, "X", research_conn=broken)[0] is True


def test_pt14_path_unchanged():
    # The pt14 disqualifier branch is untouched: a non-cashflow reason vetoes; a cashflow
    # reason for a bank is sector-suppressed.
    h = _hermes(
        rows_ps=[("BADRPT", 1, "auditor resignation; RPT"),
                 ("BANKCFO", 1, "negative CFO / high leverage")],
        rows_ss=[("BANKCFO", "Private Sector Bank", "2026-07-01")])
    r = _research()
    assert concall_veto.compute_veto(h, "BADRPT", research_conn=r)[0] is True
    assert concall_veto.compute_veto(h, "BANKCFO", research_conn=r)[0] is False


def test_module_selftest_green():
    # The module's own hermetic selftest (13 checks) stays green.
    assert concall_veto._selftest() == 0
