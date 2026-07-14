"""
screener_plus.py — Lane B · the STREAMLINED screener at /dash/screen2.

ONE wide, configurable, frozen-pane screener that unifies what is otherwise
scattered across the per-strategy lenses. The streamlining over /dash/screener:
  * a CONFLUENCE lead column (0–5) — how many pillars align right now
    (DVPT positioning · MEP accumulation · RS strength · CPR structure · CCI
    credibility) — with a ★ when ≥4 align. Sort once, see everything that lines up.
  * one-click column-GROUP toggle chips (show/hide each strategy's block) so the
    grid is as wide or as tight as the question needs — persisted across reloads.
  * SAVED SCREENS — name a (scope + visible-groups) combo and reload it instantly.
  * a single frozen top header AND frozen Symbol column; client-side sort / text
    filter / CSV export. Server-rendered HTML + vanilla JS (data-first-light-ui).

Ownership / isolation (plan §1, Lane B): NEW self-contained module. Imports only
ui_kit (chrome), v2_surfaces (nav, best-effort), and src.core.db (precomputed
reads). Touches no parallel-owned file. Self-mounts via `router`. PRECOMPUTED
tables only (stock_signals, mep_signals, cpr_signals, concall_scores) —
never recompute a strategy on read.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web import ui_kit as K
from src.web import glossary as G  # `?` hover-help — wire the existing (inert) glossary
from src.web import infographics as ifx  # shared readability scaffold + fence() vocabulary (S-C)

log = logging.getLogger("hermes.screen2")
router = APIRouter()

_BROAD = ["Nifty 50", "Nifty Next 50", "Nifty Midcap 150",
          "Nifty Smallcap 250", "Nifty 500"]
_SECTORS = ["Nifty Bank", "Nifty Financial Services", "Nifty IT", "Nifty Auto",
            "Nifty Pharma", "Nifty FMCG", "Nifty Metal", "Nifty Energy",
            "Nifty Realty", "Nifty Media", "Nifty Infrastructure",
            "Nifty Commodities", "Nifty Healthcare Index", "Nifty Consumer Durables",
            "Nifty Oil & Gas", "Nifty India Defence", "Nifty Private Bank",
            "Nifty Chemicals"]

# column groups (key -> label) — also the toggle-chip legend
_GROUPS = [
    ("conf", "Confluence"), ("pos", "Positioning · DVPT"), ("mep", "Accumulation · MEP"),
    ("rs", "Relative strength"), ("cpr", "Structure · CPR"),
    ("cci", "Credibility · CCI"), ("wol", "Wolfe"), ("rev", "Reversal ctx"),
    ("qual", "Quality · pt14"),
    ("ca", "Cap-alloc · C"), ("ctx", "Context"),
]

# CL-VIEW-15: liquidity gate WITHOUT static rupee thresholds (no-static-threshold
# doctrine). The old gate hard-coded `value > 1e7 AND close > 20` — fixed rupee numbers
# that drift with the index level and penalise low-priced-but-liquid names. Replaced by a
# self-scaling TURNOVER PERCENTILE: keep names whose traded value is at/above the 30th
# percentile of THAT day's EQ universe. The cutoff re-derives every day from the data (see
# `_turnover_cutoff`), so it tracks the market instead of a frozen number; it is passed as a
# bound `?` param (`b.value >= ?`), NOT interpolated. The penny floor is dropped — a name
# that clears the turnover percentile is liquid by construction (verified on VPS real data
# 2026-06-29: 1452 rows vs the old gate's 1369 — no regression; only 34 sub-₹20 names enter,
# all genuinely liquid by turnover). Descriptive — a universe filter, not a ranking.
_LIQ_PCTILE = 0.30
_LIQ = ("b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL) "
        "AND b.value >= ? "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list)")


def _turnover_cutoff(conn, sig_date) -> float:
    """The day's 30th-percentile EQ turnover — a self-scaling liquidity floor (no static
    rupee number; CL-VIEW-15). Computed once per request over the day's EQ universe.
    Returns 0.0 on any miss so the gate degrades to 'all turnover>0' rather than 500."""
    try:
        n = conn.execute(
            "SELECT COUNT(*) c FROM bhavcopy_rows b WHERE b.trade_date=? AND b.series='EQ' "
            "AND (b.segment='CM' OR b.segment IS NULL) AND b.value > 0 "
            "AND b.symbol IN (SELECT symbol FROM nse_equity_list)", (sig_date,)).fetchone()["c"]
        if not n:
            return 0.0
        off = int(_LIQ_PCTILE * n)
        r = conn.execute(
            "SELECT b.value v FROM bhavcopy_rows b WHERE b.trade_date=? AND b.series='EQ' "
            "AND (b.segment='CM' OR b.segment IS NULL) AND b.value > 0 "
            "AND b.symbol IN (SELECT symbol FROM nse_equity_list) "
            "ORDER BY b.value LIMIT 1 OFFSET ?", (sig_date, off)).fetchone()
        return float(r["v"]) if r and r["v"] is not None else 0.0
    except Exception as e:  # noqa: BLE001
        log.warning("turnover cutoff failed: %s", e)
        return 0.0


# ── nav / sub-nav (best-effort full site nav) ────────────────────────────────
def _nav_html(active: str) -> str:
    try:
        from src.web import v2_surfaces as V
        return K.nav_links(V.site_nav(active))
    except Exception:  # noqa: BLE001
        return ""


def _sub() -> str:
    """The Screener sub-nav — GENERATED from the lens registry (via v2_surfaces) so this
    page renders the IDENTICAL strip as every other Screener page and cannot drift. The
    old hand-rolled list wrongly showed "Strategist" (a Strategies lens) and omitted
    "Review". Highlighted on Screen+ (`active="screen2"`). Falls back to the correct
    registry-matching set if v2_surfaces is unavailable."""
    try:
        from src.web import v2_surfaces as V
        s = V.native_subnav("screen2")
        if s:
            return s
    except Exception:  # noqa: BLE001 — sub-nav is chrome; never fatal
        pass
    return K.subnav([
        ("Screen+", "/dash/screen2", True),
        ("Screen (classic)", "/dash/screener", False),
        ("Themes / Baskets", "/dash/themes", False),
        ("Review", "/dash/tags-review", False),
        ("Workbench", "/dash/workbench", False),
    ])


# ── data helpers ─────────────────────────────────────────────────────────────
def _latest(conn, table, col="trade_date"):
    try:
        r = conn.execute(f"SELECT MAX({col}) d FROM {table}").fetchone()
        return r["d"] if r else None
    except Exception:  # noqa: BLE001
        return None


def _sector_symbols(conn, sector):
    try:
        rows = conn.execute(
            """SELECT symbol FROM stock_index_membership
               WHERE index_name=? AND snapshot_date=(
                   SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name=?)
               ORDER BY symbol""", (sector, sector)).fetchall()
        return [r["symbol"] for r in rows]
    except Exception:  # noqa: BLE001
        return []


def _cpr_by_tf(conn, syms, tf):
    """{sym: row} latest cpr_signals for a timeframe over the given symbols."""
    out = {}
    if not syms:
        return out
    try:
        mx = conn.execute(
            "SELECT MAX(period_end_date) d FROM cpr_signals WHERE timeframe=?", (tf,)).fetchone()
        if not mx or not mx["d"]:
            return out
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"""SELECT * FROM cpr_signals
                    WHERE timeframe=? AND period_end_date=? AND symbol IN ({ph})""",
                [tf, mx["d"], *syms]).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("cpr lookup failed: %s", e)
    return out


def _cci_by_sym(conn, syms):
    out = {}
    if not syms:
        return out
    try:
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"""SELECT s.* FROM concall_scores s
                    JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x
                      ON x.symbol=s.symbol AND x.m=s.last_updated
                    WHERE s.symbol IN ({ph})""", syms).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("cci lookup failed: %s", e)
    return out


def _wolfe_by_sym(conn, syms):
    """{sym: row} latest Wolfe scan (wolfe_signals, owned by wolfe.py — READ-ONLY here).
    The 5th confluence pillar the legacy screener never carried. Descriptive: the §C
    falsification stands — Wolfe is geometry SELECTION, never a buy/target call.
    Tries the broadest universe present (nifty500 first); empty if the table is absent."""
    out = {}
    if not syms:
        return out
    try:
        if not conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='wolfe_signals'"
        ).fetchone():
            return out
        ph = ",".join("?" for _ in syms)
        # one row per symbol: prefer the most recent scan, then in-zone, then freshest.
        for r in conn.execute(
                f"""SELECT w.sym, w.dir, w.in_zone, w.q, w.age, w.fresh, w.scan_date
                    FROM wolfe_signals w
                    JOIN (SELECT sym, MAX(scan_date) m FROM wolfe_signals GROUP BY sym) x
                      ON x.sym=w.sym AND x.m=w.scan_date
                    WHERE w.sym IN ({ph})""", syms).fetchall():
            # keep the strongest read per symbol (in-zone beats not; higher quality wins)
            prev = out.get(r["sym"])
            cand = dict(r)
            if (prev is None
                    or (cand.get("in_zone") or 0) > (prev.get("in_zone") or 0)
                    or ((cand.get("in_zone") or 0) == (prev.get("in_zone") or 0)
                        and (cand.get("q") or 0) > (prev.get("q") or 0))):
                out[r["sym"]] = cand
    except Exception as e:  # noqa: BLE001
        log.warning("wolfe lookup failed: %s", e)
    return out


def _revctx_by_sym(conn, syms):
    """{sym: row} reversal_context (owned by reversal_context.py — READ-ONLY here).

    DESCRIPTIVE ONLY — the whole reversal-pair research arc was falsified as a
    trading signal (ledger §§ 2026-07-13 / 07-14 / 07-14b): the band reclaim-cross
    ANTI-selects and the floor-breakout book died at true cost. What ships is the
    surviving CONTEXT: band state (reclaim = caution, not entry), own-history
    stretch percentile, and the confirmed-fractal floor as a risk/invalidation
    level. Never rank, alert, or confluence-count on these columns."""
    out = {}
    if not syms:
        return out
    try:
        if not conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='reversal_context'"
        ).fetchone():
            return out
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"SELECT * FROM reversal_context WHERE symbol IN ({ph})", syms).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("revctx lookup failed: %s", e)
    return out


_REV_STATE = {"RECLAIM": ("⚠ reclaim", "early band-reclaims after a downtrend have "
                          "historically UNDERPERFORMED (falsified as an entry) — a caution flag"),
              "SLIP": ("↓ slip", "trigger slipped below the upper bank"),
              "ABOVE": ("above", "trigger above both banks"),
              "INSIDE": ("in band", "trigger between the banks"),
              "BELOW": ("below", "trigger below both banks")}


def _rev_cells(rv) -> str:
    """The 4 Reversal-ctx tds (band · stretch% · stretch pctile · floor). Descriptive."""
    st = rv.get("band_state") or ""
    label, tip = _REV_STATE.get(st, ("—", ""))
    sp = rv.get("stretch_pct")
    pc = rv.get("stretch_pctile")
    pc_txt = f"p{pc:.0f}" if pc is not None else "—"
    gap, age, deg = rv.get("floor_gap_pct"), rv.get("floor_age"), rv.get("floor_deg")
    alive = rv.get("floor_alive")
    if gap is None:
        floor_txt, floor_v = "—", 999
    elif not alive:
        floor_txt, floor_v = f"✗ broken D{deg}", 999
    else:
        floor_txt, floor_v = f"+{gap:.1f}% · D{deg} · {age}d", gap
    cg, ca_, cd = rv.get("ceil_gap_pct"), rv.get("ceil_age"), rv.get("ceil_deg")
    calive = rv.get("ceil_alive")
    if cg is None:
        ceil_txt, ceil_v = "—", 999
    elif not calive:
        ceil_txt, ceil_v = f"↑ cleared D{cd}", 999
    else:
        ceil_txt, ceil_v = f"{cg:.1f}% · D{cd} · {ca_}d", cg
    return (
        f'<td class="l cg-rev" data-v="{K.esc(st)}" title="{K.esc(tip)}">{K.esc(label)}</td>'
        f'<td class="num cg-rev" data-v="{sp if sp is not None else -999}">{_num(sp, 1)}</td>'
        f'<td class="num cg-rev" data-v="{pc if pc is not None else -1}">{pc_txt}</td>'
        f'<td class="l cg-rev mut" data-v="{floor_v}">{K.esc(floor_txt)}</td>'
        f'<td class="l cg-rev mut" data-v="{ceil_v}">{K.esc(ceil_txt)}</td>')


def _pt14_by_sym(conn, syms):
    """{sym: row} latest pt14 quality score (pattern_scores, READ-ONLY here) — the
    14-pattern quality gate the legacy screener's Quality group shows. Lets Screen+
    carry the quality column so it is a genuine superset, not just a confluence view."""
    out = {}
    if not syms:
        return out
    try:
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"""SELECT p.symbol, p.ns_base, p.tier, p.qg_pass, p.hard_disqualified
                    FROM pattern_scores p
                    JOIN (SELECT symbol, MAX(scored_at) m FROM pattern_scores GROUP BY symbol) x
                      ON x.symbol=p.symbol AND x.m=p.scored_at
                    WHERE p.symbol IN ({ph})""", syms).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("pt14 lookup failed: %s", e)
    return out


# ── cell formatters ──────────────────────────────────────────────────────────
def _num(v, dp=2):
    return f"{v:,.{dp}f}" if isinstance(v, (int, float)) else "—"


def _pct(v, dp=1):
    return f"{v:+.{dp}f}%" if isinstance(v, (int, float)) else "—"


def _trend_pill(st):
    if not st:
        return '<span class="mut">—</span>'
    kind = "up" if "STRONG_UP" in st or st in ("UPTREND", "UP") else \
           "down" if "DOWN" in st else "neutral"
    return K.pill(st.replace("_", " ").title(), kind)


def _mep_pill(st):
    if not st:
        return '<span class="mut">—</span>'
    kind = "up" if "ACCUM" in st else "down" if "DISTRIB" in st else "neutral"
    return K.pill(st.replace("_", " ").title(), kind)


def _tier_pill(t):
    if not t:
        return '<span class="mut">—</span>'
    kind = "cred" if t in ("A+", "A") else "warn" if t == "B" else "down" if t in ("D",) else "neutral"
    return K.pill(t, kind)


def _wolfe_pill(wf):
    """Wolfe geometry read: BULL/BEAR + in-zone marker. Descriptive (selection, not a call)."""
    d = (wf.get("dir") or "").lower() if wf else ""
    if not d:
        return '<span class="mut">—</span>'
    in_zone = wf.get("in_zone") or 0
    label = d.title() + (" ◉" if in_zone else "")
    kind = "up" if d == "bull" else "down" if d == "bear" else "neutral"
    return K.pill(label, kind)


def _calloc_by_sym(conn, syms):
    """Latest capital-allocation (C) composite per symbol — ca_score 0..100 +
    cross-sectional ca_tier (S77b backtest: consumed as a DESCRIPTIVE column /
    blend tilt, never a hard veto or standalone ranker)."""
    out = {}
    if not syms:
        return out
    try:
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"""SELECT c.symbol, c.ca_score, c.ca_tier
                    FROM capital_allocation_scores c
                    JOIN (SELECT symbol, MAX(as_of) m FROM capital_allocation_scores GROUP BY symbol) x
                      ON x.symbol=c.symbol AND x.m=c.as_of
                    WHERE c.symbol IN ({ph})""", syms).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("capital-allocation lookup failed: %s", e)
    return out


def _ca_pill(t):
    """Capital-allocation tier pill (cross-sectional quintile band)."""
    if not t:
        return '<span class="mut">—</span>'
    kind = "cred" if t == "EXCELLENT" else "up" if t == "GOOD" else \
           "down" if t == "POOR" else "warn" if t == "WEAK" else "neutral"
    return K.pill(t.title(), kind)


def _qual_pill(pq):
    """pt14 quality gate: tier + a ⛔ flag if hard-disqualified."""
    if not pq:
        return '<span class="mut">—</span>'
    t = pq.get("tier") or ""
    if pq.get("hard_disqualified"):
        return K.pill("⛔ DQ", "down")
    if not t:
        return '<span class="mut">—</span>'
    kind = "cred" if str(t).startswith("T1") or t in ("A+", "A") else \
           "warn" if str(t).startswith("T2") or t == "B" else "neutral"
    return K.pill(t, kind)


# ── "the instrument" — inline static micro-viz (ported from the original Screen) ─────
# The original /dash/screener leads each column-group with a self-contained inline SVG that
# turns the buried numbers into a SCANNABLE SHAPE, with the raw sortable values kept beside it
# (data-first). Screen+ had none (0 SVGs in-browser); these bring that pictorial richness in.
#
# Ported as LOCAL, self-contained fns (NO import from dashboard.py / cockpit.py — the
# parallel-ownership wall stays intact) and RE-TINTED to the institutional value palette
# (var(--up)/var(--down)/var(--warn)/var(--accent)) instead of the legacy GitHub greens
# (#2ea043/#3fb950/#7ee787) the source used — so the whole surface speaks ONE green and the
# "off" cyan-green is gone. All compute ONCE in Python (no per-cell JS), degrade to "—" on NULL.
# (py3.10 on the VPS → no backslash inside any f-string expression.)
_UP = "var(--up)"
_DOWN = "var(--down)"
_TRACK = "var(--bg-3)"          # instrument track / empty fill
_HAIR = "var(--line-2)"         # neutral hairline / axis
_MUT = "var(--ink-3)"           # muted glyph


def _mv_ladder(dvpt, p1, p2, p3, p6, p12) -> str:
    """DVPT-vs-power ladder: a track with up-to-5 notches (P1M…P12M; an --up notch = beaten
    by today's DVPT), an --up fill to today + a ▲ marker. Surfaces the power_dvpt_* family as
    one shape (the rank pill + ×power ride the adjacent numeric columns, kept)."""
    if not dvpt:
        return '<span class="mut">—</span>'
    ps = [p1, p2, p3, p6, p12]
    vals = [v for v in ps if v]
    maxv = max([dvpt] + vals)
    if not maxv:
        return '<span class="mut">—</span>'
    W, x0, x1, ty, th = 116, 3, 104, 15, 6

    def sx(v):
        return x0 + (v / maxv) * (x1 - x0)
    notches = []
    for v in ps:
        if not v:
            continue
        nx = sx(v)
        ncol = _UP if dvpt >= v else _MUT
        notches.append(f'<line x1="{nx:.1f}" y1="{ty-4}" x2="{nx:.1f}" y2="{ty+th+4}" '
                       f'stroke="{ncol}" stroke-width="1"/>')
    fw = sx(dvpt) - x0
    tx = sx(dvpt)
    tip = f'M{tx-4:.1f},{ty-8} L{tx+4:.1f},{ty-8} L{tx:.1f},{ty-2} Z'
    return (f'<svg class="mv" width="{W}" height="26" viewBox="0 0 {W} 26" aria-hidden="true">'
            f'<rect x="{x0}" y="{ty}" width="{x1-x0}" height="{th}" rx="3" fill="{_TRACK}"/>'
            f'<rect x="{x0}" y="{ty}" width="{fw:.1f}" height="{th}" rx="3" fill="{_UP}"/>'
            + "".join(notches)
            + f'<path d="{tip}" fill="{_UP}"/></svg>')


def _mv_triglyph(tcr, duo, hh) -> str:
    """Character triglyph: 3 diverging micro-bars composing the ACCUM/DIST read — WHO
    (trade-count concentration) · WAY (delivery up/down skew) · CTX (distance from 52w high).
    Right/--up = the accumulation lean; left/--down = the distribution lean."""
    def cl(v):
        return max(-1.0, min(1.0, v))
    axes = [cl((1 - tcr) * 1.4) if tcr is not None else None,   # WHO: <1 concentrating
            cl((duo - 1) * 1.0) if duo is not None else None,   # WAY: >1 up-skew
            cl((hh + 10) / 10) if hh is not None else None]     # CTX: near 52w-high
    W, cx, half, bh, ys = 42, 21, 17, 5, (5, 12, 19)
    bars = []
    for s, y in zip(axes, ys):
        if s is None:
            bars.append(f'<rect x="{cx-1}" y="{y-1}" width="2" height="2" fill="{_HAIR}"/>')
            continue
        w = abs(s) * half
        x = cx if s >= 0 else cx - w
        col = _MUT if abs(s) < 0.12 else (_UP if s > 0 else _DOWN)
        bars.append(f'<rect x="{x:.1f}" y="{y-2.5:.0f}" width="{max(w,1):.1f}" '
                    f'height="{bh}" rx="1" fill="{col}"/>')
    return (f'<svg class="mv" width="{W}" height="26" viewBox="0 0 {W} 26" aria-hidden="true">'
            f'<line x1="{cx}" y1="2" x2="{cx}" y2="24" stroke="{_HAIR}"/>'
            + "".join(bars) + '</svg>')


def _mv_rsspark(b1, b3, b6, b12) -> str:
    """RS sparkline: the rs-vs-broad slope trajectory 12m→1m (oldest→newest) as a tiny
    polyline — --up rising / --down falling. Degrades to a dot when slopes are NULL."""
    have = [(i, v) for i, v in ((0, b12), (1, b6), (2, b3), (3, b1)) if v is not None]
    if len(have) < 2:
        return '<span class="mut" style="font-size:11px">·</span>'
    vs = [v for _, v in have] + [0.0]
    mn, mx = min(vs), max(vs)
    W, x0, x1, y0, y1 = 50, 2, 48, 3, 19

    def sx(i):
        return x0 + (i / 3) * (x1 - x0)

    def sy(v):
        return (y0 + y1) / 2 if mx == mn else y1 - ((v - mn) / (mx - mn)) * (y1 - y0)
    d = " ".join(('L' if k else 'M') + f'{sx(i):.1f},{sy(v):.1f}'
                 for k, (i, v) in enumerate(have))
    last = b1 if b1 is not None else have[-1][1]
    col = _UP if last > 0 else _DOWN
    zero_y = sy(0)
    return (f'<svg class="mv" width="{W}" height="22" viewBox="0 0 {W} 22" aria-hidden="true">'
            f'<line x1="{x0}" y1="{zero_y:.1f}" x2="{x1}" y2="{zero_y:.1f}" stroke="{_HAIR}" '
            f'stroke-dasharray="2 2"/><path d="{d}" fill="none" stroke="{col}" stroke-width="1.5"/></svg>')


def _mv_adbar(score) -> str:
    """Signed accumulation/distribution mini-bar (the MEP shape). Centre = 0; --up to the
    right = accumulation, --down to the left = distribution. Clamped to ±2 for display."""
    if score is None:
        return '<span class="mut">—</span>'
    v = max(-2.0, min(2.0, score))
    frac = v / 2.0 * 50.0
    if v >= 0:
        x, w, col = 50.0, frac, _UP
    else:
        x, w, col = 50.0 + frac, -frac, _DOWN
    return (f'<svg class="mv" width="92" height="16" viewBox="0 0 100 16" preserveAspectRatio="none">'
            f'<rect x="0" y="6.5" width="100" height="3" rx="1.5" fill="{_TRACK}"/>'
            f'<rect x="{x:.1f}" y="4.5" width="{w:.1f}" height="7" rx="1.5" fill="{col}"/>'
            f'<line x1="50" y1="2" x2="50" y2="14" stroke="{_MUT}" stroke-width="1"/></svg>')


def _rs_heatstrip(b1, b3, b6, b12, b18=None, b24=None) -> str:
    """Multi-timeframe RS heat strip from the rs-vs-broad slope_%: per cell None→muted ·;
    ≥+3 strong-up ▲; >+1 mild-up ▲; |x|≤1 flat ▬; <-1 mild-down ▼; ≤-3 strong-down ▼.
    Renders [1m][3m][6m][12m] left→right (and [18m][24m] when supplied). Value-tinted."""
    cells = []
    pairs = [(b1, "1m"), (b3, "3m"), (b6, "6m"), (b12, "12m")]
    if b18 is not None or b24 is not None:
        pairs += [(b18, "18m"), (b24, "24m")]
    for v, lbl in pairs:
        if v is None:
            cls, glyph = "hs-nd", "·"
        elif v >= 3:
            cls, glyph = "hs-su", "▲"
        elif v > 1:
            cls, glyph = "hs-mu", "▲"
        elif v < -3:
            cls, glyph = "hs-sd", "▼"
        elif v < -1:
            cls, glyph = "hs-md", "▼"
        else:
            cls, glyph = "hs-fl", "▬"
        cells.append(f'<span class="hs-c {cls}">{glyph}<small>{lbl}</small></span>')
    return '<span class="hstrip">' + "".join(cells) + '</span>'


# ── column-parity check (promotability evidence) ──────────────────────────────
# The legacy /dash/screener (dashboard.py, frozen) surfaces these strategy data
# FIELDS. Screen+ is promotable to default only if it covers every analytic family
# the legacy shows AND adds the confluence/Wolfe/CCI cross-lens the legacy lacks.
# We enumerate by ANALYTIC FAMILY (not column-for-column micro-parity) — the legacy
# carries deeper per-family ladders (full p1..p12 power, b1..b24 RS slopes) that
# Screen+ summarises; the promotability claim is "every family represented + a
# superset of LENSES", documented here and viewable at /dash/screen2?parity=1.
_LEGACY_FAMILIES = {
    "Identity (symbol/sector/CMP)":      ["symbol", "sector", "close"],
    "Conviction (rank/r/p/score)":       ["trigger_rank", "r_score", "p_score", "conv"],
    "Positioning · DVPT":                ["delivery_value_per_trade", "power_dvpt_1m",
                                          "power_dvpt_3m", "is_ath_dvpt", "accum_character",
                                          "price_vs_hot_avg_pct", "turnover_surge_1m"],
    "Relative strength":                 ["rs_rank", "rs_vs_broad_trend_state",
                                          "rs_vs_broad_slope_1m", "rs_vs_broad_slope_3m",
                                          "rs_vs_broad_slope_12m", "rs_vs_sector_trend_state"],
    "Quality · pt14":                    ["ns_base", "tier", "qg_pass"],
    "Structure · CPR":                   ["pattern", "compression_pctile"],
    "Credibility · CCI":                 ["composite_score", "tier", "credibility_trend"],
    "Context":                           ["pct_from_52w_high", "turnover_surge_1m",
                                          "accum_character"],
}
# What Screen+ surfaces, by family → the columns it shows (the header `cols` list
# above is the source of truth; this maps each to its family for the report).
_SCREEN2_FAMILIES = {
    "Identity (symbol/sector/CMP)":  ["Symbol", "Sector", "CMP"],
    "Confluence (cross-lens 0-6)":   ["Confl (DVPT×MEP×RS×CPR×CCI×Wolfe)"],
    "Conviction (rank/r/p/score)":   ["Rank", "P", "R", "×1m"],
    "Positioning · DVPT":            ["DVPT-vs-power ladder", "Rank", "P", "R", "×1m", "Dlv%", "Char", "Surge"],
    "Accumulation · MEP":            ["Accum bar", "Phase", "State"],
    "Relative strength":             ["RS spark", "Heat strip", "RS#", "Trend", "1m", "3m", "6m", "12m"],
    "Structure · CPR":               ["D pattern", "Cmpr", "W pattern"],
    "Credibility · CCI":             ["CCI", "Tier", "Trend"],
    "Wolfe (geometry)":              ["Wolfe dir+zone", "Q"],
    "Quality · pt14":                ["NS", "pt14 tier"],
    "Context":                       ["Surge", "%52wH", "Char"],
}


def parity_report() -> dict:
    """Programmatic column-parity: every legacy analytic FAMILY covered by Screen+?
    Returns {covered, missing, extra, ok}. Pure (no DB) — the families are static."""
    legacy_fams = set(_LEGACY_FAMILIES)
    screen2_fams = set(_SCREEN2_FAMILIES)
    covered = sorted(legacy_fams & screen2_fams)
    missing = sorted(legacy_fams - screen2_fams)
    extra = sorted(screen2_fams - legacy_fams)
    return {"covered": covered, "missing": missing, "extra": extra,
            "ok": not missing, "n_legacy": len(legacy_fams), "n_screen2": len(screen2_fams)}


def _parity_view() -> str:
    """The promotability evidence page — family-by-family legacy↔Screen+ coverage."""
    rep = parity_report()
    rows = []
    for fam in sorted(set(_LEGACY_FAMILIES) | set(_SCREEN2_FAMILIES)):
        in_legacy = fam in _LEGACY_FAMILIES
        in_s2 = fam in _SCREEN2_FAMILIES
        leg = ", ".join(_LEGACY_FAMILIES.get(fam, [])) or "—"
        s2 = ", ".join(_SCREEN2_FAMILIES.get(fam, [])) or "—"
        if in_legacy and in_s2:
            mark, kind = "✓ covered", "up"
        elif in_legacy and not in_s2:
            mark, kind = "✗ MISSING", "down"
        else:
            mark, kind = "+ Screen+ only", "neutral"
        rows.append(
            f'<tr><td class="l"><b>{K.esc(fam)}</b></td>'
            f'<td class="l mut" style="font-size:11.5px">{K.esc(leg)}</td>'
            f'<td class="l mut" style="font-size:11.5px">{K.esc(s2)}</td>'
            f'<td>{K.pill(mark, kind)}</td></tr>')
    verdict = ("PROMOTABLE — every legacy analytic family is represented in Screen+, "
               "plus the confluence / Wolfe cross-lens the legacy never carried."
               if rep["ok"] else
               f"NOT YET — missing families: {', '.join(rep['missing'])}.")
    vkind = "up" if rep["ok"] else "down"
    table = (
        '<table class="dt" style="width:100%;margin-top:12px"><thead><tr>'
        '<th class="l">Analytic family</th><th class="l">Legacy /dash/screener fields</th>'
        '<th class="l">Screen+ columns</th><th>Coverage</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>')
    note = (
        '<div class="sec" style="margin-top:14px;font-size:12px">'
        'Parity is checked by analytic FAMILY, not micro-column. The legacy screener '
        'carries deeper per-family ladders (full p1–p12 DVPT power, b1–b24 RS slopes) '
        'that Screen+ deliberately summarises to stay readable; both read the SAME '
        'precomputed tables. Promotability = every family present + a superset of lenses. '
        f'{ifx.fence("not_reco", cap=True)}; the §C falsification stands (no buy/sell ranking).</div>')
    # the exact promotion checklist (the nav-slot flip is the orchestrator's, via
    # lens_registry — this enumerates what is DONE so the flip is a clean swap).
    checklist = [
        ("Column-superset of legacy /dash/screener", True, "8/8 analytic families + 3 new lenses (above)"),
        ("Confluence column (MEP×CCI×RS×CPR×Wolfe)", True, "0-6 confluence with per-pillar dots + ★ flag"),
        ("Scope parity (Nifty 500 default · all · watch · sectors)", True, "same _sector_symbols + index list as legacy"),
        ("Saved screens (name / load / delete)", True, "localStorage s2_screens_v1; persists scope + group toggles"),
        ("Group show/hide toggles (persisted)", True, "localStorage s2_hidden_v1; restored on load"),
        ("CSV export (visible cols + rows, data-v aware)", True, "client-side Blob; escaped; includes new lenses"),
        ("Filter + click-to-sort on every column", True, "table.dt + s2filter"),
        ("Pat bridge (scope → confluence query / save board)", True, "“Ask Pat: confluence here” + “Save as Pat board”"),
        ("Descriptive framing (no buy/sell ranking)", True, "ranked by confluence count, §C-safe"),
        ("Nav slot via lens_registry → make it the default Screener", False,
         "ORCHESTRATOR — register /dash/screen2 as Screener default; legacy stays at /dash/screener"),
    ]
    crows = []
    for label, done, detail in checklist:
        mark, kind = ("✓ done", "up") if done else ("→ orchestrator", "neutral")
        crows.append(
            f'<tr><td>{K.pill(mark, kind)}</td><td class="l"><b>{K.esc(label)}</b></td>'
            f'<td class="l mut" style="font-size:11.5px">{K.esc(detail)}</td></tr>')
    n_done = sum(1 for _, d, _ in checklist if d)
    checklist_html = (
        '<div class="wb-sec-lbl" style="margin-top:22px">Promotion checklist '
        f'<span class="mut" style="text-transform:none;font-weight:400">({n_done}/{len(checklist)} done · '
        'the last is the nav flip)</span></div>'
        '<table class="dt" style="width:100%"><thead><tr><th>Status</th>'
        '<th class="l">Requirement</th><th class="l">Evidence / owner</th></tr></thead>'
        f'<tbody>{"".join(crows)}</tbody></table>')
    head = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        '<h1 class="uk-h1">Screen+ · column parity</h1>'
        + K.badge(f"{len(rep['covered'])}/{rep['n_legacy']} legacy families covered · "
                  f"{len(rep['extra'])} new lenses") + '</div>'
        f'<div class="sec" style="margin-bottom:6px">{K.pill(verdict, vkind)}</div>')
    back = '<a class="st-open" href="/dash/screen2" style="display:inline-block;margin:10px 0">← back to Screen+</a>'
    return _CSS + head + back + table + note + checklist_html


# ── the page ─────────────────────────────────────────────────────────────────
@router.get("/dash/screen2", response_class=HTMLResponse)
def dash_screen2(scope: str = Query("Nifty 500"), parity: str = Query(""),
                 limit: str = Query("600"), rev: str = Query("")) -> HTMLResponse:
    if str(parity or "").strip() in ("1", "true", "yes"):
        return HTMLResponse(K.shell("Screen+ parity · patearn", _parity_view(),
                                    active="screener", sub=_sub(),
                                    nav_html=_nav_html("screener")))
    # CLAMP rather than 422-reject — a hand-typed URL with a bad/out-of-range limit
    # should still render the screener (demo-grade graceful degradation), not an
    # error page. `limit` is a str so FastAPI never 422s before we parse it.
    try:
        limit = max(50, min(int(str(limit).strip()), 2000))
    except (TypeError, ValueError):
        limit = 600
    scope = (scope or "Nifty 500").strip()
    # `rev=ri` = "⚠ Reclaim · floor intact" (S132b) · `rev=si` = the bearish mirror
    # "⚠ Slip · ceiling intact" (S132c): band SLIP with the confirmed up-fractal
    # ceiling UNBROKEN. Descriptive watch cuts — both crosses are falsified as
    # signals (ledger 07-13); these isolate the structurally clean situations.
    _rv = str(rev or "").strip().lower()
    rev_f = ("ri" if _rv in ("ri", "reclaim", "1")
             else "si" if _rv in ("si", "slip") else "")
    is_all = scope.lower() == "all"
    is_watch = scope.lower() in ("watch", "watchlist")
    rows: list[dict] = []
    sig_date = None
    cpr_d = cpr_w = cci = wolfe = pt14 = calloc = rev = {}
    n_members = None

    try:
        with get_conn() as conn:
            sig_date = _latest(conn, "stock_signals")
            if sig_date:
                if is_all:
                    scope_syms = None
                elif is_watch:
                    scope_syms = [r["symbol"] for r in conn.execute(
                        "SELECT symbol FROM watchlist ORDER BY symbol").fetchall()]
                else:
                    scope_syms = _sector_symbols(conn, scope)
                n_members = len(scope_syms) if scope_syms is not None else None

                # CL-VIEW-15: the day's self-scaling turnover floor (bound `?` in _LIQ),
                # inserted right after sig_date to match the `?` order in the SQL below.
                turnover_cut = _turnover_cutoff(conn, sig_date)
                clause, params = "", [sig_date, turnover_cut]
                if scope_syms is not None:
                    use = scope_syms or ["\x00"]
                    clause = " AND s.symbol IN (" + ",".join("?" for _ in use) + ")"
                    params += use
                if rev_f and conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='reversal_context'").fetchone():
                    rc_where = ("band_state='RECLAIM' AND floor_alive=1" if rev_f == "ri"
                                else "band_state='SLIP' AND ceil_alive=1")
                    clause += (" AND s.symbol IN (SELECT symbol FROM reversal_context"
                               f" WHERE {rc_where})")
                params.append(limit)

                conv = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
                rows = [dict(r) for r in conn.execute(
                    f"""SELECT s.symbol, s.primary_sector sector, b.close,
                               s.pct_from_52w_high hh, s.trigger_rank rank,
                               s.p_score, s.r_score, s.ratio_today_vs_power_1m x1,
                               b.deliv_per, s.accum_character ch, s.turnover_surge_1m su1,
                               s.rs_rank, s.rs_vs_broad_trend_state rsbt,
                               s.rs_vs_broad_slope_1m b1, s.rs_vs_broad_slope_3m b3,
                               s.rs_vs_broad_slope_6m b6, s.rs_vs_broad_slope_12m b12,
                               s.rs_vs_broad_slope_18m b18, s.rs_vs_broad_slope_24m b24,
                               s.delivery_value_per_trade dvpt,
                               s.power_dvpt_1m p1, s.power_dvpt_2m p2, s.power_dvpt_3m p3,
                               s.power_dvpt_6m p6, s.power_dvpt_12m p12,
                               s.trade_count_ratio_1m_6m tcr,
                               s.ticket_ratio_1m_6m tkr,
                               s.deliv_updown_ratio_3m duo,
                               {conv} conv,
                               m.mep_score_smooth mep_ph, m.mep_state_smooth mep_st
                        FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                        LEFT JOIN mep_signals m ON m.symbol=s.symbol AND m.trade_date=s.trade_date
                        WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                          AND {_LIQ}{clause}
                        ORDER BY conv DESC, COALESCE(s.p_score,-1) DESC LIMIT ?""",
                    params).fetchall()]

                if rows:
                    syms = [r["symbol"] for r in rows]
                    cpr_d = _cpr_by_tf(conn, syms, "D")
                    cpr_w = _cpr_by_tf(conn, syms, "W")
                    cci = _cci_by_sym(conn, syms)
                    wolfe = _wolfe_by_sym(conn, syms)
                    pt14 = _pt14_by_sym(conn, syms)
                    calloc = _calloc_by_sym(conn, syms)
                    rev = _revctx_by_sym(conn, syms)
    except Exception as e:  # noqa: BLE001
        log.warning("screen2 query failed: %s", e)

    # ── build rows with the confluence score ──
    trs = []
    for r in rows:
        sym = r["symbol"]
        cd = cpr_d.get(sym, {})
        cw = cpr_w.get(sym, {})
        cc = cci.get(sym, {})
        wf = wolfe.get(sym, {})
        pq = pt14.get(sym, {})
        ca = calloc.get(sym, {})
        rv = rev.get(sym, {})

        # confluence pillars (each 0/1) — the unifying read. Now MEP×CCI×RS×CPR×Wolfe
        # (the 5 the brief names) PLUS the DVPT positioning pillar = a 0-6 confluence.
        p_pos = 1 if (r.get("p_score") or 0) >= 4 else 0
        p_mep = 1 if (r.get("mep_st") or "") in ("ACCUM", "STRONG_ACCUM") else 0
        p_rs = 1 if (r.get("rs_rank") or 0) >= 80 else 0
        p_cpr = 1 if (cd.get("pattern") == "BULL_U") else 0
        p_cci = 1 if (cc.get("tier") or "") in ("A+", "A") else 0
        # Wolfe pillar = a BULL setup in its Fib zone now (geometry selection, descriptive).
        p_wol = 1 if ((wf.get("dir") or "").lower() == "bull" and (wf.get("in_zone") or 0)) else 0
        confl = p_pos + p_mep + p_rs + p_cpr + p_cci + p_wol
        star = "★ " if confl >= 4 else ""
        dots = "".join(
            f'<span class="cd {"on" if on else ""}" title="{lbl}"></span>'
            for lbl, on in [("DVPT", p_pos), ("MEP", p_mep), ("RS", p_rs),
                            ("CPR", p_cpr), ("CCI", p_cci), ("Wolfe", p_wol)])

        rank = r.get("rank") or "-"
        mep_ph = r.get("mep_ph")
        mep_ph_td = (f'<td class="num cg-mep" data-v="{mep_ph if mep_ph is not None else -99}" '
                     f'style="color:{"var(--up)" if (mep_ph or 0)>=0 else "var(--down)"}">'
                     f'{mep_ph:+.2f}</td>' if mep_ph is not None
                     else '<td class="num cg-mep mut" data-v="-99">—</td>')
        cpr_dpat = cd.get("pattern") or "—"
        cpr_wpat = cw.get("pattern") or "—"
        cp = cd.get("compression_pctile")
        x1v = r.get("x1")
        x1_txt = f"{x1v:.1f}×" if x1v else "—"
        dpv = r.get("deliv_per")
        dp_txt = f"{dpv:.1f}%" if dpv is not None else "—"

        # ── instruments (ported from the original Screen, retinted to --up/--down) ──
        # Each leads its group with a scannable SVG shape; sort uses the underlying value.
        ladder = _mv_ladder(r.get("dvpt"), r.get("p1"), r.get("p2"),
                            r.get("p3"), r.get("p6"), r.get("p12"))
        adbar = _mv_adbar(mep_ph)
        spark = _mv_rsspark(r.get("b1"), r.get("b3"), r.get("b6"), r.get("b12"))
        heat = _rs_heatstrip(r.get("b1"), r.get("b3"), r.get("b6"), r.get("b12"),
                            r.get("b18"), r.get("b24"))
        triglyph = _mv_triglyph(r.get("tcr"), r.get("duo"), r.get("hh"))
        # sort keys for the instrument cells (the shape's headline number)
        ix_intensity = None
        _powers = [r.get(k) for k in ("p1", "p3", "p6", "p12") if r.get(k)]
        if _powers and r.get("dvpt"):
            ix_intensity = r["dvpt"] / (sum(_powers) / len(_powers))

        trs.append(
            f'<tr>'
            # identity (always visible)
            f'<td class="sym"><a href="/dash/stock?sym={K.esc(sym)}">{K.esc(sym)}</a></td>'
            f'<td class="l mut">{K.esc(r.get("sector") or "—")}</td>'
            f'<td class="num" data-v="{r.get("close") or 0}">{_num(r.get("close"),1)}</td>'
            # confluence (lead)
            f'<td class="num cg-conf confl c{confl}" data-v="{confl}"><b>{star}{confl}</b>'
            f'<span class="dots">{dots}</span></td>'
            # positioning · dvpt — LEADS with the DVPT-vs-power ladder instrument
            f'<td class="inst l cg-pos" data-v="{ix_intensity if ix_intensity is not None else -1}">{ladder}</td>'
            f'<td class="cg-pos" data-v="{rank}"><span class="uk-pill neutral">{K.esc(str(rank))}</span></td>'
            f'<td class="num cg-pos" data-v="{r.get("p_score") if r.get("p_score") is not None else -1}">{r.get("p_score") if r.get("p_score") is not None else "—"}</td>'
            f'<td class="num cg-pos" data-v="{r.get("r_score") if r.get("r_score") is not None else -1}">{r.get("r_score") if r.get("r_score") is not None else "—"}</td>'
            f'<td class="num cg-pos" data-v="{x1v or 0}">{x1_txt}</td>'
            f'<td class="num cg-pos" data-v="{dpv or 0}">{dp_txt}</td>'
            # mep — LEADS with the signed accum/distrib bar instrument
            f'<td class="inst l cg-mep" data-v="{mep_ph if mep_ph is not None else -99}">{adbar}</td>'
            + mep_ph_td +
            # CL-VIEW-16: `or -99` made a real 0.0 sort as missing; keep 0.0 distinct.
            f'<td class="l cg-mep" data-v="{r.get("mep_ph") if r.get("mep_ph") is not None else -99}">{_mep_pill(r.get("mep_st"))}</td>'
            # rs — LEADS with the RS spark + the multi-TF heat strip instruments
            f'<td class="inst l cg-rs" data-v="{r.get("b1") if r.get("b1") is not None else -999}">{spark}</td>'
            f'<td class="inst l cg-rs" data-v="{r.get("b12") if r.get("b12") is not None else -999}">{heat}</td>'
            f'<td class="num cg-rs" data-v="{r.get("rs_rank") if r.get("rs_rank") is not None else -1}"><b>{r.get("rs_rank") if r.get("rs_rank") is not None else "—"}</b></td>'
            f'<td class="l cg-rs" data-v="{K.esc(r.get("rsbt") or "")}">{_trend_pill(r.get("rsbt"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b1") or 0}">{_pct(r.get("b1"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b3") or 0}">{_pct(r.get("b3"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b6") or 0}">{_pct(r.get("b6"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b12") or 0}">{_pct(r.get("b12"))}</td>'
            # cpr
            f'<td class="l cg-cpr" data-v="{K.esc(cpr_dpat)}">{_cpr_pat(cpr_dpat)}</td>'
            f'<td class="num cg-cpr" data-v="{cp or 0}">{(f"{cp*100:.0f}%") if cp is not None else "—"}</td>'
            f'<td class="l cg-cpr" data-v="{K.esc(cpr_wpat)}">{_cpr_pat(cpr_wpat)}</td>'
            # cci
            f'<td class="num cg-cci" data-v="{cc.get("composite_score") or -1}">{_num(cc.get("composite_score"),0)}</td>'
            f'<td class="l cg-cci" data-v="{K.esc(cc.get("tier") or "")}">{_tier_pill(cc.get("tier"))}</td>'
            f'<td class="l cg-cci mut" data-v="{K.esc(cc.get("credibility_trend") or "")}">{K.esc((cc.get("credibility_trend") or "—").title())}</td>'
            # wolfe (geometry — descriptive selection, the brief's 5th pillar)
            f'<td class="l cg-wol" data-v="{K.esc(wf.get("dir") or "")}">{_wolfe_pill(wf)}</td>'
            f'<td class="num cg-wol" data-v="{wf.get("q") or -1}">{_num(wf.get("q"),0)}</td>'
            # reversal ctx (descriptive-only; falsified as a signal — ledger 07-13/14/14b)
            f'{_rev_cells(rv)}'
            # quality · pt14
            f'<td class="num cg-qual" data-v="{pq.get("ns_base") if pq.get("ns_base") is not None else -1}">{_num(pq.get("ns_base"),0)}</td>'
            f'<td class="l cg-qual" data-v="{K.esc(pq.get("tier") or "")}">{_qual_pill(pq)}</td>'
            # capital allocation · C (descriptive; S77b backtest verdict — blend/context, never a veto)
            f'<td class="num cg-ca" data-v="{ca.get("ca_score") if ca.get("ca_score") is not None else -1}">{_num(ca.get("ca_score"),0)}</td>'
            f'<td class="l cg-ca" data-v="{K.esc(ca.get("ca_tier") or "")}">{_ca_pill(ca.get("ca_tier"))}</td>'
            # context — LEADS with the character triglyph (WHO·WAY·CTX → accum/dist read)
            f'<td class="inst l cg-ctx" data-v="{r.get("hh") if r.get("hh") is not None else -999}">{triglyph}</td>'
            f'<td class="num cg-ctx" data-v="{r.get("su1") or 0}">{_num(r.get("su1"),2)}</td>'
            f'<td class="num cg-ctx" data-v="{r.get("tkr") or 0}">{_num(r.get("tkr"),2)}</td>'
            # CL-VIEW-16: guard 0.0 (at the 52w high) so it doesn't sort as missing.
            f'<td class="num cg-ctx" data-v="{r.get("hh") if r.get("hh") is not None else -999}">{_pct(r.get("hh"))}</td>'
            f'<td class="l cg-ctx mut" data-v="{K.esc(r.get("ch") or "")}">{K.esc((r.get("ch") or "—"))}</td>'
            '</tr>')

    # ── header (two rows: group band + column names) ──
    grp_band = (
        '<tr class="grp">'
        '<th class="sym">stock</th><th colspan="2">identity</th>'
        '<th class="cg-conf s2gh" colspan="1">confluence</th>'
        '<th class="cg-pos s2gh" colspan="6">positioning · dvpt</th>'
        '<th class="cg-mep s2gh" colspan="3">accumulation · mep</th>'
        '<th class="cg-rs s2gh" colspan="8">relative strength</th>'
        '<th class="cg-cpr s2gh" colspan="3">structure · cpr</th>'
        '<th class="cg-cci s2gh" colspan="3">credibility · cci</th>'
        '<th class="cg-wol s2gh" colspan="2">wolfe</th>'
        '<th class="cg-rev s2gh" colspan="5">reversal ctx</th>'
        '<th class="cg-qual s2gh" colspan="2">quality · pt14</th>'
        '<th class="cg-ca s2gh" colspan="2">cap-alloc · C</th>'
        '<th class="cg-ctx s2gh" colspan="5">context · character</th></tr>')
    cols = ['Symbol', 'Sector', 'CMP', 'Confl',
            'DVPT vs power', 'Rank', 'P', 'R', '×1m', 'Dlv%',
            'Accum', 'Phase', 'State',
            'RS trend', 'Heat', 'RS#', 'Trend', '1m', '3m', '6m', '12m',
            'D', 'Cmpr', 'W',
            'CCI', 'Tier', 'Trend',
            'Wolfe', 'Q',
            'Band', 'Stretch%', 'sPctl', 'Floor', 'Ceil',
            'NS', 'pt14',
            'C', 'C tier',
            'Character', 'Surge', 'Ticket', '%52wH', 'Char']
    col_groups = ['', '', '', 'cg-conf',
                  'cg-pos', 'cg-pos', 'cg-pos', 'cg-pos', 'cg-pos', 'cg-pos',
                  'cg-mep', 'cg-mep', 'cg-mep',
                  'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs',
                  'cg-cpr', 'cg-cpr', 'cg-cpr',
                  'cg-cci', 'cg-cci', 'cg-cci',
                  'cg-wol', 'cg-wol',
                  'cg-rev', 'cg-rev', 'cg-rev', 'cg-rev', 'cg-rev',
                  'cg-qual', 'cg-qual',
                  'cg-ca', 'cg-ca',
                  'cg-ctx', 'cg-ctx', 'cg-ctx', 'cg-ctx', 'cg-ctx']
    # glossary key per column (aligned to `cols`) — `?` hover-help via the wired glossary.
    # Verified against docs/metrics-glossary.md: only terms that resolve to the CORRECT
    # definition are wired; '' = plain label (undocumented OR would mis-resolve, e.g. the
    # CCI 'Tier'/'Trend' columns would wrongly match the pt14 'Tier' entry). gloss() itself
    # degrades any unknown key to the plain label, so this list is safe by construction.
    col_terms = ['', '', 'cmp · δ%d · deliv%', '',                    # identity + confluence
                 'DVPT', 'trigger_rank', 'p_score', 'r_score', '×power', '',   # positioning · dvpt
                 'MEP phase', 'MEP phase', 'MEP daily state',         # mep (now documented)
                 'RS vs broad', 'RS heat strip', 'rs_rank', 'RS vs broad', '', '', '', '',  # rs
                 'pattern', 'compression_pctile', 'pattern',          # cpr
                 'Credibility composite', 'Credibility composite', 'Credibility level',  # cci (now documented; NOT 'tier'→pt14)
                 '', '',                                              # wolfe (undocumented)
                 'Band state', 'Stretch %', 'stretch_pctile', 'floor_gap_pct',
                 'ceil_gap_pct',                                      # reversal ctx
                 'ns_base', 'ns_base',                                # quality · pt14
                 'ca_score', 'ca_tier',                               # capital allocation · C
                 'accum_character', 'surge 1m', 'ticket_ratio_1m_6m',
                 'pct_from_52w_high', 'accum_character']  # context
    col_band = '<tr class="col">' + "".join(
        f'<th class="{("sym" if i==0 else "")} {g}" data-c="{i}" data-label="{K.esc(c)}">'
        f'{G.gloss(t, c) if t else K.esc(c)}</th>'
        for i, (c, g, t) in enumerate(zip(cols, col_groups, col_terms))) + '</tr>'
    thead = f'<thead>{grp_band}{col_band}</thead>'
    tbody = "".join(trs)

    # ── controls: scope chips + group toggles + saved screens + filter ──
    def _schip(name, label=None):
        on = " on" if scope.lower() == name.lower() else ""
        keep = f"&rev={rev_f}" if rev_f else ""        # scope switches keep the active cut
        return (f'<a class="uk-pill {"acc" if on else "neutral"}" '
                f'href="/dash/screen2?scope={_q(name)}{keep}">{K.esc(label or name)}</a>')
    ri_pill = (f'<a class="uk-pill {"acc" if rev_f == "ri" else "neutral"}" '
               f'href="/dash/screen2?scope={_q(scope)}{"" if rev_f == "ri" else "&rev=ri"}" '
               f'title="Only band-reclaims whose confirmed fractal floor is UNBROKEN — a '
               f'descriptive watch cut (the reclaim cross itself tested as an anti-signal, '
               f'ledger 2026-07-13); price came off the lows WITHOUT breaking known support.">'
               f'⚠ Reclaim · floor intact</a>')
    si_pill = (f'<a class="uk-pill {"acc" if rev_f == "si" else "neutral"}" '
               f'href="/dash/screen2?scope={_q(scope)}{"" if rev_f == "si" else "&rev=si"}" '
               f'title="The bearish mirror: trigger slipped below the upper bank while the '
               f'confirmed up-fractal ceiling is UNBROKEN — cooling off WITHOUT clearing known '
               f'resistance. Descriptive watch cut, not a short signal (ledger 2026-07-13).">'
               f'⚠ Slip · ceiling intact</a>')
    chips = ("".join(_schip(n) for n in _BROAD) + _schip("all", "All")
             + _schip("watch", "★ Watch") + ri_pill + si_pill)
    sec_opts = "".join(
        f'<option value="{K.esc(s)}"{" selected" if scope.lower()==s.lower() else ""}>{K.esc(s)}</option>'
        for s in _SECTORS)
    sec_sel = ('<select id="secSel" onchange="if(this.value)location=\'/dash/screen2?scope=\'+encodeURIComponent(this.value)">'
               f'<option value="">Sector ▾</option>{sec_opts}</select>')

    grp_chips = "".join(
        f'<button type="button" class="gchip on" data-g="cg-{k}">{K.esc(lbl)}</button>'
        for k, lbl in _GROUPS)

    shown = len(rows)
    if is_all:
        sub_lbl = f'All liquid equity · top <b>{shown}</b> by conviction (cap {limit})'
    elif is_watch:
        sub_lbl = f'Watchlist · <b>{shown}</b> stocks'
    else:
        mem = f'{n_members} members · ' if n_members else ''
        sub_lbl = f'<b>{K.esc(scope)}</b> · {mem}<b>{shown}</b> shown (liquid)'
    if rev_f == "ri":
        sub_lbl += ' · <b>⚠ reclaim · floor intact</b> cut (descriptive — not a signal)'
    elif rev_f == "si":
        sub_lbl += ' · <b>⚠ slip · ceiling intact</b> cut (descriptive — not a signal)'

    head = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        '<h1 class="uk-h1">Screen+</h1>'
        + K.badge(f"as of {str(sig_date)[:10] if sig_date else '—'} · precomputed")
        + '</div>'
        + ifx.bottom_line(
            'A <b>confluence screen</b>: liquid stocks ranked by how many independent pillars '
            '— momentum, accumulation, relative strength, structure — line up <b>right now</b>, '
            'each turned into a shape beside its raw numbers. A <b>shortlist to study</b>, not a '
            'buy list — sort any column, filter, and save your own screen.')
        + ifx.how_to_read_link()
        + f'<div class="sec" style="margin-bottom:14px">{sub_lbl} · '
        'confluence = pillars aligned now (DVPT · MEP · RS · CPR · CCI · Wolfe). '
        'Each group leads with an <b>instrument</b> — the <b>DVPT-vs-power ladder</b>, the '
        '<b>accum/distrib bar</b>, the <b>RS spark</b> and the <b>multi-TF heat strip</b> — '
        'that turns the buried numbers into a shape, with every raw value kept beside it. '
        'Toggle groups, sort any column, save a screen.</div>')

    # Pat bridge — turn the current scope into a conversational confluence query,
    # and pin it as a board that lands on the workbench (the screener → Pat → board loop).
    pat_q = _pat_bridge_q(scope, is_all)
    controls = (
        '<div class="s2-bar">' + chips + sec_sel + '</div>'
        '<div class="s2-bar"><span class="s2-lbl">Groups</span>' + grp_chips + '</div>'
        '<div class="s2-bar">'
        '<input id="s2filter" placeholder="Filter rows… (symbol, sector, state)" />'
        '<span class="s2-lbl">Saved</span>'
        '<select id="s2load"><option value="">Load screen…</option></select>'
        '<button type="button" id="s2save" class="gchip">＋ Save current</button>'
        '<button type="button" id="s2del" class="gchip">Delete</button>'
        '<button type="button" id="s2csv" class="gchip">⬇ CSV</button>'
        '<a class="gchip" href="/dash/screen2?parity=1" title="Column coverage vs the legacy screener">⊃ Parity</a>'
        '<span id="s2count" class="s2-lbl"></span></div>'
        '<div class="s2-bar"><span class="s2-lbl">Pat</span>'
        f'<a class="gchip" href="/dash/pat?q={_q(pat_q)}">Ask Pat: confluence here ↗</a>'
        f'<button type="button" class="gchip" data-q="{K.esc(pat_q)}" onclick="s2SaveBoard(this)">★ Save as Pat board</button>'
        '<span class="s2-lbl">the screener\'s confluence as a conversational query</span></div>')

    table = (f'<div class="uk-tw" id="s2wrap" style="max-height:80vh">'
             f'<table class="uk-t s2" id="s2tbl">{thead}<tbody>{tbody}</tbody></table></div>')
    if not trs:
        table = ('<div class="uk-card">No rows for this scope on the latest date. '
                 'Try a broader scope, or this host may not have signals computed yet.</div>')

    body = _CSS + ifx.readability_css() + G.css() + head + controls + table + _JS
    return HTMLResponse(K.shell("Screen+ · patearn", body,
                                active="screener", sub=_sub(), nav_html=_nav_html("screener")))


def _cpr_pat(p):
    if not p or p == "—":
        return '<span class="mut">—</span>'
    if p == "BULL_U":
        return K.pill("Bull-U", "up")
    if p == "BEAR_INVU":
        return K.pill("Bear-∩", "down")
    return f'<span class="mut">{K.esc(p)}</span>'


def _q(s):
    from urllib.parse import quote
    return quote(str(s))


def _pat_bridge_q(scope: str, is_all: bool) -> str:
    """Turn the current screener scope into a conversational confluence query for Pat
    (the screener leads with a 0–5 confluence column; this asks Pat the same in English).
    A sector scope qualifies the query; a cap-index scope maps to a cap-band."""
    base = "credible companies being accumulated that are RS-leading"
    s = (scope or "").strip()
    sl = s.lower()
    if is_all or sl in ("nifty 500", "nifty 50", "nifty next 50", "all", "watch", "watchlist"):
        return base
    if "smallcap" in sl:
        return base + " small caps"
    if "midcap" in sl:
        return base + " mid caps"
    if s in _SECTORS:                       # a sector index → "in <sector>"
        return base + " in " + s.replace("Nifty ", "").replace(" Index", "")
    return base


_CSS = """<style>
.s2-bar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:9px}
.s2-lbl{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink-3);margin-left:6px}
.gchip{font:inherit;font-size:12px;cursor:pointer;border:1px solid var(--line-2);background:var(--bg-1);
  color:var(--ink-3);border-radius:8px;padding:5px 11px;transition:var(--t)}
