"""Provenance / integrity layer — the honest stamp on every value Patearn returns.

This is the trust spine of the "one bus, four faces" architecture: a single
entitled, metered, **provenance-stamped** ``/v1`` read layer feeds the website
islands, REST, the Excel/Python SDK, and the MCP endpoint. For an institutional
buyer (PMS/AIF/family-office quant + compliance) to trust a Patearn read, every
value must carry an honest answer to "where did this come from, and as of when
was it knowable?". This module is that answer.

The design follows the adversarial red-team's binding corrections (the honesty
layer must NEUTRALISE its limits, not merely describe them):

  * **Basis is a required ENUM, not a strippable ``modeled`` boolean.** Each value's
    timestamp basis is one of AS_TRADED / INGESTED / MODELED / DERIVED / EVENT. A
    modelled date additionally carries ``lag_days`` and embeds the word "modeled"
    *inside* its human display string, so a downstream SDK/MCP/LLM consumer cannot
    silently drop the caveat. (``modeled`` is offered only as a convenience derived
    from ``basis``; ``basis`` is canonical.)

  * **``observe()`` (real first-seen capture) is FORWARD-ONLY and says so.** The
    historical fundamentals archive was scraped in 2026, long after the periods it
    covers, so a scrape-time "first seen" is an upper bound from a late scrape — it
    would grey out real history and mislead. We therefore do NOT back-seed
    ``knowable_at`` from scrape logs; historical rows stay honestly MODELED, and a
    real first-seen date only accrues going forward. ``lag_audit()`` measures the
    modelled-lag error once real dates exist.

  * **Survivorship is surfaced with its FLOOR.** ``universe_policy()`` reuses the
    existing ``security_master`` spine (which keeps delisted names) and headlines the
    bhav-archive floor date + a left-censoring proxy + the asymmetric-survivorship +
    SME-exclusion disclosures, so the policy is stated, not implied.

  * **An append-only restatement log** records when a stored value changes between
    two as-of reads (e.g. a CCI ``--force`` re-extract), so a "PIT replay" is auditable.

Isolation (the ``security_master.py`` / ``news_tagging.py`` house pattern): a
brand-new module that OWNS its own tables via an embedded ``_SCHEMA`` + idempotent
``ensure_schema(conn)``. It never edits ``db.py`` or any ingestion file, so it
cannot collide with the parallel sessions that own the web/ingestion tree. The
static ``PROVENANCE`` registry is the single source of provenance truth, kept in
code (like ``security_master.EQUITY_SERIES``) so it is reviewable in PRs and cannot
drift silently.

Defensive by construction: the local ``data/hermes.db`` is a 4-symbol dev stub and
``research.db`` is a VPS path absent on a laptop — every read degrades to a graceful
"absent/empty" stamp, never a crash. Pure stdlib + the project's ``get_conn``; no LLM.

CLI:
    python -m src.automation.provenance --selftest        # synthetic, no real data
    python -m src.automation.provenance --coverage        # print the coverage snapshot
    python -m src.automation.provenance --universe        # print the survivorship policy
    python -m src.automation.provenance --lag-audit       # modelled-lag error distribution
    python -m src.automation.provenance --stamp bhav_eq --symbol RELIANCE --as-of 2026-06-25
"""
from __future__ import annotations

import argparse
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.provenance")

# research.db is a separate file (holds fundamentals_history / shareholding_history).
# Hard-coded VPS path with an env override; always opened READ-ONLY + degrade-if-absent.
RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

# ── timestamp-basis enum (the canonical honesty field) ────────────────────────
AS_TRADED = "AS_TRADED"     # a real exchange trading date (NSE bhav / index close / F&O)
INGESTED = "INGESTED"       # a real first-seen/fetch timestamp (scrape, RSS, LLM enrich)
MODELED = "MODELED"         # a SYNTHETIC uniform lag (fundamentals report_date = period_end+lag)
DERIVED = "DERIVED"         # computed from other in-DB classes; inherits their (usually real) date
EVENT = "EVENT"             # a real event date (corp action ex-date, concall held/transcript date)
_REAL_BASES = {AS_TRADED, INGESTED, EVENT}

# What the PRODUCER actually stamped into the stored report_date (the BASELINE the audit measures,
# = fundamentals_history._period_to_dates: annual +90d / quarterly +50d; shareholding +30d). This
# mirrors reality on disk — do NOT "tighten" it here; the stored dates are parallel-owned.
_PRODUCER_LAG_DAYS = {
    "fundamentals_history": {"A": 90, "Q": 50, "_default": 90},
    "shareholding_history": {"_default": 30},
}

# CONSERVATIVE fallback synthetic lags for the modeled-availability case (no real date yet, no
# calibration row yet). Deliberately LATER than the producer so the fallback errs late (safe) not
# early (leak). calibrate_synthetic_lag() overwrites these per-ptype with the empirical p95 of the
# real filing lag once BSE dates exist (provenance_lag_calibration). Reader = _calibrated_lag().
_MODELED_LAG_DAYS = {
    "fundamentals_history": {"A": 120, "Q": 65, "_default": 120},
    "shareholding_history": {"_default": 45},
}


# ── the provenance descriptor + the static registry (single source of truth) ──
@dataclass(frozen=True)
class ProvenanceDescriptor:
    key: str                       # registry key, e.g. 'fundamentals_history'
    label: str                     # human label
    source: str                    # honest origin, e.g. 'Screener.in scrape'
    db: str                        # 'hermes' | 'research'
    tables: tuple                  # the table(s) this class lives in
    grain: str                     # 'daily' | 'quarterly' | 'market-level' | 'event' | 'derived' | 'snapshot'
    basis: str                     # one of the basis enum above
    has_symbol: bool = True        # False for market-level classes (participant_oi, fii_dii_flows) — the grain guard
    asof_col: str = ""             # the column carrying the as-of/observation date
    asof_real_cols: tuple = ()     # for EVENT classes: real clock columns in priority order
    ingest_col: Optional[str] = None  # 'computed_at'/'fetched_at' — when the row was written (NOT the as-of)
    template: str = ""             # honest display string w/ {placeholders}; ALWAYS embeds the basis word
    derives_from: tuple = ()       # upstream classes a DERIVED class inherits its date from
    cadence: str = ""              # expected refresh cadence (the freshness story)
    method_versioned: bool = False # True once rows carry method/prompt/model version (red-team 5.3)


def _d(*a, **k) -> ProvenanceDescriptor:
    return ProvenanceDescriptor(*a, **k)


