"""Attention Queue — the HOME-surface face of the signal-event bus (D106, S103).

"One bus, four faces" (product-strategy §9): the bus (`src/automation/signal_events.py`,
D105) already serves one face — `/v1/attention` (PIT replay, AUD-38/D104 semantics).
This module is the SECOND face: the human front-door. It answers "what changed that
deserves my attention?" across every live lens (mep · cci · oi · rs · deal) in one
magnitude-ranked tape, data-first (raw before→after beside every verdict), PIT-honest
(`?as_of=` replays any past batch via the same last-batch-on-or-before resolver the
/v1 API uses — an exact-date miss must not read as an empty tape).

FRAMING: an event is a *derived judgement that something changed* — never a
recommendation. The lenses' own fences ride along: CCI is descriptive-only (alpha
falsified), MEP is a descriptor (D62), deal prints are logistics. Magnitude ranks
attention WITHIN a batch; it is not a return forecast and no study exists on
event-follow-through (any such claim needs its own pre-registered gate first).

Isolation: brand-new module; reads ONLY through signal_events' public read APIs;
degrades to an honest empty state, never a 500. Route: /dash/attention.
Home face: `attention_home_inner()` — '' when the bus is empty (board omitted).
"""
from __future__ import annotations

import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.automation import signal_events as SE

router = APIRouter()

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PAGE_LIMIT = 200          # the full-page tape cap (the home face stays at the hard 6)

_LENS_META = {
    "mep":  ("MEP",   "#db61a2", "accumulation phase"),
    "cci":  ("CCI",   "#a371f7", "credibility step"),
    "oi":   ("F&O",   "#f0883e", "positioning quadrant"),
    "rs":   ("RS",    "#d29922", "index band state"),
    "deal": ("DEAL",  "#58a6ff", "bulk/block print"),
    "dvpt": ("DVPT",  "#3fb950", "delivery"),
    "quality": ("QLTY", "#8b949e", "quality"),
    "cpr":  ("CPR",   "#8b949e", "structure"),
}

_CSS = """
<style>
.at-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.at-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 14px;}
.at-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.at-tile .n{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.at-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.at-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.at-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.at-h small{font-weight:400;color:var(--ink-3);}
.at-chips{margin:0 0 10px;}
.at-chip{display:inline-block;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700;
  border:1px solid var(--line-2);color:var(--ink-2);margin-right:6px;text-decoration:none;}
.at-chip.on{background:var(--bg-2);color:var(--ink);border-color:var(--ink-3);}
.at-lens{display:inline-block;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:800;letter-spacing:.4px;}
table.at{border-collapse:collapse;width:100%;font-size:12.5px;}
table.at th{text-align:left;padding:4px 9px;font-size:10.5px;color:var(--ink-3);
  text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid var(--line-2);}
table.at td{padding:5px 9px;border-bottom:1px solid #1b2027;text-align:left;vertical-align:top;}
table.at td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
table.at tr:hover td{background:#11161d;}
.at-sym{font-weight:700;color:var(--ink);}
.at-arrow{color:var(--ink-3);}
.at-state{font-variant-numeric:tabular-nums;white-space:nowrap;}
.at-mag{display:inline-block;height:7px;border-radius:4px;background:var(--ink-3);vertical-align:middle;}
.at-noteline{color:var(--ink-2);}
.at-pit{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;
  padding:8px 13px;margin:0 0 12px;font-size:12px;color:var(--ink-2);}
.at-fence{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;
  padding:10px 13px;margin:14px 0 0;font-size:12px;color:var(--ink-2);line-height:1.6;max-width:1150px;}
.at-replay{margin:0 0 12px;font-size:12px;color:var(--ink-3);}
.at-replay input{background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);
  border-radius:7px;padding:3px 8px;font-size:12px;}
.at-home td{padding:3px 6px;border-bottom:1px solid #1b2027;font-size:12px;}
</style>
"""


