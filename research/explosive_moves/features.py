"""Phase B — precursor fingerprint matrix.

For every event launch day `s` (3 types) AND a reweightable random sample of
quiet liquid days (the baseline / contrast set), snapshot the precursor state
strictly as-of `s` (only data <= s; the move begins after s -> no look-ahead):

  raw_*  : descriptors computed from the symbol's own price/volume/delivery
           (trailing returns, distance-from-highs, volatility contraction, base
           tightness, volume dry-up/skew, delivery regime, trend posture).
  h_*    : the house stock_signals battery (DVPT/power/p_score/character/RS/...).
  cpr_*  : CPR compression/pivot geometry (daily timeframe), as-of <= s.

Baseline days are sampled at rate 1/K (K recorded) so Phase C/D can reweight to
true prevalence and report real-world precision/lift, not sample-relative numbers.
"""
from __future__ import annotations

import sys
import time
from bisect import bisect_right

import numpy as np

from .common import (
    STUDY_START, WARMUP_ROWS, LIQ_FLOOR, FWD_HORIZONS,
    SymbolSeries, eq_symbols, load_series, main_conn, research_conn,
)
from .events import forward_outcomes

BASELINE_K = 10          # keep ~1-in-10 non-event liquid days as baseline
EXCL_BEFORE = 20         # exclude only the immediate pre-move run-up from baseline
EXCL_AFTER = 44          # exclude the move period + immediate aftermath
RNG = np.random.default_rng(20260620)

HOUSE_NUM = [
    "p_score", "r_score", "is_ath_dvpt", "ratio_today_vs_avg_30d",
    "ratio_today_vs_power_1m", "ratio_today_vs_power_3m",
    "deliv_value_ratio_1m_6m", "trade_count_ratio_1m_6m",
    "avg_deliv_pct_1m", "avg_deliv_pct_6m", "deliv_updown_ratio_3m",
    "accum_price_drift_3m", "pct_from_52w_high",
    "turnover_surge_1m", "turnover_surge_3m", "turnover_surge_1y",
    "avg_trade_qty", "avg_deliv_qty_per_trade",
    "rs_vs_broad_slope_1m", "rs_vs_broad_slope_3m", "rs_vs_broad_slope_6m",
    "rs_vs_broad_slope_12m", "rs_vs_broad_above_50ma", "rs_vs_broad_above_200ma",
    "rs_vs_broad_new_52w_high", "rs_rank", "rs_vs_sector_slope_3m",
    "rs_vs_sector_slope_6m", "gap_to_next_p_pct",
]
HOUSE_TXT = ["trigger_rank", "accum_character", "rs_vs_broad_trend_state",
             "rs_vs_sector_trend_state", "next_p_above"]
CPR_NUM = ["compression_pctile", "width_pct", "separation_pct", "depth_pct"]
CPR_TXT = ["pattern", "regime"]

RAW_NUM = [
    "ret_1d", "ret_5d", "ret_10d", "ret_22d", "ret_66d", "ret_132d", "ret_252d",
    "dist_high_22", "dist_high_66", "dist_high_252", "dist_high_all",
    "dist_low_252", "vol_22", "vol_66", "vol_ratio", "range_tight_22",
    "range_tight_66", "atr14_pct", "atr_contraction", "nr_ratio_10_60",
    "vol_dryup_5_22", "vol_ratio_22_66", "vol_z_1d", "turnover_surge_raw",
    "deliv_per_s", "deliv_per_22", "deliv_trend", "deliv_updown_22",
    "up_frac_22", "close_vs_sma20", "close_vs_sma50", "close_vs_sma200",
    "sma50_vs_sma200", "sma50_slope", "consec_up", "gap_1d", "log_price",
    "hist_len",
    # expanded raw delivery/volume/participation battery (session 25 v2 — the "strong hand" footprint)
    "deliv_qty_trend", "deliv_val_trend", "deliv_per_pctile", "n_strong_deliv_22",
    "big_deliv_days_10", "trades_trend", "avg_trade_val_trend", "vol_pctile_252",
    "updown_vol_22", "close_strength_5", "new_high_22", "range_pos_252",
]

ALL_NUM = RAW_NUM + ["h_" + c for c in HOUSE_NUM] + ["cpr_" + c for c in CPR_NUM]
ALL_TXT = ["h_" + c for c in HOUSE_TXT] + ["cpr_" + c for c in CPR_TXT]
LABEL_COLS = ["symbol", "etype", "launch_date", "year", "label", "sustained",
              "magnitude", "med_turn", *[f"ret_{h}" for h in FWD_HORIZONS],
              "mfe_6m", "mae_6m", "maxrun_12m", "big50_6m", "big100_12m",
              "fwd_complete_132", "fwd_complete_252"]


