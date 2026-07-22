"""REVERSAL — CLEAN oversold-bounce: deep drawdown + RSI-oversold turn. PRE-REGISTERED 2026-07-22b.
The reversal LINE as a distinct, fresh approach — reversal-native features ONLY (NO RS, NO momentum).

WHY / WHAT IS NEW. The reversal-pair arc falsified the BAND-RECLAIM definition of reversal at every
level (07-13 anti-signal · 07-14/14b fractal inert/no-capacity · 07-14c reclaim-selection δ+0.004≈0
on 8 price/vol features). This study uses a DIFFERENT, cleaner reversal definition that was never
run: a classic oversold bounce — the stock is ≥25% below its trailing 252-day high (deep drawdown)
AND its price RSI(14) turns UP through 30 (recently oversold, now recovering). That event set is
distinct from the EMA-band reclaim. Per Ramana's 2026-07-22 directive this line is kept SEPARATE
from the momentum line — it uses NO relative-strength / momentum conditioning; hybrids are deferred.

PREDICTION ON RECORD (failure-ledger contract, before the run): prior is FAIL (07-13 showed early
band-reclaims are falling knives; 07-14c showed price/vol selection is inert). But the oversold-turn
definition is genuinely untested and mean-reversion is a real anomaly elsewhere, so it earns one
clean pre-registered look. Cite 07-13/14/14b/14c.

TWO-GATE FRAME (report BOTH, diagnose which fails). Gate-1 SELECTION (gross, event level): does the
entry pick future out-performers vs placebo? Gate-2 FUNDABILITY (net): does the book beat the
Nifty-500 0.89 return/vol hurdle net of realistic cost? Orthogonal.

METRIC BASIS (D142): every ratio is annualised mean/sd, no risk-free subtracted — a return/vol
ratio, not a Sharpe; the 0.89 hurdle is on the same basis. Descriptive-only, SEBI-safe.

DESIGN (locked before first run; seed 42; sorted symbols; CA-ADJUSTED prices throughout). Universe =
every EQ/CM symbol in bhavcopy_rows, signal dates >= 2012-06-01. Price RSI = Wilder(14) on adj_close.
252d high = trailing rolling max of adj_close (causal, incl. current bar); drawdown = adj_close/high
− 1. Eligibility at bar i: >=260 prior rows; trailing med_turn >= Rs 1cr; raw close >= 20; calendar
gap <= 6d around i; RSI/drawdown finite. De-overlap 22 bars/symbol for events; one open trade/symbol
for the book.

EVENT (oversold-bounce BUY): drawdown[i] <= −0.25 (>=25% off the 252d high) AND RSI[i−1] <= 30 AND
RSI[i] > 30 (RSI crosses UP through 30). Entry = CLOSE of i+1 (PIT). Horizons 5/10/22/66 bars; excess
= raw forward return − Nifty-500 over the identical span. Controls: 3 same-symbol random eligible-bar
placebos + one +63-bar time-shift placebo.

GATE-1 (SELECTION; PASS requires ALL FOUR, else FAIL-null):
  G1  n >= 300 primary events
  G2  mean AND median 22d excess > 0
  G3  Cliff's delta of 22d excess vs BOTH placebo sets >= +0.05
  G4  median 22d excess > 0 in BOTH halves (< / >= 2019-01-01)
Reversal-native conditioner buckets (exploratory, NO promotion without fresh prereg; NO RS/momentum):
drawdown-depth terciles, vol66 terciles, dist-below-200SMA terciles, prior-126d-return terciles.

GATE-2 BOOK (for the record; fundable bar). Long at entry close; exit on the FIRST of: RSI >= 60
(mean-reversion target) · close below the ratcheting 2°-down-fractal (stop) · 66-bar time stop. One
open trade/symbol. Daily equal-weight across open trades; tiered round-trip cost (half-spread by
liquidity + Zerodha delivery + stop slippage); cost booked as entry-day friction. RAW (gross) and
NET books both reported. FUNDABLE requires NET monthly return/vol > 0.89 in BOTH halves. Control =
random eligible-entry, same exit + cost (does the oversold ENTRY add value over the exit geometry?).

DISPOSITION (pre-committed). Gate-1 PASS + Gate-2 book > 0.89 both halves + beats random by >=+0.15
-> NEW candidate (fresh fences before any promotion). ELSE -> REJECTED, descriptive-only; ledger
entry cites 07-13/14/14b/14c and records WHICH gate failed.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.reversal_oversold --build   # events+trades+books -> research.db
  ... --run        # analysis -> out/reversal_oversold.json + printed report + VERDICT
  ... --selftest   # offline synthetic checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .common import (LIQ_FLOOR, OUT_DIR, SymbolSeries, cliffs_delta, eq_symbols,
                     load_series, main_conn, research_conn)
from .streamband import roll_mean, roll_std
from .momentum_band_rsi import (_Idx, _accum_book, _arr, _book_stats, _cost_rt,
                                _fwd, _stats_monthly, latest_down_fractal, rsi_wilder)

RSI_N = 14
DD_DEEP = -0.25          # >=25% below the trailing 252d high
RSI_OS = 30.0            # oversold; event = RSI crosses UP through this
RSI_TARGET = 60.0        # mean-reversion book target
TIME_STOP = 66
HI_WIN = 252
HORIZONS = (5, 10, 22, 66)
START = "2012-06-01"
HALF_SPLIT = "2019-01-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
DEOVERLAP = 22
SHIFT = 63
SEED = 42
LIQ5 = 5e7
BOOK_KEYS = ("REVDD", "RANDOM_CTL")


def rolling_max(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing max over the w bars ending at i (causal). NaN before the first full window."""
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    sw = sliding_window_view(x, w)
    with np.errstate(invalid="ignore"):
        out[w - 1:] = np.nanmax(sw, axis=1)
    return out


