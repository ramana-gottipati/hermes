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
calendar context, never a ranking or a trade. Route: /dash/seasonal-tape [?scope=index|sector&entity=..&cal=fy|cy&drill=<cell>].
"""
from __future__ import annotations

import sqlite3
import statistics
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
.st-dlist{display:flex;flex-direction:column;gap:5px;margin-top:6px;max-width:560px;}
.st-drow{display:flex;align-items:center;gap:10px;font-size:12.5px;}
.st-drow .k{width:56px;color:var(--accent);font-weight:600;}
.st-dbar{flex:1;height:14px;background:var(--bg-3);border-radius:7px;overflow:hidden;position:relative;}
.st-dbar i{display:block;height:100%;opacity:.78;position:absolute;top:0;}
.st-drow .v{width:64px;text-align:right;color:var(--ink);font-variant-numeric:tabular-nums;}
.st-chip{font-size:11px;color:var(--ink-3);}
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
</style>
"""


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
        cells = con.execute(
            "SELECT cell, script_z, n_years, hit_rate, conf, colored, signed, mechanism, "
            "pledged_sign, gate_flags, emp_p_block, emp_p_phase FROM seasonal_cells "
            "WHERE scope=? AND entity=? AND axis='month'", (scope, entity)).fetchall()
        outlook = con.execute(
            "SELECT cell, k, n, ci_lo, ci_hi, base_rate, edge, fail_avg, fail_worst, light, mechanism "
            "FROM seasonal_outlook WHERE scope=? AND entity=? AND axis='month' ORDER BY cell",
            (scope, entity)).fetchall()
        try:
            wk_rows = con.execute(
                "SELECT cell, script_z, n_years, conf, colored, mechanism, gate_flags FROM seasonal_cells "
                "WHERE scope=? AND entity=? AND axis='iso_week'", (scope, entity)).fetchall()
        except Exception:  # noqa: BLE001 — older snapshot without this axis populated -> {}
            wk_rows = []
        try:
            wd_rows = con.execute(
                "SELECT cell, script_z, n_years, conf, colored, mechanism, gate_flags FROM seasonal_cells "
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
    cmap = {r["cell"]: dict(r) for r in cells}
    omap = {r["cell"]: dict(r) for r in outlook}
    wcmap = {r["cell"]: dict(r) for r in wk_rows}
    dcmap = {r["cell"]: dict(r) for r in wd_rows}
    return {"years": years, "smap": smap, "cmap": cmap, "omap": omap, "wcmap": wcmap, "dcmap": dcmap,
            "wsmap": wsmap, "wsyears": wsyears}


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
                 vmax: float | None = None) -> str:
    """A DESCRIPTIVE (dimmed) heat-ribbon strip for a secondary axis (month/weekly/weekday) — shows
    the raw script_z shape for every populated cell (NOT certified-only, unlike the strict
    certification gate). st-empty (never heat_ribbon's literal 'no data') when nothing is populated
    yet. `vmax` tightens the signed scale (default None = heat_ribbon's own max|value| autoscale) —
    consolidation strips summarize small residuals (~±0.3σ) that a wide ±2.5σ stack scale would wash
    out, so callers pass a tighter vmax (e.g. 0.5) to keep the green/red gradient visible."""
    cells, n_cert, n_desc = _axis_strip_cells(cmap, order, label_fn)
    if n_desc == 0:
        body = (f'<div class="st-empty">No {_esc(unit)} populated for this entity yet — '
               'not hidden, just not computed/covered.</div>')
    else:
        body = (f'<div class="st-strip--desc">{ifx.heat_ribbon(cells, w=w, h=h, vmax=vmax, title_at=title_at)}</div>'
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
            '<b>An empty script is the honest finding, not missing data.</b></div>')
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
    omap = {c: {"k": k, "n": n, "ci_lo": lo, "ci_hi": hi, "base_rate": br, "edge": ed,
                "fail_avg": fa, "fail_worst": fw, "light": lt, "mechanism": mech}
            for (_sc, _asof, _ax, c, _hz, k, n, lo, hi, br, ed, fa, fw, lt, mech) in outlook}
    return {"years": years, "smap": smap, "cmap": cmap, "wcmap": wcmap, "dcmap": dcmap, "omap": omap}


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
    week_cells, _wk_cert, wk_desc = _axis_strip_cells(
        d.get("wcmap", {}), list(range(1, 54)), lambda c: f"W{c}")
    weekly_html = (
        '<div class="sc-note" style="margin-top:6px">Weekly shape (ISO week 1–53, descriptive):</div>'
        + ifx.heat_ribbon(week_cells, w=560, h=26)
    ) if wk_desc else ''
    return (
        _CARD_CSS
        + '<div class="sc-card">' + heading_html
        + f'<div class="sc-bl">{bl}</div>'
        + ifx.heat_ribbon(_consensus_ribbon_cells(d, _FISCAL_ORDER), w=560, h=34)
        + weekly_html
        + f'<div class="sc-note">{len(certified)} of 12 months certified; the rest '
          'indistinguishable from chance.</div>'
        + f'<div class="sc-fence"><ul>{caveats}</ul><b>Descriptive calendar context, never a signal.</b></div>'
        + f'<div><a href="{_esc(link)}">Open the full seasonal tape →</a></div>'
        + '</div>')


