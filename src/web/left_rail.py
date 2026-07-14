"""left_rail.py — turn the horizontal `.uk-sub` lens strip into a collapsible, GROUPED
LEFT RAIL, uniformly across BOTH page families, without editing dashboard.py / ui_kit.py /
shell_skin.py.

Why this module exists
----------------------
The site's contextual sub-nav (the second row under the top tabs) lists EVERY lens of the
active altitude in one flat, horizontally-scrolling strip — 28 items on Markets, 14 on
Strategies (registry: src.web.lens_registry). It reads as overwhelming and nothing can be
hidden. Ramana asked to move that strip into a left panel whose lenses are grouped
logically and expand on click (session 2026-07-12, "go, do what is logical").

The universal seam (why a response post-processor, not another `_shell` wrap)
-----------------------------------------------------------------------------
There are two page families and — crucially — they AGREE on two anchors:
  * legacy `dashboard._shell` pages (reskinned by shell_skin) emit the sub-nav as
    `<div class="uk-sub" role="navigation" aria-label="Section">…</div>` (via
    v2_surfaces.native_subnav) and their content container carries `id="uk-main"`.
  * native `ui_kit.shell` pages (Coverage, Strategist, Screen+, the deep-data lenses)
    emit the SAME `<div class="uk-sub">` (via ui_kit.subnav) and the SAME
    `<main id="uk-main" class="uk-page">` content container.
So ONE transform on the final HTML — swap `.uk-sub` for a fixed grouped rail, offset
`#uk-main` by the rail width — covers the whole site. A `_shell` monkeypatch (the
shell_skin / dq_banner pattern) would reach ONLY the legacy family and leave every native
page on the old strip → a half-migrated, inconsistent header. A guarded HTTP middleware is
the only seam that catches both.

What it does, per HTML response
-------------------------------
  1. find the `.uk-sub` strip; if absent (home / dossier — no sub-nav) → no-op.
  2. recover the altitude (from the strip's own `class="on"` lens href, else the lit top
     tab) and rebuild the lenses as a grouped rail from the registry (`group=` field).
  3. replace the strip with `<aside class="uk-rail">` (position:fixed) + a reopen button;
     offset `#uk-main` with `margin-left:var(--rail-w)`.
  4. inject the rail CSS + JS (topbar-height measure, accordion persistence per altitude,
     whole-rail collapse; default-collapsed on wide/Screener + phones).

Properties (the house rules): DEFENSIVE (every branch try/except → the ORIGINAL html; a
page must never 500 for the rail) · IDEMPOTENT (a `/* uk-rail v1 */` head marker) ·
NO-LOSS (only the sub-nav strip is restructured; every lens + href survives, the body is
untouched) · ADDITIVE + REVERSIBLE (don't call install(), and the middleware vanishes).
Isolation: imports lens data lazily from v2_surfaces at request time, nothing at import.
"""
from __future__ import annotations

import gzip
import logging
import re
import zlib

log = logging.getLogger("hermes.v2")

# a head marker so an already-railed html is never processed twice (idempotency).
_RAIL_MARKER = "/* uk-rail v1 */"

# The contextual sub-nav strip (identical markup from ui_kit.subnav AND
# v2_surfaces.native_subnav): a FLAT `<div class="uk-sub">` of <a>/<span class="grp">
# with NO nested <div>, so `.*?</div>` closes exactly the strip. DOTALL, non-greedy.
_UKSUB_RE = re.compile(r'<div class="uk-sub"[^>]*>.*?</div>', re.S)
# the lit lens inside the strip (native_subnav / ui_kit.subnav both emit class="on").
_ON_A_RE = re.compile(r'<a class="on" href="([^"]+)"')
# the opening <body …> tag (capture its whole attribute string to merge a class safely).
_BODY_RE = re.compile(r'<body\b([^>]*)>', re.S)
_CLASS_RE = re.compile(r'(\bclass\s*=\s*)(["\'])(.*?)\2', re.S)

# rail group DISPLAY order per altitude (registry defines membership; this orders the
# accordion). Groups not listed here fall to the end in first-seen registry order.
_GROUP_ORDER = {
    "markets": ["Big picture", "Strength & momentum", "Rotation", "Sectors",
                "Patterns", "Events & flow"],
    "strategies": ["Conviction & structure", "Fundamentals", "Accumulation",
                   "Ownership & filings", "Launchpad"],
}


