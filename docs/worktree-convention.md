# Worktree convention — one worktree per lane (working-tree isolation)

> **Lifecycle: STANDING.** The working-tree isolation rule for concurrent lanes. Update in place; do not retire. Registered in `docs/DOC_INDEX.md`. Twin: `docs/SESSION-PROTOCOL.md` (§ HOW THE SESSION RUNS).

## The failure this prevents

Multiple sessions pointed at the **one** `D:/Hermes` checkout share **one working tree and one index**. That sharing — not pushing to `main` — is the root cause of the acute multi-session failures:

- **Cross-absorption** — a sibling session's `git add -A && commit` sweeps *your* staged files into *its* commit. Your work lands under the wrong hash (or is lost if the sibling then resets).
- **Index / working-tree reset** — a sibling's `git reset --hard` or `git checkout -- .` wipes *your* uncommitted edits.

Both pass every test and are caught only by luck. They recurred repeatedly in one 2026-07-16 session (a staged §7-ratification fold was absorbed into a parallel lane's commit; the index was reset mid-commit).

**A worktree gives each lane its own working tree + index.** A sibling's `git add`/`reset`/`checkout` physically cannot touch another worktree's files or index. Lanes still all push to `origin/main` and rebase on conflict — that part was always fine and stays.

## The rule

- **Every concurrent autonomous lane/session works in its own worktree.** The shared `D:/Hermes` checkout is a **coordination anchor** — use it to `git fetch`/read state, not for a second lane's edits + commits.
- One human, one interactive session, nothing else running → the main checkout is fine. The rule binds the moment a *second* actor might touch the tree.

## The flow

```sh
# from the main checkout:
scripts/new-lane.sh <lane-slug>          # e.g. s7-guards  → D:/Hermes.worktrees/s7-guards on branch lane/s7-guards, off origin/main
cd ../Hermes.worktrees/<lane-slug>
# ...edit, commit (the doc gates run here too)...
git fetch && git rebase origin/main && git push origin HEAD:main
cd -                                      # back to the main checkout
scripts/retire-lane.sh <lane-slug>       # remove the worktree; delete the branch iff merged
```

- **Location:** worktrees live in the sibling dir `Hermes.worktrees/<lane>` (outside the repo tree, so they can never be tracked/committed into it). `lane/<slug>` is the branch.
- `new-lane.sh` branches fresh off `origin/main` (fetches first) and sets `core.hooksPath` idempotently.
- `retire-lane.sh` removes the worktree and deletes the branch **only if merged** (unmerged branches are kept, never lost) — this is what stops the orphan-worktree husks the MAINT-WTAUDIT keeps flagging.

## Gotchas (consolidated — these bit real sessions)

- **`core.hooksPath` is inherited.** It lives in the shared `.git/config`, so worktrees pick up `scripts/hooks` (the pre-commit doc gate fires). `new-lane.sh` still sets it idempotently — if it were ever unset, commits would silently skip the gate.
- **The FABLE kernel does NOT travel to a worktree.** A worktree has no CLAUDE.md context loaded for you. Boot it there too: quote the "🧠 THINK LIKE FABLE" header + its 4 phases (ORIENT · HYPOTHESIZE-THEN-ATTACK · TRACK YOUR OWN EPISTEMICS · ADVERSARIAL CLOSE) and state your §5 tier before picking work (SESSION-PROTOCOL step 1). Same rule already binds spawned workers (FABLE-PROTOCOL §5).
- **Rebase state is NOT at `.git/rebase-merge` in a worktree** — `.git` is a *file* there. Use `git rev-parse --git-path rebase-merge`. A stale rebase dir silently blocks every later rebase; clear only your OWN worktree's.
- **The state-doc gate still applies.** Staging `src/`/`scripts/` requires staging `PROJECT_STATE.md` in the same commit (or `HERMES_SKIP_STATE_GATE=1` for a deliberate exception). The gate runs in the worktree because `core.hooksPath` is inherited.
- **Numbering collisions are orthogonal.** Worktree isolation does not pick your session number for you — still check `git show origin/main:PROJECT_STATE.md` for the next free S-/D-number (the S162 lesson), because a parallel lane may have taken it.

## Why not just "never run two sessions at once"

Parallel lanes are the project's throughput model (Guardrail #0 autonomy; the union/D142/UI lanes run concurrently by design). The answer is isolation, not serialization.
