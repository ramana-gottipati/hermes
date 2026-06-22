# Concall Intelligence (CCI) — management-credibility & guidance-accuracy strategy (design v0.1)

> **Status:** **v0.3 (session 29, 2026-06-22)** — P1–P7 **BUILT & DEPLOYED** to the VPS: the full backend
> chain (results→settle→diff→score), the refinements (lender-revenue capture + EBITDA-suppressed-for-financials;
> implied-growth settlement; `--oldest` backfill order), the **P5 UI** (per-stock CCI dossier on `/dash/stock`,
> the `credibility · cci` screener column-group, Pat NL credibility/deterioration flows), the **P6 falsification
> gates** (`research/cci/` — built + validated; **verdict data-gated**), and the **P7 cron** (two staggered
> timers draining ≤18 Gemini calls/day). `/dash/concalls` + dossier + Pat flows all live. **The only thing left
> is DATA** — the Gemini free tier (20/day) means the historical backfill accrues over ~2 weeks via the cron
> (or faster via claude.ai/paid Gemini). Engine B still deferred. Autonomous continuation +
> per-session log: `docs/concall-intelligence-NEXT-SESSION.md` (§2d = session 29). **Constraint:** Gemini free
> tier = 20 requests/day. **Uncommitted — commit gated on Ramana.**
> **Working name "Concall Intelligence (CCI)" / *Management Credibility* pillar — final name + code is
> Ramana's call** (branding decision, per the patearn-brand direction). Siblings: DVPT, RS, CPR, pt14.
> **Brand:** Patearn. "Hermes" = the Nous agent only.
> This doc is the canonical, rich record (the approved plan lived at
> `C:\Users\gotti\.claude\plans\proud-toasting-mccarthy.md`, outside the repo). Keep this doc RICH —
> never one-line the intent (preserve-strategy-intent doctrine).

---

## 1. Why this strategy exists (the throughline)

The project converged here. The explosive-move research (D56) proved — at P&L level, OOS, net of costs —
that **the EOD price tape carries only momentum + churn, not tradeable alpha**. Its own next-frontier note
(`docs/explosive-move-NEXT-SESSION.md` §3, §10) states it plainly: *reported financials are a closed-period
fact, not a promise for the future; the real forward trigger is qualitative — management commentary /
earnings-concall tone / guidance / the direction in corporate announcements.* **CCI is that layer.**

**Thesis.** Management tells you the future in conference calls — in their guidance, their multi-year plans,
what they emphasise, how they handle bad news, and what they quietly drop. The market is slow and imprecise
at pricing this. So we systematically capture every management *expectation/promise*, grade it against what
*actually* landed in the subsequent result and the *next* concall, and let each company build a
**credibility track record** over many periods → a per-company **score and rank**. The edge: **credible
managements, guiding up, whose past promises came true, where the market hasn't yet caught on.**

## 2. The spec, preserved (Ramana, session 27 — this is the requirement, not a paraphrase)

1. **Start 2019** so we see how management *responded* to the COVID shock (courage/handling under fire);
   reach back to 2015/16 where it's free.
2. **Don't store whole concall PDFs** — bring the transcript in, keep it ready, store the *rated* info.
   **Separate the tables.** Compare **concall expectations vs. what was actually released** →
   in-line / **understated / overstated / concealed**.
3. **Flag where the market failed to price** the condition / future state management signalled.
4. **Expectation-adjusted, not naive period-comparison.** Media compares QoQ / YoY and shows "lower." But
   if management *warned of a headwind and still delivered*, that is a **beat vs. their own framing** —
   remember the expectation and judge actuals against it, not just against last quarter / last year.
5. **Follow-through.** Plans laid out earlier (e.g. a 3–4–5-year capex) must be tracked call-over-call —
   on schedule? how communicated to the public? **Credibility lives in this follow-up.**
6. **Behavioural axes have no existing table** — credibility, information-sharing, courage, issue-handling
   must be extracted from transcripts into our own tables.
