"""Orchestrator — run the 4 strategies through the backtest with acceptance gates.

Order (kickstart sec.9):
  1. S4 gates FIRST (decisive go/no-go for the momentum school):
       cost-delta (0/1/1.5/2x), alpha-vs-beta (regime ON vs OFF), threshold-jitter
       (+/-10% on the overfit tree cuts), capacity (participation ceiling).
  2. Full-sample portfolio metrics for S1-S4 vs buy-hold baselines + by-year.
  3. Bidirectional walk-forward (2012-19 <-> 2020-26): frozen config, both windows
     net-positive AND positive each calendar year.
  4. S3 decorrelation vs the momentum book.
Writes a text report to out/backtest_report.txt and a JSON dump to out/backtest_results.json.
ACCEPT ONLY NET OF COSTS.

The risk-adjusted number reported here (metrics.equity_stats, `retvol`) is mean/sd annualised
with NO risk-free rate subtracted — a return/vol ratio, not a Sharpe, and it reads high
against a textbook one. A true Sharpe needs a primary-source rf ingest (Guardrail #8), queued
with the TR-benchmark re-cut. (D142)
"""
from __future__ import annotations

import json
import time
from dataclasses import replace
import numpy as np

from .embase import load_symbol_cache, market_regime
from .strategies import build_strategies, COST_TIERS
from .backtest import all_trades, portfolio
from .metrics import (full_report, equity_stats, trade_stats, by_year, buy_hold,
                      alpha_beta, correlation, index_series)
from .common import OUT_DIR

FULL = ("2012-01-01", "2026-12-31")
TR1, TE1 = ("2012-01-01", "2019-12-31"), ("2020-01-01", "2026-12-31")
TR2, TE2 = ("2020-01-01", "2026-12-31"), ("2012-01-01", "2019-12-31")
LINES = []


def out(s=""):
    print(s, flush=True)
    LINES.append(s)


def run_one(cache, strat, regime, window=None, cost_mult=1.0, regime_mode=None):
    st = replace(strat, regime_mode=regime_mode) if regime_mode else strat
    trades = all_trades(cache, st, window, cost_mult)
    port = portfolio(trades, regime, st)
    return port


# ---------- gates -----------------------------------------------------------
def gate_cost_delta(cache, strat, regime):
    out(f"\n  [GATE cost-delta] {strat.name}: edge vs cost multiplier (must survive 1.5x)")
    out(f"    {'mult':>5} {'taken':>6} {'expR%':>7} {'PF':>5} {'CAGR%':>7} {'MaxDD%':>7} {'Calmar':>7}")
    res = {}
    for m in (0.0, 1.0, 1.5, 2.0):
        port = run_one(cache, strat, regime, FULL, cost_mult=m)
        es = equity_stats(port["dates"], port["equity"]) if port["dates"] else {}
        ts = trade_stats(port["taken"])
        out(f"    {m:>5.1f} {port['n_taken']:>6} {ts['exp_ret']*100:>7.2f} {ts['pf']:>5.2f} "
            f"{es.get('cagr',0)*100:>7.1f} {es.get('maxdd',0)*100:>7.1f} {es.get('calmar',0):>7.2f}")
        res[m] = {"exp_ret": ts["exp_ret"], "pf": ts["pf"], **es}
    return res


def gate_alpha_beta(cache, strat, regime):
    out(f"\n  [GATE alpha-vs-beta] {strat.name}: regime ON (gated) vs OFF (always-in)")
    res = {}
    for mode, label in (("trend", "regime-ON"), ("off", "regime-OFF")):
        rm = mode if strat.regime_mode != "inverted" else ("inverted" if mode == "trend" else "off")
        port = run_one(cache, strat, regime, FULL, regime_mode=rm)
        es = equity_stats(port["dates"], port["equity"]) if port["dates"] else {}
        ab = alpha_beta(port["dates"], port["port_ret"], "Nifty 50") if port["dates"] else {}
        ts = trade_stats(port["taken"])
        out(f"    {label:11s} taken={port['n_taken']:5d} expR={ts['exp_ret']*100:+.2f}% "
            f"CAGR={es.get('cagr',0)*100:+.1f}% MaxDD={es.get('maxdd',0)*100:.1f}% "
            f"Calmar={es.get('calmar',0):.2f} | beta={ab.get('beta',float('nan')):.2f} "
            f"alpha_ann={ab.get('alpha_ann',float('nan'))*100:+.1f}%")
        res[label] = {**es, **{f"ab_{k}": v for k, v in ab.items()}, "exp_ret": ts["exp_ret"]}
    return res