def _drill_panel(scope: str, entity: str, d: dict, month: int, order: list) -> str:
    """Server-rendered breakdown for one month cell: the per-year z values behind the script."""
    label = _MONTH_ABBR.get(month, str(month))
    yrs = d["years"]
    vals = [(y, d["smap"].get((month, y))) for y in yrs if d["smap"].get((month, y)) is not None]
    cell = d["cmap"].get(month, {})
    back = f'/dash/seasonal-tape?scope={_esc(scope)}&entity={_esc(entity)}'
    if not vals:
        return (f'<div class="st-panel st-drill"><div class="st-h">No {label} history</div>'
                f'<div><a href="{back}">← back to the tape</a></div></div>')
    vmax = max(abs(v) for _y, v in vals) or 1.0
    rows = ""
    for y, v in sorted(vals, key=lambda t: t[0], reverse=True):
        w = min(50, abs(v) / vmax * 50)
        left = 50 if v >= 0 else 50 - w
        col = "var(--up)" if v >= 0 else "var(--down)"
        rows += (f'<div class="st-drow"><span class="k">{y}</span>'
                 f'<span class="st-dbar"><i style="left:{left:.0f}%;width:{w:.0f}%;background:{col}"></i></span>'
                 f'<span class="v">{v:+.2f}σ</span></div>')
    sz = cell.get("script_z")
    verdict = "certified" if cell.get("colored") else "reported, not gated"
    mech = cell.get("mechanism") or "—"
    flags = cell.get("gate_flags") or ""
    hd = (f'{_esc(entity)} · {label} <small>— script {sz:+.2f}σ over {len(vals)} years, '
          f'{verdict}</small>') if sz is not None else f'{_esc(entity)} · {label}'
    return (
        '<div class="st-panel st-drill" id="drill">'
        f'<div class="st-h">Behind the script · {hd}</div>'
        + ifx.plain('The consensus shows the <b>average</b> year. Here is <b>every</b> year\'s ' + label
                    + ' residual, newest first — the dispersion the single number hides. A run of '
                    'similar bars = a real tendency; one or two outliers carrying it = not one.')
        + f'<div class="st-dlist">{rows}</div>'
        + f'<div class="st-chip" style="margin-top:8px">mechanism: {_esc(mech)} · gates: {_esc(flags)}</div>'
        + f'<div style="margin-top:8px"><a href="{back}">← back to the tape</a></div></div>')