7. **Negative / poor EBITDA gets its own proper table.** Pull fundamentals where needed.
8. Design the process **from management's perspective first**; surface hidden items the human eye skips.
9. Each company gets **its own rank and its own scores**, based on previous results.

## 3. Two engines (both per-company, both ranked)

- **Engine A — Credibility / Guidance-Accuracy (backward track record).** Compare concall(t) promises →
  result(t+1) actuals → concall(t+1) narrative: did past guidance, capex, margin, volume promises come
  true? Yields a **Credibility Score** + sub-scores that *compound* across periods. This is the slow,
  earned reputation — hard to fake, the real moat of the signal.
- **Engine B — Forward Signal (the trigger).** From the *latest* concall: direction (UP/DOWN/FLAT),
  conviction/tone, new developments, capex acceleration, demand commentary — **weighted by the company's
  Engine-A credibility** — cross-checked against whether price has already moved (**mispricing flag**).
  High credibility + guiding up + market-not-yet-pricing = the actionable signal.

## 4. Data model — separate tables / sections / categories (all new, in `hermes.db`)

Doctrine: own table per new entity (cf. `corporate_actions`, `bulk_block_deals`, `cpr_signals`); raw
transcript text on the **VPS filesystem** (gitignored — *not* in the DB blob, *not* in git: "we don't save
the whole PDF"); scores pre-computed; **rank/weights tunable & derived on read** (the D43/CPR pattern).
Value-based (₹) per the data doctrine.

### 4.1 Corpus / ingestion
- **`concalls`** — one row per (symbol, fiscal_period[, seq]). Cols: `symbol, period_label` (raw e.g.
  "Apr 2026"), `period_type` ∈ {Q,H1,H2,FY,MONTHLY_UPDATE}, `fy`, `quarter`, `concall_month`,
  `transcript_url` (BSE), `ppt_url`, `rec_url`, `ai_summary_id` (Screener `/concalls/summary/<id>/`),
  `ai_summary` (text), `transcript_path` (VPS file), `transcript_chars`, `transcript_sha`, `source`,
  `fetched_at`, `parse_status`, `extract_status`. Idempotent/resumable like the bhav backfill.

### 4.2 Reported numbers (free, from Screener tables) — incl. the negative-EBITDA table
- **`concall_results`** — per (symbol, fiscal_period): `revenue, ebitda, ebitda_margin, pat, eps`,
  `segment_json`, **QoQ & YoY deltas**, and the **expectation-adjusted delta** (actual vs. management's
  prior stated expectation, joined from `concall_guidance`).
- **`concall_ebitda_watch`** — the poor/negative-EBITDA ledger: rows where EBITDA ≤ 0 or margin collapses;
  `magnitude`, `mgmt_explanation`, `flagged_proactively` (did they own it before being asked?),
  `recovery_promise_id` (→ guidance), `periods_in_red` (streak).

### 4.3 Extraction — the "rated information" (the heart)
- **`concall_guidance`** — the **promise ledger / follow-through tracker**. One row per discrete forward
  statement: `source_period`, `statement_type` ∈ {revenue, margin, volume, capex, expansion,
  debt_reduction, demand_outlook, new_product, cost_savings, dividend_buyback, other}, `horizon`
  (this_q / next_q / fy / multiyear_3_5y), `claim_text`, `quantified_target`(+`unit`),
  `confidence_language` (verbatim hedge/conviction phrase), `status` ∈ {OPEN, MET, MISSED, PARTIAL,
  ABANDONED, RESTATED, ONGOING}, `resolved_period`, `evidence`, `variance_pct`.
  **A multi-year capex stays OPEN and is re-checked every subsequent call until settled** — the capex
  follow-up Ramana asked for.
- **`concall_expectations_vs_actual`** — per (symbol, period, metric): mgmt expectation vs. the actual that
  landed → `classification` ∈ {IN_LINE, BEAT, MISS, UNDERSTATED, OVERSTATED, CONCEALED};
  `headwind_adjusted` (warned of a headwind yet delivered = positive even if QoQ down);
  `market_recognized` (did price react in line, or is there a gap → feeds the mispricing flag).
- **`concall_behavior`** — behavioural axes, each 0–100 + a one-line evidence quote: `credibility`,
  `transparency`, `courage`, `issue_handling`, `consistency` (vs prior calls), `specificity`
  (numbers vs vagueness), `evasion` (dodged analyst Qs), `promo_vs_conservative`, `tone`, `confidence`.
- **`concall_redflags`** — discrete hidden / skip-the-eye items: `flag_type` ∈ {guidance_walkback,
  metric_definition_change, segment_reclassification, stopped_disclosing, one_off_masking,
  working_capital_stress, related_party, capex_slippage, promise_quietly_dropped, accounting_change,
  optimism_without_numbers, blames_externals_repeatedly}, `severity`, `evidence`, `period_first_seen`.

### 4.4 Output — the score + rank (each company its own, per period)
- **`concall_scores`** — per (symbol, as-of period/date): `credibility_score`, `guidance_accuracy_score`
  (hit-rate of *resolved* promises), `transparency_score`, `forward_direction`, `forward_conviction`,
  `mispricing_flag`, `credibility_trend`, `composite_score`, `rank` (1–N), `tier` (A+/A/B/C/D),
  `n_concalls`, `last_updated`. **Stored per period** so the track record *and the ranking itself* are
  backtestable (mirrors the DVPT ranking-history design). Weights tunable / derived-on-read.

## 5. Process "from management's perspective" — the extraction rubric

Each transcript is read as management's most sceptical analyst would, answering a fixed rubric (the
Gemini / claude.ai prompt contract → JSON into §4.3):
1. What did they **promise / guide** (every forward statement → guidance ledger)?
2. What did they **claim** about the period just ended, and how did they **frame** it vs. how the raw
   numbers actually read?
