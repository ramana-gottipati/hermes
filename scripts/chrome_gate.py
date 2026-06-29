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

    uk-skin     body.uk-skin  → shell_skin reskin applied to a legacy page
    v2bar       .v2bar        → the canonical 4-altitude nav rendered
    Trust       >Trust<       → the Coverage/Trust utility is present
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
import sys

# Run from the repo root regardless of CWD so `import src.*` resolves.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── the chrome contract ──────────────────────────────────────────────────────
# LEGACY pages render through dashboard._shell, so they MUST carry the full reskin
# chrome: the skin (uk-skin), the v2 nav bar (v2bar), the Trust utility, a Wire
# link, and NO legacy search form (.hsearch). A representative page per altitude +
# the stock page + the strategy lenses that historically lost their chrome.
LEGACY_PAGES = [
    "/dash/markets", "/dash/screener", "/dash/strategies", "/dash/dashboard",
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

# marker label → (substring, must_be_present)
_LEGACY_MARKERS = [
    ("uk-skin", 'class="uk-skin"', True),
    ("v2bar", 'class="v2bar"', True),
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
    apply it in-process so the gate tests the chrome the VPS would render)."""
    from fastapi.testclient import TestClient

    import src.main as M
    from src.web import v2_surfaces

    v2_surfaces.wire(M.app)
    v2_surfaces.wire(M.app)  # idempotent — re-applying must not double-wrap the chrome
    return TestClient(M.app)


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
    for label, needle, must_be_present in markers:
        present = needle in html
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

    print("== legacy pages (full chrome: uk-skin · v2bar · Trust · Wire · no .hsearch) ==")
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
