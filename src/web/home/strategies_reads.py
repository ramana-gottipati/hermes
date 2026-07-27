"""src/web/home/strategies_reads.py — the Strategies-workspace read layer (Graphite, lane W3-A).

The bounded, self-contained data layer behind `/dash/home/strategies*`. Same contract as
`src/web/home/reads.py`: **plain rows / dicts only, never HTML**, never a render import. It may reuse
ENGINE modules (`src.automation.*`) — which is where the classification rules are single-sourced —
but never a `src/web/*` VIEW module, because the isolation gate (tests/test_home_isolation.py) bans
preview/legacy render coupling and the whole point of the port is to carry the EVIDENCE, not the DOM.

Everything is defensive: a missing table, a cold DB or an absent engine degrades to an empty result
so the page renders its honest-empty branch instead of 500-ing. Demo constants live at the bottom and
are only ever handed out through `pick()`, which flags them `sample` so the real-vs-demo line stays
honest (standing correction #4).
"""
from __future__ import annotations

import sqlite3

# ── generic helpers (twins of reads._has/_rows, kept local so the two files stay independent) ──


def _has(conn, table: str) -> bool:
    try:
        return bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)).fetchone())
    except Exception:  # noqa: BLE001
        return False


def _rows(conn, sql: str, params=()) -> list:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:  # noqa: BLE001
        return []


def _one(conn, sql: str, params=()):
    try:
        r = conn.execute(sql, params).fetchone()
        return r[0] if r else None
    except Exception:  # noqa: BLE001
        return None


def _latest(conn, table: str, col: str):
    if not _has(conn, table):
        return None
    return _one(conn, "SELECT MAX(" + col + ") FROM " + table)


def pick(live, demo):
    """(data, is_demo) — the home's `_pick` contract. Demo only when the live read is genuinely empty."""
    if live:
        return live, False
    return demo, True


