"""sector_book.py — the Sector-Rotation (V17) portfolio engine: book history + NAV.

Materialises the FROZEN V17 configuration (docs/strategies/sector-rotation.md §3; spec-of-
record code = research/explosive_moves/sector_rotation_exp2.py, mode DFILL) into two BOUNDED
tables so /dash/sector-rotation can time-travel the book without recomputing 21 years per
request:

  sector_rotation_book(rebal_date, sector, weight)   -- the QUARTERLY builds (~86 x ~3 rows)
  sector_rotation_nav(month_date, nav, nav_bench, invested, regime, turnover)
                                                     -- MONTHLY marks (~258 rows)

`regime` = the residual sleeve's monthly state: INDEX (bench >= its 200DMA -> residual in a
Nifty-500 ETF) or CASH (below -> residual waits). The sector book itself never reacts to it.

DESCRIPTIVE / RESEARCH-CONDITIONAL — the strategy-ledger (§§ 2026-07-15..15c) records the
verdict incl. every rejected lever (short leg, monthly cadence, book-level kill). Never a
recommendation. V8 = the same book WITHOUT the sleeve (residual in cash); the view derives
V8 context from `invested` if needed — only V17 NAV is persisted (the champion-candidate).

Contract: owns its two tables (CREATE IF NOT EXISTS here; db.py untouched — the
signal_alerts/wolfe isolation pattern). Pure stdlib. PIT-honest: signals at date d use
closes <= d; entries earn the NEXT month.

CLI:
  python -m src.automation.sector_book --build      # full rebuild (2005 -> today)
  python -m src.automation.sector_book --refresh    # clock-gated: rebuild only when a NEW
                                                    # quarter month-start exists (nightly-safe)
  python -m src.automation.sector_book --selftest
"""
from __future__ import annotations

import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore

BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START = "2005-01-03"
LB, CAP, BAND, COST = 126, 0.30, 0.08, 0.0015
RSPK_WIN, DMA = 756, 200

SCHEMA = """
CREATE TABLE IF NOT EXISTS sector_rotation_book (
    rebal_date TEXT NOT NULL,
    sector     TEXT NOT NULL,
    weight     REAL NOT NULL,
    PRIMARY KEY (rebal_date, sector)
);
CREATE TABLE IF NOT EXISTS sector_rotation_nav (
    month_date TEXT PRIMARY KEY,   -- the month-END mark (next rebal date)
    nav        REAL NOT NULL,      -- V17 NAV (1.0 at inception)
    nav_bench  REAL NOT NULL,      -- Nifty 500 price-index NAV, same base
    invested   REAL NOT NULL,      -- sector-book fraction at the month START
    regime     TEXT NOT NULL,      -- INDEX | CASH (the residual sleeve's state)
    turnover   REAL NOT NULL,      -- one-way |dw| traded at the month START
    computed_at TEXT
);
"""


class _Px:
    """Daily closes + calendar + the frozen signal set (mirrors the research module)."""

    def __init__(self, conn):
        self.close: dict = defaultdict(dict)
        names = SECTORS + [BENCH]
        q = ("SELECT index_name, trade_date, close_value FROM index_rows "
             "WHERE index_name IN (%s) AND close_value > 0" % ",".join("?" * len(names)))
        for nm, d, c in conn.execute(q, names):
            self.close[nm][d] = c
        self.cal = sorted(d for d in self.close[BENCH] if d >= START)
        self.idx = {d: i for i, d in enumerate(self.cal)}
        self.rebal, seen = [], set()
        for d in self.cal:
            if d[:7] not in seen:
                seen.add(d[:7]); self.rebal.append(d)

    def ret(self, nm, d0, d1):
        a, b = self.close[nm].get(d0), self.close[nm].get(d1)
        return (b / a - 1.0) if (a and b) else None

    def trailing(self, nm, d, lb=LB):
        i = self.idx.get(d)
        if i is None or i - lb < 0:
            return None
        d0 = self.cal[i - lb]
        if d0 in self.close[nm] and d in self.close[nm]:
            return self.close[nm][d] / self.close[nm][d0] - 1.0
        return None

    def series(self, nm, d, win):
        i = self.idx.get(d)
        if i is None:
            return []
        return [self.close[nm][self.cal[k]] for k in range(max(0, i - win + 1), i + 1)
                if self.cal[k] in self.close[nm]]

    def rs_line(self, nm, d, win):
        i = self.idx.get(d)
        if i is None:
            return []
        return [self.close[nm][self.cal[k]] / self.close[BENCH][self.cal[k]]
                for k in range(max(0, i - win + 1), i + 1)
                if self.cal[k] in self.close[nm] and self.cal[k] in self.close[BENCH]]


