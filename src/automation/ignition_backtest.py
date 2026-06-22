"""Ignition backtest — the full-journey outcome study (design doc §5).

For every historical ignition (a FULL all-stars DVPT cross, `trigger_rank='SS'`,
from 2019), follow what the stock actually did and measure the journey, so we can
DERIVE — not guess — a realistic target, stop, and averaging zones:

  - MFE   = max favourable excursion (peak gain) + time-to-peak
  - MAE-from-entry / MAE-from-signal = max drawdown from the entry / signal price
  - mae_before_peak = the worst heat taken ON THE WAY to the peak (the number a
        stop has to survive) — this is what makes the win-grid path-aware
  - returns at 1m/3m/6m/12m/24m + final fate

Rigor (the design's non-negotiables, all honoured here):
  - **Survivorship** — delisted names ARE included (events come from the full
    stock_signals history; the universe gate keeps delisted stocks). Live ETFs are
    excluded (currently_listed=0 AND recently_traded=1 = a live non-EQUITY_L
    instrument = an ETF; a delisted STOCK stopped trading so recently_traded=0).
  - **No look-ahead** — entry = next-day OPEN (C4); only forward prices are used.
  - **Continuity** — a journey is truncated at any demerger/merger (security_master
    .has_break_between) so a scheme gap is never counted as a return.
  - **Corp-action clean** — all prices back-adjusted via adjust.adjustment_factors.

Parameterised on C4 (ENTRY_MODE) and C5 (WIN_GRID) — changing them is a re-run,
not a rebuild. The win-grid is REPORTED across thresholds (C5 default: a grid),
with the doc's MFE≥+25% before MAE≤−15% highlighted.

Self-contained (capture.py pattern): OWNS `ignition_outcomes`, never edits db.py.
Reads stock_signals + bhavcopy_rows + adjust + security_master. Pure arithmetic.

Run:        python -m src.automation.ignition_backtest            # compute + summary
Smoke:      python -m src.automation.ignition_backtest --limit 150
Summary:    python -m src.automation.ignition_backtest --summary  # re-derive from stored
Self-check: python -m src.automation.ignition_backtest --selftest
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from src.core.db import get_conn
from src.automation import adjust, security_master

log = logging.getLogger("hermes.ignition_backtest")

BACKTEST_FROM = "2019-01-01"
COOLDOWN_DAYS = 21          # ≥ this many trading days between distinct ignitions/symbol
MAX_HORIZON = 504           # ≈ 24 months of trading days
HORIZONS = {"ret_1m": 21, "ret_3m": 63, "ret_6m": 126, "ret_12m": 252, "ret_24m": 504}
ENTRY_MODE = "next_open"    # C4: "next_open" | "signal_close"
PRICE_SERIES = "EQ"         # journeys measured on the canonical equity series

# C5: the reported win-grid (target %, stop %). The doc's default is starred.
WIN_TARGETS = (15.0, 25.0, 40.0, 60.0)
WIN_STOPS = (-10.0, -15.0, -20.0)
DEFAULT_WIN = (25.0, -15.0)

POWER_BASELINES = ("power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m",
                   "power_dvpt_6m", "power_dvpt_12m")


# ── pure helpers ──────────────────────────────────────────────────────────────
def _mean(vals):
    xs = [v for v in vals if isinstance(v, (int, float))]
    return (sum(xs) / len(xs)) if xs else None


def _pct(sorted_vals, q):
    """Linear-interpolated percentile (q in 0..100) of an already-sorted list."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * (q / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _dedup_events(dates, cooldown=COOLDOWN_DAYS):
    """Collapse consecutive SS days into discrete ignitions: a date starts a new
    event only if it's the first or ≥ cooldown trading days after the prior one.
    `dates` must be the symbol's own ascending trading-day-indexed SS positions."""
    out = []
    last = None
    for idx in dates:
        if last is None or (idx - last) >= cooldown:
            out.append(idx)
            last = idx
    return out


