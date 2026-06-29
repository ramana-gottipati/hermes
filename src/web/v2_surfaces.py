"""
v2_surfaces.py — durable wiring of the v2 surfaces + the canonical navigation IA.

Single source of truth for (a) mounting the v2 surfaces (Coverage, RS hub, News, /v1)
and (b) the SITE NAVIGATION. It replaces the old flat "dump every lens on the top bar"
nav with the altitudes-vs-lenses model (docs/ui-architecture-v2.md §3), grounded in how
the best institutional products are built (Koyfin ~5 sections, Morningstar 3 modules,
FactSet pinned apps): a few PRIMARY destinations on top, every analytical LENS one level
down in a contextual sub-nav, Pat as a global ⌘K summon, Coverage as a "Trust" utility.

Why a module (not edits to dashboard.py)
----------------------------------------
* main.py needs only a 2-line hook (`from src.web import v2_surfaces; v2_surfaces.wire(app)`),
  re-applied idempotently by scripts/wire_v2_surfaces.py after any clobber.
* dashboard.py needs ZERO edits: the nav is REPLACED at runtime by rebinding the imported
  dashboard module's `_nav` (and neutralising its legacy `_subnav`); page handlers resolve
  `_nav` as a module global at call time, so they pick up the new chrome on every start. A
  chart-session redeploy of dashboard.py therefore cannot break it.

Properties: DEFENSIVE (each step try/except, never fatal) · IDEMPOTENT (sentinel) ·
NO-LOSS (any destination the old nav exposed that the IA doesn't home falls into a "More"
group — nothing is dropped; the sacred routes /dash/ratio, /dash/rrg, /dash/compare keep
their URLs) · ADDITIVE + REVERSIBLE (restore the previous file + restart).
"""

from __future__ import annotations

import importlib
import logging
import re

log = logging.getLogger("hermes.v2")

# Sentinel set on the dashboard module once its _nav has been replaced (no double-wrap).
_NAV_SENTINEL = "_v2_nav_wrapped"

# (label-key, module path, a sample route path to test for prior mount)
# Each is include_router'd by _mount_routers, skipped if its sample route is already
# present — so this is the DURABLE mount point: a route registered here survives a
# main.py clobber/redeploy (wire() re-mounts it) without needing a main.py edit.
_ROUTER_SPECS = [
    ("coverage", "src.web.coverage_view", "/dash/coverage"),
    # Replay the Tape — the standalone PIT-audit one-pager linked off the Coverage/Trust
    # front-door (D-PITCH-1/4). A tiny view that serves docs/replay-the-tape.html verbatim;
    # durably mounted here so the trail off Coverage never dead-ends after a main.py clobber.
    ("replay", "src.web.replay_view", "/dash/replay"),
    ("rs-hub", "src.web.rs_section", "/dash/rs-hub"),
    ("news", "src.web.news_view", "/dash/wire"),
    # Lane B surfaces — durably mounted here so they no longer depend on the
    # (uncommitted) main.py mount block (Round-2 / Lane E consolidation).
    ("strategist", "src.web.strategist_view", "/dash/strategist"),
    ("screen2", "src.web.screener_plus", "/dash/screen2"),
    # Lane A2 — the living design-system showcase.
    ("ui-showcase", "src.web.ui_showcase", "/dash/_ui"),
    # Strategies lenses that the IA already homes (/dash/growth, /dash/testing) but
    # that were never mounted in committed main.py — durably mounted here so a clean
    # clone + deploy renders them instead of 404-ing under their sub-nav entries.
    ("growth", "src.web.growth_view", "/dash/growth"),
    ("testing", "src.web.testing_view", "/dash/testing"),
    # RS band lens — its siblings rsband.py/rrg_view.py are committed but the view was
    # left untracked; now committed + durably mounted here (was only the uncommitted
    # main.py import) so /dash/rsband survives a main.py clobber and a clean checkout.
    ("rsband", "src.web.rsband_view", "/dash/rsband"),
]

# ── the canonical site IA — GENERATED from the single lens registry ──────────
# Altitudes = the top bar (a place you go). Each altitude's sub-nav = its lenses /
# sections (how you evaluate — NEVER an altitude tab). Pat = a global summon (Ask
# Pat ⌘K); Trust (Coverage · Strategy validation) = a right-side utility altitude.
#
# This block USED to hand-maintain four parallel maps (_IA_ALT/_IA_SUB/_SUB_ALIAS/
# _ALT_OF). They now GENERATE from src.web.lens_registry — the single source that the
# dossier tabs, screener columns and cross-links (Lane N3) also read — so the nav can
# no longer drift out of agreement (review §6–§7; ui-architecture-v2.md §0.4/§9). The
# DECIDED Scope × Lens IA (nav-ia-DECISIONS-and-prompts.md §1) lives in that registry.
#
# Each sub-nav item is (key, href, label, group) where `group` is an optional heading
# (e.g. "Rotation", "Accumulation") rendered as a non-link separator before its items.
from src.web import lens_registry as _LR

