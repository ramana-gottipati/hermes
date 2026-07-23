"""src/web/home/components.py — the Graphite `.g-*` component kit (spec §4).

DOM-safe (Codex #7): every piece of text is `html.escape`d; numbers are formatted server-side;
the client-side SVG/viz reads only numeric data-* attributes (never interpolated markup). URLs pass
`safe_url` (Codex #9). No import of any preview/`*_v3` module.
"""
from __future__ import annotations

import html as _html


def esc(s) -> str:
    return _html.escape("" if s is None else str(s))


def safe_url(url: str) -> str:
    """Only http(s) survive; javascript:/data:/anything else collapses to '#' (M3 B1 discipline)."""
    u = ("" if url is None else str(url)).strip()
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://") or u.startswith("/"):
        return esc(u)
    return "#"


def _num(v, dp: int = 2) -> str:
    try:
        return f"{float(v):,.{dp}f}"
    except (TypeError, ValueError):
        return "—"


def _signed_pct(v) -> tuple[str, str]:
    """(text, cls) — cls is 'up'/'dn' (a SIGNED value: up/down colour is correct)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ("—", "")
    arrow = "▲" if f >= 0 else "▼"
    return (f"{arrow} {abs(f):.2f}%", "up" if f >= 0 else "dn")


# ── containers ──────────────────────────────────────────────────────────────────
def zone(title: str, prov_text: str, body_html: str, sub: str = "") -> str:
    p = prov_text.split("·", 1)
    prov = _prov_html(p[0].strip(), (p[1].strip() if len(p) > 1 else ""))
    sub_html = f'<span class="g-sub">{esc(sub)}</span>' if sub else ""
    return ('<section class="g-zone"><div class="g-zone-h"><h2>' + esc(title) + "</h2>"
            + sub_html + prov + '</div><div class="g-zone-b">' + body_html + "</div></section>")


def card(title: str, body_html: str) -> str:
    t = f'<div class="g-card-h">{esc(title)}</div>' if title else ""
    return '<div class="g-card">' + t + body_html + "</div>"


def empty(msg: str) -> str:
    return '<p class="g-empty">' + esc(msg) + "</p>"


def fence(text: str) -> str:
    return '<p class="g-fence-top">' + esc(text) + "</p>"


# ── atoms ─────────────────────────────────────────────────────────────────────
def tile(lab: str, big: str, sub: str = "") -> str:
    return ('<div class="g-tile"><span class="g-lab">' + esc(lab) + '</span>'
            '<span class="g-big g-num">' + esc(big) + '</span>'
            + (f'<span class="g-sub">{esc(sub)}</span>' if sub else "") + "</div>")


def _prov_html(table: str, fresh: str, stale: bool = False) -> str:
    cls = "g-prov stale" if stale else "g-prov"
    tail = f" · {esc(fresh)}" if fresh else ""
    return f'<span class="{cls}">{esc(table)}{tail}</span>'


def prov(table: str, fresh: str, stale: bool = False) -> str:
    return _prov_html(table, fresh, stale)


def term_chip(label: str, code: str) -> str:
    """Plain-English-first (naming law): the readable label leads, the code is a mono badge."""
    return ('<span class="g-chip">' + esc(label) + '<b class="g-num">' + esc(code) + "</b></span>")


def count_tile(n, label: str, warn: bool = False) -> str:
    dot = '<span class="g-dot warn"></span>' if warn else '<span class="g-dot"></span>'
    return ('<div class="g-count"><div class="g-n g-num">' + esc(n) + "</div>"
            '<div class="g-k">' + dot + esc(label) + "</div></div>")


# ── zone 1 body: market pulse ───────────────────────────────────────────────────
def pulse_block(idx: list, mood: dict, breadth) -> str:
    if idx:
        cards = ""
        for r in idx[:4]:
            txt, cls = _signed_pct(r.get("ret_1d_pct"))
            cards += ('<div class="g-icard"><div class="g-nm">' + esc(r.get("index_name")) + "</div>"
                      '<div class="g-lv g-num">' + _num(r.get("close_value")) + "</div>"
                      '<div class="g-ch g-num ' + cls + '">' + txt + "</div></div>")
        cards = '<div class="g-icards">' + cards + "</div>"
    else:
        cards = empty("Today's index signals haven't landed yet.")
    # mood is a DESCRIPTIVE state -> verdict-free (neutral), NOT up/down colour
    mood_html = ('<div class="g-mood"><span class="g-dot"></span><b>Market mood: '
                 + esc(mood.get("word", "No data")) + "</b><span class=\"g-sub\">"
                 + esc(mood.get("plain", "")) + "</span></div>")
    # breadth adv/dec IS a signed/directional value -> up/down colour is correct
    if breadth and (breadth.get("adv") is not None):
        adv, dec = int(breadth.get("adv") or 0), int(breadth.get("dec") or 0)
        breadth_html = ('<div class="g-breadth" data-adv="' + str(adv) + '" data-dec="' + str(dec) + '">'
                        '<div class="g-split"><span class="g-split-up"></span></div>'
                        '<div class="g-split-lab"><span class="up">' + str(adv) + ' adv</span>'
                        '<span class="dn">' + str(dec) + ' dec</span></div>'
                        '<div class="g-as">as of ' + esc(breadth.get("d", "")) + "</div></div>")
    else:
        breadth_html = empty("Breadth internals haven't refreshed yet.")
    return '<div class="g-pulse">' + cards + mood_html + breadth_html + "</div>"


# ── the .g-* stylesheet (scoped by data-ui-g on the root, via the token layer) ──
def css() -> str:
    return """<style>/* g-kit */
