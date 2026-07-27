"""src/web/home/tracker_pages.py — the Graphite Tracker (lane W3-B, milestone M7).

The six classic Tracker surfaces (`dashboard` · `portfolios` · `model-books` · `watchlists` ·
`performance` · `import`) rebuilt in the Graphite idiom as five declared children of the Graphite
home, plus one merged view:

    /dash/home/tracker              Overview   — the cockpit  (classic `dashboard`)
                                               + the "follow a model book" view (classic `model-books`)
    /dash/home/tracker/portfolios   Positions  (classic `portfolios`)
    /dash/home/tracker/watchlists   Watchlist  (classic `watchlists`)
    /dash/home/tracker/performance  Scoreboard (classic `performance`)
    /dash/home/tracker/import       Import     (classic `import`)

Four decisions worth reading before editing this file:

1. **One watch write path.** The Graphite home already owns `POST /dash/home/watch/add` (canonical
   `stocks_in_play` watch tier, native `date_added`, symbol validated against `bhavcopy_rows`). The
   Watchlist page RE-USES that exact endpoint and its form component — it does not add a second one.
   The importer is the only new write in this lane, and it applies the same validation discipline.

2. **The demo book travels.** `tracker_gate.py` made the Tracker a private workspace on a public
   site: anonymous visitors see a clearly-labelled synthetic book, the owner unlocks with the shared
   secret. That gate is HTTP middleware for `/dash/tracker*`; these routes live under `/dash/home/*`
   so the middleware never sees them — so the page asks the gate directly
   (`tracker_gate._is_owner`). The auth is REUSED, never forked, and it fails CLOSED (any error ⇒
   the demo book, never someone's real positions).

3. **Kite-norm labels.** Part III §J: the tracker column set aligns with the vocabulary Indian users
   already read on their broker — `Avg. cost · LTP · Cur. val · P&L · Day chg.` The identity spine
   (Symbol · Sector · LTP · Entry date) is frozen and never configurable; the deeper columns are the
   Pro layer, and evidence is never paywalled — the numbers a decision rests on are all in Free.

4. **No number we cannot back.** XIRR renders only when `tracker_reads.cashflow_fidelity()` passes
   on the live data; otherwise the page prints the measured verdict and what is missing. The
   headline return metric is a chained TIME-weighted series, which needs marks rather than a
   cash-flow ledger.

Isolation: no import of `dashboard` / `shell_skin` / `left_rail` / any preview module
(`tests/test_home_isolation.py`). Own `APIRouter`, mounted by ONE anchored `v2_surfaces._ROUTER_SPECS`
entry; the five GET pages are registered in `tests/test_dash_route_registry.INTERNAL_DEV` as
declared children — no `lens_registry` entry until cutover.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from src.web.home import components as C
from src.web.home import shell
from src.web.home import tracker_reads as TR

router = APIRouter()

_BASE = "/dash/home/tracker"
_VIEWS = (("", "Overview"), ("/portfolios", "Positions"), ("/watchlists", "Watchlist"),
          ("/performance", "Scoreboard"), ("/import", "Import"))

_CSS = """<style>/* g-tracker (lane w3-tracker) */
:root[data-ui-g] .gt-nav{display:flex;gap:2px;flex-wrap:wrap;background:var(--bg-2);border:1px solid var(--line-2);
  border-radius:var(--r-pill);padding:3px;margin:0 0 14px;width:max-content;max-width:100%}
:root[data-ui-g] .gt-nav a{font:700 11.5px var(--font);color:var(--ink-3);padding:6px 13px;
  border-radius:var(--r-pill);text-decoration:none;white-space:nowrap}
:root[data-ui-g] .gt-nav a[aria-current="page"]{color:var(--on-accent);
  background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .gt-nav a:hover{color:var(--ink)}
:root[data-ui-g] .gt-demo{border:1px solid var(--warn,#c9922a);background:color-mix(in srgb,var(--warn,#c9922a) 12%,transparent);
  border-radius:12px;padding:10px 14px;font-size:12.5px;line-height:1.6;margin:0 0 14px;color:var(--ink)}
:root[data-ui-g] .gt-demo b{color:var(--ink)}
:root[data-ui-g] .gt-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:9px}
:root[data-ui-g] .gt-box{max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:11px;
  scrollbar-width:thin}
:root[data-ui-g] .gt-box.tall{max-height:440px}
:root[data-ui-g] table.gt{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] table.gt th{position:sticky;top:0;z-index:2;background:var(--bg-2);text-align:left;
  font:700 10px var(--font);letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);
  padding:7px 9px;border-bottom:1px solid var(--line-2);white-space:nowrap}
:root[data-ui-g] table.gt td{padding:6px 9px;border-bottom:1px solid var(--line);white-space:nowrap}
:root[data-ui-g] table.gt td.r,:root[data-ui-g] table.gt th.r{text-align:right;font-variant-numeric:tabular-nums}
:root[data-ui-g] table.gt tbody tr:hover{background:var(--bg-2)}
:root[data-ui-g] table.gt td.spine,:root[data-ui-g] table.gt th.spine{position:sticky;left:0;z-index:1;
  background:var(--bg-1)}
