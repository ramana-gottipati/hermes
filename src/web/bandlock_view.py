"""Band-lock streaks — names pinned at their daily price band, as a measured board
(charter X-05, S96c).

Surfaces src/automation/band_lock.py over the D-03 security-wise band feed + raw bhav
OHLC: a name that closed AT its permitted daily maximum (close == high == the +band%
limit) is UPPER-LOCKED — the buy queue outran the band; LOWER-LOCKED symmetrically.
Streaks are consecutive same-direction locked days ending at the latest bhav date.

FRAMING (the surveillance glossary's standing line, now measured): a close-at-band
streak is a QUEUE-IMBALANCE TELL — context, never a gate. No study exists on band-lock
streaks in either direction; any drift/return claim needs its own pre-registered gate.
THE HONEST WINDOW is printed on-page: bands are reconstructable only back to the feed's
first captured day (band_lock.FEED_BIRTH = 2026-07-07) — the board deepens every
trading night and never fabricates earlier history.

Flag logic single-sourced in band_lock.flagged_symbols (page == card == pillar ==
board_health). Route: /dash/band-locks
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx  # shared readability scaffold (S-C education)
from src.automation import band_lock as BL

router = APIRouter()

_CSS = """
<style>
.bl-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.bl-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.bl-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.bl-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.bl-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.bl-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.bl-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.bl-h small{font-weight:400;color:var(--ink-3);}
table.bl{border-collapse:collapse;width:100%;font-size:12.5px;}
table.bl th{text-align:right;padding:4px 9px;font-size:10.5px;color:var(--ink-3);
  text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid var(--line-2);}
table.bl th.l,table.bl td.l{text-align:left;}
table.bl td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;
  text-align:right;font-variant-numeric:tabular-nums;}
