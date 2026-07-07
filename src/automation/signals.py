"""Per-stock rolling delivery-value signals.

For each (symbol, trade_date), compute:
  - Today's delivery_value_per_trade = (deliv_qty * close) / no_of_trades

  - LEGACY flat rolling averages over 5/10/30/60/90/180/365 trading days
    (kept for /dvpt single-stock detail history table)

  - D31 R-tier — flat rolling averages over CALENDAR-day windows:
      R1M  = avg DVPT over last  30 calendar days (excl today)
      R2M  =                     60
      R3M  =                     90
      R6M  =                    180
      R12M =                    360

  - D31 P-tier — avg of top-N DVPT within CALENDAR-day windows:
      P1M  = top  4 DVPT in last  30 calendar days
      P2M  = top  7         in last  60
      P3M  = top 12         in last  90
      P6M  = top 20         in last 180
      P12M = top 30         in last 360

  - D31 Institutional price zones — for every R/P baseline, the avg CLOSE
    on the same days (R: avg close over window; P: avg close on the
    top-N-by-DVPT days). Lets us read "where institutions transacted."

  - Scores: r_score / p_score = count of R/P baselines today's DVPT beats
  - trigger_rank = SS(5)/S(4)/A(3)/B(2)/C(1)/'-' from p_score
  - ATH-DVPT, hot_days_avg_price, near-break pointer (next_p_above + gap)

  - D43 Accumulation/distribution CHARACTER — delivery data is SIDE-BLIND (every
    delivered share was simultaneously bought AND sold), so DVPT/delivery reveal
    WHO transacted (size/ownership-intent) but NEVER which side initiated. Three
    independent axes separate strong-hand accumulation from strong-hands-
    distributing-to-retail:
      WHO       — deliv_value_ratio_1m_6m, trade_count_ratio_1m_6m (broadening vs
                  concentrated), avg_deliv_pct_1m/6m
      WHICH WAY — deliv_updown_ratio_3m, accum_price_drift_3m (price is the ONLY
                  direction-revealer; built on split-ADJUSTED closes)
      CONTEXT   — pct_from_52w_high, p_score persistence
    The numerics are STORED; the `accum_character` label is DERIVED (re-tunable
    via --relabel-character without a full backfill). See accum_character().

Stored nightly into stock_signals table; queries become instant lookups.

Usage:
    python -m src.automation.signals                        # compute today's row for every stock that has bhav data today
    python -m src.automation.signals --backfill             # compute signals for ALL historical days where missing
    python -m src.automation.signals --backfill-triggers    # recompute D28/D31 trigger fields on existing rows
    python -m src.automation.signals --symbol RELIANCE      # one stock only (for debugging)
"""

import argparse
import bisect
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from src.automation.adjust import adjusted_closes, adjustment_factors
from src.core.db import get_conn

# D31 windowing — calendar days (NOT trading days).
# Format: (label, calendar_days, top_n_for_power)
_WINDOWS = (
    ("1m",   30,  4),
    ("2m",   60,  7),
    ("3m",   90, 12),
    ("6m",  180, 20),
    ("12m", 360, 30),
)
_P_LABELS = ("P1M", "P2M", "P3M", "P6M", "P12M")

# D43 — per-symbol fetch window. 372 calendar days (~53 weeks) so the 52-week
# high has a full year of ADJUSTED closes to look back over (the DVPT R/P
# windows still slice their own ≤360-day cutoffs out of this superset).
_CHAR_FETCH_DAYS = 372

# D43 — corp-action anomaly guard for the up/down direction read. A real >30%
# single-day move is impossible under NSE circuit limits, so it's always an
# unadjusted corporate action — exclude that day from the up/down skew (same
# CC_THRESH as adjust.py / D36).
_CHAR_CC_THRESH = 0.30

# D43 — accumulation/distribution CHARACTER thresholds. TUNABLE DEFAULTS — the
# numerics are stored raw, so re-tuning these + running --relabel-character
# re-derives every label without recomputing the underlying measures.
_CHAR_THRESH = {
    "active_p_score": 2,    # p_score >= this ⇒ strong hands genuinely active
    "deliv_rising":   1.2,  # deliv_value_ratio_1m_6m >= ⇒ delivery picking up
    "broadening":     1.3,  # trade_count_ratio_1m_6m >= ⇒ retail crowd broadening
    "concentrated":   1.1,  # trade_count_ratio_1m_6m <= ⇒ concentrated (few hands)
    "up_skew":        1.30, # deliv_updown_ratio_3m >= ⇒ delivery skewed to up-days
    "down_skew":      0.77, # deliv_updown_ratio_3m <= ⇒ delivery skewed to down-days
    "price_up":       5.0,  # accum_price_drift_3m  >  ⇒ price advancing
    "price_down":    -5.0,  # accum_price_drift_3m  <  ⇒ price declining
    "near_high":    -10.0,  # pct_from_52w_high     >  ⇒ near the highs
    "off_high":     -20.0,  # pct_from_52w_high     <= ⇒ off highs / in a base
}

log = logging.getLogger("hermes.signals")


# --- D43 accumulation/distribution character (shared label brain) -----------
# Pure, side-effect-free helpers so the dashboard AND the Telegram bot derive
# IDENTICAL labels + plain-English reads from the stored numerics (DRY). The
# label rule is intentionally three-axis: delivery is side-blind, so we never
# collapse WHO / WHICH-WAY / CONTEXT into one number.

def _char_flags(p_score, trade_count_ratio_1m_6m, deliv_updown_ratio_3m,
                accum_price_drift_3m, pct_from_52w_high,
                deliv_value_ratio_1m_6m=None) -> Optional[dict]:
    """Boolean axis-flags from the raw numerics. None when the essential inputs
    (activity + price direction) are missing — those two are what make the
    label meaningful; the rest degrade gracefully to False."""
    if p_score is None or accum_price_drift_3m is None:
        return None
    T = _CHAR_THRESH
    return {
        "active":       p_score >= T["active_p_score"],
        "deliv_rising": deliv_value_ratio_1m_6m is not None and deliv_value_ratio_1m_6m >= T["deliv_rising"],
        "broadening":   trade_count_ratio_1m_6m is not None and trade_count_ratio_1m_6m >= T["broadening"],
        "concentrated": trade_count_ratio_1m_6m is not None and trade_count_ratio_1m_6m <= T["concentrated"],
        "up_skew":      deliv_updown_ratio_3m is not None and deliv_updown_ratio_3m >= T["up_skew"],
        "down_skew":    deliv_updown_ratio_3m is not None and deliv_updown_ratio_3m <= T["down_skew"],
        "price_up":     accum_price_drift_3m > T["price_up"],
        "price_down":   accum_price_drift_3m < T["price_down"],
        "price_flat":   T["price_down"] <= accum_price_drift_3m <= T["price_up"],
        "near_high":    pct_from_52w_high is not None and pct_from_52w_high > T["near_high"],
        "off_high":     pct_from_52w_high is not None and pct_from_52w_high <= T["off_high"],
    }


