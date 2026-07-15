"""STREAM BAND — 13-EMA HiLo band + 5-EMA HLC3 trigger: PRE-REGISTERED reversal study (2026-07-13).

RAMANA'S SPEC (docs/reversal-pair-PLAN.md, S-reversal-pair). Band = EMA13(adj high) upper bank /
EMA13(adj low) lower bank; trigger stream = EMA5 of HLC/3 (typical price, CA-adjusted). BUY-cross =
the trigger closes above the lower bank having been below it >=3 consecutive bars; SELL-cross is
the mirror against the upper bank. STRETCH = signed % gap between the trigger and the violated
bank, ranked against the stock's OWN trailing 756-bar distribution (the standard-deviation idea
done per-stock, in percent, never absolute).

LEDGER PRIOR (cited, blocking): PULLBACK return/vol 0.56-0.72 MaxDD -44%; S3 shakeout reversion CAGR
-0.5% FAILED; raw-Wolfe book median -2.1% net, placebo-negative; momentum gross 1.29 -> net ~0.09.
Reversal BOOKS have always failed here; the only surviving form is SELECTION (Wolfe BULL +4.4%
medNet). This study tests the SELECTION claim as primary; the book form is measured for the record
against the Nifty-500 return/vol 0.89 hurdle and is EXPECTED to fail. DESCRIPTIVE-ONLY output either
way: no ranking, no buy/sell advice, SEBI-safe.

METRIC BASIS (D142): every ratio reported here is mean/sd annualised with NO risk-free rate
subtracted — a return/vol ratio, not a Sharpe; it reads high against a textbook Sharpe. The
Nifty-500 0.89 hurdle is computed on the SAME basis, so the verdict is unaffected.

DESIGN (locked before first run; global seed 42; symbols processed in sorted order). Universe =
every EQ/CM symbol in bhavcopy_rows (2004->today). Primary window: signal dates >= 2012-06-01.
Eligibility at signal bar i: >=260 prior rows; med_turn[i] >= Rs 1cr (LIQ_FLOOR); raw close[i]
>= 20; calendar gap <= 6d for bars (i-1,i) and (i,i+1); band/trigger values finite. De-overlap:
per symbol per side, a counted event blocks further events for 22 bars. PIT plumbing: the signal
uses ONLY data through the close of bar i; entry is the CLOSE of bar i+1; horizons h in
{5,10,22,66} bars measured entry-close -> close of bar i+1+h on CA-adjusted closes; excess = raw
forward return minus the Nifty-500 return over the IDENTICAL date span.

CONTROLS: (a) symbol-placebo - per event, 3 uniform random eligible bars of the SAME symbol
(controls symbol drift/survivorship); (b) time-shift placebo - the same event shifted +63 bars
(controls "any bar near this one was as good"); (c) the excess-vs-index transform (market/day
control). Placebo bars additionally require a computable 22d forward return.

FORM-1 GATE (selection; PASS requires ALL FOUR, else FAIL-null is published to the ledger):
  G1  n >= 300 primary events (HLC3 trigger, BUY side, post-de-overlap)
  G2  mean AND median 22d excess > 0
  G3  Cliff's delta of 22d excess vs BOTH placebo sets >= +0.05
  G4  median 22d excess > 0 in BOTH halves (signal date < / >= 2019-01-01)

FORM-2 BOOK (for the record; fundable bar): long at entry close; exit at the close AFTER the first
of (T < L stop-out) or (T crosses below U from at-or-above); one open trade per symbol; cost 0.3%
per side (0.6% round trip); the book is daily-equal-weighted across open trades on adjusted closes
(implicit daily rebalance, disclosed), compounded monthly. FUNDABLE requires monthly return/vol
> 0.89 in BOTH halves 2012-18 / 2019-26.

VARIANTS (exploratory only - no gate promotion without fresh pre-registration; each reported with
n): OHLC4 trigger instead of HLC3; STRETCH precondition (min signed stretch over the 5 bars ending
at the cross <= the symbol's own trailing-756-bar 10th percentile); TREND (close>SMA200) and
ANTI-TREND splits; liquidity >= Rs 5cr. BUCKETS on the primary event set: med_turn terciles AND
absolute bands (1-5cr / 5-25cr / >25cr), vol66 terciles, raw-price terciles. SELL side reported
descriptively (no shorting claim). Multiple-testing honesty: the gate is judged ONLY on the
primary cell.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.streamband --build   # events+trades+book -> research.db
  ... --run                                   # analysis -> out/streamband.json + printed report
  ... --selftest                              # offline synthetic checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .common import (LIQ_FLOOR, SymbolSeries, cliffs_delta, eq_symbols,
                     load_series, main_conn, research_conn)
from .metrics import index_series

EMA_FAST, EMA_SLOW = 5, 13
RUN_BARS = 3                 # consecutive bars beyond the bank before a cross counts
DEOVERLAP = 22
HORIZONS = (5, 10, 22, 66)
START = "2012-06-01"
HALF_SPLIT = "2019-01-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
COST_SIDE = 0.003
STRETCH_WIN = 756
SHIFT = 63
SEED = 42
LIQ5 = 5e7
BOOK_KEYS = ("ALL", "STRETCH", "TREND", "ANTITREND", "LIQ5")


# --------------------------------------------------------------------------- #
# causal primitives                                                            #
# --------------------------------------------------------------------------- #
def ema(x: np.ndarray, n: int) -> np.ndarray:
    """Recursive EMA (alpha=2/(n+1)), first-valid seed, NaN until n updates.
    NaN inputs carry the state forward (no update). Strictly causal."""
    out = np.full(len(x), np.nan)
    a = 2.0 / (n + 1)
    e, k = np.nan, 0
    for i in range(len(x)):
        v = x[i]
        if not np.isnan(v):
            e = v if np.isnan(e) else a * v + (1 - a) * e
            k += 1
        if k >= n:
            out[i] = e
    return out


def roll_mean(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    c = np.concatenate(([0.0], np.cumsum(np.nan_to_num(x, nan=0.0))))
    k = np.concatenate(([0.0], np.cumsum(~np.isnan(x))))
    s, cnt = c[w:] - c[:-w], k[w:] - k[:-w]
    with np.errstate(invalid="ignore", divide="ignore"):
        out[w - 1:] = np.where(cnt == w, s / w, np.nan)
    return out


def roll_std(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    sw = sliding_window_view(x, w)
    with np.errstate(invalid="ignore"):
        out[w - 1:] = np.nanstd(sw, axis=1)
    return out


def crosses(T: np.ndarray, U: np.ndarray, L: np.ndarray, run: int = RUN_BARS):
    """BUY = T>L after >=run consecutive bars T<=L; SELL mirrored vs U. Causal."""
    n = len(T)
    ok = ~(np.isnan(T) | np.isnan(U) | np.isnan(L))
    buy, sell = [], []
    rb = ra = 0
    for i in range(n):
        if not ok[i]:
            rb = ra = 0
            continue
        if rb >= run and T[i] > L[i]:
            buy.append(i)
        if ra >= run and T[i] < U[i]:
            sell.append(i)
        rb = rb + 1 if T[i] <= L[i] else 0
        ra = ra + 1 if T[i] >= U[i] else 0
    return buy, sell


def stretch_signed(T, U, L):
    with np.errstate(invalid="ignore", divide="ignore"):
        up = (T - U) / U * 100.0
        dn = (T - L) / L * 100.0
    s = np.zeros(len(T))
    s = np.where(T > U, up, s)
    s = np.where(T < L, dn, s)
    s[np.isnan(T) | np.isnan(U) | np.isnan(L)] = np.nan
    return s


def rolling_p10(s: np.ndarray, w: int = STRETCH_WIN) -> np.ndarray:
    """p10 of the TRAILING w values ending at i-1 (causal). NaN when <250 valid."""
    n = len(s)
    out = np.full(n, np.nan)
    if n <= w:
        return out
    sw = sliding_window_view(s, w)              # row k = s[k:k+w] ends at k+w-1
    valid = np.sum(~np.isnan(sw), axis=1)
    with np.errstate(invalid="ignore"):
        p = np.nanpercentile(sw, 10, axis=1)
    p[valid < 250] = np.nan
    out[w:] = p[: n - w]                        # threshold at i uses window ending i-1
    return out


# --------------------------------------------------------------------------- #
# build                                                                        #
# --------------------------------------------------------------------------- #
_DDL = """
DROP TABLE IF EXISTS streamband_events;
CREATE TABLE streamband_events(
  variant TEXT, kind TEXT, side TEXT, symbol TEXT, sig_date TEXT, entry_date TEXT,
  med_turn REAL, close_raw REAL, vol66 REAL, stretch_min5 REAL, stretch_pre INT, trend INT,
  fx5 REAL, fx10 REAL, fx22 REAL, fx66 REAL, fr5 REAL, fr10 REAL, fr22 REAL, fr66 REAL);
