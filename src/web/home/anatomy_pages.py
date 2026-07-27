"""src/web/home/anatomy_pages.py — the Graphite "how unusual is this?" pair (lane W2-C).

Two sibling pages, one idea — measuring something against a baseline instead of in isolation:

    /dash/home/anatomy      ← /dash/move-anatomy   (what preceded big moves, market-wide, 2011→)
    /dash/home/own-history  ← /dash/self-history   (how unusual TODAY is, for THIS name)

They stay two routes because the grain genuinely differs: anatomy is one historical study over a
labelled event panel; own-history is today's reading per name.

🔴 OWN-HISTORY IMPLEMENTATION NOTE (a recorded verdict, not a shortcut). The Graphite package may
NOT import the classic `/dash/self-history` web-view engine — doing so breaks
`tests/test_home_isolation.py`. This page therefore re-derives the self-relative axis from the
STORED `stock_signals` ratio columns, each of which is already "this name now versus this name's
own baseline", and — for a single named symbol — ranks each of those ratios against that symbol's
OWN trailing history of the same ratio (a true own-history percentile, from stored data, bounded to
one symbol). The classic lens's 3-year percentile over raw adjusted OHLC is NOT reproduced here;
that difference is disclosed on the page and in the parity ledger.

🔴 ANATOMY FENCE. The fingerprint is a POST-SELECTION base rate (events were chosen because a move
already fired), survivorship-biased UP (delisted losers are absent) and measured against a 1-in-10
sampled baseline. It is a picture of what pre-move days looked like in hindsight — NEVER an entry
rule. Its headline finding is a counter-narrative worth stating plainly: big moves launched from
momentum and strength, NOT from the tight-base, heavy-delivery "accumulation footprint" the setup
lore assumes.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import shell
from src.web.home import w2_kit as K
from src.web.home import w2_reads as W

router = APIRouter()

ANATOMY_PATH = "/dash/home/anatomy"
OWN_PATH = "/dash/home/own-history"


def _pick(live, demo):
    return (live, False) if live else (demo, True)


# ── /dash/home/anatomy ──────────────────────────────────────────────────────────
def _fingerprint(bars) -> str:
    if not bars:
        return C.empty("No precursor columns available in the research panel.")
    mx = max(abs(float(b["z"])) for b in bars) or 1.0
    out = []
    for b in bars:
        z = float(b["z"])
        out.append(K.bar_row(
            b["plain"],
            '<span class="%s">%+0.2f</span>' % ("w2-up" if z > 0 else "w2-dn", z),
            abs(z) / mx * 100.0, cls=("neg" if z < 0 else "")))
    return K.box("".join(out), tall=True)


def _envelope(env) -> str:
    ev, base = (env or {}).get("event"), (env or {}).get("baseline")
    if not ev:
        return ""
    def _cell(d, key):
        return K.num((d or {}).get(key), 1) + "%" if d and d.get(key) is not None else "—"
    trs = ("<tr><td class=\"l\">Days a big move followed</td><td>%s</td><td>%s</td><td>%s</td></tr>"
           % (_cell(ev, "mfe"), _cell(ev, "mae"), K.esc("{:,}".format(int(ev.get("n") or 0))))
           + ("<tr><td class=\"l\">A quiet day, for comparison</td><td>%s</td><td>%s</td><td>%s</td></tr>"
              % (_cell(base, "mfe"), _cell(base, "mae"),
                 K.esc("{:,}".format(int((base or {}).get("n") or 0)))) if base else ""))
    return ('<h3 class="w2-sect">How far price travelled afterwards, either way</h3>'
            + K.table(("Starting point", "Best move up, 6 months", "Worst move down, 6 months",
                       "Days measured"), trs)
            + K.note("Both numbers are measured on the <b>same</b> days, so the pair shows the "
                     "shape of the ride, not just the reward. A wider up-figure with a similar "
                     "down-figure is what a genuinely different starting point looks like."))


@router.get("/dash/home/anatomy", response_class=HTMLResponse, include_in_schema=False)
def anatomy(request: Request) -> HTMLResponse:
    """What actually preceded big moves — the fingerprint + the excursion envelope. Reads the
    research panel read-only; says so honestly when that database isn't on this host."""
    body, pat = "", ""
    try:
        d = W.move_anatomy()
        if not d or not d.get("bars"):
            body = (K.head_block(
                "What actually comes before a big move",
                "This page reads the labelled explosive-move research panel — 166,000 labelled "
                "events against a sampled quiet baseline, 2011 onwards. <b>That database is not "
                "present on this host</b>, so there is nothing to show rather than something "
                "invented.", "research panel · offline host")
                + C.empty("The research panel lives beside the main database on the production "
                          "host. Nothing is fabricated in its absence."))
        else:
            bars, env, meta = d["bars"], d.get("envelope"), d.get("meta") or {}
            top = bars[0] if bars else None
            bottom = bars[-1] if bars else None
            body = (K.head_block(
                "What actually comes before a big move",
                "Each bar is how far that measure sat from a <b>quiet</b> day, in standard "
                "deviations of the quiet baseline — so ninety raw attributes become one readable "
                "profile. The finding is a counter-narrative: big moves launched from <b>momentum "
                "and strength</b> — already up, already stronger than the market, already above "
                "its long trend lines — and <b>not</b> from the tight, heavily-delivered "
                "accumulation base the setup lore assumes.",
                "research panel · labelled event study")
                + _fingerprint(bars)
                + K.note("Strongest above baseline: <b>%s</b>. Furthest below: <b>%s</b>."
                         % (K.esc(top["plain"]) if top else "—",
                            K.esc(bottom["plain"]) if bottom else "—"))
                + _envelope(env)
                + C.learn("A bar of +0.5 means that measure ran half a standard deviation above a "
                          "quiet day. Anything within roughly ±0.2 is close enough to the baseline "
                          "that it did not distinguish pre-move days at all.")
                + C.fence("Descriptive, and deliberately fenced. Events were selected BECAUSE a "
                          "move already fired, delisted losers are absent from the panel, and the "
                          "comparison baseline is a 1-in-10 sample. This is what pre-move days "
                          "looked like in hindsight — it is not an entry rule, and it was never "
                          "tested as one.")
                + (K.note("Panel built %s." % K.esc(meta.get("built_at") or meta.get("asof") or ""))
                   if (meta.get("built_at") or meta.get("asof")) else ""))
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body = (C.fence("The move-anatomy panel isn't readable right now.")
                + C.empty("Nothing is shown rather than something invented."))
    body += K.family_strip(ANATOMY_PATH)
    return HTMLResponse(shell.shell("Move anatomy", body, extra_head=K.CSS,
                                    current="Markets", pat_html=pat))


