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


def _compose(conn, on: bool) -> str:
    """The owner-approved 2-region dashboard: a top market ribbon, a MAIN column (market pulse +
    the news hero), and a SIDEBAR of fixed-size, internally-scrolling widgets (triggers · FII/DII ·
    corporate actions · results · the preview toggle). Each list box scrolls inside itself — never
    a flat page. Every zone is a live read with a demo fallback when empty."""
    from src.web.market_mood import market_mood
    from src.web.home import demo
    idx = reads.index_pulse(conn) or demo.INDEX
    b_in, nifty_up = reads.mood_inputs(conn)
    if b_in is None and nifty_up is None:
        b_in, nifty_up = demo.MOOD_INPUTS
    breadth = reads.breadth_latest(conn) or demo.BREADTH
    series = reads.index_series(conn, "NIFTY 50", 30) or demo.SERIES
    sev = reads.severity_counts(conn)
    if not sev.get("total"):
        sev = demo.SEVERITY

    # ── MAIN column: market pulse + the news hero ──
    pulse = C.zone("Market pulse", "index_signals · nightly",
                   C.pulse_block(idx, market_mood(b_in, nifty_up), (b_in if b_in is not None else 0), breadth, series),
                   sub="the market in one glance")
    news = C.zone("Market news", "sent_news · 03:30 & 11:30",
                  C.wire(reads.recent_news(conn, limit=20) or demo.NEWS),
                  sub="headlines, symbol-tagged")
    main = '<div class="g-main">' + pulse + news + "</div>"

    # ── SIDEBAR: fixed-size scrollable widgets ──
    trig = C.zone("What changed today", "signal_events · nightly",
                  C.count_band(sev) + C.changed_rows(reads.what_changed(conn) or demo.WHATCHANGED)
                  + C.learn("Signals that flipped state since yesterday — described from the tape, never a prediction."),
                  sub="signals that flipped")
    flows = C.zone("FII / DII flows", "fii_dii_flows · 14:30 & 16:30",
                   C.flows_block(reads.fii_dii_recent(conn) or demo.FII_DII), sub="foreign vs domestic")
    ca = C.zone("Going ex — corporate actions", "corporate_actions · 02:20",
                C.ca_agenda(reads.upcoming_ca(conn, days=21) or demo.CA), sub="dividends · splits · bonuses")
    res = C.zone("Results calendar", "board_meetings · 02:00",
                 C.results_agenda(reads.upcoming_results(days=30) or demo.RESULTS), sub="who reports next")
    toggle = "Leave the preview" if on else "Enter the Graphite preview"
    toggle_card = C.card("The Graphite preview",
                         '<p style="font-size:12px;color:var(--ink-3);margin:0 0 8px">Opt-in · isolated from the '
                         "classic site.</p><form method=\"post\" action=\"/dash/home/toggle\">"
                         "<button class=\"g-btn\" type=\"submit\">" + toggle + "</button></form>")
    side = '<div class="g-side">' + trig + flows + ca + res + toggle_card + "</div>"

    return C.ribbon(idx, demo.GLOBAL) + '<div class="g-dash">' + main + side + "</div>"
