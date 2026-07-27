"""src/web/home/sectors_pages.py — the Graphite "Sectors" page (W2-B), two tabs.

The classic estate had three sector surfaces: `/dash/sectors` (the standing board),
`/dash/sector-momentum` (the constituent drill-down, reachable only by deep link — an orphan) and
`/dash/sector-economics` (a decade of what the businesses actually earn). The first two are the same
board at two zoom levels, so they become ONE tab; the third is a genuinely different claim — the
BUSINESS underneath the price — so it becomes the second tab.

    /dash/home/sectors                      → Standing (board + breadth + drill-down)
    /dash/home/sectors?tab=economics        → Economics (what they earn · what the strength cost)
    /dash/home/sectors?sec=<sector>         → the drill-down, URL-addressable

Bodies only; the routes live in `strength_pages` (this lane's single router). Imports no classic
view module.
"""
from __future__ import annotations

from src.web.home import components as C
from src.web.home import markets_reads as R
from src.web.home import markets_ui as U

TABS = (("standing", "Standing"), ("economics", "Economics"))
_KEYS = {k for k, _ in TABS}

_FENCE = ("A sector weather map for context, never a sector call. Relative strength is measured "
          "against the broad market from NSE index history; the business figures are annual filings. "
          "Descriptive only.")


def tab_of(raw) -> str:
    t = str(raw or "").strip().lower()
    return t if t in _KEYS else "standing"


def head(tab: str) -> str:
    sub = ("which sectors are leading, how broad that leadership is inside them, and which names "
           "drive it") if tab == "standing" else (
        "what the companies in each sector actually earn — and what their relative strength has "
        "cost in risk")
    return (U.tabs(TABS, tab, U.SECTORS_HREF, "tab")
            + '<p class="g-mnote" style="margin:0 0 12px">' + C.esc(sub) + "</p>")


# ── tab: STANDING (ports /dash/sectors + /dash/sector-momentum) ───────────────────────
def _standing_rows(rows, breadth: dict) -> str:
    out = ""
    for r in rows:
        # `index_signals.index_name` and `stock_signals.primary_sector` are two vocabularies for the
        # same sector; match on the raw name, then on the short label. No match = no drill link
        # (degrade, never guess a join).
        name = r.get("index_name") or ""
        b = breadth.get(name) or breadth.get(r.get("label")) or {}
        drill = ""
        if b.get("sector"):
            drill = ('<a class="g-syma" href="' + C.safe_url(U.SECTORS_HREF + "?sec="
                     + str(b["sector"])) + '">' + C.esc(r.get("label")) + "</a>")
        else:
            drill = C.esc(r.get("label"))
        out += ("<tr><td>" + drill + "</td>"
                "<td>" + U.phase_pill(r.get("phase"), r.get("phase_label")) + "</td>"
                '<td class="r">' + U.signed(r.get("s1")) + "</td>"
                '<td class="r">' + U.signed(r.get("s3")) + "</td>"
                '<td class="r">' + U.signed(r.get("s12")) + "</td>"
                "<td>" + (U.bar(b.get("up_pct"), "up") + ' <b class="g-mnum">'
                          + U.num(b.get("up_pct"), 0) + "%</b>"
                          if b.get("up_pct") is not None else '<span class="g-mnum">—</span>')
                + "</td>"
                '<td class="r pro-more">' + U.signed(r.get("r1")) + "</td>"
                '<td class="r pro-more">' + U.signed(r.get("r3")) + "</td>"
                '<td class="r pro-more">' + U.num(b.get("avg_rank"), 0) + "</td></tr>")
    return out


