"""seasonal_events_view — descriptive-factual EVENT-CADENCE lens (companion render layer for the
standalone src/automation/seasonal_events.py engine). Reads ONLY the bounded `seasonal_events`
snapshot table; NEVER computes on-demand, NEVER writes hermes.db. TIME-only (weeks) — no price, no
expected-move — per the descriptive-only fence carried through every render below:

    "Event TIMING vs this company's OWN cadence + exchange-declared meetings — factual, NOT a
     price prediction."

Embedded into /dash/seasonal-tape (scope='stock' only — the engine keys seasonal_events by
tradeable EQ symbol, not index/sector) via render_events_section(); a smaller event_cadence_card()
is available for other stock-detail embeds. Every read is table/entity-exists-guarded: a missing
table or an uncovered symbol degrades to '' (honest-empty), never an exception, matching the house
pattern used throughout seasonal_view.py.
"""
from __future__ import annotations

import calendar
import sqlite3
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.core.db import DB_PATH
from src.web.dashboard import _esc
from src.web import infographics as ifx

router = APIRouter()

try:
    from src.automation.seasonal_events import EVENT_TYPES
except Exception:  # noqa: BLE001 — guarded import; a changed/absent engine must never break the page
    EVENT_TYPES = ["RESULTS", "DIVIDEND", "BONUS", "SPLIT", "AGM", "OTHER_CA"]

_DB_PATH = str(DB_PATH)                              # overridable in _selftest (read-only)

_FISCAL_ORDER = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
_CAL_ORDER = list(range(1, 13))
_MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
_EVT_LABEL = {"RESULTS": "Results", "DIVIDEND": "Dividend", "BONUS": "Bonus",
              "SPLIT": "Split", "AGM": "AGM", "OTHER_CA": "Other CA"}
_STATUS_LABEL = {"ON_TIME": "on time", "EARLY": "early", "LATE": "late", "OVERDUE": "overdue",
                 "PENDING": "pending", "NO_HISTORY": "no history"}

_EVT_CSS = """
<style>
.sev-card{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;
  padding:14px 16px;margin:0 0 15px;max-width:1120px;}
.sev-card .sev-h{font-size:14px;font-weight:700;margin:0 0 6px;color:var(--ink);}
.sev-rows{display:flex;flex-direction:column;gap:4px;margin-top:4px;}
.sev-row{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--ink-2);}
.sev-row .k{width:74px;color:var(--ink);font-weight:600;flex:none;}
.sev-row .ov{color:var(--down);font-weight:700;}
.sev-fence{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.06);
  border-radius:0 10px 10px 0;padding:9px 13px;margin:8px 0 0;font-size:11.5px;
  color:var(--ink-2);line-height:1.5;max-width:1080px;}
.sev-fence b{color:var(--ink);}
/* cross-entity event-cadence page */
.evc-sum{display:flex;gap:22px;flex-wrap:wrap;margin:8px 0 4px;font-size:12.5px;color:var(--ink-2);}
.evc-sum b{color:var(--ink);font-size:15px;font-variant-numeric:tabular-nums;}
.evc-ctrl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0;}
.evc-ctrl .lbl{font-size:11px;color:var(--ink-3);margin-right:2px;}
.evc-ctrl a{font-size:12px;padding:3px 9px;border:1px solid var(--line);border-radius:20px;
  color:var(--ink-2);text-decoration:none;}
.evc-ctrl a.on{background:var(--accent);color:#fff;border-color:var(--accent);}
.evc-h2{font-size:13px;font-weight:700;color:var(--ink);margin:16px 0 6px;}
.evc-tbl{border-collapse:collapse;width:100%;max-width:1120px;font-size:12.5px;}
.evc-tbl th{text-align:left;color:var(--ink-3);font-weight:600;font-size:11px;
  border-bottom:1px solid var(--line);padding:5px 10px 5px 0;}
.evc-tbl td{padding:5px 10px 5px 0;border-bottom:1px solid var(--line-2,rgba(127,127,127,.12));
  color:var(--ink-2);font-variant-numeric:tabular-nums;}
.evc-tbl td.sym a{color:var(--accent);text-decoration:none;font-weight:600;}
.evc-tbl td.ov{color:var(--down);font-weight:700;}
.evc-empty{font-size:12.5px;color:var(--ink-3);padding:8px 0;}
</style>
"""


