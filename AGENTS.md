# Hermes — AGENTS.md (Codex orientation)

> This is the Codex-facing twin of `CLAUDE.md`. Both agents share one rule set so
> they never fight each other in this tree. If this file and `CLAUDE.md` ever
> disagree, `CLAUDE.md` + `PROJECT_STATE.md` win — fix this file to match.

## ⚠️ READ THIS FIRST

The running source of truth for this project is **`D:\Hermes\PROJECT_STATE.md`**.

**Boot procedure (every session, no exceptions):**
1. Read `PROJECT_STATE.md` fully — current state, decisions, session log, open items.
2. Skim recent history: `git log --oneline -20`.
3. Only then make changes. Do not re-derive the architecture; the decisions in
   `PROJECT_STATE.md` § "Decision log" are deliberate. Surface conflicts before
   overwriting them.

## 🔴 MANDATORY: keep PROJECT_STATE.md current (binding, not optional)

A commit that changes code without updating `PROJECT_STATE.md` is **incomplete**.

- New decision (architecture / defaults / policy) → append to § "Decision log" **in the same commit**.
- Structure change (new file / table / command / service) → update the matching section **in the same commit**.
- Open item closed or discovered → update § "What's NOT yet built / open items" **in the same commit**.
- End of any session that shipped → new entry at the TOP of § "Session log" with date, what shipped, commit hash(es).

## 🟡 This repo has MULTIPLE concurrent agents in the same tree

Claude Code and Codex (and sometimes parallel sessions of each) operate on
`D:\Hermes` at the same time. Therefore:

1. **Build additive — never replace.** Add features and new modules; never remove
   or reroute existing pages/logic. Sacred surfaces: `/dash/ratio`, `/dash/rrg`,
   `/dash/compare`, and any page already in the dashboard nav.
2. **Isolate new work in new modules** (e.g. a new `src/web/<thing>_view.py`) with
   a thin wrapper into the existing surface, rather than editing large shared files
   another session may be holding.
