"""src/web/home/stock_view.py — the Graphite STOCK page body (the cutover-blocking unit).

The per-symbol evidence scroll, built FROM SCRATCH in the Graphite package. It deliberately imports
NOTHING from the old preview (`stock_hub_v3` / `hub_sections_v3` / `stock_chart_v3`) or the classic
dashboard — those are `pv3-*`/legacy render modules and the isolation gate (tests/test_home_isolation)
forbids them. Only `components` (the `.g-*` kit) + `reads` (the home's own data layer).

THE SPINE IS THE REFERENCE LAYER (owner's binding principle: a number in isolation is useless — the
reference is the premium). Free gets every number, complete and honest; Pro gets each number ranked
against THIS stock's OWN ~3-year past — the same self-relative basis as `/dash/self-history`
(method replicated, module not imported). STRICTLY DESCRIPTIVE: a self-relative percentile is
context, never a signal, never advice.
"""
from __future__ import annotations

from src.web.home import components as C


def _fmt(v, dp: int = 2, suffix: str = "") -> str:
    try:
        return f"{float(v):,.{dp}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _pctxt(v) -> tuple[str, str]:
    return C._signed_pct(v) if v is not None else ("—", "")


# ── the price + delivery chart (server-computed SVG, DOM-safe, no client data) ─────────────────
_CW, _CH = 720.0, 220.0


def price_chart(series: dict) -> str:
    """Adjusted-close line + a delivery-% band underneath, drawn server-side. The close is
    corporate-action adjusted upstream (reads.stock_series), so a split/bonus never reads as a crash.
    Descriptive of the past only."""
    s = C._d(series)
    close = [float(x) for x in (s.get("close") or []) if x is not None]
    if len(close) < 5:
        return C.empty("Not enough price history to chart yet.")
    dates = s.get("dates") or []
    lo, hi = min(close), max(close)
    span = (hi - lo) or 1.0
    n = len(close)
    plot_h = _CH - 46.0                                   # leave a strip for the delivery band

    def X(i):
        return i / (n - 1) * _CW

    def Y(v):
        return 6.0 + (plot_h - 12.0) * (1.0 - (v - lo) / span)

    path = "".join(("M" if i == 0 else "L") + f"{X(i):.1f} {Y(v):.1f} " for i, v in enumerate(close))
    area = path + f"L{_CW:.1f} {plot_h:.1f} L0 {plot_h:.1f} Z"
    up = close[-1] >= close[0]
    cls = "up" if up else "dn"
    # delivery band: one thin bar per session, height = delivery % (0-100). Unsigned → neutral hue.
    dv = s.get("deliv") or []
    bars = ""
    bw = max(0.6, _CW / max(n, 1) * 0.82)
    for i, d in enumerate(dv):
        try:
            f = max(0.0, min(100.0, float(d))) / 100.0
        except (TypeError, ValueError):
            continue
        h = 30.0 * f
        bars += ('<rect class="g-sc-dv" x="%.1f" y="%.1f" width="%.2f" height="%.1f"/>'
                 % (X(i) - bw / 2, _CH - 8.0 - h, bw, h))
    first, last = (dates[0] if dates else ""), (dates[-1] if dates else "")
    axis = ('<text class="g-sc-ax" x="2" y="%.0f">%s</text>' % (_CH - 1, C.esc(str(first)[:10]))
            + '<text class="g-sc-ax" x="%.0f" y="%.0f" text-anchor="end">%s</text>'
            % (_CW - 2, _CH - 1, C.esc(str(last)[:10])))
    labs = ('<text class="g-sc-lab" x="4" y="12">%s</text>' % C.esc(_fmt(hi, 1))
            + '<text class="g-sc-lab" x="4" y="%.0f">%s</text>' % (plot_h - 2, C.esc(_fmt(lo, 1))))
    return ('<div class="g-sc"><svg viewBox="0 0 %.0f %.0f" preserveAspectRatio="none" role="img" '
            'aria-label="Price and delivery history">' % (_CW, _CH)
            + '<path class="g-sc-area ' + cls + '" d="' + area + '"/>'
            + '<path class="g-sc-line ' + cls + '" d="' + path.strip() + '"/>'
            + bars + labs + axis + "</svg></div>"
            + '<div class="g-sc-leg"><span class="pr ' + cls + '">price (split/bonus adjusted)</span>'
              '<span class="dv">delivery % per session</span>'
              "<span>" + str(n) + " sessions</span></div>")


# ── the self-relative panel: THE premium ──────────────────────────────────────────────────────
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


