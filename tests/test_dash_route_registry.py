"""test_dash_route_registry.py — the no-orphan ROUTE-REGISTRY gate (UX audit S-H).

Why this test exists
--------------------
Orphans stopped being accidents. Convention ("register every new page in the nav")
did not hold on its own, so the estate accumulated 10 legacy/orphan routes + a
data-orphan (`docs/ux-journey-audit-2026-07-13.md` §5, §7). `scripts/nav_integrity_gate.py`
already proves the *rendered* nav graph is coherent (no dead links, no orphans reachable
from a surface, no double sub-nav). This test is the complementary, STRONGER contract it
names in `docs/SURFACE-PLAYBOOK.md` §5: **every `/dash` route the app serves must carry a
positive KIND.** A route that matches no derived rule and is in no machine-readable
exemption table FAILS the build — you cannot add a page and forget to classify it.

The RouteKind contract (audit §8 / playbook §5)
-----------------------------------------------
Every distinct `/dash` path is exactly one of:

    lens            — a registered nav lens's canonical serving route (DERIVED from
                      lens_registry + nested_nav; never hand-listed).
    nested_child    — a declared child page of a lens, reached in-page (toggle / deep
                      link), not itself a top-nav lens (e.g. Wolfe "Open trades").
    dossier         — a per-entity destination that claims no altitude (stock / theme /
                      index detail), reached by clicking an entity.
    api_or_action   — a data / fragment / overlay / export endpoint or a state mutation
                      (any non-GET verb, or a known sub-resource path). Never a nav tab.
    compat_redirect — a flat → nested 307 kept alive so old links never break (DERIVED
                      from the registry, the `compat_`/`_compat_` handler name, or the
                      small REDIRECT_ALIASES table for legacy aliases).
    internal_dev    — a dev-only / infrastructure surface, deliberately unlinked.
    exempt          — anything else legitimate, allowlisted WITH owner + rationale. The
                      seed list is the audit §5 orphan inventory. A NEW exempt route is a
                      FAIL until a human adds it here with a reason — that is the whole point.

`lens` and `compat_redirect` are derived from `lens_registry` (the single source), so they
can never drift. The other kinds are MACHINE-READABLE tables below (path -> owner/rationale);
prose in a doc does not count as registration (playbook §5).

Run
---
    pytest tests/test_dash_route_registry.py       # as a gate
    python  tests/test_dash_route_registry.py      # prints the full classification table
"""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.web import lens_registry as LR      # noqa: E402
from src.web import nested_nav as NN         # noqa: E402


# ── DERIVED truth — never hand-maintained ────────────────────────────────────────
# The canonical serving route of every routed lens (nested where nesting applies, flat
# for Trust + workspace roots) and the flat originals that now 307-redirect to them.
_ROUTED = [ln for ln in LR.LENSES if ln.route]
LENS_CANON: set[str] = {NN.nested_path(ln) for ln in _ROUTED if NN.nested_path(ln)}
FLAT_REDIR: set[str] = {ln.route for ln in _ROUTED if NN.nested_path(ln) != ln.route}


# ── MACHINE-READABLE registries for the non-derivable kinds ───────────────────────
# Each maps path -> (owner, rationale). Adding a route here is the explicit human act
# that keeps the gate honest. Keep rationales specific; cite the audit §5 disposition
# for the known orphans so a future S-B session knows what to do with them.

# per-entity destinations — reached by clicking a symbol / theme / index; claim no altitude.
DOSSIER: dict[str, tuple[str, str]] = {
    "/dash/stock": ("core", "per-stock dossier — THE destination reached by clicking a symbol; "
                            "carries the lens as a #tab anchor, claims no nav altitude"),
    "/dash/theme": ("core", "per-theme detail — reached from the Themes/Baskets list (tag=)"),
    "/dash/index": ("markets", "per-index detail (idx=) — reached from the index/markets bodies; "
                               "also the logo/root landing surface"),
}

# declared children of a lens — reached in-page, never their own nav tab.
NESTED_CHILDREN: dict[str, tuple[str, str]] = {
    "/dash/wolfe/trades": ("wolfe", "Open-trades remaining-ROI view — child of the Patterns·Wolfe "
                                    "lens, reached via the on-page Fresh setups ⇄ Open trades toggle; "
                                    "emits active=\"wolfe\" so it highlights that one lens (D120)"),
    # transcribed from the slow-rotation lane's own declaration (S132f, momentum_view.py
    # "Declared child (D80 nesting)") — the lane landed the route without this row.
    "/dash/momentum-scan/slow": ("momentum", "quarterly large-cap LOWVOL_MOM anchor (Slow rotation) — "
                                             "child of the momentum-scan lens, reached from its "
                                             "on-page link; emits active=\"momentum-scan\""),
}

