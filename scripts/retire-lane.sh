#!/usr/bin/env bash
# scripts/retire-lane.sh — remove a lane worktree cleanly, no orphan husk left behind.
#
# The MAINT-WTAUDIT flags orphaned worktrees precisely because lanes forget to remove
# them. Run this at lane wrap; it removes the worktree and deletes the branch ONLY if
# it is already merged into origin/main (an unmerged branch is kept, never lost).
#
# Usage: scripts/retire-lane.sh <lane-slug>
set -eu

LANE="${1:?usage: scripts/retire-lane.sh <lane-slug>}"
ROOT="$(git rev-parse --show-toplevel)"
DEST="$(dirname "$ROOT")/Hermes.worktrees/$LANE"
BRANCH="lane/$LANE"

if ! git -C "$ROOT" worktree list --porcelain | grep -qF "$DEST"; then
  echo "no worktree at $DEST — nothing to retire (run 'git worktree list')" >&2
  git -C "$ROOT" worktree prune; exit 0
fi

if ! git -C "$ROOT" worktree remove "$DEST" 2>/dev/null; then
  echo "worktree not clean (uncommitted/untracked changes present at $DEST)." >&2
  echo "  Inspect it, then either commit/push or force-remove:" >&2
  echo "    git -C \"$ROOT\" worktree remove --force \"$DEST\"" >&2
  exit 1
fi

git -C "$ROOT" fetch --quiet origin
if git -C "$ROOT" branch --merged origin/main --format='%(refname:short)' | grep -qx "$BRANCH"; then
  git -C "$ROOT" branch -d "$BRANCH" && echo "✓ removed worktree + deleted merged branch $BRANCH"
else
  echo "✓ removed worktree; kept branch $BRANCH (NOT merged into origin/main — push it or delete by hand)"
fi
git -C "$ROOT" worktree prune
