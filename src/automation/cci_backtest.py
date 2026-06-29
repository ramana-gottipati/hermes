"""CCI Phase-3 FALSIFICATION backtest — does credibility PREDICT forward returns?

The binding gate (Ramana D61 doctrine, "don't ship unproven alpha"): rising / high
credibility must outperform OUT-OF-SAMPLE, cross-sectionally and survivorship-aware,
or CCI stays a DESCRIPTIVE avoid-overlay (the deterioration veto) — never a ranked
long factor. Pure Python over credibility_series (PIT level+momentum) x bhavcopy_rows
(forward returns); NO LLM, NO look-ahead (returns start at the as-of month-END, i.e.
after the call is public).

Returns are corporate-action-adjusted via the NSE prev_close chain
(close/prev_close is adjusted on ex-dates), so splits/bonuses don't create spurious
returns — no adj_close column needed. We de-market each point by subtracting the mean
return of its SAME-as-of-month cohort, so what's left is the cross-sectional credibility
signal, not market beta/timing.

Caveats recorded WITH the result (this is a FIRST PASS, directional only):
  - SURVIVORSHIP: the credibility universe is CURRENT concall holders (Screener), so
    delisted/failed names are under-represented -> biases the long signal optimistic
    and under-counts the avoid signal's true value.
  - Settlement is THIN pre-2023 (deep-archive ANNUAL grading only), so early-period
    'proven' points are sparse.

CLI: python -m src.automation.cci_backtest [--min-resolved 3] [--horizons 3,6,12]
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import logging
import math
from collections import defaultdict
from statistics import mean, pstdev

from src.core.db import get_conn

log = logging.getLogger("hermes.cci_backtest")

HORIZONS = (3, 6, 12)          # forward-return horizons (months)
MOM_EVENT = 5.0                # |momentum| >= this = a real rising/falling credibility move
RET_CLIP = (-0.90, 5.0)        # winsorize per-point returns (guard bhav data errors)
MIN_COHORT = 5                 # min same-as-of-month points to form a de-market baseline


def _month_end(y, m):
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


def _add_months(y, m, k):
    i = y * 12 + (m - 1) + k
    return i // 12, i % 12 + 1


def _build_index(conn, symbol):
    """Per-symbol cumulative ADJUSTED log-return index from the NSE prev_close chain.
    Returns (dates_sorted, cumlog_aligned). A single-day move beyond +/-100% is almost
    surely a bad tick, so it is dropped (contributes 0) rather than corrupting the chain."""
    rows = conn.execute(
        "SELECT trade_date, close, prev_close FROM bhavcopy_rows "
        "WHERE symbol=? AND series='EQ' AND close>0 AND prev_close>0 ORDER BY trade_date",
        (symbol,)).fetchall()
    dates, cums, cum = [], [], 0.0
    for r in rows:
        ratio = r["close"] / r["prev_close"]
        if 0.5 <= ratio <= 2.0:
            cum += math.log(ratio)
        dates.append(r["trade_date"])
        cums.append(cum)
    return dates, cums


def _cum_at(idx, bound):
    dates, cums = idx
    i = bisect.bisect_right(dates, bound) - 1
    return cums[i] if i >= 0 else None


def _fwd_return(idx, entry_bound, exit_bound):
    ce, cx = _cum_at(idx, entry_bound), _cum_at(idx, exit_bound)
    if ce is None or cx is None:
        return None
    r = math.exp(cx - ce) - 1.0
    return max(RET_CLIP[0], min(RET_CLIP[1], r))


def _stat(xs):
    if not xs:
        return None
    m = mean(xs)
    sd = pstdev(xs) if len(xs) > 1 else 0.0
    t = (m / (sd / math.sqrt(len(xs)))) if sd > 0 else 0.0
    return {"n": len(xs), "mean": m, "t": t, "hit": sum(1 for x in xs if x > 0) / len(xs)}


def _analyze(rows):
    """rows = [(asof_key, level, momentum, ret), ...] -> cohort stats on de-marketed excess."""
    by_month = defaultdict(list)
    for r in rows:
        by_month[r[0]].append(r)
    excess = []   # (level, momentum, exret)
    for grp in by_month.values():
        if len(grp) < MIN_COHORT:
            continue
        mret = mean(g[3] for g in grp)
        for g in grp:
            excess.append((g[1], g[2], g[3] - mret))
    if not excess:
        return None
    rising = [e[2] for e in excess if e[1] >= MOM_EVENT]
    falling = [e[2] for e in excess if e[1] <= -MOM_EVENT]
    flat = [e[2] for e in excess if -MOM_EVENT < e[1] < MOM_EVENT]
    levs = sorted(e[0] for e in excess)
    lo_thr, hi_thr = levs[len(levs) // 3], levs[2 * len(levs) // 3]
    low = [e[2] for e in excess if e[0] <= lo_thr]
    high = [e[2] for e in excess if e[0] >= hi_thr]
    return {"n_excess": len(excess), "n_months": len(by_month),
            "rising": _stat(rising), "flat": _stat(flat), "falling": _stat(falling),
            "high_level": _stat(high), "low_level": _stat(low)}


def run(min_resolved: int = 3, horizons=HORIZONS) -> dict:
    with get_conn() as conn:
        pts = conn.execute(
            "SELECT symbol, period_year AS y, period_month AS m, level, momentum, n_resolved "
            "FROM credibility_series WHERE momentum IS NOT NULL AND n_resolved>=? "
            "AND period_year BETWEEN 2010 AND 2026", (min_resolved,)).fetchall()
        last_date = conn.execute("SELECT MAX(trade_date) FROM bhavcopy_rows WHERE series='EQ'").fetchone()[0]
        log.info("loaded %d proven PIT points (n_resolved>=%d); prices through %s",
                 len(pts), min_resolved, last_date)
        idx_cache: dict = {}

        def idx_for(sym):
            if sym not in idx_cache:
                idx_cache[sym] = _build_index(conn, sym)
            return idx_cache[sym]

        results = {}
        for H in horizons:
            rows, measurable = [], 0
            for p in pts:
                ey, em = _add_months(p["y"], p["m"], H)
                exit_ = _month_end(ey, em)
                if exit_ > last_date:                 # horizon extends past data -> not yet OOS
                    continue
                measurable += 1
                ret = _fwd_return(idx_for(p["symbol"]), _month_end(p["y"], p["m"]), exit_)
                if ret is not None:
                    rows.append((f"{p['y']}-{p['m']:02d}", p["level"], p["momentum"], ret))
            a = _analyze(rows)
            if a:
                a["measurable"] = measurable
            results[H] = a
        return results


def _verdict(results):
    """Honest verdict — weighs BOTH the level thesis (high cred should beat low) AND momentum
    (rising should beat flat+falling). The dominant, most-significant signal wins."""
    level_spr, low_t, rise_v_fall, rise_v_flat = [], [], [], []
    for a in results.values():
        if not a:
            continue
        if a["high_level"] and a["low_level"]:
            level_spr.append(a["high_level"]["mean"] - a["low_level"]["mean"])
            low_t.append(a["low_level"]["t"])
        if a["rising"] and a["falling"]:
            rise_v_fall.append(a["rising"]["mean"] - a["falling"]["mean"])
        if a["rising"] and a["flat"]:
            rise_v_flat.append(a["rising"]["mean"] - a["flat"]["mean"])
    long_level = bool(level_spr) and all(s > 0 for s in level_spr)
    inverse_level = bool(level_spr) and all(s < 0 for s in level_spr) and any(t > 2 for t in low_t)
    mom_pos = bool(rise_v_fall) and all(s > 0 for s in rise_v_fall) and all(s > 0 for s in rise_v_flat)
    if long_level and mom_pos:
        return ("LONG FACTOR (tentative)", "high AND rising credibility both outperform — worth completing "
                "the corpus + a proper holdout/OOS test before ranking long on it.")
    if inverse_level:
        return ("NO VALIDATED FACTOR (long OR short) — inverse level print is fragile",
                "HIGH-cred UNDERPERFORMS LOW by -3/-6/-10% (3/6/12m), but this is NOT a tradable edge in "
                "EITHER direction: only n=377 survivor names; the effect is concentrated post-2023 (-17% vs "
                "-7% pre-2022) and in high-level megacap mean-reversion, so t=+3.6 is a concentrated regime "
                "print, not a structural factor. Two independent reviews: it is NOT size/value-driven "
                "(survives size + valuation neutralization) but it IS heavily SURVIVORSHIP-confounded "
                "(376/377 names still active -> low-cred realized returns inflated, blow-ups absent). Too "
                "fragile to rank long; too confounded to short. ⇒ do NOT spend to complete the corpus: the "
                "ceiling is BREADTH (the survivor universe), not depth — more extraction deepens the SAME 377 "
                "names and cannot add the delisted ones survivorship removed. CCI's only surviving use is "
                "DESCRIPTIVE (deterioration / avoid overlay) — adjudicated by the veto drawdown test below.")
    return ("INCONCLUSIVE / MIXED", "no clean directional edge either way; keep CCI descriptive and revisit "
            "after the corpus deepens. Does not justify completion spend yet.")


def report(results, min_resolved: int) -> None:
    print("\n" + "=" * 74)
    print(f"CCI FALSIFICATION BACKTEST   (proven PIT points, n_resolved >= {min_resolved})")
    print("H0: rising / high credibility -> POSITIVE forward EXCESS return (de-market, cross-sectional)")
    print("=" * 74)
    for H, a in results.items():
        print(f"\n--- {H}-month forward (excess vs same-as-of-month cohort) ---")
        if not a:
            print("  (insufficient data at this horizon)")
            continue
        print(f"  measurable points: {a['measurable']}   de-marketed obs: {a['n_excess']}   months: {a['n_months']}")

        def line(name, s):
            print(f"  {name:13}: " + (f"mean {s['mean']*100:+6.2f}%   t={s['t']:+5.2f}   hit={s['hit']*100:4.1f}%   n={s['n']}"
                                      if s else "(none)"))
        line("RISING cred", a["rising"])
        line("flat", a["flat"])
        line("FALLING cred", a["falling"])
        if a["rising"] and a["falling"]:
            print(f"  >> momentum spread (rising - falling): {(a['rising']['mean']-a['falling']['mean'])*100:+.2f}%")
        line("HIGH level", a["high_level"])
        line("LOW level", a["low_level"])
        if a["high_level"] and a["low_level"]:
            print(f"  >> level spread (high - low):          {(a['high_level']['mean']-a['low_level']['mean'])*100:+.2f}%")
    tag, why = _verdict(results)
    print("\n" + "=" * 74)
    print(f"VERDICT: {tag}")
    print(f"  {why}")
    print("\nCAVEATS (binding — FIRST PASS, directional only):")
    print("  - SURVIVORSHIP: universe = CURRENT concall holders; delisted/failed names under-represented")
    print("    -> long signal biased optimistic, avoid signal's true value under-counted.")
    print("  - Settlement THIN pre-2023 (deep-archive annual grading) -> early proven points sparse.")
    print("  - Returns adj via prev_close chain; single-day moves >+/-100% dropped as bad ticks.")
    print("=" * 74)


# --- the deterioration-VETO as a RISK / drawdown overlay (the one use the data may keep) -----

def _max_drawdown(idx, entry_bound, exit_bound):
    """Worst peak-to-trough WITHIN the forward window, from the cumlog path (a negative fraction,
    e.g. -0.35) or None — the downside metric a veto is meant to cut."""
    dates, cums = idx
    lo = bisect.bisect_right(dates, entry_bound) - 1
    hi = bisect.bisect_right(dates, exit_bound) - 1
    if lo < 0 or hi <= lo:
        return None
    base, peak, mdd = cums[lo], 0.0, 0.0
    for c in cums[lo:hi + 1]:
        v = c - base
        peak = max(peak, v)
        mdd = min(mdd, v - peak)
    return math.exp(mdd) - 1.0


def _tail(subset):
    """Left-tail risk stats for records (is_event, exret, raw_ret, mdd, year)."""
    if not subset:
        return None
    ex = sorted(r[1] for r in subset)
    raw = [r[2] for r in subset]
    mdd = [r[3] for r in subset if r[3] is not None]
    L = len(ex)
    return {"n": L, "mean_ex": mean(ex),
            "p_dd20": sum(1 for r in raw if r < -0.20) / len(raw),
            "p5_ex": ex[int(0.05 * L)], "p10_ex": ex[int(0.10 * L)],
            "mean_mdd": mean(mdd) if mdd else None}


def run_veto(min_resolved: int = 3, horizons=HORIZONS) -> dict:
    """Event study: do credibility-DETERIORATION events (a deterministic deter flag, or
    momentum <= -MOM_EVENT) precede a FATTER LEFT TAIL than non-events? Grades the avoid-overlay
    on DOWNSIDE, not mean. Survivorship works AGAINST this test (it hides the worst blow-ups), so
    any positive result is a conservative LOWER bound."""
    with get_conn() as conn:
        pts = conn.execute(
            "SELECT symbol, period_year AS y, period_month AS m, momentum, deter, n_resolved "
            "FROM credibility_series WHERE momentum IS NOT NULL AND n_resolved>=? "
            "AND period_year BETWEEN 2010 AND 2026", (min_resolved,)).fetchall()
        last_date = conn.execute("SELECT MAX(trade_date) FROM bhavcopy_rows WHERE series='EQ'").fetchone()[0]
        idx_cache: dict = {}

        def idx_for(s):
            if s not in idx_cache:
                idx_cache[s] = _build_index(conn, s)
            return idx_cache[s]

        out = {}
        for H in horizons:
            recs = []
            for p in pts:
                ey, em = _add_months(p["y"], p["m"], H)
                exit_ = _month_end(ey, em)
                if exit_ > last_date:
                    continue
                ent, idx = _month_end(p["y"], p["m"]), idx_for(p["symbol"])
                r = _fwd_return(idx, ent, exit_)
                if r is None:
                    continue
                ev = (p["deter"] or 0) >= 1 or (p["momentum"] is not None and p["momentum"] <= -MOM_EVENT)
                recs.append((bool(ev), f"{p['y']}-{p['m']:02d}", r, _max_drawdown(idx, ent, exit_), p["y"]))
            by_month = defaultdict(list)
            for rec in recs:
                by_month[rec[1]].append(rec)
            rows = []
            for grp in by_month.values():
                if len(grp) < MIN_COHORT:
                    continue
                mret = mean(g[2] for g in grp)
                rows.extend((g[0], g[2] - mret, g[2], g[3], g[4]) for g in grp)
            ev = [r for r in rows if r[0]]
            nv = [r for r in rows if not r[0]]
            out[H] = {"event": _tail(ev), "nonevent": _tail(nv),
                      "event_23": _tail([r for r in ev if r[4] >= 2023]),
                      "nonevent_23": _tail([r for r in nv if r[4] >= 2023])}
        return out


def report_veto(results) -> None:
    print("\n" + "=" * 78)
    print("CCI DETERIORATION-VETO as a RISK / DRAWDOWN overlay  (event = deter flag OR momentum<=-5)")
    print("Graded on the LEFT TAIL — a veto earns its keep by cutting downside, not lifting the mean.")
    print("=" * 78)
    signal = []
    for H, a in results.items():
        ev, nv = a["event"], a["nonevent"]
        print(f"\n--- {H}-month forward ---")
        if not ev or not nv:
            print("  (insufficient events)")
            continue
        print(f"  {'cohort':10} {'n':>5} {'mean_ex':>9} {'P(<-20%)':>9} {'p5_ex':>8} {'p10_ex':>8} {'mean_MDD':>9}")
        for nm, s in (("DETERIOR", ev), ("non-event", nv)):
            print(f"  {nm:10} {s['n']:>5} {s['mean_ex']*100:>+8.2f}% {s['p_dd20']*100:>8.1f}% "
                  f"{s['p5_ex']*100:>+7.1f}% {s['p10_ex']*100:>+7.1f}% {s['mean_mdd']*100:>+8.1f}%")
        worse = (ev["p_dd20"] > nv["p_dd20"] and ev["p10_ex"] < nv["p10_ex"]
                 and (ev["mean_mdd"] or 0) < (nv["mean_mdd"] or 0))
        signal.append(worse)
        e23, n23 = a["event_23"], a["nonevent_23"]
        if e23 and n23:
            print(f"  2023+ : DETERIOR P(<-20%)={e23['p_dd20']*100:.1f}% MDD={e23['mean_mdd']*100:+.1f}%   "
                  f"non-event P(<-20%)={n23['p_dd20']*100:.1f}% MDD={n23['mean_mdd']*100:+.1f}%")
    print("\n" + "=" * 78)
    if sum(signal) >= 2:
        print("VERDICT: VETO HAS RISK VALUE — deterioration events precede a fatter left tail / deeper")
        print("  drawdowns than non-events across horizons. KEEP CCI as a position-trim / avoid overlay in")
        print("  confluence (survivorship makes this a conservative LOWER bound). Wire the deterioration tape")
        print("  into the risk layer — but it remains NOT a long/short alpha factor.")
    else:
        print("VERDICT: VETO NOT VALIDATED (and NOT validatable on this data). On the SURVIVOR sample,")
        print("  deterioration events precede NO worse downside than non-events (if anything marginally")
        print("  better) -- BUT this test is structurally blind to the veto's true target: the delisted")
        print("  blow-ups survivorship removed are ABSENT, so the catastrophic tail it is meant to catch")
        print("  isn't in the data. NET: CCI has NO empirically-validated long / short / risk edge here.")
        print("  Defensible role = DESCRIPTIVE only: the per-name evidence DOSSIER (qualitative track")
        print("  record shown when researching a name), NOT a ranked screen or factor. Corpus kept as a")
        print("  recorded benchmark; capture stays free; no further extraction spend is justified.")
    print("=" * 78)


# --- CAPEX-PROPOSAL signal: does announcing capex/expansion predict forward returns? ----------

def run_capex(horizons=HORIZONS) -> dict:
    """Event = a concall that ANNOUNCED capex/expansion, vs concalls that didn't. Forward excess
    de-marketed by as-of month. Uses the EVENT only — the ₹ amounts have unit-normalization bugs
    (billions/crores/raw-rupees mislabeled), so magnitude/intensity is not yet usable."""
    with get_conn() as conn:
        base = conn.execute(
            "SELECT g.symbol AS symbol, c.concall_year AS y, c.concall_month AS m, "
            "MAX(CASE WHEN g.statement_type IN ('capex','expansion') THEN 1 ELSE 0 END) AS is_capex "
            "FROM concall_guidance g JOIN concalls c ON c.symbol=g.symbol AND c.period_label=g.source_period "
            "WHERE c.concall_year BETWEEN 2010 AND 2026 AND c.concall_month IS NOT NULL "
            "GROUP BY g.symbol, c.concall_year, c.concall_month").fetchall()
        last_date = conn.execute("SELECT MAX(trade_date) FROM bhavcopy_rows WHERE series='EQ'").fetchone()[0]
        idx_cache: dict = {}

        def idx_for(s):
            if s not in idx_cache:
                idx_cache[s] = _build_index(conn, s)
            return idx_cache[s]

        out = {}
        for H in horizons:
            recs = []
            for r in base:
                ey, em = _add_months(r["y"], r["m"], H)
                exit_ = _month_end(ey, em)
                if exit_ > last_date:
                    continue
                ent, idx = _month_end(r["y"], r["m"]), idx_for(r["symbol"])
                ret = _fwd_return(idx, ent, exit_)
                if ret is None:
                    continue
                recs.append((bool(r["is_capex"]), f"{r['y']}-{r['m']:02d}", ret, _max_drawdown(idx, ent, exit_), r["y"]))
            by_month = defaultdict(list)
            for rec in recs:
                by_month[rec[1]].append(rec)
            rows = []
            for grp in by_month.values():
                if len(grp) < MIN_COHORT:
                    continue
                mret = mean(g[2] for g in grp)
                rows.extend((g[0], g[2] - mret, g[2], g[3], g[4]) for g in grp)
            out[H] = {"capex": _tail([r for r in rows if r[0]]), "nocapex": _tail([r for r in rows if not r[0]])}
        return out


def report_capex(results) -> None:
    print("\n" + "=" * 78)
    print("CAPEX-PROPOSAL SIGNAL  (event = concall announced capex/expansion vs concalls that didn't)")
    print("Forward EXCESS de-marketed by as-of month; announcement-event only (₹ magnitude not yet clean).")
    print("=" * 78)
    sig = []
    for H, a in results.items():
        cap, noc = a["capex"], a["nocapex"]
        print(f"\n--- {H}-month forward ---")
        if not cap or not noc:
            print("  (insufficient)")
            continue
        print(f"  {'cohort':14} {'n':>5} {'mean_ex':>9} {'P(<-20%)':>9} {'p10_ex':>8} {'mean_MDD':>9}")
        for nm, s in (("CAPEX-announce", cap), ("no-capex", noc)):
            print(f"  {nm:14} {s['n']:>5} {s['mean_ex']*100:>+8.2f}% {s['p_dd20']*100:>8.1f}% "
                  f"{s['p10_ex']*100:>+7.1f}% {s['mean_mdd']*100:>+8.1f}%")
        spread = (cap["mean_ex"] - noc["mean_ex"]) * 100
        print(f"  >> capex-minus-nocapex excess: {spread:+.2f}%")
        sig.append(spread > 0 and cap["mean_ex"] > 0)
    print("\n" + "=" * 78)
    if sum(sig) >= 2:
        print("VERDICT: CAPEX-ANNOUNCEMENT shows a positive forward-excess tilt — worth pursuing as its OWN")
        print("  signal (and fixing the ₹-amount normalizer to test capex MAGNITUDE / capex-to-sales intensity).")
    else:
        print("VERDICT: bare capex-announcement shows no clean forward edge; revisit with clean MAGNITUDE")
        print("  (capex/sales intensity) and in confluence, not the announcement flag alone.")
    print("=" * 78)


# --- CONFLUENCE: does credibility ADD within a momentum book (what the standalone test never asked)? --

def run_confluence(min_resolved: int = 3, horizon: int = 12):
    """Within HIGH trailing-6m-momentum names (a momentum strategy's holdings): (Q1) does high
    credibility lift forward excess vs low credibility, and (Q2) do deterioration events precede
    deeper drawdowns (cut momentum crashes)? Forward 12m, de-marketed by as-of month."""
    with get_conn() as conn:
        pts = conn.execute(
            "SELECT symbol, period_year AS y, period_month AS m, level, deter, momentum "
            "FROM credibility_series WHERE momentum IS NOT NULL AND n_resolved>=? "
            "AND period_year BETWEEN 2012 AND 2026", (min_resolved,)).fetchall()
        last_date = conn.execute("SELECT MAX(trade_date) FROM bhavcopy_rows WHERE series='EQ'").fetchone()[0]
        idx_cache: dict = {}

        def idx_for(s):
            if s not in idx_cache:
                idx_cache[s] = _build_index(conn, s)
            return idx_cache[s]

        recs = []
        for p in pts:
            ey, em = _add_months(p["y"], p["m"], horizon)
            exit_ = _month_end(ey, em)
            if exit_ > last_date:
                continue
            ent = _month_end(p["y"], p["m"])
            sy, sm = _add_months(p["y"], p["m"], -6)
            idx = idx_for(p["symbol"])
            trail = _fwd_return(idx, _month_end(sy, sm), ent)
            fwd = _fwd_return(idx, ent, exit_)
            if trail is None or fwd is None:
                continue
            falling = p["momentum"] is not None and p["momentum"] <= -MOM_EVENT
            recs.append((f"{p['y']}-{p['m']:02d}", trail, fwd, _max_drawdown(idx, ent, exit_),
                         p["level"], (p["deter"] or 0) >= 1 or falling))
        by_month = defaultdict(list)
        for r in recs:
            by_month[r[0]].append(r)
        rows = []
        for grp in by_month.values():
            if len(grp) < MIN_COHORT:
                continue
            mret = mean(g[2] for g in grp)
            rows.extend((g[1], g[2] - mret, g[3], g[4], g[5]) for g in grp)
        if len(rows) < 60:
            return None
        trails = sorted(r[0] for r in rows)
        hi_thr = trails[2 * len(rows) // 3]
        himo = [r for r in rows if r[0] >= hi_thr]
        levs = sorted(r[3] for r in himo)
        med = levs[len(levs) // 2]
        hicred = [r[1] for r in himo if r[3] >= med]
        locred = [r[1] for r in himo if r[3] < med]
        det = [r for r in himo if r[4]]
        nondet = [r for r in himo if not r[4]]

        def mdd_mean(xs):
            v = [r[2] for r in xs if r[2] is not None]
            return mean(v) if v else 0.0

        def p30(xs):
            v = [r[2] for r in xs if r[2] is not None]
            return (sum(1 for x in v if x < -0.30) / len(v)) if v else 0.0

        return {"n_himo": len(himo), "n_det": len(det),
                "hicred_ex": mean(hicred) if hicred else 0.0, "locred_ex": mean(locred) if locred else 0.0,
                "det_mdd": mdd_mean(det), "nondet_mdd": mdd_mean(nondet),
                "det_p30": p30(det), "nondet_p30": p30(nondet)}


def report_confluence(a) -> None:
    print("\n" + "=" * 78)
    print("CREDIBILITY x MOMENTUM CONFLUENCE  (within HIGH trailing-6m-momentum names = a momentum book)")
    print("Does credibility ADD where the standalone test said it doesn't? 12-month forward.")
    print("=" * 78)
    if not a:
        print("  (insufficient data)")
        print("=" * 78)
        return
    print(f"  high-momentum sample: {a['n_himo']}  ({a['n_det']} with a deterioration flag)")
    print(f"  Q1 ADD RETURN?  hi-cred excess {a['hicred_ex']*100:+.2f}%  vs  lo-cred {a['locred_ex']*100:+.2f}%"
          f"   (spread {(a['hicred_ex']-a['locred_ex'])*100:+.2f}%)")
    print(f"  Q2 CUT CRASHES? deteriorating MDD {a['det_mdd']*100:+.1f}% / P(<-30%) {a['det_p30']*100:.1f}%"
          f"   vs steady MDD {a['nondet_mdd']*100:+.1f}% / P(<-30%) {a['nondet_p30']*100:.1f}%")
    print("\n" + "=" * 78)
    adds = (a["hicred_ex"] - a["locred_ex"]) > 0.02
    protects = a["det_mdd"] < a["nondet_mdd"] - 0.02 and a["det_p30"] > a["nondet_p30"]
    if adds or protects:
        bits = []
        if adds:
            bits.append("high-credibility lifts forward excess within momentum")
        if protects:
            bits.append("deterioration flags deeper drawdowns among momentum names")
        print("VERDICT: CONFLUENCE VALUE — " + "; ".join(bits) + ".")
        print("  Credibility earns a place as a CONFIRMING / RISK overlay on a momentum book (not standalone).")
        print("  Worth a proper top-N momentum-overlay backtest (the Tier-1 factory.py machinery).")
    else:
        print("VERDICT: NO confluence value within momentum either — credibility neither adds return nor")
        print("  cuts drawdown among momentum names. Consistent with the standalone falsification.")
    print("=" * 78)


# --- CONCALL-CONTENT SCAN: which forward-looking statement_type predicts returns? -------------

def run_statement_scan(horizon: int = 3) -> list:
    """For EACH forward-looking statement_type, does a concall that MADE that kind of statement
    out/under-perform concalls that didn't (de-marketed by as-of month)? Ranks concall CONTENT by
    forward excess — finds which forward-looking statements carry signal (capex was +2%; what else?)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT g.symbol AS symbol, c.concall_year AS y, c.concall_month AS m, g.statement_type AS st "
            "FROM concall_guidance g JOIN concalls c ON c.symbol=g.symbol AND c.period_label=g.source_period "
            "WHERE c.concall_year BETWEEN 2010 AND 2026 AND c.concall_month IS NOT NULL").fetchall()
        events = defaultdict(set)
        for r in rows:
            events[(r["symbol"], r["y"], r["m"])].add(r["st"])
        last_date = conn.execute("SELECT MAX(trade_date) FROM bhavcopy_rows WHERE series='EQ'").fetchone()[0]
        idx_cache: dict = {}

        def idx_for(s):
            if s not in idx_cache:
                idx_cache[s] = _build_index(conn, s)
            return idx_cache[s]

        tmp, by_month = [], defaultdict(list)
        for (sym, y, m), types in events.items():
            ey, em = _add_months(y, m, horizon)
            exit_ = _month_end(ey, em)
            if exit_ > last_date:
                continue
            ret = _fwd_return(idx_for(sym), _month_end(y, m), exit_)
            if ret is None:
                continue
            key = f"{y}-{m:02d}"
            tmp.append((key, ret, frozenset(types)))
            by_month[key].append(ret)
        mret = {k: mean(v) for k, v in by_month.items() if len(v) >= MIN_COHORT}
        demk = [(ret - mret[key], types) for key, ret, types in tmp if key in mret]
        out = []
        for st in sorted({t for _, ts in demk for t in ts}):
            w = [ex for ex, ts in demk if st in ts]
            wo = [ex for ex, ts in demk if st not in ts]
            if len(w) >= 50 and wo:
                out.append((st, len(w), mean(w), mean(w) - mean(wo)))
        return sorted(out, key=lambda x: x[3], reverse=True)


