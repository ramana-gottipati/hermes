"""src/web/home/internals_reads.py — the Graphite Markets-estate read layer (lane W2-A).

The data half of the four consolidated Graphite Markets pages (`internals_pages.py`): market
internals · flows & positioning · events & restrictions · what changed. Same contract as
`reads.py` — **plain rows/dicts only, never HTML**, every read bounded + defensive (a missing
table returns an empty result, never an exception), and NO import of any preview/legacy render
module (`tests/test_home_isolation.py` scans this file too).

Reuse, not rebuild (SURFACE-PLAYBOOK sister-data rule). Where the Graphite home already owns a
read, this module CALLS it rather than re-querying:

  * FII/DII cash flows      -> `reads.fii_dii_recent` / `reads.fii_dii_deep`
  * corporate actions       -> `reads.upcoming_ca` (which wraps `corp_actions.upcoming`)
  * results calendar        -> `reads.upcoming_results`
  * alert severity counts   -> `reads.severity_counts`
  * the surveillance/band-lock/alert-rail cohorts -> the canonical `src.automation.*` engines
    (`surveillance.transitions` · `band_lock.active_streaks` · `signal_alerts.active_alerts`),
    so the ranking/flag logic stays single-sourced exactly as the classic pages have it.

Only where no shared read exists is there new SQL here, and it is the same bounded shape the
classic lens used. The market-internals series is loaded ONCE per request and both the display
window and the percentile reference are derived from that single load — the reference grammar is
the home's (`reads.internals_reference` = the 4-metric twin), extended here with coil.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.web.home import reads

# ── generic, defensive helpers (local copies — no coupling to reads' privates) ────────
_MAX_ROWS = 4000            # hard cap on anything that could grow unbounded


def _has(conn, table: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def _rows(conn, sql: str, params=()) -> list:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error:
        return []


def _one(conn, sql: str, params=()):
    try:
        r = conn.execute(sql, params).fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None


def _f(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _median(vals) -> Optional[float]:
    v = sorted(x for x in (_f(z) for z in vals) if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def _pctile(vals, x, minpts: int = 250) -> Optional[float]:
    """Percentile 0..100 of x within `vals` (share of history <= x). None when the history is
    too thin to be an honest reference — the same refusal-to-fabricate rule as reads._pctile."""
    xf = _f(x)
    v = [z for z in (_f(y) for y in vals) if z is not None]
    if xf is None or len(v) < minpts:
        return None
    return 100.0 * sum(1 for z in v if z <= xf) / len(v)


def _ref(vals, x, minpts: int = 250) -> dict:
    """{'pctile','typical','n'} — the shape components.ref_chip consumes. {} when too thin."""
    v = [z for z in (_f(y) for y in vals) if z is not None]
    p = _pctile(v, x, minpts)
    if p is None:
        return {}
    return {"pctile": p, "typical": _median(v), "n": len(v)}


def _trend(series, back: int = 5) -> Optional[str]:
    """'up' / 'down' / 'flat' from the last `back` points — a factual direction, not a judgment."""
    v = [z for z in (_f(y) for y in series) if z is not None]
    if len(v) < back + 1:
        return None
    d = v[-1] - v[-1 - back]
    scale = abs(v[-1 - back]) or 1.0
    if d > 0.02 * scale:
        return "up"
    if d < -0.02 * scale:
        return "down"
    return "flat"


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — MARKET INTERNALS  (ports /dash/market-internals + /dash/divergence)
# ══════════════════════════════════════════════════════════════════════════════════════
# The five absolute market-state series over the bounded `market_internals_daily` snapshot
# (one row per trading day, 2004->). Descriptive market-state, point-in-time: breadth is not
# an index return, and the tape is within-stock-normalised (a breadth of accumulation, not
# price direction). Not a signal — no ranking, no "buy".
INTERNALS_METRICS = (
    # (key, column, label, unit, dp, low-word, high-word)
    ("breadth",  "pct_adv",  "Stocks advancing",  "%", 0, "narrow", "broad"),
    ("tape",     "mep_net",  "The tape",          "",  0, "distributing", "accumulating"),
    ("delivery", "avg_dp",   "Delivery conviction", "%", 0, "thin", "heavy"),
    ("disp",     "disp",     "Dispersion",        "",  2, "macro market", "stock-picker's market"),
    ("coil",     "avg_comp", "Coil",              "×", 2, "coiled", "expanded"),
)

INTERNALS_WINDOWS = {"1y": 252, "3y": 756, "5y": 1260, "all": 100_000}

# Validated crisis / thrust anchors — the proof the internals track known history. Dates only;
# every number beside them is read live from the snapshot (nothing is hard-coded).
INTERNALS_ANCHORS = (
    ("2008-10-24", "GFC crash low"),
    ("2009-05-18", "Election upper-circuit thrust"),
    ("2020-03-23", "COVID low"),
    ("2021-10-19", "2021 bull peak (approx)"),
    ("2024-06-04", "Election-result shock"),
)


def internals_pack(conn, window: str = "1y") -> dict:
    """One load of `market_internals_daily` -> the display window, the full-history reference for
    each of the five metrics, and the recent-session strip the day-drill hangs off.

    {} when the snapshot is absent (honest empty state — this layer never fabricates a series).
    The reference is computed from the SAME rows the charts draw, so a shown number and its
    percentile can never disagree (the invariant reads.internals_reference states)."""
    if not _has(conn, "market_internals_daily"):
        return {}
    allrows = _rows(conn, "SELECT d, n_eq, adv, dec, unch, pct_adv, avg_dp, disp, mep_net, avg_comp "
                          "FROM market_internals_daily WHERE pct_adv IS NOT NULL ORDER BY d")
    if not allrows:
        return {}
    n = INTERNALS_WINDOWS.get(window, INTERNALS_WINDOWS["1y"])
    rows = allrows[-n:] if n < len(allrows) else allrows
    latest = allrows[-1]
    refs, values = {}, {}
    for key, col, _lab, _u, _dp, _lo, _hi in INTERNALS_METRICS:
        series = [r.get(col) for r in allrows]
        values[key] = _f(latest.get(col))
        refs[key] = _ref(series, latest.get(col))
        refs[key]["trend"] = _trend([r.get(col) for r in allrows[-40:]])
    anchors = []
    for d, label in INTERNALS_ANCHORS:
        hit = next((r for r in allrows if (r.get("d") or "") == d), None)
        if hit:
            anchors.append({"d": d, "label": label, **hit})
    return {"rows": rows, "all_n": len(allrows), "as_of": latest.get("d"), "latest": latest,
            "values": values, "refs": refs, "anchors": anchors,
            "sessions": [r.get("d") for r in allrows[-30:]]}


def internals_drill(conn, d: str, limit: int = 8) -> dict:
    """One session's biggest movers by DELIVERED value — the texture behind a breadth number.
    Bounded to a single trade_date over `bhavcopy_rows` (EQ only, the delivery-honesty rule).
    {} when the date is absent."""
    day = str(d or "").strip()[:10]
    if not day or not _has(conn, "bhavcopy_rows"):
        return {}
    rows = _rows(conn,
                 "SELECT symbol, close, prev_close, deliv_qty FROM bhavcopy_rows "
                 "WHERE trade_date=? AND series='EQ' AND prev_close>0 AND close>0 LIMIT ?",
                 (day, _MAX_ROWS))
    out = []
    for r in rows:
        try:
            chg = (r["close"] / r["prev_close"] - 1.0) * 100.0
        except (TypeError, ZeroDivisionError):
            continue
        dval = (_f(r.get("deliv_qty")) or 0.0) * (_f(r.get("close")) or 0.0)
        out.append({"symbol": r.get("symbol"), "chg": chg, "dval": dval})
    if not out:
        return {}
    out.sort(key=lambda z: -z["dval"])
    top = out[:400]                      # rank movers among the day's genuinely-traded names
    up = sorted([z for z in top if z["chg"] > 0], key=lambda z: -z["chg"])[:limit]
    dn = sorted([z for z in top if z["chg"] < 0], key=lambda z: z["chg"])[:limit]
    return {"d": day, "up": up, "down": dn, "n": len(out)}


RS_BENCH = "Nifty 500"


def rs_divergence(conn, bench: str = RS_BENCH, limit: int = 10) -> dict:
    """The RSI-of-RS divergence watch board (ports /dash/divergence): the most recent flagged bar
    per sector/index, split bullish (RS lower-low, RSI higher-low) vs bearish, plus the RSI-of-RS
    extremes strip. Reads the ALREADY-COMPUTED `rs_extras` flags — no recompute.
    DESCRIPTIVE early-warning characterization, never a buy/sell signal."""
    out = {"bull": [], "bear": [], "oversold": [], "overbought": [], "bench": bench}
    if not _has(conn, "rs_extras"):
        return out
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(rs_extras)").fetchall()}
    except sqlite3.Error:
        return out
    if not {"numerator", "trade_date", "rs_div_bull", "rs_div_bear"} <= cols:
        return out
    rsi_sel = "rsi_of_rs" if "rsi_of_rs" in cols else "NULL AS rsi_of_rs"
    rows = _rows(conn, f"SELECT numerator, trade_date, {rsi_sel}, rs_div_bull, rs_div_bear "
                       "FROM rs_extras WHERE denominator=? AND (rs_div_bull=1 OR rs_div_bear=1) "
                       "ORDER BY trade_date DESC LIMIT ?", (bench, _MAX_ROWS))
    seen = set()
    for r in rows:
        num = r.get("numerator")
        if not num or num in seen:
            continue
        seen.add(num)
        item = {"name": num, "date": r.get("trade_date"), "rsi": r.get("rsi_of_rs")}
        (out["bull"] if r.get("rs_div_bull") else out["bear"]).append(item)
    out["bull"] = out["bull"][:limit]
    out["bear"] = out["bear"][:limit]
    if "rsi_of_rs" in cols:
        ext = _rows(conn, "SELECT numerator, rsi_of_rs FROM rs_extras WHERE denominator=? "
                          "AND rsi_of_rs IS NOT NULL ORDER BY rsi_of_rs LIMIT ?",
                    (bench, _MAX_ROWS))
        out["oversold"] = [{"name": r["numerator"], "rsi": r["rsi_of_rs"]}
                           for r in ext if (_f(r["rsi_of_rs"]) or 50) < 40][:6]
        out["overbought"] = [{"name": r["numerator"], "rsi": r["rsi_of_rs"]}
                             for r in reversed(ext) if (_f(r["rsi_of_rs"]) or 50) > 60][:6]
    return out


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — FLOWS & POSITIONING  (ports /dash/participants + /dash/fno)
# ══════════════════════════════════════════════════════════════════════════════════════
PARTICIPANTS = (("FII", "FII (foreign)"), ("DII", "DII (domestic institutions)"),
                ("PRO", "Pro (prop desks)"), ("CLIENT", "Client (retail + HNI)"))


def _net(a, b) -> Optional[float]:
    fa, fb = _f(a), _f(b)
    return None if (fa is None or fb is None) else (fa - fb)


def _ratio(a, b) -> Optional[float]:
    fa, fb = _f(a), _f(b)
    return (fa / fb) if (fa and fb) else None


def participants_pack(conn, hist_n: int = 40) -> dict:
    """Market-AGGREGATE derivatives positioning from `participant_oi` (NSE participant-wise OI,
    published daily after close): today's row per client type, the FII index-futures long:short
    stance ranked against its OWN full stored history, and the FII-vs-retail mirror.
    Descriptor / sentiment context (D62) — never a standalone timing signal. {} if absent."""
    if not _has(conn, "participant_oi"):
        return {}
    d = _one(conn, "SELECT MAX(trade_date) FROM participant_oi")
    if not d:
        return {}
    today = {r.get("client_type"): r for r in
             _rows(conn, "SELECT * FROM participant_oi WHERE trade_date=?", (d,))}
    if not today:
        return {}
    full = _rows(conn, "SELECT trade_date, client_type, fut_idx_long, fut_idx_short "
                       "FROM participant_oi WHERE client_type IN ('FII','CLIENT') "
                       "ORDER BY trade_date LIMIT ?", (_MAX_ROWS * 2,))
    dates, fii_ls, fii_net, cli_net = [], {}, {}, {}
    for r in full:
        dt, ct = r.get("trade_date"), r.get("client_type")
        if ct == "FII":
            if dt not in fii_net:
                dates.append(dt)
            fii_net[dt] = _net(r.get("fut_idx_long"), r.get("fut_idx_short"))
            fii_ls[dt] = _ratio(r.get("fut_idx_long"), r.get("fut_idx_short"))
        else:
            cli_net[dt] = _net(r.get("fut_idx_long"), r.get("fut_idx_short"))
    dates = sorted(set(x for x in dates if x))
    ratio_series = [fii_ls.get(x) for x in dates]
    ratio_hist = [x for x in ratio_series if x is not None]
    latest_ratio = ratio_hist[-1] if ratio_hist else None
    # the stance percentile needs a real history; <60 stored days is too thin to call "extreme"
    stance_ref = _ref(ratio_hist, latest_ratio, minpts=60)

    rows = []
    for ct, label in PARTICIPANTS:
        r = today.get(ct) or {}
        try:
            obias = ((_f(r.get("opt_idx_call_long")) or 0) + (_f(r.get("opt_idx_put_short")) or 0)
                     - (_f(r.get("opt_idx_call_short")) or 0) - (_f(r.get("opt_idx_put_long")) or 0))
        except (TypeError, ValueError):
            obias = None
        rows.append({"key": ct, "label": label,
                     "idx_net": _net(r.get("fut_idx_long"), r.get("fut_idx_short")),
                     "ls": _ratio(r.get("fut_idx_long"), r.get("fut_idx_short")),
                     "stk_net": _net(r.get("fut_stk_long"), r.get("fut_stk_short")),
                     "opt_bias": obias if r else None})
    fii = next((z for z in rows if z["key"] == "FII"), {})
    cli = next((z for z in rows if z["key"] == "CLIENT"), {})
    fn, cn = fii.get("idx_net"), cli.get("idx_net")
    return {"as_of": d, "rows": rows, "ratio": latest_ratio, "ratio_ref": stance_ref,
            "ratio_series": ratio_series[-hist_n:], "n_hist": len(ratio_hist),
            "fii_net": fn, "client_net": cn,
            "opposite": (fn is not None and cn is not None and (fn > 0) != (cn > 0)),
            "history": [{"d": x, "net": fii_net.get(x), "ls": fii_ls.get(x)}
                        for x in dates[-8:]][::-1]}


def participant_stance_word(ratio) -> str:
    """Plain-English label for the FII index-futures long:short ratio. The 0.9-1.1 band reads as
    balanced (Codex D8-F3: the read must track the computed ratio, never a hard-coded sentence)."""
    r = _f(ratio)
    if r is None:
        return "unavailable"
    if r < 0.6:
        return "strongly net-short"
    if r < 0.9:
        return "leaning net-short"
    if r > 1.7:
        return "strongly net-long"
    if r > 1.1:
        return "leaning net-long"
    return "balanced"


FNO_MINPTS = 60          # >=60 own-history points (~3 months) before a percentile is honest
FNO_SORTS = ("oi_pct", "pcr_pct", "dist_pct", "streak", "sym", "oi")
FNO_QUADRANTS = {
    "LONG_BUILDUP": "long buildup", "SHORT_BUILDUP": "short buildup",
    "LONG_UNWIND": "long unwind", "SHORT_COVER": "short cover", "FLAT": "flat",
}


def _signed_dist(und, mp) -> Optional[float]:
    u, m = _f(und), _f(mp)
    if u is None or not m:
        return None
    return round((u / m - 1.0) * 100.0, 2)


def _fno_row(sym: str, series: list) -> Optional[dict]:
    """One board row from a symbol's fno_oi_signals history (OLDEST->newest): today's reads plus
    each read's percentile vs the stock's OWN past, and the quadrant persistence streak."""
    if not series:
        return None
    cur = series[-1]
    q = cur.get("quadrant")
    streak = 0
    for r in reversed(series):
        if q and r.get("quadrant") == q:
            streak += 1
        else:
            break
    dists = [_signed_dist(r.get("und_price"), r.get("max_pain")) for r in series]
    dist_cur = _signed_dist(cur.get("und_price"), cur.get("max_pain"))
    return {
        "sym": sym, "date": cur.get("trade_date"), "quadrant": q, "streak": streak,
        "pcr": _f(cur.get("pcr")), "pcr_pct": _pctile([r.get("pcr") for r in series],
                                                      cur.get("pcr"), FNO_MINPTS),
        "fut_oi": _f(cur.get("fut_oi")), "oi_pct": _pctile([r.get("fut_oi") for r in series],
                                                           cur.get("fut_oi"), FNO_MINPTS),
        "oi_chg": _f(cur.get("fut_oi_chg_pct")), "basis": _f(cur.get("basis_pct")),
        "dist": dist_cur, "dist_pct": _pctile(dists, dist_cur, FNO_MINPTS),
        "und": _f(cur.get("und_price")), "max_pain": _f(cur.get("max_pain")),
        "n_hist": sum(1 for r in series if r.get("quadrant")),
    }


def fno_board(conn, sort: str = "oi_pct") -> dict:
    """Every F&O name's current positioning ranked against its OWN history (ports /dash/fno).
    The un-owned axis: a SHORT_COVER day on a 90th-percentile book means the shorts merely
    ROLLED, not left. Compute-on-read from `fno_oi_signals`, stdlib only.

    STRICTLY DESCRIPTIVE. The Phase-0 edge gate (2026-07-24) found only PCR carries a small
    cross-sectional edge (delta ~0.06) and it is FORWARD-TEST-ONLY; max-pain, basis and OI-change
    failed outright. This board RANKS and FLAGS, it never picks. {} if the table is absent."""
    if not _has(conn, "fno_oi_signals"):
        return {}
    raw = _rows(conn, "SELECT symbol, trade_date, quadrant, pcr, fut_oi, und_price, max_pain, "
                      "basis_pct, fut_oi_chg_pct FROM fno_oi_signals ORDER BY symbol, trade_date")
    if not raw:
        return {}
    by_sym: dict = {}
    for r in raw:
        by_sym.setdefault(r.get("symbol"), []).append(r)
    latest = max((v[-1].get("trade_date") or "") for v in by_sym.values())
    out = []
    for sym, series in by_sym.items():
        if (series[-1].get("trade_date") or "") != latest:
            continue                        # only names present on the current cross-section
        row = _fno_row(sym, series)
        if row:
            out.append(row)
    if sort not in FNO_SORTS:
        sort = "oi_pct"
    if sort == "sym":
        out.sort(key=lambda z: z["sym"] or "")
    elif sort == "oi":
        out.sort(key=lambda z: (z.get("fut_oi") is None, -(z.get("fut_oi") or 0)))
    else:
        out.sort(key=lambda z: (z.get(sort) is None, -(z.get(sort) or 0)))
    return {"rows": out, "as_of": latest, "sort": sort, "flags": fno_flags(out)}


def fno_flags(rows: list) -> list:
    """Auto-generated reality checks read straight off the data — the reads a same-day quadrant
    tag cannot make. Each names ONE example; none of them is a ranking or a recommendation."""
    out = []
    hollow = [r for r in rows if r.get("quadrant") == "SHORT_COVER"
              and r.get("oi_pct") is not None and r["oi_pct"] >= 70]
    if hollow:
        h = max(hollow, key=lambda z: z["oi_pct"])
        out.append({"kind": "Hollow short-cover", "sym": h["sym"], "value": h["oi_pct"],
                    "text": "Covering on a still-crowded book — futures OI sits in its "
                            "%.0fth percentile. The shorts rolled, they did not leave; the bounce "
                            "sits on an intact short book." % h["oi_pct"]})
    crowd = [r for r in rows if r.get("quadrant") == "SHORT_BUILDUP"
             and r.get("oi_pct") is not None and r["oi_pct"] >= 80 and r.get("streak", 0) >= 2]
    if crowd:
        c = max(crowd, key=lambda z: z["oi_pct"])
        out.append({"kind": "Crowded short build-up", "sym": c["sym"], "value": c["oi_pct"],
                    "text": "Fresh shorts piling into an already-heavy book (%.0fth percentile) "
                            "for %d straight sessions." % (c["oi_pct"], c["streak"])})
    fresh = [r for r in rows if r.get("quadrant") == "LONG_BUILDUP"
             and r.get("oi_pct") is not None and r["oi_pct"] <= 30]
    if fresh:
        f = min(fresh, key=lambda z: z["oi_pct"])
        out.append({"kind": "Fresh long on a thin book", "sym": f["sym"], "value": f["oi_pct"],
                    "text": "Longs building where almost nobody is positioned — OI in its "
                            "%.0fth percentile, so there is little to unwind." % f["oi_pct"]})
    fear = [r for r in rows if r.get("pcr_pct") is not None and r["pcr_pct"] >= 95]
    if fear:
        p = max(fear, key=lambda z: z["pcr_pct"])
        out.append({"kind": "Most put-heavy in its own history", "sym": p["sym"],
                    "value": p["pcr_pct"],
                    "text": "Put/call open interest at its %.0fth percentile for this name — the "
                            "most hedged/feared this book has been." % p["pcr_pct"]})
    return out


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — EVENTS & RESTRICTIONS
#   (ports /dash/actions + /dash/results-reactions + /dash/event-cadence +
#          /dash/buyback-calc + /dash/surveillance + /dash/band-locks)
# ══════════════════════════════════════════════════════════════════════════════════════
CA_TYPES = ("DIVIDEND", "BONUS", "SPLIT", "RIGHTS", "BUYBACK", "DEMERGER", "SCHEME")


def ca_calendar(conn, days: int = 30, sym: str = "") -> dict:
    """The forward corporate-actions calendar, grouped by ex-date. Reuses the home's own
    `reads.upcoming_ca` (-> `corp_actions.upcoming`, the single source every consumer reads).

    STRICTLY LOGISTICS: the ledger closed both event-drift stories on this feed — E-11 dividend
    drift tested NULL (placebo-caught) and E-12 rebrand pump is dead. This says WHAT happens
    WHEN, never what to do about it."""
    rows = reads.upcoming_ca(conn, days=int(days)) or []
    want = str(sym or "").strip().upper()
    if want:
        rows = [r for r in rows if str(r.get("symbol") or "").upper() == want]
    counts, byday = {}, {}
    for r in rows:
        t = str(r.get("action_type") or "OTHER").upper()
        counts[t] = counts.get(t, 0) + 1
        byday.setdefault(r.get("ex_date"), []).append(r)
    days_sorted = [{"d": d, "rows": byday[d]} for d in sorted(byday) if d]
    as_of = _one(conn, "SELECT MAX(fetched_at) FROM corporate_actions")
    return {"rows": rows, "days": days_sorted, "counts": counts, "n": len(rows),
            "as_of": (str(as_of)[:10] if as_of else None), "sym": want, "window": int(days)}


def ca_recent(conn, days: int = 14, limit: int = 12) -> list:
    """What just went ex (the recent past the forward calendar can't show) + the restructure
    context from `security_events` (demergers / schemes / amalgamations)."""
    out = _rows(conn, "SELECT ex_date, symbol, action_type, details FROM corporate_actions "
                      "WHERE ex_date < date('now') AND ex_date >= date('now', ?) "
                      "ORDER BY ex_date DESC, symbol LIMIT ?", (f"-{int(days)} days", int(limit)))
    if _has(conn, "security_events"):
        out += [{**r, "action_type": r.get("event_type")} for r in
                _rows(conn, "SELECT ex_date, symbol, event_type, details FROM security_events "
                            "WHERE ex_date >= date('now', ?) ORDER BY ex_date DESC LIMIT ?",
                      (f"-{int(days)} days", 6))]
    return out


def buyback_rows(conn, limit: int = 12) -> list:
    """Recent + upcoming tender BUYBACKs from the corporate-actions feed — the anchor beside the
    quota calculator. The buyback PRICE is parsed from the exchange's free-text purpose when it
    states one; when it does not, the row still lists (price None) rather than inventing a number."""
    import re as _re
    rows = _rows(conn, "SELECT symbol, ex_date, record_date, details FROM corporate_actions "
                       "WHERE UPPER(action_type)='BUYBACK' AND ex_date >= date('now', '-400 days') "
                       "ORDER BY ex_date DESC LIMIT ?", (int(limit),))
    for r in rows:
        m = _re.search(r"(?:RS\.?|INR|₹)\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
                       str(r.get("details") or ""), _re.IGNORECASE)
        price = None
        if m:
            try:
                price = float(m.group(1).replace(",", ""))
            except ValueError:
                price = None
        r["price"] = price
    return rows


def results_board(conn, view: str = "all", limit: int = 120) -> dict:
    """The results-reaction board (ports /dash/results-reactions): who reported, the Net-Profit
    surprise (SUE, no analysts), whether the strong hand confirmed it on the tape (delivered
    value vs its own trailing median), and — once ~60 sessions elapse — the realized abnormal
    drift vs Nifty 500.

    DESCRIPTIVE ONLY, and the fence is load-bearing: this is the residue of the 2026-07-05 PEAD
    study whose TRADEABLE book was FALSIFIED (net return/vol 0.10 vs the benchmark's 0.85). Every
    number is realized history or an explicitly-labelled base rate. Reads the nightly
    `results_reactions` snapshot in research.db; {} when that DB/table is absent (laptop / clean
    checkout / before the first snapshot) — never fabricated."""
    con = _research_conn()
    if con is None:
        return {}
    try:
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name='results_reactions'").fetchone():
            return {}
        try:
            meta = dict(con.execute("SELECT k, v FROM results_reactions_meta").fetchall())
        except sqlite3.Error:
            meta = {}
        where = "WHERE sue_high=1 AND deliv_high=1" if view == "confirmed" else ""
        rows = [dict(zip(("t0", "sym", "ptype", "sue", "deliv_x", "ear", "car22", "car60",
                          "beat", "sue_high", "deliv_high", "settled"), tuple(r)))
                for r in con.execute(
                    "SELECT t0, sym, ptype, sue, deliv_x, ear, car22, car60, beat, sue_high, "
                    f"deliv_high, settled FROM results_reactions {where} "
                    "ORDER BY t0 DESC, deliv_x DESC LIMIT ?", (int(limit),)).fetchall()]
        n_all = con.execute("SELECT COUNT(*) FROM results_reactions").fetchone()[0]
        n_conf = con.execute("SELECT COUNT(*) FROM results_reactions "
                             "WHERE sue_high=1 AND deliv_high=1").fetchone()[0]
        n_set = con.execute("SELECT COUNT(*) FROM results_reactions "
                            "WHERE settled=1").fetchone()[0]
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    return {"rows": rows, "meta": meta, "view": view,
            "n_all": n_all, "n_confirmed": n_conf, "n_settled": n_set}


def _research_conn():
    """Read-only handle on research.db — the sibling of the configured hermes.db (so it resolves
    both on the box, /opt/hermes/data/, and in a checkout). None when absent."""
    try:
        from src.core.db import DB_PATH
        cand = [str(DB_PATH.parent / "research.db"), "/opt/hermes/data/research.db"]
    except Exception:  # noqa: BLE001
        cand = ["/opt/hermes/data/research.db"]
    for p in cand:
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            con.execute("SELECT 1")
            return con
        except sqlite3.Error:
            continue
    return None


CADENCE_EVENTS = ("all", "RESULTS", "DIVIDEND", "BONUS", "SPLIT", "AGM", "OTHER_CA")


def event_cadence(conn, evt: str = "all", cap: int = 52, horizon: int = 60,
                  limit: int = 40) -> dict:
    """The ADDITIVE cut vs the two announced calendars (ports /dash/event-cadence): which live
    names are OVERDUE versus their OWN rhythm with nothing filed yet, and what each is next
    EXPECTED by cadence. Reads the bounded `seasonal_events` snapshot only — never computes.

    TIME-only (weeks). The fence travels verbatim: event TIMING vs this company's own cadence +
    exchange-declared meetings — factual, NOT a price prediction. {} if the snapshot is absent."""
    if not _has(conn, "seasonal_events"):
        return {}
    evt = evt if evt in CADENCE_EVENTS else "all"
    cap = max(1, min(260, int(cap)))
    horizon = max(7, min(180, int(horizon)))
    base = ["asof=(SELECT MAX(asof) FROM seasonal_events)", "anchor_basis='projection'"]
    cols = ("symbol, event_type, variance_weeks, anchor, lo, hi, n_history")

    ow = base + ["status='OVERDUE'", "variance_weeks >= ?"]
    oargs: list = [-abs(cap)]
    ew = base + ["status='PENDING'", "hi >= date('now')", "lo <= date('now', ?)"]
    eargs: list = [f"+{horizon} days"]
    if evt != "all":
        ow.append("event_type=?"); oargs.append(evt)
        ew.append("event_type=?"); eargs.append(evt)
    over = _rows(conn, f"SELECT {cols} FROM seasonal_events WHERE {' AND '.join(ow)} "
                       "ORDER BY variance_weeks ASC LIMIT ?", (*oargs, int(limit)))
    exp = _rows(conn, f"SELECT {cols} FROM seasonal_events WHERE {' AND '.join(ew)} "
                      "ORDER BY anchor ASC, symbol ASC LIMIT ?", (*eargs, int(limit)))
    dormant = _one(conn, "SELECT COUNT(*) FROM seasonal_events WHERE "
                         "asof=(SELECT MAX(asof) FROM seasonal_events) AND status='OVERDUE' "
                         "AND anchor_basis='projection' AND variance_weeks < ?", (-abs(cap),))
    return {"overdue": over, "expected": exp, "dormant": int(dormant or 0),
            "evt": evt, "cap": cap, "horizon": horizon,
            "as_of": _one(conn, "SELECT MAX(asof) FROM seasonal_events")}


def surveillance_tape(conn, days: int = 30, limit: int = 40) -> dict:
    """ASM/GSM entries, exits, stage moves and price-band changes as an event tape (ports
    /dash/surveillance). Derived on read by the CANONICAL `surveillance.transitions` (the single
    source page == card == pillar == board_health reads), so this page can never disagree with
    the classic one.

    FRAMING (standing glossary language): context, NEVER a gate. A name entering ASM often sees
    mechanically forced flows — leveraged positions unwinding under 100% margins or T2T
    settlement — which is information, not a verdict. No study has been run on this feed in
    either direction. {} if the feed is absent."""
    if not _has(conn, "surveillance_flags"):
        return {}
    try:
        from src.automation import surveillance as SV
        events, as_of = SV.transitions(conn, days=int(days))
        current = SV.current_state(conn)
        flags, _f_as_of = SV.flagged_symbols(conn)
    except Exception:  # noqa: BLE001 — a feed hiccup degrades to empty, never a 500
        return {}
    counts = {}
    for e in events:
        counts[e.get("kind")] = counts.get(e.get("kind"), 0) + 1
    return {"events": events[:int(limit)], "n_events": len(events), "as_of": as_of,
            "counts": counts, "n_flagged": len(flags or []),
            "current": {k: v for k, v in (current or {}).items()}, "days": int(days)}


def band_locks(conn, limit: int = 30) -> dict:
    """Names pinned at their daily price band (ports /dash/band-locks). A close AT the permitted
    daily maximum (close == high == the +band% limit) is an UPPER lock — the buy queue outran the
    band; lower locks are symmetric. Streaks are consecutive same-direction locked days ending at
    the latest bhav date. Single-sourced through `band_lock.active_streaks`.

    FRAMING: a close-at-band streak is a QUEUE-IMBALANCE TELL — context, never a gate; no study
    exists on band-lock streaks in either direction. THE HONEST WINDOW travels with it: bands are
    reconstructable only back to the feed's first captured day, so the board deepens every
    trading night and never fabricates earlier history. {} if the feed is absent."""
    if not _has(conn, "price_bands_current") and not _has(conn, "price_band_events"):
        return {}
    try:
        from src.automation import band_lock as BL
        streaks, latest = BL.active_streaks(conn)
        flags, _ = BL.flagged_symbols(conn)
        birth, min_streak = BL.FEED_BIRTH, BL.FLAG_MIN_STREAK
        ndays = len(BL.trading_dates(conn, birth))
    except Exception:  # noqa: BLE001
        return {}
    if not streaks and not latest:
        return {}
    return {"streaks": (streaks or [])[:int(limit)], "n": len(streaks or []),
            "as_of": latest, "n_flagged": len(flags or []), "feed_birth": birth,
            "min_streak": min_streak, "n_days": ndays,
            "up": sum(1 for s in (streaks or []) if s.get("dir") == "up"),
            "down": sum(1 for s in (streaks or []) if s.get("dir") == "down")}


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — WHAT CHANGED  (ports /dash/attention)
# ══════════════════════════════════════════════════════════════════════════════════════
ATTENTION_LENSES = ("rs", "mep", "dvpt", "cci", "oi", "deal", "quality", "cpr")


def attention_queue(conn, as_of: str = "", lens: str = "", limit: int = 30) -> dict:
    """The magnitude-ranked tape of typed state-changes across every live lens (ports
    /dash/attention): the human front-door of the signal-event bus. Data-first — the raw
    before -> after sits beside every verdict.

    PIT-honest: `as_of` replays a past batch through the same last-batch-on-or-before resolver
    the /v1 API uses, so an exact-date miss can never read as an empty tape.

    FRAMING: an event is a derived judgement that something CHANGED — never a recommendation.
    Magnitude ranks attention WITHIN a batch; it is not a return forecast and no study exists on
    event follow-through. The lenses' own fences ride along (CCI descriptive-only, MEP a
    descriptor per D62, deal prints are logistics). {} if the bus is empty."""
    if not _has(conn, "signal_events"):
        return {}
    want = str(as_of or "").strip()[:10]
    batch = None
    if want:
        batch = _one(conn, "SELECT MAX(as_of) FROM signal_events WHERE as_of <= ?", (want,))
    if not batch:
        batch = _one(conn, "SELECT MAX(as_of) FROM signal_events")
    if not batch:
        return {}
    lens = lens if lens in ATTENTION_LENSES else ""
    sql = ("SELECT symbol, lens, event_type, direction, from_state, to_state, magnitude, "
           "as_of, detected_at, note FROM signal_events WHERE as_of=?")
    args: list = [batch]
    if lens:
        sql += " AND lens=?"
        args.append(lens)
    sql += " ORDER BY magnitude DESC, detected_at DESC LIMIT ?"
    args.append(int(limit))
    rows = _rows(conn, sql, tuple(args))
    per_lens = {r["lens"]: r["c"] for r in
                _rows(conn, "SELECT lens, COUNT(*) AS c FROM signal_events WHERE as_of=? "
                            "GROUP BY lens ORDER BY c DESC", (batch,))}
    n_batch = _one(conn, "SELECT COUNT(*) FROM signal_events WHERE as_of=?", (batch,))
    hist = _rows(conn, "SELECT as_of, lens, COUNT(*) AS n FROM signal_events WHERE as_of IN "
                       "(SELECT DISTINCT as_of FROM signal_events ORDER BY as_of DESC LIMIT 12) "
                       "GROUP BY as_of, lens ORDER BY as_of DESC", ())
    batches: dict = {}
    for r in hist:
        batches.setdefault(r["as_of"], {})[r["lens"]] = r["n"]
    return {"rows": rows, "batch": batch, "per_lens": per_lens, "lens": lens,
            "n_batch": int(n_batch or 0), "replay": bool(want and want != batch),
            "asked": want, "batches": [{"as_of": k, "by_lens": v} for k, v in batches.items()],
            "total": int(_one(conn, "SELECT COUNT(*) FROM signal_events") or 0)}


def alert_rail(conn, days: int = 7, limit: int = 20) -> dict:
    """The curated, multi-day, severity-graded subset of the queue — a short notifications list,
    not the firehose (the bus's fourth face). Read-only here: promotion runs in the nightly
    `--detect`, and acknowledging an alert stays an owner action on the classic page.
    Ranking is single-sourced through `signal_alerts.active_alerts`. {} if absent."""
    if not _has(conn, "signal_alert_state"):
        return {}
    try:
        from src.automation import signal_alerts as SA
        alerts = SA.active_alerts(conn, within_days=int(days), limit=int(limit))
        counts = SA.active_count(conn, within_days=int(days))
    except Exception:  # noqa: BLE001
        return {}
    return {"alerts": alerts or [], "counts": counts or {}, "days": int(days),
            "severity": reads.severity_counts(conn, days=int(days))}