:root[data-ui-g] table.gt th.spine{z-index:3;background:var(--bg-2)}
:root[data-ui-g] .gt-flag{display:inline-block;font-size:11px;color:var(--ink-2);
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:1px 8px;margin:1px 3px 1px 0}
:root[data-ui-g] .gt-bar{display:flex;align-items:center;gap:9px;margin:5px 0;font-size:12px}
:root[data-ui-g] .gt-bar .lb{width:150px;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
:root[data-ui-g] .gt-bar .tr{flex:1;height:9px;border-radius:5px;background:var(--bg-3);overflow:hidden}
:root[data-ui-g] .gt-bar .tr i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .gt-bar .vl{width:66px;text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
:root[data-ui-g] .gt-chips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}
:root[data-ui-g] .gt-chips a{font:600 11.5px var(--font);text-decoration:none;color:var(--ink-2);
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:4px 11px}
:root[data-ui-g] .gt-chips a[aria-current="true"]{color:var(--on-accent);border-color:transparent;
  background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .gt-act{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0 0}
:root[data-ui-g] .gt-form label{display:block;font:600 10.5px var(--font);letter-spacing:.06em;
  text-transform:uppercase;color:var(--ink-3);margin:10px 0 4px}
:root[data-ui-g] .gt-form input[type=text],:root[data-ui-g] .gt-form select,
:root[data-ui-g] .gt-form textarea,:root[data-ui-g] .gt-form input[type=file]{
  width:100%;box-sizing:border-box;background:var(--bg-2);color:var(--ink);border:1px solid var(--line-2);
  border-radius:9px;padding:8px 11px;font:400 13px var(--font)}
:root[data-ui-g] .gt-form textarea{min-height:132px;font-family:var(--mono);font-size:12px;resize:vertical}
:root[data-ui-g] .gt-2col{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
:root[data-ui-g] .gt-verdict{border:1px solid var(--line-2);border-radius:12px;padding:13px 15px;margin:4px 0 0}
:root[data-ui-g] .gt-verdict.fail{border-color:var(--warn,#c9922a)}
:root[data-ui-g] .gt-verdict h4{margin:0 0 6px;font:700 13px var(--font);color:var(--ink)}
:root[data-ui-g] .gt-verdict ul{margin:7px 0 0;padding-left:19px;font-size:12.5px;line-height:1.65;color:var(--ink-2)}
:root[data-ui-g] .gt-state{font:700 9.5px var(--mono);letter-spacing:.1em;padding:2px 7px;border-radius:var(--r-pill)}
:root[data-ui-g] .gt-state.ok{background:color-mix(in srgb,var(--up) 18%,transparent);color:var(--up)}
:root[data-ui-g] .gt-state.bad{background:color-mix(in srgb,var(--dn) 18%,transparent);color:var(--dn)}
:root[data-ui-g] .gt-state.skip{background:var(--bg-3);color:var(--ink-3)}
:root[data-ui-g] .gt-curve{width:100%;height:190px;display:block}
</style>"""


# ── tiny render helpers (all values escaped / formatted server-side) ──────────────
def _rs(v, dp: int = 0) -> str:
    """A rupee amount in the Indian reading: ₹1.2Cr / ₹4.5L / ₹9,300."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    a = abs(f)
    sign = "−" if f < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{a / 1e7:,.2f}Cr"
    if a >= 1e5:
        return f"{sign}₹{a / 1e5:,.2f}L"
    return f"{sign}₹{a:,.{dp}f}"


def _pct(v, dp: int = 2) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return ("+" if f >= 0 else "−") + f"{abs(f):.{dp}f}%"


def _tone(v) -> str:
    try:
        return "up" if float(v) >= 0 else "dn"
    except (TypeError, ValueError):
        return ""


def _cell(v, kind: str = "num", dp: int = 2) -> str:
    """A right-aligned numeric cell; signed values carry up/down colour, absolutes do not."""
    if v is None:
        return '<td class="r"><span class="g-sub">—</span></td>'
    if kind == "pct":
        return '<td class="r g-num ' + _tone(v) + '">' + C.esc(_pct(v, dp)) + "</td>"
    if kind == "rs":
        return '<td class="r g-num">' + C.esc(_rs(v, dp)) + "</td>"
    if kind == "rs_signed":
        return '<td class="r g-num ' + _tone(v) + '">' + C.esc(_rs(v, dp)) + "</td>"
    return '<td class="r g-num">' + C.esc(C._num(v, dp)) + "</td>"


def _nav(active: str) -> str:
    out = ['<nav class="gt-nav" aria-label="Tracker views">']
    for suffix, label in _VIEWS:
        cur = ' aria-current="page"' if suffix == active else ""
        out.append('<a href="' + C.esc(_BASE + suffix) + '"' + cur + ">" + C.esc(label) + "</a>")
    out.append("</nav>")
    return "".join(out)


def _demo_banner(kind: str = "book") -> str:
    return ('<div class="gt-demo">🧪 <b>Demo book — invented positions, live prices.</b> The tracker is a '
            "private workspace on a public site, so a visitor sees exactly how it works and never "
            "anyone's real holdings. The entries and dates are made up; the prices, sector and "
            "relative-strength reads beside them are the real tape. "
            '<a href="/dash/tracker/owner">Owner? Unlock your books →</a></div>')


def _bars(items, unit: str = "%") -> str:
    """A labelled proportion bar list — used for allocation and hit-rate blocks."""
    out = ""
    top = max((abs(float(i.get("pct", 0) or 0)) for i in items), default=0) or 100.0
    for i in items[:12]:
        p = float(i.get("pct") or 0)
        w = max(0.0, min(100.0, abs(p) / top * 100.0))
        out += ('<div class="gt-bar"><span class="lb">' + C.esc(i.get("label")) + "</span>"
                '<span class="tr"><i style="width:' + f"{w:.1f}" + '%"></i></span>'
                '<span class="vl">' + C.esc(f"{p:.0f}{unit}") + "</span>"
                + ('<span class="g-sub">' + C.esc(i["note"]) + "</span>" if i.get("note") else "")
                + "</div>")
    return out


def _curve_svg(cv: dict) -> str:
    """Server-computed polyline: the book's chained time-weighted index against its benchmark.
    Numbers only — the client never receives interpolated markup."""
    curve, bench = cv.get("curve") or [], cv.get("bench") or []
    if len(curve) < 2:
        return C.empty("Not enough overlapping sessions yet to chain a return series.")
    vals = [v for v in curve + bench if v is not None]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    w, h = 640.0, 170.0

    def path(series):
        if len(series) < 2:
            return ""
        n = len(series) - 1
        return " ".join(f"{i / n * w:.1f},{h - (v - lo) / rng * h:.1f}" for i, v in enumerate(series))

    b = ('<polyline fill="none" stroke="var(--ink-3)" stroke-width="1.4" stroke-dasharray="4 3" points="'
         + path(bench) + '"/>') if len(bench) >= 2 else ""
    return ('<svg class="gt-curve" viewBox="0 0 640 170" preserveAspectRatio="none" role="img" '
            'aria-label="Book time-weighted return versus benchmark">' + b
            + '<polyline fill="none" stroke="var(--accent)" stroke-width="2" points="' + path(curve)
            + '"/></svg>')


def _is_owner(request) -> bool:
    """Reuse the classic Tracker's privacy gate (`tracker_gate`) rather than fork a second auth:
    the shared-secret cookie / header / query credential it already understands unlocks BOTH
    experiences with one action. Fails CLOSED — any error means the demo book."""
    try:
        from src.web import tracker_gate
        return bool(tracker_gate._is_owner(request))
    except Exception:  # noqa: BLE001 — a privacy gate never fails open
        return False


def _page(title: str, body: str, active: str, conn=None, demo: bool = False) -> HTMLResponse:
    pat = ""
    if conn is not None:
        try:
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
        except Exception:  # noqa: BLE001 — the dock is a garnish, never a dependency
            pat = ""
    head = _nav(active) + (_demo_banner() if demo else "")
    return HTMLResponse(shell.shell(title, head + body, extra_head=_CSS,
                                    current="Tracker", pat_html=pat))


def _book_chips(base: str, books, sel: str) -> str:
    if len(books) < 2:
        return ""
    out = ['<div class="gt-chips">',
           '<a href="' + C.esc(base) + '"' + (' aria-current="true"' if not sel else "") + ">All books</a>"]
    for b in books:
        cur = ' aria-current="true"' if b == sel else ""
        out.append('<a href="' + C.esc(base + "?book=" + b) + '"' + cur + ">" + C.esc(b) + "</a>")
    out.append("</div>")
    return "".join(out)


# ══ 1. OVERVIEW — the cockpit + the model-book door ═══════════════════════════════
def _totals_deck(t: dict, n_watch: int, n_books: int) -> str:
    dp = t.get("day_pct")
    return ('<div class="gt-tiles">'
            + C.tile("Books", C.esc(str(n_books or 1)), "named lists")
            + C.tile("Open positions", C.esc(str(t.get("n") or 0)), "money committed")
            + C.tile("Invested", _rs(t.get("invested"), 0), "at your entry prices")
            + C.tile("Cur. val", _rs(t.get("cur_val"), 0), "at the last close")
            + C.tile("P&L", _rs(t.get("pnl"), 0), _pct(t.get("pnl_pct")) if t.get("pnl_pct") is not None else "needs quantity")
            + C.tile("Day chg.", _pct(dp) if dp is not None else "—", "since the previous close")
            + C.tile("Watchlist", C.esc(str(n_watch)), "ideas, no money in")
            + "</div>")


def _attention_block(rows) -> str:
    att = TR.attention(rows)
    if not att:
        return (C.empty("Nothing in the book is below a stop you set, showing a weakened "
                        "relative-strength phase, or past 30% of its book.")
                + C.learn("This panel restates numbers already in your table — it never tells you to "
                          "buy, sell or hold."))
    body = ('<div class="gt-box"><table class="gt"><thead><tr><th class="spine">Symbol</th><th>Book</th>'
            '<th class="r">LTP</th><th class="r">Your stop</th><th>What we noticed</th></tr></thead><tbody>')
    for a in att:
        flags = "".join('<span class="gt-flag">' + C.esc(x) + "</span>" for x in a["labels"])
        body += ('<tr><td class="spine">' + C.sym_link(a["symbol"]) + "</td>"
                 '<td class="g-sub">' + C.esc(a["book"]) + "</td>"
                 + _cell(a.get("ltp")) + _cell(a.get("stop")) + "<td>" + flags + "</td></tr>")
    body += "</tbody></table></div>"
    return body + C.learn("Each line restates a number from your own table — your stop, the phase the "
                          "tape reports, the share of its book. Descriptive, never a recommendation.")


def _movers_block(rows) -> str:
    mv = sorted(((r["symbol"], r["day_chg"]) for r in rows if r.get("day_chg") is not None),
                key=lambda x: x[1], reverse=True)
    if not mv:
        return C.empty("No day moves on the book yet — the tape lands after the close.")

    def chips(items):
        return "".join('<a class="g-syma" href="/dash/stock?sym=' + C.esc(s) + '">' + C.esc(s)
                       + ' <b class="g-num ' + _tone(v) + '">' + C.esc(_pct(v)) + "</b></a> "
                       for s, v in items) or '<span class="g-sub">—</span>'
    ups = [m for m in mv if m[1] > 0][:5]
    dns = [m for m in mv if m[1] < 0][-5:][::-1]
    return ('<p class="g-sub" style="margin:0 0 4px">Up today</p><p>' + chips(ups) + "</p>"
            '<p class="g-sub" style="margin:10px 0 4px">Down today</p><p>' + chips(dns) + "</p>")


def _alloc_block(rows) -> str:
    al = TR.allocation(rows)
    if not al:
        return (C.empty("Allocation needs a quantity on your positions — without it there is no "
                        "rupee weight to split.")
                + C.learn("Add quantity in the Tracker, or bring it in through Import."))
    body = ('<p class="g-sub" style="margin:0 0 4px">By sector</p>' + _bars(al["by_sector"])
            + '<p class="g-sub" style="margin:12px 0 4px">By book</p>' + _bars(al["by_book"]))
    if al.get("top1") is not None:
        body += ('<p class="g-sub" style="margin:12px 0 0">Largest position <b class="g-num">'
                 + C.esc(f"{al['top1']:.0f}%") + '</b> of the book · top three <b class="g-num">'
                 + C.esc(f"{al['top3']:.0f}%") + "</b></p>")
    contrib = al.get("contrib") or []
    if contrib:
        inner = '<div class="g-ctx">'
        top, bot = contrib[0], contrib[-1]
        for lab, (sym, pp) in (("Top contributor", top), ("Top detractor", bot)):
            if lab == "Top detractor" and (bot[0] == top[0] or bot[1] >= 0):
                continue
            inner += ('<div class="g-ctx-row"><span>' + lab + " " + C.sym_link(sym) + "</span>"
                      '<b class="g-num ' + _tone(pp) + '">'
                      + C.esc(("+" if pp >= 0 else "−") + f"{abs(pp) * 100:.0f} bps") + "</b></div>")
        inner += "</div>"
        body += C.pro_more(inner + '<p class="g-fd-note">Today\'s book move attributed the same way '
                                   "the Today page does it — contribution = weight × day move, in "
                                   "basis points of the book. Descriptive of today only.</p>")
    return body


def _books_block(books) -> str:
    if not books:
        return C.empty("No named books yet — everything lands in “Main” until you name one.")
    body = ('<div class="gt-box"><table class="gt"><thead><tr><th class="spine">Book</th>'
            '<th class="r">Open</th><th class="r">Watch</th><th class="r">Invested</th>'
            '<th class="r">Cur. val</th><th class="r">P&amp;L</th><th class="r">Avg. move</th>'
            "</tr></thead><tbody>")
    for b in books:
        body += ('<tr><td class="spine"><a class="g-syma" href="' + C.esc(_BASE + "/portfolios?book=" + b["book"])
                 + '">' + C.esc(b["book"]) + "</a></td>"
                 + _cell(b["open"], "num", 0) + _cell(b["watch"], "num", 0)
                 + _cell(b.get("invested"), "rs", 0) + _cell(b.get("cur_val"), "rs", 0)
                 + _cell(b.get("pnl"), "rs_signed", 0) + _cell(b.get("avg_move"), "pct", 1) + "</tr>")
    return body + "</tbody></table></div>"


def _model_books_block() -> str:
    """The `model-books` merge, made visible rather than silently dropped.

    The classic estate carried the SAME engine books twice — once as Strategies › Model portfolios,
    once as Tracker › Model books. The Tracker copy's own registry rationale admitted the numbers
    were "already covered by the model_portfolios data flow". In the new experience there is one
    data source and two doors: the books live in Strategies, and following one seeds a named book
    here with TODAY's date and TODAY's close — never the backtest's history, because writing a
    reconstruction into a real book would make the reader's own return a fiction."""
    return (
        '<p>Model books are the engine\'s portfolios — reconstructed, never hand-edited. They live '
        'in <b>Strategies</b>; the Tracker is where you follow one and measure <em>your</em> '
        "result against it.</p>"
        '<div class="gt-act">'
        '<a class="g-btn" href="/dash/model-portfolios">Browse the books →</a>'
        '<a class="g-btn" href="/dash/tracker/model-books">Follow one into a named book →</a>'
        "</div>"
        + C.learn("Following a book copies its CURRENT holdings into a new named book using today's "
                  "date and today's close as your entry. The engine keeps its own record; your book "
                  "measures your adoption. That is why the two numbers will differ, and why both "
                  "are honest.")
        + C.fence("Reconstructed book performance is past data, not a promise and not advice."))


def _overview(conn, demo: bool) -> str:
    pos = TR.demo_positions(conn) if demo else TR.positions(conn)
    wat = TR.demo_watchlist(conn) if demo else TR.watchlist(conn)
    rows, t = pos["rows"], pos["totals"]
    books = ([{"book": "Demo book", "open": len(rows), "watch": wat["n"],
               "invested": t.get("invested"), "cur_val": t.get("cur_val"),
               "pnl": t.get("pnl"), "avg_move": t.get("avg_move")}]
             if demo else TR.books_overview(conn))
    prov = "stocks_in_play · live" if not demo else "stocks_in_play · demo"
    if not rows and not wat["n"]:
        return (C.zone("Your tracker", prov,
                       C.empty("Nothing tracked yet.")
                       + '<div class="gt-act"><a class="g-btn" href="' + _BASE + '/import">Import your holdings →</a>'
                       '<a class="g-btn" href="' + _BASE + '/watchlists">Start a watchlist →</a></div>'
                       + C.learn("A watchlist is ideas you are only watching. A position is money "
                                 "committed — it carries an entry price, so it can be scored."),
                       sub="one book, one scoreboard")
                + C.zone("Follow a model book", "auto_portfolios · nightly", _model_books_block(),
                         sub="one data source, two doors", name="Model books"))
    return (
        C.zone("Your book today", prov, _totals_deck(t, wat["n"], len(books)),
               sub="totals across every named book", sample=demo, name="Book totals")
        + C.zone("Worth a look", prov, _attention_block(rows),
                 sub="restated from your own numbers", sample=demo, name="Worth a look")
        + C.zone("Movers in your book", "NSE bhav copy · EOD", _movers_block(rows),
                 sub="your names, today", sample=demo, name="Your movers")
        + C.zone("Where your money sits", prov, _alloc_block(rows),
                 sub="sector · book · concentration", sample=demo, name="Allocation")
        + C.zone("Your books", prov, _books_block(books), sub="each named list at a glance",
                 sample=demo, name="Books")
        + C.zone("Follow a model book", "auto_portfolios · nightly", _model_books_block(),
                 sub="one data source, two doors", name="Model books"))


# ══ 2. POSITIONS ══════════════════════════════════════════════════════════════════
_POS_HEAD = (
    ('<th class="spine">Symbol</th><th>Sector</th><th class="r">Avg. cost</th><th class="r">Qty</th>'
     '<th class="r">LTP</th><th class="r">Cur. val</th><th class="r">P&amp;L</th><th class="r">P&amp;L %</th>'
     '<th class="r">Day chg.</th><th>Entry date</th>'
     '<th class="r pro-more">Weight</th><th class="r pro-more">Target</th><th class="r pro-more">Stop</th>'
     '<th class="r pro-more">Days held</th><th class="pro-more">RS phase</th><th class="pro-more">Book</th>'))


def _positions_table(rows) -> str:
    body = '<div class="gt-box tall"><table class="gt"><thead><tr>' + _POS_HEAD + "</tr></thead><tbody>"
    for r in rows:
        body += ('<tr><td class="spine">' + C.sym_link(r["symbol"]) + "</td>"
                 '<td class="g-sub">' + C.esc(r.get("sector") or "—") + "</td>"
                 + _cell(r.get("avg_cost"), "num", 2) + _cell(r.get("qty"), "num", 0)
                 + _cell(r.get("ltp"), "num", 2) + _cell(r.get("cur_val"), "rs", 0)
                 + _cell(r.get("pnl"), "rs_signed", 0) + _cell(r.get("pnl_pct"), "pct", 1)
                 + _cell(r.get("day_chg"), "pct", 2)
                 + '<td class="g-sub">' + C.esc(r.get("date_added") or "—") + "</td>"
                 + _cell(r.get("weight"), "pct", 0).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("target"), "num", 1).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("stop"), "num", 1).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("days"), "num", 0).replace('<td class="r', '<td class="r pro-more')
                 + '<td class="pro-more g-sub">' + C.esc(r.get("trend") or "—") + "</td>"
                 '<td class="pro-more g-sub">' + C.esc(r.get("book") or "Main") + "</td></tr>")
    return body + "</tbody></table></div>"


def _positions(conn, demo: bool, book: str) -> str:
    pos = TR.demo_positions(conn) if demo else TR.positions(conn, book)
    rows, t = pos["rows"], pos["totals"]
    prov = "stocks_in_play · live" if not demo else "stocks_in_play · demo"
    if not rows:
        return C.zone("Positions", prov,
                      C.empty("No open positions" + (f" in “{book}”" if book else "") + " yet.")
                      + '<div class="gt-act"><a class="g-btn" href="' + _BASE + '/import">Import holdings →</a>'
                      '<a class="g-btn" href="/dash/tracker/portfolios">Add one by hand →</a></div>',
                      sub="money committed", sample=demo)
    deck = ('<div class="gt-tiles">'
            + C.tile("Positions", C.esc(str(t.get("n") or 0)), (book or "all books"))
            + C.tile("Invested", _rs(t.get("invested"), 0), "at your entry prices")
            + C.tile("Cur. val", _rs(t.get("cur_val"), 0), "at the last close")
            + C.tile("P&L", _rs(t.get("pnl"), 0),
                     _pct(t.get("pnl_pct")) if t.get("pnl_pct") is not None else "add quantity for ₹")
            + C.tile("Day chg.", _pct(t.get("day_pct")) if t.get("day_pct") is not None else "—",
                     "since the previous close")
            + "</div>")
    actions = ('<div class="gt-act">'
               '<a class="g-btn" href="' + C.esc(_BASE + "/export?view=portfolio" + (f"&book={book}" if book else ""))
               + '">⬇ Download CSV</a>'
               '<a class="g-btn" href="' + _BASE + '/import">Import more →</a>'
               '<a class="g-btn" href="/dash/tracker/portfolios">Edit or close a position →</a></div>')
    note = C.learn("Read this the way your broker reads: <b>Avg. cost</b> is what you paid, "
                   "<b>LTP</b> the last traded price, <b>Cur. val</b> quantity × LTP, and "
                   "<b>Day chg.</b> the move since the previous close. Pro adds weight, your target "
                   "and stop, days held and the relative-strength phase — every number that a "
                   "decision rests on is already here in Free.")
    return C.zone("Positions", prov, deck + _book_chips(_BASE + "/portfolios", pos["books"], book)
                  + _positions_table(rows) + note + actions,
                  sub="your book, marked to the last close", sample=demo, name="Positions")


# ══ 3. WATCHLIST ══════════════════════════════════════════════════════════════════
def _watch_table(rows) -> str:
    body = ('<div class="gt-box tall"><table class="gt"><thead><tr><th class="spine">Symbol</th>'
            '<th>Sector</th><th class="r">LTP</th><th class="r">Day chg.</th><th>RS phase</th>'
            '<th class="r">Delivery</th><th>Added</th>'
            '<th class="r pro-more">Price then</th><th class="r pro-more">Since added</th>'
            '<th class="r pro-more">Days</th><th class="r pro-more">RS rank</th>'
            '<th class="r pro-more">Own deliv. avg</th><th class="pro-more">Book</th>'
            "</tr></thead><tbody>")
    for r in rows:
        body += ('<tr><td class="spine">' + C.sym_link(r["symbol"]) + "</td>"
                 '<td class="g-sub">' + C.esc(r.get("sector") or "—") + "</td>"
                 + _cell(r.get("ltp"), "num", 2) + _cell(r.get("day_chg"), "pct", 2)
                 + '<td class="g-sub">' + C.esc(r.get("trend") or "—") + "</td>"
                 + _cell(r.get("deliv"), "num", 0)
                 + '<td class="g-sub">' + C.esc(r.get("date_added") or "—") + "</td>"
                 + _cell(r.get("then"), "num", 2).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("since_add"), "pct", 1).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("days"), "num", 0).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("rank"), "num", 0).replace('<td class="r', '<td class="r pro-more')
                 + _cell(r.get("deliv_norm"), "num", 0).replace('<td class="r', '<td class="r pro-more')
                 + '<td class="pro-more g-sub">' + C.esc(r.get("book") or "Main") + "</td></tr>")
    return body + "</tbody></table></div>"