# The canonical data-class map. Each entry = one honest descriptor. Templates embed
# the basis word ("As-traded", "Modeled availability", "Computed from", …) by design.
PROVENANCE: dict[str, ProvenanceDescriptor] = {
    # ── Tier 1: raw exchange ingest (real dates) ──
    "bhav_eq": _d("bhav_eq", "As-traded equity OHLC", "NSE bhav copy", "hermes",
                  ("bhavcopy_rows",), "daily", AS_TRADED, asof_col="trade_date",
                  template="As-traded {field}, NSE bhav {as_of}", cadence="daily ~19:00 IST"),
    "bhav_delivery": _d("bhav_delivery", "Exchange delivery qty/%", "NSE sec_bhavdata_full", "hermes",
                        ("bhavcopy_rows",), "daily", AS_TRADED, asof_col="trade_date",
                        template="Exchange delivery, NSE bhav {as_of} (NULL for legacy/UDiFF dates)",
                        cadence="daily ~19:00 IST"),
    "index_ohlc": _d("index_ohlc", "Index OHLC + PE/PB/divyield", "NSE ind_close_all", "hermes",
                     ("index_rows",), "daily", AS_TRADED, has_symbol=False, asof_col="trade_date",
                     template="NSE index close, {as_of}", cadence="daily ~19:00 IST"),
    "corp_action": _d("corp_action", "Split/bonus/dividend/rights", "NSE corp-action feed", "hermes",
                      ("corporate_actions",), "event", EVENT, asof_col="ex_date", asof_real_cols=("ex_date",),
                      template="Corporate action (ex {as_of}), NSE feed", cadence="as announced"),
    "fno_oi": _d("fno_oi", "Stock-futures OI / PCR / basis / max-pain", "NSE F&O bhav (UDiFF)", "hermes",
                 ("fno_oi_signals",), "daily", AS_TRADED, asof_col="trade_date",
                 template="F&O OI positioning, NSE F&O bhav {as_of}", cadence="daily ~19:00 IST"),
    "participant_oi": _d("participant_oi", "FII/DII/Pro/Client long-short", "NSE participant-wise OI", "hermes",
                         ("participant_oi",), "market-level", AS_TRADED, has_symbol=False, asof_col="trade_date",
                         template="MARKET-LEVEL participant OI, {as_of} — NOT per-stock", cadence="daily ~19:00 IST"),
    "fii_dii_flows": _d("fii_dii_flows", "Market net FII/DII flows", "NSE fiidii", "hermes",
                        ("fii_dii_flows",), "market-level", INGESTED, has_symbol=False, asof_col="trade_date",
                        template="MARKET-LEVEL FII/DII net flow, {as_of} — NOT per-stock", cadence="daily"),
    "bulk_block_deals": _d("bulk_block_deals", "Named bulk/block deals", "NSE bulk/block feed", "hermes",
                           ("bulk_block_deals",), "event", INGESTED, asof_col="trade_date",
                           template="Bulk/block deal, NSE {as_of}", cadence="daily (going-forward)"),
    "index_membership": _d("index_membership", "Index constituents + weight", "niftyindices", "hermes",
                           ("stock_index_membership",), "snapshot", INGESTED, asof_col="snapshot_date",
                           template="Index constituent snapshot {as_of}", cadence="on reconstitution"),
    "equity_universe": _d("equity_universe", "NSE EQUITY_L allowlist", "NSE EQUITY_L.csv", "hermes",
                          ("nse_equity_list",), "snapshot", INGESTED, asof_col="snapshot_date",
                          template="NSE EQUITY_L snapshot {as_of} (CURRENT names only)", cadence="periodic"),
    "news_headline": _d("news_headline", "Market news headline", "RSS (MC/Mint/ET/BS)", "hermes",
                        ("sent_news",), "event", INGESTED, asof_col="sent_at",
                        template="{source} headline, first seen {as_of}", cadence="continuous"),

    # ── Tier 2: computed-from-bhav/index (DERIVED, inherit a real as-traded date) ──
    "dvpt_signals": _d("dvpt_signals", "DVPT baselines / R-P / character / key-price", "computed", "hermes",
                       ("stock_signals",), "derived", DERIVED, asof_col="trade_date", ingest_col="computed_at",
                       derives_from=("bhav_eq", "bhav_delivery"),
                       template="Computed from as-traded delivery, NSE bhav {as_of}", cadence="nightly"),
    "mep_signals": _d("mep_signals", "Signed accumulation/distribution tape", "computed", "hermes",
                      ("mep_signals",), "derived", DERIVED, asof_col="trade_date", ingest_col="computed_at",
                      derives_from=("bhav_eq",),
                      template="Computed from as-traded OHLC/VWAP, {as_of}", cadence="nightly"),
    "cpr_signals": _d("cpr_signals", "CPR structure (D/W/M)", "computed", "hermes",
                      ("cpr_signals",), "derived", DERIVED, asof_col="period_end_date", ingest_col="computed_at",
                      derives_from=("bhav_eq",), template="CPR from as-traded bars to {as_of}", cadence="nightly"),
    "stock_rs": _d("stock_rs", "Stock RS vs broad & sector + rank", "computed", "hermes",
                   ("stock_signals",), "derived", DERIVED, asof_col="trade_date", ingest_col="computed_at",
                   derives_from=("bhav_eq", "index_ohlc"), template="RS vs benchmark, as-traded {as_of}", cadence="nightly"),
    "index_signals": _d("index_signals", "Index returns/MA/52w + RS phase", "computed", "hermes",
                        ("index_signals",), "derived", DERIVED, has_symbol=False, asof_col="trade_date",
                        ingest_col="computed_at", derives_from=("index_ohlc",),
                        template="Index signal, NSE close {as_of}", cadence="nightly"),
    "rs_extras": _d("rs_extras", "JdK RS-Ratio/Momentum, RSI-of-RS, Mansfield", "computed", "hermes",
                    ("rs_extras",), "derived", DERIVED, asof_col="trade_date", ingest_col="computed_at",
                    derives_from=("index_ohlc",), template="RRG read, {as_of}", cadence="nightly"),
    "rsband": _d("rsband", "RS band % / regime / break state", "computed", "hermes",
                 ("rsband_signals",), "derived", DERIVED, asof_col="trade_date", ingest_col="computed_at",
                 derives_from=("index_ohlc",), template="RS band, {as_of}", cadence="nightly"),
    "capture": _d("capture", "Down/up capture, down-excess", "computed", "hermes",
                  ("capture_signals",), "derived", DERIVED, asof_col="trade_date", ingest_col="computed_at",
                  derives_from=("index_ohlc",), template="Capture read, {as_of}", cadence="nightly"),
    "signal_events": _d("signal_events", "Typed state-change events", "computed", "hermes",
                        ("signal_events",), "event", DERIVED, asof_col="as_of", ingest_col="detected_at",
                        template="Typed signal event on {as_of}", cadence="nightly"),

    # ── Tier 3: fundamentals & qualitative (the honest-relabel zone) ──
    "fundamentals_live": _d("fundamentals_live", "Current Screener snapshot ratios", "Screener.in scrape", "hermes",
                            ("fundamentals",), "snapshot", INGESTED, asof_col="fetched_at",
                            template="Screener snapshot, fetched {as_of}", cadence="periodic"),
    "fundamentals_history": _d("fundamentals_history", "Historical financial time-series", "Screener.in scrape", "research",
                               ("fundamentals_history",), "quarterly", MODELED, asof_col="report_date",
                               asof_real_cols=("knowable_at",),
                               template="Modeled availability (period_end +{lag}d); real first-seen not captured",
                               cadence="quarterly (modelled)"),
    "shareholding_history": _d("shareholding_history", "Quarterly shareholding", "Screener.in scrape", "research",
                               ("shareholding_history",), "quarterly", MODELED, asof_col="report_date",
                               asof_real_cols=("knowable_at",),
                               template="Modeled availability (period_end +{lag}d)", cadence="quarterly (modelled)"),
    "company_about": _d("company_about", "Business description corpus", "Screener.in", "hermes",
                        ("company_about",), "snapshot", INGESTED, asof_col="fetched_at",
                        template="Screener about, fetched {as_of}", cadence="periodic"),
    "company_profile": _d("company_profile", "AI business dossier", "Gemini flash-lite (grounded)", "hermes",
                          ("company_profile",), "snapshot", INGESTED, asof_col="enriched_at",
                          template="AI-enriched profile, {as_of}", cadence="periodic", method_versioned=True),
    "theme_tags": _d("theme_tags", "Multi-label theme tags", "index-seed / AI / human", "hermes",
                     ("company_tags",), "snapshot", INGESTED, asof_col="as_of",
                     template="Theme tag — see source/approval", cadence="weekly reseed"),
    "news_symbol_tags": _d("news_symbol_tags", "Per-symbol news tags", "rule gazetteer / classifier", "hermes",
                           ("news_symbol_tags",), "event", INGESTED, asof_col="tagged_at",
                           template="News→symbol tag — see method", cadence="continuous", method_versioned=True),
    "pattern_scores": _d("pattern_scores", "14-pattern patearn score", "computed", "hermes",
                         ("pattern_scores",), "derived", DERIVED, asof_col="scored_at", ingest_col="scored_at",
                         derives_from=("fundamentals_live",), template="Patearn score, {as_of}", cadence="on run"),

    # ── Tier 4: concall intelligence (real event clocks exist — prefer them) ──
    "concall_corpus": _d("concall_corpus", "Transcript metadata + path", "Screener → BSE PDF", "hermes",
                         ("concalls",), "event", EVENT, asof_col="period_label",
                         asof_real_cols=("concall_dt", "transcript_publish_dt", "result_filing_dt"),
                         template="Concall {as_of}", cadence="per results"),
    "concall_results": _d("concall_results", "Reported quarterly numbers", "Screener quarterly table", "hermes",
                          ("concall_results",), "event", EVENT, asof_col="period_label",
                          template="Reported {as_of} (₹cr)", cadence="per results"),
    "concall_extraction": _d("concall_extraction", "LLM guidance/behavior/redflags", "Gemini Flash on transcript", "hermes",
                             ("concall_guidance", "concall_behavior", "concall_redflags"), "event", INGESTED,
                             asof_col="source_period", template="Extracted from {as_of} transcript",
                             cadence="per transcript", method_versioned=True),
    "concall_settlement": _d("concall_settlement", "Promise MET/MISSED/PARTIAL", "deterministic vs results", "hermes",
                             ("concall_guidance",), "event", EVENT, asof_col="resolved_period",
                             template="Settled vs reported {as_of} — no look-ahead", cadence="per results"),
    "cci_credibility": _d("cci_credibility", "Credibility score + rank (snapshot)", "computed PIT", "hermes",
                          ("concall_scores",), "derived", DERIVED, asof_col="as_of_period",
                          derives_from=("concall_settlement",), template="Credibility as of {as_of}",
                          cadence="per settle", method_versioned=True),
    "cci_series": _d("cci_series", "PIT credibility level + momentum + tape", "computed PIT", "hermes",
                     ("credibility_series",), "derived", DERIVED, asof_col="period_label", ingest_col="computed_at",
                     derives_from=("concall_settlement",), template="PIT credibility at {as_of}, no look-ahead",
                     cadence="per settle", method_versioned=True),
    "survivorship": _d("survivorship", "Universe construction policy", "raw bhav archive", "hermes",
                       ("security_master", "security_events", "security_renames"), "derived", DERIVED,
                       template="Survivorship-correct universe, delisted retained", cadence="nightly"),
}


