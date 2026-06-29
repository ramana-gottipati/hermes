"""shell_skin.py — runtime reskin of the legacy dashboard._shell pages into the v2
(ui_kit) visual language, WITHOUT editing dashboard.py / cockpit.py.

The problem (docs/ui-restore-and-migration-TRACKER.md Track A): only the Trust /
Coverage surface is built on the v2 design system (`ui_kit`). Markets, Screener,
Strategies, Tracker, stock and every strategy page still render through
`dashboard._shell` — the old chrome (`pat·e·arn` green-"e" logo, a "search ticker…"
box) and the old `#0e1116 / #161b22 / #30363d` card+table palette. Same site, two
looks, two logos.

The fix, decoupled (the proven v2_surfaces monkeypatch pattern): every legacy page —
and all of cockpit — renders by calling `dashboard._shell(title, body, active, …)`.
We wrap that single function at runtime so its output is post-processed into the
ui_kit language:

  * a CSS OVERLAY (`skin_css`) scoped under ``body.uk-skin`` is injected after the
    legacy ``_BASE_CSS``. Every rule is scoped by a class, so it outranks the bare
    element / single-class base rules on specificity — the reskin wins regardless of
    source order, and NOTHING in the body markup changes (no-loss, additive).
  * the logo is recoloured to the cyan-dot ``patearn`` mark (no green "e") — CSS only,
    no fragile HTML matching.
  * the "search ticker…" form is swapped for the ui_kit "Search or ask Pat ⌘K" hint,
    which opens the global Cmd-K overlay the v2 nav already injects on every page
    (so the ticker-jump function is preserved, not lost).

Properties (the house rules): DEFENSIVE (every step try/except, a failure returns the
original html — a page must never 500 because of the skin) · IDEMPOTENT (sentinel +
a marker check) · NO-LOSS (CSS retint only; the sacred routes, every body, every
datum untouched) · ADDITIVE + REVERSIBLE (don't call install(), or restore the file).

Isolation: imports ONLY ``ui_kit`` (the dependency-free design system) for the cmdk
hint; it reaches ``dashboard`` lazily at install() time to monkeypatch, never at
import. Wired durably from ``v2_surfaces.wire(app)`` (one line) so a redeploy that
re-applies the v2 hook re-applies the skin too.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger("hermes.v2")

# set on the dashboard module once _shell has been wrapped (no double-wrap).
_SKIN_SENTINEL = "_v2_shell_skinned"
# a marker placed in the <head> so an already-skinned html string is never reskinned.
_SKIN_MARKER = "/* uk-skin v1 */"


# ── the reskin stylesheet — legacy classes retinted to the ui_kit tokens ──────
# Scoped under `body.uk-skin` so each rule's specificity (0,1,x)+ beats the base
# `_BASE_CSS` element/single-class rules; the v2 chrome (.v2bar/.v2subnav) is retinted
# by v2_surfaces itself. We retint COLOUR + surface only — never layout/sticky/z-index
# (so the carefully-tuned frozen-pane grid keeps its geometry).
_SKIN_CSS = """<style>""" + _SKIN_MARKER + """
/* ── palette anchor: the instrument background + ink ── */
body.uk-skin{
  background:
    radial-gradient(1100px 560px at 82% -12%, rgba(77,157,255,.07), transparent 60%),
    radial-gradient(860px 480px at -8% 8%, rgba(52,224,214,.05), transparent 55%),
    #0b0f17 !important;
  color:#eaf1f9;
  -webkit-font-smoothing:antialiased;
  font-feature-settings:'tnum' 1,'cv01' 1;
}
/* ── header / chrome ──
   Lane M1: the legacy two-row <header> (hrow1/hrow2/hrow3, the .v2bar nav, the brand
   logo, .hback, .uk-trustlink) is REPLACED at runtime by the native single-row ui_kit
   topbar (`.uk-top` + `.uk-sub`), which is styled by ui_kit.css() (injected after this
   block, so its top-level `.uk-*` rules win). No header rules are needed here anymore —
   the few defensive remnants below only matter if the header swap fell back to legacy
   (a <header> still present): keep the chrome dark + the back chip on-brand. */
