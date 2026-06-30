"""
nav_links.py — the CROSS-PAGE NAVIGATION GLUE (NEW, Lane N3).

What this module is for
-----------------------
Lane N1 built the single source of truth — `src.web.lens_registry` — and rewired the
nav from it. The Scope × Lens structure is now *correct*, but it is not yet *navigable*:
the lateral glue is missing. A lens manifests at ~5 surfaces (a market-wide list, a
screener column, a dossier tab, a chart overlay) but those surfaces are islands — you
cannot hop from one to the next, and a per-stock dossier carries no breadcrumb telling
you where in `Markets → Sector → Stock` you landed.

This module supplies that glue, ALL of it generated from the registry so it cannot drift
(docs/navigation-and-structure-review.md §5, patterns #1–#4; docs/nav-ia-DECISIONS-and-
prompts.md §2):

  1. Canonical link helpers that CARRY the lens as the dossier-tab anchor —
     `stock_link(sym, lens)` → `/dash/stock?sym=…#<dossier_tab>`, plus `index_link`,
     `theme_link`. (lens_registry.stock_link is the minimal seed; this is the full rail.)
  2. A `Markets → Sector → Stock` (and `Theme → Stock`) breadcrumb component.
  3. Lateral "see this lens elsewhere" link rows — for each dossier lens tab: its
     market-wide list · open in the Screener (the lens column) · on the chart overlay.

How it is installed (the decoupled, no-edit pattern)
----------------------------------------------------
EXACTLY the proven shell_skin / v2_surfaces runtime-injection pattern. We do NOT edit
the contended `dashboard.py` / `cockpit.py` bodies. Instead `install()` monkeypatches
`dashboard._shell(title, body, active, …)` — the single function every legacy page and
all of cockpit render through — and POST-PROCESSES the `body` before it is wrapped in the
page chrome, keyed off the `active` route value (which `_shell` already receives). A
dashboard.py redeploy therefore cannot wipe the glue, and we never touch a frozen file.

Composition with shell_skin: both wrap `_shell`; order does not matter. We inject into
the *body argument* (semantic markup); shell_skin retints the *assembled html*. The
sentinel + a body marker make each idempotent, so wrapping in either order, any number of
times, yields one breadcrumb and one rail.

Properties (the house rules): DEFENSIVE (every step try/except → on any failure the
ORIGINAL body/page is returned; a page must never 500 because of the glue) · IDEMPOTENT
(sentinel on the module + a per-body marker) · NO-LOSS (purely additive; no datum, link
or route removed; sacred routes /dash/ratio,/dash/rrg,/dash/compare untouched) · ADDITIVE
+ REVERSIBLE (don't call install(), or restore the file). Descriptive-only.

Isolation: imports ONLY `lens_registry` (dependency-free) at module load; reaches
`dashboard` lazily inside install() to monkeypatch, never at import.
"""
from __future__ import annotations

import logging
import re

from src.web import lens_registry as _LR

log = logging.getLogger("hermes.v2")

# set on the dashboard module once _shell has been wrapped (no double-wrap).
_GLUE_SENTINEL = "_v2_nav_glue_installed"
# a marker placed in the injected body so an already-glued body is never re-glued
# (idempotent regardless of shell_skin wrap order).
_GLUE_MARKER = "<!-- nav-glue v1 -->"


# ── escaping (self-contained — never import private dashboard helpers at load) ────
def _esc(s: object) -> str:
    """Minimal HTML-attribute/text escape for the symbols/labels we interpolate.
    Self-contained so this module imports nothing from the web layer at load time."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _qsym(sym: object) -> str:
    """URL-safe symbol for a query string. NSE symbols are [A-Z0-9&-]; we percent-encode
    the few specials defensively without pulling urllib for the hot path.
    CL-CHR-5: also encode `?`, `=`, `/` — a `?`/`=` would start a new query param and `/`
    a new path segment, so an odd index/theme name could otherwise corrupt the URL.
    `%` MUST stay first so we don't double-encode the escapes we just introduced."""
    s = str(sym).strip()
    return (s.replace("%", "%25").replace("&", "%26").replace("#", "%23")
            .replace("+", "%2B").replace(" ", "%20").replace('"', "%22")
            .replace("?", "%3F").replace("=", "%3D").replace("/", "%2F"))


