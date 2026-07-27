"""src/web/home/pat_dock.py — the alive floating Pat guide (spec §6, increment iv).

Self-contained: emits its own scoped CSS + JS. A living avatar (breathing/blink/look), proactive
bubbles and suggestion answers built from the home's OWN reads (data-bound, never canned hype),
descriptive-only (SEBI-safe). a11y (Codex #4/#5): `role="dialog"` + `aria-modal`, `inert` when
closed, Escape closes, focus moves in on open and back to the trigger on close. DOM-safe: every
answer/bubble is escaped server-side and shown by toggling hidden blocks (no runtime innerHTML of
data). Imports only `reads` + `components` from this package — no preview module.
"""
from __future__ import annotations

import re as _re

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
    """Response-format calibration: each answer is (title, detail). The TITLE is a terse one-liner,
    always shown; DETAIL (may be "") is revealed on demand behind a 'more' expander. Lookup/status
    questions ("what changed", "who's buying") stay terse (title-only or an inline chip row); explain
    questions ("what is X", "how do I read this") lead with ONE sentence + the depth on demand.
    Crisp by default, fuller only when the question needs it — never a wall for a simple ask."""
    out = {}
    all_ch = reads.what_changed(conn, days=7, limit=50)
    if all_ch:
        n = len(all_ch)
        chips = "".join(C.term_chip(C._d(r).get("symbol") or "", (C._d(r).get("lens") or "").upper()) for r in all_ch[:3])
        title = (C.esc(f"{n} name{'s' if n != 1 else ''} changed state this week — most recent:")
                 + '<div class="g-pchips">' + chips + "</div>")
        out["changed"] = (title, "")                          # terse: a count + the newest chips, no expander
    else:
        out["changed"] = ("Nothing notable changed in the last week.", "")
    fd = _fii_dii_line(conn)
    out["flows"] = (((C.esc(fd) + ' <span class="g-pat-tag">cash · provisional</span>') if fd
                     else "FII/DII flows haven't landed for today yet."),
                    "Net cash-segment flow — who is net buying vs selling on the day. Provisional, descriptive only.")
    out["dvpt"] = ("<b>DVPT</b> is the share of a day's volume actually <b>delivered</b> to buyers, not flipped intraday.",
                   "A high, rising delivery share means real conviction is behind a move — accumulation, not churn. "
                   "It is described from the tape, never a recommendation.")
    out["read"] = ("The cards up top are the whole market at a glance — scroll for your watchlist, flows, calendars and news.",
                   "Every number shows its source and links to the evidence; click a Market-pulse tile for its 30-session "
                   "trend, open a drawer to go deeper, or type a stock, sector or signal above. Nothing here is advice.")
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
    answers.update(_trust_answers())      # W5: the Proof-estate answers (see §w5-journey below)

    def _block(k, title, detail):
        more = (('<details class="g-pat-more"><summary>more</summary>'
                 '<div class="g-pat-more-b">' + detail + "</div></details>") if detail else "")
        return ('<div class="g-pat-ans-block" data-key="' + k + '" hidden>'
                '<div class="g-pat-a-title">' + title + "</div>" + more + "</div>")

    ans = "".join(_block(k, t, d) for k, (t, d) in answers.items())
    sug = "".join('<button type="button" class="g-pat-sug" data-key="' + k + '">' + C.esc(lbl) + "</button>"
                  for k, lbl in (_SUGG + _SUGG_TRUST))
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
    return _CSS + markup + _JS + _ASK_JS


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
:root[data-ui-g] .g-pat-a-title{font-size:13.5px;color:var(--ink);line-height:1.5}
:root[data-ui-g] .g-pat-a-title b{color:var(--accent)}
:root[data-ui-g] .g-pat-tag{font:600 9px/1 var(--mono);color:var(--ink-3);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:2px 6px;margin-left:4px;text-transform:uppercase;white-space:nowrap}
:root[data-ui-g] .g-pat-more{margin-top:9px}
:root[data-ui-g] .g-pat-more summary{list-style:none;cursor:pointer;font:600 11.5px var(--font);color:var(--accent)}
:root[data-ui-g] .g-pat-more summary::-webkit-details-marker{display:none}
:root[data-ui-g] .g-pat-more summary::after{content:" ›";display:inline-block;transition:transform .2s}
:root[data-ui-g] .g-pat-more[open] summary::after{transform:rotate(90deg)}
:root[data-ui-g] .g-pat-more-b{font-size:12.5px;color:var(--ink-2);line-height:1.55;margin-top:6px}
</style>"""

_JS = r"""<script>(function(){
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
/* response-format calibration for the typed box: route the question, or deep-link a symbol */
function classify(q){ var t=(q||"").toLowerCase().trim();
  if(/chang|flip|state|today|new high|newly/.test(t)) return "changed";
  if(/buy|bought|sold|sell|fii|dii|flow|institution/.test(t)) return "flows";
  if(/dvpt|deliver/.test(t)) return "dvpt";
  return "read"; }
function symToken(q){ var raw=(q||"").trim(); if(!raw||/\s/.test(raw)) return "";
  var s=raw.toUpperCase().replace(/[^A-Z0-9&]/g,""); return /^[A-Z][A-Z0-9&]{1,14}$/.test(s)?s:""; }
function symAns(tok){ ans.innerHTML="";
  var card=document.createElement("div"); card.className="g-card2";
  var t=document.createElement("div"); t.className="g-pat-a-title"; t.appendChild(document.createTextNode("Open "));
  var a=document.createElement("a"); a.setAttribute("href","/dash/stock?sym="+encodeURIComponent(tok)); a.textContent=tok+" ›"; t.appendChild(a);
  var p=document.createElement("div"); p.className="g-pat-more-b"; p.style.marginTop="6px";
  p.textContent="I'll take you to its evidence page — descriptive only."; card.appendChild(t); card.appendChild(p); ans.appendChild(card); }
function open(o){
  pat.classList.toggle("open",o); fab.setAttribute("aria-expanded",o?"true":"false");
  if(o){ panel.removeAttribute("inert"); pat.classList.remove("bub"); bub.hidden=true; ans.innerHTML=""; type(msg,GREET);
         setTimeout(function(){ if(input) input.focus(); },60); }
  else { panel.setAttribute("inert",""); fab.focus(); }
}
fab.addEventListener("click",function(){ open(!pat.classList.contains("open")); });
document.getElementById("g-pat-close").addEventListener("click",function(){ open(false); });
panel.querySelectorAll(".g-pat-sug").forEach(function(b){ b.addEventListener("click",function(){ showAns(b.getAttribute("data-key")); }); });
document.getElementById("g-pat-form").addEventListener("submit",function(e){ e.preventDefault();
  var q=input?input.value:"", tok=symToken(q);
  if(tok){ symAns(tok); } else { showAns(classify(q)); }
  if(input){ input.value=""; } });
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


# ═══ w5-journey additions — the dock gains the classic /dash/pat resolution ═══════════
# THERE IS NO THIRD PAT. The Graphite dock above is the one assistant in this experience; what it
# lacked versus the classic `/dash/pat` page was RESOLUTION — the ability to answer an arbitrary
# typed question deterministically instead of falling back to a four-way regex. That is what this
# section adds, through Pat's OWN auto-folding knowledge sources (docs/pat-knowledge-contract.md):
#
#   A. JARGON  — `src.pat.glossary.GLOSSARY`, which `_merge_web()` feeds from
#                `docs/metrics-glossary.md` at import. A new metric bullet teaches the dock with
#                ZERO code, exactly as it teaches the classic page.
#   B. PAGES   — `src.pat.nav_flow`, which ranks `lens_registry` live. A newly registered lens
#                becomes answerable the day it ships.
#   C. SYMBOLS — a strict token check, deep-linking the Graphite stock page (`?sym=`).
#
# What is deliberately NOT carried over: `engine.route()`'s LLM fallback. `route()` calls a Gemini
# classifier when every deterministic gate misses; a dock answer must be zero-cost and instant, and
# paid spend is a surface-first action. So this resolver is closed-vocabulary and model-free by
# construction — when nothing resolves it says so rather than guessing.
#
# Also not carried over (classic-page capabilities that need state the dock has no home for — each
# an honest open item, not a silent gap): multi-turn threads (`pat_tid`), saved boards, the
# thumbs-up/down loop that feeds few-shot routing, the avatar picker, and the grouped
# example-question library.

_SUGG_TRUST = [("proof", "How do you prove this?"), ("verdict", "Does any of it work?"),
               ("terms", "Explain a term")]

# Where a classic route already has a Graphite twin, Pat points at the twin. Anything not listed
# keeps its classic route (one-way home -> classic is allowed and gate-tested).
_GRAPHITE_TWIN = {
    "/dash/coverage": "/dash/home/proof", "/dash/testing": "/dash/home/validation",
    "/dash/glossary": "/dash/home/glossary", "/dash/strategy-ref": "/dash/home/strategy-ref",
    "/dash/reading-guide": "/dash/home/guide", "/dash/spec-sheets": "/dash/home/prereg",
    "/dash/rule-lab": "/dash/home/rule-lab", "/dash/replay-any-date": "/dash/home/replay",
    "/dash/evidence-pack": "/dash/home/validation?pack=1",
    "/dash/rrg": "/dash/home/rotation", "/dash/rotation": "/dash/home/rotation",
    "/dash/markets": "/dash/home",
}

_SYM_RE = _re.compile(r"^[A-Z][A-Z0-9&]{1,14}$")
_CANNED_RE = (
    ("changed", _re.compile(r"chang|flip|state|new high|newly", _re.I)),
    ("flows", _re.compile(r"buy|bought|sold|sell|fii|dii|flow|institution", _re.I)),
    ("proof", _re.compile(r"prove|proof|trust|evidence|source|coverage|look.?ahead|honest", _re.I)),
    ("verdict", _re.compile(r"work|validat|backtest|return|perform|fail|alpha|edge", _re.I)),
    ("terms", _re.compile(r"glossar|define|definition|jargon|terminolog", _re.I)),
    ("read", _re.compile(r"how do i|how to|read|start|new here|guide", _re.I)),
)


def _trust_answers() -> dict:
    """The three Proof-estate answers, so the dock speaks for the trust layer too. Static text
    (no DB) — every claim here is a pointer to a page that carries the numbers."""
    return {
        "proof": ("Every number names the table it came from, and the whole record is public — "
                  "including what failed.",
                  "Coverage and freshness live on the Proof page; the falsification record lists "
                  "every strategy with its net result against the index; and you can replay any "
                  "past date to check we are not using information we could not have had."),
        "verdict": ("Mostly no — and we publish that. Most of what we built lost to simply owning "
                    "the index after realistic costs.",
                    "The validation record shows each strategy's net return/vol against the "
                    "Nifty-500 buy-and-hold benchmark, plus the approaches recorded dead in the "
                    "ledger. Descriptive lenses stay descriptive; they never rank a stock for you."),
        "terms": ("Ask me any metric by name — I read the same dictionary the ? popovers use.",
                  "Type a term like delivery, breadth or relative strength and I will define it in "
                  "plain English. The full dictionary is on the Glossary page, grouped by family."),
    }


def resolve(q: str) -> dict:
    """Closed-vocabulary, deterministic, model-free resolution of one typed question.

    Returns {'kind': 'symbol'|'explain'|'navigate'|'canned'|'none', ...}. Never raises, never calls
    a model, never touches the network. Order matters: a bare ticker is a symbol, an explicit
    'where do I see X' is navigation, a term that resolves in the glossary is an explanation, and
    everything else falls to the small canned set (or an honest 'I don't know')."""
    raw = (q or "").strip()
    if not raw:
        return {"kind": "none"}

    # 1. a bare token is ambiguous — a ticker and a metric code look identical (DVPT, CCI, MEP).
    #    An EXACT glossary hit wins, because a code we can define is a question we can answer;
    #    anything else that looks like a ticker goes to the stock page.
    if " " not in raw:
        tok = _re.sub(r"[^A-Za-z0-9&]", "", raw).upper()
        exact = _exact_term(raw)
        if exact:
            return exact
        if _SYM_RE.match(tok):
            return {"kind": "symbol", "sym": tok}

    # 2. an explicit navigational ask -> the registry (source B, auto-folding)
    try:
        from src.pat import nav_flow
        nav = nav_flow.parse_navigate(raw)
        if nav:
            hits = nav_flow.resolve((nav.get("params") or {}).get("topic") or raw, limit=3)
            if hits:
                return {"kind": "navigate", "hits": [_twin(h) for h in hits]}
    except Exception:  # noqa: BLE001 — resolution is best-effort; never break the dock
        pass

    # 3. a metric name -> the glossary (source A, auto-folding from docs/metrics-glossary.md)
    try:
        from src.pat import glossary as PG
        hits = PG.find(raw, limit=1)
        if hits:
            slug, e = hits[0]
            return {"kind": "explain", "slug": slug, "term": e.get("term") or slug,
                    "plain": e.get("plain") or "", "detail": e.get("detail") or ""}
    except Exception:  # noqa: BLE001
        pass

    # 4. the small canned set the dock already served
    for key, rx in _CANNED_RE:
        if rx.search(raw):
            return {"kind": "canned", "key": key}
    return {"kind": "none"}


def _exact_term(raw: str):
    """An EXACT glossary slug/alias/term match, or None. Deliberately exact-only: a fuzzy match on
    a bare token would swallow every ticker."""
    try:
        from src.pat import glossary as PG
        q = raw.strip().lower()
        e = PG.get(q)
        slug = q
        if e is None:
            for s, cand in PG.GLOSSARY.items():
                aliases = {a.lower() for a in (cand.get("aliases") or [])}
                if q == (cand.get("term") or "").lower() or q in aliases:
                    e, slug = cand, s
                    break
        if e is None:
            return None
        return {"kind": "explain", "slug": slug, "term": e.get("term") or slug,
                "plain": e.get("plain") or "", "detail": e.get("detail") or ""}
    except Exception:  # noqa: BLE001
        return None


def _twin(hit: dict) -> dict:
    h = C._d(hit)
    route = h.get("route") or ""
    return {"label": h.get("label") or h.get("key") or "", "route": _GRAPHITE_TWIN.get(route, route),
            "blurb": h.get("blurb") or ""}


def answer_html(conn, q: str) -> str:
    """One question -> one escaped HTML fragment for the dock to inject. Everything is escaped
    server-side (the dock never builds markup from data), so the fragment is safe to insert."""
    r = resolve(q)
    kind = r.get("kind")
    if kind == "symbol":
        s = C.esc(r["sym"])
        return ('<div class="g-pat-a-title">Open <a href="/dash/home/stock?sym=' + s + '">'
                + s + " &rsaquo;</a></div>"
                '<div class="g-pat-more-b" style="margin-top:6px">I will take you to its evidence '
                "page &mdash; descriptive only.</div>")
    if kind == "navigate":
        links = "".join('<div style="margin-top:6px"><a href="' + C.safe_url(h["route"]) + '">'
                        + C.esc(h["label"]) + " &rsaquo;</a></div>" for h in r["hits"][:3])
        return '<div class="g-pat-a-title">Here is where that lives:</div>' + links
    if kind == "explain":
        det = (('<details class="g-pat-more"><summary>more</summary><div class="g-pat-more-b">'
                + C.esc(r["detail"]) + "</div></details>") if r.get("detail") else "")
        return ('<div class="g-pat-a-title"><b>' + C.esc(r["term"]) + "</b> &mdash; "
                + C.esc(r["plain"]) + "</div>" + det
                + '<div class="g-pat-more-b" style="margin-top:6px">'
                '<a href="/dash/home/glossary?q=' + C.esc(r["term"])
                + '">See it in the glossary &rsaquo;</a></div>')
    if kind == "canned":
        answers = {}
        try:
            answers = _answers(conn) if conn is not None else {}
        except Exception:  # noqa: BLE001
            answers = {}
        answers.update(_trust_answers())
        pair = answers.get(r["key"])
        if pair:
            title, detail = pair
            det = (('<details class="g-pat-more"><summary>more</summary><div class="g-pat-more-b">'
                    + C.esc(detail) + "</div></details>") if detail else "")
            return '<div class="g-pat-a-title">' + title + "</div>" + det
    return ('<div class="g-pat-a-title">I do not have a deterministic answer for that &mdash; I only '
            "speak in terms I can back with data.</div>"
            '<div class="g-pat-more-b" style="margin-top:6px">Try a stock symbol, a metric name, '
            'or <a href="/dash/home/guide">how to read this site &rsaquo;</a></div>')


# The typed box now asks the server. A CAPTURE-phase listener on `document` runs BEFORE the form's
# own bubble-phase handler above, so this supersedes the four-way regex without editing it; if the
# request fails the visitor gets an honest message rather than a wrong guess. `innerHTML` is used
# on a fragment the SERVER escaped — the same trust model as `showAns` above.
_ASK_JS = """<script>(function(){
var form=document.getElementById("g-pat-form"),ans=document.getElementById("g-pat-ans"),
    input=document.getElementById("g-pat-in");
if(!form||!ans||!input)return;
function put(h){ans.innerHTML="";var c=document.createElement("div");c.className="g-card2";c.innerHTML=h;ans.appendChild(c);}
document.addEventListener("submit",function(e){
  if(e.target!==form)return;
  e.preventDefault();e.stopPropagation();
  var q=(input.value||"").trim();input.value="";
  if(!q)return;
  put("<div class='g-pat-a-title'>Looking that up...</div>");
  fetch("/dash/home/pat/ask?q="+encodeURIComponent(q),{headers:{"X-Requested-With":"pat-dock"}})
    .then(function(r){return r.ok?r.text():Promise.reject(r.status);})
    .then(put)
    .catch(function(){put("<div class='g-pat-a-title'>I could not reach my notes just now - "+
      "try a stock symbol or a metric name.</div>");});
},true);})();</script>"""


def _selftest() -> int:
    ok = 0
    assert resolve("")["kind"] == "none"
    assert resolve("TCS") == {"kind": "symbol", "sym": "TCS"}
    ok += 1
    assert resolve("what is delivery")["kind"] in ("explain", "canned")
    ok += 1
    assert resolve("who is buying today")["kind"] in ("canned", "explain", "navigate")
    ok += 1
    assert "/dash/home/stock?sym=TCS" in answer_html(None, "TCS")
    ok += 1
    assert "g-pat-a-title" in answer_html(None, "zzzqqq nonsense phrase here")
    ok += 1
    assert "<script>" not in answer_html(None, "<script>alert(1)</script>")
    ok += 1
    for banned in ("gemini", "anthropic", "call_classifier"):
        assert banned not in _ASK_JS.lower(), banned
    ok += 1
    assert set(_trust_answers()) == {"proof", "verdict", "terms"}
    ok += 1
    print("pat_dock selftest OK (%d checks)" % ok)
    return 0
