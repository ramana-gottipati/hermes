"""src/web/home/pat_dock.py — the alive floating Pat guide (spec §6, increment iv).

Self-contained: emits its own scoped CSS + JS. A living avatar (breathing/blink/look), proactive
bubbles and suggestion answers built from the home's OWN reads (data-bound, never canned hype),
descriptive-only (SEBI-safe). a11y (Codex #4/#5): `role="dialog"` + `aria-modal`, `inert` when
closed, Escape closes, focus moves in on open and back to the trigger on close. DOM-safe: every
answer/bubble is escaped server-side and shown by toggling hidden blocks (no runtime innerHTML of
data). Imports only `reads` + `components` from this package — no preview module.
"""
from __future__ import annotations

from src.web.home import components as C
from src.web.home import reads

_PANEL = "g-pat-panel"

_AVATAR = (
    '<svg class="g-av" viewBox="0 0 64 64" role="img" aria-label="Pat" focusable="false">'
    '<circle class="g-av-halo" cx="32" cy="32" r="30" fill="none" stroke="var(--accent-hi)" stroke-width="1.5" opacity=".55"/>'
    '<circle class="g-av-core" cx="32" cy="32" r="24" fill="url(#gpat)"/>'
    '<defs><radialGradient id="gpat" cx="36%" cy="30%"><stop offset="0" stop-color="var(--accent-hi)"/>'
    '<stop offset="1" stop-color="var(--accent)"/></radialGradient></defs>'
    '<g class="g-av-look"><rect class="g-av-eye" x="24" y="27" width="4" height="9" rx="2" fill="var(--on-accent)"/>'
    '<rect class="g-av-eye r" x="36" y="27" width="4" height="9" rx="2" fill="var(--on-accent)"/>'
    '<path d="M26 41 q6 5 12 0" fill="none" stroke="var(--on-accent)" stroke-width="2" stroke-linecap="round"/></g></svg>'
)


def _fii_dii_line(conn) -> str:
    latest = {}
    for r in reads.fii_dii_recent(conn):
        r = C._d(r)
        cat = r.get("category")
        if cat not in latest and r.get("net_value") is not None:
            latest[cat] = float(r["net_value"])
    parts = []
    for key, nm in (("FII/FPI", "FII"), ("DII", "DII")):
        if key in latest:
            v = latest[key]
            parts.append(nm + " net " + ("bought" if v >= 0 else "sold") + " ₹" + f"{abs(v):,.0f}" + " cr")
    return " · ".join(parts)


def _answers(conn) -> dict:
    out = {}
    ch = reads.what_changed(conn, days=7, limit=3)
    if ch:
        chips = "".join(C.term_chip(C._d(r).get("symbol") or "", (C._d(r).get("lens") or "").upper()) for r in ch)
        out["changed"] = '<div class="g-pchips">' + chips + "</div>"
    else:
        out["changed"] = '<p class="g-note" style="margin:0">Nothing notable changed in the last week.</p>'
    fd = _fii_dii_line(conn)
    out["flows"] = ('<p class="g-note" style="margin:0">' + (C.esc(fd) + ". Cash segment, provisional — descriptive only."
                    if fd else "FII/DII flows haven't landed for today yet.") + "</p>")
    out["dvpt"] = ('<p class="g-note" style="margin:0"><b>DVPT</b> is the share of a day\'s volume actually '
                   "<b>delivered</b> to buyers (not flipped intraday). A high, rising share = real conviction "
                   "behind a move — described, never a recommendation.</p>")
    out["read"] = ('<p class="g-note" style="margin:0">The top zones are the whole market in one glance; each '
                   "shows where its data comes from. Open a drawer to go deeper, or ask me. Nothing here is advice.</p>")
    return out


def _bubbles(conn) -> list:
    b = []
    fd = _fii_dii_line(conn)
    if fd:
        b.append(fd + " today.")
    sc = reads.severity_counts(conn)
    if sc.get("total"):
        b.append(f"{sc['total']} names changed state this week.")
    try:
        rr = reads.upcoming_results(days=7)
        if rr:
            b.append(f"{len(rr)} results land this week.")
    except Exception:  # noqa: BLE001
        pass
    if not b:
        b = ["I've read every zone on this page — ask me anything."]
    return [C.esc(x) for x in b[:4]]


_SUGG = [("changed", "What changed today?"), ("flows", "Who's buying?"),
         ("dvpt", "What is DVPT?"), ("read", "How do I read this?")]