def journey(adj_open, adj_high, adj_low, adj_close, signal_idx, entry_idx, end_idx,
            entry_mode=ENTRY_MODE):
    """Compute one event's journey metrics over [entry_idx, end_idx]. Returns a
    dict, or None if entry price is unusable."""
    entry = adj_open[entry_idx] if entry_mode == "next_open" else adj_close[signal_idx]
    if not entry or entry <= 0:
        return None
    sig_close = adj_close[signal_idx]

    peak_high, peak_idx = -1e18, entry_idx
    trough_low = 1e18
    for i in range(entry_idx, end_idx + 1):
        h, l = adj_high[i], adj_low[i]
        if h is not None and h > peak_high:
            peak_high, peak_idx = h, i
        if l is not None and l < trough_low:
            trough_low = l
    # worst heat taken BEFORE the peak (what a stop must survive to reach target)
    pre_low = 1e18
    for i in range(entry_idx, peak_idx + 1):
        l = adj_low[i]
        if l is not None and l < pre_low:
            pre_low = l

    mfe = (peak_high / entry - 1.0) * 100.0 if peak_high > -1e17 else None
    mae_entry = (trough_low / entry - 1.0) * 100.0 if trough_low < 1e17 else None
    mae_pre_peak = (pre_low / entry - 1.0) * 100.0 if pre_low < 1e17 else None

    sig_trough = 1e18
    for i in range(signal_idx, end_idx + 1):
        l = adj_low[i]
        if l is not None and l < sig_trough:
            sig_trough = l
    mae_signal = (sig_trough / sig_close - 1.0) * 100.0 if (sig_close and sig_trough < 1e17) else None

    out = {
        "entry_price": entry, "signal_close": sig_close,
        "mfe_pct": mfe, "time_to_peak_days": peak_idx - entry_idx,
        "mae_before_peak_pct": mae_pre_peak, "mae_from_entry_pct": mae_entry,
        "mae_from_signal_pct": mae_signal, "n_days_held": end_idx - entry_idx,
    }
    for col, k in HORIZONS.items():
        j = entry_idx + k
        out[col] = ((adj_close[j] / entry - 1.0) * 100.0) if (j <= end_idx and adj_close[j]) else None
    out["ret_final_pct"] = (adj_close[end_idx] / entry - 1.0) * 100.0 if adj_close[end_idx] else None
    return out


