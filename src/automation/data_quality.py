"""Continuous data-quality monitor for the research / provenance / CCI lane.

A cheap, deterministic battery of integrity checks (NO LLM, NO network) over the data classes this
lane owns, run on a timer so corruption + drift surface early instead of at read time. It is the
companion to ``provenance.py`` (which says *where a value came from*); this says *is the value sane*.

What it catches — grouped by severity:
  * **critical** — corruption that breaks reads: out-of-range periods (the real ``period_year=225``
    row), future/garbage dates, a modeled ``report_date`` BEFORE its ``period_end`` (impossible),
    credibility levels outside 0–100.
  * **warn** — drift vs expectation: the effective knowable-lag LEAK creeping back up, the de-model
    rate falling, the synthetic-lag calibration going stale, negative/!100 holdings.
  * **info** — counts + cross-DB orphans worth knowing but not acting on.

Isolation (house pattern): a NEW module that OWNS one append-only table (``data_quality_runs``) via
an embedded schema; it never edits another module. Reads provenance's public API
(``lag_audit``/``coverage_snapshot``/``period_key``) read-only. Degrades gracefully on the 4-symbol
local stub / absent research.db — every check is wrapped so one failure can't abort the run.

CLI:
    python -m src.automation.data_quality --run        # run all checks, print + persist a snapshot
    python -m src.automation.data_quality --run --quiet # persist only (for the timer)
    python -m src.automation.data_quality --last        # print the most recent persisted run
    python -m src.automation.data_quality --selftest    # synthetic in-memory validation
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sqlite3
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.automation import provenance

log = logging.getLogger("hermes.data_quality")

RESEARCH_DB = provenance.RESEARCH_DB

SEV_OK, SEV_INFO, SEV_WARN, SEV_CRIT = "ok", "info", "warn", "critical"
_RANK = {SEV_OK: 0, SEV_INFO: 1, SEV_WARN: 2, SEV_CRIT: 3}

# drift thresholds (tunable; chosen from the Lane D/H calibration baselines)
LEAK_WARN_PCT = 6.0          # effective blended look-ahead leak above this → warn
DEMODEL_WARN = 0.55          # de-model rate below this (post-backfill ≈0.73) → warn
CALIB_STALE_DAYS = 30        # synthetic-lag calibration older than this → warn
RESTATE_WARN_PCT = 5.0       # kill-switch #4 (validation memo §5): >5% of gate-passed
                             # symbols revised within 30d → pause auto-ingest
RESTATE_MIN_UNIVERSE = 20    # below this many gate-passed symbols the % is noise (warmup)
SHAREHOLDING_XBRL_STALE_DAYS = 150  # §7.7(c): no NEW SEBI Reg-31 XBRL shareholding broadcast in
                             # ~1.5 quarters (filings land ~45d post-quarter) → the feed may be dead

_SCHEMA = """
CREATE TABLE IF NOT EXISTS data_quality_runs (
    run_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status      TEXT,
    n_critical  INTEGER,
    n_warn      INTEGER,
    report_json TEXT,
    PRIMARY KEY (run_at)
);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


def _check(name, severity, count, message, sample=None) -> dict:
    return {"check": name, "severity": severity, "count": int(count),
            "message": message, "sample": sample or []}


def _research_ro():
    if not os.path.exists(RESEARCH_DB):
        return None
    try:
        return sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=20)
    except sqlite3.Error:
        return None


def _table_exists(c, name) -> bool:
    try:
        return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None
    except sqlite3.Error:
        return False


# ── individual checks (each returns a _check dict; never raises — wrapped by run()) ──
def chk_credibility_periods(c) -> dict:
    if not _table_exists(c, "credibility_series"):
        return _check("credibility_series.period_sanity", SEV_OK, 0, "table absent")
    yr = date.today().year + 1
    bad = c.execute(
        "SELECT symbol, period_year, period_month FROM credibility_series "
        "WHERE period_year NOT BETWEEN 2000 AND ? OR period_month NOT BETWEEN 1 AND 12",
        (yr,)).fetchall()
    sev = SEV_CRIT if bad else SEV_OK
    return _check("credibility_series.period_sanity", sev, len(bad),
                  "period_year/period_month out of valid range (the period_year=225 class of bug)",
                  [list(b) for b in bad[:10]])


def chk_credibility_levels(c) -> dict:
    if not _table_exists(c, "credibility_series"):
        return _check("credibility_series.level_range", SEV_OK, 0, "table absent")
    bad = c.execute("SELECT symbol, level FROM credibility_series WHERE level < 0 OR level > 100").fetchall()
    sev = SEV_CRIT if bad else SEV_OK
    return _check("credibility_series.level_range", sev, len(bad),
                  "credibility level outside 0–100", [list(b) for b in bad[:10]])


def chk_concall_periods(c) -> dict:
    """Malformed period labels in the UPSTREAM concalls table (e.g. 'Aug 0225' → year 225). INFO:
    cci_series now skips these so they no longer reach credibility_series; this surfaces the source
    row for whoever owns the ingestion to repair, without this lane mutating parallel-owned data."""
    if not _table_exists(c, "concalls"):
        return _check("concalls.period_labels", SEV_OK, 0, "table absent")
    bad = c.execute(
        "SELECT symbol, period_label FROM concalls "
        "WHERE period_label GLOB '* [0-9][0-9][0-9][0-9]' "
        "AND CAST(substr(period_label, length(period_label)-3) AS INT) NOT BETWEEN 2000 AND 2030"
    ).fetchall()
    return _check("concalls.period_labels", SEV_INFO if bad else SEV_OK, len(bad),
                  "upstream concalls period_label with an out-of-range year (source corruption)",
                  [list(b) for b in bad[:10]])


def chk_concall_scores(c) -> dict:
    if not _table_exists(c, "concall_scores"):
        return _check("concall_scores.sanity", SEV_OK, 0, "table absent")
    cols = {r[1] for r in c.execute("PRAGMA table_info(concall_scores)")}
    conds = []
    if "guidance_accuracy_score" in cols:
        conds.append("(guidance_accuracy_score IS NOT NULL AND (guidance_accuracy_score < 0 OR guidance_accuracy_score > 100))")
    if "n_promises_resolved" in cols:
        conds.append("(n_promises_resolved IS NOT NULL AND n_promises_resolved < 0)")
    if not conds:
        return _check("concall_scores.sanity", SEV_OK, 0, "no checkable columns")
    n = c.execute(f"SELECT COUNT(*) FROM concall_scores WHERE {' OR '.join(conds)}").fetchone()[0]
    sev = SEV_CRIT if n else SEV_OK
    return _check("concall_scores.sanity", sev, n, "guidance_accuracy_score out of 0–100 or n_promises_resolved < 0")


