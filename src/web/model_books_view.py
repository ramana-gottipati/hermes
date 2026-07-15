"""/dash/tracker/model-books — every model portfolio, displayed in the Tracker, adoptable.

Ramana's ask (S146): "once you select the model, I can access the strategies and view the
model portfolios, allowing me to choose it… can you display it under the tracker?"

THE DESIGN (agreed with Ramana, and the reason this is a DISPLAY + a bridge, not a copy):
  * the ENGINE OWNS the books — `auto_portfolios` (the 4 ADMITTED: superior measured Sharpe AND
    beats the Nifty hurdle) and `classic_portfolios` (the famous public rules, most of which do
    NOT clear that bar). Both are reconstructed, no-manual-edit by construction — his lock.
  * the TRACKER DISPLAYS them read-only beside his own books, so "my book vs the models" is one
    screen. Display-only keeps the engine lock intact.
  * ADOPT is the bridge: it seeds a NAMED BOOK in `stocks_in_play` from the model's CURRENT
    holdings using **today** as the entry date and today's close as the entry price. Never the
    backtest's history — writing a reconstruction into his real book would make his XIRR fiction.
    So the model's NAV stays the engine's record, and his XIRR measures HIS adoption. Honest both
    sides of the line.

WHY ADOPT IS OFFERED EVEN FOR SHORT-HISTORY BOOKS: our fundamentals archive cliffs at ~2015, so
Magic Formula / CANSLIM / Graham / GARP have only 2-3y of reconstruction — NOT a track record, and
never charted as one. But starting them forward from today is exactly how a real record gets built
(the CCI lesson: build the series FORWARD). The history label and the adopt action are independent.

Descriptive-only: a reconstructed backtest is not advice and not a promise. Writes are POST.
Isolated router; durable mount via v2_surfaces._ROUTER_SPECS; degrades on empty hosts.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

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

        @staticmethod
        def plain(t):
            return f"<div>{t}</div>"

        @staticmethod
        def fence(kind, detail="", **k):
            return "descriptive, not a recommendation"

router = APIRouter()

MIN_YEARS = 5.0        # same honesty bar as the classics page: YEARS, never rebalance count


def _canon(key: str, fallback: str) -> str:
    """Canonical NESTED path from the registry (D80) — links can never drift from the nav."""
    try:
        from src.web import lens_registry as LR
        from src.web import nested_nav as NN
        return NN.nested_path(LR.BY_KEY[key]) or fallback
    except Exception:  # pragma: no cover
        return fallback


_SELF = _canon("model-books", "/dash/tracker/model-books")
_CLASSICS = _canon("classics", "/dash/classics")
_MODELS = _canon("model-portfolios", "/dash/model-portfolios")
_PORTFOLIOS = _canon("portfolios", "/dash/tracker/portfolios")

# (estate label, nav table, holdings table, what it means)
_ESTATES = [
    ("Engine-admitted books", "auto_portfolio_nav", "auto_portfolio_holdings",
     "Admitted on evidence: superior measured Sharpe AND beats the Nifty-500 hurdle."),
    ("Classic public strategies", "classic_portfolio_nav", "classic_portfolio_holdings",
     "The famous public rules on the same engine. Most do NOT clear the admission bar — "
     "that is the finding, not a defect."),
]

_CSS = """<style>
.mb table{border-collapse:collapse;width:100%;font-size:13px}
.mb th,.mb td{padding:6px 8px;border-bottom:1px solid var(--line-2,#333);text-align:right}
.mb th.l,.mb td.l{text-align:left}
.mb .mb-note{color:var(--ink-2,#999);font-size:12.5px;margin:8px 0;line-height:1.5}
.mb .pos{color:#3fb950}.mb .neg{color:#f85149}.mb .thin{color:#d29922}
.mb h3{margin:18px 0 4px;font-size:15px}
.mb .honesty{border:1px solid var(--line-2,#333);border-radius:8px;padding:10px 12px;
  font-size:12.5px;color:var(--ink-2,#aaa);margin:12px 0}
.mb .adopt input[type=text]{width:150px}
.mb .adopt{display:inline}
</style>"""


def _stats(rows):
    """(start, end, years, cagr%, bench_cagr%, maxdd%, n) — shared with the classics page."""
    navs = [(r["rebal_date"], r["nav"], r["bench_nav"]) for r in rows if r["nav"]]
    if len(navs) < 2:
        return None
    d0, n0, _ = navs[0]
    d1, n1, _ = navs[-1]
    try:
        yrs = (date.fromisoformat(d1) - date.fromisoformat(d0)).days / 365.25
    except (ValueError, TypeError):
        return None
    if yrs <= 0 or not n0:
        return None
    cagr = ((n1 / n0) ** (1 / yrs) - 1) * 100
    bn = [b for _d, _n, b in navs if b]
    bcagr = ((bn[-1] / bn[0]) ** (1 / yrs) - 1) * 100 if len(bn) >= 2 and bn[0] else None
    peak = mdd = 0.0
    for _d, n, _b in navs:
        peak = max(peak, n)
        if peak:
            mdd = min(mdd, n / peak - 1.0)
    return (d0, d1, yrs, cagr, bcagr, mdd * 100, len(navs))


def _books(con, nav_tbl):
    try:
        names = [r[0] for r in con.execute(
            f"SELECT DISTINCT portfolio FROM {nav_tbl} ORDER BY portfolio")]
    except sqlite3.OperationalError:
        return []
    out = []
    for p in names:
        rows = con.execute(
            f"SELECT rebal_date, nav, bench_nav FROM {nav_tbl} WHERE portfolio=? "
            "ORDER BY rebal_date", (p,)).fetchall()
        out.append((p, _stats(rows)))
    return out


def _latest_holdings(con, hold_tbl, pname):
    try:
        d = con.execute(f"SELECT MAX(rebal_date) d FROM {hold_tbl} WHERE portfolio=?",
                        (pname,)).fetchone()
        rd = d["d"] if d else None
        if not rd:
            return None, []
        rows = con.execute(
            f"SELECT symbol, rank, weight FROM {hold_tbl} WHERE portfolio=? AND rebal_date=? "
            "ORDER BY rank", (pname, rd)).fetchall()
        return rd, rows
    except sqlite3.OperationalError:
        return None, []


def _row(pname, st, hold_tbl):
    default_book = pname.replace("-25", "").title().replace("_", " ")
    if not st:
        cells = "<td class='l thin' colspan='4'>no reconstruction yet</td>"
    else:
        d0, _d1, yrs, cagr, bcagr, mdd, n = st
        thin = yrs < MIN_YEARS
        exc = (cagr - bcagr) if (cagr is not None and bcagr is not None) else None
        if thin:
            cells = (f"<td class='l'>{_esc(d0)}</td>"
                     f"<td class='l thin' colspan='3'>only {yrs:.1f}y ({n} rebalances) — "
                     "not a track record</td>")
        else:
            cells = (f"<td class='l'>{_esc(d0)} <small>({yrs:.0f}y)</small></td>"
                     f"<td>{cagr:.1f}%</td>"
                     f"<td class='{'pos' if (exc or 0) >= 0 else 'neg'}'>"
                     f"{f'{exc:+.1f}%' if exc is not None else '—'}</td>"
                     f"<td class='neg'>{mdd:.0f}%</td>")
    adopt = (
        f"<form class='adopt' method='post' action='{_SELF}/adopt'>"
        f"<input type='hidden' name='portfolio' value='{_esc(pname)}'>"
        f"<input type='hidden' name='table' value='{_esc(hold_tbl)}'>"
        f"<input type='text' name='book' value='{_esc(default_book)}' aria-label='book name'>"
        "<button type='submit'>Adopt →</button></form>")
    return f"<tr><td class='l'><b>{_esc(pname)}</b></td>{cells}<td class='l'>{adopt}</td></tr>"


@router.get("/dash/tracker/model-books", response_class=HTMLResponse)
def model_books_page(msg: str = "", err: str = ""):
    con = _ro(HDB)
    sections = ""
    if con is not None:
        con.row_factory = sqlite3.Row
        for label, nav_tbl, hold_tbl, blurb in _ESTATES:
            books = _books(con, nav_tbl)
            if not books:
                sections += (f"<h3>{_esc(label)}</h3>"
                             f"<div class='mb-note thin'>Not reconstructed on this host yet.</div>")
                continue
            rows = "".join(_row(p, st, hold_tbl) for p, st in books)
            sections += (
                f"<h3>{_esc(label)}</h3><div class='mb-note'>{_esc(blurb)}</div>"
                "<table><thead><tr><th class='l'>Book</th><th class='l'>Since</th><th>CAGR</th>"
                "<th>vs Nifty 500</th><th>MaxDD</th><th class='l'>Track it</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
        con.close()
    banner = ""
    if msg:
        banner = f"<div class='mb-note pos'>{_esc(msg)}</div>"
    elif err:
        banner = f"<div class='mb-note neg'>{_esc(err)}</div>"

    body = (
        "<div class='mb'>" + _CSS + ifx.readability_css()
        + "<h2>Model books — every engine portfolio, and how to track one</h2>"
        + ifx.bottom_line(
            "Every portfolio the engine manages, in one place: the <b>admitted</b> books (which "
            "earned their place on measured evidence) and the <b>classic public strategies</b> "
            "(most of which did not). Compare them, then <b>Adopt</b> one — that copies today's "
            "holdings into a named book of your own with <b>today</b> as the entry date, so your "
            "tracked return measures <i>your</i> money, never the backtest. "
            + ifx.fence("not_reco", cap=True) + ".")
        + ifx.how_to_read_link()
        + f"<div class='rd-htr'><a href='{_MODELS}'>Model portfolios (charts) →</a>"
        + f" · <a href='{_CLASSICS}'>Classic screens →</a>"
        + f" · <a href='{_PORTFOLIOS}'>My books →</a></div>"
        + banner
        + sections
        + ifx.plain("A model's NAV is a reconstruction the engine computed. The moment you adopt "
                    "it, a separate, honest clock starts on your side — entry today, at today's "
                    "close. The two are never mixed.")
        + "<div class='honesty'><b>Why some books show no chart.</b> A book is only shown as a "
        "track record once it has <b>5+ years</b>. Our fundamentals archive's breadth begins "
        "~2015, so the strategies needing quarterly earnings depth (Magic Formula, CANSLIM, "
        "Graham, GARP) reconstruct only from 2023-24 — and their excess returns look the "
        "<i>best</i> precisely because 2-3 years of one favourable window flatters them. They are "
        "still adoptable: starting the clock forward is how a real record gets built. "
        + ifx.fence("not_reco", cap=True) + ".</div></div>")
    return HTMLResponse(_shell("Model books", body, active="model-books", wide=True))


@router.post("/dash/tracker/model-books/adopt")
def adopt(portfolio: str = Form(...), table: str = Form(...), book: str = Form("")):
    """Seed a NAMED book in stocks_in_play from a model's CURRENT holdings, entry = today.

    Never writes the reconstruction's history: the backtest is the engine's record, this is the
    start of the user's own. Idempotent-ish: refuses if the book already holds open positions.
    """
    if table not in ("auto_portfolio_holdings", "classic_portfolio_holdings"):
        return RedirectResponse(f"{_SELF}?err=unknown+book+source", status_code=303)
    pname = portfolio.strip()
    bname = (book.strip() or pname)[:60]
    try:
        from src.core.db import get_conn
    except Exception:  # pragma: no cover
        return RedirectResponse(f"{_SELF}?err=database+unavailable", status_code=303)
    try:
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rd, rows = _latest_holdings(conn, table, pname)
            if not rows:
                return RedirectResponse(f"{_SELF}?err=no+holdings+for+{_esc(pname)}",
                                        status_code=303)
            existing = conn.execute(
                "SELECT COUNT(*) c FROM stocks_in_play WHERE book=? AND status='open'",
                (bname,)).fetchone()["c"]
            if existing:
                return RedirectResponse(
                    f"{_SELF}?err=book+'{bname}'+already+has+{existing}+open+positions",
                    status_code=303)
            td = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()["d"]
            px = {}
            if td:
                px = {r["symbol"]: r["close"] for r in conn.execute(
                    "SELECT symbol, close FROM bhavcopy_rows WHERE trade_date=? AND series='EQ'",
                    (td,))}
            today = date.today().isoformat()
            thesis = (f"Adopted from model portfolio {pname} (engine rebalance {rd}). "
                      "Entry is TODAY — the model's reconstructed history is NOT this book's.")
            conn.executemany(
                "INSERT INTO stocks_in_play (symbol, strategy, book, status, date_added, "
                "entry_price, entry_thesis) VALUES (?,?,?,?,?,?,?)",
                [(r["symbol"], pname, bname, "open", today, px.get(r["symbol"]), thesis)
                 for r in rows])
            conn.commit()
            n = len(rows)
    except Exception as e:  # noqa: BLE001 - never 500 the tracker
        return RedirectResponse(f"{_SELF}?err=adopt+failed:+{type(e).__name__}", status_code=303)
    return RedirectResponse(
        f"{_SELF}?msg=Adopted+{n}+holdings+from+{pname}+into+your+book+'{bname}'+"
        f"(entry+today).+See+My+books.", status_code=303)
