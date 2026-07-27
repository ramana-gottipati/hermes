"""src/web/home/rotation_pages.py — THE Graphite rotation experience (W2-B).

The classic estate split one question across FOUR lenses: `/dash/rrg` (the map), `/dash/rotation`
(the weather/phases), `/dash/rsband` (the level inside its own range) and `/dash/cycle-clock` (the
lifecycle clock). They are four readings of ONE dataset — a sector's relative strength versus the
broad market — so in Graphite they are four VIEWS of one page, `/dash/home/rotation?view=…`, each
URL-addressable.

The Journeys view already shipped (§5-D) and is untouched; this module adds the other three and the
switcher that makes them one experience. Bodies only — the route stays where it already lives, in
`src/web/home/__init__.py`.

Imports NOTHING from a classic view module. Every number comes from `markets_reads`, which reuses
the canonical `src/automation/` engines (`rrg` · `rsband` · `rs_phase` · `stock_rs`).
"""
from __future__ import annotations

from src.web.home import components as C
from src.web.home import markets_reads as R
from src.web.home import markets_ui as U
from src.web.home import reads as HR      # the shipped Graphite read layer (rrg_journey)

VIEWS = (("journeys", "Journeys"), ("weather", "Weather"), ("band", "Band"), ("clock", "Clock"))
_KEYS = {k for k, _ in VIEWS}

TITLES = {
    "journeys": ("Where each sector has travelled",
                 "6, 12 and 24-month rotation journeys versus the broad market"),
    "weather": ("What the weather is in each sector",
                "the shape of the relative-strength sweep across 1, 3, 6 and 12 months"),
    "band": ("How rich or cheap each sector's strength is",
             "today's relative strength inside that sector's OWN 3-year range"),
    "clock": ("The lifecycle clock",
              "every sector's position and direction of travel on one dial"),
}

_FENCE = ("Four readings of one dataset: each sector's price relative to the broad market. "
          "Descriptive of the past, from NSE index history — never advice, a recommendation, "
          "or a prediction.")


def view_of(raw) -> str:
    """Normalise `?view=` to a known view (an unknown value lands on the default, never a 404)."""
    v = str(raw or "").strip().lower()
    return v if v in _KEYS else "journeys"


def head(view: str) -> str:
    """The switcher + the title for the current view — the thing that makes four lenses one page."""
    title, sub = TITLES.get(view, TITLES["journeys"])
    return (U.tabs(VIEWS, view, U.ROTATION_HREF)
            + '<p class="g-mnote" style="margin:0 0 12px"><b style="color:var(--ink)">'
            + C.esc(title) + "</b> — " + C.esc(sub) + "</p>")


# ── view: WEATHER (ports /dash/rotation) ──────────────────────────────────────────────
def _weather_rows(rows) -> str:
    out = ""
    for r in rows:
        out += ("<tr><td>" + C.esc(r.get("label")) + "</td>"
                "<td>" + U.phase_pill(r.get("phase"), r.get("phase_label")) + "</td>"
                '<td class="r">' + U.signed(r.get("s1")) + "</td>"
                '<td class="r">' + U.signed(r.get("s3")) + "</td>"
                '<td class="r">' + U.signed(r.get("s6")) + "</td>"
                '<td class="r">' + U.signed(r.get("s12")) + "</td>"
                '<td class="r pro-more">' + U.signed(r.get("r1")) + "</td>"
                '<td class="r pro-more">' + U.signed(r.get("r3")) + "</td></tr>")
    return out


