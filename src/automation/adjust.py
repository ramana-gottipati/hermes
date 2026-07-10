"""Corporate-action (split / bonus) back-adjustment — single source of truth.

This module is the ONE canonical implementation of the split/bonus back-
adjustment that makes a raw bhav-copy close series continuous (the same method
Zerodha uses for its charts). It was first written inline in the dashboard
render (`src/web/dashboard.py`, D36); this module extracts that EXACT two-layer
logic so every consumer — the dashboard chart, RS (D33), and any future
zones-on-adjusted-price recompute — shares one definition.

The dashboard's inline copy can be unified to call `adjusted_closes` later
(open item B5); keep the algorithm here authoritative.

Pure: no DB, no I/O. Caller supplies the rows.

Algorithm (three layers; S85e reconciliation, 2026-07-10):
  - TAPE layer (primary, when the caller passes ``events``): the authoritative
    corporate-actions tape (corp_actions.price_ratios) names the EXACT ex-date +
    ratio. Each tape ratio is TOLERANCE-GATED against the observed close move on
    that date (±_TAPE_TOL relative) so a mis-parsed/mis-dated tape row can never
    corrupt a series — on disagreement the inference layers stand alone.
  - prev_close layer: D36 assumed NSE sets prev_close to the ADJUSTED previous
    close on ex-dates. **MEASURED FALSE on this archive (S85e): across 2004→2026,
    ex-day prev_close carries the RAW prior close — this layer has NEVER fired.**
    Kept (cheap, harmless) in case the bhav format ever starts adjusting it.
  - FALLBACK layer: a single-day close jump > CC_THRESH (a real 30%+ move is
    impossible under circuit limits → always a corporate action). Until S85e this
    was the ONLY working layer — which is why sub-30% actions (a 1:3 bonus ≈
    −25%) were silently missed (112 event-groups / 92 symbols in the full-history
    audit). The tape layer closes that dead zone.
  - Walk BACKWARD from newest to oldest, accumulating the cumulative factor
    `cum`; older closes are scaled by the cumulative factor in force at their
    position so the whole curve is continuous to the latest (unadjusted) close.

``events`` is optional and defaults to None → behavior identical to the legacy
two-layer walk for every existing caller until it opts in.
"""

from typing import Optional

# Thresholds — kept identical to the dashboard's D36 inline values.
PC_THRESH = 0.03   # prev_close flag: real splits/bonuses; normal days ≈ 0%
CC_THRESH = 0.30   # close-jump fallback: >30% single-day move = action NSE
                   # didn't adjust prev_close for (circuit limits make a real
                   # 30%+ daily move impossible, so it's always a corp action)
_TAPE_TOL = 0.18   # tape ratio accepted only when the observed ex-day move agrees
                   # within this relative band (audit: real matches sit ≤ ~10%,
                   # market drift included; suspects/parse errors sit far outside)


def adjustment_factors(rows: list[dict], events: Optional[dict] = None) -> list[float]:
    """Cumulative back-adjustment factor per row, OLDEST→NEWEST.

    `rows` = list of dicts with at least `close` and `prev_close` (and
    `trade_date` when using ``events``), ordered oldest first. Returns a
    parallel list of floats: multiply a row's raw OHLC by its factor to get the
    back-adjusted value. The newest row's factor is always 1.0 (anchor); older
    rows carry the product of every action factor that occurred after them.

    ``events`` (optional): {trade_date: implied_price_ratio} from the
    authoritative corporate-actions tape (corp_actions.price_ratios). A tape
    ratio is applied ONLY when the observed close move on that date agrees
    within ±_TAPE_TOL — the exact ratio then replaces the noisy observed one,
    and sub-CC_THRESH actions (the 3–30% dead zone) stop being missed. On
    disagreement the legacy inference layers decide, unchanged.
    """
    n = len(rows)
    factors = [1.0] * n
    if n < 2:
        return factors
    cum = 1.0
    for i in range(n - 1, 0, -1):
        prior_close = rows[i - 1].get("close")
        this_close = rows[i].get("close")
        pc = rows[i].get("prev_close")
        ratio: Optional[float] = None
        # TAPE layer (authoritative ex-date + exact ratio; tolerance-gated).
        if events:
            tape = events.get(rows[i].get("trade_date"))
            if (tape and 0.02 < tape < 50 and prior_close and this_close
                    and prior_close > 0 and abs(this_close / prior_close / tape - 1) <= _TAPE_TOL):
                ratio = tape
        # prev_close layer (measured never-firing on this archive — kept for safety).
        if ratio is None and pc and prior_close and prior_close > 0:
            r_pc = pc / prior_close
            if abs(r_pc - 1) > PC_THRESH and 0.02 < r_pc < 50:
                ratio = r_pc
        # Fallback: the close gapped hugely — an unadjusted corporate action
        # (PARAS 2025-07-04 style). The only layer that fired before S85e.
        if ratio is None and prior_close and prior_close > 0 and this_close:
            r_cc = this_close / prior_close
            if abs(r_cc - 1) > CC_THRESH and 0.02 < r_cc < 50:
                ratio = r_cc
        if ratio is not None:
            cum *= ratio
        factors[i - 1] = cum
    return factors


