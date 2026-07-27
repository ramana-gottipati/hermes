"""src/web/home/markets_reads.py — the W2-B (Markets · relative strength / rotation / sectors)
read layer for the Graphite experience.

Lane-owned sibling of `reads.py`, added by the Graphite cutover wave W2-B so the eleven classic
Markets surfaces (rs-hub · leaders · momentum-scan · capture-map · rrg · rotation · rsband ·
cycle-clock · sectors · sector-economics · sector-momentum) can be served from THREE consolidated
Graphite pages without importing a single classic render module.

ISOLATION CONTRACT (tests/test_home_isolation.py). Like `reads.py`, this module imports only
`src.core.db` and genuinely-shared, render-free ENGINE modules under `src/automation/` — the
`rrg._rs_ratio_momentum` reuse precedent already blessed in `reads.rrg_sectors`. It NEVER imports a
classic web VIEW (`rrg_view`, `rsband_view`, `cycle_clock`, `dashboard`, `momentum_view`, …); those
return classic HTML, and importing one would couple Graphite to the frozen classic chrome. Where a
classic view held the only copy of a computation, the computation is re-derived here from the SAME
canonical engine or the SAME stored columns — never by copying a renderer.

Every read is bounded + defensive: a missing table / absent nightly job returns an empty result,
never an exception (a heavy or edge DB must never 500 a page). Callers pair each read with the
`DEMO_*` fallback below and mark the zone `sample=True` — the real-vs-demo honesty line.

Returns plain rows/dicts ONLY, never HTML (the reads/components split).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

# The curated ECONOMIC sector universe for every Markets page in this lane — the same list the
# Today deck already uses (reads._RRG_SECTORS), so a sector never appears on one Graphite page and
# vanishes from the next. `rs_extras` / `ratio_rows` also carry factor, bond and ESG indices; those
# are deliberately excluded (they are not sectors, and mixing them makes the rotation map unreadable).
SECTORS = (
    "Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty FMCG", "Nifty Metal",
    "Nifty Energy", "Nifty Realty", "Nifty Financial Services", "Nifty Media", "Nifty PSU Bank",
    "Nifty Private Bank", "Nifty Healthcare Index", "Nifty Oil & Gas", "Nifty Consumer Durables",
    "Nifty Infrastructure", "Nifty India Defence", "Nifty Chemicals",
)

BENCHMARK = "Nifty 500"          # the broad benchmark every RS read on this lane is measured against

# The five RS weather phases, in lifecycle order (Recovery → Tailwind → Rolling-over → Headwind).
# Labels come from the canonical engine so a phase can never be worded two ways on two pages.
PHASES = ("RECOVERY", "TAILWIND", "ROLLING-OVER", "HEADWIND")


def _has(conn, table: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def _rows(conn, sql: str, params=()) -> list:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error:
        return []


def _latest_date(conn, table: str, col: str) -> Optional[str]:
    try:
        r = conn.execute(f"SELECT MAX({col}) AS d FROM {table}").fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None


def _short(name) -> str:
    """'Nifty Healthcare Index' -> 'Healthcare' — the label every page shows."""
    s = str(name or "").replace("Nifty ", "").replace(" Index", "").strip()
    return s or "—"


def phase_label(key) -> str:
    """The canonical display word for an rs_phase key (from the engine, never re-worded here)."""
    try:
        from src.automation.rs_phase import WEATHER_LABEL
        return WEATHER_LABEL.get(str(key or "").upper(), "☁ Neutral")
    except Exception:  # noqa: BLE001
        return "☁ Neutral"


# ══ ROTATION · Weather (ports /dash/rotation) ═════════════════════════════════════════
def sector_weather(conn, benchmark: str = BENCHMARK) -> list:
    """Each sector's CURRENT RS weather vs the broad market, from the nightly `index_signals` row:
    the 1/3/6/12-month RS slopes, the trend state, the 1m/3m absolute returns — and the PHASE, which
    is classified here by the canonical engine `rs_phase.rs_weather` rather than read from the
    additive `index_signals.rs_phase` column, so the page works on a box where that migration column
    has not been added yet AND can never word a phase differently from the engine that defines it.

    RS doctrine: relative strength is "did it beat the broad index over this horizon"; the PHASE is
    the SHAPE of the sweep across 1m/3m/6m/12m, not any single horizon. Sorted lifecycle-first
    (Tailwind → Recovery → Rolling-over → Headwind → Neutral), then by 3-month slope. [] when the
    nightly index-RS pass hasn't run."""
    if not _has(conn, "index_signals"):
        return []
    d = _latest_date(conn, "index_signals", "trade_date")
    if not d:
        return []
    rows = _rows(conn,
                 "SELECT index_name, rs_vs_broad_today AS rs_today, "
                 "rs_vs_broad_slope_1m AS s1, rs_vs_broad_slope_3m AS s3, "
                 "rs_vs_broad_slope_6m AS s6, rs_vs_broad_slope_12m AS s12, "
                 "rs_vs_broad_trend_state AS state, ret_1m_pct AS r1, ret_3m_pct AS r3 "
                 "FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL "
                 "AND index_name IN (%s)"
                 % ",".join("?" * len(SECTORS)), (d, *SECTORS))
    try:
        from src.automation.rs_phase import phase_key
    except Exception:  # noqa: BLE001
        phase_key = None
    order = {"TAILWIND": 0, "RECOVERY": 1, "ROLLING-OVER": 2, "HEADWIND": 3}
    out = []
    for r in rows:
        r["label"] = _short(r.get("index_name"))
        r["as_of"] = d
        p = "NEUTRAL"
        if phase_key is not None:
            try:
                p = phase_key(r.get("s1"), r.get("s3"), r.get("s6"), r.get("s12"), r.get("state"))
            except Exception:  # noqa: BLE001
                p = "NEUTRAL"
        r["phase"] = p
        r["phase_label"] = phase_label(p)
        out.append(r)
    out.sort(key=lambda r: (order.get(r["phase"], 4),
                            -(r.get("s3") if r.get("s3") is not None else -1e9)))
    return out


