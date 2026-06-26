"""Patearn v2 design system — the futuristic, isolated UI kit ("rework the theme").

The single source of visual truth for the v2 surface. A refined, layered, cool-dark
"instrument" language elevated to feel futuristic + premium + TRUSTWORTHY (the B2B
ask): hairline borders, glass edges, subtle aurora depth, a restrained electric
blue/cyan signature, tabular numerics, and micro-motion — never gamified, never neon.

Isolation (per ui-architecture-v2.md §0.8): brand-new module, ZERO `src` imports
(like glossary.py) — it cannot collide with the parallel chart-overhaul session that
owns dashboard.py/cockpit.py/stock_chart.py. v2 pages import THIS for chrome instead
of dashboard._shell, so the new theme is self-contained and the old screens are left
completely untouched (additive — nothing deleted, no functionality changed). The v2
surface grows beside the live product; the only gated step is the eventual nav
cut-over (one line in main.py), deferred until the tree frees.

Public API:
    css()                          -> the <style> block (include ONCE per page)
    shell(title, body, active=…)   -> a full futuristic page (topbar + sub-nav + body)
    topbar(active) / subnav(items) -> chrome pieces
    stat / pill / seg / card / badge / chart_host / cmdk_hint  -> components
    showcase()                     -> a demo page proving the language
Route: GET /dash/ui-kit  (the living style guide; gated include in main.py).
"""
from __future__ import annotations

import html as _html
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


def esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