def adjusted_closes(rows: list[dict], events: Optional[dict] = None) -> list[Optional[float]]:
    """Back-adjusted close per row, OLDEST→NEWEST.

    `rows` = list of dicts `{trade_date, close, prev_close}` ordered oldest
    first. Returns a parallel list of adjusted-close floats (None where the
    raw close is None). Splits/bonuses no longer fake a cliff; the latest close
    is unchanged (anchor). This is the price RS must use — a raw split would
    otherwise fake a relative-strength collapse. ``events`` as in
    adjustment_factors (tape-primary, tolerance-gated).
    """
    factors = adjustment_factors(rows, events)
    out: list[Optional[float]] = []
    for r, f in zip(rows, factors):
        c = r.get("close")
        out.append(round(c * f, 6) if c is not None else None)
    return out


# ── selftest (offline, synthetic) ────────────────────────────────────────────

def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    def mk(seq):
        rows, prior = [], None
        for d, close in seq:
            rows.append({"trade_date": d, "close": close, "prev_close": prior})
            prior = close
        return rows

    # the CUB class: 1:3 bonus ≈ −25% — inside the dead zone (3% < move < 30%)
    dead = mk([("d1", 100.0), ("d2", 101.0), ("d3", 75.8), ("d4", 76.5)])
    legacy = adjustment_factors(dead)
    check("dead-zone action MISSED without the tape (legacy)", legacy == [1.0] * 4)
    tape = adjustment_factors(dead, events={"d3": 0.75})
    check("tape closes the dead zone (exact ratio applied)",
          abs(tape[0] - 0.75) < 1e-9 and abs(tape[1] - 0.75) < 1e-9 and tape[2] == 1.0 == tape[3])
    # tolerance gate: tape says split, the market says nothing happened → refuse
    flat = mk([("d1", 100.0), ("d2", 101.0), ("d3", 100.5), ("d4", 100.0)])
    check("disagreeing tape ratio REFUSED (gate)",
          adjustment_factors(flat, events={"d3": 0.75}) == [1.0] * 4)
    # >30% jump with NO tape: the legacy fallback still catches it, unchanged
    big = mk([("d1", 100.0), ("d2", 100.0), ("d3", 50.0), ("d4", 51.0)])
    f_big = adjustment_factors(big)
    check("fallback layer unchanged (no-events path identical)",
          abs(f_big[1] - 0.5) < 1e-9 and f_big[2] == 1.0)
    # tape beats the fallback's noisy observed ratio where both apply
    f_both = adjustment_factors(big, events={"d3": 0.5})
    check("tape ratio (exact) preferred over the observed jump", abs(f_both[1] - 0.5) < 1e-9)
    # events=None → byte-identical legacy behavior on a no-action series
    check("None events == legacy", adjustment_factors(flat) == adjustment_factors(flat, events=None))
    check("adjusted_closes threads events",
          adjusted_closes(dead, events={"d3": 0.75})[0] == 75.0)

    print("adjust selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
