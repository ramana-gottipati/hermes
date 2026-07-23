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
    try:
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            body = _compose(conn)
    except Exception:  # noqa: BLE001 — a busy/edge DB must never 500 the home
        body = C.zone("Market pulse", "index_signals", C.empty("Today's signals haven't landed yet."))
    toggle = ("Leave the preview" if on else "Enter the Graphite preview")
    rail = (C.card("The Graphite preview",
                   "<p>A from-scratch, opt-in preview of the new experience — parallel to and fully "
                   "isolated from the classic site, which is unchanged.</p>"
                   "<form method=\"post\" action=\"/dash/home/toggle\">"
                   "<button class=\"g-btn\" type=\"submit\">" + toggle + "</button></form>"))
    return HTMLResponse(shell.shell("Home", body, rail_html=rail))


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


def _compose(conn) -> str:
    """Increment (i): the market-pulse zone over real reads proves the foundation end-to-end.
    Zones 2-7 land in increments (ii)-(iii); the shell + kit + reads + gates are the foundation."""
    idx = reads.index_pulse(conn)
    breadth = reads.breadth_latest(conn)
    b_in, nifty_up = reads.mood_inputs(conn)
    from src.web.market_mood import market_mood
    mood = market_mood(b_in, nifty_up)
    return C.zone("Market pulse", "index_signals · nightly",
                  C.pulse_block(idx, mood, breadth),
                  sub="where the whole market stands today")
