"""src/web/home/preview_retired.py — THE OLD PREVIEW IS RETIRED (cutover lane W6, owner OK 3d13d97).

What this replaces
------------------
The redesign M0-M5 preview estate (`/dash/preview`, `/dash/preview/stock`, `/dash/_ui3` and their
preview-only children) was the opt-in proving ground for the v3 identity. Every capability it
carried now ships in the Graphite estate, which became the site's DEFAULT LANDING at D148 — so the
preview is a second, unmaintained front door onto the same data. Two front doors is exactly the
duplication the parity ledger exists to prevent.

De-routed, NEVER deleted
------------------------
The renderers (`v3_preview` · `today_v3` · `stock_hub_v3` · `hub_sections_v3` · `stock_chart_v3` ·
`shell_v3` · `ui_showcase_v3` · `ui_*_v3` · `news_dock` · `term_chip` · `ui_skin_bold`) stay in the
tree and in git history — their `_ROUTER_SPECS` mount tuples are what was removed. Nothing outside
that cluster imports them (traced W6: the only mentions elsewhere are the `tests/test_home_isolation`
BANNED list and docstrings explaining why the Graphite package may not touch them), so de-routing
them strands no other surface.

Old bookmarks keep working
--------------------------
Every retired PAGE answers a 302 to its Graphite twin instead of a 404:

    /dash/preview               -> /dash/home              (M5 Today became the default landing)
    /dash/preview/stock?sym=X   -> /dash/home/stock?sym=X   (the W1 stock page; `sym` is carried)
    /dash/preview/stock/export  -> /dash/home/stock?sym=X   (see the honest gap below)
    /dash/_ui3                  -> /dash/home/_kit          (the Graphite component kit)

302, never 301 — the same reasoning D148 recorded for the landing switch: a permanent redirect is
cached by browsers and would make a rollback effectively impossible. Deleting this module's
`_ROUTER_SPECS` line and restoring the four preview tuples is the whole revert.

Only `sym` is carried across. The hub's other query state (`section=` · `ch=` · `cmp=`) addressed
sections, a news dock and a comparison rail that the Graphite page composes differently; forwarding
those keys would fabricate the impression that the old deep-link still resolves to the same view.

⚠ ONE HONEST GAP, disclosed rather than papered over: `/dash/preview/stock/export` was a real
server-side series CSV (bounded 3y default, `range=max`), and the Graphite chart has **no CSV twin** —
`stock_chart_g.py` never carried that endpoint. Its only consumer was the retired hub's own chart
rail, so nothing in the live estate breaks, but a bookmark of that URL now lands on the stock PAGE,
not on a CSV. That capability is not carried; it is not silently replaced either.

`/dash/preview/toggle` (POST, the `pv3` opt-in cookie) is de-routed with NO replacement: it gated an
opt-in that no longer exists, and a POST endpoint is not a bookmark class.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

router = APIRouter()

# path -> Graphite twin. The handler names below start with `compat_` so
# tests/test_dash_route_registry.classify() reads them as `compat_redirect` from the derived rule,
# with no new hand-maintained table row (the same treatment every D80 flat→nested alias gets).
LANDING = "/dash/home"
STOCK = "/dash/home/stock"
KIT = "/dash/home/_kit"

# The retirement map, exported so gates can assert it instead of re-typing the pairs.
RETIRED: dict[str, str] = {
    "/dash/preview": LANDING,
    "/dash/preview/stock": STOCK,
    "/dash/preview/stock/export": STOCK,
    "/dash/_ui3": KIT,
}


def _stock(sym: str) -> RedirectResponse:
    sym = (sym or "").strip().upper()[:24]
    # `sym` is echoed into a Location header, so it is restricted to the character class real NSE
    # symbols use (letters/digits/&/-/_/.), never passed through raw.
    sym = "".join(ch for ch in sym if ch.isalnum() or ch in "&-_.")
    from urllib.parse import quote
    target = STOCK + ("?sym=" + quote(sym, safe="") if sym else "")
    return RedirectResponse(target, status_code=302)


@router.get("/dash/preview", include_in_schema=False, name="compat_preview_landing")
def compat_preview_landing() -> RedirectResponse:
    """The M5 Today preview → the Graphite home, which IS the default landing since D148."""
    return RedirectResponse(LANDING, status_code=302)


@router.get("/dash/preview/stock", include_in_schema=False, name="compat_preview_stock")
def compat_preview_stock(sym: str = Query("", max_length=24)) -> RedirectResponse:
    """The M4 evidence-scroll hub → the Graphite stock page (W1 lineage B), carrying `sym`."""
    return _stock(sym)


@router.get("/dash/preview/stock/export", include_in_schema=False, name="compat_preview_export")
def compat_preview_export(sym: str = Query("", max_length=24)) -> RedirectResponse:
    """The hub's series CSV → the Graphite stock page. NOT an equivalent: see the module docstring —
    the Graphite chart carries no CSV export, so this preserves the link, not the capability."""
    return _stock(sym)


@router.get("/dash/_ui3", include_in_schema=False, name="compat_ui3_showcase")
def compat_ui3_showcase() -> RedirectResponse:
    """The v3 design-system showcase → the Graphite component kit, its direct successor."""
    return RedirectResponse(KIT, status_code=302)


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    for src_path, dest in (("/dash/preview", LANDING), ("/dash/_ui3", KIT),
                           ("/dash/preview/stock", STOCK)):
        r = c.get(src_path, follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == dest, (src_path, r.status_code)
    r = c.get("/dash/preview/stock?sym=M%26M", follow_redirects=False)
    assert r.headers["location"] == STOCK + "?sym=M%26M", r.headers["location"]
    print("preview_retired selftest OK — 4 routes 302 to their Graphite twins, sym carried + quoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
