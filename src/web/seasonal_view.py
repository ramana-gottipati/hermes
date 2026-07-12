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
        cells = con.execute(
            "SELECT cell, script_z, n_years, hit_rate, conf, colored, signed, mechanism, "
            "pledged_sign, gate_flags, emp_p_block, emp_p_phase FROM seasonal_cells "
            "WHERE scope=? AND entity=? AND axis='month'", (scope, entity)).fetchall()
        outlook = con.execute(
            "SELECT cell, k, n, ci_lo, ci_hi, base_rate, edge, fail_avg, fail_worst, light, mechanism "
            "FROM seasonal_outlook WHERE scope=? AND entity=? AND axis='month' ORDER BY cell",
            (scope, entity)).fetchall()
    finally:
        con.close()
    if not stack:
        return None
    years = sorted({r["year"] for r in stack})
    smap = {(r["cell"], r["year"]): r["mean_z"] for r in stack}
    cmap = {r["cell"]: dict(r) for r in cells}
    omap = {r["cell"]: dict(r) for r in outlook}
    return {"years": years, "smap": smap, "cmap": cmap, "omap": omap}


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
    return (
        _CARD_CSS
        + '<div class="sc-card">' + heading_html
        + f'<div class="sc-bl">{bl}</div>'
        + ifx.heat_ribbon(_consensus_ribbon_cells(d, _FISCAL_ORDER), w=560, h=34)
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
        if not ents:
            raise LookupError("no snapshot")
        if scope == "stock":
            # ~500-symbol universe — case-insensitive resolve (deep-links from the stock card use
            # the upper-cased symbol already, but never trust the caller's casing).
            entity = {e.upper(): e for e in ents}.get((entity or "").strip().upper()) or ents[0]
        elif entity not in ents:
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
            # ~500-symbol universe — never render the full chip row; show only the current entity
            # (reached via a deep-link from the stock's own seasonal card) + a count note.
            ent_chips = (f'<a class="on" href="/dash/seasonal-tape?scope=stock&entity={_esc(entity)}'
                        f'&cal={cal}">{_esc(entity)}</a>'
                        f'<span class="st-chip" style="margin-left:8px">{len(ents)} stocks covered — '
                        'reach one from its own /dash/stock page (Seasonal tab)</span>')
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

        # consensus ribbon: t = sign(script_z)*conf, colored cells only (paleness = 1-emp_p)
        ribbon_cells = _consensus_ribbon_cells(d, order)
        body.append(
            '<div class="st-panel"><div class="st-h">Consensus script '
            '<small>— hue = direction, paleness = uncertainty; only certified months are drawn</small></div>'
            + ifx.plain('The clubbed read across all years. <b>Green</b> = reliably hot, <b>red</b> = '
                        'reliably cold; the <b>paler</b> the bar, the less certain. A gap = that month did '
                        'not survive certification (most months don\'t).')
            + ifx.heat_ribbon(ribbon_cells, w=1060, h=42, vmax=1.0)
            + '</div>')

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
        assert "25-year stack" in r.text and "Consensus script" in r.text, "panels missing"
        assert "Forward outlook" in r.text, "outlook missing"
        r2 = c.get("/dash/seasonal-tape?scope=sector&entity=Nifty Auto&drill=10")
        assert r2.status_code == 200 and "Behind the script" in r2.text, "drill missing"
        r3 = c.get("/dash/seasonal-tape?scope=index&entity=Nifty 500&cal=cy")
        assert r3.status_code == 200, "index scope failed"
        # honest-empty path (unknown scope-entity still 200)
        r4 = c.get("/dash/seasonal-tape?scope=index&entity=DoesNotExist")
        assert r4.status_code == 200
        # scope=stock is now whitelisted (no snapshot in this tmp DB -> honest empty-state page)
        r5 = c.get("/dash/seasonal-tape?scope=stock&entity=DOESNOTEXIST")
        assert r5.status_code == 200

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

        print("seasonal_view selftest OK — stack + consensus + outlook + drill render; stock scope "
              "wired; seasonal_card embeds + honest-empties + fences the forward outlook")
    finally:
        _DB_PATH = saved
        _entities.cache_clear(); _compute.cache_clear()
        if os.path.exists(tmp):
            os.remove(tmp)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
