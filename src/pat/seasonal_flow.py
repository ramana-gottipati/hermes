"""Pat 'seasonal' flow — deterministic recognition + ranking for
"top-ranked / historically-bearish stocks for this|next month|week".

Answers the analyst's ask ("what are the top-ranked stocks for this month / next
month / this week / next week?", and the bearish reverse) by ranking the SAME
per-entity historical calendar base-rates the This-month screen ranks — mirroring
its DEFAULT confidence-adjusted order: the Wilson LOWER bound of the hit-rate for
bullish (UPPER bound for bearish), ties broken on the mean residual (move size).

DESCRIPTIVE-ONLY / SEBI-safe: historical calendar base-rates, never a
recommendation, forecast, or trade — expectancy ≈ 0 net of costs. This module is
PURE logic (recognition + a SELECT-and-sort); the HTML render lives in
src/pat/web.py:_seasonal_flow so it can reuse Pat's house helpers.

Recognition is a deterministic ₹0 first-pass in engine.route() (before the LLM
parse). It is deliberately conservative — it fires ONLY on a "<this|next>
<month|week>" period phrase + a ranking/seasonal intent, and yields to the movers
flow when the ask is clearly intraday/liquidity ("biggest movers this week") and
carries no seasonal signal. A miss simply falls through to the normal parse.
"""
from __future__ import annotations

import re
from datetime import date

from src.automation.seasonal_tape import wilson_ci

_MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

_PERIOD_RE = re.compile(r"\b(this|next|current|present|coming|upcoming|following)\s+(month|week)\b")
_INTENT_RE = re.compile(r"\b(top|best|strongest|bullish|bearish|worst|weakest|rank|ranked|"
                        r"season|seasonal|historically|historical|leader|leaders|coldest|"
                        r"hottest|avoid|winners?|losers?)\b")
_STRONG_SEASONAL_RE = re.compile(r"\b(season|seasonal|historically|historical|calendar|usually|tend|"
                                 r"base[- ]?rate)\b")
_MOVERS_RE = re.compile(r"\b(mover|movers|gainer|gainers|intraday|today|turnover|volume|liquid|"
                        r"delivery|deliv)\b")
_BEAR_RE = re.compile(r"\b(bearish|worst|weakest|cold|coldest|avoid|down|weak|fall|falling|"
                      r"negative|underperform|loser|losers|drop)\b")

_VALID_PERIODS = ("this-month", "next-month", "this-week", "next-week")
_VALID_DIRECTIONS = ("bullish", "bearish")


def parse_seasonal(query: str) -> dict | None:
    """"top stocks this month" / "historically bearish stocks next week" ->
    {flow:"seasonal", params:{period, direction}} | None. Conservative: needs a
    <this|next> <month|week> phrase + a ranking/seasonal intent, and yields to
    movers on an intraday/liquidity ask that carries no seasonal signal."""
    q = (query or "").lower()
    mper = _PERIOD_RE.search(q)
    if not mper:
        return None
    if not _INTENT_RE.search(q):
        return None
    if _MOVERS_RE.search(q) and not _STRONG_SEASONAL_RE.search(q):
        return None                                  # "biggest movers this week" -> movers flow
    when, unit = mper.group(1), mper.group(2)
    nxt = when in ("next", "coming", "upcoming", "following")
    period = ("next-" if nxt else "this-") + unit
    direction = "bearish" if _BEAR_RE.search(q) else "bullish"
    return {"flow": "seasonal", "params": {"period": period, "direction": direction}}


def cell_for_period(period: str, today: date | None = None) -> tuple[str, int]:
    """(axis, cell) for a period label — computed at render time (never cached) so
    "this month" is always the live month. Week uses the ISO week number."""
    today = today or date.today()
    if period.endswith("month"):
        m = today.month
        if period.startswith("next"):
            m = m % 12 + 1
        return ("month", m)
    w = today.isocalendar()[1]
    if period.startswith("next"):
        w = w + 1 if w < 53 else 1
    return ("iso_week", w)


def period_label(period: str, today: date | None = None) -> str:
    """Human label, e.g. 'this month (Jul)' / 'next week (ISO W28)'."""
    axis, cell = cell_for_period(period, today)
    lead = "next" if period.startswith("next") else "this"
    if axis == "month":
        return f"{lead} month ({_MONTH_ABBR.get(cell, cell)})"
    return f"{lead} week (ISO W{cell})"


