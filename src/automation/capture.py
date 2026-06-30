"""Downside / upside capture — "accumulate what falls less than the Nifty".

Ramana's stated objective: accumulate sectors that fall LESS intensely than the
broad market, and refuse to sit in sectors that fall FASTER. That is exactly the
**down-capture ratio**, conditioned on the days the benchmark was actually down:

  - down_capture < 1  → the sector took less than 100% of the Nifty's fall (good)
  - down_capture > 1  → it fell harder than the Nifty (avoid / reduce)
  - up_capture        → how much of the Nifty's rallies it captured
  - capture_spread    → up_capture − down_capture (high = all-weather)
  - down_excess       → mean(sector − benchmark | benchmark down); the robust,
    denominator-free version of "falls less" (positive = falls less, full stop)

Computed per (sector index, broad benchmark) from the daily closes already in
``index_rows`` — no new ingestion, no schema change to existing tables.

Self-contained (the ``oscillators.py`` / ``rrg.py`` pattern): OWNS its
``capture_signals`` table, never edits ``db.py``. Nightly upsert of one latest
row per pair; ₹0 SELECT on read. Pure arithmetic — no LLM.

The "accumulate" framing is only correct when the market is weak, so the UI layer
should gate this read on the existing Home regime banner (see design doc); this
module just stores the raw, regime-agnostic numbers.

Run the job:   python -m src.automation.capture
Self-check:    python -m src.automation.capture --selftest
"""

from __future__ import annotations

import argparse
import logging
import math
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.capture")


def _fin(v):
    """Coerce non-finite (inf/nan) to None so it never poisons the DB or a sort."""
    if v is None:
        return None
    return v if (isinstance(v, (int, float)) and math.isfinite(v)) else None

# Broad benchmarks (match index_signals.BROAD_BENCHMARKS title-casing exactly).
BROAD_BENCHMARKS = ("Nifty 50", "Nifty 500")
WINDOWS = (63, 126, 252)   # ≈ 3m / 6m / 12m of trading days
MIN_DOWN_DAYS = 5          # need a few down days for the ratio to mean anything


# ── pure math (date-aligned close lists, oldest → newest) ─────────────────────
def _returns(closes: list) -> list:
    """Period returns. CL-MDC-12: a non-positive/missing prev close yields None
    (a skipped observation) rather than a fabricated 0.0 flat day, which would
    otherwise dilute the up/down-capture denominators. Position is preserved so
    the sector and benchmark return lists stay index-aligned; capture_window
    drops any pair where either side is None."""
    out = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if prev and prev > 0 and cur is not None:
            out.append(cur / prev - 1.0)
        else:
            out.append(None)
    return out


def _compound(rets: list[float]) -> float:
    """Compounded return of a list of period returns."""
    acc = 1.0
    for r in rets:
        acc *= (1.0 + r)
    return acc - 1.0


def capture_window(sec_closes: list[float], ben_closes: list[float],
                   window: int) -> dict:
    """Up/down capture + down-excess over the last `window` aligned returns."""
    sr = _returns(sec_closes[-(window + 1):])
    br = _returns(ben_closes[-(window + 1):])
    n = min(len(sr), len(br))
    sr, br = sr[-n:], br[-n:]
    # CL-MDC-12: drop any index where either side's return is a skipped (None)
    # observation, keeping the remaining sector/benchmark returns aligned.
    pairs = [(sr[i], br[i]) for i in range(n) if sr[i] is not None and br[i] is not None]
    if not pairs:
        return {"down_capture": None, "up_capture": None, "down_excess": None}
    sr = [p[0] for p in pairs]
    br = [p[1] for p in pairs]
    n = len(pairs)

    s_dn = [sr[i] for i in range(n) if br[i] < 0]
    b_dn = [br[i] for i in range(n) if br[i] < 0]
    s_up = [sr[i] for i in range(n) if br[i] > 0]
    b_up = [br[i] for i in range(n) if br[i] > 0]

    down_capture = up_capture = down_excess = None
    if len(b_dn) >= MIN_DOWN_DAYS:
        cb = _compound(b_dn)
        if cb != 0:
            down_capture = _compound(s_dn) / cb
        down_excess = sum(s_dn[i] - b_dn[i] for i in range(len(b_dn))) / len(b_dn) * 100.0
    if b_up:
        cu = _compound(b_up)
        if cu != 0:
            up_capture = _compound(s_up) / cu
    return {"down_capture": down_capture, "up_capture": up_capture,
            "down_excess": down_excess}


def compute_one(sec_closes: list[float], ben_closes: list[float]) -> Optional[dict]:
    """All windows for one (sector, benchmark) close pair, or None if too short."""
    if len(sec_closes) < WINDOWS[0] + 1 or len(ben_closes) < WINDOWS[0] + 1:
        return None
    out: dict = {}
    for w in WINDOWS:
        c = capture_window(sec_closes, ben_closes, w)
        out[f"down_capture_{w}"] = c["down_capture"]
        out[f"up_capture_{w}"] = c["up_capture"]
    base = capture_window(sec_closes, ben_closes, WINDOWS[0])
    out["down_excess_63"] = base["down_excess"]
    dc, uc = out.get("down_capture_63"), out.get("up_capture_63")
    out["capture_spread_63"] = (uc - dc) if (dc is not None and uc is not None) else None
    return {k: _fin(v) for k, v in out.items()}


