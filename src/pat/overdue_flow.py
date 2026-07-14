"""Pat 'overdue' flow — deterministic recognition + a bounded read of which LIVE names are OVERDUE
for a corporate event vs their OWN historical cadence (the /dash/event-cadence signal).

Answers "which stocks are overdue for results?", "who's late on dividends?", "off-cadence names",
etc. — TIME-only, from the bounded `seasonal_events` snapshot (anchor_basis='projection' → the
cadence read, NOT the announced ex-date/board-meeting calendars, which live on /dash/actions +
/dash/results-reactions). DESCRIPTIVE-only / SEBI-safe: a rhythm flag, never a delay claim, forecast,
or trade.

Mirrors seasonal_flow.py's contract: PURE logic (recognition + a SELECT-and-sort on the snapshot);
the HTML render lives in src/pat/web.py:_overdue_flow. Recognition is a deterministic ₹0 first-pass
in engine.route() — conservative: fires only on an overdue/late/off-cadence cue with event or stock
context, and a miss simply falls through to the normal parse.
"""
from __future__ import annotations

import re

_EVT_LABEL = {"RESULTS": "Results", "DIVIDEND": "Dividend", "BONUS": "Bonus",
              "SPLIT": "Split", "AGM": "AGM", "OTHER_CA": "Other CA"}

_OVERDUE_RE = re.compile(r"\b(overdue|over ?due|past ?due|behind schedule|off[- ]?cadence|"
                         r"off[- ]?rhythm|late(?:st)? (?:for|on|to)|not (?:yet )?(?:reported|filed|"
                         r"declared)|haven'?t (?:reported|filed|declared))\b")
_LATE_RE = re.compile(r"\blate\b")
_EVENTISH_RE = re.compile(r"\b(result|results|earning|earnings|dividend|dividends|bonus|split|agm|"
                          r"event|events|report|reporting|reported|declare|declared|cadence|"
                          r"payout)\b")
_STOCKISH_RE = re.compile(r"\b(stock|stocks|compan(?:y|ies)|name|names|which|who)\b")


def parse_overdue(query: str) -> dict | None:
    """"which stocks are overdue for results" / "who's late on dividends" ->
    {flow:"overdue", params:{event}} | None. Conservative: needs an overdue/late/off-cadence cue
    AND either an event word or a stock-context word; extracts the event type when named."""
    q = (query or "").lower()
    if not (_OVERDUE_RE.search(q) or _LATE_RE.search(q)):
        return None
    if not (_EVENTISH_RE.search(q) or _STOCKISH_RE.search(q)):
        return None                                    # bare "late" with no event/stock context
    if _LATE_RE.search(q) and not _EVENTISH_RE.search(q) and not _OVERDUE_RE.search(q):
        return None                                    # "late session" etc. — not our intent
    event = ""
    if re.search(r"\b(results?|earnings?|report(?:ed|ing)?)\b", q):
        event = "RESULTS"
    elif re.search(r"\bdividend", q):
        event = "DIVIDEND"
    elif re.search(r"\bbonus\b", q):
        event = "BONUS"
    elif re.search(r"\bsplit\b", q):
        event = "SPLIT"
    elif re.search(r"\bagm\b", q):
        event = "AGM"
    return {"flow": "overdue", "params": {"event": event}}


def overdue_rows(conn, event_type: str = "", *, cap_weeks: int = 52, top_n: int = 12) -> list[dict]:
    """The bounded OVERDUE read (mirrors the /dash/event-cadence lens): status='OVERDUE',
    anchor_basis='projection' (excludes announced/declared), within `cap_weeks` (beyond = 'stopped',
    not late). Ordered most-overdue-first within the cap. Read-only; [] on any snapshot gap."""
    if conn is None:
        return []
    where = ["asof=(SELECT MAX(asof) FROM seasonal_events)", "status='OVERDUE'",
             "anchor_basis='projection'", "variance_weeks >= ?"]
    args: list = [-abs(int(cap_weeks))]
    if event_type in _EVT_LABEL:
        where.append("event_type=?"); args.append(event_type)
    args.append(max(1, min(int(top_n or 12), 50)))
    try:
        rows = conn.execute(
            "SELECT symbol, event_type, variance_weeks, lo, hi, n_history FROM seasonal_events "
            f"WHERE {' AND '.join(where)} ORDER BY variance_weeks ASC LIMIT ?", args).fetchall()
    except Exception:  # noqa: BLE001 — never break Pat on a snapshot gap
        return []
    out = []
    for r in rows:
        out.append({"symbol": r[0], "event_type": r[1],
                    "weeks_over": abs(r[2]) if r[2] is not None else None,
                    "lo": r[3], "hi": r[4], "n_history": r[5] or 0})
    return out


def _selftest() -> int:
    import os
    import sqlite3
    import tempfile
    # recognition
    assert parse_overdue("which stocks are overdue for results")["params"]["event"] == "RESULTS"
    assert parse_overdue("who's late on dividends")["params"]["event"] == "DIVIDEND"
    assert parse_overdue("off-cadence names")["flow"] == "overdue"
    assert parse_overdue("overdue events")["params"]["event"] == ""
    assert parse_overdue("companies past due for their AGM")["params"]["event"] == "AGM"
    assert parse_overdue("top stocks this month") is None, "seasonal ranking is not overdue"
    assert parse_overdue("biggest movers today") is None, "movers is not overdue"
    assert parse_overdue("late session trades") is None, "bare 'late' w/o event/stock -> not us"
    # data on a tiny synthetic snapshot: OENX overdue 6w RESULTS, DIVX overdue 40w DIVIDEND,
    # DEADX overdue 900w (beyond cap -> excluded), ANNX declared (excluded, announced elsewhere)
    tmp = os.path.join(tempfile.gettempdir(), "pat_overdue_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE seasonal_events(symbol TEXT, event_type TEXT, asof TEXT, status TEXT, "
                "variance_weeks REAL, anchor_basis TEXT, lo TEXT, hi TEXT, n_history INTEGER)")
    con.executemany(
        "INSERT INTO seasonal_events VALUES (?,?,?,?,?,?,?,?,?)",
        [("OENX", "RESULTS", "2026-07-13", "OVERDUE", -6.0, "projection", "2026-05-01", "2026-06-01", 12),
         ("DIVX", "DIVIDEND", "2026-07-13", "OVERDUE", -40.0, "projection", "2025-09-01", "2025-10-01", 9),
         ("DEADX", "DIVIDEND", "2026-07-13", "OVERDUE", -900.0, "projection", "2008-01-01", "2008-02-01", 3),
         ("ANNX", "RESULTS", "2026-07-13", "OVERDUE", -3.0, "declared", "2026-06-20", "2026-07-05", 20)])
    con.commit()
    rows = overdue_rows(con, "", cap_weeks=52)
    syms = [r["symbol"] for r in rows]
    assert syms == ["DIVX", "OENX"], syms                       # most-overdue-first, DEADX+ANNX excluded
    assert overdue_rows(con, "RESULTS")[0]["symbol"] == "OENX"  # event filter
    assert overdue_rows(con, "DIVIDEND")[0]["weeks_over"] == 40.0
    con.close()
    os.remove(tmp)
    print("overdue_flow selftest OK - recognition (event extract, seasonal/movers/bare-late yield) + "
          "bounded overdue read (<=cap, projection-only=no-announced, most-overdue-first, event filter)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
