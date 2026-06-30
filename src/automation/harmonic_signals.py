"""Harmonic scanner + nightly-persisted feed (D72 — the harmonic lane).

Mirrors the Wolfe scanner shape (wolfe.winner_scan / persist_scan): detect FRESH harmonic
setups across the universe — both CONFIRMED (point D just printed → a reversal candidate)
and FORMING (X-A-B-C printed, D projected into a PRZ → "catch it forming, down the
stream") — and materialise them into a `harmonic_signals` table this module OWNS (CREATE
IF NOT EXISTS here — db.py is NOT touched, same isolation as wolfe.py's wolfe_signals).

DESCRIPTIVE-ONLY, read BY SIDE per the reliability backtest (harmonic_backtest.py, run
2026-06-28 on 300 survivorship-inclusive symbols / 1,052 patterns):
  • BULL harmonics BEAT long-drift at every horizon (60-bar +4.5% vs +2.7% baseline;
    Gartley-bull strongest, +6.3% / 63% hit) and the ratio-fit score stratifies
    (hi ≥0.6 > lo <0.6 everywhere) → a modest, real, fit-graded BULL selection edge.
  • BEAR harmonics ≈ short-drift (no edge beyond drift) → ⚠ tail/regime only, like Wolfe.
So this is a scanner that sharpens the eye, NOT a buy/sell signal.

Nightly entry: `python -m src.automation.harmonic_signals --persist-scan`.
"""
from __future__ import annotations

import argparse

try:
    from src.core.db import get_conn
    from src.automation.wolfe import stock_series, scan_universe
    from src.automation.harmonic_patterns import detect_from_series
except Exception:  # pragma: no cover
    from core.db import get_conn  # type: ignore
    from automation.wolfe import stock_series, scan_universe  # type: ignore
    from automation.harmonic_patterns import detect_from_series  # type: ignore


_COLS = ("sym", "pattern", "dir", "state", "score", "cmp", "d_price",
         "prz_lo", "prz_hi", "in_zone", "rsi_d", "age", "tag")


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS harmonic_signals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            universe     TEXT NOT NULL,
            sym          TEXT NOT NULL,
            pattern      TEXT,
            dir          TEXT,
            state        TEXT,          -- CONFIRMED | FORMING
            score        REAL,
            cmp          REAL,
            d_price      REAL,          -- CONFIRMED: point-D price
            prz_lo       REAL,          -- FORMING: potential reversal zone
            prz_hi       REAL,
            in_zone      INTEGER,       -- price at/in the reversal zone now
            rsi_d        REAL,
            age          INTEGER,       -- bars since D (confirmed) / since C (forming)
            tag          TEXT,          -- 'edge' (BULL) | 'tail' (BEAR) per the backtest
            scan_date    TEXT,
            computed_at  TEXT
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_harm_universe "
                 "ON harmonic_signals(universe, in_zone DESC, age ASC)")


def _scan_as_of(conn):
    for sql in ("SELECT MAX(trade_date) FROM stock_signals",
                "SELECT MAX(date) FROM bhavcopy_rows"):
        try:
            r = conn.execute(sql).fetchone()
            if r and r[0]:
                return str(r[0])[:10]
        except Exception:
            continue
    return None


