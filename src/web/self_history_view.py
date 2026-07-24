"""Own-history map — every metric ranked 0-100 against each stock's OWN past.

The site is full of ABSOLUTE reads (price, delivery, turnover) and RELATIVE reads (RS vs
the benchmark). This lens adds the third axis nobody arranges the data along: **self-relative**
— how extreme is each number for THIS stock, versus its own trailing 3-year history. A ₹13,000
giant and a ₹180 small-cap then read on one 0-100 scale ("how unusual is today, for you"), so
divergent signatures pop out that a price chart hides:

  * Price     — where today's close sits in its own 3-year range (100 = at its own high).
  * Momentum  — its 3-month return, ranked against its own history of 3-month returns.
  * Delivery  — today's delivery-% (5-day smoothed), vs its own delivery history (conviction).
  * Turnover  — today's ₹ turnover, vs its own (participation; value-based, action-neutral).
  * Coil      — recent daily range, vs its own (LOW = coiled/quiet, HIGH = expanded/violent).

WHY it surprises: a stock at its own price-high with turnover in its 15th percentile and range
in its 6th is drifting up on the thinnest participation in three years (a "hollow high") — the
opposite of one making a high on 98th-percentile turnover. Same OHLC everyone has; the
ARRANGEMENT is the insight.

SECOND LENS (cross-sectional): each cell also carries its percentile vs the FIELD today (the small
number beside the big self one). A cell extreme on BOTH its own past AND its peers — a gold ring —
is the two-lens confluence, a stronger, less noisy read than either alone. Turnover is self-only
(raw ₹ turnover is a size proxy across stocks, so it has no meaningful peer rank).

Corporate-action HYGIENE (load-bearing): raw NSE close is unadjusted, so a split/bonus fakes a
crash in the price/momentum percentiles (a 1:1 bonus halves the close; Nestlé's 1:10 split ÷10).
Price & momentum are computed on a split/bonus-ADJUSTED series; delivery-%, ₹ turnover and the
range ratio are action-neutral and used raw. Without this the page would publish a data bug in
nice colours.

STRICTLY DESCRIPTIVE (ledger): a self-relative percentile is CONTEXT, not a signal — "extreme vs
its own past" says nothing about forward return, no ranking, no buy/sell. Compute-on-read, cached
per trading day (Nifty 500 ~2.3s cold, instant warm). Route: /dash/self-history [?u=..&sort=..].
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

# universes (compute-on-read, cached per trading day; Nifty 500 ~2.3s cold, instant warm)
_UNIVERSES: dict[str, str] = {
    "nifty50":     "Nifty 50",
    "next50":      "Nifty Next 50",
    "nifty500":    "Nifty 500",
    "midcap100":   "Nifty Midcap 100",
    "smallcap100": "Nifty Smallcap 100",
}
_WIN = 756          # ~3y trailing self-normalisation window
_MOMN = 63          # ~3-month momentum lookback

# the 5 self-relative columns: (key, short label, tooltip)
_COLS = [
    ("price_pct", "Price",    "where today's close sits in its own 3-year range (100 = own high)"),
    ("mom_pct",   "Momentum", "3-month return, ranked vs its own history of 3-month returns"),
    ("deliv_pct", "Delivery", "delivery-% (5-day smoothed) vs its own history (conviction)"),
    ("turn_pct",  "Turnover", "₹ turnover vs its own history (participation; action-neutral)"),
    ("vol_pct",   "Coil",     "daily range vs its own history — LOW = coiled, HIGH = expanded"),
]

# diverging blue -> neutral -> red ramp for a 0..100 self-percentile (fixed hex → theme-safe,
# text colour computed per-cell). 0 = 3-yr low (cool), 50 = middle, 100 = 3-yr high (warm).
_STOPS = [(27, 95, 166), (127, 176, 224), (207, 205, 196), (231, 154, 154), (163, 45, 45)]


def _heat(v: float) -> tuple[str, str]:
    """(bg, fg) for a 0..100 percentile — piecewise-linear across the 5 ramp stops."""
    if v is None:
        return ("var(--bg-3)", "var(--ink-3)")
    v = max(0.0, min(100.0, float(v)))
    p = v / 25.0
    i = min(3, int(p))
    f = p - i
    a, b = _STOPS[i], _STOPS[i + 1]
    c = [round(a[k] + (b[k] - a[k]) * f) for k in range(3)]
    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    return (f"rgb({c[0]},{c[1]},{c[2]})", "#fff" if lum < 150 else "#23201c")


def _pct_rank(hist: list, x: float) -> float | None:
    """SELF lens: percentile (0..100) of x within the stock's OWN history; >=120 usable points."""
    vals = [h for h in hist if h is not None]
    if len(vals) < 120 or x is None:
        return None
    n = sum(1 for h in vals if h <= x)
    return round(100.0 * n / len(vals), 1)


