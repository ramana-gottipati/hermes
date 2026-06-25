# Phase 0 — Provenance + Coverage & Settlement ledger (TRANSIENT run-book)

> TRANSIENT working doc (per [[transient-doc-lifecycle]]). Fold the durable parts into
> `docs/product-strategy-2026.md` §10 + memory when this lands, then `git rm`.
> Owner: the PO/sole-builder session (Patearn). Created 2026-06-26.

## What this is
The trust-first Phase-0 foundation (the §9 "earn-trust-before-you-sell-it" corrections), built
as **new isolated modules + a thin gated hook** — zero edits to the parallel-owned web/ingestion
tree (`dashboard.py`/`cockpit.py`/`main.py`/`stock_chart.py`/CCI files all dirty).

Signal-event bus already shipped (`signal_events.py`, commit `b36c26d`). This adds:
- `src/automation/provenance.py` — per-data-class provenance/integrity spine (owns its own tables).
- `src/web/coverage_view.py` — the "Coverage & Settlement ledger" v2 screen (imports `ui_kit`).
- survivorship surfaced via `provenance.universe_policy()` reusing the existing `security_master`.

## Panel that designed it (read-only, 2026-06-26)
Three specialist agents (data-engineer · trust/compliance+GTM · adversarial red-team). The
red-team's binding corrections are folded into the build (below). Agent IDs for follow-up:
data-eng `aea17a2352d0445d0`, GTM `ac7e9f19f2a04c311`, red-team `a30e7d693b1ad2469`.

## Binding red-team corrections — FOLDED INTO THIS BUILD
1. **Kill `modeled: bool`** → `basis` is a required enum (`AS_TRADED|INGESTED|MODELED|DERIVED|EVENT`);
   modeled dates carry `lag_days` and the basis word is embedded *in the display string* so a
   downstream SDK/MCP/LLM consumer cannot silently strip it. `/v1` (next step) must serialize a
   modeled date as `{value, basis, lag_days}`, never a bare ISO string.
2. **`observe()` is forward-only and says so.** Historical fundamentals stay honestly "modeled" —
   we deliberately do NOT seed `knowable_at` from 2026 scrape timestamps (that is an *upper bound*
   from a late scrape → over-conservative + misleading for historical backtests). Real first-seen
   accrues only going forward; `lag_audit()` measures the modeled-lag error once it does.
3. **`universe_policy()` headlines the bhav-archive FLOOR date** + a left-censoring proxy
   (count of names whose `first_date == floor`) + states survivorship is asymmetric (within-window
   only) + SME (SM/ST) excluded. `universe_on()` callers must caveat pre-floor dates.
4. **Coverage leads with the robust-core FUNNEL** (`touched → scored → ≥1 → ≥3 → ≥10 resolved`);
   "978 touched" is a labelled footnote, never the headline. Plus a **tier × n_resolved cross-tab**
   (self-incriminates thin-sample A+); unsettled names show `UNPROVEN (n=K)`, never a credibility level.
5. **Append-only restatement/corrections log** (`provenance_restatement` table + `record_restatement()`).
6. **Freshness = cadence + staleness-vs-cadence + a visible pause/incident banner + a one-line
   single-node/no-HA-DR honesty statement.**

## DISCLOSED-NOW, fix later (need parallel-owned files / external data — recorded as open items)
- **ISIN rename auto-confirm cross-gate** vs `security_events` breaks (red-team 2.2) — a behavior
  change to the committed `security_master.py`; for now `universe_policy()` DISCLOSES confirmed-vs-
  candidate counts + the ISIN-sparsity survivor bias (2.3). Harden in a dedicated session.
- **Method/prompt/model version stamp per CCI row** (red-team 5.3) — CCI producers are parallel-owned;
  registry carries a `method_versioned` flag + the coverage copy discloses the gap.
- **BSE filing-date lag CALIBRATION** before any PIT/backtest claim (red-team 1.2) — needs a new
  BSE-date scrape; `lag_audit()` is the tool, runs empty until then; methodology says so.
- **PIT reproducibility proof** (versioning + "reproduce this as-of read") (red-team 5.2) — Phase-1.

