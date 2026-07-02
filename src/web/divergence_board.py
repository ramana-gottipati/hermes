"""/dash/divergence — the RS/RSI divergence "watch board" (roadmap Phase 1, feature #4).

The early-indicator surface Ramana asked for: "whenever a sector's RSI-on-RS diverges, it
serves as an early indicator." Two columns — BULLISH divergences (RS lower-low but RSI
higher-low → early recovery) and BEARISH (RS higher-high but RSI lower-high → early
rolling-over) — sourced from the ALREADY-COMPUTED flags in rs_extras (rs_div_bull /
rs_div_bear), most-recent first, each linking to its RS-momentum pane (/dash/momentum).

ISOLATED + ADDITIVE (the credibility_fingerprint / momentum_pane pattern): self-contained
APIRouter, mounted via v2_surfaces._ROUTER_SPECS, ZERO edits to existing render paths.
Defensive: degrades to an empty-state if rs_extras / the flags aren't present. Pure read,
₹0, no LLM. DESCRIPTIVE — an early-warning characterization, never a buy/sell signal.

Public: router (GET /dash/divergence) · preview_html(conn, n) for hub embedding.
"""
from __future__ import annotations

import html
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_BENCH = "Nifty 500"


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _short(nm: str) -> str:
    return str(nm).replace("Nifty ", "").replace(" Index", "")


# ── scan the precomputed divergence flags (most-recent flagged bar per numerator) ──
def _scan(conn):
    """Return (bullish[], bearish[]) — each item {name, date, rsi}. Uses the most recent
    bar per numerator that carries a divergence flag. Defensive: [] on any miss."""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(rs_extras)").fetchall()}
    except Exception:  # noqa: BLE001
        return [], []
    if not {"numerator", "trade_date", "rs_div_bull", "rs_div_bear"} <= cols:
        return [], []
    has_rsi = "rsi_of_rs" in cols
    rsi_sel = "rsi_of_rs" if has_rsi else "NULL"
    try:
        rows = conn.execute(
            f"SELECT numerator, trade_date, {rsi_sel}, rs_div_bull, rs_div_bear "
            f"FROM rs_extras WHERE denominator=? AND (rs_div_bull=1 OR rs_div_bear=1) "
            f"ORDER BY trade_date DESC", (_BENCH,)).fetchall()
    except Exception:  # noqa: BLE001
        return [], []
    seen, bull, bear = set(), [], []
    for num, dt, rsi, b1, b2 in rows:
        if num in seen:
            continue
        seen.add(num)
        item = {"name": num, "date": dt, "rsi": rsi}
        (bull if b1 else bear).append(item)
    return bull, bear


# ── render ────────────────────────────────────────────────────────────────────
def _rows(items) -> str:
    if not items:
        return '<div class="sub" style="margin:6px 0 0">None on record.</div>'
    out = []
    for it in items:
        rsi = it.get("rsi")
        rsi_txt = f' · RSI {float(rsi):.0f}' if rsi is not None else ""
        out.append(
            f'<a class="pill" style="display:inline-flex;margin:3px" '
            f'href="/dash/momentum?sym={quote_plus(str(it["name"]))}">'
            f'{_esc(_short(it["name"]))}<span style="opacity:.6">{rsi_txt} · '
            f'{_esc(it.get("date"))}</span></a>')
    return f'<div style="line-height:2">{"".join(out)}</div>'


def _column(title: str, tok: str, gloss: str, items) -> str:
    return (
        '<div class="card" style="flex:1;min-width:280px">'
        f'<div class="h2" style="margin:0 0 2px;color:{tok}">{title} '
        f'<span style="opacity:.55;font-weight:400">({len(items)})</span></div>'
        f'<div class="sub" style="margin:0">{gloss}</div>'
        f'{_rows(items)}</div>')