3. **Never blind-delete.** Files like `*.bak-*`, orphaned `*.py`, and superseded
   docs may belong to in-flight work. Inventory + classify + get sign-off first;
   then remove via `git rm` / `git mv` so it's reversible. Never `rm -rf`. Apply
   the four-gate check (#7) before any removal.
4. **Check before you stage.** Run `git status --short <path>` before `git add`;
   stage only the specific files you changed, never `git add -A`, so you don't
   absorb another session's mid-flight work.
5. **CRLF discipline.** This is a Windows tree deployed to Linux. Keep line endings
   consistent; diff-check before any VPS deploy.
6. **Hard-freeze the shared web entrypoints.** `src/web/dashboard.py`,
   `src/web/cockpit.py`, and `src/main.py` are collision hotspots and are FROZEN
   for ordinary feature work. Don't edit their bodies, reroute existing pages, or
   move navigation into them unless Ramana explicitly authorizes that exact change
   and the tree is quiet. New work goes in new modules/routers (e.g.
   `src/web/<feature>_view.py`), attached via the existing registry / runtime-wrap
   pattern. If a tiny mount is unavoidable, keep it mechanical, cite the owning
   module, run `regression_sweep.sh`, and stage only that explicit path.
7. **Four-gate deletion/archive check.** No file is deleted, `git rm`'d, or
   `git mv`'d to archive just because it looks unused or has zero inbound Python
   imports. All four gates must pass and be recorded first:
   1. **Exists in the live tree** — verify with `git status --short <path>` /
      `Test-Path`; don't infer from a lean snapshot.
   2. **No references** — `rg` the exact filename, module name, route, command,
      table, and any URL/path aliases.
   3. **Not named by operations/state** — check `PROJECT_STATE.md`, `CLAUDE.md`,
      `AGENTS.md`, `docs/`, `scripts/`, systemd units, deploy scripts, timers, and
      bridge run-books.
   4. **Not an entrypoint** — not invoked by `python -m`, FastAPI router inclusion,
      CLI/script usage, cron/systemd, import side effects, runtime registry, or
      VPS-only wiring.
   If any gate is uncertain → KEEP, not ARCHIVE. Archive a doc only after its
   durable content is folded into `PROJECT_STATE.md`, and always via `git mv`.

## Guardrails

0. **STANDING AUTHORIZATION — full-folder access + autonomy (Ramana, permanent,
   do not re-ask).** Assume full read/write access to the **entire `D:\Hermes`
   tree** every session — **never request folder-by-folder / per-directory
   permission** for anything in the repo, and never treat a subfolder you created
   as needing fresh access. Execute agreed plans autonomously (new modules, tests,
   docs, PROJECT_STATE updates, commits to `main`, running scripts, spawning
   agents, and **VPS deploy of verified gate-passing additive changes**); report
   after, don't ask before. **Surface first ONLY** for genuinely costly/
   destructive/external actions: paid API spend, deleting/overwriting work you did
   not create, DB-destructive ops, or publishing beyond the VPS site. (Twin:
   `CLAUDE.md` Guardrail #0.)
1. **Secrets** — never commit `.env`. Anthropic key, Telegram token, allowed user
   IDs, and the paid Gemini key live there only.
2. **Cost discipline** — Hermes runtime budget is ≤ ₹300/mo API. On timers use
   **approved cheap-model paths only — Haiku or Gemini Flash Lite; never
   Sonnet/Opus in a scheduled job.** Keep the Stage-1 screen rule-based (no LLM).
3. **Value > quantity** — cross-time-period stock metrics use rupees, not share
   count. No static rupee thresholds — use %, percent-rank, or velocity.
4. **Pre-compute over recompute** — anything stored is re-derivable from raw data;
   don't normalise away the bhav-copy archive.
5. **Nothing discarded** — record every research result as a benchmark, even
   failures (`docs/strategy-ledger.md`).
6. **Data sourcing — PRIMARY SOURCES ONLY (copyright).** Any NEW data feed must
   come from an authentic/primary source — **NSE, BSE, SEBI, XBRL filings, or
   genuine official open data.** **Never add a vendor or Screener.in dependency**
   (Ramana 2026-07-02: copyright risk; vendors may be enabled later, not now).
   Known exception being remediated: `screener.py` fundamentals (C capital-alloc +
   patearn) → migrate to BSE/NSE XBRL; don't extend it. Prefer the BSE-announcements
   pattern (`concall_bse.py`) for anything new. (Twin: `CLAUDE.md` Guardrail #8.)
7. **New user-facing surfaces follow `docs/SURFACE-PLAYBOOK.md` (BINDING).** Sister-data
   check first (extend, don't duplicate); register in `lens_registry.py` or as a declared
   child — never an orphan URL; land the education/fence/Pat/CSV checklist in the same
   session. **Pat registration is machine-enforced (`tests/test_pat_coverage.py`) per the
   binding `docs/pat-knowledge-contract.md`** — every routed lens declares Pat coverage
   (DATA/EXPLAIN/NAV) and every metric has a glossary entry, or the build fails. (Twin:
   `CLAUDE.md` Guardrail #9.)

## Where to find detail

| Topic | File |
|---|---|
| Current state, decisions, open items, session log | **`PROJECT_STATE.md`** |
| **Adding ANY new screen/page/tab (binding playbook)** | **`docs/SURFACE-PLAYBOOK.md`** |
| Claude Code's twin of this file | `CLAUDE.md` |
| Map of every doc (classified, living) | `docs/DOC_INDEX.md` |
| Codex ⇄ Claude collaboration channel | `codex-bridge/README.md` |
| Database schema | `src/core/db.py` (search `SCHEMA_BASE`) |
| Rule-based scoring | `src/automation/scoring.py` |
| Bhav-copy ingestion | `src/automation/bhavcopy.py` |
| Signal computation | `src/automation/signals.py` |
| patearn methodology | `resources/patearn/SKILL.md` |
| Deploy / install scripts | `scripts/setup-news.sh`, `scripts/full-backfill.sh` |

## Stack (quick reference)

Ubuntu 22.04 VPS @ `187.127.173.149` · systemd (not Docker) · Python 3.11 venv at
`/opt/hermes/.venv/` · FastAPI + uvicorn :8000 · python-telegram-bot 21.7 ·
SQLite at `/opt/hermes/data/hermes.db` · config via `.env` + pydantic-settings.