def _phase_grid(cells: dict) -> str:
    """The 2×2 lifecycle grid: for each phase, how many names sit in it and the strict-diagonal
    shortlist (the stock AND its own sector share the phase). The count is the Free read; the names
    are the evidence behind it."""
    if not cells:
        return ""
    order = (("RECOVERY", "a base turning up"), ("TAILWIND", "strong and still strengthening"),
             ("ROLLING-OVER", "a leader cracking"), ("HEADWIND", "weak and still weakening"))
    out = ""
    for key, blurb in order:
        c = cells.get(key) or {}
        rows = c.get("rows") or []
        names = "".join('<div class="g-mrow">' + U.sym(x.get("symbol"))
                        + '<span class="g-msp"></span><span class="g-mnum">'
                        + U.num(x.get("rs_rank"), 0) + "</span></div>" for x in rows)
        if not names:
            names = '<div class="g-mrow" style="color:var(--ink-3)">No name has the stock and its ' \
                    "own sector in this phase today.</div>"
        out += ('<div class="g-mcell"><h4>' + U.phase_pill(key, c.get("label"))
                + '<span class="g-mnum">' + U.num(c.get("n"), 0) + "</span></h4>"
                '<span class="g-msub">' + C.esc(blurb) + " · stock and sector agree</span>"
                + names + "</div>")
    return '<div class="g-mgrid">' + out + "</div>"


def _turns(rows) -> str:
    if not rows:
        return C.empty("No phase changed today — that needs at least two days of rotation history, "
                       "which accrues nightly.")
    out = ""
    for r in rows:
        out += ('<a href="' + U.STOCK_HREF + C.esc(r.get("symbol")) + '">'
                + C.esc(r.get("symbol")) + " <em>" + C.esc(r.get("from_label"))
                + " → " + C.esc(r.get("to_label")) + "</em></a>")
    return '<div class="g-mturn">' + out + "</div>"


def weather(conn) -> str:
    rows, demo = R.sector_weather(conn), False
    if not rows:
        rows, demo = R.DEMO_WEATHER, True
    cells = R.phase_cells()
    turns = R.phase_turns()
    cols = [("Sector", ""), ("Weather", ""), ("1m RS", "r"), ("3m RS", "r"), ("6m RS", "r"),
            ("12m RS", "r"), ('<span class="pro-more">1m return</span>', "r pro-more"),
            ('<span class="pro-more">3m return</span>', "r pro-more")]
    body = (U.sample_note(demo, "sector weather")
            + U.table(cols, _weather_rows(rows), height=360,
                      note="RS slope = how fast this sector's price ratio versus the broad market "
                           "is rising or falling over that horizon, in percent. The weather word is "
                           "the SHAPE of all four together, not any single one.")
            + C.pro_more('<p class="g-mnote">Pro adds the sector\'s own 1-month and 3-month price '
                         "return beside its relative strength — so you can separate “it beat the "
                         "market” from “it went up”. A sector can lead while falling.</p>"))
    grid = ""
    if cells and any((cells.get(k) or {}).get("n") for k in cells):
        grid = (U.head("Which names sit in each phase",
                       "the stock AND its own sector in the same phase")
                + _phase_grid(cells))
    turnstrip = (U.head("Just turned", "phases that changed since the previous session")
                 + _turns(turns))
    edu = C.learn("Relative strength answers one question per horizon: did this sector beat the "
                  "broad market over the last month, quarter, half-year, year? The PHASE is the "
                  "shape those four answers make together — a base turning up reads differently "
                  "from a leader rolling over even when today's number is identical. Recovery is a "
                  "staged ladder, not a single event: the short horizons turn first and the long "
                  "ones follow, or the turn was noise.")
    return body + grid + turnstrip + edu


# ── view: BAND (ports /dash/rsband) ───────────────────────────────────────────────────
def _band_rows(rows) -> str:
    out = ""
    for r in rows:
        out += ("<tr><td>" + C.esc(r.get("label")) + "</td>"
                "<td>" + U.pos_strip(r.get("band"),
                                     "0 = at its own RS support · 100 = at its own RS resistance")
                + "</td>"
                "<td>" + C.esc(r.get("band_label") or "—") + "</td>"
                "<td>" + C.esc(_regime_word(r.get("regime"))) + "</td>"
                '<td class="pro-more">' + C.esc(r.get("read") or "—") + "</td>"
                '<td class="r pro-more">' + U.num(r.get("detr"), 0) + "</td></tr>")
    return out


