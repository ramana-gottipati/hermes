"""src/web/home/w2_reads.py — the read layer for the Graphite Markets W2-C pages.

Lane W2-C of the Graphite cutover: seasonal (tape · this-month screen · index divergence ·
expiry & holidays) · patterns (Wolfe · harmonic) · move anatomy · own-history · compare.

SAME CONTRACT AS `reads.py` (spec §5): plain rows/dicts only — NEVER HTML, never sqlite in the
render layer. Every read is BOUNDED and DEFENSIVE (a missing table/column returns an empty result,
never an exception), and imports only `src.core.db` + `src.web.home.reads` helpers. It imports NO
classic view module and NO analysis engine:

  * the seasonal family (`src/automation/seasonal_tape.py`) is DOCSTRING-HASHED — its `__doc__`
    is part of `frozen_family_hash()`. This module never imports it and never touches it; it reads
    the SAME bounded snapshot tables the classic views read (`seasonal_cells` · `seasonal_stack` ·
    `seasonal_outlook` · `seasonal_meta`, and `x_setups_signals` for the calendar conditioning).
  * the Wolfe/chart lane is actively committing on origin/main, so the Wolfe read here is plain
    bounded SQL over the nightly `wolfe_signals` snapshot — NO import of `wolfe*.py` or
    `stock_chart*.py`, hence zero collision surface.
  * own-history does NOT import `/dash/self-history`'s web-view engine (that breaks the home
    isolation gate — a recorded verdict). It re-derives the self-relative axis from the STORED
    `stock_signals` ratio columns, which are already "today vs this stock's own baseline".

DEMO fallbacks live at the bottom as named constants and are ONLY ever returned through the page
layer's `_pick`, so a demo-backed block always marks itself `sample` (standing correction #4).
"""
from __future__ import annotations

import json
import os
import sqlite3

from src.web.home.reads import _has, _latest_date, _rows

# ── seasonal ────────────────────────────────────────────────────────────────────
_AXES = ("month", "week", "weekday")
MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
              7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
WEEKDAY_ABBR = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
FISCAL_ORDER = (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)
CAL_ORDER = tuple(range(1, 13))


def seasonal_entities(conn, scope: str = "index", limit: int = 60) -> list:
    """The entities that have a persisted seasonal script, most-covered first. [] when the
    bounded snapshot hasn't been built."""
    if not _has(conn, "seasonal_cells"):
        return []
    return [r["entity"] for r in _rows(
        conn,
        "SELECT entity, COUNT(*) AS n FROM seasonal_cells WHERE scope=? "
        "GROUP BY entity ORDER BY n DESC, entity LIMIT ?", (scope, limit)) if r.get("entity")]


def seasonal_script(conn, scope: str, entity: str) -> dict:
    """{axis: {cell: row}} of the persisted cross-year script for one entity.

    A cell is `colored=1` ONLY when it cleared the full certification stack (placebo nulls +
    family-wide FDR + N>=15 years + out-of-sample sign stability + a pledged mechanism). MOST
    cells do not — the winnowing IS the finding, so the render must show the grey ones."""
    if not entity or not _has(conn, "seasonal_cells"):
        return {}
    out: dict = {}
    for r in _rows(conn,
                   "SELECT axis, cell, script_z, n_years, hit_rate, conf, colored, signed, "
                   "       emp_p_block, emp_p_phase, null_p95, sign_stable, fdr_pass, mechanism "
                   "FROM seasonal_cells WHERE scope=? AND entity=? AND axis IN (?,?,?) "
                   "ORDER BY axis, cell", (scope, entity, *_AXES)):
        try:
            out.setdefault(r["axis"], {})[int(r["cell"])] = r
        except (TypeError, ValueError):
            continue
    return out


def seasonal_certified_count(script: dict) -> tuple:
    """(n_colored, n_cells) across every axis of one entity's script — the winnowing headline."""
    n_col = n_all = 0
    for cmap in (script or {}).values():
        for row in cmap.values():
            n_all += 1
            if row.get("colored"):
                n_col += 1
    return n_col, n_all


