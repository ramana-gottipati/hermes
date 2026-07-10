# patearn — 14-Pattern Fundamental Quality Methodology — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** DEPLOYED analytical lens (PIT quality score; not run as standalone alpha) · **Governing decision(s):** D66 (PIT score = risk-filter, not alpha) · D76 (capital-allocation "C" lens) · supporting D7 (rule-based Stage-1, not LLM) · D8 (no bulk pre-scrape) · D24 (financial-sector adaptation) · D46 (bounded batch scoring) · D78/D82 (primary-source XBRL migration) · **Reconciled:** 2026-07-11 (S109).
> **Charter:** the single canonical definition + current-state reference for patearn. Methodology of record: [resources/patearn/SKILL.md](../../resources/patearn/SKILL.md) + [patterns.md](../../resources/patearn/patterns.md). Numbers/weights live in code + [calculations-and-weights.md](../calculations-and-weights.md); this page never restates pattern math — it links (proprietary IP).

**One-line definition:** patearn is Hermes/Patearn's rule-based, point-in-time **14-pattern fundamental-quality score** for Indian equities — the pure-Python **Stage-1 selection lens** that reads capital efficiency, operating leverage, balance-sheet strength, valuation asymmetry and ten further quality patterns, gates out governance/leverage blow-ups via five **hard disqualifiers**, and surfaces the handful of names worth a human deep-dive.

---

## 1. What it is

patearn is the project's **core analytical lens and namesake** — the methodology after which the whole platform is named. It is a disciplined process for identifying Indian **mid-cap multi-baggers *before* institutional re-rating**, built explicitly to override the intuitive shortcuts that cause most investment mistakes: buying a loud narrative, rationalising away a governance red flag, or confusing price momentum with a live thesis.

Operationally it is two things working together:

1. **A rule-based quantitative score (Phase 3).** Every surviving company is scored on **14 patterns × 3 signals each**, each signal graded No / Partial / Yes, weighted, and rolled into a single **Normalised Score (NS, 0–100)** with a mandatory sensitivity band, a **Pattern Activation Count (PAC)**, a **Quality-Gate** floor on the fundamental core, and a **tier** (T1 → T4, or DISQUALIFIED). This is what [`src/automation/scoring.py`](../../src/automation/scoring.py) implements — **pure Python, no LLM** (Guardrail #4 / D7).
2. **A qualitative process wrapper (the 6 phases).** Universe construction → hard filter → quantitative score → qualitative deep dive → entry & sizing → monitoring/exit. The score *surfaces* candidates; human judgment in claude.ai (Phase 4) *verifies* whether the story is real.

The governing empirical finding (**D66**) is the one everyone must internalise: **the patearn score is a RISK FILTER, not a return ranker.** In the survivorship-aware point-in-time backtest, blow-up rate (>50% loss / 12m) falls monotonically as tier improves, while the long-short return of the score itself is ≈ 0. patearn tells you what *not* to own and what is *high-quality enough* to own — the return engine is momentum/accumulation (see [momentum-riskadj.md](./momentum-riskadj.md)).

## 2. Our variation vs. the standard technique

Generic fundamental screening (a Piotroski F-Score, a Magic-Formula rank, a "high-ROCE-low-PE" filter) is a **static, single-snapshot, count-of-good-things** exercise. patearn deliberately departs on five axes, and the departures are the proprietary part:

- **14 hand-designed patterns, not a generic factor bundle.** Each pattern encodes a *specific* thesis about how an Indian mid-cap re-rates (operating leverage as the re-rating engine; a *named, funded, time-bounded* policy tailwind rather than a vague "sector story"; export inflection into premium markets; institutional *neglect* as the opportunity window; promoter *accumulation* while institutions capitulate). The 3-signal / Yes-Partial-No rubric and per-pattern weights are defined in [patterns.md](../../resources/patearn/patterns.md).
- **Point-in-time (PIT) rigor.** Trends beat snapshots — rising ROCE 12→16→22% is a stronger signal than a static 22%. The PIT reader ([`fundamentals_asof.py`](../../src/automation/fundamentals_asof.py)) reconstructs exactly what was *knowable* at each historical date (report-lag-safe), so the score can be backtested with no look-ahead (**D66**).
- **Value in rupees, never share count.** Every cross-time metric is measured in rupees (capital employed, operating profit, PAT), and dilution is measured *directly* (PAT-CAGR − EPS-CAGR, or equity-capital CAGR) rather than normalised away — this eliminates a whole class of corporate-action-adjustment bugs (Guardrail #5; realised in the "C" lens, §7).
- **Hard disqualifiers are binary, not soft warnings.** Five conditions (governance/leverage) *disqualify* a name regardless of how good the rest of the score is. The framework exists precisely to make "but the tailwind is so strong" un-actionable in real time.
- **The multi-bagger-*before*-re-rating thesis.** The universe is bounded to a mid-cap band (roughly ₹500 Cr–₹15,000 Cr) — small enough that the re-rating has *not* already happened, large enough to be liquid and data-covered. A name that has already run >200% caps at a low tier: you'd be buying the story, not the setup.

The calibration benchmark for a Tier-1 setup is **Apar Industries FY2021** (≈₹350, pre-~34× move), scored from public disclosures only — documented in [SKILL.md](../../resources/patearn/SKILL.md) § Calibration Standard.

## 3. How it works (methodology)

The full mechanism lives in [SKILL.md](../../resources/patearn/SKILL.md) (process) and [patterns.md](../../resources/patearn/patterns.md) (per-signal criteria). Conceptual summary only here — **exact weights, thresholds, and the normalisation math are IP and are NOT restated on this page.**

**The 6-phase process (mandatory sequence, no phase skipped):**

| Phase | Cadence | What happens | Where it runs |
|---|---|---|---|
| 1 · Universe construction | Quarterly | Bound the mid-cap pond; tag against active policy cycles (Power T&D, Defence, Renewables, Semis, Railways, Water, Export mfg, Healthcare); keep a graveyard list (survivorship discipline) | methodology |
| 2 · Hard filter | Quarterly | Apply the 5 hard disqualifiers + rising-receivables + SEBI-action screens; expect ~40–50% elimination | rule-based |
| 3 · Quantitative score | Quarterly (post-results) | Score the survivors on the 14 patterns → NS, tier, QG, PAC, sensitivity band; surface top ~20–30 | **`scoring.py` (pure Python)** |
| 4 · Qualitative deep dive | Monthly (shortlist only) | Read 8 concalls, segment margins, CFO/PAT, auditor report; **bear case written first**; 3 exit tripwires | **claude.ai + patearn skill** (not the API — cost control, D18) |
| 5 · Entry & sizing | On decision | Entry Math (implied CAGR); size by tier; record a 3-sentence thesis + written tripwires | methodology |
| 6 · Monitoring & exit | Quarterly | Re-score; re-check disqualifiers; classify each holding Hold / Trim / Re-evaluate / Exit | [exit-protocol.md](../../resources/patearn/exit-protocol.md) |

**The 14 patterns (conceptual grouping; math in [patterns.md](../../resources/patearn/patterns.md)):**

- **Fundamental core (the top-5 Quality Gate):** ROCE/ROE trajectory · operating leverage (EPS growing faster than revenue) · structural sectoral tailwind (named + funded + time-bounded) · valuation asymmetry · balance-sheet deleveraging. These carry the highest weights, and a name that fails a **Quality-Gate floor** on this group *cannot* reach the top tier no matter how good its technical or ownership signals look — this stops "a perfect chart with mediocre fundamentals" from masquerading as a multi-bagger setup.
- **Business-quality patterns:** product/revenue-mix premiumisation · capex-cycle completion (FCF now being generated) · promoter/insider accumulation · export/global-revenue expansion · institutional neglect (FII at multi-year low, thin analyst coverage).
- **Technical / stage patterns (⚠ chart-check required, scored Estimated unless real ATR/RS/volume data is pulled):** tight base / VCP breakout · relative strength & stage-of-move.
- **Discipline patterns:** working-capital efficiency · management quality & disclosure.

**Scoring architecture (mechanisms named, constants withheld):** each signal is graded No/Partial/Yes; signals not sourced from a citable document are tagged *unverified* and **discounted** (they count, but less); the weighted sum is normalised to a 0–100 **NS**; a mandatory **pessimistic / base / optimistic sensitivity band** is always reported; **PAC** counts how many of the 14 patterns are active (breadth check); the **Quality Gate** enforces a floor on the fundamental core; and names are placed into tiers **T1 (strong) → T2 → T3 → T4 (watch)**, or **DISQUALIFIED**. A name that has already run >200% in 24 months is tier-capped. The exact weights, thresholds, MAX score, unverified-discount factor and tier cutoffs are in [`scoring.py`](../../src/automation/scoring.py) + [calculations-and-weights.md](../calculations-and-weights.md).

**The 5 hard disqualifiers (binary, non-negotiable — surfaced, not hidden):** promoter pledge over the limit · net D/E too high *and still rising* · CFO negative for 2+ consecutive years · auditor resignation/qualification/unexplained change · related-party transactions too large a share of revenue. Any one fires → DISQUALIFIED, logged, no entry. Rationale and the six Indian mid-cap failure case studies (Vakrangee, Manpasand, Suzlon, Aban, PC Jeweller, Yes Bank) that motivate them: [failures.md](../../resources/patearn/failures.md).

**What the code can and cannot see:** `scoring.py` runs the *quantitative* Phase-3 score over numeric fundamentals. The patterns that need narrative/segment/technical inputs (tailwind, export mix, VCP, volume) it scores conservatively as **Partial-Estimated** and hands off to Phase 4 in claude.ai. Where a real point-in-time trend key is available (ROCE trend, OPM trend, interest coverage, profit acceleration, debtor days, cash-conversion cycle, promoter-rising — D66), the corresponding signals switch from proxy to **verified**; the live Telegram snapshot path (no trend keys) is byte-for-byte unchanged (regression-safe).

## 4. Status, validation & honesty fence

- **Deployed** and running (Telegram `/pt14`, nightly batch scoring, web dossier + screener). See §5.
- **PIT-backtestable, and backtested** — but **not validated as standalone alpha.** The honest read (D66, survivorship-aware, overlapping monthly observations, descriptive — *not* significance-tested): the score is a **risk filter**. Blow-up rate falls monotonically by tier (T2 → T3 → T4 → DISQ); **NS long-short ≈ 0**. Returns came from accumulation/RS (top-tercile delivery-drift ≈ 11% median 12m vs ~5% weak), and the sweet spot was **strong accumulation × good patearn quality** (≈11% median / 60% hit / ~2% blow-up).
- **T1 never forms in the pure-quant path** — NS caps in the low-60s because the tailwind/export/VCP/volume patterns stay Estimated. A T1-capable machine score would require folding the technical-confirmation patterns into the scorer; today T1 is a claude.ai Phase-4 judgment, not a machine output.
- **The asset is the lens, not a return edge.** Per the [patearn-charter](../patearn-charter.md): the durable product is **PIT rigor + under-covered primary data + the analytical selection lens** — an evidence machine — *not* a backtested alpha strategy. Do **not** claim a validated return edge for the score itself. It ranks/compares on reproducible, measurable inputs only (D61); interpretive content informs but never ranks.
- **"C" (capital-allocation) consumption:** the modern quality composite (§7) is used as a **blend/tilt** and a percentile lens — it **subsumes** the older ad-hoc 4-metric quality read but is **never a hard veto or a standalone ranker** (D66 keeps the C/A/B data lenses veto-/filter-only). Where C is actually consumed inside a return construct (the quality × momentum blend) is documented in [momentum-riskadj.md](./momentum-riskadj.md).

## 5. Where it lives (code · routes · DB · timers)

**Code**
- [`src/automation/scoring.py`](../../src/automation/scoring.py) — the rule-based 14-pattern scorer (Phase 3). `score_fundamentals()`, hard-disqualifier check, sensitivity band, QG, tier, Telegram formatter.
- [`src/automation/capital_allocation.py`](../../src/automation/capital_allocation.py) — the "C" capital-allocation quality composite (ROIIC, ROCE level+trend, dilution drag, debt-funding share, growth efficiency), PIT-safe, with a separate `model='financial'` path for lenders.
- [`src/automation/fundamentals_asof.py`](../../src/automation/fundamentals_asof.py) — point-in-time fundamentals reader (research.db → scorer dict; no look-ahead; provides the real trend keys).
- [`src/automation/score_batch.py`](../../src/automation/score_batch.py) — bounded, prioritized batch scorer for *surfaced* names only (D46; honors D8 — never a bulk 5,000-stock scrape).
- [`src/automation/news_feed.py`](../../src/automation/news_feed.py) — twice-daily poller; EARNINGS items trigger the Stage-1 rule-based score.
- [`src/assistant/patearn.py`](../../src/assistant/patearn.py) — the patearn system prompt + Haiku/Sonnet wrapper for the `/analyze` deep path.

**Telegram commands** (full table: [PROJECT_STATE.md](../../PROJECT_STATE.md) § Telegram bot commands)
- `/pt14 TICKER` — rule-based 14-pattern score (₹0, no LLM).
- `/analyze TICKER` — full Haiku patearn analysis (use sparingly, ~₹2).
- `/conviction` — cross-pillar shortlist; pt14 quality shown as a ★ confirmation.

**Web routes (`/dash`)**
- Per-stock **pt14 card / dossier** on the stock page (reads cached `pattern_scores`).
- **Screener** column-groups + the **Conviction** shortlist (`/dash/conviction`, D45) — pt14 is surfaced as **confirmation, not a gate** (LEFT JOIN; a ★ marks quality-confirmed, ✗ flags hard-disqualified).

**DB tables** ([`src/core/db.py`](../../src/core/db.py))
- `pattern_scores` — id, symbol, scored_at, pws, ns_base/pessimistic/optimistic, pac, tier, qg_pass, hard_disqualified, disqualifier_reasons, detail_json.
- `capital_allocation_scores` (D76) — ca_score, ca_pctile, ca_tier, model, roiic, roce_latest/avg/trend, roe_latest, roa_latest, dilution_drag, debt_funding_share, growth_efficiency, coverage, detail_json. `UNIQUE(symbol, as_of)`; module-owned schema; PIT-safe.
- `fundamentals` / `fundamentals_history` — the inputs (see §6).

**Timers (systemd on the VPS)**
- `hermes-pt14batch.timer` — daily bounded batch pt14 scoring of surfaced names (D46), after the signals chain.
- `capital_allocation` batch — `python -m src.automation.capital_allocation --backfill` (validated live 2026-07-01, 1,900 names; **not yet nightly-wired** — see §9).
- Nightly XBRL fundamentals ingest + shareholding-pattern XBRL timer (16:45) feed the inputs (D78/D82/D79).

## 6. Data & provenance

**Bhav copy + delivery = primary source.** NSE bhav copy (prices, volumes, delivery), the rolling delivery-value-per-trade signals, and the point-in-time price chain are all authentic NSE data. No concern here.

**Fundamentals = the KNOWN primary-sources exception, under active remediation. Disclose this wherever the score is shown.**

- patearn's fundamentals historically came via [`src/automation/screener.py`](../../src/automation/screener.py) → Screener.in. This is the **copyright-risk exception** flagged by **Guardrail #8** (primary sources only: NSE/BSE/SEBI/XBRL). **Do not extend the Screener dependency.**
- **The standing remediation (D78, session 73):** fundamentals move to **primary-source NSE-XBRL forward ingest** — the same financial-results XBRL documents the regulator receives — with a per-symbol **series-continuity gate** (a symbol is only appended once its recent XBRL filings reconcile with the historical series on the rupee core, so restated/netted definitions can't corrupt cross-boundary CAGRs). Every row carries a `source` tag (`NSE-XBRL-CONSO`/`-SA`; NULL = the frozen Screener era). **D82 (session 75)** extended this to banks/lenders via tag-detection mapping; the shareholding-pattern XBRL feed adds PIT promoter/FII/DII/pledge.
- **The legacy Screener series is FROZEN** — kept for history, **never re-scraped for new coverage**. New coverage arrives only through the XBRL path.
- **Remaining:** Phase 3 = historical backfill, then **delete `screener.py`** entirely. Full design + reconciliation evidence: [docs/fundamentals-xbrl-migration.md](../fundamentals-xbrl-migration.md).
- The 24-year historical archive (`research.db.fundamentals_history`, ~1,983 syms × 2002–2026) that powers the PIT backtest and the "C" lens is treated as a frozen, PIT-safe base — see memory `fundamentals-archive-built`.

## 7. Terminology canon

- **patearn** — the methodology and its 14-pattern quality score (this page). The project's namesake analytical lens. Lower-case; a coined term (about *patterns* of *earnings*/quality).
- **The 14 patterns** — the hand-designed pattern set (ROCE trajectory … relative strength); definitions in [patterns.md](../../resources/patearn/patterns.md). Grouped into a fundamental core (the Quality-Gate five), business-quality, technical, and discipline patterns.
- **NS (Normalised Score)** — the 0–100 rolled-up patearn score, always reported with its pessimistic/base/optimistic band.
- **Quality Gate (QG)** — the floor a name must clear on the top-5 fundamental patterns to be tier-1-eligible.
- **PAC (Pattern Activation Count)** — how many of the 14 patterns are active; a breadth/robustness check alongside NS.
- **Tier** — T1 (strong) / T2 / T3 / T4 (watch) / **DISQUALIFIED**.
- **Hard disqualifier** — one of the five binary governance/leverage conditions that voids a name outright (≠ a soft "concern").
- **Stage-1 screen** — the pure-Python, rule-based quantitative pass (Phases 1–3). **NOT LLM-driven** (D7/Guardrail #4). Distinct from **Phase 4**, the qualitative claude.ai deep dive.
- **"C" (capital allocation)** — the modern derived quality composite ([`capital_allocation.py`](../../src/automation/capital_allocation.py)): has management compounded *incremental* rupee capital well (ROIIC, ROCE level+trend, dilution, debt-funding, growth efficiency), or just grown size? Consumed as a blend/tilt, never a standalone ranker.
- **⚠ Disambiguation — the patearn SCORE vs. the momentum ENGINE.** patearn is the **quality/risk-filter selection lens** (this page). It is **not** the return-generating construct. The momentum / risk-adjusted engine (where returns and the quality × momentum blend live) is a *separate* lens — see [momentum-riskadj.md](./momentum-riskadj.md). Keeping these two straight is load-bearing: D66 established that patearn *filters* and momentum *ranks*.

## 8. Decision & session history

- **D7 / D8** — Stage-1 screening is **rule-based Python, not LLM** (cost + precision + reproducibility); do **not** pre-scrape Screener for thousands of stocks — wait for results events, cache, grow incrementally.
- **D18** — Phase-4 deep analysis happens in **claude.ai under the $20/mo subscription, not the API** (deliberate cost control).
- **D24 / Doctrine D** — **sector-adapted patearn for financials** (HFC/NBFC/bank): ROCE→ROE/ROA, D/E gate replaced by GNPA/CAR/ALM, etc.; without adaptation lenders score misleadingly low. The "C" lens realises this with a data-intrinsic `model='financial'` path.
- **D45 / D46** — the **Conviction** cross-pillar shortlist (RS leader × accumulation × entry read, pt14 as ★ confirmation) + **bounded batch pt14 scoring** of surfaced names (lights up the Quality pillar without violating D8).
- **D61** — rank/compare on **measurable, reproducible** inputs only; interpretive content informs but never ranks.
- **D66 (session 37, 2026-06-23)** — **the pivotal decision.** PIT fundamentals → backtestable patearn score; the score is a **RISK FILTER, returns come from accumulation.** Blow-up rate falls by tier; NS long-short ≈ 0; sweet spot = accumulation × quality.
- **D76 (session 63, 2026-07-02)** — data-roadmap ROI: build **C** (capital-allocation) → A (insider/promoter) → B (credit ratings); C is a free derived layer over data already held. Validated live 2026-07-01 (Nestlé ~100, TCS 88 vs YesBank 21, JPPower 28); financials carve-out 2026-07-02.
- **D78 (session 73) / D82 (session 75)** — fundamentals go **primary-source NSE-XBRL** with a series-continuity gate; Screener history frozen; bank mapper added. The Guardrail-#8 remediation.

## 9. Open items / frozen work

- **XBRL migration, Phase 3 (the big one).** Historical backfill of NSE-XBRL fundamentals, then **delete `screener.py`**. Until then the Screener input remains the disclosed exception. Owner doc: [fundamentals-xbrl-migration.md](../fundamentals-xbrl-migration.md).
- **Nightly-wire the "C" batch.** `capital_allocation --backfill` is validated live but still run manually; wire it into the nightly chain (D79 wired the C/A/B *data* timers; the score batch itself is the residual).
- **T1-capable machine score.** Fold the technical-confirmation patterns (VCP, volume — already in `ml_panel`/bhav) into the scorer so a machine NS can actually reach T1 (D66 identified this as the unlock).
- **C-blend re-check.** Re-validate the quality × momentum blend/tilt (does layering C on the momentum sleeve add alpha or cut drawdown?) — tracked in [momentum-riskadj.md](./momentum-riskadj.md); QUAL_MOM hints it can, unproven.
- **⚠ Flagged divergence (reconcile, do not silently "fix").** The methodology's [patterns.md](../../resources/patearn/patterns.md) and the code's `scoring.py` **agree on the total envelope and the top-5 Quality Gate**, but their **patterns 6–14 are re-labelled and re-weighted** relative to each other (e.g. the code's numeric-friendly "Earnings Momentum / Margin Expansion / Receivables Discipline / Volume Confirmation" vs. the methodology's "Mix Premiumisation / Capex Completion / Export Expansion / Relative Strength"). This is a deliberate adaptation of the lower-weight patterns to what is numerically computable from fundamentals — but the two pattern *maps* should be reconciled (or the divergence explicitly documented in `calculations-and-weights.md`) so a future reader doesn't assume pattern #N means the same thing in both. Surfaced here per the record-every-finding rule; **no code change made.**

## 10. Sources of truth

**Methodology (resources — two levels up from `docs/strategies/`):**
- [resources/patearn/SKILL.md](../../resources/patearn/SKILL.md) — the 6-phase process, scoring architecture, calibration standard.
- [resources/patearn/patterns.md](../../resources/patearn/patterns.md) — the 14 patterns, per-signal Yes/Partial/No criteria (the pattern math).
- [resources/patearn/failures.md](../../resources/patearn/failures.md) — 6 failure case studies + the pre-entry anti-signal checklist.
- [resources/patearn/exit-protocol.md](../../resources/patearn/exit-protocol.md) — the 4-mode Hold/Trim/Re-evaluate/Exit decision tree.

**Product / doctrine:**
- [docs/patearn-charter.md](../patearn-charter.md) — operating doctrine (evidence machine > signal shop; trust is the product).
- [docs/strategy-ledger.md](../strategy-ledger.md) — Tier-3 lens row: "patearn · 14-pattern PIT fundamental quality score · deployed; PIT-backtestable but not run as alpha."
- [docs/calculations-and-weights.md](../calculations-and-weights.md) — the ONE canonical explainer for the numbers/weights (never restated elsewhere).
- [docs/fundamentals-xbrl-migration.md](../fundamentals-xbrl-migration.md) — the Screener → NSE-XBRL remediation.

**Companion strategy lens:**
- [docs/strategies/momentum-riskadj.md](./momentum-riskadj.md) — the momentum / risk-adjusted return engine and where "C" is consumed (the quality × momentum blend). patearn *filters*; momentum *ranks*.

**PROJECT_STATE.md sections:** § Decision log (D7/D8/D18/D24/D45/D46/D61/**D66**/**D76**/D78/D79/D82) · § Database schema (`pattern_scores`, `capital_allocation_scores`, `fundamentals`) · § Key file paths · § Telegram bot commands · § Session log (Sessions 37, 63, 73, 75).

**Memory (user auto-memory, by slug):** `primary-intent-north-star` (patearn = the best analytical tool for Indian equity research; never leak formulas) · `fundamentals-archive-built` (the 24y PIT archive; do not re-collect) · `dataset-roadmap-c-a-b` (C/A/B lenses stay veto-only, D66) · `predictive-attributes-finding` (momentum the only surviving factor; C/A/B veto-only) · `data-sourcing-primary-only` (primary sources; never Screener/vendors).

---

## Maintenance

- **This is a canonical reference — keep it current, do not archive.** Update it in the **same commit** as any change to patearn scoring, the pattern set, the "C" lens, or the data provenance (the PROJECT_STATE `state:` update rule extends here).
- **Protect the IP.** Describe patterns and mechanisms qualitatively; **link** to [patterns.md](../../resources/patearn/patterns.md) / [scoring.py](../../src/automation/scoring.py) / [calculations-and-weights.md](../calculations-and-weights.md) for the math. **Never paste weights, thresholds, or the normalisation constants here** (`primary-intent-north-star`: never leak formulas).
- **Hold the honesty fences.** patearn is a **risk filter, not validated alpha** (D66); Stage-1 is **rule-based, not LLM** (D7); metrics are in **rupees, not share count** (Guardrail #5); "C" is a **blend/tilt, not a standalone ranker** (D66); fundamentals via Screener is a **disclosed, being-remediated exception** (Guardrail #8 / D78). If any of these stops being true, fix the fence *and* the reality in the same change.
- **When the XBRL migration completes** (Phase 3 / `screener.py` deleted), revise §6 and close the §9 item.
- **Reconcile the §9 pattern-map divergence** with the owner before assuming the two pattern numberings are interchangeable.