def _V():
    """The nav maps, lazily (v2_surfaces owns the registry-generated IA)."""
    from src.web import v2_surfaces as V
    return V


# Plain-English subtitles for the METAPHOR-only nav labels (UX audit S-C item 5 /
# SURFACE-PLAYBOOK §4: "a first-time user cannot decode Weather/Clock/Band/All-weather from
# the nav — pair every metaphor with a plain subtitle"). Keyed by lens key. Only these ~7
# opaque labels get a sub-line; every other lens stays a single clean row. Lives HERE (the
# nav renderer) — a display concern — so it needs NO edit to the forked lens_registry.
_SUBTITLES = {
    "rrg":         "sectors on the strength × momentum grid",
    "rotation":    "which of four phases each stock is in",
    "rsband":      "where a stock sits in its own RS range",
    "cycle-clock": "sectors on the rotation loop vs the market",
    "capture-map": "behaviour on up days vs down days",
    "launchpad":   "stocks showing pre-breakout traits",
    "band-locks":  "names stuck at their daily price limit",
}


def _rl_link(k, h, l, on_cls) -> str:
    """One rail link. A metaphor lens (`k` in _SUBTITLES) renders label + a dim plain
    sub-line; every other lens renders the label alone (byte-identical to before)."""
    sub = _SUBTITLES.get(k)
    if sub:
        return ('<a class="uk-rl uk-rl-2%s" href="%s"><span class="rl-l">%s</span>'
                '<span class="rl-sub">%s</span></a>'
                % (on_cls, _esc(h), _esc(l), _esc(sub)))
    return '<a class="uk-rl%s" href="%s">%s</a>' % (on_cls, _esc(h), _esc(l))