def chk_provenance_knowable(c) -> dict:
    if not _table_exists(c, "provenance_knowable"):
        return _check("provenance_knowable.sanity", SEV_OK, 0, "table absent")
    today = date.today().isoformat()
    issues = []
    fut = c.execute("SELECT COUNT(*) FROM provenance_knowable WHERE substr(knowable_at,1,10) > ?", (today,)).fetchone()[0]
    if fut:
        issues.append(f"{fut} knowable_at in the future")
    # malformed period keys: fundamentals/shareholding keys must be symbol|ptype|period_end
    # (exactly 3 parts; ptype A/Q; period_end an ISO date). Push the structural test to SQL
    # so we don't pull the whole table into Python each run. A key is GOOD iff it matches the
    # GLOB '*|[AQ]|####-##-##*' AND has exactly two pipes (so 'X|A|...|extra' is rejected). The
    # GLOB '####-##-##' enforces the date *shape*; an impossible date (2024-13-40) is rare and
    # not worth a Python pass. (CL-PROV-07)
    bad_key = c.execute(
        "SELECT COUNT(*) FROM provenance_knowable "
        "WHERE data_class IN ('fundamentals_history','shareholding_history') AND NOT ("
        "  key GLOB '*|[AQ]|[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*' "
        "  AND length(key) - length(replace(key,'|','')) = 2 )"
    ).fetchone()[0]
    if bad_key:
        issues.append(f"{bad_key} malformed period keys")
    n = fut + bad_key
    sev = SEV_CRIT if fut else (SEV_WARN if bad_key else SEV_OK)
    return _check("provenance_knowable.sanity", sev, n, "; ".join(issues) or "ok")


def chk_calibration_freshness(c) -> dict:
    if not _table_exists(c, "provenance_lag_calibration"):
        return _check("calibration.freshness", SEV_INFO, 0, "not calibrated yet (defaults in force)")
    rows = c.execute("SELECT data_class, period_type, chosen_lag, calibrated_at FROM provenance_lag_calibration").fetchall()
    if not rows:
        return _check("calibration.freshness", SEV_INFO, 0, "no calibration rows")
    today = date.today()
    stale = 0
    for _dc, _pt, _lag, cat in rows:
        try:
            age = (today - date.fromisoformat(str(cat)[:10])).days
            if age > CALIB_STALE_DAYS:
                stale += 1
        except (ValueError, TypeError):
            stale += 1
    sev = SEV_WARN if stale else SEV_OK
    # flood-gated classes (provenance._CAL_MIN_N) with no calibration row yet: show the
    # countdown so the season digest can watch the Reg-31 flood approach the bar.
    pending = ""
    try:
        from src.automation.provenance import _CAL_MIN_N
        have = {r[0] for r in rows}
        parts = []
        for cls, need in _CAL_MIN_N.items():
            if cls not in have:
                n = c.execute("SELECT COUNT(*) FROM provenance_knowable WHERE data_class=?",
                              (cls,)).fetchone()[0]
                parts.append(f"{cls} gated: {n}/{need} real dates (calibrates itself when the flood lands)")
        if parts:
            pending = "; " + "; ".join(parts)
    except Exception:  # noqa: BLE001
        pass
    return _check("calibration.freshness", sev, stale,
                  f"{stale}/{len(rows)} calibration rows older than {CALIB_STALE_DAYS}d{pending}",
                  [[r[0], r[1], r[2], str(r[3])[:10]] for r in rows])


def chk_leak_and_demodel(c) -> dict:
    """Drift: the effective look-ahead leak creeping up / the de-model rate falling."""
    try:
        la = provenance.lag_audit(conn=c, persist=False).get("fundamentals_history", {})
    except Exception as e:  # noqa: BLE001
        return _check("knowable.leak_drift", SEV_INFO, 0, f"lag_audit unavailable: {e}")
    if la.get("status") != "ok":
        return _check("knowable.leak_drift", SEV_INFO, 0, f"lag_audit status={la.get('status')}")
    eff = la.get("effective", {})
    leak = eff.get("blended_expected_leak_pct")
    demodel = eff.get("demodel_rate")
    issues, sev = [], SEV_OK
    if leak is not None and leak > LEAK_WARN_PCT:
        issues.append(f"blended leak {leak}% > {LEAK_WARN_PCT}%"); sev = SEV_WARN
    if demodel is not None and demodel < DEMODEL_WARN:
        issues.append(f"de-model {demodel} < {DEMODEL_WARN}")
        sev = SEV_WARN if sev == SEV_OK else sev
    return _check("knowable.leak_drift", sev, len(issues),
                  "; ".join(issues) or f"leak={leak}% demodel={demodel} (ok)",
                  [{"baseline": la.get("baseline_producer_model", {}).get("leak_pct"),
                    "calibrated": la.get("calibrated_model", {}).get("leak_pct"),
                    "effective": leak, "demodel": demodel}])


def chk_fundamentals_dates(r) -> dict:
    if r is None or not _table_exists(r, "fundamentals_history"):
        return _check("fundamentals_history.dates", SEV_OK, 0, "research.db absent")
    today = date.today().isoformat()
    # report_date strictly BEFORE period_end is impossible (a result filed before the period closed)
    before = r.execute(
        "SELECT COUNT(*) FROM fundamentals_history WHERE report_date IS NOT NULL AND report_date < period_end").fetchone()[0]
    future = r.execute("SELECT COUNT(*) FROM fundamentals_history WHERE period_end > ?", (today,)).fetchone()[0]
    sev = SEV_CRIT if before else (SEV_WARN if future else SEV_OK)
    msg = []
    if before:
        msg.append(f"{before} rows report_date < period_end")
    if future:
        msg.append(f"{future} rows period_end in the future")
    return _check("fundamentals_history.dates", sev, before + future, "; ".join(msg) or "ok")