def _ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    return con


def _load_events_snapshot(entity: str, db_path: str, asof: str | None = None) -> dict | None:
    """{'symbol','asof','events':{event_type:row-dict}} for the latest (or a given) `asof`
    snapshot, or None when the table/entity has no rows — honest-empty, never fabricated."""
    try:
        con = _ro(db_path)
    except sqlite3.OperationalError:
        return None
    try:
        if not con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='seasonal_events'").fetchone():
            return None
        if asof:
            use_asof = asof
        else:
            row = con.execute(
                "SELECT MAX(asof) FROM seasonal_events WHERE symbol=?", (entity,)).fetchone()
            use_asof = row[0] if row else None
        if not use_asof:
            return None
        rows = con.execute(
            "SELECT event_type, status, variance_weeks, anchor, anchor_basis, lo, hi, mu_date, "
            "sigma_days, k, n, n_history, modeled FROM seasonal_events WHERE symbol=? AND asof=?",
            (entity, use_asof)).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not rows:
        return None
    return {"symbol": entity, "asof": use_asof, "events": {r["event_type"]: dict(r) for r in rows}}


def _month_frac(iso: str | None, order: list) -> float | None:
    """Fractional x-position (0..1) of an ISO date along `order` (a 12-month calendar sequence)."""
    if not iso or len(iso) < 10:
        return None
    try:
        y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    except ValueError:
        return None
    if m not in order:
        return None
    idx = order.index(m)
    try:
        dim = calendar.monthrange(y, m)[1]
    except Exception:  # noqa: BLE001
        dim = 30
    return (idx + (d - 1) / max(dim, 1)) / len(order)


