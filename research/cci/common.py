"""CCI falsification-gate shared helpers (offline, READ-ONLY, .venv-research).

The two cheap kill-or-save tests for the Concall-Intelligence strategy (debate
rank #2, design §13 / NEXT-SESSION P6) live beside this file:

  - gate_guidance_return.py   (a) does guidance DIRECTION predict forward return?
  - gate_residual_alpha.py    (b) does credibility have INCREMENTAL alpha after
                                  orthogonalising vs quality + momentum + PEAD?

This module supplies the survivorship-safe plumbing both share, reusing the
explosive-move research layer (same read-only production DB + split-adjusted price
series + corporate-action adjuster — all proven in D56). NOTHING here writes to the
production DB. Run under the isolated research venv:

    /opt/hermes/.venv-research/bin/python -m research.cci.gate_guidance_return
    (gate_residual_alpha additionally needs `pip install statsmodels` in that venv)

DOCTRINE (D61): the gates test MEASURABLE signals only — guidance direction (sign
of the net growth-vs-reduction promises in a call), the credibility composite, the
quantification rate. The 0-100 behaviour axes are never an input.
"""

from __future__ import annotations

import sys
from bisect import bisect_left
from pathlib import Path
from typing import Optional

import numpy as np

# Reuse the explosive-move research plumbing (read-only DB, adjusted SymbolSeries).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.explosive_moves.common import main_conn, load_series  # noqa: E402

# --- gate parameters (debate-aligned) --------------------------------------
ENTRY_LAG = 2          # enter T+2 — skip the immediate concall reaction (three-clock-lite, debate #4)
HORIZON = 63           # ~3 trading months forward
COST_BPS = 60.0        # friction assumption (debate #5: 30-150 bps); subtracted from every forward return
MIN_OBS = 30           # below this the gate refuses to render a verdict (too few to be anything but noise)

# direction lexicons (same spirit as concall_settle / cci_normalize) — keep here so
# the offline gate has zero dependency on the production package being importable.
_UP = ("grow", "growth", "increase", "improv", "expand", "higher", "double", "triple",
       "ramp", "rise", "accelerat", "uptick", "scale up", "step up", "tailwind", "strong")
_DOWN = ("reduce", "decline", "lower", "cut", "delever", "deleverage", "fall", "moderat",
         "soften", "down", "headwind", "weak", "pressure", "slowdown", "de-grow")


def _month_end_anchor(year, month) -> Optional[str]:
    """No-look-ahead anchor for a concall whose exact date is unknown: the LAST day of
    the concall month. The call happened on SOME day in that month; anchoring at the
    15th (the old default) could start the forward window before the call had actually
    occurred — a mild look-ahead (CL-RES-12). Month-end is conservatively late: the call
    is certainly knowable by then, so no future information leaks into the entry.
    'YYYY-MM-DD' (last day) or None."""
    if not year or not month:
        return None
    y, m = int(year), int(month)
    import calendar
    last = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-{last:02d}"


def _anchor_date(concall_date, year, month) -> Optional[str]:
    """The anchor for the forward-return window. Prefer the ACTUAL concall date when the
    `concalls` row carries one (zero look-ahead, exact); otherwise fall back to the
    no-look-ahead month-end approximation. Replaces the old 15th-of-month heuristic,
    which could anchor before the call actually happened (CL-RES-12)."""
    if concall_date:
        s = str(concall_date)[:10]
        # accept a plausible ISO date only; anything else falls through to month-end.
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
    return _month_end_anchor(year, month)


# Back-compat alias (kept so any external caller of the old name still resolves; now
# routes through the no-look-ahead month-end anchor rather than the 15th).
def _approx_anchor_date(year, month) -> Optional[str]:
    return _month_end_anchor(year, month)


def period_direction(con, symbol: str, source_period: str) -> int:
    """Net guidance DIRECTION for one extracted call: +1 (net UP), -1 (net DOWN),
    0 (mixed/none). Counts UP- vs DOWN-keyword promises in concall_guidance —
    measurable + reproducible (no LLM read)."""
    rows = con.execute(
        "SELECT claim_text FROM concall_guidance WHERE symbol=? AND source_period=?",
        (symbol, source_period)).fetchall()
    up = dn = 0
    for r in rows:
        c = (r["claim_text"] or "").lower()
        u, d = any(w in c for w in _UP), any(w in c for w in _DOWN)
        if u and not d:
            up += 1
        elif d and not u:
            dn += 1
    return 1 if up > dn else (-1 if dn > up else 0)


def forward_return(series, anchor_date: str, lag: int = ENTRY_LAG,
                   horizon: int = HORIZON) -> Optional[float]:
    """Split-adjusted forward return entering `lag` trading days after `anchor_date`
    and held `horizon` trading days, net of COST_BPS. None if the window runs off
    the data (no look-ahead beyond what exists; survivorship-safe — delisted names
    simply stop, which is itself the signal)."""
    if series is None or not anchor_date:
        return None
    i = bisect_left(series.date, anchor_date)        # first trading day on/after anchor
    a, b = i + lag, i + lag + horizon
    if a < 0 or b >= series.n:
        return None
    p0, p1 = series.adj_close[a], series.adj_close[b]
    if not (p0 and p1) or np.isnan(p0) or np.isnan(p1) or p0 <= 0:
        return None
    return (p1 / p0 - 1.0) - COST_BPS / 1e4


