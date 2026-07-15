"""/dash/results-reactions — the Results-Reaction Scanner (descriptive).

The war-room board for results season: who just reported, what was the Net-Profit surprise (SUE, no
analysts), did the strong hand confirm it on the tape (delivered value), and — for older events — the
realized abnormal drift. It is the DESCRIPTIVE product of the 2026-07-05 PEAD study, whose tradeable
book was falsified (ledger § Experiment 2026-07-05: net return/vol 0.10 vs bench 0.85). So this is a
scanner in the exact shape of our other descriptive lenses (rotation / rsband / momentum-scan) —
NOT a signal, NOT a buy list. Every number is realized history or an explicitly labelled base-rate.

House pattern (like momentum-scan reads `momentum_scan`, capture-map reads `capture_signals`): a
nightly research-venv job (`explosive_moves.pead_surface --snapshot`) precomputes the
`results_reactions` table in research.db; this view is a thin, pure-stdlib reader + renderer. It
NEVER computes — so it needs no numpy and never holds a DB write. Degrades to an empty-state card
when the table is absent (clean checkout / laptop / before the first snapshot).

ISOLATED (the rotation_view.py pattern): a self-contained APIRouter in its own module, reusing the
shared `_shell` for chrome. Strictly additive — mounted by one line in v2_surfaces._ROUTER_SPECS,
touches nothing existing.
"""
from __future__ import annotations

import html
import sqlite3

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.web import infographics as ifx  # shared readability scaffold (S-C education)

RESEARCH_DB = "/opt/hermes/data/research.db"
HERMES_DB = "/opt/hermes/data/hermes.db"
router = APIRouter()


def _shell_fallback(title, body, active="", latest_date="", wide=False):
    return ("<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<body style='background:var(--bg-1);color:var(--ink);font-family:system-ui;"
            "max-width:1200px;margin:0 auto;padding:24px'>" + body + "</body>")


try:
    from src.web.dashboard import _shell
except Exception:                                   # pragma: no cover
    _shell = _shell_fallback


def _esc(s):
    return html.escape(str(s), quote=True)


def _pct(v, dp=1):
    if v is None:
        return '<span style="color:var(--ink-3)">·</span>'
    col = "#3fd486" if v > 0 else ("#ff6a7a" if v < 0 else "var(--ink-2)")
    return f'<span style="color:{col}">{v*100:+.{dp}f}%</span>'


def _sue(v):
    if v is None:
        return "—"
    col = "#3fd486" if v > 0 else ("#ff6a7a" if v < 0 else "var(--ink-2)")
    return f'<span style="color:{col}">{v:+.2f}</span>'


# (beat, sue_high, deliv_high) -> (label, colour, descriptive base-rate note from the 2026-07-05 study)
def _cell(beat, sue_hi, deliv_hi):
    if sue_hi and deliv_hi:
        return ("top-beat · deliv✓", "#b18cff", "hist +7.6%/60d (n=235)")
    if sue_hi:
        return ("top-beat", "#7fe6b0", "hist +3.7%/60d (n=200)")
    if beat and deliv_hi:
        return ("beat · deliv✓", "#4d9dff", "")
    if beat:
        return ("beat", "#5aa9ff", "")
    if deliv_hi:
        return ("miss · deliv✓", "#f6b73c", "")
    return ("in-line / miss", "#7e90a8", "")


