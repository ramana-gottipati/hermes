"""PRIMARY-SOURCE fundamentals ingest — NSE financial-results XBRL (Guardrail #8).

Replaces the Screener.in dependency for NEW fundamentals periods. The NSE
``corporates-financial-results`` API returns, per filing: a direct XBRL instance URL,
the exchange broadcast timestamp (the true PIT ``knowable_at``), and explicit
Consolidated / Non-cumulative / bank / audited flags — everything the panel memo
(docs/institutional-panel-assessment.md, XBRL verdict 2026-07-02) requires. The XBRL
taxonomy is the shared ``in-bse-fin`` results taxonomy (verified live on 2025-26
filings, post the Apr-2025 Integrated-Filing regime change).

Panel rules enforced here:
  * consolidated preferred over standalone for the same (symbol, period_end); which one
    was used is recorded per row in the ``source`` column (NSE-XBRL-CONSO / -SA).
  * discrete quarters only — cumulative rows (H1/9M) are skipped; annual = the FY-span
    context of the Annual filing, never a sum of tags.
  * nil/missing tag is NULL, never zero (Borrowings: a filed balance sheet with no
    borrowings tags counts as genuinely debt-free — see _borrowings()).
  * knowable_at = exchange broadcast datetime via provenance.observe(basis=INGESTED
    semantics); restatements insert with their own broadcast, earliest is preserved.
  * forward-only: by default never overwrites a Screener-era row (source IS NULL);
    reconciliation (--reconcile) is the §4 gate evidence before C switches source.

Values are stored in ₹ crores (existing fundamentals_history convention; XBRL facts
are absolute INR → ÷1e7). Banks/NBFCs are mapped since Phase 2 (2026-07-02) by a
dedicated bank-format extractor (Screener bank conventions: Revenue = InterestEarned,
Financing Profit, structural PBT/PAT — see extract_bank_for). Detection is tag-based
(InterestEarned), never the listing flag (HDFCBANK's own listing says bank="N").
The bank rupee core gated = Revenue / Net Profit / Financing Profit.

Run (VPS):
  python -m src.automation.fundamentals_xbrl --probe RELIANCE
  python -m src.automation.fundamentals_xbrl --reconcile --symbols RELIANCE,TCS,ITC
  python -m src.automation.fundamentals_xbrl --ingest --since 2026-04-01 --symbols ...
  python -m src.automation.fundamentals_xbrl --ingest --since 2026-06-25   # global window
  python -m src.automation.fundamentals_xbrl --regate --symbols HDFCBANK   # after a mapper change
  python -m src.automation.fundamentals_xbrl --selftest                    # synthetic, no network/DB
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from src.automation import provenance

log = logging.getLogger("hermes.fundamentals_xbrl")

RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")
HERMES_DB = os.environ.get("HERMES_DB", "/opt/hermes/data/hermes.db")

_NSE_HOME = "https://www.nseindia.com"
_NSE_REF = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"
_NSE_API = "https://www.nseindia.com/api/corporates-financial-results"
# Apr-2025 SEBI Integrated-Filing regime: results filed since then flow through a NEW
# endpoint (the legacy API stops at Apr-2025 + late old-period filers). Path recovered
# from /dist/js/sections/corporate-filings.js on 2026-07-02.
_NSE_IF_API = "https://www.nseindia.com/api/integrated-filing-results"
_NSE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/122 Safari/537.36")
REQUEST_PAUSE = 1.5          # match the house BSE/NSE pacing (concall_bse / insider_events)
# Results-season guard (AUD-23): first-seen symbols cost ~8 paced gate-evidence
# fetches each; a heavy night can list hundreds of them. Uncached gate checks
# past this budget defer to the NEXT nightly run (verdicts are cached forever
# once computed, so the cohort still converges within a few nights).
GATE_BUDGET_PER_RUN = int(os.environ.get("HERMES_XBRL_GATE_BUDGET", "25"))

SOURCE_CONSO = "NSE-XBRL-CONSO"
SOURCE_SA = "NSE-XBRL-SA"

_CR = 1e7                    # absolute INR -> ₹ crores (house storage convention)


# ── NSE session (insider_events pattern: prime anti-bot cookies, then API) ────
def _nse_session():
    s = requests.Session()
    h = {"User-Agent": _NSE_UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _NSE_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)
    s.get(_NSE_REF, headers=h, timeout=20)
    return s, h


def _dmy(d: str) -> str:
    """ISO date -> DD-MM-YYYY (the NSE API's query format)."""
    return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")


_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _parse_nse_dt(s: Optional[str]) -> Optional[str]:
    """'16-Jan-2025 20:20:21' / '16-Jan-2025' -> ISO ('2025-01-16 20:20:21')."""
    if not s:
        return None
    m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?", s.strip())
    if not m:
        return None
    dd, mon, yyyy, hms = m.groups()
    iso = f"{yyyy}-{_MON[mon.title()]:02d}-{dd}"
    return f"{iso} {hms}" if hms else iso


def list_filings(*, symbol: Optional[str] = None, period: str = "Quarterly",
                 from_date: Optional[str] = None, to_date: Optional[str] = None,
                 session=None, headers=None) -> list:
    """Normalized result-filing rows from the NSE API (symbol-scoped or date-window).

    Each row: symbol, company, period ('Quarterly'/'Annual'), relating_to, from_date,
    to_date (ISO period bounds), consolidated (bool), cumulative (bool), audited,
    bank (bool), broadcast (ISO datetime — the PIT knowable_at), xbrl_url.
    """
    if session is None:
        session, headers = _nse_session()
    params = {"index": "equities", "period": period}
    if symbol:
        params["symbol"] = symbol
    if from_date:
        params["from_date"] = _dmy(from_date)
    if to_date:
        params["to_date"] = _dmy(to_date)
    r = session.get(_NSE_API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()
    items = j if isinstance(j, list) else (j.get("data") or [])
    out = []
    for it in items:
        xbrl = (it.get("xbrl") or "").strip()
        if not xbrl.lower().endswith(".xml"):
            continue
        fd, td = _parse_nse_dt(it.get("fromDate")), _parse_nse_dt(it.get("toDate"))
        if not td:
            continue
        out.append({
            "symbol": (it.get("symbol") or "").strip(),
            "company": it.get("companyName"),
            "period": it.get("period") or period,
            "relating_to": it.get("relatingTo"),
            "from_date": (fd or "")[:10] or None,
            "to_date": td[:10],
            "consolidated": (it.get("consolidated") or "").strip().lower() == "consolidated",
            "cumulative": (it.get("cumulative") or "").strip().lower() == "cumulative",
            "audited": (it.get("audited") or "").strip(),
            "bank": (it.get("bank") or "N").strip().upper() == "Y",
            "broadcast": _parse_nse_dt(it.get("broadCastDate") or it.get("filingDate")),
            "xbrl_url": xbrl,
        })
    return out


def list_integrated_filings(*, symbol: Optional[str] = None,
                            from_date: Optional[str] = None, to_date: Optional[str] = None,
                            session=None, headers=None) -> list:
    """Financial rows from the Integrated-Filing API (results broadcast Apr-2025 →).

    The listing is thin (no period bounds / consolidated / bank flags) — those come from
    the XBRL instance's own meta tags, so integrated filings are parse-first-classify.
    Returns: symbol, qe_date, broadcast (ISO), revised (bool), xbrl_url.
    """
    if session is None:
        session, headers = _nse_session()
    params = {"index": "equities"}
    if symbol:
        params["symbol"] = symbol
    if from_date:
        params["from_date"] = _dmy(from_date)
    if to_date:
        params["to_date"] = _dmy(to_date)
    r = session.get(_NSE_IF_API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()
    items = j if isinstance(j, list) else (j.get("data") or [])
    out = []
    for it in items:
        if "financial" not in (it.get("type") or "").lower():
            continue                      # governance filings share the endpoint
        xbrl = (it.get("xbrl") or "").strip()
        if not xbrl.lower().endswith(".xml"):
            continue
        qe = _parse_nse_dt((it.get("qe_Date") or "").title())
        out.append({
            "symbol": (it.get("symbol") or "").strip(),
            "company": it.get("cmName"),
            "qe_date": (qe or "")[:10] or None,
            "broadcast": _parse_nse_dt(it.get("broadcast_Date")),
            "revised": bool(it.get("revised_Date")) or (it.get("type_Sub") or "") == "Revised",
            "xbrl_url": xbrl,
        })
    return out


def fetch_instance(url: str, *, session=None, headers=None) -> Optional[str]:
    if session is None:
        session, headers = _nse_session()
    try:
        r = session.get(url, headers=headers, timeout=45)
        if r.status_code != 200:
            log.warning("xbrl fetch %s -> HTTP %s", url, r.status_code)
            return None
        return r.text
    except requests.RequestException as e:  # noqa: PERF203
        log.warning("xbrl fetch %s failed: %s", url, e)
        return None


# ── XBRL instance parsing ─────────────────────────────────────────────────────
_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_instance(xml_text: str) -> dict:
    """Parse a results-taxonomy instance into {contexts, facts, meta}.

    contexts: id -> {"start","end"} (duration) or {"instant"}
    facts:    list of (localname, contextRef, value_or_None)  — xsi:nil / empty -> None
    """
    root = ET.fromstring(xml_text)
    contexts: dict = {}
    facts: list = []
    for el in root.iter():
        ln = _local(el.tag)
        if ln == "context":
            cid = el.get("id")
            start = end = instant = None
            for p in el.iter():
                pl = _local(p.tag)
                if pl == "startDate":
                    start = (p.text or "").strip()
                elif pl == "endDate":
                    end = (p.text or "").strip()
                elif pl == "instant":
                    instant = (p.text or "").strip()
            if cid:
                contexts[cid] = {"instant": instant} if instant else {"start": start, "end": end}
        elif el.get("contextRef") is not None:
            if el.get(_XSI_NIL) == "true":
                val = None
            else:
                val = (el.text or "").strip() or None
            facts.append((ln, el.get("contextRef"), val))
    meta = {}
    for name, _ctx, val in facts:
        if name in ("NatureOfReportStandaloneConsolidated", "WhetherResultsAreAuditedOrUnaudited",
                    "DateOfStartOfReportingPeriod", "DateOfEndOfReportingPeriod",
                    "DateOfStartOfFinancialYear", "DateOfEndOfFinancialYear",
                    "LevelOfRoundingUsedInFinancialStatements", "Symbol", "ScripCode"):
            meta.setdefault(name, val)
    return {"contexts": contexts, "facts": facts, "meta": meta}


def _num(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def _ctx_ids(parsed: dict, *, end: str, min_days: int, max_days: int) -> set:
    """Duration-context ids ending at ``end`` with a span in [min_days, max_days]."""
    out = set()
    for cid, c in parsed["contexts"].items():
        if c.get("end") != end or not c.get("start"):
            continue
        try:
            span = (date.fromisoformat(c["end"]) - date.fromisoformat(c["start"])).days
        except ValueError:
            continue
        if min_days <= span <= max_days:
            out.add(cid)
    return out


def _instant_ids(parsed: dict, *, at: str) -> set:
    return {cid for cid, c in parsed["contexts"].items() if c.get("instant") == at}


def _fact(parsed: dict, names, ctx_ids: set) -> Optional[float]:
    """First numeric fact among ``names`` (in priority order) within ctx_ids; nil -> None."""
    if isinstance(names, str):
        names = (names,)
    for name in names:
        for ln, ctx, val in parsed["facts"]:
            if ln == name and ctx in ctx_ids:
                n = _num(val)
                if n is not None:
                    return n
    return None


def _borrowings(parsed: dict, inst_ids: set) -> Optional[float]:
    """Total borrowings (₹ absolute). NULL unless a balance sheet was actually filed;
    a filed balance sheet (EquityAndLiabilities present) with no borrowings tags is a
    genuinely debt-free company -> 0.0 (the one place absent legitimately means zero)."""
    cur = _fact(parsed, "BorrowingsCurrent", inst_ids)
    non = _fact(parsed, "BorrowingsNoncurrent", inst_ids)
    if cur is None and non is None:
        if _fact(parsed, "EquityAndLiabilities", inst_ids) is not None:
            return 0.0
        return None
    return (cur or 0.0) + (non or 0.0)


def extract_metrics(parsed: dict, filing: dict) -> dict:
    """Legacy-listing wrapper: period 'Annual' -> the FY set, else the quarter set."""
    kind = "A" if filing["period"] == "Annual" else "Q"
    return extract_for(parsed, kind=kind, end=filing["to_date"])


# ── bank/NBFC results taxonomy (Phase 2, 2026-07-02) ─────────────────────────
# Detection is TAG-BASED (InterestEarned present), never the listing's `bank`
# flag — HDFCBANK's own legacy listing rows carry bank="N" (verified 2026-07-02),
# and integrated-filing listings carry no flag at all.
def _is_bank_instance(parsed: dict) -> bool:
    return any(n == "InterestEarned" for n, _c, _v in parsed["facts"])


def extract_bank_for(parsed: dict, *, kind: str, end: str) -> dict:
    """Bank-format extraction in Screener's bank conventions (validated against
    HDFCBANK 2026-03-31 conso + standalone, exact to the rupee):

      Revenue          = InterestEarned
      Interest         = InterestExpended
      Expenses         = OperatingExpenses + ProvisionsOtherThanTaxAndContingencies
      Financing Profit = Revenue - Interest - Expenses
      Profit before tax = OperatingProfitBeforeProvisionAndContingencies - Provisions
                          + ExceptionalItems
      Net Profit        = Profit before tax - TaxExpense + ShareOfProfitLossOfAssociates

    PBT/PAT are DERIVED structurally rather than read from their tags (filers
    misuse them — HDFCBANK's own note admits stuffing minority interest into
    ExceptionalItems because "the sheet was throwing an error"). Net Profit
    includes ExceptionalItems (economic truth; SBIN's genuine Q3-FY24 pension
    provision reconciles Screener EXACTLY only that way) — a filing that abuses
    the exceptional tag diverges from Screener and honestly gate-fails until
    the quarter ages out of the evidence window. Tag fallbacks apply only when
    the structural components are missing.

    QUARTERLY ONLY: Screener's bank ANNUAL series comes from annual reports
    (separate Depreciation line the results-XBRL doesn't carry — HDFCBANK
    FY24 Financing Profit off by exactly the year's depreciation), so bank
    annual rows are skipped loudly; Phase-3 annual-report XBRL owns them.
    No balance-sheet instants either (bank BS taxonomy differs; Screener bank
    pages carry no ROCE).
    """
    if kind == "A":
        return {}
    ids = {"OneD"} if "OneD" in parsed["contexts"] else \
        _ctx_ids(parsed, end=end, min_days=80, max_days=100)
    if not ids:
        return {}

    rev = _fact(parsed, "InterestEarned", ids)
    int_exp = _fact(parsed, "InterestExpended", ids)
    op_exp = _fact(parsed, "OperatingExpenses", ids)
    if op_exp is None:
        excl = _fact(parsed, "ExpenditureExcludingProvisionsAndContingencies", ids)
        if excl is not None and int_exp is not None:
            op_exp = excl - int_exp
    prov = _fact(parsed, "ProvisionsOtherThanTaxAndContingencies", ids)
    opbp = _fact(parsed, "OperatingProfitBeforeProvisionAndContingencies", ids)
    tax = _fact(parsed, "TaxExpense", ids)
    oi = _fact(parsed, "OtherIncome", ids)
    eps = _fact(parsed, ("BasicEarningsPerShareAfterExtraordinaryItems",
                         "BasicEarningsPerShareBeforeExtraordinaryItems"), ids)
    eqcap = _fact(parsed, "PaidUpValueOfEquityShareCapital", ids)

    # PBT and NP both include ExceptionalItems (economic truth; SBIN's genuine
    # Q3-FY24 pension provision is 61% off without it). NP additionally carries
    # the equity-method associates line (SBIN/ICICIBANK conso ~2% short without
    # it) and stays GROSS of minority interest (HDFCBANK evidence).
    excep = _fact(parsed, "ExceptionalItems", ids)
    pbt = (opbp - prov + (excep or 0.0)) if (opbp is not None and prov is not None) else \
        _fact(parsed, ("ProfitLossFromOrdinaryActivitiesBeforeTax", "ProfitBeforeTax"), ids)
    assoc = _fact(parsed, "ShareOfProfitLossOfAssociates", ids)
    pat = (pbt - tax + (assoc or 0.0)) if (pbt is not None and tax is not None) else \
        _fact(parsed, "ProfitLossForThePeriod", ids)

    # blank/zero-filled column guard (same rationale as the non-bank path)
    if all((x or 0.0) == 0.0 for x in (rev, int_exp, pbt, pat)):
        return {}

    m: dict = {}

    def put(name, v, scale=_CR):
        if v is not None:
            m[name] = round(v / scale, 4) if scale else v

    put("Revenue", rev)
    put("Interest", int_exp)
    put("Other Income", oi)
    put("Profit before tax", pbt)
    put("Net Profit", pat)
    put("EPS in Rs", eps, scale=None)
    put("Equity Capital", eqcap)
    put("Provisions", prov)          # credit cost as its OWN metric (also folded into Expenses below);
                                     # enables credit_cost_ratio = Provisions / Revenue for banks/NBFCs
    if op_exp is not None and prov is not None:
        put("Expenses", op_exp + prov)
        if rev is not None and int_exp is not None:
            fp = rev - int_exp - (op_exp + prov)
            put("Financing Profit", fp)
            if rev:
                m["Financing Margin %"] = round(fp / rev * 100.0, 2)
    return m


def extract_for(parsed: dict, *, kind: str, end: str) -> dict:
    """(metric_name -> value) for one period of one instance, in fundamentals_history
    conventions. kind 'Q' -> the discrete-quarter P&L set; 'A' -> the FY-span P&L set +
    balance-sheet instants at FY end + derived ROCE %. Money in ₹ crores.
    Bank/NBFC instances (detected by tags, not listing flags) dispatch to the
    bank-format extractor.
    """
    if _is_bank_instance(parsed):
        return extract_bank_for(parsed, kind=kind, end=end)
    # The results-taxonomy encodes the table COLUMN in the context id — OneD = current
    # discrete quarter, FourD = year-to-date (== the FY in an Annual filing), OneI =
    # instant at period end. Filers routinely stamp DEGENERATE dates into FourD (the
    # RELIANCE FY24 instance repeats the Q4 dates), so the named context is primary and
    # the date-span match is only a fallback for nonstandard filing utilities.
    if kind == "A":
        ids = {"FourD"} if "FourD" in parsed["contexts"] else \
            _ctx_ids(parsed, end=end, min_days=350, max_days=380)
    else:
        ids = {"OneD"} if "OneD" in parsed["contexts"] else \
            _ctx_ids(parsed, end=end, min_days=80, max_days=100)
    if not ids:
        return {}

    m: dict = {}

    def put(name, v, scale=_CR):
        if v is not None:
            m[name] = round(v / scale, 4) if scale else v

    sales = _fact(parsed, ("RevenueFromOperations", "RevenueFromOperation"), ids)
    other_inc = _fact(parsed, "OtherIncome", ids)
    pbeit = _fact(parsed, "ProfitBeforeExceptionalItemsAndTax", ids)
    pbt = _fact(parsed, "ProfitBeforeTax", ids)
    interest = _fact(parsed, "FinanceCosts", ids)
    dep = _fact(parsed, "DepreciationDepletionAndAmortisationExpense", ids)
    pat = _fact(parsed, "ProfitLossForPeriod", ids)
    eps = _fact(parsed, ("BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                         "BasicEarningsLossPerShareFromContinuingOperations"), ids)
    eqcap = _fact(parsed, "PaidUpValueOfEquityShareCapital", ids)

    put("Sales", sales)
    put("Other Income", other_inc)
    put("Profit before tax", pbt)
    put("Interest", interest)
    put("Depreciation", dep)
    put("Net Profit", pat)
    put("EPS in Rs", eps, scale=None)
    put("Equity Capital", eqcap)

    # Screener-convention Operating Profit (EBITDA, ex other income):
    #   OP = PBT-before-exceptional + FinanceCosts + Depreciation - OtherIncome
    base = pbeit if pbeit is not None else pbt
    if base is not None and interest is not None and dep is not None:
        op = base + interest + dep - (other_inc or 0.0)
        put("Operating Profit", op)
        if sales:
            m["OPM %"] = round(op / sales * 100.0, 2)

    # a column whose entire rupee core is EXACTLY zero is a blank/zero-filled column
    # (late filers pad the quarter column with 0s — IL&FSTRANS FY19), not a result
    if all((x or 0.0) == 0.0 for x in (sales, pat, pbt, interest, dep)):
        return {}

    if kind == "A":
        inst = _instant_ids(parsed, at=end)
        reserves = _fact(parsed, ("OtherEquity", "ReserveExcludingRevaluationReserves"), inst)
        borrow = _borrowings(parsed, inst)
        put("Reserves", reserves)
        put("Borrowings", borrow)
        # ROCE % (Screener defn ≈ (PBT + Interest) / (EqCap + Reserves + Borrowings)).
        # Every component must be REAL (nil ≠ zero) — no coerced zeros in the C-score path.
        if None not in (pbt, interest, eqcap, reserves, borrow):
            ce = eqcap + reserves + borrow
            if ce > 0:
                m["ROCE %"] = round((pbt + interest) / ce * 100.0, 2)
    return m


# ── persistence ───────────────────────────────────────────────────────────────
def _ensure_source_column(con: sqlite3.Connection) -> None:
    cols = [r[1] for r in con.execute("PRAGMA table_info(fundamentals_history)")]
    if "source" not in cols:
        con.execute("ALTER TABLE fundamentals_history ADD COLUMN source TEXT")
    con.execute("""CREATE TABLE IF NOT EXISTS fundamentals_xbrl_gate(
        symbol TEXT PRIMARY KEY, checked_at TEXT, pass INTEGER, detail TEXT)""")
    # results-season survival (AUD-23): instances already processed are never
    # re-fetched — a revised filing arrives under a NEW xml url, so url-keyed
    # skip is restatement-safe (same pattern as insider/shareholding)
    con.execute("""CREATE TABLE IF NOT EXISTS fundamentals_xbrl_seen(
        xml_url TEXT PRIMARY KEY, processed_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    # revision ledger (kill-switch #4, validation memo §5): INSERT OR REPLACE on
    # fundamentals_history erases the prior value, so a restatement is only countable
    # if journaled at write time. One row per revising filing; broadcast = its PIT clock.
    con.execute("""CREATE TABLE IF NOT EXISTS fundamentals_restatements(
        symbol TEXT NOT NULL, period_type TEXT NOT NULL, period_end TEXT NOT NULL,
        broadcast TEXT NOT NULL, n_changed INTEGER NOT NULL,
        listed_revised INTEGER NOT NULL DEFAULT 0,
        recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (symbol, period_type, period_end, broadcast))""")


# per-symbol series-continuity gate (reconciliation 2026-07-02, 15-symbol cohort):
# Screener-era rows use restated/netted definitions for SOME symbols (ITC excise-gross
# revenue, ULTRACEMCO merger restatement, LT other-operating-income) — appending as-filed
# XBRL rows to such a series would corrupt every cross-boundary CAGR downstream (C-score,
# patearn growth patterns). A symbol only gets XBRL rows once its latest overlapping
# periods MATCH on the rupee core (Sales / Net Profit / Operating Profit); mismatching
# symbols stay Screener-flagged until the Phase-2 definitional mapper.
_GATE_METRICS = ("Sales", "Net Profit", "Operating Profit",      # non-bank rupee core
                 "Revenue", "Financing Profit")                   # bank rupee core
_GATE_TOL = 0.02
# Screener rounds small-cap rupee figures to whole crores, so the flat 2% RELATIVE gate
# spuriously rejects tiny values (a ₹5cr line ±0.5cr rounding = 10% rel). An ABSOLUTE band
# floors that: a row passes if within 2% rel OR within ₹0.5cr abs. Correctness fix, not a
# loosening — on the S137/Phase-3 audit cohort it clears the rounding fails
# (VIKASECO/AHLEAST/NUVOCO/UMIYA-MRO/EIMCOELECO, |Δ|≤0.45cr) while genuine definitional
# breaks stay failed (ITC/HDFCBANK/LTF/ANANDRATHI, |Δ|≥28cr). Every _GATE_METRICS entry is a
# ₹-crore magnitude, so a flat crore floor is dimensionally sound.
_GATE_ABS_FLOOR_CR = 0.5


def _continuity_gate(con: sqlite3.Connection, sym: str, xbrl_rows: list) -> bool:
    """xbrl_rows: [(ptype, period_end, metric, value)] parsed this run. Cached verdict in
    fundamentals_xbrl_gate. Symbols with no Screener overlap at all auto-pass (new
    listings — there is no series to be inconsistent with)."""
    row = con.execute("SELECT pass FROM fundamentals_xbrl_gate WHERE symbol=?", (sym,)).fetchone()
    if row is not None:
        return bool(row[0])
    checked = matched = 0
    details = []
    for ptype, pend, metric, value in xbrl_rows:
        if metric not in _GATE_METRICS or value is None:
            continue
        prior = con.execute(
            "SELECT value FROM fundamentals_history WHERE symbol=? AND period_type=? "
            "AND period_end=? AND metric=? AND source IS NULL", (sym, ptype, pend, metric)).fetchone()
        if prior is None or prior[0] is None:
            continue
        checked += 1
        adiff = abs(value - float(prior[0]))
        rel = adiff / max(abs(float(prior[0])), 1e-9)
        ok = rel <= _GATE_TOL or adiff <= _GATE_ABS_FLOOR_CR   # rel OR abs-floor (small-cap rounding)
        matched += ok
        if not ok:
            details.append(f"{metric}@{ptype}/{pend}: xbrl={value} screener={prior[0]} "
                           f"rel={rel:.1%} abs={adiff:.2f}cr")
    if checked == 0:
        verdict = True                      # no overlap -> nothing to contradict
        detail = "no Screener overlap (auto-pass)"
    else:
        verdict = matched == checked
        detail = f"ok ({checked} rows)" if verdict else "; ".join(details[:4])
    con.execute("INSERT OR REPLACE INTO fundamentals_xbrl_gate VALUES (?,datetime('now'),?,?)",
                (sym, int(verdict), detail))
    if not verdict:
        log.warning("continuity gate FAIL %s: %s", sym, detail)
    return verdict


def write_rows(filing: dict, metrics: dict, *, research_db: str = RESEARCH_DB,
               overwrite_screener: bool = False, min_period_end: Optional[str] = None) -> int:
    """Upsert one filing's metric rows + observe real PIT. Returns rows written.

    Forward-only default: a Screener-era row (source IS NULL) is left untouched; only
    absent keys and prior XBRL rows (restatements — last filed wins) are written.
    A restatement (an XBRL-era value changing, or a listing-flagged Revised filing) is
    journaled into fundamentals_restatements for the kill-switch-#4 spike check.
    ``min_period_end`` (Phase-3 backfill) is a hard floor: a filing whose period_end is
    before it is skipped entirely, so the pre-window Screener tail is never touched.
    """
    ptype = "A" if filing["period"] == "Annual" else "Q"
    pend = filing["to_date"]
    sym = filing["symbol"]
    src = SOURCE_CONSO if filing["consolidated"] else SOURCE_SA
    rdate = (filing["broadcast"] or "")[:10] or None
    if not metrics or not rdate:
        return 0
    if min_period_end and pend < min_period_end:
        return 0     # Phase-3 backfill period floor — pre-window periods stay frozen Screener
    con = sqlite3.connect(research_db)
    _ensure_source_column(con)
    n = 0
    n_restated = 0
    for metric, value in metrics.items():
        cur = con.execute(
            "SELECT source, value FROM fundamentals_history WHERE symbol=? AND period_type=? "
            "AND period_end=? AND metric=?", (sym, ptype, pend, metric)).fetchone()
        if cur is not None and cur[0] is None and not overwrite_screener:
            continue                     # never silently replace a Screener-era value
        if (cur is not None and cur[0] is not None and cur[1] is not None
                and value is not None and abs(float(cur[1]) - float(value)) > 1e-9):
            n_restated += 1              # an XBRL-era value changing = a restatement
        con.execute(
            "INSERT OR REPLACE INTO fundamentals_history"
            "(symbol,period_type,period_end,report_date,metric,value,source) "
            "VALUES (?,?,?,?,?,?,?)", (sym, ptype, pend, rdate, metric, value, src))
        n += 1
    if n_restated or filing.get("revised"):
        con.execute(
            "INSERT OR REPLACE INTO fundamentals_restatements"
            "(symbol,period_type,period_end,broadcast,n_changed,listed_revised) "
            "VALUES (?,?,?,?,?,?)",
            (sym, ptype, pend, filing["broadcast"], n_restated,
             int(bool(filing.get("revised")))))
    con.commit()
    con.close()
    if n:
        # real exchange broadcast = knowable_at (earliest preserved on restatement)
        provenance.observe("fundamentals_history", provenance.period_key(sym, ptype, pend),
                           symbol=sym, knowable_at=filing["broadcast"],
                           source_note=f"NSE-XBRL results API ({src})")
    return n


def _prefer_consolidated(filings: list) -> list:
    """Keep one filing per (symbol, period, to_date): consolidated wins over standalone;
    within the same nature, the latest broadcast wins (restatement = last filed)."""
    best: dict = {}
    for f in filings:
        k = (f["symbol"], f["period"], f["to_date"])
        cur = best.get(k)
        if cur is None or (f["consolidated"], f["broadcast"] or "") > (cur["consolidated"], cur["broadcast"] or ""):
            best[k] = f
    return list(best.values())


def ingest(*, since: str, until: Optional[str] = None, symbols: Optional[list] = None,
           research_db: str = RESEARCH_DB, overwrite_screener: bool = False,
           min_period_end: Optional[str] = None) -> dict:
    """Forward ingest: NSE result filings broadcast in [since, until] -> fundamentals_history.

    ``min_period_end`` floors writes at a period_end (Phase-3 backfill: keep the pre-window
    Screener tail frozen); None (the forward default) writes every in-window period.
    """
    until = until or date.today().isoformat()
    session, headers = _nse_session()
    filings: list = []
    for period in ("Quarterly", "Annual"):
        if symbols:
            # the NSE API returns 0 rows when symbol AND a date range are combined
            # (verified 2026-07-02) — fetch the symbol's full list, filter client-side.
            for s in symbols:
                filings += list_filings(symbol=s, period=period,
                                        session=session, headers=headers)
                time.sleep(REQUEST_PAUSE)
        else:
            filings += list_filings(period=period, from_date=since, to_date=until,
                                    session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
    # window on the BROADCAST date (the knowable_at clock), both paths uniformly
    filings = [f for f in filings
               if f["broadcast"] and since <= f["broadcast"][:10] <= until]

    n_bank = sum(1 for f in filings if f["bank"])
    # cumulative H1/9M rows only exist in the Quarterly listing; Annual FY figures are
    # cumulative by definition (we select the FY-span context), so never drop those.
    n_cum = sum(1 for f in filings if f["cumulative"] and f["period"] != "Annual")
    # banks are NOT filtered any more (Phase-2 bank mapper; detection is tag-based
    # inside extract_for — the listing's bank flag is unreliable: HDFCBANK carries "N")
    work = _prefer_consolidated(
        [f for f in filings if not (f["cumulative"] and f["period"] != "Annual")])
    log.info("ingest window %s..%s: %d filings (%d bank-flagged, now mapped), "
             "%d cumulative skipped, %d to parse", since, until, len(filings), n_bank, n_cum, len(work))

    stats = {"filings": len(filings), "bank_flagged": n_bank, "cumulative_skipped": n_cum,
             "parsed": 0, "rows": 0, "fetch_fail": 0, "no_metrics": 0, "gate_fail_syms": 0,
             "skipped_seen": 0, "gate_deferred": 0, "aborted_throttled": False}
    gcon = sqlite3.connect(research_db)
    _ensure_source_column(gcon)
    gcon.commit()
    gate_ok: dict = {}
    gate_budget = [GATE_BUDGET_PER_RUN]
    consec_fail = [0]

    def gated(sym: str) -> bool:
        """Cached-verdict lookup with a per-run budget on UNCACHED evidence fetches
        (~8 paced requests each): past the budget, first-seen symbols defer to the
        next nightly run instead of blowing up a heavy results-season night."""
        if sym in gate_ok:
            return gate_ok[sym]
        row = gcon.execute("SELECT pass FROM fundamentals_xbrl_gate WHERE symbol=?",
                           (sym,)).fetchone()
        if row is None:
            if gate_budget[0] <= 0:
                stats["gate_deferred"] += 1
                gate_ok[sym] = False          # this run only; nothing cached
                return False
            gate_budget[0] -= 1
        gate_ok[sym] = _gate_symbol(gcon, sym, session=session, headers=headers)
        if not gate_ok[sym]:
            stats["gate_fail_syms"] += 1
        return gate_ok[sym]

    def throttled_fetch(url: str):
        """fetch_instance + consecutive-failure circuit breaker (nsearchives throttles
        after ~1.5k fetches — observed 2026-07-02; abort cleanly, resume is cheap)."""
        xml = fetch_instance(url, session=session, headers=headers)
        time.sleep(REQUEST_PAUSE)
        if xml is None:
            stats["fetch_fail"] += 1
            consec_fail[0] += 1
            if consec_fail[0] >= 6:
                log.warning("xbrl: %d consecutive fetch failures — throttled; aborting "
                            "cleanly (seen-table resumes next run)", consec_fail[0])
                stats["aborted_throttled"] = True
            else:
                time.sleep(REQUEST_PAUSE + 5 * consec_fail[0])   # gentle backoff
            return None
        consec_fail[0] = 0
        return xml

    def mark_seen(url: str) -> None:
        gcon.execute("INSERT OR IGNORE INTO fundamentals_xbrl_seen (xml_url) VALUES (?)", (url,))
        gcon.commit()

    for f in sorted(work, key=lambda x: (x["symbol"], x["to_date"])):
        if stats["aborted_throttled"]:
            break
        sym = f["symbol"]
        if not gated(sym):
            continue
        if gcon.execute("SELECT 1 FROM fundamentals_xbrl_seen WHERE xml_url=?",
                        (f["xbrl_url"],)).fetchone():
            stats["skipped_seen"] += 1
            continue
        xml = throttled_fetch(f["xbrl_url"])
        if xml is None:
            continue
        try:
            parsed = parse_instance(xml)
            metrics = extract_metrics(parsed, f)
        except ET.ParseError as e:
            log.warning("parse failed %s %s: %s", sym, f["to_date"], e)
            stats["no_metrics"] += 1
            continue
        if not metrics:
            stats["no_metrics"] += 1
            log.warning("no metrics extracted: %s %s %s (fail-loud, not zero-filled)",
                        sym, f["period"], f["to_date"])
            mark_seen(f["xbrl_url"])          # deterministic outcome; refetch won't change it
            continue
        stats["parsed"] += 1
        stats["rows"] += write_rows(f, metrics, research_db=research_db,
                                    overwrite_screener=overwrite_screener,
                                    min_period_end=min_period_end)
        mark_seen(f["xbrl_url"])

    # ── Integrated-Filing era (broadcast Apr-2025 →): parse-first-classify ──────
    if symbols:
        if_rows = []
        for s in symbols:
            if_rows += list_integrated_filings(symbol=s, session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
    else:
        if_rows = list_integrated_filings(from_date=since, to_date=until,
                                          session=session, headers=headers)
        time.sleep(REQUEST_PAUSE)
    if_rows = [r for r in if_rows
               if r["broadcast"] and since <= r["broadcast"][:10] <= until]
    stats["if_filings"] = len(if_rows)
    log.info("integrated-filing rows in window: %d", len(if_rows))

    candidates: dict = {}          # (sym, ptype, pend) -> best (conso, broadcast) filing
    if_parsed_urls: list = []      # marked seen only AFTER the candidate flush writes
    for row in if_rows:
        if stats["aborted_throttled"]:
            break
        sym = row["symbol"]
        if not gated(sym):
            continue
        if gcon.execute("SELECT 1 FROM fundamentals_xbrl_seen WHERE xml_url=?",
                        (row["xbrl_url"],)).fetchone():
            stats["skipped_seen"] += 1
            continue
        xml = throttled_fetch(row["xbrl_url"])
        if xml is None:
            continue
        try:
            parsed = parse_instance(xml)
        except ET.ParseError as e:
            log.warning("parse failed %s %s: %s", sym, row["qe_date"], e)
            stats["no_metrics"] += 1
            continue
        if_parsed_urls.append(row["xbrl_url"])
        meta = parsed["meta"]
        end = (meta.get("DateOfEndOfReportingPeriod") or row["qe_date"] or "")[:10]
        if not end:
            stats["no_metrics"] += 1
            continue
        conso = (meta.get("NatureOfReportStandaloneConsolidated") or "").lower() == "consolidated"
        fy_end = (meta.get("DateOfEndOfFinancialYear") or "")[:10]
        jobs = [("Q", end)]
        if end == fy_end and "FourD" in parsed["contexts"]:
            jobs.append(("A", end))    # the Q4 integrated filing carries the audited FY column
        for kind, pend in jobs:
            metrics = extract_for(parsed, kind=kind, end=pend)
            if not metrics:
                stats["no_metrics"] += 1
                log.warning("no metrics extracted: %s IF/%s %s (bank/NBFC taxonomy or "
                            "nonstandard contexts — fail-loud)", sym, kind, pend)
                continue
            key = (sym, kind, pend)
            cand = {"symbol": sym, "period": "Annual" if kind == "A" else "Quarterly",
                    "to_date": pend, "consolidated": conso, "broadcast": row["broadcast"],
                    "revised": row["revised"], "metrics": metrics}
            cur = candidates.get(key)
            if cur is None or (conso, row["broadcast"] or "") > (cur["consolidated"], cur["broadcast"] or ""):
                candidates[key] = cand
    for cand in candidates.values():
        stats["parsed"] += 1
        stats["rows"] += write_rows(cand, cand["metrics"], research_db=research_db,
                                    overwrite_screener=overwrite_screener,
                                    min_period_end=min_period_end)
    for url in if_parsed_urls:      # flush done — now cheap-skip these next run
        mark_seen(url)
    gcon.close()
    log.info("ingest done: %s", stats)
    return stats


def _gate_symbol(con: sqlite3.Connection, sym: str, *, session, headers) -> bool:
    """Cached continuity verdict; on first sight, fetch the symbol's recent HISTORICAL
    filings to build the Screener-overlap evidence (new-window filings have no
    Screener-era counterpart, so the window itself can't prove continuity)."""
    row = con.execute("SELECT pass FROM fundamentals_xbrl_gate WHERE symbol=?", (sym,)).fetchone()
    if row is not None:
        return bool(row[0])
    evidence: list = []
    try:
        filings: list = []
        for period in ("Quarterly", "Annual"):
            filings += list_filings(symbol=sym, period=period, session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
        hist = _prefer_consolidated(
            [f for f in filings if not (f["cumulative"] and f["period"] != "Annual")])
        hist = sorted(hist, key=lambda x: x["to_date"], reverse=True)[:6]
        for f in hist:
            xml = fetch_instance(f["xbrl_url"], session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
            if xml is None:
                continue
            try:
                metrics = extract_metrics(parse_instance(xml), f)
            except ET.ParseError:
                continue
            ptype = "A" if f["period"] == "Annual" else "Q"
            evidence += [(ptype, f["to_date"], m, v) for m, v in metrics.items()]
    except requests.RequestException as e:
        log.warning("gate evidence fetch failed for %s (%s) — deferring, no cache", sym, e)
        return False
    verdict = _continuity_gate(con, sym, evidence)
    con.commit()
    return verdict


# ── historical backfill (Phase 3) ─────────────────────────────────────────────
# Orchestrator for docs/fundamentals-xbrl-phase3-backfill.md: walk the universe
# symbol-by-symbol, replacing Screener-era rows (source IS NULL) in the >= window_start
# window with primary-source XBRL — for gate-PASSING symbols only. Reuses ingest() per
# symbol, so it inherits the per-symbol continuity gate (fail = skipped, never
# overwritten), the throttle circuit-breaker, and the url-keyed seen-table (restart is
# cheap). A per-symbol progress ledger makes the whole run resumable across the bounded
# nightly windows the cadence calls for. The pre-window tail (< window_start) stays FROZEN
# Screener via the write_rows period floor — machine-enforcing the "no NSE XBRL that far
# back" decision (Ramana, 2026-07-14).
BACKFILL_WINDOW_START = os.environ.get("HERMES_XBRL_BACKFILL_WINDOW", "2018-01-01")
BACKFILL_SINCE = os.environ.get("HERMES_XBRL_BACKFILL_SINCE", BACKFILL_WINDOW_START)
_BACKFILL_TERMINAL = ("done", "gate_fail")


def _ensure_backfill_ledger(con: sqlite3.Connection) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS fundamentals_xbrl_backfill_progress(
        symbol TEXT PRIMARY KEY, status TEXT NOT NULL, tier INTEGER,
        rows_written INTEGER DEFAULT 0, gate_pass INTEGER,
        last_run TEXT NOT NULL DEFAULT (datetime('now')), detail TEXT)""")


def _backfill_worklist(con: sqlite3.Connection, *, window_start: str, hermes_db: str) -> list:
    """Ordered (symbol, tier) over the addressable window. Tier 1 = NSE-indexed (what the
    site / scoring / Pat surface) first, then Tier 2, alphabetical within tier."""
    addr = [r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM fundamentals_history "
        "WHERE source IS NULL AND period_end>=? ORDER BY symbol", (window_start,))]
    universe: set = set()
    try:
        h = sqlite3.connect(f"file:{hermes_db}?mode=ro", uri=True)
        universe = {r[0] for r in h.execute("SELECT DISTINCT symbol FROM stock_index_membership")}
        h.close()
    except sqlite3.Error as e:      # universe is an ordering nicety, not a hard dependency
        log.warning("backfill worklist: universe read failed (%s) — treating all as tier 2", e)
    tiered = [(s, 1 if s in universe else 2) for s in addr]
    tiered.sort(key=lambda x: (x[1], x[0]))
    return tiered


def _record_backfill(con: sqlite3.Connection, sym: str, status: str, tier: int,
                     rows: int, gate_pass: Optional[int], detail: str) -> None:
    con.execute(
        "INSERT INTO fundamentals_xbrl_backfill_progress"
        "(symbol,status,tier,rows_written,gate_pass,last_run,detail) "
        "VALUES (?,?,?,?,?,datetime('now'),?) "
        "ON CONFLICT(symbol) DO UPDATE SET status=excluded.status, tier=excluded.tier, "
        "rows_written=fundamentals_xbrl_backfill_progress.rows_written+excluded.rows_written, "
        "gate_pass=excluded.gate_pass, last_run=datetime('now'), detail=excluded.detail",
        (sym, status, tier, rows, gate_pass, detail))
    con.commit()


def backfill(*, limit: Optional[int] = None, tier: Optional[int] = None,
             research_db: str = RESEARCH_DB, hermes_db: str = HERMES_DB,
             since: str = BACKFILL_SINCE, window_start: str = BACKFILL_WINDOW_START) -> dict:
    """One bounded, resumable backfill pass. Processes up to `limit` not-yet-terminal
    addressable symbols (Tier 1 first), gate-guarded overwrite via ingest(), with the
    pre-window period floor. Stops cleanly the moment NSE throttles; resume = run again
    (the seen-table + ledger converge). Terminal statuses (done / gate_fail) are not
    re-attempted; partial / error are retried next pass."""
    con = sqlite3.connect(research_db)
    _ensure_source_column(con)
    _ensure_backfill_ledger(con)
    con.commit()
    status_of = {r[0]: r[1] for r in con.execute(
        "SELECT symbol, status FROM fundamentals_xbrl_backfill_progress")}
    worklist = _backfill_worklist(con, window_start=window_start, hermes_db=hermes_db)
    pending = [(s, t) for (s, t) in worklist
               if (not tier or t == tier) and status_of.get(s) not in _BACKFILL_TERMINAL]
    if limit:
        pending = pending[:limit]

    stats = {"attempted": 0, "done": 0, "gate_fail": 0, "partial": 0, "error": 0,
             "rows": 0, "aborted_throttled": False}
    for sym, t in pending:
        stats["attempted"] += 1
        try:
            r = ingest(symbols=[sym], since=since, until=None, overwrite_screener=True,
                       research_db=research_db, min_period_end=window_start)
        except Exception as e:            # noqa: BLE001 — one symbol must never abort the batch
            log.warning("backfill %s errored: %s", sym, e)
            _record_backfill(con, sym, "error", t, 0, None, str(e)[:180])
            stats["error"] += 1
            continue
        rows = int(r.get("rows", 0))
        stats["rows"] += rows
        g = con.execute("SELECT pass FROM fundamentals_xbrl_gate WHERE symbol=?", (sym,)).fetchone()
        gate_pass = None if g is None else int(g[0])
        if r.get("aborted_throttled"):
            _record_backfill(con, sym, "partial", t, rows, gate_pass,
                             "throttled mid-symbol — resume next window")
            stats["partial"] += 1
            stats["aborted_throttled"] = True
            log.warning("backfill: NSE throttled on %s — stopping pass cleanly (resume next run)", sym)
            break
        if gate_pass == 0:
            _record_backfill(con, sym, "gate_fail", t, rows, gate_pass,
                             "continuity gate FAIL — stays on frozen Screener series")
            stats["gate_fail"] += 1
        else:
            _record_backfill(con, sym, "done", t, rows, gate_pass, "ok")
            stats["done"] += 1

    final = {r[0]: r[1] for r in con.execute(
        "SELECT symbol, status FROM fundamentals_xbrl_backfill_progress")}
    stats["queue_remaining"] = sum(
        1 for s, t in worklist
        if (not tier or t == tier) and final.get(s) not in _BACKFILL_TERMINAL)
    con.close()
    log.info("backfill pass: %s", stats)
    return stats


def backfill_status(*, research_db: str = RESEARCH_DB, window_start: str = BACKFILL_WINDOW_START,
                    hermes_db: str = HERMES_DB) -> dict:
    """Read-only progress report over the backfill ledger + the addressable universe."""
    from collections import Counter
    con = sqlite3.connect(f"file:{research_db}?mode=ro", uri=True)
    addr = [r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM fundamentals_history WHERE source IS NULL AND period_end>=?",
        (window_start,))]
    has_ledger = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='fundamentals_xbrl_backfill_progress'").fetchone() is not None
    ledger, rows_migrated = {}, 0
    if has_ledger:
        for r in con.execute(
                "SELECT symbol,status,rows_written FROM fundamentals_xbrl_backfill_progress"):
            ledger[r[0]] = r[1]
            rows_migrated += (r[2] or 0)
    con.close()
    allsyms = set(addr) | set(ledger)          # count 'done' symbols even after they drop from addr
    counts = Counter(ledger.get(s, "pending") for s in allsyms)
    print(f"\n=== Phase-3 backfill status (window >= {window_start}) ===")
    print(f"addressable + migrated symbols: {len(allsyms)}")
    for k in ("done", "gate_fail", "partial", "error", "pending"):
        print(f"  {k:10s}: {counts.get(k, 0)}")
    print(f"rows migrated (ledger tally) : {rows_migrated}")
    return dict(counts)


# ── reconciliation (the §4 validation-gate evidence; read-only) ───────────────
_CORE = ("Sales", "Net Profit", "Operating Profit", "EPS in Rs",
         "Revenue", "Financing Profit")            # last two: bank format
_DERIVED = ("ROCE %", "OPM %", "Financing Margin %")


def reconcile(symbols: list, *, research_db: str = RESEARCH_DB, periods: int = 4) -> dict:
    """Compare XBRL-derived values against existing Screener-era rows (same symbol,
    period_type, period_end, metric). Prints per-metric within-tolerance rates —
    the gate is >=99% within 1% (core P&L) and >=97% within 2% (derived ratios)."""
    session, headers = _nse_session()
    con = sqlite3.connect(research_db)
    _ensure_source_column(con)
    con.commit()
    results: dict = {m: [] for m in _CORE + _DERIVED}
    for sym in symbols:
        filings = []
        for period in ("Quarterly", "Annual"):
            filings += list_filings(symbol=sym, period=period, session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
        work = _prefer_consolidated(
            [f for f in filings if not (f["cumulative"] and f["period"] != "Annual")])
        work = sorted(work, key=lambda x: x["to_date"], reverse=True)[:periods]
        for f in work:
            xml = fetch_instance(f["xbrl_url"], session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
            if xml is None:
                continue
            try:
                metrics = extract_metrics(parse_instance(xml), f)
            except ET.ParseError:
                continue
            ptype = "A" if f["period"] == "Annual" else "Q"
            for metric, xv in metrics.items():
                if metric not in results:
                    continue
                row = con.execute(
                    "SELECT value FROM fundamentals_history WHERE symbol=? AND period_type=? "
                    "AND period_end=? AND metric=? AND source IS NULL",
                    (sym, ptype, f["to_date"], metric)).fetchone()
                if row is None or row[0] is None:
                    continue
                sv = float(row[0])
                denom = max(abs(sv), 1e-9)
                results[metric].append(
                    {"symbol": sym, "period_end": f["to_date"], "ptype": ptype,
                     "xbrl": xv, "screener": sv, "rel": abs(xv - sv) / denom})
    con.close()

    summary = {}
    print(f"\n=== XBRL vs Screener reconciliation ({len(symbols)} symbols, "
          f"last {periods} filings each) ===")
    for metric, rows in results.items():
        if not rows:
            print(f"{metric:18s}  no overlap rows")
            continue
        tol = 0.01 if metric in _CORE else 0.02
        ok = sum(1 for r in rows if r["rel"] <= tol)
        pct = ok / len(rows) * 100
        gate = 99.0 if metric in _CORE else 97.0
        summary[metric] = {"n": len(rows), "within_pct": round(pct, 1),
                           "tol": tol, "gate": gate, "pass": pct >= gate}
        print(f"{metric:18s}  n={len(rows):3d}  within {tol:.0%}: {pct:5.1f}%  "
              f"(gate {gate:.0f}%) {'PASS' if pct >= gate else 'FAIL'}")
        worst = sorted(rows, key=lambda r: -r["rel"])[:3]
        for w in worst:
            if w["rel"] > tol:
                print(f"    worst: {w['symbol']} {w['ptype']} {w['period_end']} "
                      f"xbrl={w['xbrl']} screener={w['screener']} rel={w['rel']:.1%}")
    return summary


# ── selftest (synthetic, no DB, no network) ───────────────────────────────────
def _selftest() -> int:
    """Bank-mapper identity check against the REAL HDFCBANK 2026-03-31 consolidated
    filing values. Rupee core matches Screener exactly: Revenue 87182.5 /
    Expenses 44027.87 / Financing Profit -2065.81. PBT/NP are as-filed INCLUDING
    ExceptionalItems (26948.17 / 20350.76): this specific filing stuffed minority
    interest into ExceptionalItems (its own note admits it), so its NP diverges
    from Screener's curated 21074 — the continuity gate is DESIGNED to fail such
    filings rather than guess. Genuine exceptionals (SBIN Q3-FY24 pension) require
    inclusion to reconcile at all. Annual kind must return {} (quarterly-only),
    and a non-bank instance must not dispatch to the bank path.
    """
    ctx = ('<context id="OneD"><entity><identifier scheme="s">x</identifier></entity>'
           '<period><startDate>2026-01-01</startDate><endDate>2026-03-31</endDate>'
           '</period></context>')

    def fact(name, v):
        return f'<{name} contextRef="OneD" unitRef="INR" decimals="2">{v}</{name}>'

    bank_xml = ('<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' + ctx
                + fact("InterestEarned", 871825000000)
                + fact("OtherIncome", 297374400000)
                + fact("InterestExpended", 452204400000)
                + fact("OperatingExpenses", 405878200000)
                + fact("ProvisionsOtherThanTaxAndContingencies", 34400500000)
                + fact("OperatingProfitBeforeProvisionAndContingencies", 311116800000)
                + fact("ExceptionalItems", -7234600000)          # MI quirk — must not leak
                + fact("ProfitLossFromOrdinaryActivitiesBeforeTax", 269481700000)
                + fact("TaxExpense", 65974100000)
                + fact("ShareOfProfitLossOfAssociates", 0)
                + fact("ProfitLossForThePeriod", 203507600000)
                + fact("BasicEarningsPerShareAfterExtraordinaryItems", 13.22)
                + fact("PaidUpValueOfEquityShareCapital", 15393400000)
                + '</xbrl>')
    parsed = parse_instance(bank_xml)
    assert _is_bank_instance(parsed), "bank detection failed"
    m = extract_bank_for(parsed, kind="Q", end="2026-03-31")
    exp = {"Revenue": 87182.5, "Interest": 45220.44, "Other Income": 29737.44,
           "Expenses": 44027.87, "Financing Profit": -2065.81, "Provisions": 3440.05,
           "Profit before tax": 26948.17, "Net Profit": 20350.76,
           "Financing Margin %": -2.37, "EPS in Rs": 13.22, "Equity Capital": 1539.34}
    for k, v in exp.items():
        assert abs(m.get(k, 1e18) - v) < 0.02, f"{k}: got {m.get(k)} want {v}"
    # dispatch: extract_for must route bank instances to the bank extractor
    assert extract_for(parsed, kind="Q", end="2026-03-31") == m, "dispatch failed"
    # bank annual rows are Phase-3 territory (annual-report depreciation split)
    assert extract_bank_for(parsed, kind="A", end="2026-03-31") == {}, "bank annual not skipped"

    nonbank_xml = ('<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' + ctx
                   + fact("RevenueFromOperations", 100000000)
                   + fact("ProfitBeforeTax", 20000000)
                   + fact("FinanceCosts", 1000000)
                   + fact("DepreciationDepletionAndAmortisationExpense", 2000000)
                   + fact("ProfitLossForPeriod", 15000000)
                   + '</xbrl>')
    p2 = parse_instance(nonbank_xml)
    assert not _is_bank_instance(p2), "non-bank misdetected as bank"
    m2 = extract_for(p2, kind="Q", end="2026-03-31")
    assert m2.get("Sales") == 10.0 and m2.get("Net Profit") == 1.5, m2
    # zero-filled bank column -> {}
    zero_xml = ('<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' + ctx
                + fact("InterestEarned", 0) + fact("InterestExpended", 0)
                + fact("TaxExpense", 0) + fact("ProfitLossForThePeriod", 0) + '</xbrl>')
    assert extract_for(parse_instance(zero_xml), kind="Q", end="2026-03-31") == {}

    # revision ledger: re-writing a period with a CHANGED value (or a listing-flagged
    # Revised filing) must journal exactly one fundamentals_restatements row per filing;
    # an identical re-write (resume/backfill) must journal nothing.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rdb = os.path.join(td, "research.db")
        tcon = sqlite3.connect(rdb)
        tcon.execute("CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, "
                     "period_end TEXT, report_date TEXT, metric TEXT, value REAL, "
                     "PRIMARY KEY(symbol,period_type,period_end,metric))")
        tcon.commit()
        tcon.close()
        _observe = provenance.observe
        provenance.observe = lambda *a, **k: None      # keep the selftest off the live DB
        try:
            f0 = {"symbol": "TEST", "period": "Quarterly", "to_date": "2026-03-31",
                  "consolidated": True, "broadcast": "2026-04-20T18:00:00"}
            write_rows(f0, {"Sales": 100.0}, research_db=rdb)                 # original
            write_rows(f0, {"Sales": 100.0}, research_db=rdb)                 # idempotent re-run
            write_rows(dict(f0, broadcast="2026-05-05T10:00:00", revised=True),
                       {"Sales": 101.0}, research_db=rdb)                     # the restatement
        finally:
            provenance.observe = _observe
        tcon = sqlite3.connect(rdb)
        ev = tcon.execute("SELECT broadcast, n_changed, listed_revised "
                          "FROM fundamentals_restatements").fetchall()
        tcon.close()
        assert ev == [("2026-05-05T10:00:00", 1, 1)], f"ledger wrong: {ev}"

    # Phase-3 backfill period floor: min_period_end skips pre-window periods (frozen tail)
    # and writes in-window ones — the machine guard behind the "pre-2018 stays Screener" call.
    with tempfile.TemporaryDirectory() as td:
        rdb = os.path.join(td, "research.db")
        tcon = sqlite3.connect(rdb)
        tcon.execute("CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, "
                     "period_end TEXT, report_date TEXT, metric TEXT, value REAL, "
                     "PRIMARY KEY(symbol,period_type,period_end,metric))")
        tcon.commit()
        tcon.close()
        _observe = provenance.observe
        provenance.observe = lambda *a, **k: None
        try:
            pre = {"symbol": "T", "period": "Quarterly", "to_date": "2017-12-31",
                   "consolidated": True, "broadcast": "2018-02-10T18:00:00"}
            inw = {"symbol": "T", "period": "Quarterly", "to_date": "2018-03-31",
                   "consolidated": True, "broadcast": "2018-05-10T18:00:00"}
            assert write_rows(pre, {"Sales": 10.0}, research_db=rdb, min_period_end="2018-01-01") == 0
            assert write_rows(inw, {"Sales": 11.0}, research_db=rdb, min_period_end="2018-01-01") == 1
        finally:
            provenance.observe = _observe
        tcon = sqlite3.connect(rdb)
        got = tcon.execute("SELECT period_end, value FROM fundamentals_history").fetchall()
        tcon.close()
        assert got == [("2018-03-31", 11.0)], f"period floor wrong: {got}"

    print("selftest OK  bank mapper (HDFCBANK 2026-03-31 identity + quirk guard) "
          "+ dispatch + non-bank + zero-guard + revision ledger + backfill period floor")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", metavar="SYMBOL", help="parse the latest filings for one symbol and print metrics")
    ap.add_argument("--ingest", action="store_true", help="forward ingest into fundamentals_history")
    ap.add_argument("--reconcile", action="store_true", help="compare XBRL vs Screener overlap (read-only gate evidence)")
    ap.add_argument("--since", default=(date.today() - timedelta(days=7)).isoformat())
    ap.add_argument("--until", default=None)
    ap.add_argument("--symbols", default=None, help="comma-separated NSE symbols (default: global window)")
    ap.add_argument("--periods", type=int, default=4, help="filings per symbol for --reconcile")
    ap.add_argument("--db", default=RESEARCH_DB, help="research.db path override")
    ap.add_argument("--overwrite-screener", action="store_true",
                    help="allow XBRL rows to replace Screener-era rows (off by default)")
    ap.add_argument("--regate", action="store_true",
                    help="drop cached continuity-gate verdicts for --symbols and re-arbitrate "
                         "now (use after a mapper change; e.g. banks gated pre-bank-mapper)")
    ap.add_argument("--backfill", action="store_true",
                    help="Phase-3 historical backfill: one bounded, resumable pass (gate-guarded "
                         "overwrite of Screener rows in the >= --window-start window)")
    ap.add_argument("--backfill-status", action="store_true",
                    help="print Phase-3 backfill ledger progress (read-only)")
    ap.add_argument("--limit", type=int, default=None, help="max symbols per --backfill pass")
    ap.add_argument("--tier", type=int, default=None, choices=(1, 2),
                    help="restrict --backfill to tier 1 (NSE-indexed) or tier 2 (the rest)")
    ap.add_argument("--window-start", default=BACKFILL_WINDOW_START,
                    help="backfill period-end floor; periods before it stay frozen Screener")
    ap.add_argument("--hermes-db", default=HERMES_DB, help="hermes.db path (universe for tiering)")
    ap.add_argument("--selftest", action="store_true",
                    help="synthetic bank-mapper + dispatch checks (no DB, no network)")
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else None

    if args.selftest:
        raise SystemExit(_selftest())
    if args.regate:
        if not syms:
            ap.error("--regate needs --symbols")
        session, headers = _nse_session()
        con = sqlite3.connect(args.db)
        _ensure_source_column(con)
        for sym in syms:
            con.execute("DELETE FROM fundamentals_xbrl_gate WHERE symbol=?", (sym,))
            con.commit()
            verdict = _gate_symbol(con, sym, session=session, headers=headers)
            detail = con.execute("SELECT detail FROM fundamentals_xbrl_gate WHERE symbol=?",
                                 (sym,)).fetchone()
            print(f"{sym}: {'PASS' if verdict else 'FAIL'} — {detail[0] if detail else 'no verdict cached (evidence fetch failed)'}")
        con.close()
    elif args.probe:
        session, headers = _nse_session()
        for period in ("Quarterly", "Annual"):
            filings = list_filings(symbol=args.probe.upper(), period=period,
                                   session=session, headers=headers)
            time.sleep(REQUEST_PAUSE)
            for f in _prefer_consolidated(
                    [f for f in filings
                     if not (f["cumulative"] and f["period"] != "Annual")])[:2]:
                xml = fetch_instance(f["xbrl_url"], session=session, headers=headers)
                if xml is None:
                    continue
                metrics = extract_metrics(parse_instance(xml), f)
                nature = "CONSO" if f["consolidated"] else "SA"
                print(f"\n{f['symbol']} {f['period']} {f['to_date']} [{nature}] "
                      f"broadcast={f['broadcast']} bank={f['bank']}")
                for k, v in sorted(metrics.items()):
                    print(f"  {k:18s} {v}")
    elif args.reconcile:
        if not syms:
            ap.error("--reconcile needs --symbols")
        reconcile(syms, research_db=args.db, periods=args.periods)
    elif args.backfill_status:
        backfill_status(research_db=args.db, window_start=args.window_start, hermes_db=args.hermes_db)
    elif args.backfill:
        backfill(limit=args.limit, tier=args.tier, research_db=args.db, hermes_db=args.hermes_db,
                 window_start=args.window_start, since=args.window_start)
    elif args.ingest:
        ingest(since=args.since, until=args.until, symbols=syms,
               research_db=args.db, overwrite_screener=args.overwrite_screener)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