def accum_character(p_score, trade_count_ratio_1m_6m, deliv_updown_ratio_3m,
                    accum_price_drift_3m, pct_from_52w_high) -> Optional[str]:
    """Derive the accumulation/distribution CHARACTER label (D43). First match
    wins. Returns 'ACCUMULATION' / 'DISTRIBUTION' / 'CONSOLIDATION' / 'NEUTRAL',
    or None when the essential inputs are missing (rendered as '-').

    concentration (high DVPT, contained trade count, price firm) = strong hands
    accumulating; broadening (rising trade count, high total delivery, price
    stalling near highs) = strong hands distributing INTO a retail crowd."""
    f = _char_flags(p_score, trade_count_ratio_1m_6m, deliv_updown_ratio_3m,
                    accum_price_drift_3m, pct_from_52w_high)
    if f is None:
        return None
    if f["active"] and (f["price_down"] or (f["near_high"] and not f["price_up"])) \
            and (f["broadening"] or f["down_skew"]):
        return "DISTRIBUTION"
    if f["active"] and (f["price_up"] or f["price_flat"]) \
            and (f["concentrated"] or f["up_skew"]):
        return "ACCUMULATION"
    if (not f["active"]) and f["price_flat"]:
        return "CONSOLIDATION"
    return "NEUTRAL"


def accum_character_read(label, p_score, trade_count_ratio_1m_6m,
                         deliv_updown_ratio_3m, accum_price_drift_3m,
                         pct_from_52w_high, deliv_value_ratio_1m_6m=None) -> str:
    """Plain-English nuance composed on-read from the raw numerics (D43). Same
    helper for dashboard + bot so the wording never drifts."""
    f = _char_flags(p_score, trade_count_ratio_1m_6m, deliv_updown_ratio_3m,
                    accum_price_drift_3m, pct_from_52w_high, deliv_value_ratio_1m_6m)
    if not label or f is None:
        return ""
    if label == "ACCUMULATION":
        if f["price_up"] and f["up_skew"]:
            return "markup / advance — price rising, delivery skewed to up-days"
        if f["price_flat"] and f["concentrated"] and f["off_high"]:
            return "absorption — supply soaked up quietly in a base, few large hands"
        if f["price_flat"] and f["concentrated"]:
            return "quiet accumulation — concentrated delivery, price holding firm"
        return "accumulation — strong hands on the tape, price constructive"
    if label == "DISTRIBUTION":
        if f["broadening"] and f["near_high"]:
            return "possible distribution — retail crowding in near highs while price stalls"
        if f["price_down"]:
            return "distribution — heavy delivery on down-days, price rolling over"
        return "distribution risk — broadening crowd / down-day delivery skew"
    if label == "CONSOLIDATION":
        return "consolidation — no strong-hand activity, price range-bound"
    return "neutral — no clear accumulation or distribution signature"


def _ret_signs(adj: list) -> list:
    """Per-day direction sign from the ADJUSTED close series (oldest→newest):
    +1 up day, -1 down day, 0 flat / first day / corp-action anomaly excluded."""
    n = len(adj)
    signs = [0] * n
    for j in range(1, n):
        a0, a1 = adj[j - 1], adj[j]
        if a0 and a1 and a0 > 0:
            r = a1 / a0 - 1.0
            if abs(r) > _CHAR_CC_THRESH:
                signs[j] = 0          # unadjusted corp action — not a real day
            elif r > 0:
                signs[j] = 1
            elif r < 0:
                signs[j] = -1
    return signs


def _character_metrics(dates: list, adj: list, deliv_value: list,
                       num_trades: list, deliv_per: list, ret_sign: list,
                       values: list, i: int) -> dict:
    """Compute the 8 stored D43/N3 numerics for row index `i`, given full
    per-symbol arrays ordered OLDEST→NEWEST. Calendar-day windows (30/90/180)
    matching signals._WINDOWS; delivery ₹ is value-based (split-invariant);
    direction + drift + 52w-high use ADJUSTED closes; `values` is raw daily
    turnover (₹) for the N3 ticket-size ratio."""
    d = dates[i]
    lo30  = bisect.bisect_left(dates, _cutoff_date(d, 30))
    lo90  = bisect.bisect_left(dates, _cutoff_date(d, 90))
    lo180 = bisect.bisect_left(dates, _cutoff_date(d, 180))

    def _avg(arr, lo):
        vals = [arr[j] for j in range(lo, i + 1) if arr[j] is not None]
        return (sum(vals) / len(vals)) if vals else None

    # WHO — delivery ₹ trend, trade-count trend (breadth), delivery %.
    dv30, dv180 = _avg(deliv_value, lo30), _avg(deliv_value, lo180)
    deliv_value_ratio = (dv30 / dv180) if (dv30 is not None and dv180 and dv180 > 0) else None
    tc30, tc180 = _avg(num_trades, lo30), _avg(num_trades, lo180)
    trade_count_ratio = (tc30 / tc180) if (tc30 is not None and tc180 and tc180 > 0) else None
    avg_deliv_pct_1m = _avg(deliv_per, lo30)
    avg_deliv_pct_6m = _avg(deliv_per, lo180)

    # N3 (X-01): rupee ticket-size velocity — (Σvalue/Σtrades) 1m vs 6m, a ratio of
    # SUMS so zero-trade days can't skew a daily mean. Rupee-based (guardrail #5) so
    # split-invariant without adjustment; None before ~mid-2011 (num_trades NULL).
    # Descriptive only: the D89 study's surviving feature (Cliff's δ +0.329/+0.250
    # vs both controls) — the detector built on it FAILED its gate (1/4).
    def _ticket(lo):
        v = t = 0.0
        for j in range(lo, i + 1):
            if values[j] is not None and num_trades[j]:
                v += values[j]
                t += num_trades[j]
        return (v / t) if t > 0 else None

    tk30, tk180 = _ticket(lo30), _ticket(lo180)
    ticket_ratio = (tk30 / tk180) if (tk30 is not None and tk180 and tk180 > 0) else None

    # WHICH WAY — value-weighted up/down delivery skew over 90 cal days.
    up = down = 0.0
    for j in range(lo90, i + 1):
        s = ret_sign[j]
        v = deliv_value[j]
        if v is None or s == 0:
            continue
        if s > 0:
            up += v
        else:
            down += v
    if up == 0.0 and down == 0.0:
        updown = None
    elif down == 0.0:
        updown = 99.0                # up$ only — cap (avoid div-by-zero blow-up)
    elif up == 0.0:
        # CL-MDC-05: down$ only — floor symmetrically at 1/99 so the all-down
        # extreme mirrors the all-up cap of 99 (was 0.0, an asymmetric threshold
        # that made "pure distribution" indistinguishable from "merely weak").
        updown = 1.0 / 99.0
    else:
        updown = up / down

    # 3-month adjusted price drift (the direction-revealer). Base = the close
    # at/just-before ~90 calendar days ago.
    base_idx = bisect.bisect_right(dates, _cutoff_date(d, 90)) - 1
    drift = None
    if 0 <= base_idx < i and adj[base_idx] and adj[base_idx] > 0 and adj[i] is not None:
        drift = (adj[i] / adj[base_idx] - 1.0) * 100.0

    # CONTEXT — distance below the 52-week high (last ≤252 trading rows).
    lo52 = max(0, i - 251)
    highs = [adj[k] for k in range(lo52, i + 1) if adj[k] is not None]
    pct_from_52w_high = None
    if highs and adj[i] is not None:
        mx = max(highs)
        if mx > 0:
            pct_from_52w_high = (adj[i] / mx - 1.0) * 100.0

    return {
        "deliv_value_ratio_1m_6m": deliv_value_ratio,
        "trade_count_ratio_1m_6m": trade_count_ratio,
        "ticket_ratio_1m_6m": ticket_ratio,
        "avg_deliv_pct_1m": avg_deliv_pct_1m,
        "avg_deliv_pct_6m": avg_deliv_pct_6m,
        "deliv_updown_ratio_3m": updown,
        "accum_price_drift_3m": drift,
        "pct_from_52w_high": pct_from_52w_high,
    }


