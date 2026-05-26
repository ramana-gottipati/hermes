# Hermes — Project Root CLAUDE.md

**Location:** `D:\Hermes\CLAUDE.md` (project-root; auto-loaded by Claude Code on session start)
**Purpose:** Project-specific orientation for any Claude Code session in this repo.

---

## What Hermes is

Hermes is a personal AI agent deployed on a VPS that does three things:

1. **Personal assistant** — conversational interface (Telegram / web / API) backed by Claude
2. **Automation / task runner** — scheduled jobs, scrapes, workflow automation
3. **Trading / finance** — market data, alerts, signals, possibly automated trading

One agent, one codebase, three workloads. Modular under `src/` so each workload can evolve independently.

---

## Stack

- **Host:** Ubuntu VPS
- **Runtime:** Docker + docker-compose (clean isolation between services)
- **Language:** Python 3.11+
- **API framework:** FastAPI + uvicorn
- **LLM:** Anthropic Claude (via `anthropic` Python SDK)
- **Scheduling:** APScheduler (in-process) — can graduate to Celery + Redis if load demands
- **Datastore:** TBD — start with SQLite, move to Postgres when multi-process writes appear
- **Config:** `.env` file + `pydantic-settings`

---

## Project layout

```
D:\Hermes\
├── CLAUDE.md                  # this file
├── README.md
├── docker-compose.yml          # services: hermes-api, hermes-scheduler (add db/redis later)
├── Dockerfile                  # Python 3.11-slim base
├── requirements.txt
├── .env.example                # template — copy to .env, never commit .env
├── .gitignore
├── .dockerignore
├── src/
│   ├── main.py                 # FastAPI entrypoint
│   ├── core/                   # shared: settings, llm client, logging, db
│   ├── assistant/              # personal assistant — Telegram/chat handlers
│   ├── automation/             # scheduled jobs — APScheduler tasks
│   └── trading/                # market data, signals, broker integrations
├── config/                     # static config (instruments, schedules, etc.)
└── scripts/                    # deploy/util shell scripts
```

---

## Running locally

```bash
# one-time
cp .env.example .env            # fill in ANTHROPIC_API_KEY etc.
docker compose build

# run
docker compose up               # API on :8000, scheduler runs in its own container

# logs
docker compose logs -f hermes-api
docker compose logs -f hermes-scheduler
```

Without Docker (for quick dev):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn src.main:app --reload
```

---

## Deploying to the VPS

```bash
# from local
scp -r . user@vps:/opt/hermes/

# on VPS
cd /opt/hermes
docker compose up -d --build
```

A proper deploy script lives at `scripts/deploy.sh` once the first version is working.

---

## Guardrails for any Claude Code session in this repo

- **Secrets:** never commit `.env`, API keys, broker tokens, or wallet keys. They go in `.env` only.
- **Trading code:** any code that places real orders must be feature-flagged off by default (`TRADING_LIVE=false`). Dry-run / paper mode is the default. A bug here costs real money.
- **LLM cost:** use `claude-haiku-4-5` for cheap automation tasks; reserve `claude-sonnet-4-6` / `claude-opus-4-7` for assistant conversations that need reasoning. Cache system prompts.
- **One Hermes**, not a microservice constellation. Resist splitting modules into separate repos until there is a concrete reason.
- **Pin Python deps** in `requirements.txt`. Don't use `>=` for trading-adjacent libs (`ccxt`, `pandas`) — surprise upgrades break things.

---

## Built-in Claude Code skills useful here

- `claude-api` — when wiring up the Anthropic SDK (prompt caching, model selection, tool use)
- `plan` — before any non-trivial change
- `verify` — confirming the agent actually does what you intended
- `run` — launching the dev server / docker compose
- `code-review` — local PR review before pushing to VPS
- `engineering:debug` — diagnosing runtime issues

---

## Status

**Day 0** — scaffold landed. Nothing functional yet. Next steps:

1. Fill in `.env` from `.env.example` (Anthropic key first)
2. Implement `src/core/llm.py` — thin Claude client wrapper with caching
3. Pick the first workload to ship — recommend assistant (smallest blast radius)
4. Then automation (scheduled hello-world job)
5. Then trading (paper-mode market data fetch, no orders yet)
