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
/* tier mechanism: Free shows the guided explainers (.free-only); Pro hides them (denser) AND reveals
   the premium relative-context blocks (.pro-more) — the reference points that make a bare number useful. */
:root[data-ui-g] .free-only{display:none}
:root[data-ui-g][data-tier="free"] .free-only{display:revert}
:root[data-ui-g] .pro-more{display:none}
:root[data-ui-g][data-tier="pro"] .pro-more{display:revert}
/* the classic-site directory (top-right dropdown) */
:root[data-ui-g] .g-classic{position:relative}
:root[data-ui-g] .g-classic>summary{list-style:none;cursor:pointer}
:root[data-ui-g] .g-classic>summary::-webkit-details-marker{display:none}
:root[data-ui-g] .g-classic-menu{position:absolute;right:0;top:calc(100% + 8px);z-index:50;width:min(780px,92vw);
  max-height:min(70vh,540px);overflow-y:auto;background:linear-gradient(165deg,var(--bg-2),var(--bg-1));
  border:1px solid var(--line-2);border-radius:14px;box-shadow:0 26px 64px -20px rgba(0,0,0,.7);padding:15px 17px;scrollbar-width:thin}
:root[data-ui-g] .g-cl-head{font-size:12px;color:var(--ink-3);margin-bottom:13px;line-height:1.55}
:root[data-ui-g] .g-cl-head b{color:var(--ink)}
:root[data-ui-g] .g-cl-home{margin-left:6px;color:var(--accent);font-weight:600;white-space:nowrap;text-decoration:none}
:root[data-ui-g] .g-cl-home:hover{text-decoration:underline}
:root[data-ui-g] .g-cl-cols{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:16px 18px}
:root[data-ui-g] .g-cl-col h4{margin:0 0 6px;font:700 10.5px var(--font);letter-spacing:.08em;text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--line);padding-bottom:5px}
:root[data-ui-g] .g-cl-col a{display:block;font-size:12.5px;color:var(--ink-2);text-decoration:none;padding:3px 0;line-height:1.35}
:root[data-ui-g] .g-cl-col a:hover{color:var(--accent)}
:root[data-ui-g] .g-cl-sub{font:600 9px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:9px 0 3px}
@media(max-width:560px){:root[data-ui-g] .g-classic-menu{position:fixed;left:2vw;right:2vw;width:96vw}}
</style>"""

_TIER_JS = """<script>(function(){var r=document.documentElement,k="pvgtier";
try{if(localStorage.getItem(k)==="pro")r.setAttribute("data-tier","pro");}catch(e){}
function set(m){r.setAttribute("data-tier",m);
var f=document.getElementById("g-tfree"),p=document.getElementById("g-tpro");
if(f)f.setAttribute("aria-pressed",m==="free");if(p)p.setAttribute("aria-pressed",m==="pro");
try{localStorage.setItem(k,m);}catch(e){}}
document.addEventListener("DOMContentLoaded",function(){
var f=document.getElementById("g-tfree"),p=document.getElementById("g-tpro");
if(f)f.addEventListener("click",function(){set("free");});
if(p)p.addEventListener("click",function(){set("pro");});
document.querySelectorAll(".g-proad-cta").forEach(function(b){b.addEventListener("click",function(){set("pro");});});
set(r.getAttribute("data-tier")||"free");});})();</script>"""

_THEME_JS = """<script>(function(){var r=document.documentElement,k="pvgtheme";
try{if(localStorage.getItem(k)==="light")r.setAttribute("data-theme","light");}catch(e){}
window.pvgTheme=function(){var l=r.getAttribute("data-theme")==="light";
if(l)r.removeAttribute("data-theme");else r.setAttribute("data-theme","light");
try{localStorage.setItem(k,l?"dark":"light");}catch(e){}};})();</script>"""


# The whole classic site, bundled into the top-right "Classic site" affordance (owner ask). The
# list is GENERATED from the canonical lens registry (single source of truth) so it can never drift;
# rendered in Graphite chrome as one-way links — the classic site itself is byte-untouched. Trust is
# a right-side utility altitude, appended last as "Trust & help".
_ALT_LABELS = (("markets", "Markets"), ("screener", "Screener"),
               ("strategies", "Strategies"), ("tracker", "Tracker"), ("trust", "Trust & help"))

# POST-CUTOVER: the classic home lives at /dash/classic (the cutover middleware 302s bare /dash to
# this Graphite home, so linking /dash here would bounce the user straight back — a loop).
_CLASSIC_HOME = "/dash/classic"

_CLASSIC_FALLBACK = '<a class="g-btn" style="margin:0" href="' + _CLASSIC_HOME + '">Classic site</a>'


def _classic_directory() -> str:
    """A directory of the ENTIRE classic site in a top-right dropdown, generated from lens_registry.
    Defensive: any failure degrades to the plain classic-home link (never 500s the home). lens_registry
    imports nothing from the web layer, so reading it does not couple the home to a render module."""
    try:
        from src.web import lens_registry as LR
    except Exception:  # noqa: BLE001
        return _CLASSIC_FALLBACK
    cols = ""
    for alt, alt_label in _ALT_LABELS:
        try:
            lenses = LR.subnav(alt)
        except Exception:  # noqa: BLE001
            lenses = []
        if not lenses:
            continue
        items, cur_group = "", None
        for ln in lenses:
            g = getattr(ln, "group", None)
            if g and g != cur_group:
                items += '<div class="g-cl-sub">' + _html.escape(str(g)) + "</div>"
                cur_group = g
            elif not g:
                cur_group = None
            items += ('<a href="' + _html.escape(ln.route or "/dash") + '">' + _html.escape(ln.label) + "</a>")
        cols += '<div class="g-cl-col"><h4>' + _html.escape(alt_label) + "</h4>" + items + "</div>"
    if not cols:
        return _CLASSIC_FALLBACK
    return (
        '<details class="g-classic"><summary class="g-btn" style="margin:0" '
        'aria-label="Open the classic-site directory">Classic site <span aria-hidden="true">▾</span></summary>'
        '<div class="g-classic-menu" role="group" aria-label="Classic site — all pages">'
        '<div class="g-cl-head"><b>The classic site — every page.</b> Opens in the classic experience; '
        'this one stays separate. <a class="g-cl-home" href="' + _CLASSIC_HOME + '">Classic home →</a></div>'
        '<div class="g-cl-cols">' + cols + "</div></div></details>"
    )


_CLASSIC_JS = ('<script>(function(){var d=document.querySelector(".g-classic");if(!d)return;'
               'document.addEventListener("click",function(e){if(d.open&&!d.contains(e.target))d.open=false;});'
               'document.addEventListener("keydown",function(e){if(e.key==="Escape"&&d.open)d.open=false;});})();</script>')


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
        '<!doctype html><html lang="en" data-ui-g data-tier="free"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        "<title>" + t + " — patearn</title>"
        + tokens_css() + C.css() + _SHELL_CSS + extra_head + "</head><body>"
        '<header class="g-top"><span class="g-brand">patearn<small>Indian-equity evidence</small></span>'
        # POST-CUTOVER: this is the site's default landing, so the old "PREVIEW" badge would be
        # misleading chrome on a live front door. "NEW" is the honest label while the experience
        # is still fresh; the classic site stays one click away in the directory to its right.
        '<span class="g-badge">NEW</span><span class="g-sp"></span>'
        '<span class="g-seg" role="group" aria-label="Plan">'
        '<button id="g-tfree" type="button" aria-pressed="true">✦ Free</button>'
        '<button id="g-tpro" type="button" aria-pressed="false">⚡ Pro</button></span>'
        '<button class="g-btn" style="margin:0" onclick="pvgTheme()" aria-label="Switch light/dark theme">◑ Theme</button>'
        + _classic_directory()
        + "</header>"
        '<nav class="g-destbar">' + _dests(current) + "</nav>"
        '<main class="g-wrap">' + C.fence(_FENCE)
        + '<div class="' + grid_cls + '"><div class="g-focus">' + body_html + "</div>" + rail + "</div></main>"
        '<footer class="g-foot">' + _html.escape(_FENCE) + "</footer>"
        + pat_html + _THEME_JS + _TIER_JS + _CLASSIC_JS + C.assets() + "</body></html>"
    )
