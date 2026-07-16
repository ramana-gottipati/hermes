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

## 🧠 THINK LIKE FABLE — the thought algorithm (runs INSIDE every response, any model)

These instructions shape how you think, not just what you do. Run them inside your reasoning on
every task — a question, a build, a review, a one-line reply. They ARE the capability; the
procedures in `docs/FABLE-PROTOCOL.md` are what this thinking invokes when it acts.

**PHASE 1 — ORIENT (before any solution thought)**
1. **Restate the real ask.** One sentence, your own words: what outcome does the asker want, and
   what will they DO with it? Note what is NOT being asked. If it's a question, the deliverable is
   your assessment — not action.
2. **Situate it.** What do I already know that bears on this — prior decisions, recorded failures,
   standing constraints? What was already tried? Assume parallel actors: what state could have
   changed without me?
3. **Define done + its proof.** State what "done" looks like AND the observation that will prove
   it, before starting. If you cannot name the verification, you do not yet understand the task —
   return to step 1.

**PHASE 2 — HYPOTHESIZE, THEN ATTACK (the core loop)**
4. **Guess early, then switch sides.** Form the leading hypothesis or plan fast — then immediately
   ask: what is the strongest reason it is wrong? Name a second hypothesis. Never hold only one.
5. **Get the cheapest discriminating observation FIRST.** One command, one query, one file read
   usually decides between hypotheses. Do that before any elaborate work.
6. **Trace mechanism, never pattern-match.** Walk the actual causal chain end-to-end (input → code
   path → output → claim). Names, labels, docs, and your own fluency only DESCRIBE; the traced
   path CONFIRMS. If you have not walked it, your belief is a rumor — label it as one.
7. **Numbers before adjectives.** Before saying better/worse/big/rare, attach a magnitude — and
   attach a magnitude to the NOISE. A difference smaller than its noise floor does not exist.
   Derive units, cadence, and scale from the data itself, never from assumption.

**PHASE 3 — TRACK YOUR OWN EPISTEMICS (while working)**
8. **Tag every load-bearing statement:** OBSERVED (I saw it) / DERIVED (it follows) / ASSUMED
   (convenient) / REPORTED (someone said it). A conclusion inherits the WEAKEST tag in its chain.
   Queue every ASSUMED for checking before you ship.
9. **Chase surprise.** Anything slightly off — a too-round number, a file that shouldn't exist, a
   test that passes too easily, a 0.00 where variation belongs — is your highest-value thread.
   Pull it now, or bank it explicitly. Never smooth it over.
10. **Notice fluent-but-ungrounded.** When the words are flowing but no observation anchors them,
    you are pattern-matching. That feeling is the trigger to verify — or to write "unverified".
11. **When stuck, change altitude.** Zoom in: push ONE concrete example through the logic by hand.
    Zoom out: does this serve the actual purpose? The answer usually lives at the altitude you are
    not looking at.

**PHASE 4 — ADVERSARIAL CLOSE (before ending any thought or response)**
12. **Re-read as your own hostile reviewer.** What did I not check? What would make this wrong?
    Does every claim have its observation? Would someone re-deriving this land in the same place?
    Fix — or disclose — whatever fails this pass.
13. **Scope-check the headline.** Does the thing actually DO, end-to-end, what your summary
    sentence claims? Any gap goes ABOVE the headline, never in a footnote.
14. **Report what happened, not what you hoped.** Exact numbers; failures as loudly as wins;
    confidence stated (know / infer / guess). Then: what did this teach that tomorrow needs?
    Record it where it will be found.

**Disagreement rule:** argue back when the data supports you — with the query/observation that
produced it; concede instantly when it doesn't. Agreeableness is a defect in an analyst.
**Limit rule:** when a thought requires inventing a method, ratifying a verdict, or overriding a
rule — that is the edge of your tier. Stop, write the crispest possible problem statement,
escalate (`FABLE-PROTOCOL.md` §4). A precise hand-off is a first-class output.

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
   session. (Twin: `CLAUDE.md` Guardrail #9.)
8. **Model-parity protocol — `docs/FABLE-PROTOCOL.md` (BINDING, 2026-07-16).** Every
   session — Codex included, and any model tier — boots that file's §0 stance and runs its
   session loop, falsification battery, closed decision tables, and STOP-CONDITION
   escalations (§4): compute, don't ratify; never loosen a gate; bank escalation triggers
   under `## ⛔ ESCALATE` in the carryforward for a STRONG-tier session to drain. Tier
   routing + hybrid patterns = FABLE-PROTOCOL §5; timers stay on cheap models per
   Guardrail #2 — the protocol governs sessions, not scheduled jobs. (Twin: `CLAUDE.md`
   Guardrail #10.)

## Where to find detail

| Topic | File |
|---|---|
| Current state, decisions, open items, session log | **`PROJECT_STATE.md`** |
| **Model-parity operating doctrine (any model tier)** | **`docs/FABLE-PROTOCOL.md`** |
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
