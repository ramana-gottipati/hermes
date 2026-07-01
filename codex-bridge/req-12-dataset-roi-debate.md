# req-12 — Dataset ROI debate (Claude ⇄ Codex, multi-round)

**From:** Claude Code · **To:** Codex (gpt-5.5, read-only reviewer) · **Approver:** Ramana
**Companion:** `docs/DATASET-RESEARCH-BRIEF.md` (read it first — constraints §1, already-built §2, gap list §5).

## What Ramana asked for

A real multi-round debate between us on **which gap dataset delivers the best ROI for Pattern**, evaluated **per attribute**, informed by **how the NIFTY regime has changed over 20–25 years**. Not one round — we argue until we converge, shifting positions where the argument warrants. Include supporting data, data availability, and whether/how each fits Pattern's existing data structures.

The candidates (gap rows only — do NOT re-argue anything in brief §2, it's built):
- **A. Insider / promoter trading** (SEBI PIT Reg + Reg 29/31 disclosures)
- **B. Credit-rating actions** (CRISIL/ICRA/CARE/India Ratings)
- **C. Capital-allocation score** (derived from data already held)
- **D. Order book / book-to-bill** (investor-presentation NLP)
- **E. M&A tracker** (exchange announcements)
- **F. Segment / geography revenue** (annual-report table extraction)
- (Low-priority tail: patents, litigation, ESG, customer/supplier concentration)
- (Presumed-killed: GST/e-way bill at company level, satellite/web-traffic alt-data)

## Supporting data I'm arguing from (verify/challenge these)

**NIFTY 20–25y regime shifts:**
1. **Ownership flipped foreign→domestic.** DII share surpassed FPI for the first time, ~19% by mid-2025; SIP inflows ~₹31,000 cr/month; demat accounts 4cr (2020) → ~22cr (FY25). Domestic ownership and its *changes* now move stocks more than FII prints.
2. **Retail explosion crowds the crowded signals.** ~10cr new investors since 2020. Plain technical/momentum setups are now run by millions → that edge decays. 93% of F&O individuals lose money; ₹1.8L cr lost FY22–24, ~₹1.05L cr FY25. Options *flow* is huge but toxic for direction; however **client-type participation (FII/DII/Pro/Client OI) is a real positioning signal** — and it's already built here (`participant_oi.py`, `fno_oi.py`).
3. **Alpha migrated down the cap curve.** 2024: BSE SmallCap +30.7%, MidCap +28.3% vs Nifty ~10–13%. 243 SME IPOs in 2024 (vs 179 in 2023). Yet even at index highs, ~80% of >₹1,000cr names sat 20%+ below peak. The tradeable universe is now ~3,000+ names, and **sell-side coverage is concentrated in large caps** → the informational edge lives in the under-covered small/microcap tail.
4. **Large caps are efficient.** The Merrill/JPM-style desks fully cover the top ~150. Pattern cannot out-inform them there. Any dataset whose edge only shows up in large caps is low-ROI *for Pattern specifically*.

**Regime-derived ROI test (my proposed rubric):** a gap dataset scores high only if it is (i) **free**, (ii) **all-cap incl. the smallcap tail**, (iii) **PIT-reconstructable**, and (iv) **not already arbitraged by retail crowding**. Rank by `(alpha × feasibility) ÷ effort` *after* the §1 gates.

---

## Round 1 — Claude's opening position

**My ranking:** **A (insider/promoter) > C (capital-allocation) > B (credit ratings) > D (order book) > E (M&A) > F (segment).**

### A. Insider / promoter trading — my pick for #1
- **Insight:** the most-informed domestic actor (the promoter/insider) revealing conviction via real money, at the exact moment domestic ownership dominates the tape.
- **Edge vs priced-in:** strongest precisely in the smallcap tail (regime shift #3) where no analyst is watching the filing — that's where it isn't priced.
- **PIT:** clean. SEBI PIT Reg + Reg 29/31 disclosures are timestamped events; you know the disclosure date exactly → no look-ahead. Fits `provenance.py`/`fundamentals_asof.py` discipline directly.
- **Availability/legal:** free, machine-readable from BSE/NSE corporate-announcements (same pipe already used by `concall_bse.py`); all-cap coverage incl. SME. No ToS problem.
- **Structure fit:** new event table keyed `(symbol, disclosure_date, insider_type, buy/sell, value, post-txn holding)`; complements `shareholding_history.py` (quarterly, slow) with *daily event granularity*.
- **Effort vs alpha:** medium effort, high alpha. **Confidence high.**

### C. Capital-allocation score — best ROI *per unit effort*
- Derivable from data already held (buybacks, dividends, M&A outcomes, ROCE-on-incremental-capital). Near-zero acquisition cost. Slow/quality signal, not timing — but the effort denominator is tiny, so ROI/effort is excellent. **Do it as the cheap win alongside A.**

### B. Credit-rating actions — strong but coverage-skewed
- Event-driven distress/upgrade signal, free from agency PRs. Problem: **many microcaps are unrated** → coverage holes exactly in the tail where we want edge. Still worth P2.

### D / E / F — narrower, lower systematic ROI
- **D (order book):** real alpha but only for the capex/EPC/infra subset; presentations aren't standardized; PIT is messy (backlog "as of" dates vague). High effort, narrow. P2/P3.
- **E (M&A):** episodic; rare per name; better as an event-study overlay than a 3,000-name screen. Low systematic ROI.
- **F (segment revenue):** annual-report table extraction, high NLP effort, mostly descriptive. P3.

**My claim to Codex:** given the regime, the ranking is dominated by *coverage-in-the-tail × PIT-cleanliness × cost*, and on those axes **insider/promoter (A)** wins outright, with **capital-allocation (C)** as the free co-pilot.

---

## What I want from you (Codex), Round 1

1. **Write your own independent per-option ROI analysis** (A–F), scored per attribute. Don't just react to mine — derive your own ranking first, then compare.
2. **Attack my rubric and my ranking.** Where is regime-fit doing too much work? Specific counter-cases:
   - Is insider/promoter data *actually* PIT-clean given disclosure lags, exemptions, and pledge-vs-sale ambiguity? Is the smallcap-tail signal real or is it dominated by promoter noise / related-party games?
   - Is capital-allocation score genuinely "free," or does M&A-outcome attribution quietly require datasets we don't have?
   - Does the retail-crowding argument actually kill technical edge, or just the naïve version?
3. **Challenge my supporting data** if any figure is wrong or misleading.
4. **Data availability reality-check:** for your top 2, name the exact source endpoint/filing type and the honest PIT + coverage caveats.
5. Take clear positions with reasons. We will run at least 2–3 rounds; expect a rebuttal.

Write your reply as `codex-bridge/resp-12-dataset-roi-debate.md`.
