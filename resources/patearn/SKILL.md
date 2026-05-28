---
name: patearn-explosive-move
description: |
  patearn equity research methodology for identifying Indian mid-cap multi-bagger stocks before institutional re-rating. Use this skill whenever the user wants to: research or analyse a stock for investment; screen for multi-bagger potential; score a company against the 14-pattern framework; run the 6-phase investment process on any Indian equity; assess buy/watch/pass; check for red flags or hard disqualifiers; apply the patearn ranking framework; do a deep-dive on any listed Indian company; review an existing holding against the monitoring protocol; determine position size; or apply an exit decision. ALWAYS use this skill for any Indian stock analysis, scoring, screening, or evaluation — do not rely on general knowledge. The methodology here is the standard and must be applied in full.
---

# patearn equity research framework — methodology v1.1

This is the operational standard for all equity research within the patearn framework. Every stock analysis must follow this process in sequence. No phase may be skipped. No hard disqualifier may be rationalized away. The framework exists precisely to override the intuitive shortcuts that cause most investment mistakes.

---

## MANDATORY FIRST STEP — read before doing anything else

When this skill is invoked, confirm with the user which of these modes applies:

1. **New stock analysis** — applying the full 6-phase process to a company being evaluated for the first time
2. **Quarterly re-score** — updating scores on an existing position after results
3. **Exit decision** — applying the exit protocol to an active holding
4. **Red flag check** — checking a specific governance or accounting concern
5. **Position sizing** — determining allocation given a completed score

Then proceed directly. Do not ask more questions than needed to determine the mode.

---

## CORE MATHEMATICAL FRAMEWORK

### Scoring architecture

- **14 patterns**, each with 3 signals
- Each signal scored: **No = 0, Partial = 1, Yes = 2**
- Each signal carries a **confidence tag**: Verified (from Screener.in / Annual Report / BSE filing) or Estimated (from memory, brokerage note, or judgment)
- Unverified signals contribute at **70% of their weight** — they count, but less
- Pattern Weighted Score (PWS) = sum of (signal score × confidence multiplier × pattern weight W)
- MAX_CWS = 582 (all 14 patterns, all signals Yes, all verified)
- **Normalised Score (NS)** = PWS / 582 × 100

### Sensitivity band (mandatory)
Always compute and report three values:
- **Pessimistic**: every Yes → Partial, every Partial → stays
- **Base**: scores as entered
- **Optimistic**: every Partial → Yes, every Yes → stays
Report as: `NS range: [pessimistic]% – [base]% – [optimistic]%`

### Tier classification

| Tier | NS threshold | Quality Gate | Position size |
|------|-------------|-------------|---------------|
| T1 — Strong Setup | ≥ 72% | Must pass | 4–6% of portfolio |
| T2 — Good Setup | ≥ 55% | Not required | 2–3% of portfolio |
| T3 — Developing | ≥ 40% | Not required | ≤ 1% — watch only |
| T4 — Weak / Watch | < 40% | N/A | Watchlist, no entry |
| DISQUALIFIED | Any NS | N/A | Zero — no entry |

**Quality Gate rule**: The top 5 patterns (ROCE, Operating Leverage, Tailwind, Valuation, Balance Sheet) have MAX contribution of 240 pts. If a stock scores < 60% on these five specifically (< 144 pts), it cannot reach Tier 1 regardless of total NS. Prevents technical/ownership signals masquerading as quality.

**Prior run-up rule**: A stock that has already done > 200% in the past 24 months is capped at Tier 3 maximum, regardless of score. You are buying the story, not the setup.

### Pattern Activation Count (PAC)
Count how many of the 14 patterns have at least one signal ≥ 1 (Partial or Yes). Report this alongside NS. A score of 68% with PAC 13/14 is more robust than 68% with PAC 7/14.

---

## HARD DISQUALIFIERS — non-negotiable, no exceptions

These five conditions disqualify a stock from any tier and from any position. They apply regardless of how good the sector narrative is, how strong the ROCE is, or what the composite score says. **Never rationalize an exception.**

1. **Promoter pledge > 20%** — forced-selling risk at worst times
2. **Net D/E > 2× AND still rising** — leverage buying revenue, not compounding it
3. **CFO negative for 2+ consecutive years** — profits not converting to cash; accounting suspect
4. **Auditor resignation, qualification, or unexplained change in last 3 years** — auditors see the books; when they leave, they are warning you
5. **Related party transactions > 15% of revenue** — standalone numbers unreliable

If any disqualifier fires: **DISQUALIFIED. Record the reason. Move on. Do not revisit until the condition is formally resolved and at least 2 clean annual reports have followed.**

---

## THE 6-PHASE PROCESS (mandatory sequence)

### Phase 1 — Universe Construction (Quarterly)
**Purpose:** Define the pond before fishing.

