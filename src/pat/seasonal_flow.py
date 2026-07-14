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


# ── per-symbol seasonal base rate (S150): "is TCS usually up in July" ──────────────────
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
           "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_MONTH_NAME_RE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b")
_SEAS_SYM_RE = re.compile(r"\b(season|seasonal|seasonality|usually|typically|historically|"
                          r"tend to|tends to|on average|base[- ]?rate|most years|every year)\b")
_UPDOWN_RE = re.compile(r"\b(up|down|rise|rises?|fall|falls?|gain|gains?|green|red|positive|"
                        r"negative|strong|weak|higher|lower)\b")
_S_ON_RE = re.compile(r"\b(?:is|for|of|does|do|has|how does)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_S_CAPS_RE = re.compile(r"\b([A-Z][A-Z0-9&.\-]{1,14})\b")
_S_NOT_TICKER = {"WHAT", "ANY", "THE", "IS", "IN", "ON", "OF", "DOES", "DO", "HAS", "HOW",
                 "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
                 "NOV", "DEC", "USUALLY", "SEASONAL", "SEASONALITY"}


def _seas_symbol(query: str) -> str:
    q = re.sub(r"\s+", " ", (query or "").strip())
    m = _S_ON_RE.search(q)
    if m and m.group(1).upper() not in _S_NOT_TICKER:
        return m.group(1).upper()
    caps = [t for t in _S_CAPS_RE.findall(q) if t.upper() not in _S_NOT_TICKER]
    return caps[0].upper() if len(caps) == 1 else ""


def parse_seasonal_symbol(query: str) -> dict | None:
    """"is TCS usually up in July / does INFY tend to rise in March / TCS seasonality this month"
    -> {flow:"seasonal_stock", params:{symbol, month}} | None. Symbol-anchored + needs a seasonal
    cue (or up/down + a month). month = 1..12 (named/this/next), 0 = "this month" resolved at read.
    Runs BEFORE the market-wide ranking so a symbol'd ask is not read as a leaderboard."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    mname = _MONTH_NAME_RE.search(ql)
    this_next = re.search(r"\b(this|next|current)\s+month\b", ql)
    has_month = bool(mname or this_next)
    seasonal_cue = bool(_SEAS_SYM_RE.search(ql))
    # fire on: a seasonal cue, OR an up/down word WITH an explicit month (a base-rate ask)
    if not (seasonal_cue or (has_month and _UPDOWN_RE.search(ql))):
        return None
    sym = _seas_symbol(q)
    if not sym:
        return None
    if mname:
        month = _MONTHS[mname.group(1)]
    elif this_next and this_next.group(1) == "next":
        month = -1                                    # "next month" → resolved at read
    else:
        month = 0                                     # "this month" / unspecified → resolved at read
    return {"flow": "seasonal_stock", "params": {"symbol": sym, "month": month}}


def stock_month(conn, symbol: str, month: int, today: date | None = None) -> dict | None:
    """One symbol's calendar-month base rate from seasonal_cells (scope='stock', axis='month').
    Returns {symbol, month, month_label, hit_rate, n_years, z, k} or None on a gap. Read-only."""
    if conn is None or not symbol:
        return None
    today = today or date.today()
    if month in (0, None):
        month = today.month
    elif month == -1:
        month = today.month % 12 + 1
    try:
        r = conn.execute(
            "SELECT script_z, n_years, hit_rate FROM seasonal_cells "
            "WHERE scope='stock' AND axis='month' AND cell=? AND entity=?",
            (int(month), symbol.strip().upper())).fetchone()
    except Exception:
        return None
    if not r:
        return None
    z = r["script_z"] if hasattr(r, "keys") else r[0]
    ny = (r["n_years"] if hasattr(r, "keys") else r[1]) or 0
    hr = r["hit_rate"] if hasattr(r, "keys") else r[2]
    if hr is None or ny < 1:
        return None
    return {"symbol": symbol.strip().upper(), "month": month,
            "month_label": _MONTH_ABBR.get(month, str(month)),
            "hit_rate": hr, "n_years": ny, "z": z, "k": round(hr * ny)}


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
    # ── per-symbol base rate (S150) ──
    assert parse_seasonal_symbol("is TCS usually up in July")["params"] == {"symbol": "TCS", "month": 7}
    assert parse_seasonal_symbol("does INFY tend to rise in March")["params"]["month"] == 3
    assert parse_seasonal_symbol("TCS seasonality this month")["params"]["month"] == 0
    assert parse_seasonal_symbol("is WIPRO usually down next month")["params"]["month"] == -1
    assert parse_seasonal_symbol("top stocks this month") is None, "no symbol → market-wide ranking"
    assert parse_seasonal_symbol("is TCS up today") is None, "no month/seasonal cue"
    assert parse_seasonal_symbol("TCS news") is None
    sc = stock_month(con, "AAA", 7)
    assert sc and sc["hit_rate"] == 1.0 and sc["n_years"] == 19 and sc["month_label"] == "Jul", sc
    assert stock_month(con, "AAA", 0, today=date(2026, 7, 1))["month"] == 7   # "this month"
    assert stock_month(con, "NOSUCH", 7) is None and stock_month(None, "AAA", 7) is None
    con.close()
    os.remove(tmp)
    print("seasonal_flow selftest OK — recognition (period/direction/movers-yield) + cell math "
          "(this/next month & week, Dec wrap) + confidence-adjusted rank (bull Wilson-lo, bear "
          "Wilson-hi, <15y excluded)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
