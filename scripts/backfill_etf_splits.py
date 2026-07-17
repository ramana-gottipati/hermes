"""Back-fill NSE gold-ETF unit subdivisions into ``corporate_actions`` (data-quality gap-fill).

WHY THIS EXISTS
---------------
``src/automation/corp_actions.py`` ingests the NSE corporate-actions API with
``index=equities``.  That feed structurally OMITS the ETF instrument class, so
every gold-ETF **unit subdivision** (the ETF analogue of a face-value split) is
absent from ``corporate_actions`` — verified on the box: GOLDBEES had 0 rows.

The adjustment pipelines key off that table:

  * ``research/explosive_moves/adjust.py`` ``load_factors`` reads ONLY
    ``corporate_actions`` (no observed-jump fallback) → a missing subdivision
    leaves the series fully RAW.  GOLDBEES then prints a fake ~-99% quarter and a
    nonsense native CAGR of -16.9% (vs the correct ~+11.9%).  This is the path the
    S180 gold-leg probe (docs/portfolio-layer-design.md §7c, ledger 2026-07-16AP)
    tripped over — and the reason this back-fill was spawned.
  * ``src/automation/adjust.py`` (production charts/RS) has an observed-jump
    fallback, BUT its ``0.02 < ratio < 50`` guard EXCLUDES 100:1 (r=0.01) and 50:1
    (r=0.02) subdivisions; only 10:1 (r=0.10) self-corrects there.  (Adding rows
    here does NOT reach that path today — no production consumer wires the tape;
    that gap is disclosed separately, not fixed by this seed.)

THE DATA (primary-source, Guardrail #8-clean)
---------------------------------------------
Every ratio + ex-date below is derived from the authentic NSE **bhavcopy** price
series (the exchange's own record of the ex-day price step), detected with the
generic single-day ratio jump

    WITH s AS (SELECT trade_date, close,
                      LAG(close) OVER (ORDER BY trade_date) pc
               FROM bhavcopy_rows WHERE symbol=? AND series IN ('EQ','BE','BZ'))
    SELECT trade_date, pc, close, close/pc r FROM s WHERE r<0.5 OR r>2.0;

and cross-validated two ways: (a) the rounded ratio leaves a <~2% residual
discontinuity across the ex-day (the rest is that day's real gold move); (b) for
the one illiquid oddball (AXISGOLD, whose day-1 print carried an +18% premium) the
factor was pinned against GOLDBEES as a same-date reference — AXISGOLD/GOLDBEES ran
99.5 pre-split and settled to ~0.99 post-split → 100:1.  The ratios land on the
standard Indian gold-ETF subdivision grid (100:1, 50:1, 10:1).

Idempotent: rows go through ``corp_actions.store_actions`` (``INSERT ... ON
CONFLICT(symbol, action_type, ex_date, details) DO NOTHING``).  Re-running inserts
0.  The ``details`` string is FROZEN — never edit it, or a re-run would create a
second SPLIT row on the same ex-date and the research ``load_factors`` (which does
not de-dupe by ex-date) would DOUBLE-adjust.

Usage (run with the box research venv from the repo root):
    python scripts/backfill_etf_splits.py --selftest      # offline, no DB, no network
    python scripts/backfill_etf_splits.py --dry-run       # show rows + remaining gaps vs the live DB
    python scripts/backfill_etf_splits.py --apply         # writer-safe insert into hermes.db
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sqlite3
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# ── the verified subdivisions ────────────────────────────────────────────────
# (symbol, ex_date, ratio_from, ratio_to)  — SPLIT factor = ratio_from/ratio_to
#   research load_factors:  f = rf/rt  → pre-ex closes divided by f
#   comment shows the ex-day bhavcopy step (prev close -> first post-split close)
GOLD_ETF_SPLITS = [
    ("GOLDBEES",   "2019-12-19", 100, 1),   # 3359.60 -> 33.55   (res 0.1%)
    ("AXISGOLD",   "2020-07-23", 100, 1),   # 4367.10 -> ~46     (day1 52.35 premium; cross-ETF vs GOLDBEES 99.5->0.99)
    ("HDFCMFGETF", "2021-02-17", 100, 1),   # 4242.00 -> 41.80   (res 1.5%)
    ("GOLDSHARE",  "2021-03-25", 100, 1),   # 4041.80 -> 40.45   (res 0.1%)
    ("BSLGOLDETF", "2021-11-25", 100, 1),   # 4348.65 -> 43.65   (res 0.4%)
    ("SETFGOLD",   "2022-01-06", 100, 1),   # 4259.95 -> 42.35   (res 0.6%)
    ("LICMFGOLD",  "2026-03-06", 100, 1),   # 14401.80 -> 143.20 (res 0.6%)
    ("IVZINGOLD",  "2026-04-30", 100, 1),   # 12782.95 -> 130.25 (res 1.9%)
    ("QGOLDHALF",  "2021-12-16",  50, 1),   # 2062.45 -> 41.75   (49.4 -> 50)
    ("KOTAKGOLD",  "2015-04-13",  10, 1),   # 2432.45 -> 254.90  (settles ~10)
    ("IGOLD",      "2016-06-09",  10, 1),   # 2739.00 -> 288.35  (day1 premium; settles ~9.9)
    ("ICICIGOLD",  "2018-11-15",  10, 1),   # 278.55 -> 28.45    (res ~2%)
    ("KOTAKGOLD",  "2021-07-22",  10, 1),   # 419.35 -> 41.75    (res 0.4%)
    ("GROWWGOLD",  "2026-02-06",  10, 1),   # 149.72 -> 14.81    (res 1.1%)
]

SOURCE_TAG = "nse-bhav-derived-etf-split"


def _details(rf: int, rt: int) -> str:
    """FROZEN idempotency key component — do not edit (see module docstring)."""
    return (f"ETF unit subdivision {rf}:{rt} (NSE bhavcopy-derived; "
            f"equities corporate-actions feed omits ETF instrument class)")


def build_rows() -> list[dict]:
    """The verified subdivisions as ``store_actions``-shaped row dicts. Pure."""
    rows = []
    for sym, ex, rf, rt in GOLD_ETF_SPLITS:
        rows.append({
            "symbol": sym, "action_type": "SPLIT", "ex_date": ex,
            "record_date": None, "ratio_from": float(rf), "ratio_to": float(rt),
            "details": _details(rf, rt), "source": SOURCE_TAG,
        })
    return rows


# ── the live-DB write side (lazy imports so --selftest needs no deps) ─────────

def _connect_hermes():
    from src.core.db import get_conn
    return get_conn()


def dry_run() -> int:
    """Show the rows and, against the live DB, which subdivisions are still gaps."""
    rows = build_rows()
    print(f"backfill_etf_splits: {len(rows)} verified gold-ETF subdivisions\n")
    with _connect_hermes() as conn:
        still_missing = 0
        for r in rows:
            n = conn.execute(
                "SELECT COUNT(*) FROM corporate_actions WHERE symbol=? AND action_type='SPLIT' "
                "AND ex_date=?", (r["symbol"], r["ex_date"])).fetchone()[0]
            state = "PRESENT" if n else "GAP"
            still_missing += 0 if n else 1
            print(f"  {state:8} {r['symbol']:11} {r['ex_date']}  "
                  f"{int(r['ratio_from'])}:{int(r['ratio_to'])}")
        print(f"\n  {still_missing}/{len(rows)} still missing from corporate_actions")
    return 0


def apply() -> int:
    """Idempotent insert into hermes.db via the canonical store path."""
    from src.automation.corp_actions import store_actions
    rows = build_rows()
    with _connect_hermes() as conn:
        before = conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
        inserted = store_actions(rows, conn=conn)
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
    print(f"backfill_etf_splits: inserted {inserted} row(s) "
          f"(table {before} -> {after}); {len(rows) - inserted} already present")
    return 0


# ── offline selftest (no network, no real DB) ────────────────────────────────

_CA_SCHEMA = """
CREATE TABLE corporate_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, action_type TEXT NOT NULL,
  ex_date TEXT, record_date TEXT, ratio_from REAL, ratio_to REAL, details TEXT, source TEXT,
  fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(symbol, action_type, ex_date, details));
