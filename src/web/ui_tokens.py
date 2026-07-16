"""ui_tokens.py — the shared design-system foundation for Patearn's v2 UI (Lane A2).

ONE source of truth for the design tokens + base reset + accessibility primitives +
the density scale, consumed by BOTH render paths:
  * `ui_kit.shell`  — the native v2 pages (Coverage, Strategist, Screen+, the showcase)
  * `shell_skin`    — the runtime transform applied to every legacy `dashboard._shell` page

Defining the tokens on ``:root`` (global custom properties) lets the native ``.uk`` scope
AND the legacy ``body.uk-skin`` scope inherit the identical palette/scale — so the two
shells converge on one language (the step toward retiring the two-shell duality) without
touching any page body. Values match the shipped ui_kit palette exactly (no visual
regression); this module only ADDS the structured scales (type, spacing, elevation, z),
the a11y layer, and the density switch on top.

Public API:
    tokens_css() -> the <style> block (tokens + base + a11y + density). Include ONCE/page.
    FONT / MONO  -> the font stacks (re-exported for callers that build inline styles).

Isolation: ZERO `src` imports — a leaf module (like glossary.py), safe to import from
anywhere. Additive + reversible.
"""
from __future__ import annotations

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,'Helvetica Neue',Arial,sans-serif")
MONO = ("'SF Mono',ui-monospace,'JetBrains Mono','Cascadia Code',Menlo,Consolas,monospace")

# Marker so a page (or the skin) can detect the foundation is already present and not double-inject.
TOKENS_MARKER = "/* uk-tokens v1 */"

