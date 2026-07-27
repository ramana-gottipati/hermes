"""src/web/home/tracker_reads.py — the Graphite Tracker read layer (lane W3-B, milestone M7).

The Tracker half of the Sideways cutover: six classic surfaces (`dashboard` · `portfolios` ·
`model-books` · `watchlists` · `performance` · `import`) ported into the Graphite idiom. This module
is the DATA half only — it returns plain rows/dicts and NEVER HTML, exactly like `home/reads.py`
(the components/reads split is the package rule; `tracker_pages._compose_*` is the only place the
two meet).

Three standing constraints shaped every read here:

1. **One store, one write path.** Everything reads the canonical D54 lifecycle table
   `stocks_in_play` — the same table `/dash/tracker/*` writes, that `reads.watchlist_rows` reads
   first, and that `POST /dash/home/watch/add` already writes. The Graphite home OWNS the watch-tier
   write; this module adds exactly ONE new write (the bulk importer) and reuses the same validation
   discipline (`bhavcopy_rows` EQ/BE membership, sanitised symbol, parameterised SQL).
2. **Schema-tolerant.** The lifecycle table has grown columns over time (`book`, `qty` are later
   additions and are ABSENT on older/fixture databases). Every read is `SELECT *` + `.get()`, and
   the importer builds its INSERT column list from `PRAGMA table_info` — so a thin host degrades to
   fewer columns instead of raising.
3. **Honest arithmetic.** A money-weighted return (XIRR) needs a dated CASH-FLOW ledger.
   `stocks_in_play` is a POSITION ledger (one row per lot; no partial adds/trims, no dividend
   receipts, no corporate-action adjustment of `qty`). `cashflow_fidelity()` MEASURES that gap on
   the live data instead of asserting it, and the Performance page shows the metrics that survive
   it — a chained TIME-weighted return (needs marks, not cash flows), realised/unrealised ₹ P&L,
   hit-rate, average excess vs the benchmark — and withholds XIRR with the reason. Ratified
   §K.4 asked for the fidelity check FIRST; this is that check.

Isolation: imports nothing from `dashboard`/`shell_skin`/`left_rail`/any `*_v3` render module
(`tests/test_home_isolation.py`). The one cross-module import is `src.web.tracker_gate`, an HTTP
privacy MIDDLEWARE (not a render module) — reused so the demo-book gate is not forked into a second
auth implementation.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from datetime import datetime

from src.web.home.reads import _day_change, _has, _latest_date, _rows

_SIP = "stocks_in_play"
_MAX_IMPORT_ROWS = 500          # a holdings sheet is tens of rows; this is the abuse ceiling
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


# ── schema tolerance ──────────────────────────────────────────────────────────────
def _cols(conn, table: str = _SIP) -> set:
    """The columns a host actually has. `book`/`qty` are later additions — absent on thin DBs."""
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def _sip(conn, status: str) -> list:
    """Every lifecycle row in one tier, newest first. `SELECT *` so a missing column is simply an
    absent key rather than an exception."""
    if not _has(conn, _SIP):
        return []
    return _rows(conn, f"SELECT * FROM {_SIP} WHERE status=? ORDER BY date_added DESC", (status,))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _book_of(r) -> str:
    return (r.get("book") or "Main") if isinstance(r, dict) else "Main"


def _day10(v) -> str:
    return ("" if v is None else str(v))[:10]


def _days_between(d0, d1) -> int | None:
    try:
        return (datetime.fromisoformat(_day10(d1)) - datetime.fromisoformat(_day10(d0))).days
    except (TypeError, ValueError):
        return None


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _snap_close(r):
    """The frozen close captured on the day a name was added (`snapshot_json`) — the then-vs-now
    anchor the classic watchlist shows as 'Price then'. None on any gap."""
    raw = r.get("snapshot_json")
    if not raw:
        return None
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
        return _f(d.get("close")) if isinstance(d, dict) else None
    except (ValueError, TypeError, AttributeError):
        return None


# ── sector labels (the identity spine's 2nd column) ───────────────────────────────
def sectors(conn, symbols) -> dict:
    """{symbol: sector} using the SAME priority as the home heatmap: the canonical NSE
    `stock_signals.primary_sector` first, then the already-harvested `company_about.
    screener_industry` for names in no NSE sectoral index. {} on a thin host."""
    syms = [s for s in (symbols or []) if s]
    if not syms or not _has(conn, "stock_signals"):
        return {}
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return {}
    qs = ",".join("?" * len(syms))
    has_about = _has(conn, "company_about")
    expr = "COALESCE(s.primary_sector, a.screener_industry)" if has_about else "s.primary_sector"
    join = "LEFT JOIN company_about a ON a.symbol=s.symbol" if has_about else ""
    out = {}
    for r in _rows(conn, f"SELECT s.symbol, {expr} AS sector FROM stock_signals s {join} "
                         f"WHERE s.trade_date=? AND s.symbol IN ({qs})", (d, *syms)):
        if r.get("sector"):
            out[r["symbol"]] = r["sector"]
    return out


def rs_reads(conn, symbols) -> dict:
    """{symbol: {'rank','trend','deliv_norm'}} — the live thesis-health inputs the classic tracker
    shows beside every row (RS rank + phase; the name's own 1-month delivery norm). {} if absent."""
    syms = [s for s in (symbols or []) if s]
    if not syms or not _has(conn, "stock_signals"):
        return {}
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return {}
    qs = ",".join("?" * len(syms))
    out = {}
    for r in _rows(conn, f"SELECT symbol, rs_rank, rs_vs_broad_trend_state, avg_deliv_pct_1m "
                         f"FROM stock_signals WHERE trade_date=? AND symbol IN ({qs})", (d, *syms)):
        out[r["symbol"]] = {"rank": r.get("rs_rank"), "trend": r.get("rs_vs_broad_trend_state"),
                            "deliv_norm": r.get("avg_deliv_pct_1m")}
    return out


# ── the position book (Kite-norm column names, Part III §J tracker set) ───────────
def _mark(rows, chg, sec, rs) -> list:
    """Mark a set of lifecycle rows to today's bhav close. Field names follow the Kite norm every
    Indian user already reads: `avg_cost · ltp · cur_val · pnl · day_chg`."""
    today = _today()
    out = []
    for r in rows:
        sym = r.get("symbol")
        c = chg.get(sym, {})
        ltp, day_pct = c.get("close"), c.get("pct")
        avg, qty = _f(r.get("entry_price")), _f(r.get("qty"))
        invested = (avg * qty) if (avg is not None and qty) else None
        cur_val = (ltp * qty) if (ltp is not None and qty) else None
        pnl = (cur_val - invested) if (cur_val is not None and invested is not None) else None
        pnl_pct = ((ltp - avg) / avg * 100.0) if (ltp is not None and avg) else None
        # day P&L in rupees needs the previous close, which _day_change already implies via pct
        day_abs = (cur_val * day_pct / (100.0 + day_pct)) if (cur_val is not None and day_pct is not None
                                                              and (100.0 + day_pct)) else None
        e = rs.get(sym, {})
        out.append({
            "id": r.get("id"), "symbol": sym, "sector": sec.get(sym), "book": _book_of(r),
            "strategy": r.get("strategy"), "date_added": _day10(r.get("date_added")),
            "qty": qty, "avg_cost": avg, "ltp": ltp, "invested": invested, "cur_val": cur_val,
            "pnl": pnl, "pnl_pct": pnl_pct, "day_chg": day_pct, "day_abs": day_abs,
            "target": _f(r.get("price_target")), "stop": _f(r.get("stop_loss")),
            "days": _days_between(r.get("date_added"), today),
            "then": _snap_close(r), "thesis": r.get("entry_thesis"),
            "rank": e.get("rank"), "trend": e.get("trend"), "deliv": c.get("deliv"),
            "deliv_norm": e.get("deliv_norm"),
        })
    return out


def _totals(rows) -> dict:
    inv = sum(r["invested"] for r in rows if r.get("invested"))
    cur = sum(r["cur_val"] for r in rows if r.get("cur_val"))
    day = sum(r["day_abs"] for r in rows if r.get("day_abs"))
    pls = [r["pnl_pct"] for r in rows if r.get("pnl_pct") is not None]
    for r in rows:
        r["weight"] = (r["cur_val"] / cur * 100.0) if (cur and r.get("cur_val")) else None
    return {
        "n": len(rows), "invested": inv or None, "cur_val": cur or None,
        "pnl": (cur - inv) if inv else None,
        "pnl_pct": ((cur - inv) / inv * 100.0) if inv else None,
        "day_abs": day or None, "day_pct": (day / (cur - day) * 100.0) if (cur and (cur - day)) else None,
        # the honest fallback when no position carries qty: the simple average position move
        "avg_move": (sum(pls) / len(pls)) if pls else None,
        "priced": sum(1 for r in rows if r.get("cur_val")),
    }


def positions(conn, book: str = "") -> dict:
    """The open book: marked rows + books + totals. Empty dict-shape (never None) on a thin host."""
    raw = _sip(conn, "open")
    books = sorted({_book_of(r) for r in raw})
    if book:
        raw = [r for r in raw if _book_of(r) == book]
    syms = [r.get("symbol") for r in raw if r.get("symbol")]
    rows = _mark(raw, _day_change(conn, syms), sectors(conn, syms), rs_reads(conn, syms))
    rows.sort(key=lambda r: (r.get("cur_val") or 0.0), reverse=True)
    return {"rows": rows, "books": books, "totals": _totals(rows), "book": book}


def watchlist(conn, book: str = "") -> dict:
    """The watch tier — the SAME `stocks_in_play` status='watch' rows the Graphite home's featured
    watchlist reads and `POST /dash/home/watch/add` writes. One store, one write path."""
    raw = _sip(conn, "watch")
    books = sorted({_book_of(r) for r in raw})
    if book:
        raw = [r for r in raw if _book_of(r) == book]
    syms = [r.get("symbol") for r in raw if r.get("symbol")]
    rows = _mark(raw, _day_change(conn, syms), sectors(conn, syms), rs_reads(conn, syms))
    for r in rows:
        then = r.get("then")
        r["since_add"] = ((r["ltp"] - then) / then * 100.0) if (r.get("ltp") is not None and then) else None
    return {"rows": rows, "books": books, "n": len(rows)}


def closed_trades(conn) -> list:
    """Exited positions with a usable entry AND exit price — the closed-trades log + hit-rate base."""
    raw = [r for r in _sip(conn, "closed")
           if _f(r.get("entry_price")) and _f(r.get("exit_price")) is not None]
    syms = [r.get("symbol") for r in raw if r.get("symbol")]
    sec = sectors(conn, syms)
    out = []
    for r in raw:
        ep, xp, qty = _f(r.get("entry_price")), _f(r.get("exit_price")), _f(r.get("qty"))
        out.append({
            "symbol": r.get("symbol"), "sector": sec.get(r.get("symbol")), "book": _book_of(r),
            "strategy": r.get("strategy"), "date_added": _day10(r.get("date_added")),
            "exit_date": _day10(r.get("exit_date")), "entry": ep, "exit": xp, "qty": qty,
            "pnl": (qty * (xp - ep)) if qty else None,
            "ret_pct": ((xp - ep) / ep * 100.0) if ep else None,
            "days": _days_between(r.get("date_added"), r.get("exit_date")),
            "reason": r.get("exit_reason"),
        })
    out.sort(key=lambda r: r.get("exit_date") or "", reverse=True)
    return out


# ── books + attention (the cockpit blocks) ────────────────────────────────────────
def books_overview(conn) -> list:
    """Per-book roll-up: open · watch · invested · value · ₹ P&L · avg move. The classic cockpit's
    'Books' table, one row per named book."""
    pos, wat = positions(conn), watchlist(conn)
    agg: dict = {}
    for r in pos["rows"]:
        d = agg.setdefault(r["book"], {"book": r["book"], "open": 0, "watch": 0,
                                       "invested": 0.0, "cur_val": 0.0, "moves": []})
        d["open"] += 1
        if r.get("invested"):
            d["invested"] += r["invested"]
        if r.get("cur_val"):
            d["cur_val"] += r["cur_val"]
        if r.get("pnl_pct") is not None:
            d["moves"].append(r["pnl_pct"])
    for r in wat["rows"]:
        agg.setdefault(r["book"], {"book": r["book"], "open": 0, "watch": 0,
                                   "invested": 0.0, "cur_val": 0.0, "moves": []})["watch"] += 1
    out = []
    for b in sorted(agg):
        d = agg[b]
        inv, cur = d["invested"], d["cur_val"]
        out.append({"book": b, "open": d["open"], "watch": d["watch"],
                    "invested": inv or None, "cur_val": cur or None,
                    "pnl": (cur - inv) if inv else None,
                    "avg_move": (sum(d["moves"]) / len(d["moves"])) if d["moves"] else None})
    return out


_ATT_ORDER = ("below_stop", "near_stop", "rs_weak", "concentrated")
_ATT_LABEL = {
    "below_stop":   "below your stop",
    "near_stop":    "within 3% of your stop",
    "rs_weak":      "relative strength has turned weak",
    "concentrated": "over 30% of its book",
}
_WEAK = ("WEAKENING", "LAGGING", "DOWNTREND", "STRONG_DOWNTREND")


def attention(rows) -> list:
    """Descriptive, rule-stated flags over the OPEN book — never a verdict, never advice. Each flag
    is a plain restatement of a number the reader can see in the same table:
    below/near the stop THEY set, an RS phase the tape reports, a concentration share we compute."""
    by_book: dict = {}
    for r in rows:
        if r.get("cur_val"):
            by_book[r["book"]] = by_book.get(r["book"], 0.0) + r["cur_val"]
    out = []
    for r in rows:
        flags = []
        ltp, stop = r.get("ltp"), r.get("stop")
        if ltp is not None and stop:
            if ltp < stop:
                flags.append("below_stop")
            elif ltp <= stop * 1.03:
                flags.append("near_stop")
        if (r.get("trend") or "").upper().strip() in _WEAK:
            flags.append("rs_weak")
        tot = by_book.get(r["book"])
        share = (r["cur_val"] / tot * 100.0) if (tot and r.get("cur_val")) else None
        if share is not None and share > 30.0 and sum(1 for x in rows if x["book"] == r["book"]) > 1:
            flags.append("concentrated")
        if flags:
            flags.sort(key=lambda f: _ATT_ORDER.index(f) if f in _ATT_ORDER else 9)
            out.append({"symbol": r["symbol"], "book": r["book"], "ltp": ltp, "stop": stop,
                        "share": share, "flags": flags,
                        "labels": [_ATT_LABEL[f] for f in flags]})
    out.sort(key=lambda x: _ATT_ORDER.index(x["flags"][0]) if x["flags"][0] in _ATT_ORDER else 9)
    return out


def allocation(rows) -> dict:
    """Weight buckets over the priced part of the book: by sector, by book, plus the top-1/top-3
    concentration pair. Computed from the rows already read — no extra query."""
    tot = sum(r["cur_val"] for r in rows if r.get("cur_val"))
    if not tot:
        return {}

    def bucket(key):
        d: dict = {}
        for r in rows:
            if r.get("cur_val"):
                d[r.get(key) or "—"] = d.get(r.get(key) or "—", 0.0) + r["cur_val"]
        return sorted(({"label": k, "value": v, "pct": v / tot * 100.0} for k, v in d.items()),
                      key=lambda x: x["pct"], reverse=True)

    ws = sorted((r["cur_val"] / tot * 100.0 for r in rows if r.get("cur_val")), reverse=True)
    contrib = sorted(((r["symbol"], (r["weight"] or 0.0) / 100.0 * r["day_chg"])
                      for r in rows if r.get("weight") is not None and r.get("day_chg") is not None),
                     key=lambda x: x[1], reverse=True)
    return {"by_sector": bucket("sector"), "by_book": bucket("book"),
            "top1": ws[0] if ws else None, "top3": sum(ws[:3]) if ws else None,
            "contrib": contrib, "total": tot}


# ── benchmark + the time-weighted curve (the metrics that survive the fidelity check) ──
def benchmark_return(conn, index_name: str, d0: str, d1: str):
    """% move of a broad index between two dates (as-of close on/before each). None on any gap.
    Reads `index_rows`, the historical index table — same source the classic scoreboard uses."""
    if not (d0 and d1) or not _has(conn, "index_rows"):
        return None
    try:
        a = conn.execute("SELECT close_value FROM index_rows WHERE index_name=? AND trade_date<=? "
                         "ORDER BY trade_date DESC LIMIT 1", (index_name, _day10(d0))).fetchone()
        b = conn.execute("SELECT close_value FROM index_rows WHERE index_name=? AND trade_date<=? "
                         "ORDER BY trade_date DESC LIMIT 1", (index_name, _day10(d1))).fetchone()
    except sqlite3.Error:
        return None
    if a and b and a[0]:
        return (b[0] - a[0]) / a[0] * 100.0
    return None


def _index_series(conn, index_name: str, d0: str) -> dict:
    if not _has(conn, "index_rows"):
        return {}
    out = {}
    for r in _rows(conn, "SELECT trade_date, close_value FROM index_rows WHERE index_name=? "
                         "AND trade_date>=? ORDER BY trade_date", (index_name, _day10(d0))):
        if r.get("close_value"):
            out[_day10(r["trade_date"])] = float(r["close_value"])
    return out


def twr_curve(conn, open_rows, closed, benchmark: str = "Nifty 500") -> dict:
    """A CHAINED TIME-WEIGHTED return series for the book — the return metric that does NOT need a
    cash-flow ledger, and therefore the one we can publish honestly.

    Each step is the value change of the names held on BOTH adjacent sessions, so adding or exiting
    a position never fabricates a jump (the flaw in a raw book-value line, where a fresh deposit
    looks like a gain). Chaining those daily factors gives the standard time-weighted index.

    Returns {'dates', 'curve', 'bench', 'ret', 'bench_ret', 'dd', 'dd_peak', 'dd_trough',
    'equal_weight'} — all rebased to 100 at the first day both series exist. {} when the tape or
    the book is too thin to chain honestly (fewer than 2 common sessions).
    """
    holds = []
    equal_weight = False
    for r in list(open_rows or []) + list(closed or []):
        sym, avg = r.get("symbol"), _f(r.get("avg_cost") if "avg_cost" in r else r.get("entry"))
        qty = _f(r.get("qty"))
        if not sym or not r.get("date_added"):
            continue
        if not qty:
            if not avg:
                continue
            qty, equal_weight = 1.0 / avg, True    # equal-RUPEE basis: ₹1 per position at entry
        holds.append({"symbol": sym, "qty": qty, "from": r["date_added"],
                      "to": r.get("exit_date") or None})
    if not holds or not _has(conn, "bhavcopy_rows"):
        return {}
    d0 = min(h["from"] for h in holds)
    syms = sorted({h["symbol"] for h in holds})
    qs = ",".join("?" * len(syms))
    px: dict = {}
    for r in _rows(conn, f"SELECT symbol, trade_date, close FROM bhavcopy_rows WHERE series IN ('EQ','BE') "
                         f"AND trade_date>=? AND symbol IN ({qs}) AND close IS NOT NULL "
                         f"ORDER BY trade_date", (_day10(d0), *syms)):
        px.setdefault(_day10(r["trade_date"]), {})[r["symbol"]] = float(r["close"])
    dates = sorted(px)
    if len(dates) < 2:
        return {}

    def held(h, d):
        return h["from"] <= d and (not h["to"] or d <= h["to"])

    curve, out_dates, level = [], [], 100.0
    for i in range(1, len(dates)):
        dp, dn = dates[i - 1], dates[i]
        num = den = 0.0
        for h in holds:
            if held(h, dp) and held(h, dn):
                a, b = px[dp].get(h["symbol"]), px[dn].get(h["symbol"])
                if a and b:
                    den += h["qty"] * a
                    num += h["qty"] * b
        if den <= 0:
            continue
        if not out_dates:
            out_dates.append(dp)
            curve.append(100.0)
        level *= num / den
        out_dates.append(dn)
        curve.append(level)
    if len(curve) < 2:
        return {}
    bidx = _index_series(conn, benchmark, out_dates[0])
    bench = []
    if bidx:
        base = next((bidx[d] for d in out_dates if d in bidx), None)
        if base:
            last = 100.0
            for d in out_dates:
                if d in bidx:
                    last = bidx[d] / base * 100.0
                bench.append(last)
    peak, dd, dd_p, dd_t = curve[0], 0.0, None, None
    peak_d = out_dates[0]
    for d, v in zip(out_dates, curve):
        if v > peak:
            peak, peak_d = v, d
        drop = (v - peak) / peak * 100.0
        if drop < dd:
            dd, dd_p, dd_t = drop, peak_d, d
    return {"dates": out_dates, "curve": curve, "bench": bench,
            "ret": curve[-1] - 100.0, "bench_ret": (bench[-1] - 100.0) if bench else None,
            "dd": dd if dd < 0 else None, "dd_peak": dd_p, "dd_trough": dd_t,
            "equal_weight": equal_weight, "days": _days_between(out_dates[0], out_dates[-1])}


def _split(strategy) -> list:
    """A position's strategy field is a comma-joined multi-select (D77) — attribute a closed trade
    to EACH component so a combo lands in both rows."""
    s = ("" if strategy is None else str(strategy)).strip()
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts or ["—"]


def _hit_rows(closed, key) -> list:
    agg: dict = {}
    for r in closed:
        keys = _split(r.get("strategy")) if key == "strategy" else [r.get(key) or "—"]
        for k in keys:
            a = agg.setdefault(k, {"k": k, "n": 0, "wins": 0, "ret": 0.0})
            a["n"] += 1
            a["wins"] += 1 if (r.get("ret_pct") or 0) > 0 else 0
            a["ret"] += r.get("ret_pct") or 0.0
    out = [{"k": a["k"], "n": a["n"], "hit": a["wins"] / a["n"] * 100.0, "avg_ret": a["ret"] / a["n"]}
           for a in agg.values() if a["n"]]
    out.sort(key=lambda x: x["n"], reverse=True)
    return out


def performance(conn, benchmark: str = "Nifty 500") -> dict:
    """The scoreboard, built from ONLY what the position ledger can honestly support."""
    pos = positions(conn)
    open_rows, closed = pos["rows"], closed_trades(conn)
    real = sum(r["pnl"] for r in closed if r.get("pnl") is not None) or None
    unreal = sum(r["pnl"] for r in open_rows if r.get("pnl") is not None) or None
    invested = pos["totals"].get("invested")
    total = ((real or 0.0) + (unreal or 0.0)) if (real is not None or unreal is not None) else None
    excess = []
    for r in closed:
        b = benchmark_return(conn, benchmark, r["date_added"], r["exit_date"])
        # attach the per-trade reference too: "+20% over 10 months" means nothing until you know the
        # market did +14% over the same window. That comparison is the Pro column in the trade log.
        r["bench"] = b
        r["excess"] = (r["ret_pct"] - b) if (b is not None and r.get("ret_pct") is not None) else None
        if r["excess"] is not None:
            excess.append(r["excess"])
    days = [r["days"] for r in closed if r.get("days") is not None]
    rets = [r["ret_pct"] for r in closed if r.get("ret_pct") is not None]
    return {
        "n_open": len(open_rows), "n_closed": len(closed),
        "realised": real, "unrealised": unreal, "total_pnl": total, "invested": invested,
        "total_pct": (total / invested * 100.0) if (total is not None and invested) else None,
        "open_move": pos["totals"].get("avg_move"),
        "hit": (sum(1 for r in rets if r > 0) / len(rets) * 100.0) if rets else None,
        "avg_ret": (sum(rets) / len(rets)) if rets else None,
        "best": max(rets) if rets else None, "worst": min(rets) if rets else None,
        "avg_excess": (sum(excess) / len(excess)) if excess else None, "n_excess": len(excess),
        "avg_hold": (sum(days) / len(days)) if days else None,
        "by_strategy": _hit_rows(closed, "strategy"), "by_book": _hit_rows(closed, "book"),
        "curve": twr_curve(conn, open_rows, closed, benchmark),
        "closed": closed, "benchmark": benchmark,
    }


# ── the ratified §K.4 pre-condition: does the store carry cash-flow-grade data? ────
_CA_QTY_CHANGING = ("SPLIT", "BONUS", "CONSOLIDAT", "FACE VALUE", "SUB-DIVISION", "SUBDIVISION")


def cashflow_fidelity(conn) -> dict:
    """MEASURE — never assume — whether `stocks_in_play` supports a money-weighted return (XIRR).

    Part III §K.4 ratified per-book CA-adjusted XIRR as a GOAL, conditional on "a check that dated
    cash-flow data (deposits/rebalances) exists at the fidelity a real XIRR requires". This is that
    check, run against the live rows:

      * `dated`     — rows carrying a usable `date_added` (an XIRR needs a date per flow).
      * `qty`       — rows carrying `qty` (without it there is no rupee flow at all, only a %).
      * `ca_hits`   — held names with a quantity-changing corporate action (split/bonus/consolidation)
                      dated AFTER entry. The stored `qty`/`entry_price` are never re-based for these,
                      so every derived rupee figure for that name is wrong by the ratio.
      * `div_hits`  — held names with a dividend ex-date after entry: real cash received that the
                      ledger never records, so it is missing from any money-weighted return.
      * `lots`      — symbols appearing more than once in a tier: the ledger cannot express an
                      average-in/average-out, so a real transaction history is not reconstructible.

    `verdict` is 'PASS' only when every structural requirement holds AND no un-modelled flow is
    detected. Anything else returns 'FAIL' with the specific reasons — and the Performance page
    withholds XIRR rather than printing a number it cannot back.
    """
    cols = _cols(conn)
    rows = _sip(conn, "open") + _sip(conn, "closed")
    n = len(rows)
    dated = sum(1 for r in rows if _day10(r.get("date_added")))
    with_qty = sum(1 for r in rows if _f(r.get("qty")))
    seen: dict = {}
    for r in rows:
        seen[r.get("symbol")] = seen.get(r.get("symbol"), 0) + 1
    lots = sum(1 for k, v in seen.items() if v > 1)
    ca_seen, div_seen, ca_checked = set(), set(), _has(conn, "corporate_actions")
    if ca_checked and rows:
        # Count distinct ACTIONS touching a held name, not (position × action) — two lots of the
        # same symbol share one bonus issue, and reporting it twice would overstate the damage.
        for r in rows:
            sym, d0 = r.get("symbol"), _day10(r.get("date_added"))
            if not sym or not d0:
                continue
            end = _day10(r.get("exit_date")) or _today()
            for a in _rows(conn, "SELECT action_type, ex_date FROM corporate_actions WHERE symbol=? "
                                 "AND ex_date>? AND ex_date<=?", (sym, d0, end)):
                t = str(a.get("action_type") or "").upper()
                keyed = (sym, t, _day10(a.get("ex_date")))
                if any(k in t for k in _CA_QTY_CHANGING):
                    ca_seen.add(keyed)
                elif "DIVIDEND" in t:
                    div_seen.add(keyed)
    ca_hits, div_hits = len(ca_seen), len(div_seen)
    reasons = []
    if not n:
        reasons.append("no closed or open positions yet — nothing to measure a return over")
    if "qty" not in cols:
        reasons.append("this database has no `qty` column, so no rupee cash flow exists at all")
    elif n and with_qty < n:
        reasons.append(f"{n - with_qty} of {n} positions carry no quantity, so their rupee flow is unknown")
    if n and dated < n:
        reasons.append(f"{n - dated} of {n} positions carry no entry date")
    if lots:
        reasons.append(f"{lots} symbol(s) appear as several rows — the ledger stores lots, not "
                       "dated buy/sell transactions, so averaging in or out cannot be reconstructed")
    if ca_hits:
        reasons.append(f"{ca_hits} corporate action(s) that change share count (split/bonus/"
                       "consolidation) fall after an entry date, and stored quantity is never re-based")
    if div_hits:
        reasons.append(f"{div_hits} dividend ex-date(s) fall inside a holding period — real cash the "
                       "ledger does not record")
    if not ca_checked:
        reasons.append("the corporate-actions feed is absent on this host, so CA adjustment cannot "
                       "even be checked")
    return {"n": n, "dated": dated, "with_qty": with_qty, "lots": lots,
            "ca_hits": ca_hits, "div_hits": div_hits, "ca_checked": ca_checked,
            "verdict": "PASS" if not reasons else "FAIL", "reasons": reasons}


def _flows(conn) -> list:
    """The dated cash flows an XIRR needs: a negative flow at every entry, a positive one at every
    exit, and the terminal market value of what is still open, dated today. [] when a position
    lacks a date or a quantity (in which case there is no rupee flow to place)."""
    out = []
    pos = positions(conn)
    for r in pos["rows"]:
        if r.get("date_added") and r.get("qty") and r.get("avg_cost"):
            out.append((r["date_added"], -r["qty"] * r["avg_cost"]))
    terminal = sum(r["cur_val"] for r in pos["rows"] if r.get("cur_val"))
    for r in closed_trades(conn):
        if r.get("date_added") and r.get("qty") and r.get("entry"):
            out.append((r["date_added"], -r["qty"] * r["entry"]))
        if r.get("exit_date") and r.get("qty") and r.get("exit"):
            out.append((r["exit_date"], r["qty"] * r["exit"]))
    if terminal:
        out.append((_today(), terminal))
    return sorted(out)


def xirr(conn, guard: bool = True):
    """Money-weighted annual return (%) over the dated flows — returned ONLY when
    `cashflow_fidelity()` passes, because an XIRR over an incomplete flow set is a confident-looking
    wrong number. Solved by bisection on the NPV (no external dependency, no divergence risk that a
    Newton step carries on irregular flows). None when unsolvable or when the guard blocks it."""
    if guard and cashflow_fidelity(conn).get("verdict") != "PASS":
        return None
    flows = _flows(conn)
    if len(flows) < 2:
        return None
    try:
        t0 = datetime.fromisoformat(flows[0][0])
        pts = [(((datetime.fromisoformat(d) - t0).days / 365.0), float(a)) for d, a in flows]
    except (TypeError, ValueError):
        return None
    if not (any(a < 0 for _t, a in pts) and any(a > 0 for _t, a in pts)):
        return None

    def npv(r):
        try:
            return sum(a / ((1.0 + r) ** t) for t, a in pts)
        except (OverflowError, ZeroDivisionError):
            return float("inf")

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0 * 100.0


# ── the importer: file / paste → parse → validate → preview → commit ──────────────
_HEAD_SYM = ("symbol", "ticker", "scrip", "instrument", "stock", "name", "nse")
_HEAD_QTY = ("qty", "quantity", "shares", "units", "holding")
_HEAD_PX = ("avg", "cost", "price", "buy", "entry", "rate")
_HEAD_DATE = ("date", "added", "bought", "purchase")
_HEAD_NOTE = ("strategy", "note", "thesis", "remark", "tag")


def _sniff(text: str) -> str:
    head = "\n".join(text.splitlines()[:5])
    for d in ("\t", ";", "|", ","):
        if head.count(d) >= 1:
            return d
    return ","


def _match(cell: str, keys) -> bool:
    c = (cell or "").strip().lower()
    return any(k in c for k in keys)


def _numify(v):
    """'₹1,320.50' / '1 320,50' / '(25)' → float. None when it is not a number."""
    s = re.sub(r"[^0-9.\-]", "", ("" if v is None else str(v)).replace(",", ""))
    if s in ("", "-", ".", "-."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _datify(v):
    """Best-effort date → ISO 'YYYY-MM-DD'. Accepts ISO, dd-mm-yyyy, dd/mm/yy. None if unreadable."""
    s = ("" if v is None else str(v)).strip()[:10]
    if not s:
        return None
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        y, mo, d = m.groups()
    else:
        m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})$", s)
        if not m:
            return None
        d, mo, y = m.groups()
        y = ("20" + y) if len(y) == 2 else y
    try:
        return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_holdings(text: str) -> dict:
    """ANY layout, no template required: sniff the delimiter, detect a header row by keyword, map
    Symbol · Qty · Avg cost · Entry date · Note; fall back to positional order when there is no
    header. Pure — no DB, no HTML. Returns {'rows', 'header', 'mapping', 'truncated'}."""
    text = (text or "").strip()
    if not text:
        return {"rows": [], "header": None, "mapping": {}, "truncated": False}
    rdr = csv.reader(io.StringIO(text), delimiter=_sniff(text))
    raw = [r for r in rdr if any((c or "").strip() for c in r)]
    if not raw:
        return {"rows": [], "header": None, "mapping": {}, "truncated": False}
    head, body, mapping = None, raw, {}
    first = raw[0]
    if any(_match(c, _HEAD_SYM) for c in first) and not _numify(first[-1]):
        head, body = first, raw[1:]
        # One column claims at most ONE field, and DATE outranks PRICE — otherwise a header like
        # "Entry Date | Entry Price" hands both fields to column 1 (the word "entry" is in both key
        # sets) and the price silently becomes a date string.
        for i, c in enumerate(head):
            for name, keys in (("symbol", _HEAD_SYM), ("qty", _HEAD_QTY), ("date", _HEAD_DATE),
                               ("price", _HEAD_PX), ("note", _HEAD_NOTE)):
                if name not in mapping and _match(c, keys):
                    mapping[name] = i
                    break
    if not mapping:
        mapping = {"symbol": 0, "date": 1, "price": 2, "qty": 3, "note": 4}
    truncated = len(body) > _MAX_IMPORT_ROWS
    out = []
    for r in body[:_MAX_IMPORT_ROWS]:
        def cell(k):
            i = mapping.get(k)
            return r[i] if (i is not None and i < len(r)) else None
        sym = re.sub(r"[^A-Z0-9&.\-]", "", str(cell("symbol") or "").strip().upper())[:24]
        out.append({"symbol": sym, "qty": _numify(cell("qty")), "price": _numify(cell("price")),
                    "date": _datify(cell("date")), "note": (str(cell("note") or "").strip())[:80],
                    "raw": " · ".join(str(c).strip() for c in r if str(c).strip())[:120]})
    return {"rows": out, "header": head, "mapping": mapping, "truncated": truncated}


