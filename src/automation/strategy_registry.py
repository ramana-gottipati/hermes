"""strategy_registry — one uniform, read-only "current read" per strategy.

Lane C owns this module (docs/parallel-sessions-PLAN.md §2b). It is the SINGLE source
the Strategist dashboard (Lane B, /dash/strategist) reads: one row per strategy giving
the count of currently-flagged names, the data freshness, the top names, and a health
flag — each linking to that strategy's deep page.

    summary(conn=None) -> list[dict], each row:
        { "key":   str,            # stable machine key
          "label": str,            # human label (matches the nav)
          "route": str,            # the deep page to link the card to
          "count": int | None,     # # of currently-flagged names (None = on-demand)
          "as_of": str | None,     # freshness — the latest data date (YYYY-MM-DD)
          "top":   [{"symbol","note"}],   # the strongest few current names
          "health":"ok" | "stale" | "empty" }

CONTRACT (binding): reads ONLY precomputed tables (mep_signals, concall_scores,
cpr_signals, stock_signals) — it NEVER recomputes a strategy on read; the nightly jobs
own the compute. If a table is missing/empty or a query fails, that strategy degrades to
health="empty" (never raises) so one cold table can't break the whole dashboard.

Wolfe is computed on-demand (no persisted table — see wolfe.py), so its row is
descriptive: count=None, health="ok", a note pointing at the live scanner.

`count` semantics = the number of symbols the strategy currently FLAGS at the latest
snapshot (e.g. MEP accumulation states, CPR non-NONE patterns, CCI strong tiers) — the
"actionable now" population, NOT the universe size.
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from contextlib import nullcontext

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore


# Per-strategy staleness budget (calendar days from the latest data date to today).
# Daily signals refresh every trading night; concalls are quarterly, so far more lenient.
_STALE_DAYS = {"mep": 7, "dvpt": 7, "rs": 7, "cpr": 10, "cci": 150}


# --------------------------------------------------------------------------- #
# small resilient helpers                                                       #
# --------------------------------------------------------------------------- #
def _rows(conn, sql, params=()):
    cur = conn.execute(sql, params)
    return cur.fetchall()


def _table_exists(conn, name) -> bool:
    r = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return r is not None


def _max_date(conn, table, datecol):
    r = conn.execute(f"SELECT MAX({datecol}) AS d FROM {table}").fetchone()
    return (r["d"] if r else None) or None


def _stale(as_of, budget_days) -> bool:
    """True if `as_of` (YYYY-MM-DD…) is older than the strategy's budget vs today."""
    if not as_of:
        return True
    try:
        d = _dt.date.fromisoformat(str(as_of)[:10])
    except ValueError:
        return False  # unparseable date → don't cry stale, just show it
    return (_dt.date.today() - d).days > budget_days


def _health(count, as_of, budget_days) -> str:
    if not as_of or not count:
        return "empty"
    return "stale" if _stale(as_of, budget_days) else "ok"


def _empty(key, label, route):
    return {"key": key, "label": label, "route": route,
            "count": 0, "as_of": None, "top": [], "health": "empty"}


# --------------------------------------------------------------------------- #
# per-strategy readers — each returns one summary row, never raises             #
# --------------------------------------------------------------------------- #
def _mep(conn):
    key, label, route = "mep", "Accumulation (MEP)", "/dash/mep"
    if not _table_exists(conn, "mep_signals"):
        return _empty(key, label, route)
    as_of = _max_date(conn, "mep_signals", "trade_date")
    if not as_of:
        return _empty(key, label, route)
    # latest global snapshot; the smoothed phase is the headline (daily whipsaw fixed).
    rows = _rows(conn,
        "SELECT symbol, mep_state_smooth, mep_score_smooth "
        "FROM mep_signals WHERE trade_date=? "
        "AND mep_state_smooth IN ('STRONG_ACCUM','ACCUM') "
        "ORDER BY mep_score_smooth DESC", (as_of,))
    count = len(rows)
    top = [{"symbol": r["symbol"],
            "note": (r["mep_state_smooth"] or "").replace("_", " ").title()}
           for r in rows[:5]]
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top, "health": _health(count, as_of, _STALE_DAYS["mep"])}


def _dvpt(conn):
    key, label, route = "dvpt", "Delivery (DVPT)", "/dash/screener"
    if not _table_exists(conn, "stock_signals"):
        return _empty(key, label, route)
    as_of = _max_date(conn, "stock_signals", "trade_date")
    if not as_of:
        return _empty(key, label, route)
    # flagged = a real DVPT trigger today (trigger_rank above the floor '-').
    rows = _rows(conn,
        "SELECT symbol, trigger_rank, accum_character, p_score "
        "FROM stock_signals WHERE trade_date=? "
        "AND trigger_rank IS NOT NULL AND trigger_rank NOT IN ('-','') "
        "ORDER BY p_score DESC, ratio_today_vs_power_3m DESC", (as_of,))
    count = len(rows)
    top = [{"symbol": r["symbol"],
            "note": f'{r["trigger_rank"]} · {(r["accum_character"] or "").replace("_", " ").title()}'.strip(" ·")}
           for r in rows[:5]]
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top, "health": _health(count, as_of, _STALE_DAYS["dvpt"])}