body.uk-skin header{
  background:linear-gradient(180deg,rgba(17,24,36,.92),rgba(11,15,23,.66));
  border-bottom:1px solid #1c2937;backdrop-filter:blur(12px);
}
body.uk-skin .hback{border:1px solid #27384a;color:#9bb0c6;border-radius:8px}
body.uk-skin .hback:hover{border-color:#4d9dff;background:#111824}
/* M1 FOLLOW-UP (Ramana caught it): two legacy base rules leaked onto the new unified
   topbar's <nav class="uk-nav">, because they target the bare `nav`/`nav a` elements:
     nav   { position:fixed; bottom:0; left:0; right:0 }   (the old mobile bottom-bar)
     nav a { flex:1 1 0; text-align:center }                (the old justified tab row)
   → the fixed nav was lifted out of the header flex flow and overlaid the logo + search,
   and the tabs stretched edge-to-edge. Neutralise both for the topbar nav so the logo
   (left) + tabs (clustered) + search (right) lay out exactly like the native pages. */
body.uk-skin .uk-top .uk-nav{position:static;bottom:auto;left:auto;right:auto;background:none;border-top:0}
body.uk-skin .uk-top .uk-nav a{flex:0 0 auto;text-align:initial}
/* ── cards & boxes ── */
body.uk-skin .card,
body.uk-skin .kpi .box,
body.uk-skin .cprpanel,
body.uk-skin .scard,
body.uk-skin .maj,
body.uk-skin .chip{
  background:#111824;border:1px solid #1c2937;border-radius:12px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.045);
}
body.uk-skin .maj{border-left:3px solid #4d9dff}
body.uk-skin .scard{border-top:3px solid #1c2937}
body.uk-skin .scard.sc-POS{border-top-color:#4d9dff} body.uk-skin .scard.sc-RS{border-top-color:#3fd486}
body.uk-skin .scard.sc-QUAL{border-top-color:#f6b73c} body.uk-skin .scard.sc-CPR{border-top-color:#b18cff}
body.uk-skin .kpi .num,body.uk-skin .scard .ct,body.uk-skin .maj .nm{color:#eaf1f9}
body.uk-skin .kpi .lbl,body.uk-skin .scard .th,body.uk-skin .maj .rr,body.uk-skin .sub,body.uk-skin .ghdr{color:#9bb0c6}
body.uk-skin h2,body.uk-skin .scard .nm{color:#eaf1f9}
/* ── tables (colour only; layout untouched) ── */
body.uk-skin th{color:#7e90a8;border-bottom:1px solid #27384a}/* AA: was #5c6f84 (3.4:1) */
body.uk-skin td{border-bottom:1px solid #1c2937}
body.uk-skin .sym{color:#eaf1f9}
/* ── semantic ink ── */
body.uk-skin .pos{color:#3fd486} body.uk-skin .neg{color:#ff6a7a} body.uk-skin .mut{color:#7e90a8}/* AA */
body.uk-skin .grp{color:#4d9dff}
/* ── WCAG-AA (L2 W3): legacy classes hardcoding the too-dark greys #6e7681 (4.0:1) /
   #5f7488 (3.8:1) in the FROZEN bodies — caught here by class so they clear AA without
   editing dashboard.py/stock_chart.py. Mapped to the AA-safe --ink-3 (#7e90a8). Inline
   style="color:…" on a few chart-control labels (stock_chart.py) can't be reached by a
   class rule → flagged to L3. ── */
body.uk-skin .nglat .lbl,body.uk-skin .snap i,body.uk-skin .subnav a,body.uk-skin .add,
body.uk-skin .cp-none,body.uk-skin .trow .tb,body.uk-skin .tchip.more{color:var(--ink-3)}
/* ── empty / loading / error states → the polished native system look ──
   L2 Wave2 (state polish): legacy no-data blocks render a bare left-aligned
   `<div class="empty">No data…</div>` that reads like a broken fragment. Give the legacy
   `.empty` the native `uk-empty` treatment — centered column, a muted ○ glyph above the
   message, generous padding — so a no-data legacy page reads INTENTIONAL, matching the
   native ui_components.empty. (The full uk-empty/uk-error/uk-note/uk-skel/uk-spin system is
   now injected site-wide via skin_css(), so frozen bodies can also emit native states.) */
body.uk-skin .empty{display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:8px;text-align:center;color:var(--ink-3);padding:46px 20px;font-size:var(--fs-md);line-height:1.6}
body.uk-skin .empty::before{content:"\\25CB";font-size:30px;opacity:.55;line-height:1;margin-bottom:2px}
body.uk-skin .empty b{color:var(--ink-2);font-weight:600}
/* legacy inline status/error helpers map to the native note look */
body.uk-skin .errbox,body.uk-skin .warnbox{display:flex;gap:9px;align-items:flex-start;
  border:1px solid var(--line-2);background:var(--bg-2);border-radius:var(--r-sm);padding:11px 13px;
  font-size:var(--fs-sm);color:var(--ink-2);line-height:1.5}
/* ── inputs / search / filter chips ── */
body.uk-skin .search input,body.uk-skin .hsearch input,body.uk-skin .dtf{
  background:#0b0f17;border:1px solid #27384a;color:#eaf1f9;border-radius:8px}
body.uk-skin .search button{background:#4d9dff;color:#06121f}
body.uk-skin .fbtn{background:#111824;border:1px solid #1c2937;color:#9bb0c6;border-radius:14px}
body.uk-skin .fbtn.on{background:#4d9dff;border-color:#4d9dff;color:#06121f}
/* ── theme chips ── */
body.uk-skin .tchip{background:#102234;color:#7fc0ff;border:1px solid #1d3a55}
body.uk-skin .tchip:hover{background:#1d3a55;color:#cfe8ff}
/* ── banners ── */
body.uk-skin .b-on{background:rgba(63,212,134,.13);color:#3fd486;border:1px solid #1f6f3a}
body.uk-skin .b-off{background:rgba(255,106,122,.13);color:#ff6a7a;border:1px solid #8f1f1f}
body.uk-skin .b-neu{background:rgba(246,183,60,.13);color:#f6b73c;border:1px solid #5a4a1f}
/* ── strategy thesis badge ── */
body.uk-skin .sbadge{border:1px solid #1c2937}
body.uk-skin .sbadge .th{color:#9bb0c6}
/* ── tab bars ── */
body.uk-skin .tabbar{border-bottom:1px solid #1c2937}
body.uk-skin .tabbar a{color:#9bb0c6}
body.uk-skin .tabbar a.on{color:#eaf1f9;border-bottom-color:#b18cff}
/* ── the frozen-pane data grid — COLOUR ONLY (sticky/z-index left exactly as-is) ── */
body.uk-skin .scrwrap{background:#0b0f17;border:1px solid #1c2937;border-radius:12px}
body.uk-skin table.scr th,body.uk-skin table.scr td{border-bottom:1px solid #161f2b}
body.uk-skin table.scr thead tr.sgrp th{background:#18222f;color:#7e90a8;border-bottom:1px solid #27384a;border-left:1px solid #1c2937}/* AA */
body.uk-skin table.scr thead tr.scol th{background:#111824;color:#9bb0c6;border-bottom:1px solid #27384a}
body.uk-skin table.scr .fz{background:#0b0f17;border-right:1px solid #1c2937}
body.uk-skin table.scr thead tr.scol th.fz,body.uk-skin table.scr thead tr.sgrp th.fz{background:#18222f}
body.uk-skin table.scr tbody tr:nth-child(even) td.fz{background:#0e1620}
body.uk-skin table.scr tbody tr:hover td{background:#18222f !important}
/* density — the frozen data grid's vertical row padding follows --grid-pad (6px comfortable
   == current, 3px compact). Only the big data grid is density-driven; small tables stay put. */
body.uk-skin table.scr td,body.uk-skin table.scr th{padding-top:var(--grid-pad);padding-bottom:var(--grid-pad)}
/* ════════════════════════════════════════════════════════════════════════════
   Lane L2 — BLEED-THROUGH NEUTRALISATION (the `9def4ff` bug class, generalised).
   `dashboard._BASE_CSS` (on every legacy `_shell` page) carries bare-element rules
   (h2, table, th, td, …). A native ui_kit component (`.uk-card`/`.uk-t`/`.uk-h1`/…)
   dropped onto a reskinned page either loses properties the native rule doesn't
   self-assert (e.g. bare `h2{16px}` shrinks a native card heading) or inherits the
   legacy metric. Verified IN-BROWSER: on /dash/markets an injected uk-card <h2>
   computed 16px vs 21px on the native /dash/coverage reference.
   Fix: re-assert the native `.uk-*` geometry under `body.uk-skin .uk-*` so the
   specificity (0,2,x) outranks every bare element rule — ANY native component on
   ANY reskinned page now renders identically to the native reference, immune to
   present + future bare-element bleed-through. Tokens already inherit (ui_tokens
   is prepended site-wide), so values track the design system, not hardcodes. ──── */
body.uk-skin .uk-h1{font-size:22px;font-weight:600;margin:0 0 2px;letter-spacing:-.2px;color:var(--ink)}
body.uk-skin .uk-card>h2,body.uk-skin .uk-card h2.uk-h2{font-size:21px;margin:.83em 0;color:var(--ink);font-weight:600}
body.uk-skin .uk-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;box-shadow:var(--glass)}
body.uk-skin .uk-eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink-3);margin:0 0 11px;display:flex;align-items:center;gap:8px}
body.uk-skin .uk-stat .lbl{font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
body.uk-skin .uk-stat .val{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums;font-family:var(--mono);line-height:1;color:var(--ink)}
/* native frozen table: re-assert metrics so bare `table/th/td` cannot fill in. */
body.uk-skin table.uk-t{width:100%;border-collapse:collapse;font-size:13px}
body.uk-skin .uk-t th{background:var(--bg-3);color:var(--ink-3);font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;font-weight:600;text-align:right;padding:var(--row-pad,10px) 13px;border-bottom:1px solid var(--line-2)}
body.uk-skin .uk-t th:first-child,body.uk-skin .uk-t td:first-child{text-align:left}
body.uk-skin .uk-t td{padding:var(--row-pad,10px) 13px;text-align:right;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;color:var(--ink-2)}
body.uk-skin .uk-t td.sym{color:var(--ink);font-weight:600}
body.uk-skin .uk-pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:20px;white-space:nowrap}
body.uk-skin .uk-badge{display:inline-flex;align-items:center;gap:6px;font-size:10.5px;color:var(--ink-3);border:1px solid var(--line-2);border-radius:6px;padding:2px 8px}
body.uk-skin .uk-seg a{padding:6px 13px;font-size:12px}
/* ════════════════════════════════════════════════════════════════════════════
   Lane L2 — DEEPEN the legacy-primitive reskin from COLOUR-only → native GEOMETRY.
   Lane A retinted colour; the structural gap to the native reference (radius /
   spacing / elevation / type-scale) stayed. Re-state the geometry the native
   ui_kit cards/stats use, on the legacy primitives, so a reskinned BODY reads as
   native (not just dark-with-the-right-blue). No layout/sticky/z-index touched on
   the frozen-pane grid (that geometry is sacred); only surface + type. ──────────── */
/* radius + surface only on .card — padding is context-dependent (some .card are compact
   filter/control strips, not content cards) so DON'T force it; let each keep its own. */
body.uk-skin .card{border-radius:var(--r)}
body.uk-skin .maj{border-radius:var(--r);padding:15px 16px}
body.uk-skin .scard{border-radius:var(--r)}
body.uk-skin .kpi .box{border-radius:var(--r-sm);padding:13px 14px}
body.uk-skin .kpi .num{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:600}
body.uk-skin .kpi .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.5px}
body.uk-skin .chip{border-radius:var(--r-sm)}
body.uk-skin h2{font-size:16px;font-weight:600;letter-spacing:-.1px}
/* ── RS hub (rs_section.py `rsh-*`): a self-contained mini-design-system Lane A's skin
   never retinted — it still carries the OLD palette (#161b22 / #30363d / #1f6feb /
   radius 10px). Verified in-browser: rsh-card bg #161b22 vs native #111824. Map every
   rsh primitive to the ui_kit tokens so the RS hub matches the native reference. ──── */
body.uk-skin .rsh-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);border-top:3px solid var(--accent)}
body.uk-skin .rsh-h,body.uk-skin .rsh-sym{color:var(--ink)}
body.uk-skin .rsh-go{color:var(--accent)}
body.uk-skin .rsh-q,body.uk-skin .rsh-mut,body.uk-skin .rsh-sub2{color:var(--ink-2)}
body.uk-skin .rsh-sec,body.uk-skin .rsh-sub,body.uk-skin .rsh-empty,body.uk-skin .rsh-foot{color:var(--ink-3)}
body.uk-skin .rsh-chip{background:var(--bg-1);border:1px solid var(--line);border-radius:var(--r-sm);color:var(--ink-2)}
body.uk-skin .rsh-bench{border:1px solid var(--line-2);border-radius:var(--r-sm)}
/* ── Markets "Full index bundle" tiles (.ck-tile): another legacy mini-system carrying the
   OLD palette (bg #161b22, border #30363d). Map to ui_kit tokens to match the reference.
   (A few inline-styled tag chips in the same body still hold #21262d/#30363d — inline style,
   not class-reachable; a subtle shade nuance, left to the frozen body / flagged.) ── */
body.uk-skin .ck-tile{background:var(--bg-2);border-color:var(--line)}
body.uk-skin a.ck-tile:hover{border-color:var(--accent)}
/* ── CPR strip cells (.cprstrip .c — the pivot tiles on /dash/cpr + the CPR overlay on
   the dossier): the last class-based old-palette holdout found in the W4 full-site sweep
   (bg #161b22). Map to --bg-2; the up/dn semantic ink on them is already retinted.
   Site-wide sweep otherwise clean — every other legacy page's class-based surfaces are
   already covered by the card / maj / kpi / rsh / ck-tile token maps. ── */
body.uk-skin .cprstrip .c{background:var(--bg-2)}
/* ── responsive: legacy page body on a phone ── */
@media (max-width:640px){
  body.uk-skin .wrap{padding-left:var(--gutter);padding-right:var(--gutter)}
  body.uk-skin .fbtn,body.uk-skin .fbar a,body.uk-skin .chip{padding:8px 12px}
  body.uk-skin .scrwrap{max-height:calc(100vh - 196px)}
  body.uk-skin .kpi .box{min-width:calc(50% - 5px)}
  /* NO horizontal page overflow: grid/flex children must shrink below their content so a
     wide nowrap table scrolls INSIDE its card instead of ballooning the whole page. The
     frozen-pane grids (.scr/.uk-t) keep their own wrappers — never display:block them. */
  body.uk-skin .mkt-grid>*,body.uk-skin .majgrid>*,body.uk-skin .theme-groups>*,
  body.uk-skin .scards>*,body.uk-skin .uk-cols>*{min-width:0}
  body.uk-skin .ck-board{overflow-x:auto;-webkit-overflow-scrolling:touch}
  body.uk-skin table:not(.scr):not(.uk-t){display:block;overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}
  /* L2 Wave2 (mobile audit): the dossier tab nav (.tabbar — Price/Positioning/…/F&O) is a
     flex-wrap:nowrap row ~1351px wide with overflow-x:visible and NO mobile rule → at 380px
     it forced horizontal PAGE overflow (or clipped the right tabs). Make it scroll inside
     itself like the native .uk-nav/.uk-sub do — page stays at viewport width. (Verified
     viewport-independently from the CSS facts; CDP/real-viewport unavailable in-env.) */
  body.uk-skin .tabbar{overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  body.uk-skin .tabbar::-webkit-scrollbar{display:none}
  body.uk-skin .tabbar a{flex:0 0 auto;white-space:nowrap}
}
</style>"""


def skin_css() -> str:
    """The reskin stylesheet (`<style>` block). Injected once per legacy page. Prepends the
    shared `ui_tokens` foundation (tokens + base + a11y + density scale) AND the native
    `ui_components` state system (uk-empty/uk-error/uk-note/uk-skel/uk-spin/…), so every
    legacy page carries the SAME design language as the native v2 pages — focus rings,
    reduced-motion, the density switch, and the polished empty/loading/error states now work
    site-wide. The components stylesheet is fully `.uk-*`-class-scoped (zero bleed onto legacy
    bare elements) and idempotent (its own marker). Defensive: a missing foundation/components
    module degrades gracefully (skin alone), never breaks the page."""
    try:
        from src.web import ui_tokens as _T
        head = _T.tokens_css()
    except Exception:  # noqa: BLE001
        head = ""
    try:
        from src.web import ui_components as _C
        head += _C.components_css()  # native state system → legacy pages (class-scoped, safe)
    except Exception:  # noqa: BLE001
        pass
    return head + _SKIN_CSS


# The legacy two-row header block — `<header>…</header>` produced by dashboard._shell
# (hrow1 brand+search, hrow2 the .v2bar nav, hrow3 the .v2subnav). Lane M1 replaces this
# WHOLE block with the native single-row ui_kit topbar so legacy + native pages share one
# header. Non-greedy, DOTALL: matches exactly the first header element.
_HEADER_RE = re.compile(r"<header\b[^>]*>.*?</header>", re.S)


def _native_header(active) -> str:
    """The native ui_kit header (single-row `uk-top` + contextual `uk-sub`) for a legacy
    page, so it is visually indistinguishable from a native page (Coverage/Strategist).

    Reuses the EXISTING native renderers — `ui_kit.topbar` + `ui_kit.nav_links` over
    `v2_surfaces.site_nav(active)` (Trust is the last inline nav item) and
    `v2_surfaces.native_subnav(active)` (the registry-driven contextual sub-nav) — so the
    two code paths converge on ONE header. The Cmd-K overlay is re-injected here (it used
    to ride on the legacy `_nav` we are replacing) so ⌘K keeps working; it is idempotent
    (window.__cmdk guard). Defensive: any failure raises to the caller, which falls back
    to the original legacy header (never a 500)."""
    from src.web import ui_kit as K
    from src.web import v2_surfaces as V
    nav_html = K.nav_links(V.site_nav(active))   # altitude tabs + Trust inline (exactly once)
    top = K.topbar(active, nav_html=nav_html)    # <div class="uk-top"> … </div>
    sub = V.native_subnav(active)                # <div class="uk-sub"> … </div> or ''
    return top + sub + K.cmdk_overlay()


# Fallback `active` recovery when reskin() is called without the threaded nav key (e.g. a
# direct reskin(html) call, or a future global middleware). The legacy `.v2bar` nav marks
# its current tab with `class="on"` + `aria-current="page"`; recover the altitude from
# that anchor's href. Best-effort — a miss just means no lit tab, never an error.
_ACTIVE_HREF_RE = re.compile(r'<a class="on"[^>]*href="(/dash/[^"]+)"[^>]*aria-current="page"')
# map a top-bar altitude href back to its nav key (the values site_nav highlights on).
_HREF_TO_ACTIVE = {"/dash/markets": "markets", "/dash/screener": "screener",
                   "/dash/strategist": "strategies", "/dash/strategies": "strategies",
                   "/dash/dashboard": "tracker", "/dash/coverage": "coverage"}


def _active_from_html(html: str):
    """Best-effort: recover the page's nav key from the rendered legacy nav's lit tab, so
    the native header highlights correctly even when `active` was not threaded. Returns
    None on a miss (header still renders, just no lit altitude)."""
    try:
        m = _ACTIVE_HREF_RE.search(html)
        if m:
            return _HREF_TO_ACTIVE.get(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    return None


def _cmdk_hint() -> str:
    try:
        from src.web import ui_kit as K
        return K.cmdk_hint()
    except Exception:  # noqa: BLE001 — never let the hint break the skin
        return ('<div class="uk-cmdk">Search or ask Pat '
                '<kbd>&#8984;K</kbd></div>')


def _chrome_css() -> str:
    """The native ui_kit chrome stylesheet (`.uk-top/.uk-nav/.uk-sub/.uk-cmdk` — all
    top-level selectors, not `.uk`-scoped), so the native header styles identically on a
    legacy page whose body is NOT wrapped in `.uk`. Defensive: degrades to '' if absent."""
    try:
        from src.web import ui_kit as K
        return K.css()
    except Exception:  # noqa: BLE001
        return ""


def _density_js() -> str:
    """The global density switch (defined in ui_kit so it's identical on both shells).
    Defensive: a missing ui_kit degrades to no switch, never breaks the page."""
    try:
        from src.web import ui_kit as K
        return K.density_js()
    except Exception:  # noqa: BLE001
        return ""


def reskin(html: str, active=None) -> str:
    """Post-process one ``_shell`` html string into the ui_kit language + UNIFY its header
    with the native pages. Defensive + idempotent: an already-skinned string (or any
    non-_shell html) is returned as-is.

    ``active`` is the page's nav key (the 3rd positional arg of dashboard._shell, threaded
    by install()'s wrapper). It drives the native topbar/sub-nav highlight. When absent
    (a direct reskin() call without it) we fall back to extracting it from the rendered
    nav, then to no-highlight — the page still renders, just without the lit tab."""
    try:
        if not html or _SKIN_MARKER in html:
            return html
        # Only reskin a legacy dashboard._shell page. Every _shell output carries the
        # header row `<div class="hrow1">`; a ui_kit-native page (Coverage, the style
        # guide) never does — so this guard makes reskin() self-protecting: it can be
        # pointed at ANY html (a future global middleware) and will no-op on the v2
        # surfaces rather than double-skin them.
        if 'class="hrow1"' not in html:
            return html
        # mark the body so the scoped overlay applies (and signals 'already skinned').
        if "<body" not in html:
            return html
        out = html.replace("<body>", '<body class="uk-skin">', 1)
        if 'class="uk-skin"' not in out:  # body had attrs already
            out = re.sub(r"<body(?![^>]*uk-skin)", '<body class="uk-skin"', out, count=1)
        # a11y: a keyboard skip-link as the first focusable element, targeting the page body.
        out = re.sub(r"(<body[^>]*>)",
                     r'\1<a class="uk-skip" href="#uk-main">Skip to content</a>', out, count=1)
        out = out.replace('<div class="wrap', '<div id="uk-main" class="wrap', 1)
        # ── header UNIFICATION (Lane M1) — replace the legacy two-row <header> (hrow1
        # brand+search, hrow2 the .v2bar nav, hrow3 the .v2subnav) with the native
        # single-row ui_kit topbar + contextual sub-nav, so a legacy page is visually
        # indistinguishable from a native one (Trust inline with the tabs exactly once,
        # one logo, no justified-tabs anomaly, identical responsive/hamburger behaviour).
        if active is None:
            active = _active_from_html(out)
        try:
            new_header = _native_header(active)
            out, _hdr = _HEADER_RE.subn(lambda _m: new_header, out, count=1)
        except Exception as e:  # noqa: BLE001 — header swap must never break the page
            log.warning("shell_skin native header swap skipped: %s", e)
            # Fall back to the legacy header but still swap the search box for the Ask-Pat
            # hint so the page is at least not showing the old "search ticker…" box.
            out = _HSEARCH_RE.sub(lambda _m: _cmdk_hint(), out, count=1)
        # inject the reskin css (body retint) + the native chrome css (header styling) +
        # the global density switch LAST in <head> (after _BASE_CSS). The chrome css comes
        # AFTER the skin css so the native `.uk-*` header rules win the source-order tie.
        head_add = skin_css() + _chrome_css() + _density_js()
        if "</head>" in out:
            out = out.replace("</head>", head_add + "</head>", 1)
        else:
            out = head_add + out
        return out
    except Exception as e:  # noqa: BLE001 — a skin failure must never break the page
        log.warning("shell_skin reskin skipped: %s", e)
        return html


def install() -> bool:
    """Monkeypatch ``dashboard._shell`` so every legacy page renders in the ui_kit
    language. Idempotent (sentinel), defensive (never raises). Returns True if the
    skin is in place (newly or already)."""
    try:
        import src.web.dashboard as D
    except Exception as e:  # noqa: BLE001
        log.warning("shell_skin install skipped: dashboard import failed: %s", e)
        return False
    if getattr(D, _SKIN_SENTINEL, False):
        return True
    orig_shell = getattr(D, "_shell", None)
    if not callable(orig_shell):
        log.warning("shell_skin install skipped: dashboard._shell not found")
        return False

    def _skinned_shell(*args, **kwargs):
        # dashboard._shell(title, body, active, latest_date="", wide=False): the page's
        # nav key is the 3rd positional arg (or the `active` kwarg). Thread it into reskin
        # so the native topbar/sub-nav highlight the correct altitude. Best-effort —
        # reskin falls back to recovering it from the rendered nav when absent.
        active = kwargs.get("active")
        if active is None and len(args) >= 3:
            active = args[2]
        return reskin(orig_shell(*args, **kwargs), active)

    # keep the wrapped original discoverable (debugging / revert).
    _skinned_shell.__wrapped__ = orig_shell  # type: ignore[attr-defined]
    D._shell = _skinned_shell

    # Rebind every OTHER module that captured `_shell` by reference at import time
    # (e.g. `from src.web.dashboard import _shell` in rrg_view / rsband_view /
    # rotation_view / participants_view / wolfe_view). Those modules resolve the bare
    # name `_shell` against their OWN globals, so patching dashboard._shell alone does
    # not reach them — their page would keep the legacy chrome. We sweep sys.modules
    # and repoint any module-level `_shell` that *is* the original to the wrapped one.
    # Generic (no hardcoded names), touches no source file, idempotent (the next sweep
    # finds the wrapped fn, not the original, so it skips). main.py imports every router
    # before wire() runs, so all such modules already exist here.
    import sys
    rebound = 0
    for _name, _mod in list(sys.modules.items()):
        if _mod is None or _mod is D:
            continue
        try:
            if getattr(_mod, "_shell", None) is orig_shell:
                _mod._shell = _skinned_shell
                rebound += 1
        except Exception:  # noqa: BLE001 — a quirky module must never break install
            continue

    setattr(D, _SKIN_SENTINEL, True)
    log.info("shell_skin installed — legacy pages reskinned to ui_kit (+%d imported refs)", rebound)
    return True


def _selftest() -> int:
    """Render a real legacy page through the wrapped shell + assert the reskin took,
    is no-loss (the body data survives), and is idempotent."""
    import sys
    import types

    import src.web.dashboard as D

    # simulate a view module that captured `_shell` by reference (like rrg_view) BEFORE
    # install, so we can prove the sys.modules rebind reaches it.
    _fake = types.ModuleType("src.web._fake_lens_for_skin_test")
    _fake._shell = D._shell  # the original, as `from ...dashboard import _shell` would bind
    sys.modules[_fake.__name__] = _fake

    assert install() is True
    assert install() is True  # idempotent — no double-wrap, still True
    assert _fake._shell is D._shell, "imported _shell reference was not rebound"
    assert reskin(_fake._shell("T", '<div class="card">x</div>', "markets")).count(_SKIN_MARKER) == 1, \
        "rebound ref does not produce a skinned page"
    del sys.modules[_fake.__name__]

    # a representative legacy page body with the common primitives.
    body = ('<div class="card"><h2>Markets</h2>'
            '<table><tr><th>Sym</th></tr><tr><td class="sym">RELIANCE</td>'
            '<td class="pos">+1.2%</td></tr></table></div>'
            '<div class="kpi"><div class="box"><div class="num">42</div>'
            '<div class="lbl">names</div></div></div>')
    out = D._shell("Markets · patearn", body, "markets", "2026-06-28", wide=True)

    assert "uk-skin" in out and _SKIN_MARKER in out, "skin not applied"
    assert "Search or ask Pat" in out, "Ask-Pat hint not swapped in"
    assert 'class="hsearch"' not in out, "legacy search form still present"
    assert "RELIANCE" in out and ">42<" in out, "body data lost (NOT no-loss)"
    assert out.count(_SKIN_MARKER) == 1, "skin injected more than once"
    # ── header UNIFICATION (Lane M1): the native single-row topbar REPLACED the legacy
    # two-row header, so the page now carries the SAME header markup as a native page. ──
    assert 'class="uk-top"' in out, "native topbar not emitted on legacy page"
    assert 'class="hrow1"' not in out, "legacy hrow1 header still present"
    assert 'class="v2bar"' not in out, "legacy .v2bar two-row nav still present"
    assert 'class="uk-trustlink"' not in out, "legacy top-row Trust chip still present"
    # Trust is inline with the tabs (a uk-nav anchor) and appears EXACTLY ONCE.
    assert out.count(">Trust<") == 1, f"Trust must appear exactly once, found {out.count('>Trust<')}"
    assert 'href="/dash/coverage">Trust<' in out, "Trust must be an inline nav anchor"
    # the contextual sub-nav rendered for the Markets altitude (registry-driven uk-sub).
    assert 'class="uk-sub"' in out and 'href="/dash/sectors"' in out, "Markets sub-nav not rendered"
    # the correct altitude tab is lit.
    assert 'class="on" href="/dash/markets" aria-current="page"' in out, "Markets tab not highlighted"
    # ⌘K still works — the overlay was re-injected after the legacy nav was removed.
    assert 'id="cmdk-ov"' in out, "Cmd-K overlay lost after header swap"
    # reskinning an already-skinned string is a no-op
    assert reskin(out) == out, "reskin not idempotent on its own output"
    # a non-_shell html (no <body>) is returned untouched
    assert reskin("<div>x</div>") == "<div>x</div>", "non-page html mutated"
    # the native header renders even when `active` is not threaded (a direct reskin call):
    # the topbar is always present; the sub-nav is present only when the altitude resolves.
    _direct = reskin(D.__dict__["_shell"].__wrapped__("S", "<div class='card'>z</div>", "markets"))
    assert 'class="uk-top"' in _direct, "native topbar not rendered on a direct reskin"
    # `_active_from_html` recovers the altitude from a v2-nav page's lit tab (the production
    # case where the v2 nav IS installed): build that markup and prove recovery.
    _v2nav_page = (head := "<header><div class=\"hrow1\"></div>") + \
        '<a class="on" href="/dash/markets" aria-current="page">Markets</a></header>'
    assert _active_from_html(_v2nav_page) == "markets", "active not recovered from v2 nav lit tab"
    print("shell_skin selftest OK — native header unified (uk-top + uk-sub, single inline "
          "Trust, no hrow1/.v2bar), no-loss, idempotent, defensive")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
