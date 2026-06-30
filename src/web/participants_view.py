"""/dash/participants — market-level "who is positioned" overlay.

The read surface for participant_oi.py (FII / DII / Pro / Client long-short open
interest). ISOLATED on purpose: a self-contained APIRouter in its OWN module so it
mounts via one line in main.py WITHOUT editing the (parallel-session-held)
dashboard.py / cockpit.py. Reuses the shared page shell (`_shell`) for chrome.

This is MARKET-AGGREGATE sentiment, not per-stock — the companion to the per-stock
F&O · OI tab. The headline read is the FII index-futures long:short stance and the
FII-vs-retail divergence. Descriptor-only (D62).
"""

from __future__ import annotations

import html

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell        # chrome + CSS (import-safe)

router = APIRouter()

_ORDER = ["FII", "DII", "PRO", "CLIENT"]
_LABEL = {"FII": "FII (foreign)", "DII": "DII (domestic inst)",
          "PRO": "Pro (prop desks)", "CLIENT": "Client (retail+HNI)"}


def _net(a, b):
    if a is None or b is None:
        return None
    return a - b


def _ratio(a, b):
    if not a or not b:
        return None
    return a / b


def _cell(v, scale):
    """Signed contracts cell: coloured bipolar bar + value (lakh contracts)."""
    if v is None:
        return '<td class="r mut">—</td>'
    col = "#2ea043" if v >= 0 else "#f85149"
    w = min(100, abs(v) / scale * 100) if scale else 0
    side = "left:50%" if v >= 0 else "right:50%"   # CL-VIEW-07: dead f-prefix dropped
    bar = (f'<span style="position:absolute;top:3px;{side};width:{w/2:.0f}%;height:9px;'
           f'background:{col}22;border-{"left" if v>=0 else "right"}:2px solid {col}"></span>')
    return (f'<td class="r" style="position:relative;color:{col};font-variant-numeric:tabular-nums">'
            f'{bar}<span style="position:relative">{v/1e5:+.2f}L</span></td>')


def _spark(series):
    """Zero-centred sparkline of a signed series (oldest→newest)."""
    pts = [v for v in series if v is not None]
    if len(pts) < 2:
        return ""
    m = max(abs(min(pts)), abs(max(pts))) or 1
    n = len(pts)
    coords = " ".join(f"{i/(n-1)*100:.1f},{15 - v/m*13:.1f}" for i, v in enumerate(pts))
    col = "#2ea043" if pts[-1] >= 0 else "#f85149"
    return (f'<svg width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none" '
            f'style="display:block">'
            f'<line x1="0" y1="15" x2="100" y2="15" stroke="#30363d" stroke-width="0.6"/>'
            f'<polyline points="{coords}" fill="none" stroke="{col}" stroke-width="1.3"/></svg>')


