"""shell_v3.py — the v3 preview page shell (redesign M1). ADDITIVE, opt-in only.

Renders a complete v3 document: top bar (identity + preview badge + theme toggle + back-to-
classic link), the Focus/Context grid, and the footer fence. Used ONLY by v3 preview routes
(`v3_preview.py`, `ui_showcase_v3.py`); no legacy module imports this file.

Deliberate non-markers: this HTML must NEVER contain the strings the runtime chrome wraps key
on — no `.uk-sub`, no `id="uk-main"` — so `left_rail`'s middleware and `shell_skin` can never
reshape a v3 page (verified by tests/test_v3_isolation.py).

Layout contract (docs/redesign-plan-2026-07-17.md §3): ≥1280px Focus + Context rail side by
side; below that the rail stacks under the Focus column; every wide element scrolls inside its
own container (`.pv3-scroll`), the body never scrolls horizontally.
"""
from __future__ import annotations

import html as _html

from src.web.ui_tokens_v3 import tokens_css_v3

_SHELL_CSS = """<style>
.pv3-top{display:flex;align-items:center;gap:var(--s-3);padding:10px var(--gutter);
  background:var(--bg-1);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:30}
.pv3-brand{font-weight:700;font-size:var(--t-lg);color:var(--ink);letter-spacing:.2px}
.pv3-brand small{color:var(--ink-3);font-weight:500;margin-left:8px;font-size:var(--t-xs)}
.pv3-badge{background:var(--accent-dim);color:var(--accent);border:1px solid var(--accent);
  border-radius:var(--r-pill);padding:2px 10px;font-size:var(--t-xs);font-weight:600}
.pv3-top .pv3-sp{flex:1}
.pv3-btn{background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink-2);
  border-radius:var(--r-sm);padding:6px 12px;font:500 var(--t-sm) var(--font);cursor:pointer}
.pv3-btn:hover{border-color:var(--accent);color:var(--ink)}
.pv3-wrap{max-width:1480px;margin:0 auto;padding:var(--s-4) var(--gutter)}
.pv3-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-4)}
@media (min-width:1280px){ .pv3-grid.has-rail{grid-template-columns:minmax(0,1fr) 340px} }
.pv3-focus{min-width:0}
.pv3-rail{min-width:0;display:flex;flex-direction:column;gap:var(--s-3)}
.pv3-foot{margin:var(--s-6) 0 var(--s-4);padding:var(--s-3) var(--gutter);
  border-top:1px solid var(--line);color:var(--ink-3);font-size:var(--t-xs);text-align:center}
@media (max-width:640px){
  .pv3-top{flex-wrap:wrap;row-gap:6px}
  .pv3-brand small{display:none}
}
</style>"""

# theme toggle: localStorage-backed, no dependency, ~10 lines
_THEME_JS = """<script>(function(){
var r=document.documentElement,k="pv3theme";
try{var s=localStorage.getItem(k);if(s==="light")r.setAttribute("data-theme","light");}catch(e){}
window.pv3Theme=function(){
  var l=r.getAttribute("data-theme")==="light";
  if(l){r.removeAttribute("data-theme");}else{r.setAttribute("data-theme","light");}
  try{localStorage.setItem(k,l?"dark":"light");}catch(e){}
};})();</script>"""

_FENCE_FOOT = ("patearn preview — everything here describes the past from primary exchange data; "
               "it is never investment advice or a recommendation.")


def shell(title: str, focus_html: str, rail_html: str = "", extra_head: str = "") -> str:
    """A complete v3 document. `rail_html` empty => single-column Focus layout."""
    t = _html.escape(str(title))
    rail_cls = " has-rail" if rail_html else ""
    rail = ('<aside class="pv3-rail" aria-label="Context">' + rail_html + "</aside>") if rail_html else ""
    return ("<!doctype html><html lang=\"en\" data-ui-v3><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex\">"
            "<title>" + t + " — patearn preview</title>"
            + tokens_css_v3() + _SHELL_CSS + extra_head + "</head><body>"
            "<header class=\"pv3-top\">"
            "<span class=\"pv3-brand\">patearn<small>Indian-equity evidence, described</small></span>"
            "<span class=\"pv3-badge\">PREVIEW</span>"
            "<span class=\"pv3-sp\"></span>"
            "<button class=\"pv3-btn\" onclick=\"pv3Theme()\" aria-label=\"Switch light/dark theme\">Theme</button>"
            "<a class=\"pv3-btn\" href=\"/dash\">Classic site</a>"
            "</header>"
            "<main class=\"pv3-wrap\"><div class=\"pv3-grid" + rail_cls + "\">"
            "<div class=\"pv3-focus\">" + focus_html + "</div>" + rail + "</div></main>"
            "<footer class=\"pv3-foot\">" + _FENCE_FOOT + "</footer>"
            + _THEME_JS + "</body></html>")


def _selftest() -> int:
    doc = shell("T", "<p>focus</p>", "<p>rail</p>")
    assert "data-ui-v3" in doc and "PREVIEW" in doc and "uk-tokens v3" in doc
    assert "focus" in doc and "rail" in doc and "has-rail" in doc
    # the non-marker contract: never trip the legacy chrome transforms
    assert "uk-sub" not in doc and "uk-main" not in doc and "v2bar" not in doc
    assert "never investment advice" in doc
    solo = shell("T", "<p>x</p>")
    assert 'pv3-grid has-rail' not in solo and "<aside" not in solo  # CSS strings remain; markup must not
    print("shell_v3 selftest OK — grid, themes, no legacy markers")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
