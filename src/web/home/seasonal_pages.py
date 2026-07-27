"""src/web/home/seasonal_pages.py — the Graphite "Seasonal" page (lane W2-C).

ONE page, four views, replacing the classic four-lens `_subnav()` family:

    /dash/home/seasonal?view=tape        ← /dash/seasonal-tape
                        ?view=screen     ← /dash/seasonal-screen
                        ?view=divergence ← /dash/seasonal-divergence
                        ?view=calendar   ← /dash/seasonal-calendar

The four were always one subject wearing four hats (they already shared a sub-nav strip); in
Graphite they are one page with a view selector, so the reader stops losing the thread between
"the script", "this month", "two indices" and "expiry/holiday".

🔴 THE FENCE TRAVELS WITH THE DATA. This estate's calendar-seasonality work is largely
**0-CERTIFIED — and that null result IS the finding.** A cell colours ONLY when it clears the full
certification stack (placebo nulls · family-wide FDR · N≥15 years · out-of-sample sign stability ·
a pledged mechanism); nearly none do. Nothing here is tradeable net of costs, nothing is a ranking
of what to buy, and the grey majority is published on purpose. Everything is read from the bounded
nightly snapshot tables — this module NEVER imports or edits `src/automation/seasonal_tape.py`
(its `__doc__` is part of `frozen_family_hash()`; editing it breaks a pre-registration seal).
"""
from __future__ import annotations

import datetime as _dt

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import shell
from src.web.home import w2_kit as K
from src.web.home import w2_reads as W

router = APIRouter()

PATH = "/dash/home/seasonal"
VIEWS = (("tape", "The script"), ("screen", "This month"),
         ("divergence", "Two indices"), ("calendar", "Expiry & holidays"))

_FENCE = ("Calendar seasonality, described from 25 years of point-in-time residuals. Nearly every "
          "cell fails certification — that null result is the finding, not a gap. Descriptive "
          "context only: never a signal, a ranking of what to buy, or advice.")

_SCOPES = (("index", "Indices"), ("sector", "Sectors"))
_CAL_VIEWS = (("pre_holiday_ret_delta", "Pre-holiday"), ("post_holiday_ret_delta", "Post-holiday"),
              ("expiry_ret_delta", "Expiry day"), ("expiry_week_ret_delta", "Expiry week"))


def _pick(live, demo):
    return (live, False) if live else (demo, True)


# ── view: the script (the classic Seasonal tape) ────────────────────────────────
def _cell_grid(cmap: dict, order, label_fn, *, scope: str, entity: str, axis: str,
               sel: int = None) -> str:
    if not cmap:
        return C.empty("No cells on this axis yet.")
    out = ['<div class="w2-grid">']
    for k in order:
        r = cmap.get(k)
        if not r:
            out.append('<div class="w2-cell"><span class="k">%s</span>'
                       '<span class="v">—</span></div>' % K.esc(label_fn(k)))
            continue
        cert = bool(r.get("colored"))
        z = r.get("script_z")
        hr = r.get("hit_rate")
        cls = "w2-cell" + (" cert" if cert else "") + (" sel" if sel == k else "")
        hit = ("%.0f%% of years" % (float(hr) * 100)) if hr is not None else "—"
        out.append('<a class="%s" href="%s" title="%s">'
                   '<span class="k">%s</span><span class="v">%s</span><span class="h">%s</span></a>'
                   % (cls,
                      K.href(PATH, view="tape", scope=scope, entity=entity, axis=axis, cell=k),
                      K.esc("%s · %s years%s" % (label_fn(k), r.get("n_years") or "—",
                                                 " · certified" if cert else " · reported, not certified")),
                      K.esc(label_fn(k)), K.num(z, 2), K.esc(hit)))
    out.append("</div>")
    return "".join(out)


def _year_stack(rows) -> str:
    if not rows:
        return C.empty("No per-year history behind this cell yet.")
    vals = [r.get("mean_z") for r in rows if r.get("mean_z") is not None]
    if not vals:
        return C.empty("No per-year history behind this cell yet.")
    mx = max(abs(float(v)) for v in vals) or 1.0
    out = []
    for r in rows:
        v = r.get("mean_z")
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        out.append(K.bar_row(str(r.get("year") or "—"), K.signed(f, 2),
                             abs(f) / mx * 100.0, cls=("neg" if f < 0 else "")))
    pos = sum(1 for v in vals if float(v) > 0)
    return (K.box("".join(out))
            + K.note("<b>%d of %d years</b> ran positive in this cell. A script that only holds in "
                     "a bare majority of years is exactly what an uncertified cell looks like."
                     % (pos, len(vals))))