def _watchlists(conn, demo: bool, book: str) -> str:
    wat = TR.demo_watchlist(conn) if demo else TR.watchlist(conn, book)
    rows = wat["rows"]
    prov = "stocks_in_play · live" if not demo else "stocks_in_play · demo"
    # THE SAME write path the Graphite home owns — one endpoint, one validation, one store.
    addform = C._wl_addform()
    add_note = ('<p class="g-sub" style="margin:6px 0 0">Adding writes the same watch list the '
                "Today page shows, and lands you back on Today with the confirmation.</p>")
    if not rows:
        return C.zone("Watchlist", prov,
                      C.empty("Nothing on the watchlist" + (f" in “{book}”" if book else "") + " yet.")
                      + addform + add_note
                      + C.learn("A watchlist is ideas with no money in them. The moment you commit, "
                                "promote it to a position so it can be scored."),
                      sub="ideas, no money in", sample=demo)
    actions = ('<div class="gt-act">'
               '<a class="g-btn" href="' + C.esc(_BASE + "/export?view=watchlist" + (f"&book={book}" if book else ""))
               + '">⬇ Download CSV</a>'
               '<a class="g-btn" href="/dash/tracker/watchlists">Set alerts · promote · remove →</a></div>')
    note = C.learn("These are ideas you are watching — no entry, no commitment. <b>RS phase</b> is "
                   "where the name sits against the broad market, and <b>Delivery</b> is the share of "
                   "the day's volume that actually changed hands. Pro adds the price on the day you "
                   "added it, the move since, and how today's delivery compares with the name's own "
                   "one-month average.")
    return C.zone("Watchlist", prov,
                  _book_chips(_BASE + "/watchlists", wat["books"], book) + _watch_table(rows)
                  + addform + add_note + note + actions,
                  sub="ideas, no money in", sample=demo, name="Watchlist")


