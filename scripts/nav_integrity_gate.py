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
table, renders the navigable surfaces, and asserts four contracts:

    A. NO DEAD LINKS   — every /dash href the chrome renders resolves to a real route.
    B. NO ORPHANS      — every page route is reachable from a rendered surface, OR is
                         registered as a non-nav KIND (an explicit, REASONED act).
    C. NO DOUBLE STRIP — no page renders the contextual sub-nav container more than
                         once, and the legacy `_track_subnav` stays neutralised.
    D. NO UNREACHABLE GRAPHITE PAGE — every `/dash/home*` page is reachable from the
                         POST-CUTOVER front door, unless its own registry rationale
                         declares that it is not a destination.

ONE ALLOWLIST, ONE AUTHORITY (cutover lane W6, 2026-07-27)
----------------------------------------------------------
This script used to keep its OWN `INTENTIONAL_NON_NAV` dict beside the machine-readable
tables in `tests/test_dash_route_registry.py`. Two lists doing one job is one list too
many, and they drifted exactly as you would expect: by the Graphite cutover the script's
copy carried 28 entries against the test's 48, so the script reported real, linked pages
(e.g. `/dash/home/internals`, which sits in the Graphite top bar) as orphans while the
suite was green. Only one of them could be right, and neither could be trusted.

The fix is structural, not cosmetic: the allowlist is now DERIVED, by importing that test
module and asking its `classify()` for each route's KIND. Anything that is not a `lens` is
legitimately not a nav tab — and every kind that module cannot derive already demands an
owner + a specific rationale (playbook §5), so the "explicit human act" this gate depends
on is unchanged; it just happens in ONE place now. The two gates can no longer disagree,
because there is nothing left for them to disagree about.

Reachability is measured on the nav graph a real visitor has. Since D148 the front door is
`/dash` → 302 → the Graphite home, so the crawl seeds there and walks the Graphite estate
alongside the classic surfaces — which is what makes contract D possible at all.

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