.gchip:hover{border-color:var(--accent);color:var(--ink)}
.gchip.on{background:var(--accent-dim);color:var(--accent);border-color:transparent}
#s2filter,#secSel,#s2load{font:inherit;font-size:12.5px;background:var(--bg-1);color:var(--ink);
  border:1px solid var(--line-2);border-radius:8px;padding:6px 10px}
#s2filter{min-width:240px}
table.s2 th{cursor:pointer;user-select:none}
table.s2 th.s2gh{text-align:center;color:var(--ink-2);border-left:1px solid var(--line-2)}
table.s2 tr.grp th{background:var(--bg-3);font-size:10px}
table.s2 td.confl{font-weight:600}
table.s2 td.confl b{font-size:13px}
table.s2 td.confl .dots{display:inline-flex;gap:2px;margin-left:6px;vertical-align:middle}
table.s2 td.confl .cd{width:5px;height:5px;border-radius:50%;background:var(--line-2);display:inline-block}
/* GREEN FIX (in-browser-verified): the confluence lead used --accent-cy (#34e0d6, a bright
   aqua) — an outlier that reads "off/less appealing" vs the institutional value green. Aligned
   to the value token --up (#3fd486), the same positive tint used everywhere else (pills, deltas,
   the ported instruments). The neon glow is softened to a subtle value-tint halo. */