def chk_security_master(c) -> dict:
    if not _table_exists(c, "security_master"):
        return _check("security_master.sanity", SEV_OK, 0, "table absent")
    bad_status = c.execute(
        "SELECT COUNT(*) FROM security_master WHERE status NOT IN ('ACTIVE','INACTIVE')").fetchone()[0]
    bad_dates = c.execute(
        "SELECT COUNT(*) FROM security_master WHERE last_date < first_date").fetchone()[0]
    # INACTIVE + currently_listed=1 is NOT a contradiction — it is the SUSPENDED signature
    # (in the NSE equity list but no trades for >ACTIVE_GAP_DAYS, e.g. KALYANI 2025-07).
    # Surface it as information so nobody re-files it as corruption.
    suspended = c.execute(
        "SELECT COUNT(*) FROM security_master WHERE status='INACTIVE' AND currently_listed=1").fetchone()[0]
    sev = SEV_WARN if (bad_status or bad_dates) else (SEV_INFO if suspended else SEV_OK)
    return _check("security_master.sanity", sev, bad_status + bad_dates,
                  f"{bad_status} bad status, {bad_dates} last_date<first_date; "
                  f"{suspended} listed-but-suspended (INACTIVE + in equity list — real state)")


def chk_cross_db_orphans(c, r) -> dict:
    """credibility_series symbols absent from security_master (informational coverage gap)."""
    if r is None or not _table_exists(c, "credibility_series") or not _table_exists(c, "security_master"):
        return _check("xdb.credibility_orphans", SEV_OK, 0, "tables absent")
    sm = {x[0] for x in c.execute("SELECT symbol FROM security_master")}
    cs = {x[0] for x in c.execute("SELECT DISTINCT symbol FROM credibility_series")}
    orphans = sorted(cs - sm)
    return _check("xdb.credibility_orphans", SEV_INFO if orphans else SEV_OK, len(orphans),
                  "credibility_series symbols not in security_master", orphans[:10])


# ── kill-switch checks (validation memo §5 — docs/validation-memo.md) ─────────
def chk_market_freshness(c) -> dict:
    """Kill-switch #2: EOD staleness. bhavcopy older than ~2 trading days → critical;
    the momentum scan lagging the latest trade date → warn (its cache self-heals nightly)."""
    if not _table_exists(c, "bhavcopy_rows"):
        return _check("killswitch.market_freshness", SEV_OK, 0, "table absent")
    bmax = c.execute("SELECT MAX(trade_date) FROM bhavcopy_rows").fetchone()[0]
    if not bmax:
        return _check("killswitch.market_freshness", SEV_CRIT, 1, "bhavcopy empty")
    age = (date.today() - date.fromisoformat(str(bmax)[:10])).days
    if age > 4:            # 2 trading days + weekend/holiday slack
        return _check("killswitch.market_freshness", SEV_CRIT, 1,
                      f"bhavcopy stale: last trade_date {bmax} ({age}d ago)")
    smax = None
    if _table_exists(c, "momentum_scan"):
        smax = c.execute("SELECT MAX(as_of) FROM momentum_scan").fetchone()[0]
    if smax and smax < bmax:
        return _check("killswitch.market_freshness", SEV_WARN, 1,
                      f"momentum_scan as_of {smax} < bhavcopy {bmax} (next 21:30 UTC run should heal)")
    return _check("killswitch.market_freshness", SEV_OK, 0, f"bhavcopy {bmax}, scan {smax or 'n/a'}")


def chk_regime_guard(c) -> dict:
    """Kill-switch #1 (partial): Nifty-50 below its 200DMA = momentum regime OFF — the
    shortlist surface is suspect in a crash regime. (The WML-drawdown component waits on
    accumulated momentum_scan history.)"""
    if not _table_exists(c, "index_rows"):
        return _check("killswitch.regime", SEV_OK, 0, "table absent")
    rows = c.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name='Nifty 50' "
        "ORDER BY trade_date DESC LIMIT 200").fetchall()
    if len(rows) < 200:
        return _check("killswitch.regime", SEV_OK, 0, f"only {len(rows)} Nifty rows (warmup)")
    # AUD-25: guard against a FROZEN index feed. Without a date check the 200DMA + last close are
    # computed on whatever 200 rows exist — a dead index feed then yields a plausible-but-stale
    # regime verdict presented as current. If the newest Nifty row is stale, say so, don't verdict.
    newest = str(rows[0][0])[:10]
    try:
        age = (date.today() - date.fromisoformat(newest)).days
    except (ValueError, TypeError):
        age = 0
    if age > 5:
        return _check("killswitch.regime", SEV_WARN, 1,
                      f"regime UNKNOWN — Nifty 50 index feed stale (last {newest}, {age}d ago); "
                      f"the 200DMA verdict would run on frozen data")
    closes = [float(r[1]) for r in rows if r[1] is not None]
    last, ma200 = closes[0], sum(closes) / len(closes)
    if last < ma200:
        return _check("killswitch.regime", SEV_WARN, 1,
                      f"Nifty 50 {last:.0f} < 200DMA {ma200:.0f} — momentum regime OFF (as of {newest})")
    return _check("killswitch.regime", SEV_OK, 0,
                  f"Nifty 50 {last:.0f} >= 200DMA {ma200:.0f} (as of {newest})")


def chk_universe_drift(c) -> dict:
    """Kill-switch #5: scan-eligible universe moving ±20% vs ~a month ago → investigate
    the liquidity gate / equity list before trusting the ranks."""
    if not _table_exists(c, "momentum_scan"):
        return _check("killswitch.universe_drift", SEV_OK, 0, "table absent")
    counts = c.execute(
        "SELECT as_of, COUNT(*) FROM momentum_scan GROUP BY as_of ORDER BY as_of DESC LIMIT 25"
    ).fetchall()
    if len(counts) < 2:
        return _check("killswitch.universe_drift", SEV_OK, 0, f"{len(counts)} scan snapshot(s) (warmup)")
    latest, oldest = counts[0], counts[-1]
    if oldest[1] > 0:
        drift = (latest[1] - oldest[1]) / oldest[1] * 100.0
        if abs(drift) > 20.0:
            return _check("killswitch.universe_drift", SEV_WARN, 1,
                          f"universe {oldest[1]} ({oldest[0]}) -> {latest[1]} ({latest[0]}) = {drift:+.0f}%")
    return _check("killswitch.universe_drift", SEV_OK, 0,
                  f"universe {oldest[1]} -> {latest[1]} across {len(counts)} scans")


