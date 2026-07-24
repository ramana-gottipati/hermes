"""src/web/home/reads.py — the home's self-contained, read-only data layer (spec §5).

IMPORT BAN (Codex B4/B5, gate: tests/test_home_isolation.py): this module imports ONLY
`src.core.db` + genuinely-shared, NON-preview, read-only helpers (`corp_actions.upcoming`,
`results_calendar.upcoming_results`, `whatchanged_flow.changes`, `market_mood.market_mood`). It
NEVER imports `today_v3`, `news_dock`, `shell_v3`, `ui_*_v3`, `v3_preview`, or any `*_v3` render
module (those return `pv3-*` HTML, not data). All reads are bounded + defensive: a missing table
returns an empty result, never an exception (a busy/edge DB must never 500 the home).
"""
from __future__ import annotations

import re
import sqlite3
from typing import Optional


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


def _latest_date(conn, table: str, col: str) -> Optional[str]:
    try:
        r = conn.execute(f"SELECT MAX({col}) AS d FROM {table}").fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None


# ── zone 1: market pulse ──────────────────────────────────────────────────────────
_PULSE_NAMES = ("NIFTY 50", "NIFTY BANK", "NIFTY 500", "NIFTY MIDCAP 100", "NIFTY SMALLCAP 250")


def index_pulse(conn, names=_PULSE_NAMES, limit: int = 5) -> list:
    """CASE-INSENSITIVE on index_name (box-verified 2026-07-23): the table stores mixed casing —
    'Nifty 50' / 'Nifty Bank' / 'Nifty 500' / 'Nifty Smallcap 250' but 'NIFTY Midcap 100'. An exact
    IN(...) match silently returned NOTHING, so the whole Market-pulse zone ran on demo (the 'sample'
    badge is what exposed it). `names` are the UPPER-CASE canonical forms."""
    if not _has(conn, "index_signals"):
        return []
    d = _latest_date(conn, "index_signals", "trade_date")
    if not d:
        return []
    qs = ",".join("?" * len(names))
    return _rows(conn,
                 f"SELECT index_name, close_value, ret_1d_pct, pct_above_200d_avg "
                 f"FROM index_signals WHERE trade_date=? AND UPPER(index_name) IN ({qs}) "
                 f"ORDER BY CASE UPPER(index_name) {' '.join(f'WHEN ? THEN {i}' for i in range(len(names)))} "
                 f"ELSE 99 END LIMIT ?",
                 (d, *names, *names, limit))


def vix_latest(conn) -> dict:
    """India VIX — the expected-swing gauge. It IS carried in index_signals (box-verified); higher
    means a wider expected move, so it is rendered NEUTRAL (a rising VIX is not 'good'). {} if absent."""
    if not _has(conn, "index_signals"):
        return {}
    d = _latest_date(conn, "index_signals", "trade_date")
    if not d:
        return {}
    rows = _rows(conn, "SELECT close_value, ret_1d_pct FROM index_signals "
                       "WHERE trade_date=? AND UPPER(index_name)='INDIA VIX'", (d,))
    return rows[0] if rows else {}


def mood_inputs(conn) -> tuple:
    """(breadth %, nifty_above_200dma) for the canonical market_mood(). Both None if no data."""
    if not _has(conn, "index_signals"):
        return (None, None)
    d = _latest_date(conn, "index_signals", "trade_date")
    if not d:
        return (None, None)
    try:
        row = conn.execute(
            "SELECT 100.0*SUM(CASE WHEN pct_above_200d_avg>0 THEN 1 ELSE 0 END)/COUNT(*) AS breadth "
            "FROM index_signals WHERE trade_date=?", (d,)).fetchone()
        breadth = round(row[0], 1) if row and row[0] is not None else None
    except sqlite3.Error:
        breadth = None
    try:
        r = conn.execute("SELECT pct_above_200d_avg FROM index_signals "
                         "WHERE trade_date=? AND UPPER(index_name)='NIFTY 50'", (d,)).fetchone()
        nifty_up = (r[0] > 0) if r and r[0] is not None else None
    except sqlite3.Error:
        nifty_up = None
    return (breadth, nifty_up)


def breadth_latest(conn) -> Optional[dict]:
    if not _has(conn, "market_internals_daily"):
        return None
    rows = _rows(conn, "SELECT d, adv, dec, pct_adv FROM market_internals_daily ORDER BY d DESC LIMIT 1")
    return rows[0] if rows else None