def phase_cells(limit: int = 6) -> dict:
    """The 2×2 weather grid: for each phase, how many liquid names sit in it and the STRICT-diagonal
    shortlist (the stock AND its own sector share the phase, plus the per-phase moving-average
    confirm gate). Straight from the canonical engine `stock_rs` — the same rows the classic
    /dash/rotation grid shows, no re-implementation. {} when the nightly RS pass hasn't run."""
    try:
        from src.automation import stock_rs
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for p in PHASES:
        try:
            members = stock_rs.phase_members(p, limit=300) or []
            short = stock_rs.phase_shortlist(p, limit=int(limit)) or []
        except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 a page
            members, short = [], []
        out[p] = {"n": len(members), "rows": short[:int(limit)], "label": phase_label(p)}
    return out


def phase_turns(limit: int = 18) -> list:
    """Names whose RS phase CHANGED on the latest session vs the prior one — the '✨ just turned'
    strip. Base-turns (Headwind → Recovery) and cracks (Tailwind → Rolling-over) lead. [] until at
    least two days of rotation history exist."""
    try:
        from src.automation import stock_rs
        rows = stock_rs.phase_movers(limit=int(limit) * 3) or []
    except Exception:  # noqa: BLE001
        return []
    lead = {("HEADWIND", "RECOVERY"): 0, ("TAILWIND", "ROLLING-OVER"): 1}
    rows.sort(key=lambda r: lead.get(((r.get("prev_phase") or "").upper(),
                                      (r.get("rs_phase") or "").upper()), 2))
    for r in rows:
        r["from_label"] = phase_label(r.get("prev_phase"))
        r["to_label"] = phase_label(r.get("rs_phase"))
    return rows[:int(limit)]


# ══ ROTATION · Band (ports /dash/rsband) ══════════════════════════════════════════════
def band_lanes(conn, benchmark: str = BENCHMARK, limit: int = 18) -> list:
    """Each sector's RS-band position 0–100 vs the broad market: where today's relative strength sits
    inside its OWN recency-weighted 3-year RS range (0 = at its RS support, 100 = at its RS
    resistance), plus the regime that says whether that read is even valid.

    Reuses the CANONICAL band engine `src.automation.rsband` — the stored nightly row first
    (`latest_all`), falling back to the engine's own on-read recompute (`current_all`) curated to the
    economic sectors so the page stays bounded. Cheapest-first.

    🔴 `rsband.band_verdict` returns a machine key (Ride/Fade/Trim/…) that this product NEVER
    renders — only the descriptive `state_label` third element travels to the page (the engine's own
    Codex D2-F4 rule: RS-band is a descriptive relative-level lens, not an instruction)."""
    try:
        from src.automation import rsband
    except Exception:  # noqa: BLE001
        return []
    rows = []
    try:
        rows = rsband.latest_all(benchmark, conn=conn) or []
        rows = [r for r in rows if r.get("numerator") in SECTORS]
        if not rows:
            rows = rsband.current_all(benchmark, conn=conn, only=SECTORS) or []
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in rows[:int(limit)]:
        band = r.get("rs_band_pct")
        try:
            _key, why, state_label = rsband.band_verdict(
                band, r.get("rs_regime") or "", r.get("slope_3m_pct"),
                band_state=r.get("rs_band_state"), trend_drift=r.get("trend_drift"))
        except Exception:  # noqa: BLE001
            why, state_label = "", ""
        out.append({
            "label": _short(r.get("numerator")), "index_name": r.get("numerator"),
            "band": band, "band_label": r.get("rs_band_label"),
            "regime": r.get("rs_regime"), "state": r.get("rs_band_state"),
            "detr": r.get("rs_band_pct_detr"), "long": r.get("rs_band_pct_long"),
            "width": r.get("rs_band_width_pct"), "maturity": r.get("band_maturity"),
            "read": state_label, "why": why, "trade_date": r.get("trade_date"),
        })
    return out