# dev-only / infrastructure surfaces, deliberately unlinked.
INTERNAL_DEV: dict[str, tuple[str, str]] = {
    "/dash/_ui":     ("ui-kit", "ui_kit design-system showcase — dev-only, deliberately unlinked"),
    "/dash/offline": ("pwa", "PWA offline fallback page — served by the service worker, never a tab"),
    # redesign M0-M2 preview surfaces (docs/redesign-coordination.md; Codex B1) — OPT-IN,
    # direct-URL only, deliberately unlinked until cut-over ratification promotes them to lenses.
    "/dash/preview": ("v3-preview", "v3 preview landing + opt-in gate — additive preview program, "
                                    "never linked from default chrome (byte-identity rule)"),
    "/dash/_ui3":    ("v3-preview", "v3 design-system + term-chip showcase — dev/preview-only, "
                                    "deliberately unlinked"),
    "/dash/preview/stock": ("v3-preview", "M4 evidence-scroll stock hub — preview-only, reached "
                                          "from /dash/preview + direct URL, never default chrome"),
    # Graphite Home (2026-07-23) — the fresh-and-parallel v3 home section (spec
    # docs/redesign-graphite-home-spec.md). Direct-URL, opt-in `pvg`, NO lens/nav until cutover.
    "/dash/home":     ("graphite-home", "fresh-and-parallel v3 Graphite home — opt-in preview, "
                                        "direct-URL only, no lens/nav until cutover (zero classic drift)"),
    "/dash/home/_kit": ("graphite-home", "Graphite component-kit showcase — dev/preview-only, "
                                         "deliberately unlinked"),
    "/dash/home/rotation": ("graphite-home", "Markets sector-rotation RRG (6/12/24-month journeys, "
                                             "fixed ~10-dot tails) — a declared child of the Graphite "
                                             "home, reached via 'See the full rotation →' from the Today "
                                             "RRG; direct-URL, no lens/nav until cutover"),
    # W5 / M6 — the Graphite Trust & Proof estate: eight declared children of the Graphite home
    # (src/web/home/trust_pages.py), each reached from the Proof directory strip that every one of
    # them carries and from the standing "New here? How to read →" help control. Direct-URL, no
    # lens/nav until cutover — registering a lens IS the cutover.
    "/dash/home/proof": ("graphite-home", "Proof hub — the honest boundary + the live coverage / "
                                          "settlement snapshot (the Graphite port of /dash/coverage); "
                                          "reached from the help control and every Proof page's "
                                          "directory strip"),
    "/dash/home/validation": ("graphite-home", "The published falsification record — every strategy's "
                                               "net result vs the index plus the blocking ledger (port "
                                               "of /dash/testing); ?pack=1 renders the print/procurement "
                                               "assembly that /dash/evidence-pack used to be"),
    "/dash/home/prereg": ("graphite-home", "Pre-registered study ledger with the gate written before "
                                           "the run + its SHA-256 (port of /dash/spec-sheets); linked "
                                           "from the Proof directory strip"),
    "/dash/home/rule-lab": ("graphite-home", "Rule lab — compose a rule from the closed vocabulary and "
                                             "get the ledger's answer; ALL state round-trips through "
                                             "?u=&rank=&n=&hold=&where=&veto= so a verdict is a "
                                             "shareable URL (ratified Part III §K.4)"),
    "/dash/home/replay": ("graphite-home", "Replay any date — asks the real /v1 API what was knowable "
                                           "on a past morning (port of /dash/replay-any-date); ?sym= + "
                                           "?as_of=, reached from the Proof strip and the Today card"),
    "/dash/home/glossary": ("graphite-home", "The metric dictionary rendered from the SAME "
                                             "docs/metrics-glossary.md the ? popovers use; ?q= "
                                             "pre-fills the filter so a term link is shareable"),
    "/dash/home/strategy-ref": ("graphite-home", "One canonical page per strategy, served from "
                                                 "docs/strategies/ through the public sanitizer; ?p=slug"),
    "/dash/home/guide": ("graphite-home", "How to read this site — the newcomer exit and the standing "
                                          "destination of the persistent help control (port of "
                                          "/dash/reading-guide); carries the M6 five-step arc"),
    "/dash/home/pat/ask": ("graphite-home", "The Pat dock's deterministic answer endpoint — returns an "
                                            "HTML fragment for one question, resolved from the glossary "
                                            "+ lens registry with no model call; not a page, reached "
                                            "only by the dock's own input"),
    # Sideways migration-parity board (2026-07-24) — the internal governance dashboard proving no
    # classic element is silently missed in the modern-app rebuild (gate: tests/test_sideways_parity.py).
    # An owner/ops tool, deliberately unlinked; NOT a customer lens, so no lens_registry entry.
    "/dash/sideways-parity": ("migration", "Sideways migration-parity ledger — internal governance "
                                           "board (derived inventory + dispositions), deliberately "
                                           "unlinked; owner/ops tool, not a customer nav lens"),
}

