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
from src.web import infographics as ifx      # shared inline-SVG primitives

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
    col = "var(--up)" if v >= 0 else "var(--down)"
    tint = "rgba(var(--up-rgb),.13)" if v >= 0 else "rgba(var(--down-rgb),.13)"
    w = min(100, abs(v) / scale * 100) if scale else 0
    side = "left:50%" if v >= 0 else "right:50%"   # CL-VIEW-07: dead f-prefix dropped
    bar = (f'<span style="position:absolute;top:3px;{side};width:{w/2:.0f}%;height:9px;'
           f'background:{tint};border-{"left" if v>=0 else "right"}:2px solid {col}"></span>')
    return (f'<td class="r" style="position:relative;color:{col};font-variant-numeric:tabular-nums">'
            f'{bar}<span style="position:relative">{v/1e5:+.2f}L</span></td>')


def _spark(series):
    """Zero-centred sparkline of a signed series (oldest→newest)."""
    pts = [v for v in series if v is not None]
    if len(pts) < 2:
        return ""
    m = max(abs(min(pts)), abs(max(pts))) or 1
    n = len(pts)
    coords = " ".join(f"{i/(n-1)*100:.1f},{26 - v/m*22:.1f}" for i, v in enumerate(pts))
    col = "var(--up)" if pts[-1] >= 0 else "var(--down)"
    area = coords + " 100,26 0,26"        # fill the deviation-from-zero band so it reads as a chart
    return (f'<svg width="100%" height="52" viewBox="0 0 100 52" preserveAspectRatio="none" '
            f'style="display:block">'
            f'<polygon points="{area}" style="fill:{col}" fill-opacity="0.10"/>'
            f'<line x1="0" y1="26" x2="100" y2="26" style="stroke:var(--line-2)" stroke-width="0.6"/>'
            f'<polyline points="{coords}" fill="none" style="stroke:{col}" stroke-width="1.4"/></svg>')


def _pct_of(sorted_vals, v):
    if not sorted_vals or v is None:
        return 50.0
    lo, hi = 0, len(sorted_vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] <= v:
            lo = mid + 1
        else:
            hi = mid
    return 100.0 * lo / len(sorted_vals)


