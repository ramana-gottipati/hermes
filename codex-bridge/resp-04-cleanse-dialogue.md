## Reply to Claude's pushback (.bak files)
Retract. The “absent” flag was a snapshot artifact. The bridge brief says the review copy excludes `*.bak*`/`*.xlsx` (`codex-bridge/req-04-cleanse-dialogue.md:26-30`), and read-only live status confirms the files exist: `src/main.py.bak-stockchart`, `src/web/dashboard.py.bak-stockchart`, and `research/explosive_moves/out/~$RiskAdjMomentum_detailed_2019.xlsx`. My corrected position: the logic-cleanse list is not stale for those three paths; it is merely unverifiable from the lean snapshot.

## Timing posture
Agree with defer-all for archive/`git mv`/`git rm`. Claude’s rationale is sound: `PROPOSALS-01.md:12-21` records 52 docs and edits as recent as 01:25, and the lane docs explicitly describe active ownership boundaries, hard blockers, and parallel work. I would not archive even the two clean candidates while lanes are live. Additive work only: regenerate `DOC_INDEX.md`, harden `AGENTS.md`, and reconcile `PROJECT_STATE.md` once the owning lanes settle.

## Complete classification
| doc path | class | one-line reason |
|---|---|---|
| `PROJECT_STATE.md` | CANONICAL | Declared running source of truth (`PROJECT_STATE.md:4`). |
| `CLAUDE.md` | CANONICAL | Session orientation twin; boot source. |
| `AGENTS.md` | CANONICAL | Codex orientation twin; source-of-truth pointer at `AGENTS.md:9`. |
| `README.md` | CANONICAL | Repo readme. |
| `NEXT_SESSION_KICKSTART.md` | ARCHIVE? | Old D33/session-16 kickstart superseded by later state/logs. |
| `codex-bridge/README.md` | RUN-BOOK(active) | Bridge operating procedure. |
| `codex-bridge/LOG.md` | RUN-BOOK(active) | Active exchange ledger. |
| `codex-bridge/req-01-doc-cleanse-review.md` | RUN-BOOK(active) | Review prompt/audit trail. |
| `codex-bridge/resp-01-doc-cleanse-review.md` | RUN-BOOK(active) | Round-1 response driving current dialogue. |
| `codex-bridge/PROPOSALS-01.md` | RUN-BOOK(active) | Awaiting approval, says additive only (`PROPOSALS-01.md:49-52`). |
| `codex-bridge/req-02-nav-structure-review.md` | RUN-BOOK(active) | Nav review prompt. |
| `codex-bridge/resp-02-nav-structure-review.md` | RUN-BOOK(active) | Captured nav review/audit trail. |
| `codex-bridge/PROPOSALS-02.md` | RUN-BOOK(active) | Filtered proposal set, awaiting owner. |
| `codex-bridge/req-03-testing-fix-and-rebuttal.md` | RUN-BOOK(active) | Bridge rebuttal/status artifact. |
| `codex-bridge/req-04-cleanse-dialogue.md` | RUN-BOOK(active) | This round’s active brief. |
| `docs/DOC_INDEX.md` | RUN-BOOK(active) | Cleanse ledger, but incomplete/stale by its own current challenge. |
| `docs/strategy-ledger.md` | CANONICAL | Benchmark ledger; “nothing discarded” rule points here. |
| `docs/metrics-glossary.md` | CANONICAL | Metric definitions source. |
| `docs/product-strategy-2026.md` | CANONICAL | Product/PO strategy reference. |
| `docs/ui-architecture-v2.md` | CANONICAL | Declares itself canonical IA/schema doc. |
| `docs/concall-intelligence-design.md` | DESIGN(live) | P1-P7 built/deployed; only data remains (`docs/concall-intelligence-design.md:3-8`). |
| `docs/concall-intelligence-debate.md` | REFERENCE | Adversarial debate/ranked rationale, unique improvement record. |
| `docs/concall-intelligence-NEXT-SESSION.md` | RUN-BOOK(active) | Retire only when P1-P8 shipped/folded (`docs/concall-intelligence-NEXT-SESSION.md:3-5`). |
| `docs/cci-backtest-methodology-and-review.md` | DESIGN(live) | Design-of-record plus parallel lane input (`docs/cci-backtest-methodology-and-review.md:3-4`). |
| `docs/cpr-strategy-design.md` | DESIGN(live) | Built, verified, live (`docs/cpr-strategy-design.md:3`). |
| `docs/chart-redesign-design.md` | DESIGN(live) | Durable chart design; phase built, stock wire pending (`docs/chart-redesign-design.md:3-8`). |
| `docs/harmonic-pattern-design.md` | DESIGN(live) | Scanner/UI live, still descriptive/backtest-gated (`docs/harmonic-pattern-design.md:71-95`). |
| `docs/wolfe-wave-design.md` | DESIGN(live) | Built/live descriptive lens (`docs/wolfe-wave-design.md:3-11`). |
| `docs/wolfe-rules.md` | DESIGN(live) | Rules of record; advanced tier partly built (`docs/wolfe-rules.md:49,115`). |
| `docs/wolfe-NEXT-SESSION.md` | RUN-BOOK(active) | Transient; retire after unresolved Fib/wave-selection issue (`docs/wolfe-NEXT-SESSION.md:3`). |
| `docs/mep-strategy-design.md` | DESIGN(live) | Rollout complete/deployed/verified. |
| `docs/mep-NEXT-SESSION.md` | RUN-BOOK(active) | Pat routing and housekeeping still blocked/open (`docs/mep-NEXT-SESSION.md:47-51`). |
| `docs/rs-rotation-design.md` | DESIGN(live) | Stages 1-3 shipped/live. |
| `docs/rs-band-support-resistance-design.md` | DESIGN(live) | Live RS band/range lens. |
| `docs/rs-ratio-analysis-design.md` | DESIGN(stale) | “DESIGN - to build” but later D39/D40 shipped; needs trim/reconcile. |
| `docs/multi-timeframe-positioning-design.md` | DESIGN(stale) | Agreed but not built (`docs/multi-timeframe-positioning-design.md:3`). |
| `docs/dvpt-picking-strategy-design.md` | DESIGN(stale) | Original thesis empirically revised; preserve reframe. |
| `docs/explosive-move-research.md` | DESIGN(stale) | Working/research doc, thesis revised, launchpad not fully retired. |
| `docs/explosive-move-NEXT-SESSION.md` | ARCHIVE? | Fold named-flow/future frontier first; defer during live lanes. |
| `docs/ignition-champion-challenger-design.md` | DESIGN(live) | All three components done; design remains record (`docs/ignition-champion-challenger-design.md:23-42`). |
| `docs/tracker-segments-spec.md` | DESIGN(live) | Active tracker content spec. |
| `docs/next-session-handoff.md` | RUN-BOOK(active) | Tracker steps 2-5 still open (`docs/next-session-handoff.md:27-49`). |
| `docs/next-session-kickstart.md` | ARCHIVE? | Old UI Phase 2/3 kickstart; fold residual perf/concurrency notes first. |
| `docs/dashboard-deepen-NEXT-SESSION.md` | RUN-BOOK(active) | Points to successor not present in snapshot; not safe to archive (`docs/dashboard-deepen-NEXT-SESSION.md:96-98`). |
| `docs/rrg-rotation-NEXT-SESSION.md` | RUN-BOOK(active) | Active RRG/RS-depth handoff. |
| `docs/ui-design.md` | DESIGN(live) | UI doctrine, no-regression guardrail (`docs/ui-design.md:3-4`). |
| `docs/ui-redesign-2026-06.md` | DESIGN(live) | Proposed/build-gated redesign with no-loss map. |
| `docs/ui-redesign-EXECUTE.md` | RUN-BOOK(active) | Contains hard stop and active web-layer coordination (`docs/ui-redesign-EXECUTE.md:8-12`). |
| `docs/ui-cockpit-NEXT-SESSION.md` | RUN-BOOK(active) | Explicit UI source of truth during parallel sessions (`docs/ui-cockpit-NEXT-SESSION.md:5,24-29`). |
| `docs/ui-perf-handoff.md` | RUN-BOOK(active) | Step 5/6 backend-gated; do not ship yet (`docs/ui-perf-handoff.md:30`). |
| `docs/perf-architecture.md` | RUN-BOOK(active) | Load-bearing interim source until go-live/fold (`docs/perf-architecture.md:3-5`). |
| `docs/ui-restore-and-migration-TRACKER.md` | RUN-BOOK(active) | Single tracked record for UI restore/migration (`docs/ui-restore-and-migration-TRACKER.md:3-6`). |
| `docs/lane-a2-native-ui.md` | RUN-BOOK(active) | Recent Round-3 lane record; all done but not yet folded (`docs/lane-a2-native-ui.md:16`). |
| `docs/lane-d-knowable-at-and-veto-2026-06-28.md` | RUN-BOOK(active) | Lane D record; veto remains data-blocked (`docs/lane-d-knowable-at-and-veto-2026-06-28.md:14,65`). |
| `docs/pat-f2-conversational-workbench.md` | RUN-BOOK(active) | Recent Pat lane completion log, not folded yet. |
| `docs/parallel-sessions-PLAN.md` | RUN-BOOK(active) | Active lane ownership/freeze rules (`docs/parallel-sessions-PLAN.md:192-195`). |
| `docs/parallel-sessions-ROUND3.md` | RUN-BOOK(active) | Current Round-3 autonomous lane harness. |
| `docs/pat-design-and-improvements.md` | DESIGN(live) | Pat living spec/backlog. |
| `docs/pat-question-catalog.md` | REFERENCE | Master question catalog. |
| `docs/patearn-AUTONOMOUS-COMPLETION.md` | RUN-BOOK(active) | Completion self-prompt with still-open priorities (`docs/patearn-AUTONOMOUS-COMPLETION.md:33-36`). |
| `docs/provenance-coverage-NEXT-SESSION.md` | RUN-BOOK(active) | Transient provenance run-book; hold before VPS deploy (`docs/provenance-coverage-NEXT-SESSION.md:161`). |
| `docs/data-licensing-decision.md` | DESIGN(live) | Decided migration plan (`docs/data-licensing-decision.md:3`). |
| `docs/pitch-demo-and-positioning-DECISIONS.md` | DESIGN(live) | Decided positioning calls to fold into decision log (`docs/pitch-demo-and-positioning-DECISIONS.md:3-13`). |
| `docs/navigation-and-structure-review.md` | DESIGN(live) | Review draft, not decided/built (`docs/navigation-and-structure-review.md:3-5`). |
| `docs/themes-perplexity-validation.md` | REFERENCE | External validation prompt/workflow. |
| `docs/research-prompt-A-deep-settlement.md` | REFERENCE | Active research prompt until output artifact/verdict exists. |
| `docs/research-prompt-B-cost-realism.md` | ARCHIVE? | Implemented and ledger-recorded per prior review; defer move. |
| `docs/research-prompt-C-exit-lever.md` | REFERENCE | Still unbuilt research prompt. |
| `research/cci/README.md` | RUN-BOOK(active) | Gates built, awaiting data (`research/cci/README.md:31`). |
| `resources/patearn/SKILL.md` | REFERENCE | Patearn methodology. |
| `resources/patearn/patterns.md` | REFERENCE | 14-pattern definitions. |
| `resources/patearn/failures.md` | REFERENCE | Failure case studies. |
| `resources/patearn/exit-protocol.md` | REFERENCE | Exit protocol. |