# legacy-alias 307 redirects whose handler name is NOT compat_*-prefixed and whose flat
# route is not derivable from the registry (so name/registry detection would miss them).
REDIRECT_ALIASES: dict[str, tuple[str, str]] = {
    "/dash/tracker": ("tracker", "307 → /dash/tracker/dashboard (dash_tracker_redirect) — the "
                                 "Tracker tab lands on the Dashboard sub-page"),
    "/dash/rs":      ("markets", "legacy alias — RedirectResponse to the rs-hub successor (dash_rs); "
                                 "§5 disposition already applied"),
    "/dash/scan":    ("markets", "legacy alias — RedirectResponse to the momentum-scan successor "
                                 "(dash_scan); §5 disposition already applied"),
}

# exempt-with-owner+rationale — the seed list IS the audit §5 orphan inventory + a few
# structural specials. A NEW entry here is a deliberate, reviewed decision.
EXEMPT: dict[str, tuple[str, str]] = {
    "/dash":            ("core", "root — redirects into the app shell / home landing"),
    # /dash/pat moved OUT of this table (S-D): Pat is now a registered Trust lens
    # ("Ask Pat", lens_registry) per audit §8 — the ⌘K summon stays, the nav entry adds
    # discoverability. The old "NOT a nav tab" IA note is amended by that audit decision.
    "/dash/ratio":      ("sacred", "RS-ratio analyst tool — SACRED build-additive deep-link "
                                   "(never reroute/remove, memory build-additive-never-replace); "
                                   "§5: declare exempted dossier-tool + palette entry (S-D)"),
    "/dash/strategies": ("s-b", "RETIRED legacy Strategies hub — merged into /dash/strategist; kept "
                                "alive (no 404), deliberately de-linked (v2_surfaces asserts it is "
                                "absent from the Strategist strip)"),
    "/dash/wolfe":      ("wolfe", "Wolfe picker/landing (overlay-only lens, route=None) — reached "
                                  "from the chart overlay control + the Wolfe scanner body, not a tab"),
    # ── §5 orphan inventory (per-stock panes embedded in the dossier; standalone = deep-link) ──
    "/dash/credibility": ("s-b", "per-stock CCI fingerprint (sym=) — content embedded as the dossier "
                                 "Credibility tab; §5 disposition: merge as a Credibility child/tab"),
    "/dash/momentum":    ("s-b", "per-stock RS-momentum pane (sym=) — embedded as the dossier Momentum "
                                 "tab + the per-symbol deep-link target of the /dash/divergence rows; "
                                 "§5 disposition: declare a nested child of the rs-hub/momentum family"),
    "/dash/news":        ("s-b", "per-stock news timeline (sym=) — embedded as the dossier News tab; "
                                 "standalone kept as a shareable deep-link; §5 disposition: 307 → wire"),
    "/dash/replay":      ("s-b", "Replay-the-Tape — superseded by replay-any-date; §5 disposition: "
                                 "307 or declare as a Trust child"),
}


# ── the classifier — pure over (path, methods, handler-names) ─────────────────────
_ACTION_SUFFIXES = ("/overlay", "/series", "/memo", "/ack", "/export", "/quote", "/edit")


def _is_api_or_action(path: str, methods: set[str]) -> bool:
    """A data/fragment/overlay/export endpoint or a state mutation — never a nav page."""
    if methods - {"GET"}:                                   # any non-GET verb (POST/PUT/DELETE)
        return True
    if path == "/dash/track" or path.startswith("/dash/track/"):   # tracker CRUD + fragments
        return True
    if path.startswith("/dash/import/"):                    # import preview/commit/template
        return True
    if path == "/dash/tags" or path == "/dash/drawings":    # bare action endpoints
        return True
    if path.startswith("/dash/api/"):                       # JSON data feeds, never nav pages
        return True                                         # (S-D: /dash/api/symbol-search)
    if path.endswith(_ACTION_SUFFIXES) or path.endswith("template.csv"):
        return True
    return False


