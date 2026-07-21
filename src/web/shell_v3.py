"""shell_v3.py — the v3 preview page shell (redesign M1; M4 adds the ratified nav contract).

Renders a complete v3 document: destination bar (the 6 destinations, "you are here" marked —
Part II §C.1), optional per-destination LEFT NAV RAIL in fixed order with the user-invoked
collapse/expand control (§C.2 as amended: visible by default, localStorage-persisted), optional
breadcrumb (§C.3, canonical hierarchy), the Focus/Context grid, the M3 dock slot, and the
footer fence. Used ONLY by v3 preview routes; no legacy module imports this file.

Deliberate non-markers: this HTML must NEVER contain the strings the runtime chrome wraps key
on — no `.uk-sub`, no `id="uk-main"` — so `left_rail`'s middleware and `shell_skin` can never
reshape a v3 page (verified by tests/test_v3_isolation.py).

Backward compatible: `shell(title, focus)` with no nav args renders exactly the M1-era layout
(topbar + grid + dock slot) — the preview landing and showcase are unaffected.
"""
from __future__ import annotations

import html as _html

from src.web.ui_tokens_v3 import tokens_css_v3

# The 6 ratified destinations (Part I §4 · Part II §C.1). Fixed order — never varies per page.
# Preview pages may link classic routes for destinations whose v3 twins don't exist yet
# (one-way preview→classic links are allowed; the default site never links the preview).
DESTS: list[tuple[str, str]] = [
    ("today", "Today"), ("markets", "Markets"), ("stocks", "Stocks"),
    ("strategies", "Strategies"), ("tracker", "Tracker"), ("proof", "Proof"),
]
_DEST_HREF = {
    "today": "/dash/preview", "markets": "/dash/markets", "stocks": "/dash/preview",
    "strategies": "/dash/strategist", "tracker": "/dash/tracker/dashboard",
    "proof": "/dash/coverage",
}

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
/* ── destination bar (§C.1): identical everywhere, current marked ── */
.pv3-dests{display:flex;gap:2px;padding:0 var(--gutter);background:var(--bg-1);
  border-bottom:1px solid var(--line);overflow-x:auto}
.pv3-dests a{padding:9px 14px;color:var(--ink-2);font-size:var(--t-sm);font-weight:500;
  border-bottom:2px solid transparent;white-space:nowrap}
.pv3-dests a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
/* ── breadcrumb (§C.3) ── */
.pv3-crumbs{padding:8px var(--gutter);font-size:var(--t-xs);color:var(--ink-3)}
.pv3-crumbs a{color:var(--ink-3)} .pv3-crumbs a:hover{color:var(--accent)}
.pv3-crumbs .sep{margin:0 6px;color:var(--ink-3)}
.pv3-crumbs .cur{color:var(--ink-2);font-weight:600}
/* ── grid: [nav][focus][context] — nav rail collapsible (§C.2 amended) ── */
.pv3-wrap{max-width:1560px;margin:0 auto;padding:var(--s-4) var(--gutter)}
.pv3-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-4)}
@media (min-width:1280px){
  .pv3-grid.has-rail{grid-template-columns:minmax(0,1fr) 340px}
  .pv3-grid.has-nav{grid-template-columns:190px minmax(0,1fr)}
  .pv3-grid.has-nav.has-rail{grid-template-columns:190px minmax(0,1fr) 340px}
  html.pv3-nav-off .pv3-grid.has-nav{grid-template-columns:minmax(0,1fr)}
  html.pv3-nav-off .pv3-grid.has-nav.has-rail{grid-template-columns:minmax(0,1fr) 340px}
  html.pv3-nav-off .pv3-navrail{display:none}
}
@media (max-width:1279px){ .pv3-navrail{display:none} }
.pv3-navrail{min-width:0}
.pv3-navrail .hd{font-size:var(--t-xs);font-weight:600;color:var(--ink-3);
  text-transform:uppercase;letter-spacing:.5px;margin:4px 0 8px;display:flex;align-items:center}