def _self_value(key: str, e: dict) -> str:
    """The Free number for each self-relative row, in its natural unit."""
    v = C._d(e).get("today")
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if key == "price":
        return "₹" + _fmt(f, 2)
    if key == "mom":
        return ("+" if f >= 0 else "−") + _fmt(abs(f) * 100.0, 1, "%")
    if key == "deliv":
        return _fmt(f, 0, "%")
    if key == "turn":
        return C._rupee(f)
    return _fmt(f, 2, "%")


def self_panel(ref: dict) -> str:
    """Every number ranked against this stock's OWN past. Free = the number; Pro = the reference
    chip (percentile · typical). This is the page's spine."""
    r = C._d(ref)
    if not r or not any(k in r for k, *_ in _SELF_ROWS):
        return C.empty("Not enough of its own history yet for a self-relative read (needs ~1 year).")
    rows = ""
    for key, label, why, kw in _SELF_ROWS:
        e = r.get(key)
        if not e:
            continue
        chip = C.ref_chip(e, **kw)
        rows += ('<div class="g-sr-row"><div class="g-sr-l"><span class="g-sr-nm">' + C.esc(label) + "</span>"
                 '<span class="g-sr-why">' + C.esc(why) + "</span></div>"
                 '<span class="g-sr-v g-num">' + C.esc(_self_value(key, e)) + "</span>"
                 '<div class="g-sr-r">' + chip + "</div></div>")
    span = ""
    if r.get("from") and r.get("to"):
        span = "%s → %s · %s sessions" % (str(r["from"])[:10], str(r["to"])[:10], r.get("n"))
    adj = (" · price & momentum are split/bonus adjusted" if r.get("adjusted") else "")
    return ('<div class="g-selfref">' + rows + "</div>"
            + '<p class="g-sr-foot">' + C.esc(span + adj) + "</p>"
            + C.learn("Every number here is ranked against THIS stock's own past, not against other "
                      "companies — so a ₹3,000 giant and a ₹40 small-cap read on one scale. A stock at "
                      "its own price-high on 15th-percentile turnover is a very different tape from one "
                      "making that high on 98th-percentile turnover. Descriptive of the past only."))


# ── the nightly-signal sections (delivery · strength · positioning) ───────────────────────────
def _stat(lab: str, val: str, sub: str = "", tone: str = "") -> str:
    return ('<div class="g-cell"><span class="g-lab">' + C.esc(lab) + "</span>"
            '<span class="g-big g-num ' + tone + '">' + C.esc(val) + "</span>"
            + (('<span class="g-sub">' + C.esc(sub) + "</span>") if sub else "") + "</div>")


def delivery_block(core: dict) -> str:
    """patearn's signature read: how much of the tape was actually delivered, and how that compares
    with the stock's OWN 1-month / 6-month norms (the reference, Pro)."""
    c = C._d(core)
    sig = C._d(c.get("signals"))
    today = c.get("deliv")
    n1, n6 = sig.get("avg_deliv_pct_1m"), sig.get("avg_deliv_pct_6m")
    if today is None and n1 is None:
        return C.empty("Delivery data hasn't landed for this name yet.")
    tiles = _stat("Delivery today", _fmt(today, 0, "%") if today is not None else "—",
                  "of traded value delivered")
    if n1 is not None:
        tiles += _stat("Its 1-month norm", _fmt(n1, 0, "%"), "its own recent average")
    if n6 is not None:
        tiles += _stat("Its 6-month norm", _fmt(n6, 0, "%"), "its own longer average")
    ch = sig.get("accum_character")
    if ch:
        tiles += _stat("Character", C.esc(str(ch).title()), "accumulation footprint")
    read = ""
    try:
        if today is not None and n1 is not None:
            gap = float(today) - float(n1)
            word = ("well above" if gap >= 12 else ("above" if gap >= 4 else
                    ("well below" if gap <= -12 else ("below" if gap <= -4 else "in line with"))))
            read = ('<p class="g-sr-read">Today\'s delivery is <b>' + C.esc(word)
                    + "</b> its own 1-month norm (" + C.esc(_fmt(gap, 0)) + "pt).</p>")
    except (TypeError, ValueError):
        read = ""
    pro = ""
    pw, ud = sig.get("power_dvpt_3m"), sig.get("deliv_updown_ratio_3m")
    if pw is not None or ud is not None:
        inner = '<div class="g-ctx">'
        if pw is not None:
            inner += ('<div class="g-ctx-row"><span>Power delivery (3m)</span><b class="g-num">'
                      + C.esc(C._rupee(pw)) + "</b></div>")
        if ud is not None:
            try:
                u = float(ud)
                inner += ('<div class="g-ctx-row"><span>Delivery on up-days vs down-days (3m)</span>'
                          '<b class="g-num">' + _fmt(u, 2, "×") + "</b></div>")
            except (TypeError, ValueError):
                pass
        pro = C.pro_more(inner + "</div>"
                         + '<p class="g-fd-note">Power delivery is the average of its biggest delivery '
                           "days in the window — the size of real buying it can attract. A ratio above 1 "
                           "means more delivery lands on up-days than down-days.</p>")
    return ('<div class="g-pnl">' + tiles + "</div>" + read + pro
            + C.learn("Delivery is the share of the day's traded value actually taken to the books "
                      "rather than squared off intraday — patearn's signature read on whether a move "
                      "carries holding intent."))


