"""ui_showcase.py — the living design-system style guide at /dash/_ui (Lane A2).

A single page that proves the whole v2 language: every design token (color, type scale,
spacing, radius, elevation), every component (from `ui_kit` AND `ui_components`), the
density switch, the loading/empty/error states, and the responsive behaviour. It is the
reference a designer/engineer opens to see "what does the system give me" — and the QA
surface for this lane (if a component breaks, it shows here first).

Self-contained: includes `ui_tokens` + `ui_components` CSS in its own body and renders
through `ui_kit.shell`, so it exercises the shared foundation WITHOUT modifying the native
shell (zero risk to Coverage/Strategist/Screen+). Self-mounts via `v2_surfaces._ROUTER_SPECS`.

Route: GET /dash/_ui
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web import ui_kit as K
from src.web import ui_tokens as T
from src.web import ui_components as C

router = APIRouter()


def _swatch(var: str, name: str) -> str:
    return (f'<div style="display:flex;flex-direction:column;gap:5px">'
            f'<div style="height:46px;border-radius:var(--r-sm);border:1px solid var(--line-2);'
            f'background:var(--{var})"></div>'
            f'<div style="font-size:var(--fs-2xs);color:var(--ink-3)">{name}<br>'
            f'<span class="num">var(--{var})</span></div></div>')


def _sec(title: str, body: str, *, eyebrow: str = "") -> str:
    eb = f'<div class="uk-eyebrow">{K.esc(eyebrow)}</div>' if eyebrow else ""
    return (f'<section style="margin:0 0 var(--sp-6)"><h2 style="font:var(--fw-semi) var(--fs-xl)/1.2 var(--font);'
            f'color:var(--ink);margin:0 0 var(--sp-3)">{K.esc(title)}</h2>{eb}{body}</section>')


def _body() -> str:
    # ── color ──
    surfaces = "".join(_swatch(v, v) for v in ("bg-0", "bg-1", "bg-2", "bg-3", "bg-4", "line", "line-2"))
    ink = "".join(_swatch(v, v) for v in ("ink", "ink-2", "ink-3", "ink-4"))
    accents = "".join(_swatch(v, v) for v in ("accent", "accent-cy", "up", "down", "warn", "cred"))
    color = _sec("Color", f"""
      <div class="uk-eyebrow">Surfaces &amp; hairlines</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:10px;margin-bottom:16px">{surfaces}</div>
      <div class="uk-eyebrow">Ink</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:10px;margin-bottom:16px">{ink}</div>
      <div class="uk-eyebrow">Accent &amp; semantic</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:10px">{accents}</div>""")

    # ── type ──
    sizes = [("3xl", "Display"), ("2xl", "Title"), ("xl", "Heading"), ("lg", "Subhead"),
             ("md", "Body"), ("sm", "Small"), ("xs", "Caption"), ("2xs", "Micro")]
    typ = "".join(
        f'<div style="display:flex;align-items:baseline;gap:14px;padding:7px 0;border-bottom:1px solid var(--line)">'
        f'<span style="width:64px;color:var(--ink-3);font-size:var(--fs-2xs)" class="num">--fs-{k}</span>'
        f'<span style="font-size:var(--fs-{k});color:var(--ink);font-weight:var(--fw-semi)">{lbl} · Patearn 1,412.30</span></div>'
        for k, lbl in sizes)
    type_sec = _sec("Type scale", typ, eyebrow="tabular numerics · the instrument feel")

    # ── spacing ──
    sp = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
        f'<span class="num" style="width:54px;color:var(--ink-3);font-size:var(--fs-2xs)">--sp-{n}</span>'
        f'<div style="height:13px;width:var(--sp-{n});background:var(--accent);border-radius:3px"></div></div>'
        for n in range(1, 9))
    space_sec = _sec("Spacing", sp)

    # ── buttons ──
    buttons = _sec("Buttons", f"""
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
        {C.btn("Primary", variant="primary")}{C.btn("Secondary")}{C.btn("Ghost", variant="ghost")}
        {C.btn("Danger", variant="danger")}{C.btn("Disabled", attrs="disabled")}
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        {C.btn("Small", variant="primary", size="sm")}{C.btn("Default", variant="primary")}
        {C.btn("Large", variant="primary", size="lg")}{C.btn("With icon", icon="✦")}
      </div>""")

    # ── form fields ──
    fields = _sec("Form fields", f"""
      <div class="uk-cols-2">
        {C.field("Ticker", '<input class="uk-input" placeholder="e.g. RELIANCE">')}
        {C.field("Benchmark", '<select class="uk-select"><option>Nifty 500</option><option>Nifty 50</option></select>')}
      </div>
      <div style="margin-top:12px">{C.field("Notes", '<textarea class="uk-textarea" rows="2" placeholder="free text…"></textarea>')}</div>""")

    # ── tabs (working) ──
    bar, tabs_js = C.tabs([("ov", "Overview"), ("dt", "Data"), ("nt", "Notes")], active=0)
    tabs_sec = _sec("Tabs", f"""
      <div class="uk-tabwrap">{bar}
        <div class="uk-pane on" id="ukpane-ov" style="padding:14px 2px">Overview pane — switch tabs above.</div>
        <div class="uk-pane" id="ukpane-dt" style="padding:14px 2px">Data pane — {C.tag("frozen-pane")} {C.tag("CSV")}.</div>
        <div class="uk-pane" id="ukpane-nt" style="padding:14px 2px">Notes pane — descriptive only.</div>
      </div>{tabs_js}""")

    # ── pills / verdicts / stats (from ui_kit) ──
    pills = " ".join([K.pill("Leader", "up"), K.pill("Accumulate", "acc"), K.pill("Credibility ↑", "cred"),
                      K.pill("Re-rating", "warn"), K.pill("Avoid", "down"), K.pill("Neutral", "neutral")])
    stats = "".join(f'<div class="uk-card" style="flex:1;min-width:150px">{s}</div>' for s in [
        K.stat("Price", "1,412.30", "+1.2%", "up"), K.stat("RS rank", "84", "improving", "up"),
        K.stat("CCI", "72", "+3 qtr", "up"), K.stat("MEP", "Accum", "8 sessions", "up")])
    kit_sec = _sec("ui_kit primitives", f"""
      <div class="uk-eyebrow">Verdict pills</div>
      <div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:16px">{pills}</div>
      <div class="uk-eyebrow">Stats</div>
      <div class="uk-row" style="margin-bottom:16px">{stats}</div>
      <div class="uk-eyebrow">Segmented · badge</div>
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        {K.seg([("vs Nifty 500", "#", True), ("vs Nifty 50", "#", False)])}
        {K.badge("point-in-time · zero look-ahead")}</div>""")

    # ── notes / states ──
    notes = _sec("Inline notes", f"""
      <div style="display:grid;gap:10px">
        {C.note("Descriptive read — no buy/sell implied.")}
        {C.note("Coverage is missing-not-at-random; read with selection in mind.", "warn")}
        {C.note("Deterioration tape on this name.", "down")}
        {C.note("Earning-trust tape — guidance landed.", "up")}
      </div>""")
    states = _sec("Loading · empty · error", f"""
      <div class="uk-cols">
        <div class="uk-card"><div class="uk-eyebrow">Skeleton</div>{C.skeleton(4)}</div>
        <div class="uk-card"><div class="uk-eyebrow">Spinner</div><div style="padding:14px 0">{C.spinner("loading…")}</div>
           <div class="uk-eyebrow" style="margin-top:10px">Progress</div>{C.progress(64)}</div>
        <div class="uk-card" style="padding:0">{C.empty("No matches", "Loosen a filter or widen the scope.")}</div>
        <div class="uk-card" style="padding:0">{C.error_state("Couldn’t load", "The snapshot is unavailable in this environment.")}</div>
      </div>""")

    # ── misc: tooltip · kbd · switch ──
    misc = _sec("Tooltip · kbd · switch", f"""
      <div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap">
        <span class="uk-tip" tabindex="0" data-tip="A point-in-time credibility read"
              style="border-bottom:1px dashed var(--ink-3);cursor:help">Hover me</span>
        <span>Press <span class="uk-kbd">⌘K</span> to ask Pat</span>
        <label class="uk-switch" onclick="this.classList.toggle('on')"><span class="tk"></span>Toggle</label>
      </div>""")

    # ── density (live, local to this page's .uk) ──
    density = _sec("Density", f"""
      <div class="uk-note" style="margin-bottom:12px"><span class="d"></span>
        <div>Comfortable (default) vs compact — the whole system scales from the <span class="num">--row-pad</span>,
        spacing and base-size tokens. The global toggle (every page, persisted) lands with the chrome.</div></div>
      <div style="display:flex;gap:10px">
        {C.btn("Comfortable", variant="primary", size="sm", attrs='onclick="ukDemoDensity(0)"')}
        {C.btn("Compact", size="sm", attrs='onclick="ukDemoDensity(1)"')}
      </div>
      <script>function ukDemoDensity(on){{var u=document.querySelector('.uk');
        if(on){{u.setAttribute('data-density','compact');}}else{{u.removeAttribute('data-density');}}}}</script>""",
        eyebrow="try it — affects this page")

    head = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:2px">'
        '<h1 class="uk-h1">Design system</h1>' + K.pill("v2", "acc") + K.badge("Lane A2 · ui_tokens + ui_components") +
        '</div><div class="sec" style="margin-bottom:var(--sp-5);color:var(--ink-2)">'
        'The single visual language behind Patearn — tokens, components, states, density, responsive.</div>')

    # tokens_css + components_css are included in-body (self-contained; native shell untouched).
    return (T.tokens_css() + C.components_css() + head + color + type_sec + space_sec +
            buttons + fields + tabs_sec + kit_sec + notes + states + misc + density)


@router.get("/dash/_ui", response_class=HTMLResponse)
def ui_showcase() -> HTMLResponse:
    from src.web import v2_surfaces as V
    nav = K.nav_links(V.site_nav("markets"))
    sub = K.subnav([("Design system", "/dash/_ui", True)])
    return HTMLResponse(K.shell("Design system · patearn", _body(), active="markets", sub=sub, nav_html=nav))