def validate_rows(conn, rows, status: str = "open") -> dict:
    """Mark every parsed row against reality — the SAME membership test `reads.watch_add` applies:
    a real, recently-traded NSE cash symbol (EQ/BE in `bhavcopy_rows`). Never trusts the file."""
    syms = sorted({r["symbol"] for r in rows if r.get("symbol")})
    known, dup = set(), set()
    if syms and _has(conn, "bhavcopy_rows"):
        qs = ",".join("?" * len(syms))
        known = {r["symbol"] for r in _rows(
            conn, f"SELECT DISTINCT symbol FROM bhavcopy_rows WHERE series IN ('EQ','BE') "
                  f"AND symbol IN ({qs})", tuple(syms))}
    if syms and _has(conn, _SIP):
        qs = ",".join("?" * len(syms))
        dup = {r["symbol"] for r in _rows(
            conn, f"SELECT DISTINCT symbol FROM {_SIP} WHERE status=? AND symbol IN ({qs})",
            (status, *syms))}
    ok = bad = skip = 0
    for r in rows:
        if not r.get("symbol"):
            r["state"], r["why"] = "bad", "no symbol in this row"
        elif r["symbol"] not in known:
            r["state"], r["why"] = "bad", "not a recognised NSE cash symbol (EQ/BE)"
        elif r["symbol"] in dup:
            r["state"], r["why"] = "skip", "already in this list"
        elif status == "open" and not r.get("price"):
            r["state"], r["why"] = "bad", "an entry price is required for a portfolio row"
        else:
            r["state"], r["why"] = "ok", ""
        ok += r["state"] == "ok"
        bad += r["state"] == "bad"
        skip += r["state"] == "skip"
    return {"rows": rows, "ok": ok, "bad": bad, "skip": skip, "n": len(rows)}


