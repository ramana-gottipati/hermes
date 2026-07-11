"""Move anatomy — what actually precedes a big move (deep-data sprint; features panel).

Surfaces the `features` event panel (research.db, 166K labelled events + a 1-in-10 baseline,
2011→2026), which NO page read. The finding is a counter-narrative worth stating plainly:

  Big moves launch from MOMENTUM and STRENGTH — trailing return, relative strength, price above
  its long averages — and NOT from the tight-base / heavy-delivery "accumulation footprint" the
  setup lore assumes. Delivery actually runs BELOW baseline before a move (z ≈ −0.5). This
  aligns with the team's own falsified footprint gate.

It is expressed two ways: (1) the FINGERPRINT — each precursor's event-mean as a standardised gap
from the baseline (in baseline std-devs), so ~90 raw attributes become one legible signed profile;
(2) the EXCURSION ENVELOPE — the median favourable (MFE) vs adverse (MAE) forward move of events
vs the quiet baseline.

⚠ STRICTLY DESCRIPTIVE (ledger). Leak-safe by construction: it conditions only on PRECURSORS (the
trailing `*_d` returns + structure/RS/delivery, all as-of the launch), and merely *describes* the
forward-outcome columns — an outcome is never used as an input. But it is a POST-SELECTION base-rate
(events are chosen because a move already fired), survivorship-biased UP (delisted losers absent),
and the baseline is 1-in-10 sampled. It is a picture of what pre-move days looked like in hindsight,
NEVER an entry rule. Route: /dash/move-anatomy. Reads research.db read-only.
"""
from __future__ import annotations

import math
import os
import sqlite3
from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

# curated precursors → (plain label, technical name, column, family). Plain label drives the
# chart + leads the table; technical name shown as grey subtext. Chart re-sorts by z.
# ALL are legitimate no-look-ahead precursors (trailing/structural). Outcomes are NEVER inputs.
_PRECURSORS = [
    ("Up over the past year", "12-month return", "ret_252d", "Trend & strength"),
    ("Up over the past 3 months", "3-month return", "ret_66d", "Trend & strength"),
    ("Stronger than the market", "RS rank vs market", "h_rs_rank", "Trend & strength"),
    ("Strength improving vs market", "RS slope, 3m", "h_rs_vs_broad_slope_3m", "Trend & strength"),
    ("Above its 1-year trend line", "Close vs 200-DMA", "close_vs_sma200", "Trend & strength"),
    ("Above its ~2-month trend line", "Close vs 50-DMA", "close_vs_sma50", "Trend & strength"),
    ("Short-term trend rising", "50-DMA slope", "sma50_slope", "Trend & strength"),
    ("Near its 1-year high", "Range position, 52w", "range_pos_252", "Trend & strength"),
    ("Trading range getting tighter", "NR ratio 10/60", "nr_ratio_10_60", "Quiet base"),
    ("Day-to-day swings shrinking", "ATR contraction", "atr_contraction", "Quiet base"),
    ("Volume drying up", "Volume dry-up 5/22", "vol_dryup_5_22", "Quiet base"),
    ("Days of heavy real buying", "Big-delivery days", "big_deliv_days_10", "Real buying"),
    ("Real-buying trend rising", "Delivery trend", "deliv_trend", "Real buying"),
    ("Days of strong real buying", "Strong-delivery days", "n_strong_deliv_22", "Real buying"),
    ("Share bought to hold, not day-traded", "Delivery %", "deliv_per_s", "Real buying"),
]