def _rsi(vals, n=14):
    if len(vals) < n + 1:
        return None
    g = l = 0.0
    for k in range(len(vals) - n, len(vals)):
        ch = vals[k] - vals[k - 1]
        g += max(ch, 0.0); l += max(-ch, 0.0)
    ag, al = g / n, l / n
    return 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)


def _pctile(x, arr):
    return (sum(1 for a in arr if a <= x) / len(arr)) if arr else None


def _taper(p, thr=0.85, floor=0.35):
    if p is None or p <= thr:
        return 1.0
    return max(floor, 1.0 - (p - thr) / (1 - thr) * (1 - floor))


def _cap_only(w, cap=CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap + 1e-9}
        if not over:
            break
        exc = sum(w[s] - cap for s in over)
        for s in over:
            w[s] = cap
        und = [s for s in w if w[s] < cap - 1e-9]
        tu = sum(w[s] for s in und) or 1.0
        for s in und:
            w[s] += exc * w[s] / tu
    return w


def _taper_product(px, s, d):
    f = 1.0
    line = px.rs_line(s, d, RSPK_WIN)
    f *= _taper(_pctile(line[-1], line) if len(line) > 60 else None)
    ser = px.series(s, d, 200)
    if len(ser) >= 150:
        m = sum(ser) / len(ser)
        sd = math.sqrt(sum((x - m) ** 2 for x in ser) / (len(ser) - 1))
        z = (ser[-1] - m) / sd if sd > 0 else 0.0
        f *= _taper(_pctile(z, [-2, -1, 0, 1, 1.5, 2, 2.5]), thr=0.7)
    r = _rsi(px.rs_line(s, d, 40))
    if r is not None:
        if r >= 80:
            f = 0.0
        elif r >= 70:
            f *= 0.5
    return f


def _build_book(px, d, held):
    rs = {}
    for s in SECTORS:
        tr, tb = px.trailing(s, d), px.trailing(BENCH, d)
        if tr is not None and tb is not None:
            rs[s] = tr - tb
    longs = {}
    for s, v in rs.items():
        if s in held:
            if v > -BAND:
                longs[s] = max(v, 1e-6)
        elif v > BAND:
            longs[s] = v
    keep = {}
    i = px.idx[d]
    dprev = px.cal[max(0, i - 21)]
    for s in longs:
        rn = _rsi(px.series(s, d, 40))
        rp = _rsi(px.series(s, dprev, 40))
        if s in held or (rn is not None and rn >= 50 and (rp is None or rn >= rp)):
            keep[s] = longs[s]
    if not keep:
        return {}
    base = _cap_only({s: 1.0 / len(keep) for s in keep})
    adj = {s: base[s] * _taper_product(px, s, d) for s in base}
    tot = sum(adj.values())
    if tot <= 0:
        return base
    return _cap_only({s: adj[s] / tot for s in adj})


def _regime_index(px, d):
    """True -> residual sleeve holds the index (bench >= 200DMA); False -> cash."""
    s = px.series(BENCH, d, DMA)
    return not (len(s) >= DMA and s[-1] < sum(s) / len(s))