def commit_rows(conn, rows, status: str = "open", book: str = "Main") -> tuple:
    """Write the validated rows into the canonical lifecycle table. Parameterised throughout; the
    column list is derived from the host's own schema so a DB without `book`/`qty` still imports.
    Returns (written, skipped). Defensive — never raises."""
    status = status if status in ("open", "watch") else "open"
    book = re.sub(r"[^\w \-&.]", "", (book or "Main").strip())[:40] or "Main"
    cols = _cols(conn)
    written = skipped = 0
    for r in rows:
        if r.get("state") != "ok":
            skipped += 1
            continue
        fields = {"symbol": r["symbol"], "strategy": (r.get("note") or "Imported")[:60],
                  "status": status}
        if "book" in cols:
            fields["book"] = book
        if r.get("price") is not None:
            fields["entry_price"] = r["price"]
        if r.get("qty") is not None and "qty" in cols:
            fields["qty"] = r["qty"]
        if r.get("date"):
            fields["date_added"] = r["date"]
        names = ",".join(fields)
        marks = ",".join("?" * len(fields))
        try:
            conn.execute(f"INSERT INTO {_SIP}({names}) VALUES ({marks})", tuple(fields.values()))
            written += 1
        except sqlite3.Error:
            skipped += 1
    return (written, skipped)


