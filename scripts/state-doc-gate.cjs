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
 * Pathspec commits (v1.2): `git commit --only <paths>` / `git commit [--] <paths>` commit THOSE
 * paths regardless of what else sits in the shared index — judged on the pathspec expansion, so a
 * sibling session's staged src/ file can no longer false-block a state-doc-only commit (the exact
 * flow the safe-git-add-new skill mandates in a contested index). Quoted strings (commit messages)
 * are stripped before token-parsing so message words never read as paths.
 *
 * Known accepted gaps (kept simple on purpose):
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

    // v1.2 — explicit pathspecs after `commit` define the commit's content; judge them directly.
    const seg = cmd.match(/\bgit\s+(?:-[cC]\s+\S+\s+|--\S+\s+)*commit(?![\w-])([^&;|]*)/);
    if (seg && seg[1]) {
      const rest = seg[1]
        .replace(/"(?:[^"\\]|\\.)*"/g, ' ')
        .replace(/'(?:[^'\\]|\\.)*'/g, ' ');
      const toks = rest.split(/\s+/).filter(Boolean);
      const paths = [];
      for (let i = 0; i < toks.length; i++) {
        const t = toks[i];
        if (t === '--') continue;
        if (/^-(m|F|c|C|t)$/.test(t) || /^--(message|file|template|fixup|squash|reuse-message|reedit-message|author|date)(=.*)?$/.test(t)) {
          if (!t.includes('=')) i++; // skip the option's argument (quoted ones are already stripped)
          continue;
        }
        if (t.startsWith('-')) continue;
        paths.push(t.replace(/^["']|["']$/g, ''));
      }
      if (paths.length) {
        let judged = null;
        try {
          judged = run('git diff HEAD --name-only -- ' + paths.join(' '))
            .split(/\r?\n/)
            .concat(run('git ls-files -o --exclude-standard -- ' + paths.join(' ')).split(/\r?\n/))
            .filter(Boolean);
        } catch (_) {
          judged = null; // unparseable pathspec -> fall through to index judgment
        }
        if (judged) {
          const needsP = judged.some((f) => /^(src|scripts)\//.test(f));
          const hasP =
            judged.some((f) => /^PROJECT_STATE\.md$/i.test(f)) ||
            paths.some((p) => /(^|\/)PROJECT_STATE\.md$/i.test(p));
          if (needsP && !hasP) {
            process.stderr.write(
              'state-doc-gate: this pathspec commit touches src/ or scripts/ without PROJECT_STATE.md. ' +
                'Include PROJECT_STATE.md in the same commit, or append "state:skip" for a deliberate exception.\n'
            );
            return finish(2);
          }
          return finish(0);
        }
      }
    }

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
      // v1.3 (S95 wrap-report fix): PROJECT_STATE.md named as an add token counts as intent
      // to carry it — an UNMODIFIED state doc expands to nothing via ls-files -m -o -d and
      // v1.1/v1.2 false-blocked exactly that flow. Mirrors the pathspec branch's token check.
      if (toks.some((p) => /(^|\/)PROJECT_STATE\.md$/i.test(p))) return finish(0);
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