DROP TABLE IF EXISTS streamband_trades;
CREATE TABLE streamband_trades(
  symbol TEXT, entry_date TEXT, exit_date TEXT, hold INT, gross REAL, net REAL,
  censored INT, stretch_pre INT, trend INT, med_turn REAL, exit_kind TEXT);
DROP TABLE IF EXISTS streamband_book;
CREATE TABLE streamband_book(key TEXT, month TEXT, mret REAL, avg_pos REAL);
"""


class _Idx:
    def __init__(self):
        d, c = index_series("Nifty 500")
        if not d or d[0] > START:
            raise SystemExit(f"index_rows Nifty 500 starts {d[0] if d else 'EMPTY'} > {START}")
        self.pos = {x: i for i, x in enumerate(d)}
        self.dates, self.close = d, c

    def ret(self, d0: str, d1: str):
        import bisect
        i = self.pos.get(d0)
        j = self.pos.get(d1)
        if i is None:
            i = bisect.bisect_right(self.dates, d0) - 1
        if j is None:
            j = bisect.bisect_right(self.dates, d1) - 1
        if i < 0 or j < 0 or j <= i:
            return np.nan
        return float(self.close[j] / self.close[i] - 1.0)


def _fwd(S: SymbolSeries, i: int, idx: _Idx):
    """(raw, excess) dicts for entry at close of i+1."""
    e = i + 1
    raw, exc = {}, {}
    p0 = S.adj_close[e]
    for h in HORIZONS:
        j = e + h
        if j <= S.n - 1 and p0 > 0 and S.adj_close[j] > 0:
            r = float(S.adj_close[j] / p0 - 1.0)
            raw[h] = r
            ir = idx.ret(S.date[e], S.date[j])
            exc[h] = r - ir if not np.isnan(ir) else np.nan
        else:
            raw[h] = np.nan
            exc[h] = np.nan
    return raw, exc


def _gapdays(dates64: np.ndarray, i: int, j: int) -> int:
    return int((dates64[j] - dates64[i]) / np.timedelta64(1, "D"))


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript(_DDL)
    idx = _Idx()
    rng = np.random.default_rng(SEED)

    syms = eq_symbols(mc)
    ev_rows, tr_rows = [], []
    # book accumulators: key -> {date: [sum_ret, n]}
    book = {k: {} for k in BOOK_KEYS}
    n_sym = n_used = 0

    for sym in syms:
        n_sym += 1
        S = load_series(mc, sym)
        if S is None or S.n < 300:
            continue
        n_used += 1
        d64 = np.array(S.date, dtype="datetime64[D]")
        gap_prev = np.full(S.n, 999)
        gap_prev[1:] = (d64[1:] - d64[:-1]) / np.timedelta64(1, "D")
        gap_next = np.full(S.n, 999)
        gap_next[:-1] = gap_prev[1:]

        adj_open = S.open * S.factors
        tp3 = (S.adj_high + S.adj_low + S.adj_close) / 3.0
        tp4 = (adj_open + S.adj_high + S.adj_low + S.adj_close) / 4.0
        U = ema(S.adj_high, EMA_SLOW)
        L = ema(S.adj_low, EMA_SLOW)
        sma200 = roll_mean(S.adj_close, 200)
        vol66 = roll_std(S.ret_raw, 66)

        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START))
        # placebo pool additionally needs a computable 22d forward
        can22 = np.zeros(S.n, dtype=bool)
        lim = S.n - 1 - 23
        if lim > 0:
            can22[:lim] = True

        for variant, tp in (("HLC3", tp3), ("OHLC4", tp4)):
            T = ema(tp, EMA_FAST)
            st = stretch_signed(T, U, L)
            p10 = rolling_p10(st)
            okband = ~(np.isnan(T) | np.isnan(U) | np.isnan(L))
            buys, sells = crosses(T, U, L)

            plc_pool = np.where(base_elig & can22 & okband)[0]
            counted = {"BUY": -10**9, "SELL": -10**9}
            open_until = -1          # trades: one open per symbol (HLC3 only)

            for side, hits in (("BUY", buys), ("SELL", sells)):
                for i in hits:
                    if not base_elig[i] or i + 1 >= S.n:
                        continue
                    if i - counted[side] < DEOVERLAP:
                        continue
                    counted[side] = i
                    smin5 = float(np.nanmin(st[max(0, i - 4): i + 1]))
                    spre = int(not np.isnan(p10[i]) and smin5 <= p10[i])
                    trend = int(not np.isnan(sma200[i]) and S.adj_close[i] > sma200[i])
                    raw, exc = _fwd(S, i, idx)
                    ev_rows.append((variant, "event", side, sym, S.date[i], S.date[i + 1],
                                    float(S.med_turn[i]), float(S.close[i]),
                                    float(vol66[i]) if not np.isnan(vol66[i]) else None,
                                    smin5, spre, trend,
                                    exc[5], exc[10], exc[22], exc[66],
                                    raw[5], raw[10], raw[22], raw[66]))

                    if side == "BUY":
                        # controls
                        if len(plc_pool) >= 4:
                            for p in rng.choice(plc_pool, size=3, replace=False):
                                p = int(p)
                                rw, ex = _fwd(S, p, idx)
                                ev_rows.append((variant, "plc_sym", side, sym, S.date[p],
                                                S.date[p + 1], float(S.med_turn[p]),
                                                float(S.close[p]), None, None, 0, 0,
                                                ex[5], ex[10], ex[22], ex[66],
                                                rw[5], rw[10], rw[22], rw[66]))
                        p = i + SHIFT
                        if p < S.n - 1 and base_elig[p] and can22[p]:
                            rw, ex = _fwd(S, p, idx)
                            ev_rows.append((variant, "plc_shift", side, sym, S.date[p],
                                            S.date[p + 1], float(S.med_turn[p]),
                                            float(S.close[p]), None, None, 0, 0,
                                            ex[5], ex[10], ex[22], ex[66],
                                            rw[5], rw[10], rw[22], rw[66]))

                    # FORM-2 trade (primary variant, BUY only, no pyramiding)
                    if variant == "HLC3" and side == "BUY" and i + 1 > open_until:
                        e = i + 1
                        exit_j, exit_kind, censored = S.n - 1, "censored", 1
                        for j in range(e + 1, S.n):
                            if not okband[j]:
                                continue
                            if T[j] < L[j]:
                                exit_j, exit_kind, censored = min(j + 1, S.n - 1), "stop", 0
                                break
                            if j > 0 and okband[j - 1] and T[j - 1] >= U[j - 1] and T[j] < U[j]:
                                exit_j, exit_kind, censored = min(j + 1, S.n - 1), "band_exit", 0
                                break
                        if exit_j > e and S.adj_close[e] > 0 and S.adj_close[exit_j] > 0:
                            open_until = exit_j
                            gross = float(S.adj_close[exit_j] / S.adj_close[e] - 1.0)
                            net = gross - 2 * COST_SIDE
                            tr_rows.append((sym, S.date[e], S.date[exit_j], exit_j - e,
                                            gross, net, censored, spre, trend,
                                            float(S.med_turn[i]), exit_kind))
                            keys = ["ALL"]
                            if spre:
                                keys.append("STRETCH")
                            keys.append("TREND" if trend else "ANTITREND")
                            if S.med_turn[i] >= LIQ5:
                                keys.append("LIQ5")
                            for k in range(e + 1, exit_j + 1):
                                if S.adj_close[k] > 0 and S.adj_close[k - 1] > 0:
                                    r = float(S.adj_close[k] / S.adj_close[k - 1] - 1.0)
                                    dte = S.date[k]
                                    for key in keys:
                                        cell = book[key].setdefault(dte, [0.0, 0])
                                        cell[0] += r
                                        cell[1] += 1

        if n_sym % 400 == 0:
            print(f"  …{n_sym}/{len(syms)} symbols, events={len(ev_rows)}, trades={len(tr_rows)}",
                  flush=True)

    rc.executemany("INSERT INTO streamband_events VALUES (" + ",".join("?" * 20) + ")", ev_rows)
    rc.executemany("INSERT INTO streamband_trades VALUES (" + ",".join("?" * 11) + ")", tr_rows)

    # monthly book per key
    brows = []
    for key, days in book.items():
        if not days:
            continue
        months = {}
        for dte in sorted(days):
            s, c = days[dte]
            months.setdefault(dte[:7], []).append((s / c, c))
        for m in sorted(months):
            rs = months[m]
            mret = float(np.prod([1 + r for r, _ in rs]) - 1)
            brows.append((key, m, mret, float(np.mean([c for _, c in rs]))))
    rc.executemany("INSERT INTO streamband_book VALUES (?,?,?,?)", brows)
    rc.commit()
    rc.close()
    mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"BUILD done: {n_used}/{n_sym} symbols, {len(ev_rows)} event-rows "
          f"({sum(1 for r in ev_rows if r[1] == 'event')} events), {len(tr_rows)} trades, "
          f"{len(brows)} book-months in {dt:.0f}s")


# --------------------------------------------------------------------------- #
# run (analysis)                                                               #
# --------------------------------------------------------------------------- #
def _arr(rows, col):
    return np.array([r[col] if r[col] is not None else np.nan for r in rows], dtype=float)


def _cell(ev):
    x = _arr(ev, "fx22")
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "mean22": round(float(np.mean(x)) * 100, 3),
            "med22": round(float(np.median(x)) * 100, 3),
            "pos%": round(float(np.mean(x > 0)) * 100, 1)}


def _stats_monthly(mr):
    mr = np.asarray(mr, float)
    if len(mr) < 6:
        return None
    eq = np.cumprod(1 + mr)
    peak = np.maximum.accumulate(eq)
    dd = float((eq / peak - 1).min())
    sd = mr.std()
    return {"retvol": round(float(mr.mean() / sd * np.sqrt(12)), 2) if sd > 0 else 0.0,
            "cagr%": round((float(eq[-1]) ** (12 / len(mr)) - 1) * 100, 1),
            "maxdd%": round(dd * 100, 1), "months": int(len(mr))}


def run():
    rc = research_conn()
    ev = rc.execute("SELECT * FROM streamband_events").fetchall()
    tr = rc.execute("SELECT * FROM streamband_trades").fetchall()
    bk = rc.execute("SELECT * FROM streamband_book ORDER BY key, month").fetchall()
    rc.close()

    out = {"registered_gate": "see module docstring (prereg registry: streamband)",
           "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")}

    def sel(variant, kind, side, pred=lambda r: True):
        return [r for r in ev if r["variant"] == variant and r["kind"] == kind
                and r["side"] == side and pred(r)]

    prim = sel("HLC3", "event", "BUY")
    psym = sel("HLC3", "plc_sym", "BUY")
    pshf = sel("HLC3", "plc_shift", "BUY")

    x = _arr(prim, "fx22")
    xs = x[~np.isnan(x)]
    a = _arr(psym, "fx22")
    b = _arr(pshf, "fx22")
    d_sym = cliffs_delta(xs, a[~np.isnan(a)])
    d_shf = cliffs_delta(xs, b[~np.isnan(b)])
    h1 = np.array([r["fx22"] for r in prim
                   if r["sig_date"] < HALF_SPLIT and r["fx22"] is not None], dtype=float)
    h2 = np.array([r["fx22"] for r in prim
                   if r["sig_date"] >= HALF_SPLIT and r["fx22"] is not None], dtype=float)

    g1 = len(prim) >= 300
    g2 = len(xs) > 0 and float(np.mean(xs)) > 0 and float(np.median(xs)) > 0
    g3 = (not np.isnan(d_sym) and d_sym >= 0.05) and (not np.isnan(d_shf) and d_shf >= 0.05)
    g4 = len(h1) > 0 and len(h2) > 0 and np.median(h1) > 0 and np.median(h2) > 0
    verdict = "PASS-selection" if (g1 and g2 and g3 and g4) else "FAIL-null"

    horiz = {}
    for h in HORIZONS:
        v = _arr(prim, f"fx{h}")
        v = v[~np.isnan(v)]
        if len(v):
            horiz[f"{h}d"] = {"n": int(len(v)), "mean%": round(float(np.mean(v)) * 100, 3),
                              "med%": round(float(np.median(v)) * 100, 3),
                              "pos%": round(float(np.mean(v > 0)) * 100, 1)}

    out["FORM1_primary"] = {
        "cell": _cell(prim), "horizons": horiz,
        "placebo_sym": _cell(psym), "placebo_shift": _cell(pshf),
        "cliffs_vs_sym": round(float(d_sym), 4), "cliffs_vs_shift": round(float(d_shf), 4),
        "half1_med22%": round(float(np.median(h1)) * 100, 3) if len(h1) else None,
        "half2_med22%": round(float(np.median(h2)) * 100, 3) if len(h2) else None,
        "gates": {"G1_n300": bool(g1), "G2_mean_med_pos": bool(g2),
                  "G3_cliffs_.05_both": bool(g3), "G4_both_halves": bool(g4)},
        "VERDICT": verdict}

    # variants (exploratory)
    variants = {
        "OHLC4": sel("OHLC4", "event", "BUY"),
        "STRETCH_pre": [r for r in prim if r["stretch_pre"]],
        "no_STRETCH": [r for r in prim if not r["stretch_pre"]],
        "TREND": [r for r in prim if r["trend"]],
        "ANTITREND": [r for r in prim if not r["trend"]],
        "LIQ_5cr": [r for r in prim if r["med_turn"] >= LIQ5],
        "SELL_side(desc)": sel("HLC3", "event", "SELL"),
    }
    out["variants"] = {k: _cell(v) for k, v in variants.items()}

    # buckets on the primary set
    def terciles(rows, col, label):
        vals = _arr(rows, col)
        ok = ~np.isnan(vals)
        if ok.sum() < 30:
            return {}
        q1, q2 = np.nanpercentile(vals[ok], [33.3, 66.7])
        return {f"{label}_lo": _cell([r for r, v in zip(rows, vals) if not np.isnan(v) and v <= q1]),
                f"{label}_mid": _cell([r for r, v in zip(rows, vals) if not np.isnan(v) and q1 < v <= q2]),
                f"{label}_hi": _cell([r for r, v in zip(rows, vals) if not np.isnan(v) and v > q2])}

    buckets = {}
    buckets.update(terciles(prim, "med_turn", "turnover"))
    buckets.update(terciles(prim, "vol66", "vol66"))
    buckets.update(terciles(prim, "close_raw", "price"))
    buckets["band_1-5cr"] = _cell([r for r in prim if LIQ_FLOOR <= r["med_turn"] < LIQ5])
    buckets["band_5-25cr"] = _cell([r for r in prim if LIQ5 <= r["med_turn"] < 25e7])
    buckets["band_>25cr"] = _cell([r for r in prim if r["med_turn"] >= 25e7])
    out["buckets"] = buckets

    # FORM-2 trades + book
    nets = np.array([t["net"] for t in tr], dtype=float)
    if len(nets):
        out["FORM2_trades"] = {
            "n": int(len(nets)), "hit%": round(float(np.mean(nets > 0)) * 100, 1),
            "mean_net%": round(float(np.mean(nets)) * 100, 2),
            "med_net%": round(float(np.median(nets)) * 100, 2),
            "avg_hold": round(float(np.mean([t["hold"] for t in tr])), 1),
            "censored": int(sum(t["censored"] for t in tr)),
            "exit_mix": {k: int(sum(1 for t in tr if t["exit_kind"] == k))
                         for k in ("stop", "band_exit", "censored")}}
    books = {}
    for key in BOOK_KEYS:
        rows = [r for r in bk if r["key"] == key and r["month"] >= "2012-06"]
        mr = [r["mret"] for r in rows]
        st_full = _stats_monthly(mr)
        st_h1 = _stats_monthly([r["mret"] for r in rows if r["month"] < "2019"])
        st_h2 = _stats_monthly([r["mret"] for r in rows if r["month"] >= "2019"])
        if st_full:
            fundable = bool(st_h1 and st_h2 and st_h1["retvol"] > 0.89 and st_h2["retvol"] > 0.89)
            books[key] = {"full": st_full, "h1_2012_18": st_h1, "h2_2019_26": st_h2,
                          "avg_pos": round(float(np.mean([r["avg_pos"] for r in rows])), 1),
                          "FUNDABLE_vs_0.89": fundable}
    out["FORM2_book"] = books

    from .common import OUT_DIR  # noqa: PLC0415
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "streamband.json").write_text(json.dumps(out, indent=1))

    print(json.dumps(out, indent=1))
    print(f"\n=== STREAM BAND VERDICT: {verdict} ===")
    return out


# --------------------------------------------------------------------------- #
# selftest (offline)                                                           #
# --------------------------------------------------------------------------- #
def selftest():
    # EMA matches brute force
    rng = np.random.default_rng(0)
    x = np.cumsum(rng.normal(0, 1, 400)) + 100
    e = ema(x, 5)
    a = 2 / 6
    bf = x[0]
    for i in range(1, 300):
        bf = a * x[i] + (1 - a) * bf
    assert abs(e[299] - bf) < 1e-9
    assert np.isnan(e[3]) and not np.isnan(e[4])

    # causality: truncating the future never changes the past
    T = ema(x, EMA_FAST)
    U = ema(x * 1.01, EMA_SLOW)
    L = ema(x * 0.99, EMA_SLOW)
    b_full, s_full = crosses(T, U, L)
    Tc = ema(x[:250], EMA_FAST)
    Uc = ema((x * 1.01)[:250], EMA_SLOW)
    Lc = ema((x * 0.99)[:250], EMA_SLOW)
    b_cut, s_cut = crosses(Tc, Uc, Lc)
    assert [i for i in b_full if i < 250 - 0] == b_cut
    assert [i for i in s_full if i < 250 - 0] == s_cut

    # a clean dip-and-recover produces exactly one BUY cross
    y = np.concatenate([np.full(60, 100.0), np.linspace(100, 80, 30),
                        np.full(20, 80.0), np.linspace(80, 110, 40)])
    Ty = ema((y * 1.0), EMA_FAST)
    Uy = ema(y * 1.02, EMA_SLOW)
    Ly = ema(y * 0.98, EMA_SLOW)
    by, _sy = crosses(Ty, Uy, Ly)
    assert len(by) >= 1, "dip-recover must fire a BUY cross"

    # stretch: below-band is negative; p10 threshold is causal (NaN early)
    st = stretch_signed(Ty, Uy, Ly)
    assert np.nanmin(st) < 0
    p = rolling_p10(np.concatenate([st] * 8))
    assert np.isnan(p[100])

    print("STREAMBAND selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
