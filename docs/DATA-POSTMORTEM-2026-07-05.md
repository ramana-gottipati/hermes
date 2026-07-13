# Data-estate postmortem — 2026-07-05 (analyst-team deep dive)

> **Lifecycle: PERMANENT.** keep-forever data-estate findings record (integrity failures, live counts); not retired. Registered in `docs/DOC_INDEX.md`.


> **Provenance.** This document is the consolidated output of a one-day adversarial deep-dive on the live Hermes/Patearn data estate. An advisor set the program; **eleven domain specialists** (market-microstructure & delivery; PIT-fundamentals & XBRL; ownership & flow; derivatives & positioning; corporate-events & credit; concall-corpus & text; index/breadth/regime; data-dynamics cross-DB; data-quality/survivorship/storage; research-lab panels; client-value/B2B) each ran read-only SQL against the live VPS (`/opt/hermes/data/hermes.db` + `research.db`) and read the repo read-only; a **3-lens risk panel** (PIT-leak / cost-realism / failure-ledger) issued a verdict on every candidate dynamic; an **architect** grouped survivors into 16 build units; and a **UI/UX pass** decided which of ~60 dynamics earn a surface. Nothing on the VPS or in the repo was modified. Every number below is from a live count on 2026-07-05 unless flagged otherwise. Where a specialist number contradicts project doctrine, doctrine wins and the discrepancy is logged in §11.

---

## 1. Executive summary

**Headline (advisor):** The estate is **data-rich and surface-poor.** Nearly every domain holds computed-but-unsurfaced descriptive value — ownership aggregators built and tested but wired to nothing, a 5,225-row settled promise ledger, 50,334 ignition-outcome rows, a 14-year index valuation history, 3,797 fresh company profiles — blocked only by wiring. Alongside sit a few **silent integrity failures**: `corporate_actions` is a dead 0-row pipe that silently disables split-adjustment and continuity-break detection; the rename boundary breaks 100% of price tapes for renamed symbols and orphans ~188 fundamentals links; the fundamentals archive is 99%-survivor-conditioned but that fact lives only in prose.

**The single most important truth:** the recorded **C-BLEND 50/50 "champion" bar (net Sharpe 1.32 / MaxDD −28.2% / Calmar 1.15)** is a **flat-cost number never re-run under realistic participation-rate costs.** Its fundable status is therefore *unproven*, and the entire strategy leaderboard's fundability ranking rests on it. The only orthogonal next-sleeve candidates are **non-price event axes** (rating-drift, insider-drift, guidance) — not momentum variants, whose headroom is ~zero (momentum-ensemble components correlate 0.54–0.95; residual alpha t=1.99 < the t≥3 bar).

**Top conclusions:**