_ALT_LABELS = {"markets": "Markets", "screener": "Screener",
               "strategies": "Strategies", "tracker": "Tracker", "trust": "Trust"}
# top-bar tab href = the first sub-nav route of each altitude (its landing).
def _alt_landing(_alt: str) -> str:
    """First routed lens of an altitude, or a safe self-route if the altitude has only
    overlay-only lenses (subnav() empty) — never index [0] of an empty list at import time."""
    _sn = _LR.subnav(_alt)
    return _sn[0].route if _sn else f"/dash/{_alt}"


_IA_ALT = [(_alt, _alt_landing(_alt), _ALT_LABELS.get(_alt, _alt.title()))
           for _alt in _LR.altitude_order()]
# {altitude: [(key, href, label, group), ...]} — overlay-only lenses excluded by subnav().
_IA_SUB = {_alt: [(ln.key, ln.route, ln.label, ln.group) for ln in _LR.subnav(_alt)]
           for _alt in (*_LR.altitude_order(), "trust")}
# Discoverability trail (the MEP/Wolfe lesson): the Lab moved to Trust as "Strategy
# validation". Leave a signposted pointer where it used to live (under Strategies) so the
# muscle-memory path is not orphaned — a "see also", not a lens.
if "strategies" in _IA_SUB:
    _IA_SUB["strategies"].append(
        ("testing", "/dash/testing", "Strategy validation → Trust", None))
# sub-nav key -> the set of route `active` values that should highlight it.
_SUB_ALIAS = {ln.key: _LR.alias_set(ln.key) for ln in _LR.LENSES if ln.aliases}
# route `active` value -> its altitude (top-bar highlight + which sub-nav renders).
# DELIBERATELY no "stock" entry: the per-stock dossier is a destination, not a lens, so
# it must NOT claim Strategies›Positioning (the stock→stocks alias quirk — review §6 #5).
_ALT_OF: dict[str, str] = dict(_LR.ALT_OF)

# every href the IA homes (the no-loss known set) + the always-present utilities.
_KNOWN_HREFS = ({h for _k, h, _l in _IA_ALT}
                | {h for _its in _IA_SUB.values() for _k, h, _l, _g in _its}
                | {"/dash/coverage", "/dash/testing", "/dash/pat", "/dash/ratio",
                   "/dash/news", "/dash/leaders", "/dash/wolfe", "/dash/wolfe/scan",
                   # Hub merged into Strategist: its route stays live but must not be
                   # re-surfaced as "More" clutter on the top bar.
                   "/dash/strategies"})

_NAV_LINK_RE = re.compile(r'<a [^>]*href="([^"]+)">([^<]+)</a>')

_V2NAV_CSS = """<style>
.v2bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:2px}
.v2bar .wsnav{flex:0 1 auto}
.v2bar .wsnav a.on{color:#eaf1f9;border-bottom-color:#4d9dff}
.v2util{margin-left:auto;display:flex;align-items:center;gap:8px}
.v2util a,.v2util .v2askpat{font:inherit;font-size:12.5px;cursor:pointer;text-decoration:none;
  border:1px solid #27384a;background:#0b0f17;color:#9bb0c6;border-radius:8px;padding:6px 11px}
.v2util a.on,.v2util a:hover,.v2util .v2askpat:hover{border-color:#4d9dff;color:#eaf1f9}
/* Trust = the institutional lead wedge — a prominent teal chip, not a faint link. */
.v2util a.v2trust{border-color:#2f6f63;background:#11221e;color:#dcf6ee;font-weight:600}
.v2util a.v2trust::before{content:"✓ ";color:#34e0d6;font-weight:700}
.v2util a.v2trust:hover{border-color:#34e0d6;color:#eafff9}
.v2askpat kbd{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;background:#18222f;
  border:1px solid #27384a;border-radius:4px;padding:1px 5px;margin-left:6px;color:#9bb0c6}
.v2subnav{display:flex;gap:4px;flex-wrap:wrap;padding:7px 0 0;margin:0 0 4px;
  border-bottom:1px solid #1c2937;overflow-x:auto}
.v2subnav a{font-size:12.5px;color:#9bb0c6;text-decoration:none;padding:5px 10px;
  border-radius:7px 7px 0 0;white-space:nowrap}
.v2subnav a:hover{color:#eaf1f9;background:#111824}
.v2subnav a.on{color:#eaf1f9;background:#111824;font-weight:600;border-bottom:2px solid #4d9dff}
.v2subnav .sgrp{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  color:#5f7488;padding:5px 4px 5px 10px;align-self:center;white-space:nowrap;border-left:1px solid #1c2937}
.v2subnav .sgrp:first-child{border-left:0;padding-left:2px}
/* ── responsive: phone-usable chrome (the altitude bar scrolls, the utilities compact) ── */
@media (max-width:640px){
  .v2bar{gap:6px;flex-wrap:nowrap}
  .v2bar .wsnav{overflow-x:auto;flex:1 1 auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .v2bar .wsnav::-webkit-scrollbar{display:none}
  .v2bar .wsnav a{padding:10px 11px}            /* ≥40px touch target */
  .v2util{gap:5px;flex:none}
  .v2util a,.v2util .v2askpat{padding:9px 10px;font-size:12px}
  .v2askpat kbd{display:none}                    /* no ⌘ key on a phone */
  .v2subnav{padding-top:5px}
  .v2subnav a{padding:8px 11px}
}
</style>"""


