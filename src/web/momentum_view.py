"""/dash/momentum-scan — Risk-adjusted momentum SCANNER (Markets altitude).

A candidate shortlister, not an alpha engine. Ranks the liquid equity universe by RISKADJ
(6-mo return / 3-mo vol) and the equal-weight ensemble (MOM12+HI52+RISKADJ+LOWVOL_MOM), and
inlines the C/A/B VETO columns (capital-allocation tier, insider pledge/conviction, credit
adverse) so a human researches the survivors — the workload reducer. Momentum here is
gross momentum-BETA (attribution: not proprietary selection alpha; see
docs/predictive-attributes-findings.md); this surface says so plainly.

Reads `momentum_scan` (written by research/explosive_moves/momentum_scan.py, nightly) + joins
insider_events / credit_rating_events / capital_allocation_scores — ALL in hermes.db, so the
view runs in the app venv (no numpy). Isolated APIRouter, reuses `_shell`, degrades gracefully
(never 500). Read-only.
"""
from __future__ import annotations

import html
import sqlite3

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

HDB = "/opt/hermes/data/hermes.db"
router = APIRouter()


def _shell_fallback(title, body, active="", latest_date="", wide=False):
    return ("<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<body style='background:var(--bg-1);color:var(--ink);font-family:system-ui;"
            "max-width:1200px;margin:0 auto;padding:24px'>" + body + "</body>")


try:
    from src.web.dashboard import _shell
except Exception:                                    # pragma: no cover
    _shell = _shell_fallback


def _esc(s):
    return html.escape(str(s), quote=True)


def _ro(path):
    try:
        return sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    except Exception:
        try:
            return sqlite3.connect(path)
        except Exception:
            return None


_CSS = """
<style>
.msc .lead{color:#8b97a7;font-size:13px;line-height:1.6;max-width:900px;margin:2px 0 16px}
.msc .bar{background:#101a16;border:1px solid #1c3a2c;border-radius:10px;padding:10px 14px;margin:0 0 16px;font-size:12.5px;color:#cdd6e0}
.msc table{width:100%;border-collapse:collapse;font-size:12.5px}
.msc th{text-align:right;color:#8b97a7;font-weight:500;font-size:10px;letter-spacing:.05em;text-transform:uppercase;padding:0 9px 7px;border-bottom:1px solid #262e39;cursor:pointer;user-select:none}
.msc th:first-child,.msc td:first-child,.msc th.l,.msc td.l{text-align:left}
.msc td{padding:6px 9px;border-bottom:1px solid #1b212b;font-family:monospace;text-align:right}
.msc td.nm{font-family:inherit;color:#e8ecf1;font-weight:600}
.msc .pos{color:var(--up)}.msc .neg{color:var(--down)}
.msc .tier-EXCELLENT{color:var(--up);font-weight:600}.msc .tier-GOOD{color:#7bd88f}
.msc .tier-AVERAGE{color:#8b97a7}.msc .tier-WEAK{color:var(--warn)}.msc .tier-POOR{color:var(--down)}
.msc .buy{color:var(--up)}.msc .risk{color:var(--down);font-weight:600}
.msc .f-clear{color:var(--up)}.msc .f-caution{color:var(--warn)}.msc .f-avoid{color:var(--down);font-weight:700}
.msc .note{color:#8b97a7;font-size:11px;margin-top:18px;border-top:1px solid #262e39;padding-top:11px;line-height:1.6}
.msc .seg{display:inline-block;margin:0 0 12px}.msc .seg a{color:#8b97a7;text-decoration:none;padding:5px 12px;border:1px solid #262e39;border-radius:7px;margin-right:6px;font-size:12px}
.msc .seg a.on{background:#15202b;color:#e8ecf1;border-color:#2f3d4d}
</style>"""

_SORT_JS = """
<script>
document.querySelectorAll('.msc th[data-k]').forEach(function(h){h.onclick=function(){
 var t=h.closest('table'),b=t.tBodies[0],i=[].indexOf.call(h.parentNode.children,h),
 num=h.dataset.num==='1',asc=h.dataset.asc!=='1';h.dataset.asc=asc?'1':'0';
 [].slice.call(b.rows).sort(function(x,y){var a=x.cells[i].dataset.v||x.cells[i].innerText,
 c=y.cells[i].dataset.v||y.cells[i].innerText;if(num){a=parseFloat(a)||0;c=parseFloat(c)||0;}
 return (a>c?1:a<c?-1:0)*(asc?1:-1);}).forEach(function(r){b.appendChild(r);});};});
</script>"""


