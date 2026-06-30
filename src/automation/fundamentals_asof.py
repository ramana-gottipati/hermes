"""Point-in-time fundamentals reader — serve the patearn scorer / backtest from the
historical Screener archive (research.db.fundamentals_history) AS OF any date.

WHY: scoring.py reads only the live snapshot (hermes.db.fundamentals, ~58 syms) and many
patterns fall back to "no time-series available → estimated from current value". The archive
(1,983 syms, 2002→2026, point-in-time via report_date) lets us (a) BACKTEST the patearn score
with no look-ahead, and (b) replace those estimated signals with real trends.

POINT-IN-TIME CONTRACT: a period is only "known" on/after its EFFECTIVE knowable date. By default
that is the real BSE filing date captured in provenance_knowable (hermes.db), and where no real date
exists yet, a CONSERVATIVE calibrated lag (period_end + provenance's learned p95), NOT the producer's
leaky +90/+50 model. So every read here uses ONLY rows knowable by as_of — and a backtest can neither
peek at unfiled results (the old +50/+90 leaked ~12% for late filers) nor wait longer than the real
filing. Degrades gracefully to the stored report_date if provenance / hermes.db is unavailable (laptop).
See provenance.lag_audit() / calibrate_synthetic_lag() and docs/lane-d-knowable-at-and-veto-2026-06-28.md.

OUTPUT: a flat dict using the SAME keys scoring.score_fundamentals already consumes (so it is a
drop-in — ZERO changes to scoring.py), PLUS richer time-series keys (roce_rising_3y, opm_trend_3y,
interest_coverage, debtor_days, cash_conversion_cycle, profit_accel_ttm, …) for a future pattern
upgrade. Unknown keys are ignored by the current scorer.

NOT IN THE ARCHIVE: shareholding (promoter/pledge/FII/DII) — those keys are None here; they need a
separate quarterly shareholding feed. ROE % exists only for banks/NBFCs (the scorer doesn't use it
in any pattern, so this is cosmetic). PE/PB need a price — pass `price=` (the backtest has it from
the bhav cache); otherwise they are None.

Pure stdlib + sqlite3 (no numpy/pandas) so it imports cleanly in the production venv.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta
from typing import Optional

RESEARCH_DB = "/opt/hermes/data/research.db"
_HERMES_DB = RESEARCH_DB.replace("research.db", "hermes.db")   # provenance_knowable + calibration live here


# --- effective knowable date (real BSE date, else conservative calibrated lag) -------------

def _hermes_ro():
    """READ-ONLY connection to the main hermes.db (holds provenance_knowable + the lag calibration).
    None if absent (laptop / fresh box) → callers fall back to the stored modeled report_date."""
    if not os.path.exists(_HERMES_DB):
        return None
    try:
        return sqlite3.connect(f"file:{_HERMES_DB}?mode=ro", uri=True, timeout=20)
    except sqlite3.Error:
        return None


def _effective_date_map(symbol: str, periods: set, hconn, data_class: str) -> dict:
    """{(period_type, period_end): effective_knowable_date} for ``symbol`` — the REAL BSE filing date
    from provenance_knowable where captured, else period_end + the CONSERVATIVE calibrated lag (never
    the producer's leaky +90/+50). Returns {} (→ caller keeps the stored report_date) if provenance
    is unavailable, so this is always backward-compatible."""
    if hconn is None or not periods:
        return {}
    try:
        from src.automation import provenance
    except Exception:  # noqa: BLE001
        return {}
    sym = symbol.upper().strip()
    real: dict = {}
    try:
        for key, knew in hconn.execute(
                "SELECT key, knowable_at FROM provenance_knowable WHERE data_class=? AND symbol=?",
                (data_class, sym)):
            real[key] = knew
    except sqlite3.Error:
        return {}
    lags: dict = {}
    out: dict = {}
    for (ptype, pend) in periods:
        key = provenance.period_key(sym, ptype, pend)
        v = real.get(key)
        if v:
            out[(ptype, pend)] = str(v)[:10]
            continue
        if ptype not in lags:
            try:
                lags[ptype] = provenance._calibrated_lag(data_class, ptype, conn=hconn)
            except Exception:  # noqa: BLE001
                lags[ptype] = None
        if lags[ptype] is not None:
            try:
                out[(ptype, pend)] = (date.fromisoformat(str(pend)[:10]) + timedelta(days=int(lags[ptype]))).isoformat()
            except ValueError:
                pass
    return out

# Screener metric-name fallbacks: banks/NBFCs report Revenue / Financing Margin %
# instead of Sales / OPM %, and Borrowings is "Borrowing" on a few pages.
_SALES = ("Sales", "Revenue")
_OPM = ("OPM %", "Financing Margin %")
_BORROW = ("Borrowings", "Borrowing")


# --- loading ---------------------------------------------------------------

def _build_frame(rows, symbol: str, data_class: str, hconn, *, use_real_knowable: bool) -> dict:
    """Rows → {(ptype, metric): [(period_end, EFFECTIVE_date, value)]}. The third element is the
    EFFECTIVE knowable date (real BSE date, else conservative calibrated lag) when use_real_knowable,
    else the stored modeled report_date — so _known()'s `rdate <= as_of` gate becomes no-leak."""
    eff = {}
    if use_real_knowable:
        own = False
        if hconn == "__open__":
            hconn = _hermes_ro(); own = True
        periods = {(ptype, pend) for (ptype, _m, pend, _r, _v) in rows}
        eff = _effective_date_map(symbol, periods, hconn, data_class)
        if own and hconn is not None:
            hconn.close()
    frame: dict = {}
    for ptype, metric, pend, rdate, val in rows:
        # Normalise the knowable date to an ISO *date* (YYYY-MM-DD). The eff-map values are
        # already [:10] (see _effective_date_map); the stored-report_date fallback may carry a
        # timestamp ('2024-05-10 00:00:00') from some ingest paths, and an un-sliced string
        # compare against a [:10] as_of would lexicographically drop a period knowable *on*
        # as_of ('2024-05-10 00:00:00' <= '2024-05-10' is False). Slice both sides → no-leak. (CL-PROV-01)
        kdate = eff.get((ptype, pend), rdate)
        if kdate is not None:
            kdate = str(kdate)[:10]
        frame.setdefault((ptype, metric), []).append((pend, kdate, val))
    for key in frame:
        frame[key].sort(key=lambda t: t[0])
    return frame


def load_symbol_history(symbol: str, *, db_path: str = RESEARCH_DB, hconn="__open__",
                        use_real_knowable: bool = True) -> dict:
    """{(period_type, metric): [(period_end, effective_knowable_date, value), ...]} sorted by period_end.

    The effective date prefers the REAL BSE filing date (provenance_knowable), else period_end + the
    conservative calibrated lag. Pass ``use_real_knowable=False`` for the legacy stored-report_date
    behaviour, or a shared RO ``hconn`` (else one is opened per call) in a large backtest.

    One query per symbol — in a backtest, load the frame ONCE and call as_of_from_frame()
    for every rebalance date instead of re-querying.
    """
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT period_type, metric, period_end, report_date, value "
            "FROM fundamentals_history WHERE symbol=? AND value IS NOT NULL",
            (symbol.upper().strip(),)).fetchall()
    finally:
        con.close()
    return _build_frame(rows, symbol, "fundamentals_history", hconn, use_real_knowable=use_real_knowable)