def _route_paths(app) -> set[str]:
    out: set[str] = set()
    for r in getattr(app, "routes", []):
        p = getattr(r, "path", None)
        if p:
            out.add(p)
    return out


def _mount_routers(app) -> None:
    """include_router for each v2 view module, skipping any already present."""
    have = _route_paths(app)
    for desc, mod_path, sample in _ROUTER_SPECS:
        try:
            if sample in have:
                continue
            mod = importlib.import_module(mod_path)
            app.include_router(mod.router)
            have = _route_paths(app)
        except Exception as e:  # noqa: BLE001 — a bad module must never be fatal
            log.warning("v2 router skipped (%s): %s", desc, e)


def _mount_v1(app) -> None:
    """Mount the /v1 service layer (the compliance/data-feed + SDK/MCP bus face)."""
    try:
        if "/v1" in _route_paths(app):
            return
        from src.api.v1 import build_app  # local import: optional dependency

        app.mount("/v1", build_app())
    except Exception as e:  # noqa: BLE001
        log.warning("v2 /v1 mount skipped: %s", e)


def _altitude_of(active) -> str | None:
    """Which altitude (markets/screener/strategies/tracker), the 'trust' utility, or
    None, the given route `active` value belongs to."""
    a = (active or "").strip().lower()
    if a in _ALT_OF:
        return _ALT_OF[a]
    # The per-stock dossier is a DESTINATION, not a lens — it must claim no altitude
    # (legacy dashboard._WS maps "stock"->"strategies", which wrongly lit Strategies›
    # Positioning). Override that here so a per-stock everything-page highlights nothing.
    if a == "stock":
        return None
    try:
        import src.web.dashboard as D
        ws = D._WS.get(a, a)
        if ws == "themes":
            return "screener"
        if ws in ("markets", "screener", "strategies", "tracker", "trust"):
            return ws
    except Exception:  # noqa: BLE001
        pass
    return None


