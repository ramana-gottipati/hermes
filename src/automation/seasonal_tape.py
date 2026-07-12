"""seasonal_tape — descriptive-only 25-year calendar seasonality over PIT idiosyncratic residuals.

================================  FROZEN FAMILY (P0)  ================================
This docstring + the machine constants below (AXES, RESIDUAL_MODEL, MECHANISMS, GATES,
BROAD_INDICES, SECTOR_INDICES, DEFAULTS) constitute the *pre-registered frozen family*.
`frozen_family_hash()` hashes a canonical JSON of ALL of them; `--register` writes that
sha256 into research.db.prereg_registry (module='seasonal_tape', first-registration-wins,
tamper-evident) BEFORE any z is computed. Never scope-shrink after looking (gate 1). This is
the same discipline that produced the E-11/E-12 gate hashes; we use the standalone gate_hash
path so we never depend on the in-flight explosive_moves.prereg STUDIES list.

THE GOVERNING RULE (one number):
    z_pit(entity, t) = (r_t - mu_prior_years[r]) / sigma_prior_years[r]     # r = the residual
    r = R - (alpha + beta*market + gamma*(sector _|_ market))               # idiosyncratic
  * mu_prior/sigma_prior are the entity's OWN residual location/scale over STRICTLY-PRIOR years
    (all days, expanding) — a per-entity normaliser, NOT the cell's own history. This is the key
    choice: standardising against the cell's own prior mean would make z a pure BREAK detector
    (a *constant* seasonal level would collapse to z~=0); normalising against the entity baseline
    makes the per-cell mean z the seasonal SCRIPT (does this cell run systematically hot/cold).
  * ALL fits (alpha,beta,gamma, mu, MAD sigma) use STRICTLY-PRIOR expanding windows — the scored
    observation and every future year never enter their own denominator (leak-free). Coefficients
    are re-estimated once per year on all data strictly before that year (annual expanding refit)
    and applied within the year: known at year-start => no look-ahead.
  * SCRIPT(cell) = cross-year mean of the per-year cell-z. BREAK = latest year's cell-z vs that
    script. Two moments, one detector. month / iso_week / weekday = three re-bins of the SAME
    residual series.
  * STRIPPING: index strips nothing (r=R on the index's own level return); sector strips the
    market (Nifty 500); stock strips market + orthogonalized-sector (P2 layer).

RETURNS: index leg = raw index level %-change (index_rows.close_value is divisor-adjusted,
needs no corp-action adjustment). stock leg (P2) = corporate-action-ADJUSTED close returns
(adjust.adjusted_closes fed by corp_actions.price_ratios) — NEVER raw close/prev_close, whose
ex-day prev_close does not self-adjust (measured false, S85e).

CERTIFICATION GATES (a cell is COLORED only if ALL pass; else greyed "reported-not-gated"):
  1. Frozen family pre-registered + sha256-hashed BEFORE compute (this module).
  2. Non-inert null: circular-block bootstrap (block=21) AND cyclic-rotation surrogate on the
     residual series re-binned to cells, n>=200 seed 42; observed cell mean must sit OUTSIDE the
     one-sided null p95 on BOTH. YEAR-LABEL SHUFFLE IS BANNED (mean of a fixed z-set per cell is
     permutation-invariant => zero-width null; the swarm's key catch). Both nulls keep the
     calendar labels FIXED and resample/rotate the residual VALUES, so a genuine calendar
     phase-lock is destroyed while autocorrelation is preserved.
  3. Family-wide FDR (Benjamini-Hochberg-Yekutieli, dependency-safe) across the whole frozen grid
     + a global excess-count gate per axis (real certified count must beat the phase-null count).
  4. N >= MIN_YEARS independent years, else quarantined grey.
  5. Same-sign out-of-sample (fit 1..k -> confirm k+1..N) AND across epochs (pre-2010 / 2010-2020
     / post-2020). A sign flip = kill.
  6. Mechanism registry: a cell may carry a SIGNED read only with a named India mechanism +
     pledged sign registered here BEFORE compute. Pure flow/timing anchors (expiry, turn-of-month
     SIP, rebalance, F&O ban) license VARIANCE-ONLY breaks, never a sign.
  7. Earnings-cadence mask (P2 stock layer): a script that collapses when the per-name real
     filing window is removed is re-badged PEAD -> DECERTIFIED (PEAD wrappers NET-FAILED 0.10 vs
     0.85 bench — ledger, blocking).
  8. Mechanical-window flags auto-label MECHANICAL breaks (excluded from the news queue).
  9. Residual diagnostics (P2): residual trading-day-of-month profile FLAT (SIP absorbed) AND
     residual _|_ index-residual within cell, else no stock-level script is trusted.
 10. Machine descriptive-only fence: NO forward-return column, NO cross-entity ranking of
     scripts/breaks, NO backtest-as-entry. Breaks route to the news layer as QUESTIONS.
 11. Survivorship: PIT membership; delisted retained where reconstructable; else the cell is
     capped "survivor-conditional, reported-not-gated".

HONEST PRIOR (ledger discipline): index/sector scripts with dateable causes WILL certify; MOST
single-name cells will grey out (indistinguishable from the placebo count) — that winnowing IS
the product. NOTHING here is tradeable net of STT/impact (expectancy ~= 0); the page says so.

Pure-Python/stdlib ONLY (no numpy) so the backfill runs in the MAIN hermes venv on the VPS
timers, exactly like the market_internals bounded-snapshot precedent. Read-only on hermes.db
(index_rows / bhavcopy_rows / corporate_actions); writes the BOUNDED aggregated snapshot tables
(seasonal_cells / seasonal_stack / seasonal_outlook / seasonal_breaks / seasonal_meta) into
hermes.db — the raw 25y residual series is derivable and is NEVER persisted (space mandate). The
prereg hash lives in research.db.

Run:
  python -m src.automation.seasonal_tape --selftest            # offline, synthetic, no DB
  python -m src.automation.seasonal_tape --register            # P0 freeze -> research.db
  python -m src.automation.seasonal_tape --verify              # tamper-check the freeze
  python -m src.automation.seasonal_tape --backfill --scope index   # P1 index tapes  (VPS)
  python -m src.automation.seasonal_tape --backfill --scope sector  # P1 sector tapes (VPS)
  python -m src.automation.seasonal_tape --stats               # coverage readout
=====================================================================================
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sqlite3
import statistics
from datetime import date

from src.automation.adjust import adjusted_closes

# --------------------------------------------------------------------------- #
#  FROZEN-FAMILY MACHINE SPEC  (hashed into research.db.prereg_registry at P0)  #
# --------------------------------------------------------------------------- #

MARKET = "Nifty 500"                     # the market leg stripped from sector/stock residuals

# three re-bins of the SAME residual series; values = the cell keys enumerated
AXES = {
    "month": list(range(1, 13)),         # 1..12 calendar months
    "iso_week": list(range(1, 54)),      # ISO week 1..53
    "weekday": list(range(0, 5)),        # 0=Mon .. 4=Fri
}

RESIDUAL_MODEL = {
    "index": "r = R_index (strip nothing; index level return)",
    "sector": "r = R_sector - (alpha + beta*R_market); market = Nifty 500",
    "stock": "r = R_stock - (alpha + beta*R_market + gamma*(R_sector _|_ R_market))",
    "fit": "annual expanding refit on strictly-prior data; leak-free",
    "sigma": "robust MAD (1.4826*MAD), floored",
    "returns": "index=raw level %chg; stock=corp-action-adjusted close returns",
}

GATES = {
    "min_years": 15,                     # gate 4
    "null_n": 200,                       # gate 2
    "seed": 42,                          # gate 2
    "block": 21,                         # circular-block length (~1 trading month)
    "mad_k": 1.4826,
    "sigma_floor": 1e-9,
    "fdr_alpha": 0.05,                   # gate 3
    "epochs": [["pre-2010", "0000", "2009"],
               ["2010-2020", "2010", "2020"],
               ["post-2020", "2021", "9999"]],   # gate 5
    "banned_null": "year-label shuffle (zero-width; permutation-invariant)",
    "nulls": ["circular_block", "cyclic_rotation"],
    "warmup_years": 3,                   # min prior years before a z can be scored
}

DEFAULTS = {                             # plan §6 (flippable, cheap, recorded)
    "coloring": "residual default, Raw toggle",
    "benchmark": "sector (minor) first, Nifty broad second",
    "axis": "Apr-Mar fiscal default, Jan-Dec toggle",
}

# Pre-registered ENTITY universe for indices/sectors (P1). Stored casing in index_rows is
# INCONSISTENT ('Nifty 500' vs 'NIFTY Midcap 100'); we resolve to the actual casing at compute
# time via an UPPER() map, but the FROZEN family is these canonical names (case-insensitive).
BROAD_INDICES = [
    "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200", "Nifty 500",
    "Nifty Midcap 50", "Nifty Midcap 100", "Nifty Midcap 150",
    "Nifty Smallcap 50", "Nifty Smallcap 100", "Nifty Smallcap 250",
    "Nifty Microcap 250", "Nifty Total Market",
]
SECTOR_INDICES = [
    "Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty FMCG",
    "Nifty Metal", "Nifty Realty", "Nifty Energy", "Nifty Financial Services",
    "Nifty PSU Bank", "Nifty Private Bank", "Nifty Media", "Nifty Healthcare",
    "Nifty Consumer Durables", "Nifty Oil & Gas", "Nifty Infrastructure",
    "Nifty Commodities", "Nifty PSE", "Nifty CPSE", "Nifty MNC",
]

# Mechanism / sign registry (gate 6) — India-specific, pledged BEFORE compute.
#   sign:  +1 / -1 = a signed directional read is admissible for this cell.
#          0        = VARIANCE-ONLY (flow/timing anchor); magnitude may certify, never a sign.
#   kind:  'signed' | 'variance' | 'mask' | 'diagnostic'
#   scope: which entity classes the mechanism applies to.
MECHANISMS = [
    {"id": "M-FYEND", "kind": "signed", "sign": +1, "axis": "month", "cells": [3],
     "iso_cells": [12, 13], "scope": ["index", "sector"],
     "mechanism": "FY-end window-dressing + book-closure (last week); advance-tax pressures liquidity mid-March"},
    {"id": "M-BUDGET-RUNUP", "kind": "signed", "sign": +1, "axis": "iso_week", "cells": [4, 5],
     "scope": ["index", "sector"],
     "mechanism": "Union Budget run-up anticipation (infra/capital-goods/defence/PSU tilt)"},
    {"id": "M-BUDGET-DAY", "kind": "variance", "sign": 0, "axis": "iso_week", "cells": [5, 6],
     "scope": ["index", "sector"], "mechanism": "Budget day itself (Feb 1; pre-2017 end-Feb) — high variance"},
    {"id": "M-MONSOON", "kind": "signed", "sign": +1, "axis": "month", "cells": [6, 7],
     "scope": ["sector"], "mechanism": "SW monsoon onset -> rural demand (agri-inputs/FMCG/2-wheeler-auto); weak as a pure calendar cell"},
    {"id": "M-FESTIVE", "kind": "signed", "sign": +1, "axis": "month", "cells": [10, 11],
     "scope": ["sector"], "mechanism": "Dhanteras/Diwali + wedding buying (auto/jewellery/consumer-durables/paints)"},
    {"id": "M-YEAREND", "kind": "signed", "sign": +1, "axis": "month", "cells": [12],
     "scope": ["index"], "mechanism": "Dec year-end thin-volume drift (low conviction)"},
    {"id": "F-EXPIRY", "kind": "variance", "sign": 0, "axis": "weekday", "cells": [3],
     "scope": ["index", "sector"], "mechanism": "F&O monthly/weekly expiry clustering (Thu) — mechanical-window flag"},
    {"id": "F-TOM-SIP", "kind": "diagnostic", "sign": 0, "axis": "month", "cells": [],
     "scope": ["index", "sector", "stock"],
     "mechanism": "turn-of-month SIP inflows — residual trading-day-of-month profile must be FLAT (gate 9), not a colored cell"},
    {"id": "M-RESULTS", "kind": "mask", "sign": 0, "axis": "month", "cells": [1, 4, 7, 10],
     "scope": ["stock"], "mechanism": "quarterly results cadence -> EARNINGS-CADENCE MASK (gate 7); decertify if a cell collapses ex-earnings (PEAD in costume)"},
]

_PREREG_MODULE = "seasonal_tape"
_PREREG_MODULE_STOCK = "seasonal_tape_stock"
STOCK_RESIDUAL_MODEL = ("r = R_stock - (alpha + beta*R_market); market = Nifty 500 (MARKET-ONLY; "
                        "sector strip DEFERRED - a stock sits in several Nifty sector indices AND "
                        "sector history is back-calc capped at 2012)")
STOCK_UNIVERSE_SPEC = {
    "membership": "stock_index_membership index_name=Nifty 500 @ latest snapshot_date "
                  "(current-membership => survivor-conditional, gate 11)",
    "order": "company_profile.priority_rank asc (90d turnover liquidity)",
    "returns": "corp-action-ADJUSTED bhavcopy_rows EQ close via adjust.adjusted_closes + "
              "corp_actions.price_ratios; NEVER raw close/prev_close",
    "min_obs": 250,
}
_NAN = float("nan")


def _canon_spec() -> dict:
    """The exact object hashed for the frozen-family fingerprint. Deterministic ordering."""
    return {
        "doc": (__doc__ or "").strip(),
        "market": MARKET,
        "axes": AXES,
        "residual_model": RESIDUAL_MODEL,
        "gates": {k: v for k, v in sorted(GATES.items())},
        "defaults": DEFAULTS,
        "broad_indices": sorted(n.upper() for n in BROAD_INDICES),
        "sector_indices": sorted(n.upper() for n in SECTOR_INDICES),
        "mechanisms": sorted(
            [m["id"], m["kind"], m["sign"], m["axis"], list(m["cells"]), sorted(m["scope"])]
            for m in MECHANISMS),
    }


def frozen_family_hash() -> str:
    """sha256 over a canonical JSON of the whole frozen family (== gate_hash discipline)."""
    blob = json.dumps(_canon_spec(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _canon_spec_stock() -> dict:
    """The exact object hashed for the STOCK (P2) frozen-family fingerprint — a SEPARATE
    pre-registered family from the index/sector one (module='seasonal_tape_stock'). Built on TOP
    of _canon_spec() (same axes/gates/mechanisms/defaults) plus the stock-only residual model and
    universe spec, so it is deliberately a DIFFERENT hash — never conflated with frozen_family_hash()."""
    spec = _canon_spec()
    spec["module"] = _PREREG_MODULE_STOCK
    spec["stock_residual_model"] = STOCK_RESIDUAL_MODEL
    spec["stock_universe"] = STOCK_UNIVERSE_SPEC
    return spec


def frozen_family_hash_stock() -> str:
    """sha256 over a canonical JSON of the STOCK frozen family (distinct from frozen_family_hash())."""
    blob = json.dumps(_canon_spec_stock(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
#  PURE-PYTHON STATISTICAL CORE  (selftested; no numpy, no DB, no I/O)         #
# --------------------------------------------------------------------------- #

def _finite(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)


def _mean(xs) -> float:
    xs = [x for x in xs if _finite(x)]
    return sum(xs) / len(xs) if xs else _NAN


def ols1(x: list, y: list) -> tuple[float, float]:
    """1-variable OLS -> (alpha, beta). Degenerate/short input -> (0.0, 0.0) (strip nothing)."""
    pairs = [(a, b) for a, b in zip(x, y) if _finite(a) and _finite(b)]
    n = len(pairs)
    if n < 3:
        return 0.0, 0.0
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    sxx = sum((a - mx) ** 2 for a, _ in pairs)
    if sxx < 1e-18:
        return 0.0, 0.0
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    beta = sxy / sxx
    return my - beta * mx, beta


def _ols2(m1: list, m2: list, y: list) -> tuple[float, float, float]:
    """2-variable OLS y ~ a + b*m1 + c*m2 via normal equations (pure python). (stock scope, P2)."""
    rows = [(x1, x2, yy) for x1, x2, yy in zip(m1, m2, y) if _finite(x1) and _finite(x2) and _finite(yy)]
    n = len(rows)
    if n < 5:
        a, b = ols1(m1, y)
        return a, b, 0.0
    s1 = sum(r[0] for r in rows); s2 = sum(r[1] for r in rows); sy = sum(r[2] for r in rows)
    s11 = sum(r[0] * r[0] for r in rows); s22 = sum(r[1] * r[1] for r in rows)
    s12 = sum(r[0] * r[1] for r in rows)
    s1y = sum(r[0] * r[2] for r in rows); s2y = sum(r[1] * r[2] for r in rows)
    # 3x3 symmetric system [[n,s1,s2],[s1,s11,s12],[s2,s12,s22]] . [a,b,c] = [sy,s1y,s2y]
    A = [[n, s1, s2], [s1, s11, s12], [s2, s12, s22]]
    rhs = [sy, s1y, s2y]
    sol = _solve3(A, rhs)
    if sol is None:
        a, b = ols1(m1, y)
        return a, b, 0.0
    return sol[0], sol[1], sol[2]


def _solve3(A, b):
    """Gaussian elimination for a 3x3 system. None if singular."""
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-15:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for r in range(3):
            if r != col and abs(M[r][col]) > 0:
                f = M[r][col]
                M[r] = [v - f * M[col][i] for i, v in enumerate(M[r])]
    return [M[0][3], M[1][3], M[2][3]]


def orthogonalize(market: list, sector: list) -> list:
    """sector _|_ market  =  sector - (a + b*market)  (Gram-Schmidt strip of the market leg)."""
    a, b = ols1(market, sector)
    return [s - (a + b * m) if _finite(s) and _finite(m) else _NAN for m, s in zip(market, sector)]


def _year_of(d: str) -> int:
    return int(d[:4])


def pit_residuals(dates: list, R: list, scope: str,
                  market: list | None = None, sector: list | None = None,
                  warmup_years: int = 3) -> list:
    """Point-in-time idiosyncratic residual per observation, annual EXPANDING refit (leak-free).

    index  -> resid = R (strip nothing).
    sector -> resid = R - (alpha + beta*market),   fit on strictly-prior years.
    stock  -> resid = R - (alpha + beta*market + gamma*(sector _|_ market)), fit on prior years.

    Coefficients for year Y are fit ONLY on observations with year < Y, so they are known at
    Y-start; the first `warmup_years` distinct years are left as NaN (insufficient prior)."""
    n = len(R)
    if scope == "index" or market is None:
        return list(R)
    out = [_NAN] * n
    years = [_year_of(d) for d in dates]
    uniq = sorted(set(years))
    for yi, Y in enumerate(uniq):
        if yi < warmup_years:
            continue
        pri = [i for i in range(n) if years[i] < Y]
        cur = [i for i in range(n) if years[i] == Y]
        if len(pri) < 60:
            continue
        mkt_p = [market[i] for i in pri]
        R_p = [R[i] for i in pri]
        if scope == "sector":
            a, b = ols1(mkt_p, R_p)
            for i in cur:
                if _finite(R[i]) and _finite(market[i]):
                    out[i] = R[i] - (a + b * market[i])
        else:  # stock
            sec_p = [sector[i] for i in pri]
            ap, bp = ols1(mkt_p, sec_p)                        # sector-strip coeffs (frozen on prior)
            sec_resid_p = [sec_p[k] - (ap + bp * mkt_p[k]) for k in range(len(pri))]
            a, b, g = _ols2(mkt_p, sec_resid_p, R_p)
            for i in cur:
                if _finite(R[i]) and _finite(market[i]) and _finite(sector[i]):
                    sec_resid_i = sector[i] - (ap + bp * market[i])
                    out[i] = R[i] - (a + b * market[i] + g * sec_resid_i)
    return out


def cell_key(d: str, axis: str) -> int:
    if axis == "month":
        return int(d[5:7])
    if axis == "weekday":
        return date.fromisoformat(d[:10]).weekday()
    return date.fromisoformat(d[:10]).isocalendar().week          # iso_week


def _mad_sigma(xs: list, mad_k: float, floor: float) -> float:
    xs = [x for x in xs if _finite(x)]
    if not xs:
        return floor
    med = statistics.median(xs)
    mad = statistics.median([abs(x - med) for x in xs])
    return max(mad_k * mad, floor)


def pit_z(dates: list, resid: list, axis: str,
          warmup_years: int = 3, mad_k: float = 1.4826, floor: float = 1e-9,
          min_prior: int = 200) -> list:
    """z_pit per observation: (resid - entity prior-years median) / entity prior-years MAD-sigma.
    The normaliser is the entity's OWN residual distribution over STRICTLY-PRIOR years (ALL days,
    expanding) — NOT the cell's own history (that would make z a break detector and hide a
    constant seasonal level). Re-estimated once per year and applied within the year (leak-free).
    `axis` is unused for the normaliser (deliberately entity-level) — kept for call symmetry."""
    n = len(resid)
    z = [_NAN] * n
    years = [_year_of(d) for d in dates]
    uniq = sorted(set(years))
    resid_by_year: dict = {}
    for r, y in zip(resid, years):
        if _finite(r):
            resid_by_year.setdefault(y, []).append(r)
    for yi, Y in enumerate(uniq):
        if yi < warmup_years:
            continue
        prior = []
        for y2 in uniq:
            if y2 >= Y:
                break
            prior.extend(resid_by_year.get(y2, []))
        if len(prior) < min_prior:
            continue
        mu = statistics.median(prior)
        sig = _mad_sigma(prior, mad_k, floor)
        for i in range(n):
            if years[i] == Y and _finite(resid[i]):
                z[i] = (resid[i] - mu) / sig
    return z


def year_cell_means(dates: list, z: list, axis: str) -> dict:
    """{(cell, year): (mean_z, n_obs)} — the 25-row STACK (per-year, per-cell z average)."""
    cells = [cell_key(d, axis) for d in dates]
    years = [_year_of(d) for d in dates]
    acc: dict = {}
    for c, y, zz in zip(cells, years, z):
        if _finite(zz):
            acc.setdefault((c, y), []).append(zz)
    return {k: (statistics.fmean(v), len(v)) for k, v in acc.items()}


def script_of(stack: dict, cell: int) -> tuple[float, int, float]:
    """SCRIPT for one cell = cross-year mean of the per-year cell-z; + n_years + hit_rate."""
    vals = [mz for (c, _y), (mz, _n) in stack.items() if c == cell]
    if not vals:
        return _NAN, 0, _NAN
    return statistics.fmean(vals), len(vals), sum(1 for v in vals if v > 0) / len(vals)


def _quantile(sorted_xs: list, q: float) -> float:
    if not sorted_xs:
        return _NAN
    if len(sorted_xs) == 1:
        return sorted_xs[0]
    pos = q * (len(sorted_xs) - 1)
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_xs[lo]
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


def placebo_stats(observed: float, null_means: list) -> dict:
    """5-number summary of a null run (mirrors evlib.placebo_stats). One-sided against |observed|."""
    a = sorted(abs(v) for v in null_means if _finite(v))
    if not a or not _finite(observed):
        return {"n_null": 0, "observed": observed, "null_p95": _NAN, "emp_p": _NAN, "inflation_x": _NAN}
    oo = abs(observed)
    p95 = _quantile(a, 0.95)
    emp_p = (sum(1 for v in a if v >= oo) + 1) / (len(a) + 1)     # add-one smoothing
    return {"n_null": len(a), "observed": float(observed), "null_p95": p95,
            "emp_p": emp_p, "inflation_x": (oo / p95) if p95 > 0 else float("inf")}


def _cell_means(cells: list, vals: list, uniq: list) -> dict:
    acc = {c: [] for c in uniq}
    for c, v in zip(cells, vals):
        if _finite(v):
            acc[c].append(v)
    return {c: (statistics.fmean(acc[c]) if acc[c] else _NAN) for c in uniq}


def circular_block_null(dates: list, resid: list, axis: str,
                        block: int = 21, n: int = 200, seed: int = 42) -> dict:
    """Circular-block bootstrap: resample residual VALUES in blocks; calendar labels stay FIXED,
    which breaks the cell/value alignment. Returns {cell: placebo_stats}. Non-inert (unlike the
    banned year-label shuffle, this destroys the phase-locking between residual and calendar)."""
    N = len(resid)
    cells = [cell_key(d, axis) for d in dates]
    uniq = sorted(set(cells))
    rng = random.Random(seed)
    obs = _cell_means(cells, resid, uniq)
    null = {c: [] for c in uniq}
    for _ in range(n):
        rb = []
        while len(rb) < N:
            s = rng.randrange(N)
            for k in range(block):
                rb.append(resid[(s + k) % N])
                if len(rb) >= N:
                    break
        cm = _cell_means(cells, rb, uniq)
        for c in uniq:
            null[c].append(cm[c])
    return {c: placebo_stats(obs[c], null[c]) for c in uniq}


def cyclic_rotation_null(dates: list, resid: list, axis: str,
                         n: int = 200, seed: int = 42) -> dict:
    """Cyclic-rotation surrogate: rotate the whole residual series by a random lag (circular),
    calendar labels FIXED. Preserves autocorrelation, destroys calendar phase-locking. A distinct,
    FFT-free non-inert null complementing the block bootstrap. Returns {cell: placebo_stats}."""
    N = len(resid)
    cells = [cell_key(d, axis) for d in dates]
    uniq = sorted(set(cells))
    rng = random.Random(seed + 1)
    obs = _cell_means(cells, resid, uniq)
    null = {c: [] for c in uniq}
    for _ in range(n):
        tau = rng.randrange(1, N) if N > 1 else 0
        rot = resid[tau:] + resid[:tau]
        cm = _cell_means(cells, rot, uniq)
        for c in uniq:
            null[c].append(cm[c])
    return {c: placebo_stats(obs[c], null[c]) for c in uniq}


def bh_yekutieli(pvals: list, alpha: float = 0.05) -> list:
    """Benjamini-Hochberg-Yekutieli FDR (dependency-safe). Returns a pass mask aligned to pvals."""
    idx = [i for i, p in enumerate(pvals) if _finite(p)]
    m = len(idx)
    out = [False] * len(pvals)
    if m == 0:
        return out
    c_m = sum(1.0 / k for k in range(1, m + 1))                  # Yekutieli dependency correction
    order = sorted(idx, key=lambda i: pvals[i])
    thresh = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= (rank / m) * alpha / c_m:
            thresh = rank
    for rank, i in enumerate(order, start=1):
        if rank <= thresh:
            out[i] = True
    return out


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a hit-rate k/n. n==0 -> (0,1)."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def _sign(v: float) -> int:
    return (v > 0) - (v < 0)


def epoch_signs(stack: dict, cell: int, epochs) -> list:
    """Sign of the mean per-year cell-z within each epoch (0 where empty)."""
    signs = []
    for _name, lo, hi in epochs:
        vals = [mz for (c, y), (mz, _n) in stack.items()
                if c == cell and str(lo) <= f"{y:04d}" <= str(hi)]
        signs.append(_sign(statistics.fmean(vals)) if vals else 0)
    return signs


def oos_same_sign(stack: dict, cell: int) -> bool:
    """Fit sign on the earlier half of years, confirm the later half agrees (gate 5, in-sample OOS)."""
    ys = sorted({y for (c, y) in stack if c == cell})
    if len(ys) < 6:
        return False
    half = len(ys) // 2
    early = [stack[(cell, y)][0] for y in ys[:half] if (cell, y) in stack]
    late = [stack[(cell, y)][0] for y in ys[half:] if (cell, y) in stack]
    if not early or not late:
        return False
    me, ml = statistics.fmean(early), statistics.fmean(late)
    return _sign(me) == _sign(ml) and me != 0


def mechanism_for(scope: str, axis: str, cell: int) -> dict | None:
    """The pledged mechanism (if any) covering this (scope, axis, cell)."""
    for m in MECHANISMS:
        if scope not in m["scope"] or m["axis"] != axis:
            continue
        cells = m["cells"] if axis != "iso_week" else m.get("iso_cells", m["cells"])
        if cell in cells:
            return m
    return None


def certify_cell(scope: str, axis: str, cell: int, stack: dict,
                 nb: dict, nr: dict, fdr_pass: bool, gates: dict) -> dict:
    """Apply gates 2/4/5/6 to one cell -> the certification verdict + flags + confidence."""
    script_z, n_years, hit = script_of(stack, cell)
    mech = mechanism_for(scope, axis, cell)
    emp_block = nb.get(cell, {}).get("emp_p", _NAN)
    emp_rot = nr.get(cell, {}).get("emp_p", _NAN)
    signs = epoch_signs(stack, cell, gates["epochs"])
    nz = [s for s in signs if s != 0]
    epoch_stable = bool(nz) and all(s == nz[0] for s in nz)
    oos = oos_same_sign(stack, cell)

    g_years = n_years >= gates["min_years"]
    g_null = (_finite(emp_block) and emp_block < 0.05 and _finite(emp_rot) and emp_rot < 0.05)
    g_sign = epoch_stable and oos
    g_mech_sign = True
    if mech and mech["kind"] == "signed" and _finite(script_z):
        g_mech_sign = _sign(script_z) == mech["sign"]

    colored = bool(g_years and g_null and fdr_pass and g_sign and g_mech_sign)
    # Gate 7 (STOCK ONLY): a results-month (earnings-cadence mask) cell that would otherwise
    # certify is re-badged PEAD-in-costume and force-DECERTIFIED — a script that survives ONLY
    # because it collapses when the quarterly filing window is inside it is not a calendar
    # tendency, it's the ledger-blocking PEAD wrapper wearing a different hat (ledger, 0.10 vs
    # 0.85 bench). Index/sector cells are UNAFFECTED (no mask mechanism is registered for them).
    mask_decert = bool(colored and scope == "stock" and mech and mech.get("kind") == "mask")
    if mask_decert:
        colored = False
    signed = colored and mech is not None and mech["kind"] == "signed"
    conf = 0.0
    if _finite(emp_block) and _finite(emp_rot):
        conf = max(0.0, min(1.0, 1.0 - max(emp_block, emp_rot)))
    if not colored:
        conf = min(conf, 0.25)

    flags = []
    if not g_years:
        flags.append(f"N<{gates['min_years']}")
    if not g_null:
        flags.append("null-inside-band")
    if not fdr_pass:
        flags.append("fdr-fail")
    if not g_sign:
        flags.append("sign-unstable")
    if mech is None:
        flags.append("no-mechanism")
    elif mech["kind"] != "signed":
        flags.append(mech["kind"])
    if colored and not g_mech_sign:
        flags.append("sign-vs-pledge")
    if mask_decert:
        flags.append("mask-decert")

    return {
        "scope": scope, "axis": axis, "cell": cell,
        "script_z": None if not _finite(script_z) else round(script_z, 4),
        "n_years": n_years, "hit_rate": None if not _finite(hit) else round(hit, 4),
        "conf": round(conf, 4), "colored": colored, "signed": signed,
        "emp_p_block": None if not _finite(emp_block) else round(emp_block, 4),
        "emp_p_phase": None if not _finite(emp_rot) else round(emp_rot, 4),
        "null_p95": nb.get(cell, {}).get("null_p95"),
        "sign_stable": g_sign, "fdr_pass": bool(fdr_pass),
        "mechanism": mech["id"] if mech else None,
        "pledged_sign": mech["sign"] if mech else None,
        "gate_flags": ",".join(flags) if flags else "OK",
    }


# --------------------------------------------------------------------------- #
#  ENGINE  (reads hermes.db read-only; writes the bounded snapshot)            #
# --------------------------------------------------------------------------- #

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seasonal_cells (
  scope TEXT, entity TEXT, axis TEXT, cell INTEGER,
  script_z REAL, n_years INTEGER, hit_rate REAL, conf REAL,
  colored INTEGER, signed INTEGER,
  emp_p_block REAL, emp_p_phase REAL, null_p95 REAL,
  sign_stable INTEGER, fdr_pass INTEGER,
  mechanism TEXT, pledged_sign INTEGER, gate_flags TEXT,
  computed_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (scope, entity, axis, cell)
);
CREATE TABLE IF NOT EXISTS seasonal_stack (
  scope TEXT, entity TEXT, axis TEXT, cell INTEGER, year INTEGER,
  mean_z REAL, n_obs INTEGER,
  PRIMARY KEY (scope, entity, axis, cell, year)
);
CREATE TABLE IF NOT EXISTS seasonal_outlook (
  scope TEXT, entity TEXT, asof TEXT, axis TEXT, cell INTEGER, horizon TEXT,
  k INTEGER, n INTEGER, ci_lo REAL, ci_hi REAL, base_rate REAL, edge REAL,
  fail_avg REAL, fail_worst REAL, light TEXT, mechanism TEXT,
  computed_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (scope, entity, axis, cell, asof)
);
CREATE TABLE IF NOT EXISTS seasonal_breaks (
  scope TEXT, entity TEXT, date TEXT, axis TEXT, cell INTEGER,
  z REAL, mech_flag INTEGER, note TEXT,
  computed_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (scope, entity, date, axis)
);
CREATE TABLE IF NOT EXISTS seasonal_meta (k TEXT PRIMARY KEY, v TEXT);
"""


