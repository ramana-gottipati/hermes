"""How to read the charts — a beginner's guide to the site's visual language (deep-data sprint).

Ramana: "we should give guidance somewhere on how to read the analytics / charts" → then, after a
beginner review: "show, don't tell — use REAL annotated examples + one 'read one together'."

So this guide now:
  1. Opens with a WORKED example — the real 22-year market-breadth ribbon, walked through in 4
     plain steps, with the crashes everyone remembers marked (2008 · COVID · 2024).
  2. Teaches the six chart SHAPES, each with a LIVE example drawn from REAL data on the actual
     pages (falling back to an illustrative example only if a table is absent — never 500).
  3. Explains the recurring ideas in plain words, and states the golden rule (descriptive, never
     advice).

The VISUAL companion to the text Glossary (sits beside it in Trust). Linked from every deep-data
lens header ("How to read these charts →") + the Coverage index. Route: /dash/reading-guide.
"""
from __future__ import annotations

import os
import sqlite3
from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

_CSS = """
<style>
.rg-note{color:var(--ink-2);font-size:13.5px;line-height:1.6;margin:2px 0 14px;max-width:960px;}
.rg-card{background:var(--bg-1);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px;}
.rg-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 4px;}
.rg-top h3{font-size:16px;margin:0;color:var(--ink);}
.rg-top .where{font-size:11px;color:var(--ink-3);margin-left:auto;}
.rg-top .where a{color:var(--accent);text-decoration:none;}
.rg-real{font-family:var(--mono);font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--up);border:1px solid rgba(var(--up-rgb),.4);background:rgba(var(--up-rgb),.08);
  border-radius:20px;padding:2px 8px;}
.rg-ex{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:12px 14px;margin:8px 0 10px;}
.rg-ex .cap{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin:0 0 6px;}
.rg-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.rg-grid .k{font-size:11px;font-weight:700;color:var(--accent-2);text-transform:uppercase;letter-spacing:.05em;margin:0 0 3px;font-family:var(--mono);}
.rg-grid p{margin:0;font-size:13px;line-height:1.55;color:var(--ink-2);}
.rg-grid p b{color:var(--ink);}
@media(max-width:640px){.rg-grid{grid-template-columns:1fr;}}
.rg-ideas{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:11px;margin-top:8px;}
.rg-idea{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:11px 14px;}
.rg-idea .t{font-weight:700;color:var(--ink);font-size:13px;}
.rg-idea .d{font-size:12.5px;color:var(--ink-2);line-height:1.5;margin-top:2px;}
.rg-gold{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.07);border-radius:0 12px 12px 0;
  padding:14px 18px;margin:6px 0 4px;max-width:1000px;}
.rg-gold .t{font-weight:800;color:var(--ink);font-size:15px;margin:0 0 4px;}
.rg-gold p{margin:0;font-size:13.5px;color:var(--ink-2);line-height:1.6;}
.rg-h{font-size:20px;font-weight:750;margin:26px 0 8px;letter-spacing:-.01em;color:var(--ink);}
.rg-next{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}
.rg-next a{border:1px solid var(--line-2);background:var(--bg-2);border-radius:20px;padding:6px 14px;
  color:var(--ink);text-decoration:none;font-size:12.5px;}
.rg-next a:hover{border-color:var(--accent);}
/* worked walkthrough */
.rg-walk{background:linear-gradient(180deg,rgba(84,163,255,.06),rgba(84,163,255,.01));
  border:1px solid var(--line-2);border-left:3px solid var(--accent);border-radius:0 14px 14px 0;padding:18px 20px;margin:0 0 18px;}
.rg-walk .wcap{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin:8px 0 6px;}
.rg-steps{list-style:none;margin:12px 0 0;padding:0;counter-reset:s;}
.rg-steps li{position:relative;padding:2px 0 12px 40px;margin:0;font-size:13.5px;line-height:1.55;color:var(--ink-2);}
.rg-steps li b{color:var(--ink);}
.rg-steps li::before{counter-increment:s;content:counter(s);position:absolute;left:0;top:0;
  width:26px;height:26px;border-radius:50%;background:var(--accent);color:var(--on-accent);
  font:700 13px var(--mono);display:flex;align-items:center;justify-content:center;}
.rg-steps li:not(:last-child)::after{content:"";position:absolute;left:12.5px;top:26px;bottom:2px;width:1px;background:var(--line-2);}
.rg-done{margin-top:6px;font-size:13.5px;color:var(--up);font-weight:600;}
</style>
"""