def chk_restatement_spike(r) -> dict:
    """Kill-switch #4: >RESTATE_WARN_PCT% of gate-passed symbols receiving revised XBRL
    filings within the trailing 30 days → pause XBRL auto-ingest, re-run the reconciliation
    cohort. Reads the revision ledger journaled by fundamentals_xbrl.write_rows (INSERT OR
    REPLACE on fundamentals_history erases the prior value, so the ledger is the only
    restatement record)."""
    if (r is None or not _table_exists(r, "fundamentals_restatements")
            or not _table_exists(r, "fundamentals_xbrl_gate")):
        return _check("killswitch.restatement_spike", SEV_OK, 0,
                      "ledger/gate tables absent (no XBRL ingest yet)")
    denom = r.execute("SELECT COUNT(*) FROM fundamentals_xbrl_gate WHERE pass=1").fetchone()[0]
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    rows = r.execute(
        "SELECT DISTINCT symbol FROM fundamentals_restatements WHERE substr(broadcast,1,10) >= ?",
        (cutoff,)).fetchall()
    num = len(rows)
    if denom < RESTATE_MIN_UNIVERSE:
        return _check("killswitch.restatement_spike", SEV_INFO if num else SEV_OK, num,
                      f"warmup: {num} restated / {denom} gate-passed symbols "
                      f"(% is noise below {RESTATE_MIN_UNIVERSE})")
    pct = num / denom * 100.0
    if pct > RESTATE_WARN_PCT:
        return _check("killswitch.restatement_spike", SEV_WARN, num,
                      f"{num}/{denom} gate-passed symbols ({pct:.1f}%) revised in 30d "
                      f"> {RESTATE_WARN_PCT}% — pause XBRL auto-ingest, re-run reconciliation cohort",
                      [x[0] for x in rows[:10]])
    return _check("killswitch.restatement_spike", SEV_OK, num,
                  f"{num}/{denom} gate-passed symbols ({pct:.1f}%) revised in 30d")


def chk_feed_freshness(c) -> dict:
    """Event-feed liveness — the check that would have caught the Mar-2026 corporates-pit
    endpoint death within a week (dataset A silently ingested 0 rows for 4 months). Covers 10
    hermes.db feeds per its own cadence: near-daily (insider · bulk/block · FII-DII · participant
    OI · F&O OI · news), monthly (ratings · SAST reg-29/pledge), quarterly-clustered (concalls).
    (AUD-25.) Research.db feeds fundamentals_history / shareholding_history are DELIBERATELY not
    recency-checked here: both carry forward-dated `report_date`s (estimated filing dates), so a
    naive MAX(report_date) reads perpetually "fresh" and would hide a real death — their integrity
    is covered by chk_fundamentals_dates + chk_leak_and_demodel; a true arrival-recency check needs
    an `ingested_at` column, tracked as a residual."""
    problems, notes = 0, []
    for table, col, max_age, label in (
            ("insider_events", "disclosure_dt", 7, "insider disclosures"),
            ("credit_rating_events", "broadcast_dt", 30, "credit-rating events"),
            ("sast_reg29_events", "broadcast_dt", 21, "SAST reg-29 stakes"),
            ("sast_pledge_events", "broadcast_dt", 30, "SAST pledge flow"),
            ("bulk_block_deals", "trade_date", 5, "bulk/block deals"),
            ("fii_dii_flows", "trade_date", 5, "FII/DII flows"),
            ("participant_oi", "trade_date", 5, "participant OI"),
            ("fno_oi_signals", "trade_date", 5, "F&O OI"),
            # AUD-25 coverage: the news intelligence feed (near-daily; sent_at tracks PROCESSING,
            # not Telegram delivery, so it stays fresh while Telegram is blocked in India) and the
            # concall filings feed (quarterly-clustered → a loose 120d catches a dead endpoint —
            # the Mar-2026 corporates-pit silent-death class — without off-season false alarms).
            ("sent_news", "sent_at", 7, "news feed"),
            ("concalls", "result_filing_dt", 120, "concall filings")):
        if not _table_exists(c, table):
            continue
        mx = c.execute(f"SELECT MAX({col}) FROM {table}").fetchone()[0]
        if not mx:
            problems += 1
            notes.append(f"{label}: empty")
            continue
        age = (date.today() - date.fromisoformat(str(mx)[:10])).days
        if age > max_age:
            problems += 1
            notes.append(f"{label}: newest {mx} ({age}d ago > {max_age}d)")
        else:
            notes.append(f"{label}: {mx} ok")
    return _check("killswitch.feed_freshness", SEV_WARN if problems else SEV_OK,
                  problems, "; ".join(notes) or "tables absent")


def chk_index_name_variants(c) -> dict:
    """NSE has historically flipped index-name casing ("NIFTY Midcap 50" vs "Nifty Midcap 50"),
    silently splitting one index's history across two keys. The known groups are canonicalised
    at ingest (indexes._NAME_CANON) + merged in the data; this check WARNs if a NEW variant
    group ever appears so it gets folded into the canon map instead of splitting history again."""
    if not _table_exists(c, "index_rows"):
        return _check("index.name_variants", SEV_OK, 0, "table absent")
    groups = c.execute(
        "SELECT GROUP_CONCAT(index_name, ' | ') FROM (SELECT DISTINCT index_name FROM index_rows) "
        "GROUP BY lower(index_name) HAVING COUNT(*) > 1").fetchall()
    if groups:
        return _check("index.name_variants", SEV_WARN, len(groups),
                      "case-variant index keys splitting history (extend indexes._NAME_CANON + merge)",
                      [g[0] for g in groups[:10]])
    return _check("index.name_variants", SEV_OK, 0, "no case-variant index keys")