# ── 1. canonical link helpers (lens carried as the dossier-tab anchor) ───────────
def stock_link(sym: str, lens: str | None = None) -> str:
    """Canonical dossier link that carries the clicked lens to its dossier tab:
    `stock_link("INFY", "mep")` → `/dash/stock?sym=INFY#mep`. The lens→tab mapping
    comes from the registry, so a screener MEP cell, a Leaders row and a CCI tile each
    land on the lens that was clicked (review §5 #2), not generic price. Falls back to
    the plain dossier when the lens has no dossier tab (e.g. Launchpad)."""
    base = f"/dash/stock?sym={_qsym(sym)}"
    if not lens:
        return base
    ln = _LR.BY_KEY.get(lens)
    tab = ln.dossier_tab if ln else None
    return f"{base}#{tab}" if tab else base


def index_link(idx: str) -> str:
    """Canonical link to an index/sector detail page (`/dash/index?idx=…`)."""
    return f"/dash/index?idx={_qsym(idx)}"


def theme_link(tag: str) -> str:
    """Canonical link to one theme's participants drill (`/dash/theme?tag=…`)."""
    return f"/dash/theme?tag={_qsym(tag)}"


# ── 2. breadcrumb component ──────────────────────────────────────────────────────
_CRUMB_CSS = """<style>
/* The trail must NEVER push the page past the viewport edge (esp. at 380px, where a
   long sector/symbol crumb would overflow). It still WRAPS to a second line when there
   are several short items; if a single token is wider than the box it SCROLLS inside
   itself (overflow-x:auto + max-width:100%) instead of pushing the page. min-width:0
   lets the flex children shrink; overflow-wrap on links breaks an over-long token. */
.ngcrumb{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:12px;
  color:#5f7488;margin:0 0 8px;padding:0;max-width:100%;min-width:0;overflow-x:auto;
  -webkit-overflow-scrolling:touch}
.ngcrumb a{color:#9bb0c6;text-decoration:none;border-bottom:1px solid transparent;padding:1px 0;
  overflow-wrap:anywhere;min-width:0}
.ngcrumb a:hover{color:#eaf1f9;border-bottom-color:#4d9dff}
.ngcrumb .sep{color:#3a4a5c;font-size:11px;flex:none}
.ngcrumb .here{color:#eaf1f9;font-weight:600;overflow-wrap:anywhere;min-width:0}
/* The lateral rail shares the same risk: its chips are white-space:nowrap, so at 380px
   they would overflow the page. Contain them to scroll inside the rail box. */
.nglat{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;
  color:#5f7488;margin:8px 0 4px;padding:8px 11px;border:1px solid #1c2937;
  border-radius:9px;background:#0e1620;max-width:100%;min-width:0;overflow-x:auto;
  -webkit-overflow-scrolling:touch}
.nglat .lbl{color:#5f7488;text-transform:uppercase;letter-spacing:.05em;font-size:10.5px}
.nglat a{color:#9bb0c6;text-decoration:none;border:1px solid #27384a;border-radius:7px;
  padding:3px 9px;background:#0b0f17;white-space:nowrap}
.nglat a:hover{border-color:#4d9dff;color:#eaf1f9}
.nglat .sep{color:#28384a}
</style>"""


def breadcrumb(trail: list[tuple[str | None, str]]) -> str:
    """Render a structured breadcrumb from a trail of `(href_or_None, label)` steps.
    The last step (href None) renders as the current location (`.here`), the rest as
    links. Empty/whitespace labels are skipped so a missing middle level collapses
    cleanly rather than leaving a dangling separator."""
    steps = [(h, lbl) for (h, lbl) in trail if (lbl or "").strip()]
    if not steps:
        return ""
    parts = []
    for i, (href, label) in enumerate(steps):
        if i:
            parts.append('<span class="sep">&rsaquo;</span>')
        if href:
            parts.append(f'<a href="{_esc(href)}">{_esc(label)}</a>')
        else:
            parts.append(f'<span class="here">{_esc(label)}</span>')
    return f'<nav class="ngcrumb" aria-label="Breadcrumb">{"".join(parts)}</nav>'


