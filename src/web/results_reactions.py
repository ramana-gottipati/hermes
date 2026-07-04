"""/dash/results-reactions — the Results-Reaction Scanner (descriptive).

The war-room board for results season: who just reported, what was the Net-Profit surprise (SUE, no
analysts), did the strong hand confirm it on the tape (delivered value), and — for older events — the
realized abnormal drift. It is the DESCRIPTIVE product of the 2026-07-05 PEAD study, whose tradeable
book was falsified (ledger § Experiment 2026-07-05: net Sharpe 0.10 vs bench 0.85). So this is a
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

RESEARCH_DB = "/opt/hermes/data/research.db"
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
</style>"""


def _ro():
    try:
        return sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return None


def _empty(msg):
    body = (_CSS + '<div class="rr"><h2>Results-Reaction Scanner</h2>'
            f'<div class="base">{msg}</div></div>')
    return HTMLResponse(_shell("Results-Reaction Scanner", body, active="markets", wide=True))


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
        durl = f"/dash/stock?symbol={_esc(sym)}"
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
    body = [_CSS, '<div class="rr">',
            '<h2>Results-Reaction Scanner</h2>',
            '<div class="lead">Who just reported, whether the earnings surprise was <b>confirmed by '
            'delivered value</b> (the strong hand showing up, not intraday churn), and — once ~60 '
            'sessions elapse — the realized abnormal drift vs Nifty&nbsp;500. Descriptive realized '
            'history, <b>not a forecast or a buy list</b>. SUE = Net-Profit seasonal surprise (no '
            'analysts); Deliv× = reaction-window delivered value vs its own trailing median.</div>',
            f'<div class="base">📎 <b>Descriptive base rate</b> (14y settled events, 2026-07-05 study): '
            f'a top-quintile surprise <b>confirmed by top-tercile delivery drifted +7.6% over 60 '
            f'sessions</b> (n=235); the same surprise on thin delivery only +3.7%; bad news did not '
            f'drift. Cuts this run: SUE&nbsp;p80={_esc(sue_hi)}, Deliv&nbsp;p67={_esc(dlv_hi)}. These '
            f'are historical averages attached to a cell — <b>never a prediction for any single name</b>. '
            f'The tradeable version was tested and failed (net Sharpe 0.10 vs index 0.85); this board '
            f'is the honest descriptive residue.</div>',
            '<div class="kpis">'
            f'<div class="kpi"><div class="n">{n_all}</div><div class="l">recent events</div></div>'
            f'<div class="kpi"><div class="n" style="color:#b18cff">{n_conf}</div>'
            f'<div class="l">deliv-confirmed top-beats</div></div>'
            f'<div class="kpi"><div class="n">{n_settled}</div><div class="l">settled (60d elapsed)</div></div>'
            '</div>',
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
            f'is in the failure ledger.</div>',
            '</div>']
    return HTMLResponse(_shell("Results-Reaction Scanner", "".join(body), active="markets",
                               latest_date=meta.get("generated_at", ""), wide=True))
