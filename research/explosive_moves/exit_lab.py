"""EXIT LAB — best stop/exit engine for the SAME reclaim entry: PRE-REGISTERED (2026-07-14).

THE QUESTION (Ramana): for the falsified-as-timing reclaim entry, which exit engine best
"maximizes profit when right, cuts fast when wrong"? Exits redistribute an entry's P&L —
they cannot create edge the entry lacks (fences 07-14b: random entries + trail ~= real book;
managed stack 07-14d: the 2-candle exit destroyed it, ordering trail 0.59 > band 0.37 >
2-candle -0.50). This study makes the exit ordering COMPLETE across ten coherent engines,
with anti-overfit protocol, and publishes the full table win or lose.

ENTRIES: identical to 07-13 (EMA5(HLC3) reclaims EMA13(lows) after >=3 bars below; warmup>=260,
med_turn>=Rs1cr, close>=20, gaps<=6d, >=2012-06-01, de-overlap 22 bars/symbol; entry next close;
ONE open trade per symbol; no re-entries). 0.3%/side flat (1.5x sensitivity per engine).

THE TEN ENGINES (locked; all decisions on CLOSES, fills next close; stops/trails ratchet up only;
'frac2' = the nearest confirmed 2-degree down-fractal low at entry, fallback entry-8% if absent):
  E1  band-only            exit when EMA5 < lower bank (the naive baseline, 0.37)
  E2  frac2 + trail2       initial frac2 stop; trail ratchets under confirmed 2-deg lows
  E3  frac2 + trail5       same but 5-degree lows (wider — let winners breathe)
  E4  pct8 + chand3        8% initial stop; chandelier trail = highest close - 3x ATR20
  E5  pct8 + chand2        chandelier at 2x ATR20 (tighter)
  E6  frac2 + trail2@+5%   trail2 ARMS only after +5% gross profit; frac2 stop before that
  E7  frac2 + 5cand        close below the min low of the previous FIVE candles (loosened 07-14d)
  E8  frac2 + p90take+66d  profit-take when own-history stretch percentile >= p90; 66-bar time stop
  E9  frac2 + upper+66d    profit-take when EMA5 reaches the UPPER bank; 66-bar time stop
  E10 pct8 + trail5        percent stop + wide fractal trail
Exit precedence within a bar: stop/trail first, then structural exit (band/5cand), then
profit-take, then time. Censored at series end.

ANTI-OVERFIT PROTOCOL: all ten run everywhere; the WINNER is chosen ONLY on the 2012-18 half
(highest h1 book return/vol among engines with h1 avg hold >= 8 bars — the churn guard that would
have rejected the 2-candle rule a priori); the headline result is that winner's UNTOUCHED
2019-26 return/vol. Ten-engine selection is disclosed; the full table is published either way.

METRIC BASIS (D142): every ratio here is mean/sd annualised with NO risk-free rate subtracted — a
return/vol ratio, not a Sharpe; it reads high against a textbook Sharpe. The 0.79 and 0.89 bars are
on the SAME basis, so the verdict is unaffected.

PRE-REGISTERED BARS:
  G-BETTER  = winner's 2019-26 return/vol >= 0.79 (known-best exit's h2, fences trail 0.69, +0.10)
  G-FUNDABLE= winner > 0.89 in BOTH halves (standing index bar; expected FAIL — the entry has no
              edge to protect; exits can only shape the loss). Published to the ledger either way.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.exit_lab --build    # legs + books -> research.db
  ... --run                                  # table + verdict -> out/exit_lab.json
  ... --selftest                             # offline checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .common import LIQ_FLOOR, eq_symbols, load_series, main_conn, research_conn
from .fractal_floor import fractal_flags
from .streamband import (EMA_FAST, EMA_SLOW, RUN_BARS, _stats_monthly, crosses,
                         ema, roll_mean, stretch_signed)
from .streamband_managed import Book, last_fractal_level, mark_leg

START = "2012-06-01"
HALF = "2019-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
DEOVERLAP = 22
COST = 0.003
PCT_STOP = 0.08
ARM_PROFIT = 0.05
TMAX = 66
HOLD_GUARD = 8

ENGINES = {
    "E1_band":        dict(stop=None,   trail=None,  band=True,  fivec=False, take=None,   tmax=None),
    "E2_frac_trail2": dict(stop="frac", trail="t2",  band=False, fivec=False, take=None,   tmax=None),
    "E3_frac_trail5": dict(stop="frac", trail="t5",  band=False, fivec=False, take=None,   tmax=None),
    "E4_pct8_chand3": dict(stop="pct",  trail="ch3", band=False, fivec=False, take=None,   tmax=None),
    "E5_pct8_chand2": dict(stop="pct",  trail="ch2", band=False, fivec=False, take=None,   tmax=None),
    "E6_trail2_arm5": dict(stop="frac", trail="t2",  band=False, fivec=False, take=None,   tmax=None, arm=ARM_PROFIT),
    "E7_frac_5cand":  dict(stop="frac", trail=None,  band=False, fivec=True,  take=None,   tmax=None),
    "E8_p90_take":    dict(stop="frac", trail=None,  band=False, fivec=False, take="p90",  tmax=TMAX),
    "E9_upper_take":  dict(stop="frac", trail=None,  band=False, fivec=False, take="upper", tmax=TMAX),
    "E10_pct8_trail5": dict(stop="pct", trail="t5",  band=False, fivec=False, take=None,   tmax=None),
}


def rolling_p90(s, w=756, minv=250):
    n = len(s)
    out = np.full(n, np.nan)
    if n <= w:
        return out
    sw = sliding_window_view(s, w)
    valid = np.sum(~np.isnan(sw), axis=1)
    with np.errstate(invalid="ignore"):
        p = np.nanpercentile(sw, 90, axis=1)
    p[valid < minv] = np.nan
    out[w:] = p[: n - w]
    return out


def walk(spec, S, i, T, U, L, st, p90, atr, lo2, lo5):
    """One trade under one engine. Entry close i+1; returns (exit_bar, kind)."""
    n = S.n
    ac, al = S.adj_close, S.adj_low
    e = i + 1
    p0 = ac[e]
    stop = None
    if spec["stop"] == "frac":
        stop = last_fractal_level(lo2, al, i)
        if stop is None or stop >= p0:
            stop = p0 * (1 - PCT_STOP)
    elif spec["stop"] == "pct":
        stop = p0 * (1 - PCT_STOP)
    tr_kind = spec["trail"]
    fr_idx = lo2 if tr_kind == "t2" else lo5 if tr_kind == "t5" else None
    fr_deg = 2 if tr_kind == "t2" else 5
    kmul = 3.0 if tr_kind == "ch3" else 2.0 if tr_kind == "ch2" else None
    ptr = 0
    trail = -np.inf
    armed = spec.get("arm") is None
    hi_close = p0
    for j in range(e + 1, n):
        cj = ac[j]
        if np.isnan(cj):
            continue
        hi_close = max(hi_close, cj)
        if not armed and hi_close / p0 - 1.0 >= spec["arm"]:
            armed = True
        if fr_idx is not None:
            while ptr < len(fr_idx) and fr_idx[ptr] + fr_deg <= j:
                f = fr_idx[ptr]
                if f > i and not np.isnan(al[f]):
                    trail = max(trail, float(al[f]))
                ptr += 1
        elif kmul is not None and not np.isnan(atr[j]):
            trail = max(trail, hi_close - kmul * atr[j])
        eff = stop if stop is not None else -np.inf
        if armed and trail > eff:
            eff = trail
        if cj < eff:
            return min(j + 1, n - 1), "stop"
        if spec["band"] and not (np.isnan(T[j]) or np.isnan(L[j])) and T[j] < L[j]:
            return min(j + 1, n - 1), "band"
        if spec["fivec"] and j >= e + 5:
            five = np.nanmin(al[j - 5:j])
            if not np.isnan(five) and cj < five:
                return min(j + 1, n - 1), "5cand"
        if spec["take"] == "p90" and not (np.isnan(st[j]) or np.isnan(p90[j])) and st[j] >= p90[j]:
            return min(j + 1, n - 1), "take"
        if spec["take"] == "upper" and not (np.isnan(T[j]) or np.isnan(U[j])) and T[j] >= U[j]:
            return min(j + 1, n - 1), "take"
        if spec["tmax"] and j - e >= spec["tmax"]:
            return min(j + 1, n - 1), "time"
    return n - 1, "censored"


_DDL = """
DROP TABLE IF EXISTS exitlab_legs;
CREATE TABLE exitlab_legs(engine TEXT, symbol TEXT, entry_date TEXT, exit_date TEXT,
  hold INT, gross REAL, net REAL, kind TEXT);