## Build / verify checklist
- [ ] `provenance.py` — `--selftest` green (synthetic in-memory DB, no real data needed).
- [ ] `coverage_view.py` — TestClient mounts + `/dash/coverage` 200 + key sections present.
- [ ] py_compile both; inject→assert→cleanup for `provenance_knowable`/`_restatement` on local stub.
- [ ] Commit own new files (explicit paths, co-author trailer); HOLD for Ramana before push/deploy.
- [ ] Then: `/v1` service-layer skeleton (`src/api/v1/`) consuming `provenance.stamp`.

---

## PLAN — real `knowable_at` capture (forward ingest hook + BSE filing-date backfill)
> Added 2026-06-26 (investigation only; NO code shipped — `fundamentals_history.py` is
> committed/clean but treated as parallel-owned, so the design is zero-touch on it).
> This is the concrete build spec for two run-book open items: the forward-only
> `observe()` wiring and the "BSE filing-date CALIBRATION" line.

### 0. PREREQUISITE (key contract) — ✅ RESOLVED in the provenance lane (2026-06-26)
Was BROKEN: `provenance --selftest` failed ("earliest must be preserved") because three
`provenance_knowable` key formats disagreed AND `provenance_for._key()` dropped `period_type`
— but `(symbol, period_end)` is **not unique** (annual *Mar-2023* and quarterly Q4 *Mar-2023*
share `period_end=2023-03-31`, different filing dates). The provenance-owning session fixed it:
`provenance.period_key(symbol, period_type, period_end)` → **`"<SYM>|<A|Q>|<period_end>"`** is now
the ONE builder for both writer and reader (`data_class` is a separate PK column, not in the key),
and `provenance_for(..., period_type=...)` selects the right modelled lag too. **Selftest green
(35 classes).** Consumers MUST build keys via `period_key()` — never hand-format.

### A. Forward ingest hook — NEW isolated wrapper, ZERO edits to the collector
New module `src/automation/fundamentals_provenance.py` (house pattern: own module, thin gate):
```
def collect_with_provenance(symbol, con, *, recency_gate_days=150):
    before = {(pt, pe) for pt, pe in con.execute(
        "SELECT DISTINCT period_type, period_end FROM fundamentals_history WHERE symbol=?", (symbol,))}
    n = fundamentals_history.collect(symbol, con)          # unchanged; does its own INSERT-OR-REPLACE+commit
    after  = {(pt, pe) for pt, pe in con.execute(... same ...)}
    fresh  = [(pt, pe) for (pt, pe) in (after - before)
              if (date.today() - date.fromisoformat(pe)).days <= recency_gate_days]   # the HONESTY gate
    for pt, pe in fresh:                                   # one observe per period (INSERT-OR-IGNORE keeps earliest)
        provenance.observe("fundamentals_history", provenance.period_key(symbol, pt, pe),
                           conn=con, symbol=symbol, source_note="screener-first-seen")  # knowable_at defaults to now
    return n
```
(NOTE: build via `provenance.period_key()` — the §0 canonical builder. The BSE backfill module
`fundamentals_filing_dates.py` already follows this exact contract.)
Scheduler calls the wrapper instead of `collect()`. Rationale:
- **Diff before/after the upsert** = the only way to detect a first-appearance, because `collect()`
  is `INSERT OR REPLACE` (re-writes every period every run) and `fundamentals_done.at` is per-symbol
  + overwritten, so neither carries a per-period first-seen today.
