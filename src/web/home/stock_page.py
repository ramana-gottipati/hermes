"""src/web/home/stock_page.py — the Graphite stock page (`/dash/home/stock?sym=`). W1.

The cutover blocker: the old preview uniquely served a stock hub, so `/dash/home` could not become
the default while `/dash/preview/stock` was the only per-symbol dossier in the new identity. This
module is the Graphite replacement.

SHAPE (the ratified archetype, `docs/redesign-coordination.md` Part II §A): ONE evidence-scroll hub
— identity strip → digest tiles (each an anchor to its evidence) → a deterministic descriptive
sentence → the sticky section index → the evidence sections, each a FIXED-SIZE box that scrolls
INTERNALLY (standing correction #3) — beside a context rail (news · results · corporate actions ·
peers) that is always visible.

TIERING (§3 grammar): FREE is complete and honest — every number is on the page, never crippled.
PRO adds the REFERENCE LAYER via the existing `components.ref_chip` idiom: percentile · typical ·
direction vs the stock's OWN history, so a bare number becomes decision-useful. One `pro_teaser`
advertises that layer to Free.

ISOLATION: no preview/legacy render module is imported (gate: `tests/test_home_isolation.py`). Every
concept the M4 hub borrowed from `dashboard`/`hub_sections_v3` is re-implemented over the tables in
`stock_reads.py`; the chart is re-implemented in `stock_chart_g.py`. All CSS is `.g-*`.

HONESTY: descriptive-only throughout — no buy/sell/add/avoid verbs, no ranking of the falsified
families (MEP is a descriptor (D62), CCI failed Gate B leak-free, Wolfe's edge is selection not
craft, the X-setups are descriptive scans). Demo data is never fabricated for a symbol: an absent
read renders an honest empty state, and the page marks its own sample status.
"""
from __future__ import annotations

import urllib.parse as _uq

from src.web.home import components as C
from src.web.home import reads as MR
from src.web.home import stock_chart_g as CH
from src.web.home import stock_reads as SR

esc = C.esc

# ── the section catalog (order = the sticky index) ──────────────────────────────
# key, title, one-line sub, the classic lens this evidence also powers (spoke)
SECTIONS = (
    ("chart", "Chart", "price · institutional zones · delivery", "/dash/stock", "Full charting workstation"),
    # W1-CONVERGENCE fold: the retired `stock_view.py` lineage led with THIS as its spine, and it was
    # right to — a bare number says nothing until it is ranked against the same stock's own past. Its
    # five metrics (price · 3-month momentum · delivery · turnover · coil) over ~3 years on a
    # corporate-action-ADJUSTED close are strictly richer than this page's own 252-session,
    # three-metric reference, so both are kept: that one stays inline beside the numbers it qualifies,
    # this one is the dedicated panel.
    ("own", "Own history", "every number ranked against its own past", "/dash/self-history",
     "Own-history lens"),
    ("pos", "Positioning", "where big money transacted", "/dash/stocks", "Positioning lens"),
    ("mep", "Accumulation", "signed accumulation / distribution", "/dash/mep", "Accum / Distrib lens"),
    ("rs", "Strength", "relative strength vs the broad market", "/dash/rs-hub", "Relative-strength hub"),
    ("qual", "Quality", "the 14-pattern read and its real gates", "/dash/growth", "Growth / quality lens"),
    ("cpr", "Structure", "pivot structure across timeframes", "/dash/cpr", "Structure lens"),
    ("cci", "Credibility", "promise vs delivery on the concalls", "/dash/concalls", "Credibility lens"),
    ("setups", "Setups", "base · shelves · overnight split", "/dash/launchpad", "Launchpad"),
    ("fno", "F&O", "open interest, quadrant and basis", "/dash/fno", "F&O positioning board"),
    # W1-CONVERGENCE fold: the ONLY block the retired lineage served that had no counterpart here at
    # all. These are SEBI primary-source disclosures — PIT insider trades, SAST pledge events and
    # Reg-29 substantial-acquisition crossings — read via `reads.stock_events`. The rail's "Corporate
    # actions" card is the FORWARD view (what goes ex in the next 90 days); this is the RECORD.
    ("disc", "Ownership & disclosures", "insider · pledge · substantial acquisitions",
     "/dash/insider", "Insider lens"),
)

_STATE_WORDS = {"STRONG_ACCUM": "strong accumulation", "ACCUM": "accumulation",
                "NEUTRAL": "a neutral tape", "DISTRIB": "distribution",
                "STRONG_DISTRIB": "strong distribution"}


# ── small helpers ───────────────────────────────────────────────────────────────
def _g(row, key, default=None):
    if not row:
        return default
    try:
        v = row[key] if not isinstance(row, dict) else row.get(key)
    except (KeyError, IndexError, TypeError):
        return default
    return default if v is None else v


def glink(sym, label=None) -> str:
    """A symbol link that stays INSIDE the Graphite experience (never `?symbol=`)."""
    s = esc(sym)
    return ('<a class="g-syma" href="/dash/home/stock?sym=' + _uq.quote(str(sym or "")) + '">'
            + esc(label if label is not None else sym) + "</a>") if s else ""


def _spoke(href: str, label: str, sym: str) -> str:
    return ('<a class="g-spoke" href="' + C.safe_url(href) + "?sym=" + _uq.quote(sym) + '">'
            + esc(label) + " for " + esc(sym) + " →</a>")