def _sim_rev(S, e, R, dfrac):
    """Mean-reversion exit: first of RSI>=target / close<ratcheting 2-fractal / time stop."""
    n = S.n
    stop = dfrac[e] if not np.isnan(dfrac[e]) else -np.inf
    exit_j, kind = n - 1, "time"
    for j in range(e + 1, n):
        if np.isnan(R[j]):
            continue
        if not np.isnan(dfrac[j]) and dfrac[j] > stop:
            stop = dfrac[j]
        if R[j] >= RSI_TARGET:
            exit_j, kind = min(j + 1, n - 1), "target"
            break
        if S.adj_close[j] < stop:
            exit_j, kind = min(j + 1, n - 1), "frac_stop"
            break
        if j - e >= TIME_STOP:
            exit_j, kind = min(j + 1, n - 1), "time"
            break
    p0 = S.adj_close[e]
    gross = float(S.adj_close[exit_j] / p0 - 1.0) if p0 > 0 and S.adj_close[exit_j] > 0 else np.nan
    return exit_j, kind, gross


_DDL = """
DROP TABLE IF EXISTS rev_events;
CREATE TABLE rev_events(
  kind TEXT, symbol TEXT, sig_date TEXT, entry_date TEXT, med_turn REAL, close_raw REAL,
  ddepth REAL, vol66 REAL, dist200 REAL, ret126 REAL,
  fx5 REAL, fx10 REAL, fx22 REAL, fx66 REAL, fr5 REAL, fr10 REAL, fr22 REAL, fr66 REAL);
DROP TABLE IF EXISTS rev_trades;
CREATE TABLE rev_trades(
  symbol TEXT, entry_date TEXT, exit_date TEXT, hold INT, med_turn REAL, exit_kind TEXT,
  gross REAL, net REAL, cost_rt REAL);
DROP TABLE IF EXISTS rev_book;
CREATE TABLE rev_book(key TEXT, gross_net TEXT, month TEXT, mret REAL, avg_pos REAL);
"""


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript(_DDL)
    idx = _Idx()
    rng = np.random.default_rng(SEED)
    syms = eq_symbols(mc)

    ev_rows, tr_rows = [], []
    book = {(k, g): {} for k in BOOK_KEYS for g in ("gross", "net")}
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

        R = rsi_wilder(S.adj_close, RSI_N)
        hi = rolling_max(S.adj_close, HI_WIN)
        with np.errstate(invalid="ignore", divide="ignore"):
            dd = S.adj_close / hi - 1.0
        sma200 = roll_mean(S.adj_close, 200)
        vol66 = roll_std(S.ret_raw, 66)
        dfrac = latest_down_fractal(S.adj_low, 2)

        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START) & ~np.isnan(R))
        can22 = np.zeros(S.n, dtype=bool)
        lim = S.n - 1 - 23
        if lim > 0:
            can22[:lim] = True

        ev = np.zeros(S.n, dtype=bool)
        for i in range(1, S.n):
            if (not np.isnan(R[i]) and not np.isnan(R[i - 1]) and not np.isnan(dd[i])
                    and R[i - 1] <= RSI_OS and R[i] > RSI_OS and dd[i] <= DD_DEEP):
                ev[i] = True
        hits = np.where(ev)[0]

        plc_pool = np.where(base_elig & can22)[0]
        last_ev = -10**9
        open_until = -1

        for i in hits:
            if not base_elig[i] or i + 1 >= S.n or np.isnan(R[i + 1]):
                continue
            if i - last_ev < DEOVERLAP:
                continue
            last_ev = i
            dist200 = float(S.adj_close[i] / sma200[i] - 1.0) if not np.isnan(sma200[i]) else None
            ret126 = float(S.adj_close[i] / S.adj_close[i - 126] - 1.0) if i >= 126 and S.adj_close[i - 126] > 0 else None
            raw, exc = _fwd(S, i, idx)
            ev_rows.append(("event", sym, S.date[i], S.date[i + 1], float(S.med_turn[i]),
                            float(S.close[i]), float(dd[i]),
                            float(vol66[i]) if not np.isnan(vol66[i]) else None, dist200, ret126,
                            exc[5], exc[10], exc[22], exc[66], raw[5], raw[10], raw[22], raw[66]))
            if len(plc_pool) >= 4:
                for p in rng.choice(plc_pool, size=3, replace=False):
                    p = int(p)
                    rw, ex = _fwd(S, p, idx)
                    ev_rows.append(("plc_sym", sym, S.date[p], S.date[p + 1], float(S.med_turn[p]),
                                    float(S.close[p]), None, None, None, None,
                                    ex[5], ex[10], ex[22], ex[66], rw[5], rw[10], rw[22], rw[66]))
            p = i + SHIFT
            if p < S.n - 1 and base_elig[p] and can22[p]:
                rw, ex = _fwd(S, p, idx)
                ev_rows.append(("plc_shift", sym, S.date[p], S.date[p + 1], float(S.med_turn[p]),
                                float(S.close[p]), None, None, None, None,
                                ex[5], ex[10], ex[22], ex[66], rw[5], rw[10], rw[22], rw[66]))

            e = i + 1
            if i + 1 > open_until:
                exit_j, kind, gross = _sim_rev(S, e, R, dfrac)
                if exit_j > e and S.adj_close[e] > 0 and not np.isnan(gross):
                    open_until = exit_j
                    crt = _cost_rt(float(S.med_turn[i]), kind in ("frac_stop", "target", "time"))
                    net = gross - crt
                    tr_rows.append((sym, S.date[e], S.date[exit_j], int(exit_j - e),
                                    float(S.med_turn[i]), kind, gross, net, crt))
                    _accum_book(book, "REVDD", "gross", e, exit_j, S, crt)
                    _accum_book(book, "REVDD", "net", e, exit_j, S, crt)

            if len(plc_pool) >= 1:
                rp = int(rng.choice(plc_pool))
                if rp + 1 < S.n and not np.isnan(R[rp + 1]):
                    ce = rp + 1
                    xj, ck, cg = _sim_rev(S, ce, R, dfrac)
                    if xj > ce and S.adj_close[ce] > 0 and not np.isnan(cg):
                        crt = _cost_rt(float(S.med_turn[rp]), ck != "time")
                        _accum_book(book, "RANDOM_CTL", "gross", ce, xj, S, crt)
                        _accum_book(book, "RANDOM_CTL", "net", ce, xj, S, crt)

        if n_sym % 400 == 0:
            print(f"  …{n_sym}/{len(syms)} symbols, events="
                  f"{sum(1 for r in ev_rows if r[0]=='event')}, trades={len(tr_rows)}", flush=True)

    rc.executemany("INSERT INTO rev_events VALUES (" + ",".join("?" * 18) + ")", ev_rows)
    rc.executemany("INSERT INTO rev_trades VALUES (" + ",".join("?" * 9) + ")", tr_rows)
    brows = []
    for (key, gnet), days in book.items():
        if not days:
            continue
        months = {}
        for dte in sorted(days):
            s, c = days[dte]
            if c > 0:
                months.setdefault(dte[:7], []).append((s / c, c))
        for m in sorted(months):
            rs = months[m]
            mret = float(np.prod([1 + r for r, _ in rs]) - 1)
            brows.append((key, gnet, m, mret, float(np.mean([c for _, c in rs]))))
    rc.executemany("INSERT INTO rev_book VALUES (?,?,?,?,?)", brows)
    rc.commit()
    rc.close()
    mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"BUILD done: {n_used}/{n_sym} symbols, "
          f"{sum(1 for r in ev_rows if r[0]=='event')} events, {len(tr_rows)} trades, "
          f"{len(brows)} book rows in {dt:.0f}s")


