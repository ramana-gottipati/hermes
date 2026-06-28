"""
strategist_view.py — Lane B · the STRATEGIST DASHBOARD at /dash/strategist.

Every strategy's current read AT A GLANCE: one card per strategy showing its
count, freshness, top names + a one-line note, and a health pill — each card
links to its deep page. The single "where do I look first" surface that sits
above the individual strategy lenses.

Ownership / isolation (docs/parallel-sessions-PLAN.md §1, Lane B): this is a
NEW, self-contained module. It imports ONLY:
  * src.web.ui_kit          — chrome (read-only; the v2 "Trust" look)
  * src.web.v2_surfaces     — the canonical site nav (read-only, best-effort)
  * src.core.db             — precomputed-table reads
It does NOT touch dashboard.py / cockpit.py / ui_kit.py / v2_surfaces.py /
wolfe* (no edits). Routes self-mount via `router` (included from main.py at EOF).

Read-API contract (plan §2b): consumes `strategy_registry.summary(conn)` (Lane C)
when present; otherwise falls back to an in-module derivation of the SAME shape
over the precomputed tables (stock_signals, mep_signals, cpr_signals,
concall_scores). PRECOMPUTED reads only — never recompute a strategy on-read.

summary() row shape (the fixed contract):
    { "key", "label", "route", "count", "as_of",
      "top": [{"symbol", "note"}, ...], "health": "ok|stale|empty" }
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web import ui_kit as K

log = logging.getLogger("hermes.strategist")
router = APIRouter()


# ── nav (best-effort: carry the full v2 site nav; fall back to ui_kit default) ──
def _nav_html(active: str) -> str:
    try:
        from src.web import v2_surfaces as V
        return K.nav_links(V.site_nav(active))
    except Exception:  # noqa: BLE001 — nav is chrome; never fatal
        return ""


def _sub(active: str) -> str:
    """The Strategies altitude sub-nav, with Strategist as the lead item (plan §2a)."""
    items = [
        ("Strategist", "/dash/strategist", active == "strategist"),
        ("Hub", "/dash/strategies", False),
        ("Conviction", "/dash/conviction", False),
        ("Positioning", "/dash/stocks", False),
        ("Accumulation (MEP)", "/dash/mep", False),
        ("Structure", "/dash/cpr", False),
        ("Strength", "/dash/leaders", False),
        ("Credibility", "/dash/concalls", False),
        ("Growth-intent", "/dash/growth", False),
        ("Wolfe · Scan", "/dash/wolfe/scan", False),
        ("Launchpad", "/dash/launchpad", False),
        ("Screen+", "/dash/screen2", False),
    ]
    return K.subnav(items)


# ── freshness helper ─────────────────────────────────────────────────────────
def _staleness(as_of: str | None) -> str:
    """ok if within ~6 days of today, stale if older, empty if missing."""
    if not as_of:
        return "empty"
    s = str(as_of)[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        # period strings like 'FY25Q4' — treat as present-but-undatable → ok
        return "ok"
    return "ok" if (date.today() - d).days <= 6 else "stale"


def _latest(conn, table: str, col: str = "trade_date"):
    try:
        r = conn.execute(f"SELECT MAX({col}) d FROM {table}").fetchone()
        return r["d"] if r else None
    except Exception:  # noqa: BLE001
        return None


# liquidity / universe gate, mirrors dashboard._SCAN_FILTERS (kept self-contained)
_LIQ = ("b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL) "
        "AND b.value > 10000000 AND b.close > 20 "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list)")


# ── the fallback derivation (same shape as Lane C's strategy_registry.summary) ──
def _fallback_summary(conn) -> list[dict]:
    out: list[dict] = []
    sig_date = _latest(conn, "stock_signals")

    def _rows(sql, params=()):
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:  # noqa: BLE001
            log.warning("strategist fallback query failed: %s", e)
            return None

    # 1. Conviction — tri-pillar blend (positioning + RS); the cross-pillar shortlist
    if sig_date:
        conv = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
        r = _rows(
            f"""SELECT s.symbol, {conv} conv, s.p_score, s.rs_rank
                FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                  AND {_LIQ}
                ORDER BY conv DESC LIMIT 600""", (sig_date,))
        if r is not None:
            strong = [x for x in r if (x["conv"] or 0) >= 78]
            out.append({
                "key": "conviction", "label": "Conviction", "route": "/dash/conviction",
                "count": len(strong), "as_of": sig_date,
                "top": [{"symbol": x["symbol"], "note": f"conv {x['conv']:.0f}"}
                        for x in r[:5]],
                "health": _staleness(sig_date)})

    # 2. Positioning · DVPT — institutional positioning by power-baseline score
    if sig_date:
        r = _rows(
            f"""SELECT s.symbol, s.p_score, s.trigger_rank,
                       s.ratio_today_vs_power_1m x1
                FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                  AND {_LIQ}
                ORDER BY COALESCE(s.p_score,-1) DESC,
                         COALESCE(s.delivery_value_today,0) DESC LIMIT 600""",
            (sig_date,))
        if r is not None:
            strong = [x for x in r if (x["p_score"] or 0) >= 4]
            out.append({
                "key": "stocks", "label": "Positioning · DVPT", "route": "/dash/stocks",
                "count": len(strong), "as_of": sig_date,
                "top": [{"symbol": x["symbol"],
                         "note": (f"{x['trigger_rank'] or '-'} · "
                                  f"{('%.1f×' % x['x1']) if x['x1'] else '—'}")}
                        for x in r[:5]],
                "health": _staleness(sig_date)})

    # 3. Accumulation · MEP — strong signed accumulation phase (descriptor-only)
    mep_date = _latest(conn, "mep_signals")
    if mep_date:
        r = _rows(
            """SELECT symbol, mep_score_smooth ph, mep_state_smooth st
               FROM mep_signals WHERE trade_date=? AND mep_score_smooth IS NOT NULL
               ORDER BY mep_score_smooth DESC LIMIT 600""", (mep_date,))
        if r is not None:
            accum = [x for x in r if (x["st"] or "") in ("STRONG_ACCUM", "ACCUM")]
            out.append({
                "key": "mep", "label": "Accumulation · MEP", "route": "/dash/mep",
                "count": len(accum), "as_of": mep_date,
                "top": [{"symbol": x["symbol"],
                         "note": f"{(x['st'] or '').replace('_',' ').title()} {x['ph']:+.2f}"}
                        for x in r[:5]],
                "health": _staleness(mep_date)})

    # 4. Structure · CPR — fresh confirmed bull-U reversals on the daily timeframe
    cpr_date = _latest(conn, "cpr_signals", "period_end_date")
    if cpr_date:
        r = _rows(
            """SELECT symbol, compression_pctile cp, days_since_pattern dsp, confirmed
               FROM cpr_signals
               WHERE timeframe='D' AND period_end_date=?
                 AND pattern='BULL_U'
               ORDER BY confirmed DESC, COALESCE(compression_pctile,0) DESC LIMIT 600""",
            (cpr_date,))
        if r is not None:
            fresh = [x for x in r if (x["dsp"] is not None and x["dsp"] <= 3)]
            out.append({
                "key": "cpr", "label": "Structure · CPR", "route": "/dash/cpr",
                "count": len(fresh) or len(r), "as_of": cpr_date,
                "top": [{"symbol": x["symbol"],
                         "note": ("bull-U" + (" · confirmed" if x["confirmed"] else "")
                                  + (f" · {x['cp']*100:.0f}%ile" if x["cp"] is not None else ""))}
                        for x in r[:5]],
                "health": _staleness(cpr_date)})

    # 5. Strength · RS — relative-strength leaders vs the broad market
    if sig_date:
        r = _rows(
            f"""SELECT s.symbol, s.rs_rank, s.rs_vs_broad_trend_state st
                FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                WHERE s.trade_date=? AND s.rs_rank IS NOT NULL AND {_LIQ}
                ORDER BY s.rs_rank DESC LIMIT 600""", (sig_date,))
        if r is not None:
            lead = [x for x in r if (x["rs_rank"] or 0) >= 80]
            out.append({
                "key": "leaders", "label": "Strength · RS", "route": "/dash/leaders",
                "count": len(lead), "as_of": sig_date,
                "top": [{"symbol": x["symbol"],
                         "note": f"RS {x['rs_rank']}" + (f" · {x['st']}" if x["st"] else "")}
                        for x in r[:5]],
                "health": _staleness(sig_date)})

    # 6. Credibility · CCI — management credibility from concalls (top tier)
    cci_asof = _latest(conn, "concall_scores", "as_of_period")
    r = _rows(
        """SELECT s.symbol, s.composite_score cs, s.tier, s.credibility_trend tr
           FROM concall_scores s
           JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x
             ON x.symbol=s.symbol AND x.m=s.last_updated
           ORDER BY COALESCE(s.composite_score,0) DESC LIMIT 600""")
    if r is not None:
        top_tier = [x for x in r if (x["tier"] or "") in ("A+", "A")]
        out.append({
            "key": "concalls", "label": "Credibility · CCI", "route": "/dash/concalls",
            "count": len(top_tier), "as_of": cci_asof,
            "top": [{"symbol": x["symbol"],
                     "note": (f"{x['tier'] or '—'} · {x['cs']:.0f}" if x["cs"] is not None
                              else (x["tier"] or "—"))}
                    for x in r[:5]],
            "health": _staleness(cci_asof) if r else "empty"})

    # 7-9. Compute-on-read lenses (Wolfe / Growth-intent / Launchpad). We do NOT
    # recompute a whole-universe scan on a dashboard read (the pre-compute doctrine);
    # they show as link cards until Lane C's strategy_registry supplies their counts.
    out.append({"key": "wolfe", "label": "Wolfe · Scan", "route": "/dash/wolfe/scan",
                "count": None, "as_of": None, "top": [], "health": "link"})
    out.append({"key": "growth", "label": "Growth-intent", "route": "/dash/growth",
                "count": None, "as_of": None, "top": [], "health": "link"})
    out.append({"key": "launchpad", "label": "Launchpad", "route": "/dash/launchpad",
                "count": None, "as_of": None, "top": [], "health": "link"})
    return out


# The full strategy catalog (label, route) — the Strategies altitude, in order.
# Used to AUGMENT whatever summary() returns so NO strategy is missing from the
# at-a-glance board even if the registry doesn't (yet) cover it. Dedup is by route.
_CATALOG = [
    ("Conviction", "/dash/conviction"),
    ("Positioning", "/dash/stocks"),
    ("Accumulation · MEP", "/dash/mep"),
    ("Structure · CPR", "/dash/cpr"),
    ("Strength · RS", "/dash/leaders"),
    ("Credibility · CCI", "/dash/concalls"),
    ("Growth-intent", "/dash/growth"),
    ("Wolfe · Scan", "/dash/wolfe/scan"),
    ("Launchpad", "/dash/launchpad"),
]


def _augment_catalog(rows: list[dict]) -> list[dict]:
    """Append link-only cards for any catalog strategy the registry/fallback didn't
    return (matched by route), so the board always shows the COMPLETE strategy set."""
    covered = {(_clean_route(r.get("route"))) for r in rows}
    for label, route in _CATALOG:
        if _clean_route(route) not in covered:
            rows.append({"key": route.rsplit("/", 1)[-1], "label": label,
                         "route": route, "count": None, "as_of": None,
                         "top": [], "health": "link"})
    return rows


def _clean_route(route) -> str:
    return (route or "").rstrip("/").lower()


def summary(conn) -> list[dict]:
    """Prefer Lane C's strategy_registry.summary(); fall back to the in-module
    derivation of the same shape. Either way: precomputed reads only."""
    rows = None
    try:
        from src.automation import strategy_registry as REG  # Lane C, optional
        rows = REG.summary(conn)
    except Exception as e:  # noqa: BLE001 — registry optional; fall back cleanly
        log.info("strategy_registry not used (%s); using fallback", e)
    if not rows:
        rows = _fallback_summary(conn)
    return _augment_catalog(list(rows))


# ── render ───────────────────────────────────────────────────────────────────
_HEALTH_PILL = {
    "ok": ("Fresh", "up"), "stale": ("Stale", "warn"),
    "empty": ("No data", "neutral"), "link": ("Live page", "acc"),
}


def _card(row: dict) -> str:
    health = row.get("health") or "empty"
    htext, hkind = _HEALTH_PILL.get(health, ("—", "neutral"))
    count = row.get("count")
    count_str = f"{count:,}" if isinstance(count, int) else "—"
    as_of = row.get("as_of")
    as_of_str = (f"as of {str(as_of)[:10]}" if as_of else "—")
    route = row.get("route") or "#"
    label = row.get("label") or row.get("key") or "Strategy"

    # top names — drop placeholder/empty symbols (e.g. an on-demand lens like Wolfe)
    tops = [t for t in (row.get("top") or [])
            if (t.get("symbol") or "").strip() not in ("", "—", "-")]
    if tops:
        lis = "".join(
            f'<a class="st-name" href="/dash/stock?sym={K.esc(t.get("symbol",""))}">'
            f'<span class="sym">{K.esc(t.get("symbol",""))}</span>'
            f'<span class="note">{K.esc(t.get("note",""))}</span></a>'
            for t in tops[:5])
        names = f'<div class="st-names">{lis}</div>'
    else:
        # surface a descriptive note if the lens provided one (on-demand strategies)
        hint = ""
        for t in (row.get("top") or []):
            if t.get("note"):
                hint = t["note"]
                break
        if not hint:
            hint = ("Open the lens for live names →" if health in ("link", "ok")
                    else "No current names")
        names = f'<div class="st-empty">{K.esc(hint)}</div>'

    head = (
        f'<div class="st-head">'
        f'<div class="st-count num">{count_str}</div>'
        f'<div class="st-meta"><div class="st-title">{K.esc(label)}</div>'
        f'<div class="st-sub">{K.esc(as_of_str)}</div></div>'
        f'{K.pill(htext, hkind)}</div>')

    foot = f'<a class="st-open" href="{K.esc(route)}">Open {K.esc(label)} →</a>'
    return f'<div class="st-card">{head}{names}{foot}</div>'


_PAGE_CSS = """<style>
.st-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px}
.st-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);
  padding:15px 16px;box-shadow:var(--glass);display:flex;flex-direction:column;gap:11px;
  transition:var(--t);min-height:172px}