# PEER lens: which comparable raw quantity each cell is cross-ranked on across the universe.
# Turnover is deliberately absent — raw ₹ turnover is a size proxy (a giant always ranks top), so
# it has no meaningful peer rank and stays self-only.
_CROSS_SRC = {"price_pct": "off_hi", "mom_pct": "ret63", "deliv_pct": "deliv", "vol_pct": "rng"}


def _cross_rank(sorted_vals: list, x: float) -> float | None:
    """PEER lens: percentile (0..100) of x within the universe's values TODAY (>=20 peers).
    Direction matches the self lens per _CROSS_SRC (higher off_hi/ret63/deliv → higher; lower
    range → lower = coiled), so the small peer number reads the same way as the big self one."""
    if x is None or len(sorted_vals) < 20:
        return None
    n = sum(1 for h in sorted_vals if h <= x)
    return round(100.0 * n / len(sorted_vals), 1)


def _adj_events(conn, sym: str) -> list:
    """(ex_date, factor) for split/bonus actions — pre-ex prices multiply by the cumulative
    factor to sit on today's basis. SPLIT 5->1 => x0.2; BONUS a:b (a new / b held) => b/(a+b)."""
    out = []
    try:
        rows = conn.execute(
            "SELECT action_type, ex_date, ratio_from, ratio_to FROM corporate_actions "
            "WHERE symbol=? AND action_type IN ('SPLIT','BONUS') AND ex_date IS NOT NULL", (sym,)
        ).fetchall()
    except Exception:  # noqa: BLE001 — no corp-actions table on a bare host
        return out
    for r in rows:
        at, ex, rf, rt = r[0], r[1], r[2], r[3]
        try:
            if at == "SPLIT" and rf:
                out.append((ex, rt / rf))
            elif at == "BONUS" and rf is not None and rt is not None and (rf + rt):
                out.append((ex, rt / (rf + rt)))
        except Exception:  # noqa: BLE001
            continue
    return out


def _sm(a: list, k: int = 5) -> list:
    """trailing mean smoother (skips gaps by carrying the window)."""
    out = []
    for i in range(len(a)):
        w = a[max(0, i - k + 1):i + 1]
        out.append(sum(w) / len(w) if w else 0.0)
    return out


def _metrics(conn, sym: str) -> dict | None:
    rows = conn.execute(
        "SELECT trade_date, close, high, low, value, deliv_per FROM bhavcopy_rows "
        "WHERE symbol=? AND series='EQ' AND close>0 ORDER BY trade_date DESC LIMIT ?",
        (sym, _WIN)).fetchall()
    if len(rows) < 200:
        return None
    rows = rows[::-1]
    dts = [r[0] for r in rows]
    rclose = [r[1] for r in rows]
    rhigh = [r[2] for r in rows]
    rlow = [r[3] for r in rows]
    val = [r[4] for r in rows]
    dp = [r[5] for r in rows]
    n = len(rclose)

    evs = _adj_events(conn, sym)

    def adj(d):
        f = 1.0
        for ex, ff in evs:
            if ex > d:
                f *= ff
        return f

    close = [rclose[i] * adj(dts[i]) for i in range(n)]
    high = [rhigh[i] * adj(dts[i]) if rhigh[i] else rhigh[i] for i in range(n)]
    low = [rlow[i] * adj(dts[i]) if rlow[i] else rlow[i] for i in range(n)]

    price_pct = _pct_rank(close, close[-1])

    moms = [close[i] / close[i - _MOMN] - 1 for i in range(_MOMN, n) if close[i - _MOMN]]
    mom_latest = moms[-1] if moms else None
    mom_pct = _pct_rank(moms, mom_latest)

    dps = [d for d in dp if d is not None]
    dp_fill = [d if d is not None else (dps[-1] if dps else 0.0) for d in dp]
    dp_s = _sm(dp_fill, 5)
    deliv_pct = _pct_rank(dp_s, dp_s[-1]) if dps else None

    turn_pct = _pct_rank(val, val[-1])

    rng = [(high[i] - low[i]) / close[i] for i in range(n) if close[i]]
    rng14 = _sm(rng, 14)
    vol_pct = _pct_rank(rng14, rng14[-1])

    hi252 = max(close[-252:]) if n >= 252 else max(close)
    off_hi = round(100.0 * (close[-1] / hi252 - 1), 1) if hi252 else None
    ret63 = round(100.0 * mom_latest, 1) if mom_latest is not None else None
    return {
        "sym": sym, "date": dts[-1],
        "price_pct": price_pct, "mom_pct": mom_pct, "deliv_pct": deliv_pct,
        "turn_pct": turn_pct, "vol_pct": vol_pct,
        "off_hi": off_hi, "ret63": ret63,
        "deliv": round(dp_s[-1], 1) if dps else None,
        "rng": round(rng14[-1], 5) if rng14 else None,   # raw range for the peer (cross) lens
        "turn_cr": round((val[-1] or 0) / 1e7, 1), "close": round(close[-1], 1),
    }


