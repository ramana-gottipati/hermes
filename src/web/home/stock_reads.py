"""src/web/home/stock_reads.py — the Graphite stock page's per-symbol read layer (W1).

Sibling of `reads.py` (which is market-wide) and bound by the SAME contract:

  * returns plain rows / dicts / scalars — **never HTML**;
  * imports ONLY `src.core.db` and genuinely-shared, NON-render helpers
    (`corp_actions`, `adjust`, `results_calendar`, `x_setups_signals`, `scoring`);
  * imports NO preview/legacy render module — `dashboard`, `hub_sections_v3`,
    `stock_chart_v3`, `term_chip`, … are all banned by `tests/test_home_isolation.py`,
    so every concept the M4 hub took from them is RE-IMPLEMENTED here from the tables;
  * every read is bounded and defensive: a missing table/row yields an empty result,
    never an exception (a busy or partial DB must never 500 the page).

It lives in its own module (rather than growing `reads.py`) so the market-wide read layer
stays byte-untouched while several cutover lanes are in flight.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

# the deepest chart window we will ever assemble in one request (payload budget, spec §A)
DEFAULT_SESSIONS = 756          # ~3 trading years
MAX_SESSIONS = 6000             # "Max" — the whole bhav archive for the deepest name


# ── primitives (same discipline as reads.py) ─────────────────────────────────────
def _has(conn, table: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def _row(conn, sql: str, params=()) -> Optional[dict]:
    try:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r is not None else None
    except sqlite3.Error:
        return None


def _rows(conn, sql: str, params=()) -> list:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error:
        return []


def _pctile(vals: list, x) -> Optional[float]:
    """Percentile rank of `x` inside `vals` (0-100). None when the history is too thin to be
    honest — the same 20-observation floor the market-wide reference layer uses."""
    try:
        xv = float(x)
    except (TypeError, ValueError):
        return None
    nums = []
    for v in vals:
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            continue
    if len(nums) < 20:
        return None
    below = sum(1 for v in nums if v < xv)
    ties = sum(1 for v in nums if v == xv)
    return round(100.0 * (below + 0.5 * ties) / len(nums), 1)


def _median(vals: list) -> Optional[float]:
    nums = sorted(float(v) for v in vals if isinstance(v, (int, float)))
    if not nums:
        return None
    mid = len(nums) // 2
    return nums[mid] if len(nums) % 2 else (nums[mid - 1] + nums[mid]) / 2.0


def _trend(vals: list, back: int = 10) -> Optional[str]:
    """'up' / 'down' / 'flat' from the last `back` observations vs the ones before them.
    A factual direction, never a judgment (the ref-chip grammar)."""
    nums = [float(v) for v in vals if isinstance(v, (int, float))]
    if len(nums) < back * 2:
        return None
    recent = sum(nums[-back:]) / back
    prior = sum(nums[-back * 2:-back]) / back
    if prior == 0:
        return None
    delta = (recent - prior) / abs(prior)
    return "up" if delta > 0.05 else ("down" if delta < -0.05 else "flat")


# ── symbol resolution (a miss must route onward, never dead-end) ─────────────────
def clean_symbol(raw) -> str:
    """Hard-sanitise anything arriving from the query string. NSE tickers are A-Z 0-9 & . -."""
    s = "".join(ch for ch in str(raw or "").strip().upper() if ch.isalnum() or ch in "&.-")
    return s[:20]


def exists(conn, sym: str) -> bool:
    if not sym or not _has(conn, "bhavcopy_rows"):
        return False
    return _row(conn, "SELECT 1 AS x FROM bhavcopy_rows WHERE symbol=? AND series IN ('EQ','BE') "
                      "LIMIT 1", (sym,)) is not None


def suggest(conn, sym: str, limit: int = 6) -> list:
    """Did-you-mean candidates for an unknown ticker: prefix match first, then company-name
    substring. [] when nothing is close (the page then offers the search box + screener)."""
    if not sym or not _has(conn, "bhavcopy_rows"):
        return []
    out, seen = [], set()
    for r in _rows(conn, "SELECT DISTINCT symbol FROM bhavcopy_rows WHERE series IN ('EQ','BE') "
                         "AND symbol LIKE ? ORDER BY symbol LIMIT ?", (sym[:4] + "%", limit)):
        s = r.get("symbol")
        if s and s not in seen:
            seen.add(s)
            out.append({"symbol": s, "name": ""})
    if len(out) < limit and _has(conn, "nse_equity_list"):
        for r in _rows(conn, "SELECT symbol, company_name FROM nse_equity_list "
                             "WHERE UPPER(company_name) LIKE ? ORDER BY symbol LIMIT ?",
                       ("%" + sym + "%", limit)):
            s = r.get("symbol")
            if s and s not in seen:
                seen.add(s)
                out.append({"symbol": s, "name": r.get("company_name") or ""})
    return out[:limit]


# ── the ONE bounded core read (feeds identity · digest · every section) ──────────
def core(conn, sym: str) -> dict:
    """One bounded pass over the per-symbol signal tables. Absent tables/rows → None fields.

    Re-implements `hub_sections_v3.load_core` from the tables directly (that module is banned by
    the isolation gate) and adds the fields the classic dossier header carries.
    """
    c: dict = {"sym": sym}
    c["sig"] = _row(conn, "SELECT * FROM stock_signals WHERE symbol=? ORDER BY trade_date DESC "
                          "LIMIT 1", (sym,)) if _has(conn, "stock_signals") else None
    bars = _rows(conn, "SELECT trade_date, close, prev_close, deliv_per, value, volume "
                       "FROM bhavcopy_rows WHERE symbol=? AND series IN ('EQ','BE') "
                       "ORDER BY trade_date DESC LIMIT 2", (sym,)) if _has(conn, "bhavcopy_rows") else []
    c["bar"] = bars[0] if bars else None
    c["prev"] = bars[1] if len(bars) > 1 else None
    c["mep"] = _row(conn, "SELECT * FROM mep_signals WHERE symbol=? ORDER BY trade_date DESC "
                          "LIMIT 1", (sym,)) if _has(conn, "mep_signals") else None
    c["pt"] = _row(conn, "SELECT * FROM pattern_scores WHERE symbol=? ORDER BY scored_at DESC "
                         "LIMIT 1", (sym,)) if _has(conn, "pattern_scores") else None
    c["ca"] = _row(conn, "SELECT * FROM capital_allocation_scores WHERE symbol=? "
                         "ORDER BY as_of DESC LIMIT 1", (sym,)) \
        if _has(conn, "capital_allocation_scores") else None
    c["cci"] = _row(conn, "SELECT * FROM concall_scores WHERE symbol=? "
                          "ORDER BY as_of_period DESC, rowid DESC LIMIT 1", (sym,)) \
        if _has(conn, "concall_scores") else None
    # NOTE: wolfe_signals keys on `sym`, NOT `symbol` (see wolfe._ensure_scan_table). Querying
    # `symbol` raises, gets swallowed, and the Wolfe badge silently never fires — the exact bug
    # the M4 hub shipped with. Pinned by tests/test_home_stock_page.
    c["wolfe"] = _row(conn, "SELECT * FROM wolfe_signals WHERE sym=? "
                            "ORDER BY scan_date DESC, id DESC LIMIT 1", (sym,)) \
        if _has(conn, "wolfe_signals") else None
    c["fno"] = _row(conn, "SELECT * FROM fno_oi_signals WHERE symbol=? ORDER BY trade_date DESC "
                          "LIMIT 1", (sym,)) if _has(conn, "fno_oi_signals") else None
    c["cpr"] = cpr_by_tf(conn, sym)
    c["name"] = ""
    for tbl, col in (("nse_equity_list", "company_name"), ("security_master", "company_name")):
        if not c["name"] and _has(conn, tbl):
            r = _row(conn, f"SELECT COALESCE({col},'') AS n FROM {tbl} WHERE symbol=?", (sym,))
            c["name"] = (r or {}).get("n") or ""
    c["themes"] = themes(conn, sym)
    return c


def cpr_by_tf(conn, sym: str) -> dict:
    """Latest CPR row per timeframe (D/W/M/Q) — the Structure section, read straight from the
    table (the classic `_cpr_latest_by_tf` helper lives in the banned `dashboard` module)."""
    if not _has(conn, "cpr_signals"):
        return {}
    out: dict = {}
    for r in _rows(conn, "SELECT * FROM cpr_signals WHERE symbol=? "
                         "ORDER BY period_end_date DESC LIMIT 40", (sym,)):
        tf = str(r.get("timeframe") or "").upper()
        if tf and tf not in out:
            out[tf] = r
    return out


def themes(conn, sym: str, limit: int = 5) -> list:
    try:
        from src.automation import theme_tags as TT
        return list((TT.approved_tags_for(conn, [sym]).get(sym) or [])[:limit])
    except Exception:  # noqa: BLE001 — the tags layer is optional; never fail the page
        return []


# ── the chart data island (bounded; corporate-action back-adjusted) ──────────────
def chart_island(conn, sym: str, max_sessions: int = DEFAULT_SESSIONS) -> dict:
    """{"series": [...oldest-first...], "zones": [...], "adjusted": bool, "n": int}.

    Same assembly the classic chart uses — bhav OHLC + DVPT + delivery + traded/delivered value,
    back-adjusted for splits/bonuses via the CANONICAL `adjust.adjustment_factors`, tape-primary
    from `corp_actions.price_ratios` (the exact ex-date + ratio, so sub-30% actions adjust too).
    Rupee figures (turnover, delivered value) use RAW prices — they are split-invariant by
    construction, so back-adjusting them would double-count.
    """
    if not _has(conn, "bhavcopy_rows"):
        return {"series": [], "zones": [], "adjusted": False, "n": 0}
    n = max(60, min(int(max_sessions or DEFAULT_SESSIONS), MAX_SESSIONS))
    raw = _rows(conn,
                "SELECT b.trade_date, b.open, b.high, b.low, b.close, b.prev_close, b.deliv_per, "
                "       b.value, b.deliv_qty, s.delivery_value_per_trade AS dvpt, "
                "       s.ratio_today_vs_power_1m AS r1m "
                "FROM bhavcopy_rows b LEFT JOIN stock_signals s "
                "  ON s.symbol=b.symbol AND s.trade_date=b.trade_date "
                "WHERE b.symbol=? AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL) "
                "ORDER BY b.trade_date DESC LIMIT ?", (sym, n))
    series = []
    for r in reversed(raw):
        close = r.get("close")
        if close is None:
            continue
        dq = r.get("deliv_qty")
        series.append({
            "t": str(r.get("trade_date"))[:10],
            "o": r.get("open") if r.get("open") is not None else close,
            "h": r.get("high") if r.get("high") is not None else close,
            "l": r.get("low") if r.get("low") is not None else close,
            "c": close,
            "prev_close": r.get("prev_close"),
            "dvpt": r.get("dvpt"),
            "dp": round(r["deliv_per"], 1) if r.get("deliv_per") is not None else None,
            "r1m": round(r["r1m"], 2) if r.get("r1m") is not None else None,
            "tv": round(float(r["value"]), 2) if r.get("value") is not None else None,
            "dv": round(dq * close, 2) if (dq is not None and close is not None) else None,
        })
    adjusted = False
    if series:
        try:
            from src.automation import adjust
            try:
                from src.automation.corp_actions import price_ratios
                events = price_ratios(conn, sym)
            except Exception:  # noqa: BLE001 — tape absent → inference-only, the legacy fallback
                events = {}
            factors = adjust.adjustment_factors(
                [{"trade_date": s["t"], "close": s["c"], "prev_close": s.get("prev_close")}
                 for s in series], events=events)
            for f, s in zip(factors, series):
                if f != 1.0:
                    adjusted = True
                for k in ("o", "h", "l", "c"):
                    s[k] = round(s[k] * f, 2)
        except Exception:  # noqa: BLE001 — an adjustment failure must never blank the chart
            pass
    for s in series:
        s.pop("prev_close", None)
    return {"series": series, "zones": zone_lines(conn, sym), "adjusted": adjusted,
            "n": len(series)}


_ZONE_DEFS = (("P1M", "avg_close_p1m"), ("P3M", "avg_close_p3m"), ("P6M", "avg_close_p6m"),
              ("P12M", "avg_close_p12m"), ("R12M", "avg_close_r12m"))


def zone_lines(conn, sym: str) -> list:
    """The institutional price zones drawn on the chart (label + price)."""
    sig = _row(conn, "SELECT * FROM stock_signals WHERE symbol=? ORDER BY trade_date DESC LIMIT 1",
               (sym,)) if _has(conn, "stock_signals") else None
    if not sig:
        return []
    out = []
    for label, col in _ZONE_DEFS:
        v = sig.get(col)
        if v:
            out.append({"label": label, "price": round(float(v), 2)})
    return out


# ── the Pro reference layer: percentile vs the stock's OWN recent history ────────
def self_reference(conn, sym: str, n: int = 252) -> dict:
    """{'deliv': ref, 'turnover': ref, 'dvpt': ref} where each ref = {'pctile','typical','n'}
    — the exact shape `components.ref_chip` consumes.

    This is the reference-point premium AT THE STOCK LEVEL: is today's delivery / turnover /
    delivery-size unusual FOR THIS NAME? Computed from the stock's own last ~1 year of bhav rows,
    so it never needs the `/dash/self-history` web-view engine (importing that breaks the
    isolation gate — the same verdict the market map already recorded).
    """
    out: dict = {"deliv": {}, "turnover": {}, "dvpt": {}}
    if not _has(conn, "bhavcopy_rows"):
        return out
    rows = _rows(conn, "SELECT b.deliv_per, b.value, s.delivery_value_per_trade AS dvpt "
                       "FROM bhavcopy_rows b LEFT JOIN stock_signals s "
                       "  ON s.symbol=b.symbol AND s.trade_date=b.trade_date "
                       "WHERE b.symbol=? AND b.series IN ('EQ','BE') "
                       "ORDER BY b.trade_date DESC LIMIT ?", (sym, int(n)))
    if not rows:
        return out
    today, hist = rows[0], rows[1:]
    for key, col in (("deliv", "deliv_per"), ("turnover", "value"), ("dvpt", "dvpt")):
        vals = [r.get(col) for r in hist if r.get(col) is not None]
        p = _pctile(vals, today.get(col))
        if p is None:
            continue
        out[key] = {"pctile": p, "typical": _median(vals), "n": len(vals),
                    "trend": _trend(list(reversed(vals)))}
    return out


# ── context rail reads ───────────────────────────────────────────────────────────
def peers(conn, sym: str, limit: int = 8) -> list:
    """Same-sector names by turnover, from the canonical `stock_signals.primary_sector`."""
    if not _has(conn, "stock_signals"):
        return []
    me = _row(conn, "SELECT primary_sector FROM stock_signals WHERE symbol=? "
                    "ORDER BY trade_date DESC LIMIT 1", (sym,))
    sec = (me or {}).get("primary_sector")
    if not sec:
        return []
    d = _row(conn, "SELECT MAX(trade_date) AS d FROM stock_signals")
    rows = _rows(conn, "SELECT symbol, rs_rank FROM stock_signals WHERE primary_sector=? "
                       "AND trade_date=? AND symbol<>? ORDER BY rs_rank DESC LIMIT ?",
                 (sec, (d or {}).get("d"), sym, int(limit)))
    return [{"symbol": r["symbol"], "rs_rank": r.get("rs_rank"), "sector": sec} for r in rows]


def news_for(conn, sym: str, limit: int = 8) -> list:
    """Headlines tagged to THIS symbol (news_symbol_tags ⋈ sent_news). [] when either is absent."""
    if not (_has(conn, "news_symbol_tags") and _has(conn, "sent_news")):
        return []
    return _rows(conn, "SELECT n.source, n.url, n.title, n.sent_at FROM news_symbol_tags t "
                       "JOIN sent_news n ON n.url=t.news_url WHERE t.symbol=? "
                       "ORDER BY n.sent_at DESC LIMIT ?", (sym, int(limit)))


def results_next(sym: str, days: int = 60) -> Optional[dict]:
    try:
        from src.automation.results_calendar import upcoming_results
        for r in upcoming_results(days=days) or []:
            row = dict(r)
            if str(row.get("symbol", "")).upper() == sym:
                return row
    except Exception:  # noqa: BLE001
        return None
    return None


def actions_for(conn, sym: str, days: int = 90, limit: int = 6) -> list:
    try:
        from src.automation.corp_actions import upcoming
        rows, _as_of = upcoming(conn, days=days)
        return [dict(r) for r in (rows or [])
                if str(dict(r).get("symbol", "")).upper() == sym][:limit]
    except Exception:  # noqa: BLE001
        return []


# ── the X-setups dossier block (X-04 · X-07 · X-09 for THIS symbol) ─────────────
X_MODULES = ("base_breakout", "volume_shelves", "overnight_split")


def x_setups(conn, sym: str) -> dict:
    """{'base_breakout': payload|None, 'volume_shelves': …, 'overnight_split': …, 'asof': str}.

    Reads the SAME nightly `x_setups_signals` snapshot that `x_setups_signals.latest()` /
    `calendar_conditioning_view` read, and never recomputes at render time. Two deliberate
    differences from calling `latest()`:

      * it filters `WHERE module=? AND symbol=?` — a dossier block wants ONE row, not the whole
        ~4,600-row scan decoded from JSON on every page view;
      * `latest()` calls `ensure_table()`, which issues a `CREATE TABLE IF NOT EXISTS` — a WRITE.
        This page is strictly read-only, and the API process must never open a write transaction
        against the live DB, so the table's presence is probed instead.

    Both stay stdlib-only (numpy lives in the compute half), which is what the prod venv requires.
    A missing table (fresh clone / pre-first-scan box) honest-empties.
    """
    import json as _json
    out: dict = {m: None for m in X_MODULES}
    out["asof"] = ""
    if not _has(conn, "x_setups_signals"):
        return out
    for mod in X_MODULES:
        r = _row(conn, "SELECT payload FROM x_setups_signals WHERE module=? AND symbol=? "
                       "ORDER BY rank ASC LIMIT 1", (mod, sym))
        if not r:
            continue
        try:
            out[mod] = _json.loads(r["payload"])
        except (ValueError, TypeError, KeyError):
            continue
    meta = _row(conn, "SELECT v FROM x_setups_meta WHERE k='asof'") if _has(conn, "x_setups_meta") else None
    out["asof"] = (meta or {}).get("v") or ""
    return out


def quality_thresholds() -> tuple:
    """(QG_THRESHOLD, QG_MAX, UNVERIFIED_MULTIPLIER) imported from the scorer — the real numbers,
    never restated in the view (the calculations-are-canonical rule)."""
    try:
        from src.automation.scoring import QG_MAX, QG_THRESHOLD, UNVERIFIED_MULTIPLIER
        return (QG_THRESHOLD, QG_MAX, UNVERIFIED_MULTIPLIER)
    except Exception:  # noqa: BLE001
        return (151.2, 252, 0.70)


def _selftest() -> int:
    """Hermetic: an EMPTY in-memory DB must honest-empty every read, never raise."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    assert clean_symbol(" ta<script>ta ") == "TASCRIPTTA"
    assert clean_symbol("A" * 50) == "A" * 20
    assert exists(conn, "TCS") is False
    assert suggest(conn, "TC") == []
    c = core(conn, "TCS")
    assert c["sym"] == "TCS" and c["sig"] is None and c["cpr"] == {} and c["themes"] == []
    isl = chart_island(conn, "TCS")
    assert isl == {"series": [], "zones": [], "adjusted": False, "n": 0}
    assert self_reference(conn, "TCS") == {"deliv": {}, "turnover": {}, "dvpt": {}}
    assert peers(conn, "TCS") == [] and news_for(conn, "TCS") == []
    x = x_setups(conn, "TCS")
    assert x["asof"] == "" and all(x[m] is None for m in X_MODULES)
    assert _pctile([1, 2, 3], 2) is None                     # under the 20-observation floor
    assert _pctile(list(range(100)), 50) is not None
    qt = quality_thresholds()
    assert len(qt) == 3 and qt[1] >= 100
    print("home/stock_reads selftest OK — every read honest-empties on an empty DB")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
