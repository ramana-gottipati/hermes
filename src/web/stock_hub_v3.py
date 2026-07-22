"""stock_hub_v3.py — /dash/preview/stock, the M4 evidence-scroll stock hub. ADDITIVE, opt-in.

The spec's §2 anatomy: breadcrumb + identity strip → the digest (tiles-as-anchors + the
deterministic narrative + fired-lens badges) → sticky section index → the sections (open
inline or server-expanded via ?section=; spec §6) → ONE related strip (≤5) — beside the
Context rail (news · next results · corp actions · peers · CCI chip) and above the M3 dock
(symbol-filtered). Shell nav contract per requirement #0 (dest bar · Stocks rail · crumbs).

URL state: ?sym= (required) · ?section=<key|all> (expansion) — a shared URL reproduces the
view. Unknown symbol → the did-you-mean recovery, never a dead end.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _uq

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web import hub_sections_v3 as H
from src.web import news_dock, shell_v3, term_chip, ui_components_v3 as C

router = APIRouter()


def _e(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _identity(core: dict) -> str:
    """Spec §2.1: symbol + name + sector/theme chips + CMP with day change (value-contract
    colors) + the provenance line."""
    sym, bar, prev, sig = core["sym"], core.get("bar"), core.get("prev"), core.get("sig")
    date = str(bar["trade_date"])[:10] if bar is not None else "no tape data"
    cmp_html = ""
    if bar is not None:
        chg, tone = "", ""
        try:
            if prev is not None and prev["close"]:
                pct = (bar["close"] - prev["close"]) / prev["close"] * 100
                chg = " <i class=\"" + ("up" if pct >= 0 else "down") + "\">" \
                    + ("+" if pct >= 0 else "") + format(pct, ".2f") + "%</i>"
        except Exception:
            pass
        cmp_html = ('<span class="cmp pv3-num">₹' + format(bar["close"], ",.2f") + chg + "</span>")
    chips = []
    try:
        if sig is not None and sig["primary_sector"]:
            chips.append('<span class="hub-chip">' + _e(sig["primary_sector"]) + "</span>")
    except Exception:
        pass
    for t in (core.get("themes") or [])[:4]:
        chips.append('<span class="hub-chip thm">' + _e(t) + "</span>")
    return ('<div class="hub-id"><h1>' + _e(sym) + "</h1>"
            + ('<span class="nm">' + _e(core.get("name")) + "</span>" if core.get("name") else "")
            + cmp_html
            + '<span class="prov">as of ' + _e(date) + " · NSE bhav copy</span></div>"
            + ('<div class="hub-chips">' + "".join(chips) + "</div>" if chips else "")
            + '<style>.hub-id{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-bottom:4px}'
            ".hub-id h1{margin:0;font-size:var(--t-2xl)}"
            ".hub-id .nm{color:var(--ink-2)}"
            ".hub-id .cmp{font-size:var(--t-lg);font-weight:600}"
            ".hub-id .cmp i{font-style:normal;font-size:var(--t-sm)}"
            ".hub-id .cmp i.up{color:var(--up)} .hub-id .cmp i.down{color:var(--down)}"
            ".hub-id .prov{color:var(--ink-3);font-size:var(--t-xs);margin-left:auto}"
            ".hub-chips{margin-bottom:8px}"
            ".hub-chip{display:inline-block;background:var(--bg-3);border:1px solid var(--line-2);"
            "border-radius:var(--r-pill);padding:2px 10px;font-size:var(--t-xs);"
            "color:var(--ink-2);margin-right:6px}"
            ".hub-chip.thm{background:var(--accent-dim);color:var(--accent);border-color:var(--accent)}"
            "</style>")


def _section_index(core: dict) -> str:
    out = ['<nav class="hub-idx" aria-label="Sections">']
    for key, title in H.SECTIONS:
        if key == "fno" and not core.get("has_fno"):
            continue
        out.append('<a href="#' + key + '">' + _e(title) + "</a>")
    out.append("</nav>")
    return "".join(out)


def _related(sym: str) -> str:
    """ONE related block, ≤5, fixed position (§D)."""
    q = _uq.quote(sym)
    links = [("Compare " + sym + " with peers", "/dash/compare?sym=" + q),
             ("Screen the full universe", "/dash/screen2"),
             (sym + " relative-strength history", "/dash/momentum?sym=" + q),
             ("The validation record", "/dash/testing"),
             ("How to read this page", "/dash/reading-guide")]
    inner = "<br>".join(C.evidence_link(h, l) for l, h in links[:5])
    return C.section("Related") + C.card("", "<p>" + inner + "</p>")


def _rail(core: dict) -> str:
    sym = core["sym"]
    cards = []
    # news timeline (bounded, existing read)
    try:
        from src.web.news_view import render_stock_timeline
        cards.append(C.card("News for " + sym, render_stock_timeline(sym, limit=10)))
    except Exception:
        pass
    # next results date
    try:
        from src.automation.results_calendar import upcoming_results
        mine = [r for r in upcoming_results(days=45) if str(r["symbol"]).upper() == sym][:1]
        if mine:
            cards.append(C.card("Next results",
                                "<p>" + _e(str(mine[0]["meeting_date"])[:10]) + " · "
                                + _e(mine[0]["purpose"] or "board meeting") + "</p>"))
    except Exception:
        pass
    # upcoming corp actions
    try:
        from src.automation import corp_actions as CA
        with get_conn() as conn:
            rows, _asof = CA.upcoming(conn, days=45)
        mine = [r for r in rows if str(r.get("symbol", "")).upper() == sym][:4]
        if mine:
            body = "".join("<p>ex " + _e(str(r.get("ex_date"))[:10]) + " · "
                           + _e(str(r.get("action_type", "")).replace("_", " ").lower()) + "</p>"
                           for r in mine)
            cards.append(C.card("Corporate actions", body))
    except Exception:
        pass
    # peers (the verified /dash/api/peers read, inlined)
    try:
        from src.web.dashboard import _narrow_sector, _sector_symbols
        with get_conn() as conn:
            sec = _narrow_sector(conn, sym)
            peers = [s for s in _sector_symbols(conn, sec) if s and s != sym][:8] if sec else []
        if peers:
            body = " · ".join('<a href="/dash/preview/stock?sym=' + _uq.quote(p) + '">' + _e(p)
                              + "</a>" for p in peers)
            body += ('<p style="margin-top:8px">' + C.evidence_link(
                "/dash/compare?sym=" + _uq.quote(sym) + "," + _uq.quote(peers[0]),
                "Compare with " + peers[0]) + "</p>")
            cards.append(C.card("Peers (" + _e(sec or "") + ")", body))
    except Exception:
        pass
    if core.get("cci") is not None:
        cards.append(C.card("Credibility", "<p>" + term_chip.chip("cci", sym=sym) + "</p>"))
    return "".join(cards) if cards else C.card("Context", "<p>No context data yet.</p>")


def _miss(sym: str) -> str:
    body = "<p>No tape data for <b>" + _e(sym) + "</b>.</p>"
    try:
        from src.web.symbol_search import did_you_mean_html
        body += did_you_mean_html(sym)
    except Exception:
        pass
    body += "<p>" + C.evidence_link("/dash/screen2", "Browse the screener instead") + "</p>"
    return C.card("Symbol not found", body)


@router.get("/dash/preview/stock", response_class=HTMLResponse, include_in_schema=False)
def stock_hub(sym: str = "", section: str = "", ch: str = "", cmp: str = "",
              range: str = "") -> HTMLResponse:
    """URL state (spec §6): sym · section · ch (dock channel) · cmp (the chart fork reads it
    client-side from the URL) · range ('' = the 3y bounded island, 'max' = full history)."""
    sym = str(sym or "").strip().upper()[:20]
    ch = str(ch or "").strip().lower()[:12]
    cmp = str(cmp or "").strip().upper()[:96]
    qs_extra = ("&ch=" + _uq.quote(ch) if ch else "") + ("&cmp=" + _uq.quote(cmp) if cmp else "")
    head = C.css() + term_chip.assets() + news_dock.css() + H.css()
    crumbs = [("Home", "/dash/preview"), ("Stocks", "/dash/preview"), (sym or "…", "")]
    nav_items = [("Screener (classic)", "/dash/screen2", False),
                 ("Themes (classic)", "/dash/themes", False),
                 ((sym + " dossier") if sym else "Dossier", "#", True)]
    if not sym:
        focus = C.card("Pick a stock", '<form method="get" action="/dash/preview/stock">'
                       '<input name="sym" placeholder="Symbol, e.g. TCS" '
                       'style="text-transform:uppercase"> '
                       '<button class="pv3-btn" type="submit">Open</button></form>')
        return HTMLResponse(shell_v3.shell("Stock hub", focus, "", head, "",
                                           dest="stocks", crumbs=crumbs[:2],
                                           nav_title="Stocks", nav_items=nav_items[:2]))
    core = H.load_core(sym)
    core["rng"] = "max" if range == "max" else ""
    if core.get("bar") is None and core.get("sig") is None:
        return HTMLResponse(shell_v3.shell(sym, _miss(sym), "", head, "", dest="stocks",
                                           crumbs=crumbs, nav_title="Stocks",
                                           nav_items=nav_items))
    open_secs = set(H.DEFAULT_OPEN)
    if section == "all":
        open_secs = {k for k, _t in H.SECTIONS}
    elif section in {k for k, _t in H.SECTIONS}:
        open_secs.add(section)
    focus = (_identity(core)
             + H.digest_tiles(core)
             + H.narrative(core)
             + H.fired_badges(core)
             + C.fence("not_advice")
             + _section_index(core)
             + '<p class="hub-note"><a href="/dash/preview/stock?sym=' + _uq.quote(sym)
             + '&section=all' + qs_extra + '">Open every section</a> · sections open one at a '
               "time to keep this page fast.</p>"
             + H.render_sections(core, open_secs, qs_extra)
             + _related(sym))
    dock = news_dock.dock_html(ch=ch or "wire", sym=sym, base="/dash/preview/stock")
    return HTMLResponse(shell_v3.shell(sym + " · stock hub", focus, _rail(core), head, dock,
                                       dest="stocks", crumbs=crumbs, nav_title="Stocks",
                                       nav_items=nav_items))


def _selftest() -> int:
    routes = {getattr(r, "path", None) for r in router.routes}
    assert "/dash/preview/stock" in routes
    print("stock_hub_v3 selftest OK — route mounted")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
