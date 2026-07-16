"""Backtest metrics + baselines.

Primary acceptance metric is Calmar/MAR (CAGR / |MaxDD|). We also report return/vol,
Sortino, profit factor, realized hit rate, expectancy-in-R (from the fill-level sim,
NOT arithmetic on MFE/MAE means), MFE-capture efficiency, by-year P&L, and — for the
alpha-vs-beta gate — the strategy's beta/alpha vs Nifty plus buy-and-hold baselines.

equity_stats() emits mean/sd annualised under the `retvol` key with NO risk-free rate
subtracted — a return/vol ratio, not a Sharpe, and it reads high against a textbook one;
`sortino` carries the same defect (no rf/MAR subtracted). Every consumer of these keys
inherits the caveat. A true Sharpe needs a primary-source rf ingest (Guardrail #8), queued
with the TR-benchmark re-cut. (D142)
"""
from __future__ import annotations

from datetime import date
import numpy as np

from .common import main_conn

TD = 252


def _years(d0: str, d1: str) -> float:
    a, b = date.fromisoformat(d0), date.fromisoformat(d1)
    return max((b - a).days / 365.25, 1e-9)


def equity_stats(dates, equity) -> dict:
    if len(equity) < 2:
        return {"cagr": 0, "maxdd": 0, "calmar": 0, "retvol": 0, "sortino": 0,
                "total_ret": 0, "ndays": len(equity)}
    eq = np.asarray(equity, float)
    ret = eq[1:] / eq[:-1] - 1.0
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    maxdd = float(dd.min())
    yrs = _years(dates[0], dates[-1])
    total = float(eq[-1] / eq[0] - 1.0)
    cagr = float((eq[-1] / eq[0]) ** (1.0 / yrs) - 1.0)
    sd = float(ret.std())
    dn = ret[ret < 0]
    dsd = float(dn.std()) if len(dn) else np.nan
    retvol = float(ret.mean() / sd * np.sqrt(TD)) if sd > 0 else 0.0
    sortino = float(ret.mean() / dsd * np.sqrt(TD)) if dsd and dsd > 0 else 0.0
    return {"cagr": cagr, "maxdd": maxdd, "calmar": cagr / abs(maxdd) if maxdd < 0 else 0.0,
            "retvol": retvol, "sortino": sortino, "total_ret": total, "ndays": len(eq),
            "years": yrs}


def trade_stats(taken) -> dict:
    """Per-trade stats over the TAKEN trades (list of (trade, weight))."""
    trs = [t for t, _ in taken]
    if not trs:
        return {"n": 0, "hit": 0, "exp_R": 0, "pf": 0, "avg_win_R": 0, "avg_loss_R": 0,
                "avg_bars": 0, "mfe_capture": 0}
    nr = np.array([t["net_ret"] for t in trs])
    rm = np.array([t["r_multiple"] for t in trs])
    mfe = np.array([t["mfe"] for t in trs])
    wins, losses = nr[nr > 0], nr[nr <= 0]
    pf = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")
    cap = nr[(nr > 0) & (mfe > 0)] / mfe[(nr > 0) & (mfe > 0)]
    return {
        "n": len(trs), "hit": float((nr > 0).mean()), "exp_R": float(rm.mean()),
        "exp_ret": float(nr.mean()), "pf": pf,
        "avg_win_R": float(rm[nr > 0].mean()) if (nr > 0).any() else 0.0,
        "avg_loss_R": float(rm[nr <= 0].mean()) if (nr <= 0).any() else 0.0,
        "avg_bars": float(np.mean([t["bars"] for t in trs])),
        "mfe_capture": float(np.mean(cap)) if len(cap) else 0.0,
        "reasons": {r: int(sum(1 for t in trs if t["reason"] == r))
                    for r in set(t["reason"] for t in trs)},
    }


def by_year(taken) -> dict:
    """Mean net return and count of taken trades by entry year (sanity, not equity)."""
    trs = [t for t, _ in taken]
    yrs = {}
    for t in trs:
        y = t["entry_date"][:4]
        yrs.setdefault(y, []).append(t["net_ret"])
    return {y: {"n": len(v), "avg_ret": float(np.mean(v)), "hit": float(np.mean(np.array(v) > 0))}
            for y, v in sorted(yrs.items())}


def index_series(name="Nifty 50"):
    mc = main_conn()
    rows = mc.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name=? ORDER BY trade_date",
        (name,)).fetchall()
    mc.close()
    return [r[0] for r in rows], np.array([float(r[1]) for r in rows])


def buy_hold(name, d0, d1) -> dict:
    dts, cl = index_series(name)
    idx = [i for i, d in enumerate(dts) if d0 <= d <= d1]
    if len(idx) < 2:
        return {}
    sub_d = [dts[i] for i in idx]
    sub_c = cl[idx]
    st = equity_stats(sub_d, sub_c / sub_c[0])
    st["index"] = name
    return st


def alpha_beta(dates, port_ret, index_name="Nifty 50") -> dict:
    """Daily beta/alpha of the strategy vs an index over the matching dates."""
    dts, cl = index_series(index_name)
    iret = {dts[i]: cl[i] / cl[i - 1] - 1.0 for i in range(1, len(dts))}
    xs, ys = [], []
    for i in range(1, len(dates)):
        d = dates[i]
        if d in iret:
            xs.append(iret[d]); ys.append(port_ret[i])
    if len(xs) < 30:
        return {"beta": np.nan, "alpha_ann": np.nan, "corr": np.nan}
    x, y = np.array(xs), np.array(ys)
    var = x.var()
    beta = float(np.cov(x, y)[0, 1] / var) if var > 0 else np.nan
    alpha_d = float(y.mean() - beta * x.mean())
    corr = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else np.nan
    return {"beta": beta, "alpha_ann": alpha_d * TD, "corr": corr}


def correlation(dates_a, ret_a, dates_b, ret_b) -> float:
    """60d-overlap-agnostic daily correlation between two strategy return streams."""
    ma = {d: ret_a[i] for i, d in enumerate(dates_a)}
    xs, ys = [], []
    for i, d in enumerate(dates_b):
        if d in ma:
            xs.append(ma[d]); ys.append(ret_b[i])
    if len(xs) < 30:
        return np.nan
    x, y = np.array(xs), np.array(ys)
    return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else np.nan


def full_report(name, port, taken=None) -> dict:
    taken = taken if taken is not None else port["taken"]
    dates, equity = port["dates"], port["equity"]
    es = equity_stats(dates, equity) if len(dates) else {}
    ts = trade_stats(taken)
    rep = {"strategy": name, **{f"eq_{k}": v for k, v in es.items()},
           **{f"tr_{k}": v for k, v in ts.items() if k != "reasons"},
           "reasons": ts.get("reasons", {}),
           "n_signals": port.get("n_signals", 0), "n_taken": port.get("n_taken", 0),
           "skipped_regime": port.get("skipped_regime", 0),
           "skipped_heat": port.get("skipped_heat", 0),
           "skipped_dup": port.get("skipped_dup", 0)}
    if len(dates):
        rep["window"] = (dates[0], dates[-1])
        rep["alpha_beta_nifty"] = alpha_beta(dates, port["port_ret"], "Nifty 50")
    return rep
