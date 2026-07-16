#!/usr/bin/env bash
# scripts/new-lane.sh — create an ISOLATED worktree for one autonomous lane/session.
#
# WHY THIS EXISTS (the failure it prevents):
#   Multiple sessions sharing the ONE D:/Hermes checkout share ONE working tree and
#   ONE index. A sibling session's `git add -A` then sweeps YOUR staged files into
#   its commit (cross-absorption), and its `git reset --hard` wipes YOUR uncommitted
#   edits. Both passed every test and were caught only by luck. A worktree gives each
#   lane its OWN working tree + index; a sibling's git ops can never touch yours.
#   All lanes still push to origin/main (rebase-on-conflict is normal + safe) — the
#   isolation is at the working-tree/index level, which is the actual root cause.
#
# Usage:   scripts/new-lane.sh <lane-slug>
# Example: scripts/new-lane.sh s7-guards
#
# Full convention + gotchas: docs/worktree-convention.md
set -eu

LANE="${1:?usage: scripts/new-lane.sh <lane-slug>   (e.g. s7-guards)}"
case "$LANE" in *[!a-z0-9-]*) echo "lane-slug must be [a-z0-9-] only" >&2; exit 2;; esac

ROOT="$(git rev-parse --show-toplevel)"
WT_HOME="$(dirname "$ROOT")/Hermes.worktrees"   # sibling of the repo, OUTSIDE the tree
DEST="$WT_HOME/$LANE"
BRANCH="lane/$LANE"

if [ -e "$DEST" ]; then echo "already exists: $DEST (retire it first: scripts/retire-lane.sh $LANE)" >&2; exit 1; fi

git -C "$ROOT" fetch --quiet origin
mkdir -p "$WT_HOME"
git -C "$ROOT" worktree add -b "$BRANCH" "$DEST" origin/main

# core.hooksPath lives in the SHARED config → inherited by worktrees, but set it
# idempotently so the pre-commit doc gates (scripts/hooks/pre-commit) fire regardless.
git -C "$DEST" config core.hooksPath scripts/hooks

cat <<BANNER

✓ Lane worktree ready:
    $DEST   (branch $BRANCH, freshly off origin/main)

  cd "$DEST"
  # ...edit, then commit here — the doc gates run in this worktree too...
  git fetch && git rebase origin/main && git push origin HEAD:main   # land on main
  cd "$ROOT" && scripts/retire-lane.sh $LANE                         # clean up (no orphan husk)

REMEMBER (a worktree does NOT inherit CLAUDE.md context):
  • Boot the FABLE kernel here too — quote the "THINK LIKE FABLE" header + its 4 phases
    (ORIENT / HYPOTHESIZE-THEN-ATTACK / TRACK YOUR OWN EPISTEMICS / ADVERSARIAL CLOSE)
    and state your §5 tier before picking work (SESSION-PROTOCOL step 1).
  • Rebase state lives at \`git rev-parse --git-path rebase-merge\`, NOT .git/rebase-merge
    (a stale one silently blocks every later rebase; clear only your OWN worktree's).
BANNER
