# CCI — Concall Credibility Index (Patearn) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** FAILED-AS-FACTOR → DESCRIPTIVE / VETO-ONLY · **Governing decision(s):** D60 (build + debate inversion, 2026-06-21/22) · D61 (measurable-only doctrine, 2026-06-22) · the **2026-06-25 factor falsification** (`cci_backtest.py`) · the **2026-06-30 Gate B FAIL** (residual-alpha, leak-free, `65f3a32`) · **Reconciled:** 2026-07-11 (S111).
> **Origin:** 🏠 HOUSE (the Concall Credibility Index — guidance-vs-delivery scoring, built inside patearn). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for CCI. Deep design + panel review: [cci-backtest-methodology-and-review.md](../cci-backtest-methodology-and-review.md). Falsification record: [strategy-ledger.md](../strategy-ledger.md). Numbers live in code + [calculations-and-weights.md §5g](../calculations-and-weights.md); this page never restates a formula's constants — it links.

**One-line definition:** CCI is a **point-in-time management-credibility time-series** built from Indian earnings-**concall** transcripts — every management promise is captured, graded against what actually landed in the next result, and compounded into an as-of `credibility_series(symbol, date, level, momentum)` per company. **CCI here = Concall Credibility Index (the in-repo program name is "Concall Intelligence"), NOT the Commodity Channel Index** — it has nothing to do with Lambert's price/volatility oscillator.

---

## 1. What it is

A per-company, point-in-time read on whether a management **does what it said it would do**. The unit of evidence is the *promise*: on each earnings call, management makes forward statements ("revenue up double-digit", "capex ₹2,000cr", "debt down by FY-end"). CCI extracts each one, waits for the resolving result, grades it MET / PARTIAL / MISSED against the actual, and rolls the settled track record into a **credibility level** (kept-promise hit-rate), a **momentum** (level vs the prior period), and two symmetric **tapes** — an `EARNING_TRUST` tape (a name earning credibility) and a `DETERIORATION` tape (a name losing it). Ramana's framing: *credibility is a price, not a stamp* — a stock at 500 won't stay 500, and neither does trust; it moves as concalls land and promises settle. Hence a **series**, not a static score.

The original thesis (D56 → D60) was a wedge: *a management-credibility signal that FRONT-RUNS price re-ratings* — credible managements, guiding up, where the market hasn't priced it. That thesis was **return-tested and rejected** (see §4). What survives is the honest, defensible thing: a **qualitative evidence dossier** per name — the promise ledger with verbatim quotes, variances, and outcomes — shown when a human is researching a stock.

## 2. Our variation vs. the standard technique

There is **no textbook "concall credibility index."** This is proprietary, and it is deliberately *not* the two naive things a first attempt would build:

- **Not sentiment/tone scoring.** The 8-lens adversarial debate (D60; [concall-intelligence-debate.md](../concall-intelligence-debate.md)) caught the fatal flaw in scoring credibility from the transcript's own tone: it ranks the **best-spoken frauds highest** (Manpasand / Vakrangee / DHFL / Yes Bank / Brightcom / Coffee Day all ran smooth, confident calls straight into collapse). So the scorer was **inverted**: a forensic **VETO gate goes first** (promoter pledge ≥ 20% + pt14 hard-disqualifiers), the **resolved track record is primary**, self-testimony is demoted, and tone is kept only as a per-speaker *deviation*, never a level.
- **Not an LLM opinion blended into a rank.** Under **D61 (measurable-only doctrine)** — CCI was the *original violator* that forced the rule — the rank rests only on reproducible, ground-truthable numbers: `guidance_accuracy` (kept-promise hit-rate after settlement) and `quantification_rate` (the deterministic % of forward statements that are *falsifiable numbers*, computed from `claim_text` — this **replaces** the LLM "transparency" score). The 10 behaviour axes are still stored and shown, labelled **"AI read — not ranked."**

What makes it **PIT and honest**: every series point is computed using **only what was knowable at that concall date** — promises resolved by T, quantification of promises made by T, deterioration flags seen by T — with **no look-ahead**; unproven names (no settled promises) are **capped below A** rather than flattered; thin samples are shrunk toward a neutral prior; and the whole thing was subjected to a pre-registered falsification gate *before* any edge claim (§4).

## 3. How it works (methodology)

The pipeline, in order (runner: [`cci_pipeline.py`](../../src/automation/cci_pipeline.py); free except the extract step):

