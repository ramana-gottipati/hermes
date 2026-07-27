"""src/web/home/w2_kit.py — shared Graphite chrome for the W2-C Markets pages.

Lane-owned so the four page modules (seasonal · patterns · anatomy · compare) share ONE stylesheet
and ONE view-selector grammar without appending to `components.py` (which five sibling lanes are
editing concurrently). Everything here returns HTML only and never touches sqlite — the same
components/reads split the package is built on.

CSS is scoped `:root[data-ui-g] .w2-*` and injected through `shell(..., extra_head=...)`, so it can
neither reach the classic site nor collide with another lane's classes.
"""
from __future__ import annotations

from urllib.parse import quote, urlencode

from src.web.home import components as C

esc = C.esc

# The Graphite stock page (landed on main as `/dash/home/stock`, lane W1). Every symbol on a W2-C
# page resolves there, so the family never bounces a reader back into the classic dossier.
STOCK_PATH = "/dash/home/stock"


def num(v, dp: int = 2, dash: str = "—") -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dash
    if f != f:
        return dash
    return f"{f:,.{dp}f}"


def signed(v, dp: int = 2, unit: str = "") -> str:
    """A signed number with an up/dn class — used only where the sign is a factual direction."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '<span class="w2-z">—</span>'
    if f != f:
        return '<span class="w2-z">—</span>'
    cls = "w2-up" if f > 0 else ("w2-dn" if f < 0 else "w2-z")
    return '<span class="%s">%+.*f%s</span>' % (cls, dp, f, esc(unit))


def sym_link(symbol) -> str:
    """A symbol that deep-links to the GRAPHITE stock page (`/dash/home/stock?sym=`), not the
    classic dossier. Lane-owned rather than `components.sym_link` because that shared helper still
    pointed at `/dash/stock` on this lane's base — the stock lane has since retargeted it, so the two
    now agree. Escaping is identical (`esc` on the symbol, which is alnum-ish by construction)."""
    s = esc(symbol)
    return '<a class="g-syma" href="' + STOCK_PATH + "?sym=" + s + '">' + s + "</a>"


def href(path: str, **params) -> str:
    """A same-page link with the given query params (URL is the source of truth for view state)."""
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    return esc(path + ("?" + urlencode(clean, quote_via=quote) if clean else ""))


def view_bar(path: str, views, active: str, keep: dict = None, label: str = "View") -> str:
    """The lane's view selector — the honest consolidation control. `views` = ((key, label), ...)."""
    keep = keep or {}
    out = ['<div class="w2-vbar" role="group" aria-label="%s">' % esc(label)]
    for key, lab in views:
        on = " on" if key == active else ""
        out.append('<a class="w2-vb%s" href="%s"%s>%s</a>'
                   % (on, href(path, view=key, **keep),
                      ' aria-current="page"' if key == active else "", esc(lab)))
    out.append("</div>")
    return "".join(out)


def box(body_html: str, tall: bool = False) -> str:
    """A FIXED-SIZE box that scrolls INTERNALLY (standing correction #3) — never an endless page."""
    return '<div class="w2-box%s">%s</div>' % (" tall" if tall else "", body_html)


def table(head, rows_html: str, tall: bool = False) -> str:
    ths = "".join('<th%s>%s</th>' % ((' class="l"' if i == 0 else ""), h) for i, h in enumerate(head))
    return box('<table class="w2-tbl"><thead><tr>' + ths + "</tr></thead><tbody>"
               + (rows_html or '<tr><td colspan="%d" class="w2-z">Nothing to show.</td></tr>' % len(head))
               + "</tbody></table>", tall=tall)


def head_block(title: str, lede: str, prov_text: str = "", sample: bool = False) -> str:
    p = C.prov(prov_text, "", sample=sample) if prov_text else ""
    return ('<div class="w2-head"><h2>' + esc(title) + "</h2>" + p + "</div>"
            + '<p class="w2-lede">' + lede + "</p>")


def note(text_html: str) -> str:
    return '<p class="w2-note">' + text_html + "</p>"


