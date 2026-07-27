"""src/web/home/journey.py — the M6 guided/help layer for the Graphite experience (lane W5).

Built to `docs/redesign-m6-journey-spec.md` v1.1 (REVIEW-CLEAN, ratified in direction), retargeted
from the retired `*_v3` preview onto Graphite. The spec's evidence is one-sided (NN/g n=70: upfront
multi-step tours made apps feel HARDER; skippers rated them easier), so this module is deliberately
**TOURLESS**. It ships exactly four things and nothing more:

  1. THE ONE-SHOT NUDGE      — one dismissible tip, one time, ever (`localStorage pvgnudge=done`).
  2. THE PERSISTENT HELP     — "New here? How to read →" in the SAME top-bar slot on every page.
  3. TEACHING EMPTY STATES   — `teaching_empty(why, href, label)`: all three arguments MANDATORY,
                               so a bare "no data" literally cannot be constructed.
  4. PER-PERSONA EXITS       — the four §E exits, each reachable in ≤1 click (asserted, not assumed).

Structural tour-ban (spec §2, Codex A3): this module emits NO backdrop, NO dimming layer, NO focus
trap, NO body-scroll lock, NO multi-step state beyond the single `pvgnudge` flag, and NO "next"
control. `tests/test_home_journey.py` asserts all of that at the source level.

Isolation: zero DB, zero legacy/preview imports, CSS scoped `:root[data-ui-g] .g-*`. Pure
presentation — every function is `(data) -> html str`. Adopted by a page passing `journey.assets()`
as `shell.shell(..., extra_head=)`; the help control is then injected into the existing top bar by
progressive enhancement, so NO shared shell file has to change to adopt it.
"""
from __future__ import annotations

from src.web.home import components as C

# ── the standing help destination (same label, same slot, site-wide) ─────────────────
HELP_HREF = "/dash/home/guide"
HELP_LABEL = "New here? How to read"

# The five-step arc (§E). STRUCTURE delivers steps 1-2 and 4-5 (Today + the stock hub); M6 adds the
# "learn" trigger and the standing help. Kept as data so the guide page and the tests read the SAME
# list — a step can never drift between the copy and the gate.
STEPS: tuple = (
    ("understand", "Understand the day",
     "One calibrated read of the tape — mood, breadth, delivery, who was buying.", "/dash/home"),
    ("search", "Find a name",
     "Every symbol on the site is a link. Type one into Pat, or click any chip.", "/dash/home"),
    ("learn", "Learn what a number means",
     "Every metric has a plain-English definition and names the table it came from.",
     "/dash/home/glossary"),
    ("view", "Form your own view",
     "Read the evidence — coverage, the validation record, the pre-registered gates.",
     "/dash/home/proof"),
    ("track", "Track it",
     "Put the name on your watchlist and let the change log tell you when it moves.",
     "/dash/tracker/dashboard"),
)

# The four persona exits (§E, incl. Codex A4's tracker exit). Each MUST be reachable in ≤1 click
# from every journey-adopting page — `tests/test_home_journey.py` asserts the hrefs are present.
EXITS: tuple = (
    ("newcomer", "I'm new here", "Start with how to read the site", HELP_HREF),
    ("analyst", "I want the evidence", "Coverage, sources and freshness", "/dash/home/proof"),
    ("skeptic", "Prove it works", "The published falsification record", "/dash/home/validation"),
    ("tracker", "I already own names", "Your watchlist and portfolio", "/dash/tracker/dashboard"),
)


def help_link() -> str:
    """The persistent help affordance, server-rendered. The top bar is owned by `shell.py` (a
    shared file this lane does not edit), so `assets()` MOVES this node into the top bar on load;
    if that never runs, it still renders in the page flow rather than vanishing."""
    return ('<a class="g-help" id="g-help" href="' + C.safe_url(HELP_HREF) + '">'
            + C.esc(HELP_LABEL) + ' <span aria-hidden="true">→</span></a>')


