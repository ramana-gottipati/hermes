"""CCI falsification GATE B — does credibility have INCREMENTAL alpha?

The decisive kill-or-save test (debate rank #2b / NEXT-SESSION P6, design §13). A
raw credibility rank just re-prints the quality factor (Pidilite / Asian Paints),
which is already arbitraged. The only thing worth shipping standalone is credibility
alpha that SURVIVES orthogonalisation against the known factors:

    forward_return ~ credibility + quality(ROCE, debt) + size + 12-1 momentum + PEAD

estimated with Newey-West (HAC) standard errors (overlapping windows + cross-
sectional clustering inflate naive t-stats). If the credibility coefficient is NOT
significant after these controls -> there is no incremental edge -> **MERGE CCI
into pt14, do NOT ship a standalone book** (the debate's explicit decision rule).

Needs statsmodels in the research venv:
    /opt/hermes/.venv-research/bin/pip install statsmodels
    /opt/hermes/.venv-research/bin/python -m research.cci.gate_residual_alpha

Read-only. Price/size/momentum/PEAD controls are point-in-time from the bhav
archive; ROCE/debt are POINT-IN-TIME from fundamentals_history (report_date <= the
anchor — the `latest_known` pattern, fixing CL-RES-02). The credibility regressor is
the leak-free per-period AS-OF composite from the precomputed `credibility_series`
(cci_series.py: composite restricted to promises resolved on/before each anchor, no
look-ahead). If that series is unbuilt the gate renders UNSCORED (CL-RES-01) rather
than fall back to the latest snapshot composite, which would embed the future.
"""

from __future__ import annotations

import sqlite3
from bisect import bisect_left

import numpy as np

from research.cci.common import (main_conn, gather_observations, load_series,
                                 unscored_credibility, MIN_OBS, MIN_RESOLVED_ASOF)
from research.explosive_moves.common import RESEARCH_DB


# --- PIT fundamentals (CL-RES-02) ------------------------------------------
# ROCE / debt-to-equity must be known AS OF the anchor, not the latest snapshot, or
# a 2021 forward return gets orthogonalised against 2026 quality → the credibility
# coefficient is biased by look-ahead. Read fundamentals_history with report_date <=
# anchor (the same `latest_known` join factor_zoo uses). debt/equity is derived from
# Borrowings / (Equity Capital + Reserves) exactly as factor_zoo.fundamentals does.
#
# NOTE: fundamentals_history lives in research.db (NOT the production hermes.db that
# main_conn() opens) — same as factor_zoo, which reads it from RESEARCH_DB. So we open
# a dedicated read-only connection to it here rather than using the production conn.
_ROCE = ("ROCE %", "Financing Margin %")
_BORROW = ("Borrowings", "Borrowing")

_FUND_CON: sqlite3.Connection | None = None
_FUND_UNAVAILABLE = False


def _fund_con() -> sqlite3.Connection | None:
    """Cached read-only connection to research.db (where fundamentals_history lives).
    Returns None if that DB / table is unavailable (the gate then has no PIT quality
    controls, and says so — it does NOT silently fall back to a non-PIT snapshot)."""
    global _FUND_CON, _FUND_UNAVAILABLE
    if _FUND_UNAVAILABLE:
        return None
    if _FUND_CON is None:
        try:
            con = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
            con.row_factory = sqlite3.Row
            con.execute("SELECT 1 FROM fundamentals_history LIMIT 1")   # probe table presence
            _FUND_CON = con
        except Exception:
            _FUND_UNAVAILABLE = True
            return None
    return _FUND_CON


def _load_fund_frame(sym) -> dict:
    """All PIT fundamentals rows for one symbol: {(period_type, metric): [(period_end,
    report_date, value), ...]}. Empty dict if research.db / the table is absent."""
    con = _fund_con()
    if con is None:
        return {}
    fr: dict = {}
    try:
        for r in con.execute(
                "SELECT period_type, metric, period_end, report_date, value "
                "FROM fundamentals_history WHERE symbol=? AND value IS NOT NULL", (sym,)):
            fr.setdefault((r["period_type"], r["metric"]), []).append(
                (r["period_end"], r["report_date"], r["value"]))
    except Exception:
        return {}
    return fr


def _latest_known(fr, pt, names, asof):
    """Most-recent value (by period_end) among rows whose report_date <= asof — the
    point-in-time `latest_known` pattern (identical to factor_zoo.latest)."""
    for nm in (names if isinstance(names, tuple) else (names,)):
        vals = [(pe, v) for (pe, rd, v) in fr.get((pt, nm), []) if rd and rd <= asof]
        if vals:
            return max(vals, key=lambda t: t[0])[1]
    return None


def _pit_fundamentals(fr, asof) -> dict:
    """ROCE + debt/equity knowable strictly as-of `asof` (anchor date)."""
    roce = _latest_known(fr, "A", _ROCE, asof)
    borrow = _latest_known(fr, "A", _BORROW, asof)
    eqc = _latest_known(fr, "A", "Equity Capital", asof)
    res = _latest_known(fr, "A", "Reserves", asof)
    nw = (eqc + res) if (eqc is not None and res is not None) else None
    de = (borrow / nw) if (borrow is not None and nw and nw > 0) else None
    return {"roce": roce, "de": de}


