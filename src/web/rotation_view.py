"""/dash/rotation — the four-phase RS weather rotation (stocks), the read surface
for the RS-rotation build (session 25; design in docs/rs-rotation-design.md).

ISOLATED on purpose (the rrg_view.py pattern): a self-contained APIRouter in its
OWN module, mounted via one line in main.py WITHOUT editing the parallel-held
dashboard.py / cockpit.py. It reuses the shared page shell (`_shell`) for chrome +
CSS consistency, and the rotation reads in stock_rs (phase_members / phase_shortlist
/ phase_movers). Pure read, rule-based, ZERO LLM. STRICTLY ADDITIVE — nothing
existing is removed or rerouted.

The 2×2 (positioned like the RRG axes):
    🌅 Recovery   |  🌤 Tailwind        (RS turning up | strong & strengthening)
    🌧 Headwind   |  ⛅ Rolling-over     (weak & weakening | a leader cracking)
Clockwise lifecycle: Recovery → Tailwind → Rolling-over → Headwind → Recovery.

Empty-state (no rs_phase populated yet) tells the operator to run the compute —
so the page never 500s before the backfill lands.
"""

from __future__ import annotations

import html
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.automation import stock_rs
from src.core.db import get_conn
from src.web.dashboard import _shell   # chrome + CSS (import-safe; see rrg_view)

try:
    from src.web.dashboard import REAL_SECTORS as _REAL_SECTORS
except Exception:
    _REAL_SECTORS = None

router = APIRouter()

# Phase → (label, accent, dim-bg). ONE colour contract (pitch D-PITCH-2): the rotation
# weather reads in the site's value language — green=strength/up (--up #3fd486),
# red=weakness/down (--down #ff6a7a), amber=caution (--warn #f6b73c). Strengthening half
# is the green family (Recovery = a lighter, not-yet-confirmed tint of --up → Tailwind =
# full-strength --up); weakening half runs amber (a leader cracking) → red (weak &
# weakening). Blue (--accent #4d9dff) stays the neutral accent site-wide and is
# deliberately NOT used here so it never re-reads as "bull". Descriptive lifecycle, not a
# buy/sell signal. NOTE: cockpit._WEATHER / rrg_view.QCOLOR still carry the legacy palette
# (other lanes) — flagged for the same D-PITCH-2 remap so the badges/RRG re-converge.
PHASE = {
    "RECOVERY":     ("🌅 Recovery",     "#7fe6b0", "#10271d"),
    "TAILWIND":     ("🌤 Tailwind",     "#3fd486", "#102a1d"),
    "ROLLING-OVER": ("⛅ Rolling over",  "#f6b73c", "#2e2611"),
    "HEADWIND":     ("🌧 Headwind",     "#ff6a7a", "#2e161b"),
    "NEUTRAL":      ("☁ Neutral",       "#7e90a8", "#1a232f"),
}
# grid order = the RRG quadrant layout (top-left, top-right, bottom-left, bottom-right)
GRID = ("RECOVERY", "TAILWIND", "HEADWIND", "ROLLING-OVER")
TABLE_PHASES = ("RECOVERY", "TAILWIND", "ROLLING-OVER", "HEADWIND")


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _pct(v, dp: int = 1) -> str:
    if v is None:
        return '<span style="color:#6e7681">—</span>'
    col = "#3fd486" if v > 0 else ("#ff6a7a" if v < 0 else "#8b949e")
    return f'<span style="color:{col}">{v:+.{dp}f}</span>'


def _marks(r: dict) -> str:
    """The §4b leverage reads as compact pills."""
    out = []
    if r.get("rs_leads_price"):
        out.append('<span class="rmk" style="color:#4d9dff" title="RS at a new 52w high while price still off its high">RS▲&gt;price</span>')
    if r.get("rs_accel_up"):
        out.append('<span class="rmk" style="color:#3fd486" title="term structure stacked up (1m&gt;3m&gt;6m&gt;12m)">⚡accel</span>')
    if r.get("rs_accel_down"):
        out.append('<span class="rmk" style="color:#ff6a7a" title="term structure stacked down">⚡down</span>')
    if r.get("delivery_confirmed"):
        out.append('<span class="rmk" style="color:#b18cff" title="DVPT power-day / accumulation coincides — turn is delivery-confirmed">✅deliv</span>')
    if r.get("abs_trend_up"):
        out.append('<span class="rmk" style="color:#3fd486" title="absolute price trend up (3m drift &gt; 0) — dual-momentum">abs✔</span>')
    if r.get("rsi_overbought"):
        out.append('<span class="rmk" style="color:#f6b73c" title="RSI-of-RS &gt; 70 — relative move extended, do not chase">RSI hot</span>')
    if r.get("rsi_oversold"):
        out.append('<span class="rmk" style="color:#4d9dff" title="RSI-of-RS &lt; 30 — washed-out, earliest turn tell">RSI cold</span>')
    return " ".join(out)


