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


def _approx_anchor_date(year, month) -> Optional[str]:
    """Approximate concall date = the 15th of the concall month (the precise
    concall_dt three-clock model is deferred — debate #4). 'YYYY-MM-15' or None."""
    if not year or not month:
        return None
    return f"{int(year):04d}-{int(month):02d}-15"


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


def gather_observations(con) -> list[dict]:
    """One observation per EXTRACTED concall (a distinct symbol+source_period in
    concall_guidance): its guidance direction, the credibility signals available
    as-of, and the survivorship-safe forward return. The unit the gates analyse."""
    periods = con.execute(
        "SELECT DISTINCT g.symbol, g.source_period, c.concall_year, c.concall_month "
        "FROM concall_guidance g "
        "JOIN concalls c ON c.symbol=g.symbol AND c.period_label=g.source_period").fetchall()
    # latest credibility composite per symbol (a coarse as-of proxy until per-period
    # scoring lands; fine for the cheap gate — it never enters as look-ahead because
    # the forward return is measured strictly after the call date).
    sc = {r["symbol"]: dict(r) for r in con.execute(
        "SELECT s.* FROM concall_scores s JOIN "
        "(SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x "
        "ON x.symbol=s.symbol AND x.m=s.last_updated").fetchall()}
    series_cache: dict[str, object] = {}
    out: list[dict] = []
    for p in periods:
        sym = p["symbol"]
        anchor = _approx_anchor_date(p["concall_year"], p["concall_month"])
        if not anchor:
            continue
        if sym not in series_cache:
            series_cache[sym] = load_series(con, sym)
        fr = forward_return(series_cache[sym], anchor)
        if fr is None:
            continue
        s = sc.get(sym, {})
        out.append({
            "symbol": sym, "period": p["source_period"], "anchor": anchor,
            "direction": period_direction(con, sym, p["source_period"]),
            "fwd_ret": fr,
            "composite": s.get("composite_score"),
            "quantification": s.get("quantification_rate"),
            "guidance_acc": s.get("guidance_accuracy_score"),
            "deterioration": s.get("deterioration_score") or 0,
            "veto": s.get("veto_active") or 0,
        })
    return out


def insufficient(n: int) -> None:
    """Print the standard 'gate built, awaiting data' message (the cron drains the
    extraction backfill at 18/day)."""
    print(f"\n  ⏳ INSUFFICIENT DATA — {n} observation(s), need >= {MIN_OBS}.")
    print("  The gate is BUILT and ready; the verdict awaits the extraction backfill.")
    print("  hermes-concalls.timer drains ~18 concalls/day oldest-first; re-run this")
    print("  gate once >= 40 concalls across the golden set have been extracted.\n")