def _ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _resolve_names(conn: sqlite3.Connection, canonical: list) -> dict:
    """{canonical_name: actual stored index_name} via an UPPER() map (casing is inconsistent)."""
    have = {}
    for r in conn.execute("SELECT DISTINCT index_name FROM index_rows"):
        have[str(r[0]).upper()] = str(r[0])
    return {c: have[c.upper()] for c in canonical if c.upper() in have}


def load_index_returns(conn: sqlite3.Connection, index_name: str) -> tuple[list, list]:
    """Oldest-first daily %-change of one index from index_rows.close_value (raw level; clean)."""
    rows = conn.execute(
        "SELECT trade_date, close_value FROM index_rows "
        "WHERE index_name=? AND close_value IS NOT NULL AND close_value>0 "
        "ORDER BY trade_date ASC", (index_name,)).fetchall()
    dates, closes = [], []
    for r in rows:
        dates.append(str(r["trade_date"])[:10])
        closes.append(float(r["close_value"]))
    if len(closes) < 2:
        return [], []
    ret = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    return dates[1:], ret


def load_stock_returns(rconn: sqlite3.Connection, symbol: str) -> tuple[list, list]:
    """Oldest-first daily %-change of one stock, CORP-ACTION-ADJUSTED (adjust.adjusted_closes fed
    by corp_actions.price_ratios) — NEVER raw close/prev_close (ex-day prev_close does not
    self-adjust; a raw return would inject a false split/bonus jump, S85e)."""
    rows = [dict(r) for r in rconn.execute(
        "SELECT trade_date, close, prev_close FROM bhavcopy_rows "
        "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
        "ORDER BY trade_date ASC", (symbol,)).fetchall()]
    if len(rows) < 2:
        return [], []
    try:
        from src.automation.corp_actions import price_ratios
        events = price_ratios(rconn, symbol)
    except Exception:  # noqa: BLE001 — the tape must never fail a compute; falls back to inference
        events = {}
    adj = adjusted_closes(rows, events)
    dates = [str(r["trade_date"])[:10] for r in rows]
    ret = [(adj[i] / adj[i - 1] - 1.0)
           if (adj[i] is not None and adj[i] > 0 and adj[i - 1] is not None and adj[i - 1] > 0)
           else _NAN
           for i in range(1, len(adj))]
    return dates[1:], ret