# ── owned tables ──────────────────────────────────────────────────────────────
_SCHEMA = """
-- (1) Real first-seen capture. ONE row the first time a (data_class, key) is observed.
--     INSERT OR IGNORE preserves the EARLIEST timestamp (the whole point of first-seen).
CREATE TABLE IF NOT EXISTS provenance_knowable (
    data_class   TEXT NOT NULL,
    key          TEXT NOT NULL,
    symbol       TEXT,
    knowable_at  TEXT NOT NULL DEFAULT (datetime('now')),
    source_note  TEXT,
    PRIMARY KEY (data_class, key)
);
CREATE INDEX IF NOT EXISTS idx_prov_knowable_sym  ON provenance_knowable(data_class, symbol);
CREATE INDEX IF NOT EXISTS idx_prov_knowable_when ON provenance_knowable(data_class, knowable_at);

-- (2) Append-only lag-audit ledger: measured (real knowable_at − modelled report_date).
CREATE TABLE IF NOT EXISTS provenance_lag_audit (
    data_class     TEXT NOT NULL,
    key            TEXT NOT NULL,
    symbol         TEXT,
    modeled_date   TEXT,
    knowable_at    TEXT,
    lag_error_days INTEGER,
    measured_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (data_class, key, measured_at)
);
CREATE INDEX IF NOT EXISTS idx_prov_lag_class ON provenance_lag_audit(data_class);

-- (3) Append-only restatement/corrections log: a stored value changed between as-of reads.
CREATE TABLE IF NOT EXISTS provenance_restatement (
    data_class   TEXT NOT NULL,
    key          TEXT NOT NULL,
    symbol       TEXT,
    field        TEXT,
    old_value    TEXT,
    new_value    TEXT,
    reason       TEXT,
    observed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_prov_restate ON provenance_restatement(data_class, key, observed_at);

-- (4) Calibrated conservative synthetic lag per (data_class, period_type), LEARNED from the real
--     BSE filing dates so the modeled fallback (where no real date exists yet) errs LATE (safe),
--     not early (leak). chosen_lag = a high percentile of observed (real − period_end). One
--     current row per (class, ptype); recomputed idempotently by calibrate_synthetic_lag().
CREATE TABLE IF NOT EXISTS provenance_lag_calibration (
    data_class    TEXT NOT NULL,
    period_type   TEXT NOT NULL,
    n             INTEGER,
    p50           INTEGER,
    p90           INTEGER,
    p95           INTEGER,
    p99           INTEGER,
    chosen_lag    INTEGER,
    percentile    INTEGER,
    calibrated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (data_class, period_type)
);
"""


# ── connection plumbing (own-or-borrow, the security_master pattern) ──────────
def _with_conn(fn, conn, *, write: bool = False):
    """Own-or-borrow a connection (the security_master pattern). When we OWN it and
    `write` is set, commit before closing so single-call writes persist (get_conn does
    not auto-commit). Borrowed connections are never committed here — the caller owns
    the transaction (so a producer can batch observe() inside its own commit)."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        r = fn(conn)
        if own and write:
            conn.commit()
        return r
    finally:
        if own:
            cm.__exit__(None, None, None)


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


def _key(*parts) -> str:
    """The ONE key builder for provenance_knowable — used by BOTH the observe() writer
    and the provenance_for() reader, so the namespacing can never drift (the edge case
    the data-engineer flagged). `data_class` is a separate column (part of the PK), so it
    is NOT repeated here: key = the natural identity WITHIN the class."""
    return "|".join(str(v) for v in parts if v is not None and str(v) != "")


def period_key(symbol: str, period_type: Optional[str], period_end: str) -> str:
    """Canonical knowable-key for a PERIOD-typed class (fundamentals/shareholding):
    ``symbol|period_type|period_end``. period_type is REQUIRED for uniqueness — annual
    'Mar 2023' and quarterly Q4 'Mar 2023' share period_end 2023-03-31 but file on
    different dates. Both the forward ingest hook (writer) and provenance_for (reader)
    build the key through here so they can never diverge."""
    return _key(symbol, period_type, period_end)


def _research_ro():
    """Open research.db READ-ONLY, or None if absent (laptop / fresh box)."""
    if not os.path.exists(RESEARCH_DB):
        return None
    try:
        return sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=20)
    except sqlite3.Error:
        return None


def _scalar(conn, sql: str, params=()):
    """A single defensive scalar read — None on any sqlite error (missing table etc.)."""
    try:
        r = conn.execute(sql, params).fetchone()
        if r is None:
            return None
        return r[0]
    except sqlite3.Error:
        return None


def _rows(conn, sql: str, params=()):
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []


# ── observe: idempotent real first-seen capture (FORWARD-ONLY) ────────────────
def observe(data_class: str, key: str, conn=None, *, symbol: Optional[str] = None,
            knowable_at: Optional[str] = None, source_note: Optional[str] = None) -> bool:
    """Record the REAL first-seen of a (data_class, key) — once. Returns True on first
    sighting, False if already known (the earliest timestamp is preserved).

    FORWARD-ONLY by design: call this from the scheduler/post-ingest path as new data
    lands, so ``knowable_at`` is a genuine ingestion clock. We deliberately do NOT
    back-seed historical rows from scrape logs (a 2026 scrape of a 2018 period is an
    upper bound that would mislead) — those stay honestly MODELED until a real
    filing-date backfill provides ``knowable_at``."""
    if data_class not in PROVENANCE:
        raise ValueError(f"unknown data_class {data_class!r}")

    def q(c):
        before = c.total_changes
        c.execute(
            "INSERT OR IGNORE INTO provenance_knowable (data_class, key, symbol, knowable_at, source_note) "
            "VALUES (?,?,?,COALESCE(?, datetime('now')),?)",
            (data_class, key, symbol, knowable_at, source_note))
        return (c.total_changes - before) > 0
    return _with_conn(q, conn, write=True)


def observe_batch(data_class: str, keys, conn=None, *, knowable_at: Optional[str] = None,
                  source_note: Optional[str] = None) -> int:
    """Observe many keys (each 'key' or (key, symbol)); returns #newly-captured.
    Intended to be called inside a producer's existing transaction (pass its conn)."""
    if data_class not in PROVENANCE:
        raise ValueError(f"unknown data_class {data_class!r}")

    def q(c):
        before = c.total_changes
        payload = []
        for k in keys:
            if isinstance(k, (tuple, list)):
                payload.append((data_class, k[0], k[1] if len(k) > 1 else None, knowable_at, source_note))
            else:
                payload.append((data_class, k, None, knowable_at, source_note))
        c.executemany(
            "INSERT OR IGNORE INTO provenance_knowable (data_class, key, symbol, knowable_at, source_note) "
            "VALUES (?,?,?,COALESCE(?, datetime('now')),?)", payload)
        return c.total_changes - before
    return _with_conn(q, conn, write=True)