# ── /dash/home/own-history ──────────────────────────────────────────────────────
def _own_universe(conn, sort: str) -> str:
    live, as_of = W.own_history_universe(conn, limit=40, sort=sort)
    if live:
        rows, demo = live, False
    else:
        rows, as_of = W.DEMO_OWN
        demo = True
    chips = '<div class="w2-chips">' + "".join(
        '<a class="%s" href="%s">%s</a>' % ("on" if k == sort else "",
                                            K.href(OWN_PATH, sort=k), K.esc(plain))
        for (k, plain, _c, _u, _h) in W.OWN_METRICS[:4]) + "</div>"

    trs = "".join(
        '<tr><td class="l">%s</td><td class="l">%s</td><td>%s</td><td>%s</td><td>%s</td>'
        '<td>%s</td><td>%s</td></tr>'
        % (K.sym_link(r.get("symbol")), K.esc(r.get("primary_sector") or "—"),
           (K.num(r.get("turnover_surge_1m"), 2) + "×") if r.get("turnover_surge_1m") is not None else "—",
           (K.num(r.get("turnover_surge_1y"), 2) + "×") if r.get("turnover_surge_1y") is not None else "—",
           (K.num(r.get("avg_deliv_pct_1m"), 0) + "%") if r.get("avg_deliv_pct_1m") is not None else "—",
           K.signed(r.get("_deliv_gap"), 1, "pp"),
           K.signed(r.get("pct_from_52w_high"), 1, "%"))
        for r in rows)

    return (K.head_block(
        "How unusual is today — for each name?",
        "Every column here compares a name to <b>its own</b> baseline, not to other stocks. A "
        "₹13,000 giant and a ₹180 small-cap therefore read on the same axis: <i>busier than usual "
        "for you</i>, <i>more conviction than usual for you</i>, <i>near your own high</i>. That is "
        "the third way to look at the tape — beside absolute price and strength-versus-the-market — "
        "and it is what makes a quiet drift to a high on the thinnest participation in a year stand "
        "out at all.",
        "stock_signals · nightly%s" % ((" · " + K.esc(as_of)) if as_of and not demo else ""),
        sample=demo)
        + chips
        + K.table(("Symbol", "Sector", "Turnover vs own 1-month", "vs own 1-year",
                   "Delivery, 1-month", "vs own 6-month", "From own 1-year high"), trs, tall=True)
        + C.learn("“2.4×” means the name traded 2.4 times its own recent normal turnover — not that "
                  "it traded more than other stocks. Read the delivery gap beside it: heavy turnover "
                  "with delivery below its own norm is churn, not conviction.")
        + C.fence("Self-relative extremity is CONTEXT — how unusual today is for this name. It says "
                  "nothing about what happens next, and nothing here is ranked as an opportunity."))


