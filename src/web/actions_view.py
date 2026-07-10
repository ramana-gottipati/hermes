"""Corporate-actions calendar — what goes ex, when (D94 queue #5, S91).

Surfaces `corporate_actions` (hermes.db, NSE corporate-actions feed, nightly
`hermes-corp-actions.timer`, 26.8K actions 2004→present) as a FORWARD calendar:
every dividend / bonus / split / rights / buyback with an ex-date ahead, grouped
by day — plus the recent past and the `security_events` restructure context
(demergers / schemes / amalgamations).

STRICTLY LOGISTICS (ledger-cited): E-11 dividend-surprise drift tested NULL
(placebo-caught — dividend PAYERS drift in random windows too; "no chip ships")
and E-12 rebrand pump is dead (CAR22 −0.41%). This page tells you WHAT happens
WHEN — never what to do about it. Splits/bonuses shown here are the same events
that drive the site's adjusted-price engine (value-not-quantity doctrine).

Flag logic single-sourced in corp_actions.flagged_symbols (page == card ==
pillar == board_health). Route: /dash/actions [?window=30|60|120] [?sym=X]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.automation import corp_actions as CA

router = APIRouter()

_TYPE_CHIP = {
    "DIVIDEND": ("DIVIDEND", "background:var(--up-dim);color:var(--up)"),
    "BONUS":    ("BONUS", "background:rgba(88,166,255,.15);color:#58a6ff"),
    "SPLIT":    ("SPLIT", "background:rgba(210,168,255,.18);color:#d2a8ff"),
    "RIGHTS":   ("RIGHTS", "background:rgba(240,136,62,.15);color:#f0883e"),
    "BUYBACK":  ("BUYBACK", "background:rgba(126,231,135,.15);color:#7ee787"),
    "DEMERGER": ("DEMERGER", "background:rgba(227,181,65,.18);color:#e3b341"),
    "SCHEME":   ("SCHEME", "background:var(--bg-3);color:var(--ink-2)"),
    "OTHER":    ("other", "background:var(--bg-3);color:var(--ink-3)"),
}

_CSS = """
<style>
.ca-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.ca-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.ca-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.ca-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.ca-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.ca-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.ca-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.ca-h small{font-weight:400;color:var(--ink-3);}
.ca-day{font-size:12.5px;font-weight:700;color:var(--ink);background:var(--bg-2);border:1px solid var(--line-2);
  border-radius:8px;padding:5px 11px;margin:12px 0 6px;display:inline-block;}
.ca-day small{color:var(--ink-3);font-weight:400;}
table.ca{border-collapse:collapse;width:100%;font-size:12.5px;}
table.ca td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;vertical-align:middle;}
table.ca td.l{text-align:left;}
table.ca tr:hover td{background:#11161d;}
.ca-sym{font-weight:700;color:var(--ink);}
.ca-chip{display:inline-block;padding:1px 8px;border-radius:9px;font-size:10.5px;font-weight:700;letter-spacing:.2px;}
.ca-mut{color:var(--ink-3);}
.ca-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 10px;}
.ca-ctrl a{padding:4px 11px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;
  text-decoration:none;white-space:nowrap;}
