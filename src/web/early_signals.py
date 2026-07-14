"""/dash/early-signals — the daily "what's turning up today" feed (roadmap #11).

The earliest actionable read, aggregated across the market from ALREADY-computed signals:
  • stocks that JUST flipped up into Recovery / Tailwind (fresh phase turns, from
    stock_rs.phase_movers — the prev→now transition),
  • sectors flashing a fresh BULLISH RS/RSI divergence (rs_extras flags, via divergence_board).
Each links to its momentum pane. Descriptive early-warning — never a buy list.

ISOLATED + ADDITIVE (momentum_pane / divergence_board / cycle_clock pattern): self-contained
router, reads only precomputed tables, no new compute/storage (space rule). Defensive.
"""
from __future__ import annotations

import html
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web import infographics as ifx  # shared readability scaffold (S-C education)

router = APIRouter()

_PHCOL = {"RECOVERY": "#7fdcae", "TAILWIND": "var(--up)", "ROLLING-OVER": "var(--warn)",
          "HEADWIND": "var(--down)", "NEUTRAL": "var(--ink-3)", "LAGGING": "var(--down)",
          "IMPROVING": "var(--accent)"}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _short(nm: str) -> str:
    return str(nm).replace("Nifty ", "").replace(" Index", "")


def _fetch(conn):
    fresh, confirm = [], []
    try:
        from src.automation.stock_rs import phase_movers
        for r in (phase_movers(90) or []):
            now = (r.get("rs_phase") or "").upper()
            prev = (r.get("prev_phase") or "").upper()
            rec = {"sym": r.get("symbol"), "prev": prev, "now": now,
                   "rsi": r.get("rsi") if r.get("rsi") is not None else r.get("rsi_of_rs"),
                   "rank": r.get("rs_rank")}
            if now in ("RECOVERY", "TAILWIND") and prev not in ("RECOVERY", "TAILWIND"):
                fresh.append(rec)
            elif prev == "RECOVERY" and now == "TAILWIND":
                confirm.append(rec)
    except Exception:  # noqa: BLE001
        pass
    bull = []
    try:
        from src.web.divergence_board import _scan
        bull, _bear = _scan(conn)
    except Exception:  # noqa: BLE001
        pass
    return fresh, confirm, bull


def _rsi_txt(v) -> str:
    if v is None:
        return ""
    col = ("var(--warn)" if float(v) >= 70 else "var(--accent)" if float(v) <= 30 else "var(--ink-2)")
    return f' · <span style="color:{col}">RSI {float(v):.0f}</span>'


def _stock_chips(items) -> str:
    if not items:
        return '<div class="sub" style="margin:6px 0 0">None right now.</div>'
    out = []
    for r in items:
        pcol = _PHCOL.get((r["now"] or "").upper(), "var(--ink-2)")
        rk = f' · #{r["rank"]}' if r.get("rank") is not None else ""
        prev_l = _esc(_short(r["prev"] or "—").split(" ")[-1])
        now_l = _esc(_short(r["now"] or "—").split(" ")[-1])
        out.append(
            # color:var(--ink): theme-following; without it anchors render browser-default blue
            f'<a class="pill" style="display:inline-flex;margin:3px;color:var(--ink)" '
            f'href="/dash/momentum?sym={quote_plus(str(r["sym"]))}">'
            f'<b>{_esc(r["sym"])}</b><span style="opacity:.7"> '
            f'{prev_l}→<span style="color:{pcol}">{now_l}</span>{rk}{_rsi_txt(r.get("rsi"))}'
            f'</span></a>')
    return f'<div style="line-height:2">{"".join(out)}</div>'


def _sector_chips(items) -> str:
    if not items:
        return '<div class="sub" style="margin:6px 0 0">None right now.</div>'
    out = []
    for x in items:
        rsi = x.get("rsi")
        rt = f' · RSI {float(rsi):.0f}' if rsi is not None else ""
        out.append(
            f'<a class="pill" style="display:inline-flex;margin:3px;color:var(--ink)" '
            f'href="/dash/sector-momentum?idx={quote_plus(str(x["name"]))}">'
            f'{_esc(_short(x["name"]))}<span style="opacity:.6">{rt} · {_esc(x.get("date"))}</span></a>')
    return f'<div style="line-height:2">{"".join(out)}</div>'


def _card(title: str, tok: str, gloss: str, body: str) -> str:
    return ('<div class="card" style="margin-bottom:12px">'
            f'<div class="h2" style="margin:0 0 2px;color:{tok}">{title}</div>'
            f'<div class="sub" style="margin:0">{gloss}</div>{body}</div>')


def feed_html(conn) -> str:
    fresh, confirm, bull = _fetch(conn)
    if not (fresh or confirm or bull):
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">Early signals</div>'
                '<div class="sub" style="margin:0">Nothing turning up on the latest signals '
                '(needs the nightly RS / rrg compute). Inert until then.</div></div>')
    return (
        '<div class="card" style="margin-bottom:12px"><div class="h2" style="margin:0 0 2px">'
        'Early signals — what\'s turning up today</div><div class="sub" style="margin:0">'
        'The earliest reads across the market: fresh phase turns + bullish sector divergences. '
        '<b>Descriptive early-warning</b> — click a name for its momentum pane.</div></div>'
        + _card(f'Just turned up — fresh ({len(fresh)})', "#7fdcae",
                "Stocks flipping into Recovery / Tailwind from a weaker phase.", _stock_chips(fresh))
        + _card(f'Confirming → Tailwind ({len(confirm)})', "var(--up)",
                "Recoveries graduating to strong-and-strengthening.", _stock_chips(confirm))
        + _card(f'Sectors — bullish divergence ({len(bull)})', "var(--accent)",
                "Sector momentum (RSI of RS) turning up before price.", _sector_chips(bull)))


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)


@router.get("/dash/early-signals", response_class=HTMLResponse)
def early_signals_page():
    with _open() as conn:
        body = feed_html(conn) if conn is not None else feed_html(None)
    body = (ifx.readability_css()
            + ifx.bottom_line(
                'What is <b>turning up today</b>: stocks that just flipped into a recovering / '
                'leading strength phase, and sectors flashing a fresh <b>bullish divergence</b> — '
                'the earliest, freshest turn-ups from already-computed signals. An <b>early-warning '
                'watch feed</b>, never a buy list.')
            + ifx.how_to_read_link()
            + body)
    try:
        from src.web.dashboard import _shell
        return HTMLResponse(_shell("Early signals", body, active="early-signals", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _selftest() -> None:
    assert "None right now" in _stock_chips([])
    assert "None right now" in _sector_chips([])
    assert "RSI 72" in _rsi_txt(72)
    print("early_signals selftest: OK")


if __name__ == "__main__":
    _selftest()