def _character_arrays(asc_rows: list) -> tuple:
    """Build the per-symbol arrays _character_metrics needs from bhav rows
    ordered OLDEST→NEWEST. Each row needs close/prev_close/deliv_qty/
    num_trades/deliv_per."""
    closes = [r["close"] for r in asc_rows]
    adj = adjusted_closes([{"close": r["close"], "prev_close": r["prev_close"]}
                           for r in asc_rows])
    # CL-MDC-01: delivery VALUE must be split-invariant over the 1m/6m ratio
    # window — use the ADJUSTED close (same basis as accum_price_drift), NOT the
    # raw close. A split inside the ≤180d window would otherwise put deliv_qty
    # and close on different scales and distort deliv_value_ratio_1m_6m / the
    # up-down skew. (The stored same-day rupee figures delivery_value_today /
    # _per_trade keep using raw close — they are true single-day turnover.)
    deliv_value = [
        (r["deliv_qty"] * adj[k])
        if (r["deliv_qty"] is not None and adj[k] is not None) else None
        for k, r in enumerate(asc_rows)
    ]
    num_trades = [r["num_trades"] for r in asc_rows]
    deliv_per = [r["deliv_per"] for r in asc_rows]
    values = [r["value"] for r in asc_rows]        # raw ₹ turnover (N3 ticket ratio)
    ret_sign = _ret_signs(adj)
    return adj, deliv_value, num_trades, deliv_per, ret_sign, values


def _delivery_value_per_trade(deliv_qty, close, num_trades) -> Optional[float]:
    """(deliv_qty * close) / num_trades. Returns None on any missing piece."""
    if deliv_qty is None or close is None or num_trades is None or num_trades == 0:
        return None
    if deliv_qty <= 0 or close <= 0:
        return None
    return (deliv_qty * close) / num_trades


def _delivery_value(deliv_qty, close) -> Optional[float]:
    if deliv_qty is None or close is None:
        return None
    return deliv_qty * close


def _cutoff_date(trade_date: str, days: int) -> str:
    """Calendar-day cutoff string for SQL filter. Inclusive lower bound."""
    dt = datetime.strptime(trade_date, "%Y-%m-%d")
    return (dt - timedelta(days=days)).strftime("%Y-%m-%d")


# --- D44 value-weighted institutional key price + entry/ticket/surge ---------
# ADDITIVE — a separate compute path that reuses the already-fetched window rows
# but never touches the D28/D31/D43 calculations. The key price refines the D31
# flat `avg_close_p*` zones (which equal-weight close on the top-N power days):
# here the BIG institutional day dominates the cost line (value-weighted) and we
# use the day's avg_price (where shares actually changed hands).

_KEY_BAND = (-1.0, 5.0)   # D44 asymmetric launch zone: close ∈ [key−1%, key+5%]


def is_near_key(gap) -> bool:
    """D44 — is a signed gap-to-key-price (%) within the asymmetric launch band?
    Price at/just-above the institutional cost, not far below. Tunable via
    _KEY_BAND so the band re-tunes on read with no backfill."""
    return gap is not None and _KEY_BAND[0] <= gap <= _KEY_BAND[1]


def _key_price_metrics(dates, dvpts, avg_prices, deliv_qtys, closes,
                       values, volumes, num_trades, factors, i) -> dict:
    """Compute the 15 stored D44 numerics for row index `i` from full per-symbol
    arrays ordered OLDEST→NEWEST.

      key_price_p{label}  = value-weighted mean price over the SAME top-N power-
                            DVPT days p_stats selects (weight = delivered VALUE
                            deliv_qty·raw_price, split-invariant; the averaged
                            price is SPLIT/BONUS-ADJUSTED to today's basis so a
                            split inside the window can't mix price scales) — the
                            big institutional day dominates the cost line.
      gap_to_key_p{label} = (today_close − key) / key · 100  (signed; −=below cost)
      avg_trade_qty             = volume / num_trades        (today, ticket size)
      avg_deliv_qty_per_trade   = deliv_qty / num_trades     (today)
      turnover_surge_{1m,3m,1y} = today value / avg(value over prior window)
    """
    d = dates[i]
    today_close = closes[i]
    out = {}
    for label, days, top_n in _WINDOWS:
        lo = bisect.bisect_left(dates, _cutoff_date(d, days))
        # prior days in window (exclude today=i), ranked by DVPT desc — the
        # SAME top-N power days p_stats picks for power_dvpt / avg_close_p.
        cand = [j for j in range(lo, i) if dvpts[j] is not None]
        cand.sort(key=lambda j: dvpts[j], reverse=True)
        num = den = 0.0
        for j in cand[:top_n]:
            raw = avg_prices[j] if avg_prices[j] is not None else closes[j]
            dq = deliv_qtys[j]
            if raw is None or raw <= 0 or dq is None:
                continue
            w = dq * raw                   # delivered VALUE (split-invariant) = the weight
            if w <= 0:
                continue
            num += (raw * factors[j]) * w  # average the SPLIT-ADJUSTED price (today basis) — no cross-split scale mixing
            den += w
        kp = (num / den) if den > 0 else None
        out[f"key_price_p{label}"] = kp
        out[f"gap_to_key_p{label}"] = (
            (today_close - kp) / kp * 100.0
            if (kp and kp > 0 and today_close is not None) else None
        )

    nt = num_trades[i]
    out["avg_trade_qty"] = (volumes[i] / nt) if (volumes[i] is not None and nt) else None
    out["avg_deliv_qty_per_trade"] = (deliv_qtys[i] / nt) if (deliv_qtys[i] is not None and nt) else None

    today_val = values[i]
    for label, days in (("1m", 30), ("3m", 90), ("1y", 360)):
        lo = bisect.bisect_left(dates, _cutoff_date(d, days))
        vals = [values[j] for j in range(lo, i) if values[j] is not None]
        avgv = (sum(vals) / len(vals)) if vals else None
        out[f"turnover_surge_{label}"] = (
            (today_val / avgv) if (today_val and avgv and avgv > 0) else None
        )
    return out


