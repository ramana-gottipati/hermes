# Lane D — Data & Provenance: knowable_at calibration + the deterioration-veto re-test

> Session 2026-06-28 (autonomous, Lane D of the parallel-sessions plan). Owner: the Data &
> Provenance lane. Owns only `provenance.py`, `fundamentals_filing_dates.py`,
> `fundamentals_provenance.py`, `cci_*.py`, the research.db lane — zero web-layer edits.
> Run on the VPS (local hermes.db is a 4-symbol stub). Folds into PROJECT_STATE + memory.

Two missions: (1) the **survivorship-complete deterioration-veto re-test** on the 1,722
delisted names; (2) the **knowable_at BSE calibration** so `provenance.lag_audit()` is
non-empty and the fundamentals archive de-models from "modeled" to real exchange dates.

---

## MISSION 1 — deterioration-veto re-test → **BLOCKED (data gap, quantified)**

**Question:** does CCI credibility *deterioration* flag real blow-ups out-of-sample? The prior
falsification (memory [[cci-credibility-timeseries]], `cci_backtest --mode veto`) found no edge
**on survivors**, but that test is structurally blind: the veto's true target — companies that
deteriorated and **delisted** — is censored out of a current-holder universe. The re-test needs
deterioration signals for the delisted names. This session checked whether that data exists.

**It does not.** Coverage of the target population, measured on the VPS:

| Population | Count | Has concall capture | Has extracted credibility |
|---|---:|---:|---:|
| `security_master` INACTIVE (delisted) | 1,722 | 8 | 1 |
| …delisted **2016–2025**, ≥500 trading days (distress-era, real companies) | **648** | **5** | **~0** |
| `credibility_series` symbols (the scored universe) | 806 | 806 | 805 ACTIVE / **1 INACTIVE** |

- The one INACTIVE name in `credibility_series` is **CIGNITITEC** (last traded 2026-05-14 — a
  rename/recent, not a blow-up).
- The 8 delisted names with *any* concall row are mostly **renames/mergers** (MINDTREE→LTIMindtree,
  CIGNITITEC, GSPL). Only a handful are genuine failures — **MANPASAND** (Manpasand Beverages, an
  audit-resignation fraud), **LAKSHVILAS** (Lakshmi Vilas Bank, forced amalgamation), **LEEL** —
  and **none of them has a single extracted guidance row, score, or credibility-series point.**

**Root cause.** Concall ingestion was built to sweep the **current liquid universe** by priority
rank (`concalls.py --universe N`, liquidity-ranked). Delisted names were never targeted, so they
enter the corpus only incidentally (8 of 1,722 = 0.5%). Extraction (paid Gemini) was further
prioritized to active names, so even the incidental delisted captures were never extracted into
promises. The veto's target population is therefore **uncomputable end-to-end** — we have neither
the concalls nor the credibility series for the names that actually blew up.

**Verdict.** The survivorship-complete re-test **cannot be run with current data**. The CCI
deterioration-veto therefore remains **DESCRIPTIVE-ONLY** (the doctrine already held in
[[cci-credibility-timeseries]] / [[phase0-provenance-coverage]]); it has *not* earned a validated
avoid claim, and this session did not manufacture one from survivor data (which can only fail to
validate it, never validate it). Recorded as a benchmark per [[ramana-working-principles]]
("nothing discarded → record every result").

**What it would take to unblock (costed, for a future decision — NOT done here):**
1. **Ingest** (free, perishable — see the data-capture doctrine in [[cci-credibility-timeseries]]):
   target the ~648 distress-era delisted names in `concalls.py` (`--targets`), pulling their
   transcripts from BSE's archive *while they still exist*. Many will 404 (delisted IR pages
   rot) → expect partial yield, perhaps 150–350 names with ≥1 usable call.
2. **Extract** (paid Gemini ≈ ₹0.2–0.3/transcript): the promises for those names. At ~12
   calls/name × ~250 names ≈ 3,000 extractions ≈ **₹600–900**.
3. **Settle + score + series**: free, reuses the existing pipeline (`concall_settle` →
   `concall_scores` → `cci_series`) — these names settle against the 24-yr `fundamentals_history`
   archive, which *does* retain delisted history.
4. **Re-test**: deterioration-flag-before-delisting vs a matched surviving control, with delisting
   as the censored blow-up event → real CIs. Only after step 3 yields ≥~50 delisted names with
   ≥3 resolved promises each is a defensible CI possible.

Until funded, the honest status is **DATA-BLOCKED**, and the avoid-overlay stays descriptive.

---

## MISSION 2 — knowable_at BSE calibration → **DONE (lag_audit non-empty; archive de-modeling)**