def load_shareholding_history(symbol: str, *, db_path: str = RESEARCH_DB, hconn="__open__",
                              use_real_knowable: bool = True) -> dict:
    """Same shape as load_symbol_history, for research.db.shareholding_history (period_type 'Q':
    Promoters / FIIs / DIIs / Public / …). Returns {} if the table doesn't exist yet."""
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT period_type, metric, period_end, report_date, value "
            "FROM shareholding_history WHERE symbol=? AND value IS NOT NULL",
            (symbol.upper().strip(),)).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()
    return _build_frame(rows, symbol, "shareholding_history", hconn, use_real_knowable=use_real_knowable)


# --- point-in-time selection ----------------------------------------------

def _known(frame: dict, ptype: str, metric, as_of: str) -> list:
    """Sorted [(period_end, value)] for entries whose report_date <= as_of.

    `metric` may be a tuple of fallback names (first one with data wins).
    """
    names = (metric,) if isinstance(metric, str) else metric
    as_of = str(as_of)[:10]   # compare ISO date↔ISO date (frame dates are already [:10]; CL-PROV-01)
    for name in names:
        out = [(pend, val) for pend, rdate, val in frame.get((ptype, name), [])
               if rdate is not None and rdate <= as_of]
        if out:
            out.sort(key=lambda t: t[0])
            return out
    return []