def template_csv() -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Symbol", "Entry Date", "Entry Price", "Qty", "Strategy"])
    w.writerow(["RELIANCE", "2026-01-15", "1320.50", "25", "Quality"])
    w.writerow(["BANDHANBNK", "2026-02-03", "190", "100", "RS leader"])
    return out.getvalue()


def export_csv(conn, view: str = "portfolio", book: str = "") -> tuple:
    """Server-side CSV (playbook §3.8 — never a DOM blob). Leading columns mirror the import
    template so an export re-imports cleanly. Returns (filename, text)."""
    today = _today()
    out = io.StringIO()
    w = csv.writer(out)
    if view == "watchlist":
        w.writerow(["Symbol", "Added Date", "Strategy", "Book", "Price When Added", "LTP",
                    "Change % Since Added", "Target", "Stop", "Sector"])
        for r in watchlist(conn, book)["rows"]:
            w.writerow([r["symbol"], r["date_added"], r["strategy"] or "", r["book"],
                        _csvnum(r.get("then")), _csvnum(r.get("ltp")), _csvnum(r.get("since_add"), 1),
                        _csvnum(r.get("target")), _csvnum(r.get("stop")), r.get("sector") or ""])
    elif view == "closed":
        w.writerow(["Symbol", "Entry Date", "Entry Price", "Qty", "Strategy", "Book", "Exit Date",
                    "Exit Price", "Return %", "Rs P&L", "Days", "Reason"])
        for r in closed_trades(conn):
            w.writerow([r["symbol"], r["date_added"], _csvnum(r["entry"]), _csvnum(r.get("qty"), 0),
                        r["strategy"] or "", r["book"], r["exit_date"], _csvnum(r["exit"]),
                        _csvnum(r.get("ret_pct"), 1), _csvnum(r.get("pnl"), 0),
                        (str(r["days"]) if r.get("days") is not None else ""), r.get("reason") or ""])
    else:
        view = "portfolio"
        w.writerow(["Symbol", "Entry Date", "Entry Price", "Qty", "Strategy", "Book", "LTP",
                    "Cur. val", "P&L", "P&L %", "Day chg. %", "Sector", "Target", "Stop", "Days"])
        for r in positions(conn, book)["rows"]:
            w.writerow([r["symbol"], r["date_added"], _csvnum(r.get("avg_cost")), _csvnum(r.get("qty"), 0),
                        r["strategy"] or "", r["book"], _csvnum(r.get("ltp")), _csvnum(r.get("cur_val"), 0),
                        _csvnum(r.get("pnl"), 0), _csvnum(r.get("pnl_pct"), 1), _csvnum(r.get("day_chg"), 2),
                        r.get("sector") or "", _csvnum(r.get("target")), _csvnum(r.get("stop")),
                        (str(r["days"]) if r.get("days") is not None else "")])
    tag = re.sub(r"[^A-Za-z0-9]+", "-", book).strip("-") if book else "all"
    return (f"patearn-tracker-{view}-{tag}-{today}.csv", out.getvalue())