.pv3-navrail .hd .pv3-btn{margin-left:auto;padding:2px 8px;font-size:var(--t-xs)}
.pv3-navrail a{display:block;padding:7px 10px;border-radius:var(--r-sm);color:var(--ink-2);
  font-size:var(--t-sm)}
.pv3-navrail a.on{background:var(--accent-dim);color:var(--accent);font-weight:600}
.pv3-navshow{display:none}
html.pv3-nav-off .pv3-navshow{display:inline-block}
.pv3-focus{min-width:0}
.pv3-rail{min-width:0;display:flex;flex-direction:column;gap:var(--s-3)}
.pv3-foot{margin:var(--s-6) 0 var(--s-4);padding:var(--s-3) var(--gutter);
  border-top:1px solid var(--line);color:var(--ink-3);font-size:var(--t-xs);text-align:center}
.pv3-dockwrap{max-width:1560px;margin:var(--s-4) auto 0;padding:0}
@media (max-width:640px){
  .pv3-top{flex-wrap:wrap;row-gap:6px}
  .pv3-brand small{display:none}
}
</style>"""

_THEME_JS = """<script>(function(){
var r=document.documentElement,k="pv3theme",n="pv3nav";
try{if(localStorage.getItem(k)==="light")r.setAttribute("data-theme","light");}catch(e){}
try{if(localStorage.getItem(n)==="off")r.classList.add("pv3-nav-off");}catch(e){}
window.pv3Theme=function(){
  var l=r.getAttribute("data-theme")==="light";
  if(l){r.removeAttribute("data-theme");}else{r.setAttribute("data-theme","light");}
  try{localStorage.setItem(k,l?"dark":"light");}catch(e){}
};
window.pv3Nav=function(){
  var off=r.classList.toggle("pv3-nav-off");
  try{localStorage.setItem(n,off?"off":"on");}catch(e){}
};})();</script>"""

_FENCE_FOOT = ("patearn preview — everything here describes the past from primary exchange data; "
               "it is never investment advice or a recommendation.")


def _dest_bar(dest: str) -> str:
    out = ['<nav class="pv3-dests" aria-label="Destinations">']
    for key, label in DESTS:
        if key == dest:
            out.append('<a href="' + _DEST_HREF[key] + '" aria-current="page">' + label + "</a>")
        else:
            out.append('<a href="' + _DEST_HREF[key] + '">' + label + "</a>")
    out.append("</nav>")
    return "".join(out)


def _crumb_bar(crumbs: list[tuple[str, str]]) -> str:
    """crumbs = [(label, href)] canonical ancestors; last item = current page (href ignored)."""
    parts = []
    for i, (label, href) in enumerate(crumbs):
        if i == len(crumbs) - 1:
            parts.append('<span class="cur">' + _html.escape(label) + "</span>")
        else:
            parts.append('<a href="' + _html.escape(href) + '">' + _html.escape(label) + "</a>")
    sep = '<span class="sep">›</span>'
    return '<nav class="pv3-crumbs" aria-label="Breadcrumb">' + sep.join(parts) + "</nav>"


def _nav_rail(title: str, items: list[tuple[str, str, bool]]) -> str:
    """items = [(label, href, active)] — the destination's sub-views, FIXED order (§C.1)."""
    out = ['<nav class="pv3-navrail" aria-label="' + _html.escape(title) + ' pages">',
           '<div class="hd">' + _html.escape(title)
           + '<button class="pv3-btn" onclick="pv3Nav()" aria-label="Collapse navigation">⟨</button></div>']
    for label, href, active in items:
        cls = ' class="on" aria-current="page"' if active else ""
        out.append("<a" + cls + ' href="' + _html.escape(href) + '">' + _html.escape(label) + "</a>")
    out.append("</nav>")
    return "".join(out)