- **Recency gate is the honesty guard** (red-team #2 in spirit): on a symbol's *initial* backfill
  `before` is empty so `after-before` = its entire deep history; stamping those `now` would be a
  misleading 2026 upper bound on a 2015 period. The gate keeps only period_end within ~150d of
  today (just-filed quarter), discarding deep history → leaves it honestly MODELED. Same gate also
  handles late-added symbols. `observe_batch` is `INSERT OR IGNORE` so re-runs preserve the earliest.
- **Bound direction (state it correctly):** first-seen `S ≥ true filing date F`, i.e. **S is an
  upper bound on F** = the earliest date a no-look-ahead backtest may use the datum. Gating on S
  can never inject look-ahead (unlike modeled `period_end+lag`, which falls either side of F and
  leaks for late filers). With a regular scrape cadence S≈F+cadence → a *tight* real bound.

### B. BSE filing-date backfill — the ONLY retroactive de-modeler
New module `src/automation/fundamentals_filing_dates.py`, reuses concalls.py's proven BSE pattern
(`BSE_HEADERS` browser-UA+Referer, `requests`+pacing).
- **Source:** BSE corporate-announcements JSON `api.bseindia.com/BseIndiaAPI/api/AnnGetData/w`
  (category=Result), per-announcement `NEWS_DT` = the real filing timestamp. Ref impl:
  BennyThadikaran/BseIndiaApi `get_all_announcements.py`. **Archive depth: 2006+** (BSE official).
- **symbol→BSE scripcode map** (the main coverage limiter): BSE scrip master / ISIN join (ISIN is
  sparse in our bhav feed — survivor-biased toward listed names) / Screener already bridges the BSE
  code. Build a one-time map, accept partial coverage, disclose it.
- **announcement→period match:** parse the period from the result-announcement subject, else nearest
  announcement DATE in the [period_end+30d, period_end+75d] window. Store real date via `observe()`
  (`source_note="BSE-AnnGetData"`), then `lag_audit()` reports `(BSE_date − modeled_date)` — i.e.
  exactly how much look-ahead the +50/+90 modeling was injecting. (This is what `lag_audit()` is for.)
- **NSE** (`api.nseindia.com/api/corporate-announcements`) = cross-check/fallback only: harder
  bot-blocking (cookie priming), shallower clean archive.
- Disclose: 2006 floor; scrip-map gaps (delisted/renamed); pre-~2012 category-tag noise; the
  period-match heuristic needs a validation pass on the pilot set before any PIT/backtest claim.

### C. Coverage estimate (de-model potential) — band now, exact on VPS
research.db is VPS-only; compute the exact figure there with:
```sql
SELECT substr(period_end,1,4) AS yr, period_type, COUNT(*) rows,
       SUM(CASE WHEN period_end >= '2006-01-01' THEN 1 ELSE 0 END) AS bse_window_rows
FROM fundamentals_history GROUP BY yr, period_type ORDER BY yr;
```
- **Forward hook:** de-models 0% of history, but ~100% of every NEW period from switch-on (tight).
- **BSE backfill:** period_end ≥ 2006 ≈ 20 of 24 cohort-years → **all** quarterly rows (only ~3y
  deep, all post-2023) + the bulk of annual rows are in-window; pre-2006 annual (~4 cohorts) stays
  modeled. Net of within-window match rate (scripmap × category-tag × period-match ≈ 70–88%):
  **≈ 75–85% of all archived rows could carry a real exchange filing date.** Replace the band with
  the query above before quoting a number externally.

### Build order / status
1. ✅ **DONE** — key contract (§0) fixed in the provenance lane; `provenance --selftest` green.
2. ✅ **BUILT + offline-verified (2026-06-26)** — `src/automation/fundamentals_filing_dates.py` (§B):
   BSE result-announcement backfill → `provenance.observe()` under `period_key`. `--selftest` green
   (parse + match + observe round-trip, ptype-keyed, idempotent); `py_compile` clean. Untracked,
   uncommitted, NOT yet run against BSE/research.db. **VPS run gated on Ramana.**
   - Pre-run on VPS: (a) seed `bse_scrip_map` (`--seed-scrips <csv>`), (b) validate BSE field names
     (`NEWS_DT`/`HEADLINE`) + `is_results_filing`/`period_from_subject` on the ~25-name pilot before a
     universe sweep, (c) `--backfill RELIANCE` smoke, then `--lag-report` to read the look-ahead error.
3. ⏳ **OPEN (provenance/ingestion lane)** — §A forward hook (`collect_with_provenance` wrapper +
   scheduler swap). The provenance session built `period_key` naming the writer — likely theirs.
4. ⏳ Run the §C coverage query on research.db; fold the real % into product-strategy §10 +
   PROJECT_STATE decision log. **HOLD for Ramana before any VPS deploy.**
