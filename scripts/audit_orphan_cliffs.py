"""Full-history orphan-cliff audit + CLEAN-only heal (S185, ledger 16AU; task_74bd9558).

THE HOLE (quantified by S184/16AT): ~184 corporate-action-shaped price cliffs across the whole
bhavcopy archive have NO matching `corporate_actions` row — modern ETF unit subdivisions (the
16AQ class: NSE's equities CA feed omits the ETF instrument class) plus old EQUITY splits that
predate the CA feed's coverage. Consequences on record: `adjust.py` consumers see fake −75..−99%
days where factors are missing, and `research/explosive_moves/quarantine.py` silently EXCLUDES
many of these names (lost universe). The nightly `chk_split_cliffs` guard (S184) only watches a
~120-day rolling window — this script is the one-time historical remediation instrument.

METHOD — evidence battery per candidate cliff (prev_close ≥ ₹100, close ≤ 25% of prev, traded
value on both days, no CA row within ±5d):
  E1 canonical-ratio fit : r = prev/close within ±6% of one of {4,5,8,10,20,25,50,100}
                           (a subdivision lands on a face-value ratio; a crash lands anywhere —
                           the ±6% absorbs a normal market day at the new level)
  E2 persistence         : median of the NEXT 5 closes within [0.85, 1.15] × the cliff close
                           (a subdivision HOLDS the new level; a bad row snaps back)
  E3 longevity           : ≥ 20 further trading sessions for the symbol
                           (a terminal-collapse-then-delist event is not a subdivision)
  E4 value continuity    : cliff-day traded value ≤ 5× the trailing-10-session median and > 0
                           (a panic crash trades 10-30× normal VALUE; a subdivision does not —
                           units jump ~ratio×, rupee value stays ordinary)
CLEAN  = E1..E4 all pass → healable, ratio = the fitted canonical c:1.
AMBIGUOUS = any fail   → REPORTED ONLY, never healed (a wrong ratio corrupts worse than a
missing one — per-event human/archive verification owed; prefer NSE's official historical CA
archive for old equities).

The tape-derived basis follows the accepted S182 precedent (SOURCE_TAG "nse-bhav-derived-…",
ledger 16AQ): the bhavcopy itself is the primary source. Inserts go through the canonical
`store_actions` path, idempotent via the frozen details text below.

⚠ BINDING FOLLOW-THROUGH (16AS loop): applying this heal CHANGES adjusted history and can
change research universes (quarantine un-exclusion) → re-derive the sealed-ladder gate anchors
via `research/explosive_moves/union_forward.py --derive-anchors` + a new ledger entry in the
SAME arc, and re-check `portfolio_mix.py`'s load gates.

Usage:
    python scripts/audit_orphan_cliffs.py --selftest            # offline synthetic proof
    python scripts/audit_orphan_cliffs.py [DB] [--csv out.csv]  # audit + report (read-only)
    python scripts/audit_orphan_cliffs.py [DB] --apply          # heal CLEAN events (idempotent)
"""
from __future__ import annotations

import os
import sqlite3
import statistics
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

CANON = (4.0, 5.0, 8.0, 10.0, 20.0, 25.0, 50.0, 100.0)
RATIO_TOL = 0.06          # E1
PERSIST_BAND = (0.85, 1.15)  # E2, median of next 5 closes vs cliff close
MIN_AFTER = 20            # E3
VALUE_SPIKE_MAX = 5.0     # E4, cliff-day value vs trailing-10 median
SOURCE_TAG = "nse-bhav-derived-split-audit"


def _details(rf: int, rt: int) -> str:
    """FROZEN idempotency key component for this audit's inserts — do not edit."""
    return (f"Unit/share subdivision {rf}:{rt} (NSE bhavcopy-derived; S185 full-history "
            f"orphan-cliff audit, ledger 16AU)")


def classify(closes, values, i):
    """Evidence battery at index i (the cliff day) of a symbol's ordered (close, value) series.
    Returns (verdict, canon_ratio_or_None, tags)."""
    prev_c = closes[i - 1]
    c = closes[i]
    tags = []
    r = prev_c / c
    fit = min(CANON, key=lambda k: abs(r / k - 1.0))
    if abs(r / fit - 1.0) > RATIO_TOL:
        tags.append(f"E1-ratio {r:.2f} not canonical")
        fit = None
    nxt = closes[i + 1:i + 6]
    if len(nxt) >= 3:
        med = statistics.median(nxt)
        if not (PERSIST_BAND[0] <= med / c <= PERSIST_BAND[1]):
            tags.append(f"E2-no-persist med5 {med / c:.2f}x")
    else:
        tags.append("E2-tail too short to confirm")
    if len(closes) - 1 - i < MIN_AFTER:
        tags.append(f"E3-only {len(closes) - 1 - i} sessions after")
    base = [v for v in values[max(0, i - 10):i] if v]
    if base:
        spike = (values[i] or 0) / statistics.median(base)
        if spike > VALUE_SPIKE_MAX:
            tags.append(f"E4-value-spike {spike:.1f}x")
    return ("CLEAN" if fit and not tags else "AMBIGUOUS"), fit, tags


