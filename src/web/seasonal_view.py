"""Seasonal tape — 25y calendar seasonality of PIT idiosyncratic residuals (P1: index + sector).

The descriptive-only companion to the RS/rotation lenses: for each index and sector, when does it
historically run hot or cold on the calendar — AFTER stripping the market move, so what remains is
the entity's own idiosyncratic *residual* tendency, not beta. Three re-bins of one residual series
(month / ISO-week / weekday); a cell is COLORED only if it clears the full certification stack
(placebo nulls + family-wide FDR + N>=15 years + out-of-sample sign-stability + a pledged India
mechanism), else it is greyed "reported-not-gated". MOST cells grey out — that winnowing IS the
product.

Reads the BOUNDED snapshot tables (seasonal_cells / seasonal_stack / seasonal_outlook) written by
src/automation/seasonal_tape.py; opens hermes.db READ-ONLY (never contends with the writer). The
engine is where all PIT/leak discipline lives; this view only renders the snapshot.

⚠ HONESTY (on-page): (1) NOTHING here is tradeable net of STT/impact (expectancy ~= 0) — never a
signal; (2) point-in-time residuals (no look-ahead), frozen family sha256-hashed before compute;
(3) a white outlook light = the CI touches the 50% baseline = explicitly noise. Descriptive
calendar context, never a ranking or a trade. Route: /dash/seasonal-tape
[?scope=index|sector&entity=..&cal=fy|cy&drill=<month>|wdrill=<iso_week>].
"""
from __future__ import annotations

import sqlite3
import statistics
from datetime import date
from functools import lru_cache
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import DB_PATH
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_DB_PATH = str(DB_PATH)                              # overridable in _selftest (read-only)

_MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
_FISCAL_ORDER = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
_CAL_ORDER = list(range(1, 13))
_LIGHT = {"green": "🟢", "amber": "🟡", "white": "⚪"}
_WEEKDAY_ABBR = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}

_CSS = """
<style>
.st-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 12px;max-width:1180px;}
.st-note b{color:var(--ink);}
.st-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 6px;}
.st-ctrl a{padding:4px 12px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;text-decoration:none;}
.st-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.st-ctrl .lbl{font-size:11px;color:var(--ink-3);margin-right:2px;}
.st-panel{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;padding:15px 17px;margin:0 0 15px;}
.st-h{font-size:15px;font-weight:700;margin:0 0 3px;color:var(--ink);}
.st-h small{font-weight:400;color:var(--ink-3);font-size:12px;}
.st-sub{color:var(--ink-2);font-size:12px;line-height:1.5;margin:4px 0 10px;max-width:1080px;}
.st-ol{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:6px;}
.st-olc{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;font-size:12.5px;}
.st-olc .m{font-weight:700;color:var(--ink);font-size:13px;}
.st-olc .d{font-variant-numeric:tabular-nums;margin-top:3px;color:var(--ink-2);line-height:1.5;}
.st-mech{color:var(--ink-3);font-size:11px;margin-top:4px;}
.st-fence{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.06);border-radius:0 10px 10px 0;
  padding:11px 15px;margin:14px 0 2px;font-size:12.5px;color:var(--ink-2);line-height:1.55;max-width:1120px;}
.st-fence b{color:var(--ink);} .st-fence ul{margin:6px 0 0;padding-left:18px;} .st-fence li{margin:3px 0;}
.st-drill{border-left:3px solid var(--accent);}
/* in-place cell drill (embed only): each week/month panel is a :target block, hidden until its
   cell anchor (#sdrill-w23 / #sdrill-m4) is clicked. The tab JS has no hashchange listener, so
   the hash change reveals the panel without disturbing the dossier's tabs. */
.st-dtgt{display:none;scroll-margin-top:120px;}
.st-dtgt:target{display:block;}
.st-drillwrap{margin-top:2px;}
.st-dlist{display:flex;flex-direction:column;gap:5px;margin-top:6px;max-width:560px;}
.st-drow{display:flex;align-items:center;gap:10px;font-size:12.5px;}
.st-drow .k{width:56px;color:var(--accent);font-weight:600;}
.st-dbar{flex:1;height:14px;background:var(--bg-3);border-radius:7px;overflow:hidden;position:relative;}
.st-dbar i{display:block;height:100%;opacity:.78;position:absolute;top:0;}
.st-drow .v{width:64px;text-align:right;color:var(--ink);font-variant-numeric:tabular-nums;}
.st-chip{font-size:11px;color:var(--ink-3);}
/* placebo / "why grey" teaching block inside a drill — the delta between looks-strong and survives */
.st-placebo{margin-top:12px;padding:11px 13px;border-radius:10px;background:var(--bg-2,rgba(127,127,127,.06));
  border:1px solid var(--line);max-width:560px;}
.st-h2{font-size:12.5px;font-weight:700;color:var(--ink);margin-bottom:7px;}
.st-pbar{position:relative;height:16px;background:var(--bg-3);border-radius:8px;overflow:hidden;}
.st-pzone{position:absolute;left:0;top:0;height:100%;background:var(--ink-4,rgba(127,127,127,.35));opacity:.5;}
.st-pbar i{position:absolute;top:-2px;width:3px;height:20px;border-radius:2px;}
.st-pbl{display:flex;justify-content:space-between;font-size:10.5px;color:var(--ink-3);margin:3px 1px 0;}
.st-pb{font-size:12.5px;color:var(--ink-2);line-height:1.55;margin-top:8px;}
.st-pb b{color:var(--ink);}
.st-search{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0;}
.st-search .st-in{padding:5px 10px;border:1px solid var(--line-2);border-radius:8px;
  background:var(--bg-2);color:var(--ink);font-size:13px;min-width:240px;}
.st-search button{padding:5px 14px;border:1px solid var(--accent);border-radius:8px;
  background:var(--accent);color:#fff;font-size:12.5px;cursor:pointer;}
.st-empty{background:var(--bg-2);border:1px dashed var(--line-2);border-radius:10px;
  padding:14px 16px;color:var(--ink-2);font-size:12.5px;line-height:1.55;max-width:1060px;}
.st-empty b{color:var(--ink);}
.st-strip--desc{opacity:.55;}
.st-cap{color:var(--ink-3);font-size:11px;margin-top:4px;}
.st-prompt{color:var(--ink-2);font-size:13px;margin:10px 0;max-width:900px;}
.st-subnav{margin:2px 0 12px;}
.st-hint{color:var(--ink-3);font-size:12px;margin:2px 0 8px;}
.st-cta{display:inline-block;margin:4px 0 12px;padding:7px 14px;border-radius:9px;
  background:var(--accent);color:#fff;font-size:13px;font-weight:600;text-decoration:none;}
.st-cta:hover{opacity:.9;}
.st-scanall{font-size:12.5px;margin:2px 0 8px;}
.st-scanall a{color:var(--accent-cy);}
</style>
"""


def _subnav(active: str) -> str:
    """Shared sub-nav strip for the three seasonal surfaces (tape / this-month screen / index
    divergence) — rendered at the top of each page so the trio is discoverable from any one of
    them. Deliberately duplicated in seasonal_screen_view.py (no cross-module import, avoids an
    import cycle) rather than factored into a shared module."""
    links = (
        ("screen", "🔍 Scan this month", "/dash/seasonal-screen"),
        ("tape", "📅 Seasonal tape", "/dash/seasonal-tape"),
        ("divergence", "⚖ Index divergence", "/dash/seasonal-divergence"),
    )
    chips = "".join(
        f'<a class="{"on" if key == active else ""}" href="{href}">{lbl}</a>'
        for key, lbl, href in links)
    return f'<div class="st-ctrl st-subnav">{chips}</div>'


def _ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    return con


@lru_cache(maxsize=8)
def _entities(scope: str, db_path: str) -> tuple:
    try:
        con = _ro(db_path)
    except sqlite3.OperationalError:
        return ()
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seasonal_cells'").fetchone():
            return ()
        rows = con.execute(
            "SELECT DISTINCT entity FROM seasonal_cells WHERE scope=? ORDER BY entity", (scope,)).fetchall()
        return tuple(r["entity"] for r in rows)
    finally:
        con.close()


@lru_cache(maxsize=64)
def _compute(scope: str, entity: str, db_path: str):
    """Month stack (year x month z), the certified consensus per month, and the forward outlook —
    all from the bounded snapshot. Returns None when the snapshot is absent/empty for this entity."""
    try:
        con = _ro(db_path)
    except sqlite3.OperationalError:
        return None
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seasonal_stack'").fetchone():
            return None
        stack = con.execute(
            "SELECT cell, year, mean_z FROM seasonal_stack "
            "WHERE scope=? AND entity=? AND axis='month' ORDER BY year, cell", (scope, entity)).fetchall()
        try:
            wstack = con.execute(
                "SELECT cell, year, mean_z FROM seasonal_stack "
                "WHERE scope=? AND entity=? AND axis='iso_week' ORDER BY year, cell",
                (scope, entity)).fetchall()
        except Exception:  # noqa: BLE001 — older snapshot without this axis populated -> []
            wstack = []
        try:
            dstack = con.execute(
                "SELECT cell, year, mean_z FROM seasonal_stack "
                "WHERE scope=? AND entity=? AND axis='weekday' ORDER BY year, cell",
                (scope, entity)).fetchall()
        except Exception:  # noqa: BLE001 — older snapshot without this axis populated -> []
            dstack = []
        cells = con.execute(
            "SELECT cell, script_z, n_years, hit_rate, conf, colored, signed, mechanism, "
            "pledged_sign, gate_flags, emp_p_block, emp_p_phase, null_p95, fdr_pass FROM seasonal_cells "
            "WHERE scope=? AND entity=? AND axis='month'", (scope, entity)).fetchall()
        outlook = con.execute(
            "SELECT cell, k, n, ci_lo, ci_hi, base_rate, edge, fail_avg, fail_worst, light, mechanism "
            "FROM seasonal_outlook WHERE scope=? AND entity=? AND axis='month' ORDER BY cell",
            (scope, entity)).fetchall()
        try:
            wk_rows = con.execute(
                "SELECT cell, script_z, n_years, conf, colored, mechanism, gate_flags, "
                "emp_p_block, emp_p_phase, null_p95, fdr_pass FROM seasonal_cells "
                "WHERE scope=? AND entity=? AND axis='iso_week'", (scope, entity)).fetchall()
        except Exception:  # noqa: BLE001 — older snapshot without this axis populated -> {}
            wk_rows = []
        try:
            wd_rows = con.execute(
                "SELECT cell, script_z, n_years, conf, colored, mechanism, gate_flags, "
                "emp_p_block, emp_p_phase, null_p95, fdr_pass FROM seasonal_cells "
                "WHERE scope=? AND entity=? AND axis='weekday'", (scope, entity)).fetchall()
        except Exception:  # noqa: BLE001
            wd_rows = []
    finally:
        con.close()
    if not stack:
        return None
    years = sorted({r["year"] for r in stack})
    smap = {(r["cell"], r["year"]): r["mean_z"] for r in stack}
    wsmap = {(r["cell"], r["year"]): r["mean_z"] for r in wstack}
    wsyears = sorted({r["year"] for r in wstack})
    dsmap = {(r["cell"], r["year"]): r["mean_z"] for r in dstack}
    dsyears = sorted({r["year"] for r in dstack})
    cmap = {r["cell"]: dict(r) for r in cells}
    omap = {r["cell"]: dict(r) for r in outlook}
    wcmap = {r["cell"]: dict(r) for r in wk_rows}
    dcmap = {r["cell"]: dict(r) for r in wd_rows}
    return {"years": years, "smap": smap, "cmap": cmap, "omap": omap, "wcmap": wcmap, "dcmap": dcmap,
            "wsmap": wsmap, "wsyears": wsyears, "dsmap": dsmap, "dsyears": dsyears}


