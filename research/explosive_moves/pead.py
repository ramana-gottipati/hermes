"""PEAD — post-earnings-announcement drift on REAL BSE result dates, delivery-confirmed.

THE HYPOTHESIS (pre-registered in chat before any data was touched, 2026-07-05): after a
results announcement, abnormal drift [+2, +60 trading days] is (a) increasing in the earnings
surprise (SUE computed WITHOUT analyst estimates — seasonal random walk on Net Profit rupees),
and (b) stronger when the day-0 reaction came on ABNORMAL DELIVERED VALUE (conviction buying,
not intraday churn). Delivery is the India-specific interaction no US PEAD study has.

WHY THIS ISN'T ALREADY IN THE LEDGER: every prior strategy was calendar-time cross-sectional
ranking (monthly rebalance, always invested). This is EVENT-time — episodic capital, measured
per-event and as a Jegadeesh-Titman calendar-time portfolio of active events. DELIV_MOM's
ledger failure (Sharpe 0.42-0.85) was a calendar-time LEVEL; day-0 delivery here is an
event-day INTERACTION — an untested cell.

EVENT DATES — the honesty core: only events whose result-announcement date is the REAL BSE
filing date captured in hermes.db.provenance_knowable (fundamentals_filing_dates.py backfill;
ground-truthed: RELIANCE A|2024-03-31 -> 2024-04-22 = the actual Q4FY24 results day). Modeled
/ calibrated-lag dates are NOT used — date noise attenuates nothing here because misaligned
events are simply excluded. Annual keys ARE Q4-results dates in India (same board meeting).

TWO STUDIES
  A: annual-results events, real dates ~2011->2026 (dense 2015+), SUE over trailing annual
     Net-Profit diffs (24y archive) — long enough for the house walk-forward halves.
  Q: quarterly events, real dates dense 2023->2026, SUE over trailing SEASONAL diffs
     (q vs q-4; archive is ~13 quarters deep, so sigma uses >=3 diffs).
  A Q4-event and an A-event of the same symbol within 5 sessions are deduped (keep Q).

NO-LEAK CONTRACT
  * Event knowable date t0 = MIN(real BSE date) for the key, sanity-lagged 5..200d after
    period_end. day0 = first trading row with date >= t0.
  * Reaction window = [day0, day0+1] (two sessions — covers pre-open and after-close filings
    without intraday timestamps). ENTRY = close of day0+1. Drift = CAR over (entry, entry+60].
  * DESCRIPTIVE tables rank SUE / EAR / delivery within event cohorts (calendar quarter of
    t0) — standard event-study practice, fine for science, NOT tradeable.
  * The PORTFOLIO ranks every event ONLY against events announced in the trailing 365 days
    strictly BEFORE its own entry (min 60 same-type priors) — the entry decision is fully
    decidable at the entry close (CL-RES-03 discipline).
  * Fundamentals archive is survivor-conditioned (collected 2026 for the live universe) —
    same caveat as every fundamentals experiment in the ledger; stated in the output.

COSTS (per side): tier half-spread + fees (strategies.COST_TIERS by trailing median turnover)
+ 0.5 x ATR14% naive-market-order slippage (cost_realism basis). Personal-scale book — no
participation impact (clip << ADV); that IS the thesis (capacity-ceiling anomalies persist).
1.5x stress variant reported.

Read-only on hermes.db + research.db. Writes out/pead_events.csv + out/pead_summary.csv.
Run on VPS:
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.pead            # full run
  ... -m explosive_moves.pead --selftest # offline, synthetic, no DB
"""
from __future__ import annotations

import bisect
import csv
import math
import os
import sqlite3
import sys
from datetime import date, timedelta

import numpy as np

from .common import LIQ_FLOOR, OUT_DIR, load_series, main_conn, RESEARCH_DB
from .metrics import equity_stats

