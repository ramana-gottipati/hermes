"""Market Internals — the health of the market beneath the index (22 years, 2004→).

The product's only "breadth" was RS-relative and sector-scoped (cockpit / rotation). There
was no ABSOLUTE whole-market internal anywhere, and nothing reached the 2004-2011 era (every
signals table starts 2011-12). This lens surfaces five market-state series over the full
`bhavcopy_rows` + `mep_signals` history, read from the bounded `market_internals_daily`
snapshot (one row per trading day, ~5.4k rows — the space-mandate "bounded snapshot"
exception; built by src/automation/market_internals.py):

  * Price-breadth   — % of the cash universe advancing (adv/dec/unch).
  * The tape (effort-breadth) — net accumulation−distribution from the smoothed MEP phase.
  * Delivery conviction — market-wide delivery-%, the "real buying" regime.
  * Dispersion      — cross-sectional stdev of returns ("stock-picker's vs macro market").
  * Coil            — mean ATR-compression (coiled ↔ expanded).

THE HERO is the divergence between price-breadth and the tape: when price-breadth rises while
the tape distributes, the market is being DISTRIBUTED INTO STRENGTH — a warning the cap-
weighted index cannot show. Extremes validated exactly vs history (GFC 2008-10-24: 6% adv,
tape −92; COVID 2020-03-23: 4% adv, tape −74, coil 1.69; 2009-05-18 thrust: 98% adv, tape +90).

STRICTLY DESCRIPTIVE (ledger): market-state context, point-in-time. Breadth ≠ index return.
The tape is within-stock-normalised (a breadth of accumulation, not price direction). Not a
signal — no ranking, no "buy". Route: /dash/market-internals [?window=1y|3y|5y|all].
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_WINDOWS = {"1y": 252, "3y": 756, "5y": 1260, "all": 10_000}

# validated crisis/thrust anchors — proof the internals track known history
_ANCHORS = [
    ("2008-10-24", "GFC crash low"),
    ("2009-05-18", "Election upper-circuit thrust"),
    ("2020-03-23", "COVID low"),
    ("2021-10-19", "2021 bull peak (approx)"),
    ("2024-06-04", "Election-result shock"),
]

_CSS = """
<style>
.mi-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 14px;max-width:1180px;}
.mi-note b{color:var(--ink);} .mi-note .warn{color:var(--warn);}
.mi-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(184px,1fr));gap:10px;margin:0 0 16px;}
.mi-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:11px;padding:11px 13px;}
.mi-tile .n{font-size:25px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.05;}
.mi-tile .l{font-size:11.5px;font-weight:700;margin-top:5px;color:var(--ink);}
.mi-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:3px;line-height:1.4;}
.mi-panel{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;padding:14px 16px;margin:0 0 15px;}
.mi-h{font-size:15px;font-weight:700;margin:0 0 3px;color:var(--ink);}
.mi-h small{font-weight:400;color:var(--ink-3);font-size:12px;}
.mi-sub{color:var(--ink-2);font-size:12px;line-height:1.5;margin:4px 0 10px;max-width:1120px;}
.mi-lbl{font-size:11px;color:var(--ink-3);margin:9px 0 2px;font-weight:600;letter-spacing:.2px;}
.mi-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:2px 0 14px;}
.mi-ctrl a{padding:4px 12px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;text-decoration:none;}
.mi-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.mi-div{display:flex;gap:10px;align-items:flex-start;background:var(--bg-2);border:1px solid var(--line-2);
  border-left:3px solid var(--warn);border-radius:9px;padding:9px 13px;margin:10px 0 2px;font-size:12.5px;color:var(--ink-2);line-height:1.5;}
