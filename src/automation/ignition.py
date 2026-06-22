"""Ignition ranking — the DVPT picking-strategy "picker" (daily timeframe).

Among today's all-stars DVPT crossers, rank by how HARD they crossed — the
ignition *intensity* (today's delivery-per-trade vs its own peak-day baselines),
modified by breadth (full SS vs partial S), accumulation character, and a
first-ignition (origin) bonus. (docs/dvpt-picking-strategy-design.md §2–3, with
the §11 confirmations resolved: C1 graded-band intensity, C2 first-flag + keep
tracking, C3 the 5 power baselines 1m/2m/3m/6m/12m.)

Honors two deliberate design rules:
  - **Act vs Watch, never discard.** Lesser-intensity ignitions stay browsable in
    WATCH; distribution-character ones are flagged AVOID — nothing is dropped from
    the ignited set (only a modest liquidity floor keeps un-actionable junk out,
    and the count dropped is logged).
  - **Survivorship-correct.** The universe is gated through the security_master
    spine (recently-traded equities), so the ranking can never include a name that
    isn't actually tradeable.

DAILY only for now. The multi-horizon (D+W+M) version has a hard dependency on the
weekly/monthly signals foundation (the MTF engine) and is deferred until that runs;
the schema already carries a `timeframe` column so W/M rows slot in without change.

Self-contained (the capture.py / security_master.py pattern): OWNS its two tables,
never edits db.py. Reads stock_signals + security_master only. Pure arithmetic, no
LLM. The latest snapshot (`ignition_ranking`) is fully recomputed each run; the
time series (`ranking_history`) is ONLY upserted for the current date — never
bulk-deleted, so accumulated daily history is preserved.

Run:        python -m src.automation.ignition
Self-check: python -m src.automation.ignition --selftest
For a date: python -m src.automation.ignition --date 2026-06-22
Inspect:    python -m src.automation.ignition --symbol RELIANCE
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.ignition")

# The 5 power baselines (top-N peak-day DVPT per window) confirmed live (C3).
POWER_BASELINES = ("power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m",
                   "power_dvpt_6m", "power_dvpt_12m")
ALLSTAR_RANKS = ("SS", "S")          # the existing all-stars crossings we rank among
FIRST_IGNITION_FROM = "2019-01-01"   # origin flag evaluated from here (design §3)
LIQ_FLOOR = 2_500_000                # ₹25 lakh delivery value — drop un-actionable junk
ACT_INTENSITY = 3.0                  # ACT tier floor (× over peak baselines)

# transparent, tunable multipliers (stored components → fully auditable)
CHAR_MULT = {"ACCUMULATION": 1.15, "NEUTRAL": 1.0, "CONSOLIDATION": 0.90,
             "DISTRIBUTION": 0.50}
BREADTH_MULT = {"SS": 1.10, "S": 1.0}
FIRST_BONUS = 1.15


# ── pure helpers ──────────────────────────────────────────────────────────────
def _mean(vals) -> Optional[float]:
    xs = [v for v in vals if isinstance(v, (int, float))]
    return (sum(xs) / len(xs)) if xs else None


def _band(x: float) -> str:
    if x >= 10:  return "EXTREME"
    if x >= 5:   return "HIGH"
    if x >= 3:   return "ELEVATED"
    if x >= 1.5: return "MODERATE"
    return "MILD"


def _tier(intensity: float, trigger_rank: str, character: Optional[str]) -> str:
    """ACT = unusually huge intensity + a full all-stars cross + CLEAN accumulation
    (the design's actionable gate). DISTRIBUTION → AVOID (kept, flagged). Everything
    else that ignited → WATCH (kept, browsable)."""
    if character == "DISTRIBUTION":
        return "AVOID"
    if intensity >= ACT_INTENSITY and trigger_rank == "SS" and character == "ACCUMULATION":
        return "ACT"
    return "WATCH"


def _rank_score(intensity: float, trigger_rank: str, character: Optional[str],
                is_first: bool) -> float:
    return (intensity
            * CHAR_MULT.get(character, 1.0)
            * BREADTH_MULT.get(trigger_rank, 1.0)
            * (FIRST_BONUS if is_first else 1.0))


# ── storage (owns its own tables) ─────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS ignition_ranking (
    symbol               TEXT PRIMARY KEY,
    canonical_symbol     TEXT,
    trade_date           TEXT,
    timeframe            TEXT DEFAULT 'D',
    today_dvpt           REAL,
    baseline_mean        REAL,
    intensity            REAL,
    intensity_band       TEXT,
    breadth              INTEGER,        -- how many of the 5 power baselines today beat
    trigger_rank         TEXT,           -- SS (full all-stars) / S (partial)
    character            TEXT,           -- accum_character
    is_ath_dvpt          INTEGER,
    rs_rank              INTEGER,
    delivery_value_today REAL,
    first_ignition_date  TEXT,
    is_first_ignition    INTEGER,
    rank_score           REAL,
    rank                 INTEGER,
    tier                 TEXT,           -- ACT / WATCH / AVOID
    status               TEXT,           -- NEW / FRESH / CONTINUING / COOLING
    computed_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ign_rank ON ignition_ranking(rank);
CREATE INDEX IF NOT EXISTS idx_ign_tier ON ignition_ranking(tier, rank);

CREATE TABLE IF NOT EXISTS ranking_history (
    symbol     TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    timeframe  TEXT NOT NULL DEFAULT 'D',
    intensity  REAL,
    rank       INTEGER,
    tier       TEXT,
    status     TEXT,
    character  TEXT,
    PRIMARY KEY (symbol, trade_date, timeframe)
);
CREATE INDEX IF NOT EXISTS idx_rh_date ON ranking_history(trade_date, timeframe);
CREATE INDEX IF NOT EXISTS idx_rh_sym  ON ranking_history(symbol, trade_date);
"""

_RANK_COLS = [
    "symbol", "canonical_symbol", "trade_date", "timeframe", "today_dvpt",
    "baseline_mean", "intensity", "intensity_band", "breadth", "trigger_rank",
    "character", "is_ath_dvpt", "rs_rank", "delivery_value_today",
    "first_ignition_date", "is_first_ignition", "rank_score", "rank", "tier", "status",
]


def _latest_date(conn) -> Optional[str]:
    r = conn.execute("SELECT MAX(trade_date) m FROM stock_signals").fetchone()
    return r["m"] if (r and r["m"]) else None


def compute_for_date(conn, trade_date: str) -> tuple[list, int]:
    """Rank the all-stars crossers for one date. Returns (ranked_rows, n_dropped_illiquid).
    Survivorship-gated via security_master.recently_traded."""
    pbcols = ", ".join(f"s.{c}" for c in POWER_BASELINES)
    cand = conn.execute(
        f"SELECT s.symbol, s.delivery_value_per_trade dvpt, s.delivery_value_today dvt, "
        f"       s.trigger_rank tr, s.accum_character ch, s.is_ath_dvpt ath, s.rs_rank rsr, "
        f"       {pbcols} "
        f"FROM stock_signals s "
        f"JOIN security_master m ON m.symbol = s.symbol AND m.recently_traded = 1 "
        f"WHERE s.trade_date = ? AND s.trigger_rank IN ('SS','S') "
        f"      AND s.delivery_value_per_trade IS NOT NULL",
        (trade_date,)).fetchall()

    # first-ignition (origin) date per symbol — the first FULL all-stars cross
    first_ig = {r["symbol"]: r["f"] for r in conn.execute(
        "SELECT symbol, MIN(trade_date) f FROM stock_signals "
        "WHERE trigger_rank='SS' AND trade_date >= ? GROUP BY symbol",
        (FIRST_IGNITION_FROM,)).fetchall()}

    # the previous ranked day (for status) — intensities only
    prev_row = conn.execute(
        "SELECT MAX(trade_date) m FROM ranking_history WHERE timeframe='D' AND trade_date < ?",
        (trade_date,)).fetchone()
    prev_date = prev_row["m"] if prev_row else None
    prev_intensity = {}
    if prev_date:
        prev_intensity = {r["symbol"]: r["intensity"] for r in conn.execute(
            "SELECT symbol, intensity FROM ranking_history WHERE timeframe='D' AND trade_date=?",
            (prev_date,)).fetchall()}

    out, dropped = [], 0
    for r in cand:
        dvt = r["dvt"]
        if dvt is not None and dvt < LIQ_FLOOR:        # un-actionable junk
            dropped += 1
            continue
        baselines = [r[c] for c in POWER_BASELINES]
        bmean = _mean(baselines)
        dvpt = r["dvpt"]
        if not bmean or bmean <= 0 or dvpt is None:
            continue
        intensity = dvpt / bmean
        breadth = sum(1 for b in baselines if isinstance(b, (int, float)) and dvpt > b)
        tr, ch = r["tr"], r["ch"]
        fdate = first_ig.get(r["symbol"])
        is_first = 1 if (fdate and fdate == trade_date) else 0

        if is_first:
            status = "NEW"
        elif r["symbol"] not in prev_intensity:
            status = "FRESH"
        elif prev_intensity[r["symbol"]] and intensity < prev_intensity[r["symbol"]] * 0.8:
            status = "COOLING"
        else:
            status = "CONTINUING"

        out.append({
            "symbol": r["symbol"], "canonical_symbol": r["symbol"],
            "trade_date": trade_date, "timeframe": "D",
            "today_dvpt": dvpt, "baseline_mean": bmean,
            "intensity": intensity, "intensity_band": _band(intensity),
            "breadth": breadth, "trigger_rank": tr, "character": ch,
            "is_ath_dvpt": r["ath"], "rs_rank": r["rsr"], "delivery_value_today": dvt,
            "first_ignition_date": fdate, "is_first_ignition": is_first,
            "rank_score": _rank_score(intensity, tr, ch, bool(is_first)),
            "tier": _tier(intensity, tr, ch), "status": status,
        })

    out.sort(key=lambda d: d["rank_score"], reverse=True)
    for i, d in enumerate(out, 1):
        d["rank"] = i
    return out, dropped


def compute_and_store(conn=None, trade_date: Optional[str] = None) -> dict:
    """Compute + persist the ignition ranking for `trade_date` (default: latest).
    Recomputes the `ignition_ranking` snapshot in full; upserts ONLY this date's
    rows into `ranking_history` (history is never bulk-deleted). Manages its own
    connection if none given."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        d = trade_date or _latest_date(conn)
        if not d:
            log.warning("ignition: no stock_signals data")
            return {"trade_date": None, "ranked": 0}

        ranked, dropped = compute_for_date(conn, d)

        # latest snapshot — full recompute of OUR table only
        conn.execute("DELETE FROM ignition_ranking")
        ph = ",".join("?" * len(_RANK_COLS))
        conn.executemany(
            f"INSERT OR REPLACE INTO ignition_ranking ({','.join(_RANK_COLS)}) VALUES ({ph})",
            [[row.get(c) for c in _RANK_COLS] for row in ranked])

        # time series — upsert THIS date only (never touch other dates' history)
        conn.executemany(
            "INSERT OR REPLACE INTO ranking_history "
            "(symbol, trade_date, timeframe, intensity, rank, tier, status, character) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [(r["symbol"], d, "D", r["intensity"], r["rank"], r["tier"], r["status"], r["character"])
             for r in ranked])

        if own:
            conn.commit()

        stats = {
            "trade_date": d, "ranked": len(ranked),
            "act": sum(1 for r in ranked if r["tier"] == "ACT"),
            "watch": sum(1 for r in ranked if r["tier"] == "WATCH"),
            "avoid": sum(1 for r in ranked if r["tier"] == "AVOID"),
            "new": sum(1 for r in ranked if r["status"] == "NEW"),
            "dropped_illiquid": dropped,
        }
        log.info("ignition: %s", stats)
        return stats
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── read API ──────────────────────────────────────────────────────────────────
def _with_conn(fn, conn):
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        return fn(conn)
    finally:
        if own:
            cm.__exit__(None, None, None)


def top(limit: int = 100, tier: Optional[str] = None, conn=None) -> list:
    def q(c):
        sql = "SELECT * FROM ignition_ranking"
        args = []
        if tier:
            sql += " WHERE tier=?"
            args.append(tier)
        sql += " ORDER BY rank LIMIT ?"
        args.append(limit)
        return [dict(r) for r in c.execute(sql, args).fetchall()]
    return _with_conn(q, conn)


def get(symbol: str, conn=None) -> Optional[dict]:
    def q(c):
        r = c.execute("SELECT * FROM ignition_ranking WHERE symbol=?", (symbol,)).fetchone()
        return dict(r) if r else None
    return _with_conn(q, conn)


def history(symbol: str, limit: int = 120, conn=None) -> list:
    def q(c):
        return [dict(r) for r in c.execute(
            "SELECT * FROM ranking_history WHERE symbol=? AND timeframe='D' "
            "ORDER BY trade_date DESC LIMIT ?", (symbol, limit)).fetchall()]
    return _with_conn(q, conn)


# ── self-check (synthetic in-memory DB — no real data needed) ─────────────────
def _selftest() -> None:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    pbdefs = ", ".join(f"{c} REAL" for c in POWER_BASELINES)
    conn.executescript(f"""
        CREATE TABLE stock_signals (
            symbol TEXT, trade_date TEXT, delivery_value_per_trade REAL,
            delivery_value_today REAL, trigger_rank TEXT, accum_character TEXT,
            is_ath_dvpt INTEGER, rs_rank INTEGER, {pbdefs});
        CREATE TABLE security_master (symbol TEXT PRIMARY KEY, recently_traded INTEGER);
    """)
    d = "2026-06-22"
    # (symbol, dvpt, dvt, trigger, character, baselines-all-equal)  baseline mean = b
    fixtures = [
        ("HUGEACC", 100.0, 5e7, "SS", "ACCUMULATION", 10.0),   # intensity 10× → ACT, EXTREME
        ("MILDACC", 1.3,   5e7, "S",  "ACCUMULATION", 1.0),    # intensity 1.3× → WATCH
        ("BIGDIST", 50.0,  5e7, "SS", "DISTRIBUTION", 10.0),   # intensity 5× but distribution → AVOID
        ("PENNYXX", 99.0,  1e5, "SS", "ACCUMULATION", 1.0),    # huge intensity but illiquid → dropped
    ]
    for sym, dvpt, dvt, tr, ch, b in fixtures:
        conn.execute("INSERT INTO security_master VALUES (?,1)", (sym,))
        cols = "symbol,trade_date,delivery_value_per_trade,delivery_value_today,trigger_rank,accum_character,is_ath_dvpt,rs_rank," + ",".join(POWER_BASELINES)
        ph = ",".join("?" * (8 + len(POWER_BASELINES)))
        conn.execute(f"INSERT INTO stock_signals ({cols}) VALUES ({ph})",
                     (sym, d, dvpt, dvt, tr, ch, 0, 50, *([b] * len(POWER_BASELINES))))

    stats = compute_and_store(conn=conn, trade_date=d)
    assert stats["ranked"] == 3 and stats["dropped_illiquid"] == 1, stats

    rows = top(conn=conn)
    by = {r["symbol"]: r for r in rows}
    assert by["HUGEACC"]["rank"] == 1, "highest clean intensity must rank #1"
    assert abs(by["HUGEACC"]["intensity"] - 10.0) < 1e-6, by["HUGEACC"]["intensity"]
    assert by["HUGEACC"]["tier"] == "ACT" and by["HUGEACC"]["intensity_band"] == "EXTREME"
    assert by["HUGEACC"]["status"] == "NEW", "first-ever SS must be NEW (origin)"
    assert by["MILDACC"]["tier"] == "WATCH", "low intensity is kept in WATCH, not dropped"
    assert by["BIGDIST"]["tier"] == "AVOID", "distribution character → AVOID"
    assert "PENNYXX" not in by, "illiquid name must be dropped from the ranking"

    # a second day: HUGEACC continues (not first anymore) → CONTINUING; idempotent re-run
    d2 = "2026-06-23"
    for sym, dvpt, dvt, tr, ch, b in fixtures[:1]:
        cols = "symbol,trade_date,delivery_value_per_trade,delivery_value_today,trigger_rank,accum_character,is_ath_dvpt,rs_rank," + ",".join(POWER_BASELINES)
        ph = ",".join("?" * (8 + len(POWER_BASELINES)))
        conn.execute(f"INSERT INTO stock_signals ({cols}) VALUES ({ph})",
                     (sym, d2, dvpt, dvt, tr, ch, 0, 50, *([b] * len(POWER_BASELINES))))
    compute_and_store(conn=conn, trade_date=d2)
    assert get("HUGEACC", conn=conn)["status"] == "CONTINUING", "still-ranked next day → CONTINUING"
    # history preserved for BOTH days
    assert len(history("HUGEACC", conn=conn)) == 2, "history must accumulate, never be wiped"
    print(f"ignition selftest: OK  {stats}")


def main() -> None:
    p = argparse.ArgumentParser(description="Daily ignition intensity ranking (the DVPT picker).")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--date", help="rank a specific trade_date (default: latest)")
    p.add_argument("--symbol", help="print one symbol's current rank + recent history")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        _selftest()
        return
    if args.symbol:
        sym = args.symbol.strip().upper()
        print(f"{sym}: {get(sym)}")
        for h in history(sym, limit=10):
            print(f"  {h['trade_date']} rank={h['rank']} {h['tier']} {h['status']} "
                  f"intensity={h['intensity']:.2f}")
        return

    stats = compute_and_store(trade_date=args.date)
    print(f"ignition: {stats}")


if __name__ == "__main__":
    main()