MIN_LAG_D, MAX_LAG_D = 5, 200        # plausible (real date - period_end); TCS files in ~9d
REACT_WIN = 2                        # sessions in the reaction window (day0, day0+1)
HOLD = 60                            # drift horizon in trading days after entry
CHECKPOINTS = (5, 22, 60)            # CAR horizons reported
MIN_DIFFS = 3                        # min prior NP diffs for a sigma
MAX_DIFFS = 8                        # sigma window (trailing diffs)
DELIV_BASE_WIN = 66                  # trailing window for median delivered value
MIN_PRIOR_ROWS = 70                  # tape history required before day0
ENTRY_LAG = REACT_WIN - 1            # entry at close of day0+1
TRAIL_DAYS = 365                     # portfolio trailing-rank reference window
MIN_PRIORS = 60                      # min prior same-type events before portfolio can rank
SUE_P, DLV_P = 0.80, 2.0 / 3.0       # portfolio entry thresholds (trailing percentiles)
H1_END = "2020-12-31"                # walk-forward halves boundary (house convention era-split)
SEASON_MIN_COHORT = 30               # min already-announced same-season cohort before within-season ranking


# ---------- pure helpers (selftested) ----------------------------------------

def sue_series(pairs: list[tuple[str, float]], seasonal: int) -> dict[str, float]:
    """{period_end: SUE} from [(period_end, net_profit)] sorted asc. SUE = (NP_t - NP_{t-s})
    / sigma(trailing diffs, min MIN_DIFFS, max MAX_DIFFS, excluding the current diff).
    ``seasonal``=1 for annual series, 4 for quarterly (q vs q-4). Sigma has a floor so a
    flat tiny series can't mint infinite SUE."""
    out: dict[str, float] = {}
    if len(pairs) < seasonal + MIN_DIFFS + 1:
        return out
    ends = [p for p, _ in pairs]
    vals = [v for _, v in pairs]
    # a seasonal partner must really be ~12 months back — a missing quarter must not
    # silently pair q against the wrong q-4 (fiscal-year changes, collection gaps)
    def _aligned(i: int) -> bool:
        try:
            gap = (date.fromisoformat(ends[i]) - date.fromisoformat(ends[i - seasonal])).days
        except ValueError:
            return False
        return 320 <= gap <= 430
    diffs: list[float | None] = []   # diff[j] aligns to period ends[j+seasonal]; None = misaligned
    for i in range(seasonal, len(vals)):
        diffs.append(vals[i] - vals[i - seasonal] if _aligned(i) else None)
    for j in range(len(diffs)):
        i = j + seasonal
        if diffs[j] is None:
            continue
        prior = [d for d in diffs[max(0, j - MAX_DIFFS):j] if d is not None]
        if len(prior) < MIN_DIFFS:
            continue
        med_abs = np.median(np.abs(np.array(vals[max(0, i - MAX_DIFFS):i + 1])))
        floor = max(0.02 * med_abs, 0.05)          # ~2% of scale, min 0.05 cr
        sigma = max(float(np.std(prior)), floor)
        out[ends[i]] = float(diffs[j] / sigma)
    return out


def dedup_earliest(rows: list[tuple[str, str]]) -> dict[str, str]:
    """{key: earliest knowable date} from (key, knowable_at) rows (provenance may hold
    several observations per key; the FIRST filing is the market event)."""
    out: dict[str, str] = {}
    for k, v in rows:
        v = str(v)[:10]
        if k not in out or v < out[k]:
            out[k] = v
    return out


def plausible(period_end: str, knowable: str) -> bool:
    try:
        lag = (date.fromisoformat(knowable) - date.fromisoformat(period_end)).days
    except ValueError:
        return False
    return MIN_LAG_D <= lag <= MAX_LAG_D


def trailing_pct(history: list[tuple[str, float]], asof: str, x: float,
                 min_n: int = MIN_PRIORS) -> float:
    """Percentile of ``x`` among values whose date is in [asof-365d, asof) — STRICTLY
    before asof. ``history`` sorted by date asc. NaN if fewer than min_n priors."""
    lo = (date.fromisoformat(asof) - timedelta(days=TRAIL_DAYS)).isoformat()
    i0 = bisect.bisect_left(history, (lo, -math.inf))
    i1 = bisect.bisect_left(history, (asof, -math.inf))
    window = [v for _, v in history[i0:i1] if v == v]
    if len(window) < min_n:
        return float("nan")
    return sum(1 for v in window if v <= x) / len(window)


def car_path(stock_levels: list[float], idx_levels: list[float]) -> list[float]:
    """Cumulative abnormal return path: CAR[h] over the first h steps of the two
    aligned level series (levels[0] = entry). Geometric stock minus geometric index."""
    out = []
    for h in range(1, len(stock_levels)):
        rs = stock_levels[h] / stock_levels[0] - 1.0
        ri = idx_levels[h] / idx_levels[0] - 1.0
        out.append(rs - ri)
    return out