# ── provenance_for: the honest stamp ──────────────────────────────────────────
def provenance_for(data_class: str, *, symbol: Optional[str] = None, as_of: Optional[str] = None,
                   period_type: Optional[str] = None, conn=None, field_name: Optional[str] = None) -> dict:
    """The honest provenance stamp for a value of ``data_class``.

    Returns a dict whose canonical field is ``basis`` (the enum). ``modeled`` is a
    convenience derived from it. For a MODELED class the real ``knowable_at`` (if it
    has accrued via observe()) is preferred and flips the stamp to real; otherwise it
    falls back to the modelled date and the display string says "Modeled availability".
    Never raises — an unknown class or absent table degrades to an honest 'unknown'."""
    d = PROVENANCE.get(data_class)
    if d is None:
        return {"data_class": data_class, "basis": "UNKNOWN", "modeled": False,
                "as_of": as_of, "as_of_kind": "unknown", "display": f"Unknown data class {data_class}",
                "warnings": [f"no provenance descriptor for {data_class!r}"]}

    warnings: list[str] = []
    # grain guard — a market-level class queried per-symbol must NOT pretend it has one
    if symbol is not None and not d.has_symbol:
        warnings.append(f"{data_class} is {d.grain}; symbol ignored (no per-stock split)")
        symbol = None

    basis = d.basis
    as_of_kind = "real" if basis in _REAL_BASES else basis.lower()
    chosen = as_of
    lag = None

    def _run(c):
        nonlocal basis, as_of_kind, chosen, lag
        # MODELED: prefer a real knowable_at if it has accrued; else fall back to modelled date.
        if d.basis == MODELED:
            real = None
            if c is not None and symbol is not None and as_of is not None:
                # canonical period key (period_type included for uniqueness); falls back to
                # symbol|as_of if the caller did not pass period_type (best-effort).
                k = period_key(symbol, period_type, as_of) if period_type else _key(symbol, as_of)
                real = _scalar(c, "SELECT knowable_at FROM provenance_knowable WHERE data_class=? AND key=?",
                               (data_class, k))
            if real:
                basis, as_of_kind, chosen = INGESTED, "real", real
            else:
                basis, as_of_kind = MODELED, "modeled"
                # the CONSERVATIVE calibrated lag (per ptype), not the producer's leaky +50/+90
                lag = _calibrated_lag(data_class, period_type, conn=c)
                if chosen is None and c is not None and symbol is not None:
                    chosen = _scalar(c, f"SELECT MAX({d.asof_col}) FROM {d.tables[0]} WHERE symbol=?", (symbol,))
        # EVENT: prefer a real clock column; fall back to the period label
        elif d.basis == EVENT and d.asof_real_cols and c is not None and symbol is not None:
            for col in d.asof_real_cols:
                v = _scalar(c, f"SELECT {col} FROM {d.tables[0]} WHERE symbol=? AND {col} IS NOT NULL "
                               f"ORDER BY {col} DESC LIMIT 1", (symbol,))
                if v:
                    chosen, as_of_kind = v, "event"
                    break
        # latest as-of fallback for real classes when none supplied
        if chosen is None and c is not None and d.asof_col:
            if d.has_symbol and symbol is not None:
                chosen = _scalar(c, f"SELECT MAX({d.asof_col}) FROM {d.tables[0]} WHERE symbol=?", (symbol,))
            else:
                chosen = _scalar(c, f"SELECT MAX({d.asof_col}) FROM {d.tables[0]}")

    if conn is not None:
        _run(conn)
    elif d.basis in (MODELED, EVENT) or as_of is None:
        # only borrow a connection if we actually need a DB lookup
        try:
            _with_conn(lambda c: (_run(c), None)[1], None)
        except Exception as e:  # noqa: BLE001 — provenance must never crash a caller
            warnings.append(f"db lookup skipped: {e}")

    # build the display — ALWAYS embed the basis word so it can't be silently stripped
    try:
        display = d.template.format(field=field_name or d.label, as_of=chosen or "n/a", lag=lag or "?")
    except Exception:  # noqa: BLE001
        display = f"{d.label} ({basis})"
    if basis == MODELED and "modeled" not in display.lower():
        display = f"Modeled availability — {display}"

    # effective (no-leak) PIT date: the real BSE date if it accrued, else period_end + the
    # CONSERVATIVE calibrated lag. A leak-sensitive consumer (a backtest's as-of gate) should use
    # this, NOT the bare period_end — it errs late (safe), never early (look-ahead).
    effective_as_of = chosen
    if basis == MODELED and lag is not None and as_of:
        try:
            effective_as_of = (date.fromisoformat(str(as_of)[:10]) + timedelta(days=int(lag))).isoformat()
        except (ValueError, TypeError):
            effective_as_of = chosen

    return {
        "data_class": data_class, "label": d.label, "source": d.source, "db": d.db,
        "grain": d.grain, "has_symbol": d.has_symbol,
        "basis": basis,                       # CANONICAL honesty field (enum)
        "modeled": basis == MODELED,          # convenience derived from basis
        "redistribution": redistribution_status(data_class),   # data-licensing posture (/v1 scope gate)
        "as_of": chosen, "as_of_kind": as_of_kind,
        "effective_as_of": effective_as_of,    # the no-leak PIT date (real, or period_end+calibrated lag)
        "lag_days": lag,                       # the conservative calibrated lag when modeled
        "method_versioned": d.method_versioned,
        "display": display,                    # the string ui_kit.badge() renders
        "warnings": warnings,
    }


def stamp(value: dict, data_class: str, **kw) -> dict:
    """Attach a provenance stamp to an outbound /v1 value under the `_provenance` key.
    The underscore marks it as metadata that survives JSON → REST/Excel/MCP uniformly."""
    return {**value, "_provenance": provenance_for(data_class, **kw)}


def stamp_many(rows: list, data_class: str, **kw) -> dict:
    """Stamp a homogeneous set of rows once at the response grain (not per cell)."""
    return {"rows": rows, "_provenance": provenance_for(data_class, **kw)}


# ── data-licensing / redistribution posture per class (docs/data-licensing-decision.md) ──
# PUBLIC_RECORD = exchange disclosure / official file (resale still needs the exchange's
#   redistribution licence, but it is OUR compiled use of a public record); VENDOR_TOS = scraped
#   from a vendor whose ToS restricts redistribution (the migration target — fundamentals/concall
#   index/shareholding); OWNED = computed by us / our LLM-rule extraction (our IP); NEWS_LICENSE =
#   per-source news terms. The /v1 external scope can refuse to serve a non-redistributable class.
PUBLIC_RECORD, VENDOR_TOS, OWNED, NEWS_LICENSE = "public-record", "vendor-tos", "owned", "news-license"


def redistribution_status(data_class: str) -> str:
    """The data-licensing posture for a class (for /v1 external-scope gating + the coverage panel).
    Derived from the descriptor's source/basis; conservative default VENDOR_TOS so nothing is ever
    accidentally treated as redistributable. See docs/data-licensing-decision.md §3."""
    d = PROVENANCE.get(data_class)
    if d is None:
        return VENDOR_TOS
    src = (d.source or "").lower()
    if d.basis == DERIVED or "computed" in src or "deterministic" in src or "raw bhav" in src:
        return OWNED
    if "gemini" in src or "classifier" in src or "gazetteer" in src or "human" in src:
        return OWNED                 # our LLM / rule extraction is our IP (inputs may be public/licensed)
    if "screener" in src:
        return VENDOR_TOS            # the migration target
    if "rss" in src or "news" in src:
        return NEWS_LICENSE
    if any(k in src for k in ("nse", "bse", "bhav", "nifty", "exchange", "udiff",
                              "equity_l", "fiidii", "corp-action", "participant")):
        return PUBLIC_RECORD
    return VENDOR_TOS


def licensing_digest() -> dict:
    """Per-class redistribution posture + the counts (the migration ledger for the pre-pitch swap)."""
    rows = [{"key": k, "source": PROVENANCE[k].source, "redistribution": redistribution_status(k)}
            for k in PROVENANCE]
    counts: dict = {}
    for r in rows:
        counts[r["redistribution"]] = counts.get(r["redistribution"], 0) + 1
    return {"counts": counts, "classes": rows,
            "migration_target": [r["key"] for r in rows if r["redistribution"] == VENDOR_TOS]}


def provenance_registry_digest() -> list[dict]:
    """The whole static registry as plain dicts — served once by the four faces so a
    client resolves a data_class key → its full descriptor without it riding every cell."""
    return [{"key": d.key, "label": d.label, "source": d.source, "db": d.db,
             "grain": d.grain, "basis": d.basis, "has_symbol": d.has_symbol,
             "cadence": d.cadence, "method_versioned": d.method_versioned,
             "redistribution": redistribution_status(d.key),
             "modeled": d.basis == MODELED} for d in PROVENANCE.values()]