# --- design tokens + base + components (the whole system in one stylesheet) ---
_CSS = """<style>
.uk, .uk *{box-sizing:border-box}
.uk{
  --bg-0:#070a10; --bg-1:#0b0f17; --bg-2:#111824; --bg-3:#18222f;
  --line:#1c2937; --line-2:#27384a;
  --ink:#eaf1f9; --ink-2:#9bb0c6; --ink-3:#5c6f84;
  --accent:#4d9dff; --accent-cy:#34e0d6; --accent-dim:rgba(77,157,255,.14);
  --up:#3fd486; --up-dim:rgba(63,212,134,.13);
  --down:#ff6a7a; --down-dim:rgba(255,106,122,.13);
  --warn:#f6b73c; --cred:#b18cff; --cred-dim:rgba(177,140,255,.15);
  --r:12px; --r-sm:8px; --r-lg:18px;
  --shadow:0 14px 36px rgba(0,0,0,.46); --glass:inset 0 1px 0 rgba(255,255,255,.045);
  --t:170ms cubic-bezier(.2,.7,.2,1);
  --font:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,'Helvetica Neue',Arial,sans-serif;
  --mono:'SF Mono',ui-monospace,'JetBrains Mono','Cascadia Code',Menlo,Consolas,monospace;
  font-family:var(--font); color:var(--ink); font-size:14px; line-height:1.5;
  -webkit-font-smoothing:antialiased; font-feature-settings:'tnum' 1, 'cv01' 1;
  background:
    radial-gradient(1100px 560px at 82% -12%, rgba(77,157,255,.07), transparent 60%),
    radial-gradient(860px 480px at -8% 8%, rgba(52,224,214,.05), transparent 55%),
    var(--bg-1);
  min-height:100%;
}
.uk .num{font-variant-numeric:tabular-nums; font-family:var(--mono)}
.uk a{color:var(--accent); text-decoration:none}
.uk .mut{color:var(--ink-3)} .uk .sec{color:var(--ink-2)}
.uk .up{color:var(--up)} .uk .down{color:var(--down)} .uk .cred{color:var(--cred)}

/* topbar */
.uk-top{display:flex;align-items:center;gap:18px;padding:11px 20px;position:sticky;top:0;z-index:30;
  background:linear-gradient(180deg, rgba(17,24,36,.92), rgba(11,15,23,.66));
  border-bottom:1px solid var(--line); backdrop-filter:blur(12px);}
.uk-logo{font-weight:600;letter-spacing:.4px;font-size:15px;display:flex;align-items:center;gap:9px;color:var(--ink)}
.uk-logo .dot{width:9px;height:9px;border-radius:50%;background:var(--accent-cy);box-shadow:0 0 11px var(--accent-cy)}
.uk-nav{display:flex;gap:3px}
.uk-nav a{padding:7px 13px;border-radius:9px;color:var(--ink-2);font-size:13px;font-weight:500;transition:var(--t)}
.uk-nav a:hover{color:var(--ink);background:var(--bg-2)}
.uk-nav a.on{color:var(--ink);background:var(--accent-dim);box-shadow:var(--glass)}
.uk-cmdk{margin-left:auto;display:inline-flex;align-items:center;gap:9px;padding:6px 11px;border:1px solid var(--line-2);
  border-radius:9px;color:var(--ink-3);font-size:12px;cursor:pointer;transition:var(--t);background:var(--bg-1)}
.uk-cmdk:hover{border-color:var(--accent);color:var(--ink-2)}
.uk-cmdk kbd{font-family:var(--mono);background:var(--bg-3);border:1px solid var(--line-2);border-radius:5px;padding:1px 6px;font-size:11px;color:var(--ink-2)}

/* sub-nav (one paradigm everywhere) */
.uk-sub{display:flex;gap:3px;padding:9px 20px;border-bottom:1px solid var(--line);background:rgba(11,15,23,.5);overflow-x:auto}
.uk-sub a{padding:5px 11px;border-radius:8px;font-size:12.5px;color:var(--ink-3);white-space:nowrap;transition:var(--t)}
.uk-sub a:hover{color:var(--ink-2);background:var(--bg-2)}
.uk-sub a.on{color:var(--ink);background:var(--bg-3);box-shadow:var(--glass)}
.uk-sub .grp{align-self:center;font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink-3);padding:0 4px 0 10px}

/* layout */
.uk-page{padding:22px 20px;max-width:1320px;margin:0 auto}
.uk-grid{display:grid;gap:14px}
.uk-row{display:flex;gap:14px;flex-wrap:wrap}
.uk-h1{font-size:22px;font-weight:600;margin:0 0 2px;letter-spacing:-.2px}

/* card */
.uk-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;box-shadow:var(--glass)}
.uk-card.lift{box-shadow:var(--glass),var(--shadow)}
.uk-card.accent{border-top:2px solid var(--accent)}
.uk-eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink-3);margin:0 0 11px;display:flex;align-items:center;gap:8px}

/* stat */
.uk-stat .lbl{font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.uk-stat .val{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums;font-family:var(--mono);line-height:1;color:var(--ink)}
.uk-stat .dl{font-size:12.5px;font-variant-numeric:tabular-nums;margin-top:5px}

/* pill / verdict */
.uk-pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.2px;white-space:nowrap}
.uk-pill.up{background:var(--up-dim);color:var(--up)}
.uk-pill.down{background:var(--down-dim);color:var(--down)}
.uk-pill.acc{background:var(--accent-dim);color:var(--accent)}
.uk-pill.cred{background:var(--cred-dim);color:var(--cred)}
.uk-pill.warn{background:rgba(246,183,60,.14);color:var(--warn)}
.uk-pill.neutral{background:var(--bg-3);color:var(--ink-2)}

/* segmented toggle (the ONE toggle) */
.uk-seg{display:inline-flex;border:1px solid var(--line-2);border-radius:9px;overflow:hidden;background:var(--bg-1)}
.uk-seg a{padding:6px 13px;font-size:12px;color:var(--ink-2);transition:var(--t);border-right:1px solid var(--line)}
.uk-seg a:last-child{border-right:none}
.uk-seg a.on{background:var(--accent-dim);color:var(--accent)}
.uk-seg a:hover:not(.on){background:var(--bg-2);color:var(--ink)}

/* table (frozen header + frozen first col, tabular) */
.uk-tw{overflow:auto;border:1px solid var(--line);border-radius:var(--r);background:var(--bg-2);max-height:70vh}
table.uk-t{width:100%;border-collapse:collapse;font-size:13px}
.uk-t th{position:sticky;top:0;background:var(--bg-3);color:var(--ink-3);font-size:10.5px;text-transform:uppercase;
  letter-spacing:.5px;font-weight:600;text-align:right;padding:10px 13px;white-space:nowrap;border-bottom:1px solid var(--line-2);z-index:2}
.uk-t th:first-child,.uk-t td:first-child{text-align:left;position:sticky;left:0;background:var(--bg-2)}
.uk-t th:first-child{z-index:3;background:var(--bg-3)}
.uk-t td{padding:10px 13px;text-align:right;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;color:var(--ink-2);white-space:nowrap}
.uk-t td.sym{color:var(--ink);font-weight:600;font-family:var(--font)}
.uk-t tbody tr{transition:background var(--t)}
.uk-t tbody tr:hover td{background:var(--bg-3)}

/* bounded chart host (the geometry fix, as a token) */
.uk-chart{position:relative;width:100%;max-width:1200px;height:clamp(420px,62vh,760px);
  border:1px solid var(--line);border-radius:var(--r);background:var(--bg-2);overflow:hidden}
.uk-chart .exp{position:absolute;top:10px;right:10px;width:26px;height:26px;display:flex;align-items:center;justify-content:center;
  border:1px solid var(--line-2);border-radius:7px;background:rgba(11,15,23,.7);color:var(--ink-2);cursor:pointer;font-size:13px;z-index:5;transition:var(--t)}
.uk-chart .exp:hover{border-color:var(--accent);color:var(--accent)}

/* provenance / PIT badge (trust signature) */
.uk-badge{display:inline-flex;align-items:center;gap:6px;font-size:10.5px;color:var(--ink-3);border:1px solid var(--line-2);border-radius:6px;padding:2px 8px}
.uk-badge .d{width:5px;height:5px;border-radius:50%;background:var(--accent-cy);box-shadow:0 0 6px var(--accent-cy)}

/* divergence shade helper for signature glyphs */
.uk-spark{display:block}
</style>"""