def _regime_word(regime) -> str:
    """Plain English for the honesty gate that decides whether 'cheap' even means anything."""
    r = str(regime or "").upper()
    if r == "MEAN_REVERTING":
        return "Range — the cheap/rich read applies"
    if r == "TRENDING":
        return "Trend — cheap can stay cheap"
    return "—"


def band(conn) -> str:
    rows, demo = R.band_lanes(conn), False
    if not rows:
        rows, demo = R.DEMO_BAND, True
    cols = [("Sector", ""), ("Position in its own range", ""), ("Where that sits", ""),
            ("Regime", ""), ('<span class="pro-more">Read</span>', "pro-more"),
            ('<span class="pro-more">Trend-removed</span>', "r pro-more")]
    fence = C.fence(
        "This is a relative-LEVEL description, not an instruction. A sector at the bottom of its own "
        "range is not therefore cheap: if its regime is a trend, that low reading is the trend "
        "working, and it can go lower.")
    return (U.sample_note(demo, "sector RS bands")
            + fence
            + U.table(cols, _band_rows(rows), height=380,
                      note="Position runs 0 to 100 across that sector's OWN trailing three years of "
                           "relative strength, weighted towards recent history — never a rupee "
                           "level and never a cross-sector comparison.")
            + C.pro_more('<p class="g-mnote">Pro adds the plain read for the position × regime × '
                         "direction combination, and the trend-removed position — the same "
                         "percentile computed after the multi-year drift is stripped out, which "
                         "separates “stretched” from “simply re-rating steadily”.</p>")
            + C.learn("Every sector gets judged against itself. The strip shows where today's "
                      "relative strength sits inside that sector's own three-year range: at the "
                      "left it is as weak versus the market as it has been; at the right, as strong. "
                      "The regime column is the honesty gate — in a range, the position means "
                      "something; in a trend, it mostly means the trend is intact."))


# ── view: CLOCK (ports /dash/cycle-clock) ─────────────────────────────────────────────
def _clock_svg(dots) -> str:
    """One dial: each sector plotted by how far its relative strength sits from normal (x) and how
    fast that is changing (y), both centred at 100. Server-computed SVG, DOM-safe, no animation."""
    pts = [d for d in (dots or []) if d.get("rr") is not None and d.get("mm") is not None]
    if not pts:
        return C.empty("No rotation snapshot on record yet.")
    W = H = 460.0
    cx = cy = W / 2.0
    mag = max([max(abs(float(d["rr"]) - 100.0), abs(float(d["mm"]) - 100.0)) for d in pts] + [1.5])
    R_ = (W / 2.0) - 42.0
    body = ('<circle class="rim" cx="%.1f" cy="%.1f" r="%.1f"/>' % (cx, cy, R_)
            + '<circle class="rim" cx="%.1f" cy="%.1f" r="%.1f"/>' % (cx, cy, R_ * 0.5)
            + '<line class="ax" x1="%.1f" y1="14" x2="%.1f" y2="%.1f"/>' % (cx, cx, H - 14)
            + '<line class="ax" x1="14" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (cy, W - 14, cy)
            + '<text class="lbl" x="%.0f" y="16" text-anchor="end">LEADING</text>' % (W - 12)
            + '<text class="lbl" x="12" y="16">IMPROVING</text>'
            + '<text class="lbl" x="12" y="%.0f">LAGGING</text>' % (H - 8)
            + '<text class="lbl" x="%.0f" y="%.0f" text-anchor="end">WEAKENING</text>' % (W - 12, H - 8))
    for d in pts:
        dx = (float(d["rr"]) - 100.0) / mag * R_
        dy = (float(d["mm"]) - 100.0) / mag * R_
        x, y = cx + dx, cy - dy
        rsi = d.get("rsi")
        ttl = (str(d.get("label")) + " · " + str(d.get("quadrant") or "—")
               + (" · RSI-of-RS " + U.num(rsi, 0) if rsi is not None else ""))
        cls = {"Leading": "q-lead", "Improving": "q-impr",
               "Weakening": "q-weak", "Lagging": "q-lag"}.get(d.get("quadrant"), "q-lag")
        body += ('<g class="' + cls + '"><title>' + C.esc(ttl) + "</title>"
                 '<circle cx="%.1f" cy="%.1f" r="5" fill="currentColor" opacity=".85"/>' % (x, y)
                 + '<text class="nm" x="%.1f" y="%.1f">%s</text>'
                 % (x + 8, y + 3, C.esc(d.get("label"))) + "</g>")
    return ('<svg class="g-mclock" viewBox="0 0 460 460" preserveAspectRatio="xMidYMid meet" '
            'role="img" aria-label="Sector rotation lifecycle clock">' + body + "</svg>")


