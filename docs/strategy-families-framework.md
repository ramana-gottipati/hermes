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
