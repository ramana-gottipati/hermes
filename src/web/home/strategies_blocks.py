"""src/web/home/strategies_blocks.py — the Strategies-workspace render kit (Graphite, lane W3-A).

HTML only, never sqlite — the mirror of `strategies_reads.py`, exactly as `components.py` mirrors
`reads.py`. Every function is a pure `(rows) -> html str` and composes the SHARED `.g-*` atoms from
`components.py` (zone · card · tile · empty · fence · learn · term_chip · ref_chip · pro_more ·
pro_teaser · sym_link · prov), so the workspace inherits the Graphite identity for free and adds no
second design system.

Two doctrines are enforced *in this file* because they are what makes these pages honest:
  • **Fences travel with their surface.** Every recorded verdict (D138 scope gap · D141 rejection ·
    D62 descriptor-only · CCI Gate-B failure · launchpad's no-fundable-edge · conviction's sorting
    heuristic · the Screener.in provenance exception) is rendered, ABOVE the numbers it qualifies —
    never softened, never demoted to a footnote.
  • **Link, don't restate.** Measured verdict numbers live in `docs/strategy-ledger.md` and the
    engine tables; pages link them (`/dash/strategy-ref`, `/dash/testing`) instead of hard-coding a
    second copy that can silently go stale.
"""
from __future__ import annotations

from src.web.home import components as C

# ── local atoms ────────────────────────────────────────────────────────────────

REF = "/dash/strategy-ref"
LEDGER = "/dash/testing"

# The Graphite stock page (built in parallel by lane W1 at /dash/home/stock). We link the ROUTE and
# import nothing from it — a lane-owned twin of `components.sym_link`, which still points at the
# classic `/dash/stock` because that atom is shared with the pre-cutover home. Kept local so this
# workspace can adopt the new dossier without touching a shared file.
STOCK = "/dash/home/stock?sym="


def sym(symbol) -> str:
    s = C.esc(symbol)
    return '<a class="g-syma" href="' + STOCK + s + '">' + s + "</a>"


def _n(v, dp: int = 2, suf: str = "") -> str:
    try:
        return f"{float(v):,.{dp}f}" + suf
    except (TypeError, ValueError):
        return "—"


def _pct(v, dp: int = 1) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return ("+" if f > 0 else "") + f"{f:,.{dp}f}%"


