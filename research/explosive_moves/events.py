"""Phase A — explosive-move event detection + forward outcomes.

Three independent event sets, all on a survivorship-safe, point-in-time-liquid
universe (₹1cr trailing-median turnover), de-overlapped to launch ONSETS so the
precursor fingerprint is "what preceded the start of the move" (not day-3 of a rip):

  daily   : a +10% single day (raw close/prev_close, NSE-split-clean, CA rows excluded),
            onset = first such day after a 5-td calm stretch.
  weekly  : +10% over the forward 5 trading days (adjusted closes), onset of the surge.
  monthly : Ramana's definition — a >=20% close-basis thrust within ~22 td that then
            RETAINS >=50% of the gain on closes over the next ~22 td ("genuine buying").
            We record ALL >=20% thrusts with a `sustained` flag so the study can
            contrast what made a move hold vs fade.

For every launch we record forward outcomes (returns at +5/10/22/66/132/252 td,
6-month MFE/MAE, 12-month max run, big-winner flags) — these power the success ratio.

The launch day `s` is the last close BEFORE the move begins; all precursor features
(Phase B) are snapshotted as-of `s` => no look-ahead.
"""
from __future__ import annotations

import sys
import time

import numpy as np

from .common import (
    DAILY_MOVE, WEEKLY_MOVE, WEEKLY_WIN, MONTHLY_WIN, MONTHLY_MOVE,
    FWD_HORIZONS, STUDY_START, WARMUP_ROWS, LIQ_FLOOR,
    MAX_GAP_DAILY, MAX_GAP_WEEKLY, MAX_GAP_MONTHLY,
    SymbolSeries, eq_symbols, load_series, main_conn, research_conn,
)

DAILY_COOLDOWN = 5     # td: onset = no +10% day in the prior 5 td
WEEKLY_SPACING = 5     # td between weekly onsets
MONTHLY_SPACING = MONTHLY_WIN  # non-overlapping monthly launches


def _eligible(ss: SymbolSeries, s: int) -> bool:
    """Launch day s is liquid (point-in-time) and has enough prior history."""
    if s < WARMUP_ROWS or s >= ss.n:
        return False
    mt = ss.med_turn[s]
    return (not np.isnan(mt)) and mt >= LIQ_FLOOR


def forward_outcomes(ss: SymbolSeries, s: int) -> dict:
    """Adjusted-close forward path from launch day s (corporate-action clean)."""
    p0 = ss.adj_close[s]
    out: dict = {}
    if not (p0 > 0):
        return out
    for h in FWD_HORIZONS:
        j = s + h
        out[f"ret_{h}"] = (ss.adj_close[j] / p0 - 1.0) if j < ss.n and ss.adj_close[j] > 0 else np.nan
    # forward path slices (exclude launch day itself)
    def _slice(h):
        return ss.adj_close[s + 1: min(s + 1 + h, ss.n)]
    p6 = _slice(132)
    p12 = _slice(252)
    out["mfe_6m"] = (np.nanmax(p6) / p0 - 1.0) if len(p6) else np.nan
    out["mae_6m"] = (np.nanmin(p6) / p0 - 1.0) if len(p6) else np.nan
    out["maxrun_12m"] = (np.nanmax(p12) / p0 - 1.0) if len(p12) else np.nan
    out["big50_6m"] = int(out["mfe_6m"] >= 0.50) if len(p6) and not np.isnan(out["mfe_6m"]) else None
    out["big100_12m"] = int(out["maxrun_12m"] >= 1.00) if len(p12) and not np.isnan(out["maxrun_12m"]) else None
    out["fwd_complete_252"] = int(s + 252 < ss.n)
    out["fwd_complete_132"] = int(s + 132 < ss.n)
    return out


def _base(ss: SymbolSeries, s: int, move_idx: int, magnitude: float, etype: str) -> dict:
    rec = {
        "symbol": ss.symbol, "etype": etype,
        "launch_date": ss.date[s], "launch_idx": s,
        "move_date": ss.date[move_idx], "magnitude": float(magnitude),
        "year": ss.date[s][:4],
        "close_s": float(ss.close[s]), "adj_close_s": float(ss.adj_close[s]),
        "med_turn": float(ss.med_turn[s]),
    }
    rec.update(forward_outcomes(ss, s))
    return rec