def seasonal_year_stack(conn, scope: str, entity: str, axis: str, cell: int, limit: int = 30) -> list:
    """The per-year residual behind ONE cell — 'behind the script'. Newest year last."""
    if not _has(conn, "seasonal_stack"):
        return []
    return _rows(conn,
                 "SELECT year, mean_z, n_obs FROM seasonal_stack "
                 "WHERE scope=? AND entity=? AND axis=? AND cell=? "
                 "ORDER BY year DESC LIMIT ?", (scope, entity, axis, int(cell), limit))[::-1]


def seasonal_outlook(conn, scope: str, entity: str, axis: str = "month") -> list:
    """The persisted forward-outlook rows for one entity (latest `asof` only). A `light='white'`
    row means the confidence interval touches the 50% baseline — explicitly noise."""
    if not _has(conn, "seasonal_outlook"):
        return []
    d = _latest_date(conn, "seasonal_outlook", "asof")
    if not d:
        return []
    return _rows(conn,
                 "SELECT axis, cell, horizon, k, n, ci_lo, ci_hi, base_rate, edge, light, mechanism "
                 "FROM seasonal_outlook WHERE scope=? AND entity=? AND axis=? AND asof=? "
                 "ORDER BY cell LIMIT 40", (scope, entity, axis, d))


def seasonal_meta(conn) -> dict:
    """{k: v} of the seasonal snapshot metadata — the frozen-family sha256 fingerprints + asof.
    Rendered as provenance: the family was hashed BEFORE compute."""
    if not _has(conn, "seasonal_meta"):
        return {}
    return {r["k"]: r["v"] for r in _rows(conn, "SELECT k, v FROM seasonal_meta LIMIT 40") if r.get("k")}


def _wilson(k, n, z: float = 1.96) -> tuple:
    """Wilson 95% interval for a hit-rate — the honesty column: most rows visibly straddle 50%."""
    try:
        k, n = float(k), float(n)
    except (TypeError, ValueError):
        return (None, None)
    if n <= 0:
        return (None, None)
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    r = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def seasonal_month_screen(conn, month: int, scope: str = "index", limit: int = 40,
                          lean: str = "hot") -> list:
    """The THIS-MONTH ranked base-rate screen (the classic `/dash/seasonal-screen` claim).

    Ranked by the Wilson LOWER bound (hot) / UPPER bound (cold) of the hit-rate, NOT the raw
    percent — a raw hit-% rewards tiny samples (a lucky 3/3 outranking a proven 30/32). Every row
    carries its interval so a reader can see, on the page, that most are indistinguishable from
    chance. Display-layer ranking only: still descriptive, still not certified, not tradeable."""
    if not _has(conn, "seasonal_cells"):
        return []
    rows = _rows(conn,
                 "SELECT entity, cell, script_z, n_years, hit_rate, conf, colored, mechanism "
                 "FROM seasonal_cells WHERE scope=? AND axis='month' AND cell=? "
                 "  AND n_years IS NOT NULL AND hit_rate IS NOT NULL LIMIT 800",
                 (scope, int(month)))
    out = []
    for r in rows:
        try:
            n = int(r["n_years"] or 0)
            hr = float(r["hit_rate"])
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        lo, hi = _wilson(round(hr * n), n)
        r = dict(r)
        r["ci_lo"], r["ci_hi"] = lo, hi
        r["indistinct"] = bool(lo is not None and hi is not None and lo <= 0.5 <= hi)
        r["_key"] = (lo if lean == "hot" else -(hi if hi is not None else 1.0))
        out.append(r)
    out.sort(key=lambda x: (x["_key"] if x["_key"] is not None else -9,
                            abs(float(x.get("script_z") or 0.0))), reverse=True)
    return out[:limit]


