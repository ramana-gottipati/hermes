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
.cls .card td.l small{color:var(--ink-2,#999)}
.cls .honesty{border:1px solid var(--line-2,#333);border-radius:8px;padding:10px 12px;
  font-size:12.5px;color:var(--ink-2,#aaa);margin:12px 0}
.cls a.run{white-space:nowrap}
</style>"""

_STATUS_TXT = {"full": "runs on our data", "proxy": "runs — proxy noted", "none": "reference only"}

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
def classics_page(s: str = "", fmt: str = ""):
    strat = s.strip().lower()
    if strat not in STRATEGIES or STRATEGIES.get(strat, ("", "", "", "none"))[3] == "none":
        strat = ""

    con = _ro(HDB)
    roster, as_of = [], ""
    if con is not None:
        con.row_factory = sqlite3.Row
        try:
            r = con.execute("SELECT MAX(as_of) d FROM classic_roster").fetchone()
            as_of = (r["d"] if r else "") or ""
        except sqlite3.OperationalError:
            as_of = ""
        if strat:
            roster = _roster_rows(con, strat)
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

    # the catalog
    cat = ""
    for key, (name, author, rule, comp) in STRATEGIES.items():
        link = (f"<a class='run' href='{_SELF}?s={key}'>roster →</a>"
                if comp != "none" else "<span class='none'>phase 2</span>")
        cat += ("<tr class='card'>"
                f"<td class='l'><b>{_esc(name)}</b><br><small>{_esc(author)}</small></td>"
                f"<td class='l'>{_esc(rule)}</td>"
                f"<td class='l {comp}'>{_STATUS_TXT[comp]}</td>"
                f"<td class='l'>{link}</td></tr>")

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
        + "<table><thead><tr><th class='l'>Strategy</th><th class='l'>How we run it</th>"
        "<th class='l'>Status</th><th class='l'></th></tr></thead><tbody>" + cat + "</tbody></table>"
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
