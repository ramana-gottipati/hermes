"""src/web/home/shell.py — the Graphite home page shell (spec §4).

Renders a complete `data-ui-g` document with its OWN chrome — deliberately free of every legacy
marker (`.uk-sub`, `id="uk-main"`) AND every preview marker (`.pv3-*`, `data-ui-v3`), so neither
`shell_skin`/`left_rail` middleware nor anything else can reshape it, and the isolation gate can
prove separation in both directions. Imports only the home token + component layers.
"""
from __future__ import annotations

import html as _html

from src.web.home import components as C
from src.web.home.tokens import tokens_css

# The 6 destinations. Graphite twins don't exist yet, so non-Today links point at the classic
# routes (one-way home->classic is allowed; the classic site never links back — gate-tested).
DESTS = [("Today", "/dash/home"), ("Markets", "/dash/markets"), ("Stocks", "/dash/stocks"),
         ("Strategies", "/dash/strategist"), ("Tracker", "/dash/tracker/dashboard"),
         ("Proof", "/dash/coverage")]

_FENCE = ("Descriptive only — everything here is past data from primary exchange sources "
          "(NSE · BSE). Never advice, a recommendation, or a prediction.")

_SHELL_CSS = """<style>/* g-shell */
:root[data-ui-g] .g-top{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:14px;
  padding:11px 22px;background:color-mix(in srgb,var(--bg-1) 84%,transparent);
  border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}
:root[data-ui-g] .g-brand{font-weight:800;font-size:18px;letter-spacing:.3px;text-shadow:0 0 22px var(--glow)}
:root[data-ui-g] .g-brand small{font-weight:500;color:var(--ink-3);font-size:11px;margin-left:9px}
:root[data-ui-g] .g-badge{font:600 9.5px/1 var(--mono);letter-spacing:.14em;color:var(--accent);
  background:var(--acc-dim);border:1px solid var(--accent);border-radius:var(--r-pill);padding:4px 9px}
:root[data-ui-g] .g-destbar{display:flex;padding:0 22px;background:var(--bg-1);border-bottom:1px solid var(--line);position:sticky;top:52px;z-index:39;overflow-x:auto;scrollbar-width:none}
:root[data-ui-g] .g-destbar::-webkit-scrollbar{display:none}
:root[data-ui-g] .g-dests{display:flex;gap:2px}
:root[data-ui-g] .g-dests a{font:600 11px/1 var(--font);letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-2);padding:10px 12px;white-space:nowrap;border-bottom:2px solid transparent;text-decoration:none}
:root[data-ui-g] .g-dests a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--accent)}
:root[data-ui-g] .g-dests a:hover{color:var(--ink)}
:root[data-ui-g] .g-sp{flex:1}
:root[data-ui-g] .g-wrap{max-width:1300px;margin:0 auto;padding:20px 22px 90px}
:root[data-ui-g] .g-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
@media(min-width:1200px){ :root[data-ui-g] .g-grid.has-rail{grid-template-columns:minmax(0,1fr) 320px} }
:root[data-ui-g] .g-rail{display:flex;flex-direction:column;gap:14px}
:root[data-ui-g] .g-foot{max-width:1300px;margin:0 auto;padding:16px 22px;border-top:1px solid var(--line);
  color:var(--ink-3);font-size:11.5px;text-align:center}
:root[data-ui-g] .g-seg{display:inline-flex;background:var(--bg-2);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:3px;gap:2px}
:root[data-ui-g] .g-seg button{border:0;background:transparent;color:var(--ink-3);font:700 11.5px var(--font);padding:6px 12px;border-radius:var(--r-pill);cursor:pointer}
:root[data-ui-g] .g-seg button[aria-pressed="true"]{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .new-only{display:none}
:root[data-ui-g][data-persona="new"] .new-only{display:revert}
:root[data-ui-g] .pro-only{display:none}
:root[data-ui-g][data-persona="pro"] .pro-only{display:revert}
</style>"""

_PERSONA_JS = """<script>(function(){var r=document.documentElement,k="pvgmode";
try{if(localStorage.getItem(k)==="pro")r.setAttribute("data-persona","pro");}catch(e){}
function set(m){r.setAttribute("data-persona",m);
var n=document.getElementById("g-mnew"),p=document.getElementById("g-mpro");
if(n)n.setAttribute("aria-pressed",m==="new");if(p)p.setAttribute("aria-pressed",m==="pro");
try{localStorage.setItem(k,m);}catch(e){}}
document.addEventListener("DOMContentLoaded",function(){
var n=document.getElementById("g-mnew"),p=document.getElementById("g-mpro");
if(n)n.addEventListener("click",function(){set("new");});
if(p)p.addEventListener("click",function(){set("pro");});
set(r.getAttribute("data-persona")||"new");});})();</script>"""

_THEME_JS = """<script>(function(){var r=document.documentElement,k="pvgtheme";
try{if(localStorage.getItem(k)==="light")r.setAttribute("data-theme","light");}catch(e){}
window.pvgTheme=function(){var l=r.getAttribute("data-theme")==="light";
if(l)r.removeAttribute("data-theme");else r.setAttribute("data-theme","light");
try{localStorage.setItem(k,l?"dark":"light");}catch(e){}};})();</script>"""


def _dests(current: str) -> str:
    out = ['<nav class="g-dests" aria-label="Destinations">']
    for label, href in DESTS:
        cur = ' aria-current="page"' if label == current else ""
        out.append('<a href="' + _html.escape(href) + '"' + cur + ">" + _html.escape(label) + "</a>")
    out.append("</nav>")
    return "".join(out)


def shell(title: str, body_html: str, rail_html: str = "", extra_head: str = "",
          current: str = "Today", pat_html: str = "") -> str:
    t = _html.escape(str(title))
    grid_cls = "g-grid has-rail" if rail_html else "g-grid"
    rail = ('<aside class="g-rail" aria-label="Context">' + rail_html + "</aside>") if rail_html else ""
    return (
        '<!doctype html><html lang="en" data-ui-g data-persona="new"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        "<title>" + t + " — patearn</title>"
        + tokens_css() + C.css() + _SHELL_CSS + extra_head + "</head><body>"
        '<header class="g-top"><span class="g-brand">patearn<small>Indian-equity evidence</small></span>'
        '<span class="g-badge">PREVIEW</span><span class="g-sp"></span>'
        '<span class="g-seg" role="group" aria-label="Experience mode">'
        '<button id="g-mnew" type="button" aria-pressed="true">✦ New here</button>'
        '<button id="g-mpro" type="button" aria-pressed="false">⚡ Pro</button></span>'
        '<button class="g-btn" style="margin:0" onclick="pvgTheme()" aria-label="Switch light/dark theme">◑ Theme</button>'
        '<a class="g-btn" style="margin:0" href="/dash">Classic site</a>'
        "</header>"
        '<nav class="g-destbar">' + _dests(current) + "</nav>"
        '<main class="g-wrap">' + C.fence(_FENCE)
        + '<div class="' + grid_cls + '"><div class="g-focus">' + body_html + "</div>" + rail + "</div></main>"
        '<footer class="g-foot">' + _html.escape(_FENCE) + "</footer>"
        + pat_html + _THEME_JS + _PERSONA_JS + C.assets() + "</body></html>"
    )
