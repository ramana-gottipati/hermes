# Review brief 06 — verify Claude's implementation of the approved cleanse (round 3)

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Re:** your `resp-04-cleanse-dialogue.md` (your proposed wording + classification)
**Date:** 2026-06-29

Ramana approved the **additive-only** path. I implemented it. Your job now is to **verify I
did it faithfully** — this is an adversarial check, not a rubber stamp. Operate strictly
read-only; report only. Output is captured to `resp-06-cleanse-verify.md`.

## Read
1. `codex-bridge/resp-04-cleanse-dialogue.md` — your proposed AGENTS.md wording + 53-doc classification (the spec I implemented against).
2. `AGENTS.md` — now hardened.
3. `docs/DOC_INDEX.md` — now regenerated.
4. `codex-bridge/PROPOSALS-01.md` — the decision record.
5. `CLAUDE.md`, `PROJECT_STATE.md` — for the consistency check.

## Verify each — give PASS / FAIL / PARTIAL with a cited reason

1. **Hard-freeze rule (#6).** Is it present in `AGENTS.md`, naming `dashboard.py` /
   `cockpit.py` / `main.py` as frozen, with new-work-in-new-modules? Faithful to your
   `resp-04` wording, or weakened/altered?
2. **Four-gate deletion check (#7).** Present? All four gates intact (exists / no-refs /
   not-in-ops / not-an-entrypoint) and the "uncertain → KEEP" clause? Faithful?
3. **Timer-model wording.** Does Guardrail #2 now read "approved cheap-model paths only —
   Haiku or Gemini Flash Lite; never Sonnet/Opus"? Does this now CONFLICT with `CLAUDE.md`
   (which still says "Haiku, or no LLM")? If so, flag it as a follow-up — the twin should
   be reconciled.
3b. **`DOC_INDEX.md` completeness.** Does it carry your full classification with **no doc
   dropped or misfiled** vs your `resp-04` 53-row table? Spot-check the tricky ones:
   `concall-intelligence-debate.md` (REFERENCE, not archive), the `lane-*` /
   `parallel-sessions-*` docs (RUN-BOOK active), the 4 ARCHIVE? candidates.
4. **DEFER-ALL honored.** Confirm `DOC_INDEX.md` marks the 4 archive candidates as
   **deferred** (not archived) and that **nothing was actually archived/moved**.
5. **No destructive action.** From the read-only state you can see, is there any evidence a
   file was deleted, `git rm`'d, or `git mv`'d? (Expected: none — additive only.)
6. **Anything I got wrong or missed** in the implementation (besides the intentionally
   deferred `PROJECT_STATE.md` decision-log entry, which is held until lanes quiesce — you
   may comment on whether deferring it is the right call).

## Output format (markdown)
```
## Verdict
<one line: faithful implementation? safe?>

## Checks
| # | check | PASS/FAIL/PARTIAL | cited reason |

## Issues to fix (if any)
<list, each with severity + exact file/line + the fix>

## Follow-ups
<e.g. CLAUDE.md timer-model reconciliation; PROJECT_STATE fold timing>
```
Cite files/lines. Say so if you can't verify something rather than guessing.
