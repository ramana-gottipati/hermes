#!/usr/bin/env python3
"""
nav_integrity_gate.py — the NAV-vs-ROUTES contract gate.

Why this exists
---------------
chrome_gate.py proves the right *chrome* is served (skin, topbar, Trust, Wire).
regression_sweep.sh proves every route answers 200. Neither checks the one thing
that actually bit us: whether the navigation graph is COHERENT with the routes the
app serves. Two failure modes slipped past both gates because they are about
*structure*, not *presence*:

  1. DUPLICATE sub-nav — a page renders the same lens strip twice. The Tracker
     workspace did exactly this: the registry-driven shell sub-nav AND the legacy
     in-page `_track_subnav()` pills both drew {Dashboard·Portfolios·Watchlists·
     Performance·Import}. Every chrome marker was still present (twice), so the
     chrome gate passed. A 200 hides it. Only a human eye caught it.

  2. ORPHAN / DEAD links — a real page route that the nav links NOWHERE (a feature
     you can't reach), or a nav link that points at a route that doesn't exist (a
     404 waiting to happen). Presence checks can't see either.

This gate makes both a FAIL at commit time. It builds the app in-process exactly
as production wires it (src.main + v2_surfaces.wire), enumerates the real route
table, renders the navigable surfaces, and asserts three contracts:

    A. NO DEAD LINKS   — every /dash href the chrome renders resolves to a real route.
    B. NO ORPHANS      — every page route is reachable from a rendered surface, OR is
                         on INTENTIONAL_NON_NAV (an explicit, REASONED allowlist).
    C. NO DOUBLE STRIP — no page renders the contextual sub-nav container more than
                         once, and the legacy `_track_subnav` stays neutralised.

The allowlist is the load-bearing part: a new orphan is a FAIL *unless* a human adds
it to INTENTIONAL_NON_NAV with a reason. That converts "did the agent remember to
look?" into "the build won't pass if the nav graph drifts."

Usage
-----
    python scripts/nav_integrity_gate.py     # exit 0 = nav graph coherent, 1 = drift
"""
from __future__ import annotations

import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── what counts as a "page" ───────────────────────────────────────────────────
# Sub-resource / data / fragment endpoints are NOT navigable destinations, so they
# are excluded from the orphan check (they are reached by JS/forms, never by a tab).
_SUBRES_MARKERS = (
    "/overlay", "/series", "/export", "/quote", "template.csv",
    "/memo", "/track/", "/dash/drawings", "/dash/scan",
)

# ── INTENTIONAL non-nav page routes (the REASONED allowlist) ──────────────────
# Each entry is a real page route that is deliberately NOT a top-bar/sub-nav tab.
# Adding here is the explicit human act that keeps the gate honest: a NEW orphan
# fails until someone justifies it in this dict. Keep the reasons specific.
INTENTIONAL_NON_NAV: dict[str, str] = {
    "/dash":            "root — redirects into the app shell",
    "/dash/index":      "home/landing surface (entered via the logo / root), not a lens tab",
    "/dash/_ui":        "ui_kit design-system showcase — dev-only, deliberately unlinked",
    "/dash/offline":    "PWA offline fallback page — served by the service worker, never a tab",
    "/dash/pat":        "Pat is the global Cmd-K summon, NOT a nav tab (IA decision)",
    "/dash/stock":      "per-stock dossier — a DESTINATION reached by clicking a stock, claims no altitude",
    "/dash/theme":      "per-theme detail — a DESTINATION reached from the Themes list",
    "/dash/tracker":    "alias landing of /dash/dashboard (registry alias) — Tracker tab lands on dashboard",
    "/dash/strategies": "RETIRED legacy Strategies hub — merged into /dash/strategist; kept alive (no 404), "
                        "deliberately de-linked (v2_surfaces asserts it must not appear in the Strategist strip)",
    # Wolfe/Harmonic: the per-stock CHART OVERLAY stays overlay-only (route=None records),
    # AND the market-wide SCANNERS are now Markets "Patterns" nav lenses (Ramana 2026-07-02).
    # /dash/harmonic + /dash/wolfe/scan are therefore REACHABLE (removed from this allowlist);
    # /dash/wolfe (the picker landing) stays non-nav — reached from the chart + the scanner body.
    "/dash/wolfe":      "Wolfe picker/landing — reached from the chart overlay + the Wolfe scanner body; the SCANNER (/dash/wolfe/scan) is the Markets·Patterns nav lens",
    # per-stock news timeline — its CONTENT is now embedded as the dossier's News tab
    # (render_stock_timeline), so it is surfaced in-page; the standalone route is kept as
    # a shareable deep-link (/dash/news?sym=). Distinct from /dash/wire (market wire).
    "/dash/news":       "per-stock news timeline — content embedded as the stock-dossier News tab; "
                        "standalone route kept as a shareable deep-link. Distinct from /dash/wire.",
    # per-stock RS-momentum pane — same pattern as /dash/news: its CONTENT is embedded as
    # the stock-dossier Momentum tab (dashboard._mompane card_html), and every row of the
    # nav-reachable /dash/divergence board deep-links here per symbol (links are DATA-driven,
    # so an empty dev DB renders none for the gate to see).
    "/dash/momentum":   "per-stock RS-momentum pane — content embedded as the stock-dossier "
                        "Momentum tab; standalone route is the per-symbol deep-link target of "
                        "the /dash/divergence board rows.",
    # reachable via page-BODY cross-links (not the top chrome) — verified live:
    "/dash/ratio":      "sacred ratio page — reached from the index/markets bodies (cockpit ratio links)",
    "/dash/rs":         "full RS ranking — reached from the cockpit 'Full RS ranking' body link",
    "/dash/replay":     "Replay-the-Tape — reached from the Trust/Coverage page body (the S55 trail)",
    # Wolfe open-trades view (D120/S121): a declared NESTED CHILD of the Patterns·Wolfe lens,
    # reached via the on-page Fresh setups ⇄ Open trades toggle (emits active="wolfe"), not a tab.
    # (tests/test_dash_route_registry.py classifies it 'nested_child'; this keeps the sister gate green.)
    "/dash/wolfe/trades": "Wolfe open-trades remaining-ROI view — reached from the on-page "
                          "Fresh ⇄ Open toggle on the Wolfe scanner, not a top-nav tab (D120)",
    # Alert-rail dismiss action (D106/S123): a GET mutation endpoint, not a navigable page
    # (POST-ification tracked as S-B2 debt). Sibling gate classifies it 'api_or_action'.
    "/dash/attention/ack": "alert-rail dismiss action — a GET mutation endpoint (303 back), not a "
                           "navigable page; reached from the ✕ controls on /dash/attention",
}

