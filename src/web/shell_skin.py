"""shell_skin.py — runtime reskin of the legacy dashboard._shell pages into the v2
(ui_kit) visual language, WITHOUT editing dashboard.py / cockpit.py.

The problem (docs/ui-restore-and-migration-TRACKER.md Track A): only the Trust /
Coverage surface is built on the v2 design system (`ui_kit`). Markets, Screener,
Strategies, Tracker, stock and every strategy page still render through
`dashboard._shell` — the old chrome (`pat·e·arn` green-"e" logo, a "search ticker…"
box) and the old `#0e1116 / #161b22 / #30363d` card+table palette. Same site, two
looks, two logos.

The fix, decoupled (the proven v2_surfaces monkeypatch pattern): every legacy page —
and all of cockpit — renders by calling `dashboard._shell(title, body, active, …)`.
We wrap that single function at runtime so its output is post-processed into the
ui_kit language:

  * a CSS OVERLAY (`skin_css`) scoped under ``body.uk-skin`` is injected after the
    legacy ``_BASE_CSS``. Every rule is scoped by a class, so it outranks the bare
    element / single-class base rules on specificity — the reskin wins regardless of
    source order, and NOTHING in the body markup changes (no-loss, additive).
  * the logo is recoloured to the cyan-dot ``patearn`` mark (no green "e") — CSS only,
    no fragile HTML matching.
  * the "search ticker…" form is swapped for the ui_kit "Search or ask Pat ⌘K" hint,
    which opens the global Cmd-K overlay the v2 nav already injects on every page
    (so the ticker-jump function is preserved, not lost).

Properties (the house rules): DEFENSIVE (every step try/except, a failure returns the
original html — a page must never 500 because of the skin) · IDEMPOTENT (sentinel +
a marker check) · NO-LOSS (CSS retint only; the sacred routes, every body, every
datum untouched) · ADDITIVE + REVERSIBLE (don't call install(), or restore the file).

Isolation: imports ONLY ``ui_kit`` (the dependency-free design system) for the cmdk
hint; it reaches ``dashboard`` lazily at install() time to monkeypatch, never at
import. Wired durably from ``v2_surfaces.wire(app)`` (one line) so a redeploy that
re-applies the v2 hook re-applies the skin too.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger("hermes.v2")

# set on the dashboard module once _shell has been wrapped (no double-wrap).
_SKIN_SENTINEL = "_v2_shell_skinned"
# a marker placed in the <head> so an already-skinned html string is never reskinned.
_SKIN_MARKER = "/* uk-skin v1 */"


# ── the reskin stylesheet — legacy classes retinted to the ui_kit tokens ──────
# Scoped under `body.uk-skin` so each rule's specificity (0,1,x)+ beats the base
# `_BASE_CSS` element/single-class rules; the v2 chrome (.v2bar/.v2subnav) is retinted
# by v2_surfaces itself. We retint COLOUR + surface only — never layout/sticky/z-index
# (so the carefully-tuned frozen-pane grid keeps its geometry).
_SKIN_CSS = """<style>""" + _SKIN_MARKER + """
/* ── palette anchor: the instrument background + ink ── */
body.uk-skin{
  background:
    radial-gradient(1100px 560px at 82% -12%, rgba(77,157,255,.07), transparent 60%),
    radial-gradient(860px 480px at -8% 8%, rgba(52,224,214,.05), transparent 55%),
    #0b0f17 !important;
  color:#eaf1f9;
  -webkit-font-smoothing:antialiased;
  font-feature-settings:'tnum' 1,'cv01' 1;
}
/* ── header / chrome ── */
body.uk-skin header{
  background:linear-gradient(180deg,rgba(17,24,36,.92),rgba(11,15,23,.66));
  border-bottom:1px solid #1c2937;backdrop-filter:blur(12px);
}
body.uk-skin header .brand .logo,
body.uk-skin header .brand .logo span{color:#eaf1f9 !important;font-weight:600;letter-spacing:.4px;font-size:16px}
body.uk-skin header .dot{background:#34e0d6 !important;box-shadow:0 0 11px #34e0d6;width:9px;height:9px}
body.uk-skin .hback{border:1px solid #27384a;color:#9bb0c6;border-radius:8px}
body.uk-skin .hback:hover{border-color:#4d9dff;background:#111824}
body.uk-skin .hrow3{border-top:1px solid #111824}
/* the swapped-in Ask-Pat hint (standalone copy of ui_kit .uk-cmdk, since the body
   here is NOT inside a .uk wrapper) */
body.uk-skin .uk-cmdk{margin-left:auto;display:inline-flex;align-items:center;gap:9px;
  padding:6px 11px;border:1px solid #27384a;border-radius:9px;color:#5c6f84;font-size:12px;
  cursor:pointer;transition:170ms cubic-bezier(.2,.7,.2,1);background:#0b0f17;white-space:nowrap}
body.uk-skin .uk-cmdk:hover{border-color:#4d9dff;color:#9bb0c6}
body.uk-skin .uk-cmdk kbd{font-family:'SF Mono',ui-monospace,Menlo,Consolas,monospace;
  background:#18222f;border:1px solid #27384a;border-radius:5px;padding:1px 6px;font-size:11px;color:#9bb0c6}
/* ── cards & boxes ── */
body.uk-skin .card,
body.uk-skin .kpi .box,
body.uk-skin .cprpanel,
body.uk-skin .scard,
body.uk-skin .maj,
body.uk-skin .chip{
  background:#111824;border:1px solid #1c2937;border-radius:12px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.045);
}
body.uk-skin .maj{border-left:3px solid #4d9dff}
body.uk-skin .scard{border-top:3px solid #1c2937}
body.uk-skin .scard.sc-POS{border-top-color:#4d9dff} body.uk-skin .scard.sc-RS{border-top-color:#3fd486}
body.uk-skin .scard.sc-QUAL{border-top-color:#f6b73c} body.uk-skin .scard.sc-CPR{border-top-color:#b18cff}
body.uk-skin .kpi .num,body.uk-skin .scard .ct,body.uk-skin .maj .nm{color:#eaf1f9}
body.uk-skin .kpi .lbl,body.uk-skin .scard .th,body.uk-skin .maj .rr,body.uk-skin .sub,body.uk-skin .ghdr{color:#9bb0c6}
body.uk-skin h2,body.uk-skin .scard .nm{color:#eaf1f9}
/* ── tables (colour only; layout untouched) ── */
body.uk-skin th{color:#5c6f84;border-bottom:1px solid #27384a}
body.uk-skin td{border-bottom:1px solid #1c2937}
body.uk-skin .sym{color:#eaf1f9}
/* ── semantic ink ── */
body.uk-skin .pos{color:#3fd486} body.uk-skin .neg{color:#ff6a7a} body.uk-skin .mut{color:#5c6f84}
body.uk-skin .grp{color:#4d9dff}
/* ── inputs / search / filter chips ── */
body.uk-skin .search input,body.uk-skin .hsearch input,body.uk-skin .dtf{
  background:#0b0f17;border:1px solid #27384a;color:#eaf1f9;border-radius:8px}
body.uk-skin .search button{background:#4d9dff;color:#06121f}
body.uk-skin .fbtn{background:#111824;border:1px solid #1c2937;color:#9bb0c6;border-radius:14px}
body.uk-skin .fbtn.on{background:#4d9dff;border-color:#4d9dff;color:#06121f}
/* ── theme chips ── */
body.uk-skin .tchip{background:#102234;color:#7fc0ff;border:1px solid #1d3a55}
body.uk-skin .tchip:hover{background:#1d3a55;color:#cfe8ff}
/* ── banners ── */
body.uk-skin .b-on{background:rgba(63,212,134,.13);color:#3fd486;border:1px solid #1f6f3a}
body.uk-skin .b-off{background:rgba(255,106,122,.13);color:#ff6a7a;border:1px solid #8f1f1f}
body.uk-skin .b-neu{background:rgba(246,183,60,.13);color:#f6b73c;border:1px solid #5a4a1f}
/* ── strategy thesis badge ── */
body.uk-skin .sbadge{border:1px solid #1c2937}
body.uk-skin .sbadge .th{color:#9bb0c6}
/* ── tab bars ── */
body.uk-skin .tabbar{border-bottom:1px solid #1c2937}
body.uk-skin .tabbar a{color:#9bb0c6}
body.uk-skin .tabbar a.on{color:#eaf1f9;border-bottom-color:#b18cff}
/* ── the frozen-pane data grid — COLOUR ONLY (sticky/z-index left exactly as-is) ── */
body.uk-skin .scrwrap{background:#0b0f17;border:1px solid #1c2937;border-radius:12px}
body.uk-skin table.scr th,body.uk-skin table.scr td{border-bottom:1px solid #161f2b}
body.uk-skin table.scr thead tr.sgrp th{background:#18222f;color:#5c6f84;border-bottom:1px solid #27384a;border-left:1px solid #1c2937}
body.uk-skin table.scr thead tr.scol th{background:#111824;color:#9bb0c6;border-bottom:1px solid #27384a}
body.uk-skin table.scr .fz{background:#0b0f17;border-right:1px solid #1c2937}
body.uk-skin table.scr thead tr.scol th.fz,body.uk-skin table.scr thead tr.sgrp th.fz{background:#18222f}
body.uk-skin table.scr tbody tr:nth-child(even) td.fz{background:#0e1620}
body.uk-skin table.scr tbody tr:hover td{background:#18222f !important}
/* density — the frozen data grid's vertical row padding follows --grid-pad (6px comfortable
   == current, 3px compact). Only the big data grid is density-driven; small tables stay put. */
body.uk-skin table.scr td,body.uk-skin table.scr th{padding-top:var(--grid-pad);padding-bottom:var(--grid-pad)}
/* ── responsive: legacy page body on a phone ── */
@media (max-width:640px){
  body.uk-skin .wrap{padding-left:var(--gutter);padding-right:var(--gutter)}
  body.uk-skin .fbtn,body.uk-skin .fbar a,body.uk-skin .chip{padding:8px 12px}
  body.uk-skin .scrwrap{max-height:calc(100vh - 196px)}
  body.uk-skin .kpi .box{min-width:calc(50% - 5px)}
  /* NO horizontal page overflow: grid/flex children must shrink below their content so a
     wide nowrap table scrolls INSIDE its card instead of ballooning the whole page. The
     frozen-pane grids (.scr/.uk-t) keep their own wrappers — never display:block them. */
  body.uk-skin .mkt-grid>*,body.uk-skin .majgrid>*,body.uk-skin .theme-groups>*,
  body.uk-skin .scards>*,body.uk-skin .uk-cols>*{min-width:0}
  body.uk-skin .ck-board{overflow-x:auto;-webkit-overflow-scrolling:touch}
  body.uk-skin table:not(.scr):not(.uk-t){display:block;overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}
}
</style>"""


def skin_css() -> str:
    """The reskin stylesheet (`<style>` block). Injected once per legacy page. Prepends the
    shared `ui_tokens` foundation (tokens + base + a11y + density scale) so every legacy page
    carries the SAME design language as the native v2 pages — focus rings, reduced-motion and
    the density switch now work site-wide. Defensive: a missing foundation degrades to the
    skin alone (never breaks the page)."""
    try:
        from src.web import ui_tokens as _T
        return _T.tokens_css() + _SKIN_CSS
    except Exception:  # noqa: BLE001
        return _SKIN_CSS


# the search form on every legacy page (action=/dash/stock). We swap the WHOLE form
# for the ui_kit Ask-Pat hint; the Cmd-K overlay (injected by the v2 nav) provides the
# ticker-jump, so search is preserved, not lost.
_HSEARCH_RE = re.compile(r'<form class="hsearch".*?</form>', re.S)


def _cmdk_hint() -> str:
    try:
        from src.web import ui_kit as K
        return K.cmdk_hint()
    except Exception:  # noqa: BLE001 — never let the hint break the skin
        return ('<div class="uk-cmdk">Search or ask Pat '
                '<kbd>&#8984;K</kbd></div>')


def _density_js() -> str:
    """The global density switch (defined in ui_kit so it's identical on both shells).
    Defensive: a missing ui_kit degrades to no switch, never breaks the page."""
    try:
        from src.web import ui_kit as K
        return K.density_js()
    except Exception:  # noqa: BLE001
        return ""


def reskin(html: str) -> str:
    """Post-process one ``_shell`` html string into the ui_kit language. Defensive +
    idempotent: an already-skinned string (or any non-_shell html) is returned as-is."""
    try:
        if not html or _SKIN_MARKER in html:
            return html
        # Only reskin a legacy dashboard._shell page. Every _shell output carries the
        # header row `<div class="hrow1">`; a ui_kit-native page (Coverage, the style
        # guide) never does — so this guard makes reskin() self-protecting: it can be
        # pointed at ANY html (a future global middleware) and will no-op on the v2
        # surfaces rather than double-skin them.
        if 'class="hrow1"' not in html:
            return html
        # mark the body so the scoped overlay applies (and signals 'already skinned').
        if "<body" not in html:
            return html
        out = html.replace("<body>", '<body class="uk-skin">', 1)
        if 'class="uk-skin"' not in out:  # body had attrs already
            out = re.sub(r"<body(?![^>]*uk-skin)", '<body class="uk-skin"', out, count=1)
        # a11y: a keyboard skip-link as the first focusable element, targeting the page body.
        out = re.sub(r"(<body[^>]*>)",
                     r'\1<a class="uk-skip" href="#uk-main">Skip to content</a>', out, count=1)
        out = out.replace('<div class="wrap', '<div id="uk-main" class="wrap', 1)
        # swap the legacy search box for the Ask-Pat hint (preserve via Cmd-K overlay).
        out = _HSEARCH_RE.sub(lambda _m: _cmdk_hint(), out, count=1)
        # inject the reskin css + the global density switch LAST in <head> (after _BASE_CSS).
        head_add = skin_css() + _density_js()
        if "</head>" in out:
            out = out.replace("</head>", head_add + "</head>", 1)
        else:
            out = head_add + out
        return out
    except Exception as e:  # noqa: BLE001 — a skin failure must never break the page
        log.warning("shell_skin reskin skipped: %s", e)
        return html


def install() -> bool:
    """Monkeypatch ``dashboard._shell`` so every legacy page renders in the ui_kit
    language. Idempotent (sentinel), defensive (never raises). Returns True if the
    skin is in place (newly or already)."""
    try:
        import src.web.dashboard as D
    except Exception as e:  # noqa: BLE001
        log.warning("shell_skin install skipped: dashboard import failed: %s", e)
        return False
    if getattr(D, _SKIN_SENTINEL, False):
        return True
    orig_shell = getattr(D, "_shell", None)
    if not callable(orig_shell):
        log.warning("shell_skin install skipped: dashboard._shell not found")
        return False

    def _skinned_shell(*args, **kwargs):
        return reskin(orig_shell(*args, **kwargs))

    # keep the wrapped original discoverable (debugging / revert).
    _skinned_shell.__wrapped__ = orig_shell  # type: ignore[attr-defined]
    D._shell = _skinned_shell

    # Rebind every OTHER module that captured `_shell` by reference at import time
    # (e.g. `from src.web.dashboard import _shell` in rrg_view / rsband_view /
    # rotation_view / participants_view / wolfe_view). Those modules resolve the bare
    # name `_shell` against their OWN globals, so patching dashboard._shell alone does
    # not reach them — their page would keep the legacy chrome. We sweep sys.modules
    # and repoint any module-level `_shell` that *is* the original to the wrapped one.
    # Generic (no hardcoded names), touches no source file, idempotent (the next sweep
    # finds the wrapped fn, not the original, so it skips). main.py imports every router
    # before wire() runs, so all such modules already exist here.
    import sys
    rebound = 0
    for _name, _mod in list(sys.modules.items()):
        if _mod is None or _mod is D:
            continue
        try:
            if getattr(_mod, "_shell", None) is orig_shell:
                _mod._shell = _skinned_shell
                rebound += 1
        except Exception:  # noqa: BLE001 — a quirky module must never break install
            continue

    setattr(D, _SKIN_SENTINEL, True)
    log.info("shell_skin installed — legacy pages reskinned to ui_kit (+%d imported refs)", rebound)
    return True


def _selftest() -> int:
    """Render a real legacy page through the wrapped shell + assert the reskin took,
    is no-loss (the body data survives), and is idempotent."""
    import sys
    import types

    import src.web.dashboard as D

    # simulate a view module that captured `_shell` by reference (like rrg_view) BEFORE
    # install, so we can prove the sys.modules rebind reaches it.
    _fake = types.ModuleType("src.web._fake_lens_for_skin_test")
    _fake._shell = D._shell  # the original, as `from ...dashboard import _shell` would bind
    sys.modules[_fake.__name__] = _fake

    assert install() is True
    assert install() is True  # idempotent — no double-wrap, still True
    assert _fake._shell is D._shell, "imported _shell reference was not rebound"
    assert reskin(_fake._shell("T", '<div class="card">x</div>', "markets")).count(_SKIN_MARKER) == 1, \
        "rebound ref does not produce a skinned page"
    del sys.modules[_fake.__name__]

    # a representative legacy page body with the common primitives.
    body = ('<div class="card"><h2>Markets</h2>'
            '<table><tr><th>Sym</th></tr><tr><td class="sym">RELIANCE</td>'
            '<td class="pos">+1.2%</td></tr></table></div>'
            '<div class="kpi"><div class="box"><div class="num">42</div>'
            '<div class="lbl">names</div></div></div>')
    out = D._shell("Markets · patearn", body, "markets", "2026-06-28", wide=True)

    assert "uk-skin" in out and _SKIN_MARKER in out, "skin not applied"
    assert "Search or ask Pat" in out, "Ask-Pat hint not swapped in"
    assert 'class="hsearch"' not in out, "legacy search form still present"
    assert "RELIANCE" in out and ">42<" in out, "body data lost (NOT no-loss)"
    assert out.count(_SKIN_MARKER) == 1, "skin injected more than once"
    # reskinning an already-skinned string is a no-op
    assert reskin(out) == out, "reskin not idempotent on its own output"
    # a non-_shell html (no <body>) is returned untouched
    assert reskin("<div>x</div>") == "<div>x</div>", "non-page html mutated"
    print("shell_skin selftest OK — reskin applied, no-loss, idempotent, defensive")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
