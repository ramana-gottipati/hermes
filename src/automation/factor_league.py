"""Factor League — the classic strategy families as tracked portfolios (descriptive).

Ramana's ask (S132g): the "hugely considered, constantly successful" equity strategy
families, made concrete IN OUR SYSTEM — ranked by the Sharpe/alpha WE measured on 14y
of NSE data (docs/strategy-ledger.md § Tier-1 factor zoo + cost-realism), with each
family's CURRENT participants visible, an automatic portfolio for the champion, and a
constant churn feed. The ranking numbers themselves live in the ledger (frozen results);
this module maintains the LIVE ROSTERS + CHURN for the families whose exact formulas
are computable from the nightly `momentum_scan` snapshot:

  PACER-25    = RISKADJ   (6-mo return ÷ 3-mo vol)          — top flat-cost Sharpe 1.13
  SPRINTER-25 = MOM12     (raw 12-mo momentum)              — highest CAGR, brutal DD
  STEADY-25   = LOWVOL_MOM — the NET champion; its CANONICAL roster is the QUARTERLY
                anchor owned by slow_rotation.py (not duplicated here; the league page
                links it). This module tracks only the fast families' monthly-clock
                drift rosters.

Universe for rosters: latest momentum_scan with turnover ≥ ₹5cr (the recorded
leaderboard's universe). Rosters are top-25 by family score; churn = day-over-day
roster diffs appended to `factor_league_churn` (pruned at 120 days — bounded).
DESCRIPTIVE-ONLY: gross selection lenses, not net-of-cost claims, not advice —
the flat-cost Sharpes are labeled as such wherever shown (C-BLEND lesson).

Owns isolated tables `factor_league` + `factor_league_churn` (no db.py edit).
Pure stdlib. CLI:
  python -m src.automation.factor_league --refresh
  python -m src.automation.factor_league --selftest
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
    from src.automation.slow_rotation import pctrank
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore
    from automation.slow_rotation import pctrank  # type: ignore

TOPN = 25
MIN_TURN_CR = 5.0            # the recorded leaderboard's ₹5cr universe
CHURN_KEEP_DAYS = 120
FAMILIES = ("PACER", "SPRINTER")     # STEADY's canonical roster = slow_rotation anchor

SCHEMA = """
CREATE TABLE IF NOT EXISTS factor_league (
    family  TEXT,
    symbol  TEXT,
    rank    INTEGER,
    score   REAL,
    as_of   TEXT,
    computed_at TEXT,
    PRIMARY KEY(family, symbol)
);
CREATE TABLE IF NOT EXISTS factor_league_churn (
    family  TEXT,
    symbol  TEXT,
    action  TEXT,     -- enter | exit
    on_date TEXT,     -- the momentum_scan as_of that produced the diff
    rank    INTEGER,  -- rank on entry (NULL on exit)
    PRIMARY KEY(family, symbol, on_date, action)
);
"""


def rosters(rows):
    """rows: dicts(symbol, mom6, mom12, vol_66, riskadj, turnover_cr) ->
    {family: [(symbol, rank, score), ...top-25]}. Exact leaderboard formulas."""
    ok = [r for r in rows if r["turnover_cr"] is not None
          and r["turnover_cr"] >= MIN_TURN_CR]
    out = {}
    pacer = [r for r in ok if r["riskadj"] is not None]
    pacer.sort(key=lambda r: -r["riskadj"])
    out["PACER"] = [(r["symbol"], i + 1, round(float(r["riskadj"]), 3))
                    for i, r in enumerate(pacer[:TOPN])]
    spr = [r for r in ok if r["mom12"] is not None]
    spr.sort(key=lambda r: -r["mom12"])
    out["SPRINTER"] = [(r["symbol"], i + 1, round(float(r["mom12"]), 4))
                       for i, r in enumerate(spr[:TOPN])]
    return out


def refresh(conn=None) -> str:
    if conn is None:
        with get_conn() as c:
            return refresh(c)
    conn.executescript(SCHEMA)
    row = conn.execute("SELECT MAX(as_of) d FROM momentum_scan").fetchone()
    as_of = row["d"] if row else None
    if not as_of:
        return "no momentum_scan data"
    prev_asof = conn.execute(
        "SELECT MAX(as_of) d FROM factor_league").fetchone()
    if prev_asof and prev_asof["d"] == as_of:
        return f"rosters already current for {as_of}"
    rows = [dict(r) for r in conn.execute(
        "SELECT symbol, mom6, mom12, vol_66, riskadj, turnover_cr "
        "FROM momentum_scan WHERE as_of=?", (as_of,))]
    ros = rosters(rows)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    n_churn = 0
    for fam in FAMILIES:
        prev = {r["symbol"] for r in conn.execute(
            "SELECT symbol FROM factor_league WHERE family=?", (fam,))}
        cur_rows = ros.get(fam, [])
        cur = {s for s, _rk, _sc in cur_rows}
        if prev:                                   # day-over-day churn feed
            for s, rk, _sc in cur_rows:
                if s not in prev:
                    conn.execute("INSERT OR IGNORE INTO factor_league_churn "
                                 "VALUES (?,?,?,?,?)", (fam, s, "enter", as_of, rk))
                    n_churn += 1
            for s in prev - cur:
                conn.execute("INSERT OR IGNORE INTO factor_league_churn "
                             "VALUES (?,?,?,?,?)", (fam, s, "exit", as_of, None))
                n_churn += 1
        conn.execute("DELETE FROM factor_league WHERE family=?", (fam,))
        conn.executemany(
            "INSERT OR REPLACE INTO factor_league VALUES (?,?,?,?,?,?)",
            [(fam, s, rk, sc, as_of, now) for s, rk, sc in cur_rows])
    conn.execute(
        "DELETE FROM factor_league_churn WHERE on_date < date(?, ?)",
        (as_of, f"-{CHURN_KEEP_DAYS} days"))
    conn.commit()
    return (f"rosters refreshed for {as_of}: "
            + ", ".join(f"{f}={len(ros.get(f, []))}" for f in FAMILIES)
            + f", churn+{n_churn}")


def selftest():
    rows = [{"symbol": f"S{i}", "mom6": 0.01 * i, "mom12": 0.02 * (100 - i),
             "vol_66": 0.02, "riskadj": float(i), "turnover_cr": 10.0}
            for i in range(1, 61)]
    rows.append({"symbol": "ILLIQ", "mom6": 9, "mom12": 9, "vol_66": 0.01,
                 "riskadj": 999.0, "turnover_cr": 1.0})       # below ₹5cr -> excluded
    ros = rosters(rows)
    assert len(ros["PACER"]) == TOPN and len(ros["SPRINTER"]) == TOPN
    assert ros["PACER"][0][0] == "S60"                        # best riskadj
    assert ros["SPRINTER"][0][0] == "S1"                      # best mom12
    assert all(s != "ILLIQ" for s, _r, _x in ros["PACER"])    # gate held
    ranks = [rk for _s, rk, _x in ros["PACER"]]
    assert ranks == list(range(1, TOPN + 1))
    # pctrank import is live (used by callers/views for context columns)
    assert pctrank([1.0, 2.0])[1] == 1.0
    print("FACTOR_LEAGUE selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--refresh" in sys.argv:
        print("factor_league:", refresh())
    else:
        print(__doc__)