def _per_period_credibility(con) -> dict[tuple[str, str], dict]:
    """As-of credibility keyed on (symbol, source_period) — the ONLY join that is
    free of look-ahead. Returns {} until a true point-in-time per-period score exists.

    CL-RES-01 (the critical leak): the previous code attached the *latest* composite
    per symbol (``MAX(last_updated)``), which is computed from ALL of a symbol's
    concalls — including resolutions that happen YEARS after a given anchor. Feeding
    that as the regressor in GATE B embeds the future in the predictor (the in-code
    "not look-ahead because the return is measured after" comment was wrong: the
    *regressor* leaks, not the target). A leaked regressor can manufacture a false
    PASS on a trust-validation gate, which is the worst possible outcome.

    The correct fix is to join the credibility score that was knowable AS OF the
    anchor period, on (symbol, source_period). ``concall_scores`` is keyed
    (symbol, as_of_period) and *looks* like such a series, but it is NOT point-in-time:
    ``concall_scores.score_symbol`` aggregates a symbol's WHOLE resolved-promise
    history into every row regardless of ``as_of_period`` (its guidance query has no
    period/resolution-date bound), and it is re-derived nightly. So even an exact
    ``as_of_period == source_period`` row still embeds promises resolved long after
    the anchor. There is therefore NO leak-free per-period score available today.

    Until ``concall_scores`` grows a genuine as-of aggregation (composite restricted
    to promises resolved on/before the anchor), this returns {} and the gate renders
    UNSCORED rather than a leaked verdict. When such a series lands, populate this map
    from it (join on symbol+period, bound by resolution date) and the gates light up
    automatically — no other change needed."""
    return {}


def gather_observations(con) -> list[dict]:
    """One observation per EXTRACTED concall (a distinct symbol+source_period in
    concall_guidance): its guidance direction, the credibility signals available
    AS-OF the anchor, and the survivorship-safe forward return. The unit the gates
    analyse.

    ``composite``/``quantification``/… are populated ONLY from a leak-free per-period
    as-of score (see ``_per_period_credibility``). Today that map is empty, so every
    observation carries ``composite=None`` and ``credibility_asof_available=False`` —
    GATE B must then report UNSCORED, never PASS (CL-RES-01). The guidance DIRECTION
    and forward return are measured purely from the anchor forward, so the guidance
    gate (GATE A) is unaffected."""
    periods = con.execute(
        "SELECT DISTINCT g.symbol, g.source_period, c.concall_year, c.concall_month, "
        "c.concall_date "
        "FROM concall_guidance g "
        "JOIN concalls c ON c.symbol=g.symbol AND c.period_label=g.source_period").fetchall()
    cred = _per_period_credibility(con)        # {} until a PIT per-period score exists
    series_cache: dict[str, object] = {}
    out: list[dict] = []
    for p in periods:
        sym = p["symbol"]
        # CL-RES-12: actual concall_date when present (exact, zero look-ahead); else the
        # no-look-ahead month-end approximation. (was: 15th-of-month, a mild look-ahead.)
        anchor = _anchor_date(p["concall_date"], p["concall_year"], p["concall_month"])
        if not anchor:
            continue
        if sym not in series_cache:
            series_cache[sym] = load_series(con, sym)
        fr = forward_return(series_cache[sym], anchor)
        if fr is None:
            continue
        s = cred.get((sym, p["source_period"]), {})       # as-of score, or {} (no leak)
        out.append({
            "symbol": sym, "period": p["source_period"], "anchor": anchor,
            "direction": period_direction(con, sym, p["source_period"]),
            "fwd_ret": fr,
            # credibility fields come from the as-of join ONLY; None when unavailable.
            "credibility_asof_available": bool(s),
            "composite": s.get("composite_score"),
            "quantification": s.get("quantification_rate"),
            "guidance_acc": s.get("guidance_accuracy_score"),
            "deterioration": s.get("deterioration_score") or 0,
            "veto": s.get("veto_active") or 0,
        })
    return out


def unscored_credibility(n_obs: int, n_with_cred: int) -> None:
    """Standard 'gate cannot render a credibility verdict' message — printed when no
    leak-free per-period as-of credibility is available (CL-RES-01). This is NOT a
    PASS and NOT a FAIL: it is the honest 'underpowered/unscored' state. A false PASS
    on a trust-validation gate is the worst outcome, so the gate stays mute on
    credibility until a point-in-time per-period score exists."""
    print("\n  ⚠ UNSCORED — credibility's incremental-alpha verdict is WITHHELD.")
    print(f"  {n_obs} forward observations formed, but {n_with_cred} carry a leak-free")
    print("  AS-OF (point-in-time, per-period) credibility score — the only regressor")
    print("  that does not embed the future.")
    print("  The per-symbol composite in concall_scores is the LATEST snapshot (it")
    print("  aggregates a symbol's whole resolved-promise history, incl. resolutions")
    print("  AFTER each anchor); regressing forward return on it would leak look-ahead")
    print("  and could manufacture a FALSE PASS. The gate therefore renders no verdict.")
    print("  Resolution: give concall_scores a genuine as-of aggregation (composite")
    print("  restricted to promises resolved on/before the anchor period), then")
    print("  _per_period_credibility() will populate and this gate lights up.\n")


def insufficient(n: int) -> None:
    """Print the standard 'gate built, awaiting data' message (the cron drains the
    extraction backfill at 18/day)."""
    print(f"\n  ⏳ INSUFFICIENT DATA — {n} observation(s), need >= {MIN_OBS}.")
    print("  The gate is BUILT and ready; the verdict awaits the extraction backfill.")
    print("  hermes-concalls.timer drains ~18 concalls/day oldest-first; re-run this")
    print("  gate once >= 40 concalls across the golden set have been extracted.\n")