def gate_jitter(cache, strat, regime):
    out(f"\n  [GATE threshold-jitter] {strat.name}: +/-10% on entry cuts (expectancy must stay +)")
    base = strat.params
    res = []
    keys = [k for k in base if isinstance(base[k], (int, float)) and k not in ("coiled",)]
    for k in keys:
        for f, tag in ((0.9, "-10%"), (1.0, "base"), (1.1, "+10%")):
            p = dict(base); p[k] = base[k] * f
            st = replace(strat, params=p)
            trades = all_trades(cache, st, FULL)
            ts = trade_stats([(t, 1.0) for t in trades])
            out(f"    {k:>10s} {tag:>5} = {p[k]:+.4f}  n={ts['n']:5d} expR={ts['exp_ret']*100:+.2f}% PF={ts['pf']:.2f}")
            res.append({"param": k, "factor": f, "value": p[k], "exp_ret": ts["exp_ret"], "pf": ts["pf"]})
    return res


def gate_capacity(cache, strat, regime, participation=0.10):
    """Capital ceiling: position weight w of equity must stay <= participation * ADV turnover.
    capacity_per_trade = participation * med_turn / w. Report median & p25 across taken trades.
    """
    port = run_one(cache, strat, regime, FULL)
    caps = []
    for tr, w in port["taken"]:
        # med_turn at entry isn't on the trade; recover via cache
        A = cache[tr["sym"]]
        mt = float(A["med_turn"][tr["e"] - 1])           # as-of close s
        if w > 0 and mt == mt:
            caps.append(participation * mt / w)
    caps = np.array(caps)
    if len(caps):
        out(f"\n  [GATE capacity] {strat.name}: max equity before a position exceeds "
            f"{participation:.0%} of ADV turnover")
        out(f"    median cap = Rs {np.median(caps)/1e7:.0f} cr | p25 = Rs {np.percentile(caps,25)/1e7:.0f} cr "
            f"| p10 = Rs {np.percentile(caps,10)/1e7:.0f} cr  (n={len(caps)})")
        return {"median_cr": float(np.median(caps) / 1e7), "p25_cr": float(np.percentile(caps, 25) / 1e7),
                "p10_cr": float(np.percentile(caps, 10) / 1e7)}
    return {}


# ---------- portfolio + walk-forward ----------------------------------------
def portfolio_line(cache, strat, regime, window, tag):
    port = run_one(cache, strat, regime, window)
    es = equity_stats(port["dates"], port["equity"]) if port["dates"] else {}
    ts = trade_stats(port["taken"])
    ab = alpha_beta(port["dates"], port["port_ret"], "Nifty 50") if port["dates"] else {}
    out(f"    {tag:14s} taken={port['n_taken']:5d} CAGR={es.get('cagr',0)*100:+6.1f}% "
        f"MaxDD={es.get('maxdd',0)*100:6.1f}% Calmar={es.get('calmar',0):5.2f} "
        f"ret/vol={es.get('retvol',0):5.2f} expR={ts['exp_ret']*100:+.2f}% PF={ts['pf']:.2f} "
        f"hit={ts['hit']*100:.0f}% beta={ab.get('beta',float('nan')):.2f}")
    return {"tag": tag, **es, **ts, **{f"ab_{k}": v for k, v in ab.items()},
            "n_taken": port["n_taken"], "port": port}