def _latest(frame: dict, ptype: str, metric, as_of: str):
    series = _known(frame, ptype, metric, as_of)
    return series[-1][1] if series else None


# --- growth helpers --------------------------------------------------------

def _cagr(start, end, years):
    if start is None or end is None or start <= 0 or end <= 0 or years <= 0:
        return None
    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


def _ann_growth(series: list, n: int):
    """N-year CAGR from an annual [(period_end, value)] series (latest vs n periods back)."""
    if len(series) < n + 1:
        return None
    return _cagr(series[-1 - n][1], series[-1][1], n)


def _span_days(series: list) -> Optional[int]:
    """Days between the first and last period_end of `series` (None if unparseable)."""
    if len(series) < 2:
        return 0
    try:
        d0 = date.fromisoformat(str(series[0][0])[:10])
        d1 = date.fromisoformat(str(series[-1][0])[:10])
    except (ValueError, TypeError):
        return None
    return (d1 - d0).days


def _consecutive_4q(series: list) -> bool:
    """True only if the last 4 quarterly points span ~1 year (≤370d) → genuinely
    consecutive. A wider span means a gap was silently collapsed (missing filings),
    which would corrupt any TTM sum. CL-PROV-15."""
    if len(series) < 4:
        return False
    span = _span_days(series[-4:])
    return span is not None and span <= 370


def _ttm(series: list):
    """(ttm, prior_ttm) = sums of the last 4 and previous 4 quarterly values.
    Each window must be genuinely consecutive (≤370d span) or it is None — a
    collapsed gap would otherwise sum non-adjacent quarters. CL-PROV-15."""
    if len(series) < 4 or not _consecutive_4q(series):
        return None, None
    ttm = sum(v for _, v in series[-4:])
    prior = (sum(v for _, v in series[-8:-4])
             if len(series) >= 8 and _consecutive_4q(series[-8:-4])
             else None)
    return ttm, prior


# --- the reader ------------------------------------------------------------