# ── zone 3: FII/DII flows (the real stored categories are 'FII/FPI' | 'DII') ────────
def fii_dii_recent(conn, limit: int = 10) -> list:
    if not _has(conn, "fii_dii_flows"):
        return []
    return _rows(conn,
                 "SELECT trade_date, category, net_value FROM fii_dii_flows "
                 "WHERE category IN ('FII/FPI','DII') ORDER BY trade_date DESC LIMIT ?", (limit * 2,))


# ── zone 6: news wire ───────────────────────────────────────────────────────────
def recent_news(conn, limit: int = 8) -> list:
    """Recent headlines, near-duplicates collapsed (same story from two sources → one row)."""
    if not _has(conn, "sent_news"):
        return []
    rows = _rows(conn, "SELECT source, url, title, sent_at FROM sent_news "
                       "ORDER BY sent_at DESC LIMIT ?", (limit * 3,))
    seen, out = set(), []
    for r in rows:
        key = " ".join(re.sub(r"[^a-z0-9 ]", " ", (r.get("title") or "").lower()).split()[:4])
        if key and key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= limit:
            break
    return out


# ── zones 4/5/2/7: thin wrappers over shared, non-preview reads ─────────────────
def upcoming_ca(conn, days: int = 21) -> list:
    """corp_actions.upcoming returns a (rows, as_of) tuple — unpack it and hand back the rows."""
    try:
        from src.automation.corp_actions import upcoming
        rows, _as_of = upcoming(conn, days=days)
        return rows or []
    except Exception:  # noqa: BLE001
        return []


def upcoming_results(days: int = 30) -> list:
    try:
        from src.automation.results_calendar import upcoming_results as _u
        return list(_u(days=days)) or []
    except Exception:  # noqa: BLE001
        return []


def what_changed(conn, days: int = 7, limit: int = 12) -> list:
    try:
        from src.pat.whatchanged_flow import changes
        return list(changes(conn, "", within_days=days, limit=limit)) or []
    except Exception:  # noqa: BLE001
        return []


def severity_counts(conn, days: int = 7) -> dict:
    """Counts over the curated alert rail (signal_alert_state) — descriptive, verdict-free.
    severity is 'critical'|'high'; valence is 'risk'|'opportunity'|'neutral'."""
    out = {"critical": 0, "high": 0, "opportunity": 0, "risk": 0, "total": 0}
    if not _has(conn, "signal_alert_state"):
        return out
    try:
        rows = conn.execute(
            "SELECT severity, valence, COUNT(*) FROM signal_alert_state "
            "WHERE as_of >= date('now', ?) GROUP BY severity, valence",
            (f"-{int(days)} day",)).fetchall()
    except sqlite3.Error:
        return out
    for sev, val, c in rows:
        out["total"] += c
        if sev == "critical":
            out["critical"] += c
        elif sev == "high":
            out["high"] += c
        if val == "opportunity":
            out["opportunity"] += c
        elif val == "risk":
            out["risk"] += c
    return out


def index_series(conn, name: str = "NIFTY 50", n: int = 30) -> list:
    """Chronological close series for one index — for the pulse sparkline. [] on any gap."""
    if not _has(conn, "index_signals"):
        return []
    try:
        rows = conn.execute(
            "SELECT close_value FROM index_signals WHERE UPPER(index_name)=UPPER(?) AND close_value IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT ?", (name, n)).fetchall()
        return [float(r[0]) for r in rows][::-1]
    except (sqlite3.Error, TypeError, ValueError):
        return []


def delivery_leaders(conn, limit: int = 6) -> list:
    """Delivery-conviction leaders — the REAL column is power_dvpt_3m (there is no bare power_dvpt)."""
    if not _has(conn, "stock_signals"):
        return []
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return []
    return _rows(conn, "SELECT symbol, power_dvpt_3m FROM stock_signals "
                       "WHERE trade_date=? AND power_dvpt_3m IS NOT NULL "
                       "ORDER BY power_dvpt_3m DESC LIMIT ?", (d, limit))


# ── market-pulse instrument deck: internals history + 52w highs + sector heat ──────
def internals_series(conn, n: int = 30) -> list:
    """Chronological market-internals rows for the pulse trend tiles (breadth · delivery %
    · accumulation MEP · dispersion). [] if the table/data is absent."""
    if not _has(conn, "market_internals_daily"):
        return []
    rows = _rows(conn, "SELECT d, adv, dec, pct_adv, avg_dp, mep_net, disp FROM market_internals_daily "
                       "WHERE pct_adv IS NOT NULL ORDER BY d DESC LIMIT ?", (int(n),))
    return rows[::-1]  # oldest→newest for the sparklines


