"""test_education_coverage.py — the EDUCATION-MINIMUM gate (UX audit S-C / SURFACE-PLAYBOOK §3.3).

Why this test exists
--------------------
`test_dash_route_registry.py` (S-H) proves every `/dash` route is *registered* — no orphan
URLs. This is its complement for the NEXT checklist line: **SURFACE-PLAYBOOK §3 item 3, the
"Education minimum"** — every user-facing nav lens must carry the shared readability scaffold
(`infographics.bottom_line()` + `infographics.how_to_read_link()`) so a beginner is never
dropped onto a wall of charts with no plain-English on-ramp. The audit measured the gap
("education = two disjoint half-systems", `docs/ux-journey-audit-2026-07-13.md` §4/§8); S-C
item 2 is the back-fit. This gate keeps it from regressing and stops a NEW lens from shipping
un-scaffolded — the same "convention did not hold on its own" logic that motivated S-H.

The contract
------------
Every routed lens's serving path is exactly one of:

    COVERED — its handler module calls both scaffold helpers (computed at runtime, never
              hand-listed; this is the thing we actually want to be true everywhere).
    EXEMPT  — a lens where a "how to read these charts" band is genuinely N/A (a reference
              reader with no charts of its own). Allowlisted WITH owner + rationale; a NEW
              exempt lens is a deliberate, reviewed act.
    PENDING — the education back-fit backlog: a real lens that SHOULD get the scaffold but
              hasn't yet. A documented set (collective rationale below), trimmed as pages
              land. Being on it is honest debt, not an exemption.

A lens in NONE of the three FAILS the build — you cannot add a nav page and forget the
education minimum. `COVERED` is derived from source, so it can never drift; `EXEMPT`/`PENDING`
are the machine-readable tables (prose in a doc does not count, per playbook §5).

Coverage is a *module-level* source scan (endpoint `__module__` → does its source call the
helpers). That is coarse for `src.web.dashboard`, which serves ~13 legacy lenses from one
6k-line file (one page's helper call would flip all of them "covered"); every dashboard-served
lens is therefore explicitly PENDING/EXEMPT-listed and not relied upon for its runtime read.

PENDING is seeded from the **committed (HEAD)** coverage state, deliberately — a parallel
session may carry un-committed scaffold in the working tree; listing on HEAD keeps the
committed gate green regardless of which session lands first. As pages are scaffolded, trim
them here (the __main__ report prints "covered but still PENDING — trim" hints).

Run
---
    pytest tests/test_education_coverage.py       # as a gate
    python  tests/test_education_coverage.py       # prints the full coverage table
"""
from __future__ import annotations

import inspect
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.web import lens_registry as LR      # noqa: E402
from src.web import nested_nav as NN         # noqa: E402


# ── the education minimum: both helpers present in the lens's handler module ──────
SCAFFOLD_TOKENS = ("bottom_line(", "how_to_read_link(")


# ── DERIVED truth — the canonical serving path of every routed lens ───────────────
# (nested where nesting applies, flat otherwise) — identical basis to the route gate.
_ROUTED = [ln for ln in LR.LENSES if ln.route]
LENS_CANON: dict[str, object] = {(NN.nested_path(ln) or ln.route): ln for ln in _ROUTED}


# ── EXEMPT — a chart-reading band is genuinely N/A here (path -> owner, rationale) ─
# Reference readers with no charts of their own. A NEW entry is a reviewed decision.
EXEMPT: dict[str, tuple[str, str]] = {
    "/dash/glossary": ("trust", "the metric dictionary itself — definitions, no charts to read; "
                                 "it IS the education target other pages link to"),
    "/dash/reading-guide": ("trust", "the visual how-to-read guide itself — the destination of "
                                      "how_to_read_link(); linking it to itself is nonsensical"),
    "/dash/strategy-ref": ("trust", "the docs/strategies/ markdown reader (like glossary) — a "
                                     "reference reader, not a chart lens; carries its own prose intro"),
}


