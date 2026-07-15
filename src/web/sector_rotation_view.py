"""sector_rotation_view.py — /dash/sector-rotation: the Sector-Rotation (V17) portfolio
with TIME TRAVEL and rebalance analytics.

Ramana's premium bar (2026-07-15): after reading a strategy's detail page you land on the
PORTFOLIO, and there you can move backward/forward in time to see the exact book at any
point and HOW each rebalance occurred. This view delivers exactly that for the V17
champion-candidate (docs/strategies/sector-rotation.md):

  * `?asof=YYYY-MM-DD` — the book at any past rebalance (default: the latest), with
    ◀ prev / next ▶ steppers and a year strip;
  * the REBALANCE DIFF vs the previous quarter (entered · exited · re-weighted);
  * analytics-to-date (NAV multiple, CAGR, Sharpe, MaxDD — strategy vs Nifty 500 to that
    same date) + a dual NAV sparkline with the as-of marker;
  * the residual sleeve's regime at that date (INDEX above the 200DMA / CASH below);
  * `?fmt=csv` — the holdings at the as-of date (server-side, playbook item).

Reads the bounded snapshots `sector_rotation_book` / `sector_rotation_nav` (owned by
src/automation/sector_book.py — read-only here). DESCRIPTIVE / RESEARCH-CONDITIONAL:
the ledger verdict + every rejected lever is linked, never softened. Isolated module
(glossary_view pattern): own APIRouter, durably mounted via v2_surfaces._ROUTER_SPECS.
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.web import infographics as ifx
from src.web.momentum_view import HDB, _esc, _ro, _shell

router = APIRouter()
_ROUTE = "/dash/sector-rotation"


# ── data reads (defensive: page renders honestly when tables are absent/empty) ───────
def _load():
    c = _ro(HDB)
    if c is None:
        return {}, []
    try:
        book = {}
        for rd, s, w in c.execute(
                "SELECT rebal_date, sector, weight FROM sector_rotation_book "
                "ORDER BY rebal_date, weight DESC"):
            book.setdefault(rd, []).append((s, w))
        nav = [dict(d=r[0], nav=r[1], bench=r[2], inv=r[3], regime=r[4], turn=r[5])
               for r in c.execute(
                "SELECT month_date, nav, nav_bench, invested, regime, turnover "
                "FROM sector_rotation_nav ORDER BY month_date")]
        return book, nav
    except Exception:  # noqa: BLE001 — missing table = empty state, never a 500
        return {}, []
    finally:
        try:
            c.close()
        except Exception:  # noqa: BLE001
            pass


def _stats(navs):
    """CAGR / Sharpe / MaxDD from a NAV path (monthly marks, base 1.0 prepended)."""
    if len(navs) < 6:
        return None
    path = [1.0] + navs
    rets = [path[i] / path[i - 1] - 1 for i in range(1, len(path))]
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    pk, mdd = 1.0, 0.0
    for v in path:
        pk = max(pk, v)
        mdd = min(mdd, v / pk - 1)
    yrs = len(rets) / 12.0
    return dict(mult=navs[-1], cagr=navs[-1] ** (1 / yrs) - 1 if yrs > 0 else 0.0,
                sharpe=(m / sd * math.sqrt(12)) if sd > 0 else 0.0, mdd=mdd)


def _spark(nav, upto_i):
    """Dual log-scale NAV sparkline (strategy vs bench) with the as-of marker."""
    if len(nav) < 2:
        return ""
    W, H = 640, 90
    los = [min(r["nav"], r["bench"]) for r in nav]
    his = [max(r["nav"], r["bench"]) for r in nav]
    lo, hi = math.log(max(1e-6, min(los))), math.log(max(his))
    span = (hi - lo) or 1.0
    n = len(nav)

    def pts(key):
        out = []
        for i, r in enumerate(nav):
            x = 4 + i * (W - 8) / (n - 1)
            y = 4 + (hi - math.log(max(1e-6, r[key]))) / span * (H - 8)
            out.append(f"{x:.1f},{y:.1f}")
        return " ".join(out)

    mx = 4 + upto_i * (W - 8) / (n - 1)
    return (f"<svg viewBox='0 0 {W} {H}' style='width:100%;max-width:{W}px;height:{H}px' "
            f"role='img' aria-label='NAV of the strategy vs Nifty 500, log scale'>"
            f"<polyline points='{pts('bench')}' fill='none' stroke='var(--ink-3)' "
            f"stroke-width='1.2' stroke-dasharray='5 4'/>"
            f"<polyline points='{pts('nav')}' fill='none' stroke='var(--accent)' stroke-width='1.8'/>"
            f"<line x1='{mx:.1f}' y1='2' x2='{mx:.1f}' y2='{H-2}' stroke='var(--warn,#d99)' "
            f"stroke-width='1' stroke-dasharray='2 3'/></svg>")


def _pct(x, dp=1):
    return f"{x*100:.{dp}f}%"


@router.get(_ROUTE, response_class=HTMLResponse)
def sector_rotation_page(asof: str = Query(""), fmt: str = Query("")):
    book, nav = _load()
    rebs = sorted(book)
    asof = (asof or "").strip()[:10]
    if not rebs or not nav:
        body = (ifx.bottom_line(
            "The Sector-Rotation portfolio snapshot has not been computed yet — run "
            "<code>python -m src.automation.sector_book --build</code>. Methodology: "
            f"<a href='/dash/strategy-ref?p=sector-rotation'>the strategy reference</a>.")
            + ifx.how_to_read_link())
        return HTMLResponse(_shell("Sector rotation", body, active="sector-rotation", wide=True))

    pick = [d for d in rebs if not asof or d <= asof]
    cur = pick[-1] if pick else rebs[0]
    ci = rebs.index(cur)
    prev_d = rebs[ci - 1] if ci > 0 else None
    next_d = rebs[ci + 1] if ci + 1 < len(rebs) else None
    hold = book[cur]
    inv = sum(w for _s, w in hold)

    # nav rows up to the month AFTER this rebalance (the book's own month is marked at next)
    upto = [i for i, r in enumerate(nav) if r["d"] > cur]
    upto_i = upto[0] if upto else len(nav) - 1
    regime = nav[upto_i]["regime"]
    st = _stats([r["nav"] for r in nav[:upto_i + 1]])
    sb = _stats([r["bench"] for r in nav[:upto_i + 1]])
    st_full = _stats([r["nav"] for r in nav])
    sb_full = _stats([r["bench"] for r in nav])

    if fmt == "csv":
        lines = ["rebal_date,sector,weight,sleeve_regime"]
        for s, w in hold:
            lines.append(f"{cur},{s},{w:.4f},{regime}")
        lines.append(f"{cur},RESIDUAL_SLEEVE,{max(0.0, 1-inv):.4f},{regime}")
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    # rebalance diff vs the previous build
    prev_map = dict(book.get(prev_d, [])) if prev_d else {}
    cur_map = dict(hold)
    entered = sorted(set(cur_map) - set(prev_map))
    exited = sorted(set(prev_map) - set(cur_map))
    moved = [(s, prev_map[s], cur_map[s]) for s in sorted(set(cur_map) & set(prev_map))
             if abs(cur_map[s] - prev_map[s]) > 0.01]

    def _nm(s):
        return _esc(s.replace("Nifty ", ""))

    nav_link = "&asof=" if False else ""  # keep flake quiet
    def _lnk(d, label):
        return f"<a class='srp-btn' href='{_ROUTE}?asof={d}'>{label}</a>" if d else \
               f"<span class='srp-btn srp-dis'>{label}</span>"

    years = sorted({d[:4] for d in rebs})
    yearstrip = " ".join(
        f"<a href='{_ROUTE}?asof={y}-12-31' class='srp-yr" +
        (" on" if y == cur[:4] else "") + f"'>{y}</a>" for y in years)

    bars = "".join(
        f"<div class='srp-row'><span class='srp-sec'>{_nm(s)}</span>"
        f"<span class='srp-bar'><span style='width:{min(100, w*100/0.32):.0f}%'></span></span>"
        f"<span class='srp-w'>{_pct(w)}</span></div>"
        for s, w in hold)
    sleeve_w = max(0.0, 1 - inv)
    bars += (f"<div class='srp-row srp-slv'><span class='srp-sec'>Residual sleeve "
             f"({'Nifty 500 ETF' if regime == 'INDEX' else 'cash — index below its 200-day avg'})</span>"
             f"<span class='srp-bar'><span style='width:{min(100, sleeve_w*100/0.32):.0f}%'></span></span>"
             f"<span class='srp-w'>{_pct(sleeve_w)}</span></div>")

    def _difftxt():
        parts = []
        if entered:
            parts.append("<b>Entered:</b> " + ", ".join(_nm(s) + f" ({_pct(cur_map[s])})" for s in entered))
        if exited:
            parts.append("<b>Exited:</b> " + ", ".join(_nm(s) for s in exited))
        if moved:
            parts.append("<b>Re-weighted:</b> " + ", ".join(
                f"{_nm(s)} {_pct(a)}→{_pct(b)} {'▲' if b > a else '▼'}" for s, a, b in moved))
        if not parts:
            parts.append("No membership change — weights carried (hysteresis held every position).")
        return " · ".join(parts)

    def _stat_cells(tag, s_):
        if not s_:
            return f"<td>{tag}</td><td colspan='4'>—</td>"
        return (f"<td>{tag}</td><td>{s_['mult']:.2f}×</td><td>{_pct(s_['cagr'])}</td>"
                f"<td>{s_['sharpe']:.2f}</td><td>{_pct(s_['mdd'])}</td>")

    body = f"""