def side_cost(med_turn: float, atr_pct: float, mult: float = 1.0) -> float:
    """One-side trading cost fraction: tier half-spread + fees + 0.5*ATR% slippage."""
    from .strategies import COST_TIERS, tier_for_turnover
    t = tier_for_turnover(med_turn) or "T1"
    c = COST_TIERS[t]
    a = atr_pct if atr_pct == atr_pct else 0.04
    return mult * (c["spread_rt"] / 2.0 + c["fees_ps"] + 0.5 * min(a, 0.08))


# ---------- event assembly ----------------------------------------------------

def load_real_dates(hcon) -> dict[tuple[str, str, str], str]:
    """{(symbol, ptype, period_end): earliest real BSE date} — plausibility-lagged."""
    rows = hcon.execute(
        "SELECT key, knowable_at FROM provenance_knowable WHERE data_class='fundamentals_history'"
    ).fetchall()
    earliest = dedup_earliest([(r[0], r[1]) for r in rows])
    out = {}
    for k, v in earliest.items():
        try:
            sym, ptype, pend = k.split("|")
        except ValueError:
            continue
        if plausible(pend, v):
            out[(sym, ptype, pend)] = v
    return out


def load_np(rcon) -> dict[tuple[str, str], list[tuple[str, float]]]:
    """{(symbol, ptype): [(period_end, NP)] asc} from fundamentals_history Net Profit."""
    rows = rcon.execute(
        "SELECT symbol, period_type, period_end, value FROM fundamentals_history "
        "WHERE metric='Net Profit' AND value IS NOT NULL").fetchall()
    out: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for sym, pt, pend, val in rows:
        out.setdefault((sym, pt), []).append((str(pend)[:10], float(val)))
    for k in out:
        out[k].sort()
    return out


def assemble_events(real_dates, np_map) -> list[dict]:
    """Cross real dates with SUE — one candidate event per (sym, ptype, period_end)."""
    events = []
    sue_cache: dict[tuple[str, str], dict[str, float]] = {}
    for (sym, ptype, pend), t0 in real_dates.items():
        key = (sym, ptype)
        if key not in sue_cache:
            pairs = np_map.get(key, [])
            sue_cache[key] = sue_series(pairs, 1 if ptype == "A" else 4)
        s = sue_cache[key].get(pend)
        if s is None:
            continue
        events.append({"sym": sym, "ptype": ptype, "pend": pend, "t0": t0, "sue": s})
    # dedup: same symbol, A + Q events within 5 calendar days -> keep the Q (finer signal)
    events.sort(key=lambda e: (e["sym"], e["t0"]))
    keep, last = [], None
    for e in events:
        if (last and last["sym"] == e["sym"]
                and abs((date.fromisoformat(e["t0"]) - date.fromisoformat(last["t0"])).days) <= 5):
            if last["ptype"] == "A" and e["ptype"] == "Q":
                keep[-1] = e
            continue
        keep.append(e); last = e
    return keep


# ---------- tape join ----------------------------------------------------------

def index_levels(hcon, name="Nifty 500") -> tuple[list[str], dict[str, float]]:
    rows = hcon.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name=? ORDER BY trade_date",
        (name,)).fetchall()
    dates = [r[0] for r in rows]
    return dates, {r[0]: float(r[1]) for r in rows if r[1] is not None}


def idx_level_asof(idx_dates: list[str], idx_map: dict[str, float], d: str) -> float:
    i = bisect.bisect_right(idx_dates, d) - 1
    return idx_map[idx_dates[i]] if i >= 0 else float("nan")