1. **Ship the descriptive / product wedge now, gate every forward claim later.** PIT event ledgers + lag-audited provenance sold as *data, never signals*. The `/v1` API is fully built with **zero tenants**; the day-one sellable dataset is the promoter/governance event tape (PIT-native, vendor-clean).
2. **The census in the briefing is wrong on nearly every table.** `ratio_rows` is 486K rows not 286M (588× over); `concalls` 24,088 not 75.9K (3.2×); `credit_rating_events` 2,798 not 18.3K (6.5×); `concall_scores` 879 not 8.6K (9.8×); `insider_events` 10,008 not 16.3K; `credibility_series` 19,028 not 45.9K. Every trust-surface number sourced from a census instead of a live count is one purge away from wrong.
3. **The real storage target is not `ratio_rows`.** It is ~6.4 GB of re-derivable `stock_signals`/`mep_signals`/`cpr_signals` history and ~4.3 GB of over-indexing — an **index diet**, not a data purge. The raw bhav archive stays sacred (doctrine #6).
4. **Two "sellable" charter premises collapse on live data.** Surprise-vs-street is dead (`street_value`/`market_recognized` 100% NULL). Downgrade-momentum is un-computable (credit tape is 59-symbol / 10-month PIT, 16 downgrades on 2 symbols). The real assets are the **management-candor axis** and the **settled promise ledger**.
5. **The corpus PIT premise is broken.** 2 of 3 concall timestamps are 100% empty; `concall_dt` covers 1.4%. Every concall forward/overlay claim is dishonest until `transcript_publish_dt` is backfilled from the BSE announcement feed (primary-source, no LLM).
6. **The house-signature failure reproduced again.** RS-rank → ignition-magnitude and intensity gradients look like selection edges but reconcile to bull-beta / tail artifacts. Do not re-attempt "tilt by RS" as a ranker; do not re-attempt DELIV_MOM levels (already failed Sharpe 0.42–0.85).
7. **Season clock is load-bearing.** The Provisions-merged-into-Expenses extractor bug must be fixed *before* ~Jul-09 or thousands of bank rows land without credit-cost. Shareholding real-date capture (0.12% today) heals only when Reg-31 real broadcast dates arrive ~Jul-21.

---

## 2. The estate in numbers

All counts **live 2026-07-05** (read-only). "Brief" column = the estate briefing this team was handed; the ratio column is the correction the team owes `PROJECT_STATE.md`.

### 2a. Core operational tables (hermes.db)

| Table | Rows (live) | Range / note | Brief | Drift |
|---|---|---|---|---|
| `bhavcopy_rows` | 9,366,390 | 2004-07-23 → 2026-07-03; RAW, sacred | 9.56M | 1.02× |
| `stock_signals` | ~5.95M | 94–95 cols; PK(symbol,trade_date); epoch 2011-06 | 5.95M | ok |
| `mep_signals` | 7.58M | derived; per-symbol windows → recomputable | 7.58M | ok |
| `cpr_signals` | 6,960,511 | derived; per-symbol → recomputable | 7.15M | 1.03× |
| `ratio_rows` | **486,504** | **NOT 286M** — 191 numerators × {Nifty50, Nifty500} × ≤3,530 dates; 52.6 MiB | 286.3M | **588×** |
| `index_signals` | 300,353 | MAX(rowid)=931,981 = INSERT-OR-REPLACE churn | 932K | 3.1× churn |
| `index_rows` | 283,369 | 209 indices; PE/PB/DY since 2012 (79.6/81.5/81.5% non-null) | — | — |
| `fno_oi_signals` | 102,297 | 2024-07-01 → 2026-07-03; 273 F&O names; 2y | 126K | 1.23× |
| `participant_oi` | 2,460 | 2024-01-01 → ; 4 client types | — | ok |
| `insider_events` | **10,008** | 2025-11-01 → 2026-07-04; 871 syms; 8 months | 16.3K | 1.63× |
| `sast_reg29_events` | 3,424 | 830 syms; 8 months | — | ok |
| `sast_pledge_events` | 559 (589¹) | 153 syms; CREATE 364 / RELEASE 187 / INVOKE 8 | — | thin |
| `credit_rating_events` | **2,798** | 2021-09-17 → 2026-06-25 (rating_date); broadcast_dt only 2025-09 →; **59 mapped syms**, 633 NULL-symbol; DOWNGRADE 16 on 2 syms | 18.3K | **6.5×** |
| `bulk_block_deals` | 1,438 | 2026-06-19 → 2026-07-03; 219 syms; **15 days** | — | — |
| `fii_dii_flows` | **18** | 15 days; 2 categories — a stub | — | — |
| `momentum_scan` | 2,836 | nightly since 2026-07-01; latest == bhav max | — | ok |
| `credibility_series` | **19,028** | 2006-05 → 2026-06; 809 syms; MNAR-deep | 45.9K | 2.4× |
| `capital_allocation_scores` | 5,712 | 1,904 syms; as_of 2026-07-02..04 (bounded snapshot) | — | ok |
| `security_master` | 4,449 | 2,057 not-listed (46.2%); 324 renames | — | ok |
| `security_renames` | 324 | all confirmed=1 (ISIN) | — | ok |

¹ pledge count 559 (dq report) vs 589 (ownership/event reports) reflects a live append between batches; use 559 as the floor.

### 2b. Concall / text estate (hermes.db)

| Table | Rows (live) | Note | Brief | Drift |
|---|---|---|---|---|
| `concalls` | **24,088** | 23,758 screener + 330 bse-ann; 1,069 syms; 16,471 with URL; 13,212 parsed; 4,101 extracted | 75.9K | **3.2×** |
| `concall_guidance` | 51,678 | 809 syms; 26,076 quantified (50.5%); resolved 5,225 / 541 syms | 52.7K | ~ok |
| `concall_signals` | 57,271 | STALE — 5,593 phantom rows vs guidance (rebuild not chained) | 57.3K | ok |
| `concall_redflags` | 25,633 | `guidance_walkback` sev 3.1 is the heavyweight | 68.1K | 2.7× |
| `concall_expectations_vs_actual` | 15,034 | `street_value`/`market_recognized`/`external_classification` **all 0 rows** | 21.6K | 1.4× |
| `concall_behavior` | 3,929 | pairs | 4.1K | ok |
| `concall_scores` | **879** | latest snapshot, NOT a series (canonical series = credibility_series) | 8.6K | **9.8×** |
| `concall_results` | 936 | 73 syms; frozen Screener actuals | 4.6K | 4.9× |
| `concall_coverage` | **0** | purpose-built miss-audit ledger; NO populator exists | 0 | — |

### 2c. Research-lab estate (research.db)

| Table | Rows (live) | Range / note |
|---|---|---|
| `fundamentals_history` | **767,992** | A 511,275 (1,983 syms, 2002→) + Q 256,717 (1,921 syms, 2005→); XBRL era = **24 rows**; brief said 824K |
| `fund_panel` | 51,652 | 2012-06-01 → 2026-05-22; 1,250 syms; fwd_252 NULL 16% |
| `ml_panel` | 116,537 | ~100% overlap with stock_signals; silent survivorship drops → archive candidate |
| `features` | 166,175 | 136,257 event + 29,918 baseline; **only home of the validated Launchpad ingredients** |
| `events_monthly` | 69,746 | crown label set: sustained 37,343 / faded 32,403 |
| `ignition_outcomes` | 50,334 | 41% censored (2024 68%, 2025+ 100%); time-to-MFE + recovery tables — **unsurfaced** |
| `shareholding_history` | 84,427 | 1,517 syms; 2019-06 →; "Promoter Pledge" only 104 rows / 102 syms |
| `strategy_runs` | 22 | all stamped 2026-06-25 12:59:57; **missing C-BLEND 1.32 champion + PEAD 0.10 failure** |
| `accum_screen` | 12,233 | LIVE writer, ORPHAN reader (zero consumers) |

### 2d. Empty-table ledger (all live-verified 0 rows; each has a complete-but-idle writer unless noted)

| Table | Writer | Classification | Cost of emptiness |
|---|---|---|---|
| `corporate_actions` | `corp_actions.py` (CLI, no timer) | **never-run pipe** | split-adjustment + continuity-break silently dead AND unmonitored; the Mar-2026 pit death class |
| `security_events` | derived FROM corporate_actions (`security_master.py:194`) | **empty by cascade** | demerger/rename/event spine unowned; `has_break_between()` returns nothing |
| `earnings_triggers` | `news_feed.py:414` | **dead pipe (wired, produces zero)** | earnings-news branch never fires; 15-min debug before ~Jul-09 |
| `signal_events` | `signal_events.py` (CLI, no timer) | **never-run** | Attention Queue / since-you-looked / alert rail / `/v1` events all dark |
| `bars_weekly`/`monthly`, `weekly`/`monthly_signals` | `mtf_signals.py --backfill` | **never-run (D52)** | MTF DVPT confirmation absent (charting unaffected — cpr_signals covers it) |
| `concall_coverage` | **none** | **dead schema** | no honest denominator for "gone dark" mandatory-but-absent calls |
| `provenance_restatement` | `provenance.py:624` | **dormant-by-design** | restatement policy unproven; ~Jul-09 XBRL season = first live test |
| `fundamentals_restatements` | XBRL path | **dormant-by-design** | records a COUNT not metric identities (see §4 PIT-fundamentals) |
| `v1_tenants` / `v1_api_keys` | seed CLI | **un-activated** | 0 tenants; `v1_usage`=22 selftest rows only |

---

## 3. Missed perspectives (master list)

The advisor's twelve, restated as the load-bearing correctives:

1. **The 1.32 bar is flat-cost fiction** — never re-run under `cost_participation.py` participation-rate costs; the whole leaderboard's fundability ranking is unproven until this is settled.
2. **Silent correctness rot beats missing features** — `corporate_actions`=0 disables split-adjustment AND continuity-break detection AND is unwatched by the very DQ battery whose docstring says it exists to catch this.
3. **The rename boundary breaks 100% of price tapes** and orphans ~188 fundamentals links because almost nothing routes through `security_master.canonical()`.
4. **The house-signature failure reproduced** — RS-rank → ignition-magnitude reconciles to bull-beta/tail (momentum residual t=1.99 < 3). Do not tilt by RS as a ranker.
5. **Momentum-family sleeves are near-collinear** (mean-abs-rank-diff ~8.7; component r 0.54–0.95); C is the ONLY proven orthogonal sleeve, so every future sleeve MUST be a non-price axis (rating/insider/guidance).
6. **Survivorship is a NUMBER, not prose** — 99.0% of delisted names are fundamentally dark; 44.1% of tape mass is unjoinable to fundamentals. It inflates every quintile-lift level and must accompany every backtest claim on the trust surface.
7. **Two charter premises collapse** — surprise-vs-street is dead (`street_value`/`market_recognized` 100% NULL); downgrade-momentum un-computable (59-symbol / 10-month stub). Real assets = candor axis + settled promise ledger.
8. **The corpus PIT premise is broken** — 2 of 3 concall timestamps 100% empty, `concall_dt` 1.4%.
9. **Charter figures are stale by multiples** — concall 24,088 not 75.9K, scores 879 not 8.6K, ratio_rows 486K not 286M, credit feed 6.5× smaller.
10. **Base-rate numbers that embed the overnight gap are NOT capturable returns** — close-to-close next1d includes the gap; DELIV_MOM levels already failed (0.42–0.85). Label "base rate, not tradable" everywhere.
11. **Coverage cliffs are the real constraint** on the ownership/governance story — distress-spiral 589-row/102-symbol, pledge overlap 46/187, SAST invocation n=8. Boards, never gates; Reg-31 flood (~Jul-21) widens.
12. **The B2B wedge is evidence + trust sold as a FEED, not a signal** — `/v1` built with 0 tenants; the lag-audit (149,920 records, measured 87% modeled-date leak-rate + the `knowable_at` fix) IS the compliance SKU. Ranked-alpha stays a permanent CANNOT-COMPETE axis until a strategy clears realistic-cost fundability.

---

## 4. Domain postmortems

Each subsection: the missed perspective → the new dynamic it unlocks → the finer detailing now possible → the conclusion, with evidence numbers. Compact where a table earns its space.

### 4.1 Market-microstructure & delivery (EOD tape)

**Missed perspective — rupee ticket size is never formed.** `value/num_trades` (the direct institutionalization proxy) is computed nowhere; `num_trades` feeds only the DVPT denominator and two *share-count* columns — a doctrine-#6 inversion (shares stored, rupees unformed). **Coverage truth:** `num_trades` is NULL for all of 2004–2010 (2.44M rows) → every trades-derived series starts ~mid-2011 (15y, not 22y).

**New dynamics.** (a) `ticket_ratio_1m_6m` = (Σvalue 22d / Σtrades 22d) / (Σvalue 132d / Σtrades 132d) — the ONE new stored column earning its place (cross-sectional scan + `_character_metrics` already holds both arrays, zero extra I/O); with `trade_count_ratio_1m_6m` it forms an on-read 2×2 (ticket-up + trades-down = blockization). (b) Gap-character base-rate table (on-read, nothing stored). (c) Delivery-percentile primitive. (d) Absorption-at-support scan. (e) SERIES_CHANGE event stream into empty `security_events`. (f) Amihud → per-name capacity chip.

**Detailing — the gap × delivery interaction cleanly separates continuation from fade** (EQ 2016+, |gap|>2%, n=690K):

| side | deliv band | n | next-1d % |
|---|---|---|---|
| UP | dp<45 | 100,619 | −0.11 |
| UP | dp70+ | 173,371 | **+0.78** |
| DN | dp<45 | 43,451 | +0.19 |
| DN | dp70+ | 79,510 | **−0.43** |

High-delivery up-gaps drift +78bps next day while low-delivery up-gaps go flat; high-delivery down-gaps CONTINUE −43bps. Monotone both directions. **Capacity decomposition:** the headline `capacity_cr=30` scalar → ~940 of 2,348 names fundable (deciles 1–4, amihud ≤~20bps/cr); decile 8+ (≥467bps/cr) is un-executable at size — the flat-cost illusion's antidote at the name level.

**Consumption audit — 12 dead columns.** Written nightly for 5.95M rows, referenced nowhere (`avg_dvpt_5d..365d`, `total_value_today`, `ratio_today_vs_avg_30d`, two sector-RS bools) ≈ 0.45–0.55 GB re-written every night. **Correctness gate:** `rs_vs_sector_above_200ma` IS read (`pat/flows.py:199,203`, `pat/web.py:663`) and `rs_vs_broad_new_52w_high` is heavily read — DO NOT drop those two; the candidate wrongly listed the whole RS trio.

**Conclusion.** Every return figure quoted here is a **base rate, not a capturable return** (close-to-close next1d embeds the overnight gap; DELIV_MOM level already failed 0.42–0.85). Ship descriptive; any promotion is a separate pre-registered event study vs net Sharpe 1.32.

### 4.2 PIT-fundamentals & XBRL

**Missed perspective — CFO is verified ABSENT from all 768K facts.** The Screener cash-flow section was never scraped and re-collection is banned (doctrine #8). The profit-vs-CFO accrual gap is **not computable, 24y, full stop.** The honest substitute is a Sloan-lite working-capital accrual proxy from Debtor/Inventory/Payable days.

**New dynamics.** Growth-streak survival lookup; `wc_accrual_proxy`; 8 orphan-metric ratios (Dividend Payout % — 18,833 A-rows, the single richest orphan — Tax %, CWIP, asset-growth, fixed-asset-turnover…); `qg_component_lift`; bank NIM proxy. Only `asset_growth_yoy` earns a `fund_panel` column (negative-predictor prior, must be pre-registered).

**Detailing — the FIRST-ever per-component QG lift.** Date-neutral quintile lift (excess vs same-date mean), survivor-conditioned:

| component | Q1 excess | Q5 excess | Q5−Q1 (pp) | read |
|---|---|---|---|---|
| roce | +5.60 | −7.36 | **−12.96** | hard inversion |
| icov | +7.46 | −4.34 | −11.80 | hard inversion |
| de (leverage) | −1.42 | +3.29 | +4.71 | high leverage wins (beta) |
| debtor_days | −2.32 | +4.19 | +6.51 | worse debtors win |
| **roce_rising** | −0.14 | **+1.87** | — | **only right-signed — a CHANGE variable** |

`qg_pass=1` cohort **underperforms −3.83pp/yr**; `hard_disq=1` **outperforms +2.45pp**. **T1 has ZERO rows in 51,652 PIT observations** — the ns≥72 + qg_pass bar has never been met point-in-time. Quality LEVELS carry zero-or-negative selection information (sharper than D66); only CHANGES (`roce_rising`) are right-signed — exactly why C-BLEND beat the 4-metric level lens.

**Growth-persistence survival (24y, gaps-and-islands):** P(Sales>15% streak survives ≥2y)=45.8%, ≥3y=**17.4%**, ≥5y=**3.7%**. Genuinely earns a visual — a decay line the number alone hides.

**Conclusion / binding rules.** (i) **24y dynamics = ANNUAL only** — the quarterly archive is a 12-quarter 2023-cliff (TTM 5.6% populated). (ii) All joins through `effective_as_of` with a `pit_confidence` stamp. (iii) **Bank Provisions extractor bug is season-critical**: one `put("Provisions", prov)` in `extract_bank_for` makes `credit_cost_ratio` formable — the tag is already parsed; miss ~Jul-09 and thousands of bank rows land without it. **PIT engine measured:** real BSE dates cover ~69% of period-keys (2011+); the old +90/+50 model leaked on **11.9% of 149,920 audited rows** (worst 659 days) → calibrated p95 = A 114d / Q 59d.

### 4.3 Ownership & flow

**Missed perspective — the aggregators were built, tested, and wired to nothing.** `insider_events.aggregate()` and `sast_events.aggregate()` compute PIT net-cashflow, cluster-buy, pledge roll-ups — **zero imports across `src/`**; both are CLI-only. The one production consumer (`momentum_view.py:84`) runs a raw magnitude-blind COUNT the docstrings warn against. **The system stores ₹38,672cr of promoter caution-selling and surfaces none of it.**

**New dynamics.** `ownership_flow_snapshot` (nightly bounded, C-column precedent); SHP velocity/acceleration (only sign-booleans exist today); pledge-feed union; promoter-buy cluster tape; deal counterparty fingerprint; distress-spiral composite.

**Detailing.** Promoter holding is **inert for 86% of names/quarter** (|Δ|<0.25pp); the information is entirely in the ~60-name tails (SAMMAANCAP FII +21.3pp, WSI +12.9). Conviction-buying is 4× more frequent but caution-selling is **4× larger by value** (2,669 ev/₹9,870cr vs 688 ev/₹38,672cr). Two pledge feeds are complementary (insider 80 syms, SAST 153, overlap only 46, union 187). Deal tape is 58.6% same-day HFT churn — the top-5 counterparties are all perfectly two-sided.

**Distress-spiral proven live** (pledge stock × flow × drawdown): 2 symbols fire all three legs today (JPPOWER 73% pledged / −34.6% from high; AVG 66.7% / −26.3%); NEOGEN shows the early-warning shape (24.7% pledged, flow firing, price intact −5.5%). **Coverage cliff to state on the tape: 589-row / 102-symbol; SAST INVOKE n=8** — board only, never a gate.

**Conclusion + correctness rider.** Descriptive columns only (S1). **Denominator warning:** SHP pledge % = % of *promoter* holding; SAST encumb % = % of *total* equity — display side-by-side, never blend. **Schema-lock NOW:** add `client_key = upper(collapse_whitespace(client_name))` at ingest in `deals.py` so 6 months of NSE-drifting names stay joinable.

### 4.4 Derivatives & positioning

**Missed perspective — the primary-source pre-UDiFF F&O archive is LIVE but only 2y is ingested**, and 5 dormant F&O columns in `bhavcopy_rows` are 100% empty. A bounded ~675K-row near-month futures backfill turns every 2y finding into a decade-long one.

**New dynamics.** `fno_fut_history` (near-month only — DROP far-month/option-chain where rows explode); OI×delivery conviction tape; quadrant-transition ribbon; basis/max-pain levels descriptor; participant-OI noise-map.

**Detailing — the ONE cell where positioning leads.** OI×delivery: only **25% of OI-up days are "real"** (OI up + delivery spike + price up = CONVICTION_LONG). The F&O quadrant **confirms same-day but barely leads** — a 7pp edge collapses to 3pp over next-5.

**Honest labels (mandatory).** (a) +2.7pp/2y and 7pp→3pp are thin-sample level effects — NOT rankers. (b) `max_pain` does **NOT** pin price into expiry (folk belief fails its base-rate control; slightly *looser* near expiry) — ship as levels/disagreement descriptor, expiry-pin recorded-failed. (c) `participant_oi` carries NO index-level forward edge at n~609 (FII/Client/Pro all non-monotonic) — surface as a **noise map**, grey out structurally-empty DII-option cells (DII avg 109K vs Client 14.8M). PRO-desk net-long (~9bp, within noise) is the only pre-registerable cell — and only after the backfill lifts n=285.

**Conclusion.** Descriptors ship now on 2y data as honest labels; depth/promotability waits on the backfill. Scope HARD to near-month futures.

### 4.5 Corporate-events & credit

**Missed perspective — the concall PIT spine does not exist.** `result_filing_dt` and `transcript_publish_dt` are 0 of 24,088; `concall_dt` exists only for 330 bse-ann rows (and even those hold the *announcement* date, mislabeled). Every derived ledger floats on month-granular `period_label`. **No event study, no day-level bhav join, no results-season clock can run on concall data today.**

**New dynamics.** Promise-tenor value curve; management-candor (sandbag) index; rating-event tape (notch-velocity, agency-disagreement, dedup Acute/Acuite); deterioration-lead tape; governance-stress composite; balance-sheet promise settlement.

**Detailing — the promise-tenor value curve (the sellable aggregate).** Resolved-only (n=5,225):

| horizon | n | MET% | MISS% | avg variance | variance when MISSED |
|---|---|---|---|---|---|
| next_q | 500 | 61.2 | 37.6 | +10.6 | **−13.0%** |
| fy | 3,982 | 56.8 | 37.8 | +2.1 | **−22.6%** |
| multiyear_3_5y | 380 | 52.9 | 41.8 | +0.6 | **−31.7%** |

Miss RATE is roughly flat (~37–42%) but miss DEPTH scales monotonically with horizon — managements miss long-dated promises ~2.4× harder. **Candor asymmetry:** UNDERSTATED : OVERSTATED = 3,427 : 132 (~26:1) — the corpus says managements systematically sandbag; 1,271 CONCEALED instances sit as a narrative flag. **Deterioration lead:** `related_party` (n=111, −5.62 next-period credibility Δ) and `evasion` (−4.71) are OUTSIDE the deterministic-penalty set — genuine information, not construction.

**Credit truth-check.** 2,798 events, **59 issuers**, DOWNGRADE=16 on 2 symbols, REAFFIRM=2,440 (87%). broadcast_dt coverage is 10 months, not 5y. Downgrade-momentum is un-computable; the only live finding is agency labeling disagreement. **ISIN dedup is a hard correctness gate** before any symbol roll-up (rating ISINs are mostly debt ISINs — 633 rows NULL-symbol, ISIN bridge recovers only 5).

**Conclusion.** All descriptive (CCI Gate B failed on leak-free inputs). The concall timestamp backfill is the highest-priority PIT prerequisite — it converts five derived tables from panel to event data.

### 4.6 Concall-corpus & text-asset

**Missed perspective — the coverage funnel is DESIGN + BACKLOG, and `concall_coverage` (0 rows, the purpose-built miss-audit ledger) has no populator.** 24,088 → 16,471 URLs (by design) → 13,212 parsed → **4,101 extracted** (9,111 unextracted = pure LLM-budget backlog; ~506 days at the free-tier pace). `concall_signals` is stale by 5,593 phantom rows (rebuild not chained).

**New dynamics.** Concall clock backfill (97.3% of transcripts carry a cover-page date; regex-free win); `concall_coverage` populator (nightly pure-SQL, zero LLM); zero-LLM mention graph (~10⁴–10⁵ edges over 13,212 texts); topic tape (money-regex over the unextracted 9,111); settle-after-XBRL loop.

**Detailing — text assets built, paid for, rendered nowhere.** `company_profile.business_brief` = 2,903 Gemini-grounded briefs, **ZERO references in `src/web`**; `vocab_tags` = 2,760, never synced. The stock dossier has no "what does this company do" line while 2,903 briefs sit unused — the cheapest UI win in the estate.

**Cost to close the backlog (ESTIMATE only, no spend).** Gemini free tier ~506 days (in budget, uselessly slow); Haiku 4.5 ~₹18.5K (reject); **Gemini Flash-Lite ~₹1,700 one-time, triaged to ~₹900–1,000** on a liquidity-ranked subset → a surfaced decision for Ramana, not a standing burn. The FREE full-corpus regex numeric pass over 13,224 texts is fine to run now.

**Conclusion.** Nearly everything is descriptive/tape/disclosure. The `+2.8%/+2.3%/+1.8%/+1.5%` at-3m forward tilt (debt-reduction/volume/new-product/capex) is CCI descriptive-only zone (Gate B failed leak-free); any promotion is a NEW pre-registered experiment re-tested on the BSE publish date.

### 4.7 Index, breadth & regime

**Missed perspective — the census was wrong about the largest object.** `ratio_rows` = 486,504 rows (MAX(rowid)=286M is INSERT-OR-REPLACE churn — the full history rewritten ~588×). The real inefficiency is **write churn** (WAL pressure, lock windows), not storage. Redirect the space audit to `stock_signals` (3.97GB) / `mep_signals` (1.30GB) / `cpr_signals` (0.96GB).

**New dynamics.** Index valuation-band board (PE/PB/DY percentile, 171 indices, on-read); breadth time-series (~3,500 rows <1MB stored); phase-transition stats (dwell + transition matrix + forward-return, reconstructable on-read); regime-overlay 3-tuple (valuation × phase × breadth — never crossed); membership events.

**Detailing.** The market sits in the **cheap third of its 14-year valuation history** (Nifty 50 PE 20.92 = 27.7th percentile of 3,530 days) — a materially different statement than the current 252-day window can make. Phase memory is only **10 trading days** deep in-app, but the classifier is a pure function of stored slopes → 14 years reconstructs in 1.4s: HEADWIND is the stickiest state (12.8d avg dwell), RECOVERY/ROLLING-OVER transient (~4.4d). **Forward 66-day excess after entering each phase: beat rates 47.5–49.4% across ALL phases** → phase entry carries no directional edge; the information is persistence and composition — independently confirms descriptive-only.

**Conclusion.** All boards descriptive-CLEAR. Weight-change events are **IMPOSSIBLE** (`weight_pct` all NULL); inclusion/promotion events are fine. 18 dormant thematics have RS but no capture/RRG — a one-line allowlist edit gains them coverage free. Case-variant duplicate index keys ("NIFTY Midcap 100" vs "Nifty Midcap 100") silently split history — DQ hand-off.

### 4.8 Data-dynamics (cross-table & cross-DB joins)

**Missed perspective — no module uses ATTACH; the rename boundary breaks exactly where predicted.** The production bridge is two `?mode=ro` connections merged in Python. For `AKZOINDIA→JSWDULUX`: concalls/credibility keyed to the NEW symbol, fundamentals archive to the OLD — any symbol-equality cross-DB join for JSWDULUX returns **ZERO fundamentals** (C allocation, PIT scorer, promise-settlement silently lose the company). For `LTI→LTM`: old symbol last traded 2022-12-02, effective 2026-02-27 — a 3.2-year gap = ISIN-recycling false-edge risk.

**New dynamics.** Canonical-symbol resolver (chain-resolve `security_renames`, cycle-guarded, + gap sanity check); mechanical settlement sweep; promoter stock-vs-flow reconciliation board; insider post-disclosure tape; theme-rotation index; the `(metric, period_end)` index on `fundamentals_history` — the **highest-leverage index addition in the estate** (every cross-sectional as-of scan is currently a full 824K-row scan).

**Detailing — the six unrun joins, each with a RUN proof.** J1 (insider × bhav): conviction clusters ≥₹5cr, Jan–Mar 2026, **+2.73% avg forward-2m, 64% up** while Nifty 500 fell −10.8% (descriptive only; VIPIND ₹1,029cr is a control-change block misclassified as conviction — filter pct_equity<5%). J4 (SHP × reg29): the correct recipe anchors on `pct_after` LEVELS per acquirer_hash, not flow sums (reg29 inter-se legs carry pct_acq=0.0 with real pct_after — naive sums double-count). J6 (downgrade × pledge × drawdown): **ZERO rows** — 16 downgrades on 2 symbols; correctly specified, not yet computable.

**Conclusion.** The canonical cross-DB recipe (`ATTACH ?mode=ro` + canonicalize key FIRST) is the correct guard against both the write-lock outage and the 188-name drop. Record it in the decision log as binding.

### 4.9 Data-quality, survivorship & storage

**Missed perspective — the census handed to the team is itself drifted, and the DQ battery is blind to every new event feed.** Inflated tables all have dedup/purge lifecycles. **Survivorship geometry (the disclosure numbers):** 2,057/4,449 not currently listed (46.2%); 2,461/4,449 never in fundamentals (55.3%); **4,135,026/9,366,390 bhav rows unjoinable to fundamentals (44.1%)** → fundamentals-conditioned analyses cover **55.9% of tape mass / 82.3% of today's universe**, and the excluded 44.1% is where the delistings live.

**PIT-lag truth (149,920 measured rows):** avg lag_error −20.7d (conservative), but **12.9% leak, 2.5% leak >30d, 201 rows >90d (max 659d)**. Modeled fundamentals dates safe for 87.1% of measured periods; calibrated p95 (A 114d / Q 59d) is the quantitative defense.

**Corporate-action fragility.** `corporate_actions`=0 because all four NSE archive CSVs 404'd (~session 18); never resurrected, never watched — while the trust page *claims* its outputs (`coverage_view.py:74` says demergers are recorded as continuity-break events; `security_events`=0). What protects the system is `adjust.py` inferring split factors from prev_close discontinuities. **One fragile column family:** `key_price_p1m..p12m` + `gap_to_key_*` feed RAW avg_price with no adjustment → a 1:5 split 3 months back inflates key_price → `gap_to_key` a −60..−80% artifact, self-healing only as the window rolls off.

**Storage census vs doctrine #5.** Derived tables + indexes ≈ 9.85 GiB = 63% of the file; **indexes alone ≈ 4.3 GiB (28%)**. The honest reclamation is an **index diet** (4 single-column mep indexes 847 MiB → one composite; overlapping cpr tf-indexes; stock_signals single-column → partial on recent dates) ≈ 2–2.5 GiB, zero row deletion. mep/cpr full histories (~4.3 GiB) are the only true compute-on-read candidates — flag for Ramana, don't act unilaterally. (Tooling note: `dbstat` pgsize overflows 32-bit on >4GiB btrees — use pages×4096.)

**Conclusion.** ZERO DQ checks watch `sast_reg29`/`pledge`, deals, `fii_dii`, `participant_oi`, `fno_oi`, `corporate_actions` emptiness, or `stock_signals`/`mep`/`cpr` staleness vs bhav — the three largest derived tables can silently stop updating with no banner anywhere. One registry-driven staleness+nonzero check closes the whole class.

### 4.10 Research-lab (research.db panels & labels)

**Missed perspective — the machine ledger lags the paper ledger, and `/dash/testing` shows a superseded, flat-cost bar as the house best.** `strategy_runs` = 22 rows all stamped 2026-06-25 12:59:57; nothing appended since. Missing: the overlay experiment, the gate study, the **cost-participation correction (LOWVOL_MOM Rs50cr net 1.02 — OVERTURNS the seeded story)**, **C-BLEND 1.32 (the current bar)**, and the **PEAD failure (net 0.10 / hedged −0.58)**. The Trust-altitude page renders "none beats buy-and-hold net of cost" — **FALSE since 2026-07-02**.

**New dynamics.** `launchpad_snapshot` (bounded nightly, the validated Launchpad ingredients live only in `features`/one-day cockpit recompute — you cannot screen the historical universe by the one precursor this estate validated); canonical outcomes library; breakout-regime tape; ledger auto-seed extension.

**Detailing — five label systems disagree.** Horizon grids collide (ignition 21/63/126 vs everyone else 22/66/132 — joins off by 1–6 td); units collide (ignition `mfe_pct` +145.8 *percent* vs events 0.5174 *decimal* — a 100× trap); censoring differs (events 11.8% NaN, ignition 41% flagged, fund_panel 16% NULL + unflagged realized-death, ml_panel 0% because dying names are silently DROPPED). The Launchpad lift (`ret_22d>0.0801 AND deliv_qty_trend<=1.477`) is **OOS-robust both directions** (test_lift 7.07 / 5.68) but recorded in three places, none the machine ledger.

**Conclusion.** `fund_panel` raw tier means show **no positive ordering** (DISQUALIFIED +21.78% > T3 +18.05%; T1 n=0) — independent confirmation of D66. The one promotion is SURFACING the Launchpad, not gating it.

### 4.11 Client-value & product (B2B data wedge)

**Missed perspective — the `/v1` layer is fully built with ZERO tenants, and the flagship dataset is 2 fixes from feed-grade.** `v1_tenants`=0, `v1_usage`=22 (selftest). The single highest-leverage act is not building — it is flipping `HERMES_V1_ENABLED`, minting one key, and exposing the promoter/governance event tape (PIT-native, vendor-clean, primary-source).

**Day-one sellability ranking.** (1) **Promoter/governance event tape** — wins on all three panel criteria simultaneously (PIT-defensible + coverage-honest + no vendor taint); 30d tape separates ₹14,302cr INTER_SE from ₹9,561cr true promoter selling. (2) **Guidance/promise ledger** — the bigger differentiator (nobody sells this for India; resolution engine proven symmetric at +20.4% MET / −22.8% MISSED) but fails two of three today (no `transcript_publish_dt`; 98.6% Screener-discovered → disclose per doctrine #8). (3) **PIT replay packs / provenance** — the door-opener; the 149,920-measurement lag audit is a demo artifact no competitor can produce about themselves.

**Detailing — the confluence join.** ≥2 independent stress sources in 90d = **7 symbols** (MTARTECH, NRBBEARING, RELTD… all insider_sell+pledge; the ratings leg contributed zero due to the mapping gap). Nothing surfaces this today.

**Conclusion.** WIN axes: PIT event ledgers with dual clocks / measured lag audit / 22y microstructure depth / management-behavior taxonomy. CANNOT-COMPETE: estimates (none), breadth/global, ranked alpha (none fundable). Price to analyst-hours build cost (junior analyst ₹8–15L/yr), never the ₹300/mo run-rate: paid POC ₹2–4L → single-dataset ₹5–12L → multi-dataset + provenance ₹15–25L.

---

## 5. New data dynamics — the catalog

Every surviving dynamic. `PIT` = leak risk (none/low/med/high). `Verdict` = risk-panel call (clear/caution). Compute shape: OR=on-read · NS=nightly-snapshot · BB=bounded-backfill.

| id | definition sketch | inputs | shape | PIT | verdict |
|---|---|---|---|---|---|
| micro:gap-deliv-tape | gap_pct + same-day-fill + liquidity-tercile + delivery band → base-rate table | bhavcopy_rows open/prev_close/deliv_per/value | OR | low | caution |
| micro:dead-dozen-cols | stop-write 10 verified-dead stock_signals cols (NOT the 2 read RS bools) | signals.py/_SIGNAL_COLS | NS | none | clear |
| micro:ticket-institutionalization | ticket_ratio_1m_6m = rupee ticket velocity; 2×2 vs trade-count | bhavcopy value+num_trades | NS | none | caution |
| micro:amihud-capacity-ladder | impact_bps + days_to_build per name | mep_signals.amihud_22d | OR | none | clear |
| micro:series-event-stream | SERIES_CHANGE (EQ→BE…) into empty security_events | bhavcopy_rows.series | BB+NS | low | clear |
| micro:absorption-at-support | high-delivery down-days at key prices | bhavcopy × stock_signals gap_to_key | OR | none | caution |
| micro:deliv-pctile-primitive | percentile-rank of today's delivery vs own history | bhavcopy deliv_qty×close | OR | none | clear |
| funda:qg-lift-inverted | per-component date-neutral quintile lift (levels inverted) | fund_panel | OR | med | caution |
| funda:no-cfo-wc-accrual | Sloan-lite wc_accrual_proxy (CFO verified absent) | fundamentals_history A | OR/BB | low | caution |
| funda:growth-streak-base-rates | streak age + survival lookup (17% survive yr3) | fundamentals_history A | OR/NS | low | clear |
| funda:orphan-metrics | 8 ratios (payout, tax, CWIP, asset-growth…) | fundamentals_history A | OR/BB | low | caution |
| funda:bank-season-credit-cost-gap | NIM proxy formable; credit-cost BLOCKED on extractor | fundamentals_history bank-Q | OR | none | caution |
| funda:pit-lag-truth | pit_confidence stamp (real / calibrated-p95 / modeled) | provenance tables | OR | none | clear |
| funda:quarterly-2023-cliff | binding rule: 24y dynamics = ANNUAL only | — | n/a | none | clear |
| own:unwired-aggregators | ownership_flow_snapshot (1-row/symbol nightly) | insider/sast/shp aggregators | NS | none | clear |
| own:shp-velocity | d1q/accel/vel_4q window funcs | shareholding_history | OR | med | clear |
| own:pledge-feed-union | union of both pledge feeds + reg29 stake tape | insider/sast_pledge/reg29 | OR | none | clear |
| own:cluster-tape | promoter buy/sell clusters (dedup same-person-day) | insider_events | OR | low | clear |
| own:distress-spiral | pledge stock × flow × drawdown (589-row driver) | shp × sast_pledge × stock_signals | OR | low | caution |
| own:deals-fingerprint | counterparty one-sidedness; lock client_key NOW | bulk_block_deals | OR | none | clear |
| own:insider-drift-study | pre-registered drift study n=2,596, disclosure_dt entry | insider_events × bhavcopy | BB | med | caution |
| own:fii-dii-backfill | daily FII/DII archive (18-row stub → years) | NSE/BSE daily reports | BB+append | low | caution |
| posn:fut-backfill-10y | 10y near-month futures (~675K rows) | legacy foDD…bhav zip | BB | none | clear |
| posn:oi-x-deliv-conviction | OI×delivery 2×2 (only 25% of OI-up "real") | fno_oi_signals × bhavcopy | OR | low | caution |
| posn:quadrant-coincident | quadrant transition ribbon (confirms, barely leads) | fno_oi_signals | OR | low | clear |
| posn:maxpain-no-expiry-pin | levels + disagreement (max_pain does NOT pin) | fno_oi_signals × bhavcopy | OR | none | clear |
| posn:participant-oi-noise | noise-map (grey out empty DII-option cells) | participant_oi | OR | med | caution |
| posn:dormant-cols-dead | repurpose 5 empty F&O cols for near-month OI | bhavcopy_rows | BB | none | clear |
| event:promise-ledger | GA% + avg-variance per (horizon,statement_type) | concall_guidance | OR | none | clear |
| event:street-value-empty | candor axis (surprise-vs-street is dead) | concall_expectations_vs_actual | OR | none | caution |
| event:credit-tape-stub | rating dispersion (ISIN-dedup); notch-velocity NOT computable | credit_rating_events | OR | low | caution |
| event:gov-stress-join | trailing-365d adverse-event composite (≤40-59 syms) | credit/pledge/insider/redflags | OR | low | clear |
| event:season-clock-and-tape | season watch via concall_month/year (PIT dates empty) | concalls/guidance/redflags | OR | med | caution |
| corpus:pit-empty | transcript_publish_dt/concall_dt backfill from BSE feed | BSE announcement API | BB | high | clear |
| corpus:mention-graph | zero-LLM supply/rivalry graph over 13,224 texts | transcripts × name gazetteer | BB | low | caution |
| corpus:orphan-profile | render 3,797 business_briefs on the dossier | company_profile | OR | none | clear |
| corpus:extract-backlog | FREE regex numeric pass (LLM behavioral pass cost-gated) | concall_signals regex | BB | low | caution |
| corpus:coverage-ledger | populate concall_coverage nightly (F&O cohort) | bhavcopy turnover × concalls | NS | none | clear |
| regime:valuation-band | PE/PB/DY percentile board (171 indices) | index_rows | OR | none | clear |
| regime:breadth-series | ~3,500-row breadth time-series (<1MB) | stock_signals aggregates | NS | low | caution |
| regime:phase-transition-stats | dwell + transition matrix + forward-return | index_signals slopes | OR | low | caution |
| regime:regime-overlay | valuation × phase × breadth 3-tuple badge | index_signals + valuation + breadth | OR | low | clear |
| regime:membership-events | inclusion/promotion stream (weight-change impossible) | stock_index_membership | OR | low | caution |
| regime:coverage-gaps | allowlist 18 dormant thematics for capture/RRG | sector-curation layer | OR/NS | none | clear |
| regime:ratio-rows-correction | census fix: 486K not 286M; redirect space audit | dbstat | n/a | none | clear |
| strat:cblend-not-cost-real | re-cost C-BLEND under participation model (unproven) | strategy_runs + cost_participation | OR | none | clear |
| strat:valuation-regime-untested | Nifty500 PE-tercile split of C-BLEND | index_rows.pe × c_overlay | OR | low | caution |
| strat:ignition-holding-exit-tables | surface time-to-MFE + recovery (50.3K stored rows) | ignition_outcomes | OR | low | clear |
| strat:rs-gradient-beta-artifact | RS-rank→ignition gradient = bull-beta (diagnostic) | ignition_outcomes | OR | low | clear |
| strat:momentum-sleeve-collinear | rank-agreement matrix (headroom ~0; C only orthogonal) | momentum_scan + ca_pctile | OR | none | clear |
| strat:rating-action-overlay | #1 event candidate; sample-reconcile FIRST | credit_rating_events × bhav | event-study | low | caution |
| strat:amihud-capacity-per-name | cap_cr per name (flat-cost antidote) | mep_signals.amihud_22d | OR | none | clear |
| lab:launchpad-lift-buried | launchpad_precursor_score (15× OOS lift, descriptive) | features raw battery | NS | low | caution |
| lab:ledger-db-missing-champion | append 2 missing strategy_runs rows | strategy-ledger.md | OR | none | clear |
| lab:label-recipe-reconciliation | td↔month crosswalk + unified MAE VIEW | ignition/events/fund_panel | OR | med | clear |
| lab:combined-panel-dormant | quality-conditioned launch lift (pre-registered) | combined_panel | BB | med | caution |
| lab:staleness-labelable-2025 | re-run events/features/panel to advance frontier | bhavcopy (RO) | BB | low | clear |
| lab:accum-screen-overlay | drop 2 copied cols, join live; keep sweet_spot | stock_signals + fundamentals_asof | NS | low | clear |
| plumb:rename-boundary-break | canonicalize BOTH sides before join (fixes 100% breaks) | security_renames | OR | high | clear |
| plumb:canonical-crossdb-recipe | ATTACH ?mode=ro + canonical key (nobody does this) | — | OR | none | clear |
| plumb:empty-table-adjudication | wire corp_actions/signal_events/mtf/coverage writers | existing writers | NS/BB | none | clear |
| plumb:mgmt-batting-avg | mgmt_hit_rate (settled≥8; down-weight is_qa) | concall_guidance | NS | none | caution |
| plumb:shp-sast-reconciliation | promoter stock-vs-flow (mismatch is the signal) | shp × reg29 | NS | med | caution |
| plumb:theme-rs-rotation | theme_rs = AVG(rs_rank) GROUP BY tag (members≥8) | company_tags × stock_signals | OR | low | clear |
| plumb:insider-tape-forward | insider forward tape (disclosure_dt, NOT transaction_dt) | insider_events × bhavcopy | OR | low | caution |
| plumb:fh-metric-index | (metric, period_end) index — highest-leverage add | fundamentals_history DDL | one-time | none | clear |
| dq:corp-actions-dead-pipe | freshness check for corporate_actions (dead + unwatched) | data_quality.py | OR | high | clear |
| dq:survivorship-99pct-dark | coverage_by_status in universe_policy (99% dark) | security_master × fundamentals | OR | high | clear |
| dq:pit-leak-measured-vs-blind | shareholding lag calibration (after Reg-31 ~Jul-21) | provenance_knowable | NS | med | clear |
| dq:dq-battery-blind-feeds | staleness + SAST-sanity + rowcount-floor checks | feed tables | OR | low | clear |
| dq:storage-real-target | bounded_snapshot_reclaim of ~6.4GB stock/mep/cpr | stock/mep/cpr full history | BB | none | clear |
| dq:promoter-flow-reconciliation | promoter_flow_tie_out (ΔSHP − ΣSAST residual) | shp × reg29 × pledge | OR | low | clear |
| dq:table-census | nightly table_census (kills census drift) | all tables | NS | none | clear |
| dq:key-price-adjust-fix | apply adjustment_factors inside _key_price_arrays | signals.py | NS/BB | none | clear |
| prod:kept-word-ledger | kept_word_score + hedge_index; /v1 promises SKU | concall_guidance | NS | low | clear |
| prod:provenance-lag-audit | publish measured 87% leak-rate + knowable_at fix | provenance_lag_audit | OR | high | clear |
| prod:v1-activation-promises | flip HERMES_V1_ENABLED; /coverage + /registry first | src/api/v1 | OR | low | clear |
| prod:governance-stress-tape | disclosure-dated adverse-event composite | insider/sast/credit/redflags | NS | low | clear |
| prod:defensibility-pricing-map | win vs cannot-compete scorecard; analyst-hours pricing | — | OR | low | clear |
| prod:expectations-gap-concealment | management_candor_score (incl. 1,271 CONCEALED) | concall_expectations_vs_actual | NS | low | caution |

---

## 6. Strategy candidates & pre-registration queue

**The bar (cited throughout):** RISKADJ rel-gate + **C-BLEND 50/50 = net Sharpe 1.32 / MaxDD −28.2% / Calmar 1.15** (Experiment 2026-07-03). **Critical caveat:** this bar is FLAT-cost and its fundable status is UNPROVEN under realistic participation cost. Every experiment routes through the binding pre-registration checklist (§8 notes): pre-registration block written before touching outcome data; failure-ledger citation; PIT discipline; cost & capacity honesty (participation model at ≥₹50cr, gross never leaves the lab); both-halves + t≥3 (HAC); deflated-Sharpe with true trial count; new-sleeve correlation pre-filter |r|<0.6 vs riskadj.

| Experiment | Hypothesis | Benchmark to beat | Kill criteria |
|---|---|---|---|
| **Cost-reality re-cut of the C-BLEND champion** | C-BLEND 50/50 survives realistic participation-rate cost (C tilts toward lower-slippage names) | RISKADJ-realistic net 0.09 AND Nifty-500 B&H ~0.89 net at ≥50cr | Net Sharpe at ≥10% ADV/day POV (Almgren k=0.6) < Nifty-500 B&H net at any of ≥3 AUM points → **not fundable; 1.32 re-stated as flat-cost-only** |
| **Rating-action drift overlay** (#1 orthogonal candidate) | Notch changes (broadcast_dt+1 entry, delivery-confirmed) carry orthogonal drift on C-BLEND | residual-alpha t≥3 (momentum's t=1.99 is the FLOOR to exceed) AND orthogonal Sharpe on top of 1.32; 2021-only disclosed | **Sample reconciliation fails FIRST** (candidate 18.3K events vs live 59-symbol/16-downgrade stub) → if actionable events <300 or t_cohort<2, abort before any book; must not duplicate pead.py SUE |
| **Promoter-conviction / insider-drift event study** | Promoter-buy conviction (cluster-vs-solo × pct-equity quartile) predicts forward abnormal return | residual-alpha t≥3 vs matched non-event symbols; n=2,596 with full windows | Entry on transaction_dt (leak) instead of disclosure_dt invalidates the run; if +5/+22/+66d t<3 or duplicates pead.py → descriptive-only |
| **Valuation-regime conditioning of C-BLEND** | Nifty500 PE-tercile (expanding-window, leak-guarded) conditions the edge | flat C-BLEND 1.32 net on block-bootstrapped BOTH halves after idle-month cash-drag + realistic cost | D66 tripwire — if a standalone-value tilt, or fails either half, or single-14-year-path curve-fit → descriptive regime board only |
| **Fundamental-CHANGE composite overlay** | change-composite (roce_rising / ΔOPM / Δdilution / Δasset-growth) is legitimate where LEVELS are not | OOS + realistic-cost on c_overlay.py; beat net 1.32; survivorship-disclosed | D66 — standalone quality not a ranker; if fails OOS or lift is survivorship artifact → descriptive column; asset_growth_yoy carries a negative-predictor prior, pre-register |
| **Sleeve-orthogonality routing gate** | Only non-price axes add orthogonal headroom; momentum variants do not | mean-abs-rank-diff vs riskadj/ensemble/C-blend must exceed the ~8.7 collinearity floor before any book slot | Any momentum-family sleeve (headroom ~0) or the RS-rank→ignition gradient (bull-beta, t=1.99 class) is BLOCKED at the gate |
| **Survivorship re-cut of the champion bar** | 1.32 survives restriction to the PIT-knowable universe (ACTIVE-only / universe_on(as_of)) | reproduce ≥1.32-class Sharpe on the survivorship-restricted universe | If 99.0%-survivor-conditioned fundamentals materially inflate the lift and restricted Sharpe collapses → bar re-stated with the coverage caveat |

**Untested cells confirmed** (strategist): regime conditioning at Tier-1 is entirely absent; C-BLEND has NEVER run through `cost_participation.py`; sleeve return correlations are structurally unanswerable today (no monthly return series persisted — a ~3,700-row `strategy_returns` table fixes it permanently). **Ignition exit tables (stored, unsurfaced):** 81% of uncensored peaks come after 132td (avg MFE 238%); early peaks are disasters (ret_12m −42%); a −30% stop cuts 48% of eventual +25% winners.

---

## 7. Do NOT do (nothing discarded silently)

| Item | Reason (with the number) |
|---|---|
| Drop `rs_vs_sector_above_200ma` or `rs_vs_broad_new_52w_high` | READ (`pat/flows.py:199,203`, `pat/web.py:663`; telegram/cockpit/dashboard/index_signals). Only the 2 sector-specific bools + avg_dvpt family are dead. Grep-gate every drop. |
| "Tilt by RS rank" or DELIV_MOM levels as rankers | RS-rank→ignition reconciles to bull-beta/tail (residual t=1.99<3); DELIV_MOM level failed Sharpe 0.42–0.85. House-signature failure — descriptive diagnostic only. |
| Add momentum-family sleeves | Ensemble near-collinear (component r 0.54–0.95; mom6×riskadj 0.95; mean-abs-rank-diff ~8.7, headroom ~0). C is the only orthogonal sleeve. |
| Re-propose BOOK_YIELD or standalone value/quality as rankers | BOOK_YIELD = hard reject (β1.54, MaxDD −82%, negative alpha). Standalone value/quality = veto/context only (D66); quality LEVELS are sign-inverted (roce Q5−Q1 −12.96); only CHANGE carries the right sign. |
| Promote CCI/credibility, Wolfe, harmonic, or capture to gates/rankers | Descriptive-only zones; CCI Gate B failed on leak-free inputs; Wolfe edge = selection. redflag→credibility-momentum and concealment→drawdown sit here. |
| Quote surprise-vs-street or downgrade-momentum/notch-velocity | `street_value`/`market_recognized` 100% NULL; credit tape 59-symbol/10-month, 16 downgrades on 2 symbols. `commitment_strength`/`speaker_role`/`is_qa` 100% NULL → charter's term-structure×cohort cut un-runnable without cheap-model re-extraction. |
| Store a new stock_signals column for ticket-size or any DELIV level | Doctrine #5: stored only if a cross-sectional SCAN needs it. `_character_metrics` already exposes the arrays; compute on-read. DELIV_MOM level analogs failed 0.42–0.85. |
| Claim gap/absorption base-rate numbers as tradable returns | close-to-close next1d embeds the overnight gap → non-capturable base rates. Label "base rate, not a tradable return." |
| Run corp_actions/FII-DII/F&O/concall fetchers holding a write txn across network I/O | DB-write-lock outage lesson: per-filing commits + throttle; busy_timeout < TimeoutStartSec. Never `systemctl start` a hermes timer mid-day (AUD-95, `Requires=` fires immediately). |
| Auto-run the ~₹1,139 LLM concall behavioral extraction | Paid spend needs Ramana's surface-first sign-off (guardrail #0) + cheap-model discipline (doctrine #7). The FREE regex numeric pass over 13,224 texts is fine; the LLM behavioral pass is not auto-run. |
| Extend Screener or add any vendor feed | Doctrine #2/#8: primary sources ONLY (NSE/BSE/SEBI/XBRL). Screener→fundamentals is a frozen legacy exception being migrated, not extended. |
| Build any 24y quarterly-velocity claim | Quarterly archive is a 12-quarter 2023-cliff (TTM 5.6% populated). 24y dynamics = ANNUAL only. |
| Audit `ratio_rows` for space or claim ~0.5GB from dead columns | `ratio_rows` = 486K not 286M (premise ~588× wrong). Real target = ~6.4GB re-derivable stock/mep/cpr + ~4.3GB over-indexing. Never touch raw bhav (doctrine #6). |
| Treat distress-spiral / SAST composite as a signal or gate | SAST INVOKE n=8; distress-spiral 589-row/102-symbol; pledge overlap 46/187 — board only; widen after ~Jul-21, then pre-register. |
| Put alpha language in any `/v1` envelope or claim forward estimates | No forward consensus/estimates, no ranked net-of-cost alpha, no multi-year insider depth exist. Wedge = evidence sold as a feed; ranked-alpha stays CANNOT-COMPETE until realistic-cost fundability is proven. |
| Expect weight-change index events or expiry max-pain pinning | `weight_pct` 100% NULL → weight-change events impossible (inclusion events are fine). max_pain does NOT pin into expiry (fails its base-rate control). |
| Naively sum reg29 flow or blend SHP % with SAST encumb % | reg29 inter-se legs carry pct_acq=0.0 with real pct_after → sums double-count; anchor on pct_after LEVELS per acquirer_hash. SHP pledge % (of promoter) ≠ SAST encumb % (of equity). |

---

## 8. Build plan (architect)

Sixteen build units. `Store`: OR=on-read · NS-B=nightly-bounded-snapshot · BB=bounded-backfill · REMOVE. `Seq` = suggested order.

| # | Build unit | Covers (ids) | Store | Size | Seq |
|---|---|---|---|---|---|
| **10** | **Canonical cross-DB recipe + rename-boundary fix** (`src/core/crossdb.py`: ATTACH ?mode=ro + `security_master.canonical()` before join; theme_rs siblings) | plumb:rename-boundary, plumb:canonical-crossdb, plumb:theme-rs-rotation | OR | S | **1st** |
| **9** | **Empty-table adjudication** — wire corp_actions.fetch_all (un-empties corporate_actions AND security_events), signal_events, mtf, concall_coverage | plumb:empty-table, dq:corp-actions-dead-pipe, corpus:coverage-ledger | NS/BB | M | early |
| **2** | **Stop-write dead columns** (~0.5GB; grep-gate each; keep the 2 read RS bools) | micro:dead-dozen-cols | REMOVE | S | early |
| **8** | **Concall timestamp backfill** — `transcript_publish_dt`/`concall_dt` from BSE feed (primary-source, no LLM) | corpus:pit-empty | BB | M | before 11 |
| **1** | **Delivery-tape descriptive engine** (`tape_descriptors.py` + `/dash/tape`): gap/absorption/ticket/capacity/deliv-pctile/SERIES_CHANGE | micro:gap-deliv, absorption, ticket, amihud-capacity, deliv-pctile, series-event, strat:amihud-per-name | OR (+security_events BB) | M | after 9 |
| **3** | **Ownership & flow layer** (`ownership_flow.py` + `/dash/ownership`): aggregators, velocity, pledge-union, clusters, fingerprint, distress, tie-out | own:unwired-aggregators, shp-velocity, pledge-union, cluster-tape, deals-fingerprint, distress-spiral, dq:promoter-flow-recon, plumb:shp-sast-recon | NS-B (~1K) + OR | L | after 10 |
| **7** | **Corporate-events & credit ledgers** (`event_ledgers.py` + `/dash/ledgers`): promise-reliability, candor, credit-dispersion (ISIN-dedup), gov-stress, season-clock | event:promise-ledger, street-value-empty, credit-tape-stub, gov-stress-join, season-clock, cohort-null, funda:restatement-count, dq:rating-migration | OR | L | after 10 |
| **11** | **Concall mention graph + orphan-profile** (`concall_mentions.py`; regex numeric pass; render business_brief) | corpus:mention-graph, orphan-profile, extract-backlog | mention_tape (stored) + OR | M | after 8 |
| **12** | **PIT-fundamentals ledgers** (`funda_ledgers.py`): growth-streak, accrual-proxy, orphan-ratios, QG-lift, bank-NIM, pit_confidence footer | funda:growth-streak, no-cfo-accrual, orphan-metrics, qg-lift, bank-season, pit-lag-truth, quarterly-cliff | OR (asset_growth_yoy → fund_panel BB) | L | parallel |
| **6** | **Derivatives positioning descriptors** (`fno_view.py` + `fno_descriptors.py`): OI×delivery, quadrant ribbon, basis, noise-map | posn:oi-x-deliv, quadrant, maxpain, participant-oi | OR | M | after 5 |
| **5** | **FII/DII + near-month F&O backfills** (`fii_dii_archive.py`, `fno_fut_history.py`; repurpose 5 dead cols) | own:fii-dii-backfill, posn:fut-backfill-10y, dormant-cols | fii_dii append + ~675K BB | L | infra |
| **15** | **Index/regime boards** (`regime_board.py` + `/dash/regime`; `breadth_series.py`): valuation-band, breadth-series, phase-transition, regime-overlay, membership, coverage-gaps, ignition-journey, launchpad-score | regime:valuation/breadth/phase/overlay/membership/coverage-gaps, strat:ignition-tables, lab:launchpad, delivery-absent | OR (+breadth ~3.5K NS-B) | L | parallel |
| **13** | **B2B data-wedge product layer** (`/v1` activation; Kept-Word ledger; lag-SLA; gov-stress; defensibility) | prod:v1-activation, kept-word, provenance-lag, gov-stress-tape, defensibility, expectations-concealment, plumb:mgmt-batting-avg | NS-B aggregates + OR | L | after 7 |
| **14** | **DQ expansion + storage reclaim + ledger integrity** (`data_quality.py` extend; `bounded_snapshot_reclaim.py`; 2 missing strategy_runs rows; advance label frontier; accum_screen reconcile) | dq:dq-battery-blind, storage-real-target, ratio-rows-correction, survivorship-99pct, pit-leak-measured, table-census, lab:ledger-missing, label-recipe, staleness, accum-screen | NET REDUCTION | L | with 9, after 2 |
| **16** | **Experiment gatekeeper** (research-side: rating_overlay, cost_recut, regime_cond, sleeve_orthogonality, survivorship_recut, quality_cond_launch) | strat:rating-overlay, cblend-not-cost-real, valuation-regime, momentum-collinear, rs-gradient, lab:combined-panel, dq:survivorship | strategy_runs rows | L | **last** |
| **4** | **Promoter-conviction / insider-drift studies** (`research/explosive_moves/insider_drift.py`) | own:insider-drift-study, plumb:insider-tape-forward | strategy_runs + descriptive tape | M | research-side |

**Architect global notes (binding):**

- **Dead-column correctness gate:** grep-verified droppable = `avg_dvpt_5d/10d/30d/60d/90d/180d/365d`, `total_value_today`, `ratio_today_vs_avg_30d`, `rs_vs_sector_above_50ma`, `rs_vs_sector_new_52w_high`. **DO NOT DROP** `rs_vs_sector_above_200ma` / `rs_vs_broad_new_52w_high` — both read. Repo-wide grep assertion per column before dropping.
- **DB placement:** hermes.db owns the operational/EOD estate + concall/insider/sast/credit; research.db owns the lab estate + `shareholding_history` + `strategy_*`. Cross-DB reads use ATTACH ?mode=ro (BUILD-10); writes always through `get_conn()` to hermes.db.
- **Only 4 new stored objects** are justified against the 16GB mandate: `ownership_flow_snapshot` (~1K nightly, C-column precedent), `concall_mention_tape` (a graph/scan target), `breadth_series` (~3.5K <1MB, un-reconstructable series), `security_events` SERIES_CHANGE + corp-action events (bounded event stream). `asset_growth_yoy` is the only new `fund_panel` column. Everything else OR or bounded latest-date snapshot.
- **Storage census correction:** `ratio_rows` 486K not 286M — redirect the space audit to the real ~6.4GB re-derivable stock/mep/cpr + the ~4.3GB index diet; keep raw bhav intact.
- **PIT prerequisite (blocking):** BUILD-8 must date transcripts BEFORE any text overlay (BUILD-11) or forward-tilt claim is honest.
- **In-flight complements (do NOT duplicate):** `pead.py` (SUE×day-0 delivery); shareholding deep-history crawl (Reg-31 ~Jul-21 widens); the ~Jul-09 XBRL+banks season (Provisions one-liner is time-critical); AUD-10 momentum_scan re-run (verify — it is fresher than the note implies, nightly since 2026-07-01).
- **Ops discipline:** all new nightly timers sandboxed (ProtectSystem=strict, ReadWritePaths=/opt/hermes /var/log, jitter); NEVER `systemctl start` a hermes timer mid-day; network fetchers NEVER hold a write txn across I/O; paid LLM/data spend is surface-first to Ramana, cheap-model only.

---

## 9. Surface plan (UI/UX)

**Ruthless verdict:** of ~60 candidates, only ~7 earn a genuine visual; the rest are Screen+ columns, dossier fact-chips, or monitors. The dominant pattern is "built-and-tested, surfaced nowhere" — the highest-leverage design work is **one-line renders + columns + fact-strips wiring EXISTING data onto surfaces that already exist**, not new pages.

### 9a. The ~7 earned visuals

| Surface | What earns the visual | Placement | Key glossary |
|---|---|---|---|
| **PIT-provenance lag-SLA strip** | one horizontal lag-distribution strip per data-class (p50–p95 band + max whisker + leak-rate %, colored real/calibrated/modeled) — the "87% leak measured-and-neutralised" story in one row-per-class chart. THE credibility artifact. | Trust → `/dash/coverage` + replay-the-tape footer + every `/v1` `_meta` | pit_confidence, lag_error_days, leak_rate, knowable_at, coverage_by_status |
| **Kept-Word promise term-structure** | per-symbol horizon-axis bar of GA% showing the down-sloping reliability-with-horizon curve — "keeps near promises, misses far ones" at a glance | Strategies → Credibility (`/dash/concalls`) + #cci dossier fact | kept_word_score/GA%, hedge_index, avg_signed_variance, settled guidance |
| **Governance distress small-multiple** | for a flagged name, 3 stacked mini-bars (pledge stock %, pledge-flow net, drawdown from 52wH) on one time axis — the "2 fires + 1 early-warning" composite; coverage-cliff badge where 102-symbol pledge runs out | Strategies → Governance-risk lens | governance_stress_index, distress_spiral, pledge INVOKE/CREATE, promoter_flow_tie_out |
| **Sector regime grid** | rows=sectors, 3 columns (rotation-phase glyph, valuation-band %ile heat cell, breadth %-above-200MA bar) — the never-crossed valuation×phase×breadth read; + net-highs breadth tape on Overview | Markets → Regime board (`/dash/markets/regime`) | valuation band, breadth_series/net_highs, regime_overlay, phase dwell/transition |
| **Growth-persistence survival curve** | P(survive next year \| current streak) from the measured 24y curve — "17% survive yr3, 4% yr5" as one decay line, the stock's streak marked | Growth (`/dash/growth`) + #qual dossier | growth_streak_age/survival, wc_accrual_proxy, asset_growth_yoy, qg_component_lift |
| **OI×delivery conviction 2×2** | {OI up/down} × {delivery spike/normal} → CONVICTION_LONG / LEVERAGE_CHURN / SHORT_CONVICTION — the one cell where positioning leads (only 25% of OI-up days "real"); quadrant path ribbon beside it | Markets → Participants (`/dash/participants`) + #fno dossier | OI×delivery conviction, fno quadrant, basis_pct, max_pain (no expiry pin), participant_oi noise-map |
| **Sleeve-orthogonality matrix** | mean-abs-rank-diff heatmap between riskadj/ensemble/C-blend — shows C is the ONLY orthogonal sleeve, momentum headroom ≈ 0; the visual that governs what earns a test slot; + ignition time-to-MFE bucket cards | Trust → Strategy validation (`/dash/testing`) + Strategist | strategy_runs, sleeve orthogonality, rating drift CAR, ignition time-to-MFE |

### 9b. Column / fact-chip / monitor surfaces (no visual)

- **Ownership-flow columns** (Screen+ + #pos dossier): aggregators, velocity, clusters, pledge-union — with the deals `client_key` schema-lock action.
- **Microstructure character columns**: gap-character, ticket_ratio, deliv_pctile, absorption preset, quiet-coil flag — every return claim BLOCKED as base-rate.
- **Tradability/capacity chip**: cap_cr per name (impact_bps, days_to_build) — the flat-cost-illusion antidote.
- **Management-candor column** (beside Kept-Word): sandbag-vs-spin, incl. 1,271 CONCEALED — surprise-vs-street is dead.
- **PIT-provenance monitors** (data_quality.py, no page): corp_actions freshness, SAST-sanity, rowcount-floor — the "monitors-never-pages" audit theme.
- **Stop-writes + reclaim** (DB hygiene, no surface).
- **Defensibility scorecard** (Trust → Coverage): win vs cannot-compete positioning matrix; ranked-alpha stays cannot-compete.

### 9c. UI/UX global notes

- **Gap #2:** Screen+ column-controls (`table_controls._PAGES`) cover ONLY `stocks`. Extending `_PAGES` to cockpit tables + classic screener (AUD-71) is the single biggest structural unlock — it lets a dozen descriptive columns land WITHOUT new pages.
- **Gap #3:** dossier tabs mostly show a table, not a FACT STRIP. A reusable **dossier-fact-chip primitive** (the C capital-allocation fact is the only one that exists) drains ~15 per-symbol facts (kept-word, candor, growth-streak, capacity, gap-character, business_brief, ownership velocity).
- **Gap #4:** provenance/PIT honesty is computed but surfaced almost nowhere — wiring the `pit_confidence` stamp + lag-SLA card converts the project's best defensibility asset from prose into a visible, sellable layer.
- **Placement vocab** (anchored to `lens_registry.py`): 4 altitudes markets/screener/strategies/tracker + Trust; every page = `/dash/<workspace>/<page>` via `nested_nav`; a NEW page = add a Lens record, never an orphan URL. New destinations: Markets→Regime, Strategies→Governance-risk. Glossary keys = family-grouped bullets in `docs/metrics-glossary.md` (parsed by `G.gloss()` for `?` popovers).
- **Discipline guardrail:** descriptive-first is the ledger, not a style choice. The UI must render every "strategy" as a column/tape/study-card, NEVER a ranked gate, or it re-sells the flat-cost illusion the ledger exists to prevent.

---

## 10. The program

### 10a. Quick wins (season-gated first)

1. **Fix the Provisions extractor BEFORE ~Jul-09** — one line (`put('Provisions', prov)` in `extract_bank_for`) makes `credit_cost_ratio` formable; miss the window and thousands of bank rows land without it. `[funda:bank-season-credit-cost-gap]`
2. **Lock deals `client_key` normalization NOW** — every day unlocked loses joinable history. `[own:deals-fingerprint]`
3. **Append the 2 missing `strategy_runs` rows** (C-BLEND 1.32 champion + PEAD 0.10 failure) — failures are blocking and belong in the DB. `[lab:ledger-db-missing-champion]`
4. **Surface the 3,797 orphaned business_briefs** — one template line, zero new storage. `[corpus:orphan-profile]`
5. **Drop the verified zero-reader `stock_signals` columns** (grep-gated; NOT the 2 read RS bools). `[micro:dead-dozen-cols]`
6. **Record the corrected data census in PROJECT_STATE** — `ratio_rows` 486K not 286M; redirect the space audit. `[regime:ratio-rows-correction, dq:storage-real-target]`
7. **Add the 18 dormant thematics to the capture/RRG allowlist** — free coverage on the next nightly. `[regime:coverage-gaps]`

### 10b. Strategic builds

Foundation (BUILD-10 canonical cross-DB + BUILD-9 empty-pipe fills + BUILD-14 DQ expansion) is the correctness floor everything stands on. Then: concall timestamp backfill (the PIT prerequisite) → descriptive product wedge (event ledgers + Kept-Word + candor + gov-stress, then `/v1` behind the flag with `/coverage` + `/provenance/registry` FIRST, then `/promises`) → descriptive surface layers (ownership, delivery-tape, regime boards, PIT-fundamentals ledgers) → primary-source backfills (FII/DII + 10y near-month F&O) → the experiment gatekeeper.

### 10c. Product plays

- **Kept-Word promise-reliability ledger** as the day-one `/v1` SKU (`/v1/securities/{sym}/promises`) — 5,225 resolved claims / 541 names, per-symbol horizon term-structure. Descriptive-only (Gate B failed).
- **Self-audited provenance as the compliance product** — publish the measured 87% leak-rate + the built `knowable_at` fix; a per-class lag-SLA card + survivorship `coverage_by_status`. Ship `/coverage` + `/provenance/registry` FIRST.
- **Management-candor axis + governance-stress tape** — the PIT-clean substitute for the dead surprise-vs-street concept; coverage-cliff badged.
- **Defensibility & pricing scorecard** — win axes vs cannot-compete; ranked-alpha stays cannot-compete until realistic-cost fundability is proven; price to analyst-hours.

### 10d. Sequence

1. **Foundation first** — BUILD-10 canonical cross-DB + rename fix; wire corp_actions/signal_events/coverage (BUILD-9); expand DQ (freshness+rowcount-floor+SAST-sanity, BUILD-14); record the corrected census.
2. **Season-gated quick wins** (before ~Jul-09) — Provisions extractor; deals client_key; 2 strategy_runs rows; orphaned briefs; dead-column drop; 18 thematics allowlist.
3. **PIT prerequisite** — concall timestamp backfill (BUILD-8), parallel with the ~Jul-09 ramp so new transcripts land dated.
4. **Descriptive product wedge** (depends on 1) — event/credit ledgers + Kept-Word + candor + gov-stress; flip `/v1` (BUILD-13); publish lag-SLA + defensibility scorecard.
5. **Descriptive surface layers** (parallel, depend on 1) — ownership; delivery-tape (SERIES_CHANGE after security_events adjudicated); regime boards; PIT-fundamentals ledgers.
6. **Primary-source backfill infra** — FII/DII + 10y near-month F&O (network-safe, per-file commits); positioning descriptors ship on 2y now.
7. **Reg-31 flood (~Jul-21) milestone** — shareholding real-date capture heals; widen ownership/governance coverage; extend lag-calibration to shareholding; only THEN pre-register any SHP×SAST study.
8. **Experiment gatekeeper** (research-side, on-request, all pre-registered) — FIRST settle `strat:cblend-not-cost-real` (cost-reality + survivorship re-cut); then sleeve-orthogonality routing; then rating-action drift (sample-reconciled), insider-drift, valuation-regime, fundamental-CHANGE composite.
9. **Storage reclaim** (after step 2's drop, coordinated on the shared tree) — bounded-snapshot reclaim of the real ~6.4GB + the index diet; never touch raw bhav.

---

## 11. Open questions

Genuine unresolved forks, doctrine conflicts, and decisions Ramana owns.

1. **The champion bar's fundability is unproven and must be settled before any book claim.** Every specialist cites net Sharpe 1.32 as "the bar," but it is FLAT-cost and has never run through `cost_participation.py`. Until the cost-reality re-cut runs (§6), the strategy leaderboard's fundability ranking — including what `/dash/testing` shows — is not trustworthy. **Doctrine wins:** treat 1.32 as flat-cost-only in all copy until re-cut.
2. **Which specialist count is canonical?** Two live counts differ across reports (pledge 559 vs 589; insider 10,008 consistently but brief said 16.3K; concall 24,088 consistently). Root cause: live appends between batches + a drifted brief. The `table_census` nightly (BUILD-14) is the fix; until it lands, PROJECT_STATE should carry the floor numbers in §2 and stop citing the brief.
3. **mep/cpr full-history compute-on-read (~4.3GB) — Ramana decision.** The dq auditor explicitly declines to act unilaterally; the index diet (~2–2.5GB, zero row deletion) is safe to do, but dropping mep/cpr history bodies is a doctrine-#5 judgment call that touches issue-date backtest reproducibility. **Surface-first.**
4. **The ~₹900–1,700 LLM concall backlog close — paid spend, surface-first.** The FREE regex numeric pass is fine now; the behavioral-axis LLM pass (credibility/candor) requires Ramana's sign-off (guardrail #0) and cheap-model discipline (doctrine #7). Gemini Flash-Lite pricing is an external estimate — re-verify before any decision.
5. **Data-licensing/redistribution posture is unresolved and is the procurement deal-killer** for the B2B wedge. Ramana-owned. Also: the 98.6%-Screener-discovered concall taint must carry a disclosure line wherever guidance surfaces (doctrine #8) — this is the specific limit to volunteer in the pitch.
6. **`corporate_actions` resurrection source.** The dead NSE archive CSVs 404 permanently. The fix must use a PRIMARY source that works — the BSE-announcements pattern (`concall_bse.py`) or NSE's current corporate-actions endpoint — NOT the dead archive (doctrine #2), and NOT `setup-news.sh` on the VPS (AUD-28 ban). The inferred-action tape from `adjust.py` factors is the honest interim.
7. **Discrepancy — the `capacity_cr=30` scalar vs the ~₹141cr weakest-link book estimate.** The microstructure and strategist reports frame capacity differently (per-name amihud decomposition → ~940 fundable names, vs the monthly-turnover-limited ₹30cr record vs a ₹141cr weakest-link at 10% POV). These are not contradictory but must be reconciled into ONE cost model before any fundable claim; `cap_cr` (BUILD-1) must match `cost_participation.py` (BUILD-16) exactly.
8. **`security_master` has one impossible row** (INACTIVE + currently_listed=1) and 12 fundamentals rows with absurd report-lags (+2,649d) — both untested by the current battery. Minor, but they belong in the DQ sanity-floor expansion.
9. **AUD-10 may be stale-as-briefed.** momentum_scan is nightly since 2026-07-01 (fresher than the AUD-10 note); `ensemble_pctile` may nonetheless be stale from the frozen seed. Verify (kickstart-pick-verify) before re-running.