<style>
.srp-head{{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin:2px 0 10px}}
.srp-head h2{{font-size:17px;margin:0}}
.srp-btn{{border:1px solid var(--line-2);border-radius:6px;padding:2px 10px;font-size:12px;text-decoration:none;color:var(--ink-2)}}
.srp-btn:hover{{color:var(--accent)}} .srp-dis{{opacity:.35}}
.srp-yr{{font-size:11px;color:var(--ink-3);text-decoration:none;margin-right:2px}}
.srp-yr.on{{color:var(--accent);font-weight:600}}
.srp-row{{display:flex;align-items:center;gap:10px;margin:4px 0;font-size:13px}}
.srp-sec{{width:280px;color:var(--ink-2)}}
.srp-bar{{flex:1;background:var(--bg-2);border-radius:4px;height:14px;overflow:hidden}}
.srp-bar>span{{display:block;height:100%;background:var(--accent);opacity:.75}}
.srp-slv .srp-bar>span{{background:var(--ink-3)}}
.srp-w{{width:52px;text-align:right;font-variant-numeric:tabular-nums}}
.srp-tbl{{border-collapse:collapse;font-size:12.5px;margin:10px 0}}
.srp-tbl td,.srp-tbl th{{border:1px solid var(--line-2);padding:4px 10px;text-align:right}}
.srp-tbl td:first-child,.srp-tbl th:first-child{{text-align:left}}
.srp-diff{{font-size:12.5px;background:var(--bg-1);border:1px solid var(--line-2);border-radius:8px;padding:8px 12px;margin:10px 0}}
</style>
<div class='srp-head'>
  <h2>Sector rotation — the V17 book</h2>
  <span style='font-size:12px;color:var(--ink-3)'>{ifx.fence('not_reco', 'research-stage (CONDITIONAL); ledger-verdict linked below')}</span>
