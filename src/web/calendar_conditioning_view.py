"""calendar_conditioning_view — DESCRIPTIVE expiry / holiday conditioning lens (X-10 render layer).

Fourth member of the seasonal `_subnav()` family (Markets · Big picture). Reads ONLY the bounded
`x_setups_signals` snapshot (module='calendar_conditioning') that the nightly
`src/automation/x_setups_signals.py` spine (S205) materialises from
`research.explosive_moves.calendar_conditioning.scan()` — the house "web reads a bounded snapshot
table" pattern (like `seasonal_view` ← `seasonal_cells`). It NEVER computes on demand and NEVER
imports the research module (numpy / venv-separated); a missing/empty snapshot degrades to an
honest-empty note, never a 500.

FENCE carried through every render: each figure is a name's mean daily return in a calendar window
(monthly-expiry day · expiry week · pre / post-holiday) MINUS its all-days mean — DESCRIPTIVE
conditioning read against `seasonal_tape`'s null prior (the estate's calendar-seasonality work was
largely **0-certified**). It is calendar CONTEXT, never a signal, ranking, or entry.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.core.db import DB_PATH
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx
from src.web import glossary as G

router = APIRouter()

_MODULE = "calendar_conditioning"
_DB_PATH = str(DB_PATH)   # overridable in _selftest (read-only)

# (json key, column label, glossary term for the header popover)
_COLS = [
    ("expiry_ret_delta",       "Expiry day",   "Monthly F&O expiry"),
    ("expiry_week_ret_delta",  "Expiry week",  "Expiry week"),
    ("pre_holiday_ret_delta",  "Pre-holiday",  "Holiday adjacency (pre / post)"),
    ("post_holiday_ret_delta", "Post-holiday", "Holiday adjacency (pre / post)"),
]
_SORT_KEYS = {k for k, _, _ in _COLS}
_DEFAULT_SORT = "pre_holiday_ret_delta"
_CSV_COLS = ["symbol", "expiry_ret_delta", "expiry_week_ret_delta", "pre_holiday_ret_delta",
             "post_holiday_ret_delta", "n_days", "n_expiry", "med_turn"]

_CSS = """
<style>
.cc-sum{display:flex;gap:20px;flex-wrap:wrap;margin:8px 0 4px;font-size:12.5px;color:var(--ink-2);}
.cc-sum b{color:var(--ink);font-variant-numeric:tabular-nums;}
.cc-ctrl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:10px 0 4px;}
.cc-ctrl .lbl{font-size:11px;color:var(--ink-3);margin-right:2px;}
.cc-ctrl a{font-size:12px;padding:3px 9px;border:1px solid var(--line);border-radius:20px;
  color:var(--ink-2);text-decoration:none;}
.cc-ctrl a.on{background:var(--accent);color:#fff;border-color:var(--accent);}
.cc-tbl{border-collapse:collapse;width:100%;max-width:1080px;font-size:12.5px;margin-top:8px;}
.cc-tbl th{text-align:right;color:var(--ink-3);font-weight:600;font-size:11px;padding:5px 9px;
  border-bottom:1px solid var(--line);white-space:nowrap;}
.cc-tbl th.sym,.cc-tbl td.sym{text-align:left;}
.cc-tbl td{padding:5px 9px;border-bottom:1px solid var(--bg-2);text-align:right;
  font-variant-numeric:tabular-nums;color:var(--ink-2);}
.cc-tbl td.sym a{color:var(--ink);text-decoration:none;font-weight:600;}
.cc-tbl td.sym a:hover{text-decoration:underline;}
.cc-up{color:var(--up);}
.cc-dn{color:var(--down);}
.cc-z{color:var(--ink-3);}
.cc-dl{margin:12px 0 0;font-size:12px;}
.cc-dl a{color:var(--accent);text-decoration:none;}
.cc-empty{border:1px dashed var(--line);border-radius:12px;padding:18px 20px;margin:14px 0;
  color:var(--ink-3);font-size:12.5px;max-width:1000px;}
.cc-fence{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.06);
  border-radius:0 10px 10px 0;padding:9px 13px;margin:12px 0 0;font-size:11.5px;
  color:var(--ink-2);line-height:1.5;max-width:1040px;}
