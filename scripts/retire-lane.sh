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

# Remove the worktree; on failure report the ACTUAL reason (not a guess), and
# distinguish "already gone" (stale registration → prune + still clean the branch)
# from a genuinely dirty/locked worktree (needs your attention).
if ! rm_err="$(git -C "$ROOT" worktree remove "$DEST" 2>&1)"; then
  if [ ! -d "$DEST" ]; then
    echo "worktree dir already gone at $DEST (removed out-of-band) — pruning stale registration." >&2
    git -C "$ROOT" worktree prune
    # fall through to branch cleanup below
  else
    echo "could not remove worktree at $DEST — git said:" >&2
    printf '  %s\n' "$rm_err" >&2
    echo "  If it holds only uncommitted/untracked work you don't need, force it:" >&2
    echo "    git -C \"$ROOT\" worktree remove --force \"$DEST\"" >&2
    exit 1
  fi
fi

git -C "$ROOT" fetch --quiet origin
if git -C "$ROOT" branch --merged origin/main --format='%(refname:short)' | grep -qx "$BRANCH"; then
  git -C "$ROOT" branch -d "$BRANCH" && echo "✓ removed worktree + deleted merged branch $BRANCH"
else
  echo "✓ removed worktree; kept branch $BRANCH (NOT merged into origin/main — push it or delete by hand)"
fi
git -C "$ROOT" worktree prune