def stock_breadcrumb(sym: str, sector: str | None = None) -> str:
    """The `Markets → Sector → Stock` drill trail for a stock dossier. When the sector
    is unknown (we post-process the rendered body and don't always have it), the chain
    degrades to `Markets → Sectors → <sym>` — still a real, climbable trail up to the
    altitude, never a dead end (the drill chain of review §5 #4)."""
    trail: list[tuple[str | None, str]] = [("/dash/markets", "Markets")]
    if sector and sector.strip():
        trail.append((index_link(sector), sector.strip()))
    else:
        trail.append(("/dash/sectors", "Sectors"))
    trail.append((None, sym))
    return breadcrumb(trail)


def index_breadcrumb(idx: str) -> str:
    """`Markets → <index>` for an index/sector detail page."""
    return breadcrumb([("/dash/markets", "Markets"), (None, idx)])


def theme_breadcrumb(tag: str) -> str:
    """`Screener → Themes → <tag>` for a theme participants page (themes live under
    the Screener altitude in the decided IA)."""
    return breadcrumb([("/dash/screener", "Screener"),
                       ("/dash/themes", "Themes"), (None, tag)])


# ── 3. lateral "see this lens elsewhere" rows (generated from the registry) ───────
# A dossier surfaces one tab per lens. For each lens that exists at multiple surfaces,
# offer the lateral hops the registry knows about: the market-wide LIST (lens.route),
# the SCREENER filtered to the lens column (lens.screener_col), and the per-stock CHART
# overlay (lens.overlay → the dossier price tab, where the overlay draws). This turns a
# lens's surfaces from islands into a loop (review §5 #3).
def _lens_lateral_links(lens_key: str, sym: str) -> list[tuple[str, str]]:
    """The (href, label) lateral hops for one lens on a stock's dossier."""
    ln = _LR.BY_KEY.get(lens_key)
    if ln is None:
        return []
    out: list[tuple[str, str]] = []
    if ln.route:                                   # the market-wide ranked list
        out.append((ln.route, "market-wide list"))
    if ln.screener_col:                            # the Screener, with this lens's columns
        # CL-CHR-2: the legacy /dash/screener honours only scope+limit and SILENTLY
        # DROPS ?lens=, so the old link landed on the unfiltered grid (a no-op filter
        # masquerading as one). Point at /dash/screen2 (the default Screen+) instead —
        # its labelled column-GROUP keys are EXACTLY screener_col (pos/mep/rs/cpr/cci/
        # qual), so the lens is a first-class, visible, labelled block there. No dead
        # query param promising a filter the screener never applies.
        out.append(("/dash/screen2", "open in Screener"))
    if ln.overlay:                                 # the chart overlay (the price tab)
        out.append((stock_link(sym), "on the chart"))
    return out


def lens_rail(lens_key: str, sym: str) -> str:
    """The lateral rail for one dossier lens tab — a single row of 'see this lens
    elsewhere' links. Returns '' when the lens has no other surfaces (nothing to hop to),
    so a lens with no list/screener/overlay (e.g. a synthesis) shows no empty rail."""
    links = _lens_lateral_links(lens_key, sym)
    if not links:
        return ""
    ln = _LR.BY_KEY.get(lens_key)
    label = (ln.label if ln else lens_key)
    parts = [f'<span class="lbl">{_esc(label)} elsewhere</span>']
    for i, (href, txt) in enumerate(links):
        if i:
            parts.append('<span class="sep">·</span>')
        parts.append(f'<a href="{_esc(href)}">{_esc(txt)}</a>')
    return f'<div class="nglat">{"".join(parts)}</div>'