_TOKENS_CSS = """<style>""" + TOKENS_MARKER + """
:root{
  /* ═══ LIGHT-FIRST (P1, Ramana 2026-07-17): light is the site default; the FULL legacy
     dark palette moves — value-exact — to `:root[data-theme="dark"]` below, behind the
     ☾ toggle (theme_js in ui_kit; persisted like the density switch). Every light value
     is AA-checked on its ground (ink-3 5.4:1 on white, accent 5.0:1, semantics ≥4.5:1). ═══ */
  color-scheme:light;
  /* ── surfaces (bg-1 = page ground, bg-2 = card, bg-3 = th/inset/hover, bg-4 = deep inset) ── */
  --bg-0:#e9edf2; --bg-1:#f4f6f9; --bg-2:#ffffff; --bg-3:#eef1f5; --bg-4:#e2e8ee;
  /* ── hairlines ── */
  --line:#e2e8ee; --line-2:#cdd7e0; --line-3:#b3c0cc;
  /* ── ink ── */
  --ink:#111a22; --ink-2:#40505e; --ink-3:#5f7183; --ink-4:#a8b6c2;
  /* ── accents + semantics (patearn teal family, dark-calibrated for the light ground) ── */
  --accent:#0e7490; --accent-2:#155e75; --accent-cy:#0891b2; --accent-dim:rgba(14,116,144,.10);
  --up:#0f8a50; --up-dim:rgba(15,138,80,.10);
  --down:#ce3b57; --down-dim:rgba(206,59,87,.09);
  --warn:#b45309; --warn-dim:rgba(180,83,9,.12);
  --cred:#7c3aed; --cred-dim:rgba(124,58,237,.10);
  /* ── value RGB triples (colour-alignment Phase 0) — build ANY-alpha tint from ONE source,
     e.g. rgba(var(--up-rgb),.08). Values == --up/--down/--warn per theme. ── */
  --up-rgb:15,138,80; --down-rgb:206,59,87; --warn-rgb:180,83,9;
  /* ── status / health — present/absent/enabled badges (role ≠ the value contract). ── */
  --ok:#0f8a50; --off:#ce3b57; --neu:#b45309;
  /* ── foreground ON an --accent fill (primary buttons, active pills). ── */
  --on-accent:#ffffff;
  /* ── categorical scorecard identity (RS border must never read "bullish"). ── */
  --cat-rs:#0891b2;
  /* ── categorical / chart-series identity (colour-alignment Phase 3). Canvas code seeds
     from getComputedStyle(:root), so each theme carries its own calibrated ramp. ── */
  --accent-orange:#c2610e;                 /* VWAP / MACD-signal / DISTRIB / Launchpad */
  --series-1:#0e7c86; --series-2:#c2610e; --series-3:#7c3aed; --series-4:#188038;
  --series-5:#c2417f; --series-6:#0969da; --series-7:#9a6700; --series-8:#d23f77;
  --chart-line:#1a66c2;                    /* price line / area primary */
  --chart-blue:#2f81d6;                    /* delivery / wolfe / macd */
  --chart-dvpt:#9a6700;                    /* DVPT footprint amber */
  --chart-idle:#8fa9bd;                    /* idle DVPT marker (muted) */
  --chart-vol:#a4b7c6;                     /* volume histogram (recessive grey-blue) */
  --chart-dval:#188038;                    /* delivered-value bar — categorical green, NOT --up */
  --chart-rsi:#8250df;                     /* RSI line (violet) */
  /* ── theme-dependent chrome surfaces (P1): the topbar/sub-nav glass, the page aurora,
     the chart-expand chip, and the frozen-grid hairline/zebra — token-ized so ui_kit /
     shell_skin carry ZERO baked-in dark assumptions. ── */
  --topbar-grad:linear-gradient(180deg,rgba(255,255,255,.94),rgba(244,246,249,.78));
  --subnav-bg:rgba(244,246,249,.72);
  --chartexp-bg:rgba(255,255,255,.82);
  --aurora:radial-gradient(1100px 560px at 82% -12%,rgba(14,116,144,.05),transparent 60%),
           radial-gradient(860px 480px at -8% 8%,rgba(8,145,178,.04),transparent 55%);
  --grid-line:#e8edf2; --fz-zebra:#eef1f5;
  /* ── type scale (tabular instrument feel) ── */
  --fs-2xs:10.5px; --fs-xs:11.5px; --fs-sm:12.5px; --fs-md:14px; --fs-lg:16px;
  --fs-xl:19px; --fs-2xl:23px; --fs-3xl:30px;
  --lh:1.5; --lh-tight:1.25;
  --fw-med:500; --fw-semi:600; --fw-bold:700;
  /* ── spacing scale ── */
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:22px; --sp-6:30px; --sp-7:44px; --sp-8:64px;
  --gutter:20px;            /* page side padding — shrinks on mobile (see base) */
  --row-pad:10px;          /* native table/card row padding — driven by density */
  --grid-pad:6px;          /* dense frozen-grid (table.scr / .uk-t) vertical padding — density */
  /* ── radius ── */
  --r-xs:5px; --r-sm:8px; --r:12px; --r-lg:18px; --r-pill:999px;
  /* ── elevation ── */
  --e-1:0 1px 2px rgba(16,24,32,.07); --e-2:0 6px 18px rgba(16,24,32,.09); --e-3:0 14px 36px rgba(16,24,32,.13);
  --glass:inset 0 1px 0 rgba(255,255,255,.6); --shadow:var(--e-3);
  /* ── motion ── */
  --t:170ms cubic-bezier(.2,.7,.2,1); --t-fast:110ms cubic-bezier(.2,.7,.2,1);
  /* ── z-index scale ── */
  --z-sticky:20; --z-nav:30; --z-overlay:9998; --z-toast:10000;
  /* ── fonts ── */
  --font:""" + FONT + """; --mono:""" + MONO + """;
}

/* ═══ DARK THEME (the ☾ toggle) — the pre-P1 palette, VALUE-EXACT (zero regression for
   the familiar instrument look). Selected by `data-theme="dark"` on <html>, stamped
   pre-paint by ui_kit.theme_js() from localStorage("uk-theme"); light is the default. ═══ */
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg-0:#070a10; --bg-1:#0b0f17; --bg-2:#111824; --bg-3:#18222f; --bg-4:#202d3d;
  --line:#1c2937; --line-2:#27384a; --line-3:#33485f;
  /* AA note preserved: --ink-3 #7e90a8 = 5.5:1 on bg-2 / 5.9 on bg-1 / 4.9 on bg-3. */
  --ink:#eaf1f9; --ink-2:#9bb0c6; --ink-3:#7e90a8; --ink-4:#3c4a5c;
  --accent:#4d9dff; --accent-2:#6db3ff; --accent-cy:#34e0d6; --accent-dim:rgba(77,157,255,.14);
  --up:#3fd486; --up-dim:rgba(63,212,134,.13);
  --down:#ff6a7a; --down-dim:rgba(255,106,122,.13);
  --warn:#f6b73c; --warn-dim:rgba(246,183,60,.14);
  --cred:#b18cff; --cred-dim:rgba(177,140,255,.15);
  --up-rgb:63,212,134; --down-rgb:255,106,122; --warn-rgb:246,183,60;
  --ok:#3fd486; --off:#ff6a7a; --neu:#f6b73c;
  --on-accent:#06121f;
  --cat-rs:#34e0d6;
  --accent-orange:#f0883e;
  --series-1:#39c5cf; --series-2:#f0883e; --series-3:#a371f7; --series-4:#56d364;
  --series-5:#db61a2; --series-6:#4d9dff; --series-7:#d29922; --series-8:#f778ba;
  --chart-line:#1f6feb; --chart-blue:#58a6ff; --chart-dvpt:#d29922; --chart-idle:#30506b;
  --chart-vol:#3b5168; --chart-dval:#2ea043; --chart-rsi:#d2a8ff;
  --topbar-grad:linear-gradient(180deg,rgba(17,24,36,.92),rgba(11,15,23,.66));
  --subnav-bg:rgba(11,15,23,.5);
  --chartexp-bg:rgba(11,15,23,.7);
  --aurora:radial-gradient(1100px 560px at 82% -12%,rgba(77,157,255,.07),transparent 60%),
           radial-gradient(860px 480px at -8% 8%,rgba(52,224,214,.05),transparent 55%);
  --grid-line:#161f2b; --fz-zebra:#0e1620;
  --e-1:0 1px 2px rgba(0,0,0,.30); --e-2:0 6px 18px rgba(0,0,0,.34); --e-3:0 14px 36px rgba(0,0,0,.46);
  --glass:inset 0 1px 0 rgba(255,255,255,.045);
}

/* ── density: compact shrinks spacing + row padding + base size (comfortable = default) ── */
[data-density="compact"]{
  --sp-3:9px; --sp-4:12px; --sp-5:16px; --sp-6:22px;
  --row-pad:6px; --grid-pad:3px; --fs-md:13px; --fs-sm:12px; --gutter:14px;
}

/* ── base / reset (scoped so it never restyles a legacy page that isn't opted in) ── */
.uk,.uk *,body.uk-skin,body.uk-skin *{box-sizing:border-box}
.uk,body.uk-skin{
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
  font-feature-settings:'tnum' 1,'cv01' 1; text-rendering:optimizeLegibility;
}
.uk .num,body.uk-skin .num,.uk-num{font-variant-numeric:tabular-nums;font-family:var(--mono)}

/* ── accessibility primitives ── */
.uk-sr-only{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;
  overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.uk-skip{position:fixed;left:-999px;top:0;z-index:var(--z-toast);background:var(--accent);
  color:var(--on-accent);font:600 13px var(--font);padding:9px 16px;border-radius:0 0 10px 0;text-decoration:none}
.uk-skip:focus{left:0}
.uk :where(a,button,input,select,textarea,summary,[tabindex]):focus-visible,
body.uk-skin :where(a,button,input,select,textarea,summary,[tabindex]):focus-visible{
  outline:2px solid var(--accent); outline-offset:2px; border-radius:4px}
@media (prefers-reduced-motion:reduce){
  .uk *,.uk *::before,.uk *::after,body.uk-skin *,body.uk-skin *::before,body.uk-skin *::after{
    animation-duration:.001ms!important; animation-iteration-count:1!important;
    transition-duration:.001ms!important; scroll-behavior:auto!important}
}

/* ── responsive gutter (mobile tightens the page edges) ── */
@media (max-width:640px){ :root{ --gutter:13px } }

/* ── density toggle (universal chrome — lives in the foundation so it styles on BOTH
   the native .uk-top and the legacy .v2util; the bars visually tighten when compact) ── */
.uk-denstoggle{display:inline-flex;flex-direction:column;justify-content:center;gap:3px;
  width:30px;height:30px;padding:0 7px;border:1px solid var(--line-2);background:var(--bg-1);
  border-radius:var(--r-sm);cursor:pointer;transition:var(--t);flex:none}
.uk-denstoggle:hover{border-color:var(--accent)}
.uk-denstoggle i{display:block;height:2px;background:var(--ink-3);border-radius:1px;transition:var(--t)}
.uk-denstoggle.on{gap:1.5px}
.uk-denstoggle.on i{background:var(--accent)}
.uk-top .uk-denstoggle{margin-left:2px}

/* ── theme toggle (☾/☀ — universal chrome, sibling of the density switch; injected by
   ui_kit.theme_js() into .uk-top on native pages and .v2util on legacy pages) ── */
.uk-themetoggle{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;
  padding:0;border:1px solid var(--line-2);background:var(--bg-1);border-radius:var(--r-sm);
  color:var(--ink-3);font-size:14px;line-height:1;cursor:pointer;transition:var(--t);flex:none}
.uk-themetoggle:hover{border-color:var(--accent);color:var(--accent)}
.uk-top .uk-themetoggle{margin-left:2px}

/* ── print: any page prints as a clean light document — a leave-behind (D-PITCH-2).
   L2 W3: deepened — A4 page box with margins + a footer page counter, light-flip the whole
   palette, hide every interactive-only control, keep tables/cards intact across page breaks,
   and let value-colour (green/red) survive so a printed dossier still reads the contract. ── */
@page{margin:16mm 14mm 18mm}
@media print{
  /* selector carries data-theme too: :root[data-theme="dark"] (0,2,0) would otherwise
     out-rank a bare :root print override — printing from dark mode must STILL be light. */
  :root,:root[data-theme="dark"]{--bg-0:#fff;--bg-1:#fff;--bg-2:#fff;--bg-3:#f4f6f9;--bg-4:#eef1f5;
    --line:#c4ccd4;--line-2:#aab4be;--line-3:#9aa6b2;--ink:#0b0f17;--ink-2:#33414e;--ink-3:#5a6775;
    --shadow:none;--glass:none;--e-1:none;--e-2:none;--e-3:none;--aurora:none}
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .uk,body.uk-skin,body{background:#fff !important;color:#0b0f17}
  /* hide all chrome + interactive-only controls (toggles, filters, search, chart fullscreen) */
  .uk-top,.uk-sub,.v2bar,.v2subnav,.uk-cmdk,.uk-denstoggle,.uk-skip,.uk-seg,.uk-switch,
  .fbar,.fbtn,.search,.hsearch,.dtf,.tabbar,
  body.uk-skin header,#cmdk-ov,.uk-chart .exp{display:none !important}
  .uk-card,.uk-tw,.card,.scrwrap,.cprpanel,.maj,.kpi .box,.uk-stat,.cov-pane{box-shadow:none !important;
    border-color:#c4ccd4 !important;break-inside:avoid}
  h1,h2,.uk-h1,.uk-eyebrow{break-after:avoid}
  .uk-page,.wrap,.wrap.wide{max-width:none !important;padding:0 !important}
  a{color:#0b0f17 !important;text-decoration:none}
  /* tables: repeat the header on every printed page + visible hairlines + no clip */
  table{border-collapse:collapse}
  thead{display:table-header-group}
  tr,td,th{break-inside:avoid}
  th{border-bottom:1px solid #aab4be !important}
  /* value-colour contract survives print (a printed verdict must still read up/down) */
  .pos,.up,.uk-pill.up{color:#137a43 !important}
  .neg,.down,.uk-pill.down{color:#b22433 !important}
  /* a page-number footer so a multi-page leave-behind is paginated */
  body::after{content:"patearn — descriptive evidence, point-in-time; not investment advice";
    position:fixed;bottom:-13mm;left:0;right:0;text-align:center;font-size:8.5px;color:#5a6775}
}
</style>"""


