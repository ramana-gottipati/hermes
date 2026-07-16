# Hermes — CLAUDE.md (session orientation)

## ⚠️ READ THIS FIRST — and the MANDATORY UPDATE RULE

The running source of truth for this project is **`D:\Hermes\PROJECT_STATE.md`**.

### Boot procedure (every session, no exceptions)

0. **Follow `docs/SESSION-PROTOCOL.md`** — the binding start/end checklist — and start work from **`docs/NEXT-SESSION-CARRYFORWARD.md`** (the current queue + takeover prompt). Sessions run **autonomously** (Guardrail #0); get guidance from the agents, not per-step confirmation. **Boot the `docs/FABLE-PROTOCOL.md` §0 stance first (Guardrail #10) — binding for whatever model tier is running this session.**
1. Read the **top Session-log entry** of `PROJECT_STATE.md` (+ grep sections as needed). **Do NOT read the whole file** — protect the context window; lazy-load.
2. Skim recent commits: `git log --oneline -20`; `git fetch` + verify the tip; **kickstart-pick-verify** before redoing any "open" item.
3. Only then start making changes.

Don't re-derive the architecture from scratch. The decisions in `PROJECT_STATE.md` § "Decision log" are deliberate. Surface conflicts before overwriting them.

### 🔴 MANDATORY: Update PROJECT_STATE.md as you work

**Binding rule:** every decision, structure change, open-item change, and session's shipped work
updates its `PROJECT_STATE.md` section **in the SAME commit** as the code. Machine-enforced for
commits touching `src/`/`scripts/` by the PreToolUse gate `scripts/state-doc-gate.cjs` (D97;
deliberate exception = append `state:skip` to the commit command). Route by this table:

| If you do this in a session... | Update this section of PROJECT_STATE.md... |
|---|---|
| Add a new Telegram command | § "Telegram bot commands" table |
| Add or change a DB table / column | § "Database schema" |
| Add a new file in `src/` or `scripts/` | § "Key file paths" |
| Make an architectural choice (model selection, schedule change, etc.) | § "Decision log" (numbered entry with WHY) |
| Build something that was open / discover something broken | § "What's NOT yet built" (remove / add) |
| End the session with any shipped work | New § "Session log" entry at top, with commit hashes |

Goal: a future session gets the complete current picture from `PROJECT_STATE.md` without grepping
the codebase.

---

## What Hermes is (one paragraph)

Personal AI agent for Ramana (a financial analyst in Vizag, India). Runs 24/7 on a Hostinger KVM4 VPS in Mumbai. Three workloads: conversational Telegram assistant, Indian-market news intelligence with patearn-style screening, and rule-based equity scoring backed by NSE bhav copy + Screener.in fundamentals. Deep stock analysis (Phase 4 qualitative) happens in claude.ai under Ramana's $20/mo subscription, NOT via the API — this is a deliberate cost-control choice.

---

## Quick stack reference

- **Host:** Ubuntu 22.04 LTS, Hostinger VPS @ `187.127.173.149`
- **Process manager:** systemd (NOT Docker)
- **Language:** Python 3.11+ in a venv at `/opt/hermes/.venv/`
- **API framework:** FastAPI + uvicorn (port 8000)
- **Bot library:** python-telegram-bot 21.7
- **LLM:** Anthropic Claude (Haiku 4.5 default; Sonnet on user-initiated /analyze only)
- **Datastore:** SQLite at `/opt/hermes/data/hermes.db` (single-file portability)
- **Config:** `.env` + `pydantic-settings` (`src/core/settings.py`)

---

## Most-needed commands at a glance

| Goal | Command |
|---|---|
| SSH to VPS | `ssh root@187.127.173.149` |
| Update VPS from latest GitHub | 🔴 **Deploy = scp + writer-safe restart** (`vps-deploy-reality` memory / PROJECT_STATE recipe). Do NOT use `setup-news.sh` to update a live box — it is a FRESH-BOOTSTRAP script only (pip-install + unit-overwrite). Its AUD-28 hazards (stale heredocs that REVERTED live units + a mid-day `systemctl start`) were **FIXED S123** — it now delegates unit install to `scripts/install-systemd.sh` (canonical captured units) and never enables/starts. **Never `systemctl start` a hermes timer mid-day** (AUD-95: `Requires=` fires the job). |
| Run 5y bhav copy backfill (background) | `nohup bash /opt/hermes/scripts/full-backfill.sh > /var/log/hermes-backfill.log 2>&1 &` |
| Pull all VPS data to laptop | Double-click `D:\Hermes\scripts\download-from-vps.bat` |
| Bot status | `systemctl status hermes-telegram` |
| Bot live logs | `journalctl -u hermes-telegram -f` |

---

## Guardrails for any Claude Code session in this repo

**0. STANDING AUTHORIZATION — full-folder access + autonomy (Ramana, permanent, do not re-ask).** Assume full read/write access to the **entire `D:\Hermes` tree** in every session — **never request folder-by-folder or per-directory permission** for anything inside the repo, and never treat a subfolder you created as needing fresh access. Execute agreed/converged plans autonomously: new modules, tests, docs, `PROJECT_STATE.md` updates, local commits to `main` (topic branch only when isolation is genuinely needed), running local/VPS scripts, spawning agents, and **VPS deploy of verified, gate-passing, additive changes** (recipe: `PROJECT_STATE.md`/VPS-deploy notes). Report outcomes after acting, not permission requests before. **Surface first ONLY** for genuinely costly/destructive/external actions: **paid API spend** (Gemini/GLM/vendor data), **deleting or overwriting work you did not create**, **DB-destructive ops**, or **publishing beyond the VPS site**. (Twin: `AGENTS.md` Guardrail #0.)

**0-bis. PERMISSION IS MACHINE-ENFORCED — NEVER ASK FOR ACCESS (Ramana, 2026-07-02, non-negotiable).** The committed `.claude/settings.json` (loads in every session AND every git worktree) sets `permissions.defaultMode: "bypassPermissions"` plus a full tool/path allowlist and `additionalDirectories` for `~/.claude` and the Temp scratchpad tree. That file IS the standing authorization above, made permanent at the harness level. Binding on every session and subagent: (a) **never** ask the user for folder/file/tool access — not via AskUserQuestion, not as a "shall I proceed?" message; (b) **never weaken that file** — do not switch it to a stricter mode, add `ask:` rules, or remove allow entries (only Ramana edits it); (c) if a permission prompt still fires anyway, treat it as a **bug to report at session wrap** (note which tool/path prompted), never as a cue to ask for more access; (d) the surface-first list in #0 (paid spend / deleting others' work / DB-destructive / publishing) remains the ONLY reason to pause — decided in conversation, never via access prompts.

1. **Secrets** — never commit `.env`. Anthropic key, Telegram bot token, Telegram allowed user IDs live there only.
2. **Cost discipline** — operating Hermes (per month) should be ≤ ₹300 API spend. THIS chat session is more expensive than Hermes itself. Bundle changes. Avoid long iterative tinkering. For text/prompt tweaks, suggest SSH-edit on VPS.
3. **Cheap models only in scheduled jobs.** Anything that runs on a timer uses approved cheap-model paths only — Haiku or Gemini Flash Lite; never Sonnet/Opus. (Twin of `AGENTS.md` Guardrail #2.)
4. **Rule-based > LLM for screening.** The Stage 1 screen is pure Python over Screener data. Don't reintroduce LLM-driven screening.
5. **Value > quantity.** All cross-time-period stock metrics use rupees, not share count. Eliminates corporate-action adjustment bugs.
6. **Pre-compute over recompute.** Anything stored can be re-derived from raw data; don't normalise away the bhav copy archive.
7. **At session wrap, append to `PROJECT_STATE.md` § Session log** with what shipped + commit hashes. The doc is the running source of truth — keep it current.
8. **Data sourcing — PRIMARY SOURCES ONLY (copyright).** Any NEW data feed must come from an authentic/primary source — **NSE, BSE, SEBI, XBRL filings, or genuine official open data.** **Never add a vendor or Screener.in dependency** (Ramana 2026-07-02: copyright risk; he may enable vendors later, not now). Current known exception being remediated: `screener.py`→`fundamentals`/`fundamentals_history` (powers C capital-allocation + patearn scoring) — migrate to BSE/NSE XBRL; do not extend it, and disclose it where shown. Prefer the BSE-announcements pattern (`concall_bse.py`) for anything new.
9. **New user-facing surfaces follow `docs/SURFACE-PLAYBOOK.md` (BINDING, 2026-07-13).** Before adding ANY page/board/tab/embed: run its sister-data check (extend, don't duplicate), register in `lens_registry.py` or as a declared child (never an orphan URL), and land the full checklist (education scaffold + glossary + fence + Pat registration + server CSV + `sym` links + home-exposure decision) in the SAME session. Nav labels: plain English first, no internal jargon (session/decision IDs, "Ramana") in rendered HTML.

10. **Model-parity protocol — `docs/FABLE-PROTOCOL.md` (BINDING, 2026-07-16).** Every session, regardless of the model running it (Fable/Opus/Sonnet/Haiku/Codex/any future model), boots that file's §0 stance and runs its session loop, falsification battery, closed decision tables, and STOP-CONDITION escalations. Capability lives in the scaffolding, not only the model: a lower-tier model follows the protocol mechanically and **escalates at the §4 stop conditions instead of improvising** (bank triggers under `## ⛔ ESCALATE` in the carryforward for a STRONG-tier session to drain). Tier routing + hybrid patterns = FABLE-PROTOCOL §5; timers stay on cheap models per Guardrail #3 — the protocol governs sessions, not scheduled jobs. (Twin: `AGENTS.md` Guardrail #8.)

---

## Useful built-in Claude Code skills

- `plan` — before any non-trivial change
- `claude-api` — when wiring up Anthropic SDK (caching, models, tool use)
- `code-review` — local PR review before pushing
- `engineering:debug` — diagnosing runtime issues on VPS

---

## Where to find detail

| Topic | File |
|---|---|
| Current state, decisions, open items, session log | **`PROJECT_STATE.md`** |
| **Model-parity operating doctrine (any model tier behaves like Fable)** | **`docs/FABLE-PROTOCOL.md`** — boot stance §0 + session loop + falsification battery + stop conditions + tier routing; twin of Guardrail #10 |
| **Adding ANY new screen/page/tab (binding playbook)** | **`docs/SURFACE-PLAYBOOK.md`** — decision tree + landing checklist; twin of Guardrail #9 |
| UX / user-journey audit + remediation session plan | `docs/ux-journey-audit-2026-07-13.md` (joint Claude+Codex, S-A…S-H program) |
| **Strategy definitions, status & terminology (canonical)** | **`docs/strategies/`** (start at `docs/strategies/README.md`) — **continuously maintained**: every new/changed strategy updates its page in the SAME commit (served at `/dash/strategy-ref`); machine backstop = `tests/test_strategy_docs_coverage.py` |
| Bhav copy + DVPT signals architecture (Word) | `docs/hermes-bhavcopy-architecture.docx` |
| patearn methodology (source skill) | `resources/patearn/SKILL.md` + sibling files |
| Telegram bot implementation | `src/assistant/telegram_bot.py` |
| Database schema | `src/core/db.py` (search for `SCHEMA_BASE`) |
| Rule-based scoring | `src/automation/scoring.py` |
| Bhav copy ingestion | `src/automation/bhavcopy.py` |
| Signal computation | `src/automation/signals.py` |
| Deploy / install scripts | `scripts/setup-news.sh`, `scripts/full-backfill.sh` |
