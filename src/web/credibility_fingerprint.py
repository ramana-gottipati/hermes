"""/dash/credibility — the management "promise vs delivery" fingerprint.

Flagship visual A of the premium-visuals program (docs/premium-visuals-brainstorm.md,
approved 2026-07-02). A per-symbol picture that a table of tier letters cannot convey:
every SETTLED promise plotted over time against a "promise kept" baseline, coloured by
outcome — so a *deteriorating streak of widening misses* (the actual credibility signal)
is visible at a glance.

ISOLATED on purpose (the rsband_view / mini_rrg pattern): a self-contained APIRouter in
its OWN module, durably mounted via v2_surfaces._ROUTER_SPECS (no dashboard.py / main.py
edit). Reuses the shared page shell (_shell) for chrome consistency, and exposes
``card_html(sym, conn=…)`` so the stock dossier's CCI tab can embed the same fingerprint.

Data (pure read, ₹0, no LLM):
  * concall_guidance — the promise ledger. Each settled row carries status
    (MET|PARTIAL|MISSED) + variance_pct (actual vs target at resolution). We plot
    variance_pct (unit-free → mixed metric types share ONE y-axis) coloured by status.
  * concall_scores — the rolled-up headline (credibility_trend, guidance_accuracy_score).

DESCRIPTIVE ONLY. This is a management *track record*, never a forward buy-signal — GATE B
failed on leak-free inputs (see docs/strategy-ledger.md + [[failure-models-ledger]]). The
copy on the surface says so.
"""
from __future__ import annotations

import html
import re
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell

try:  # glossary popovers (Tier-0 #1) — defensive, never fatal
    from src.web import glossary as _G
except Exception:  # noqa: BLE001
    _G = None

router = APIRouter()

# status → design token (var() is invalid in a raw SVG fill= attribute, so every
# token colour is injected via style="fill:…" / style="stroke:…", per mini_rrg).
_SCOLOR = {"MET": "var(--up)", "PARTIAL": "var(--warn)", "MISSED": "var(--down)"}
_SLABEL = {"MET": "Met", "PARTIAL": "Partial", "MISSED": "Missed"}
_TREND_TOK = {"IMPROVING": "var(--up)", "DETERIORATING": "var(--down)", "STABLE": "var(--ink-2)"}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _gloss(term: str, label: str) -> str:
    """Glossary '?' popover if available, else the plain label."""
    if _G is not None:
        try:
            return _G.gloss(term, label)
        except Exception:  # noqa: BLE001
            pass
    return _esc(label)


def _period_key(label) -> tuple:
    """Sort Indian FY period labels chronologically (lexical sort is WRONG:
    'Q4FY23' < 'Q1FY24' chronologically but not as strings). Robust fallback."""
    s = str(label or "").upper().replace(" ", "")
    mq = re.search(r"Q([1-4])", s)
    q = int(mq.group(1)) if mq else 0
    y = 9999
    my = re.search(r"FY'?(\d{2,4})", s)
    if my:
        yy = int(my.group(1))
        y = yy + 2000 if yy < 100 else yy
    else:
        my2 = re.search(r"(\d{4})", s)
        if my2:
            y = int(my2.group(1))
    return (y, q, s)


# ── data ────────────────────────────────────────────────────────────────────
def _fetch(sym: str, conn):
    """(points oldest→newest, headline row|None). Points = settled promises with a
    resolution variance; access by index so we don't depend on a row_factory."""
    rows = conn.execute(
        "SELECT source_period, resolved_period, statement_type, status, "
        "       variance_pct, claim_text "
        "  FROM concall_guidance "
        " WHERE symbol = ? AND status IN ('MET','PARTIAL','MISSED') "
        "   AND variance_pct IS NOT NULL",
        (sym,),
    ).fetchall()
    pts = []
    for r in rows:
        per = r[1] or r[0]
        pts.append({
            "period": per, "type": r[2], "status": r[3],
            "var": float(r[4]), "claim": r[5], "key": _period_key(per),
        })
    pts.sort(key=lambda p: p["key"])

    head = conn.execute(
        "SELECT credibility_score, guidance_accuracy_score, credibility_trend, "
        "       composite_score, as_of_period "
        "  FROM concall_scores WHERE symbol = ? "
        " ORDER BY as_of_period DESC LIMIT 1",
        (sym,),
    ).fetchone()
    return pts, head