.st-card:hover{border-color:var(--line-2);box-shadow:var(--glass),var(--shadow)}
.st-head{display:flex;align-items:center;gap:12px}
.st-count{font-size:30px;font-weight:600;line-height:1;color:var(--ink);min-width:54px}
.st-meta{flex:1;min-width:0}
.st-title{font-size:14px;font-weight:600;color:var(--ink)}
.st-sub{font-size:11px;color:var(--ink-3);margin-top:2px}
.st-names{display:flex;flex-direction:column;gap:3px;flex:1}
.st-name{display:flex;justify-content:space-between;gap:10px;padding:4px 7px;border-radius:7px;
  font-size:12.5px;transition:var(--t)}
.st-name:hover{background:var(--bg-3)}
.st-name .sym{color:var(--ink);font-weight:600}
.st-name .note{color:var(--ink-3);font-variant-numeric:tabular-nums;font-family:var(--mono);font-size:11.5px;white-space:nowrap}
.st-empty{font-size:12px;color:var(--ink-3);flex:1;display:flex;align-items:center}
.st-open{font-size:12px;color:var(--accent);font-weight:500;margin-top:auto}
.st-strip{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.st-strip .uk-card{flex:1;min-width:150px}
</style>"""


@router.get("/dash/strategist", response_class=HTMLResponse)
def dash_strategist() -> HTMLResponse:
    rows: list[dict] = []
    sig_date = mep_date = None
    universe = None
    try:
        with get_conn() as conn:
            rows = summary(conn)
            sig_date = _latest(conn, "stock_signals")
            mep_date = _latest(conn, "mep_signals")
            try:
                u = conn.execute("SELECT COUNT(*) n FROM nse_equity_list").fetchone()
                universe = u["n"] if u else None
            except Exception:  # noqa: BLE001
                universe = None
    except Exception as e:  # noqa: BLE001
        log.warning("strategist page query failed: %s", e)

    # at-a-glance strip
    fresh_n = sum(1 for r in rows if (r.get("health") == "ok"))
    measured = [r for r in rows if isinstance(r.get("count"), int)]
    strip = (
        '<div class="st-strip">'
        + K.card(K.stat("Strategies", str(len(rows)),
                        f"{fresh_n} fresh · {len(measured)} measured", "up"))
        + K.card(K.stat("Universe", f"{universe:,}" if universe else "—", "NSE equities"))
        + K.card(K.stat("Bhav as of", str(sig_date)[:10] if sig_date else "—",
                        "latest signal date"))
        + K.card(K.stat("MEP as of", str(mep_date)[:10] if mep_date else "—",
                        "accumulation phase"))
        + '</div>')

    cards = "".join(_card(r) for r in rows) or (
        '<div class="uk-card">No strategies available yet. '
        'Check the precomputed tables on this host.</div>')

    head = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        '<h1 class="uk-h1">Strategist</h1>'
        + K.badge("every strategy · at a glance · precomputed") + '</div>'
        '<div class="sec" style="margin-bottom:16px">Each strategy\'s current read — '
        'count, freshness, top names — one card per lens. Click any card to open its deep page.</div>')

    body = _PAGE_CSS + head + strip + f'<div class="st-grid">{cards}</div>'
    return HTMLResponse(K.shell("Strategist · patearn", body,
                                active="strategies", sub=_sub("strategist"),
                                nav_html=_nav_html("strategist")))


def wire(app):
    """Idempotent self-mount (used if main.py prefers a wire() hook over include)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/strategist" not in paths:
            app.include_router(router)
    except Exception as e:  # noqa: BLE001
        log.warning("strategist wire skipped: %s", e)
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    r = c.get("/dash/strategist")
    assert r.status_code == 200, r.status_code
    assert "Strategist" in r.text
    assert "st-grid" in r.text
    print("strategist_view selftest OK — /dash/strategist 200, grid renders")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
