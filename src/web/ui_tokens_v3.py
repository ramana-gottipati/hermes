"""ui_tokens_v3.py — the OPT-IN v3 theme foundation (redesign M1).

A NEW, parallel token layer for the v3 preview experience (docs/redesign-plan-2026-07-17.md §5;
approvals + review dispositions: docs/redesign-coordination.md). It does NOT edit or replace
`ui_tokens.py` — the live default look is untouched (the S177 additive-only rule). v3 pages are
whole documents rendered by `shell_v3.py`; nothing here is injected into legacy pages.

Isolation (Gemini review A3): every token is defined on `:root[data-ui-v3]` and every component
class is `.pv3-*`, so even if this CSS ever reached a legacy page it could not restyle it.

Two themes from day one: dark (default, matches the current product) and light via
`[data-theme="light"]`. The value contract (--up/--down/--warn) and categorical series hues are
inherited from the v1 palette so charts and signed values read identically across eras.

Public API:
    tokens_css_v3() -> the <style> block. Include ONCE per v3 page (shell_v3 does this).
    FONT / MONO    -> font stacks (re-exported from ui_tokens so the stacks never fork).

Isolation: imports ONLY ui_tokens (a leaf) for the font stacks. Additive + reversible.
"""
from __future__ import annotations

from src.web.ui_tokens import FONT, MONO

TOKENS_V3_MARKER = "/* uk-tokens v3 */"

_CSS = """<style>""" + TOKENS_V3_MARKER + """
:root[data-ui-v3]{
  /* ── surfaces (dark default) ── */
  --bg-0:#070a10; --bg-1:#0c1118; --bg-2:#121a26; --bg-3:#192433; --bg-4:#213043;
  --line:#1e2b3a; --line-2:#2a3d51;
  --ink:#eaf1f9; --ink-2:#9bb0c6; --ink-3:#7e90a8;
  /* value contract + accents — inherited verbatim from the v1 palette (no re-learning) */
  --accent:#4d9dff; --accent-dim:rgba(77,157,255,.14); --on-accent:#06121f;
  --up:#3fd486; --down:#ff6a7a; --warn:#f6b73c;
  --up-rgb:63,212,134; --down-rgb:255,106,122; --warn-rgb:246,183,60;
  --series-1:#39c5cf; --series-2:#f0883e; --series-3:#a371f7; --series-4:#56d364;
  /* ── type: 6 steps, numbers first-class ── */
  --t-xs:11.5px; --t-sm:13px; --t-md:15px; --t-lg:17px; --t-xl:21px; --t-2xl:27px;
  --lh:1.55; --lh-tight:1.25;
  /* ── 8px rhythm ── */
  --s-1:4px; --s-2:8px; --s-3:16px; --s-4:24px; --s-5:32px; --s-6:48px;
  --gutter:24px; --r-sm:8px; --r:12px; --r-pill:999px;
  --e-1:0 1px 2px rgba(0,0,0,.30); --e-2:0 8px 24px rgba(0,0,0,.35);
  --t-fast:150ms ease-out; --t-med:200ms ease-out;
  --font:""" + FONT + """; --mono:""" + MONO + """;
}
/* ── light theme (both ship day one; cut-over is a choice, not a bet) ── */
:root[data-ui-v3][data-theme="light"]{
  --bg-0:#f5f7fa; --bg-1:#ffffff; --bg-2:#ffffff; --bg-3:#eef2f7; --bg-4:#e4eaf2;
  --line:#d7dfe8; --line-2:#c2cedb;
  --ink:#131c26; --ink-2:#41566c; --ink-3:#5f7590;
  --accent:#1668cc; --accent-dim:rgba(22,104,204,.10); --on-accent:#ffffff;
  --up:#0e8a4d; --down:#c92a3c; --warn:#a06a00;
  --up-rgb:14,138,77; --down-rgb:201,42,60; --warn-rgb:160,106,0;
  --e-1:0 1px 2px rgba(16,32,48,.08); --e-2:0 8px 24px rgba(16,32,48,.10);
}
/* ── base (scoped: only a data-ui-v3 document is ever styled) ── */
:root[data-ui-v3] body{margin:0;background:var(--bg-0);color:var(--ink);
  font:400 var(--t-md)/var(--lh) var(--font);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
:root[data-ui-v3] *{box-sizing:border-box}
:root[data-ui-v3] a{color:var(--accent);text-decoration:none}
:root[data-ui-v3] a:hover{text-decoration:underline}
:root[data-ui-v3] .pv3-num{font-family:var(--mono);font-variant-numeric:tabular-nums}
:root[data-ui-v3] :where(a,button,input,select,summary,[tabindex]):focus-visible{
  outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
@media (prefers-reduced-motion:reduce){
  :root[data-ui-v3] *,:root[data-ui-v3] *::before,:root[data-ui-v3] *::after{
    animation-duration:.001ms!important;transition-duration:.001ms!important}
}
/* every wide element scrolls in its own container — the page body NEVER scrolls sideways */
:root[data-ui-v3] .pv3-scroll{overflow-x:auto;max-width:100%}
:root[data-ui-v3] img,:root[data-ui-v3] svg{max-width:100%}
@media (max-width:640px){ :root[data-ui-v3]{ --gutter:14px } }
</style>"""


def tokens_css_v3() -> str:
    """The v3 foundation <style> block (tokens + base + a11y). One per v3 page."""
    return _CSS


def _selftest() -> int:
    css = tokens_css_v3()
    assert TOKENS_V3_MARKER in css
    for tok in ("data-ui-v3", 'data-theme="light"', "--up:#3fd486", "--down:#ff6a7a",
                "--t-md:15px", "--s-3:16px", "tabular-nums", "prefers-reduced-motion",
                "pv3-scroll"):
        assert tok in css, "missing " + tok
    # the v1 value contract survives verbatim in the dark theme (no re-learning)
    assert "--up-rgb:63,212,134" in css and "--down-rgb:255,106,122" in css
    # isolation: nothing may target bare :root or legacy scopes
    assert ":root{" not in css and "uk-skin" not in css and ".uk " not in css
    print("ui_tokens_v3 selftest OK — scoped, two themes, value contract preserved")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