def _key_price_arrays(asc_rows) -> tuple:
    """Per-symbol arrays for _key_price_metrics from bhav rows OLDEST→NEWEST.
    Each row needs close/avg_price/value/volume/deliv_qty/num_trades."""
    dates      = [r["trade_date"] for r in asc_rows]
    dvpts      = [_delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
                  for r in asc_rows]
    avg_prices = [r["avg_price"] for r in asc_rows]
    deliv_qtys = [r["deliv_qty"] for r in asc_rows]
    closes     = [r["close"] for r in asc_rows]
    values     = [r["value"] for r in asc_rows]
    volumes    = [r["volume"] for r in asc_rows]
    num_trades = [r["num_trades"] for r in asc_rows]
    # split/bonus back-adjustment factors (newest row = 1.0) so key_price averages
    # prices on ONE basis — a split inside a window no longer mixes pre/post scales.
    factors    = adjustment_factors([{"close": r["close"],
                                      "prev_close": (r["prev_close"] if "prev_close" in r.keys() else None)}
                                     for r in asc_rows])
    return dates, dvpts, avg_prices, deliv_qtys, closes, values, volumes, num_trades, factors


def compute_signals_for_symbol_date(symbol: str, trade_date: str) -> Optional[dict]:
    """Compute the full signal row for one (symbol, trade_date).

    Fetches all bhav rows for the symbol within the last 360 calendar days,
    then slices per window (30/60/90/180/360 calendar days) for R-tier and
    P-tier baselines. D31 calendar-day windowing replaces D28's trading-day
    windowing.
    """
    # 372-day fetch (D43) — superset of the 360-day DVPT windows, giving the
    # 52-week high a full year of adjusted closes. prev_close + deliv_per feed
    # the D43 character axes (adjustment + delivery %).
    cutoff = _cutoff_date(trade_date, _CHAR_FETCH_DAYS)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT trade_date, close, prev_close, avg_price, value, volume,
                   deliv_qty, deliv_per, num_trades
            FROM bhavcopy_rows
            WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
              AND trade_date <= ? AND trade_date >= ?
            ORDER BY trade_date DESC
            """,
            (symbol, trade_date, cutoff),
        ).fetchall()

    if not rows:
        return None

    today_row = rows[0]
    if today_row["trade_date"] != trade_date:
        return None

    today_dvpt = _delivery_value_per_trade(
        today_row["deliv_qty"], today_row["close"], today_row["num_trades"]
    )
    today_dv = _delivery_value(today_row["deliv_qty"], today_row["close"])
    today_total = today_row["value"]

    # Build a per-day baseline list (excluding today) with both DVPT and close.
    # Each entry: (trade_date_str, dvpt, close).
    baseline_full = []
    for r in rows[1:]:
        dvpt = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        if dvpt is None:
            continue
        baseline_full.append((r["trade_date"], dvpt, r["close"]))

    n_baseline = len(baseline_full)

    # Legacy trading-day windows — used only for /dvpt history backward compat.
    legacy_dvpts = [x[1] for x in baseline_full]

    def legacy_flat_avg(td_window: int) -> Optional[float]:
        if td_window > len(legacy_dvpts):
            return None
        sub = legacy_dvpts[:td_window]
        return sum(sub) / len(sub)

    def safe_ratio(num, den) -> Optional[float]:
        if num is None or den is None or den <= 0:
            return None
        return num / den

    # D31 calendar-day windowing helpers.
    def window_subset(days: int):
        """Return the baseline rows within the last `days` calendar days.

        CL-MDC-14: this lexicographic `b[0] >= cutoff` window math is only
        correct because every trade_date is normalized to ISO YYYY-MM-DD at
        ingestion (all three bhavcopy parsers; UDIFF via bhavcopy._norm_iso_date
        as of CL-MDC-04). _cutoff_date emits the same ISO format, so string
        ordering == chronological ordering.
        """
        cutoff = _cutoff_date(trade_date, days)
        return [b for b in baseline_full if b[0] >= cutoff]

    def r_stats(days: int) -> tuple:
        """R-tier: flat avg DVPT + flat avg close over the calendar window."""
        sub = window_subset(days)
        if not sub:
            return None, None
        avg_dvpt = sum(b[1] for b in sub) / len(sub)
        closes = [b[2] for b in sub if b[2] is not None]
        avg_close = (sum(closes) / len(closes)) if closes else None
        return avg_dvpt, avg_close

    def p_stats(days: int, top_n: int) -> tuple:
        """P-tier: avg of top-N DVPT + avg close on those same top-N days."""
        sub = window_subset(days)
        if not sub:
            return None, None
        # Sort by DVPT descending, take top_n.
        top = sorted(sub, key=lambda b: b[1], reverse=True)[:top_n]
        if not top:
            return None, None
        avg_dvpt = sum(b[1] for b in top) / len(top)
        closes = [b[2] for b in top if b[2] is not None]
        avg_close = (sum(closes) / len(closes)) if closes else None
        return avg_dvpt, avg_close

    signal = {
        "symbol": symbol,
        "trade_date": trade_date,
        "delivery_value_today": today_dv,
        "total_value_today": today_total,
        "delivery_value_per_trade": today_dvpt,
        # LEGACY flat averages (trading-day windows; /dvpt history table)
        "avg_dvpt_5d":   legacy_flat_avg(5),
        "avg_dvpt_10d":  legacy_flat_avg(10),
        "avg_dvpt_30d":  legacy_flat_avg(30),
        "avg_dvpt_60d":  legacy_flat_avg(60),
        "avg_dvpt_90d":  legacy_flat_avg(90),
        "avg_dvpt_180d": legacy_flat_avg(180),
        "avg_dvpt_365d": legacy_flat_avg(365),
        "data_points_used": n_baseline,
    }

    # D31 R-tier + P-tier — calendar-day windows.
    for label, days, top_n in _WINDOWS:
        r_dvpt, r_close = r_stats(days)
        p_dvpt, p_close = p_stats(days, top_n)
        signal[f"avg_dvpt_{label}"]   = r_dvpt
        signal[f"power_dvpt_{label}"] = p_dvpt
        signal[f"avg_close_r{label}"] = r_close
        signal[f"avg_close_p{label}"] = p_close

    # Legacy ratios (kept for backward compat — point at the new calendar-day baselines).
    signal["ratio_today_vs_avg_30d"]  = safe_ratio(today_dvpt, signal["avg_dvpt_1m"])
    signal["ratio_today_vs_power_1m"] = safe_ratio(today_dvpt, signal["power_dvpt_1m"])
    signal["ratio_today_vs_power_3m"] = safe_ratio(today_dvpt, signal["power_dvpt_3m"])

    # --- Two-tier scoring + layered triggers (D28 logic, D31 baselines) ----
    r_keys = tuple(f"avg_dvpt_{lbl}"   for lbl, _, _ in _WINDOWS)
    p_keys = tuple(f"power_dvpt_{lbl}" for lbl, _, _ in _WINDOWS)

    r_score = _count_beaten(today_dvpt, [signal[k] for k in r_keys])
    p_score = _count_beaten(today_dvpt, [signal[k] for k in p_keys])
    signal["r_score"] = r_score
    signal["p_score"] = p_score
    signal["trigger_rank"] = _rank_from_p_score(p_score)

    next_above, gap = _next_p_above(today_dvpt, [signal[k] for k in p_keys], _P_LABELS)
    signal["next_p_above"] = next_above
    signal["gap_to_next_p_pct"] = gap

    # ATH-DVPT — true full-history check via stock_signals (not just the
    # 365-day window in `baseline`).
    if today_dvpt is not None:
        with get_conn() as conn:
            prow = conn.execute(
                """SELECT MAX(delivery_value_per_trade) AS pm
                   FROM stock_signals
                   WHERE symbol = ? AND trade_date < ?""",
                (symbol, trade_date),
            ).fetchone()
        prior_max = prow["pm"] if prow else None
        signal["is_ath_dvpt"] = 1 if (prior_max is None or today_dvpt > prior_max) else 0
    else:
        signal["is_ath_dvpt"] = None

    # Hot-day average close: avg close on last 10 days where that day's
    # DVPT > its own 1m power baseline.
    hot_avg = _hot_days_avg_close(rows[1:])
    signal["hot_days_avg_price"] = hot_avg
    if hot_avg is not None and today_row["close"] is not None and hot_avg > 0:
        signal["price_vs_hot_avg_pct"] = (today_row["close"] - hot_avg) / hot_avg * 100.0
    else:
        signal["price_vs_hot_avg_pct"] = None

    # --- D43 accumulation/distribution character --------------------------
    # `rows` is newest-first; the metric helpers want oldest→newest. Today is
    # the newest row, so its index in the ascending arrays is the last one.
    asc = list(reversed(rows))
    dates_a = [r["trade_date"] for r in asc]
    adj_a, dv_a, nt_a, dp_a, rs_a, val_a = _character_arrays(asc)
    cm = _character_metrics(dates_a, adj_a, dv_a, nt_a, dp_a, rs_a, val_a, len(asc) - 1)
    signal.update(cm)
    signal["accum_character"] = accum_character(
        signal["p_score"], cm["trade_count_ratio_1m_6m"], cm["deliv_updown_ratio_3m"],
        cm["accum_price_drift_3m"], cm["pct_from_52w_high"],
    )

    # --- D44 value-weighted key price + entry/ticket/surge (ADDITIVE) ------
    # Reuses the same oldest→newest `asc` rows; computes only the 15 NEW
    # columns and never touches anything set above.
    kp_arrays = _key_price_arrays(asc)
    signal.update(_key_price_metrics(*kp_arrays, len(asc) - 1))

    return signal


def _count_beaten(today_v, baselines: list) -> int:
    """How many baselines (non-None) does today's value strictly exceed."""
    if today_v is None:
        return 0
    return sum(1 for b in baselines if b is not None and today_v > b)