# ══ ROTATION · Clock (ports /dash/cycle-clock) ════════════════════════════════════════
def clock_dots(conn, benchmark: str = BENCHMARK) -> list:
    """The lifecycle-clock dots: each sector's (RS-Ratio, RS-Momentum) offset from the 100/100 centre
    plus its RSI-of-RS, from the nightly `rs_extras` snapshot. The clock is the SAME two numbers as
    the RRG map drawn radially — one dataset, two readings. Falls back to the engine's on-read
    recompute when the nightly snapshot is absent. [] if neither is available."""
    try:
        from src.automation import rrg
    except Exception:  # noqa: BLE001
        return []
    rows = []
    try:
        rows = [r for r in (rrg.latest_all(benchmark, conn=conn) or [])
                if r.get("numerator") in SECTORS]
        if not rows:
            rows = rrg.current_all(benchmark, conn=conn, only=SECTORS) or []
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in rows:
        rr, mm = r.get("rs_ratio"), r.get("rs_momentum")
        if rr is None or mm is None:
            continue
        try:
            q = rrg.quadrant(rr, mm)
        except Exception:  # noqa: BLE001
            q = None
        out.append({"label": _short(r.get("numerator")), "index_name": r.get("numerator"),
                    "rr": rr, "mm": mm, "rsi": r.get("rsi_of_rs"),
                    "mansfield": r.get("mansfield"), "quadrant": q})
    return out


# ══ STRENGTH · Leaders & laggards (ports /dash/leaders) ═══════════════════════════════
def leaders(kind: str = "leaders", limit: int = 20) -> list:
    """The 'strong-in-strong' composite: a LEADER is in an RS uptrend vs its sector AND vs the broad
    market AND its sector is itself in an RS uptrend vs the market — all three at once. A LAGGARD is
    the mirror. Straight from the canonical engine `stock_rs.leaders_laggards` (the same rows the
    classic board and the Telegram command show). [] when the nightly RS pass hasn't run."""
    try:
        from src.automation import stock_rs
        return stock_rs.leaders_laggards("leaders" if kind == "leaders" else "laggards",
                                         int(limit)) or []
    except Exception:  # noqa: BLE001
        return []


# ══ STRENGTH · RS standing (ports /dash/rs-hub) ═══════════════════════════════════════
def rs_standing(conn, limit: int = 20) -> list:
    """Today's strongest names by RS rank (1–99 percentile vs the broad universe), with the stored
    context that explains the rank: RS vs broad and vs its own sector, the trend state, the RS phase
    and RSI-of-RS. All STORED columns on `stock_signals` — no recompute, no view import."""
    if not _has(conn, "stock_signals"):
        return []
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return []
    return _rows(conn,
                 "SELECT symbol, rs_rank, primary_sector, rs_phase, rsi_of_rs AS rsi, "
                 "rs_vs_broad_today AS rs_broad, rs_vs_sector_today AS rs_sector, "
                 "rs_vs_broad_trend_state AS state, rs_vs_broad_slope_1m AS s1, "
                 "rs_vs_broad_slope_3m AS s3, rs_vs_broad_slope_6m AS s6, "
                 "rs_vs_broad_slope_12m AS s12, rs_vs_broad_new_52w_high AS rs_nh, "
                 "pct_from_52w_high AS pfh "
                 "FROM stock_signals WHERE trade_date=? AND rs_rank IS NOT NULL "
                 "ORDER BY rs_rank DESC LIMIT ?", (d, int(limit)))


def rs_counts(conn) -> dict:
    """The one-glance RS standing of the whole universe today: how many names are in each RS
    trend state, and how many sit in the top / bottom RS-rank deciles. {} if absent."""
    if not _has(conn, "stock_signals"):
        return {}
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return {}
    out = {"as_of": d, "states": {}, "top": 0, "bottom": 0, "total": 0}
    for r in _rows(conn, "SELECT rs_vs_broad_trend_state AS st, COUNT(*) AS n FROM stock_signals "
                         "WHERE trade_date=? AND rs_vs_broad_trend_state IS NOT NULL "
                         "GROUP BY rs_vs_broad_trend_state", (d,)):
        out["states"][r.get("st")] = r.get("n")
    r = _rows(conn, "SELECT COUNT(*) AS total, SUM(rs_rank>=90) AS top, SUM(rs_rank<=10) AS bottom "
                    "FROM stock_signals WHERE trade_date=? AND rs_rank IS NOT NULL", (d,))
    if r:
        out.update({k: (r[0].get(k) or 0) for k in ("total", "top", "bottom")})
    return out


