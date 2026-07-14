"""/dash/model-portfolios — the automated model portfolios, one screen, since 2019.

Ramana's spec (S132h): named, system-managed portfolios (STEADY-25 · PACER-25 ·
SPRINTER-25) churned continuously by their own rules — NO manual adds/removes exist
anywhere (the engine is the only writer) — reconstructed from 2019-01-01 so each has
a real track record. One stable screen: primary chart (picked portfolio vs Nifty 500)
+ comparative chart (all three + benchmark) + stats + current constituents with
engine-controlled weights + churn feed — and TIME TRAVEL: `?asof=2020-01-15` shows
the portfolio exactly as it stood then. Eligibility for a model portfolio = superior
measured Sharpe AND beats the NIFTY hurdle (ledger Tier-1); only these three qualify.

Honesty: NAV is flat-cost (0.3%/side on churn, labeled); STEADY-25 is the only family
that also survives PARTICIPATION costs — PACER/SPRINTER are gross lenses and say so.
Descriptive, not advice. Reads auto_portfolio_holdings / auto_portfolio_nav
(auto_portfolios.py, nightly); churn derived on read from consecutive snapshots.
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
PORTS = ("STEADY-25", "PACER-25", "SPRINTER-25")
COLORS = {"STEADY-25": "#3fb950", "PACER-25": "#58a6ff", "SPRINTER-25": "#d29922",
          "N500": "#8b97a7"}
_NOTES = {"STEADY-25": "quarterly · large-cap · NET-cost survivor (the champion)",
          "PACER-25": "monthly · risk-adjusted momentum · gross lens",
          "SPRINTER-25": "monthly · classic 12-mo momentum · gross lens"}

# The inspiration story (Ramana, S132h-b): the lineage behind the three runners,
# told plainly — century-old effects, honest names, admitted only after re-proving
# themselves on OUR data. Collapsible so the working screen stays clean.
_STORY = (
    "<details style='margin:14px 0'><summary style='cursor:pointer;font-size:14px;"
    "font-weight:600'>Where these portfolios come from — the inspiration</summary>"
    "<div class='honesty' style='margin-top:8px'>"
    "<p><b>The mother idea — momentum — is the most replicated finding in finance.</b> "
    "Academically it dates to Jegadeesh &amp; Titman (1993): last year's leaders keep "
    "leading, on average, for months. It has been verified across two centuries, dozens "
    "of countries and every major asset class — and practitioners (Livermore, Darvas, "
    "Driehaus, O'Neil) traded it decades before the professors named it. When we ran our "
    "own 32-signal test over 14 years of NSE data, the same verdict emerged unprompted: "
    "price strength was the only gross forward-return engine we could find.</p>"
    "<p><b>Why it exists:</b> people are slow, then social. Good news seeps into prices "
    "gradually (anchoring, staged institutional buying), then herding extends the move. "
    "It survives being famous because it is uncomfortable to hold — it crashes hard and "
    "looks like reckless chasing. The discomfort is the moat. Which is also the honest "
    "caveat: this is a risk premium you <i>harvest</i>, not stock-picking genius — beta, "
    "not skill.</p>"
    "<p><b>One squad, three runners, three temperaments:</b></p>"
    "<p>🏃 <b>SPRINTER-25</b> — momentum in its rawest academic form: rank by plain "
    "12-month return. Explosive over short stretches (our highest CAGR) and it collapses "
    "when the race turns — the literature's 'momentum crashes' are our measured −43% "
    "drawdowns. A sprinter is magnificent and cannot run a marathon.</p>"
    "<p>⏱ <b>PACER-25</b> — the first great refinement: divide the run by the shaking "
    "(return ÷ volatility). Smooth rises predict better than jumpy ones (the "
    "'frog-in-the-pan' effect; volatility-managed momentum). A pacer isn't the fastest "
    "runner — he holds the strongest <i>sustainable</i> rhythm. Best flat-cost Sharpe of "
    "everything we tested (1.13).</p>"
    "<p>🧘 <b>STEADY-25</b> — momentum married to the second-oldest anomaly: the "
    "low-volatility effect (boring stocks beat exciting ones per unit of risk, because "
    "crowds overpay for lottery-like thrills). Half strength, half calmness, held "
    "quarterly — essentially the classic 'conservative formula'. The name is the thesis: "
    "steady is what survives — the only runner still standing after real trading costs.</p>"
    "<p><b>The part that's ours:</b> the literature gave the ideas; it didn't earn them "
    "this page. Each family re-proved itself on our own point-in-time NSE record — "
    "walk-forward across both halves of 14 years, against the 0.89 buy-and-hold hurdle, "
    "then through a realistic market-impact cost model. The famous value strategies took "
    "the same exam and <b>failed it here</b> (negative alpha) — that is why there is no "
    "'Marathoner' portfolio. Century-old truths, plain names that state their temperament, "
    "admitted on evidence — and run by an engine no human hand can override.</p>"
    "</div></details>")

_CSS = """<style>
.mpf table{border-collapse:collapse;width:100%;font-size:13px}
.mpf th,.mpf td{padding:5px 8px;border-bottom:1px solid var(--line-2,#333);text-align:right}
.mpf th.l,.mpf td.l{text-align:left}
.mpf .lead,.mpf .bar{color:var(--ink-2,#999);font-size:12.5px;margin:8px 0}
.mpf .pos{color:#3fb950}.mpf .neg{color:#f85149}
.mpf .seg a{margin-right:10px;font-size:13px;padding:4px 10px;border:1px solid var(--line-2,#333);border-radius:7px;text-decoration:none}
.mpf .seg a.on{background:var(--bg-2,#15202b);font-weight:600}
.mpf .stats{display:flex;gap:18px;flex-wrap:wrap;margin:10px 0;font-size:13px}
.mpf .stats b{font-size:17px}
.mpf .honesty{border:1px solid var(--line-2,#333);border-radius:8px;padding:10px 12px;font-size:12.5px;color:var(--ink-2,#aaa);margin:12px 0}
.mpf .churn{font-size:12.5px;line-height:1.9}
.mpf .churn .in{color:#3fb950}.mpf .churn .out{color:#f85149}
</style>"""


def _svg_lines(series, w=940, h=250, pad=42):
    """series: [(label, color, [(date, val), ...])] -> inline SVG line chart."""
    allv = [v for _l, _c, pts in series for _d, v in pts if v is not None]
    alld = sorted({d for _l, _c, pts in series for d, v in pts if v is not None})
    if not allv or len(alld) < 2:
        return "<div class='bar'>no series yet</div>"
    lo, hi = min(allv), max(allv)
    if hi <= lo:
        hi = lo + 1
    dx = {d: i for i, d in enumerate(alld)}
    n = len(alld) - 1

    def X(d):
        return pad + (w - pad - 12) * dx[d] / n

    def Y(v):
        return h - 24 - (h - 40) * (v - lo) / (hi - lo)

    out = [f"<svg viewBox='0 0 {w} {h}' width='100%' role='img' aria-label='equity curves'>"]
    for gv in (1, 2, 3, 4, 6, 8):
        if lo <= gv <= hi:
            y = Y(gv)
            out.append(f"<line x1='{pad}' y1='{y:.0f}' x2='{w-12}' y2='{y:.0f}' "
                       f"stroke='#2a3340' stroke-width='1'/>"
                       f"<text x='4' y='{y+4:.0f}' fill='#8b97a7' font-size='11'>{gv}×</text>")
    for lbl, col, pts in series:
        pl = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in pts if v is not None and d in dx)
        out.append(f"<polyline points='{pl}' fill='none' stroke='{col}' stroke-width='2'/>")
        last = [(d, v) for d, v in pts if v is not None]
        if last:
            d, v = last[-1]
            out.append(f"<text x='{min(X(d)+4, w-70):.0f}' y='{Y(v)-4:.0f}' fill='{col}' "
                       f"font-size='11'>{lbl} {v:.2f}×</text>")
    for i in range(0, len(alld), max(1, len(alld) // 6)):
        out.append(f"<text x='{X(alld[i]):.0f}' y='{h-8}' fill='#8b97a7' font-size='10' "
                   f"text-anchor='middle'>{alld[i][:7]}</text>")
    out.append("</svg>")
    return "".join(out)


def _stats(navs):
    vals = [v for _d, v in navs if v is not None]
    if len(vals) < 8:
        return None
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    var = sum((x - mu) ** 2 for x in rets) / len(rets)
    ppy = 12 if len(vals) > 40 else 4
    sd = var ** 0.5
    peak, dd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    yrs = len(rets) / ppy
    return {"x": vals[-1], "cagr": (vals[-1] ** (1 / max(yrs, 1e-9)) - 1) * 100,
            "sharpe": (mu / sd * ppy ** 0.5) if sd > 0 else 0, "dd": dd * 100}


@router.get("/dash/model-portfolios", response_class=HTMLResponse)
def model_portfolios_page(p: str = "STEADY-25", asof: str = "", fmt: str = ""):
    pname = p if p in PORTS else "STEADY-25"
    asof = (asof or "").strip()[:10]
    con = _ro(HDB)
    nav, holds, snaps, latest_px = {}, [], [], {}
    snap_date = ""
    if con is not None:
        con.row_factory = sqlite3.Row
        try:
            for r in con.execute("SELECT * FROM auto_portfolio_nav ORDER BY rebal_date"):
                nav.setdefault(r["portfolio"], []).append(
                    (r["rebal_date"], r["nav"], r["bench_nav"], r["n_churned"]))
            snaps = [r["d"] for r in con.execute(
                "SELECT DISTINCT rebal_date d FROM auto_portfolio_holdings "
                "WHERE portfolio=? ORDER BY rebal_date", (pname,))]
            pick = [d for d in snaps if not asof or d <= asof]
            snap_date = pick[-1] if pick else (snaps[-1] if snaps else "")
            if snap_date:
                holds = con.execute(
                    "SELECT * FROM auto_portfolio_holdings WHERE portfolio=? AND "
                    "rebal_date=? ORDER BY rank", (pname, snap_date)).fetchall()
                ph = ",".join("?" for _ in holds)
                if holds:
                    latest_day = con.execute(
                        "SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()["d"]
                    for r in con.execute(
                            f"SELECT symbol, close FROM bhavcopy_rows WHERE trade_date=? "
                            f"AND series='EQ' AND symbol IN ({ph})",
                            [latest_day] + [h["symbol"] for h in holds]):
                        latest_px[r["symbol"]] = float(r["close"] or 0)
        except sqlite3.OperationalError:
            nav = {}
        con.close()

    if fmt == "csv" and holds:
        lines = ["portfolio,rebal_date,rank,symbol,score,target_weight"]
        for h in holds:
            lines.append(f"{pname},{snap_date},{h['rank']},{h['symbol']},"
                         f"{h['score']},{h['weight']}")
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    if not nav:
        body = ("<div class='mpf'>" + _CSS + "<h2>Model portfolios</h2>"
                "<div class='lead'>Not backfilled on this host yet — run "
                "<code>python -m src.automation.auto_portfolios --backfill</code>. "
                "This surface is read-only; portfolios are engine-managed only.</div></div>")
        return HTMLResponse(_shell("Model portfolios", body, active="model-portfolios",
                                   wide=True))

    mynav = nav.get(pname, [])
    prim = _svg_lines([
        (pname, COLORS[pname], [(d, v) for d, v, _b, _c in mynav]),
        ("Nifty 500", COLORS["N500"], [(d, b) for d, _v, b, _c in mynav]),
    ])
    comp = _svg_lines(
        [(q, COLORS[q], [(d, v) for d, v, _b, _c in nav.get(q, [])]) for q in PORTS]
        + [("Nifty 500", COLORS["N500"],
            [(d, b) for d, _v, b, _c in nav.get("STEADY-25", [])])], h=230)

    st = _stats([(d, v) for d, v, _b, _c in mynav])
    bt = _stats([(d, b) for d, _v, b, _c in mynav])
    stats = ""
    if st and bt:
        stats = ("<div class='stats'>"
                 f"<span>Since 2019: <b>{st['x']:.2f}×</b></span>"
                 f"<span>CAGR <b>{st['cagr']:.1f}%</b> (N500 {bt['cagr']:.1f}%)</span>"
                 f"<span>Sharpe <b>{st['sharpe']:.2f}</b> (N500 {bt['sharpe']:.2f})</span>"
                 f"<span>MaxDD <b>{st['dd']:.0f}%</b> (N500 {bt['dd']:.0f}%)</span></div>")

    segs = "".join(
        f"<a class='{'on' if q == pname else ''}' "
        f"href='/dash/model-portfolios?p={q}{'&asof=' + asof if asof else ''}'>{q}</a>"
        for q in PORTS)

    # churn feed (derived on read): last 6 rebalances' diffs
    churn_html = ""
    idx = snaps.index(snap_date) if snap_date in snaps else -1
    if con is None:
        con2 = None
    else:
        con2 = _ro(HDB)
    if con2 is not None and idx >= 0:
        con2.row_factory = sqlite3.Row
        feed = []
        for k in range(idx, max(0, idx - 6), -1):
            cur = {r["symbol"] for r in con2.execute(
                "SELECT symbol FROM auto_portfolio_holdings WHERE portfolio=? AND rebal_date=?",
                (pname, snaps[k]))}
            if k == 0:
                feed.append(f"<div><b>{_esc(snaps[0])}</b> inception: {len(cur)} names</div>")
                break
            prev = {r["symbol"] for r in con2.execute(
                "SELECT symbol FROM auto_portfolio_holdings WHERE portfolio=? AND rebal_date=?",
                (pname, snaps[k - 1]))}
            ins, outs = sorted(cur - prev), sorted(prev - cur)
            if ins or outs:
                feed.append(
                    f"<div><b>{_esc(snaps[k])}</b>: "
                    + (f"<span class='in'>▲ {_esc(', '.join(ins))}</span>" if ins else "")
                    + (" · " if ins and outs else "")
                    + (f"<span class='out'>▼ {_esc(', '.join(outs))}</span>" if outs else "")
                    + "</div>")
            else:
                feed.append(f"<div><b>{_esc(snaps[k])}</b>: no changes (band held)</div>")
        con2.close()
        churn_html = "<div class='churn'>" + "".join(feed) + "</div>"

    tr = ""
    tot_now = 0.0
    now_vals = {}
    for h in holds:
        cur = latest_px.get(h["symbol"])
        v = (cur / h["px"]) if (cur and h["px"]) else None
        if v:
            now_vals[h["symbol"]] = h["weight"] * v
            tot_now += h["weight"] * v
    for h in holds:
        nw = (now_vals.get(h["symbol"], 0) / tot_now * 100) if tot_now else None
        ret = ((latest_px.get(h["symbol"], 0) / h["px"] - 1) * 100
               if (not asof and h["px"] and latest_px.get(h["symbol"])) else None)
        tr += ("<tr>"
               f"<td>{h['rank'] or '—'}</td>"
               f"<td class='l'><a href='/dash/stock?sym={_esc(h['symbol'])}'>"
               f"{_esc(h['symbol'])}</a></td>"
               f"<td>{h['score']}</td>"
               f"<td>{h['weight'] * 100:.1f}%</td>"
               f"<td>{f'{nw:.1f}%' if nw else '—'}</td>"
               f"<td class='{'pos' if (ret or 0) >= 0 else 'neg'}'>"
               f"{f'{ret:+.0f}%' if ret is not None else '—'}</td></tr>")

    tt = (f"<div class='bar'>⏳ Time travel: showing the portfolio as of "
          f"<b>{_esc(snap_date)}</b>"
          + (f" (asked: {_esc(asof)})" if asof else " (latest rebalance)")
          + " — try <code>?asof=2020-01-15</code> for any past date · "
          f"<a href='/dash/model-portfolios?p={pname}&fmt=csv"
          + (f"&asof={asof}" if asof else "") + "'>CSV</a></div>")

    body = (
        "<div class='mpf'>" + _CSS + ifx.readability_css()
        + "<h2>Model portfolios — automated, since January 2019</h2>"
        + ifx.bottom_line(
            "Three named portfolios, each churned continuously by its own validated rule "
            "since <b>1 Jan 2019</b> — fully system-managed: no one (including us) can add "
            "or remove a stock by hand; the engine is the only writer. Eligibility for a "
            "model portfolio: superior measured Sharpe AND beats the NIFTY on our 14-year "
            "record. Descriptive, not advice.")
        + ifx.how_to_read_link()
        + "<div class='rd-htr'><a href='/dash/factor-league'>The league behind these →</a></div>"
        + f"<div class='seg'>{segs}</div>"
        + f"<div class='bar'><b>{pname}</b> — {_NOTES[pname]} · equal-weight 1/25 re-set at "
        "every rebalance (engine-controlled) · entries = top 25, holdings persist to rank 35 "
        "(the churn dampener)</div>"
        + stats
        + prim
        + "<h3>All portfolios vs the index</h3>" + comp
        + tt
        + f"<h3>Constituents — {_esc(snap_date)}</h3>"
        "<table><thead><tr><th>#</th><th class='l'>Symbol</th><th>Score</th>"
        "<th title='engine target weight, re-equalized each rebalance'>Target W</th>"
        "<th title='drifted weight at the latest close'>W now</th>"
        "<th>Since rebal</th></tr></thead><tbody>" + tr + "</tbody></table>"
        + "<h3>Churn — automatic, every rebalance</h3>" + churn_html
        + _STORY
        + "<div class='honesty'>NAV is <b>flat-cost</b> (0.3%/side on the churned fraction, "
        "labeled) and marked at rebalance dates. STEADY-25 is the only family that also "
        "survives PARTICIPATION-cost reality (net ~1.02 @₹50cr); PACER-25 and SPRINTER-25 "
        "are gross selection lenses shown for comparison — their real-world size capacity is "
        "small. History is a reconstruction: the SAME frozen rule applied point-in-time from "
        "2019 — no hand edits, ever. Full doctrine: <code>docs/strategy-ledger.md</code>. "
        "Not investment advice.</div></div>")
    return HTMLResponse(_shell("Model portfolios", body, active="model-portfolios", wide=True))