_CSS = """
<style>
.rwrap{max-width:1280px}
.rgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0 16px}
.rq{border:1px solid #30363d;border-radius:12px;padding:12px 14px;background:#0d1117}
.rq h3{margin:0 0 2px;font-size:15px}
.rq .rq-sub{color:#8b949e;font-size:11px;margin-bottom:8px}
.rq .rq-n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums}
.rq table{width:100%;border-collapse:collapse;font-size:12px}
.rq td{padding:2px 4px;border-bottom:1px solid #161b22;white-space:nowrap}
.rq .sym{font-weight:700}
.rmk{display:inline-block;font-size:9px;font-weight:700;padding:1px 5px;border-radius:7px;
     background:#161b22;border:1px solid #30363d;margin-right:3px}
.rbanner{border:1px solid #30363d;border-radius:10px;padding:8px 12px;margin:6px 0 4px;
         background:#161b22;font-size:13px;color:#c9d1d9}
.rmovers{margin:4px 0 14px;font-size:12px;color:#c9d1d9}
.rmovers .mv{display:inline-block;border:1px solid #30363d;border-radius:8px;
             padding:2px 8px;margin:3px 6px 3px 0;background:#0d1117}
.rdt{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
.rdt th,.rdt td{padding:4px 7px;border-bottom:1px solid #21262d;text-align:right;white-space:nowrap}
.rdt th:first-child,.rdt td:first-child,.rdt th.l,.rdt td.l{text-align:left}
.rdt thead th{position:sticky;top:0;background:#0d1117;color:#8b949e;font-weight:600;z-index:1}
.rpill{display:inline-block;text-decoration:none;font-size:12px;font-weight:600;
       padding:4px 11px;border-radius:9px;border:1px solid #30363d;margin-right:6px;color:#c9d1d9}
a.row,a.rpill{text-decoration:none}
</style>
"""


def _empty() -> str:
    return (
        '<h2>RS rotation</h2>'
        '<div class="card"><div class="sub">No rotation data yet.</div>'
        '<p style="color:#c9d1d9;line-height:1.5">This view reads the per-stock '
        '<code>rs_phase</code> (the weather rotation label) computed by '
        '<code>stock_rs</code>. Once stock signals are computed it populates:</p>'
        '<pre style="background:#0d1117;border:1px solid #30363d;border-radius:6px;'
        'padding:10px;overflow:auto">python -m src.automation.index_signals\n'
        'python -m src.automation.stock_rs</pre></div>')


def _banner(conn) -> str:
    """§4b-7 leadership breadth — sector phase mix (curated to REAL_SECTORS)."""
    irow = conn.execute("SELECT MAX(trade_date) d FROM index_signals").fetchone()
    idd = irow["d"] if irow else None
    if not idd:
        return ""
    q = ("SELECT rs_phase, COUNT(*) n FROM index_signals "
         "WHERE trade_date=? AND broad_benchmark IS NOT NULL AND rs_phase IS NOT NULL")
    params = [idd]
    if _REAL_SECTORS:
        ph = ",".join("?" * len(_REAL_SECTORS))
        q += f" AND index_name IN ({ph})"
        params += list(_REAL_SECTORS)
    q += " GROUP BY rs_phase"
    counts = {r["rs_phase"]: r["n"] for r in conn.execute(q, params).fetchall()}
    total = sum(counts.values())
    if not total:
        return ""
    lead = counts.get("TAILWIND", 0)
    rec = counts.get("RECOVERY", 0)
    parts = []
    for k in ("TAILWIND", "RECOVERY", "ROLLING-OVER", "HEADWIND", "NEUTRAL"):
        if counts.get(k):
            lbl, col, _ = PHASE[k]
            parts.append(f'<b style="color:{col}">{counts[k]} {lbl}</b>')
    share = lead / total if total else 0
    health = ("broad leadership" if share >= 0.35 else
              ("narrow leadership — fragile" if share <= 0.15 else "mixed leadership"))
    tilt = "risk-on rotation" if rec >= lead and rec > 0 else "leaders in control"
    return (f'<div class="rbanner">Sector weather ({total} sectors): '
            + " · ".join(parts) + f' &nbsp;—&nbsp; <b>{health}</b> · {tilt}.</div>')


