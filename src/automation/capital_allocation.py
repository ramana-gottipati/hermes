"""Capital-allocation quality score (Dataset "C" — the free, derived P1).

Answers: has management compounded *incremental* capital well, or just grown size?
This is a DERIVED layer over fundamentals we already hold (research.db.fundamentals_history)
— no new data acquisition. Codex/Claude ROI debate verdict: build C first (free, days),
then A (insider/promoter), then B (credit ratings). See codex-bridge/DISCUSSION-dataset-roi.md.

What it computes (all PIT-safe via fundamentals_asof effective-knowable dates):
  - ROIIC     : incremental return on incremental capital = Δ operating profit / Δ capital employed
  - ROCE level + trend : is deployed capital productive, and improving?
  - dilution drag       : PAT CAGR − EPS CAGR (shares quietly issued to fund growth?)
  - debt-funding share  : share of incremental capital that came from borrowings (fragility)
  - growth efficiency   : PAT CAGR / capital-employed CAGR (earnings growth per unit capital growth)

Capital employed = (Equity Capital + Reserves) + Borrowings, per year, from fundamentals_history.
The HARD version (M&A-outcome attribution, buyback/dividend interpretation) is deferred until
dataset E exists — see the brief. This is the honest "easy version".

Scoring philosophy (per Ramana's no-static-thresholds principle):
  - raw metrics are stored verbatim (nothing discarded → every value is a benchmark)
  - the composite uses smooth logistic maps around documented ECONOMIC anchors (e.g. ROIIC
    centred on ~12% ≈ nominal cost of capital), not arbitrary cliffs
  - ca_tier is a CROSS-SECTIONAL percentile band (relative), filled in the batch pass — not a
    fixed cutoff.

CLI:
  python -m src.automation.capital_allocation --selftest          # synthetic math checks, no DB
  python -m src.automation.capital_allocation --inspect RELIANCE  # print available metric keys
  python -m src.automation.capital_allocation --symbol RELIANCE   # score one, print, no persist
  python -m src.automation.capital_allocation --backfill          # score full universe + percentile
  python -m src.automation.capital_allocation --limit 200         # cap symbols this run
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from src.automation.fundamentals_asof import (
    RESEARCH_DB,
    _cagr,
    _known,
    load_symbol_history,
)
from src.core.db import get_conn

log = logging.getLogger("hermes.capital_allocation")

# --- metric-name fallbacks (Screener section headers vary) -----------------
_SALES = ("Sales", "Revenue", "Total Revenue", "Net Sales", "Sales+")
_NPAT = ("Net Profit", "Net profit", "PAT", "Profit after tax")
_OPRO = ("Operating Profit", "EBIT", "Profit before tax")  # EBIT proxy, PBT last resort
_ROCE = ("ROCE %", "ROCE", "Return on capital employed %")
_EQCAP = ("Equity Capital", "Equity Share Capital", "Share Capital")
_RESV = ("Reserves", "Reserves and Surplus", "Other Equity")
_BORR = ("Borrowings", "Borrowing", "Total Debt", "Debt")
_EPS = ("EPS in Rs", "EPS", "Adjusted EPS in Rs", "EPS in Rs.")

# --- economic anchors for the smooth component maps (documented, not cliffs)
_ANCHORS = {
    "roiic": (12.0, 0.10),        # centre ≈ nominal cost of capital (India ~12%)
    "roce_level": (15.0, 0.12),   # ROCE ~15% ≈ decent; smooth around it
    "roce_trend": (0.0, 1.0),     # slope pp/yr; rising is good
    "dilution": (1.0, 0.60),      # PAT−EPS CAGR gap of ~1pp/yr tolerable (INVERTED)
    "dilution_eqcap": (3.0, 0.30),  # fallback: equity-capital CAGR >~3%/yr signals issuance (INVERTED)
    "debt_share": (50.0, 0.05),   # >50% of growth debt-funded starts to hurt (INVERTED)
    "growth_eff": (1.0, 1.50),    # PAT CAGR / CE CAGR; >1 = earnings outgrew capital
    # financial (bank/NBFC) model — ROCE/ROIIC are meaningless for lenders (leverage IS the business)
    "roe_level": (13.0, 0.15),    # ROE ~13-15% ≈ decent for a lender
    "roe_trend": (0.0, 0.80),     # ROE slope pp/yr
    "roa_level": (1.5, 0.60),     # ROA ~1.5%+ (banks ~1%, good NBFCs 2-4%)
}
_WEIGHTS = {
    "roiic": 0.30,
    "roce_level": 0.20,
    "roce_trend": 0.12,
    "dilution": 0.16,
    "debt_share": 0.12,
    "growth_eff": 0.10,
}
# financial model weights (keys are component names produced by score_metrics for model='financial')
_FIN_WEIGHTS = {
    "roe_level": 0.35,
    "roe_trend": 0.15,
    "roa_level": 0.20,
    "dilution": 0.20,
    "growth_eff": 0.10,
}
_FIN_MARKERS = ("Financing Profit", "Financing Margin %")  # Screener rows unique to lenders
_TOTAL_ASSETS = ("Total Assets", "Total assets")
_MIN_YEARS = 3          # aligned annual points required for incremental metrics
_MIN_SPAN = 2           # calendar-year span required
_TIER_BANDS = [(80, "EXCELLENT"), (60, "GOOD"), (40, "AVERAGE"), (20, "WEAK"), (0, "POOR")]


# --- pure math helpers (unit-testable, no DB) ------------------------------

def _logistic(x: float, x0: float, k: float) -> float:
    """Smooth 0..100 map. score(x0)=50, increasing in x."""
    z = -k * (x - x0)
    if z > 60:
        return 0.0
    if z < -60:
        return 100.0
    return 100.0 / (1.0 + math.exp(z))


def _year(period_end: str) -> int:
    return int(str(period_end)[:4])


def _smap(series: list) -> dict:
    """[(period_end, value)] -> {period_end[:10]: value} (last write wins on dup)."""
    return {str(pe)[:10]: v for pe, v in series if v is not None}


def _slope_per_year(points: list) -> Optional[float]:
    """Least-squares slope of value vs calendar-year for [(period_end, value)]."""
    pts = [(_year(pe), v) for pe, v in points if v is not None]
    if len(pts) < 2:
        return None
    n = len(pts)
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None
    return (n * sxy - sx * sy) / denom


def compute_metrics(frame: dict, as_of: str) -> dict:
    """Compute raw capital-allocation metrics from a PIT frame. Pure — no DB, no scoring.

    ``frame`` is the shape returned by fundamentals_asof.load_symbol_history.
    Returns a dict of raw metrics + coverage notes (values may be None when data is thin).
    """
    as_of = str(as_of)[:10]
    sales = _known(frame, "A", _SALES, as_of)
    npat = _known(frame, "A", _NPAT, as_of)
    opro = _known(frame, "A", _OPRO, as_of)
    roce = _known(frame, "A", _ROCE, as_of)
    eqcap = _known(frame, "A", _EQCAP, as_of)
    resv = _known(frame, "A", _RESV, as_of)
    borr = _known(frame, "A", _BORR, as_of)
    eps = _known(frame, "A", _EPS, as_of)

    eq_m, rs_m, bo_m = _smap(eqcap), _smap(resv), _smap(borr)
    op_m, np_m, eps_m = _smap(opro), _smap(npat), _smap(eps)

    # Net worth needs equity capital + reserves. Capital employed adds borrowings
    # (absent borrowings row => treat as debt-free 0, noted in coverage).
    nw_periods = sorted(set(eq_m) & set(rs_m))
    coverage = []
    if not bo_m:
        coverage.append("no_borrowings_row(assumed_0)")
    ce = []  # [(period_end, capital_employed)]
    for pe in nw_periods:
        nw = eq_m[pe] + rs_m[pe]
        ce.append((pe, nw + bo_m.get(pe, 0.0)))

    metrics = {
        "as_of": as_of, "model": "industrial",
        "roiic": None, "roce_latest": None, "roce_avg": None, "roce_trend": None,
        "roe_latest": None, "roe_avg": None, "roe_trend": None, "roa_latest": None,
        "dilution_drag": None, "equity_capital_cagr": None,
        "debt_funding_share": None, "growth_efficiency": None,
        "n_years": 0, "span_years": 0, "coverage": coverage,
    }

    # ROCE level/trend only needs the ROCE series
    if roce:
        metrics["roce_latest"] = roce[-1][1]
        metrics["roce_avg"] = sum(v for _, v in roce) / len(roce)
        metrics["roce_trend"] = _slope_per_year(roce)

    # Incremental metrics need an aligned CE + operating-profit window
    aligned = [(pe, cev, op_m[pe]) for pe, cev in ce if pe in op_m]
    metrics["n_years"] = len(aligned)
    if len(aligned) >= _MIN_YEARS:
        pe0, ce0, op0 = aligned[0]
        pe1, ce1, op1 = aligned[-1]
        span = _year(pe1) - _year(pe0)
        metrics["span_years"] = span
        if span >= _MIN_SPAN:
            d_ce = ce1 - ce0
            d_op = op1 - op0
            if d_ce > 1e-6:
                metrics["roiic"] = 100.0 * d_op / d_ce
                metrics["debt_funding_share"] = (
                    100.0 * (bo_m.get(pe1, 0.0) - bo_m.get(pe0, 0.0)) / d_ce
                )
            else:
                # Capital employed is flat or SHRANK (buybacks / deleveraging / distress turnaround).
                # "Return on INCREMENTAL capital" is then genuinely undefined — ABSTAIN rather than
                # reward. A sentinel here produced false-positive "elite allocator" reads on distressed
                # deleveraging (e.g. SUZLON, GMR crawling out of debt). ROCE level/trend + dilution +
                # growth-efficiency carry the score instead (cf. NESTLE: ROIIC undefined, ROCE 96 → ~100).
                coverage.append("capital_flat_or_returned")
            ce_cagr = _cagr(ce0, ce1, span)
            pat0, pat1 = np_m.get(pe0), np_m.get(pe1)
            pat_cagr = _cagr(pat0, pat1, span) if (pat0 and pat1) else None
            if pat_cagr is not None and ce_cagr and ce_cagr > 0:
                metrics["growth_efficiency"] = pat_cagr / ce_cagr
            eps0, eps1 = eps_m.get(pe0), eps_m.get(pe1)
            eps_cagr = _cagr(eps0, eps1, span) if (eps0 and eps1) else None
            if pat_cagr is not None and eps_cagr is not None:
                metrics["dilution_drag"] = pat_cagr - eps_cagr  # +ve => shares grew
            # Equity-capital CAGR — a dilution proxy that survives PAT sign changes (loss→profit
            # turnarounds make the PAT−EPS gap undefined; equity capital still shows the issuance).
            eqc0, eqc1 = eq_m.get(pe0), eq_m.get(pe1)
            metrics["equity_capital_cagr"] = _cagr(eqc0, eqc1, span) if (eqc0 and eqc1) else None
    metrics["coverage"] = coverage
    return metrics


def _is_financial(frame: dict) -> bool:
    """Lender (bank/NBFC) if Screener reports the Financing-Profit/Margin rows unique to them."""
    return any(("A", m) in frame for m in _FIN_MARKERS)


def compute_metrics_fin(frame: dict, as_of: str) -> dict:
    """Capital-allocation metrics for LENDERS: ROE / ROA / dilution / book-value growth.

    ROCE/ROIIC/capital-employed/debt-funding are meaningless when borrowing IS the business —
    applying them mis-rated every NBFC/bank as POOR (e.g. TATACAP). Net worth = Equity + Reserves.
    """
    as_of = str(as_of)[:10]
    np_m = _smap(_known(frame, "A", _NPAT, as_of))
    eq_m = _smap(_known(frame, "A", _EQCAP, as_of))
    rs_m = _smap(_known(frame, "A", _RESV, as_of))
    ta_m = _smap(_known(frame, "A", _TOTAL_ASSETS, as_of))
    eps_m = _smap(_known(frame, "A", _EPS, as_of))
    nw_periods = sorted(set(eq_m) & set(rs_m) & set(np_m))

    m = {"as_of": as_of, "model": "financial",
         "roiic": None, "roce_latest": None, "roce_avg": None, "roce_trend": None,
         "roe_latest": None, "roe_avg": None, "roe_trend": None, "roa_latest": None,
         "dilution_drag": None, "equity_capital_cagr": None,
         "debt_funding_share": None, "growth_efficiency": None,
         "n_years": len(nw_periods), "span_years": 0, "coverage": ["financial_model"]}

    roe = [(pe, 100.0 * np_m[pe] / (eq_m[pe] + rs_m[pe]))
           for pe in nw_periods if (eq_m[pe] + rs_m[pe]) > 0]
    if roe:
        m["roe_latest"] = roe[-1][1]
        m["roe_avg"] = sum(v for _, v in roe) / len(roe)
        m["roe_trend"] = _slope_per_year(roe)
    ta_periods = sorted(set(ta_m) & set(np_m))
    if ta_periods and ta_m[ta_periods[-1]] > 0:
        m["roa_latest"] = 100.0 * np_m[ta_periods[-1]] / ta_m[ta_periods[-1]]

    if len(nw_periods) >= _MIN_YEARS:
        pe0, pe1 = nw_periods[0], nw_periods[-1]
        span = _year(pe1) - _year(pe0)
        m["span_years"] = span
        if span >= _MIN_SPAN:
            eqc0, eqc1 = eq_m.get(pe0), eq_m.get(pe1)
            m["equity_capital_cagr"] = _cagr(eqc0, eqc1, span) if (eqc0 and eqc1) else None
            nw_cagr = _cagr(eq_m[pe0] + rs_m[pe0], eq_m[pe1] + rs_m[pe1], span)
            pat_cagr = _cagr(np_m.get(pe0), np_m.get(pe1), span) if (np_m.get(pe0) and np_m.get(pe1)) else None
            if pat_cagr is not None and nw_cagr and nw_cagr > 0:
                m["growth_efficiency"] = pat_cagr / nw_cagr          # earnings growth per unit book growth
            e0, e1 = eps_m.get(pe0), eps_m.get(pe1)
            eps_cagr = _cagr(e0, e1, span) if (e0 and e1) else None
            if pat_cagr is not None and eps_cagr is not None:
                m["dilution_drag"] = pat_cagr - eps_cagr
    return m


def score_metrics(m: dict) -> dict:
    """Map raw metrics -> 0..100 component scores + weighted composite ca_score.

    Missing components are dropped and the weights renormalised so a data-thin name is
    not silently penalised to zero. Returns {"ca_score", "components", "weights_used"}.
    """
    comp = {}
    if m.get("model") == "financial":
        weights = _FIN_WEIGHTS
        if m.get("roe_latest") is not None:
            comp["roe_level"] = _logistic(m["roe_latest"], *_ANCHORS["roe_level"])
        if m.get("roe_trend") is not None:
            comp["roe_trend"] = _logistic(m["roe_trend"], *_ANCHORS["roe_trend"])
        if m.get("roa_latest") is not None:
            comp["roa_level"] = _logistic(m["roa_latest"], *_ANCHORS["roa_level"])
        if m.get("dilution_drag") is not None:
            comp["dilution"] = 100.0 - _logistic(m["dilution_drag"], *_ANCHORS["dilution"])
        elif m.get("equity_capital_cagr") is not None:
            comp["dilution"] = 100.0 - _logistic(m["equity_capital_cagr"], *_ANCHORS["dilution_eqcap"])
        if m.get("growth_efficiency") is not None:
            comp["growth_eff"] = _logistic(m["growth_efficiency"], *_ANCHORS["growth_eff"])
    else:
        weights = _WEIGHTS
        if m.get("roiic") is not None:
            comp["roiic"] = _logistic(m["roiic"], *_ANCHORS["roiic"])
        if m.get("roce_latest") is not None:
            comp["roce_level"] = _logistic(m["roce_latest"], *_ANCHORS["roce_level"])
        if m.get("roce_trend") is not None:
            comp["roce_trend"] = _logistic(m["roce_trend"], *_ANCHORS["roce_trend"])
        if m.get("dilution_drag") is not None:
            comp["dilution"] = 100.0 - _logistic(m["dilution_drag"], *_ANCHORS["dilution"])
        elif m.get("equity_capital_cagr") is not None:
            comp["dilution"] = 100.0 - _logistic(m["equity_capital_cagr"], *_ANCHORS["dilution_eqcap"])
        if m.get("debt_funding_share") is not None:
            comp["debt_share"] = 100.0 - _logistic(m["debt_funding_share"], *_ANCHORS["debt_share"])
        if m.get("growth_efficiency") is not None:
            comp["growth_eff"] = _logistic(m["growth_efficiency"], *_ANCHORS["growth_eff"])

    wsum = sum(weights[c] for c in comp)
    ca = sum(comp[c] * weights[c] for c in comp) / wsum if wsum > 0 else None
    return {
        "ca_score": round(ca, 2) if ca is not None else None,
        "components": {c: round(v, 2) for c, v in comp.items()},
        "weights_used": {c: weights[c] for c in comp},
    }


# --- DB layer (hermes.db) --------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS capital_allocation_scores (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    as_of         TEXT NOT NULL,
    computed_at   TEXT NOT NULL DEFAULT (datetime('now')),
    ca_score      REAL,
    ca_pctile     REAL,
    ca_tier       TEXT,
    model         TEXT,
    roiic         REAL,
    roce_latest   REAL,
    roce_avg      REAL,
    roce_trend    REAL,
    roe_latest    REAL,
    roa_latest    REAL,
    dilution_drag REAL,
    debt_funding_share REAL,
    growth_efficiency  REAL,
    n_years       INTEGER,
    coverage      TEXT,
    detail_json   TEXT,
    UNIQUE(symbol, as_of)
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_SCHEMA)


def compute(symbol: str, as_of: Optional[str] = None, *,
            db_path: str = RESEARCH_DB, frame: Optional[dict] = None) -> dict:
    """Full per-symbol result: raw metrics + scores. PIT-safe. Does not persist.

    Pass ``frame`` to score a pre-loaded history (tests / backtests). Otherwise the
    frame is loaded once from research.db.fundamentals_history.
    """
    as_of = as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if frame is None:
        frame = load_symbol_history(symbol, db_path=db_path)
    m = compute_metrics_fin(frame, as_of) if _is_financial(frame) else compute_metrics(frame, as_of)
    s = score_metrics(m)
    out = {"symbol": symbol.upper().strip()}
    out.update(m)
    out.update(s)
    return out


def save_score(conn: sqlite3.Connection, r: dict) -> None:
    """Upsert one result into capital_allocation_scores."""
    detail = json.dumps({"components": r.get("components"),
                         "weights_used": r.get("weights_used"),
                         "span_years": r.get("span_years"),
                         "equity_capital_cagr": r.get("equity_capital_cagr")})
    conn.execute(
        """INSERT INTO capital_allocation_scores
             (symbol, as_of, ca_score, model, roiic, roce_latest, roce_avg, roce_trend,
              roe_latest, roa_latest, dilution_drag, debt_funding_share, growth_efficiency,
              n_years, coverage, detail_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(symbol, as_of) DO UPDATE SET
             computed_at=datetime('now'), ca_score=excluded.ca_score, model=excluded.model,
             roiic=excluded.roiic, roce_latest=excluded.roce_latest, roce_avg=excluded.roce_avg,
             roce_trend=excluded.roce_trend, roe_latest=excluded.roe_latest,
             roa_latest=excluded.roa_latest, dilution_drag=excluded.dilution_drag,
             debt_funding_share=excluded.debt_funding_share,
             growth_efficiency=excluded.growth_efficiency, n_years=excluded.n_years,
             coverage=excluded.coverage, detail_json=excluded.detail_json""",
        (r["symbol"], r["as_of"], r.get("ca_score"), r.get("model"), r.get("roiic"),
         r.get("roce_latest"), r.get("roce_avg"), r.get("roce_trend"),
         r.get("roe_latest"), r.get("roa_latest"),
         r.get("dilution_drag"), r.get("debt_funding_share"), r.get("growth_efficiency"),
         r.get("n_years"), ",".join(r.get("coverage") or []), detail),
    )


def _universe(db_path: str, min_years: int) -> list:
    """Symbols in research.db.fundamentals_history with enough annual history."""
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    except sqlite3.OperationalError:
        return []  # DB file/dir absent (e.g. running off the VPS) → empty universe
    try:
        rows = con.execute(
            "SELECT symbol, COUNT(DISTINCT period_end) n FROM fundamentals_history "
            "WHERE period_type='A' GROUP BY symbol HAVING n >= ? ORDER BY symbol",
            (min_years,)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()
    return [r[0] for r in rows]


def _fill_percentiles(conn: sqlite3.Connection, as_of: str) -> int:
    """Cross-sectional percentile + relative tier, ranked WITHIN model (financials vs industrials
    are not comparable on one scale — an 'EXCELLENT' lender is top-quintile among lenders)."""
    total = 0
    for model in ("industrial", "financial"):
        rows = conn.execute(
            "SELECT id, ca_score FROM capital_allocation_scores "
            "WHERE as_of=? AND ca_score IS NOT NULL AND model=? ORDER BY ca_score",
            (as_of, model)).fetchall()
        n = len(rows)
        for rank, row in enumerate(rows):
            pct = 100.0 * (rank + 0.5) / n
            tier = next(t for lo, t in _TIER_BANDS if pct >= lo)
            conn.execute("UPDATE capital_allocation_scores SET ca_pctile=?, ca_tier=? WHERE id=?",
                         (round(pct, 1), tier, row[0]))
        total += n
    return total


def run_batch(as_of: Optional[str] = None, *, limit: Optional[int] = None,
              min_years: int = _MIN_YEARS, db_path: str = RESEARCH_DB,
              dry_run: bool = False) -> dict:
    as_of = as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    syms = _universe(db_path, min_years)
    if limit:
        syms = syms[:limit]
    if dry_run:
        return {"as_of": as_of, "universe": len(syms), "dry_run": True}
    scored = failed = 0
    with get_conn() as conn:
        ensure_schema(conn)
        conn.commit()
        for sym in syms:
            try:
                r = compute(sym, as_of, db_path=db_path)
                save_score(conn, r)
                scored += 1
            except Exception as e:  # noqa: BLE001 — batch resilience
                log.warning("capital_allocation failed for %s: %s", sym, e)
                failed += 1
            if scored % 50 == 0:
                # bounded write txns — a full-universe pass holds the lock for
                # minutes otherwise and starves hermes-api (AUD-24 / D82c class)
                conn.commit()
        conn.commit()
        ranked = _fill_percentiles(conn, as_of)   # its own short txn via get_conn exit
    return {"as_of": as_of, "universe": len(syms), "scored": scored,
            "failed": failed, "ranked": ranked}


# --- selftest (synthetic, no DB) -------------------------------------------

def _selftest() -> int:
    """Hand-built frames validate the math end-to-end without any database."""
    def frame_from(annual: dict) -> dict:
        # annual: {metric: [(period_end, value), ...]}; knowable date = period_end (past → known)
        fr = {}
        for metric, pts in annual.items():
            fr[("A", metric)] = [(pe, pe, v) for pe, v in pts]
        return fr

    # Compounder: EBIT 100->150 over CE 500->700 => ROIIC 25%; ROCE rising; no dilution; no new debt.
    good = frame_from({
        "Operating Profit": [("2019-03-31", 100), ("2020-03-31", 117), ("2021-03-31", 133), ("2022-03-31", 150)],
        "Equity Capital": [("2019-03-31", 50), ("2020-03-31", 50), ("2021-03-31", 50), ("2022-03-31", 50)],
        "Reserves": [("2019-03-31", 350), ("2020-03-31", 417), ("2021-03-31", 483), ("2022-03-31", 550)],
        "Borrowings": [("2019-03-31", 100), ("2020-03-31", 100), ("2021-03-31", 100), ("2022-03-31", 100)],
        "ROCE %": [("2019-03-31", 16), ("2020-03-31", 18), ("2021-03-31", 20), ("2022-03-31", 22)],
        "Net Profit": [("2019-03-31", 80), ("2020-03-31", 95), ("2021-03-31", 112), ("2022-03-31", 130)],
        "EPS in Rs": [("2019-03-31", 8.0), ("2020-03-31", 9.5), ("2021-03-31", 11.2), ("2022-03-31", 13.0)],
    })
    r = compute("GOOD", "2023-06-30", frame=good)
    assert r["roiic"] is not None and 24 < r["roiic"] < 26, r["roiic"]
    assert r["debt_funding_share"] is not None and abs(r["debt_funding_share"]) < 1, r["debt_funding_share"]
    assert r["roce_trend"] and r["roce_trend"] > 0, r["roce_trend"]
    assert r["ca_score"] and r["ca_score"] > 65, r["ca_score"]

    # Empire-builder: EBIT 100->120 over CE 300->700 => ROIIC 5%; ~75% debt-funded; EPS falls (dilution).
    bad = frame_from({
        "Operating Profit": [("2019-03-31", 100), ("2020-03-31", 107), ("2021-03-31", 113), ("2022-03-31", 120)],
        "Equity Capital": [("2019-03-31", 50), ("2020-03-31", 63), ("2021-03-31", 77), ("2022-03-31", 90)],
        "Reserves": [("2019-03-31", 150), ("2020-03-31", 170), ("2021-03-31", 190), ("2022-03-31", 210)],
        "Borrowings": [("2019-03-31", 100), ("2020-03-31", 200), ("2021-03-31", 300), ("2022-03-31", 400)],
        "ROCE %": [("2019-03-31", 18), ("2020-03-31", 15), ("2021-03-31", 12), ("2022-03-31", 9)],
        "Net Profit": [("2019-03-31", 80), ("2020-03-31", 85), ("2021-03-31", 90), ("2022-03-31", 95)],
        "EPS in Rs": [("2019-03-31", 8.0), ("2020-03-31", 7.0), ("2021-03-31", 6.1), ("2022-03-31", 5.3)],
    })
    rb = compute("BAD", "2023-06-30", frame=bad)
    assert rb["roiic"] is not None and 4 < rb["roiic"] < 6, rb["roiic"]
    assert rb["debt_funding_share"] and rb["debt_funding_share"] > 70, rb["debt_funding_share"]
    assert rb["dilution_drag"] and rb["dilution_drag"] > 0, rb["dilution_drag"]
    assert rb["roce_trend"] and rb["roce_trend"] < 0, rb["roce_trend"]
    assert rb["ca_score"] is not None and rb["ca_score"] < 40, rb["ca_score"]

    assert r["ca_score"] > rb["ca_score"] + 25, (r["ca_score"], rb["ca_score"])

    # Thin data: only ROCE, no incremental window => score from level alone, no crash.
    thin = frame_from({"ROCE %": [("2021-03-31", 19), ("2022-03-31", 21)]})
    rt = compute("THIN", "2023-06-30", frame=thin)
    assert rt["roiic"] is None and rt["ca_score"] is not None, rt

    # financial (lender): the 'Financing Profit' marker routes to the ROE/ROA model; ROIIC ignored.
    fin = frame_from({
        "Financing Profit": [("2019-03-31", 100), ("2022-03-31", 160)],
        "Net Profit": [("2019-03-31", 90), ("2020-03-31", 108), ("2021-03-31", 130), ("2022-03-31", 156)],
        "Equity Capital": [("2019-03-31", 50), ("2020-03-31", 50), ("2021-03-31", 50), ("2022-03-31", 50)],
        "Reserves": [("2019-03-31", 450), ("2020-03-31", 520), ("2021-03-31", 600), ("2022-03-31", 700)],
        "Total Assets": [("2019-03-31", 5000), ("2020-03-31", 5800), ("2021-03-31", 6700), ("2022-03-31", 7800)],
        "EPS in Rs": [("2019-03-31", 9.0), ("2020-03-31", 10.8), ("2021-03-31", 13.0), ("2022-03-31", 15.6)],
    })
    rf = compute("BANKX", "2023-06-30", frame=fin)
    assert rf["model"] == "financial" and rf["roiic"] is None, rf
    assert rf["roe_latest"] and 20 < rf["roe_latest"] < 22, rf["roe_latest"]      # 156/750
    assert rf["roa_latest"] and 1.9 < rf["roa_latest"] < 2.1, rf["roa_latest"]    # 156/7800
    assert rf["ca_score"] and rf["ca_score"] > 55, rf["ca_score"]

    print("selftest OK  good=%.1f bad=%.1f thin=%.1f fin=%.1f"
          % (r["ca_score"], rb["ca_score"], rt["ca_score"], rf["ca_score"]))
    print("  good metrics:", {k: r[k] for k in ("roiic", "roce_trend", "debt_funding_share", "dilution_drag")})
    print("  bad  metrics:", {k: rb[k] for k in ("roiic", "roce_trend", "debt_funding_share", "dilution_drag")})
    return 0


def _inspect(symbol: str, db_path: str) -> int:
    frame = load_symbol_history(symbol, db_path=db_path)
    keys = sorted({m for (pt, m) in frame if pt == "A"})
    print("annual metrics for %s (%d):" % (symbol, len(keys)))
    for m in keys:
        pts = frame[("A", m)]
        print("  %-30s %d pts  latest=%s" % (m, len(pts), pts[-1][2] if pts else None))
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true", help="run synthetic math checks (no DB)")
    p.add_argument("--inspect", metavar="SYMBOL", help="print available annual metric keys")
    p.add_argument("--symbol", metavar="SYMBOL", help="score one symbol, print, do not persist")
    p.add_argument("--backfill", action="store_true", help="score the full eligible universe")
    p.add_argument("--limit", type=int, default=None, help="cap symbols this run")
    p.add_argument("--as-of", default=None, help="ISO date for point-in-time (default today)")
    p.add_argument("--min-years", type=int, default=_MIN_YEARS, help="min annual periods required")
    p.add_argument("--db", default=RESEARCH_DB, help="research.db path")
    p.add_argument("--dry-run", action="store_true", help="print plan only")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    if args.inspect:
        raise SystemExit(_inspect(args.inspect, args.db))
    if args.symbol:
        r = compute(args.symbol, args.as_of, db_path=args.db)
        print(json.dumps(r, indent=2, default=str))
        return
    if args.backfill or args.limit or args.dry_run:
        res = run_batch(args.as_of, limit=args.limit, min_years=args.min_years,
                        db_path=args.db, dry_run=args.dry_run)
        log.info("capital_allocation batch: %s", res)
        return
    p.print_help()


if __name__ == "__main__":
    main()
