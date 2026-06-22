"""Loss-control research (all in %): can we bring the worst year (2025, -11%) down to the
controllable ~-3% level, and how much return does it cost? Levers: volatility-target
tightness + a drawdown circuit-breaker (de-risk when the book falls X% below its peak)."""
import numpy as np
from explosive_moves.v2_backtest import run


def by_period(daily, dates, key):
    d = {}
    for dt, r in zip(dates, daily):
        d.setdefault(dt[:key], []).append(r)
    return {k: (np.prod([1 + x for x in v]) - 1) for k, v in d.items()}


def stats_pct(daily, dates):
    yr = by_period(daily, dates, 4)
    eq = np.cumprod(1 + np.array(daily)); peak = np.maximum.accumulate(eq)
    dd = (eq / peak - 1).min(); yrs = len(eq) / 252
    cagr = eq[-1] ** (1 / yrs) - 1
    yv = sorted(yr.values())
    return {"cagr": cagr, "maxdd": dd, "worst": yv[0], "worst2": yv[1],
            "pos_years": sum(1 for v in yr.values() if v > 0), "n_years": len(yr),
            "y2022": yr.get("2022", 0), "y2025": yr.get("2025", 0), "yr": yr}


base = run(score="riskadj", exit_top=40, vtarget=0.25, use_sl=False)
b = stats_pct(base["daily"], base["dates"])
print("BASE (risk-adj momentum + buffer + vol-target 0.25) — yearly % returns:")
for y, v in sorted(b["yr"].items()):
    print(f"   {y}: {v*100:+5.1f}%")

print("\nWORST YEAR 2025 — month by month (%):")
for m, v in sorted(by_period(base["daily"], base["dates"], 7).items()):
    if m.startswith("2025"):
        print(f"   {m}: {v*100:+5.1f}%")
print("2022 monthly (the controllable -3% year):")
for m, v in sorted(by_period(base["daily"], base["dates"], 7).items()):
    if m.startswith("2022"):
        print(f"   {m}: {v*100:+5.1f}%")

print("\nLOSS-CONTROL SWEEP (all %). Goal: shrink worst year toward -3% at low CAGR cost.")
print(f"{'setting':38}{'CAGR':>7}{'worstYr':>8}{'2nd':>7}{'maxDD':>7}{'2022':>7}{'2025':>7}{'+yrs':>6}")
configs = [
    ("VT0.25 (current)", dict(vtarget=0.25)),
    ("VT0.20", dict(vtarget=0.20)),
    ("VT0.15", dict(vtarget=0.15)),
    ("VT0.25 + brake@-10%", dict(vtarget=0.25, dd_brake=0.10)),
    ("VT0.20 + brake@-10%", dict(vtarget=0.20, dd_brake=0.10)),
    ("VT0.20 + brake@-8%", dict(vtarget=0.20, dd_brake=0.08)),
    ("VT0.15 + brake@-8%", dict(vtarget=0.15, dd_brake=0.08)),
]
for name, kw in configs:
    r = run(score="riskadj", exit_top=40, use_sl=False, **kw)
    s = stats_pct(r["daily"], r["dates"])
    print(f"{name:38}{s['cagr']*100:>6.1f}%{s['worst']*100:>7.1f}%{s['worst2']*100:>6.1f}%"
          f"{s['maxdd']*100:>6.1f}%{s['y2022']*100:>6.1f}%{s['y2025']*100:>6.1f}%{s['pos_years']:>4}/{s['n_years']}")