def _finite(v):
    """float(v) when it is a real, FINITE number — else None.

    NaN is genuinely reachable on this page: the X-setups payloads store it deliberately
    (`vol_surge` is `float('nan')` when the base turnover is 0, `on_share` when the move nets 0),
    and `json.loads` hands it back as a float. `float()` accepts it and `%`-formatting prints a
    literal "nan", so every numeric formatter here has to reject it explicitly — the same guard
    the canonical dashboard helper carries (`dashboard._nonfinite`)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (f != f or f in (float("inf"), float("-inf"))) else f


def _n(v, dp: int = 2) -> str:
    """`components._num` with the non-finite guard — never renders "nan" / "inf"."""
    f = _finite(v)
    return "—" if f is None else C._num(f, dp)


def _rupee(v) -> str:
    f = _finite(v)
    if f is None:
        return "—"
    for cut, suf in ((1e7, " cr"), (1e5, " L")):
        if abs(f) >= cut:
            return "₹" + C._num(f / cut, 2) + suf
    return "₹" + C._num(f, 0)


def _pct(v, dp: int = 1, signed: bool = False) -> str:
    f = _finite(v)
    if f is None:
        return "—"
    return ("%+." + str(dp) + "f%%") % f if signed else ("%." + str(dp) + "f%%") % f


def _yn(v) -> str:
    """yes / no — but "—" when the field is ABSENT. A missing column is not a "no": conflating
    them would quietly assert a fact the database never recorded (standing correction #4/#6)."""
    return "—" if v is None else ("yes" if v else "no")


def _kv(rows) -> str:
    """A label / value / note table. Every value is server-formatted and escaped."""
    out = ['<table class="g-kv">']
    for item in rows:
        lab, val = item[0], item[1]
        note = item[2] if len(item) > 2 else ""
        out.append('<tr><th scope="row">' + esc(lab) + '</th><td class="g-num">' + esc(val)
                   + "</td><td>" + (note or "") + "</td></tr>")
    out.append("</table>")
    return "".join(out)


# ── identity strip ──────────────────────────────────────────────────────────────
def identity(core: dict, selfref: dict) -> str:
    sym = core["sym"]
    bar, prev, sig = core.get("bar"), core.get("prev"), core.get("sig")
    date = str(_g(bar, "trade_date", ""))[:10] or "no tape yet"
    cmp_html, day = "", None
    if bar:
        close = _g(bar, "close")
        pc = _g(prev, "close")
        if close is not None and pc:
            try:
                day = (float(close) - float(pc)) / float(pc) * 100.0
            except (TypeError, ValueError, ZeroDivisionError):
                day = None
        txt, cls = C._signed_pct(day)
        cmp_html = ('<span class="g-sprice g-num">₹' + _n(close, 2) + "</span>"
                    '<span class="g-sday ' + cls + '">' + esc(txt) + "</span>")
    chips = []
    if _g(sig, "primary_sector"):
        chips.append('<span class="g-schip">' + esc(_g(sig, "primary_sector")) + "</span>")
    phase = _g(sig, "rs_phase") or _g(sig, "rs_vs_broad_trend_state")
    if phase:
        chips.append('<span class="g-schip">RS phase · '
                     + esc(str(phase).replace("_", " ").lower()) + "</span>")
    dp = _g(bar, "deliv_per")
    if dp is not None:
        chips.append('<span class="g-schip">delivery ' + esc(_pct(dp)) + "</span>")
    for t in (core.get("themes") or [])[:3]:
        chips.append('<span class="g-schip thm">' + esc(t) + "</span>")
    refs = ""
    dref = (selfref or {}).get("deliv") or {}
    if dref.get("pctile") is not None:
        refs = C.pro_more(
            '<div class="g-srefs"><span class="g-lab">Unusual for this stock?</span>'
            + C.ref_chip(dref, unit="%", dp=1, trend=dref.get("trend"), bare=True)
            + '<span class="g-sub">today\'s delivery share vs its own last ' + esc(dref.get("n"))
            + " sessions</span></div>")
    # W1-CONVERGENCE fold: the retired lineage's header carried the watchlist write and the escape
    # hatch to the classic dossier. Both are real affordances a stock page owes, and the POST route
    # (`/dash/home/watch/add`) is already home-owned — so they move here rather than being lost.
    actions = ('<form class="g-sact" method="post" action="/dash/home/watch/add">'
               '<input type="hidden" name="symbol" value="' + esc(sym) + '">'
               '<button class="g-btn" type="submit">+ Add to watchlist</button></form>'
               '<a class="g-sclassic" href="/dash/stock?sym=' + _uq.quote(str(sym or ""))
               + '">Full classic view →</a>')
    return ('<header class="g-sid"><div class="g-sid-top"><h1>' + esc(sym) + "</h1>"
            + ('<span class="g-sname">' + esc(core.get("name")) + "</span>" if core.get("name") else "")
            + cmp_html
            + '<span class="g-prov">NSE bhav copy · ' + esc(date) + "</span></div>"
            + ('<div class="g-schips">' + "".join(chips) + "</div>" if chips else "")
            + refs + '<div class="g-sactions">' + actions + "</div></header>")


# ── digest: tiles as anchors into the evidence ─────────────────────────────────
def _tile(value: str, label: str, anchor: str, sub: str = "") -> str:
    return ('<a class="g-stile" href="#' + esc(anchor) + '"><span class="g-lab">' + esc(label)
            + '</span><span class="g-big g-num">' + esc(value) + "</span>"
            + ('<span class="g-sub">' + esc(sub) + "</span>" if sub else "")
            + '<span class="g-ev">evidence →</span></a>')


def _conviction(p_score, rs_rank):
    """The composite the classic dossier shows: p-pillar (0-5) and RS rank (0-99) on one 0-100
    scale. A SORTING HEURISTIC, not a validated model — labelled as such on the surface."""
    try:
        p = float(p_score or 0)
        r = float(rs_rank or 0)
    except (TypeError, ValueError):
        return None
    return round(min(100.0, p / 5.0 * 50.0 + r / 99.0 * 50.0))


def digest(core: dict) -> str:
    sig, mep, pt, cci = core.get("sig"), core.get("mep"), core.get("pt"), core.get("cci")
    tiles = []
    if sig:
        conv = _conviction(_g(sig, "p_score"), _g(sig, "rs_rank"))
        # the qualifier is on the SURFACE, not only in the docstring: an unvalidated composite
        # rendered as a bare "96/100" reads as a verdict. Say what it is, where it is shown.
        tiles.append(_tile(str(conv) + "/100" if conv is not None else "—", "Conviction", "pos",
                           "sorting heuristic · p" + str(_g(sig, "p_score", 0)) + "/5 · RS "
                           + str(_g(sig, "rs_rank", "—")) + "/99"))
        xp = _g(sig, "ratio_today_vs_power_1m")
        tiles.append(_tile(str(_g(sig, "trigger_rank", "—")), "Delivery trigger", "pos",
                           (_n(xp, 2) + "× its 1-month power day") if xp is not None else "no spike"))
        rs = _g(sig, "rs_rank")
        tiles.append(_tile(("#" + str(rs)) if rs is not None else "—", "Relative strength", "rs",
                           "of 99 · " + str(_g(sig, "rs_vs_broad_trend_state", "—")).replace("_", " ").lower()))
    if mep:
        tiles.append(_tile(str(_g(mep, "mep_state_smooth", "—")).replace("_", " ").lower(),
                           "Accumulation", "mep", "descriptor only (D62)"))
    if pt:
        tiles.append(_tile(str(_g(pt, "tier", "—")), "Quality", "qual",
                           "naked score " + str(_g(pt, "ns_base", "—")) + "/100"))
    if cci:
        tiles.append(_tile(str(_g(cci, "tier", "—")), "Credibility", "cci",
                           "composite " + str(_g(cci, "composite_score", "—"))))
    if core.get("cpr"):
        d = core["cpr"].get("D") or {}
        tiles.append(_tile(str(_g(d, "pattern", "—")).replace("_", " ").lower(), "Structure", "cpr",
                           "daily pivot pattern"))
    if sig:
        w = _g(sig, "pct_from_52w_high")
        tiles.append(_tile(_pct(w, 1, signed=True) if w is not None else "—", "vs 52-week high",
                           "chart", "today's close"))
    if not tiles:
        return C.empty("No stored signals for this symbol yet — the tape below is still readable.")
    return '<div class="g-stiles">' + "".join(tiles) + "</div>"


def narrative(core: dict) -> str:
    """ONE deterministic descriptive sentence assembled from stored, dated fields. Describes; never
    predicts, never recommends."""
    sig, mep, pt, cci = core.get("sig"), core.get("mep"), core.get("pt"), core.get("cci")
    bits = []
    if _g(sig, "trigger_rank") in ("SS", "S"):
        bits.append("today's delivery positioning sits in the top trigger band")
    st = _g(mep, "mep_state_smooth")
    if st in _STATE_WORDS:
        bits.append("the tape reads as " + _STATE_WORDS[st])
    r = _g(sig, "rs_rank")
    if r is not None:
        band = "top-quartile" if r >= 75 else ("bottom-quartile" if r <= 25 else "mid-pack")
        bits.append("relative strength is " + band + " (#" + str(r) + " of 99)")
    if _g(pt, "tier"):
        bits.append("the 14-pattern quality read grades tier " + str(_g(pt, "tier")))
    if _g(cci, "tier"):
        bits.append("management credibility grades " + str(_g(cci, "tier")))
    if not bits:
        return ""
    # sentence-case the FIRST character only — `str.capitalize()` would lower-case the rest and
    # silently mangle stored grades ("tier B" -> "tier b", "credibility A" -> "a").
    line = "; ".join(bits[:4])
    line = line[:1].upper() + line[1:] + "."
    return ('<p class="g-snarr">' + esc(line)
            + '<span class="g-sub">Every clause is a stored, dated read — open the matching '
              "section for the numbers behind it.</span></p>")


def badges(core: dict) -> str:
    """Which lenses flag THIS name, derived from the fields already loaded (no estate-wide scan)."""
    sym, out = core["sym"], []

    def add(label, href):
        out.append('<a class="g-sbadge" href="' + C.safe_url(href) + "?sym=" + _uq.quote(sym)
                   + '">' + esc(label) + "</a>")
    sig, mep = core.get("sig"), core.get("mep")
    if _g(sig, "trigger_rank") in ("SS", "S"):
        add("Positioning trigger", "/dash/stocks")
    if str(_g(mep, "mep_state_smooth", "")).startswith("STRONG"):
        add("Accumulation extreme", "/dash/mep")
    if (_g(sig, "rs_rank") or 0) >= 90:
        add("Leaders board", "/dash/leaders")
    if _g(core.get("wolfe"), "in_zone"):
        add("Wolfe wave in zone", "/dash/wolfe/scan")
    if core.get("fno"):
        add("F&O positioning", "/dash/fno")
    if not out:
        return ""
    return ('<div class="g-sbadges"><span class="g-lab">Lenses flagging ' + esc(sym)
            + "</span>" + "".join(out) + "</div>")


def section_index(keys) -> str:
    out = ['<nav class="g-sidx" aria-label="Sections">']
    for key, title, _sub, _href, _lab in SECTIONS:
        if key in keys:
            out.append('<a href="#' + key + '">' + esc(title) + "</a>")
    out.append("</nav>")
    return "".join(out)


def section(key: str, title: str, sub: str, prov: str, body: str, spoke: str = "",
            fence_text: str = "") -> str:
    """A fixed-size evidence box that scrolls INTERNALLY (standing correction #3)."""
    return ('<section class="g-sec" id="' + esc(key) + '" data-sec="' + esc(key) + '">'
            '<div class="g-sec-h"><h2>' + esc(title) + "</h2>"
            '<span class="g-sub">' + esc(sub) + "</span>"
            + C.prov(prov.split("·")[0].strip(), (prov.split("·", 1)[1].strip() if "·" in prov else ""))
            + "</div>"
            + (C.fence(fence_text) if fence_text else "")
            + '<div class="g-sec-b">' + body + "</div>"
            + ('<div class="g-sec-f">' + spoke + "</div>" if spoke else "")
            + "</section>")


# ── the evidence sections ───────────────────────────────────────────────────────
def sec_chart(core: dict, island: dict, deep: bool) -> str:
    body = CH.chart_html(core["sym"], core.get("name") or "", island, deep=deep)
    body += C.learn("Blue candles closed up, grey closed down — the outline keeps both readable in "
                    "either theme. The dashed lines are the institutional price zones: the average "
                    "close on the days big delivery actually happened.")
    return body


def sec_positioning(core: dict, selfref: dict) -> str:
    sig = core.get("sig")
    if not sig:
        return C.empty("No positioning signals for this symbol yet.")
    dv = _g(sig, "delivery_value_per_trade")
    rows = [("Delivery size today (DVPT)", _rupee(dv) if dv is not None else "—",
             '<span class="g-sub">rupees delivered per trade</span>'),
            ("Intensity vs its own 1-month power days",
             (_n(_g(sig, "ratio_today_vs_power_1m"), 2) + "×")
             if _g(sig, "ratio_today_vs_power_1m") is not None else "—", ""),
            ("Baselines beaten today (p / r)",
             str(_g(sig, "p_score", "—")) + " / " + str(_g(sig, "r_score", "—")),
             '<span class="g-sub">how many delivery baselines today cleared</span>'),
            ("Trigger band", str(_g(sig, "trigger_rank", "—")), ""),
            ("Accumulation character",
             str(_g(sig, "accum_character", "—")).replace("_", " ").lower(), ""),
            ("Turnover surge vs 1 month",
             (_n(_g(sig, "turnover_surge_1m"), 2) + "×")
             if _g(sig, "turnover_surge_1m") is not None else "—", "")]
    out = _kv(rows)

    # institutional key price + the gap ladder (the classic dossier's D44 block)
    kp = []
    for lab, kc, gc in (("1M", "key_price_p1m", "gap_to_key_p1m"),
                        ("3M", "key_price_p3m", "gap_to_key_p3m"),
                        ("6M", "key_price_p6m", "gap_to_key_p6m"),
                        ("12M", "key_price_p12m", "gap_to_key_p12m")):
        price, gap = _g(sig, kc), _g(sig, gc)
        if price is None and gap is None:
            continue
        kp.append((lab + " key price", "₹" + _n(price, 1) if price is not None else "—",
                   '<span class="g-sub">close is ' + esc(_pct(gap, 1, signed=True))
                   + " vs that cost line</span>" if gap is not None else ""))
    if kp:
        out += ('<div class="g-subhd">Institutional key price <span class="g-sub">value-weighted '
                "on the delivery-heavy days</span></div>" + _kv(kp))

    # institutional price zones (P-tier = where institutions transacted; R = flat baseline)
    zones = [(lab + " zone", "₹" + _n(_g(sig, col), 1), "")
             for lab, col in (("P1M", "avg_close_p1m"), ("P3M", "avg_close_p3m"),
                              ("P6M", "avg_close_p6m"), ("P12M", "avg_close_p12m"),
                              ("R12M", "avg_close_r12m")) if _g(sig, col) is not None]
    if zones:
        out += '<div class="g-subhd">Institutional price zones</div>' + _kv(zones)

    ref = (selfref or {}).get("dvpt") or {}
    tref = (selfref or {}).get("turnover") or {}
    depth = ""
    if ref.get("pctile") is not None or tref.get("pctile") is not None:
        depth = ('<div class="g-srefrow"><span class="g-lab">vs its own year</span>'
                 + (C.ref_chip(ref, unit="", dp=0, trend=ref.get("trend"), bare=True)
                    if ref.get("pctile") is not None else "")
                 + (C.ref_chip(tref, unit="", dp=0, trend=tref.get("trend"), bare=True)
                    if tref.get("pctile") is not None else "")
                 + '<span class="g-sub">delivery size · turnover, ranked inside this stock\'s own '
                   "recent history — not against other stocks</span></div>")
        out += C.pro_more(depth)
        out += C.pro_teaser(depth, cta_sub="See whether today is unusual FOR THIS STOCK",
                            advertise=True)
    out += C.learn("DVPT is the rupee value delivered per trade — big tickets, not busy tickets. "
                   "The p-score counts how many of this stock's own delivery baselines today beat.")
    return out


def sec_accumulation(core: dict) -> str:
    mep = core.get("mep")
    if not mep:
        return C.empty("No accumulation/distribution reading for this symbol yet.")
    st = _g(mep, "mep_state_smooth", "—")
    rows = [("State (smoothed)", str(st).replace("_", " ").lower(), ""),
            ("Score (smoothed)", _n(_g(mep, "mep_score_smooth"), 2), ""),
            ("Raw state", str(_g(mep, "mep_state", "—")).replace("_", " ").lower(), ""),
            ("Pressure", _n(_g(mep, "pressure"), 3), ""),
            ("Close location in the day's range", _n(_g(mep, "clv"), 3), ""),
            ("22-day drift", _n(_g(mep, "drift_22d"), 3), ""),
            ("Up/down volume, 22 days", _n(_g(mep, "updown_vol_22d"), 2), ""),
            ("As of", str(_g(mep, "trade_date", "—"))[:10], "")]
    return _kv(rows) + C.learn(
        "Delivery is side-blind, so this fuses price location, drift and up/down volume into one "
        "signed read of whether the tape looks like accumulation or distribution.")


def sec_strength(core: dict) -> str:
    sig = core.get("sig")
    if not sig:
        return C.empty("No relative-strength reading for this symbol yet.")
    rows = [("Rank in the broad universe",
             ("#" + str(_g(sig, "rs_rank"))) if _g(sig, "rs_rank") is not None else "—", "of 99"),
            ("Trend state vs the broad market",
             str(_g(sig, "rs_vs_broad_trend_state", "—")).replace("_", " ").lower(), ""),
            ("Phase", str(_g(sig, "rs_phase", "—")).replace("_", " ").lower(), ""),
            ("Above its 50-day RS average", _yn(_g(sig, "rs_vs_broad_above_50ma")), ""),
            ("Above its 200-day RS average", _yn(_g(sig, "rs_vs_broad_above_200ma")), ""),
            ("New 52-week RS high", _yn(_g(sig, "rs_vs_broad_new_52w_high")), "")]
    slopes = [(h.upper() + " slope vs broad", _n(_g(sig, "rs_vs_broad_slope_" + h), 4), "")
              for h in ("1m", "3m", "6m", "12m") if _g(sig, "rs_vs_broad_slope_" + h) is not None]
    sect = [("Trend vs its own sector",
             str(_g(sig, "rs_vs_sector_trend_state", "—")).replace("_", " ").lower(), ""),
            ("Sector", str(_g(sig, "primary_sector", "—")), "")]
    out = _kv(rows)
    if slopes:
        out += '<div class="g-subhd">How the ratio is sloping</div>' + _kv(slopes)
    out += '<div class="g-subhd">Against its own sector</div>' + _kv(sect)
    return out + C.learn(
        "Relative strength here means the stock's price ratio against the broad market. The rank is "
        "a position among peers today; the slopes say whether that position is being earned or lost.")


def sec_quality(core: dict) -> str:
    pt, ca = core.get("pt"), core.get("ca")
    if not pt and not ca:
        return C.empty("This symbol has no 14-pattern quality score yet (unscored, or a financial "
                       "— the scorer excludes some structures by design).")
    thr, mx, haircut = SR.quality_thresholds()
    out = ""
    if pt:
        checks = [(bool(_g(pt, "qg_pass")), "Quality gate",
                   "score vs threshold " + _n(thr, 1) + " / " + str(mx)),
                  (not bool(_g(pt, "hard_disqualified")), "No hard disqualifier",
                   str(_g(pt, "disqualifier_reasons") or "none recorded"))]
        out += _checks("Quality gates — the scorer's real thresholds; an unverified pattern carries "
                       "a ×" + _n(haircut, 2) + " haircut", checks)
        out += _kv([("Naked score", str(_g(pt, "ns_base", "—")) + " / 100", ""),
                    ("Pessimistic / optimistic",
                     str(_g(pt, "ns_pessimistic", "—")) + " / " + str(_g(pt, "ns_optimistic", "—")), ""),
                    ("Tier", str(_g(pt, "tier", "—")), ""),
                    ("Scored", str(_g(pt, "scored_at", "—"))[:10], "")])
    if ca:
        out += ('<div class="g-subhd">Capital allocation</div>'
                + _kv([("Tier", str(_g(ca, "ca_tier", "—")), ""),
                       ("Score", _n(_g(ca, "ca_score"), 1), "")]))
    return out + C.learn("The 14-pattern read scores a business against the patearn pattern set. It "
                         "describes what the filings show; it never sizes or times anything.")


def _checks(head: str, items) -> str:
    li = "".join('<li class="' + ("ok" if ok else "no") + '"><span class="g-mk">'
                 + ("✓" if ok else "✗") + "</span>" + esc(label)
                 + '<span class="g-sub">' + esc(detail) + "</span></li>"
                 for ok, label, detail in items)
    n = sum(1 for ok, _l, _d in items if ok)
    return ('<div class="g-checks"><div class="g-lab">' + esc(head) + " — " + str(n) + " of "
            + str(len(items)) + " met</div><ul>" + li + "</ul></div>")


def sec_structure(core: dict) -> str:
    by_tf = core.get("cpr") or {}
    if not by_tf:
        return C.empty("No pivot-structure rows for this symbol yet.")
    names = {"D": "Daily", "W": "Weekly", "M": "Monthly", "Q": "Quarterly", "H": "Half-yearly"}
    out = []
    for tf in ("D", "W", "M", "Q", "H"):
        r = by_tf.get(tf)
        if not r:
            continue
        out.append('<div class="g-subhd">' + esc(names.get(tf, tf)) + "</div>" + _kv([
            ("Pattern", str(_g(r, "pattern", "—")).replace("_", " ").lower(), ""),
            ("Central pivot", _n(_g(r, "p"), 2), ""),
            ("Band (bottom / top)", _n(_g(r, "bc"), 2) + " / " + _n(_g(r, "tc"), 2), ""),
            ("Width", _pct(_g(r, "width_pct"), 2), ""),
            # compression_pctile is stored as a 0-1 FRACTION ("fraction of trailing N widths wider
            # than now", db.py) — rendering it raw printed "0.8" under a label that says
            # percentile. Scale it once, here, the same way the classic view does.
            ("Compression percentile",
             _pct(_finite(_g(r, "compression_pctile")) * 100.0
                  if _finite(_g(r, "compression_pctile")) is not None else None, 0),
             '<span class="g-sub">how coiled this band is vs its own history</span>'),
            ("Regime", str(_g(r, "regime", "—")).replace("_", " ").lower(), ""),
            ("Period ending", str(_g(r, "period_end_date", "—"))[:10], ""),
        ]))
    return "".join(out) + C.learn(
        "The central pivot band is a width read: a narrow band says the period closed coiled, a wide "
        "one says it closed stretched. The pattern names how consecutive bands sit against each other.")


def sec_credibility(core: dict) -> str:
    cci = core.get("cci")
    if not cci:
        return C.empty("No concall credibility record for this symbol yet — the pilot covers a "
                       "subset of names.")
    return _kv([("Tier", str(_g(cci, "tier", "—")), ""),
                ("Composite score", _n(_g(cci, "composite_score"), 1), " / 100"),
                ("Credibility", _n(_g(cci, "credibility_score"), 1), ""),
                ("Guidance accuracy", _n(_g(cci, "guidance_accuracy_score"), 1),
                 '<span class="g-sub">hit-rate of the promises that have resolved</span>'),
                ("Transparency", _n(_g(cci, "transparency_score"), 1), ""),
                ("Trend", str(_g(cci, "credibility_trend", "—")).lower(), ""),
                ("Concalls read", str(_g(cci, "n_concalls", "—")), ""),
                ("Promises resolved", str(_g(cci, "n_promises_resolved", "—")), ""),
                ("As of", str(_g(cci, "as_of_period", "—")), "")]) + C.learn(
        "Credibility here is a settled record: promises made on an earnings call, checked against "
        "what later filings showed. It is a description of past follow-through, nothing more.")


def sec_setups(core: dict, xs: dict) -> str:
    """The X-setups dossier block — X-04 overnight split · X-07 volume shelves · X-09 base/breakout
    for THIS symbol, read from the nightly `x_setups_signals` snapshot. Descriptive scans."""
    sym = core["sym"]
    asof = (xs or {}).get("asof") or ""
    blocks, hits = [], 0
    bb = (xs or {}).get("base_breakout")
    if bb:
        hits += 1
        blocks.append('<div class="g-subhd">Base &amp; breakout <span class="g-sub">X-09</span></div>'
                      + _kv([("Score", _n(bb.get("x09_score"), 2),
                              '<span class="g-sub">base length × thrust</span>'),
                             ("Base length", str(bb.get("base_length", "—")) + " sessions", ""),
                             ("Base depth", _frac_pct(bb.get("base_depth"), 1),
                              '<span class="g-sub">how far it corrected off the pivot</span>'),
                             ("Breakout thrust", _frac_pct(bb.get("breakout_velocity"), 2),
                              '<span class="g-sub">realised gain above the pivot, per day</span>'),
                             ("Volume surge", _n(bb.get("vol_surge"), 2) + "×", ""),
                             ("Breakout date", str(bb.get("breakout_date", "—"))[:10],
                              '<span class="g-sub">'
                              + esc(str(bb.get("days_since_breakout", "—")) + " sessions ago")
                              + "</span>"),
                             ("Still above the pivot",
                              "yes" if bb.get("still_above_pivot") else "no", "")]))
    vs = (xs or {}).get("volume_shelves")
    if vs:
        hits += 1
        blocks.append('<div class="g-subhd">Volume shelves <span class="g-sub">X-07</span></div>'
                      + _kv([("Point of control", "₹" + _n(vs.get("poc"), 2),
                              '<span class="g-sub">the price that traded the most value</span>'),
                             ("Value area", "₹" + _n(vs.get("va_low"), 2) + " – ₹"
                              + _n(vs.get("va_high"), 2), ""),
                             ("Shelves found", str(vs.get("n_shelves", "—")), ""),
                             ("Price vs the value area", _VA_WORDS.get(
                                 str(vs.get("price_vs_va", "")),
                                 str(vs.get("price_vs_va", "—")).replace("_", " ").lower()), ""),
                             ("Last close", "₹" + _n(vs.get("last_close"), 2), "")]))
    os_ = (xs or {}).get("overnight_split")
    if os_:
        hits += 1
        blocks.append('<div class="g-subhd">Overnight vs intraday <span class="g-sub">X-04</span></div>'
                      + _kv([("Share of the move made overnight",
                              _frac_pct(os_.get("on_share"), 1), ""),
                             ("Total move over the window",
                              _frac_pct(os_.get("cum_total_pct"), 1), ""),
                             ("Flagged as an overnight pump",
                              "yes" if os_.get("overnight_pump") else "no", "")]))
    if not hits:
        body = C.empty("None of the three setup scans currently list " + esc(sym)
                       + (" (snapshot as of " + esc(asof) + ")." if asof else
                          " — the nightly setup scan has not landed in this database yet."))
    else:
        body = "".join(blocks)
    # W6 cutover: both cross-links were classic routes whose Graphite twins are now live —
    # /dash/launchpad -> the W3-A Launchpad page, /dash/seasonal-calendar -> the W2-C Seasonal
    # page's expiry view. Read-only doors, so they retarget inward like every other symbol link.
    body += ('<p class="g-sub">Cross-links: '
             + '<a href="/dash/home/strategies/launchpad?sym=' + _uq.quote(sym) + '">Launchpad</a>'
               " covers the coiled, pre-breakout half of the same family; "
             + '<a href="/dash/home/seasonal?view=calendar">expiry &amp; holiday conditioning</a> '
               "is the fourth scan and lives with the seasonal family.</p>")
    body += C.learn("These are descriptive scans of the tape: how long a base ran, where volume "
                    "actually piled up, and how much of a move happened while the market was shut. "
                    "They describe structure; none of them is a signal to act on.")
    return body


_VA_WORDS = {"in_value_area": "inside it", "above_value_area": "above it",
             "below_value_area": "below it"}


def _frac_pct(v, dp: int = 1) -> str:
    """Render an X-setups FRACTION as a percentage.

    The scan payloads store ratios, not percentages — `base_depth` = (pivot−low)/pivot,
    `on_share` = overnight ÷ total, and (despite its name) `cum_total_pct` = `expm1(Σ log-returns)`,
    i.e. 0.44 means +44%. Multiplying unconditionally is deliberate: a magnitude heuristic would
    silently under-report exactly the explosive movers this scan selects for (a +200% window is
    2.0, not 2%). NaN / None render as an em dash rather than a fabricated zero."""
    f = _finite(v)                # NaN (on_share when the move nets 0) / inf -> em dash, never 0
    if f is None:
        return "—"
    return ("%." + str(dp) + "f%%") % (f * 100.0)


# ── the own-history panel (folded from the retired stock_view lineage, W1-CONVERGENCE) ─────────
# (key, label, why, ref_chip kwargs) — the chip kwargs make the chip's "typical" render in the SAME
# unit as the Free value above it (₹ for price/turnover; a fraction scaled to % for momentum).
_SELF_ROWS = (
    ("price", "Price", "where today's close sits in its own 3-year range", {"rupee": True}),
    ("mom", "Momentum", "its 3-month return, ranked vs its own history of 3-month returns",
     {"unit": "%", "dp": 1, "scale": 100.0}),
    ("deliv", "Delivery", "delivery % (5-day smoothed) vs its own history — conviction",
     {"unit": "%", "dp": 0}),
    ("turn", "Turnover", "₹ turnover vs its own history — participation", {"rupee": True}),
    ("coil", "Coil", "daily range vs its own history — LOW = coiled, HIGH = expanded",
     {"unit": "%", "dp": 2}),
)


def _self_value(key: str, entry: dict) -> str:
    """The Free number for each own-history row, in its natural unit.

    Routed through this module's `_finite` guard rather than a bare `float()`: the retired lineage's
    formatter printed a literal "nan" for any non-finite value, and a fabricated-looking "nan" under
    a percentile label is exactly the surface dishonesty the estate's fences exist to prevent."""
    f = _finite(C._d(entry).get("today"))
    if f is None:
        return "—"
    if key == "price":
        return "₹" + _n(f, 2)
    if key == "mom":
        return ("+" if f >= 0 else "−") + _n(abs(f) * 100.0, 1) + "%"
    if key == "deliv":
        return _n(f, 0) + "%"
    if key == "turn":
        return _rupee(f)
    return _n(f, 2) + "%"


def sec_own_history(ref: dict) -> str:
    """Every number ranked against THIS stock's OWN past. Free = the number; Pro = the reference chip
    (percentile · typical). Same self-relative basis as `/dash/self-history` — method replicated, the
    module never imported (isolation gate)."""
    r = C._d(ref)
    if not r or not any(k in r for k, *_ in _SELF_ROWS):
        return C.empty("Not enough of its own history yet for a self-relative read (needs ~1 year).")
    rows = ""
    for key, label, why, kw in _SELF_ROWS:
        e = r.get(key)
        if not e:
            continue
        rows += ('<div class="g-sr-row"><div class="g-sr-l"><span class="g-sr-nm">' + esc(label)
                 + '</span><span class="g-sr-why">' + esc(why) + "</span></div>"
                 '<span class="g-sr-v g-num">' + esc(_self_value(key, e)) + "</span>"
                 '<div class="g-sr-r">' + C.ref_chip(e, **kw) + "</div></div>")
    span = ""
    if r.get("from") and r.get("to"):
        span = "%s → %s · %s sessions" % (str(r["from"])[:10], str(r["to"])[:10], r.get("n"))
    adj = (" · price & momentum are split/bonus adjusted" if r.get("adjusted") else "")
    return ('<div class="g-selfref">' + rows + "</div>"
            + '<p class="g-sr-foot">' + esc(span + adj) + "</p>"
            + C.learn("Every number here is ranked against THIS stock's own past, not against other "
                      "companies — so a ₹3,000 giant and a ₹40 small-cap read on one scale. A stock at "
                      "its own price-high on 15th-percentile turnover is a very different tape from one "
                      "making that high on 98th-percentile turnover. Descriptive of the past only."))


# ── ownership & disclosures (folded from the retired stock_view lineage, W1-CONVERGENCE) ────────
def sec_disclosures(events: dict) -> str:
    """SEBI primary-source disclosures for this name: PIT insider trades, SAST pledge events and
    Reg-29 substantial-acquisition crossings, plus the corporate actions already on the record."""
    e = C._d(events)
    ca, fil = e.get("ca") or [], e.get("filings") or []
    if not ca and not fil:
        return C.empty("No recent ownership filings or corporate actions for this name.")
    out = ""
    for r in fil[:8]:
        r = C._d(r)
        cls = (r.get("cls") or "").strip()
        dot = "pos" if cls == "pos" else ("warn" if cls == "warn" else "")
        out += ('<div class="g-fl"><span class="g-fl-dot ' + dot + '"></span>'
                '<span class="g-fl-s">' + esc(r.get("detail") or "") + "</span>"
                '<span class="g-fl-d"></span>'
                '<span class="g-fl-when g-num">' + esc((r.get("date") or "")[:10]) + "</span></div>")
    for r in ca[:8]:
        r = C._d(r)
        det = (r.get("details") or "").strip()
        lab = str(r.get("action_type") or "").title()
        if det:
            lab += " — " + det[:60]
        out += ('<div class="g-fl"><span class="g-fl-dot"></span>'
                '<span class="g-fl-s">' + esc(lab) + "</span>"
                '<span class="g-fl-d"></span>'
                '<span class="g-fl-when g-num">' + esc((r.get("ex_date") or "")[:10]) + "</span></div>")
    return ('<div class="g-filings">' + out + "</div>"
            + C.learn("These are filings, not opinions: a promoter or large holder told the exchange "
                      "what they did, and this is the dated record of it. Descriptive only."))


def sec_fno(core: dict) -> str:
    """Column names are the CANONICAL `db.SCHEMA_BASE` ones (`fut_oi`, `fut_oi_chg`, `pcr`, …) —
    pinned by tests/test_home_stock_page so a rename can never silently render em dashes here."""
    f = core.get("fno")
    if not f:
        return C.empty("No single-stock futures for this symbol.")
    rows = [("Quadrant", str(_g(f, "quadrant", "—")).replace("_", " ").lower(),
             '<span class="g-sub">today\'s price move paired with the OI move</span>'),
            ("Futures open interest", _n(_g(f, "fut_oi"), 0), ""),
            ("Change in open interest", _n(_g(f, "fut_oi_chg"), 0),
             ('<span class="g-sub">' + esc(_pct(_g(f, "fut_oi_chg_pct"), 1, signed=True))
              + " on the day</span>") if _g(f, "fut_oi_chg_pct") is not None else ""),
            ("Put / call open-interest ratio", _n(_g(f, "pcr"), 2), ""),
            ("Basis (futures vs cash)", _pct(_g(f, "basis_pct"), 2, signed=True),
             '<span class="g-sub">premium if positive, discount if negative</span>'),
            ("Max pain", _n(_g(f, "max_pain"), 1),
             '<span class="g-sub">the expiry price that pays option writers least</span>'),
            ("Put wall / call wall", _n(_g(f, "sup_strike"), 1) + " / "
             + _n(_g(f, "res_strike"), 1),
             '<span class="g-sub">strikes holding the most put / call open interest</span>'),
            ("As of", str(_g(f, "trade_date", "—"))[:10], "")]
    return _kv(rows) + C.learn(
        "Open interest says how many contracts are still open, not who is right. The quadrant pairs "
        "the price move with the OI move — a description of positioning, not a forecast. Only the "
        "put/call ratio showed any selection in the phase-0 test, and only weakly.")


# ── the context rail ────────────────────────────────────────────────────────────
def rail(core: dict, news, res, acts, peers) -> str:
    sym = core["sym"]
    out = []
    if news:
        rows = "".join('<div class="g-wrow"><a href="' + C.safe_url(n.get("url"))
                       + '" rel="noopener">' + esc(n.get("title")) + "</a>"
                       '<span class="g-sub">' + esc(n.get("source")) + " · "
                       + esc(str(n.get("sent_at") or "")[:10]) + "</span></div>"
                       for n in news[:8])
        out.append(C.zone("News for " + sym, "Newswire · 2× daily",
                          '<div class="g-wire">' + rows + "</div>", sub="symbol-tagged"))
    else:
        out.append(C.zone("News for " + sym, "Newswire · 2× daily",
                          C.empty("No symbol-tagged headlines in the recent window."),
                          sub="symbol-tagged"))
    body = ""
    if res:
        body += ('<p>' + esc(str(res.get("meeting_date") or "")[:10]) + " · "
                 + esc(res.get("purpose") or "board meeting") + "</p>")
    else:
        body += C.empty("No board meeting scheduled in the next 60 days.")
    out.append(C.zone("Next results", "Board meetings · daily", body, sub="who reports next"))
    if acts:
        body = "".join("<p>ex " + esc(str(a.get("ex_date") or "")[:10]) + " · "
                       + esc(str(a.get("action_type") or "").replace("_", " ").lower())
                       + "</p>" for a in acts)
    else:
        body = C.empty("No corporate action going ex in the next 90 days.")
    out.append(C.zone("Corporate actions", "NSE filings · daily", body, sub="dividends · splits"))
    if peers:
        chips = " ".join(glink(p["symbol"]) + ('<span class="g-sub">#'
                                               + esc(p.get("rs_rank")) + "</span>"
                                               if p.get("rs_rank") is not None else "")
                         for p in peers)
        out.append(C.zone("Peers", "stock_signals · nightly",
                          '<div class="g-peers">' + chips + "</div>"
                          + '<p class="g-sub">Same sector ('
                          + esc(peers[0].get("sector") or "") + "), strongest first. "
                          + '<a href="/dash/compare?sym=' + _uq.quote(sym) + ","
                          + _uq.quote(peers[0]["symbol"]) + '">Compare them →</a></p>',
                          sub="same sector"))
    links = [("The full charting workstation", "/dash/stock?sym=" + _uq.quote(sym)),
             ("Every metric, defined", "/dash/glossary"),
             ("What we have tested and failed", "/dash/testing"),
             ("How to read this page", "/dash/reading-guide")]
    out.append(C.zone("Go deeper", "lens registry", "".join(
        '<p><a href="' + C.safe_url(h) + '">' + esc(t) + " →</a></p>" for t, h in links),
        sub="the classic evidence"))
    return "".join(out)


# ── miss / picker states ────────────────────────────────────────────────────────
def picker() -> str:
    return (C.zone("Open a stock", "NSE bhav copy · EOD",
                   '<form method="get" action="/dash/home/stock" class="g-sform">'
                   '<label class="g-lab" for="g-symq">NSE ticker</label>'
                   '<input id="g-symq" name="sym" placeholder="e.g. TCS" autocomplete="off" '
                   'autocapitalize="characters" style="text-transform:uppercase">'
                   '<button class="g-btn" type="submit">Open</button></form>'
                   + C.learn("Every stock page opens with the same evidence in the same order: the "
                             "chart, then how it traded, then how it ranks, then what the filings "
                             "say."), sub="one symbol, all the evidence"))


def miss(sym: str, suggestions) -> str:
    body = "<p>No NSE tape for <b>" + esc(sym) + "</b> — that may not be its ticker.</p>"
    if suggestions:
        body += ('<p class="g-sub">Did you mean: '
                 + " · ".join(glink(s["symbol"]) + (" " + esc(s["name"]) if s.get("name") else "")
                              for s in suggestions) + "</p>")
    # W6 cutover: was `/dash/screen2` (classic). The Graphite screener shipped in W4, so a
    # not-found page no longer ejects the reader into the classic site to look up a ticker.
    body += ('<p><a href="/dash/home/screen">Browse the screener</a> — the ticker is in the first '
             "column.</p>")
    return C.zone("Symbol not found", "NSE bhav copy · EOD", body) + picker()


# ── the composer ────────────────────────────────────────────────────────────────
def compose(conn, sym: str, chart_deep: bool = False) -> tuple:
    """(body_html, rail_html) — always a 2-tuple, including on the not-found path."""
    core = SR.core(conn, sym)
    if core.get("bar") is None and core.get("sig") is None:
        return (miss(sym, SR.suggest(conn, sym)), "")
    island = SR.chart_island(conn, sym,
                             SR.MAX_SESSIONS if chart_deep else SR.DEFAULT_SESSIONS)
    selfref = SR.self_reference(conn, sym)
    xs = SR.x_setups(conn, sym)
    # W1-CONVERGENCE: the two folded blocks come from the market-wide read layer, which already owned
    # a per-symbol half (built for the retired lineage). Calling it here keeps that half LIVE rather
    # than letting it rot into dead code, and avoids re-implementing an adjusted 3-year percentile and
    # a three-table disclosure union that already exist and are gate-pinned.
    own = MR.stock_selfref(conn, sym)
    events = MR.stock_events(conn, sym)

    bodies = {
        "chart": sec_chart(core, island, chart_deep),
        "own": sec_own_history(own),
        "disc": sec_disclosures(events),
        "pos": sec_positioning(core, selfref),
        "mep": sec_accumulation(core),
        "rs": sec_strength(core),
        "qual": sec_quality(core),
        "cpr": sec_structure(core),
        "cci": sec_credibility(core),
        "setups": sec_setups(core, xs),
        "fno": sec_fno(core) if core.get("fno") else "",
    }
    provs = {"chart": "bhavcopy_rows · EOD", "pos": "stock_signals · nightly",
             "own": "bhavcopy_rows · 3-year self-relative",
             "disc": "SEBI PIT / SAST filings · NSE corporate actions",
             "mep": "mep_signals · nightly", "rs": "stock_signals · nightly",
             "qual": "pattern_scores · on filing", "cpr": "cpr_signals · nightly",
             "cci": "concall_scores · on concall", "setups": "x_setups_signals · nightly",
             "fno": "fno_oi_signals · nightly"}
    fences = {
        "mep": "Descriptive only — this state failed its out-of-sample gate (D62), so it describes "
               "the tape and never ranks a stock.",
        "cci": "Descriptive only — the credibility composite failed its leak-free predictive gate, "
               "so it is published as a record, never as a ranking.",
        "setups": "Descriptive only — these scans describe structure that already happened. The "
                  "closest tradeable wrapper in this family showed no edge net of cost.",
    }
    secs = []
    keys = []
    for key, title, sub, href, lab in SECTIONS:
        body = bodies.get(key) or ""
        if not body:
            continue
        keys.append(key)
        secs.append(section(key, title, sub, provs.get(key, "stock_signals · nightly"), body,
                            spoke=_spoke(href, lab, sym), fence_text=fences.get(key, "")))
    body = (identity(core, selfref) + digest(core) + narrative(core) + badges(core)
            + section_index(keys) + '<div class="g-secs">' + "".join(secs) + "</div>")
    rail_html = rail(core, SR.news_for(conn, sym), SR.results_next(sym),
                     SR.actions_for(conn, sym), SR.peers(conn, sym))
    return (body, rail_html)


CSS = """<style>/* g-stock */
:root[data-ui-g] .g-sid{margin-bottom:14px}
:root[data-ui-g] .g-sid-top{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
:root[data-ui-g] .g-sid-top h1{margin:0;font-size:30px;letter-spacing:-.4px}
:root[data-ui-g] .g-sname{color:var(--ink-2);font-size:14px}
:root[data-ui-g] .g-sprice{font-size:22px;font-weight:700}
:root[data-ui-g] .g-sday{font-weight:700;font-size:13px}
:root[data-ui-g] .g-schips{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
:root[data-ui-g] .g-schip{background:var(--bg-3);border:1px solid var(--line-2);border-radius:var(--r-pill);
  padding:3px 11px;font-size:11.5px;color:var(--ink-2)}
:root[data-ui-g] .g-schip.thm{background:var(--acc-dim);color:var(--accent);border-color:var(--accent)}
:root[data-ui-g] .g-srefs,:root[data-ui-g] .g-srefrow{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:8px}
:root[data-ui-g] .g-stiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:10px;margin:14px 0}
:root[data-ui-g] .g-stile{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:11px 13px;display:flex;flex-direction:column;gap:4px;text-decoration:none;color:var(--ink)}
:root[data-ui-g] .g-stile:hover{border-color:var(--accent);text-decoration:none}
:root[data-ui-g] .g-stile .g-big{font-size:20px}
:root[data-ui-g] .g-stile .g-ev{font:600 10px/1 var(--mono);color:var(--accent);letter-spacing:.06em}
:root[data-ui-g] .g-snarr{color:var(--ink-2);font-size:14px;margin:10px 0 6px}
:root[data-ui-g] .g-snarr .g-sub{display:block;margin-top:4px}
:root[data-ui-g] .g-sbadges{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:8px 0 14px}
:root[data-ui-g] .g-sbadge{background:var(--acc-dim);color:var(--accent);border:1px solid var(--accent);
  border-radius:var(--r-pill);padding:3px 11px;font-size:11.5px;text-decoration:none}
:root[data-ui-g] .g-sidx{position:sticky;top:96px;z-index:20;display:flex;gap:2px;flex-wrap:wrap;
  padding:7px 0;margin-bottom:12px;background:var(--bg-0);border-bottom:1px solid var(--line)}
:root[data-ui-g] .g-sidx a{padding:4px 11px;border-radius:var(--r-pill);font-size:11.5px;color:var(--ink-2);text-decoration:none}
:root[data-ui-g] .g-sidx a:hover{background:var(--acc-dim);color:var(--accent);text-decoration:none}
:root[data-ui-g] .g-sec{background:linear-gradient(165deg,var(--bg-2),var(--bg-1) 62%);
  border:1px solid var(--line);border-radius:var(--r);margin-bottom:16px;scroll-margin-top:150px;overflow:hidden}
:root[data-ui-g] .g-sec-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:11px 15px 7px}
:root[data-ui-g] .g-sec-h h2{margin:0;font-size:15px}
:root[data-ui-g] .g-sec-b{padding:2px 15px 12px;max-height:520px;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:var(--line-2) transparent}
:root[data-ui-g] .g-sec[data-sec="chart"] .g-sec-b{max-height:none;overflow:visible}
:root[data-ui-g] .g-sec-f{padding:8px 15px 12px;border-top:1px solid var(--line)}
:root[data-ui-g] .g-spoke{font-size:12px;color:var(--accent)}
:root[data-ui-g] .g-subhd{font:700 10.5px var(--font);letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3);margin:14px 0 4px;border-bottom:1px solid var(--line);padding-bottom:5px}
:root[data-ui-g] .g-kv{width:100%;border-collapse:collapse;font-size:13px}
:root[data-ui-g] .g-kv th{text-align:left;font-weight:400;color:var(--ink-2);padding:6px 8px 6px 0;
  border-bottom:1px solid var(--line);vertical-align:top}
:root[data-ui-g] .g-kv td{padding:6px 0 6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
:root[data-ui-g] .g-kv td.g-num{text-align:right;white-space:nowrap;font-weight:600}
:root[data-ui-g] .g-kv tr:last-child th,:root[data-ui-g] .g-kv tr:last-child td{border-bottom:0}
:root[data-ui-g] .g-checks{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:10px 13px;margin:10px 0}
:root[data-ui-g] .g-checks ul{list-style:none;margin:6px 0 0;padding:0}
:root[data-ui-g] .g-checks li{padding:3px 0;font-size:13px}
:root[data-ui-g] .g-checks .g-mk{display:inline-block;width:20px;font-weight:700}
:root[data-ui-g] .g-checks li.ok .g-mk{color:var(--up)}
:root[data-ui-g] .g-checks li.no .g-mk{color:var(--down)}
:root[data-ui-g] .g-checks .g-sub{margin-left:8px}
:root[data-ui-g] .g-peers{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
:root[data-ui-g] .g-sform{display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap}
:root[data-ui-g] .g-sform input{background:var(--bg-0);border:1px solid var(--line-2);color:var(--ink);
  border-radius:8px;padding:8px 12px;font:600 14px var(--font);min-width:180px}
:root[data-ui-g] .g-sform label{display:block;margin-bottom:4px}
/* W1-CONVERGENCE folds: header actions + the own-history panel (from the retired stock_view).
   The disclosures block reuses the SHARED .g-filings/.g-fl-* rules already in components.py. */
:root[data-ui-g] .g-sactions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:10px}
:root[data-ui-g] .g-sact{margin:0}
:root[data-ui-g] .g-sclassic{font-size:12px;color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap}
:root[data-ui-g] .g-sclassic:hover{text-decoration:underline}
:root[data-ui-g] .g-selfref{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
:root[data-ui-g] .g-sr-row{display:grid;grid-template-columns:1fr auto minmax(0,168px);gap:14px;align-items:center;
  padding:11px 13px;border-bottom:1px solid var(--line)}
:root[data-ui-g] .g-sr-row:last-child{border-bottom:0}
:root[data-ui-g] .g-sr-l{display:flex;flex-direction:column;gap:2px;min-width:0}
:root[data-ui-g] .g-sr-nm{font-weight:700;font-size:13.5px}
:root[data-ui-g] .g-sr-why{font-size:11px;color:var(--ink-3);line-height:1.4}
:root[data-ui-g] .g-sr-v{font-weight:800;font-size:15px;white-space:nowrap}
:root[data-ui-g] .g-sr-r{min-width:0}
:root[data-ui-g] .g-sr-r .g-refchip{margin-top:0}
:root[data-ui-g] .g-sr-foot{font-size:10.5px;color:var(--ink-3);margin:8px 0 0}
@media(max-width:720px){:root[data-ui-g] .g-sr-row{grid-template-columns:1fr auto;row-gap:8px}
  :root[data-ui-g] .g-sr-r{grid-column:1/-1}}
@media(max-width:700px){:root[data-ui-g] .g-sidx{top:0} :root[data-ui-g] .g-sec-b{max-height:420px}}
</style>"""


def head_assets() -> str:
    return CSS + CH.CSS


def _selftest() -> int:
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    body, rl = compose(conn, "NOPE")
    assert "Symbol not found" in body and "g-sform" in body and rl == ""
    # a synthetic core exercises every renderer without a DB
    core = {"sym": "TESTX", "sig": None, "bar": None, "prev": None, "mep": None, "pt": None,
            "ca": None, "cci": None, "wolfe": None, "fno": None, "cpr": {}, "name": "", "themes": []}
    assert "TESTX" in identity(core, {})
    assert "No stored signals" in digest(core)
    assert narrative(core) == "" and badges(core) == ""
    for fn in (sec_positioning, sec_accumulation, sec_strength, sec_quality, sec_structure,
               sec_credibility, sec_fno):
        out = fn(core, {}) if fn is sec_positioning else fn(core)
        assert "g-empty" in out, fn.__name__
    st = sec_setups(core, {"base_breakout": None, "volume_shelves": None,
                           "overnight_split": None, "asof": ""})
    assert "g-empty" in st and "Launchpad" in st
    # populated setups render every field
    st2 = sec_setups(core, {"base_breakout": {"symbol": "TESTX", "x09_score": 1.4, "base_length": 55,
                                              "base_depth": 0.18, "breakout_velocity": 0.021,
                                              "vol_surge": 3.2, "days_since_breakout": 4,
                                              "still_above_pivot": True, "breakout_date": "2026-07-20"},
                            "volume_shelves": {"poc": 100.5, "va_low": 90.0, "va_high": 110.0,
                                               "n_shelves": 3, "price_vs_va": "above_value_area",
                                               "last_close": 112.0},
                            "overnight_split": {"on_share": float("nan"), "cum_total_pct": 2.0,
                                                "overnight_pump": True},
                            "asof": "2026-07-24"})
    assert "X-09" in st2 and "X-07" in st2 and "X-04" in st2
    assert "18.0%" in st2 and "2.10%" in st2, "fractions render as percentages"
    assert "200.0%" in st2, "a +200% window must not be under-reported as 2%"
    assert st2.count(chr(8212)) >= 1, "a NaN share renders as an em dash, never a fabricated 0" 
    # honesty: no verdict verbs anywhere in the module's own copy (the sanctioned boundary
    # phrase "buy/sell" is stripped before the scan)
    blob = (st2 + CSS + "".join(x[2] for x in SECTIONS)).lower().replace("buy/sell", "")
    for verb in (" buy ", " sell ", " avoid ", " ride ", " fade "):
        assert verb not in blob, verb
    # links use ?sym= (never ?symbol=) and never leak a legacy/preview marker
    all_html = st2 + identity(core, {}) + digest(core) + CSS
    assert "?symbol=" not in all_html
    for m in ("pv3-", "data-ui-v3", "uk-sub", 'id="uk-main"'):
        assert m not in all_html, m
    print("home/stock_page selftest OK — empty states, setups block, sym= discipline, fence held")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