def _tape(conn, q) -> str:
    scope = q.get("scope", "index")
    if scope not in dict(_SCOPES):
        scope = "index"
    ents = W.seasonal_entities(conn, scope)
    entity = q.get("entity", "") or (ents[0] if ents else "")
    script, demo = _pick(W.seasonal_script(conn, scope, entity) if entity else {}, W.DEMO_SCRIPT)
    if demo:
        entity = entity or "Nifty 500"
    n_col, n_all = W.seasonal_certified_count(script)

    scope_chips = '<div class="w2-chips">' + "".join(
        '<a class="%s" href="%s">%s</a>' % ("on" if k == scope else "",
                                            K.href(PATH, view="tape", scope=k), K.esc(lab))
        for k, lab in _SCOPES) + "</div>"
    ent_chips = ""
    if ents:
        ent_chips = '<div class="w2-chips">' + "".join(
            '<a class="%s" href="%s">%s</a>' % ("on" if e == entity else "",
                                                K.href(PATH, view="tape", scope=scope, entity=e), K.esc(e))
            for e in ents[:14]) + "</div>"

    verdict = ("<b>%d of %d</b> cells cleared certification." % (n_col, n_all)) if n_all else ""
    body = [K.head_block(
        "The seasonal script — %s" % K.esc(entity or "—"),
        "For each calendar slot, how this name's <b>own</b> residual behaved once the market move "
        "was stripped out, across 25 years. %s A coloured cell is one that survived placebo nulls, "
        "family-wide false-discovery control, a 15-year minimum, out-of-sample sign stability and a "
        "pledged mechanism. <b>Nearly none do — that is the result.</b>" % verdict,
        "seasonal_cells · nightly snapshot", sample=demo)]
    body.append(scope_chips + ent_chips)

    axis = q.get("axis", "month")
    if axis not in ("month", "week", "weekday"):
        axis = "month"
    try:
        sel = int(q.get("cell", "") or 0) or None
    except (TypeError, ValueError):
        sel = None

    body.append('<h3 class="w2-sect">By month</h3>')
    body.append(_cell_grid(script.get("month") or {}, W.CAL_ORDER,
                           lambda m: W.MONTH_ABBR.get(m, str(m)),
                           scope=scope, entity=entity, axis="month",
                           sel=(sel if axis == "month" else None)))
    body.append('<h3 class="w2-sect">By weekday</h3>')
    body.append(_cell_grid(script.get("weekday") or {}, tuple(range(5)),
                           lambda w: W.WEEKDAY_ABBR.get(w, str(w)),
                           scope=scope, entity=entity, axis="weekday",
                           sel=(sel if axis == "weekday" else None)))
    wk = script.get("week") or {}
    if wk:
        body.append('<h3 class="w2-sect">By week of the year</h3>')
        body.append(_cell_grid(wk, tuple(sorted(wk.keys())), lambda w: "W%d" % w,
                               scope=scope, entity=entity, axis="week",
                               sel=(sel if axis == "week" else None)))
    body.append('<div class="w2-legend"><span><b>Number</b> = the residual score for that slot '
                '(0 means "no different from an average slot").</span>'
                '<span><b>Coloured</b> = certified · <b>grey</b> = reported, not certified.</span></div>')

    if sel:
        label = ("W%d" % sel if axis == "week"
                 else (W.MONTH_ABBR.get(sel, str(sel)) if axis == "month"
                       else W.WEEKDAY_ABBR.get(sel, str(sel))))
        body.append('<h3 class="w2-sect">Behind the script — %s, year by year</h3>' % K.esc(label))
        body.append(_year_stack(W.seasonal_year_stack(conn, scope, entity, axis, sel) if not demo else []))
    else:
        body.append(C.learn("Click any slot above to see the year-by-year record behind it — the "
                            "single most useful check, because a 'strong' slot usually turns out to "
                            "be a handful of loud years and a lot of noise."))

    outlook = W.seasonal_outlook(conn, scope, entity) if not demo else []
    if outlook:
        rows = "".join(
            '<tr><td class="l">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
            % (K.esc(W.MONTH_ABBR.get(int(o.get("cell") or 0), o.get("cell"))),
               K.esc(o.get("horizon") or "—"),
               K.num((o.get("base_rate") or 0) * 100, 0) + "%",
               "%s–%s" % (K.num((o.get("ci_lo") or 0) * 100, 0), K.num((o.get("ci_hi") or 0) * 100, 0)),
               '<span class="w2-pill%s">%s</span>'
               % (" warn" if (o.get("light") or "") == "white" else "",
                  K.esc((o.get("light") or "—").upper())))
            for o in outlook[:12])
        body.append('<h3 class="w2-sect">Forward outlook — with its confidence band</h3>')
        body.append(C.pro_more(
            K.table(("Slot", "Horizon", "Base rate", "95% band", "Read"), rows)
            + K.note("A <b>WHITE</b> read means the confidence band touches the 50% coin-flip line — "
                     "explicitly noise. Most rows are white, and that is the honest state of "
                     "calendar seasonality.")))
        body.append(C.pro_teaser(
            K.table(("Slot", "Horizon", "Base rate", "95% band", "Read"), rows),
            cta_sub="The forward band per slot — including how often it is indistinguishable from a coin flip",
            advertise=True))

    meta = W.seasonal_meta(conn)
    if meta:
        fam = meta.get("frozen_family_sha256") or ""
        if fam:
            body.append(K.note("Pre-registered: the whole cell family was sha256-fingerprinted "
                               "<b>before</b> it was computed (<code>%s…</code>), so the rules could "
                               "not be tuned after seeing the answer." % K.esc(str(fam)[:16])))
    return "".join(body)