1. **Ingest (free)** — [`concalls.py`](../../src/automation/concalls.py): Screener "Concalls" index → BSE transcript PDF → `pypdf` text on the VPS filesystem (no OCR). Ingestion captures a **perishable** source (transcripts rotate off BSE/IR sites) and must never stop for budget.
2. **Extract (paid, one-time/transcript)** — [`concall_extract.py`](../../src/automation/concall_extract.py): one Gemini pass per transcript → structured promise/guidance rows. Pre-processed by [`cci_normalize.py`](../../src/automation/cci_normalize.py) (Hinglish + lakh/crore parsing, "fifteen hundred crore" → 1500, commitment classifier, hedge lexicon where ritual fillers score 0). Intent direction (increase/maintain/decrease) via [`concall_direction.py`](../../src/automation/concall_direction.py).
3. **Results** — [`concall_results.py`](../../src/automation/concall_results.py): quarterly actuals + neg-EBITDA ledger (lender-aware: banks/NBFCs report Revenue + Financing Profit, EBITDA forced NULL).
4. **Deep actuals (the depth lever)** — [`cci_deep_actuals.py`](../../src/automation/cci_deep_actuals.py): grades old promises against the **24-year `fundamentals_history` archive** (research.db), not just Screener's shallow ~FY2019 table — so a track record reaches back to ~2017. PIT by construction (only `report_date ≤ as_of` visible).
5. **Settle** — [`concall_settle.py`](../../src/automation/concall_settle.py): resolves OPEN promises against actuals → MET / PARTIAL / MISSED (level / growth% / margin / directional sign-match), multi-year → ONGOING, **no look-ahead**.
6. **Diff** — [`concall_diff.py`](../../src/automation/concall_diff.py): deterministic consecutive-transcript deterioration tape (walked-back / dropped guidance).
7. **Score** — [`concall_scores.py`](../../src/automation/concall_scores.py): pure-Python, zero-LLM rank + tier. **Machine-owner of the scoring constants** (`W_GA`, `W_QR`, `UNPROVEN_CEILING`, `DETER_PEN_PER`, sample gate, shrinkage prior) — do not restate them here; read the code (and [calculations-and-weights.md §5g](../calculations-and-weights.md) for the weights + numbers doctrine).
8. **Series (the spine)** — [`cci_series.py`](../../src/automation/cci_series.py): materializes the PIT `credibility_series` (level + momentum + tape), reusing the scorer's exact constants so the series and the snapshot never diverge. This is the **canonical leak-free as-of credibility** that every downstream (the gate, the backtest, the RRG, the dossier) reads. ~18,944 PIT points at last full build.

> Do **not** paste or duplicate any of these constants/thresholds into this page — they are code-owned. Link.

## 4. Status, validation & honesty fence

**CCI is FALSIFIED as a factor. It has NO validated long / short / risk edge. Its only defensible role is a DESCRIPTIVE per-name evidence dossier — never a ranked screen, factor, or leaderboard.** This is the headline, and it is load-bearing: representing CCI as a working signal is a **blocking error**.

**The return-test (2026-06-25, [`cci_backtest.py`](../../src/automation/cci_backtest.py)):** PIT `credibility_series` (level + momentum) × corporate-action-adjusted forward returns (NSE `prev_close` chain over `bhavcopy_rows`), de-marketed cross-sectionally by concall-month cohort; 3,523 proven points (n_resolved ≥ 3) across **377 symbols**; 3/6/12m. **Two independent reviews (code + methodology) reproduced the result on the VPS** before it was recorded.

| Test | 3m | 6m | 12m | Read |
|---|---|---|---|---|
| **Level: HIGH−LOW excess** | −3.1% | −5.8% | **−10.0%** | high-credibility **UNDERPERFORMS** (low-cohort t up to +3.6) |
| **Momentum: rising−falling** | +0.3% | +0.8% | +1.1% | weak; both rising **and** falling beat flat → "moved" not "rose" |
| **Deterioration veto: P(<−20%) event vs non-event** | 6.8 / 6.9% | 12.6 / 12.5% | 14.9 / 15.8% | **NO** downside difference (event marginally *better*) |

Spearman ≈ **0**. The inverse level print is **fragile**: n=377 **survivor** names, concentrated post-2023 (−17% vs −7% pre-2022) and in high-level megacap mean-reversion — a **regime print, not a structural factor**. It survives size + valuation neutralization but is heavily **survivorship-confounded** (the universe is *current* concall-holders, so only surviving low-credibility names are sampled; the delisted blow-ups the deterioration veto is *supposed* to catch have been removed by survivorship — the veto is structurally blind to its true target).