def detect_daily(ss: SymbolSeries) -> list[dict]:
    big = (ss.ret_raw >= DAILY_MOVE) & (~ss.is_ca)
    big = np.nan_to_num(big, nan=0).astype(bool)
    events = []
    for m in range(1, ss.n):
        if not big[m]:
            continue
        lo = max(0, m - DAILY_COOLDOWN)
        if big[lo:m].any():        # not an onset: a +10% day occurred in prior 5 td
            continue
        s = m - 1
        if not _eligible(ss, s):
            continue
        if ss.date[m] < STUDY_START:
            continue
        if ss.gap_days(s, m) > MAX_GAP_DAILY:
            continue
        events.append(_base(ss, s, m, ss.ret_raw[m], "daily"))
    return events


def detect_weekly(ss: SymbolSeries) -> list[dict]:
    n = ss.n
    ac = ss.adj_close
    qual = np.zeros(n, dtype=bool)
    for s in range(0, n - WEEKLY_WIN):
        j = s + WEEKLY_WIN
        if ac[s] > 0 and ac[j] > 0 and (ac[j] / ac[s] - 1.0) >= WEEKLY_MOVE:
            qual[s] = True
    events = []
    last = -10_000
    for s in range(0, n - WEEKLY_WIN):
        # onset = a forward 5-td >=10% surge that did NOT already qualify yesterday
        is_onset = qual[s] and (s == 0 or not qual[s - 1])
        if not is_onset:
            continue
        if s - last < WEEKLY_SPACING:
            continue
        j = s + WEEKLY_WIN
        if not _eligible(ss, s):
            continue
        if ss.date[j] < STUDY_START:
            continue
        if ss.gap_days(s, j) > MAX_GAP_WEEKLY:
            continue
        events.append(_base(ss, s, j, ac[j] / ac[s] - 1.0, "weekly"))
        last = s
    return events


def detect_monthly(ss: SymbolSeries) -> list[dict]:
    """Rolling sustained +10% over ~1 month (Ramana's def).

    A base day s qualifies when a +10% move occurs within the next MONTHLY_WIN td
    (`reached_max >= 10%`); it is **SUSTAINED** when the close is still >= +10% at
    the end of the rolling month (`end_gain >= 10%` — held the gain), else FADED.
    De-overlap is by SPACING (distinct non-overlapping rolling months, >= MONTHLY_WIN
    apart) — NOT an onset-flip, which would mechanically couple the base day's 1-day
    return to the sustained/faded label (the forward-max boundary forces the month-end
    close to be the high when the base closed up). Spacing avoids that artifact while
    still anchoring the look-back at the *base* (where pre-move accumulation shows).
    No 20%/retain-half bar. All windows are rolling (any date), never calendar-bucketed.
    """
    n = ss.n
    ac = ss.adj_close
    end_gain = np.full(n, np.nan)
    reached = np.full(n, np.nan)
    rq = np.zeros(n, dtype=bool)
    for s in range(0, n - MONTHLY_WIN):
        p0 = ac[s]
        if not (p0 > 0):
            continue
        win = ac[s + 1: s + 1 + MONTHLY_WIN]
        if len(win) < MONTHLY_WIN or np.all(np.isnan(win)):
            continue
        end_gain[s] = ac[s + MONTHLY_WIN] / p0 - 1.0
        reached[s] = np.nanmax(win) / p0 - 1.0
        rq[s] = reached[s] >= MONTHLY_MOVE
    events = []
    last = -10_000
    for s in range(WARMUP_ROWS, n - MONTHLY_WIN):
        if not rq[s]:                              # a +10% move occurs within the forward month
            continue
        if s - last < MONTHLY_WIN:                 # spacing dedup → distinct non-overlapping months
            continue                               #   (avoids the onset-flip selection artifact)
        if not _eligible(ss, s):
            continue
        if ss.date[s + MONTHLY_WIN] < STUDY_START:
            continue
        if ss.gap_days(s, s + MONTHLY_WIN) > MAX_GAP_MONTHLY:
            continue
        d10 = None
        for k in range(1, MONTHLY_WIN + 1):
            if ac[s + k] / ac[s] - 1.0 >= MONTHLY_MOVE:
                d10 = k
                break
        rec = _base(ss, s, s + MONTHLY_WIN, end_gain[s], "monthly")
        rec.update({
            "end_gain": float(end_gain[s]), "reached_max": float(reached[s]),
            "sustained": int(end_gain[s] >= MONTHLY_MOVE),
            "days_to_10": (float(d10) if d10 else None),
        })
        events.append(rec)
        last = s
    return events