# ── view: this month (the classic This-month screen) ────────────────────────────
def _screen(conn, q) -> str:
    try:
        month = int(q.get("month", "") or _dt.date.today().month)
    except (TypeError, ValueError):
        month = _dt.date.today().month
    month = month if 1 <= month <= 12 else _dt.date.today().month
    lean = "cold" if q.get("lean") == "cold" else "hot"
    scope = q.get("scope", "index")
    if scope not in dict(_SCOPES):
        scope = "index"
    rows, demo = _pick(W.seasonal_month_screen(conn, month, scope=scope, lean=lean), W.DEMO_SCREEN)

    chips = '<div class="w2-chips">' + "".join(
        '<a class="%s" href="%s">%s</a>' % ("on" if m == month else "",
                                            K.href(PATH, view="screen", month=m, lean=lean, scope=scope),
                                            K.esc(W.MONTH_ABBR[m])) for m in W.CAL_ORDER) + "</div>"
    lean_chips = '<div class="w2-chips">' + "".join(
        '<a class="%s" href="%s">%s</a>' % ("on" if k == lean else "",
                                            K.href(PATH, view="screen", month=month, lean=k, scope=scope),
                                            K.esc(lab))
        for k, lab in (("hot", "Historically warmer"), ("cold", "Historically cooler"))) + "</div>"

    trs = []
    for i, r in enumerate(rows, 1):
        lo, hi = r.get("ci_lo"), r.get("ci_hi")
        band = ("%.0f–%.0f%%" % (lo * 100, hi * 100)) if (lo is not None and hi is not None) else "—"
        flag = ('<span class="w2-pill warn">indistinguishable from chance</span>'
                if r.get("indistinct") else '<span class="w2-pill on">outside the coin-flip band</span>')
        trs.append('<tr><td class="l">%d. %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>'
                   '<td class="l">%s</td></tr>'
                   % (i, K.esc(r.get("entity") or "—"),
                      K.num((r.get("hit_rate") or 0) * 100, 0) + "%",
                      K.esc(band), K.esc(r.get("n_years") or "—"),
                      K.signed(r.get("script_z"), 2), flag))

    return (K.head_block(
        "%s — what the record says" % W.MONTH_ABBR.get(month, "This month"),
        "Every name's <b>%s</b> record, ranked by the <b>lower</b> edge of its 95%% confidence band "
        "rather than the raw hit-rate — because a raw percentage rewards tiny samples (a lucky 3-of-3 "
        "would outrank a proven 30-of-32). The band is the point of the page: on most rows it "
        "straddles 50%%, meaning the record is <b>indistinguishable from a coin flip</b>."
        % K.esc(W.MONTH_ABBR.get(month, "this month")),
        "seasonal_cells · nightly snapshot", sample=demo)
        + chips + lean_chips
        + K.table(("Name", "Rose in", "95% band", "Years", "Residual", "Read"), "".join(trs), tall=True)
        + K.note('<a href="%s">Download this table as CSV →</a>'
                 % K.href(PATH, view="screen", month=month, lean=lean, scope=scope, format="csv"))
        + C.fence("Ranked for readability, NOT certified and NOT tradeable. Ordering a descriptive "
                  "base-rate does not turn it into a signal — the confidence band beside each row is "
                  "what you should actually read.")
        + C.learn("“Rose in 62% of years” sounds strong until you read the band beside it. If that "
                  "band includes 50%, the honest translation is: over this sample, we cannot tell "
                  "this apart from chance."))