def _lens_chip(lens: str) -> str:
    label, color, _ = _LENS_META.get(lens, (lens.upper(), "#8b949e", ""))
    return (f'<span class="at-lens" style="background:{color}22;color:{color}">'
            f'{_esc(label)}</span>')


def _dir_glyph(direction) -> str:
    return {"up": "▲", "down": "▼", "flip": "⇄", "in": "→", "out": "←"}.get(direction or "", "·")


def _sym_cell(ev: dict) -> str:
    """rs-lens symbols are INDEX names (no dossier) — route them to the band lens."""
    sym = ev.get("symbol") or ""
    if ev.get("lens") == "rs":
        return (f'<a class="at-sym" href="/dash/rsband">{_esc(sym)}</a>')
    return (f'<a class="at-sym" href="/dash/stock?symbol={_esc(sym)}">{_esc(sym)}</a>')


def render_queue_table(events: list[dict]) -> str:
    """The magnitude-ranked tape for one batch. Pure over rows (hermetically testable)."""
    if not events:
        return ('<div class="at-note">No events in this batch — a quiet tape is a quiet '
                'tape, stated as such (nothing is fabricated to fill the queue).</div>')
    rows = []
    for e in events:
        mag = e.get("magnitude")
        magw = max(3, int(round(56 * min(1.0, max(0.0, float(mag or 0))))))
        fr, to = e.get("from_state"), e.get("to_state")
        change = (f'<span class="at-state">{_esc(str(fr))}</span> '
                  f'<span class="at-arrow">→</span> '
                  f'<span class="at-state">{_esc(str(to))}</span>'
                  if fr is not None else f'<span class="at-state">{_esc(str(to or "—"))}</span>')
        det = str(e.get("detected_at") or "")[11:16]
        rows.append(
            f'<tr><td>{_sym_cell(e)}</td>'
            f'<td>{_lens_chip(e.get("lens") or "")}</td>'
            f'<td>{_esc((e.get("event_type") or "").replace("_", " "))} '
            f'{_dir_glyph(e.get("direction"))}</td>'
            f'<td>{change}</td>'
            f'<td class="num"><span class="at-mag" style="width:{magw}px"></span> '
            f'{(f"{float(mag):.2f}" if mag is not None else "—")}</td>'
            f'<td class="at-noteline">{_esc(e.get("note") or "")}</td>'
            f'<td class="num" style="color:var(--ink-3)">{_esc(det)}</td></tr>')
    head = ('<tr><th>Symbol</th><th>Lens</th><th>Event</th><th>From → To</th>'
            '<th style="text-align:right">Impact</th><th>Note</th>'
            '<th style="text-align:right">UTC</th></tr>')
    return f'<table class="at">{head}{"".join(rows)}</table>'


def render_batch_history(hist: list[dict], live_lenses: tuple[str, ...]) -> str:
    """Per-batch per-lens counts, newest first. `hist` rows: {as_of, lens, n}."""
    if not hist:
        return ""
    days: dict[str, dict[str, int]] = {}
    for r in hist:
        days.setdefault(r["as_of"], {})[r["lens"]] = r["n"]
    lenses = [l for l in live_lenses if any(l in d for d in days.values())]
    head = ("<tr><th>Batch (as_of)</th>"
            + "".join(f'<th style="text-align:right">{_esc(l)}</th>' for l in lenses)
            + '<th style="text-align:right">Total</th></tr>')
    rows = []
    for day in sorted(days, reverse=True):
        cnt = days[day]
        rows.append(f'<tr><td>{_esc(day)}</td>'
                    + "".join(f'<td class="num">{cnt.get(l) or "·"}</td>' for l in lenses)
                    + f'<td class="num"><b>{sum(cnt.values())}</b></td></tr>')
    return f'<table class="at" style="max-width:720px">{head}{"".join(rows)}</table>'