# ══ 4. SCOREBOARD ═════════════════════════════════════════════════════════════════
def _xirr_panel(fid: dict, value) -> str:
    """The ratified §K.4 pre-condition, rendered. When the check passes the number ships; when it
    fails the reader gets the measurement and the reason, never a plausible-looking figure."""
    if fid.get("verdict") == "PASS" and value is not None:
        return ('<div class="gt-verdict"><h4>XIRR ' + C.esc(_pct(value, 1)) + "</h4>"
                '<p class="g-sub" style="margin:0">Money-weighted annual return. This book passed the '
                "cash-flow check: every position carries a date and a quantity, no symbol appears as "
                "several lots, and no split, bonus or dividend falls inside a holding period — so the "
                "dated flows are complete and the number means what it says.</p></div>")
    items = "".join("<li>" + C.esc(r) + "</li>" for r in (fid.get("reasons") or []))
    return ('<div class="gt-verdict fail"><h4>XIRR — not shown, and here is exactly why</h4>'
            '<p class="g-sub" style="margin:0 0 2px">A money-weighted return (XIRR) needs a dated '
            "<b>cash-flow</b> ledger: every rupee in and out, on the day it moved, adjusted for splits "
            "and bonuses. What we store is a <b>position</b> ledger — one row per holding. We ran the "
            "check against your actual rows:</p><ul>" + (items or "<li>nothing to measure yet</li>")
            + "</ul>"
            '<p class="g-sub" style="margin:8px 0 0">So the headline below is a <b>time-weighted</b> '
            "return instead: it chains each session's move across the names held on both sides of that "
            "session, which needs prices rather than cash flows. It answers “how did the selection "
            "do”, not “how did my money do”. The second question returns the day the ledger records "
            "transactions.</p></div>")