def _cr(v) -> str:
    """Rupees, rendered at the scale a reader in India actually uses (crore)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return "₹" + f"{f / 1e7:,.2f}" + " cr"


def _signed(v, dp: int = 1, suf: str = "%") -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '<span class="g-num">—</span>'
    cls = "up" if f >= 0 else "dn"
    return ('<span class="g-num ' + cls + '">' + ("▲" if f >= 0 else "▼") + " "
            + f"{abs(f):,.{dp}f}" + C.esc(suf) + "</span>")


def table(headers, rows_html: str, cls: str = "") -> str:
    """A fixed-height, INTERNALLY scrolling table (standing correction #3 — never an endless page)."""
    th = "".join("<th>" + C.esc(h) + "</th>" for h in headers)
    return ('<div class="g-scroll"><table class="g-tbl"><thead><tr>' + th + "</tr></thead><tbody>"
            + (rows_html or '<tr><td colspan="' + str(len(headers))
               + '" class="g-empty">Nothing to show yet.</td></tr>') + "</tbody></table></div>")


def ref_link(page: str, label: str = "Methodology") -> str:
    if not page:
        return ""
    return ('<a class="g-more" href="' + REF + "?p=" + C.esc(page) + '">' + C.esc(label) + " →</a>")


def tabs(items, active: str, base: str, param: str = "tab") -> str:
    """A server-rendered tab strip — URL-addressable state (playbook 8b), no client framework."""
    out = ['<nav class="g-tabs" aria-label="Views">']
    for key, label in items:
        href = base + (("?" + param + "=" + key) if key else "")
        cur = ' aria-current="page"' if (key or "") == (active or "") else ""
        out.append('<a href="' + C.esc(href) + '"' + cur + ">" + C.esc(label) + "</a>")
    out.append("</nav>")
    return "".join(out)


def crumb(label: str) -> str:
    return ('<p class="g-crumb"><a href="/dash/home">Today</a> › '
            '<a href="/dash/home/strategies">Strategies</a> › <b>' + C.esc(label) + "</b></p>")


def verdict(text: str, tone: str = "warn") -> str:
    """A RECORDED VERDICT box. Rendered ABOVE the stat it qualifies — the scope-gap rule."""
    return '<div class="g-verdict ' + C.esc(tone) + '">' + text + "</div>"


# ── the hub ────────────────────────────────────────────────────────────────────

PAGES = (
    ("books", "Model portfolios", "Four engine-locked books, rebuilt by rule since 2012."),
    ("sector-rotation", "Sector rotation", "A monthly sector-index book — sectors, not stocks."),
    ("library", "Strategy library", "Every strategy we run, filtered by who created it."),
    ("positioning", "Positioning & stealth", "Where delivery money is sitting, and what is quiet."),
    ("conviction", "Conviction shortlist", "Names clearing strength, positioning and quality."),
    ("mep", "Accumulation & distribution", "The signed pressure tape."),
    ("credibility", "Management credibility", "Promises made on calls, and whether they landed."),
    ("growth", "Growth intent", "What management said it will spend and build."),
    ("ownership", "Ownership & filings", "Insiders, credit ratings, stakes, pledges, holdings."),
    ("launchpad", "Launchpad", "A validated setup screen and its published track record."),
)

_HUB_FENCE = ("A research map — descriptive only. Nothing here is a buy or sell call, and no page "
              "ranks stocks by an expected return.")


def hub(cat: list, asof: dict, sample: bool = False) -> str:
    tiles = "".join([
        C.tile("Strategies tracked", str(len([c for c in cat if c])) or "—", "from the registry"),
        C.tile("Listed universe", _n(asof.get("universe"), 0), "NSE cash symbols"),
        C.tile("Prices to", C.esc(asof.get("bhav") or "—"), "bhav copy"),
        C.tile("Signals to", C.esc(asof.get("signals") or "—"), "nightly compute"),
    ])
    dirq = "".join(
        '<a class="g-dcard" href="/dash/home/strategies/' + C.esc(k) + '"><b>' + C.esc(lab)
        + "</b><span>" + C.esc(sub) + "</span></a>" for k, lab, sub in PAGES)
    cards = ""
    for c in cat:
        if not isinstance(c, dict):
            continue
        n, lab = c.get("count"), c.get("label") or c.get("key")
        cards += ('<div class="g-card"><div class="g-card-h">' + C.esc(lab) + "</div>"
                  '<p class="g-num g-big">' + (_n(n, 0) if n is not None else "—") + "</p>"
                  '<p class="g-sub">' + C.esc(c.get("as_of") or "no date") + " · "
                  + C.esc(c.get("health") or "") + "</p></div>")
    honest = verdict(
        "<b>The honest headline, first.</b> Sixteen strategies are tracked here and most of them are "
        "<b>descriptive</b> — they describe what already happened. Exactly one result in this whole "
        "estate survived realistic costs: the quarterly large-cap low-volatility × momentum book "
        "(STEADY-25). Everything else is either a gross-of-cost demonstration, a context layer, or a "
        "recorded failure that we publish on purpose. "
        '<a class="g-more" href="' + LEDGER + '">See the validation record →</a>', "warn")
    origins = ('<p class="g-legend">Who made it: '
               + " ".join('<span class="g-chip">' + g + " " + C.esc(lab) + "</span>"
                          for _k, g, lab in (("ramana", "\U0001F9D1", "Ramana's idea"),
                                             ("house", "\U0001F3E0", "Built in-house"),
                                             ("classic", "\U0001F4DA", "Public/classic")))
               + ' <a class="g-more" href="/dash/home/strategies/library">Filter the library →</a></p>')
    return (C.fence(_HUB_FENCE) + honest
            + C.zone("Strategies", "strategy_registry", '<div class="g-tiles">' + tiles + "</div>"
                     + origins + '<div class="g-dgrid">' + dirq + "</div>",
                     sub="every strategy surface, one place", sample=sample)
            + C.zone("Health of each strategy", "strategy_registry · nightly",
                     C.learn("Each card shows how many names the strategy has today and how fresh "
                             "the data behind it is. A stale card means the overnight job has not "
                             "run, not that the strategy changed.")
                     + '<div class="g-cards">' + (cards or C.empty("The registry has not reported yet."))
                     + "</div>", sample=sample))


# ── model portfolios ───────────────────────────────────────────────────────────

_RETVOL_NOTE = ("Return / volatility ratio — <b>not a Sharpe ratio</b>: no risk-free rate is "
                "subtracted and costs are modelled flat.")


def books(spec: dict, stats: dict, nav: list, holds: list, churn: list, book: str,
          all_books: list, sample: bool = False, hold_date=None) -> str:
    chip = spec.get("chip") or ""
    banner = verdict(
        "<b>✅ Fundable core.</b> This is the only book in the estate that still stands up once "
        "realistic trading costs are paid, at a size an individual can actually run. Every other "
        "book below is a <b>gross-of-cost demonstration</b> of a rule, not a fundable plan. "
        '<a class="g-more" href="' + LEDGER + '">The costing record →</a>', "ok") \
        if chip == "FUNDABLE-CORE" else verdict(
        "<b>⚠ Gross-lens demonstration.</b> These numbers are before real trading costs. The rule is "
        "real and frozen; the <i>returns</i> are an upper bound, not something you could have kept. "
        '<a class="g-more" href="' + LEDGER + '">The costing record →</a>', "warn")

    seg = "".join('<a class="g-seg-a' + (" on" if b["book"] == book else "") + '" href="'
                  '/dash/home/strategies/books?book=' + C.esc(b["book"]) + '">' + C.esc(b["book"])
                  + "</a>" for b in all_books)

    bk, bn = (stats.get("book") or {}), (stats.get("bench") or {})
    st = "".join([
        C.tile("Growth of ₹1", (_n(bk.get("mult"), 2) + "×") if bk.get("mult") else "—",
               "since " + C.esc(stats.get("start") or "—")),
        C.tile("Per year", _pct(bk.get("cagr")), "Nifty 500: " + _pct(bn.get("cagr"))),
        C.tile("Return / volatility", _n(bk.get("retvol"), 2), "not a Sharpe ratio"),
        C.tile("Worst fall", _pct(bk.get("maxdd")), "peak to trough"),
    ])

    hrows = ""
    for h in holds:
        hrows += ("<tr><td>" + sym(h.get("symbol")) + "</td><td>"
                  + C.esc(h.get("sector") or "—") + "</td><td class='g-num'>"
                  + _n(h.get("cmp")) + "</td><td class='g-num'>" + _n(h.get("w_target"), 1)
                  + "%</td><td class='g-num'>" + _n(h.get("w_now"), 1) + "%</td><td>"
                  + _signed(h.get("since")) + "</td><td class='g-num'>" + _n(h.get("score"), 2)
                  + "</td></tr>")
    hold_tbl = table(("Symbol", "Sector", "Price", "Target weight", "Weight now", "Since rebalance",
                      "Score"), hrows)

    crows = "".join("<tr><td>" + C.esc(c.get("date")) + "</td><td>"
                    + (", ".join(sym(s) for s in c.get("in", [])[:8]) or "—")
                    + "</td><td>" + (", ".join(sym(s) for s in c.get("out", [])[:8]) or "—")
                    + "</td></tr>" for c in churn)

    prov = "auto_portfolio_nav · " + C.esc(stats.get("end") or "—")
    return (crumb("Model portfolios") + banner
            + C.zone(C.esc(book), prov,
                     '<p class="g-sub">' + C.esc(spec.get("rule") or "") + " · <b>"
                     + C.esc(spec.get("profile") or "") + "</b> · " + C.esc(spec.get("origin") or "")
                     + " classic formula</p>"
                     + '<div class="g-segbar">' + seg + "</div>"
                     + '<div class="g-tiles">' + st + "</div>"
                     + spark_pair(nav, "nav", "bench_nav", "rebal_date")
                     + '<p class="g-note">' + _RETVOL_NOTE + " History is a reconstruction: the same "
                     "frozen rule applied point-in-time, with no hand edits, ever.</p>"
                     + C.pro_more('<p class="g-note">Reference depth: the ~70-column evidence pool '
                                  "(fundamentals, key-price, F&amp;O families) attaches to this "
                                  "table at cutover. Columns are never paywalled — evidence is free; "
                                  "only convenience can ever be premium.</p>"),
                     sub=C.esc(spec.get("profile") or ""), sample=sample)
            + C.zone("What the book holds", "auto_portfolio_holdings · " + C.esc(hold_date or "—"),
                     C.learn("The first four columns never change on any book — symbol, sector, "
                             "price and how it has done since the last rebalance. That is the spine; "
                             "the rest are the columns this particular book's reader checks.")
                     + hold_tbl, sample=sample)
            + C.zone("Rebalance ledger", "auto_portfolio_holdings",
                     C.learn("Every change the rule made, in the order it made them. Nothing is "
                             "back-edited — that is what makes the record checkable.")
                     + table(("Rebalanced", "Bought in", "Sold out"), crows), sample=sample)
            + C.fence("Descriptive record of a rule, not investment advice. Past reconstruction is "
                      "not a promise about the future."))


def spark_pair(rows: list, a: str, b: str, xkey: str) -> str:
    """Two normalised lines (book vs benchmark) as one small inline SVG — no chart library."""
    xs = [r for r in rows if r.get(a) is not None]
    if len(xs) < 2:
        return C.empty("Not enough history to plot yet.")
    va = [float(r[a]) for r in xs]
    vb = [float(r[b]) for r in xs if r.get(b) is not None]
    lo = min(va + (vb or va))
    hi = max(va + (vb or va))
    rng = (hi - lo) or 1.0
    w, h = 640, 130

    def path(vals):
        n = len(vals)
        return " ".join(("M" if i == 0 else "L") + f"{i * w / max(1, n - 1):.1f},"
                        f"{h - ((v - lo) / rng) * (h - 8) - 4:.1f}" for i, v in enumerate(vals))
    bench = ('<path d="' + path(vb) + '" fill="none" stroke="var(--ink-3)" stroke-width="1.6" '
             'stroke-dasharray="4 3"/>') if len(vb) >= 2 else ""
    return ('<figure class="g-spark2"><svg viewBox="0 0 ' + str(w) + " " + str(h) + '" '
            'preserveAspectRatio="none" role="img" aria-label="Book value against the Nifty 500">'
            + bench + '<path d="' + path(va) + '" fill="none" stroke="var(--accent)" '
            'stroke-width="2.1"/></svg><figcaption class="g-sub">Solid = the book · dashed = '
            'Nifty 500 · ' + C.esc(str(xs[0].get(xkey))) + " → " + C.esc(str(xs[-1].get(xkey)))
            + "</figcaption></figure>")


# ── sector rotation ────────────────────────────────────────────────────────────

_D138 = ("<b>🔴 Read this before the numbers.</b> This book picks <b>SECTORS, not STOCKS</b>. It "
         "holds sector <i>indices</i> — so a headline return here says nothing about which shares "
         "to own, and there is no liquid index instrument for several of these legs even though "
         "every leg is costed as if there were. The follow-on idea — use the sector call to pick "
         "stocks inside it — was <b>built, simulated and rejected</b> at realistic cost. Treat every "
         "figure below as an upper bound on a paper portfolio.")


def rotation(book: dict, diff: dict, stats: dict, sample: bool = False) -> str:
    ws = book.get("weights") or []
    tot = sum(float(w.get("weight") or 0) for w in ws) or 1.0
    bars = "".join(
        '<div class="g-bar"><span class="g-bl">' + C.esc(w.get("sector")) + '</span>'
        '<span class="g-bt"><i style="width:' + f"{min(100.0, float(w.get('weight') or 0) / tot * 100):.1f}"
        + '%"></i></span><span class="g-num">'
        + _n((float(w.get("weight") or 0) / tot) * 100, 1) + "%</span></div>" for w in ws)
    d = ("<p><b>Entered:</b> " + (", ".join(C.esc(x) for x in diff.get("entered", [])) or "—")
         + "</p><p><b>Exited:</b> " + (", ".join(C.esc(x) for x in diff.get("exited", [])) or "—")
         + "</p><p><b>Re-weighted:</b> "
         + (", ".join(C.esc(k) + " " + _signed(v * 100, 1, "pp") for k, v in diff.get("moved", [])[:8])
            or "—")
         + "</p><p><b>Turnover this rebalance:</b> " + _n(diff.get("turnover", 0) * 100, 1) + "%</p>")
    bk, bn = (stats.get("book") or {}), (stats.get("bench") or {})
    st = "".join([
        C.tile("Growth of ₹1", (_n(bk.get("mult"), 2) + "×") if bk.get("mult") else "—", "the book"),
        C.tile("Per year", _pct(bk.get("cagr")), "Nifty 500: " + _pct(bn.get("cagr"))),
        C.tile("Return / volatility", _n(bk.get("retvol"), 2), "not a Sharpe ratio"),
        C.tile("Worst fall", _pct(bk.get("maxdd")), "peak to trough"),
    ])
    return (crumb("Sector rotation") + verdict(_D138, "warn")
            + C.zone("Sector rotation", "sector_rotation_book · " + C.esc(book.get("asof") or "—"),
                     '<div class="g-tiles">' + st + "</div>"
                     + spark_pair(book.get("nav") or [], "nav", "nav_bench", "month_date")
                     + '<p class="g-note">' + _RETVOL_NOTE + " Research-stage and conditional: the "
                     "sector layer only, with no stock selection. " + ref_link("sector-rotation")
                     + "</p>", sub="the V21 book", sample=sample)
            + C.zone("What it holds now", "sector_rotation_book",
                     C.learn("Each bar is how much of the book sits in that sector index. The "
                             "residual sleeve is the part deliberately left un-invested when the "
                             "regime filter is off.") + '<div class="g-bars">' + bars + "</div>",
                     sample=sample)
            + C.zone("How this rebalance happened", "sector_rotation_book", d, sample=sample)
            + C.fence("Descriptive research record, not advice, and not a stock recommendation."))


# ── strategy library ───────────────────────────────────────────────────────────

_ORIGIN_GLYPH = {"ramana": "\U0001F9D1", "house": "\U0001F3E0", "classic": "\U0001F4DA"}
_ORIGIN_WORD = {"ramana": "Ramana's idea", "house": "Built in-house", "classic": "Public / classic"}


def library(rows: list, origin: str, classics: list, sample: bool = False) -> str:
    chips = tabs((("", "All"), ("ramana", "\U0001F9D1 Ramana"), ("house", "\U0001F3E0 House"),
                  ("classic", "\U0001F4DA Classic")), origin,
                 "/dash/home/strategies/library", "origin")
    body = ""
    for r in rows:
        body += ("<tr><td><a href=\"" + C.safe_url(r.get("route") or "#") + "\">"
                 + C.esc(r.get("label")) + "</a></td><td>"
                 + _ORIGIN_GLYPH.get(r.get("origin"), "") + " "
                 + C.esc(_ORIGIN_WORD.get(r.get("origin"), "")) + "</td><td>"
                 + C.esc(r.get("blurb") or "") + "</td><td class='g-num'>"
                 + (("<a href='/dash/home/strategies/library?s=" + C.esc(r.get("key")) + "'>"
                     + _n(r.get("n"), 0) + "</a>") if r.get("n") is not None else "—")
                 + "</td><td>" + (ref_link(r.get("ref"), "Reference") or "—") + "</td></tr>")
    crows = "".join("<tr><td><a href='/dash/home/strategies/library?s=" + C.esc(c.get("key"))
                    + "'>" + C.esc(c.get("label")) + "</a></td><td class='g-num'>"
                    + (_n(c.get("n"), 0) if c.get("n") is not None else "—") + "</td><td>"
                    + C.esc(c.get("as_of") or "—") + "</td></tr>" for c in classics)
    return (crumb("Strategy library")
            + C.zone("Strategy library", "lens registry · docs/strategies",
                     C.learn("Three kinds of strategy live here. 🧑 means Ramana thought of it. 🏠 "
                             "means we designed it in-house. 📚 means it is a public, textbook idea "
                             "that we re-tested on our own data before admitting it — including the "
                             "ones that failed, which stay on the list with their numbers.")
                     + chips
                     + table(("Strategy", "Who made it", "What it does", "Names today", "Reference"),
                             body)
                     + '<p class="g-note">Measured verdicts — returns, drawdowns, whether a family '
                     'passed or failed — live in the validation record and each strategy\'s own '
                     'reference page, so there is exactly one copy of every number. '
                     '<a class="g-more" href="' + LEDGER + '">Validation record →</a></p>',
                     sub="factor families and classic screens, merged", sample=sample)
            + C.zone("Classic screens on our data", "classic_roster",
                     C.learn("Famous published screens, re-run point-in-time on our own exchange "
                             "data. Where we cannot reproduce a rule exactly we say so and label it "
                             "a proxy — never silently substituted.")
                     + table(("Screen", "Names", "As of"), crows), sample=sample))


def classic_detail(key: str, label: str, roster: list, nav: list, sample: bool = False,
                   show_nav: bool = True, prov: str = "classic_roster") -> str:
    rows = "".join("<tr><td class='g-num'>" + _n(r.get("rank"), 0) + "</td><td>"
                   + sym(r.get("symbol")) + "</td><td>" + C.esc(r.get("sector") or "—")
                   + "</td><td class='g-num'>" + _n(r.get("cmp")) + "</td><td class='g-num'>"
                   + _n(r.get("score"), 2) + "</td></tr>" for r in roster)
    warn = ""
    if show_nav and len(nav) < 10:
        # MIN_YEARS discipline: too few rebalances is NOT a track record, and we say so instead of
        # drawing a flattering line through three points.
        warn = verdict("<b>Insufficient history — not a track record.</b> There are too few "
                       "rebalances here to plot anything you should trust, so we deliberately do "
                       "not draw a performance line.", "warn")
    return (C.zone(C.esc(label), prov,
                   warn + (spark_pair(nav, "nav", "bench_nav", "rebal_date")
                           if (show_nav and len(nav) >= 10) else "")
                   + table(("#", "Symbol", "Sector", "Price", "Score"), rows)
                   + '<p class="g-note">A reconstructed study, not a record of money. This roster '
                     'is shown as research, not a buy list.</p>', sample=sample))


# ── positioning + stealth ──────────────────────────────────────────────────────

_CHAR = {"ACCUMULATION": ("🟢", "accumulating"), "DISTRIBUTION": ("🔴", "distributing"),
         "NEUTRAL": ("🟡", "neutral")}


def positioning(rows: list, stealth: bool, asof, sample: bool = False) -> str:
    body = ""
    for r in rows:
        g, w = _CHAR.get(str(r.get("accum_character") or ""), ("", "—"))
        body += ("<tr><td>" + sym(r.get("symbol")) + "</td><td class='g-num'>"
                 + _n(r.get("trigger_rank"), 0) + "</td><td class='g-num'>"
                 + _n(r.get("r_score"), 0) + "/" + _n(r.get("p_score"), 0) + "</td><td class='g-num'>"
                 + _n(r.get("ratio_today_vs_power_1m"), 2) + "×</td><td class='g-num'>"
                 + _n(r.get("cmp")) + "</td><td>" + g + " " + C.esc(w) + "</td><td class='g-num'>"
                 + _cr(r.get("delivery_value_per_trade")) + "</td><td class='g-num'>"
                 + _n(r.get("rs_rank"), 0) + "</td><td>" + _signed(r.get("pct_from_52w_high"))
                 + "</td><td>" + _signed(r.get("gap_to_key_p3m")) + "</td></tr>")
    heads = ("Symbol", "Trigger rank", "Strength / positioning", "vs its own peak day", "Price",
             "Behaviour", "Delivery per trade", "Strength rank", "Off 52-week high", "Gap to key price")
    fence = ("A watch-idea list to investigate, never a buy list." if stealth
             else "Descriptive positioning — a description of where delivery money is sitting, not a signal.")
    seg = tabs((("", "All names"), ("stealth", "🕵 Stealth only")), "stealth" if stealth else "",
               "/dash/home/strategies/positioning", "view")
    learn_txt = ("Stealth means the quiet corner of the same tape: names being accumulated on "
                 "shrinking trade counts while still well below their 52-week high — bought "
                 "patiently rather than chased." if stealth else
                 "Delivery value per trade is the average rupee size of the trades that actually "
                 "settled. Big, persistent ticket sizes are the footprint of size; the columns "
                 "compare today against this stock's own busiest past days, never against other stocks.")
    return (crumb("Positioning" + (" · stealth" if stealth else ""))
            + C.zone("🕵 Stealth accumulation" if stealth else "Positioning",
                     "stock_signals · " + C.esc(asof or "—"),
                     seg + C.learn(learn_txt) + table(heads, body)
                     + C.pro_teaser('<p class="g-note">Pro depth: this stock vs <b>its own</b> '
                                    "one-month turnover surge and delivery share, the extra "
                                    "positioning columns, and rank-change history.</p>",
                                    "Reference depth — see how unusual today is for this name",
                                    advertise=True),
                     sample=sample)
            + C.fence(fence))


# ── conviction ─────────────────────────────────────────────────────────────────

_CONV_CHIP = ("<b>A sorting heuristic, not a validated model.</b> This list is a synthesis of three "
              "descriptive pillars — relative strength, positioning behaviour and quality. It has "
              "never been shown to predict returns, and it is not ranked by expected return. Study "
              "it first; do not trade it.")

_PT14_DISCLOSURE = ("<b>Source note.</b> The Quality column is scored from our historical "
                    "fundamentals archive, which was originally collected from Screener.in — the "
                    "one known non-primary source in the system, frozen and being migrated to "
                    "BSE/NSE XBRL filings. It is read here, never extended.")


def conviction(rows: list, sample: bool = False) -> str:
    near = sum(1 for r in rows if (r.get("gap_to_key_p3m") is not None
                                   and abs(float(r.get("gap_to_key_p3m") or 99)) <= 3))
    qual = sum(1 for r in rows if r.get("pt14_tier"))
    tiles = "".join([C.tile("Names clearing all three", str(len(rows)), "today"),
                     C.tile("Near the key price", str(near), "within 3%"),
                     C.tile("Quality confirmed", str(qual), "pt14 tier present")])
    body = ""
    for r in rows:
        dq = r.get("pt14_dq")
        body += ("<tr><td>" + sym(r.get("symbol")) + "</td><td class='g-num'>"
                 + _n(r.get("rs_rank"), 0) + "</td><td>" + C.esc(r.get("primary_sector") or "—")
                 + "</td><td>" + C.esc(str(r.get("accum_character") or "—").title())
                 + "</td><td class='g-num'>" + _n(r.get("key_price_p3m")) + "</td><td>"
                 + _signed(r.get("gap_to_key_p3m")) + "</td><td class='g-num'>"
                 + _n(r.get("trigger_rank"), 0) + " · " + _n(r.get("p_score"), 0)
                 + "</td><td>" + ("✗ " if dq else "") + C.esc(r.get("pt14_tier") or "—")
                 + "</td></tr>")
    return (crumb("Conviction") + verdict(_CONV_CHIP, "warn")
            + C.zone("Conviction shortlist", "stock_signals ⋈ pattern_scores",
                     '<div class="g-tiles">' + tiles + "</div>"
                     + C.learn("Three separate reads have to agree before a name appears: it is "
                               "outperforming both its sector and the market, delivery behaviour "
                               "looks like accumulation, and the durability patterns do not "
                               "disqualify it. Most days almost nothing clears all three — that is "
                               "the point, not a bug.")
                     + table(("Symbol", "Strength rank", "Sector", "Behaviour", "Key price (3m)",
                              "Gap to key", "Trigger · positioning", "Quality"), body)
                     + '<p class="g-note">' + _PT14_DISCLOSURE + "</p>", sample=sample)
            + C.fence("A synthesis to study first, not a buy list. Conviction is rare by design."))


# ── MEP ────────────────────────────────────────────────────────────────────────

_MEP_FENCE = ("<b>Descriptor only — never a ranker.</b> The predictive version of this measure was "
              "tested and failed its gate, so it is published as a description of behaviour and "
              "nothing else. It never orders a buy list.")

_MEP_WORD = {"STRONG_ACCUM": "Strong accumulation", "ACCUM": "Accumulating",
             "NEUTRAL": "Consolidating", "DISTRIB": "Distributing",
             "STRONG_DISTRIB": "Strong distribution"}


def mep(rows: list, counts: dict, asof, direction: str = "", sample: bool = False) -> str:
    tiles = "".join(C.count_tile(counts.get(k, 0), lab, warn=k.endswith("DISTRIB"))
                    for k, lab in (("STRONG_ACCUM", "Strong accumulation"),
                                   ("ACCUM", "Accumulating"), ("NEUTRAL", "Consolidating"),
                                   ("DISTRIB", "Distributing"),
                                   ("STRONG_DISTRIB", "Strong distribution")))
    show = [r for r in rows
            if not direction
            or (direction == "up" and str(r.get("mep_state_smooth") or "").endswith("ACCUM"))
            or (direction == "dn" and str(r.get("mep_state_smooth") or "").endswith("DISTRIB"))]
    body = ""
    for r in show:
        s = float(r.get("mep_score_smooth") or 0)
        pos = max(0.0, min(100.0, (s + 1.0) * 50.0))
        body += ("<tr><td>" + sym(r.get("symbol")) + "</td><td class='g-num'>"
                 + _n(r.get("cmp")) + "</td><td><span class='g-adbar'><i style='left:"
                 + f"{pos:.1f}" + "%'></i></span></td><td>"
                 + C.esc(_MEP_WORD.get(str(r.get("mep_state_smooth")), "—")) + "</td><td>"
                 + _signed(s, 2, "") + "</td><td class='g-num'>" + _n(r.get("pressure"), 2)
                 + "</td><td class='g-num'>" + _n(r.get("clv"), 2) + "</td><td class='g-num'>"
                 + _n(r.get("drift_22d"), 3) + "</td><td class='g-num'>"
                 + _n(r.get("updown_vol_22d"), 2) + "</td><td class='g-num'>"
                 + _n(r.get("compression"), 2) + "</td></tr>")
    return (crumb("Accumulation & distribution") + verdict(_MEP_FENCE, "warn")
            + C.zone("Accumulation & distribution", "mep_signals · " + C.esc(asof or "—"),
                     '<div class="g-counts">' + tiles + "</div>"
                     + tabs((("", "All"), ("up", "📈 Accumulating"), ("dn", "📉 Distributing")),
                            direction, "/dash/home/strategies/mep", "dir")
                     + C.learn("This reads the side of the tape that delivery size alone cannot "
                               "see: where in its daily range a stock closes, whether volume "
                               "expands on up days or down days, and how tightly it is coiling. "
                               "Smoothed over fifteen sessions so one odd day cannot flip a phase.")
                     + table(("Symbol", "Price", "Accumulation ↔ distribution", "Phase", "Score",
                              "Pressure", "Close location", "Drift", "Up/down volume", "Compression"),
                             body)
                     + '<p class="g-note">' + ref_link("mep") + "</p>", sample=sample))


# ── credibility (CCI) ──────────────────────────────────────────────────────────

_CCI_FENCE = ("<b>Descriptive only — never ranked.</b> As a return factor this was tested "
              "leak-free and <b>failed</b>. What survives is a promise-keeping record and a "
              "deterioration veto: it can tell you a management has missed what it said, it cannot "
              "tell you what the share will do. The table is ordered by how much evidence each name "
              "has (most settled promises first), deliberately NOT by score.")

_CORPUS_NOTE = ("<b>Source note.</b> Roughly 98.6% of the call transcripts behind this page were "
                "originally <i>discovered</i> through Screener.in links — a frozen legacy path, "
                "with a BSE-primary migration in progress. Disclosed here because everything else "
                "on this site comes from exchange primary sources.")


def credibility(rows: list, counts: dict, asof, fingerprint: list = None, focus: str = "",
                sample: bool = False) -> str:
    tiles = "".join([C.count_tile(counts.get("proven", 0), "With settled promises"),
                     C.count_tile(counts.get("unproven", 0), "Not yet proven"),
                     C.count_tile(counts.get("vetoed", 0), "Under deterioration veto", warn=True),
                     C.count_tile(counts.get("scored", 0), "Scored in total")])
    body = ""
    for r in rows:
        body += ("<tr><td>" + sym(r.get("symbol")) + "</td><td>"
                 + C.esc(r.get("tier") or "—") + "</td><td class='g-num'>"
                 + _n(r.get("composite_score"), 1) + "</td><td>"
                 + C.esc(r.get("forward_direction") or "—") + "</td><td>"
                 + ("⛔ " + C.esc(r.get("veto_reason") or "veto") if r.get("veto_active") else "—")
                 + "</td><td class='g-num'>" + _n(r.get("guidance_accuracy_score"), 0) + " ("
                 + _n(r.get("n_promises_resolved"), 0) + ")</td><td class='g-num'>"
                 + _n((r.get("quantification_rate") or 0) * 100, 0) + "%</td><td>"
                 + C.esc(r.get("as_of_period") or "—") + "</td><td class='g-num'>"
                 + _n(r.get("n_concalls"), 0) + "</td><td><a href='/dash/home/strategies/credibility?sym="
                 + C.esc(r.get("symbol")) + "'>Track record</a></td></tr>")
    fp = ""
    if focus:
        frows = "".join("<tr><td>" + C.esc(g.get("source_period") or "—") + "</td><td>"
                        + C.esc(g.get("resolved_period") or "pending") + "</td><td>"
                        + C.esc(g.get("statement_type") or "—") + "</td><td>"
                        + C.esc(g.get("status") or "—") + "</td><td>"
                        + _signed(g.get("variance_pct")) + "</td><td>"
                        + C.esc((g.get("claim_text") or "")[:180]) + "</td></tr>"
                        for g in (fingerprint or []))
        fp = C.zone(C.esc(focus) + " — promise vs delivery", "concall_guidance",
                    C.learn("Each row is something management committed to on a call, and what "
                            "actually happened when the period closed. A negative variance means "
                            "they fell short of their own number.")
                    + table(("Said in", "Settled in", "Kind", "Outcome", "Variance", "What was said"),
                            frows)
                    + '<p class="g-note">A descriptive track record — not a forward signal.</p>',
                    sample=sample)
    return (crumb("Management credibility") + verdict(_CCI_FENCE, "warn")
            + C.zone("Management credibility", "concall_scores · " + C.esc(asof or "—"),
                     '<div class="g-counts">' + tiles + "</div>"
                     + C.learn("We only count things that can be measured: did a stated number "
                               "arrive, how much of what they say is quantified at all, and whether "
                               "the record is getting worse. A name stays 'not yet proven' until "
                               "its promises have had time to settle.")
                     + table(("Symbol", "Tier", "Score", "Forward tone", "Veto",
                              "Guidance accuracy (settled)", "How much is quantified", "As of",
                              "Calls", ""), body)
                     + '<p class="g-note">' + _CORPUS_NOTE + " " + ref_link("cci") + "</p>",
                     sample=sample) + fp)


# ── growth intent ──────────────────────────────────────────────────────────────

_GROWTH_FENCE = ("<b>A proposal ledger, not a signal.</b> The idea that these statements tilt "
                 "forward returns was tested against randomised placebo windows and <b>killed</b> — "
                 "the apparent drift came from which companies get covered, not from what was said. "
                 "Rows are ordered by the size of the commitment, never by expected return.")


def growth(rows: list, stype: str, tabs_def, sample: bool = False) -> str:
    body = ""
    for r in rows:
        neg = (r.get("polarity") or 0) < 0
        body += ("<tr><td>" + sym(r.get("symbol")) + "</td><td>"
                 + C.esc(r.get("period_label") or r.get("year") or "—") + "</td><td>"
                 + C.esc(str(r.get("statement_type") or "—").replace("_", " ")) + "</td><td class='g-num'>"
                 + (_n(r.get("amount_cr"), 0) if r.get("amount_cr") else "—") + "</td><td"
                 + (" class='dn'" if neg else "") + ">"
                 + C.esc((r.get("claim_text") or "")[:240]) + "</td></tr>")
    return (crumb("Growth intent") + verdict(_GROWTH_FENCE, "warn")
            + C.zone("Growth intent", "concall_signals",
                     tabs(tabs_def, stype, "/dash/home/strategies/growth", "type")
                     + C.learn("Everything management said it intends to spend, build, launch or "
                               "repay on an earnings call, with the rupee amounts normalised to "
                               "crore so a ₹1,250 crore plan and a ₹12.5 billion plan sort together.")
                     + table(("Symbol", "Period", "Kind", "₹ crore", "What management said"), body)
                     + '<p class="g-note">' + _CORPUS_NOTE + "</p>", sample=sample))


# ── ownership & filings (4 lenses, ONE hub) ────────────────────────────────────

_OWN_FENCE = ("Anchored to the date each filing became public — what was knowable when. Descriptive "
              "only; no return edge is claimed in either direction. Read-only, and nothing here is "
              "scraped from a third-party site.")


def ownership(lens: str, payload: dict, sample: bool = False) -> str:
    nav = tabs((("insider", "Insider dealing"), ("ratings", "Credit ratings"),
                ("sast", "Stake & pledge"), ("shp", "Shareholding")), lens,
               "/dash/home/strategies/ownership", "lens")
    if lens == "ratings":
        inner = _own_ratings(payload)
    elif lens == "sast":
        inner = _own_sast(payload)
    elif lens == "shp":
        inner = _own_shp(payload)
    else:
        inner = _own_insider(payload)
    return (crumb("Ownership & filings")
            + C.zone("Ownership & filings", C.esc(payload.get("prov") or "filings"),
                     nav + inner, sub="four filing feeds, one place", sample=sample)
            + C.fence(_OWN_FENCE))


def _own_insider(p: dict) -> str:
    board = p.get("board") or []
    tape = p.get("tape") or []
    tiles = "".join([
        C.count_tile(sum(1 for r in board if r.get("verdict") == "conviction"), "Buying conviction"),
        C.count_tile(sum(1 for r in board if r.get("verdict") == "caution"), "Selling", warn=True),
        C.count_tile(sum(1 for r in board if (r.get("promoter_cluster_buy_30d") or 0) >= 2),
                     "Several insiders buying"),
        C.count_tile(sum(1 for r in board if (r.get("pledge_adverse_ct_90") or 0) > 0),
                     "Pledge risk", warn=True)])
    brows = "".join("<tr><td>" + sym(r.get("symbol")) + "</td><td>"
                    + C.esc(str(r.get("verdict") or "—").replace("_", " ")) + "</td><td class='g-num'>"
                    + _cr(r.get("open_market_buy_value_30d")) + "</td><td class='g-num'>"
                    + _cr(r.get("open_market_buy_value_90d")) + "</td><td class='g-num'>"
                    + _cr(r.get("open_market_sell_value_90d")) + "</td><td class='g-num'>"
                    + _n(r.get("promoter_cluster_buy_30d"), 0) + "</td><td class='g-num'>"
                    + _n(r.get("n_filings_90"), 0) + "</td></tr>" for r in board)
    trows = "".join("<tr><td>" + C.esc(r.get("disclosure_dt")) + "</td><td>"
                    + sym(r.get("symbol")) + "</td><td>" + C.esc(r.get("category") or "—")
                    + "</td><td>" + C.esc(str(r.get("signal_class") or "—").replace("_", " "))
                    + "</td><td class='g-num'>" + _cr(r.get("value_rs")) + "</td><td>"
                    + (("<a href='" + C.safe_url(r.get("source_url")) + "'>Filing ⇗</a>")
                       if r.get("source_url") else "—") + "</td></tr>" for r in tape)
    return ('<div class="g-counts">' + tiles + "</div>"
            + C.learn("Directors, promoters and key managers must disclose their own dealing. We "
                      "only treat open-market buying by those principals as meaningful; routine "
                      "plumbing like inter-se transfers and ESOP allotments is classified out.")
            + table(("Symbol", "Read", "Bought 30d", "Bought 90d", "Sold 90d", "Insiders buying",
                     "Filings"), brows)
            + "<h3>The tape</h3>"
            + table(("Disclosed", "Symbol", "Who", "What", "Value", "Source"), trows))


def _own_ratings(p: dict) -> str:
    tr = p.get("transitions") or []
    tape = p.get("tape") or []
    tiles = "".join([
        C.count_tile(sum(1 for r in tr if (r.get("notch") or 0) > 0), "Upgrades"),
        C.count_tile(sum(1 for r in tr if (r.get("notch") or 0) < 0), "Downgrades", warn=True),
        C.count_tile(sum(1 for r in tr if r.get("below_investment_grade")),
                     "Below investment grade", warn=True),
        C.count_tile(len(tape), "Filings in window")])
    rows = "".join("<tr><td>" + C.esc(r.get("broadcast_dt") or "—") + "</td><td>"
                   + sym(r.get("symbol")) + "</td><td>"
                   + _signed(r.get("notch"), 0, " notch") + "</td><td>"
                   + C.esc(r.get("rating_raw") or "—") + "</td><td>"
                   + C.esc(r.get("agency") or "—") + "</td><td>"
                   + C.esc(r.get("outlook") or "—") + "</td></tr>" for r in tr)
    trows = "".join("<tr><td>" + C.esc(r.get("broadcast_dt")) + "</td><td>"
                    + C.esc(r.get("issuer_name") or r.get("symbol") or "—") + "</td><td>"
                    + C.esc(r.get("agency") or "—") + "</td><td>"
                    + C.esc(r.get("action_class") or "—") + "</td><td>"
                    + C.esc(r.get("rating_raw") or "—") + "</td><td>"
                    + (("<a href='" + C.safe_url(r.get("attachment_url")) + "'>Filing ⇗</a>")
                       if r.get("attachment_url") else "—") + "</td></tr>" for r in tape)
    return ('<div class="g-counts">' + tiles + "</div>"
            + C.learn("A credit rating agency's view of whether a company can pay its debts. We "
                      "count company-level actions, never raw filing rows — one downgrade "
                      "re-broadcast by three agencies on the same day is one event.")
            + table(("Broadcast", "Symbol", "Move", "Rating", "Agency", "Outlook"), rows)
            + "<h3>The tape</h3>"
            + table(("Broadcast", "Issuer", "Agency", "Action", "Rating as filed", "Source"), trows))


def _own_sast(p: dict) -> str:
    conf = p.get("confluence") or []
    tape = p.get("tape") or []
    tiles = "".join([
        C.count_tile(len(conf), "Stake and pledge both moved"),
        C.count_tile(sum(1 for r in conf if r.get("shape") == "constructive"), "Constructive"),
        C.count_tile(sum(1 for r in conf if r.get("shape") == "distress"), "Distress", warn=True),
        C.count_tile(sum(1 for r in conf if (r.get("invocations") or 0) > 0),
                     "Pledges invoked", warn=True)])
    rows = "".join("<tr><td>" + sym(r.get("symbol")) + "</td><td>"
                   + C.esc(str(r.get("shape") or "—")) + "</td><td>"
                   + _signed(r.get("stake_net"), 2, "pp") + "</td><td>"
                   + _signed(r.get("pledge_net"), 2, "pp") + "</td><td class='g-num'>"
                   + _n(r.get("encumb_now"), 2) + "%</td><td class='g-num'>"
                   + _n(r.get("n_filings"), 0) + "</td></tr>" for r in conf)
    trows = "".join("<tr><td>" + C.esc(r.get("broadcast_dt")) + "</td><td>"
                    + sym(r.get("symbol")) + "</td><td>"
                    + C.esc(r.get("event_type") or r.get("acq_sale") or "—") + "</td><td class='g-num'>"
                    + _n(r.get("event_pct") if r.get("feed") == "pledge"
                         else (r.get("pct_acq") or r.get("pct_sale")), 2) + "%</td><td class='g-num'>"
                    + _n(r.get("post_pct") or r.get("pct_after"), 2) + "%</td><td>"
                    + (("<a href='" + C.safe_url(r.get("attachment")) + "'>Filing ⇗</a>")
                       if r.get("attachment") else "—") + "</td></tr>" for r in tape)
    return ('<div class="g-counts">' + tiles + "</div>"
            + C.learn("Two filing streams read together: who crossed a stake threshold, and who "
                      "pledged or released shares as loan collateral. A filing that moves a quarter "
                      "of the company is badged as a control event and never added into the "
                      "ordinary stake totals. A shape describes a crossing that already happened.")
            + table(("Symbol", "Shape", "Stake change", "Pledge change", "Pledged now", "Filings"), rows)
            + "<h3>The tape</h3>"
            + table(("Broadcast", "Symbol", "Event", "% of equity", "After", "Source"), trows))


def _own_shp(p: dict) -> str:
    m = p.get("matrix") or {}
    qs = m.get("quarters") or []
    rows = m.get("rows") or []
    if not qs:
        return (C.learn("Who owns the company, quarter by quarter: promoters, foreign "
                        "institutions, domestic institutions.")
                + C.empty("The quarterly shareholding archive is not attached to this environment. "
                          "It lives in the separate research store on the server."))
    head = ["Symbol"] + [q for q in qs]
    body = ""
    for r in rows:
        cells = ""
        for c in r.get("cells", []):
            pr, fi, di = c.get("Promoters"), c.get("FIIs"), c.get("DIIs")
            if pr is None and fi is None and di is None:
                cells += "<td class='g-num'>—</td>"
                continue
            cells += ("<td class='g-num'><b>" + _n(pr, 1) + "</b><br><span class='g-sub'>FII "
                      + _n(fi, 1) + " · DII " + _n(di, 1) + "</span>"
                      + ("<br><span class='g-sub'>ⓧ mixed source</span>" if c.get("mixed") else "")
                      + "</td>")
        body += "<tr><td>" + sym(r.get("symbol")) + "</td>" + cells + "</tr>"
    return (C.learn("Each cell is the promoter holding for that quarter, with foreign and domestic "
                    "institutional holdings underneath. Only neighbouring quarters can be compared — "
                    "a reporting gap is shown but never counted as a change.")
            + table(head, body)
            + '<p class="g-note">History comes from a frozen archive collection, read-only and never '
              're-fetched; newer cells come from exchange XBRL filings. Where the two meet they are '
              'continuity-checked, and a cell mixing both sources is marked.</p>')


# ── launchpad (screen + evidence) ──────────────────────────────────────────────

_LP_FENCE = ("<b>A candidate screen, not a strategy.</b> The recorded verdict is exact: a "
             "<b>validated screen with no fundable edge net of cost</b>. What was validated is the "
             "<i>selection</i> — these setups really do precede large moves more often than chance. "
             "What was never found is a tradeable edge: once realistic costs are paid, no wrapper "
             "around this screen made money. Use it as a shortlist to research, never as a buy list.")

_LP_EVIDENCE_FENCE = ("Read it as a distribution, not a promise. This is a point-in-time study, "
                      "<b>gross of costs</b>, and survivorship-exposed — delisted losers are absent, "
                      "so the returns here are biased upward.")


def launchpad(tab: str, screen: list, asof, ev: dict, sample: bool = False) -> str:
    nav = tabs((("", "Today's setups"), ("evidence", "Track record")), tab,
               "/dash/home/strategies/launchpad")
    if tab == "evidence":
        inner = _lp_evidence(ev)
        prov = "ignition_outcomes · " + C.esc(str(ev.get("as_of") or "—"))
    else:
        inner = _lp_screen(screen)
        prov = "launchpad_signals · " + C.esc(str(asof or "—"))
    return (crumb("Launchpad") + verdict(_LP_FENCE, "warn")
            + C.zone("Launchpad", prov, nav + inner, sub="a validated screen and its record",
                     sample=sample))


def _lp_screen(rows: list) -> str:
    if not rows:
        return (C.learn("Setups where price has moved but activity is contracting rather than "
                        "expanding — the coil before a move, not the move itself.")
                + C.empty("Tonight's scan has not landed yet. Check back after the next run."))
    _SETUP = {"MOM_CONT": "Momentum, still contracting", "COILED": "Coiled",
              "PULLBACK": "Pullback in an uptrend"}
    body = ""
    for r in rows:
        flags = [f for f in str(r.get("flags") or "").split("|") if f]
        pills = " · ".join(C.esc(_SETUP.get(f, f)) for f in flags) or "—"
        star = " ⭐" if r.get("buyer") else ""
        body += ("<tr><td>" + sym(r.get("symbol")) + star + "</td><td>" + pills
                 + "</td><td class='g-num'>" + _n(r.get("age"), 0) + "</td><td>"
                 + _signed((r.get("ret22") or 0) * 100) + "</td><td class='g-num'>"
                 + _n(r.get("vratio"), 2) + "×</td><td>"
                 + _signed((r.get("rng") or 0) * 100) + "</td><td class='g-num'>"
                 + _cr(r.get("med_turn")) + "</td></tr>")
    return (C.learn("Setups where price has moved but day-to-day activity is contracting rather "
                    "than expanding — the coil before a move, not the move itself. ⭐ marks a name "
                    "where a genuine one-sided institutional buyer showed up in the bulk/block "
                    "tape. A liquidity floor keeps illiquid names out.")
            + table(("Symbol", "Setup", "Sessions since trigger", "22-day move", "Volume ratio",
                     "22-day range", "Typical daily turnover"), body))


def _lp_evidence(ev: dict) -> str:
    if not ev.get("n"):
        return C.empty("The outcome study has not been computed in this environment.")
    tiles = "".join([
        C.tile("Signals studied", _n(ev.get("n"), 0), "historical setups"),
        C.tile("Reached +25% in a year", _pct(ev.get("hit25")), "share of signals"),
        C.tile("Typical one-year return", _pct(ev.get("med12")), "median, gross of costs"),
        C.tile("Typical dip first", _pct(ev.get("med_mae")), "median worst drawdown"),
    ])
    crows = "".join("<tr><td>" + C.esc(c.get("character") or "—") + "</td><td class='g-num'>"
                    + _n(c.get("n"), 0) + "</td><td>" + _signed(c.get("avg12"))
                    + "</td><td class='g-num'>" + _pct(c.get("hit")) + "</td><td>"
                    + _signed(c.get("avg_mfe")) + "</td><td>" + _signed(c.get("avg_mae"))
                    + "</td></tr>" for c in (ev.get("cohorts") or []))
    tot = sum((h.get("n") or 0) for h in (ev.get("hist") or [])) or 1
    hbars = "".join('<div class="g-bar"><span class="g-bl">' + C.esc(h.get("bin"))
                    + '</span><span class="g-bt"><i style="width:'
                    + f"{(h.get('n') or 0) / tot * 100:.1f}" + '%"></i></span>'
                    '<span class="g-num">' + _n((h.get("n") or 0) / tot * 100, 1) + "%</span></div>"
                    for h in (ev.get("hist") or []))
    lrows = "".join("<tr><td>" + C.esc(z.get("label") or z.get("x")) + "</td><td class='g-num'>"
                    + _n(z.get("n_touched"), 0) + "</td><td class='g-num'>"
                    + _pct((z.get("recover_rate") or 0) * 100) + "</td><td class='g-num'>"
                    + _pct((z.get("base_rate") or 0) * 100) + "</td></tr>"
                    for z in (ev.get("ladder") or []))
    return ('<div class="g-tiles">' + tiles + "</div>"
            + verdict(_LP_EVIDENCE_FENCE, "warn")
            + C.learn("Medians, not averages — a handful of enormous winners drags an average "
                      "somewhere no individual signal ever went.")
            + "<h3>By setup type</h3>"
            + table(("Setup", "Signals", "Typical year", "Reached +25%", "Typical best rise",
                     "Typical worst dip"), crows)
            + "<h3>Where the one-year outcomes landed</h3>"
            + '<div class="g-bars">' + (hbars or C.empty("No distribution yet.")) + "</div>"
            + ("<h3>If it drops, how often did it come back?</h3>"
               + table(("Drop from entry", "Times touched", "Recovered", "Base rate"), lrows)
               if lrows else ""))


# ── the workspace stylesheet (scoped `:root[data-ui-g]`, additive to components.css) ──


def css() -> str:
    return """<style>/* g-strategies (lane w3) */
:root[data-ui-g] .g-crumb{font-size:12px;color:var(--ink-3);margin:0 0 12px}
:root[data-ui-g] .g-crumb a{color:var(--ink-2);text-decoration:none}
:root[data-ui-g] .g-crumb a:hover{color:var(--accent)}
:root[data-ui-g] .g-verdict{border:1px solid var(--line-2);border-left:3px solid var(--warn,#c69316);
  background:var(--bg-2);border-radius:10px;padding:12px 15px;margin:0 0 16px;font-size:13px;line-height:1.6;color:var(--ink-2)}
:root[data-ui-g] .g-verdict.ok{border-left-color:var(--accent)}
:root[data-ui-g] .g-verdict b{color:var(--ink)}
:root[data-ui-g] .g-scroll{max-height:440px;overflow:auto;border:1px solid var(--line);border-radius:10px;scrollbar-width:thin}
:root[data-ui-g] .g-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] .g-tbl th{position:sticky;top:0;z-index:1;background:var(--bg-2);text-align:left;
  font:600 10.5px/1.3 var(--font);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);
  padding:8px 10px;border-bottom:1px solid var(--line-2);white-space:nowrap}
:root[data-ui-g] .g-tbl td{padding:7px 10px;border-bottom:1px solid var(--line);color:var(--ink-2);vertical-align:top}
:root[data-ui-g] .g-tbl tr:hover td{background:var(--bg-2)}
:root[data-ui-g] .g-tbl td.g-num,:root[data-ui-g] .g-tbl th.g-num{text-align:right;font-family:var(--mono)}
:root[data-ui-g] .g-tabs{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 12px}
:root[data-ui-g] .g-tabs a{font:600 11.5px var(--font);color:var(--ink-3);text-decoration:none;
  padding:6px 12px;border:1px solid var(--line-2);border-radius:var(--r-pill)}
:root[data-ui-g] .g-tabs a[aria-current="page"]{color:var(--on-accent);background:var(--accent);border-color:var(--accent)}
:root[data-ui-g] .g-tabs a:hover{color:var(--ink)}
:root[data-ui-g] .g-segbar{display:flex;flex-wrap:wrap;gap:4px;margin:12px 0}
:root[data-ui-g] .g-seg-a{font:700 11.5px var(--font);color:var(--ink-3);text-decoration:none;padding:7px 13px;
  border:1px solid var(--line-2);border-radius:var(--r-pill)}
:root[data-ui-g] .g-seg-a.on{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi));border-color:var(--accent)}
:root[data-ui-g] .g-dgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:10px;margin-top:14px}
:root[data-ui-g] .g-dcard{display:block;padding:12px 14px;border:1px solid var(--line-2);border-radius:11px;
  background:var(--bg-2);text-decoration:none}
:root[data-ui-g] .g-dcard:hover{border-color:var(--accent)}
:root[data-ui-g] .g-dcard b{display:block;color:var(--ink);font-size:13.5px;margin-bottom:3px}
:root[data-ui-g] .g-dcard span{color:var(--ink-3);font-size:11.5px;line-height:1.45}
:root[data-ui-g] .g-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
:root[data-ui-g] .g-bars{display:flex;flex-direction:column;gap:6px;max-height:340px;overflow:auto;scrollbar-width:thin}
:root[data-ui-g] .g-bar{display:grid;grid-template-columns:150px 1fr 72px;align-items:center;gap:10px;font-size:12.5px}
:root[data-ui-g] .g-bl{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
:root[data-ui-g] .g-bt{display:block;height:9px;background:var(--bg-3);border-radius:5px;overflow:hidden}
:root[data-ui-g] .g-bt i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .g-adbar{position:relative;display:block;width:110px;height:8px;background:var(--bg-3);border-radius:4px}
:root[data-ui-g] .g-adbar i{position:absolute;top:-2px;width:3px;height:12px;background:var(--accent);border-radius:2px}
:root[data-ui-g] .g-spark2{margin:14px 0 6px}
:root[data-ui-g] .g-spark2 svg{width:100%;height:130px;display:block}
:root[data-ui-g] .g-note{font-size:12px;color:var(--ink-3);line-height:1.6;margin:10px 0 0}
:root[data-ui-g] .g-note b{color:var(--ink-2)}
:root[data-ui-g] .g-legend{font-size:12px;color:var(--ink-3);margin:12px 0 0;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
:root[data-ui-g] .g-more{color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap}
:root[data-ui-g] .g-more:hover{text-decoration:underline}
:root[data-ui-g] .g-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
:root[data-ui-g] .g-counts{display:flex;flex-wrap:wrap;gap:10px}
:root[data-ui-g] .g-focus h3{font:700 13px var(--font);color:var(--ink);margin:18px 0 8px}
@media(max-width:620px){:root[data-ui-g] .g-bar{grid-template-columns:96px 1fr 60px}}
</style>"""
