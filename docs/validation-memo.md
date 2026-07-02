# Model Validation Memo — momentum selection lens + data layer

**Scope:** the risk-adjusted momentum scanner (`/dash/momentum-scan`, `momentum_scan.py`), the
equal-weight ensemble (MOM12 + HI52 + RISKADJ + LOWVOL_MOM, 0.25 each — see
`docs/calculations-and-weights.md` §2), and the C/A/B veto data layer.
**Style:** SR 11-7 (development evidence → independent checks → limits → ongoing monitoring).
**Status:** the panel's gap #6 deliverable (see `docs/institutional-panel-assessment.md`).
**Date:** 2026-07-02. Owner: Hermes autonomous sessions; approver: Ramana.

---

## 1. What the model claims — and what it deliberately does NOT claim

The scanner is a **gross cross-sectional selection lens**: it ranks the liquid NSE universe so a
human researches the top slice. It is NOT an execution signal, NOT a net-of-cost buy basket, and
NOT proprietary alpha:

- **Attribution PROOF (binding):** RISKADJ residual alpha after factor attribution is +7.3%/yr
  with **t = 1.99 — below the t ≥ 3 evidentiary bar**; the WML momentum factor absorbs ~51% of
  gross return. The engine is **momentum beta, not selection skill** (`attribution.py`,
  `docs/predictive-attributes-findings.md`).
- **Cost reality (binding):** the flat-cost Sharpe 1.29 collapses to ≈ 0.09 under realistic
  participation-based costs; nothing in the zoo beats Nifty-500 buy-and-hold net
  (`cost_realism.py`, `cost_participation.py`). Fundable expression is only a **defensive
  ₹50–100 cr tilt**.
- **Deflated statistics:** DSR 0.966 / PBO 0.34 on the momentum family — a real but
  un-proprietary premium. No claim of edge beyond documented factor exposure.

## 2. Development evidence (what was independently re-derived vs. taken on faith)

| Check | Verdict | Artifact |
|---|---|---|
| Anchor/split-adjustment leak in ratio factors | **Disproven** — ratio/return factors are anchor-invariant | `anchor_audit.py` |
| Look-ahead in fundamentals PIT | Real BSE filing dates via `provenance_knowable`; modelled lag only as calibrated fallback (never earlier than producer lag) | `fundamentals_filing_dates.py`, `provenance.py` |
| Regime filter 1-bar leak | Fixed (SMA uses prior close, CL-RES-03) | `embase.market_regime` |
| Survivorship | Universe from bhav-copy actual trading rows (delisted names present historically; names not trading on the latest session are dropped from TODAY's scan only) | `momentum_scan.build` |
| Corporate actions | Value-based (₹, not share count) per Guardrail #5; CA-adjusted closes from factors table | `embase.py` |
| Known failure models | **BOOK_YIELD is a hard reject** (β 1.54, MaxDD −82%, negative α, fails both halves). Standalone value/quality are not rankers. | `docs/strategy-ledger.md` |

**Independent replication protocol** (to re-run after any factor change): recompute factor
Sharpes from raw bhav copy on a clean venv (`factor_zoo.py`), reconcile against the strategy
ledger benchmarks (RISKADJ internal benchmark Sharpe 1.13), then re-run `attribution.py`; a
change is accepted only if the residual-α t-stat conclusion is unchanged or improved.

## 3. Data lineage

```
NSE bhav copy (primary, as-traded)  ->  bhavcopy_rows (hermes.db)
                                        -> em_cache.pkl (features; self-heals when stale)
                                        -> momentum_scan (table + /dash surface)
NSE XBRL results (primary, PIT)     ->  fundamentals_history (research.db, source column)
BSE announcements (primary)         ->  provenance_knowable (real filing dates)
NSE corporates APIs (primary)       ->  insider_events (A) / credit_rating_events (B)
Screener.in (LEGACY, being retired) ->  fundamentals_history rows with source IS NULL
```
Per-row `source` discrimination is mandatory (panel red line); XBRL rows only append for
symbols passing the series-continuity gate (`fundamentals_xbrl_gate`).

## 4. Limits (hard)

| Limit | Value | Rationale |
|---|---|---|
| Mandate | Selection lens only; any live money expression capped at defensive ₹50–100 cr | cost_participation capacity |
| Portfolio beta | ≤ 1.3 | momentum = beta; cap the beta it is |
| Single sector | ≤ 25% of the shortlist | concentration in momentum crashes |
| Universe | Equity-only allowlist (D42), relative liquidity gate ≥ 60th pctile turnover | ETF/low-vol artifacts |
| C/A/B role | **Veto only, never rankers** (D66) | failed as standalone rankers |

## 5. Kill-switches (ongoing monitoring; check nightly, act same-day)

1. **Momentum-crash guard:** Nifty-50 < 200DMA (regime OFF) **and** trailing-21d WML proxy
   drawdown > 15% → suspend the shortlist surface (banner, not silent).
2. **Data-freshness:** `MAX(bhavcopy_rows.trade_date)` older than 2 trading days, or
   `momentum_scan.as_of` ≠ latest trade date → scan is stale; surface shows the as-of date
   prominently (already data-first) and ops alert fires.
3. **Live-IC decay:** rolling 6-mo rank-IC of ensemble_pctile vs forward 1-mo returns < 0 for
   3 consecutive months → freeze weights, rerun attribution before any change.
4. **Restatement spike:** > 5% of gate-passed symbols receiving revised XBRL filings in a month
   → pause XBRL auto-ingest, re-run reconciliation cohort.
5. **Universe drift:** scan-eligible count moving ± 20% month-over-month → investigate the
   liquidity gate / equity list before trusting the ranks.
6. **Beta/sector breach:** any shortlist snapshot violating §4 limits renders the breach on the
   surface itself (data-first: show, don't hide).

Enforcement wiring for #1/#3/#4/#5 into the nightly data-quality timer is the open follow-up;
#2 and #6 are live by construction (as-of shown on the surface; scan self-heals its cache).

## 6. Change control

Weights and formulas are machine-owned constants cited in `docs/calculations-and-weights.md`
(single source). Any change: code constant + that one doc entry + re-run of §2's replication
protocol, in the same commit. Failures recorded in `docs/strategy-ledger.md` are **blocking**:
cite the recorded numbers before any re-attempt.
