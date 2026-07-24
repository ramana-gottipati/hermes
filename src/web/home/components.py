"""src/web/home/components.py — the Graphite `.g-*` component kit (spec §4).

DOM-safe (Codex #7): every piece of text is `html.escape`d; numbers are formatted server-side;
the client-side SVG/viz reads only numeric data-* attributes (never interpolated markup). URLs pass
`safe_url` (Codex #9). No import of any preview/`*_v3` module.
"""
from __future__ import annotations

import datetime as _dt
import html as _html

_WD = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _d(r):
    """Coerce a sqlite3.Row or dict to a plain dict; {} on anything else."""
    if isinstance(r, dict):
        return r
    try:
        return dict(r)
    except (TypeError, ValueError):
        return {}


def esc(s) -> str:
    return _html.escape("" if s is None else str(s))


def safe_url(url: str) -> str:
    """Only http(s) survive; javascript:/data:/anything else collapses to '#' (M3 B1 discipline)."""
    u = ("" if url is None else str(url)).strip()
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://") or u.startswith("/"):
        return esc(u)
    return "#"


def sym_link(symbol) -> str:
    """A symbol that deep-links to its stock detail (one-way home -> classic /dash/stock)."""
    s = esc(symbol)
    return '<a class="g-syma" href="/dash/stock?sym=' + s + '">' + s + "</a>"


def _num(v, dp: int = 2) -> str:
    try:
        return f"{float(v):,.{dp}f}"
    except (TypeError, ValueError):
        return "—"


