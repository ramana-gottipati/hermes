"""anchor_audit.py — quantify the terminal-anchor survivorship leak in level factors.

MODEL-GOVERNANCE AUDIT (SR 11-7). READ-ONLY. Writes nothing to any DB, does not
mutate adjust.py or any shared module. New research-only artefact.

BACKGROUND (docs/institutional-panel-assessment.md, gap #2)
----------------------------------------------------------
Production back-adjustment (`src/automation/adjust.py`) walks BACKWARD from the
newest row and anchors the cumulative corporate-action factor at the *terminal*
(latest) price: newest factor = 1.0, older factors carry the product of every
action factor that occurred AFTER them. For a survivor the terminal is today's
price; for a delisted name it is a (frequently distressed) final print.

The panel's suspicion: LEVEL-based factors — range_pos_252 (52-wk band position),
dist-to-high — inherit an asymmetry from the choice of anchor, while pure-RETURN
factors (MOM6/MOM12) are anchor-invariant. This script MEASURES that directly.

METHOD — same factor, two anchors, per historical as-of date t
--------------------------------------------------------------
For each sampled symbol and each as-of date t we compute the identical factor
TWO ways and diff them:

  (a) TERMINAL anchor (what production does): compute adjustment_factors over the
      FULL series (oldest..terminal), then read the level factor as-of t using
      only rows[0..t]. The prices at t are scaled by the cumulative factor that
      folds in EVERY action, including those AFTER t.

  (b) AS-OF anchor (rolling / point-in-time honest): compute adjustment_factors
      over rows[0..t] ONLY (as if t were the terminal), then read the same level
      factor. Actions after t cannot exist yet, so they cannot enter the factor.

If (a) != (b) the terminal anchor has leaked future corporate actions into a
level read at t. Because a delisted name is FROZEN at its terminal while a
survivor keeps trading (and keeps having future splits/bonuses), the leak
distributes differently across the two cohorts — that difference IS the
survivorship asymmetry.

range_pos_252(t) = (P_t - min_252) / (max_252 - min_252)   [uses closes t-251..t]
dist_high_252(t) = P_t / max_252 - 1

MOM6(t) = adj_close[t] / adj_close[t-126] - 1   (pure return; sanity: invariant)

Run (VPS):
  ssh hermes
  cd /opt/hermes && PYTHONPATH=/opt/hermes \
    /opt/hermes/.venv-research/bin/python research/explosive_moves/anchor_audit.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.environ.get("PYTHONPATH", "/opt/hermes"))

from research.explosive_moves.common import main_conn, load_adjust  # noqa: E402

RNG = np.random.default_rng(11731)   # SR 11-7 :)
N_DELISTED = 30
N_SURVIVOR = 30
MIN_DAYS = 250
LOOKBACK = 252          # 52-week window
MOM_LAG = 126           # ~6 months trading days
N_ASOF_PER_SYM = 8      # historical as-of dates sampled per symbol
WARMUP = LOOKBACK + MOM_LAG + 10   # need a full 252 window + 126 mom lag before t


# ---------------------------------------------------------------------------
def sample_symbols(con):
    """~30 delisted (INACTIVE, >=250 days) and ~30 survivors (ACTIVE, listed)."""
    delisted = [r[0] for r in con.execute(
        "SELECT symbol FROM security_master "
        "WHERE status='INACTIVE' AND n_days>=? ORDER BY symbol", (MIN_DAYS,)).fetchall()]
    survivors = [r[0] for r in con.execute(
        "SELECT symbol FROM security_master "
        "WHERE status='ACTIVE' AND currently_listed=1 AND n_days>=? ORDER BY symbol",
        (MIN_DAYS,)).fetchall()]
    d = list(RNG.choice(delisted, size=min(N_DELISTED, len(delisted)), replace=False))
    s = list(RNG.choice(survivors, size=min(N_SURVIVOR, len(survivors)), replace=False))
    return sorted(d), sorted(s)


def load_rows(con, sym):
    """Raw close/prev_close oldest->newest for the EQ cash series."""
    rows = con.execute(
        "SELECT trade_date, close, prev_close FROM bhavcopy_rows "
        "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
        "ORDER BY trade_date ASC", (sym,)).fetchall()
    return [{"trade_date": r[0], "close": r[1], "prev_close": r[2]} for r in rows]


def level_factors(adj, rows, upto):
    """Return the per-row cumulative factor array computed with anchor at `upto`.

    upto=None -> full series (terminal anchor, production behaviour).
    upto=k    -> as-of anchor: recompute over rows[0..k] only.
    """
    sub = rows if upto is None else rows[: upto + 1]
    return np.array(adj.adjustment_factors(sub), dtype=float)


def factors_at(adj, rows, t, terminal_factors):
    """(range_pos_252, dist_high_252, mom6) at index t under BOTH anchors.

    terminal_factors is the full-series factor array (compute once per symbol).
    Returns dict of (a=terminal, b=asof) tuples.
    """
    closes = np.array([r["close"] if r["close"] is not None else np.nan
                       for r in rows], dtype=float)
    w0 = t - LOOKBACK + 1

    # (a) terminal anchor: scale the window with the full-series factors
    fa = terminal_factors
    win_a = closes[w0: t + 1] * fa[w0: t + 1]
    pt_a = closes[t] * fa[t]

    # (b) as-of anchor: recompute factors over rows[0..t] only
    fb = level_factors(adj, rows, upto=t)
    win_b = closes[w0: t + 1] * fb[w0: t + 1]
    pt_b = closes[t] * fb[t]

    def rp(win, pt):
        lo, hi = np.nanmin(win), np.nanmax(win)
        return (pt - lo) / (hi - lo) if (hi - lo) > 0 else np.nan

    def dh(win, pt):
        hi = np.nanmax(win)
        return pt / hi - 1.0 if hi > 0 else np.nan

    def mom(fac):
        p0 = closes[t - MOM_LAG] * fac[t - MOM_LAG]
        p1 = closes[t] * fac[t]
        return p1 / p0 - 1.0 if p0 > 0 else np.nan

    # Proof-of-work: the two factor arrays MUST actually differ over the window
    # whenever a corporate action occurs after t, otherwise the 0-diff result
    # would be a trivial artefact of comparing identical inputs. Record the
    # scalar ratio between the two anchors at t and the max within-window
    # relative spread of that ratio (0 ⇒ pure constant rescale ⇒ ratio-invariant).
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio_win = np.where(win_b != 0, win_a / win_b, np.nan)
    r_at_t = (pt_a / pt_b) if pt_b else np.nan
    finite = ratio_win[np.isfinite(ratio_win)]
    win_ratio_spread = (float(np.max(finite) / np.min(finite) - 1.0)
                        if len(finite) else np.nan)
    # ABSOLUTE (non-ratio) level factor — the one that WOULD leak: the raw
    # adjusted price level at t under each anchor. This is what a naive
    # "distance in rupees to 52w high" or a cross-sectional level sort sees.
    abs_price = (pt_a, pt_b)

    return {
        "range_pos": (rp(win_a, pt_a), rp(win_b, pt_b)),
        "dist_high": (dh(win_a, pt_a), dh(win_b, pt_b)),
        "mom6": (mom(fa), mom(fb)),
        "anchor_ratio_at_t": r_at_t,
        "win_ratio_spread": win_ratio_spread,
        "abs_price": abs_price,
    }


def audit_symbol(adj, rows):
    n = len(rows)
    if n < WARMUP + 5:
        return None
    tf = level_factors(adj, rows, upto=None)   # terminal anchor, once
    n_ca_total = int(np.sum(np.abs(np.diff(tf)) > 1e-9))
    lo, hi = WARMUP, n - 1
    if hi <= lo:
        return None
    ts = sorted(set(RNG.integers(lo, hi + 1, size=N_ASOF_PER_SYM).tolist()))
    recs = []
    for t in ts:
        f = factors_at(adj, rows, t, tf)
        recs.append(f)
    return recs, n_ca_total, n


def summarize(name, per_sym):
    """per_sym: list of (recs, n_ca_total, n_rows). Aggregate |a-b| by factor."""
    diffs = {"range_pos": [], "dist_high": [], "mom6": []}
    rp_a_vals, rp_b_vals = [], []
    anchor_ratios = []          # |terminal/asof price at t - 1|  (the raw level leak)
    win_spreads = []            # non-constant part of the rescale (should be ~0)
    n_obs_with_real_rescale = 0  # obs where the two anchors actually differ
    n_syms = 0
    n_syms_with_ca = 0
    n_obs = 0
    for recs, n_ca, _ in per_sym:
        n_syms += 1
        if n_ca > 0:
            n_syms_with_ca += 1
        for r in recs:
            n_obs += 1
            for k in diffs:
                a, b = r[k]
                if not (np.isnan(a) or np.isnan(b)):
                    diffs[k].append(abs(a - b))
            a, b = r["range_pos"]
            if not (np.isnan(a) or np.isnan(b)):
                rp_a_vals.append(a); rp_b_vals.append(b)
            ar = r["anchor_ratio_at_t"]
            if not np.isnan(ar):
                anchor_ratios.append(abs(ar - 1.0))
                if abs(ar - 1.0) > 1e-9:
                    n_obs_with_real_rescale += 1
            ws = r["win_ratio_spread"]
            if not np.isnan(ws):
                win_spreads.append(abs(ws))
    ar = np.array(anchor_ratios); wsp = np.array(win_spreads)
    out = {"cohort": name, "n_syms": n_syms, "n_syms_with_ca": n_syms_with_ca,
           "n_obs": n_obs, "n_obs_with_real_rescale": n_obs_with_real_rescale,
           "anchor_ratio_mean": float(np.mean(ar)) if len(ar) else float("nan"),
           "anchor_ratio_max": float(np.max(ar)) if len(ar) else float("nan"),
           "win_ratio_spread_max": float(np.max(wsp)) if len(wsp) else float("nan")}
    for k, v in diffs.items():
        v = np.array(v)
        out[k] = {
            "mean_abs_diff": float(np.mean(v)) if len(v) else float("nan"),
            "p95_abs_diff": float(np.percentile(v, 95)) if len(v) else float("nan"),
            "max_abs_diff": float(np.max(v)) if len(v) else float("nan"),
            "n_nonzero": int(np.sum(v > 1e-9)),
            "n": len(v),
        }
    # rank-impact: Spearman-ish — how many obs would flip a >0.05 band bucket
    a = np.array(rp_a_vals); b = np.array(rp_b_vals)
    if len(a):
        out["rp_band_flip_frac_0p05"] = float(np.mean(np.abs(a - b) > 0.05))
    else:
        out["rp_band_flip_frac_0p05"] = float("nan")
    return out


def fmt(o):
    L = [f"\n=== {o['cohort']} ===",
         f"symbols={o['n_syms']}  with_corp_action={o['n_syms_with_ca']}  as_of_obs={o['n_obs']}"]
    for k in ("range_pos", "dist_high", "mom6"):
        d = o[k]
        L.append(f"  {k:10s}  mean|Δ|={d['mean_abs_diff']:.6f}  "
                 f"p95={d['p95_abs_diff']:.6f}  max={d['max_abs_diff']:.6f}  "
                 f"nonzero={d['n_nonzero']}/{d['n']}")
    L.append(f"  range_pos band-flip (|Δ|>0.05): {o['rp_band_flip_frac_0p05']:.4f}")
    L.append(f"  PROOF anchors actually differ at t: "
             f"{o['n_obs_with_real_rescale']}/{o['n_obs']} obs have terminal≠asof rescale; "
             f"mean|anchorΔ|={o['anchor_ratio_mean']:.4f} max={o['anchor_ratio_max']:.4f}")
    L.append(f"  within-window rescale non-constancy (max): "
             f"{o['win_ratio_spread_max']:.2e}  (~0 ⇒ pure scalar ⇒ ratio factors invariant)")
    return "\n".join(L)


def main():
    con = main_conn()
    adj = load_adjust()
    delisted, survivors = sample_symbols(con)
    print(f"Sampled {len(delisted)} delisted + {len(survivors)} survivors "
          f"(status INACTIVE / ACTIVE&listed, n_days>={MIN_DAYS})")

    def run(syms):
        acc = []
        for sym in syms:
            rows = load_rows(con, sym)
            res = audit_symbol(adj, rows)
            if res is not None:
                acc.append(res)
        return acc

    d_res = run(delisted)
    s_res = run(survivors)
    con.close()

    od = summarize("DELISTED", d_res)
    os_ = summarize("SURVIVORS", s_res)
    print(fmt(od))
    print(fmt(os_))

    print("\n=== INTERPRETATION ===")
    rp_d = od["range_pos"]["mean_abs_diff"]
    rp_s = os_["range_pos"]["mean_abs_diff"]
    dh_d = od["dist_high"]["mean_abs_diff"]
    mom_d = od["mom6"]["max_abs_diff"]
    print(f"range_pos_252 mean|Δ|:  delisted={rp_d:.6f}  survivors={rp_s:.6f}")
    print(f"dist_high_252 mean|Δ|:  delisted={dh_d:.6f}  survivors={os_['dist_high']['mean_abs_diff']:.6f}")
    print(f"MOM6 max|Δ| (both cohorts, sanity): "
          f"delisted={mom_d:.2e}  survivors={os_['mom6']['max_abs_diff']:.2e}  "
          f"(≈0 ⇒ anchor-invariant, as theory predicts)")


if __name__ == "__main__":
    main()