def _consensus_ribbon_cells(d: dict, order: list) -> list:
    """The consensus-ribbon cell list: (month label, signed value) per dash_seasonal's Consensus
    script panel — t = sign(script_z)*conf for certified months, None (greyed, filtered by
    heat_ribbon) otherwise. Extracted so seasonal_card can reuse the IDENTICAL read."""
    cells = []
    for m in order:
        c = d["cmap"].get(m)
        if c and c.get("colored") and c.get("script_z") is not None:
            sign = 1.0 if c["script_z"] >= 0 else -1.0
            cells.append((_MONTH_ABBR[m], sign * float(c.get("conf") or 0.0)))
        else:
            cells.append((_MONTH_ABBR[m], None))     # greyed -> filtered by heat_ribbon
    return cells


def _axis_strip_cells(cmap: dict, order: list, label_fn) -> tuple:
    """The DESCRIPTIVE strip cell list for a secondary axis (weekly/weekday): (label, script_z) for
    EVERY cell with >=15 years and a script_z, regardless of certification — gating this strip to
    certified-only would empty out almost everywhere (the whole point of this lens is that most
    cells don't certify). Returns (cells, n_cert, n_desc) so the caller can caption both counts."""
    cells, n_cert, n_desc = [], 0, 0
    for c in order:
        row = cmap.get(c)
        populated = bool(row and (row.get("n_years") or 0) >= 15 and row.get("script_z") is not None)
        if populated:
            cells.append((label_fn(c), float(row["script_z"])))
            n_desc += 1
            if row.get("colored"):
                n_cert += 1
        else:
            cells.append((label_fn(c), None))
    return cells, n_cert, n_desc


def _strip_panel(title: str, small: str, plain: str, cmap: dict, order: list, label_fn, *,
                 w: int, h: int, unit: str, title_at: list | None = None,
                 vmax: float | None = None, link_fn=None) -> str:
    """A DESCRIPTIVE (dimmed) heat-ribbon strip for a secondary axis (month/weekly/weekday) — shows
    the raw script_z shape for every populated cell (NOT certified-only, unlike the strict
    certification gate). st-empty (never heat_ribbon's literal 'no data') when nothing is populated
    yet. `vmax` tightens the signed scale (default None = heat_ribbon's own max|value| autoscale) —
    consolidation strips summarize small residuals (~±0.3σ) that a wide ±2.5σ stack scale would wash
    out, so callers pass a tighter vmax (e.g. 0.5) to keep the green/red gradient visible.

    `link_fn(cell)->href`, when given, makes every POPULATED bar a click-through (heat_ribbon's own
    cell_link seam). heat_ribbon indexes AFTER dropping None cells, so the i-th surviving bar is the
    i-th entry of `order` whose value is not None — `populated` below replicates that exact filter
    so the index lines up; do not pass link_fn if that filter ever diverges from heat_ribbon's."""
    cells, n_cert, n_desc = _axis_strip_cells(cmap, order, label_fn)
    if n_desc == 0:
        body = (f'<div class="st-empty">No {_esc(unit)} populated for this entity yet — '
               'not hidden, just not computed/covered.</div>')
    else:
        cell_link = None
        if link_fn:
            populated = [c for c, (_lab, v) in zip(order, cells) if v is not None]
            cell_link = lambda i: link_fn(populated[i])  # noqa: E731
        body = (f'<div class="st-strip--desc">{ifx.heat_ribbon(cells, w=w, h=h, vmax=vmax, title_at=title_at, cell_link=cell_link)}</div>'
               f'<div class="st-cap">{n_cert} of {len(order)} {_esc(unit)} certified '
               '· descriptive shape, never a signal.</div>')
    return (f'<div class="st-panel"><div class="st-h">{_esc(title)} <small>{_esc(small)}</small></div>'
           + ifx.plain(plain) + body + '</div>')


def _consensus_panel(d: dict, order: list) -> str:
    """The Consensus-script panel body: certified months only, via the shared ribbon reader. Zero
    certified renders an honest st-empty (never heat_ribbon's literal 'no data' — an empty script
    IS the finding here, not a missing-data artefact)."""
    ribbon_cells = _consensus_ribbon_cells(d, order)
    n_cert = sum(1 for c in d["cmap"].values() if c.get("colored"))
    if n_cert == 0:
        panel_body = (
            '<div class="st-empty">No month survives certification — empty by design. Every '
            'apparent calendar pattern here failed at least one gate (a placebo null, family-wide '
            'FDR, the 15-year minimum, out-of-sample sign-stability, or a pledged mechanism). '
            '<b>An empty script is the honest finding, not missing data.</b></div>'
            # NOTE: demo_framing() lives in a parallel session's UNCOMMITTED infographics.py; guard
            # so this live 0-cert path never 500s on a host whose infographics.py lacks it yet.
            + getattr(ifx, "demo_framing", lambda: "")())
    else:
        panel_body = ifx.heat_ribbon(ribbon_cells, w=1060, h=42, vmax=1.0)
    return (
        '<div class="st-panel"><div class="st-h">Consensus script '
        '<small>— hue = direction, paleness = uncertainty; only certified months are drawn</small></div>'
        + ifx.plain('The clubbed read across all years. <b>Green</b> = reliably hot, <b>red</b> = '
                    'reliably cold; the <b>paler</b> the bar, the less certain. A gap = that month did '
                    'not survive certification (most months don\'t).')
        + panel_body + '</div>')


def _dict_from_inmemory(payload: dict) -> dict:
    """Convert compute_stock_inmemory()'s raw payload (cells/stack/outlook lists spanning all THREE
    axes) into the SAME {years,smap,cmap,omap,wcmap,dcmap} shape _compute() returns from the
    persisted snapshot — so every render helper below works identically whether the entity is
    persisted or computed on-demand (FIX-2: this never touches hermes.db)."""
    cells = payload.get("cells", [])
    stack = payload.get("stack", [])
    outlook = payload.get("outlook", [])
    cmap = {c["cell"]: c for c in cells if c.get("axis") == "month"}
    wcmap = {c["cell"]: c for c in cells if c.get("axis") == "iso_week"}
    dcmap = {c["cell"]: c for c in cells if c.get("axis") == "weekday"}
    smap = {(cell, year): mz for (_sc, ax, cell, year, mz, _n) in stack if ax == "month"}
    years = sorted({year for (_sc, ax, _cell, year, _mz, _n) in stack if ax == "month"})
    # iso_week + weekday per-year stacks are in the payload too (compute_entity spans all THREE
    # axes) — carry them so the on-demand path renders the 52-week + weekday stacks and their
    # drills identically to the persisted _compute path (previously month-only, a latent gap).
    wsmap = {(cell, year): mz for (_sc, ax, cell, year, mz, _n) in stack if ax == "iso_week"}
    wsyears = sorted({year for (_sc, ax, _cell, year, _mz, _n) in stack if ax == "iso_week"})
    dsmap = {(cell, year): mz for (_sc, ax, cell, year, mz, _n) in stack if ax == "weekday"}
    dsyears = sorted({year for (_sc, ax, _cell, year, _mz, _n) in stack if ax == "weekday"})
    omap = {c: {"k": k, "n": n, "ci_lo": lo, "ci_hi": hi, "base_rate": br, "edge": ed,
                "fail_avg": fa, "fail_worst": fw, "light": lt, "mechanism": mech}
            for (_sc, _asof, _ax, c, _hz, k, n, lo, hi, br, ed, fa, fw, lt, mech) in outlook}
    return {"years": years, "smap": smap, "cmap": cmap, "wcmap": wcmap, "dcmap": dcmap, "omap": omap,
            "wsmap": wsmap, "wsyears": wsyears, "dsmap": dsmap, "dsyears": dsyears}


def _stock_search_box(entity: str, cal: str, ents: tuple) -> str:
    """Free-typed symbol search (GET form, read-only) — the ~500+ symbol universe is never chip-
    listed; this replaces the old dead single-chip block that silently defaulted to ents[0]."""
    opts = "".join(f'<option value="{_esc(e)}"></option>' for e in ents)
    cur = f' value="{_esc(entity)}"' if entity else ''
    return (
        '<form class="st-search" method="get" action="/dash/seasonal-tape">'
        '<input type="hidden" name="scope" value="stock">'
        f'<input type="hidden" name="cal" value="{_esc(cal)}">'
        '<input class="st-in" list="st-syms" name="entity" autocomplete="off" '
        'placeholder="Search any NSE EQ symbol — e.g. RELIANCE" '
        f'oninput="this.value=this.value.toUpperCase()"{cur}>'
        f'<datalist id="st-syms">{opts}</datalist>'
        '<button type="submit">Load</button>'
        f'<span class="st-chip">{len(ents)} stocks covered — full EQ list, not a Nifty-500 cap</span>'
        '</form>')