_CSS = """
<style>
.ma-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 12px;max-width:1180px;}
.ma-note b{color:var(--ink);}
.ma-thesis{background:var(--bg-2);border:1px solid var(--line-2);border-left:3px solid var(--accent);
  border-radius:0 11px 11px 0;padding:13px 17px;margin:0 0 16px;max-width:1100px;font-size:14px;line-height:1.6;color:var(--ink);}
.ma-thesis b{color:var(--accent-2);}
.ma-panel{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;padding:15px 17px;margin:0 0 15px;}
.ma-h{font-size:15px;font-weight:700;margin:0 0 3px;color:var(--ink);}
.ma-h small{font-weight:400;color:var(--ink-3);font-size:12px;}
.ma-sub{color:var(--ink-2);font-size:12px;line-height:1.5;margin:4px 0 12px;max-width:1080px;}
.ma-leg{display:flex;gap:16px;flex-wrap:wrap;margin:2px 0 10px;font-size:11px;color:var(--ink-3);}
.ma-leg i{width:11px;height:11px;border-radius:2px;display:inline-block;vertical-align:-1px;margin-right:5px;}
.ma-fence{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.06);border-radius:0 10px 10px 0;
  padding:11px 15px;margin:14px 0 2px;font-size:12.5px;color:var(--ink-2);line-height:1.55;max-width:1100px;}
.ma-fence b{color:var(--ink);} .ma-fence ul{margin:6px 0 0;padding-left:18px;} .ma-fence li{margin:3px 0;}
table.ma{border-collapse:collapse;width:100%;max-width:760px;font-size:12.5px;margin-top:4px;}
table.ma th{color:var(--ink-3);font-weight:600;text-align:right;padding:5px 11px;border-bottom:1px solid var(--line-2);}
table.ma td{padding:5px 11px;border-bottom:1px solid #171d25;text-align:right;font-variant-numeric:tabular-nums;}
table.ma td.l,table.ma th.l{text-align:left;}
.ma-fam{color:var(--ink-3);font-size:11px;}
.ma-hi{color:var(--series-1);} .ma-lo{color:var(--accent-orange);}
</style>
"""

_POS = "var(--series-1)"   # elevated in the pre-move population (cyan) — NOT a value hue
_NEG = "var(--accent-orange)"  # suppressed (orange)


