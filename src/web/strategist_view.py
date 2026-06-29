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
from urllib.parse import quote_plus

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
/* workbench: toolbar + section toggles + alerts + boards */
.wb-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 14px}
.wb-tog{font:inherit;font-size:12px;cursor:pointer;border:1px solid var(--line-2);background:var(--bg-1);
  color:var(--ink-3);border-radius:8px;padding:5px 11px}
.wb-tog.on{background:var(--accent-dim);color:var(--accent);border-color:transparent}
.wb-tog:hover{color:var(--ink)}
.wb-sec-lbl{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink-3);margin:18px 0 9px;font-weight:600}
.wb-alerts{background:var(--bg-2);border:1px solid var(--line);border-left:2px solid var(--accent-cy);
  border-radius:var(--r);padding:13px 16px;margin-bottom:8px}
.wb-alerts .ah{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:7px}
.wb-alerts .ah b{font-size:15px}
.wb-new{display:inline-flex;align-items:center;gap:5px;background:var(--up-dim);color:var(--up);
  border-radius:20px;padding:2px 9px;font-size:11.5px;font-weight:600}
.wb-seen{font:inherit;font-size:11.5px;cursor:pointer;border:1px solid var(--line-2);background:var(--bg-1);
  color:var(--ink-3);border-radius:7px;padding:3px 9px;margin-left:auto}
.wb-seen:hover{border-color:var(--accent);color:var(--ink)}
.bd-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);padding:13px 15px;
  display:flex;flex-direction:column;gap:7px}
