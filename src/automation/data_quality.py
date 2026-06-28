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
import sqlite3
from datetime import date
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
    # malformed period keys: fundamentals/shareholding keys must be symbol|ptype|period_end (3 parts)
    bad_key = 0
    for key, in c.execute("SELECT key FROM provenance_knowable WHERE data_class IN ('fundamentals_history','shareholding_history')"):
        parts = key.split("|")
        if len(parts) != 3 or parts[1] not in ("A", "Q"):
            bad_key += 1
        else:
            try:
                date.fromisoformat(parts[2][:10])
            except ValueError:
                bad_key += 1
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
    return _check("calibration.freshness", sev, stale,
                  f"{stale}/{len(rows)} calibration rows older than {CALIB_STALE_DAYS}d",
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
    sev = SEV_WARN if (bad_status or bad_dates) else SEV_OK
    return _check("security_master.sanity", sev, bad_status + bad_dates,
                  f"{bad_status} bad status, {bad_dates} last_date<first_date")


def chk_cross_db_orphans(c, r) -> dict:
    """credibility_series symbols absent from security_master (informational coverage gap)."""
    if r is None or not _table_exists(c, "credibility_series") or not _table_exists(c, "security_master"):
        return _check("xdb.credibility_orphans", SEV_OK, 0, "tables absent")
    sm = {x[0] for x in c.execute("SELECT symbol FROM security_master")}
    cs = {x[0] for x in c.execute("SELECT DISTINCT symbol FROM credibility_series")}
    orphans = sorted(cs - sm)
    return _check("xdb.credibility_orphans", SEV_INFO if orphans else SEV_OK, len(orphans),
                  "credibility_series symbols not in security_master", orphans[:10])


# ── run all ───────────────────────────────────────────────────────────────────
def run(conn=None, *, persist: bool = True) -> dict:
    """Run the full battery. Returns {status, n_critical, n_warn, checks:[...]}.
    Each check is isolated — a thrown check becomes an 'info' note, never aborts the run."""
    def go(c):
        ensure_schema(c)
        r = _research_ro()
        checks = []
        plan = [
            (chk_credibility_periods, (c,)), (chk_credibility_levels, (c,)),
            (chk_concall_periods, (c,)), (chk_concall_scores, (c,)), (chk_provenance_knowable, (c,)),
            (chk_calibration_freshness, (c,)), (chk_leak_and_demodel, (c,)),
            (chk_fundamentals_dates, (r,)), (chk_security_master, (c,)),
            (chk_cross_db_orphans, (c, r)),
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
        CREATE TABLE security_master (symbol TEXT, first_date TEXT, last_date TEXT, status TEXT);
        INSERT INTO credibility_series VALUES ('GOOD',2025,3,82.0),('BADP',225,3,80.0),('BADL',2025,3,150.0);
        INSERT INTO concall_scores VALUES ('GOOD',90.0,12),('BAD',120.0,-1);
        INSERT INTO security_master VALUES ('GOOD','2015-01-01','2026-06-01','ACTIVE'),('BAD','2020-01-01','2019-01-01','WEIRD');
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
    assert rep["status"] == SEV_CRIT and rep["n_critical"] >= 3
    # persisted + readable
    lr = last_run(conn=c)
    assert lr and lr["status"] == SEV_CRIT and lr["report"]["n_critical"] >= 3
    print(f"data_quality selftest: OK  ({rep['n_critical']} critical, {rep['n_warn']} warn detected on synthetic faults)")


def _pp(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


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
        return
    ap.print_help()


if __name__ == "__main__":
    main()