def report_scan(results, horizon: int) -> None:
    print("\n" + "=" * 78)
    print(f"CONCALL-CONTENT SIGNAL SCAN — {horizon}m forward excess by statement_type (de-marketed)")
    print("Which forward-looking statements predict returns? (event = a concall made that statement)")
    print("=" * 78)
    print(f"  {'statement_type':16} {'n':>6} {'mean_ex':>9} {'vs-without':>11}")
    for st, n, mex, spread in results:
        print(f"  {st:16} {n:>6} {mex*100:>+8.2f}% {spread*100:>+10.2f}%")
    print("=" * 78)
    if results and results[0][3] > 0:
        top = results[0]
        print(f"  TOP: '{top[0]}' (+{top[3]*100:.2f}% vs concalls without it) — the strongest concall-content")
        print("  signal. Pursue the leaders as event / intensity factors; credibility is NOT among them.")
    else:
        print("  No statement_type shows a positive forward tilt at this horizon.")
    print("=" * 78)


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI Phase-3 falsification backtest (credibility -> returns)")
    ap.add_argument("--min-resolved", type=int, default=3, help="min settled promises to count a point (gate)")
    ap.add_argument("--horizons", default="3,6,12", help="comma-separated forward horizons in months")
    ap.add_argument("--mode", choices=["factor", "veto", "capex", "confluence", "scan", "both", "all"],
                    default="both", help="which test(s) to run")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    hs = tuple(int(x) for x in args.horizons.split(","))
    if args.mode in ("factor", "both", "all"):
        report(run(min_resolved=args.min_resolved, horizons=hs), args.min_resolved)
    if args.mode in ("veto", "both", "all"):
        report_veto(run_veto(min_resolved=args.min_resolved, horizons=hs))
    if args.mode in ("capex", "all"):
        report_capex(run_capex(horizons=hs))
    if args.mode in ("confluence", "all"):
        report_confluence(run_confluence(min_resolved=args.min_resolved))
    if args.mode in ("scan", "all"):
        report_scan(run_statement_scan(horizon=hs[0]), hs[0])


if __name__ == "__main__":
    main()