.bd-card .bn{font-weight:600;font-size:13.5px;color:var(--ink)}
.bd-card .bq{font-size:11.5px;color:var(--ink-3);flex:1}
.bd-card .br{display:flex;gap:10px;align-items:center}
.bd-card .br a{font-size:12px;color:var(--accent)}
.bd-del{margin-left:auto;font:inherit;font-size:11px;color:var(--ink-3);background:none;border:none;cursor:pointer}
.bd-del:hover{color:var(--down)}
.hide-alerts .wb-alerts-sec,.hide-strategies .wb-strategies-sec,.hide-boards .wb-boards-sec,
.hide-credibility .wb-cci-sec,.hide-changed .wb-changed-sec{display:none}
.wc-row{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid var(--line)}
.wc-row:last-child{border-bottom:none}
.wc-strat{font-size:13px;font-weight:600;color:var(--ink);min-width:150px}
.wc-bits{flex:1;display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink-3)}
.wc-up{color:var(--up);font-weight:600}
.wc-dn{color:var(--down);font-weight:600}
.wc-chip{display:inline-block;padding:1px 7px;margin:1px;border-radius:6px;font-size:11.5px;font-weight:600}
.wc-new{background:var(--up-dim);color:var(--up)}
.wc-drop{background:var(--down-dim,rgba(248,81,73,.12));color:var(--down)}
.cci-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:6px}
.cci-kv{background:var(--bg-1);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.cci-n{font-size:24px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
.cci-l{font-size:12px;color:var(--ink);font-weight:600;margin-top:4px}
.cci-s{font-size:10.5px;color:var(--ink-3);margin-top:2px}
</style>"""


def _alerts_strip(conn) -> str:
    """The proactive confluence-alerts strip: names that NEWLY entered the confluence
    (credible ∩ accumulated) since the last snapshot. Descriptive; opt-in 'mark seen'."""
    try:
        from src.pat import alerts as A
        a = A.compute(conn)
    except Exception:  # noqa: BLE001
        return ""
    cnt = a.get("count", 0)
    new = a.get("new", [])
    dropped = a.get("dropped", [])
    asof = a.get("as_of")

    def _chips(syms, bg="var(--bg-3)"):
        return " ".join(
            f'<a class="st-name" href="/dash/stock?sym={K.esc(s)}" '
            f'style="display:inline-flex;padding:3px 9px;background:{bg};border-radius:7px;margin:2px">'
            f'<span class="sym">{K.esc(s)}</span></a>' for s in syms)

    if a.get("first_run"):
        body = (f'<b>{cnt}</b> names currently in confluence (credible ∩ accumulated). '
                'Baseline set — I\'ll flag new entrants from here.')
        badge = '<span class="wb-new">baseline</span>'
    elif new:
        body = (f'<b>{len(new)}</b> newly aligned since {K.esc(str(a.get("baseline_at"))[:10])} '
                f'· {cnt} in confluence now:</div><div style="margin:4px 0">{_chips(new[:14])}')
        badge = f'<span class="wb-new">▲ {len(new)} new</span>'
    else:
        body = (f'<b>{cnt}</b> names in confluence (credible ∩ accumulated) · '
                'no new entrants since the last check.')
        badge = '<span class="wb-new" style="background:var(--bg-3);color:var(--ink-2)">no change</span>'

    # F3-8 polish: surface names that DROPPED OUT (left confluence — a descriptive
    # signal, not a sell call) + the WATCHLIST-alignment read (opt-in: only if a
    # watchlist exists and overlaps confluence).
    extra = ""
    if dropped and not a.get("first_run"):
        extra += (f'<div class="sec" style="margin-top:6px;color:var(--ink-2);font-size:12px">'
                  f'▽ <b>{len(dropped)}</b> dropped out since the last check '
                  f'(no longer credible ∩ accumulated — descriptive, not a sell call): '
                  f'{_chips(dropped[:12], bg="var(--bg-2)")}</div>')
    try:
        from src.pat import alerts as _A
        wl = _A.watchlist_alignment(conn)
    except Exception:  # noqa: BLE001
        wl = []
    if wl:
        wsyms = [w["symbol"] for w in wl][:14]
        extra += (f'<div class="sec" style="margin-top:6px;font-size:12px">'
                  f'★ <b>{len(wsyms)}</b> of your watchlist '
                  f'{"name is" if len(wsyms) == 1 else "names are"} in confluence right now: '
                  f'{_chips(wsyms)}</div>')
    return (
        '<div class="wb-alerts wb-alerts-sec">'
        f'<div class="ah">{badge}<b>Confluence alerts</b>'
        f'<span class="mut" style="font-size:11px">as of {K.esc(str(asof)[:10] if asof else "—")} · descriptive, not a buy call</span>'
        '<button class="wb-seen" onclick="wbMarkSeen(this)">↻ mark seen</button></div>'
        f'<div class="sec">{body}</div>'
        f'{extra}'
        '</div>')


def _what_changed(conn, rows) -> str:
    """The 'what changed since last refresh' read — per strategy, the names that NEWLY
    entered its top set + the ones that DROPPED, diffed against the last board view via
    alerts.diff_set (namespaced 'strat:<key>'). Makes the board a LIVING watch, not a
    static snapshot. Descriptive (a membership change, never a buy/sell call). Empty on
    the very first view (every strategy baselines silently) or with no rows."""
    if conn is None or not rows:
        return ""
    try:
        from src.pat import alerts as A
    except Exception:  # noqa: BLE001
        return ""
    items = []
    any_delta = False
    for r in rows:
        key = (r.get("key") or "").strip()
        label = r.get("label") or key or "Strategy"
        route = _clean_route(r.get("route"))
        tops = [(t.get("symbol") or "").strip() for t in (r.get("top") or [])
                if (t.get("symbol") or "").strip() not in ("", "—", "-")]
        if not key or not tops:
            continue
        d = A.diff_set(conn, f"strat:{key}", tops)
        new, dropped = d.get("new", []), d.get("dropped", [])
        if d.get("first_run") or (not new and not dropped):
            continue                       # nothing to show (baseline or unchanged)
        any_delta = True

        def _chips(syms, cls):
            return " ".join(
                f'<a class="wc-chip {cls}" href="/dash/stock?sym={K.esc(s)}">{K.esc(s)}</a>'
                for s in syms[:10])
        bits = []
        if new:
            bits.append(f'<span class="wc-up">▲ {len(new)} new</span> {_chips(new, "wc-new")}')
        if dropped:
            bits.append(f'<span class="wc-dn">▽ {len(dropped)} dropped</span> {_chips(dropped, "wc-drop")}')
        items.append(
            f'<div class="wc-row"><a class="wc-strat" href="{K.esc(route)}">{K.esc(label)}</a>'
            f'<div class="wc-bits">{" · ".join(bits)}</div></div>')
    if not any_delta:
        return ('<div class="wb-changed-sec"><div class="wb-sec-lbl">What changed</div>'
                '<div class="wb-alerts" style="border-left-color:var(--ink-3)">'
                '<div class="sec" style="font-size:12.5px">No membership changes since your last '
                'view of the board — every strategy\'s top set is unchanged. (Descriptive.)</div>'
                '</div></div>')
    return ('<div class="wb-changed-sec"><div class="wb-sec-lbl">What changed '
            '<span class="mut" style="text-transform:none;font-weight:400">'
            '(since your last board view · descriptive)</span></div>'
            '<div class="wb-alerts" style="border-left-color:var(--accent-cy)">'
            + "".join(items) + '</div></div>')


def _cci_tile(conn) -> str:
    """The Credibility RRG + divergence tile (CCI Phase 3, `credibility_rrg`, 806
    names) — an at-a-glance DESCRIPTIVE read of management-credibility level×momentum
    and the credibility÷price divergence. Surfaces the §C-falsified map as a research
    lens (NEVER a buy/sell ranking; the 1/806-delisted survivorship limit + the
    no-return-edge verdict stand). Empty if cci_rrg isn't built on this host."""
    try:
        from src.automation import cci_rrg
        if not conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='credibility_rrg'"
        ).fetchone():
            return ""
        s = cci_rrg.summary(conn)
    except Exception as e:  # noqa: BLE001
        log.warning("cci tile skipped: %s", e)
        return ""
    n = s.get("n", 0)
    if not n:
        return ""
    quad = s.get("by_quadrant", {}) or {}
    div = s.get("by_divergence", {}) or {}
    asof = _latest(conn, "credibility_rrg", "as_of_period") or _latest(conn, "concall_scores", "last_updated")

    # the four headline reads (proven&improving = best evidence; low&deteriorating = avoid tape)
    def _q(*keys):
        return sum(int(quad.get(k, 0)) for k in keys)
    proven_up = _q("PROVEN_IMPROVING")
    proven_slip = _q("PROVEN_SLIPPING")
    low_det = _q("LOW_DETERIORATING", "UNPROVEN_DETERIORATING")
    pos_div = int(div.get("POSITIVE_DIVERGENCE", 0))
    neg_div = int(div.get("NEGATIVE_DIVERGENCE", 0))

    def _kv(label, val, sub, kind="neutral"):
        col = {"up": "var(--up)", "down": "var(--down)", "cy": "var(--accent-cy)"}.get(kind, "var(--ink)")
        return (f'<div class="cci-kv"><div class="cci-n" style="color:{col}">{val}</div>'
                f'<div class="cci-l">{K.esc(label)}</div><div class="cci-s">{K.esc(sub)}</div></div>')

    grid = (
        '<div class="cci-grid">'
        + _kv("Proven & improving", proven_up, "high-evidence track record", "up")
        + _kv("Proven but slipping", proven_slip, "watch — momentum fading", "neutral")
        + _kv("Low & deteriorating", low_det, "avoid tape (descriptive)", "down")
        + _kv("Positive divergence", pos_div, "credibility ↑ vs price flat/down", "cy")
        + _kv("Negative divergence", neg_div, "credibility ↓ vs price up", "down")
        + '</div>')
    return (
        '<div class="wb-cci-sec"><div class="wb-sec-lbl">Credibility RRG · divergence '
        '<span class="mut" style="text-transform:none;font-weight:400">(CCI Phase 3 · descriptive map)</span></div>'
        '<div class="wb-alerts" style="border-left-color:var(--accent)">'
        f'<div class="ah"><b>Management credibility — level × momentum</b>'
        f'<span class="mut" style="font-size:11px">{n} names · as of {K.esc(str(asof)[:10] if asof else "—")} · '
        'a research map, NOT a ranked signal (no validated return edge — §C falsified; '
        'survivorship-limited)</span></div>'
        f'{grid}'
        '<div class="sec" style="margin-top:8px;font-size:12px">'
        '<a class="st-open" href="/dash/pat?flow=credibility">credibility leaders →</a> &nbsp; '
        '<a class="st-open" href="/dash/pat?flow=deterioration">deterioration tape →</a> &nbsp; '
        '<a class="st-open" href="/dash/coverage">methodology · coverage →</a>'
        '</div></div></div>')


def _boards_section(conn) -> str:
    """Saved NL-query boards as workbench cards (the 'configurable' part — the user
    pins the views they care about; each reloads its Pat answer)."""
    try:
        from src.pat import boards as B
        items = B.list_boards(kind="pat", limit=40)
    except Exception:  # noqa: BLE001
        items = []
    if not items:
        inner = ('<div class="st-empty" style="padding:12px">No saved boards yet. Ask Pat a '
                 'question and tap “★ Save as board” to pin it here.</div>')
    else:
        cards = []
        for b in items:
            href = ("/dash/pat?q=" + quote_plus(b["query"])) if b.get("query") else \
                   ("/dash/pat?flow=" + quote_plus(b.get("flow") or ""))
            cards.append(
                '<div class="bd-card">'
                f'<div class="bn">★ {K.esc(b["name"])}</div>'
                f'<div class="bq">{K.esc(b.get("query") or b.get("flow") or "")}</div>'
                f'<div class="br"><a href="{K.esc(href)}">open →</a>'
                f'<button class="bd-del" data-name="{K.esc(b["name"])}" onclick="wbDelBoard(this)">delete</button>'
                '</div></div>')
        inner = f'<div class="st-grid">{"".join(cards)}</div>'
    return ('<div class="wb-boards-sec"><div class="wb-sec-lbl">Your boards</div>'
            + '<a class="st-open" href="/dash/pat" style="margin:0 0 9px;display:inline-block">'
            '+ ask Pat &amp; save a new board →</a>' + inner + '</div>')


_WB_JS = """<script>(function(){
var KEY='wb_hidden_v1';
function gh(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return {}}}
function sh(h){localStorage.setItem(KEY,JSON.stringify(h))}
function apply(){var h=gh(),wrap=document.getElementById('wbWrap');if(!wrap)return;
  ['alerts','changed','credibility','strategies','boards'].forEach(function(s){
    wrap.classList.toggle('hide-'+s,!!h[s]);
    var b=document.querySelector('.wb-tog[data-s="'+s+'"]');if(b)b.classList.toggle('on',!h[s]);});}
document.querySelectorAll('.wb-tog[data-s]').forEach(function(b){
  b.addEventListener('click',function(){var s=b.getAttribute('data-s'),h=gh();h[s]=!h[s];sh(h);apply();});});
apply();
window.wbMarkSeen=function(btn){btn.disabled=true;btn.textContent='…';
  fetch('/pat/alerts/seen',{method:'POST'}).then(function(r){return r.json();})
  .then(function(j){btn.textContent=j.ok?'✓ seen':'failed';setTimeout(function(){location.reload();},500);})
  .catch(function(){btn.textContent='failed';btn.disabled=false;});};
window.wbDelBoard=function(btn){var n=btn.getAttribute('data-name');if(!n||!confirm('Delete board "'+n+'"?'))return;
  fetch('/pat/board/delete',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({name:n,kind:'pat'})}).then(function(){location.reload();});};
})();</script>"""


@router.get("/dash/strategist", response_class=HTMLResponse)
def dash_strategist(fmt: str = "") -> HTMLResponse:
    from fastapi.responses import PlainTextResponse
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

    # CSV export of the strategy board (the workbench's "export" affordance).
    if (fmt or "").lower() == "csv":
        lines = ["strategy,route,count,as_of,health,top_names"]
        for r in rows:
            tops = " ".join((t.get("symbol") or "") for t in (r.get("top") or [])[:5]).strip()
            cnt = r.get("count")
            lines.append(",".join('"%s"' % str(x).replace('"', '""') for x in [
                r.get("label") or r.get("key") or "", r.get("route") or "",
                cnt if isinstance(cnt, int) else "", r.get("as_of") or "",
                r.get("health") or "", tops]))
        return PlainTextResponse("\n".join(lines), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=strategist.csv"})

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

    # alerts + what-changed + credibility tile + boards (workbench sections) — best-effort
    alerts_html = changed_html = cci_html = boards_html = ""
    try:
        with get_conn() as conn:
            alerts_html = _alerts_strip(conn)
            changed_html = _what_changed(conn, rows)
            cci_html = _cci_tile(conn)
            boards_html = _boards_section(conn)
    except Exception as e:  # noqa: BLE001
        log.warning("workbench sections skipped: %s", e)

    head = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        '<h1 class="uk-h1">Strategist · Workbench</h1>'
        + K.badge("every strategy + your boards + alerts · precomputed") + '</div>'
        '<div class="sec" style="margin-bottom:14px">Your configurable board — every '
        'strategy\'s current read, the names that newly aligned, and the queries you\'ve '
        'pinned. Click any card to open its deep page. Descriptive, never a buy call.</div>')

    toolbar = (
        '<div class="wb-bar">'
        '<button class="wb-tog on" data-s="alerts">Alerts</button>'
        '<button class="wb-tog on" data-s="changed">What changed</button>'
        '<button class="wb-tog on" data-s="credibility">Credibility</button>'
        '<button class="wb-tog on" data-s="strategies">Strategies</button>'
        '<button class="wb-tog on" data-s="boards">Boards</button>'
        '<a class="wb-tog" href="/dash/strategist?fmt=csv" style="margin-left:auto">⬇ CSV</a>'
        '</div>')

    strategies_section = ('<div class="wb-strategies-sec">'
                          '<div class="wb-sec-lbl">Strategies</div>'
                          f'<div class="st-grid">{cards}</div></div>')

    body = (_PAGE_CSS + head + strip + toolbar
            + f'<div id="wbWrap">{alerts_html}{changed_html}{cci_html}{strategies_section}{boards_html}</div>'
            + _WB_JS)
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
    assert "Strategist" in r.text and "st-grid" in r.text
    assert "wb-bar" in r.text and "Confluence alerts" in r.text, "workbench sections missing"
    # exercise the NON-empty boards path (the quote_plus-class bug hid there): seed a
    # board, render, assert it appears + the page still 200s, then clean up.
    try:
        from src.pat import boards as _B
        _B.save("__selftest_board__", query="RS leaders that are credible", flow="rs")
        r2 = c.get("/dash/strategist")
        assert r2.status_code == 200 and "__selftest_board__" in r2.text, "boards section render failed"
        assert c.get("/dash/strategist?fmt=csv").status_code == 200, "CSV export failed"
    finally:
        try:
            from src.pat import boards as _B
            _B.delete("__selftest_board__")
        except Exception:
            pass
    print("strategist_view selftest OK — workbench 200, alerts + boards (non-empty) + CSV render")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
