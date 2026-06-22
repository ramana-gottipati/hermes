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

Read-only. Controls are best-effort point-in-time from the bhav archive; ROCE/debt
are the latest fundamentals snapshot (a known limitation until a point-in-time
fundamentals history exists — noted in the output).
"""

from __future__ import annotations

from bisect import bisect_left

import numpy as np

from research.cci.common import (main_conn, gather_observations, load_series,
                                 insufficient, MIN_OBS)


def _controls(con, o, series_cache) -> dict | None:
    """Point-in-time-ish control factors at the observation's anchor date."""
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
    return {"size": size, "momentum": mom, "pead": pead}


def _fundamentals(con, syms) -> dict:
    out = {}
    try:
        ph = ",".join("?" * len(syms))
        for r in con.execute(
                f"SELECT symbol, roce, debt_to_equity FROM fundamentals WHERE symbol IN ({ph})", list(syms)):
            out[r["symbol"]] = {"roce": r["roce"], "de": r["debt_to_equity"]}
    except Exception:
        pass
    return out


def main() -> None:
    print("=" * 72)
    print("CCI GATE B — credibility's INCREMENTAL alpha (orthogonalised, Newey-West)")
    print("  fwd_ret ~ credibility + ROCE + debt + size + 12-1 momentum + PEAD")
    print("=" * 72)
    with main_conn() as con:
        obs = gather_observations(con)
        fund = _fundamentals(con, {o["symbol"] for o in obs})
        cache: dict = {}
        rows = []
        for o in obs:
            if o["composite"] is None:
                continue
            c = _controls(con, o, cache)
            if c is None:
                continue
            f = fund.get(o["symbol"], {})
            rows.append({"y": o["fwd_ret"], "cred": o["composite"],
                         "roce": f.get("roce"), "de": f.get("de"), **c})
    n = len(rows)
    print(f"  usable observations (have credibility + controls + forward window): {n}")
    if n < MIN_OBS:
        insufficient(n)
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
    print("  NOTE: ROCE/debt are the latest fundamentals snapshot, not point-in-time;")
    print("  credibility is the per-symbol composite (per-period scoring is a later refinement).")
    print("=" * 72)


if __name__ == "__main__":
    main()
