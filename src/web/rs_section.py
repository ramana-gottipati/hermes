"""RS Section — P0 of UI Architecture v2 (docs/ui-architecture-v2.md §0.1, §13).

The first-class **Relative Strength** hub that lives at the MARKETS altitude
(active="rs-hub"). RS is NOT a top-level tab and NOT a Strategies lens — its
macro face is Markets content (§0.1, corrected by the 2026-06-23 red-team).

Isolation (per §0.8): this is a brand-new module so it cannot collide with the
parallel session that owns dashboard.py/cockpit.py/the rotation views. It:
  - REUSES the existing lens routes (links to /dash/leaders, /dash/sectors,
    /dash/rrg, /dash/rsband, /dash/rotation) — it does NOT reimplement them.
  - reads ONLY precomputed signal tables for its previews (§0.7 perf guardrail);
    never the on-read recompute paths (current_all / band_lane / per-member RS).
  - is fully self-contained for chrome+style (only imports the stable _shell /
    _esc / _q from dashboard); every preview is wrapped defensively so a shifting
    upstream signature degrades to "open →" instead of crashing the hub.

The ONLY contended-file edit P0 needs is ONE line in src/main.py:
    from src.web.rs_section import router as rs_section_router
    app.include_router(rs_section_router)
That hook is DEFERRED until the parallel session frees the web layer (§0.8).
Until wired, this module is inert and harmless.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell, _esc, _q  # chrome + helpers (import-safe)
from src.web import infographics as ifx  # shared readability scaffold (S-C education)

router = APIRouter()

_BENCH = ("Nifty 500", "Nifty 50")

# RS lens registry (the §9 scaffolding, scoped to RS). Adding a future RS lens =
# one row here → it auto-appears as a hub card. key · label · existing route ·
# the question it answers · whether the route accepts a ?den= benchmark.
_LENSES = [
    ("leaders",  "Leaders",  "/dash/leaders",  "who is strong-in-strong",          False),
    ("sectors",  "Sectors",  "/dash/sectors",  "sector RS ranking",                False),
    ("momentum", "Momentum", "/dash/rrg",      "rotation — direction of travel",   True),
    ("divergence", "Divergence", "/dash/divergence", "momentum turning before price", False),
    ("level",    "Level",    "/dash/rsband",   "cheap vs rich in its own RS range", True),
    ("phase",    "Phase",    "/dash/rotation", "lifecycle state + fresh turns",     False),
]


def _fmt(v, d=1):
    try:
        return f"{float(v):.{d}f}"
    except (TypeError, ValueError):
        return "—"


def _href(base: str, takes_den: bool, den: str) -> str:
    return f"{base}?den={_q(den)}" if takes_den else base


# --- previews: PRECOMPUTED-table reads only (§0.7); each defensive ------------

def _pv_leaders() -> str:
    try:
        from src.automation.stock_rs import leaders_laggards
        lead = leaders_laggards("leaders", 4) or []
        lag = leaders_laggards("laggards", 2) or []

        def row(r, cls):
            rk = r.get("rs_rank")
            return (f'<div class="rsh-row"><span class="rsh-sym">{_esc(r.get("symbol", ""))}</span>'
                    f'<span class="rsh-sec">{_esc((r.get("primary_sector") or "")[:13])}</span>'
                    f'<span class="rsh-rk {cls}">{rk if rk is not None else "—"}</span></div>')
        out = "".join(row(r, "up") for r in lead)
        if lag:
            out += '<div class="rsh-sub">laggards</div>' + "".join(row(r, "dn") for r in lag)
        return out or '<div class="rsh-empty">no leaders today</div>'
    except Exception:
        return '<div class="rsh-empty">—</div>'


def _pv_momentum(den: str) -> str:
    try:
        from src.automation import rrg
        rows = rrg.latest_all(den) or []          # rs_extras, momentum-sorted DESC
        if not rows:
            return '<div class="rsh-empty">run rrg nightly</div>'

        def row(r):
            nm = r.get("numerator") or r.get("sector") or ""
            return (f'<div class="rsh-row"><span class="rsh-sym">{_esc(str(nm)[:16])}</span>'
                    f'<span class="rsh-mut">RS {_fmt(r.get("rs_ratio"))} · M {_fmt(r.get("rs_momentum"))}</span></div>')
        return "".join(row(r) for r in rows[:4])
    except Exception:
        return '<div class="rsh-empty">—</div>'


def _pv_level(den: str) -> str:
    try:
        from src.automation import rsband
        rows = rsband.latest_all(den) or []        # rsband_signals, band_pct ASC (cheap first)
        if not rows:
            return '<div class="rsh-empty">run rsband nightly</div>'

        def row(r):
            nm = r.get("numerator") or ""
            return (f'<div class="rsh-row"><span class="rsh-sym">{_esc(str(nm)[:16])}</span>'
                    f'<span class="rsh-mut">band {_fmt(r.get("rs_band_pct"), 0)}</span></div>')
        out = '<div class="rsh-sub">cheap · at RS support</div>' + "".join(row(r) for r in rows[:3])
        return out
    except Exception:
        return '<div class="rsh-empty">—</div>'


def _pv_phase() -> str:
    try:
        from src.automation.stock_rs import phase_movers
        movers = phase_movers(8) or []
        if not movers:
            return '<div class="rsh-empty">no turns today</div>'
        chips = "".join(
            f'<span class="rsh-chip">{_esc(r.get("symbol", ""))} '
            f'<span class="rsh-mut">{_esc((r.get("prev_phase") or "")[:3])}→{_esc((r.get("rs_phase") or "")[:3])}</span></span>'
            for r in movers[:8])
        return f'<div class="rsh-chips">{chips}</div>'
    except Exception:
        return '<div class="rsh-empty">—</div>'


def _pv_sectors() -> str:
    # The merged sector-ranking table lives on /dash/sectors; keep the hub light.
    return '<div class="rsh-empty">returns · RS strip · weather · momentum %ile — open the ranking</div>'


def _pv_divergence(den: str) -> str:
    try:
        from src.core.db import get_conn
        from src.web.divergence_board import _scan, _short
        with get_conn() as conn:
            bull, bear = _scan(conn)
        if not bull and not bear:
            return '<div class="rsh-empty">no divergences (run rrg nightly)</div>'

        def chips(items):
            return ('<div class="rsh-chips">'
                    + "".join(f'<span class="rsh-chip">{_esc(_short(x["name"]))}</span>'
                              for x in items[:4]) + '</div>')
        out = ""
        if bull:
            out += f'<div class="rsh-sub">▲ {len(bull)} bullish · early recovery</div>' + chips(bull)
        if bear:
            out += f'<div class="rsh-sub">▼ {len(bear)} bearish · early roll-over</div>' + chips(bear)
        return out
    except Exception:
        return '<div class="rsh-empty">—</div>'


_PREVIEW = {
    "leaders": lambda den: _pv_leaders(),
    "sectors": lambda den: _pv_sectors(),
    "momentum": lambda den: _pv_momentum(den),
    "divergence": lambda den: _pv_divergence(den),
    "level": lambda den: _pv_level(den),
    "phase": lambda den: _pv_phase(),
}

_CSS = """<style>
.rsh-wrap{max-width:1100px;}
.rsh-top{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:2px 0 12px;}
.rsh-top h2{margin:0;font-size:18px;}
.rsh-sub2{color:var(--ink-2);font-size:12px;}
.rsh-bench{margin-left:auto;display:inline-flex;border:1px solid var(--line-2);border-radius:7px;overflow:hidden;font-size:12px;}
.rsh-bench a{padding:5px 10px;color:var(--ink-2);text-decoration:none;}
.rsh-bench a.on{background:var(--bg-3);color:var(--ink);}
.rsh-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;}
.rsh-card{display:block;border:1px solid var(--line-2);border-radius:10px;padding:12px;background:var(--bg-2);color:inherit;text-decoration:none;border-top:3px solid #1f6feb;}
.rsh-card:hover{border-color:#388bfd;}
.rsh-h{display:flex;align-items:center;font-weight:600;font-size:14px;color:var(--ink);}
.rsh-go{margin-left:auto;font-size:11px;color:#58a6ff;font-weight:400;}
.rsh-q{color:var(--ink-2);font-size:11px;margin:2px 0 8px;}
.rsh-b{font-size:12px;font-variant-numeric:tabular-nums;}
.rsh-row{display:flex;align-items:center;gap:8px;padding:2px 0;}
.rsh-sym{font-weight:600;color:var(--ink);}
.rsh-sec{color:var(--ink-3);flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}
.rsh-mut{color:var(--ink-2);margin-left:auto;}
.rsh-rk{margin-left:auto;font-weight:600;}
.rsh-rk.up{color:var(--up);} .rsh-rk.dn{color:var(--down);}
.rsh-sub{color:var(--ink-3);font-size:10px;text-transform:uppercase;letter-spacing:.4px;margin:6px 0 2px;}
.rsh-empty{color:var(--ink-3);font-size:11px;line-height:1.5;}
.rsh-chips{display:flex;flex-wrap:wrap;gap:4px;}
.rsh-chip{background:var(--bg-1);border:1px solid var(--line-2);border-radius:9px;padding:2px 7px;font-size:11px;color:var(--ink);}
.rsh-foot{color:var(--ink-3);font-size:11px;margin-top:12px;}
</style>"""


def render_rs_hub(den: str = "Nifty 500") -> str:
    den = den if den in _BENCH else "Nifty 500"
    bench = ('<span class="rsh-bench">'
             + "".join(f'<a class="{"on" if b == den else ""}" href="/dash/rs-hub?den={_q(b)}">vs {_esc(b)}</a>'
                       for b in _BENCH)
             + '</span>')
    cards = []
    for key, label, base, question, takes_den in _LENSES:
        body = _PREVIEW[key](den)
        cards.append(
            f'<a class="rsh-card" href="{_href(base, takes_den, den)}">'
            f'<div class="rsh-h">{_esc(label)}<span class="rsh-go">open →</span></div>'
            f'<div class="rsh-q">{_esc(question)}</div>'
            f'<div class="rsh-b">{body}</div></a>')
    return (_CSS + '<div class="rsh-wrap">'
            '<div class="rsh-top"><h2>Relative strength</h2>'
            '<span class="rsh-sub2">rank · momentum · level · phase — one place, vs the benchmark</span>'
            '<a class="rsh-go" href="/dash/ratio" style="margin-left:10px" '
            'title="Single pair: an index vs a chosen denominator">RS ratio chart ↗</a>'
            f'{bench}</div>'
            f'<div class="rsh-grid">{"".join(cards)}</div>'
            '<div class="rsh-foot">A Markets-altitude hub (RS is macro content, not a stand-alone strategy). '
            'Previews read precomputed signal tables only; open any lens for the full, live view.</div>'
            '</div>')


@router.get("/dash/rs-hub", response_class=HTMLResponse)
def rs_hub(den: str = Query("Nifty 500")) -> HTMLResponse:
    body = (ifx.readability_css()
            + ifx.bottom_line(
                'Four ways to read one question — <b>is it beating the market?</b> Rank (who '
                'leads), momentum (is the lead growing), level (where it sits in its own range) '
                'and phase (which quarter of the cycle) — all versus the benchmark you pick. '
                '<b>A hub of context lenses</b>; open any card for the full view.')
            + ifx.how_to_read_link()
            + render_rs_hub(den))
    return HTMLResponse(_shell("Relative strength · patearn", body, active="rs-hub", wide=True))