def _extremes_html(conn) -> str:
    """Most oversold (earliest-turn candidates) / overbought (extended) sectors by
    RSI-of-RS — the 'related signals' watch strip. Cheap: one rs_extras read."""
    try:
        rows = conn.execute(
            "SELECT numerator, rsi_of_rs FROM rs_extras WHERE denominator=? "
            "AND rsi_of_rs IS NOT NULL ORDER BY rsi_of_rs", (_BENCH,)).fetchall()
    except Exception:  # noqa: BLE001
        return ""
    lo = [(r[0], r[1]) for r in rows if r[1] is not None and r[1] < 40][:6]
    hi = list(reversed([(r[0], r[1]) for r in rows if r[1] is not None and r[1] > 60]))[:6]
    if not lo and not hi:
        return ""

    def chips(items, tok):
        return "".join(
            f'<a class="pill" style="display:inline-flex;margin:3px;border-color:{tok};'
            f'color:{tok}" href="/dash/momentum?sym={quote_plus(str(n))}">{_esc(_short(n))} '
            f'<span style="opacity:.7">RSI {v:.0f}</span></a>' for n, v in items)
    lo_html = chips(lo, "var(--accent)") or '<span class="sub">none</span>'
    hi_html = chips(hi, "var(--warn)") or '<span class="sub">none</span>'
    return (
        '<div class="card" style="margin-bottom:12px">'
        '<div class="h2" style="margin:0 0 2px">RSI-of-RS extremes</div>'
        '<div class="sub" style="margin:0">Oversold = washed-out, earliest-turn tell · '
        'Overbought = extended, do not chase. Descriptive.</div>'
        f'<div style="line-height:2;margin-top:6px"><b style="color:var(--accent)">Oversold</b> {lo_html}</div>'
        f'<div style="line-height:2"><b style="color:var(--warn)">Overbought</b> {hi_html}</div>'
        '</div>')


def board_html(conn) -> str:
    bull, bear = _scan(conn)
    if not bull and not bear:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">RS/RSI '
                'divergence board</div><div class="sub" style="margin:0">No divergences '
                'on record yet — needs the nightly RS compute (rs_extras flags). This '
                'surface is inert until then.</div></div>')
    return (
        '<div class="card" style="margin-bottom:12px"><div class="h2" style="margin:0 0 2px">'
        'RS/RSI divergence — early-warning board</div><div class="sub" style="margin:0">'
        'Where a sector\'s momentum (RSI of RS) turns <b>before</b> its price does. '
        '<b>Descriptive early indicator</b> — click a name for its momentum pane.</div></div>'
        + _extremes_html(conn)
        + '<div style="display:flex;gap:12px;flex-wrap:wrap">'
        + _column("Bullish — early recovery", "var(--up)",
                  "RS lower low, RSI higher low.", bull)
        + _column("Bearish — early roll-over", "var(--down)",
                  "RS higher high, RSI lower high.", bear)
        + '</div>')


def preview_html(conn, n: int = 6) -> str:
    """Compact hub-embeddable preview (counts + a few most-recent names each side)."""
    bull, bear = _scan(conn)
    if not bull and not bear:
        return ""
    b = ", ".join(_short(x["name"]) for x in bull[:n]) or "—"
    r = ", ".join(_short(x["name"]) for x in bear[:n]) or "—"
    return (
        '<div class="card"><div class="h2" style="margin:0 0 2px">'
        '<a href="/dash/divergence" style="text-decoration:none">RS/RSI divergence ▸</a>'
        '</div><div class="sub" style="margin:0 0 6px">Momentum turning before price '
        '(early indicator).</div>'
        f'<div style="margin:0 0 3px"><span style="color:var(--up)">▲ {len(bull)} bullish</span>'
        f' &nbsp; {_esc(b)}</div>'
        f'<div><span style="color:var(--down)">▼ {len(bear)} bearish</span> &nbsp; {_esc(r)}</div>'
        '</div>')


@router.get("/dash/divergence", response_class=HTMLResponse)
def divergence_page():
    cm = _open()
    with cm as conn:
        body = board_html(conn) if conn is not None else board_html(None)
    try:
        from src.web.dashboard import _shell
        return HTMLResponse(_shell("RS/RSI divergence", body, active="markets", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)
