"""cost_ledger — the machine's rupee-meter: every LLM-calling job logs tokens x rate here.

WHY (D134 analytics-company plan §4-B + §5.4 · S150 LANE-B)
-----------------------------------------------------------
Budget discipline has so far been a REMEMBERED rule (CLAUDE.md Guardrail #2: runtime
API spend stays in the low hundreds of ₹/month) — nothing machine-checked. The plan's
budget law (§5.4) makes it structural:

    Steady-state runtime target ≤ ₹2,500/month excluding Claude Code build sessions.
    Every LLM-calling component ships with a hard monthly cap and logs to the
    cost-ledger; the morning line reports month-to-date vs cap. Exceeding cap =
    degrade to templates, never silent overrun.

This module is the ledger half of that law: one append-only `cost_ledger` table, a
`record()` one-liner for jobs, `month_to_date()` for the meter, and `cap_status()`
returning OK / AMBER / BREACH so callers (the estate heartbeat, and later each
LLM-calling job's own degrade check) act on a verdict instead of re-deriving
arithmetic. The heartbeat (`estate_heartbeat.py`, same lane) carries the verdict
into the one positive morning line.

DOCTRINE
--------
* Isolation (the signal_alerts precedent): owns its table via CREATE TABLE IF NOT
  EXISTS below — **no db.py edit**. Stdlib-only (sqlite3/argparse/datetime); zero
  LLM; ₹0 to run.
* Estimates, honestly labeled: `inr_estimate` = tokens x published USD price x an
  editable FX constant — a budget GUARD, not an accounting system. Unknown models
  are charged the conservative `_default` (Sonnet-class) rate so the meter can only
  over-count, never silently under-count.
* Rates are DATA, in one place: edit `USD_INR` / `RATES_INR_PER_MTOK` below when
  prices or FX move. Keys match the model ids the repo actually configures
  (src/core/settings.py, enrich.py); dated variants resolve by longest-prefix.
* Hermetic by construction: every public function accepts `conn=` (reuse a caller's
  connection — the pattern jobs holding `get_conn()` need) or `db_path=` (tests /
  CLI point at a temp SQLite file). Only when BOTH are absent does it lazily import
  the canonical `src.core.db.DB_PATH` — so tests never touch settings or hermes.db.

API
---
    record(job, model, tokens_in, tokens_out, note=..., conn=|db_path=...) -> ₹ recorded
    month_to_date(month="YYYY-MM"|None, conn=|db_path=...)                 -> float ₹
    cap_status(cap_inr=DEFAULT_CAP_INR, month=None, conn=|db_path=...)
        -> {"status": "OK"|"AMBER"|"BREACH", "mtd_inr", "cap_inr", "fraction", "month"}

CLI (bare run = --report)
-------------------------
    python -m src.automation.cost_ledger --report [--month YYYY-MM] [--cap 2500] [--db PATH]
    python -m src.automation.cost_ledger --selftest
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

# --- rates (DATA — edit here when prices/FX move) -----------------------------------
# FX: approximate mid-2026 INR per USD. An editable constant, not a live feed — the
# ledger is a budget guard; a few percent of FX drift is immaterial at a ₹2,500 cap.
USD_INR = 88.0

# ₹ per MILLION tokens, (input, output), expressed as published-USD-price x USD_INR so
# the source stays visible. Sources: Anthropic pricing page (Haiku 4.5 $1/$5,
# Sonnet 4.5/4.6 $3/$15 at ≤200K context, Opus 4.1 $15/$75 per Mtok) and Google AI
# pricing (Gemini 2.5 Flash-Lite $0.10/$0.40, Flash $0.30/$2.50 per Mtok), as of
# 2026-07 knowledge. Keys match the ids configured in src/core/settings.py + enrich.py.
RATES_INR_PER_MTOK = {
    "claude-haiku-4-5":      (1.00 * USD_INR,   5.00 * USD_INR),
    "claude-sonnet-4-6":     (3.00 * USD_INR,  15.00 * USD_INR),
    "claude-sonnet-4-5":     (3.00 * USD_INR,  15.00 * USD_INR),
    "claude-opus-4-1":       (15.00 * USD_INR, 75.00 * USD_INR),
    "gemini-2.5-flash-lite": (0.10 * USD_INR,   0.40 * USD_INR),
    "gemini-2.5-flash":      (0.30 * USD_INR,   2.50 * USD_INR),
    # Conservative fallback for any model id we have not tabled: Sonnet-class, so an
    # unknown model OVER-counts spend rather than slipping under the cap unmetered.
    "_default":              (3.00 * USD_INR,  15.00 * USD_INR),
}

# --- budget law (plan §5.4) ----------------------------------------------------------
DEFAULT_CAP_INR = 2500.0   # steady-state runtime target, ₹/month, excl. build sessions
AMBER_AT = 0.80            # fraction of cap where the meter turns AMBER (early warning)

# --- owned table (isolation: NOT in db.py SCHEMA_BASE — signal_alerts precedent) -----
_SCHEMA = """
CREATE TABLE IF NOT EXISTS cost_ledger (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL DEFAULT (datetime('now')),  -- UTC, sqlite datetime format
    job          TEXT NOT NULL,                            -- e.g. 'news_screen', 'enrich'
    model        TEXT NOT NULL,                            -- model id as the caller knows it
    tokens_in    INTEGER NOT NULL DEFAULT 0,
    tokens_out   INTEGER NOT NULL DEFAULT 0,
    inr_estimate REAL NOT NULL,                            -- tokens x rate (or caller override)
    note         TEXT
);
CREATE INDEX IF NOT EXISTS idx_cost_ledger_ts  ON cost_ledger(ts);
CREATE INDEX IF NOT EXISTS idx_cost_ledger_job ON cost_ledger(job, ts);
"""


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open the ledger DB. db_path=None -> the canonical hermes.db, imported LAZILY so
    hermetic tests and --selftest never pull src.core.db (and its settings chain)."""
    if db_path is None:
        from src.core.db import DB_PATH  # deferred on purpose (see docstring)
        db_path = str(DB_PATH)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