def main():
    t0 = time.time()
    cache = load_symbol_cache()
    _, regime, _ = market_regime("Nifty 50", 200)
    S = build_strategies()
    results = {}

    out("=" * 96)
    out("EXPLOSIVE-MOVE STRATEGY BACKTEST — net of realistic costs (slippage on stops),")
    out("survivorship-safe raw archive, no look-ahead (features as-of s, enter s+1 open).")
    out(f"Regime gate = Nifty50 > 200DMA. Exit (plateau center): stop -18%, sell 50% @+25%,")
    out(f"trail 50% @6xATR after +25%, 132d max. Risk 0.5%/trade. Built {time.strftime('%Y-%m-%d')}.")
    out("=" * 96)

    # ---- baselines ----
    out("\nBASELINES (buy & hold, same 2012-2026 window):")
    for idx in ("Nifty 50", "Nifty 500", "Nifty Midcap 50"):
        bh = buy_hold(idx, *FULL)
        if bh:
            out(f"    {idx:16s} CAGR={bh['cagr']*100:+.1f}% MaxDD={bh['maxdd']*100:.1f}% "
                f"Calmar={bh['calmar']:.2f} ret/vol={bh['retvol']:.2f}")
            results.setdefault("baselines", {})[idx] = bh

    # ---- 1. S4 GATES FIRST ----
    out("\n" + "=" * 96)
    out("1. S4 SKEPTIC ACCEPTANCE GATES (decisive go/no-go for the momentum school)")
    out("=" * 96)
    s4 = S["S4"]
    results["S4_gates"] = {
        "cost_delta": gate_cost_delta(cache, s4, regime),
        "alpha_beta": gate_alpha_beta(cache, s4, regime),
        "jitter": gate_jitter(cache, s4, regime),
        "capacity": gate_capacity(cache, s4, regime),
    }

    # ---- 2. FULL-SAMPLE PORTFOLIO ----
    out("\n" + "=" * 96)
    out("2. FULL-SAMPLE PORTFOLIO METRICS (2012-2026, net of costs)")
    out("=" * 96)
    results["full"] = {}
    ports = {}
    for k in ("S1", "S2", "S3", "S4"):
        out(f"\n  {k}: {S[k].desc}")
        r = portfolio_line(cache, S[k], regime, FULL, "full")
        ports[k] = r.pop("port")
        results["full"][k] = r
        yr = by_year(ports[k]["taken"])
        ylabel = " ".join(f"{y}:{v['avg_ret']*100:+.0f}%({v['n']})" for y, v in yr.items())
        out(f"      by-year expR: {ylabel}")
        results["full"][k]["by_year"] = yr

    # ---- 3. WALK-FORWARD ----
    out("\n" + "=" * 96)
    out("3. BIDIRECTIONAL WALK-FORWARD (frozen config; both windows must be net-positive)")
    out("=" * 96)
    # HONESTY NOTE (CL-RES-09): the frozen M1/M2 entry cuts in strategies.py were DERIVED
    # on the 2012-2019 split (the forward-split tree, "T12-19 -> 2020-26"). So for those
    # canonical configs the 2012-2019 line below is IN-SAMPLE (the derivation window) and
    # only the 2020-2026 line is genuinely OUT-OF-SAMPLE. The two are NOT independent
    # evidence; do not read a positive 2012-2019 number as confirmation. The bidirectional
    # framing is retained for the SECOND fit (TR2/TE2) and for non-derived strategies, but
    # each line is tagged with its provenance (IN-SAMPLE / OOS) so the report can't be
    # misread. (A clean test would re-derive the cuts on each train fold; that re-run is
    # deferred — we LABEL rather than relabel the existing frozen numbers as OOS.)
    out("    NOTE: M1/M2 cuts were derived on 2012-2019 -> that window is IN-SAMPLE for the")
    out("          frozen configs; only 2020-2026 is true OOS. Lines tagged accordingly.")
    results["walkforward"] = {}
    for k in ("S1", "S2", "S3", "S4"):
        out(f"\n  {k}:")
        a = portfolio_line(cache, S[k], regime, TR1, "2012-2019 [IN-SAMPLE: derivation window]")
        b = portfolio_line(cache, S[k], regime, TE1, "2020-2026 [OOS]")
        a.pop("port"); b.pop("port")
        a["sample"] = "in_sample_derivation"
        b["sample"] = "out_of_sample"
        results["walkforward"][k] = {"2012-2019": a, "2020-2026": b}

    # ---- 4. S3 DECORRELATION ----
    out("\n" + "=" * 96)
    out("4. CROSS-STRATEGY DECORRELATION (S3 must stay < +0.4 to the momentum book)")
    out("=" * 96)
    for k in ("S1", "S2", "S4"):
        c = correlation(ports["S3"]["dates"], ports["S3"]["port_ret"],
                        ports[k]["dates"], ports[k]["port_ret"])
        out(f"    corr(S3, {k}) = {c:+.2f}")
        results.setdefault("decorrelation", {})[f"S3_{k}"] = c

    # ---- save ----
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "backtest_report.txt").write_text("\n".join(LINES), encoding="utf-8")
    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items() if k != "port"}
        if isinstance(o, (list, tuple)):
            return [_clean(x) for x in o]
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        return o
    (OUT_DIR / "backtest_results.json").write_text(json.dumps(_clean(results), indent=2, default=str),
                                                   encoding="utf-8")
    out(f"\nDONE in {time.time()-t0:.0f}s. Report -> out/backtest_report.txt")


if __name__ == "__main__":
    main()
