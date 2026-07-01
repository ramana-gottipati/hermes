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

## Classes
`CANONICAL` keep indefinitely · `DESIGN(live)` design-of-record for shipped/in-build
feature · `DESIGN(stale)` design not built / partly superseded (keep, trim later) ·
`RUN-BOOK(active)` transient but retire-condition NOT yet fired · `REFERENCE`
methodology / external / catalog · `ARCHIVE?` candidate, **deferred** (verify + fold +
`git mv` only when the tree is quiet; never delete).

---

## A. CANONICAL (8)

| Doc | Why |
|---|---|
| `PROJECT_STATE.md` | Running source of truth. |
| `CLAUDE.md` | Claude orientation twin. |
| `AGENTS.md` | Codex orientation twin. |
| `README.md` | Repo readme. |
| `docs/strategy-ledger.md` | Benchmark ledger ("nothing discarded"). |
| `docs/metrics-glossary.md` | Metric definitions source. |
| `docs/product-strategy-2026.md` | Product / PO strategy reference. |
| `docs/ui-architecture-v2.md` | Canonical IA / schema doc. |

## B. DESIGN(live) — design-of-record, keep (18)

| Doc | Note |
|---|---|
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

## C. DESIGN(stale) — keep, trim superseded sections later (4)

| Doc | Note |
|---|---|
| `docs/rs-ratio-analysis-design.md` | "to build" but D39/D40 shipped; reconcile. |
| `docs/multi-timeframe-positioning-design.md` | Agreed but not built. |
| `docs/dvpt-picking-strategy-design.md` | Thesis empirically revised; preserve reframe. |
| `docs/explosive-move-research.md` | Working doc; thesis revised, launchpad not fully retired. |

## D. RUN-BOOK(active) — transient, retire-condition NOT fired, KEEP

**Docs (28):** `docs/concall-intelligence-NEXT-SESSION.md` · `docs/wolfe-NEXT-SESSION.md`
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
`docs/DOC_INDEX.md` (this file) · `research/cci/README.md`

> **Lane-record rule (so this index stops chasing live lanes):** every `docs/lane-*.md`,
> `docs/L<N>-*.md` (e.g. `L2-status.md`, `L3-charting-STATUS.md`, `L4-status.md`),
> `docs/*-LANE-*.md`, `docs/parallel-sessions-*.md`, and `docs/CARRY-FORWARD-*.md` is
> **RUN-BOOK(active) by rule** — auto-generated by active lanes, load-bearing for collision
> avoidance, and **never archived while lanes run**. New ones are covered by this rule
> without re-listing; the explicit entries above are examples, not an exhaustive set.

**Bridge (`codex-bridge/*`):** the active two-agent collaboration channel — `README.md`,
`LOG.md`, and the `req-*` / `resp-*` / `PROPOSALS-*` artifacts. Process scaffolding;
keep while the bridge is in use (gitignore-able).

## E. REFERENCE — keep (9)

| Doc | Note |
|---|---|
| `docs/concall-intelligence-debate.md` | Adversarial debate / unique improvement record. |
| `docs/pat-question-catalog.md` | Master question catalog. |
| `docs/themes-perplexity-validation.md` | External validation prompt/workflow. |
| `docs/research-prompt-A-deep-settlement.md` | Active research prompt (no output artifact yet). |
| `docs/research-prompt-C-exit-lever.md` | Still-unbuilt research prompt. |
| `resources/patearn/SKILL.md` | patearn methodology. |
| `resources/patearn/patterns.md` | 14-pattern definitions. |
| `resources/patearn/failures.md` | Failure case studies. |
| `resources/patearn/exit-protocol.md` | Exit protocol. |

## F. ARCHIVE? — candidates, **DEFERRED** (do NOT act while lanes are live) (4)

| Doc | Fold first? | When |
|---|---|---|
| `NEXT_SESSION_KICKSTART.md` (root) | No — old D33/session-16 kickstart, superseded by later state/logs. | Clean archive once tree is quiet. |
| `docs/research-prompt-B-cost-realism.md` | No — implemented (`research/explosive_moves/cost_realism.py` + ledger records it). | Clean archive once tree is quiet. |
| `docs/explosive-move-NEXT-SESSION.md` | **Yes** — fold named-flow A/B + future-frontier notes into PROJECT_STATE first. | After fold + quiet. |
| `docs/next-session-kickstart.md` | **Yes** — fold residual perf/concurrency notes into current UI docs first. | After fold + quiet. |

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
