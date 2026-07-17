"""/dash/factor-league — the classic strategy families, ranked by OUR measured numbers.

Ramana's ask (S132g): the famous "premium" equity strategies (momentum, quality,
low-vol, value…) as ONE ranked league — but ranked by the return/vol + alpha measured on
OUR 14 years of NSE data (docs/strategy-ledger.md § Tier-1 factor zoo + the 2026-07
cost-realism experiments), never by textbook claims. Each live family shows its
CURRENT top-25 participants; the NET champion (STEADY-25, the quarterly LOWVOL_MOM
anchor) is the automatic portfolio; a churn feed shows every roster change.

Honesty spine: the ranking ratio is FLAT-COST and carries NO risk-free subtraction — two
independent conventions, both disclosed on the star (D142; the ratio is return/vol, not a
Sharpe, and reads high against one). The C-BLEND lesson is why cost is labeled; the
failed families are shown WITH their failure numbers (that is the point of the
league — the menu includes what does NOT work); momentum's alpha is a known
risk-premium BETA, not selection skill. Descriptive-only, not advice, SEBI-safe.

Reads: factor_league / factor_league_churn (factor_league.py, nightly) ·
slow_rotation (the champion's canonical quarterly anchor) · momentum_scan (context
columns). Isolated router; durable mount via v2_surfaces._ROUTER_SPECS; degrades
gracefully on empty hosts.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.web.momentum_view import HDB, _esc, _ro, _shell

try:
    from src.web import infographics as ifx
except Exception:  # pragma: no cover
    class ifx:  # type: ignore
        @staticmethod
        def readability_css():
            return ""

        @staticmethod
        def bottom_line(t):
            return f"<div>{t}</div>"

        @staticmethod
        def how_to_read_link():
            return ""

router = APIRouter()

_CSS = """<style>
.flg table{border-collapse:collapse;width:100%;font-size:13px}
.flg th,.flg td{padding:6px 8px;border-bottom:1px solid var(--line-2,#333);text-align:right}
.flg th.l,.flg td.l{text-align:left}
.flg .lead,.flg .bar{color:var(--ink-2,#999);font-size:12.5px;margin:8px 0}
.flg .pos{color:#3fb950}.flg .neg{color:#f85149}
.flg .champ{color:#3fb950;font-weight:700}.flg .gross{color:#d29922}
.flg .fail{color:#f85149}.flg .bench{color:var(--ink-2,#999);font-style:italic}
.flg .honesty{border:1px solid var(--line-2,#333);border-radius:8px;padding:10px 12px;
  font-size:12.5px;color:var(--ink-2,#aaa);margin:12px 0}
.flg .seg a{margin-right:12px;font-size:13px}
.flg .churn{font-size:12.5px;line-height:1.9}
.flg .churn .in{color:#3fb950}.flg .churn .out{color:#f85149}
</style>"""

# The league table — FROZEN measured results, restated from docs/strategy-ledger.md
# (§ Tier-1 leaderboard, § BLOCKING FAILURE MODELS, §§ 2026-07-02/05c cost realism).
# Display copy only: the ledger is the single source; do not edit numbers here
# without a ledger citation. (name, family, flat_retvol, cagr%, maxdd%, alpha_note,
# status, roster_key)  status: champion|gross|filter|fail|reject|bench
_LEAGUE = [
    ("STEADY-25", "Low-volatility momentum · quarterly large-cap (LOWVOL_MOM)",
     1.10, 18.5, -26.0, "the ONLY family that beats the index NET of real costs: "
     "1.02 @₹50cr, capacity ~₹100-150cr", "champion", "steady"),
    ("LOWVOL", "Low volatility, pure — the defensive HALF of the champion",
     0.96, 12.7, -21.3, "net of cost (16BA): shallowest drawdown of any factor (−21%), but ALONE it "
     "fails the index (−2.6%). Its calm is exactly what makes LOWVOL_MOM the champion once blended "
     "with momentum — the basket shows the defensive names", "filter", "lowvol"),
    ("PACER-25", "Risk-adjusted momentum (RISKADJ = 6-mo return ÷ 3-mo vol)",
     1.13, 28.6, -33.1, "best flat-cost return/vol of all 32 signals; NET fails at scale "
     "on its monthly clock — a gross selection lens", "gross", "pacer"),
    ("CRAFTSMAN-25", "Quality + momentum blend (QUAL_MOM)",
     1.10, 20.1, -26.7, "gentlest fast-clock drawdowns; runs as a model portfolio "
     "since 2012", "gross", "craftsman"),
    ("SPRINTER-25", "Classic 12-month momentum (MOM12)",
     1.06, 30.0, -43.0, "highest CAGR, brutal drawdowns; gross lens", "gross", "sprinter"),
    ("MOM6", "6-month momentum, pure (MOM6)",
     0.60, 14.1, -46.9, "net of cost (16BA): a shorter, wilder SPRINTER — FAILS the index alone "
     "(−1.2%) with −47% drawdowns; the momentum half before it is tamed by low-vol", "fail", "mom6"),
    ("—", "Delivery momentum (DELIV_MOM)",
     0.85, None, -45.0, "delivery % added no standalone edge", "fail", None),
    ("—", "Quality standalone (pt14)",
     0.76, None, None, "α ≈ 0 — quality does not RANK returns; it works as a veto/filter "
     "attached to momentum", "filter", None),
    ("—", "Value (earnings yield)",
     0.70, None, -71.0, "α +0.4% — no index-beating edge, deep drawdowns", "fail", None),
    ("—", "Deep value (book yield)",
     0.62, None, -82.0, "α NEGATIVE (−1.8…−2.2%), β 1.54 — a value-trap engine; "
     "HARD-REJECTED", "reject", None),
    ("Nifty 500", "Buy & hold (the hurdle every strategy must beat)",
     0.89, 15.3, -30.1, "the honest benchmark", "bench", None),
]

_STATUS_TXT = {"champion": "NET CHAMPION", "gross": "gross lens", "filter": "veto/filter",
               "fail": "FAILED", "reject": "REJECTED", "bench": "benchmark"}


def _steady_panel(con):
    try:
        rows = con.execute(
            "SELECT symbol, role, rebal_date, rank_at_rebal FROM slow_rotation "
            "WHERE role IN ('hold','entered') ORDER BY rank_at_rebal LIMIT 5").fetchall()
        n = con.execute("SELECT COUNT(*) c FROM slow_rotation "
                        "WHERE role IN ('hold','entered')").fetchone()["c"]
    except sqlite3.OperationalError:
        return "<div class='bar'>STEADY-25 anchor not present on this host.</div>"
    if not rows:
        return "<div class='bar'>STEADY-25 anchor not seeded yet.</div>"
    top = " · ".join(f"<a href='/dash/stock?sym={_esc(r['symbol'])}'>{_esc(r['symbol'])}</a>"
                     for r in rows)
    return (f"<div class='bar'><b>STEADY-25 — the automatic portfolio</b> (net champion): "
            f"{n} holdings anchored {_esc(rows[0]['rebal_date'])}, frozen until the quarter "
            f"turns. Top of book: {top} … "
            f"<a href='/dash/momentum-scan/slow'>full portfolio + drift →</a></div>")


def _roster_rows(con, fam_key):
    fam = fam_key.upper()
    try:
        return con.execute(
            "SELECT f.symbol, f.rank, f.score, m.mom6, m.mom12, m.vol_66, m.turnover_cr "
            "FROM factor_league f LEFT JOIN momentum_scan m ON m.symbol=f.symbol "
            "AND m.as_of=f.as_of WHERE f.family=? ORDER BY f.rank", (fam,)).fetchall()
    except sqlite3.OperationalError:
        return []


def _churn_html(con):
    try:
        rows = con.execute(
            "SELECT family, symbol, action, on_date, rank FROM factor_league_churn "
            "ORDER BY on_date DESC, family, action LIMIT 60").fetchall()
    except sqlite3.OperationalError:
        rows = []
    steady = []
    try:
        steady = con.execute(
            "SELECT symbol, role, rebal_date FROM slow_rotation WHERE role IN "
            "('entered','exited') ORDER BY role").fetchall()
    except sqlite3.OperationalError:
        pass
    out = []
    if steady:
        ins = [r["symbol"] for r in steady if r["role"] == "entered"]
        outs = [r["symbol"] for r in steady if r["role"] == "exited"]
        d = steady[0]["rebal_date"]
        if ins:
            out.append(f"<div><b>STEADY-25</b> {_esc(d)} (quarterly rebalance): "
                       f"<span class='in'>▲ {len(ins)} entered</span>"
                       + (f" · <span class='out'>▼ {len(outs)} exited "
                          f"({_esc(', '.join(outs[:6]))})</span>" if outs else "") + "</div>")
    for r in rows:
        arrow = ("<span class='in'>▲ enter</span>" if r["action"] == "enter"
                 else "<span class='out'>▼ exit</span>")
        rk = f" @#{r['rank']}" if r["rank"] else ""
        out.append(f"<div><b>{_esc(r['family'])}-25</b> {_esc(r['on_date'])}: {arrow} "
                   f"<a href='/dash/stock?sym={_esc(r['symbol'])}'>{_esc(r['symbol'])}</a>{rk}</div>")
    if not out:
        out = ["<div class='bar'>No roster changes recorded yet (the feed builds from "
               "the second nightly refresh onward).</div>"]
    return "<div class='churn'>" + "".join(out[:40]) + "</div>"


@router.get("/dash/factor-league", response_class=HTMLResponse)
def factor_league_page(family: str = "", fmt: str = ""):
    con = _ro(HDB)
    roster, churn, steady, as_of = [], "", "", ""
    fam_key = family.strip().lower() if family.strip().lower() in ("pacer", "sprinter", "mom6", "lowvol") else ""
    if con is not None:
        con.row_factory = sqlite3.Row
        try:
            r = con.execute("SELECT MAX(as_of) d FROM factor_league").fetchone()
            as_of = (r["d"] if r else "") or ""
        except sqlite3.OperationalError:
            as_of = ""
        if fam_key:
            roster = _roster_rows(con, fam_key)
        churn = _churn_html(con)
        steady = _steady_panel(con)
        con.close()

    if fmt == "csv" and fam_key:
        lines = ["family,rank,symbol,score,mom6,mom12,vol_66,turnover_cr"]
        for r in roster:
            lines.append(f"{fam_key.upper()},{r['rank']},{r['symbol']},{r['score']},"
                         f"{r['mom6']},{r['mom12']},{r['vol_66']},{r['turnover_cr']}")
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    lg = ""
    for name, famtxt, sh, cagr, dd, note, status, rkey in _LEAGUE:
        cls = {"champion": "champ", "gross": "gross", "fail": "fail",
               "reject": "fail", "filter": "gross", "bench": "bench"}[status]
        excess = f"{cagr - 15.3:+.1f}%" if cagr is not None and status != "bench" else "—"
        link = ""
        if rkey == "steady":
            link = "<a href='/dash/momentum-scan/slow'>portfolio →</a>"
        elif rkey == "craftsman":
            link = "<a href='/dash/model-portfolios?p=CRAFTSMAN-25'>portfolio →</a>"
        elif rkey:
            link = f"<a href='/dash/factor-league?family={rkey}'>25 names →</a>"
        lg += ("<tr>"
               f"<td class='l'><b>{_esc(name)}</b></td>"
               f"<td class='l'>{famtxt}</td>"
               f"<td data-v='{sh}'><b>{sh:.2f}</b></td>"
               f"<td>{f'{cagr:.1f}%' if cagr is not None else '—'}</td>"
               f"<td>{excess}</td>"
               f"<td>{f'{dd:.0f}%' if dd is not None else '—'}</td>"
               f"<td class='l {cls}'>{_STATUS_TXT[status]}</td>"
               f"<td class='l'>{note}</td>"
               f"<td class='l'>{link}</td></tr>")

    roster_html = ""
    if fam_key and roster:
        pname = {"pacer": "PACER-25 (risk-adjusted momentum)",
                 "sprinter": "SPRINTER-25 (12-month momentum)",
                 "mom6": "MOM6 basket (6-month momentum — research, not fundable)",
                 "lowvol": "LOWVOL basket (pure low volatility — research, not fundable)"}[fam_key]
        rt = ""
        for r in roster:
            m12 = r["mom12"]
            rt += ("<tr>"
                   f"<td>{r['rank']}</td>"
                   f"<td class='l'><a href='/dash/stock?sym={_esc(r['symbol'])}'>"
                   f"{_esc(r['symbol'])}</a></td>"
                   f"<td>{r['score']}</td>"
                   f"<td class='{'pos' if (r['mom6'] or 0) >= 0 else 'neg'}'>"
                   f"{(r['mom6'] or 0) * 100:+.0f}%</td>"
                   f"<td class='{'pos' if (m12 or 0) >= 0 else 'neg'}'>"
                   f"{(m12 or 0) * 100:+.0f}%</td>"
                   f"<td>{(r['vol_66'] or 0) * 100:.1f}%</td>"
                   f"<td>{(r['turnover_cr'] or 0):,.0f}</td></tr>")
        roster_html = (
            f"<h3>{pname} — current participants</h3>"
            "<div class='bar'>Monthly-clock GROSS lens: this roster drifts daily and is a "
            "research shortlist, NOT the auto-portfolio (that is STEADY-25). "
            f"<a href='/dash/factor-league?family={fam_key}&fmt=csv'>Download CSV</a></div>"
            "<table><thead><tr><th>#</th><th class='l'>Symbol</th><th>Score</th><th>6m</th>"
            "<th>12m</th><th>Vol</th><th>Turn₹cr</th></tr></thead>"
            "<tbody>" + rt + "</tbody></table>")

    body = (
        "<div class='flg'>" + _CSS + ifx.readability_css()
        + "<h2>Factor league — the classic strategies, ranked by OUR data</h2>"
        + ifx.bottom_line(
            "The famous 'premium' strategy families — momentum, quality, low-vol, value — "
            "measured head-to-head on 14 years of NSE data and ranked by what they ACTUALLY "
            "delivered here. The league's verdict: <b>strength strategies top the table, value "
            "strategies fail it</b>, and only ONE family survives real trading costs — the "
            "quarterly low-vol momentum that runs as the automatic portfolio "
            "<b>STEADY-25</b>. Descriptive, not advice.")
        + ifx.how_to_read_link()
        + "<div class='rd-htr'><a href='/dash/strategy-ref?p=momentum-riskadj'>Methodology →</a>"
        + " · <a href='/dash/testing'>How we validate →</a></div>"
        + steady
        + "<div class='bar'><b>Origin: 📚 CLASSIC</b> — public, bookish families measured on OUR data. Your own (🧑) and proprietary (🏠) strategies live on <a href='/dash/strategist'>Strategist</a>; the full provenance map is <code>docs/strategies/origins.md</code>.</div>"
        + f"<div class='bar'>rosters as-of <b>{_esc(as_of) or '—'}</b> · Return-vol/CAGR/DD = the "
        "RECORDED 2012-26 walk-forward (top-25 monthly, ₹5cr universe, FLAT costs — labeled; "
        "net reality is in the Status column) · excess = CAGR minus Nifty 500's 15.3%</div>"
        "<table><thead><tr><th class='l'>Portfolio</th><th class='l'>Strategy family</th>"
        "<th title='flat-cost walk-forward return/vol, 2012-26. Mean return ÷ volatility, "
        "annualised — NOT a Sharpe ratio: no risk-free rate is subtracted, so it reads "
        "higher than a textbook Sharpe would.'>Return/vol*</th><th>CAGR</th>"
        "<th>Excess</th><th>MaxDD</th><th class='l'>Status</th><th class='l'>The verdict"
        "</th><th class='l'></th></tr></thead><tbody>" + lg + "</tbody></table>"
        + roster_html
        + "<h3>Churn — every roster change</h3>" + churn
        + "<div class='honesty'><b>Read the star:</b> Return/vol* is FLAT-COST (0.3%/turnover) "
        "AND has no risk-free rate subtracted — so it is not a Sharpe, and reads higher than "
        "one. Both are conventions of the measurement, not results; it is still essentially "
        "the number most backtests quote. Under a realistic participation-cost model the fast "
        "monthly families do NOT keep their headline (that is why the table's only NET "
        "CHAMPION is the quarterly form). Momentum's edge here is a known risk-premium "
        "<b>beta</b>, not stock-selection skill (residual α failed t≥3); value's alpha was "
        "NEGATIVE on our data. Every number restates the frozen record in "
        "<code>docs/strategy-ledger.md</code> — this page may not soften them. Not investment "
        "advice.</div></div>")
    return HTMLResponse(_shell("Factor league", body, active="factor-league", wide=True))