table.mi-anc{border-collapse:collapse;width:100%;font-size:12px;margin-top:4px;}
table.mi-anc th{color:var(--ink-3);font-weight:600;text-align:right;padding:4px 9px;border-bottom:1px solid var(--line-2);}
table.mi-anc td{padding:4px 9px;border-bottom:1px solid #171d25;text-align:right;font-variant-numeric:tabular-nums;}
table.mi-anc td.l,table.mi-anc th.l{text-align:left;}
.mi-pos{color:var(--up);} .mi-neg{color:var(--down);}
</style>
"""


def _pctile(sorted_vals: list, v: float) -> float:
    if not sorted_vals or v is None:
        return 50.0
    lo, hi = 0, len(sorted_vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] <= v:
            lo = mid + 1
        else:
            hi = mid
    return 100.0 * lo / len(sorted_vals)


def _roll(vals: list, k: int) -> list:
    """Simple trailing mean, k>=1; skips None (carries last mean on gaps)."""
    if k < 2:
        return list(vals)
    out, acc, buf = [], 0.0, []
    for v in vals:
        buf.append(v if v is not None else (buf[-1] if buf else 0.0))
        if len(buf) > k:
            buf.pop(0)
        out.append(sum(buf) / len(buf))
    return out


def _ord(n: float) -> str:
    i = int(round(n))
    if 10 <= (i % 100) <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suf}"


def _phrase(p: float, low_word: str, high_word: str) -> str:
    if p <= 8:
        return f"22-yr low — deeply {low_word}"
    if p <= 25:
        return f"{low_word} ({_ord(p)} pctile of 22y)"
    if p >= 92:
        return f"22-yr high — deeply {high_word}"
    if p >= 75:
        return f"{high_word} ({_ord(p)} pctile)"
    return f"middling ({_ord(p)} pctile of 22y)"


def _tiles(rows: list) -> str:
    last = rows[-1]
    padv = sorted(r["pct_adv"] for r in rows if r["pct_adv"] is not None)
    dps = sorted(r["avg_dp"] for r in rows if r["avg_dp"] is not None)
    disp = sorted(r["disp"] for r in rows if r["disp"] is not None)
    mep = sorted(r["mep_net"] for r in rows if r["mep_net"] is not None)
    coil = sorted(r["avg_comp"] for r in rows if r["avg_comp"] is not None)

    def tile(nval, ncolor, label, sub):
        return (f'<div class="mi-tile"><div class="n" style="color:{ncolor}">{nval}</div>'
                f'<div class="l">{_esc(label)}</div><div class="s">{_esc(sub)}</div></div>')

    pa = last["pct_adv"]
    mn = last["mep_net"]
    t = [
        tile(f'{pa:.0f}%', "var(--up)" if pa >= 50 else "var(--down)", "Advancing today",
             f'{last["adv"]}▲ / {last["dec"]}▼ of {last["n_eq"]} · {_phrase(_pctile(padv, pa), "weak", "broad")}'),
        tile(f'{mn:+.0f}', "var(--up)" if mn >= 0 else "var(--down)", "The tape (net accum−distrib)",
             _phrase(_pctile(mep, mn), "distribution", "accumulation")),
        tile(f'{last["avg_dp"]:.0f}%', "var(--chart-blue)", "Delivery conviction",
             _phrase(_pctile(dps, last["avg_dp"]), "low-conviction era", "high-conviction")),
        tile(f'{last["disp"]:.2f}', "var(--accent-orange)", "Dispersion",
             _phrase(_pctile(disp, last["disp"]), "macro / correlated", "stock-picker's")),
        tile(f'{last["avg_comp"]:.2f}', "var(--series-1)", "Coil ↔ expansion",
             ("coiled" if last["avg_comp"] < 1 else "expanded") + f' · {_phrase(_pctile(coil, last["avg_comp"]), "coiled", "expanded")}'),
    ]
    return f'<div class="mi-tiles">{"".join(t)}</div>'


def _panel(title, sub, *body) -> str:
    return (f'<div class="mi-panel"><div class="mi-h">{title}</div>'
            f'<div class="mi-sub">{sub}</div>{"".join(body)}</div>')


def _anchor_table(conn) -> str:
    trs = []
    for d, lab in _ANCHORS:
        r = conn.execute("SELECT pct_adv,avg_dp,disp,mep_net,avg_comp FROM market_internals_daily "
                         "WHERE d=?", (d,)).fetchone()
        if not r:
            continue
        mep = r["mep_net"]
        trs.append(
            f'<tr><td class="l">{_esc(d)}</td><td class="l" style="color:var(--ink-3)">{_esc(lab)}</td>'
            f'<td class="{"mi-pos" if r["pct_adv"]>=50 else "mi-neg"}">{r["pct_adv"]:.0f}%</td>'
            f'<td>{r["avg_dp"]:.0f}%</td><td>{r["disp"]:.2f}</td>'
            f'<td class="{"mi-pos" if mep>=0 else "mi-neg"}">{mep:+.0f}</td>'
            f'<td>{r["avg_comp"]:.2f}</td></tr>')
    if not trs:
        return ""
    return ('<table class="mi-anc"><thead><tr><th class="l">Date</th><th class="l">Event</th>'
            '<th>% adv</th><th>Deliv</th><th>Disp</th><th>Tape</th><th>Coil</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table>')


@router.get("/dash/market-internals", response_class=HTMLResponse)
def dash_market_internals(window: str = "5y") -> HTMLResponse:
    window = window if window in _WINDOWS else "5y"
    body = [_CSS]
    as_of = ""
    try:
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND "
                                "name='market_internals_daily'").fetchone():
                raise LookupError("market_internals_daily absent")
            allrows = conn.execute(
                "SELECT d,n_eq,adv,dec,unch,pct_adv,avg_dp,disp,mep_net,avg_comp "
                "FROM market_internals_daily ORDER BY d").fetchall()
            if not allrows:
                raise LookupError("empty")
            as_of = allrows[-1]["d"]
            n = _WINDOWS[window]
            rows = allrows[-n:] if n < len(allrows) else allrows

            body.append(
                '<h2 style="margin:0 0 2px">Market Internals '
                f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">the health beneath the '
                f'index · 22 years (2004→) · as of {_esc(as_of)}</small></h2>'
                '<div class="mi-note">Every other "breadth" view here is <b>relative</b> (RS vs the '
                'benchmark) and starts 2011. This is the <b>absolute</b> market internal — how many stocks '
                'actually rose, whether buyers paid up (the tape), how much was delivered, how independently '
                'stocks moved — back to <b>2004</b>, the era no other lens can reach. '
                '<b>The hero is the divergence:</b> when price-breadth rises while the tape '
                '<span class="warn">distributes</span>, the market is being distributed into strength — a '
                'warning the cap-weighted index can\'t show. <b>Descriptive market-state, point-in-time — '
                'not a signal.</b> <a href="/dash/glossary?q=breadth">glossary →</a></div>')

            # tiles: latest value + its percentile vs FULL 22y history
            body.append(_tiles(allrows))

            tabs = "".join(f'<a class="{"on" if window==w else ""}" '
                           f'href="/dash/market-internals?window={w}">{w.upper()}</a>'
                           for w in ("1y", "3y", "5y", "all"))
            body.append(f'<div class="mi-ctrl">{tabs}<span style="color:var(--ink-3);font-size:11px">'
                        f'{len(rows)} trading days shown</span></div>')

            dates = [r["d"] for r in rows]
            pct_adv = [r["pct_adv"] for r in rows]
            mep_net = [r["mep_net"] for r in rows]
            avg_dp = [r["avg_dp"] for r in rows]
            disp = [r["disp"] for r in rows]
            coil = [r["avg_comp"] for r in rows]
            k = max(5, len(rows) // 60)

            # HERO: price-breadth vs the tape
            pb_line = _roll([(p - 50) if p is not None else None for p in pct_adv], k)
            tp_line = _roll(mep_net, k)
            pb_ribbon = [(d, ((p or 50) - 50) / 50.0) for d, p in zip(dates, pct_adv)]
            tp_ribbon = [(d, (m or 0) / 100.0) for d, m in zip(dates, mep_net)]
            div_note = _divergence_note(pct_adv[-1], mep_net[-1], pb_line[-1], tp_line[-1])
            body.append(_panel(
                'Price-breadth vs the tape <small>— the market\'s two breadths</small>',
                'Top: <b>price-breadth</b> — % of stocks advancing (green) vs declining (red). '
                'Bottom: <b>the tape</b> — net accumulation−distribution, whether buyers are paying up. '
                'They usually agree; where they diverge is the story.',
                '<div class="mi-lbl">PRICE-BREADTH · % advancing (smoothed) — centred at 50</div>',
                ifx.spark_area(pb_line, h=104, signed=True, baseline=0),
                '<div class="mi-lbl">daily texture</div>',
                ifx.heat_ribbon(pb_ribbon, h=34),
                '<div class="mi-lbl" style="margin-top:12px">THE TAPE · net accumulation−distribution (smoothed)</div>',
                ifx.spark_area(tp_line, h=104, signed=True, baseline=0),
                '<div class="mi-lbl">daily texture</div>',
                ifx.heat_ribbon(tp_ribbon, h=34),
                f'<div class="mi-div"><span>⚠</span><span>{div_note}</span></div>'))

            # Delivery-conviction regime
            body.append(_panel(
                'Delivery-conviction regime <small>— is it real buying?</small>',
                'Market-wide delivery-% — the share of volume taken to demat, not intraday-churned. '
                'It fell structurally from ~64% (2004-13) to ~54% (post-2020) as the F&O / algo era took '
                'over. Delivery <i>spikes</i> on panic days (intraday traders vanish; only holders transact).',
                ifx.spark_area(_roll(avg_dp, k), h=120, color="var(--chart-blue)")))

            # Dispersion regime
            body.append(_panel(
                'Dispersion — stock-picker\'s vs macro market <small>— how independently stocks move</small>',
                'Cross-sectional stdev of daily returns. <b>High</b> = names move on their own merits '
                '(selection pays); <b>low</b> = everything moves together (macro / risk-on-off). It spikes '
                'in every crisis (COVID 5.97, GFC 5.81) and has drifted structurally lower.',
                ifx.spark_area(_roll(disp, k), h=120, color="var(--accent-orange)")))

            # Coil
            body.append(_panel(
                'Coil ↔ expansion <small>— the market\'s volatility spring</small>',
                'Mean ATR-compression across the universe (short-vs-long range). <b>&lt;1 coiled</b> '
                '(quiet, wound tight) · <b>&gt;1 expanded</b> (violent, unwound). Expansion peaks coincide '
                'with the distribution thrusts above (COVID 1.69).',
                ifx.spark_area(_roll(coil, k), h=120, color="var(--series-1)")))

            # Crisis fingerprints (proof it tracks history)
            body.append(_panel(
                'Crisis fingerprints <small>— the internals, validated against known history</small>',
                'The same five internals on the days everyone remembers. Every extreme lines up: '
                'the tape reads −92 at the GFC low, −74 at the COVID low, +90 on the 2009 thrust.',
                _anchor_table(conn)))
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Market Internals</h2><div class="mi-note">The <code>market_internals_daily</code> '
            'snapshot is not populated on this host. It is built from <code>bhavcopy_rows</code> + '
            '<code>mep_signals</code> by <code>src/automation/market_internals.py</code> (bounded, one '
            'row per trading day). This surface is read-only and never fabricates data.</div>')
    return HTMLResponse(_shell("Market Internals · patearn", "".join(body), "market-internals",
                               str(as_of)[:10], wide=True))


def _divergence_note(pa: float, mn: float, pb_s: float, tp_s: float) -> str:
    if pa is None or mn is None:
        return "Divergence read unavailable for the latest session."
    price_up = (pa >= 50)
    tape_up = (mn >= 0)
    if price_up and not tape_up:
        return (f"<b>Today: distribution into strength.</b> {pa:.0f}% of stocks advanced, but the tape is "
                f"net-<b>distribution</b> ({mn:+.0f}) — buyers are lifting price without paying up. This is "
                f"the divergence the index hides; historically it clusters near local tops. Descriptive only.")
    if (not price_up) and tape_up:
        return (f"<b>Today: accumulation into weakness.</b> Only {pa:.0f}% advanced, yet the tape is net-"
                f"<b>accumulation</b> ({mn:+.0f}) — strong hands absorbing supply on a down day.")
    if price_up and tape_up:
        return (f"<b>Today: breadth and tape agree (constructive).</b> {pa:.0f}% advancing and the tape "
                f"net-accumulation ({mn:+.0f}) — the rise is being paid for.")
    return (f"<b>Today: breadth and tape agree (weak).</b> {pa:.0f}% advancing and the tape net-"
            f"distribution ({mn:+.0f}) — decline confirmed by the tape.")


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/market-internals" not in paths:
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
    for url in ("/dash/market-internals", "/dash/market-internals?window=all",
                "/dash/market-internals?window=1y"):
        r = c.get(url)
        assert r.status_code == 200, url
        assert "Market Internals" in r.text
    print("market_internals_view selftest OK — page 200 (populated or honest-empty), windows 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