def _rank_from_p_score(p_score: int) -> str:
    """Pure count-based rank — no hidden ordering between P-windows (D28)."""
    return {5: "SS", 4: "S", 3: "A", 2: "B", 1: "C", 0: "-"}.get(p_score, "-")


def _next_p_above(today_v, p_baselines: list, p_labels: tuple) -> tuple:
    """Find the smallest P-baseline today does NOT beat (the next 'wall').

    Returns (label, gap_pct) where gap_pct is (today - p) / p * 100, negative
    means today is below the wall. None,None if today beats all five (clean SS).
    """
    if today_v is None:
        return None, None
    candidates = []
    for label, p in zip(p_labels, p_baselines):
        if p is None or p <= 0:
            continue
        if today_v <= p:
            candidates.append((p, label))
    if not candidates:
        return None, None
    # Smallest p-baseline today fails to beat = the closest wall above.
    candidates.sort()
    p, label = candidates[0]
    gap_pct = (today_v - p) / p * 100.0
    return label, gap_pct


def _hot_days_avg_close(prior_rows) -> Optional[float]:
    """Avg close on the last 10 prior days where that day's DVPT exceeded its
    own 1m power baseline (top-5 avg of preceding 22 days). Used to anchor the
    'price vs where smart money was buying' (D26 / D28). None if <1 hot day.
    """
    if not prior_rows:
        return None
    cap = min(len(prior_rows), 250)
    dvpts = []
    closes = []
    for r in prior_rows[:cap]:
        v = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        dvpts.append(v)
        closes.append(r["close"])

    hot_closes = []
    for i in range(len(dvpts)):
        today_v = dvpts[i]
        if today_v is None:
            continue
        baseline_window = [v for v in dvpts[i + 1 : i + 1 + 22] if v is not None]
        # CL-MDC-10: require a min count rather than the full 22 non-None points,
        # otherwise thin/illiquid names (with gappy DVPT) never register a hot
        # day at all. 15 still gives a meaningful top-5 power baseline.
        if len(baseline_window) < 15:
            continue
        top5 = sorted(baseline_window, reverse=True)[:5]
        if not top5:
            continue
        power_1m = sum(top5) / len(top5)
        if power_1m <= 0:
            continue
        if today_v / power_1m > 1.0 and closes[i] is not None and closes[i] > 0:
            hot_closes.append(closes[i])
            if len(hot_closes) == 10:
                break
    if not hot_closes:
        return None
    return sum(hot_closes) / len(hot_closes)


_SIGNAL_COLS = [
    "symbol", "trade_date",
    "delivery_value_today", "total_value_today", "delivery_value_per_trade",
    # Legacy trading-day windows (kept for /dvpt history table)
    "avg_dvpt_5d", "avg_dvpt_10d", "avg_dvpt_30d", "avg_dvpt_60d",
    "avg_dvpt_90d", "avg_dvpt_180d", "avg_dvpt_365d",
    # D31 R-tier (calendar-day flat averages: 30/60/90/180/360)
    "avg_dvpt_1m", "avg_dvpt_2m", "avg_dvpt_3m", "avg_dvpt_6m", "avg_dvpt_12m",
    # D31 P-tier (top-N within calendar-day window: 4/30, 7/60, 12/90, 20/180, 30/360)
    "power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m", "power_dvpt_6m", "power_dvpt_12m",
    # D31 institutional price zones (avg close on baseline days, R + P)
    "avg_close_r1m", "avg_close_r2m", "avg_close_r3m", "avg_close_r6m", "avg_close_r12m",
    "avg_close_p1m", "avg_close_p2m", "avg_close_p3m", "avg_close_p6m", "avg_close_p12m",
    # Legacy ratios
    "ratio_today_vs_avg_30d", "ratio_today_vs_power_1m", "ratio_today_vs_power_3m",
    "data_points_used",
    # Two-tier triggers (D28 logic, D31 baselines)
    "r_score", "p_score", "trigger_rank",
    "is_ath_dvpt", "hot_days_avg_price", "price_vs_hot_avg_pct",
    "next_p_above", "gap_to_next_p_pct",
    # D43 accumulation/distribution character (8 stored numerics + derived label;
    # ticket_ratio_1m_6m is the N3/X-01 addition)
    "deliv_value_ratio_1m_6m", "trade_count_ratio_1m_6m", "ticket_ratio_1m_6m",
    "avg_deliv_pct_1m", "avg_deliv_pct_6m",
    "deliv_updown_ratio_3m", "accum_price_drift_3m", "pct_from_52w_high",
    "accum_character",
    # D44 value-weighted key price + multi-horizon entry gap + ticket + surge
    "key_price_p1m", "key_price_p2m", "key_price_p3m", "key_price_p6m", "key_price_p12m",
    "gap_to_key_p1m", "gap_to_key_p2m", "gap_to_key_p3m", "gap_to_key_p6m", "gap_to_key_p12m",
    "avg_trade_qty", "avg_deliv_qty_per_trade",
    "turnover_surge_1m", "turnover_surge_3m", "turnover_surge_1y",
]