@lru_cache(maxsize=8)
def _compute(u_key: str, asof: str) -> tuple:
    """Self-relative percentiles for one universe, as of the latest trading day. Cached per
    (universe, trading-day) so it recomputes at most once a day. asof is passed only to key
    the cache to the data date (compute reads the live latest bar)."""
    idx = _UNIVERSES[u_key]
    out = []
    with get_conn() as conn:
        snap = conn.execute("SELECT MAX(snapshot_date) FROM stock_index_membership "
                            "WHERE index_name=?", (idx,)).fetchone()[0]
        if not snap:
            return tuple()
        syms = [r[0] for r in conn.execute(
            "SELECT symbol FROM stock_index_membership WHERE index_name=? AND snapshot_date=?",
            (idx, snap)).fetchall()]
        for s in syms:
            try:
                m = _metrics(conn, s)
            except Exception:  # noqa: BLE001 — one bad symbol never breaks the board
                m = None
            if m:
                out.append(m)
    # SECOND LENS — cross-sectional (vs the field TODAY): rank each comparable raw quantity across
    # the universe → cx_<cellkey>. Turnover stays self-only (no peer rank). The render highlights
    # CONFLUENCE (a cell extreme on its own past AND vs peers) — the stronger, less noisy read.
    for key, src in _CROSS_SRC.items():
        vals = sorted(r[src] for r in out if r.get(src) is not None)
        for r in out:
            r["cx_" + key] = _cross_rank(vals, r.get(src))
    return tuple(out)


def _latest_date() -> str:
    with get_conn() as conn:
        r = conn.execute("SELECT MAX(trade_date) FROM bhavcopy_rows").fetchone()
        return (r[0] if r and r[0] else "")


_SORTS = {c[0] for c in _COLS} | {"sym"}


def _sorted(rows: list, sort: str) -> list:
    if sort == "sym":
        return sorted(rows, key=lambda z: z["sym"])
    return sorted(rows, key=lambda z: (z.get(sort) is None, -(z.get(sort) or 0)))


_CSS = """
<style>
.sh-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 12px;max-width:1120px;}
.sh-note b{color:var(--ink);}
.sh-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:2px 0 10px;}
.sh-ctrl a{padding:4px 12px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;text-decoration:none;}
.sh-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.sh-ctrl .sep{color:var(--ink-3);font-size:11px;margin:0 2px;}
.sh-key{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:0 0 12px;font-size:11.5px;color:var(--ink-3);}
.sh-key .ramp{display:inline-block;width:132px;height:11px;border-radius:3px;
  background:linear-gradient(90deg,rgb(27,95,166),rgb(127,176,224),rgb(207,205,196),rgb(231,154,154),rgb(163,45,45));}
.sh-wrap{overflow-x:auto;margin:0 0 8px;}
table.sh{border-collapse:collapse;font-size:12px;min-width:640px;}
table.sh th{color:var(--ink-3);font-weight:600;padding:3px 6px 7px;white-space:nowrap;}
table.sh th a{color:var(--ink-3);text-decoration:none;}
table.sh th a:hover{color:var(--ink);}
table.sh th.raw{color:var(--ink-3);text-align:right;font-weight:500;}
table.sh td{padding:0 2px;border-top:1px solid var(--line);height:23px;}
table.sh td.sym a{color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap;}
table.sh td.sym a:hover{text-decoration:underline;}
table.sh td.cell{padding:0 1px;}
table.sh td.cell .b{text-align:center;padding:3px 0;border-radius:3px;font-variant-numeric:tabular-nums;min-width:47px;}
table.sh td.cell .b .xs{font-size:9.5px;font-weight:400;opacity:.72;margin-left:3px;}
table.sh td.cell .b.cf{outline:2px solid #f5c518;outline-offset:-2px;}
.sh-cf-dot{display:inline-block;width:11px;height:11px;border-radius:2px;outline:2px solid #f5c518;outline-offset:-2px;background:var(--bg-3);vertical-align:-1px;}
table.sh td.raw{text-align:right;padding:0 6px;font-variant-numeric:tabular-nums;color:var(--ink-2);}
table.sh td.raw.mut{color:var(--ink-3);}
.sh-pos{color:var(--up);} .sh-neg{color:var(--down);}
.sh-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 6px;}
.sh-chip{background:var(--bg-2);border:1px solid var(--line-2);border-radius:9px;padding:6px 10px;font-size:11.5px;color:var(--ink-2);}
.sh-chip b{color:var(--ink);} .sh-chip a{color:var(--accent);text-decoration:none;}
</style>
"""