def tape_features(ss, ev: dict, idx_dates, idx_map) -> dict | None:
    """Attach day0/entry/reaction/delivery/CAR features to an event. None = excluded."""
    i0 = bisect.bisect_left(ss.date, ev["t0"])
    if i0 >= ss.n or i0 < MIN_PRIOR_ROWS:
        return None
    entry = i0 + ENTRY_LAG
    if entry + 2 >= ss.n:
        return None
    # liquidity gate + CA hygiene around the event
    mt = ss.med_turn[i0 - 1]
    if not (mt == mt and mt >= LIQ_FLOOR):
        return None
    if ss.is_ca[max(0, i0 - 1):entry + 3].any():
        return None
    # suspension guard: reaction window must be contiguous within ~6 calendar days
    if ss.gap_days(i0 - 1, entry) > 6:
        return None
    # reaction: EAR over [day0, day0+1]
    ac = ss.adj_close
    if not (ac[i0 - 1] > 0 and ac[entry] > 0):
        return None
    rs = ac[entry] / ac[i0 - 1] - 1.0
    li0, li1 = idx_level_asof(idx_dates, idx_map, ss.date[i0 - 1]), idx_level_asof(idx_dates, idx_map, ss.date[entry])
    if not (li0 == li0 and li1 == li1 and li0 > 0):
        return None
    ear = rs - (li1 / li0 - 1.0)
    # delivery conviction: mean delivered VALUE over the reaction window vs trailing median
    dv = ss.deliv_qty[i0:entry + 1] * ss.close[i0:entry + 1]
    base = ss.deliv_qty[i0 - DELIV_BASE_WIN:i0] * ss.close[i0 - DELIV_BASE_WIN:i0]
    base = base[~np.isnan(base) & (base > 0)]
    if len(base) < DELIV_BASE_WIN // 2 or np.isnan(dv).any():
        return None
    deliv_x = float(np.mean(dv) / np.median(base))
    # ATR% for costs (prior 14 rows, adj-invariant ratio)
    hl = (ss.high[i0 - 14:i0] - ss.low[i0 - 14:i0]) / ss.close[i0 - 14:i0]
    atr = float(np.nanmean(hl)) if len(hl) else float("nan")
    # CAR path from entry close to entry+HOLD (truncate at series end; drop if < 40 rows)
    end = min(entry + HOLD, ss.n - 1)
    if end - entry < 40:
        return None
    sl = [float(ac[j]) for j in range(entry, end + 1)]
    il = [idx_level_asof(idx_dates, idx_map, ss.date[j]) for j in range(entry, end + 1)]
    if any(not (x == x and x > 0) for x in il) or any(not (x == x and x > 0) for x in sl):
        return None
    path = car_path(sl, il)
    stock_rets = [sl[j + 1] / sl[j] - 1.0 for j in range(len(sl) - 1)]
    out = dict(ev)
    out.update({
        "day0": ss.date[i0], "entry_date": ss.date[entry], "entry_i": entry,
        "ear": float(ear), "deliv_x": deliv_x, "med_turn": float(mt), "atr": atr,
        "car5": path[4] if len(path) > 4 else float("nan"),
        "car22": path[21] if len(path) > 21 else float("nan"),
        "car60": path[-1], "n_path": len(path),
        "dates_path": [ss.date[j] for j in range(entry + 1, end + 1)],
        "stock_rets": stock_rets,
    })
    return out


# ---------- descriptive study --------------------------------------------------

def cohort_of(d: str) -> str:
    return f"{d[:4]}-Q{(int(d[5:7]) - 1) // 3 + 1}"


def rank_in(group: list[float], x: float) -> float:
    return sum(1 for v in group if v <= x) / len(group)