def _slc(a, lo, hi):
    lo = max(0, lo)
    return a[lo:hi]


def _safe_div(a, b):
    return a / b if (b is not None and b == b and b != 0) else np.nan


def raw_features(ss: SymbolSeries, s: int) -> dict:
    ac, ah, al = ss.adj_close, ss.adj_high, ss.adj_low
    c = ac[s]
    f = {}
    def ret(k):
        j = s - k
        return (c / ac[j] - 1.0) if j >= 0 and ac[j] > 0 else np.nan
    f["ret_1d"], f["ret_5d"], f["ret_10d"] = ret(1), ret(5), ret(10)
    f["ret_22d"], f["ret_66d"], f["ret_132d"], f["ret_252d"] = ret(22), ret(66), ret(132), ret(252)
    for w in (22, 66, 252):
        hi = np.nanmax(_slc(ac, s - w + 1, s + 1))
        f[f"dist_high_{w}"] = (c / hi - 1.0) if hi > 0 else np.nan
    f["dist_high_all"] = (c / np.nanmax(ac[:s + 1]) - 1.0)
    lo252 = np.nanmin(_slc(ac, s - 251, s + 1))
    f["dist_low_252"] = (c / lo252 - 1.0) if lo252 > 0 else np.nan
    # realized vol of daily log returns
    lr = np.diff(np.log(np.clip(_slc(ac, s - 66, s + 1), 1e-9, None)))
    f["vol_22"] = float(np.nanstd(lr[-22:])) if len(lr) >= 22 else np.nan
    f["vol_66"] = float(np.nanstd(lr)) if len(lr) >= 30 else np.nan
    f["vol_ratio"] = _safe_div(f["vol_22"], f["vol_66"])
    for w in (22, 66):
        seg = _slc(ac, s - w + 1, s + 1)
        m = np.nanmean(seg)
        f[f"range_tight_{w}"] = ((np.nanmax(seg) - np.nanmin(seg)) / m) if m > 0 else np.nan
    tr = (_slc(ah, s - 13, s + 1) - _slc(al, s - 13, s + 1)) / np.clip(_slc(ac, s - 13, s + 1), 1e-9, None)
    f["atr14_pct"] = float(np.nanmean(tr)) if len(tr) else np.nan
    tr60 = (_slc(ah, s - 59, s + 1) - _slc(al, s - 59, s + 1)) / np.clip(_slc(ac, s - 59, s + 1), 1e-9, None)
    f["atr_contraction"] = _safe_div(f["atr14_pct"], float(np.nanmean(tr60)) if len(tr60) else np.nan)
    rng10 = np.nanmean((_slc(ah, s - 9, s + 1) - _slc(al, s - 9, s + 1)))
    rng60 = np.nanmean((_slc(ah, s - 59, s + 1) - _slc(al, s - 59, s + 1)))
    f["nr_ratio_10_60"] = _safe_div(rng10, rng60)
    # volume
    v = ss.volume
    f["vol_dryup_5_22"] = _safe_div(np.nanmean(_slc(v, s - 4, s + 1)), np.nanmean(_slc(v, s - 21, s + 1)))
    f["vol_ratio_22_66"] = _safe_div(np.nanmean(_slc(v, s - 21, s + 1)), np.nanmean(_slc(v, s - 65, s + 1)))
    v22 = _slc(v, s - 21, s + 1)
    f["vol_z_1d"] = _safe_div(v[s] - np.nanmean(v22), np.nanstd(v22))
    f["turnover_surge_raw"] = _safe_div(ss.value[s], ss.med_turn[s])
    # delivery
    dp = ss.deliv_per
    f["deliv_per_s"] = dp[s]
    f["deliv_per_22"] = float(np.nanmean(_slc(dp, s - 21, s + 1)))
    f["deliv_trend"] = f["deliv_per_22"] - float(np.nanmean(_slc(dp, s - 65, s + 1)))
    # value-weighted up/down delivery over last 22 (raw ₹)
    dv = ss.deliv_qty * ss.close
    rets = np.diff(ac[max(0, s - 22):s + 1])
    dvw = dv[max(0, s - 22) + 1:s + 1]
    up = np.nansum(dvw[rets > 0]); dn = np.nansum(dvw[rets < 0])
    f["deliv_updown_22"] = _safe_div(up, dn)
    f["up_frac_22"] = float(np.mean(rets > 0)) if len(rets) else np.nan
    # trend posture
    def sma(w):
        seg = _slc(ac, s - w + 1, s + 1)
        return float(np.nanmean(seg)) if len(seg) >= w * 0.8 else np.nan
    s20, s50, s200 = sma(20), sma(50), sma(200)
    f["close_vs_sma20"] = _safe_div(c, s20) - 1 if s20 == s20 else np.nan
    f["close_vs_sma50"] = _safe_div(c, s50) - 1 if s50 == s50 else np.nan
    f["close_vs_sma200"] = _safe_div(c, s200) - 1 if s200 == s200 else np.nan
    f["sma50_vs_sma200"] = _safe_div(s50, s200) - 1 if (s50 == s50 and s200 == s200) else np.nan
    s50_prev = float(np.nanmean(_slc(ac, s - 69, s - 19))) if s >= 69 else np.nan
    f["sma50_slope"] = _safe_div(s50, s50_prev) - 1 if (s50 == s50 and s50_prev == s50_prev) else np.nan
    # consecutive up days ending at s
    cu = 0
    for k in range(s, 0, -1):
        if ac[k] > ac[k - 1]:
            cu += 1
        else:
            break
    f["consec_up"] = cu
    f["gap_1d"] = (ss.open[s] / ss.close[s - 1] - 1.0) if s >= 1 and ss.close[s - 1] > 0 else np.nan
    f["log_price"] = float(np.log10(ss.close[s])) if ss.close[s] > 0 else np.nan
    f["hist_len"] = float(s)
    # --- raw delivery / volume / participation battery (the "strong hand" footprint, read RAW,
    #     NOT via the house DVPT constructs) ---
    dq = ss.deliv_qty
    f["deliv_qty_trend"] = _safe_div(np.nanmean(_slc(dq, s - 21, s + 1)), np.nanmean(_slc(dq, s - 65, s + 1)))
    f["deliv_val_trend"] = _safe_div(np.nanmean(_slc(dv, s - 21, s + 1)), np.nanmean(_slc(dv, s - 65, s + 1)))
    dpw = _slc(dp, s - 251, s + 1)
    f["deliv_per_pctile"] = float(np.nanmean(dpw <= dp[s])) if (len(dpw) and not np.isnan(dp[s])) else np.nan
    f["n_strong_deliv_22"] = float(np.nansum(_slc(dp, s - 21, s + 1) > 70))
    dv60 = np.nanmean(_slc(dv, s - 59, s + 1))
    f["big_deliv_days_10"] = float(np.nansum(_slc(dv, s - 9, s + 1) > 2 * dv60)) if dv60 > 0 else np.nan
    f["trades_trend"] = _safe_div(np.nanmean(_slc(ss.num_trades, s - 21, s + 1)),
                                  np.nanmean(_slc(ss.num_trades, s - 65, s + 1)))
    with np.errstate(divide="ignore", invalid="ignore"):
        atv = np.where(ss.num_trades > 0, ss.value / np.where(ss.num_trades > 0, ss.num_trades, np.nan), np.nan)
    f["avg_trade_val_trend"] = _safe_div(np.nanmean(_slc(atv, s - 21, s + 1)), np.nanmean(_slc(atv, s - 65, s + 1)))
    vw = _slc(v, s - 251, s + 1)
    f["vol_pctile_252"] = float(np.nanmean(vw <= v[s])) if (len(vw) and not np.isnan(v[s])) else np.nan
    vv = v[max(0, s - 22) + 1:s + 1]
    f["updown_vol_22"] = _safe_div(np.nansum(vv[rets > 0]), np.nansum(vv[rets < 0]))
    hl = ss.high - ss.low
    with np.errstate(divide="ignore", invalid="ignore"):
        cs = np.where(hl > 0, (ss.close - ss.low) / np.where(hl > 0, hl, np.nan), np.nan)
    f["close_strength_5"] = float(np.nanmean(_slc(cs, s - 4, s + 1)))
    f["new_high_22"] = float(np.nansum(ss.is_ath[max(0, s - 21):s + 1]))
    mx252 = np.nanmax(_slc(ac, s - 251, s + 1)); mn252 = np.nanmin(_slc(ac, s - 251, s + 1))
    f["range_pos_252"] = _safe_div(c - mn252, mx252 - mn252)
    return f