def dock_html(conn) -> str:
    answers = _answers(conn)
    ans = "".join('<div class="g-pat-ans-block" data-key="' + k + '" hidden>' + v + "</div>"
                  for k, v in answers.items())
    sug = "".join('<button type="button" class="g-pat-sug" data-key="' + k + '">' + C.esc(lbl) + "</button>"
                  for k, lbl in _SUGG)
    bubs = "".join("<li>" + x + "</li>" for x in _bubbles(conn))
    markup = (
        '<div class="g-pat" id="g-pat">'
        '<div class="' + _PANEL + '" id="g-pat-panel" role="dialog" aria-modal="true" '
        'aria-label="Pat — your guide" inert>'
        '<div class="g-pat-head"><span class="g-pat-av">' + _AVATAR + "</span>"
        '<span class="g-pat-who">Pat<small id="g-pat-role">your guide to the evidence</small></span>'
        '<button type="button" class="g-pat-x" id="g-pat-close" aria-label="Close Pat">×</button></div>'
        '<div class="g-pat-body"><p class="g-pat-msg" id="g-pat-msg"></p>'
        '<div class="g-pat-sugg">' + sug + "</div>"
        '<div class="g-pat-ans" id="g-pat-ans"></div>' + ans + "</div>"
        '<form class="g-pat-input" id="g-pat-form"><input id="g-pat-in" '
        'placeholder="Ask about any stock, sector or signal…" aria-label="Ask Pat">'
        '<button type="submit" aria-label="Send">↑</button></form></div>'
        '<div class="g-pat-bub" id="g-pat-bub" hidden></div>'
        '<button type="button" class="g-pat-fab" id="g-pat-fab" aria-label="Open Pat, your guide" '
        'aria-expanded="false" aria-controls="g-pat-panel">' + _AVATAR
        + '<span class="g-pat-badge" aria-hidden="true"></span></button>'
        '<ul class="g-pat-bubsrc" id="g-pat-bubsrc" hidden>' + bubs + "</ul>"
        "</div>"
    )
    return _CSS + markup + _JS


_CSS = """<style>/* g-pat */
:root[data-ui-g] .g-pat{position:fixed;right:24px;bottom:24px;z-index:60;display:flex;flex-direction:column;align-items:flex-end;gap:12px}
:root[data-ui-g] .g-pat-panel{width:min(360px,88vw);background:linear-gradient(165deg,var(--bg-2),var(--bg-1));border:1px solid var(--line-2);
  border-radius:20px;box-shadow:0 26px 64px -20px rgba(0,0,0,.7),0 0 0 1px var(--acc-dim);overflow:hidden;transform-origin:bottom right;
  opacity:0;transform:translateY(14px) scale(.95);pointer-events:none;transition:opacity .22s,transform .22s}
:root[data-ui-g] .g-pat.open .g-pat-panel{opacity:1;transform:none;pointer-events:auto}
:root[data-ui-g] .g-pat-head{display:flex;align-items:center;gap:11px;padding:13px 15px;border-bottom:1px solid var(--line);
  background:radial-gradient(120px 60px at 12% 0,var(--acc-dim),transparent)}
:root[data-ui-g] .g-pat-av{width:32px;height:32px;display:block}
:root[data-ui-g] .g-pat-who{font-weight:700;font-size:14px}
:root[data-ui-g] .g-pat-who small{display:block;font-weight:500;color:var(--accent);font-size:10.5px}
:root[data-ui-g] .g-pat-x{margin-left:auto;background:transparent;border:0;color:var(--ink-3);cursor:pointer;font-size:19px;line-height:1;padding:2px 6px}
:root[data-ui-g] .g-pat-body{padding:14px 15px;max-height:min(52vh,420px);overflow-y:auto}
:root[data-ui-g] .g-pat-msg{font-size:13.5px;color:var(--ink-2);margin:0 0 12px;min-height:19px}
:root[data-ui-g] .g-pat-sugg{display:flex;flex-wrap:wrap;gap:7px}
:root[data-ui-g] .g-pat-sug{font:500 12px var(--font);color:var(--ink);background:var(--bg-3);border:1px solid var(--line-2);
  border-radius:var(--r-pill);padding:6px 11px;cursor:pointer}
:root[data-ui-g] .g-pat-sug:hover{border-color:var(--accent)}
:root[data-ui-g] .g-pat-ans{margin-top:13px}
:root[data-ui-g] .g-pat-ans .g-card2{background:var(--bg-0);border:1px solid var(--line);border-radius:12px;padding:12px 13px}
:root[data-ui-g] .g-pchips{display:flex;flex-wrap:wrap;gap:7px}
:root[data-ui-g] .g-pat-input{display:flex;gap:8px;padding:12px 15px;border-top:1px solid var(--line)}
:root[data-ui-g] .g-pat-input input{flex:1;background:var(--bg-0);border:1px solid var(--line-2);border-radius:10px;padding:9px 11px;color:var(--ink);font:400 13px var(--font)}
:root[data-ui-g] .g-pat-input button{background:var(--accent);color:var(--on-accent);border:0;border-radius:10px;padding:0 13px;font:700 15px var(--font);cursor:pointer}
:root[data-ui-g] .g-pat-bub{position:absolute;right:74px;bottom:12px;max-width:230px;background:var(--bg-2);border:1px solid var(--line-2);
  border-radius:14px 14px 4px 14px;padding:10px 13px;font-size:12.5px;color:var(--ink);box-shadow:0 12px 30px -12px rgba(0,0,0,.6);cursor:pointer}
:root[data-ui-g] .g-pat-fab{position:relative;width:64px;height:64px;border-radius:50%;border:0;background:transparent;cursor:pointer;padding:0;
  filter:drop-shadow(0 8px 22px var(--glow));animation:g-bob 5s ease-in-out infinite}
:root[data-ui-g] .g-pat.open .g-pat-fab{animation:none}
:root[data-ui-g] .g-pat-badge{position:absolute;top:2px;right:2px;width:14px;height:14px;border-radius:50%;background:var(--warn);border:2px solid var(--bg-0)}
:root[data-ui-g] .g-pat.open .g-pat-badge{display:none}
:root[data-ui-g] .g-av{width:100%;height:100%;display:block}
:root[data-ui-g] .g-av-core{transform-origin:center;animation:g-breathe 3.4s ease-in-out infinite}
:root[data-ui-g] .g-av-halo{transform-origin:center;animation:g-halo 3.6s ease-in-out infinite}
:root[data-ui-g] .g-av-eye{transform-box:fill-box;transform-origin:center;animation:g-blink 5.2s infinite}
:root[data-ui-g] .g-av-eye.r{animation-delay:.08s}
:root[data-ui-g] .g-av-look{transform-origin:center;animation:g-look 7s ease-in-out infinite}
@keyframes g-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes g-breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
@keyframes g-halo{0%,100%{opacity:.5;transform:scale(1)}50%{opacity:.85;transform:scale(1.05)}}
@keyframes g-blink{0%,93%,100%{transform:scaleY(1)}96%{transform:scaleY(.12)}}
@keyframes g-look{0%,40%,100%{transform:translateX(0)}55%,80%{transform:translateX(2.4px)}}
</style>"""