def _picker(conn) -> str:
    """Empty-state: pick a symbol that actually has a settled-promise track record."""
    rows = conn.execute(
        "SELECT symbol, COUNT(*) c FROM concall_guidance "
        " WHERE status IN ('MET','PARTIAL','MISSED') AND variance_pct IS NOT NULL "
        " GROUP BY symbol HAVING c >= 2 ORDER BY c DESC LIMIT 48"
    ).fetchall()
    if rows:
        chips = "".join(
            f'<a class="pill" style="margin:3px" href="/dash/credibility?sym={quote_plus(str(s))}">'
            f'{_esc(s)} <span style="opacity:.55">{c}</span></a>' for s, c in rows)
        pick = f'<div style="margin-top:10px;line-height:2">{chips}</div>'
    else:
        pick = ('<div class="sub" style="margin-top:8px">No settled-promise ledger on '
                'record yet — run the CCI settlement pass first.</div>')
    return (
        '<div class="card">'
        '<div class="h2" style="margin:0 0 4px">Credibility fingerprint</div>'
        '<div class="sub" style="margin:0">Every settled management promise on one '
        'timeline against a “promise kept” baseline — the shape is the track record. '
        'Pick a company (count = settled promises):</div>'
        f'{pick}</div>'
        '<form method="get" action="/dash/credibility" style="margin-top:10px">'
        '<input name="sym" placeholder="Ticker, e.g. TANLA" '
        'style="padding:8px 10px;min-width:220px" autofocus> '
        '<button type="submit">Show fingerprint</button></form>'
    )


# ── the fingerprint SVG (pure renderer) ───────────────────────────────────────
def _txt(x, y, s, *, size=12, ink="var(--ink-2)", anchor="middle", weight=400) -> str:
    return (f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" '
            f'style="fill:{ink};font:{weight} {size}px system-ui,-apple-system,'
            f'Segoe UI,sans-serif">{_esc(s)}</text>')


