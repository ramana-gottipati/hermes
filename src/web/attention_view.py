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

S108 adds the "since you last looked" brief (D110) at the top of the live view: a
cookie-keyed strip of everything DETECTED since the viewer's last visit (the bus's
own `events_since` feed), distinct from the impact-ranked current-batch queue below.
Last-visit is a client cookie (a timestamp) — no per-user server state, no new table.

This module also hosts the bus's FOURTH face — the **alert rail** (`signal_alerts.py`):
the curated, multi-day, severity-graded set of only the highest-impact state-changes,
edge-triggered so each fires once and is kept as it rolls past today's batch. It is a
strict subset of the queue (a short notifications list, not the firehose), read-only
here (promotion runs in the nightly bus --detect), and it carries the same fence: a
state-change, never a recommendation.

Isolation: brand-new module; reads ONLY through signal_events' public read APIs;
degrades to an honest empty state, never a 500. Route: /dash/attention.
Home face: `attention_home_inner()` — '' when the bus is empty (board omitted).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx  # shared readability scaffold (S-C education)
from src.automation import signal_events as SE
from src.automation import signal_alerts as SA

router = APIRouter()

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")   # the last-seen cookie shape
_SEEN_COOKIE = "patearn_bus_seen"    # holds the viewer's last-visit detected_at (client-side)
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
.at-seen{border-radius:10px;padding:9px 13px;margin:0 0 12px;font-size:12.5px;
  line-height:1.5;border:1px solid var(--line-2);}
.at-seen-new{background:rgba(88,166,255,.10);border-color:rgba(88,166,255,.35);color:var(--ink);}
.at-seen-none{background:var(--bg-2);color:var(--ink-2);}
.at-seen-more{margin-top:6px;color:var(--ink-3);font-size:11.5px;}
.at-rail{border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;margin:0 0 14px;
  background:var(--bg-2);}
.at-rail-h{font-size:13px;font-weight:700;color:var(--ink);margin:0 0 4px;display:flex;
  align-items:center;gap:8px;flex-wrap:wrap;}
.at-rail-sub{font-size:11.5px;color:var(--ink-3);margin:0 0 8px;line-height:1.5;}
.at-badge{display:inline-block;padding:1px 8px;border-radius:9px;font-size:11px;font-weight:800;
  border:1px solid var(--line-2);color:var(--ink-2);}