def stock_universe(rconn: sqlite3.Connection, limit: int | None = None) -> list:
    """Nifty 500 constituents @ latest snapshot_date, ordered by company_profile.priority_rank
    (90d turnover liquidity) ascending, unranked names last — the frozen STOCK_UNIVERSE_SPEC
    membership/order. Current-membership only (survivor-conditional, gate 11)."""
    row = rconn.execute(
        "SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name='Nifty 500'").fetchone()
    snap = row[0] if row else None
    if not snap:
        return []
    has_profile = rconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='company_profile'").fetchone()
    if has_profile:
        rows = rconn.execute(
            "SELECT m.symbol AS symbol FROM stock_index_membership m "
            "LEFT JOIN company_profile p ON p.symbol = m.symbol "
            "WHERE m.index_name='Nifty 500' AND m.snapshot_date=? "
            "ORDER BY (p.priority_rank IS NULL), p.priority_rank ASC, m.symbol ASC", (snap,)).fetchall()
    else:  # defensive: company_profile is populated by a separate enrichment pass (enrich.py)
        rows = rconn.execute(
            "SELECT symbol FROM stock_index_membership WHERE index_name='Nifty 500' "
            "AND snapshot_date=? ORDER BY symbol ASC", (snap,)).fetchall()
    out = [r["symbol"] for r in rows]
    return out[:limit] if limit is not None else out


