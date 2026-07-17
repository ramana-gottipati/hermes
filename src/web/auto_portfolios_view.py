"""/dash/model-portfolios — the automated model portfolios, one screen, since 2019.

Ramana's spec (S132h): named, system-managed portfolios (STEADY-25 · PACER-25 ·
SPRINTER-25) churned continuously by their own rules — NO manual adds/removes exist
anywhere (the engine is the only writer) — reconstructed from 2019-01-01 so each has
a real track record. One stable screen: primary chart (picked portfolio vs Nifty 500)
+ comparative chart (all three + benchmark) + stats + current constituents with
engine-controlled weights + churn feed — and TIME TRAVEL: `?asof=2020-01-15` shows
the portfolio exactly as it stood then. Eligibility for a model portfolio = superior
measured RETURN/VOL AND beats the NIFTY hurdle (ledger Tier-1); only these three qualify.

The criterion says return/vol, not Sharpe, because that is what was measured (D142): the
research figure it gates on is mean/sd annualised with no risk-free rate subtracted. The
RULE is unchanged and no book's eligibility moves — the NIFTY hurdle it is compared against
is computed on the same no-rf basis, so both sides shift together and the verdict is
identical. Only the name was wrong.

Honesty: NAV is flat-cost (0.3%/side on churn, labeled); STEADY-25 is the only family
that also survives PARTICIPATION costs — PACER/SPRINTER are gross lenses and say so.
Descriptive, not advice. Reads auto_portfolio_holdings / auto_portfolio_nav
(auto_portfolios.py, nightly); churn derived on read from consecutive snapshots.
"""
from __future__ import annotations

import sqlite3
from datetime import date

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
PORTS = ("STEADY-25", "CRAFTSMAN-25", "PACER-25", "SPRINTER-25")
COLORS = {"STEADY-25": "#3fb950", "CRAFTSMAN-25": "#b19cf7", "PACER-25": "#58a6ff",
          "SPRINTER-25": "#d29922", "N500": "#8b97a7"}
_NOTES = {"STEADY-25": "quarterly · large-cap · the ONLY book fundable net of participation cost (the champion)",
          "CRAFTSMAN-25": "monthly · quality-momentum blend (strength + delivery + calm) · ⚠ GROSS-LENS DEMONSTRATION — not fundable net of cost",
          "PACER-25": "monthly · risk-adjusted momentum · ⚠ GROSS-LENS DEMONSTRATION — not fundable net of cost",
          "SPRINTER-25": "monthly · classic 12-mo momentum · ⚠ GROSS-LENS DEMONSTRATION — not fundable net of cost"}

# Tier D (D143 strategy-families framework): the three monthly runners are flat-cost GROSS lenses —
# their headline CAGR collapses net of realistic participation cost. Shown for education, never funded.
GROSS_LENS = {"PACER-25", "SPRINTER-25", "CRAFTSMAN-25"}
_NET_NOTE = {
    "PACER-25": "Its RISKADJ core: gross 35.6% CAGR → NET −1.4% at realistic participation cost (cost_realism.csv). Not fundable.",
    "SPRINTER-25": "Flat-cost 12-mo-momentum lens; net of participation cost this family collapses like PACER (RISKADJ 35.6%→−1.4%). Not fundable.",
    "CRAFTSMAN-25": "Flat-cost quality-momentum lens; net of participation cost this family collapses like PACER (RISKADJ 35.6%→−1.4%). Not fundable.",
}

# Tier A (D143 §8, action #2 — Ramana-ratified): STEADY-25 is the FUNDABLE CORE — the one book that
# beats the index NET of realistic participation cost. Net CAGR is capacity-tiered (pinned + freshly
# re-verified 2026-07-17 via cost_participation.py; reproduces the recorded 16AE/#602 numbers to the digit).
FUNDABLE = {"STEADY-25"}
_FUND_NOTE = ("net of realistic participation cost it BEATS the index at investable size — "
              "net CAGR 19.2% @₹25cr · 18.1% @₹50cr · 16.5% @₹100cr (index 15.3%); "
              "capacity ceiling ~₹150cr, beyond which it no longer beats buy-and-hold.")

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
    "runner — he holds the strongest <i>sustainable</i> rhythm. Best flat-cost return/vol of "
    "everything we tested (1.13).</p>"
    "<p>🛠 <b>CRAFTSMAN-25</b> — the blend our factor zoo scored gentlest of the "
    "fast runners: 40% risk-adjusted strength, 30% REAL delivery (are strong hands "
    "actually taking the stock home?), 30% calmness. Strength that is being "
    "genuinely accumulated, not just quoted higher.</p>"
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