def render_participants() -> str:
    with get_conn() as conn:
        d = conn.execute("SELECT MAX(trade_date) m FROM participant_oi").fetchone()["m"]
        if not d:
            return ('<h2>Participant positioning</h2><div class="empty">No participant-OI data yet — '
                    'run <code>python -m src.automation.participant_oi --backfill</code>.</div>')
        rows = {r["client_type"]: dict(r) for r in conn.execute(
            "SELECT * FROM participant_oi WHERE trade_date=?", (d,)).fetchall()}
        hist = [dict(r) for r in conn.execute(
            "SELECT trade_date, fut_idx_long, fut_idx_short FROM participant_oi "
            "WHERE client_type='FII' ORDER BY trade_date DESC LIMIT 40", (
            )).fetchall()][::-1]

    def idx_net(ct):
        r = rows.get(ct, {})
        return _net(r.get("fut_idx_long"), r.get("fut_idx_short"))

    def stk_net(ct):
        r = rows.get(ct, {})
        return _net(r.get("fut_stk_long"), r.get("fut_stk_short"))

    def opt_bias(ct, pre):  # directional option OI: (callL + putS) − (callS + putL)
        r = rows.get(ct, {})
        try:
            return ((r.get(f"opt_{pre}_call_long") or 0) + (r.get(f"opt_{pre}_put_short") or 0)
                    - (r.get(f"opt_{pre}_call_short") or 0) - (r.get(f"opt_{pre}_put_long") or 0))
        except Exception:
            return None

    fii_net = idx_net("FII")
    fii_l, fii_s = rows.get("FII", {}).get("fut_idx_long"), rows.get("FII", {}).get("fut_idx_short")
    fii_ratio = _ratio(fii_l, fii_s)
    cli_net = idx_net("CLIENT")

    # --- headline FII gauge ---
    stance = ("strongly bearish" if (fii_ratio is not None and fii_ratio < 0.6)
              else "bearish-leaning" if (fii_ratio is not None and fii_ratio < 0.9)
              else "strongly bullish" if (fii_ratio is not None and fii_ratio > 1.7)
              else "bullish-leaning" if (fii_ratio is not None and fii_ratio > 1.1)
              else "balanced")
    scol = ("#f85149" if "bearish" in stance else "#2ea043" if "bullish" in stance else "#8b949e")
    diverge = ""
    if fii_net is not None and cli_net is not None and (fii_net > 0) != (cli_net > 0):
        diverge = (f' <b style="color:#d29922">FII and retail are on opposite sides</b> — '
                   f'the classic smart-money/retail divergence.')

    series = [_net(h["fut_idx_long"], h["fut_idx_short"]) for h in hist]
    # guard fii_net=None (CL-VIEW-08): a missing FII index-OI row makes idx_net("FII")
    # None; `(None/1e5):+.2f` 500s the whole page. Mirror the matrix _cell None-guard.
    net_str = f"{(fii_net/1e5):+.2f}L" if fii_net is not None else "—"
    gauge = (
        f'<div class="card" style="padding:10px 12px">'
        f'<div style="font-size:13px">FII index-futures stance: '
        f'<b style="color:{scol};font-size:16px">{html.escape(stance.upper())}</b> '
        f'<span class="mut">— net {net_str} contracts · long:short '
        f'{("%.2f" % fii_ratio) if fii_ratio else "—"}</span></div>'
        f'<div style="margin-top:6px">{_spark(series)}</div>'
        f'<div class="sub mut" style="margin-top:2px;font-size:11px">FII net index-futures '
        f'position, last {len(series)} days (oldest→newest). Net short = hedged/bearish; '
        f'watch the swing, not the level.{diverge}</div></div>')

    # --- positioning matrix ---
    scale = max((abs(idx_net(c) or 0) for c in _ORDER), default=1) or 1
    sscale = max((abs(stk_net(c) or 0) for c in _ORDER), default=1) or 1
    oscale = max((abs(opt_bias(c, "idx") or 0) for c in _ORDER), default=1) or 1
    body = ""
    for ct in _ORDER:
        r = rows.get(ct, {})
        rt = _ratio(r.get("fut_idx_long"), r.get("fut_idx_short"))
        body += (f'<tr><td class="l"><b>{html.escape(_LABEL[ct])}</b></td>'
                 + _cell(idx_net(ct), scale)
                 + f'<td class="r mut">{("%.2f" % rt) if rt else "—"}</td>'
                 + _cell(stk_net(ct), sscale)
                 + _cell(opt_bias(ct, "idx"), oscale)
                 + '</tr>')
    matrix = (
        '<div class="sub" style="margin:12px 0 4px">Net positioning by participant '
        '<span class="mut">(green = net long, red = net short; contracts in lakhs)</span></div>'
        '<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
        '<thead><tr><th class="l">Participant</th><th class="r">Index fut net</th>'
        '<th class="r">L/S</th><th class="r">Stock fut net</th>'
        '<th class="r">Index opt bias</th></tr></thead>'
        f'<tbody>{body}</tbody></table></div>')

    # --- history table ---
    hrows = ""
    for h in reversed(hist[-15:]):
        nt = _net(h["fut_idx_long"], h["fut_idx_short"])
        rt = _ratio(h["fut_idx_long"], h["fut_idx_short"])
        c = "#2ea043" if (nt or 0) >= 0 else "#f85149"
        hrows += (f'<tr><td class="l mut">{html.escape(h["trade_date"])}</td>'
                  f'<td class="r" style="color:{c}">{(nt/1e5):+.2f}L</td>'
                  f'<td class="r mut">{("%.2f" % rt) if rt else "—"}</td></tr>')
    histtbl = ('<div class="sub" style="margin:12px 0 4px">FII index-futures history</div>'
               '<div class="card" style="padding:6px 10px"><table class="ck-t">'
               '<thead><tr><th class="l">Date</th><th class="r">Net (L)</th><th class="r">L/S</th>'
               '</tr></thead><tbody>' + hrows + '</tbody></table></div>')

    foot = ('<div class="sub mut" style="margin-top:10px;font-size:11px">NSE participant-wise OI '
            '(FII/DII/Pro/Client), published daily after close. Market-aggregate — the companion to '
            'the per-stock F&amp;O·OI tab. Index-option bias = (call-long + put-short) − (call-short + '
            'put-long). Descriptor / sentiment context (D62) — not a standalone timing signal.</div>')

    return (f'<h2 style="margin-top:2px">🧭 Participant positioning '
            f'<span class="sub" style="margin:0">who is long / short — FII · DII · Pro · Client · '
            f'as of {html.escape(d)}</span></h2>'
            + gauge + matrix + histtbl + foot)


@router.get("/dash/participants", response_class=HTMLResponse)
def dash_participants() -> HTMLResponse:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
    sig_date = row["d"] if row and row["d"] else ""
    return HTMLResponse(_shell("Participants · patearn", render_participants(),
                               "markets", sig_date, wide=True))
