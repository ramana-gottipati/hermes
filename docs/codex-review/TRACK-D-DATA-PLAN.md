# Track D — Doctrine-D financials scorer: primary-source DATA PLAN

> **Lifecycle: TRANSIENT-CAMPAIGN.** The data-sourcing plan for the financial-sector patearn adaptation
> (Codex D3-F1). Decision doc for Ramana → then build. Retire once the scorer ships.

## The problem (D3-F1, verified on the VPS)
`scoring.py`'s pt14 applies **generic ROCE / D-E** thresholds to banks/NBFCs/HFCs and hard-disqualifies
`D/E > 2.0` — structurally wrong for lenders (leverage IS the business). Live proof: HDFCBANK's stored
`fundamentals` row reads `roce=1.57`, `roe=7.04`, `debt_to_equity=(empty)` — nonsense for a bank. The
score currently mis-rates every lender.

**VERIFIED LIVE (2026-07-14, S136 read-only VPS query).** Confirmed the mis-rating on the box:
HDFCBANK `roce=7.04, roe=13.8, debt_to_equity=NULL` → **NS 29.2% / tier T4**; ICICIBANK `roce=7.2` →
T4 (NS 31%); BAJFINANCE `roce=10.8` → T4 (NS 28.9%). None hard-disqualified (D/E is NULL for lenders,
so the D/E>2 gate never fires — the failure is the LOW score, not a bogus DQ). Three of India's
highest-quality franchises rendered bottom-tier because ROCE/OPM/D-E thresholds are structurally wrong
for lenders. (The earlier `roce=1.57` reading was an older snapshot; the point stands — ROCE is
nonsense-low for a bank either way.)