def _csvnum(v, d: int = 2) -> str:
    return "" if v is None else f"{round(float(v), d):g}"


# ── the demo book (the anonymous state) ───────────────────────────────────────────
def _demo_source() -> tuple:
    """The ONE demo book, reused from `tracker_gate` (the classic gate's synthetic positions) so the
    public demo tells the same story on both experiences. Falls back to a local copy if the module
    is unavailable — the demo must never be the reason a page 500s."""
    try:
        from src.web import tracker_gate as TG
        return (list(TG._DEMO_POSITIONS), list(TG._DEMO_WATCH))
    except Exception:  # noqa: BLE001
        return ([("RELIANCE", 10, 1180.0, "2026-04-08"), ("TCS", 5, 3620.0, "2026-03-20"),
                 ("HDFCBANK", 12, 1512.0, "2026-05-05"), ("INFY", 15, 1385.0, "2026-02-14"),
                 ("TATAPOWER", 40, 372.0, "2026-06-02"), ("PCBL", 25, 268.0, "2026-06-18")],
                ["BHEL", "KAJARIACER", "LAURUSLABS"])


def demo_positions(conn) -> dict:
    """The demo book, marked to LIVE prices where the tape has them (honest: the positions are
    invented, the prices/sector/RS reads are real — the exact framing the classic demo uses)."""
    pos, _watch = _demo_source()
    raw = [{"id": None, "symbol": s, "qty": q, "entry_price": p, "date_added": d,
            "strategy": "Demo", "book": "Demo book", "status": "open"} for s, q, p, d in pos]
    syms = [r["symbol"] for r in raw]
    rows = _mark(raw, _day_change(conn, syms), sectors(conn, syms), rs_reads(conn, syms))
    for r in rows:                    # a thin/late tape must still produce a legible demo
        if r.get("ltp") is None and r.get("avg_cost"):
            r["ltp"] = r["avg_cost"]
            r["cur_val"] = r["avg_cost"] * (r.get("qty") or 0)
            r["invested"] = r["cur_val"]
            r["pnl"], r["pnl_pct"] = 0.0, 0.0
    return {"rows": rows, "books": ["Demo book"], "totals": _totals(rows), "book": ""}