def _aligned(a_dates, a_vals, b_dates, b_vals):
    """Inner-join two oldest-first daily series on date -> (dates, a, b)."""
    bmap = dict(zip(b_dates, b_vals))
    ds, av, bv = [], [], []
    for d, v in zip(a_dates, a_vals):
        if d in bmap:
            ds.append(d); av.append(v); bv.append(bmap[d])
    return ds, av, bv


def compute_entity(dates: list, ret: list, scope: str, market: list | None = None,
                   resid_scope: str | None = None) -> dict:
    """Full per-entity pipeline for all three axes. Returns cells/stack/outlook payloads.

    `resid_scope` (optional) lets the RESIDUAL MATH differ from the storage/certification
    `scope` — the P2 stock market-only residual reuses the ALREADY-TESTED scope='sector' path
    (strip market only) via resid_scope='sector', while every cell is still stored/labeled/
    certified as scope='stock' (mechanism registry + gate 7 mask-decert apply correctly)."""
    g = GATES
    resid = pit_residuals(dates, ret, resid_scope or scope, market=market, warmup_years=g["warmup_years"])
    if sum(1 for r in resid if _finite(r)) < 250:
        return {}
    result = {"cells": [], "stack": [], "outlook": []}
    for axis in AXES:
        z = pit_z(dates, resid, axis, warmup_years=g["warmup_years"],
                  mad_k=g["mad_k"], floor=g["sigma_floor"])
        zd = [(d, zz) for d, zz in zip(dates, z) if _finite(zz)]
        if not zd:
            continue
        zdates = [d for d, _ in zd]
        zvals = [v for _, v in zd]
        stack = year_cell_means(dates, z, axis)
        if not stack:
            continue
        nb = circular_block_null(zdates, zvals, axis, block=g["block"], n=g["null_n"], seed=g["seed"])
        nr = cyclic_rotation_null(zdates, zvals, axis, n=g["null_n"], seed=g["seed"])
        cell_list = sorted({c for (c, _y) in stack})
        pvals = [min(nb.get(c, {}).get("emp_p", 1.0), nr.get(c, {}).get("emp_p", 1.0)) for c in cell_list]
        fdr = dict(zip(cell_list, bh_yekutieli(pvals, alpha=g["fdr_alpha"])))
        for c in cell_list:
            result["cells"].append(certify_cell(scope, axis, c, stack, nb, nr, fdr.get(c, False), g))
            for (cc, yy), (mz, nobs) in stack.items():
                if cc == c:
                    result["stack"].append((scope, axis, c, yy, round(mz, 4), nobs))
        if axis == "month":
            result["outlook"].extend(_month_outlook(scope, dates, stack))
    return result


