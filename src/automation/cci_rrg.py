"""CCI Phase 3 — credibility RRG + credibility÷price divergence (DESCRIPTIVE map).

⚠️ DESCRIPTIVE ONLY. The §C falsification (cci_backtest.py, reproduced by two independent agents)
found CCI has NO validated long / short / risk RETURN edge — high-credibility names UNDERperform,
the momentum signal is weak, and the deterioration-veto is survivorship-blind. So this module is a
map for RESEARCHING a name (the credibility track-record in confluence), NOT a ranked buy/sell
signal. In particular the "credibility rising while price flat = pre-re-rating alpha" premise is
UNDERCUT by the weak-momentum result; positive divergence is surfaced as an OBSERVATION, never a
recommendation. (See docs/strategy-ledger.md Tier-3 + product-strategy-2026 §9.)

Two reads over the PIT credibility_series (+ bhavcopy_rows for price), materialised into one owned
table (credibility_rrg), as the data layer a future descriptive view consumes:

  1. credibility RRG quadrant — level (proven vs low, vs 50 neutral) × momentum_3p (improving vs
     deteriorating) → PROVEN_IMPROVING / PROVEN_SLIPPING / UNPROVEN_IMPROVING / LOW_DETERIORATING
     (the four canonical credibility-rotation cells), with an UNPROVEN guard for thin samples.
  2. credibility ÷ price divergence — the credibility slope (momentum_3p) vs the stock's
     corporate-action-adjusted return over a comparable trailing window → CONFIRMING /
     POSITIVE_DIVERGENCE / NEGATIVE_DIVERGENCE.

Returns are adjusted via the NSE prev_close chain over bhavcopy_rows (splits/bonuses don't create
spurious moves), the same method cci_backtest.py uses. Pure stdlib. Owns its table; never edits
another module. CLI --build / --show / --selftest.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from typing import Optional

log = logging.getLogger("hermes.cci_rrg")

# thresholds (descriptive cut-points, not tuned for any edge — the edge was falsified)
LEVEL_NEUTRAL = 50.0        # credibility composite midpoint (PRIOR_RATE 0.5 → 50 neutral)
MOM_BAND = 2.0             # |momentum_3p| inside this = flat
MIN_RESOLVED = 3          # < this resolved promises → UNPROVEN (the binding sample gate)
PRICE_LOOKBACK_DAYS = 189  # ~9 trading months ≈ 3 concall periods (matches momentum_3p span)
PRICE_FLAT_BAND = 5.0      # |adjusted return %| inside this = flat
BAD_TICK = 1.0            # drop single-day |move| > 100% as a bad tick (prev_close chain)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS credibility_rrg (
    symbol        TEXT PRIMARY KEY,
    as_of_period  TEXT,
    level         REAL,
    momentum_3p   REAL,
    n_resolved    INTEGER,
    tier          TEXT,
    quadrant      TEXT,
    price_ret_pct REAL,
    divergence    TEXT,
    computed_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cred_rrg_quad ON credibility_rrg(quadrant);
CREATE INDEX IF NOT EXISTS idx_cred_rrg_div  ON credibility_rrg(divergence);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


# ── classification (pure) ─────────────────────────────────────────────────────
def quadrant(level: Optional[float], mom: Optional[float], n_resolved: Optional[int]) -> str:
    """The credibility-RRG cell. Thin samples (n_resolved < gate) are UNPROVEN, split by slope."""
    m = mom or 0.0
    direction = "IMPROVING" if m > MOM_BAND else ("DETERIORATING" if m < -MOM_BAND else "FLAT")
    if (n_resolved or 0) < MIN_RESOLVED or level is None:
        return f"UNPROVEN_{direction}"
    if level >= LEVEL_NEUTRAL:
        return "PROVEN_IMPROVING" if m > MOM_BAND else ("PROVEN_SLIPPING" if m < -MOM_BAND else "PROVEN_STABLE")
    return "LOW_IMPROVING" if m > MOM_BAND else ("LOW_DETERIORATING" if m < -MOM_BAND else "LOW_STABLE")


def divergence(cred_mom: Optional[float], price_ret_pct: Optional[float]) -> str:
    """credibility slope vs price return → CONFIRMING / POSITIVE_DIVERGENCE / NEGATIVE_DIVERGENCE /
    NONE. POSITIVE = credibility up while price flat/down (the observation, NOT a buy); NEGATIVE =
    credibility down while price up (distribution/risk observation)."""
    if cred_mom is None or price_ret_pct is None:
        return "NONE"
    cred_up = cred_mom > MOM_BAND
    cred_down = cred_mom < -MOM_BAND
    px_up = price_ret_pct > PRICE_FLAT_BAND
    px_down = price_ret_pct < -PRICE_FLAT_BAND
    if cred_up and not px_up:
        return "POSITIVE_DIVERGENCE"
    if cred_down and px_up:
        return "NEGATIVE_DIVERGENCE"
    if (cred_up and px_up) or (cred_down and px_down):
        return "CONFIRMING"
    return "NONE"


# ── price (adjusted return over a trailing window, prev_close chain) ──────────
def _adj_return_pct(conn, symbol: str, lookback_days: int = PRICE_LOOKBACK_DAYS) -> Optional[float]:
    """Corporate-action-adjusted % return over the last ``lookback_days`` trading rows (the NSE
    close/prev_close chain absorbs splits/bonuses). None if too little clean data."""
    try:
        rows = conn.execute(
            "SELECT close, prev_close FROM bhavcopy_rows "
            "WHERE symbol=? AND series='EQ' AND close>0 AND prev_close>0 ORDER BY trade_date",
            (symbol,)).fetchall()
    except sqlite3.Error:
        return None
    if len(rows) < lookback_days // 2:
        return None
    window = rows[-lookback_days:]
    cum = 1.0
    for close, prev in window:
        ratio = close / prev
        if abs(ratio - 1.0) > BAD_TICK:     # drop a >100% single-day move as a bad tick
            continue
        cum *= ratio
    return round((cum - 1.0) * 100.0, 1)


def _latest_point(conn, symbol: str):
    """The most recent credibility_series point for a symbol (PIT 'current')."""
    return conn.execute(
        "SELECT period_label, level, momentum_3p, n_resolved, tier FROM credibility_series "
        "WHERE symbol=? ORDER BY period_year DESC, period_month DESC LIMIT 1", (symbol,)).fetchone()


# ── build ─────────────────────────────────────────────────────────────────────
def build(conn, *, symbol: Optional[str] = None) -> int:
    """(Re)compute the RRG + divergence for every scored symbol (or one). Returns #rows."""
    ensure_schema(conn)
    syms = ([symbol.upper().strip()] if symbol
            else [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM credibility_series")])
    n = 0
    for sym in syms:
        pt = _latest_point(conn, sym)
        if not pt:
            continue
        period, level, mom3, nres, tier = pt
        px = _adj_return_pct(conn, sym)
        q = quadrant(level, mom3, nres)
        d = divergence(mom3, px)
        conn.execute(
            "INSERT OR REPLACE INTO credibility_rrg (symbol, as_of_period, level, momentum_3p, "
            "n_resolved, tier, quadrant, price_ret_pct, divergence, computed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))",
            (sym, period, level, mom3, nres, tier, q, px, d))
        n += 1
    conn.commit()
    return n


def summary(conn) -> dict:
    """Counts by quadrant + divergence (the descriptive board's header)."""
    ensure_schema(conn)
    quad = dict(conn.execute("SELECT quadrant, COUNT(*) FROM credibility_rrg GROUP BY quadrant").fetchall())
    div = dict(conn.execute("SELECT divergence, COUNT(*) FROM credibility_rrg GROUP BY divergence").fetchall())
    return {"n": sum(quad.values()), "by_quadrant": quad, "by_divergence": div}


# ── selftest ────────────────────────────────────────────────────────────────
def _selftest() -> None:
    # pure classification
    assert quadrant(80, 5, 12) == "PROVEN_IMPROVING"
    assert quadrant(80, -5, 12) == "PROVEN_SLIPPING"
    assert quadrant(30, 5, 12) == "LOW_IMPROVING"
    assert quadrant(30, -5, 12) == "LOW_DETERIORATING"
    assert quadrant(90, 5, 1) == "UNPROVEN_IMPROVING", "thin sample must be UNPROVEN regardless of level"
    assert quadrant(80, 0.5, 12) == "PROVEN_STABLE"
    assert divergence(5, -10) == "POSITIVE_DIVERGENCE"      # cred up, price down
    assert divergence(5, 2) == "POSITIVE_DIVERGENCE"        # cred up, price flat
    assert divergence(-5, 20) == "NEGATIVE_DIVERGENCE"      # cred down, price up
    assert divergence(5, 20) == "CONFIRMING"
    assert divergence(None, 10) == "NONE"

    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE credibility_series (symbol TEXT, period_label TEXT, period_year INT,
        period_month INT, level REAL, momentum_3p REAL, n_resolved INT, tier TEXT)""")
    conn.execute("""CREATE TABLE bhavcopy_rows (symbol TEXT, series TEXT, trade_date TEXT,
        close REAL, prev_close REAL)""")
    conn.executescript("""
        INSERT INTO credibility_series VALUES ('RISER','May 2026',2026,5,72,8,12,'A'),
                                              ('RISER','Feb 2026',2026,2,64,4,11,'B');
    """)
    # RISER: price roughly FLAT (cred up + price flat → POSITIVE_DIVERGENCE)
    for i in range(200):
        conn.execute("INSERT INTO bhavcopy_rows VALUES ('RISER','EQ',?,100.0,100.0)", (f"2026-{i:04d}",))
    n = build(conn)
    assert n == 1
    row = conn.execute("SELECT quadrant, divergence FROM credibility_rrg WHERE symbol='RISER'").fetchone()
    assert row == ("PROVEN_IMPROVING", "POSITIVE_DIVERGENCE"), row
    s = summary(conn)
    assert s["n"] == 1 and s["by_quadrant"].get("PROVEN_IMPROVING") == 1
    print("cci_rrg selftest: OK  (quadrant + divergence classification, build + summary round-trip)")


def main() -> None:
    from src.core.db import get_conn
    ap = argparse.ArgumentParser(description="CCI Phase 3 — credibility RRG + divergence (descriptive).")
    ap.add_argument("--build", action="store_true", help="(re)compute the RRG + divergence for all scored symbols")
    ap.add_argument("--symbol", help="restrict --build / --show to one symbol")
    ap.add_argument("--show", action="store_true", help="print the summary + (with --symbol) the row")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.selftest:
        _selftest(); return
    if args.build:
        with get_conn() as conn:
            print(f"built {build(conn, symbol=args.symbol)} credibility_rrg rows")
        return
    if args.show:
        import json
        with get_conn() as conn:
            ensure_schema(conn)
            if args.symbol:
                r = conn.execute("SELECT * FROM credibility_rrg WHERE symbol=?", (args.symbol.upper(),)).fetchone()
                print(dict(zip([c[0] for c in conn.execute("SELECT * FROM credibility_rrg LIMIT 0").description], r)) if r else "no row")
            print(json.dumps(summary(conn), indent=2))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
