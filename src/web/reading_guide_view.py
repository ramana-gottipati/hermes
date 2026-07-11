"""How to read the charts — a beginner's guide to the site's visual language (deep-data sprint).

Ramana: "we should give guidance somewhere on how to read the analytics / charts." The inline
"In plain English" lines translate each chart in place; this page teaches the chart LANGUAGE
itself — one live mini-example per chart type + a plain "what it is / how to read it", the
recurring plain-word ideas (breadth, the tape, delivery, drawdown, median, percentile, ROCE,
FII…), and the golden rule (everything here is DESCRIPTIVE, never advice).

Trust altitude, next to the Glossary (text terms) — this is the VISUAL companion. Linked from
every deep-data lens header ("How to read these charts →") and the Coverage index.
Route: /dash/reading-guide. No data reads — pure teaching surface with illustrative examples.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_CSS = """
<style>
.rg-note{color:var(--ink-2);font-size:13.5px;line-height:1.6;margin:2px 0 14px;max-width:960px;}
.rg-card{background:var(--bg-1);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px;}
.rg-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 4px;}
.rg-top h3{font-size:16px;margin:0;color:var(--ink);}
.rg-top .where{font-size:11px;color:var(--ink-3);margin-left:auto;}
.rg-top .where a{color:var(--accent);text-decoration:none;}
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
</style>
"""


def _card(title, svg, cap, what, how, where_label, where_href) -> str:
    return (f'<div class="rg-card"><div class="rg-top"><h3>{_esc(title)}</h3>'
            f'<span class="where">where you\'ll see it: <a href="{where_href}">{_esc(where_label)}</a></span></div>'
            f'<div class="rg-ex"><div class="cap">{_esc(cap)}</div>{svg}</div>'
            f'<div class="rg-grid"><div><div class="k">What it is</div><p>{what}</p></div>'
            f'<div><div class="k">How to read it</div><p>{how}</p></div></div></div>')


_IDEAS = [
    ("Breadth", "How many stocks are actually rising — not just the one headline index. Broad = most stocks up."),
    ("The tape", "Whether buyers are <b>aggressive</b> (paying up to own stock) or quietly stepping back. Rising price with a weak tape is a warning."),
    ("Delivery", "Shares actually bought to <b>keep</b> (moved to your demat account), not flipped the same day. High delivery = real conviction."),
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

    body.append(
        '<h2 style="margin:0 0 2px">How to read the charts '
        '<small style="color:var(--ink-3);font-size:12px;font-weight:400">a 2-minute guide · no finance '
        'background needed</small></h2>'
        + ifx.bottom_line(
            'Every chart on this site uses one of a handful of simple shapes. Learn these six and the '
            'plain-word ideas below, and you can read <b>any</b> analytic here — from the 22-year market '
            'map to the sector heat-grid. Nothing here needs a finance degree.')
        + '<div class="rg-note">Tip: on the pages themselves, look for the <b>“In plain English”</b> line '
        'under each chart — it translates <i>that specific</i> chart. This page teaches the shapes so those '
        'translations click.</div>')

    body.append('<div class="rg-h">The six chart shapes</div>')

    # 1. heat-ribbon
    ribbon = [(str(i), v) for i, v in enumerate(
        [.9, .8, .6, .4, .1, -.2, -.5, -.8, -.9, -.6, -.3, .1, .4, .6, .3, -.1, -.4, -.2, .2, .5,
         .7, .8, .6, .3, -.1, -.5, -.7, -.4, 0, .3, .6, .8])]
    body.append(_card(
        "The colour ribbon", ifx.heat_ribbon(ribbon, w=760, h=44),
        "example — a made-up 'regime' strip",
        "A row of thin coloured bars, one per week (oldest on the left). It squeezes years into a single strip.",
        "<b>Colour = direction</b> (green = up/healthy, red = down/weak); <b>brightness = strength</b>. Don't "
        "read one bar — read the <b>eras</b>: a long green stretch is a calm rise; a red cluster is a rough patch.",
        "Market internals", "/dash/market-internals"))

    # 2. filled line
    body.append(_card(
        "The filled line", ifx.spark_area([2, 3, 1, 4, 3, 5, 4, 6, 4, 3, 5, 6, 7, 5, 6],
                                          w=760, h=110, signed=True, baseline=4),
        "example — a line that crosses a neutral middle",
        "A line that fills <b>green above</b> the middle and <b>red below</b> it. The middle line is 'neutral / zero'.",
        "Above the middle = positive, below = negative. The <b>shape over time</b> is the story — drifting up, "
        "down, or swinging? The dot marks the latest value.",
        "The FII tape", "/dash/participants"))

    # 3. fingerprint / diverging bars (neutral palette)
    body.append(_card(
        "The fingerprint (spreading bars)",
        ifx.diverging_bars([("Much higher than normal", 0.9), ("A bit higher", 0.4),
                            ("About normal", 0.05), ("A bit lower", -0.5), ("Much lower", -0.85)],
                           w=620, bar_h=24, label_w=190, pos_color="var(--series-1)", neg_color="var(--accent-orange)"),
        "example — five traits vs a normal day",
        "Bars spread <b>left and right</b> from a centre line — one bar per trait.",
        "<b>Right of centre = higher</b> than a normal day; <b>left = lower</b>. The <b>longer</b> the bar, the more "
        "unusual. Skim top-to-bottom to see what stood out.",
        "Move anatomy", "/dash/move-anatomy"))

    # 4. gain-vs-pain floating bars
    body.append(_card(
        "The gain-vs-pain bar",
        ifx.floating_bars([("A big-move setup", -10, 40, "best rise"), ("A random quiet day", -18, 11, "")],
                          w=640, bar_h=32, label_w=170),
        "example — the typical journey after two kinds of day",
        "A <b>floating bar</b> showing a typical journey, not one number: how far something dips and how far it rises.",
        "The <b>red end (left)</b> = how far it typically <b>dipped</b>; the <b>green end (right)</b> = how far it "
        "typically <b>rose</b>. A bar leaning right = more gain than pain.",
        "Launchpad track record", "/dash/launchpad-track"))

    # 5. percentile gauge
    body.append(_card(
        "The 'how unusual' gauge",
        ifx.pct_gauge(0.88, [i / 100 for i in range(100)] * 3 + [0.2, 0.25, 0.3] * 20, w=560, h=66,
                      label="today", vfmt=2),
        "example — where today sits in its own history",
        "A marker on a range showing where <b>today</b> sits compared with its <b>own past</b>.",
        "The faint hill is where the number usually sits; the bright line is today. “<b>88th percentile</b>” = today "
        "is higher than 88% of history — unusually high (or low, near the left).",
        "The FII tape", "/dash/participants"))

    # 6. heat-grid
    body.append(_card(
        "The coloured table (heat-grid)",
        ifx.heat_grid(["Sector A", "Sector B", "Sector C"], ["2019", "2021", "2023", "2025"],
                      [[12, 18, 22, 25], [30, 28, 26, 24], [8, 14, 9, 16]], w=620, cell_h=28, fmt=0, row_w=92),
        "example — sectors down the side, years across the top",
        "A coloured table — <b>rows</b> (e.g. sectors) and <b>columns</b> (e.g. years).",
        "<b>Warmer (oranger) = higher.</b> Read <b>across a row</b> to watch something rise or fade over time; read "
        "<b>down a column</b> to compare at one moment. A blank cell = too little data to trust.",
        "Sector economics", "/dash/sector-economics"))

    # key ideas
    body.append('<div class="rg-h">The ideas, in plain words</div>')
    ideas = "".join(f'<div class="rg-idea"><div class="t">{_esc(t)}</div><div class="d">{d}</div></div>'
                    for t, d in _IDEAS)
    body.append(f'<div class="rg-ideas">{ideas}</div>')

    # golden rule
    body.append(
        '<div class="rg-h">The one rule that matters most</div>'
        '<div class="rg-gold"><div class="t">Everything here describes the past — it never tells you what to do.</div>'
        '<p>These analytics tell you what <b>has</b> happened, with all the caveats stated on each page. <b>No chart '
        'on this site is a buy or sell signal.</b> They are for understanding the market\'s character and history — '
        'the decision is always yours. When a page shows a caveat (survivorship, “after the fact”, thin data), that '
        'is the honest fine print, not a footnote to skip.</p></div>')

    # where to go next
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
    assert r.text.count("<svg") >= 6 and "golden" not in r.text.lower()  # 6 example charts
    assert "The colour ribbon" in r.text and "in plain words" in r.text.lower()
    print("reading_guide_view selftest OK — page 200, 6 chart examples, ideas + golden rule")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