def rank(conn, axis: str, cell: int, direction: str, *, top_n: int = 10,
         min_years: int = 15) -> list[dict]:
    """Ranked stock base-rates for one (axis, cell), mirroring the This-month
    screen's DEFAULT order: keep names with the right-signed mean residual and
    >=min_years history; bullish -> Wilson LOWER bound desc (ties bigger move);
    bearish -> Wilson UPPER bound asc (ties more-negative move). Read-only."""
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT entity, script_z, n_years, hit_rate FROM seasonal_cells "
            "WHERE scope='stock' AND axis=? AND cell=?", (axis, cell)).fetchall()
    except Exception:  # noqa: BLE001 — never break Pat on a snapshot gap
        return []
    recs = []
    for r in rows:
        ent, sz, ny, hr = r[0], r[1], (r[2] or 0), r[3]
        if ny < min_years or sz is None or hr is None:
            continue
        if direction == "bullish" and not sz > 0:
            continue
        if direction == "bearish" and not sz < 0:
            continue
        k = round(hr * ny)
        lo, hi = wilson_ci(k, ny)
        recs.append({"entity": ent, "z": sz, "years": ny, "hit": hr, "k": k, "lo": lo, "hi": hi})
    if direction == "bullish":
        recs.sort(key=lambda d: (d["lo"], d["z"]), reverse=True)
    else:
        recs.sort(key=lambda d: (d["hi"], d["z"]))   # lowest upper-bound + most-negative first
    return recs[: max(1, min(int(top_n or 10), 50))]


def _selftest() -> int:
    import os
    import sqlite3
    import tempfile
    # recognition
    assert parse_seasonal("what are the top-ranked stocks for this month") == \
        {"flow": "seasonal", "params": {"period": "this-month", "direction": "bullish"}}
    assert parse_seasonal("historically bearish stocks next week")["params"] == \
        {"period": "next-week", "direction": "bearish"}
    assert parse_seasonal("seasonal losers this month")["params"]["direction"] == "bearish"
    assert parse_seasonal("strongest stocks next month")["params"]["period"] == "next-month"
    assert parse_seasonal("biggest movers this week") is None, "must yield to movers flow"
    assert parse_seasonal("top gainers this week") is None, "intraday gainers -> not seasonal"
    assert parse_seasonal("top stocks today") is None, "no month/week period"
    assert parse_seasonal("bullish stocks") is None, "no period"
    # cell math
    ref = date(2026, 7, 13)  # a Monday in ISO week 29
    assert cell_for_period("this-month", ref) == ("month", 7)
    assert cell_for_period("next-month", ref) == ("month", 8)
    assert cell_for_period("this-week", ref)[0] == "iso_week"
    assert "Jul" in period_label("this-month", ref)
    # december wrap
    assert cell_for_period("next-month", date(2026, 12, 1)) == ("month", 1)
    # ranking on a tiny synthetic DB
    tmp = os.path.join(tempfile.gettempdir(), "pat_seasonal_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE seasonal_cells(scope TEXT, entity TEXT, axis TEXT, cell INTEGER, "
                "script_z REAL, n_years INTEGER, hit_rate REAL)")
    con.executemany(
        "INSERT INTO seasonal_cells VALUES ('stock',?,?,?,?,?,?)",
        [("AAA", "month", 7, 0.30, 19, 19 / 19),   # perfect, bull -> #1
         ("BBB", "month", 7, 0.10, 19, 18 / 19),
         ("CCC", "month", 7, -0.20, 18, 6 / 18),   # bearish
         ("DDD", "month", 7, 0.05, 8, 1.0),        # <15y -> excluded
         ("EEE", "month", 7, -0.30, 17, 5 / 17)])  # bearish, bigger down
    con.commit()
    con.row_factory = sqlite3.Row
    bull = rank(con, "month", 7, "bullish", top_n=5)
    assert [r["entity"] for r in bull] == ["AAA", "BBB"], [r["entity"] for r in bull]
    bear = rank(con, "month", 7, "bearish", top_n=5)
    assert set(r["entity"] for r in bear) == {"CCC", "EEE"}, [r["entity"] for r in bear]
    con.close()
    os.remove(tmp)
    print("seasonal_flow selftest OK — recognition (period/direction/movers-yield) + cell math "
          "(this/next month & week, Dec wrap) + confidence-adjusted rank (bull Wilson-lo, bear "
          "Wilson-hi, <15y excluded)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