def event_cadence_lane(payload: dict | None, order: list, cal: str, w: int = 1100) -> str:
    """One horizontal calendar-axis row per EVENT_TYPES. A SOLID triangle marks a real actual
    occurrence this cycle (ON_TIME/EARLY/LATE, not itself a modelled fallback date); a HOLLOW,
    dashed@60%-opacity marker means the anchor is either MODELED (no filed date captured — e.g. the
    concalls period-label month-end fallback) or a still-open PROJECTED window (drawn over its
    faint lo..hi band); a red ⚠ + a signed week count marks OVERDUE; a row greys out entirely on
    NO_HISTORY (fewer than the engine's min_hist occurrences and no declared anchor) — never faked
    as present. `cal`/`order` align the shared x-axis to the SAME Apr-Mar/Jan-Dec toggle as the
    rest of /dash/seasonal-tape."""
    events = (payload or {}).get("events", {})
    rows_n = len(EVENT_TYPES)
    top, row_h = 22, 28
    h = top + row_h * rows_n + 6
    lbl_w = 80
    pw = w - lbl_w - 10

    def X(frac: float) -> float:
        return lbl_w + frac * pw

    out = [f'<svg viewBox="0 0 {w} {h}" class="ifx sev-lane" role="img" '
           f'preserveAspectRatio="xMidYMid meet" style="max-width:100%;height:auto">',
           '<style>'
           '.sev-tri{stroke:var(--ink-2);stroke-width:1;}'
           '.sev-tri.solid{fill:var(--accent);}'
           '.sev-tri.hollow{fill:var(--bg-1);stroke-dasharray:2 2;opacity:.6;}'
           '.sev-band{fill:var(--accent);opacity:.10;}'
           '.sev-axis{stroke:var(--line-2);stroke-width:.6;}'
           '.sev-mlbl{fill:var(--ink-3);font-size:9px;}'
           '.sev-rlbl{fill:var(--ink);font-size:11px;font-weight:600;}'
           '.sev-rlbl.dim{fill:var(--ink-4);font-style:italic;font-weight:400;}'
           '.sev-ov{fill:var(--down);font-size:10px;font-weight:700;}'
           '.sev-nh{fill:var(--ink-4);font-size:10px;font-style:italic;}'
           '</style>']
    for i, m in enumerate(order):
        x = X(i / len(order))
        out.append(f'<line x1="{x:.1f}" y1="{top-6}" x2="{x:.1f}" y2="{h-4}" class="sev-axis"/>')
        out.append(f'<text x="{x+2:.1f}" y="{top-9}" class="sev-mlbl">{_MONTH_ABBR[m]}</text>')
    for i, et in enumerate(EVENT_TYPES):
        y = top + i * row_h + row_h / 2
        ev = events.get(et)
        status = (ev or {}).get("status") or "NO_HISTORY"
        no_hist = (not ev) or status == "NO_HISTORY"
        rlbl_cls = "sev-rlbl dim" if no_hist else "sev-rlbl"
        out.append(f'<text x="0" y="{y+4:.1f}" class="{rlbl_cls}">{_esc(_EVT_LABEL.get(et, et))}</text>')
        if no_hist:
            out.append(f'<text x="{lbl_w+4}" y="{y+4:.1f}" class="sev-nh">no history</text>')
            continue
        lo_f = _month_frac(ev.get("lo"), order)
        hi_f = _month_frac(ev.get("hi"), order)
        anchor_f = _month_frac(ev.get("anchor"), order)
        if lo_f is not None and hi_f is not None and status == "PENDING":
            x0, x1 = X(lo_f), X(hi_f)
            if x1 < x0:      # window straddles the calendar-axis seam — draw to the right edge
                x1 = w - 4
            out.append(f'<rect x="{x0:.1f}" y="{y-8:.1f}" width="{max(x1-x0,2):.1f}" height="16" '
                       f'class="sev-band"/>')
        if anchor_f is not None:
            x = X(anchor_f)
            pts = f"{x:.1f},{y-7:.1f} {x-6:.1f},{y+6:.1f} {x+6:.1f},{y+6:.1f}"
            modeled = bool(ev.get("modeled"))
            solid = status in ("ON_TIME", "EARLY", "LATE") and not modeled
            cls = "sev-tri " + ("solid" if solid else "hollow")
            tip = f'{_esc(et)} · {_esc(_STATUS_LABEL.get(status, status))}'
            out.append(f'<polygon points="{pts}" class="{cls}"><title>{tip}</title></polygon>')
        if status == "OVERDUE":
            vw = ev.get("variance_weeks")
            vw_txt = f'{vw:+.1f}w' if vw is not None else "?"
            out.append(f'<text x="{w-4:.1f}" y="{y+4:.1f}" text-anchor="end" class="sev-ov">'
                       f'⚠ {_esc(vw_txt)}</text>')
    out.append("</svg>")
    return "".join(out)