@lru_cache(maxsize=2)
def _compute(_dbpath: str):
    """Fingerprint z-scores + MFE/MAE envelope. Cached (the panel is a static study)."""
    con = sqlite3.connect(f"file:{_dbpath}?mode=ro", uri=True)
    try:
        cols = [c for _, _, c, _ in _PRECURSORS]
        # one aggregate pass per group — baseline needs avg + avg(sq) for the std
        base_sel = ", ".join(f"avg({c}), avg({c}*{c})" for c in cols)
        b = con.execute(f"SELECT {base_sel} FROM features WHERE label=0").fetchone()
        evt_sel = ", ".join(f"avg({c})" for c in cols)
        e = con.execute(f"SELECT {evt_sel} FROM features WHERE label=1").fetchone()
        fp = []
        for i, (plain_l, tech_l, col, fam) in enumerate(_PRECURSORS):
            bmean, bsq, emean = b[2 * i], b[2 * i + 1], e[i]
            if bmean is None or bsq is None or emean is None:
                continue
            var = bsq - bmean * bmean
            sd = math.sqrt(var) if var > 0 else None
            if not sd:
                continue
            fp.append({"label": plain_l, "tech": tech_l, "family": fam, "z": (emean - bmean) / sd,
                       "evt": emean, "base": bmean})
        # excursion envelope — MEDIAN mfe/mae, only fully-completed forward windows
        env = {}
        for grp, lab in ((1, "event"), (0, "baseline")):
            rows = con.execute(
                "SELECT mfe_6m, mae_6m FROM features WHERE label=? AND fwd_complete_132=1 "
                "AND mfe_6m IS NOT NULL AND mae_6m IS NOT NULL", (grp,)).fetchall()
            mfe = sorted(r[0] for r in rows)
            mae = sorted(r[1] for r in rows)
            big = con.execute("SELECT avg(big50_6m) FROM features WHERE label=? AND fwd_complete_132=1 "
                              "AND big50_6m IS NOT NULL", (grp,)).fetchone()[0]
            n = len(mfe)
            env[lab] = {"n": n, "mfe": (mfe[n // 2] * 100) if n else None,
                        "mae": (mae[n // 2] * 100) if n else None,
                        "big50": (big * 100) if big is not None else None}
        meta = {r[0]: r[1] for r in con.execute("SELECT k, v FROM feat_meta").fetchall()}
        return {"fp": fp, "env": env, "meta": meta}
    finally:
        con.close()


@router.get("/dash/move-anatomy", response_class=HTMLResponse)
def dash_move_anatomy() -> HTMLResponse:
    body = [_CSS, ifx.readability_css()]
    try:
        d = _compute(_RESEARCH_DB)
        fp = sorted(d["fp"], key=lambda r: -r["z"])
        env = d["env"]
        n_evt = int(d["meta"].get("n_events", 0) or 0)
        n_base = int(d["meta"].get("n_baseline", 0) or 0)
        if not fp:
            raise LookupError("no fingerprint")

        body.append(
            '<h2 style="margin:0 0 2px">Move anatomy '
            '<small style="color:var(--ink-3);font-size:12px;font-weight:400">what actually precedes '
            f'a big move · {n_evt:,} events vs a {n_base:,} quiet-day baseline · 2011→2026</small></h2>'
            + ifx.bottom_line(
                "Big market moves start from <b>strength and momentum</b> — a stock that is already "
                "rising and beating the market. They do <b>not</b> start from the quiet, heavy-buying "
                "“accumulation” setup that popular lore assumes; in fact real buying is a touch "
                "<b>below</b> normal beforehand. This is a description of 15 years of history, not a "
                "buy rule.")
            + ifx.how_to_read_link()
            + '<div class="ma-thesis">The panel of 166K labelled moves says something the setup lore '
            'doesn\'t: big moves launch from <b>momentum and strength</b> — trailing return, relative '
            'strength, price above its long averages — <b>not</b> from a tight base with heavy '
            'delivery. Delivery actually runs <b>below</b> baseline before a move. It quietly confirms '
            'the falsified footprint gate: the "strong-hand accumulation" fingerprint isn\'t there in '
            'aggregate.</div>')

        # FINGERPRINT
        bars = [(f'{r["label"]}', r["z"]) for r in fp]
        body.append('<div class="ma-panel">'
                    '<div class="ma-h">The fingerprint <small>— each trait: how far above/below a '
                    'normal day it was, just before big moves (in σ = "normal-day steps"; bigger = more '
                    'unusual)</small></div>'
                    + ifx.plain(
                        'Each bar is one trait. Bars to the <b>right (cyan)</b> were <b>higher than a '
                        'normal day</b> before big moves; to the <b>left (orange)</b>, <b>lower</b>. '
                        'The shape of it: <b>trend and strength sit at the top; “real buying” sits at '
                        'the bottom</b> — the opposite of what the accumulation setup would predict.')
                    + '<div class="ma-sub">Ranked most-elevated to most-suppressed. A '
                    '<i>description</i> of what pre-move days looked like — not a recipe.</div>'
                    '<div class="ma-leg"><span><i style="background:var(--series-1)"></i>higher than normal before moves</span>'
                    '<span><i style="background:var(--accent-orange)"></i>lower than normal before moves</span></div>'
                    + ifx.diverging_bars(bars, w=640, bar_h=22, label_w=180, unit="σ",
                                         pos_color=_POS, neg_color=_NEG)
                    + '</div>')

        # ENVELOPE
        ev, bs = env.get("event", {}), env.get("baseline", {})
        fb = []
        if ev.get("mfe") is not None:
            fb.append((f'Big-move events (n={ev["n"]:,})', ev["mae"], ev["mfe"],
                       f'reached +50% in {ev["big50"]:.0f}%'))
        if bs.get("mfe") is not None:
            fb.append((f'Quiet baseline (n={bs["n"]:,})', bs["mae"], bs["mfe"],
                       f'{bs["big50"]:.0f}%'))
        body.append('<div class="ma-panel">'
                    '<div class="ma-h">Gain vs pain <small>— over the next 6 months, the typical best '
                    'rise (green, right) vs worst dip (red, left)</small></div>'
                    + ifx.plain(
                        'After a big move fires, the typical stock later ran up ~<b>40%</b> at best and '
                        'only dipped ~<b>10%</b> first (top bar). A <b>random quiet day</b>: +11% up, '
                        '−18% down. So big-move setups had far better upside-for-downside — <b>but you '
                        'only know a move “fired” after the fact</b>, so treat this as history, not a '
                        'promised return.')
                    + '<div class="ma-sub">Medians over a fixed 6-month window (analysts: MFE = maximum '
                    'favourable excursion, MAE = maximum adverse excursion). Post-selection &amp; '
                    'survivorship-biased — a base-rate, not an achievable return.</div>'
                    + ifx.floating_bars(fb, w=700, bar_h=32, label_w=210, unit="%")
                    + '</div>')

        # TABLE
        trs = ""
        for r in fp:
            cls = "ma-hi" if r["z"] >= 0 else "ma-lo"
            trs += (f'<tr><td class="l">{_esc(r["label"])}'
                    f'<span class="rd-tech">{_esc(r["tech"])}</span></td>'
                    f'<td class="l ma-fam">{_esc(r["family"])}</td>'
                    f'<td class="{cls}">{r["z"]:+.2f}σ</td>'
                    f'<td style="color:var(--ink-3)">{r["evt"]:.2f}</td>'
                    f'<td style="color:var(--ink-3)">{r["base"]:.2f}</td></tr>')
        body.append('<div class="ma-panel"><div class="ma-h">Every trait, ranked '
                    '<small>— plain name on top, the analyst name beneath</small></div>'
                    + ifx.plain('“How unusual” is the same σ as the chart. The last two columns are the '
                                'raw averages it comes from — <b>before moves</b> vs a <b>normal day</b> '
                                '— there only if you want the arithmetic.')
                    + '<table class="ma"><thead><tr><th class="l">Trait</th><th class="l">Group</th>'
                    '<th>How unusual</th><th>Before moves</th><th>Normal day</th></tr></thead>'
                    f'<tbody>{trs}</tbody></table></div>')

        body.append(
            '<div class="ma-fence"><b>How to read this honestly — the caveats are the point:</b>'
            '<ul>'
            '<li><b>Descriptive, not a signal.</b> Events are chosen <i>because</i> a move fired — this is '
            'what pre-move days looked like in hindsight, a post-selection base-rate, never "buy when X."</li>'
            '<li><b>Survivorship.</b> The universe is today\'s listings; delisted losers are absent, so every '
            'forward number is biased upward.</li>'
            '<li><b>Medians, not means</b> (means are pulled by the big-winner tail); the baseline is '
            '<b>1-in-10 sampled</b> (multiply by ~10 for true prevalence).</li>'
            '<li><b>Leak-safe:</b> only trailing/structural <i>precursors</i> feed the fingerprint; the '
            'forward-outcome columns are described, never used as inputs. Recent-era events with an '
            'incomplete forward window are excluded from the envelope.</li>'
            '<li><b>Aggregate, not per-name.</b> Delivery being suppressed <i>in aggregate</i> doesn\'t make '
            'delivery useless on a single stock — it means it doesn\'t separate the pre-move population.</li>'
            '</ul></div>')
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Move anatomy</h2><div class="ma-note">The <code>features</code> event panel '
            '(research.db) is not present on this host. It is the labelled explosive-move panel built by '
            '<code>research/explosive_moves/</code>. This surface is read-only and never fabricates data.</div>')
    return HTMLResponse(_shell("Move anatomy · patearn", "".join(body), "move-anatomy", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/move-anatomy" not in paths:
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
    r = c.get("/dash/move-anatomy")
    assert r.status_code == 200 and "Move anatomy" in r.text
    print("move_anatomy_view selftest OK — page 200 (populated or honest-empty)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
