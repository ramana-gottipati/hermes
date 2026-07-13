# Patearn — next session kickstart (colour/UI + premium-visuals thread)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the colour / premium-visuals thread is folded into PROJECT_STATE. Registered in `docs/DOC_INDEX.md`.


**Mode: fully autonomous. Access: full folder + tools, already granted — do not ask for access
or per-step confirmation, and do not repeatedly re-request it.** Execute the agreed plan
end-to-end. Proceed freely on reversible in-repo work (new modules, tests, docs, local commits
on `main`). Only surface/confirm the genuinely irreversible or outward/costly: VPS deploy,
`git push`, paid API calls, or deleting/overwriting another session's uncommitted work. Keep the
hard guardrails (secrets never committed, cost discipline, cheap models in scheduled jobs,
additive/colour-only changes). This is a SHARED tree with parallel sessions — never clobber
another session's uncommitted files; stash/restore only your own.

> Product = **Patearn**. "Hermes" now refers ONLY to the Nous agent and legacy infra names
> (repo path `D:\Hermes`, `hermes-api`/`hermes-telegram` systemd units, ssh alias `hermes`).
> Never call the product Hermes.

You are on `main` (all work goes directly on `main`).

## 1. Boot
Read `PROJECT_STATE.md` fully — focus on Sessions 64–69 (colour Phases 2–4, reconcile+push,
deploy-parity audit) and Session 68 (premium-visuals program). `git log --oneline -25`. Confirm
`git branch --show-current` = `main`.

## 2. Re-baseline the shared state (do this FIRST — the tree moves under you)
- `git fetch origin` then `git rev-list --left-right --count origin/main...main`. If diverged,
  reconcile (merge `origin/main`; the only historically-conflicting file is `PROJECT_STATE.md`,
  ort usually auto-merges it). Only push work that's green and yours — don't push another
  session's incomplete commits.
- Gates: `python scripts/chrome_gate.py && python scripts/nav_integrity_gate.py && python scripts/color_gate.py`.
  **Nav gate was RED at last wrap on 2 orphans** — `/dash/credibility` and `/dash/momentum`.
  Verify whether still orphaned (concurrent sessions may have linked them). If red → item 4a.
- **Deploy-parity audit** (recurring, valuable): CR-normalized md5 of every `src/web/*.py`
  (`git show HEAD:<f>`) vs the VPS (`ssh hermes`, `/opt/hermes/src/web/`). Drift/missing =
  committed-but-undeployed parallel work; render-verify (200 + graceful + 0 `fill=/stroke="var("`
  leaks) before deploying colour-only (LF, py3.10, backup first, restart, health-check).

## 3. Verify-first rule
For every item below, confirm it's genuinely still open (grep code / hit route / check gate)
BEFORE working — prior kickstarts have propagated stale "open" markers for work that already
shipped in another session.

## 4. Genuinely-open threads (colour system itself is DONE — these are LOW–MEDIUM)
- **4a. Nav orphans.** `/dash/credibility` needs linking — Session 68's plan: embed its
  `card_html(sym, conn=…)` on the stock-dossier **CCI tab** + link from `/dash/concalls`.
  `/dash/momentum` is a parallel session's feature — touch only if yours. ⚠ nav files
  (`lens_registry.py`, dashboard nav) are HOT with concurrent edits — check `git status` /
  recent commits first.
- **4b. Premium-visuals program** (`docs/premium-visuals-brainstorm.md`, Ramana-endorsed):
  flagship **B** (rotation cycle-clock), **C** (promise-vs-delivery capture scatter). Flagship A
  (credibility fingerprint) is built + deployed; just needs the 4a embed.
- **4c. Colour Phase-3 categorical remainder** (low value): `_COMPARE_PALETTE` (`dashboard.py`),
  21-colour `_RRG_PALETTE`, scattered `.sc-*`/`kt-*`/`_fq/_qc` hexes → `--series-*`/`--cat-*`.
  Tokens already exist (`--series-1..8`, `--accent-orange`, `--chart-*`). Worth doing only as one
  coherent pass.

## 5. Guardrails
Colour/UI changes additive + colour-only (no behaviour change); no secrets; cheap models only in
any fan-out and **forbid git inside agents** (a fan-out once lost 8 files to `git stash`),
batches ≤8; VPS deploy = scp+restart (LF, backup first), never git-pull; update
`PROJECT_STATE.md` § Session log in the same commit as any shipped work.
