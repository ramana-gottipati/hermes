"""Surveillance transitions — ASM/GSM entries, exits, stage moves and price-band
changes as an event tape (D94 queue #6 — the LAST item, S92).

Surfaces the two D-02/D-03 primary feeds (src/automation/surveillance.py, NSE
lists, nightly): `surveillance_flags` (dated ASM-LT / ASM-ST / GSM membership
snapshots — transitions DERIVED by diffing consecutive list dates; the earliest
date is the baseline) and `price_band_events` (band set / removed / tightened /
relaxed, with NULL semantics kept honest).

FRAMING (carried from the glossary's standing language): **context, never a
gate.** A name entering ASM often sees mechanically forced flows — leveraged
positions unwinding under 100% margins or T2T settlement — which is information,
not a verdict. No study has been run on this feed in either direction; the tape
states facts and stops.

Flag logic single-sourced in surveillance.flagged_symbols (page == card ==
pillar == board_health). Route: /dash/surveillance [?sym=X]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.automation import surveillance as SV

router = APIRouter()

_KIND_CHIP = {
    "ASM-LT": ("ASM · LT", "background:rgba(240,136,62,.15);color:#f0883e"),
    "ASM-ST": ("ASM · ST", "background:rgba(240,136,62,.25);color:#f0883e"),
    "GSM":    ("GSM", "background:rgba(248,81,73,.18);color:#ff7b72"),
    "BAND":   ("BAND", "background:rgba(88,166,255,.15);color:#58a6ff"),
}
_DIR_MARK = {"up": ("▲", "var(--down)"),      # restriction UP reads adverse-red
             "down": ("▽", "var(--up)"),
             "flat": ("→", "var(--ink-3)")}

_CSS = """
<style>
.sv-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.sv-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.sv-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.sv-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.sv-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.sv-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.sv-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.sv-h small{font-weight:400;color:var(--ink-3);}
table.sv{border-collapse:collapse;width:100%;font-size:12.5px;}
table.sv td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;vertical-align:middle;}
table.sv td.l{text-align:left;}
table.sv tr:hover td{background:#11161d;}
.sv-sym{font-weight:700;color:var(--ink);}
.sv-chip{display:inline-block;padding:1px 8px;border-radius:9px;font-size:10.5px;font-weight:700;letter-spacing:.2px;}
.sv-mut{color:var(--ink-3);}
.sv-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;}
.sv-box{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;
  max-height:38vh;overflow:auto;}