def _install_nav() -> None:
    """Replace dashboard._nav (at runtime) with the canonical 4-altitude IA chrome:
    a clean top bar + Ask-Pat/Trust utilities + a contextual sub-nav, so lenses live
    UNDER altitudes instead of cluttering the top bar. Gate-safe, reversible, no-loss."""
    import src.web.dashboard as D

    if getattr(D, _NAV_SENTINEL, False):
        return
    if not hasattr(D, "_nav"):
        log.warning("v2 nav skipped: dashboard._nav not found")
        return
    orig_nav = D._nav

    # highlight hints for any other dashboard code path that reads _WS — kept in sync
    # with the registry IA: leaders→Markets (RS is Markets content), testing→Trust.
    try:
        D._WS.update({"coverage": "trust", "rs-hub": "markets", "wire": "markets",
                      "news": "markets", "participants": "markets", "leaders": "markets",
                      "growth": "strategies", "wolfe": "strategies", "testing": "trust"})
    except Exception as e:  # noqa: BLE001
        log.warning("v2 _WS update skipped: %s", e)

    def _wrapped_nav(active):
        alt = _altitude_of(active)
        _aria_cur = ' aria-current="page"'   # standalone (no backslash in any f-string expr)
        tabs = "".join(
            f'<a class="{"on" if alt == k else ""}" href="{h}"{_aria_cur if alt == k else ""}>{lbl}</a>'
            for k, h, lbl in _IA_ALT)
        # NO-LOSS: any destination the original nav exposed that the IA doesn't home
        # is preserved in a trailing "More" group, so a future route is never dropped.
        extra, seen = "", set()
        try:
            unknown = []
            for href, label in _NAV_LINK_RE.findall(orig_nav(active)):
                if href not in _KNOWN_HREFS and href not in seen:
                    seen.add(href)
                    unknown.append((href, label))
            if unknown:
                extra = "".join(f'<a href="{h}">{l}</a>' for h, l in unknown)
        except Exception:  # noqa: BLE001
            extra = ""
        util = ('<div class="v2util">'
                f'<a class="v2trust{" on" if alt == "trust" else ""}" href="/dash/coverage" '
                'title="Trust — data coverage, provenance &amp; strategy validation">Trust</a>'
                '<button class="v2askpat" type="button" data-cmdk>Ask Pat <kbd>⌘K</kbd></button>'
                '</div>')
        top = (f'<div class="v2bar"><nav class="wsnav v2nav" aria-label="Primary">'
               f'{tabs}{extra}</nav>{util}</div>')
        sub = ""
        items = _IA_SUB.get(alt)
        if items:
            parts, last_group = [], None
            for k, h, lbl, group in items:
                if group and group != last_group:        # render the heading once per run
                    parts.append(f'<span class="sgrp">{group}</span>')
                last_group = group
                on = "on" if (active == k or active in _SUB_ALIAS.get(k, {k})) else ""
                parts.append(f'<a class="{on}" href="{h}">{lbl}</a>')
            sub = ('<div class="v2subnav" role="navigation" aria-label="Section">'
                   f'{"".join(parts)}</div>')
        out = _V2NAV_CSS + top + sub
        try:
            from src.web import ui_kit as _K
            out += _K.cmdk_overlay()
        except Exception:  # noqa: BLE001 — the overlay is additive; never break the nav
            pass
        return out

    D._nav = _wrapped_nav
    # our nav renders its own sub-nav; neutralise the legacy _subnav to avoid a double.
    if hasattr(D, "_subnav"):
        try:
            D._subnav = lambda active="": ""
        except Exception:  # noqa: BLE001
            pass
    setattr(D, _NAV_SENTINEL, True)


def site_nav(active: str = ""):
    """The nav destination list for the v2 (ui_kit) chrome (e.g. Coverage): the four
    altitudes + the Trust utility, highlight-aware. ONE IA, two renderers."""
    alt = _altitude_of(active)
    items = [(h, lbl, alt == k) for k, h, lbl in _IA_ALT]
    items.append(("/dash/coverage", "Trust", alt == "trust"))
    return items


def native_subnav(active: str = "") -> str:
    """Render the contextual sub-nav for a page as the NATIVE ui_kit `uk-sub` strip —
    the SAME registry-driven lens list (`_IA_SUB`/`_altitude_of`/`_SUB_ALIAS`) the legacy
    `.v2subnav` consumes, but in the native markup so a legacy `_shell` page can carry the
    identical sub-nav to the native pages (Lane M1: header unification). Returns '' when
    the active page's altitude has no sub-nav (home/dossier) — caller renders no strip.

    Markup mirrors `ui_kit.subnav([...])`: a `<div class="uk-sub">` of `<a>` items with a
    leading `<span class="grp">` heading per group run. Dependency-light (only `ui_kit.esc`
    for escaping, best-effort); defensive — any failure returns ''."""
    try:
        from src.web import ui_kit as _K
        _esc = _K.esc
    except Exception:  # noqa: BLE001
        def _esc(s):  # minimal fallback escaper
            return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    try:
        alt = _altitude_of(active)
        items = _IA_SUB.get(alt)
        if not items:
            return ""
        parts, last_group = [], None
        for k, h, lbl, group in items:
            if group and group != last_group:
                parts.append(f'<span class="grp">{_esc(group)}</span>')
            last_group = group
            on = "on" if (active == k or active in _SUB_ALIAS.get(k, {k})) else ""
            parts.append(f'<a class="{on}" href="{_esc(h)}">{_esc(lbl)}</a>')
        return f'<div class="uk-sub" role="navigation" aria-label="Section">{"".join(parts)}</div>'
    except Exception as e:  # noqa: BLE001 — sub-nav is chrome; never fatal
        log.warning("native_subnav skipped: %s", e)
        return ""


def _install_skin() -> None:
    """Reskin the legacy dashboard._shell pages into the ui_kit language (Track A) —
    every page (Markets/Screener/Strategies/Tracker/stock/strategy lenses) picks up the
    cyan-dot logo, the Ask-Pat hint and the v2 card+table palette. Defensive + idempotent
    (shell_skin.install owns the sentinel); a failure leaves the legacy chrome intact."""
    try:
        from src.web import shell_skin
        shell_skin.install()
    except Exception as e:  # noqa: BLE001 — the skin is additive; never break the nav
        log.warning("v2 shell skin skipped: %s", e)