def _esc(s) -> str:
    try:
        from src.web.ui_kit import esc as _e
        return _e(s)
    except Exception:  # noqa: BLE001 — a minimal fallback escaper, never fatal
        return ((str(s) if s is not None else "").replace("&", "&amp;")
                .replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _altitude_for(on_href, html) -> str | None:
    """Which altitude this page belongs to. Primary: the strip's lit lens href → its
    altitude (reliable when a lens is active, i.e. every lens page + altitude landing).
    Fallback: the lit top-bar tab (for a page whose strip has no on-lens)."""
    V = _V()
    if on_href:
        for alt, items in V._IA_SUB.items():
            for _k, h, _l, _g in items:
                if h == on_href:
                    return alt
    try:
        top = html.split('class="uk-sub"', 1)[0]        # search only the topbar slice
        for tag in re.findall(r'<a\b[^>]*>', top):
            if 'aria-current="page"' not in tag:
                continue
            hm = re.search(r'href="([^"]+)"', tag)
            if not hm:
                continue
            href = hm.group(1)
            for k, h, _l in V._IA_ALT:
                if h == href:
                    return k
            if href == "/dash/coverage":
                return "trust"
    except Exception:  # noqa: BLE001
        pass
    return None


def _rail(alt: str, on_href) -> str:
    """The grouped left-rail markup for an altitude. Pinned (ungrouped) lenses sit at the
    top; grouped lenses fold into `_GROUP_ORDER` accordions. The group holding the active
    lens is expanded by default. Rebuilt from the registry so it can never drift."""
    V = _V()
    items = V._IA_SUB.get(alt) or []
    if not items:
        return ""
    label = V._ALT_LABELS.get(alt, (alt or "").title())

    def _on(h):
        return " on" if (on_href and h == on_href) else ""

    pinned: list[tuple[str, str, str]] = []
    gmap: dict[str, list[tuple[str, str, str]]] = {}
    seen: list[str] = []
    for _k, h, l, g in items:
        if not g:
            pinned.append((_k, h, l))
        else:
            if g not in gmap:
                gmap[g] = []
                seen.append(g)
            gmap[g].append((_k, h, l))
    pref = _GROUP_ORDER.get(alt, [])
    ordered = [g for g in pref if g in gmap] + [g for g in seen if g not in pref]

    # the group holding the active lens is expanded by default; if the active lens is
    # pinned (a landing page), open the FIRST group so the rail shows structure, not a
    # wall of collapsed headers. (The client remembers the user's own toggles thereafter.)
    default_open = None
    for g in ordered:
        if any(_on(h) for _kk, h, _l in gmap[g]):
            default_open = g
            break
    if default_open is None and ordered:
        default_open = ordered[0]

    P = ['<aside class="uk-rail" role="navigation" aria-label="Section">']
    P.append('<div class="uk-rail-hd"><span class="ttl">%s</span>'
             '<button class="uk-rail-tg" type="button" aria-label="Collapse menu" '
             'title="Collapse menu">&#171;</button></div>' % _esc(label))
    for k, h, l in pinned:
        P.append(_rl_link(k, h, l, _on(h)))
    for g in ordered:
        its = gmap[g]
        gon = (g == default_open) or any(_on(h) for _kk, h, _l in its)
        P.append('<div class="uk-rg" data-g="%s">' % _esc(g))
        P.append('<button class="uk-rg-h" type="button" aria-expanded="%s">'
                 '<span class="cr">&#9656;</span><span class="lb">%s</span></button>'
                 % ("true" if gon else "false", _esc(g)))
        P.append('<div class="uk-rg-b%s">' % (" show" if gon else ""))
        for k, h, l in its:
            P.append(_rl_link(k, h, l, _on(h)))
        P.append("</div></div>")
    P.append("</aside>")
    # reopen affordance (fixed; shown only when the rail is collapsed — see CSS).
    P.append('<button class="uk-rail-show" type="button" aria-label="Show menu" '
             'title="Show menu">&#9776;</button>')
    return "".join(P)


def _mark_body(html: str, alt: str) -> str:
    """Add `has-rail` + `data-alt` + `data-wide` to <body>, preserving every existing
    attribute and MERGING into an existing class (never a duplicate class= attr)."""
    m = _BODY_RE.search(html)
    if not m:
        return html
    attrs = m.group(1)
    if "has-rail" in attrs:
        return html
    cm = _CLASS_RE.search(attrs)
    if cm:
        classes = cm.group(3).split()
        classes.append("has-rail")
        attrs = (attrs[:cm.start()] + cm.group(1) + cm.group(2)
                 + " ".join(classes) + cm.group(2) + attrs[cm.end():])
    else:
        attrs = attrs.rstrip() + ' class="has-rail"'
    # default-collapse hint: the Screener altitude only — its 50-100-column frozen-pane
    # tables are genuinely width-sensitive, so the rail starts collapsed there. Every other
    # altitude shows the rail expanded (that IS the organize-the-menu win Ramana asked for).
    wide = "1" if alt == "screener" else "0"
    attrs += ' data-alt="%s" data-wide="%s"' % (_esc(alt), wide)
    return html[:m.start()] + "<body" + attrs + ">" + html[m.end():]


def reshape_html(html: str) -> str:
    """Post-process ONE dashboard HTML string: swap the `.uk-sub` strip for the grouped
    left rail + offset the content. Returns the input UNCHANGED when it isn't a dashboard
    page, has no sub-nav, or anything goes wrong. Idempotent."""
    try:
        if not html or _RAIL_MARKER in html:
            return html
        if 'class="uk-sub"' not in html or 'class="uk-top"' not in html:
            return html
        m = _UKSUB_RE.search(html)
        if not m:
            return html
        strip = m.group(0)
        om = _ON_A_RE.search(strip)
        on_href = om.group(1) if om else None
        alt = _altitude_for(on_href, html)
        if not alt:
            return html
        rail = _rail(alt, on_href)
        if not rail:
            return html
        out = html[:m.start()] + rail + html[m.end():]
        out = _mark_body(out, alt)
        add = _RAIL_CSS + _RAIL_JS
        out = out.replace("</head>", add + "</head>", 1) if "</head>" in out else add + out
        return out
    except Exception as e:  # noqa: BLE001 — the rail must never break a page
        log.warning("left_rail reshape skipped: %s", e)
        return html


# ── the rail stylesheet — fixed left panel + content offset, both page families ───────
# All selectors key on `body.has-rail` (added by _mark_body) and the universal `#uk-main`
# content id, so legacy (`#uk-main.wrap`) and native (`#uk-main.uk-page`) both offset. The
# rail is position:fixed → its DOM location (inside `.uk` on native, body-level on legacy)
# is irrelevant to layout. Colours via ui_kit tokens (prepended site-wide) → light/dark.
_RAIL_CSS = """<style>""" + _RAIL_MARKER + """
body.has-rail{--rail-w:214px;--top-h:47px}
body.has-rail.rail-collapsed{--rail-w:0px}
body.has-rail #uk-main{margin-left:var(--rail-w);transition:margin-left .16s ease}
.uk-rail{position:fixed;left:0;top:var(--top-h);width:var(--rail-w);height:calc(100vh - var(--top-h));
  box-sizing:border-box;overflow-y:auto;overflow-x:hidden;z-index:25;background:var(--bg-1);
  border-right:1px solid var(--line);padding:10px 8px 28px;transition:width .16s ease}
.uk-rail *{box-sizing:border-box}
body.rail-collapsed .uk-rail{width:0;padding:0;border-right:0;overflow:hidden}
.uk-rail-hd{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:2px 6px 10px}
.uk-rail-hd .ttl{font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink-3);white-space:nowrap}
.uk-rail-tg{flex:none;background:none;border:1px solid var(--line-2);border-radius:7px;color:var(--ink-3);
  cursor:pointer;padding:2px 7px;font-size:13px;line-height:1}
.uk-rail-tg:hover{border-color:var(--accent);color:var(--ink-2)}
.uk-rail .uk-rl{display:block;padding:6px 10px;border-radius:8px;color:var(--ink-3);font-size:12.5px;
  text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:var(--t)}
.uk-rail .uk-rl:hover{color:var(--ink-2);background:var(--bg-2)}
.uk-rail .uk-rl.on{color:var(--ink);background:var(--bg-3);box-shadow:var(--glass)}
.uk-rail .uk-rl-2{white-space:normal;line-height:1.2;padding-top:5px;padding-bottom:6px}
.uk-rail .uk-rl-2 .rl-l{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.uk-rail .uk-rl-2 .rl-sub{display:block;font-size:9.5px;color:var(--ink-3);margin-top:1px;letter-spacing:.1px}
.uk-rail .uk-rl-2:hover .rl-sub,.uk-rail .uk-rl-2.on .rl-sub{color:var(--ink-2)}
.uk-rg{margin-top:1px}
.uk-rg-h{display:flex;align-items:center;gap:7px;width:100%;background:none;border:0;cursor:pointer;
  color:var(--ink-3);font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;padding:9px 8px 5px;text-align:left}
.uk-rg-h:hover{color:var(--ink-2)}
.uk-rg-h .cr{flex:none;font-size:9px;transition:transform .12s;display:inline-block}
.uk-rg-h[aria-expanded="true"] .cr{transform:rotate(90deg)}
.uk-rg-b{display:none}
.uk-rg-b.show{display:block}
.uk-rail-show{display:none;position:fixed;left:9px;top:calc(var(--top-h) + 9px);z-index:40;
  background:var(--bg-2);border:1px solid var(--line-2);border-radius:8px;color:var(--ink-2);
  cursor:pointer;padding:5px 10px;font-size:15px;line-height:1}
.uk-rail-show:hover{border-color:var(--accent);color:var(--ink)}
body.rail-collapsed .uk-rail-show{display:inline-flex}
@media (max-width:860px){
  body.has-rail #uk-main{margin-left:0}
  .uk-rail{top:var(--top-h);width:min(280px,82vw);z-index:45;box-shadow:0 14px 44px rgba(0,0,0,.5);
    transform:translateX(-102%);transition:transform .18s ease}
  body:not(.rail-collapsed) .uk-rail{transform:translateX(0)}
  body.rail-collapsed .uk-rail{transform:translateX(-102%);width:min(280px,82vw)}
  .uk-rail-show{display:inline-flex}
}
</style>"""

# ── the rail behaviour — measure the topbar, accordion (persist per altitude), collapse ─
_RAIL_JS = """<script>
(function(){
 if(window.__ukRail)return;window.__ukRail=1;
 function init(){
  var b=document.body;if(!b||(''+b.className).indexOf('has-rail')<0)return;
  var top=document.querySelector('.uk-top');
  function st(){if(top)b.style.setProperty('--top-h',top.offsetHeight+'px');}
  st();window.addEventListener('resize',st);
  var alt=b.getAttribute('data-alt')||'';var AK='rail:acc:'+alt,CK='rail:col:'+alt;
  var saved=null;try{saved=JSON.parse(localStorage.getItem(AK)||'null');}catch(e){}
  var groups=[].slice.call(document.querySelectorAll('.uk-rail .uk-rg'));
  function set(h,bd,o){h.setAttribute('aria-expanded',o?'true':'false');if(o){bd.classList.add('show');}else{bd.classList.remove('show');}}
  function save(){var a=[];groups.forEach(function(g){var h=g.querySelector('.uk-rg-h');if(h&&h.getAttribute('aria-expanded')==='true'){a.push(g.getAttribute('data-g'));}});try{localStorage.setItem(AK,JSON.stringify(a));}catch(e){}}
  groups.forEach(function(g){
   var h=g.querySelector('.uk-rg-h'),bd=g.querySelector('.uk-rg-b'),nm=g.getAttribute('data-g');
   if(!h||!bd)return;
   var open=saved?saved.indexOf(nm)>=0:h.getAttribute('aria-expanded')==='true';
   set(h,bd,open);
   h.addEventListener('click',function(){set(h,bd,h.getAttribute('aria-expanded')!=='true');save();});
  });
  var v=null;try{v=localStorage.getItem(CK);}catch(e){}
  var mob=false;try{mob=window.matchMedia('(max-width:860px)').matches;}catch(e){}
  var col=v==='1'?true:v==='0'?false:(b.getAttribute('data-wide')==='1'||mob);
  if(col){b.classList.add('rail-collapsed');}else{b.classList.remove('rail-collapsed');}
  document.addEventListener('click',function(e){
   var t=e.target;var hit=false;
   while(t&&t!==document.body){var c=''+(t.className||'');if(c.indexOf('uk-rail-tg')>=0||c.indexOf('uk-rail-show')>=0){hit=true;break;}t=t.parentNode;}
   if(!hit)return;
   var nc=!b.classList.contains('rail-collapsed');
   if(nc){b.classList.add('rail-collapsed');}else{b.classList.remove('rail-collapsed');}
   try{localStorage.setItem(CK,nc?'1':'0');}catch(e2){}
  });
 }
 if(document.readyState!=='loading'){init();}else{document.addEventListener('DOMContentLoaded',init);}
})();
</script>"""


async def _read_body(resp) -> bytes:
    """Read the full response body (BaseHTTPMiddleware hands us a streaming response;
    reading its iterator consumes it, so the caller MUST rebuild the response)."""
    bi = getattr(resp, "body_iterator", None)
    if bi is None:
        return getattr(resp, "body", b"") or b""
    chunks = []
    async for c in bi:
        chunks.append(c if isinstance(c, bytes) else str(c).encode("utf-8"))
    return b"".join(chunks)


def _decode(raw: bytes, enc: str):
    """(plaintext, ok). `ok=False` (brotli / undecodable) → leave the response untouched."""
    try:
        if "gzip" in enc:
            return gzip.decompress(raw), True
        if "deflate" in enc:
            try:
                return zlib.decompress(raw), True
            except Exception:  # noqa: BLE001 — raw deflate (no zlib header)
                return zlib.decompress(raw, -zlib.MAX_WBITS), True
        if "br" in enc:                    # brotli — not handled here; pass through
            return raw, False
        return raw, True
    except Exception:  # noqa: BLE001
        return raw, False


def _encode(body: bytes, enc: str) -> bytes:
    """Re-apply the ORIGINAL content-encoding so the kept `content-encoding` header stays
    truthful (the client decodes it exactly as before)."""
    if "gzip" in enc:
        return gzip.compress(body)
    if "deflate" in enc:
        return zlib.compress(body)
    return body


def _rebuild(resp, body: bytes):
    from starlette.responses import Response as _R
    headers = dict(resp.headers)
    headers.pop("content-length", None)            # Response recomputes it from `body`
    return _R(content=body, status_code=resp.status_code, headers=headers)


async def _dispatch(request, call_next):
    """Guarded HTTP middleware: reshape only `text/html` responses carrying the `.uk-sub`
    strip; pass everything else (JSON /v1, CSV, SVG) straight through. CRITICAL: this
    middleware sits OUTSIDE the app's GZip middleware, so the body arrives already
    compressed — we must decompress → reshape → recompress, and on ANY miss return the
    ORIGINAL bytes intact (never a re-encoded/half-processed body)."""
    resp = await call_next(request)
    if "text/html" not in (resp.headers.get("content-type", "") or "").lower():
        return resp                                 # not html → body_iterator untouched
    raw = await _read_body(resp)                     # consumes the stream — must rebuild now
    try:
        enc = (resp.headers.get("content-encoding", "") or "").lower()
        data, ok = _decode(raw, enc)
        if not ok:
            return _rebuild(resp, raw)               # can't decode → original bytes verbatim
        new = reshape_html(data.decode("utf-8", "ignore"))
        return _rebuild(resp, _encode(new.encode("utf-8"), enc))
    except Exception as e:  # noqa: BLE001 — a failure must never break a page
        log.warning("left_rail dispatch skipped: %s", e)
        return _rebuild(resp, raw)                    # the untouched original body


def install(app) -> bool:
    """Register the rail middleware ONCE on the FastAPI app. Idempotent (an app.state flag),
    defensive (never raises). Called last in v2_surfaces.wire() so it post-processes the
    fully-assembled + reskinned page."""
    try:
        if getattr(app.state, "_left_rail", False):
            return True
    except Exception:  # noqa: BLE001 — a stateless app object: fall through and add once
        pass
    try:
        from starlette.middleware.base import BaseHTTPMiddleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=_dispatch)
        try:
            app.state._left_rail = True
        except Exception:  # noqa: BLE001
            pass
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("left_rail install skipped: %s", e)
        return False