# ── surfaces to render to discover what is reachable ──────────────────────────
# The top-bar landings + the known body-cross-link hubs (index/markets/sectors/rrg/
# coverage/stock). Rendering these captures every href the chrome AND the major
# in-page rails emit, so "reachable" reflects what a user can actually click.
RENDER_SURFACES = [
    "/dash/markets", "/dash/index", "/dash/sectors", "/dash/rrg", "/dash/rs-hub",
    "/dash/coverage", "/dash/dashboard", "/dash/screen2", "/dash/strategist",
    "/dash/stock?sym=ACC", "/dash/screener", "/dash/themes",
    # CCI board — nav-reachable (Strategies · Credibility); its header links the
    # credibility fingerprint (/dash/credibility), which the dossier CCI tab also embeds
    # but only when the dev DB has rows — so the gate verifies THIS static link.
    "/dash/concalls",
]

# altitude landing pages that MUST carry exactly one contextual sub-nav strip.
SUBNAV_PAGES = ["/dash/markets", "/dash/dashboard", "/dash/strategist", "/dash/portfolios"]
# the contextual sub-nav container classes (legacy shell + native ui_kit).
_SUBNAV_CONTAINER_RE = re.compile(r'class="(?:v2subnav|uk-sub)\b')


def _build_client():
    from fastapi.testclient import TestClient
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return TestClient(M.app), M.app


def _page_routes(app) -> list[str]:
    routes = sorted({
        r.path for r in app.routes
        if getattr(r, "path", "").startswith("/dash")
        and "GET" in getattr(r, "methods", set())
    })
    return [r for r in routes if not any(m in r for m in _SUBRES_MARKERS)]


def _all_routes(app) -> set[str]:
    return {r.path for r in app.routes if getattr(r, "path", "").startswith("/dash")}


def _hrefs(html: str) -> set[str]:
    """Every distinct /dash path the page links to (query/fragment stripped)."""
    return set(re.findall(r'href="(/dash[^"#?]*)', html))