# --- rate lookup (pure) --------------------------------------------------------------

def _rate_for(model: str) -> tuple[float, float, str]:
    """(₹/Mtok in, ₹/Mtok out, matched_key). Exact key first, then longest prefix —
    so dated ids like 'claude-haiku-4-5-20251001' meter at the family rate — then
    the conservative '_default'."""
    m = (model or "").strip().lower()
    if m in RATES_INR_PER_MTOK and m != "_default":
        ri, ro = RATES_INR_PER_MTOK[m]
        return ri, ro, m
    for key in sorted((k for k in RATES_INR_PER_MTOK if k != "_default"),
                      key=len, reverse=True):
        if m.startswith(key):
            ri, ro = RATES_INR_PER_MTOK[key]
            return ri, ro, key
    ri, ro = RATES_INR_PER_MTOK["_default"]
    return ri, ro, "_default"


def estimate_inr(model: str, tokens_in: int, tokens_out: int) -> float:
    """Pure tokens-x-rate arithmetic (no DB). Exposed so jobs can pre-check a call's
    cost against their own cap before spending it."""
    ri, ro, _ = _rate_for(model)
    return (int(tokens_in) / 1e6) * ri + (int(tokens_out) / 1e6) * ro


def fmt_inr(x: float) -> str:
    """'2,500.00' -> '2,500'; '118.42' stays '118.42'. One formatting rule everywhere."""
    s = f"{float(x):,.2f}"
    return s[:-3] if s.endswith(".00") else s


# --- the ledger ----------------------------------------------------------------------

