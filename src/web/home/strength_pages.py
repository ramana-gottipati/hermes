"""src/web/home/strength_pages.py — the Graphite "Strength" page (W2-B) + this lane's ONE router.

The classic estate split relative strength across four lenses: `/dash/rs-hub` (the hub),
`/dash/leaders` (strong-in-strong), `/dash/momentum-scan` (risk-adjusted momentum) and
`/dash/capture-map` (the all-weather map). They answer one question — *is it beating the market, and
what did that cost?* — so in Graphite they are four VIEWS of one page, `/dash/home/strength?view=…`.

This module also owns the lane's single `APIRouter`, mounted by ONE anchored entry in
`v2_surfaces._ROUTER_SPECS`. It registers three routes; the page BODIES live in their own lane-owned
modules (`strength_pages` here, `sectors_pages`, `rotation_pages`) so no module owns two jobs.

Isolation: nothing here imports a classic view module. Numbers come from `markets_reads`, which
reuses the canonical `src/automation/` engines.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import markets_reads as R
from src.web.home import markets_ui as U

router = APIRouter()

VIEWS = (("overview", "Overview"), ("leaders", "Leaders"), ("momentum", "Momentum"),
         ("capture", "All-weather"))
_KEYS = {k for k, _ in VIEWS}

TITLES = {
    "overview": ("Where strength sits today",
                 "how many names are beating the market, and the four ways to read it"),
    "leaders": ("Strong inside a strong sector",
                "names leading their own sector AND the market, in a sector leading the market"),
    "momentum": ("Move per unit of choppiness",
                 "six-month return divided by recent volatility — a shortlister, never a buy list"),
    "capture": ("What the strength cost",
                "how much of the market's rises and falls each sector actually took"),
}

_FENCE = ("Relative strength is one question asked per horizon: did this beat the broad market? "
          "Everything here describes what already happened, from NSE data — never advice, "
          "a recommendation, or a prediction.")


def view_of(raw) -> str:
    v = str(raw or "").strip().lower()
    return v if v in _KEYS else "overview"


def head(view: str) -> str:
    title, sub = TITLES.get(view, TITLES["overview"])
    return (U.tabs(VIEWS, view, U.STRENGTH_HREF)
            + '<p class="g-mnote" style="margin:0 0 12px"><b style="color:var(--ink)">'
            + C.esc(title) + "</b> — " + C.esc(sub) + "</p>")


# ── view: OVERVIEW (ports /dash/rs-hub) ───────────────────────────────────────────────
def _state_word(st) -> str:
    return {"UPTREND": "Beating the market", "BREAKOUT": "Just broke out",
            "CONSOLIDATING": "Going sideways versus the market",
            "DOWNTREND": "Lagging the market", "BREAKDOWN": "Just broke down"}.get(
        str(st or "").upper(), str(st or "—").title())


def _standing_rows(rows) -> str:
    out = ""
    for r in rows:
        out += ("<tr><td>" + U.sym(r.get("symbol")) + "</td>"
                '<td class="r">' + U.num(r.get("rs_rank"), 0) + "</td>"
                "<td>" + C.esc(R._short(r.get("primary_sector"))) + "</td>"
                "<td>" + U.phase_pill(r.get("rs_phase"), R.phase_label(r.get("rs_phase"))) + "</td>"
                "<td>" + C.esc(_state_word(r.get("state"))) + "</td>"
                '<td class="r pro-more">' + U.signed(r.get("s3")) + "</td>"
                '<td class="r pro-more">' + U.signed(r.get("s12")) + "</td>"
                '<td class="r pro-more">' + U.num(r.get("rsi"), 0) + "</td></tr>")
    return out


def _counts_strip(c: dict) -> str:
    """The one-glance answer: of everything we rank today, how much is actually beating the market."""
    if not c or not c.get("total"):
        return ""
    st = c.get("states") or {}
    up = (st.get("UPTREND") or 0) + (st.get("BREAKOUT") or 0)
    dn = (st.get("DOWNTREND") or 0) + (st.get("BREAKDOWN") or 0)
    tot = sum(v or 0 for v in st.values()) or 1
    return ('<div class="g-mgrid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">'
            + C.tile("Beating the market", U.num(100.0 * up / tot, 0) + "%",
                     str(up) + " of " + str(tot) + " ranked names")
            + C.tile("Lagging the market", U.num(100.0 * dn / tot, 0) + "%", str(dn) + " names")
            + C.tile("In the top RS decile", U.num(c.get("top"), 0), "rank 90 and above")
            + C.tile("In the bottom decile", U.num(c.get("bottom"), 0), "rank 10 and below")
            + "</div>")


def _lens_cards() -> str:
    """The hub's job: name the four readings and where each one goes."""
    cards = (
        ("Leaders", U.STRENGTH_HREF + "?view=leaders", "who is strong inside a strong sector",
         "Three layers have to agree at once: the stock beats its sector, the stock beats the "
         "market, and the sector beats the market."),
        ("All-weather", U.STRENGTH_HREF + "?view=capture", "what the strength cost in falls",
         "Two numbers most boards hide behind one: how much of the market's rise a sector took, "
         "and how much of its fall."),
        ("Rotation", U.ROTATION_HREF, "the direction of travel",
         "The same relative strength drawn as a journey, a weather map, a range position and a "
         "lifecycle clock."),
        ("Sectors", U.SECTORS_HREF, "the sector standing and the businesses underneath",
         "Which sectors lead, how broad that leadership is inside them, and a decade of what the "
         "companies actually earn."),
    )
    out = ""
    for title, href, q, blurb in cards:
        out += ('<a class="g-mcell" style="text-decoration:none;display:block" href="'
                + C.safe_url(href) + '"><h4>' + C.esc(title)
                + '<span class="g-mnum" style="color:var(--accent)">→</span></h4>'
                '<span class="g-msub">' + C.esc(q) + "</span>"
                '<p class="g-mnote" style="margin:0">' + C.esc(blurb) + "</p></a>")
    return '<div class="g-mgrid">' + out + "</div>"