def nudge(text: str = "New here? Every number on this page names its source — start with "
                     "“How to read”.", anchor: str = "#g-help") -> str:
    """THE one-shot nudge. One tip, one time, EVER. Never blocks anything: no overlay, no dimming,
    no "next", no focus trap — a single floating tip with an ×, anchored under `anchor`. It renders
    only if the anchor exists on the page, and is dismissed by the ×, Esc, scrolling past, or
    activating the anchor. `prefers-reduced-motion` is honoured (no entrance animation)."""
    return ('<div class="g-nudge" id="g-nudge" data-anchor="' + C.esc(anchor) + '" role="note" hidden>'
            '<span class="g-nudge-t">' + C.esc(text) + "</span>"
            '<button type="button" class="g-nudge-x" id="g-nudge-x" aria-label="Dismiss this tip">×</button>'
            "</div>")


def teaching_empty(why: str, href: str, label: str) -> str:
    """A TEACHING empty state — the M6 §1.3 contract, enforced by the component itself.

    Every honest-empty section must say WHY it is empty (and therefore what WOULD appear here) and
    offer exactly ONE action. All three arguments are mandatory and non-empty: a bare "no data yet"
    cannot be constructed through this function. Raises ValueError otherwise, so a violation is a
    build failure at the call site rather than a silent dead end for a visitor."""
    why_s = (why or "").strip()
    href_s = (href or "").strip()
    label_s = (label or "").strip()
    if not why_s or not href_s or not label_s:
        raise ValueError(
            "teaching_empty(why, href, label): all three are mandatory — an empty state must "
            "teach what would appear here and offer exactly one action "
            f"(got why={why!r}, href={href!r}, label={label!r})")
    return ('<div class="g-empty2"><p class="g-empty2-w">' + C.esc(why_s) + "</p>"
            '<a class="g-empty2-a" href="' + C.safe_url(href_s) + '">' + C.esc(label_s)
            + ' <span aria-hidden="true">→</span></a></div>')


def steps_block(current: str = "") -> str:
    """The five-step arc rendered as a compact, non-blocking ladder (NOT a tour — it is a static
    list of links the visitor may ignore entirely). `current` highlights one step."""
    out = ['<ol class="g-steps">']
    for i, (key, title, body, href) in enumerate(STEPS, start=1):
        cur = ' aria-current="step"' if key == current else ""
        out.append('<li class="g-step"' + cur + '><span class="g-step-n">' + str(i) + "</span>"
                   '<a class="g-step-t" href="' + C.safe_url(href) + '">' + C.esc(title) + "</a>"
                   '<span class="g-step-b">' + C.esc(body) + "</span></li>")
    out.append("</ol>")
    return "".join(out)


def exits_block(title: str = "Where do you want to go?") -> str:
    """The four per-persona exits, side by side. Every journey page carries this, so all four are
    always ≤1 click away (the §E contract, asserted by the gate)."""
    cards = "".join(
        '<a class="g-exit" href="' + C.safe_url(href) + '" data-exit="' + C.esc(key) + '">'
        '<b>' + C.esc(label) + "</b><span>" + C.esc(sub) + "</span></a>"
        for key, label, sub, href in EXITS)
    return ('<div class="g-exits"><div class="g-exits-h">' + C.esc(title) + "</div>"
            '<div class="g-exits-g">' + cards + "</div></div>")


def replay_card(facts: dict) -> str:
    """The Today-page CARD for Replay-any-date — the single most differentiating trust asset.

    Shipped as a component only: this lane does NOT edit the Today page (`__init__._compose` is a
    shared file). The parent wires it with one line — see the adoption note in the module docstring
    of `trust_pages.py`. `facts` = the cheap subset from `trust_reads.replay_facts` (universe count
    + mechanism on the date, and the knowable clock for one symbol); everything is optional and the
    card degrades to a teaching empty rather than fabricating a number."""
    f = C._d(facts)
    sym = f.get("symbol") or ""
    as_of = f.get("as_of") or ""
    rows = []
    if f.get("universe_n") is not None:
        rows.append(("Names listed that day", f"{int(f['universe_n']):,}", f.get("mechanism") or ""))
    if f.get("knowable_from"):
        rows.append(("Earliest we could have known", str(f["knowable_from"]),
                     ("clock: " + str(f.get("knowable_basis") or "")) if f.get("knowable_basis") else ""))
    if not rows:
        body = teaching_empty(
            "The point-in-time replay answers a live API on demand, so there is nothing cached to "
            "show here. Open it and pick any date — it rebuilds what we could honestly have known "
            "that morning.",
            "/dash/home/replay", "Replay a date yourself")
    else:
        body = "".join(
            '<div class="g-rp-row"><span class="g-rp-k">' + C.esc(k) + "</span>"
            '<b class="g-rp-v g-num">' + C.esc(v) + "</b>"
            + ('<span class="g-rp-s">' + C.esc(s) + "</span>" if s else "") + "</div>"
            for k, v, s in rows)
        body += ('<a class="g-rp-cta" href="/dash/home/replay?sym=' + C.esc(sym)
                 + "&as_of=" + C.esc(as_of) + '">Drive it yourself — pick any date →</a>')
    head = ("What we could have known on " + C.esc(as_of)) if as_of else "Replay any date"
    return ('<div class="g-replay-card"><div class="g-rp-h">' + head + "</div>"
            '<p class="g-rp-sub">Zero look-ahead, proved on demand: the API is asked for a past '
            "date and answers with only what was knowable then.</p>" + body + "</div>")


