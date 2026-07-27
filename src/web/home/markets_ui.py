"""src/web/home/markets_ui.py — the shared `.g-m*` render atoms for the W2-B Markets pages.

Lane-owned. The three Markets pages (Strength · Rotation · Sectors) share a small vocabulary: a view
switcher, a fixed-height internally-scrolling box, a plain table, a 0-100 position strip and a
signed bar. They live here once so the three pages cannot drift apart, and so `components.py` — a
file five other lanes are editing this wave — needs no additions.

Everything here is a pure `(data) -> html str` function that reuses the Graphite kit (`components`)
for escaping, tiers and provenance. CSS is scoped `:root[data-ui-g] .g-m…` exactly like the rest of
the Graphite layer, so it cannot reach a classic or preview page. No sqlite, no Request, no canvas,
no animation (reduced-motion safe by construction).
"""
from __future__ import annotations

from src.web.home import components as C

# Where a symbol goes. The Graphite stock hub is built in parallel by lane W1 at this route; this
# lane LINKS it and imports nothing from it. One constant so a route rename is a one-line change.
STOCK_HREF = "/dash/home/stock?sym="

ROTATION_HREF = "/dash/home/rotation"
STRENGTH_HREF = "/dash/home/strength"
SECTORS_HREF = "/dash/home/sectors"


def sym(symbol) -> str:
    """A clickable symbol (owner rule: symbols are always clickable; the param is `sym`, never
    `symbol`). Escaped; an empty symbol degrades to plain text, never a bare link."""
    s = C.esc(symbol)
    if not s:
        return "—"
    return '<a class="g-syma" href="' + STOCK_HREF + s + '">' + s + "</a>"


def tabs(items, active: str, base: str, param: str = "view") -> str:
    """The view switcher — real links, so every view is URL-addressable and shareable (no JS-only
    state). `items` = [(key, label)]; the FIRST item is the default and gets the bare URL. The active
    one is marked for assistive tech."""
    items = list(items)
    out = ['<nav class="g-mtabs" aria-label="View">']
    for i, (key, label) in enumerate(items):
        cur = key == active
        href = base if i == 0 else (base + "?" + param + "=" + key)
        out.append('<a class="g-mtab' + (" on" if cur else "") + '" href="' + C.esc(href) + '"'
                   + (' aria-current="page"' if cur else "") + ">" + C.esc(label) + "</a>")
    out.append("</nav>")
    return "".join(out)


def chips(items, active: str, href_of) -> str:
    """A secondary filter row (horizon, metric, benchmark) — again real links, so the choice lives in
    the URL and survives a share or a reload. `href_of(key)` builds each URL, so a page that already
    carries a `?view=` can keep it."""
    out = ['<div class="g-mchips" role="group">']
    for key, label in items:
        cur = key == active
        out.append('<a class="g-mchip' + (" on" if cur else "") + '" href="'
                   + C.safe_url(href_of(key)) + '"'
                   + (' aria-current="true"' if cur else "") + ">" + C.esc(label) + "</a>")
    out.append("</div>")
    return "".join(out)


def scroll(body_html: str, height: int = 340) -> str:
    """A FIXED-SIZE box that scrolls INTERNALLY (binding correction #3: never a flat endless page).
    The page keeps its shape however many rows land."""
    return ('<div class="g-mscroll" style="max-height:' + str(int(height)) + 'px" tabindex="0">'
            + body_html + "</div>")


def table(cols, rows_html: str, height: int = 340, note: str = "") -> str:
    """A plain, dense table inside a scroll box. `cols` = [(label, css_class)] — the class carries
    alignment only. Header stays visible while the body scrolls."""
    head = "".join('<th class="' + C.esc(c or "") + '">' + lab + "</th>" for lab, c in cols)
    n = ('<p class="g-mnote">' + C.esc(note) + "</p>") if note else ""
    return (scroll('<table class="g-mtbl"><thead><tr>' + head + "</tr></thead><tbody>"
                   + (rows_html or '<tr><td colspan="' + str(len(cols)) + '" class="g-mempty">'
                                   "Nothing on record for this view yet.</td></tr>")
                   + "</tbody></table>", height) + n)