</div>
<div class='srp-head'>
  {_lnk(prev_d, '◀ previous rebalance')}
  <b style='font-size:14px'>{_esc(cur)}</b>
  {_lnk(next_d, 'next rebalance ▶')}
  <span style='margin-left:12px'>{yearstrip}</span>
  <span style='flex:1'></span>
  <a class='srp-btn' href='{_ROUTE}?asof={cur}&fmt=csv'>CSV</a>
  <a class='srp-btn' href='/dash/strategy-ref?p=sector-rotation'>methodology</a>
</div>
{bars}
<div class='srp-diff'><b>How this rebalance occurred</b> (vs {_esc(prev_d) if prev_d else 'inception'}): {_difftxt()}
 · sleeve regime at month-start: <b>{regime}</b> · turnover paid: {_pct(nav[upto_i]['turn'], 1)}</div>
{_spark(nav, upto_i)}
<table class='srp-tbl'>
<tr><th></th><th>NAV ×</th><th>CAGR</th><th>Sharpe</th><th>MaxDD</th></tr>
<tr>{_stat_cells('V17 to ' + nav[upto_i]['d'], st)}</tr>
<tr>{_stat_cells('Nifty 500 to same date', sb)}</tr>
<tr>{_stat_cells('V17 full period', st_full)}</tr>
<tr>{_stat_cells('Nifty 500 full period', sb_full)}</tr>
</table>
{ifx.bottom_line(
    "Every sector beating Nifty 500 on 6-month relative strength is held (equal-weighted, "
    "30% cap), entries need an RSI-green recovery, weights taper as a sector nears its own "
    "RS peak, and the idle residual sits in a Nifty ETF only while the index holds its "
    "200-day average. Long-only; the short leg, monthly churn and book-level kill-switch "
    "were all tested and <a href='/dash/strategy-ref?p=sector-rotation'>REJECTED — see the "
    "methodology + ledger verdict</a>. Price-index numbers, dividends excluded on both sides.")}
{ifx.how_to_read_link()}
"""
    return HTMLResponse(_shell("Sector rotation", body, active="sector-rotation", wide=True))


def wire(app):
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if _ROUTE not in paths:
            app.include_router(router)
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger("hermes.sector_rotation_view").warning("wire skipped: %s", e)
    return app


def _selftest() -> int:
    import sqlite3
    import tempfile
    import os
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "t.db")
    c = sqlite3.connect(db)
    c.executescript("""
    CREATE TABLE sector_rotation_book (rebal_date TEXT, sector TEXT, weight REAL);
    CREATE TABLE sector_rotation_nav (month_date TEXT, nav REAL, nav_bench REAL,
        invested REAL, regime TEXT, turnover REAL, computed_at TEXT);
    """)
    c.executemany("INSERT INTO sector_rotation_book VALUES (?,?,?)", [
        ("2020-01-01", "Nifty IT", 0.30), ("2020-01-01", "Nifty Pharma", 0.30),
        ("2020-04-01", "Nifty Pharma", 0.30), ("2020-04-01", "Nifty FMCG", 0.25)])
    rows = []
    navv = navb = 1.0
    for i, m in enumerate(["2020-02-01", "2020-03-02", "2020-04-01", "2020-05-04",
                           "2020-06-01", "2020-07-01", "2020-08-03"]):
        navv *= 1.01
        navb *= 1.005
        rows.append((m, navv, navb, 0.6, "INDEX" if i % 2 == 0 else "CASH", 0.1 if i % 3 == 0 else 0.0, "t"))
    c.executemany("INSERT INTO sector_rotation_nav VALUES (?,?,?,?,?,?,?)", rows)
    c.commit(); c.close()

    globals()["HDB"] = db          # rebind THIS module's global (works under -m too)
    app = FastAPI(); app.include_router(router)
    t = TestClient(app)
    r = t.get(_ROUTE)
    assert r.status_code == 200 and "V17 book" in r.text and "2020-04-01" in r.text, r.status_code
    r2 = t.get(_ROUTE + "?asof=2020-02-15")
    assert "2020-01-01" in r2.text and "previous rebalance" in r2.text, "time travel broken"
    assert "Entered:" in t.get(_ROUTE + "?asof=2020-05-01").text, "rebalance diff missing"
    csv = t.get(_ROUTE + "?asof=2020-05-01&fmt=csv").text
    assert csv.startswith("rebal_date,sector") and "RESIDUAL_SLEEVE" in csv, "csv broken"
    globals()["HDB"] = os.path.join(tmp, "missing.db")
    r3 = t.get(_ROUTE)
    assert r3.status_code == 200 and "not been computed" in r3.text, "empty state must not 500"
    print("sector_rotation_view selftest OK — time-travel + diff + csv + empty-state all render")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
