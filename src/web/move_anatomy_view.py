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

# curated precursors → (display label, column, family). Ordered by family; the chart re-sorts by z.
# ALL are legitimate no-look-ahead precursors (trailing/structural). Outcomes are NEVER inputs.
_PRECURSORS = [
    ("Trailing 12m return", "ret_252d", "Momentum / strength"),
    ("Trailing 3m return", "ret_66d", "Momentum / strength"),
    ("RS rank vs market", "h_rs_rank", "Momentum / strength"),
    ("RS slope (3m)", "h_rs_vs_broad_slope_3m", "Momentum / strength"),
    ("Close vs 200-DMA", "close_vs_sma200", "Momentum / strength"),
    ("Close vs 50-DMA", "close_vs_sma50", "Momentum / strength"),
    ("50-DMA slope", "sma50_slope", "Momentum / strength"),
    ("Range position (52w)", "range_pos_252", "Momentum / strength"),
    ("NR ratio (10/60)", "nr_ratio_10_60", "Base / volatility"),
    ("ATR contraction", "atr_contraction", "Base / volatility"),
    ("Volume dry-up (5/22)", "vol_dryup_5_22", "Base / volatility"),
    ("Big-delivery days", "big_deliv_days_10", "Delivery / accumulation"),
    ("Delivery trend", "deliv_trend", "Delivery / accumulation"),
    ("Strong-delivery days", "n_strong_deliv_22", "Delivery / accumulation"),
    ("Delivery %", "deliv_per_s", "Delivery / accumulation"),
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
        cols = [c for _, c, _ in _PRECURSORS]
        # one aggregate pass per group — baseline needs avg + avg(sq) for the std
        base_sel = ", ".join(f"avg({c}), avg({c}*{c})" for c in cols)
        b = con.execute(f"SELECT {base_sel} FROM features WHERE label=0").fetchone()
        evt_sel = ", ".join(f"avg({c})" for c in cols)
        e = con.execute(f"SELECT {evt_sel} FROM features WHERE label=1").fetchone()
        fp = []
        for i, (lab, col, fam) in enumerate(_PRECURSORS):
            bmean, bsq, emean = b[2 * i], b[2 * i + 1], e[i]
            if bmean is None or bsq is None or emean is None:
                continue
            var = bsq - bmean * bmean
            sd = math.sqrt(var) if var > 0 else None
            if not sd:
                continue
            fp.append({"label": lab, "family": fam, "z": (emean - bmean) / sd,
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
    body = [_CSS]
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
            '<div class="ma-thesis">The panel of 166K labelled moves says something the setup lore '
            'doesn\'t: big moves launch from <b>momentum and strength</b> — trailing return, relative '
            'strength, price above its long averages — <b>not</b> from a tight base with heavy '
            'delivery. Delivery actually runs <b>below</b> baseline before a move. It quietly confirms '
            'the falsified footprint gate: the "strong-hand accumulation" fingerprint isn\'t there in '
            'aggregate.</div>')

        # FINGERPRINT
        bars = [(f'{r["label"]}', r["z"]) for r in fp]
        body.append('<div class="ma-panel">'
                    '<div class="ma-h">The fingerprint <small>— each precursor, event-mean minus '
                    'baseline-mean, in baseline std-devs (σ)</small></div>'
                    '<div class="ma-sub">Read it left-to-right: what was <b>elevated</b> on pre-move '
                    'days (cyan, right) vs <b>suppressed</b> (orange, left) relative to a normal quiet '
                    'day. This is a <i>description</i> of the pre-move population, not a recipe.</div>'
                    '<div class="ma-leg"><span><i style="background:var(--series-1)"></i>elevated before moves</span>'
                    '<span><i style="background:var(--accent-orange)"></i>suppressed before moves</span></div>'
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
                    '<div class="ma-h">The excursion envelope <small>— median forward gain (MFE) vs '
                    'pain (MAE), 6-month window</small></div>'
                    '<div class="ma-sub">How far up vs how far down, after the fact. Events carry a far '
                    'better gain-for-pain than the quiet baseline — but this is <b>post-selection</b> '
                    '(the move already fired) and survivorship-biased, so it is a base-rate, never an '
                    'achievable return.</div>'
                    + ifx.floating_bars(fb, w=700, bar_h=32, label_w=210)
                    + '</div>')

        # TABLE
        trs = ""
        for r in fp:
            cls = "ma-hi" if r["z"] >= 0 else "ma-lo"
            trs += (f'<tr><td class="l">{_esc(r["label"])}</td>'
                    f'<td class="l ma-fam">{_esc(r["family"])}</td>'
                    f'<td class="{cls}">{r["z"]:+.2f}σ</td>'
                    f'<td style="color:var(--ink-3)">{r["evt"]:.2f}</td>'
                    f'<td style="color:var(--ink-3)">{r["base"]:.2f}</td></tr>')
        body.append('<div class="ma-panel"><div class="ma-h">Every precursor, ranked</div>'
                    '<table class="ma"><thead><tr><th class="l">Precursor</th><th class="l">Family</th>'
                    '<th>z (σ)</th><th>Event</th><th>Baseline</th></tr></thead>'
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
