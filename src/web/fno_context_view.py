"""F&O positioning board — every OI read ranked against the stock's OWN history.

The per-stock #fno dossier tab and /dash/participants show today's SNAPSHOT: today's
quadrant, today's PCR, today's max-pain. That is exactly what every free tool shows — and
it is the trap Ramana named: a strong SHORT_COVER day does not mean a squeeze if the short
book it is covering is still historically HUGE (positions merely rolled, not left). The
un-owned move — the same axis /dash/self-history adds to price/delivery/turnover — is to
rank each F&O read against the stock's OWN past, so "is this real or noise?" gets a number:

  * PCR percentile   — today's put/call OI ratio vs its own history (extreme fear vs normal).
  * OI percentile    — futures OI vs its own history = CROWDEDNESS of the book (the missing
                       context: covering on a 90th-pctl book = shorts barely trimming).
  * Max-pain distance— signed % gap of spot from max-pain, and where that sits in its own range.
  * Build-up streak  — how many days the stock has held THIS quadrant (persistence, not a blip).

Plus a handful of auto-generated "reality-check" callouts read straight off the data — the
hollow short-cover (covering on a still-crowded book), the crowded short build-up, the fresh
long on a thin book — the reads a same-day tag cannot make.

STRICTLY DESCRIPTIVE (D62 / ledger): a percentile is CONTEXT, not a forecast. The Phase-0
edge gate (2026-07-24) found only PCR carries a small cross-sectional edge (δ≈0.06,
forward-test-only); this board RANKS and FLAGS, it never picks. Compute-on-read from
fno_oi_signals (stdlib only — the web venv has no numpy), cached per trading day.
Route: /dash/fno  ->  nested /dash/markets/fno  [?sort=..].
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_MINPTS = 60          # need >=60 own-history points before a percentile is trustworthy (~3 months)

# quadrant -> (colour, short label) — self-contained (does not import dashboard._FNO_QC)
_QC = {
    "LONG_BUILDUP":  ("var(--up)",   "long buildup"),
    "SHORT_BUILDUP": ("var(--down)", "short buildup"),
    "LONG_UNWIND":   ("#f0883e",     "long unwind"),
    "SHORT_COVER":   ("var(--up)",   "short cover"),
    "FLAT":          ("#8b949e",     "flat"),
}

# the ranked columns: (key, short label, tooltip)
_COLS = [
    ("pcr_pct",  "PCR pctl",   "today's put/call OI ratio ranked vs the stock's own history (100 = most put-heavy ever)"),
    ("oi_pct",   "OI pctl",    "futures OI vs its own history = crowdedness of the book (100 = book at its own heaviest)"),
    ("dist_pct", "MaxPain pctl", "signed spot-vs-max-pain distance ranked vs its own history"),
]

# diverging blue -> neutral -> red ramp for a 0..100 percentile (matches self-history for a
# consistent site read). Text colour computed per-cell for contrast.
_STOPS = [(27, 95, 166), (127, 176, 224), (207, 205, 196), (231, 154, 154), (163, 45, 45)]


def _heat(v) -> tuple[str, str]:
    if v is None:
        return ("var(--bg-3)", "var(--ink-3)")
    v = max(0.0, min(100.0, float(v)))
    p = v / 25.0
    i = min(3, int(p))
    f = p - i
    a, b = _STOPS[i], _STOPS[i + 1]
    c = [round(a[k] + (b[k] - a[k]) * f) for k in range(3)]
    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    return (f"rgb({c[0]},{c[1]},{c[2]})", "#fff" if lum < 150 else "#23201c")


def _pct_rank(hist: list, x) -> float | None:
    """Percentile (0..100) of x within the stock's OWN history; needs >=_MINPTS points."""
    vals = [h for h in hist if h is not None]
    if len(vals) < _MINPTS or x is None:
        return None
    n = sum(1 for h in vals if h <= x)
    return round(100.0 * n / len(vals), 1)


def _signed_dist(und, mp):
    """Signed % gap of spot from max-pain: +ve = spot ABOVE max-pain (pulled down into expiry)."""
    if und is None or not mp:
        return None
    return round((und / mp - 1.0) * 100.0, 2)