def store_signal(signal: dict) -> None:
    placeholders = ",".join("?" * len(_SIGNAL_COLS))
    sql = (
        f"INSERT OR REPLACE INTO stock_signals ({','.join(_SIGNAL_COLS)}) "
        f"VALUES ({placeholders})"
    )
    with get_conn() as conn:
        conn.execute(sql, [signal.get(c) for c in _SIGNAL_COLS])


def signal_exists(symbol: str, trade_date: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM stock_signals WHERE symbol = ? AND trade_date = ?",
            (symbol, trade_date),
        ).fetchone()
        return row is not None


# --- Modes -----------------------------------------------------------------

def compute_for_date(trade_date: str) -> int:
    """Compute signals for every symbol that traded on trade_date. Returns count."""
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            """SELECT DISTINCT symbol FROM bhavcopy_rows
               WHERE trade_date = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
               ORDER BY symbol""",
            (trade_date,),
        ).fetchall()]

    if not symbols:
        log.info("no symbols for %s — nothing to compute", trade_date)
        return 0

    log.info("computing signals for %d symbols on %s", len(symbols), trade_date)
    n = 0
    for i, sym in enumerate(symbols, 1):
        if signal_exists(sym, trade_date):
            continue
        sig = compute_signals_for_symbol_date(sym, trade_date)
        if sig and sig.get("delivery_value_per_trade") is not None:
            store_signal(sig)
            n += 1
        if i % 200 == 0:
            log.info("  progress: %d / %d", i, len(symbols))
    log.info("date %s done: %d signals stored", trade_date, n)
    return n


