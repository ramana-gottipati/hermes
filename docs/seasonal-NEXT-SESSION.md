# Seasonal Tape — Session Handoff & Carry-Forward (2026-07-12 → 2026-07-13)

> **Lifecycle: TRANSIENT** — the authoritative record until it is folded into
> `PROJECT_STATE.md` (§ Session log + § Decision log + § Key file paths + § Database schema)
> and `docs/strategies/`, then `git rm`-ed together with `docs/seasonal-tape-PLAN.md`.
> **Blocked on:** the parallel **codex** session's uncommitted edits to `PROJECT_STATE.md`
> (state:skip was used on every commit this session to avoid cross-author absorption).

## TL;DR — the whole Seasonal Tape estate is BUILT, DEPLOYED, and LIVE
A descriptive-only calendar-seasonality estate on the PIT idiosyncratic residual, live on
`https://srv1704897.hstgr.cloud`. Index/sector + **all ~2,427 EQ stocks**, weekly+weekday, event
cadence with delay variance, a ranked this-month screen, index divergence, and a wired
navigation journey. **Honest core finding: almost nothing certifies — the greying IS the
product** (rigorous calendar seasonality is not a tradeable edge net of the placebo+FDR stack).

## Commits (all on `main`, all deployed to the VPS + walked live)
1. `9a82731` — P0/P1: ship Seasonal Tape lens (index/sector). Engine `seasonal_tape.py` + view `seasonal_view.py`.
2. `bdbe4c3` — P2 stock layer: per-entity `seasonal_card` on the /dash/stock tab + /dash/index section; market-only stock family.
3. `19d1e77` — all-EQ universe + read-only on-demand + weekly/weekday strips + **event-cadence variance** + this-month screen + index divergence. New family `seasonal_tape_stock_all`.
4. `e5983d0` — **D122**: rank the this-month screen (Bullish / Bearish / Lookup modes).
5. `60242e7` — symmetric **stack + consolidation** layout (month & new 52-week stack); tight ±0.5σ gradient; removed the empty "Consensus script" panel.
6. `ce424f3` — discoverability **journey**: sub-nav on all 3 surfaces, index→constituent scan (`?index=`), "Scan stocks in {entity}" CTA, drill hint, screen rows → `#seasonal`.
7. `82060fa` — **ISO-week cell drill** (click a week on the 52-week stack → year-by-year) + clickable consolidation strips.
8. `63957f7` — **D122+**: confidence-adjusted ranking on the this-month screen (Wilson lower/upper bound + residual-magnitude tie-break + "Strength t" col + per-name month-rank). Display-layer only, hashes unchanged.
9. `557a209` — **nightly writer-safe TIMERS** (open-item #2): `hermes-seasonal-stock` (22:30 UTC, index+sector+all-EQ full recompute) + `hermes-seasonal-events` (23:00 UTC, all-EQ cadence). AUD-95-safe (`Unit=` binding, NO `Requires=`). `seasonal_events.py --backfill-all` derives the universe internally.
10. `266b8a2` — **bound `seasonal_events` to one asof** (space guard for the nightly): PK is `(symbol,event_type,asof)` so runs were accreting a full ~19k-row snapshot/day (33,924 live rows = 2 asofs). Per-symbol delete-then-insert (`_write` house pattern) + `--backfill-all` finalizer sweep of `asof < MAX(asof)`.

> ⚠ commits 8–10 are on `main` but **NOT pushed** — `origin/main` is at `76f5724`; local is 3 ahead. Push once codex settles (it may also be committing).

## Frozen families (`research.db.prereg_registry`) — INTEGRITY CRITICAL
| module | sha256 (short) | scope | note |
|---|---|---|---|
| `seasonal_tape` | `2882ccbc` | index/sector | strip market+sector |
| `seasonal_tape_stock` | `cb32d1b9` | stock (market-only) | SUPERSEDED by stock_all; kept as immutable history, still verifies |
| `seasonal_tape_stock_all` | `e566904c` | **all-EQ** (market-only) | the ACTIVE stock family; stale `frozen_family_stock_sha256` meta key deleted |

- **⚠ The module docstring IS part of the hash** (`_canon_spec()` includes `"doc": __doc__`). NEVER edit the `seasonal_tape.py` module docstring (or `_canon_spec`/GATES/MECHANISMS/constants) without a deliberate re-registration — it silently moves all three hashes.
- **Invariant check (run before/after ANY engine edit):**
  `python -c "from src.automation import seasonal_tape as st; print(st.frozen_family_hash()[:8], st.frozen_family_hash_stock()[:8], st.frozen_family_hash_stock_all()[:8])"` → MUST print `2882ccbc cb32d1b9 e566904c`.

## Files (all committed; `src/`)
- `src/automation/seasonal_tape.py` — engine: PIT residual z, certification (2 non-inert nulls + BH-Yekutieli FDR + N≥15 + epoch/OOS sign + mechanism), 3 families, `stock_universe_all` (all-EQ turnover-ranked, FUND-excluded), `compute_stock_inmemory` (READ-ONLY on-demand), `backfill_stocks_all`, `certify_cell` (mask-decert for stock results-months), CLI `--register-stock-all|--verify-stock-all|--backfill --scope stock-all|--ondemand`.
- `src/automation/seasonal_events.py` — **NEW**: event cadence. `load_event_history` / `project_next_window` (PAST-ONLY) / `expected_vs_actual` (signed WEEKS; OVERDUE→negative) / `backfill_events`. Outside both z-families, NO prereg.
- `src/web/seasonal_view.py` — the lens: scope tabs, entity SEARCH (stock), month 25y stack → **monthly consolidation** → **52-week stack** → **weekly consolidation** → weekday, event section, forward outlook, month+week **drill** (`_drill_panel(axis=month|iso_week)`), sub-nav, index→scan CTA.
- `src/web/seasonal_events_view.py` — **NEW**: `event_cadence_lane` / `event_cadence_card` / `render_events_section` (triangle timeline, OVERDUE flags, factual TIME variance).
- `src/web/seasonal_screen_view.py` — **NEW**: `/dash/seasonal-screen` (ranked D122, `?month=&index=&scope=&sort=&lean=`) + `/dash/seasonal-divergence` (Nifty200-vs-50 co-movement + YTD-vs-consensus).
- `src/web/lens_registry.py` (+3 Lens), `src/web/v2_surfaces.py` (+3 routes), `src/web/dashboard.py` (stock Seasonal tab: card + event card), `src/web/cockpit.py` (index seasonal section: card + event card — **⚠ codex is now live-editing cockpit.py**).

## Routes (LIVE)
- `/dash/seasonal-tape?scope=index|sector|stock&entity=..&cal=fy|cy&drill=<month>&wdrill=<week>` (nav: Markets → Big picture "Seasonal tape").
- `/dash/seasonal-screen?month=&scope=stock&index=<constituent filter>&sort=&dir=&lean=` (ranked Bullish/Bearish/Lookup).
- `/dash/seasonal-divergence?a=Nifty 200&b=Nifty 50&cal=`.
- `/dash/stock?sym=X#seasonal` (Seasonal tab: card + event triangles) · `/dash/index?idx=X` (seasonal section).

## Data state (VPS `hermes.db`)
- **Index history**: broad **Nifty 50/100/200/500 deep to 2004-01-01** (I sourced pre-2012 from niftyindices.com — see method below). Sector/size indices still **2012-capped** (back-calc declined for shared `index_rows` integrity).
- **Stock**: **2,427 EQ stocks** backfilled under `seasonal_tape_stock_all` (all-EQ, ~7 min).
- **Events**: `seasonal_events` for 2,427 stocks, **14,562 rows, 430 OVERDUE** (re-run after any new stock/event backfill).
- Bounded snapshots: `seasonal_cells / seasonal_stack / seasonal_outlook / seasonal_breaks / seasonal_meta / seasonal_events`. **0 colored** everywhere (honest).

## Key findings & decisions
- **Rigorous calendar seasonality does NOT certify** (index/sector/stock all 0 colored). Descriptive tendencies visible: Nifty 500 Jan/Feb weak (15%/20% up), Apr best; **MARIUTI Sep up 89%** (16/19). Consistent with the ledger ("momentum is beta not skill"). Stays descriptive, never a signal.
- **D122 (Ramana-authorized, 2026-07-13)**: the this-month screen ranks by descriptive base-rate. **Display-layer amendment only** — frozen hashes unchanged, `seasonal_tape.py` docstring NOT edited; D122 recorded in the screen's banner/docstring + commit. A true forward-return/certified ranking would need a real re-registration.
- The **inert-null catch**: year-label shuffle is permutation-invariant (zero-width) → BANNED; use circular-block + cyclic-rotation nulls.
- **mask-decert**: results-month (Jan/Apr/Jul/Oct) stock cells force-decertified (PEAD-in-costume guard). Verified live (0 results-month cells colored).
- **On-demand = READ-ONLY** (`compute_stock_inmemory`, no web-process DB write — protects the writer-safe-restart gate).
- **niftyindices pre-2012 index history method**: `POST /BackPage/getHistoricaldatatabletoString` body `{cinfo:"{'name':'NIFTY 50','startDate':'01-Jan-2004','endDate':..,'indexName':..}"}`. Akamai-gated → a VPS `requests` call returns the HTML shell; must be captured via the **in-app browser same-origin fetch** (gzip+base64 out). The daily `indexes.py` (`ind_close_all`) source is HARD-CAPPED at 2012 — pre-2012 rows are a one-time manual enrichment, NOT reproducible by the pipeline.

## OPEN ITEMS (carry-forward)
1. **🔴 PROJECT_STATE.md reconciliation** — the entire arc (7 commits, D122, 3 families, new tables/files) is in commits but NOT yet in `PROJECT_STATE.md` (§ Session log / Decision log / Key file paths / Database schema / What's-NOT-built). Blocked by codex's uncommitted edits in that file. Do it once codex settles: add entries, retire `seasonal-tape-PLAN.md` + this file.
2. ~~**Timers / durability**~~ — ✅ **DONE** (`557a209` + `266b8a2`, deployed + verified 2026-07-13). Two nightly units live on the VPS: `hermes-seasonal-stock.timer` (22:30 UTC) recomputes index+sector+all-EQ; `hermes-seasonal-events.timer` (23:00 UTC) refreshes cadence. Both **enabled + armed** (`list-timers` shows future next-runs; both services verified `inactive` — nothing fired on enable). Events service **functionally test-run**: universe grew 2,427→**3,227** (newly-liquid EQ picked up), table now **bounded to one asof** (19,362 rows, 469 OVERDUE). Frozen hashes intact throughout. **Still manual:** pre-2012 broad-index rows (niftyindices note) — not pipeline-reproducible.
3. **Sector/size index history** stays 2012-capped (back-calc declined). Sector tapes shallower than broad. Decide if a curated sector deepening is worth it.
4. **Gates 7 (full earnings-cadence mask) + 9 (residual diagnostics)** are conservatively stubbed for stock scope (mask-decert covers the critical case). Full impl changes no current output (nothing certifies) — clean next increment.
5. **Week-drill on the embedded stock-page card** — the month+week drill is on the lens; the /dash/stock Seasonal-tab card doesn't drill yet (Ramana offered a "yes" pending).
6. **Weekday stack** — weekday is a strip only; a 5-col × 25-yr grid was offered, pending Ramana's call.
7. **cockpit.py multi-session** — codex is live-editing it; my event-card embed is committed, its edits uncommitted → watch for conflicts on next deploy/commit.

## Deploy / ops recipe (verified this session)
- **Single-owner files** (`seasonal_*.py`) → plain `scp`. **Hot/forked files** (`dashboard.py`, `cockpit.py`, `lens_registry.py`, `v2_surfaces.py`) → **PATCH-OVER only** (fetch VPS copy, apply anchored hunks locally, `scp` back), NEVER full-scp (VPS drifts behind HEAD).
- Every push: `tr -d '\r'` (CRLF) → `py_compile` → `import` check → **then** `systemctl restart hermes-api` (writer-safe; NEVER hermes-telegram / setup-news.sh AUD-28 / timer-start AUD-95). Backups to `/tmp/bak.*`.
- Backfills: off-hours, per-symbol commits, `nohup` background. Walk the public `hstgr.cloud` URL after.
- Commits: stage EXPLICIT paths only (codex is live) + `state:skip` (PROJECT_STATE entangled).
- **Timer install (verified 2026-07-13):** scp `.service`+`.timer` → `/etc/systemd/system/`; `sed -i 's/\r$//'` (CRLF); `systemctl daemon-reload`; `systemctl enable --now <timer>`. **AUD-95-safe ONLY because the timers have NO `Requires=`** (they bind via `Unit=` in `[Timer]`) — so `enable --now` arms the OnCalendar run WITHOUT firing the service. ALWAYS verify immediately: `systemctl is-active <service>` must return `inactive`, and `list-timers` must show a FUTURE next-run. **Never add `Requires=<service>` to a hermes timer's `[Unit]`** (that is the exact wolfe-scan shape the AUD-95 ban warns about). Seasonal units run under `/opt/hermes/.venv` (pure stdlib). No `hermes-api` restart needed — the CLI-only change doesn't touch the imported view surface, and the view reads `MAX(asof)` so a data refresh goes live on its own.
- **`seasonal_events` is a SINGLE-asof snapshot** — its PK includes `asof`, so any backfill MUST delete the symbol's prior rows first (done in `backfill_events` + `--backfill-all` sweep). Don't reintroduce plain `INSERT OR REPLACE` without the delete, or the nightly timer leaks ~19k rows/night.

## CARRY-FORWARD PROMPT (paste into the next session)
> Continue the Hermes **Seasonal Tape** work. It is BUILT + LIVE on the VPS across 7 commits
> (latest `82060fa`), read `docs/seasonal-NEXT-SESSION.md` first (full record + frozen-hash
> invariant + deploy recipe). Frozen families `2882ccbc / cb32d1b9 / e566904c` must stay
> byte-unchanged (the module docstring is hashed — do NOT edit it). Top open items:
> (1) reconcile `PROJECT_STATE.md` (Session/Decision/Key-file-paths/Schema) for the whole arc
> + D122 once the parallel **codex** session's `PROJECT_STATE.md` edits are committed, then
> retire `seasonal-tape-PLAN.md` + this handoff; (2) wire nightly timers for the all-EQ stock
> backfill + event snapshot (writer-safe, off-hours); (3) optional per-Ramana: week-drill on the
> stock-page card, a weekday stack, sector-index deepening. Deploy = patch-over hot files + plain-scp
> single-owner + writer-safe restart; verify the frozen-hash invariant before/after any engine edit.
> Codex may still be editing `cockpit.py` — stage explicit paths only, `state:skip`.
