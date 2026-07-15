"""/dash/classics — the famous public equity strategies, run on OUR data.

Ramana's ask (S145): the name-brand strategies every serious desk respects — Magic Formula,
CANSLIM, Piotroski, Coffee Can, GARP, Graham, Quality, Low-Vol — catalogued honestly and made
RUNNABLE as screens over the NSE universe, each with a live top-25 roster the analyst inspects.

Sibling of /dash/factor-league (which ranks the raw factor FAMILIES on OUR measured return/vol).
This page is the named, multi-signal STRATEGIES. Rosters come from famous_strategies.py (nightly,
isolated table classic_roster). Every strategy card states the public rule, the way WE express it,
and its computability on our point-in-time data — proxies (Magic Formula's E/P; Piotroski's 5-of-9)
are LABELED, and the value strategies are shown NEXT TO what they actually delivered here (deep
value = HARD-REJECTED on 14y of NSE data). Descriptive-only, not advice, SEBI-safe.

Isolated router; durable mount via v2_surfaces._ROUTER_SPECS; degrades gracefully on empty hosts.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.web.momentum_view import HDB, _esc, _ro, _shell
from src.web import glossary as G

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

        @staticmethod
        def fence(kind, detail="", **k):
            return (detail + " · descriptive, not a recommendation") if detail \
                else "descriptive, not a recommendation"

try:
    from src.automation.famous_strategies import STRATEGIES
except Exception:  # pragma: no cover - keep the page alive on a slim host
    STRATEGIES = {}

try:  # the NAV line-chart primitive (reused, never rebuilt)
    from src.web.auto_portfolios_view import _svg_lines
except Exception:  # pragma: no cover
    def _svg_lines(series, w=940, h=250, pad=42):  # type: ignore
        return ""

# screen key -> the reconstructed portfolio name (classic_portfolios.CLASSIC_SPECS)
_PORTFOLIO_OF = {
    "lowvol": "LOWVOL-25", "quality": "QMJ-25", "coffeecan": "COFFEECAN-25",
    "canslim": "CANSLIM-25", "garp": "GARP-25", "magic": "MAGIC-25",
    "piotroski": "PIOTROSKI-25", "graham": "GRAHAM-25",
}
# A book needs a real WINDOW before we chart it as a track record. The archive's
# fundamentals breadth begins ~2015 (60-90 symbols before that), so the quarterly-
# earnings-dependent books (Magic/GARP/Graham/CANSLIM) start 2023-24 — NOT a record.
# Gate on YEARS, never on rebalance count: 20 rebalances is 5y on the quarterly clock
# but only 1.7y on the monthly one (CANSLIM shipped as "charted" under a count gate).
MIN_YEARS = 5.0


def _nav_rows(con, pname):
    try:
        return con.execute(
            "SELECT rebal_date, nav, bench_nav, n_churned FROM classic_portfolio_nav "
            "WHERE portfolio=? ORDER BY rebal_date", (pname,)).fetchall()
    except sqlite3.OperationalError:
        return []


def _book_stats(rows):
    """(start, end, years, cagr%, bench_cagr%, maxdd%, n) — None-safe, no numpy."""
    if not rows:
        return None
    navs = [(r["rebal_date"], r["nav"], r["bench_nav"]) for r in rows if r["nav"]]
    if len(navs) < 2:
        return None
    d0, n0, _b0 = navs[0]
    d1, n1, _b1 = navs[-1]
    try:
        yrs = (date.fromisoformat(d1) - date.fromisoformat(d0)).days / 365.25
    except (ValueError, TypeError):
        return None
    if yrs <= 0:
        return None
    cagr = ((n1 / n0) ** (1 / yrs) - 1) * 100 if n0 > 0 else None
    bn = [b for _d, _n, b in navs if b]
    bcagr = ((bn[-1] / bn[0]) ** (1 / yrs) - 1) * 100 if len(bn) >= 2 and bn[0] > 0 else None
    peak, mdd = 0.0, 0.0
    for _d, n, _b in navs:
        peak = max(peak, n)
        if peak > 0:
            mdd = min(mdd, n / peak - 1.0)
    return (d0, d1, yrs, cagr, bcagr, mdd * 100, len(navs))


def _per_year(rows):
    """[(year, book%, bench%)] — calendar-year returns off the rebalance NAV marks."""
    by_year = {}
    for r in rows:
        if r["nav"]:
            by_year.setdefault(r["rebal_date"][:4], []).append((r["nav"], r["bench_nav"]))
    out, years = [], sorted(by_year)
    for i, y in enumerate(years):
        first_n, first_b = by_year[y][0]
        last_n, last_b = by_year[y][-1]
        # chain from the previous year's close so a full year is measured
        if i > 0:
            pn, pb = by_year[years[i - 1]][-1]
            first_n, first_b = pn, pb
        rb = (last_n / first_n - 1) * 100 if first_n else None
        bb = (last_b / first_b - 1) * 100 if (first_b and last_b) else None
        out.append((y, rb, bb))
    return out


def _asof_holdings(con, pname, asof):
    """Holdings at the LAST rebalance on/before `asof` — the backdate read."""
    try:
        d = con.execute(
            "SELECT MAX(rebal_date) d FROM classic_portfolio_holdings "
            "WHERE portfolio=? AND rebal_date<=?", (pname, asof)).fetchone()
        rd = d["d"] if d else None
        if not rd:
            return None, []
        rows = con.execute(
            "SELECT symbol, rank, score, weight, px FROM classic_portfolio_holdings "
            "WHERE portfolio=? AND rebal_date=? ORDER BY rank", (pname, rd)).fetchall()
        return rd, rows
    except sqlite3.OperationalError:
        return None, []

router = APIRouter()


def _canon(key: str, fallback: str) -> str:
    """The canonical NESTED path of a lens (D80: `/dash/<workspace>/<page>`), DERIVED from the
    registry — so every in-page link matches the nav and can never drift back to a bare
    `/dash/<page>` orphan URL. Falls back to the flat route only if the registry is unavailable."""
    try:
        from src.web import lens_registry as LR
        from src.web import nested_nav as NN
        return NN.nested_path(LR.BY_KEY[key]) or fallback
    except Exception:  # pragma: no cover - registry always present in the app
        return fallback


_SELF = _canon("classics", "/dash/classics")                  # /dash/strategies/classics
_FACTOR_LEAGUE = _canon("factor-league", "/dash/factor-league")
_STRATEGY_REF = _canon("strategy-ref", "/dash/strategy-ref")

_CSS = """<style>
.cls table{border-collapse:collapse;width:100%;font-size:13px}
.cls th,.cls td{padding:6px 8px;border-bottom:1px solid var(--line-2,#333);text-align:right}
.cls th.l,.cls td.l{text-align:left}
/* NB: never name a class `bar` — the design system owns `.bar` as a 7px METER
   (height:7px;overflow:hidden), which guillotines any text placed in it. Namespaced. */
.cls .lead,.cls .cls-note{color:var(--ink-2,#999);font-size:12.5px;margin:8px 0;line-height:1.5}
.cls .pos{color:#3fb950}.cls .neg{color:#f85149}
.cls .full{color:#3fb950;font-weight:600}.cls .proxy{color:#d29922}
.cls .none{color:var(--ink-2,#999);font-style:italic}
.cls .thin{color:#d29922}
.cls .prov{border-left:2px solid var(--line-2,#333);padding-left:10px}
.cls h4{margin:14px 0 4px;font-size:14px}
.cls .card td.l small{color:var(--ink-2,#999)}
.cls .honesty{border:1px solid var(--line-2,#333);border-radius:8px;padding:10px 12px;
  font-size:12.5px;color:var(--ink-2,#aaa);margin:12px 0}
.cls a.run{white-space:nowrap}
</style>"""

_STATUS_TXT = {"full": "runs on our data", "proxy": "runs — proxy noted", "none": "reference only"}

# Guardrail #8 requires the Screener.in dependency be DISCLOSED wherever it is shown. Every
# non-price number on this page (ROCE · P/E · P/B · margins · growth) is read from
# fundamentals_history, which measured 90.9% Screener-sourced vs 9.1% NSE-XBRL (2026-07-15,
# 789,838 rows). Dated on purpose — the split shifts as the XBRL migration lands, and an
# undated "91%" would itself go stale into a untruth. Price/universe/benchmark are 100% NSE.
_PROVENANCE = (
    "<div class='cls-note prov'><b>Where these numbers come from.</b> Price, momentum, "
    "volatility, the tradeable universe and the Nifty-500 benchmark are <b>100% primary NSE</b> "
    "(bhav copy, EQUITY_L, index feed). The <b>fundamentals</b> (ROCE · P/E · P/B · margins · "
    "growth) are today read mostly from a <b>third-party archive (Screener.in)</b> — ≈91% of rows "
    "as of 2026-07 — with NSE XBRL primary filings at ≈9% and growing as the migration lands. "
    "Point-in-time dates come from real BSE/NSE filings where captured, else a conservative "
    "calibrated lag. We say this plainly because the source matters as much as the number.</div>")

# Per-strategy roster columns: (detail_key, header, kind, gloss_term) — kind ∈ pct|num|x1|bool
# gloss_term matches a docs/metrics-glossary.md key ("" = no popover; degrades to plain label).
_COLS = {
    "lowvol":    [("vol", "Vol 66d", "pct", "Volatility"), ("mom12", "12m", "pct", ""),
                  ("range52", "52w pos", "pct", "pct_from_52w_high")],
    "quality":   [("roce_avg", "ROCE 3y", "num", "ROCE"), ("opm", "OPM", "num", "OPM"),
                  ("de", "D/E", "x1", "D/E")],
    "coffeecan": [("roce", "ROCE", "num", "ROCE"), ("roce_avg", "ROCE 3y", "num", "ROCE"),
                  ("sales_g5y", "Sales 5y", "num", "Sales growth"), ("rising", "Rising", "bool", "")],
    "canslim":   [("pg_ttm", "Profit TTM", "num", "Profit growth"), ("pg_3y", "Profit 3y", "num", "Profit growth"),
                  ("range52", "52w pos", "pct", "pct_from_52w_high"), ("fii_up", "FII↑", "bool", "")],
    "garp":      [("peg", "PEG", "x1", "PEG"), ("pe", "P/E", "x1", "P/E"),
                  ("pg_3y", "Growth 3y", "num", "Profit growth"), ("roce", "ROCE", "num", "ROCE")],
    "magic":     [("roce", "ROC (ROCE)", "num", "ROCE"), ("ey", "Earn yield", "num", "Earnings yield"),
                  ("pe", "P/E", "x1", "P/E")],
    "piotroski": [("f5", "F-Score /5", "x1", "F-Score"), ("roce", "ROCE", "num", "ROCE"),
                  ("pg_ttm", "Profit TTM", "num", "Profit growth")],
    "graham":    [("pe", "P/E", "x1", "P/E"), ("pb", "P/B", "x1", "P/B")],
}

# The proxy / caution note shown on each card (single-sourced honesty).
_NOTE = {
    "magic": "Greenblatt ranks EBIT/EV yield; we substitute earnings yield (E/P) — no PIT "
             "enterprise value yet. ROC uses ROCE.",
    "piotroski": "5 of Piotroski's 9 signals (ΔNI, ROCE>0, ΔROCE, Δmargin, leverage-safe). The "
                 "cash-flow trio (CFO>0, CFO>NI, Δcurrent-ratio) needs the XBRL cash-flow feed — phase 2.",
    "graham": "Deep value is the family our own 14-year test HARD-REJECTED — book-yield alpha was "
              "NEGATIVE (−2%), beta 1.54, MaxDD −82%. This roster is shown as a caution, not a buy list. "
              "Current-ratio leg not yet computable.",
    "acquirers": "Not runnable yet: EV/EBIT needs point-in-time enterprise value (cash + share count) "
                 "we do not hold. Closing that XBRL gap is phase 2.",
}


def _fmt(kind, v):
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(str(v))
    if kind == "pct":
        cls = "pos" if f >= 0 else "neg"
        return f"<span class='{cls}'>{f * 100:+.0f}%</span>"
    if kind == "num":
        return f"{f:.1f}"
    if kind == "x1":
        return f"{f:.2f}"
    if kind == "bool":
        return "✓" if v else "·"
    return _esc(str(v))


def _roster_rows(con, strat):
    try:
        return con.execute(
            "SELECT symbol, rank, score, detail_json FROM classic_roster "
            "WHERE strategy=? ORDER BY rank", (strat,)).fetchall()
    except sqlite3.OperationalError:
        return []


def _roster_html(strat, rows):
    name = STRATEGIES.get(strat, (strat,))[0]
    cols = _COLS.get(strat, [])
    head = "".join(f"<th>{G.gloss(gt, h) if gt else _esc(h)}</th>" for _k, h, _t, gt in cols)
    body = ""
    for r in rows:
        det = {}
        try:
            det = json.loads(r["detail_json"]) if r["detail_json"] else {}
        except (ValueError, TypeError):
            det = {}
        cells = "".join(f"<td>{_fmt(t, det.get(k))}</td>" for k, _h, t, _gt in cols)
        body += ("<tr>"
                 f"<td>{r['rank']}</td>"
                 f"<td class='l'><a href='/dash/stock?sym={_esc(r['symbol'])}'>"
                 f"{_esc(r['symbol'])}</a></td>"
                 f"{cells}</tr>")
    note = _NOTE.get(strat, "")
    note_html = f"<div class='cls-note'>{_esc(note)}</div>" if note else ""
    return (
        f"<h3>{_esc(name)} — current top-{len(rows)} roster</h3>"
        + note_html
        + "<div class='cls-note'>A research shortlist that re-ranks every night — "
        + ifx.fence("not_reco", cap=True)
        + f". <a href='{_SELF}?s={_esc(strat)}&amp;fmt=csv'>Download CSV</a></div>"
        + "<table><thead><tr><th>#</th><th class='l'>Symbol</th>"
        + head + "</tr></thead><tbody>" + body + "</tbody></table>")


@router.get("/dash/classics", response_class=HTMLResponse)
def classics_page(s: str = "", fmt: str = "", asof: str = ""):
    strat = s.strip().lower()
    if strat not in STRATEGIES or STRATEGIES.get(strat, ("", "", "", "none"))[3] == "none":
        strat = ""
    asof = asof.strip()[:10]

    con = _ro(HDB)
    roster, as_of = [], ""
    books, nav_rows, asof_date, asof_rows = {}, [], None, []
    if con is not None:
        con.row_factory = sqlite3.Row
        try:
            r = con.execute("SELECT MAX(as_of) d FROM classic_roster").fetchone()
            as_of = (r["d"] if r else "") or ""
        except sqlite3.OperationalError:
            as_of = ""
        for _k, _p in _PORTFOLIO_OF.items():          # the cross-book comparison
            books[_k] = _book_stats(_nav_rows(con, _p))
        if strat:
            roster = _roster_rows(con, strat)
            pname = _PORTFOLIO_OF.get(strat)
            if pname:
                nav_rows = _nav_rows(con, pname)
                if asof:
                    asof_date, asof_rows = _asof_holdings(con, pname, asof)
        con.close()

    if fmt == "csv" and strat:
        cols = _COLS.get(strat, [])
        header = ["rank", "symbol"] + [k for k, _h, _t, _gt in cols]
        lines = [",".join(header)]
        for r in roster:
            try:
                det = json.loads(r["detail_json"]) if r["detail_json"] else {}
            except (ValueError, TypeError):
                det = {}
            vals = [str(r["rank"]), r["symbol"]] + [str(det.get(k, "")) for k, _h, _t, _gt in cols]
            lines.append(",".join(vals))
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    # the catalog == the cross-book comparison ("which was outstanding, and when")
    cat = ""
    for key, (name, author, rule, comp) in STRATEGIES.items():
        link = (f"<a class='run' href='{_SELF}?s={key}'>portfolio →</a>"
                if comp != "none" else "<span class='none'>phase 2</span>")
        st = books.get(key)
        if not st:
            perf = ("<td class='l none' colspan='4'>no reconstruction yet</td>"
                    if comp != "none" else
                    "<td class='l none' colspan='4'>not runnable — needs PIT enterprise value</td>")
        else:
            d0, _d1, yrs, cagr, bcagr, mdd, n = st
            thin = (yrs or 0) < MIN_YEARS
            excess = (cagr - bcagr) if (cagr is not None and bcagr is not None) else None
            if thin:
                perf = (f"<td class='l'>{_esc(d0)}</td>"
                        f"<td class='l thin' colspan='3'>insufficient history "
                        f"({yrs:.1f}y, {n} rebalances) — not a track record</td>")
            else:
                perf = (f"<td class='l'>{_esc(d0)} <small>({yrs:.0f}y)</small></td>"
                        f"<td>{f'{cagr:.1f}%' if cagr is not None else '—'}</td>"
                        f"<td class='{'pos' if (excess or 0) >= 0 else 'neg'}'>"
                        f"{f'{excess:+.1f}%' if excess is not None else '—'}</td>"
                        f"<td class='neg'>{f'{mdd:.0f}%' if mdd is not None else '—'}</td>")
        cat += ("<tr class='card'>"
                f"<td class='l'><b>{_esc(name)}</b><br><small>{_esc(author)}</small></td>"
                f"<td class='l'>{_esc(rule)}</td>"
                f"{perf}"
                f"<td class='l'>{link}</td></tr>")

    # ── the PORTFOLIO layer: named book, NAV chart, per-year, backdating ──────
    pf_html = ""
    if strat:
        title = STRATEGIES.get(strat, (strat,))[0]
        pname = _PORTFOLIO_OF.get(strat, "")
        st = books.get(strat)
        n = st[6] if st else 0
        if st and (st[2] or 0) >= MIN_YEARS:
            d0, d1, yrs, cagr, bcagr, mdd, _n = st
            excess = (cagr - bcagr) if (cagr is not None and bcagr is not None) else None
            chart = _svg_lines([
                (pname, "#58a6ff",
                 [(r["rebal_date"], r["nav"]) for r in nav_rows if r["nav"]]),
                ("Nifty 500", "#8b949e",
                 [(r["rebal_date"], r["bench_nav"]) for r in nav_rows if r["bench_nav"]]),
            ])
            py = "".join(
                f"<tr><td class='l'>{_esc(y)}</td>"
                f"<td class='{'pos' if (bk or 0) >= 0 else 'neg'}'>"
                f"{f'{bk:+.1f}%' if bk is not None else '—'}</td>"
                f"<td>{f'{bn:+.1f}%' if bn is not None else '—'}</td>"
                f"<td class='{'pos' if ((bk or 0) - (bn or 0)) >= 0 else 'neg'}'>"
                f"{f'{bk - bn:+.1f}%' if (bk is not None and bn is not None) else '—'}</td></tr>"
                for y, bk, bn in _per_year(nav_rows))
            back = ""
            if asof_date:
                hrows = "".join(
                    f"<tr><td>{h['rank']}</td><td class='l'>"
                    f"<a href='/dash/stock?sym={_esc(h['symbol'])}'>{_esc(h['symbol'])}</a></td>"
                    f"<td>{(h['weight'] or 0) * 100:.1f}%</td>"
                    f"<td>{h['px'] if h['px'] else '—'}</td></tr>" for h in asof_rows)
                back = (f"<h4>Holdings as of {_esc(asof)} "
                        f"<small>(last rebalance {_esc(asof_date)})</small></h4>"
                        "<table><thead><tr><th>#</th><th class='l'>Symbol</th>"
                        "<th>Weight</th><th>Px at rebal</th></tr></thead><tbody>"
                        + hrows + "</tbody></table>")
            elif asof:
                back = (f"<div class='cls-note thin'>No rebalance on/before {_esc(asof)} — this book "
                        f"starts {_esc(d0)}.</div>")
            pf_html = (
                f"<h3>{_esc(title)} — model portfolio <small>({_esc(pname)})</small></h3>"
                + f"<div class='cls-note'>Reconstructed <b>{_esc(d0)} → {_esc(d1)}</b> "
                f"({yrs:.1f}y · {n} rebalances) · CAGR <b>{cagr:.1f}%</b> vs Nifty 500 "
                f"{bcagr:.1f}% (<b>{excess:+.1f}%</b>) · MaxDD {mdd:.0f}% · equal-weight 1/25, "
                "band-35 churn, flat cost — a reconstructed backtest, not a record of money.</div>"
                + chart
                + ifx.plain("The blue line is the strategy's ₹1 grown on our data; grey is Nifty 500 "
                            "over the same window. Below, calendar-year returns — that is where you "
                            "see <i>which</i> year a book earned or lost its reputation.")
                + "<h4>Year by year</h4>"
                + "<table><thead><tr><th class='l'>Year</th><th>Book</th><th>Nifty 500</th>"
                "<th>Excess</th></tr></thead><tbody>" + py + "</tbody></table>"
                + "<form method='get' class='cls-note' style='margin-top:10px'>"
                f"<input type='hidden' name='s' value='{_esc(strat)}'>"
                "Backdate — show holdings as of "
                f"<input type='date' name='asof' value='{_esc(asof)}' "
                f"min='{_esc(d0)}' max='{_esc(d1)}' style='margin:0 6px'>"
                "<button type='submit'>Go</button></form>"
                + back)
        elif st:
            d0, d1, yrs, _c, _b, _m, _n = st
            pf_html = (
                f"<h3>{_esc(title)} — model portfolio <small>({_esc(pname)})</small></h3>"
                + f"<div class='cls-note thin'><b>Insufficient history — not a track record.</b> "
                f"This book only reconstructs from <b>{_esc(d0)}</b> ({yrs:.1f}y, {n} rebalances). "
                "Our fundamentals archive's breadth begins ~2015 (60–90 symbols before that), and "
                "this rule additionally needs quarterly earnings depth — so there is no honest "
                "chart to draw yet. Deliberately not plotted.</div>")
        else:
            pf_html = (f"<div class='cls-note'>No reconstruction stored for <b>{_esc(strat)}</b> — "
                       "run <code>classic_portfolios --backfill</code> on the box.</div>")

    roster_html = _roster_html(strat, roster) if (strat and roster) else (
        f"<div class='cls-note'>No roster stored for <b>{_esc(strat)}</b> yet — the nightly "
        "<code>famous_strategies</code> refresh populates it on the live box.</div>"
        if strat else "")

    body = (
        "<div class='cls'>" + _CSS + ifx.readability_css() + G.css()
        + "<h2>Classic screens — the famous strategies, run on our data</h2>"
        + ifx.bottom_line(
            "The name-brand equity strategies — <b>Magic Formula, CANSLIM, Piotroski, Coffee Can, "
            "GARP, Graham, Quality, Low-Vol</b> — each expressed as a faithful screen over the NSE "
            "universe with a live top-25 roster. We label every proxy (where our point-in-time data "
            "can't yet match the textbook rule exactly) and show the value strategies next to what "
            "they ACTUALLY delivered here. " + ifx.fence("not_reco", cap=True) + ".")
        + ifx.how_to_read_link()
        + f"<div class='rd-htr'><a href='{_FACTOR_LEAGUE}'>Factor league (the raw families) →</a>"
        + f" · <a href='{_STRATEGY_REF}?p=classic-screens'>Methodology &amp; honesty →</a></div>"
        + f"<div class='cls-note'>rosters as-of <b>{_esc(as_of) or '—'}</b> · universe = liquid NSE "
        "names (turnover ≥ ₹5cr) · every metric is point-in-time (no look-ahead)</div>"
        + _PROVENANCE
        + "<table><thead><tr><th class='l'>Strategy</th><th class='l'>How we run it</th>"
        "<th class='l' title='first rebalance the data supports'>Since</th><th>CAGR</th>"
        "<th title='CAGR minus Nifty 500 over the same window'>vs Nifty 500</th>"
        "<th>MaxDD</th><th class='l'></th></tr></thead><tbody>" + cat + "</tbody></table>"
        + pf_html
        + roster_html
        + "<div class='honesty'><b>How to read this menu.</b> These are public, citable rules — we "
        "run our closest faithful expression of each against the data we actually hold, and we do "
        "not soften the result. Where the textbook needs data we lack point-in-time (enterprise "
        "value, cash-flow statement, current ratio), the card says so and the rule is proxied or "
        "held for phase 2. The value strategies (Graham, the Magic Formula value leg) are shown "
        "with our own recorded numbers — on 14 years of NSE data <b>deep value's alpha was "
        "negative</b> — so a low-multiple roster reads as context, never as a signal. "
        + ifx.fence("not_reco", cap=True) + ".</div></div>")
    return HTMLResponse(_shell("Classic screens", body, active="classics", wide=True))