# ── storage ───────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS ignition_outcomes (
    symbol              TEXT NOT NULL,
    signal_date         TEXT NOT NULL,
    entry_date          TEXT,
    entry_price         REAL,
    signal_close        REAL,
    intensity           REAL,
    character           TEXT,
    rs_rank             INTEGER,
    is_first_ignition   INTEGER,
    n_days_held         INTEGER,
    mfe_pct             REAL,
    time_to_peak_days   INTEGER,
    mae_before_peak_pct REAL,
    mae_from_entry_pct  REAL,
    mae_from_signal_pct REAL,
    ret_1m REAL, ret_3m REAL, ret_6m REAL, ret_12m REAL, ret_24m REAL,
    ret_final_pct       REAL,
    break_in_window     INTEGER DEFAULT 0,
    censored            INTEGER DEFAULT 0,
    computed_at         TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, signal_date)
);
CREATE INDEX IF NOT EXISTS idx_igo_mfe ON ignition_outcomes(mfe_pct);
"""

_COLS = ["symbol", "signal_date", "entry_date", "entry_price", "signal_close",
         "intensity", "character", "rs_rank", "is_first_ignition", "n_days_held",
         "mfe_pct", "time_to_peak_days", "mae_before_peak_pct", "mae_from_entry_pct",
         "mae_from_signal_pct", "ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_24m",
         "ret_final_pct", "break_in_window", "censored"]


def _price_series(conn, symbol):
    """Adjusted O/H/L/C arrays + a date→index map for one symbol (EQ, oldest→newest)."""
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, prev_close FROM bhavcopy_rows "
        "WHERE symbol=? AND series=? ORDER BY trade_date", (symbol, PRICE_SERIES)).fetchall()
    if len(rows) < 2:
        return None
    rl = [dict(r) for r in rows]
    f = adjust.adjustment_factors(rl)
    ao = [(r["open"] * f[i]) if r["open"] else None for i, r in enumerate(rl)]
    ah = [(r["high"] * f[i]) if r["high"] else None for i, r in enumerate(rl)]
    al = [(r["low"] * f[i]) if r["low"] else None for i, r in enumerate(rl)]
    ac = [(r["close"] * f[i]) if r["close"] else None for i, r in enumerate(rl)]
    dates = [r["trade_date"] for r in rl]
    idx = {d: i for i, d in enumerate(dates)}
    return {"dates": dates, "idx": idx, "ao": ao, "ah": ah, "al": al, "ac": ac}


def compute_and_store(conn=None, limit: Optional[int] = None) -> dict:
    """Walk every de-duplicated ignition's forward journey and store outcomes."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)

        # events + signal-time descriptors, survivorship+ETF gated. Delisted stocks
        # kept (recently_traded=0); live ETFs (currently_listed=0 AND recently_traded=1) dropped.
        pbcols = ", ".join(f"s.{c}" for c in POWER_BASELINES)
        ev_rows = conn.execute(
            f"SELECT s.symbol, s.trade_date, s.accum_character ch, s.rs_rank rsr, "
            f"       s.delivery_value_per_trade dvpt, {pbcols} "
            f"FROM stock_signals s "
            f"JOIN security_master m ON m.symbol = s.symbol "
            f"     AND (m.currently_listed = 1 OR m.recently_traded = 0) "
            f"WHERE s.trigger_rank='SS' AND s.trade_date >= ? "
            f"ORDER BY s.symbol, s.trade_date", (BACKTEST_FROM,)).fetchall()

        # group events by symbol
        by_sym: dict = {}
        for r in ev_rows:
            by_sym.setdefault(r["symbol"], []).append(r)
        symbols = sorted(by_sym)
        if limit:
            symbols = symbols[:limit]

        conn.execute("DELETE FROM ignition_outcomes")
        latest = conn.execute("SELECT MAX(trade_date) m FROM bhavcopy_rows").fetchone()["m"]
        stored, no_price, skipped = 0, 0, 0
        batch = []
        for sym in symbols:
            ps = _price_series(conn, sym)
            if not ps:
                no_price += 1
                continue
            idxmap = ps["idx"]
            # break dates for this symbol (truncate the window at the first break after signal)
            breaks = [e["ex_date"] for e in security_master.events_for(sym, conn=conn)]
            # SS positions present in the price series, ascending
            ss = [(r, idxmap[r["trade_date"]]) for r in by_sym[sym] if r["trade_date"] in idxmap]
            ss.sort(key=lambda t: t[1])
            keep_idx = set(_dedup_events([i for _, i in ss]))
            first_done = False
            for r, sidx in ss:
                if sidx not in keep_idx:
                    continue
                is_first = 0 if first_done else 1
                first_done = True
                entry_idx = sidx + 1 if ENTRY_MODE == "next_open" else sidx
                if entry_idx >= len(ps["dates"]):
                    skipped += 1
                    continue
                end_idx = min(entry_idx + MAX_HORIZON, len(ps["dates"]) - 1)
                # truncate at the first continuity break strictly after the signal
                brk = 0
                for bd in breaks:
                    if bd and bd > r["trade_date"]:
                        bpos = idxmap.get(bd)
                        if bpos is not None and entry_idx <= bpos <= end_idx:
                            end_idx, brk = max(entry_idx, bpos - 1), 1
                        break
                if end_idx <= entry_idx:
                    skipped += 1
                    continue
                jr = journey(ps["ao"], ps["ah"], ps["al"], ps["ac"], sidx, entry_idx, end_idx)
                if not jr:
                    skipped += 1
                    continue
                intensity = None
                bmean = _mean([r[c] for c in POWER_BASELINES])
                if bmean and bmean > 0 and r["dvpt"]:
                    intensity = r["dvpt"] / bmean
                censored = 1 if jr["n_days_held"] < MAX_HORIZON and end_idx >= len(ps["dates"]) - 1 and not brk else 0
                rec = {
                    "symbol": sym, "signal_date": r["trade_date"],
                    "entry_date": ps["dates"][entry_idx], "intensity": intensity,
                    "character": r["ch"], "rs_rank": r["rsr"], "is_first_ignition": is_first,
                    "break_in_window": brk, "censored": censored, **jr,
                }
                batch.append([rec.get(c) for c in _COLS])
                stored += 1
            if len(batch) >= 5000:
                conn.executemany(
                    f"INSERT OR REPLACE INTO ignition_outcomes ({','.join(_COLS)}) "
                    f"VALUES ({','.join('?'*len(_COLS))})", batch)
                batch = []
        if batch:
            conn.executemany(
                f"INSERT OR REPLACE INTO ignition_outcomes ({','.join(_COLS)}) "
                f"VALUES ({','.join('?'*len(_COLS))})", batch)
        if own:
            conn.commit()

        stats = {"symbols": len(symbols), "events_stored": stored,
                 "no_price": no_price, "skipped": skipped, "latest": latest}
        log.info("ignition_backtest: %s", stats)
        return stats
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── derivation / summary (the actual deliverable: target / stop / win-grid) ──────
def summarize(conn=None, full_only=True) -> dict:
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        where = "WHERE break_in_window=0"
        if full_only:
            where += " AND ret_6m IS NOT NULL"     # ≥6m of forward data for stable stats
        rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM ignition_outcomes {where}").fetchall()]
        n = len(rows)
        if n == 0:
            return {"events": 0}

        mfe = sorted(r["mfe_pct"] for r in rows if r["mfe_pct"] is not None)
        target_pctls = {f"p{q}": round(_pct(mfe, q), 1) for q in (25, 50, 60, 75, 90)}

        def win(r, tgt, stop):
            return (r["mfe_pct"] is not None and r["mae_before_peak_pct"] is not None
                    and r["mfe_pct"] >= tgt and r["mae_before_peak_pct"] > stop)

        grid = {}
        for tgt in WIN_TARGETS:
            for stop in WIN_STOPS:
                w = sum(1 for r in rows if win(r, tgt, stop))
                grid[f"tgt+{tgt:.0f}/stop{stop:.0f}"] = round(100.0 * w / n, 1)

        dt, ds = DEFAULT_WIN
        winners = [r for r in rows if win(r, dt, ds)]
        losers = [r for r in rows if not win(r, dt, ds)]
        win_pre = sorted(r["mae_before_peak_pct"] for r in winners if r["mae_before_peak_pct"] is not None)

        def _avg(rs, k):
            xs = [r[k] for r in rs if r[k] is not None]
            return round(sum(xs) / len(xs), 1) if xs else None

        out = {
            "events": n, "winners": len(winners),
            "win_rate_default": round(100.0 * len(winners) / n, 1),
            "default_def": f"MFE>=+{dt:.0f}% before MAE<={ds:.0f}%",
            "target_from_MFE_pctiles": target_pctls,
            "stop_from_winner_heat": {  # how much heat winners survive → stop guidance
                "p10": round(_pct(win_pre, 10), 1) if win_pre else None,
                "p25": round(_pct(win_pre, 25), 1) if win_pre else None,
                "median": round(_pct(win_pre, 50), 1) if win_pre else None,
            },
            "win_grid_pct": grid,
            "winner_vs_loser": {
                "intensity": (_avg(winners, "intensity"), _avg(losers, "intensity")),
                "rs_rank": (_avg(winners, "rs_rank"), _avg(losers, "rs_rank")),
                "median_MFE": (round(_pct(sorted(r["mfe_pct"] for r in winners if r["mfe_pct"] is not None), 50), 1) if winners else None,
                               round(_pct(sorted(r["mfe_pct"] for r in losers if r["mfe_pct"] is not None), 50), 1) if losers else None),
            },
        }
        log.info("ignition_backtest summary: events=%d win=%.1f%%", n, out["win_rate_default"])
        return out
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── self-check (synthetic prices — no real data) ──────────────────────────────
def _selftest() -> None:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    pbdefs = ", ".join(f"{c} REAL" for c in POWER_BASELINES)
    conn.executescript(f"""
        CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT,
            open REAL, high REAL, low REAL, close REAL, prev_close REAL);
        CREATE TABLE stock_signals (symbol TEXT, trade_date TEXT, trigger_rank TEXT,
            accum_character TEXT, rs_rank INTEGER, delivery_value_per_trade REAL, {pbdefs});
    """)
    conn.executescript(security_master._SCHEMA)   # canonical security_master/events/renames
    # WINNER: enters 100, dips to 92 (-8%), peaks 150 (+50%), ends 120.
    # day 0 = signal, day 1 = entry(open 100). Build 40 days.
    def day(i):
        return f"2020-01-{i+1:02d}" if i < 31 else f"2020-02-{i-30:02d}"
    conn.execute("INSERT INTO security_master (symbol, currently_listed, recently_traded) VALUES ('WIN',1,1)")
    prices = [100] * 2 + [96, 92, 95, 110, 130, 150, 140, 120] + [120] * 30
    prev = 100
    for i, c in enumerate(prices):
        o = prev
        hi = max(o, c) * 1.0
        lo = min(o, c)
        conn.execute("INSERT INTO bhavcopy_rows VALUES ('WIN',?,?,?,?,?,?,?)",
                     (day(i), "EQ", o, hi, lo, c, prev))
        prev = c
    # SS ignition on day 0
    cols = "symbol,trade_date,trigger_rank,accum_character,rs_rank,delivery_value_per_trade," + ",".join(POWER_BASELINES)
    ph = ",".join("?" * (6 + len(POWER_BASELINES)))
    conn.execute(f"INSERT INTO stock_signals ({cols}) VALUES ({ph})",
                 ("WIN", day(0), "SS", "ACCUMULATION", 80, 50.0, *([5.0] * len(POWER_BASELINES))))

    stats = compute_and_store(conn=conn)
    assert stats["events_stored"] == 1, stats
    row = dict(conn.execute("SELECT * FROM ignition_outcomes").fetchone())
    assert abs(row["mfe_pct"] - 50.0) < 1.0, row["mfe_pct"]            # peak 150 vs entry 100
    assert -9 < row["mae_before_peak_pct"] < -7, row["mae_before_peak_pct"]  # the -8% dip
    assert abs(row["intensity"] - 10.0) < 1e-6, row["intensity"]      # 50 / 5
    s = summarize(conn=conn, full_only=False)
    assert s["events"] == 1 and s["winners"] == 1, s                  # +50% before -15% = win
    assert s["win_grid_pct"]["tgt+25/stop-15"] == 100.0, s["win_grid_pct"]
    print(f"ignition_backtest selftest: OK  mfe={row['mfe_pct']:.1f} "
          f"mae_pre={row['mae_before_peak_pct']:.1f} ttp={row['time_to_peak_days']}")


def main() -> None:
    p = argparse.ArgumentParser(description="Ignition full-journey backtest (derive target/stop).")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--summary", action="store_true", help="re-derive summary from stored outcomes")
    p.add_argument("--limit", type=int, help="process only the first N symbols (smoke test)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        _selftest()
        return
    if args.summary:
        import json
        print(json.dumps(summarize(), indent=2))
        return
    stats = compute_and_store(limit=args.limit)
    print(f"ignition_backtest: {stats}")
    import json
    print(json.dumps(summarize(), indent=2))


if __name__ == "__main__":
    main()