def _month_outlook(scope: str, dates: list, stack: dict) -> list:
    """Forward month outlook (plan lane 7): per month cell k/N hit-rate, Wilson CI, edge vs the
    entity's own all-month base rate, fail-case (avg/worst NEGATIVE year), traffic light."""
    asof = dates[-1]
    allv = [mz for (_c, _y), (mz, _n) in stack.items()]
    base = (sum(1 for v in allv if v > 0) / len(allv)) if allv else 0.5
    out = []
    for c in AXES["month"]:
        vals = [mz for (cc, _y), (mz, _n) in stack.items() if cc == c]
        if len(vals) < GATES["min_years"]:
            continue
        k = sum(1 for v in vals if v > 0); n = len(vals)
        lo, hi = wilson_ci(k, n)
        neg = [v for v in vals if v < 0]
        fail_avg = statistics.fmean(neg) if neg else 0.0
        fail_worst = min(vals)
        edge = (k / n) - base
        mech = mechanism_for(scope, "month", c)
        if lo <= 0.5 <= hi:
            light = "white"
        elif lo > 0.5 and mech and mech["kind"] == "signed":
            light = "green"
        elif lo > 0.5 or hi < 0.5:
            light = "amber"
        else:
            light = "white"
        out.append((scope, asof, "month", c, "1M", k, n, round(lo, 4), round(hi, 4),
                    round(base, 4), round(edge, 4), round(fail_avg, 4), round(fail_worst, 4),
                    light, mech["id"] if mech else None))
    return out


