"""X-10 — expiry / holiday conditioning (S204).

A precise trading-calendar CONDITIONING UTILITY, computed from the trading-date sequence
alone (the exchange's own calendar -> primary-source, no feed):

  * monthly F&O expiry     = the last trading day on-or-before the last Thursday of each
                             month (so a holiday on expiry Thursday rolls it to the prior
                             trading day automatically).
  * days_to_expiry         = trading days to the next monthly expiry; is_expiry_week flags
                             the final week into it.
  * holiday adjacency      = pre_holiday / post_holiday, derived from calendar gaps between
                             consecutive trading days that exceed the normal weekend (Fri->Mon
                             = 3d) or weekday (1d) spacing -- i.e. a market holiday intervened.

WHY A UTILITY, NOT A NEW EDGE STUDY (important fence): the calendar-seasonality question is
already OWNED by the frozen `src.automation.seasonal_tape` estate -- which carries an
`F-EXPIRY` family (F&O Thursday clustering) + `F-TOM-SIP` and whose finding was largely
0-CERTIFIED (calendar effects did not survive). This module does NOT re-litigate that. It
supplies the *precise* expiry-date + holiday-adjacency primitive the estate lacks (seasonal_tape
uses a coarse all-Thursdays weekday proxy; nothing computes the actual monthly-expiry trading
day or holiday adjacency). The per-symbol `condition_series` read is DESCRIPTIVE ONLY and must
be read against that null prior -- a conditioning lens, not a signal.
"""
from __future__ import annotations

import calendar as _cal
import json
import sys
from datetime import date, timedelta

import numpy as np

from .common import LIQ_FLOOR, OUT_DIR, eq_symbols, load_series, main_conn

EXPIRY_WEEK_TD = 5                                             # trading days that count as "expiry week"


# ---------- pure calendar utility (deterministic; hermetically testable) ----------

def _last_thursday(year: int, month: int) -> date:
    """The calendar last-Thursday of a month (weekday 3)."""
    last_dom = _cal.monthrange(year, month)[1]
    d = date(year, month, last_dom)
    return d - timedelta(days=(d.weekday() - 3) % 7)


def monthly_expiry_dates(dates) -> list[str]:
    """Monthly F&O expiry trading days: the last trading date on-or-before each month's last
    Thursday (holiday on the Thursday -> the prior trading day). ``dates`` = sorted ISO strings."""
    ds = [date.fromisoformat(s) for s in dates]
    by_month: dict[tuple[int, int], list[date]] = {}
    for d in ds:
        by_month.setdefault((d.year, d.month), []).append(d)
    out = []
    for (y, m), days in by_month.items():
        lt = _last_thursday(y, m)
        on_or_before = [d for d in days if d <= lt]
        if on_or_before:
            out.append(max(on_or_before).isoformat())
    return sorted(out)


def calendar_flags(dates) -> dict:
    """Per-date conditioning flags for a sorted ISO trading calendar. All arrays length n."""
    ds = [date.fromisoformat(s) for s in dates]
    n = len(ds)
    exp = set(monthly_expiry_dates(dates))
    exp_idx = [i for i, s in enumerate(dates) if s in exp]

    is_expiry = np.array([s in exp for s in dates], dtype=bool)
    days_to_expiry = np.full(n, np.nan)
    j = 0
    for i in range(n):
        while j < len(exp_idx) and exp_idx[j] < i:
            j += 1
        if j < len(exp_idx):
            days_to_expiry[i] = exp_idx[j] - i
    is_expiry_week = np.array([np.isfinite(days_to_expiry[i]) and days_to_expiry[i] < EXPIRY_WEEK_TD
                               for i in range(n)], dtype=bool)

    is_pre_holiday = np.zeros(n, dtype=bool)
    is_post_holiday = np.zeros(n, dtype=bool)
    prior_gap = np.full(n, np.nan)
    for i in range(1, n):
        gap = (ds[i] - ds[i - 1]).days
        prior_gap[i] = gap
        expected = 3 if ds[i - 1].weekday() == 4 else 1     # Fri->Mon = 3, else consecutive = 1
        if gap > expected:                                   # a holiday intervened
            is_post_holiday[i] = True
            is_pre_holiday[i - 1] = True
    return {
        "is_monthly_expiry": is_expiry,
        "days_to_expiry": days_to_expiry,
        "is_expiry_week": is_expiry_week,
        "is_pre_holiday": is_pre_holiday,
        "is_post_holiday": is_post_holiday,
        "prior_gap_days": prior_gap,
    }


def condition_series(values, flags) -> dict:
    """DESCRIPTIVE stats of ``values`` (e.g. daily returns) conditioned on each calendar flag:
    n, mean, median, and mean delta vs the all-days mean. Read against seasonal_tape's null prior."""
    v = np.asarray(values, dtype=float)
    fin = np.isfinite(v)
    all_mean = float(np.nanmean(v)) if fin.any() else float("nan")
    out = {"all_days": {"n": int(fin.sum()), "mean": all_mean}}
    for key in ("is_monthly_expiry", "is_expiry_week", "is_pre_holiday", "is_post_holiday"):
        sel = flags[key] & fin
        vv = v[sel]
        out[key] = {
            "n": int(sel.sum()),
            "mean": float(np.mean(vv)) if vv.size else float("nan"),
            "median": float(np.median(vv)) if vv.size else float("nan"),
            "mean_delta_vs_all": (float(np.mean(vv)) - all_mean) if vv.size else float("nan"),
        }
    return out


