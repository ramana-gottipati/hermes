# Patearn — performance & data-delivery architecture (work-stream of record)

> **Status:** active (opened 2026-06-19, data/performance session). **Companions:** `docs/ui-design.md` (D54 UI revamp — owns the render layer) · `docs/ui-perf-handoff.md` (the render-layer items handed to that session).
> **Owner split (the call, taken deliberately):** the UI/UX (D54) session owns `src/web/dashboard.py` (the entire render layer). This work-stream owns everything else — `src/main.py`, `src/core/db.py`, `src/automation/*`, infra/scripts, the serving edge. The seam is the natural data-engineer ↔ UI/UX division, and it also avoids two sessions editing the same file (PROJECT_STATE session-19 cross-absorption hazard).

---

## 1. Diagnosis (one paragraph)
The dashboard **computes and ships a full, uncompressed, uncacheable document on every click**; fast data apps **ship a cached shell once and then move only thin, precomputed data**. Target architecture, same stack (server-render + vanilla JS, no SPA): **shell once · data thin · read precomputed · stay warm.** Every fix is additive and no-regression.

## 2. Shipped this session (backend, isolated)
- **App-layer gzip** — `src/main.py`: `app.add_middleware(GZipMiddleware, minimum_size=500)`. Compresses every HTML/JSON response (incl. all of the UI session's pages) without touching their file. Belt-and-suspenders vs the unversioned edge proxy whose gzip status we can't confirm.
  - *State:* **committed locally** on `main` by explicit path (only my files; the UI session's working changes left untouched), **not pushed**. Live only after deploy — see § 8.
  - *Verify:* `python -m py_compile src/main.py` (syntax only; no side effects).
- **DB maintenance script** — `scripts/db-maintenance.sh`: `PRAGMA wal_checkpoint(TRUNCATE)` (reclaims the `-wal` that a long backfill + continuous reads let grow) **plus `PRAGMA optimize`** (refreshes `sqlite_stat1` so the planner stops mis-choosing the low-cardinality `idx_bhav_series` — folds audit findings E + F into one idle pass). Safe to re-run, not cron-wired yet (no trigger). `bash -n` clean.

## 3. Backend backlog (sequenced, with rationale)

### Land independently (read-path / infra — safe for the sole session any time)
- **Equity-allowlist JOIN — ASSESSED, NOT WORTH IT (2026-06-19).** On reading the code, `_LIQUID_FILTER` (`src/automation/stock_rs.py:64`) uses `s.symbol IN (SELECT symbol FROM nse_equity_list)` — an **uncorrelated** subquery against a `PRIMARY KEY` column (`nse_equity_list.symbol`, `db.py:381`), which SQLite already rewrites to a semi-join over the PK index. An explicit JOIN yields an equivalent plan (near-zero win) while churning three correctness-critical queries (leaders/laggards/conviction/rank) that can't be measured locally. Deferred per Doctrine B (don't optimize a hypothetical bottleneck). The earlier audit mislabelled it "correlated/per-row". *(The `_SCAN_FILTERS` copy in dashboard.py is the UI session's; same verdict.)*
- **Serving reproducibility.** uvicorn currently runs single-worker (`scripts/setup-news.sh:136`, no `--workers`) and the **nginx/TLS/gzip/static-cache edge is not in the repo**. Add `--workers N` (mind per-worker 256 MB mmap on the KVM4) and **retrieve + commit the nginx config**. Infra only; apply on next deploy (not triggered from here).
- **WAL hygiene + planner stats — SHIPPED as `scripts/db-maintenance.sh`** (see § 2). Replaces the "ready command" plan with a real, idle-only script that both reclaims the `-wal` and refreshes `sqlite_stat1`. Run after the deep backfill / at end of the nightly chain; cron-wire once validated.

### Fold into the D47 post-backfill full recompute (do NOT run a second full-history pass)
> D47 already mandates one full-history recompute once deep history (~2005) lands (PROJECT_STATE D47). Batch the two new precomputed columns **and** the O(N²) fix into *that* pass — recomputing millions of rows twice is the wrong data-engineering call.

- **`adj_close` precomputed nightly** into `stock_signals` via the canonical `src/automation/adjust.py` (closes long-open item **B5**). Kills the ~3.5 s cold `/dash/stock` route and removes the inline duplicate. The render switch is hand-off item 5.
- **`conv` (conviction) precomputed** into `stock_signals` + index `(trade_date, conv DESC)`. Turns the screener's whole-universe expression sort into a range-scan + LIMIT. The render switch is hand-off item 6.
- **O(N²) → rolling/deque windows** in `src/automation/signals.py:822–826,846` (today it rebuilds the full strictly-prior list per date and re-sorts per window). This is the real **scaling cliff**: nightly cost grows super-linearly as D47 deepens history. Rewrite to incremental add/evict windows; validate row-for-row against the current output (R/P scores, rank, `is_ath_dvpt` must be identical) before it powers the recompute.

## 4. Connection tier (note, low priority)
`get_conn()` opens a fresh connection + 7 PRAGMAs per call with a cold private 64 MB cache (`src/core/db.py:776–789,574–586`); `/dash/stock` pays it 3×. A pooled/warm read connection would keep the page cache hot — but `get_conn()` is shared with the per-symbol-commit writers, so changing it naively breaks the write model. Defer until a dedicated read-pool can be added without disturbing writers; mmap already softens the cold-cache cost (why WAL alone got clicks to 0.03–0.12 s).

## 5. Performance budget (targets)
Warm board/screener click **< 300 ms** · first-paint shell **< 50 KB gzipped** · chart pages **< 80 KB** initial doc + lazy data fetch · nightly chain **sub-linear** as history deepens.

## 6. Non-goals (shared doctrine)
No SPA / framework / heavy build · no Postgres (SQLite + WAL is right for one box) · no speculative caching · virtualize only the screener. Everything additive and reversible.

## 7. PROJECT_STATE.md note
Deliberately not edited this session to avoid colliding with the live UI session's wrap. When sessions consolidate (or a sole session resumes): add a Session-log entry (gzip shipped; maintenance script + these two docs created) and fold §3 items into "What's NOT yet built". This doc is the interim source of truth for the perf work-stream.

## 8. Go-live runbook (owned plan — the when/how/where)
The operational calls, taken so nothing is left dangling for the user to decide:

- **Committed, not pushed (done now).** My files are committed locally on `main`, staged by explicit path; the concurrent UI session's working changes are untouched and unstaged. Not pushed — push happens at consolidation so the two sessions' histories reconcile cleanly.
- **Go-live window = after the deep-history (D47) backfill completes** — the box is then idle (a watcher re-invokes a session at that point), the maintenance script's `TRUNCATE` can fully succeed, and there's no contention with a multi-hour writer. Deploying *now*, mid-backfill, from a session parallel to the UI session, buys nothing that can't wait one window.
- **At that window, in order:**
  1. `scp src/main.py hermes:/opt/hermes/src/main.py && ssh hermes 'systemctl restart hermes-api'` — gzip live.
  2. `scp scripts/db-maintenance.sh hermes:/opt/hermes/scripts/ && ssh hermes 'bash /opt/hermes/scripts/db-maintenance.sh'` — reclaim `-wal` + refresh planner stats.
  3. Fold a PROJECT_STATE Session-log entry, then `git push` (consolidated with the UI session).
- **Precompute pass (adj_close/conv + the O(N²) window fix) = same window, sole in tree.** Implement, validate row-for-row against real data, then run inside the D47 full recompute (not a second pass). Speced in § 3; deliberately NOT landed as dormant code now — it can't run until the recompute, and restructuring correctness-critical pipeline code mid-backfill is needless risk.