def _clock_rows(dots) -> str:
    out = ""
    for d in sorted(dots or [], key=lambda x: -(x.get("mm") or 0)):
        out += ("<tr><td>" + C.esc(d.get("label")) + "</td>"
                "<td>" + U.quad_pill(d.get("quadrant")) + "</td>"
                '<td class="r">' + U.num(d.get("rr"), 1) + "</td>"
                '<td class="r">' + U.num(d.get("mm"), 1) + "</td>"
                '<td class="r pro-more">' + U.num(d.get("rsi"), 0) + "</td>"
                '<td class="r pro-more">' + U.num(d.get("mansfield"), 1) + "</td></tr>")
    return out


def clock(conn) -> str:
    dots, demo = R.clock_dots(conn), False
    if not dots:
        dots, demo = R.DEMO_CLOCK, True
    cols = [("Sector", ""), ("Quadrant", ""), ("Strength", "r"), ("Change in strength", "r"),
            ('<span class="pro-more">RSI-of-RS</span>', "r pro-more"),
            ('<span class="pro-more">Mansfield</span>', "r pro-more")]
    return (U.sample_note(demo, "the rotation clock")
            + _clock_svg(dots)
            + '<p class="g-mnote" style="text-align:center">Right of centre = stronger than the '
              "broad market by more than usual. Above centre = that strength is still building. "
              "Sectors circulate clockwise: Improving → Leading → Weakening → Lagging.</p>"
            + U.head("The same dial as a table", "every dot, with its numbers")
            + U.table(cols, _clock_rows(dots), height=320,
                      note="Both numbers are centred at 100 by construction — 100 means “as strong "
                           "versus the market as this sector normally is”, not zero and not a price.")
            + C.pro_more('<p class="g-mnote">Pro adds RSI-of-RS (is the relative move itself '
                         "stretched?) and Mansfield (relative strength versus its own long-run "
                         "average) — the two reads that separate a durable turn from a bounce.</p>")
            + C.learn("The clock and the journey map are the SAME two numbers drawn two ways. The "
                      "map shows the path travelled; the clock shows where everything stands right "
                      "now, on one dial, so you can see whether leadership is concentrated in one "
                      "corner or spread around it."))


# ── the page body ─────────────────────────────────────────────────────────────────────
def body(conn, view: str = "journeys") -> str:
    """The whole rotation page body for `view`. Never raises: each view degrades to a fence + empty
    state, and the caller wraps this in its own try/except as well."""
    v = view_of(view)
    if v == "journeys":
        try:
            journeys = {m: HR.rrg_journey(conn, months=m) for m in (6, 12, 24)}
        except Exception:  # noqa: BLE001
            journeys = {}
        inner = C.rotation_view(journeys)   # the §5-D view, byte-untouched
    elif v == "weather":
        inner = weather(conn)
    elif v == "band":
        inner = band(conn)
    else:
        inner = clock(conn)
    return C.zone("Sector rotation", "NSE index history · nightly", head(v) + inner,
                  sub="one dataset, four readings", name="Rotation")


def page_fence() -> str:
    return C.fence(_FENCE)