def build(conn=None) -> str:
    if conn is None:
        with get_conn() as c:
            return build(c)
    conn.executescript(SCHEMA)
    px = _Px(conn)
    if len(px.rebal) < 24:
        return "insufficient index history"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev: dict = {}
    nav = 1.0
    nav_b = 1.0
    book_rows, nav_rows = [], []
    for k in range(len(px.rebal) - 1):
        d, dn = px.rebal[k], px.rebal[k + 1]
        if k % 3 == 0:
            w = _build_book(px, d, set(prev))
            for s, x in sorted(w.items()):
                book_rows.append((d, s, round(x, 6)))
        else:
            w = dict(prev)
        rb = px.ret(BENCH, d, dn) or 0.0
        on_index = _regime_index(px, d)
        inv = sum(w.values())
        if not w:
            rp = rb if on_index else 0.0
        else:
            rp = sum(x * (px.ret(s, d, dn) or 0.0) for s, x in w.items())
            if inv < 1.0 and on_index:
                rp += (1.0 - inv) * rb
        turn = 0.0
        if k % 3 == 0:
            allk = set(w) | set(prev)
            turn = sum(abs(w.get(s, 0.0) - prev.get(s, 0.0)) for s in allk)
            rp -= turn * COST
        nav *= (1 + rp)
        nav_b *= (1 + rb)
        nav_rows.append((dn, round(nav, 6), round(nav_b, 6), round(inv, 4),
                         "INDEX" if on_index else "CASH", round(turn, 4), now))
        prev = w
    with conn:  # atomic replace — a failed rebuild keeps the prior snapshot
        conn.execute("DELETE FROM sector_rotation_book")
        conn.execute("DELETE FROM sector_rotation_nav")
        conn.executemany("INSERT INTO sector_rotation_book VALUES (?,?,?)", book_rows)
        conn.executemany("INSERT INTO sector_rotation_nav VALUES (?,?,?,?,?,?,?)", nav_rows)
    return (f"built: {len(set(r[0] for r in book_rows))} rebalances, "
            f"{len(nav_rows)} nav months, latest {nav_rows[-1][0]} nav {nav_rows[-1][1]:.2f}")


def refresh(conn=None) -> str:
    """Nightly-safe: full rebuild only when a NEW quarter month-start has appeared."""
    if conn is None:
        with get_conn() as c:
            return refresh(c)
    conn.executescript(SCHEMA)
    px = _Px(conn)
    q_dates = [px.rebal[k] for k in range(0, max(0, len(px.rebal) - 1), 3)]
    want = q_dates[-1] if q_dates else None
    have = conn.execute("SELECT MAX(rebal_date) d FROM sector_rotation_book").fetchone()
    have_d = have[0] if have else None
    if want and have_d == want:
        return f"clock unchanged (latest rebalance {want})"
    return build(conn)


def _selftest() -> int:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE index_rows (index_name TEXT, trade_date TEXT, close_value REAL)")
    # 3 years of synthetic dailies: bench flat-ish drift; sector A strongly beats; B lags.
    import datetime as _dt
    d0 = _dt.date(2005, 1, 3)
    rows = []
    day = 0
    while day < 780:
        dt = d0 + _dt.timedelta(days=day * 7 // 5)      # ~weekday spacing
        ds = dt.isoformat()
        rows.append((BENCH, ds, 100 * (1.0003 ** day)))
        rows.append(("Nifty IT", ds, 100 * (1.0012 ** day)))
        rows.append(("Nifty FMCG", ds, 100 * (0.9998 ** day)))
        day += 1
    conn.executemany("INSERT INTO index_rows VALUES (?,?,?)", rows)
    out = build(conn)
    assert out.startswith("built:"), out
    bk = conn.execute("SELECT COUNT(DISTINCT rebal_date), COUNT(*) FROM sector_rotation_book").fetchone()
    assert bk[0] >= 4 and bk[1] >= 4, bk
    w = [r[0] for r in conn.execute("SELECT weight FROM sector_rotation_book")]
    assert all(0 < x <= CAP + 1e-6 for x in w), "cap violated"
    it = conn.execute("SELECT COUNT(*) FROM sector_rotation_book WHERE sector='Nifty IT'").fetchone()[0]
    lag = conn.execute("SELECT COUNT(*) FROM sector_rotation_book WHERE sector='Nifty FMCG'").fetchone()[0]
    assert it > 0 and lag == 0, (it, lag)               # the leader is held, the laggard never enters
    nv = conn.execute("SELECT COUNT(*), MIN(nav), MAX(regime), MIN(regime) FROM sector_rotation_nav").fetchone()
    assert nv[0] >= 20 and nv[1] > 0, nv
    assert refresh(conn).startswith("clock unchanged"), "refresh must be clock-gated"
    print(f"sector_book selftest OK — {bk[0]} rebalances, {nv[0]} nav months, cap+gate+clock hold")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    elif "--build" in sys.argv:
        print("sector_book:", build())
    elif "--refresh" in sys.argv:
        print("sector_book:", refresh())
    else:
        print(__doc__)
