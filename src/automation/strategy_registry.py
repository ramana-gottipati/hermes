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

CONTRACT (binding): reads ONLY precomputed tables (stock_signals, mep_signals,
cpr_signals, concall_scores, concall_signals, launchpad_signals, momentum_scan,
wolfe_signals + results_reactions in research.db) — it NEVER recomputes a strategy
on read; the nightly jobs own the compute. If a table is missing/empty or a query
fails, that strategy degrades to health="empty" (never raises) so one cold table
can't break the whole dashboard.

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
    from src.core.db import DB_PATH, get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import DB_PATH, get_conn  # type: ignore


# Per-strategy staleness budget (calendar days from the latest data date to today).
# Daily signals refresh every trading night; concalls are quarterly, so far more lenient.
_STALE_DAYS = {"mep": 7, "dvpt": 7, "rs": 7, "cpr": 10, "cci": 150,
               "conviction": 7, "growth": 150, "launchpad": 7,
               "momentum": 7, "reactions": 10, "insider": 7, "ratings": 10}

# Liquidity / universe gate for whole-universe rankers — mirrors
# dashboard._SCAN_FILTERS, kept self-contained (same choice strategist_view made).
_LIQ = ("b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL) "
        "AND b.value > 10000000 AND b.close > 20 "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list)")


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


def _conviction(conn):
    """The cross-pillar shortlist — names strong on BOTH the strong-hand delivery
    footprint (p_score) AND relative strength at once. Same blend the Conviction
    deep page / strategist fallback uses (0.55 positioning + 0.45 RS, flag >= 78)."""
    key, label, route = "conviction", "Conviction", "/dash/conviction"
    if not _table_exists(conn, "stock_signals"):
        return _empty(key, label, route)
    as_of = _max_date(conn, "stock_signals", "trade_date")
    if not as_of:
        return _empty(key, label, route)
    conv = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
    rows = _rows(conn,
        f"SELECT s.symbol, {conv} conv "
        f"FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date) "
        f"WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL AND {_LIQ} "
        f"ORDER BY conv DESC LIMIT 600", (as_of,))
    flagged = [r for r in rows if (r["conv"] or 0) >= 78]
    count = len(flagged)
    top = [{"symbol": r["symbol"], "note": f'conv {r["conv"]:.0f}'} for r in flagged[:5]]
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top,
            "health": _health(count, as_of, _STALE_DAYS["conviction"])}


def _dvpt(conn):
    # route = /dash/stocks (the Positioning table), matching the Strategies-altitude
    # catalog — the old /dash/screener route made the board grow a SECOND, link-only
    # "Positioning" card beside this one (dedup is by route).
    key, label, route = "dvpt", "Positioning (DVPT)", "/dash/stocks"
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
    # CL-SCO-15: `count` and `top` must read the SAME population — otherwise a card
    # could show count=0 yet list 5 names. The card is about the flagged cohort, so
    # show the flagged names (rows are sorted by rs_rank DESC, so [:5] = strongest).
    flagged = [r for r in rows if (r["rs_rank"] or 0) >= 90]
    count = len(flagged)
    top = [{"symbol": r["symbol"],
            "note": f'RS {r["rs_rank"]} · {(r["rs_vs_broad_trend_state"] or "").title()}'.strip(" ·")}
           for r in flagged[:5]]
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
    # CL-SCO-15: rows can exist while both date columns are NULL/unhelpful, leaving
    # as_of None even though we have scores — which would mislabel the card "empty".
    # Fall back to the max non-null date carried on the rows so a populated card
    # always reports an as_of.
    if not as_of and rows:
        cand = conn.execute(
            "SELECT MAX(COALESCE(as_of_date, last_updated)) AS d FROM concall_scores"
        ).fetchone()
        as_of = (cand["d"] if cand else None) or None
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