def _selftest() -> int:
    """Reshape a representative page from EACH family + assert the rail took, is grouped,
    no-loss, idempotent, and no-ops off-target."""
    from src.web import ui_kit as K
    from src.web import v2_surfaces as V  # noqa: F401 — ensures the IA maps are importable

    # A native ui_kit page (Markets altitude) built exactly like a real one.
    sub = K.subnav([("Rotation · Map", "/dash/rrg", True), ("Sectors", "/dash/sectors", False)])
    native = K.shell("Markets · patearn", "<div class='uk-card'>BODY-DATA</div>",
                     active="markets", sub=sub,
                     nav_html=K.nav_links(V.site_nav("markets")))
    out = reshape_html(native)
    assert _RAIL_MARKER in out, "rail css marker not injected"
    assert 'class="uk-rail"' in out and 'class="uk-rg"' in out, "grouped rail not built"
    assert ">Big picture<" in out or ">Rotation<" in out, "no group headings in rail"
    # S-C item 5: metaphor lenses (Weather/Clock/Band/Map/All-weather/Launchpad) carry a plain
    # sub-line; a non-metaphor lens (Sectors) does not gain one.
    assert 'class="rl-sub"' in out and "which of four phases" in out, \
        "metaphor-lens subtitle not rendered in the rail (S-C item 5)"
    assert "has-rail" in out and 'data-alt="markets"' in out, "body not marked"
    assert "BODY-DATA" in out, "body content lost (NOT no-loss)"
    assert 'class="uk-sub"' not in out, "old horizontal strip still present"
    assert reshape_html(out) == out, "reshape not idempotent on its own output"

    # A legacy dashboard._shell page (as reskinned): the uk-sub + #uk-main.wrap anchors.
    legacy = ('<!doctype html><html><head></head><body class="uk-skin">'
              '<div class="uk-top"><a class="on" href="/dash/markets" aria-current="page">Markets</a></div>'
              '<div class="uk-sub" role="navigation" aria-label="Section">'
              '<a class="on" href="/dash/rrg">Rotation · Map</a></div>'
              '<div id="uk-main" class="wrap wide">LEGACY-BODY</div></body></html>')
    lout = reshape_html(legacy)
    assert 'class="uk-rail"' in lout and "LEGACY-BODY" in lout, "legacy page not railed / body lost"
    assert 'data-wide="0"' in lout, "a wide Markets page must NOT default-collapse (only Screener does)"
    assert lout.count('class="uk-skin') == 1 and "has-rail" in lout, "body class merge wrong"

    # the Screener altitude is the one that default-collapses (width-sensitive tables).
    scr = K.shell("Screen+ · patearn", "<div class='uk-card'>S</div>", active="screen2",
                  sub=K.subnav([("Screen+", "/dash/screen2", True), ("Themes / Baskets", "/dash/themes", False)]),
                  nav_html=K.nav_links(V.site_nav("screen2")))
    sout = reshape_html(scr)
    assert 'data-wide="1"' in sout and 'data-alt="screener"' in sout, "Screener must hint default-collapse"

    # off-target html (no sub-nav) is returned untouched.
    assert reshape_html("<div>x</div>") == "<div>x</div>", "non-page html mutated"
    home = '<html><head></head><body><div class="uk-top">t</div><div id="uk-main">h</div></body></html>'
    assert reshape_html(home) == home, "a page with no sub-nav must be untouched"

    print("left_rail selftest OK — grouped rail on BOTH families (native + legacy), "
          "no-loss, idempotent, off-target no-op")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
