# The STRATEGY-FAMILIES FRAMEWORK — organizing the >15% CAGR corpus into governed families

> **Class: DESIGN(live) / LIVING design-of-record.** Registered in `docs/DOC_INDEX.md` §B. Opened by
> Ramana's directive 2026-07-17 (below, verbatim). This is the **meta-organization layer** over the whole
> research corpus — it does not create or modify any strategy; it inventories, groups, labels, and governs
> the strategies that already exist in `docs/strategy-ledger.md` + `docs/strategies/*`.
>
> **⚠ STATUS: DIRECTIVE RECORDED + FRAMEWORK PROPOSED — AWAITING OWNER RATIFICATION.** No strategy,
> seal, or model-portfolio has been changed. §1 is the intent as given; §2–§6 are my proposed framework,
> to be confirmed/corrected by Ramana before the inventory (§7) runs.

---

## §1 The directive (Ramana, 2026-07-17 — recorded verbatim, before any change)

Captured in Ramana's own words so the intent is preserved exactly (my structured reading is §2 onward,
clearly separated so nothing is put in his mouth):

> "I also want to include the highest-CAGR components we discussed over the past few days, since we
> started, across all sessions and threads. For any strategy that achieved a CAGR above 15%, we need to
> conduct a thorough review. We should familiarize ourselves with them and group similar tweaks into
> families."
>
> "If we treat the various turns as a single group, the conversation will change. It's a ballgame, so we
> need to decide when to move, when to remove, and how to assign responsibilities. How can we plan this
> framework properly?"
>
> "Now we have a modern model portfolio that needs to be organized. Please record my intent accurately
> before we proceed with any changes."

Also standing from the same message: *drawdown is inherent to the equity component* (accepted — the
diversifier legs, not strategy changes, are how drawdown is managed), and *"I'm fine with what you're
trying to do"* (the portfolio-layer direction continues).

**My one-sentence restatement (for confirmation):** *Take every strategy/variant with CAGR > 15% found
across the entire research history (all sessions/threads treated as one corpus), review each thoroughly,
group them into families by shared levers/tweaks, and stand up a governance framework — when to promote,
when to retire, who is responsible — so the "modern model portfolio" is assembled from vetted family
heads, not from raw CAGR.*

---

## §2 The load-bearing principle (must be settled before the register is built)

**CAGR > 15% is a SCREEN, not a verdict.** The estate's own ledger repeatedly shows high-CAGR strategies
that die at realistic cost — RISKADJ 28.6% is flat-cost paper that fails at participation cost; C-BLEND
1.32 is flat-cost-only, "NOT fundable"; the sector two-step (D141) was rejected at realistic cost. So the
register's FIRST job is to sort **REAL** (net-of-cost, forward-viable) from **PAPER** (flat-cost-only)
from **FALSIFIED** (killed with numbers). **Family membership is by LEVER; fundability is by STATUS
(§4).** Grouping by CAGR without status would resurrect already-falsified books — which the failure-
ledger discipline forbids (falsified = BLOCKING; cite the numbers before any re-attempt). *This is the
"thorough review" Ramana asked for, made into the framework's spine.*

---

## §3 The Register — one row per >15% CAGR strategy/variant

The single organized inventory. Columns:

| field | meaning |
|---|---|
| **name / tag** | strategy or variant + its `strategy-ledger.md` tag |
| **family** | its lever-lineage group (§5) |
| **CAGR (headline)** | the reported in-sample CAGR |
| **CAGR (net-of-cost)** | after the estate's participation-cost model — the number that matters |
| **levers / tweaks** | the knobs that define it (selection, cap, cadence, sleeve, trail, weights…) |
| **status** | FUNDABLE · SEALED · CANDIDATE · PAPER · FALSIFIED (§4) |
| **prereg / seal** | hash-frozen prereg ref if any |
| **origin** | 🧑 human-idea · 🏠 house-engine · 📚 literature (the existing taxonomy, `docs/strategies/origins.md`) |

Sources to sweep: `docs/strategy-ledger.md` (the 15x/16x tags), `docs/strategies/*` (17 canonical pages),
the factor zoo (`out/factor_zoo.csv`), the model-portfolios estate, `docs/strategies/union-ladder.md`
(the union family compendium already complete).