# ══ STRENGTH · Risk-adjusted momentum (ports /dash/momentum-scan) ═════════════════════
def riskadj_scan(conn, limit: int = 25) -> list:
    """Risk-adjusted momentum, read from the CANONICAL `momentum_scan` table the nightly research job
    already writes — the same rows, the same RISKADJ definition (split-adjusted 6-month return ÷
    66-day return volatility), so the Graphite page and the classic scanner can never show two
    different numbers for one name.

    🔴 The doctrine travels with the number: momentum here is a known risk-premium BETA, not
    stock-selection skill (residual alpha failed its t≥3 gate). It is a shortlister, never a buy
    list. The C-blend overlay is deliberately NOT carried into this page — it is flat-cost-only
    (NOT fundable net of participation cost) and it is derived from the Screener-era fundamentals
    path that is under primary-source remediation.

    [] when the research job has not populated `momentum_scan` on this host — the page then says so
    rather than inventing a shortlist."""
    if not _has(conn, "momentum_scan"):
        return []
    d = _latest_date(conn, "momentum_scan", "as_of")
    if not d:
        return []
    rows = _rows(conn,
                 "SELECT symbol, mom6, mom12, vol_66, riskadj, range_pos_252, turnover_cr, "
                 "riskadj_pctile, ensemble_pctile FROM momentum_scan WHERE as_of=? "
                 "AND riskadj IS NOT NULL ORDER BY riskadj DESC LIMIT ?", (d, int(limit)))
    for r in rows:
        r["as_of"] = d
    return rows


# ══ STRENGTH · All-weather capture map (ports /dash/capture-map) ══════════════════════
HORIZONS = {"63": "3 months", "126": "6 months", "252": "12 months"}


def capture_map(conn, benchmark: str = BENCHMARK, horizon: str = "63", limit: int = 20) -> list:
    """Each sector's up-capture and down-capture vs the broad market over the chosen horizon, and
    the spread between them. Down-capture < 1 = it fell LESS than the market on the market's DOWN
    days; up-capture > 1 = it rose MORE on the market's UP days. A high spread is the "all-weather"
    read: joins the rallies, defends the falls.

    Reuses the CANONICAL engine `src.automation.capture` (stored nightly row first, the engine's own
    on-read recompute as fallback), curated to the economic sectors. `horizon` is clamped to the
    engine's own window set before it can reach a column name. Widest spread first.

    Descriptive: this is a behaviour TRACK RECORD over the past window, never a forward signal."""
    h = str(horizon) if str(horizon) in HORIZONS else "63"
    try:
        from src.automation import capture
    except Exception:  # noqa: BLE001
        return []
    try:
        rows = [r for r in (capture.latest_all(benchmark, conn=conn) or [])
                if r.get("numerator") in SECTORS]
        if not rows:
            rows = capture.current_all(benchmark, conn=conn, only=SECTORS) or []
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in rows:
        up, dn = r.get("up_capture_" + h), r.get("down_capture_" + h)
        if up is None or dn is None:
            continue
        out.append({"label": _short(r.get("numerator")), "index_name": r.get("numerator"),
                    "down": dn, "up": up, "spread": float(up) - float(dn), "horizon": h,
                    "trade_date": r.get("trade_date")})
    out.sort(key=lambda r: -r["spread"])
    return out[:int(limit)]


# ══ SECTORS · standing + drill-down (ports /dash/sectors · /dash/sector-momentum) ═════
def sector_standing(conn, benchmark: str = BENCHMARK) -> list:
    """The sector board: every economic sector's relative strength vs the broad market today, its RS
    trend state and phase, and the 1/3/6/12-month RS slopes — the shape of the sweep, which is what
    a phase actually is. Strongest 3-month RS first. [] when the nightly index-RS pass hasn't run."""
    rows = sector_weather(conn, benchmark)
    rows.sort(key=lambda r: -(r.get("s3") if r.get("s3") is not None else -1e9))
    return rows