_CSS = """
<style>
.rr{max-width:1180px}
.rr .lead{color:var(--ink-2);font-size:13px;line-height:1.6;max-width:900px;margin:2px 0 14px}
.rr .base{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 14px;
          margin:0 0 14px;font-size:12.5px;color:var(--ink);line-height:1.6}
.rr .base b{color:#b18cff}
.rr .kpis{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.rr .kpi{border:1px solid var(--line-2);border-radius:10px;padding:8px 13px;background:var(--bg-1)}
.rr .kpi .n{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums}
.rr .kpi .l{font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-2)}
.rr .tabs{margin:0 0 10px;font-size:12px}
.rr .tabs a{text-decoration:none;border:1px solid var(--line-2);border-radius:8px;padding:4px 10px;
            margin-right:6px;color:var(--ink-2)}
.rr .tabs a.on{background:var(--bg-2);color:var(--ink);border-color:var(--accent)}
.rr table{width:100%;border-collapse:collapse;font-size:12.5px}
.rr th,.rr td{padding:5px 9px;border-bottom:1px solid var(--bg-3);text-align:right;white-space:nowrap}
.rr th:first-child,.rr td:first-child,.rr th.l,.rr td.l{text-align:left}
.rr thead th{position:sticky;top:0;background:var(--bg-1);color:var(--ink-2);font-weight:600;
             font-size:10px;letter-spacing:.05em;text-transform:uppercase;z-index:1}
.rr td.sym{font-weight:700}
.rr .pill{display:inline-block;font-size:10px;font-weight:700;padding:1px 7px;border-radius:8px;
          background:var(--bg-2);border:1px solid var(--line-2)}
.rr .br{font-size:10px;color:var(--ink-3)}
.rr .dot{color:#d29922}.rr .dot.s{color:#3fd486}
.rr .note{color:var(--ink-2);font-size:11px;margin-top:16px;border-top:1px solid var(--line-2);
          padding-top:11px;line-height:1.6;max-width:900px}
.rr .up{border:1px solid var(--line-2);border-radius:10px;padding:10px 14px;margin:0 0 14px;background:var(--bg-1)}
.rr .up .uph{font-size:12px;font-weight:700;color:var(--ink);margin-bottom:6px}
.rr .up .uprow{display:flex;gap:8px;align-items:baseline;padding:4px 0;border-top:1px solid var(--bg-3);flex-wrap:wrap}
.rr .up .upd{font-size:11px;color:var(--ink-2);min-width:80px;font-weight:600;font-variant-numeric:tabular-nums}
.rr .up .ups{font-size:11px;text-decoration:none;color:var(--ink);border:1px solid var(--line-2);
             border-radius:6px;padding:1px 6px;background:var(--bg-2)}
.rr .up .more{color:var(--ink-3);font-size:11px}
/* published event briefs (D134 §4-E last mile, S159) — AI-drafted, desk-approved */
.rr .briefs{margin:12px 0;border:1px solid var(--line-2);border-radius:10px;
            background:var(--bg-2);padding:10px 13px}
.rr .briefs .bhdr{font-size:12px;color:var(--ink-2);margin-bottom:8px}
.rr .briefs .bhdr b{color:var(--ink)}
.rr .bcard{border-top:1px solid var(--line-2);padding:9px 0 3px}
.rr .bcard:first-of-type{border-top:0}
.rr .bcard .bhead{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:4px}
.rr .bcard .bsym{font-weight:700;color:var(--ink);text-decoration:none}
.rr .bcard .btitle{font-size:12px;color:var(--ink-2)}
.rr .bcard .bai{font-size:10px;border:1px solid var(--line-2);border-radius:10px;
                padding:1px 7px;color:var(--ink-2);background:var(--bg)}
.rr .bcard .bwhen{font-size:10px;color:var(--ink-3);margin-left:auto}
.rr .bcard p{margin:3px 0;font-size:13px;line-height:1.5}
</style>"""


def _ro():
    try:
        return sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return None