### §3a THE REGISTER — inventory v1 (2026-07-17, 3-agent read-only sweep of ledger + 17 pages + factor zoo)

**Status tally (distinct strategies, sweep-batches consolidated):** FUNDABLE **1** · SEALED **4** ·
CANDIDATE **3** · PAPER **~20** · FALSIFIED **many** (whole families walled). **The headline of the whole
sweep: exactly ONE strategy is fundable net-of-cost, and its net CAGR is modest (~13–18%). Every CAGR
above ~24% is either in-sample-and-forward-untested (union family) or flat-cost PAPER that dies at
participation cost.** This is the §2 principle, confirmed across the entire corpus.

**FAMILY 1 — Momentum-selection (Union)** · head: **COMPOSITE-30** (sealed lead), A2 (lower-DD alt)

| strategy | tag | CAGR (PR / TR) | honest fwd | status | key lever added |
|---|---|---|---|---|---|
| Union | 16V | 17.5 / 18.1 | 15.7 (deflated) | SEALED `a9a14058` | 6b-recovery ∪ RSI-trend, top-60 EW |
| β14 | 16Y | 18.1 / 18.7 | 16.6 | SEALED `08b46199` | + trailing-β≤1.4 at selection (fixes 2012-17) |
| C40RA | 16AB | 21.0 / 21.8 | 18.1 | SEALED `0715a0d9` | + RISKADJ-rank + top-40 |
| **COMPOSITE-30 (K30)** | 16AF | **26.4 / 27.3** | **21.6** | SEALED `07ef2ef9` | + era-floor + top-30 + let-winners-run (PBO 0.043) |
| A2-composite | 16AE | 25.5 / 26.3 | 21.0 | CANDIDATE (reg-ready) | era-floor clamped; lower DD (−27.2); small/mid tilt |
| A1-composite | 16AE | 25.6 / 26.4 | — | CANDIDATE (dominated by A2) | raw floor, no clamp |
| B1 rf-cash | 16AE | 21.4 | — | CANDIDATE (measurement) | idle earns rf; reporting-only |