table.bl tr:hover td{background:#11161d;}
.bl-sym{font-weight:700;color:var(--ink);}
.bl-chip{display:inline-block;padding:1px 8px;border-radius:9px;font-size:10.5px;font-weight:700;}
.bl-up{background:rgba(63,185,80,.15);color:var(--up);}
.bl-dn{background:rgba(248,81,73,.15);color:var(--down);}
.bl-flag{color:#f0883e;font-weight:800;}
.bl-fence{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;
  padding:10px 13px;margin:14px 0 0;font-size:12px;color:var(--ink-2);line-height:1.6;max-width:1150px;}
</style>
"""


def _tiles(streaks: list, flags: list, ndays: int) -> str:
    up = sum(1 for s in streaks if s["dir"] == "UP")
    dn = sum(1 for s in streaks if s["dir"] == "DOWN")
    longest = max((s["days"] for s in streaks), default=0)
    t = [
        (str(len(streaks)), "Locked at band today", "close == high/low == the daily limit", "var(--ink)"),
        (str(up), "Upper locks ▲", "buy queue outran the band", "var(--up)"),
        (str(dn), "Lower locks ▼", "sell queue pinned the floor", "var(--down)"),
        (str(len(flags)), f"Streaks ≥ {BL.FLAG_MIN_STREAK}d (flagged)", "the persistence cohort", "#f0883e"),
        (f"{longest}/{ndays}", "Longest / window (days)", "window opens at the feed's birth", "var(--ink-3)"),
    ]
    return '<div class="bl-tiles">' + "".join(
        f'<div class="bl-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t) + "</div>"


def _board(streaks: list) -> str:
    if not streaks:
        return ('<div class="bl-note">No name is locked at its band on the latest trading '
                'day — a healthy zero, stated as such.</div>')
    rows = []
    for s in streaks:
        chip = ('<span class="bl-chip bl-up">▲ UP</span>' if s["dir"] == "UP"
                else '<span class="bl-chip bl-dn">▼ DOWN</span>')
        flag = ' <span class="bl-flag">⚑</span>' if s["days"] >= BL.FLAG_MIN_STREAK else ""
        move = f'{s["move_pct"]:+.1f}%' if s["move_pct"] is not None else "—"
        mcol = "var(--up)" if (s["move_pct"] or 0) >= 0 else "var(--down)"
        rows.append(
            f'<tr><td class="l"><a class="bl-sym" href="/dash/stock?sym={_esc(s["symbol"])}">'
            f'{_esc(s["symbol"])}</a>{flag}</td>'
            f'<td class="l">{chip}</td>'
            f'<td><b>{s["days"]}</b></td>'
            f'<td>{s["band"]:g}%</td>'
            f'<td>{s["last_close"]:,.2f}</td>'
            f'<td style="color:{mcol};font-weight:700">{_esc(move)}</td>'
            f'<td class="l" style="color:var(--ink-3)">{_esc(s["first_date"])}</td></tr>')
    head = ('<tr><th class="l">Symbol</th><th class="l">Side</th><th>Streak</th>'
            '<th>Band</th><th>Close</th><th>Move over streak</th><th class="l">Since</th></tr>')
    return f'<table class="bl">{head}{"".join(rows)}</table>'


@router.get("/dash/band-locks", response_class=HTMLResponse)
def band_locks_page() -> HTMLResponse:
    body = [_CSS, ifx.readability_css()]
    as_of = None
    try:
        with get_conn() as conn:
            streaks, as_of = BL.active_streaks(conn)
            flags, _ = BL.flagged_symbols(conn)
            ndays = len(BL.trading_dates(conn, BL.FEED_BIRTH))
            body.append(
                '<h2>Band-lock streaks</h2>'
                + ifx.bottom_line(
                    'Stocks <b>pinned at their daily price limit</b> — the exchange\'s band capped '
                    'the move and the queue never cleared — and for how many straight sessions. '
                    'A long streak = one-sided demand or supply the auction cannot absorb: a '
                    '<b>queue-imbalance tell to investigate</b>, never a gate or a signal.')
                + ifx.how_to_read_link()
                + '<div class="bl-note">Names that closed <b>pinned at their daily price band</b> '
                '— close == high == the +band% limit (▲ upper lock: the buy queue outran the '
                'band) or close == low == the −band% floor (▼ lower lock) — and for how many '
                'consecutive sessions. A lock means the auction could not clear at the '
                'permitted range: a <b>queue-imbalance tell, never a gate</b>. Locks are '
                'detected on as-traded prices with each day&#39;s band reconstructed from the '
                'change log. <a href="/dash/surveillance">Surveillance Δ →</a> carries the '
                'restriction context (ASM/GSM/T2T); '
                '<a href="/dash/glossary?q=band-lock">glossary →</a></div>')
            body.append(_tiles(streaks, flags, ndays))
            body.append(f'<div class="bl-h">Active locks <small>— as of {_esc(str(as_of or "—"))}, '
                        f'longest streak first; ⚑ = flagged (≥ {BL.FLAG_MIN_STREAK}d)</small></div>')
            body.append(_board(streaks))
            body.append(
                '<div class="bl-fence">📏 <b>The honest window:</b> the security-wise band feed '
                f'began capturing on <b>{BL.FEED_BIRTH}</b> — past bands are reconstructed from '
                'the change log back to that day and no further, so streaks cannot yet exceed '
                'the window and earlier locks are invisible here by construction. The board '
                'deepens every trading night. <b>Descriptive only:</b> no study exists on '
                'band-lock streaks in either direction; any claim that locks precede returns '
                'would need its own pre-registered gate first (M-04). Not investment advice.</div>')
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Band-lock streaks</h2><div class="bl-note">The band tables are not populated '
            'on this host. Bands are ingested nightly on production from the NSE security-wise '
            'band list (<code>src/automation/surveillance.py</code>); lock detection lives in '
            '<code>src/automation/band_lock.py</code>. This surface is read-only and never '
            'fabricates data.</div>')
    return HTMLResponse(_shell("Band locks · patearn", "".join(body),
                               "band-locks", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/band-locks" not in paths:
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
    r = c.get("/dash/band-locks")
    assert r.status_code == 200
    assert "Band-lock streaks" in r.text
    print("bandlock_view selftest OK — page 200 (populated or honest-empty)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