def _insider(conn):
    """Insider activity — the fresh-conviction cohort from insider_events
    (D94 queue #1): principals net-BOUGHT on the open market over 90d with
    buying inside the last 30d. Flag logic lives in
    insider_events.flagged_symbols (single source: card == pillar == gate)."""
    key, label, route = "insider", "Insider activity", "/dash/insider"
    if not _table_exists(conn, "insider_events"):
        return _empty(key, label, route)
    try:
        from src.automation import insider_events as IE
        flags, as_of = IE.flagged_symbols(conn)
    except Exception:  # noqa: BLE001
        return _empty(key, label, route)
    if not as_of:
        return _empty(key, label, route)
    count = len(flags)
    top = []
    for sym, a in flags[:5]:
        note = f'₹{a["open_market_buy_value_30d"] / 1e7:,.1f}cr 30d'
        if a["promoter_cluster_buy_30d"] >= 2:
            note += f' · {a["promoter_cluster_buy_30d"]} buyers'
        top.append({"symbol": sym, "note": note})
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": str(as_of)[:10], "top": top,
            "health": _health(count, as_of, _STALE_DAYS["insider"])}


def _ratings(conn):
    """Credit-rating transitions — DEDUPED company-level up/down actions in the
    trailing 90d (D94 queue #2). Flag logic lives in
    credit_ratings.flagged_symbols (the E-02 dedup: one event per symbol ×
    broadcast day × direction — raw rows are ~6× pseudo-replication).
    Descriptive; the pre-registered E-02 drift study is armed — no return claim."""
    key, label, route = "ratings", "Rating transitions", "/dash/ratings"
    if not _table_exists(conn, "credit_rating_events"):
        return _empty(key, label, route)
    try:
        from src.automation import credit_ratings as CRR
        flags, as_of = CRR.flagged_symbols(conn)
    except Exception:  # noqa: BLE001
        return _empty(key, label, route)
    if not as_of:
        return _empty(key, label, route)
    count = len(flags)
    if not count:
        # quiet 90d window over a LIVE feed (true actions ~2/month) — healthy zero
        return {"key": key, "label": label, "route": route, "count": 0,
                "as_of": str(as_of)[:10],
                "top": [{"symbol": "—", "note": "no company-level transitions in 90d"}],
                "health": "ok" if not _stale(as_of, _STALE_DAYS["ratings"]) else "stale"}
    top = []
    for sym, e in flags[:5]:
        arrow = "↑" if e["sign"] > 0 else "↓"
        notch = abs(e.get("notch") or 0)
        note = f'{arrow}{notch if notch else ""} {(e.get("lt_grade") or "").strip()}'.strip()
        agency = (e.get("agency") or "").split(" Ratings")[0].split(" Limited")[0].strip()
        if agency:
            note += f' · {agency}'
        top.append({"symbol": sym, "note": note})
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": str(as_of)[:10], "top": top,
            "health": _health(count, as_of, _STALE_DAYS["ratings"])}


def _growth(conn):
    """Growth-intent — forward proposals managements committed to on concalls
    (capex / expansion / debt-cut / new products), Rs-normalised. Flagged = the
    distinct companies with a growth-polarity statement in the last 12 months."""
    key, label, route = "growth", "Growth-intent", "/dash/growth"
    if not _table_exists(conn, "concall_signals"):
        return _empty(key, label, route)
    r = conn.execute("SELECT MAX(year*100+month) ym FROM concall_signals "
                     "WHERE is_growth_intent=1").fetchone()
    ym = r["ym"] if r else None
    if not ym:
        return _empty(key, label, route)
    yr, mo = int(ym) // 100, int(ym) % 100
    as_of = f"{yr:04d}-{mo:02d}-01"
    lo = (yr - 1) * 100 + mo
    rows = _rows(conn,
        "SELECT symbol, statement_type, MAX(COALESCE(amount_cr,0)) amt "
        "FROM concall_signals "
        "WHERE is_growth_intent=1 AND COALESCE(polarity,1) >= 0 "
        "  AND (year*100+month) >= ? "
        "GROUP BY symbol ORDER BY amt DESC", (lo,))
    count = len(rows)
    top = []
    for r in rows[:5]:
        typ = (r["statement_type"] or "growth").replace("_", " ")
        note = (f'{typ} · Rs{r["amt"]:,.0f}cr' if r["amt"] else typ)
        top.append({"symbol": r["symbol"], "note": note})
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top,
            "health": _health(count, as_of, _STALE_DAYS["growth"])}