# Tab-aware rails: hide every tagged rail by default and reveal ONLY the active dossier
# tab's rail. The default tab is Price (no lens → no rail), so the candle chart is no
# longer buried under 8 stacked "… elsewhere" rows (QA #5). A tiny script syncs rail
# visibility to the SAME tab control the dossier already wires (`#stabbar a[data-stab]`)
# + the initial hash; it only toggles display, composing with the dossier's own tab JS.
_RAILS_CSS = """<style>
#ngrails .nglat[data-ngtab]{display:none}
#ngrails .nglat[data-ngtab].ng-on{display:flex}
</style>"""
_RAILS_JS = """<script>(function(){
  var box=document.getElementById('ngrails'); if(!box) return;
  var bar=document.getElementById('stabbar');
  function sync(k){ box.querySelectorAll('.nglat[data-ngtab]').forEach(function(r){
    r.classList.toggle('ng-on', r.getAttribute('data-ngtab')===k); }); }
  function cur(){ var h=(location.hash||'').replace('#',''); return h||'price'; }
  if(bar){ bar.querySelectorAll('a[data-stab]').forEach(function(a){
    a.addEventListener('click', function(){ sync(a.getAttribute('data-stab')); }); }); }
  window.addEventListener('hashchange', function(){ sync(cur()); });
  sync(cur());
})();</script>"""


def dossier_lens_rails(sym: str) -> str:
    """The full set of lateral rails for a stock dossier — one row per registry lens
    that has a dossier tab AND at least one other surface. Each rail carries a
    `data-ngtab="<tab>"` attribute; they are wrapped in `#ngrails` and shown ONE AT A
    TIME — only the rail for the currently-open dossier tab is visible (the rest are
    `display:none`). The default Price tab has no lens rail, so the chart is not pushed
    down a wall of links (QA #5). Generated from the registry — a new lens with a dossier
    tab gets its rail automatically. Returns '' when no rail exists (caller injects
    nothing)."""
    rows = []
    seen_tabs: set[str] = set()
    for ln in _LR.LENSES:
        if not ln.dossier_tab or ln.dossier_tab in seen_tabs:
            continue
        seen_tabs.add(ln.dossier_tab)
        rail = lens_rail(ln.key, sym)
        if rail:
            rows.append(rail.replace('<div class="nglat">',
                                     f'<div class="nglat" data-ngtab="{_esc(ln.dossier_tab)}">', 1))
    if not rows:
        return ""
    return _RAILS_CSS + '<div id="ngrails">' + "".join(rows) + '</div>' + _RAILS_JS


# ── injection: post-process the _shell body per route ────────────────────────────
# extract the symbol from the stock dossier's <h2> header (cockpit/dashboard render it
# as `<h2>SYM <span class="pill ...`). Self-protecting: no match → no injection.
_STOCK_H2_RE = re.compile(r'<h2>([A-Z0-9&._-]{1,20})\s*<span class="pill ')
# the stock dossier is unambiguously identified by its tab bar id.
_STABBAR = 'id="stabbar"'
# extract the index/sector name from the index detail header (cockpit.render_index_detail:
# `<h2 style="margin-top:2px">NAME <span class="sub" ...>broad / size index · …` or `… sector · …`).
_INDEX_H2_RE = re.compile(
    r'<h2 style="margin-top:2px">([^<]{1,60}?)\s*<span class="sub"[^>]*>\s*'
    r'(?:broad / size index|sector)\b')
# extract the theme name from the theme participants header
# (cockpit.render_theme_detail: `<h2 style="margin-top:2px">NAME <span class="sub" style="margin:0">BLURB`).
# CL-CHR-10: the old pattern shared its entire prefix with _INDEX_H2_RE (`<h2 style=
# "margin-top:2px">…<span class="sub"`), so it was only the route `active` dispatch + the
# call-site "/dash/theme?tag=" guard keeping them apart. Narrow it to the theme header's
# exact `<span class="sub" style="margin:0">` so it can't latch a differently-styled <h2>
# even if the active dispatch ever widened. (Still routed only on active in themes/theme.)
_THEME_H2_RE = re.compile(r'<h2 style="margin-top:2px">([^<]{1,60}?)\s*<span class="sub" style="margin:0">')