def new_highs(conn) -> dict:
    """Fresh 52-week highs today + names within 2% of their high (real leadership breadth).
    {} if stock_signals is absent. There is no 52w-LOW flag, so we never fabricate one."""
    if not _has(conn, "stock_signals"):
        return {}
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return {}
    try:
        hi = conn.execute("SELECT COUNT(*) FROM stock_signals WHERE trade_date=? "
                          "AND rs_vs_broad_new_52w_high=1", (d,)).fetchone()
        near = conn.execute("SELECT COUNT(*) FROM stock_signals WHERE trade_date=? "
                            "AND pct_from_52w_high IS NOT NULL AND pct_from_52w_high>=-2", (d,)).fetchone()
        return {"highs": int(hi[0]) if hi and hi[0] is not None else 0,
                "near": int(near[0]) if near and near[0] is not None else 0}
    except sqlite3.Error:
        return {}


def sector_heat(conn, limit: int = 9) -> list:
    """Per-sector average relative strength today (leaders → laggards), a SIGNED read
    (rs_vs_broad_today is a % vs the broad index). [] if absent. Sectors with <3 names dropped."""
    if not _has(conn, "stock_signals"):
        return []
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return []
    return _rows(conn,
                 "SELECT primary_sector AS sector, AVG(rs_vs_broad_today) AS rs, COUNT(*) AS n "
                 "FROM stock_signals WHERE trade_date=? AND primary_sector IS NOT NULL "
                 "AND rs_vs_broad_today IS NOT NULL GROUP BY primary_sector "
                 "HAVING n>=3 ORDER BY rs DESC LIMIT ?", (d, int(limit)))


# ── per-symbol enrichment (day change from bhav copy · RS phase from signals) ──────
def _day_change(conn, symbols) -> dict:
    """{symbol: {'pct','deliv','close'}} from the latest EQ/BE bhav-copy row. {} if absent."""
    if not symbols or not _has(conn, "bhavcopy_rows"):
        return {}
    d = _latest_date(conn, "bhavcopy_rows", "trade_date")
    if not d:
        return {}
    qs = ",".join("?" * len(symbols))
    out = {}
    for r in _rows(conn, f"SELECT symbol, close, prev_close, deliv_per FROM bhavcopy_rows "
                         f"WHERE trade_date=? AND series IN ('EQ','BE') AND symbol IN ({qs})",
                   (d, *symbols)):
        cl, pc = r.get("close"), r.get("prev_close")
        try:
            pct = ((cl - pc) / pc * 100.0) if (cl is not None and pc) else None
        except (TypeError, ZeroDivisionError):
            pct = None
        out[r["symbol"]] = {"pct": pct, "deliv": r.get("deliv_per"), "close": cl}
    return out


def _rs_of(conn, symbols) -> dict:
    """{symbol: {'rank','trend'}} from the latest stock_signals row. {} if absent."""
    if not symbols or not _has(conn, "stock_signals"):
        return {}
    d = _latest_date(conn, "stock_signals", "trade_date")
    if not d:
        return {}
    qs = ",".join("?" * len(symbols))
    out = {}
    for r in _rows(conn, f"SELECT symbol, rs_rank, rs_vs_broad_trend_state FROM stock_signals "
                         f"WHERE trade_date=? AND symbol IN ({qs})", (d, *symbols)):
        out[r["symbol"]] = {"rank": r.get("rs_rank"), "trend": r.get("rs_vs_broad_trend_state")}
    return out


# ── featured card: watchlist · portfolio · movers · ticker feeds ───────────────────
def watchlist_rows(conn, limit: int = 10) -> list:
    """The user's followed names, enriched with day change + RS phase.

    Reads BOTH watchlist tiers (box-verified 2026-07-23): the lifecycle tracker's lightweight tier
    (`stocks_in_play` status='watch' — the canonical D54 tier that /dash/tracker/watchlists writes)
    AND the legacy `watchlist` table, deduped in that order. Reading only the legacy table meant a
    name added through the Tracker would never show up here. [] if both are empty — the caller then
    falls back to demo (marked sample)."""
    syms = []
    if _has(conn, "stocks_in_play"):
        syms += [r["symbol"] for r in _rows(
            conn, "SELECT DISTINCT symbol FROM stocks_in_play WHERE status='watch' "
                  "ORDER BY date_added DESC LIMIT ?", (int(limit),))]
    if _has(conn, "watchlist"):
        syms += [r["symbol"] for r in _rows(
            conn, "SELECT symbol FROM watchlist ORDER BY added_at DESC LIMIT ?", (int(limit),))]
    seen, ordered = set(), []
    for s in syms:
        if s and s not in seen:
            seen.add(s)
            ordered.append(s)
    syms = ordered[:limit]
    if not syms:
        return []
    chg, rs = _day_change(conn, syms), _rs_of(conn, syms)
    out = []
    for s in syms:
        c, r = chg.get(s, {}), rs.get(s, {})
        out.append({"symbol": s, "pct": c.get("pct"), "deliv": c.get("deliv"),
                    "rank": r.get("rank"), "trend": r.get("trend")})
    return out