DROP TABLE IF EXISTS exitlab_book;
CREATE TABLE exitlab_book(engine TEXT, cost TEXT, month TEXT, mret REAL, avg_pos REAL);
"""


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript(_DDL)
    books = {(nm, c): Book() for nm in ENGINES for c in ("1.0", "1.5")}
    rows = []
    n_sym = 0
    for sym in eq_symbols(mc):
        n_sym += 1
        S = load_series(mc, sym)
        if S is None or S.n < 300:
            continue
        d64 = np.array(S.date, dtype="datetime64[D]")
        gp = np.full(S.n, 999)
        gp[1:] = (d64[1:] - d64[:-1]) / np.timedelta64(1, "D")
        gn = np.full(S.n, 999)
        gn[:-1] = gp[1:]
        ii = np.arange(S.n)
        elig = ((ii >= WARMUP) & (gp <= MAX_GAP) & (gn <= MAX_GAP)
                & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                & (np.array(S.date) >= START))
        tp = (S.adj_high + S.adj_low + S.adj_close) / 3.0
        U, L, T = ema(S.adj_high, EMA_SLOW), ema(S.adj_low, EMA_SLOW), ema(tp, EMA_FAST)
        st = stretch_signed(T, U, L)
        p90 = rolling_p90(np.array(st, dtype=float))
        with np.errstate(invalid="ignore"):
            pc = np.roll(S.adj_close, 1)
            pc[0] = np.nan
            tr = np.nanmax(np.vstack([S.adj_high - S.adj_low,
                                      np.abs(S.adj_high - pc),
                                      np.abs(S.adj_low - pc)]), axis=0)
        atr = roll_mean(tr, 20)
        buys, _ = crosses(T, U, L, RUN_BARS)
        lo2 = list(np.where(fractal_flags(S.adj_low, 2, "low"))[0])
        lo5 = list(np.where(fractal_flags(S.adj_low, 5, "low"))[0])
        open_until = {nm: -1 for nm in ENGINES}
        last = -10**9
        for i in buys:
            if not elig[i] or i + 1 >= S.n or i - last < DEOVERLAP:
                continue
            last = i
            for nm, spec in ENGINES.items():
                if i + 1 <= open_until[nm]:
                    continue
                x, kind = walk(spec, S, i, T, U, L, st, p90, atr, lo2, lo5)
                e = i + 1
                if x <= e or not (S.adj_close[e] > 0 and S.adj_close[x] > 0):
                    continue
                open_until[nm] = x
                gross = float(S.adj_close[x] / S.adj_close[e] - 1.0)
                rows.append((nm, sym, S.date[e], S.date[x], x - e, gross,
                             gross - 2 * COST, kind))
                mark_leg(books[(nm, "1.0")], S, e, x, 1, COST, COST)
                mark_leg(books[(nm, "1.5")], S, e, x, 1, 1.5 * COST, 1.5 * COST)
        if n_sym % 400 == 0:
            print(f"  …{n_sym} symbols, legs={len(rows)}", flush=True)
    rc.executemany("INSERT INTO exitlab_legs VALUES (?,?,?,?,?,?,?,?)", rows)
    brows = []
    for (nm, c), b in books.items():
        months = {}
        for d in sorted(b.days):
            s, cnt = b.days[d]
            months.setdefault(d[:7], []).append((s / cnt, cnt))
        for m in sorted(months):
            rs = months[m]
            brows.append((nm, c, m, float(np.prod([1 + r for r, _ in rs]) - 1),
                          float(np.mean([x for _, x in rs]))))
    rc.executemany("INSERT INTO exitlab_book VALUES (?,?,?,?,?)", brows)
    rc.commit()
    rc.close()
    mc.close()
    print(f"BUILD done: {len(rows)} legs across {len(ENGINES)} engines "
          f"in {(datetime.now(timezone.utc)-t0).total_seconds():.0f}s")


def run():
    rc = research_conn()
    legs = rc.execute("SELECT * FROM exitlab_legs").fetchall()
    bk = rc.execute("SELECT * FROM exitlab_book ORDER BY engine, month").fetchall()
    rc.close()
    out = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "known": {"naive_band": 0.37, "fences_trail_full": 0.59,
                     "fences_trail_h2": 0.69, "index_bar": 0.89}}
    table = {}
    for nm in ENGINES:
        rowsb = [r for r in bk if r["engine"] == nm and r["cost"] == "1.0"
                 and r["month"] >= "2012-06"]
        mr = [r["mret"] for r in rowsb]
        full = _stats_monthly(mr)
        h1 = _stats_monthly([r["mret"] for r in rowsb if r["month"] < HALF])
        h2 = _stats_monthly([r["mret"] for r in rowsb if r["month"] >= HALF])
        r15 = [r["mret"] for r in bk if r["engine"] == nm and r["cost"] == "1.5"
               and r["month"] >= "2012-06"]
        ls = [l for l in legs if l["engine"] == nm]
        nets = np.array([l["net"] for l in ls])
        wins = nets[nets > 0]
        loss = nets[nets <= 0]
        h1_legs = [l for l in ls if l["entry_date"] < "2019-01-01"]
        table[nm] = {
            "book": {"full": full, "h1": h1, "h2": h2},
            "book15_full": _stats_monthly(r15),
            "legs": int(len(ls)), "hit%": round(float(np.mean(nets > 0)) * 100, 1),
            "med_net%": round(float(np.median(nets)) * 100, 2),
            "avg_win%": round(float(np.mean(wins)) * 100, 2) if len(wins) else None,
            "avg_loss%": round(float(np.mean(loss)) * 100, 2) if len(loss) else None,
            "payoff": round(float(np.mean(wins) / -np.mean(loss)), 2)
            if len(wins) and len(loss) and np.mean(loss) < 0 else None,
            "big_wins_gt20%": round(float(np.mean(nets > 0.20)) * 100, 1),
            "avg_hold": round(float(np.mean([l["hold"] for l in ls])), 1),
            "h1_avg_hold": round(float(np.mean([l["hold"] for l in h1_legs])), 1)
            if h1_legs else None,
            "exit_mix": {k: int(sum(1 for l in ls if l["kind"] == k))
                         for k in ("stop", "band", "5cand", "take", "time", "censored")}}
    out["engines"] = table

    # fit-half winner (churn guard), OOS headline
    cands = [(nm, t) for nm, t in table.items()
             if t["book"]["h1"] and t["h1_avg_hold"] and t["h1_avg_hold"] >= HOLD_GUARD]
    if cands:
        wnm, wt = max(cands, key=lambda x: x[1]["book"]["h1"]["retvol"])
        h2s = wt["book"]["h2"]["retvol"] if wt["book"]["h2"] else None
        # D142 re-cut (S190, 16AY): book ratios are excess-basis via factory.eqstats, so the
        # bars follow. BAR_FULL_EX measured in-run by factor_zoo (RAW 0.899 -> 0.528; flat
        # 6.5%/yr rf); the 0.79 companion is shifted by the SAME measured penalty (0.371) —
        # an approximation (its own sigma basis was never separately recorded), descriptive lab.
        BAR_FULL_EX, BAR_079_EX = 0.528, 0.79 - 0.371
        g_better = bool(h2s is not None and h2s >= BAR_079_EX)
        g_fund = bool(wt["book"]["h1"] and wt["book"]["h2"]
                      and wt["book"]["h1"]["retvol"] > BAR_FULL_EX and wt["book"]["h2"]["retvol"] > BAR_FULL_EX)
        out["WINNER"] = {"engine": wnm, "chosen_on": "h1 return/vol (hold>=8 guard)",
                         "h1_retvol": wt["book"]["h1"]["retvol"], "oos_h2_retvol": h2s,
                         "G_BETTER_vs_0.419ex": g_better, "G_FUNDABLE_0.528ex": g_fund}
        out["VERDICT"] = ("BETTER-EXIT-FOUND" if g_better else "NO-BETTER-EXIT") + \
                         (" + FUNDABLE" if g_fund else " (not fundable)")
    else:
        out["VERDICT"] = "VOID (no engine passed the hold guard)"
    from .common import OUT_DIR  # noqa: PLC0415
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "exit_lab.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== EXIT LAB VERDICT: {out['VERDICT']} ===")
    return out


def selftest():
    class X:
        pass
    S = X()
    up = np.concatenate([np.full(5, 100.0), np.linspace(100, 160, 40), np.linspace(160, 150, 8)])
    S.adj_close = up
    S.adj_high = up * 1.01
    S.adj_low = up * 0.99
    S.n = len(up)
    S.date = [f"2020-{(i//28)%12+1:02d}-{i%28+1:02d}" for i in range(S.n)]
    T = [None] * S.n
    U = np.full(S.n, np.inf)
    L = np.full(S.n, -np.inf)
    st = np.full(S.n, np.nan)
    p90 = np.full(S.n, np.nan)
    atr = np.full(S.n, 2.0)
    Tn = np.full(S.n, np.nan)
    lo2 = list(np.where(fractal_flags(S.adj_low, 2, "low"))[0])
    x, kind = walk(ENGINES["E5_pct8_chand2"], S, 4, Tn, U, L, st, p90, atr, lo2, [])
    assert kind == "stop" and x > 40, (x, kind)   # chandelier holds the rise, exits the fade
    p8 = ENGINES["E4_pct8_chand3"]
    crash = X()
    dn = np.concatenate([np.full(5, 100.0), np.linspace(100, 80, 20)])
    crash.adj_close = dn
    crash.adj_high = dn * 1.01
    crash.adj_low = dn * 0.99
    crash.n = len(dn)
    crash.date = [f"2020-01-{i%28+1:02d}" for i in range(crash.n)]
    x2, k2 = walk(p8, crash, 4, np.full(crash.n, np.nan), np.full(crash.n, np.inf),
                  np.full(crash.n, -np.inf), np.full(crash.n, np.nan),
                  np.full(crash.n, np.nan), np.full(crash.n, 2.0), [], [])
    assert k2 == "stop" and x2 <= 15                # 8% stop cuts the crash quickly
    rng = np.random.default_rng(5)
    for _ in range(10):                             # invariants on random walks, all engines
        n = 300
        c = 100 * np.cumprod(1 + rng.normal(0, 0.02, n))
        W = X()
        W.adj_close = c
        W.adj_high = c * 1.01
        W.adj_low = c * 0.99
        W.n = n
        W.date = [f"2019-{(i//28)%12+1:02d}-{i%28+1:02d}" for i in range(n)]
        tp = (W.adj_high + W.adj_low + W.adj_close) / 3
        Uw, Lw, Tw = ema(W.adj_high, 13), ema(W.adj_low, 13), ema(tp, 5)
        stw = np.array(stretch_signed(Tw, Uw, Lw), dtype=float)
        l2 = list(np.where(fractal_flags(W.adj_low, 2, "low"))[0])
        l5 = list(np.where(fractal_flags(W.adj_low, 5, "low"))[0])
        for nm, spec in ENGINES.items():
            x3, k3 = walk(spec, W, 30, Tw, Uw, Lw, stw, np.full(n, np.nan),
                          np.full(n, 2.0), l2, l5)
            assert 31 < x3 <= n - 1 and k3 in ("stop", "band", "5cand", "take",
                                               "time", "censored"), (nm, x3, k3)
    print("EXIT_LAB selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