**Second method, same verdict — Gate B (2026-06-30, [`research/cci/gate_residual_alpha.py`](../../research/cci/gate_residual_alpha.py), `65f3a32`):** the orthogonalized residual-alpha regression `fwd_ret ~ cred + ROCE + debt + size + 12-1mom + PEAD` (Newey-West HAC), n=1119, reading the **leak-free PIT `credibility_series`** as the regressor → **cred coef −0.00108, t=−3.71, p<0.001, NEGATIVE** (R² 0.028). PASS needs positive + significant → **FAIL → merge CCI into pt14, no standalone book.** Credibility re-prints the *already-arbitraged quality factor* — it is not incremental alpha over quality + PEAD. (Gate A guidance→return also FAIL/WEAK.)

**The content follow-up — and why no content chip ships either.** After credibility died, the hypothesis was that the *real* signal was concall **CONTENT** (growth-intent: debt_reduction / capex / volume / new_product / expansion), not credibility. A first cross-sectional scan (2026-06-25) looked economically coherent (debt_reduction +2.8% / volume +2.3% / new_product +1.8% / capex +1.5% vs cost_savings −1.0%). **But the placebo harness killed it (2026-07-08, S83e, [`concall_intent.py`](../../research/explosive_moves/concall_intent.py) walk-forward on real `concall_dt`, 9,461 events):** six statement-types passed t_cohort ≥ 2 with same-sign halves (debt_reduction +3.52% t2.43, capex +3.07% t2.70…) — yet against the **shuffled-date placebo** the largest passing type printed **observed +1.90% vs null mean +2.75% / p95 +3.66%** (inflation 0.52×, empirical-p 0.925). **Random windows of the same covered names drift MORE than post-call windows.** The old month-granular tilts are recorded **"not reproducible on real dates" — covered-universe beta, not content edge.** Guidance therefore stays a candor/promise **descriptive** axis; **no content chip ships as an edge.** Do not overstate the content angle.

**Why more extraction cannot fix it (the breadth ceiling).** The binding defect is **BREADTH / survivorship — the 377-name current-holder universe — NOT corpus depth.** No amount of additional Gemini extraction changes the universe you can sample; it only deepens names already in a survivorship-biased set. Therefore the **decision (D-recorded): do NOT spend (~₹2,500) to complete the transcript corpus for any factor/screen use.** Transcript **CAPTURE stays running (free)** as a research asset; **EXTRACTION stays deferrable** (reads on-disk `.txt`, loses nothing when paused).