def as_of_from_frame(frame: dict, as_of: str, *, symbol: Optional[str] = None,
                     company_name: Optional[str] = None, price: Optional[float] = None,
                     sh: Optional[dict] = None) -> Optional[dict]:
    """Compute the scorer dict AS OF `as_of` (YYYY-MM-DD) from a loaded history frame.

    Returns None if nothing was known by that date.
    """
    sales_a = _known(frame, "A", _SALES, as_of)
    np_a = _known(frame, "A", "Net Profit", as_of)
    if not sales_a and not np_a:
        return None

    roce_a = _known(frame, "A", "ROCE %", as_of)
    opm_a = _known(frame, "A", _OPM, as_of)
    sales_q = _known(frame, "Q", _SALES, as_of)
    np_q = _known(frame, "Q", "Net Profit", as_of)
    eps_q = _known(frame, "Q", "EPS in Rs", as_of)

    # Leverage & quality (latest known annual)
    borrow = _latest(frame, "A", _BORROW, as_of)
    eqcap = _latest(frame, "A", "Equity Capital", as_of)
    reserves = _latest(frame, "A", "Reserves", as_of)
    net_worth = (eqcap + reserves) if (eqcap is not None and reserves is not None) else None
    de = (borrow / net_worth) if (borrow is not None and net_worth and net_worth > 0) else None

    op_a = _latest(frame, "A", "Operating Profit", as_of)
    int_a = _latest(frame, "A", "Interest", as_of)
    icov = (op_a / int_a) if (op_a is not None and int_a and int_a > 0) else None

    # TTM growth (quarterly)
    sales_ttm, sales_ttm_prior = _ttm(sales_q)
    np_ttm, np_ttm_prior = _ttm(np_q)
    eps_ttm = sum(v for _, v in eps_q[-4:]) if _consecutive_4q(eps_q) else None  # CL-PROV-15
    sales_g_ttm = _cagr(sales_ttm_prior, sales_ttm, 1)
    profit_g_ttm = _cagr(np_ttm_prior, np_ttm, 1)

    # Quarterly profit acceleration: YoY of latest quarter minus YoY of prior quarter
    profit_accel = None
    if len(np_q) >= 6:
        yoy_now = _cagr(np_q[-5][1], np_q[-1][1], 1)
        yoy_prev = _cagr(np_q[-6][1], np_q[-2][1], 1)
        if yoy_now is not None and yoy_prev is not None:
            profit_accel = yoy_now - yoy_prev

    # ROCE / OPM trends
    roce = roce_a[-1][1] if roce_a else None
    roce_3y_avg = (sum(v for _, v in roce_a[-3:]) / len(roce_a[-3:])) if roce_a else None
    roce_rising_3y = (roce_a[-1][1] > roce_a[-4][1]) if len(roce_a) >= 4 else None
    opm_latest = opm_a[-1][1] if opm_a else None
    opm_trend_3y = (opm_a[-1][1] - opm_a[-4][1]) if len(opm_a) >= 4 else None

    # PE / PB require a price (annual EPS + net worth → shares → BVPS)
    pe = pb = None
    if price:
        if eps_ttm and eps_ttm > 0:
            pe = price / eps_ttm
        np_latest = np_a[-1][1] if np_a else None
        eps_latest_a = _latest(frame, "A", "EPS in Rs", as_of)
        if net_worth and np_latest and eps_latest_a:
            shares_cr = np_latest / eps_latest_a            # ₹cr / ₹ → cr shares
            bvps = (net_worth / shares_cr) if shares_cr else None
            if bvps and bvps > 0:
                pb = price / bvps

    # Shareholding from the separate quarterly feed (~3y depth; None if not collected yet).
    promoter = fii = dii = prom_rising = fii_rising = None
    if sh:
        prom_s = _known(sh, "Q", "Promoters", as_of)
        fii_s = _known(sh, "Q", "FIIs", as_of)
        dii_s = _known(sh, "Q", "DIIs", as_of)
        promoter = prom_s[-1][1] if prom_s else None
        fii = fii_s[-1][1] if fii_s else None
        dii = dii_s[-1][1] if dii_s else None
        if len(prom_s) >= 5:
            prom_rising = prom_s[-1][1] > prom_s[-5][1]      # promoter holding rose over ~1y
        if len(fii_s) >= 5:
            fii_rising = fii_s[-1][1] > fii_s[-5][1]         # FII holding rose over ~1y

    return {
        "symbol": symbol,
        "company_name": company_name,
        "as_of": as_of,
        "as_of_period_end": (sales_a or np_a)[-1][0],
        # --- keys scoring.score_fundamentals consumes (drop-in, no scoring.py change) ---
        "roce": roce,
        "roe": _latest(frame, "A", "ROE %", as_of),     # archive: banks/NBFCs only
        "pe": pe,
        "pb": pb,
        "debt_to_equity": de,
        "opm_latest": opm_latest,
        "eps_ttm": eps_ttm,
        "sales_growth_5y": _ann_growth(sales_a, 5),
        "sales_growth_3y": _ann_growth(sales_a, 3),
        "sales_growth_ttm": sales_g_ttm,
        "profit_growth_5y": _ann_growth(np_a, 5),
        "profit_growth_3y": _ann_growth(np_a, 3),
        "profit_growth_ttm": profit_g_ttm,
        # shareholding from the separate quarterly feed (pledge still needs BSE → None)
        "promoter_holding": promoter, "promoter_pledge": None,
        "fii_holding": fii, "dii_holding": dii,
        "promoter_rising_4q": prom_rising, "fii_rising_4q": fii_rising,
        # --- richer time-series keys for the pattern upgrade (ignored by current scorer) ---
        "roce_3y_avg": roce_3y_avg,
        "roce_rising_3y": roce_rising_3y,
        "opm_trend_3y": opm_trend_3y,
        "interest_coverage": icov,
        "debtor_days": _latest(frame, "A", "Debtor Days", as_of),
        "inventory_days": _latest(frame, "A", "Inventory Days", as_of),
        "cash_conversion_cycle": _latest(frame, "A", "Cash Conversion Cycle", as_of),
        "working_capital_days": _latest(frame, "A", "Working Capital Days", as_of),
        "profit_accel_ttm": profit_accel,
        "net_worth_cr": net_worth,
        "borrowings_cr": borrow,
    }