def record(job: str, model: str, tokens_in: int = 0, tokens_out: int = 0, *,
           note: Optional[str] = None, inr_override: Optional[float] = None,
           ts: Optional[str] = None,
           conn: Optional[sqlite3.Connection] = None,
           db_path: Optional[str] = None) -> float:
    """Append one metered call; returns the ₹ recorded. `ts` override exists for tests
    (month boundaries); `inr_override` for callers with exact billing knowledge."""
    ti, to = int(tokens_in or 0), int(tokens_out or 0)
    if ti < 0 or to < 0:
        raise ValueError("cost_ledger.record: token counts must be >= 0")
    if not (job or "").strip() or not (model or "").strip():
        raise ValueError("cost_ledger.record: job and model are required")
    inr = float(inr_override) if inr_override is not None else estimate_inr(model, ti, to)
    own = conn is None
    c = conn if conn is not None else _connect(db_path)
    try:
        ensure_schema(c)
        if ts:
            c.execute(
                "INSERT INTO cost_ledger (ts, job, model, tokens_in, tokens_out,"
                " inr_estimate, note) VALUES (?,?,?,?,?,?,?)",
                (str(ts), job.strip(), model.strip(), ti, to, inr, note))
        else:
            c.execute(
                "INSERT INTO cost_ledger (job, model, tokens_in, tokens_out,"
                " inr_estimate, note) VALUES (?,?,?,?,?,?)",
                (job.strip(), model.strip(), ti, to, inr, note))
        c.commit()
        return inr
    finally:
        if own:
            c.close()


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def month_to_date(month: Optional[str] = None, *,
                  conn: Optional[sqlite3.Connection] = None,
                  db_path: Optional[str] = None) -> float:
    """Total ₹ recorded in `month` ('YYYY-MM'; default = current UTC month)."""
    mm = (month or _current_month()).strip()[:7]
    own = conn is None
    c = conn if conn is not None else _connect(db_path)
    try:
        ensure_schema(c)
        row = c.execute(
            "SELECT COALESCE(SUM(inr_estimate), 0.0) FROM cost_ledger"
            " WHERE substr(ts, 1, 7) = ?", (mm,)).fetchone()
        return float(row[0] or 0.0)
    finally:
        if own:
            c.close()