def event_cadence_card(scope: str, entity: str, *, db_path: str | None = None,
                       asof: str | None = None) -> str:
    """Compact per-event-type list for embedding elsewhere (e.g. a stock detail page): status +
    signed week variance, factual TIME only. '' honest-empty when uncovered/wrong scope — a silent
    no-op for the caller. Reads ONLY the seasonal_events snapshot, never computes on-demand."""
    if scope != "stock":
        return ''
    path = db_path or _DB_PATH
    payload = _load_events_snapshot(entity, path, asof=asof)
    if not payload:
        return ''
    lines = []
    for et in EVENT_TYPES:
        ev = payload["events"].get(et)
        status = (ev or {}).get("status")
        if not ev or status in (None, "NO_HISTORY"):
            continue
        vw = ev.get("variance_weeks")
        vw_txt = f'{vw:+.1f}w' if vw is not None else '—'
        cls = ' class="ov"' if status == "OVERDUE" else ''
        lines.append(f'<div class="sev-row"><span class="k">{_esc(_EVT_LABEL.get(et, et))}</span>'
                     f'<span{cls}>{_esc(_STATUS_LABEL.get(status, status))} ({_esc(vw_txt)})</span></div>')
    if not lines:
        return ''
    return (
        _EVT_CSS
        + '<div class="sev-card"><div class="sev-h">Event cadence '
          '<small style="font-weight:400;color:var(--ink-3);font-size:11px">timing vs own '
          'history</small></div>'
        + f'<div class="sev-rows">{"".join(lines)}</div>'
        + '<div class="sev-fence"><b>Factual, not predictive:</b> timing vs this company’s own '
          'cadence + exchange-declared meetings — never a price signal.</div>'
        + '</div>')


def render_events_section(scope: str, entity: str, cal: str, *, db_path: str | None = None) -> str:
    """Full event-cadence lens section — appended on /dash/seasonal-tape for scope='stock' after
    the 25-year stack grid. '' honest-empty (wrong scope / not populated / engine unavailable) —
    never fabricates a lane, never raises (the caller in seasonal_view.py guards this import too)."""
    if scope != "stock":
        return ''
    path = db_path or _DB_PATH
    payload = _load_events_snapshot(entity, path)
    if not payload:
        return ''
    order = _CAL_ORDER if cal == "cy" else _FISCAL_ORDER
    lane = event_cadence_lane(payload, order, cal, w=1100)
    return (
        _EVT_CSS
        + '<div class="sev-card"><div class="sev-h">Event cadence '
          '<small style="font-weight:400;color:var(--ink-3);font-size:11px">RESULTS / DIVIDEND / '
          'BONUS / SPLIT / AGM / other corp actions — when they actually happen vs this '
          'company’s own history</small></div>'
        + ifx.plain('Each row is one event type. A <b>solid triangle</b> marks a real occurrence '
                    'this cycle; a <b>hollow, dashed</b> marker means the date is modelled (no filed '
                    'date captured) or still a forward projection (drawn over its faint expected '
                    'window); <b>⚠ red</b> = the expected window has passed with nothing filed '
                    'yet — overdue.')
        + lane
        + '<div class="sev-fence"><b>Read this honestly:</b> Event <b>TIMING</b> vs this '
          'company’s <b>own</b> cadence + exchange-declared board meetings — '
          '<b>factual</b>, <b>NOT</b> a price prediction. No forward-return or price-move number is '
          'computed anywhere in this section.</div>'
        + '</div>')


# ── cross-entity EVENT-CADENCE lens: /dash/event-cadence ─────────────────────────────────────────
# The ADDITIVE cut the two ANNOUNCED calendars structurally cannot show: which LIVE names are OVERDUE
# vs their OWN historical rhythm (expected-but-silent), and what each is next EXPECTED by cadence.
# Reads ONLY the bounded seasonal_events snapshot; TIME-only; anchor_basis='projection' ONLY — so
# declared/announced events (served by /dash/actions ex-dates + /dash/results-reactions board
# meetings) are NEVER duplicated here (sister-data check, SURFACE-PLAYBOOK §2).
_IDX_MAP = {"all": None, "n50": "Nifty 50", "n100": "Nifty 100", "n500": "Nifty 500"}
_IDX_LABEL = [("all", "All liquid"), ("n50", "Nifty 50"), ("n100", "Nifty 100"), ("n500", "Nifty 500")]
_EVT_KEYS = ["all", "RESULTS", "DIVIDEND", "BONUS", "SPLIT", "AGM", "OTHER_CA"]