def _tiles(st: dict, batch: str | None, batch_n: int) -> str:
    by_lens = st.get("by_lens") or {}
    t = [
        (str(batch or "—"), "Serving batch (as_of)", "the newest computed event day", "var(--ink)"),
        (str(batch_n), "Events in this batch", "magnitude-ranked below", "var(--ink)"),
        (str(sum(1 for v in by_lens.values() if v)), "Lenses that have emitted",
         " · ".join(f"{k} {v}" for k, v in list(by_lens.items())[:5]) or "—", "var(--ink-3)"),
        (str(st.get("events") or 0), "Events all-time", "bus live since 2026-07-10", "var(--ink-3)"),
    ]
    return '<div class="at-tiles">' + "".join(
        f'<div class="at-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t) + "</div>"


def _lens_filter_chips(active: str | None) -> str:
    live = ("mep", "cci", "oi", "rs", "deal")
    chips = [f'<a class="at-chip{" on" if not active else ""}" href="/dash/attention">All</a>']
    chips += [f'<a class="at-chip{" on" if active == l else ""}" '
              f'href="/dash/attention?lens={l}">{_esc(_LENS_META[l][0])}</a>' for l in live]
    return '<div class="at-chips">' + "".join(chips) + "</div>"


@router.get("/dash/attention", response_class=HTMLResponse)
def attention_page(as_of: str = "", lens: str = "") -> HTMLResponse:
    body = [_CSS]
    served: str | None = None
    try:
        with get_conn() as conn:
            st = SE.stats(conn)
            requested = as_of.strip()[:10] if as_of and _DATE_RE.match(as_of.strip()[:10]) else None
            served = (SE.latest_batch_on_or_before(conn, requested) if requested
                      else st.get("latest_as_of"))
            # Fetch the WHOLE batch (a batch is a few hundred rows at most) so the tile
            # count and the filter denominator are the batch's truth; cap only the RENDER.
            events = SE.attention_queue(conn, as_of=served, limit=1_000_000) if served else []
            lens_q = lens.strip().lower()
            shown = [e for e in events if e.get("lens") == lens_q] if lens_q in SE.LENSES else events
            shown_total = len(shown)
            shown = shown[:_PAGE_LIMIT]
            hist = [dict(r) for r in conn.execute(
                "SELECT as_of, lens, COUNT(*) AS n FROM signal_events WHERE as_of IN ("
                "SELECT DISTINCT as_of FROM signal_events ORDER BY as_of DESC LIMIT 12) "
                "GROUP BY as_of, lens ORDER BY as_of DESC").fetchall()]

            body.append(
                '<h2>Attention queue</h2>'
                '<div class="at-note">The signal-event bus in one tape: every lens emits a '
                'TYPED state-change — MEP phase flips, credibility steps, F&amp;O quadrant '
                'flips, index RS-band flips, bulk/block prints — and this queue ranks the '
                'current batch by <b>impact (magnitude), then recency</b>. Every row keeps '
                'the raw before → after beside the verdict (data-first), and every event '
                'carries the date it is computed <i>for</i> (<code>as_of</code>, point-in-'
                'time honest). An event is a <b>state-change, never a recommendation</b>. '
                '<a href="/dash/glossary?q=attention">glossary →</a></div>')
            if requested:
                body.append(
                    f'<div class="at-pit">⏪ <b>Replay:</b> requested <b>{_esc(requested)}</b> → '
                    f'serving batch <b>{_esc(str(served or "none"))}</b> — the last computed '
                    f'batch on-or-before the requested day (the same resolver as '
                    f'<code>/v1/attention</code>; a weekend/holiday miss must not read as an '
                    f'empty tape). <a href="/dash/attention">back to latest →</a></div>')
            body.append(_tiles(st, served, len(events)))
            body.append('<form class="at-replay" method="get" action="/dash/attention">'
                        'Replay the queue as it stood on '
                        f'<input type="date" name="as_of" value="{_esc(requested or "")}"> '
                        '<button class="at-chip" type="submit">Replay</button></form>')
            body.append(_lens_filter_chips(lens_q if lens_q in SE.LENSES else None))
            nlab = (f' · {_esc(lens_q)} only ({shown_total} of {len(events)})'
                    if lens_q in SE.LENSES else "")
            cap = (f' · showing the top {len(shown)} of {shown_total} by impact'
                   if shown_total > len(shown) else "")
            body.append(f'<div class="at-h">The queue <small>— batch '
                        f'{_esc(str(served or "—"))}{nlab}{cap}</small></div>')
            body.append(render_queue_table(shown))
            bh = render_batch_history(hist, ("mep", "cci", "oi", "rs", "deal"))
            if bh:
                body.append('<div class="at-h">Batches <small>— events per lens for the '
                            'last 12 computed days; the bus deepens nightly (chain '
                            'step 60)</small></div>')
                body.append(bh)
            body.append(
                '<div class="at-fence">📏 <b>How to read impact:</b> magnitude is normalized '
                'WITHIN each lens — a phase/quadrant flip is 1.0 by construction; a '
                'credibility step is |Δlevel|/50 (capped); a deal print is the symbol&#39;s '
                'share-of-day value <i>percentile</i> (relative, never a rupee constant). It '
                'ranks attention within a batch; it is <b>not a return forecast</b> — no '
                'study exists on event follow-through, and any such claim needs its own '
                'pre-registered gate first. <b>The lenses&#39; own fences ride along:</b> CCI '
                'is descriptive-only (alpha falsified), MEP is a descriptor (D62), deal '
                'prints are logistics. <b>PIT honesty (two clocks):</b> <code>as_of</code> '
                '= the day the change actually occurred; <code>UTC</code> = when the bus '
                'detected it. Detection began 2026-07-10, so for names whose LAST state-'
                'change was long ago (thin/delisted symbols swept in the first run) a '
                'replay can serve batches dated years before the bus existed — real '
                'state-changes at their real dates, detected late, never fabricated. One '
                'event per (symbol, lens, type, day) — idempotent by key. Not investment '
                'advice. Machine face: <code>/v1/attention</code>.</div>')
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Attention queue</h2><div class="at-note">The signal-event bus is not '
            'populated on this host. Events are emitted nightly on production as step 60 '
            'of the bhavcopy chain (<code>src/automation/signal_events.py --detect</code>). '
            'This surface is read-only and never fabricates data.</div>')
    return HTMLResponse(_shell("Attention · patearn", "".join(body),
                               "attention", str(served or "")[:10], wide=True))