_PHASE_GOOD = ("LEADING", "IMPROVING", "UPTREND", "STRONG_UPTREND", "RECOVERY")
_PHASE_WEAK = ("WEAKENING", "LAGGING", "DOWNTREND", "STRONG_DOWNTREND")


def strength_block(core: dict) -> str:
    """Relative strength vs the broad market + its sector (all nightly, already computed)."""
    sig = C._d(C._d(core).get("signals"))
    if not sig:
        return C.empty("Strength signals haven't landed for this name yet.")
    rank, phase = sig.get("rs_rank"), (sig.get("rs_phase") or "")
    trend = (sig.get("rs_vs_broad_trend_state") or "").upper().strip()
    tone = "up" if trend in _PHASE_GOOD else ("dn" if trend in _PHASE_WEAK else "")
    tiles = ""
    if rank is not None:
        tiles += _stat("RS rank", "#" + _fmt(rank, 0), "across the market")
    if phase:
        tiles += _stat("Phase", str(phase).title(), "its rotation stage")
    if trend:
        tiles += _stat("Trend vs market", trend.replace("_", " ").title(), "medium-term state", tone)
    rb = sig.get("rs_vs_broad_today")
    if rb is not None:
        txt, cls = _pctxt(rb)
        tiles += _stat("vs broad market", txt, "today's relative move", cls)
    rs_sec = sig.get("rs_vs_sector_today")
    pro = ""
    if rs_sec is not None or sig.get("rsi_of_rs") is not None:
        inner = '<div class="g-ctx">'
        if rs_sec is not None:
            t2, _c2 = _pctxt(rs_sec)
            inner += ('<div class="g-ctx-row"><span>vs its own sector today</span><b class="g-num">'
                      + C.esc(t2) + "</b></div>")
        if sig.get("rsi_of_rs") is not None:
            inner += ('<div class="g-ctx-row"><span>RSI of its relative-strength line</span>'
                      '<b class="g-num">' + C.esc(_fmt(sig.get("rsi_of_rs"), 0)) + "</b></div>")
        for lab, k in (("Slope 1-month", "rs_vs_broad_slope_1m"), ("Slope 3-month", "rs_vs_broad_slope_3m"),
                       ("Slope 12-month", "rs_vs_broad_slope_12m")):
            v = sig.get(k)
            if v is not None:
                inner += ('<div class="g-ctx-row"><span>' + C.esc(lab) + '</span><b class="g-num">'
                          + C.esc(_fmt(v, 2)) + "</b></div>")
        pro = C.pro_more(inner + "</div>")
    if not tiles:
        return C.empty("Strength signals haven't landed for this name yet.")
    return ('<div class="g-pnl">' + tiles + "</div>" + pro
            + C.learn("Relative strength compares this stock's path with the broad market's: leading "
                      "means it is outpacing, lagging means the market is carrying more of the move."))


def positioning_block(core: dict) -> str:
    """Where price sits against its 52-week high and its nearby institutional price zones."""
    sig = C._d(C._d(core).get("signals"))
    if not sig:
        return C.empty("Positioning signals haven't landed for this name yet.")
    tiles = ""
    off = sig.get("pct_from_52w_high")
    if off is not None:
        try:
            f = float(off)
            tiles += _stat("From its 52-week high", ("at its high" if abs(f) < 0.05
                                                     else _fmt(abs(f), 1, "% below")),
                           "peak-to-today", "up" if abs(f) < 2 else "")
        except (TypeError, ValueError):
            pass
    for lab, kp, kg in (("Key zone · 3-month", "key_price_p3m", "gap_to_key_p3m"),
                        ("Key zone · 12-month", "key_price_p12m", "gap_to_key_p12m")):
        p, g = sig.get(kp), sig.get(kg)
        if p is None:
            continue
        sub = ""
        try:
            sub = ("%s%% away" % _fmt(abs(float(g)), 1)) if g is not None else ""
        except (TypeError, ValueError):
            sub = ""
        tiles += _stat(lab, "₹" + _fmt(p, 1), sub)
    surge = sig.get("turnover_surge_1m")
    if surge is not None:
        try:
            s = float(surge)
            tiles += _stat("Turnover vs its 1-month", _fmt(s, 1, "×"),
                           "participation today", "up" if s >= 2 else "")
        except (TypeError, ValueError):
            pass
    if not tiles:
        return C.empty("Positioning signals haven't landed for this name yet.")
    return ('<div class="g-pnl">' + tiles + "</div>"
            + C.learn("Key zones are price levels where unusually large delivery happened before — "
                      "areas the tape has already shown it cares about. Descriptive, never a target."))