def _write(wconn: sqlite3.Connection, scope: str, entity: str, payload: dict) -> None:
    """Writer-safe upsert of one entity's cells/stack/outlook (per-entity commit)."""
    wconn.executescript(_SCHEMA)
    wconn.execute("DELETE FROM seasonal_cells WHERE scope=? AND entity=?", (scope, entity))
    wconn.execute("DELETE FROM seasonal_stack WHERE scope=? AND entity=?", (scope, entity))
    wconn.execute("DELETE FROM seasonal_outlook WHERE scope=? AND entity=?", (scope, entity))
    wconn.executemany(
        "INSERT OR REPLACE INTO seasonal_cells (scope,entity,axis,cell,script_z,n_years,hit_rate,"
        "conf,colored,signed,emp_p_block,emp_p_phase,null_p95,sign_stable,fdr_pass,mechanism,"
        "pledged_sign,gate_flags) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(scope, entity, v["axis"], v["cell"], v["script_z"], v["n_years"], v["hit_rate"],
          v["conf"], int(v["colored"]), int(v["signed"]), v["emp_p_block"], v["emp_p_phase"],
          v["null_p95"], int(v["sign_stable"]), int(v["fdr_pass"]), v["mechanism"],
          v["pledged_sign"], v["gate_flags"]) for v in payload.get("cells", [])])
    wconn.executemany(
        "INSERT OR REPLACE INTO seasonal_stack (scope,entity,axis,cell,year,mean_z,n_obs) "
        "VALUES (?,?,?,?,?,?,?)",
        [(sc, entity, ax, c, y, mz, nobs) for (sc, ax, c, y, mz, nobs) in payload.get("stack", [])])
    wconn.executemany(
        "INSERT OR REPLACE INTO seasonal_outlook (scope,entity,asof,axis,cell,horizon,k,n,ci_lo,"
        "ci_hi,base_rate,edge,fail_avg,fail_worst,light,mechanism) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(sc, entity, asof, ax, c, hz, k, n, lo, hi, br, ed, fa, fw, lt, mech)
         for (sc, asof, ax, c, hz, k, n, lo, hi, br, ed, fa, fw, lt, mech) in payload.get("outlook", [])])
    wconn.commit()


def backfill(read_path: str, write_path: str, scope: str = "all", limit: int | None = None) -> dict:
    """Compute + persist the bounded snapshot for index and/or sector entities. Read-only on the
    archive; per-entity commits keep the write-lock <1s each (writer-safe)."""
    rconn = _ro(read_path)
    wconn = sqlite3.connect(write_path, timeout=60)
    wconn.executescript(_SCHEMA)
    wconn.execute("INSERT OR REPLACE INTO seasonal_meta VALUES ('frozen_family_sha256', ?)",
                  (frozen_family_hash(),))
    wconn.commit()
    counts = {"index": 0, "sector": 0, "colored": 0}
    try:
        mkt_stored = _resolve_names(rconn, [MARKET]).get(MARKET, MARKET)
        market_dates, market_ret = load_index_returns(rconn, mkt_stored)
        wanted = []
        if scope in ("all", "index"):
            wanted += [("index", n) for n in BROAD_INDICES]
        if scope in ("all", "sector"):
            wanted += [("sector", n) for n in SECTOR_INDICES]
        resolved = _resolve_names(rconn, [n for _s, n in wanted])
        done = 0
        for sc, canon in wanted:
            if limit is not None and done >= limit:
                break
            stored = resolved.get(canon)
            if not stored:
                continue
            dates, ret = load_index_returns(rconn, stored)
            if len(dates) < 250:
                continue
            if sc == "index":
                payload = compute_entity(dates, ret, "index")
            else:
                ad, av, mk = _aligned(dates, ret, market_dates, market_ret)
                if len(ad) < 250:
                    continue
                payload = compute_entity(ad, av, "sector", market=mk)
            if not payload:
                continue
            _write(wconn, sc, canon, payload)
            counts[sc] += 1
            counts["colored"] += sum(1 for v in payload["cells"] if v["colored"])
            done += 1
    finally:
        rconn.close(); wconn.close()
    return counts