def _movers(conn) -> str:
    rows = stock_rs.phase_movers(limit=40)
    if not rows:
        return ('<div class="rmovers"><span class="sub">No phase transitions yet '
                '(needs ≥2 days of rotation history — accrues nightly).</span></div>')
    # lead with the actionable crossings
    def _key(r):
        pair = (r.get("prev_phase"), r.get("rs_phase"))
        if pair == ("HEADWIND", "RECOVERY"):
            return 0
        if pair == ("TAILWIND", "ROLLING-OVER"):
            return 1
        return 2
    rows.sort(key=_key)
    chips = []
    for r in rows[:24]:
        to = r.get("rs_phase")
        col = PHASE.get(to, PHASE["NEUTRAL"])[1]
        frm = PHASE.get(r.get("prev_phase"), ("?", "#8b949e", ""))[0].split(" ")[0]
        tol = PHASE.get(to, ("?", "", ""))[0].split(" ")[0]
        chips.append(
            f'<span class="mv"><a class="row" href="/dash/stock?sym={quote_plus(r["symbol"])}" '
            f'style="color:#e6edf3">{_esc(r["symbol"])}</a> '
            f'<span style="color:#8b949e">{frm}→</span><span style="color:{col}">{tol}</span></span>')
    return ('<div class="rmovers"><b>✨ Just turned</b> '
            '<span class="sub">phase changed today (base-turns &amp; cracks first)</span><br>'
            + "".join(chips) + '</div>')


def _cell(phase: str) -> str:
    lbl, col, bg = PHASE[phase]
    rows = stock_rs.phase_shortlist(phase, limit=200)
    sub = {"RECOVERY": "confirmed base-turn (stock + sector)",
           "TAILWIND": "strong-in-strong (stock + sector)",
           "ROLLING-OVER": "a leader cracking (stock + sector)",
           "HEADWIND": "weak-in-weak (stock + sector)"}[phase]
    body = []
    for r in rows[:7]:
        body.append(
            f'<tr><td><a class="row sym" href="/dash/stock?sym={quote_plus(r["symbol"])}" '
            f'style="color:#e6edf3">{_esc(r["symbol"])}</a></td>'
            f'<td style="color:#8b949e">{_esc((r.get("primary_sector") or "").replace("Nifty ",""))}</td>'
            f'<td style="text-align:right">{r["rs_rank"] if r.get("rs_rank") is not None else "—"}</td>'
            f'<td style="text-align:right">{_marks(r)}</td></tr>')
    table = (f'<table><tbody>{"".join(body)}</tbody></table>' if body
             else '<div class="sub" style="margin:6px 0">None right now.</div>')
    more = (f'<div style="margin-top:6px"><a class="row" style="color:#4d9dff" '
            f'href="/dash/rotation?phase={quote_plus(phase)}">See all {len(rows)} →</a></div>'
            if len(rows) > 7 else "")
    return (f'<div class="rq" style="border-color:{col}33">'
            f'<h3 style="color:{col}">{lbl} <span class="rq-n" style="color:{col}">{len(rows)}</span></h3>'
            f'<div class="rq-sub">{sub}</div>{table}{more}</div>')


