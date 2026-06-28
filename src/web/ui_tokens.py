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
  --ink:#eaf1f9; --ink-2:#9bb0c6; --ink-3:#5c6f84; --ink-4:#3c4a5c;
  /* ── accents + semantics ── */
  --accent:#4d9dff; --accent-2:#6db3ff; --accent-cy:#34e0d6; --accent-dim:rgba(77,157,255,.14);
  --up:#3fd486; --up-dim:rgba(63,212,134,.13);
  --down:#ff6a7a; --down-dim:rgba(255,106,122,.13);
  --warn:#f6b73c; --warn-dim:rgba(246,183,60,.14);
  --cred:#b18cff; --cred-dim:rgba(177,140,255,.15);
  /* ── type scale (tabular instrument feel) ── */
  --fs-2xs:10.5px; --fs-xs:11.5px; --fs-sm:12.5px; --fs-md:14px; --fs-lg:16px;
  --fs-xl:19px; --fs-2xl:23px; --fs-3xl:30px;
  --lh:1.5; --lh-tight:1.25;
  --fw-med:500; --fw-semi:600; --fw-bold:700;
  /* ── spacing scale ── */
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:22px; --sp-6:30px; --sp-7:44px; --sp-8:64px;
  --gutter:20px;            /* page side padding — shrinks on mobile (see base) */
  --row-pad:10px;          /* table/list row padding — driven by density */
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
  --row-pad:6px; --fs-md:13px; --fs-sm:12px; --gutter:14px;
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
</style>"""


def tokens_css() -> str:
    """The shared foundation `<style>` block (tokens + base + a11y + density). One per page."""
    return _TOKENS_CSS


def _selftest() -> int:
    css = tokens_css()
    assert TOKENS_MARKER in css
    for tok in ("--bg-1:#0b0f17", "--accent:#4d9dff", "--ink:#eaf1f9", "--up:#3fd486",
                "--down:#ff6a7a", "--fs-md:14px", "--sp-4:16px", "--r:12px"):
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