def sector_breadth(conn, limit: int = 18) -> list:
    """Constituent breadth per sector: how many of a sector's own names are in an RS uptrend vs the
    broad market, and the sector's average RS. The honest cross-check on a sector call — a sector can
    read 'strong' on two mega-caps while most of its members lag. Grouped from stored
    `stock_signals` columns; sectors with fewer than 3 names dropped."""
    if not _has(conn, "stock_signals"):
        return []
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return []
    rows = _rows(conn,
                 "SELECT primary_sector AS sector, COUNT(*) AS n, "
                 "AVG(rs_vs_broad_today) AS rs, "
                 "SUM(rs_vs_broad_trend_state IN ('UPTREND','BREAKOUT')) AS up, "
                 "SUM(rs_vs_broad_trend_state IN ('DOWNTREND','BREAKDOWN')) AS dn, "
                 "AVG(rs_rank) AS avg_rank "
                 "FROM stock_signals WHERE trade_date=? AND primary_sector IS NOT NULL "
                 "AND rs_vs_broad_today IS NOT NULL GROUP BY primary_sector HAVING n>=3 "
                 "ORDER BY rs DESC LIMIT ?", (d, int(limit)))
    for r in rows:
        n = r.get("n") or 0
        r["label"] = _short(r.get("sector"))
        r["up_pct"] = (100.0 * (r.get("up") or 0) / n) if n else None
    return rows


def sector_members(conn, sector: str, limit: int = 25) -> list:
    """The names inside one sector, strongest RS rank first — the drill-down the classic sector
    board deep-linked to. [] for an unknown sector."""
    if not sector or not _has(conn, "stock_signals"):
        return []
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return []
    return _rows(conn,
                 "SELECT symbol, rs_rank, rs_phase, rs_vs_broad_today AS rs_broad, "
                 "rs_vs_sector_today AS rs_sector, rs_vs_broad_trend_state AS state, "
                 "rsi_of_rs AS rsi FROM stock_signals WHERE trade_date=? AND primary_sector=? "
                 "AND rs_rank IS NOT NULL ORDER BY rs_rank DESC LIMIT ?",
                 (d, sector, int(limit)))


def sector_risk_economics(conn, benchmark: str = BENCHMARK, limit: int = 20) -> list:
    """What each sector's relative strength has COST in risk: the RS band position (how rich or cheap
    its RS is versus its OWN 3-year range), the regime that says whether that read is even valid, and
    its up/down capture. One row per sector, joining the two canonical engines already read above; a
    sector appears where at least one of them has landed. Widest capture spread first."""
    band = {r["index_name"]: r for r in band_lanes(conn, benchmark, limit=60) if r.get("index_name")}
    cap = {r["index_name"]: r for r in capture_map(conn, benchmark, limit=60) if r.get("index_name")}
    weather = {r.get("index_name"): r for r in sector_weather(conn, benchmark)}
    names = [n for n in SECTORS if n in band or n in cap or n in weather]
    out = []
    for n in names[:int(limit)]:
        b, c, w = band.get(n, {}), cap.get(n, {}), weather.get(n, {})
        out.append({"label": _short(n), "index_name": n,
                    "band": b.get("band"), "regime": b.get("regime"), "read": b.get("read"),
                    "down": c.get("down"), "up": c.get("up"), "spread": c.get("spread"),
                    "phase": w.get("phase"), "phase_label": w.get("phase_label"),
                    "s3": w.get("s3"), "rs_today": w.get("rs_today")})
    out.sort(key=lambda r: -(r.get("spread") if r.get("spread") is not None else -1e9))
    return out


# ── SECTORS · the business half (ports /dash/sector-economics) ────────────────────────
# The two fundamentals the classic surface charts. Key -> (metric name as stored, unit, plain word).
FUND_METRICS = {
    "roce": ("ROCE %", "%", "Return on capital employed — what the business earns on the money "
                            "employed in it"),
    "opm": ("OPM %", "%", "Operating margin — what share of revenue survives as operating profit"),
}
_FUND_Y0, _FUND_Y1 = 2015, 2026
_FUND_MIN_N = 5          # a (sector, year) median needs at least this many tagged companies


def _research_db() -> str:
    import os
    return os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")


