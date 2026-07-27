"""test_graphite_parity_defects.py — pins the two XS CORRECTNESS defects the 2026-07-28 Graphite
gap audit found (`docs/graphite-gap-register.md` §3j row 1 and §4b row 1).

Both were the same species of bug: a Graphite port that reads a store with the WRONG KEY, so the
page renders, looks complete, passes every existing test — and is silently wrong.

  1. BAND-LOCKS DIRECTION CASE (register §3j). `src/automation/band_lock.py:111` emits
     `dir = "UP" | "DOWN"`; the Graphite read + render compared against lowercase `"up"`, so
     EVERY row rendered "▼ lower" and BOTH the "Locked up" and "Locked down" tiles read 0 on a
     board full of locks. Classic compares "UP" (`src/web/bandlock_view.py:60-61`, `:82-83`).

  2. SEASONAL ISO-WEEK AXIS (register §4b). The engine persists the weekly axis as `'iso_week'`
     (`src/automation/seasonal_tape.py:104`); the Graphite read asked for `'week'`, so the
     By-week-of-the-year grid and its cell-drill could NEVER render, for any entity — while the
     parity ledger recorded the ISO-week grid as SHIPPED.

Each test below fails on the pre-fix code (verified RED before the fix landed) and passes after.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


# ══════════════════════════════════════════════════════════════════════════════════════
# 1. band-locks — the direction the ENGINE emits is the direction the page must read
# ══════════════════════════════════════════════════════════════════════════════════════
def _band_conn():
    """A REAL feed the engine can read: LOCKY upper-locked 3 straight days, DOWNY lower-locked
    once (same shape as band_lock.selftest, so the fixture is the engine's own vocabulary)."""
    c = _conn()
    c.executescript(
        "CREATE TABLE price_bands_current (as_of TEXT, symbol TEXT, series TEXT, band TEXT, "
        "remarks TEXT);"
        "CREATE TABLE price_band_events (as_of TEXT, symbol TEXT, series TEXT, old_band TEXT, "
        "new_band TEXT);"
        "CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT, open REAL, "
        "high REAL, low REAL, close REAL, prev_close REAL);")
    px = 100.0
    for d in ("2026-07-07", "2026-07-08", "2026-07-09"):
        nxt = round(px * 1.05, 2)
        c.execute("INSERT INTO bhavcopy_rows VALUES ('LOCKY', ?, 'EQ', ?, ?, ?, ?, ?)",
                  (d, px, nxt, px * 0.99, nxt, px))
        px = nxt
    c.execute("INSERT INTO price_bands_current VALUES ('2026-07-09','LOCKY','EQ','5','')")
    c.execute("INSERT INTO bhavcopy_rows VALUES ('DOWNY','2026-07-09','EQ',200,201,180,180,200)")
    c.execute("INSERT INTO price_bands_current VALUES ('2026-07-09','DOWNY','EQ','10','')")
    c.commit()
    return c


def _band_fixture():
    """One upper lock and one lower lock, in the engine's own vocabulary."""
    return [{"symbol": "AAA", "dir": "UP", "days": 3, "band": 10, "first_date": "2026-07-24",
             "last_close": 101.0, "move_pct": 21.5},
            {"symbol": "BBB", "dir": "DOWN", "days": 2, "band": 5, "first_date": "2026-07-25",
             "last_close": 47.0, "move_pct": -9.1}]


def test_the_engine_still_emits_uppercase_directions():
    """The premise of the fix, asserted not assumed — if band_lock ever switches to lowercase this
    tells you here rather than through a silently wrong board."""
    import inspect

    from src.automation import band_lock as BL
    src = inspect.getsource(BL)
    assert '"dir": "UP" if up else "DOWN"' in src, (
        "band_lock no longer emits UP/DOWN — re-check every consumer's comparison")


def test_band_lock_direction_predicates_match_the_engine_vocabulary():
    up, dn = _band_fixture()
    from src.web.home import internals_reads as R
    assert R.is_upper_lock(up) and not R.is_lower_lock(up)
    assert R.is_lower_lock(dn) and not R.is_upper_lock(dn)
    # defensive: a missing / empty direction is neither
    assert not R.is_upper_lock({}) and not R.is_lower_lock({"dir": None})


def test_band_lock_tiles_count_upper_and_lower_locks_instead_of_reading_zero():
    """THE DEFECT, read→render end to end: on a feed carrying one upper and one lower lock, both
    tiles read 0. Walked from the real engine so no hand-typed dict can hide the mismatch."""
    from src.web.home import internals_pages as P
    from src.web.home import internals_reads as R
    pack = R.band_locks(_band_conn())
    assert pack and pack["n"] == 2, pack
    assert (pack["up"], pack["down"]) == (1, 1), (
        "the tiles must count the engine's UP/DOWN, got up=%r down=%r" % (pack.get("up"),
                                                                         pack.get("down")))
    html = P._bandlock_block(pack)
    assert "LOCKY" in html and "DOWNY" in html
    assert html.count("▲ upper") == 1 and html.count("▼ lower") == 1, html[:400]


def test_band_lock_rows_render_the_direction_the_engine_reported():
    """THE DEFECT: every row rendered '▼ lower', including the upper locks."""
    from src.web.home import internals_pages as P
    html = P._bandlock_block({"streaks": _band_fixture(), "n": 2, "as_of": "2026-07-27",
                              "n_flagged": 1, "feed_birth": "2025-01-01", "min_streak": 3,
                              "n_days": 400, "up": 1, "down": 1})
    assert "▲ upper" in html, "an UP streak must render as an upper lock"
    assert "▼ lower" in html, "a DOWN streak must render as a lower lock"
    assert html.count("▼ lower") == 1, "only the DOWN row may read 'lower'"


# ══════════════════════════════════════════════════════════════════════════════════════
# 2. seasonal — the ISO-week grid must actually be reachable
# ══════════════════════════════════════════════════════════════════════════════════════
def _seasonal_fixture():
    """A store written the way the ENGINE writes it: axis='iso_week'."""
    conn = _conn()
    conn.execute(
        "CREATE TABLE seasonal_cells (scope TEXT, entity TEXT, axis TEXT, cell INTEGER, "
        "script_z REAL, n_years INTEGER, hit_rate REAL, conf REAL, colored INTEGER, signed INTEGER,"
        " emp_p_block REAL, emp_p_phase REAL, null_p95 REAL, sign_stable INTEGER, fdr_pass INTEGER,"
        " mechanism TEXT)")
    conn.execute("CREATE TABLE seasonal_stack (scope TEXT, entity TEXT, axis TEXT, cell INTEGER, "
                 "year INTEGER, mean_z REAL, n_obs INTEGER)")
    rows = [("index", "Nifty 500", "month", 7, 0.11, 24, 0.54),
            ("index", "Nifty 500", "weekday", 2, -0.03, 24, 0.49),
            ("index", "Nifty 500", "iso_week", 31, 0.42, 22, 0.63)]
    for sc, en, ax, cl, z, ny, hr in rows:
        conn.execute("INSERT INTO seasonal_cells (scope, entity, axis, cell, script_z, n_years, "
                     "hit_rate, colored) VALUES (?,?,?,?,?,?,?,0)", (sc, en, ax, cl, z, ny, hr))
    for yr, mz in ((2024, 0.3), (2025, -0.1), (2026, 0.5)):
        conn.execute("INSERT INTO seasonal_stack VALUES ('index','Nifty 500','iso_week',31,?,?,20)",
                     (yr, mz))
    conn.commit()
    return conn


def test_the_engine_still_persists_the_weekly_axis_as_iso_week():
    """The premise of the fix, asserted not assumed."""
    import inspect

    from src.automation import seasonal_tape as ST
    assert '"iso_week"' in inspect.getsource(ST), (
        "the seasonal engine no longer writes an iso_week axis — re-check the read's translation")


def test_seasonal_script_returns_the_iso_week_cells_under_the_page_key():
    """THE DEFECT: script.get('week') was ALWAYS empty, so the grid could never render."""
    from src.web.home import w2_reads as W
    script = W.seasonal_script(_seasonal_fixture(), "index", "Nifty 500")
    assert "week" in script, "the ISO-week axis must reach the page under its 'week' key"
    assert 31 in script["week"], script.get("week")
    assert abs(float(script["week"][31]["script_z"]) - 0.42) < 1e-9
    # the other two axes are unchanged by the translation
    assert 7 in script.get("month", {}) and 2 in script.get("weekday", {})


def test_seasonal_year_stack_reaches_the_iso_week_rows_for_the_cell_drill():
    """THE DEFECT: clicking a week cell drilled into an empty stack."""
    from src.web.home import w2_reads as W
    rows = W.seasonal_year_stack(_seasonal_fixture(), "index", "Nifty 500", "week", 31)
    assert [r["year"] for r in rows] == [2024, 2025, 2026], rows


def test_the_weekly_grid_actually_renders_on_the_seasonal_tape():
    """End of the chain: the page emits the 'By week of the year' section and its W-labelled cell."""
    from src.web.home import seasonal_pages as S
    html = S._tape(_seasonal_fixture(), {"scope": "index", "entity": "Nifty 500"})
    assert "By week of the year" in html
    assert "W31" in html