def events_block(events: dict) -> str:
    """Corporate actions + ownership filings for this name."""
    e = C._d(events)
    ca, fil = e.get("ca") or [], e.get("filings") or []
    if not ca and not fil:
        return C.empty("No recent corporate actions or ownership filings for this name.")
    out = ""
    for r in fil[:8]:
        r = C._d(r)
        cls = (r.get("cls") or "").strip()
        dot = "pos" if cls == "pos" else ("warn" if cls == "warn" else "")
        out += ('<div class="g-fl"><span class="g-fl-dot ' + dot + '"></span>'
                '<span class="g-fl-s">' + C.esc(r.get("detail") or "") + "</span>"
                '<span class="g-fl-d"></span>'
                '<span class="g-fl-when g-num">' + C.esc((r.get("date") or "")[:10]) + "</span></div>")
    for r in ca[:8]:
        r = C._d(r)
        det = (r.get("details") or "").strip()
        lab = str(r.get("action_type") or "").title()
        if det:
            lab += " — " + det[:60]
        out += ('<div class="g-fl"><span class="g-fl-dot"></span>'
                '<span class="g-fl-s">' + C.esc(lab) + "</span>"
                '<span class="g-fl-d"></span>'
                '<span class="g-fl-when g-num">' + C.esc((r.get("ex_date") or "")[:10]) + "</span></div>")
    return '<div class="g-filings">' + out + "</div>"


# ── the page head (identity + actions + search) ───────────────────────────────────────────────
def _search(sym: str) -> str:
    return ('<form class="g-sc-search" method="get" action="/dash/home/stock" autocomplete="off">'
            '<input class="g-wl-in" type="text" name="sym" maxlength="24" value="' + C.esc(sym or "")
            + '" placeholder="Look up a symbol — e.g. TCS" aria-label="Look up a stock symbol" '
              'pattern="[A-Za-z0-9&.\\-]{1,24}">'
            '<button class="g-btn" type="submit">Look up</button></form>')


def head_block(core: dict) -> str:
    c = C._d(core)
    sym = c.get("symbol") or ""
    sig = C._d(c.get("signals"))
    txt, cls = _pctxt(c.get("pct"))
    sector = sig.get("primary_sector") or ""
    ind = c.get("industry") or ""
    meta = []
    if sector:
        meta.append(C.esc(sector))
    elif ind:
        meta.append(C.esc(ind) + ' <span class="g-sc-src">(Screener industry)</span>')
    if c.get("date"):
        meta.append("as of " + C.esc(str(c["date"])[:10]))
    actions = ('<form class="g-sc-act" method="post" action="/dash/home/watch/add">'
               '<input type="hidden" name="symbol" value="' + C.esc(sym) + '">'
               '<button class="g-btn" type="submit">+ Add to watchlist</button></form>'
               '<a class="g-sc-classic" href="/dash/stock?sym=' + C.esc(sym) + '">Full classic view →</a>')
    return ('<div class="g-sc-head"><div class="g-sc-id"><h2 class="g-sc-sym">' + C.esc(sym) + "</h2>"
            '<div class="g-sc-meta">' + " · ".join(meta) + "</div></div>"
            '<div class="g-sc-px"><span class="g-sc-close g-num">₹' + C.esc(_fmt(c.get("close"), 2)) + "</span>"
            '<span class="g-num ' + cls + '" style="font-weight:800;font-size:15px">' + txt + "</span></div>"
            '<div class="g-sc-actions">' + actions + "</div></div>")