def audit(conn):
    """Sweep the whole tape; return (clean_rows, ambiguous)."""
    cur = conn.execute(
        "SELECT symbol, trade_date, close, value FROM bhavcopy_rows "
        "WHERE series IN ('EQ','BE','BZ') AND close > 0 ORDER BY symbol, trade_date")
    clean, ambiguous = [], []

    def flush(sym, dates, closes, values):
        for i in range(1, len(closes)):
            if closes[i - 1] >= 100 and closes[i] <= 0.25 * closes[i - 1] \
                    and (values[i - 1] or 0) > 0 and (values[i] or 0) > 0:
                covered = conn.execute(
                    "SELECT 1 FROM corporate_actions WHERE symbol=? "
                    "AND ex_date BETWEEN date(?, '-5 day') AND date(?, '+5 day') LIMIT 1",
                    (sym, dates[i], dates[i])).fetchone()
                if covered:
                    continue
                verdict, fit, tags = classify(closes, values, i)
                row = (sym, dates[i], closes[i - 1], closes[i], fit, "; ".join(tags))
                (clean if verdict == "CLEAN" else ambiguous).append(row)

    sym_p, dates, closes, values = None, [], [], []
    for sym, d, c, v in cur:
        if sym != sym_p:
            if sym_p is not None:
                flush(sym_p, dates, closes, values)
            sym_p, dates, closes, values = sym, [], [], []
        dates.append(d); closes.append(c); values.append(v)
    if sym_p is not None:
        flush(sym_p, dates, closes, values)
    return clean, ambiguous


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    db = args[0] if args else "data/hermes.db"
    apply_ = "--apply" in sys.argv
    csv_path = None
    if "--csv" in sys.argv:
        csv_path = sys.argv[sys.argv.index("--csv") + 1]
    conn = sqlite3.connect(db)
    clean, ambiguous = audit(conn)
    print(f"orphan-cliff audit: {len(clean)} CLEAN (healable) + {len(ambiguous)} AMBIGUOUS "
          f"(report-only) = {len(clean) + len(ambiguous)} total")
    for tag, rows in (("CLEAN", clean), ("AMBIGUOUS", ambiguous)):
        by_era = {}
        for r in rows:
            by_era[r[1][:4]] = by_era.get(r[1][:4], 0) + 1
        print(f"  {tag} by year: " + " ".join(f"{y}:{n}" for y, n in sorted(by_era.items())))
    if csv_path:
        import csv as _csv
        with open(csv_path, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["verdict", "symbol", "ex_date", "prev_close", "close", "canon", "tags"])
            for r in clean:
                w.writerow(["CLEAN", *r])
            for r in ambiguous:
                w.writerow(["AMBIGUOUS", *r])
        print(f"  full table -> {csv_path}")
    for r in ambiguous[:15]:
        print("   AMB", r[0], r[1], f"{r[2]:.0f}->{r[3]:.2f}", "|", r[5])
    if not apply_:
        print("dry-run (audit only) — pass --apply to heal the CLEAN set")
        conn.close()
        return 0
    conn.close()
    from src.core.db import get_conn
    from src.automation.corp_actions import store_actions
    rows = [{
        "symbol": sym, "action_type": "SPLIT", "ex_date": ex,
        "record_date": None, "ratio_from": float(fit), "ratio_to": 1.0,
        "details": _details(int(fit), 1), "source": SOURCE_TAG,
    } for sym, ex, _pc, _c, fit, _t in clean]
    with get_conn() as wconn:
        before = wconn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
        inserted = store_actions(rows, conn=wconn)
        wconn.commit()
        after = wconn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
    print(f"healed {inserted} CLEAN event(s) (table {before} -> {after}); "
          f"{len(rows) - inserted} already present; {len(ambiguous)} AMBIGUOUS left untouched")
    return 0


def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE bhavcopy_rows (symbol TEXT, series TEXT, trade_date TEXT, "
              "close REAL, value REAL)")
    c.execute("CREATE TABLE corporate_actions (symbol TEXT, action_type TEXT, ex_date TEXT)")

    def series(sym, spec):
        for n, (d, px, val) in enumerate(spec):
            c.execute("INSERT INTO bhavcopy_rows VALUES (?,?,?,?,?)", (sym, "EQ", d, px, val))

    from datetime import date, timedelta
    _epoch = date(2024, 1, 1)

    def days(start_m, n, px, val=5e7, step=0.0):
        return [((_epoch + timedelta(days=start_m + i)).isoformat(), px * (1 + step * i), val)
                for i in range(n)]

    # (a) clean 10:1 subdivision: 500 -> 50, holds, normal value, long tail
    series("CLEANSPLIT", days(0, 30, 500) + days(30, 40, 50))
    # (b) Satyam-shaped crash: 179 -> 40 (ratio 4.48, off-canonical) + 20x value spike
    series("CRASHCO", days(0, 30, 179) + days(30, 1, 40.0, val=1e9) + days(31, 40, 38))
    # (c) one-day glitch: 300 -> 30 for a single day, snaps back
    series("GLITCHCO", days(0, 30, 300) + days(30, 1, 30.0) + days(31, 40, 300))
    # (d) covered split: 400 -> 40 with a CA row present
    series("COVERED", days(0, 30, 400) + days(30, 40, 40))
    c.execute("INSERT INTO corporate_actions VALUES ('COVERED','SPLIT',?)",
              (days(30, 1, 40)[0][0],))
    c.commit()
    clean, ambiguous = audit(c)
    cs = {r[0] for r in clean}
    as_ = {r[0] for r in ambiguous}
    check("clean 10:1 classified CLEAN", "CLEANSPLIT" in cs)
    check("crash (off-canonical + value spike) AMBIGUOUS", "CRASHCO" in as_)
    check("one-day glitch AMBIGUOUS (no persistence)", "GLITCHCO" in as_)
    check("covered split not a candidate at all", "COVERED" not in cs | as_)
    check("clean row carries canonical 10", any(r[0] == "CLEANSPLIT" and r[4] == 10.0 for r in clean))
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