def chk_fund_leak(c) -> dict:
    """Regression guard for the ETF-in-EQ-series exclusion: FUND-class instruments
    (security_master.instrument_class, fed by nse_etf_list + INF ISINs) must never appear
    in the RANKED momentum output — an ETF in a stock momentum book is wrong data. The raw
    layers (bhavcopy/stock_signals) legitimately carry fund rows; ranked outputs must not."""
    if not (_table_exists(c, "momentum_scan") and _table_exists(c, "security_master")):
        return _check("fund.leak", SEV_OK, 0, "tables absent")
    try:
        funds = c.execute(
            "SELECT COUNT(*) FROM momentum_scan mo JOIN security_master m ON m.symbol=mo.symbol "
            "WHERE mo.as_of=(SELECT MAX(as_of) FROM momentum_scan) "
            "AND m.instrument_class='FUND'").fetchone()[0]
        n_class = c.execute(
            "SELECT COUNT(*) FROM security_master WHERE instrument_class='FUND'").fetchone()[0]
    except sqlite3.OperationalError:
        return _check("fund.leak", SEV_INFO, 0, "instrument_class not populated yet (pre-migration)")
    if funds:
        return _check("fund.leak", SEV_WARN, funds,
                      f"{funds} FUND-class instruments in the latest momentum_scan (universe gate broken?)")
    return _check("fund.leak", SEV_OK, 0, f"ranked outputs fund-free ({n_class} FUND instruments classified)")


def chk_action_tape_agreement(c) -> dict:
    """S85e forward guard: recent SPLIT/BONUS/CONSOLIDATION tape events vs the observed
    ex-day move. TAPE_SUSPECT (disagreement beyond the adjust tolerance) = parse/NSE
    quirk → WARN for review (the gate refuses these, so series stay safe). Dead-zone
    events (3–30% move) are factor-correct for tape-wired consumers (signals) but still
    invisible to the not-yet-wired ones (mep/cpr/stock_rs/wolfe) → surfaced as INFO
    until that adoption wave completes."""
    if not _table_exists(c, "corporate_actions"):
        return _check("action.tape_agreement", SEV_OK, 0, "tape absent")
    try:
        from src.automation.corp_actions import reconcile
        rec = reconcile(c, since=(date.today() - timedelta(days=45)).isoformat())
    except Exception as e:  # noqa: BLE001
        return _check("action.tape_agreement", SEV_INFO, 0, f"reconcile unavailable: {e}")
    sus = rec["counts"].get("TAPE_SUSPECT", 0)
    dz = rec["counts"].get("MISSED_DEAD_ZONE", 0)
    if sus:
        return _check("action.tape_agreement", SEV_WARN, sus,
                      f"{sus} recent tape event(s) disagree with the observed ex-day move "
                      f"(parse/NSE quirk — review; the tolerance gate refused them); "
                      f"{dz} dead-zone event(s)", rec["detail"]["TAPE_SUSPECT"][:5])
    msg = f"{rec['groups']} recent action-groups reconcile clean"
    if dz:
        msg += (f"; {dz} dead-zone event(s) — tape-wired consumers adjust these, "
                f"un-wired (mep/cpr/rs/wolfe) still miss them")
    return _check("action.tape_agreement", SEV_INFO if dz else SEV_OK, dz, msg,
                  rec["detail"]["MISSED_DEAD_ZONE"][:5])


def chk_table_census(c) -> dict:
    """D91 census guard: the machine snapshot must stay fresh, and no data table may
    silently SHRINK >20% day-over-day (the truncation/purge signature — the class the
    588x MAX(rowid) census fiasco and the ratio_rows purge both belonged to)."""
    try:
        from src.automation import table_census as _tc
    except Exception:  # noqa: BLE001
        return _check("census.sanity", SEV_INFO, 0, "table_census module absent")
    days = _tc.latest_dates(c, 1)
    if not days:
        return _check("census.sanity", SEV_INFO, 0, "no census yet (first nightly run takes it)")
    try:
        age = (date.today() - date.fromisoformat(str(days[0])[:10])).days
    except ValueError:
        return _check("census.sanity", SEV_WARN, 1, f"unparseable census_date {days[0]!r}")
    if age > 3:
        return _check("census.sanity", SEV_WARN, 1, f"census stale: last {days[0]} ({age}d ago)")
    shrunk = _tc.shrunk_tables(c)
    if shrunk:
        return _check("census.sanity", SEV_WARN, len(shrunk),
                      "tables shrank >20% day-over-day (truncation/purge signature): "
                      + "; ".join(shrunk[:5]), shrunk[:10])
    n = c.execute("SELECT COUNT(*) FROM table_census WHERE census_date=?", (days[0],)).fetchone()[0]
    return _check("census.sanity", SEV_OK, 0, f"census {days[0]}: {n} tables, no shrink alarms")


def chk_derived_liveness(c) -> dict:
    """The three largest DERIVED tables (stock_signals / mep_signals / cpr_signals) plus the index
    tape recompute EVERY trading day from bhavcopy — if a nightly compute job dies they silently
    FREEZE with no banner anywhere (the exact gap the audit flagged: a nightly-signals death shows
    nothing). Compare each to the bhavcopy clock; stale beyond ~2 trading days = a dead compute job
    = CRIT. Also surface the long-known corporate_actions dead pipe (split-adjust still works via
    adjust.py's prev_close inference, so WARN not CRIT)."""
    if not _table_exists(c, "bhavcopy_rows"):
        return _check("liveness.derived", SEV_OK, 0, "bhavcopy absent")
    bmax = c.execute("SELECT MAX(trade_date) FROM bhavcopy_rows").fetchone()[0]
    if not bmax:
        return _check("liveness.derived", SEV_OK, 0, "bhavcopy empty")
    bref = date.fromisoformat(str(bmax)[:10])
    stale, ok = [], []
    for table, col in (("stock_signals", "trade_date"), ("mep_signals", "trade_date"),
                       ("cpr_signals", "period_end_date"), ("index_signals", "trade_date")):
        if not _table_exists(c, table):
            continue
        mx = c.execute(f"SELECT MAX({col}) FROM {table}").fetchone()[0]
        if not mx:
            stale.append(f"{table} EMPTY")
            continue
        d = (bref - date.fromisoformat(str(mx)[:10])).days
        (stale if d > 4 else ok).append(
            f"{table} {mx}" + (f" ({d}d behind bhav {bmax})" if d > 4 else ""))
    ca = c.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0] \
        if _table_exists(c, "corporate_actions") else 0
    if stale:
        return _check("liveness.derived", SEV_CRIT, len(stale),
                      "DERIVED COMPUTE FROZEN: " + "; ".join(stale)
                      + ("" if ca else "; corporate_actions EMPTY (dead pipe)"))
    if not ca:
        return _check("liveness.derived", SEV_WARN, 1,
                      f"derived tables track bhav {bmax}; corporate_actions EMPTY (dead pipe — "
                      "resurrect a primary feed; split-adjust falls back to adjust.py prev_close)")
    return _check("liveness.derived", SEV_OK, 0, f"derived tables + corp-actions track bhav {bmax}")


