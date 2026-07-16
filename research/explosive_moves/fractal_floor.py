"""FRACTAL FLOOR — Williams-fractal floor + up-fractal breakout trigger: PRE-REGISTERED (2026-07-14).

RAMANA'S SPEC (docs/reversal-pair-PLAN.md §1). A down-fractal of degree N = a bar whose adjusted LOW
is strictly below the lows of the N bars before AND the N bars after (confirmed, and therefore only
KNOWABLE, N bars later — every event here respects that lag). The confirmed fractal low is the FLOOR.
The stock is in WATCH while the close sits within +15 percent above a live floor (floor dies the bar a
close prints below it). The ENTRY trigger is his breakout rule: the close crosses above T1 = the most
recent CONFIRMED degree-2 up-fractal high formed after the floor bar (up-fractals that confirmed
before the floor itself confirmed still count — they formed after the trough and are knowable by
trigger time). STRONG flag = close also above T2 = the higher of the last two up-fractal highs
("beats the first two up-frac"). Primary degree N=10 (his emphasis: a held 10-fractal is a >=20-bar
consolidation by construction); N=5 and N=2 run as variants. Bear mirror DEFERRED (disclosed, not
silently dropped) — this study is the long side only.

LEDGER PRIOR (cited, blocking): STREAM BAND BUY-cross (2026-07-13) FAIL-null and ANTI-selects — 22d
excess mean -0.22 pct / median -1.25 pct, BOTH placebos beat it (delta -0.019/-0.027), book 0.37 vs
0.89; its one hypothesis-generating thread = heavy right skew (66d mean ~0, median -2.7) -> the open
question is CONFIRMATION and WHICH bounce, not the first reclaim. PULLBACK 0.56-0.72; S3 shakeout
-0.5 pct CAGR; raw-Wolfe book -2.1 pct median placebo-negative; Wolfe BULL SELECTION +4.4 pct medNet
is the only surviving reversal-family form. This study tests whether the structural breakout
confirmation (trigger) separates launchers from falling knives; the book is measured for the record
and EXPECTED to fail. DESCRIPTIVE-ONLY either way; no ranking, no advice.

DESIGN (locked before first run; seed 42; sorted-symbol order; same harness as streamband).
Universe = every EQ/CM symbol; signals >= 2012-06-01; eligibility at signal bar i: >=260 prior rows,
med_turn >= Rs 1cr, raw close >= 20, calendar gaps <= 6d at (i-1,i) and (i,i+1), floor age
i - floor_bar <= 252, proximity 0 < close/floor - 1 <= 0.15. De-overlap 22 bars per symbol per event
kind. PIT: signal on close of bar i -> entry close of bar i+1; horizons 5/10/22/66; excess vs
Nifty-500 over identical spans. EVENT KINDS: 'event' = the TRIGGER cross (close > T1, previous close
<= previous T1 or T1 newly knowable); 'watch' = first entry into the proximity band with NO trigger
requirement (the contrast cohort). CONTROLS: same-symbol random eligible bars x3 (seed 42) +
the same trigger shifted +63 bars; plus the excess transform.

FORM-1 GATE (selection; PASS requires ALL FOUR, judged ONLY on the D10 trigger cell):
  G1  n >= 300 D10 trigger events
  G2  mean AND median 22d excess > 0
  G3  Cliff's delta of 22d excess vs BOTH placebo sets >= +0.05
  G4  median 22d excess > 0 in BOTH halves (< / >= 2019-01-01)
SECONDARY CONTRAST (reported; cannot create a pass): Cliff's delta(trigger, watch) >= +0.05 would
support "the up-fractal confirmation adds value over mere floor proximity".

FORM-2 BOOK (for the record): long at entry close; trail = max(floor, every degree-2 down-fractal
low confirmed after entry, ratchet up only); exit close of the bar AFTER the first close < trail
(exit_kind floor_stop / trail_stop, censored at series end); one open trade per symbol; 0.3 pct per
side; daily equal-weight across open trades, monthly compounding; FUNDABLE bar = return/vol > 0.89
in BOTH halves 2012-18 / 2019-26.

METRIC BASIS (D142): every ratio reported here is mean/sd annualised with NO risk-free rate
subtracted — a return/vol ratio, not a Sharpe; it reads high against a textbook Sharpe. The 0.89
hurdle is computed on the SAME basis, so the verdict is unaffected.

VARIANTS (exploratory, no gate promotion): degree N=5, N=2; STRONG subset (close > T2); proximity
<= 0.10 and <= 0.05; TREND (close > SMA200) and ANTI-TREND; liquidity >= Rs 5cr. BUCKETS on the D10
trigger set: med_turn terciles + absolute bands (1-5cr / 5-25cr / >25cr), vol66 terciles, raw-price
terciles, floor-age terciles. Multiple-testing honesty: the gate is judged only on the primary cell.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.fractal_floor --build   # events+trades+book -> research.db
  ... --run                                      # analysis -> out/fractal_floor.json + report
  ... --selftest                                 # offline synthetic checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .common import LIQ_FLOOR, cliffs_delta, eq_symbols, load_series, main_conn, research_conn
from .streamband import (HORIZONS, _Idx, _arr, _cell, _fwd, _stats_monthly,
                         roll_mean, roll_std)

DEGREES = (10, 5, 2)
UPDEG = 2
PROX_MAX = 0.15
AGE_MAX = 252
DEOVERLAP = 22
START = "2012-06-01"
HALF_SPLIT = "2019-01-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
COST_SIDE = 0.003
SHIFT = 63
SEED = 42
LIQ5 = 5e7
BOOK_KEYS = ("ALL", "STRONG", "TREND", "PROX10", "LIQ5")


# --------------------------------------------------------------------------- #
# fractal primitives (strict inequality; NaN windows never qualify)             #
# --------------------------------------------------------------------------- #
def fractal_flags(x: np.ndarray, N: int, kind: str) -> np.ndarray:
    """True at bar f if x[f] is a strict extreme vs the N bars each side.
    kind='low' -> down-fractal on lows; kind='high' -> up-fractal on highs.
    The flag sits at f; it is only KNOWABLE at bar f+N (caller enforces)."""
    n = len(x)
    out = np.zeros(n, dtype=bool)
    w = 2 * N + 1
    if n < w:
        return out
    sw = sliding_window_view(x, w)                    # row k covers k..k+2N, center k+N
    center = sw[:, N]
    others = np.delete(sw, N, axis=1)
    ok = ~np.isnan(sw).any(axis=1)
    if kind == "low":
        ext = center < others.min(axis=1)
    else:
        ext = center > others.max(axis=1)
    out[N: n - N] = ok & ext
    return out


def scan(adj_close, adj_high, adj_low, N: int):
    """Pure state machine -> (triggers, watches, floors) for degree N.
    triggers: list of (i, floor_bar, floor_val, T1, strong)
    watches:  list of (i, floor_bar, floor_val)
    Causal by construction: a fractal at f is used only from bar f+deg onward."""
    n = len(adj_close)
    fr_lo = fractal_flags(adj_low, N, "low")
    fr_hi = fractal_flags(adj_high, UPDEG, "high")
    ups_all = []                     # confirmed up-fractals (bar, high), append at confirm time
    floor_bar, floor_val, alive = -1, np.nan, False
    ups = []                         # confirmed up-fractals with bar > floor_bar
    prev_t1 = np.nan
    prev_close = np.nan
    triggers, watches = [], []
    seen_watch = seen_trig = False
    for t in range(n):
        u = t - UPDEG
        if u >= 0 and fr_hi[u]:
            ups_all.append((u, adj_high[u]))
        f = t - N
        if f >= 0 and fr_lo[f] and not np.isnan(adj_low[f]):
            floor_bar, floor_val, alive = f, adj_low[f], True
            ups = [p for p in ups_all if p[0] > f]
            seen_watch = seen_trig = False
            prev_t1 = np.nan
        elif alive and u >= 0 and fr_hi[u] and u > floor_bar:
            ups.append((u, adj_high[u]))
        c = adj_close[t]
        if alive and not np.isnan(c) and c < floor_val:
            alive = False
        if alive and not np.isnan(c) and t >= floor_bar + N:
            prox = c / floor_val - 1.0
            t1 = ups[-1][1] if ups else np.nan
            t2 = max(ups[-1][1], ups[-2][1]) if len(ups) >= 2 else np.nan
            if 0.0 < prox <= PROX_MAX:
                if not seen_watch:
                    watches.append((t, floor_bar, floor_val))
                    seen_watch = True
                if (not seen_trig and not np.isnan(t1) and c > t1
                        and (np.isnan(prev_t1) or np.isnan(prev_close) or prev_close <= prev_t1)):
                    strong = int(not np.isnan(t2) and c > t2)
                    triggers.append((t, floor_bar, floor_val, t1, strong))
                    seen_trig = True
            prev_t1 = t1
        else:
            prev_t1 = np.nan
        prev_close = c
    return triggers, watches


# --------------------------------------------------------------------------- #
# build                                                                        #
# --------------------------------------------------------------------------- #
_DDL = """
DROP TABLE IF EXISTS fractal_events;
CREATE TABLE fractal_events(
  variant TEXT, kind TEXT, symbol TEXT, sig_date TEXT, entry_date TEXT,
  prox REAL, age INT, strong INT, trend INT, med_turn REAL, close_raw REAL, vol66 REAL,
  fx5 REAL, fx10 REAL, fx22 REAL, fx66 REAL, fr5 REAL, fr10 REAL, fr22 REAL, fr66 REAL);
