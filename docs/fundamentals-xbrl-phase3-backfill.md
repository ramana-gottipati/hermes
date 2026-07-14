# Fundamentals migration Phase 3 — XBRL historical backfill & Screener retirement

> **Lifecycle: TRANSIENT-CAMPAIGN.** The build/decision plan for Phase 3 of the Screener→NSE-XBRL
> migration (Guardrail #8). Retire once the backfill has run, the residual live scrapers are removed,
> and [fundamentals-xbrl-migration.md](fundamentals-xbrl-migration.md) § Phasing marks Phase 3 DONE.

**Status:** DRAFT — awaiting Ramana's decisions (§10). Read-only coverage audit run 2026-07-14 (₹0, no writes).
**Predecessor:** Phases 1–2 LIVE (forward-only gated ingest + bank mapper + shareholding). See the migration doc.
**Module reused:** `src/automation/fundamentals_xbrl.py` (no new extractor — Phase 3 is an orchestrator on top).

---

## 1. Objective / definition of done

Convert every **gate-passing** symbol's **2018→present** history in `research.db.fundamentals_history`
from Screener-scraped (`source IS NULL`) to primary-source NSE XBRL (`NSE-XBRL-CONSO`/`-SA`) — same
values, true point-in-time broadcast dates — then remove the two live Screener network paths so
`screener.py` can be deleted. Everything that **cannot** be migrated is explicitly source-labeled,
never silently mixed with as-filed XBRL.

Done when: (a) the addressable window is XBRL-sourced for all gate-pass symbols; (b) the frozen tail,
gate-fail cohort, and bank annuals are labeled; (c) no live consumer calls `screener.py` /
`fundamentals_history.py`; (d) Guardrail #8's "one Screener dependency" line is closed in
PROJECT_STATE + the migration doc.

## 2. Starting line — read-only coverage audit (2026-07-14)

`fundamentals_history`: **770,324 rows · 1,997 symbols · 37 metrics.**

| Source | Rows | Symbols | period_end span |
|---|--:|--:|---|
| Screener (`source IS NULL`) | 770,211 | 1,993 | 2002-03-31 → 2026-06-30 |
| `NSE-XBRL-CONSO` | 86 | 8 | 2026-03-31 → 2026-06-30 |
| `NSE-XBRL-SA` | 27 | 3 | 2019-03-31 → 2026-06-30 |

**The split that defines the work:**

| Cohort | Rows | Symbols | Fate |
|---|--:|--:|---|
| **Addressable** (Screener, ≥ 2018-01-01) | 654,070 | 1,933 | **Migrate to XBRL** where gate passes |
| **Frozen tail** (Screener, < 2018-01-01) | 116,141 | 1,356 | Keep + label — no NSE XBRL exists that far back |
| Already migrated (any XBRL row) | 113 | 11 | done (forward feed) |

- **Fetch upper-bound:** 37,914 period-instances in the addressable window (Q 23,164 / A 14,750).
- **Untouched addressable symbols:** ~1,926.
- **Priority tiering:** NSE-indexed universe = 759. Addressable **in-index (Tier 1) = 690**;
  out-of-index (Tier 2) = 1,243. Do Tier 1 first — it is what the site, scoring, and Pat surface.

## 3. What already exists (REUSE — do not rebuild)

- `ingest(symbols=[SYM], since=…, overwrite_screener=True)` already fetches a symbol's **entire**
  filing list (legacy `/corporates-financial-results` back to ~2018 + the Apr-2025
  `/integrated-filing-results` era), gates it, and writes — **gate-failing symbols are skipped before
  any overwrite**, so `overwrite_screener=True` is safe by construction.
- The **per-symbol continuity gate** (`_gate_symbol` / `_continuity_gate`) + cached verdicts in
  `fundamentals_xbrl_gate`.
- **Resumability**: `fundamentals_xbrl_seen` (url-keyed skip — a revised filing arrives at a new url,
  so it's restatement-safe) and the throttle **circuit-breaker** (aborts cleanly after 6 consecutive
  fetch failures; the seen-table resumes next run).
- The **restatement ledger** (`fundamentals_restatements`) and real-PIT `provenance.observe`.
- `reconcile()` for read-only XBRL-vs-Screener evidence.

## 4. The gate FAIL cohort — evidence for the tolerance floor (decision §10.2)

Of 22 symbols gated so far, 9 fail. Tagging each by the **magnitude of the failing value** (not the
symbol's peak) splits them cleanly:

| Symbol | Failing metric | XBRL vs Screener | |Δ| | Class |
|---|---|---|--:|---|
| VIKASECO | Net Profit (A) | 6.85 vs 7.0 (2.2%) | 0.15cr | rounding |
| AHLEAST | Net Profit (Q) | 4.83 vs 5.0 (3.4%) | 0.17cr | rounding |
| NUVOCO | Net Profit (Q) | 2.84 vs 3.0 (5.3%) | 0.16cr | rounding |
| UMIYA-MRO | Operating Profit (Q) | −0.27 vs −0.13 (108%) | 0.14cr | near-zero noise |
| EIMCOELECO | Net Profit (Q) | 7.55 vs 8.0 (5.7%) | 0.45cr | rounding |
| ANANDRATHI | Sales (A) | 724.3 vs 752 (3.7%) | 27.7cr | **definitional** |
| LTF | Revenue (Q) | 3806 vs 4098 (7.1%) | 292cr | **definitional** (NBFC) |
| HDFCBANK | Net Profit (Q) | 17826 vs 18627 (4.3%) | 801cr | **definitional** (MI/known) |
| ITC | Sales (Q) | 20350 vs 18790 (8.3%) | 1560cr | **definitional** (excise/known) |

**A ₹0.5cr absolute-tolerance floor recovers all 5 rounding fails and leaves exactly the 4 genuine
definitional breaks.** Screener rounds small-cap figures to whole crores, so the flat 2% relative gate
spuriously rejects tiny values (a ₹5cr line ±0.5cr rounding = 10% relative). This is a **correctness
fix**, not a loosening — it does not touch the ITC/HDFCBANK/LTF-class residue.

## 5. New pieces to build (the deltas)

1. **Backfill orchestrator** — the only substantial new code. A CLI subcommand
   `fundamentals_xbrl --backfill` (or a thin `scripts/fundamentals_backfill.py`) that walks the
   universe symbol-by-symbol with `overwrite_screener=True` and a wide `since`, **resumable via a new
   `fundamentals_xbrl_backfill_progress` ledger** (symbol → done/partial/throttled/last_period),
   bounded per run, honoring the existing circuit-breaker, Tier-1-first ordering.
2. **Gate tolerance floor** — add the ~₹0.5cr absolute band to `_continuity_gate`; then `--regate` the
   9-symbol fail cohort (recovers 5). Pin with a unit test using the values in §4.
3. **Per-symbol source boundary** — record each symbol's XBRL-earliest migrated period so consumers
   and audits know where the source switches (small table or column).
4. **Source-composition audit + coverage surface** — promote this audit into a repeatable report and
   wire source provenance into `src/web/coverage_view.py` (already renders fundamentals_history
   coverage) so the site shows what is primary vs legacy.
5. **Consumer swap + retirement** — repoint the residual live scrape in `score_batch.py` / `scoring.py`
   to read the archive (`capital_allocation.py` already does), then delete the network paths in BOTH
   `screener.py` and `fundamentals_history.py` (both are Screener scrapers).

## 6. Staged rollout

| Stage | What | Cost / risk |
|---|---|---|
| **3.0** | Read-only coverage audit → real migrate/freeze/fail counts | ✅ DONE, ₹0, no writes |
| **3.1** | Land the gate tolerance floor + full gate sweep of the 1,911 un-gated addressable symbols | network (gate evidence), no overwrites |
| **3.2** | **Pilot backfill** ~25–50 Tier-1 gate-pass symbols with `overwrite_screener=True`; reconcile + verify C-score and patearn CAGRs unchanged across the source boundary | writes, reversible; go/no-go gate |
| **3.3** | Universe backfill over bounded windows, Tier 1 → Tier 2 | writes, resumable |
| **3.4** | Consumer swap → delete live scrapers → close Guardrail #8 in migration doc + PROJECT_STATE | code + docs |

## 7. Operational safety

- **Dedicated job, NOT the nightly forward timer.** Must dodge the busy windows (UTC): bhavcopy chain
  ~14:01, pt14batch 15:30, fundamentals-xbrl 16:30, shareholding-xbrl 16:45, capital-allocation 17:18.
  A **morning-IST window** (NSE quiet, no Hermes timer) is ideal.
- **Volume:** ~40–50k paced instance fetches (37,914 period-instances + gate evidence, minus seen-skips)
  at 1.5s each. NSE throttles ~1.5k fetches/session → the circuit-breaker aborts and the seen-table
  resumes. Realistic convergence: **~1–2 weeks of bounded nightly windows**, or a focused multi-day
  push with backoff. Every restart is cheap.
- WAL + per-symbol commits already; the read-only website is unaffected throughout.
- **Never** run it concurrently with the 16:30 forward ingest or 17:18 capital-allocation (shared DB writer).

## 8. Honest limits (state up front)

- **Pre-2018 history stays Screener-sourced** — 116k rows / 1,356 symbols. No NSE results-XBRL reaches
  before the SEBI mandate; BSE's archive largely doesn't either for standardized results XBRL. The
  decision-relevant recent ~7 years become primary; the deep tail is legacy-**labeled**. "Delete
  `screener.py`" removes live *scraping*, not these already-banked rows.
- **Bank annuals stay Screener** — results-XBRL lacks the annual-report depreciation split (documented
  in `extract_bank_for`); bank `kind="A"` returns `{}` by design. Bank *quarterlies* migrate normally.
- **Definitional-break residue** (ITC excise / HDFCBANK MI / LTF NBFC-revenue / ANANDRATHI): stays on
  the frozen Screener series, labeled, until a definitional mapper — a separate, later effort.

## 9. Guardrail closure

After 3.4: new periods = XBRL (already true), 2018+ history = XBRL for gate-pass symbols, pre-2018 +
residue = labeled legacy, **no live Screener network path anywhere**. Guardrail #8's remediation line
moves from "in progress" to "closed"; the `screener.py` / `fundamentals_history.py` deletions land in
§ Key file paths.

## 10. Decisions for Ramana (recommendations inline)

1. **Pre-2018 tail** — keep frozen + labeled *(recommend)* / attempt BSE backfill / drop it.
2. **Gate tolerance floor** — add the ~₹0.5cr absolute band *(recommend — §4 shows it recovers 5/9
   fails and touches no real break)*.
3. **Definitional-break cohort** — leave labeled on Screener *(recommend)* / build definitional mappers now.
4. **Cadence** — bounded nightly windows *(recommend — safest on NSE)* / one dedicated multi-day push.

## 11. Recommended first build step

Land **3.1** (the tolerance floor + `--regate` the 9 fails to prove the §4 prediction, then the full
gate sweep). It's cheap, reversible, and produces the exact gate-pass cohort that 3.2/3.3 operate on.