def overview(conn) -> str:
    counts = R.rs_counts(conn)
    rows, demo = R.rs_standing(conn, limit=25), False
    if not rows:
        rows, demo = R.DEMO_STANDING, True
    cols = [("Symbol", ""), ("RS rank", "r"), ("Sector", ""), ("Phase", ""),
            ("Versus the market", ""), ('<span class="pro-more">3m RS</span>', "r pro-more"),
            ('<span class="pro-more">12m RS</span>', "r pro-more"),
            ('<span class="pro-more">RSI-of-RS</span>', "r pro-more")]
    return (_counts_strip(counts)
            + U.head("Four ways to read one question", "open any card for the full view")
            + _lens_cards()
            + U.head("Today's strongest names", "highest relative-strength rank first")
            + U.sample_note(demo, "the RS standing")
            + U.table(cols, _standing_rows(rows), height=360,
                      note="RS rank is a percentile against everything else ranked today — 97 means "
                           "stronger than 97 percent of the universe, not a 97 percent gain.")
            + C.pro_more('<p class="g-mnote">Pro adds the 3-month and 12-month relative-strength '
                         "slopes beside the rank, plus RSI-of-RS — so a name at rank 90 that is "
                         "still accelerating reads differently from one at rank 90 that is "
                         "fading.</p>")
            + C.learn("Relative strength compares a stock's price to the broad index. If the index "
                      "falls 5 percent and the stock falls 2, its relative strength ROSE — it is "
                      "strong while still losing money. That is why relative strength is context, "
                      "never a standalone reason to do anything."))


# ── view: LEADERS (ports /dash/leaders) ───────────────────────────────────────────────
def _leader_rows(rows) -> str:
    out = ""
    for r in rows:
        out += ("<tr><td>" + U.sym(r.get("symbol")) + "</td>"
                '<td class="r">' + U.num(r.get("rs_rank"), 0) + "</td>"
                "<td>" + C.esc(R._short(r.get("primary_sector"))) + "</td>"
                '<td class="r pro-more">' + U.num(r.get("rsi"), 0) + "</td>"
                '<td class="pro-more">' + C.esc(_state_word(r.get("broad_state"))) + "</td>"
                '<td class="pro-more">' + C.esc(_state_word(r.get("sector_state"))) + "</td>"
                '<td class="pro-more">' + C.esc(_state_word(r.get("sector_broad_state")))
                + "</td></tr>")
    return out