def attention_home_inner(limit: int = 6) -> str:
    """The compact Home card body — the hard-capped queue. '' when the bus is empty
    or unreadable (the caller omits the board; Home never breaks on this face)."""
    try:
        with get_conn() as conn:
            events = SE.attention_queue(conn, limit=limit)
            if not events:
                return ""
            rows = []
            for e in events:
                note = (e.get("note") or "")
                note = note if len(note) <= 86 else note[:83] + "…"
                rows.append(
                    f'<tr class="at-home"><td>{_sym_cell(e)}</td>'
                    f'<td>{_lens_chip(e.get("lens") or "")}</td>'
                    f'<td style="color:var(--ink-2)">{_esc(note)}</td>'
                    f'<td style="color:var(--ink-3);white-space:nowrap">'
                    f'{_esc(str(e.get("as_of") or ""))}</td></tr>')
            return (_CSS + '<table class="at"><tbody>' + "".join(rows)
                    + "</tbody></table>")
    except Exception:  # noqa: BLE001
        return ""


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/attention" not in paths:
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
    r = c.get("/dash/attention")
    assert r.status_code == 200
    assert "Attention queue" in r.text
    r2 = c.get("/dash/attention?as_of=2026-01-01&lens=mep")
    assert r2.status_code == 200
    print("attention_view selftest OK — page 200 (populated or honest-empty), replay 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