def _own_symbol(conn, sym: str) -> str:
    d = W.own_history_symbol(conn, sym)
    if not d:
        return (K.head_block("How unusual is today — %s" % K.esc(sym.upper()),
                             "No stored history for that symbol yet.", "stock_signals")
                + C.empty("Check the spelling, or pick a name from the table.")
                + K.note('<a href="%s">← back to the whole list</a>' % K.href(OWN_PATH)))
    rows = []
    for m in d["metrics"]:
        p = m.get("pctile")
        if p is None:
            rows.append(K.bar_row(m["plain"], '<span class="w2-z">not enough history</span>', 0))
            continue
        band = ("unusually high" if p >= 80 else ("unusually low" if p <= 20 else "about typical"))
        val = K.num(m.get("value"), 2) + (m.get("unit") or "")
        rows.append(K.bar_row(
            m["plain"],
            '%s <span class="w2-z">· %s pct · %s</span>' % (val, K.num(p, 0), K.esc(band)), p))
    return (K.head_block(
        "How unusual is today — %s" % K.esc(d["symbol"]),
        "Each measure ranked against <b>%s's own</b> last %d sessions of the same measure. 100 "
        "means the most extreme reading in that window; 50 means a completely ordinary day for this "
        "name. Typical value shown beside each bar in the list view."
        % (K.esc(d["symbol"]), int(d.get("n_sessions") or 0)),
        "stock_signals · own history%s" % ((" · " + K.esc(d.get("as_of"))) if d.get("as_of") else ""))
        + K.box("".join(rows))
        + K.note("Sector <b>%s</b> · strength rank <b>%s</b> · character <b>%s</b>."
                 % (K.esc(d.get("sector") or "—"), K.esc(d.get("rs_rank") or "—"),
                    K.esc(d.get("character") or "—")))
        + K.note('<a href="%s">← back to the whole list</a> · '
                 '<a href="%s?sym=%s">open the full stock page →</a>'
                 % (K.href(OWN_PATH), K.STOCK_PATH, K.esc(d["symbol"])))
        + C.fence("Percentiles are against this name's own stored history of the same ratio. They "
                  "describe how unusual today is for it — never a forecast, never a ranking."))


@router.get("/dash/home/own-history", response_class=HTMLResponse, include_in_schema=False)
def own_history(request: Request) -> HTMLResponse:
    """The self-relative map: how unusual today is for each name, measured against its own stored
    baselines (never the classic view engine — see the module docstring). `?sym=` drills to one
    name's own-history percentiles. Never 500s."""
    q = dict(request.query_params)
    sym = (q.get("sym") or "").strip().upper()
    sort = q.get("sort", "turn1m")
    if sort not in {k for (k, _p, _c, _u, _h) in W.OWN_METRICS}:
        sort = "turn1m"
    body, pat = "", ""
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            body = _own_symbol(conn, sym) if sym else _own_universe(conn, sort)
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body = (C.fence("Today's per-name readings haven't landed yet.")
                + C.empty("Check back after the next nightly run."))
    body += K.family_strip(OWN_PATH)
    return HTMLResponse(shell.shell("Own history", body, extra_head=K.CSS,
                                    current="Markets", pat_html=pat))
