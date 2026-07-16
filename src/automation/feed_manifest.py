"""Feed + signal manifests and the licence-class registry (D134 LANE-C; plan s4-C, layers L1/L3/L8).

Converts tribal feed wiring into DECLARED CONTRACTS (docs/patearn-analytics-company-plan.md s2):
every acquisition feed (L1) and every flagship derived series (L3) gets one declarative row here,
beside the code. Adding feed #22 or derived series #200 = adding a manifest row + the module; the
manifests power auto-docs, the licence gate, DQ coverage, and Pat's provenance answers. Pure
declarative registries: stdlib-only, NO DB access, NO network, inert on import.

LICENCE CLASSES (plan s3.4(3) - the legal data boundary, made mechanical)
-------------------------------------------------------------------------
  public-archive : fetched from an official/public primary source endpoint (NSE/BSE exchange
                   archives + APIs, NSE Indices constituent files). NOTE the honest nuance from
                   docs/data-licensing-decision.md s3: public-archive == PUBLIC-RECORD (our
                   compiled use of a public record), it is NOT a redistribution licence - resale
                   of raw exchange data would still need the exchange's data-services licence.
  licensed       : data under a commercial licence/subscription. NONE today - the class exists so
                   the gate has teeth the day one arrives.
  personal-broker: personal broker API entitlements (e.g. a personal Kite Connect feed). NONE
                   today; the LANE-I real-time seam (intraday_adapter) will register here.
  derived        : no external fetch - materialised entirely from tables/files we already store
                   (OWNED in docs/data-licensing-decision.md vocabulary; our IP).

THE LICENCE GATE (enforced by tests/test_feed_manifest.py): no feed whose licence_class is in
RESTRICTED_LICENCE_CLASSES ({licensed, personal-broker}) may be referenced by any src/web/*.py
source - restricted data must stay off every public surface BY CONSTRUCTION. The v1 gate is a
conservative source-text scan (see the test docstring for the approximation and its limits).

UNCLASSIFIED FEEDS (the honest gap - deliberately NOT in FEEDS)
---------------------------------------------------------------
Fetchers whose source has no honest fit in the enum are listed in UNCLASSIFIED_FEEDS with the
reason, instead of being defaulted to 'public-archive'. Today these are the Screener.in-era
sources (VENDOR-TOS in docs/data-licensing-decision.md s3, under Guardrail-#8 remediation via
the XBRL migration) and the RSS news feed ('per-source ToS' in the same doc).

TODO(D134 LANE-R + Ramana): decide the enum treatment for VENDOR-TOS-class sources - either a
fifth licence_class (e.g. 'vendor-tos-remediating', gated off public surfaces like the restricted
classes) or keep them out of FEEDS until the XBRL/BSE migrations retire them. Do NOT silently
move any UNCLASSIFIED key into FEEDS without that decision (a test pins them).

SIGNAL VALIDATION STATUSES (mirror docs/strategy-ledger.md verdicts VERBATIM - never soften)
--------------------------------------------------------------------------------------------
  descriptive-only                       : tested and/or fenced descriptive (MEP D62, Wolfe,
                                           seasonal-tape prereg, market internals).
  falsified-as-factor                    : return-tested, factor claim FALSIFIED (CCI).
  benchmark-gross-only                   : flat-cost/gross internal benchmark, "indicative, not
                                           validated" (RISKADJ 1.13; momentum NET ~0.09).
  validated-screen-only                  : the screen validated OOS, the tradeable book failed
                                           net of costs (Launchpad: "NO survivor net of costs").
  not-return-tested-as-standalone-alpha  : built + deployed lens, never run as alpha (the
                                           strategy-ledger Tier-3 class header).

Fences quote the ledger's exact recorded numbers where load-bearing; a fence here may only be
changed in the same commit as the corresponding docs/strategy-ledger.md verdict change.

CLI
---
    python -m src.automation.feed_manifest --selftest   # validate + print both manifest tables
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, fields

# --------------------------------------------------------------------------------------
# Enums (frozen vocabularies)
# --------------------------------------------------------------------------------------

LICENCE_CLASSES: frozenset = frozenset(
    {"public-archive", "licensed", "personal-broker", "derived"}
)

#: Classes the licence gate keeps OFF every public surface (plan s3.4(3)).
RESTRICTED_LICENCE_CLASSES: frozenset = frozenset({"licensed", "personal-broker"})

#: Verbatim-mirrored docs/strategy-ledger.md verdict vocabulary. Adding a value here means a NEW
#: ledger verdict class exists; never add a softer synonym for an existing one.
VALIDATION_STATUSES: frozenset = frozenset(
    {
        "descriptive-only",
        "falsified-as-factor",
        "benchmark-gross-only",
        "validated-screen-only",
        "not-return-tested-as-standalone-alpha",
    }
)

# --------------------------------------------------------------------------------------
# Dataclasses
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Feed:
    """One acquisition (or derived data-layer) feed - the L1 contract row.

    key           : registry key (== FEEDS dict key).
    module        : repo-relative path of the owning module (one path).
    source_org    : who publishes the data ("NSE", "BSE", "NSE Indices Ltd", "derived (internal)").
    cadence       : how often new data lands.
    licence_class : one of LICENCE_CLASSES.
    knowable_rule : the PIT clock - when a row becomes knowable (the D94/provenance discipline).
    fence_status  : the consumption fence recorded for this feed (descriptive-only, veto-only,
                    raw-archive, ...) - cite before consuming (D94 rows!=events lesson).
    tables        : the DB tables this feed owns/writes.
    notes         : one-line honest caveats (coverage limits, era boundaries, remediations).
    """

    key: str
    module: str
    source_org: str
    cadence: str
    licence_class: str
    knowable_rule: str
    fence_status: str
    tables: tuple
    notes: str


@dataclass(frozen=True)
class Signal:
    """One flagship derived series - the L3 contract row.

    key               : registry key (== SIGNALS dict key).
    module            : repo-relative path(s) of the engine module(s); a suite may list several,
                        whitespace-separated (every token must exist - tested).
    inputs            : upstream tables/feeds the series is computed from.
    validation_status : one of VALIDATION_STATUSES - the docs/strategy-ledger.md verdict, verbatim.
    fence             : the operational fence, with the ledger's recorded numbers where load-bearing.
    ledger_ref        : where in docs/strategy-ledger.md (or the decision log) the verdict lives.
    """

    key: str
    module: str
    inputs: tuple
    validation_status: str
    fence: str
    ledger_ref: str


# --------------------------------------------------------------------------------------
# FEEDS - the L1 acquisition manifest
# --------------------------------------------------------------------------------------

FEEDS: dict = {
    # ---------------- public-archive: NSE equities / indices tape ----------------
    "bhavcopy": Feed(
        key="bhavcopy",
        module="src/automation/bhavcopy.py",
        source_org="NSE (nsearchives)",
        cadence="daily (trading days, published ~18:30-19:30 IST)",
        licence_class="public-archive",
        knowable_rule="EOD publish same trading day; row knowable at publish, never intraday",
        fence_status="raw-archive (the pre-compute doctrine keeps it never normalised away)",
        tables=("bhavcopy_rows", "bhavcopy_dates"),
        notes="Primary sec_bhavdata_full (has DELIV_QTY/PER); UDIFF + legacy fallbacks carry no delivery.",
    ),
    "indexes": Feed(
        key="indexes",
        module="src/automation/indexes.py",
        source_org="NSE (nsearchives)",
        cadence="daily (trading days)",
        licence_class="public-archive",
        knowable_rule="EOD publish same trading day (ind_close_all file)",
        fence_status="raw-archive",
        tables=("index_rows", "index_dates"),
        notes="Daily OHLC + valuation per index (D32).",
    ),
    "indexes_tri": Feed(
        key="indexes_tri",
        module="research/explosive_moves/niftyindices_hist.py",
        source_org="NSE (niftyindices.com)",
        cadence="pull-on-demand (backfill tool; the union forward-test runner refreshes before judging)",
        licence_class="public-archive",
        knowable_rule="official TRI/G-sec history endpoints; values published EOD",
        fence_status="raw-archive",
        tables=("index_rows",),
        notes="TRI + long G-sec histories (S174/S175, ledger 16AI/16AK): 'Nifty 500 TRI', "
              "'Nifty Next 50 TRI', 'Nifty GS 10Yr', 'Nifty GS Compsite' [sic, official trading name]. "
              "Backfill verified to the paisa vs the daily indexes feed (PR cross-check).",
    ),
    "deals": Feed(
        key="deals",
        module="src/automation/deals.py",
        source_org="NSE",
        cadence="daily (current-day files only; history accrues from first run)",
        licence_class="public-archive",
        knowable_rule="same-evening publish (~19:30 IST); no free dated back-archive for bulk/block",
        fence_status="descriptive-only (named-flow banking; no stealth-accumulation claim - ledger)",
        tables=("bulk_block_deals", "fii_dii_flows"),
        notes="Bulk + block deals name the counterparty; FII/DII is market-level net flow.",
    ),
    "corp_actions": Feed(
        key="corp_actions",
        module="src/automation/corp_actions.py",
        source_org="NSE (corporate-actions API)",
        cadence="trailing-window poll (default 400d; deep backfill to 2004)",
        licence_class="public-archive",
        knowable_rule="exchange announcement rows served windowed; ex_date drives adjustment semantics",
        fence_status="raw-archive (feeds security_events continuity spine + adjust.py cross-validation)",
        tables=("corporate_actions",),
        notes="Resurrected 2026-07-06 after the legacy CSVs 404'd; liveness now watched by data_quality.",
    ),
    "equity_list": Feed(
        key="equity_list",
        module="src/automation/equity_list.py",
        source_org="NSE",
        cadence="snapshot refresh (replaced only on a successful, non-empty fetch)",
        licence_class="public-archive",
        knowable_rule="CURRENT snapshot only - NOT point-in-time (delisted names drop out; "
        "security_master keeps the survivorship-honest spine)",
        fence_status="allowlist (equity-vs-ETF separator; never a PIT universe)",
        tables=("nse_equity_list", "nse_etf_list"),
        notes="EQUITY_L.csv + the exchange ETF list (positive fund identification).",
    ),
    "membership": Feed(
        key="membership",
        module="src/automation/membership.py",
        source_org="NSE Indices Ltd (niftyindices.com)",
        cadence="snapshot per run (curated index set)",
        licence_class="public-archive",
        knowable_rule="current constituents stamped with snapshot_date; no weights provided",
        fence_status="raw-archive (sector->stock drill JOIN)",
        tables=("stock_index_membership",),
        notes="index_name keys must exactly match index_rows.index_name (D33b).",
    ),
    "surveillance": Feed(
        key="surveillance",
        module="src/automation/surveillance.py",
        source_org="NSE",
        cadence="daily (ASM/GSM lists + full price-band file)",
        licence_class="public-archive",
        knowable_rule="the day's list is the day's state; transitions derivable by self-join",
        fence_status="descriptive-only (label, don't filter - the coverage-cliff lesson)",
        tables=("surveillance_flags", "price_bands_current", "price_band_events"),
        notes="ASM/GSM stages as veto-CONTEXT chips; band state feeds the X-05 band-lock study.",
    ),
    "slb": Feed(
        key="slb",
        module="src/automation/slb.py",
        source_org="NSE (archives/slbs)",
        cadence="daily (two EOD files per trading day)",
        licence_class="public-archive",
        knowable_rule="EOD publish; 404 = holiday/not-published = clean skip",
        fence_status="descriptive-only (no study run on this feed yet - future consumers need prereg)",
        tables=("slb_volumes", "slb_open_positions"),
        notes="India's only short-interest proxy: lending-fee tape (flow) + open positions (stock).",
    ),
    "credit_ratings": Feed(
        key="credit_ratings",
        module="src/automation/credit_ratings.py",
        source_org="NSE (corporate-credit-rating API)",
        cadence="windowed poll (date-range JSON)",
        licence_class="public-archive",
        knowable_rule="BroadcastDateTime = the PIT clock (never the rating-action date)",
        fence_status="veto-only downside (downgrade/watch-negative haircut; absence is NEUTRAL, "
        "never a positive quality signal)",
        tables=("credit_rating_events",),
        notes="Heterogeneous agency strings -> ordinal ladder via parse_rating/notch_delta; "
        "coverage skews to rated (larger/debt-heavy) names.",
    ),
    "insider_events": Feed(
        key="insider_events",
        module="src/automation/insider_events.py",
        source_org="NSE (SEBI PIT Reg 7(2) disclosures)",
        cadence="windowed poll",
        licence_class="public-archive",
        knowable_rule="disclosure_dt = exchange DISCLOSURE/broadcast date, never the transaction date",
        fence_status="taxonomy-fenced ('promoter bought = bullish' is BANNED; plumbing classes "
        "never mix with open-market conviction)",
        tables=("insider_events", "insider_gg_seen"),
        notes="Dataset A flagship; person names stored as sha1 hashes (privacy convention).",
    ),
    "sast_events": Feed(
        key="sast_events",
        module="src/automation/sast_events.py",
        source_org="NSE (SAST Reg 29 + pledge Reg 31/32 listings)",
        cadence="chunked windowed poll (~570 + ~110 rows/month)",
        licence_class="public-archive",
        knowable_rule="exchange broadcast/system timestamp, never the event date",
        fence_status="descriptive-only (stake + pledge FLOW context; content-hash idempotent)",
        tables=("sast_reg29_events", "sast_pledge_events"),
        notes="Pledge flow with magnitude between the quarterly SHP stocks; names sha1-hashed.",
    ),
    "shareholding_xbrl": Feed(
        key="shareholding_xbrl",
        module="src/automation/shareholding_xbrl.py",
        source_org="NSE (SEBI Reg 31 shareholding-pattern XBRL)",
        cadence="quarterly filings (listing poll + per-filing XBRL instance)",
        licence_class="public-archive",
        knowable_rule="broadcastDate = the true PIT knowable_at; revisions carry their own broadcast",
        fence_status="raw-archive (source-stamped rows; Screener-era rows never overwritten)",
        tables=("shareholding_history", "shareholding_gg_seen", "shareholding_xbrl_gate"),
        notes="Guardrail-#8 replacement for the Screener shareholding scrape; adds promoter-pledge "
        "% (a metric the Screener era never had).",
    ),
    "fundamentals_xbrl": Feed(
        key="fundamentals_xbrl",
        module="src/automation/fundamentals_xbrl.py",
        source_org="NSE (corporates-financial-results XBRL)",
        cadence="results filings (event-driven poll; Phase-3 backfill in flight)",
        licence_class="public-archive",
        knowable_rule="exchange broadcast datetime via provenance.observe; restatements insert "
        "with their own broadcast, earliest preserved",
        fence_status="raw-archive (panel rules: conso preferred, discrete quarters only, "
        "nil/missing = NULL never zero)",
        tables=(
            "fundamentals_history",
            "fundamentals_restatements",
            "fundamentals_xbrl_seen",
            "fundamentals_xbrl_gate",
            "fundamentals_xbrl_backfill_progress",
        ),
        notes="Guardrail-#8 replacement for the Screener fundamentals scrape; banks mapped via "
        "the dedicated bank-format extractor (tag-based detection).",
    ),
    "fundamentals_filing_dates": Feed(
        key="fundamentals_filing_dates",
        module="src/automation/fundamentals_filing_dates.py",
        source_org="BSE (corporate announcements, category=Result)",
        cadence="backfill + windowed poll",
        licence_class="public-archive",
        knowable_rule="NEWS_DT = the actual filing timestamp -> provenance_knowable (retroactively "
        "de-models the +90d/+50d synthetic report_date lag)",
        fence_status="raw-archive (provenance backbone; the safest class per "
        "docs/data-licensing-decision.md)",
        tables=("bse_scrip_map",),
        notes="Writes provenance via provenance.observe(), never into fundamentals_history; "
        "BSE archive reaches back to 2006 (pre-2006 annuals stay modeled).",
    ),
    "concall_bse": Feed(
        key="concall_bse",
        module="src/automation/concall_bse.py",
        source_org="BSE (corporate announcements - Earnings Call Transcript)",
        cadence="windowed announcement poll + per-filing PDF download",
        licence_class="public-archive",
        knowable_rule="NEWS_DT = transcript-filing broadcast; transcript text stored on disk, not DB",
        fence_status="raw-archive (capture only; paid extraction is a separately-gated step)",
        tables=("concalls", "bse_scrip_map"),
        notes="De-Screener transcript DISCOVERY (exchange public record) and reaches delisted "
        "names; adds rows source='bse-ann' to the shared concalls table.",
    ),
    "results_calendar": Feed(
        key="results_calendar",
        module="src/automation/results_calendar.py",
        source_org="NSE (event-calendar API)",
        cadence="forward poll (next 30d default)",
        licence_class="public-archive",
        knowable_rule="board-meeting INTIMATIONS are filed in advance - knowable at filing, "
        "forward-looking by design",
        fence_status="descriptive-only (the forward 'who reports next' rail)",
        tables=("board_meetings",),
        notes="Distinct from the backward result filing (fundamentals_filing_dates rejects "
        "intimations; this captures them).",
    ),
    "fno_oi": Feed(
        key="fno_oi",
        module="src/automation/fno_oi.py",
        source_org="NSE (F&O UDiFF bhavcopy)",
        cadence="daily (trading days, after the cash bhav)",
        licence_class="public-archive",
        knowable_rule="EOD UDiFF publish; UDiFF era starts mid-2024 (legacy parser deferred)",
        fence_status="descriptor-only per D62 (characterises/confirms; never ranks until it "
        "passes the walk-forward + Deflated-Sharpe gate)",
        tables=("fno_oi_signals",),
        notes="Stock-futures OI vs price -> the four-quadrant buildup map + options PCR.",
    ),
    "participant_oi": Feed(
        key="participant_oi",
        module="src/automation/participant_oi.py",
        source_org="NSE (nsccl participant-wise OI file)",
        cadence="daily (published ~17:00-18:00 IST)",
        licence_class="public-archive",
        knowable_rule="same-evening publish; one row per (date, client_type)",
        fence_status="descriptor-only per D62 (market-level sentiment context, never a "
        "ranking/timing signal by itself)",
        tables=("participant_oi",),
        notes="Client/DII/FII/Pro long-short across index/stock futures & options - "
        "market-aggregate, not per-stock.",
    ),
    # ---------------- derived: the L2 canonical-store builders ----------------
    "security_master": Feed(
        key="security_master",
        module="src/automation/security_master.py",
        source_org="derived (internal)",
        cadence="rebuild from the stored archive (idempotent)",
        licence_class="derived",
        knowable_rule="derived spine - PIT honesty comes from the underlying bhav rows "
        "(first/last trade dates), NOT from the current-snapshot equity list",
        fence_status="raw-archive (survivorship + rename stitching + continuity breaks)",
        tables=("security_master", "security_events", "security_renames"),
        notes="The entity spine (the 'Vedanta problem'); built from bhavcopy_rows + "
        "corporate_actions so delisted names are kept.",
    ),
    "mtf_signals": Feed(
        key="mtf_signals",
        module="src/automation/mtf_signals.py",
        source_org="derived (internal)",
        cadence="nightly resample of bhavcopy_rows",
        licence_class="derived",
        knowable_rule="a bar is knowable at its period's LAST trading day EOD; the partial "
        "current bar is flagged is_partial and never read as closed",
        fence_status="descriptive-only (multi-timeframe alignment context; D43 rules locked)",
        tables=("bars_weekly", "bars_monthly", "weekly_signals", "monthly_signals"),
        notes="True calendar W/M bars + the two-tier DVPT scheme on those bars (D52).",
    ),
    "news_tagging": Feed(
        key="news_tagging",
        module="src/automation/news_tagging.py",
        source_org="derived (internal)",
        cadence="nightly deterministic tagger over stored headlines",
        licence_class="derived",
        knowable_rule="tag derived at tag time from a stored headline; precision-first "
        "(would rather miss than mis-tag)",
        fence_status="descriptive-only (gazetteer matcher over nse_equity_list; no LLM)",
        tables=("news_symbol_tags",),
        notes="The derivation is OWNED IP; the upstream sent_news headlines carry the "
        "news_feed per-source-ToS caveat (see UNCLASSIFIED_FEEDS).",
    ),
    # ---------------- personal-broker: the real-time seam (INTERFACE ONLY) ----------------
    "intraday_seam": Feed(
        key="intraday_seam",
        module="src/automation/intraday_adapter.py",
        source_org="(none wired) — personal broker feed optional; Kite key = Ramana's paid decision",
        cadence="opt-in intraday snapshots; NullSource (empty) until an entitlement is wired",
        licence_class="personal-broker",
        knowable_rule="a tick is knowable at its own ts_utc; the window is a bounded buffer, "
        "never a durable tape (EOD bhavcopy stays the archive)",
        fence_status="OFF every public surface BY CONSTRUCTION - the licence gate forbids any "
        "src/web reference to a personal-broker module (D134 LANE-I)",
        tables=("intraday_window",),
        notes="v1 = interface + bounded window store + NullSource + T0LiteSource STUB (NSE EOD-"
        "preliminary files, ~15:45-16:15 IST, Rs0, public-archive when wired). No Kite wiring.",
    ),
}

#: Ratchet floor: the number of feeds catalogued at build time (D134 LANE-C, 2026-07-15;
#: +1 intraday_seam, D134 LANE-I). tests/test_feed_manifest.py asserts len(FEEDS) >= MIN_FEEDS -
#: removing a feed row without consciously lowering this constant fails the suite.
MIN_FEEDS: int = 22

# --------------------------------------------------------------------------------------
# UNCLASSIFIED feeds - catalogued but deliberately NOT in FEEDS (no honest enum fit).
# TODO(D134 LANE-R + Ramana): see the module docstring - decide a fifth class or retire.
# --------------------------------------------------------------------------------------

UNCLASSIFIED_FEEDS: dict = {
    "screener": "Screener.in current-snapshot fundamentals scrape (fundamentals table). "
    "VENDOR-TOS in docs/data-licensing-decision.md s3; Guardrail-#8 remediation via "
    "fundamentals_xbrl. Not public-archive (vendor compilation), not licensed (no licence held).",
    "fundamentals_history": "Screener.in historical financials scrape (research.db). Same "
    "VENDOR-TOS class; being replaced by fundamentals_xbrl + the Phase-3 XBRL backfill.",
    "shareholding_history": "Screener.in shareholding-section scrape. VENDOR-TOS wrapper over "
    "an underlying PUBLIC-RECORD filing; replaced going-forward by shareholding_xbrl.",
    "concalls": "Concall CORPUS fetcher - transcript PDFs are BSE public record, but the "
    "DISCOVERY index comes via Screener.in (VENDOR-TOS per docs/data-licensing-decision.md); "
    "concall_bse.py is the de-Screener discovery path.",
    "news_feed": "Indian-market RSS headlines (sent_news). docs/data-licensing-decision.md s3 "
    "marks news_* 'per-source ToS' - NOT blessed as public-record; redistributed headlines "
    "would need a licensed news API. No honest fit in the v1 enum.",
    "enrich": "Company-profile dossier (company_profile) - Gemini synthesis grounded on web "
    "text fetched via screener.py (inherits the VENDOR-TOS caveat); paused at the Gemini cap.",
}

#: HTTP-using src/automation modules that are NOT acquisition feeds (the ratchet scan skips them).
KNOWN_NON_FEEDS: dict = {
    "digest": "outbound Telegram delivery only (candidate digest), no data acquisition",
    "season_digest": "outbound ops DM only (season-ops morning readout), no data acquisition",
    "fetch_retry": "shared throttle/holiday taxonomy helper for the fetchers, not a feed",
}

# --------------------------------------------------------------------------------------
# SIGNALS - the L3 flagship derived-series manifest
# --------------------------------------------------------------------------------------

SIGNALS: dict = {
    "dvpt": Signal(
        key="dvpt",
        module="src/automation/signals.py",
        inputs=("bhavcopy_rows",),
        validation_status="descriptive-only",
        fence="positioning descriptor (delivery-value per trade, R-tier windows); DELIV_MOM "
        "standalone recorded return/vol 0.76-0.85 / MaxDD -45% with no standalone edge - never a "
        "standalone ranker",
        ledger_ref="docs/strategy-ledger.md s'BLOCKING FAILURE MODELS' (ACCEL/PULLBACK/DELIV_MOM "
        "row) + s'Tier 3' (MEP/DVPT: confirmation, not prediction)",
    ),
    "mep": Signal(
        key="mep",
        module="src/automation/mep_signals.py",
        inputs=("bhavcopy_rows",),
        validation_status="descriptive-only",
        fence="signed accumulation/distribution character; NEVER ranks/sizes/sorts-by-default "
        "(D62, locked 2026-06-22)",
        ledger_ref="docs/strategy-ledger.md s'BLOCKING FAILURE MODELS' ('MEP-accumulation as "
        "alpha': Deflated-Sharpe DSR 0.45->0.36 when added; do not re-test as alpha) + D62",
    ),
    "rs_suite": Signal(
        key="rs_suite",
        module="src/automation/stock_rs.py src/automation/rrg.py src/automation/rs_phase.py "
        "src/automation/rsband.py src/automation/capture.py",
        inputs=("bhavcopy_rows", "index_rows", "ratio_rows", "stock_signals"),
        validation_status="not-return-tested-as-standalone-alpha",
        fence="relative-strength weather/context (RRG, RSI-of-RS, Mansfield, capture, rs_band_pct); "
        "descriptive surfaces only, never a standalone ranker",
        ledger_ref="docs/strategy-ledger.md s'Tier 3' (RS suite: deployed (descriptive))",
    ),
    "cpr": Signal(
        key="cpr",
        module="src/automation/cpr_signals.py",
        inputs=("bhavcopy_rows",),
        validation_status="not-return-tested-as-standalone-alpha",
        fence="structure pillar (P/BC/TC + width% across three degrees); descriptive surfaces only",
        ledger_ref="docs/strategy-ledger.md s'Tier 3' class header (BUILT + deployed; NOT "
        "return-tested as standalone alpha); D53",
    ),
    "wolfe": Signal(
        key="wolfe",
        module="src/automation/wolfe.py",
        inputs=("bhavcopy_rows", "corporate_actions"),
        validation_status="descriptive-only",
        fence="geometry lens; BULL winner-profile is a SELECTION edge only - FAILS as a book, "
        "BEAR fails the primary OOS bar; the 2/3/4 fractal detection gate is MANDATORY (D108)",
        ledger_ref="docs/strategy-ledger.md s'Wolfe winner-profile' (OOS re-validated 2026-07-11 "
        "under the D111 rebalance) + s'Tier 3'",
    ),
    "launchpad": Signal(
        key="launchpad",
        module="src/automation/launchpad_signals.py",
        inputs=("bhavcopy_rows", "stock_signals"),
        validation_status="validated-screen-only",
        fence="explosive-move PRECURSOR screen (MOM_CONT/COILED/PULLBACK, OOS hit 70-80%); the "
        "Tier-2 swing book recorded 'NO survivor net of costs' - screen only, never a book",
        ledger_ref="docs/strategy-ledger.md s'Tier 2' (Launchpad swing program: S1 +4.0% .. S4 "
        "negative at 1.5x cost) + D56",
    ),
    "seasonal": Signal(
        key="seasonal",
        module="src/automation/seasonal_tape.py",
        inputs=("bhavcopy_rows", "index_rows"),
        validation_status="descriptive-only",
        fence="25y calendar seasonality on PIT idiosyncratic residuals; FROZEN pre-registered "
        "family (hash-locked), placebo-gated; a 0-certified cell IS the finding - never a timing "
        "signal",
        ledger_ref="prereg_registry (module='seasonal_tape', first-registration-wins) + the "
        "seasonal-tape estate record (PROJECT_STATE)",
    ),
    "internals": Signal(
        key="internals",
        module="src/automation/market_internals.py",
        inputs=("bhavcopy_rows", "mep_signals"),
        validation_status="descriptive-only",
        fence="absolute market-health internals (breadth/delivery/dispersion/tape/coil); "
        "market-level context only, no per-stock claims",
        ledger_ref="deep-data insight-lens record (S110, bounded-snapshot exception); "
        "descriptive-only by design",
    ),
    "momentum_factor": Signal(
        key="momentum_factor",
        module="research/explosive_moves/factory.py src/automation/factor_league.py "
        "src/automation/auto_portfolios.py",
        inputs=("bhavcopy_rows", "momentum_scan"),
        validation_status="benchmark-gross-only",
        fence="RISKADJ flat-cost return/vol 1.13 is 'indicative, not validated' (naive 0.3%/turnover "
        "cost, static Rs5cr floor); momentum NET ~0.09 vs bench 0.85-0.89 under realistic cost; "
        "C-BLEND 1.32 is flat-cost-only and beats the index at NO AUM - internal benchmark, "
        "never sold as fundable",
        ledger_ref="docs/strategy-ledger.md s'Tier 1' (+ the honest caveat) + s'BLOCKING FAILURE "
        "MODELS' ('Momentum sold as a FUNDABLE strategy'; 'C-BLEND 50/50 as a FUNDABLE book "
        "2026-07-05c')",
    ),
    "cci": Signal(
        key="cci",
        module="src/automation/cci_series.py",
        inputs=("concalls", "concall_scores", "fundamentals_history"),
        validation_status="falsified-as-factor",
        fence="credibility as a PIT time series; Spearman ~0, HIGH-LOW excess -10% @12m "
        "(inverse, survivorship) - descriptive/veto only, NEVER ranked",
        ledger_ref="docs/strategy-ledger.md s'Concall Intelligence - RETURN-TESTED + FALSIFIED "
        "as a factor (2026-06-25)' + s'BLOCKING FAILURE MODELS' (CCI row)",
    ),
    "patearn_score": Signal(
        key="patearn_score",
        module="src/automation/scoring.py",
        inputs=("fundamentals", "fundamentals_history"),
        validation_status="not-return-tested-as-standalone-alpha",
        fence="rule-based 14-pattern quality score; quality is a veto/filter layer, not a ranker "
        "(QUALITY standalone: return/vol 0.76, alpha ~0.0 - ledger); C/A/B stay veto-only (D66)",
        ledger_ref="docs/strategy-ledger.md s'Tier 3' (patearn: PIT-backtestable but not run as "
        "alpha) + s'BLOCKING FAILURE MODELS' (QUALITY standalone row) + D66",
    ),
}

#: Ratchet floor for SIGNALS (same convention as MIN_FEEDS).
MIN_SIGNALS: int = 11

# --------------------------------------------------------------------------------------
# Read API
# --------------------------------------------------------------------------------------


def licence_distribution() -> dict:
    """Count of FEEDS per licence_class (sorted by class name)."""
    out: dict = {}
    for f in FEEDS.values():
        out[f.licence_class] = out.get(f.licence_class, 0) + 1
    return dict(sorted(out.items()))


def restricted_feeds() -> list:
    """Feeds the licence gate must keep off every public surface."""
    return [f for f in FEEDS.values() if f.licence_class in RESTRICTED_LICENCE_CLASSES]


def validate() -> list:
    """Structural invariants; returns a list of problem strings ([] = healthy).

    Belt for the box (where the pytest suite doesn't run): --selftest calls this, and
    tests/test_feed_manifest.py re-asserts the same contracts plus the licence gate.
    """
    problems: list = []
    for k, f in FEEDS.items():
        if f.key != k:
            problems.append("FEEDS[%r].key mismatch: %r" % (k, f.key))
        if f.licence_class not in LICENCE_CLASSES:
            problems.append("FEEDS[%r] licence_class %r not in enum" % (k, f.licence_class))
        if not f.tables:
            problems.append("FEEDS[%r] owns no tables" % k)
        for fld in fields(Feed):
            v = getattr(f, fld.name)
            if isinstance(v, str) and not v.strip():
                problems.append("FEEDS[%r].%s is empty" % (k, fld.name))
    for k, s in SIGNALS.items():
        if s.key != k:
            problems.append("SIGNALS[%r].key mismatch: %r" % (k, s.key))
        if s.validation_status not in VALIDATION_STATUSES:
            problems.append(
                "SIGNALS[%r] validation_status %r not in vocabulary" % (k, s.validation_status)
            )
        if not s.inputs:
            problems.append("SIGNALS[%r] has no inputs" % k)
        for fld in fields(Signal):
            v = getattr(s, fld.name)
            if isinstance(v, str) and not v.strip():
                problems.append("SIGNALS[%r].%s is empty" % (k, fld.name))
    overlap = set(UNCLASSIFIED_FEEDS) & set(FEEDS)
    if overlap:
        problems.append("UNCLASSIFIED_FEEDS overlap FEEDS: %s" % sorted(overlap))
    if len(FEEDS) < MIN_FEEDS:
        problems.append("FEEDS ratchet broken: %d < MIN_FEEDS %d" % (len(FEEDS), MIN_FEEDS))
    if len(SIGNALS) < MIN_SIGNALS:
        problems.append("SIGNALS ratchet broken: %d < MIN_SIGNALS %d" % (len(SIGNALS), MIN_SIGNALS))
    return problems


# --------------------------------------------------------------------------------------
# Rendering (--selftest)
# --------------------------------------------------------------------------------------


def _table(headers: tuple, rows: list, widths: tuple) -> str:
    def cell(text: str, w: int) -> str:
        text = str(text)
        return (text[: w - 2] + "..") if len(text) > w else text.ljust(w)

    lines = ["  ".join(cell(h, w) for h, w in zip(headers, widths))]
    lines.append("  ".join("-" * w for w in widths))
    for r in rows:
        lines.append("  ".join(cell(c, w) for c, w in zip(r, widths)))
    return "\n".join(lines)


def render_feeds_table() -> str:
    rows = [
        (f.key, f.licence_class, f.source_org, f.cadence, ",".join(f.tables))
        for f in FEEDS.values()
    ]
    return _table(
        ("FEED", "LICENCE", "SOURCE", "CADENCE", "TABLES"), rows, (26, 15, 30, 40, 44)
    )


def render_signals_table() -> str:
    rows = [
        (s.key, s.validation_status, ",".join(s.inputs), s.fence) for s in SIGNALS.values()
    ]
    return _table(
        ("SIGNAL", "VALIDATION_STATUS", "INPUTS", "FENCE"), rows, (16, 38, 34, 66)
    )


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" not in argv:
        print(__doc__.split("\n", 1)[0])
        print("usage: python -m src.automation.feed_manifest --selftest")
        return 2
    problems = validate()
    print("=" * 100)
    print("FEEDS manifest (L1 acquisition + derived data-layer) - %d rows" % len(FEEDS))
    print("=" * 100)
    print(render_feeds_table())
    print()
    print("=" * 100)
    print("SIGNALS manifest (L3 flagship derived series) - %d rows" % len(SIGNALS))
    print("=" * 100)
    print(render_signals_table())
    print()
    print("licence-class distribution : %s" % licence_distribution())
    print("restricted (gated) feeds   : %s" % sorted(f.key for f in restricted_feeds()))
    print(
        "UNCLASSIFIED (not in FEEDS; awaiting the LANE-R/Ramana enum decision): %s"
        % sorted(UNCLASSIFIED_FEEDS)
    )
    if problems:
        print("\nSELFTEST FAIL - %d problem(s):" % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    print("\nSELFTEST OK - %d feeds, %d signals, all invariants hold." % (len(FEEDS), len(SIGNALS)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
