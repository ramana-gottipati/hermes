# Review brief 01 — documentation cleanse plan + workspace-sharing setup

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Date:** 2026-06-28

You are the independent reviewer in a two-agent system sharing the workspace
`D:\Hermes`. Review the material below. **Do not modify, move, or delete anything**
— output your review as text only (it will be captured to `resp-01-doc-cleanse-review.md`).

## Read these first, in order

1. `AGENTS.md` — your project orientation (twin of `CLAUDE.md`).
2. `CLAUDE.md` — the other agent's orientation + the binding rules.
3. `PROJECT_STATE.md` — the source of truth (state, decision log, session log, open items).
4. `docs/DOC_INDEX.md` — the documentation cleanse ledger you are reviewing (Phase 0 inventory).

Spot-check a sample of the docs DOC_INDEX classifies (especially the §D archive
candidates and anything marked "load-bearing") against what PROJECT_STATE.md and
the code actually say — don't take the classification on faith.

## What to assess and report

### 1. The workspace-sharing setup (`AGENTS.md`)
- Is it correct and complete for two agents safely sharing this tree?
- Does anything in it conflict with `CLAUDE.md` or `PROJECT_STATE.md`?
- Gaps that would let the two agents collide (the project's documented failure mode:
  parallel sessions clobbering shared files like `dashboard.py`/`cockpit.py`/`main.py`)?

### 2. The cleanse plan (`docs/DOC_INDEX.md`)
- Is the classification sound? Flag any **misclassification** in either direction:
  - a doc marked **ARCHIVE?/§D** that is actually still load-bearing or parallel-held, or
  - a doc marked **KEEP** that is actually dead/superseded.
- Are the §D "what to verify" notes the right checks? Anything missing?
- Is the fold-then-`git mv`-to-`docs/archive/` process genuinely non-destructive and reversible? Any step that could disrupt a live system, break inbound links, or lose unique content?

### 3. The logic cleanse (orphans/backups)
- Are the listed orphan/backup files (`*.bak-stockchart`, the `~$…xlsx` lock, zero-import `.py`) safe to remove by the stated method? Any you would NOT touch?

### 4. Problems & risks
- List concrete problems, each with severity (BLOCKER / SHOULD-FIX / NICE-TO-HAVE) and the file/line or doc it concerns.

### 5. Improvements
- Propose specific, actionable improvements to the setup or the process, prioritized. For each: the change, why it helps, and any risk.

## Output format (markdown)

```
## Verdict
<one paragraph: is the plan safe to proceed? overall quality?>

## §D row-by-row verdicts
<table: doc | KEEP / FOLD-THEN-ARCHIVE (items to fold) / ARCHIVE (already folded) | one-line citation>

## Problems
<list, each: [SEVERITY] problem — location — why it matters>

## Improvements
<prioritized list, each: change — rationale — risk>

## Anything the plan missed
<free text>
```

Be specific and cite files. If you can't verify a claim from the workspace, say so
rather than guessing.
