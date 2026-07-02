# Hermes — CLAUDE.md (session orientation)

**Location:** `D:\Hermes\CLAUDE.md` (project root — auto-loaded by Claude Code on session start)

---

## ⚠️ READ THIS FIRST — and the MANDATORY UPDATE RULE

The running source of truth for this project is **`D:\Hermes\PROJECT_STATE.md`**.

### Boot procedure (every session, no exceptions)

1. **Read `PROJECT_STATE.md` fully.** It contains current state, all decisions made, the session log, and what's open.
2. Skim recent commits: `git log --oneline -20`
3. Only then start making changes.

Don't re-derive the architecture from scratch. The decisions in `PROJECT_STATE.md` § "Decision log" are deliberate. Surface conflicts before overwriting them.

### 🔴 MANDATORY: Update PROJECT_STATE.md as you work

This is a **binding rule, not a suggestion**:

- **Every time a new decision is made** (architectural choice, defaults change, policies change) → append it to § "Decision log" in `PROJECT_STATE.md` **in the same commit** as the code change.
- **Every time code structure changes** (new file, new table, new command, new service) → update the relevant section of `PROJECT_STATE.md` (Quick reference / Architecture / Database schema / commands tables) **in the same commit**.
- **Every time an open item is closed** or a new one identified → update § "What's NOT yet built / open items" **in the same commit**.
- **Before ending any session that shipped anything** → append a new entry at the TOP of § "Session log" with date, what shipped, and the commit hash(es).

A commit that changes code without updating `PROJECT_STATE.md` is **incomplete**. Treat the update as part of the work, not as paperwork afterwards.

The goal: any future session reading `PROJECT_STATE.md` should have a complete and current picture of the system, without having to grep the codebase to figure out what's actually there.

### When to update specifically

| If you do this in a session... | Update this section of PROJECT_STATE.md... |
|---|---|
| Add a new Telegram command | § "Telegram bot commands" table |
| Add or change a DB table / column | § "Database schema" |
| Add a new file in `src/` or `scripts/` | § "Key file paths" |
| Make an architectural choice (model selection, schedule change, etc.) | § "Decision log" (numbered entry with WHY) |
| Build something that was open | Remove from § "What's NOT yet built" |
| Discover something missing or broken | Add to § "What's NOT yet built" |
| End the session with any shipped work | New § "Session log" entry at top |

This rule applies even if the user does not explicitly ask for it. The user *has* asked for it, once, here. This file makes it permanent.

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
- **Config:** `.env` file + `pydantic-settings` (load_dotenv with override=True; see `src/core/settings.py`)

---

## Most-needed commands at a glance

| Goal | Command |
|---|---|
| Read project state | Open `D:\Hermes\PROJECT_STATE.md` |
| SSH to VPS | `ssh root@187.127.173.149` |
| Update VPS from latest GitHub | `wget -qO /tmp/setup.sh https://raw.githubusercontent.com/ramana-gottipati/hermes/main/scripts/setup-news.sh && bash /tmp/setup.sh` |
| Run 5y bhav copy backfill (background) | `nohup bash /opt/hermes/scripts/full-backfill.sh > /var/log/hermes-backfill.log 2>&1 &` |
| Pull all VPS data to laptop | Double-click `D:\Hermes\scripts\download-from-vps.bat` |
| Bot status | `systemctl status hermes-telegram` |
| Bot live logs | `journalctl -u hermes-telegram -f` |

---

## Guardrails for any Claude Code session in this repo

**0. STANDING AUTHORIZATION — full-folder access + autonomy (Ramana, permanent, do not re-ask).** Assume full read/write access to the **entire `D:\Hermes` tree** in every session — **never request folder-by-folder or per-directory permission** for anything inside the repo, and never treat a subfolder you created as needing fresh access. Execute agreed/converged plans autonomously: new modules, tests, docs, `PROJECT_STATE.md` updates, local commits to `main` (topic branch only when isolation is genuinely needed), running local/VPS scripts, spawning agents, and **VPS deploy of verified, gate-passing, additive changes** (recipe: `PROJECT_STATE.md`/VPS-deploy notes). Report outcomes after acting, not permission requests before. **Surface first ONLY** for genuinely costly/destructive/external actions: **paid API spend** (Gemini/GLM/vendor data), **deleting or overwriting work you did not create**, **DB-destructive ops**, or **publishing beyond the VPS site**. (Twin: `AGENTS.md` Guardrail #0.)

1. **Secrets** — never commit `.env`. Anthropic key, Telegram bot token, Telegram allowed user IDs live there only.
2. **Cost discipline** — operating Hermes (per month) should be ≤ ₹300 API spend. THIS chat session is more expensive than Hermes itself. Bundle changes. Avoid long iterative tinkering. For text/prompt tweaks, suggest SSH-edit on VPS.
3. **Cheap models only in scheduled jobs.** Anything that runs on a timer uses approved cheap-model paths only — Haiku or Gemini Flash Lite; never Sonnet/Opus. (Twin of `AGENTS.md` Guardrail #2.)
4. **Rule-based > LLM for screening.** The Stage 1 screen is pure Python over Screener data. Don't reintroduce LLM-driven screening.
5. **Value > quantity.** All cross-time-period stock metrics use rupees, not share count. Eliminates corporate-action adjustment bugs.
6. **Pre-compute over recompute.** Anything stored can be re-derived from raw data; don't normalise away the bhav copy archive.
7. **At session wrap, append to `PROJECT_STATE.md` § Session log** with what shipped + commit hashes. The doc is the running source of truth — keep it current.

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
| Bhav copy + DVPT signals architecture (Word) | `docs/hermes-bhavcopy-architecture.docx` |
| patearn methodology (source skill) | `resources/patearn/SKILL.md` + sibling files |
| Telegram bot implementation | `src/assistant/telegram_bot.py` |
| Database schema | `src/core/db.py` (search for `SCHEMA_BASE`) |
| Rule-based scoring | `src/automation/scoring.py` |
| Bhav copy ingestion | `src/automation/bhavcopy.py` |
| Signal computation | `src/automation/signals.py` |
| Deploy / install scripts | `scripts/setup-news.sh`, `scripts/full-backfill.sh` |