def _drill(conn, sector: str) -> str:
    """The per-sector drill-down the classic estate hid behind a deep link: which names inside this
    sector actually carry its relative strength, and how broad that is."""
    rows = R.sector_members(conn, sector, limit=30)
    if not rows:
        return (U.head("Inside " + R._short(sector), "constituent detail")
                + C.empty("No ranked constituents on record for this sector yet — that needs the "
                          "nightly stock relative-strength pass."))
    body = ""
    for r in rows:
        body += ("<tr><td>" + U.sym(r.get("symbol")) + "</td>"
                 '<td class="r">' + U.num(r.get("rs_rank"), 0) + "</td>"
                 "<td>" + U.phase_pill(r.get("rs_phase"), R.phase_label(r.get("rs_phase"))) + "</td>"
                 '<td class="r">' + U.signed(r.get("rs_broad")) + "</td>"
                 '<td class="r">' + U.signed(r.get("rs_sector")) + "</td>"
                 '<td class="r pro-more">' + U.num(r.get("rsi"), 0) + "</td></tr>")
    hot = [r for r in rows if (r.get("rsi") or 0) >= 70]
    cold = [r for r in rows if r.get("rsi") is not None and r["rsi"] <= 30]
    cols = [("Symbol", ""), ("RS rank", "r"), ("Phase", ""), ("Versus market", "r"),
            ("Versus its sector", "r"), ('<span class="pro-more">RSI-of-RS</span>', "r pro-more")]
    return (U.head("Inside " + R._short(sector),
                   str(len(rows)) + " ranked names · strongest first")
            + U.table(cols, body, height=360,
                      note="“Versus its sector” is the honest second read: a name can beat the "
                           "market simply by sitting in the right sector. Beating the sector too is "
                           "the part that is about the company.")
            + C.pro_more('<p class="g-mnote">Pro adds RSI-of-RS per name — right now '
                         + str(len(hot)) + " of these look stretched on relative strength and "
                         + str(len(cold)) + " look washed out. Breadth like that is what separates "
                         "a sector move carried by two names from one carried by twenty.</p>")
            + '<p class="g-mnote"><a class="g-syma" href="' + C.safe_url(U.SECTORS_HREF)
            + '">← back to all sectors</a></p>')


def standing(conn, sector: str = "") -> str:
    rows, demo = R.sector_standing(conn), False
    if not rows:
        rows, demo = R.DEMO_WEATHER, True
    br = R.sector_breadth(conn)
    if not br:
        br = R.DEMO_BREADTH
    breadth = {}
    for b in br:
        breadth[b.get("sector")] = b
        breadth.setdefault(R._short(b.get("sector")), b)
    cols = [("Sector", ""), ("Weather", ""), ("1m RS", "r"), ("3m RS", "r"), ("12m RS", "r"),
            ("Members beating the market", ""),
            ('<span class="pro-more">1m return</span>', "r pro-more"),
            ('<span class="pro-more">3m return</span>', "r pro-more"),
            ('<span class="pro-more">Avg RS rank</span>', "r pro-more")]
    out = (U.sample_note(demo, "the sector standing")
           + U.table(cols, _standing_rows(rows, breadth), height=400,
                     note="Breadth is the cross-check on the headline: a sector can read strong on "
                          "two mega-caps while most of its members lag. Click a sector to see who "
                          "is actually carrying it.")
           + C.pro_more('<p class="g-mnote">Pro adds each sector\'s own price return beside its '
                        "relative strength, and the average relative-strength rank of its members "
                        "— the difference between “the index led” and “the companies led”.</p>"))
    if sector:
        out += _drill(conn, sector)
    return out + C.learn(
        "A sector's relative strength is its index measured against the broad market, so it answers "
        "“did money move here” — not “is this a good business”. The Economics tab answers the other "
        "half. Read them together: leadership on weak economics is a rotation; leadership on "
        "improving economics is a re-rating.")


# ── tab: ECONOMICS (ports /dash/sector-economics) ─────────────────────────────────────
def _heat(grid: dict) -> str:
    """A decade of each sector's median business economics. A compact grid, not a chart: the value
    is IN each cell (a colour alone is not evidence), the colour only ranks it."""
    years, sectors, matrix = grid.get("years") or [], grid.get("sectors") or [], grid.get("matrix") or []
    flat = [v for row in matrix for v in row if v is not None]
    if not flat:
        return ""
    lo, hi = min(flat), max(flat)
    span = (hi - lo) or 1.0
    head = '<th class="rw">Sector</th>' + "".join(
        "<th>FY" + C.esc(y[2:]) + "</th>" for y in years)
    body = ""
    for i, sec in enumerate(sectors):
        cells = ""
        for v in matrix[i]:
            if v is None:
                cells += '<td class="na" title="fewer than 5 tagged companies with a filing">·</td>'
            else:
                t = (float(v) - lo) / span
                cells += ('<td style="background:color-mix(in srgb,var(--accent) '
                          + U.num(6 + 44 * t, 0) + '%,transparent)">' + U.num(v, 1) + "</td>")
        body += ('<tr><th class="rwc">' + C.esc(R._short(sec)) + "</th>" + cells + "</tr>")
    return U.scroll('<table class="g-mheat"><thead><tr>' + head + "</tr></thead><tbody>"
                    + body + "</tbody></table>", 420)