def breakdown(month: Optional[str] = None, *,
              conn: Optional[sqlite3.Connection] = None,
              db_path: Optional[str] = None) -> list[dict]:
    """Per (job, model) spend for the month, biggest first — the --report body."""
    mm = (month or _current_month()).strip()[:7]
    own = conn is None
    c = conn if conn is not None else _connect(db_path)
    try:
        ensure_schema(c)
        rows = c.execute(
            "SELECT job, model, COUNT(*) AS calls,"
            "       SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out,"
            "       SUM(inr_estimate) AS inr"
            " FROM cost_ledger WHERE substr(ts, 1, 7) = ?"
            " GROUP BY job, model ORDER BY inr DESC", (mm,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def cap_status(cap_inr: float = DEFAULT_CAP_INR, month: Optional[str] = None, *,
               conn: Optional[sqlite3.Connection] = None,
               db_path: Optional[str] = None) -> dict:
    """The budget-law verdict (plan §5.4). Bands: OK below AMBER_AT x cap; AMBER from
    AMBER_AT x cap up to (not incl.) cap; BREACH at/over cap — the degrade trigger."""
    cap = float(cap_inr)
    if cap <= 0:
        raise ValueError("cost_ledger.cap_status: cap_inr must be > 0")
    mm = (month or _current_month()).strip()[:7]
    mtd = month_to_date(mm, conn=conn, db_path=db_path)
    frac = mtd / cap
    status = "BREACH" if frac >= 1.0 else ("AMBER" if frac >= AMBER_AT else "OK")
    return {"status": status, "mtd_inr": round(mtd, 2), "cap_inr": cap,
            "fraction": round(frac, 4), "month": mm}


# --- report + selftest ----------------------------------------------------------------

def report(month: Optional[str] = None, cap_inr: float = DEFAULT_CAP_INR, *,
           conn: Optional[sqlite3.Connection] = None,
           db_path: Optional[str] = None) -> str:
    own = conn is None
    c = conn if conn is not None else _connect(db_path)
    try:
        st = cap_status(cap_inr, month, conn=c)
        pct = int(round(st["fraction"] * 100))
        lines = [
            f"cost-ledger report — {st['month']}",
            f"  MTD ₹{fmt_inr(st['mtd_inr'])} / cap ₹{fmt_inr(st['cap_inr'])}"
            f" ({pct}%) -> {st['status']}",
        ]
        rows = breakdown(st["month"], conn=c)
        if not rows:
            lines.append("  (no metered calls this month)")
        for r in rows:
            lines.append(
                f"  {r['job']:<20} {r['model']:<24} ₹{fmt_inr(r['inr']):>10}"
                f"  ({r['calls']} calls, {int(r['tokens_in'] or 0):,} in /"
                f" {int(r['tokens_out'] or 0):,} out)")
        return "\n".join(lines)
    finally:
        if own:
            c.close()


def selftest() -> int:
    """Hermetic end-to-end on a temp SQLite file: record -> MTD scoping -> cap bands
    -> report. Exit 0 on pass, 1 on fail. Never touches the canonical DB."""
    import tempfile
    fd, path = tempfile.mkstemp(prefix="hermes-cost-ledger-selftest-", suffix=".db")
    os.close(fd)
    try:
        c = _connect(path)
        try:
            inr = record("selftest_job", "claude-haiku-4-5", 1_000_000, 1_000_000,
                         note="selftest", conn=c)
            want = sum(RATES_INR_PER_MTOK["claude-haiku-4-5"])
            assert abs(inr - want) < 1e-9, f"haiku 1M/1M metered {inr}, want {want}"
            # prefix match: a dated id meters at the family rate
            inr2 = record("selftest_job", "claude-haiku-4-5-20251001", 1_000_000, 0, conn=c)
            assert abs(inr2 - RATES_INR_PER_MTOK["claude-haiku-4-5"][0]) < 1e-9
            # a previous-month row must NOT count toward this month's meter
            prev = (datetime.now(timezone.utc).replace(day=1)
                    - timedelta(days=1)).strftime("%Y-%m-15 00:00:00")
            record("old_month", "gemini-2.5-flash-lite", 1_000_000, 0, ts=prev, conn=c)
            mtd = month_to_date(conn=c)
            assert abs(mtd - (inr + inr2)) < 1e-9, f"MTD {mtd} leaked across months"
            assert cap_status(conn=c)["status"] == "OK"
            assert cap_status(cap_inr=mtd / 0.85, conn=c)["status"] == "AMBER"
            assert cap_status(cap_inr=mtd / 2.0, conn=c)["status"] == "BREACH"
            print(report(conn=c))
        finally:
            c.close()
        print("cost_ledger selftest OK")
        return 0
    except AssertionError as e:
        print(f"cost_ledger selftest FAIL: {e}")
        return 1
    finally:
        try:
            os.remove(path)
        except OSError:
            pass  # Windows file-lock stragglers live in tmp; harmless


def main(argv: Optional[list] = None) -> int:
    # Windows consoles can be cp1252; the ₹ glyph must never crash a report.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(description="Hermes cost-ledger (₹-meter, plan §5.4)")
    p.add_argument("--report", action="store_true", help="print MTD spend vs cap (default)")
    p.add_argument("--selftest", action="store_true", help="hermetic temp-DB self-check")
    p.add_argument("--month", default=None, help="YYYY-MM (default: current UTC month)")
    p.add_argument("--cap", type=float, default=DEFAULT_CAP_INR,
                   help=f"monthly cap in ₹ (default {DEFAULT_CAP_INR:g}, plan §5.4)")
    p.add_argument("--db", default=None, help="SQLite path override (tests/dry-runs)")
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    print(report(a.month, a.cap, db_path=a.db))
    return 0


if __name__ == "__main__":
    sys.exit(main())
