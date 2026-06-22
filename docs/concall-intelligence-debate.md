# Concall Intelligence (CCI) — Debate Synthesis & Ranked Action Record

> **Provenance:** an aggressive 8-lens adversarial debate run as a 17-agent workflow (session 27, 2026-06-21;
> run `wf_ba231db9-88f`; 1.77M subagent tokens). Lenses: Indian buy-side PM · forensic accountant/short-seller ·
> SEBI/disclosure · quant/NLP/backtest · market-microstructure · data-eng/cost/ops · behavioural linguist ·
> devil's-advocate. 3 rounds: opening critiques → cross-examination clash → moderator synthesis. The agents
> read the actual shipped code (`concall_scores.py`, `db.py`, pt14 `SKILL.md`, the D56 research doc).
> Companion to `docs/concall-intelligence-design.md`. **This is the record of improvements, India-emphasis.**

**Moderator verdict (blunt):** CCI is two products fused into one, and only one survives. **Engine A** (the
credibility / promise-follow-through ledger) is genuinely novel and non-redundant for India. **Engine B** (the
price-reaction "mispricing" alpha trigger) re-imports the exact EOD tape this repo already falsified in D56 and
should not be built until two cheap tests clear it.

The decisive flaw seven lenses converged on: **credibility is measured from the suspect's own testimony.** The
shipped scorer (`src/automation/concall_scores.py`, verified) blends absolute LLM `credibility` + `confidence`
into ~50% of the composite and fires `forward_direction='UP'` on `tone >= 60` — a *promotional-quality
detector* that ranks the best-spoken Indian frauds **highest** and routes them into the BUY bucket. Manpasand,
Vakrangee, DHFL, Yes Bank, Brightcom, Coffee Day all ran smooth, confident, numeric calls to collapse. The fix
is an **architectural inversion**, not tuning.

> **One correction the panel earned:** the quant lens's "fatal circularity" does **not** exist in the shipped
> code — `mispricing_flag` is hard-coded `None` and no price field enters credibility today. The firewall
> holds; lock it with a build-failing lineage assertion before any Phase-2 re-couples price.

---

## Ranked improvements

| # | Improvement | Problem (tied to CCI) | Fix | India | Impact | Effort | Consensus |
|---|---|---|---|---|---|---|---|
| 1 | **Forensic veto gate in front of credibility** | `concall_scores.py:144` scores credibility from the transcript; the engine ranks the best-spoken fraud highest | Wire **existing pt14 disqualifiers** (pledge, auditor exit, CFO churn, CFO/PAT, RPT) as a hard tier=D veto. Don't build new tables | ✅ | High | **Low** | Unanimous; strongest cross-lens consensus |
| 2 | **Two cheap falsification gates BEFORE any build** | Plan builds 4 tables+dashboard before testing the premise (D56 sunk-cost trap) | (a) ~2hr guidance-direction→fwd-return test; (b) residual test of credibility's *incremental* alpha after quality+PEAD controls, Newey-West t-stats | — | High | **Low** | Quant+nihilist; all confirm |
| 3 | **Flip primary deliverable to a deterioration / avoid tape** | Buy-rank re-prints Pidilite/Asian Paints (quality factor already priced); duplicates pt14 | Deterministic transcript-diff red flags (walk-back, stopped_disclosing, horizon-rolling); rank the credibility-vs-valuation *residual*, not the level | ✅ | High | Medium | Nihilist; forensic/buyside/sebi/dataops confirm |
| 4 | **Three-clock event model** | §6 uses ONE window; schema has zero timestamps | Store reg30/result/concall/transcript datetimes; fire mispricing only on the **residual-after-print** abnormal return | ✅ | High | Medium | **Over-determined**: micro+sebi+quant independently |
| 5 | **Hard liquidity / circuit / surveillance gate** | Edge lives in illiquid circuit-banded names where the gap is uninvestable; D56 proved cost kills it | Gate on ADV + circuit-CENSORED flag + delivery% + surveillance; measure half-life; `in_fno` de-weight only (no OI ingester) | ✅ | High | Medium | Micro; quant/forensic/dataops confirm |
| 6 | **Point-in-time coverage + survivorship spine** | Phased SEBI mandate (top-100 FY19→top-1000 FY25); breakers vanish from universe | `concall_coverage` keyed to as-of mandatory cohort; rebuild universe from bhav-copy archive; ABSENCE = high-severity; ISIN-keyed | ✅ | High | High | Dataops; rediscovered by 4 lenses |
| 7 | **Deterministic settlement + commitment-strength + non-monotonic specificity** | No Reg-FD → most rows have no number; specificity rewarded monotonically up-ranks value traps | Python number-comparison settlement; HARD/SOFT/DIRECTIONAL/ASPIRATIONAL; grade directional on sign-match; ABANDONED=MISS | ✅ | High | Medium | Buyside; quant/sebi/dataops/nihilist confirm |
| 8 | **Demote 10-axis table; per-speaker deviation; prepared-vs-Q&A split** | 0-100 axes are unreliable & collinear; absolute tone = long-the-loudest-promoter | Kappa>=0.6 gate; keep only countable axes; tone as z-deviation; score evasion from Q&A only; drop analyst-attributed rows | — | High | Medium | Linguist+quant+nihilist |
| 9 | **External BEAT/MISS anchor; sandbagging as a positive tell** | `headwind_adjusted` self-grades vs management's own framing — rewards lowballers | Add street/trailing-trend anchor; classify vs both; only credit headwinds stated *before* the result | ✅ | Medium | Medium | Buyside/nihilist/quant/micro/sebi |
| 10 | **Sector rubric + Ind-AS guards + COVID carve-out** | One revenue/EBITDA/PAT schema mis-reads ~40% of market; accounting artefacts mis-fire flags | `sector_profile`; suppress cash-test for lenders/cyclicals; basis tags; macro-context tags | ✅ | Medium | High | Buyside/sebi/dataops; **deferred past v0.1** |