def css() -> str:
    return _CSS


# --- components --------------------------------------------------------------

def pill(text: str, kind: str = "neutral") -> str:
    return f'<span class="uk-pill {esc(kind)}">{esc(text)}</span>'


def badge(text: str) -> str:
    return f'<span class="uk-badge"><span class="d"></span>{esc(text)}</span>'


def stat(label: str, value: str, delta: str = "", direction: str = "") -> str:
    dl = f'<div class="dl {esc(direction)}">{esc(delta)}</div>' if delta else ""
    return (f'<div class="uk-stat"><div class="lbl">{esc(label)}</div>'
            f'<div class="val">{esc(value)}</div>{dl}</div>')


def seg(options: list[tuple[str, str, bool]]) -> str:
    """options = [(label, href, is_on), ...]"""
    inner = "".join(f'<a class="{"on" if on else ""}" href="{esc(href)}">{esc(lbl)}</a>'
                    for lbl, href, on in options)
    return f'<div class="uk-seg">{inner}</div>'


def card(body: str, *, eyebrow: str = "", cls: str = "") -> str:
    eb = f'<div class="uk-eyebrow">{eyebrow}</div>' if eyebrow else ""
    return f'<div class="uk-card {esc(cls)}">{eb}{body}</div>'


def chart_host(host_id: str = "ukChart", inner: str = "") -> str:
    return (f'<div class="uk-chart" id="{esc(host_id)}">'
            f'<div class="exp" title="Fullscreen (Shift+F)">⤢</div>{inner}</div>')


def cmdk_hint() -> str:
    return '<div class="uk-cmdk">Search or ask Pat <kbd>⌘K</kbd></div>'


_NAV = [("markets", "Markets"), ("screener", "Screener"),
        ("strategies", "Strategies"), ("tracker", "Tracker")]


def nav_links(items) -> str:
    """Render the COMPLETE site nav as uk-nav anchors. ``items`` = [(href, label,
    is_on), ...]. Used so a v2 (ui_kit) page carries the identical destination set
    as the rest of the site — no dead-ends, one nav contract (the source of that
    list is v2_surfaces.site_nav, kept dependency-free here)."""
    return "".join(
        f'<a class="{"on" if on else ""}" href="{esc(href)}">{esc(lbl)}</a>'
        for href, lbl, on in items)


def topbar(active: str = "", nav_html: str = "") -> str:
    # nav_html (when given) is the full site nav rendered by v2_surfaces/nav_links;
    # the built-in _NAV is only the offline fallback for the standalone style guide.
    if not nav_html:
        nav_html = "".join(
            f'<a class="{"on" if k == active else ""}" href="/dash/{k}">{esc(lbl)}</a>'
            for k, lbl in _NAV)
    return (f'<div class="uk-top"><div class="uk-logo"><span class="dot"></span>patearn</div>'
            f'<nav class="uk-nav">{nav_html}</nav>{cmdk_hint()}</div>')


def subnav(items: list[tuple[str, str, bool]]) -> str:
    """items = [(label, href, is_on), ...]; a leading (label, '', False) renders a group tag."""
    out = []
    for lbl, href, on in items:
        if not href:
            out.append(f'<span class="grp">{esc(lbl)}</span>')
        else:
            out.append(f'<a class="{"on" if on else ""}" href="{esc(href)}">{esc(lbl)}</a>')
    return f'<div class="uk-sub">{"".join(out)}</div>'