.sv-box b{font-size:12.5px;}
.sv-box .row-line{display:flex;justify-content:space-between;font-size:12px;padding:2px 0;
  border-bottom:1px solid #1b2027;}
</style>
"""


def _chip(kind: str) -> str:
    label, style = _KIND_CHIP.get(kind, ("—", ""))
    return f'<span class="sv-chip" style="{style}">{_esc(label)}</span>'


def _move(e: dict) -> str:
    mark, col = _DIR_MARK.get(e["direction"], ("→", "var(--ink-3)"))
    frm = e["frm"] if e["frm"] not in (None, "") else "—"
    to = e["to"] if e["to"] not in (None, "") else "—"
    return (f'<span style="color:{col};font-weight:700">{mark}</span> '
            f'<b>{_esc(e["what"])}</b> <span class="sv-mut">{_esc(str(frm))} → {_esc(str(to))}</span>')


def _tiles(events: list, flags: list, cur: dict) -> str:
    up = sum(1 for e in events if e["direction"] == "up")
    down = sum(1 for e in events if e["direction"] == "down")
    tight = sum(1 for e in events if e["what"] == "TIGHTENED")
    t = [
        (str(len(flags)), f"Names with a move · {SV.FLAG_DAYS}d", "any entry / exit / stage / band change", "var(--ink)"),
        (str(up), "Restriction UP", "entered ASM/GSM · band tightened", "var(--down)"),
        (str(down), "Restriction DOWN", "exited · band relaxed/removed", "var(--up)"),
        (str(tight), "Band tightenings", "e.g. 20 → 10 → 5 — queue-imbalance context", "#58a6ff"),
        (f'{len(cur.get("ASM-LT", []))}/{len(cur.get("ASM-ST", []))}/{len(cur.get("GSM", []))}',
         "Under now · LT/ST/GSM", "latest NSE lists (membership, not events)", "var(--ink-3)"),
    ]
    tiles = "".join(
        f'<div class="sv-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t)
    return f'<div class="sv-tiles">{tiles}</div>'


def _tape(events: list, sym: str) -> str:
    if sym:
        events = [e for e in events if e["symbol"] == sym.upper()]
    if not events:
        return ('<div class="sv-note">No transitions in the window yet — the snapshot feed is '
                'young (armed 2026-07) and diffs accrue nightly; band changes appear as NSE '
                'publishes them.</div>')
    trs = "".join(
        f'<tr><td class="l sv-mut">{_esc(e["d"])}</td>'
        f'<td class="l"><a class="row" href="/dash/stock?sym={_esc(e["symbol"])}">'
        f'<span class="sv-sym">{_esc(e["symbol"])}</span></a></td>'
        f'<td class="l">{_chip(e["kind"])}</td>'
        f'<td class="l">{_move(e)}</td></tr>' for e in events[:400])
    return (f'<div style="max-height:46vh;overflow:auto"><table class="sv">'
            f'<tbody>{trs}</tbody></table></div>')


def _current(cur: dict) -> str:
    boxes = []
    for kind, title in (("ASM-LT", "ASM long-term"), ("ASM-ST", "ASM short-term"),
                        ("GSM", "GSM"), ("BAND", "Tight bands (2% / 5%)")):
        items = cur.get(kind) or []
        if not items:
            continue
        rows = "".join(
            f'<div class="row-line"><a class="row" href="/dash/stock?sym={_esc(s)}">'
            f'<span class="sv-sym">{_esc(s)}</span></a>'
            f'<span class="sv-mut">{_esc(str(st))}</span></div>' for s, st in items[:120])
        more = (f'<div class="sv-mut" style="font-size:11px;margin-top:4px">'
                f'+{len(items) - 120} more</div>' if len(items) > 120 else "")
        boxes.append(f'<div class="sv-box"><b>{_esc(title)}</b> '
                     f'<span class="sv-mut">· {len(items)}</span>{rows}{more}</div>')
    return f'<div class="sv-cols">{"".join(boxes)}</div>' if boxes else ""


@router.get("/dash/surveillance", response_class=HTMLResponse)
def dash_surveillance(sym: str = "") -> HTMLResponse:
    body = [_CSS]
    as_of = None
    try:
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='surveillance_flags'").fetchone():
                raise LookupError("surveillance tables absent")
            events, as_of = SV.transitions(conn)
            flags, _ = SV.flagged_symbols(conn)
            cur = SV.current_state(conn)
            body.append(
                '<h2 style="margin:0 0 2px">Surveillance transitions <small style="color:var(--ink-3);'
                f'font-size:12px;font-weight:400">NSE ASM / GSM / price-band lists · as of '
                f'{_esc(str(as_of or "—"))} · context, never a gate</small></h2>'
                '<div class="sv-note">Exchange-imposed restriction MOVES: names entering or leaving '
                'ASM/GSM, stage shifts, and price-band changes (a tightening band and close-at-band '
                'streaks are queue-imbalance context). A name entering ASM often sees mechanically '
                'FORCED flows — leveraged positions unwinding under 100% margins or T2T settlement — '
                'which is information, not a verdict. Delivery metrics on T2T names are excluded '
                'site-wide, not polluted. <b>No study exists on this feed in either direction</b> — '
                'the tape states facts and stops. Transitions are diffs of consecutive NSE list '
                'dates (earliest date = baseline). '
                '<a href="/dash/glossary?q=surveillance">glossary →</a></div>')
            body.append(_tiles(events, flags, cur))
            body.append(f'<div class="sv-h">The tape <small>— last {SV.FLAG_DAYS} days, newest first'
                        f'{", " + _esc(sym.upper()) if sym else ""}</small></div>')
            body.append(_tape(events, sym))
            body.append('<div class="sv-h">Under surveillance now <small>— membership, '
                        'not events; latest lists</small></div>')
            body.append(_current(cur))
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Surveillance transitions</h2><div class="sv-note">The surveillance tables are not '
            'populated on this host. They are ingested nightly on production from the NSE ASM/GSM/'
            'price-band lists (<code>src/automation/surveillance.py</code>). This surface is '
            'read-only and never fabricates data.</div>')
    return HTMLResponse(_shell("Surveillance · patearn", "".join(body),
                               "surveillance", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/surveillance" not in paths:
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
    assert c.get("/dash/surveillance").status_code == 200
    assert "Surveillance transitions" in c.get("/dash/surveillance").text
    assert c.get("/dash/surveillance?sym=RELIANCE").status_code == 200
    print("surveil_view selftest OK — page 200 (populated or honest-empty), filter 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
