"""src/web/home/compare_pages.py — the Graphite "Compare" page (lane W2-C).

    /dash/home/compare?sym=TCS&cmp=INFY&idx=Nifty%2050&r=252     ← /dash/compare

🔴 `/dash/compare` and `/dash/ratio` are SACRED classic routes: the classic site keeps serving them
byte-untouched. This is a NEW page at a NEW route — nothing classic is edited, moved or wrapped.

URL is the source of truth, and the parameter names are deliberately compatible with the rest of
the Graphite estate: `sym` is the primary name (repeatable or comma-separated) and `cmp` is what to
compare it against, so a stock page can deep-link `…/compare?sym=X&cmp=Y` without this module and
that one importing each other. `idx` adds index lines; `r` is the window in sessions.

Every line is REBASED to 100 at the left edge, which is the only honest way to put a ₹180 name and
a 24,000-point index on one axis. Stock lines are split/bonus-adjusted from the canonical corporate
-actions table — without that a 1:1 bonus renders as a 50% crash, which would be publishing a data
bug in nice colours. Render-only: no derived claim, no ranking, no signal.
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import shell
from src.web.home import w2_kit as K
from src.web.home import w2_reads as W

router = APIRouter()

PATH = "/dash/home/compare"
_WINDOWS = ((63, "3 months"), (126, "6 months"), (252, "1 year"), (504, "2 years"), (1260, "5 years"))
_DEFAULT_IDX = ("Nifty 500", "Nifty 50")


def _split(values) -> list:
    """Accept both repeated params (?sym=A&sym=B) and comma lists (?sym=A,B)."""
    out = []
    for v in values or []:
        for part in str(v).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _chart(series: list) -> str:
    """A server-computed rebased overlay. Points are mapped to a fixed viewBox; nothing is
    interpolated into markup except numbers formatted here."""
    if not series:
        return C.empty("Nothing to plot yet.")
    n = max(len(s["points"]) for s in series)
    vals = [p["v"] for s in series for p in s["points"]]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad
    Wd, Ht = 900.0, 320.0

    def _xy(i, m, v):
        x = (i / max(1, m - 1)) * Wd
        y = Ht - ((float(v) - lo) / (hi - lo)) * Ht
        return x, y

    lines, legend = [], []
    for k, s in enumerate(series):
        col = K.LINE_COLORS[k % len(K.LINE_COLORS)]
        m = len(s["points"])
        pts = " ".join("%.1f,%.1f" % _xy(i, m, p["v"]) for i, p in enumerate(s["points"]))
        lines.append('<polyline class="w2-cl" stroke="%s" points="%s"/>' % (col, pts))
        ch = s.get("change")
        chs = ("<b class=\"%s\">%+.1f%%</b>" % (("w2-up" if ch >= 0 else "w2-dn"), ch)
               if ch is not None else "")
        legend.append('<span><i style="background:%s"></i>%s %s</span>' % (col, K.esc(s["name"]), chs))
    base_y = Ht - ((100.0 - lo) / (hi - lo)) * Ht
    base = ('<line class="w2-cbase" x1="0" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (base_y, Wd, base_y)
            if lo <= 100.0 <= hi else "")
    first = series[0]["points"][0]["t"]
    last = max(s["points"][-1]["t"] for s in series)
    return ('<div class="w2-cmp"><svg viewBox="0 0 900 320" preserveAspectRatio="none" role="img" '
            'aria-label="Rebased comparison, all lines start at 100">' + base + "".join(lines)
            + "</svg></div>"
            + '<div class="w2-cleg">' + "".join(legend) + "</div>"
            + K.note("All lines start at <b>100</b> on %s and run to %s — %d sessions. The dashed "
                     "line is that starting level." % (K.esc(first), K.esc(last), n)))


@router.get("/dash/home/compare", response_class=HTMLResponse, include_in_schema=False)
def compare(request: Request) -> HTMLResponse:
    """Overlay up to six stocks and/or indices, each rebased to 100 at the left edge. Read-only;
    never 500s. `sym`/`cmp` are the deep-link parameters other Graphite pages use."""
    qp = request.query_params
    want_syms = _split(qp.getlist("sym")) + _split(qp.getlist("cmp"))
    want_idx = _split(qp.getlist("idx"))
    try:
        r = int(qp.get("r", "252"))
    except (TypeError, ValueError):
        r = 252
    if r not in dict(_WINDOWS):
        r = 252

    body, pat = "", ""
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            valid_idx_all = W.compare_indices(conn)
            syms = W.valid_symbols(conn, want_syms)
            idxs = [n for n in want_idx if n in set(valid_idx_all)][:W.COMPARE_MAX]
            if not syms and not idxs:
                idxs = [n for n in _DEFAULT_IDX if n in set(valid_idx_all)] or valid_idx_all[:2]
            series = W.compare_series(conn, idxs, syms, sessions=r)
            demo = not series
            if demo:
                # honest sample so the page is legible before the tape lands — the provenance chip
                # says 'sample', and the series are named SAMPLE* so they can't read as real names.
                series = W.DEMO_COMPARE

            def _url(sel_syms, sel_idx, window):
                parts = ["sym=" + quote(s) for s in sel_syms]
                parts += ["idx=" + quote(i) for i in sel_idx]
                parts.append("r=%d" % window)
                return K.esc(PATH + "?" + "&".join(parts))

            win = '<div class="w2-chips">' + "".join(
                '<a class="%s" href="%s">%s</a>'
                % ("on" if w == r else "", _url(syms, idxs, w), K.esc(lab))
                for w, lab in _WINDOWS) + "</div>"

            form = ('<form class="w2-form" method="get" action="%s">'
                    '<input type="text" name="sym" placeholder="Add a symbol, e.g. TCS" '
                    'aria-label="Symbol to compare" maxlength="24">'
                    '<input type="hidden" name="r" value="%d">%s'
                    '<button type="submit">Add</button></form>'
                    % (PATH, r,
                       "".join('<input type="hidden" name="idx" value="%s">' % K.esc(i) for i in idxs)))

            idx_chips = ""
            if valid_idx_all:
                cells = []
                for n in valid_idx_all[:10]:
                    on = n in idxs
                    nxt = [i for i in idxs if i != n] if on else (idxs + [n])[:W.COMPARE_MAX]
                    cells.append('<a class="%s" href="%s">%s</a>'
                                 % ("on" if on else "", _url(syms, nxt, r), K.esc(n)))
                idx_chips = '<div class="w2-chips">' + "".join(cells) + "</div>"
            sym_chips = ""
            if syms:
                cells = []
                for s in syms:
                    nxt = [x for x in syms if x != s]
                    cells.append('<a class="on" href="%s" title="Remove %s">%s ×</a>'
                                 % (_url(nxt, idxs, r), K.esc(s), K.esc(s)))
                sym_chips = '<div class="w2-chips">' + "".join(cells) + "</div>"

            body = (K.head_block(
                "Compare — side by side, from a common start",
                "Put up to six names and indices on one axis. Every line is <b>rebased to 100</b> at "
                "the left edge, so what you read is the shape of each journey over the window, not "
                "the price. Stock lines are adjusted for splits and bonuses from the exchange's own "
                "corporate-action record — without that a 1:1 bonus would render as a 50% crash.",
                "index_rows · bhavcopy_rows · corporate_actions", sample=demo)
                + win + form + sym_chips + idx_chips
                + (_chart(series) if series else
                   C.empty("No history for that selection yet — try a longer window or another name."))
                + (K.note("These two lines are a <b>sample</b> — the exchange price history for "
                          "your selection hasn't landed on this host yet. Nothing real is shown as "
                          "real.") if demo else "")
                + C.learn("Rebasing answers “which grew more over this window”. It deliberately "
                          "does NOT answer “which is cheaper” or “which is better” — a line that "
                          "ends higher simply travelled further from where this window started.")
                + C.fence("Descriptive price history from the exchange tape. No ranking, no "
                          "recommendation, and nothing here is adjusted for risk."))
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body = (C.fence("Price history isn't readable right now.")
                + C.empty("Check back after the next nightly run."))
    body += K.family_strip(PATH)
    return HTMLResponse(shell.shell("Compare", body, extra_head=K.CSS,
                                    current="Markets", pat_html=pat))