# ── PENDING — the education back-fit backlog (audit §8 education-everywhere). A real
#    lens that should get bottom_line()+how_to_read_link() but hasn't yet. Trim an entry
#    when its page lands the scaffold (the __main__ report flags covered-but-still-listed).
#    Seeded from the HEAD (committed) coverage state — see the module docstring on why.
PENDING: set[str] = {
    # ── Markets ──  (momentum-scan·rotation·rrg·rsband·wire·wolfe-scan landed the scaffold
    #    in S-C item 2, a38a122 — they now read COVERED and are off this list)
    "/dash/markets",                    # Overview hub
    "/dash/markets/actions",
    "/dash/markets/attention",
    "/dash/markets/band-locks",
    "/dash/markets/buyback-calc",
    "/dash/markets/capture-map",
    "/dash/markets/compare",
    "/dash/markets/cycle-clock",
    "/dash/markets/divergence",
    "/dash/markets/early-signals",
    "/dash/markets/harmonic-scan",
    "/dash/markets/leaders",
    "/dash/markets/results-reactions",
    "/dash/markets/rs-hub",
    "/dash/markets/sector-momentum",
    "/dash/markets/sectors",
    "/dash/markets/surveillance",
    # ── Strategies ──  (growth·insider·ratings·sast·shp landed in S-C item 2, a38a122)
    "/dash/strategies/concalls",
    "/dash/strategies/conviction",
    "/dash/strategies/cpr",
    "/dash/strategies/launchpad",
    "/dash/strategies/mep",
    "/dash/strategies/stealth",
    "/dash/strategies/stocks",
    "/dash/strategies/strategist",
    # ── Screener ──
    "/dash/screener",
    "/dash/screener/screen2",           # S-C item 2 target (Screen+)
    "/dash/screener/tags-review",
    "/dash/screener/themes",
    "/dash/screener/workbench",
    # ── Tracker (demo-book workspace — owned by the tracker lane) ──
    "/dash/tracker/dashboard",
    "/dash/tracker/import",
    "/dash/tracker/performance",
    "/dash/tracker/portfolios",
    "/dash/tracker/watchlists",
    # ── Trust / meta ──
    "/dash/coverage",
    "/dash/evidence-pack",
    "/dash/replay-any-date",
    "/dash/spec-sheets",
    "/dash/testing",
}


# ── the SURFACE-PLAYBOOK line, embedded in the failure message ────────────────────
_EDUCATION_CHECKLIST = """\
An UN-SCAFFOLDED /dash lens means a nav page was shipped without the education minimum.
Per docs/SURFACE-PLAYBOOK.md §3 item 3 (same commit as the page):
  Education minimum — infographics.bottom_line() + infographics.how_to_read_link()
                      (a bottom-line-first takeaway band + the "New here?" reading-guide link).
Use the shared helpers in src/web/infographics.py — the readability scaffold reads identically
site-wide (do NOT hand-roll a bespoke band). See any S110 lens (e.g. move_anatomy_view.py) for
the idiom: prepend ifx.readability_css() to the page CSS, then ifx.bottom_line(...) +
ifx.how_to_read_link() right after the page header.

If the page genuinely has no charts to read (a reference reader), add it to EXEMPT in this file
WITH an owner + rationale. If it is real education debt, add it to PENDING (and land the
scaffold soon). Either way is a deliberate, reviewed act — prose in a doc does not count."""


# ── build the app in-process, exactly as production wires it ──────────────────────
def _build_app():
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return M.app


def _lens_module_map(app) -> dict[str, str]:
    """{lens serving path -> handler module name} for every routed lens the app serves."""
    out: dict[str, str] = {}
    for r in app.routes:
        p = getattr(r, "path", "")
        if p in LENS_CANON and p not in out:
            ep = getattr(r, "endpoint", None)
            out[p] = getattr(ep, "__module__", "") if ep is not None else ""
    return out


def _module_has_scaffold(modname: str) -> bool:
    """True iff the handler module's SOURCE calls both scaffold helpers (coarse but stable —
    see the module docstring on multi-lens modules)."""
    if not modname or not modname.startswith("src"):
        return False
    try:
        mod = sys.modules.get(modname) or __import__(modname, fromlist=["_"])
        src = inspect.getsource(mod)
    except Exception:
        return False
    return all(tok in src for tok in SCAFFOLD_TOKENS)


def _covered(app) -> set[str]:
    mm = _lens_module_map(app)
    return {p for p, mod in mm.items() if _module_has_scaffold(mod)}


@pytest.fixture(scope="module")
def app():
    return _build_app()