:root[data-ui-g] .g-zone{background:linear-gradient(165deg,var(--bg-2),var(--bg-1) 62%);
  border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin-bottom:16px;position:relative}
:root[data-ui-g] .g-zone::before{content:"";position:absolute;inset:0 auto auto 0;width:44px;height:2px;
  background:linear-gradient(90deg,var(--accent-hi),transparent)}
:root[data-ui-g] .g-zone-h{display:flex;align-items:center;gap:10px;padding:13px 16px 10px;flex-wrap:wrap}
:root[data-ui-g] .g-zone-h h2{margin:0;font-size:15px;font-weight:700}
:root[data-ui-g] .g-sub{font-size:12px;color:var(--ink-3)}
:root[data-ui-g] .g-zone-b{padding:4px 16px 16px}
:root[data-ui-g] .g-prov{margin-left:auto;font:600 10px/1 var(--mono);color:var(--ink-3);background:var(--bg-0);
  border:1px solid var(--line);border-radius:var(--r-pill);padding:4px 9px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
:root[data-ui-g] .g-prov::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--accent)}
:root[data-ui-g] .g-prov.stale::before{background:var(--warn)}
:root[data-ui-g] .g-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px}
:root[data-ui-g] .g-card-h{font-weight:700;margin-bottom:8px}
:root[data-ui-g] .g-empty{color:var(--ink-3);font-size:13px;margin:8px 0}
:root[data-ui-g] .g-fence-top{font-size:12px;color:var(--ink-2);margin:0 0 18px;padding:9px 13px;
  border:1px solid var(--line-2);border-left:2px solid var(--accent);border-radius:0 8px 8px 0;background:var(--acc-dim)}
:root[data-ui-g] .g-tile{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:13px 14px;display:flex;flex-direction:column;gap:5px}
:root[data-ui-g] .g-lab{font:600 10px/1 var(--font);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-big{font-size:26px;font-weight:700;line-height:1}
:root[data-ui-g] .g-chip{display:inline-flex;align-items:center;gap:6px;background:var(--bg-3);border:1px solid var(--line-2);
  border-radius:var(--r-pill);padding:4px 6px 4px 11px;font-size:12px;color:var(--ink)}
:root[data-ui-g] .g-chip b{font:600 10px/1 var(--mono);color:var(--accent);background:var(--acc-dim);border-radius:var(--r-pill);padding:3px 6px}
:root[data-ui-g] .g-count{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:11px 12px}
:root[data-ui-g] .g-n{font-size:24px;font-weight:700;line-height:1}
:root[data-ui-g] .g-k{font-size:11px;color:var(--ink-3);margin-top:3px}
:root[data-ui-g] .g-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-right:5px;vertical-align:middle}
:root[data-ui-g] .g-dot.warn{background:var(--warn)}
:root[data-ui-g] .g-pulse{display:flex;flex-direction:column;gap:14px}
:root[data-ui-g] .g-icards{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}
:root[data-ui-g] .g-icard{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px}
:root[data-ui-g] .g-nm{font:700 11px var(--font);letter-spacing:.05em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-lv{font-size:22px;font-weight:700;line-height:1.15}
:root[data-ui-g] .g-ch{font-weight:700;font-size:12.5px}
:root[data-ui-g] .g-ch.up,:root[data-ui-g] .up{color:var(--up)}
:root[data-ui-g] .g-ch.dn,:root[data-ui-g] .dn{color:var(--down)}
:root[data-ui-g] .g-mood{display:flex;align-items:baseline;gap:8px;font-size:14px;flex-wrap:wrap}
:root[data-ui-g] .g-mood .g-sub{flex-basis:100%;color:var(--ink-2)}
:root[data-ui-g] .g-split{height:12px;border-radius:999px;overflow:hidden;background:var(--bg-3);display:flex}
:root[data-ui-g] .g-split-up{height:100%;width:0;background:var(--up);transition:width 1s cubic-bezier(.2,.7,.2,1)}
:root[data-ui-g] .g-split-lab{display:flex;justify-content:space-between;margin-top:5px;font:600 11px var(--mono)}
:root[data-ui-g] .g-as{font-size:10.5px;color:var(--ink-3);margin-top:4px}
:root[data-ui-g] .g-btn{background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink);border-radius:8px;
  padding:8px 14px;font:600 13px var(--font);cursor:pointer;margin-top:8px}
:root[data-ui-g] .g-btn:hover{border-color:var(--accent)}
</style>"""


def assets() -> str:
    """The client viz bundle — reads numeric data-* attrs only (DOM-safe), reduced-motion aware."""
    return """<script>(function(){
var RM=matchMedia("(prefers-reduced-motion:reduce)").matches;
document.querySelectorAll(".g-breadth").forEach(function(el){
  var adv=+el.getAttribute("data-adv")||0, dec=+el.getAttribute("data-dec")||0, tot=adv+dec;
  var up=el.querySelector(".g-split-up"); if(!up||!tot) return;
  var pct=Math.round(adv/tot*100)+"%";
  if(RM){ up.style.width=pct; } else { requestAnimationFrame(function(){ up.style.width=pct; }); }
});
})();</script>"""