*Falsified/paper tail (all with numbers): inverse-vol sizing · throttles (16W) · 16Z reject batch ×10
(15.9–17.3) · 16AC reject batch ×7 · ML rankers M1/M2 (prereg-rejected, β = #1 feature 3×) · monthly
cadence (cadence law, 4 confirmations) · component engines RSI+consist70 15.6 / 6b-recovery 15.4.*
Forward test fires **2026-10-03**; adjudication graduates ≤1.

**FAMILY 2 — Sector-rotation** · head: V21 (live) / V24 (designated) — ⚠ **HALF-BUILT: picks SECTORS not stocks**

| strategy | tag | CAGR | status | note |
|---|---|---|---|---|
| V21 | 15d | 16.57 | PAPER (LIVE `/dash/sector-rotation`) | index-only; flat-cost-optimistic |
| V24 | 15f | ~17.2 | PAPER (designated carry-fwd) | best DD; statistically ≈ V21 (D139) |
| two-step sector→stock | 15l (D141) | 16.7 net | **FALSIFIED** | the stock build — loses to V24 at realistic cost |
| V32 + Round-4 rejects | 15f/15i | 15.1–17.9 | FALSIFIED | V32 retired (≈ V24, more complex); rest worse DD |

⚠ ~⅜ of sectors have no liquid ETF → the number may be untradeable. Upper bound on a paper portfolio.

**FAMILY 3 — Low-vol / risk-adjusted momentum** · head: **LOWVOL_MOM** (the one fundable corner)

| strategy | tag | CAGR | status | note |
|---|---|---|---|---|
| **LOWVOL_MOM / STEADY-25** | Tier-1 / #602 | flat 18.5 · **net ~13–18% (AUM-dependent)** | **FUNDABLE** (rule-lab prereg `31d4fe11`, S163-signed) | net return/vol 1.19 @₹75cr — the ONLY participation-fundable book; capacity ~₹50–100cr; net CAGR modest ⚠ needs one clean number |
| RISKADJ engine | Tier-1 | 28.6–35.4 flat · **−1.4 net** | PAPER (internal 0.89 benchmark) | dies at participation cost (~36%/yr); beta not skill |

**FAMILY 4 — Factor-books (the factor zoo)** · head: none fundable (all PAPER/FALSIFIED, flat-cost)

RISKADJ 35.4 · MOM12 37.6 · RESID_MOM 30.2 · MOM6 30.0 · VAL_MOM 24.4 · HI52 24.2 · QUAL_MOM 23.5 ·
QMV 20.4 · EARN_YIELD 17.5 — **all flat-cost PAPER; every headline collapses net of participation cost**
(`cost_realism.csv`). C-BLEND (ret/vol 1.32) flat-cost champion, not fundable. **BOOK_YIELD 16.2 =
FALSIFIED** (β1.54, MaxDD −82%, α<0 — the ledger's hard-reject wall). VAL_MOM/QMV fail walk-forward.

**FAMILY 5 — Relative-strength** · descriptive lens suite (RRG · RS-band · rotation · Mansfield): PAPER,
never trades as a book ("no RS lens is fundable alpha") — it is selection/context input to Family 1.

**FAMILY 6 — Portfolio-allocation (the layer above)** · head: the allocation dial + **STEADY-25**

- Descriptive dials: book+G-sec (16AN) · book+gold (16AP) · three-asset (16AR) — PAPER, the survivability dial.
- **The LIVE "modern model portfolio" (`src/automation/auto_portfolios.py`): PACER-25 (wraps RISKADJ) ·
  SPRINTER-25 (MOM12) · CRAFTSMAN-25 (QUAL_MOM) — all admitted GROSS-LENS PAPER; STEADY-25 (wraps
  LOWVOL_MOM) — the one resting on a fundable config.** *This is the estate the directive wants organized.*

**FAMILY 7 — Other (descriptive / veto-only, no fundable book):** CCI (factor falsified → veto-only) ·
MEP (descriptor-only, DSR-failed) · DVPT (picker refuted, within-stock only) · patearn (risk-filter, not
a ranker) · classic-screens (value/book-yield hard-rejected) · CPR / harmonic / wolfe (descriptive
charting; wolfe/harmonic BULL show a modest selection edge, never trade) · reversal-context (falsified at
all 4 levels) · rule-lab (an evidence TOOL, not a strategy).

**Provenance:** 3-agent sweep — ledger (all 3,258 lines) + 17 strategy pages + `factor_zoo.csv` /
`strategy_leaderboard.csv` / `cost_realism.csv` + `auto_portfolios.py`. Numbers are as-recorded; all
Union-family CAGRs are IN-SAMPLE (read against the deflated fwd column). Review actions surfaced: (i) pin
LOWVOL_MOM's single net CAGR; (ii) the model-portfolio estate is 3/4 gross-lens — the §6-governed
re-organization should build from FUNDABLE/SEALED heads only.

---

## §4 Status labels — the honesty spine (a strategy carries exactly one)

- **FUNDABLE** — survived net-of-cost + falsification (+ ideally forward/OOS). *Currently exactly one:
  LOWVOL_MOM qtr large-cap (net return/vol 1.19 @₹75cr, the S163-signed NEW-BENCHMARK).*
- **SEALED · forward-testing** — pre-registered, hash-frozen, awaiting the 2026-10-03 forward verdict.
  *The union family: union · β14 · C40RA · COMPOSITE-30.*
- **CANDIDATE / LEAD** — measured, promising, not yet sealed. *A2-composite; the portfolio-layer dial.*
- **PAPER / DESCRIPTIVE** — high CAGR but flat-cost-only / not net-of-cost viable. *RISKADJ 28.6%,
  C-BLEND 1.32, the MEP/CCI/Wolfe descriptive-only books.*
- **FALSIFIED / RETIRED** — killed with numbers; lives on the ledger wall (nothing discarded).
  *The unconditioned-RS family, the reversal family, V32 (dominated by V21, D139).*

---

## §5 Families — grouping by shared lever-lineage (initial cut, to be confirmed in the review)

Membership is by the LEVER a variant tweaks, not by CAGR. Each family has a **head** (its current lead)
and members (variants + retired attempts). Proposed initial families:

- **Momentum-selection (the Union family)** — union · β14 · C40RA · COMPOSITE-30 · A2 + all `union_lab*`
  variants. Lever: quarterly momentum selection + beta-cap + risk-adj rank + trail + era-floor. Head:
  **COMPOSITE-30** (sealed lead), A2 (deferred, lower-DD). Compendium: `docs/strategies/union-ladder.md`.
- **Sector-rotation** — V21 (live) · V24/V32 (retired) + the two-step (rejected). Lever: sector RS rotation.
- **Low-vol / risk-adjusted momentum** — LOWVOL_MOM (FUNDABLE) · `momentum-riskadj`. Lever: low-vol × momentum.
- **Factor books** — from the factor zoo (QMV, single/blended factors). Lever: factor tilts. Mostly PAPER.
- **Relative-strength / rotation** — the RS-rotation, RRG, reversal-context work. Lever: RS shape.
- **Portfolio-allocation (the new layer)** — book + G-sec + gold fixed-mix. Lever: cross-asset weights.
  This family sits ABOVE the others (it allocates across their heads). DoR: `docs/portfolio-layer-design.md`.

(Others — CPR, harmonic, Wolfe, CCI, MEP, classic-screens — are mostly descriptive-only and enter the
register at PAPER/DESCRIPTIVE; the review confirms placement.)

---

## §6 Lifecycle governance — when to MOVE, when to REMOVE, who is RESPONSIBLE

- **PROMOTE ("move up") a family head** — only through the existing pre-registered gates, never on
  in-sample CAGR: net-of-cost survival → seal (hash-frozen prereg) → forward / OOS pass → FUNDABLE. The
  2026-10-03 union forward test is exactly this gate firing.
- **RETIRE ("remove")** — when falsified net-of-cost, failed OOS, or **dominated by a simpler sibling**
  (the D139 precedent: V32 retired for the statistically-indistinguishable, higher-capacity V21). Retire
  to the ledger wall + a `FALSIFIED` register row; **never delete** (nothing discarded — a failing family
  is evidence about the family).
- **RESPONSIBILITIES (roles):**
  - *Research lanes (sessions/agents)* — build + measure variants; feed the register; cite the ledger before re-attempting.
  - *Validation suite* (`union_ladder_val.py` prereg + deflation + PBO/CSCV + the forward runner) — the gate that a promotion must clear.
  - *Machine gates* (`tests/test_*`) — enforce the labels (retvol-label, docs-coverage, pat-coverage).
  - *Owner (Ramana)* — ratifies seals, promotions, retirements, and the model-portfolio composition. **The framework proposes; the owner disposes.**

**The "modern model portfolio"** is assembled ONLY from FUNDABLE / SEALED family heads as building
blocks, with the portfolio-allocation layer (book + G-sec + gold) on top — never from PAPER or raw-CAGR rows.

---

## §7 Execution plan (runs only after §1 intent is confirmed)

1. **Inventory** (read-only sweep → the §3 register). Breadth suits delegated agents over the ledger + the
   17 strategy pages + the factor zoo; each returns structured rows, I synthesize the register.
2. **Review** each row (levers, net-of-cost, status) → families crystallize (§5 confirmed/revised).
3. **Ratify governance** (§6) with Ramana.
4. **Organize the model portfolio** from the vetted heads + the allocation layer.

Nothing in steps 2–4 changes a sealed strategy; any strategy/portfolio change is a separate,
owner-ratified step.

---

## §8 Phase 4 — the RE-ORGANIZED MODEL PORTFOLIO (DRAFT proposal, awaiting ratification)

**Status: TIER STRUCTURE RATIFIED by Ramana (2026-07-17). Action #1 (relabel Tier D) SHIPPED** — the
three gross-lens books (PACER-25 · SPRINTER-25 · CRAFTSMAN-25) on the live `/dash/model-portfolios` now
carry an explicit "GROSS-LENS DEMONSTRATION — not fundable net of participation cost" banner + the RISKADJ
gross→net evidence (35.6%→−1.4%), and STEADY-25 is labelled the ONLY fundable book. **Action #2 (pin +
promote STEADY-25) SHIPPED** — net CAGR PINNED (freshly re-verified 2026-07-17 via `cost_participation.py`,
reproduces 16AE/#602 to the digit): capacity-tiered **19.2% @₹25cr · 18.1% @₹50cr · 16.5% @₹100cr (index
15.3%), ceiling ~₹150cr** — the 13.3% crude-cost figure is dead. STEADY-25 now shows a green **FUNDABLE
CORE** banner with that curve. **Action #3 (wire the Tier-B ballast overlay) SHIPPED** — STEADY-25's
OWN ballast dial measured (ledger 16AX; the 16AN/AR dials were the union book): already-defensive STEADY
still benefits — a modest G-sec/gold sleeve ~HALVES MaxDD (−19% → −9 to −13%) for ~1–2pp CAGR, every mix
beats the index; the STEADY-25 page now carries a "🛟 Survivability overlay" dial (80/10/10 balanced
default). **Action #4 (stage Tier C — union head as "graduating candidate, funds only after 2026-10-03")
remains**, owner-ratified before shipping.

**The honest headline (say it first, above the structure):** the portfolio you can *actually run today* is
**modest** — a defensive low-vol-momentum core (~16–18% net, capacity ~₹100cr) plus bond/gold ballast for
survivability. The exciting high-CAGR books are either **forward-pending** (the union family, verdict
2026-10-03) or **gross-lens paper** (the factor books). The real edge here is **survivability engineering
(uncorrelated ballast) + PIT-data rigor**, NOT high-octane alpha. Scale matters: this is a **personal /
small-scale** portfolio (fits Ramana's own capital) — at personal scale the union family's small/mid-cap
tilt is executable; at institutional scale it is not (capacity "presumed poor, untested", `16AE`).

**The proposed structure — four tiers by STATUS, not by CAGR:**

| tier | contents | role | can real money go here? |
|---|---|---|---|
| **A — FUNDABLE CORE** | **STEADY-25 / LOWVOL_MOM** (net 1.02 @₹50cr / 1.19 rule-lab #602 vs index 0.89; net CAGR 16–18%; DD −21 to −27%; cap ~₹100cr) | the one book that survives realistic cost | **YES — today** |
| **B — SURVIVABILITY LAYER** | the allocation dial (`portfolio-layer-design.md`): equity-core + **G-sec** ballast (± a modest **gold** sleeve). e.g. **80/20** core/G-sec, or **80/10/10** core/G-sec/gold | cut drawdown via ~zero-corr assets; owner picks the risk point | YES (primary-source, descriptive dial) |
| **C — SEALED, FORWARD-PENDING** | the **union head COMPOSITE-30** (+ β14/C40RA/A2 siblings); deflated fwd ~21.6% | high-potential satellite, **shown not funded** until it clears the 2026-10-03 forward test | **NOT until Oct-3** — and ⚠ its realistic-participation cost/capacity is UNVERIFIED (only slippage-stressed); personal-scale only |
| **D — GROSS-LENS / DEMONSTRATION** | **PACER-25** (RISKADJ) · **SPRINTER-25** (MOM12) · **CRAFTSMAN-25** (QUAL_MOM) | educational lenses — "what raw momentum/quality look like GROSS" | **NO — relabel as demonstration, never presented as investable** |

**Retired to the wall (nothing deleted):** BOOK_YIELD (hard-reject β1.54/DD−82%) · the two-step
sector→stock (D141) · throttles · inverse-vol · ML rankers · the reversal family — all FALSIFIED with numbers.

**The concrete re-org actions (each owner-ratified before it ships):**
1. **Relabel Tier D** (PACER/SPRINTER/CRAFTSMAN) on `/dash/model-portfolios` as "gross-lens demonstration —
   not fundable net of cost," with the `cost_realism` net number shown beside each gross CAGR. *(The single
   highest-integrity change: it stops three paper books from reading as investable.)*
2. **Promote Tier A** (STEADY-25) to the labelled FUNDABLE CORE, with its one pinned net CAGR (review
   action (i) — resolve 16.5 vs 18.1 to a single agreed figure first).
3. **Wire Tier B** as an optional overlay on the core (the 80/20 or 80/10/10 dial), descriptive.
4. **Stage Tier C** as "graduating candidate — funds only after 2026-10-03," with the participation-cost
   caveat visible.

**What this does NOT do without a further prereg:** register the union head as fundable before its forward
test; fund any Tier-C/D book; add dynamic/timed weights to Tier B (the §8 hard bar of the portfolio-layer
design still binds). The model portfolio is organized by *honesty of status*, and the owner disposes.