def _chips(rows: list) -> str:
    """A few auto-generated 'what stands out' callouts — descriptive, from the data itself."""
    def top(key, want_low=False):
        cand = [r for r in rows if r.get(key) is not None]
        if not cand:
            return None
        return sorted(cand, key=lambda z: z[key])[0 if want_low else -1]

    out = []
    coiled = top("vol_pct", want_low=True)
    if coiled:
        out.append(f'<div class="sh-chip">Most coiled vs its own past: <a href="/dash/stock?sym='
                   f'{_esc(coiled["sym"])}">{_esc(coiled["sym"])}</a> <b>{coiled["vol_pct"]:.0f}</b> range pctl</div>')
    hollow = [r for r in rows if (r.get("price_pct") or 0) >= 90 and (r.get("turn_pct") is not None)
              and r["turn_pct"] < 25]
    if hollow:
        h = sorted(hollow, key=lambda z: z["turn_pct"])[0]
        out.append(f'<div class="sh-chip">Highest on thinnest trade ("hollow high"): '
                   f'<a href="/dash/stock?sym={_esc(h["sym"])}">{_esc(h["sym"])}</a> '
                   f'price <b>{h["price_pct"]:.0f}</b> · turnover <b>{h["turn_pct"]:.0f}</b></div>')
    dist = [r for r in rows if (r.get("price_pct") or 0) >= 80 and (r.get("mom_pct") is not None)
            and r["mom_pct"] <= 20 and (r.get("deliv_pct") or 0) >= 80]
    if dist:
        d = sorted(dist, key=lambda z: z["mom_pct"])[0]
        out.append(f'<div class="sh-chip">High range, fading momentum, heavy delivery: '
                   f'<a href="/dash/stock?sym={_esc(d["sym"])}">{_esc(d["sym"])}</a> '
                   f'mom <b>{d["mom_pct"]:.0f}</b> · deliv <b>{d["deliv_pct"]:.0f}</b></div>')

    # confluence: the name with the most cells extreme on BOTH lenses (own past AND vs peers)
    def _cfn(r):
        c = 0
        for key, _l, _t in _COLS:
            v, x = r.get(key), r.get("cx_" + key)
            if v is not None and x is not None and ((v >= 80 and x >= 80) or (v <= 20 and x <= 20)):
                c += 1
        return c
    ranked = sorted(((_cfn(r), r) for r in rows), key=lambda z: -z[0])
    if ranked and ranked[0][0] >= 2:
        cnt, r = ranked[0]
        out.append(f'<div class="sh-chip"><span class="sh-cf-dot"></span> Strongest two-lens agreement: '
                   f'<a href="/dash/stock?sym={_esc(r["sym"])}">{_esc(r["sym"])}</a> '
                   f'<b>{cnt}</b> of {len(_COLS)} metrics extreme on <b>both</b> its own past &amp; vs peers</div>')
    return f'<div class="sh-chips">{"".join(out)}</div>' if out else ""


