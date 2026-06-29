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

import sqlite3
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
MIN_RESOLVED_ASOF = 3  # an as-of period counts as a credibility OBSERVATION only with >= this many SETTLED
                       # promises by the anchor. Below it `level` rests on a 1-2 promise track record (a 1/1
                       # "MET" is a spurious 100) — noise that would only attenuate the test, not a credibility
                       # signal. Mirrors the product's "proven" floor and the depth gate cci_backtest already
                       # applies to credibility_series. Local constant (not imported from the production
                       # package) so the research gate stays self-contained — same doctrine as the lexicons.

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


def _per_period_credibility(con) -> dict[tuple[str, str], dict]:
    """As-of credibility keyed on (symbol, source_period) — the ONLY join that is
    free of look-ahead. Reads the precomputed point-in-time series ``credibility_series``
    (built nightly by ``src/automation/cci_series.py``). Returns {} if that table is
    absent/unbuilt, so the gate then renders UNSCORED rather than a leaked verdict.

    CL-RES-01 (the leak this fixes): GATE B originally regressed forward return on the
    *latest* per-symbol composite in ``concall_scores`` (``MAX(last_updated)``), which
    ``score_symbol`` aggregates over a symbol's WHOLE resolved-promise history — incl.
    resolutions that land YEARS after a given anchor. That embeds the future in the
    *regressor* (the in-code "not look-ahead because the return is measured after"
    comment was wrong: the regressor leaks, not the target), and a leaked regressor can
    manufacture a FALSE PASS on a trust-validation gate — the worst possible outcome.

    ``credibility_series`` is the genuine as-of series. For each (symbol, period T) its
    ``level`` is the SAME measurable composite the snapshot scorer uses — cci_series
    imports W_GA/W_QR/UNPROVEN_CEILING/DETER_PEN_PER/_tier/_clamp straight from
    concall_scores — but restricted to what was knowable by T: promises whose resolution
    period is <= T (cci_series counts ``p["res"] <= tym``), quantification of promises
    made by T, deterioration flags seen by T. No resolution AFTER the anchor enters it,
    so it is leak-free by construction. This is exactly the "as-of aggregation (composite
    restricted to promises resolved on/before the anchor)" CL-RES-01 called for.

    We READ that table rather than re-deriving the as-of aggregation inside
    ``concall_scores.score_symbol``: cci_series already materialises precisely this
    (18,944 PIT points / 806 symbols), is validated and nightly-maintained, and is the
    same series ``cci_backtest`` / ``cci_rrg`` / the dossier already consume. A second
    as-of table in the snapshot scorer would be a divergent source of truth for the
    identical quantity (and concall_scores was under concurrent edit — not duplicating
    its aggregation keeps this fix off that contested file).

    Keys are (symbol, period_label); ``period_label`` == ``concall_guidance.source_period``
    for every gate observation (``gather_observations`` joins source_period to
    ``concalls.period_label``, which is what credibility_series is keyed on). Only periods
    with a real SETTLED track record (``n_resolved >= MIN_RESOLVED_ASOF``) are admitted —
    a "credibility" resting on 0-2 resolved promises is not a track record and must not
    enter a credibility-alpha test. The forensic veto is a CURRENT-fundamentals gate
    (pledge / auditor-exit) that is not point-in-time reconstructable, so cci_series
    deliberately omits it from the series and we report ``veto_active=0`` here — correct
    for a PIT regressor (a retro-applied live veto would itself be look-ahead)."""
    try:
        rows = con.execute(
            "SELECT symbol, period_label, level, ga, qr, n_resolved, deter "
            "FROM credibility_series WHERE level IS NOT NULL AND n_resolved >= ?",
            (MIN_RESOLVED_ASOF,)).fetchall()
    except sqlite3.OperationalError:
        return {}        # table not built on this host → gate stays UNSCORED (no leaked fallback)
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        out[(r["symbol"], r["period_label"])] = {
            "composite_score": r["level"],        # the leak-free PIT composite — GATE B's credibility regressor
            "guidance_accuracy_score": r["ga"],
            "quantification_rate": r["qr"],
            "deterioration_score": r["deter"] or 0,
            "veto_active": 0,                      # not PIT-reconstructable; intentionally absent from the series
            "n_resolved": r["n_resolved"],
        }
    return out


def gather_observations(con) -> list[dict]:
    """One observation per EXTRACTED concall (a distinct symbol+source_period in
    concall_guidance): its guidance direction, the credibility signals available
    AS-OF the anchor, and the survivorship-safe forward return. The unit the gates
    analyse.

    ``composite``/``quantification``/… are populated ONLY from the leak-free per-period
    as-of score (see ``_per_period_credibility``, which reads the precomputed
    ``credibility_series``). Where that series has a settled-track-record point for
    (symbol, source_period) the observation carries the PIT composite and
    ``credibility_asof_available=True``; where it does not (no settled track record by
    the anchor, or the series unbuilt) it carries ``composite=None`` and GATE B excludes
    it — rendering UNSCORED only if NONE qualify (CL-RES-01). The guidance DIRECTION and
    forward return are measured purely from the anchor forward, so the guidance gate
    (GATE A) is unaffected either way."""
    periods = con.execute(
        "SELECT DISTINCT g.symbol, g.source_period, c.concall_year, c.concall_month "
        "FROM concall_guidance g "
        "JOIN concalls c ON c.symbol=g.symbol AND c.period_label=g.source_period").fetchall()
    cred = _per_period_credibility(con)        # {} until a PIT per-period score exists
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
    print("  Resolution: build the point-in-time series (it IS the genuine as-of")
    print("  aggregation — composite restricted to promises resolved on/before each")
    print("  anchor) via  python -m src.automation.cci_series --all ; then")
    print("  _per_period_credibility() populates from credibility_series and this lights up.\n")


def insufficient(n: int) -> None:
    """Print the standard 'gate built, awaiting data' message (the cron drains the
    extraction backfill at 18/day)."""
    print(f"\n  ⏳ INSUFFICIENT DATA — {n} observation(s), need >= {MIN_OBS}.")
    print("  The gate is BUILT and ready; the verdict awaits the extraction backfill.")
    print("  hermes-concalls.timer drains ~18 concalls/day oldest-first; re-run this")
    print("  gate once >= 40 concalls across the golden set have been extracted.\n")
