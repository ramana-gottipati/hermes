"""Machine-generated table census — D91 made operational (data-postmortem 2026-07-05).

WHY: every hand-carried coverage number drifts. The postmortem found the estate briefing
inflated up to 588x because counts were MAX(rowid)-derived (INSERT OR REPLACE burns rowids)
and then quoted from memory: ratio_rows "286M" was 486K live; concalls "75.9K" was 24K.
D91 ruled (a) census by COUNT(*) only, (b) trust surfaces quote a MACHINE snapshot, never a
typed figure. This module IS that snapshot.

WHAT: one row per (census_date, db, table) — COUNT(*) + a best-effort as-of boundary
(min/max of the table's most date-like column) — for BOTH hermes.db and research.db,
written into hermes.db `table_census`. ~120 tiny rows/day (KB-scale; the D93
bounded-snapshot class, deliberately kept as HISTORY so day-over-day deltas can alarm:
a sudden table shrink is the truncation/purge signature the census exists to catch).

WHO RUNS IT: the nightly data_quality battery (persist=True path) takes the census before
its checks; `chk_table_census` then alarms on staleness + >20% day-over-day shrinkage.

CLI:
  python -m src.automation.table_census --run          # census both DBs now
  python -m src.automation.table_census --show [-n 30] # latest census, biggest first
  python -m src.automation.table_census --selftest
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
from datetime import date
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.table_census")

RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

_DDL = """
CREATE TABLE IF NOT EXISTS table_census (
    census_date TEXT NOT NULL,
    db          TEXT NOT NULL,
    table_name  TEXT NOT NULL,
    row_count   INTEGER,
    asof_col    TEXT,
    min_asof    TEXT,
    max_asof    TEXT,
    captured_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (census_date, db, table_name)
);
CREATE INDEX IF NOT EXISTS idx_census_table ON table_census(db, table_name, census_date);
"""

# the census's own bookkeeping is not DATA — skip it (and sqlite internals)
_SKIP = ("table_census",)

# boundary-column preference: explicit event/series clocks first, generic *_at last
# (created_at/parsed_at are ingest clocks, still better than nothing)
_COL_PRIORITY = ("trade_date", "as_of", "period_end", "period_end_date", "ex_date",
                 "broadcast_dt", "disclosure_dt", "snapshot_date", "meeting_date",
                 "rating_date", "launch_date", "census_date", "as_of_date", "report_date")
_COL_GENERIC = re.compile(r"(date|_dt|_at)$", re.IGNORECASE)


def _asof_col(cols: list) -> Optional[str]:
    low = {c.lower(): c for c in cols}
    for want in _COL_PRIORITY:
        if want in low:
            return low[want]
    for c in cols:
        if _COL_GENERIC.search(c):
            return c
    return None


def _census_one_db(conn: sqlite3.Connection, dbname: str, today: str) -> list:
    """[(census_date, db, table, count, asof_col, min, max)] for every user table."""
    out = []
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name")]
    for t in tables:
        if t in _SKIP:
            continue
        try:
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]   # D91: never MAX(rowid)
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
            ac = _asof_col(cols)
            lo = hi = None
            if ac and n:
                lo, hi = conn.execute(
                    f'SELECT MIN("{ac}"), MAX("{ac}") FROM "{t}"').fetchone()
                lo = str(lo)[:19] if lo is not None else None
                hi = str(hi)[:19] if hi is not None else None
            out.append((today, dbname, t, n, ac, lo, hi))
        except sqlite3.Error as e:
            log.warning("census %s.%s failed: %s", dbname, t, e)
            out.append((today, dbname, t, None, None, None, None))
    return out


def run_census(conn, *, research_db: Optional[str] = None, today: Optional[str] = None) -> dict:
    """Take today's census of the given hermes connection + the research DB (read-only,
    graceful if absent) and upsert into hermes.table_census. Never raises past a per-table
    failure; a same-day rerun refreshes in place (PK upsert)."""
    conn.executescript(_DDL)
    today = today or date.today().isoformat()
    rows = _census_one_db(conn, "hermes", today)
    rpath = research_db if research_db is not None else RESEARCH_DB
    n_research = 0
    if rpath and os.path.exists(rpath):
        try:
            rconn = sqlite3.connect(f"file:{rpath}?mode=ro", uri=True, timeout=20)
            try:
                rrows = _census_one_db(rconn, "research", today)
                rows += rrows
                n_research = len(rrows)
            finally:
                rconn.close()
        except sqlite3.Error as e:  # research locked/absent — census hermes anyway
            log.warning("research census skipped: %s", e)
    conn.executemany(
        "INSERT OR REPLACE INTO table_census "
        "(census_date, db, table_name, row_count, asof_col, min_asof, max_asof) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    stats = {"census_date": today, "tables": len(rows), "hermes": len(rows) - n_research,
             "research": n_research}
    log.info("table_census: %s", stats)
    return stats


# ── read side ─────────────────────────────────────────────────────────────────

def latest_dates(conn, n: int = 2) -> list:
    try:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT census_date FROM table_census ORDER BY census_date DESC LIMIT ?",
            (n,))]
    except sqlite3.Error:
        return []


def shrunk_tables(conn, *, pct: float = 0.20, floor: int = 500) -> list:
    """Tables whose latest census count dropped > pct vs the previous census day —
    the truncation/purge signature. Ignores small tables (< floor rows previously)."""
    days = latest_dates(conn, 2)
    if len(days) < 2:
        return []
    cur, prev = days[0], days[1]
    return [f"{r[0]}.{r[1]} {r[3]}→{r[2]}" for r in conn.execute(
        """SELECT a.db, a.table_name, a.row_count, b.row_count
           FROM table_census a JOIN table_census b
             ON b.db=a.db AND b.table_name=a.table_name AND b.census_date=?
           WHERE a.census_date=? AND b.row_count >= ? AND a.row_count IS NOT NULL
             AND a.row_count < (1.0 - ?) * b.row_count""",
        (prev, cur, floor, pct))]


# ── selftest (offline, synthetic) ────────────────────────────────────────────

def _selftest() -> int:
    import tempfile

    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, close REAL);
        CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT);
        INSERT INTO bhavcopy_rows VALUES ('A','2024-01-01',1),('A','2026-07-01',2);
        INSERT INTO notes (body) VALUES ('x');
    """)
    with tempfile.TemporaryDirectory() as td:
        rdb = os.path.join(td, "research.db")
        rc = sqlite3.connect(rdb)
        rc.executescript("CREATE TABLE fundamentals_history (symbol TEXT, report_date TEXT, value REAL);"
                         "INSERT INTO fundamentals_history VALUES ('A','2020-05-01',1.0);")
        rc.commit(); rc.close()

        s1 = run_census(con, research_db=rdb, today="2026-07-01")
        check("censused both DBs", s1["hermes"] == 2 and s1["research"] == 1)
        row = con.execute("SELECT row_count, asof_col, min_asof, max_asof FROM table_census "
                          "WHERE db='hermes' AND table_name='bhavcopy_rows'").fetchone()
        check("COUNT(*) + boundary via trade_date",
              row == (2, "trade_date", "2024-01-01", "2026-07-01"))
        check("no-date table gets NULL boundary", con.execute(
            "SELECT asof_col FROM table_census WHERE table_name='notes'").fetchone()[0] is None)
        check("research row present", con.execute(
            "SELECT row_count FROM table_census WHERE db='research' "
            "AND table_name='fundamentals_history'").fetchone()[0] == 1)
        # same-day rerun refreshes in place (no dup PK explosion)
        run_census(con, research_db=rdb, today="2026-07-01")
        check("same-day rerun idempotent", con.execute(
            "SELECT COUNT(*) FROM table_census WHERE census_date='2026-07-01'").fetchone()[0] == 3)
        # day 2: bhavcopy shrinks 50% (>20%, prev>=floor? prev=2 < floor 500 → NOT flagged);
        # use a big synthetic to exercise the alarm properly
        con.execute("CREATE TABLE big (d TEXT)")
        con.executemany("INSERT INTO big VALUES (?)", [("2026-01-01",)] * 1000)
        run_census(con, research_db=rdb, today="2026-07-02")
        con.execute("DELETE FROM big WHERE rowid % 2 = 0")               # 50% purge
        run_census(con, research_db=rdb, today="2026-07-03")
        sh = shrunk_tables(con)
        check("shrink alarm fires for the purged big table",
              len(sh) == 1 and sh[0].startswith("hermes.big 1000→500"))
        check("small-table churn ignored (floor)", not any("notes" in x or "bhavcopy" in x for x in sh))
        check("absent research db degrades", run_census(
            sqlite3.connect(":memory:"), research_db=os.path.join(td, "nope.db"),
            today="2026-07-01")["research"] == 0)
    con.close()
    print("table_census selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Machine table census (D91): COUNT(*) + as-of boundaries, both DBs")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--show", action="store_true", help="latest census, biggest tables first")
    ap.add_argument("-n", type=int, default=30)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    with get_conn() as conn:
        if args.run:
            run_census(conn)
        if args.show or args.run:
            days = latest_dates(conn, 1)
            if not days:
                print("no census yet — run with --run")
                return
            print(f"census {days[0]} (biggest first):")
            for r in conn.execute(
                    "SELECT db, table_name, row_count, asof_col, min_asof, max_asof "
                    "FROM table_census WHERE census_date=? ORDER BY COALESCE(row_count,0) DESC LIMIT ?",
                    (days[0], args.n)):
                print(f"  {r[0]:8s} {r[1]:34s} {r[2] if r[2] is not None else '?':>10}  "
                      f"{(r[3] or '-'):18s} {(r[4] or '')[:10]} .. {(r[5] or '')[:10]}")
        if not (args.run or args.show):
            ap.error("give --run, --show or --selftest")


if __name__ == "__main__":
    main()