def seasonal_divergence(conn, a: str, b: str, scope: str = "index") -> list:
    """Month-by-month cells for TWO entities side by side + the gap — 'do they move together on
    the calendar, and where do they part?'. Rows for all 12 months; missing cells render as '—'."""
    if not (a and b and _has(conn, "seasonal_cells")):
        return []
    def _map(ent):
        return {int(r["cell"]): r for r in _rows(
            conn, "SELECT cell, script_z, hit_rate, n_years, colored FROM seasonal_cells "
                  "WHERE scope=? AND entity=? AND axis='month' LIMIT 24", (scope, ent))
            if r.get("cell") is not None}
    ma, mb = _map(a), _map(b)
    out = []
    for m in CAL_ORDER:
        ra, rb = ma.get(m), mb.get(m)
        za = (ra or {}).get("script_z")
        zb = (rb or {}).get("script_z")
        gap = None
        try:
            gap = float(za) - float(zb)
        except (TypeError, ValueError):
            gap = None
        out.append({"cell": m, "a": ra, "b": rb, "gap": gap})
    return out


def calendar_conditioning(conn, sort: str = "pre_holiday_ret_delta", cap: int = 40) -> tuple:
    """(rows, asof) from the bounded `x_setups_signals` snapshot (module='calendar_conditioning').

    Each figure is a name's mean daily return in a calendar window (monthly-expiry day · expiry
    week · pre/post-holiday) MINUS its own all-days mean. Read against the seasonal null prior:
    the estate's calendar-seasonality work was largely 0-certified, so these are CONTEXT."""
    if not _has(conn, "x_setups_signals"):
        return [], ""
    raw = _rows(conn, "SELECT payload FROM x_setups_signals WHERE module=? ORDER BY rank ASC LIMIT 400",
                ("calendar_conditioning",))
    rows = []
    for r in raw:
        try:
            rows.append(json.loads(r["payload"]))
        except (TypeError, ValueError):
            continue
    asof = ""
    if _has(conn, "x_setups_meta"):
        m = _rows(conn, "SELECT v FROM x_setups_meta WHERE k='asof' LIMIT 1")
        asof = (m[0].get("v") or "") if m else ""

    def _k(r):
        try:
            f = abs(float(r.get(sort)))
            return f if f == f else -9.0
        except (TypeError, ValueError):
            return -9.0
    return sorted(rows, key=_k, reverse=True)[:max(1, cap)], asof


# ── patterns: Wolfe + harmonic (read-only over the nightly snapshots) ────────────
def wolfe_scan(conn, universe: str = "nifty500", limit: int = 40) -> tuple:
    """(rows, meta) from the nightly `wolfe_signals` snapshot — actionable (in-zone) first.

    Plain bounded SQL, NOT `src.automation.wolfe`: the Wolfe/chart lane is hot on origin/main and
    this lane must present zero collision surface. Descriptive-only — the OOS-validated edge is in
    the SELECTION, not the stop or the target."""
    if not _has(conn, "wolfe_signals"):
        return [], {}
    rows = _rows(conn,
                 "SELECT sym, dir, cmp, zlo, zhi, sl, t1, epa, up, age, q, in_zone, "
                 "       scan_date, computed_at, fresh "
                 "FROM wolfe_signals WHERE universe=? "
                 "ORDER BY in_zone DESC, age ASC LIMIT ?", (universe, max(1, limit)))
    if not rows:
        return [], {}
    m = rows[0]
    return rows, {"scan_date": m.get("scan_date"), "computed_at": m.get("computed_at"),
                  "fresh": m.get("fresh"), "universe": universe}


def harmonic_scan(conn, universe: str = "nifty500", limit: int = 40) -> tuple:
    """(rows, meta) from the nightly `harmonic_signals` snapshot — in-zone first, freshest first.
    Read BY SIDE: BULL carries a modest fit-graded selection edge; BEAR is tail/regime-only."""
    if not _has(conn, "harmonic_signals"):
        return [], {}
    rows = _rows(conn,
                 "SELECT sym, pattern, dir, state, score, cmp, d_price, prz_lo, prz_hi, "
                 "       in_zone, age, tag, scan_date, computed_at "
                 "FROM harmonic_signals WHERE universe=? "
                 "ORDER BY in_zone DESC, age ASC LIMIT ?", (universe, max(1, limit)))
    if not rows:
        return [], {}
    m = rows[0]
    return rows, {"scan_date": m.get("scan_date"), "computed_at": m.get("computed_at"),
                  "universe": universe}