def bar_row(label: str, value_html: str, pct: float, cls: str = "") -> str:
    """A horizontal magnitude bar — pct is 0-100 of the row width; sign drives the class."""
    try:
        p = max(0.0, min(100.0, float(pct)))
    except (TypeError, ValueError):
        p = 0.0
    return ('<div class="w2-bar %s"><span class="w2-bl">%s</span>'
            '<span class="w2-bt"><i style="width:%.1f%%"></i></span>'
            '<span class="w2-bv">%s</span></div>' % (esc(cls), esc(label), p, value_html))


# the lane's Markets pages — cross-linked so landing on one reaches the family
W2_PAGES = (("/dash/home/seasonal", "Seasonal"),
            ("/dash/home/patterns", "Patterns"),
            ("/dash/home/own-history", "Own history"),
            ("/dash/home/anatomy", "Move anatomy"),
            ("/dash/home/compare", "Compare"),
            ("/dash/home/rotation", "Rotation"))


def family_strip(current: str) -> str:
    """The sibling rail. A declared child that links nowhere is an orphan — this is the visible
    control that makes the five pages one family rather than five direct URLs."""
    cells = "".join(
        '<a class="%s" href="%s">%s</a>' % ("on" if path == current else "", esc(path), esc(lab))
        for path, lab in W2_PAGES)
    return ('<h3 class="w2-sect">More market context</h3><div class="w2-chips">' + cells + "</div>")