3. What did they **emphasise** vs. **bury** (→ red-flags)?
4. How did they **handle bad news / hard questions** (→ courage, evasion)?
5. What **changed** vs. the last call (→ consistency, walk-backs, quietly-dropped promises)?
6. Given the **conditions they described** (head/tailwinds), did they **under- or over-deliver vs. their
   own framing** (→ expectation-adjusted, headwind-adjusted classification)?

When the next result + concall arrive, **open promises are settled** with the later actuals → Engine A
updates. **No look-ahead by construction** (a promise is graded only once its resolving period exists).

**Settlement ↔ extraction idempotency contract (binding).** Extraction owns the *raw* promise set for a
`source_period`; settlement is a *derived overlay* on top of it. Re-extracting a period — which only happens
under `--force` (the normal queue in `pending_rows` skips anything already `extract_status='DONE'`) —
**deletes every `concall_guidance` row for that `(symbol, source_period)`, settled rows included**, then
reinserts the freshly-extracted promises as `OPEN`. This is the same "delete-the-period-set, then reinsert"
idempotency the sibling tables (`concall_behavior`, `concall_redflags`, `concall_expectations_vs_actual`)
already use, and it holds because `status` / `resolved_period` / `variance_pct` are **pure deterministic
functions of the stored promise + later `concall_results`** — so discarding them on re-extract loses nothing
the settlement pass cannot rebuild. **Therefore: (1)** the Phase-2 settlement pass MUST be deterministic and
idempotent (safe to run repeatedly); **(2)** after any `--force` re-extract you MUST re-run settlement
*before* `concall_scores --rerank`, else `guidance_accuracy_score` is computed over an unsettled (all-`OPEN`)
ledger. *Do not* re-add a `status='OPEN'` qualifier to the extraction delete: the earlier status-scoped delete
left settled rows behind while the reinsert added a duplicate `OPEN` copy of the same promise — double-counting
it in the ledger and inflating `guidance_accuracy_score` (fixed session 27, `concall_extract._persist`). There
is intentionally **no `UNIQUE(symbol, source_period, claim_text)` DB constraint**: `claim_text` is an LLM
paraphrase that legitimately drifts across prompt/model bumps (a content-hash key would *not* catch the
duplicate the `--force` re-extract creates), so the *contract above* — not a row constraint — guarantees a
single copy per promise; a unique index would also require a `concall_guidance` table rebuild now that rows exist.