"""


def _load_research_adjust():
    """Import research/explosive_moves/adjust.py (the load_factors path) by path."""
    path = os.path.join(REPO_ROOT, "research", "explosive_moves", "adjust.py")
    spec = importlib.util.spec_from_file_location("research_adjust", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    rows = build_rows()
    check("14 verified subdivisions", len(rows) == 14)
    check("all SPLIT with rf/rt>0", all(r["action_type"] == "SPLIT" and r["ratio_from"] > 0
                                        and r["ratio_to"] > 0 for r in rows))
    check("details carry no re-parse triggers (bonus/merg/scheme/deb)",
          all(not any(k in r["details"].lower() for k in ("bonus", "merg", "scheme", "deb"))
              for r in rows))

    # raw-SQL round-trip (no corp_actions import → no requests dependency)
    con = sqlite3.connect(":memory:")
    con.executescript(_CA_SCHEMA)
    ins = ("INSERT INTO corporate_actions (symbol,action_type,ex_date,record_date,"
           "ratio_from,ratio_to,details,source) VALUES (?,?,?,?,?,?,?,?) "
           "ON CONFLICT(symbol,action_type,ex_date,details) DO NOTHING")

    def store(rs):
        c = 0
        for r in rs:
            cur = con.execute(ins, (r["symbol"], r["action_type"], r["ex_date"], r["record_date"],
                                    r["ratio_from"], r["ratio_to"], r["details"], r["source"]))
            c += max(cur.rowcount, 0)
        con.commit()
        return c

    n1, n2 = store(rows), store(rows)
    check("idempotent insert (14 then 0)", n1 == 14 and n2 == 0)
    check("two KOTAKGOLD rows coexist (distinct ex_date)",
          con.execute("SELECT COUNT(*) FROM corporate_actions WHERE symbol='KOTAKGOLD'").fetchone()[0] == 2)

    # research load_factors reads the rows → correct factors
    radj = _load_research_adjust()
    fac = radj.load_factors(con)
    check("GOLDBEES factor = 100", "GOLDBEES" in fac and abs(fac["GOLDBEES"][0][1] - 100.0) < 1e-9)
    check("QGOLDHALF factor = 50", abs(fac["QGOLDHALF"][0][1] - 50.0) < 1e-9)
    check("KOTAKGOLD has 2 factors", len(fac["KOTAKGOLD"]) == 2)

    # THE POINT: adjust_closes makes the GOLDBEES ex-day continuous (no fake cliff)
    closes = {"2019-12-18": 3359.6, "2019-12-19": 33.55, "2019-12-20": 33.65}
    adj = radj.adjust_closes(closes, fac["GOLDBEES"])
    check("pre-split close divided by 100 (3359.6 -> ~33.60)", abs(adj["2019-12-18"] - 33.596) < 1e-3)
    check("on/after ex-date unchanged (anchor)", adj["2019-12-19"] == 33.55 and adj["2019-12-20"] == 33.65)
    step = adj["2019-12-19"] / adj["2019-12-18"]
    check("adjusted ex-day step is continuous (|1-step|<3%)", abs(step - 1) < 0.03)
    con.close()

    print("backfill_etf_splits selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Back-fill NSE gold-ETF unit subdivisions into corporate_actions")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest", action="store_true", help="offline synthetic proof (no DB, no network)")
    g.add_argument("--dry-run", action="store_true", help="show rows + remaining gaps vs the live DB")
    g.add_argument("--apply", action="store_true", help="idempotent insert into hermes.db")
    args = p.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    if args.dry_run:
        raise SystemExit(dry_run())
    raise SystemExit(apply())


if __name__ == "__main__":
    main()
