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
def zone(title: str, prov_text: str, body_html: str, sub: str = "") -> str:
    p = prov_text.split("·", 1)
    prov = _prov_html(p[0].strip(), (p[1].strip() if len(p) > 1 else ""))
    sub_html = f'<span class="g-sub">{esc(sub)}</span>' if sub else ""
    return ('<section class="g-zone"><div class="g-zone-h"><h2>' + esc(title) + "</h2>"
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


def _prov_html(table: str, fresh: str, stale: bool = False) -> str:
    cls = "g-prov stale" if stale else "g-prov"
    tail = f" · {esc(fresh)}" if fresh else ""
    return f'<span class="{cls}">{esc(table)}{tail}</span>'


def prov(table: str, fresh: str, stale: bool = False) -> str:
    return _prov_html(table, fresh, stale)


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
        out += ('<div class="g-chrow"><span class="g-sym g-num">' + esc(r.get("symbol")) + "</span>"
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
                + '<span class="g-ag-b"><b class="g-ag-s g-num">' + esc(sym) + "</b> "
                '<span class="g-ag-d">' + desc + "</span></span></div>")
    return '<div class="g-agenda">' + out + "</div>"


def ca_agenda(rows: list) -> str:
    items = []
    for r in (rows or [])[:6]:
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
    for r in (rows or [])[:6]:
        r = _d(r)
        items.append((r.get("meeting_date"), r.get("symbol"), esc((r.get("purpose") or "Results")[:56])))
    return agenda(items)


# ── zone 6: news wire (every href passes safe_url — Codex #9) ────────────────────
def wire(rows: list) -> str:
    if not rows:
        return empty("No headlines have landed yet.")
    out = ""
    for r in (rows or [])[:6]:
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
    cards = ""
    for r in (idx or [])[:4]:
        txt, cls = _signed_pct(r.get("ret_1d_pct"))
        cards += ('<div class="g-icard"><div class="g-nm">' + esc(r.get("index_name")) + "</div>"
                  '<div class="g-lv g-num">' + _num(r.get("close_value")) + "</div>"
                  '<div class="g-ch g-num ' + cls + '">' + txt + "</div></div>")
    if not cards:
        cards = empty("Index signals pending.")
    left = ('<div class="g-pl-l"><div class="g-icards">' + cards + "</div>" + spark(series or []) + "</div>")
    # RIGHT: the restored semicircle mood gauge + breadth (verdict-free mood; signed breadth)
    gtile = ('<div class="g-mtile"><span class="g-lab">Market mood</span>'
             + gauge(mood_pct, "Market mood", mood.get("word", "No data"))
             + '<span class="g-sub">' + esc((mood.get("plain") or "")[:64]) + "</span></div>")
    if breadth and breadth.get("adv") is not None:
        adv, dec = int(breadth.get("adv") or 0), int(breadth.get("dec") or 0)
        btile = ('<div class="g-mtile"><span class="g-lab">Breadth · NSE</span>'
                 '<div class="g-breadth" data-adv="' + str(adv) + '" data-dec="' + str(dec) + '">'
                 '<div class="g-split"><span class="g-split-up"></span></div>'
                 '<div class="g-split-lab"><span class="up">' + str(adv) + ' adv</span>'
                 '<span class="dn">' + str(dec) + ' dec</span></div></div>'
                 '<span class="g-sub">advancers vs decliners</span></div>')
    else:
        btile = '<div class="g-mtile">' + empty("Breadth pending.") + "</div>"
    return ('<div class="g-pulse2">' + left + '<div class="g-pl-r">' + gtile + btile + "</div></div>")


# ── the .g-* stylesheet (scoped by data-ui-g on the root, via the token layer) ──
def css() -> str:
    return """<style>/* g-kit */
:root[data-ui-g] .g-zone{background:linear-gradient(165deg,var(--bg-2),var(--bg-1) 62%);
  border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin-bottom:16px;position:relative}
:root[data-ui-g] .g-zone::before{content:"";position:absolute;inset:0 auto auto 0;width:44px;height:2px;
  background:linear-gradient(90deg,var(--accent-hi),transparent)}
:root[data-ui-g] .g-zone-h{display:flex;align-items:center;gap:10px;padding:13px 16px 10px;flex-wrap:wrap}
:root[data-ui-g] .g-zone-h h2{margin:0;font-size:15px;font-weight:700}
:root[data-ui-g] .g-sub{font-size:12px;color:var(--ink-3)}
:root[data-ui-g] .g-zone-b{padding:4px 16px 16px}
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
:root[data-ui-g] .g-count{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:11px 12px}
:root[data-ui-g] .g-n{font-size:24px;font-weight:700;line-height:1}
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
:root[data-ui-g] .g-chrow{display:grid;grid-template-columns:74px 1fr auto;gap:12px;align-items:center;padding:8px 2px;border-bottom:1px solid var(--line);font-size:13px}
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
:root[data-ui-g] .g-wrow{padding:10px 2px;border-bottom:1px solid var(--line)}
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
:root[data-ui-g] .g-learn{font-size:12.5px;color:var(--ink-2);margin-top:12px;line-height:1.55;padding:10px 12px;background:var(--acc-dim);border-left:2px solid var(--accent);border-radius:0 8px 8px 0}
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
})();</script>"""
