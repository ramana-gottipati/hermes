# Documentation Index (living map)

> **Status:** regenerated 2026-06-29 from **two independent passes** — Claude's Phase-0
> inventory + Codex (`gpt-5.5`) round-1/round-2 review (see `codex-bridge/resp-01…`,
> `resp-04…`). **Posture: DEFER-ALL.** Parallel lanes were editing docs as recently as
> 01:25 today, so **nothing is archived, moved, or deleted** — this is a map + a set of
> safe rules, not a cleanup event. Both agents agreed: additive work only until the
> owning lanes quiesce, then a fresh pass before any `git mv`.
>
> **This file is a living map, not a one-time audit** — it will drift as parallel lanes
> add docs. Re-run a fresh classification before acting on the ARCHIVE? section.
>
> **Round-3 update (2026-06-29):** a Codex verification pass confirmed the core hardening
> is faithful (hard-freeze, four-gate, DEFER-ALL all PASS) and folded in 5 newly-added
> lane/nav docs; `CLAUDE.md` timer wording reconciled to match `AGENTS.md`. **Note:** the
> doc count is climbing through the session (53 → 62 as lanes spawn status docs) — treat any
> count here as a snapshot. The authoritative completeness check is the **disk-vs-index diff**
> (compare `docs/*.md` on disk against the names referenced here), not this file's own tally.
>
> **Round-4 update (2026-07-14, S131/D128):** the `doc_hygiene_gate.py` ratchet now machine-checks
> disk-vs-index. This pass closed the coverage gap — the 35 previously-unindexed docs are catalogued
> below (A/B/C/D/E/F) and 32 transient docs carry `Lifecycle:` banners; lane docs (`L<N>-*`,
> `parallel-sessions-*`, `CARRY-FORWARD-*`, `*-LANE-*`) stay covered by the by-rule clause.

## Classes
`CANONICAL` keep indefinitely · `DESIGN(live)` design-of-record for shipped/in-build
feature · `DESIGN(stale)` design not built / partly superseded (keep, trim later) ·
`RUN-BOOK(active)` transient but retire-condition NOT yet fired · `REFERENCE`
methodology / external / catalog · `ARCHIVE?` candidate, **deferred** (verify + fold +
`git mv` only when the tree is quiet; never delete).

---

## A. CANONICAL (15)