def _latest_members(con: sqlite3.Connection, idx_name: str) -> set | None:
    """Current constituents of `idx_name` (latest snapshot) — None on any error (→ no filter)."""
    try:
        row = con.execute("SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name=?",
                          (idx_name,)).fetchone()
        if not row or not row[0]:
            return None
        return {r[0] for r in con.execute(
            "SELECT symbol FROM stock_index_membership WHERE index_name=? AND snapshot_date=?",
            (idx_name, row[0]))}
    except sqlite3.Error:
        return None


def _evc_rows(con: sqlite3.Connection, *, overdue: bool, evt: str, members: set | None,
              cap: int, horizon: int, today: str) -> list:
    """OVERDUE (bounded to `cap` weeks — beyond is 'stopped', not late) or EXPECTED-by-cadence
    (projection window overlapping [today, today+horizon]). projection basis ONLY (no announced)."""
    where = ["asof=(SELECT MAX(asof) FROM seasonal_events)", "anchor_basis='projection'"]
    args: list = []
    if overdue:
        where += ["status='OVERDUE'", "variance_weeks >= ?"]; args.append(-abs(cap))
    else:
        where += ["status='PENDING'", "hi >= ?", "lo <= date(?, ?)"]
        args += [today, today, f"+{int(horizon)} days"]
    if evt != "all":
        where.append("event_type=?"); args.append(evt)
    order = "variance_weeks ASC" if overdue else "anchor ASC, symbol ASC"
    rows = [dict(r) for r in con.execute(
        "SELECT symbol, event_type, variance_weeks, anchor, lo, hi, n_history "
        f"FROM seasonal_events WHERE {' AND '.join(where)} ORDER BY {order} LIMIT 400", args)]
    return [r for r in rows if members is None or r["symbol"] in members]