def wire(app):
    """Mount the v2 routes + install the canonical nav + reskin the legacy pages.
    Idempotent + defensive."""
    _mount_routers(app)
    _mount_v1(app)
    try:
        _install_nav()
    except Exception as e:  # noqa: BLE001 — nav install must never break import
        log.warning("v2 nav install skipped: %s", e)
    _install_skin()
    return app


def _selftest() -> int:
    """Mount on a throwaway app + assert the clean IA renders, is no-loss, idempotent."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import src.web.dashboard as D

    app = FastAPI()
    app.include_router(D.router)
    wire(app)
    wire(app)  # idempotent

    c = TestClient(app)
    for path in ("/dash/coverage", "/dash/rs-hub", "/dash/wire", "/dash/news"):
        assert c.get(path).status_code == 200, path

    # Every router in _ROUTER_SPECS must actually be MOUNTED by wire() (route present).
    # Page-render liveness of the data-dependent ones (growth/testing read the research
    # DB) is verified separately on the VPS — here we assert the route exists, not 200.
    mounted = _route_paths(app)
    for _desc, _mod, sample in _ROUTER_SPECS:
        assert sample in mounted, f"router spec not mounted: {sample}"

    # Test the nav RENDERER directly (no page render -> no data/route-mount dependency;
    # route liveness of every sub-nav target is verified separately on the VPS).
    home = D._nav("dash")
    for _k, h, lbl in _IA_ALT:                       # the 4 altitudes present
        assert f'href="{h}"' in home, f"altitude missing: {lbl}"
    assert "v2askpat" in home and 'href="/dash/coverage"' in home, "utilities missing"
    assert home.count('class="v2bar"') == 1, "nav rendered more than once (not idempotent)"
    # the OLD clutter must be GONE from the top bar (growth/wolfe/themes are now sub-nav)
    top_bar = home.split('class="v2subnav"')[0]
    for gone in ('>Growth<', '>Wolfe wave<', '>Themes<', '>News<', '>Relative strength<'):
        assert gone not in top_bar, f"lens still on top bar: {gone}"

    # every altitude (incl. Trust) renders its lenses as a contextual sub-nav (no-loss).
    _probe = {"tracker": "dashboard", "trust": "coverage"}
    for alt, items in _IA_SUB.items():
        nav = D._nav(_probe.get(alt, alt))
        for _k, h, _l, _g in items:
            assert f'href="{h}"' in nav, f"{alt} sub-nav missing {h}"

    # ── the DECIDED Scope × Lens IA (nav-ia-DECISIONS §1) is wired correctly ──
    mkt = D._nav("markets")
    assert 'href="/dash/leaders"' in mkt, "Leaders must be a Markets sub-nav entry"
    strat = D._nav("strategist")
    # Scope the IA assertions to the SUB-NAV strip (the cmdk ⌘K palette legitimately
    # still lists Wolfe/Hub as searchable destinations — they stay reachable, just not
    # as Strategies sub-nav tabs). The strip is the v2subnav block.
    _strat_strip = strat.split('class="v2subnav"', 1)[-1].split("</div>", 1)[0]
    assert 'href="/dash/leaders"' not in _strat_strip, "Leaders must NOT be under Strategies"
    assert 'href="/dash/strategies"' not in _strat_strip, "Hub must be merged into Strategist"
    assert '>Accumulation<' in _strat_strip, "Positioning+MEP must group under 'Accumulation'"
    for gone in ('>Wolfe', '/dash/wolfe'):           # Wolfe demoted to chart overlay
        assert gone not in _strat_strip, f"Wolfe must be off the Strategies sub-nav: {gone}"
    trust = D._nav("coverage")
    assert 'href="/dash/coverage"' in trust and 'href="/dash/testing"' in trust, \
        "Trust sub-nav must wire Coverage + Strategy validation(/dash/testing)"
    assert '>Strategy validation<' in trust, "Trust slot must label /dash/testing"
    # the per-stock dossier must NOT light Strategies›Positioning (the alias-quirk fix).
    assert _altitude_of("stock") is None, "stock dossier must not claim an altitude"

    print("v2_surfaces selftest OK — Scope x Lens IA: Leaders->Markets, Hub merged into "
          "Strategist, Accumulation group, Wolfe overlay-only, Trust sub-nav, dossier "
          "claims no altitude; no-loss; idempotent")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
