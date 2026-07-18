# REWIRE AFTER RENAME — D:\Hermes → D:\patearn (execute in the FIRST session opened in D:\patearn)

> **Lifecycle: TRANSIENT** — retire when: every checklist item below is verified green and the
> outcome is recorded in PROJECT_STATE §Session log; then `git rm` this file. Fold into:
> `PROJECT_STATE.md` §Session log.

**Context.** On 2026-07-18 Ramana renamed the repo folder from `D:\Hermes` to `D:\patearn`
(plan §Q-3, naming law §Q). Everything below was PRE-STAGED before the rename by the planning
session: the full plan + all work is pushed to origin (`acd42c2`), the memory directory is
pre-copied to the new project slug, and the Oct-3 union forward-test task's prompt already
points at the new path with a fallback. This checklist finishes the rewiring. **The VPS,
GitHub remote, deploy recipes, and all gates are unaffected by design — do not touch them.**

## The checklist (in order, verify each)

1. **Git sanity in the renamed main repo:**
   `git -C D:/patearn status && git -C D:/patearn log --oneline -3` — must show the tree with
   its pre-rename state (any sibling lane's uncommitted files — e.g. `dashboard.py`,
   `adjust.py`, `corp_actions.py` — are EXPECTED to still be there, untouched; do not clean).
2. **Repair the worktrees** (their `.git` files still point at `D:/Hermes/.git/...`):
   `git -C D:/patearn worktree repair D:/Hermes.worktrees/v3-preview` — repeat for every path
   in `git -C D:/patearn worktree list` that lives under `D:/Hermes.worktrees/`. Then verify:
   `git -C D:/Hermes.worktrees/v3-preview status` works and shows a clean tree.
   (The worktrees FOLDER keeps its old name for now — renaming it is optional; if renamed to
   `D:/patearn.worktrees`, run `git worktree repair <each-new-path>` again and update
   `scripts/new-lane.sh`'s `WT_HOME` line in the same commit.)
3. **Memory:** confirm this session's memory directory is
   `C:\Users\gotti\.claude\projects\D--patearn\memory` and that MEMORY.md loaded (82 files were
   pre-copied, byte-verified). If the harness derived a DIFFERENT slug (check the memory path in
   the system prompt), copy `C:\Users\gotti\.claude\projects\D--Hermes\memory\.` into the actual
   new slug's `memory\` directory. **Do NOT delete the old `D--Hermes` copy for at least a week.**
4. **Scheduled tasks:** `union-forward-test-q3-2026` prompt already updated (new path + fallback
   — verify by reading its SKILL.md); `banknifty-post-earnings-rerun` (fires 2026-07-21) and
   `claude-til-daily` carry no repo paths — confirm both still listed and enabled.
5. **Tool re-trust:** Gemini CLI trusts folders by path — next Gemini run from `D:/patearn`
   needs `GEMINI_CLI_TRUST_WORKSPACE=true` (non-interactive) as before; Codex runs by cwd, no
   action. `.claude/settings.json` + `launch.json` were audited: zero absolute paths — no edits.
6. **Verification battery (all must pass before declaring done):**
   a. `python -m pytest tests/ -q` from `D:/patearn` — expect the pre-rename green suite.
   b. `python scripts/nav_integrity_gate.py` — green.
   c. A no-op docs commit + push from a worktree → `git diff --quiet HEAD origin/main` verifies
      by CONTENT (the recorded rule).
   d. `ssh root@187.127.173.149 systemctl is-active hermes-api` — active (proves ops path
      untouched; the service keeps its infra codename per naming law §Q).
7. **Record:** PROJECT_STATE §Session log entry (under the Patearn name, per the naming law) +
   retire this file (fold-then-delete, same commit).

## What was deliberately NOT changed
- systemd `hermes-*` units, `/opt/hermes`, `hermes.db`, `HERMES_*` env — frozen infra codenames
  (§Q-4 deferral). — The GitHub repo name — optional later step; redirects preserved if done.
- History: past session logs, sealed docs, the ledger — records stay records.