- Market cap range: ₹500 Cr to ₹15,000 Cr. Below ₹500 Cr: liquidity risk, data gaps. Above ₹15,000 Cr: re-rating has likely already happened.
- Exclude automatically: CIRP/NCLT proceedings, trading suspended > 30 days, listed < 5 years, promoter holding < 25%, negative net worth.
- Tag each stock against active macro/policy cycles: Power T&D, Defence, Renewables, Semiconductor ecosystem, Railways, Water infra, Export manufacturing, Healthcare.
- Target universe: 600–800 stocks. Refresh quarterly.

**Pitfall:** Survivorship bias — only studying currently-listed stocks misses failed companies. Maintain a graveyard list of removed stocks and why.

**Output:** Tagged CSV of 600–800 stocks.

---

### Phase 2 — Hard Filter (Quarterly, runs on universe)
**Purpose:** Eliminate automatically. These are not judgment calls.

Run all 5 Hard Disqualifiers (see above). Additionally eliminate:
- Receivable days rising > 25 days over 3 consecutive years
- Any active SEBI investigation or regulatory action against promoter

**Rule:** No exceptions. "But the sector tailwind is so strong" is the exact reasoning that gets investors into frauds. The Hard Filter exists to override this in real time.

**Output:** Disqualified list with reason codes. Expect ~40–50% elimination.

---

### Phase 3 — Quantitative Score (Quarterly, after results)
**Purpose:** Score the surviving universe on 14 patterns. Surface top 20–30 for qualitative review.

Steps:
1. Pull Screener.in export: ROCE, Revenue CAGR, EPS CAGR, Debt/Equity, Interest Coverage, CFO, Promoter %, FII %, PE, P/B, Debtor Days, Creditor Days, Sales Growth 5Y, Profit Growth 5Y
2. Compute time-shifted features: use 3-year trends, not point-in-time values. Rising ROCE from 12→16→22% is a stronger signal than static 22%.
3. Score each stock using the 14 Pattern Framework (read `references/patterns.md` for full signal definitions)
4. Rank by NS. Top 20–30 (NS > 50%) proceed to Phase 4. Below 50% → Watch list. Right-quality-wrong-price (PE > 25× despite good ROCE) → Wait list.

**Pitfall:** Never override a score with recent price performance. A stock that has run 80% in 3 months may score 70% — but the entry price has already captured much of the asymmetry. Score and price are separate judgments.

**Output:** Ranked shortlist of 20–30, Watch list, Wait list.

---

### Phase 4 — Qualitative Deep Dive (Monthly, shortlisted names only)
**Purpose:** Read, not just screen. The score surfaces candidates; judgment verifies whether the story is real.

Mandatory checks:
1. **Last 8 concall transcripts, in chronological order** — look for narrative consistency vs segment data. If management claims export mix is growing, the segment revenue must confirm it.
2. **Segment margins over 5 years** — headline OPM hides everything. Check each segment's EBIT margin separately. If the "premium" segment management discusses isn't showing margin expansion, the story is aspirational.
3. **CFO vs PAT ratio** — for every ₹100 of PAT, ≥ ₹80 should appear in CFO over 3 years. Cumulative ratio < 0.7 is deeply problematic regardless of headline growth.
4. **Auditor's report** — read the emphasis of matter, qualified opinion, and auditor continuity. One unexplained auditor change = immediate exit from shortlist.
5. **Promoter pledge and OFS history** — any OFS in last 24 months while management was talking up the story requires explanation.
6. **Bear case first** — write 3 specific conditions that would break the thesis before writing the bull case. If you can't articulate 3 credible bear cases, you haven't done the work.

**Pitfall:** Confirmation bias. You found the stock via a positive screen, so you read the annual report looking for reasons to buy. The structure above forces you to check the adversarial evidence first.

**Output:** Go/No-go decision with documented bull case, bear case, and 3 specific exit tripwires.

---

### Phase 5 — Entry and Sizing (On decision)
**Purpose:** Enter at the right price with the right size. The framework works only if you actually size it.

Mandatory steps:
1. **Run Entry Math**: State entry price, current EPS, expected EPS growth rate, exit PE multiple, holding years. Compute implied CAGR. If implied CAGR < 15% at conservative assumptions, reconsider the entry price or wait. The entry math calculator is in the patearn_framework_os.jsx artifact.
2. **Size by tier**: T1 → 4–6% portfolio. T2 → 2–3%. T3 → ≤ 1%. Below T3 → no entry.
3. **Record thesis** in exactly 3 sentences: (a) what will happen, (b) the timeframe you expect it in, (c) the specific condition under which you exit if wrong.
4. **Set tripwires before entry, not after**:
   - ROCE falling below 15% for 2 consecutive years
   - Promoter pledge crossing 20%
   - Receivable days rising > 30 days in 2 consecutive years
   - Net D/E crossing 1.5× with debt still rising
   - Auditor resignation or qualification

**Pitfall:** Sizing too small on T1 setups because of uncertainty. If the framework says T1, size it like T1. Half-conviction positions don't change financial outcomes.

**Output:** Position entry with documented size, thesis, and written exit conditions.

---