def num(v, dp: int = 1, suffix: str = "") -> str:
    try:
        return ("%." + str(int(dp)) + "f") % float(v) + suffix
    except (TypeError, ValueError):
        return "—"


def signed(v, dp: int = 1, suffix: str = "%") -> str:
    """A signed number that carries its own direction class (never colour alone — the sign is in the
    text too, so the read survives a colour-blind reader or a greyscale print)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '<span class="g-mnum">—</span>'
    cls = "up" if f > 0 else ("dn" if f < 0 else "")
    return ('<span class="g-mnum ' + cls + '">' + ("+" if f > 0 else "")
            + (("%." + str(int(dp)) + "f") % f) + C.esc(suffix) + "</span>")


def pos_strip(pct, label: str = "") -> str:
    """A 0→100 position strip: where a value sits inside its own range. Used for the RS band (0 = at
    its own RS support, 100 = at its own RS resistance) and for constituent breadth. Renders the
    NUMBER beside the strip — the bar is the shape, the number is the evidence."""
    try:
        p = max(0.0, min(100.0, float(pct)))
    except (TypeError, ValueError):
        return '<span class="g-mnum">—</span>'
    return ('<span class="g-mpos" title="' + C.esc(label or (num(p, 0) + " of 100")) + '">'
            '<span class="g-mpos-t"><span class="g-mpos-d" style="left:' + num(p, 1) + '%"></span></span>'
            '<b class="g-mnum">' + num(p, 0) + "</b></span>")


def bar(pct, tone: str = "") -> str:
    """A left-anchored proportion bar (0-100). Tone is a category, never a verdict."""
    try:
        p = max(0.0, min(100.0, float(pct)))
    except (TypeError, ValueError):
        p = 0.0
    return ('<span class="g-mbar"><span class="g-mbar-f ' + C.esc(tone)
            + '" style="width:' + num(p, 1) + '%"></span></span>')


_PHASE_CLS = {"TAILWIND": "ph-tail", "RECOVERY": "ph-rec", "ROLLING-OVER": "ph-roll",
              "HEADWIND": "ph-head", "NEUTRAL": "ph-neu"}


def phase_pill(phase, label: str = "") -> str:
    """The RS weather phase as a pill. The word comes from the canonical engine; the colour is a
    CATEGORY hue, deliberately not a good/bad signed colour."""
    k = str(phase or "NEUTRAL").upper()
    return ('<span class="g-mph ' + _PHASE_CLS.get(k, "ph-neu") + '">'
            + C.esc(label or k.title()) + "</span>")


_QUAD_CLS = {"Leading": "q-lead", "Improving": "q-impr", "Weakening": "q-weak", "Lagging": "q-lag"}


def quad_pill(q) -> str:
    return ('<span class="g-mq ' + _QUAD_CLS.get(q, "q-lag") + '">' + C.esc(q or "—") + "</span>")


def head(title: str, sub: str = "") -> str:
    return ('<h3 class="g-mh">' + C.esc(title)
            + ('<span>' + C.esc(sub) + "</span>" if sub else "") + "</h3>")


def sample_note(is_demo: bool, what: str) -> str:
    """The real-vs-demo honesty line IN WORDS, beside the zone's `sample` badge (correction #4: the
    preview may look full, but it must never pass illustrative data off as live)."""
    if not is_demo:
        return ""
    return ('<p class="g-msample">Showing <b>illustrative sample</b> ' + C.esc(what)
            + " — the live read is empty on this host. Real numbers replace it as soon as the "
              "nightly job lands.</p>")


def css() -> str:
    """The lane's scoped stylesheet, injected once per page via `shell(extra_head=…)`."""
    return """<style>/* g-markets w2 */
:root[data-ui-g] .g-mtabs{display:flex;gap:2px;flex-wrap:wrap;margin:0 0 14px;border-bottom:1px solid var(--line)}
:root[data-ui-g] .g-mtab{font:600 12px/1 var(--font);color:var(--ink-3);padding:9px 13px;text-decoration:none;
  border-bottom:2px solid transparent;white-space:nowrap}
:root[data-ui-g] .g-mtab:hover{color:var(--ink)}
:root[data-ui-g] .g-mtab.on{color:var(--ink);border-bottom-color:var(--accent)}
:root[data-ui-g] .g-mchips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}
:root[data-ui-g] .g-mchip{font:600 11px/1 var(--font);color:var(--ink-3);background:var(--bg-2);
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:6px 11px;text-decoration:none}
:root[data-ui-g] .g-mchip.on{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi));border-color:transparent}
:root[data-ui-g] .g-mscroll{overflow:auto;border:1px solid var(--line);border-radius:10px;background:var(--bg-1)}
:root[data-ui-g] .g-mtbl{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] .g-mtbl th{position:sticky;top:0;z-index:1;background:var(--bg-2);color:var(--ink-3);
  font:600 10.5px/1.5 var(--font);letter-spacing:.05em;text-transform:uppercase;text-align:left;
  padding:8px 10px;border-bottom:1px solid var(--line-2);white-space:nowrap}
:root[data-ui-g] .g-mtbl td{padding:7px 10px;border-bottom:1px solid var(--line);color:var(--ink-2);vertical-align:middle}
:root[data-ui-g] .g-mtbl tr:last-child td{border-bottom:0}
:root[data-ui-g] .g-mtbl th.r,:root[data-ui-g] .g-mtbl td.r{text-align:right}
:root[data-ui-g] .g-mtbl th.c,:root[data-ui-g] .g-mtbl td.c{text-align:center}
:root[data-ui-g] .g-mempty{color:var(--ink-3);text-align:center;padding:22px 10px!important;font-size:12.5px}
:root[data-ui-g] .g-mnum{font:600 12.5px/1 var(--mono);color:var(--ink)}
:root[data-ui-g] .g-mnum.up{color:var(--up)}
:root[data-ui-g] .g-mnum.dn{color:var(--down)}
:root[data-ui-g] .g-mnote{color:var(--ink-3);font-size:11.5px;line-height:1.6;margin:8px 0 0}
:root[data-ui-g] .g-msample{color:var(--ink-3);font-size:11.5px;line-height:1.6;margin:0 0 10px;
  border-left:2px solid var(--line-2);padding-left:9px}
:root[data-ui-g] .g-msample b{color:var(--ink-2)}
:root[data-ui-g] .g-mh{font:700 13px/1.4 var(--font);color:var(--ink);margin:18px 0 9px;display:flex;
  align-items:baseline;gap:9px;flex-wrap:wrap}
:root[data-ui-g] .g-mh span{font:400 11.5px var(--font);color:var(--ink-3)}
:root[data-ui-g] .g-mpos{display:inline-flex;align-items:center;gap:7px;min-width:104px}
:root[data-ui-g] .g-mpos-t{position:relative;flex:1;height:5px;border-radius:3px;
  background:linear-gradient(90deg,var(--bg-3,var(--bg-2)),var(--line-2))}
:root[data-ui-g] .g-mpos-d{position:absolute;top:-3px;width:3px;height:11px;border-radius:2px;background:var(--accent);transform:translateX(-1px)}
:root[data-ui-g] .g-mbar{display:inline-block;width:76px;height:6px;border-radius:3px;background:var(--line);vertical-align:middle}
:root[data-ui-g] .g-mbar-f{display:block;height:100%;border-radius:3px;background:var(--accent)}
:root[data-ui-g] .g-mbar-f.up{background:var(--up)}
:root[data-ui-g] .g-mbar-f.dn{background:var(--down)}
:root[data-ui-g] .g-mph,:root[data-ui-g] .g-mq{display:inline-block;font:600 10.5px/1 var(--font);
  border-radius:var(--r-pill);padding:4px 9px;white-space:nowrap;border:1px solid var(--line-2);color:var(--ink-2)}
:root[data-ui-g] .g-mph.ph-tail{color:#6fd3a4;border-color:#6fd3a460}
:root[data-ui-g] .g-mph.ph-rec{color:#79c0ff;border-color:#79c0ff60}
:root[data-ui-g] .g-mph.ph-roll{color:#e2b341;border-color:#e2b34160}
:root[data-ui-g] .g-mph.ph-head{color:#e58a8a;border-color:#e58a8a60}
:root[data-ui-g] .g-mq.q-lead{color:#6fd3a4;border-color:#6fd3a460}
:root[data-ui-g] .g-mq.q-impr{color:#79c0ff;border-color:#79c0ff60}
:root[data-ui-g] .g-mq.q-weak{color:#e2b341;border-color:#e2b34160}
:root[data-ui-g] .g-mq.q-lag{color:#e58a8a;border-color:#e58a8a60}
:root[data-ui-g] .g-mgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
:root[data-ui-g] .g-mcell{border:1px solid var(--line);border-radius:11px;background:var(--bg-1);padding:12px 13px}
:root[data-ui-g] .g-mcell h4{font:700 12px/1.3 var(--font);color:var(--ink);margin:0 0 2px;display:flex;
  align-items:center;gap:8px;justify-content:space-between}
:root[data-ui-g] .g-mcell .g-msub{font-size:11px;color:var(--ink-3);display:block;margin:0 0 9px}
:root[data-ui-g] .g-mrow{display:flex;align-items:center;gap:8px;font-size:12px;padding:3px 0;color:var(--ink-2)}
:root[data-ui-g] .g-mrow .g-msp{flex:1}
:root[data-ui-g] .g-mturn{display:flex;gap:6px;flex-wrap:wrap;margin:2px 0 0}
:root[data-ui-g] .g-mturn a{font:600 11px/1 var(--font);text-decoration:none;color:var(--ink-2);
  background:var(--bg-2);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:5px 9px}
:root[data-ui-g] .g-mturn a:hover{color:var(--accent);border-color:var(--accent)}
:root[data-ui-g] .g-mturn em{font-style:normal;color:var(--ink-3);font-size:10px}
:root[data-ui-g] .g-mclock{width:100%;max-width:520px;height:auto;display:block;margin:0 auto}
:root[data-ui-g] .g-mclock .ax{stroke:var(--line-2);stroke-width:1;stroke-dasharray:3 4}
:root[data-ui-g] .g-mclock .rim{fill:none;stroke:var(--line-2);stroke-width:1}
:root[data-ui-g] .g-mclock .lbl{fill:var(--ink-3);font:600 9px var(--font);letter-spacing:.09em}
:root[data-ui-g] .g-mclock .nm{fill:var(--ink-2);font:500 9.5px var(--font)}
:root[data-ui-g] .g-mheat{border-collapse:collapse;font-size:11px}
:root[data-ui-g] .g-mheat th{background:var(--bg-2);color:var(--ink-3);font:600 9.5px var(--font);
  padding:6px 5px;text-align:center;position:sticky;top:0;z-index:1}
:root[data-ui-g] .g-mheat th.rw{text-align:left;left:0;z-index:2;min-width:118px}
:root[data-ui-g] .g-mheat td{padding:5px 6px;text-align:center;color:var(--ink);font:600 10.5px var(--mono);
  border:1px solid var(--bg-1)}
:root[data-ui-g] .g-mheat td.na{color:var(--ink-3);background:var(--bg-2)}
:root[data-ui-g] .g-mheat th.rwc{position:sticky;left:0;background:var(--bg-2);text-align:left;
  color:var(--ink-2);font:600 10.5px var(--font);white-space:nowrap;z-index:1}
</style>"""