def _launchpad(conn):
    """Launchpad — the D56-validated explosive-move precursors, read from the
    nightly launchpad_signals snapshot (launchpad_signals.py, wolfe pattern).
    Flagged = FRESH triggers (rising edge <= 2 sessions) — the actionable cut."""
    key, label, route = "launchpad", "Launchpad", "/dash/launchpad"
    if not _table_exists(conn, "launchpad_signals"):
        # snapshot not materialised yet on this host — descriptive link row
        return {"key": key, "label": label, "route": route, "count": None,
                "as_of": None,
                "top": [{"symbol": "—",
                         "note": "nightly snapshot pending — open the lens for the live scan"}],
                "health": "ok"}
    try:
        meta = dict(conn.execute("SELECT k, v FROM launchpad_scan_meta").fetchall())
    except Exception:  # noqa: BLE001
        meta = {}
    as_of = meta.get("scan_date") or _max_date(conn, "launchpad_signals", "scan_date")
    if not as_of:
        return _empty(key, label, route)
    rows = _rows(conn,
        "SELECT symbol, flags, age, buyer FROM launchpad_signals WHERE scan_date=? "
        "ORDER BY buyer DESC, (age IS NULL), age ASC, med_turn DESC", (as_of,))
    fresh = [r for r in rows if r["age"] is not None and r["age"] <= 2]
    count = len(fresh)
    top = []
    for r in fresh[:5]:
        bits = [(r["flags"] or "").replace("|", "+").replace("_", "·")]
        bits.append("fresh" if r["age"] == 0 else f'{r["age"]}d')
        if r["buyer"]:
            bits.append("⭐ buyer")
        top.append({"symbol": r["symbol"], "note": " · ".join(b for b in bits if b)})
    if not count:
        # scan ran, nothing fresh — a healthy, current read (mirror wolfe's shape)
        return {"key": key, "label": label, "route": route, "count": 0, "as_of": as_of,
                "top": [{"symbol": "—", "note": "no fresh precursor triggers"}],
                "health": "ok" if not _stale(as_of, _STALE_DAYS["launchpad"]) else "stale"}
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": as_of, "top": top,
            "health": _health(count, as_of, _STALE_DAYS["launchpad"])}


def _momentum(conn):
    """Momentum ensemble — the nightly risk-adjusted momentum scan
    (momentum_scan, explosive_moves.momentum_scan). Flagged = top-decile
    ensemble percentile. DESCRIPTIVE: attribution proved this is momentum BETA,
    not stock-selection (see docs/strategy-ledger.md) — a tilt, never a buy list."""
    key, label, route = "momentum", "Momentum · ensemble", "/dash/markets/momentum-scan"
    if not _table_exists(conn, "momentum_scan"):
        return _empty(key, label, route)
    as_of = _max_date(conn, "momentum_scan", "as_of")
    if not as_of:
        return _empty(key, label, route)
    rows = _rows(conn,
        "SELECT symbol, ensemble_pctile p FROM momentum_scan "
        "WHERE as_of=? AND ensemble_pctile IS NOT NULL "
        "ORDER BY ensemble_pctile DESC", (as_of,))
    flagged = [r for r in rows if (r["p"] or 0) >= 90]
    count = len(flagged)
    top = [{"symbol": r["symbol"], "note": f'ens {r["p"]:.0f}'} for r in flagged[:5]]
    return {"key": key, "label": label, "route": route, "count": count,
            "as_of": str(as_of)[:10], "top": top,
            "health": _health(count, as_of, _STALE_DAYS["momentum"])}


