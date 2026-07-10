#!/usr/bin/env node
/*
 * state-doc-gate.cjs — PreToolUse[Bash|PowerShell] hook for the Hermes repo.
 *
 * Enforces the CLAUDE.md mandatory rule: a commit that changes src/ or scripts/
 * must update PROJECT_STATE.md in the SAME commit.
 *
 * Behavior:
 *   - Fires only on commands where `commit` is a git subcommand (git [opts] commit).
 *   - Checks `git diff --cached --name-only` (plus worktree-modified files when the
 *     command carries -a/--all) for src/|scripts/ paths without PROJECT_STATE.md.
 *   - Violation -> exit 2 (blocks the tool call; stderr is fed back to the model).
 *   - Escape hatch for deliberate exceptions: include "state:skip" in the command,
 *     or set HERMES_SKIP_STATE_GATE=1.
 *   - Fail-open on ANY internal error, non-git dirs, and repos without a
 *     PROJECT_STATE.md at their root. A broken gate must never block all commits.
 *
 * Compound commands: the hook runs BEFORE the Bash call, so `git add X && git commit`
 * would see a pre-add index. When the command carries a `git add`, its pathspecs are
 * expanded via `git ls-files -mod` and unioned into the staged set (add -A/. => all
 * modified+untracked+deleted), so single-line add+commit flows are gated correctly.
 *
 * Known accepted gaps (kept simple on purpose):
 *   - `git commit <pathspec>` commits are judged by the index, not the pathspec.
 *   - Commands run from a subdirectory report paths relative to it (repo-root flows are the norm).
 *   - A quoted literal like echo "git commit" can false-positive; state:skip covers it.
 */
'use strict';

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  let exitCode = 0;
  try {
    const inp = JSON.parse(raw || '{}');
    const cmd = String((inp.tool_input && inp.tool_input.command) || '');

    // `commit` must appear as the git subcommand: `git`, optional global opts
    // (-c k=v / -C path / --flag[=v]), then `commit`. `git log --grep commit`
    // does NOT match ("log" breaks the chain); `commit-tree` is excluded.
    const GIT_COMMIT = /\bgit\s+(?:-[cC]\s+\S+\s+|--\S+\s+)*commit(?![\w-])/;
    if (!GIT_COMMIT.test(cmd)) return finish(0);

    if (cmd.includes('state:skip') || process.env.HERMES_SKIP_STATE_GATE === '1') return finish(0);

    const cwd = (inp.cwd && String(inp.cwd)) || process.cwd();
    const { execSync } = require('child_process');
    const run = (c) =>
      execSync(c, { cwd, encoding: 'utf8', timeout: 8000, stdio: ['ignore', 'pipe', 'ignore'] });

    let root = '';
    try {
      root = run('git rev-parse --show-toplevel').trim();
    } catch (_) {
      return finish(0); // not a git dir — not our business
    }
    const fs = require('fs');
    const path = require('path');
    if (!fs.existsSync(path.join(root, 'PROJECT_STATE.md'))) return finish(0);

    let staged = run('git diff --cached --name-only').split(/\r?\n/).filter(Boolean);

    // `git commit -a` (any short-opt cluster containing `a`, or --all) also sweeps
    // modified tracked files that aren't staged yet.
    if (/(^|\s)--all\b/.test(cmd) || /(^|\s)-[A-Za-z]*a[A-Za-z]*\b/.test(cmd)) {
      staged = staged.concat(run('git diff --name-only').split(/\r?\n/).filter(Boolean));
    }

    // Compound `git add ... && git commit` in ONE call: the add hasn't run yet at hook
    // time, so expand the add's pathspecs (git itself resolves globs/dirs) and union them.
    const addMatch = /\bgit\s+add\b/.test(cmd) && cmd.match(/\bgit\s+add\s+([^&;|]*)/);
    if (addMatch) {
      const toks = addMatch[1]
        .split(/\s+/)
        .map((t) => t.replace(/^["']|["']$/g, ''))
        .filter((t) => t && !t.startsWith('-'));
      try {
        const spec = toks.length ? toks.join(' ') : '.';
        const expanded = run('git ls-files -m -o -d --exclude-standard -- ' + spec);
        staged = staged.concat(expanded.split(/\r?\n/).filter(Boolean));
      } catch (_) {
        /* unparseable pathspec -> fall back to index-only view (fail-open) */
      }
    }
    if (!staged.length) return finish(0);

    const needsState = staged.some((f) => /^(src|scripts)\//.test(f));
    const hasState = staged.some((f) => /^PROJECT_STATE\.md$/i.test(f));
    if (needsState && !hasState) {
      process.stderr.write(
        'state-doc-gate: this commit stages src/ or scripts/ changes without PROJECT_STATE.md. ' +
          'CLAUDE.md mandatory rule: update PROJECT_STATE.md (Decision log / Key file paths / ' +
          'open items / Session log) in the SAME commit, `git add PROJECT_STATE.md`, then retry. ' +
          'Deliberate exception: append "state:skip" to the commit command.\n'
      );
      exitCode = 2;
    }
  } catch (_) {
    exitCode = 0; // fail-open
  }
  finish(exitCode);

  function finish(code) {
    process.exit(code);
  }
});
