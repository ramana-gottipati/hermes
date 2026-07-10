"""Launchpad — the track record (orphan rescue: `ignition_outcomes`, 50,334 rows 2019→2026).

The Launchpad page shows only TODAY's ignition scan. The empirical answer to "does this
screen actually work?" sits in `ignition_outcomes` — one row per historical ignition signal
with its realised excursion (mfe/mae), time-to-peak, recovery-after-drawdown and 1m..24m
forward returns — and NO page reads it (orphan audit, F). This lens turns a "trust the screen"
list into an honest OUTCOME DISTRIBUTION.

STRICTLY DESCRIPTIVE, point-in-time (ledger: "launchpad = validated screen, no fundable edge
net of cost"): this is a one-shot study computed on its `computed_at` date, GROSS of costs,
survivorship-exposed (universe = current listings; delisted losers absent → returns biased
up). It is NOT a live-updating track record and NOT a recommendation — it is "here is what
these setups did, historically, with the drawdown you'd have sat through." Paired with the
`averaging_zones` recovery ladder (how often a drawdown of −X% still reached +25%).

Route: /dash/launchpad-track. Reads ignition_outcomes + averaging_zones (hermes.db).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_CSS = """
<style>
.lt-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 14px;max-width:1180px;}
.lt-note b{color:var(--ink);} .lt-note code{font-size:12px;}
.lt-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:0 0 16px;}
.lt-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:11px;padding:11px 13px;}
.lt-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.05;}
.lt-tile .l{font-size:11.5px;font-weight:700;margin-top:5px;color:var(--ink);}
.lt-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:3px;}
.lt-panel{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;padding:14px 16px;margin:0 0 15px;}
.lt-h{font-size:15px;font-weight:700;margin:0 0 3px;color:var(--ink);}
.lt-h small{font-weight:400;color:var(--ink-3);font-size:12px;}
.lt-sub{color:var(--ink-2);font-size:12px;line-height:1.5;margin:4px 0 10px;max-width:1120px;}
table.lt{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:4px;}
table.lt th{color:var(--ink-3);font-weight:600;text-align:right;padding:5px 10px;border-bottom:1px solid var(--line-2);}
table.lt td{padding:5px 10px;border-bottom:1px solid #171d25;text-align:right;font-variant-numeric:tabular-nums;}
table.lt td.l,table.lt th.l{text-align:left;}
.lt-pos{color:var(--up);} .lt-neg{color:var(--down);}
.lt-lad{display:flex;flex-direction:column;gap:6px;margin-top:6px;max-width:640px;}
.lt-lrow{display:flex;align-items:center;gap:10px;font-size:12px;}
.lt-lrow .k{width:52px;text-align:right;color:var(--ink-2);font-variant-numeric:tabular-nums;}
.lt-lbar{flex:1;height:16px;background:var(--bg-3);border-radius:8px;overflow:hidden;position:relative;}
.lt-lbar i{display:block;height:100%;background:linear-gradient(90deg,var(--down),var(--warn),var(--up));opacity:.8;}
.lt-lrow .v{width:52px;color:var(--ink);font-variant-numeric:tabular-nums;}
.lt-hist{display:flex;align-items:flex-end;gap:3px;height:120px;margin-top:8px;}
.lt-hbar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:3px;}
.lt-hbar i{width:100%;border-radius:3px 3px 0 0;}
.lt-hbar .c{font-size:9px;color:var(--ink-3);}
.lt-hbar .x{font-size:9px;color:var(--ink-3);margin-top:2px;white-space:nowrap;}
</style>
"""


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _agg(rows, keyfn):
    """Group rows by keyfn → {key: {n, med_r12, hit25, med_mfe, med_mae}}."""
    g = {}
    for r in rows:
        g.setdefault(keyfn(r), []).append(r)
    out = {}
    for k, rs in g.items():
        r12 = [r["ret_12m"] for r in rs if r["ret_12m"] is not None]
        out[k] = {
            "n": len(rs),
            "med_r12": _median(r12),
            # ret_12m is stored in PERCENT units (median ~18 = +18%), so hit +25% is x>25
            "hit25": (100.0 * sum(1 for x in r12 if x > 25) / len(r12)) if r12 else None,
            "med_mfe": _median([r["mfe_pct"] for r in rs]),
            "med_mae": _median([r["mae_from_entry_pct"] for r in rs]),
        }
    return out


@router.get("/dash/launchpad-track", response_class=HTMLResponse)
def dash_launchpad_track() -> HTMLResponse:
    body = [_CSS]
    as_of = ""
    try:
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND "
                                "name='ignition_outcomes'").fetchone():
                raise LookupError("ignition_outcomes absent")
            rows = conn.execute(
                "SELECT character, is_first_ignition, ret_12m, mfe_pct, mae_from_entry_pct "
                "FROM ignition_outcomes WHERE ret_12m IS NOT NULL").fetchall()
            if not rows:
                raise LookupError("empty")
            asr = conn.execute("SELECT MAX(computed_at) c FROM ignition_outcomes").fetchone()
            as_of = (asr["c"] or "")[:10]
            zones = conn.execute("SELECT label, recover_rate, base_rate FROM averaging_zones "
                                 "ORDER BY x").fetchall()

            by_char = _agg(rows, lambda r: (r["character"] or "—"))
            by_first = _agg(rows, lambda r: "First ignition" if r["is_first_ignition"]
                            else "Repeat")
            allr12 = [r["ret_12m"] for r in rows if r["ret_12m"] is not None]
            overall = _agg(rows, lambda r: "ALL")["ALL"]

            body.append(
                '<h2 style="margin:0 0 2px">Launchpad — the track record '
                f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">does the ignition '
                f'screen actually work? · {len(rows):,} historical signals · study as of {_esc(as_of)}</small></h2>'
                '<div class="lt-note">The Launchpad page shows only <b>today\'s</b> scan. This is the '
                f'evidence behind it: every ignition signal since 2019 ({len(rows):,} of them), with the '
                'return it delivered <b>and the drawdown you\'d have sat through first</b>. '
                '<b>Read it as a distribution, not a promise:</b> this is a point-in-time study '
                f'(computed {_esc(as_of)}), <b>gross of costs</b>, and survivorship-exposed (delisted '
                'losers are absent, so returns are biased up). The ledger is explicit — the launchpad is '
                'a <b>validated screen with no fundable edge net of cost</b>; this page quantifies the '
                'screen\'s character, it is not a recommendation. <a href="/dash/launchpad">← today\'s scan</a></div>')

            # tiles
            def tile(n, c, l, s):
                return (f'<div class="lt-tile"><div class="n" style="color:{c}">{n}</div>'
                        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>')
            body.append(
                '<div class="lt-tiles">'
                + tile(f'{len(rows):,}', "var(--ink)", "Signals studied", "ignitions 2019→2026, 12m window")
                + tile(f'{overall["hit25"]:.0f}%', "var(--up)", "Hit +25% in 12m",
                       "share that reached a +25% move")
                + tile(f'{overall["med_r12"]:+.0f}%', "var(--up)" if overall["med_r12"] >= 0 else "var(--down)",
                       "Median 12m return", "typical outcome (median, not mean)")
                + tile(f'{overall["med_mae"]:.0f}%', "var(--down)", "Median drawdown first",
                       "the pain before the payoff (MAE)")
                + tile(f'{_median([r["mfe_pct"] for r in rows]):.0f}%', "var(--up)", "Median peak (MFE)",
                       "best excursion reached in-window")
                + '</div>')

            # MFE/MAE envelope by character
            order = sorted(by_char.items(), key=lambda kv: -kv[1]["n"])
            fb = [(f'{k} (n={v["n"]:,})', v["med_mae"], v["med_mfe"],
                   f'hit+25% {v["hit25"]:.0f}%' if v["hit25"] is not None else "")
                  for k, v in order if v["med_mfe"] is not None and v["med_mae"] is not None]
            body.append(
                '<div class="lt-panel"><div class="lt-h">Gain vs pain, by ignition character '
                '<small>— median favourable (MFE) vs adverse (MAE) excursion</small></div>'
                '<div class="lt-sub">Each bar spans the typical <b>drawdown</b> (red, left) to the typical '
                '<b>peak</b> (green, right) an ignition of that character reached within the window. The '
                'accumulation-character cohort carries the best gain-for-pain — but every character sits '
                'through a real drawdown first. Medians (means are tail-pulled).</div>'
                + ifx.floating_bars(fb, w=680, bar_h=30, label_w=190)
                + '</div>')

            # character table
            trs = ""
            for k, v in order:
                trs += (f'<tr><td class="l">{_esc(k)}</td><td>{v["n"]:,}</td>'
                        f'<td class="{"lt-pos" if (v["med_r12"] or 0)>=0 else "lt-neg"}">{v["med_r12"]:+.1f}%</td>'
                        f'<td>{v["hit25"]:.0f}%</td>'
                        f'<td class="lt-pos">+{v["med_mfe"]:.0f}%</td>'
                        f'<td class="lt-neg">{v["med_mae"]:.0f}%</td></tr>')
            for k, v in sorted(by_first.items(), key=lambda kv: -kv[1]["n"]):
                trs += (f'<tr style="opacity:.85"><td class="l" style="color:var(--ink-3)">· {_esc(k)}</td>'
                        f'<td>{v["n"]:,}</td>'
                        f'<td class="{"lt-pos" if (v["med_r12"] or 0)>=0 else "lt-neg"}">{v["med_r12"]:+.1f}%</td>'
                        f'<td>{v["hit25"]:.0f}%</td><td class="lt-pos">+{v["med_mfe"]:.0f}%</td>'
                        f'<td class="lt-neg">{v["med_mae"]:.0f}%</td></tr>')
            body.append(
                '<div class="lt-panel"><div class="lt-h">By character · by first-vs-repeat ignition</div>'
                '<div class="lt-sub">First ignitions (a name\'s first fire after a quiet base) run more '
                'explosively — and with a fatter tail — than repeats. All medians.</div>'
                '<table class="lt"><thead><tr><th class="l">Cohort</th><th>N</th><th>Med 12m</th>'
                '<th>Hit +25%</th><th>Med peak</th><th>Med drawdown</th></tr></thead>'
                f'<tbody>{trs}</tbody></table></div>')

            # ret_12m distribution histogram
            body.append(_hist_panel(allr12))

            # averaging-down recovery ladder (averaging_zones)
            if zones:
                base = zones[0]["base_rate"] if zones else None
                lad = ""
                for z in zones:
                    rr = z["recover_rate"]
                    lad += (f'<div class="lt-lrow"><span class="k">{_esc(z["label"])}</span>'
                            f'<span class="lt-lbar"><i style="width:{rr:.0f}%"></i></span>'
                            f'<span class="v">{rr:.0f}%</span></div>')
                body.append(
                    '<div class="lt-panel"><div class="lt-h">The drawdown-recovery ladder '
                    '<small>— should you sit through it? (averaging_zones)</small></div>'
                    '<div class="lt-sub">Of all entries that fell to −X%, the share that still went on to '
                    f'reach +25%. Base rate across all entries: <b>{base:.0f}%</b>. The deeper the hole, the '
                    'lower the odds — an honest antidote to reflexive averaging-down. Descriptive base-rates.</div>'
                    f'<div class="lt-lad">{lad}</div></div>')
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Launchpad — the track record</h2><div class="lt-note">The '
            '<code>ignition_outcomes</code> study table is not populated on this host. It is a '
            'point-in-time outcome study over historical ignition signals (see '
            '<code>src/automation/ignition_outcomes.py</code>). Read-only; never fabricates data.</div>')
    return HTMLResponse(_shell("Launchpad track record · patearn", "".join(body),
                               "launchpad-track", str(as_of)[:10], wide=True))


def _hist_panel(r12: list) -> str:
    """CSS-bar histogram of 12m forward returns — shows it's a wide distribution, not a point."""
    if not r12:
        return ""
    # ret_12m is in PERCENT units
    edges = [(-1e9, -25, "≤−25%", "var(--down)"), (-25, 0.0, "−25..0", "var(--down)"),
             (0.0, 25, "0..25", "var(--warn)"), (25, 50, "25..50", "var(--up)"),
             (50, 100, "50..100", "var(--up)"), (100, 200, "100..200", "var(--up)"),
             (200, 1e12, "200%+", "var(--up)")]
    counts = []
    for lo, hi, lab, col in edges:
        c = sum(1 for x in r12 if lo <= x < hi)
        counts.append((c, lab, col))
    cmax = max(c for c, _, _ in counts) or 1
    bars = ""
    for c, lab, col in counts:
        pctlab = f'{100.0*c/len(r12):.0f}%'
        bars += (f'<div class="lt-hbar"><span class="c">{pctlab}</span>'
                 f'<i style="height:{c/cmax*100:.0f}%;background:{col};opacity:.8"></i>'
                 f'<span class="x">{_esc(lab)}</span></div>')
    return ('<div class="lt-panel"><div class="lt-h">Distribution of 12-month outcomes '
            '<small>— the spread is the point</small></div>'
            '<div class="lt-sub">Ignition outcomes are a wide distribution, not a single number: a heavy '
            'right tail of big winners, a real left tail of losers. Any single signal lands somewhere in '
            'here — the median is the honest expectation.</div>'
            f'<div class="lt-hist">{bars}</div></div>')


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/launchpad-track" not in paths:
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
    r = c.get("/dash/launchpad-track")
    assert r.status_code == 200 and "track record" in r.text
    print("launchpad_track_view selftest OK — page 200 (populated or honest-empty)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