def _one(sym: str, series: list) -> dict | None:
    """series = the stock's fno_oi_signals rows, OLDEST->newest. Build one board row:
    today's values + each read's own-history percentile + the quadrant streak."""
    if not series:
        return None
    cur = series[-1]
    q = cur["quadrant"]

    # streak: consecutive days (from today, backwards) in the same quadrant
    streak = 0
    for r in reversed(series):
        if q and r["quadrant"] == q:
            streak += 1
        else:
            break

    pcr_hist = [r["pcr"] for r in series]
    oi_hist = [r["fut_oi"] for r in series]
    dist_hist = [_signed_dist(r["und_price"], r["max_pain"]) for r in series]
    dist_cur = _signed_dist(cur["und_price"], cur["max_pain"])

    return {
        "sym": sym, "date": cur["trade_date"],
        "quadrant": q, "streak": streak,
        "pcr": cur["pcr"], "pcr_pct": _pct_rank(pcr_hist, cur["pcr"]),
        "fut_oi": cur["fut_oi"], "oi_pct": _pct_rank(oi_hist, cur["fut_oi"]),
        "oi_chg": cur["fut_oi_chg_pct"], "basis": cur["basis_pct"],
        "dist": dist_cur, "dist_pct": _pct_rank(dist_hist, dist_cur),
        "und": cur["und_price"], "max_pain": cur["max_pain"],
        "n_hist": sum(1 for r in series if r["quadrant"]),
    }


@lru_cache(maxsize=2)
def _compute(asof: str) -> tuple:
    """Every F&O name's current positioning + own-history percentiles, as of the latest day.
    Cached per trading day (asof keys the cache; the compute reads the live latest bar)."""
    out = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, trade_date, quadrant, pcr, fut_oi, und_price, max_pain, "
            "basis_pct, fut_oi_chg_pct FROM fno_oi_signals ORDER BY symbol, trade_date"
        ).fetchall()
    if not rows:
        return tuple()
    by_sym: dict[str, list] = {}
    for r in rows:
        by_sym.setdefault(r["symbol"], []).append(r)
    latest = max(v[-1]["trade_date"] for v in by_sym.values())
    for sym, series in by_sym.items():
        if series[-1]["trade_date"] != latest:      # only names present on the current cross-section
            continue
        try:
            m = _one(sym, series)
        except Exception:  # noqa: BLE001 — one bad symbol never breaks the board
            m = None
        if m:
            out.append(m)
    return tuple(out)


def _latest_date() -> str:
    with get_conn() as conn:
        r = conn.execute("SELECT MAX(trade_date) FROM fno_oi_signals").fetchone()
        return (r[0] if r and r[0] else "")


_SORTS = {c[0] for c in _COLS} | {"sym", "streak", "oi"}


def _sorted(rows: list, sort: str) -> list:
    if sort == "sym":
        return sorted(rows, key=lambda z: z["sym"])
    if sort == "oi":
        return sorted(rows, key=lambda z: (z.get("fut_oi") is None, -(z.get("fut_oi") or 0)))
    return sorted(rows, key=lambda z: (z.get(sort) is None, -(z.get(sort) or 0)))


def _oi(v) -> str:
    if v is None:
        return "—"
    if v >= 1e7:
        return f"{v/1e7:.2f}Cr"
    if v >= 1e5:
        return f"{v/1e5:.2f}L"
    return f"{v:,.0f}"


_CSS = """
<style>
.fn-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 12px;max-width:1120px;}
.fn-note b{color:var(--ink);}
.fn-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:2px 0 10px;}
.fn-ctrl a{padding:4px 12px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;text-decoration:none;}
.fn-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.fn-ctrl .sep{color:var(--ink-3);font-size:11px;margin:0 2px;}
.fn-key{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:0 0 12px;font-size:11.5px;color:var(--ink-3);}
.fn-key .ramp{display:inline-block;width:132px;height:11px;border-radius:3px;
  background:linear-gradient(90deg,rgb(27,95,166),rgb(127,176,224),rgb(207,205,196),rgb(231,154,154),rgb(163,45,45));}
.fn-wrap{overflow-x:auto;margin:0 0 8px;}
table.fn{border-collapse:collapse;font-size:12px;min-width:720px;}
table.fn th{color:var(--ink-3);font-weight:600;padding:3px 6px 7px;white-space:nowrap;}
table.fn th a{color:var(--ink-3);text-decoration:none;}
table.fn th a:hover{color:var(--ink);}
table.fn th.raw{color:var(--ink-3);text-align:right;font-weight:500;}
table.fn td{padding:0 2px;border-top:1px solid var(--line);height:23px;}
table.fn td.sym a{color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap;}
table.fn td.sym a:hover{text-decoration:underline;}
table.fn td.q{white-space:nowrap;font-weight:600;}
table.fn td.cell{padding:0 1px;}
table.fn td.cell .b{text-align:center;padding:3px 0;border-radius:3px;font-variant-numeric:tabular-nums;min-width:47px;}
table.fn td.raw{text-align:right;padding:0 8px;font-variant-numeric:tabular-nums;color:var(--ink-2);}
table.fn td.raw.mut{color:var(--ink-3);}
.fn-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px;}
.fn-chip{background:var(--bg-2);border:1px solid var(--line-2);border-radius:9px;padding:6px 10px;font-size:11.5px;color:var(--ink-2);max-width:340px;}
.fn-chip b{color:var(--ink);} .fn-chip a{color:var(--accent);text-decoration:none;}
.fn-chip .h{display:block;font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-3);margin-bottom:2px;}
</style>
"""