def _table(rows: list, u_key: str, sort: str) -> str:
    def hcell(key, label, tip):
        arrow = " ▾" if sort == key else ""
        return (f'<th title="{_esc(tip)}"><a href="/dash/self-history?u={u_key}&sort={key}">'
                f'{_esc(label)}{arrow}</a></th>')

    head = ['<th class="raw" style="text-align:left">'
            f'<a href="/dash/self-history?u={u_key}&sort=sym" style="color:var(--ink-3);text-decoration:none">Stock</a></th>']
    for key, label, tip in _COLS:
        head.append(hcell(key, label, tip))
    head += ['<th class="raw" title="% from own 3-yr high (adjusted)">vs hi</th>',
             '<th class="raw" title="3-month return, adjusted">3m %</th>',
             '<th class="raw" title="latest delivery %">dlv%</th>',
             '<th class="raw" title="turnover, ₹ crore">₹ cr</th>']
    trs = []
    for r in rows:
        tds = [f'<td class="sym"><a href="/dash/stock?sym={_esc(r["sym"])}">{_esc(r["sym"])}</a></td>']
        for key, _lab, _tip in _COLS:
            v = r.get(key)
            cx = r.get("cx_" + key)
            bg, fg = _heat(v)
            main = f'{v:.0f}' if v is not None else 'n/a'
            sub = f'<span class="xs">{cx:.0f}</span>' if cx is not None else ''
            cf = (v is not None and cx is not None
                  and ((v >= 80 and cx >= 80) or (v <= 20 and cx <= 20)))
            tip = (f'{_lab}: {main} vs own 3-yr past'
                   + (f' · {cx:.0f} vs peers today' if cx is not None else ' · self-only (no peer rank)')
                   + (' · CONFLUENCE — extreme on both' if cf else ''))
            tds.append(f'<td class="cell"><div class="b{" cf" if cf else ""}" '
                       f'style="background:{bg};color:{fg}" title="{_esc(tip)}">{main}{sub}</div></td>')
        ret = r.get("ret63")
        rc = "sh-neg" if (ret is not None and ret < 0) else "sh-pos"
        off = r.get("off_hi")
        tds += [
            f'<td class="raw">{off:+.1f}</td>' if off is not None else '<td class="raw mut">–</td>',
            (f'<td class="raw {rc}">{ret:+.1f}</td>' if ret is not None else '<td class="raw mut">–</td>'),
            f'<td class="raw">{r["deliv"]:.0f}</td>' if r.get("deliv") is not None else '<td class="raw mut">–</td>',
            f'<td class="raw mut">{r["turn_cr"]:,.0f}</td>',
        ]
        trs.append(f'<tr>{"".join(tds)}</tr>')
    return (f'<div class="sh-wrap"><table class="sh"><thead><tr>{"".join(head)}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def _csv(rows: list) -> str:
    cols = ["sym", "date",
            "price_pct", "cx_price_pct", "mom_pct", "cx_mom_pct", "deliv_pct", "cx_deliv_pct",
            "turn_pct", "vol_pct", "cx_vol_pct",
            "off_hi", "ret63", "deliv", "turn_cr", "close"]
    out = [",".join(cols)]
    for r in rows:
        out.append(",".join("" if r.get(c) is None else str(r.get(c)) for c in cols))
    return "\n".join(out) + "\n"


@router.get("/dash/self-history", response_class=HTMLResponse)
def dash_self_history(u: str = "nifty50", sort: str = "price_pct", format: str = "") -> HTMLResponse:
    u = u if u in _UNIVERSES else "nifty50"
    sort = sort if sort in _SORTS else "price_pct"
    as_of = ""
    try:
        as_of = _latest_date()
        if not as_of:
            raise LookupError("no bhavcopy_rows")
        rows = _sorted(list(_compute(u, as_of)), sort)
        if not rows:
            raise LookupError("empty universe")
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        empty = (
            '<h2>Own-history map</h2><div class="sh-note">This lens computes each stock\'s '
            'metrics ranked against its <b>own</b> 3-year history, read live from '
            '<code>bhavcopy_rows</code> + <code>stock_index_membership</code>. Those tables are not '
            'populated on this host, so there is nothing to rank yet. Read-only; never fabricates data.</div>')
        return HTMLResponse(_shell("Own-history map · patearn", _CSS + empty, "self-history",
                                   str(as_of)[:10], wide=True))

    if format == "csv":
        return PlainTextResponse(_csv(rows), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="self-history-{u}.csv"'})

    body = [_CSS, ifx.readability_css()]
    body.append(
        '<h2 style="margin:0 0 2px">Own-history map '
        f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">every metric ranked '
        f'0–100 vs each stock\'s own 3-year past · {_esc(_UNIVERSES[u])} · as of {_esc(as_of)}</small></h2>')
    body.append(ifx.bottom_line(
        'Beside "cheap vs the market", ask "extreme <b>vs its own past</b>". Every number below is a '
        '<b>0–100 rank against that same stock\'s own 3-year history</b>, so a giant and a small-cap '
        'read on one scale. A name at its own price-high on <b>15th-percentile turnover</b> is drifting '
        'up on the thinnest trade in three years — a signature a price chart hides.'))
    body.append(ifx.how_to_read_link())
    body.append(
        '<div class="sh-note">Five self-relative reads per stock: <b>Price</b> (where today sits in '
        'its own range), <b>Momentum</b> (3-month return vs its own history), <b>Delivery</b> '
        '(conviction), <b>Turnover</b> (participation), <b>Coil</b> (range — low = wound tight). '
        'Price &amp; momentum are <b>split/bonus-adjusted</b> (raw NSE close would fake a crash on a '
        'bonus); delivery, turnover and range are action-neutral. '
        'Each cell now carries a <b>second number</b>: the <b>big</b> figure ranks the stock vs its '
        'own 3-year past; the <b>small</b> figure ranks it vs its peers <i>today</i>. A '
        '<span class="sh-cf-dot"></span> <b>gold ring</b> marks cells extreme on <b>both</b> — the '
        'two-lens confluence, a stronger read than either alone. (Turnover has no peer rank — raw ₹ '
        'is a size proxy — so it stays self-only.) '
        f'{ifx.fence("not_signal", cap=True)}. '
        '<a href="/dash/glossary?q=cross-sectional percentile">glossary →</a></div>')

    # universe + sort controls (URL-addressable state)
    us = "".join(f'<a class="{"on" if u==k else ""}" href="/dash/self-history?u={k}&sort={sort}">'
                 f'{_esc(v)}</a>' for k, v in _UNIVERSES.items())
    body.append(f'<div class="sh-ctrl">{us}<span class="sep">·</span>'
                f'<span style="color:var(--ink-3);font-size:11px">{len(rows)} names · '
                f'sorted by {_esc(dict((c[0],c[1]) for c in _COLS).get(sort, "symbol"))}</span>'
                f'<span class="sep">·</span>'
                f'<a href="/dash/self-history?u={u}&sort={sort}&format=csv" '
                f'style="border-color:var(--line-2)">Download CSV</a></div>')

    body.append('<div class="sh-key"><span><span class="ramp"></span> 0 = low · 50 = middle · '
                '100 = high</span>'
                '<span><b style="color:var(--ink)">big</b> = vs its own 3-yr past · '
                f'<b style="color:var(--ink)">small</b> = vs peers in {_esc(_UNIVERSES[u])} today · '
                '<span class="sh-cf-dot"></span> = extreme on <b style="color:var(--ink)">both</b></span>'
                '<span>click a header to sort · symbols link to the dossier</span></div>')
    body.append(_chips(rows))
    body.append(_table(rows, u, sort))
    body.append('<div class="sh-note" style="margin-top:10px;color:var(--ink-3);font-size:11.5px">'
                'A self-relative percentile is <b>context, not a forecast</b>: "extreme vs its own past" '
                'says nothing about the next move. No ranking of one stock above another, no buy/sell.</div>')
    return HTMLResponse(_shell("Own-history map · patearn", "".join(body), "self-history",
                               str(as_of)[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/self-history" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    # unit: the pure helpers, no DB
    assert _pct_rank(list(range(200)), 199) == 100.0
    assert _pct_rank(list(range(200)), 0) == 0.5
    assert _pct_rank([1, 2, 3], 3) is None            # too few points
    assert _cross_rank(list(range(20)), 19) == 100.0  # peer lens works at N=20
    assert _cross_rank([1, 2, 3], 3) is None          # too few peers
    bg, fg = _heat(100.0)
    assert bg.startswith("rgb(") and fg in ("#fff", "#23201c")
    assert _heat(None)[0] == "var(--bg-3)"
    assert _sorted([{"sym": "B", "price_pct": 1}, {"sym": "A", "price_pct": 9}], "price_pct")[0]["sym"] == "A"
    assert _csv([{"sym": "X", "date": "2026-01-01", "price_pct": 50}]).splitlines()[0].startswith("sym,date")
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    for url in ("/dash/self-history", "/dash/self-history?u=midcap100&sort=vol_pct",
                "/dash/self-history?u=nifty500&sort=mom_pct",
                "/dash/self-history?u=bogus&sort=bogus", "/dash/self-history?format=csv"):
        r = c.get(url)
        assert r.status_code == 200, (url, r.status_code)
    assert "Own-history map" in c.get("/dash/self-history").text
    print("self_history_view selftest OK — helpers + page 200 (populated or honest-empty) + csv")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