def _svg(pts: list) -> str:
    if not pts:
        return ''
    L, R, TOP, BASE = 70, 686, 40, 150
    span = BASE - TOP                       # px for one vmax unit
    vmax = min(80.0, max(20.0, max(abs(p["var"]) for p in pts) * 1.15))
    n = len(pts)

    def X(i):
        return L if n == 1 else L + (R - L) * i / (n - 1)

    def Y(v):
        v = max(-vmax, min(vmax, v))
        return BASE - (v / vmax) * span

    H = BASE + span + 46
    out = [f'<svg width="100%" viewBox="0 0 720 {H:.0f}" role="img" '
           f'xmlns="http://www.w3.org/2000/svg" '
           f'aria-label="Promise versus delivery fingerprint: {n} settled promises">']

    # grids + baseline (0% = promise kept exactly)
    for v, strong in ((vmax, False), (vmax / 2, False), (0.0, True),
                      (-vmax / 2, False), (-vmax, False)):
        y = Y(v)
        col = "var(--line-2)" if strong else "var(--line)"
        out.append(f'<line x1="{L}" y1="{y:.0f}" x2="{R}" y2="{y:.0f}" '
                   f'style="stroke:{col};stroke-width:0.5"/>')
        lab = "0% · kept" if strong else (f'+{v:.0f}%' if v > 0 else f'−{abs(v):.0f}%')
        out.append(_txt(L - 8, y + 4, lab, anchor="end",
                        ink=("var(--ink-2)" if strong else "var(--ink-3)")))

    # trajectory connector (light) then markers
    poly = " ".join(f'{X(i):.0f},{Y(p["var"]):.0f}' for i, p in enumerate(pts))
    out.append(f'<polyline points="{poly}" '
               f'style="fill:none;stroke:var(--line-2);stroke-width:1.5"/>')
    step = max(1, -(-n // 8))               # label ~8 x-ticks max
    for i, p in enumerate(pts):
        x, y = X(i), Y(p["var"])
        col = _SCOLOR.get(p["status"], "var(--ink-2)")
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" '
                   f'style="fill:{col};stroke:var(--bg-1);stroke-width:2"/>')
        if i % step == 0 or i == n - 1:
            out.append(_txt(x, BASE + span + 22, p["period"], size=11, ink="var(--ink-3)"))

    # legend
    lx = L
    for st in ("MET", "PARTIAL", "MISSED"):
        out.append(f'<circle cx="{lx}" cy="{H-14:.0f}" r="5" style="fill:{_SCOLOR[st]}"/>')
        out.append(_txt(lx + 10, H - 10, _SLABEL[st], anchor="start", ink="var(--ink-2)"))
        lx += 22 + 9 * len(_SLABEL[st]) + 26
    out.append('</svg>')
    return "".join(out)


# ── the reusable card (dossier-embeddable) ────────────────────────────────────
def card_html(sym: str, pts=None, head=None, conn=None) -> str:
    sym = (sym or "").strip().upper()
    if pts is None:
        cm = nullcontext(conn) if conn is not None else get_conn()
        with cm as c:
            pts, head = _fetch(sym, c)

    if not pts:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">'
                f'{_esc(sym)} — credibility fingerprint</div>'
                '<div class="sub" style="margin:0">No settled promises on record for '
                'this company yet. The fingerprint needs at least a couple of resolved '
                'guidance items (MET / PARTIAL / MISSED).</div></div>')

    met = sum(1 for p in pts if p["status"] == "MET")
    missed = sum(1 for p in pts if p["status"] == "MISSED")
    trend = (head[2] if head else None) or "—"
    acc = head[1] if head else None

    def _pill(label_html, tok):
        return (f'<span class="pill" style="border-color:{tok};color:{tok}">'
                f'{label_html}</span>')

    pills = [_pill(f'{_gloss("credibility_trend", "Trend")}: '
                   f'{_esc(str(trend).title())}', _TREND_TOK.get(str(trend).upper(), "var(--ink-2)"))]
    if acc is not None:
        pills.append(_pill(f'{_gloss("guidance_accuracy_score", "Accuracy")}: '
                           f'{float(acc):.0f}/100', "var(--ink-2)"))
    pills.append(_pill(f'{met} met · {missed} missed of {len(pts)}', "var(--ink-2)"))

    return (
        '<div class="card">'
        f'<div class="h2" style="margin:0 0 2px">{_esc(sym)} — promise vs delivery</div>'
        '<div class="sub" style="margin:0 0 10px">Each settled promise vs a “promise '
        'kept” baseline, over time. <b>Descriptive track record — not a forward '
        'signal.</b></div>'
        f'<div style="margin:0 0 10px">{" ".join(pills)}</div>'
        f'{_svg(pts)}'
        '</div>'
    )


# ── route ─────────────────────────────────────────────────────────────────────
@router.get("/dash/credibility", response_class=HTMLResponse)
def credibility_page(sym: str = Query("")):
    sym = (sym or "").strip().upper()
    with get_conn() as conn:
        if not sym:
            return HTMLResponse(_shell("Credibility fingerprint", _picker(conn),
                                       active="strategies", wide=True))
        pts, head = _fetch(sym, conn)
        body = card_html(sym, pts, head, conn=conn)
    return HTMLResponse(_shell(f"{sym} — Credibility", body, active="strategies", wide=True))