# ── record_restatement: append-only corrections log ──────────────────────────
def record_restatement(data_class: str, key: str, field_name: str, old_value, new_value,
                       conn=None, *, symbol: Optional[str] = None, reason: Optional[str] = None) -> None:
    """Append a record that a stored value changed between as-of reads (e.g. a CCI
    --force re-extract). Makes a 'PIT replay' auditable instead of a silent mutation."""
    def q(c):
        c.execute(
            "INSERT INTO provenance_restatement (data_class, key, symbol, field, old_value, new_value, reason) "
            "VALUES (?,?,?,?,?,?,?)",
            (data_class, key, symbol, field_name,
             None if old_value is None else str(old_value),
             None if new_value is None else str(new_value), reason))
    _with_conn(q, conn, write=True)


# ── synthetic-lag calibration: learn a conservative lag from real filing dates ─
def _pct(sorted_vals: list, p: float):
    """Nearest-rank percentile of a PRE-SORTED list (p in [0,100]); None if empty."""
    if not sorted_vals:
        return None
    i = min(len(sorted_vals) - 1, max(0, int(round(p / 100.0 * len(sorted_vals))) - 1))
    return sorted_vals[i]


def _calibrated_lag(data_class: str, period_type: Optional[str], conn=None) -> int:
    """The CONSERVATIVE synthetic lag (days) for a (class, ptype): the learned calibration row if
    present, else the conservative ``_MODELED_LAG_DAYS`` fallback — never the producer's leaky
    +50/+90 (that is ``_PRODUCER_LAG_DAYS``, used only as the audit baseline)."""
    pt = period_type or "_default"

    def lookup(c):
        return _scalar(c, "SELECT chosen_lag FROM provenance_lag_calibration "
                          "WHERE data_class=? AND period_type=?", (data_class, pt)) if c is not None else None
    learned = None
    try:
        learned = lookup(conn) if conn is not None else _with_conn(lookup, None)
    except sqlite3.Error:
        learned = None
    if learned is not None:
        return int(learned)
    t = _MODELED_LAG_DAYS.get(data_class, {})
    return int(t.get(pt, t.get("_default", 90)))


def calibrate_synthetic_lag(conn=None, *, percentile: int = 95, clip=(1, 400)) -> dict:
    """Learn a conservative synthetic lag from the REAL filing dates in provenance_knowable: for
    each (class, period_type), lag = real_knowable − period_end, clipped to ``clip`` (drops the
    negative/ultra-fast mismatches and the restatement tail), and ``chosen_lag`` = the
    ``percentile`` of that distribution (p95 ⇒ the modeled fallback under-shoots the real date
    only ~5% of the time → look-ahead nearly eliminated for the not-yet-de-modeled rows). Persists
    one current row per (class, ptype); idempotent. Empty (defaults stay in force) until real
    dates exist."""
    lo, hi = clip

    def q(c):
        out: dict = {}
        for cls in ("fundamentals_history", "shareholding_history"):
            rows = _rows(c, "SELECT key, knowable_at FROM provenance_knowable WHERE data_class=?", (cls,))
            by_pt: dict = {}
            for key, knew in rows:
                parts = key.split("|")
                if len(parts) < 3 or not knew:
                    continue
                ptype, period = parts[1], parts[-1]
                try:
                    lag = (date.fromisoformat(knew[:10]) - date.fromisoformat(period[:10])).days
                except ValueError:
                    continue
                if lo <= lag <= hi:
                    by_pt.setdefault(ptype, []).append(lag)
            for pt, vals in by_pt.items():
                vals.sort()
                chosen = _pct(vals, percentile)
                rec = {"n": len(vals), "p50": _pct(vals, 50), "p90": _pct(vals, 90),
                       "p95": _pct(vals, 95), "p99": _pct(vals, 99),
                       "chosen_lag": chosen, "percentile": percentile}
                out.setdefault(cls, {})[pt] = rec
                c.execute(
                    "INSERT OR REPLACE INTO provenance_lag_calibration "
                    "(data_class, period_type, n, p50, p90, p95, p99, chosen_lag, percentile, calibrated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))",
                    (cls, pt, rec["n"], rec["p50"], rec["p90"], rec["p95"], rec["p99"], chosen, percentile))
        return out
    return _with_conn(q, conn, write=True)