def _risk_rows(rows) -> str:
    out = ""
    for r in rows:
        out += ("<tr><td>" + C.esc(r.get("label")) + "</td>"
                "<td>" + U.phase_pill(r.get("phase"), r.get("phase_label")) + "</td>"
                "<td>" + U.pos_strip(r.get("band"),
                                     "0 = at its own RS support · 100 = at its own RS resistance")
                + "</td>"
                '<td class="r">' + U.num(r.get("up"), 2) + "</td>"
                '<td class="r">' + U.num(r.get("down"), 2) + "</td>"
                '<td class="r">' + U.signed(r.get("spread"), 2, "") + "</td>"
                '<td class="pro-more">' + C.esc(r.get("read") or "—") + "</td></tr>")
    return out


def economics(conn, metric: str = "roce") -> str:
    m = metric if metric in R.FUND_METRICS else "roce"
    grid = R.sector_fundamentals(conn, m)
    risk, demo = R.sector_risk_economics(conn), False
    if not risk:
        risk, demo = [], True

    biz = (U.chips([(k, v[2].split("—")[0].strip()) for k, v in R.FUND_METRICS.items()], m,
                   lambda k: U.SECTORS_HREF + "?tab=economics&metric=" + k))
    if grid:
        biz += (_heat(grid)
                + '<p class="g-mnote">' + C.esc(grid.get("plain") or "")
                + ". Median of the companies tagged into each sector, per financial year; a cell is "
                  "blank where fewer than 5 of them filed that year.</p>"
                + C.fence(
                    "Read the coverage honestly. Survivorship: sectors are TODAY's index membership "
                    "applied backwards, so this is how today's constituents evolved, not how the "
                    "sector stood then. Thin and multi-label: a company can sit in two sectors, and "
                    "medians under 5 companies are left blank rather than guessed. Financials are "
                    "mostly blank by design — lenders are judged on return on equity, not return on "
                    "capital employed. Provenance: these fundamentals come from the pre-migration "
                    "archive and are being moved to NSE and BSE filings; treat them as provisional."))
    else:
        biz += (C.empty("The company-fundamentals archive isn't available on this host, so this half "
                        "is empty rather than illustrated. Business figures are never sampled — a "
                        "made-up margin for a real company would be indistinguishable from a real "
                        "one, and that is not a line worth blurring.")
                + '<p class="g-mnote">The relative-strength half below reads live and is unaffected.'
                  "</p>")

    riskcols = [("Sector", ""), ("Weather", ""), ("Strength in its own range", ""),
                ("Took of rises", "r"), ("Took of falls", "r"), ("Difference", "r"),
                ('<span class="pro-more">Read</span>', "pro-more")]
    riskblock = (U.head("What the strength cost", "position in its own range × how it behaved in "
                                                  "rises and falls")
                 + (U.table(riskcols, _risk_rows(risk), height=360,
                            note="One row per sector, joining the range position with the capture "
                                 "behaviour — the two things that say whether today's leadership "
                                 "was expensive.")
                    if risk else
                    C.empty("The relative-strength band and capture snapshots haven't landed on "
                            "this host yet — they arrive with the nightly run."))
                 + C.pro_more('<p class="g-mnote">Pro adds the plain read for each sector\'s '
                              "range-position and regime combination.</p>"))

    return (U.head("What the businesses earn", "a decade of annual filings, by sector")
            + biz + riskblock
            + C.learn("Two different questions share this tab. What a sector EARNS moves over years "
                      "and comes from company filings. What its relative strength COST is a market "
                      "read that changes weekly. Neither predicts the other — but a sector leading "
                      "the market while its economics deteriorate is a very different story from "
                      "one leading while they improve."))


# ── the page body ─────────────────────────────────────────────────────────────────────
def body(conn, tab: str = "standing", sector: str = "", metric: str = "roce") -> str:
    t = tab_of(tab)
    inner = economics(conn, metric) if t == "economics" else standing(conn, sector)
    return C.zone("Sectors", "NSE index history + annual filings · nightly",
                  C.fence(_FENCE) + head(t) + inner,
                  sub="who is leading, how broadly, and on what economics", name="Sectors")
