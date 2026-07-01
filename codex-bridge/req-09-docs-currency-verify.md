# Review brief 09 — verify the canonical docs are properly + consistently updated (live-tree snapshot)

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Date:** 2026-06-29 · **Output:** captured to `resp-09-docs-currency-verify.md`

Ramana asked: *"check if the documentation is properly updated, then send it for Codex 5.5
review."* Fresh currency pass on top of the already-PASSED `req-06` verify (`resp-06` confirmed
the core hardening + applied 2 fixes: CLAUDE.md timer reconciled + 5 new docs folded into
DOC_INDEX). This re-checks against the *current* live tree. The tree is **live** right now
(`PROJECT_STATE.md` last written 17:11; lane status docs through 16:59; `DOC_INDEX.md`
rewritten 15:23) — so **DEFER-ALL still holds and nothing has been edited/archived/deleted
for this request.** Your job: an adversarial, read-only currency + consistency check of the
canonical docs as they stand on disk *now*. Report only; change nothing.

## Read
1. `docs/DOC_INDEX.md` — the living map (note its self-healing "lane-record rule" in §D).
2. `AGENTS.md` — hardened twin (esp. concurrent-agents §, #6 hard-freeze, #7 four-gate).
3. `CLAUDE.md` — Claude twin (esp. guardrails 1–7).
4. `PROJECT_STATE.md` — running source of truth (large; skim Session log + decision log head).
5. `codex-bridge/resp-04-cleanse-dialogue.md` — your prior 53-doc classification + agreed wording.

## Verify each — PASS / FAIL / PARTIAL with a cited reason (file:line)

1. **DOC_INDEX completeness (disk-vs-index diff).** Compare `docs/*.md` on disk against the
   names referenced in `DOC_INDEX.md`. Are all docs either explicitly listed OR covered by the
   §D lane-record rule (`L<N>-*.md` / `*-LANE-*.md` / `lane-*` / `parallel-sessions-*` /
   `CARRY-FORWARD-*`)? Name any doc that is neither listed nor rule-covered.
2. **AGENTS.md #6 / #7 intact + faithful** to your `resp-04` wording (hard-freeze names
   dashboard.py/cockpit.py/main.py; four-gate has all 4 gates + "uncertain → KEEP").
3. **Twin consistency (the finding I want you to adjudicate).** `AGENTS.md` line ~3 says "both
   agents share one rule set." Timer-model wording now matches (`CLAUDE.md` #3 ≡ `AGENTS.md`
   #2 — confirm). **But `CLAUDE.md` does NOT carry the hard-freeze-of-3-entrypoints or the
   four-gate deletion check that `AGENTS.md` #6/#7 carry.** Is this a real divergence that
   should be reconciled (mirror the freeze/four-gate into `CLAUDE.md`, or have `CLAUDE.md`
   reference `AGENTS.md` #6/#7)? Or acceptable as-is? Give a recommendation.
4. **DEFER-ALL still honored.** From read-only state, is there any evidence a doc was
   archived / `git mv`'d / `git rm`'d / deleted? (Expected: none.)
5. **PROJECT_STATE currency.** `DOC_INDEX.md` §"Open reconciliation" claims PROJECT_STATE lags
   the live git history. Still true? Is deferring the fold (until lanes quiesce) the right call,
   or is anything durable at risk of being lost?
6. **Anything stale, contradictory, or missing** across the four canonical docs that a future
   session would be misled by.

## Output format (markdown)
```
## Verdict
<one line: are the canonical docs properly + consistently updated? safe?>

## Checks
| # | check | PASS/FAIL/PARTIAL | cited reason (file:line) |

## Issues to fix (if any)
<list, each: severity + exact file/line + the fix — but remember DEFER-ALL: recommend, don't expect edits now>

## Follow-ups
<twin reconciliation; PROJECT_STATE fold timing; anything else>
```
Cite files/lines. If you can't verify something read-only, say so rather than guessing.