def _chips(rows: list) -> str:
    """Auto-generated 'reality-check' callouts read straight off the data — the reads a
    same-day quadrant tag cannot make. Each is a NAMED example, never a ranking."""
    out = []

    # 1) hollow short-cover — covering, but the short book is still historically crowded
    #    (the shorts merely rolled, they did not leave; a real squeeze is unlikely). Ramana's case.
    hollow = [r for r in rows if r["quadrant"] == "SHORT_COVER"
              and r.get("oi_pct") is not None and r["oi_pct"] >= 70]
    if hollow:
        h = sorted(hollow, key=lambda z: -z["oi_pct"])[0]
        out.append('<div class="fn-chip"><span class="h">Hollow short-cover</span>'
                   f'Covering on a still-crowded book: <a href="/dash/stock?sym={_esc(h["sym"])}">'
                   f'{_esc(h["sym"])}</a> — OI in its <b>{h["oi_pct"]:.0f}th</b> percentile. '
                   'Shorts rolled, not left; the bounce sits on an intact short book.</div>')

    # 2) crowded short build-up — fresh shorts piling into an already-heavy book, held for days
    crowd = [r for r in rows if r["quadrant"] == "SHORT_BUILDUP"
             and r.get("oi_pct") is not None and r["oi_pct"] >= 80 and r["streak"] >= 2]
    if crowd:
        c = sorted(crowd, key=lambda z: -(z["oi_pct"] + z["streak"]))[0]
        out.append('<div class="fn-chip"><span class="h">Crowded short build-up</span>'
                   f'<a href="/dash/stock?sym={_esc(c["sym"])}">{_esc(c["sym"])}</a> — '
                   f'day <b>{c["streak"]}</b> of short buildup, OI at its <b>{c["oi_pct"]:.0f}th</b> '
                   'percentile. Conviction distribution, not a one-day blip.</div>')

    # 3) fresh long on a thin book — new longs with the futures book still light (room to grow)
    fresh = [r for r in rows if r["quadrant"] == "LONG_BUILDUP"
             and r.get("oi_pct") is not None and r["oi_pct"] <= 40 and r["streak"] >= 2]
    if fresh:
        f = sorted(fresh, key=lambda z: z["oi_pct"])[0]
        out.append('<div class="fn-chip"><span class="h">Fresh long, thin book</span>'
                   f'<a href="/dash/stock?sym={_esc(f["sym"])}">{_esc(f["sym"])}</a> — '
                   f'day <b>{f["streak"]}</b> of long buildup, OI only <b>{f["oi_pct"]:.0f}th</b> '
                   'percentile. Early accumulation with headroom.</div>')

    # 4) extreme PCR — the one read Phase-0 found a (small) edge in; flag its own-history extreme
    pcx = [r for r in rows if r.get("pcr_pct") is not None and r["pcr_pct"] >= 92]
    if pcx:
        p = sorted(pcx, key=lambda z: -z["pcr_pct"])[0]
        out.append('<div class="fn-chip"><span class="h">Extreme PCR (own history)</span>'
                   f'<a href="/dash/stock?sym={_esc(p["sym"])}">{_esc(p["sym"])}</a> — PCR '
                   f'<b>{p["pcr"]:.2f}</b>, its <b>{p["pcr_pct"]:.0f}th</b> percentile (most put-heavy '
                   'in its own history). Contrarian fear read.</div>')

    return f'<div class="fn-chips">{"".join(out)}</div>' if out else ""