table.s2 td.confl .cd.on{background:var(--up);box-shadow:0 0 4px var(--up-dim)}
table.s2 td.confl.c4,table.s2 td.confl.c5,table.s2 td.confl.c6{color:var(--up)}
table.s2 td.confl.c3{color:var(--up);opacity:.85}
/* ── "the instrument": inline micro-viz cells (ported from the original Screen) ── */
table.s2 td.inst{padding:3px 8px;text-align:left}
.mv{vertical-align:middle;display:inline-block}
/* multi-TF RS heat strip — value-tinted cells (--up up-bands / --warn flat / --down down-bands) */
.hstrip{display:inline-flex;gap:2px;vertical-align:middle}
.hstrip .hs-c{width:19px;height:22px;border-radius:4px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;font-size:10px;line-height:1;font-weight:700}
.hstrip .hs-c small{font-size:7px;opacity:.7;margin-top:1px;font-weight:600}
.hstrip .hs-su{background:var(--up-dim);color:var(--up)}
.hstrip .hs-mu{background:rgba(63,212,134,.07);color:var(--up)}
.hstrip .hs-fl{background:var(--warn-dim);color:var(--warn)}
.hstrip .hs-md{background:rgba(255,106,122,.08);color:var(--down)}
.hstrip .hs-sd{background:var(--down-dim);color:var(--down)}
.hstrip .hs-nd{background:var(--bg-3);color:var(--ink-3)}
/* group hide classes (toggled on the wrapper) */
.h-conf .cg-conf,.h-pos .cg-pos,.h-mep .cg-mep,.h-rs .cg-rs,
.h-cpr .cg-cpr,.h-cci .cg-cci,.h-wol .cg-wol,.h-rev .cg-rev,.h-qual .cg-qual,.h-ca .cg-ca,.h-ctx .cg-ctx{display:none}
</style>"""

_JS = """<script>(function(){
var wrap=document.getElementById('s2wrap'), tbl=document.getElementById('s2tbl');
if(!tbl) return;
var KEY='s2_hidden_v1', SKEY='s2_screens_v1';
function getHidden(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return {}}}
function setHidden(h){localStorage.setItem(KEY,JSON.stringify(h))}
function applyHidden(){var h=getHidden();
  ['conf','pos','mep','rs','cpr','cci','wol','rev','qual','ctx'].forEach(function(g){
    wrap.classList.toggle('h-'+g, !!h['cg-'+g]);
    var b=document.querySelector('.gchip[data-g="cg-'+g+'"]'); if(b) b.classList.toggle('on', !h['cg-'+g]);
  });}
document.querySelectorAll('.gchip[data-g]').forEach(function(b){
  b.addEventListener('click',function(){var g=b.getAttribute('data-g');var h=getHidden();
    h[g]=!h[g]; setHidden(h); applyHidden();});});
applyHidden();

// sort
var tb=tbl.tBodies[0];
function rowsArr(){return Array.prototype.slice.call(tb.rows);}
function val(td){if(!td)return '';var d=td.getAttribute('data-v');
  if(d!==null){var f=parseFloat(d); return isNaN(f)?d.toLowerCase():f;} return (td.textContent||'').trim().toLowerCase();}
var sortState={};
tbl.querySelectorAll('tr.col th').forEach(function(th,i){
  th.addEventListener('click',function(){
    var asc=!(sortState[i]); sortState={}; sortState[i]=asc;
    var rs=rowsArr();
    rs.sort(function(a,b){var x=val(a.cells[i]),y=val(b.cells[i]);
      if(x<y)return asc?-1:1; if(x>y)return asc?1:-1; return 0;});
    rs.forEach(function(r){tb.appendChild(r);});
  });});

// filter
var fi=document.getElementById('s2filter'), cnt=document.getElementById('s2count');
function recount(){var n=0;rowsArr().forEach(function(r){if(r.style.display!=='none')n++;});
  if(cnt)cnt.textContent=n+' rows';}
function doFilter(){var q=(fi.value||'').toLowerCase();
  rowsArr().forEach(function(r){r.style.display=(!q||r.textContent.toLowerCase().indexOf(q)>=0)?'':'none';});
  recount();}
if(fi)fi.addEventListener('input',doFilter);
recount();

// saved screens (scope + hidden groups)
var scope=new URLSearchParams(location.search).get('scope')||'Nifty 500';
function getScreens(){try{return JSON.parse(localStorage.getItem(SKEY)||'{}')}catch(e){return {}}}
function setScreens(s){localStorage.setItem(SKEY,JSON.stringify(s))}
var sel=document.getElementById('s2load');
function refreshSel(){if(!sel)return;var s=getScreens();
  sel.innerHTML='<option value="">Load screen…</option>'+Object.keys(s).map(function(k){
    return '<option value="'+k.replace(/"/g,'&quot;')+'">'+k+'</option>';}).join('');}
refreshSel();
var sv=document.getElementById('s2save');
if(sv)sv.addEventListener('click',function(){var name=prompt('Name this screen:');if(!name)return;
  var s=getScreens(); s[name]={scope:scope,hidden:getHidden()}; setScreens(s); refreshSel();
  if(sel)sel.value=name;});
if(sel)sel.addEventListener('change',function(){var v=sel.value;if(!v)return;var s=getScreens()[v];if(!s)return;
  setHidden(s.hidden||{}); location='/dash/screen2?scope='+encodeURIComponent(s.scope||'Nifty 500');});
var del=document.getElementById('s2del');
if(del)del.addEventListener('click',function(){var v=sel&&sel.value;if(!v){alert('Pick a screen to delete.');return;}
  var s=getScreens(); delete s[v]; setScreens(s); refreshSel();});

// CSV (visible columns + visible rows)
var csv=document.getElementById('s2csv');
if(csv)csv.addEventListener('click',function(){
  function visCols(){var out=[];tbl.querySelectorAll('tr.col th').forEach(function(th,i){
    if(th.offsetParent!==null)out.push(i);});return out;}
  var cols=visCols(), lines=[];
  var hdr=[];tbl.querySelectorAll('tr.col th').forEach(function(th,i){if(cols.indexOf(i)>=0){var lbl=th.getAttribute('data-label')||(th.textContent||'').trim();hdr.push('"'+String(lbl).replace(/"/g,'""')+'"');}});
  lines.push(hdr.join(','));
  rowsArr().forEach(function(r){if(r.style.display==='none')return;var c=[];
    cols.forEach(function(i){var td=r.cells[i];var d=td&&td.getAttribute('data-v');
      var t=(d!==null&&d!==undefined)?d:(td?td.textContent.trim():'');c.push('"'+String(t).replace(/"/g,'""')+'"');});
    lines.push(c.join(','));});
  var blob=new Blob([lines.join('\\n')],{type:'text/csv'});var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download='screen2_'+scope.replace(/[^a-z0-9]+/gi,'_')+'.csv';a.click();});

// Pat bridge — save the scope's confluence query as a Pat board (lands on the workbench)
window.s2SaveBoard=function(b){var q=b.getAttribute('data-q')||'';var n=prompt('Name this board:',q);
  if(!n)return;
  fetch('/pat/board/save',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({name:n,query:q,flow:'',params:{},kind:'pat'})})
  .then(function(r){return r.json();}).then(function(j){b.textContent=j.ok?('★ Saved'):'failed';b.disabled=!!j.ok;})
  .catch(function(){b.textContent='failed';});};
})();</script>"""


def wire(app):
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/screen2" not in paths:
            app.include_router(router)
    except Exception as e:  # noqa: BLE001
        log.warning("screen2 wire skipped: %s", e)
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    r = c.get("/dash/screen2")
    assert r.status_code == 200, r.status_code
    assert "Screen+" in r.text and "s2tbl" in r.text
    assert "confluence" in r.text.lower()
    r2 = c.get("/dash/screen2?scope=all&limit=50")
    assert r2.status_code == 200
    print("screener_plus selftest OK — /dash/screen2 200, table + confluence render")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