def _inject_body(body: str, active: str) -> str:
    """Insert the breadcrumb (+ the dossier lateral rails) into a page body, keyed off
    the route `active` value. Idempotent (the body marker), defensive (any failure → the
    original body). Only the three drill-destination pages are touched; every other page
    is returned unchanged (no-loss)."""
    try:
        if not body or _GLUE_MARKER in body:
            return body
        a = (active or "").strip().lower()

        # ── stock dossier: Markets → Sectors → <sym> breadcrumb + lateral rails ──
        if a == "stock" and _STABBAR in body:
            m = _STOCK_H2_RE.search(body)
            if not m:
                return body
            sym = m.group(1)
            crumb = stock_breadcrumb(sym)
            rails = dossier_lens_rails(sym)
            block = _GLUE_MARKER + _CRUMB_CSS + crumb
            # breadcrumb goes ABOVE the <h2>; rails go right AFTER the tab bar so the
            # "see this lens elsewhere" loop sits with the lenses it links.
            out = body.replace(m.group(0), block + m.group(0), 1)
            if rails:
                # insert after the tab bar's closing </div> (the first one following stabbar).
                idx = out.find(_STABBAR)
                close = out.find("</div>", idx)
                if close != -1:
                    cut = close + len("</div>")
                    out = out[:cut] + rails + out[cut:]
            return out

        # ── index / sector detail: Markets → <index> breadcrumb ──
        if a in ("markets", "index"):
            m = _INDEX_H2_RE.search(body)
            if m and ("/dash/sectors" in body or "Inside the index" in body):
                idx = m.group(1).strip()
                block = _GLUE_MARKER + _CRUMB_CSS + index_breadcrumb(idx)
                return body.replace(m.group(0), block + m.group(0), 1)
            return body

        # ── theme participants: Screener → Themes → <tag> breadcrumb ──
        if a in ("themes", "theme"):
            # only the single-theme drill (it self-links to /dash/stock and carries the
            # theme header); the Themes browse index has its own header we leave alone.
            if "/dash/theme?tag=" in body or "Themes · " in body:
                m = _THEME_H2_RE.search(body)
                if m:
                    tag = m.group(1).strip()
                    if tag and tag.lower() != "themes":
                        block = _GLUE_MARKER + _CRUMB_CSS + theme_breadcrumb(tag)
                        return body.replace(m.group(0), block + m.group(0), 1)
            return body

        return body
    except Exception as e:  # noqa: BLE001 — the glue must never break a page
        log.warning("nav_links inject skipped: %s", e)
        return body


def install() -> bool:
    """Monkeypatch `dashboard._shell` so every page body is post-processed with the
    breadcrumb + lateral glue before it is wrapped in the chrome. Idempotent (sentinel),
    defensive (never raises). Composes with shell_skin in either install order. Returns
    True if the glue is in place (newly or already)."""
    try:
        import src.web.dashboard as D
    except Exception as e:  # noqa: BLE001
        log.warning("nav_links install skipped: dashboard import failed: %s", e)
        return False
    if getattr(D, _GLUE_SENTINEL, False):
        return True
    orig_shell = getattr(D, "_shell", None)
    if not callable(orig_shell):
        log.warning("nav_links install skipped: dashboard._shell not found")
        return False

    def _glued_shell(title, body, active, *args, **kwargs):
        try:
            body = _inject_body(body, active)
        except Exception:  # noqa: BLE001 — defensive double-guard
            pass
        return orig_shell(title, body, active, *args, **kwargs)

    _glued_shell.__wrapped__ = orig_shell  # type: ignore[attr-defined]
    D._shell = _glued_shell

    # Rebind every OTHER module that captured `_shell` by reference at import time
    # (the same sweep shell_skin does — rrg_view / rsband_view / participants_view /
    # wolfe_view do `from src.web.dashboard import _shell`). Patching dashboard._shell
    # alone does not reach those; repoint any module-level `_shell` that IS the original.
    import sys
    rebound = 0
    for _name, _mod in list(sys.modules.items()):
        if _mod is None or _mod is D:
            continue
        try:
            if getattr(_mod, "_shell", None) is orig_shell:
                _mod._shell = _glued_shell
                rebound += 1
        except Exception:  # noqa: BLE001
            continue

    setattr(D, _GLUE_SENTINEL, True)
    log.info("nav_links installed — breadcrumbs + lateral lens rails (+%d imported refs)", rebound)
    return True


