"""/dash/testing — the "Strategy validation" surface (Trust altitude).

Reframed (Lane N2, nav-IA pass): this is no longer a "strategy lens" — it is the
audit-grade RIGOR EVIDENCE that sits under Trust, alongside Coverage. It surfaces the
honest backtest record, including the standing verdict that nothing here is FUNDABLE
net of realistic participation cost at AUM (the best flat-cost champion failed its
2026-07-05 cost re-cut). We test our strategies and report what fails — that is the wedge.

Reads the persistent registry (research.db: strategy_registry / strategy_runs /
strategy_holdings) so backtested strategies + their current holdings live IN THE APP,
not in terminal output or a static file. ISOLATED on purpose: a self-contained
APIRouter that mounts via one line in main.py and does NOT edit the (parallel-session-
held) dashboard.py. It reuses the shared page shell `_shell` (import-safe) for chrome/
CSS consistency, with a defensive fallback. Read-only — never writes any table.

Refine loop: edit a signal/params -> re-run its backtest -> strategy_store.record_run()
appends a timestamped row -> this page shows the new result. The honest verdict
(no fundable net-of-cost alpha at AUM) is shown, not hidden.
"""
from __future__ import annotations

import html
import sqlite3

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

RESEARCH_DB = "/opt/hermes/data/research.db"
router = APIRouter()


def _shell_fallback(title, body, active="", latest_date="", wide=False):
    return ("<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<body style='background:var(--bg-1);color:var(--ink);font-family:system-ui;"
            "max-width:1100px;margin:0 auto;padding:24px'>" + body + "</body>")


try:
    from src.web.dashboard import _shell
except Exception:                                   # pragma: no cover
    _shell = _shell_fallback


def _esc(s):
    return html.escape(str(s), quote=True)


def _n(v, dp=2, suf=""):
    return "—" if v is None else f"{v:.{dp}f}{suf}"


_CSS = """
<style>
.tlab .lead{color:#8b97a7;font-size:13px;line-height:1.6;max-width:820px;margin:2px 0 18px}
.tlab .bar{background:#101a16;border:1px solid #1c3a2c;border-radius:10px;padding:11px 15px;margin:0 0 18px;font-size:13px}
.tlab .bar b{color:#e8ecf1}.tlab .bar .g{color:var(--series-4);font-family:monospace}
.tlab table{width:100%;border-collapse:collapse;font-size:12.5px;margin-bottom:10px}
.tlab th{text-align:right;color:#8b97a7;font-weight:500;font-size:10px;letter-spacing:.06em;text-transform:uppercase;padding:0 10px 7px;border-bottom:1px solid #262e39}
.tlab th:first-child,.tlab td:first-child{text-align:left}
.tlab td{padding:6px 10px;border-bottom:1px solid #1b212b;font-family:monospace}
.tlab td.nm{font-family:inherit;color:#e8ecf1}
.tlab tr.bench{background:#10241c}.tlab tr.bench td{color:var(--series-4)}
.tlab tr.real td:first-child::before{content:'● ';color:#d29922}
.tlab tr.flat td:first-child::before{content:'○ ';color:#6b7686}
.tlab .pos{color:var(--up)}.tlab .neg{color:var(--down)}
.tlab .legend{color:#8b97a7;font-size:11px;margin:4px 0 22px}
.tlab .card{background:var(--bg-2);border:1px solid #262e39;border-radius:12px;padding:14px 16px;margin:12px 0}
.tlab .cn{font-weight:700;font-size:14px}.tlab .cm{color:#8b97a7;font-family:monospace;font-size:11px;margin:3px 0 10px}
.tlab .chips{display:flex;flex-wrap:wrap;gap:6px}
.tlab .chip{background:#1c232d;border:1px solid #262e39;border-radius:6px;padding:4px 8px;font-size:11px;font-family:monospace;color:#cdd6e0}
.tlab h3{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#8b97a7;margin:24px 0 8px}
.tlab .note{color:#8b97a7;font-size:11px;margin-top:20px;border-top:1px solid #262e39;padding-top:12px;line-height:1.6}
</style>"""


def _registry(con):
    return con.execute("""
        SELECT g.name, g.category, g.status,
          (SELECT sharpe       FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
          (SELECT cagr_pct     FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
          (SELECT maxdd_pct    FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
          (SELECT ann_cost_pct FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
          (SELECT cost_model   FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
          (SELECT capacity_cr  FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1)
        FROM strategy_registry g
        ORDER BY (CASE WHEN (SELECT sharpe FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1)
                  IS NULL THEN 1 ELSE 0 END), 4 DESC""").fetchall()


def _holdings(con):
    out = {}
    for nm, asof, sym in con.execute(
            "SELECT name, as_of, symbol FROM strategy_holdings ORDER BY name, rank"):
        out.setdefault(nm, [asof, []])
        out[nm][1].append(sym)
    return out


def _disp(name):
    return name.split(":", 1)[1] if ":" in name else name


