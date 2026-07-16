"""STREAM BAND MANAGED — Ramana's Case-A trade management, both sides: PRE-REGISTERED (2026-07-14).

WHAT CHANGED VS THE 07-13 STUDY. Same entry event (the falsified-as-timing reclaim), but the naive
book is replaced by RAMANA'S DICTATED MANAGEMENT (S133 spec, docs/reversal-pair-PLAN.md §7):
  BULL leg (entry = EMA5(HLC3) closes above EMA13(lows) after >=3 bars below):
    X1 STREAM stop  — EMA5 closes back below the lower bank -> exit, setup DIES (terminal).
    X2 FRACTAL stop — PRICE closes below the leg's "immediate previous" confirmed 2-degree
       down-fractal low (nearest in time at leg entry; FIXED for the leg). Dips inside the
       channel that do not break it are ignored.
    X3 TWO-CANDLE   — price closes below min(low[t-1], low[t-2]).
    RE-ENTRY — after X2/X3 the call SURVIVES: re-enter at the first close back ABOVE the broken
       level while the stream condition still holds (EMA5 >= lower bank); max 3 re-entries per
       setup; the fractal stop is REFRESHED at each re-entry. X1 always terminal.
  BEAR mirror: entry = EMA5 closes below EMA13(highs) after >=3 bars at/above; stops/re-entry
  mirrored on 2-degree UP-fractals and two-candle HIGHS. The bear book is a MEASUREMENT ONLY
  (single-stock cash shorting is not practically holdable in India) — its use is exit discipline.

LEDGER PRIOR (cited): the naive reclaim book = return/vol 0.37 full (0.16/0.53 halves), hit 41%,
median trade -2.08% net (07-13). Fences (07-14b): the exit craft carried ~all P&L in this family
(random entries + trail ~= real book). This study asks whether RAMANA'S richer exit/re-entry
stack beats the naive book — a management test, NOT a revival of the falsified entry timing.

MECHANICS (identical harness): eligibility warmup>=260, med_turn>=Rs1cr, close>=20, gaps<=6d,
signals>=2012-06-01, entry-event de-overlap 22 bars/symbol/side (re-entries exempt — same setup);
entries/exits at the NEXT bar's close after the signal/stop bar; one setup per symbol at a time;
0.3%/side; legs skipped if no confirmed 2-degree fractal exists in the trailing 100 bars at leg
entry; daily equal-weight book across open legs, monthly compounding; seed-free (deterministic).

METRIC BASIS (D142): every ratio here — the naive baseline included — is mean/sd annualised with NO
risk-free rate subtracted: a return/vol ratio, not a Sharpe; it reads high against a textbook Sharpe.
The 0.89 index bar is on the SAME basis, so the verdicts are unaffected.

PRE-REGISTERED VERDICT BARS (published either way):
  IMPROVED   = BULL managed book full return/vol >= 0.52 (naive 0.37 + 0.15) AND >= the naive
               book's return/vol in BOTH halves (0.16 / 0.53).
  FUNDABLE   = > 0.89 in BOTH halves (the standing index bar; expected FAIL per ledger).
  Otherwise  = NOT-IMPROVED. Bear book: descriptive only, no bar (non-shortable), reported with
               the same statistics. Trade-level stats (hit, median net, expectancy, exit mix,
               re-entry counts) reported vs the naive baseline. Cost sensitivity 1.5x reported.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.streamband_managed --build   # legs + books -> research.db
  ... --run                                           # report -> out/streamband_managed.json
  ... --selftest                                      # offline invariant checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

from .common import LIQ_FLOOR, eq_symbols, load_series, main_conn, research_conn
from .fractal_floor import fractal_flags
from .streamband import EMA_FAST, EMA_SLOW, RUN_BARS, crosses, ema
from .streamband import _stats_monthly

START = "2012-06-01"
HALF_SPLIT = "2019-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
DEOVERLAP = 22
COST_SIDE = 0.003
MAX_REENTRY = 3
FRAC_LOOKBACK = 100
NAIVE = {"full": 0.37, "h1": 0.16, "h2": 0.53}
IMPROVE_MARGIN = 0.15


class Book:
    def __init__(self):
        self.days = {}

    def add(self, date, r):
        c = self.days.setdefault(date, [0.0, 0])
        c[0] += r
        c[1] += 1

    def stats(self):
        months = {}
        for d in sorted(self.days):
            s, c = self.days[d]
            months.setdefault(d[:7], []).append(s / c)
        mm = sorted(months)
        mr = [float(np.prod([1 + r for r in months[m]]) - 1) for m in mm]
        return {"full": _stats_monthly(mr),
                "h1": _stats_monthly([r for m, r in zip(mm, mr) if m < HALF_SPLIT]),
                "h2": _stats_monthly([r for m, r in zip(mm, mr) if m >= HALF_SPLIT])}


def mark_leg(book, S, e, x, sign, ce, cx):
    """Daily marks close e -> close x; sign=+1 long / -1 short (short = a
    daily-rebalanced measurement, disclosed); entry/exit costs on their days."""
    for k in range(e + 1, x + 1):
        a, b = S.adj_close[k - 1], S.adj_close[k]
        if not (a > 0 and b > 0):
            continue
        r = sign * float(b / a - 1.0)
        if k == e + 1:
            r -= ce
        if k == x:
            r -= cx
        book.add(S.date[k], r)


def last_fractal_level(fr_idx, vals, t, lookback=FRAC_LOOKBACK):
    """Level of the most recent CONFIRMED degree-2 fractal as of bar t
    (fractal at f is knowable at f+2). fr_idx = sorted flag indices."""
    import bisect
    j = bisect.bisect_right(fr_idx, t - 2) - 1
    if j < 0:
        return None
    f = fr_idx[j]
    if t - f > lookback:
        return None
    return float(vals[f])


def run_side(S, side, T, U, L, entries, base_elig, fr_lo2_idx, fr_hi2_idx):
    """The Case-A state machine for one symbol/side. Returns list of legs:
    (entry_bar, exit_bar, kind, reentry_no). All decisions on closes; fills next close."""
    n = S.n
    ac, lo, hi = S.adj_close, S.adj_low, S.adj_high
    long_ = side == "BULL"
    legs = []
    last_ev = -10**9
    entries = set(entries)
    state = None      # None | ("IN", entry_bar, frac_level, k) | ("OUT", armed_level, k)
    t = 0
    while t < n - 1:
        Tt, Ut, Lt = T[t], U[t], L[t]
        band_ok = not (Tt is None or np.isnan(Tt) or np.isnan(Ut) or np.isnan(Lt))
        stream_dead = band_ok and ((Tt < Lt) if long_ else (Tt > Ut))
        if state is None:
            if t in entries and base_elig[t] and t - last_ev >= DEOVERLAP:
                last_ev = t
                lvl = (last_fractal_level(fr_lo2_idx, lo, t) if long_
                       else last_fractal_level(fr_hi2_idx, hi, t))
                if lvl is not None:
                    state = ("IN", t + 1, lvl, 0)
        elif state[0] == "IN":
            _s, e, lvl, k = state
            if t > e:                                   # manage from the bar after entry
                exit_kind = None
                if stream_dead:
                    exit_kind = "stream"
                elif (ac[t] < lvl) if long_ else (ac[t] > lvl):
                    exit_kind = "fractal"
                elif t >= 2:
                    two = (min(lo[t - 1], lo[t - 2]) if long_
                           else max(hi[t - 1], hi[t - 2]))
                    if not np.isnan(two) and ((ac[t] < two) if long_ else (ac[t] > two)):
                        exit_kind = "2cand"
                        lvl = float(two)                 # the broken level arms re-entry
                if exit_kind:
                    x = min(t + 1, n - 1)
                    if x > e:
                        legs.append((e, x, exit_kind, k))
                    state = None if exit_kind == "stream" else ("OUT", lvl, k)
                    t = x                                # resume after the fill bar
                    continue
        else:                                           # OUT — re-entry armed
            _s, lvl, k = state
            if stream_dead:
                state = None
            elif k < MAX_REENTRY and ((ac[t] > lvl) if long_ else (ac[t] < lvl)):
                nl = (last_fractal_level(fr_lo2_idx, lo, t) if long_
                      else last_fractal_level(fr_hi2_idx, hi, t))
                state = ("IN", t + 1, nl if nl is not None else lvl, k + 1)
        t += 1
    if state is not None and state[0] == "IN" and n - 1 > state[1]:
        legs.append((state[1], n - 1, "censored", state[3]))
    return legs


_DDL = """
DROP TABLE IF EXISTS sbm_legs;
CREATE TABLE sbm_legs(side TEXT, symbol TEXT, entry_date TEXT, exit_date TEXT,
  hold INT, gross REAL, net REAL, exit_kind TEXT, reentry_no INT, med_turn REAL);