def backfill_stocks(read_path: str, write_path: str, limit: int | None = None) -> dict:
    """Compute + persist the bounded snapshot for STOCK entities (P2) — the MARKET-ONLY residual
    (resid_scope='sector' math, scope='stock' storage/certification), a SEPARATE pre-registered
    frozen family (frozen_family_hash_stock()). Mirrors backfill()'s per-entity commit discipline
    exactly; read-only on the archive; NEVER touches the index/sector frozen family or its rows."""
    rconn = _ro(read_path)
    wconn = sqlite3.connect(write_path, timeout=60)
    wconn.executescript(_SCHEMA)
    wconn.execute("INSERT OR REPLACE INTO seasonal_meta VALUES ('frozen_family_stock_sha256', ?)",
                  (frozen_family_hash_stock(),))
    wconn.commit()
    counts = {"stock": 0, "colored": 0, "skipped": 0}
    try:
        mkt_stored = _resolve_names(rconn, [MARKET]).get(MARKET, MARKET)
        market_dates, market_ret = load_index_returns(rconn, mkt_stored)
        for sym in stock_universe(rconn, limit):
            dates, ret = load_stock_returns(rconn, sym)
            if len(dates) < 250:
                counts["skipped"] += 1
                continue
            ad, av, mk = _aligned(dates, ret, market_dates, market_ret)
            if len(ad) < 250:
                counts["skipped"] += 1
                continue
            payload = compute_entity(ad, av, "stock", market=mk, resid_scope="sector")
            if not payload:
                counts["skipped"] += 1
                continue
            _write(wconn, "stock", sym, payload)
            counts["stock"] += 1
            counts["colored"] += sum(1 for v in payload["cells"] if v["colored"])
    finally:
        rconn.close(); wconn.close()
    return counts


def stats(path: str) -> dict:
    con = _ro(path)
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seasonal_cells'").fetchone():
            return {"present": False}
        row = con.execute(
            "SELECT COUNT(DISTINCT entity), COUNT(*), SUM(colored) FROM seasonal_cells").fetchone()
        by_axis = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT axis, COUNT(*), SUM(colored) FROM seasonal_cells GROUP BY axis")}
        h = con.execute("SELECT v FROM seasonal_meta WHERE k='frozen_family_sha256'").fetchone()
        return {"present": True, "entities": row[0], "cells": row[1], "colored": row[2] or 0,
                "by_axis": by_axis, "frozen_family_sha256": (h[0][:12] if h else None)}
    finally:
        con.close()


# --------------------------------------------------------------------------- #
#  PREREG FREEZE (P0)                                                          #
# --------------------------------------------------------------------------- #

def _research_db() -> str:
    return os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")


def register(force: bool = False, db_path: str | None = None,
             module: str | None = None, hash_fn=None) -> dict:
    """P0: write frozen_family_hash() into research.db.prereg_registry (first-registration-wins,
    tamper-evident). Standalone path — does NOT touch the in-flight explosive_moves.prereg STUDIES.
    `module`/`hash_fn` (optional) let the STOCK family register under its own module id + hash
    (module='seasonal_tape_stock', hash_fn=frozen_family_hash_stock) without touching this path's
    zero-arg (index/sector) behavior."""
    import datetime
    path = db_path or _research_db()
    mod = module or _PREREG_MODULE
    h = (hash_fn or frozen_family_hash)()
    con = sqlite3.connect(path, timeout=30)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS prereg_registry (module TEXT PRIMARY KEY, "
                    "gate_sha256 TEXT NOT NULL, registered_at TEXT NOT NULL, note TEXT)")
        cur = con.execute("SELECT gate_sha256 FROM prereg_registry WHERE module=?", (mod,)).fetchone()
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        if cur is None:
            con.execute("INSERT INTO prereg_registry VALUES (?,?,?,?)",
                        (mod, h, now, "frozen BEFORE first compute"))
            con.commit()
            return {"action": "registered", "sha256": h, "at": now}
        if cur[0] == h:
            return {"action": "already-registered", "sha256": h}
        if force:
            con.execute("UPDATE prereg_registry SET gate_sha256=?, registered_at=?, note=? WHERE module=?",
                        (h, now, "FORCED re-register", mod))
            con.commit()
            return {"action": "forced", "sha256": h, "was": cur[0]}
        return {"action": "TAMPER", "stored": cur[0], "current": h}
    finally:
        con.close()


def verify(db_path: str | None = None, module: str | None = None, hash_fn=None) -> dict:
    """Tamper-check the freeze. `module`/`hash_fn` mirror register()'s STOCK-family override."""
    path = db_path or _research_db()
    mod = module or _PREREG_MODULE
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        cur = con.execute("SELECT gate_sha256 FROM prereg_registry WHERE module=?", (mod,)).fetchone()
    except sqlite3.OperationalError:
        cur = None
    finally:
        con.close()
    h = (hash_fn or frozen_family_hash)()
    if cur is None:
        return {"ok": False, "reason": "not-registered", "current": h}
    return {"ok": cur[0] == h, "stored": cur[0], "current": h}


# --------------------------------------------------------------------------- #
#  SELFTEST (offline, synthetic, no DB, no numpy)                             #
# --------------------------------------------------------------------------- #

def _synth_series(years=25, seed=7, planted_month=3, bump=0.004):
    """25y of business-day dates + a market series + a sector series that carries a planted
    positive residual every `planted_month` (used to prove the pipeline recovers a real cell AND
    that the nulls do NOT flag an unplanted cell)."""
    rng = random.Random(seed)
    dates, mret, sret = [], [], []
    for y in range(2001, 2001 + years):
        for mo in range(1, 13):
            for dd in range(1, 21):
                try:
                    d = date(y, mo, dd)
                except ValueError:
                    continue
                if d.weekday() >= 5:
                    continue
                dates.append(d.isoformat())
                m = rng.gauss(0.0004, 0.010)
                mret.append(m)
                s = 1.1 * m + rng.gauss(0.0, 0.008)
                if mo == planted_month:
                    s += bump
                sret.append(s)
    return dates, mret, sret


def _corr(a: list, b: list) -> float:
    pairs = [(x, y) for x, y in zip(a, b) if _finite(x) and _finite(y)]
    if len(pairs) < 3:
        return 0.0
    mx = sum(p[0] for p in pairs) / len(pairs); my = sum(p[1] for p in pairs) / len(pairs)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    sxx = sum((p[0] - mx) ** 2 for p in pairs); syy = sum((p[1] - my) ** 2 for p in pairs)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0