.at-badge.crit{background:rgba(248,81,73,.16);color:#f85149;border-color:rgba(248,81,73,.42);}
.at-badge.high{background:rgba(210,153,34,.14);color:#d29922;border-color:rgba(210,153,34,.4);}
.at-sev{display:inline-block;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:800;
  letter-spacing:.3px;white-space:nowrap;}
.at-sev-critical{background:rgba(248,81,73,.16);color:#f85149;}
.at-sev-high{background:rgba(210,153,34,.14);color:#d29922;}
.at-val{white-space:nowrap;font-size:11.5px;}
.at-rail-more{margin-top:6px;color:var(--ink-3);font-size:11.5px;}
.at-rail-empty{color:var(--ink-2);font-size:12.5px;}
.at-dismiss{color:var(--ink-3);text-decoration:none;font-weight:700;padding:0 4px;}
.at-dismiss:hover{color:#f85149;}
.at-dismiss-all{margin-left:auto;font-size:11px;font-weight:700;color:var(--ink-3);
  text-decoration:none;border:1px solid var(--line-2);border-radius:9px;padding:2px 9px;}
.at-dismiss-all:hover{color:var(--ink);border-color:var(--ink-3);}
.at-chips-lbl{font-size:10.5px;color:var(--ink-3);margin-right:6px;text-transform:uppercase;
  letter-spacing:.4px;}
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
    return (f'<a class="at-sym" href="/dash/stock?sym={_esc(sym)}">{_esc(sym)}</a>')


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


_VAL_GLYPH = {
    "risk":        '<span class="at-val" style="color:#f85149">▼ risk</span>',
    "opportunity": '<span class="at-val" style="color:#3fb950">▲ opp</span>',
    "neutral":     '<span class="at-val" style="color:var(--ink-3)">· —</span>',
}


def render_alert_rail(alerts: list[dict], count: dict, *, window_days: int,
                      anchor: str | None, limit: int = 24, promoted_ever: bool = True,
                      interactive: bool = True, active_sev: str | None = None,
                      active_val: str | None = None, as_of_param: str = "") -> str:
    """The alert rail — the bus's 4th face: the curated, multi-day, severity-graded set of
    the highest-impact state-changes, edge-triggered (each fires once). Distinct from the
    single-batch queue below and the per-viewer 'since you last looked' brief above it.
    Pure over its inputs (hermetically testable). '' is never returned — an empty rail is
    stated honestly (a quiet rail is a quiet rail). `interactive` (LIVE view only, never a
    replay) adds the dismiss controls — server-side ack turns the rail into a triage inbox.
    `active_sev`/`active_val` are the current triage filters; `alerts` is already filtered."""
    total = int(count.get("total") or 0)                        # UNFILTERED window total
    by = count.get("by_severity") or {}
    byv = count.get("by_valence") or {}
    crit, high = int(by.get("critical") or 0), int(by.get("high") or 0)
    risk_n, opp_n = int(byv.get("risk") or 0), int(byv.get("opportunity") or 0)
    filtered = bool(active_sev or active_val)
    badges = []
    if crit:
        badges.append(f'<span class="at-badge crit">{crit} critical</span>')
    if high:
        badges.append(f'<span class="at-badge high">{high} high</span>')
    dismiss_all = ('<a class="at-dismiss-all" href="/dash/attention/ack?all=1">✓ dismiss all</a>'
                   if interactive and total else "")
    head = ('<div class="at-rail-h">🔔 Alert rail '
            + (f'<span class="at-badge">{total} active</span>' if total else "")
            + "".join(badges) + dismiss_all + '</div>')
    sub = (f'<div class="at-rail-sub">The highest-impact state-changes over the last '
           f'{window_days} days, each surfaced once — kept as they roll past today’s '
           f'batch. A <b>state-change, never a recommendation</b>; the <i>valence</i> tag '
           f'(risk / opportunity) reads the direction of the change, not what to do.</div>')

    def _qs(sev, val):
        parts = []
        if as_of_param:
            parts.append(f"as_of={_esc(str(as_of_param))}")
        if sev:
            parts.append(f"asev={sev}")
        if val:
            parts.append(f"aval={val}")
        return "/dash/attention" + ("?" + "&".join(parts) if parts else "")

    def _chip(label, href, on):
        return f'<a class="at-chip{" on" if on else ""}" href="{href}">{label}</a>'

    chips = ""
    if total:   # only offer filters when the (unfiltered) rail has alerts to narrow
        sev_c = (_chip("All", _qs(None, active_val), not active_sev)
                 + _chip(f"Critical{f' {crit}' if crit else ''}", _qs("critical", active_val),
                         active_sev == "critical")
                 + _chip(f"High{f' {high}' if high else ''}", _qs("high", active_val),
                         active_sev == "high"))
        val_c = (_chip("All", _qs(active_sev, None), not active_val)
                 + _chip(f"▼ Risk{f' {risk_n}' if risk_n else ''}", _qs(active_sev, "risk"),
                         active_val == "risk")
                 + _chip(f"▲ Opp{f' {opp_n}' if opp_n else ''}", _qs(active_sev, "opportunity"),
                         active_val == "opportunity"))
        chips = ('<div class="at-chips" style="margin-top:2px">'
                 '<span class="at-chips-lbl">severity</span>' + sev_c
                 + '<span class="at-chips-lbl" style="margin-left:12px">read</span>' + val_c
                 + '</div>')

    if not alerts:
        if filtered:
            flabel = " ".join(x for x in (active_sev, active_val) if x)
            msg = (f'No <b>{_esc(flabel)}</b> alerts in the window — clear the filter above, '
                   f'or see the full tape below.')
        else:
            msg = ('✓ No high-impact alerts in the window (only genuinely notable changes are '
                   'promoted here — the full tape is the queue below).' if promoted_ever else
                   'The rail seeds on the nightly bus run (chain step 60) — no alerts have been '
                   'promoted on this host yet. The full tape is the queue below.')
        return ('<div class="at-rail">' + head + sub + chips
                + f'<div class="at-rail-empty">{msg}</div></div>')
    rows = []
    for a in alerts[:limit]:
        sev = a.get("severity") or "high"
        val = _VAL_GLYPH.get(a.get("valence") or "neutral", _VAL_GLYPH["neutral"])
        fr, to = a.get("from_state"), a.get("to_state")
        change = (f'<span class="at-state">{_esc(str(fr))}</span> '
                  f'<span class="at-arrow">→</span> '
                  f'<span class="at-state">{_esc(str(to))}</span>'
                  if fr is not None else f'<span class="at-state">{_esc(str(to or "—"))}</span>')
        dismiss = (f'<td class="num"><a class="at-dismiss" title="dismiss" '
                   f'href="/dash/attention/ack?id={int(a.get("id") or 0)}">✕</a></td>'
                   if interactive else "")
        rows.append(
            f'<tr><td><span class="at-sev at-sev-{_esc(sev)}">{_esc(sev.upper())}</span></td>'
            f'<td>{val}</td>'
            f'<td>{_sym_cell(a)}</td>'
            f'<td>{_lens_chip(a.get("lens") or "")}</td>'
            f'<td class="at-noteline">{_esc(a.get("note") or "")}</td>'
            f'<td>{change}</td>'
            f'<td class="num" style="color:var(--ink-3);white-space:nowrap">'
            f'{_esc(str(a.get("as_of") or ""))}</td>{dismiss}</tr>')
    dcol = '<th></th>' if interactive else ""
    head_row = ('<tr><th>Severity</th><th>Read</th><th>Symbol</th><th>Lens</th>'
                f'<th>Note</th><th>From → To</th><th style="text-align:right">as_of</th>{dcol}</tr>')
    shown = min(len(alerts), limit)
    show_note = (f'<div class="at-rail-more">Showing {shown} of {len(alerts)} '
                 + (f'<b>{_esc(" ".join(x for x in (active_sev, active_val) if x))}</b> ' if filtered else "")
                 + f'alert(s){f" (of {total} active)" if filtered else ""}'
                 + (' — dismiss some, or narrow with the filters above' if len(alerts) > limit
                    else '') + '</div>') if (len(alerts) > limit or filtered) else ""
    return ('<div class="at-rail">' + head + sub + chips
            + f'<table class="at">{head_row}{"".join(rows)}</table>' + show_note + '</div>')


def render_since_last_looked(new_events: list[dict], since_ts: str | None,
                             *, first_visit: bool, limit: int = 15) -> str:
    """The 'since you last looked' brief — events DETECTED after the viewer's last visit,
    newest first, ACROSS batches (distinct from the impact-ranked current-batch queue below).
    Reads the bus's purpose-built events_since feed. first_visit (no/!valid cookie) → a gentle
    intro, never a fake '0 new'. Pure over its inputs so the whole brief is hermetically tested."""
    if first_visit:
        return ('<div class="at-seen at-seen-new">👋 <b>First visit.</b> The live tape is '
                'below. Next time, this strip shows only what changed <i>since you last '
                'looked</i> — your last visit is remembered in a browser cookie (a timestamp, '
                'nothing more), never server-side.</div>')
    if not new_events:
        return (f'<div class="at-seen at-seen-none">✓ <b>All caught up</b> — nothing new '
                f'since your last visit (<span class="at-state">{_esc(str(since_ts or ""))}'
                f'</span> UTC).</div>')
    rows = []
    for e in new_events[:limit]:
        rows.append(
            f'<tr><td>{_sym_cell(e)}</td><td>{_lens_chip(e.get("lens") or "")}</td>'
            f'<td class="at-noteline">{_esc(e.get("note") or "")}</td>'
            f'<td class="num" style="color:var(--ink-3);white-space:nowrap">'
            f'{_esc(str(e.get("as_of") or ""))}</td></tr>')
    more = (f'<div class="at-seen-more">+ {len(new_events) - limit} more new — see the full '
            f'tape below</div>' if len(new_events) > limit else "")
    return (f'<div class="at-seen at-seen-new">🆕 <b>{len(new_events)} new</b> since your '
            f'last visit (<span class="at-state">{_esc(str(since_ts or ""))}</span> UTC), '
            f'newest first:<table class="at" style="margin-top:8px"><tbody>'
            f'{"".join(rows)}</tbody></table>{more}</div>')


@router.get("/dash/attention", response_class=HTMLResponse)
def attention_page(request: Request, as_of: str = "", lens: str = "",
                   asev: str = "", aval: str = "") -> HTMLResponse:
    body = [_CSS, ifx.readability_css()]
    served: str | None = None
    seen_stamp: str | None = None      # write-back cookie value = the latest detected_at
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
                + ifx.bottom_line(
                    '<b>What changed that deserves a look</b>: every lens\'s state-changes in one '
                    'tape, ranked by <b>size of the move, then how fresh it is</b> — with the raw '
                    'before → after kept beside each verdict. A <b>triage queue</b>, never a to-do '
                    'list or a signal.')
                + ifx.how_to_read_link()
                + '<div class="at-note">The signal-event bus in one tape: every lens emits a '
                'TYPED state-change — MEP phase flips, credibility steps, F&amp;O quadrant '
                'flips, index RS-band flips, bulk/block prints — and this queue ranks the '
                'current batch by <b>impact (magnitude), then recency</b>. Every row keeps '
                'the raw before → after beside the verdict (data-first), and every event '
                'carries the date it is computed <i>for</i> (<code>as_of</code>, point-in-'
                'time honest). An event is a <b>state-change, never a recommendation</b>. '
                '<a href="/dash/glossary?q=attention">glossary →</a></div>')
            # --- alert rail (the bus's 4th face): the curated, multi-day, severity-graded
            # set of the highest-impact changes, anchored to the SERVED batch so a replay
            # windows on that date. Rendered for live AND replay; empty state is honest. ---
            if served and (st.get("events") or 0) > 0:
                a_sev = asev.strip().lower() if asev.strip().lower() in SA.SEVERITIES else None
                a_val = aval.strip().lower() if aval.strip().lower() in SA.VALENCES else None
                # full filtered set (window ≤ few hundred) — render caps the display + counts "+more"
                rail_alerts = SA.active_alerts(conn, within_days=7, limit=1000, as_of=served,
                                               sev=a_sev, val=a_val)
                rail_count = SA.active_count(conn, within_days=7, as_of=served)   # UNFILTERED badge
                ever = (SA.stats(conn).get("alerts") or 0) > 0    # table populated at all?
                body.append(render_alert_rail(rail_alerts, rail_count, window_days=7,
                                              anchor=served, limit=24, promoted_ever=ever,
                                              interactive=not requested,  # no dismiss on a replay
                                              active_sev=a_sev, active_val=a_val,
                                              as_of_param=(requested or "")))
            # --- "since you last looked" brief (LIVE view only; a replay is a historical
            # read, not a visit) — reuses the bus's events_since feed, keyed on a client
            # cookie. Compute against the OLD cookie, then stamp the cookie to now. ---
            if not requested and (st.get("events") or 0) > 0:
                seen_stamp = conn.execute(
                    "SELECT MAX(detected_at) FROM signal_events").fetchone()[0]
                cookie_val = request.cookies.get(_SEEN_COOKIE)
                valid = bool(cookie_val and _TS_RE.match(cookie_val))
                new_ev = SE.events_since(conn, cookie_val, limit=200) if valid else []
                body.append(render_since_last_looked(
                    new_ev, cookie_val if valid else None, first_visit=not valid))
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
    resp = HTMLResponse(_shell("Attention · patearn", "".join(body),
                               "attention", str(served or "")[:10], wide=True))
    if seen_stamp:      # remember THIS visit so the next one is incremental (1yr, /dash-scoped)
        resp.set_cookie(_SEEN_COOKIE, seen_stamp, max_age=31_536_000,
                        samesite="lax", path="/dash")
    return resp


@router.get("/dash/attention/ack")
def attention_ack(request: Request) -> RedirectResponse:
    """Dismiss one alert (?id=N) or every active alert in the current window (?all=1). The
    ONLY web-layer write in this face — a single quick UPDATE on an explicit analyst click
    (server-side / global, since there is one analyst). Turns the rail into a triage inbox:
    dismissed alerts leave the rail (they remain in signal_events + the queue). 303 back to
    the rail. Defensive — a failed ack degrades to a plain redirect, never a 500."""
    try:
        with get_conn() as conn:
            if request.query_params.get("all"):
                SA.acknowledge_all(conn, within_days=7)
            else:
                aid = (request.query_params.get("id") or "").strip()
                if aid.isdigit():
                    SA.acknowledge(conn, int(aid))
    except Exception:  # noqa: BLE001
        pass
    return RedirectResponse("/dash/attention", status_code=303)


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