## What already exists (REUSE — do not rebuild)
1. **Primary XBRL pipeline is LIVE** — `fundamentals_xbrl.py` + nightly `hermes-fundamentals-xbrl.timer`
   fetches SEBI-mandated results XBRL from NSE (`in-bse-fin` taxonomy; true PIT via broadcast timestamp;
   Guardrail-#8-clean). **Confirmed: HDFCBANK has 49 quarterly XBRL filings available.**
2. **A bank-format XBRL extractor already exists** — `extract_bank_for()`, detected tag-based via
   `InterestEarned` present (NOT the listing's `bank` flag — HDFCBANK's own listing says `bank="N"`).
   It already reads **Interest earned / Interest expended** (→ NII), Financing Profit, structural PBT/PAT.
3. **A `model='financial'` capital-allocation path exists** — `capital_allocation.py` computes
   **RoE / RoA / RoE-trend / dilution / book-value growth** for lenders (`_is_financial()`), covering
   **Doctrine-D Pattern 1**. But it runs on **Screener** data and lacks the bank regulatory metrics.

## The gap (what Track D must source)
The bank **regulatory** metrics are NOT extracted or stored (no columns in `fundamentals`):

| Doctrine-D pattern | Metric needed | Primary source | Availability |
|---|---|---|---|
| 1 ROCE→RoE/RoA | RoE, RoA | XBRL analytical ratios (RoA) + equity from balance sheet (RoE) | RoA tagged in most banks' quarterly XBRL; RoE derivable |
| 2 Op-leverage | **NII** growth, **cost-to-income** | InterestEarned − InterestExpended (**already extracted**); cost-to-income derivable (opex / (NII+other income)) | HIGH (NII confirmed available) |
| 5 Balance sheet | **GNPA%, NNPA%, CAR/CRAR%** | XBRL asset-quality + analytical-ratios facts | **NEEDS EMPIRICAL CONFIRMATION** (see Step 1) — usually tagged; some filers put them in an untagged notes block |
| 5/12/13 ALM | **ALM structural-liquidity gap**, PCR | Annual report / Basel III Pillar-3 (bank IR sites / annual XBRL) | LOW in quarterly → Phase 2 or proxy |

## Recommended approach — extend the existing NSE-XBRL pipeline (NO new vendor)

**Phase 1 (primary-source, tractable):**
- **Step 1 — tag-inventory spike (the feasibility gate).** Fetch the raw XBRL *instance* for 3–5 lenders
  (bank: HDFCBANK/AXISBANK; NBFC: BAJFINANCE; HFC: e.g. LICHSGFIN) and inventory the actual tag
  local-names. Confirm whether `GrossNPA/NetNPA/PercentageOfGrossNPA/PercentageOfNetNPA`,
  `CapitalAdequacyRatio/CRAR`, `ReturnOnAssets` are TAGGED (vs sitting in an untagged notes block).
  ⚠ My quick attempt used `list_filings()` (which returns metadata, no XBRL URL) and got a stub — the
  correct path is the raw `/api/corporates-financial-results` row's `xbrl` field → `fetch_instance()`;
  wire that first. **This step decides Phase-1 scope** (tagged → parse directly; untagged → the metric
  moves to Phase 2 / notes-parsing).

### ✅ Step-1 spike DONE (2026-07-14, S136) — the feasibility gate is CLEARED for banks
Read-only spike on live NSE XBRL (HDFCBANK/AXISBANK/SBIN banks · BAJFINANCE NBFC · LICHSGFIN HFC),
Q3FY25 (period-end 2024-12-31). Correct path used: `list_filings(symbol=…)` → `xbrl_url` →
`fetch_instance()` → element-tag inventory. **Result — the tags Doctrine-D Pattern 5 needs ARE tagged
for banks, in the STANDALONE instance:**

| Metric | Tag local-name | HDFCBANK (SA) | SBIN (SA) | AXISBANK (conso) |
|---|---|--:|--:|--:|
| Gross NPA % | `PercentageOfGrossNpa` | 1.42% | 2.07% | 1.46% |
| Net NPA % | `PercentageOfNpa` | 0.46% | 0.53% | 0.35% |
| Gross NPA (₹abs) | `GrossNonPerformingAssets` | 36,018cr | 84,360cr | 15,850cr |
| Net NPA (₹abs) | `NonPerformingAssets` | 11,587cr | 21,377cr | 3,775cr |
| RoA (quarterly) | `ReturnOnAssets` | 0.47% | 1.04% | 1.64% |
| CET1 ratio | `CET1Ratio` | 19.97% | 9.52% | — |
| Add'l Tier-1 | `AdditionalTier1Ratio` | 0.00% | 1.33% | 0.39% |
| Interest earned | `InterestEarned` | ✓ | ✓ | ✓ |
| Interest expended | `InterestExpended` | ✓ | ✓ | ✓ |

**Three decisive nuances (implementation-binding):**
1. **Read the STANDALONE (SA) instance, not consolidated.** HDFCBANK's CONSOLIDATED instance reports
   `PercentageOfGrossNpa`/`ReturnOnAssets`/`GrossNonPerformingAssets` = **0.00** (prudential ratios are
   a standalone-bank concept; the conso group folds in non-bank subs). AXISBANK's conso happened to carry
   them, but HDFC's did not → **always prefer `SOURCE_SA`** for the regulatory metrics. The pipeline
   already distinguishes `SOURCE_SA`/`SOURCE_CONSO`.
2. **No total-CRAR tag in the quarterly XBRL — use CET1.** There is NO `CapitalAdequacyRatio`/`CRAR`
   total tag; only `CET1Ratio` (+ `AdditionalTier1Ratio`) are tagged. CET1 is the binding regulatory
   buffer, so **use CET1Ratio as the capital-strength metric** (optionally CET1+AT1 as a CRAR proxy).
   True total-CRAR stays a Phase-2 item (annual / Basel-III Pillar-3) if ever needed.
3. **NBFC/HFC quarterly XBRL carries P&L ONLY.** BAJFINANCE + LICHSGFIN (NBFC_INDAS taxonomy) tag
   `InterestEarned` and the Ind-AS P&L, but **NO GNPA / NNPA / CAR / RoA** at all → those move to
   **Phase 2 / proxy** for non-banks. Their Phase-1 model must lean on the P&L structure (NII, growth,
   and RoA only if total assets are tagged — a follow-up probe not yet run).

**Bottom line: Phase-1 is fully tractable for BANKS** (GNPA%, NNPA%, RoA, CET1 all tagged in SA) and
**P&L-only for NBFC/HFC** (regulatory ratios deferred to Phase-2/proxy). This ANSWERS decision-question
#3 empirically — no vendor needed. Spike scripts: session scratchpad `xbrl_tag_spike.py` /
`xbrl_sa_probe.py` (read-only, ₹0).

### The financial DETECTOR for scoring.py (decided by the spike)
The pt14 scorer consumes the flat `fundamentals` dict (no XBRL frame), so `capital_allocation._is_financial`
(which reads a Screener frame) is not directly reusable there. **Detector = NSE financial-index
membership** via `company_tags` (`source='index'`): a symbol is a lender/financial iff it carries any of
`{'Financial Services', 'Banks', 'PSU Banks', 'Private Banks'}`. Verified on the box: `'Financial
Services'` is the union tag that catches banks + NBFCs + HFCs (HDFCBANK, BAJFINANCE, LICHSGFIN all carry
it; counts: Banks 23 · Financial Services 20 · PSU Banks 12 · Private Banks 10). **Primary-source
(NSE index constituents), guardrail-#8-clean, already stored** — no fragile numeric heuristic.
*Caveat:* a lender OUTSIDE the NSE financial indices (a micro-NBFC) wouldn't be caught — acceptable for
the interim suppress-label; the full Doctrine-D build detects lenders directly via the XBRL `InterestEarned`
bank-taxonomy tag (the `extract_bank_for` path), which is complete.
- **Step 2 — extend `extract_bank_for()`** to pull the confirmed tags: GNPA%, NNPA%, CAR/CRAR%, RoA,
  cost-to-income, Advances, Deposits (NII already there).
- **Step 3 — add columns** to `fundamentals` / `fundamentals_history` (`gnpa_pct`, `nnpa_pct`, `crar`,
  `roa`, `nii_cr`, `cost_to_income`, `advances_cr`, `deposits_cr`) — nullable, XBRL-sourced, PIT.
- **Step 4 — route financials in `scoring.py`** to a Doctrine-D model (reuse the `_is_financial` /
  `InterestEarned` detector): Pattern 1 = RoE/RoA vs sub-type thresholds; Pattern 2 = NII growth +
  cost-to-income trend; Pattern 5 = GNPA<1.5% ∧ CRAR>18% (+ ALM proxy). **Disable the generic D/E hard-
  disqualifier for lenders.** Emit the required **"sector-adapted thresholds (Doctrine D)"** note on
  every surface (Telegram, stock card, Pat, Screen+) — the D3-F1 requirement.

**Phase 2 (deferred, harder):** ALM structural-liquidity gap + PCR from annual reports / Basel III
Pillar-3. Recommend **proxy ALM via CRAR + GNPA in Phase 1** (Doctrine D already treats ALM as a
Pattern-5 proxy) and defer true ALM extraction.

## Decisions for Ramana (the ask)
1. **Sub-type thresholds** — distinct **bank vs NBFC vs HFC** threshold sets (Doctrine D implies yes:
   bank RoA ~1%, NBFC RoA 2–4%, HFC RoE 12–15%), or one "financial" set? *(Recommend sub-type-aware — a
   small table, materially better fidelity.)*
2. **ALM** — proxy via CRAR+GNPA in Phase 1 and defer true ALM to Phase 2, or block on ALM now?
   *(Recommend proxy + defer.)*
3. ~~**GNPA/CAR availability**~~ **✅ RESOLVED by the Step-1 spike (2026-07-14).** GNPA%, NNPA%, RoA,
   CET1 are all TAGGED in the banks' STANDALONE quarterly XBRL (no vendor needed). Total-CRAR is not
   tagged → use CET1. NBFC/HFC regulatory ratios are NOT in quarterly XBRL → Phase 2 / proxy. No decision
   left here except to accept "banks Phase-1, NBFC/HFC P&L-only-Phase-1".
4. **Scope order** — build the **data (Steps 1–3) first, scorer (Step 4) second**, or land a Step-4
   *interim* now that simply **suppresses + labels** pt14 for financials ("sector-adapted model pending")
   so no wrong number shows while the data lands? *(Recommend the interim suppress-label immediately +
   data in parallel — stops the live mis-rating today.)* **STILL AWAITS RAMANA.**

## Interim suppress-label — SPEC'd + READY (S136); ship gated on multi-session + scope decision
The interim (decision #4) is fully designed and de-risked — mechanical to ship once unblocked:
- **Detect:** `is_financial_symbol(symbol)` → True iff `company_tags` (source='index') carries any of
  `{'Financial Services','Banks','PSU Banks','Private Banks'}` (see detector section above).
- **Suppress:** in `score_fundamentals`, when financial, return `sector_model_pending=True` +
  `sector_note` and DO NOT present the generic NS%/tier as a quality verdict (the ROCE/OPM/D-E patterns
  are structurally wrong for lenders). Emit the required **"sector-adapted thresholds (Doctrine D)
  pending"** note.
- **Surfaces:** the note must reach Telegram (`format_score_for_telegram`, in scoring.py — SAFE) + the
  stock card (`dashboard.py`) + Pat (`pat/flows.py`/`pat/web.py`) + Screen+ (`screener_plus.py`).
- ⚠ **MULTI-SESSION BLOCK (2026-07-14):** the web/Pat consumer surfaces (`dashboard.py` D80-forked,
  `screener_plus.py` reversal-lane-hot, `pat/*` Pat-lane-hot) are in active parallel sessions' hot
  zones — editing them now would collide. Only the `scoring.py` ENGINE layer (detector + flag + note +
  the in-file Telegram formatter) is safe to land this session; the web/Pat/Screen+ adoption + the VPS
  re-score defer to a coordinated session. And whether to land the interim at all vs. wait for the full
  build is decision #4 (awaits Ramana). Recommendation stands: land the engine-level interim now, adopt
  on surfaces when they free up.

## Guardrails honored
Primary sources only (NSE SEBI XBRL — no vendor/Screener to fill gaps; defer instead). PIT via broadcast
timestamp. Reuse `fundamentals_xbrl` + the existing financial `capital_allocation` model. Cheap/₹0 (no LLM,
no paid feed).
