"""RECLAIM SELECTION — do validated selection factors separate the launchers? PRE-REGISTERED (2026-07-14).

THE QUESTION (the one thread the reversal-pair arc left open). The event set = STREAM BAND
BUY-reclaims WITH the confirmed fractal floor intact (the live Screen+ "reclaim . floor intact"
pill, applied historically). The event itself is a falsified ANTI-signal (ledger 2026-07-13:
22d excess med -1.25 pct, both placebos better) BUT with heavy right skew (66d mean ~0 vs med
-2.7): a minority launch. Ledger doctrine says timing fails and SELECTION sometimes survives
(Wolfe BULL winner-profile +4.4 pct medNet, alpha +5.07, true-OOS). This study asks ONLY the
selection question: can factors already validated as gross selection engines (momentum /
risk-adjusted momentum / low-vol / delivery) identify a reclaim subset with POSITIVE forward
excess? No book, no timing, no fundable claim regardless of outcome — a selection-lens test.

EVENTS. Universe/eligibility/PIT identical to the streamband study (EQ symbols; signal dates
>= 2012-06-01; warmup >=260 rows; med_turn >= Rs 1cr; close >= 20; gaps <= 6d; de-overlap 22
bars/symbol; HLC3 trigger reclaim after >=3 bars below the lower bank; entry close i+1; excess
vs Nifty-500 over identical spans). PLUS the floor-intact condition AT the signal bar: the
latest CONFIRMED degree-10 (fallback degree-5) down-fractal within 400 bars has NO close below
it up to bar i (the live-surface definition, PIT: a degree-N fractal counts only N bars later).

FEATURES at the signal bar (8, price/volume-only, all PIT): mom6, mom12, riskadj (mom6/vol66),
vol66, deliv_rel (deliv_per / own trailing-252 median), surge (day value / med_turn),
dist52 (close vs trailing-252 max), smin5 (min signed stretch over the last 5 bars).

FIT -> FREEZE -> TEST (the Wolfe true-OOS protocol; multiple-testing honesty by construction):
  FIT on signal dates < 2019-01-01 ONLY: per feature, tercile split at the fit-set 33.3/66.7
  quantiles; direction = the tercile side with the higher median 22d excess; feature is
  ELIGIBLE only if the top-vs-bottom median gap keeps the SAME SIGN in both fit sub-periods
  (< / >= 2016-01-01). RULE = conjunction of the TWO eligible features with the largest
  absolute gap, each at its favorable tercile, cutoffs FROZEN at the fit-quantile values.
  TEST on >= 2019-01-01 with the frozen numeric rule. The fit table is published either way.

PRE-REGISTERED OOS GATE (PASS-selection requires ALL FOUR, else FAIL-null to the ledger):
  G1  n_selected(OOS) >= 150
  G2  OOS selected mean AND median 22d excess > 0
  G3  Cliff's delta(selected, unselected OOS events) >= +0.10
  G4  Cliff's delta(selected, the selected events' own symbol-placebos x2) >= +0.05
66d excess is reported as secondary context and cannot create a pass. Liquidity-band cuts
reported. Even a PASS ships as a DESCRIPTIVE selection lens (Wolfe-class), never a book —
the fences lesson (07-14b) stands. Seed 42; sorted-symbol order; DESCRIPTIVE-ONLY output.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.reclaim_selection --build   # events+features -> research.db
  ... --run                                          # fit/freeze/test -> out/reclaim_selection.json
  ... --selftest                                     # offline checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .common import LIQ_FLOOR, cliffs_delta, eq_symbols, load_series, main_conn, research_conn
from .fractal_floor import fractal_flags
from .streamband import (EMA_FAST, EMA_SLOW, RUN_BARS, _Idx, _fwd, crosses,
                         ema, roll_std, stretch_signed)

START = "2012-06-01"
FIT_SPLIT = "2019-01-01"
FIT_MID = "2016-01-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
DEOVERLAP = 22
FLOOR_LOOKBACK = 400
SEED = 42
FEATURES = ("mom6", "mom12", "riskadj", "vol66", "deliv_rel", "surge", "dist52", "smin5")
MIN_N_SEL = 150
G3_D, G4_D = 0.10, 0.05


def _roll_agg(x, w, fn):
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    sw = sliding_window_view(x, w)
    with np.errstate(invalid="ignore"):
        out[w - 1:] = fn(sw, axis=1)
    return out


def floor_intact(flags10, flags5, ac, al, i, lookback=FLOOR_LOOKBACK):
    """True if the latest CONFIRMED D10 (fallback D5) floor within `lookback`
    bars of i is unbroken (no close below it) as of bar i. PIT: fractal at f
    counts only when f + deg <= i."""
    for deg, fl in ((10, flags10), (5, flags5)):
        cand = None
        lo = max(0, i - lookback)
        for f in range(i - deg, lo - 1, -1):
            if fl[f]:
                cand = f
                break
        if cand is None:
            continue
        v = al[cand]
        seg = ac[cand + 1:i + 1]
        seg = seg[~np.isnan(seg)]
        return bool(len(seg) == 0 or seg.min() >= v)
    return False


# --------------------------------------------------------------------------- #
_DDL = """
DROP TABLE IF EXISTS reclaim_sel_events;
CREATE TABLE reclaim_sel_events(
  kind TEXT, symbol TEXT, sig_date TEXT, entry_date TEXT, med_turn REAL,
  mom6 REAL, mom12 REAL, riskadj REAL, vol66 REAL, deliv_rel REAL,
  surge REAL, dist52 REAL, smin5 REAL,
  fx22 REAL, fx66 REAL, fr22 REAL, fr66 REAL);
