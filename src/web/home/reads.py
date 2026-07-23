"""src/web/home/reads.py — the home's self-contained, read-only data layer (spec §5).

IMPORT BAN (Codex B4/B5, gate: tests/test_home_isolation.py): this module imports ONLY
`src.core.db` + genuinely-shared, NON-preview, read-only helpers (`corp_actions.upcoming`,
`results_calendar.upcoming_results`, `whatchanged_flow.changes`, `market_mood.market_mood`). It
NEVER imports `today_v3`, `news_dock`, `shell_v3`, `ui_*_v3`, `v3_preview`, or any `*_v3` render
module (those return `pv3-*` HTML, not data). All reads are bounded + defensive: a missing table
returns an empty result, never an exception (a busy/edge DB must never 500 the home).
"""
from __future__ import annotations

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


def index_pulse(conn, names=_PULSE_NAMES, limit: int = 4) -> list:
    if not _has(conn, "index_signals"):
        return []
    d = _latest_date(conn, "index_signals", "trade_date")
    if not d:
        return []
    qs = ",".join("?" * len(names))
    return _rows(conn,
                 f"SELECT index_name, close_value, ret_1d_pct, pct_above_200d_avg "
                 f"FROM index_signals WHERE trade_date=? AND index_name IN ({qs}) "
                 f"ORDER BY CASE index_name {' '.join(f'WHEN ? THEN {i}' for i in range(len(names)))} "
                 f"ELSE 99 END LIMIT ?",
                 (d, *names, *names, limit))


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
                         "WHERE trade_date=? AND index_name='NIFTY 50'", (d,)).fetchone()
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
    if not _has(conn, "sent_news"):
        return []
    return _rows(conn, "SELECT source, url, title, sent_at FROM sent_news "
                       "ORDER BY sent_at DESC LIMIT ?", (limit,))


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
            "SELECT close_value FROM index_signals WHERE index_name=? AND close_value IS NOT NULL "
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
