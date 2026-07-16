"""home_tiers.py — P2 of the UI revamp (S177): re-TIER the home page so the daily-open
answer comes first, WITHOUT editing the frozen cockpit.py.

The problem (UX spec v2 §05-B, Ramana-ratified 2026-07-17): cockpit.render_home emits
    hero · search · mood · start-here · COUNTER TILES · flagship band · ALL boards · fresh
so the jargon counter strip owns the prime slot while the "what changed today" boards
(Attention queue, RS Band moves, the news wire) sit at the very BOTTOM of the board stack.

The fix, at the proven wrap seam (the shell_skin pattern — cockpit.py is a forked/hot
file, so its source is never edited): wrap cockpit.render_home at install() time and
re-order its OUTPUT string into
    hero · search · mood · start-here
    · TODAY band        (Attention · RS Band · Latest headlines — promoted)
    · THE FUNNEL band   (Conviction · Triggers · Rotation · Leaders · Stealth · MEP …)
    · flagship band     (unchanged)
    · counter tiles     (demoted to the tail — still one click to every lens)
    · fresh footer

Properties (house rules): DEFENSIVE (any anchor miss → the ORIGINAL html, never a 500)
· IDEMPOTENT (marker comment) · NO-LOSS (pure re-order — every byte of every section is
kept; boards keep their internal order within their band) · ADDITIVE + REVERSIBLE
(don't call install(), or drop the wire line). Content, queries and the precomputed-only
read guarantee are untouched — this module never touches the DB.
"""
from __future__ import annotations

import logging

log = logging.getLogger("hermes.v2")

_SENTINEL = "_home_tiers_installed"          # set on cockpit once wrapped
_MARKER = "<!-- home-tiers v1 -->"           # idempotence marker in the output

# ── anchors in cockpit.render_home's output (verified against cockpit.py @ S177) ──
_COUNT_START = '<div class="ghdr" style="margin-top:8px">Live lens counters'
_FLAG_START = '<div class="ghdr" style="margin-top:12px">Why this is different'
_CKPT_START = '<div class="ckpt">'
_FRESH_START = '<div class="sub" style="margin-top:6px">Stock signals'
_BOARD_OPEN = '<div class="card ck-board"'
# boards that belong to the "Today" band, matched by their ck-h heading fragments
_TODAY_MARKS = ("</span> Attention", "</span> RS Band", "\U0001F4F0 Latest headlines")


def _band(title: str, hint: str, boards_html: str) -> str:
    """A tier heading + its own board grid — reuses the existing .ghdr/.sub/.ckpt
    classes so the bands inherit the page's (and the skin's) styling untouched."""
    return ('<div class="ghdr" style="margin-top:12px">' + title +
            ' <span class="sub" style="margin:0;font-weight:400">' + hint + '</span></div>'
            '<div class="ckpt">' + boards_html + '</div>')


def retier(html: str) -> str:
    """Re-order one render_home output string into the tiered layout. Any structural
    surprise (missing anchor, out-of-order anchors, no Today board present) returns
    the input unchanged — the wrap must never cost a working home page."""
    try:
        if not html or _MARKER in html:
            return html
        i_cnt = html.find(_COUNT_START)
        i_flag = html.find(_FLAG_START)
        i_ck = html.find(_CKPT_START, max(i_flag, 0))
        i_fresh = html.find(_FRESH_START)
        if min(i_cnt, i_flag, i_ck, i_fresh) < 0 or not (i_cnt < i_flag < i_ck < i_fresh):
            return html
        head = html[:i_cnt]                       # css + hero + search + mood + start-here
        counters = html[i_cnt:i_flag]             # the tile strip (demoted below)
        flag = html[i_flag:i_ck]                  # the flagship band (unchanged)
        ck_block = html[i_ck:i_fresh]             # <div class="ckpt"> boards… </div>
        tail = html[i_fresh:]                     # the fresh footer

        inner = ck_block[len(_CKPT_START):]
        j = inner.rfind("</div>")                 # the ckpt wrapper's own closer
        if j < 0:
            return html
        between = inner[j + 6:]                   # anything after the ckpt closer (expect '')
        inner = inner[:j]

        parts = inner.split(_BOARD_OPEN)
        lead = parts[0]                           # pre-board content inside ckpt (expect '')
        boards = [_BOARD_OPEN + p for p in parts[1:]]
        if not boards:
            return html
        today = [b for b in boards if any(m in b for m in _TODAY_MARKS)]
        if not today:
            return html                           # nothing to promote (thin data) → original
        in_today = set(map(id, today))
        funnel = [b for b in boards if id(b) not in in_today]

        out = [head,
               _band("Today", "what changed since the last close — the queue, the tape, the wire",
                     "".join(today))]
        if funnel or lead.strip():
            out.append(_band("The funnel", "where the independent lenses agree",
                             lead + "".join(funnel)))
        elif lead.strip():
            out.append(lead)
        out += [flag, counters, between, _MARKER, tail]
        return "".join(out)
    except Exception as e:  # noqa: BLE001 — a re-tier failure must never break home
        log.warning("home_tiers retier skipped: %s", e)
        return html