## 6. Market-mispricing detection

For each settled expectation, compare the **direction/magnitude management signalled** against the
**price reaction** in a window around the result/concall (using split-adjusted closes via `adjust.py`):
- management signalled materially better future + price flat/down → **under-priced** (the buy edge).
- management signalled deterioration + price flat/up → **over-priced** (the avoid/short-watch).
- `market_recognized` + `mispricing_flag` capture this; weighted by Engine-A credibility (a credible
  management's unpriced signal matters; a serial over-promiser's doesn't).

## 7. Cost architecture (honours the doctrine)

| Layer | Runs as | Cost |
|---|---|---|
| Fetch concall list + transcripts (Screener→BSE), PDF→text, results join, QoQ/YoY/expectation deltas, score+rank roll-up, lexicon tone first-pass, capture Screener's free AI-summary | **Pure Python / deterministic** | **₹0** |
| One-time structured extraction per concall (guidance + behavior + red-flags JSON) | **Gemini Flash** (`call_extractor` in `llm_router.py`), **cached forever**; ≈1/company/quarter recurring; backfill throttled under a stated rupee cap | ~₹0.10–0.15/transcript |
| Deepest nuance / borderline "is this concealment?" on the shortlist | **claude.ai** (subscription) — paste batched digest, import JSON | **₹0 marginal** |
| Nightly / periodic score + rank | **Pure SQL/Python, NO LLM at run-time** | **₹0** |

Backfill cost estimate (corrected for full-transcript size, ~12k in / ~3k out, not the tiny-classifier rate):
~25-name pilot × ~30 transcripts × ₹0.12 ≈ **₹90** one-time (cap with `--limit`, or `--use-summary` ≈ 10× cheaper
≈ ₹15); full ~500 universe one-time ≈ **₹1,500–1,800** → **throttle across months, or do the bulk in claude.ai
for free** and reserve Gemini for the incremental. Recurring ≈ ₹0.12 × (new concalls/quarter) — negligible.
A 3-name / 2-transcript smoke test to eyeball quality ≈ **₹1**.

## 8. Ingestion technical contract (validated this session against live Screener + BSE)

- **Screener Concalls DOM:** `div.documents.concalls` → `ul.list-links` → one `li` per concall. `li`
  children: date `div.ink-600` (e.g. "Apr 2026"); `a.concall-link[title="Raw Transcript"]` → **BSE PDF**;
  `button.concall-link[data-url="/concalls/summary/<id>/"]` → free **AI Summary**; `a.concall-link` "PPT"
  → BSE PDF; `a.concall-link` "REC" → YouTube. Absent items render as `div`/`button` (no href) → skip.
- **BSE transcript URL:** `https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=<uuid>.pdf`. Fetch with
  a browser UA + `Referer: https://www.bseindia.com/`. **Verified:** RELIANCE Apr-2026 = HTTP 200,
  application/pdf, 31 pp; pypdf extracted ~10.3k clean chars in 4 pp (digital text, **no OCR**).
- **Concall-month → fiscal period (Indian FY Apr–Mar), best-effort:** Apr/May→Q4 (+FY) of the just-ended
  FY; Jul/Aug→Q1; Oct/Nov→Q2; Jan/Feb→Q3. Store the raw `period_label` as ground truth; derive fy/quarter.
- **PDF→text:** `pypdf` (installed in the **production `.venv`** — it's a tiny pure-Python lib, NOT the
  numpy/pandas the doctrine bans; running ingestion under `.venv-research` would force re-installing
  requests/bs4/lxml/pydantic-settings/dotenv there, so production `.venv` is the pragmatic home). Scanned
  PDFs (rare) → OCR fallback, deferred.
- **Transcript text → VPS filesystem:** `/opt/hermes/data/concalls/<SYMBOL>/<period_label>.txt`
  (gitignored). DB stores the path + sha + char count, not the blob.
- **Politeness:** reuse `screener.py` UA ethos + hard caching; backfill via `nohup` on VPS, poll the log
  (flaky-SSH discipline). Never silently treat "no concall" as "bad" — set a coverage flag.

## 9. Phasing

- **Phase 0 (this session):** this design doc; the 8 tables in `db.py`; `concalls.py` corpus fetcher;
  validate on real data (DONE: DOM + BSE + pypdf proven).
- **Phase 1:** `concall_extract.py` (Gemini hybrid) + the four extraction tables; `concall_scores.py`
  deterministic score/rank; the **≈25-name pilot** end-to-end; **data-first dashboard** — a *Management
  Credibility* universe screener (raw numbers beside every pill, wide frozen-pane grid) + a per-company
  **dossier** (promise ledger with MET/MISSED, behaviour radar, red-flag log, expectation-vs-actual
  timeline) + Pat NL flows.
- **Phase 2:** auto-settlement of promises as new results land; the mispricing overlay; CCI as an
  overlay/filter on DVPT/RS/pt14 **and** its own ranked portfolio (the throughline) → expand to ~500.
- **Phase 3:** **backtest the rank** — do high-credibility / guiding-up / not-yet-priced cohorts outperform
  forward? Walk-forward, survivorship-safe, point-in-time (same rigour as D56). The proof it earns a place.

## 10. Backtest / validation discipline

Same rigour as the rest of the project: for each as-of period, does a high composite-score (or
"credibility high + guiding up + not yet priced") cohort outperform forward, OOS, survivorship-safe? The
credibility track record is inherently point-in-time (built only from concalls available as-of), so no
look-ahead if promises settle only with later data. Carry CCI as a **screen/overlay** until the backtest
clears it (same honest stance as the Launchpad).

## 11. Open items / risks

- **PDF quality:** most BSE transcripts are digital text (verified); scanned ones → OCR fallback (deferred).
- **Universe coverage:** small-caps may lack transcripts / sparse pre-2019 → coverage flag; never treat
  missing as bad.
- **LLM extraction drift:** lock the JSON schema + a golden-set of hand-checked transcripts to regression
  the prompt; store model + prompt version on each extracted row.
- **Working-tree discipline:** `PROJECT_STATE.md` + `dashboard.py` are modified by parallel work — the
  PROJECT_STATE update (Decision entry + schema + file paths + session log) is **DEFERRED** until the file
  is free (same precedent as the explosive-move session). Don't clobber.
- **Naming/branding:** final strategy name + code is Ramana's pick.
- **Commit:** ask Ramana before committing (precedent: explosive-move package still uncommitted).

## 12. File map

- `src/automation/concalls.py` — corpus fetcher (Screener Concalls → BSE transcript text on VPS + results).
- `src/automation/concall_extract.py` — deterministic + Gemini JSON extraction → §4.3 tables.
- `src/automation/concall_scores.py` — pure-Python score + cross-universe rank → `concall_scores`.
- `src/core/db.py` — the 8 `CREATE TABLE` blocks + indexes.
- `src/web/dashboard.py` — `/dash/concalls` screener + per-stock Management panel (Phase 1).
- `src/pat/{glossary,flows,engine}.py` — CCI terms + read-only flows (Phase 1).
- `scripts/setup-news.sh` + `hermes-concalls.timer` — periodic incremental run (Phase 1/2).

## 13. Adversarial debate (session 27) — verdict & the architectural inversion

A 17-agent, 8-lens aggressive debate stress-tested this design (full ranked record + India-ecosystem
must-dos: `docs/concall-intelligence-debate.md`). Headline outcomes that **change this design**:

- **⚠ KNOWN ISSUE in the shipped scorer (must fix before any pilot is trusted).** `concall_scores.py`
  blends absolute LLM `credibility` + `confidence` into ~half the composite and fires `forward_direction='UP'`
  on `tone>=60`. That is a *promotional-quality detector*: it ranks the **best-spoken frauds highest** and
  routes them to BUY (every Indian blow-up — Manpasand, Vakrangee, DHFL, Yes Bank, Brightcom, Coffee Day —
  ran smooth, confident, numeric calls). **Credibility cannot be scored from the suspect's own testimony.**
- **The fix is an inversion, not tuning.** (1) A **forensic veto gate IN FRONT** of credibility, wired from
  the **existing pt14 hard disqualifiers** (promoter pledge, auditor exit/qualification, CFO churn, CFO/PAT,
  RPT) — pledge-invocation or auditor-exit ⇒ instant tier D regardless of call tone. Do **not** build new
  forensic tables (pt14 already enforces these). (2) **Pivot the primary deliverable** from "find the unpriced
  credible compounder" (arbitraged — a raw credibility rank just re-prints Pidilite/Asian Paints) to a
  **credibility-DETERIORATION / avoid tape**, computed mostly *deterministically* by diffing consecutive
  transcripts (walk-backs, stopped-disclosing, horizon-rolling). The sell-side won't publish credibility
  decay on its banking/IPO clients — that conflict is the moat.
- **Engine B (price-reaction "mispricing") is gated, maybe cut.** It re-imports the EOD tape D56 falsified.
  Don't build it until the cheap tests clear it; if built, require the three-clock event model (result/print
  ≠ concall ≠ transcript-publish) + a liquidity/circuit/surveillance gate. The price↔credibility firewall
  currently holds (`mispricing_flag` is hard-coded `None`) — lock it with a build-failing lineage assertion.