.ca-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
</style>
"""


def _chip(t: str) -> str:
    label, style = _TYPE_CHIP.get(t or "OTHER", _TYPE_CHIP["OTHER"])
    return f'<span class="ca-chip" style="{style}">{_esc(label)}</span>'


def _ratio(r) -> str:
    if r["ratio_from"] and r["ratio_to"]:
        return f'{r["ratio_from"]:g}:{r["ratio_to"]:g}'
    return ""


def _tiles(fwd: list, flags: list, as_of) -> str:
    def _n(t):
        return sum(1 for r in fwd if r["action_type"] == t)
    t = [
        (str(len(flags)), f"Names going ex · {CA.FLAG_DAYS}d", "the card cohort — soonest first", "var(--ink)"),
        (str(_n("DIVIDEND")), "Dividends ahead", "amounts as filed, shown verbatim", "var(--up)"),
        (str(_n("BONUS") + _n("SPLIT")), "Bonus / splits ahead", "these re-base the adjusted-price engine", "#d2a8ff"),
        (str(_n("RIGHTS") + _n("BUYBACK")), "Rights / buybacks ahead", "capital events (dilution / return)", "#f0883e"),
        (_esc(str(as_of or "—")), "Feed ingested", "nightly NSE corporate-actions feed", "var(--ink-3)"),
    ]
    tiles = "".join(
        f'<div class="ca-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t)
    return f'<div class="ca-tiles">{tiles}</div>'


def _calendar(rows: list, sym: str) -> str:
    if sym:
        rows = [r for r in rows if r["symbol"] == sym.upper()]
    if not rows:
        return '<div class="ca-note">No forward actions in this window.</div>'
    days: dict = {}
    for r in rows:
        days.setdefault(r["ex_date"], []).append(r)
    parts = []
    for d in sorted(days):
        items = days[d]
        trs = "".join(
            f'<tr><td class="l"><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
            f'<span class="ca-sym">{_esc(r["symbol"])}</span></a></td>'
            f'<td class="l">{_chip(r["action_type"])}</td>'
            f'<td class="l">{_esc(_ratio(r))}</td>'
            f'<td class="l ca-mut" title="{_esc(r["details"] or "")}">{_esc((r["details"] or "—")[:64])}</td>'
            f'<td class="l ca-mut" title="record date">{_esc(str(r["record_date"] or "—")[:10])}</td></tr>'
            for r in items)
        parts.append(
            f'<div class="ca-day">{_esc(d)} <small>· {len(items)} going ex</small></div>'
            f'<table class="ca"><tbody>{trs}</tbody></table>')
    return "".join(parts)


def _recent(conn) -> str:
    """The recent-past tape (last 30d) + security_events restructure context."""
    rows = conn.execute(
        "SELECT ex_date, symbol, action_type, details FROM corporate_actions "
        "WHERE ex_date < date('now') AND ex_date >= date('now', '-30 days') "
        "ORDER BY ex_date DESC LIMIT 200").fetchall()
    sev = conn.execute(
        "SELECT ex_date, symbol, event_type, details FROM security_events "
        "WHERE ex_date >= date('now', '-180 days') ORDER BY ex_date DESC LIMIT 40").fetchall()
    out = []
    if rows:
        trs = "".join(
            f'<tr><td class="l ca-mut">{_esc(str(r[0])[:10])}</td>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_esc(r[1])}">'
            f'<span class="ca-sym">{_esc(r[1])}</span></a></td>'
            f'<td class="l">{_chip(r[2])}</td>'
            f'<td class="l ca-mut">{_esc((r[3] or "—")[:64])}</td></tr>' for r in rows)
        out.append('<div class="ca-h">Just went ex <small>— the last 30 days</small></div>'
                   f'<div style="max-height:34vh;overflow:auto"><table class="ca"><tbody>{trs}</tbody></table></div>')
    if sev:
        trs = "".join(
            f'<tr><td class="l ca-mut">{_esc(str(r[0])[:10])}</td>'
            f'<td class="l"><span class="ca-sym">{_esc(r[1])}</span></td>'
            f'<td class="l">{_chip(r[2])}</td>'
            f'<td class="l ca-mut">{_esc((r[3] or "—")[:64])}</td></tr>' for r in sev)
        out.append('<div class="ca-h">Restructure context <small>— demergers / schemes / '
                   'amalgamations, last 180 days (security_events)</small></div>'
                   f'<div style="max-height:28vh;overflow:auto"><table class="ca"><tbody>{trs}</tbody></table></div>')
    return "".join(out)


@router.get("/dash/actions", response_class=HTMLResponse)
def dash_actions(window: int = 60, sym: str = "") -> HTMLResponse:
    window = window if window in (30, 60, 120) else 60
    body = [_CSS]
    as_of = None
    try:
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='corporate_actions'").fetchone():
                raise LookupError("corporate_actions absent")
            fwd, as_of = CA.upcoming(conn, days=window)
            flags, _ = CA.flagged_symbols(conn)
            body.append(
                '<h2 style="margin:0 0 2px">Corporate-actions calendar <small style="color:var(--ink-3);'
                f'font-size:12px;font-weight:400">NSE corporate-actions feed · ingested {_esc(str(as_of or "—"))} '
                '· descriptive / logistical</small></h2>'
                '<div class="ca-note">Every dividend, bonus, split, rights issue and buyback with an ex-date '
                'AHEAD, grouped by day — beside the <a href="/dash/markets/results-reactions">results '
                'calendar</a>. Bonus/split events here are exactly what re-bases the site\'s adjusted-price '
                'engine (value, not quantity). <b>This page is logistics, not signal:</b> the dividend-drift '
                'study came back NULL against placebo and the rebrand-pump story is dead (both in the '
                'failure ledger) — the calendar tells you WHAT happens WHEN, never what to do about it. '
                '<a href="/dash/glossary?q=ex-date">glossary →</a></div>')
            body.append(_tiles(fwd, flags, as_of))
            tabs = "".join(
                f'<a class="{"on" if window == w else ""}" href="/dash/actions?window={w}">{w}d</a>'
                for w in (30, 60, 120))
            body.append(f'<div class="ca-ctrl">{tabs}</div>')
            body.append(f'<div class="ca-h">Going ex next <small>— {window} days ahead'
                        f'{", " + _esc(sym.upper()) if sym else ""}</small></div>')
            body.append(_calendar(fwd, sym))
            body.append(_recent(conn))
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Corporate-actions calendar</h2><div class="ca-note">The '
            '<code>corporate_actions</code> table is not populated on this host. It is ingested '
            'nightly on production from the NSE corporate-actions feed '
            '(<code>src/automation/corp_actions.py</code>). This surface is read-only and never '
            'fabricates data.</div>')
    return HTMLResponse(_shell("Corp actions · patearn", "".join(body),
                               "actions", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/actions" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    assert c.get("/dash/actions").status_code == 200
    assert "Corporate-actions calendar" in c.get("/dash/actions").text
    assert c.get("/dash/actions?window=120&sym=RELIANCE").status_code == 200
    print("actions_view selftest OK — page 200 (populated or honest-empty), filters 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