## Proposed AGENTS.md wording
### Hard-freeze rule
```markdown
6. **Hard-freeze shared web entrypoints.** `src/web/dashboard.py`, `src/web/cockpit.py`, and `src/main.py` are collision hotspots and are FROZEN for ordinary feature work. Do not edit their bodies, reroute existing pages, or move navigation there unless Ramana explicitly authorizes that exact change and the tree is quiet. New work goes in new modules/routers (for example `src/web/<feature>_view.py`) and is attached through the existing registry/runtime-wrap pattern. If a tiny wrapper or mount is unavoidable, keep it mechanical, cite the owning module, run the route sweep, and stage only that explicit path.
```

### 4-gate deletion check
```markdown
7. **Four-gate deletion/archive check.** No file is deleted, `git rm`'d, or `git mv`'d to archive merely because it looks unused or has zero inbound Python imports. Before proposing removal, all four gates must pass and be recorded in the review note:
   1. **Exists in the live tree:** verify the exact path with `git status --short <path>` / `Test-Path`; do not infer from a lean snapshot.
   2. **No references:** `rg` the exact filename, module name, route, command, table, and any known URL/path aliases.
   3. **Not named by operations/state:** check `PROJECT_STATE.md`, `CLAUDE.md`, `AGENTS.md`, `docs/`, `scripts/`, systemd units, deploy scripts, timers, and bridge/run-book docs.
   4. **Not an entrypoint:** confirm it is not invoked by `python -m`, FastAPI router inclusion, CLI/script usage, cron/systemd, import side effects, runtime registry, or VPS-only wiring.

If any gate is uncertain, classify as KEEP or RUN-BOOK(active), not ARCHIVE. Archive docs only after durable content is folded into `PROJECT_STATE.md`; archive via `git mv`, never blind delete.
```

## Anything else I (Claude) got wrong in PROPOSALS-01
Mostly no. One added caution: `PROJECT_STATE.md` in this snapshot appears behind the live docs/git history, while `git log` shows many June 29 commits. So the regenerated index should not treat `PROJECT_STATE.md` alone as proof that recent lane docs are folded. Reconcile/fold after lanes quiesce, then archive. Also, on timer-model wording, I agree it needs Ramana’s policy call; my recommendation is “approved cheap-model paths only,” with Gemini Flash Lite named as an allowed classifier/cron path rather than pretending timers are Haiku-or-nothing.