def bucket_table(events: list[dict], label: str, out_lines: list[str]) -> None:
    """CAR by SUE quintile, by delivery tercile, and the interaction corners."""
    by_cohort: dict[str, list[dict]] = {}
    for e in events:
        by_cohort.setdefault(cohort_of(e["t0"]), []).append(e)
    for es in by_cohort.values():
        if len(es) < 25:
            for e in es:
                e["skip_cohort"] = True
            continue
        sues = [e["sue"] for e in es]
        dlvs = [e["deliv_x"] for e in es]
        for e in es:
            e["sue_q"] = min(int(rank_in(sues, e["sue"]) * 5), 4)
            e["dlv_t"] = min(int(rank_in(dlvs, e["deliv_x"]) * 3), 2)
    pool = [e for e in events if not e.get("skip_cohort")]

    def stats(sel: list[dict], name: str):
        if len(sel) < 30:
            out_lines.append(f"  {name:<26} n={len(sel):>5}  (too small)")
            return
        for h, key in (("CAR60", "car60"), ("CAR22", "car22"), ("CAR5", "car5")):
            xs = np.array([e[key] for e in sel if e[key] == e[key]])
            if h != "CAR60" and name not in ("SUE Q5 x DELIV T3", "SUE Q5", "ALL"):
                continue
            t = xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))) if len(xs) > 2 else float("nan")
            # cohort-clustered t: mean of cohort means over their dispersion
            cm: dict[str, list[float]] = {}
            for e in sel:
                if e[key] == e[key]:
                    cm.setdefault(cohort_of(e["t0"]), []).append(e[key])
            cmeans = np.array([np.mean(v) for v in cm.values() if len(v) >= 5])
            tc = (cmeans.mean() / (cmeans.std(ddof=1) / math.sqrt(len(cmeans)))
                  if len(cmeans) > 3 else float("nan"))
            hit = float((xs > 0).mean())
            out_lines.append(f"  {name:<26} {h:<6} n={len(xs):>5}  mean={xs.mean()*100:+6.2f}%  "
                             f"med={np.median(xs)*100:+6.2f}%  hit={hit*100:4.1f}%  t={t:5.2f}  t_cohort={tc:5.2f}")

    out_lines.append(f"\n=== {label}: n={len(pool)} events (cohort-ranked, descriptive) ===")
    stats(pool, "ALL")
    for q in range(5):
        stats([e for e in pool if e.get("sue_q") == q], f"SUE Q{q+1}")
    for tt in range(3):
        stats([e for e in pool if e.get("dlv_t") == tt], f"DELIV T{tt+1}")
    stats([e for e in pool if e.get("sue_q") == 4 and e.get("dlv_t") == 2], "SUE Q5 x DELIV T3")
    stats([e for e in pool if e.get("sue_q") == 4 and e.get("dlv_t") == 0], "SUE Q5 x DELIV T1")
    stats([e for e in pool if e.get("sue_q") == 0 and e.get("dlv_t") == 2], "SUE Q1 x DELIV T3")
    stats([e for e in pool if e.get("sue_q") == 4 and e.get("dlv_t") == 2 and e["ear"] > 0],
          "Q5 x T3 x EAR>0")


# ---------- calendar-time portfolio (tradeable, trailing ranks) -----------------

def run_portfolio(events: list[dict], cal: list[str], label: str, out_lines: list[str],
                  cost_mult: float = 1.0, use_delivery: bool = True,
                  idx_ret: dict[str, float] | None = None) -> dict | None:
    """Jegadeesh-Titman calendar-time book: enter an event at its entry close when its
    trailing-percentile SUE >= SUE_P (same ptype), delivery >= DLV_P (pooled) and EAR>0;
    hold HOLD sessions, equal-weight across actives daily, side costs on entry/exit.
    ``idx_ret`` set = HEDGED DIAGNOSTIC: daily book return minus the index return on
    invested days (harvests CAR directly; GROSS of hedge-leg cost/margin — a diagnostic
    that separates 'edge is fake' from 'long-only wrapper eats it', not a fundable book)."""
    sue_hist: dict[str, list[tuple[str, float]]] = {"A": [], "Q": []}
    dlv_hist: list[tuple[str, float]] = []
    picks = []
    for e in sorted(events, key=lambda x: x["entry_date"]):
        sp = trailing_pct(sue_hist[e["ptype"]], e["entry_date"], e["sue"])
        dp = trailing_pct(dlv_hist, e["entry_date"], e["deliv_x"], min_n=100)
        sue_hist[e["ptype"]].append((e["entry_date"], e["sue"]))
        dlv_hist.append((e["entry_date"], e["deliv_x"]))
        if not (sp == sp and sp >= SUE_P and e["ear"] > 0):
            continue
        if use_delivery and not (dp == dp and dp >= DLV_P):
            continue
        picks.append(e)
    return _book(picks, cal, label, out_lines, cost_mult, idx_ret)


