"""Harmonic pattern reliability backtest (D72) — the GATE before trusting harmonics.

Ramana's principle ([[ramana-working-principles]]): don't dress research as product, and
record every result as a benchmark. Detection (harmonic_patterns.py) is the cheap part;
this answers the only question that matters — do completed harmonic patterns carry a real
forward edge on OUR universe, by pattern type × horizon, vs the market's own drift?

Method (mirrors the Wolfe / ignition backtests):
  • Universe = survivorship-INCLUSIVE (top-liquid incl. delisted) so the result isn't a
    survivor mirage.
  • For each CONFIRMED pattern, entry = `lag` bars AFTER point D (non-repaint: a zigzag D
    only confirms once price has swung away, so a few-bar lag keeps it point-in-time).
  • Forward outcome over horizons (bars), SIGNED by the pattern's reversal direction
    (bull = long, bear = short), reported as median + hit-rate.
  • Baseline = the same-horizon directional drift (long-drift for bulls, short-drift for
    bears) sampled across the same universe — a harmonic only has edge if it BEATS its
    directional baseline.
  • Score tiers test whether ratio-fit quality stratifies outcomes (as Wolfe's Q did).

DESCRIPTIVE-ONLY. Output is a benchmark, not a trading signal.

Run on the VPS (real archive — the local hermes.db is a 4-symbol stub):
  python -m src.automation.harmonic_backtest --universe inclusive
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from statistics import median

try:
    from src.core.db import get_conn
    from src.automation.wolfe import stock_series, scan_universe
    from src.automation.harmonic_patterns import detect_from_series
except Exception:  # pragma: no cover
    from core.db import get_conn  # type: ignore
    from automation.wolfe import stock_series, scan_universe  # type: ignore
    from automation.harmonic_patterns import detect_from_series  # type: ignore


def _pct(xs):
    return f"{100*median(xs):+5.1f}%" if xs else "   — "


def _hit(xs):
    return f"{100*sum(1 for x in xs if x > 0)/len(xs):3.0f}%" if xs else "  —"


def _report(agg, base, n_syms, horizons):
    lines = [f"\nHarmonic reliability — {n_syms} symbols (survivorship-inclusive)\n"]
    # baseline
    lines.append("BASELINE directional drift (median | hit):")
    for dirn in ("BULL", "BEAR"):
        seg = "  ".join(f"{h}b {_pct(base[dirn][h])} {_hit(base[dirn][h])}" for h in horizons)
        lines.append(f"  {dirn:4}  {seg}")
    lines.append("")
    # per pattern, with totals per direction
    tot = defaultdict(lambda: {"n": 0, "rets": {h: [] for h in horizons}})
    lines.append(f"{'pattern':<16}{'dir':<6}{'n':>5}   " + "  ".join(f"{h}b(med|hit)" for h in horizons))
    for (name, dirn) in sorted(agg, key=lambda kd: (kd[1], -agg[kd]["n"])):
        a = agg[(name, dirn)]
        seg = "  ".join(f"{_pct(a['rets'][h])} {_hit(a['rets'][h])}" for h in horizons)
        lines.append(f"{name:<16}{dirn:<6}{a['n']:>5}   {seg}")
        tot[dirn]["n"] += a["n"]
        for h in horizons:
            tot[dirn]["rets"][h] += a["rets"][h]
    lines.append("")
    for dirn in ("BULL", "BEAR"):
        t = tot[dirn]
        seg = "  ".join(f"{_pct(t['rets'][h])} {_hit(t['rets'][h])}" for h in horizons)
        lines.append(f"{'ALL ' + dirn:<22}{t['n']:>5}   {seg}")
    return "\n".join(lines)


def _report_score_tiers(per_setup, horizons):
    tier = {"hi (>=0.6)": {h: [] for h in horizons}, "lo (<0.6)": {h: [] for h in horizons}}
    for sc, dirn, rets in per_setup:
        b = "hi (>=0.6)" if sc >= 0.6 else "lo (<0.6)"
        for h in horizons:
            if h in rets:
                tier[b][h].append(rets[h])
    out = ["\nscore tier (pooled, SIGNED by reversal direction):",
           f"{'tier':<12}{'n':>6}   " + "  ".join(f"{h}b(med|hit)" for h in horizons)]
    for b in ("hi (>=0.6)", "lo (<0.6)"):
        n = len(tier[b][horizons[0]]) if tier[b][horizons[0]] else 0
        seg = "  ".join(f"{_pct(tier[b][h])} {_hit(tier[b][h])}" for h in horizons)
        out.append(f"{b:<12}{n:>6}   {seg}")
    return "\n".join(out)


def run(universe="inclusive", k=1.5, lag=5, horizons=(10, 20, 40, 60), max_symbols=None):
    # collect per-setup too (for the score-tier read)
    per_setup = []
    with get_conn() as conn:
        syms = scan_universe(conn, universe)
        if max_symbols:
            syms = syms[:max_symbols]
        agg = defaultdict(lambda: {"n": 0, "rets": {h: [] for h in horizons}, "scores": []})
        base = {"BULL": {h: [] for h in horizons}, "BEAR": {h: [] for h in horizons}}
        hmax = max(horizons)
        n_syms = 0
        for sym in syms:
            s = stock_series(conn, sym)
            if not s:
                continue
            n_syms += 1
            dates, opens, highs, lows, closes = s
            n = len(closes)
            for p in detect_from_series(dates, opens, highs, lows, closes, k=k, forming=False):
                d_idx = p.points[-1][1]
                e = d_idx + lag
                if e >= n or closes[e] <= 0:
                    continue
                entry = closes[e]
                bull = p.direction == "BULL"
                key = (p.name, p.direction)
                agg[key]["n"] += 1
                agg[key]["scores"].append(p.score)
                rets = {}
                for h in horizons:
                    j = e + h
                    if j < n:
                        sret = ((closes[j] - entry) / entry) if bull else (-(closes[j] - entry) / entry)
                        agg[key]["rets"][h].append(sret)
                        rets[h] = sret
                per_setup.append((p.score, p.direction, rets))
            for i in range(60, n - hmax, 40):
                if closes[i] <= 0:
                    continue
                for h in horizons:
                    if i + h < n:
                        d = (closes[i + h] - closes[i]) / closes[i]
                        base["BULL"][h].append(d)
                        base["BEAR"][h].append(-d)
    print(_report(agg, base, n_syms, horizons))
    print(_report_score_tiers(per_setup, horizons))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Harmonic pattern reliability backtest")
    ap.add_argument("--universe", default="inclusive", help="inclusive | nifty500 | sym,sym")
    ap.add_argument("--k", type=float, default=1.5, help="zigzag ATR multiple")
    ap.add_argument("--lag", type=int, default=5, help="entry bars after D (non-repaint)")
    ap.add_argument("--max", type=int, default=None, help="cap symbols (smoke test)")
    a = ap.parse_args()
    run(universe=a.universe, k=a.k, lag=a.lag, max_symbols=a.max)