def _reactions(conn):
    """Results reactions — the season war-room scanner (results_reactions in
    research.db, refreshed nightly). Flagged = delivery-CONFIRMED reactions
    (big earnings surprise AND holding money showed up the same day)."""
    key, label, route = ("reactions", "Results reactions",
                         "/dash/markets/results-reactions")
    rdb = DB_PATH.parent / "research.db"
    if not rdb.exists():
        return _empty(key, label, route)
    try:
        con = sqlite3.connect(f"file:{rdb}?mode=ro", uri=True)
    except Exception:  # noqa: BLE001
        return _empty(key, label, route)
    try:
        con.row_factory = sqlite3.Row
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                           "AND name='results_reactions'").fetchone():
            return _empty(key, label, route)
        meta = dict(con.execute("SELECT k, v FROM results_reactions_meta").fetchall())
        as_of = str(meta.get("generated_at") or "")[:10] or None
        n_conf = con.execute("SELECT COUNT(*) n FROM results_reactions "
                             "WHERE sue_high=1 AND deliv_high=1").fetchone()["n"]
        rows = con.execute(
            "SELECT sym, ptype, deliv_x FROM results_reactions "
            "WHERE sue_high=1 AND deliv_high=1 "
            "ORDER BY t0 DESC, deliv_x DESC LIMIT 5").fetchall()
    except Exception:  # noqa: BLE001
        return _empty(key, label, route)
    finally:
        con.close()
    top = [{"symbol": r["sym"],
            "note": ((r["ptype"] or "results") +
                     (f' · {r["deliv_x"]:.1f}× deliv' if r["deliv_x"] is not None else ""))}
           for r in rows]
    return {"key": key, "label": label, "route": route, "count": n_conf,
            "as_of": as_of, "top": top,
            "health": _health(n_conf, as_of, _STALE_DAYS["reactions"])}


def _wolfe(conn):
    key, label, route = "wolfe", "Wolfe (winner-profile)", "/dash/wolfe/scan"
    # Prefer the nightly-persisted snapshot (wolfe_signals, owned by wolfe.py). If it
    # hasn't been materialised yet, fall back to a descriptive row (the live scan is too
    # heavy for an at-a-glance read).
    if not _table_exists(conn, "wolfe_signals"):
        return {"key": key, "label": label, "route": route, "count": None, "as_of": None,
                "top": [{"symbol": "—", "note": "live scan — descriptive, read by side (BULL ✓ / BEAR ⚠)"}],
                "health": "ok"}
    rows = _rows(conn,
        "SELECT sym, dir, in_zone FROM wolfe_signals WHERE universe='nifty500' "
        "ORDER BY in_zone DESC, age ASC")
    r = conn.execute(
        "SELECT MAX(scan_date) FROM wolfe_signals WHERE universe='nifty500'").fetchone()
    as_of = (r[0] if r else None) or None
    count = len(rows)
    top = [{"symbol": x["sym"],
            "note": (f'{x["dir"]} ' + ("✓ edge" if x["dir"] == "BULL" else "⚠ tail")
                     + (" · IN" if x["in_zone"] else ""))}
           for x in rows[:5]]
    if not count:
        # snapshot ran but found nothing fresh — still a healthy, current read.
        return {"key": key, "label": label, "route": route, "count": 0, "as_of": as_of,
                "top": [{"symbol": "—", "note": "no fresh winner-profile setups"}],
                "health": "ok" if as_of else "empty"}
    return {"key": key, "label": label, "route": route, "count": count, "as_of": as_of,
            "top": top, "health": _health(count, as_of, _STALE_DAYS["mep"])}


# registry order = the order the Strategist dashboard shows the cards.
_READERS = [_conviction, _dvpt, _mep, _cpr, _rs, _cci, _insider, _ratings,
            _growth, _launchpad, _momentum, _reactions, _wolfe]


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
    for want in ("conviction", "dvpt", "mep", "cpr", "rs", "cci", "insider",
                 "ratings", "growth", "launchpad", "momentum", "reactions", "wolfe"):
        assert want in keys, f"{want} row missing"
    print(f"OK  strategy_registry.summary() -> {len(rows)} rows")
    for r in rows:
        print(f"  {r['key']:6} {r['health']:6} count={str(r['count']):>5} "
              f"as_of={r['as_of']}  top={[t['symbol'] for t in r['top']]}")
    return rows


if __name__ == "__main__":
    _selftest()