def _rs(conn):
    key, label, route = "rs", "Strength (RS)", "/dash/leaders"
    if not _table_exists(conn, "stock_signals"):
        return _empty(key, label, route)
    as_of = _max_date(conn, "stock_signals", "trade_date")
    if not as_of:
        return _empty(key, label, route)
    # RS is denormalized onto stock_signals; leaders = top RS rank at the latest snapshot.
    rows = _rows(conn,
        "SELECT symbol, rs_rank, rs_vs_broad_trend_state "
        "FROM stock_signals WHERE trade_date=? AND rs_rank IS NOT NULL "
        "ORDER BY rs_rank DESC", (as_of,))
    # "flagged" = strong relative strength (rank in the top decile, 90+).
    flagged = [r for r in rows if (r["rs_rank"] or 0) >= 90]
    count = len(flagged)
    top = [{"symbol": r["symbol"],
            "note": f'RS {r["rs_rank"]} · {(r["rs_vs_broad_trend_state"] or "").title()}'.strip(" ·")}
           for r in rows[:5]]
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top, "health": _health(count, as_of, _STALE_DAYS["rs"])}


def _cpr(conn):
    key, label, route = "cpr", "Structure (CPR)", "/dash/cpr"
    if not _table_exists(conn, "cpr_signals"):
        return _empty(key, label, route)
    # daily timeframe is the primary read; latest snapshot for it.
    r = conn.execute(
        "SELECT MAX(period_end_date) AS d FROM cpr_signals WHERE timeframe='D'").fetchone()
    as_of = (r["d"] if r else None) or None
    if not as_of:
        return _empty(key, label, route)
    rows = _rows(conn,
        "SELECT symbol, pattern, compression_pctile, days_since_pattern "
        "FROM cpr_signals WHERE timeframe='D' AND period_end_date=? "
        "AND pattern IS NOT NULL AND pattern!='NONE' "
        "ORDER BY (days_since_pattern IS NULL), days_since_pattern ASC, "
        "compression_pctile ASC", (as_of,))
    count = len(rows)
    top = [{"symbol": r["symbol"],
            "note": f'{r["pattern"]}' + (f' · {r["days_since_pattern"]}d' if r["days_since_pattern"] is not None else '')}
           for r in rows[:5]]
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top, "health": _health(count, as_of, _STALE_DAYS["cpr"])}


def _cci(conn):
    key, label, route = "cci", "Credibility (CCI)", "/dash/concalls"
    if not _table_exists(conn, "concall_scores"):
        return _empty(key, label, route)
    as_of = _max_date(conn, "concall_scores", "as_of_date") \
        or _max_date(conn, "concall_scores", "last_updated")
    # latest score per symbol (scores trickle in continuously, not as a nightly snapshot).
    rows = _rows(conn,
        "SELECT s.symbol, s.composite_score, s.tier, s.forward_direction, "
        "       s.credibility_trend "
        "FROM concall_scores s "
        "JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x "
        "  ON x.symbol=s.symbol AND x.m=s.last_updated "
        "ORDER BY s.composite_score DESC")
    # "flagged" = the credible cohort (A+/A tiers).
    flagged = [r for r in rows if (r["tier"] or "") in ("A+", "A")]
    count = len(flagged)
    top = []
    for r in rows[:5]:
        note = f'{r["tier"] or "?"}'
        if r["forward_direction"]:
            note += f' · {r["forward_direction"]}'
        if r["credibility_trend"]:
            note += f' · {r["credibility_trend"].title()}'
        top.append({"symbol": r["symbol"], "note": note})
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": (as_of[:10] if as_of else None), "top": top,
            "health": _health(count, as_of, _STALE_DAYS["cci"])}


def _wolfe(conn):
    # No persisted table — the scan is computed on-demand (wolfe.winner_scan), too heavy
    # for an at-a-glance read. Descriptive row pointing at the live scanner.
    return {"key": "wolfe", "label": "Wolfe (winner-profile)",
            "route": "/dash/wolfe/scan", "count": None, "as_of": None,
            "top": [{"symbol": "—", "note": "live scan — descriptive, read by side (BULL ✓ / BEAR ⚠)"}],
            "health": "ok"}


# registry order = the order the Strategist dashboard shows the cards.
_READERS = [_mep, _dvpt, _rs, _cpr, _cci, _wolfe]


def summary(conn=None) -> list[dict]:
    """One row per strategy for the Strategist dashboard (see module docstring)."""
    ctx = nullcontext(conn) if conn is not None else get_conn()
    out = []
    with ctx as c:
        for reader in _READERS:
            try:
                out.append(reader(c))
            except Exception:
                # one cold/odd table never breaks the dashboard — degrade that card.
                k = reader.__name__.lstrip("_")
                out.append(_empty(k, k.upper(), "/dash/strategies"))
    return out


# --------------------------------------------------------------------------- #
# selftest — `python -m src.automation.strategy_registry`                       #
# --------------------------------------------------------------------------- #
def _selftest():
    rows = summary()
    assert isinstance(rows, list) and rows, "summary() returned no rows"
    required = {"key", "label", "route", "count", "as_of", "top", "health"}
    keys = set()
    for r in rows:
        missing = required - set(r)
        assert not missing, f"{r.get('key')} missing keys: {missing}"
        assert r["health"] in ("ok", "stale", "empty"), f"bad health: {r['health']}"
        assert isinstance(r["top"], list), f"{r['key']} top not a list"
        for t in r["top"]:
            assert set(t) >= {"symbol", "note"}, f"{r['key']} bad top item: {t}"
        keys.add(r["key"])
    assert "wolfe" in keys, "wolfe row missing"
    print(f"OK  strategy_registry.summary() -> {len(rows)} rows")
    for r in rows:
        print(f"  {r['key']:6} {r['health']:6} count={str(r['count']):>5} "
              f"as_of={r['as_of']}  top={[t['symbol'] for t in r['top']]}")
    return rows


if __name__ == "__main__":
    _selftest()