def run_today() -> tuple[bool, str]:
    """Compute signals for the most recent trade_date in bhavcopy_rows."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(trade_date) AS d FROM bhavcopy_rows"
        ).fetchone()
    if not row or not row["d"]:
        return False, "no bhav data found"
    n = compute_for_date(row["d"])
    return True, f"computed {n} signals for {row['d']}"


def run_backfill() -> tuple[int, int]:
    """Compute signals for every date in bhavcopy_dates where missing."""
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT trade_date FROM bhavcopy_dates ORDER BY trade_date ASC"
        ).fetchall()]
    log.info("backfill: %d dates to potentially process", len(dates))
    total = 0
    for d in dates:
        n = compute_for_date(d)
        total += n
        time.sleep(0.05)  # let other DB writes through
    return len(dates), total


# --- Two-tier + price-zone trigger backfill (D28 + D31) --------------------

def _backfill_triggers_for_symbol(conn, symbol: str) -> int:
    """For one symbol: walk every (symbol, trade_date) in stock_signals and
    populate ALL D28 + D31 fields (R/P-tier baselines under calendar-day
    windowing, scores, rank, ATH, hot-day, near-break, AND the 10 institutional
    price-zone columns). Per-symbol bulk fetch + batch UPDATE.
    """
    bhav = conn.execute(
        """SELECT trade_date, close, prev_close, deliv_qty, deliv_per, num_trades
           FROM bhavcopy_rows
           WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
           ORDER BY trade_date ASC""",
        (symbol,),
    ).fetchall()
    if not bhav:
        return 0

    n = len(bhav)
    dvpts  = [None] * n
    closes = [None] * n
    dates  = [None] * n
    for i, r in enumerate(bhav):
        dvpts[i]  = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        closes[i] = r["close"]
        dates[i]  = r["trade_date"]
    date_to_idx = {d: i for i, d in enumerate(dates)}

    # D43 character arrays (oldest→newest, matching `bhav`/`dates` ordering).
    char_adj, char_dv, char_nt, char_dp, char_rs, char_val = _character_arrays(bhav)

    # Running ATH-DVPT max over strictly-prior history.
    prior_max = None

    sig_dates = [r["trade_date"] for r in conn.execute(
        "SELECT trade_date FROM stock_signals WHERE symbol = ? ORDER BY trade_date ASC",
        (symbol,),
    ).fetchall()]

    updates = []
    for d in sig_dates:
        i = date_to_idx.get(d)
        if i is None:
            continue
        today_v = dvpts[i]
        # ATH check uses strictly-prior values.
        # CL-MDC-02: a symbol's FIRST-EVER row is an all-time-high by definition
        # (nothing precedes it). Match the realtime path (signals.py:549) and the
        # in-memory MTF path, which both set 1 when prior_max is None — backfill
        # used to set 0 here, disagreeing with realtime for the very first row.
        if today_v is not None:
            is_ath = 1 if (prior_max is None or today_v > prior_max) else 0
            if prior_max is None or today_v > prior_max:
                prior_max = today_v
        else:
            is_ath = None

        # Build the strictly-prior baseline list for THIS date `d`.
        # We need (date, dvpt, close) for every prior trade with non-None dvpt.
        prior = []
        for j in range(i):
            if dvpts[j] is None:
                continue
            prior.append((dates[j], dvpts[j], closes[j]))

        # Slice helpers — calendar-day windows on the prior list.
        def window_subset(days: int):
            cutoff = _cutoff_date(d, days)
            return [x for x in prior if x[0] >= cutoff]

        def r_stats(days: int):
            sub = window_subset(days)
            if not sub:
                return None, None
            avg_dvpt  = sum(x[1] for x in sub) / len(sub)
            cls       = [x[2] for x in sub if x[2] is not None]
            avg_close = (sum(cls) / len(cls)) if cls else None
            return avg_dvpt, avg_close

        def p_stats(days: int, top_n: int):
            sub = window_subset(days)
            if not sub:
                return None, None
            top = sorted(sub, key=lambda x: x[1], reverse=True)[:top_n]
            if not top:
                return None, None
            avg_dvpt  = sum(x[1] for x in top) / len(top)
            cls       = [x[2] for x in top if x[2] is not None]
            avg_close = (sum(cls) / len(cls)) if cls else None
            return avg_dvpt, avg_close

        r_dvpts  = []
        r_closes = []
        p_dvpts  = []
        p_closes = []
        for _label, win_days, top_n in _WINDOWS:
            rd, rc = r_stats(win_days)
            pd, pc = p_stats(win_days, top_n)
            r_dvpts.append(rd);  r_closes.append(rc)
            p_dvpts.append(pd);  p_closes.append(pc)

        r_score = _count_beaten(today_v, r_dvpts)
        p_score = _count_beaten(today_v, p_dvpts)
        rank = _rank_from_p_score(p_score)
        next_above, gap = _next_p_above(today_v, p_dvpts, _P_LABELS)

        # Hot-days avg close (same definition as D28 — last 10 prior days
        # where that day's DVPT exceeded its own 1m power baseline of
        # top-5 of the 22 trading days immediately preceding it).
        hot_closes = []
        j = i - 1
        while j >= 0 and len(hot_closes) < 10:
            v_j = dvpts[j]
            if v_j is not None and (j - 22) >= 0:
                sub = [v for v in dvpts[j - 22 : j] if v is not None]
                if len(sub) >= 22:
                    top5 = sorted(sub, reverse=True)[:5]
                    p1m_j = sum(top5) / len(top5)
                    if p1m_j > 0 and v_j / p1m_j > 1.0 and closes[j] is not None and closes[j] > 0:
                        hot_closes.append(closes[j])
            j -= 1
        hot_avg = (sum(hot_closes) / len(hot_closes)) if hot_closes else None
        if hot_avg is not None and closes[i] is not None and hot_avg > 0:
            pvh = (closes[i] - hot_avg) / hot_avg * 100.0
        else:
            pvh = None

        # D43 accumulation/distribution character for this date.
        cm = _character_metrics(dates, char_adj, char_dv, char_nt, char_dp, char_rs, char_val, i)
        clabel = accum_character(
            p_score, cm["trade_count_ratio_1m_6m"], cm["deliv_updown_ratio_3m"],
            cm["accum_price_drift_3m"], cm["pct_from_52w_high"],
        )

        updates.append((
            # avg_dvpt_1m..12m (R-tier DVPT baselines, calendar-day)
            r_dvpts[0], r_dvpts[1], r_dvpts[2], r_dvpts[3], r_dvpts[4],
            # power_dvpt_1m..12m (P-tier DVPT baselines, calendar-day, new top-N)
            p_dvpts[0], p_dvpts[1], p_dvpts[2], p_dvpts[3], p_dvpts[4],
            # avg_close_r1m..r12m (R-tier price zones)
            r_closes[0], r_closes[1], r_closes[2], r_closes[3], r_closes[4],
            # avg_close_p1m..p12m (P-tier price zones)
            p_closes[0], p_closes[1], p_closes[2], p_closes[3], p_closes[4],
            # Scores + rank + ATH + hot + near-break
            r_score, p_score, rank,
            is_ath, hot_avg, pvh,
            next_above, gap,
            # D43 character — 8 numerics (incl. N3 ticket) + derived label
            cm["deliv_value_ratio_1m_6m"], cm["trade_count_ratio_1m_6m"],
            cm["ticket_ratio_1m_6m"],
            cm["avg_deliv_pct_1m"], cm["avg_deliv_pct_6m"],
            cm["deliv_updown_ratio_3m"], cm["accum_price_drift_3m"],
            cm["pct_from_52w_high"], clabel,
            # WHERE clause
            symbol, d,
        ))

    if updates:
        conn.executemany(
            """UPDATE stock_signals
                  SET avg_dvpt_1m   = ?, avg_dvpt_2m   = ?, avg_dvpt_3m   = ?,
                      avg_dvpt_6m   = ?, avg_dvpt_12m  = ?,
                      power_dvpt_1m = ?, power_dvpt_2m = ?, power_dvpt_3m = ?,
                      power_dvpt_6m = ?, power_dvpt_12m = ?,
                      avg_close_r1m = ?, avg_close_r2m = ?, avg_close_r3m = ?,
                      avg_close_r6m = ?, avg_close_r12m = ?,
                      avg_close_p1m = ?, avg_close_p2m = ?, avg_close_p3m = ?,
                      avg_close_p6m = ?, avg_close_p12m = ?,
                      r_score = ?, p_score = ?, trigger_rank = ?,
                      is_ath_dvpt = ?, hot_days_avg_price = ?, price_vs_hot_avg_pct = ?,
                      next_p_above = ?, gap_to_next_p_pct = ?,
                      deliv_value_ratio_1m_6m = ?, trade_count_ratio_1m_6m = ?,
                      ticket_ratio_1m_6m = ?,
                      avg_deliv_pct_1m = ?, avg_deliv_pct_6m = ?,
                      deliv_updown_ratio_3m = ?, accum_price_drift_3m = ?,
                      pct_from_52w_high = ?, accum_character = ?
                WHERE symbol = ? AND trade_date = ?""",
            updates,
        )
    return len(updates)


def run_backfill_triggers() -> tuple[int, int]:
    """Populate all D28 two-tier columns for every existing stock_signals row.

    Per-symbol bulk-load → batch UPDATE. Expected runtime ~20-30 min on the
    VPS for the current 2.35M-row baseline.
    """
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            "SELECT DISTINCT symbol FROM stock_signals ORDER BY symbol"
        ).fetchall()]
    log.info("backfill-triggers: %d symbols to walk", len(symbols))

    total_rows = 0
    for k, sym in enumerate(symbols, 1):
        with get_conn() as conn:
            try:
                total_rows += _backfill_triggers_for_symbol(conn, sym)
            except Exception as e:
                log.warning("backfill-triggers failed for %s: %s", sym, e)
        if k % 100 == 0:
            log.info("  progress: %d / %d symbols, %d rows updated", k, len(symbols), total_rows)
    log.info("backfill-triggers complete: %d symbols, %d rows updated",
             len(symbols), total_rows)
    return len(symbols), total_rows


# --- Character relabel (D43) — fast threshold re-tuning, no full backfill ----

def run_relabel_character() -> tuple[int, int]:
    """Recompute ONLY `accum_character` from the already-stored numerics for
    every stock_signals row. Use after editing _CHAR_THRESH — re-derives every
    label in seconds without touching the (expensive) underlying measures.
    Per-symbol batches keep memory bounded on the VPS."""
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            "SELECT DISTINCT symbol FROM stock_signals ORDER BY symbol"
        ).fetchall()]
    log.info("relabel-character: %d symbols to relabel", len(symbols))

    total = 0
    for k, sym in enumerate(symbols, 1):
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT trade_date, p_score, trade_count_ratio_1m_6m,
                          deliv_updown_ratio_3m, accum_price_drift_3m, pct_from_52w_high
                   FROM stock_signals WHERE symbol = ?""",
                (sym,),
            ).fetchall()
            ups = [
                (accum_character(r["p_score"], r["trade_count_ratio_1m_6m"],
                                 r["deliv_updown_ratio_3m"], r["accum_price_drift_3m"],
                                 r["pct_from_52w_high"]),
                 sym, r["trade_date"])
                for r in rows
            ]
            if ups:
                conn.executemany(
                    "UPDATE stock_signals SET accum_character = ? "
                    "WHERE symbol = ? AND trade_date = ?", ups)
                total += len(ups)
        if k % 200 == 0:
            log.info("  relabel progress: %d / %d symbols", k, len(symbols))
    log.info("relabel-character complete: %d symbols, %d rows", len(symbols), total)
    return len(symbols), total


# --- D44 key-price backfill — ADDITIVE, UPDATE-only (never INSERT OR REPLACE) -