DROP TABLE IF EXISTS fractal_trades;
CREATE TABLE fractal_trades(
  symbol TEXT, entry_date TEXT, exit_date TEXT, hold INT, gross REAL, net REAL,
  censored INT, exit_kind TEXT, prox REAL, age INT, strong INT, trend INT, med_turn REAL);
DROP TABLE IF EXISTS fractal_book;
CREATE TABLE fractal_book(key TEXT, month TEXT, mret REAL, avg_pos REAL);
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
        sma200 = roll_mean(S.adj_close, 200)
        vol66 = roll_std(S.ret_raw, 66)
        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START))
        can22 = np.zeros(S.n, dtype=bool)
        lim = S.n - 1 - 23
        if lim > 0:
            can22[:lim] = True
        plc_pool = np.where(base_elig & can22)[0]
        fr_lo2 = fractal_flags(S.adj_low, UPDEG, "low")      # for the trade trail

        for N in DEGREES:
            variant = f"D{N}"
            triggers, watches = scan(S.adj_close, S.adj_high, S.adj_low, N)
            last = {"event": -10**9, "watch": -10**9}
            open_until = -1

            def emit(kind, i, prox, age, strong, sig_sym=sym, SS=S):
                trend = int(not np.isnan(sma200[i]) and SS.adj_close[i] > sma200[i])
                raw, exc = _fwd(SS, i, idx)
                ev_rows.append((variant, kind, sig_sym, SS.date[i], SS.date[i + 1],
                                round(float(prox), 5) if prox is not None else None,
                                int(age) if age is not None else None,
                                strong, trend, float(SS.med_turn[i]), float(SS.close[i]),
                                float(vol66[i]) if not np.isnan(vol66[i]) else None,
                                exc[5], exc[10], exc[22], exc[66],
                                raw[5], raw[10], raw[22], raw[66]))
                return trend

            for (i, fb, fv, t1, strong) in triggers:
                if not base_elig[i] or i + 1 >= S.n or i - fb > AGE_MAX:
                    continue
                if i - last["event"] < DEOVERLAP:
                    continue
                last["event"] = i
                prox = S.adj_close[i] / fv - 1.0
                trend = emit("event", i, prox, i - fb, strong)

                # controls (trigger events only)
                if len(plc_pool) >= 4:
                    for p in rng.choice(plc_pool, size=3, replace=False):
                        p = int(p)
                        rw, ex = _fwd(S, p, idx)
                        ev_rows.append((variant, "plc_sym", sym, S.date[p], S.date[p + 1],
                                        None, None, 0, 0, float(S.med_turn[p]),
                                        float(S.close[p]), None,
                                        ex[5], ex[10], ex[22], ex[66],
                                        rw[5], rw[10], rw[22], rw[66]))
                p = i + SHIFT
                if p < S.n - 1 and base_elig[p] and can22[p]:
                    rw, ex = _fwd(S, p, idx)
                    ev_rows.append((variant, "plc_shift", sym, S.date[p], S.date[p + 1],
                                    None, None, 0, 0, float(S.med_turn[p]),
                                    float(S.close[p]), None,
                                    ex[5], ex[10], ex[22], ex[66],
                                    rw[5], rw[10], rw[22], rw[66]))

                # FORM-2 trade (D10 only, no pyramiding)
                if N == 10 and i + 1 > open_until:
                    e = i + 1
                    trail = fv
                    exit_j, exit_kind, censored = S.n - 1, "censored", 1
                    for j in range(e + 1, S.n):
                        f2 = j - UPDEG
                        if f2 > i and fr_lo2[f2] and not np.isnan(S.adj_low[f2]):
                            trail = max(trail, float(S.adj_low[f2]))
                        cj = S.adj_close[j]
                        if not np.isnan(cj) and cj < trail:
                            exit_j = min(j + 1, S.n - 1)
                            exit_kind = "floor_stop" if trail == fv else "trail_stop"
                            censored = 0
                            break
                    if exit_j > e and S.adj_close[e] > 0 and S.adj_close[exit_j] > 0:
                        open_until = exit_j
                        gross = float(S.adj_close[exit_j] / S.adj_close[e] - 1.0)
                        tr_rows.append((sym, S.date[e], S.date[exit_j], exit_j - e, gross,
                                        gross - 2 * COST_SIDE, censored, exit_kind,
                                        round(float(prox), 5), i - fb, strong, trend,
                                        float(S.med_turn[i])))
                        # ⚠ DEFECT (recorded, ledger § Study 2026-07-14b): this book never
                        # charges the documented 0.3%/side — its return/vol ratios are
                        # GROSS. Kept as-run (the committed JSON is evidence);
                        # fractal_fences.py is the corrected accounting (flat-cost
                        # PROX10 = 0.59, not 1.04).
                        keys = ["ALL"]
                        if strong:
                            keys.append("STRONG")
                        if trend:
                            keys.append("TREND")
                        if prox <= 0.10:
                            keys.append("PROX10")
                        if S.med_turn[i] >= LIQ5:
                            keys.append("LIQ5")
                        for k in range(e + 1, exit_j + 1):
                            if S.adj_close[k] > 0 and S.adj_close[k - 1] > 0:
                                r = float(S.adj_close[k] / S.adj_close[k - 1] - 1.0)
                                for key in keys:
                                    cell = book[key].setdefault(S.date[k], [0.0, 0])
                                    cell[0] += r
                                    cell[1] += 1

            for (i, fb, fv) in watches:
                if not base_elig[i] or i + 1 >= S.n or i - fb > AGE_MAX:
                    continue
                if i - last["watch"] < DEOVERLAP:
                    continue
                last["watch"] = i
                emit("watch", i, S.adj_close[i] / fv - 1.0, i - fb, 0)

        if n_sym % 400 == 0:
            print(f"  …{n_sym}/{len(syms)} symbols, rows={len(ev_rows)}, trades={len(tr_rows)}",
                  flush=True)

    rc.executemany("INSERT INTO fractal_events VALUES (" + ",".join("?" * 20) + ")", ev_rows)
    rc.executemany("INSERT INTO fractal_trades VALUES (" + ",".join("?" * 13) + ")", tr_rows)
    brows = []
    for key, days in book.items():
        months = {}
        for dte in sorted(days):
            s, c = days[dte]
            months.setdefault(dte[:7], []).append((s / c, c))
        for m in sorted(months):
            rs = months[m]
            brows.append((key, m, float(np.prod([1 + r for r, _ in rs]) - 1),
                          float(np.mean([c for _, c in rs]))))
    rc.executemany("INSERT INTO fractal_book VALUES (?,?,?,?)", brows)
    rc.commit()
    rc.close()
    mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    n_ev = sum(1 for r in ev_rows if r[1] == "event")
    n_w = sum(1 for r in ev_rows if r[1] == "watch")
    print(f"BUILD done: {n_used}/{n_sym} symbols, {len(ev_rows)} rows "
          f"({n_ev} triggers, {n_w} watches), {len(tr_rows)} trades, "
          f"{len(brows)} book-months in {dt:.0f}s")


