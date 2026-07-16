"""/dash/momentum-scan/slow — the QUARTERLY large-cap LOWVOL_MOM portfolio (Slow rotation).

The one momentum form that survived the participation-cost recut (strategy-ledger
2026-07-02/05c: family flat-cost ~1.10 → NET ~1.02 @₹50cr, beats the index net up to
~₹100-150cr; every faster/smaller variant failed). This page shows the CURRENT quarterly
anchor maintained by src/automation/slow_rotation.py (top turnover quintile · LOWVOL_MOM
= 0.5·pctrank(mom6)+0.5·pctrank(−vol) · top-25 with a keep-while-≤35 hold band · frozen
between quarters) plus each holding's LIVE rank drift, recomputed on read from the
nightly momentum_scan snapshot (compute-on-read; the anchor table is the only state).

DESCRIPTIVE-ONLY (SEBI-safe): the validated rule's composition shown as data — not
advice, not an execution system; momentum is BETA, not selection skill. Declared child
of /dash/momentum-scan (D80 nesting); registers on momentum_view.router (append-only
EOF import there), so it rides the same durable mount. Read-only; degrades gracefully.
"""
from __future__ import annotations

import sqlite3

from fastapi.responses import HTMLResponse, PlainTextResponse

from src.automation.slow_rotation import BAND, TOPN, gate_and_rank
from src.web.momentum_view import HDB, _esc, _ro, _shell, router

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

_CSS = """<style>
.slr table{border-collapse:collapse;width:100%;font-size:13px}
.slr th,.slr td{padding:5px 8px;border-bottom:1px solid var(--line-2,#333);text-align:right}
.slr th.l,.slr td.l{text-align:left}
.slr .lead{color:var(--ink-2,#999);font-size:13px;margin:8px 0}
.slr .bar{color:var(--ink-2,#999);font-size:12px;margin:8px 0}
.slr .pos{color:#3fb950}.slr .neg{color:#f85149}
.slr .b-held{color:var(--ink-2,#999)}.slr .b-new{color:#3fb950;font-weight:600}
.slr .b-out{color:#f85149}
.slr .honesty{border:1px solid var(--line-2,#333);border-radius:8px;padding:10px 12px;
  font-size:12.5px;color:var(--ink-2,#aaa);margin:10px 0}
.slr .seg a{margin-right:12px;font-size:13px}
</style>"""


def _next_quarter(rebal: str) -> str:
    y, m = int(rebal[:4]), int(rebal[5:7])
    q = (m - 1) // 3
    ny, nm = (y + 1, 1) if q == 3 else (y, 3 * (q + 1) + 1)
    return f"{ny}-{nm:02d}-01"


def _load(con):
    anchor = [dict(r) for r in con.execute(
        "SELECT * FROM slow_rotation ORDER BY CASE role WHEN 'exited' THEN 1 ELSE 0 END, "
        "rank_at_rebal")]
    as_of = (con.execute("SELECT MAX(as_of) FROM momentum_scan").fetchone() or [None])[0]
    live = {}
    n_gated = 0
    if as_of:
        rows = [dict(r) for r in con.execute(
            "SELECT symbol, mom6, vol_66, turnover_cr FROM momentum_scan WHERE as_of=?",
            (as_of,))]
        ranked = gate_and_rank(rows)
        n_gated = len(ranked)
        live = {r["symbol"]: r for r in ranked}
    return anchor, as_of or "", live, n_gated