def _scoreboard(conn, demo: bool) -> str:
    if demo:
        pos = TR.demo_positions(conn)
        t = pos["totals"]
        body = ('<div class="gt-tiles">'
                + C.tile("Open", C.esc(str(t.get("n") or 0)), "demo positions")
                + C.tile("Unrealised", _rs(t.get("pnl"), 0), "live prices, invented entries")
                + C.tile("Avg. move", _pct(t.get("avg_move"), 1) if t.get("avg_move") is not None else "—",
                         "per position")
                + "</div>"
                + C.empty("The full scoreboard — realised versus unrealised, hit-rate, the return "
                          "curve against Nifty 500, and the cash-flow check behind XIRR — is built "
                          "from a real trade history.")
                + C.learn("Unlock your books and the scoreboard fills itself in as you take and "
                          "close positions. Nothing here needs configuring."))
        return C.zone("Scoreboard", "stocks_in_play · demo", body, sub="the demo book",
                      sample=True, name="Scoreboard")
    p = TR.performance(conn)
    fid = TR.cashflow_fidelity(conn)
    xirr = TR.xirr(conn) if fid.get("verdict") == "PASS" else None
    if not (p["n_open"] or p["n_closed"]):
        return C.zone("Scoreboard", "stocks_in_play · live",
                      C.empty("No positions yet — the scoreboard fills itself as you take and close them.")
                      + '<div class="gt-act"><a class="g-btn" href="' + _BASE + '/import">Import your holdings →</a></div>',
                      sub="your record, measured")
    cv = p.get("curve") or {}
    deck = ('<div class="gt-tiles">'
            + C.tile("Open", C.esc(str(p["n_open"])), "positions")
            + C.tile("Closed", C.esc(str(p["n_closed"])), "trades logged")
            + C.tile("Realised", _rs(p.get("realised"), 0), "booked")
            + C.tile("Unrealised", _rs(p.get("unrealised"), 0), "still open")
            + C.tile("Total P&L", _rs(p.get("total_pnl"), 0),
                     _pct(p.get("total_pct"), 1) if p.get("total_pct") is not None else "needs quantity")
            + C.tile("Hit-rate", (f"{p['hit']:.0f}%" if p.get("hit") is not None else "—"),
                     f"of {p['n_closed']} closed")
            + C.tile("Avg. return", _pct(p.get("avg_ret"), 1) if p.get("avg_ret") is not None else "—",
                     "per closed trade")
            + C.tile("vs Nifty 500", _pct(p.get("avg_excess"), 1) if p.get("avg_excess") is not None else "—",
                     f"avg excess, {p.get('n_excess') or 0} trades")
            + C.tile("Avg. hold", (f"{p['avg_hold']:.0f}d" if p.get("avg_hold") is not None else "—"),
                     "days per closed trade")
            + "</div>")
    curve = ""
    if cv:
        sub = ("Book <b class='g-num " + _tone(cv.get("ret")) + "'>" + C.esc(_pct(cv.get("ret"), 1))
               + "</b> · " + C.esc(p["benchmark"]) + " <b class='g-num " + _tone(cv.get("bench_ret"))
               + "'>" + C.esc(_pct(cv["bench_ret"], 1) if cv.get("bench_ret") is not None else "—")
               + "</b>" + (" · deepest fall <b class='g-num dn'>" + C.esc(_pct(cv["dd"], 1)) + "</b>"
                           if cv.get("dd") else ""))
        curve = ('<p class="g-sub" style="margin:0 0 6px">' + sub + "</p>" + _curve_svg(cv)
                 + '<p class="g-sub" style="margin:6px 0 0">Both rebased to 100 at the first session '
                 "the book existed. The dashed line is " + C.esc(p["benchmark"]) + ".</p>"
                 + C.learn("Because a new position entering the book would otherwise look like a "
                           "gain, each step compares only the names held on <b>both</b> sides of "
                           "that session, then chains the steps. That is a time-weighted return: it "
                           "measures the selection, not the timing of your deposits."))
        if cv.get("equal_weight"):
            curve += C.fence("Some positions carry no quantity, so the curve weights every position "
                             "equally by rupee at entry. Add quantity for a true book weighting.")
    hits = ""
    if p["by_strategy"] or p["by_book"]:
        def hrows(rows):
            return [{"label": r["k"], "pct": r["hit"],
                     "note": f"n={r['n']} · avg {r['avg_ret']:+.1f}%"} for r in rows]
        hits = ('<p class="g-sub" style="margin:0 0 4px">Hit-rate by strategy</p>' + _bars(hrows(p["by_strategy"]))
                + ('<p class="g-sub" style="margin:12px 0 4px">Hit-rate by book</p>' + _bars(hrows(p["by_book"]))
                   if p["by_book"] else "")
                + C.learn("Hit-rate is the share of <em>closed</em> positions that exited above entry. "
                          "Read it beside the average return next to it — a high hit-rate with small "
                          "wins and rare large losses is not the same record."))
    else:
        hits = C.empty("Hit-rate, attribution and the closed-trades log fill in once you close trades.")
    log = ""
    if p["closed"]:
        log = ('<div class="gt-box"><table class="gt"><thead><tr><th class="spine">Symbol</th>'
               '<th>Book</th><th>Strategy</th><th>Entry</th><th>Exit</th><th class="r">Days</th>'
               '<th class="r">Entry ₹</th><th class="r">Exit ₹</th><th class="r">Return</th>'
               '<th class="r">₹ P&amp;L</th>'
               '<th class="r pro-more">' + C.esc(p["benchmark"]) + ' same window</th>'
               '<th class="r pro-more">Excess</th><th>Reason</th></tr></thead><tbody>')
        for r in p["closed"]:
            log += ('<tr><td class="spine">' + C.sym_link(r["symbol"]) + "</td>"
                    '<td class="g-sub">' + C.esc(r["book"]) + "</td>"
                    '<td class="g-sub">' + C.esc(r.get("strategy") or "—") + "</td>"
                    '<td class="g-sub">' + C.esc(r["date_added"]) + "</td>"
                    '<td class="g-sub">' + C.esc(r["exit_date"]) + "</td>"
                    + _cell(r.get("days"), "num", 0) + _cell(r.get("entry"), "num", 2)
                    + _cell(r.get("exit"), "num", 2) + _cell(r.get("ret_pct"), "pct", 1)
                    + _cell(r.get("pnl"), "rs_signed", 0)
                    + _cell(r.get("bench"), "pct", 1).replace('<td class="r', '<td class="r pro-more')
                    + _cell(r.get("excess"), "pct", 1).replace('<td class="r', '<td class="r pro-more')
                    + '<td class="g-sub">' + C.esc(r.get("reason") or "—") + "</td></tr>")
        log += ('</tbody></table></div>'
                + C.learn("Every number on this scoreboard is in Free — evidence is never behind a "
                          "paywall. Pro adds the <em>reference</em> beside each exit: what "
                          + C.esc(p["benchmark"]) + " did over that same holding window, and the "
                          "difference. A +20% trade in a +25% market is not a good trade.")
                + '<div class="gt-act"><a class="g-btn" href="'
                + _BASE + '/export?view=closed">⬇ Download CSV</a></div>')
    return (C.zone("Scoreboard", "stocks_in_play · live", deck + _xirr_panel(fid, xirr),
                   sub="your record, measured honestly", name="Scoreboard")
            + (C.zone("Return over time", "NSE bhav copy · EOD", curve,
                      sub="time-weighted, against " + p["benchmark"], name="Return curve") if curve else "")
            + C.zone("What worked", "stocks_in_play · live", hits, sub="by strategy and by book",
                     name="What worked")
            + (C.zone("Closed trades", "stocks_in_play · live", log, sub="every exit, logged",
                      name="Closed trades") if log else ""))