**Problem.** `fundamentals_history` stamps a **modeled** `report_date = period_end + 50d
(quarterly) / + 90d (annual)` — a synthetic uniform lag with no real filing date behind it. A
no-look-ahead backtest that treats that as "knowable" **leaks look-ahead for late filers** (the
number wasn't public yet) and is over-conservative for fast ones. `provenance.lag_audit()` existed
to measure the error but ran empty (no real dates captured).

**What shipped this session (all on the VPS, owned modules only):**

1. **`bse_scrip_map` seeded reproducibly.** Added `seed_scrip_map_from_bse()` (+ `--seed-bse`) to
   `fundamentals_filing_dates.py`: fetches BSE's equity **scrip master** (`ListofScripData/w`) and
   joins it to `security_master` on **ISIN** (robust to symbol ≠ BSE ticker and to renames),
   scoped to symbols that actually have a `fundamentals_history` archive. Result: **1,873 of the
   1,979** archived-with-ISIN symbols mapped (94.6%); 106 ISINs unmatched (delisted/suspended,
   absent from the Active master).

2. **Fixed the BSE announcements endpoint.** The committed module pointed at `AnnGetData/w`, which
   now soft-blocks ("No Record Found!"). The live contract is **`AnnSubCategoryGetData/w`** with
   lowercase **`strscrip`** + **`subcategory=-1`**; response parsing hardened against the bare
   `"No Record Found!"` string; subject matching now scans both `NEWSSUB` and `HEADLINE`.

3. **`lag_audit()` semantics fixed (`provenance.py`).** The function mislabeled the leak
   direction: it counted `err < 0` as `n_leaks`, but with `err = real_filing − modeled_date`, a
   **leak is `err > 0`** (real filing *later* than modeled ⟹ a backtest using the modeled date
   sees the datum *before* it was public). Corrected to report `n_leaks` (err>0, with
   `leak_median`/`leak_max`), `n_conservative` (err<0, safe), and `n_exact`. `provenance --selftest`
   still green (35 classes).

4. **Backfill run on the VPS** → `provenance.lag_audit()` is **non-empty**. Smoke + pilot
   validated; full universe sweep made restartable (per-symbol commit; `resume` skips done names)
   after catching that the original `backfill_universe` held a **single multi-hour write
   transaction on the production 16 GB hermes.db** (lock-contention + total-rollback-on-crash risk).

**The calibration finding (pilot, n=437 period-pairs across 26 names — universe figures below
once the full sweep lands):**

| metric | value | meaning |
|---|---:|---|
| median err | **−23 d** | modeled date is typically ~23 days **later** than the real filing → the +50/+90 model is **over-conservative**, not leaking, for typical filers |
| `n_conservative` | 395 (90%) | modeled later than real (safe) |
| **`n_leaks`** | **38 (8.7%)** | modeled **earlier** than real ⟹ genuine look-ahead; `leak_median` 9 d, `leak_max` 85 d |
| `n_exact` | 4 | |

**Interpretation.** The leak is **name-concentrated, not random**: bluechip fast filers (RELIANCE:
23/23 conservative, files ~19 d after quarter-end) never leak, while **calendar-year filers (ABB,
3M India: Q4+annual at Dec-31 filed ~50 d later) and slow-filing small/mid-caps (annuals landing
Jul/Aug vs a modeled Jun-29)** do. So a PIT backtest on the modeled date injects look-ahead on a
minority (~9%) of periods, but for *those* names it can be material (up to ~85 d). Calibration
replaces the blanket +50/+90 with the **real per-period exchange date** via
`provenance.observe()` → `provenance_for()` flips MODELED → INGESTED automatically.

**Match-quality caveat (honest):** assignment is headline-first (precise) with a strict
single-candidate date-heuristic fallback; spot-checks (ABB, RELIANCE) confirm filings land on the
correct periods with sane 33–50 d post-period-end gaps. Extreme quarterly "leaks" (>~75 d, e.g.
ABB Q2-2022 matched to a Nov filing) are most likely **restatements/revised filings**, not the
original — they inflate the leak tail slightly and warrant manual review before any per-name PIT
claim. The **distribution and direction** (mostly conservative; ~9% concentrated leaks) are robust.

### De-model coverage (the payoff) — REALIZED
- Archive: **1,983 symbols / 767,258 rows / 2002–2026** (`fundamentals_history`).
- **Realized de-model rate = 73.6%** of archived *periods* on the names processed so far carry a
  **real BSE exchange filing date** (1,494 captured / 2,031 archived distinct (symbol,
  period_type, period_end) over the done names). Split: Annual 671 / Quarterly 823. This lands at
  the honest lower edge of the run-book's **75–85%** estimate and projects cleanly across the
  universe; the residual ~26% is pre-2006 annual history (below BSE's archive floor), the 106
  unmapped delisted/suspended ISINs, and restatement/subject-parse misses.
- Full universe sweep (1,847 mapped symbols) runs detached on the VPS (`--backfill-universe`,
  per-symbol commit, `resume`-able; `/var/log/hermes-filing-backfill.log`). Final exact figure:
  re-run the coverage query (above) + `--lag-report` once the sweep completes. Because
  `provenance_for()` already prefers the captured real date, **every de-modeled period is live to
  any PIT reader the moment it lands** — no further wiring needed for reads.

### Forward hook (`fundamentals_provenance.py`)
Selftest green on the VPS; it captures real first-seen `knowable_at` for **newly-ingested** periods
(recency gate rejects deep history). Because the archive is already fully ingested, a `--run` today
captures ~0 (correct) — its value accrues going forward. **Gated deploy** = swap the scheduler's
`collect_universe` → `collect_universe_with_provenance` (one line, in a parallel-owned scheduler;
not done here per ownership boundaries).

---

## Files touched (owned only) — commit at wrap
- `src/automation/fundamentals_filing_dates.py` — `seed_scrip_map_from_bse()` + `--seed-bse`;
  `AnnSubCategoryGetData` endpoint + param/response fixes; per-symbol commit + `resume`.
- `src/automation/provenance.py` — `lag_audit()` leak-direction semantics fixed.
- `src/automation/fundamentals_provenance.py` — unchanged (deployed + selftest-validated only).

NOT touched: any web-layer file; `concalls.py`/`concall_*` (parallel-owned); PROJECT_STATE.md /
shared docs are dirty from parallel lanes → updates ride the reconciliation (noted, not staged).