def shell(title: str, body: str, *, active: str = "", sub: str = "", nav_html: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title>{_CSS}</head>'
            f'<body style="margin:0"><div class="uk">{topbar(active, nav_html)}{sub}'
            f'<div class="uk-page">{body}</div></div></body></html>')


# --- the living style guide (visual proof of the language) -------------------

def _demo_table() -> str:
    rows = [
        ("RELIANCE", "1,412", "+1.2%", "up", "84", "72 ↑", "Accumulate", "acc"),
        ("PERSISTENT", "5,940", "+2.8%", "up", "91", "78 ↑", "Leader", "up"),
        ("VEDL", "468", "-0.9%", "down", "63", "61 ↑", "Re-rating", "cred"),
        ("KIRLOSENG", "1,205", "+0.4%", "up", "77", "55 ↓", "Watch", "warn"),
        ("IDEA", "9.1", "-3.4%", "down", "22", "31 ↓", "Avoid", "down"),
    ]
    head = ("<tr><th>Symbol</th><th>Price</th><th>%Chg</th><th>RS#</th>"
            "<th>CCI</th><th>Verdict</th></tr>")
    body = ""
    for sym, px, chg, d, rs, cci, verdict, vk in rows:
        body += (f'<tr><td class="sym">{sym}</td><td class="num">{px}</td>'
                 f'<td class="num {d}">{chg}</td><td class="num">{rs}</td>'
                 f'<td class="num cred">{cci}</td><td style="text-align:right">{pill(verdict, vk)}</td></tr>')
    return f'<div class="uk-tw"><table class="uk-t"><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def showcase_body() -> str:
    stats = "".join(f'<div class="uk-card" style="flex:1;min-width:150px">{s}</div>' for s in [
        stat("Price", "1,412.30", "+1.2% · +16.4", "up"),
        stat("RS rank", "84", "improving", "up"),
        stat("CCI credibility", "72", "+3 this qtr", "up"),
        stat("MEP phase", "Accum", "8 sessions", "up"),
    ])
    pills = " ".join([pill("Leader", "up"), pill("Accumulate", "acc"),
                      pill("Credibility ↑", "cred"), pill("Re-rating window", "warn"),
                      pill("Avoid", "down"), pill("Neutral", "neutral")])
    toggles = seg([("vs Nifty 500", "#", True), ("vs Nifty 50", "#", False)])
    return f"""
<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">
  <h1 class="uk-h1">RELIANCE Industries</h1>{pill("MARKET LEADER", "acc")}
  {badge("point-in-time · zero look-ahead")}
</div>
<div class="sec" style="margin-bottom:18px">Reliance Industries Ltd · Energy · Nifty 50 · the v2 design language, applied</div>

<div class="uk-row" style="margin-bottom:14px">{stats}</div>

<div class="uk-row" style="margin-bottom:14px">
  <div class="uk-card lift" style="flex:2;min-width:340px">
    <div class="uk-eyebrow">Price · volume · DVPT — one bounded, fullscreen chart {badge("clamp 420–760px")}</div>
    {chart_host("demoChart", '<div style="position:absolute;inset:40px 16px 16px;border-left:1px solid var(--line);border-bottom:1px solid var(--line)"><svg viewBox="0 0 600 230" width="100%" height="100%" preserveAspectRatio="none"><polyline points="0,180 60,150 120,165 180,120 240,140 300,95 360,110 420,70 480,84 540,40 600,55" fill="none" stroke="#3fd486" stroke-width="2"/></svg></div>')}
  </div>
  <div class="uk-card" style="flex:1;min-width:240px">
    <div class="uk-eyebrow">Benchmark</div>
    <div style="margin-bottom:14px">{toggles}</div>
    <div class="uk-eyebrow">Verdict language</div>
    <div style="display:flex;gap:7px;flex-wrap:wrap">{pills}</div>
  </div>
</div>

<div class="uk-card" style="margin-bottom:6px">
  <div class="uk-eyebrow">Frozen-pane data grid — one table, everywhere {badge("tabular numerics")}</div>
  {_demo_table()}
</div>
"""


@router.get("/dash/ui-kit", response_class=HTMLResponse)
def ui_kit_page() -> HTMLResponse:
    sub = subnav([("Markets", "/dash/markets", False), ("Design system", "/dash/ui-kit", True)])
    return HTMLResponse(shell("Design system · patearn", showcase_body(), active="markets", sub=sub))