def _published_briefs(limit=3):
    """APPROVED auto-analyst briefs for this board (D134 §4-E last mile, S159).

    Reads hermes.db's `published_briefs` (brief_publisher owns it). Defensive on every
    path — a missing table / absent DB / any sqlite error renders NO band rather than a
    500: the board's own content must never depend on the L6 layer being present.
    ONLY published rows exist here; an unapproved draft lives in the Review Inbox and
    is structurally unreachable from this read (L6: only an approved brief publishes).
    """
    try:
        con = sqlite3.connect(f"file:{HERMES_DB}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return []
    try:
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name='published_briefs'").fetchone():
            return []
        return con.execute(
            "SELECT sym, title, text, label, approved_at FROM published_briefs "
            "WHERE retracted_at IS NULL ORDER BY published_at DESC, item_id DESC "
            "LIMIT ?", (int(limit),)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()


def _render_briefs(rows):
    """The AI-labeled band. Empty rows -> no band at all (never an empty shell)."""
    if not rows:
        return ""
    cards = []
    for sym, title, text, label, approved_at in rows:
        body = "".join(f"<p>{_esc(ln)}</p>" for ln in (text or "").split("\n") if ln.strip())
        link = (f'<a href="/dash/stock?sym={_esc(sym)}" class="bsym">{_esc(sym)}</a>'
                if sym else "")
        cards.append(
            f'<div class="bcard"><div class="bhead">{link}'
            f'<span class="btitle">{_esc(title)}</span>'
            f'<span class="bai" title="drafted by a cheap model from this board\'s own '
            f'numbers, then read and approved by the desk before it appeared here">'
            f'{_esc(label or "AI-drafted, human-reviewed")}</span>'
            f'<span class="bwhen">approved {_esc((approved_at or "")[:10])}</span>'
            f'</div>{body}</div>')
    return ('<div class="briefs"><div class="bhdr">📝 <b>Event briefs</b> '
            '<small>— written from the numbers on this board, then read and approved by '
            'the desk before publishing. Nothing appears here unreviewed; every figure '
            'traces to a row below.</small></div>' + "".join(cards) + '</div>')


def _tape_lag(meta):
    """Live weekday-lag of the snapshot's tape date (stamped by the nightly job, AUD-29).
    Computed at RENDER time, so a dead snapshot job also trips it — its stamp ages. The
    anchor is the last COMPLETED IST session (today only after ~20:00 IST on a weekday),
    so morning renders never false-flag. Twin of pead_surface._expected_session/_weekday_lag."""
    import datetime as _dt
    mx = (meta.get("tape_max_trade_date") or "")[:10]
    if not mx:
        return None, None                      # pre-AUD-29 snapshot: no stamp, no banner
    try:
        d = _dt.date.fromisoformat(mx)
    except ValueError:
        return mx, None
    ist = _dt.datetime.utcnow() + _dt.timedelta(hours=5, minutes=30)
    anchor = ist.date()
    if ist.weekday() >= 5 or ist.hour < 20:
        anchor -= _dt.timedelta(days=1)
    while anchor.weekday() >= 5:
        anchor -= _dt.timedelta(days=1)
    lag, cur = 0, d + _dt.timedelta(days=1)
    while cur <= anchor:
        if cur.weekday() < 5:
            lag += 1
        cur += _dt.timedelta(days=1)
    return mx, lag


def _car_fan_svg(meta, fresh_rows):
    """S83e: the event-time CAR fan — cohort mean paths + IQR band over the 14y settled
    population (from the snapshot's bounded `car_fan` meta), with this season's fresh
    reporters as dots at their +22d mark. Server-SVG, zero JS. The falsification line
    is printed ON the chart so the visual can never be mistaken for a strategy."""
    import json as _json
    try:
        fan = _json.loads(meta.get("car_fan") or "")
    except (ValueError, TypeError):
        return ""
    if not fan.get("confirmed"):
        return ""
    W, H, L, T = 860, 300, 46, 18
    pw, ph = W - L - 14, H - T - 46
    ys = []
    for c in fan.values():
        ys += c["p25"] + c["p75"] + c["mean"]
    lo, hi = min(ys + [-0.02]), max(ys + [0.05])
    span = (hi - lo) or 1.0

    def X(i):
        return L + pw * i / 59.0

    def Y(v):
        return T + ph * (1 - (v - lo) / span)

    def poly(c):
        up = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(c["p75"]))
        dn = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in reversed(list(enumerate(c["p25"]))))
        return up + " " + dn

    def line(c, col, wdt, dash=""):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(c["mean"]))
        return (f'<polyline points="{pts}" fill="none" stroke="{col}" '
                f'stroke-width="{wdt}"{dash}/>')

    conf, alle = fan["confirmed"], fan.get("all")
    parts = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:{W}px;height:auto" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Event-time abnormal-return fan after results">']
    for gv in (0.0, 0.05, 0.10):
        if lo <= gv <= hi:
            parts.append(f'<line x1="{L}" y1="{Y(gv):.1f}" x2="{W-14}" y2="{Y(gv):.1f}" '
                         f'stroke="#2a3242" stroke-width="1"/>'
                         f'<text x="{L-6}" y="{Y(gv)+4:.1f}" fill="#7e90a8" font-size="10" '
                         f'text-anchor="end">{gv*100:+.0f}%</text>')
    parts.append(f'<polygon points="{poly(conf)}" fill="rgba(177,140,255,.16)"/>')
    if alle:
        parts.append(line(alle, "#7e90a8", 1.4, ' stroke-dasharray="4 3"'))
    if fan.get("thin_deliv"):
        parts.append(line(fan["thin_deliv"], "#4d9dff", 1.6))
    if fan.get("miss"):
        parts.append(line(fan["miss"], "#ff6a7a", 1.4))
    parts.append(line(conf, "#b18cff", 2.6))
    dots = 0
    for r in fresh_rows:
        c22 = r.get("car22")
        if c22 is None or r.get("settled") or dots >= 40:
            continue
        parts.append(f'<circle cx="{X(21):.1f}" cy="{Y(c22):.1f}" r="2.6" '
                     f'fill="#f6b73c" opacity=".85"><title>{_esc(r["sym"])} +22d '
                     f'{c22*100:+.1f}%</title></circle>')
        dots += 1
    for i in (0, 21, 59):
        parts.append(f'<text x="{X(i):.1f}" y="{H-30}" fill="#7e90a8" font-size="10" '
                     f'text-anchor="middle">+{i+1}d</text>')
    parts.append(
        f'<text x="{L}" y="{H-12}" fill="#7e90a8" font-size="10.5">'
        f'▉ top-beat·deliv✓ mean+IQR (n={conf["n"]}) · ▬ thin-delivery · ▬ miss · ▬ all · '
        f'● fresh reporters at +22d — realized history, not a forecast. '
        f'The tradeable book on this drift FAILED (net return/vol 0.10 vs index 0.85, hedged −0.58).'
        f'</text></svg>')
    return ('<div class="up"><div class="uph">📈 What historically followed — abnormal return '
            'vs Nifty 500, day-by-day after results (14y settled population)</div>'
            + "".join(parts) + '</div>')


