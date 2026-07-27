"""src/web/home/w2_pages.py — the ONE mount point for the lane W2-C Markets children.

Five declared-child routes under the already-mounted `/dash/home*` prefix, so `__init__.py` takes a
single anchored two-line insert instead of five (five sibling cutover lanes are editing that file
concurrently). Every route is registered in `tests/test_dash_route_registry.py::INTERNAL_DEV` in
the same commit — declared children, no `lens_registry` entry, no nav, until cutover.

    /dash/home/seasonal      seasonal_pages   tape · this-month screen · index divergence · expiry
    /dash/home/patterns      patterns_pages   Wolfe waves · harmonic shapes
    /dash/home/anatomy       anatomy_pages    what preceded big moves (research panel)
    /dash/home/own-history   anatomy_pages    how unusual today is, for this name
    /dash/home/compare       compare_pages    rebased side-by-side overlay
"""
from __future__ import annotations

from fastapi import APIRouter

from src.web.home import anatomy_pages, compare_pages, patterns_pages, seasonal_pages

router = APIRouter()
for _mod in (seasonal_pages, patterns_pages, anatomy_pages, compare_pages):
    router.include_router(_mod.router)