def classify(path: str, methods: set[str], names: set[str]) -> str | None:
    """Return the single RouteKind for a /dash path, or None if UNCLASSIFIED (a fail)."""
    if _is_api_or_action(path, methods):
        return "api_or_action"
    if (path in FLAT_REDIR or path in REDIRECT_ALIASES
            or any(n.startswith(("compat_", "_compat_")) for n in names)):
        return "compat_redirect"
    if path in LENS_CANON:
        return "lens"
    if path in NESTED_CHILDREN:
        return "nested_child"
    if path in DOSSIER:
        return "dossier"
    if path in INTERNAL_DEV:
        return "internal_dev"
    if path in EXEMPT:
        return "exempt"
    return None


# ── the SURFACE-PLAYBOOK landing checklist, embedded in the failure message ───────
_PLAYBOOK_CHECKLIST = """\
An UNCLASSIFIED /dash route means a page was added without registering it. Fix it, do NOT
just append to a table. Per docs/SURFACE-PLAYBOOK.md §3 (landing checklist, same commit):
  1  Registry entry     — a lens_registry.py Lens (or a declared child of one)
  2  Durable mount      — anchored insert in v2_surfaces._ROUTER_SPECS
  3  Education minimum   — infographics.bottom_line()/plain()/how_to_read_link() + gloss()
  4  Honesty fence       — the shared fence wording; no buy/sell/avoid/ride/fade verdict verbs
  5  Glossary keys       — new metrics → docs/metrics-glossary.md (feeds popovers AND Pat)
  6  Pat registration    — at least a nav-answer (Pat can name + link the page)
  7  Strategy doc        — a strategy surface updates its docs/strategies/ page same commit
  8  Export              — analyst tables ship server-side ?format=csv, not a DOM blob
  9  Symbol links        — every symbol cell links /dash/stock?sym=  (never ?symbol=)
  10 Home exposure       — decide tile/board/flagship/none, record why in the commit
  11 Writes are POST     — never a state-mutating GET
  12 State doc           — PROJECT_STATE §Key-paths/§Decision-log in the same commit

If the route is NOT a nav page, add it to exactly ONE machine-readable table in this file
(DOSSIER / NESTED_CHILDREN / INTERNAL_DEV / REDIRECT_ALIASES / EXEMPT) WITH an owner and a
specific rationale — that is the deliberate, reviewed act the gate requires."""


# ── build the app in-process, exactly as production wires it ──────────────────────
def _build_app():
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return M.app


def _dash_paths(app) -> dict[str, dict]:
    """{path: {"methods": set, "names": set}} for every /dash route the app serves."""
    table: dict[str, dict] = {}
    for r in app.routes:
        p = getattr(r, "path", "")
        if not p.startswith("/dash"):
            continue
        methods = {m for m in (getattr(r, "methods", set()) or set()) if m not in ("HEAD", "OPTIONS")}
        ent = table.setdefault(p, {"methods": set(), "names": set()})
        ent["methods"] |= methods
        ent["names"].add(getattr(r, "name", "") or "")
    return table


@pytest.fixture(scope="module")
def routes():
    return _dash_paths(_build_app())


# ── the contracts ─────────────────────────────────────────────────────────────────
def test_every_dash_route_has_a_kind(routes):
    """Contract: every served /dash route classifies into exactly one RouteKind."""
    unclassified = sorted(
        p for p, meta in routes.items()
        if classify(p, meta["methods"], meta["names"]) is None
    )
    assert not unclassified, (
        f"\n{len(unclassified)} UNCLASSIFIED /dash route(s) — the no-orphan gate FAILED:\n"
        + "\n".join(f"  !! {p}" for p in unclassified)
        + "\n\n" + _PLAYBOOK_CHECKLIST
    )


def test_no_stale_registry_entries(routes):
    """Every hand-maintained table entry must still be a live route (no dead config)."""
    served = set(routes)
    stale = []
    for name, tbl in (("DOSSIER", DOSSIER), ("NESTED_CHILDREN", NESTED_CHILDREN),
                      ("INTERNAL_DEV", INTERNAL_DEV), ("REDIRECT_ALIASES", REDIRECT_ALIASES),
                      ("EXEMPT", EXEMPT)):
        for p in tbl:
            if p not in served:
                stale.append(f"{name}: {p} is registered but is no longer a served route")
    assert not stale, "\nStale registry entries (remove them):\n" + "\n".join(f"  !! {s}" for s in stale)