def install() -> bool:
    """Wrap cockpit.render_home so the home page renders tiered. Idempotent (sentinel),
    defensive (never raises), reversible (skip the call). Sweeps sys.modules for any
    module that captured render_home by reference (the shell_skin rebind pattern)."""
    try:
        import src.web.cockpit as C
    except Exception as e:  # noqa: BLE001
        log.warning("home_tiers install skipped: cockpit import failed: %s", e)
        return False
    if getattr(C, _SENTINEL, False):
        return True
    orig = getattr(C, "render_home", None)
    if not callable(orig):
        log.warning("home_tiers install skipped: cockpit.render_home not found")
        return False

    def _tiered_render_home(*args, **kwargs):
        return retier(orig(*args, **kwargs))

    _tiered_render_home.__wrapped__ = orig  # type: ignore[attr-defined]
    C.render_home = _tiered_render_home

    import sys
    rebound = 0
    for _name, _mod in list(sys.modules.items()):
        if _mod is None or _mod is C:
            continue
        try:
            if getattr(_mod, "render_home", None) is orig:
                _mod.render_home = _tiered_render_home
                rebound += 1
        except Exception:  # noqa: BLE001
            continue
    setattr(C, _SENTINEL, True)
    log.info("home_tiers installed — home re-tiered (Today first; +%d imported refs)", rebound)
    return True


def _selftest() -> int:
    # a synthetic render_home-shaped page with every anchor + 5 boards (2 Today, 3 funnel)
    b = lambda h: _BOARD_OPEN + ' style="x"><div class="ck-h">' + h + '</div>data</div>'  # noqa: E731
    synth = ("<style>css</style>HERO SEARCH MOOD START "
             + _COUNT_START + ' …</div><div class="ck-tiles">CNTDATA</div>'
             + _FLAG_START + ' …</div><div class="ck-tiles fl-tiles">FLAGDATA</div>'
             + _CKPT_START
             + b('<span class="em">⭐</span> Conviction shortlist')
             + b('<span class="em">🔔</span> Attention')
             + b('<span class="em">⚡</span> Top triggers')
             + b('<span class="em">📊</span> RS Band')
             + b('\U0001F4F0 Latest headlines')
             + "</div>"
             + _FRESH_START + " footer</div>")
    out = retier(synth)
    assert out != synth and _MARKER in out, "retier did not apply"
    # order: Today band (with Attention/RS Band/News) BEFORE the funnel (Conviction/Triggers),
    # flagship AFTER the funnel, counters demoted after the flagship, fresh last.
    i_today = out.find(">Today ")
    i_att = out.find("</span> Attention")
    i_conv = out.find("Conviction shortlist")
    i_flag = out.find("Why this is different")
    i_cnt = out.find("Live lens counters")
    i_fresh = out.find("Stock signals")
    assert 0 < i_today < i_att < i_conv < i_flag < i_cnt < i_fresh, \
        (i_today, i_att, i_conv, i_flag, i_cnt, i_fresh)
    # NO-LOSS: every board + section survives exactly once
    for frag in ("Conviction shortlist", "</span> Attention", "</span> RS Band",
                 "\U0001F4F0 Latest headlines", "Top triggers", "CNTDATA", "FLAGDATA", "footer"):
        assert out.count(frag) == 1, f"section lost/duplicated: {frag}"
    # idempotent + defensive
    assert retier(out) == out, "not idempotent"
    assert retier("<div>plain</div>") == "<div>plain</div>", "non-home html mutated"
    assert retier("") == ""
    # a page with anchors but NO Today board (thin data) stays untouched
    thin = synth.replace(b('<span class="em">🔔</span> Attention'), "") \
                .replace(b('<span class="em">📊</span> RS Band'), "") \
                .replace(b('\U0001F4F0 Latest headlines'), "")
    assert retier(thin) == thin, "thin page must no-op"
    # install() wraps + is idempotent + reaches name-bound refs
    import sys
    import types

    import src.web.cockpit as C
    _fake = types.ModuleType("src.web._fake_home_ref")
    _fake.render_home = C.render_home
    sys.modules[_fake.__name__] = _fake
    orig = C.render_home
    assert install() is True and install() is True
    assert C.render_home is not orig and _fake.render_home is C.render_home
    del sys.modules[_fake.__name__]
    print("home_tiers selftest OK — Today first, funnel second, counters demoted; "
          "no-loss, idempotent, defensive")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