@router.get("/dash/momentum-scan/slow", response_class=HTMLResponse)
def slow_rotation_page(fmt: str = ""):
    con = _ro(HDB)
    anchor, as_of, live, n_gated = ([], "", {}, 0)
    if con is not None:
        con.row_factory = sqlite3.Row      # _ro() returns tuples; _load needs dict(row)
        try:
            anchor, as_of, live, n_gated = _load(con)
        except sqlite3.OperationalError:
            anchor = []
        finally:
            con.close()

    holds = [r for r in anchor if r["role"] in ("hold", "entered")]
    exited = [r for r in anchor if r["role"] == "exited"]

    if fmt == "csv":
        lines = ["symbol,role,rebal_date,rank_at_rebal,score,mom6,vol_66,turnover_cr,live_rank"]
        for r in holds + exited:
            lv = live.get(r["symbol"], {}).get("rank", "")
            lines.append(",".join(str(x if x is not None else "") for x in (
                r["symbol"], r["role"], r["rebal_date"], r["rank_at_rebal"], r["score"],
                r["mom6"], r["vol_66"], r["turnover_cr"], lv)))
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    if not holds:
        body = ("<div class='slr'>" + _CSS + "<h2>Slow rotation — quarterly LOWVOL_MOM</h2>"
                "<div class='lead'>No anchor yet on this host. It is maintained nightly by "
                "<code>python -m src.automation.slow_rotation --refresh</code> (rebalances only "
                "when the calendar quarter turns). This surface is read-only and never "
                "fabricates a portfolio.</div></div>")
        return HTMLResponse(_shell("Slow rotation", body, active="momentum-scan", wide=True))

    rebal = holds[0]["rebal_date"]
    tr = ""
    for i, r in enumerate(holds, 1):
        s = r["symbol"]
        lv = live.get(s)
        lrank = lv["rank"] if lv else None
        drift = ""
        if lrank is not None and r["rank_at_rebal"] is not None:
            d = r["rank_at_rebal"] - lrank
            drift = f"<span class='pos'>▲{d}</span>" if d > 0 else \
                    f"<span class='neg'>▼{-d}</span>" if d < 0 else "▬"
        inband = "—"
        if lrank is not None:
            inband = ("<span class='pos'>✓ ≤" + str(BAND) + "</span>") if lrank <= BAND \
                else "<span class='neg'>✗ would drop</span>"
        role = ("<span class='b-new'>entered</span>" if r["role"] == "entered"
                else "<span class='b-held'>held</span>")
        m6 = r["mom6"]
        m6c = "pos" if (m6 or 0) >= 0 else "neg"
        tr += ("<tr>"
               f"<td data-v='{i}'>{i}</td>"
               f"<td class='l'><a href='/dash/stock?sym={_esc(s)}'>{_esc(s)}</a></td>"
               f"<td class='l'>{role}</td>"
               f"<td>{r['rank_at_rebal']}</td>"
               f"<td>{lrank if lrank is not None else '—'}</td>"
               f"<td class='l'>{drift}</td>"
               f"<td class='l'>{inband}</td>"
               f"<td>{(r['score'] or 0) * 100:.0f}</td>"
               f"<td class='{m6c}'>{(m6 or 0) * 100:+.0f}%</td>"
               f"<td>{(r['vol_66'] or 0) * 100:.1f}%</td>"
               f"<td>{(r['turnover_cr'] or 0):,.0f}</td></tr>")

    ex_txt = " · ".join(
        f"<a href='/dash/stock?sym={_esc(r['symbol'])}' class='b-out'>{_esc(r['symbol'])}</a>"
        for r in exited) or "none"

    body = (
        "<div class='slr'>" + _CSS + ifx.readability_css()
        + "<h2>Slow rotation — quarterly large-cap LOWVOL_MOM</h2>"
        + ifx.bottom_line(
            "The one momentum form that survived REAL trading costs in our testing: large-cap, "
            "low-volatility momentum, rebalanced QUARTERLY with a wide hold band. Shown as "
            "<b>data about the validated rule</b> — a defensive tilt, not advice, and not a fast "
            "signal: between quarters, rank moves are drift, not trades.")
        + ifx.how_to_read_link()
        + "<div class='rd-htr'><a href='/dash/strategy-ref?p=momentum-riskadj'>Methodology →</a></div>"
        + "<div class='seg'><a href='/dash/momentum-scan'>⇄ Daily scanner</a>"
        f"<a href='/dash/momentum-scan/slow?fmt=csv'>Download CSV</a></div>"
        f"<div class='bar'>anchor set <b>{_esc(rebal)}</b> · latest data <b>{_esc(as_of)}</b> · "
        f"next rebalance <b>{_esc(_next_quarter(rebal))}</b> · gated universe (top turnover "
        f"quintile) <b>{n_gated}</b> names · band: members stay while live rank ≤ {BAND}, "
        f"portfolio refills to {TOPN}</div>"
        "<table><thead><tr><th>#</th><th class='l'>Symbol</th><th class='l'>Role</th>"
        "<th title='rank when the quarterly anchor was set'>Rebal rank</th>"
        "<th title='rank recomputed on today&#39;s data, same gate and score'>Live rank</th>"
        "<th class='l'>Drift</th><th class='l' title='would this name survive if the rebalance "
        "were today?'>In band</th><th title='LOWVOL_MOM percentile blend ×100'>Score</th>"
        "<th>6m</th><th>Vol</th><th>Turn₹cr</th></tr></thead>"
        "<tbody>" + tr + "</tbody></table>"
        f"<div class='bar'>exited at last rebalance: {ex_txt}</div>"
        "<div class='honesty'><b>The honest numbers (why this page exists):</b> across 32 tested "
        "signals over 14 years, only the slow momentum family beat holding the Nifty 500 — and only "
        "THIS form survived a realistic participation-cost model: <b>net return/vol ~1.02 at ₹50cr</b>, "
        "beating the index net up to a capacity ceiling of roughly ₹100–150cr "
        "(<code>docs/strategy-ledger.md</code> §§ 2026-06-24 / 07-02 / 07-05c). Return/vol is mean "
        "return ÷ volatility, annualised — NOT a Sharpe ratio: no risk-free rate is subtracted, so it "
        "reads higher than a textbook Sharpe would. Flat-cost headline "
        "numbers elsewhere (1.10–1.32) are NOT net claims. Attribution says this return is a known "
        "risk-premium <b>beta</b> (defensive momentum), not proprietary skill — which is exactly why "
        "it is shown openly. Quarterly clock and the hold band ARE the strategy: they keep turnover "
        "(and therefore cost) small enough to survive. Descriptive only — not investment advice.</div>"
        "</div>")
    return HTMLResponse(_shell("Slow rotation", body, active="momentum-scan", wide=True))
