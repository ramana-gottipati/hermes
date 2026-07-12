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

from src.core.db import DB_PATH
from src.web.dashboard import _esc
from src.web import infographics as ifx

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

    os.remove(tmp)
    print("seasonal_events_view selftest OK — honest-empty on missing table/entity; lane/card/section "
          "render OVERDUE(+week count)/ON_TIME/PENDING(+band)/no-history correctly; descriptive-only "
          "TIME-only fence text present; stock-scope-only enforced")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