---

## Indian ecosystem — MUST-DO

1. **Promoter pledge + auditor exit are the un-spinnable spine.** Free, numeric/binary, quarterly,
   point-in-time. Rising pledge + upbeat call = a machine-checkable Reg-31-vs-transcript contradiction =
   instant tier D. Wire pt14's existing disqualifiers. (Coffee Day, CG Power, Zee/Essel, Suzlon, Eros all
   front-ran the transcript here.)
2. **Treat "no numeric guidance" as the NORMAL case.** India has no Regulation FD; PIT Reg 3 makes specific
   undisclosed forward numbers a selective-disclosure risk, so well-advised managements stay qualitative on
   the record. Use the commitment-strength model and grade DIRECTIONAL promises on sign-match, or the ledger
   is empty exactly where the alpha is claimed to live.
3. **Invert the US "specific = credible" prior.** Serial round-number targets from promoter small-caps
   (Vakrangee "1000 stores", Manpasand "double in 3 years") are value-trap leading indicators. The Indian
   quality marker is the inverse — the terse under-promiser (Asian Paints, Pidilite, HDFC Bank pre-merger,
   Page). Make specificity non-monotonic, conditioned on a resolved-promise track record.
4. **Separate the three clocks.** Result→print gap (Reg 30 files first) ≠ concall reaction (T+0 to T+2) ≠
   transcript publish (up to 5 working days later). Measure off the first disclosure, never the lagged
   transcript. The regime is tightening (2023 Reg 30 + rumour-verification), so a 2019–2022 backtest
   over-states the 2026 edge — test the post-2024 sub-period explicitly.
5. **Gate on Indian microstructure.** Circuit bands (5/10/20%) censor the large reactions the flag depends
   on; illiquidity (₹5–50 L/day) taxes; ASM/GSM/T2T surveillance; small-caps have no F&O. The coverage
   gradient and the tradability gradient both run **opposite** to the edge gradient — target the thin
   liquid-but-not-algo-covered middle band.
6. **Coverage is a first-class point-in-time variable.** Phased mandate (top-100 FY19 → top-250 FY22 →
   top-1000 ~FY25) + frauds going dark before collapse = structural survivorship bias. Rebuild the universe
   from the bhav-copy archive (incl. delisted), not Screener's current DOM. Transcript ABSENCE is
   missing-NOT-at-random — a high-severity signal.
7. **Sector + Ind-AS realities.** EBITDA is meaningless for banks/NBFCs (credit-cost/slippage/GNPA/NIM/AUM is
   the game); pharma = USFDA 483/OAI + US launches; IT = USD/CC + TCV + attrition; cyclicals = volume-vs-
   realisation (YoY-down = cycle, not miss). Suppress definition-change flags at Ind-AS 116 (FY20) and the
   Sept-2019 tax-cut dates; carve out the COVID guidance-withdrawal quarters (Q4FY20–Q2FY21).
