"""src/web/home — the fresh-and-parallel v3 "Graphite Home" section (build increment i).

A completely SEPARATE, self-contained section (owner decision 2026-07-23; spec
docs/redesign-graphite-home-spec.md v1.2). Reached by direct URL + the `pvg` opt-in cookie only —
NO affordance in classic chrome, NO lens_registry entry (nav is generated from the lens registry;
adding one would drift the classic nav — deferred to cutover). Mounted by ONE additive
`v2_surfaces._ROUTER_SPECS` entry.

Isolation (machine-enforced by tests/test_home_isolation.py): this package imports NO `*_v3` /
`v3_preview` / preview render module; its CSS is scoped `:root[data-ui-g]` + `.g-*` so it can never
touch a legacy or existing-preview page, and those pages can never carry a Graphite marker.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.web.home import components as C
from src.web.home import reads, shell

router = APIRouter()

_COOKIE = "pvg"


def is_on(request: Request) -> bool:
    return request.cookies.get(_COOKIE) == "1"


@router.get("/dash/home", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request) -> HTMLResponse:
    from src.core.db import get_conn
    on = is_on(request)
    body, pat = "", ""
    try:
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            body = _compose(conn, on)
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a busy/edge DB must never 500 the home
        body = C.zone("Market pulse", "index_signals", C.empty("Today's signals haven't landed yet."))
    return HTMLResponse(shell.shell("Home", body, pat_html=pat))


@router.post("/dash/home/toggle", include_in_schema=False)
def toggle(request: Request) -> RedirectResponse:
    resp = RedirectResponse("/dash/home", status_code=303)
    if is_on(request):
        resp.delete_cookie(_COOKIE, path="/")
    else:
        resp.set_cookie(_COOKIE, "1", path="/", max_age=60 * 60 * 24 * 30, samesite="lax")
    return resp


@router.get("/dash/home/_kit", response_class=HTMLResponse, include_in_schema=False)
def kit(request: Request) -> HTMLResponse:
    """The component showcase — dev/preview-only, proves the kit renders in isolation."""
    body = (C.zone("Kit — tiles", "components", C.tile("Market mood", "72", "Constructive"))
            + C.zone("Kit — provenance", "components",
                     C.prov("index_signals", "nightly") + " " + C.prov("market_internals", "⚠ no timer", stale=True))
            + C.zone("Kit — chips", "glossary",
                     C.term_chip("Delivery size", "DVPT") + " " + C.term_chip("Composite rank", "CONVICTION")))
    return HTMLResponse(shell.shell("Component kit", body))


def _pick(live, demo_val):
    """Return (data, is_demo): the live read, or the demo fallback flagged so the zone can mark
    itself 'sample' (the real-vs-demo honesty line — a preview must look full but never pass fake
    data as primary)."""
    return (live, False) if live else (demo_val, True)


def _feeds(conn, idx, wl, wl_demo, pf, pf_demo):
    """Assemble the selectable ticker feeds (indices · watchlist · portfolio · model · movers). The
    globals-strip (Dow/Gold) is deliberately omitted — no real source exists, so it is not shown as
    live in the always-on ticker (honesty). Model is illustrative until wired to the books estate."""
    from src.web.home import demo
    ich = "".join(C.rib_chip(C._d(r).get("index_name"), C._num(C._d(r).get("close_value"), 0),
                             C._d(r).get("ret_1d_pct")) for r in (idx or [])[:6])
    feeds = [{"key": "indices", "label": "Indices", "chips": ich, "sample": False}]

    wch = C.rib_chip("Watchlist", None, None, acc=True) + "".join(
        C.rib_chip(C._d(r).get("symbol"), None, C._d(r).get("pct")) for r in (wl or [])[:8])
    feeds.append({"key": "watch", "label": "My watchlist", "chips": wch, "sample": wl_demo})

    prows = C._d(pf).get("rows") or []
    pch = C.rib_chip("Portfolio · day", None, None, acc=True) + "".join(
        C.rib_chip(C._d(r).get("symbol"),
                   (f"{float(C._d(r)['weight']):.0f}% wt" if C._d(r).get("weight") is not None else None),
                   C._d(r).get("pct")) for r in prows[:8])
    feeds.append({"key": "folio", "label": "My portfolio", "chips": pch, "sample": pf_demo})

    model = [("NESTLEIND", 0.34), ("HINDUNILVR", 0.51), ("ITC", -0.15), ("BRITANNIA", 0.88), ("DABUR", 0.27)]
    mch = C.rib_chip("Model · LowVol-Mom", None, None, acc=True) + "".join(C.rib_chip(n, None, p) for n, p in model)
    feeds.append({"key": "model", "label": "Model · LowVol-Mom", "chips": mch, "sample": True})

    mv = reads.movers(conn)
    mv, mv_demo = (mv, False) if mv else (demo.MOVERS, True)
    mv = C._d(mv)
    mch2 = C.rib_chip("Top movers", None, None, acc=True) + "".join(
        C.rib_chip(C._d(r).get("symbol"), None, C._d(r).get("pct"))
        for r in ((mv.get("gainers") or [])[:4] + (mv.get("losers") or [])[:4]))
    feeds.append({"key": "movers", "label": "Top movers", "chips": mch2, "sample": mv_demo})
    return feeds


def _compose(conn, on: bool) -> str:
    """The owner-approved SCROLL-STACK dashboard: a selectable ticker, a MAIN column (a FEATURED card
    you choose — watchlist · portfolio · index — then the always-visible Market-pulse deck · What-
    changed · News), and a RAIL (FII/DII · corporate actions · results · a go-deeper drawer · the
    preview toggle). Every card is visible as you scroll; ⋮ pins/collapses/hides. Each zone is a live
    read with a demo fallback that marks itself 'sample'."""
    from src.web.market_mood import market_mood
    from src.web.home import demo

    idx, idx_demo = _pick(reads.index_pulse(conn), demo.INDEX)
    b_in, nifty_up = reads.mood_inputs(conn)
    if b_in is None and nifty_up is None:
        b_in, nifty_up = demo.MOOD_INPUTS
    breadth, _bd = _pick(reads.breadth_latest(conn), demo.BREADTH)
    series70 = reads.index_series(conn, "NIFTY 50", 70) or demo.SERIES
    internals, _id = _pick(reads.internals_series(conn, 30), demo.INTERNALS)
    highs = reads.new_highs(conn) or demo.NEW_HIGHS
    sectors = reads.sector_heat(conn) or demo.SECTOR_HEAT
    vix = reads.vix_latest(conn) or demo.VIX
    sev = reads.severity_counts(conn)
    if not sev.get("total"):
        sev = demo.SEVERITY
    mood = market_mood(b_in, nifty_up)
    fd, fd_demo = _pick(reads.fii_dii_recent(conn), demo.FII_DII)
    conv, conv_demo = _pick(reads.conviction_now(), demo.CONVICTION)
    fil, fil_demo = _pick(reads.filings_recent(conn), demo.FILINGS)

    # ── the regime one-liner (very top): one calibrated, descriptive read of the day ──
    _adp = [C._d(r).get("avg_dp") for r in internals]
    _delivery = _adp[-1] if _adp else None
    _fii_net = next((float(C._d(r)["net_value"]) for r in fd
                     if C._d(r).get("category") == "FII/FPI" and C._d(r).get("net_value") is not None), None)
    regime = C.regime_banner(mood.get("word"), b_in, breadth, _delivery, _fii_net, nifty_up)

    # ── the FEATURED card + the selectable ticker ──
    wl, wl_demo = _pick(reads.watchlist_rows(conn), demo.WATCHLIST)
    pf, pf_demo = _pick(reads.portfolio(conn), demo.PORTFOLIO)
    featured = C.featured_card(C.watchlist_block(wl), wl_demo,
                               C.portfolio_block(pf), pf_demo,
                               C.index_focus_block(idx, series70))
    ribbon = C.ribbon_feeds(_feeds(conn, idx, wl, wl_demo, pf, pf_demo))

    # ── MAIN column: featured · pulse deck · what-changed · news (all visible) ──
    pulse = C.zone("Market pulse", "market internals · nightly",
                   C.pulse_deck(idx, mood, (b_in if b_in is not None else 0), breadth,
                                series70[-30:], internals, highs, sectors, vix=vix),
                   sub="the market in one glance", sample=idx_demo)
    trig = C.zone("What changed today", "Signal engine · nightly",
                  C.count_band(sev) + C.changed_rows(reads.what_changed(conn) or demo.WHATCHANGED)
                  + C.learn("Signals that flipped state since yesterday — described from the tape, never a prediction."),
                  sub="signals that flipped")
    conviction = C.zone("Today's conviction", "Cross-pillar synthesis · nightly", C.conviction_block(conv),
                        sub="where all pillars align", sample=conv_demo, name="Conviction")
    news_rows, news_demo = _pick(reads.recent_news(conn, limit=20), demo.NEWS)
    news = C.zone("Market news", "Newswire · 2× daily", C.wire(news_rows),
                  sub="headlines, symbol-tagged", sample=news_demo)
    main = '<div class="g-main">' + regime + featured + pulse + conviction + trig + news + "</div>"

    # ── RAIL: flows · filings · calendars · go-deeper · toggle ──
    flows = C.zone("FII / DII flows", "FII/DII cash · post-close", C.flows_block(fd),
                   sub="foreign vs domestic", sample=fd_demo)
    filings = C.zone("Filings & ownership", "SEBI disclosures · daily", C.filings_block(fil),
                     sub="insider · pledge · stake", sample=fil_demo, name="Filings")
    ca_rows, ca_demo = _pick(reads.upcoming_ca(conn, days=21), demo.CA)
    ca = C.zone("Going ex — corporate actions", "NSE filings · daily", C.ca_agenda(ca_rows),
                sub="dividends · splits · bonuses", sample=ca_demo, name="Going ex")
    res_rows, res_demo = _pick(reads.upcoming_results(days=30), demo.RESULTS)
    res = C.zone("Results calendar", "Board meetings · daily", C.results_agenda(res_rows),
                 sub="who reports next", sample=res_demo)
    drawer = C.delivery_drawer(reads.delivery_leaders(conn) or demo.DELIVERY)
    toggle = "Leave the preview" if on else "Enter the Graphite preview"
    toggle_card = C.card("The Graphite preview",
                         '<p style="font-size:12px;color:var(--ink-3);margin:0 0 8px">Opt-in · isolated from the '
                         "classic site.</p><form method=\"post\" action=\"/dash/home/toggle\">"
                         "<button class=\"g-btn\" type=\"submit\">" + toggle + "</button></form>")
    side = '<div class="g-side">' + flows + filings + ca + res + drawer + toggle_card + "</div>"

    return ribbon + C.hidden_tray() + '<div class="g-dash">' + main + side + "</div>"