def render_event_cadence(evt: str = "all", idx: str = "all", cap: int = 52, horizon: int = 60,
                         fmt: str = "html", db_path: str | None = None):
    """The cross-entity event-cadence lens (HTMLResponse for fmt='html', CSV str for fmt='csv').
    Honest-empty everywhere the snapshot is absent — never fabricates, never raises."""
    path = db_path or _DB_PATH
    evt = evt if evt in _EVT_KEYS else "all"
    idx = idx if idx in _IDX_MAP else "all"
    try:
        cap = max(1, min(260, int(cap)))
    except (TypeError, ValueError):
        cap = 52
    try:
        horizon = max(7, min(180, int(horizon)))
    except (TypeError, ValueError):
        horizon = 60
    today = date.today().isoformat()
    over, exp, dormant = [], [], 0
    try:
        con = _ro(path)
    except sqlite3.OperationalError:
        con = None
    if con is not None:
        try:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                           "AND name='seasonal_events'").fetchone():
                idx_name = _IDX_MAP.get(idx)
                members = _latest_members(con, idx_name) if idx_name else None
                over = _evc_rows(con, overdue=True, evt=evt, members=members, cap=cap,
                                 horizon=horizon, today=today)
                exp = _evc_rows(con, overdue=False, evt=evt, members=members, cap=cap,
                                horizon=horizon, today=today)
                d = con.execute(
                    "SELECT COUNT(*) FROM seasonal_events WHERE asof=(SELECT MAX(asof) FROM "
                    "seasonal_events) AND status='OVERDUE' AND anchor_basis='projection' "
                    "AND variance_weeks < ?", (-abs(cap),)).fetchone()
                dormant = d[0] if d else 0
        except sqlite3.Error:
            pass
        finally:
            con.close()

    if fmt == "csv":  # CSV honors the same filters (playbook §8b)
        out = ["section,symbol,event,weeks_overdue,expected_anchor,window_lo,window_hi,times_seen"]
        for r in over:
            out.append(f"overdue,{r['symbol']},{_EVT_LABEL.get(r['event_type'], r['event_type'])},"
                       f"{abs(r['variance_weeks'] or 0):.1f},,{r['lo'] or ''},{r['hi'] or ''},"
                       f"{r['n_history'] or 0}")
        for r in exp:
            out.append(f"expected,{r['symbol']},{_EVT_LABEL.get(r['event_type'], r['event_type'])},"
                       f",{r['anchor'] or ''},{r['lo'] or ''},{r['hi'] or ''},{r['n_history'] or 0}")
        return "\n".join(out) + "\n"

    def _u(evt2=evt, idx2=idx, cap2=cap, hz2=horizon):
        return f"/dash/event-cadence?evt={evt2}&idx={idx2}&cap={cap2}&horizon={hz2}"

    evt_chips = "".join(
        f'<a class="{"on" if evt == k else ""}" href="{_u(evt2=k)}">'
        f'{"All" if k == "all" else _EVT_LABEL.get(k, k)}</a>' for k in _EVT_KEYS)
    idx_chips = "".join(
        f'<a class="{"on" if idx == k else ""}" href="{_u(idx2=k)}">{lbl}</a>' for k, lbl in _IDX_LABEL)

    def _row(r, kind):
        sym = f'<td class="sym"><a href="/dash/stock?sym={quote(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
        evtc = f'<td>{_EVT_LABEL.get(r["event_type"], r["event_type"])}</td>'
        seen = f'<td>{r["n_history"] or 0}</td>'
        win = f'<td>{_esc(r["lo"] or "—")} → {_esc(r["hi"] or "—")}</td>'
        if kind == "over":
            return (f'<tr>{sym}{evtc}<td class="ov">{abs(r["variance_weeks"] or 0):.0f} wk</td>'
                    f'{win}{seen}</tr>')
        return f'<tr>{sym}{evtc}<td>{_esc(r["anchor"] or "—")}</td>{win}{seen}</tr>'

    def _table(rows, kind, cols, empty):
        if not rows:
            return f'<div class="evc-empty">{empty}</div>'
        head = "".join(f"<th>{c}</th>" for c in cols)
        return (f'<div style="overflow-x:auto"><table class="evc-tbl"><thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(_row(r, kind) for r in rows)}</tbody></table></div>')

    from src.web.dashboard import _shell  # lazy — seasonal_events_view is imported by dashboard
    bl = (f"Which liquid companies are <b>past their own typical window</b> for an event with nothing "
          f"filed yet (<b>{len(over)}</b> overdue ≤{cap} wk), and what each is next <b>expected</b> by "
          f"its historical rhythm (<b>{len(exp)}</b> due within {horizon} days). Event TIMING vs a "
          "company's OWN cadence — <b>never a price call</b>, and NOT a confirmed date.")
    body = [
        _EVT_CSS,
        '<h2 style="margin:0 0 2px">Event cadence <small style="color:var(--ink-3);font-size:12px;'
        'font-weight:400">who&rsquo;s overdue or due for results / dividends — vs each company&rsquo;s '
        'own rhythm</small></h2>',
        ifx.bottom_line(bl),
        ifx.how_to_read_link(),
        f'<div class="evc-ctrl"><span class="lbl">event</span>{evt_chips}</div>',
        f'<div class="evc-ctrl"><span class="lbl">universe</span>{idx_chips}</div>',
        '<div class="evc-sum">'
        f'<span><b>{len(over)}</b> overdue</span><span><b>{len(exp)}</b> expected soon</span>'
        + (f'<span style="color:var(--ink-4)">+{dormant} long-dormant hidden (&gt;{cap} wk = stopped)</span>'
           if dormant else '')
        + f'<span style="margin-left:auto"><a href="{_u()}&format=csv" style="color:var(--accent);'
          'text-decoration:none">Download CSV ↓</a></span></div>',
        '<div class="evc-h2">⚠ Overdue vs its own rhythm</div>',
        ifx.plain('Each name is <b>past the window it usually files this event in</b> (its own history) '
                  f'and nothing is filed yet. Bounded to ≤{cap} weeks — anything longer is treated as '
                  '<b>stopped</b>, not late, and hidden. A rhythm flag, <b>not</b> a confirmed delay — '
                  'schedules legitimately shift.'),
        _table(over, "over", ("Symbol", "Event", "Overdue by", "Its usual window", "Times seen"),
               "No liquid name is recently overdue in this filter — nothing off its own rhythm."),
        '<div class="evc-h2">Expected next (by cadence)</div>',
        ifx.plain('The next occurrence each name is <b>due</b> based on its own spacing — an '
                  '<b>estimate from rhythm, not an announcement</b>. For CONFIRMED upcoming dates see '
                  '<a href="/dash/actions">Corp actions</a> (ex-dates) + '
                  '<a href="/dash/results-reactions">Results reactions</a> (declared board meetings).'),
        _table(exp, "exp", ("Symbol", "Event", "Expected around", "Window", "Times seen"),
               "Nothing projected in this window for this filter."),
        '<div class="sev-fence"><b>Read this honestly:</b> Event <b>TIMING</b> vs each company&rsquo;s '
        '<b>own</b> cadence — <b>factual, NOT a price prediction</b>, and <b>NOT a confirmed date</b> '
        '(a cadence estimate; many events legitimately shift). Declared/announced events are '
        'deliberately excluded here — they live on Corp actions + Results reactions.</div>',
    ]
    return HTMLResponse(_shell("Event cadence · patearn", "".join(body), "event-cadence", "", wide=True))