def _roll(vals, k):
    if k < 2:
        return list(vals)
    out, buf = [], []
    for v in vals:
        buf.append(v if v is not None else (buf[-1] if buf else 0.0))
        if len(buf) > k:
            buf.pop(0)
        out.append(sum(buf) / len(buf))
    return out


@lru_cache(maxsize=1)
def _real(_hermes_tag: str, research_db: str) -> dict:
    """Pull the real examples once (cached). Any piece may be None → the card falls back to an
    illustrative example. Never raises."""
    out = {"ribbon": None, "eras": None, "tape": None, "tape_lab": None, "fp": None,
           "env": None, "gauge_v": None, "gauge_d": None, "sector": None, "as_of": None}
    # breadth ribbon + tape line, from market_internals_daily (hermes.db)
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT d, pct_adv, mep_net FROM market_internals_daily "
                                "ORDER BY d").fetchall()
        if rows and len(rows) > 500:
            dates = [r["d"] for r in rows]
            out["as_of"] = dates[-1]

            def frac(ymd):
                for i, dd in enumerate(dates):
                    if dd >= ymd:
                        return i / len(dates)
                return 1.0
            step = max(1, len(rows) // 420)
            idx = list(range(0, len(rows), step))
            out["ribbon"] = [(dates[i], ((rows[i]["pct_adv"] or 50) - 50) / 50.0) for i in idx]
            out["eras"] = [(frac("2008-10-01"), "2008 crash"), (frac("2020-03-01"), "COVID"),
                           (frac("2024-06-04"), "2024 shock")]
            k = max(5, len(rows) // 60)
            out["tape"] = _roll([r["mep_net"] for r in rows], k)
            out["tape_lab"] = [(frac("2008-10-01"), "2008"), (frac("2020-03-01"), "COVID"),
                               (0.99, "now")]
    except Exception:  # noqa: BLE001
        pass
    # FII long:short gauge, from participant_oi (hermes.db)
    try:
        with get_conn() as conn:
            r = conn.execute("SELECT fut_idx_long, fut_idx_short FROM participant_oi "
                             "WHERE client_type='FII' AND fut_idx_short>0 ORDER BY trade_date").fetchall()
        ratios = [a / b for a, b in ((x["fut_idx_long"], x["fut_idx_short"]) for x in r) if a and b]
        if len(ratios) > 50:
            out["gauge_v"], out["gauge_d"] = ratios[-1], ratios
    except Exception:  # noqa: BLE001
        pass
    # fingerprint + gain/pain envelope, reusing move_anatomy's cached compute (research.db)
    try:
        from src.web.move_anatomy_view import _compute as _ac
        d = _ac(research_db)
        fp = sorted(d["fp"], key=lambda r: -r["z"])
        out["fp"] = [(r["label"], r["z"]) for r in (fp[:3] + fp[-2:])]
        ev, bs = d["env"].get("event", {}), d["env"].get("baseline", {})
        if ev.get("mfe") is not None and bs.get("mfe") is not None:
            out["env"] = [("A big-move setup", ev["mae"], ev["mfe"], "best rise"),
                          ("A random quiet day", bs["mae"], bs["mfe"], "")]
    except Exception:  # noqa: BLE001
        pass
    # sector heat-grid slice, reusing sector_econ's cached compute
    try:
        from src.web.sector_econ_view import _compute as _sc
        d = _sc("roce", research_db)
        if d and d["sectors"]:
            secs = d["sectors"][:4]
            yrs = d["years"]
            want = [y for y in ("2016", "2019", "2022", "2025") if y in yrs]
            yidx = [yrs.index(y) for y in want] or list(range(0, len(yrs), max(1, len(yrs) // 4)))
            cols = [f"FY{yrs[i][2:]}" for i in yidx]
            mat = [[d["matrix"][d["sectors"].index(s)][i] for i in yidx] for s in secs]
            out["sector"] = (secs, cols, mat)
    except Exception:  # noqa: BLE001
        pass
    return out


def _card(title, real_flag, svg, cap, what, how, where_label, where_href) -> str:
    tag = '<span class="rg-real">real chart</span>' if real_flag else ''
    return (f'<div class="rg-card"><div class="rg-top"><h3>{_esc(title)}</h3>{tag}'
            f'<span class="where">on: <a href="{where_href}">{_esc(where_label)}</a></span></div>'
            f'<div class="rg-ex"><div class="cap">{_esc(cap)}</div>{svg}</div>'
            f'<div class="rg-grid"><div><div class="k">What it is</div><p>{what}</p></div>'
            f'<div><div class="k">How to read it</div><p>{how}</p></div></div></div>')


_IDEAS = [
    ("Breadth", "How many stocks are actually rising — not just the one headline index. Broad = most stocks up."),
    ("The tape", "Whether buyers are <b>aggressive</b> (paying up to own stock) or quietly stepping back. Rising price with a weak tape is a warning."),
    ("Delivery", "Shares actually bought to <b>keep</b> (moved to your demat / holding account), not flipped the same day. High delivery = real conviction."),
    ("Drawdown", "The dip — how far something falls from a high before (maybe) recovering. The pain you sit through before a payoff."),
    ("Dispersion", "How <b>differently</b> stocks move. High = each on its own merits (picking matters); low = they all move together on the big news."),
    ("Median vs average", "The <b>median</b> is the middle outcome — the “typical” one. The <b>average</b> gets pulled up by a few huge winners, so we prefer the median."),
    ("Percentile", "Where a number sits versus its own history. “88th percentile” = higher than 88% of the past — unusually high."),
    ("Base-rate", "How often something happened <b>historically</b>. It describes the past; it is not a prediction of the future."),
    ("Survivorship", "We mostly see companies that survived. Failures dropped off the list, so raw historical returns look rosier than reality."),
    ("FII / DII", "<b>FII</b> = foreign investors. <b>DII</b> = domestic (Indian) mutual funds &amp; insurers. They often trade against each other."),
    ("ROCE / OPM", "<b>ROCE</b> = profit earned per ₹100 of capital a company uses. <b>OPM</b> = profit left from every ₹100 of sales. Higher = a better business."),
    ("Long / short", "A “<b>long</b>” bet profits if the price rises; a “<b>short</b>” bet profits if it falls. “Net short” = more down-bets than up."),
]


@router.get("/dash/reading-guide", response_class=HTMLResponse)
def dash_reading_guide() -> HTMLResponse:
    body = [_CSS, ifx.readability_css()]
    r = _real("v1", _RESEARCH_DB)

    body.append(
        '<h2 style="margin:0 0 2px">How to read the charts '
        '<small style="color:var(--ink-3);font-size:12px;font-weight:400">a 2-minute guide · no finance '
        'background needed</small></h2>'
        + ifx.bottom_line(
            'Every chart on this site is one of a handful of simple shapes. We\'ll <b>read a real one '
            'together</b> first, then name the six shapes — after that you can read <b>any</b> analytic '
            'here. Nothing needs a finance degree.'))

    # ── 1. WORKED EXAMPLE — read one together (real breadth ribbon) ─────────────
    if r["ribbon"]:
        ribbon_svg = ifx.heat_ribbon(r["ribbon"], w=880, h=52, title_at=r["eras"])
        wcap = f'the real thing — how much of the market rose vs fell, every week, 2004 → {_esc(str(r["as_of"]))}'
        step3 = ('See the <b>bright-red bands</b>? Those are real market crashes you may remember — the '
                 '<b>2008</b> crash and <b>COVID in March 2020</b>, marked right on the strip. Almost '
                 'nothing rose in those weeks.')
    else:
        ribbon_svg = ifx.heat_ribbon([(str(i), v) for i, v in enumerate(
            [.8, .6, .3, -.2, -.7, -.9, -.5, 0, .4, .7, .5, .1, -.3, -.6, -.2, .3, .6, .8, .5, .2])], w=880, h=52)
        wcap = 'example — how much of the market rose (green) vs fell (red), week by week'
        step3 = ('The <b>bright-red bands</b> are the rough patches — weeks when almost nothing rose. '
                 'You can spot every bad stretch at a glance.')
    body.append(
        '<div class="rg-h" style="margin-top:14px">Start here — let\'s read one chart together</div>'
        '<div class="rg-walk">'
        f'<div class="wcap">{wcap}</div>{ribbon_svg}'
        '<ol class="rg-steps">'
        '<li>This one strip is <b>22 years</b>. Each thin bar is about a week; the <b>left</b> edge is '
        '2004, the <b>right</b> edge is today.</li>'
        '<li><b>Green</b> = most stocks <b>rose</b> that week; <b>red</b> = most <b>fell</b>. The '
        '<b>brighter</b> the colour, the stronger it was.</li>'
        f'<li>{step3}</li>'
        '<li>That\'s the whole trick — don\'t squint at one bar, <b>read the bands</b>: long green = a calm '
        'rise, red clusters = trouble.</li>'
        '</ol>'
        '<div class="rg-done">✓ You just read a 22-year chart. Every coloured strip on the site works exactly like this.</div>'
        '</div>')

    # ── 2. THE SIX SHAPES ───────────────────────────────────────────────────────
    body.append('<div class="rg-h">The six shapes you\'ll meet</div>'
                '<div class="rg-note">You just used the first one. Here are all six — each example below is '
                'the <b>real chart</b> from the page named on its right (a small illustration if that data '
                'isn\'t loaded).</div>')

    # 1. ribbon (reuse the worked one, smaller)
    body.append(_card(
        "The colour ribbon", bool(r["ribbon"]),
        ifx.heat_ribbon(r["ribbon"], w=760, h=42, title_at=r["eras"]) if r["ribbon"] else
        ifx.heat_ribbon([(str(i), v) for i, v in enumerate([.8, .5, .1, -.4, -.8, -.5, 0, .5, .8, .4, -.2, -.6, .1, .5, .7])], w=760, h=42),
        "how much of the market rose vs fell, week by week",
        "A row of thin coloured bars, one per week (oldest on the left). It squeezes years into a single strip.",
        "<b>Colour = direction</b> (green = up, red = down); <b>brightness = strength</b>. Read the "
        "<b>bands / eras</b>, not one bar.",
        "Market internals", "/dash/market-internals"))

    # 2. filled line (real tape)
    body.append(_card(
        "The filled line", bool(r["tape"]),
        ifx.spark_area(r["tape"], w=760, h=110, signed=True, baseline=0, labels=r["tape_lab"]) if r["tape"] else
        ifx.spark_area([2, 3, 1, 4, 3, 5, 4, 6, 4, 3, 5, 6, 7, 5, 6], w=760, h=110, signed=True, baseline=4),
        "the real 'buying pressure' line — buyers keen (green) vs backing off (red)",
        "A line that fills <b>green above</b> a middle line and <b>red below</b> it. Here the middle means "
        "“<b>neither buying nor selling hard</b>”.",
        "Above the middle = the positive side (here: keen buyers); below = the negative side. The "
        "<b>shape over time</b> is the story — note the deep-red dips at the crashes.",
        "The FII tape", "/dash/participants"))

    # 3. fingerprint (real z)
    body.append(_card(
        "The fingerprint (spreading bars)", bool(r["fp"]),
        ifx.diverging_bars(r["fp"], w=620, bar_h=26, label_w=210, show_values=False, pos_color="var(--series-1)", neg_color="var(--accent-orange)") if r["fp"] else
        ifx.diverging_bars([("Much higher than normal", 0.9), ("A bit higher", 0.4), ("A bit lower", -0.5), ("Much lower", -0.85)],
                           w=620, bar_h=26, label_w=210, show_values=False, pos_color="var(--series-1)", neg_color="var(--accent-orange)"),
        "the real thing — what stands out just before big market moves",
        "Bars spread <b>left and right</b> from a centre line — one per trait. (This is the actual result: "
        "before big moves, strength is up top, heavy buying is at the bottom.)",
        "<b>Right of centre = higher</b> than a normal day; <b>left = lower</b>. Longer bar = more unusual. "
        "Skim top-to-bottom to see what stood out.",
        "Move anatomy", "/dash/move-anatomy"))

    # 4. gain-vs-pain (real env)
    body.append(_card(
        "The gain-vs-pain bar", bool(r["env"]),
        ifx.floating_bars(r["env"], w=640, bar_h=32, label_w=175, unit="%") if r["env"] else
        ifx.floating_bars([("A big-move setup", -10, 40, "best rise"), ("A random quiet day", -18, 11, "")], w=640, bar_h=32, label_w=175, unit="%"),
        "the real typical journey — dip you sit through vs rise you get",
        "A <b>floating bar</b> showing a typical journey, not one number: how far something dips and how far it rises.",
        "The <b>red end (left)</b> = how far it typically <b>dipped</b>; the <b>green end (right)</b> = how "
        "far it typically <b>rose</b>. A bar leaning right = more gain than pain.",
        "Launchpad track record", "/dash/launchpad-track"))

    # 5. gauge (real FII)
    body.append(_card(
        "The 'how unusual' gauge", bool(r["gauge_v"] is not None),
        ifx.pct_gauge(r["gauge_v"], r["gauge_d"], w=560, h=66, label="today", vfmt=2) if r["gauge_v"] is not None else
        ifx.pct_gauge(0.88, [i / 100 for i in range(100)] * 3 + [0.2, 0.25, 0.3] * 20, w=560, h=66, label="today", vfmt=2),
        "the real gauge — where foreigners' stance sits vs its own 2.5-year history",
        "A marker on a range showing where <b>today</b> sits compared with its <b>own past</b>.",
        "The faint hill is where the number usually sits; the bright line is today. Near the <b>left</b> = "
        "unusually low; near the <b>right</b> = unusually high (e.g. “more extreme than 88% of history”).",
        "The FII tape", "/dash/participants"))

    # 6. heat-grid (real sector)
    if r["sector"]:
        secs, cols, mat = r["sector"]
        grid_svg = ifx.heat_grid(secs, cols, mat, w=620, cell_h=28, fmt=0, row_w=118, unit="%")
        grid_cap = "the real thing — how profitable each sector was, year by year"
    else:
        grid_svg = ifx.heat_grid(["Sector A", "Sector B", "Sector C"], ["2019", "2021", "2023", "2025"],
                                 [[12, 18, 22, 25], [30, 28, 26, 24], [8, 14, 9, 16]], w=620, cell_h=28, fmt=0, row_w=92, unit="%")
        grid_cap = "example — sectors down the side, years across the top"
    body.append(_card(
        "The coloured table (heat-grid)", bool(r["sector"]), grid_svg, grid_cap,
        "A coloured table — <b>rows</b> (here, sectors) and <b>columns</b> (here, years).",
        "<b>Warmer (oranger) = higher.</b> Read <b>across a row</b> to watch a sector rise or fade over "
        "time; read <b>down a column</b> to compare in one year. A blank cell = too little data to trust.",
        "Sector economics", "/dash/sector-economics"))

    # ── 3. ideas ────────────────────────────────────────────────────────────────
    body.append('<div class="rg-h">The words, in plain English</div>')
    ideas = "".join(f'<div class="rg-idea"><div class="t">{_esc(t)}</div><div class="d">{d}</div></div>'
                    for t, d in _IDEAS)
    body.append(f'<div class="rg-ideas">{ideas}</div>')

    # ── 4. golden rule ──────────────────────────────────────────────────────────
    body.append(
        '<div class="rg-h">The one rule that matters most</div>'
        '<div class="rg-gold"><div class="t">Everything here describes the past — it never tells you what to do.</div>'
        '<p>These analytics tell you what <b>has</b> happened, with all the caveats stated on each page. <b>No chart '
        'on this site is a buy or sell signal.</b> They are for understanding the market\'s character and history — '
        'the decision is always yours. When a page shows a caveat (survivorship, “after the fact”, thin data), that '
        'is the honest fine print, not a footnote to skip.</p></div>')

    # ── 5. next ─────────────────────────────────────────────────────────────────
    body.append(
        '<div class="rg-h">Now try a page</div>'
        '<div class="rg-next">'
        '<a href="/dash/market-internals">Market internals →</a>'
        '<a href="/dash/participants">The FII tape →</a>'
        '<a href="/dash/launchpad-track">Launchpad track record →</a>'
        '<a href="/dash/move-anatomy">Move anatomy →</a>'
        '<a href="/dash/sector-economics">Sector economics →</a>'
        '<a href="/dash/glossary">Full glossary (every term) →</a></div>')

    return HTMLResponse(_shell("How to read the charts · patearn", "".join(body), "reading-guide", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/reading-guide" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    r = c.get("/dash/reading-guide")
    assert r.status_code == 200 and "How to read the charts" in r.text
    assert r.text.count("<svg") >= 7          # walkthrough + 6 shape examples
    assert "read one chart together" in r.text and "You just read a 22-year chart" in r.text
    assert "in plain english" in r.text.lower() and "buy or sell signal" in r.text
    print("reading_guide_view selftest OK — worked walkthrough + 6 examples + ideas + golden rule")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