def portfolio(conn) -> dict:
    """Holdings from the lifecycle tracker (`stocks_in_play`, status open/watch) marked to today's
    bhav close: rows + day P&L% + invested + count. {} if no holdings (caller shows demo/sample)."""
    if not _has(conn, "stocks_in_play"):
        return {}
    holds = _rows(conn, "SELECT symbol, qty, entry_price, book FROM stocks_in_play "
                        "WHERE status IN ('open','watch')")
    if not holds:
        return {}
    syms = [h["symbol"] for h in holds]
    chg = _day_change(conn, syms)
    rows, invested, day_pnl = [], 0.0, 0.0
    for h in holds:
        c = chg.get(h["symbol"], {})
        px, pct, qty, ep = c.get("close"), c.get("pct"), (h.get("qty") or 0), h.get("entry_price")
        mv = (px * qty) if (px is not None and qty) else None
        if mv:
            invested += mv
            if pct is not None:
                day_pnl += mv * pct / 100.0
        since = ((px - ep) / ep * 100.0) if (px is not None and ep) else None
        rows.append({"symbol": h["symbol"], "pct": pct, "mv": mv, "since": since, "book": h.get("book")})
    for r in rows:
        r["weight"] = (r["mv"] / invested * 100.0) if (invested and r.get("mv")) else None
    return {"rows": rows, "invested": invested, "day_pnl": day_pnl,
            "day_pct": (day_pnl / invested * 100.0) if invested else None, "n": len(rows)}


def movers(conn, limit: int = 6) -> dict:
    """Today's biggest gainers/losers by day change (EQ/BE bhav copy). {} if absent."""
    if not _has(conn, "bhavcopy_rows"):
        return {}
    d = _latest_date(conn, "bhavcopy_rows", "trade_date")
    if not d:
        return {}
    rows = []
    for r in _rows(conn, "SELECT symbol, close, prev_close FROM bhavcopy_rows "
                         "WHERE trade_date=? AND series IN ('EQ','BE') AND close IS NOT NULL AND prev_close>0", (d,)):
        try:
            r["pct"] = (r["close"] - r["prev_close"]) / r["prev_close"] * 100.0
            rows.append(r)
        except (TypeError, ZeroDivisionError):
            continue
    rows.sort(key=lambda x: x["pct"], reverse=True)
    return {"gainers": rows[:limit], "losers": rows[-limit:][::-1]} if rows else {}


# ── the analyst's "today" additions: conviction shortlist + ownership filings ─────
def conviction_now(limit: int = 40) -> list:
    """The cross-pillar Conviction shortlist (RS leader + accumulating now + near entry, pt14 quality
    as a ✓) — reuses the CANONICAL stock_rs.conviction_shortlist (same as /dash/conviction, DRY). It
    opens its own read-only connection. Returns the FULL qualifying set (up to `limit`) so the card
    can state the honest count ('N cleared all 3 pillars today') even though it displays only the top
    few. [] on any error → the caller shows demo (marked sample)."""
    try:
        from src.automation.stock_rs import conviction_shortlist
        return list(conviction_shortlist(limit=limit) or [])
    except Exception:  # noqa: BLE001 — a heavy/edge synthesis must never 500 the home
        return []


# The REAL insider vocabulary (box-verified 2026-07-23). `plumbing` (ESOP/gift/inter-se/allotment,
# ~3.0k rows) and `ignore` (UNKNOWN, ~390) are administrative NOISE — they must never crowd the card;
# the signal lives in conviction/caution/buy_other/sell_other/pledge_risk/pledge_relief.
_INSIDER_NOISE = ("ignore", "plumbing")
_INSIDER_POS = ("conviction", "buy_other", "pledge_relief")
_INSIDER_WARN = ("caution", "sell_other", "pledge_risk")


