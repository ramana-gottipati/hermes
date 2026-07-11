"""/dash/sector-momentum — sector → constituent RSI-of-RS drill + momentum BREADTH
(roadmap #12 + #9).

"Which stocks are driving this sector's turn, and is the move broad or narrow?" For a
chosen sector it lists its constituent stocks with RSI-of-RS, RS rank and rotation phase
(each linking to its momentum pane), plus a BREADTH read (% of constituents with RSI-of-RS
above 50 / above 70 / below 30). Answers what the sector-level RRG/clock can't: the internals.

ISOLATED + ADDITIVE (momentum_pane / divergence_board / cycle_clock pattern): self-contained
router, reads ONLY the already-stored stock_signals snapshot (primary_sector, rsi_of_rs,
rs_rank, rs_phase) — no new compute/storage (space rule). Defensive empty-state. Descriptive.
"""
from __future__ import annotations

import html
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

_PHCOL = {"RECOVERY": "#7fdcae", "TAILWIND": "var(--up)", "ROLLING-OVER": "var(--warn)",
          "HEADWIND": "var(--down)", "NEUTRAL": "var(--ink-3)"}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _short(nm: str) -> str:
    return str(nm).replace("Nifty ", "").replace(" Index", "")


def _rsi_date(conn):
    try:
        r = conn.execute("SELECT MAX(trade_date) d FROM stock_signals "
                         "WHERE rsi_of_rs IS NOT NULL").fetchone()
        return r[0] if r else None
    except Exception:  # noqa: BLE001
        return None


def _rsi_cell(v) -> str:
    if v is None:
        return '<span style="color:var(--ink-3)">—</span>'
    v = float(v)
    col = ("var(--warn)" if v >= 70 else "var(--accent)" if v <= 30
           else "var(--up)" if v > 50 else "var(--down)")
    return f'<span style="color:{col};font-weight:600">{v:.0f}</span>'


def _constituents(sector: str, conn):
    d = _rsi_date(conn)
    if not d:
        return None, {}
    try:
        rows = [dict(symbol=r[0], rank=r[1], rsi=r[2], phase=r[3]) for r in conn.execute(
            "SELECT symbol, rs_rank, rsi_of_rs, rs_phase FROM stock_signals "
            "WHERE primary_sector=? AND trade_date=? AND rsi_of_rs IS NOT NULL "
            "ORDER BY rsi_of_rs DESC", (sector, d)).fetchall()]
    except Exception:  # noqa: BLE001
        return None, {}
    if not rows:
        return [], {}
    n = len(rows)
    rsis = [float(r["rsi"]) for r in rows]
    breadth = {
        "n": n,
        "gt50": round(sum(1 for x in rsis if x > 50) / n * 100),
        "gt70": round(sum(1 for x in rsis if x >= 70) / n * 100),
        "lt30": round(sum(1 for x in rsis if x <= 30) / n * 100),
        "as_of": d,
    }
    return rows, breadth


def _bar(pct: int, tok: str) -> str:
    return (f'<span style="display:inline-block;width:120px;height:8px;border-radius:5px;'
            f'background:var(--bg-2);vertical-align:middle;overflow:hidden">'
            f'<span style="display:block;height:100%;width:{max(0, min(100, pct))}%;'
            f'background:{tok}"></span></span>')


def drill_html(sector: str, conn) -> str:
    sector = (sector or "").strip()
    rows, b = _constituents(sector, conn)
    if not rows:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">'
                f'{_esc(_short(sector))} — constituent momentum</div>'
                '<div class="sub" style="margin:0">No constituents with RSI-of-RS on record '
                'for this sector (needs the nightly stock RS compute).</div></div>')
    tr = []
    for r in rows:
        ph = (r["phase"] or "NEUTRAL").upper()
        pcol = _PHCOL.get(ph, "var(--ink-3)")
        tr.append(
            f'<tr><td class="l"><a class="row" href="/dash/momentum?sym={quote_plus(str(r["symbol"]))}" '
            f'style="color:var(--ink);font-weight:700">{_esc(r["symbol"])}</a></td>'
            f'<td style="text-align:right">{_rsi_cell(r["rsi"])}</td>'
            f'<td style="text-align:right">{r["rank"] if r["rank"] is not None else "—"}</td>'
            f'<td class="l" style="color:{pcol}">{_esc(_short(str(r["phase"] or "—")))}</td></tr>')
    return (
        '<div class="card" style="margin-bottom:12px">'
        f'<div class="h2" style="margin:0 0 2px">{_esc(_short(sector))} — constituent momentum</div>'
        f'<div class="sub" style="margin:0 0 8px">{b["n"]} constituents · as of {_esc(b["as_of"])}. '
        'RSI-of-RS breadth = is the move broad or narrow? <b>Descriptive.</b></div>'
        f'<div style="font-size:12px;line-height:2.2">'
        f'<b style="color:var(--up)">{b["gt50"]}%</b> above RSI 50 {_bar(b["gt50"], "var(--up)")} '
        f'&nbsp; <b style="color:var(--warn)">{b["gt70"]}%</b> hot (≥70) '
        f'&nbsp; <b style="color:var(--accent)">{b["lt30"]}%</b> washed-out (≤30)'
        '</div></div>'
        '<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt" '
        'style="width:100%;border-collapse:collapse;font-size:12px">'
        '<thead><tr><th class="l">Symbol</th><th style="text-align:right">RSI-of-RS</th>'
        '<th style="text-align:right">RS rank</th><th class="l">Phase</th></tr></thead>'
        f'<tbody>{"".join(tr)}</tbody></table></div>')


def _picker(conn) -> str:
    d = _rsi_date(conn)
    rows = []
    if d:
        try:
            rows = conn.execute(
                "SELECT primary_sector, COUNT(*) c FROM stock_signals "
                "WHERE trade_date=? AND rsi_of_rs IS NOT NULL AND primary_sector IS NOT NULL "
                "GROUP BY primary_sector ORDER BY primary_sector", (d,)).fetchall()
        except Exception:  # noqa: BLE001
            rows = []
    if not rows:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">Sector momentum</div>'
                '<div class="sub" style="margin:0">No sector constituents with RSI-of-RS yet.</div></div>')
    chips = "".join(
        f'<a class="pill" style="margin:3px;color:var(--ink)" '
        f'href="/dash/sector-momentum?idx={quote_plus(str(s))}">'
        f'{_esc(_short(s))} <span style="opacity:.55">{c}</span></a>' for s, c in rows)
    return ('<div class="card"><div class="h2" style="margin:0 0 2px">Sector momentum drill</div>'
            '<div class="sub" style="margin:0 0 6px">Pick a sector to see which constituents drive '
            'its momentum + the RSI-of-RS breadth.</div>'
            f'<div style="line-height:2">{chips}</div></div>')


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)


@router.get("/dash/sector-momentum", response_class=HTMLResponse)
def sector_momentum_page(idx: str = Query("")):
    idx = (idx or "").strip()
    with _open() as conn:
        body = (drill_html(idx, conn) if idx else _picker(conn)) if conn is not None else _picker(None)
    try:
        from src.web.dashboard import _shell
        title = f"{_short(idx)} — sector momentum" if idx else "Sector momentum"
        return HTMLResponse(_shell(title, body, active="sector-momentum", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _selftest() -> None:
    assert _rsi_cell(72).find("var(--warn)") > 0
    assert _rsi_cell(25).find("var(--accent)") > 0
    assert "%" in _bar(60, "var(--up)")
    print("sector_momentum selftest: OK")


if __name__ == "__main__":
    _selftest()
