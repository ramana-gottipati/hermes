"""CCI falsification GATE A — does guidance DIRECTION predict forward return?

The first cheap kill-or-save test (debate rank #2a / NEXT-SESSION P6). For every
EXTRACTED concall we read the net guidance direction (sign of the UP- vs DOWN-
promises in the call — measurable, no LLM), then the survivorship-safe forward
return entering T+2 and held ~3 months, net of costs. If "guiding up" does NOT
beat "guiding down" out of sample, the whole premise is dead and CCI should NOT
ship as a return engine (it can still serve as an avoid-tape / quality overlay).

Read-only; numpy only (no statsmodels needed). Run:
    /opt/hermes/.venv-research/bin/python -m research.cci.gate_guidance_return

VERDICT printed at the end. Honest stance (design §10): CCI is carried as a
screen/overlay until this — and gate B — clear it.
"""

from __future__ import annotations

import numpy as np

from research.cci.common import (main_conn, gather_observations, insufficient,
                                 MIN_OBS, HORIZON, ENTRY_LAG, COST_BPS)


def _welch_t(a: np.ndarray, b: np.ndarray):
    """Welch's t (unequal variance) for mean(a) - mean(b). (t, df-ish n) — SciPy-free."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    if se == 0:
        return None
    return (a.mean() - b.mean()) / se


def main() -> None:
    print("=" * 72)
    print("CCI GATE A — guidance direction -> forward return")
    print(f"  entry T+{ENTRY_LAG}, horizon {HORIZON}td, cost {COST_BPS:.0f}bps, "
          f"survivorship-safe (bhav archive incl. delisted)")
    print("=" * 72)
    with main_conn() as con:
        obs = gather_observations(con)
    n = len(obs)
    print(f"  observations (extracted concalls with a forward window): {n}")
    if n < MIN_OBS:
        insufficient(n)
        # still show the directional split we have, as a smoke check of the wiring
        _peek(obs)
        return

    up = np.array([o["fwd_ret"] for o in obs if o["direction"] > 0])
    dn = np.array([o["fwd_ret"] for o in obs if o["direction"] < 0])
    fl = np.array([o["fwd_ret"] for o in obs if o["direction"] == 0])
    print(f"\n  UP-guidance   n={len(up):4d}  mean fwd {up.mean()*100:+6.2f}%  median {np.median(up)*100:+6.2f}%"
          if len(up) else "  UP-guidance   n=0")
    print(f"  DOWN-guidance n={len(dn):4d}  mean fwd {dn.mean()*100:+6.2f}%  median {np.median(dn)*100:+6.2f}%"
          if len(dn) else "  DOWN-guidance n=0")
    print(f"  FLAT/mixed    n={len(fl):4d}  mean fwd {fl.mean()*100:+6.2f}%"
          if len(fl) else "  FLAT/mixed    n=0")

    spread = (up.mean() - dn.mean()) if (len(up) and len(dn)) else None
    t = _welch_t(up, dn) if (len(up) >= 2 and len(dn) >= 2) else None
    print("\n  " + "-" * 50)
    if spread is not None:
        print(f"  UP - DOWN forward-return spread: {spread*100:+.2f}%  "
              f"(t = {t:+.2f})" if t is not None else f"  spread {spread*100:+.2f}%")
        passed = (spread > 0) and (t is not None and t > 2.0)
        print(f"\n  VERDICT: {'PASS — guidance direction carries forward return (proceed to gate B).' if passed else 'FAIL/WEAK — direction does NOT cleanly predict; do NOT ship as a return engine (keep it an avoid-tape/overlay).'}")
    else:
        print("  Not enough UP and DOWN observations to compute a spread yet.")
    print("=" * 72)


def _peek(obs) -> None:
    if not obs:
        print("  (no observations — extract some concalls first)")
        return
    print("  current observations (smoke check):")
    for o in sorted(obs, key=lambda x: (x["symbol"], x["period"])):
        d = {1: "UP", -1: "DOWN", 0: "flat"}[o["direction"]]
        print(f"    {o['symbol']:11s} {o['period']:9s} dir={d:4s} fwd={o['fwd_ret']*100:+6.2f}%")


if __name__ == "__main__":
    main()