@router.get("/dash/seasonal-tape", response_class=HTMLResponse)
def dash_seasonal(scope: str = "index", entity: str = "", cal: str = "fy", drill: str = "") -> HTMLResponse:
    scope = scope if scope in ("index", "sector", "stock") else "index"
    order = _CAL_ORDER if cal == "cy" else _FISCAL_ORDER
    body = [_CSS, ifx.readability_css()]
    try:
        ents = _entities(scope, _DB_PATH)
        if not ents and scope != "stock":
            raise LookupError("no snapshot")

        def _stock_early_return(msg_html: str, q_val: str) -> HTMLResponse:
            eb = ['<h2 style="margin:0 0 2px">Seasonal tape '
                 '<small style="color:var(--ink-3);font-size:12px;font-weight:400">stock — search</small>'
                 '</h2>', _stock_search_box(q_val, cal, ents), f'<div class="st-prompt">{msg_html}</div>']
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

        col_labels = [_MONTH_ABBR[m] for m in order]
        yrs_desc = sorted(d["years"], reverse=True)
        matrix = [[d["smap"].get((m, y)) for m in order] for y in yrs_desc]
        body.append(
            '<div class="st-panel"><div class="st-h">25-year stack '
            '<small>— each cell = that year\'s residual for that month, in σ</small></div>'
            + ifx.plain('Each <b>row</b> is a year (newest on top), each <b>column</b> a month. '
                        '<b>Green</b> = the month ran <b>above</b> this entity\'s own baseline that year, '
                        '<b>red</b> below; a <b>blank</b> cell = too few observations. Read <b>down a '
                        'column</b> to judge whether a month is a real tendency or just 2–3 loud years. '
                        '<b>Click a column\'s cell</b> to break the month down year-by-year.')
            + ifx.heat_grid([str(y) for y in yrs_desc], col_labels, matrix, w=1060, cell_h=22,
                            row_w=64, signed=True, fmt=1, unit="σ", vmin=-2.5, vmax=2.5,
                            cell_link=lambda i, j: (f'/dash/seasonal-tape?scope={scope}&entity={_esc(entity)}'
                                                    f'&cal={cal}&drill={order[j]}#drill'))
            + '</div>')

        # month consolidation: the descriptive gradient companion to the stack above — EVERY month
        # with enough history gets a bar (not certified-only), the symmetric twin of the week/weekday
        # consolidation strips below (Ramana D122: months + weeks both get stack-then-gradient).
        body.append(_strip_panel(
            "Monthly consolidation", "— the 25-year clubbed gradient: each month's average residual "
            "(green above baseline, red below; paler = less certain)",
            "Every month with enough history gets a bar here, whether or not it separately survives "
            "full certification — a populated bar is descriptive, not a claim. See the bottom-line "
            "summary above for exactly which month(s), if any, clear the full gate.",
            d["cmap"], order, lambda m: _MONTH_ABBR[m], w=1060, h=44, unit="months", vmax=0.5))

        # 52-week stack: the per-year ISO-week mirror of the month stack above (symmetry: weeks get a
        # full stack too, not just a thin strip).
        wsyears_desc = sorted(d.get("wsyears", []), reverse=True)
        week_cols = list(range(1, 54))
        week_w = 50 + len(week_cols) * 20
        if wsyears_desc:
            week_col_labels = [f"W{w}" if w % 4 == 1 else "" for w in week_cols]
            week_matrix = [[d.get("wsmap", {}).get((w, y)) for w in week_cols] for y in wsyears_desc]
            week_grid = ifx.heat_grid([str(y) for y in wsyears_desc], week_col_labels, week_matrix,
                                      w=week_w, cell_h=20, row_w=50, signed=True, fmt=1, unit="σ",
                                      vmin=-2.5, vmax=2.5)
            week_stack_body = f'<div style="overflow-x:auto"><div style="width:{week_w}px">{week_grid}</div></div>'
        else:
            week_stack_body = ('<div class="st-empty">No 52-week stack populated for this entity yet — '
                               'not hidden, just not computed/covered.</div>')
        body.append(
            '<div class="st-panel"><div class="st-h">52-week stack '
            '<small>— each cell = that year\'s residual for that ISO week, in σ</small></div>'
            + ifx.plain('Same idea as the month stack, one column per ISO calendar week. Wide — '
                        'scroll sideways. Read down a column to judge a real weekly tendency vs a '
                        'couple of loud years.')
            + week_stack_body + '</div>')

        # weekly + weekday consolidation strips (descriptive shape, secondary axes of the SAME
        # certification bar as months)
        body.append(_strip_panel(
            "Weekly consolidation", "— the 25-year clubbed gradient across ISO weeks 1–53",
            "Same idea as the 52-week stack above, clubbed into one gradient — a populated bar is "
            "this week\'s descriptive average residual, not a certified signal unless separately gated.",
            d.get("wcmap", {}), list(range(1, 54)), lambda c: str(c), w=1060, h=40, unit="weeks",
            vmax=0.5))
        body.append(_strip_panel(
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
                body.append(ev_section)
        except Exception:  # noqa: BLE001 — the events lens must never break this page
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
            body.append(
                '<div class="st-panel"><div class="st-h">Forward outlook '
                '<small>— base-rate only; a ⚪ light means the interval touches 50% = noise</small></div>'
                + ifx.plain('For each month: how often it has been positive, with a 95% confidence band. '
                            '🟢 = reliably positive with a mechanism, 🟡 = leans one way, <b>⚪ = the band '
                            'includes a coin-flip, so treat it as noise</b>. This is history\'s base rate, '
                            '<b>not</b> a forecast or a trade.')
                + f'<div class="st-ol">{cards}</div></div>')

        if drill:
            try:
                m = int(drill)
                if m in _CAL_ORDER:
                    body.append(f'<div id="drill"></div>{_drill_panel(scope, entity, d, m, order)}')
            except ValueError:
                pass

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
        body.append(
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
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Seasonal tape</h2><div class="st-note">The seasonal snapshot '
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
        r2 = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto&drill=10")
        assert r2.status_code == 200 and "Behind the script" in r2.text, "drill missing"
        r3 = c.get("/dash/seasonal-tape?scope=index&entity=Nifty 500&cal=cy")
        assert r3.status_code == 200, "index scope failed"
        # honest-empty path (unknown scope-entity still 200)
        r4 = c.get("/dash/seasonal-tape?scope=index&entity=DoesNotExist")
        assert r4.status_code == 200
        # scope=stock, no snapshot + no entity at all -> the search prompt, never ents[0]/3MINDIA
        r5 = c.get("/dash/seasonal-tape?scope=stock")
        assert r5.status_code == 200
        assert "st-search" in r5.text and "Search a symbol above" in r5.text, "no-entity search prompt missing"
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
        assert "<svg" in card, "card missing the consensus ribbon"
        # honest-empty: no stock snapshot at all in this tmp DB
        assert seasonal_card("stock", "DOESNOTEXIST", db_path=tmp) == "", \
            "seasonal_card should honest-empty for an uncovered stock"
        # DESCRIPTIVE-ONLY FENCE: the card must never leak the forward-outlook / traffic-light read
        for token in ("1M", "🟢", "🟡", "⚪", "Forward outlook"):
            assert token not in card, f"seasonal_card leaked a forward-outlook token: {token!r}"
        # the new Weekly strip is additive to the card and must not reintroduce the fenced tokens
        assert "Weekly shape" in card, "seasonal_card should carry the new descriptive Weekly strip"

        print("seasonal_view selftest OK — stack + consensus + outlook + drill + weekly/weekday "
              "strips + events section render; stock search box + FIX-1 no-default-entity + FIX-2 "
              "in-memory on-demand resolve wired; 0-certified consensus st-empties honestly; "
              "seasonal_card embeds + honest-empties + fences the forward outlook")
    finally:
        _DB_PATH = saved
        _entities.cache_clear(); _compute.cache_clear()
        if os.path.exists(tmp):
            os.remove(tmp)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