def _f(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


# ── the strategy catalog (hub) ───────────────────────────────────────────────────


def catalog(conn) -> list:
    """One row per tracked strategy — reuses the canonical `strategy_registry.summary` engine
    (count · as-of · health · route), so the hub can never drift from the registry."""
    try:
        from src.automation import strategy_registry as SR
        return list(SR.summary(conn) or [])
    except Exception:  # noqa: BLE001
        return []


def universe_asof(conn) -> dict:
    """The freshness spine for the hub header — every date the workspace depends on."""
    return {
        "bhav": _latest(conn, "bhavcopy_rows", "trade_date"),
        "signals": _latest(conn, "stock_signals", "trade_date"),
        "mep": _latest(conn, "mep_signals", "trade_date"),
        "cpr": _latest(conn, "cpr_signals", "period_end_date"),
        "universe": _one(conn, "SELECT COUNT(*) FROM nse_equity_list") if _has(conn, "nse_equity_list") else None,
    }


# ── model portfolios (the 4 engine-locked books) ────────────────────────────────

# Risk-profile mapping + the fundability verdicts. RATIFIED in docs/redesign-plan-2026-07-17.md
# Part III §J (book -> risk profile -> chip). The measured NUMBERS are NOT restated here — they live
# in docs/strategy-ledger.md and are rendered from `auto_portfolio_nav` at read time.
BOOKS = (
    ("STEADY-25", "Low-volatility × momentum, quarterly, large-cap",
     "Conservative / Core", "FUNDABLE-CORE", "\U0001F4DA"),
    ("CRAFTSMAN-25", "Quality × momentum, monthly", "Balanced / Quality", "GROSS-LENS", "\U0001F4DA"),
    ("PACER-25", "Risk-adjusted momentum, monthly", "Growth / Assertive", "GROSS-LENS", "\U0001F4DA"),
    ("SPRINTER-25", "12-month momentum, monthly", "Aggressive", "GROSS-LENS", "\U0001F4DA"),
)

# Part III §J default column sets — the "BOOK CORE" layer, per risk profile. Rendered from what the
# stored holdings actually carry; anything the store does not have is simply not shown (never faked).
BOOK_COLS = {
    "STEADY-25": ("Target W", "W now", "Since rebal", "Score"),
    "CRAFTSMAN-25": ("Target W", "W now", "Since rebal", "Score"),
    "PACER-25": ("Target W", "W now", "Since rebal", "Score"),
    "SPRINTER-25": ("Target W", "W now", "Since rebal", "Score"),
}


def book_specs() -> list:
    """The engine-locked book definitions, read from the canonical engine where available."""
    out = []
    specs = {}
    try:
        from src.automation import auto_portfolios as AP
        specs = dict(getattr(AP, "SPECS", {}) or {})
    except Exception:  # noqa: BLE001
        specs = {}
    for name, rule, profile, chip, origin in BOOKS:
        s = specs.get(name)
        out.append({"book": name, "rule": rule, "profile": profile, "chip": chip,
                    "origin": origin, "engine": (str(s) if s is not None else "")})
    return out


def book_nav(conn, book: str, since: int = 0) -> list:
    """The NAV series for one book beside its benchmark. `since` = a calendar year floor."""
    if not _has(conn, "auto_portfolio_nav"):
        return []
    sql = ("SELECT rebal_date, nav, bench_nav, n_churned FROM auto_portfolio_nav "
           "WHERE portfolio=? " + (" AND rebal_date >= ? " if since else "") +
           "ORDER BY rebal_date")
    p = (book, str(since) + "-01-01") if since else (book,)
    return _rows(conn, sql, p)


def series_stats(rows: list, nav_key: str = "nav", bench_key: str = "bench_nav") -> dict:
    """Multiple · CAGR · return/vol ratio · max drawdown, for a book and its benchmark.

    🔴 `retvol` is a RETURN / VOLATILITY RATIO — NOT a Sharpe ratio (no risk-free rate is
    subtracted, costs are flat-modelled). The estate-wide label rule (D142) is machine-enforced by
    tests/test_retvol_label_gate.py; every caller must render it with that exact wording.
    """
    out = {"n": len(rows), "start": None, "end": None}
    if len(rows) < 2:
        return out
    xs = [_f(r.get(nav_key)) for r in rows]
    bs = [_f(r.get(bench_key)) for r in rows]
    xs = [x for x in xs if x and x > 0]
    bs = [b for b in bs if b and b > 0]
    if len(xs) < 2:
        return out
    out["start"], out["end"] = rows[0].get("rebal_date"), rows[-1].get("rebal_date")

    def _leg(v):
        mult = v[-1] / v[0]
        # cadence is DERIVED from the row dates, never assumed (D140).
        yrs = _years(rows)
        cagr = ((mult ** (1.0 / yrs)) - 1.0) * 100.0 if yrs and yrs > 0 and mult > 0 else None
        rets = [(v[i] / v[i - 1]) - 1.0 for i in range(1, len(v))]
        m = sum(rets) / len(rets)
        var = sum((r - m) ** 2 for r in rets) / max(1, len(rets) - 1)
        sd = var ** 0.5
        per_yr = (len(rets) / yrs) if yrs else 0
        retvol = ((m * per_yr) / (sd * (per_yr ** 0.5))) if (sd > 0 and per_yr > 0) else None
        peak, dd = v[0], 0.0
        for x in v:
            peak = max(peak, x)
            dd = min(dd, (x / peak) - 1.0)
        return {"mult": mult, "cagr": cagr, "retvol": retvol, "maxdd": dd * 100.0}
    out["book"] = _leg(xs)
    out["bench"] = _leg(bs) if len(bs) >= 2 else None
    return out


def _years(rows: list):
    try:
        a, b = str(rows[0].get("rebal_date")), str(rows[-1].get("rebal_date"))
        ya, yb = int(a[:4]), int(b[:4])
        ma, mb = int(a[5:7]), int(b[5:7])
        return max(0.5, ((yb - ya) * 12 + (mb - ma)) / 12.0)
    except Exception:  # noqa: BLE001
        return None


def book_holdings(conn, book: str, asof: str = "") -> tuple:
    """(rows, rebal_date) — the constituents at a rebalance, enriched with the IDENTITY SPINE
    (Symbol · Sector · CMP) that Part III §J freezes on every book table."""
    if not _has(conn, "auto_portfolio_holdings"):
        return [], None
    date = asof or _one(conn, "SELECT MAX(rebal_date) FROM auto_portfolio_holdings WHERE portfolio=?", (book,))
    if not date:
        return [], None
    rows = _rows(conn, "SELECT symbol, rank, score, weight, px FROM auto_portfolio_holdings "
                       "WHERE portfolio=? AND rebal_date=? ORDER BY rank LIMIT 60", (book, date))
    if not rows:
        return [], date
    _enrich_spine(conn, rows)
    for r in rows:
        px, cmp_ = _f(r.get("px")), _f(r.get("cmp"))
        r["since"] = ((cmp_ / px) - 1.0) * 100.0 if (px and cmp_ and px > 0) else None
        r["w_target"] = _f(r.get("weight"))
    # drifted weight now = value share of the book at CMP
    tot = 0.0
    for r in rows:
        px, cmp_, w = _f(r.get("px")), _f(r.get("cmp")), _f(r.get("weight"))
        r["_v"] = (w * (cmp_ / px)) if (px and cmp_ and w and px > 0) else None
        tot += r["_v"] or 0.0
    for r in rows:
        r["w_now"] = ((r.pop("_v") or 0.0) / tot * 100.0) if tot else None
        if r.get("w_target") is not None:
            r["w_target"] = r["w_target"] * 100.0
    return rows, date


def _enrich_spine(conn, rows: list) -> None:
    """Attach `sector` + `cmp` to any list of dicts carrying `symbol` (bounded IN-clause)."""
    syms = [str(r.get("symbol")) for r in rows if r.get("symbol")][:80]
    if not syms:
        return
    q = ",".join("?" * len(syms))
    sec, cmp_ = {}, {}
    if _has(conn, "stock_signals"):
        for r in _rows(conn, "SELECT symbol, primary_sector FROM stock_signals WHERE symbol IN (" + q
                             + ") GROUP BY symbol", syms):
            sec[r["symbol"]] = r.get("primary_sector")
    if _has(conn, "bhavcopy_rows"):
        for r in _rows(conn, "SELECT symbol, close, MAX(trade_date) d FROM bhavcopy_rows WHERE symbol IN ("
                             + q + ") AND series IN ('EQ','BE') GROUP BY symbol", syms):
            cmp_[r["symbol"]] = r.get("close")
    for r in rows:
        r["sector"] = sec.get(r.get("symbol"))
        r["cmp"] = cmp_.get(r.get("symbol"))


def book_churn(conn, book: str, n: int = 6) -> list:
    """The last N rebalances as in/out sets — the rebalance ledger (§I.4)."""
    if not _has(conn, "auto_portfolio_holdings"):
        return []
    dates = [r["rebal_date"] for r in _rows(
        conn, "SELECT DISTINCT rebal_date FROM auto_portfolio_holdings WHERE portfolio=? "
              "ORDER BY rebal_date DESC LIMIT ?", (book, n + 1))]
    out = []
    for i in range(len(dates) - 1):
        cur = {r["symbol"] for r in _rows(conn, "SELECT symbol FROM auto_portfolio_holdings "
                                                "WHERE portfolio=? AND rebal_date=?", (book, dates[i]))}
        prv = {r["symbol"] for r in _rows(conn, "SELECT symbol FROM auto_portfolio_holdings "
                                                "WHERE portfolio=? AND rebal_date=?", (book, dates[i + 1]))}
        out.append({"date": dates[i], "in": sorted(cur - prv), "out": sorted(prv - cur)})
    return out


# ── sector rotation (the V21 book) ──────────────────────────────────────────────


def rotation_book(conn, asof: str = "") -> dict:
    """Weights + the rebalance diff + the NAV series + stats for the sector-rotation book.

    🔴 D138 SCOPE GAP: this book holds SECTOR INDICES, not individual stocks. The caller renders
    that ABOVE the headline stat — it is a recorded verdict, never a footnote. D141: the two-step
    sector→stock extension was BUILT, SIMULATED and REJECTED at realistic cost.
    """
    out = {"weights": [], "prev": [], "nav": [], "asof": None, "dates": []}
    if not _has(conn, "sector_rotation_book"):
        return out
    dates = [r["rebal_date"] for r in _rows(
        conn, "SELECT DISTINCT rebal_date FROM sector_rotation_book ORDER BY rebal_date DESC LIMIT 40")]
    out["dates"] = dates
    if not dates:
        return out
    date = asof if asof in dates else dates[0]
    out["asof"] = date
    out["weights"] = _rows(conn, "SELECT sector, weight FROM sector_rotation_book WHERE rebal_date=? "
                                 "ORDER BY weight DESC", (date,))
    i = dates.index(date)
    if i + 1 < len(dates):
        out["prev"] = _rows(conn, "SELECT sector, weight FROM sector_rotation_book WHERE rebal_date=?",
                            (dates[i + 1],))
    if _has(conn, "sector_rotation_nav"):
        out["nav"] = _rows(conn, "SELECT month_date, nav, nav_bench, invested, regime, turnover "
                                 "FROM sector_rotation_nav ORDER BY month_date")
    return out


def rotation_diff(cur: list, prev: list) -> dict:
    """Entered / exited / re-weighted — 'how this rebalance occurred'."""
    c = {r["sector"]: _f(r.get("weight"), 0.0) for r in cur}
    p = {r["sector"]: _f(r.get("weight"), 0.0) for r in prev}
    entered = sorted(k for k in c if k not in p)
    exited = sorted(k for k in p if k not in c)
    moved = sorted(((k, c[k] - p[k]) for k in c if k in p and abs(c[k] - p[k]) > 1e-9),
                   key=lambda t: -abs(t[1]))
    turnover = sum(abs(c.get(k, 0.0) - p.get(k, 0.0)) for k in set(c) | set(p)) / 2.0
    return {"entered": entered, "exited": exited, "moved": moved, "turnover": turnover}


# ── the strategy library (factor-league + classics, MERGED) ─────────────────────

# The BINDING origin taxonomy (docs/strategies/origins.md): 🧑 RAMANA · 🏠 HOUSE · 📚 CLASSIC.
ORIGINS = (("ramana", "\U0001F9D1", "Ramana"), ("house", "\U0001F3E0", "House"),
           ("classic", "\U0001F4DA", "Classic"))

# Library metadata ONLY — origin class + the canonical reference page. Deliberately carries NO
# measured numbers: every verdict figure lives in docs/strategy-ledger.md / the engine tables and is
# LINKED, never restated here (a restated number is a number that can silently go stale).
LIBRARY = (
    ("dvpt", "DVPT positioning", "ramana", "dvpt", "/dash/home/strategies/positioning",
     "Delivery value per trade vs its own power baselines."),
    ("mep", "Accumulation / distribution (MEP)", "ramana", "mep", "/dash/home/strategies/mep",
     "Signed accumulation-distribution pressure — a descriptor, never a picker."),
    ("conviction", "Conviction shortlist", "house", "", "/dash/home/strategies/conviction",
     "Cross-pillar synthesis: relative strength × positioning × quality."),
    ("cci", "Concall credibility (CCI)", "house", "cci", "/dash/home/strategies/credibility",
     "Promise-keeping record from earnings calls + a deterioration veto."),
    ("launchpad", "Launchpad", "house", "", "/dash/home/strategies/launchpad",
     "Momentum with contracting volatility — a validated screen."),
    ("cpr", "CPR structure", "classic", "cpr", "/dash/stock",
     "Pivot-range structure, multi-timeframe. Lives on the stock chart."),
    ("rs", "Relative strength suite", "classic", "relative-strength", "/dash/home/rotation",
     "RRG, RS bands, rotation and capture — measured our way."),
    ("wolfe", "Wolfe waves", "classic", "wolfe-wave", "/dash/wolfe/scan",
     "Classic wave geometry plus Ramana's strength rebalance."),
    ("harmonic", "Harmonic (XABCD)", "classic", "harmonic", "/dash/harmonic",
     "Gartley/Carney geometry with a point-in-time detector."),
    ("sector-rotation", "Sector rotation", "ramana", "sector-rotation",
     "/dash/home/strategies/sector-rotation",
     "A monthly sector-index book. Picks SECTORS, not stocks."),
    ("steady", "STEADY-25 (low-vol × momentum)", "classic", "momentum-riskadj",
     "/dash/home/strategies/books?book=STEADY-25", "The quarterly large-cap core book."),
    ("pacer", "PACER-25 (risk-adjusted momentum)", "classic", "momentum-riskadj",
     "/dash/home/strategies/books?book=PACER-25", "Volatility-adjusted momentum, monthly."),
    ("sprinter", "SPRINTER-25 (12-month momentum)", "classic", "momentum-riskadj",
     "/dash/home/strategies/books?book=SPRINTER-25", "Textbook 12-month momentum, monthly."),
    ("craftsman", "CRAFTSMAN-25 (quality × momentum)", "classic", "momentum-riskadj",
     "/dash/home/strategies/books?book=CRAFTSMAN-25", "Quality screen crossed with momentum."),
    ("reversal", "Reversal context", "ramana", "reversal-context", "/dash/screen2",
     "Band state and stretch — falsified as an entry, kept as context."),
    ("seasonal", "Seasonal tape", "house", "", "/dash/seasonal-tape",
     "Calendar seasonality against a null prior. Zero certified IS the finding."),
    ("union", "The Union (sealed)", "ramana", "union",
     "/dash/strategy-ref?p=union", "Pre-registered, sealed; forward verdict due 2026-10-03."),
    ("patearn", "patearn 14-pattern quality", "house", "patearn", "/dash/home/strategies/conviction",
     "Durability patterns used as a filter and veto, never a ranker."),
)


# The factor families whose live rosters the library can show (`factor_league.FAMILIES`).
_FAM_OF = {"pacer": "PACER", "sprinter": "SPRINTER", "craftsman": "MOM6", "steady": "LOWVOL"}


def library(conn, origin: str = "") -> list:
    """The merged Strategy library — factor families + classic screens under ONE origin-filtered
    table. Live roster counts are attached where the engine table exists."""
    counts = {}
    if _has(conn, "classic_roster"):
        for r in _rows(conn, "SELECT strategy, COUNT(*) n FROM classic_roster GROUP BY strategy"):
            counts["classic:" + str(r.get("strategy"))] = r.get("n")
    if _has(conn, "factor_league"):
        for r in _rows(conn, "SELECT family, COUNT(*) n FROM factor_league GROUP BY family"):
            counts["factor:" + str(r.get("family"))] = r.get("n")
    out = []
    for key, label, org, ref, route, blurb in LIBRARY:
        if origin and org != origin:
            continue
        fam = _FAM_OF.get(key)
        out.append({"key": key, "label": label, "origin": org, "ref": ref, "route": route,
                    "blurb": blurb,
                    "n": counts.get("classic:" + key)
                         or (counts.get("factor:" + fam) if fam else None)})
    return out


def factor_roster(conn, key: str, limit: int = 25) -> tuple:
    """(rows, family) — the live top-25 participants of one factor family, enriched with the
    identity spine. Empty when the key is not a family or the nightly table has not landed."""
    fam = _FAM_OF.get(str(key or "").lower())
    if not fam or not _has(conn, "factor_league"):
        return [], None
    rows = _rows(conn, "SELECT symbol, rank, score, as_of FROM factor_league WHERE family=? "
                       "ORDER BY rank LIMIT ?", (fam, limit))
    if rows:
        _enrich_spine(conn, rows)
    return rows, fam


def classic_screens(conn) -> list:
    """The famous public-formula screens we re-run on our own point-in-time data (📚 CLASSIC)."""
    meta = {}
    try:
        from src.automation import famous_strategies as FS
        meta = dict(getattr(FS, "STRATEGIES", {}) or {})
    except Exception:  # noqa: BLE001
        meta = {}
    counts, asof = {}, None
    if _has(conn, "classic_roster"):
        asof = _one(conn, "SELECT MAX(as_of) FROM classic_roster")
        for r in _rows(conn, "SELECT strategy, COUNT(*) n FROM classic_roster GROUP BY strategy"):
            counts[str(r.get("strategy"))] = r.get("n")
    out = []
    for key in sorted(meta) or sorted(counts):
        spec = meta.get(key) or {}
        label = spec.get("label") if isinstance(spec, dict) else None
        out.append({"key": key, "label": label or str(key).replace("_", " ").title(),
                    "n": counts.get(key), "as_of": asof})
    return out


def classic_roster(conn, key: str, limit: int = 25) -> list:
    if not _has(conn, "classic_roster"):
        return []
    rows = _rows(conn, "SELECT symbol, rank, score, as_of FROM classic_roster WHERE strategy=? "
                       "ORDER BY rank LIMIT ?", (key, limit))
    _enrich_spine(conn, rows)
    return rows


def classic_nav(conn, key: str) -> list:
    if not _has(conn, "classic_portfolio_nav"):
        return []
    return _rows(conn, "SELECT rebal_date, nav, bench_nav FROM classic_portfolio_nav "
                       "WHERE portfolio=? ORDER BY rebal_date", (key,))


# ── positioning (stocks + stealth, ONE renderer) ────────────────────────────────

_POS_COLS = ("s.symbol, s.trade_date, s.trigger_rank, s.r_score, s.p_score, "
             "s.ratio_today_vs_power_1m, s.accum_character, s.delivery_value_per_trade, s.rs_rank, "
             "s.rs_vs_broad_trend_state, s.pct_from_52w_high, s.key_price_p3m, s.gap_to_key_p3m, "
             "s.turnover_surge_1m, s.avg_deliv_pct_1m, s.primary_sector, s.is_ath_dvpt, "
             "s.trade_count_ratio_1m_6m")


def positioning(conn, stealth: bool = False, limit: int = 60) -> tuple:
    """(rows, as_of). ONE read serves both the positioning board and its Stealth toggle — the classic
    site admitted the same thing (`/dash/stealth` delegated to `view=='stealth'`), so the merge is a
    registry fact, not a judgement call. Stealth = accumulation + p≥3 + thinning trade count + ≥10%
    off the 52-week high (the classic filter, reproduced exactly)."""
    if not _has(conn, "stock_signals"):
        return [], None
    d = _latest(conn, "stock_signals", "trade_date")
    if not d:
        return [], None
    where = "s.trade_date=?"
    order = "s.is_ath_dvpt DESC, s.p_score DESC, s.r_score DESC, s.trigger_rank"
    if stealth:
        where += (" AND s.accum_character='ACCUMULATION' AND COALESCE(s.p_score,0)>=3 "
                  "AND COALESCE(s.trade_count_ratio_1m_6m,99)<=1.1 AND s.pct_from_52w_high<=-10")
        order = "s.p_score DESC, s.pct_from_52w_high ASC"
    else:
        where += " AND s.delivery_value_per_trade IS NOT NULL"
    sql = ("SELECT " + _POS_COLS + ", b.close AS cmp FROM stock_signals s "
           "LEFT JOIN bhavcopy_rows b ON b.symbol=s.symbol AND b.trade_date=s.trade_date "
           "AND b.series IN ('EQ','BE') WHERE " + where + " ORDER BY " + order + " LIMIT ?")
    return _rows(conn, sql, (d, limit)), d


# ── conviction ──────────────────────────────────────────────────────────────────


def conviction(limit: int = 60) -> list:
    """The cross-pillar shortlist, from the canonical engine (`stock_rs.conviction_shortlist`).

    ⚠ The Quality pillar (pt14 tier) is scored from the historical fundamentals ARCHIVE, which was
    collected from Screener.in — the ONE known primary-source exception, under remediation to
    BSE/NSE XBRL (CLAUDE.md guardrail #8). The caller must DISCLOSE that where the column shows.
    Not extended here: this reads the stored tier, nothing new is fetched.
    """
    try:
        from src.automation.stock_rs import conviction_shortlist
        return list(conviction_shortlist(limit=limit) or [])
    except Exception:  # noqa: BLE001
        return []


# ── MEP (accumulation / distribution) ───────────────────────────────────────────

MEP_STATES = (("STRONG_ACCUM", "Strong accumulation"), ("ACCUM", "Accumulating"),
              ("NEUTRAL", "Consolidating"), ("DISTRIB", "Distributing"),
              ("STRONG_DISTRIB", "Strong distribution"))


def mep_board(conn, limit: int = 80) -> tuple:
    """(rows, counts, as_of) — the top accumulation and distribution ends of the same tape."""
    if not _has(conn, "mep_signals"):
        return [], {}, None
    d = _latest(conn, "mep_signals", "trade_date")
    if not d:
        return [], {}, None
    counts = {r["mep_state_smooth"]: r["n"] for r in _rows(
        conn, "SELECT mep_state_smooth, COUNT(*) n FROM mep_signals WHERE trade_date=? "
              "GROUP BY mep_state_smooth", (d,)) if r.get("mep_state_smooth")}
    cols = ("m.symbol, m.mep_score_smooth, m.mep_state_smooth, m.mep_score, m.pressure, m.clv, "
            "m.drift_22d, m.updown_vol_22d, m.compression, b.close AS cmp")
    base = ("SELECT " + cols + " FROM mep_signals m LEFT JOIN bhavcopy_rows b ON b.symbol=m.symbol "
            "AND b.trade_date=m.trade_date AND b.series IN ('EQ','BE') WHERE m.trade_date=? "
            "AND m.mep_score_smooth IS NOT NULL ORDER BY m.mep_score_smooth ")
    half = max(10, limit // 2)
    rows = _rows(conn, base + "DESC LIMIT ?", (d, half))
    rows += _rows(conn, base + "ASC LIMIT ?", (d, half))
    seen, uniq = set(), []
    for r in rows:
        if r["symbol"] in seen:
            continue
        seen.add(r["symbol"])
        uniq.append(r)
    return uniq, counts, d


# ── credibility (CCI) — absorbs the per-symbol fingerprint ──────────────────────


def cci_board(conn, limit: int = 120) -> tuple:
    """(rows, counts, as_of). Ordering is COVERAGE-FIRST (#settled desc) — deliberately NOT a
    credibility ranking, because CCI's Gate B failed leak-free: descriptive only, never ranked."""
    if not _has(conn, "concall_scores"):
        return [], {}, None
    rows = _rows(conn, "SELECT s.symbol, s.tier, s.composite_score, s.forward_direction, "
                       "s.veto_active, s.veto_reason, s.guidance_accuracy_score, "
                       "s.n_promises_resolved, s.quantification_rate, s.deterioration_score, "
                       "s.as_of_period, s.n_concalls, s.credibility_trend "
                       "FROM concall_scores s JOIN (SELECT symbol, MAX(last_updated) lu "
                       "FROM concall_scores GROUP BY symbol) x ON x.symbol=s.symbol "
                       "AND x.lu=s.last_updated ORDER BY s.n_promises_resolved DESC, "
                       "s.symbol LIMIT ?", (limit,))
    counts = {
        "proven": sum(1 for r in rows if (r.get("n_promises_resolved") or 0) >= 1),
        "vetoed": sum(1 for r in rows if r.get("veto_active")),
        "unproven": sum(1 for r in rows if not (r.get("n_promises_resolved") or 0)),
        "scored": len(rows),
    }
    return rows, counts, _latest(conn, "concall_scores", "as_of_date")


def cci_fingerprint(conn, sym: str) -> list:
    """Promise vs delivery for ONE name — the absorbed `/dash/credibility` fingerprint."""
    if not sym or not _has(conn, "concall_guidance"):
        return []
    return _rows(conn, "SELECT source_period, resolved_period, statement_type, status, "
                       "variance_pct, claim_text FROM concall_guidance WHERE symbol=? "
                       "AND status IS NOT NULL ORDER BY resolved_period, source_period LIMIT 80",
                 (str(sym).upper()[:24],))


# ── growth-intent (management's forward proposals) ──────────────────────────────

GROWTH_TABS = (("", "All growth"), ("debt_reduction", "Debt ↓"), ("volume", "Volume"),
               ("new_product", "New product"), ("capex", "Capex"), ("expansion", "Expansion"))


def growth(conn, stype: str = "", min_cr: float = 0.0, since: int = 0, limit: int = 300) -> list:
    """Forward-looking statements from earnings calls, largest commitment first.

    ⚠ PROVENANCE (guardrail #8 disclosure the caller must render): the concall corpus was ~98.6%
    DISCOVERED via Screener.in links — the frozen legacy path, with a BSE-primary migration in
    progress. Nothing here is extended; this is a read of the stored `concall_signals`.
    """
    if not _has(conn, "concall_signals"):
        return []
    where, p = ["1=1"], []
    if stype:
        where.append("statement_type=?")
        p.append(stype)
    if min_cr:
        where.append("COALESCE(amount_cr,0) >= ?")
        p.append(float(min_cr))
    if since:
        where.append("COALESCE(year,0) >= ?")
        p.append(int(since))
    p.append(int(limit))
    return _rows(conn, "SELECT symbol, period_label, year, statement_type, amount_cr, polarity, "
                       "claim_text FROM concall_signals WHERE " + " AND ".join(where) +
                       " ORDER BY COALESCE(amount_cr,0) DESC, year DESC LIMIT ?", p)


# ── ownership & filings (insider · ratings · SAST · shareholding) ───────────────

OWN_LENSES = (("insider", "Insider dealing"), ("ratings", "Credit ratings"),
              ("sast", "Stake & pledge"), ("shp", "Shareholding"))


def own_insider(conn, days: int = 90, limit: int = 120) -> tuple:
    """(board, tape, as_of). Classification is single-sourced in `insider_events` — never re-derived
    here, so the hub can never disagree with the classic lens about what a 'conviction' buy is."""
    if not _has(conn, "insider_events"):
        return [], [], None
    asof = _latest(conn, "insider_events", "disclosure_dt")
    board = []
    try:
        from src.automation import insider_events as IE
        board = list(IE.universe_aggregate(conn, window_days=days) or [])[:limit]
    except Exception:  # noqa: BLE001
        board = []
    tape = _rows(conn, "SELECT symbol, disclosure_dt, category, txn_class, signal_class, shares, "
                       "value_rs, mode, promoter_group_flag, source_url FROM insider_events "
                       "WHERE disclosure_dt >= date(?, ?) AND COALESCE(signal_class,'') "
                       "NOT IN ('ignore','plumbing') ORDER BY disclosure_dt DESC LIMIT ?",
                 (asof or "now", "-" + str(int(days)) + " days", limit))
    return board, tape, asof


def own_ratings(conn, days: int = 180, limit: int = 120) -> tuple:
    """(transitions, tape, as_of). Company-level dedup lives in `credit_ratings.transitions`."""
    if not _has(conn, "credit_rating_events"):
        return [], [], None
    asof = _latest(conn, "credit_rating_events", "broadcast_dt")
    tr = []
    try:
        from src.automation import credit_ratings as CR
        tr = list(CR.transitions(conn, window_days=days) or [])[:limit]
    except Exception:  # noqa: BLE001
        tr = []
    tape = _rows(conn, "SELECT symbol, issuer_name, agency, action_class, rating_raw, outlook, "
                       "notch_delta, below_investment_grade, broadcast_dt, attachment_url "
                       "FROM credit_rating_events WHERE broadcast_dt >= date(?, ?) "
                       "ORDER BY broadcast_dt DESC LIMIT ?",
                 (asof or "now", "-" + str(int(days)) + " days", limit))
    return tr, tape, asof


def own_sast(conn, days: int = 90, limit: int = 120) -> tuple:
    """(confluence, tape, as_of). Shape rules (constructive / distress / mixed) come from
    `sast_events` so the ≥25% control exclusion and the Reg29(1) level-vs-flow split hold."""
    if not (_has(conn, "sast_reg29_events") or _has(conn, "sast_pledge_events")):
        return [], [], None
    a1 = _latest(conn, "sast_reg29_events", "broadcast_dt")
    a2 = _latest(conn, "sast_pledge_events", "broadcast_dt")
    asof = max([x for x in (a1, a2) if x] or [None]) if (a1 or a2) else None
    conf = []
    try:
        from src.automation import sast_events as SE
        conf = list(SE.universe_confluence(conn, window_days=days) or [])[:limit]
    except Exception:  # noqa: BLE001
        conf = []
    tape = []
    if _has(conn, "sast_reg29_events"):
        tape += [dict(r, feed="stake") for r in _rows(
            conn, "SELECT symbol, broadcast_dt, acq_sale, promoter_flag, mode, reg_type, pct_acq, "
                  "pct_sale, pct_after, attachment FROM sast_reg29_events WHERE broadcast_dt >= "
                  "date(?, ?) ORDER BY broadcast_dt DESC LIMIT ?",
            (asof or "now", "-" + str(int(days)) + " days", limit // 2 or 1))]
    if _has(conn, "sast_pledge_events"):
        tape += [dict(r, feed="pledge") for r in _rows(
            conn, "SELECT symbol, broadcast_dt, event_type, event_pct, pre_pct, post_pct, "
                  "encumb_pct, counterparty, attachment FROM sast_pledge_events WHERE broadcast_dt "
                  ">= date(?, ?) ORDER BY broadcast_dt DESC LIMIT ?",
            (asof or "now", "-" + str(int(days)) + " days", limit // 2 or 1))]
    tape.sort(key=lambda r: str(r.get("broadcast_dt") or ""), reverse=True)
    return conf, tape[:limit], asof


_SHP_METRICS = ("Promoters", "FIIs", "DIIs", "Public", "Promoter Pledge")


def own_shp(symbols: int = 40, quarters: int = 8) -> dict:
    """The quarter matrix: symbol × quarter × holder class (Part III §I.5).

    Lives in research.db (a SEPARATE store), reached through the engine's own path constant — so
    this never assumes a file location. Returns {'quarters': [...], 'rows': [...], 'source': str}.
    Degrades to an empty matrix when research.db is absent (it is, on a laptop fixture).
    """
    out = {"quarters": [], "rows": [], "source": ""}
    path = None
    try:
        from src.automation import shareholding_xbrl as SX
        path = str(getattr(SX, "RESEARCH_DB", "") or "")
    except Exception:  # noqa: BLE001
        return out
    if not path:
        return out
    out["source"] = path
    try:
        rc = sqlite3.connect("file:" + path + "?mode=ro", uri=True, timeout=3)
        rc.row_factory = sqlite3.Row
    except Exception:  # noqa: BLE001
        return out
    try:
        if not _has(rc, "shareholding_history"):
            return out
        qs = [r["q"] for r in _rows(rc, "SELECT DISTINCT substr(period_end,1,7) q FROM "
                                        "shareholding_history ORDER BY q DESC LIMIT ?", (quarters,))]
        qs = list(reversed(qs))
        if not qs:
            return out
        syms = [r["symbol"] for r in _rows(
            rc, "SELECT symbol, COUNT(*) n FROM shareholding_history WHERE metric='Promoters' "
                "GROUP BY symbol ORDER BY n DESC, symbol LIMIT ?", (symbols,))]
        if not syms:
            return out
        ph = ",".join("?" * len(syms))
        qh = ",".join("?" * len(qs))
        raw = _rows(rc, "SELECT symbol, substr(period_end,1,7) q, metric, value, source, period_end "
                        "FROM shareholding_history WHERE symbol IN (" + ph + ") AND metric IN "
                        "('Promoters','FIIs','DIIs') AND substr(period_end,1,7) IN (" + qh + ") "
                        "ORDER BY period_end", syms + qs)
        cell = {}
        for r in raw:
            cell[(r["symbol"], r["q"], r["metric"])] = r  # later period_end wins within a quarter
        out["quarters"] = qs
        out["rows"] = [{"symbol": s,
                        "cells": [{"q": q, **{m: (cell.get((s, q, m)) or {}).get("value")
                                              for m in ("Promoters", "FIIs", "DIIs")},
                                   "mixed": len({(cell.get((s, q, m)) or {}).get("source")
                                                 for m in ("Promoters", "FIIs", "DIIs")
                                                 if (s, q, m) in cell}) > 1}
                                  for q in qs]} for s in syms]
        return out
    finally:
        try:
            rc.close()
        except Exception:  # noqa: BLE001
            pass


# ── launchpad (screen + its evidence) ───────────────────────────────────────────


def launchpad_screen(conn, limit: int = 60) -> tuple:
    """(rows, scan_date) — today's setups from the nightly snapshot, freshest first.

    Reads the persisted `launchpad_signals` table anchored by `launchpad_scan_meta.scan_date` (the
    engine's own anchor). It deliberately does NOT fall back to the live scan the classic page runs:
    a page render must never become a heavy market-wide compute.
    """
    if not _has(conn, "launchpad_signals"):
        return [], None
    d = None
    if _has(conn, "launchpad_scan_meta"):
        d = _one(conn, "SELECT v FROM launchpad_scan_meta WHERE k='scan_date'")
    d = d or _latest(conn, "launchpad_signals", "scan_date")
    if not d:
        return [], None
    rows = _rows(conn, "SELECT symbol, flags, age, ret22, ret1, vratio, rng, vol66, med_turn, buyer "
                       "FROM launchpad_signals WHERE scan_date=? "
                       "ORDER BY age ASC, med_turn DESC LIMIT ?", (d, limit))
    return rows, d


def launchpad_evidence(conn) -> dict:
    """The `ignition_outcomes` study — the screen's OWN published track record (50k signals).

    Read it as a DISTRIBUTION, not a promise: point-in-time, GROSS of costs, and survivorship-exposed
    (delisted losers are absent, so returns are biased up). The ledger verdict on the tradeable
    wrapper is unchanged — a validated screen with NO fundable edge net of cost.
    """
    out = {"n": 0, "hit25": None, "med12": None, "med_mae": None, "med_mfe": None,
           "cohorts": [], "hist": [], "ladder": [], "as_of": None}
    if not _has(conn, "ignition_outcomes"):
        return out
    out["as_of"] = _one(conn, "SELECT MAX(computed_at) FROM ignition_outcomes")
    base = "FROM ignition_outcomes WHERE ret_12m IS NOT NULL"
    out["n"] = _one(conn, "SELECT COUNT(*) " + base) or 0
    if not out["n"]:
        return out
    out["hit25"] = _one(conn, "SELECT 100.0*SUM(CASE WHEN ret_12m>=25 THEN 1 ELSE 0 END)/COUNT(*) " + base)
    out["med12"] = _median(conn, "ret_12m")
    out["med_mae"] = _median(conn, "mae_from_entry_pct")
    out["med_mfe"] = _median(conn, "mfe_pct")
    out["cohorts"] = _rows(conn, "SELECT character, COUNT(*) n, "
                                 "100.0*SUM(CASE WHEN ret_12m>=25 THEN 1 ELSE 0 END)/COUNT(*) hit, "
                                 "AVG(ret_12m) avg12, AVG(mae_from_entry_pct) avg_mae, "
                                 "AVG(mfe_pct) avg_mfe " + base + " AND character IS NOT NULL "
                                 "GROUP BY character ORDER BY n DESC LIMIT 12")
    out["hist"] = _rows(conn, "SELECT CASE WHEN ret_12m < -25 THEN '≤ −25%' "
                              "WHEN ret_12m < 0 THEN '−25–0%' WHEN ret_12m < 25 THEN '0–25%' "
                              "WHEN ret_12m < 50 THEN '25–50%' WHEN ret_12m < 100 THEN '50–100%' "
                              "WHEN ret_12m < 200 THEN '100–200%' ELSE '200%+' END bin, COUNT(*) n "
                              + base + " GROUP BY bin")
    if _has(conn, "averaging_zones"):
        out["ladder"] = _rows(conn, "SELECT x, label, n_touched, recover_rate, base_rate "
                                    "FROM averaging_zones ORDER BY x")
    return out


def _median(conn, col: str):
    n = _one(conn, "SELECT COUNT(*) FROM ignition_outcomes WHERE " + col + " IS NOT NULL") or 0
    if not n:
        return None
    return _one(conn, "SELECT " + col + " FROM ignition_outcomes WHERE " + col + " IS NOT NULL "
                      "ORDER BY " + col + " LIMIT 1 OFFSET ?", (n // 2,))


# ── demo constants (handed out ONLY through pick(), which flags `sample`) ───────

DEMO_BOOK_NAV = [{"rebal_date": "2022-03-31", "nav": 100.0, "bench_nav": 100.0, "n_churned": 0},
                 {"rebal_date": "2022-09-30", "nav": 108.4, "bench_nav": 104.1, "n_churned": 6},
                 {"rebal_date": "2023-03-31", "nav": 112.9, "bench_nav": 105.8, "n_churned": 5},
                 {"rebal_date": "2023-09-29", "nav": 129.6, "bench_nav": 119.2, "n_churned": 7},
                 {"rebal_date": "2024-03-28", "nav": 141.2, "bench_nav": 133.4, "n_churned": 4},
                 {"rebal_date": "2024-09-30", "nav": 155.8, "bench_nav": 143.0, "n_churned": 6},
                 {"rebal_date": "2025-03-31", "nav": 149.3, "bench_nav": 138.7, "n_churned": 8},
                 {"rebal_date": "2025-09-30", "nav": 168.5, "bench_nav": 151.2, "n_churned": 5}]

DEMO_HOLDINGS = [{"symbol": "SAMPLEA", "rank": 1, "score": 0.91, "sector": "IT", "cmp": 1420.0,
                  "w_target": 6.0, "w_now": 6.4, "since": 7.1},
                 {"symbol": "SAMPLEB", "rank": 2, "score": 0.88, "sector": "Pharma", "cmp": 880.5,
                  "w_target": 6.0, "w_now": 5.8, "since": -2.4},
                 {"symbol": "SAMPLEC", "rank": 3, "score": 0.84, "sector": "Auto", "cmp": 2310.0,
                  "w_target": 6.0, "w_now": 6.1, "since": 1.9}]

DEMO_ROTATION = {"asof": "2025-09-30", "dates": ["2025-09-30", "2025-08-29"],
                 "weights": [{"sector": "Nifty IT", "weight": 0.28},
                             {"sector": "Nifty Pharma", "weight": 0.22},
                             {"sector": "Nifty Auto", "weight": 0.18},
                             {"sector": "Nifty FMCG", "weight": 0.12},
                             {"sector": "Residual sleeve", "weight": 0.20}],
                 "prev": [{"sector": "Nifty IT", "weight": 0.20},
                          {"sector": "Nifty Pharma", "weight": 0.22},
                          {"sector": "Nifty Metal", "weight": 0.18},
                          {"sector": "Residual sleeve", "weight": 0.40}],
                 "nav": [{"month_date": "2024-10-31", "nav": 100.0, "nav_bench": 100.0, "regime": "ON"},
                         {"month_date": "2025-01-31", "nav": 104.8, "nav_bench": 101.9, "regime": "ON"},
                         {"month_date": "2025-04-30", "nav": 99.1, "nav_bench": 97.6, "regime": "OFF"},
                         {"month_date": "2025-07-31", "nav": 110.2, "nav_bench": 104.4, "regime": "ON"},
                         {"month_date": "2025-09-30", "nav": 115.6, "nav_bench": 107.1, "regime": "ON"}]}

DEMO_POSITIONING = [{"symbol": "SAMPLEA", "trigger_rank": 1, "r_score": 4, "p_score": 4,
                     "ratio_today_vs_power_1m": 1.82, "accum_character": "ACCUMULATION",
                     "delivery_value_per_trade": 48200.0, "rs_rank": 23, "primary_sector": "IT",
                     "pct_from_52w_high": -6.4, "gap_to_key_p3m": -2.1, "cmp": 1420.0},
                    {"symbol": "SAMPLEB", "trigger_rank": 2, "r_score": 3, "p_score": 4,
                     "ratio_today_vs_power_1m": 1.44, "accum_character": "DISTRIBUTION",
                     "delivery_value_per_trade": 31900.0, "rs_rank": 88, "primary_sector": "Pharma",
                     "pct_from_52w_high": -14.2, "gap_to_key_p3m": 5.8, "cmp": 880.5}]

DEMO_MEP = [{"symbol": "SAMPLEA", "mep_score_smooth": 0.74, "mep_state_smooth": "STRONG_ACCUM",
             "pressure": 0.61, "clv": 0.44, "drift_22d": 0.08, "updown_vol_22d": 1.32,
             "compression": 0.41, "cmp": 1420.0},
            {"symbol": "SAMPLEB", "mep_score_smooth": -0.68, "mep_state_smooth": "STRONG_DISTRIB",
             "pressure": -0.55, "clv": -0.39, "drift_22d": -0.06, "updown_vol_22d": 0.71,
             "compression": 0.29, "cmp": 880.5}]

DEMO_CCI = [{"symbol": "SAMPLEA", "tier": "A", "composite_score": 72.4, "forward_direction": "UP",
             "veto_active": 0, "guidance_accuracy_score": 78.0, "n_promises_resolved": 9,
             "quantification_rate": 0.62, "deterioration_score": 0.1, "as_of_period": "Q1 FY26",
             "n_concalls": 12, "credibility_trend": "IMPROVING"},
            {"symbol": "SAMPLEB", "tier": "D", "composite_score": 31.0, "forward_direction": "FLAT",
             "veto_active": 1, "veto_reason": "guidance deterioration", "guidance_accuracy_score": 34.0,
             "n_promises_resolved": 6, "quantification_rate": 0.21, "deterioration_score": 0.8,
             "as_of_period": "Q1 FY26", "n_concalls": 8, "credibility_trend": "DETERIORATING"}]

DEMO_GROWTH = [{"symbol": "SAMPLEA", "period_label": "Q1 FY26", "year": 2026, "amount_cr": 1250.0,
                "statement_type": "capex", "polarity": 1,
                "claim_text": "We plan to commission the new line with a capex of about Rs 1,250 crore."},
               {"symbol": "SAMPLEB", "period_label": "Q4 FY25", "year": 2025, "amount_cr": 400.0,
                "statement_type": "debt_reduction", "polarity": 1,
                "claim_text": "We intend to bring gross debt down by roughly Rs 400 crore this year."}]

DEMO_INSIDER = [{"symbol": "SAMPLEA", "verdict": "conviction", "open_market_buy_value_30d": 82000000,
                 "open_market_buy_value_90d": 140000000, "open_market_sell_value_90d": 0,
                 "net_90": 140000000, "promoter_cluster_buy_30d": 2, "pledge_adverse_ct_90": 0,
                 "n_filings_90": 6}]

DEMO_RATINGS = [{"symbol": "SAMPLEA", "agency": "Sample Ratings", "action_class": "UPGRADE",
                 "rating_raw": "AA-", "notch": 1, "outlook": "Stable", "broadcast_dt": "2026-07-20",
                 "below_investment_grade": 0}]

DEMO_SAST = [{"symbol": "SAMPLEA", "shape": "constructive", "stake_net": 1.8, "pledge_net": -0.9,
              "invocations": 0, "encumb_now": 4.2, "n_filings": 5}]