# ── storage (owns its own table) ──────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS capture_signals (
    numerator         TEXT NOT NULL,
    denominator       TEXT NOT NULL,
    trade_date        TEXT,
    down_capture_63   REAL,
    up_capture_63     REAL,
    down_capture_126  REAL,
    up_capture_126    REAL,
    down_capture_252  REAL,
    up_capture_252    REAL,
    down_excess_63    REAL,
    capture_spread_63 REAL,
    computed_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (numerator, denominator)
);
CREATE INDEX IF NOT EXISTS idx_capture_den ON capture_signals(denominator, down_capture_63);
"""

_COLS = [
    "numerator", "denominator", "trade_date",
    "down_capture_63", "up_capture_63", "down_capture_126", "up_capture_126",
    "down_capture_252", "up_capture_252", "down_excess_63", "capture_spread_63",
]


def _closes(conn, index_name: str) -> tuple[list[str], dict]:
    rows = conn.execute(
        "SELECT trade_date, close_value FROM index_rows "
        "WHERE index_name=? AND close_value IS NOT NULL AND close_value > 0 "
        "ORDER BY trade_date ASC", (index_name,),
    ).fetchall()
    return [r["trade_date"] for r in rows], {r["trade_date"]: r["close_value"] for r in rows}


def compute_and_store(conn=None) -> int:
    """Up/down capture for every sector (the numerators already in ratio_rows)
    vs each broad benchmark, upserted one latest row per pair. Returns rows
    stored. Manages its own connection if none given."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        sectors = [r["numerator"] for r in conn.execute(
            "SELECT DISTINCT numerator FROM ratio_rows").fetchall()]
        ben_cache: dict = {b: _closes(conn, b) for b in BROAD_BENCHMARKS}
        placeholders = ",".join("?" * len(_COLS))
        sql = f"INSERT OR REPLACE INTO capture_signals ({','.join(_COLS)}) VALUES ({placeholders})"
        n = 0
        for sec in sectors:
            s_dates, s_map = _closes(conn, sec)
            if not s_dates:
                continue
            for ben in BROAD_BENCHMARKS:
                if ben == sec:
                    continue
                b_dates, b_map = ben_cache[ben]
                common = [d for d in s_dates if d in b_map]   # date-align
                if len(common) < WINDOWS[0] + 1:
                    continue
                sec_closes = [s_map[d] for d in common]
                ben_closes = [b_map[d] for d in common]
                res = compute_one(sec_closes, ben_closes)
                if not res:
                    continue
                res["numerator"], res["denominator"] = sec, ben
                res["trade_date"] = common[-1]
                conn.execute(sql, [res.get(c) for c in _COLS])
                n += 1
        if own:
            conn.commit()
        return n
    finally:
        if own:
            cm.__exit__(None, None, None)


def latest_all(denominator: str, conn=None) -> list[dict]:
    """Every sector's latest capture vs one benchmark, falls-less first."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        rows = conn.execute(
            "SELECT * FROM capture_signals WHERE denominator=? "
            "ORDER BY down_capture_63 ASC", (denominator,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            cm.__exit__(None, None, None)


def current_all(denominator: str, conn=None, only=None) -> list[dict]:
    """On-read fallback: compute capture for each sector vs one benchmark straight
    from index_rows. `only` (an iterable of sector names) curates the universe so
    the page stays fast. Same row shape as latest_all(), falls-less first."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        sectors = [r["numerator"] for r in conn.execute(
            "SELECT DISTINCT numerator FROM ratio_rows WHERE denominator=?",
            (denominator,)).fetchall()]
        if only:
            keep = set(only)
            sectors = [s for s in sectors if s in keep]
        _, b_map = _closes(conn, denominator)
        if not b_map:
            return []
        out = []
        for sec in sectors:
            if sec == denominator:        # never a self-pair (parity with compute_and_store)
                continue
            s_dates, s_map = _closes(conn, sec)
            common = [d for d in s_dates if d in b_map]
            if len(common) < WINDOWS[0] + 1:
                continue
            res = compute_one([s_map[d] for d in common], [b_map[d] for d in common])
            if not res:
                continue
            res["numerator"], res["denominator"] = sec, denominator
            res["trade_date"] = common[-1]
            out.append(res)
        out.sort(key=lambda d: d["down_capture_63"] if d["down_capture_63"] is not None else 1e9)
        return out
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── self-check (synthetic series — no DB needed) ──────────────────────────────
def _selftest() -> None:
    # Benchmark with alternating up/down days; sector takes 50% of downs, 100% of ups.
    ben = [100.0]
    for i in range(120):
        ben.append(ben[-1] * (1.0 - 0.01 if i % 2 == 0 else 1.0 + 0.012))
    sec = [100.0]
    for i in range(1, len(ben)):
        br = ben[i] / ben[i - 1] - 1.0
        sr = br * (0.5 if br < 0 else 1.0)            # falls half as much
        sec.append(sec[-1] * (1.0 + sr))
    res = compute_one(sec, ben)
    assert res is not None, "compute_one returned None"
    dc = res["down_capture_63"]
    assert dc is not None and 0.3 < dc < 0.8, f"down_capture should be ~0.5, got {dc}"
    assert res["down_excess_63"] is not None and res["down_excess_63"] > 0, \
        "down_excess should be positive when falling less"

    # A sector that falls 1.5× as hard must read down_capture > 1.
    sec2 = [100.0]
    for i in range(1, len(ben)):
        br = ben[i] / ben[i - 1] - 1.0
        sec2.append(sec2[-1] * (1.0 + br * (1.5 if br < 0 else 1.0)))
    dc2 = compute_one(sec2, ben)["down_capture_63"]
    assert dc2 is not None and dc2 > 1.1, f"down_capture should be >1, got {dc2}"
    print("capture selftest: OK")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.selftest:
        _selftest()
        return
    stored = compute_and_store()
    log.info("capture_signals: stored %d pairs", stored)
    print(f"capture_signals: stored {stored} pairs")


if __name__ == "__main__":
    main()
