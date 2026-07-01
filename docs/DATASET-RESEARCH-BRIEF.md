# Dataset Research Brief — for Codex + Claude

**Audience:** Codex and Claude working the shared folder. **Author:** ChatGPT-side brainstorm, grounded against the actual `D:\Hermes` repo by Claude Code.
**Status:** Living brief. Update in place; log findings with reasons, not adjectives.

---

## 0. What this is

Ramana is building **Pattern** (this repo = Hermes / Patearn) — an Indian-equity research platform, ~3,000+ NSE names, EOD-first, running on a ₹300/mo operating budget with cheap models only in scheduled jobs. NSE bhav copy + Screener fundamentals are already ingested to a Hostinger VPS.

The brainstorm that spawned this brief produced a 40-row "data wishlist" table. **Do not treat that table as the task.** A large fraction of it is already built (see §2). The task is to find, rank, and cost the *remaining* datasets — and to kill the ones that look valuable but aren't, in the specific Indian + low-budget context.

**Prime directive: no generic answers.** "Track volume spikes / sentiment / ESG" adds nothing. Every proposal must name the exact source, the exact acquisition method, the exact cost, the legal/ToS reality, and the derived metric — or it doesn't go in.

---

## 1. Hard constraints (these are gates, not preferences)

1. **Cost.** Operating spend ≤ ₹300/mo. No paid data vendors by default. Cheap models (Haiku / Gemini Flash Lite) only in anything that runs on a timer. A proposal that needs a vendor subscription must justify itself as a paid tier, explicitly flagged.
2. **Point-in-time (PIT).** Every dataset must be scored on whether we can know *what was knowable on each historical date*. A signal we can't reconstruct PIT is descriptive-only, never backtestable. The repo already enforces this (`provenance.py`, `fundamentals_asof.py`, `fundamentals_provenance.py`) — new datasets must fit that discipline.
3. **Legality / ToS.** Primary filings (BSE / NSE / SEBI / XBRL) are public and machine-readable — prefer them. Screener.in is used only where nothing else exists, and its ToS is the live constraint (the repo already de-Screeners'd concall discovery via BSE announcements for exactly this reason). No mass-scraping of a rendered UI. State the copyright/ToS position for every source.
4. **Scale.** Must be collectable for 3,000+ companies, on a schedule, unattended. A method that works for 20 names by hand does not qualify.
5. **Honesty over product.** If a signal fails as alpha, it is labelled descriptive-only, not dressed up. (Precedent: CCI credibility and Wolfe/harmonic are descriptive-only in this repo after honest falsification.)

---

## 2. Already built — DO NOT re-propose these

You will waste cycles if you "discover" these. They exist in `src/automation/`:

- Price / volume / delivery %, ATR, relative volume — `bhavcopy.py`, `signals.py`, `oscillators.py`
- Shareholding pattern trends (promoter/FII/DII/MF/retail) — `shareholding_history.py`
- Bulk & block deals + buyer/seller classification — `deals.py`, `client_classify.py`
- Corporate actions + adjustment — `corp_actions.py`, `adjust.py`
- Quarterly financials / cash flow / balance sheet — `screener.py`, `fundamentals_history.py`
- Concall / management-commentary intelligence (CCI) — `concall_*.py`
- Guidance-vs-actual **credibility time-series** (descriptive-only) — `cci_series.py`, `concall_settle.py`, `cci_deep_actuals.py`
- Sector breadth / relative strength / RRG / RS bands / regime — `index_signals.py`, `stock_rs.py`, `rrg.py`, `rsband.py`, `rs_phase.py`
- F&O client-type participation + OI — `participant_oi.py`, `fno_oi.py`
- MEP accumulation/distribution — `mep_signals.py`
- Rule-based quality/scoring — `scoring.py`
- Point-in-time provenance — `provenance.py`, `fundamentals_asof.py`, `fundamentals_provenance.py`
- Business dossier enrichment (Gemini-grounded) — `enrich.py`
- Pattern engines: Wolfe, harmonic, ignition, CPR (descriptive-only) — `wolfe.py`, `harmonic_*.py`, `ignition*.py`, `cpr_signals.py`

If a proposal overlaps one of these, the deliverable is "extend X", not "build new".

---

## 3. The core research question (per candidate dataset)

For **each** candidate dataset, answer all of:

1. **Insight** — what specific investment question does it answer? (Not "sentiment" — *which* decision does it change?)
2. **Edge vs. priced-in** — is this already in the price, or is there an informational/timing edge? Say why.
3. **PIT feasibility** — can we reconstruct it as-of each historical date? If no → descriptive-only.
4. **Legal/scale** — collectable legally for 3,000+ names on a schedule? Exact ToS/copyright position.
5. **Cheapest reliable acquisition** — exact source (URL/API/filing type), exact method, exact cost (₹ or free).
6. **Derived metrics** — the actual columns/signals we'd compute, normalized to scale where relevant (e.g. order-book ÷ market-cap, ÷ revenue; not raw ₹).
7. **AI extraction method** — XBRL parse / structured API / table extraction / OCR / LLM-NLP — and which cheap model.
8. **Effort vs. alpha** — engineering effort (person-days) against expected alpha contribution, with a confidence score.

---

## 4. Ranking rule

Rank by **ROI = (expected alpha × feasibility) ÷ effort**, *after* applying the gates in §1. Not by popularity, not by how sophisticated it sounds. A boring, free, PIT-clean, structured source beats a glamorous alt-data source every time. Output an ordered list; put the killed candidates at the bottom with the reason they failed a gate.

---

## 5. Candidate gaps to investigate (rough prior — re-rank, don't trust)

**Likely high ROI (structured, free, PIT-friendly):**
- **Insider / promoter trading (SEBI Reg 7 disclosures)** — structured, free, management-conviction signal. Confirm PIT availability and coverage.
- **Credit-rating actions** (CRISIL/ICRA/CARE/India Ratings press releases) — event-driven, cheap, debt-risk early warning. Check machine-readability + history depth.
- **Capital-allocation score** — derivable from data *already held* (buybacks, dividends, M&A outcomes, ROCE trend). Near-zero acquisition cost.

**Medium ROI (real alpha, higher extraction effort):**
- **Order book / book-to-bill** from investor presentations — high value for capex/infra/EPC names; LLM/table extraction; normalize to market-cap and revenue.
- **M&A tracker** — exchange announcements; weight by deal size ÷ acquirer market-cap and acquirer's historical M&A track record.
- **Segment / geography revenue** — annual-report table extraction; surfaces hidden growth.
- **Capex pipeline / capacity utilization** — presentation NLP; expansion trigger.

**Investigate but expect low stock-level ROI:**
- Patent filings, litigation, customer/supplier concentration, employee/attrition, ESG/governance — annual-report NLP; mostly descriptive, risk-flag not alpha.

**Likely killed by a gate (prove me wrong or bottom-rank):**
- **GST / e-way bill** — company-level is NOT available (the govt API returns *your own* GSTIN's filings, not third parties'). Only aggregate national/state monthly exists → macro/sector nowcast, near-zero single-stock alpha. Do not budget as a stock signal.
- **Satellite / web-traffic / port / power / alt-data** — not attributable to individual smallcaps, not affordable at this budget. Default: out.

---

## 6. Output format (what to return to Ramana)

A single ranked table/list where each row carries: dataset · insight · edge-vs-priced-in · PIT (Y/N) · source · acquisition method · cost (₹/free) · legal/ToS · derived metrics · extraction method · effort (days) · expected alpha · confidence · **verdict (Build P1/P2/P3 / Descriptive-only / Kill)** · owner · reason.

The reason column is mandatory. A verdict without a reason is rejected.

---

## 7. Collaboration ground rules

- Codex and Claude each append findings under a dated heading; disagree explicitly and say why (don't silently overwrite).
- Cite the source for every factual claim (a URL, a filing type, a rate card). No unsourced cost figures.
- When a candidate is killed by a §1 gate, name the gate.
- Keep it India-specific and budget-specific. Anything that reads like it could apply to any market in any country is too generic — cut it.