# ── the contracts ─────────────────────────────────────────────────────────────────
def test_every_lens_has_education_or_is_listed(app):
    """The gate: every routed lens is COVERED, EXEMPT, or PENDING — never unaccounted."""
    covered = _covered(app)
    offenders = sorted(
        p for p in LENS_CANON
        if p not in covered and p not in EXEMPT and p not in PENDING
    )
    assert not offenders, (
        f"\n{len(offenders)} /dash lens(es) with NO education scaffold and NOT listed — "
        "the education-minimum gate FAILED:\n"
        + "\n".join(f"  !! {p}   [{getattr(LENS_CANON[p], 'label', '')}]" for p in offenders)
        + "\n\n" + _EDUCATION_CHECKLIST
    )


def test_listed_paths_are_live_lenses(app):
    """No stale config: every EXEMPT/PENDING path must still be a routed lens."""
    stale = []
    for name, paths in (("EXEMPT", set(EXEMPT)), ("PENDING", PENDING)):
        for p in sorted(paths):
            if p not in LENS_CANON:
                stale.append(f"{name}: {p} is listed but is no longer a routed lens — remove it")
    assert not stale, "\nStale education-table entries:\n" + "\n".join(f"  !! {s}" for s in stale)


def test_exempt_entries_carry_owner_and_rationale():
    """EXEMPT = a reviewed decision: an (owner, rationale) tuple, both non-empty."""
    bad = [p for p, v in EXEMPT.items()
           if not isinstance(v, tuple) or len(v) != 2 or not str(v[0]).strip() or not str(v[1]).strip()]
    assert not bad, "\nEXEMPT entries missing owner/rationale:\n" + "\n".join(f"  !! {b}" for b in bad)


def test_exempt_and_pending_are_disjoint():
    """A lens is exempt OR pending, never both (a category error)."""
    both = sorted(set(EXEMPT) & PENDING)
    assert not both, "\nPaths in BOTH EXEMPT and PENDING:\n" + "\n".join(f"  !! {p}" for p in both)


def test_scanner_finds_the_stable_covered_anchors(app):
    """Sanity: the source scan actually detects coverage — the committed S110 lenses (stable,
    not in any active edit) must read COVERED, else the scanner is broken and the gate is blind."""
    covered = _covered(app)
    anchors = ["/dash/markets/market-internals", "/dash/markets/move-anatomy",
               "/dash/markets/participants"]
    missing = [a for a in anchors if a in LENS_CANON and a not in covered]
    assert not missing, (
        "the scaffold scanner found none of the stable S110 anchors covered — it is broken:\n"
        + "\n".join(f"  !! {m}" for m in missing) + f"\n(covered={len(covered)})"
    )


def test_synthetic_unscaffolded_lens_is_flagged():
    """The Done criterion: a lens path that is neither covered nor listed is an offender —
    proving the contract bites on a NEW un-scaffolded page, not just today's inventory."""
    synthetic = "/dash/__synthetic_unscaffolded_lens__"
    assert synthetic not in EXEMPT and synthetic not in PENDING
    # not covered (not a real module), not listed -> would be an offender
    offender = (synthetic not in EXEMPT and synthetic not in PENDING)
    assert offender is True


# ── human-readable report ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    _app = _build_app()
    mm = _lens_module_map(_app)
    cov = _covered(_app)
    rows = []
    for p in sorted(LENS_CANON):
        if p in cov:
            kind = "COVERED"
        elif p in EXEMPT:
            kind = "EXEMPT"
        elif p in PENDING:
            kind = "PENDING"
        else:
            kind = "!!OFFENDER"
        rows.append((kind, p, mm.get(p, ""), getattr(LENS_CANON[p], "label", "")))
    for kind, p, mod, label in rows:
        print(f"{kind:10} {p:34} {mod:28} [{label}]")
    n_cov = sum(1 for r in rows if r[0] == "COVERED")
    n_off = sum(1 for r in rows if r[0] == "!!OFFENDER")
    stale_pending = sorted(p for p in PENDING if p in cov)
    print(f"\n{n_cov}/{len(rows)} lenses covered · {len(EXEMPT)} exempt · "
          f"{len(PENDING)} pending · {n_off} OFFENDERS")
    if stale_pending:
        print("\ncovered but still PENDING — trim these from PENDING:")
        for p in stale_pending:
            print(f"  ~ {p}")