def _median(vals: list):
    vs = sorted(v for v in vals if v is not None)
    if not vs:
        return None
    n = len(vs)
    return vs[n // 2] if n % 2 else (vs[n // 2 - 1] + vs[n // 2]) / 2.0


def sector_fundamentals(conn, metric: str = "roce") -> dict:
    """A decade of each sector's BUSINESS economics: the median ROCE % (or operating margin) of the
    companies tagged into that sector, per financial year.

    Two sources, joined here: the sector tags live in the main DB (`company_tags`, index-seeded),
    the annual fundamentals live in the separate research archive (`fundamentals_history`), opened
    READ-ONLY. Returns {} when either is absent on this host — the page then says so and shows
    nothing, because a fabricated company fundamental is not an honest sample.

    🔴 Two honesty limits travel with every number here and are rendered on the page:
      • SURVIVORSHIP — sectors are TODAY's index membership applied backwards. This is how today's
        constituents evolved, not how the sector stood then.
      • PROVENANCE — these fundamentals are the Screener-era archive under migration to NSE/BSE
        XBRL (the one known primary-source exception). Provisional until that lands.
    A cell is blank under 5 companies; the median is used, never the mean."""
    key = metric if metric in FUND_METRICS else "roce"
    label = FUND_METRICS[key][0]
    tags: dict = {}
    try:
        for r in _rows(conn, "SELECT symbol, tag FROM company_tags WHERE approved=1 "
                             "AND source='index'"):
            tags.setdefault(r.get("tag"), []).append(r.get("symbol"))
    except Exception:  # noqa: BLE001
        return {}
    if not tags:
        return {}
    years = [str(y) for y in range(_FUND_Y0, _FUND_Y1 + 1)]
    vals: dict = {}                                    # symbol -> {year: value}
    try:
        import sqlite3 as _s
        rc = _s.connect("file:%s?mode=ro" % _research_db(), uri=True)
        try:
            cur = rc.execute("SELECT symbol, period_end, value FROM fundamentals_history "
                             "WHERE metric=? AND period_type='A' AND value IS NOT NULL "
                             "AND period_end>=?", (label, str(_FUND_Y0)))
            for sym, pe, v in cur.fetchall():
                y = str(pe or "")[:4]
                if y in years:
                    vals.setdefault(sym, {})[y] = v
        finally:
            rc.close()
    except Exception:  # noqa: BLE001 — the research archive is absent on most hosts
        return {}
    if not vals:
        return {}
    matrix, keep = [], []
    for sector, syms in tags.items():
        row, pops = [], 0
        for y in years:
            got = [vals[s][y] for s in syms if s in vals and y in vals[s]]
            if len(got) >= _FUND_MIN_N:
                row.append(_median(got))
                pops += 1
            else:
                row.append(None)
        if pops >= 3:                                  # a sector needs a real decade, not one dot
            keep.append(sector)
            matrix.append(row)
    if not keep:
        return {}
    order = sorted(range(len(keep)),
                   key=lambda i: next((v for v in reversed(matrix[i]) if v is not None), -1e9),
                   reverse=True)
    return {"metric": key, "label": label, "unit": FUND_METRICS[key][1],
            "plain": FUND_METRICS[key][2], "years": years,
            "sectors": [keep[i] for i in order], "matrix": [matrix[i] for i in order],
            "n_syms": len(vals)}


# ══ DEMO fallbacks — illustrative preview data, ALWAYS flagged `sample` by the caller ═
# Owner correction #4: generate representative data when a live read is empty so the preview shows
# the full experience — but keep the real-vs-demo line HONEST (the zone renders a `sample` badge and
# the page says so in words). Never merged with live rows; a zone is wholly live or wholly sample.
DEMO_WEATHER = [
    {"label": "IT", "index_name": "Nifty IT", "phase": "TAILWIND", "phase_label": "🌤 Tailwind",
     "rs_today": 1.4, "s1": 2.1, "s3": 3.4, "s6": 4.2, "s12": 6.1, "state": "UPTREND"},
    {"label": "Metal", "index_name": "Nifty Metal", "phase": "TAILWIND", "phase_label": "🌤 Tailwind",
     "rs_today": 1.1, "s1": 1.6, "s3": 2.8, "s6": 3.1, "s12": 2.2, "state": "UPTREND"},
    {"label": "Auto", "index_name": "Nifty Auto", "phase": "RECOVERY", "phase_label": "🌅 Recovery",
     "rs_today": 0.4, "s1": 1.8, "s3": 0.9, "s6": -0.6, "s12": -2.4, "state": "UPTREND"},
    {"label": "Realty", "index_name": "Nifty Realty", "phase": "RECOVERY", "phase_label": "🌅 Recovery",
     "rs_today": 0.2, "s1": 1.3, "s3": 0.4, "s6": -1.2, "s12": -3.8, "state": "UPTREND"},
    {"label": "Bank", "index_name": "Nifty Bank", "phase": "ROLLING-OVER", "phase_label": "⛅ Rolling over",
     "rs_today": -0.2, "s1": -0.9, "s3": 0.6, "s6": 1.8, "s12": 3.2, "state": "UPTREND"},
    {"label": "Energy", "index_name": "Nifty Energy", "phase": "ROLLING-OVER", "phase_label": "⛅ Rolling over",
     "rs_today": -0.4, "s1": -1.4, "s3": 0.2, "s6": 1.1, "s12": 2.6, "state": "UPTREND"},
    {"label": "Pharma", "index_name": "Nifty Pharma", "phase": "HEADWIND", "phase_label": "🌧 Headwind",
     "rs_today": -0.9, "s1": -1.7, "s3": -2.6, "s6": -3.1, "s12": -4.4, "state": "DOWNTREND"},
    {"label": "FMCG", "index_name": "Nifty FMCG", "phase": "HEADWIND", "phase_label": "🌧 Headwind",
     "rs_today": -1.2, "s1": -2.2, "s3": -3.1, "s6": -2.8, "s12": -5.2, "state": "DOWNTREND"},
    {"label": "Media", "index_name": "Nifty Media", "phase": "NEUTRAL", "phase_label": "☁ Neutral",
     "rs_today": 0.0, "s1": 0.2, "s3": -0.3, "s6": 0.4, "s12": -0.6, "state": "SIDEWAYS"},
]

DEMO_BAND = [
    {"label": "Pharma", "index_name": "Nifty Pharma", "band": 8.0, "band_label": "At RS support",
     "regime": "MEAN_REVERTING", "state": "TOUCH_SUP", "read": "Low band · no turn yet", "detr": 14.0},
    {"label": "FMCG", "index_name": "Nifty FMCG", "band": 17.0, "band_label": "At RS support",
     "regime": "MEAN_REVERTING", "state": "INSIDE", "read": "Low band · turning", "detr": 22.0},
    {"label": "Auto", "index_name": "Nifty Auto", "band": 34.0, "band_label": "Lower band",
     "regime": "MEAN_REVERTING", "state": "INSIDE", "read": "Mid-band · rising", "detr": 38.0},
    {"label": "Realty", "index_name": "Nifty Realty", "band": 46.0, "band_label": "Mid-band",
     "regime": "TRENDING", "state": "INSIDE", "read": "Trending · band secondary", "detr": 41.0},
    {"label": "Bank", "index_name": "Nifty Bank", "band": 62.0, "band_label": "Mid-band",
     "regime": "MEAN_REVERTING", "state": "INSIDE", "read": "Mid-band · fading", "detr": 58.0},
    {"label": "Metal", "index_name": "Nifty Metal", "band": 81.0, "band_label": "Upper band",
     "regime": "MEAN_REVERTING", "state": "TOUCH_RES", "read": "At resistance", "detr": 72.0},
    {"label": "IT", "index_name": "Nifty IT", "band": 93.0, "band_label": "At RS resistance",
     "regime": "TRENDING", "state": "BREAKOUT_UP", "read": "Broke ceiling · re-rating", "detr": 64.0},
]

DEMO_CLOCK = [
    {"label": "IT", "index_name": "Nifty IT", "rr": 102.1, "mm": 102.4, "rsi": 71.0, "quadrant": "Leading"},
    {"label": "Metal", "index_name": "Nifty Metal", "rr": 101.6, "mm": 101.8, "rsi": 64.0, "quadrant": "Leading"},
    {"label": "Auto", "index_name": "Nifty Auto", "rr": 99.4, "mm": 102.1, "rsi": 58.0, "quadrant": "Improving"},
    {"label": "Realty", "index_name": "Nifty Realty", "rr": 98.8, "mm": 101.4, "rsi": 54.0, "quadrant": "Improving"},
    {"label": "Bank", "index_name": "Nifty Bank", "rr": 100.6, "mm": 99.2, "rsi": 47.0, "quadrant": "Weakening"},
    {"label": "Energy", "index_name": "Nifty Energy", "rr": 100.9, "mm": 98.8, "rsi": 44.0, "quadrant": "Weakening"},
    {"label": "Pharma", "index_name": "Nifty Pharma", "rr": 98.2, "mm": 98.4, "rsi": 31.0, "quadrant": "Lagging"},
    {"label": "FMCG", "index_name": "Nifty FMCG", "rr": 98.9, "mm": 98.9, "rsi": 36.0, "quadrant": "Lagging"},
]

DEMO_CAPTURE = [
    {"label": "FMCG", "index_name": "Nifty FMCG", "down": 0.62, "up": 0.71, "spread": 0.09},
    {"label": "Pharma", "index_name": "Nifty Pharma", "down": 0.68, "up": 0.84, "spread": 0.16},
    {"label": "IT", "index_name": "Nifty IT", "down": 0.79, "up": 1.24, "spread": 0.45},
    {"label": "Bank", "index_name": "Nifty Bank", "down": 0.94, "up": 1.02, "spread": 0.08},
    {"label": "Auto", "index_name": "Nifty Auto", "down": 1.04, "up": 1.18, "spread": 0.14},
    {"label": "Metal", "index_name": "Nifty Metal", "down": 1.31, "up": 1.44, "spread": 0.13},
    {"label": "Realty", "index_name": "Nifty Realty", "down": 1.42, "up": 1.36, "spread": -0.06},
]

DEMO_LEADERS = [
    {"symbol": "PERSISTENT", "rs_rank": 97, "primary_sector": "Nifty IT", "rsi": 68.0, "close": 5820.0},
    {"symbol": "COFORGE", "rs_rank": 95, "primary_sector": "Nifty IT", "rsi": 64.0, "close": 8140.0},
    {"symbol": "JSWSTEEL", "rs_rank": 92, "primary_sector": "Nifty Metal", "rsi": 61.0, "close": 1042.0},
    {"symbol": "HINDALCO", "rs_rank": 90, "primary_sector": "Nifty Metal", "rsi": 59.0, "close": 728.0},
    {"symbol": "TVSMOTOR", "rs_rank": 88, "primary_sector": "Nifty Auto", "rsi": 57.0, "close": 2914.0},
    {"symbol": "BHARTIARTL", "rs_rank": 86, "primary_sector": "Nifty Media", "rsi": 55.0, "close": 1684.0},
]

DEMO_LAGGARDS = [
    {"symbol": "NESTLEIND", "rs_rank": 11, "primary_sector": "Nifty FMCG", "rsi": 31.0, "close": 2210.0},
    {"symbol": "BRITANNIA", "rs_rank": 14, "primary_sector": "Nifty FMCG", "rsi": 34.0, "close": 5180.0},
    {"symbol": "DIVISLAB", "rs_rank": 17, "primary_sector": "Nifty Pharma", "rsi": 36.0, "close": 5940.0},
    {"symbol": "DABUR", "rs_rank": 19, "primary_sector": "Nifty FMCG", "rsi": 29.0, "close": 498.0},
]

DEMO_STANDING = [
    {"symbol": "PERSISTENT", "rs_rank": 97, "primary_sector": "Nifty IT", "rs_phase": "TAILWIND",
     "rsi": 68.0, "rs_broad": 2.4, "rs_sector": 1.1, "state": "UPTREND", "s1": 2.8, "s3": 4.1,
     "s6": 5.2, "s12": 7.4},
    {"symbol": "COFORGE", "rs_rank": 95, "primary_sector": "Nifty IT", "rs_phase": "TAILWIND",
     "rsi": 64.0, "rs_broad": 2.1, "rs_sector": 0.8, "state": "UPTREND", "s1": 2.2, "s3": 3.6,
     "s6": 4.4, "s12": 6.2},
    {"symbol": "TVSMOTOR", "rs_rank": 88, "primary_sector": "Nifty Auto", "rs_phase": "RECOVERY",
     "rsi": 57.0, "rs_broad": 0.9, "rs_sector": 0.6, "state": "UPTREND", "s1": 1.9, "s3": 0.7,
     "s6": -0.4, "s12": -1.8},
    {"symbol": "JSWSTEEL", "rs_rank": 92, "primary_sector": "Nifty Metal", "rs_phase": "TAILWIND",
     "rsi": 61.0, "rs_broad": 1.6, "rs_sector": 0.4, "state": "UPTREND", "s1": 1.7, "s3": 2.9,
     "s6": 3.0, "s12": 2.4},
    {"symbol": "NESTLEIND", "rs_rank": 11, "primary_sector": "Nifty FMCG", "rs_phase": "HEADWIND",
     "rsi": 31.0, "rs_broad": -1.8, "rs_sector": -0.7, "state": "DOWNTREND", "s1": -2.4, "s3": -3.2,
     "s6": -2.9, "s12": -5.6},
]

DEMO_BREADTH = [
    {"sector": "Nifty IT", "label": "IT", "n": 10, "rs": 1.4, "up": 8, "dn": 1, "up_pct": 80.0, "avg_rank": 71.0},
    {"sector": "Nifty Metal", "label": "Metal", "n": 15, "rs": 1.1, "up": 10, "dn": 3, "up_pct": 66.7, "avg_rank": 64.0},
    {"sector": "Nifty Auto", "label": "Auto", "n": 15, "rs": 0.4, "up": 8, "dn": 4, "up_pct": 53.3, "avg_rank": 57.0},
    {"sector": "Nifty Bank", "label": "Bank", "n": 12, "rs": -0.2, "up": 5, "dn": 5, "up_pct": 41.7, "avg_rank": 48.0},
    {"sector": "Nifty Pharma", "label": "Pharma", "n": 20, "rs": -0.9, "up": 5, "dn": 12, "up_pct": 25.0, "avg_rank": 38.0},
    {"sector": "Nifty FMCG", "label": "FMCG", "n": 15, "rs": -1.2, "up": 3, "dn": 10, "up_pct": 20.0, "avg_rank": 31.0},
]