8. **Hinglish + lakh/crore parsing is load-bearing.** The expectation-adjusted BEAT/MISS is computed on
   numbers parsed from Hinglish/ASR text where "fifteen hundred crore" = 1500 and ASR garbles "fifteen
   percent" → "50%", silently inverting MET/MISSED. Ship a deterministic lakh/crore + spoken-number
   normaliser and a versioned India-concall hedge lexicon ("by God's grace", "going forward", "needful",
   "one-time exceptional") before extraction.

---

## Killed / corrected ideas (with why)

- **Quant's "fatal circularity"** — REFUTED on the code; firewall already holds (`mispricing_flag=None`).
  Downgrade to "add a lineage assertion to keep it that way."
- **Nihilist's "abandon CCI"** — over-reach; the deterioration/avoid side is non-redundant (sell-side
  conflicts). Re-scope, don't abandon.
- **Sebi's "transcript has no signal"** — self-refuting (would kill Engine A too). Reg 30 scrubs the
  *number*, not the *behaviour* (Q&A evasion, walk-backs, disclosure-shrinkage).
- **5 new forensic tables** — CUT; pt14 already enforces pledge/auditor/CFO/PAT/RPT as binary vetoes. Wire,
  don't rebuild a forensic-accounting platform off brittle annual-report PDF parsing.
- **F&O OI / PCR / IV-crush ingester** — CUT; Ramana already vetoed F&O in D56. The free `in_fno` boolean
  suffices to de-weight.
- **`mgmt_archetype` classifier as a scoring input** — CUT; a second uncalibrated LLM layer compounding
  drift, fails the kappa≥0.6 gate. Keep only a cheap deterministic `ir_agency` display tag.
- **Code-switch-density / externalisation-shock-calendar** — CUT; ASR artefacts, untestable.
- **Stored global 1..N cross-universe rank** — CUT; India's staggered ~6-week results season makes it a
  "who-reported-most-recently" rank. Store self-relative time series + dated red-flag events; derive
  cross-sectional comparison on read within freshness-matched cohorts.
- **Sector-specific rubrics as a v0.1 requirement** — DEFERRED, not killed (4–5× prompt/golden-set surface).
- **D56 as a blanket "EOD tape has no signal → kill CCI"** — CORRECTED; D56's actual verdict is the precursor
  was real/gross-positive/OOS-robust and failed only as a beta-0.43 standalone book, and the doc explicitly
  names the concall qualitative layer as the **next frontier**. D56 points AT Engine A, not away from it.

---

## Open disagreements for Ramana to decide

1. **Ship-or-merge** if the residual test passes *weakly*: a standalone overlay vs a pt14 sub-pillar.
2. **How hard the forensic gate vetoes honest cyclicals/NBFCs** — which disqualifiers are universal (pledge,
   auditor exit) vs sector-suppressed (CFO/PAT, cash conversion, where negative CFO is structural).
3. **Whether Engine B (price-reaction mispricing) is built at all** — ship only Engine A, or gate Engine B
   behind the half-life + three-clock test. The rank-#2 falsification is designed to settle this.
4. **Street-consensus anchor feasibility** — does the trailing-trend stand-in work in the small-cap edge
   zone, or does sandbagging-detection only work where consensus exists (i.e. where the edge is arbitraged)?
5. **Backfill cost/sequencing** — make claude.ai-subscription the DEFAULT for the ~96k-transcript historical
   bulk (₹0 marginal) and reserve Gemini for steady-state incremental; scope to the covered cohort, not the
   full ~4000-name universe.

---

## Recommended sequencing (the panel's ordering — which the current design §9 phasing INVERTS)

1. **Forensic-veto wiring + the two cheap falsification gates + point-in-time universe from bhav-copy** —
   cheap, kill-or-save.
2. **Only if that survives:** firewalled credibility hit-rate + deterministic settlement, validated on a
   labelled blow-up set (Manpasand / Vakrangee / DHFL / Yes Bank / Brightcom / Coffee Day / PC Jeweller vs
   Asian Paints / HDFC-pre-merger / Pidilite / Page), scored as-of 2–4 quarters BEFORE discovery.
3. **Only if it discriminates frauds:** the pre-registered residual-vs-quality backtest.
4. **Dashboard last.**

Carry CCI as a screen/overlay until the backtest clears it — the same honest *screen-not-book /
confirmation-not-prediction* stance the project already adopted for explosive-move.