def demo_watchlist(conn) -> dict:
    _pos, watch = _demo_source()
    raw = [{"id": None, "symbol": s, "strategy": "Demo", "book": "Demo book",
            "date_added": "2026-06-30", "status": "watch"} for s in watch]
    syms = [r["symbol"] for r in raw]
    rows = _mark(raw, _day_change(conn, syms), sectors(conn, syms), rs_reads(conn, syms))
    for r in rows:
        r["since_add"] = None
    return {"rows": rows, "books": ["Demo book"], "n": len(rows)}


def _selftest() -> int:
    """Pure-function checks that need no database."""
    p = parse_holdings("Symbol,Entry Date,Entry Price,Qty,Strategy\nRELIANCE,2026-01-15,1320.50,25,Quality\n")
    assert p["rows"] and p["rows"][0]["symbol"] == "RELIANCE", p
    assert p["rows"][0]["qty"] == 25 and p["rows"][0]["price"] == 1320.50
    assert p["rows"][0]["date"] == "2026-01-15", p["rows"][0]
    q = parse_holdings("TCS\t10\t3600\nINFY\t5\t1400")           # no header, tab-delimited
    assert q["rows"][0]["symbol"] == "TCS", q
    bad = parse_holdings("Symbol,Qty\n<script>alert(1)</script>,5")
    assert "<" not in bad["rows"][0]["symbol"], bad["rows"][0]
    assert _numify("₹1,320.50") == 1320.50 and _numify("abc") is None
    assert _datify("15/01/2026") == "2026-01-15" and _datify("nope") is None
    assert _split("DVPT accumulation, RS leader") == ["DVPT accumulation", "RS leader"]
    assert _csvnum(None) == "" and _csvnum(1.50) == "1.5"
    print("tracker_reads selftest OK — any-layout parse, sanitised symbols, date/number coercion")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