def leaders(conn) -> str:
    lead, lag = R.leaders("leaders", 30), R.leaders("laggards", 20)
    demo = not lead and not lag
    if demo:
        lead, lag = R.DEMO_LEADERS, R.DEMO_LAGGARDS
    cols = [("Symbol", ""), ("RS rank", "r"), ("Sector", ""),
            ('<span class="pro-more">RSI-of-RS</span>', "r pro-more"),
            ('<span class="pro-more">Versus market</span>', "pro-more"),
            ('<span class="pro-more">Versus sector</span>', "pro-more"),
            ('<span class="pro-more">Sector vs market</span>', "pro-more")]
    return (U.sample_note(demo, "leaders and laggards")
            + C.fence("An alignment screen, not a buy or sell list. It says three relative-strength "
                      "readings agree right now; it says nothing about what happens next.")
            + U.head("Leaders", "strong versus their sector, versus the market, in a sector beating "
                                "the market")
            + U.table(cols, _leader_rows(lead), height=340)
            + U.head("Laggards", "the exact mirror — all three readings down")
            + U.table(cols, _leader_rows(lag), height=260,
                      note="Only liquid names are eligible, so a thin counter that technically "
                           "qualifies cannot fill the board.")
            + C.pro_more('<p class="g-mnote">Pro shows the three underlying trend states that had '
                         "to align, plus RSI-of-RS — so you can see whether a name qualified "
                         "comfortably or only just.</p>")
            + C.learn("Any one relative-strength reading can flatter a name: a weak stock in a "
                      "collapsing sector still 'beats its sector'. Requiring all three at once — "
                      "stock over sector, stock over market, sector over market — removes most of "
                      "that flattery. It is a filter, not a forecast."))


# ── view: MOMENTUM (ports /dash/momentum-scan) ────────────────────────────────────────
def _momentum_rows(rows) -> str:
    out = ""
    for i, r in enumerate(rows, 1):
        out += ('<tr><td class="r">' + str(i) + "</td>"
                "<td>" + U.sym(r.get("symbol")) + "</td>"
                '<td class="r">' + U.signed(r.get("mom6")) + "</td>"
                '<td class="r">' + U.signed(r.get("mom12")) + "</td>"
                '<td class="r">' + U.num(r.get("vol_66"), 1) + "</td>"
                '<td class="r">' + U.num(r.get("riskadj"), 2) + "</td>"
                '<td class="r pro-more">' + U.num(r.get("range_pos_252"), 0) + "</td>"
                '<td class="r pro-more">' + U.num(r.get("turnover_cr"), 1) + "</td>"
                '<td class="r pro-more">' + U.num(r.get("riskadj_pctile"), 0) + "</td></tr>")
    return out


def momentum(conn) -> str:
    rows = R.riskadj_scan(conn, limit=40)
    cols = [("#", "r"), ("Symbol", ""), ("6-month", "r"), ("12-month", "r"), ("Volatility", "r"),
            ("Move per unit of risk", "r"),
            ('<span class="pro-more">Position in 52w range</span>', "r pro-more"),
            ('<span class="pro-more">Turnover ₹cr</span>', "r pro-more"),
            ('<span class="pro-more">Percentile</span>', "r pro-more")]
    fence = C.fence(
        "A gross SELECTION lens, not skill. Attribution on this estate showed the momentum here is "
        "a known market-wide risk premium — the residual, the part that would be OUR edge, failed "
        "its significance test. Read it as a shortlist to research, never as a buy list.")
    if not rows:
        return (fence
                + C.empty("The momentum scan hasn't been computed on this host yet. This page reads "
                          "the stored scan and never fabricates a shortlist — check back after the "
                          "next nightly run.")
                + C.learn("Risk-adjusted momentum divides a stock's six-month return by how choppy "
                          "it has been. Two names up 40 percent are not the same trade if one got "
                          "there in a straight line and the other on a rollercoaster."))
    return (fence
            + U.table(cols, _momentum_rows(rows), height=420,
                      note="Six-month return divided by roughly three months of return volatility, "
                           "on split- and bonus-adjusted prices so a corporate action cannot fake a "
                           "move. As of " + C.esc(str(rows[0].get("as_of") or "—")) + ".")
            + C.pro_more('<p class="g-mnote">Pro adds where the price sits in its own 52-week '
                         "range, the traded turnover behind the move, and the percentile of the "
                         "risk-adjusted score — the three things that separate a real move from a "
                         "thin one.</p>")
            + C.learn("Momentum is the most-studied effect in equities and it is real — but it is a "
                      "known, published risk premium that anyone can buy. On this estate it is kept "
                      "as a shortlister for that reason: it narrows where to look, it does not tell "
                      "you what to own."))


# ── view: CAPTURE (ports /dash/capture-map) ───────────────────────────────────────────
_CAP_READ = {
    (True, True): ("All-weather", "joins the rises, gives back less of the falls"),
    (True, False): ("High-beta", "amplifies the market both ways"),
    (False, True): ("Defensive", "damped both ways — misses rallies, cushions falls"),
    (False, False): ("Worst of both", "lags the rises, takes more of the falls"),
}


