"""market_internals — build the bounded market_internals_daily snapshot (deep-data sprint).

One row per trading day of ABSOLUTE market-health internals, computed from the raw archive:
  * price-breadth   — adv/dec/unch + % advancing        (bhavcopy_rows, series='EQ')
  * delivery        — market-wide avg delivery-%          (bhavcopy_rows)
  * dispersion      — winsorised cross-sectional stdev of returns (bhavcopy_rows)
  * the tape        — accum−distrib effort-breadth        (mep_signals.mep_state_smooth)
  * coil            — mean ATR-compression                (mep_signals.compression)

WHY a snapshot (not compute-on-read): a 22-year series would scan ~8M rows on every request.
The table is ~5.5k rows ever (one per trading day) — the space-optimization "bounded snapshot"
exception. Heavy reads go to TEMP tables so the main write-lock is held <1s. Idempotent full
rebuild via `backfill`; `refresh_tail` appends only new dates (for a nightly piggyback or a
lazy page refresh) without a full rescan. NO new timer is wired by this module.

Read surface: src/web/market_internals_view.py (/dash/market-internals). Descriptive only.
Run: python -m src.automation.market_internals [--backfill]
"""
from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_internals_daily (
  d        TEXT PRIMARY KEY,
  n_eq     INTEGER, adv INTEGER, dec INTEGER, unch INTEGER, pct_adv REAL,
  avg_dp   REAL, disp REAL,
  mep_n    INTEGER, mep_acc INTEGER, mep_dis INTEGER, mep_net REAL, avg_comp REAL,
  computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# breadth / delivery / dispersion from the EQ cash tape; `since` bounds the scan for tail refresh
_BREADTH = """
SELECT trade_date AS d, COUNT(*) AS n_eq,
       SUM(close>prev_close) AS adv, SUM(close<prev_close) AS dec, SUM(close=prev_close) AS unch,
       ROUND(100.0*SUM(close>prev_close)/COUNT(*),2) AS pct_adv,
       ROUND(AVG(deliv_per),2) AS avg_dp,
       ROUND(SQRT(MAX(AVG(w*w)-AVG(w)*AVG(w),0))*100,3) AS disp
FROM (
  SELECT trade_date, close, prev_close, deliv_per,
         MAX(-0.2, MIN(0.2, close/prev_close - 1.0)) AS w
  FROM bhavcopy_rows
  WHERE series='EQ' AND prev_close>0 AND close>0 {since}
) GROUP BY trade_date
"""

_MEP = """
SELECT trade_date AS d,
       SUM(mep_state_smooth IN ('ACCUM','STRONG_ACCUM')) AS mep_acc,
       SUM(mep_state_smooth IN ('DISTRIB','STRONG_DISTRIB')) AS mep_dis,
       SUM(mep_state_smooth<>'' AND mep_state_smooth IS NOT NULL) AS mep_n,
       ROUND(AVG(compression),4) AS avg_comp
FROM mep_signals {where} GROUP BY trade_date
"""


def _rows(conn: sqlite3.Connection, since: str | None):
    br_since = f"AND trade_date > '{since}'" if since else ""
    mep_where = f"WHERE trade_date > '{since}'" if since else ""
    br = {r[0]: r for r in conn.execute(_BREADTH.format(since=br_since)).fetchall()}
    mep = {r[0]: r for r in conn.execute(_MEP.format(where=mep_where)).fetchall()}
    out = []
    for d, b in br.items():
        m = mep.get(d)
        acc = m[1] if m else None
        dis = m[2] if m else None
        mn = m[3] if m else None
        net = round(100.0 * (acc - dis) / mn, 2) if (m and mn) else None
        out.append((d, b[1], b[2], b[3], b[4], b[5], b[6], b[7], mn, acc, dis, net, (m[4] if m else None)))
    return out


def _upsert(conn: sqlite3.Connection, rows: list) -> None:
    # rely on the connection's implicit transaction (executemany batches under one txn) +
    # commit — avoids nesting under the DELETE's already-open transaction in backfill().
    conn.executemany(
        "INSERT OR REPLACE INTO market_internals_daily "
        "(d,n_eq,adv,dec,unch,pct_adv,avg_dp,disp,mep_n,mep_acc,mep_dis,mep_net,avg_comp) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()


def backfill(conn: sqlite3.Connection) -> int:
    """Full idempotent rebuild over all history. Returns row count."""
    conn.executescript(_SCHEMA)
    rows = _rows(conn, since=None)
    conn.execute("DELETE FROM market_internals_daily")
    if rows:
        _upsert(conn, rows)
    return len(rows)


def refresh_tail(conn: sqlite3.Connection) -> int:
    """Append only dates newer than the current max(d) — cheap; for a nightly piggyback or
    lazy page refresh. Returns the number of new days added."""
    conn.executescript(_SCHEMA)
    cur = conn.execute("SELECT MAX(d) FROM market_internals_daily").fetchone()[0]
    rows = _rows(conn, since=cur)
    if rows:
        _upsert(conn, rows)
    return len(rows)


def _selftest() -> int:
    # in-memory: build tiny bhavcopy_rows + mep_signals, compute, assert one row lands
    conn = sqlite3.connect(":memory:")
    conn.row_factory = None
    conn.executescript(
        "CREATE TABLE bhavcopy_rows(symbol TEXT,trade_date TEXT,series TEXT,close REAL,"
        "prev_close REAL,deliv_per REAL);"
        "CREATE TABLE mep_signals(symbol TEXT,trade_date TEXT,mep_state_smooth TEXT,compression REAL);"
        "INSERT INTO bhavcopy_rows VALUES ('A','2020-01-01','EQ',110,100,60),"
        "('B','2020-01-01','EQ',90,100,40),('A','2020-01-02','EQ',115,110,55);"
        "INSERT INTO mep_signals VALUES ('A','2020-01-01','STRONG_ACCUM',0.9),"
        "('B','2020-01-01','DISTRIB',1.2),('A','2020-01-02','ACCUM',0.8);")
    n = backfill(conn)
    assert n == 2, n
    r = conn.execute("SELECT adv,dec,pct_adv,mep_net FROM market_internals_daily WHERE d='2020-01-01'").fetchone()
    assert r[0] == 1 and r[1] == 1 and abs(r[2] - 50.0) < 1e-6, r
    assert abs(r[3] - 0.0) < 1e-6, r  # 1 accum - 1 distrib over 2 = 0 net
    assert refresh_tail(conn) == 0  # nothing new
    print("market_internals selftest OK — breadth+tape compute; idempotent; tail no-op")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv or len(sys.argv) == 1:
        sys.exit(_selftest())
    if "--backfill" in sys.argv:
        from src.core.db import get_conn
        with get_conn() as c:
            print("market_internals_daily rows:", backfill(c))