def _summarize_errs(errs: list) -> dict:
    """Summary stats for signed errors (real − modeled, days). LEAK = err>0 (model too early)."""
    errs = sorted(errs)
    n = len(errs)
    if n == 0:
        return {"n": 0}
    leaks = [e for e in errs if e > 0]
    return {
        "n": n, "mean": round(sum(errs) / n, 1), "median": errs[n // 2],
        "p10": errs[max(0, n // 10)], "p90": errs[min(n - 1, (9 * n) // 10)],
        "n_leaks": len(leaks), "leak_pct": round(100.0 * len(leaks) / n, 1),
        "leak_median": (sorted(leaks)[len(leaks) // 2] if leaks else 0),
        "leak_max": (max(leaks) if leaks else 0),
        "n_conservative": sum(1 for e in errs if e < 0),
        "n_exact": sum(1 for e in errs if e == 0),
    }


# ── lag_audit: measure the look-ahead leak vs the REAL filing dates ───────────
def lag_audit(conn=None, *, classes=("fundamentals_history", "shareholding_history"),
              persist: bool = True) -> dict:
    """Measure the look-ahead LEAK of the synthetic report_date against the REAL BSE filing dates,
    under three models: **baseline** (the producer's stored +50/+90 report_date), **calibrated**
    (period_end + the learned conservative lag), and **effective** (prefer the real date where it
    exists — leak 0 by construction — else calibrated → the blended expected leak). LEAK = real
    filing LATER than the model's date (model too early ⇒ a backtest sees the datum before it was
    public). Runs empty until observe() captures real dates — that empty state is honest."""
    def q(c):
        out: dict = {}
        rdb = _research_ro()
        for cls in classes:
            d = PROVENANCE.get(cls)
            if d is None:
                out[cls] = {"status": "unknown_class"}
                continue
            captured = _rows(c, "SELECT key, symbol, knowable_at FROM provenance_knowable WHERE data_class=?", (cls,))
            if not captured:
                out[cls] = {"status": "no_real_observations_yet", "n": 0}
                continue
            src = rdb if d.db == "research" else c
            if src is None:
                out[cls] = {"status": "research_db_absent", "n_captured": len(captured)}
                continue
            cal_lags = {pt: _calibrated_lag(cls, pt, conn=c) for pt in ("A", "Q", "_default")}
            base_errors, cal_errs = [], []
            for row in captured:
                key, sym, knew = row[0], row[1], row[2]
                parts = key.split("|")          # canonical period key = symbol|period_type|period_end
                period = parts[-1] if len(parts) >= 2 else None
                ptype = parts[1] if len(parts) >= 3 else None
                if not (period and knew):
                    continue
                try:
                    kd, pe = date.fromisoformat(knew[:10]), date.fromisoformat(period[:10])
                except ValueError:
                    continue
                # (a) baseline: the producer's stored report_date
                if ptype:
                    modeled = _scalar(src, f"SELECT {d.asof_col} FROM {d.tables[0]} "
                                           f"WHERE symbol=? AND period_type=? AND period_end=? LIMIT 1",
                                      (sym, ptype, period))
                else:
                    modeled = _scalar(src, f"SELECT {d.asof_col} FROM {d.tables[0]} "
                                           f"WHERE symbol=? AND period_end=? LIMIT 1", (sym, period))
                if modeled:
                    try:
                        base_errors.append((key, sym, modeled, knew,
                                            (kd - date.fromisoformat(modeled[:10])).days))
                    except ValueError:
                        pass
                # (b) calibrated: period_end + the learned conservative lag
                cal_errs.append((kd - (pe + timedelta(days=cal_lags.get(ptype, cal_lags["_default"])))).days)
            if not base_errors and not cal_errs:
                out[cls] = {"status": "no_matched_pairs", "n_captured": len(captured)}
                continue
            # de-model coverage (captured ÷ distinct archived periods) for the blended estimate
            archived = _scalar(src, f"SELECT COUNT(*) FROM (SELECT DISTINCT symbol, period_type, period_end "
                                    f"FROM {d.tables[0]})")
            demodel = round(len(captured) / archived, 3) if archived else None
            cal = _summarize_errs(cal_errs)
            blended = round((1 - demodel) * cal.get("leak_pct", 0.0), 2) if demodel is not None else None
            out[cls] = {
                "status": "ok", "n_pairs": len(base_errors),
                "baseline_producer_model": {"lag_days": _PRODUCER_LAG_DAYS.get(cls),
                                            **_summarize_errs([e[4] for e in base_errors])},
                "calibrated_model": {"lag_days": {pt: cal_lags[pt] for pt in ("A", "Q")}
                                     if cls == "fundamentals_history" else cal_lags["_default"], **cal},
                "effective": {"demodel_rate": demodel, "real_preferred_leak_pct": 0.0,
                              "blended_expected_leak_pct": blended,
                              "note": "where a real BSE date exists the leak is 0; the calibrated "
                                      "synthetic covers the rest → blended ≈ (1−demodel)×calibrated_leak"},
            }
            if persist and base_errors:
                c.executemany(
                    "INSERT INTO provenance_lag_audit (data_class, key, symbol, modeled_date, knowable_at, lag_error_days) "
                    "VALUES (?,?,?,?,?,?)", [(cls, *e) for e in base_errors])
        if rdb is not None:
            rdb.close()
        return out
    return _with_conn(q, conn, write=persist)


# ── universe_policy: surface the survivorship spine (with its FLOOR) ──────────
def universe_policy(conn=None, *, as_of: Optional[str] = None) -> dict:
    """The survivorship/universe-construction policy as a first-class returnable stamp,
    reusing the existing security_master spine (built from the raw bhav archive, keeps
    delisted names). Headlines the archive FLOOR + a left-censoring proxy + the
    asymmetric-survivorship & SME-exclusion disclosures (red-team blocker)."""
    def q(c):
        total = _scalar(c, "SELECT COUNT(*) FROM security_master")
        if total is None:
            return {"status": "security_master_empty",
                    "policy": "Survivorship spine not built in this DB (run security_master).",
                    "_provenance": provenance_for("survivorship", conn=c)}
        active = _scalar(c, "SELECT COUNT(*) FROM security_master WHERE status='ACTIVE'")
        inactive = _scalar(c, "SELECT COUNT(*) FROM security_master WHERE status='INACTIVE'")
        floor = _scalar(c, "SELECT MIN(first_date) FROM security_master")
        ceil_ = _scalar(c, "SELECT MAX(last_date) FROM security_master")
        left_censor = _scalar(c, "SELECT COUNT(*) FROM security_master WHERE first_date=?", (floor,)) if floor else None
        events = {row[0]: row[1] for row in
                  _rows(c, "SELECT event_type, COUNT(*) FROM security_events GROUP BY event_type")}
        ren_conf = _scalar(c, "SELECT COUNT(*) FROM security_renames WHERE confirmed=1")
        ren_cand = _scalar(c, "SELECT COUNT(*) FROM security_renames WHERE confirmed=0")
        universe_as_of = None
        if as_of:
            try:
                from src.automation import security_master as SM
                universe_as_of = len(SM.universe_on(as_of, conn=c))
            except Exception:  # noqa: BLE001
                universe_as_of = None
        return {
            "status": "ok",
            "policy": ("Survivorship-correct: universe built from RAW bhavcopy_rows (delisted/suspended "
                       "names RETAINED), not the current nse_equity_list snapshot."),
            "total_securities": total, "active": active, "delisted_or_inactive": inactive,
            "archive_floor": floor, "archive_ceiling": ceil_,
            "left_censored_at_floor": left_censor,
            "as_of": as_of, "universe_on_as_of": universe_as_of,
            "as_of_mechanism": "first_date <= d <= last_date  (security_master.universe_on)",
            "continuity_breaks": events,
            "renames": {"confirmed": ren_conf, "candidates": ren_cand},
            "disclosures": [
                f"Survivorship is correct only from the archive floor {floor}; delistings BEFORE the "
                f"archive start are not captured (left-censoring).",
                "Asymmetric: the price/survivorship spine keeps delisted names, but the fundamentals "
                "universe is the ~listed-today set — the two universes differ.",
                "Universe = NSE mainboard EQ/BE/BZ series; SME (SM/ST) excluded.",
                "Renames auto-confirmed via shared-ISIN clean handover; ISIN is sparse in the historical "
                "bhav feed, so rename resolution is biased toward currently-listed names until the "
                "authoritative NSE symbol-change feed is loaded.",
            ],
            "_provenance": provenance_for("survivorship", as_of=as_of, conn=c),
        }
    return _with_conn(q, conn)


# ── coverage_snapshot: the single read that powers the Coverage ledger ────────
def _latest_cci(c):
    """Latest credibility_series row per symbol → list of (n_resolved, ga, tier, momentum, momentum_3p, tape)."""
    sql = ("WITH latest AS (SELECT symbol, n_resolved, ga, tier, momentum, momentum_3p, tape, "
           "ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY period_year DESC, period_month DESC) rn "
           "FROM credibility_series) SELECT n_resolved, ga, tier, momentum, momentum_3p, tape FROM latest WHERE rn=1")
    return _rows(c, sql)


def coverage_snapshot(conn=None) -> dict:
    """Everything the Coverage & Settlement ledger renders — all defensive (None/empty
    on the 4-symbol stub or a missing table), so the screen degrades gracefully and
    honestly. Leads with the CCI robust-core FUNNEL, not breadth (red-team blocker)."""
    def q(c):
        snap: dict = {}
        snap["as_of"] = _scalar(c, "SELECT MAX(trade_date) FROM bhavcopy_dates") or \
            _scalar(c, "SELECT MAX(trade_date) FROM bhavcopy_rows")
        snap["build_at"] = _scalar(c, "SELECT datetime('now')")
        snap["universe"] = universe_policy(conn=c)

        # ── per-data-class coverage matrix (distinct symbols + latest as-of, defensive) ──
        classes = []
        active_n = snap["universe"].get("active") if isinstance(snap["universe"], dict) else None
        for key, d in PROVENANCE.items():
            if key == "survivorship":
                continue
            t = d.tables[0]
            # n_unit makes the count honest: per-symbol classes count distinct SYMBOLS;
            # market-level/index classes count distinct trading DAYS (counting their rows
            # would render a misleading huge "n" on a trust screen).
            if d.db == "research":
                rdb = _research_ro()
                if rdb is None:
                    classes.append({"key": key, "label": d.label, "source": d.source, "n": None,
                                    "n_unit": "symbols", "latest": None, "grain": d.grain,
                                    "basis": d.basis, "has_symbol": d.has_symbol, "cadence": d.cadence,
                                    "pct_active": None, "method_versioned": d.method_versioned,
                                    "note": "research.db absent here"})
                    continue
                n, n_unit = _scalar(rdb, f"SELECT COUNT(DISTINCT symbol) FROM {t}"), "symbols"
                latest = _scalar(rdb, f"SELECT MAX({d.asof_col}) FROM {t}") if d.asof_col else None
                rdb.close()
            elif d.has_symbol:
                n, n_unit = _scalar(c, f"SELECT COUNT(DISTINCT symbol) FROM {t}"), "symbols"
                latest = _scalar(c, f"SELECT MAX({d.asof_col}) FROM {t}") if d.asof_col else None
            else:
                n = (_scalar(c, f"SELECT COUNT(DISTINCT {d.asof_col}) FROM {t}") if d.asof_col
                     else _scalar(c, f"SELECT COUNT(*) FROM {t}"))
                n_unit = "days" if d.asof_col else "rows"
                latest = _scalar(c, f"SELECT MAX({d.asof_col}) FROM {t}") if d.asof_col else None
            pct = round(100.0 * n / active_n, 1) if (n and active_n and n_unit == "symbols") else None
            classes.append({"key": key, "label": d.label, "source": d.source, "n": n, "n_unit": n_unit,
                            "latest": latest, "grain": d.grain, "basis": d.basis, "has_symbol": d.has_symbol,
                            "cadence": d.cadence, "pct_active": pct, "method_versioned": d.method_versioned})
        snap["classes"] = classes

        # ── CCI settlement funnel + robustness (the headline honesty artifact) ──
        touched = _scalar(c, "SELECT COUNT(DISTINCT symbol) FROM concalls") or \
            _scalar(c, "SELECT COUNT(DISTINCT symbol) FROM concall_guidance")
        scored = _scalar(c, "SELECT COUNT(DISTINCT symbol) FROM concall_scores")
        series_syms = _scalar(c, "SELECT COUNT(DISTINCT symbol) FROM credibility_series")
        latest_cci = _latest_cci(c)
        b0 = b12 = b39 = b10 = unproven = mom_ready = mom4_ready = 0
        tiers_core: dict = {}
        cross: dict = {}   # tier -> {bucket: count}
        tape_counts = {"EARNING_TRUST": 0, "DETERIORATION": 0, "NULL": 0}
        for row in latest_cci:
            nres = row[0] or 0
            ga, tier, mom, mom3, tape = row[1], row[2], row[3], row[4], row[5]
            bucket = "0" if nres == 0 else "1-2" if nres <= 2 else "3-9" if nres <= 9 else ">=10"
            if nres == 0:
                b0 += 1
            elif nres <= 2:
                b12 += 1
            elif nres <= 9:
                b39 += 1
            else:
                b10 += 1
            if ga is None:
                unproven += 1
            if mom is not None:
                mom_ready += 1
            if mom3 is not None:
                mom4_ready += 1
            if nres >= 10 and tier:
                tiers_core[tier] = tiers_core.get(tier, 0) + 1
            if tier:
                cross.setdefault(tier, {}).setdefault(bucket, 0)
                cross[tier][bucket] += 1
            tape_counts[tape if tape in tape_counts else "NULL"] += 1
        snap["cci"] = {
            "funnel": {"touched": touched, "scored": scored, "series_symbols": series_syms,
                       "resolved_ge1": b12 + b39 + b10, "resolved_ge3": b39 + b10, "robust_core_ge10": b10},
            "n_resolved_buckets": {"0": b0, "1-2": b12, "3-9": b39, ">=10": b10},
            "unproven_ceiling": unproven, "momentum_ready": mom_ready, "momentum4_ready": mom4_ready,
            "tiers_robust_core": tiers_core, "tier_x_nresolved": cross, "tape": tape_counts,
            # numeric, sanity-bounded (a corrupt period_year would defeat a string MAX, e.g. '225-08')
            "latest_as_of": _scalar(c, "SELECT printf('%04d-%02d', period_year, period_month) "
                                       "FROM credibility_series WHERE period_year BETWEEN 2000 AND 2100 "
                                       "ORDER BY period_year DESC, period_month DESC LIMIT 1"),
            "paused_note": ("CCI runs on the analytics host and is currently PAUSED at a Gemini extraction "
                            "spend cap; the universe sweep (~9.6k transcripts pending) is incomplete. "
                            "Figures reflect the settled subset only."),
        }

        # ── lag audit + restatement count ──
        snap["lag_audit"] = lag_audit(conn=c, persist=False)
        snap["lag_headline"] = lag_headline(snap["lag_audit"])  # flat, render-ready
        snap["restatements"] = _scalar(c, "SELECT COUNT(*) FROM provenance_restatement") or 0
        snap["knowable_captured"] = _scalar(c, "SELECT COUNT(*) FROM provenance_knowable") or 0
        return snap
    return _with_conn(q, conn)


def lag_headline(la: dict | None = None, conn=None) -> dict:
    """A FLAT, render-ready summary of the look-ahead leak for the Coverage/provenance
    read — so the *effective* leak is VISIBLE, not buried in the nested lag_audit.

    Returns the three headline numbers a trust screen should lead with:
      {status, n_pairs, baseline_leak_pct, calibrated_leak_pct,
       effective_leak_pct, demodel_rate_pct, leak_cut_x}
    'effective' = where a real BSE filing date exists the leak is 0; the calibrated
    synthetic covers the rest → the blended expected leak. ``leak_cut_x`` = how many
    times the leak shrank vs the naive +90/+50 baseline. Degrades to status!='ok'
    when no real dates have accrued (forward-only)."""
    if la is None:
        la = lag_audit(conn=conn, persist=False)
    fh = (la or {}).get("fundamentals_history", {}) if isinstance(la, dict) else {}
    if not isinstance(fh, dict) or fh.get("status") != "ok":
        return {"status": (fh or {}).get("status", "no_real_observations_yet"),
                "n_pairs": (fh or {}).get("n", 0)}
    base = fh.get("baseline_producer_model", {}) or {}
    cal = fh.get("calibrated_model", {}) or {}
    eff = fh.get("effective", {}) or {}
    base_leak = base.get("leak_pct")
    eff_leak = eff.get("blended_expected_leak_pct")
    cut = round(base_leak / eff_leak, 1) if (base_leak and eff_leak) else None
    return {
        "status": "ok",
        "n_pairs": fh.get("n_pairs") or fh.get("n"),
        "baseline_leak_pct": base_leak,
        "calibrated_leak_pct": cal.get("leak_pct"),
        "effective_leak_pct": eff_leak,
        "demodel_rate_pct": round(100.0 * eff.get("demodel_rate", 0), 1) if eff.get("demodel_rate") is not None else None,
        "leak_cut_x": cut,
    }


# ── self-check (synthetic in-memory DB — no real data needed) ─────────────────
def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # minimal synthetic tables the snapshot/policy touch
    conn.executescript("""
        CREATE TABLE bhavcopy_dates (trade_date TEXT PRIMARY KEY);
        CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT);
        -- full column set so security_master.universe_on()'s own ensure-schema (which
        -- indexes isin) runs cleanly against the synthetic table, as it will on the VPS
        CREATE TABLE security_master (symbol TEXT PRIMARY KEY, first_date TEXT, last_date TEXT,
                                      n_days INTEGER, isin TEXT, company_name TEXT, listing_date TEXT,
                                      currently_listed INT, recently_traded INT, status TEXT, computed_at TEXT);
        CREATE TABLE security_events (symbol TEXT, event_type TEXT, ex_date TEXT, details TEXT, source TEXT);
        CREATE TABLE security_renames (old_symbol TEXT, new_symbol TEXT, effective_date TEXT,
                                       isin TEXT, source TEXT, confirmed INT);
        CREATE TABLE credibility_series (symbol TEXT, period_label TEXT, period_year INT, period_month INT,
                                         level REAL, ga REAL, n_resolved INT, momentum REAL, momentum_3p REAL,
                                         tape TEXT, tier TEXT);
        CREATE TABLE concalls (symbol TEXT, period_label TEXT);
        CREATE TABLE concall_scores (symbol TEXT);
    """)
    conn.executescript("""
        INSERT INTO bhavcopy_dates VALUES ('2026-06-25');
        INSERT INTO security_master (symbol, first_date, last_date, status, currently_listed) VALUES
            ('RELIANCE','2015-01-05','2026-06-25','ACTIVE',1),
            ('DELISTO','2012-03-01','2016-09-30','INACTIVE',0),
            ('OLDDEAD','2012-03-01','2013-01-01','INACTIVE',0);
        INSERT INTO security_events (symbol, event_type, ex_date) VALUES ('RELIANCE','DEMERGER','2023-07-20');
        INSERT INTO security_renames (old_symbol, new_symbol, confirmed) VALUES ('ZOMATO','ETERNAL',1),('FOO','BAR',0);
        INSERT INTO concalls VALUES ('RELIANCE','Q1'),('TANLA','Q1'),('THIN','Q1');
        INSERT INTO concall_scores VALUES ('RELIANCE'),('TANLA');
        -- RELIANCE robust (n=12, A+), TANLA thin (n=1, A+ → must NOT count in robust core), THIN unproven (ga NULL)
        INSERT INTO credibility_series VALUES
            ('RELIANCE','Q4',2026,3,82,90.0,12,4.0,6.0,'EARNING_TRUST','A+'),
            ('TANLA','Q4',2026,3,80,100.0,1,NULL,NULL,NULL,'A+'),
            ('THIN','Q4',2026,3,55,NULL,0,NULL,NULL,NULL,NULL);
    """)
    ensure_schema(conn)

    # observe is idempotent first-seen; key built via the SAME canonical period_key the
    # reader uses (period_type included for uniqueness — annual vs Q4 share period_end)
    kx = period_key("X", "A", "2024-03-31")
    assert observe("fundamentals_history", kx, conn=conn, symbol="X", knowable_at="2024-05-01") is True
    assert observe("fundamentals_history", kx, conn=conn, symbol="X", knowable_at="2099-01-01") is False
    assert _scalar(conn, "SELECT knowable_at FROM provenance_knowable WHERE data_class=? AND key=?",
                   ("fundamentals_history", kx)) == "2024-05-01", "earliest must be preserved"
    try:
        observe("not_a_class", "k", conn=conn)
        assert False, "unknown class should raise"
    except ValueError:
        pass

    # provenance_for: basis is canonical; modeled embeds the word; grain guard works
    p = provenance_for("bhav_eq", symbol="RELIANCE", as_of="2026-06-25", conn=conn)
    assert p["basis"] == AS_TRADED and p["modeled"] is False and "as-traded" in p["display"].lower(), p
    pm = provenance_for("fundamentals_history", symbol="ZZ", as_of="2024-03-31", conn=conn)
    assert pm["basis"] == MODELED and pm["modeled"] is True and "modeled" in pm["display"].lower(), pm
    assert pm["lag_days"] == 120, pm                       # conservative default (not the producer's 90)
    assert pm["effective_as_of"] == "2024-07-29", pm        # period_end + 120d (no-leak PIT date)
    pr = provenance_for("fundamentals_history", symbol="X", as_of="2024-03-31", period_type="A", conn=conn)
    assert pr["basis"] == INGESTED and pr["as_of"] == "2024-05-01", "real knowable_at must override modelled"
    assert pr["effective_as_of"] == "2024-05-01", "effective_as_of = the real date when it exists"
    # a same-period-end DIFFERENT period_type must NOT collide onto X's annual capture
    pq = provenance_for("fundamentals_history", symbol="X", as_of="2024-03-31", period_type="Q", conn=conn)
    assert pq["basis"] == MODELED, "Q4 must not read the annual knowable_at (period_type uniqueness)"
    pg = provenance_for("participant_oi", symbol="RELIANCE", conn=conn)
    assert pg["has_symbol"] is False and any("symbol ignored" in w for w in pg["warnings"]), pg

    # stamp attaches metadata
    s = stamp({"close": 1412.3}, "bhav_eq", symbol="RELIANCE", as_of="2026-06-25", conn=conn)
    assert s["close"] == 1412.3 and s["_provenance"]["basis"] == AS_TRADED

    # restatement log appends
    record_restatement("cci_series", "RELIANCE|Q4", "tier", "A", "A+", conn=conn, symbol="RELIANCE", reason="re-extract")
    assert _scalar(conn, "SELECT COUNT(*) FROM provenance_restatement") == 1

    # universe_policy: floor + asymmetry disclosures + counts
    up = universe_policy(conn=conn, as_of="2014-01-01")
    assert up["total_securities"] == 3 and up["active"] == 1 and up["delisted_or_inactive"] == 2, up
    assert up["archive_floor"] == "2012-03-01" and up["left_censored_at_floor"] == 2, up
    assert up["continuity_breaks"].get("DEMERGER") == 1 and up["renames"]["confirmed"] == 1, up
    assert up["universe_on_as_of"] is not None and any("left-censor" in dd.lower() for dd in up["disclosures"]), up

    # coverage_snapshot: the funnel + robust-core honesty
    cov = coverage_snapshot(conn=conn)
    f = cov["cci"]["funnel"]
    assert f["touched"] == 3 and f["scored"] == 2 and f["robust_core_ge10"] == 1, f
    assert cov["cci"]["n_resolved_buckets"] == {"0": 1, "1-2": 1, "3-9": 0, ">=10": 1}, cov["cci"]["n_resolved_buckets"]
    assert cov["cci"]["tiers_robust_core"] == {"A+": 1}, "thin A+ must NOT enter the robust core"
    assert cov["cci"]["unproven_ceiling"] == 1, cov["cci"]
    assert cov["cci"]["tier_x_nresolved"]["A+"]["1-2"] == 1, "cross-tab must expose the thin A+"
    assert cov["universe"]["total_securities"] == 3
    assert isinstance(cov["classes"], list) and any(cl["key"] == "participant_oi" for cl in cov["classes"])

    # synthetic-lag calibration: learn a conservative lag from real dates → flows into the
    # modeled fallback (lag_days + effective_as_of) and lag_audit's calibrated leak.
    for pe, kn in [("2024-06-30", "2024-08-09"), ("2024-09-30", "2024-11-13"), ("2024-12-31", "2025-02-14"),
                   ("2025-03-31", "2025-05-25"), ("2025-06-30", "2025-09-30")]:   # Q lags 40/44/45/55/92
        observe("fundamentals_history", period_key("CAL", "Q", pe), conn=conn, symbol="CAL", knowable_at=kn)
    cal = calibrate_synthetic_lag(conn=conn, percentile=95)
    assert cal["fundamentals_history"]["Q"]["chosen_lag"] == 92, cal      # p95 (nearest-rank) of the lags
    assert _calibrated_lag("fundamentals_history", "Q", conn=conn) == 92
    pcal = provenance_for("fundamentals_history", symbol="NOPE", as_of="2025-06-30", period_type="Q", conn=conn)
    assert pcal["basis"] == MODELED and pcal["lag_days"] == 92, pcal       # calibrated lag, not the 65 default
    assert pcal["effective_as_of"] == "2025-09-30", pcal                   # 2025-06-30 + 92d

    # lag_audit tolerates no-matched-pairs gracefully (synthetic has no research.db)
    la = lag_audit(conn=conn, persist=False)
    assert "fundamentals_history" in la

    # registry digest
    dig = provenance_registry_digest()
    assert len(dig) >= 25 and all("basis" in e for e in dig)

    # data-licensing posture: Screener=vendor-tos (migration target), exchange=public-record, computed=owned
    assert redistribution_status("fundamentals_history") == VENDOR_TOS
    assert redistribution_status("shareholding_history") == VENDOR_TOS
    assert redistribution_status("bhav_eq") == PUBLIC_RECORD
    assert redistribution_status("cci_series") == OWNED
    lic = licensing_digest()
    assert "fundamentals_history" in lic["migration_target"] and lic["counts"].get(VENDOR_TOS, 0) >= 2
    assert all("redistribution" in e for e in dig)

    print(f"provenance selftest: OK  ({len(PROVENANCE)} classes, "
          f"funnel touched={f['touched']}->core={f['robust_core_ge10']}, floor={up['archive_floor']})")


# ── CLI ───────────────────────────────────────────────────────────────────────
def _pp(obj, indent=0):
    import json
    print(json.dumps(obj, indent=2, default=str))


def main() -> None:
    ap = argparse.ArgumentParser(description="Provenance / integrity layer (the honest stamp + coverage).")
    ap.add_argument("--selftest", action="store_true", help="synthetic in-memory validation (no real data)")
    ap.add_argument("--coverage", action="store_true", help="print the coverage snapshot")
    ap.add_argument("--universe", action="store_true", help="print the survivorship/universe policy")
    ap.add_argument("--lag-audit", action="store_true", help="print the look-ahead leak (baseline vs calibrated vs effective)")
    ap.add_argument("--licensing", action="store_true", help="print the per-class redistribution posture (migration ledger)")
    ap.add_argument("--calibrate", action="store_true", help="learn the conservative synthetic lag from real BSE dates")
    ap.add_argument("--percentile", type=int, default=95, help="calibration percentile (default 95)")
    ap.add_argument("--registry", action="store_true", help="print the provenance registry digest")
    ap.add_argument("--stamp", metavar="DATA_CLASS", help="print the provenance stamp for a class")
    ap.add_argument("--symbol")
    ap.add_argument("--as-of", dest="as_of")
    ap.add_argument("--period-type", dest="period_type", help="A|Q for period-typed classes")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.selftest:
        _selftest(); return
    if args.registry:
        _pp(provenance_registry_digest()); return
    if args.stamp:
        _pp(provenance_for(args.stamp, symbol=args.symbol, as_of=args.as_of,
                           period_type=args.period_type)); return
    if args.universe:
        _pp(universe_policy(as_of=args.as_of)); return
    if args.licensing:
        _pp(licensing_digest()); return
    if args.calibrate:
        _pp(calibrate_synthetic_lag(percentile=args.percentile)); return
    if args.lag_audit:
        _pp(lag_audit()); return
    if args.coverage:
        _pp(coverage_snapshot()); return
    ap.print_help()


if __name__ == "__main__":
    main()