def chk_t2t_universe(c) -> dict:
    """X-02 disclosure (S83c): delivery-based measures read series='EQ' only, so names under
    trade-to-trade surveillance (BE/BZ — delivery 100% by settlement rule) are EXCLUDED, not
    polluted. This check publishes the excluded mass so the honesty note stays a live number;
    it never fails — a large T2T cohort is market state, not a defect."""
    if not _table_exists(c, "bhavcopy_rows"):
        return _check("delivery.t2t_excluded", SEV_OK, 0, "bhavcopy absent")
    bmax = c.execute("SELECT MAX(trade_date) FROM bhavcopy_rows").fetchone()[0]
    if not bmax:
        return _check("delivery.t2t_excluded", SEV_OK, 0, "bhavcopy empty")
    today_n = c.execute(
        "SELECT COUNT(*) FROM bhavcopy_rows WHERE trade_date=? AND series IN ('BE','BZ')",
        (bmax,)).fetchone()[0]
    yr = c.execute(
        "SELECT COUNT(*), COUNT(DISTINCT symbol) FROM bhavcopy_rows "
        "WHERE trade_date>=date(?, '-365 day') AND series IN ('BE','BZ')", (bmax,)).fetchone()
    return _check("delivery.t2t_excluded", SEV_OK, today_n,
                  f"T2T/BE excluded from delivery signals BY DESIGN: {today_n} names on {bmax}; "
                  f"{yr[0]} symbol-days / {yr[1]} names last 365d (X-02 honesty number)")


def chk_shareholding_xbrl_freshness(r) -> dict:
    """§7.7(c): true arrival-recency for the shareholding_xbrl feed (SEBI Reg-31 XBRL). Closes the
    residual chk_feed_freshness flagged: the Screener-era rows carry forward-dated report_dates
    (perpetually 'fresh'), but the XBRL rows (source IS NOT NULL) stamp report_date with the real
    broadcastDate, so MAX over ONLY those is a genuine liveness signal. Quarterly SEBI Reg-31
    filings (~45d post-quarter windows) → a loose SHAREHOLDING_XBRL_STALE_DAYS catches a dead
    endpoint without off-season false alarms. research.db absent / no XBRL rows yet → OK
    (Guardrail-#8 migration still pending)."""
    if r is None or not _table_exists(r, "shareholding_history"):
        return _check("shareholding_xbrl.freshness", SEV_OK, 0, "research.db absent")
    mx = r.execute(
        "SELECT MAX(report_date) FROM shareholding_history "
        "WHERE source IS NOT NULL AND report_date IS NOT NULL").fetchone()[0]
    if not mx:
        return _check("shareholding_xbrl.freshness", SEV_OK, 0,
                      "no XBRL-sourced shareholding rows yet (Guardrail-#8 migration pending)")
    age = (date.today() - date.fromisoformat(str(mx)[:10])).days
    if age > SHAREHOLDING_XBRL_STALE_DAYS:
        return _check("shareholding_xbrl.freshness", SEV_WARN, 1,
                      f"newest XBRL shareholding broadcast {mx} ({age}d ago > "
                      f"{SHAREHOLDING_XBRL_STALE_DAYS}d) — the SEBI Reg-31 XBRL feed may be dead")
    return _check("shareholding_xbrl.freshness", SEV_OK, 0,
                  f"newest XBRL shareholding broadcast {mx} ok ({age}d ago)")


def chk_split_cliffs(c) -> dict:
    """16AQ recurrence guard (S184): a corporate-action-shaped price cliff with NO matching
    corporate_actions row is SILENT adjustment corruption. Root cause on record: the NSE equities
    CA feed omits the ETF instrument class — 14 gold-ETF unit subdivisions were missing until
    S182 backfilled them (scripts/backfill_etf_splits.py; proof scripts/verify_etf_splits.py).
    History is healed; this check watches the ROLLING window so the class cannot recur silently —
    for gold ETFs (the portfolio layer consumes them, 16AP/16AR) and for any other symbol.
    Shape: within ~120d of the tape's own max date, a one-day close drop to <= 25% of a >= Rs100
    prior close, traded value on BOTH days (subdivisions keep trading; junk rows don't), and no
    corporate_actions row within +/-5 days of the cliff -> CRITICAL. Fail-safe: tables absent -> OK."""
    try:
        rows = c.execute(
            "SELECT symbol, trade_date, close, value FROM bhavcopy_rows "
            "WHERE series IN ('EQ','BE','BZ') AND close > 0 "
            "AND trade_date >= date((SELECT MAX(trade_date) FROM bhavcopy_rows), '-120 day') "
            "ORDER BY symbol, trade_date").fetchall()
    except sqlite3.Error:
        return _check("split_cliffs", SEV_OK, 0, "bhavcopy_rows absent — nothing to scan")
    orphans, prev = [], {}
    for sym, d, close, val in rows:
        p = prev.get(sym)
        prev[sym] = (d, close, val or 0)
        if not p:
            continue
        _pd, pc, pv = p
        if pc >= 100 and close <= 0.25 * pc and pv > 0 and (val or 0) > 0:
            try:
                covered = c.execute(
                    "SELECT 1 FROM corporate_actions WHERE symbol=? "
                    "AND ex_date BETWEEN date(?, '-5 day') AND date(?, '+5 day') LIMIT 1",
                    (sym, d, d)).fetchone()
            except sqlite3.Error:
                covered = None
            if not covered:
                orphans.append(f"{sym}@{d} ({pc:.0f}->{close:.2f})")
    if orphans:
        return _check("split_cliffs", SEV_CRIT, len(orphans),
                      "corporate-action-shaped cliff(s) with NO corporate_actions row — adjusted "
                      "prices are silently corrupt for every consumer (the 16AQ class): "
                      + "; ".join(orphans[:5])
                      + (" …" if len(orphans) > 5 else "")
                      + " — heal via scripts/backfill_etf_splits.py-style CA insert, then re-verify",
                      sample=orphans[:10])
    return _check("split_cliffs", SEV_OK, 0,
                  f"no orphan split-shaped cliffs in the ~120d window ({len(prev)} symbols scanned)")


