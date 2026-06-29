"""/dash/harmonic — the harmonic XABCD scanner surface + the per-symbol chart-overlay feed.

The D72 harmonic lane (engine: src/automation/harmonic_patterns.py + harmonic_signals.py;
design + the reliability benchmark: docs/harmonic-pattern-design.md). DESCRIPTIVE-only,
read BY SIDE (the backtest: BULL = a modest fit-graded selection edge over drift, BEAR ≈
short-drift / tail-only — same shape as Wolfe).

Two routes, both on this module's own APIRouter, which is mounted by being included INTO
the already-mounted wolfe_view router (one line in wolfe_view.py) — so no main.py edit and
it survives a redeploy (committed), unlike an in-place hook:
  • /dash/harmonic            — the scanner page (reads the nightly harmonic_signals
                                snapshot, live fallback); rows click through to the stock chart.
  • /dash/harmonic/overlay    — JSON of a symbol's harmonic patterns for the /dash/stock
                                overlay (live-computed; confirmed recent + forming PRZ).
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from src.core.db import get_conn
from src.automation import harmonic_patterns as HP
from src.automation import harmonic_signals as HS

try:
    from src.web.dashboard import _shell, _esc, _q
except Exception:  # pragma: no cover
    from urllib.parse import quote_plus

    def _esc(s):
        return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _q(s):
        return quote_plus(str(s) if s is not None else "")

    def _shell(title, body, active, latest_date="", wide=False):
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{title}</title><style>body{{background:#0d1117;color:#e6edf3;"
                "font-family:system-ui,sans-serif;margin:0;padding:16px}</style></head>"
                f"<body>{body}</body></html>")

router = APIRouter()

_BULL, _BEAR = "#3fb950", "#f85149"


# --------------------------------------------------------------------------- #
# overlay feed — a symbol's harmonic patterns shaped for the candle chart       #
# --------------------------------------------------------------------------- #
@router.get("/dash/harmonic/overlay")
def harmonic_overlay(sym: str = Query("", max_length=24),
                     confirmed: int = Query(6, ge=0, le=20),
                     max_age: int = Query(180, ge=10, le=2000),
                     tf: str = Query("d", pattern="^[dwm]$")):
    """JSON: the symbol's harmonic patterns for the /dash/stock overlay. Returns the most
    recent CONFIRMED patterns (capped) + all FORMING ones (with the projected PRZ).
    tf='d'/'w'/'m' detects on daily / weekly / monthly bars (multi-TF hand-off)."""
    sym = sym.strip().upper()
    if not sym:
        return JSONResponse({"patterns": []})
    # weekly/monthly bars are coarser → relax the recency window so W/M setups surface
    age = max_age if tf == "d" else max(max_age, 1000)
    with get_conn() as conn:
        pats = HP.detect(conn, sym, tf=tf, forming=True, max_age=age)
    conf = [p for p in pats if p.state == "CONFIRMED"]
    form = [p for p in pats if p.state == "FORMING"]
    conf = sorted(conf, key=lambda p: -p.points[-1][1])[:confirmed]   # newest D first
    out = []
    for p in conf + form:
        out.append({
            "name": p.name, "dir": p.direction, "state": p.state,
            "score": p.score, "tag": ("edge" if p.direction == "BULL" else "tail"),
            "points": [{"label": lbl, "t": dt, "price": pr}
                       for (lbl, _i, pr, dt) in p.points],
            "prz": p.prz or None, "rsi_d": p.rsi_d})
    return JSONResponse({"patterns": out, "sym": sym, "tf": tf})


# --------------------------------------------------------------------------- #
# scanner page — the persisted snapshot, read by side                          #
# --------------------------------------------------------------------------- #
def _zone(r):
    if r["state"] == "CONFIRMED":
        return _esc(r["d_price"]) if r["d_price"] is not None else "—"
    lo, hi = r.get("prz_lo"), r.get("prz_hi")
    if lo is None:
        return "—"
    return f'{_esc(round(min(lo, hi), 1))}–{_esc(round(max(lo, hi), 1))}'


@router.get("/dash/harmonic", response_class=HTMLResponse)
def harmonic_page(universe: str = Query("nifty500", max_length=24),
                  refresh: int = Query(0, ge=0, le=1),
                  tf: str = Query("d", pattern="^[dwm]$")):
    """The harmonic scanner — reads the nightly harmonic_signals snapshot (instant) for the
    daily timeframe, with a live fallback. W/M timeframes are always a live scan (no nightly
    snapshot kept for them). Descriptive, read by side; click a row → that stock's chart."""
    uni = universe or "nifty500"
    with get_conn() as conn:
        # snapshot only exists for the daily TF; W/M is a live multi-TF scan (the hand-off)
        data = None if (refresh or tf != "d") else HS.latest(conn, universe=uni)
        if data:
            rows, scan_date, computed = data["rows"], data.get("scan_date"), data.get("computed_at")
            live = False
        else:
            rows = HS.scan(conn, universe=uni, tf=tf)
            scan_date, computed, live = None, None, True
    nin = sum(1 for r in rows if r["in_zone"])
    tf = tf if tf in ("d", "w", "m") else "d"
    _tf_iv = {"d": "d", "w": "w", "m": "m"}[tf]   # the chart interval to open at
    _tf_label = {"d": "daily", "w": "weekly", "m": "monthly"}[tf]
    trs = []
    for r in rows:
        bull = r["dir"] == "BULL"
        col = _BULL if bull else _BEAR
        tag = ('<span style="color:#3fb950;font-size:11px" title="OOS benchmark: bull harmonics beat long-drift at every horizon (Gartley-bull strongest); fit-score stratifies">✓ edge</span>'
               if bull else
               '<span style="color:#d29922;font-size:11px" title="≈ short-drift in the backtest — tail/regime only, not a standalone edge">⚠ tail</span>')
        status = ('<span style="color:#3fb950;font-weight:700">● IN</span>' if r["in_zone"]
                  else '<span style="color:#6e7681">watch</span>')
        sc = f'{r["score"]:.2f}' if (r["state"] == "CONFIRMED" and r["score"]) else "—"
        trs.append(
            f'<tr onclick="location.href=\'/dash/stock?sym={_q(r["sym"])}\'" '
            f'style="cursor:pointer;border-top:1px solid #21262d" '
            f'onmouseover="this.style.background=\'#1c2430\'" onmouseout="this.style.background=\'transparent\'">'
            f'<td style="padding:6px 10px"><b style="color:{col}">{_esc(r["sym"])}</b></td>'
            f'<td>{_esc(r["pattern"])}</td>'
            f'<td style="color:{col};font-weight:600">{r["dir"]}<br>{tag}</td>'
            f'<td style="color:#8b949e">{_esc(r["state"].title())}</td>'
            f'<td>{status}</td><td style="color:#8b949e">{r["age"]}d</td>'
            f'<td>{_esc(r["cmp"])}</td><td>{_zone(r)}</td>'
            f'<td style="color:#8b949e">{sc}</td></tr>')
    if not rows:
        trs = [f'<tr><td colspan="9" style="padding:14px;color:#8b949e">No fresh {_tf_label} harmonic setups right now — '
               f'try <a href="/dash/harmonic?tf={tf}&refresh=1" style="color:#58a6ff">a live recompute</a>.</td></tr>']
    head = ('symbol', 'pattern', 'dir', 'state', 'status', 'age', 'CMP', 'zone / PRZ', 'fit')
    if tf == "d":
        fresh_line = (f'as-of <b>{_esc(scan_date or "—")}</b> '
                      f'<span style="color:#6e7681">(nightly snapshot{(" · " + _esc(computed[:16])) if computed else ""})</span> · '
                      f'<a href="/dash/harmonic?refresh=1" style="color:#58a6ff" title="recompute live now">↻ refresh</a>'
                      if not live else 'as-of today <span style="color:#6e7681">(live)</span>')
    else:
        fresh_line = f'{_tf_label} bars <span style="color:#6e7681">(live multi-TF scan)</span>'
    # timeframe selector — D from the nightly snapshot, W/M live (the multi-TF hand-off)
    tf_pills = " ".join(
        f'<a href="/dash/harmonic?tf={t}" style="text-decoration:none;padding:2px 9px;border-radius:5px;font-size:12px;'
        + ('background:#1f6feb;color:#fff' if t == tf else 'color:#8b949e;border:1px solid #30363d') + f'">{lbl}</a>'
        for (t, lbl) in (("d", "Daily"), ("w", "Weekly"), ("m", "Monthly")))
    body = (
        '<h2>Harmonic scanner <span style="color:#8b949e;font-size:15px;font-weight:400">— XABCD, read by side</span></h2>'
        '<div class="sub" style="margin-bottom:6px">Auto-detected harmonic patterns '
        '(Gartley · Bat · Butterfly · Crab · Deep Crab) on daily bars — <b>CONFIRMED</b> '
        '(point D printed → reversal candidate) and <b>FORMING</b> (X-A-B-C printed, D '
        'projected into a PRZ — caught down the stream). <b>Read by side</b> '
        '(survivorship-inclusive backtest, 1,052 patterns): '
        '<span style="color:#3fb950;font-weight:600">BULL ✓ edge</span> = a modest, real, '
        'fit-graded selection edge that beats long-drift at every horizon (Gartley-bull '
        'strongest); <span style="color:#d29922;font-weight:600">BEAR ⚠ tail</span> ≈ '
        'short-drift, reliable only when the broad tape is weak. <b>Click a row</b> for the '
        'chart. <span style="color:#3fb950">● IN</span> = price in the reversal zone now. '
        '<i>Descriptive — not a buy/sell signal.</i></div>'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
        f'<span style="color:#6e7681;font-size:11px;text-transform:uppercase;letter-spacing:.4px">Timeframe</span>{tf_pills}</div>'
        f'<div style="color:#8b949e;font-size:13px;margin-bottom:10px">{_esc(uni)} · {_tf_label} · {fresh_line} · '
        f'<b>{len(rows)} setups · {nin} in zone now</b></div>'
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        '<thead><tr style="color:#8b949e;text-align:left">'
        + "".join(f'<th style="padding:6px 10px">{h}</th>' for h in head)
        + '</tr></thead><tbody>' + "".join(trs) + '</tbody></table>')
    return HTMLResponse(_shell("Harmonic scanner", body, "wolfe", wide=True))