# -- the SINGLE ALLOWLIST AUTHORITY: tests/test_dash_route_registry.py --------
# The route-registry gate already classifies every /dash route into exactly one KIND, with an
# owner + rationale for every kind it cannot derive (playbook section 5). Importing it here --
# rather than keeping a second copy of the same judgements -- is what makes the two gates incapable
# of drifting apart. It is loaded by PATH (`tests/` is not a package), so this script still runs
# standalone, from any cwd, with no test-runner involved.
def _registry():
    import importlib.util
    path = os.path.join(_ROOT, "tests", "test_dash_route_registry.py")
    spec = importlib.util.spec_from_file_location("_nav_route_registry", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# A `/dash/home*` internal_dev page is exempt from contract D only when its OWN rationale says, in
# so many words, that it is not a destination. These two phrases are the recorded vocabulary -- both
# already appear verbatim on the surfaces that mean it (`/dash/home/_kit` = "deliberately unlinked";
# `/dash/home/pat/ask` = "not a page, reached only by the dock's own input"). Anything else shipped
# under /dash/home is a page somebody built for a reader, and it has to be reachable.
_NOT_A_DESTINATION = ("deliberately unlinked", "not a page")

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
    rendered: set[str] = set()

    def _walk(path: str) -> set[str]:
        """Render one surface, bank its hrefs, return them. Never raises.

        Redirects are FOLLOWED (TestClient's default, and what this gate always did): under D80
        every flat lens URL 307s to its nested canonical, and `/dash` itself 302s to the Graphite
        home since the cutover — a crawl that stopped at the redirect would render nothing."""
        if path in rendered:
            return set()
        rendered.add(path)
        try:
            r = client.get(path, follow_redirects=True)
        except Exception as e:  # noqa: BLE001
            render_fail.append(f"{path} -> render raised {type(e).__name__}: {e}")
            return set()
        if r.status_code != 200:
            render_fail.append(f"{path} -> {r.status_code} (expected 200)")
            return set()
        hs = _hrefs(r.text)
        linked.update(hs)
        reachable.update(hs)
        return hs

    for path in RENDER_SURFACES:
        _walk(path)

    # POST-CUTOVER crawl (D148): the real front door is `/dash`, which 302s to the Graphite home.
    # Walking it — and then every Graphite page it leads to, breadth-first — is what makes
    # "reachable" mean what a visitor can actually click TODAY rather than what the classic chrome
    # happened to emit. Bounded by the estate itself: only /dash/home* hrefs are followed, and each
    # page is rendered at most once, so the crawl terminates on the graph's own size.
    frontier = sorted(h for h in _walk("/dash") if h.startswith("/dash/home"))
    reachable.add("/dash/home")
    while frontier:
        nxt = frontier.pop(0)
        for h in sorted(_walk(nxt)):
            if h.startswith("/dash/home") and h not in rendered:
                frontier.append(h)

    # expand reachability across the flat↔nested equivalence (both directions).
    for _flat, _nested in flat_to_nested.items():
        if _nested in reachable:
            reachable.add(_flat)
        if _flat in reachable:
            reachable.add(_nested)

    fails: list[str] = list(render_fail)

    # ── Contract A: no dead links (chrome points only at things that answer) ───
    # The route TABLE is not the whole truth any more: since D148 `/dash/classic` is served by the
    # cutover MIDDLEWARE (it rewrites the path ahead of routing), so it is a perfectly live URL that
    # appears in no `app.routes` entry. A table miss is therefore a suspicion, not a verdict —
    # confirm it by asking the app, which is the thing a reader's click would actually ask.
    dead = []
    for h in sorted(linked):
        if h in real_routes:
            continue
        try:
            if client.get(h, follow_redirects=True).status_code != 404:
                continue      # served by middleware / a mount — alive, just not a route row
        except Exception:  # noqa: BLE001 — an unrenderable link is as dead as a 404
            pass
        dead.append(h)
    for h in dead:
        fails.append(f"DEAD LINK: nav links {h} but nothing answers it (404)")

    # ── Contract B: no orphans (every page reachable, or registered as a non-nav KIND) ─
    # The allowlist is DERIVED from tests/test_dash_route_registry.py — see the module docstring.
    # A route classified as anything other than `lens` was a deliberate, owner+rationale'd act
    # there; a route classified as NOTHING is that gate's failure to raise, not ours to duplicate.
    reg = _registry()
    kinds = {p: reg.classify(p, meta["methods"], meta["names"])
             for p, meta in reg._dash_paths(app).items()}
    orphans = []
    for p in page_routes:
        if p in reachable or kinds.get(p) not in (None, "lens"):
            continue
        orphans.append(p)
    for p in sorted(orphans):
        fails.append(f"ORPHAN: page route {p} (kind={kinds.get(p)}) is reachable from no rendered "
                     f"surface — link it, or register its kind in tests/test_dash_route_registry.py "
                     f"with an owner and a reason")

    # ── Contract D: no unreachable Graphite page ───────────────────────────────
    # Contract B lets `internal_dev` off the hook by design (that is what the kind MEANS). The
    # Graphite estate is entirely internal_dev — the D148 owner decision REJECTED registering it in
    # lens_registry, because that registry generates the CLASSIC nav and registering there would
    # drift it. Without this contract the whole new site would sit in B's blind spot, and a page
    # nobody can reach would gate green. So: under /dash/home, "registered" is not enough — a page
    # is either reachable from the front door or its own rationale says it is not a destination.
    unreachable = []
    for p in page_routes:
        if not p.startswith("/dash/home") or p in reachable:
            continue
        why = (reg.INTERNAL_DEV.get(p) or ("", ""))[1].lower()
        if any(tok in why for tok in _NOT_A_DESTINATION):
            continue
        unreachable.append(p)
    for p in sorted(unreachable):
        fails.append(f"UNREACHABLE GRAPHITE PAGE: {p} is built and routed but no page in the "
                     f"Graphite estate links it — wire it into the nav, or say in its "
                     f"tests/test_dash_route_registry.INTERNAL_DEV rationale why it is not a "
                     f"destination ({' / '.join(_NOT_A_DESTINATION)})")

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
    non_nav = sum(1 for p in page_routes if kinds.get(p) not in (None, "lens"))
    print(f"== nav-integrity: {len(page_routes)} page routes · {len(rendered)} surfaces rendered · "
          f"{len(reachable)} reachable · {non_nav} registered non-nav (derived) ==")
    print("  A. dead links     :", "PASS" if not dead else f"FAIL ({len(dead)})")
    print("  B. orphans        :", "PASS" if not orphans else f"FAIL ({len(orphans)})")
    print("  C. double sub-nav :", "PASS" if not any("DOUBLE STRIP" in f for f in fails) else "FAIL")
    print("  D. graphite reach :", "PASS" if not unreachable else f"FAIL ({len(unreachable)})")

    if not fails:
        print("PASS — nav graph coherent: no dead links, no orphans, no duplicate sub-nav, every Graphite page reachable.")
        return 0
    print(f"\nFAIL — {len(fails)} nav-integrity issue(s). STOP: fix, link, or allowlist with a reason.")
    for line in fails:
        print(f"  !! {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