# ---- persistence ------------------------------------------------------------
_COMMON_COLS = [
    "symbol", "etype", "launch_date", "launch_idx", "move_date", "magnitude", "year",
    "close_s", "adj_close_s", "med_turn",
    *[f"ret_{h}" for h in FWD_HORIZONS],
    "mfe_6m", "mae_6m", "maxrun_12m", "big50_6m", "big100_12m",
    "fwd_complete_132", "fwd_complete_252",
]
_MONTHLY_EXTRA = ["end_gain", "reached_max", "sustained", "days_to_10"]


def _create_tables(rc):
    for tbl, extra in (("events_daily", []), ("events_weekly", []), ("events_monthly", _MONTHLY_EXTRA)):
        cols = _COMMON_COLS + extra
        rc.execute(f"DROP TABLE IF EXISTS {tbl}")
        coldefs = ", ".join(f'"{c}" {"TEXT" if c in ("symbol","etype","launch_date","move_date","year","peak_date") else "REAL"}' for c in cols)
        rc.execute(f"CREATE TABLE {tbl} ({coldefs})")
        rc.execute(f"CREATE INDEX idx_{tbl}_sym ON {tbl}(symbol)")
        rc.execute(f"CREATE INDEX idx_{tbl}_year ON {tbl}(year)")


def _insert(rc, tbl, cols, records):
    if not records:
        return
    ph = ",".join("?" for _ in cols)
    rc.executemany(
        f'INSERT INTO {tbl} ({",".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({ph})',
        [[r.get(c) for c in cols] for r in records],
    )


def main(limit: int | None = None):
    t0 = time.time()
    mc = main_conn()
    rc = research_conn()
    _create_tables(rc)
    syms = eq_symbols(mc)
    if limit:
        syms = syms[:limit]
    tot = {"daily": 0, "weekly": 0, "monthly": 0, "monthly_sust": 0}
    buf = {"events_daily": [], "events_weekly": [], "events_monthly": []}
    for k, sym in enumerate(syms):
        ss = load_series(mc, sym)
        if ss is None:
            continue
        d = detect_daily(ss); w = detect_weekly(ss); m = detect_monthly(ss)
        buf["events_daily"].extend(d); buf["events_weekly"].extend(w); buf["events_monthly"].extend(m)
        tot["daily"] += len(d); tot["weekly"] += len(w); tot["monthly"] += len(m)
        tot["monthly_sust"] += sum(1 for r in m if r.get("sustained") == 1)
        if (k + 1) % 500 == 0:
            _insert(rc, "events_daily", _COMMON_COLS, buf["events_daily"])
            _insert(rc, "events_weekly", _COMMON_COLS, buf["events_weekly"])
            _insert(rc, "events_monthly", _COMMON_COLS + _MONTHLY_EXTRA, buf["events_monthly"])
            rc.commit()
            buf = {"events_daily": [], "events_weekly": [], "events_monthly": []}
            print(f"  {k+1}/{len(syms)} symbols  events so far {tot}  ({time.time()-t0:.0f}s)", flush=True)
    _insert(rc, "events_daily", _COMMON_COLS, buf["events_daily"])
    _insert(rc, "events_weekly", _COMMON_COLS, buf["events_weekly"])
    _insert(rc, "events_monthly", _COMMON_COLS + _MONTHLY_EXTRA, buf["events_monthly"])
    rc.commit()
    print(f"DONE in {time.time()-t0:.0f}s. Totals: {tot}")
    print(f"  monthly sustained rate = {tot['monthly_sust']}/{tot['monthly']} "
          f"= {100*tot['monthly_sust']/max(1,tot['monthly']):.1f}%")
    rc.close(); mc.close()


if __name__ == "__main__":
    lim = None
    if len(sys.argv) > 1 and sys.argv[1].startswith("--limit"):
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else int(sys.argv[1].split("=")[1])
    main(lim)