.cc-fence b{color:var(--ink);}
</style>
"""


def _ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)


def _load(db_path=None):
    """(rows, asof) from the bounded x_setups_signals snapshot, rank-ordered; (None, '') if the
    table/snapshot is absent, empty, or unreadable (honest-empty — never raises)."""
    try:
        con = _ro(db_path or _DB_PATH)
        con.row_factory = sqlite3.Row
        try:
            rows = [json.loads(r["payload"]) for r in con.execute(
                "SELECT payload FROM x_setups_signals WHERE module=? ORDER BY rank ASC",
                (_MODULE,)).fetchall()]
            m = con.execute("SELECT v FROM x_setups_meta WHERE k='asof'").fetchone()
            return (rows or None), ((m["v"] if m else "") or "")
        finally:
            con.close()
    except Exception:  # noqa: BLE001 — missing table / unreadable DB honest-empties
        return None, ""


def _subnav(active: str) -> str:
    """The seasonal-family subnav — kept in sync with the seasonal_view / seasonal_screen_view copies."""
    links = (
        ("screen", "🔍 Scan this month", "/dash/seasonal-screen"),
        ("tape", "📅 Seasonal tape", "/dash/seasonal-tape"),
        ("divergence", "⚖ Index divergence", "/dash/seasonal-divergence"),
        ("calendar", "🗓 Expiry & holidays", "/dash/seasonal-calendar"),
    )
    chips = "".join(
        f'<a class="{"on" if key == active else ""}" href="{href}">{lbl}</a>'
        for key, lbl, href in links)
    return f'<div class="st-ctrl st-subnav">{chips}</div>'


def _bps(v) -> str:
    """A daily-return delta (fraction) as signed basis points, or an em-dash when undefined."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return '<span class="cc-z">—</span>'
    if x != x:  # nan
        return '<span class="cc-z">—</span>'
    cls = "cc-up" if x > 1e-9 else ("cc-dn" if x < -1e-9 else "cc-z")
    return f'<span class="{cls}">{x * 1e4:+.0f}</span>'


def _sorted(rows, sort, cap):
    key = sort if sort in _SORT_KEYS else _DEFAULT_SORT

    def _k(r):
        try:
            f = abs(float(r.get(key)))
            return f if f == f else -9.0
        except (TypeError, ValueError):
            return -9.0
    return key, sorted(rows, key=_k, reverse=True)[:cap]


def render(sort: str = _DEFAULT_SORT, cap: int = 60, fmt: str = "html", db_path=None):
    rows_all, asof = _load(db_path)

    if not rows_all:
        if fmt == "csv":
            return ",".join(_CSV_COLS) + "\n"
        body = [_CSS, ifx.readability_css(), _subnav("calendar"),
                ifx.bottom_line("Expiry &amp; holiday conditioning — <b>descriptive</b> calendar context, "
                                "never a signal."),
                '<div class="cc-empty">Snapshot not populated yet. It is materialised nightly by '
                '<code>python -m src.automation.x_setups_signals --persist-scan</code> '
                '(the X-scan spine). This surface is read-only and never fabricates data.</div>']
        return HTMLResponse(_shell("Expiry & holidays · patearn", "".join(body), "seasonal-calendar", "", wide=True))

    key, rows = _sorted(rows_all, sort, cap)

    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(_CSV_COLS)
        for r in rows:
            w.writerow([r.get(c) for c in _CSV_COLS])
        return buf.getvalue()

    body = [_CSS, ifx.readability_css(), _subnav("calendar")]
    body.append(ifx.bottom_line(
        "Each figure is a name's mean daily return in that calendar window <b>minus</b> its own all-days "
        "mean, in basis points — <b>descriptive</b> expiry/holiday context read against the seasonal null "
        "prior, <b>never</b> a signal or an entry."))
    body.append(ifx.how_to_read_link())
    body.append(f'<div class="cc-sum"><span>{len(rows_all)} names</span>'
                f'<span>asof <b>{_esc(asof)}</b></span>'
                f'<span>showing top <b>{len(rows)}</b> by |{_esc(key.replace("_ret_delta", "").replace("_", " "))}|</span></div>')

    # sort control (URL-addressable; CSV honors the same params)
    ctrl = ['<div class="cc-ctrl"><span class="lbl">rank by</span>']
    for k, lbl, _term in _COLS:
        on = "on" if k == key else ""
        ctrl.append(f'<a class="{on}" href="/dash/seasonal-calendar?sort={k}&cap={cap}">{lbl}</a>')
    ctrl.append("</div>")
    body.append("".join(ctrl))

    # table — every metric header carries its glossary popover; every symbol cell sym-links (§9)
    head = ['<table class="cc-tbl"><thead><tr><th class="sym">Symbol</th>']
    for _k, lbl, term in _COLS:
        head.append(f"<th>{G.gloss(term, lbl)}</th>")
    head.append('<th>Days</th><th>#Exp</th></tr></thead><tbody>')
    rowshtml = []
    for r in rows:
        sym = str(r.get("symbol", ""))
        cells = "".join(f"<td>{_bps(r.get(k))}</td>" for k, _, _ in _COLS)
        rowshtml.append(
            f'<tr><td class="sym"><a href="/dash/stock?sym={quote(sym)}">{_esc(sym)}</a></td>'
            f'{cells}<td>{int(r.get("n_days") or 0)}</td><td>{int(r.get("n_expiry") or 0)}</td></tr>')
    body.append("".join(head) + "".join(rowshtml) + "</tbody></table>")

    body.append(ifx.plain(
        "A positive expiry-day figure means that name tended to run slightly hotter on monthly-expiry days "
        "than on an average day, over its whole history; negative means cooler. Figures near zero are the "
        "norm — calendar effects were largely 0-certified in the estate's seasonal work, so read this as "
        "context, not edge."))
    body.append(f'<div class="cc-dl"><a href="/dash/seasonal-calendar?sort={_esc(key)}&cap={cap}&format=csv">'
                'Download CSV →</a></div>')
    body.append(
        '<div class="cc-fence">Descriptive calendar conditioning, <b>not</b> advice and <b>not</b> a signal. '
        'These deltas are published — including the many near-zero ones — to preserve the descriptive fence: '
        'the estate\'s calendar-seasonality studies were largely 0-certified, and showing that honestly is the '
        'point, not a claim that expiry/holiday timing predicts returns.</div>')
    return HTMLResponse(_shell("Expiry & holidays · patearn", "".join(body), "seasonal-calendar", "", wide=True))