DROP TABLE IF EXISTS sbm_book;
CREATE TABLE sbm_book(key TEXT, month TEXT, mret REAL, avg_pos REAL);
"""


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript(_DDL)
    books = {"BULL": Book(), "BULL15": Book(), "BEAR": Book()}
    leg_rows = []
    n_sym = 0
    for sym in eq_symbols(mc):
        n_sym += 1
        S = load_series(mc, sym)
        if S is None or S.n < 300:
            continue
        d64 = np.array(S.date, dtype="datetime64[D]")
        gap_prev = np.full(S.n, 999)
        gap_prev[1:] = (d64[1:] - d64[:-1]) / np.timedelta64(1, "D")
        gap_next = np.full(S.n, 999)
        gap_next[:-1] = gap_prev[1:]
        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START))
        tp = (S.adj_high + S.adj_low + S.adj_close) / 3.0
        U = ema(S.adj_high, EMA_SLOW)
        L = ema(S.adj_low, EMA_SLOW)
        T = ema(tp, EMA_FAST)
        buys, sells = crosses(T, U, L, RUN_BARS)
        fr_lo2_idx = list(np.where(fractal_flags(S.adj_low, 2, "low"))[0])
        fr_hi2_idx = list(np.where(fractal_flags(S.adj_high, 2, "high"))[0])

        for side, ents in (("BULL", buys), ("BEAR", sells)):
            sign = 1 if side == "BULL" else -1
            legs = run_side(S, side, T, U, L, ents, base_elig, fr_lo2_idx, fr_hi2_idx)
            for (e, x, kind, k) in legs:
                if not (S.adj_close[e] > 0 and S.adj_close[x] > 0):
                    continue
                gross = sign * float(S.adj_close[x] / S.adj_close[e] - 1.0)
                net = gross - 2 * COST_SIDE
                leg_rows.append((side, sym, S.date[e], S.date[x], x - e, gross, net,
                                 kind, k, float(S.med_turn[min(e, S.n - 1)])))
                mark_leg(books[side], S, e, x, sign, COST_SIDE, COST_SIDE)
                if side == "BULL":
                    mark_leg(books["BULL15"], S, e, x, sign,
                             1.5 * COST_SIDE, 1.5 * COST_SIDE)
        if n_sym % 400 == 0:
            print(f"  …{n_sym} symbols, legs={len(leg_rows)}", flush=True)

    rc.executemany("INSERT INTO sbm_legs VALUES (?,?,?,?,?,?,?,?,?,?)", leg_rows)
    brows = []
    for key, b in books.items():
        months = {}
        for d in sorted(b.days):
            s, c = b.days[d]
            months.setdefault(d[:7], []).append((s / c, c))
        for m in sorted(months):
            rs = months[m]
            brows.append((key, m, float(np.prod([1 + r for r, _ in rs]) - 1),
                          float(np.mean([c for _, c in rs]))))
    rc.executemany("INSERT INTO sbm_book VALUES (?,?,?,?)", brows)
    rc.commit()
    rc.close()
    mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"BUILD done: {len(leg_rows)} legs in {dt:.0f}s")


def run():
    rc = research_conn()
    legs = rc.execute("SELECT * FROM sbm_legs").fetchall()
    bk = rc.execute("SELECT * FROM sbm_book ORDER BY key, month").fetchall()
    rc.close()
    out = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "naive_baseline_07_13": {"retvol_full": NAIVE["full"], "h1": NAIVE["h1"],
                                    "h2": NAIVE["h2"], "hit%": 41.0, "med_net%": -2.08,
                                    "avg_hold": 15.3}}

    def leg_stats(side):
        ls = [l for l in legs if l["side"] == side]
        nets = np.array([l["net"] for l in ls])
        if not len(nets):
            return {"n": 0}
        setups = sum(1 for l in ls if l["reentry_no"] == 0)
        return {"legs": int(len(nets)), "setups_first_legs": int(setups),
                "reentry_legs": int(len(nets) - setups),
                "hit%": round(float(np.mean(nets > 0)) * 100, 1),
                "mean_net%": round(float(np.mean(nets)) * 100, 2),
                "med_net%": round(float(np.median(nets)) * 100, 2),
                "avg_hold": round(float(np.mean([l["hold"] for l in ls])), 1),
                "exit_mix": {k: int(sum(1 for l in ls if l["exit_kind"] == k))
                             for k in ("stream", "fractal", "2cand", "censored")}}

    def book_stats(key):
        rows = [r for r in bk if r["key"] == key and r["month"] >= "2012-06"]
        mr = [r["mret"] for r in rows]
        st = {"full": _stats_monthly(mr),
              "h1": _stats_monthly([r["mret"] for r in rows if r["month"] < HALF_SPLIT]),
              "h2": _stats_monthly([r["mret"] for r in rows if r["month"] >= HALF_SPLIT]),
              "avg_pos": round(float(np.mean([r["avg_pos"] for r in rows])), 1) if rows else 0}
        return st

    bull = book_stats("BULL")
    out["BULL_managed"] = {"trades": leg_stats("BULL"), "book": bull,
                           "book_cost_1.5x": book_stats("BULL15")}
    out["BEAR_managed_measurement_only"] = {"trades": leg_stats("BEAR"),
                                            "book": book_stats("BEAR")}
    ok = (bull["full"] and bull["h1"] and bull["h2"]
          and bull["full"]["retvol"] >= NAIVE["full"] + IMPROVE_MARGIN
          and bull["h1"]["retvol"] >= NAIVE["h1"] and bull["h2"]["retvol"] >= NAIVE["h2"])
    fundable = (bull["h1"] and bull["h2"]
                and bull["h1"]["retvol"] > 0.89 and bull["h2"]["retvol"] > 0.89)
    out["VERDICT"] = ("IMPROVED" if ok else "NOT-IMPROVED") + \
                     (" + FUNDABLE" if fundable else " (not fundable vs 0.89)")
    from .common import OUT_DIR  # noqa: PLC0415
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "streamband_managed.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== STREAMBAND MANAGED VERDICT: {out['VERDICT']} ===")
    return out


# --------------------------------------------------------------------------- #
def selftest():
    class T:
        pass
    rng = np.random.default_rng(3)
    for trial in range(30):
        n = 420
        S = T()
        ret = rng.normal(0, 0.02, n)
        S.adj_close = 100 * np.cumprod(1 + ret)
        S.adj_high = S.adj_close * (1 + np.abs(rng.normal(0, 0.008, n)))
        S.adj_low = S.adj_close * (1 - np.abs(rng.normal(0, 0.008, n)))
        S.n = n
        S.date = [f"2018-{(i//28)%12+1:02d}-{i%28+1:02d}" for i in range(n)]
        tp = (S.adj_high + S.adj_low + S.adj_close) / 3.0
        U, L, Tr = ema(S.adj_high, 13), ema(S.adj_low, 13), ema(tp, 5)
        buys, sells = crosses(Tr, U, L, 3)
        lo2 = list(np.where(fractal_flags(S.adj_low, 2, "low"))[0])
        hi2 = list(np.where(fractal_flags(S.adj_high, 2, "high"))[0])
        elig = np.ones(n, dtype=bool)
        for side, ents in (("BULL", buys), ("BEAR", sells)):
            legs = run_side(S, side, Tr, U, L, ents, elig, lo2, hi2)
            prev_end = -1
            for (e, x, kind, k) in legs:
                assert x > e, (side, e, x)
                assert e > prev_end, "legs overlap"
                prev_end = x
                assert kind in ("stream", "fractal", "2cand", "censored")
                assert 0 <= k <= MAX_REENTRY
            # re-entry legs only ever follow a fractal/2cand exit of the SAME setup
            for i in range(1, len(legs)):
                if legs[i][3] > 0:
                    assert legs[i - 1][2] in ("fractal", "2cand")
                    assert legs[i][3] == legs[i - 1][3] + 1 or legs[i][3] == 1
    print("STREAMBAND_MANAGED selftest OK (30 random walks, invariants hold, both sides)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
