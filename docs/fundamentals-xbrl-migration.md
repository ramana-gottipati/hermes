# Fundamentals migration: Screener.in → NSE XBRL (Guardrail #8)

**Status:** Phase-1 LIVE (forward-only, gated) — 2026-07-02.
**Module:** `src/automation/fundamentals_xbrl.py` · nightly `hermes-fundamentals-xbrl.timer` (16:30 UTC).
**Gate memo:** the joint risk-governance + data-product panel verdict (2026-07-02) that shaped this
design; its rules are restated inline below.

---

## Why

Guardrail #8: primary sources only. `screener.py` → `fundamentals`/`fundamentals_history` was the
one Screener.in dependency (powers C capital-allocation + patearn scoring). This migration replaces
it for NEW periods with SEBI-mandated XBRL results filings fetched from NSE — an authentic primary
source with a per-filing exchange broadcast timestamp (true PIT).

## Source layout (verified live, 2026-07-02)

Two NSE APIs, split by the **Apr-2025 SEBI Integrated-Filing regime change**:

| Era | API | Coverage | Notes |
|---|---|---|---|
| ≤ Apr-2025 (+ late old-period filers) | `/api/corporates-financial-results` | RELIANCE: 53 quarterly filings back to 2018; Annual listings separate | rich flags: `consolidated`, `cumulative`, `bank`, `audited`, `broadCastDate`, direct `xbrl` URL. **Quirk: symbol + date-range combined returns 0 rows** — symbol-scoped calls fetch all, filter client-side. Date-window filtering is by BROADCAST date and needs an explicit `period` param. |
| ≥ Apr-2025 | `/api/integrated-filing-results` | thin listing: `qe_Date`, `broadcast_Date`, `revised_Date`, `xbrl` URL | **no period bounds / consolidated / bank flags** → parse-first-classify: the XBRL instance's own meta tags (`NatureOfReportStandaloneConsolidated`, `DateOfEndOfReportingPeriod`, `DateOfEndOfFinancialYear`) supply them. Path recovered from `/dist/js/sections/corporate-filings.js`. Financial + governance filings share the endpoint (filter `type`). |

## Instance format (shared `in-bse-fin` taxonomy)

- Facts are **absolute INR** (`unitRef="INR"`) regardless of the `LevelOfRounding` display tag →
  ÷1e7 = ₹ crores (house convention). Verified: RELIANCE FY24 Sales fact 9,144,720,000,000 =
  914,472 cr = the filed figure.
- **Context ids encode the results-table COLUMN**, not honest dates: `OneD` = current discrete
  quarter, `FourD` = year-to-date (== FY in a Q4/Annual filing), `OneI` = instant at period end.
  Filers stamp **degenerate dates** into `FourD` (RELIANCE FY24 repeats the Q4 dates), so named
  contexts are primary; date-span match is only a fallback.
- Quarterly filings carry P&L only; balance-sheet items (`OtherEquity`, `BorrowingsCurrent/
  Noncurrent`) exist in annual (H1) filings at `OneI`.
- `xsi:nil` / missing tag → NULL, never zero (panel red line). One exception, documented in
  `_borrowings()`: a filed balance sheet (`EquityAndLiabilities` present) with no borrowings tags
  is genuinely debt-free → 0.0.

## Metric mapping (non-bank; banks skipped loudly pending a Phase-2 mapper)

| fundamentals_history metric | XBRL |
|---|---|
| Sales | `RevenueFromOperations` |
| Net Profit | `ProfitLossForPeriod` (as-filed, incl. NCI) |
| Operating Profit | `ProfitBeforeExceptionalItemsAndTax + FinanceCosts + Depreciation − OtherIncome` (Screener EBITDA convention) |
| OPM % | derived OP / Sales |
| Interest / Depreciation / Other Income / Profit before tax | direct tags |
| EPS in Rs | `BasicEPS…ContinuingAndDiscontinuedOperations` (as-filed — see EPS caveat) |
| Equity Capital | `PaidUpValueOfEquityShareCapital` |
| Reserves (A only) | `OtherEquity` |
| Borrowings (A only) | `BorrowingsCurrent + BorrowingsNoncurrent` |
| ROCE % (A only) | (PBT + Interest) / (EqCap + Reserves + Borrowings); NULL if any component nil |

## PIT rules

- `knowable_at` = the exchange **broadcast datetime** (never board-meeting or period-end), via
  `provenance.observe()` → earliest sighting preserved; a restatement inserts with its own
  broadcast and the VALUE follows last-filed-wins (`INSERT OR REPLACE`), so an as-of-T backtest
  still sees what was knowable at T.
- Every row carries `source` = `NSE-XBRL-CONSO` / `NSE-XBRL-SA` (new column, NULL = Screener era).
  Consolidated preferred when both natures are filed for the same (symbol, period_end).

## Reconciliation (15-symbol cohort, last 6 filings each, 2026-07-02)

Raw agreement: Sales 81% / Net Profit 96.4% / OP 84.5% / EPS 79.8% within 1%; ROCE 21% / OPM 61%
within 2%. Every large divergence root-caused to a **definitional or restatement difference, not a
parser bug**:

- **EPS exactly 2× (RELIANCE):** Screener restates history for the Oct-2024 1:1 bonus; XBRL is
  as-filed. As-filed is the PIT-honest value; per-share series crossing a corporate action must
  not be mixed — rupee metrics are the primary consumers anyway (Guardrail #5).
- **ITC Sales +13-14%:** gross-vs-net-of-excise revenue definition.
- **ULTRACEMCO PAT +8-17%:** Screener shows post-merger restated history; XBRL as-filed-then.
- **LT OP −20%:** other-operating-income treatment in Screener's OP.
- **ROCE:** Screener uses average capital employed + its own EBIT variant → level shift.

## The series-continuity gate (the design consequence)

Appending as-filed XBRL rows to a Screener series with a different definition would corrupt every
cross-boundary CAGR downstream (C-score, patearn growth patterns). So ingest is **gated per
symbol**: before a symbol's first XBRL write, its recent historical filings are parsed and compared
to Screener-era rows on the rupee core (Sales / Net Profit / Operating Profit, 2% tolerance, all
overlapping rows must match). Verdicts are cached in `research.db.fundamentals_xbrl_gate`
(symbol, checked_at, pass, detail). No overlap at all (new listings) = auto-pass. Gate-failing
symbols stay Screener-flagged until a Phase-2 definitional mapper handles them.

This is stricter than the panel's cohort-level gate: continuity is enforced **per symbol**, so the
migrated cohort is exactly the set whose series are provably consistent.

## Phasing

1. **Phase 1 (LIVE):** forward-only nightly ingest, gated, source-tagged, parallel to the frozen
   Screener history. C consumes new XBRL periods only for gate-passed symbols.
2. **Phase 2 (LIVE 2026-07-02, bank mapper):** see § Phase-2 evidence below. Bank/NBFC results
   now extracted (Screener bank conventions, tag-based detection, quarterly-only); definitional
   mappers resolved by evidence (most dissolved); `--regate` CLI re-arbitrates cached verdicts
   after mapper changes. Still open from the Phase-2 list: shareholding-pattern filings
   (promoter/FII/DII/pledge — separate NSE filing class, own module).
3. **Phase 3:** historical backfill from the legacy API (2018+ per symbol) + BSE archive where
   deeper, replacing Screener-era rows symbol-by-symbol where reconciliation allows; then delete
   `screener.py`. Bank ANNUAL rows and the excise cohort (ITC) land here by series replacement.

## Phase-2 evidence (2026-07-02, live instances + Screener DB)

**Definitional mappers — evidence dissolved most of the list:**
- **Excise-gross Sales (ITC): NOT mappable.** The results instances carry NO excise fact — excise
  sits untagged inside `OtherExpenses`; the filing notes confirm revenue is excise-gross per
  Ind AS 115/Schedule III. Screener's net-of-excise Sales cannot be reconstructed from this feed.
  ITC stays gate-failed on the frozen Screener series until Phase-3 series replacement. (Its
  Feb-2026 excise hike makes even ITC's own series "not strictly comparable" — their words.)
- **NCI netting (LT): NOT needed.** Screener's LT consolidated Net Profit (3,974 cr, Q3-FY25)
  equals `ProfitLossForPeriod` INCLUDING non-controlling interests — exactly what Phase 1 already
  stores. Sales and the OP identity also reproduce exactly on current quarters.
- **Other-operating-income OP (LT): no current mismatch.** The Screener identity
  `PBT = OP + OtherIncome − Interest − Depreciation` reproduces to the rupee on Q3-FY25.
  The reconciliation-era −20% did not recur; the gate arbitrates live at results season.

**Bank/NBFC mapper (the real Phase-2 build) — `extract_bank_for`:**
- **Detection is TAG-based** (`InterestEarned` present), never the listing flag: HDFCBANK's own
  legacy listing rows say `bank="N"`, and integrated listings carry no flag at all.
- Mapping (validated to the rupee against Screener rows, both natures):
  `Revenue = InterestEarned` · `Interest = InterestExpended` ·
  `Expenses = OperatingExpenses + ProvisionsOtherThanTaxAndContingencies` ·
  `Financing Profit = Revenue − Interest − Expenses` ·
  `PBT = OperatingProfitBeforeProvisionAndContingencies − Provisions + ExceptionalItems` ·
  `Net Profit = PBT − TaxExpense + ShareOfProfitLossOfAssociates` (structural derivations —
  tagged PBT/PAT are unreliable: filers stuff MI into ExceptionalItems).
- **Reconcile (HDFCBANK/ICICIBANK/SBIN × 6 quarters): Revenue 100% · Financing Profit 100% ·
  Net Profit 100% for ICICIBANK+SBIN.** ExceptionalItems must be INCLUDED (SBIN's genuine
  Q3-FY24 pension provision is 61% off without it); the associates line must be added
  (SBIN/ICICIBANK ~2% short without it).
- **Gate verdicts: ICICIBANK PASS · SBIN PASS · HDFCBANK FAIL (by design)** — HDFCBANK
  chronically misfiles MI inside ExceptionalItems while tagging `ProfitLossOfMinorityInterest=0`
  (its own filing note admits the utility forced it), so its Screener-curated NP series cannot
  be continued from tags. It stays on the frozen Screener series. Honest refusal > guessing.
- **Quarterly only:** Screener's bank ANNUAL series comes from annual reports (separate
  Depreciation line absent from results-XBRL — HDFCBANK FY24 Financing Profit off by exactly
  the year's depreciation). Bank `kind="A"` returns {} loudly; Phase 3 owns bank annuals.
- Bank rupee core gated = `Revenue / Net Profit / Financing Profit` (added to `_GATE_METRICS`).
- Known non-gated divergences: bank EPS 2× for HDFCBANK (Screener restated the 2025 1:1 bonus;
  as-filed is PIT-honest — same class as RELIANCE) · `Financing Margin %` stored precise while
  Screener stores integer-rounded.

## Red lines (standing)

Never mix sources silently (the `source` column is mandatory) · never coerce nil to zero ·
never flip a consumer to XBRL for a gate-failing symbol · switch at period boundaries only.
