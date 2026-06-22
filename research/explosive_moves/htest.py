"""Phase H — flexible hypothesis tester.

Run any boolean precursor condition (pandas-eval syntax over the feature columns,
use & | and parentheses) and get its real-world stats: reweighted hit/lift for a
SUSTAINED +10% month, coverage, and the within-event outcome quality (sustain,
ret66, big50, MFE/MAE) of the matching moves. Lets us confirm/refute the analyst
panel's proposed tests fast.

  python -m explosive_moves.htest "deliv_qty_trend>1.05 & trades_trend>1.10"
  python -m explosive_moves.htest --num "vol_ratio_22_66/deliv_qty_trend"   # distribution compare event vs baseline
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
from .common import research_conn

K = 10.0


def _load():
    rc = research_conn()
    ev = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly'", rc)
    base = pd.read_sql_query("SELECT * FROM features WHERE etype='baseline'", rc)
    for df in (ev, base):
        for c in df.columns:
            if c not in ("symbol", "etype", "launch_date", "year", "move_date",
                         "h_accum_character", "h_rs_vs_broad_trend_state",
                         "h_rs_vs_sector_trend_state", "h_next_p_above", "cpr_pattern", "cpr_regime"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return ev, base


def test_bool(ev, base, expr):
    em = ev.eval(expr); bm = base.eval(expr)
    pos = ev[ev.sustained == 1]
    pm = pos.eval(expr)
    tot_pos, tot_ctrl = len(pos), len(base)
    a = int(pm.sum()); b = int(bm.sum())
    base_rate = tot_pos / (tot_pos + K * tot_ctrl)
    prec = a / (a + K * b) if (a + K * b) > 0 else float("nan")
    sub = ev[em]              # ALL matching events (sustained or not) for quality
    c132 = sub[sub.fwd_complete_132 == 1]
    print(f"\nEXPR: {expr}")
    print(f"  events matching: {int(em.sum())}/{len(ev)} ({100*em.mean():.1f}%) | baseline matching: {100*bm.mean():.1f}%")
    print(f"  SUSTAINED-month  hit={prec:.3f}  lift={prec/base_rate:.2f}  coverage={a/tot_pos:.2f}  (base {base_rate:.3f})")
    if len(sub):
        print(f"  within matching moves: sustain={sub.sustained.mean():.3f}  ret66={sub.ret_66.mean():+.3f}  "
              f"mfe6m={sub.mfe_6m.mean():+.3f}  mae6m={sub.mae_6m.mean():+.3f}  "
              f"big50={c132.big50_6m.mean():.3f}" if len(c132) else "")


def test_num(ev, base, expr):
    e = ev.eval(expr); b = base.eval(expr)
    e = e.replace([np.inf, -np.inf], np.nan).dropna(); b = b.replace([np.inf, -np.inf], np.nan).dropna()
    print(f"\nNUM: {expr}")
    print(f"  event  median={e.median():.3f} mean={e.mean():.3f} p25={e.quantile(.25):.3f} p75={e.quantile(.75):.3f}")
    print(f"  base   median={b.median():.3f} mean={b.mean():.3f} p25={b.quantile(.25):.3f} p75={b.quantile(.75):.3f}")
    print(f"  e/b mean ratio={e.mean()/b.mean():.2f}" if b.mean() else "")
    # within-events: correlation of the derived value with outcomes
    ev2 = ev.copy(); ev2["_x"] = ev.eval(expr).replace([np.inf, -np.inf], np.nan)
    ev2 = ev2.dropna(subset=["_x", "ret_66"])
    if len(ev2) > 100:
        try:
            ev2["_q"] = pd.qcut(ev2["_x"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
            print("  by quartile of the expr (within events): sustain | ret66 | big50")
            print(ev2.groupby("_q", observed=True).agg(n=("ret_66", "size"), sustain=("sustained", "mean"),
                  ret66=("ret_66", "mean"), big50=("big50_6m", "mean")).round(3).to_string())
        except Exception as e:
            print("  (qcut failed)", e)


def main(argv):
    ev, base = _load()
    if argv and argv[0] == "--num":
        for expr in argv[1:]:
            test_num(ev, base, expr)
    else:
        for expr in argv:
            test_bool(ev, base, expr)


if __name__ == "__main__":
    main(sys.argv[1:])