CSS = """<style>/* w2-markets */
:root[data-ui-g] .w2-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:2px 0 4px}
:root[data-ui-g] .w2-head h2{margin:0;font-size:17px;font-weight:800}
:root[data-ui-g] .w2-lede{margin:0 0 12px;font-size:13px;line-height:1.6;color:var(--ink-2);max-width:80ch}
:root[data-ui-g] .w2-lede b{color:var(--ink)}
:root[data-ui-g] .w2-note{margin:10px 0 0;font-size:12px;line-height:1.6;color:var(--ink-3);max-width:80ch}
:root[data-ui-g] .w2-note b{color:var(--ink-2)}
:root[data-ui-g] .w2-vbar{display:inline-flex;flex-wrap:wrap;gap:3px;background:var(--bg-2);
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:3px;margin:0 0 14px}
:root[data-ui-g] .w2-vb{font:700 12px var(--font);color:var(--ink-2);padding:7px 14px;
  border-radius:var(--r-pill);text-decoration:none;white-space:nowrap}
:root[data-ui-g] .w2-vb:hover{color:var(--ink)}
:root[data-ui-g] .w2-vb.on{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .w2-box{max-height:430px;overflow:auto;border:1px solid var(--line);
  border-radius:var(--r-sm);background:var(--bg-1);scrollbar-width:thin}
:root[data-ui-g] .w2-box.tall{max-height:620px}
:root[data-ui-g] .w2-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] .w2-tbl th{position:sticky;top:0;z-index:1;background:var(--bg-2);color:var(--ink-3);
  font:600 11px var(--font);text-align:right;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
:root[data-ui-g] .w2-tbl th.l,:root[data-ui-g] .w2-tbl td.l{text-align:left}
:root[data-ui-g] .w2-tbl td{padding:6px 10px;text-align:right;border-bottom:1px solid var(--line);
  color:var(--ink-2);font-variant-numeric:tabular-nums;white-space:nowrap}
:root[data-ui-g] .w2-tbl tbody tr:last-child td{border-bottom:0}
:root[data-ui-g] .w2-up{color:var(--up)}
:root[data-ui-g] .w2-dn{color:var(--dn,var(--down))}
:root[data-ui-g] .w2-z{color:var(--ink-3)}
:root[data-ui-g] .w2-pill{display:inline-block;font:700 10px var(--mono);letter-spacing:.06em;
  padding:2px 7px;border-radius:var(--r-pill);border:1px solid var(--line-2);color:var(--ink-3)}
:root[data-ui-g] .w2-pill.on{border-color:var(--accent);color:var(--accent)}
:root[data-ui-g] .w2-pill.warn{border-color:#c69316;color:#c69316}
/* the seasonal script grid — grey is the DEFAULT because most cells never certify */
:root[data-ui-g] .w2-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(64px,1fr));gap:6px}
:root[data-ui-g] .w2-cell{border:1px solid var(--line);border-radius:var(--r-sm);padding:8px 6px;
  text-align:center;background:var(--bg-2);text-decoration:none;display:block}
:root[data-ui-g] .w2-cell .k{display:block;font:700 11px var(--font);color:var(--ink-2)}
:root[data-ui-g] .w2-cell .v{display:block;font:800 14px var(--mono);color:var(--ink-3);margin-top:3px}
:root[data-ui-g] .w2-cell .h{display:block;font-size:10px;color:var(--ink-3);margin-top:2px}
:root[data-ui-g] .w2-cell.cert{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 13%,transparent)}
:root[data-ui-g] .w2-cell.cert .v{color:var(--ink)}
:root[data-ui-g] .w2-cell.sel{outline:2px solid var(--accent);outline-offset:1px}
:root[data-ui-g] .w2-legend{display:flex;flex-wrap:wrap;gap:14px;margin:9px 0 0;font-size:11.5px;color:var(--ink-3)}
:root[data-ui-g] .w2-legend b{color:var(--ink-2)}
:root[data-ui-g] .w2-sect{margin:20px 0 8px;font-size:14px;font-weight:700}
/* magnitude bars (move anatomy · own history) */
:root[data-ui-g] .w2-bar{display:grid;grid-template-columns:minmax(140px,1.4fr) minmax(90px,2fr) 78px;
  gap:10px;align-items:center;padding:6px 10px;border-bottom:1px solid var(--line);font-size:12.5px}
:root[data-ui-g] .w2-bar:last-child{border-bottom:0}
:root[data-ui-g] .w2-bl{color:var(--ink-2)}
:root[data-ui-g] .w2-bt{position:relative;height:9px;border-radius:5px;background:var(--bg-2);overflow:hidden}
:root[data-ui-g] .w2-bt i{position:absolute;left:0;top:0;bottom:0;border-radius:5px;
  background:linear-gradient(90deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .w2-bar.neg .w2-bt i{background:linear-gradient(90deg,#c96a5a,#e0917f)}
:root[data-ui-g] .w2-bv{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
/* compare */
:root[data-ui-g] .w2-cmp{border:1px solid var(--line);border-radius:var(--r-sm);padding:10px;background:var(--bg-1)}
:root[data-ui-g] .w2-cmp svg{width:100%;height:auto;display:block}
:root[data-ui-g] .w2-cl{stroke-width:1.6;fill:none;vector-effect:non-scaling-stroke}
:root[data-ui-g] .w2-cbase{stroke:var(--line-2);stroke-width:1;stroke-dasharray:3 3}
:root[data-ui-g] .w2-cleg{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px;font-size:12px}
:root[data-ui-g] .w2-cleg span{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2)}
:root[data-ui-g] .w2-cleg i{width:11px;height:3px;border-radius:2px;display:inline-block}
:root[data-ui-g] .w2-form{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:0 0 12px}
:root[data-ui-g] .w2-form input{background:var(--bg-2);border:1px solid var(--line-2);border-radius:var(--r-pill);
  color:var(--ink);font:500 12.5px var(--font);padding:7px 13px;min-width:190px}
:root[data-ui-g] .w2-form button{border:0;border-radius:var(--r-pill);padding:7px 15px;cursor:pointer;
  font:700 12px var(--font);color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .w2-chips{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 12px}
:root[data-ui-g] .w2-chips a{font:600 11.5px var(--font);color:var(--ink-2);text-decoration:none;
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:4px 11px}
:root[data-ui-g] .w2-chips a.on{color:var(--on-accent);border-color:transparent;
  background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
</style>"""

# a stable, colour-blind-safe line palette for the compare overlay (order = selection order)
LINE_COLORS = ("#4d9bf0", "#e0917f", "#7fc8a9", "#c9a227", "#a98bd6", "#7fb3c8")