def _table(rows: list, sort: str) -> str:
    def hcell(key, label, tip):
        arrow = " ▾" if sort == key else ""
        return (f'<th title="{_esc(tip)}"><a href="/dash/fno?sort={key}">{_esc(label)}{arrow}</a></th>')

    head = ['<th class="raw" style="text-align:left">'
            '<a href="/dash/fno?sort=sym" style="color:var(--ink-3);text-decoration:none">Stock</a></th>',
            '<th style="text-align:left">Today</th>',
            '<th class="raw"><a href="/dash/fno?sort=streak" style="color:var(--ink-3);text-decoration:none">days</a></th>']
    for key, label, tip in _COLS:
        head.append(hcell(key, label, tip))
    head += ['<th class="raw" title="today put/call OI ratio">PCR</th>',
             '<th class="raw" title="futures OI (summed across expiries)">'
             '<a href="/dash/fno?sort=oi" style="color:var(--ink-3);text-decoration:none">Fut OI</a></th>',
             '<th class="raw" title="signed % of spot from max-pain (+ = spot above)">MaxPain %</th>',
             '<th class="raw" title="near-month future vs spot">basis</th>']
    trs = []
    for r in rows:
        qcol, qlbl = _QC.get(r["quadrant"] or "", ("#8b949e", r["quadrant"] or "—"))
        tds = [f'<td class="sym"><a href="/dash/stock?sym={_esc(r["sym"])}">{_esc(r["sym"])}</a></td>',
               f'<td class="q" style="color:{qcol}">{_esc(qlbl)}</td>',
               f'<td class="raw">{r["streak"]}</td>']
        for key, _lab, _tip in _COLS:
            v = r.get(key)
            bg, fg = _heat(v)
            main = f'{v:.0f}' if v is not None else 'n/a'
            tds.append(f'<td class="cell"><div class="b" style="background:{bg};color:{fg}">{main}</div></td>')
        pcr = r.get("pcr")
        basis = r.get("basis")
        dist = r.get("dist")
        tds += [
            f'<td class="raw">{pcr:.2f}</td>' if pcr is not None else '<td class="raw mut">–</td>',
            f'<td class="raw mut">{_oi(r.get("fut_oi"))}</td>',
            (f'<td class="raw" style="color:{"var(--up)" if dist >= 0 else "var(--down)"}">{dist:+.1f}</td>'
             if dist is not None else '<td class="raw mut">–</td>'),
            (f'<td class="raw" style="color:{"var(--up)" if basis >= 0 else "var(--down)"}">{basis:+.2f}</td>'
             if basis is not None else '<td class="raw mut">–</td>'),
        ]
        trs.append(f'<tr>{"".join(tds)}</tr>')
    return (f'<div class="fn-wrap"><table class="fn"><thead><tr>{"".join(head)}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def _csv(rows: list) -> str:
    cols = ["sym", "date", "quadrant", "streak", "pcr", "pcr_pct", "fut_oi", "oi_pct",
            "dist", "dist_pct", "basis", "und", "max_pain"]
    out = [",".join(cols)]
    for r in rows:
        out.append(",".join("" if r.get(c) is None else str(r.get(c)) for c in cols))
    return "\n".join(out) + "\n"


@router.get("/dash/fno", response_class=HTMLResponse)
def dash_fno(sort: str = "oi_pct", format: str = "") -> HTMLResponse:
    sort = sort if sort in _SORTS else "oi_pct"
    as_of = ""
    try:
        as_of = _latest_date()
        if not as_of:
            raise LookupError("no fno_oi_signals")
        rows = _sorted(list(_compute(as_of)), sort)
        if not rows:
            raise LookupError("empty F&O universe")
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        empty = (
            '<h2>F&amp;O positioning</h2><div class="fn-note">This board ranks each F&amp;O name\'s '
            'open-interest reads against its <b>own</b> history, read live from '
            '<code>fno_oi_signals</code> (NSE F&amp;O bhavcopy). That table is not populated on this '
            'host, so there is nothing to rank yet. Read-only; never fabricates data.</div>')
        return HTMLResponse(_shell("F&O positioning · patearn", _CSS + empty, "fno",
                                   str(as_of)[:10], wide=True))

    if format == "csv":
        return PlainTextResponse(_csv(rows), media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="fno-positioning.csv"'})

    body = [_CSS, ifx.readability_css()]
    body.append(
        '<h2 style="margin:0 0 2px">F&amp;O positioning '
        f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">every OI read ranked '
        f'0–100 vs each stock\'s own history · {len(rows)} F&amp;O names · as of {_esc(as_of)}</small></h2>')
    body.append(ifx.bottom_line(
        'A short-covering day is not a squeeze if the short book it is covering is still '
        '<b>historically huge</b> — the positions merely rolled. So beside today\'s quadrant, every '
        'number here is ranked <b>vs the stock\'s own past</b>: <b>OI percentile</b> = how crowded the '
        'book is, <b>PCR percentile</b> = how extreme the fear, <b>max-pain distance</b> = how far spot '
        'has strayed. That turns "is this real or noise?" into a number.'))
    body.append(ifx.how_to_read_link())
    body.append(
        '<div class="fn-note">Four ranked reads per name: <b>PCR pctl</b> (put/call OI vs its own '
        'history), <b>OI pctl</b> (futures-book crowdedness), <b>MaxPain pctl</b> (signed spot-vs-max-pain '
        'gap vs its own range), and the quadrant <b>streak</b> (persistence, not a one-day blip). The '
        'cards below are auto-generated reality-checks — a hollow short-cover (covering on a still-crowded '
        f'book), a crowded short build-up, a fresh long on a thin book. {ifx.fence("not_signal", cap=True)}. '
        '<a href="/dash/glossary?q=OI percentile">glossary →</a></div>')

    sorts = [("oi_pct", "OI crowdedness"), ("pcr_pct", "PCR extreme"), ("dist_pct", "max-pain distance"),
             ("streak", "streak length"), ("oi", "book size"), ("sym", "symbol")]
    ss = "".join(f'<a class="{"on" if sort==k else ""}" href="/dash/fno?sort={k}">{_esc(lab)}</a>'
                 for k, lab in sorts)
    body.append(f'<div class="fn-ctrl">{ss}<span class="sep">·</span>'
                f'<a href="/dash/fno?sort={sort}&format=csv" style="border-color:var(--line-2)">Download CSV</a></div>')

    body.append('<div class="fn-key"><span><span class="ramp"></span> 0 = own low · 50 = middle · '
                '100 = own high</span><span>percentiles need ≥3 months of the stock\'s own F&amp;O history · '
                'symbols link to the dossier</span></div>')
    body.append(_chips(rows))
    body.append(_table(rows, sort))
    body.append('<div class="fn-note" style="margin-top:10px;color:var(--ink-3);font-size:11.5px">'
                'An own-history percentile is <b>context, not a forecast</b>. The Phase-0 edge gate found '
                'only PCR carries a small cross-sectional edge (forward-test-only); this board ranks and '
                'flags — it never picks. F&amp;O covers ~190–220 large-caps only.</div>')
    return HTMLResponse(_shell("F&O positioning · patearn", "".join(body), "fno",
                               str(as_of)[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/fno" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    # unit: the pure helpers, no DB
    assert _pct_rank(list(range(120)), 119) == 100.0
    assert _pct_rank(list(range(120)), 0) == round(100.0 / 120, 1)
    assert _pct_rank([1, 2, 3], 3) is None                 # too few points
    assert _signed_dist(110, 100) == 10.0
    assert _signed_dist(90, 100) == -10.0
    assert _signed_dist(100, None) is None
    bg, fg = _heat(100.0)
    assert bg.startswith("rgb(") and fg in ("#fff", "#23201c")
    assert _heat(None)[0] == "var(--bg-3)"
    # _one: streak + percentiles over a synthetic series
    series = [{"trade_date": f"2026-01-{i:02d}", "quadrant": "LONG_BUILDUP", "pcr": 0.5 + i * 0.01,
               "fut_oi": 1000 + i, "und_price": 100 + i, "max_pain": 100, "basis_pct": 0.2,
               "fut_oi_chg_pct": 1.0} for i in range(1, 71)]
    m = _one("TEST", series)
    assert m["streak"] == 70 and m["quadrant"] == "LONG_BUILDUP"
    assert m["oi_pct"] == 100.0 and m["pcr_pct"] == 100.0     # today is the max of its own history
    assert _sorted([{"sym": "B", "oi_pct": 1}, {"sym": "A", "oi_pct": 9}], "oi_pct")[0]["sym"] == "A"
    assert _csv([{"sym": "X", "date": "2026-01-01", "quadrant": "FLAT"}]).splitlines()[0].startswith("sym,date")
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    for url in ("/dash/fno", "/dash/fno?sort=pcr_pct", "/dash/fno?sort=streak",
                "/dash/fno?sort=bogus", "/dash/fno?format=csv"):
        r = c.get(url)
        assert r.status_code == 200, (url, r.status_code)
    assert "F&O positioning" in c.get("/dash/fno").text
    print("fno_context_view selftest OK — helpers + streak/percentile + page 200 (populated or honest-empty) + csv")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