# --------------------------------------------------------------------------- #
# run                                                                          #
# --------------------------------------------------------------------------- #
def run():
    rc = research_conn()
    ev = rc.execute("SELECT * FROM fractal_events").fetchall()
    tr = rc.execute("SELECT * FROM fractal_trades").fetchall()
    bk = rc.execute("SELECT * FROM fractal_book ORDER BY key, month").fetchall()
    rc.close()

    out = {"registered_gate": "see module docstring (prereg registry: fractal_floor)",
           "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")}

    def sel(variant, kind, pred=lambda r: True):
        return [r for r in ev if r["variant"] == variant and r["kind"] == kind and pred(r)]

    prim = sel("D10", "event")
    watch = sel("D10", "watch")
    psym = sel("D10", "plc_sym")
    pshf = sel("D10", "plc_shift")

    x = _arr(prim, "fx22")
    xs = x[~np.isnan(x)]
    a = _arr(psym, "fx22")
    b = _arr(pshf, "fx22")
    w = _arr(watch, "fx22")
    d_sym = cliffs_delta(xs, a[~np.isnan(a)])
    d_shf = cliffs_delta(xs, b[~np.isnan(b)])
    d_watch = cliffs_delta(xs, w[~np.isnan(w)])
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

    out["FORM1_primary_D10_trigger"] = {
        "cell": _cell(prim), "horizons": horiz,
        "watch_cohort": _cell(watch),
        "placebo_sym": _cell(psym), "placebo_shift": _cell(pshf),
        "cliffs_vs_sym": round(float(d_sym), 4), "cliffs_vs_shift": round(float(d_shf), 4),
        "cliffs_trigger_vs_watch": round(float(d_watch), 4),
        "half1_med22%": round(float(np.median(h1)) * 100, 3) if len(h1) else None,
        "half2_med22%": round(float(np.median(h2)) * 100, 3) if len(h2) else None,
        "gates": {"G1_n300": bool(g1), "G2_mean_med_pos": bool(g2),
                  "G3_cliffs_.05_both": bool(g3), "G4_both_halves": bool(g4)},
        "VERDICT": verdict}

    out["variants"] = {
        "D5_trigger": _cell(sel("D5", "event")),
        "D2_trigger": _cell(sel("D2", "event")),
        "D5_watch": _cell(sel("D5", "watch")),
        "D2_watch": _cell(sel("D2", "watch")),
        "STRONG": _cell([r for r in prim if r["strong"]]),
        "not_STRONG": _cell([r for r in prim if not r["strong"]]),
        "prox<=10%": _cell([r for r in prim if r["prox"] is not None and r["prox"] <= 0.10]),
        "prox<=5%": _cell([r for r in prim if r["prox"] is not None and r["prox"] <= 0.05]),
        "TREND": _cell([r for r in prim if r["trend"]]),
        "ANTITREND": _cell([r for r in prim if not r["trend"]]),
        "LIQ_5cr": _cell([r for r in prim if r["med_turn"] >= LIQ5]),
    }

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
    buckets.update(terciles(prim, "age", "floor_age"))
    buckets["band_1-5cr"] = _cell([r for r in prim if LIQ_FLOOR <= r["med_turn"] < LIQ5])
    buckets["band_5-25cr"] = _cell([r for r in prim if LIQ5 <= r["med_turn"] < 25e7])
    buckets["band_>25cr"] = _cell([r for r in prim if r["med_turn"] >= 25e7])
    out["buckets"] = buckets

    nets = np.array([t["net"] for t in tr], dtype=float)
    if len(nets):
        out["FORM2_trades"] = {
            "n": int(len(nets)), "hit%": round(float(np.mean(nets > 0)) * 100, 1),
            "mean_net%": round(float(np.mean(nets)) * 100, 2),
            "med_net%": round(float(np.median(nets)) * 100, 2),
            "avg_hold": round(float(np.mean([t["hold"] for t in tr])), 1),
            "censored": int(sum(t["censored"] for t in tr)),
            "exit_mix": {k: int(sum(1 for t in tr if t["exit_kind"] == k))
                         for k in ("floor_stop", "trail_stop", "censored")}}
    books = {}
    for key in BOOK_KEYS:
        rows = [r for r in bk if r["key"] == key and r["month"] >= "2012-06"]
        mr = [r["mret"] for r in rows]
        st_full = _stats_monthly(mr)
        st_h1 = _stats_monthly([r["mret"] for r in rows if r["month"] < "2019"])
        st_h2 = _stats_monthly([r["mret"] for r in rows if r["month"] >= "2019"])
        if st_full:
            books[key] = {"full": st_full, "h1_2012_18": st_h1, "h2_2019_26": st_h2,
                          "avg_pos": round(float(np.mean([r["avg_pos"] for r in rows])), 1),
                          "FUNDABLE_vs_0.89": bool(st_h1 and st_h2 and st_h1["retvol"] > 0.89
                                                   and st_h2["retvol"] > 0.89)}
    out["FORM2_book"] = books

    from .common import OUT_DIR  # noqa: PLC0415
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fractal_floor.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== FRACTAL FLOOR VERDICT: {verdict} ===")
    return out