_CARD_CSS = (
    "<style>"
    ".sc-card{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;"
    "padding:14px 16px;margin:0 0 14px;max-width:620px;}"
    ".sc-card .sc-h{font-size:14px;font-weight:700;margin:0 0 8px;color:var(--ink);}"
    ".sc-card .sc-bl{font-size:13px;line-height:1.5;color:var(--ink);margin:0 0 8px;}"
    ".sc-card .sc-note{font-size:11.5px;color:var(--ink-3);margin:6px 0 8px;}"
    ".sc-card .sc-fence{font-size:11px;color:var(--ink-2);line-height:1.5;border-left:2px solid var(--warn);"
    "padding:6px 10px;margin:8px 0;background:rgba(var(--warn-rgb),.05);border-radius:0 8px 8px 0;}"
    ".sc-card .sc-fence ul{margin:2px 0 4px;padding-left:16px;}"
    ".sc-card .sc-fence b{color:var(--ink);}"
    ".sc-card a{color:var(--accent-cy);text-decoration:none;font-size:12px;}"
    "</style>"
)


def _iso_week_month(ref_year: int = 2026) -> dict:
    """{ISO week 1..53 -> calendar month of that week's Thursday}. 2026 is a 53-week ISO year so
    week 53 resolves; the guard keeps any short-year edge safe. Approximate by design (weeks don't
    nest in months) — hence the '≈' on every week label the strip renders."""
    out = {}
    for wk in range(1, 54):
        try:
            out[wk] = date.fromisocalendar(ref_year, wk, 4).month
        except ValueError:
            out[wk] = 12
    return out


_WK_MONTH = _iso_week_month()


def _week_daterange(wk: int, ref_year: int = 2026) -> str:
    """Approx 'Jun 30–Jul 06' span of an ISO week (reference year) for the hover tooltip."""
    try:
        mon = date.fromisocalendar(ref_year, wk, 1)
        sun = date.fromisocalendar(ref_year, wk, 7)
    except ValueError:
        return "year-end"
    if mon.month == sun.month:
        return f"{_MONTH_ABBR[mon.month]} {mon.day}–{sun.day}"
    return f"{_MONTH_ABBR[mon.month]} {mon.day} – {_MONTH_ABBR[sun.month]} {sun.day}"


def _svg_open(w: int, h: int) -> str:
    return (f'<svg viewBox="0 0 {w} {h}" class="ifx" role="img" '
            'preserveAspectRatio="xMidYMid meet" style="max-width:100%;height:auto">')