# ══ 5. IMPORT ═════════════════════════════════════════════════════════════════════
def _import_form(demo: bool) -> str:
    disabled = " disabled" if demo else ""
    return (
        '<form class="gt-form" method="post" action="' + _BASE + '/import/preview" '
        'enctype="multipart/form-data">'
        '<div class="gt-2col">'
        '<div><label for="gt-status">Bring it in as</label>'
        '<select id="gt-status" name="status"' + disabled + '>'
        '<option value="open">Positions — money already committed</option>'
        '<option value="watch">Watchlist — just watching</option></select></div>'
        '<div><label for="gt-book">Book name</label>'
        '<input id="gt-book" type="text" name="book" value="Main" maxlength="40"' + disabled + '></div>'
        "</div>"
        '<label for="gt-file">Upload a file <span class="g-sub">CSV, any column order</span></label>'
        '<input id="gt-file" type="file" name="file" accept=".csv,text/csv,text/plain"' + disabled + '>'
        '<label for="gt-paste">…or paste it straight in</label>'
        '<textarea id="gt-paste" name="pasted" placeholder="Symbol,Qty,Avg cost,Date&#10;'
        'RELIANCE,25,1320.50,2026-01-15"' + disabled + "></textarea>"
        '<div class="gt-act"><button class="g-btn" type="submit"' + disabled + ">Preview before saving</button>"
        '<a class="g-btn" href="' + _BASE + '/template.csv">⬇ Blank template</a></div>'
        "</form>")