def chk_prereg_seals() -> dict:
    """The pre-registration DOCSTRING seals hold (tamper-evidence for study gates, S194e).

    `prereg --verify` recomputes sha256(gate docstring) for every STUDIES module, and
    `seasonal_tape --verify` recomputes the frozen-family param-JSON hash, both vs
    research.db.prereg_registry. They run ONLY under the research venv (they import the
    study modules), so this shells out to it — data_quality itself runs under the prod venv.
    A broken seal = a pre-registered gate was edited AFTER sealing without re-registering:
    it may be a legitimate relabel (then `prereg --register-all --force --note …`) OR a
    silent post-hoc gate edit — either way a human must look, so it is a WARN, not a CRIT
    (no kill-switch coupling). Research venv/db absent (laptop/CI) → OK 'skipped', like the
    table-absent checks. This closes the gap where the exit_lab seal broke unnoticed (S194d).
    """
    root = Path(__file__).resolve().parents[2]           # repo root (== /opt/hermes on the box)
    rpy = root / ".venv-research" / "bin" / "python"
    if not (rpy.exists() and (root / "data" / "research.db").exists()):
        return _check("prereg.seal_integrity", SEV_OK, 0, "research venv/db absent — skipped (box-only)")
    fails = []
    for label, cmd, cwd in (
        ("studies", [str(rpy), "-m", "explosive_moves.prereg", "--verify"], root / "research"),
        ("seasonal", [str(rpy), "-m", "src.automation.seasonal_tape", "--verify"], root),
    ):
        try:
            p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)
            if p.returncode != 0:
                tail = " | ".join((p.stdout + p.stderr).strip().splitlines()[-3:])
                fails.append(f"{label} --verify exit {p.returncode}: {tail}")
        except Exception as e:  # noqa: BLE001 — a probe failure is itself a WARN, never aborts the run
            fails.append(f"{label} probe errored: {type(e).__name__}: {e}")
    if fails:
        return _check("prereg.seal_integrity", SEV_WARN, len(fails),
                      "; ".join(fails) + " — re-register if the gate edit was legitimate, else investigate")
    return _check("prereg.seal_integrity", SEV_OK, 0, "all study + frozen-family gate seals intact")


# ── run all ───────────────────────────────────────────────────────────────────
def run(conn=None, *, persist: bool = True) -> dict:
    """Run the full battery. Returns {status, n_critical, n_warn, checks:[...]}.
    Each check is isolated — a thrown check becomes an 'info' note, never aborts the run."""
    def go(c):
        ensure_schema(c)
        r = _research_ro()
        checks = []
        # the nightly (persist) run takes the D91 machine census FIRST, so the trust
        # surfaces + chk_table_census below always have a fresh COUNT(*)-truth snapshot;
        # ad-hoc persist=False runs skip it (a full census walks every btree once).
        if persist:
            try:
                from src.automation import table_census as _tc
                _tc.run_census(c)
            except Exception as e:  # noqa: BLE001 — census failure must not block the checks
                checks.append(_check("census.run", SEV_INFO, 0, f"census failed: {e}"))
        plan = [
            (chk_credibility_periods, (c,)), (chk_credibility_levels, (c,)),
            (chk_concall_periods, (c,)), (chk_concall_scores, (c,)), (chk_provenance_knowable, (c,)),
            (chk_calibration_freshness, (c,)), (chk_leak_and_demodel, (c,)),
            (chk_fundamentals_dates, (r,)), (chk_security_master, (c,)),
            (chk_cross_db_orphans, (c, r)),
            # kill-switches (validation memo §5)
            (chk_market_freshness, (c,)), (chk_regime_guard, (c,)),
            (chk_universe_drift, (c,)), (chk_feed_freshness, (c,)),
            (chk_derived_liveness, (c,)), (chk_index_name_variants, (c,)),
            (chk_t2t_universe, (c,)), (chk_fund_leak, (c,)),
            (chk_table_census, (c,)), (chk_action_tape_agreement, (c,)),
            (chk_restatement_spike, (r,)),
            (chk_shareholding_xbrl_freshness, (r,)),
            (chk_split_cliffs, (c,)),
            (chk_prereg_seals, ()),
        ]
        for fn, fargs in plan:
            try:
                checks.append(fn(*fargs))
            except Exception as e:  # noqa: BLE001
                checks.append(_check(getattr(fn, "__name__", "check"), SEV_INFO, 0, f"check errored: {e}"))
        if r is not None:
            r.close()
        n_crit = sum(1 for k in checks if k["severity"] == SEV_CRIT)
        n_warn = sum(1 for k in checks if k["severity"] == SEV_WARN)
        status = SEV_CRIT if n_crit else (SEV_WARN if n_warn else SEV_OK)
        report = {"status": status, "n_critical": n_crit, "n_warn": n_warn, "checks": checks}
        if persist:
            c.execute(
                "INSERT INTO data_quality_runs (status, n_critical, n_warn, report_json) VALUES (?,?,?,?)",
                (status, n_crit, n_warn, json.dumps(report, default=str)))
        return report
    return provenance._with_conn(go, conn, write=persist)


