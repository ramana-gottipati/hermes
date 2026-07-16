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
  /* ── surfaces ── */
  --bg-0:#070a10; --bg-1:#0b0f17; --bg-2:#111824; --bg-3:#18222f; --bg-4:#202d3d;
  /* ── hairlines ── */
  --line:#1c2937; --line-2:#27384a; --line-3:#33485f;
  /* ── ink ── */
  /* WCAG-AA (L2 W3 a11y): --ink-3 was #5c6f84 = 3.44:1 on the card bg → FAILS AA 4.5 for
     normal text, and it carries eyebrows / captions / table-th / .mut site-wide. Lifted to
     #7e90a8 = 5.5:1 on bg-2, 5.9:1 on bg-1, 4.9:1 on bg-3 → clears AA on every surface while
     staying a clearly-muted tertiary (ink-2 #9bb0c6 = 8.6:1 remains the distinct step above). */
  --ink:#eaf1f9; --ink-2:#9bb0c6; --ink-3:#7e90a8; --ink-4:#3c4a5c;
  /* ── accents + semantics ── */
  --accent:#4d9dff; --accent-2:#6db3ff; --accent-cy:#34e0d6; --accent-dim:rgba(77,157,255,.14);
  --up:#3fd486; --up-dim:rgba(63,212,134,.13);
  --down:#ff6a7a; --down-dim:rgba(255,106,122,.13);
  --warn:#f6b73c; --warn-dim:rgba(246,183,60,.14);
  --cred:#b18cff; --cred-dim:rgba(177,140,255,.15);
  /* ── value RGB triples (colour-alignment Phase 0) — build ANY-alpha tint from ONE source,
     e.g. rgba(var(--up-rgb),.08), so heat-cells / zone fills / chart tints stop re-hardcoding
     the legacy RGB (63,185,80 / 248,81,73 / 31,111,235). Values == --up/--down/--warn. ── */
  --up-rgb:63,212,134; --down-rgb:255,106,122; --warn-rgb:246,183,60;
  /* ── status / health — present/absent/enabled badges. A role SEPARATE from the value
     contract (a green "ON" is not a "+x%"); aliased to the value hues but NAMED distinctly so
     the colour gate + future audits never conflate a status pill with a directional verdict. ── */
  --ok:#3fd486; --off:#ff6a7a; --neu:#f6b73c;
  /* ── foreground ON an --accent fill (primary buttons, active pills) — was the orphan #06121f. ── */
  --on-accent:#06121f;
  /* ── categorical scorecard identity — a DISTINCT hue (cyan), NEVER a value green, so the RS
     scorecard border (.sc-RS) can't read as "bullish". Gives the 4 cards 4 distinct hues
     (POS=accent / RS=cat-rs / QUAL=warn / CPR=cred). Decouples category from the value contract. ── */
  --cat-rs:#34e0d6;
  /* ── categorical / chart-series identity (colour-alignment Phase 3). Role #2 (D-COL-1):
     multi-series + indicator-identity hues that must NEVER be --up/--down even when green/red.
     Values MATCH the shipped chart palettes (CMP_COLORS + the stock-chart `C` grammar), so
     seeding the canvas colour objects from getComputedStyle(:root) is colour-preserving. The
     `--series-*` ramp is the canonical categorical palette (compare overlays / RRG sectors);
     the `--chart-*` set names the indicator signatures the semantic tokens don't cover. ── */
  --accent-orange:#f0883e;                 /* VWAP / MACD-signal / DISTRIB / Launchpad — categorical orange */
  --series-1:#39c5cf; --series-2:#f0883e; --series-3:#a371f7; --series-4:#56d364;
  --series-5:#db61a2; --series-6:#4d9dff; --series-7:#d29922; --series-8:#f778ba;
  --chart-line:#1f6feb;                    /* price line / area primary */
  --chart-blue:#58a6ff;                    /* delivery / wolfe / macd */
  --chart-dvpt:#d29922;                    /* DVPT footprint amber */
  --chart-idle:#30506b;                    /* idle DVPT marker (muted) */
  --chart-vol:#3b5168;                     /* volume histogram (recessive grey-blue) */
  --chart-dval:#2ea043;                    /* delivered-value bar — categorical green, NOT --up */
  --chart-rsi:#d2a8ff;                     /* RSI line (lilac) */
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
  --e-1:0 1px 2px rgba(0,0,0,.30); --e-2:0 6px 18px rgba(0,0,0,.34); --e-3:0 14px 36px rgba(0,0,0,.46);
  --glass:inset 0 1px 0 rgba(255,255,255,.045); --shadow:var(--e-3);
  /* ── motion ── */
  --t:170ms cubic-bezier(.2,.7,.2,1); --t-fast:110ms cubic-bezier(.2,.7,.2,1);
  /* ── z-index scale ── */
  --z-sticky:20; --z-nav:30; --z-overlay:9998; --z-toast:10000;
  /* ── fonts ── */
  --font:""" + FONT + """; --mono:""" + MONO + """;
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
  color:#06121f;font:600 13px var(--font);padding:9px 16px;border-radius:0 0 10px 0;text-decoration:none}
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

/* ── print: any page prints as a clean light document — a leave-behind (D-PITCH-2).
   L2 W3: deepened — A4 page box with margins + a footer page counter, light-flip the whole
   palette, hide every interactive-only control, keep tables/cards intact across page breaks,
   and let value-colour (green/red) survive so a printed dossier still reads the contract. ── */
@page{margin:16mm 14mm 18mm}
@media print{
  :root{--bg-0:#fff;--bg-1:#fff;--bg-2:#fff;--bg-3:#f4f6f9;--bg-4:#eef1f5;
    --line:#c4ccd4;--line-2:#aab4be;--line-3:#9aa6b2;--ink:#0b0f17;--ink-2:#33414e;--ink-3:#5a6775;
    --shadow:none;--glass:none;--e-1:none;--e-2:none;--e-3:none}
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
    for tok in ("--bg-1:#0b0f17", "--accent:#4d9dff", "--ink:#eaf1f9", "--up:#3fd486",
                "--down:#ff6a7a", "--fs-md:14px", "--sp-4:16px", "--r:12px",
                # colour-alignment Phase 0 additions
                "--up-rgb:63,212,134", "--down-rgb:255,106,122", "--warn-rgb:246,183,60",
                "--ok:#3fd486", "--off:#ff6a7a", "--on-accent:#06121f", "--cat-rs:#34e0d6",
                # colour-alignment Phase 3 (categorical / chart-series identity)
                "--accent-orange:#f0883e", "--series-1:#39c5cf", "--series-8:#f778ba",
                "--chart-line:#1f6feb", "--chart-dval:#2ea043"):
        assert tok in css, f"missing token {tok}"
    assert 'data-density="compact"' in css and "uk-sr-only" in css and "prefers-reduced-motion" in css
    # the shipped ui_kit values must be preserved exactly (no visual regression)
    for legacy in ("--bg-2:#111824", "--line:#1c2937", "--ink-2:#9bb0c6", "--accent-cy:#34e0d6"):
        assert legacy in css, f"palette drift: {legacy}"
    print("ui_tokens selftest OK — tokens + base + a11y + density; palette preserved")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