# ── move anatomy (research.db `features` panel — read-only, bounded) ─────────────
RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

# Curated precursors: (plain label, technical name, column, family). ALL are trailing/structural
# and as-of the launch day — an OUTCOME column is never an input (leak-safe by construction).
PRECURSORS = (
    ("Up over the past year", "12-month return", "ret_252d", "Trend & strength"),
    ("Up over the past 3 months", "3-month return", "ret_66d", "Trend & strength"),
    ("Stronger than the market", "RS rank vs market", "h_rs_rank", "Trend & strength"),
    ("Above its 1-year trend line", "Close vs 200-DMA", "close_vs_sma200", "Trend & strength"),
    ("Above its ~2-month trend line", "Close vs 50-DMA", "close_vs_sma50", "Trend & strength"),
    ("Near its 1-year high", "% from 52-week high", "h_pct_from_52w_high", "Position"),
    ("Quiet recent range", "20-day realised volatility", "vol_20d", "Volatility & range"),
    ("Delivery running heavy", "Delivery %, 1-month", "h_avg_deliv_pct_1m", "Participation"),
    ("Turnover running heavy", "Turnover surge, 1-month", "h_turnover_surge_1m", "Participation"),
)


def move_anatomy(db_path: str = None) -> dict:
    """The FINGERPRINT (each precursor's event-mean as a standardised gap from the 1-in-10 quiet
    baseline, in baseline std-devs) + the EXCURSION ENVELOPE (median favourable vs adverse forward
    move). {} when research.db is absent on this host — the page then says so honestly.

    ⚠ It is a POST-SELECTION base rate (events are chosen because a move already fired),
    survivorship-biased UP (delisted losers absent) and the baseline is 1-in-10 sampled. A picture
    of what pre-move days looked like in hindsight, NEVER an entry rule."""
    path = db_path or RESEARCH_DB
    if not path or not os.path.exists(path):
        return {}
    try:
        con = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=10)
        con.row_factory = sqlite3.Row
    except sqlite3.Error:
        return {}
    try:
        cols = [c for (_p, _t, c, _f) in PRECURSORS]
        try:
            have = {r[1] for r in con.execute("PRAGMA table_info(features)").fetchall()}
        except sqlite3.Error:
            return {}
        cols = [c for c in cols if c in have]
        if not cols:
            return {}
        sel_b = ", ".join("avg(%s) a_%s, count(%s) n_%s" % (c, c, c, c) for c in cols)
        base = con.execute("SELECT %s FROM features WHERE label=0" % sel_b).fetchone()
        evt = con.execute("SELECT %s FROM features WHERE label=1" % sel_b).fetchone()
        if base is None or evt is None:
            return {}
        # baseline dispersion, one pass per column (sqlite has no stdev())
        bars = []
        for (plain, tech, c, fam) in PRECURSORS:
            if c not in cols:
                continue
            try:
                mu_b, mu_e = base["a_" + c], evt["a_" + c]
                if mu_b is None or mu_e is None:
                    continue
                sd = con.execute(
                    "SELECT avg((%s - ?)*(%s - ?)) v FROM features WHERE label=0 AND %s IS NOT NULL"
                    % (c, c, c), (mu_b, mu_b)).fetchone()["v"]
                sd = (float(sd) ** 0.5) if sd else 0.0
                if sd <= 0:
                    continue
                bars.append({"plain": plain, "tech": tech, "col": c, "family": fam,
                             "z": (float(mu_e) - float(mu_b)) / sd,
                             "event": float(mu_e), "baseline": float(mu_b)})
            except (sqlite3.Error, TypeError, ValueError, ZeroDivisionError):
                continue
        env = {}
        for lab, key in ((1, "event"), (0, "baseline")):
            try:
                r = con.execute(
                    "SELECT avg(mfe_6m) f, avg(mae_6m) a, count(*) n FROM features "
                    "WHERE label=? AND fwd_complete_132=1", (lab,)).fetchone()
                if r and r["n"]:
                    env[key] = {"mfe": r["f"], "mae": r["a"], "n": r["n"]}
            except sqlite3.Error:
                continue
        meta = {}
        try:
            meta = {r[0]: r[1] for r in con.execute("SELECT k, v FROM feat_meta LIMIT 40").fetchall()}
        except sqlite3.Error:
            meta = {}
        bars.sort(key=lambda b: b["z"], reverse=True)
        return {"bars": bars, "envelope": env, "meta": meta}
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass


# ── own history (self-relative, from STORED stock_signals ratio columns) ────────
# (key, plain label, stored column, unit, "high means") — every one of these is ALREADY a
# self-relative reading: today (or this month) measured against THIS stock's own baseline. No
# classic-view import, no recompute of a 3-year percentile at request time.
OWN_METRICS = (
    ("turn1m", "Turnover vs its own 1-month norm", "turnover_surge_1m", "x", "busier than usual"),
    ("turn1y", "Turnover vs its own 1-year norm", "turnover_surge_1y", "x", "busiest in a year"),
    ("deliv", "Delivery % — 1-month vs 6-month", "_deliv_gap", "pp", "more conviction than usual"),
    ("dvpt", "Delivery size vs its own 30-day average", "ratio_today_vs_avg_30d", "x", "heavier tickets"),
    ("power", "Delivery size vs its own best month", "ratio_today_vs_power_1m", "x", "near its own best"),
    ("high", "Distance from its own 1-year high", "pct_from_52w_high", "%", "near its own high"),
)


def own_history_universe(conn, limit: int = 40, sort: str = "turn1m") -> tuple:
    """(rows, as_of): today's self-relative reading for the most-traded names, from stored columns.

    Each column is "this stock now vs this stock's own baseline", so a ₹13,000 giant and a ₹180
    small-cap read on the same axis. Descriptive: self-relative extremity is CONTEXT about how
    unusual today is FOR THIS NAME, and says nothing about forward return."""
    if not _has(conn, "stock_signals"):
        return [], ""
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return [], ""
    rows = _rows(conn,
                 "SELECT symbol, primary_sector, turnover_surge_1m, turnover_surge_3m, "
                 "       turnover_surge_1y, avg_deliv_pct_1m, avg_deliv_pct_6m, "
                 "       ratio_today_vs_avg_30d, ratio_today_vs_power_1m, pct_from_52w_high, "
                 "       accum_character, rs_rank, total_value_today "
                 "FROM stock_signals WHERE trade_date=? AND total_value_today IS NOT NULL "
                 "ORDER BY total_value_today DESC LIMIT ?", (d, max(1, limit) * 3))
    for r in rows:
        try:
            r["_deliv_gap"] = float(r["avg_deliv_pct_1m"]) - float(r["avg_deliv_pct_6m"])
        except (TypeError, ValueError):
            r["_deliv_gap"] = None
    col = dict((k, c) for (k, _p, c, _u, _h) in OWN_METRICS).get(sort, "turnover_surge_1m")

    def _k(r):
        try:
            v = float(r.get(col))
            return v if v == v else -9e9
        except (TypeError, ValueError):
            return -9e9
    rows.sort(key=_k, reverse=True)
    return rows[:max(1, limit)], d