def last_run(conn=None) -> Optional[dict]:
    def go(c):
        ensure_schema(c)
        row = c.execute(
            "SELECT run_at, status, n_critical, n_warn, report_json FROM data_quality_runs "
            "ORDER BY run_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        out = {"run_at": row[0], "status": row[1], "n_critical": row[2], "n_warn": row[3]}
        try:
            out["report"] = json.loads(row[4])
        except (TypeError, ValueError):
            out["report"] = None
        return out
    return provenance._with_conn(go, conn)


# ── selftest ────────────────────────────────────────────────────────────────
def _selftest() -> None:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    provenance.ensure_schema(c)
    ensure_schema(c)
    c.executescript("""
        CREATE TABLE credibility_series (symbol TEXT, period_year INT, period_month INT, level REAL);
        CREATE TABLE concall_scores (symbol TEXT, guidance_accuracy_score REAL, n_promises_resolved INT);
        CREATE TABLE security_master (symbol TEXT, first_date TEXT, last_date TEXT, status TEXT,
                                      currently_listed INTEGER DEFAULT 0);
        INSERT INTO credibility_series VALUES ('GOOD',2025,3,82.0),('BADP',225,3,80.0),('BADL',2025,3,150.0);
        INSERT INTO concall_scores VALUES ('GOOD',90.0,12),('BAD',120.0,-1);
        INSERT INTO security_master (symbol, first_date, last_date, status)
            VALUES ('GOOD','2015-01-01','2026-06-01','ACTIVE'),('BAD','2020-01-01','2019-01-01','WEIRD');
    """)
    # a future knowable_at (critical) + a malformed key (warn)
    c.execute("INSERT INTO provenance_knowable (data_class,key,symbol,knowable_at) VALUES "
              "('fundamentals_history',?,?,?)", (provenance.period_key("GOOD", "Q", "2025-03-31"), "GOOD", "2099-01-01"))
    c.execute("INSERT INTO provenance_knowable (data_class,key,symbol,knowable_at) VALUES "
              "('fundamentals_history','MALFORMED|KEY','BADK','2025-05-01')")

    rep = run(conn=c, persist=True)
    by = {k["check"]: k for k in rep["checks"]}
    assert by["credibility_series.period_sanity"]["severity"] == SEV_CRIT and by["credibility_series.period_sanity"]["count"] == 1
    assert by["credibility_series.level_range"]["severity"] == SEV_CRIT and by["credibility_series.level_range"]["count"] == 1
    assert by["concall_scores.sanity"]["severity"] == SEV_CRIT and by["concall_scores.sanity"]["count"] == 1
    assert by["provenance_knowable.sanity"]["severity"] == SEV_CRIT          # future date dominates
    assert by["security_master.sanity"]["severity"] == SEV_WARN and by["security_master.sanity"]["count"] == 2
    # D91 census: the persist run must have taken a same-day census of the synthetic
    # tables and the guard must read it back clean (one day → no shrink comparison yet).
    assert by["census.sanity"]["severity"] == SEV_OK, by["census.sanity"]
    assert c.execute("SELECT COUNT(*) FROM table_census").fetchone()[0] >= 3
    assert rep["status"] == SEV_CRIT and rep["n_critical"] >= 3
    # persisted + readable
    lr = last_run(conn=c)
    assert lr and lr["status"] == SEV_CRIT and lr["report"]["n_critical"] >= 3

    # kill-switch #4 restatement-spike (direct-call on a synthetic research conn):
    # 3/25 gate-passed symbols revised in-window = 12% > 5% → warn; a 5-symbol
    # universe is warmup → info, never warn.
    rr = sqlite3.connect(":memory:")
    rr.executescript("""
        CREATE TABLE fundamentals_xbrl_gate(symbol TEXT PRIMARY KEY, checked_at TEXT, pass INTEGER, detail TEXT);
        CREATE TABLE fundamentals_restatements(symbol TEXT, period_type TEXT, period_end TEXT,
            broadcast TEXT, n_changed INT, listed_revised INT, recorded_at TEXT);
    """)
    rr.executemany("INSERT INTO fundamentals_xbrl_gate VALUES (?,?,1,'ok')",
                   [(f"S{i:02d}", "x") for i in range(25)])
    today = date.today().isoformat()
    rr.executemany("INSERT INTO fundamentals_restatements VALUES (?,?,?,?,1,0,?)",
                   [(f"S{i:02d}", "Q", "2026-03-31", today, today) for i in range(3)])
    k = chk_restatement_spike(rr)
    assert k["severity"] == SEV_WARN and k["count"] == 3, k
    rr.execute("DELETE FROM fundamentals_xbrl_gate WHERE symbol >= 'S05'")   # 5 left = warmup
    k2 = chk_restatement_spike(rr)
    assert k2["severity"] == SEV_INFO and k2["count"] == 3, k2
    rr.close()
    print(f"data_quality selftest: OK  ({rep['n_critical']} critical, {rep['n_warn']} warn detected on synthetic faults)")


def _pp(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _page_on_seal_break(rep: dict) -> None:
    """Autonomous alert: if the prereg/frozen-family seal-integrity check is NOT ok, DM Ramana
    via the AUD-26 pager (scripts/alert-telegram.sh --text). WHY a bespoke path and not the
    systemd OnFailure that every other unit uses: a broken seal is deliberately a WARN, not a
    CRIT (chk_prereg_seals — 'a human must look', no kill-switch coupling), so it never fails the
    service and OnFailure never fires on it. This closes that gap without flipping the severity.
    Kept in the CLI (not run()) so run() stays pure/network-free; never raises (a pager failure
    must not abort the nightly — mirrors alert-telegram.sh's own exit-0 contract)."""
    try:
        seal = next((k for k in rep.get("checks", []) if k.get("check") == "prereg.seal_integrity"), None)
        if seal is None or seal.get("severity") == SEV_OK:
            return
        pager = Path(__file__).resolve().parents[2] / "scripts" / "alert-telegram.sh"
        if not pager.exists():
            return  # laptop / CI — no pager, nothing to do
        msg = (f"\U0001F512 SEAL INTEGRITY {seal.get('severity', '?').upper()}: {seal.get('message', '')}\n"
               f"host: {socket.gethostname()}  time: {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}\n"
               f"A pre-registered study / frozen-family gate changed after sealing. Re-register if the "
               f"edit was legitimate (prereg --register-all --force --note …), else investigate.")
        subprocess.run(["/bin/bash", str(pager), "--text", msg], timeout=15, check=False)
    except Exception:  # noqa: BLE001 — alerting must never crash the monitor
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Continuous data-quality monitor (research/provenance lane).")
    ap.add_argument("--run", action="store_true", help="run all checks, print + persist a snapshot")
    ap.add_argument("--last", action="store_true", help="print the most recent persisted run")
    ap.add_argument("--selftest", action="store_true", help="synthetic in-memory validation")
    ap.add_argument("--quiet", action="store_true", help="persist only; print just the one-line status")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.selftest:
        _selftest(); return
    if args.last:
        _pp(last_run()); return
    if args.run:
        rep = run()
        if args.quiet:
            print(f"data_quality: {rep['status']}  critical={rep['n_critical']} warn={rep['n_warn']}")
        else:
            _pp(rep)
        _page_on_seal_break(rep)   # autonomous seal-break DM (WARN-level, so OnFailure won't page)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