# ── assets ──────────────────────────────────────────────────────────────────────────
_CSS = """<style>/* g-journey */
:root[data-ui-g] .g-help{font:600 11.5px var(--font);color:var(--accent);background:var(--acc-dim);
  border:1px solid var(--accent);border-radius:var(--r-pill);padding:6px 12px;text-decoration:none;white-space:nowrap}
:root[data-ui-g] .g-help:hover{color:var(--on-accent);background:var(--accent)}
:root[data-ui-g] .g-nudge{position:fixed;top:96px;right:22px;z-index:55;max-width:min(320px,90vw);
  display:flex;gap:10px;align-items:flex-start;background:linear-gradient(165deg,var(--bg-2),var(--bg-1));
  border:1px solid var(--accent);border-radius:14px;padding:11px 12px;
  box-shadow:0 18px 44px -18px rgba(0,0,0,.65)}
:root[data-ui-g] .g-nudge-t{font-size:12.5px;line-height:1.5;color:var(--ink-2)}
:root[data-ui-g] .g-nudge-x{background:transparent;border:0;color:var(--ink-3);cursor:pointer;
  font-size:17px;line-height:1;padding:0 2px;margin-left:auto}
:root[data-ui-g] .g-empty2{border:1px dashed var(--line-2);border-radius:12px;background:var(--bg-2);
  padding:13px 15px;margin:6px 0}
:root[data-ui-g] .g-empty2-w{margin:0 0 9px;font-size:12.5px;line-height:1.6;color:var(--ink-2)}
:root[data-ui-g] .g-empty2-a{font:600 12px var(--font);color:var(--accent);text-decoration:none}
:root[data-ui-g] .g-empty2-a:hover{text-decoration:underline}
:root[data-ui-g] .g-steps{list-style:none;margin:0;padding:0;display:grid;gap:9px}
:root[data-ui-g] .g-step{display:grid;grid-template-columns:26px 1fr;gap:4px 11px;align-items:baseline;
  border-left:2px solid var(--line-2);padding:2px 0 2px 12px}
:root[data-ui-g] .g-step[aria-current="step"]{border-left-color:var(--accent)}
:root[data-ui-g] .g-step-n{grid-row:span 2;font:700 12px var(--mono);color:var(--accent);
  border:1px solid var(--line-2);border-radius:50%;width:24px;height:24px;display:grid;place-items:center}
:root[data-ui-g] .g-step-t{font:700 13px var(--font);color:var(--ink);text-decoration:none}
:root[data-ui-g] .g-step-t:hover{color:var(--accent)}
:root[data-ui-g] .g-step-b{font-size:12px;color:var(--ink-3);line-height:1.5}
:root[data-ui-g] .g-exits{margin:14px 0 0}
:root[data-ui-g] .g-exits-h{font:600 10.5px var(--font);letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 8px}
:root[data-ui-g] .g-exits-g{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:9px}
:root[data-ui-g] .g-exit{display:block;border:1px solid var(--line-2);border-radius:12px;background:var(--bg-2);
  padding:11px 13px;text-decoration:none}
:root[data-ui-g] .g-exit:hover{border-color:var(--accent)}
:root[data-ui-g] .g-exit b{display:block;font-size:13px;color:var(--ink);margin-bottom:3px}
:root[data-ui-g] .g-exit span{font-size:11.5px;color:var(--ink-3);line-height:1.45}
:root[data-ui-g] .g-replay-card{border:1px solid var(--line-2);border-radius:14px;background:var(--bg-2);padding:13px 15px}
:root[data-ui-g] .g-rp-h{font:700 13.5px var(--font);color:var(--ink);margin-bottom:4px}
:root[data-ui-g] .g-rp-sub{margin:0 0 11px;font-size:11.5px;color:var(--ink-3);line-height:1.55}
:root[data-ui-g] .g-rp-row{display:flex;flex-wrap:wrap;gap:4px 9px;align-items:baseline;
  border-top:1px solid var(--line);padding:7px 0}
:root[data-ui-g] .g-rp-k{font-size:12px;color:var(--ink-2)}
:root[data-ui-g] .g-rp-v{font-size:15px;color:var(--ink)}
:root[data-ui-g] .g-rp-s{font:600 9.5px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-rp-cta{display:inline-block;margin-top:10px;font:600 12px var(--font);color:var(--accent);text-decoration:none}
</style>"""