# ── view: two indices (the classic Index divergence) ────────────────────────────
def _divergence(conn, q) -> str:
    ents = W.seasonal_entities(conn, "index")
    a = q.get("a", "") or (ents[0] if ents else "Nifty 50")
    b = q.get("b", "") or (ents[1] if len(ents) > 1 else "Nifty Midcap 100")
    rows = W.seasonal_divergence(conn, a, b)
    demo = not rows
    if demo:
        rows = [{"cell": m, "a": W.DEMO_SCRIPT["month"].get(m), "b": None,
                 "gap": (W.DEMO_SCRIPT["month"].get(m) or {}).get("script_z")} for m in W.CAL_ORDER]

    pick = ""
    if ents:
        pick = ('<div class="w2-chips">' + "".join(
            '<a class="%s" href="%s">%s</a>' % ("on" if e == a else "",
                                                K.href(PATH, view="divergence", a=e, b=b), K.esc(e))
            for e in ents[:8]) + "</div>"
            + '<div class="w2-chips">' + "".join(
            '<a class="%s" href="%s">%s</a>' % ("on" if e == b else "",
                                                K.href(PATH, view="divergence", a=a, b=e), K.esc(e))
            for e in ents[:8]) + "</div>")

    trs = []
    for r in rows:
        ra, rb = r.get("a") or {}, r.get("b") or {}
        trs.append('<tr><td class="l">%s</td><td>%s</td><td>%s</td><td>%s</td>'
                   '<td>%s</td><td>%s</td></tr>'
                   % (K.esc(W.MONTH_ABBR.get(r["cell"], r["cell"])),
                      K.num(ra.get("script_z"), 2), K.num(rb.get("script_z"), 2),
                      K.signed(r.get("gap"), 2),
                      K.esc(ra.get("n_years") or "—"), K.esc(rb.get("n_years") or "—")))

    return (K.head_block(
        "Do two indices share a calendar?",
        "The same month-by-month residual for <b>%s</b> and <b>%s</b>, side by side, with the gap "
        "between them. A gap is where one index's calendar record parts from the other's — and, "
        "given how little certifies, the honest reading of almost every gap is <b>sampling noise, "
        "not a structural difference</b>." % (K.esc(a), K.esc(b)),
        "seasonal_cells · nightly snapshot", sample=demo)
        + pick
        + K.table(("Month", K.esc(a), K.esc(b), "Gap", "Years (A)", "Years (B)"), "".join(trs))
        + C.learn("Read the two columns first, the gap second. Two indices built from overlapping "
                  "constituents will share most of their calendar by construction — a difference "
                  "only means something if it survives the same certification the tape applies, "
                  "and on this data set that almost never happens."))