def _book(picks: list[dict], cal: list[str], label: str, out_lines: list[str],
          cost_mult: float = 1.0, idx_ret: dict[str, float] | None = None) -> dict | None:
    """Shared book builder: equal-weight across daily-active picks, side costs folded into
    each pick's first/last day, net equity curve + full/halves stats. ``idx_ret`` set =
    subtract index return on invested days (hedged diagnostic)."""
    if len(picks) < 40:
        out_lines.append(f"  {label}: only {len(picks)} qualifying entries — skipped")
        return None
    day_rets: dict[str, list[float]] = {}
    for e in picks:
        cost = side_cost(e["med_turn"], e["atr"], cost_mult)
        rets = list(e["stock_rets"])
        rets[0] -= cost
        rets[-1] -= cost
        for d, r in zip(e["dates_path"], rets):
            day_rets.setdefault(d, []).append(r)
    d0 = min(e["entry_date"] for e in picks)
    d1 = max(e["dates_path"][-1] for e in picks)
    days = [d for d in cal if d0 < d <= d1]
    eq, curve, invested, sizes = 1.0, [], 0, []
    for d in days:
        rs = day_rets.get(d)
        if rs:
            r = float(np.mean(rs))
            if idx_ret is not None:
                r -= idx_ret.get(d, 0.0)
            eq *= 1.0 + r
            invested += 1
            sizes.append(len(rs))
        curve.append(eq)
    st = equity_stats(days, curve)
    out_lines.append(f"  {label}: entries={len(picks)}  window={days[0]}..{days[-1]}  "
                     f"invested={invested/len(days)*100:.0f}% of days  book avg={np.mean(sizes):.1f} max={max(sizes)}")
    out_lines.append(f"    net  CAGR={st['cagr']*100:6.2f}%  MaxDD={st['maxdd']*100:6.1f}%  "
                     f"Sharpe={st['sharpe']:5.2f}  Calmar={st['calmar']:5.2f}")
    for tag, lo, hi in (("H1", days[0], H1_END), ("H2", H1_END, days[-1])):
        sub = [(d, c) for d, c in zip(days, curve) if lo <= d <= hi]
        if len(sub) > 250:
            s2 = equity_stats([d for d, _ in sub], [c for _, c in sub])
            out_lines.append(f"    {tag} {sub[0][0]}..{sub[-1][0]}: Sharpe={s2['sharpe']:5.2f}  "
                             f"CAGR={s2['cagr']*100:6.2f}%  MaxDD={s2['maxdd']*100:6.1f}%")
    return {"days": days, "curve": curve, "picks": picks, "stats": st}


def _season_select(events: list[dict]) -> list[dict]:
    """WITHIN-SEASON-SO-FAR picker (pure). Rank each event's SUE / delivery ONLY against
    same-(ptype, period_end) cohort-mates that announced STRICTLY EARLIER — a whole same-t0
    group is ranked against prior groups, then all added together, so there is no same-day
    leak. Enter if within-season SUE pctile >= SUE_P, EAR>0, delivery pctile >= DLV_P."""
    from collections import defaultdict
    cohorts: dict[tuple, list[dict]] = defaultdict(list)
    for e in events:
        cohorts[(e["ptype"], e["pend"])].append(e)
    picks: list[dict] = []
    for evs in cohorts.values():
        evs = sorted(evs, key=lambda x: x["t0"])
        seen_sue: list[float] = []
        seen_dlv: list[float] = []
        i = 0
        while i < len(evs):
            t0 = evs[i]["t0"]
            group = []
            while i < len(evs) and evs[i]["t0"] == t0:
                group.append(evs[i]); i += 1
            if len(seen_sue) >= SEASON_MIN_COHORT:
                for e in group:
                    sp = sum(1 for v in seen_sue if v <= e["sue"]) / len(seen_sue)
                    dp = sum(1 for v in seen_dlv if v <= e["deliv_x"]) / len(seen_dlv)
                    if sp >= SUE_P and e["ear"] > 0 and dp >= DLV_P:
                        picks.append(e)
            for e in group:
                seen_sue.append(e["sue"]); seen_dlv.append(e["deliv_x"])
    return picks


def run_portfolio_season(events: list[dict], cal: list[str], label: str,
                         out_lines: list[str], cost_mult: float = 1.0) -> dict | None:
    """The ONE untested PEAD construction on the ledger (pre-registered 2026-07-05): rank
    within the same reporting season as it unfolds, not against a trailing-365d mixed-season
    window. PRE-REGISTERED GATE: net Sharpe beats Nifty-500 (0.89) in BOTH halves -> a
    fundable strategy exists, build it; otherwise PEAD stays a descriptive lens (ledger)."""
    return _book(_season_select(events), cal, label, out_lines, cost_mult)


