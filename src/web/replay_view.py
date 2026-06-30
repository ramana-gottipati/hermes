"""replay_view.py — serve the "Replay the Tape" point-in-time audit one-pager.

The static artifact ``docs/replay-the-tape.html`` is the client-facing zero-look-ahead
demonstrator (D-PITCH-1 / D-PITCH-4 beat 3): scrub to a past date, see only what the desk
could have known on that day, then reveal what happened next. It is the prominent,
discoverable trail OFF the Coverage / Trust front-door — ``coverage_view.py`` links here.

The file is a COMPLETE standalone HTML document: it carries its own ``<head>``/``<style>``/
``<script>`` and ALL of its data inline (the ALKYLAMINE / TANLA heroes), with no API or
network dependency. So this route serves the file verbatim; it is deliberately NOT wrapped
in the v2 dashboard shell (it has its own chrome and is meant to read as a finished memo).

Isolation (the rs_section.py / coverage_view.py house pattern): a brand-new module that
adds ONE route, imports nothing from the app, and deletes nothing. It is durably mounted via
``v2_surfaces._ROUTER_SPECS`` so the route survives a main.py clobber / redeploy. Defensive:
a missing artifact degrades to a small note rather than a 500 — this is a trust artifact
reached from the trust page, and a trust surface must never error.

Route: GET /dash/replay
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# The artifact lives under docs/ at the repo root. This module is .../src/web/replay_view.py,
# so parents[2] is the repo root (/opt/hermes on the VPS). A CWD-relative path is tried as a
# fallback in case the process layout differs.
_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "docs" / "replay-the-tape.html",
    Path("docs/replay-the-tape.html"),
]

_FALLBACK = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    "<title>Replay the Tape · patearn</title></head>"
    "<body style=\"margin:0;background:#0e1116;color:#e8ecf1;"
    "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif\">"
    "<div style=\"max-width:640px;margin:14vh auto;padding:0 24px;line-height:1.6\">"
    "<h1 style=\"font-size:20px;margin:0 0 10px\">Replay the Tape</h1>"
    "<p style=\"color:#8b97a7\">The point-in-time audit one-pager is not available in this "
    "environment. On the analytics host it renders the live zero-look-ahead walkthrough "
    "(scrub to a past date, then reveal what happened next).</p>"
    "<p><a href=\"/dash/coverage\" style=\"color:#5ec8ff;text-decoration:none\">"
    "&larr; Back to Coverage</a></p></div></body></html>"
)


def _read_artifact() -> str | None:
    """Return the standalone HTML document, or None if it cannot be read anywhere."""
    for p in _CANDIDATES:
        try:
            return p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 — try the next candidate path
            continue
    return None


@router.get("/dash/replay", response_class=HTMLResponse)
def replay_page() -> HTMLResponse:
    """Serve the Replay-the-Tape PIT audit document verbatim.

    Read from disk on each request (the file is small and self-contained; reading live keeps
    the route in lock-step with a redeployed artifact). Degrades to a small note if the file
    is absent — never a 500."""
    html = _read_artifact()
    if html is None:
        return HTMLResponse(_FALLBACK)
    return HTMLResponse(html)
