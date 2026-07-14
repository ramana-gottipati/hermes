# Track D — Doctrine-D financials scorer: primary-source DATA PLAN

> **Lifecycle: TRANSIENT-CAMPAIGN.** The data-sourcing plan for the financial-sector patearn adaptation
> (Codex D3-F1). Decision doc for Ramana → then build. Retire once the scorer ships.

## The problem (D3-F1, verified on the VPS)
`scoring.py`'s pt14 applies **generic ROCE / D-E** thresholds to banks/NBFCs/HFCs and hard-disqualifies
`D/E > 2.0` — structurally wrong for lenders (leverage IS the business). Live proof: HDFCBANK's stored
`fundamentals` row reads `roce=1.57`, `roe=7.04`, `debt_to_equity=(empty)` — nonsense for a bank. The
score currently mis-rates every lender.

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
3. **GNPA/CAR availability** — approve the Step-1 tag-inventory spike as the gate; if a metric proves
   untagged in the quarterly XBRL, it moves to Phase 2 rather than pulling in a vendor. *(Guardrail #8:
   never Screener/vendor to fill a gap — defer instead.)*
4. **Scope order** — build the **data (Steps 1–3) first, scorer (Step 4) second**, or land a Step-4
   *interim* now that simply **suppresses + labels** pt14 for financials ("sector-adapted model pending")
   so no wrong number shows while the data lands? *(Recommend the interim suppress-label immediately +
   data in parallel — stops the live mis-rating today.)*

## Guardrails honored
Primary sources only (NSE SEBI XBRL — no vendor/Screener to fill gaps; defer instead). PIT via broadcast
timestamp. Reuse `fundamentals_xbrl` + the existing financial `capital_allocation` model. Cheap/₹0 (no LLM,
no paid feed).