def render_positioning_tape(conn) -> str:
    """The FLAGSHIP fix (D-recon): the FII stance across its FULL history (~2.5y), with a
    percentile gauge and the FII-vs-retail mirror — replacing the amnesiac 40-day sparkline
    below with the regime + extremity the short window hides. Descriptive positioning (D62)."""
    rows = conn.execute(
        "SELECT trade_date, client_type, fut_idx_long, fut_idx_short FROM participant_oi "
        "WHERE client_type IN ('FII','CLIENT') ORDER BY trade_date").fetchall()
    if not rows:
        return ""
    fii_ls, fii_net, cli_net, dates = {}, {}, {}, []
    for r in rows:
        d, ct = r["trade_date"], r["client_type"]
        lo, sh = r["fut_idx_long"], r["fut_idx_short"]
        if ct == "FII":
            if d not in fii_net:
                dates.append(d)
            fii_net[d] = (lo - sh) if (lo is not None and sh is not None) else None
            fii_ls[d] = (lo / sh) if (lo and sh) else None
        else:
            cli_net[d] = (lo - sh) if (lo is not None and sh is not None) else None
    dates = sorted(set(dates))
    if len(dates) < 20:
        return ""
    ratio = [fii_ls.get(d) for d in dates]
    fii_n = [(fii_net.get(d) / 1e5) if fii_net.get(d) is not None else None for d in dates]
    cli_n = [(cli_net.get(d) / 1e5) if cli_net.get(d) is not None else None for d in dates]
    latest = next((r for r in reversed(ratio) if r is not None), None)
    dist = sorted(r for r in ratio if r is not None)
    pct = _pct_of(dist, latest) if latest is not None else 50.0

    if pct <= 12:
        extreme = (f'<b style="color:var(--down)">near-record net-short</b> — more bearish than '
                   f'{100 - pct:.0f}% of the last {len(dist)} days')
    elif pct >= 88:
        extreme = (f'<b style="color:var(--up)">near-record net-long</b> — more bullish than '
                   f'{pct:.0f}% of the last {len(dist)} days')
    else:
        extreme = f'{ifx._ord(pct)} percentile of {len(dist)} days'

    tape = (
        '<div class="sub" style="margin:16px 0 4px">📼 The positioning tape '
        '<span class="mut">— the FII stance across its FULL 2.5-year history, not the last 40 days</span></div>'
        '<div class="card" style="padding:12px 14px">'
        f'<div style="font-size:13px">FII index-futures long:short — '
        f'<b style="font-variant-numeric:tabular-nums">{("%.2f" % latest) if latest else "—"}</b> '
        f'<span class="mut">· {extreme}</span></div>'
        '<div style="font-size:11px;color:var(--ink-3);margin:8px 0 2px">'
        'LONG:SHORT RATIO — green = net long (&gt;1), red = net short (&lt;1)</div>'
        + ifx.plain('This line is foreigners’ <b>“up” bets divided by “down” bets</b> on the whole '
                    'market. <b>Above</b> the dotted line = betting the market rises; <b>below</b> = betting it '
                    'falls. It’s sitting near the bottom of its 2½-year range — an unusually bearish stance.')
        + ifx.spark_area(ratio, h=120, signed=True, baseline=1.0)
        + '<div style="max-width:520px;margin-top:8px">'
        + ifx.pct_gauge(latest, dist, label="today", vfmt=2) + '</div>'
        + '<div class="sub mut" style="margin-top:6px;font-size:11px">FII shorts are mostly <b>hedging '
          'and arbitrage</b> (protective/paired trades), not simple bets the market will fall — so read '
          'this as <b>stance and how extreme it is</b>, never a market-timing call (D62). The percentile '
          'just answers "how unusual is today vs its own history".</div>'
        '</div>'
        '<div class="sub" style="margin:16px 0 4px">🪞 Smart money vs retail '
        '<span class="mut">— who is on the other side of the FII short</span></div>'
        '<div class="card" style="padding:12px 14px">'
        + ifx.plain('For every bet, someone takes the other side. Watch the two lines mirror each other: '
                    'as <b>foreigners</b> pile on “down” bets (first chart dips), <b>everyday investors</b> '
                    'pile on “up” bets (second chart rises) by almost the same amount. Retail is the counterparty.')
        + '<div style="font-size:11px;color:var(--ink-3);margin-bottom:2px">FII net index position (lakh contracts)</div>'
        + ifx.spark_area(fii_n, h=84, signed=True, baseline=0)
        + '<div style="font-size:11px;color:var(--ink-3);margin:10px 0 2px">CLIENT (retail + HNI) net index position</div>'
        + ifx.spark_area(cli_n, h=84, signed=True, baseline=0)
        + '<div class="sub mut" style="margin-top:6px;font-size:11px">A near-perfect mirror: as FII '
          'shorts deepen, retail longs swell in lockstep — retail is the counterparty. "CLIENT" is '
          'retail + HNI + residual, not pure retail. Positioning context, not a signal.</div>'
        '</div>')
    return tape


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
        tape_html = render_positioning_tape(conn)   # the full-history flagship tape

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
    scol = ("var(--down)" if "bearish" in stance else "var(--up)" if "bullish" in stance else "var(--ink-2)")
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
        f'position, last {len(series)} days (oldest→newest). Net short = leaning bearish (often just '
        f'hedging); watch the swing, not the level.{diverge}</div></div>')

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
    for h in reversed(hist[-8:]):        # compact companion to the matrix — the 40-day trend is the sparkline above
        nt = _net(h["fut_idx_long"], h["fut_idx_short"])
        rt = _ratio(h["fut_idx_long"], h["fut_idx_short"])
        c = "var(--up)" if (nt or 0) >= 0 else "var(--down)"
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

    _bear = (fii_ratio is not None and fii_ratio < 0.9)
    _blurb = ("betting hard against the market — they hold far more “down” bets than “up”, and everyday "
              "investors are taking the other side" if _bear else
              "leaning bullish — more “up” bets than “down”")
    return (f'<h2 style="margin-top:2px">🧭 Participant positioning '
            f'<span class="sub" style="margin:0">who is long / short — FII · DII · Pro · Client · '
            f'as of {html.escape(d)}</span></h2>'
            + ifx.readability_css()
            + ifx.bottom_line(f'Right now foreign investors (FIIs) are <b>{_blurb}</b>. This page shows '
                              'who is positioned which way in the futures market — foreigners, Indian '
                              'funds, professional desks, and everyday investors.')
            + ifx.how_to_read_link()
            + '<div class="sub mut" style="font-size:11px;margin:2px 0 8px">FII = foreign investors · '
              'DII = Indian mutual funds/insurers · Pro = professional trading desks · Client = everyday '
              '+ wealthy retail · “long” = betting up, “short” = betting down.</div>'
            + gauge
            + tape_html
            # matrix (5-col) + history (3-col) were two narrow tables each alone in a
            # full-width card → paired side-by-side so neither leaves a half-empty row.
            + '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start">'
            + f'<div style="flex:1.5 1 340px;min-width:300px">{matrix}</div>'
            + f'<div style="flex:1 1 250px;min-width:240px">{histtbl}</div></div>'
            + foot)


@router.get("/dash/participants", response_class=HTMLResponse)
def dash_participants() -> HTMLResponse:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
    sig_date = row["d"] if row and row["d"] else ""
    return HTMLResponse(_shell("Participants · patearn", render_participants(),
                               "participants", sig_date, wide=True))