def test_registry_entries_carry_owner_and_rationale():
    """Machine-readable = an (owner, rationale) tuple, both non-empty — not prose elsewhere."""
    bad = []
    for name, tbl in (("DOSSIER", DOSSIER), ("NESTED_CHILDREN", NESTED_CHILDREN),
                      ("INTERNAL_DEV", INTERNAL_DEV), ("REDIRECT_ALIASES", REDIRECT_ALIASES),
                      ("EXEMPT", EXEMPT)):
        for p, val in tbl.items():
            if (not isinstance(val, tuple) or len(val) != 2
                    or not str(val[0]).strip() or not str(val[1]).strip()):
                bad.append(f"{name}: {p} lacks an (owner, rationale)")
    assert not bad, "\n" + "\n".join(f"  !! {b}" for b in bad)


def test_no_path_matches_two_kinds(routes):
    """Kinds must be mutually exclusive: a path classifies to one bucket, not several.
    (Guards against a future edit that lets, say, an EXEMPT path also sit in FLAT_REDIR.)"""
    overlaps = []
    tables = {"nested_child": set(NESTED_CHILDREN), "dossier": set(DOSSIER),
              "internal_dev": set(INTERNAL_DEV), "redirect_alias": set(REDIRECT_ALIASES),
              "exempt": set(EXEMPT)}
    for p in routes:
        hits = [k for k, s in tables.items() if p in s]
        # a hand-table path must not ALSO be a derived lens/flat-redirect
        if p in LENS_CANON:
            hits.append("lens")
        if p in FLAT_REDIR:
            hits.append("compat_redirect(flat)")
        if len(hits) > 1:
            overlaps.append(f"{p} → {hits}")
    assert not overlaps, "\nRoutes matching >1 kind:\n" + "\n".join(f"  !! {o}" for o in overlaps)


def test_kinds_are_non_degenerate(routes):
    """Sanity: the derivation actually populated the core kinds (catches a broken import
    that would make everything fall through to a single bucket)."""
    counts: dict[str, int] = {}
    for p, meta in routes.items():
        counts[classify(p, meta["methods"], meta["names"]) or "UNCLASSIFIED"] = \
            counts.get(classify(p, meta["methods"], meta["names"]) or "UNCLASSIFIED", 0) + 1
    for kind in ("lens", "compat_redirect", "api_or_action", "dossier", "exempt"):
        assert counts.get(kind, 0) > 0, f"no routes classified as {kind} — derivation looks broken ({counts})"


def test_synthetic_unregistered_route_fails_pure():
    """The Done criterion (pure): an unknown GET-HTML /dash route is UNCLASSIFIED."""
    assert classify("/dash/__synthetic_orphan__", {"GET"}, {"orphan_page"}) is None


def test_synthetic_unregistered_route_fails_end_to_end():
    """The Done criterion (end-to-end): mounting a fresh, unregistered GET /dash page makes
    the gate flag it — proving the contract bites on a real route, not just a string."""
    app = _build_app()
    synthetic = "/dash/__synthetic_orphan__"
    app.add_api_route(synthetic, lambda: "orphan", methods=["GET"], include_in_schema=False)
    table = _dash_paths(app)
    assert synthetic in table, "synthetic route was not mounted"
    unclassified = [p for p, m in table.items() if classify(p, m["methods"], m["names"]) is None]
    assert synthetic in unclassified, "the gate did NOT flag a synthetic unregistered route"


# ── script mode — prints the full classification table (like nav_integrity_gate) ──
def _main() -> int:
    table = _dash_paths(_build_app())
    by_kind: dict[str, list[str]] = {}
    unclassified: list[str] = []
    for p, meta in sorted(table.items()):
        k = classify(p, meta["methods"], meta["names"])
        if k is None:
            unclassified.append(p)
        else:
            by_kind.setdefault(k, []).append(p)
    order = ("lens", "nested_child", "dossier", "api_or_action", "compat_redirect",
             "internal_dev", "exempt")
    print(f"== route-registry: {len(table)} distinct /dash paths ==")
    for k in order:
        print(f"  {k:15}: {len(by_kind.get(k, []))}")
    if unclassified:
        print(f"\nFAIL — {len(unclassified)} UNCLASSIFIED:")
        for p in unclassified:
            print(f"  !! {p}")
        print("\n" + _PLAYBOOK_CHECKLIST)
        return 1
    print("PASS — every /dash route carries a kind (no orphans).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