def _import_page(demo: bool) -> str:
    body = (
        "<p>Bring an existing book in from your broker's holdings export, a spreadsheet, or a "
        "pasted block — <b>any column order</b>. We read Symbol, Quantity, Average cost, Entry date "
        "and an optional note, match every ticker against the NSE cash list, and show you exactly "
        "what will be saved <b>before</b> anything is written.</p>"
        + _import_form(demo)
        + C.learn("Nothing is saved at this step. The preview marks each row <b>ready</b>, "
                  "<b>already there</b>, or <b>can't read it</b> with the reason, and you confirm. "
                  "Rows that fail are never written, and the file itself is discarded once parsed.")
        + C.fence("Imported entries are your record of what you paid. We do not verify them against "
                  "your broker — they are your numbers, used only to compute your own P&L."))
    if demo:
        body += C.empty("Importing is switched off in the public demo — unlock your books to load "
                        "your own holdings.")
    return C.zone("Import", "stocks_in_play · write", body, sub="file or paste → preview → save",
                  sample=demo, name="Import")


_STATE_LABEL = {"ok": ("ok", "READY"), "skip": ("skip", "ALREADY THERE"), "bad": ("bad", "CAN'T READ")}


def _preview_page(v: dict, status: str, book: str, truncated: bool) -> str:
    rows = v["rows"]
    deck = ('<div class="gt-tiles">'
            + C.tile("Rows read", C.esc(str(v["n"])), "from your file")
            + C.tile("Ready to save", C.esc(str(v["ok"])), "validated against NSE")
            + C.tile("Already there", C.esc(str(v["skip"])), "left alone")
            + C.tile("Can't read", C.esc(str(v["bad"])), "not saved")
            + "</div>")
    tbl = ('<div class="gt-box tall"><table class="gt"><thead><tr><th class="spine">Symbol</th>'
           '<th class="r">Qty</th><th class="r">Avg. cost</th><th>Entry date</th><th>Note</th>'
           '<th>Status</th></tr></thead><tbody>')
    for r in rows:
        cls, lab = _STATE_LABEL.get(r.get("state"), ("skip", "?"))
        why = ('<span class="g-sub"> ' + C.esc(r.get("why")) + "</span>") if r.get("why") else ""
        tbl += ('<tr><td class="spine">' + (C.sym_link(r["symbol"]) if r.get("symbol")
                                            else '<span class="g-sub">—</span>') + "</td>"
                + _cell(r.get("qty"), "num", 0) + _cell(r.get("price"), "num", 2)
                + '<td class="g-sub">' + C.esc(r.get("date") or "today") + "</td>"
                '<td class="g-sub">' + C.esc(r.get("note") or "—") + "</td>"
                '<td><span class="gt-state ' + cls + '">' + lab + "</span>" + why + "</td></tr>")
    tbl += "</tbody></table></div>"
    payload = json.dumps([{k: r.get(k) for k in ("symbol", "qty", "price", "date", "note")}
                          for r in rows if r.get("state") == "ok"], separators=(",", ":"))
    confirm = ('<form class="gt-form" method="post" action="' + _BASE + '/import/commit">'
               '<input type="hidden" name="status" value="' + C.esc(status) + '">'
               '<input type="hidden" name="book" value="' + C.esc(book) + '">'
               '<input type="hidden" name="rows" value="' + C.esc(payload) + '">'
               '<div class="gt-act"><button class="g-btn" type="submit">Save '
               + C.esc(str(v["ok"])) + " row" + ("" if v["ok"] == 1 else "s") + " to “"
               + C.esc(book) + "”</button>"
               '<a class="g-btn" href="' + _BASE + '/import">Start over</a></div></form>'
               ) if v["ok"] else ('<div class="gt-act"><a class="g-btn" href="' + _BASE
                                  + '/import">Try another file</a></div>')
    warn = (C.fence(f"Only the first {len(rows)} rows were read — split a larger file and import it "
                    "in parts.") if truncated else "")
    return C.zone("Import preview", "stocks_in_play · nothing saved yet",
                  deck + warn + tbl
                  + C.learn("Everything is still unsaved. Confirm and only the <b>ready</b> rows are "
                            "written — each one re-checked at the moment of saving, so a stale "
                            "preview can never write a bad row.")
                  + confirm,
                  sub="check it, then save", name="Import preview")


# ══ routes ════════════════════════════════════════════════════════════════════════
def _conn():
    from src.core.db import get_conn
    return get_conn()


def _render(request: Request, active: str, title: str, fn) -> HTMLResponse:
    demo = not _is_owner(request)
    try:
        with _conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            return _page(title, fn(conn, demo), active, conn, demo)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 a page
        return _page(title, C.fence("Your tracker data hasn't landed yet.")
                     + C.empty("Check back after the next nightly run."), active, None, demo)