# ---------- per-symbol row + scan --------------------------------------------------

def symbol_row(ss, asof=None, min_days=120):
    dates = np.asarray(ss.date)
    cut = np.ones(len(dates), dtype=bool) if asof is None else (dates <= asof)
    idx = np.where(cut)[0]
    if len(idx) < min_days:
        return None
    dcut = [ss.date[i] for i in idx]
    ret = np.asarray(ss.ret_raw, dtype=float)[idx]             # split-clean daily return
    flags = calendar_flags(dcut)
    cond = condition_series(ret, flags)
    med_turn = getattr(ss, "med_turn", None)
    mt = float(med_turn[cut][-1]) if med_turn is not None and len(med_turn) else float("nan")
    return {
        "symbol": ss.symbol,
        "asof": dcut[-1],
        "n_days": len(idx),
        "expiry_ret_delta": cond["is_monthly_expiry"]["mean_delta_vs_all"],
        "expiry_week_ret_delta": cond["is_expiry_week"]["mean_delta_vs_all"],
        "pre_holiday_ret_delta": cond["is_pre_holiday"]["mean_delta_vs_all"],
        "post_holiday_ret_delta": cond["is_post_holiday"]["mean_delta_vs_all"],
        "n_expiry": cond["is_monthly_expiry"]["n"],
        "n_pre_holiday": cond["is_pre_holiday"]["n"],
        "med_turn": mt,
    }


def scan(con, asof=None, liq_floor=LIQ_FLOOR, min_days=120):
    out = []
    for sym in eq_symbols(con):
        ss = load_series(con, sym)
        if ss is None:
            continue
        row = symbol_row(ss, asof, min_days)
        if row is None:
            continue
        if liq_floor and not (np.isfinite(row["med_turn"]) and row["med_turn"] >= liq_floor):
            continue
        out.append(row)
    out.sort(key=lambda r: abs(r["pre_holiday_ret_delta"]) if np.isfinite(r["pre_holiday_ret_delta"]) else -9,
             reverse=True)
    return out


# ---------- selftest (offline, no DB) --------------------------------------------

def _weekday_calendar(start, end, holidays):
    """All weekdays in [start, end] minus ``holidays`` (a set of date objects), as ISO strings."""
    out, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in holidays:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def selftest() -> None:
    # A real 2026 calendar: all weekdays Jan-Feb, minus Republic Day (Mon 2026-01-26) and a
    # holiday ON Feb's expiry-Thursday (2026-02-26) to prove the roll-to-prior-trading-day.
    hols = {date(2026, 1, 26), date(2026, 2, 26)}
    dates = _weekday_calendar(date(2026, 1, 1), date(2026, 2, 28), hols)

    # 1. monthly expiry: Jan's last Thursday (2026-01-29) is a trading day -> expiry.
    #    Feb's last Thursday (2026-02-26) is a holiday -> rolls to Wed 2026-02-25.
    exp = monthly_expiry_dates(dates)
    assert "2026-01-29" in exp and "2026-02-25" in exp and "2026-02-26" not in exp, exp

    f = calendar_flags(dates)
    ix = {s: i for i, s in enumerate(dates)}

    # 2. expiry-day flag + days_to_expiry counts down to 0 at expiry.
    assert f["is_monthly_expiry"][ix["2026-01-29"]] and f["days_to_expiry"][ix["2026-01-29"]] == 0
    assert f["days_to_expiry"][ix["2026-01-28"]] == 1 and f["is_expiry_week"][ix["2026-01-28"]]

    # 3. Republic Day (Mon 2026-01-26 removed): Fri 01-23 is PRE-holiday, Tue 01-27 is POST-holiday.
    assert f["is_pre_holiday"][ix["2026-01-23"]] and f["is_post_holiday"][ix["2026-01-27"]]

    # 4. a normal weekend is NOT a holiday: Fri 2026-01-09 -> Mon 2026-01-12 (gap 3) unflagged.
    assert not f["is_pre_holiday"][ix["2026-01-09"]] and not f["is_post_holiday"][ix["2026-01-12"]]

    # 5. conditioning is descriptive + aligns: a synthetic +1% on every expiry day shows a
    #    positive expiry delta; flat elsewhere.
    n = len(dates)
    ret = np.zeros(n)
    ret[f["is_monthly_expiry"]] = 0.01
    cond = condition_series(ret, f)
    assert cond["is_monthly_expiry"]["mean_delta_vs_all"] > 0 and cond["is_monthly_expiry"]["n"] == 2

    print("CALENDAR_CONDITIONING (X-10) selftest OK")


def run():
    con = main_conn()
    rows = scan(con)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "calendar_conditioning.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"calendar_conditioning: {len(rows)} names conditioned -> {path} "
          f"(DESCRIPTIVE; read against seasonal_tape's null prior)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        run()