def _backfill_keyprice_for_symbol(conn, symbol: str) -> int:
    """Populate ONLY the 15 D44 columns (key price / entry gap / ticket / surge)
    for every existing stock_signals row of `symbol`. Pure additive UPDATE — it
    touches no other column, so all D28/D31/D43 values stay byte-identical."""
    bhav = conn.execute(
        """SELECT trade_date, close, prev_close, avg_price, value, volume, deliv_qty, num_trades
           FROM bhavcopy_rows
           WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
           ORDER BY trade_date ASC""",
        (symbol,),
    ).fetchall()
    if not bhav:
        return 0

    arrays = _key_price_arrays(bhav)
    dates = arrays[0]
    date_to_idx = {d: j for j, d in enumerate(dates)}

    sig_dates = [r["trade_date"] for r in conn.execute(
        "SELECT trade_date FROM stock_signals WHERE symbol = ? ORDER BY trade_date ASC",
        (symbol,),
    ).fetchall()]

    updates = []
    for d in sig_dates:
        i = date_to_idx.get(d)
        if i is None:
            continue
        m = _key_price_metrics(*arrays, i)
        updates.append((
            m["key_price_p1m"], m["key_price_p2m"], m["key_price_p3m"],
            m["key_price_p6m"], m["key_price_p12m"],
            m["gap_to_key_p1m"], m["gap_to_key_p2m"], m["gap_to_key_p3m"],
            m["gap_to_key_p6m"], m["gap_to_key_p12m"],
            m["avg_trade_qty"], m["avg_deliv_qty_per_trade"],
            m["turnover_surge_1m"], m["turnover_surge_3m"], m["turnover_surge_1y"],
            symbol, d,
        ))

    if updates:
        conn.executemany(
            """UPDATE stock_signals
                  SET key_price_p1m = ?, key_price_p2m = ?, key_price_p3m = ?,
                      key_price_p6m = ?, key_price_p12m = ?,
                      gap_to_key_p1m = ?, gap_to_key_p2m = ?, gap_to_key_p3m = ?,
                      gap_to_key_p6m = ?, gap_to_key_p12m = ?,
                      avg_trade_qty = ?, avg_deliv_qty_per_trade = ?,
                      turnover_surge_1m = ?, turnover_surge_3m = ?, turnover_surge_1y = ?
                WHERE symbol = ? AND trade_date = ?""",
            updates,
        )
    return len(updates)


def run_backfill_keyprice() -> tuple[int, int]:
    """D44 ADDITIVE backfill of the 15 key-price/ticket/surge columns for every
    existing stock_signals row. UPDATE-only — deliberately does NOT re-run
    --backfill-triggers (that would needlessly rewrite established values)."""
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            "SELECT DISTINCT symbol FROM stock_signals ORDER BY symbol"
        ).fetchall()]
    log.info("backfill-keyprice: %d symbols to walk", len(symbols))

    total = 0
    for k, sym in enumerate(symbols, 1):
        with get_conn() as conn:
            try:
                total += _backfill_keyprice_for_symbol(conn, sym)
            except Exception as e:
                log.warning("backfill-keyprice failed for %s: %s", sym, e)
        if k % 200 == 0:
            log.info("  keyprice progress: %d / %d symbols, %d rows", k, len(symbols), total)
    log.info("backfill-keyprice complete: %d symbols, %d rows", len(symbols), total)
    return len(symbols), total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--backfill-triggers", action="store_true",
                   help="Populate D28 two-tier columns (r_score, p_score, "
                        "trigger_rank, ATH, hot-day avg, near-break) AND the D43 "
                        "accumulation/distribution character (7 numerics + label) "
                        "for every existing stock_signals row. Per-symbol bulk "
                        "fetch + UPDATE.")
    p.add_argument("--relabel-character", action="store_true",
                   help="Recompute ONLY accum_character from stored numerics "
                        "(fast — for re-tuning _CHAR_THRESH without a full backfill).")
    p.add_argument("--backfill-keyprice", action="store_true",
                   help="D44 ADDITIVE backfill — populate ONLY the 15 key-price / "
                        "entry-gap / ticket-size / turnover-surge columns via "
                        "UPDATE. Never rewrites D28/D31/D43 values.")
    p.add_argument("--date", type=str, help="YYYY-MM-DD")
    p.add_argument("--symbol", type=str, help="compute one symbol's latest signal")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.symbol:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT MAX(trade_date) AS d FROM bhavcopy_rows WHERE symbol = ?",
                (args.symbol.upper(),),
            ).fetchone()
        if not row or not row["d"]:
            log.warning("no bhav data for %s", args.symbol)
            return
        sig = compute_signals_for_symbol_date(args.symbol.upper(), row["d"])
        if sig:
            store_signal(sig)
            log.info("computed signal for %s @ %s: dvpt=%.0f ratio_power_1m=%s",
                     args.symbol, row["d"],
                     sig.get("delivery_value_per_trade") or 0,
                     sig.get("ratio_today_vs_power_1m"))
    elif args.backfill:
        n_dates, total = run_backfill()
        log.info("backfill complete: %d dates, %d signals stored", n_dates, total)
    elif args.backfill_triggers:
        n_syms, n_rows = run_backfill_triggers()
        log.info("trigger backfill complete: %d symbols, %d rows updated",
                 n_syms, n_rows)
    elif args.relabel_character:
        n_syms, n_rows = run_relabel_character()
        log.info("character relabel complete: %d symbols, %d rows updated",
                 n_syms, n_rows)
    elif args.backfill_keyprice:
        n_syms, n_rows = run_backfill_keyprice()
        log.info("key-price backfill complete: %d symbols, %d rows updated",
                 n_syms, n_rows)
    elif args.date:
        compute_for_date(args.date)
    else:
        ok, msg = run_today()
        log.info(msg)


def backfill_ticket_ratio_latest() -> int:
    """N3 one-off: populate ticket_ratio_1m_6m for the LATEST trade_date only
    (additive UPDATE — the nightly forward-fills from tonight; history stays NULL
    per the space doctrine and recomputes on-read from bhav when a study needs it).
    Reuses _character_metrics' exact window math via minimal arrays."""
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) d FROM stock_signals").fetchone()
        d = row["d"]
        syms = [r["symbol"] for r in conn.execute(
            "SELECT symbol FROM stock_signals WHERE trade_date = ? "
            "AND ticket_ratio_1m_6m IS NULL", (d,)).fetchall()]
    log.info("ticket-ratio latest fill: %s, %d symbols", d, len(syms))
    n = 0
    for k, sym in enumerate(syms, 1):
        cutoff = _cutoff_date(d, 190)
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT trade_date, value, num_trades FROM bhavcopy_rows
                   WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
                     AND trade_date <= ? AND trade_date >= ? ORDER BY trade_date ASC""",
                (sym, d, cutoff)).fetchall()
            if not rows or rows[-1]["trade_date"] != d:
                continue
            dates = [r["trade_date"] for r in rows]
            vals = [r["value"] for r in rows]
            nts = [r["num_trades"] for r in rows]
            none_l = [None] * len(rows)
            cm = _character_metrics(dates, none_l, none_l, nts, none_l,
                                    [0] * len(rows), vals, len(rows) - 1)
            tk = cm["ticket_ratio_1m_6m"]
            if tk is not None:
                conn.execute("UPDATE stock_signals SET ticket_ratio_1m_6m = ? "
                             "WHERE symbol = ? AND trade_date = ?", (tk, sym, d))
                n += 1
        if k % 300 == 0:
            log.info("  ticket fill: %d/%d", k, len(syms))
    log.info("ticket-ratio latest fill done: %d rows updated", n)
    return n


if __name__ == "__main__":
    import sys as _sys
    if "--fill-ticket-latest" in _sys.argv:
        backfill_ticket_ratio_latest()
    else:
        main()