def _table(phase: str) -> str:
    rows = stock_rs.phase_members(phase, limit=300)
    lbl = PHASE.get(phase, PHASE["NEUTRAL"])[0]
    if not rows:
        return f'<h3 style="margin-top:14px">{lbl} — all members</h3><div class="sub">None right now.</div>'
    head = ('<thead><tr><th class="l">Symbol</th><th>RS rank</th><th class="l">Sector</th>'
            '<th>Sector</th><th>1m</th><th>3m</th><th>6m</th><th>12m</th><th>18m</th><th>24m</th>'
            '<th>RSI-RS</th><th class="l">Signals</th><th>CMP</th></tr></thead>')
    tr = []
    for r in rows:
        sphase = r.get("sector_phase")
        scol = PHASE.get(sphase, PHASE["NEUTRAL"])[1] if sphase else "#6e7681"
        slbl = PHASE.get(sphase, ("—", "", ""))[0].split(" ")[-1] if sphase else "—"
        rsi = r.get("rsi")
        # precompute cell text (avoid nested same-quote f-strings — Python 3.11)
        rank_txt = r["rs_rank"] if r.get("rs_rank") is not None else "—"
        sec_txt = _esc((r.get("primary_sector") or "").replace("Nifty ", ""))
        rsi_txt = "—" if rsi is None else f"{rsi:.0f}"
        cmp_txt = "—" if r.get("close") is None else f"{r['close']:.1f}"
        sym = _esc(r["symbol"])
        link = quote_plus(r["symbol"])
        tr.append(
            f'<tr><td class="l"><a class="row sym" href="/dash/stock?sym={link}" '
            f'style="color:#e6edf3;font-weight:700">{sym}</a></td>'
            f'<td>{rank_txt}</td>'
            f'<td class="l" style="color:#8b949e">{sec_txt}</td>'
            f'<td style="color:{scol}">{_esc(slbl)}</td>'
            f'<td>{_pct(r.get("b1"))}</td><td>{_pct(r.get("b3"))}</td><td>{_pct(r.get("b6"))}</td>'
            f'<td>{_pct(r.get("b12"))}</td><td>{_pct(r.get("b18"))}</td><td>{_pct(r.get("b24"))}</td>'
            f'<td>{rsi_txt}</td>'
            f'<td class="l">{_marks(r)}</td>'
            f'<td>{cmp_txt}</td></tr>')
    return (f'<h3 style="margin-top:16px">{lbl} — all members '
            f'<span class="sub" style="margin:0">{len(rows)} · full RS term structure</span></h3>'
            f'<div style="overflow-x:auto"><table class="rdt">{head}<tbody>{"".join(tr)}</tbody></table></div>')


def _pills(active: str) -> str:
    out = []
    for p in TABLE_PHASES:
        lbl, col, _ = PHASE[p]
        on = f"background:{col}22;border-color:{col};color:{col};" if p == active else ""
        out.append(f'<a class="rpill" style="{on}" href="/dash/rotation?phase={quote_plus(p)}">{lbl}</a>')
    return '<div style="margin:8px 0">' + "".join(out) + '</div>'


@router.get("/dash/rotation", response_class=HTMLResponse)
def rotation_page(phase: str = Query("RECOVERY", max_length=20)) -> HTMLResponse:
    phase = phase.upper()
    if phase not in PHASE:
        phase = "RECOVERY"
    with get_conn() as conn:
        # is rs_phase populated for the latest date? (empty-state guard before the
        # backfill). Scope to the latest trade_date (indexed) — a bare
        # "rs_phase IS NOT NULL" mis-picks an index → ~3s over 5.9M rows.
        try:
            sd = conn.execute("SELECT MAX(trade_date) d FROM stock_signals").fetchone()
            has = (conn.execute(
                "SELECT 1 FROM stock_signals WHERE trade_date=? AND rs_phase IS NOT NULL LIMIT 1",
                (sd["d"],)).fetchone() if (sd and sd["d"]) else None)
        except Exception:
            has = None
        if not has:
            return HTMLResponse(_shell("RS rotation · patearn", _CSS + _empty(), active="markets", wide=True))
        banner = _banner(conn)
    grid = '<div class="rgrid">' + "".join(_cell(p) for p in GRID) + '</div>'
    movers = ""
    with get_conn() as conn:
        movers = _movers(conn)
    head = ('<h2 style="margin-bottom:2px">RS rotation '
            '<span class="sub" style="margin:0">the four-phase weather rotation · stock × sector</span></h2>'
            '<div class="sub" style="margin-top:2px">Clockwise: 🌅 Recovery → 🌤 Tailwind → '
            '⛅ Rolling-over → 🌧 Headwind. Grid = the strict diagonal (stock <b>and</b> its sector '
            'share the phase). Table below = every member of the selected phase, full RS term structure.</div>')
    body = ('<div class="rwrap">' + head + banner + grid + movers
            + _pills(phase) + _table(phase) + '</div>')
    return HTMLResponse(_shell("RS rotation · patearn", _CSS + body, active="markets", wide=True))