def _load_house(mc, symbol):
    rows = mc.execute(
        f"SELECT trade_date,{','.join(HOUSE_NUM + HOUSE_TXT)} FROM stock_signals WHERE symbol=?",
        (symbol,)).fetchall()
    return {r["trade_date"]: r for r in rows}


def _load_cpr(mc, symbol):
    rows = mc.execute(
        f"""SELECT period_end_date,{','.join(CPR_NUM + CPR_TXT)} FROM cpr_signals
            WHERE symbol=? AND timeframe='D' ORDER BY period_end_date ASC""",
        (symbol,)).fetchall()
    return [r["period_end_date"] for r in rows], rows


def _cpr_asof(dates, rows, d):
    i = bisect_right(dates, d)
    return rows[i - 1] if i > 0 else None


def _make_row(ss, s, etype, label, mc_house, cpr_dates, cpr_rows, sustained=None, magnitude=None):
    d = ss.date[s]
    rec = {"symbol": ss.symbol, "etype": etype, "launch_date": d, "year": d[:4],
           "label": label, "sustained": sustained, "magnitude": magnitude,
           "med_turn": float(ss.med_turn[s])}
    rec.update(forward_outcomes(ss, s))
    rec.update(raw_features(ss, s))
    hr = mc_house.get(d)
    for c in HOUSE_NUM:
        rec["h_" + c] = (hr[c] if hr is not None else None)
    for c in HOUSE_TXT:
        rec["h_" + c] = (hr[c] if hr is not None else None)
    cr = _cpr_asof(cpr_dates, cpr_rows, d)
    for c in CPR_NUM:
        rec["cpr_" + c] = (cr[c] if cr is not None else None)
    for c in CPR_TXT:
        rec["cpr_" + c] = (cr[c] if cr is not None else None)
    return rec