def _cap_rows(rows) -> str:
    out = ""
    for r in rows:
        up, dn = r.get("up"), r.get("down")
        try:
            word, blurb = _CAP_READ[(float(up) >= 1.0, float(dn) < 1.0)]
        except (TypeError, ValueError):
            word, blurb = "—", ""
        out += ("<tr><td>" + C.esc(r.get("label")) + "</td>"
                '<td class="r">' + U.num(up, 2) + "</td>"
                '<td class="r">' + U.num(dn, 2) + "</td>"
                '<td class="r">' + U.signed(r.get("spread"), 2, "") + "</td>"
                '<td title="' + C.esc(blurb) + '">' + C.esc(word) + "</td></tr>")
    return out


def capture(conn, horizon: str = "63") -> str:
    h = horizon if horizon in R.HORIZONS else "63"
    rows, demo = R.capture_map(conn, horizon=h), False
    if not rows:
        rows, demo = R.DEMO_CAPTURE, True
    cols = [("Sector", ""), ("Took of the rises", "r"), ("Took of the falls", "r"),
            ("Difference", "r"), ("Read", "")]
    return (U.chips(sorted(R.HORIZONS.items(), key=lambda kv: int(kv[0])), h,
                    lambda k: U.STRENGTH_HREF + "?view=capture&h=" + k)
            + U.sample_note(demo, "the capture map")
            + C.fence("A behaviour track record over the past window, never a forward signal. "
                      "A sector that defended the last fall is not thereby defensive in the next "
                      "one.")
            + U.table(cols, _cap_rows(rows), height=380,
                      note="1.00 means it moved exactly with the market. Took-of-the-falls BELOW "
                           "1.00 is the defensive read; took-of-the-rises ABOVE 1.00 is the "
                           "participation read. The prize is high on the first and low on the "
                           "second — a diagonal two separate columns hide.")
            + C.learn("Averages hide this. Two sectors with the same yearly return can have got "
                      "there in opposite ways: one by capturing every rally and every crash, the "
                      "other by taking most of the upside and little of the downside. The "
                      "difference between the two columns is the whole point."))


# ── the page bodies ───────────────────────────────────────────────────────────────────
def body(conn, view: str = "overview", horizon: str = "63") -> str:
    v = view_of(view)
    if v == "leaders":
        inner = leaders(conn)
    elif v == "momentum":
        inner = momentum(conn)
    elif v == "capture":
        inner = capture(conn, horizon)
    else:
        inner = overview(conn)
    return C.zone("Relative strength", "NSE bhav copy + index history · nightly", head(v) + inner,
                  sub="is it beating the market, and what did that cost", name="Strength")


# ══ ROUTES — this lane's ONE router (three declared children of the Graphite home) ════
def _render(title: str, build) -> HTMLResponse:
    """Shared route shell: open a connection, build the body, never 500 (a heavy or edge read must
    degrade to an honest empty state, per the shipped rotation-route pattern)."""
    from src.web.home import shell
    body_html, pat = "", ""
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            body_html = build(conn)
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body_html = (C.fence("This board hasn't landed on this host yet.")
                     + C.empty("Check back after the next nightly run."))
    return HTMLResponse(shell.shell(title, body_html, current="Markets", pat_html=pat,
                                    extra_head=U.css()))


@router.get("/dash/home/strength", response_class=HTMLResponse, include_in_schema=False)
def strength(request: Request) -> HTMLResponse:
    """Relative strength — the RS hub, leaders/laggards, risk-adjusted momentum and the all-weather
    capture map as four URL-addressable views of one page."""
    v = view_of(request.query_params.get("view"))
    h = request.query_params.get("h") or "63"
    return _render("Relative strength", lambda c: body(c, v, h))


@router.get("/dash/home/sectors", response_class=HTMLResponse, include_in_schema=False)
def sectors(request: Request) -> HTMLResponse:
    """Sectors — the standing board (with constituent breadth and a per-sector drill-down) and the
    economics tab (what the businesses earn, and what the strength cost in risk)."""
    from src.web.home import sectors_pages as S
    t = S.tab_of(request.query_params.get("tab"))
    sec = (request.query_params.get("sec") or "").strip()[:60]
    met = (request.query_params.get("metric") or "roce").strip().lower()[:12]
    return _render("Sectors", lambda c: S.body(c, t, sec, met))