def _month_strip(cmap: dict, order: list, *, w: int = 560, h: int = 50, vmax: float = 0.5) -> str:
    """12 LABELLED month cells (each month named beneath it), coloured by its average residual; a
    dot marks a certified month; hover carries the value + up-years. Every month is present and
    labelled, so the card leads with the picture a reader thinks in — never an empty 'no data'."""
    n = len(order)
    bw = w / n
    top, band = 3, h - 24
    parts = [_svg_open(w, h)]
    for i, mth in enumerate(order):
        x = i * bw
        c = cmap.get(mth) or {}
        sz = c.get("script_z")
        ny = c.get("n_years") or 0
        cert = bool(c.get("colored"))
        if sz is not None and ny >= 15:
            hr = c.get("hit_rate")
            up = f" · {round(hr * ny)}/{ny} up" if (hr is not None and ny) else ""
            fill = ifx.signed_fill(sz / vmax)
            tip = f"{_MONTH_ABBR[mth]} · {sz:+.2f}σ{up} · {'certified' if cert else 'descriptive'}"
        else:
            fill = "var(--bg-3)"
            tip = f"{_MONTH_ABBR[mth]} · no 15-year history"
        parts.append(
            f'<rect x="{x:.2f}" y="{top}" width="{bw - 1.4:.2f}" height="{band}" rx="2" '
            f'fill="{fill}"><title>{_esc(tip)}</title></rect>')
        if cert:
            parts.append(f'<circle cx="{x + bw / 2:.1f}" cy="{top + 4:.1f}" r="2.1" '
                         'fill="var(--accent-cy)"/>')
        parts.append(
            f'<text x="{x + bw / 2:.1f}" y="{h - 6}" text-anchor="middle" '
            f'fill="var(--ink-3)" font-size="9.5">{_MONTH_ABBR[mth]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _week_strip(wcmap: dict, *, w: int = 560, h: int = 44, vmax: float = 0.5,
                link_fn=None, mark_best: bool = False, week_ticks: bool = False) -> str:
    """53 FIXED ISO-week slots (gaps drawn faint, positions preserved so weeks map to a stable x),
    with month tick-labels beneath at each month's first week — so a hot patch reads as 'that's
    July', not 'week 27 of what?'. Hover on any cell = 'W27 ≈ Jun 30–Jul 06 · +0.31σ'.

    Full-page options: `week_ticks` prints week numbers (W1, W5, …) along the TOP so you never have
    to hover to place a bar; `mark_best` puts a ★ over the strongest positive week; `link_fn(wk)`
    makes each populated bar a click-through to the year-by-year drill."""
    weeks = list(range(1, 54))
    bw = w / len(weeks)
    top = 14 if week_ticks else 3
    bottom_pad = 16 if week_ticks else 15
    band = h - top - bottom_pad
    best_wk = None
    if mark_best:
        pop = [(wk, (wcmap.get(wk) or {}).get("script_z")) for wk in weeks
               if (wcmap.get(wk) or {}).get("script_z") is not None
               and ((wcmap.get(wk) or {}).get("n_years") or 0) >= 15]
        if pop:
            cand_wk, cand_sz = max(pop, key=lambda t: t[1])
            if cand_sz > 0:
                best_wk = cand_wk
    parts = [_svg_open(w, h)]
    for i, wk in enumerate(weeks):
        x = i * bw
        c = wcmap.get(wk) or {}
        sz = c.get("script_z")
        ny = c.get("n_years") or 0
        rng = _week_daterange(wk)
        if sz is not None and ny >= 15:
            fill = ifx.signed_fill(sz / vmax)
            tip = f"W{wk} ≈ {rng} · {sz:+.2f}σ"
        else:
            fill = "var(--bg-3)"
            tip = f"W{wk} ≈ {rng} · no 15-year history"
        rect = (f'<rect x="{x:.2f}" y="{top}" width="{bw + 0.4:.2f}" height="{band}" '
                f'fill="{fill}"><title>{_esc(tip)}</title></rect>')
        if link_fn and sz is not None and ny >= 15:
            rect = f'<a href="{_esc(link_fn(wk))}">{rect}</a>'
        parts.append(rect)
        if wk == best_wk:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{top - 3:.1f}" text-anchor="middle" '
                         'fill="var(--warn)" font-size="10">★</text>')
    if week_ticks:
        for i, wk in enumerate(weeks):
            if wk % 4 == 1:
                parts.append(f'<text x="{i * bw + 1:.1f}" y="9" fill="var(--ink-3)" '
                             f'font-size="8">W{wk}</text>')
    seen = set()
    for i, wk in enumerate(weeks):
        mo = _WK_MONTH.get(wk)
        if mo and mo not in seen:
            seen.add(mo)
            x = i * bw
            parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + band}" '
                         'stroke="var(--bg-1)" stroke-width="1"/>')
            parts.append(f'<text x="{x + 1.5:.1f}" y="{h - 5}" fill="var(--ink-2)" '
                         f'font-size="8.5">{_MONTH_ABBR[mo]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _month_bars(cmap: dict, order: list, *, w: int = 1060, vmax: float = 0.5, link_fn=None) -> str:
    """Diverging BAR chart of each month's 25-year average residual — bar HEIGHT = magnitude, so the
    strongest month is unmistakably the tallest (not a green shade you must decode). Green bars rise
    above the baseline, red fall below; the value (σ) is printed on each bar; every month is named
    beneath with its <b>#rank</b> (residual, hottest→coldest); <b>★</b> marks the single strongest
    month; a certified month's name is drawn in accent. Populated bars click through to the drill."""
    n = len(order)
    bw = w / n
    h, mid, maxbar = 140, 58, 38
    pop = []
    for mth in order:
        c = cmap.get(mth) or {}
        sz = c.get("script_z")
        if sz is not None and (c.get("n_years") or 0) >= 15:
            pop.append((mth, sz))
    rankmap = {mth: r for r, (mth, _s) in enumerate(sorted(pop, key=lambda t: t[1], reverse=True), 1)}
    best = max(pop, key=lambda t: t[1])[0] if pop else None
    best_pos = bool(pop) and dict(pop)[best] > 0
    parts = [_svg_open(w, h)]
    parts.append(f'<line x1="0" y1="{mid}" x2="{w}" y2="{mid}" stroke="var(--line-2)" stroke-width="1"/>')
    for i, mth in enumerate(order):
        cx = i * bw + bw / 2
        c = cmap.get(mth) or {}
        sz = c.get("script_z")
        ny = c.get("n_years") or 0
        cert = bool(c.get("colored"))
        nm = _MONTH_ABBR[mth]
        if sz is not None and ny >= 15:
            t = max(-1.0, min(1.0, sz / vmax))
            bh = max(1.0, abs(t) * maxbar)
            col = "var(--up)" if sz >= 0 else "var(--down)"
            if sz >= 0:
                ry, vy = mid - bh, mid - bh - 3
            else:
                ry, vy = mid, mid + bh + 9
            bwid = bw * 0.6
            hr = c.get("hit_rate")
            up = f" · {round(hr * ny)}/{ny} up" if (hr is not None and ny) else ""
            rk = rankmap.get(mth)
            tip = (f"{nm} · {sz:+.2f}σ{up} · rank {rk} of {len(pop)} · "
                   f"{'certified' if cert else 'descriptive'}")
            rect = (f'<rect x="{cx - bwid / 2:.1f}" y="{ry:.1f}" width="{bwid:.1f}" '
                    f'height="{bh:.1f}" rx="2" fill="{col}" opacity="0.82">'
                    f'<title>{_esc(tip)}</title></rect>')
            if link_fn:
                rect = f'<a href="{_esc(link_fn(mth))}">{rect}</a>'
            parts.append(rect)
            parts.append(f'<text x="{cx:.1f}" y="{vy:.1f}" text-anchor="middle" fill="var(--ink)" '
                         f'font-size="9.5" font-weight="600">{sz:+.1f}</text>')
            if mth == best and best_pos:
                parts.append(f'<text x="{cx:.1f}" y="{max(9.0, ry - 12):.1f}" text-anchor="middle" '
                             'fill="var(--warn)" font-size="12">★</text>')
            rk_col = "var(--warn)" if (mth == best and best_pos) else "var(--ink-3)"
            rk_txt = f"#{rk}" + (" best" if (mth == best and best_pos) else "")
            parts.append(f'<text x="{cx:.1f}" y="{h - 3}" text-anchor="middle" fill="{rk_col}" '
                         f'font-size="8.5">{_esc(rk_txt)}</text>')
        else:
            parts.append(f'<rect x="{cx - 2:.1f}" y="{mid - 1:.1f}" width="4" height="2" '
                         f'fill="var(--bg-3)"><title>{_esc(nm)} · no 15-year history</title></rect>')
            parts.append(f'<text x="{cx:.1f}" y="{h - 3}" text-anchor="middle" fill="var(--ink-4)" '
                         'font-size="8">—</text>')
        parts.append(f'<text x="{cx:.1f}" y="{h - 14}" text-anchor="middle" '
                     f'fill="{"var(--accent-cy)" if cert else "var(--ink-2)"}" '
                     f'font-size="10">{nm}</text>')
    parts.append("</svg>")
    return "".join(parts)


def seasonal_card(scope: str, entity: str, *, db_path: str | None = None, heading: bool = True) -> str:
    """Reusable COMPACT seasonal card for embedding in another lens (the stock detail page's
    Seasonal tab, the index/sector detail page). Resolves `entity` case-insensitively against the
    frozen universe for `scope` (index_rows/index casing is inconsistent; stock symbols are usually
    already upper). Returns '' (honest-empty) when the scope/entity has no snapshot coverage — a
    silent no-op for the caller, never a fabricated card.

    DESCRIPTIVE-ONLY FENCE: reads ONLY seasonal_cells + seasonal_stack (via _compute) — this card
    must NEVER read or surface seasonal_outlook (the forward 1-month horizon + traffic-light read);
    that stays exclusive to the full /dash/seasonal-tape page. `d["omap"]` is deliberately unused."""
    path = db_path or _DB_PATH
    ents = _entities(scope, path)
    if not ents:
        return ''
    resolved = {e.upper(): e for e in ents}.get((entity or "").strip().upper())
    if not resolved:
        return ''
    d = _compute(scope, resolved, path)
    if not d:
        return ''
    certified = [c for c in d["cmap"].values() if c.get("colored")]
    if certified:
        names = ", ".join(sorted(_MONTH_ABBR[c["cell"]] for c in certified))
        bl = (f'<b>{_esc(resolved)}</b>: <b>{_esc(names)}</b> survive(s) the full certification stack '
              '— historically hot/cold after stripping the market, with a named mechanism behind each.')
    else:
        bl = (f'<b>{_esc(resolved)}</b>: no calendar cell survives certification — '
              'indistinguishable from chance.')
    heading_html = ('<div class="sc-h">Seasonal tape <small style="font-weight:400;color:var(--ink-3);'
                    'font-size:11px">25-year calendar seasonality</small></div>') if heading else ''
    caveats = '<li>Single-day residual spikes may reflect an un-taped corporate action.</li>'
    if scope == 'stock':
        caveats += '<li>Current-membership universe — survivor-conditional.</li>'
    link = f'/dash/seasonal-tape?scope={scope}&entity={quote(resolved)}'
    # finer weekly strip only when this entity has ANY populated ISO-week cell (>=15y)
    wk_desc = any((c.get("script_z") is not None and (c.get("n_years") or 0) >= 15)
                  for c in d.get("wcmap", {}).values())
    weekly_html = (
        '<div class="sc-note" style="margin-top:8px">Weekly detail '
        '<span style="color:var(--ink-4)">— ISO weeks, month-anchored; hover any cell</span></div>'
        + _week_strip(d.get("wcmap", {}))
    ) if wk_desc else ''
    return (
        _CARD_CSS
        + '<div class="sc-card">' + heading_html
        + f'<div class="sc-bl">{bl}</div>'
        + '<div class="sc-note" style="margin-top:2px">Monthly rhythm '
          '<span style="color:var(--ink-4)">— Jan→Dec, avg residual (● = certified); hover for '
          'the number</span></div>'
        + _month_strip(d["cmap"], _CAL_ORDER)
        + weekly_html
        + f'<div class="sc-note">{len(certified)} of 12 months certified; the rest '
          'indistinguishable from chance.</div>'
        + f'<div class="sc-fence"><ul>{caveats}</ul><b>Descriptive calendar context, never a signal.</b></div>'
        + f'<div><a href="{_esc(link)}">Open the full seasonal tape →</a></div>'
        + '</div>')


def _placebo_block(cellrow: dict, axis: str, entity: str, label: str) -> str:
    """The teaching artifact inside every drill: turn the seductive hit-rate into the TWO honest
    gates it must clear, so a reader learns the delta between 'looks strong' and 'survives looking'.
    Data-driven from the per-cell placebo stats (emp_p_block/emp_p_phase/null_p95/fdr_pass):
      gate 1 = single-calendar placebo (does it beat a random reshuffle of the entity's own calendar?)
      gate 2 = multiple-cell correction (BH-Yekutieli across the axis' 12 months / 53 weeks / 5 weekdays)
    The canonical lesson (MARUTI Sep, 89% up, still grey): a cell can CLEAR gate 1 yet die at gate 2 —
    strong in isolation is not the same as surviving the look-elsewhere across the whole calendar."""
    z = cellrow.get("script_z")
    pb, pr = cellrow.get("emp_p_block"), cellrow.get("emp_p_phase")
    if z is None or pb is None or pr is None:
        return ''  # older snapshot without placebo stats -> skip quietly, never fabricate
    p95 = cellrow.get("null_p95")
    n_years = cellrow.get("n_years") or 0
    hit = cellrow.get("hit_rate")
    colored = bool(cellrow.get("colored"))
    fdr = bool(cellrow.get("fdr_pass"))
    flags = cellrow.get("gate_flags") or ""
    m, noun = {"month": (12, "months"), "iso_week": (53, "weeks"),
               "weekday": (5, "weekdays")}.get(axis, (12, "cells"))
    p_pct = max(pb, pr) * 100.0          # must clear BOTH nulls -> the harder one is the honest headline
    g_null = pb < 0.05 and pr < 0.05
    hit_pct = f"{hit*100:.0f}%" if hit is not None else "—"
    hotcold = "hot" if (z or 0) >= 0 else "cold"

    bar = ''
    if p95 is not None and p95 > 0:
        az = abs(z); scale = (max(az, p95) * 1.2) or 1.0
        zone = min(100.0, p95 / scale * 100.0); mk = min(100.0, az / scale * 100.0)
        inside = az <= p95
        mcol = "var(--down)" if inside else "var(--up)"
        bar = (f'<div class="st-pbar" title="the shaded band is the strongest a random calendar '
               f'reshuffle produces 95% of the time; the tick is this cell">'
               f'<div class="st-pzone" style="width:{zone:.0f}%"></div>'
               f'<i style="left:{mk:.0f}%;background:{mcol}"></i></div>'
               f'<div class="st-pbl"><span>chance’s 95% reach</span>'
               f'<span>this {_esc(label)}: {z:+.2f}σ</span></div>')

    if colored:
        head = "Why this reads <b>certified</b>"
        body = (f"It clears the single-calendar placebo (a random reshuffle of {_esc(entity)}’s own "
                f"calendar beats it only <b>{p_pct:.1f}%</b> of the time) <i>and</i> survives the correction "
                f"for testing all {m} {noun} — the rare cell that certifies. Still descriptive: a base rate "
                "with a named mechanism, never a standalone trade.")
    elif "N<" in flags or n_years < 15:
        head = "Why this reads <b>grey</b>"
        body = (f"Only <b>{n_years}</b> years of history — too few to test a stable seasonal read "
                "(needs ≥15). Shown for completeness, not assessed.")
    elif not g_null:
        head = "Why this reads <b>grey</b>"
        body = (f"Reshuffle {_esc(entity)}’s own calendar at random and a {_esc(label)} at least this "
                f"{hotcold} turns up <b>{p_pct:.1f}%</b> of the time — so the {hit_pct} you see sits "
                "<b>inside what pure chance produces</b>. That is the whole reason it stays grey.")
    elif not fdr:
        head = "Why this reads <b>grey</b> — the subtle one"
        body = (f"On its own this looks strong: a random reshuffle beats it only <b>{p_pct:.1f}%</b> of the "
                f"time. But it is <b>1 of {m} {noun}</b> tested for {_esc(entity)}; correct for looking at all "
                f"{m} (dependency-safe Benjamini–Hochberg–Yekutieli) and it no longer stands. "
                f"<b>Strong in isolation ≠ surviving the look across the whole calendar</b> — {hit_pct} up, "
                "still grey.")
    else:
        head = "Why this reads <b>grey</b>"
        reason = ("its sign flips across sub-periods" if "sign" in flags else
                  "it collapses inside the earnings window (PEAD guard)" if "mask" in flags else
                  "a certification gate did not clear")
        body = f"It clears the placebo but {reason} — so it is reported, not certified."

    return (f'<div class="st-placebo"><div class="st-h2">{head}</div>{bar}'
            f'<div class="st-pb">{body}</div></div>')


def _drill_panel(scope: str, entity: str, d: dict, cell: int, order: list, *,
                 axis: str = "month", panel_id: str = "drill", back: str | None = None,
                 inline: bool = False) -> str:
    """Server-rendered breakdown for one calendar cell: the per-year z values behind the script.
    axis="month" (default) is the ORIGINAL per-month breakdown, unchanged byte-for-byte. axis=
    "iso_week" mirrors it for the 52-week stack (d["wsmap"]/d["wcmap"]/d["wsyears"]) — same panel
    shell, same st-drill styling, same "No {label} history" honest-empty branch; only the source
    maps and the cell label differ.

    Embed reuse (inline=True): the SAME panel becomes a hidden :target block (class st-dtgt,
    unique panel_id like 'sdrill-w23') so a detail page reveals it IN PLACE on a cell click,
    instead of navigating to the lens. `back` overrides the footer link (→ '#stx-top' to close);
    defaults (inline=False, panel_id='drill', back=None) keep the /dash/seasonal-tape output
    byte-for-byte identical."""
    if axis == "iso_week":
        stackmap = d.get("wsmap", {})
        cellinfo = d.get("wcmap", {})
        label = f"Week {cell}"
        yrs = d.get("wsyears", d["years"])
    elif axis == "weekday":
        stackmap = d.get("dsmap", {})
        cellinfo = d.get("dcmap", {})
        label = _WEEKDAY_ABBR.get(cell, str(cell))
        yrs = d.get("dsyears", d["years"])
    else:
        stackmap = d["smap"]
        cellinfo = d["cmap"]
        label = _MONTH_ABBR.get(cell, str(cell))
        yrs = d["years"]
    vals = [(y, stackmap.get((cell, y))) for y in yrs if stackmap.get((cell, y)) is not None]
    cellrow = cellinfo.get(cell, {})
    back = back or f'/dash/seasonal-tape?scope={_esc(scope)}&entity={_esc(entity)}'
    back_label = "← close" if inline else "← back to the tape"
    tgt = " st-dtgt" if inline else ""
    if not vals:
        return (f'<div class="st-panel st-drill{tgt}" id="{panel_id}"><div class="st-h">No {label} history</div>'
                f'<div><a href="{back}">{back_label}</a></div></div>')
    vmax = max(abs(v) for _y, v in vals) or 1.0
    rows = ""
    for y, v in sorted(vals, key=lambda t: t[0], reverse=True):
        w = min(50, abs(v) / vmax * 50)
        left = 50 if v >= 0 else 50 - w
        col = "var(--up)" if v >= 0 else "var(--down)"
        rows += (f'<div class="st-drow"><span class="k">{y}</span>'
                 f'<span class="st-dbar"><i style="left:{left:.0f}%;width:{w:.0f}%;background:{col}"></i></span>'
                 f'<span class="v">{v:+.2f}σ</span></div>')
    sz = cellrow.get("script_z")
    verdict = "certified" if cellrow.get("colored") else "reported, not gated"
    mech = cellrow.get("mechanism") or "—"
    flags = cellrow.get("gate_flags") or ""
    head_label = f"{label} — year by year" if axis in ("iso_week", "weekday") else label
    hd = (f'{_esc(entity)} · {head_label} <small>— script {sz:+.2f}σ over {len(vals)} years, '
          f'{verdict}</small>') if sz is not None else f'{_esc(entity)} · {head_label}'
    return (
        f'<div class="st-panel st-drill{tgt}" id="{panel_id}">'
        f'<div class="st-h">Behind the script · {hd}</div>'
        + ifx.plain('The consensus shows the <b>average</b> year. Here is <b>every</b> year\'s ' + label
                    + ' residual, newest first — the dispersion the single number hides. A run of '
                    'similar bars = a real tendency; one or two outliers carrying it = not one.')
        + f'<div class="st-dlist">{rows}</div>'
        + _placebo_block(cellrow, axis, entity, label)
        + f'<div class="st-chip" style="margin-top:8px">mechanism: {_esc(mech)} · gates: {_esc(flags)}</div>'
        + f'<div style="margin-top:8px"><a href="{back}">{back_label}</a></div></div>')


def _panels_html(d: dict, scope: str, entity: str, order: list, cal: str, *,
                 inline_drill: bool = False) -> str:
    """The FULL seasonal analysis panels for one entity — EVERY perspective, shared verbatim by the
    /dash/seasonal-tape route AND the inline detail-page embed (seasonal_full_panel): the 25-year
    month stack, the monthly consolidation gradient, the 52-week stack, the weekly + weekday
    consolidations, the event-cadence lens, and the forward outlook.

    Cell clicks drill year-by-year. On the lens (inline_drill=False) a click deep-links to the full
    page's server-rendered drill (byte-for-byte unchanged). In an embed (inline_drill=True) the
    click instead reveals a PRE-RENDERED :target panel in place (see _mlink/_wlink → '#sdrill-*'
    and the appended st-dtgt blocks) — the identical _drill_panel body, no page navigation, no
    dependence on the host page's tab JS."""
    parts = []

    def _mlink(m):
        return (f'#sdrill-m{m}' if inline_drill else
                f'/dash/seasonal-tape?scope={scope}&entity={_esc(entity)}&cal={cal}&drill={m}#drill')

    def _wlink(wk):
        return (f'#sdrill-w{wk}' if inline_drill else
                f'/dash/seasonal-tape?scope={scope}&entity={_esc(entity)}&cal={cal}&wdrill={wk}#drill')

    def _dlink(wd):
        return (f'#sdrill-d{wd}' if inline_drill else
                f'/dash/seasonal-tape?scope={scope}&entity={_esc(entity)}&cal={cal}&ddrill={wd}#drill')

    col_labels = [_MONTH_ABBR[m] for m in order]
    yrs_desc = sorted(d["years"], reverse=True)
    matrix = [[d["smap"].get((m, y)) for m in order] for y in yrs_desc]
    parts.append('<div class="st-hint">💡 Click any month cell below to break it down year-by-year.</div>')
    parts.append(
        '<div class="st-panel"><div class="st-h">25-year stack '
        '<small>— each cell = that year\'s residual for that month, in σ</small></div>'
        + ifx.plain('Each <b>row</b> is a year (newest on top), each <b>column</b> a month. '
                    '<b>Green</b> = the month ran <b>above</b> this entity\'s own baseline that year, '
                    '<b>red</b> below; a <b>blank</b> cell = too few observations. Read <b>down a '
                    'column</b> to judge whether a month is a real tendency or just 2–3 loud years. '
                    '<b>Click a column\'s cell</b> to break the month down year-by-year.')
        + ifx.heat_grid([str(y) for y in yrs_desc], col_labels, matrix, w=1060, cell_h=22,
                        row_w=64, signed=True, fmt=1, unit="σ", vmin=-2.5, vmax=2.5,
                        cell_link=lambda i, j: _mlink(order[j]))
        + '</div>')
    # month consolidation — a diverging BAR chart (height = magnitude), every month named + ranked,
    # ★ on the strongest, value printed on each bar (so the reader never has to decode a shade).
    n_month_cert = sum(1 for c in d["cmap"].values() if c.get("colored"))
    parts.append(
        '<div class="st-panel"><div class="st-h">Monthly consolidation '
        '<small>— every month named &amp; ranked by its 25-year average residual; ★ = strongest '
        'month</small></div>'
        + ifx.plain('One bar per month. <b>Bar height = the size of the move</b> (σ), green above '
                    'this entity\'s own baseline, red below — so the strongest month is simply the '
                    'tallest, no shade to decode. The number on each bar is that value; the '
                    '<b>#rank</b> under each name orders the months hottest→coldest, and <b>★</b> '
                    'marks the single strongest. Click a bar to break the month down year-by-year. '
                    'Descriptive shape, never a signal.')
        + _month_bars(d["cmap"], order, w=1060, vmax=0.5, link_fn=_mlink)
        + f'<div class="st-cap">{n_month_cert} of 12 months certified · descriptive shape, '
          'never a signal.</div></div>')
    # 52-week stack: the per-year ISO-week mirror of the month stack above.
    wsyears_desc = sorted(d.get("wsyears", []), reverse=True)
    week_cols = list(range(1, 54))
    week_w = 50 + len(week_cols) * 20
    if wsyears_desc:
        week_col_labels = [f"W{w}" if w % 4 == 1 else "" for w in week_cols]
        week_matrix = [[d.get("wsmap", {}).get((w, y)) for w in week_cols] for y in wsyears_desc]
        week_grid = ifx.heat_grid([str(y) for y in wsyears_desc], week_col_labels, week_matrix,
                                  w=week_w, cell_h=20, row_w=50, signed=True, fmt=1, unit="σ",
                                  vmin=-2.5, vmax=2.5,
                                  cell_link=lambda i, j: _wlink(week_cols[j]))
        week_stack_body = f'<div style="overflow-x:auto"><div style="width:{week_w}px">{week_grid}</div></div>'
    else:
        week_stack_body = ('<div class="st-empty">No 52-week stack populated for this entity yet — '
                           'not hidden, just not computed/covered.</div>')
    parts.append('<div class="st-hint">💡 Click any week cell to break it down year-by-year.</div>')
    parts.append(
        '<div class="st-panel"><div class="st-h">52-week stack '
        '<small>— each cell = that year\'s residual for that ISO week, in σ</small></div>'
        + ifx.plain('Same idea as the month stack, one column per ISO calendar week. Wide — '
                    'scroll sideways. Read down a column to judge a real weekly tendency vs a '
                    'couple of loud years.')
        + week_stack_body + '</div>')
    # weekly consolidation — month-anchored: week numbers along the top, month labels beneath, so a
    # bar is placeable without hovering; ★ on the strongest week; click-through to the week drill.
    parts.append(
        '<div class="st-panel"><div class="st-h">Weekly consolidation '
        '<small>— ISO weeks 1–53, month-anchored; week numbers on top, months beneath; ★ = '
        'strongest week</small></div>'
        + ifx.plain('Same idea across ISO weeks. <b>Week numbers</b> (W1, W5, …) run along the top '
                    'and <b>month labels</b> beneath, so you can place any bar without hovering — '
                    'the hover still gives the exact value and week date-span. <b>★</b> marks the '
                    'strongest week; click any bar to break it down year-by-year. Descriptive.')
        + '<div style="overflow-x:auto">'
        + _week_strip(d.get("wcmap", {}), w=1060, h=60, vmax=0.5, mark_best=True, week_ticks=True,
                      link_fn=_wlink)
        + '</div></div>')
    # weekday stack: the per-year Mon–Fri mirror of the month / 52-week stacks — same read (down a
    # column = a real day-of-week tendency vs a few loud years) + per-weekday year-by-year drill.
    dsyears_desc = sorted(d.get("dsyears", []), reverse=True)
    wd_cols = [0, 1, 2, 3, 4]
    if dsyears_desc:
        wd_col_labels = [_WEEKDAY_ABBR[c] for c in wd_cols]
        wd_matrix = [[d.get("dsmap", {}).get((c, y)) for c in wd_cols] for y in dsyears_desc]
        wd_grid = ifx.heat_grid([str(y) for y in dsyears_desc], wd_col_labels, wd_matrix,
                                w=440, cell_h=20, row_w=50, signed=True, fmt=1, unit="σ",
                                vmin=-2.5, vmax=2.5, cell_link=lambda i, j: _dlink(wd_cols[j]))
        parts.append('<div class="st-hint">💡 Click any weekday cell to break it down year-by-year.</div>')
        parts.append(
            '<div class="st-panel"><div class="st-h">Weekday stack '
            '<small>— each cell = that year\'s residual for that weekday, in σ</small></div>'
            + ifx.plain('The Mon–Fri mirror of the month and 52-week stacks: each <b>row</b> is a '
                        'year, each <b>column</b> a weekday. Read <b>down a column</b> to judge '
                        'whether a day-of-week tilt (a Monday effect, an expiry-Thursday one) is a '
                        'real tendency or just a couple of loud years. <b>Click a cell</b> for the '
                        'year-by-year breakdown. Descriptive, never a signal.')
            + f'<div style="overflow-x:auto"><div style="width:440px">{wd_grid}</div></div></div>')
    parts.append(_strip_panel(
        "Weekday", "— Monday–Friday, same certification bar as months",
        "Day-of-week tendency (e.g. a Monday effect), shown descriptively — most days will "
        "show nothing.",
        d.get("dcmap", {}), [0, 1, 2, 3, 4], lambda c: _WEEKDAY_ABBR[c],
        w=1060, h=40, unit="weekdays", vmax=0.5))
    # events lens (descriptive-factual, TIME-only): guarded import, honest-empty on no snapshot
    try:
        from src.web.seasonal_events_view import render_events_section
        ev_section = render_events_section(scope, entity, cal, db_path=_DB_PATH)
        if ev_section:
            parts.append(ev_section)
    except Exception:  # noqa: BLE001 — the events lens must never break the page
        pass
    # forward outlook strip
    if d["omap"]:
        cards = ""
        for m in order:
            o = d["omap"].get(m)
            if not o:
                continue
            lo, hi = o["ci_lo"] * 100, o["ci_hi"] * 100
            rate = 100.0 * o["k"] / o["n"] if o["n"] else 0.0
            light = _LIGHT.get(o["light"], "⚪")
            mech = o.get("mechanism") or ""
            mech_html = f'<div class="st-mech">{_esc(mech)}</div>' if mech else ""
            edge = o["edge"] * 100
            cards += (
                f'<div class="st-olc"><div class="m">{light} {_MONTH_ABBR[m]}</div>'
                f'<div class="d">up {o["k"]}/{o["n"]} yrs ({rate:.0f}%)<br>'
                f'95% CI {lo:.0f}–{hi:.0f}% · edge {edge:+.0f}pp<br>'
                f'down years avg {o["fail_avg"]:+.2f}σ, worst {o["fail_worst"]:+.2f}σ</div>'
                f'{mech_html}</div>')
        parts.append(
            '<div class="st-panel"><div class="st-h">Forward outlook '
            '<small>— base-rate only; a ⚪ light means the interval touches 50% = noise</small></div>'
            + ifx.plain('For each month: how often it has been positive, with a 95% confidence band. '
                        '🟢 = reliably positive with a mechanism, 🟡 = leans one way, <b>⚪ = the band '
                        'includes a coin-flip, so treat it as noise</b>. This is history\'s base rate, '
                        '<b>not</b> a forecast or a trade.')
            + f'<div class="st-ol">{cards}</div></div>')
    # in-place cell drill (embed only): pre-render the year-by-year panel for every POPULATED month
    # and ISO week as a hidden :target block (heat_grid links only populated cells, so this covers
    # exactly the clickable set — no dead anchors). Reuses _drill_panel verbatim, so the embed drill
    # is byte-identical to the lens drill; only the reveal (a #sdrill-* hash) differs.
    if inline_drill:
        panels = []
        months_with_data = {k[0] for k in d.get("smap", {})}
        for m in order:
            if m in months_with_data:
                panels.append(_drill_panel(scope, entity, d, m, order,
                                           panel_id=f"sdrill-m{m}", inline=True, back="#stx-top"))
        week_order = list(range(1, 54))
        weeks_with_data = {k[0] for k in d.get("wsmap", {})}
        for wk in week_order:
            if wk in weeks_with_data:
                panels.append(_drill_panel(scope, entity, d, wk, week_order, axis="iso_week",
                                           panel_id=f"sdrill-w{wk}", inline=True, back="#stx-top"))
        wd_order = [0, 1, 2, 3, 4]
        weekdays_with_data = {k[0] for k in d.get("dsmap", {})}
        for wd in wd_order:
            if wd in weekdays_with_data:
                panels.append(_drill_panel(scope, entity, d, wd, wd_order, axis="weekday",
                                           panel_id=f"sdrill-d{wd}", inline=True, back="#stx-top"))
        if panels:
            parts.append('<div class="st-drillwrap">' + "".join(panels) + '</div>')
    return "".join(parts)


def _honesty_fence() -> str:
    """The shared 'read this honestly' fence (frozen-family hash + the 4 discipline bullets) — used
    by both the full page and the inline embed so the honesty framing travels with the analysis."""
    h = ""
    try:
        con = _ro(_DB_PATH)
        try:
            r = con.execute("SELECT v FROM seasonal_meta WHERE k='frozen_family_sha256'").fetchone()
            h = (r[0][:12] if r else "")
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        h = ""
    return (
        '<div class="st-fence"><b>Read this honestly:</b>'
        '<ul>'
        '<li><b>Not a signal.</b> Nothing here is tradeable net of STT + market impact — expectancy '
        '≈ 0 (PEAD, the closest cousin, net-failed 0.10 Sharpe vs 0.85 buy-and-hold). Descriptive '
        'calendar context, never a ranking or an entry.</li>'
        '<li><b>Point-in-time.</b> Every residual and z is computed only from data knowable that year '
        '(annual expanding fit); the frozen hypothesis family was sha256-hashed <i>before</i> any '
        f'number was computed{f" ({_esc(h)}…)" if h else ""}.</li>'
        '<li><b>Certification is strict.</b> A month is coloured only if it clears two placebo nulls, '
        'family-wide FDR, ≥15 years, out-of-sample sign-stability, AND a pledged India mechanism. Most '
        'cells grey out — that winnowing is the point.</li>'
        '<li><b>Sector residuals</b> strip the Nifty 500 move; the index itself is its own baseline. '
        'Membership for sub-drills is current-tag (survivorship) where it applies.</li>'
        '</ul></div>')


def seasonal_full_panel(scope: str, entity: str, *, db_path: str | None = None,
                        cal: str = "cy") -> str:
    """The COMPLETE seasonal analysis for one entity, for INLINE embedding in a detail page's
    Seasonal tab (the stock dossier, the index/sector page) — the SAME body the full
    /dash/seasonal-tape page renders (bottom line + every perspective panel + honesty fence), NOT
    the reduced compact card. Cell clicks deep-link to the full page's year-by-year drill; a header
    link opens the full page with its calendar/scope controls. '' (honest-empty) when uncovered.

    Resolves `entity` case-insensitively; for a stock not in the persisted snapshot it falls back to
    the engine's READ-ONLY on-demand in-memory compute (never writes hermes.db), same as the route."""
    path = db_path or _DB_PATH
    ents = _entities(scope, path)
    resolved = {e.upper(): e for e in ents}.get((entity or "").strip().upper()) if ents else None
    d = _compute(scope, resolved, path) if resolved else None
    if d is None and scope == "stock":
        q = (entity or "").strip().upper()
        try:
            from src.automation import seasonal_tape as _ST
            _rc = _ST._ro(path)
            try:
                sym = _ST.resolve_stock_symbol(_rc, q)
                if sym:
                    inmem = _ST.compute_stock_inmemory(_rc, sym)
                    if inmem:
                        resolved = inmem.get("entity", sym)
                        d = _dict_from_inmemory(inmem)
            finally:
                _rc.close()
        except Exception:  # noqa: BLE001 — guarded engine import, must never break the caller
            d = None
    if not d:
        return ''
    order = _CAL_ORDER if cal == "cy" else _FISCAL_ORDER
    certified = [c for c in d["cmap"].values() if c.get("colored")]
    if certified:
        names = ", ".join(sorted(_MONTH_ABBR[c["cell"]] for c in certified))
        bl = (f'For <b>{_esc(resolved)}</b>, the calendar cell(s) that survive the full test are '
              f'<b>{_esc(names)}</b> — historically hot/cold after stripping the market, with a named '
              'mechanism behind each. Everything else is greyed: indistinguishable from chance.')
    else:
        bl = (f'For <b>{_esc(resolved)}</b>, <b>no</b> calendar cell survives the certification stack — '
              'every apparent pattern is indistinguishable from a placebo. The greying IS the finding.')
    link = f'/dash/seasonal-tape?scope={scope}&entity={quote(resolved)}'
    return (
        _CSS + ifx.readability_css()
        + '<div class="st-embed" id="stx-top">'
        + ifx.bottom_line(bl + ' This is descriptive calendar context, <b>never</b> a signal.')
        + ifx.how_to_read_link()
        + f'<div style="margin:2px 0 10px"><a class="st-cta" href="{_esc(link)}">Open the full '
          'seasonal tape — calendar/scope controls + year-by-year drill-downs →</a></div>'
        + _panels_html(d, scope, resolved, order, cal, inline_drill=True)
        + _honesty_fence()
        + '</div>')


@router.get("/dash/seasonal-tape", response_class=HTMLResponse)
def dash_seasonal(scope: str = "index", entity: str = "", cal: str = "fy", drill: str = "",
                  wdrill: str = "", ddrill: str = "") -> HTMLResponse:
    scope = scope if scope in ("index", "sector", "stock") else "index"
    order = _CAL_ORDER if cal == "cy" else _FISCAL_ORDER
    body = [_CSS, ifx.readability_css()]
    try:
        ents = _entities(scope, _DB_PATH)
        if not ents and scope != "stock":
            raise LookupError("no snapshot")

        def _stock_early_return(msg_html: str, q_val: str) -> HTMLResponse:
            cur_month = date.today().month
            eb = ['<h2 style="margin:0 0 2px">Seasonal tape '
                 '<small style="color:var(--ink-3);font-size:12px;font-weight:400">stock — search</small>'
                 '</h2>', _subnav("tape"), _stock_search_box(q_val, cal, ents),
                 f'<div class="st-scanall"><a href="/dash/seasonal-screen?scope=stock&month={cur_month}">'
                 '…or scan every stock for this month →</a></div>',
                 f'<div class="st-prompt">{msg_html}</div>']
            return HTMLResponse(_shell("Seasonal tape · patearn", "".join(body + eb), "seasonal-tape", "",
                                       wide=True))

        d = None
        if scope == "stock":
            # ~500+ symbol universe — case-insensitive resolve. FIX-1: NEVER default to ents[0]
            # (silent alphabetical-first) when the query doesn't resolve — an honest search prompt
            # instead. FIX-2: an unrecognized query is resolved + computed READ-ONLY in memory
            # (never written to hermes.db) via the seasonal_tape engine's on-demand bridge.
            q = (entity or "").strip().upper()
            resolved = {e.upper(): e for e in ents}.get(q)
            resolved_sym, inmem = None, None
            if not resolved and q:
                try:
                    from src.automation import seasonal_tape as _ST
                    _rc = _ST._ro(_DB_PATH)
                    try:
                        resolved_sym = _ST.resolve_stock_symbol(_rc, q)
                        if resolved_sym:
                            inmem = _ST.compute_stock_inmemory(_rc, resolved_sym)
                    finally:
                        _rc.close()
                except Exception:  # noqa: BLE001 — guarded engine import, must never break the page
                    resolved_sym, inmem = None, None
            if resolved:
                entity = resolved
                d = _compute(scope, entity, _DB_PATH)
                if not d:
                    return _stock_early_return(
                        f'Resolved to <b>{_esc(entity)}</b> but it computed nothing — insufficient '
                        'history for a stable script. Not hidden, just empty.', entity)
            elif inmem:
                entity = inmem.get("entity", resolved_sym or q)
                d = _dict_from_inmemory(inmem)
            elif q:
                reason = (f'no usable history for <b>{_esc(resolved_sym)}</b> yet (needs a full '
                         'year of trading)' if resolved_sym else
                         f'<b>{_esc(q)}</b> does not resolve to a tradeable NSE EQ symbol')
                return _stock_early_return(f'Searched <b>{_esc(q)}</b> — computed nothing: {reason}. '
                                          'Not hidden, just empty.', q)
            else:
                return _stock_early_return(
                    'Search a symbol above… coverage is the full EQ list, not a Nifty-500 cap.', "")
        else:
            if entity not in ents:
                entity = ents[0]
            d = _compute(scope, entity, _DB_PATH)
        if not d:
            raise LookupError("no coverage")

        body.append('<h2 style="margin:0 0 2px">Seasonal tape '
                    '<small style="color:var(--ink-3);font-size:12px;font-weight:400">25-year calendar '
                    'seasonality of idiosyncratic residuals</small></h2>')
        body.append(_subnav("tape"))
        # bottom line: name the certified months if any
        certified = [c for c in d["cmap"].values() if c.get("colored")]
        if certified:
            names = ", ".join(sorted(_MONTH_ABBR[c["cell"]] for c in certified))
            bl = (f'For <b>{_esc(entity)}</b>, the calendar cell(s) that survive the full test are '
                  f'<b>{_esc(names)}</b> — historically hot/cold after stripping the market, with a named '
                  'mechanism behind each. Everything else is greyed: indistinguishable from chance.')
        else:
            bl = (f'For <b>{_esc(entity)}</b>, <b>no</b> calendar cell survives the certification stack — '
                  'every apparent pattern is indistinguishable from a placebo. The greying IS the finding.')
        body.append(ifx.bottom_line(bl + ' This is descriptive calendar context, <b>never</b> a signal.'))
        body.append(ifx.how_to_read_link())

        # controls: scope + entity + calendar
        scope_tabs = "".join(
            f'<a class="{"on" if scope==s else ""}" href="/dash/seasonal-tape?scope={s}">{lbl}</a>'
            for s, lbl in (("index", "Index"), ("sector", "Sector"), ("stock", "Stock")))
        if scope == "stock":
            # ~500+ symbol universe — a free-typed search box, never a chip row (FIX-1: no
            # ranked/default leaderboard, no silent ents[0] pick).
            ent_chips = _stock_search_box(entity, cal, ents)
        else:
            ent_chips = "".join(
                f'<a class="{"on" if e==entity else ""}" href="/dash/seasonal-tape?scope={scope}&entity={_esc(e)}&cal={cal}">{_esc(e)}</a>'
                for e in ents)
        cal_tabs = "".join(
            f'<a class="{"on" if cal==c else ""}" href="/dash/seasonal-tape?scope={scope}&entity={_esc(entity)}&cal={c}">{lbl}</a>'
            for c, lbl in (("fy", "Apr–Mar"), ("cy", "Jan–Dec")))
        body.append(f'<div class="st-ctrl"><span class="lbl">scope</span>{scope_tabs}</div>')
        body.append(f'<div class="st-ctrl"><span class="lbl">entity</span>{ent_chips}</div>')
        body.append(f'<div class="st-ctrl"><span class="lbl">calendar</span>{cal_tabs}</div>')

        cur_month = date.today().month
        if scope in ("index", "sector"):
            # the index/sector -> constituent-stocks drill (D-seasonal-nav): scan this month's
            # ranked base-rates restricted to THIS entity's current members.
            body.append(
                f'<a class="st-cta" href="/dash/seasonal-screen?scope=stock&index={quote(entity)}'
                f'&month={cur_month}">🔍 Scan the stocks in {_esc(entity)} for '
                f'{_esc(_MONTH_ABBR[cur_month])} →</a>')
        elif scope == "stock":
            body.append(
                f'<div class="st-scanall"><a href="/dash/seasonal-screen?scope=stock&month={cur_month}">'
                '…or scan every stock for this month →</a></div>')

        body.append(_panels_html(d, scope, entity, order, cal))

        if drill:
            try:
                m = int(drill)
                if m in _CAL_ORDER:
                    body.append(f'<div id="drill"></div>{_drill_panel(scope, entity, d, m, order)}')
            except ValueError:
                pass
        if wdrill:
            try:
                w = int(wdrill)
                if 1 <= w <= 53:
                    body.append(f'<div id="drill"></div>{_drill_panel(scope, entity, d, w, list(range(1, 54)), axis="iso_week")}')
            except ValueError:
                pass
        if ddrill:
            try:
                wd = int(ddrill)
                if 0 <= wd <= 4:
                    body.append(f'<div id="drill"></div>{_drill_panel(scope, entity, d, wd, [0, 1, 2, 3, 4], axis="weekday")}')
            except ValueError:
                pass

        body.append(_honesty_fence())
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Seasonal tape</h2>' + _subnav("tape") +
            '<div class="st-note">The seasonal snapshot '
            '(<code>seasonal_cells</code> / <code>seasonal_stack</code>) is not populated on this host. '
            'Run <code>python -m src.automation.seasonal_tape --backfill --scope index</code> on the box. '
            'This surface is read-only and never fabricates data.</div>')
    return HTMLResponse(_shell("Seasonal tape · patearn", "".join(body), "seasonal-tape", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/seasonal-tape" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    """End-to-end: build a temp hermes.db, populate the snapshot via the real engine backfill,
    point the view at it, and assert the grid/ribbon/outlook/drill all render."""
    import os
    import tempfile
    import random
    from datetime import date
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.automation import seasonal_tape as ST

    global _DB_PATH
    tmp = os.path.join(tempfile.gettempdir(), "seasonal_view_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("CREATE TABLE index_rows(index_name TEXT, trade_date TEXT, close_value REAL);")
    rng = random.Random(5)
    # market (Nifty 500) + a sector with a planted festive (Oct/Nov) bump
    mlvl, slvl = 1000.0, 500.0
    for y in range(2001, 2026):
        for mo in range(1, 13):
            for dd in range(1, 21):
                try:
                    d = date(y, mo, dd)
                except ValueError:
                    continue
                if d.weekday() >= 5:
                    continue
                mr = rng.gauss(0.0004, 0.010)
                sr = 1.1 * mr + rng.gauss(0.0, 0.008) + (0.004 if mo in (10, 11) else 0.0)
                mlvl *= (1 + mr); slvl *= (1 + sr)
                con.execute("INSERT INTO index_rows VALUES (?,?,?)", ("Nifty 500", d.isoformat(), mlvl))
                con.execute("INSERT INTO index_rows VALUES (?,?,?)", ("Nifty Auto", d.isoformat(), slvl))
    con.commit(); con.close()
    ST.backfill(tmp, tmp, scope="all", limit=None)

    saved = _DB_PATH
    _DB_PATH = tmp
    _entities.cache_clear(); _compute.cache_clear()
    try:
        app = FastAPI(); app.include_router(router); c = TestClient(app)
        r = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto")
        assert r.status_code == 200 and "Seasonal tape" in r.text, r.status_code
        assert "25-year stack" in r.text, "month stack missing"
        assert "Monthly consolidation" in r.text, "month consolidation strip missing"
        assert "52-week stack" in r.text, "52-week stack missing"
        assert "Weekly consolidation" in r.text, "weekly consolidation strip missing"
        assert "Weekday" in r.text, "weekday strip missing"
        assert "Forward outlook" in r.text, "outlook missing"
        # monthly consolidation is now a ranked BAR chart: every month named + #rank + a best ★,
        # and value labels (so the reader never decodes a shade). Weekly carries week-number ticks.
        assert "★" in r.text, "best-month/week marker (★) missing from the consolidation panels"
        assert "#1 best" in r.text, "monthly consolidation missing the ranked #1-best label"
        assert "Bar height = the size of the move" in r.text, "month bars explainer missing"
        assert "W5" in r.text and "Week numbers" in r.text, "weekly consolidation week-number ticks missing"
        r2 = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto&drill=10")
        assert r2.status_code == 200 and "Behind the script" in r2.text, "drill missing"
        # ISO-week drill (D123): the 52-week stack's cell_link + the sibling wdrill= query param
        r2w = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto&wdrill=23")
        assert r2w.status_code == 200 and "Week 23" in r2w.text, "week drill missing"
        assert "wdrill=" in r.text, "52-week stack missing wdrill= cell links"
        assert "Click any week cell to break it down" in r.text, "week drill hint missing"
        r3 = c.get("/dash/seasonal-tape?scope=index&entity=Nifty 500&cal=cy")
        assert r3.status_code == 200, "index scope failed"
        # honest-empty path (unknown scope-entity still 200)
        r4 = c.get("/dash/seasonal-tape?scope=index&entity=DoesNotExist")
        assert r4.status_code == 200
        # scope=stock, no snapshot + no entity at all -> the search prompt, never ents[0]/3MINDIA
        r5 = c.get("/dash/seasonal-tape?scope=stock")
        assert r5.status_code == 200
        assert "st-search" in r5.text and "Search a symbol above" in r5.text, "no-entity search prompt missing"

        # D-seasonal-nav: sub-nav trio (all 3 links) renders on the tape page, in every scope
        for text in (r.text, r3.text, r5.text):
            assert ("🔍 Scan this month" in text and "📅 Seasonal tape" in text
                    and "⚖ Index divergence" in text), "seasonal sub-nav trio missing"
        # drill hint above the 25-year stack
        assert "Click any month cell below to break it down" in r.text, "drill hint missing"
        # index/sector -> constituent-scan CTA (the index->stocks drill)
        assert "Scan the stocks in Nifty Auto" in r.text and "scope=stock&index=Nifty" in r.text, \
            "sector -> constituent-scan CTA missing"
        assert "Scan the stocks in Nifty 500" in r3.text and "scope=stock&index=Nifty" in r3.text, \
            "index -> constituent-scan CTA missing"
        # stock-scope: the "...or scan every stock" discoverability link on the search prompt
        assert "…or scan every stock for this month" in r5.text, "stock-scope scan-all link missing"
        # scope=stock, an unresolvable query (no bhavcopy_rows table in this tmp DB -> the guarded
        # resolve raises internally and is caught) -> honest 'computed nothing', not a silent default
        r5b = c.get("/dash/seasonal-tape?scope=stock&entity=DOESNOTEXIST")
        assert r5b.status_code == 200
        assert "computed nothing" in r5b.text, "unresolvable stock query must show the honest prompt"
        assert "25-year stack" not in r5b.text, "must never silently render some other entity's data"

        # FIX-1 regression: with a (fake) persisted stock entity present, an unrelated unknown query
        # must still show the prompt, never silently fall back to that entity (the old ents[0] bug).
        con2 = sqlite3.connect(tmp)
        con2.execute(
            "INSERT OR REPLACE INTO seasonal_cells (scope,entity,axis,cell,script_z,n_years,hit_rate,"
            "conf,colored,signed,emp_p_block,emp_p_phase,null_p95,sign_stable,fdr_pass,mechanism,"
            "pledged_sign,gate_flags) VALUES ('stock','AAA','month',1,0.1,20,0.5,0.1,0,0,0.5,0.5,0.5,"
            "0,0,NULL,NULL,'OK')")
        con2.commit(); con2.close()
        _entities.cache_clear(); _compute.cache_clear()
        r5c = c.get("/dash/seasonal-tape?scope=stock&entity=ZZZNOPE")
        assert r5c.status_code == 200
        assert "computed nothing" in r5c.text
        assert "25-year stack" not in r5c.text, "unknown query must not silently default to AAA (ents[0])"
        # AAA itself: resolves (chip match) but has no seasonal_stack rows -> the specific
        # 'resolved but computed nothing' honest message, not a 500 and not a fabricated chart.
        r5d = c.get("/dash/seasonal-tape?scope=stock&entity=AAA")
        assert r5d.status_code == 200 and "st-search" in r5d.text
        assert "computed nothing" in r5d.text, "resolved-but-empty stock must say so honestly"

        # direct unit test of the 0-certified consensus path: st-empty, never heat_ribbon's 'no data'
        zero_cert_html = _consensus_panel({"cmap": {1: {"colored": False, "script_z": 0.1}}}, [1])
        assert "st-empty" in zero_cert_html and "honest finding" in zero_cert_html
        assert "no data" not in zero_cert_html, "0-certified consensus must never say literal 'no data'"
        one_cert_html = _consensus_panel(
            {"cmap": {1: {"colored": True, "script_z": 0.5, "conf": 0.8}}}, [1])
        assert "<svg" in one_cert_html and "st-empty" not in one_cert_html

        # seasonal_card: the reusable embed — non-empty for a covered sector, with the deep-link
        # + a ribbon (SVG); case-insensitive entity resolution.
        card = seasonal_card("sector", "nifty auto", db_path=tmp)
        assert card, "seasonal_card should render for a covered sector (case-insensitive)"
        assert "/dash/seasonal-tape?scope=sector" in card and "entity=Nifty%20Auto" in card, \
            "card missing the seasonal-tape deep-link"
        assert "<svg" in card, "card missing the month/week strips"
        # honest-empty: no stock snapshot at all in this tmp DB
        assert seasonal_card("stock", "DOESNOTEXIST", db_path=tmp) == "", \
            "seasonal_card should honest-empty for an uncovered stock"
        # DESCRIPTIVE-ONLY FENCE: the card must never leak the forward-outlook / traffic-light read
        for token in ("1M", "🟢", "🟡", "⚪", "Forward outlook"):
            assert token not in card, f"seasonal_card leaked a forward-outlook token: {token!r}"
        # NEW month-anchored journey: the card leads with a LABELLED monthly strip (every month
        # named) + a month-anchored weekly strip whose cells carry an approximate month/date hover.
        assert "Monthly rhythm" in card, "card should lead with the labelled Monthly rhythm strip"
        assert "Weekly detail" in card and "month-anchored" in card, \
            "card should carry the month-anchored Weekly detail strip"
        assert "Jan" in card and "Jul" in card and "Dec" in card, \
            "every calendar month must be labelled on the monthly strip"
        assert "≈" in card, "week cells must carry the approximate week->month hover mapping"
        # the week->month map + date range must actually resolve (July sits around ISO week 27)
        assert _WK_MONTH[27] == 7, f"ISO week 27 should map to July, got {_WK_MONTH[27]}"
        assert "Jun" in _week_daterange(27) or "Jul" in _week_daterange(27), \
            "week-27 date range should straddle late Jun / early Jul"

        # seasonal_full_panel: the INLINE embed must carry the COMPLETE analysis — every perspective
        # the full /dash/seasonal-tape page renders, not the reduced card. Assert each panel + fence.
        fp = seasonal_full_panel("sector", "nifty auto", db_path=tmp)
        assert fp, "seasonal_full_panel should render for a covered sector"
        for panel in ("25-year stack", "Monthly consolidation", "52-week stack",
                      "Weekly consolidation", "Weekday stack", "Weekday", "Forward outlook"):
            assert panel in fp, f"full panel missing the '{panel}' perspective"
        assert "Read this honestly" in fp, "full panel must carry the honesty fence"
        assert "Open the full seasonal tape" in fp and "/dash/seasonal-tape?scope=sector" in fp, \
            "full panel must deep-link to the full page for drill-downs/controls"
        # D124 in-place drill: embed cells reveal a PRE-RENDERED :target panel instead of navigating
        # to the lens. Assert the anchors + hidden panels are present, the close-link targets the
        # embed top, and the reused _drill_panel body ("Behind the script") is inlined.
        assert 'href="#sdrill-w' in fp and 'href="#sdrill-m' in fp and 'href="#sdrill-d' in fp, \
            "embed must link month/week/WEEKDAY cells to in-place #sdrill-* drill anchors"
        assert 'class="st-panel st-drill st-dtgt"' in fp and 'id="sdrill-w' in fp \
            and 'id="sdrill-d' in fp, \
            "embed must pre-render hidden :target week + weekday drill panels"
        assert 'id="stx-top"' in fp and 'href="#stx-top"' in fp, \
            "embed drill panels must offer a close link back to the embed top"
        assert "Behind the script" in fp, "embed drill must reuse the _drill_panel body verbatim"
        # the LENS keeps its server-rendered reload drill — it must NOT emit the inline anchors
        # (the CSS comment mentions #sdrill for docs, so assert on the actual <a href> only).
        assert 'href="#sdrill-' not in c.get(
            "/dash/seasonal-tape?scope=sector&entity=Nifty Auto").text, \
            "lens must keep the server-rendered drill (no inline #sdrill anchors)"
        # it is strictly RICHER than the compact card (which has no 25-year stack / weekday axis)
        assert "25-year stack" not in card and "Weekday" not in card, \
            "the compact card must stay compact (the full panel is the rich one)"
        assert seasonal_full_panel("stock", "DOESNOTEXIST", db_path=tmp) == "", \
            "seasonal_full_panel should honest-empty for an uncovered entity"
        # the route (dash_seasonal) still renders the same panels via the shared _panels_html
        rr = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto")
        for panel in ("25-year stack", "Monthly consolidation", "52-week stack",
                      "Weekday stack", "Weekday"):
            assert panel in rr.text, f"route regression: '{panel}' missing after _panels_html extraction"
        # weekday drill (ddrill=) — the lens renders the server-rendered year-by-year weekday panel
        rd = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto&ddrill=3")
        assert "Behind the script" in rd.text and "year by year" in rd.text, \
            "ddrill= must render the weekday year-by-year drill on the lens"
        # D126 placebo teaching block — the two-gate delta, tested DIRECTLY on _placebo_block so it is
        # deterministic (independent of the tiny synthetic temp DB). The canonical case is MARUTI Sep:
        # 89% up, clears the single-calendar placebo (p=0.5%), yet grey because it dies at the FDR.
        pb_fdr = _placebo_block({"script_z": 0.214, "emp_p_block": 0.005, "emp_p_phase": 0.005,
                                 "null_p95": 0.162, "n_years": 18, "hit_rate": 0.89, "colored": 0,
                                 "fdr_pass": 0, "gate_flags": "fdr-fail,no-mechanism"},
                                "month", "MARUTI", "Sep")
        assert "Why this reads" in pb_fdr and "1 of 12 months" in pb_fdr and "still grey" in pb_fdr, \
            "an FDR-fail cell must teach 'strong in isolation is not surviving the look-elsewhere'"
        pb_noise = _placebo_block({"script_z": 0.05, "emp_p_block": 0.42, "emp_p_phase": 0.38,
                                   "null_p95": 0.20, "n_years": 18, "hit_rate": 0.55, "colored": 0,
                                   "fdr_pass": 0, "gate_flags": "null-inside-band"}, "month", "ACME", "Feb")
        assert "inside what pure chance" in pb_noise, "an inside-chance cell must say so plainly"
        pb_cert = _placebo_block({"script_z": 0.6, "emp_p_block": 0.001, "emp_p_phase": 0.002,
                                  "null_p95": 0.30, "n_years": 20, "hit_rate": 0.85, "colored": 1,
                                  "fdr_pass": 1, "gate_flags": ""}, "month", "ACME", "Mar")
        assert "certified" in pb_cert and "never a standalone trade" in pb_cert, \
            "a certified cell must still carry the descriptive fence"
        assert _placebo_block({"script_z": 0.2, "emp_p_block": None, "emp_p_phase": None},
                              "month", "X", "Jan") == "", "no placebo stats -> render nothing, never fabricate"

        print("seasonal_view selftest OK — stack + consensus + outlook + drill + weekly/weekday "
              "strips + events section render; stock search box + FIX-1 no-default-entity + FIX-2 "
              "in-memory on-demand resolve wired; 0-certified consensus st-empties honestly; "
              "seasonal_card embeds + honest-empties + fences the forward outlook; sub-nav trio + "
              "drill hint + index/sector->constituent-scan CTA + stock scan-all link wired; "
              "ISO-week cell drill-down (wdrill=) + 52-week stack cell_link wired (D123); "
              "in-place embed cell drill via :target #sdrill-* panels, lens keeps reload drill (D124); "
              "weekday stack (5-col x N-year) + weekday drill (ddrill=/#sdrill-d) wired (D125); "
              "placebo 'why grey' teaching block in every drill — single-calendar placebo + "
              "multiple-cell FDR, the strong-in-isolation-vs-survives-looking delta (D126)")
    finally:
        _DB_PATH = saved
        _entities.cache_clear(); _compute.cache_clear()
        if os.path.exists(tmp):
            os.remove(tmp)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