def _veto_maps(con):
    pledge, conviction, adverse, catier = {}, {}, {}, {}
    try:
        for sym, sc, n in con.execute(
                "SELECT symbol, signal_class, COUNT(*) FROM insider_events "
                "WHERE signal_class IN ('pledge_risk','conviction') AND symbol IS NOT NULL "
                "GROUP BY symbol, signal_class"):
            (pledge if sc == "pledge_risk" else conviction)[sym] = n
    except sqlite3.OperationalError:
        pass
    try:
        for sym, n in con.execute(
                "SELECT symbol, COUNT(*) FROM credit_rating_events WHERE symbol IS NOT NULL "
                "AND (action_class IN ('DOWNGRADE','DEFAULT') OR below_investment_grade=1) GROUP BY symbol"):
            adverse[sym] = n
    except sqlite3.OperationalError:
        pass
    try:
        for sym, tier in con.execute(
                "SELECT symbol, ca_tier FROM capital_allocation_scores WHERE ca_tier IS NOT NULL "
                "GROUP BY symbol HAVING as_of=MAX(as_of)"):
            catier[sym] = tier
    except sqlite3.OperationalError:
        pass
    return pledge, conviction, adverse, catier


@router.get("/dash/momentum-scan", response_class=HTMLResponse)
def momentum_scan_page(sort: str = "riskadj"):
    con = _ro(HDB)
    rows, as_of = [], ""
    if con is not None:
        try:
            as_of = (con.execute("SELECT MAX(as_of) FROM momentum_scan").fetchone() or [None])[0] or ""
            if as_of:
                order = {"ens": "ensemble_pctile", "cblend": "cblend"}.get(sort, "riskadj")
                # C-BLEND 50/50 = mean(RISKADJ pctile, capital-allocation C pctile) — the S77b
                # backtest's new-best overlay (Sharpe 1.32 / Calmar 1.15 / MaxDD -28.2%,
                # docs/strategy-ledger.md § Experiment 2026-07-03). Missing C -> neutral 50th
                # pctile, exactly as the backtest neutral-filled. A DESCRIPTIVE tilt, not a buy list.
                rows = con.execute(
                    "SELECT m.symbol,m.mom6,m.mom12,m.vol_66,m.riskadj,m.range_pos_252,m.turnover_cr,"
                    "m.riskadj_pctile,m.ensemble_pctile,"
                    "(0.5*m.riskadj_pctile + 0.5*COALESCE(c.ca_pctile,50.0)) AS cblend "
                    "FROM momentum_scan m LEFT JOIN capital_allocation_scores c "
                    "ON c.symbol=m.symbol AND c.as_of=(SELECT MAX(as_of) FROM capital_allocation_scores) "
                    "WHERE m.as_of=? ORDER BY %s DESC LIMIT 60" % order, (as_of,)).fetchall()
            pledge, conviction, adverse, catier = _veto_maps(con) if as_of else ({}, {}, {}, {})
        except sqlite3.OperationalError:
            rows = []
        finally:
            con.close()

    if not rows:
        body = ("<div class='msc'>" + _CSS + "<h2>Risk-adjusted momentum</h2>"
                "<div class='lead'>The <code>momentum_scan</code> table is not populated on this host. "
                "It is written on production by "
                "<code>python -m explosive_moves.momentum_scan</code> (nightly). This surface is "
                "read-only and never fabricates a shortlist.</div></div>")
        return HTMLResponse(_shell("Risk-adjusted momentum", body, active="momentum-scan", wide=True))

    def flag(sym, tier):
        if sym in pledge or sym in adverse or tier == "POOR":
            return "avoid"
        if tier == "WEAK":
            return "caution"
        return "clear"

    tr = ""
    for i, (s, m6, m12, vol, ra, hi, turn, rap, enp, cbl) in enumerate(rows, 1):
        tier = catier.get(s, "—")
        a = ("<span class='risk'>pledge×%d</span>" % pledge[s]) if s in pledge else \
            ("<span class='buy'>buy×%d</span>" % conviction[s]) if s in conviction else "·"
        a_rank = "2" if s in pledge else ("1" if s in conviction else "0")
        b = ("<span class='risk'>ADVERSE×%d</span>" % adverse[s]) if s in adverse else "·"
        fl = flag(s, tier)
        m6c = "pos" if (m6 or 0) >= 0 else "neg"
        m12c = "pos" if (m12 or 0) >= 0 else "neg"
        tr += ("<tr>"
               f"<td data-v='{i}'>{i}</td><td class='nm l' data-v='{_esc(s)}'>{_esc(s)}</td>"
               f"<td class='{m6c}' data-v='{m6*100:.1f}'>{m6*100:+.0f}%</td>"
               f"<td class='{m12c}' data-v='{m12*100:.1f}'>{m12*100:+.0f}%</td>"
               f"<td data-v='{vol*100:.2f}'>{vol*100:.1f}%</td>"
               f"<td data-v='{ra:.2f}'><b>{ra:.1f}</b></td>"
               f"<td data-v='{(hi or 0):.2f}'>{(hi or 0):.2f}</td>"
               f"<td data-v='{turn:.0f}'>{turn:,.0f}</td>"
               f"<td data-v='{enp:.1f}'>{enp:.0f}</td>"
               f"<td data-v='{(cbl or 0):.1f}'><b>{(cbl or 0):.0f}</b></td>"
               f"<td class='tier-{_esc(tier)} l' data-v='{_esc(tier)}'>{_esc(tier)}</td>"
               f"<td class='l' data-v='{a_rank}'>{a}</td>"
               f"<td class='l' data-v='{1 if s in adverse else 0}'>{b}</td>"
               f"<td class='f-{fl} l' data-v='{fl}'>{fl}</td></tr>")

    head = ("<tr><th data-k data-num=1>#</th><th class='l' data-k>Symbol</th>"
            "<th data-k data-num=1>6m</th><th data-k data-num=1>12m</th><th data-k data-num=1>Vol</th>"
            "<th data-k data-num=1>RISKADJ</th><th data-k data-num=1>HI52</th><th data-k data-num=1>Turn₹cr</th>"
            "<th data-k data-num=1>ENSpct</th>"
            "<th data-k data-num=1 title='C-BLEND 50/50 = mean(RISKADJ pctile, capital-allocation C pctile); S77b best overlay (Sharpe 1.32)'>C-blend</th>"
            "<th class='l' data-k title='derived from Screener.in fundamentals — migrating to BSE/NSE XBRL (primary-source policy)'>Cap-alloc (C)*</th>"
            "<th class='l' data-k>Insider (A)</th><th class='l' data-k>Credit (B)</th><th class='l' data-k>Flag</th></tr>")
    seg = ("<div class='seg'>"
           f"<a class='{'on' if sort=='riskadj' else ''}' href='/dash/momentum-scan?sort=riskadj'>Risk-adjusted momentum</a>"
           f"<a class='{'on' if sort=='cblend' else ''}' href='/dash/momentum-scan?sort=cblend'>C-blend 50/50</a>"
           f"<a class='{'on' if sort=='ens' else ''}' href='/dash/momentum-scan?sort=ens'>Equal-weight ensemble</a></div>")
    body = (
        "<div class='msc'>" + _CSS +
        "<h2>Risk-adjusted momentum — candidate scanner</h2>"
        "<div class='lead'>Ranks the liquid equity universe by <b>RISKADJ</b> (6-mo return ÷ 3-mo "
        "volatility) and the equal-weight ensemble, with the <b>C/A/B veto</b> inlined so you research "
        "the survivors, not the whole market. <b>This is a gross SELECTION lens, not alpha</b> — "
        "attribution shows momentum here is a known risk-premium beta, not proprietary skill. Use it to "
        "shortlist; do the judgement on top.</div>"
        f"<div class='bar'>as-of <b>{_esc(as_of)}</b> · click any header to sort · "
        "<b>Flag</b>: clear · caution (WEAK capital-allocation) · avoid (pledge / credit-adverse / POOR). "
        "Insider/credit history is ~4 months — a blank means no red flag <i>on record</i>, not never.</div>"
        + seg +
        "<table><thead>" + head + "</thead><tbody>" + tr + "</tbody></table>" + _SORT_JS +
        "<div class='note'>RISKADJ = split-adjusted 6-mo return ÷ 66-day return vol (anchor-invariant). "
        "Equity-only (ETFs/liquid funds excluded). Momentum is a research shortlister, not a buy list or a "
        "net-of-cost claim — see <a href='/dash/testing' style='color:#58a6ff'>Strategy validation</a>. "
        "Weights: <code>docs/calculations-and-weights.md</code>.<br>"
        "<b>C-blend 50/50</b> ranks by the mean of the RISKADJ and capital-allocation (C) percentiles — "
        "the S77b backtest's best risk-adjusted overlay (Sharpe 1.32, Calmar 1.15, MaxDD −28.2% vs "
        "RISKADJ's −41.9%; survives both walk-forward halves and 1.5× cost, "
        "<code>docs/strategy-ledger.md</code> § Experiment 2026-07-03). It is a DESCRIPTIVE tilt — "
        "NOT a hard veto, NOT a standalone ranker, NOT a buy list; a missing C fills to the neutral "
        "50th percentile (~91% live coverage).<br>"
        "<b>*Source note:</b> prices / insider (A) / credit (B) are PRIMARY-SOURCE (NSE). "
        "<b>Capital-allocation (C) is derived from Screener.in fundamentals — being migrated to "
        "BSE/NSE XBRL per the primary-source-only policy</b> (CLAUDE.md §8); treat the C column as "
        "provisional until then.</div></div>")
    return HTMLResponse(_shell("Risk-adjusted momentum", body, active="momentum-scan", wide=True))