**Consistent with doctrine:** credibility is a veto / context layer, never a ranker or fundable alpha (the ledger's corollary: *price strength is the only gross forward-return engine; value/quality/credibility/accumulation are veto/filter/context layers, not rankers*). This negative result is a **recorded benchmark** — reproduce with `python -m src.automation.cci_backtest --mode both`.

## 5. Where it lives (code · routes · DB · timers)

**Analytics (`src/automation/`):** `cci_pipeline.py` (runner) · `concalls.py` (ingest) · `concall_extract.py` (Gemini) · `cci_normalize.py` · `concall_direction.py` · `concall_results.py` · `cci_deep_actuals.py` · `concall_settle.py` · `concall_diff.py` · `concall_veto.py` (forensic gate) · `concall_scores.py` (rank/tier, constant-owner) · [`cci_series.py`](../../src/automation/cci_series.py) (PIT series — the spine) · `concall_clock.py` (PIT event dates) · `concall_signals.py` (content/growth-intent materialization — descriptive, see §4) · [`cci_backtest.py`](../../src/automation/cci_backtest.py) (falsification) · [`cci_rrg.py`](../../src/automation/cci_rrg.py) (credibility RRG + ÷price divergence — **descriptive map, explicitly not a buy/sell signal**).

**Falsification gates (`research/cci/`):** `gate_guidance_return.py` (A) · `gate_residual_alpha.py` (B — the standalone-vs-merge decision) · `gate_golden_discrimination.py` · `common.py`.

**Web (`src/web/`):** [`credibility_fingerprint.py`](../../src/web/credibility_fingerprint.py) → **`/dash/credibility`** (the promise-vs-delivery fingerprint flagship; also embedded as the stock dossier's CCI tab) · `growth_view.py` → **`/dash/growth`** (content/growth-intent board — descriptive). Surfaces: **`/dash/concalls`** (avoid-tape + credibility-leaders board), **`/dash/stock`** CCI dossier panel, the **`credibility · cci`** screener column-group, and **Pat** NL flows (credibility / deterioration queries). Every surface carries the descriptive-only / no-forward-signal copy.

**DB (SQLite; 9 base tables per D60):** `concalls`, `concall_results`, `concall_ebitda_watch`, `concall_guidance` (the promise ledger), `concall_expectations_vs_actual`, `concall_behavior` (AI-read, not ranked), `concall_redflags`, `concall_scores`, `concall_coverage` (survivorship spine) — schema in [`src/core/db.py`](../../src/core/db.py) `SCHEMA_BASE`. Plus module-owned tables: `credibility_series` (`cci_series.py`), `credibility_rrg` (`cci_rrg.py`), `concall_signals` (`concall_signals.py`). Transcript text on disk at `/opt/hermes/data/concalls/<SYM>/*.txt` (metadata-only in DB — no PDFs kept).

**Timers (systemd, VPS):** `hermes-concall-capture.{service,timer}` — **free** full-universe capture, Wed + Sun 09:00 UTC ([`scripts/`](../../scripts/)); `hermes-concalls.timer` (Mon–Sat 07:00 UTC) drains ~18 Gemini extractions/day oldest-first + settles; `hermes-concalls-refresh.timer` (Sun) weekly incremental. (Deploy discipline: **never** run `setup-news.sh` or `systemctl start` a hermes timer mid-day on the VPS — see project deploy notes.)

## 6. Data & provenance

**Source:** Indian earnings **concall transcripts** — Screener "Concalls" section is used **only as the index** (the concall LIST + transcript URLs); the **PDFs download DIRECT from BSE** (`Referer: bseindia`, ~71% BSE / rest NSE / company-IR), parsed with `pypdf`. Quarterly actuals come from Screener + our own 24-year `fundamentals_history` (research.db) for deep settlement. This keeps CCI close to **primary sources**; the standing wean path off the Screener index for ongoing discovery is the **BSE corporate-announcements API** (`api.bseindia.com/.../AnnGetData/w`, probed 200-OK with primed cookies) — a focused adapter, not urgent, consistent with Guardrail #8 (primary sources only; the `screener.py` dependency is the known-remediated exception, not to be extended).

**PIT / knowable-at handling (the leak fence):** every graded promise is visible only where `report_date ≤ as_of`; `cci_series.py` composes each point from **only what was knowable at that concall date**. Entry/knowable clock is **two-tier (D104, 2026-07-10):** the **real concall/transcript event date** `max(concall_dt, transcript_publish_dt)` when captured (16,208 rows carry a real `concall_dt` from the S84 BSE calibration), with period-month-end only as the fallback — so a "Q4 (Mar)" call that actually happened in late-April is not back-dated to Mar-31 (the leak the panel flagged). **Gate B's own leak (CL-RES-01)** — an early version regressed on the *latest* composite (embedding resolutions after each anchor) — was fixed by pointing the regressor at the PIT `credibility_series`; the FAIL verdict is leak-free.

## 7. Terminology canon

- **CCI = Concall Credibility Index.** **Disambiguate loudly: this is NOT the Commodity Channel Index** (Donald Lambert's 1980 price/volatility momentum oscillator). Zero relationship — different domain, different math, different purpose. In Patearn, "CCI" always means concall/management credibility.
- **In-repo naming nuance:** the umbrella program is titled **"Concall Intelligence (CCI)"** in D60 and the ledger; its scored core — the point-in-time management-credibility index — is the **Concall Credibility Index**. Both abbreviate to CCI in-repo and refer to the same thing. (Flagged as a terminology reconciliation, not a conflict — see §8 / final report.)
- **`credibility_series`** — the canonical PIT time-series (symbol, date, level, momentum, tape); the leak-free source of truth.
- **guidance-accuracy** — kept-promise hit-rate after settlement (the primary *measurable* rank input).
- **quantification_rate** — deterministic % of forward statements that are falsifiable numbers (the reproducible "transparency"; replaces the LLM score).
- **candor / promise axis** — the descriptive frame guidance now lives in (no content edge ships).
- **tapes** — `EARNING_TRUST` (trust being earned) vs `DETERIORATION` (trust eroding; the avoid tape).
- **tier / UNPROVEN** — internal letter grades (client-facing copy leads with the *statistic*, e.g. "guidance met X% · n=Y · peer Z%"); `UNPROVEN` = no settled promises → capped below A.
- **forensic veto** — an exogenous integrity gate (pledge ≥ 20% + pt14 disqualifiers), **not** a credibility-score ranker (so no D61 breach).

## 8. Decision & session history

- **D60 (2026-06-21/22, S27–29)** — CCI built (9 tables, ingest→extract→settle→diff→score, `/dash/concalls` + dossier + Pat), then **inverted** after the 8-lens debate (veto-first, track-record-primary, price↔credibility firewall). Engine-B price-mispricing deferred. Sequenced: cheap falsification gates *before* scale.
- **D61 (2026-06-22)** — measurable-only doctrine; CCI (the original violator) rewritten to rank on `guidance_accuracy` + `quantification_rate` + veto + deterministic deterioration; behaviour axes demoted to "AI read — not ranked."
- **Credibility-as-a-price upgrade (2026-06-24, Ramana "I agree with all of them, go")** — evolve the static score into the PIT `credibility_series`; deep-settle old promises against 24-yr `fundamentals_history` (`cci_deep_actuals.py`).
- **2026-06-25 — RETURN-TEST + FALSIFICATION** (`cci_backtest.py`): LONG thesis rejected, INVERSE level (−3.1 / −5.8 / −10.0%), weak momentum, veto shows no downside-cutting value; reproduced by two independent agents; binding defect = breadth/survivorship (n=377), not depth. **Content follow-up** found a coherent-looking growth-intent structure — hypothesized as the "real signal."
- **2026-06-30 — GATE B FAIL** (`gate_residual_alpha.py`, `65f3a32`): residual-alpha coef −0.00108, t=−3.71 — a *second* method confirming descriptive-only; **merge into pt14, no standalone book.**
- **2026-07-08 (S83e) — CONTENT ALSO FALSIFIED**: the growth-intent walk-forward on real `concall_dt` failed the shuffled-date placebo (observed +1.90% < null p95 +3.66%); "covered-name drift" is the null that kills content-conditioned concall claims. **No content chip ships as an edge.**
- **D104 (2026-07-10, S100)** — `/v1` PIT knowable clock upgraded to the real two-tier concall/transcript event date.

## 9. Open items / frozen work

- **Transcript CAPTURE continues (free, running)** — a perishable research asset worth preserving regardless of the factor verdict. **EXTRACTION stays paused/deferrable** (no factor-use spend justified; the breadth ceiling, not depth, is binding).
- **Delisted-name re-test is structurally BLOCKED** — the survivorship fix needs concalls for delisted/failed names, which are not on Screener/BSE for dead tickers; a single pre-collapse call also can't be caught (the deterioration diff needs ≥ 2 consecutive calls). So the deterioration veto stays **descriptive, un-validatable here**, never ranked.
- **Merge-into-pt14** is the recorded consumption shape (Gate B): CCI informs the qualitative dossier, it does not run as its own book.
- **Hygiene-only** — a historical PIT-dating nicety in settlement was verified immaterial to the verdict (fix is cosmetic now the factor use is dead).

## 10. Sources of truth

- **Deep design + independent panel review:** [cci-backtest-methodology-and-review.md](../cci-backtest-methodology-and-review.md) · full program design: [concall-intelligence-design.md](../concall-intelligence-design.md) · the debate that inverted the scorer: [concall-intelligence-debate.md](../concall-intelligence-debate.md).
- **Falsification record (exact numbers + the failure-model row):** [strategy-ledger.md](../strategy-ledger.md) — see "Concall Intelligence — RETURN-TESTED + FALSIFIED as a factor (2026-06-25)", the "Studies 2026-07-08" placebo nulls, and the BLOCKING FAILURE MODELS row ("CCI credibility as a factor").
- **Numbers doctrine (constants live in code):** [calculations-and-weights.md §5g](../calculations-and-weights.md); the CCI scoring constants are machine-owned in [`concall_scores.py`](../../src/automation/concall_scores.py) (`W_GA` / `W_QR` / `UNPROVEN_CEILING` / `DETER_PEN_PER`).
- **Running state / decisions:** [PROJECT_STATE.md](../../PROJECT_STATE.md) — D60, D61, D104; the S100 / S96b PIT entries; the 2026-06-30 Gate B session note.
- **Canonical memory:** `cci-credibility-timeseries` — THE CCI record (Gate B FAILED leak-free → descriptive-only; Phase-0 build history absorbed as an appendix).

## Maintenance

- This is a **linking** reference: when a number, weight, or verdict changes, update it **in code / the ledger / calculations-and-weights.md** and adjust the one-line pointer here — never restate a constant on this page.
- **The honesty fence in §4 is non-negotiable.** If a future session proposes reviving CCI as a factor, screen, or ranked leaderboard, it is **BLOCKED** until it beats the recorded numbers (Spearman ≈ 0; HIGH−LOW −10% @12m; Gate B t = −3.71) *net of realistic cost, on a survivorship-safe universe* — cite them first ([failure-ledger](../strategy-ledger.md) discipline).
- Keep the **Concall Credibility Index vs Commodity Channel Index** disambiguation intact — it is the single most common misread of "CCI."
- If CCI's role changes (e.g. a formal pt14 merge lands, or the BSE-announcements wean adapter ships), record it in §8 and update the Status badge.