def as_of_fundamentals(symbol: str, as_of: str, *, price: Optional[float] = None,
                       db_path: str = RESEARCH_DB, use_real_knowable: bool = True) -> Optional[dict]:
    """Convenience: load a symbol's history and compute the as-of dict in one call. Shares ONE
    read-only hermes.db connection across both loads for the effective-date lookup."""
    hconn = _hermes_ro() if use_real_knowable else None
    try:
        frame = load_symbol_history(symbol, db_path=db_path, hconn=hconn, use_real_knowable=use_real_knowable)
        if not frame:
            return None
        sh = load_shareholding_history(symbol, db_path=db_path, hconn=hconn, use_real_knowable=use_real_knowable)
    finally:
        if hconn is not None:
            hconn.close()
    return as_of_from_frame(frame, as_of, symbol=symbol.upper().strip(), price=price, sh=sh)


def score_asof(symbol: str, as_of: str, *, price: Optional[float] = None,
               db_path: str = RESEARCH_DB) -> dict:
    """Point-in-time patearn score — feeds the as-of dict to the EXISTING scorer.

    Does NOT persist (backtest-safe; never writes pattern_scores).
    """
    from src.automation.scoring import score_fundamentals
    f = as_of_fundamentals(symbol, as_of, price=price, db_path=db_path)
    if not f:
        return {"error": f"no fundamentals known for {symbol} as of {as_of}", "symbol": symbol}
    return score_fundamentals(f)


if __name__ == "__main__":
    import json
    import sys

    sym = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    asof = sys.argv[2] if len(sys.argv) > 2 else "2026-06-23"
    px = float(sys.argv[3]) if len(sys.argv) > 3 else None

    data = as_of_fundamentals(sym, asof, price=px)
    print(json.dumps(data, indent=2, default=str))
    if data:
        from src.automation.scoring import score_fundamentals
        s = score_fundamentals(data)
        print(f"\n{sym} @ {asof}  →  TIER {s['tier']}  NS {s['ns_base']:.1f}% "
              f"({s['ns_pessimistic']:.1f}-{s['ns_optimistic']:.1f})  "
              f"QG {'PASS' if s['qg_pass'] else 'FAIL'}  PAC {s['pac']}/14")
