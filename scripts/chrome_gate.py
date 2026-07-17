#!/usr/bin/env python3
"""
chrome_gate.py — the CLEAN-CHECKOUT chrome contract gate (the other half of the
release gate; the live-200 sweep is scripts/regression_sweep.sh).

Why this exists
---------------
regression_sweep.sh proves the live VPS still *answers* every route with a 200.
But a 200 says nothing about WHAT was served: the v2 chrome is wired at runtime
(v2_surfaces.wire → the canonical nav + shell_skin reskin), and every one of those
hooks is DEFENSIVE — a failure is logged and swallowed so a page never 500s. That
is the right runtime posture, but it means the site can silently regress to the
legacy chrome (green-"e" logo, the old search box, the flat top bar) while every
route still returns 200. The live-200 sweep would call that a PASS.

This gate closes that gap. It builds the app IN-PROCESS from the current checkout
(no network, no live VPS), reproduces the production wiring (the v2 hook that
scripts/wire_v2_surfaces.py applies to the VPS's main.py), renders the actual
pages through TestClient, and asserts the HTML carries the chrome markers:

    uk-skin     body.uk-skin  → shell_skin reskin applied to a legacy page (asserted as a
                                CLASS TOKEN on <body>, not an exact attribute string — the
                                S122 left-rail middleware merges `has-rail` into the same
                                class attribute on rail-bearing pages, see _UK_SKIN_RE)
    uk-top      .uk-top       → the NATIVE single-row topbar rendered (Lane M1: legacy
                                pages now render the same uk-top as the native pages,
                                replacing the old two-row .v2bar header)
    no .v2bar   class="v2bar" ABSENT → the legacy two-row nav anomaly is gone (header
                                unified; this is the marker M1 flipped from present→absent)
    Trust       >Trust<       → the Coverage/Trust utility is present (now inline w/ tabs)
    Wire        /dash/wire    → the News/Wire surface is mounted + linked in nav
    no .hsearch class="hsearch" ABSENT → the legacy search form was swapped out

A regression in any of those is now a FAIL at commit time, before deploy — not a
green light from a 200 that hides a reverted skin.

Usage
-----
    python scripts/chrome_gate.py          # exit 0 = chrome intact, 1 = regressed
    .venv/bin/python scripts/chrome_gate.py # on the VPS, with the app venv

Exit 0 = every chrome marker present where required. Exit 1 = a regression — STOP,
fix or revert before committing (same contract as regression_sweep.sh).
"""
from __future__ import annotations

import os
import re
import sys

# Run from the repo root regardless of CWD so `import src.*` resolves.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── the chrome contract ──────────────────────────────────────────────────────
# LEGACY pages render through dashboard._shell, so they MUST carry the full reskin
# chrome: the skin (uk-skin), the NATIVE single-row topbar (uk-top) — Lane M1 unified
# the header, so the old two-row .v2bar must be ABSENT — the Trust utility, a Wire
# link, and NO legacy search form (.hsearch). A representative page per altitude +
# the stock page + the strategy lenses that historically lost their chrome.
LEGACY_PAGES = [
    # NB: /dash/strategies, /dash/rs, /dash/scan are now 307-redirects to their canonical
    # successors (strategist / rs-hub / stocks) — orphaned-screen dedup 2026-07-02 — so
    # they are no longer full chrome pages. /dash/stocks (Positioning) stands in as the
    # still-live strategies-altitude legacy page.
    "/dash/markets", "/dash/screener", "/dash/stocks", "/dash/dashboard",
    "/dash/stock?sym=ACC", "/dash/mep", "/dash/cpr", "/dash/leaders",
    "/dash/conviction", "/dash/sectors",
    # /dash/testing must render (graceful "unavailable" state) even when research.db
    # is absent — a data-backed page that 500s is an institutional-demo credibility hit.
    "/dash/testing",
]

# NATIVE pages are built directly on the ui_kit design system (NOT via _shell), so
# they carry their own chrome — no uk-skin/v2bar body markup — but they MUST still
# render and expose the shared Trust + Wire destinations in their own nav.
NATIVE_PAGES = ["/dash/coverage", "/dash/screen2", "/dash/strategist", "/dash/_ui"]

# S122 left rail (src/web/left_rail.py, db70db8): the rail middleware MERGES `has-rail`
# (+ data-alt/data-wide) into the existing <body> class on every rail-bearing page, so the
# served attribute is `class="uk-skin has-rail"` — locally through TestClient AND on the
# live box (curl-verified 2026-07-17, byte-identical). An exact-attribute needle
# 'class="uk-skin"' therefore false-failed 10/11 legacy pages while the chrome was fully
# intact (only /dash/stock passed — the dossier claims no altitude, so the rail skips it).
# Assert the CLASS TOKEN on the <body> tag instead: still fails when the skin is truly
# gone, indifferent to whatever other classes share the attribute.
_UK_SKIN_RE = re.compile(r'<body[^>]*\bclass="[^"]*\buk-skin\b')