def _selftest() -> int:
    """Exercise the helpers + the body injection against representative page bodies;
    assert it's correct, no-loss, idempotent, and defensive."""
    # ── link helpers carry the lens via the registry ──
    assert stock_link("INFY", "mep") == "/dash/stock?sym=INFY#mep"
    assert stock_link("INFY", "cpr") == "/dash/stock?sym=INFY#cpr"
    assert stock_link("INFY", "launchpad") == "/dash/stock?sym=INFY"   # no dossier tab
    assert stock_link("INFY") == "/dash/stock?sym=INFY"
    assert index_link("NIFTY IT") == "/dash/index?idx=NIFTY%20IT"
    assert theme_link("Defence") == "/dash/theme?tag=Defence"

    # ── breadcrumb renders + degrades cleanly ──
    bc = stock_breadcrumb("INFY")
    assert 'href="/dash/markets"' in bc and 'href="/dash/sectors"' in bc and ">INFY<" in bc
    bc2 = stock_breadcrumb("INFY", "NIFTY IT")
    assert "/dash/index?idx=NIFTY%20IT" in bc2 and ">NIFTY IT<" in bc2 and "/dash/sectors" not in bc2
    assert index_breadcrumb("NIFTY BANK").count("<a ") == 1   # Markets link + the here-node
    assert ">Themes<" in theme_breadcrumb("Defence")

    # ── lateral rails are registry-generated ──
    mep_rail = lens_rail("mep", "INFY")
    # CL-CHR-2 (already shipped) pointed "open in Screener" at /dash/screen2 and dropped the
    # no-op `?lens=` param; the rail now carries the market-wide list + the screen2 hop + the
    # chart overlay. (Stale `lens=mep` assertion removed to match the shipped behaviour.)
    assert "/dash/mep" in mep_rail and "/dash/screen2" in mep_rail and ">on the chart<" in mep_rail
    assert lens_rail("conviction", "INFY") == "" or "market-wide list" in lens_rail("conviction", "INFY")
    rails = dossier_lens_rails("INFY")
    for tab in ("pos", "mep", "rs", "cpr", "cci"):
        assert f'data-ngtab="{tab}"' in rails, f"missing dossier rail for tab {tab}"

    # ── body injection: a representative stock dossier body ──
    stock_body = ('<div class="sub">x</div>'
                  '<div class="tabbar" id="stabbar"><a href="#price">Price</a></div>'
                  '<h2>INFY <span class="pill p-A">A</span> · Infosys</h2>'
                  '<div class="tabpane" data-tab="price">chart</div>')
    out = _inject_body(stock_body, "stock")
    assert _GLUE_MARKER in out and 'class="ngcrumb"' in out, "stock breadcrumb not injected"
    assert ">INFY<" in out and 'class="nglat"' in out, "stock rails not injected"
    assert "Infosys" in out and "chart" in out, "stock body data lost (NOT no-loss)"
    assert _inject_body(out, "stock") == out, "stock injection not idempotent"

    # ── index detail body ──
    index_body = ('<div class="sub">&#8592; <a href="/dash/markets">Markets</a> · '
                  '<a href="/dash/sectors">Sectors</a></div>'
                  '<h2 style="margin-top:2px">NIFTY BANK <span class="sub" style="margin:0">'
                  'sector · 2026-06-28</span></h2><div>Inside the index</div>')
    iout = _inject_body(index_body, "markets")
    assert 'class="ngcrumb"' in iout and ">NIFTY BANK<" in iout, "index breadcrumb not injected"
    assert "Inside the index" in iout, "index body data lost"
    assert _inject_body(iout, "markets") == iout, "index injection not idempotent"

    # ── theme detail body ──
    theme_body = ('<h2 style="margin-top:2px">Defence <span class="sub" style="margin:0">'
                  'theme participants</span></h2>'
                  '<a href="/dash/theme?tag=Defence">x</a>')
    tout = _inject_body(theme_body, "theme")
    assert 'class="ngcrumb"' in tout and ">Defence<" in tout, "theme breadcrumb not injected"

    # ── pages that are NOT drill destinations are untouched (no-loss) ──
    plain = '<div class="card"><h2>Screener</h2><table></table></div>'
    assert _inject_body(plain, "screener") == plain, "non-destination page mutated"
    # a stock-like <h2> on a NON-stock page (no stabbar) must not trigger the stock path
    assert _GLUE_MARKER not in _inject_body('<h2>INFY <span class="pill p-A">A</span></h2>', "leaders")

    print("nav_links selftest OK — link helpers carry the lens; breadcrumbs + lateral "
          "rails inject; no-loss; idempotent; defensive; registry-driven")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