# The persistent-help injector. `shell.py` owns the top bar and is a SHARED file this lane does not
# edit, so the control is MOVED into the bar by progressive enhancement (idempotent, and a no-op if
# the bar is absent — the node then simply stays where it was server-rendered). Any other lane
# adopts the whole layer by passing `journey.assets()` as `extra_head`; nothing else changes.
_HELP_JS = """<script>(function(){
function place(){var a=document.getElementById("g-help"),bar=document.querySelector(".g-top");
if(!a||!bar||a.parentNode===bar)return;
var theme=bar.querySelector('button[onclick="pvgTheme()"]');
if(theme)bar.insertBefore(a,theme);else bar.appendChild(a);}
if(document.readyState!=="loading")place();else document.addEventListener("DOMContentLoaded",place);})();</script>"""

# THE one-shot nudge. Structural tour-ban: no backdrop, no dimming, no focus trap, no scroll lock,
# no "next", and exactly ONE persisted flag (`pvgnudge`) — there is no step counter to advance.
_NUDGE_JS = """<script>(function(){
var RM=matchMedia("(prefers-reduced-motion:reduce)").matches, K="pvgnudge";
function seen(){try{return localStorage.getItem(K)==="done";}catch(e){return true;}}
function done(){try{localStorage.setItem(K,"done");}catch(e){}}
function start(){
var n=document.getElementById("g-nudge");if(!n)return;
var anchor=document.querySelector(n.getAttribute("data-anchor")||"#g-help");
if(!anchor||seen()){if(n.parentNode)n.parentNode.removeChild(n);return;}
function hide(){n.hidden=true;done();}
var x=document.getElementById("g-nudge-x");if(x)x.addEventListener("click",hide);
anchor.addEventListener("click",hide);
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&!n.hidden)hide();});
addEventListener("scroll",function(){if(!n.hidden&&(scrollY||0)>260)hide();},{passive:true});
n.hidden=false;if(!RM)n.style.transition="opacity .2s";}
if(document.readyState!=="loading")start();else document.addEventListener("DOMContentLoaded",start);})();</script>"""


def assets() -> str:
    """Everything the M6 layer needs, for `shell.shell(..., extra_head=journey.assets())`."""
    return _CSS + _HELP_JS + _NUDGE_JS


def _selftest() -> int:
    """python src/web/home/journey.py — the contract, checkable without the suite."""
    ok = 0
    assert "g-help" in help_link() and HELP_HREF in help_link(); ok += 1
    assert "pvgnudge" in assets() and "g-nudge" in nudge(); ok += 1
    for bad in (("", "/x", "l"), ("w", "", "l"), ("w", "/x", ""), ("  ", "/x", "l")):
        try:
            teaching_empty(*bad)
            raise AssertionError("teaching_empty accepted a blank argument: %r" % (bad,))
        except ValueError:
            pass
    ok += 1
    te = teaching_empty("Nothing has landed yet.", "/dash/home", "Go home")
    assert "g-empty2" in te and "Go home" in te; ok += 1
    for banned in ("data-tour", "step 1 of", "Next →", "backdrop", "scroll-lock", "inert"):
        assert banned not in assets(), banned
    ok += 1
    assert len(STEPS) == 5 and len(EXITS) == 4; ok += 1
    eb = exits_block()
    assert all(h in eb for _k, _l, _s, h in EXITS); ok += 1
    assert "g-replay-card" in replay_card({}); ok += 1
    print(f"journey selftest OK ({ok} checks)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_selftest())