def _cadence(dates):
    """(elapsed years, rebalances/yr) read from the actual dates — never guessed.

    A row-count heuristic cannot tell a 14-year QUARTERLY book from a 5-year monthly
    one: STEADY-25 rebalances quarterly, so its 58 real points spanning 2012-06..2026-07
    were read as 58 monthly points = 4.8 years, trebling its CAGR and annualising its
    vol by sqrt(12) instead of sqrt(4). Both sibling books derive years from dates
    (model_books_view._stats, classics_view._book_stats); this matches them.
    """
    try:
        d0, d1 = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
        gaps = sorted((date.fromisoformat(dates[i]) - date.fromisoformat(dates[i - 1])).days
                      for i in range(1, len(dates)))
    except (ValueError, TypeError, IndexError):
        return None, None
    yrs = (d1 - d0).days / 365.25
    med = gaps[len(gaps) // 2] if gaps else 0
    if yrs <= 0 or med <= 0:
        return None, None
    return yrs, max(round(365.25 / med), 1)


def _stats(navs):
    """{multiple, CAGR%, return/vol, maxDD%} for a (date, nav) series, or None.

    `retvol` is mean/sd annualised — NOT a Sharpe ratio: no risk-free rate is
    subtracted, so it reads high against a textbook Sharpe. A true Sharpe needs a
    primary-source rf ingest (Guardrail #8) and is queued with the TR-benchmark
    re-cut, which moves the same figures. Render it as "Return/vol", never "Sharpe".
    """
    pts = [(d, v) for d, v in navs if v is not None]
    if len(pts) < 8:
        return None
    yrs, ppy = _cadence([d for d, _v in pts])
    if not yrs:
        return None
    vals = [v for _d, v in pts]
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = (sum((x - mu) ** 2 for x in rets) / len(rets)) ** 0.5
    peak, dd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    return {"x": vals[-1], "cagr": (vals[-1] ** (1 / yrs) - 1) * 100,
            "retvol": (mu / sd * ppy ** 0.5) if sd > 0 else 0, "dd": dd * 100}


@router.get("/dash/model-portfolios", response_class=HTMLResponse)
def model_portfolios_page(p: str = "STEADY-25", asof: str = "", fmt: str = "",
                          since: str = ""):
    pname = p if p in PORTS else "STEADY-25"
    asof = (asof or "").strip()[:10]
    since = since if since in ("2019", "2022") else ""      # default = full 2012 history
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

    if since:
        cut = since + "-01-01"
        reb = {}
        for q, rows_ in nav.items():
            rows_ = [r for r in rows_ if r[0] >= cut]
            if rows_:
                n0 = rows_[0][1] or 1.0
                b0_ = rows_[0][2] or None
                reb[q] = [(d, round(v / n0, 4) if v else None,
                           round(b / b0_, 4) if (b and b0_) else None, c)
                          for d, v, b, c in rows_]
        nav = reb

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
        lbl = since or "2012"
        stats = ("<div class='stats'>"
                 f"<span>Since {lbl}: <b>{st['x']:.2f}×</b></span>"
                 f"<span>CAGR <b>{st['cagr']:.1f}%</b> (N500 {bt['cagr']:.1f}%)</span>"
                 f"<span title='Mean return ÷ volatility, annualised. NOT a Sharpe "
                 f"ratio — no risk-free rate is subtracted, so it reads higher than "
                 f"a textbook Sharpe would.'>Return/vol <b>{st['retvol']:.2f}</b> "
                 f"(N500 {bt['retvol']:.2f})</span>"
                 f"<span>MaxDD <b>{st['dd']:.0f}%</b> (N500 {bt['dd']:.0f}%)</span></div>")
        if pname in GROSS_LENS:
            stats += ("<div style='margin-top:6px;padding:6px 10px;border-left:3px solid #f85149;"
                      "background:rgba(248,81,73,.08);color:#f85149;font-size:.85em;border-radius:4px'>"
                      "⚠ <b>GROSS-LENS DEMONSTRATION</b> — the CAGR above is <b>flat-cost</b>; this book "
                      "is <b>NOT fundable</b> net of participation cost. " + _NET_NOTE[pname] + "</div>")
        if pname in FUNDABLE:
            stats += ("<div style='margin-top:6px;padding:6px 10px;border-left:3px solid #3fb950;"
                      "background:rgba(63,185,80,.08);color:#3fb950;font-size:.85em;border-radius:4px'>"
                      "✅ <b>FUNDABLE CORE</b> — the ONLY book that survives realistic cost: " + _FUND_NOTE
                      + "</div>")

    since_chips = " · ".join(
        ("<b>" if (since or "2012") == (y or "2012") else "")
        + f"<a href='/dash/model-portfolios?p={pname}"
        + (f"&since={y}" if y else "") + f"'>{y or '2012'}</a>"
        + ("</b>" if (since or "2012") == (y or "2012") else "")
        for y in ("", "2019", "2022"))
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

    # Tier B (D143 §8 action #3): the survivability overlay — pair the FUNDABLE CORE with ~zero-corr
    # ballast (G-sec / gold) to cut drawdown. Measured on STEADY-25's own quarterly NAV (ledger 16AX,
    # steady_ballast.py); descriptive. Only shown on the core (it's the only fundable book).
    ballast_html = ""
    if pname == "STEADY-25":
        _br = ("<tr><td>{}</td><td>{}</td><td>{}</td><td style='color:#3fb950'>{}</td></tr>")
        ballast_html = (
            "<div style='margin:14px 0;padding:10px 12px;border:1px solid #30363d;border-radius:6px'>"
            "<h3 style='margin:0 0 4px'>🛟 Survivability overlay — pair the core with ballast (descriptive)</h3>"
            "<p style='font-size:.85em;color:#8b97a7;margin:.3em 0 .6em'>STEADY-25 is already defensive, but "
            "pairing it with a ~zero-correlation sleeve — <b>G-sec bonds</b> (corr +0.08) or <b>gold</b> "
            "(corr −0.24) — roughly <b>halves the drawdown</b> for ~1–2pp of CAGR, and every mix still beats "
            "the index (13.4% this window). Native 2012+, 57 quarters (ledger 16AX). Descriptive, primary-source; "
            "return/vol is not a Sharpe; gold's return is regime-loaded (2012–26 bull) — not a forward promise. "
            "The dial is the design layer of <code>docs/portfolio-layer-design.md</code>; weights are the owner's "
            "risk-appetite choice, not an optimiser's.</p>"
            "<table class='pt' style='font-size:.9em'><tr><th style='text-align:left'>mix — core / G-sec / gold</th>"
            "<th>CAGR</th><th>ret/vol</th><th>MaxDD</th></tr>"
            + _br.format("100 / 0 / 0 — core alone", "17.1%", "1.09", "−19.1%")
            + _br.format("80 / 20 / 0 — + G-sec", "15.1%", "1.18", "−14.7%")
            + _br.format("80 / 0 / 20 — + gold", "16.2%", "1.30", "−11.6%")
            + _br.format("<b>80 / 10 / 10 — balanced</b>", "<b>15.7%</b>", "<b>1.25</b>", "<b>−13.1%</b>")
            + _br.format("70 / 10 / 20 — survivability-tilted", "15.2%", "1.39", "−9.4%")
            + "</table></div>")

    body = (
        "<div class='mpf'>" + _CSS + ifx.readability_css()
        + "<h2>Model portfolios — automated, since June 2012</h2>"
        + ifx.bottom_line(
            "Three named portfolios, each churned continuously by its own validated rule "
            "since <b>June 2012</b> — the start of the VALIDATED walk-forward window — fully system-managed: no one (including us) can add "
            "or remove a stock by hand; the engine is the only writer. Eligibility for a "
            "model portfolio: superior measured return/vol AND beats the NIFTY on our 14-year "
            "record. Descriptive, not advice.")
        + ifx.how_to_read_link()
        + "<div class='rd-htr'><a href='/dash/factor-league'>The league behind these →</a></div>"
        + f"<div class='seg'>{segs}</div>"
        + f"<div class='bar'>View since: {since_chips} (curves rebased to 1× at the chosen start)</div>"
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
        + ballast_html
        + "<h3>Churn — automatic, every rebalance</h3>" + churn_html
        + _STORY
        + "<div class='bar'><b>Origin: 📚 CLASSIC</b> — all four runners are public, bookish families (provenance map: <code>docs/strategies/origins.md</code>); none is proprietary. Ramana-original and house-proprietary strategies live on <a href='/dash/strategist'>Strategist</a>.</div>"
        + "<div class='honesty'>NAV is <b>flat-cost</b> (0.3%/side on the churned fraction, "
        "labeled) and marked at rebalance dates. <b>STEADY-25 is the ONLY book fundable net of "
        "participation cost</b> (net ~1.02 @₹50cr, the S163-signed benchmark). <b>PACER-25, "
        "SPRINTER-25 and CRAFTSMAN-25 are GROSS-LENS DEMONSTRATIONS — not fundable net of cost</b>: "
        "their flat-cost headline collapses under realistic participation cost (e.g. the RISKADJ core "
        "of PACER-25 goes 35.6% gross → −1.4% net; <code>cost_realism.csv</code>). They are shown for "
        "education, never as investable portfolios. History is a reconstruction: the SAME frozen rule "
        "applied point-in-time from 2019 — no hand edits, ever. Full doctrine: "
        "<code>docs/strategy-ledger.md</code> · <code>docs/strategy-families-framework.md</code> (D143). "
        "Not investment advice.</div></div>")
    return HTMLResponse(_shell("Model portfolios", body, active="model-portfolios", wide=True))