def _create_table(rc):
    rc.execute("DROP TABLE IF EXISTS features")
    cols = LABEL_COLS + ALL_NUM + ALL_TXT
    defs = []
    txt = set(["symbol", "etype", "launch_date", "year"] + ALL_TXT)
    for c in cols:
        defs.append(f'"{c}" {"TEXT" if c in txt else "REAL"}')
    rc.execute(f"CREATE TABLE features ({', '.join(defs)})")
    rc.execute("CREATE INDEX idx_feat_etype ON features(etype, label)")
    rc.execute("CREATE INDEX idx_feat_year ON features(year)")
    return cols


def main(limit=None):
    t0 = time.time()
    mc = main_conn(); rc = research_conn()
    cols = _create_table(rc)
    # event launch indices per symbol per type
    ev = {}
    for tbl, et in (("events_daily", "daily"), ("events_weekly", "weekly"), ("events_monthly", "monthly")):
        for r in rc.execute(f"SELECT symbol,launch_idx,launch_date,magnitude,"
                            f"{'sustained' if et=='monthly' else 'NULL sustained'} FROM {tbl}"):
            ev.setdefault(r["symbol"], []).append((et, int(r["launch_idx"]), r["launch_date"],
                                                   r["magnitude"], r["sustained"]))
    syms = eq_symbols(mc)
    if limit:
        syms = syms[:limit]
    buf = []
    n_ev = 0; n_base = 0
    for k, sym in enumerate(syms):
        ss = load_series(mc, sym)
        if ss is None:
            continue
        house = _load_house(mc, sym)
        cpr_dates, cpr_rows = _load_cpr(mc, sym)
        evs = ev.get(sym, [])
        blocked = np.zeros(ss.n, dtype=bool)
        for (et, s, ld, mag, sust) in evs:
            if 0 <= s < ss.n and ss.date[s] == ld:   # safety: index maps to same row
                blocked[max(0, s - EXCL_BEFORE): min(ss.n, s + EXCL_AFTER + 1)] = True
                buf.append(_make_row(ss, s, et, 1, house, cpr_dates, cpr_rows, sust, mag))
                n_ev += 1
        # baseline: quiet liquid days, 1-in-K
        for s in range(WARMUP_ROWS, ss.n):
            if blocked[s]:
                continue
            if ss.date[s] < STUDY_START:
                continue
            mt = ss.med_turn[s]
            if np.isnan(mt) or mt < LIQ_FLOOR:
                continue
            if RNG.random() < 1.0 / BASELINE_K:
                buf.append(_make_row(ss, s, "baseline", 0, house, cpr_dates, cpr_rows))
                n_base += 1
        if len(buf) >= 5000:
            _flush(rc, cols, buf); buf = []
        if (k + 1) % 500 == 0:
            print(f"  {k+1}/{len(syms)}  events={n_ev} baseline={n_base}  ({time.time()-t0:.0f}s)", flush=True)
    _flush(rc, cols, buf)
    rc.execute("DROP TABLE IF EXISTS feat_meta")
    rc.execute("CREATE TABLE feat_meta (k TEXT, v TEXT)")
    rc.executemany("INSERT INTO feat_meta VALUES (?,?)",
                   [("baseline_k", str(BASELINE_K)), ("n_events", str(n_ev)),
                    ("n_baseline", str(n_base)), ("excl_before", str(EXCL_BEFORE)),
                    ("excl_after", str(EXCL_AFTER))])
    rc.commit()
    print(f"DONE in {time.time()-t0:.0f}s. events={n_ev} baseline={n_base} (K={BASELINE_K})")
    rc.close(); mc.close()


def _flush(rc, cols, buf):
    if not buf:
        return
    ph = ",".join("?" for _ in cols)
    rc.executemany(f'INSERT INTO features ({",".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({ph})',
                   [[r.get(c) for c in cols] for r in buf])
    rc.commit()


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(lim)