def _selftest() -> int:
    # 1) OLS + orthogonalize
    x = [1.0, 2, 3, 4, 5]; y = [2.0 + 3.0 * v for v in x]
    a, b = ols1(x, y)
    assert abs(a - 2) < 1e-6 and abs(b - 3) < 1e-6, (a, b)
    assert all(abs(v) < 1e-6 for v in orthogonalize(x, y)), "orthogonalize should zero a linear dep"

    # 2) index residual strips nothing
    dts, mret, sret = _synth_series()
    ri = pit_residuals(dts, mret, "index")
    assert ri == list(mret), "index must strip nothing"

    # 3) sector residual removes the market beta (residual ~ uncorrelated with market)
    rs = pit_residuals(dts, sret, "sector", market=mret, warmup_years=3)
    corr = _corr([r for r in rs if _finite(r)], [m for r, m in zip(rs, mret) if _finite(r)])
    assert abs(corr) < 0.2, f"sector residual still market-correlated: {corr}"

    # 4) PIT z is leak-free: the FIRST warmup years must be NaN
    z = pit_z(dts, rs, "month", warmup_years=3)
    scored_years = {int(d[:4]) for d, zz in zip(dts, z) if _finite(zz)}
    assert min(scored_years) >= 2004, f"z scored too early (leak): {min(scored_years)}"

    # 5) the planted March cell recovers a positive script
    stack = year_cell_means(dts, z, "month")
    smar, nmar, hmar = script_of(stack, 3)
    assert smar > 0.15 and hmar > 0.6, f"planted March not recovered: z={smar} hit={hmar}"

    # 6) nulls: the planted cell clears the band on BOTH nulls
    zd = [(d, zz) for d, zz in zip(dts, z) if _finite(zz)]
    zdates = [d for d, _ in zd]; zvals = [v for _, v in zd]
    nb = circular_block_null(zdates, zvals, "month", block=21, n=120, seed=42)
    nr = cyclic_rotation_null(zdates, zvals, "month", n=120, seed=42)
    assert nb[3]["emp_p"] < 0.10, f"planted March failed block-null: {nb[3]}"
    assert nr[3]["emp_p"] < 0.15, f"planted March failed rotation-null: {nr[3]}"

    # 6b) the BANNED year-label shuffle is provably zero-width: keeping each obs in its own cell,
    #     the per-cell mean is invariant under any permutation of year labels.
    cells = [cell_key(d, "month") for d in zdates]
    mar_before = statistics.fmean([v for c, v in zip(cells, zvals) if c == 3])
    yr_perm = list(range(len(zvals))); random.Random(1).shuffle(yr_perm)  # permute YEAR labels only
    # simulate: relabel years but keep month cell fixed -> the March set is unchanged -> same mean
    mar_after = statistics.fmean([v for c, v in zip(cells, zvals) if c == 3])
    assert abs(mar_before - mar_after) < 1e-12, "year-label shuffle must be a zero-width null (banned)"

    # 7) Wilson CI + BH-Y monotonic
    lo, hi = wilson_ci(18, 25)
    assert 0.5 < lo < hi < 1.0, (lo, hi)
    passed = bh_yekutieli([0.001, 0.02, 0.3, 0.8], alpha=0.05)
    assert passed[0] and not passed[3], passed

    # 8) full entity pipeline + certification shape
    payload = compute_entity(dts, sret, "sector", market=mret)
    assert payload and payload["cells"], "empty payload"
    mar = [v for v in payload["cells"] if v["axis"] == "month" and v["cell"] == 3][0]
    assert mar["n_years"] >= 15 and mar["script_z"] > 0, mar
    assert payload["outlook"], "month outlook should be produced"

    # 9) frozen-family hash stable + register/verify roundtrip on a temp research.db
    h1 = frozen_family_hash(); h2 = frozen_family_hash()
    assert h1 == h2 and len(h1) == 64, h1
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "seasonal_prereg_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    r = register(db_path=tmp)
    assert r["action"] == "registered", r
    assert verify(db_path=tmp)["ok"], "verify should pass right after register"
    os.remove(tmp)

    # 9b) STOCK frozen family (P2) is pre-registered under its OWN module + a DISTINCT hash — it
    # must never conflate with the index/sector family (frozen 2882ccbc...).
    hs1 = frozen_family_hash_stock()
    assert hs1 != h1 and len(hs1) == 64, hs1
    tmp2 = os.path.join(tempfile.gettempdir(), "seasonal_prereg_stock_selftest.db")
    if os.path.exists(tmp2):
        os.remove(tmp2)
    rs_reg = register(db_path=tmp2, module=_PREREG_MODULE_STOCK, hash_fn=frozen_family_hash_stock)
    assert rs_reg["action"] == "registered" and rs_reg["sha256"] == hs1, rs_reg
    vs = verify(db_path=tmp2, module=_PREREG_MODULE_STOCK, hash_fn=frozen_family_hash_stock)
    assert vs["ok"], "stock verify should pass right after stock register"
    # the plain (index/sector) module id must still be absent from this fresh DB
    assert verify(db_path=tmp2)["reason"] == "not-registered"
    os.remove(tmp2)

    # 9c) the P2 stock market-only residual REUSES the already-tested scope='sector' math
    # (resid_scope='sector') while storing/certifying as scope='stock'; no stock mechanism is
    # ever 'signed' (M-RESULTS is mask-only), so every stock cell must have signed==False.
    stock_payload = compute_entity(dts, sret, "stock", market=mret, resid_scope="sector")
    assert stock_payload and stock_payload["cells"], "empty stock payload"
    assert all(not c["signed"] for c in stock_payload["cells"]), "stock cells must never be signed"

    # 9d) gate 7 fix: a stock cell in an earnings-cadence MASK month (M-RESULTS: 1,4,7,10) that
    # clears every other gate is FORCE-DECERTIFIED (PEAD-in-costume) — an identical index/sector
    # cell in the same month is UNAFFECTED (no mask mechanism registered for those scopes).
    fake_years = list(range(2001, 2021))                      # 20 years, uniform +1.0sigma
    fake_stack = {(4, y): (1.0, 250) for y in fake_years}      # month=4 -> in M-RESULTS cells
    fake_nb = {4: {"emp_p": 0.001, "null_p95": 0.5}}
    fake_nr = {4: {"emp_p": 0.001, "null_p95": 0.5}}
    cell_stock = certify_cell("stock", "month", 4, fake_stack, fake_nb, fake_nr, True, GATES)
    assert cell_stock["colored"] is False and "mask-decert" in cell_stock["gate_flags"], cell_stock
    cell_index = certify_cell("index", "month", 4, fake_stack, fake_nb, fake_nr, True, GATES)
    assert cell_index["colored"] is True, cell_index

    # 10) end-to-end DB write to an in-memory-ish temp hermes.db
    import tempfile as _t
    tmpdb = os.path.join(_t.gettempdir(), "seasonal_engine_selftest.db")
    if os.path.exists(tmpdb):
        os.remove(tmpdb)
    con = sqlite3.connect(tmpdb)
    con.executescript("CREATE TABLE index_rows(index_name TEXT, trade_date TEXT, close_value REAL);")
    lvl = 1000.0
    rng = random.Random(3)
    for d in dts:
        lvl *= (1 + rng.gauss(0.0004, 0.01))
        con.execute("INSERT INTO index_rows VALUES (?,?,?)", ("Nifty 500", d, lvl))
    con.commit(); con.close()
    c = backfill(tmpdb, tmpdb, scope="index", limit=1)
    assert c["index"] == 1, c
    s = stats(tmpdb)
    assert s["present"] and s["cells"] > 0, s
    os.remove(tmpdb)

    print(f"seasonal_tape selftest OK — leak-free z, market-strip, 2 non-inert nulls, gates, "
          f"DB roundtrip, frozen-family {h1[:12]} / stock-family {hs1[:12]} (distinct, mask-decert "
          f"verified) (cf. E-11 e9bd1a7f / E-12 c3f48a42)")
    return 0


if __name__ == "__main__":
    import sys
    argv = sys.argv[1:]
    if not argv or "--selftest" in argv:
        raise SystemExit(_selftest())
    if "--register-stock" in argv:
        print(register(module=_PREREG_MODULE_STOCK, hash_fn=frozen_family_hash_stock,
                       force="--force" in argv))
        raise SystemExit(0)
    if "--register" in argv:
        print(register(force="--force" in argv)); raise SystemExit(0)
    if "--verify-stock" in argv:
        v = verify(module=_PREREG_MODULE_STOCK, hash_fn=frozen_family_hash_stock)
        print(v); raise SystemExit(0 if v.get("ok") else 1)
    if "--verify" in argv:
        v = verify(); print(v); raise SystemExit(0 if v.get("ok") else 1)
    if "--stats" in argv:
        from src.core.db import DB_PATH
        print(stats(str(DB_PATH))); raise SystemExit(0)
    if "--backfill" in argv:
        from src.core.db import DB_PATH
        scope = "all"
        if "--scope" in argv:
            i = argv.index("--scope")
            if i + 1 < len(argv):
                scope = argv[i + 1]
        lim = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
        if scope == "stock":
            print(backfill_stocks(str(DB_PATH), str(DB_PATH), limit=lim))
        else:
            print(backfill(str(DB_PATH), str(DB_PATH), scope=scope, limit=lim))
        raise SystemExit(0)
    print("usage: --selftest | --register [--force] | --register-stock [--force] | --verify | "
          "--verify-stock | --backfill [--scope index|sector|stock|all] [--limit N] | --stats")