def shell(title: str, focus_html: str, rail_html: str = "", extra_head: str = "",
          dock_html: str = "", dest: str = "", crumbs=None, nav_title: str = "",
          nav_items=None) -> str:
    """A complete v3 document.

    Nav contract (M4 req #0): `dest` marks the current destination in the fixed 6-item bar;
    `crumbs` renders the canonical breadcrumb; `nav_title`+`nav_items` render the destination's
    left rail (visible by default; the ⟨ control collapses it, the ⟩ button in the top bar
    brings it back — localStorage-persisted). All optional: omitting them renders the M1 layout.
    """
    t = _html.escape(str(title))
    grid_cls = "pv3-grid"
    navrail = ""
    if nav_items:
        grid_cls += " has-nav"
        navrail = _nav_rail(nav_title or "Pages", nav_items)
    if rail_html:
        grid_cls += " has-rail"
    rail = ('<aside class="pv3-rail" aria-label="Context">' + rail_html + "</aside>") if rail_html else ""
    dock = ('<section class="pv3-dockwrap" aria-label="News and flow">' + dock_html
            + "</section>") if dock_html else ""
    dests = _dest_bar(dest) if dest else ""
    crumbbar = _crumb_bar(crumbs) if crumbs else ""
    navshow = ('<button class="pv3-btn pv3-navshow" onclick="pv3Nav()" '
               'aria-label="Expand navigation">⟩ Nav</button>') if nav_items else ""
    return ("<!doctype html><html lang=\"en\" data-ui-v3><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex\">"
            "<title>" + t + " — patearn preview</title>"
            + tokens_css_v3() + _SHELL_CSS + extra_head + "</head><body>"
            "<header class=\"pv3-top\">"
            "<span class=\"pv3-brand\">patearn<small>Indian-equity evidence, described</small></span>"
            "<span class=\"pv3-badge\">PREVIEW</span>"
            "<span class=\"pv3-sp\"></span>" + navshow +
            "<button class=\"pv3-btn\" onclick=\"pv3Theme()\" aria-label=\"Switch light/dark theme\">Theme</button>"
            "<a class=\"pv3-btn\" href=\"/dash\">Classic site</a>"
            "</header>"
            + dests + crumbbar +
            "<main class=\"pv3-wrap\"><div class=\"" + grid_cls + "\">"
            + navrail +
            "<div class=\"pv3-focus\">" + focus_html + "</div>" + rail + "</div>"
            + dock + "</main>"
            "<footer class=\"pv3-foot\">" + _FENCE_FOOT + "</footer>"
            + _THEME_JS + "</body></html>")


def _selftest() -> int:
    doc = shell("T", "<p>focus</p>", "<p>rail</p>")
    assert "data-ui-v3" in doc and "PREVIEW" in doc and "uk-tokens v3" in doc
    assert "focus" in doc and "rail" in doc and "has-rail" in doc
    assert "uk-sub" not in doc and "uk-main" not in doc and "v2bar" not in doc
    assert "never investment advice" in doc
    # M1-compat: no nav chrome MARKUP unless asked (CSS strings always present)
    assert '<nav class="pv3-dests"' not in doc and '<nav class="pv3-navrail"' not in doc
    assert '<nav class="pv3-crumbs"' not in doc
    solo = shell("T", "<p>x</p>")
    assert 'pv3-grid has-rail' not in solo and "<aside" not in solo
    docked = shell("T", "<p>x</p>", dock_html="<p>dockbody</p>")
    assert "pv3-dockwrap" in docked and "dockbody" in docked
    # the nav contract (M4 req #0)
    full = shell("T", "<p>x</p>", "<p>r</p>", dest="stocks",
                 crumbs=[("Home", "/dash/preview"), ("Stocks", "/dash/preview"), ("TCS", "")],
                 nav_title="Stocks", nav_items=[("Screener", "/dash/screen2", False),
                                                ("TCS dossier", "#", True)])
    body = full.split("</head>", 1)[1]
    assert body.count('aria-current="page"') == 2          # dest bar + rail active (CSS excluded)
    assert 'aria-current="page">Stocks' in full             # you-are-here in the bar
    assert "pv3-crumbs" in full and '<span class="cur">TCS</span>' in full
    assert "pv3-navrail" in full and "pv3Nav()" in full and "pv3-navshow" in full
    assert full.index("pv3-dests") < full.index("pv3-crumbs") < full.index("pv3-grid")
    assert len(DESTS) == 6
    print("shell_v3 selftest OK — grid, themes, nav contract (bar+crumbs+rail+collapse)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