def _insider_ev(r: dict) -> dict:
    tc = (r.get("txn_class") or "").upper()          # OPEN_MARKET_BUY | OPEN_MARKET_SELL | ...
    sc = (r.get("signal_class") or "").lower()
    who = "Promoter" if r.get("promoter_group_flag") else "Insider"
    verb = "buy" if ("BUY" in tc or "ACQ" in tc) else ("sell" if ("SELL" in tc or "DISP" in tc) else "trade")
    cls = "pos" if sc in _INSIDER_POS else ("warn" if sc in _INSIDER_WARN else "")
    return {"symbol": r.get("symbol"), "detail": f"{who} {verb}", "date": r.get("disclosure_dt"), "cls": cls}


def _pledge_ev(r: dict) -> dict:
    et = (r.get("event_type") or "").lower()
    pct = r.get("event_pct")
    created = ("creat" in et) or ("invoc" in et)
    verb = "Pledge created" if created else ("Pledge released" if ("releas" in et or "revoc" in et) else "Pledge change")
    detail = verb + (f" {abs(float(pct)):.1f}%" if pct is not None else "")
    return {"symbol": r.get("symbol"), "detail": detail, "date": r.get("broadcast_dt"), "cls": ("warn" if created else "pos")}


def _reg29_ev(r: dict) -> dict:
    ac = (r.get("acq_sale") or "").lower()
    who = "Promoter" if r.get("promoter_flag") else "Substantial holder"
    if "acq" in ac or "buy" in ac:
        return {"symbol": r.get("symbol"), "detail": f"{who} stake acquired", "date": r.get("broadcast_dt"), "cls": "pos"}
    if "sale" in ac or "sell" in ac or "disp" in ac:
        return {"symbol": r.get("symbol"), "detail": f"{who} stake sold", "date": r.get("broadcast_dt"), "cls": "warn"}
    return {"symbol": r.get("symbol"), "detail": f"{who} stake change", "date": r.get("broadcast_dt"), "cls": ""}


def filings_recent(conn, days: int = 21, limit: int = 12) -> list:
    """Recent ownership/insider filings — insider transactions + SAST pledge + Reg-29 stake events,
    unified newest-first, each a plain-English descriptive line. [] if the tables are absent/empty
    (the caller falls back to demo). Descriptive only, never a recommendation.

    BALANCED BY SOURCE, box-verified 2026-07-23. Two real defects this fixes:
      1. Stake disclosures fire far more often than insider trades (281 vs 158 in 21d) AND carry
         to-the-minute timestamps while `disclosure_dt` is date-only — so a newest-first merge served
         12/12 stake events and buried every insider buy. Sources are now ROUND-ROBIN interleaved
         (each internally newest-first), which is immune to that timestamp-granularity skew.
      2. `signal_class` 'plumbing'/'ignore' (ESOP, gifts, inter-se, UNKNOWN — the bulk of the table)
         is administrative noise; it is filtered out so the card carries actual signal.
    Near-duplicates (same symbol + same event line) collapse. Descriptive only."""
    per = max(4, int(limit) // 2)
    win = (f"-{int(days)} day", per)
    groups = []
    if _has(conn, "insider_events"):
        qs = ",".join("?" * len(_INSIDER_NOISE))
        groups.append([_insider_ev(r) for r in _rows(
            conn, "SELECT symbol, disclosure_dt, txn_class, signal_class, promoter_group_flag FROM insider_events "
                  f"WHERE disclosure_dt >= date('now', ?) AND COALESCE(signal_class,'') NOT IN ({qs}) "
                  "ORDER BY disclosure_dt DESC LIMIT ?",
            (f"-{int(days)} day", *_INSIDER_NOISE, per))])
    if _has(conn, "sast_pledge_events"):
        groups.append([_pledge_ev(r) for r in _rows(
            conn, "SELECT symbol, broadcast_dt, event_type, event_pct FROM sast_pledge_events "
                  "WHERE broadcast_dt >= date('now', ?) ORDER BY broadcast_dt DESC LIMIT ?", win)])
    if _has(conn, "sast_reg29_events"):
        groups.append([_reg29_ev(r) for r in _rows(
            conn, "SELECT symbol, broadcast_dt, acq_sale, promoter_flag FROM sast_reg29_events "
                  "WHERE broadcast_dt >= date('now', ?) ORDER BY broadcast_dt DESC LIMIT ?", win)])
    groups = [[e for e in g if e.get("symbol")] for g in groups]
    seen, out = set(), []
    for i in range(per):                       # round-robin: one source can never crowd out another
        for g in groups:
            if i >= len(g):
                continue
            e = g[i]
            key = (e.get("symbol"), e.get("detail"))
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
    return out[:limit]