def bench_stats(hcon, d0: str, d1: str, out_lines: list[str]) -> None:
    dates, levels = index_levels(hcon)
    win = [(d, levels[d]) for d in dates if d0 <= d <= d1 and d in levels]
    st = equity_stats([d for d, _ in win], [v for _, v in win])
    out_lines.append(f"  Nifty500 B&H same window: Sharpe={st['sharpe']:5.2f}  "
                     f"CAGR={st['cagr']*100:6.2f}%  MaxDD={st['maxdd']*100:6.1f}%")
    for tag, lo, hi in (("H1", d0, H1_END), ("H2", H1_END, d1)):
        sub = [(d, v) for d, v in win if lo <= d <= hi]
        if len(sub) > 250:
            s2 = equity_stats([d for d, _ in sub], [v for _, v in sub])
            out_lines.append(f"    bench {tag}: Sharpe={s2['sharpe']:5.2f}  CAGR={s2['cagr']*100:6.2f}%")


# ---------- main ----------------------------------------------------------------

def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    hcon = main_conn()
    rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
    out: list[str] = []
    print("loading real dates + Net Profit archive...", flush=True)
    real = load_real_dates(hcon)
    np_map = load_np(rcon)
    rcon.close()
    cand = assemble_events(real, np_map)
    print(f"candidate events with real dates + SUE: {len(cand)}", flush=True)

    idx_dates, idx_map = index_levels(hcon)
    syms = sorted({e["sym"] for e in cand})
    by_sym: dict[str, list[dict]] = {}
    for e in cand:
        by_sym.setdefault(e["sym"], []).append(e)
    events: list[dict] = []
    for k, sym in enumerate(syms):
        ss = load_series(hcon, sym)
        if ss is None:
            continue
        for e in by_sym[sym]:
            fe = tape_features(ss, e, idx_dates, idx_map)
            if fe is not None:
                events.append(fe)
        if (k + 1) % 300 == 0:
            print(f"  tape-joined {k+1}/{len(syms)} symbols, events={len(events)}", flush=True)
    print(f"final events: {len(events)}", flush=True)
    out.append(f"PEAD study — {len(events)} events with real BSE dates, liquid, CA-clean "
               f"(survivor-conditioned fundamentals archive; entry = close of day0+1)")
    dens: dict[str, dict[str, int]] = {}
    for e in events:
        dens.setdefault(e["t0"][:4], {}).setdefault(e["ptype"], 0)
        dens[e["t0"][:4]][e["ptype"]] += 1
    out.append("event density (post liquidity/CA gates): " + "  ".join(
        f"{y}:A{v.get('A',0)}/Q{v.get('Q',0)}" for y, v in sorted(dens.items())))

    ann = [e for e in events if e["ptype"] == "A"]
    qtr = [e for e in events if e["ptype"] == "Q"]
    bucket_table(ann, "STUDY A — annual results (real dates ~2015->2026)", out)
    bucket_table(qtr, "STUDY Q — quarterly results (real dates 2023->2026)", out)

    out.append("\n=== CALENDAR-TIME PORTFOLIO (trailing ranks — tradeable rule) ===")
    out.append("rule: SUE trailing-pct>=0.80 (same ptype) AND EAR>0 AND delivery trailing-pct>=0.667, hold 60td")
    cal = idx_dates
    iret = {idx_dates[i]: idx_map[idx_dates[i]] / idx_map[idx_dates[i - 1]] - 1.0
            for i in range(1, len(idx_dates))
            if idx_dates[i] in idx_map and idx_dates[i - 1] in idx_map}
    p_full = run_portfolio(events, cal, "PEAD full (SUE+EAR+delivery)", out)
    run_portfolio(events, cal, "no-delivery variant (SUE+EAR only)", out, use_delivery=False)
    run_portfolio(events, cal, "cost x1.5 stress", out, cost_mult=1.5)
    run_portfolio(events, cal, "HEDGED diagnostic (minus index, gross hedge leg)", out, idx_ret=iret)
    out.append("\n=== PRE-REGISTERED VARIANT — within-season-so-far ranks (the ledger's one untested cell) ===")
    out.append("rule: SUE pctile vs already-announced same-(ptype,period_end) cohort >=0.80 AND EAR>0 AND "
               "delivery pctile >=0.667, hold 60td, NET. GATE: beat Nifty500 0.89 both halves -> fundable.")
    run_portfolio_season(events, cal, "PEAD within-season (full)", out)
    run_portfolio_season(events, cal, "PEAD within-season @1.5x cost", out, cost_mult=1.5)
    if p_full:
        bench_stats(hcon, p_full["days"][0], p_full["days"][-1], out)

    with open(OUT_DIR / "pead_events.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sym", "ptype", "pend", "t0", "entry_date", "sue", "ear", "deliv_x",
                    "med_turn", "car5", "car22", "car60"])
        for e in events:
            w.writerow([e["sym"], e["ptype"], e["pend"], e["t0"], e["entry_date"],
                        f"{e['sue']:.3f}", f"{e['ear']:.4f}", f"{e['deliv_x']:.3f}",
                        f"{e['med_turn']:.0f}", f"{e['car5']:.4f}", f"{e['car22']:.4f}",
                        f"{e['car60']:.4f}"])
    with open(OUT_DIR / "pead_summary.txt", "w") as fh:
        fh.write("\n".join(out) + "\n")
    hcon.close()
    print("\n".join(out))
    print(f"\nwrote {OUT_DIR/'pead_events.csv'} + pead_summary.txt")