| Doc | Why |
|---|---|
| `PROJECT_STATE.md` | Running source of truth. |
| `CLAUDE.md` | Claude orientation twin. |
| `AGENTS.md` | Codex orientation twin. |
| `README.md` | Repo readme. |
| `docs/strategy-ledger.md` | Benchmark ledger ("nothing discarded"). |
| `docs/zerodha-cost-gauntlet-2026-07-18.md` | Research record (ledger 16BC, S196): factor baskets vs union family net of REAL Zerodha cost 2005-2026 + capital-gains tax. Factor baskets don't beat the index; K30/A2 do in-sample (+17.8/+17.2 vs +11.7); K30 capacity ceiling ~₹25-50cr; Codex-validated. Companion: the 17-sheet investor xlsx. |
| `docs/codex-stock-selection-brief.md` | TRANSIENT hand-off brief: the two-step sector→stock strategy's full state (§15h…§15Q, D141/D142) synthesized into one problem statement for an external solver. Retire once its build lands and folds into strategy-ledger.md/sector-rotation.md/PROJECT_STATE.md. |
| `docs/SURFACE-PLAYBOOK.md` | BINDING playbook for adding any user-facing screen/page/tab — sister-data check, lens registry, education/fence/Pat/CSV landing checklist (twins: CLAUDE.md #9 / AGENTS.md #7). |
| `docs/strategies/origins.md` | Canonical provenance map (S132j): every strategy labeled RAMANA / HOUSE / CLASSIC + the binding origin-labeling rule + the external-sources policy + the documentation loop. |
| `docs/strategies/` (index: `README.md`) | Canonical strategy reference layer (S109) — one page per strategy (definition · status · terminology). Links to design docs; never duplicates ledger/weights. |
| `docs/metrics-glossary.md` | Metric definitions source. |
| `docs/pat-knowledge-contract.md` | BINDING contract — Pat's three self-feeding knowledge sources (glossary auto-fold · registry auto-fold · inline flows) + the same-commit rule, machine-enforced by `tests/test_pat_coverage.py` (twins: SURFACE-PLAYBOOK items 5+6 / CLAUDE.md #9 / AGENTS.md #7). |
| `docs/product-strategy-2026.md` | Product / PO strategy reference. |
| `docs/ui-architecture-v2.md` | Canonical IA / schema doc. |
| `docs/SESSION-PROTOCOL.md` | Binding per-session start/end checklist (CLAUDE.md boot references it). |
| `docs/worktree-convention.md` | BINDING working-tree isolation convention — one worktree per concurrent lane (`scripts/new-lane.sh` / `retire-lane.sh`) so a sibling session's `git add`/`reset` cannot absorb or wipe your work; consolidated worktree gotchas (twin: SESSION-PROTOCOL § HOW THE SESSION RUNS). |
| `docs/FABLE-PROTOCOL.md` | BINDING model-parity operating doctrine — the strongest-model session behavior (boot stance · loop · falsification battery · stop-condition escalations · tier routing/hybrid) executable by ANY model tier (twins: CLAUDE.md #10 / AGENTS.md #8). |
| `docs/calculations-and-weights.md` | Canonical single-source explainer of every analytical weight + formula. |
| `docs/patearn-charter.md` | CEO-mode operating doctrine + NOW roadmap (amended by the Decision log). |
| `docs/patearn-analytics-company-plan.md` | Company-level plan (D134): analytics-company posture + validated regulatory boundaries + adaptable layers L0–L8 + structured cost model + the rated component roadmap. |

## B. DESIGN(live) — design-of-record, keep (27)

| Doc | Note |
|---|---|
| `docs/x-setups-render-spec.md` | TRANSIENT hand-off: the X-setups render-lens build spec (data spine LIVE S205/S207; render owner/redesign-gated). Retire when the lens ships. |
| `docs/concall-intelligence-design.md` | P1–P7 built/deployed; only data remains. |
| `docs/cci-backtest-methodology-and-review.md` | Design-of-record + panel review. |
| `docs/cpr-strategy-design.md` | Built, verified, live. |
| `docs/chart-redesign-design.md` | Durable chart design; stock wire pending. |
| `docs/harmonic-pattern-design.md` | Scanner/UI live, backtest-gated. |
| `docs/wolfe-wave-design.md` | Built/live descriptive lens. |
| `docs/wolfe-rules.md` | Rules of record; advanced tier partly built. |
| `docs/mep-strategy-design.md` | Rollout complete/deployed/verified. |
| `docs/rs-rotation-design.md` | Stages 1–3 shipped/live. |
| `docs/rs-band-support-resistance-design.md` | Live RS band/range lens. |
| `docs/ignition-champion-challenger-design.md` | All three components done; design = record. |
| `docs/tracker-segments-spec.md` | Active tracker content spec. |
| `docs/ui-design.md` | UI doctrine, no-regression guardrail. |
| `docs/ui-redesign-2026-06.md` | Proposed/build-gated redesign with no-loss map. |
| `docs/pat-design-and-improvements.md` | Pat living spec/backlog. |
| `docs/data-licensing-decision.md` | Decided migration plan. |
| `docs/pitch-demo-and-positioning-DECISIONS.md` | Decided positioning calls to fold into decision log. |
| `docs/navigation-and-structure-review.md` | Review draft, not yet decided/built. |
| `docs/nav-ia-DECISIONS-and-prompts.md` | Scope×Lens nav IA — Ramana-approved, LOCKS the IA. |
| `docs/color-system-alignment.md` | Colour-token alignment design-of-record; Phases 0–4 shipped, tail open. |
| `docs/fundamentals-xbrl-migration.md` | DoR for the Screener→NSE/BSE-XBRL fundamentals migration (Guardrail #8). |
| `docs/fundamentals-xbrl-phase3-backfill.md` | Phase-3 build/decision plan: XBRL historical backfill + Screener retirement (Guardrail #8). |
| `docs/momentum-engine-formalization.md` | Living spec: gross-momentum selection → production ranking lens. |
| `docs/premium-visuals-brainstorm.md` | Living design program for the premium-visuals / infographics uplift. |
| `docs/rs-momentum-divergence-roadmap.md` | Living master plan: RSI-of-RS + divergence + recovery ecosystem. |
| `docs/ux-journey-audit-2026-07-13.md` | Joint Claude+Codex UX/IA audit of record + S-A…S-H program tracker. |
| `docs/portfolio-layer-design.md` | DoR for the portfolio-construction layer (16AN): fixed-mix book+G-sec weights policy on the measured dial, rebalance band, gold leg pending primary data, drawdown-target-as-policy-not-signal. Descriptive; no registration. |
| `docs/strategy-families-framework.md` | DoR for organizing the >15% CAGR corpus into governed families (Ramana directive 2026-07-17): the register, status labels (fundable/sealed/candidate/paper/falsified), families by lever-lineage, promote/retire/responsibility governance. Meta-org only; no strategy changed. Awaiting owner ratification. |
| `docs/redesign-plan-2026-07-17.md` | The web-experience redesign plan of record (Focus + Rails, term chips, 6 destinations, M0–M8). M0–M2 owner-approved + built; M3–M8 pending. TRANSIENT — folds into SURFACE-PLAYBOOK + PROJECT_STATE on full ratification/rejection. |
| `docs/redesign-coordination.md` | Redesign approval + communication record — verdict grammar, Codex/Gemini verdicts + dispositions, module status. THE single source for redesign-program approvals. |
| `docs/metric-verdicts.md` | Term-chip sidecar: per-metric Verdict · How-it-could-improve · Origin lines (parsed only by `src/web/term_chip.py`; definitions stay in `docs/metrics-glossary.md`). |
| `docs/codex-review/REDESIGN-M0M2-CODEX.md` | Codex channel record: redesign plan review verdict (M0–M2 focus), verbatim. |
| `docs/redesign-m6-journey-spec.md` | M6 guided-journey module spec (one-shot nudge · persistent help · teaching empty states — tourless per the ratified evidence). TRANSIENT — build only on owner go; folds into the coordination record on landing. |
| `docs/redesign-m4-stock-hub-spec.md` | M4 stock-hub module spec (evidence-scroll per the ratified contracts). TRANSIENT — build only on owner go; folds into the coordination record on landing. |
| `docs/codex-review/M4-STOCK-HUB-CODEX.md` | Codex channel record: M4 stock-hub spec review verdict, verbatim (1 BLOCKING + 6 ADVISORY, dispositioned in redesign-coordination.md §3b). |
| `docs/codex-review/REDESIGN-M4SPEC-CODEX.md` | Codex channel record: the parallel M4 spec pre-build verdict (OBJECT → v1.1 fixes), verbatim — the two passes are reconciled in the spec's status block. |
| `docs/redesign-graphite-home-spec.md` | The fresh-and-parallel Graphite Home build spec (v1.2, REVIEW-CLEAN) — new isolated `/dash/home` section, per-zone reads, isolation/AA gates, deploy + gated retire plan. TRANSIENT — folds into the coordination record + PROJECT_STATE at cutover. |
| `docs/graphite-home-carryforward.md` | Graphite Home carry-forward + takeover prompt — LIVE state, this session's arc, the binding corrections, the open feedback (rearrange/organize · Market-Pulse more entries · watchlist/portfolio · real-vs-demo honesty · response calibration), deploy recipe. TRANSIENT — retire at cutover. |
| `docs/codex-review/GRAPHITE-HOME-SPEC-CODEX.md` | Codex channel record: Graphite Home spec review (OBJECT v1.0 → convergence APPROVE-WITH-CHANGES → v1.2), verbatim dispositions. |
| `docs/codex-review/REDESIGN-PROTOTYPE-CODEX.md` | Codex channel record: the v3 experience-prototype review (OBJECT, 8 BLOCKING + 2 ADVISORY), dispositions in redesign-coordination.md. |

## C. DESIGN(stale) — keep, trim superseded sections later (6)

| Doc | Note |
|---|---|
| `docs/rs-ratio-analysis-design.md` | "to build" but D39/D40 shipped; reconcile. |
| `docs/multi-timeframe-positioning-design.md` | Agreed but not built. |
| `docs/dvpt-picking-strategy-design.md` | Thesis empirically revised; preserve reframe. |
| `docs/explosive-move-research.md` | Working doc; thesis revised, launchpad not fully retired. |
| `docs/screener-merge-plan.md` | Plan to give Screen+ the original Screen's pictorial instruments. |

## D. RUN-BOOK(active) — transient, retire-condition NOT fired, KEEP

**Docs (30):** `docs/parallel-lane-prompts-D134.md` (paste-ready lane prompts + relay protocol
for the analytics-company plan; retire when all lanes LANDED) · `docs/time-machine-audit.md`
(LANE-F as-of capability audit, 67 lenses; retire → fold into plan §4-F) ·`docs/concall-intelligence-NEXT-SESSION.md` · `docs/wolfe-NEXT-SESSION.md`
· `docs/mep-NEXT-SESSION.md` · `docs/next-session-handoff.md` ·
`docs/dashboard-deepen-NEXT-SESSION.md` · `docs/rrg-rotation-NEXT-SESSION.md` ·
`docs/ui-redesign-EXECUTE.md` · `docs/ui-cockpit-NEXT-SESSION.md` ·
`docs/ui-perf-handoff.md` · `docs/perf-architecture.md` ·
`docs/ui-restore-and-migration-TRACKER.md` · `docs/lane-a2-native-ui.md` ·
`docs/lane-d-knowable-at-and-veto-2026-06-28.md` · `docs/pat-f2-conversational-workbench.md`
· `docs/parallel-sessions-PLAN.md` · `docs/parallel-sessions-ROUND3.md` ·
`docs/nav-chrome-unification-LANE-M1.md` · `docs/charting-completion-LANE-G3.md` ·
`docs/pat-f3-flagship-analyst.md` · `docs/CARRY-FORWARD-anchor-and-4-lanes.md` ·
`docs/L2-body-migration-audit.md` · `docs/L2-status.md` · `docs/L3-chart-inventory.md` ·
`docs/L3-charting-STATUS.md` · `docs/patearn-AUTONOMOUS-COMPLETION.md` · `docs/provenance-coverage-NEXT-SESSION.md` ·
`docs/DOC_INDEX.md` (this file) · `research/cci/README.md` ·
`docs/CORRECTION-ARC-HANDOFF.md` · `docs/CORRECTION-KICKSTART-PROMPT.md` · `docs/KICKSTART-NEXT-SESSION.md` ·
`docs/KICKSTART-PATEARN-NEXT.md` · `docs/NEXT-SESSION-CARRYFORWARD.md` · `docs/POST-MERGE-DEPLOY-RUNBOOK.md` ·
`docs/chrome-consistency-sweep.md` · `docs/strategic-review-2026-07-07.md` ·
`docs/codex-review/00-CONTEXT-FOR-CODEX.md` · `docs/codex-review/FINDINGS-LEDGER.md` ·
`docs/codex-review/TRACK-C-RESULTS.md` · `docs/codex-review/TRACK-D-DATA-PLAN.md` · `docs/codex-review/CARRYFORWARD.md`

> **Lane-record rule (so this index stops chasing live lanes):** every `docs/lane-*.md`,
> `docs/L<N>-*.md` (e.g. `L2-status.md`, `L3-charting-STATUS.md`, `L4-status.md`),
> `docs/*-LANE-*.md`, `docs/parallel-sessions-*.md`, and `docs/CARRY-FORWARD-*.md` is
> **RUN-BOOK(active) by rule** — auto-generated by active lanes, load-bearing for collision
> avoidance, and **never archived while lanes run**. New ones are covered by this rule
> without re-listing; the explicit entries above are examples, not an exhaustive set.

**Bridge (`codex-bridge/*`):** the active two-agent collaboration channel — `README.md`,
`LOG.md`, and the `req-*` / `resp-*` / `PROPOSALS-*` artifacts. Process scaffolding;
keep while the bridge is in use (gitignore-able).

## E. REFERENCE — keep (23)

| Doc | Note |
|---|---|
| `docs/concall-intelligence-debate.md` | Adversarial debate / unique improvement record. |
| `docs/pat-question-catalog.md` | Master question catalog. |
| `docs/pat-seasonal-demo.md` | Pat seasonal ranking flow — live query→report demo (S127). |
| `docs/themes-perplexity-validation.md` | External validation prompt/workflow. |
| `docs/research-prompt-A-deep-settlement.md` | Active research prompt (no output artifact yet). |
| `docs/research-prompt-C-exit-lever.md` | Still-unbuilt research prompt. |
| `resources/patearn/SKILL.md` | patearn methodology. |
| `resources/patearn/patterns.md` | 14-pattern definitions. |
| `resources/patearn/failures.md` | Failure case studies. |
| `resources/patearn/exit-protocol.md` | Exit protocol. |
| `docs/AUDIT-2026-07-02-institutional-review.md` | Multi-agent platform audit; 117 AUD findings (permanent record). |
| `docs/bug-audit-2026-06.md` | 2026-06-30 full-codebase bug/improvement audit + verdicts. |
| `docs/DATA-POSTMORTEM-2026-07-05.md` | Data-estate deep-dive; live counts + integrity-failure findings. |
| `docs/DATASET-RESEARCH-BRIEF.md` | Living brief ranking/costing candidate datasets under PIT+cost gates. |
| `docs/QA-issue-register.md` | Round-1 in-browser QA sweep — graded findings record. |
| `docs/QA-round2-register.md` | Round-2 depth QA of the 6-beat pitch path — findings record. |
| `docs/institutional-panel-assessment.md` | Four-reviewer institutional adversarial assessment synthesis. |
| `docs/mvio-dataset-a.md` | Institutional proof-point: PIT insider/promoter/pledge event dataset. |
| `docs/predictive-attributes-findings.md` | Findings record: momentum is beta, not selection alpha. |
| `docs/validation-memo.md` | SR 11-7 model-validation memo (momentum lens + C/A/B layer). |
| `docs/prereg/union-prereg.md` | Pre-registered forward-test spec for the UNION signal (frozen rules + pass/fail, SHA-256 sealed); ledger 2026-07-16W. |
| `docs/prereg/union-ml-prereg.md` | Pre-registered walk-forward ML ranker over the union's qualifiers (train ≤2016, test 2017+, frozen models + pass bar, SHA-256 sealed BEFORE the run). |
| `docs/prereg/union-beta14-prereg.md` | Pre-registered SIBLING forward-test spec: union + per-name beta≤1.4 at selection (frozen rules + criteria + sibling adjudication, SHA-256 sealed); ledger 2026-07-16Y. |
| `docs/prereg/union-c40ra-prereg.md` | Pre-registered THIRD sibling: β14 + top-40 + RISKADJ-rank (frozen rules + criteria + 3-way family adjudication + multiplicity disclosure, SHA-256 sealed; family closed at three); ledger 2026-07-16AB. |
| `docs/prereg/union-ml2-prereg.md` | Pre-registered walk-forward ML ranker v2 over the ERA-FLOOR capped qualifiers (GBM primary per 16AA's declared succession; frozen 5-criterion bar incl. slip-2 stress; SHA-256 sealed BEFORE the run). |
| `docs/prereg/union-composite30-prereg.md` | Pre-registered FOURTH sibling: COMPOSITE-30, the Ramana-confirmed lead (family reopened by owner decision 2026-07-16; full self-contained spec + 4-way adjudication; SHA-256 sealed); ledger 2026-07-16AH. |
| `docs/prereg/union-k30-hold-prereg.md` | Pre-registered FIFTH sibling: K30-HOLD = COMPOSITE-30 with one lever change (hold a name while it stays in the top-60, 2× the 30 held), from the "improve the R logic" inquiry; +1.1pp net-of-gauntlet, DD unchanged, robustness-swept; SHA-256 sealed `e6994c19…`; ledger 2026-07-16BD. |
| `docs/prereg/union-a2-hold-prereg.md` | Pre-registered SIXTH sibling: A2-HOLD = the A2 composite (equal-weight top-40, lower drawdown) + the same 2×-holdings hold-band (top-80); +1.4pp net-of-gauntlet, DD −33% unchanged; SHA-256 sealed `17e0dd1a…`; ledger 2026-07-16BD. |
| `docs/prereg/union-k30-deephold-prereg.md` | Pre-registered SEVENTH sibling: K30-DEEP-HOLD = COMPOSITE-30 with TWO stacked levers — deeper-oversold turn (<20) from 16BE + the 2×-holdings hold-band (top-60) from 16BD; net 17.8→19.2% AND drawdown −38→−29% (best of all variants); SHA-256 sealed `b705f770…`; ledger 2026-07-16BF. Highest overfit risk of the siblings (two stacked in-sample levers) — disclosed. |
| `docs/prereg/union-ladder-validation-prereg.md` | Pre-registered VALIDATION protocol (NOT a strategy registration / not a 5th sibling): three frozen checks on the existing union ladder — C1 D139 paired-significance of the increments, C2 interim ≤2018-frozen / 2019-26-held OOS, C3 deflated forward-CAGR per CL-RES-07; SHA-256 sealed `37c28824…`; coordination session, 2026-07-16. |
| `docs/strategies/union-ladder.md` | LIVING compendium: every union-family configuration IN FULL (complete specs + all recorded numbers incl. stress ladders) — sealed, recorded, and walled members; Ramana's record-in-full directive (S173). |
| `docs/codex-review/rs-strategy-brief-2026-07-15.md` | The full-day RS-strategy brief sent to Codex for independent review (every config, number and bug); its verdict is ledger 2026-07-15R. |
| `docs/codex-review/UX-CODEX-INDEPENDENT.md` | Codex's independent UX/web-estate review findings. |
| `docs/codex-review/UX-DIALOGUE-R1-CODEX.md` | Codex round-1 UX dialogue verdicts. |
| `docs/codex-review/UX-DIALOGUE-R2-CODEX.md` | Codex round-2 UX final verification + drift check. |

## F. ARCHIVE? — candidates, **DEFERRED** (do NOT act while lanes are live) (5)

| Doc | Fold first? | When |
|---|---|---|
| `NEXT_SESSION_KICKSTART.md` (root) | No — old D33/session-16 kickstart, superseded by later state/logs. | Clean archive once tree is quiet. |
| `docs/research-prompt-B-cost-realism.md` | No — implemented (`research/explosive_moves/cost_realism.py` + ledger records it). | Clean archive once tree is quiet. |
| `docs/explosive-move-NEXT-SESSION.md` | **Yes** — fold named-flow A/B + future-frontier notes into PROJECT_STATE first. | After fold + quiet. |
| `docs/next-session-kickstart.md` | **Yes** — fold residual perf/concurrency notes into current UI docs first. | After fold + quiet. |
| `docs/PR-1-DESCRIPTION.md` | No — PR #1 already merged (`58e68fa`); body lives in git + PROJECT_STATE. | Clean archive once tree is quiet. |

When the lanes quiesce: regenerate this map, run the four-gate check (`AGENTS.md` #7),
fold durable content into `PROJECT_STATE.md`, then `git mv` into `docs/archive/`.

## Logic cleanse (parallel track — also DEFERRED)

These exist in the live tree (`git status` confirms) and are valid removal candidates,
but stay untouched until the four-gate check passes on a quiet tree:
`src/main.py.bak-stockchart`, `src/web/dashboard.py.bak-stockchart`,
`research/explosive_moves/out/~$RiskAdjMomentum_detailed_2019.xlsx` (Excel lock file).
The old "zero inbound imports → delete" heuristic is **retired** — many Hermes modules
run via `python -m` / timers with no Python importer. Use the four-gate check instead.

## Open reconciliation (Codex's catch)

`PROJECT_STATE.md` currently lags the live git history (many 2026-06-29 commits not yet
reflected). Do **not** treat PROJECT_STATE alone as proof a recent lane doc is "folded."
Reconcile PROJECT_STATE with the lanes once they settle, *then* archive.