# marker label → (needle, must_be_present); a needle is a plain substring or a compiled
# regex (regex needles are matched with .search).
# Lane M1 (header unification): legacy pages render the NATIVE single-row `uk-top` topbar
# (the same one the native pages use) instead of the legacy two-row `.v2bar` header. So
# `uk-top` MUST be present and the old `.v2bar` MUST be absent — that pair locks the
# unification (a silent revert to the two-row header now FAILS the gate).
_LEGACY_MARKERS = [
    ("uk-skin", _UK_SKIN_RE, True),
    ("uk-top", 'class="uk-top"', True),
    ("no .v2bar (header unified)", 'class="v2bar"', False),
    ("Trust", ">Trust<", True),
    ("Wire", "/dash/wire", True),
    ("no .hsearch", 'class="hsearch"', False),
]
_NATIVE_MARKERS = [
    ("Trust", ">Trust<", True),
    ("Wire", "/dash/wire", True),
]


def _build_client():
    """Build the app exactly as production serves it: import src.main, then apply the
    durable v2 hook (scripts/wire_v2_surfaces.py adds this line to the VPS main.py; we
    apply it in-process so the gate tests the chrome the VPS would render).

    CL-SCR-12: the old code just called wire() twice and asserted nothing, so the
    "idempotency test" was a no-op — a double-wrap regression would pass silently. We
    now snapshot the route table after the first wire(), wire() a second time, and
    ASSERT the route count is unchanged. A second wire() that adds routes (double-mount)
    or wraps the chrome twice is a real bug and now fails the gate before deploy."""
    from fastapi.testclient import TestClient

    import src.main as M
    from src.web import v2_surfaces

    v2_surfaces.wire(M.app)
    routes_before = len(M.app.routes)
    v2_surfaces.wire(M.app)            # must be idempotent — no new routes, no double-wrap
    routes_after = len(M.app.routes)
    if routes_after != routes_before:
        raise AssertionError(
            f"v2_surfaces.wire is NOT idempotent: route count {routes_before} -> "
            f"{routes_after} on a second call (double-mount / double-wrap regression)")
    return TestClient(M.app)


# CL-SCR-02: a degraded page can still emit just enough nav scaffolding to satisfy a
# bare substring like ">Trust<" while having lost its actual body (e.g. an error page
# that inherits the shell). Require a minimum rendered length so a stub/error page that
# happens to carry the nav markers cannot false-green the gate. A real Patearn page is
# several KB; 2KB is comfortably below any real page and well above an error stub.
_MIN_HTML_LEN = 2048


def _check(client, path: str, markers) -> list[str]:
    """Return a list of human-readable failures for one page (empty == PASS)."""
    fails: list[str] = []
    try:
        r = client.get(path)
    except Exception as e:  # noqa: BLE001
        return [f"{path} -> render raised {type(e).__name__}: {e}"]
    if r.status_code != 200:
        return [f"{path} -> {r.status_code} (expected 200)"]
    html = r.text
    if len(html) < _MIN_HTML_LEN:
        fails.append(f"{path} -> page suspiciously short ({len(html)}B < {_MIN_HTML_LEN}B): "
                     "likely a degraded/error stub that still carries nav scaffolding")
    # require the markers to live inside the document body, not anywhere in the response
    # (a bare-substring match can be satisfied by a stray comment/attribute on a broken
    # page). We anchor the must-be-present markers to the <body>..</body> span when one
    # exists; absence markers still scan the whole document (stricter).
    lo = html.find("<body")
    hi = html.rfind("</body>")
    body = html[lo:hi] if (lo != -1 and hi != -1 and hi > lo) else html
    for label, needle, must_be_present in markers:
        haystack = body if must_be_present else html
        if isinstance(needle, re.Pattern):
            present = needle.search(haystack) is not None
        else:
            present = needle in haystack
        if present != must_be_present:
            verb = "missing" if must_be_present else "leaked (should be gone)"
            fails.append(f"{path} -> chrome marker {verb}: {label}")
    return fails


def main() -> int:
    try:
        client = _build_client()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL — could not build the app in-process: {type(e).__name__}: {e}")
        return 1

    fails: list[str] = []

    print("== legacy pages (full chrome: uk-skin · uk-top · no .v2bar · Trust · Wire · no .hsearch) ==")
    for p in LEGACY_PAGES:
        f = _check(client, p, _LEGACY_MARKERS)
        fails += f
        if f:
            for line in f:
                print(f"  !! {line}")

    print("== native ui_kit pages (own chrome: 200 · Trust · Wire) ==")
    for p in NATIVE_PAGES:
        f = _check(client, p, _NATIVE_MARKERS)
        fails += f
        if f:
            for line in f:
                print(f"  !! {line}")

    n = len(LEGACY_PAGES) + len(NATIVE_PAGES)
    if not fails:
        print(f"PASS — chrome contract intact ({len(LEGACY_PAGES)} legacy + "
              f"{len(NATIVE_PAGES)} native pages, all markers present)")
        return 0
    print(f"FAIL — {len(fails)} chrome regression(s) across {n} pages. "
          "STOP: fix or revert before committing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