def _signed_pct(v) -> tuple[str, str]:
    """(text, cls) — cls is 'up'/'dn' (a SIGNED value: up/down colour is correct)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ("—", "")
    arrow = "▲" if f >= 0 else "▼"
    return (f"{arrow} {abs(f):.2f}%", "up" if f >= 0 else "dn")


# ── containers ──────────────────────────────────────────────────────────────────
def zone(title: str, prov_text: str, body_html: str, sub: str = "", sample: bool = False,
         name: str = None) -> str:
    """A dashboard card. `sample=True` marks the provenance chip so demo-backed zones read honestly
    (real-vs-demo line). `data-name` lets the arrange menu label a hidden/pinned card."""
    p = prov_text.split("·", 1)
    prov = _prov_html(p[0].strip(), (p[1].strip() if len(p) > 1 else ""), sample=sample)
    sub_html = f'<span class="g-sub">{esc(sub)}</span>' if sub else ""
    nm = esc(name if name is not None else title)
    return ('<section class="g-zone" data-name="' + nm + '"><div class="g-zone-h"><h2>' + esc(title) + "</h2>"
            + sub_html + prov + '</div><div class="g-zone-b">' + body_html + "</div></section>")


def card(title: str, body_html: str) -> str:
    t = f'<div class="g-card-h">{esc(title)}</div>' if title else ""
    return '<div class="g-card">' + t + body_html + "</div>"


def empty(msg: str) -> str:
    return '<p class="g-empty">' + esc(msg) + "</p>"


def fence(text: str) -> str:
    return '<p class="g-fence-top">' + esc(text) + "</p>"


def learn(text: str) -> str:
    """A beginner explainer — shown only in the 'New here' persona (Codex #3 depth)."""
    return '<p class="g-learn new-only">' + esc(text) + "</p>"


# ── atoms ─────────────────────────────────────────────────────────────────────
def tile(lab: str, big: str, sub: str = "") -> str:
    return ('<div class="g-tile"><span class="g-lab">' + esc(lab) + '</span>'
            '<span class="g-big g-num">' + esc(big) + '</span>'
            + (f'<span class="g-sub">{esc(sub)}</span>' if sub else "") + "</div>")


def _prov_html(table: str, fresh: str, stale: bool = False, sample: bool = False) -> str:
    cls = "g-prov"
    if stale:
        cls += " stale"
    if sample:
        cls += " sample"
    tail = f" · {esc(fresh)}" if fresh else ""
    smp = " · sample" if sample else ""
    return f'<span class="{cls}">{esc(table)}{tail}{smp}</span>'


def prov(table: str, fresh: str, stale: bool = False, sample: bool = False) -> str:
    return _prov_html(table, fresh, stale, sample)


def term_chip(label: str, code: str) -> str:
    """Plain-English-first (naming law): the readable label leads, the code is a mono badge."""
    return ('<span class="g-chip">' + esc(label) + '<b class="g-num">' + esc(code) + "</b></span>")


def count_tile(n, label: str, warn: bool = False) -> str:
    dot = '<span class="g-dot warn"></span>' if warn else '<span class="g-dot"></span>'
    return ('<div class="g-count"><div class="g-n g-num">' + esc(n) + "</div>"
            '<div class="g-k">' + dot + esc(label) + "</div></div>")


# ── zone 2: today / what changed ────────────────────────────────────────────────
LENS_LABELS = {
    "mep": "Delivery accumulation", "rs": "Relative strength", "dvpt": "Delivery size",
    "cci": "Concall credibility", "oi": "F&O positioning", "deal": "Bulk / block deal",
    "quality": "Quality gate", "cpr": "CPR structure",
}


def count_band(c: dict) -> str:
    return ('<div class="g-count-band">'
            + count_tile(c.get("critical", 0), "Critical", warn=True)
            + count_tile(c.get("high", 0), "High")
            + count_tile(c.get("opportunity", 0), "Opportunity")
            + count_tile(c.get("risk", 0), "Risk", warn=True) + "</div>")


def changed_rows(rows: list) -> str:
    if not rows:
        return empty("No notable state-changes fired in the last week.")
    out = ""
    for r in rows[:8]:
        lens = (r.get("lens") or "").strip()
        lbl = LENS_LABELS.get(lens, lens.upper() or "signal")
        fr, to = (r.get("from_state") or ""), (r.get("to_state") or "")
        chg = (esc(lbl) + ": " + esc(fr) + " → " + esc(to)) if (fr or to) else esc(lbl)
        code = ('<b class="g-code g-num">' + esc(lens.upper()) + "</b>") if lens else ""
        out += ('<div class="g-chrow"><span class="g-sym g-num">' + sym_link(r.get("symbol")) + "</span>"
                '<span class="g-what">' + chg + " " + code + "</span>"
                '<span class="g-when g-num">' + esc(r.get("as_of") or "") + "</span></div>")
    return '<div class="g-changed">' + out + "</div>"


# ── zone 3: FII/DII flows (net flow is a SIGNED value -> up/down colour is correct) ──
def flows_block(rows: list) -> str:
    if not rows:
        return empty("FII/DII flows haven't landed for today yet.")
    latest, asof = {}, ""
    for r in rows:
        cat = r.get("category")
        if cat not in latest and r.get("net_value") is not None:
            latest[cat] = r.get("net_value")
            asof = asof or (r.get("trade_date") or "")
    items = [("FII", latest.get("FII/FPI")), ("DII", latest.get("DII"))]
    vals = [abs(float(v)) for _, v in items if v is not None] or [1.0]
    mx = max(vals) * 1.1 or 1.0
    bars = ""
    for nm, v in items:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        pos = f >= 0
        val_txt = ("+" if pos else "−") + "₹" + f"{abs(f):,.0f}" + " cr"
        bars += ('<div class="g-frow"><span class="g-fnm">' + esc(nm) + "</span>"
                 '<div class="g-divtrack" data-net="' + f"{f:.1f}" + '" data-max="' + f"{mx:.1f}" + '">'
                 '<span class="g-mid"></span><span class="g-fbar ' + ("up" if pos else "dn") + '"></span></div>'
                 '<span class="g-fval g-num ' + ("up" if pos else "dn") + '">' + val_txt + "</span></div>")
    foot = ('<div class="g-flow-foot"><span>← net sell · net buy →</span>'
            '<span>₹ crore · cash segment · provisional · as of ' + esc(asof) + "</span></div>")
    return '<div class="g-flow">' + bars + foot + "</div>"


def spark(series: list, cls: str = "accent") -> str:
    """A sparkline container — the JS reads the numeric data-series (DOM-safe). Default tone is
    the neutral accent (a price line is not a signed delta); pass 'up'/'dn' only for signed series."""
    if not series or len(series) < 2:
        return ""
    data = ",".join(f"{float(x):.2f}" for x in series)
    tone = cls if cls in ("accent", "up", "dn") else "accent"
    return '<div class="g-spark ' + tone + '" data-series="' + data + '"></div>'


# ── zones 4/5: calendars (agenda strips) ────────────────────────────────────────
def _date_chip(iso) -> str:
    s = ("" if iso is None else str(iso))[:10]
    try:
        d = _dt.date.fromisoformat(s)
        return '<span class="g-date">' + d.strftime("%d %b") + "<small>" + _WD[d.weekday()] + "</small></span>"
    except (ValueError, TypeError):
        return '<span class="g-date">' + esc(s or "—") + "</span>"


def agenda(items: list) -> str:
    """items = list of (date_iso, symbol, desc_html). The detail sits INLINE after the symbol (no
    far-right chip -> no dead horizontal space), and a repeated date collapses to a blank chip so
    the date column reads once per day (kills the monotonous 14x '23 Jul')."""
    if not items:
        return empty("Nothing on the calendar in this window.")
    out, prev = "", None
    for date_iso, sym, desc in items:
        d = ("" if date_iso is None else str(date_iso))[:10]
        chip = _date_chip(date_iso) if d != prev else '<span class="g-date g-date-cont"></span>'
        prev = d
        out += ('<div class="g-ag">' + chip
                + '<span class="g-ag-b"><b class="g-ag-s g-num">' + sym_link(sym) + "</b> "
                '<span class="g-ag-d">' + desc + "</span></span></div>")
    return '<div class="g-agenda">' + out + "</div>"


def ca_agenda(rows: list) -> str:
    items = []
    for r in (rows or [])[:14]:
        r = _d(r)
        detail = (r.get("details") or "").strip()          # the feed's own label, e.g. "Dividend - Rs1.25"
        if not detail:                                     # bonus/split: build from the ratio
            at = (r.get("action_type") or "Action").title()
            rf, rt = r.get("ratio_from"), r.get("ratio_to")
            detail = at + ((" " + str(rf) + ":" + str(rt)) if (rf and rt) else "")
        items.append((r.get("ex_date"), r.get("symbol"), esc(detail)))
    return agenda(items)


def results_agenda(rows: list) -> str:
    items = []
    for r in (rows or [])[:14]:
        r = _d(r)
        items.append((r.get("meeting_date"), r.get("symbol"), esc((r.get("purpose") or "Results")[:56])))
    return agenda(items)


# ── zone 6: news wire (every href passes safe_url — Codex #9) ────────────────────
def wire(rows: list) -> str:
    if not rows:
        return empty("No headlines have landed yet.")
    out = ""
    for r in (rows or [])[:14]:
        r = _d(r)
        href = safe_url(r.get("url"))
        title = esc(r.get("title"))
        title_html = (('<a href="' + href + '" target="_blank" rel="noopener noreferrer">' + title + "</a>")
                      if href != "#" else title)
        out += ('<div class="g-wrow"><div class="g-wh">' + title_html + "</div>"
                '<div class="g-wm"><span class="g-wsrc">' + esc(r.get("source")) + "</span>"
                "<span>· " + esc((r.get("sent_at") or "")[:16]) + "</span></div></div>")
    return '<div class="g-wire">' + out + "</div>"


# ── zone 7: go-deeper drawers (progressive disclosure) ──────────────────────────
def drawer(title: str, code: str, summary: str, body_html: str, is_open: bool = False) -> str:
    op = " open" if is_open else ""
    codechip = ('<span class="g-code g-num">' + esc(code) + "</span>") if code else ""
    return ('<details class="g-drawer"' + op + "><summary>"
            '<span class="g-dw-t">' + esc(title) + " " + codechip + "</span>"
            '<span class="g-dw-s">' + esc(summary) + "</span>"
            '<svg class="g-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></summary>'
            '<div class="g-dw-b">' + body_html + "</div></details>")


def rowbars(items: list) -> str:
    """items = list of (label, pct 0-100, value_text)."""
    if not items:
        return empty("No data for this drawer yet.")
    out = ""
    for label, pct, val in items:
        try:
            p = max(0.0, min(100.0, float(pct)))
        except (TypeError, ValueError):
            p = 0.0
        out += ('<div class="g-rowbar"><span class="g-rb-n g-num">' + esc(label) + "</span>"
                '<span class="g-rb-t"><span class="g-rb-f" data-w="' + f"{p:.0f}" + '"></span></span>'
                '<span class="g-rb-v g-num">' + esc(val) + "</span></div>")
    return '<div class="g-rowbars">' + out + "</div>"


def delivery_drawer(leaders: list) -> str:
    ld = [_d(r) for r in (leaders or [])]
    vals = [float(r["power_dvpt_3m"]) for r in ld if r.get("power_dvpt_3m") is not None]
    if not vals:
        body = empty("No delivery-conviction leaders today.")
    else:
        mx = max(vals) or 1.0
        items = [(r.get("symbol") or "", float(r["power_dvpt_3m"]) / mx * 100, f"{float(r['power_dvpt_3m']):.1f}×")
                 for r in ld if r.get("power_dvpt_3m") is not None]
        body = (rowbars(items) + '<p class="g-note">Delivery-weighted “power” (3-month) — how much of '
                "the tape was actually delivered, scaled to the day's leader. States are neutral; colour "
                "stays reserved for signed price change.</p>")
    return drawer("Delivery & flow", "DVPT", "today's conviction leaders", body, is_open=True)


# ── zone 1 body: market pulse ───────────────────────────────────────────────────
def gauge(value, label: str = "", word: str = "") -> str:
    """The restored 0-100 semicircle gauge (the mood tile). JS fills the arc to data-value."""
    try:
        v = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        v = 0.0
    return ('<div class="g-gauge" data-value="' + f"{v:.0f}" + '" role="img" aria-label="'
            + esc(label) + " " + f"{v:.0f}" + ' of 100">'
            '<svg viewBox="0 0 140 82" preserveAspectRatio="xMidYMid meet">'
            '<path class="g-gtrack" d="M14 74 A60 60 0 0 1 126 74" fill="none" stroke-width="11" stroke-linecap="round"/>'
            '<path class="g-gfill" d="M14 74 A60 60 0 0 1 126 74" fill="none" stroke-width="11" stroke-linecap="round"/>'
            '</svg><div class="g-gword">' + esc(word) + "</div></div>")


def pulse_block(idx: list, mood: dict, mood_pct, breadth, series: list = None) -> str:
    # LEFT: compact index cards + a sparkline
    # the ribbon already carries every index value — the pulse shows ONE headline chart, not a repeat
    head = empty("Index signals pending.")
    if idx:
        r0 = idx[0]
        txt, cls = _signed_pct(r0.get("ret_1d_pct"))
        head = ('<div class="g-pl-head"><span class="g-pl-nm">' + esc(r0.get("index_name")) + "</span>"
                '<span class="g-pl-lv g-num">' + _num(r0.get("close_value")) + "</span>"
                '<span class="g-num ' + cls + '" style="font-weight:700">' + txt + "</span></div>")
    left = '<div class="g-pl-l g-pl-chart">' + head + spark(series or []) + "</div>"
    # RIGHT: the restored semicircle mood gauge + breadth (verdict-free mood; signed breadth)
    _bp = (f"{float(mood_pct):.0f}% of indices above their 200-DMA" if mood_pct else "medium-term index trend")
    gtile = ('<div class="g-mtile"><span class="g-lab">Market mood</span>'
             + gauge(mood_pct, "Market mood", mood.get("word", "No data"))
             + '<span class="g-sub">' + _bp + "</span></div>")
    if breadth and breadth.get("adv") is not None:
        adv, dec = int(breadth.get("adv") or 0), int(breadth.get("dec") or 0)
        btile = ('<div class="g-mtile"><span class="g-lab">Breadth · today</span>'
                 '<div class="g-breadth" data-adv="' + str(adv) + '" data-dec="' + str(dec) + '">'
                 '<div class="g-split"><span class="g-split-up"></span></div>'
                 '<div class="g-split-lab"><span class="up">' + str(adv) + ' adv</span>'
                 '<span class="dn">' + str(dec) + ' dec</span></div></div>'
                 '<span class="g-sub">advancers vs decliners</span></div>')
    else:
        btile = '<div class="g-mtile">' + empty("Breadth pending.") + "</div>"
    return ('<div class="g-pulse2">' + left + '<div class="g-pl-r">' + gtile + btile + "</div></div>")


def ribbon(idx: list, extra: list = None) -> str:
    """The top market ribbon — key indices + global/currency/commodity, horizontally scrollable."""
    chips = ""
    for r in (idx or [])[:4]:
        txt, cls = _signed_pct(r.get("ret_1d_pct"))
        chips += ('<span class="g-rib"><b>' + esc(r.get("index_name")) + "</b>"
                  '<span class="g-num">' + _num(r.get("close_value"), 0) + "</span>"
                  '<span class="g-num ' + cls + '">' + txt + "</span></span>")
    for e in (extra or []):
        up = float(e.get("chg", 0)) >= 0
        chips += ('<span class="g-rib"><b>' + esc(e.get("name")) + "</b>"
                  '<span class="g-num">' + esc(e.get("value")) + "</span>"
                  '<span class="g-num ' + ("up" if up else "dn") + '">'
                  + ("▲" if up else "▼") + f'{abs(float(e.get("chg", 0))):.2f}%' + "</span></span>")
    return ('<div class="g-ribbon"><span class="g-rib-live">● LIVE</span>'
            '<div class="g-rib-scroll">' + chips + "</div></div>")


# ── shared helpers for the new builders ──────────────────────────────────────────
def _sparkdiv(series, cls: str) -> str:
    """A DOM-safe sparkline: JS reads only the numeric data-series (never interpolated markup)."""
    vals = [x for x in (series or []) if x is not None]
    if len(vals) < 2:
        return ""
    return '<div class="' + cls + '" data-series="' + ",".join(f"{float(x):.3f}" for x in vals) + '"></div>'


def _col(rows, key):
    return [_d(r).get(key) for r in (rows or [])]


def _rupee(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f) >= 1e7:
        return f"₹{f / 1e7:.2f}Cr"
    if abs(f) >= 1e5:
        return f"₹{f / 1e5:.2f}L"
    return f"₹{f:,.0f}"


# ── market pulse: the instrument deck (expanded, click-to-open trends) ────────────
def _mood_tile(mood_pct, mood: dict) -> str:
    bp = (f"{float(mood_pct):.0f}% of indices above their 200-DMA" if mood_pct else "medium-term index trend")
    return ('<div class="g-cell"><span class="g-lab">Market mood</span>'
            + gauge(mood_pct, "Market mood", (mood or {}).get("word", "No data"))
            + '<span class="g-sub">' + esc(bp) + "</span></div>")


def _breadth_tile(breadth) -> str:
    b = _d(breadth)
    if b and b.get("adv") is not None:
        adv, dec = int(b.get("adv") or 0), int(b.get("dec") or 0)
        return ('<div class="g-cell"><span class="g-lab">Breadth · today</span>'
                '<div class="g-split" data-adv="' + str(adv) + '" data-dec="' + str(dec) + '"><span class="g-split-up"></span></div>'
                '<div class="g-split-lab"><span class="up">' + str(adv) + ' adv</span>'
                '<span class="dn">' + str(dec) + ' dec</span></div>'
                '<span class="g-sub">advancers vs decliners</span></div>')
    return '<div class="g-cell"><span class="g-lab">Breadth · today</span>' + empty("Breadth pending.") + "</div>"


def _deck_cell(lab, big, sub, series, exp_id, tone="", hint="trend ›") -> str:
    return ('<div class="g-cell click" data-exp="' + esc(exp_id) + '" tabindex="0" role="button">'
            '<span class="g-hint">' + esc(hint) + '</span><span class="g-lab">' + esc(lab) + "</span>"
            '<span class="g-big g-num ' + tone + '">' + esc(big) + "</span>"
            + _sparkdiv(series, "g-tspark " + tone) + '<span class="g-sub">' + esc(sub) + "</span></div>")


def _deck_static(lab, big, sub, exp_id, tone="") -> str:
    return ('<div class="g-cell click" data-exp="' + esc(exp_id) + '" tabindex="0" role="button">'
            '<span class="g-hint">detail ›</span><span class="g-lab">' + esc(lab) + "</span>"
            '<span class="g-big g-num ' + tone + '">' + esc(big) + "</span>"
            '<span class="g-sub">' + esc(sub) + "</span></div>")


def _exp(exp_id, title, series, tone, text) -> str:
    return ('<div class="g-expand" id="' + esc(exp_id) + '"><h4>' + esc(title) + "</h4>"
            + _sparkdiv(series, "g-bigspark " + tone) + "<p>" + esc(text) + "</p></div>")


def _sector_tile(sectors) -> str:
    chips = ""
    for s in (sectors or [])[:9]:
        s = _d(s)
        try:
            v = float(s.get("rs"))
        except (TypeError, ValueError):
            continue
        nm = esc((s.get("sector") or "").replace("Nifty ", "").strip() or "—")
        chips += ('<span class="g-sec"><b>' + nm + '</b><span class="' + ("up" if v >= 0 else "dn") + '">'
                  + ("+" if v >= 0 else "−") + f"{abs(v):.1f}" + "</span></span>")
    if not chips:
        return ""
    return ('<div class="g-cell wide"><span class="g-lab">Sector heat · relative strength today</span>'
            '<div class="g-heat">' + chips + "</div></div>")


def pulse_deck(idx, mood, mood_pct, breadth, series, internals, highs, sectors, vix=None) -> str:
    """The market in one glance: a headline index + a deck of internals tiles (breadth · delivery
    conviction · accumulation · 52w highs · dispersion · sector heat). Each metric tile opens its
    30-session trend. Every read is bounded; a missing feed just drops its tile."""
    head = empty("Index signals pending.")
    if idx:
        r0 = _d(idx[0])
        txt, cls = _signed_pct(r0.get("ret_1d_pct"))
        head = ('<div class="g-pl-head"><span class="g-pl-nm">' + esc(r0.get("index_name")) + "</span>"
                '<span class="g-pl-lv g-num">' + _num(r0.get("close_value")) + "</span>"
                '<span class="g-num ' + cls + '" style="font-weight:700">' + txt + "</span>"
                + _sparkdiv(series, "g-pl-spark") + "</div>")
    padv, adp = _col(internals, "pct_adv"), _col(internals, "avg_dp")
    mep, disp = _col(internals, "mep_net"), _col(internals, "disp")
    tiles = _mood_tile(mood_pct, mood) + _breadth_tile(breadth)
    if padv and padv[-1] is not None:
        tiles += _deck_cell("Breadth trend", f"{float(padv[-1]):.0f}%", "advancing · recent sessions", padv, "e-breadth", tone="up")
    if adp and adp[-1] is not None:
        tiles += _deck_cell("Delivery conviction", f"{float(adp[-1]):.0f}%", "of turnover delivered", adp, "e-deliv")
    if mep and mep[-1] is not None:
        v = float(mep[-1])
        tiles += _deck_cell("Accumulation tape", ("+" if v >= 0 else "−") + f"{abs(v):.1f}",
                            "net accumulating · MEP", mep, "e-accum", tone=("up" if v >= 0 else "dn"))
    hi = _d(highs)
    if hi and hi.get("highs") is not None:
        tiles += _deck_static("New 52-wk highs", str(int(hi.get("highs") or 0)),
                              f"{int(hi.get('near') or 0)} within 2% of high", "e-52w", tone="up")
    if disp and disp[-1] is not None:
        tiles += _deck_cell("Dispersion", f"{float(disp[-1]):.2f}", "stock-pickers' spread", disp, "e-disp", hint="what's this ›")
    v = _d(vix)
    if v and v.get("close_value") is not None:
        chg = v.get("ret_1d_pct")
        try:
            sub = ("%s%.1f%% today" % ("+" if float(chg) >= 0 else "−", abs(float(chg)))) if chg is not None else "expected swing"
        except (TypeError, ValueError):
            sub = "expected swing"
        # NEUTRAL by design: a higher VIX is a wider expected move, not a "good" or "bad" reading.
        tiles += _deck_static("Volatility · India VIX", f"{float(v['close_value']):.1f}", sub, "e-vix")
    tiles += _sector_tile(sectors)
    exps = ""
    if padv:
        exps += _exp("e-breadth", "Breadth trend — % of stocks advancing", padv, "up",
                     "The share of stocks advancing over recent sessions. A broadening tape means more names "
                     "participate, not a few index heavyweights carrying the move. Descriptive of the past only.")
    if adp:
        exps += _exp("e-deliv", "Delivery conviction — market-wide delivery %", adp, "",
                     "How much of the day's traded value was actually taken to delivery rather than squared off "
                     "intraday. A steady, high share is buying that carries holding intent — patearn's signature read.")
    if mep:
        exps += _exp("e-accum", "Accumulation tape — net MEP", mep, "up",
                     "Net accumulation across the market: positive when more stocks show a signed accumulation "
                     "footprint than distribution. A signed value, so up/down colour is meaningful here.")
    if hi and hi.get("highs") is not None:
        exps += _exp("e-52w", "New 52-week highs", None, "up",
                     "Stocks printing a fresh 52-week high today, with the count within 2% of their high — "
                     "expanding new-high leadership. When highs dry up while the index rises, that divergence shows here.")
    if v and v.get("close_value") is not None:
        exps += _exp("e-vix", "India VIX — the market's expected swing", None, "",
                     "The index of expected near-term volatility priced into Nifty options. A higher "
                     "reading means the market is paying up for a wider move — it says nothing about "
                     "direction, so it is shown neutral, never as good or bad news.")
    if disp:
        exps += _exp("e-disp", "Dispersion — how spread-out returns are", disp, "",
                     "Higher dispersion means stocks are moving quite differently from one another — a "
                     "stock-pickers' market where selection matters more than index direction. Low dispersion: everything moves together.")
    return ('<div class="g-pl-wrap">' + head
            + learn("Six instruments read the market's internals — how broad, how convicted, how accumulated the "
                    "move was, not just where the index closed. Click any tile for its trend and a plain-English read.")
            + '<div class="g-deck">' + tiles + exps + "</div></div>")


# ── the FEATURED card: your pick leads; watchlist · portfolio · index focus ───────
_TREND_LEAD = ("LEADING", "IMPROVING", "UPTREND", "STRONG_UPTREND")
_TREND_WEAK = ("WEAKENING", "LAGGING", "DOWNTREND", "STRONG_DOWNTREND")


def _wl_rows(rows) -> str:
    out = ""
    for r in (rows or [])[:10]:
        r = _d(r)
        pct = r.get("pct")
        txt, cls = _signed_pct(pct) if pct is not None else ("—", "")
        trend = (r.get("trend") or "").upper().strip()
        pc = "lead" if trend in _TREND_LEAD else ("weak" if trend in _TREND_WEAK else "")
        deliv, rank = r.get("deliv"), r.get("rank")
        tail = (f"Deliv {float(deliv):.0f}%" if deliv is not None
                else (f"RS #{int(rank)}" if rank is not None else "—"))
        out += ('<div class="g-wl"><span>' + sym_link(r.get("symbol")) + "</span>"
                '<span class="g-wl-chg g-num ' + cls + '">' + txt + "</span>"
                '<span class="g-phase ' + pc + '">' + esc(trend or "—") + "</span>"
                '<span class="g-wl-ev">' + esc(tail) + "</span></div>")
    return out


def watchlist_block(rows) -> str:
    body = _wl_rows(rows)
    if not body:
        return (empty("Your watchlist is empty.")
                + '<p class="g-wl-add"><span class="g-sub">Add names in the Tracker or via Telegram to follow them here.</span></p>')
    return ('<div class="g-watch">' + body + "</div>"
            '<p class="g-wl-add"><span class="g-sub">Followed names — day move, RS phase, delivery. Manage in the Tracker.</span></p>')


def portfolio_block(p) -> str:
    p = _d(p)
    rows = p.get("rows") or []
    if not rows:
        return empty("No holdings tracked yet — add positions in the Tracker to see your book here.")
    dp = p.get("day_pct")
    dtxt, dcls = _signed_pct(dp) if dp is not None else ("—", "")
    summ = ('<div class="g-pnl"><div class="g-cell"><span class="g-lab">Day P&amp;L</span>'
            '<span class="g-big g-num ' + dcls + '">' + dtxt + "</span></div>"
            '<div class="g-cell"><span class="g-lab">Invested</span>'
            '<span class="g-big g-num">' + _rupee(p.get("invested")) + "</span>"
            '<span class="g-sub">' + esc(str(p.get("n") or len(rows))) + " holdings</span></div></div>")
    body = ""
    for r in rows[:12]:
        r = _d(r)
        pct = r.get("pct")
        txt, cls = _signed_pct(pct) if pct is not None else ("—", "")
        wt = r.get("weight")
        wtx = f"{float(wt):.0f}% wt" if wt is not None else "—"
        since = r.get("since")
        stx = ""
        if since is not None:
            sc = "up" if since >= 0 else "dn"
            stx = ('<span class="' + sc + '">' + ("+" if since >= 0 else "−")
                   + f"{abs(float(since)):.0f}% since entry</span>")
        body += ('<div class="g-wl"><span>' + sym_link(r.get("symbol")) + "</span>"
                 '<span class="g-wl-chg g-num ' + cls + '">' + txt + "</span>"
                 '<span class="g-phase">' + esc(wtx) + "</span>"
                 '<span class="g-wl-ev">' + stx + "</span></div>")
    return summ + '<div class="g-watch">' + body + "</div>"


def index_focus_block(idx, series70) -> str:
    r0 = _d(idx[0]) if idx else {}
    lvl = _num(r0.get("close_value")) if r0 else "—"
    txt, cls = _signed_pct(r0.get("ret_1d_pct")) if r0 else ("—", "")
    above = r0.get("pct_above_200d_avg")

    def _ret(series, k):
        s = [x for x in (series or []) if x is not None]
        if len(s) > k and s[-1] and s[-k - 1]:
            return (s[-1] - s[-k - 1]) / s[-k - 1] * 100.0
        return None

    def _stat(lab, val, tone="", sub=""):
        return ('<div class="g-cell"><span class="g-lab">' + esc(lab) + '</span>'
                '<span class="g-big g-num ' + tone + '">' + esc(val) + "</span>"
                + (f'<span class="g-sub">{esc(sub)}</span>' if sub else "") + "</div>")

    def _pstat(lab, v, sub):
        if v is None:
            return _stat(lab, "—", "", sub)
        return _stat(lab, ("+" if v >= 0 else "−") + f"{abs(v):.1f}%", "up" if v >= 0 else "dn", sub)

    ab_yes = "Yes" if (above is not None and above > 0) else ("No" if above is not None else "—")
    ab_cls = "up" if (above is not None and above > 0) else ("dn" if above is not None else "")
    stats = (_stat("Above 200-DMA", ab_yes, ab_cls, "medium-term trend")
             + _pstat("1-month", _ret(series70, 21), "vs ~21 sessions")
             + _pstat("3-month", _ret(series70, 63), "vs ~63 sessions")
             + (_pstat("vs 200-DMA", above, "distance to its 200-day avg") if above is not None else _stat("From high", "—")))
    nm = esc(r0.get("index_name") or "NIFTY 50")
    head = ('<div class="g-idx-head"><span class="g-pl-nm">' + nm + "</span>"
            '<span class="g-pl-lv g-num">' + lvl + "</span>"
            '<span class="g-num ' + cls + '" style="font-weight:700">' + txt + "</span></div>")
    return head + _sparkdiv(series70, "g-bigspark idx") + '<div class="g-idx-stats">' + stats + "</div>"


def featured_card(watch_html, watch_sample, folio_html, folio_sample, index_html) -> str:
    """The user's chosen lead view. A segmented chooser promotes Watchlist / Portfolio / Index to the
    top slot (persisted per-browser by the client) — it does NOT hide the rest of the page, which
    scrolls below. Default = watchlist."""
    def _prov(sample):
        return ('<span class="g-prov sample" style="float:right">demo · sample</span>' if sample
                else '<span class="g-prov" style="float:right">your data · live</span>')
    return (
        '<section class="g-zone g-feat" data-name="Featured"><div class="g-feat-h">'
        '<div class="g-feat-ttl"><span class="g-eyebrow">★ Featured — your pick leads every visit</span>'
        '<h2 id="g-feat-title">Your watchlist</h2></div>'
        '<div class="g-featbar" role="group" aria-label="Choose your featured view">'
        '<button class="g-fb" type="button" data-v="v-watch" data-title="Your watchlist" aria-pressed="true">◈ Watchlist</button>'
        '<button class="g-fb" type="button" data-v="v-folio" data-title="Your portfolio" aria-pressed="false">Portfolio</button>'
        '<button class="g-fb" type="button" data-v="v-index" data-title="Index focus" aria-pressed="false">Index</button>'
        '<button class="g-star" id="g-feat-star" type="button" title="Make the current view your default" aria-label="Set current view as default">★</button>'
        '</div></div><div class="g-zone-b">'
        '<div class="g-featv on" id="v-watch">' + _prov(watch_sample) + watch_html + "</div>"
        '<div class="g-featv" id="v-folio">' + _prov(folio_sample) + folio_html + "</div>"
        '<div class="g-featv" id="v-index"><span class="g-prov" style="float:right">NSE indices · nightly</span>' + index_html + "</div>"
        "</div></section>"
    )


# ── the selectable ticker feed (all feeds pre-rendered DOM-safe; JS just toggles) ──
def rib_chip(name, val, pct, acc: bool = False) -> str:
    if pct is None:
        pctspan = ""
    else:
        f = float(pct)
        c = "up" if f >= 0 else "dn"
        pctspan = '<span class="g-num ' + c + '">' + ("▲" if f >= 0 else "▼") + " " + f"{abs(f):.2f}" + "%</span>"
    valspan = ('<span class="g-num">' + esc(val) + "</span>") if val is not None else ""
    b = ('<b class="acc">' + esc(name) + "</b>") if acc else ("<b>" + esc(name) + "</b>")
    return '<span class="g-rib">' + b + valspan + pctspan + "</span>"


def ribbon_feeds(feeds) -> str:
    """feeds = list of {'key','label','chips','sample'}. First is shown; a <select> toggles."""
    opts = "".join('<option value="' + esc(f["key"]) + '">' + esc(f["label"]) + "</option>" for f in feeds)
    groups = ""
    for i, f in enumerate(feeds):
        smp = '<span class="g-smp">sample</span>' if f.get("sample") else ""
        groups += ('<div class="g-rib-scroll" data-feed="' + esc(f["key"]) + '"' + ("" if i == 0 else " hidden") + ">"
                   + smp + f["chips"] + "</div>")
    return ('<div class="g-ribbon"><span class="g-rib-live">LIVE</span>'
            '<select class="g-feedpick" id="g-feedpick" aria-label="Choose ticker feed">' + opts + "</select>"
            + groups + "</div>")


def hidden_tray() -> str:
    return '<div class="g-hidden-tray" id="g-tray"></div>'


# ── the analyst's "today" additions: regime line · conviction · filings ───────────
def regime_banner(mood_word, breadth_pct, breadth_row, delivery_pct, fii_net, nifty_up) -> str:
    """One calibrated, descriptive sentence at the very top — the read an analyst wants first.
    Leads with the mood word, states the day's facts, and flags the single most salient thing to
    watch. Descriptive of the tape, never advice."""
    parts = []
    b = _d(breadth_row)
    if b and b.get("adv") is not None:
        parts.append(f"{int(b.get('adv') or 0)} advancing vs {int(b.get('dec') or 0)}")
    elif breadth_pct is not None:
        parts.append(f"breadth {float(breadth_pct):.0f}%")
    if delivery_pct is not None:
        parts.append(f"~{float(delivery_pct):.0f}% delivered")
    if nifty_up is not None:
        parts.append("Nifty above its 200-DMA" if nifty_up else "Nifty below its 200-DMA")
    watch = ""
    try:
        if fii_net is not None and float(fii_net) < 0:
            watch = " Watch: FII net sellers today."
        elif breadth_pct is not None and float(breadth_pct) < 40:
            watch = " Watch: breadth is thinning."
    except (TypeError, ValueError):
        watch = ""
    facts = ", ".join(parts)
    body = (esc(facts) + "." if facts else "") + esc(watch)
    return ('<div class="g-regime"><span class="g-regime-dot"></span>'
            '<span class="g-regime-t"><b>' + esc(mood_word or "Market") + ".</b> " + body + "</span></div>")


def conviction_block(rows) -> str:
    rows = list(rows or [])
    n = len(rows)
    if not rows:
        return empty("No names cleared all three pillars today.")
    shown = min(n, 8)
    extra = (" · top " + str(shown) + " shown") if n > shown else ""
    head = ('<p class="g-cv-count"><b class="g-num">' + str(n) + "</b> name" + ("" if n == 1 else "s")
            + " cleared all 3 pillars today" + esc(extra) + "</p>")
    out = ""
    for r in rows[:8]:
        r = _d(r)
        rank = r.get("rs_rank")
        sector = (r.get("primary_sector") or "").replace("Nifty ", "").strip()
        tags = ""
        gap = r.get("gap_to_key_p3m")
        try:
            if gap is not None and abs(float(gap)) <= 3:
                tags += '<span class="g-cv-tag near">near entry</span>'
        except (TypeError, ValueError):
            pass
        if r.get("pt14_ns") is not None and not r.get("pt14_dq"):
            tags += '<span class="g-cv-tag q">★ quality</span>'
        meta = "RS #" + (esc(rank) if rank is not None else "—") + (" · " + esc(sector) if sector else "")
        out += ('<div class="g-cv"><span class="g-cv-s">' + sym_link(r.get("symbol")) + "</span>"
                '<span class="g-cv-meta g-num">' + meta + "</span>"
                '<span class="g-cv-tags">' + tags + "</span></div>")
    return (head + '<div class="g-convw">' + out + "</div>"
            + learn("Names where all three pillars line up — a relative-strength leader, institutions "
                    "accumulating now, near a buyable entry, with quality as a ✓. Described from the data, never a recommendation."))


# ── sector canonicalisation: unify the NSE (primary_sector) + Screener (screener_industry)
#    taxonomies into ONE coarse bucket set, so 'IT' and 'Information Technology' — or 'Bank',
#    'PSU Bank' and 'Financial Services' — merge into a single heatmap block instead of duplicates.
_SECTOR_MAP = {
    "bank": "Financials", "psu bank": "Financials", "private bank": "Financials",
    "financial services": "Financials", "fin services": "Financials", "financial services ex-bank": "Financials",
    "it": "IT", "information technology": "IT",
    "auto": "Auto",
    "metal": "Metals & Mining", "commodities": "Metals & Mining", "materials": "Metals & Mining",
    "chemicals": "Chemicals",
    "realty": "Realty", "real estate": "Realty",
    "media": "Media",
    "fmcg": "FMCG & Consumer", "consumer durables": "FMCG & Consumer",
    "consumer discretionary": "FMCG & Consumer", "consumer staples": "FMCG & Consumer", "consumer": "FMCG & Consumer",
    "energy": "Energy", "oil & gas": "Energy", "utilities": "Energy",
    "healthcare": "Pharma & Health", "pharma": "Pharma & Health", "health care": "Pharma & Health",
    "infrastructure": "Industrials", "india defence": "Industrials", "industrials": "Industrials",
    "telecommunication": "Telecom", "communication services": "Telecom", "telecom": "Telecom",
    "services": "Services",
    "midcap select": "Other",                                # a size index, not a sector
}
# Substring fallback — SAFE keywords only (never a bare 'it': 'capital' contains 'it').
_SECTOR_KW = (
    ("Financials", ("bank", "financ", "insur", "nbfc", "capital market")),
    ("IT", ("software", "infotech", "info tech")),
    ("Pharma & Health", ("pharma", "health", "hospital", "medic", "life scien")),
    ("Energy", ("oil", "gas", "power", "energy", "coal", "petro", "utilit")),
    ("Auto", ("auto", "vehicle", "tyre")),
    ("Metals & Mining", ("metal", "mining", "steel", "commodit", "material")),
    ("Chemicals", ("chemical", "fertil")),
    ("FMCG & Consumer", ("consumer", "fmcg", "retail", "food", "beverage", "textile", "apparel")),
    ("Industrials", ("industri", "infra", "capital goods", "defence", "cement", "construct",
                     "engineering", "logist", "transport", "aviation", "airport")),
    ("Telecom", ("telecom", "communicat")),
    ("Realty", ("realty", "real estate")),
    ("Media", ("media", "entertain")),
    ("Services", ("service",)),
)


def _canon_sector(label) -> str:
    s = (label or "").lower().replace("nifty ", "").replace(" index", "").strip()
    if not s:
        return "Other"
    if s in _SECTOR_MAP:
        return _SECTOR_MAP[s]
    for name, keys in _SECTOR_KW:
        if any(k in s for k in keys):
            return name
    return "Other"


# ── the market heatmap: a server-computed SQUARIFIED treemap (Bruls et al.) ───────
# Computed in Python (no client layout lib, CSP-safe); tiles are absolute-positioned by percentage,
# coloured by day-move via color-mix on the signed --up/--down tokens (theme-aware). Geometry is
# gate-tested (tests/test_home_featured.py) since it can't be pixel-verified this session.
def _hm_layout(sizes, x, y, dx, dy):
    """Lay a run of areas as a single row or column inside (x,y,dx,dy). Returns rects in order."""
    rects = []
    total = sum(sizes)
    if total <= 0 or dx <= 0 or dy <= 0:
        return [{"x": x, "y": y, "dx": 0.0, "dy": 0.0} for _ in sizes]
    if dx >= dy:                                   # a row: fixed width, stacked vertically
        w = total / dy
        yy = y
        for s in sizes:
            hh = s / w if w else 0.0
            rects.append({"x": x, "y": yy, "dx": w, "dy": hh})
            yy += hh
    else:                                          # a column: fixed height, laid horizontally
        h = total / dx
        xx = x
        for s in sizes:
            ww = s / h if h else 0.0
            rects.append({"x": xx, "y": y, "dx": ww, "dy": h})
            xx += ww
    return rects


def _hm_worst(sizes, dx, dy):
    worst = 0.0
    for r in _hm_layout(sizes, 0.0, 0.0, dx, dy):
        a, b = r["dx"], r["dy"]
        if a <= 0 or b <= 0:
            return float("inf")
        worst = max(worst, a / b, b / a)
    return worst


def _squarify(sizes, x, y, dx, dy):
    """Squarified treemap. `sizes` must be pre-scaled so sum(sizes)==dx*dy and sorted DESCENDING.
    Returns one rect per size, in the same order."""
    sizes = [float(s) for s in sizes]
    if not sizes:
        return []
    if len(sizes) == 1:
        return _hm_layout(sizes, x, y, dx, dy)
    i = 1
    while i < len(sizes) and _hm_worst(sizes[:i], dx, dy) >= _hm_worst(sizes[:i + 1], dx, dy):
        i += 1
    current, remaining = sizes[:i], sizes[i:]
    row = _hm_layout(current, x, y, dx, dy)
    cov = sum(current)
    if dx >= dy:
        w = cov / dy if dy else 0.0
        rest = _squarify(remaining, x + w, y, dx - w, dy)
    else:
        h = cov / dx if dx else 0.0
        rest = _squarify(remaining, x, y + h, dx, dy - h)
    return row + rest


_HM_W, _HM_H = 1000.0, 525.0


def _hm_tile(stk, r) -> str:
    try:
        p = float(stk.get("pct"))
    except (TypeError, ValueError):
        p = 0.0
    cls = "up" if p >= 0 else "dn"
    inten = min(1.0, abs(p) / 4.0)                 # saturate the colour at ±4%
    left, top = r["x"] / _HM_W * 100, r["y"] / _HM_H * 100
    w, h = r["dx"] / _HM_W * 100, r["dy"] / _HM_H * 100
    sym = esc(stk.get("symbol"))
    title = sym + " " + ("+" if p >= 0 else "−") + f"{abs(p):.1f}%"
    label = ('<span class="g-hm-l">' + sym + "</span>") if (w >= 4.2 and h >= 4.6) else ""
    return ('<a class="g-hm-t ' + cls + '" href="/dash/stock?sym=' + sym + '" title="' + title + '" '
            'style="left:' + f"{left:.2f}" + "%;top:" + f"{top:.2f}" + "%;width:" + f"{w:.2f}"
            + "%;height:" + f"{h:.2f}" + "%;--i:" + f"{inten:.2f}" + '">' + label + "</a>")


def heatmap(rows) -> str:
    """The whole market as one treemap: sector blocks (sized by sector turnover), each subdivided into
    its stocks (sized by turnover, coloured by day-move). Descriptive of the tape, never a signal."""
    rows = [_d(r) for r in (rows or [])]
    rows = [r for r in rows if r.get("turnover")]
    if not rows:
        return empty("Market map data hasn't landed yet.")
    secs = {}
    for r in rows:
        secs.setdefault(_canon_sector(r.get("sector")), []).append(r)
    sec_list = sorted(secs.items(), key=lambda kv: sum(x["turnover"] for x in kv[1]), reverse=True)
    area = _HM_W * _HM_H
    totals = [sum(x["turnover"] for x in v) for _, v in sec_list]
    grand = sum(totals) or 1.0
    sec_rects = _squarify([t / grand * area for t in totals], 0.0, 0.0, _HM_W, _HM_H)
    tiles = ""
    for (_name, stocks), rect in zip(sec_list, sec_rects):
        stocks = sorted(stocks, key=lambda x: x["turnover"], reverse=True)
        st = [x["turnover"] for x in stocks]
        sgrand = sum(st) or 1.0
        srect_area = rect["dx"] * rect["dy"]
        st_rects = _squarify([s / sgrand * srect_area for s in st],
                             rect["x"], rect["y"], rect["dx"], rect["dy"])
        for stk, sr in zip(stocks, st_rects):
            tiles += _hm_tile(stk, sr)
    n_other = len(secs.get("Other", []))
    other_note = (" · " + str(n_other) + " unclassified") if n_other else ""
    legend = ('<div class="g-hm-leg"><span><i class="dn"></i> down</span>'
              '<span><i class="up"></i> up</span><span>tile size = turnover · '
              + str(len(rows)) + " most-traded · sectors: NSE + Screener" + other_note
              + " · click any tile</span></div>")
    return '<div class="g-hm">' + tiles + "</div>" + legend


def filings_block(rows) -> str:
    if not rows:
        return empty("No fresh ownership filings in this window.")
    out = ""
    for r in (rows or [])[:12]:
        r = _d(r)
        cls = (r.get("cls") or "").strip()
        dot = "pos" if cls == "pos" else ("warn" if cls == "warn" else "")
        out += ('<div class="g-fl"><span class="g-fl-dot ' + dot + '"></span>'
                '<span class="g-fl-s">' + sym_link(r.get("symbol")) + "</span>"
                '<span class="g-fl-d">' + esc(r.get("detail")) + "</span>"
                '<span class="g-fl-when g-num">' + esc((r.get("date") or "")[:10]) + "</span></div>")
    return '<div class="g-filings">' + out + "</div>"


# ── the REGIME band: sector-rotation RRG + breadth-vs-delivery divergence ─────────
_QCLASS = {"Leading": "q-lead", "Improving": "q-impr", "Weakening": "q-weak", "Lagging": "q-lag"}


def rrg_map(sectors) -> str:
    """Sector rotation map (JdK RRG): RS-Ratio (x) × RS-Momentum (y), centred at 100. Sectors drift
    through Leading / Improving / Weakening / Lagging; the comet TAIL is real recent history and the
    BRIGHT head is today. Server-computed SVG, DOM-safe. Quadrant colours are a 4-hue palette (not the
    signed --up/--down — quadrant is a category, not a signed value)."""
    sectors = [_d(s) for s in (sectors or []) if _d(s).get("points")]
    xs = [p[0] for s in sectors for p in s["points"] if p and p[0] is not None]
    ys = [p[1] for s in sectors for p in s["points"] if p and p[1] is not None]
    if not xs or not ys:
        return empty("Rotation data hasn't landed yet.")
    W, H = 460.0, 380.0
    m = max([abs(v - 100) for v in xs + ys] + [3.0]) * 1.14
    lo, hi = 100 - m, 100 + m

    def sx(v):
        return (v - lo) / (hi - lo) * W

    def sy(v):
        return H - (v - lo) / (hi - lo) * H

    cx, cy = sx(100.0), sy(100.0)
    quads = ('<rect class="q-lead" x="%.1f" y="0" width="%.1f" height="%.1f"/>' % (cx, W - cx, cy)
             + '<rect class="q-impr" x="0" y="0" width="%.1f" height="%.1f"/>' % (cx, cy)
             + '<rect class="q-lag" x="0" y="%.1f" width="%.1f" height="%.1f"/>' % (cy, cx, H - cy)
             + '<rect class="q-weak" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (cx, cy, W - cx, H - cy))
    cross = ('<line class="g-rrg-ax" x1="%.1f" y1="0" x2="%.1f" y2="%.1f"/>' % (cx, cx, H)
             + '<line class="g-rrg-ax" x1="0" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (cy, W, cy))
    qlab = ('<text class="g-rrg-q" x="%.0f" y="15" text-anchor="end">LEADING</text>' % (W - 7)
            + '<text class="g-rrg-q" x="7" y="15">IMPROVING</text>'
            + '<text class="g-rrg-q" x="7" y="%.0f">LAGGING</text>' % (H - 7)
            + '<text class="g-rrg-q" x="%.0f" y="%.0f" text-anchor="end">WEAKENING</text>' % (W - 7, H - 7))
    dots = ""
    for s in sectors:
        pts = [(sx(p[0]), sy(p[1])) for p in s["points"] if p and p[0] is not None and p[1] is not None]
        if len(pts) < 2:
            continue
        q = _QCLASS.get(s.get("quadrant"), "q-lag")
        k = len(pts)
        segs = ""
        for i in range(k - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            frac = (i + 1) / (k - 1)                            # 0..1, newer = higher
            is_last = (i == k - 2)                              # the connecting line to TODAY
            op = 1.0 if is_last else (0.20 + 0.6 * frac)
            w = 3.2 if is_last else (1.0 + 1.4 * frac)
            segs += ('<line class="g-rrg-seg%s" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                     'style="opacity:%.2f;stroke-width:%.1f"/>'
                     % (" last" if is_last else "", x1, y1, x2, y2, op, w))
        hx, hy = pts[-1]
        lbl, qn = esc(s.get("label")), esc(s.get("quadrant") or "")
        dots += ('<g class="g-rrg-s ' + q + '" tabindex="0" role="img" aria-label="' + lbl + ': ' + qn + '">'
                 + segs
                 + '<circle class="g-rrg-head" cx="%.1f" cy="%.1f" r="4.8"/>' % (hx, hy)
                 + '<text class="g-rrg-lbl" x="%.1f" y="%.1f">%s</text>' % (hx + 6, hy + 3, lbl)
                 + "</g>")
    leg = ('<div class="g-rrg-leg"><span class="q-lead">Leading</span><span class="q-impr">Improving</span>'
           '<span class="q-weak">Weakening</span><span class="q-lag">Lagging</span>'
           '<span class="g-rrg-note">bright dot = today · tail ≈ 8 weeks (weekly steps) · vs Nifty 500</span></div>')
    return ('<div class="g-rrg"><svg viewBox="0 0 460 380" preserveAspectRatio="xMidYMid meet" '
            'role="img" aria-label="Sector rotation map (RRG)">' + quads + cross + qlab + dots + "</svg></div>" + leg)


def breadth_divergence_chart(rows) -> str:
    """Price-breadth (% of stocks advancing) vs EFFORT-breadth (% showing net accumulation effort)
    over recent sessions — the GAP is the regime read. Server-computed SVG; today's point marked."""
    rows = [_d(r) for r in (rows or []) if _d(r).get("price") is not None]
    if len(rows) < 2:
        return empty("Breadth history hasn't landed yet.")
    W, H = 460.0, 200.0
    n = len(rows)

    def X(i):
        return i / (n - 1) * W

    def Y(v):
        return H - max(0.0, min(100.0, float(v))) / 100.0 * H

    price = [(X(i), Y(r["price"])) for i, r in enumerate(rows)]
    have_eff = all(r.get("effort") is not None for r in rows)
    eff = [(X(i), Y(r["effort"])) for i, r in enumerate(rows)] if have_eff else []
    fill = ""
    if eff:
        fwd = " ".join("%.1f,%.1f" % p for p in price)
        bwd = " ".join("%.1f,%.1f" % p for p in reversed(eff))
        fill = '<polygon class="g-bd-gap" points="%s %s"/>' % (fwd, bwd)

    def _pl(points, cls):
        return '<polyline class="%s" points="%s"/>' % (cls, " ".join("%.1f,%.1f" % p for p in points))

    mid = '<line class="g-bd-mid" x1="0" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (Y(50), W, Y(50))
    dots = '<circle class="g-bd-dot price" cx="%.1f" cy="%.1f" r="3.6"/>' % price[-1]
    if eff:
        dots += '<circle class="g-bd-dot eff" cx="%.1f" cy="%.1f" r="3.6"/>' % eff[-1]
    svg = ('<div class="g-bd"><svg viewBox="0 0 460 200" preserveAspectRatio="xMidYMid meet" '
           'role="img" aria-label="Breadth vs delivery">' + fill + mid + _pl(price, "g-bd-price")
           + (_pl(eff, "g-bd-eff") if eff else "") + dots + "</svg></div>")
    leg = ('<div class="g-bd-leg"><span class="price">Price-breadth · % advancing</span>'
           '<span class="eff">Effort-breadth · delivery/MEP</span></div>')
    last = rows[-1]
    read = ""
    if last.get("effort") is not None:
        pv, ev = float(last["price"]), float(last["effort"])
        gap = pv - ev
        verb = ("advancing on thin delivery" if gap > 8 else
                ("delivery leading price" if gap < -8 else "delivery keeping pace with price"))
        read = ('<p class="g-bd-read"><b>Today:</b> ' + esc(f"{pv:.0f}% advancing vs {ev:.0f}% delivering")
                + " — " + esc(verb) + ".</p>")
    return svg + leg + read


def regime_band(rrg_html, breadth_html, rrg_sample: bool = False, bd_sample: bool = False) -> str:
    """The 'bigger picture' band, placed BELOW the today-core (owner call): multi-week rotation +
    multi-day breadth trend, fenced as regime CONTEXT — never today's change (today's point is marked
    on each). Full-width, two cards side by side."""
    def _chip(s):
        return ('<span class="g-prov sample">demo · sample</span>' if s
                else '<span class="g-prov">live · nightly</span>')
    fence = ('<p class="g-fence-top">The bigger picture — multi-week sector rotation and the multi-day '
             "breadth trend. This is regime CONTEXT, not today's change; each marks where things stand today.</p>")
    return ('<section class="g-rband"><div class="g-rband-h"><h2>Market regime — the bigger picture</h2>'
            '<span class="g-sub">rotation &amp; breadth over time</span></div>' + fence
            + '<div class="g-rband-grid">'
            '<div class="g-rband-card"><div class="g-rband-ch"><h3>Sector rotation · RRG</h3>' + _chip(rrg_sample)
            + "</div>" + rrg_html + "</div>"
            '<div class="g-rband-card"><div class="g-rband-ch"><h3>Breadth vs delivery</h3>' + _chip(bd_sample)
            + "</div>" + breadth_html + "</div></div></section>")


# ── the .g-* stylesheet (scoped by data-ui-g on the root, via the token layer) ──
def css() -> str:
    return """<style>/* g-kit */
:root[data-ui-g] .g-zone{background:linear-gradient(165deg,var(--bg-2),var(--bg-1) 62%);
  border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin-bottom:16px;position:relative}
:root[data-ui-g] .g-zone::before{content:"";position:absolute;inset:0 auto auto 0;width:44px;height:2px;
  background:linear-gradient(90deg,var(--accent-hi),transparent)}
:root[data-ui-g] .g-zone-h{display:flex;align-items:center;gap:10px;padding:10px 14px 7px;flex-wrap:wrap}
:root[data-ui-g] .g-zone-h h2{margin:0;font-size:15px;font-weight:700}
:root[data-ui-g] .g-sub{font-size:12px;color:var(--ink-3)}
:root[data-ui-g] .g-zone-b{padding:2px 14px 12px}
:root[data-ui-g] .g-prov{margin-left:auto;font:600 10px/1 var(--mono);color:var(--ink-3);background:var(--bg-0);
  border:1px solid var(--line);border-radius:var(--r-pill);padding:4px 9px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
:root[data-ui-g] .g-prov::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--accent)}
:root[data-ui-g] .g-prov.stale::before{background:var(--warn)}
:root[data-ui-g] .g-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px}
:root[data-ui-g] .g-card-h{font-weight:700;margin-bottom:8px}
:root[data-ui-g] .g-empty{color:var(--ink-3);font-size:13px;margin:8px 0}
:root[data-ui-g] .g-fence-top{font-size:12px;color:var(--ink-2);margin:0 0 18px;padding:9px 13px;
  border:1px solid var(--line-2);border-left:2px solid var(--accent);border-radius:0 8px 8px 0;background:var(--acc-dim)}
:root[data-ui-g] .g-tile{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:13px 14px;display:flex;flex-direction:column;gap:5px}
:root[data-ui-g] .g-lab{font:600 10px/1 var(--font);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-big{font-size:26px;font-weight:700;line-height:1}
:root[data-ui-g] .g-chip{display:inline-flex;align-items:center;gap:6px;background:var(--bg-3);border:1px solid var(--line-2);
  border-radius:var(--r-pill);padding:4px 6px 4px 11px;font-size:12px;color:var(--ink)}
:root[data-ui-g] .g-chip b{font:600 10px/1 var(--mono);color:var(--accent);background:var(--acc-dim);border-radius:var(--r-pill);padding:3px 6px}
:root[data-ui-g] .g-count{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:8px 10px}
:root[data-ui-g] .g-n{font-size:20px;font-weight:700;line-height:1}
:root[data-ui-g] .g-k{font-size:11px;color:var(--ink-3);margin-top:3px}
:root[data-ui-g] .g-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-right:5px;vertical-align:middle}
:root[data-ui-g] .g-dot.warn{background:var(--warn)}
:root[data-ui-g] .g-pulse{display:flex;flex-direction:column;gap:14px}
:root[data-ui-g] .g-icards{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}
:root[data-ui-g] .g-icard{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px}
:root[data-ui-g] .g-nm{font:700 11px var(--font);letter-spacing:.05em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-lv{font-size:22px;font-weight:700;line-height:1.15}
:root[data-ui-g] .g-ch{font-weight:700;font-size:12.5px}
:root[data-ui-g] .g-ch.up,:root[data-ui-g] .up{color:var(--up)}
:root[data-ui-g] .g-ch.dn,:root[data-ui-g] .dn{color:var(--down)}
:root[data-ui-g] .g-mood{display:flex;align-items:baseline;gap:8px;font-size:14px;flex-wrap:wrap}
:root[data-ui-g] .g-mood .g-sub{flex-basis:100%;color:var(--ink-2)}
:root[data-ui-g] .g-split{height:12px;border-radius:999px;overflow:hidden;background:var(--bg-3);display:flex}
:root[data-ui-g] .g-split-up{height:100%;width:0;background:var(--up);transition:width 1s cubic-bezier(.2,.7,.2,1)}
:root[data-ui-g] .g-split-lab{display:flex;justify-content:space-between;margin-top:5px;font:600 11px var(--mono)}
:root[data-ui-g] .g-as{font-size:10.5px;color:var(--ink-3);margin-top:4px}
:root[data-ui-g] .g-btn{background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink);border-radius:8px;
  padding:8px 14px;font:600 13px var(--font);cursor:pointer;margin-top:8px}
:root[data-ui-g] .g-btn:hover{border-color:var(--accent)}
:root[data-ui-g] .g-count-band{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:560px){:root[data-ui-g] .g-count-band{grid-template-columns:repeat(2,1fr)}}
:root[data-ui-g] .g-changed{display:flex;flex-direction:column;margin-top:14px}
:root[data-ui-g] .g-chrow{display:grid;grid-template-columns:74px 1fr auto;gap:12px;align-items:center;padding:6px 2px;border-bottom:1px solid var(--line);font-size:12.5px}
:root[data-ui-g] .g-chrow:last-child{border-bottom:0}
:root[data-ui-g] .g-sym{font-weight:700;font-size:12.5px}
:root[data-ui-g] .g-what{color:var(--ink-2)}
:root[data-ui-g] .g-code{font:600 9.5px/1 var(--mono);color:var(--accent);background:var(--acc-dim);border-radius:var(--r-pill);padding:2px 6px;margin-left:4px}
:root[data-ui-g] .g-when{font-size:11px;color:var(--ink-3);text-align:right}
:root[data-ui-g] .g-flow{display:flex;flex-direction:column;gap:12px;margin-top:4px}
:root[data-ui-g] .g-frow{display:grid;grid-template-columns:44px 1fr 112px;gap:12px;align-items:center}
:root[data-ui-g] .g-fnm{font-weight:700;font-size:12.5px;color:var(--ink-2)}
:root[data-ui-g] .g-divtrack{position:relative;height:18px;background:var(--bg-0);border:1px solid var(--line);border-radius:6px;overflow:hidden}
:root[data-ui-g] .g-mid{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--line-2)}
:root[data-ui-g] .g-fbar{position:absolute;top:2px;bottom:2px;width:0;border-radius:4px;transition:width 1s cubic-bezier(.2,.7,.2,1)}
:root[data-ui-g] .g-fbar.up{background:var(--up)}
:root[data-ui-g] .g-fbar.dn{background:var(--down)}
:root[data-ui-g] .g-fval{font-family:var(--mono);font-weight:700;font-size:12.5px;text-align:right}
:root[data-ui-g] .g-fval.up{color:var(--up)}
:root[data-ui-g] .g-fval.dn{color:var(--down)}
:root[data-ui-g] .g-flow-foot{display:flex;justify-content:space-between;gap:10px;font-size:11px;color:var(--ink-3);margin-top:2px;flex-wrap:wrap}
:root[data-ui-g] .g-spark{height:38px;margin-top:2px;color:var(--accent)}
:root[data-ui-g] .g-spark.up{color:var(--up)}
:root[data-ui-g] .g-spark.dn{color:var(--down)}
:root[data-ui-g] .g-spark svg{width:100%;height:38px;display:block}
:root[data-ui-g] .g-agenda{display:flex;flex-direction:column}
:root[data-ui-g] .g-ag{display:flex;align-items:baseline;gap:12px;padding:8px 2px;border-bottom:1px solid var(--line)}
:root[data-ui-g] .g-date-cont{border-color:transparent!important;background:transparent!important;color:transparent}
:root[data-ui-g] .g-ag:last-child{border-bottom:0}
:root[data-ui-g] .g-date{font:700 11px/1.25 var(--mono);color:var(--ink);background:var(--bg-0);border:1px solid var(--line-2);border-radius:7px;padding:5px 8px;text-align:center;min-width:54px}
:root[data-ui-g] .g-date small{display:block;font-size:9px;color:var(--ink-3);font-weight:500}
:root[data-ui-g] .g-ag-b{min-width:0;font-size:13px}
:root[data-ui-g] .g-ag-s{font-weight:700;font-size:12.5px}
:root[data-ui-g] .g-ag-d{color:var(--ink-2)}
:root[data-ui-g] .g-kind{font:600 10px/1 var(--mono);color:var(--ink-3);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:3px 8px;white-space:nowrap}
:root[data-ui-g] .g-wire{display:flex;flex-direction:column}
:root[data-ui-g] .g-wrow{padding:7px 2px;border-bottom:1px solid var(--line)}
:root[data-ui-g] .g-wrow:last-child{border-bottom:0}
:root[data-ui-g] .g-wh{font-size:13px;color:var(--ink);line-height:1.4}
:root[data-ui-g] .g-wm{display:flex;gap:8px;margin-top:5px;font-size:11px;color:var(--ink-3);flex-wrap:wrap}
:root[data-ui-g] .g-wsrc{font-weight:600;color:var(--ink-2)}
:root[data-ui-g] .g-drawer{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin-bottom:12px}
:root[data-ui-g] .g-drawer summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:12px;padding:13px 16px}
:root[data-ui-g] .g-drawer summary::-webkit-details-marker{display:none}
:root[data-ui-g] .g-dw-t{font-weight:700;font-size:14px}
:root[data-ui-g] .g-dw-s{font-size:12px;color:var(--ink-3)}
:root[data-ui-g] .g-chev{margin-left:auto;width:20px;height:20px;color:var(--ink-3);transition:transform .2s ease}
:root[data-ui-g] .g-drawer[open] .g-chev{transform:rotate(180deg)}
:root[data-ui-g] .g-dw-b{padding:2px 16px 16px;border-top:1px solid var(--line)}
:root[data-ui-g] .g-rowbars{display:flex;flex-direction:column;gap:9px;margin-top:12px}
:root[data-ui-g] .g-rowbar{display:grid;grid-template-columns:104px 1fr 56px;gap:12px;align-items:center;font-size:12.5px}
:root[data-ui-g] .g-rb-n{font-weight:600;color:var(--ink-2)}
:root[data-ui-g] .g-rb-t{height:9px;background:var(--bg-3);border-radius:var(--r-pill);overflow:hidden}
:root[data-ui-g] .g-rb-f{display:block;height:100%;width:0;border-radius:var(--r-pill);background:linear-gradient(90deg,var(--accent),var(--accent-hi));transition:width 1s cubic-bezier(.2,.7,.2,1)}
:root[data-ui-g] .g-rb-v{font-family:var(--mono);text-align:right;color:var(--ink-2)}
:root[data-ui-g] .g-note{font-size:12px;color:var(--ink-3);margin-top:12px;line-height:1.5}
:root[data-ui-g] .g-learn{font-size:12px;color:var(--ink-2);margin-top:9px;line-height:1.5;padding:8px 10px;background:var(--acc-dim);border-left:2px solid var(--accent);border-radius:0 8px 8px 0}
:root[data-ui-g] .g-learn b{color:var(--ink)}
:root[data-ui-g] .g-pulse2{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:14px}
@media(max-width:720px){:root[data-ui-g] .g-pulse2{grid-template-columns:minmax(0,1fr)}}
:root[data-ui-g] .g-pl-l{display:flex;flex-direction:column;gap:10px}
:root[data-ui-g] .g-pl-r{display:grid;grid-template-rows:1fr 1fr;gap:10px}
:root[data-ui-g] .g-mtile{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px;display:flex;flex-direction:column;gap:6px}
:root[data-ui-g] .g-mtile .g-sub{color:var(--ink-2)}
:root[data-ui-g] .g-gauge{position:relative;width:100%;max-width:170px;margin:2px auto 0}
:root[data-ui-g] .g-gauge svg{width:100%;height:auto;display:block}
:root[data-ui-g] .g-gtrack{stroke:var(--bg-3)}
:root[data-ui-g] .g-gfill{stroke:var(--accent)}
:root[data-ui-g] .g-gword{position:absolute;left:0;right:0;bottom:6px;text-align:center;font-weight:700;font-size:16px;color:var(--ink);text-shadow:0 0 16px var(--glow)}
:root[data-ui-g] .g-row2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;align-items:start}
@media(max-width:820px){:root[data-ui-g] .g-row2{grid-template-columns:1fr}}
:root[data-ui-g] .g-row2 .g-zone{margin-bottom:0}
/* fixed-size boxes that scroll internally (owner directive) — never a flat endless page */
:root[data-ui-g] .g-agenda,:root[data-ui-g] .g-wire,:root[data-ui-g] .g-changed{max-height:300px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--line-2) transparent;padding-right:4px}
:root[data-ui-g] .g-agenda::-webkit-scrollbar,:root[data-ui-g] .g-wire::-webkit-scrollbar,:root[data-ui-g] .g-changed::-webkit-scrollbar{width:8px}
:root[data-ui-g] .g-agenda::-webkit-scrollbar-thumb,:root[data-ui-g] .g-wire::-webkit-scrollbar-thumb,:root[data-ui-g] .g-changed::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:8px}
:root[data-ui-g] .g-agenda::-webkit-scrollbar-track,:root[data-ui-g] .g-wire::-webkit-scrollbar-track,:root[data-ui-g] .g-changed::-webkit-scrollbar-track{background:transparent}
/* the 2-region dashboard: main column (pulse + news hero) | sidebar of widgets */
:root[data-ui-g] .g-ribbon{display:flex;align-items:center;gap:14px;padding:9px 14px;background:var(--bg-1);border:1px solid var(--line);border-radius:var(--r);margin-bottom:16px}
:root[data-ui-g] .g-rib-live{font:700 10px/1 var(--font);letter-spacing:.14em;color:var(--acc);flex:none}
:root[data-ui-g] .g-rib-scroll{display:flex;gap:22px;overflow-x:auto;scrollbar-width:none;min-width:0}
:root[data-ui-g] .g-rib-scroll::-webkit-scrollbar{display:none}
:root[data-ui-g] .g-rib{display:inline-flex;align-items:baseline;gap:6px;font-size:12px;white-space:nowrap}
:root[data-ui-g] .g-rib b{font-weight:700}
:root[data-ui-g] .g-rib .g-num{color:var(--ink-2)}
:root[data-ui-g] .g-rib .up{color:var(--up)}
:root[data-ui-g] .g-rib .dn{color:var(--down)}
:root[data-ui-g] .g-dash{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:16px;align-items:start}
@media(max-width:860px){:root[data-ui-g] .g-dash{grid-template-columns:minmax(0,1fr)}}
:root[data-ui-g] .g-main,:root[data-ui-g] .g-side{display:flex;flex-direction:column;gap:16px;min-width:0}
:root[data-ui-g] .g-main>.g-zone,:root[data-ui-g] .g-side>.g-zone{margin-bottom:0}
:root[data-ui-g] .g-main .g-wire{max-height:440px}
:root[data-ui-g] .g-syma{color:inherit;text-decoration:none}
:root[data-ui-g] .g-syma:hover{color:var(--accent);text-decoration:underline}
:root[data-ui-g] .g-pl-head{display:flex;align-items:baseline;gap:10px}
:root[data-ui-g] .g-pl-nm{font:700 12px var(--font);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-pl-lv{font-size:22px;font-weight:700;text-shadow:0 0 18px var(--glow)}
:root[data-ui-g] .g-pl-chart .g-spark{height:96px}
/* ── featured card + chooser ── */
:root[data-ui-g] .g-feat{border-color:color-mix(in srgb,var(--accent) 40%,var(--line));background:linear-gradient(165deg,color-mix(in srgb,var(--accent) 7%,var(--bg-2)),var(--bg-1) 66%);box-shadow:0 0 34px -18px var(--glow)}
:root[data-ui-g] .g-feat::before{width:100%;background:linear-gradient(90deg,var(--accent-hi),transparent 60%)}
:root[data-ui-g] .g-feat-h{display:flex;align-items:center;gap:12px 14px;padding:12px 15px 10px;flex-wrap:wrap}
:root[data-ui-g] .g-feat-ttl{display:flex;flex-direction:column;gap:2px;margin-right:auto;min-width:0}
:root[data-ui-g] .g-eyebrow{font:700 9px/1 var(--mono);letter-spacing:.16em;color:var(--accent);text-transform:uppercase}
:root[data-ui-g] .g-feat-ttl h2{margin:0;font-size:17px;font-weight:800}
:root[data-ui-g] .g-featbar{display:inline-flex;align-items:center;gap:2px;background:var(--bg-0);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:3px}
:root[data-ui-g] .g-fb{border:0;background:transparent;color:var(--ink-3);font:700 11.5px var(--font);padding:7px 13px;border-radius:var(--r-pill);cursor:pointer;white-space:nowrap}
:root[data-ui-g] .g-fb[aria-pressed="true"]{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .g-fb:hover:not([aria-pressed="true"]){color:var(--ink)}
:root[data-ui-g] .g-star{border:0;background:transparent;color:var(--ink-3);cursor:pointer;font-size:15px;line-height:1;padding:5px 7px;border-radius:var(--r-pill)}
:root[data-ui-g] .g-star.set{color:var(--warn)}
:root[data-ui-g] .g-featv{display:none}
:root[data-ui-g] .g-featv.on{display:block}
:root[data-ui-g] .g-pnl{display:flex;gap:11px;flex-wrap:wrap;margin-bottom:12px}
:root[data-ui-g] .g-pnl .g-cell{flex:1;min-width:120px}
/* ── watchlist / portfolio rows ── */
:root[data-ui-g] .g-watch{display:flex;flex-direction:column;max-height:320px;overflow-y:auto;scrollbar-width:thin}
:root[data-ui-g] .g-wl{display:grid;grid-template-columns:minmax(78px,96px) 74px 88px 1fr;gap:10px;align-items:center;padding:9px 4px;border-bottom:1px solid var(--line);font-size:13px}
:root[data-ui-g] .g-wl:last-child{border-bottom:0}
:root[data-ui-g] .g-wl-chg{font-weight:700;text-align:right}
:root[data-ui-g] .g-phase{font:600 9.5px/1 var(--mono);letter-spacing:.03em;border-radius:var(--r-pill);padding:3px 6px;white-space:nowrap;border:1px solid var(--line-2);color:var(--ink-2);text-align:center}
:root[data-ui-g] .g-phase.lead{color:var(--up);border-color:color-mix(in srgb,var(--up) 45%,transparent)}
:root[data-ui-g] .g-phase.weak{color:var(--down);border-color:color-mix(in srgb,var(--down) 45%,transparent)}
:root[data-ui-g] .g-wl-ev{font-size:11.5px;color:var(--ink-3);text-align:right}
:root[data-ui-g] .g-wl-add{margin:11px 0 0;padding-top:11px;border-top:1px dashed var(--line-2)}
/* ── index focus ── */
:root[data-ui-g] .g-idx-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:6px}
:root[data-ui-g] .g-idx-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-top:10px}
@media(max-width:620px){:root[data-ui-g] .g-idx-stats{grid-template-columns:repeat(2,1fr)}}
/* ── pulse deck ── */
:root[data-ui-g] .g-deck{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin-top:12px}
@media(max-width:1150px){:root[data-ui-g] .g-deck{grid-template-columns:repeat(2,minmax(0,1fr))}}
:root[data-ui-g] .g-cell{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px;display:flex;flex-direction:column;gap:7px;position:relative;transition:border-color .18s,transform .18s}
:root[data-ui-g] .g-cell.click{cursor:pointer}
:root[data-ui-g] .g-cell.click:hover{border-color:var(--accent);transform:translateY(-1px)}
:root[data-ui-g] .g-cell.wide{grid-column:1/-1}
:root[data-ui-g] .g-cell .g-big{font-size:26px}
:root[data-ui-g] .g-cell .g-sub{font-size:11px;color:var(--ink-2)}
:root[data-ui-g] .g-hint{font:600 8.5px/1 var(--mono);letter-spacing:.08em;color:var(--ink-3);position:absolute;top:11px;right:11px;text-transform:uppercase;opacity:.7}
:root[data-ui-g] .g-tspark{height:26px;margin-top:2px;color:var(--accent)}
:root[data-ui-g] .g-bigspark{height:70px;margin:8px 0 4px;color:var(--accent)}
:root[data-ui-g] .g-pl-spark{flex:1;min-width:120px;height:34px;color:var(--candle-up)}
:root[data-ui-g] .g-tspark.up,:root[data-ui-g] .g-bigspark.up,:root[data-ui-g] .g-pl-spark.up{color:var(--up)}
:root[data-ui-g] .g-tspark.dn,:root[data-ui-g] .g-bigspark.dn,:root[data-ui-g] .g-pl-spark.dn{color:var(--down)}
:root[data-ui-g] .g-tspark svg,:root[data-ui-g] .g-bigspark svg,:root[data-ui-g] .g-pl-spark svg{width:100%;display:block}
:root[data-ui-g] .g-expand{grid-column:1/-1;background:var(--bg-0);border:1px solid var(--accent);border-radius:var(--r-sm);padding:13px 15px;margin-top:2px;display:none}
:root[data-ui-g] .g-expand.on{display:block}
:root[data-ui-g] .g-expand h4{margin:0 0 4px;font-size:13px}
:root[data-ui-g] .g-expand p{margin:0;font-size:12.5px;color:var(--ink-2);line-height:1.55}
:root[data-ui-g] .g-heat{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px}
:root[data-ui-g] .g-sec{display:inline-flex;flex-direction:column;gap:2px;padding:7px 10px;border-radius:8px;border:1px solid var(--line);min-width:74px;background:var(--bg-0)}
:root[data-ui-g] .g-sec b{font-size:11px;font-weight:700}
:root[data-ui-g] .g-sec span{font:700 12px var(--mono)}
/* ── ribbon feed picker + sample marks ── */
:root[data-ui-g] .g-feedpick{background:var(--bg-0);color:var(--ink);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:5px 11px;font:700 11px var(--font);cursor:pointer;flex:none}
:root[data-ui-g] .g-feedpick:hover{border-color:var(--accent)}
:root[data-ui-g] .g-rib b.acc{color:var(--accent)}
:root[data-ui-g] .g-smp{font:600 8.5px/1 var(--mono);letter-spacing:.1em;color:var(--warn);border:1px solid color-mix(in srgb,var(--warn) 55%,transparent);border-radius:var(--r-pill);padding:2px 5px;text-transform:uppercase;flex:none;align-self:center}
:root[data-ui-g] .g-prov.sample{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 45%,transparent)}
:root[data-ui-g] .g-prov.sample::before{background:var(--warn)}
/* ── arrange (pin / collapse / hide) ── */
:root[data-ui-g] .g-zone-b.collapsed{display:none}
:root[data-ui-g] .g-zone.hidden{display:none}
:root[data-ui-g] .g-arr{position:relative;margin-left:6px}
:root[data-ui-g] .g-arr-b{border:0;background:transparent;color:var(--ink-3);cursor:pointer;font-size:16px;line-height:1;padding:2px 6px;border-radius:6px}
:root[data-ui-g] .g-arr-b:hover{color:var(--ink);background:var(--bg-3)}
:root[data-ui-g] .g-arr-m{position:absolute;right:0;top:26px;z-index:20;background:var(--bg-3);border:1px solid var(--line-2);border-radius:10px;padding:5px;min-width:140px;box-shadow:0 12px 32px rgba(0,0,0,.4);display:none}
:root[data-ui-g] .g-arr-m.on{display:block}
:root[data-ui-g] .g-arr-m button{display:block;width:100%;text-align:left;border:0;background:transparent;color:var(--ink-2);font:600 12px var(--font);padding:7px 9px;border-radius:6px;cursor:pointer}
:root[data-ui-g] .g-arr-m button:hover{background:var(--bg-0);color:var(--ink)}
:root[data-ui-g] .g-hidden-tray{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 14px;background:var(--bg-1);border:1px dashed var(--line-2);border-radius:var(--r);margin-bottom:16px;font-size:12px;color:var(--ink-3)}
:root[data-ui-g] .g-hidden-tray:empty{display:none}
:root[data-ui-g] .g-restore{background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink-2);border-radius:var(--r-pill);padding:4px 10px;font:600 11px var(--font);cursor:pointer}
/* ── regime one-liner (very top) ── */
:root[data-ui-g] .g-regime{display:flex;align-items:center;gap:11px;padding:11px 15px;margin-bottom:16px;
  background:linear-gradient(100deg,var(--acc-dim),transparent 72%),var(--bg-1);border:1px solid var(--line);
  border-left:3px solid var(--accent);border-radius:var(--r);font-size:13.5px;color:var(--ink-2);line-height:1.45}
:root[data-ui-g] .g-regime-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);flex:none;box-shadow:0 0 10px var(--glow)}
:root[data-ui-g] .g-regime-t b{color:var(--ink)}
/* ── conviction shortlist ── */
:root[data-ui-g] .g-cv-count{font-size:12px;color:var(--ink-3);margin:0 0 9px}
:root[data-ui-g] .g-cv-count b{color:var(--accent)}
:root[data-ui-g] .g-convw{display:flex;flex-direction:column}
:root[data-ui-g] .g-cv{display:grid;grid-template-columns:112px 1fr auto;gap:12px;align-items:center;padding:8px 2px;border-bottom:1px solid var(--line);font-size:13px}
:root[data-ui-g] .g-cv:last-child{border-bottom:0}
:root[data-ui-g] .g-cv-meta{color:var(--ink-3);font-size:12px}
:root[data-ui-g] .g-cv-tags{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
:root[data-ui-g] .g-cv-tag{font:600 9.5px/1 var(--mono);border-radius:var(--r-pill);padding:3px 7px;white-space:nowrap;border:1px solid var(--line-2);color:var(--ink-2)}
:root[data-ui-g] .g-cv-tag.near{color:var(--up);border-color:color-mix(in srgb,var(--up) 45%,transparent)}
:root[data-ui-g] .g-cv-tag.q{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent)}
/* ── filings & ownership feed ── */
:root[data-ui-g] .g-filings{display:flex;flex-direction:column;max-height:260px;overflow-y:auto;scrollbar-width:thin}
:root[data-ui-g] .g-fl{display:grid;grid-template-columns:11px 92px 1fr auto;gap:9px;align-items:center;padding:7px 2px;border-bottom:1px solid var(--line);font-size:12.5px}
:root[data-ui-g] .g-fl:last-child{border-bottom:0}
:root[data-ui-g] .g-fl-dot{width:7px;height:7px;border-radius:50%;background:var(--ink-3)}
:root[data-ui-g] .g-fl-dot.pos{background:var(--up)}
:root[data-ui-g] .g-fl-dot.warn{background:var(--warn)}
:root[data-ui-g] .g-fl-d{color:var(--ink-2)}
:root[data-ui-g] .g-fl-when{font-size:11px;color:var(--ink-3);text-align:right}
/* ── market heatmap (squarified treemap) ── */
:root[data-ui-g] .g-hm{position:relative;width:100%;aspect-ratio:1000/525;min-height:300px;border-radius:var(--r-sm);overflow:hidden;background:var(--bg-0);border:1px solid var(--line)}
:root[data-ui-g] .g-hm-t{position:absolute;overflow:hidden;display:flex;align-items:center;justify-content:center;
  border:1px solid color-mix(in srgb,var(--bg-0) 55%,transparent);text-decoration:none;transition:filter .12s,outline-color .12s;outline:1px solid transparent}
:root[data-ui-g] .g-hm-t.up{background:color-mix(in srgb,var(--up) calc(var(--i,.3)*70% + 14%),var(--bg-3))}
:root[data-ui-g] .g-hm-t.dn{background:color-mix(in srgb,var(--down) calc(var(--i,.3)*70% + 14%),var(--bg-3))}
:root[data-ui-g] .g-hm-t:hover{filter:brightness(1.28);z-index:3;outline-color:var(--ink)}
:root[data-ui-g] .g-hm-l{padding:0 2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;
  font:700 9px/1.05 var(--font);color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.55);letter-spacing:.01em}
:root[data-ui-g][data-theme="light"] .g-hm-l{color:#0b1a12;text-shadow:0 1px 1px rgba(255,255,255,.45)}
:root[data-ui-g] .g-hm-leg{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-top:9px;font-size:11px;color:var(--ink-3)}
:root[data-ui-g] .g-hm-leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:middle}
:root[data-ui-g] .g-hm-leg i.up{background:var(--up)} :root[data-ui-g] .g-hm-leg i.dn{background:var(--down)}
/* ── regime band (below the today-core): RRG + breadth divergence ── */
:root[data-ui-g] .g-rband{margin-top:20px;background:linear-gradient(165deg,var(--bg-2),var(--bg-1) 66%);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px 18px;position:relative;overflow:hidden}
:root[data-ui-g] .g-rband::before{content:"";position:absolute;inset:0 auto auto 0;width:60px;height:2px;background:linear-gradient(90deg,var(--accent-hi),transparent)}
:root[data-ui-g] .g-rband-h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:10px}
:root[data-ui-g] .g-rband-h h2{margin:0;font-size:16px;font-weight:800}
:root[data-ui-g] .g-rband-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:820px){:root[data-ui-g] .g-rband-grid{grid-template-columns:1fr}}
:root[data-ui-g] .g-rband-card{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px 14px}
:root[data-ui-g] .g-rband-ch{display:flex;align-items:center;gap:10px;margin-bottom:8px}
:root[data-ui-g] .g-rband-ch h3{margin:0;font-size:13px;font-weight:700}
:root[data-ui-g] .g-rband-ch .g-prov{margin-left:auto}
/* quadrant hue vars (a 4-hue palette, NOT the signed up/down) */
:root[data-ui-g] .q-lead{--qc:var(--accent-hi)} :root[data-ui-g] .q-impr{--qc:var(--candle-up)}
:root[data-ui-g] .q-weak{--qc:var(--warn)} :root[data-ui-g] .q-lag{--qc:var(--ink-3)}
:root[data-ui-g] .g-rrg{width:100%;aspect-ratio:460/380}
:root[data-ui-g] .g-rrg svg{width:100%;height:100%;display:block}
:root[data-ui-g] .g-rrg rect{fill:color-mix(in srgb,var(--qc) 9%,transparent)}
:root[data-ui-g] .g-rrg-ax{stroke:var(--line-2);stroke-width:1;stroke-dasharray:3 3}
:root[data-ui-g] .g-rrg-q{fill:var(--ink-3);font:700 8.5px var(--font);letter-spacing:.1em}
:root[data-ui-g] .g-rrg-s{transition:opacity .15s;cursor:pointer;outline:none}
:root[data-ui-g] .g-rrg.iso .g-rrg-s{opacity:.09}
:root[data-ui-g] .g-rrg.iso .g-rrg-s.on{opacity:1}
:root[data-ui-g] .g-rrg-seg{fill:none;stroke:var(--qc);stroke-linecap:round}
:root[data-ui-g] .g-rrg-seg.last{filter:drop-shadow(0 0 3px var(--qc))}
:root[data-ui-g] .g-rrg-head{fill:var(--qc);stroke:var(--bg-0);stroke-width:1}
:root[data-ui-g] .g-rrg-s:focus-visible .g-rrg-head{stroke:var(--accent-hi);stroke-width:2.4}
:root[data-ui-g] .g-rrg-lbl{fill:var(--ink);font:700 9px var(--font);paint-order:stroke;stroke:var(--bg-0);stroke-width:2.4px}
:root[data-ui-g] .g-rrg-leg{display:flex;flex-wrap:wrap;gap:11px;align-items:center;margin-top:8px;font-size:10.5px;color:var(--ink-2)}
:root[data-ui-g] .g-rrg-leg span{display:inline-flex;align-items:center;gap:5px}
:root[data-ui-g] .g-rrg-leg span::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--qc)}
:root[data-ui-g] .g-rrg-note{color:var(--ink-3)} :root[data-ui-g] .g-rrg-note::before{display:none!important}
/* breadth divergence chart */
:root[data-ui-g] .g-bd{width:100%;aspect-ratio:460/200}
:root[data-ui-g] .g-bd svg{width:100%;height:100%;display:block}
:root[data-ui-g] .g-bd-gap{fill:var(--acc-dim)}
:root[data-ui-g] .g-bd-mid{stroke:var(--line-2);stroke-width:1;stroke-dasharray:3 3}
:root[data-ui-g] .g-bd-price{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
:root[data-ui-g] .g-bd-eff{fill:none;stroke:var(--candle-up);stroke-width:2;stroke-linejoin:round;opacity:.9}
:root[data-ui-g] .g-bd-dot{stroke:var(--bg-0);stroke-width:1.5}
:root[data-ui-g] .g-bd-dot.price{fill:var(--accent)} :root[data-ui-g] .g-bd-dot.eff{fill:var(--candle-up)}
:root[data-ui-g] .g-bd-leg{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:10.5px;color:var(--ink-2)}
:root[data-ui-g] .g-bd-leg span{display:inline-flex;align-items:center;gap:5px}
:root[data-ui-g] .g-bd-leg span::before{content:"";width:12px;height:3px;border-radius:2px}
:root[data-ui-g] .g-bd-leg .price::before{background:var(--accent)} :root[data-ui-g] .g-bd-leg .eff::before{background:var(--candle-up)}
:root[data-ui-g] .g-bd-read{font-size:12.5px;color:var(--ink-2);margin:9px 0 0}
:root[data-ui-g] .g-bd-read b{color:var(--ink)}
</style>"""


def assets() -> str:
    """The client viz bundle — reads numeric data-* attrs only (DOM-safe), reduced-motion aware."""
    return """<script>(function(){
var RM=matchMedia("(prefers-reduced-motion:reduce)").matches;
function w(el,v){ if(RM){ el.style.width=v; } else { requestAnimationFrame(function(){ el.style.width=v; }); } }
document.querySelectorAll(".g-breadth").forEach(function(el){
  var adv=+el.getAttribute("data-adv")||0, dec=+el.getAttribute("data-dec")||0, tot=adv+dec;
  var up=el.querySelector(".g-split-up"); if(!up||!tot) return;
  w(up, Math.round(adv/tot*100)+"%");
});
document.querySelectorAll(".g-divtrack").forEach(function(el){
  var net=+el.getAttribute("data-net")||0, max=+el.getAttribute("data-max")||1, bar=el.querySelector(".g-fbar");
  if(!bar||!max) return; bar.style[net>=0?"left":"right"]="50%";
  w(bar, Math.min(50,Math.abs(net)/max*50)+"%");
});
document.querySelectorAll(".g-spark").forEach(function(el){
  var s=(el.getAttribute("data-series")||"").split(",").map(Number).filter(function(x){return !isNaN(x);});
  if(s.length<2) return;
  var W=300,H=38,mn=Math.min.apply(null,s),mx=Math.max.apply(null,s),n=s.length,col=getComputedStyle(el).color;
  function X(i){return i/(n-1)*W;} function Y(v){return 4+(H-8)*(1-(v-mn)/((mx-mn)||1));}
  var d=""; for(var i=0;i<n;i++){ d+=(i?"L":"M")+X(i).toFixed(1)+" "+Y(s[i]).toFixed(1)+" "; }
  el.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" aria-hidden="true">'
    +'<path d="'+d+'" fill="none" stroke="'+col+'" stroke-width="1.7"/>'
    +'<circle cx="'+X(n-1).toFixed(1)+'" cy="'+Y(s[n-1]).toFixed(1)+'" r="2.5" fill="'+col+'"/></svg>';
});
document.querySelectorAll(".g-rb-f").forEach(function(el){ w(el, (+el.getAttribute("data-w")||0)+"%"); });
document.querySelectorAll(".g-gauge").forEach(function(el){
  var v=Math.max(0,Math.min(100,+el.getAttribute("data-value")||0)), fill=el.querySelector(".g-gfill");
  if(!fill) return; var L=fill.getTotalLength(); fill.style.strokeDasharray=L; var off=L*(1-v/100);
  if(RM){ fill.style.strokeDashoffset=off; } else { fill.style.strokeDashoffset=L; fill.style.transition="stroke-dashoffset 1.2s cubic-bezier(.2,.7,.2,1)"; requestAnimationFrame(function(){ fill.style.strokeDashoffset=off; }); }
});
/* ── deck / featured sparklines (tspark · bigspark · pl-spark) ── */
function gspark(el){
  var s=(el.getAttribute("data-series")||"").split(",").map(Number).filter(function(x){return !isNaN(x);});
  if(s.length<2) return;
  var big=el.className.indexOf("g-bigspark")>=0, W=300,
      H=el.className.indexOf("g-tspark")>=0?26:(big?70:34),
      mn=Math.min.apply(null,s),mx=Math.max.apply(null,s),n=s.length,col=getComputedStyle(el).color;
  function X(i){return i/(n-1)*W;} function Y(v){return 3+(H-6)*(1-(v-mn)/((mx-mn)||1));}
  var d=""; for(var i=0;i<n;i++){ d+=(i?"L":"M")+X(i).toFixed(1)+" "+Y(s[i]).toFixed(1)+" "; }
  var fill=big?('<path d="'+d+'L'+W+' '+H+' L0 '+H+' Z" fill="'+col+'" opacity=".12"/>'):"";
  el.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" aria-hidden="true">'+fill
    +'<path d="'+d+'" fill="none" stroke="'+col+'" stroke-width="1.8"/>'
    +'<circle cx="'+X(n-1).toFixed(1)+'" cy="'+Y(s[n-1]).toFixed(1)+'" r="2.4" fill="'+col+'"/></svg>';
}
document.querySelectorAll(".g-tspark,.g-bigspark,.g-pl-spark").forEach(gspark);
/* ── breadth split tiles (data on .g-split) ── */
document.querySelectorAll(".g-split[data-adv]").forEach(function(el){
  var a=+el.getAttribute("data-adv")||0,d=+el.getAttribute("data-dec")||0,t=a+d,u=el.querySelector(".g-split-up");
  if(u&&t) w(u,Math.round(a/t*100)+"%");
});
/* ── pulse deck: click a tile to open its trend ── */
document.querySelectorAll(".g-cell.click").forEach(function(c){
  function tog(){ var id=c.getAttribute("data-exp"),p=id&&document.getElementById(id); if(!p) return;
    var open=p.classList.contains("on");
    document.querySelectorAll(".g-expand.on").forEach(function(x){x.classList.remove("on");});
    if(!open){ p.classList.add("on"); p.querySelectorAll(".g-bigspark").forEach(gspark); } }
  c.addEventListener("click",tog);
  c.addEventListener("keydown",function(e){ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); tog(); } });
});
/* ── featured chooser: promote your pick (persisted); the rest still scrolls below ── */
(function(){
  var fbs=document.querySelectorAll(".g-featbar .g-fb"), title=document.getElementById("g-feat-title"),
      star=document.getElementById("g-feat-star"); if(!fbs.length) return;
  var K="pvgfeat", def="v-watch";
  try{ var sv=localStorage.getItem(K); if(sv) def=sv; }catch(e){}
  if(!document.getElementById(def)) def="v-watch";
  function show(v){
    fbs.forEach(function(b){ b.setAttribute("aria-pressed",b.getAttribute("data-v")===v?"true":"false"); });
    document.querySelectorAll(".g-featv").forEach(function(p){ p.classList.toggle("on",p.id===v); });
    var btn=document.querySelector('.g-featbar .g-fb[data-v="'+v+'"]');
    if(btn&&title) title.textContent=btn.getAttribute("data-title")||title.textContent;
    var el=document.getElementById(v); if(el) el.querySelectorAll(".g-tspark,.g-bigspark,.g-pl-spark").forEach(gspark);
    if(star) star.classList.toggle("set",v===def);
  }
  fbs.forEach(function(b){ b.addEventListener("click",function(){ show(b.getAttribute("data-v")); }); });
  if(star) star.addEventListener("click",function(){
    var cur=document.querySelector('.g-featbar .g-fb[aria-pressed="true"]'); if(!cur) return;
    def=cur.getAttribute("data-v"); try{ localStorage.setItem(K,def); }catch(e){}
    star.classList.add("set"); star.title="This is your default";
  });
  show(def);
})();
/* ── selectable ticker feed (persisted) ── */
(function(){
  var sel=document.getElementById("g-feedpick"); if(!sel) return;
  var K="pvgfeed";
  function set(k){ document.querySelectorAll(".g-rib-scroll[data-feed]").forEach(function(g){ g.hidden=g.getAttribute("data-feed")!==k; }); }
  try{ var sv=localStorage.getItem(K); if(sv&&document.querySelector('.g-rib-scroll[data-feed="'+sv+'"]')){ sel.value=sv; set(sv); } }catch(e){}
  sel.addEventListener("change",function(){ set(sel.value); try{ localStorage.setItem(K,sel.value); }catch(e){} });
})();
/* ── arrange: pin / collapse / hide any card (persisted) ── */
(function(){
  var tray=document.getElementById("g-tray"); if(!tray) return;
  var K="pvghidden", hidden={}; try{ hidden=JSON.parse(localStorage.getItem(K)||"{}")||{}; }catch(e){}
  function persist(){ try{ localStorage.setItem(K,JSON.stringify(hidden)); }catch(e){} }
  function restoreChip(name,z){
    var chip=document.createElement("button"); chip.type="button"; chip.className="g-restore"; chip.textContent="+ "+name;
    chip.addEventListener("click",function(){ z.classList.remove("hidden"); delete hidden[name]; persist();
      tray.removeChild(chip); if(!tray.querySelector(".g-restore")) tray.innerHTML=""; });
    if(!tray.querySelector(".g-restore")) tray.innerHTML="<span>Hidden:</span>";
    tray.appendChild(chip);
  }
  document.querySelectorAll(".g-side .g-zone, .g-main .g-zone:not(.g-feat)").forEach(function(z){
    var h=z.querySelector(".g-zone-h"), name=z.getAttribute("data-name")||"Section"; if(!h) return;
    var wrap=document.createElement("span"); wrap.className="g-arr";
    wrap.innerHTML='<button class="g-arr-b" type="button" aria-label="Arrange" title="Pin, collapse or hide">⋮</button>'
      +'<span class="g-arr-m"><button data-a="pin">↑ Pin to top</button><button data-a="collapse">▾ Collapse</button><button data-a="hide">✕ Hide</button></span>';
    h.appendChild(wrap);
    var b=wrap.querySelector(".g-arr-b"), m=wrap.querySelector(".g-arr-m"), body=z.querySelector(".g-zone-b");
    b.addEventListener("click",function(e){ e.stopPropagation();
      document.querySelectorAll(".g-arr-m.on").forEach(function(x){ if(x!==m) x.classList.remove("on"); }); m.classList.toggle("on"); });
    m.querySelector('[data-a="pin"]').addEventListener("click",function(){ z.parentNode.prepend(z); m.classList.remove("on"); });
    m.querySelector('[data-a="collapse"]').addEventListener("click",function(ev){ if(body) body.classList.toggle("collapsed");
      ev.target.textContent=(body&&body.classList.contains("collapsed"))?"▸ Expand":"▾ Collapse"; m.classList.remove("on"); });
    m.querySelector('[data-a="hide"]').addEventListener("click",function(){ z.classList.add("hidden"); hidden[name]=1; persist();
      m.classList.remove("on"); restoreChip(name,z); });
    if(hidden[name]){ z.classList.add("hidden"); restoreChip(name,z); }
  });
  document.addEventListener("click",function(){ document.querySelectorAll(".g-arr-m.on").forEach(function(x){ x.classList.remove("on"); }); });
})();
/* ── RRG: hover / focus / click to isolate one sector (declutter) ── */
(function(){
  var rrg=document.querySelector(".g-rrg"); if(!rrg) return;
  var pinned=null;
  function grp(t){ return (t&&t.closest)?t.closest(".g-rrg-s"):null; }
  function iso(g){ rrg.classList.add("iso");
    rrg.querySelectorAll(".g-rrg-s.on").forEach(function(x){ if(x!==g) x.classList.remove("on"); });
    if(g) g.classList.add("on"); }
  function clear(){ if(pinned) return; rrg.classList.remove("iso");
    rrg.querySelectorAll(".g-rrg-s.on").forEach(function(x){ x.classList.remove("on"); }); }
  rrg.addEventListener("pointerover",function(e){ var g=grp(e.target); if(g) iso(g); });
  rrg.addEventListener("pointerout",function(e){ var g=grp(e.target); if(g&&!g.contains(e.relatedTarget)) clear(); });
  rrg.addEventListener("focusin",function(e){ var g=grp(e.target); if(g) iso(g); });
  rrg.addEventListener("focusout",function(){ clear(); });
  rrg.addEventListener("click",function(e){ var g=grp(e.target);
    if(g){ if(pinned===g){ pinned=null; clear(); } else { pinned=g; iso(g); } }
    else { pinned=null; clear(); } });
})();
})();</script>"""
