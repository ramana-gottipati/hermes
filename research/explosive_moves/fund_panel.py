"""Track B — point-in-time FUNDAMENTAL panel: the patearn score AS-OF every monthly
rebalance, joined to SURVIVORSHIP-AWARE forward returns.

Answers the headline question — *does the rule-based patearn score predict forward returns,
with no look-ahead?* — and gives the backtest a clean fundamental factor.

For each liquid (symbol, month) since 2012-06, it computes the patearn score from the historical
Screener archive AS OF that date (research.db.fundamentals_history via fundamentals_asof —
report_date <= date, so a result is used only after it was filed), attaches forward 1/3/6/12m
returns, and writes research.db.fund_panel. Same calendar as panel_build (ml_panel) so the two
panels JOIN on (symbol, date).

SURVIVORSHIP: a delisted/long-suspended name (its last bar is >45 calendar days before the global
data-end) realizes its return-to-last-traded-price when the horizon runs past its death — instead
of the window silently truncating to NULL and dropping the blow-up. A name that is simply at the
right edge of the data (still trading, 12m not yet elapsed) stays NULL (genuinely unobservable).
Without this, low-quality buckets look artificially good (their failures vanish).

Valuation: PE/PB use the RAW close at the date (not back-adjusted) so the ratio is right in its own
period; forward returns use adj_close (split/bonus-clean). Liquidity floor is ₹5cr median turnover
(investable mid-caps — patearn's universe), overridable via EM_PANEL_LIQ.

Run:  cd /opt/hermes/research && PYTHONPATH=/opt/hermes python -m explosive_moves.fund_panel [limit]
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

# Make BOTH the research package and the production src/ importable, however launched.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.environ.get("HERMES_ROOT", "/opt/hermes"), os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np

from explosive_moves.common import (
    RESEARCH_DB, WARMUP_ROWS,
    eq_symbols, load_series, main_conn, research_conn,
)
from explosive_moves.metrics import index_series
from src.automation.fundamentals_asof import load_symbol_history, load_shareholding_history, as_of_from_frame
from src.automation.scoring import score_fundamentals

REBAL_STEP = 22                                          # ~monthly, matches panel_build (ml_panel)
START = "2012-06-01"
HORIZONS = [22, 66, 132, 252]                            # forward 1m / 3m / 6m / 12m (trading days)
PANEL_LIQ = float(os.environ.get("EM_PANEL_LIQ", 5e7))   # ₹5cr median turnover — investable universe
DEAD_GAP_DAYS = 45                                       # last bar this far before data-end ⇒ delisted/dead

COLS = [
    "symbol", "date", "as_of_period_end", "price",
    "ns_base", "ns_pess", "ns_opt", "pac", "qg_pass", "hard_disq", "tier",
    "roce", "opm", "de", "roce_rising", "opm_trend", "sales_g3", "profit_g3",
    "profit_gttm", "icov", "debtor_days", "ccc", "profit_accel", "pe", "pb",
    "fwd_22", "fwd_66", "fwd_132", "fwd_252",
]
_TEXT = {"symbol", "date", "as_of_period_end", "tier"}


def _f(x):
    return float(x) if x is not None else None


def _b(x):
    return None if x is None else (1 if x else 0)


def _fwd_returns(ac, i0, n, is_dead):
    """Survivorship-aware forward returns at each horizon. Returns (values, n_censored)."""
    base = ac[i0]
    if not (base > 0):
        return [None] * len(HORIZONS), 0
    last_ret = float(ac[-1] / base - 1.0) if ac[-1] == ac[-1] else None   # return to last traded price
    out, cens = [], 0
    for h in HORIZONS:
        j = i0 + h
        if j < n and ac[j] == ac[j]:
            out.append(float(ac[j] / base - 1.0))             # observed full horizon
        elif is_dead and last_ret is not None:
            out.append(max(last_ret, -1.0))                   # delisted before horizon → realized outcome
            cens += 1
        else:
            out.append(None)                                   # right edge — not yet observable
    return out, cens


def build(limit=None):
    mc = main_conn()
    syms = eq_symbols(mc)
    if limit:
        syms = syms[:limit]

    data_end = mc.execute("SELECT max(trade_date) FROM bhavcopy_rows").fetchone()[0]
    dead_cutoff = (date.fromisoformat(data_end) - timedelta(days=DEAD_GAP_DAYS)).isoformat()

    dts, _ = index_series("Nifty 50")
    rebal = sorted(set([d for d in dts if d >= START][::REBAL_STEP]))
    print(f"{len(syms)} symbols, {len(rebal)} rebalances {rebal[0]}..{rebal[-1]}, "
          f"data_end={data_end}, liq>=Rs{PANEL_LIQ/1e7:.0f}cr", flush=True)

    rc = research_conn()
    rc.execute("DROP TABLE IF EXISTS fund_panel")
    rc.execute("CREATE TABLE fund_panel (%s, PRIMARY KEY(symbol,date))" %
               ",".join(c + (" TEXT" if c in _TEXT else " REAL") for c in COLS))
    placeholders = ",".join("?" for _ in COLS)

    summ = []          # (tier, ns_base, fwd_252, fwd_66)
    n = n_cens = 0
    for k, sym in enumerate(syms):
        ss = load_series(mc, sym)
        if ss is None or ss.n < WARMUP_ROWS + 5:
            continue
        frame = load_symbol_history(sym, db_path=RESEARCH_DB)
        if not frame:
            continue
        sh = load_shareholding_history(sym, db_path=RESEARCH_DB)
        is_dead = ss.date[-1] < dead_cutoff
        d2i = {d: i for i, d in enumerate(ss.date)}
        ac = ss.adj_close
        buf = []
        for d0 in rebal:
            i0 = d2i.get(d0)
            if i0 is None or i0 < WARMUP_ROWS:
                continue
            if not (ss.med_turn[i0] >= PANEL_LIQ):           # investable only (NaN → skip)
                continue
            price = float(ss.close[i0]) if ss.close[i0] == ss.close[i0] else None
            f = as_of_from_frame(frame, d0, symbol=sym, price=price, sh=sh)
            if not f:                                         # nothing filed by this date
                continue
            s = score_fundamentals(f)
            fwd, cens = _fwd_returns(ac, i0, ss.n, is_dead)
            n_cens += cens
            buf.append([
                sym, d0, f["as_of_period_end"], price,
                _f(s["ns_base"]), _f(s["ns_pessimistic"]), _f(s["ns_optimistic"]),
                s["pac"], _b(s["qg_pass"]), _b(s["hard_disqualified"]), s["tier"],
                _f(f["roce"]), _f(f["opm_latest"]), _f(f["debt_to_equity"]),
                _b(f["roce_rising_3y"]), _f(f["opm_trend_3y"]), _f(f["sales_growth_3y"]),
                _f(f["profit_growth_3y"]), _f(f["profit_growth_ttm"]), _f(f["interest_coverage"]),
                _f(f["debtor_days"]), _f(f["cash_conversion_cycle"]), _f(f["profit_accel_ttm"]),
                _f(f["pe"]), _f(f["pb"]),
                fwd[0], fwd[1], fwd[2], fwd[3],
            ])
            summ.append((s["tier"], s["ns_base"], fwd[3], fwd[1]))
        if buf:
            rc.executemany(f"INSERT OR REPLACE INTO fund_panel VALUES ({placeholders})", buf)
            rc.commit()
            n += len(buf)
        if (k + 1) % 200 == 0:
            print(f"  {k+1}/{len(syms)} syms, {n} rows, {n_cens} delisting-censored recovered", flush=True)

    mc.close()
    rc.close()
    print(f"DONE. fund_panel rows={n}, delisting-censored fwd returns recovered={n_cens}")
    _summary(summ)


def _bucket_stats(vals):
    a = np.array([v for v in vals if v is not None], dtype=float)
    if len(a) == 0:
        return None
    return {"n": len(a), "med": float(np.median(a)) * 100, "mean": float(np.mean(a)) * 100,
            "hit": float((a > 0).mean()) * 100, "blow": float((a < -0.5).mean()) * 100}


def _row(label, st):
    return f"{label:20}{st['n']:>7}{st['med']:>9.1f}%{st['hit']:>7.0f}%{st['blow']:>8.0f}%{st['mean']:>9.1f}%"


def _summary(summ):
    """Honest read-out: median / hit-rate / blow-up rate / mean — not just mean."""
    if not summ:
        print("no rows — nothing to summarize"); return
    hdr = f"{'bucket':20}{'n':>7}{'med12m':>10}{'hit%':>7}{'blow%':>8}{'mean12m':>10}"

    print("\n=== forward 12m by patearn TIER (survivorship-aware, no look-ahead) ===")
    print(hdr)
    for t in ("T1", "T2", "T3", "T4", "DISQUALIFIED"):
        st = _bucket_stats([x[2] for x in summ if x[0] == t])
        if st:
            print(_row(t, st))

    pairs = [(x[1], x[2]) for x in summ if x[1] is not None and x[2] is not None]
    if len(pairs) > 50:
        ns = np.array([p[0] for p in pairs])
        fr = np.array([p[1] for p in pairs])
        qs = np.quantile(ns, [0, .2, .4, .6, .8, 1.0])
        print("\n=== forward 12m by patearn-NS quintile ===")
        print(hdr)
        q_meds = []
        for i in range(5):
            lo, hi = qs[i], qs[i + 1]
            m = (ns >= lo) & (ns <= hi) if i == 4 else (ns >= lo) & (ns < hi)
            st = _bucket_stats(list(fr[m]))
            if st:
                q_meds.append(st["med"])
                print(_row(f"Q{i+1} NS[{lo:4.0f},{hi:4.0f}]", st))
        if len(q_meds) == 5:
            print(f"\nlong-short (Q5−Q1) median 12m spread: {q_meds[-1] - q_meds[0]:+.1f} pts "
                  f"(positive ⇒ higher patearn score → higher return)")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    build(limit=lim)
