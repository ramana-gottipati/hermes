"""src/web/home/patterns_pages.py — the Graphite "Patterns" page (lane W2-C).

ONE page, two views, replacing the classic Patterns pair:

    /dash/home/patterns?view=wolfe     ← /dash/wolfe/scan
                       ?view=harmonic  ← /dash/harmonic

They were already a sub-nav pair on the classic site (both emit the "Patterns" group), both read a
nightly snapshot of an auto-detected price shape, and both are read BY SIDE — so they are one page
with a view selector, not two nav rows.

🔴 FENCES THAT TRAVEL WITH THE DATA
  * Wolfe: the out-of-sample result says the edge is in the **SELECTION, not the craft** — not in
    the stop, not in the target, not in the drawing. Descriptive-only.
  * Both: read BY SIDE. BULL carries a modest, real, fit-graded selection edge; BEAR is roughly
    short-drift — tail/regime only, never a standalone edge.

🔴 HOT-LANE DISCIPLINE. The Wolfe/chart lane is actively committing to origin/main. This module
imports NOTHING from `wolfe*.py` or `stock_chart*.py`; it reads the nightly `wolfe_signals` /
`harmonic_signals` snapshots with plain bounded SQL in `w2_reads.py`, so the port has zero
collision surface with that lane.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import shell
from src.web.home import w2_kit as K
from src.web.home import w2_reads as W

router = APIRouter()

PATH = "/dash/home/patterns"
VIEWS = (("wolfe", "Wolfe waves"), ("harmonic", "Harmonic shapes"))

_FENCE = ("Auto-detected price shapes from the nightly scan. Descriptive — a place to look, never "
          "a buy or sell signal. Where these were tested, the edge lived in WHICH names the shape "
          "selected, not in the entry, stop or target drawn on the chart.")


def _pick(live, demo):
    return (live, False) if live else (demo, True)


def _side(direction: str) -> str:
    d = (direction or "").upper()
    if d == "BULL":
        return '<span class="w2-pill on">BULL · selection edge</span>'
    if d == "BEAR":
        return '<span class="w2-pill warn">BEAR · tail only</span>'
    return '<span class="w2-pill">%s</span>' % K.esc(d or "—")


def _status(in_zone) -> str:
    return ('<span class="w2-up">● in zone</span>' if in_zone
            else '<span class="w2-z">watching</span>')


def _asof(meta: dict, demo: bool) -> str:
    d = (meta or {}).get("scan_date") or ""
    if demo or not d:
        return ""
    c = (meta or {}).get("computed_at") or ""
    return K.note("Scan as of <b>%s</b>%s. The scan runs nightly; nothing here recomputes when you "
                  "load the page." % (K.esc(d), (" · computed " + K.esc(str(c)[:16])) if c else ""))


# ── view: Wolfe ─────────────────────────────────────────────────────────────────
def _wolfe(conn, q) -> str:
    live_rows, live_meta = W.wolfe_scan(conn, limit=60)
    if live_rows:
        rows, meta, demo = live_rows, live_meta, False
    else:
        rows, meta = W.DEMO_WOLFE
        demo = True
    n_in = sum(1 for r in rows if r.get("in_zone"))

    trs = "".join(
        '<tr><td class="l">%s</td><td class="l">%s</td><td>%s</td><td>%s</td><td>%s</td>'
        '<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
        % (K.sym_link(r.get("sym")), _side(r.get("dir")), _status(r.get("in_zone")),
           K.esc(r.get("age") if r.get("age") is not None else "—") + "d",
           K.num(r.get("cmp"), 1),
           "%s–%s" % (K.num(r.get("zlo"), 1), K.num(r.get("zhi"), 1)),
           K.num(r.get("sl"), 1), K.num(r.get("t1"), 1),
           (K.num(r.get("up"), 0) + "%") if r.get("up") is not None else "—")
        for r in rows)

    depth = K.table(("Symbol", "Side", "Status", "Age", "Price", "Zone", "Stop", "First target",
                     "Room to target"), trs, tall=True)

    return (K.head_block(
        "Wolfe waves — where the shape completed",
        "A Wolfe wave is a five-point price structure whose last leg overshoots the earlier trend "
        "line. This scan lists the names where the structure finished recently. <b>%d in their zone "
        "right now</b> out of %d. Tested honestly — fitted on 2004-14 and then run untouched on "
        "2015-26 with a market-regime control — the result was blunt: <b>the edge is in the "
        "selection, not the craft.</b> Which names the shape picks out carried the result; the "
        "stop and target drawn around it did not." % (n_in, len(rows)),
        "wolfe_signals · nightly snapshot", sample=demo)
        + _asof(meta, demo)
        + C.learn("Read the Side column first. BULL setups held up across regimes; BEAR ones were "
                  "roughly the same as simply being short in a falling market — so they tell you "
                  "about the tape, not about the name.")
        + depth
        + C.fence("Descriptive. The zone, stop and target are shown because they define the shape "
                  "that was measured — not because following them is a validated way to trade."))


# ── view: harmonic ──────────────────────────────────────────────────────────────
def _harmonic(conn, q) -> str:
    live_rows, live_meta = W.harmonic_scan(conn, limit=60)
    if live_rows:
        rows, meta, demo = live_rows, live_meta, False
    else:
        rows, meta = W.DEMO_HARMONIC
        demo = True
    n_in = sum(1 for r in rows if r.get("in_zone"))

    def _zone(r):
        if (r.get("state") or "").upper() == "CONFIRMED":
            return K.num(r.get("d_price"), 1)
        lo, hi = r.get("prz_lo"), r.get("prz_hi")
        if lo is None or hi is None:
            return '<span class="w2-z">—</span>'
        try:
            return "%s–%s" % (K.num(min(lo, hi), 1), K.num(max(lo, hi), 1))
        except (TypeError, ValueError):
            return '<span class="w2-z">—</span>'

    trs = "".join(
        '<tr><td class="l">%s</td><td class="l">%s</td><td class="l">%s</td><td class="l">%s</td>'
        '<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
        % (K.sym_link(r.get("sym")), K.esc(r.get("pattern") or "—"), _side(r.get("dir")),
           K.esc((r.get("state") or "").title() or "—"), _status(r.get("in_zone")),
           K.esc(r.get("age") if r.get("age") is not None else "—") + "d",
           K.num(r.get("cmp"), 1), _zone(r),
           K.num(r.get("score"), 2) if r.get("score") is not None else "—")
        for r in rows)

    return (K.head_block(
        "Harmonic shapes — five-point reversals",
        "Gartley, Bat, Butterfly and Crab are named five-point price shapes whose legs sit in fixed "
        "proportions to one another; when the last point lands, the shape marks a candidate reversal "
        "zone. <b>%d of %d are in their zone now.</b> <b>Confirmed</b> means the final point has "
        "printed; <b>forming</b> means the zone is projected and the price hasn't got there yet. "
        "Same honest split as the Wolfe scan: the bull side carried a modest, fit-graded selection "
        "edge; the bear side was about the same as short-drift." % (n_in, len(rows)),
        "harmonic_signals · nightly snapshot", sample=demo)
        + _asof(meta, demo)
        + K.table(("Symbol", "Shape", "Side", "State", "Status", "Age", "Price",
                   "Zone / projected", "Fit"), trs, tall=True)
        + C.learn("The Fit column grades how closely the shape matched its ideal proportions. It "
                  "stratifies the sample — a better fit was a cleaner selection — but it is a "
                  "description of geometry, not a probability of profit.")
        + C.fence("Descriptive — a place to look, not a buy or sell signal. Read by side: bull is a "
                  "modest selection edge, bear is tail/regime only."))


_RENDER = {"wolfe": _wolfe, "harmonic": _harmonic}


@router.get("/dash/home/patterns", response_class=HTMLResponse, include_in_schema=False)
def patterns(request: Request) -> HTMLResponse:
    """The consolidated Patterns page (Wolfe waves · harmonic shapes). Read-only over the nightly
    snapshots — no live recompute, no chart-lane imports; never 500s."""
    q = dict(request.query_params)
    view = q.get("view", "wolfe")
    if view not in _RENDER:
        view = "wolfe"
    body, pat = "", ""
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            body = _RENDER[view](conn, q)
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body = (C.fence("The pattern scan hasn't landed yet.")
                + C.empty("Both scans are built nightly. Check back after the next run."))
    page = (C.fence(_FENCE) + K.view_bar(PATH, VIEWS, view, label="Pattern view")
            + body + K.family_strip(PATH))
    return HTMLResponse(shell.shell("Patterns", page, extra_head=K.CSS,
                                    current="Markets", pat_html=pat))