@router.get("/dash/testing", response_class=HTMLResponse)
def testing_page():
    # Degrade gracefully when research.db is absent (a demo laptop / clean checkout /
    # missing data dir): NEVER 500 — render a polished "unavailable" state instead.
    con = None
    try:
        con = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True)
    except Exception:
        try:
            con = sqlite3.connect(RESEARCH_DB)
        except Exception:
            con = None
    reg, holds, nruns = [], {}, 0
    if con is not None:
        try:
            try:
                reg = _registry(con)
                holds = _holdings(con)
            except sqlite3.OperationalError:
                reg, holds = [], {}
            nruns = con.execute("SELECT COUNT(*) FROM strategy_runs").fetchone()[0] if reg else 0
        except Exception:
            reg, holds, nruns = [], {}, 0
        finally:
            con.close()

    if not reg:
        if con is None:
            heading = "Strategy validation — unavailable in this environment"
            lead = ("The strategy-research database (<code>research.db</code>) is not present on "
                    "this host, so the validation record cannot render here. It is populated on the "
                    "production environment; this surface is read-only and never fabricates results — "
                    "absence is shown as absence, not a fabricated number.")
        else:
            heading = "Strategy validation"
            lead = ("Validation registry empty. Seed it on the VPS:<br>"
                    "<code>python -m explosive_moves.strategy_store --seed</code>")
        body = ("<div class='tlab'>" + _CSS + f"<h2>{html.escape(heading)}</h2>"
                f"<div class='lead'>{lead}</div></div>")
        return HTMLResponse(_shell("Strategy validation", body, active="testing", wide=True))

    rows = ""
    for nm, cat, status, sh, cg, dd, cost, cm, cap in reg:
        cls = "bench" if cat == "baseline" else ("real" if cm and "realistic" in cm else "flat")
        cgcls = "pos" if (cg or 0) >= 0 else "neg"
        rows += (f"<tr class='{cls}'><td class='nm'>{_esc(_disp(nm))}</td>"
                 f"<td>{_esc(cat)}</td><td style='text-align:left;color:#8b97a7'>{_esc(cm or '—')}</td>"
                 f"<td>{_n(sh)}</td><td class='{cgcls}'>{_n(cg,1,'%')}</td><td class='neg'>{_n(dd,1,'%')}</td>"
                 f"<td>{_n(cost,1,'%') if cost is not None else '—'}</td>"
                 f"<td>{('Rs'+_n(cap,0)+'cr') if cap is not None else '—'}</td></tr>")
    table = ("<table><thead><tr><th>Strategy</th><th>Category</th><th>Cost basis</th><th>Sharpe</th>"
             "<th>CAGR</th><th>MaxDD</th><th>Ann cost</th><th>Capacity</th></tr></thead><tbody>"
             + rows + "</tbody></table>"
             "<div class='legend'>○ flat-cost (illustrative) · ● realistic cost (tier spread + slippage) · "
             "green row = the buy-and-hold benchmark every active row must beat</div>")

    cards = "<h3>Candidate holdings (current top-25)</h3>"
    if holds:
        for nm, (asof, syms) in holds.items():
            chips = "".join(f"<span class='chip'>{_esc(s)}</span>" for s in syms)
            cards += (f"<div class='card'><div class='cn'>{_esc(_disp(nm))}</div>"
                      f"<div class='cm'>as of {_esc(asof)} · {len(syms)} names</div>"
                      f"<div class='chips'>{chips}</div></div>")
    else:
        cards += "<div class='lead'>No holdings stored yet — run <code>strategy_menu.py</code>.</div>"

    from src.web.infographics import demo_framing, readability_css
    body = (
        "<div class='tlab'>" + _CSS + readability_css() +
        "<h2>Strategy validation</h2>" + demo_framing() +
        "<div class='lead'>A Trust-altitude rigor record, not a strategy lens: every strategy we have "
        "backtested, its results net of cost, and the current holdings of the deployable candidates — "
        "published so the failures are as visible as the wins. Saved in <code>research.db</code> "
        f"({len(reg)} strategies · {nruns} backtest runs); refine a signal, re-run, and a new "
        "timestamped result appears here. <b>Honest verdict (re-cut 2026-07-05): nothing is FUNDABLE "
        "net of realistic participation cost at AUM.</b> The best flat-cost champion (C-BLEND 50/50, "
        "Sharpe 1.32) fails at scale — net 0.52 @₹25cr, 0.17 @₹50cr, −0.30 @₹100cr vs the 0.89 index "
        "bar; every PEAD event-book wrapper died (net 0.10, hedged −0.58); the one participation-"
        "fundable corner is quarterly large-cap LOWVOL_MOM (1.02 @₹50cr, ceiling ~₹150cr — defensive, "
        "not alpha). We publish those failures rather than bury them; the full pre-registered record "
        "is on <a href='/dash/spec-sheets' style='color:var(--accent)'>Spec sheets</a>.</div>"
        "<div class='bar'>⚖️ <b>The bar every active strategy must clear:</b> <span class='g'>Nifty 500 "
        "buy &amp; hold — Sharpe 0.89 / CAGR 15.3% / MaxDD −29%</span>. The choice among the rest is a "
        "risk-profile call, not alpha.</div>"
        + table + cards +
        "<div class='note'>Realistic metrics are net of per-name cost (tier spread + 0.5×ATR slippage), "
        "walk-forward 2012–26, no look-ahead. Universe for holdings = live Nifty 500 constituents "
        "(no delisted tickers, no liquid/ETF funds). Descriptive research artifact, not investment advice "
        "and not a performance claim. Full narrative: <code>docs/strategy-ledger.md</code>. "
        "See also the <a href='/dash/coverage' style='color:#58a6ff'>Coverage &amp; Settlement ledger</a> "
        "for the data limits behind these tests.</div></div>")
    return HTMLResponse(_shell("Strategy validation", body, active="testing", wide=True))