# ── view: expiry & holidays (the classic calendar-conditioning lens) ────────────
def _calendar(conn, q) -> str:
    sort = q.get("sort", "pre_holiday_ret_delta")
    if sort not in dict(_CAL_VIEWS):
        sort = "pre_holiday_ret_delta"
    live, asof = W.calendar_conditioning(conn, sort=sort, cap=40)
    if live:
        rows, demo = live, False
    else:
        rows, asof = W.DEMO_CALENDAR
        demo = True

    chips = '<div class="w2-chips">' + "".join(
        '<a class="%s" href="%s">%s</a>' % ("on" if k == sort else "",
                                            K.href(PATH, view="calendar", sort=k), K.esc(lab))
        for k, lab in _CAL_VIEWS) + "</div>"

    def _bps(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return '<span class="w2-z">—</span>'
        if f != f:
            return '<span class="w2-z">—</span>'
        cls = "w2-up" if f > 1e-9 else ("w2-dn" if f < -1e-9 else "w2-z")
        return '<span class="%s">%+.0f</span>' % (cls, f * 1e4)

    trs = "".join(
        '<tr><td class="l">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>'
        '<td>%s</td></tr>'
        % (K.sym_link(r.get("symbol")), _bps(r.get("expiry_ret_delta")),
           _bps(r.get("expiry_week_ret_delta")), _bps(r.get("pre_holiday_ret_delta")),
           _bps(r.get("post_holiday_ret_delta")), K.esc(int(r.get("n_days") or 0)),
           K.esc(int(r.get("n_expiry") or 0)))
        for r in rows)

    return (K.head_block(
        "Expiry days and holidays",
        "For each name: its average day in that calendar window <b>minus</b> its own average day "
        "overall, in basis points (100 bps = 1%). Positive means it tended to run slightly hotter "
        "around monthly expiry or a market holiday; negative, cooler. <b>Most figures sit near "
        "zero</b> — read against the seasonal null above, this is calendar context, not edge.",
        "x_setups_signals · nightly snapshot%s" % ((" · as of " + K.esc(asof)) if asof else ""),
        sample=demo)
        + chips
        + K.table(("Symbol", "Expiry day", "Expiry week", "Pre-holiday", "Post-holiday", "Days",
                   "Expiries"), trs, tall=True)
        + K.note('<a href="%s">Download this table as CSV →</a>'
                 % K.href(PATH, view="calendar", sort=sort, format="csv"))
        + C.fence("Descriptive calendar conditioning. The near-zero rows are published on purpose: "
                  "the estate's calendar-seasonality studies were largely 0-certified, and showing "
                  "that honestly is the point — not a claim that expiry timing predicts returns."))


_RENDER = {"tape": _tape, "screen": _screen, "divergence": _divergence, "calendar": _calendar}

_CSV_COLS = {
    "calendar": ("symbol", "expiry_ret_delta", "expiry_week_ret_delta", "pre_holiday_ret_delta",
                 "post_holiday_ret_delta", "n_days", "n_expiry"),
    "screen": ("entity", "cell", "hit_rate", "ci_lo", "ci_hi", "n_years", "script_z", "colored"),
}


def _csv(conn, view: str, q) -> str:
    """Server-side export of exactly what the page shows (playbook §8 — same params, same rows)."""
    cols = _CSV_COLS.get(view)
    if not cols:
        return ""
    if view == "calendar":
        sort = q.get("sort", "pre_holiday_ret_delta")
        rows, _asof = W.calendar_conditioning(conn, sort=sort, cap=500)
    else:
        try:
            month = int(q.get("month", "") or _dt.date.today().month)
        except (TypeError, ValueError):
            month = _dt.date.today().month
        rows = W.seasonal_month_screen(conn, month if 1 <= month <= 12 else 1,
                                       scope=(q.get("scope") or "index"), limit=500,
                                       lean=("cold" if q.get("lean") == "cold" else "hot"))
    out = [",".join(cols)]
    for r in rows:
        out.append(",".join(
            ('"%s"' % str(r.get(c)).replace('"', "") if isinstance(r.get(c), str)
             else ("" if r.get(c) is None else str(r.get(c)))) for c in cols))
    return "\n".join(out) + "\n"


@router.get("/dash/home/seasonal", response_class=HTMLResponse, include_in_schema=False)
def seasonal(request: Request):
    """The consolidated Seasonal page (tape · this-month screen · index divergence · expiry &
    holidays). Read-only over the bounded nightly snapshots; never 500s. `format=csv` exports the
    same rows the view shows, with the same query params."""
    q = dict(request.query_params)
    view = q.get("view", "tape")
    if view not in _RENDER:
        view = "tape"
    if q.get("format") == "csv" and view in _CSV_COLS:
        from fastapi.responses import PlainTextResponse
        text = ""
        try:
            from src.core.db import get_conn
            with get_conn() as conn:
                conn.row_factory = __import__("sqlite3").Row
                text = _csv(conn, view, q)
        except Exception:  # noqa: BLE001 — an export hiccup must never 500 the page
            text = ",".join(_CSV_COLS[view]) + "\n"
        return PlainTextResponse(
            text or (",".join(_CSV_COLS[view]) + "\n"), media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename=seasonal-%s.csv' % view})
    body, pat = "", ""
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            body = _RENDER[view](conn, q)
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body = (C.fence("The seasonal snapshot hasn't landed yet.")
                + C.empty("It is built by the nightly seasonal run. Check back after the next one."))
    keep = {k: q[k] for k in ("scope", "entity") if q.get(k)}
    page = (C.fence(_FENCE) + K.view_bar(PATH, VIEWS, view, keep=keep, label="Seasonal view")
            + body + K.family_strip(PATH))
    return HTMLResponse(shell.shell("Seasonal", page, extra_head=K.CSS,
                                    current="Markets", pat_html=pat))