def own_history_symbol(conn, symbol: str, n: int = 760) -> dict:
    """ONE name's stored self-relative ratios, each ranked against ITS OWN trailing history of the
    same ratio (a true own-history percentile, computed from `stock_signals` rows for this symbol
    only — bounded to `n` sessions, ~3 years). {} when the name/history is absent."""
    sym = (symbol or "").strip().upper()
    if not sym or not _has(conn, "stock_signals"):
        return {}
    hist = _rows(conn,
                 "SELECT trade_date, turnover_surge_1m, turnover_surge_1y, avg_deliv_pct_1m, "
                 "       avg_deliv_pct_6m, ratio_today_vs_avg_30d, ratio_today_vs_power_1m, "
                 "       pct_from_52w_high, accum_character, rs_rank, primary_sector "
                 "FROM stock_signals WHERE symbol=? ORDER BY trade_date DESC LIMIT ?",
                 (sym, max(60, min(int(n), 1500))))
    if not hist:
        return {}
    for r in hist:
        try:
            r["_deliv_gap"] = float(r["avg_deliv_pct_1m"]) - float(r["avg_deliv_pct_6m"])
        except (TypeError, ValueError):
            r["_deliv_gap"] = None
    today = hist[0]
    out = []
    for (key, plain, col, unit, high_means) in OWN_METRICS:
        cur = today.get(col)
        try:
            cur = float(cur)
        except (TypeError, ValueError):
            cur = None
        vals = []
        for r in hist[1:]:
            try:
                v = float(r.get(col))
            except (TypeError, ValueError):
                continue
            if v == v:
                vals.append(v)
        pct = None
        typical = None
        if cur is not None and cur == cur and len(vals) >= 30:
            below = sum(1 for v in vals if v <= cur)
            pct = 100.0 * below / len(vals)
            s = sorted(vals)
            typical = s[len(s) // 2]
        out.append({"key": key, "plain": plain, "unit": unit, "high_means": high_means,
                    "value": cur, "pctile": pct, "typical": typical, "n": len(vals)})
    return {"symbol": sym, "as_of": today.get("trade_date"), "sector": today.get("primary_sector"),
            "rs_rank": today.get("rs_rank"), "character": today.get("accum_character"),
            "metrics": out, "n_sessions": len(hist)}


# ── compare (rebased overlay; the Graphite twin of the sacred /dash/compare) ────
COMPARE_MAX = 6


def compare_indices(conn, limit: int = 60) -> list:
    """The index names that have a level history — the picker universe."""
    if not _has(conn, "index_rows"):
        return []
    return [r["index_name"] for r in _rows(
        conn, "SELECT DISTINCT index_name FROM index_rows ORDER BY index_name LIMIT ?",
        (limit,)) if r.get("index_name")]


def _adj_factor_map(conn, sym: str, dates: list) -> dict:
    """Cumulative split/bonus factor per date, so a 1:1 bonus does not read as a 50% crash. Built
    from the canonical `corporate_actions` ratios; {} (no adjustment) when the table is absent."""
    if not dates or not _has(conn, "corporate_actions"):
        return {}
    acts = _rows(conn,
                 "SELECT action_type, ex_date, ratio_from, ratio_to FROM corporate_actions "
                 "WHERE symbol=? AND ex_date IS NOT NULL AND ratio_from IS NOT NULL "
                 "  AND ratio_to IS NOT NULL LIMIT 200", (sym,))
    evs = []
    for a in acts:
        try:
            f, t = float(a["ratio_from"]), float(a["ratio_to"])
        except (TypeError, ValueError):
            continue
        if f <= 0 or t <= 0:
            continue
        kind = (a.get("action_type") or "").lower()
        if "split" in kind:
            ratio = t / f          # face-value split: 10 -> 2 means price /5
        elif "bonus" in kind:
            ratio = f / (f + t)    # 1:1 bonus -> price x 0.5
        else:
            continue
        evs.append((str(a["ex_date"]), ratio))
    if not evs:
        return {}
    out = {}
    for d in dates:
        f = 1.0
        for (ex, ratio) in evs:
            if d < ex:
                f *= ratio
        out[d] = f
    return out


def compare_series(conn, idx_names: list, syms: list, sessions: int = 252) -> list:
    """Rebased overlay series for up to COMPARE_MAX lines: indices from `index_rows.close_value`,
    stocks from `bhavcopy_rows.close` on a split/bonus-ADJUSTED basis. Each returns
    {'name','kind','points':[{'t','v'}]} where v is REBASED to 100 at the common left anchor —
    render-only, no derived claim."""
    sessions = max(20, min(int(sessions or 252), 2000))
    out = []
    for name in (idx_names or [])[:COMPARE_MAX]:
        pts = _rows(conn,
                    "SELECT trade_date t, close_value v FROM index_rows "
                    "WHERE index_name=? AND close_value IS NOT NULL "
                    "ORDER BY trade_date DESC LIMIT ?", (name, sessions))[::-1]
        if len(pts) >= 2:
            out.append({"name": name, "kind": "idx", "points": pts})
    for sym in (syms or []):
        if len(out) >= COMPARE_MAX:
            break
        pts = _rows(conn,
                    "SELECT trade_date t, close v FROM bhavcopy_rows "
                    "WHERE symbol=? AND series IN ('EQ','BE') AND close IS NOT NULL "
                    "ORDER BY trade_date DESC LIMIT ?", (sym, sessions))[::-1]
        if len(pts) < 2:
            continue
        fac = _adj_factor_map(conn, sym, [p["t"] for p in pts])
        if fac:
            for p in pts:
                try:
                    p["v"] = float(p["v"]) * fac.get(p["t"], 1.0)
                except (TypeError, ValueError):
                    pass
        out.append({"name": sym, "kind": "stk", "points": pts})
    # rebase each line to 100 at its own first point inside the common window
    for s in out:
        try:
            base = float(s["points"][0]["v"])
        except (TypeError, ValueError, IndexError):
            base = 0.0
        if base <= 0:
            s["points"] = []
            continue
        s["points"] = [{"t": p["t"], "v": 100.0 * float(p["v"]) / base}
                       for p in s["points"] if p.get("v") is not None]
        s["change"] = (s["points"][-1]["v"] - 100.0) if s["points"] else None
    return [s for s in out if s["points"]]


def valid_symbols(conn, syms: list) -> list:
    """Keep only symbols the NSE cash tape actually carries (uppercased, deduped, capped)."""
    seen, keep = set(), []
    for s in (syms or []):
        s = (s or "").strip().upper()
        if not s or s in seen or not s.replace("&", "").replace("-", "").replace(".", "").isalnum():
            continue
        seen.add(s)
        keep.append(s)
        if len(keep) >= COMPARE_MAX:
            break
    if not keep or not _has(conn, "bhavcopy_rows"):
        return []
    qs = ",".join("?" * len(keep))
    have = {r["symbol"] for r in _rows(
        conn, "SELECT DISTINCT symbol FROM bhavcopy_rows WHERE symbol IN (%s) "
              "AND series IN ('EQ','BE') LIMIT 50" % qs, tuple(keep))}
    return [s for s in keep if s in have]


# ── demo fallbacks (returned ONLY through _pick, so the block marks itself 'sample') ──
DEMO_SCRIPT = {
    "month": {m: {"axis": "month", "cell": m, "script_z": z, "n_years": 24, "hit_rate": hr,
                  "conf": 0.0, "colored": 0, "signed": 0, "mechanism": None}
              for (m, z, hr) in ((1, 0.11, 0.54), (2, -0.06, 0.46), (3, 0.19, 0.58), (4, 0.24, 0.62),
                                 (5, -0.02, 0.50), (6, -0.14, 0.42), (7, 0.08, 0.54), (8, 0.03, 0.50),
                                 (9, -0.21, 0.38), (10, 0.16, 0.58), (11, 0.27, 0.62), (12, 0.05, 0.54))},
    "weekday": {w: {"axis": "weekday", "cell": w, "script_z": z, "n_years": 24, "hit_rate": hr,
                    "conf": 0.0, "colored": 0, "signed": 0, "mechanism": None}
                for (w, z, hr) in ((0, -0.04, 0.49), (1, 0.06, 0.52), (2, 0.02, 0.51),
                                   (3, -0.01, 0.50), (4, 0.09, 0.53))},
}

DEMO_SCREEN = [
    {"entity": "Nifty Auto", "cell": 7, "script_z": 0.31, "n_years": 22, "hit_rate": 0.64,
     "colored": 0, "ci_lo": 0.43, "ci_hi": 0.81, "indistinct": True, "mechanism": None},
    {"entity": "Nifty IT", "cell": 7, "script_z": 0.22, "n_years": 24, "hit_rate": 0.58,
     "colored": 0, "ci_lo": 0.39, "ci_hi": 0.75, "indistinct": True, "mechanism": None},
    {"entity": "Nifty Metal", "cell": 7, "script_z": -0.28, "n_years": 21, "hit_rate": 0.38,
     "colored": 0, "ci_lo": 0.21, "ci_hi": 0.58, "indistinct": True, "mechanism": None},
]

DEMO_CALENDAR = ([
    {"symbol": "SAMPLEA", "expiry_ret_delta": 0.0012, "expiry_week_ret_delta": -0.0003,
     "pre_holiday_ret_delta": 0.0025, "post_holiday_ret_delta": -0.0011, "n_days": 900, "n_expiry": 42},
    {"symbol": "SAMPLEB", "expiry_ret_delta": -0.0006, "expiry_week_ret_delta": 0.0001,
     "pre_holiday_ret_delta": 0.0009, "post_holiday_ret_delta": 0.0002, "n_days": 700, "n_expiry": 33},
], "sample")

DEMO_WOLFE = ([
    {"sym": "SAMPLEA", "dir": "BULL", "cmp": 412.5, "zlo": 398.0, "zhi": 408.0, "sl": 386.0,
     "t1": 452.0, "epa": 486.0, "up": 17.8, "age": 4, "q": 21, "in_zone": 0},
    {"sym": "SAMPLEB", "dir": "BEAR", "cmp": 1180.0, "zlo": 1195.0, "zhi": 1215.0, "sl": 1246.0,
     "t1": 1104.0, "epa": 1050.0, "up": 11.0, "age": 9, "q": 17, "in_zone": 1},
], {"scan_date": "sample", "computed_at": "", "fresh": 15, "universe": "nifty500"})

DEMO_HARMONIC = ([
    {"sym": "SAMPLEA", "pattern": "Gartley", "dir": "BULL", "state": "CONFIRMED", "score": 0.87,
     "cmp": 412.5, "d_price": 404.0, "prz_lo": None, "prz_hi": None, "in_zone": 1, "age": 3,
     "tag": "edge"},
    {"sym": "SAMPLEB", "pattern": "Bat", "dir": "BEAR", "state": "FORMING", "score": None,
     "cmp": 1180.0, "d_price": None, "prz_lo": 1206.0, "prz_hi": 1228.0, "in_zone": 0, "age": 6,
     "tag": "tail"},
], {"scan_date": "sample", "computed_at": "", "universe": "nifty500"})

def _demo_line(name, kind, drift, wobble):
    pts, v = [], 100.0
    for i in range(120):
        v *= (1.0 + drift + wobble * ((i * 7919) % 23 - 11) / 1000.0)
        pts.append({"t": "2026-%02d-%02d" % (1 + i // 21, 1 + i % 21), "v": v})
    return {"name": name, "kind": kind, "points": pts, "change": pts[-1]["v"] - 100.0}


DEMO_COMPARE = [_demo_line("Sample index", "idx", 0.0012, 0.9),
                _demo_line("SAMPLEA", "stk", 0.0026, 2.1)]

DEMO_OWN = ([
    {"symbol": "SAMPLEA", "primary_sector": "Auto", "turnover_surge_1m": 2.4, "turnover_surge_3m": 1.9,
     "turnover_surge_1y": 1.6, "avg_deliv_pct_1m": 61.0, "avg_deliv_pct_6m": 48.0, "_deliv_gap": 13.0,
     "ratio_today_vs_avg_30d": 1.8, "ratio_today_vs_power_1m": 0.92, "pct_from_52w_high": -3.2,
     "accum_character": "STEADY", "rs_rank": 41, "total_value_today": 8.2e8},
    {"symbol": "SAMPLEB", "primary_sector": "IT", "turnover_surge_1m": 0.7, "turnover_surge_3m": 0.8,
     "turnover_surge_1y": 0.6, "avg_deliv_pct_1m": 39.0, "avg_deliv_pct_6m": 47.0, "_deliv_gap": -8.0,
     "ratio_today_vs_avg_30d": 0.6, "ratio_today_vs_power_1m": 0.31, "pct_from_52w_high": -21.4,
     "accum_character": "QUIET", "rs_rank": 318, "total_value_today": 5.1e8},
], "sample")