def _cell(ev):
    x = _arr(ev, "fx22")
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "mean22": round(float(np.mean(x)) * 100, 3),
            "med22": round(float(np.median(x)) * 100, 3), "pos%": round(float(np.mean(x > 0)) * 100, 1)}


def run():
    rc = research_conn()
    ev = rc.execute("SELECT * FROM rev_events").fetchall()
    tr = rc.execute("SELECT * FROM rev_trades").fetchall()
    bk = rc.execute("SELECT * FROM rev_book").fetchall()
    rc.close()

    out = {"registered_gate": "see module docstring (prereg: reversal_oversold)",
           "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "prediction": "FAIL expected (07-13/14c priors); genuinely-new definition"}

    prim = [r for r in ev if r["kind"] == "event"]
    psym = [r for r in ev if r["kind"] == "plc_sym"]
    pshf = [r for r in ev if r["kind"] == "plc_shift"]
    x = _arr(prim, "fx22"); xs = x[~np.isnan(x)]
    a = _arr(psym, "fx22"); b = _arr(pshf, "fx22")
    d_sym = cliffs_delta(xs, a[~np.isnan(a)]) if len(xs) else float("nan")
    d_shf = cliffs_delta(xs, b[~np.isnan(b)]) if len(xs) else float("nan")
    h1 = np.array([r["fx22"] for r in prim if r["sig_date"] < HALF_SPLIT and r["fx22"] is not None], float)
    h2 = np.array([r["fx22"] for r in prim if r["sig_date"] >= HALF_SPLIT and r["fx22"] is not None], float)
    g1 = len(prim) >= 300
    g2 = len(xs) > 0 and float(np.mean(xs)) > 0 and float(np.median(xs)) > 0
    g3 = (not np.isnan(d_sym) and d_sym >= 0.05) and (not np.isnan(d_shf) and d_shf >= 0.05)
    g4 = len(h1) > 0 and len(h2) > 0 and np.median(h1) > 0 and np.median(h2) > 0
    ev_verdict = "PASS-signal" if (g1 and g2 and g3 and g4) else "FAIL-null"

    horiz = {}
    for h in HORIZONS:
        v = _arr(prim, f"fx{h}"); v = v[~np.isnan(v)]
        if len(v):
            horiz[f"{h}d"] = {"n": int(len(v)), "mean%": round(float(np.mean(v)) * 100, 3),
                              "med%": round(float(np.median(v)) * 100, 3), "pos%": round(float(np.mean(v > 0)) * 100, 1)}

    def terciles(col, label):
        vals = _arr(prim, col); ok = ~np.isnan(vals)
        if ok.sum() < 60:
            return {}
        q1, q2 = np.nanpercentile(vals[ok], [33.3, 66.7])
        return {f"{label}_lo": _cell([r for r, v in zip(prim, vals) if not np.isnan(v) and v <= q1]),
                f"{label}_mid": _cell([r for r, v in zip(prim, vals) if not np.isnan(v) and q1 < v <= q2]),
                f"{label}_hi": _cell([r for r, v in zip(prim, vals) if not np.isnan(v) and v > q2])}
    buckets = {}
    for col, lab in (("ddepth", "drawdown"), ("vol66", "vol66"), ("dist200", "dist200"), ("ret126", "ret126")):
        buckets.update(terciles(col, lab))

    out["GATE1_selection"] = {
        "cell": _cell(prim), "horizons": horiz, "placebo_sym": _cell(psym), "placebo_shift": _cell(pshf),
        "cliffs_vs_sym": round(float(d_sym), 4) if not np.isnan(d_sym) else None,
        "cliffs_vs_shift": round(float(d_shf), 4) if not np.isnan(d_shf) else None,
        "half1_med22%": round(float(np.median(h1)) * 100, 3) if len(h1) else None,
        "half2_med22%": round(float(np.median(h2)) * 100, 3) if len(h2) else None,
        "gates": {"G1_n300": bool(g1), "G2_mean_med_pos": bool(g2), "G3_cliffs_.05_both": bool(g3),
                  "G4_both_halves": bool(g4)},
        "conditioner_buckets(reversal-native)": buckets, "VERDICT": ev_verdict}

    nets = np.array([t["net"] for t in tr], float)
    gr = np.array([t["gross"] for t in tr], float)
    if len(nets):
        out["GATE2_trades"] = {
            "n": int(len(nets)), "success%(net>0)": round(float(np.mean(nets > 0)) * 100, 1),
            "mean_gross%": round(float(np.mean(gr)) * 100, 2), "mean_net%": round(float(np.mean(nets)) * 100, 2),
            "med_net%": round(float(np.median(nets)) * 100, 2), "avg_hold": round(float(np.mean([t["hold"] for t in tr])), 1),
            "exit_mix": {k: int(sum(1 for t in tr if t["exit_kind"] == k)) for k in ("target", "frac_stop", "time")}}
    rb_net = _book_stats(bk, "REVDD", "net"); rb_gross = _book_stats(bk, "REVDD", "gross")
    ctl_net = _book_stats(bk, "RANDOM_CTL", "net")
    out["BOOK_net"] = rb_net
    out["BOOK_gross(raw)"] = rb_gross
    out["BOOK_random_control_net"] = ctl_net
    out["CAGR_raw_vs_net"] = {"raw_cagr%": rb_gross["full"]["cagr%"] if rb_gross["full"] else None,
                              "net_cagr%": rb_net["full"]["cagr%"] if rb_net["full"] else None,
                              "cost_impact_cagr_pp": (round(rb_gross["full"]["cagr%"] - rb_net["full"]["cagr%"], 1)
                                                      if rb_gross["full"] and rb_net["full"] else None)}
    h1n = rb_net["h1_2012_18"]; h2n = rb_net["h2_2019_26"]
    g_book = bool(h1n and h2n and h1n["retvol"] > 0.89 and h2n["retvol"] > 0.89)
    g_better = bool(rb_net["full"] and ctl_net["full"] and (rb_net["full"]["retvol"] - ctl_net["full"]["retvol"]) >= 0.15)
    book_verdict = "PASS-book" if (g_book and g_better) else "FAIL"
    out["BOOK_gates"] = {"G_BOOK_0.89_both_halves": g_book, "G_BETTER_vs_random_+0.15": g_better,
                         "net_retvol_full": rb_net["full"]["retvol"] if rb_net["full"] else None,
                         "random_net_retvol_full": ctl_net["full"]["retvol"] if ctl_net["full"] else None,
                         "VERDICT": book_verdict}
    out["OVERALL_VERDICT"] = "PASS" if book_verdict == "PASS-book" else "REJECTED (descriptive-only)"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "reversal_oversold.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== GATE-1: {ev_verdict} | GATE-2 BOOK: {book_verdict} | OVERALL: {out['OVERALL_VERDICT']} ===")
    return out


def selftest():
    x = np.array([10, 12, 11, 15, 9, 8, 20], float)
    rm = rolling_max(x, 3)
    assert np.isnan(rm[1]) and rm[2] == 12 and rm[3] == 15 and rm[6] == 20, "rolling_max causal"
    # oversold turn: RSI must cross UP through 30 after a decline then bounce
    dn = np.concatenate([np.linspace(100, 60, 40), np.linspace(60, 75, 20)])
    R = rsi_wilder(dn, 14)
    turns = [i for i in range(1, len(dn)) if not np.isnan(R[i - 1]) and R[i - 1] <= 30 < R[i]]
    assert len(turns) >= 1, "a decline-then-bounce must produce an RSI up-cross through 30"
    print("REVERSAL_OVERSOLD selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
