"""v3_preview.py — /dash/preview, the opt-in gate for the v3 experience (redesign M0).

The S177-mandated missing piece: a preview you ENTER deliberately. Direct URL only — no link,
button, or affordance is added to any existing page or chrome, so the default site's rendered
bytes are provably unchanged (Codex review B2; proven by tests/test_v3_isolation.py + a live
curl diff at deploy).

Mechanics:
  GET  /dash/preview         — the preview landing page (rendered in shell_v3, so opening it
                               IS the demo), showing toggle state + what's in the preview.
  POST /dash/preview/toggle  — sets / clears the `pv3` opt-in cookie (playbook #11: writes are
                               POST, never a state-mutating GET), 303 back to the landing.

The cookie is read ONLY by v3-aware modules (none of the legacy estate reads it). Until M4+
ships v3 twins of real pages, the preview's destinations are this landing + /dash/_ui3.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.web import shell_v3, term_chip, ui_components_v3 as C

router = APIRouter()

_COOKIE = "pv3"


def is_on(request: Request) -> bool:
    """The one place v3-aware modules ask 'is the preview opted in?'."""
    return request.cookies.get(_COOKIE) == "1"


@router.get("/dash/preview", response_class=HTMLResponse, include_in_schema=False)
def preview_landing(request: Request, ch: str = "wire", sym: str = "") -> HTMLResponse:
    on = is_on(request)
    state = ("ON — v3-aware pages will render the new look for this browser."
             if on else "OFF — the classic site is untouched everywhere.")
    btn = "Leave the preview" if on else "Enter the preview"
    focus = (
        C.card("The Patearn v3 preview",
               "<p>An opt-in, additive preview of the redesigned experience "
               "(plan: approved modules only — the theme layer and the self-teaching term "
               "chips are live here today). Nothing about the classic site changes unless "
               "you opt in, and leaving restores it instantly.</p>"
               "<p>Preview is <b>" + state + "</b></p>"
               "<form method=\"post\" action=\"/dash/preview/toggle\">"
               "<button class=\"pv3-btn\" type=\"submit\">" + btn + "</button></form>"
               + C.fence("not_advice"))
        + C.section("In this preview")
        + C.card("", "<p><a href=\"/dash/_ui3\">The v3 design system + term chips →</a><br>"
                 "Try a chip: " + term_chip.chip("dvpt") + " · " + term_chip.chip("conviction")
                 + "</p>")
    )
    rail = C.card("Status", "<p>Approved: M0 preview gate · M1 theme layer · M2 term chips · "
                  "M3 news/flow dock (below).<br>"
                  "Pending owner approval: the recomposed stock page, Today, "
                  "the guided journey.</p>"
                  "<p>" + C.evidence_link("/dash", "Back to the classic site") + "</p>")
    from src.web import news_dock
    dock = news_dock.dock_html(ch=ch, sym=sym, base="/dash/preview")
    head = C.css() + term_chip.assets() + news_dock.css()
    return HTMLResponse(shell_v3.shell("Preview", focus, rail, extra_head=head, dock_html=dock))


@router.post("/dash/preview/toggle", include_in_schema=False)
def preview_toggle(request: Request) -> RedirectResponse:
    resp = RedirectResponse("/dash/preview", status_code=303)
    if is_on(request):
        resp.delete_cookie(_COOKIE, path="/")
    else:
        # session-scoped opt-in; SameSite=Lax, HttpOnly not needed (no secret — a UI flag)
        resp.set_cookie(_COOKIE, "1", path="/", max_age=60 * 60 * 24 * 30, samesite="lax")
    return resp


def _selftest() -> int:
    routes = {getattr(r, "path", None) for r in router.routes}
    assert "/dash/preview" in routes and "/dash/preview/toggle" in routes
    methods = {m for r in router.routes if getattr(r, "path", "") == "/dash/preview/toggle"
               for m in getattr(r, "methods", set())}
    assert methods == {"POST"}, methods   # the write is POST-only (playbook #11)
    print("v3_preview selftest OK — landing + POST toggle")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