def stock_page(core: dict, series: dict, ref: dict, events: dict, sym: str = "") -> str:
    """The whole Graphite stock page body. Every zone is a live read; a missing feed degrades to an
    honest empty line, never fabricated data."""
    c = C._d(core)
    if not c:
        return (C.fence("Look up any NSE cash-market symbol to see its evidence scroll.")
                + _search(sym)
                + (C.empty("No such symbol in the NSE cash market — check the spelling.") if sym else
                   C.empty("Enter a symbol above to begin.")))
    zones = C.zone("Price & delivery", "NSE bhav copy · EOD", price_chart(series),
                   sub="what the tape did", name="Chart")
    zones += C.zone("Versus its own history", "NSE bhav copy · 3-year self-relative",
                    self_panel(ref), sub="the reference that makes a number mean something",
                    name="Self-history")
    zones += C.zone("Delivery & accumulation", "Signal engine · nightly", delivery_block(core),
                    sub="was the move actually delivered?", name="Delivery")
    zones += C.zone("Relative strength", "Signal engine · nightly", strength_block(core),
                    sub="how it travels vs the market", name="Strength")
    zones += C.zone("Positioning & key zones", "Signal engine · nightly", positioning_block(core),
                    sub="where price sits", name="Positioning")
    zones += C.zone("Corporate actions & filings", "NSE · SEBI disclosures", events_block(events),
                    sub="what was disclosed", name="Events")
    return (C.fence("Everything below is descriptive of past, primary-source data (NSE · BSE · SEBI "
                    "filings). Never advice, a recommendation, or a prediction.")
            + _search(sym) + head_block(core) + zones)


CSS = """<style>/* g-stock */
:root[data-ui-g] .g-sc-search{display:flex;gap:8px;margin:0 0 14px;flex-wrap:wrap}
:root[data-ui-g] .g-sc-head{display:flex;align-items:center;gap:18px;flex-wrap:wrap;padding:14px 16px;margin-bottom:16px;
  background:linear-gradient(165deg,var(--bg-2),var(--bg-1) 62%);border:1px solid var(--line);border-radius:var(--r)}
:root[data-ui-g] .g-sc-id{flex:1;min-width:180px}
:root[data-ui-g] .g-sc-sym{margin:0;font-size:26px;font-weight:800;letter-spacing:.4px}
:root[data-ui-g] .g-sc-meta{font-size:12px;color:var(--ink-3);margin-top:3px}
:root[data-ui-g] .g-sc-src{color:var(--ink-3);font-size:10.5px}
:root[data-ui-g] .g-sc-px{display:flex;flex-direction:column;align-items:flex-end;gap:2px}
:root[data-ui-g] .g-sc-close{font-size:24px;font-weight:800}
:root[data-ui-g] .g-sc-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
:root[data-ui-g] .g-sc-act{margin:0}
:root[data-ui-g] .g-sc-classic{font-size:12px;color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap}
:root[data-ui-g] .g-sc-classic:hover{text-decoration:underline}
/* price + delivery chart */
:root[data-ui-g] .g-sc{width:100%;aspect-ratio:720/220;background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
:root[data-ui-g] .g-sc svg{width:100%;height:100%;display:block}
:root[data-ui-g] .g-sc-line{fill:none;stroke-width:1.8;stroke-linejoin:round;vector-effect:non-scaling-stroke}
:root[data-ui-g] .g-sc-line.up{stroke:var(--candle-up)} :root[data-ui-g] .g-sc-line.dn{stroke:var(--ink-3)}
:root[data-ui-g] .g-sc-area{stroke:none;opacity:.13}
:root[data-ui-g] .g-sc-area.up{fill:var(--candle-up)} :root[data-ui-g] .g-sc-area.dn{fill:var(--ink-3)}
:root[data-ui-g] .g-sc-dv{fill:var(--accent);opacity:.42}
:root[data-ui-g] .g-sc-ax,:root[data-ui-g] .g-sc-lab{fill:var(--ink-3);font:500 9px var(--mono)}
:root[data-ui-g] .g-sc-leg{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:10.5px;color:var(--ink-3)}
:root[data-ui-g] .g-sc-leg span{display:inline-flex;align-items:center;gap:5px}
:root[data-ui-g] .g-sc-leg span::before{content:"";width:11px;height:3px;border-radius:2px;background:currentColor}
:root[data-ui-g] .g-sc-leg .pr.up{color:var(--candle-up)} :root[data-ui-g] .g-sc-leg .pr.dn{color:var(--ink-3)}
:root[data-ui-g] .g-sc-leg .dv{color:var(--accent)}
/* the self-relative panel — the page's spine */
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
:root[data-ui-g] .g-sr-read{font-size:12.5px;color:var(--ink-2);margin:10px 0 0}
:root[data-ui-g] .g-sr-read b{color:var(--ink)}
@media(max-width:720px){:root[data-ui-g] .g-sr-row{grid-template-columns:1fr auto;row-gap:8px}
  :root[data-ui-g] .g-sr-r{grid-column:1/-1}}
</style>"""