"""


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript(_DDL)
    idx = _Idx()
    rng = np.random.default_rng(SEED)
    rows_out = []
    n_sym = n_used = n_ev = 0

    for sym in eq_symbols(mc):
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
        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START))
        can22 = np.zeros(S.n, dtype=bool)
        if S.n - 24 > 0:
            can22[:S.n - 24] = True
        plc_pool = np.where(base_elig & can22)[0]

        tp = (S.adj_high + S.adj_low + S.adj_close) / 3.0
        U = ema(S.adj_high, EMA_SLOW)
        L = ema(S.adj_low, EMA_SLOW)
        T = ema(tp, EMA_FAST)
        st = stretch_signed(T, U, L)
        buys, _sells = crosses(T, U, L, RUN_BARS)
        flags10 = fractal_flags(S.adj_low, 10, "low")
        flags5 = fractal_flags(S.adj_low, 5, "low")
        vol66 = roll_std(S.ret_raw, 66)
        dmed252 = _roll_agg(S.deliv_per, 252, np.nanmedian)
        max252 = _roll_agg(S.adj_close, 252, np.nanmax)

        def feats(i):
            ac = S.adj_close
            mom6 = ac[i] / ac[i - 126] - 1 if i >= 126 and ac[i - 126] > 0 else np.nan
            mom12 = ac[i] / ac[i - 252] - 1 if i >= 252 and ac[i - 252] > 0 else np.nan
            v = vol66[i]
            ra = mom6 / (v + 1e-6) if not (np.isnan(mom6) or np.isnan(v)) else np.nan
            dr = (S.deliv_per[i] / dmed252[i]
                  if dmed252[i] and not np.isnan(dmed252[i]) and dmed252[i] > 0
                  and not np.isnan(S.deliv_per[i]) else np.nan)
            sg = (S.value[i] / S.med_turn[i]
                  if S.med_turn[i] and S.med_turn[i] > 0 else np.nan)
            d52 = ac[i] / max252[i] - 1 if max252[i] and max252[i] > 0 else np.nan
            sm5 = float(np.nanmin(st[max(0, i - 4):i + 1]))
            return [mom6, mom12, ra, v if not np.isnan(v) else np.nan, dr, sg, d52, sm5]

        last = -10**9
        for i in buys:
            if not base_elig[i] or i + 1 >= S.n or i - last < DEOVERLAP:
                continue
            last = i
            if not floor_intact(flags10, flags5, S.adj_close, S.adj_low, i):
                continue
            n_ev += 1
            raw, exc = _fwd(S, i, idx)
            f = feats(i)
            rows_out.append(("event", sym, S.date[i], S.date[i + 1],
                             float(S.med_turn[i]), *[None if np.isnan(x) else float(x) for x in f],
                             exc[22], exc[66], raw[22], raw[66]))
            if len(plc_pool) >= 3:
                for p in rng.choice(plc_pool, size=2, replace=False):
                    p = int(p)
                    rw, ex = _fwd(S, p, idx)
                    rows_out.append(("plc", sym, S.date[p], S.date[p + 1],
                                     float(S.med_turn[p]), *([None] * 8),
                                     ex[22], ex[66], rw[22], rw[66]))
        if n_sym % 400 == 0:
            print(f"  …{n_sym} symbols, events={n_ev}", flush=True)

    rc.executemany("INSERT INTO reclaim_sel_events VALUES (" + ",".join("?" * 17) + ")",
                   rows_out)
    rc.commit()
    rc.close()
    mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"BUILD done: {n_used}/{n_sym} symbols, {n_ev} floor-intact reclaims "
          f"({len(rows_out)} rows incl placebos) in {dt:.0f}s")


# --------------------------------------------------------------------------- #
def _med(a):
    a = a[~np.isnan(a)]
    return float(np.median(a)) if len(a) else np.nan


def fit_rule(fit_rows):
    """The pre-registered derivation. Returns (chosen, table) where chosen =
    [(feature, lo_cut, hi_cut, favorable_side)] for the top-2 eligible features."""
    x22 = np.array([r["fx22"] if r["fx22"] is not None else np.nan for r in fit_rows])
    mid = np.array([r["sig_date"] < FIT_MID for r in fit_rows])
    table, eligible = {}, []
    for f in FEATURES:
        v = np.array([r[f] if r[f] is not None else np.nan for r in fit_rows])
        ok = ~np.isnan(v) & ~np.isnan(x22)
        if ok.sum() < 300:
            table[f] = {"n": int(ok.sum()), "eligible": False, "note": "n<300"}
            continue
        q1, q2 = np.nanpercentile(v[ok], [33.3, 66.7])
        top, bot = ok & (v > q2), ok & (v <= q1)
        gap = _med(x22[top]) - _med(x22[bot])
        # sub-period consistency (same sign of the top-bottom gap in both)
        g_a = _med(x22[top & mid]) - _med(x22[bot & mid])
        g_b = _med(x22[top & ~mid]) - _med(x22[bot & ~mid])
        consistent = bool(not np.isnan(g_a) and not np.isnan(g_b)
                          and np.sign(g_a) == np.sign(g_b) and np.sign(gap) != 0)
        side = "top" if gap > 0 else "bottom"
        table[f] = {"n": int(ok.sum()), "q33": round(float(q1), 4), "q67": round(float(q2), 4),
                    "med22_top%": round(_med(x22[top]) * 100, 3),
                    "med22_bot%": round(_med(x22[bot]) * 100, 3),
                    "gap%": round(gap * 100, 3), "sub_gaps%": [round(g_a * 100, 3),
                                                               round(g_b * 100, 3)],
                    "eligible": consistent, "favorable": side}
        if consistent:
            eligible.append((abs(gap), f, float(q1), float(q2), side))
    eligible.sort(reverse=True)
    chosen = [(f, q1, q2, side) for _g, f, q1, q2, side in eligible[:2]]
    return chosen, table


def _selected_mask(rows, chosen):
    m = np.ones(len(rows), dtype=bool)
    for f, q1, q2, side in chosen:
        v = np.array([r[f] if r[f] is not None else np.nan for r in rows])
        m &= (v > q2) if side == "top" else (v <= q1)   # NaN fails both -> unselected
    return m


def run():
    rc = research_conn()
    ev = [dict(r) for r in rc.execute(
        "SELECT * FROM reclaim_sel_events WHERE kind='event'")]
    plc = {}
    for r in rc.execute("SELECT * FROM reclaim_sel_events WHERE kind='plc'"):
        plc.setdefault((r["symbol"]), []).append(r["fx22"])
    rc.close()

    fit_rows = [r for r in ev if r["sig_date"] < FIT_SPLIT]
    oos_rows = [r for r in ev if r["sig_date"] >= FIT_SPLIT]
    chosen, table = fit_rule(fit_rows)

    out = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "n_events": len(ev), "n_fit": len(fit_rows), "n_oos": len(oos_rows),
           "fit_table": table,
           "frozen_rule": [{"feature": f, "cut_lo": round(q1, 4), "cut_hi": round(q2, 4),
                            "favorable": side} for f, q1, q2, side in chosen]}

    def stats(rows, mask=None):
        x = np.array([r["fx22"] if r["fx22"] is not None else np.nan for r in rows])
        if mask is not None:
            x = x[mask]
        x = x[~np.isnan(x)]
        if not len(x):
            return {"n": 0}
        return {"n": int(len(x)), "mean22%": round(float(np.mean(x)) * 100, 3),
                "med22%": round(float(np.median(x)) * 100, 3),
                "pos%": round(float(np.mean(x > 0)) * 100, 1)}

    verdict = "FAIL-null"
    if len(chosen) < 2:
        out["VERDICT"] = "FAIL-null (fewer than 2 consistent features in the fit half)"
    else:
        sel = _selected_mask(oos_rows, chosen)
        x = np.array([r["fx22"] if r["fx22"] is not None else np.nan for r in oos_rows])
        x66 = np.array([r["fx66"] if r["fx66"] is not None else np.nan for r in oos_rows])
        xs, xu = x[sel], x[~sel]
        xs = xs[~np.isnan(xs)]
        xu = xu[~np.isnan(xu)]
        pl = []
        for r, s in zip(oos_rows, sel):
            if s:
                pl += [v for v in plc.get(r["symbol"], []) if v is not None]
        pl = np.array(pl, dtype=float)
        d_uns = cliffs_delta(xs, xu)
        d_plc = cliffs_delta(xs, pl)
        g1 = len(xs) >= MIN_N_SEL
        g2 = len(xs) > 0 and float(np.mean(xs)) > 0 and float(np.median(xs)) > 0
        g3 = not np.isnan(d_uns) and d_uns >= G3_D
        g4 = not np.isnan(d_plc) and d_plc >= G4_D
        verdict = "PASS-selection" if (g1 and g2 and g3 and g4) else "FAIL-null"
        s66 = x66[sel]
        s66 = s66[~np.isnan(s66)]
        out["OOS"] = {
            "baseline_all": stats(oos_rows),
            "selected": stats(oos_rows, sel),
            "unselected": stats(oos_rows, ~sel),
            "selected_66d": {"n": int(len(s66)),
                             "mean%": round(float(np.mean(s66)) * 100, 3) if len(s66) else None,
                             "med%": round(float(np.median(s66)) * 100, 3) if len(s66) else None},
            "placebo_of_selected": {"n": int(len(pl)),
                                    "med22%": round(_med(pl) * 100, 3) if len(pl) else None},
            "cliffs_sel_vs_unsel": round(float(d_uns), 4),
            "cliffs_sel_vs_placebo": round(float(d_plc), 4),
            "gates": {"G1_n150": bool(g1), "G2_mean_med_pos": bool(g2),
                      f"G3_delta_unsel_{G3_D}": bool(g3), f"G4_delta_plc_{G4_D}": bool(g4)},
        }
        # liquidity bands of the selected set
        mt = np.array([r["med_turn"] for r in oos_rows])
        out["selected_liquidity"] = {
            "1-5cr": stats(oos_rows, sel & (mt < 5e7)),
            "5-25cr": stats(oos_rows, sel & (mt >= 5e7) & (mt < 25e7)),
            ">25cr": stats(oos_rows, sel & (mt >= 25e7))}
        out["VERDICT"] = verdict

    from .common import OUT_DIR  # noqa: PLC0415
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "reclaim_selection.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== RECLAIM SELECTION VERDICT: {out['VERDICT']} ===")
    return out


# --------------------------------------------------------------------------- #
def selftest():
    # fit_rule picks the two planted features, right side, frozen cuts
    rng = np.random.default_rng(0)
    rows = []
    for k in range(1200):
        date = "2013-06-01" if k % 2 else "2017-06-01"     # both fit sub-periods
        good = rng.random()
        noise = rng.normal()
        rows.append({"sig_date": date,
                     "mom6": good, "mom12": rng.random(), "riskadj": good + 0.1 * noise,
                     "vol66": rng.random(), "deliv_rel": rng.random(),
                     "surge": rng.random(), "dist52": -rng.random(),
                     "smin5": -rng.random() * 10,
                     "fx22": 0.05 * good - 0.02 + 0.01 * rng.normal()})
    chosen, table = fit_rule(rows)
    names = [c[0] for c in chosen]
    assert "mom6" in names or "riskadj" in names, names
    for f, q1, q2, side in chosen:
        if f in ("mom6", "riskadj"):
            assert side == "top"

    # selection mask honors frozen cuts; NaN never selects
    m = _selected_mask([{"mom6": 0.9, "riskadj": 0.9, "fx22": 0},
                        {"mom6": None, "riskadj": 0.9, "fx22": 0}],
                       [("mom6", 0.3, 0.6, "top"), ("riskadj", 0.3, 0.6, "top")])
    assert list(m) == [True, False]

    # floor_intact: PIT lag + break detection on a hand-built path
    n = 60
    al = np.array([50.0 - i if i < 30 else 20.0 + (i - 30) for i in range(n)])
    ac = al + 1.0
    f10 = fractal_flags(al, 10, "low")
    assert f10[30]                                          # trough at 30
    assert not floor_intact(f10, fractal_flags(al, 5, "low"), ac, al, 33)  # neither degree confirmed yet
    assert floor_intact(f10, fractal_flags(al, 5, "low"), ac, al, 45)      # confirmed + intact
    ac2 = ac.copy()
    ac2[50] = 10.0                                          # close below the floor
    assert not floor_intact(f10, fractal_flags(al, 5, "low"), ac2, al, 55)
    print("RECLAIM_SELECTION selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