# ---------- selftest (offline, no DB) --------------------------------------------

def selftest() -> None:
    # SUE: known answer, annual
    pairs = [(f"{y}-03-31", v) for y, v in
             zip(range(2015, 2023), [10, 12, 11, 14, 13, 16, 15, 40])]
    s = sue_series(pairs, 1)
    assert "2022-03-31" in s and s["2022-03-31"] > 3, s          # 15->40 jump vs ~2.1 sigma
    assert "2016-03-31" not in s                                  # too few diffs
    # quarterly seasonal alignment: q vs q-4
    qp = [(f"2023-{m:02d}-30", 10) for m in (6, 9, 12)] + [("2024-03-31", 10)] + \
         [(f"2024-{m:02d}-30", 12) for m in (6, 9, 12)] + [("2025-03-31", 12)] + \
         [(f"2025-{m:02d}-30", 12) for m in (6, 9, 12)] + [("2026-03-31", 30)]
    sq = sue_series(qp, 4)
    assert "2026-03-31" in sq and sq["2026-03-31"] > 2, sq
    # dedup earliest + plausibility
    dd = dedup_earliest([("K", "2024-04-24"), ("K", "2024-04-21 09:00:00")])
    assert dd["K"] == "2024-04-21"
    assert plausible("2024-03-31", "2024-04-21") and not plausible("2024-03-31", "2025-06-01")
    # trailing_pct: strictly-before window + min_n
    hist = [(f"2024-01-{d:02d}", float(d)) for d in range(1, 31)]
    assert trailing_pct(hist, "2024-02-01", 30.0, min_n=10) == 1.0
    assert trailing_pct(hist, "2024-01-15", 100.0, min_n=10) != trailing_pct(hist, "2024-01-15", 0.0, min_n=10)
    assert math.isnan(trailing_pct(hist, "2024-01-05", 5.0, min_n=10))   # too few priors
    # no-leak: percentile at a date must ignore same-day and later values
    h2 = [("2024-01-01", 1.0), ("2024-01-02", 2.0), ("2024-01-03", 99.0)]
    p = trailing_pct(h2, "2024-01-03", 0.5, min_n=2)
    assert p == 0.0, p                                            # 99 (same-day) excluded, 0.5 < {1,2}
    # CAR: hand-computed
    car = car_path([100, 110, 121], [1000, 1000, 1100])
    assert abs(car[0] - 0.10) < 1e-9 and abs(car[1] - (0.21 - 0.10)) < 1e-9
    # cost monotone in ATR and tier
    assert side_cost(30e7, 0.02) < side_cost(2e7, 0.02) < side_cost(2e7, 0.06)
    # within-season selector: none before the min cohort; only top-SUE names after; EAR gate blocks
    evs = [{"ptype": "Q", "pend": "2025-03-31",
            "t0": f"2025-{5 + d // 28:02d}-{(d % 28) + 1:02d}",
            "sue": float(d), "deliv_x": float(d), "ear": 1.0} for d in range(35)]
    picks = _season_select(evs)
    assert len(picks) == 5 and all(p["sue"] >= 30 for p in picks), [p["sue"] for p in picks]
    assert _season_select([dict(e, ear=-1.0) for e in evs]) == []
    print("PEAD selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