def tokens_css() -> str:
    """The shared foundation `<style>` block (tokens + base + a11y + density). One per page."""
    return _TOKENS_CSS


def _selftest() -> int:
    css = tokens_css()
    assert TOKENS_MARKER in css
    # P1 light-first: :root carries the LIGHT palette; the dark block carries the legacy
    # palette VALUE-EXACT. Split the sheet at the dark selector to assert each side.
    dark_sel = ':root[data-theme="dark"]{'   # brace-anchored: the :root comment cites the bare selector
    assert dark_sel in css, "dark theme block missing"
    light_part, dark_part = css.split(dark_sel, 1)
    for tok in ("--bg-1:#f4f6f9", "--bg-2:#ffffff", "--accent:#0e7490", "--ink:#111a22",
                "--up:#0f8a50", "--down:#ce3b57", "--on-accent:#ffffff",
                "--up-rgb:15,138,80", "--down-rgb:206,59,87", "--warn-rgb:180,83,9",
                "--fs-md:14px", "--sp-4:16px", "--r:12px",
                "--topbar-grad", "--subnav-bg", "--chartexp-bg", "--aurora", "--grid-line",
                "--fz-zebra", "color-scheme:light"):
        assert tok in light_part, f"missing LIGHT token {tok}"
    # the pre-P1 dark values are preserved exactly (zero regression behind the ☾ toggle)
    for tok in ("--bg-1:#0b0f17", "--bg-2:#111824", "--line:#1c2937", "--ink:#eaf1f9",
                "--ink-2:#9bb0c6", "--accent:#4d9dff", "--accent-cy:#34e0d6",
                "--up:#3fd486", "--down:#ff6a7a", "--on-accent:#06121f", "--cat-rs:#34e0d6",
                "--accent-orange:#f0883e", "--series-1:#39c5cf", "--series-8:#f778ba",
                "--chart-line:#1f6feb", "--chart-dval:#2ea043",
                "--up-rgb:63,212,134", "--down-rgb:255,106,122", "--warn-rgb:246,183,60",
                "--ok:#3fd486", "--off:#ff6a7a", "color-scheme:dark",
                "--grid-line:#161f2b", "--fz-zebra:#0e1620"):
        assert tok in dark_part, f"dark palette drift: {tok}"
    assert 'data-density="compact"' in css and "uk-sr-only" in css and "prefers-reduced-motion" in css
    assert "uk-themetoggle" in css, "theme toggle style missing"
    # printing from EITHER theme must be light (the hardened print selector)
    assert ':root,:root[data-theme="dark"]{--bg-0:#fff' in css, "print override must beat the dark block"
    print("ui_tokens selftest OK — light-first :root + value-exact dark block + toggle + print guard")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