**Sequencing — SUPERSEDES §9 (the panel's ordering inverts it):**
1. Forensic-veto wiring + **two ~₹0 falsification gates first** — (a) guidance-direction→forward-return on
   the pilot names; (b) credibility's **incremental** alpha after orthogonalising vs quality (ROCE/debt/size/
   momentum) + PEAD. If incremental alpha dies, **merge into pt14, don't ship a standalone portfolio.**
2. Point-in-time **coverage + survivorship spine** from the bhav-copy archive (the SEBI transcript mandate is
   phased: top-100 FY19 → top-250 FY22 → top-1000 ~FY25 → absence is missing-NOT-at-random).
3. Only if it discriminates a **labelled blow-up set** (Manpasand/Vakrangee/DHFL/Yes Bank/Brightcom/Coffee
   Day vs Asian Paints/Pidilite/Page) scored 2–4 quarters BEFORE discovery → the residual backtest.
4. **Dashboard last.** Carry CCI as a screen/overlay until the backtest clears it (screen-not-book stance).

India-specific must-dos (detail in the debate doc): no-Reg-FD ⇒ grade DIRECTIONAL promises on sign-match;
**specificity is non-monotonic** (serial round-number promoter targets are a value-trap tell); external/
trailing anchor for BEAT/MISS (self-grading rewards sandbaggers); sector rubric + Ind-AS 116 / tax-cut
guards + COVID carve-out; deterministic lakh/crore + Hinglish normaliser before extraction.

## 14. Measurable-only ranking (D61) — the binding rule

**Rank and compare on measurable items only.** The composite + the cross-stock rank use ONLY objective,
reproducible inputs: `guidance_accuracy` (kept-promise hit-rate, after settlement), `quantification_rate`
(% of forward statements that are falsifiable numbers — the deterministic *transparency*, replacing the
0–100 LLM one), the **forensic veto** (pledge/auditor/pt14), and **deterministic deterioration** (the
disclosure-diff flags from `concall_diff`, NOT the soft LLM red-flags). The 10 behaviour axes
(credibility/courage/tone/…) stay in `concall_behavior` and are shown as an **"AI read — not ranked"** with
the evidence quote; under/over/concealed are an informational flag, not a ranked class. An **unproven** name
(no settled promises) is capped below A/A+. This aligns CCI with DVPT/RS/CPR/pt14 (already number-ranked).
Rule for any future attribute: **if it can't be measured reproducibly, it informs but does not rank.**