@router.get("/dash/home/tracker", response_class=HTMLResponse, include_in_schema=False)
def tracker_home(request: Request) -> HTMLResponse:
    return _render(request, "", "Tracker", _overview)


@router.get("/dash/home/tracker/portfolios", response_class=HTMLResponse, include_in_schema=False)
def tracker_positions(request: Request) -> HTMLResponse:
    book = (request.query_params.get("book") or "").strip()[:40]
    return _render(request, "/portfolios", "Positions",
                   lambda conn, demo: _positions(conn, demo, book))


@router.get("/dash/home/tracker/watchlists", response_class=HTMLResponse, include_in_schema=False)
def tracker_watchlists(request: Request) -> HTMLResponse:
    book = (request.query_params.get("book") or "").strip()[:40]
    return _render(request, "/watchlists", "Watchlist",
                   lambda conn, demo: _watchlists(conn, demo, book))


@router.get("/dash/home/tracker/performance", response_class=HTMLResponse, include_in_schema=False)
def tracker_performance(request: Request) -> HTMLResponse:
    return _render(request, "/performance", "Scoreboard", _scoreboard)


@router.get("/dash/home/tracker/import", response_class=HTMLResponse, include_in_schema=False)
def tracker_import(request: Request) -> HTMLResponse:
    demo = not _is_owner(request)
    return _page("Import", _import_page(demo), "/import", None, demo)


@router.get("/dash/home/tracker/template.csv", include_in_schema=False)
def tracker_template() -> PlainTextResponse:
    return PlainTextResponse(
        TR.template_csv(), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="patearn-import-template.csv"'})


@router.get("/dash/home/tracker/export", include_in_schema=False)
def tracker_export(request: Request):
    """Server-side CSV of what the reader is looking at (playbook §3.8). Owner-only: an export is
    the personal book leaving the site, so the demo never produces one."""
    if not _is_owner(request):
        return RedirectResponse(_BASE, status_code=303)
    view = (request.query_params.get("view") or "portfolio").strip().lower()
    view = view if view in ("portfolio", "watchlist", "closed") else "portfolio"
    book = (request.query_params.get("book") or "").strip()[:40]
    try:
        with _conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            fname, text = TR.export_csv(conn, view, book)
    except Exception:  # noqa: BLE001
        return RedirectResponse(_BASE, status_code=303)
    return PlainTextResponse(text, media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/dash/home/tracker/import/preview", response_class=HTMLResponse, include_in_schema=False)
async def tracker_import_preview(request: Request, status: str = Form("open"),
                                 book: str = Form("Main"),
                                 pasted: str = Form(""),
                                 file: UploadFile = File(None)) -> HTMLResponse:
    """Parse + validate ONLY — nothing is written here. Owner-only."""
    if not _is_owner(request):
        return RedirectResponse(_BASE + "/import", status_code=303)
    status = status if status in ("open", "watch") else "open"
    book = (book or "Main").strip()[:40] or "Main"
    text = pasted or ""
    if file is not None and getattr(file, "filename", ""):
        raw = await file.read(TR.MAX_UPLOAD_BYTES + 1)
        if len(raw) > TR.MAX_UPLOAD_BYTES:
            return _page("Import", C.zone("Import", "stocks_in_play · write",
                                          C.fence("That file is larger than 2 MB. A holdings sheet "
                                                  "is far smaller — check it is the right file.")
                                          + _import_form(False), name="Import"), "/import")
        text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        return _page("Import", C.zone("Import", "stocks_in_play · write",
                                      C.fence("Nothing to read — attach a CSV or paste your rows.")
                                      + _import_form(False), name="Import"), "/import")
    p = TR.parse_holdings(text)
    try:
        with _conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            v = TR.validate_rows(conn, p["rows"], status)
    except Exception:  # noqa: BLE001
        return _page("Import", C.zone("Import", "stocks_in_play · write",
                                      C.fence("Couldn't check those rows against the market list "
                                              "just now — try again in a moment.")
                                      + _import_form(False), name="Import"), "/import")
    return _page("Import preview", _preview_page(v, status, book, p.get("truncated", False)), "/import")


@router.post("/dash/home/tracker/import/commit", include_in_schema=False)
def tracker_import_commit(request: Request, rows: str = Form(""), status: str = Form("open"),
                          book: str = Form("Main")):
    """Write the confirmed rows. Every row is RE-VALIDATED here — the preview's verdict is never
    trusted on the way back in, so a tampered or stale form cannot write an unknown symbol."""
    if not _is_owner(request):
        return RedirectResponse(_BASE + "/import", status_code=303)
    status = status if status in ("open", "watch") else "open"
    book = (book or "Main").strip()[:40] or "Main"
    written = 0
    try:
        parsed = json.loads(rows or "[]")
        clean = [{"symbol": str(r.get("symbol") or "")[:24].upper(),
                  "qty": r.get("qty"), "price": r.get("price"),
                  "date": r.get("date"), "note": str(r.get("note") or "")[:80]}
                 for r in parsed if isinstance(r, dict)][:500]
        with _conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            v = TR.validate_rows(conn, clean, status)
            written, _skipped = TR.commit_rows(conn, v["rows"], status, book)
    except Exception:  # noqa: BLE001 — a write hiccup must never crash the page
        written = 0
    dest = _BASE + ("/watchlists" if status == "watch" else "/portfolios")
    return RedirectResponse(dest + "?imported=" + str(written), status_code=303)


def _selftest() -> int:
    """Render-shape checks that need no database."""
    assert _nav("/portfolios").count("aria-current") == 1
    assert '<a href="/dash/home/tracker/import"' in _nav("/import")
    assert "gt-demo" in _demo_banner() and "/dash/tracker/owner" in _demo_banner()
    assert _rs(12500000, 0) == "₹1.25Cr" and _rs(-45000) == "−₹45,000" and _rs(None) == "—"
    assert _pct(-1.234) == "−1.23%" and _pct(None) == "—"
    f = _xirr_panel({"verdict": "FAIL", "reasons": ["no quantity"]}, None)
    assert "not shown" in f and "no quantity" in f and "time-weighted" in f
    ok = _xirr_panel({"verdict": "PASS", "reasons": []}, 12.5)
    assert "XIRR +12.5%" in ok
    frm = _import_form(False)
    assert 'action="/dash/home/tracker/import/preview"' in frm and "pasted" in frm
    assert "disabled" in _import_form(True)
    assert 'action="/dash/home/watch/add"' in C._wl_addform(), "the watch write path must stay shared"
    assert "pro-more" in _POS_HEAD, "the Pro column layer must be declared on the header row"
    print("tracker_pages selftest OK — 5 views, demo banner, shared watch POST, XIRR verdict both ways")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
