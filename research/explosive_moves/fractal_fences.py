"""FRACTAL FENCES — the three pre-registered confirmation checks on the PROX10 cell (2026-07-14).

WHAT IS BEING TESTED. Ledger § Study 2026-07-14 (FRACTAL FLOOR): the event gate was FAIL-null, but the
PROX≤10% structural-stop BOOK cleared the flat-cost bar in both halves (Sharpe 1.04; 0.92/1.15;
MaxDD −28.5%; ~69 avg positions) — the only reversal-family cell ever to do so, recorded FLAT-COST-ONLY
and 1-of-5-cells. THIS study runs the three fences that entry declared, with pass bars frozen here
BEFORE the run. If ANY fence fails, the 1.04 stays a descriptive artifact; if all three pass it becomes
a paper-tracking candidate (the fences cannot cure the cell-selection effect — a forward OOS period
remains the final arbiter, stated up front).

THE CELL (reconstructed EXACTLY as frozen in fractal_floor.build): D10 triggers, base eligibility
(warmup 260, med_turn >= Rs 1cr, close >= 20, gaps <= 6d, >= 2012-06-01), floor age <= 252, event
de-overlap 22 bars, one open trade per symbol across ALL prox<=0.15 trades; the CELL keeps daily marks
only for trades with prox <= 0.10. Entry close i+1; trail = max(floor, every 2-degree down-fractal low
confirmed after the signal bar, ratchet up only); exit close j+1 after the first close < trail; flat
0.3%/side. Reconstruction is verified against the frozen JSON (full Sharpe within +/-0.03 of 1.04)
before any fence is scored.

FENCE 1 — PARTICIPATION COST (the C-BLEND killer). Cost model = cost_participation.side_costs VERBATIM
(K=0.6 sqrt-law, POV cap 10%/day, delay penalty 0.5*sigma*sqrt(days-1), tiered half-spread+fees);
order_value = AUM / 69 (the cell's frozen avg position count); sigma = trailing-66d daily vol at
signal; per-trade entry+exit costs charged on their actual entry/exit days in the daily book.
AUM frontier reported: 1 / 5 / 10 / 25 / 50 / 100 cr.
  PASS-1 = net Sharpe > 0.89 in BOTH halves (2012-18 / 2019-26) at AUM >= Rs 10cr.

FENCE 2 — RANDOM-ENTRY / SAME-EXIT CONTROL (is the entry inert?). For every real cell trade, control
trades with IDENTICAL risk geometry: same symbol, synthetic floor = signal close / (1 + real prox),
same trail engine, same flat cost — only the WHERE/WHEN of entry is randomized. Family A = uniform
random eligible bar (>=2012-06); family B = uniform random eligible bar in the SAME CALENDAR YEAR as
the real trade (regime-matched). Seeds 42/43/44 per family (3 independent books each).
  PASS-2 = real flat-cost FULL Sharpe >= family-mean + 0.15 for BOTH families, AND real h2 Sharpe
  > each family's mean h2. (If a random entry with the same stop geometry reproduces the book, the
  fractal floor carries no entry information — the Wolfe craft lesson, inverted.)

FENCE 3 — FILL REALISM. Re-run the real cell with BOTH: entry lagged one extra bar (close i+2) AND
pessimistic stop fills (when stopped, exit value = min(next close, trail level) — no favorable
bounce-back credit), flat 0.3%/side.
  PASS-3 = net Sharpe > 0.89 in BOTH halves under the combined stress.
  (Sensitivity reported, not gated: 1.5x flat cost on the base engine.)

OVERALL: PROMOTABLE-to-paper-tracking requires PASS on ALL THREE; otherwise BLOCKED (ledger gets the
numbers either way). Universe/history identical to fractal_floor; seed-fixed; DESCRIPTIVE-ONLY output.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.fractal_fences --run       # everything -> out/fractal_fences.json
  ... --selftest                                    # offline synthetic checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

from .common import LIQ_FLOOR, eq_symbols, load_series, main_conn
from .cost_participation import side_costs
from .fractal_floor import (AGE_MAX, DEOVERLAP, MAX_GAP, MIN_CLOSE, PROX_MAX,
                            START, UPDEG, WARMUP, fractal_flags, scan)
from .streamband import _stats_monthly, roll_std

COST_SIDE = 0.003
PROX_CELL = 0.10
TARGET_POS = 69.0
CR = 1e7
AUM_LIST = [1, 5, 10, 25, 50, 100]          # in crore
PASS_AUM = 10
SEEDS = (42, 43, 44)
MARGIN = 0.15
FROZEN_FULL = 1.04
RECON_TOL = 0.03
HALF_SPLIT = "2019-01"


class Book:
    """Daily equal-weight across open trades; monthly compounding; optional
    per-day extra cost hits (entry/exit costs land on their actual days)."""

    def __init__(self):
        self.days = {}

    def add(self, date, r):
        cell = self.days.setdefault(date, [0.0, 0])
        cell[0] += r
        cell[1] += 1

    def stats(self):
        months = {}
        for dte in sorted(self.days):
            s, c = self.days[dte]
            months.setdefault(dte[:7], []).append(s / c)
        mm = sorted(months)
        mr = [float(np.prod([1 + r for r in months[m]]) - 1) for m in mm]
        full = _stats_monthly(mr)
        h1 = _stats_monthly([r for m, r in zip(mm, mr) if m < HALF_SPLIT])
        h2 = _stats_monthly([r for m, r in zip(mm, mr) if m >= HALF_SPLIT])
        return {"full": full, "h1": h1, "h2": h2}


def walk_exit(S, sig, entry, floor, fr_lo2, min_fill=False):
    """Trail-stop walk from `entry` (bar index of the entry close). Returns
    (exit_bar, exit_value_factor) where the trade return uses
    adj_close[entry] -> exit_value. Trail ratchets on 2-degree down-fractal
    lows confirmed after `sig`. Mirrors fractal_floor.build exactly."""
    n = S.n
    trail = floor
    for j in range(entry + 1, n):
        f2 = j - UPDEG
        if f2 > sig and fr_lo2[f2] and not np.isnan(S.adj_low[f2]):
            trail = max(trail, float(S.adj_low[f2]))
        cj = S.adj_close[j]
        if not np.isnan(cj) and cj < trail:
            x = min(j + 1, n - 1)
            v = float(S.adj_close[x])
            if min_fill:
                v = min(v, trail)
            return x, v, 0
    x = n - 1
    return x, float(S.adj_close[x]), 1


def mark_trade(book, S, entry, exit_bar, exit_val, cost_entry, cost_exit):
    """Daily marks entry+1..exit; the final day's mark is adjusted so the trade
    compounds exactly to exit_val/entry_val; costs hit their actual days."""
    p0 = float(S.adj_close[entry])
    if not (p0 > 0 and exit_bar > entry):
        return
    for k in range(entry + 1, exit_bar + 1):
        a, b = S.adj_close[k - 1], S.adj_close[k]
        if not (a > 0 and b > 0):
            continue
        r = float(b / a - 1.0)
        if k == exit_bar:
            r = float(exit_val / a - 1.0)
        if k == entry + 1:
            r -= cost_entry
        if k == exit_bar:
            r -= cost_exit
        book.add(S.date[k], r)


def run():
    mc = main_conn()
    syms = eq_symbols(mc)
    rng = {(fam, sd): np.random.default_rng(sd + (1000 if fam == "B" else 0))
           for fam in "AB" for sd in SEEDS}

    books = {"REAL": Book(), "LAG_MINFILL": Book(), "COST15": Book()}
    for a in AUM_LIST:
        books[f"AUM_{a}cr"] = Book()
    for fam in "AB":
        for sd in SEEDS:
            books[f"CTRL_{fam}_{sd}"] = Book()

    n_tr = 0
    n_sym = 0
    for sym in syms:
        n_sym += 1
        S = load_series(mc, sym)
        if S is None or S.n < 300:
            continue
        d64 = np.array(S.date, dtype="datetime64[D]")
        gap_prev = np.full(S.n, 999)
        gap_prev[1:] = (d64[1:] - d64[:-1]) / np.timedelta64(1, "D")
        gap_next = np.full(S.n, 999)
        gap_next[:-1] = gap_prev[1:]
        vol66 = roll_std(S.ret_raw, 66)
        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START))
        fr_lo2 = fractal_flags(S.adj_low, UPDEG, "low")
        years = np.array([d[:4] for d in S.date])
        pool = np.where(base_elig & (ii + 2 < S.n))[0]
        if not len(pool):
            continue

        triggers, _w = scan(S.adj_close, S.adj_high, S.adj_low, 10)
        last_ev = -10**9
        open_until = -1
        for (i, fb, fv, t1, strong) in triggers:
            if not base_elig[i] or i + 1 >= S.n or i - fb > AGE_MAX:
                continue
            if i - last_ev < DEOVERLAP:
                continue
            last_ev = i
            if i + 1 <= open_until:
                continue
            prox = S.adj_close[i] / fv - 1.0
            if not (0.0 < prox <= PROX_MAX):
                continue
            e = i + 1
            exit_bar, exit_val, censored = walk_exit(S, i, e, fv, fr_lo2)
            if exit_bar <= e or not S.adj_close[e] > 0:
                continue
            open_until = exit_bar
            if prox > PROX_CELL:
                continue                                   # trade exists; not in the cell
            n_tr += 1
            sig_mt = float(S.med_turn[i])
            sig_sd = float(vol66[i]) if np.isfinite(vol66[i]) else float("nan")

            # REAL flat + 1.5x sensitivity
            mark_trade(books["REAL"], S, e, exit_bar, exit_val, COST_SIDE, COST_SIDE)
            mark_trade(books["COST15"], S, e, exit_bar, exit_val,
                       1.5 * COST_SIDE, 1.5 * COST_SIDE)

            # FENCE-1: AUM ladder (same path, participation costs on entry/exit days)
            for a in AUM_LIST:
                fx_in, imp_in, _ = side_costs(sig_mt, sig_sd, a * CR / TARGET_POS)
                fx_out, imp_out, _ = side_costs(sig_mt, sig_sd, a * CR / TARGET_POS)
                mark_trade(books[f"AUM_{a}cr"], S, e, exit_bar, exit_val,
                           fx_in + imp_in, fx_out + imp_out)

            # FENCE-3: entry lag +1 AND pessimistic stop fill
            e2 = i + 2
            if e2 < S.n - 1 and S.adj_close[e2] > 0:
                xb, xv, _c = walk_exit(S, i, e2, fv, fr_lo2, min_fill=True)
                if xb > e2:
                    mark_trade(books["LAG_MINFILL"], S, e2, xb, xv, COST_SIDE, COST_SIDE)

            # FENCE-2: matched-geometry random-entry controls
            for fam in "AB":
                fam_pool = pool if fam == "A" else pool[years[pool] == S.date[i][:4]]
                if not len(fam_pool):
                    continue
                for sd in SEEDS:
                    r = int(rng[(fam, sd)].choice(fam_pool))
                    re_ = r + 1
                    if re_ >= S.n or not S.adj_close[re_] > 0:
                        continue
                    rfloor = float(S.adj_close[r]) / (1.0 + prox)
                    xb, xv, _c = walk_exit(S, r, re_, rfloor, fr_lo2)
                    if xb > re_:
                        mark_trade(books[f"CTRL_{fam}_{sd}"], S, re_, xb, xv,
                                   COST_SIDE, COST_SIDE)
        if n_sym % 800 == 0:
            print(f"  …{n_sym}/{len(syms)} symbols, cell trades={n_tr}", flush=True)
    mc.close()

    out = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "cell_trades": n_tr}
    st = {k: b.stats() for k, b in books.items() if b.days}

    real = st["REAL"]
    recon_ok = (real["full"] and abs(real["full"]["sharpe"] - FROZEN_FULL) <= RECON_TOL)
    out["reconstruction"] = {"real_flat": real, "frozen_full": FROZEN_FULL,
                             "tolerance": RECON_TOL, "OK": bool(recon_ok)}

    # fence 1
    ladder = {}
    p1 = False
    for a in AUM_LIST:
        s = st.get(f"AUM_{a}cr")
        if not s or not s["full"]:
            continue
        ok = bool(s["h1"] and s["h2"] and s["h1"]["sharpe"] > 0.89 and s["h2"]["sharpe"] > 0.89)
        ladder[f"{a}cr"] = {**s, "both_halves_gt_0.89": ok}
        if a >= PASS_AUM and ok:
            p1 = True
    out["FENCE1_participation"] = {"ladder": ladder, "PASS": p1,
                                   "bar": f"both halves > 0.89 at >= Rs {PASS_AUM}cr"}

    # fence 2
    f2 = {"real_full": real["full"], "real_h2": real["h2"]}
    p2 = True
    for fam in "AB":
        fulls, h2s, per = [], [], {}
        for sd in SEEDS:
            s = st.get(f"CTRL_{fam}_{sd}")
            if s and s["full"]:
                fulls.append(s["full"]["sharpe"])
                h2s.append(s["h2"]["sharpe"] if s["h2"] else np.nan)
                per[str(sd)] = {"full": s["full"], "h2": s["h2"]}
        mf = float(np.mean(fulls)) if fulls else float("nan")
        mh = float(np.nanmean(h2s)) if h2s else float("nan")
        okf = bool(real["full"] and not np.isnan(mf)
                   and real["full"]["sharpe"] >= mf + MARGIN)
        okh = bool(real["h2"] and not np.isnan(mh) and real["h2"]["sharpe"] > mh)
        f2[f"family_{fam}"] = {"mean_full": round(mf, 3), "mean_h2": round(mh, 3),
                               "seeds": per,
                               "margin_full": round(real["full"]["sharpe"] - mf, 3)
                               if real["full"] and not np.isnan(mf) else None,
                               "full_ok": okf, "h2_ok": okh}
        p2 = p2 and okf and okh
    f2["PASS"] = p2
    f2["bar"] = f"real full >= control-mean + {MARGIN} AND real h2 > control h2, both families"
    out["FENCE2_random_entry_same_exit"] = f2

    # fence 3
    lm = st.get("LAG_MINFILL")
    p3 = bool(lm and lm["h1"] and lm["h2"]
              and lm["h1"]["sharpe"] > 0.89 and lm["h2"]["sharpe"] > 0.89)
    out["FENCE3_fill_realism"] = {"lag1_minfill": lm, "PASS": p3,
                                  "bar": "both halves > 0.89 under entry-lag+1 AND min-fill stops",
                                  "sensitivity_cost_1.5x": st.get("COST15")}

    verdict = ("PROMOTABLE-to-paper-tracking" if (recon_ok and p1 and p2 and p3)
               else "BLOCKED (fence fail)" if recon_ok else "VOID (reconstruction mismatch)")
    out["VERDICT"] = verdict

    from .common import OUT_DIR  # noqa: PLC0415
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fractal_fences.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== FRACTAL FENCES VERDICT: {verdict} ===")
    return out


# --------------------------------------------------------------------------- #
def selftest():
    # walk_exit: trail ratchet + min_fill behave as specified on a hand-built path
    class T:
        pass
    S = T()
    S.adj_close = np.array([100, 102, 104, 103, 101, 99.0, 104, 105], dtype=float)
    S.adj_low = np.array([99, 101, 103, 101.5, 100, 98.0, 103, 104], dtype=float)
    S.n = 8
    S.date = [f"2020-01-0{k+1}" for k in range(8)]
    fr = np.zeros(8, bool)
    fr[4] = True                       # 2-deg down-fractal at bar 4 (low 100), confirmed bar 6
    x, v, c = walk_exit(S, 0, 1, 95.0, fr)             # floor 95; close never < trail until...
    # trail becomes 100 at bar 6; close[5]=99 evaluated BEFORE confirmation -> no stop at 5;
    # bars 6,7 are above 100 -> censored at end
    assert (x, c) == (7, 1), (x, c)
    S2 = T()
    S2.adj_close = np.array([100, 102, 104, 103, 101, 99.0, 99.5, 105], dtype=float)
    S2.adj_low = S.adj_low.copy()
    S2.n = 8
    S2.date = S.date
    x2, v2, c2 = walk_exit(S2, 0, 1, 95.0, fr)          # at bar 6 trail=100, close 99.5 < 100 -> exit bar 7
    assert (x2, c2) == (7, 0)
    assert v2 == 105.0                                   # plain fill = next close
    x3, v3, c3 = walk_exit(S2, 0, 1, 95.0, fr, min_fill=True)
    assert v3 == 100.0                                   # pessimistic fill capped at the trail

    # Book: two flat trades of +10% over 2 days compound to the same monthly ret
    b = Book()
    S3 = T()
    S3.adj_close = np.array([100.0, 105, 110], dtype=float)
    S3.n = 3
    S3.date = ["2020-02-01", "2020-02-02", "2020-02-03"]
    mark_trade(b, S3, 0, 2, 110.0, 0.0, 0.0)
    st = b.stats()
    assert st["full"] is None                            # <6 months -> no stats, but days exist
    assert abs(sum(v[0] for v in b.days.values()) - (0.05 + 110 / 105 - 1)) < 1e-9

    print("FRACTAL_FENCES selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