### Phase 6 — Monitoring and Exit (Quarterly, every results season)
**Purpose:** Track whether the thesis is alive, evolving, or broken. Exit cleanly.

Each quarter after results, for every active holding:
1. Re-score the stock using the 14 patterns. Note which patterns strengthened, which weakened.
2. Check all 5 Hard Disqualifiers. If any fires: **exit immediately — do not deliberate, do not wait for a better price.**
3. After a 3× return: re-run Entry Math at current price. "Would I buy this today at today's price?" If the honest answer is no, write the justification. If you cannot justify it in writing, trim.
4. If the specific reason you bought has reversed (e.g. export mix declining despite management claims), exit. Even if the stock is still rising on momentum.

Apply the exit protocol from `references/exit-protocol.md`. Every holding must be classified into exactly one mode at each review: **Hold Full / Trim / Re-evaluate / Exit**.

**Pitfall:** The hardest exit is when the stock is working but the thesis has changed. Price momentum is not a thesis. Do not conflate them.

---

## SCORING DISCIPLINE — rules that prevent slippage

These are the most common places the framework degrades when applied loosely. Apply them without exception:

**On scoring:**
- Never score a signal Yes without being able to cite the specific document, page, or data source. If you cannot cite it, it is Partial at best.
- VCP and technical signals (patterns 11 and 14) must be marked as Estimated unless you have pulled actual ATR and volume data. They still count, but at 70%.
- Do not conflate a Partial with a Yes because the stock "feels right." Feelings are not signals.

**On the Quality Gate:**
- If the top 5 patterns don't pass 60% (< 144 pts), the stock cannot be T1. Period. Do not override this because the technical or ownership signals look beautiful. A stock with a perfect VCP and high promoter holding but mediocre ROCE fundamentals is a trade, not a multi-bagger setup.

**On the bear case:**
- It must be written before the score is saved. It must contain at least 3 specific falsifiable conditions — not "business could deteriorate" but "aluminium cost spike > 15% sustained over 2 quarters would compress EBITDA/MT below ₹15,000, making the current PE unjustifiable."

**On Hard Disqualifiers:**
- They are not soft warnings. They are binary exits. A stock with pledge > 20% is not a "watch" or "partial concern" — it is disqualified. Log it and move on.

**On position sizing:**
- The tier is not a suggestion. T1 = 4–6%. T2 = 2–3%. Do not size a T2 at 5% because you are "very confident" — the framework already priced in your confidence in the tier. Trust the system.

---

## REFERENCE FILES

For detailed content, read the relevant reference file:

| File | When to read |
|------|-------------|
| `references/patterns.md` | Full definitions of all 14 patterns with sub-signal Yes/Partial/No criteria, source checks, and double-count warnings |
| `references/failures.md` | 6 Indian mid-cap failure case studies (Vakrangee, Manpasand, Suzlon, Aban, PC Jeweller, Yes Bank) with anti-signals present before each collapse |
| `references/exit-protocol.md` | Full Hold/Trim/Re-evaluate/Exit decision tree with specific triggers, action, and common mistakes for each mode |

Always read `references/patterns.md` when scoring a stock. Always read `references/failures.md` when a stock scores high (> 65%) to run an adversarial anti-signal check. Always read `references/exit-protocol.md` when making an exit or sizing decision.

---

## CALIBRATION STANDARD

The APARINDS (Apar Industries) FY2021 calibration is the benchmark for the framework. Any stock that reaches T1 should score similarly on the fundamental patterns (top 5) to what APARINDS scored in mid-2021, when it was at ₹350 before its eventual ~34x move.

Apar FY2021 reference scores (from public disclosures only, no hindsight):
- ROCE: 2/2, Partial/2 → Pattern score ~1.7/2 average (COVID dip in trend)
- Operating Leverage: confirmed via 19% EPS growth on -14% revenue
- Tailwind: RDSS + Gati Shakti + PLI announced 2021 — fully Yes
- Valuation: PE 8.4× vs own median 13×, P/B 1.09×, EV/EBITDA ~3.6×
- Balance Sheet: FCF ₹226Cr, interest declining, D/E 0.23×
- Promoter: +250 bps in 3 years, zero pledge, zero dilution
- Export: 52.1% of conductor revenue, 55% of order book — export inflection confirmed
- Institutional Neglect: FII at 4.18%, 4-year low, < 5 analyst reports
- Governance flags: all zero
- Final NS: ~80%, T1, QG Pass, PAC 14/14

This is the standard. If a stock you are analysing cannot match this calibration on the top 5 patterns while also passing the Hard Disqualifiers, it should not be in your T1 portfolio.

---

## INTERACTIVE TOOL

The patearn_framework_os.jsx artifact contains the full interactive scoring interface. Use it to:
- Score stocks with live NS calculation
- View the sensitivity band
- Store scored stocks persistently
- Run the Entry Math calculator
- Review exit protocol in decision mode

The artifact is the operational layer. This SKILL.md is the methodology that governs how the artifact must be used.