@router.get("/dash/seasonal-calendar", response_class=HTMLResponse)
def dash_seasonal_calendar(sort: str = _DEFAULT_SORT, cap: int = 60, format: str = "html"):
    """Expiry/holiday conditioning lens (X-10). `format=csv` streams the same sorted/capped rows
    (playbook §8 server-side export; §8b same params)."""
    try:
        cap = max(5, min(int(cap), 500))
    except (TypeError, ValueError):
        cap = 60
    if format == "csv":
        return PlainTextResponse(render(sort=sort, cap=cap, fmt="csv"), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=calendar-conditioning.csv"})
    return render(sort=sort, cap=cap, fmt="html")


def _selftest() -> int:
    """Offline: honest-empty on a missing snapshot table; a populated synthetic x_setups_signals
    snapshot renders the sym-linked table, glossary-linked headers, descriptive fence, and CSV."""
    import os
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "cc_view_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)

    # 1) no x_setups_signals table -> honest-empty, never raises; CSV is just the header
    sqlite3.connect(tmp).close()
    empty = render(db_path=tmp)
    assert "Snapshot not populated" in empty.body.decode("utf-8")
    assert render(fmt="csv", db_path=tmp).startswith("symbol,")

    # 2) populate a synthetic snapshot via the real spine (single source of truth for the shape)
    from src.automation import x_setups_signals as XS
    con = sqlite3.connect(tmp)
    con.row_factory = sqlite3.Row
    computed = {"calendar_conditioning": [
        {"symbol": "TESTA", "asof": "2026-07-20", "n_days": 900, "expiry_ret_delta": 0.0012,
         "expiry_week_ret_delta": -0.0003, "pre_holiday_ret_delta": 0.0025, "post_holiday_ret_delta": -0.0011,
         "n_expiry": 42, "n_pre_holiday": 30, "med_turn": 8e7},
        {"symbol": "TESTB", "asof": "2026-07-20", "n_days": 700, "expiry_ret_delta": -0.0006,
         "expiry_week_ret_delta": 0.0001, "pre_holiday_ret_delta": float("nan"), "post_holiday_ret_delta": 0.0002,
         "n_expiry": 33, "n_pre_holiday": 0, "med_turn": 5e7}]}
    XS.persist_scan(con, computed=computed, computed_at="2026-07-20 18:00:00")
    con.commit(); con.close()

    html = render(db_path=tmp).body.decode("utf-8")
    assert "Expiry & holidays" in html
    assert '/dash/stock?sym=TESTA' in html, "every symbol cell must sym-link (playbook §9)"
    assert "+25" in html, "pre-holiday +25 bps should render"
    assert "asof <b>2026-07-20</b>" in html, "asof from x_setups_meta must render"
    assert "0-certified" in html and 'class="cc-fence"' in html, "descriptive fence + null-prior required"
    assert "🗓 Expiry & holidays" in html, "4th seasonal subnav chip must render"
    assert "format=csv" in html, "server-side CSV download link required"

    csv_out = render(fmt="csv", db_path=tmp)
    assert csv_out.startswith("symbol,expiry_ret_delta"), "CSV header missing"
    assert "TESTA," in csv_out
    _key, ordered = _sorted(computed["calendar_conditioning"], "pre_holiday_ret_delta", 60)
    assert ordered[0]["symbol"] == "TESTA", "finite |delta| must outrank NaN"

    os.remove(tmp)
    print("calendar_conditioning_view selftest OK — honest-empty on missing snapshot table; populated "
          "x_setups_signals snapshot renders sym-linked table + glossary headers + asof + "
          "descriptive/0-certified fence + CSV; NaN sorts last")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