@router.get("/dash/event-cadence", response_class=HTMLResponse)
def dash_event_cadence(evt: str = "all", idx: str = "all", cap: int = 52, horizon: int = 60,
                       format: str = "html"):
    """Cross-entity event-cadence lens: OVERDUE vs own rhythm + EXPECTED-by-cadence. `format=csv`
    streams the same (filtered) rows as a download (playbook §8 server-side export)."""
    if format == "csv":
        return PlainTextResponse(
            render_event_cadence(evt=evt, idx=idx, cap=cap, horizon=horizon, fmt="csv"),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=event-cadence.csv"})
    return render_event_cadence(evt=evt, idx=idx, cap=cap, horizon=horizon, fmt="html")


def _selftest() -> int:
    """Offline: honest-empty on a missing/empty table; a populated synthetic snapshot renders the
    lane/card/section with the OVERDUE/ON_TIME/PENDING/no-history encodings all present."""
    import os
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "seasonal_events_view_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.close()

    # 1) no seasonal_events table at all -> every render honest-empties, never raises
    assert render_events_section("stock", "TESTSYM", "fy", db_path=tmp) == ''
    assert event_cadence_card("stock", "TESTSYM", db_path=tmp) == ''
    assert _load_events_snapshot("TESTSYM", tmp) is None

    # 2) populate a synthetic snapshot: OVERDUE (RESULTS), ON_TIME+modeled (DIVIDEND),
    #    PENDING (AGM); BONUS/SPLIT/OTHER_CA absent entirely -> must render as honest 'no history'.
    con = sqlite3.connect(tmp)
    con.executescript(
        "CREATE TABLE seasonal_events ("
        " symbol TEXT, event_type TEXT, asof TEXT, status TEXT, variance_weeks REAL,"
        " anchor TEXT, anchor_basis TEXT, lo TEXT, hi TEXT, mu_date TEXT, sigma_days REAL,"
        " k INTEGER, n INTEGER, n_history INTEGER, modeled INTEGER,"
        " computed_at TEXT NOT NULL DEFAULT (datetime('now')),"
        " PRIMARY KEY (symbol, event_type, asof));")
    asof = "2026-07-12"
    rows = [
        ("TESTSYM", "RESULTS", asof, "OVERDUE", -3.2, "2026-06-01", "projection",
         "2026-05-20", "2026-06-10", None, 7.0, 12, 12, 12, 0),
        ("TESTSYM", "DIVIDEND", asof, "ON_TIME", 0.5, "2026-08-15", "declared",
         "2026-08-10", "2026-08-20", None, 5.0, 4, 4, 4, 1),
        ("TESTSYM", "AGM", asof, "PENDING", None, "2026-09-20", "projection",
         "2026-09-05", "2026-10-05", None, 15.0, 5, 5, 5, 0),
        ("TESTSYM", "SPLIT", asof, "ON_TIME", 1.0, "2026-03-15", "projection",
         "2026-03-10", "2026-03-20", None, 4.0, 6, 6, 6, 0),
    ]
    con.executemany(
        "INSERT INTO seasonal_events (symbol,event_type,asof,status,variance_weeks,anchor,"
        "anchor_basis,lo,hi,mu_date,sigma_days,k,n,n_history,modeled) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()

    payload = _load_events_snapshot("TESTSYM", tmp)
    assert payload and payload["events"]["RESULTS"]["status"] == "OVERDUE"
    assert payload["events"].get("BONUS") is None, "unfetched event types stay absent, never faked"

    lane = event_cadence_lane(payload, _FISCAL_ORDER, "fy", w=1100)
    assert "<svg" in lane
    assert "⚠" in lane and "-3.2w" in lane, "OVERDUE warning + signed week count missing"
    assert "no history" in lane, "BONUS/SPLIT/OTHER_CA (never fetched) must render as honest no-history"
    assert "sev-band" in lane, "PENDING (AGM) must draw its faint projected window"
    assert "solid" in lane, "ON_TIME actual (non-modeled) should get a solid marker somewhere"

    section = render_events_section("stock", "TESTSYM", "fy", db_path=tmp)
    assert section and "Event cadence" in section and "<svg" in section
    assert "factual" in section.lower() and "a price prediction" in section.lower()

    card = event_cadence_card("stock", "TESTSYM", db_path=tmp)
    assert card and "overdue" in card.lower()
    assert event_cadence_card("index", "Nifty 500", db_path=tmp) == '', "events are stock-scope only"
    assert event_cadence_card("stock", "NOSUCHSYM", db_path=tmp) == '', "uncovered symbol honest-empties"

    # cross-entity Event-Cadence lens (/dash/event-cadence). CSV path (no shell) exercises the queries:
    # RESULTS OVERDUE -3.2w (projection, within the 52w cap) -> overdue section; AGM PENDING/projection
    # with an in-window future window -> expected section; the DIVIDEND row is anchor_basis='declared'
    # so it must be EXCLUDED from BOTH (announced events live on /dash/actions + results-reactions).
    csv = render_event_cadence(db_path=tmp, fmt="csv")
    assert csv.startswith("section,symbol,event"), "CSV header missing"
    assert "overdue,TESTSYM,Results" in csv, "OVERDUE projection within cap must appear"
    assert "expected,TESTSYM,AGM" in csv, "PENDING+projection in-window must appear as expected"
    assert "TESTSYM,Dividend" not in csv, "declared/announced rows must NOT be duplicated here"
    ec = render_event_cadence(db_path=tmp)  # HTMLResponse — exercises _shell + sym-links + fence
    ectxt = ec.body.decode("utf-8")
    assert "Event cadence" in ectxt and "Overdue vs its own rhythm" in ectxt
    assert "/dash/stock?sym=TESTSYM" in ectxt, "every symbol cell must sym-link (playbook §9)"
    assert "NOT a price prediction" in ectxt and "/dash/actions" in ectxt, \
        "honesty fence + cross-links to the announced calendars required"

    os.remove(tmp)
    print("seasonal_events_view selftest OK — honest-empty on missing table/entity; lane/card/section "
          "render OVERDUE(+week count)/ON_TIME/PENDING(+band)/no-history correctly; descriptive-only "
          "TIME-only fence text present; stock-scope-only enforced; cross-entity /dash/event-cadence "
          "overdue+expected sections + CSV + sym-links + declared-excluded + fence wired")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