def main() -> int:
    try:
        client, app = _build_client()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL — could not build the app in-process: {type(e).__name__}: {e}")
        return 1

    page_routes = _page_routes(app)
    real_routes = _all_routes(app)

    # D80 URL nesting: a lens page lives at BOTH its flat route (/dash/wire, kept as a
    # 307 redirect) and its nested canonical (/dash/markets/wire, what the chrome links).
    # Derive the equivalence from the SAME engine that installs it (never a hand list),
    # so either form being linked marks the page reachable — the flat originals must not
    # read as orphans once the chrome emits nested hrefs.
    flat_to_nested: dict[str, str] = {}
    try:
        from src.web import nested_nav as _NN
        from src.web import lens_registry as _LR
        for _ln in _LR.LENSES:
            _n = _NN.nested_path(_ln)
            if _ln.route and _n and _n != _ln.route:
                flat_to_nested[_ln.route] = _n
            elif _ln.route and _n == _ln.route and _ln.route == f"/dash/{_ln.altitude}/{_ln.key}":
                # lens already registered at its nested canonical (e.g. Tracker) — its
                # legacy flat /dash/<key> survives as a 307 compat route; same page.
                flat_to_nested[f"/dash/{_ln.key}"] = _ln.route
    except Exception as e:  # noqa: BLE001 — pre-nesting checkouts still gate cleanly
        print(f"  (nested-nav equivalence unavailable: {type(e).__name__}: {e})")

    # render the navigable surfaces; collect everything reachable + all linked hrefs.
    reachable: set[str] = set()
    linked: set[str] = set()
    render_fail: list[str] = []
    for path in RENDER_SURFACES:
        try:
            r = client.get(path)
        except Exception as e:  # noqa: BLE001
            render_fail.append(f"{path} -> render raised {type(e).__name__}: {e}")
            continue
        if r.status_code != 200:
            render_fail.append(f"{path} -> {r.status_code} (expected 200)")
            continue
        hs = _hrefs(r.text)
        linked |= hs
        reachable |= hs

    # expand reachability across the flat↔nested equivalence (both directions).
    for _flat, _nested in flat_to_nested.items():
        if _nested in reachable:
            reachable.add(_flat)
        if _flat in reachable:
            reachable.add(_nested)

    fails: list[str] = list(render_fail)

    # ── Contract A: no dead links (chrome points only at real routes) ──────────
    dead = sorted(h for h in linked if h not in real_routes)
    for h in dead:
        fails.append(f"DEAD LINK: nav links {h} but no such route exists (404 risk)")

    # ── Contract B: no orphans (every page reachable or explicitly allowlisted) ─
    orphans = []
    for p in page_routes:
        if p in reachable or p in INTENTIONAL_NON_NAV:
            continue
        orphans.append(p)
    for p in sorted(orphans):
        fails.append(f"ORPHAN: page route {p} is reachable from no rendered surface "
                     f"and is not in INTENTIONAL_NON_NAV (add it with a reason, or link it)")

    # stale allowlist hygiene: an allowlisted route that no longer exists is dead config.
    for p in sorted(INTENTIONAL_NON_NAV):
        if p not in real_routes:
            fails.append(f"STALE ALLOWLIST: {p} is in INTENTIONAL_NON_NAV but is no longer a route")

    # ── Contract C: no double sub-nav strip ────────────────────────────────────
    # C1 — direct regression lock on the bug we fixed: the legacy Tracker strip must
    #      stay neutralised (it now renders via the registry sub-nav, like every page).
    import src.web.dashboard as D
    if hasattr(D, "_track_subnav") and D._track_subnav("dashboard") != "":
        fails.append("DOUBLE STRIP: dashboard._track_subnav is rendering again — the Tracker "
                     "workspace will show TWO identical sub-nav strips (the registry one + "
                     "this legacy in-page one). It must stay neutralised by v2_surfaces.wire.")
    # C2 — generic: no altitude page renders the contextual sub-nav container twice.
    for path in SUBNAV_PAGES:
        try:
            html = client.get(path).text
        except Exception:  # noqa: BLE001
            continue
        n = len(_SUBNAV_CONTAINER_RE.findall(html))
        if n > 1:
            fails.append(f"DOUBLE STRIP: {path} renders {n} contextual sub-nav containers "
                         f"(expected exactly 1) — a duplicated lens strip")

    # ── report ─────────────────────────────────────────────────────────────────
    print(f"== nav-integrity: {len(page_routes)} page routes · "
          f"{len(reachable)} reachable · {len(INTENTIONAL_NON_NAV)} allowlisted ==")
    print("  A. dead links     :", "PASS" if not dead else f"FAIL ({len(dead)})")
    print("  B. orphans        :", "PASS" if not orphans else f"FAIL ({len(orphans)})")
    print("  C. double sub-nav :", "PASS" if not any("DOUBLE STRIP" in f for f in fails) else "FAIL")

    if not fails:
        print("PASS — nav graph coherent: no dead links, no orphans, no duplicate sub-nav.")
        return 0
    print(f"\nFAIL — {len(fails)} nav-integrity issue(s). STOP: fix, link, or allowlist with a reason.")
    for line in fails:
        print(f"  !! {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