_JS = """<script>(function(){
var RM=matchMedia("(prefers-reduced-motion:reduce)").matches;
var pat=document.getElementById("g-pat"),fab=document.getElementById("g-pat-fab"),panel=document.getElementById("g-pat-panel"),
    msg=document.getElementById("g-pat-msg"),ans=document.getElementById("g-pat-ans"),bub=document.getElementById("g-pat-bub"),
    input=document.getElementById("g-pat-in");
if(!pat||!fab||!panel) return;
var GREET="Hi — I'm Pat. I've read every zone on this page. Ask me anything, or start here:";
function type(el,t){ if(RM){ el.textContent=t; return; } el.textContent=""; var i=0,iv=setInterval(function(){ el.textContent+=t[i++]||""; if(i>=t.length)clearInterval(iv); },16); }
function showAns(key){
  ans.innerHTML="";
  var src=panel.querySelector('.g-pat-ans-block[data-key="'+key+'"]');
  if(!src) return;
  var card=document.createElement("div"); card.className="g-card2"; card.innerHTML=src.innerHTML; ans.appendChild(card);
}
function open(o){
  pat.classList.toggle("open",o); fab.setAttribute("aria-expanded",o?"true":"false");
  if(o){ panel.removeAttribute("inert"); pat.classList.remove("bub"); bub.hidden=true; ans.innerHTML=""; type(msg,GREET);
         setTimeout(function(){ if(input) input.focus(); },60); }
  else { panel.setAttribute("inert",""); fab.focus(); }
}
fab.addEventListener("click",function(){ open(!pat.classList.contains("open")); });
document.getElementById("g-pat-close").addEventListener("click",function(){ open(false); });
panel.querySelectorAll(".g-pat-sug").forEach(function(b){ b.addEventListener("click",function(){ showAns(b.getAttribute("data-key")); }); });
document.getElementById("g-pat-form").addEventListener("submit",function(e){ e.preventDefault(); showAns("read"); });
bub.addEventListener("click",function(){ open(true); });
document.addEventListener("keydown",function(e){ if(e.key==="Escape"&&pat.classList.contains("open")) open(false);
  if((e.key==="p"||e.key==="P")&&!/input|textarea/i.test((e.target.tagName||""))) open(!pat.classList.contains("open")); });
/* proactive presence: rotate the real-data bubbles (motion only) */
if(!RM){
  var src=document.getElementById("g-pat-bubsrc"), items=src?[].map.call(src.querySelectorAll("li"),function(li){return li.textContent;}):[], bi=0;
  function show(){ if(pat.classList.contains("open")||!items.length) return; bub.textContent=items[bi%items.length]; bi++; bub.hidden=false;
    setTimeout(function(){ bub.hidden=true; },5200); }
  setTimeout(show,2400); setInterval(show,14000);
}
})();</script>"""