def scan(conn, universe="nifty500", k=1.5, fresh=12, max_symbols=None, tf="d"):
    """Fresh harmonic setups across a universe — actionable-first then freshest. Each row
    matches `_COLS`. CONFIRMED kept only if D is within `fresh` bars; FORMING always (the
    PRZ is forward-looking). `tag` = the backtest's by-side read (BULL edge / BEAR tail).

    tf='d'/'w'/'m' detects on daily / weekly / monthly bars (the multi-TF hand-off). W/M
    bars are coarser, so `fresh` is widened so recent W/M setups still surface."""
    from src.automation.harmonic_patterns import resample_series  # local: avoid import cycle at load
    out = []
    syms = scan_universe(conn, universe)
    if max_symbols:
        syms = syms[:max_symbols]
    fresh_eff = fresh if tf == "d" else max(fresh, 8)
    for sym in syms:
        s = stock_series(conn, sym)
        if not s:
            continue
        if tf in ("w", "m"):
            s = resample_series(*s, tf)
        dates, opens, highs, lows, closes = s
        n = len(closes)
        cmp_ = closes[-1]
        if cmp_ <= 0:
            continue
        for p in detect_from_series(dates, opens, highs, lows, closes, k=k, forming=True):
            bull = p.direction == "BULL"
            tag = "edge" if bull else "tail"
            if p.state == "CONFIRMED":
                d_idx = p.points[-1][1]
                d_price = p.points[-1][2]
                age = n - 1 - d_idx
                if age > fresh_eff:
                    continue
                in_zone = abs(cmp_ - d_price) / d_price <= 0.02 if d_price else False
                out.append({"sym": sym, "pattern": p.name, "dir": p.direction,
                            "state": "CONFIRMED", "score": p.score, "cmp": round(cmp_, 2),
                            "d_price": d_price, "prz_lo": None, "prz_hi": None,
                            "in_zone": bool(in_zone), "rsi_d": p.rsi_d, "age": age, "tag": tag})
            else:  # FORMING
                c_idx = p.points[-1][1]
                age = n - 1 - c_idx
                if age > fresh_eff:
                    continue
                lo, hi = p.prz.get("lo"), p.prz.get("hi")
                in_zone = (lo is not None and min(lo, hi) * 0.99 <= cmp_ <= max(lo, hi) * 1.01)
                out.append({"sym": sym, "pattern": p.name, "dir": p.direction,
                            "state": "FORMING", "score": 0.0, "cmp": round(cmp_, 2),
                            "d_price": None, "prz_lo": lo, "prz_hi": hi,
                            "in_zone": bool(in_zone), "rsi_d": None, "age": age, "tag": tag})
    out.sort(key=lambda r: (not r["in_zone"], r["age"], -(r["score"] or 0)))
    return out


def persist_scan(conn, universe="nifty500", k=1.5, fresh=12, computed_at=None):
    """Materialise scan() into harmonic_signals as a clean per-universe snapshot."""
    _ensure_table(conn)
    rows = scan(conn, universe=universe, k=k, fresh=fresh)
    scan_date = _scan_as_of(conn)
    conn.execute("DELETE FROM harmonic_signals WHERE universe=?", (universe,))
    conn.executemany(
        "INSERT INTO harmonic_signals "
        "(universe,sym,pattern,dir,state,score,cmp,d_price,prz_lo,prz_hi,in_zone,"
        " rsi_d,age,tag,scan_date,computed_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(universe, r["sym"], r["pattern"], r["dir"], r["state"], r["score"], r["cmp"],
          r["d_price"], r["prz_lo"], r["prz_hi"], 1 if r["in_zone"] else 0, r["rsi_d"],
          r["age"], r["tag"], scan_date, computed_at) for r in rows])
    try:
        conn.commit()
    except Exception:
        pass
    return len(rows), scan_date


def latest(conn, universe="nifty500"):
    """Read the persisted snapshot (instant) or None when absent/empty."""
    try:
        cur = conn.execute(
            "SELECT sym,pattern,dir,state,score,cmp,d_price,prz_lo,prz_hi,in_zone,"
            "rsi_d,age,tag,scan_date,computed_at FROM harmonic_signals "
            "WHERE universe=? ORDER BY in_zone DESC, age ASC", (universe,))
        recs = cur.fetchall()
    except Exception:
        return None
    if not recs:
        return None
    rows = [{"sym": r[0], "pattern": r[1], "dir": r[2], "state": r[3], "score": r[4],
             "cmp": r[5], "d_price": r[6], "prz_lo": r[7], "prz_hi": r[8],
             "in_zone": bool(r[9]), "rsi_d": r[10], "age": r[11], "tag": r[12]} for r in recs]
    return {"rows": rows, "scan_date": recs[0][13], "computed_at": recs[0][14]}


def _cli():
    import datetime as _dt
    ap = argparse.ArgumentParser(description="Harmonic scanner — persist fresh setups")
    ap.add_argument("--persist-scan", action="store_true")
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--k", type=float, default=1.5)
    ap.add_argument("--fresh", type=int, default=12)
    a = ap.parse_args()
    if a.persist_scan:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_conn() as conn:
            n, sd = persist_scan(conn, universe=a.universe, k=a.k, fresh=a.fresh, computed_at=stamp)
        print(f"persisted {n} harmonic setups for {a.universe} (as-of {sd}, computed {stamp})")
    else:
        ap.print_help()


if __name__ == "__main__":
    _cli()