def _stale_banner(meta):
    tape_max, lag = _tape_lag(meta)
    if lag is None or lag < 1:
        return ""
    col = "#ff6a7a" if lag >= 3 else "#f6b73c"
    return (f'<div class="base" style="border-color:{col}"><b style="color:{col}">⚠ tape not '
            f'fresh:</b> delivery/price data runs to <b>{_esc(tape_max)}</b> ({lag} weekday(s) '
            f'behind — holiday or pipeline lag). Every number below is honest as of that date; '
            f'nothing here is presented as tonight&#39;s data.</div>')


def _empty(msg):
    body = (_CSS + '<div class="rr"><h2>Results-Reaction Scanner</h2>'
            f'<div class="base">{msg}</div>' + _render_upcoming(_upcoming(14)) + '</div>')
    return HTMLResponse(_shell("Results-Reaction Scanner", body, active="results-reactions", wide=True))


def _upcoming(days=14):
    """Next `days` of results board meetings from board_meetings (hermes.db, the D-01 calendar
    feed). Returns [] if the table/DB is absent — the war-room forward half degrades cleanly."""
    import datetime as _dt
    try:
        con = sqlite3.connect(f"file:{HERMES_DB}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return []
    try:
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name='board_meetings'").fetchone():
            return []
        lo = _dt.date.today().isoformat()
        hi = (_dt.date.today() + _dt.timedelta(days=days)).isoformat()
        return con.execute(
            "SELECT meeting_date, symbol, purpose FROM board_meetings "
            "WHERE is_results=1 AND meeting_date>=? AND meeting_date<=? "
            "ORDER BY meeting_date ASC, symbol ASC LIMIT 160", (lo, hi)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()


def _render_upcoming(rows):
    import datetime as _dt
    if not rows:
        return ('<div class="up"><div class="uph">📅 Upcoming results calendar</div>'
                '<div class="more">No board-meeting calendar loaded yet — the NSE feed populates '
                '<code>board_meetings</code> nightly (D-01).</div></div>')
    bydate = {}
    for md, sym, _pu in rows:
        bydate.setdefault(md, []).append(sym)
    # S83c heat-strip: weekday-aligned 2×5 grid, cell tint scaled by count — "which evening
    # is heavy" at a glance (the read that matters for same-evening MTTR during season).
    try:
        days, d = [], _dt.date.today()
        while len(days) < 10:
            if d.weekday() < 5:
                days.append(d)
            d += _dt.timedelta(days=1)
        peak = max((len(v) for v in bydate.values()), default=1) or 1
        cells = []
        for d in days:
            syms = bydate.get(d.isoformat(), [])
            n = len(syms)
            alpha = (0.05 + 0.30 * (n / peak)) if n else 0.0
            chips = " ".join(f'<a class="ups" href="/dash/stock?sym={_esc(s)}">{_esc(s)}</a>'
                             for s in syms[:6])
            more = f' <span class="more">+{n - 6}</span>' if n > 6 else ""
            cells.append(
                f'<td style="vertical-align:top;padding:6px 8px;border:1px solid var(--bg-3);'
                f'background:rgba(177,140,255,{alpha:.2f});min-width:108px;width:20%">'
                f'<div class="upd">{d.strftime("%a %d %b")}'
                f'{f" <b>{n}</b>" if n else ""}</div>'
                f'<div style="margin-top:3px;line-height:2.0">{chips}{more}</div></td>')
        grid = ('<table style="border-collapse:collapse;width:100%"><tr>'
                + "".join(cells[:5]) + '</tr><tr>' + "".join(cells[5:]) + '</tr></table>')
        return ('<div class="up"><div class="uph">📅 Upcoming results — next 14 days '
                '<span style="color:var(--ink-3);font-weight:400">(NSE board-meeting calendar · '
                'cell tint = how heavy that evening is)</span></div>' + grid + '</div>')
    except Exception:
        # degrade to the flat per-date list — never break the war room over a visual
        out = ['<div class="up"><div class="uph">📅 Upcoming results — next 14 days '
               '<span style="color:var(--ink-3);font-weight:400">(NSE board-meeting calendar · who reports next)</span>'
               '</div>']
        for md, syms in bydate.items():
            try:
                lbl = _dt.date.fromisoformat(md).strftime("%a %d %b")
            except ValueError:
                lbl = md
            chips = " ".join(f'<a class="ups" href="/dash/stock?sym={_esc(s)}">{_esc(s)}</a>'
                             for s in syms[:16])
            more = f' <span class="more">+{len(syms)-16} more</span>' if len(syms) > 16 else ""
            out.append(f'<div class="uprow"><span class="upd">{lbl}</span><span>{chips}{more}</span></div>')
        out.append('</div>')
        return "".join(out)


@router.get("/dash/results-reactions", response_class=HTMLResponse)
def results_reactions(view: str = Query("all")):
    con = _ro()
    if con is None:
        return _empty("The research database (<code>research.db</code>) is not present here — this "
                      "board renders on the VPS after the nightly snapshot.")
    try:
        has = con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                          "AND name='results_reactions'").fetchone()
        if not has:
            return _empty("No snapshot yet. Run <code>python -m explosive_moves.pead_surface "
                          "--snapshot</code> (research venv) to populate <code>results_reactions</code>.")
        meta = dict(con.execute("SELECT k, v FROM results_reactions_meta").fetchall())
        confirmed_only = (view == "confirmed")
        where = "WHERE sue_high=1 AND deliv_high=1" if confirmed_only else ""
        rows = con.execute(
            f"""SELECT t0, sym, ptype, sue, deliv_x, ear, car22, car60, beat, sue_high,
                       deliv_high, settled
                FROM results_reactions {where} ORDER BY t0 DESC, deliv_x DESC LIMIT 500""").fetchall()
        n_all = con.execute("SELECT COUNT(*) FROM results_reactions").fetchone()[0]
        n_conf = con.execute("SELECT COUNT(*) FROM results_reactions "
                             "WHERE sue_high=1 AND deliv_high=1").fetchone()[0]
        n_settled = con.execute("SELECT COUNT(*) FROM results_reactions WHERE settled=1").fetchone()[0]
    finally:
        con.close()

    tr = []
    for (t0, sym, ptype, sue, dx, ear, c22, c60, beat, shi, dhi, settled) in rows:
        lbl, col, br = _cell(beat, shi, dhi)
        dot = '<span class="dot s" title="settled: full 60d elapsed">●</span>' if settled else \
              '<span class="dot" title="fresh — drift still accruing">◔</span>'
        durl = f"/dash/stock?sym={_esc(sym)}"
        tr.append(
            f'<tr><td class="l">{_esc(t0)}</td>'
            f'<td class="l sym"><a href="{durl}" style="color:var(--ink);text-decoration:none">{_esc(sym)}</a></td>'
            f'<td class="l" style="color:var(--ink-2)">{_esc(ptype)}</td>'
            f'<td>{_sue(sue)}</td>'
            f'<td>{dx:.2f}×</td>'
            f'<td class="l"><span class="pill" style="color:{col}">{lbl}</span> '
            f'<span class="br">{br}</span></td>'
            f'<td>{_pct(ear)}</td>'
            f'<td>{_pct(c22)}</td>'
            f'<td>{_pct(c60)}</td>'
            f'<td>{dot}</td></tr>')

    gen = _esc(meta.get("generated_at", "—"))
    sue_hi = meta.get("sue_hi", "?"); dlv_hi = meta.get("dlv_hi", "?")
    body = [_CSS, ifx.readability_css(), '<div class="rr">',
            '<h2>Results-Reaction Scanner</h2>',
            ifx.bottom_line(
                'Who just <b>reported earnings</b>, whether the surprise was backed by <b>real '
                'delivered buying</b> (not intraday churn), and what actually happened to the '
                'price in the weeks after. Historically, big beats confirmed by heavy delivery '
                'drifted higher; unconfirmed ones mostly didn\'t. <b>Realized history, not a '
                'forecast or a buy list.</b>'),
            ifx.how_to_read_link(),
            '<div class="lead">Who just reported, whether the earnings surprise was <b>confirmed by '
            'delivered value</b> (the strong hand showing up, not intraday churn), and — once ~60 '
            'sessions elapse — the realized abnormal drift vs Nifty&nbsp;500. Descriptive realized '
            'history, <b>not a forecast or a buy list</b>. SUE = Net-Profit seasonal surprise (no '
            'analysts); Deliv× = reaction-window delivered value vs its own trailing median.</div>',
            _stale_banner(meta),
            f'<div class="base">📎 <b>Descriptive base rate</b> (14y settled events, 2026-07-05 study): '
            f'a top-quintile surprise <b>confirmed by top-tercile delivery drifted +7.6% over 60 '
            f'sessions</b> (n=235); the same surprise on thin delivery only +3.7%; bad news did not '
            f'drift. Cuts this run: SUE&nbsp;p80={_esc(sue_hi)}, Deliv&nbsp;p67={_esc(dlv_hi)}. These '
            f'are historical averages attached to a cell — <b>never a prediction for any single name</b>. '
            f'The tradeable version was tested and failed (net return/vol 0.10 vs index 0.85); this board '
            f'is the honest descriptive residue.</div>',
            '<div class="kpis">'
            f'<div class="kpi"><div class="n">{n_all}</div><div class="l">recent events</div></div>'
            f'<div class="kpi"><div class="n" style="color:#b18cff">{n_conf}</div>'
            f'<div class="l">deliv-confirmed top-beats</div></div>'
            f'<div class="kpi"><div class="n">{n_settled}</div><div class="l">settled (60d elapsed)</div></div>'
            '</div>',
            _render_upcoming(_upcoming(14)),
            _render_briefs(_published_briefs(3)),
            _car_fan_svg(meta, [{"sym": r[1], "car22": r[6], "settled": r[11]} for r in rows]),
            '<div class="tabs">'
            f'<a href="/dash/results-reactions" class="{"on" if not confirmed_only else ""}">All recent</a>'
            f'<a href="/dash/results-reactions?view=confirmed" class="{"on" if confirmed_only else ""}">'
            'Delivery-confirmed top-beats only</a></div>',
            '<table><thead><tr>'
            '<th class="l">Results date</th><th class="l">Stock</th><th class="l">Q/A</th>'
            '<th>SUE</th><th>Deliv×</th><th class="l">Cell · base-rate</th>'
            '<th title="reaction: 2-session abnormal move at the announcement">React</th>'
            '<th title="abnormal vs Nifty 500, +22 sessions">+22d</th>'
            '<th title="abnormal vs Nifty 500, +60 sessions">+60d</th><th>·</th>'
            '</tr></thead><tbody>',
            "".join(tr) or '<tr><td colspan="10" class="l" style="color:var(--ink-2)">no rows</td></tr>',
            '</tbody></table>',
            f'<div class="note">Snapshot generated {gen} from the nightly '
            f'<code>results_reactions</code> table (research.db). ● settled (full 60d) · ◔ fresh, drift '
            f'still accruing. Rows capped at 500, most recent first. Delivery is the India-specific '
            f'confirmation the US PEAD literature lacks; it is descriptive only — the book built on it '
            f'is in the failure ledger. T2T/BE-series rows never enter this board — the loader reads '
            f'the EQ series only, so Deliv× cannot be trade-to-trade-polluted (delivery in a T2T '
            f'series is definitionally 100%).</div>',
            '</div>']
    return HTMLResponse(_shell("Results-Reaction Scanner", "".join(body), active="results-reactions",
                               latest_date=meta.get("generated_at", ""), wide=True))
