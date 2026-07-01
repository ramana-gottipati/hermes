## Verdict
Not safe to proceed as-is. The cleanse approach is directionally sound (`fold → git mv`, no deletes), but `docs/DOC_INDEX.md` is stale/incomplete and several §D archive candidates are still active, parallel-held, or have unmet retire conditions. The workspace-sharing rules in `AGENTS.md` are mostly correct, but should be strengthened with the newer freeze rule for `dashboard.py` / `cockpit.py` / `main.py`.

## §D Row-By-Row Verdicts

| doc | verdict | one-line citation |
|---|---|---|
| `docs/concall-intelligence-NEXT-SESSION.md` | KEEP | P8 is explicitly still data-gated: “P8 = gated…” at lines 137-139; next action is rerun gates/backtest at lines 100-106. |
| `docs/concall-intelligence-debate.md` | KEEP | Unique adversarial rationale and ranked fixes live here, especially lines 28-42; `PROJECT_STATE.md` still cites it as the flaw-catcher. |
| `docs/mep-NEXT-SESSION.md` | KEEP | Still has live open/parallel-held work: Pat routing and uncommitted/tangled bits at lines 48-51. |
| `docs/explosive-move-NEXT-SESSION.md` | FOLD-THEN-ARCHIVE | Backtest verdict is now largely recorded, but fold named-flow A/B + future qualitative frontier from lines 112-137 before archiving. |
| `docs/dashboard-deepen-NEXT-SESSION.md` | KEEP | It points to successor `docs/tags-and-index-NEXT-SESSION.md` at lines 97-99, but that file is absent in this snapshot. Do not archive until successor state is found/folded. |
| `docs/rrg-rotation-NEXT-SESSION.md` | KEEP | Remaining work is explicit at lines 92-98, and cockpit/dashboard contention is called out at line 101. |
| `docs/ui-perf-handoff.md` | KEEP | Step 5 remains backend-gated; lines 30 and 43 say not to ship/delete fallback until columns are live. |
| `docs/next-session-handoff.md` | KEEP | Tracker Steps 2-5 remain open at lines 27-49, with PROJECT_STATE reconciliation still pending at line 50. |
| `docs/next-session-kickstart.md` | FOLD-THEN-ARCHIVE | Old UI Phase 2/3 kickstart; fold any still-current concurrency/perf gate notes from lines 33-40 and 51-55 into current UI docs. |
| `NEXT_SESSION_KICKSTART.md` | ARCHIVE | Old root kickstart around D33/session-16 state; superseded by later PROJECT_STATE session logs and active NEXT docs. |
| `docs/themes-perplexity-validation.md` | KEEP | Still a reusable enrichment prompt; it documents 3,424 untagged companies at lines 7-15 and merge workflow at lines 128-132. |
| `docs/research-prompt-A-deep-settlement.md` | KEEP | Active CCI unblocker; explicitly says `concall_settle.py` is actively edited at lines 3-5 and defines unresolved success criteria at lines 37-47. |
| `docs/research-prompt-B-cost-realism.md` | ARCHIVE | Implemented: `research/explosive_moves/cost_realism.py` exists and `strategy-ledger.md` records results at lines 319-326. |
| `docs/research-prompt-C-exit-lever.md` | KEEP | No `exit_lever.py` found; prompt remains an unbuilt research task. |

## Problems

[BLOCKER] `DOC_INDEX.md` is not a complete inventory — `docs/DOC_INDEX.md:18` claims “one map of every Markdown doc,” but the snapshot contains unlisted docs including `docs/data-licensing-decision.md`, `docs/harmonic-pattern-design.md`, `docs/parallel-sessions-PLAN.md`, `docs/parallel-sessions-ROUND3.md`, `docs/ui-restore-and-migration-TRACKER.md`, `docs/lane-*.md`, and `docs/pat-f2-conversational-workbench.md`.

[BLOCKER] Several §D candidates are misclassified as archive candidates while still active — examples: `concall-intelligence-NEXT-SESSION.md:137-139`, `mep-NEXT-SESSION.md:48-51`, `rrg-rotation-NEXT-SESSION.md:92-101`, `ui-perf-handoff.md:30-43`.

[SHOULD-FIX] `AGENTS.md` lacks the newer hard freeze from `PROJECT_STATE.md`: freeze `dashboard.py` / `cockpit.py` / `main.py`; new work in modules + runtime wraps. `AGENTS.md:35-37` says “prefer isolate,” while `PROJECT_STATE.md` records it as binding after repeated collisions.

[SHOULD-FIX] Logic-cleanse file list is stale in this snapshot — `src/main.py.bak-stockchart`, `src/web/dashboard.py.bak-stockchart`, and `research/explosive_moves/out/~$RiskAdjMomentum_detailed_2019.xlsx` are not present, despite `DOC_INDEX.md:124-126`.

[SHOULD-FIX] “zero inbound imports” is unsafe as a deletion rule — many active CLI modules are invoked by `python -m`, timers, routers, scripts, or deployment hooks, not Python imports. The rule at `DOC_INDEX.md:127` needs entrypoint/timer/route/script checks.

[NICE-TO-HAVE] `AGENTS.md` conflicts slightly with `CLAUDE.md` on model/cost wording: `AGENTS.md:51-52` says “Haiku-or-nothing on timers,” while current `PROJECT_STATE.md` records Gemini Flash classifier use and cron-based CCI extraction. Rephrase as “approved cheap model paths only.”

## Improvements

1. Update `DOC_INDEX.md` from a fresh Markdown inventory before Phase 2 — prevents archiving against an incomplete map. Risk: small bookkeeping cost.

2. Add a “hard-held files” rule to `AGENTS.md`: `dashboard.py`, `cockpit.py`, and `main.py` are frozen unless explicitly coordinated; use new modules, routers, and runtime wiring. This matches `PROJECT_STATE.md` and directly addresses the known collision mode. Risk: slightly more indirection.

3. Add a pre-archive checklist per file: successor doc exists, retire condition fired, PROJECT_STATE folded, no active self-prompt/open items, no “parallel-held/dirty/uncommitted” warnings. Risk: none beyond slower cleanse.

4. For logic cleanse, require four checks before `git rm`: path exists, no references by `rg`, not named in PROJECT_STATE/docs/scripts/systemd, and not an entrypoint (`python -m`, FastAPI router, script, timer). Risk: avoids removing apparently orphaned but operational files.

5. Treat research prompts as `REFERENCE/RUN-BOOK` until output artifact exists and ledger records the verdict. This cleanly separates B, which is done, from A/C, which are still active.

## Anything The Plan Missed

The plan missed the newer parallel-sessions documentation and current lane docs entirely, which are highly load-bearing for collision avoidance. It also missed that the listed backup/lock files are absent in this review snapshot, so that logic-cleanse section should be regenerated before anyone acts on it.