def _controls(con, o, series_cache, fund_cache) -> dict | None:
    """Point-in-time control factors at the observation's anchor date (price-based
    size/momentum/PEAD from the bhav archive + PIT ROCE/debt from fundamentals_history)."""
    sym = o["symbol"]
    if sym not in series_cache:
        series_cache[sym] = load_series(con, sym)
    s = series_cache[sym]
    if s is None:
        return None
    i = bisect_left(s.date, o["anchor"])
    if i <= 252 or i >= s.n:
        return None
    # size = log trailing median turnover (₹); momentum = 12-1 (t-252..t-21);
    # PEAD proxy = the 21d drift into the call (the just-reported quarter's reaction).
    size = np.log(s.med_turn[i]) if (i < len(s.med_turn) and s.med_turn[i] and s.med_turn[i] > 0) else np.nan
    p_252, p_21, p_now = s.adj_close[i - 252], s.adj_close[i - 21], s.adj_close[i]
    mom = (p_21 / p_252 - 1.0) if (p_252 and p_21 and p_252 > 0) else np.nan
    pead = (p_now / p_21 - 1.0) if (p_21 and p_now and p_21 > 0) else np.nan
    if sym not in fund_cache:
        fund_cache[sym] = _load_fund_frame(sym)
    f = _pit_fundamentals(fund_cache[sym], o["anchor"])    # report_date <= anchor
    return {"size": size, "momentum": mom, "pead": pead, "roce": f["roce"], "de": f["de"]}


def main() -> None:
    print("=" * 72)
    print("CCI GATE B — credibility's INCREMENTAL alpha (orthogonalised, Newey-West)")
    print("  fwd_ret ~ credibility + ROCE + debt + size + 12-1 momentum + PEAD")
    print("=" * 72)
    with main_conn() as con:
        obs = gather_observations(con)
        # CL-RES-01: the credibility regressor is admitted ONLY from a leak-free
        # per-period as-of score. If none is available, the gate must render UNSCORED
        # (not PASS / not FAIL) — a forward-leaking regressor can fake a PASS.
        n_with_cred = sum(1 for o in obs if o.get("credibility_asof_available")
                          and o.get("composite") is not None)
        if n_with_cred == 0:
            unscored_credibility(len(obs), n_with_cred)
            print("=" * 72)
            return
        scache: dict = {}
        fcache: dict = {}
        rows = []
        for o in obs:
            if not (o.get("credibility_asof_available") and o.get("composite") is not None):
                continue
            c = _controls(con, o, scache, fcache)        # PIT controls incl. ROCE/debt
            if c is None:
                continue
            rows.append({"y": o["fwd_ret"], "cred": o["composite"], **c})
    n = len(rows)
    print(f"  usable observations (have AS-OF credibility + PIT controls + forward window): {n}")
    print(f"  credibility regressor: PIT credibility_series.level (as-of composite, >= {MIN_RESOLVED_ASOF} "
          f"promises settled by the anchor; leak-free — CL-RES-01).")
    if n:
        n_roce = sum(1 for r in rows if r.get("roce") is not None)
        if _FUND_UNAVAILABLE:
            print("  ⚠ PIT controls: research.db/fundamentals_history unavailable — ROCE/debt OMITTED")
            print("    (the gate does NOT substitute a non-point-in-time snapshot; CL-RES-02).")
        else:
            print(f"  PIT controls: ROCE knowable as-of-anchor on {n_roce}/{n} obs (report_date <= anchor).")
    if n < MIN_OBS:
        unscored_credibility(len(obs), n)
        print("=" * 72)
        return

    try:
        import statsmodels.api as sm
    except ImportError:
        print("\n  statsmodels not installed in this venv. Install then re-run:")
        print("    /opt/hermes/.venv-research/bin/pip install statsmodels\n")
        return

    # Build the design matrix, dropping any control that is all-NaN / zero-variance
    # (so a thin pilot still estimates the credibility coefficient against whatever
    # controls have signal). credibility is ALWAYS retained — it is the test.
    y = np.array([r["y"] for r in rows], dtype=float)
    candidates = ["cred", "roce", "de", "size", "momentum", "pead"]
    cols, names = [], []
    for c in candidates:
        v = np.array([r[c] if r[c] is not None else np.nan for r in rows], dtype=float)
        if np.isnan(v).all():
            continue
        v = np.where(np.isnan(v), np.nanmean(v), v)        # mean-impute the rest
        if c != "cred" and np.nanstd(v) == 0:
            continue
        cols.append(v); names.append(c)
    if "cred" not in names:
        print("  credibility column has no variance — cannot test. (Need scored names.)")
        return
    X = sm.add_constant(np.column_stack(cols))
    model = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": max(1, int(round(n ** 0.25)))})
    labels = ["const"] + names
    print("\n  coef (Newey-West HAC):")
    for lab, b, t, p in zip(labels, model.params, model.tvalues, model.pvalues):
        star = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
        print(f"    {lab:10s} {b:+10.5f}  t={t:+6.2f}  p={p:0.3f} {star}")
    ci = labels.index("cred")
    cred_t, cred_p = model.tvalues[ci], model.pvalues[ci]
    print(f"\n  R² = {model.rsquared:.3f}   n = {n}")
    passed = (cred_p < 0.05) and (model.params[ci] > 0)
    print("  " + "-" * 50)
    print(f"  VERDICT: {'PASS — credibility carries INCREMENTAL alpha after controls -> a standalone book is defensible.' if passed else 'FAIL — no incremental alpha after quality+momentum+PEAD -> MERGE CCI into pt14, do NOT ship a standalone book (debate decision rule).'}")
    print("  NOTE: ROCE/debt are POINT-IN-TIME (fundamentals_history, report_date <= anchor;")
    print("  CL-RES-02). credibility is a leak-free per-period AS-OF score (CL-RES-01).")
    print("=" * 72)


if __name__ == "__main__":
    main()