# --------------------------------------------------------------------------- #
# selftest (offline)                                                           #
# --------------------------------------------------------------------------- #
def selftest():
    rng = np.random.default_rng(7)
    x = np.cumsum(rng.normal(0, 1, 600)) + 200

    # fractal flags match brute force
    for N in (2, 10):
        fl = fractal_flags(x, N, "low")
        for f in range(N, len(x) - N):
            manual = all(x[f] < x[f - k] for k in range(1, N + 1)) and \
                     all(x[f] < x[f + k] for k in range(1, N + 1))
            assert fl[f] == manual, (N, f)

    # engineered V-bottom: decline -> trough -> pullback high -> breakout = ONE D10 trigger
    lows = np.concatenate([200 - 1.5 * np.arange(30),                       # decline to 156.5 trough
                           156.5 + np.array([2, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6.5, 7, 8, 9, 10,
                                             11, 12, 13, 14, 15], dtype=float)])
    highs = lows + 2.0
    closes = lows + 1.0
    trig, wtch = scan(closes, highs, lows, 10)
    assert len(trig) == 1, f"expected 1 trigger, got {trig}"
    i, fb, fv, t1, strong = trig[0]
    assert fb == 29 and abs(fv - 156.5) < 1e-9          # the trough is the floor
    assert i > fb + 10                                   # PIT: after confirmation only
    assert closes[i] > t1 and closes[i - 1] <= t1        # genuine cross of the up-fractal high
    assert len(wtch) >= 1 and wtch[0][0] >= fb + 10      # watch also respects the lag

    # causality: truncating the future never adds/changes past triggers
    t_full, _ = scan(closes, highs, lows, 10)
    t_cut, _ = scan(closes[:i + 1], highs[:i + 1], lows[:i + 1], 10)
    assert [z[0] for z in t_cut] == [z[0] for z in t_full if z[0] <= i]

    # floor invalidation: a close below the floor kills the setup (no trigger after)
    lows2 = lows.copy()
    closes2 = closes.copy()
    closes2[42:] = 150.0                                 # crash through the floor before breakout
    trig2, _ = scan(closes2, highs, lows2, 10)
    assert all(z[0] < 42 for z in trig2)

    print("FRACTAL_FLOOR selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
