# Options-Implied Signals — Scoped Effort

> **🛑 STATUS 2026-07-23 — PHASE 0/1.5/1.6 RAN → STOPPED. The OI-positioning half is PRICED.** PCR was the
> only OI signal to select (δ +0.06, Phase 0), but it is NOT a fundable book: monthly net R/V 0.28
> (turnover 815%/yr), and SLOWING it made it worse (0.11–0.20) — its signal decays fast (Phase 1.5/1.6,
> ledger "Study 2026-07-23 — OPTIONS-IMPLIED PHASE 0"). **Phase 1 (the IV/skew build) is NOT justified on
> current evidence** (2yr window + base rate: crossover/regime/flow/OI-positioning = 3+ signals, 0 fundable).
> Phases 1 (IV back-compute) + 0.5 (pre-2024 backfill) below remain a VALID design for a FUTURE dedicated
> effort ONLY if explicitly prioritized — IV is a distinct (slower) signal that this OI-positioning result
> does not strictly condemn, but it is a 2-3-session bet against a discouraging base rate. Do not auto-start.
>
> **Lifecycle: SCOPE — PARKED (2026-07-23).** A dedicated, phased plan to test the options-implied dimension.
> Grounded in *verified* data reality, NOT greenfield. Retire/delete only when a future session decides IV is
> or isn't worth building; the Phase-0/1.5/1.6 results are folded into `docs/strategy-ledger.md`.

## Why this exists
The fundable product is the standalone low-vol book. Every other orthogonal signal tested (regime, all 3
forms of institutional flow) is real-but-not-tradeable or a risk tool, not a return tool. Options-implied
(IV / skew / PCR / max-pain / positioning) is the one remaining orthogonal axis and is *structurally* the
most forward-looking. This scopes it honestly before any multi-day commitment.

## Data reality — VERIFIED on the box (2026-07-23)
**Already ingested (testable NOW, no new fetch):**
- `fno_oi_signals` (hermes.db, 104,817 rows, **2024-07-01 → 2026-07-24, 273 F&O symbols**): per-stock daily
  **PCR, max_pain, call_oi/put_oi, fut_oi + change, basis_pct, sup/res strike, quadrant**. Built by
  `src/automation/fno_oi.py` from the NSE UDiFF F&O bhavcopy.
- `participant_oi` (hermes.db, 2,508 rows): FII/DII/Pro/Client long-short in index & stock futures & options.

**Net-new (needs building):** **implied volatility / IV-rank / IV-skew / IV term-structure** — the
forward-looking vol signals. NOT computed. Back-computable (Black-Scholes) from the per-strike settlement +
OI in the SAME UDiFF F&O bhav `fno_oi.py` already fetches (URL verified:
`nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip`, date = `YYYYMMDD`).
`fno_oi.py` deferred the per-strike parse; that parser is the core new code.

## ⚠ THE HARD LIMIT — state it up front
History is **~2 years only** (the UDiFF F&O format began 2024-07). Both the existing OI signals AND any IV
build inherit this. **2 years ≈ very low statistical power** — even a positive result is low-confidence and
must be labelled so; it can never be a fundable book off the backtest, only a forward-test candidate.
Extending pre-2024 requires the OLD-format F&O archive + a second parser (Phase 0.5, optional). This limit
is the single biggest reason to probe cheaply before committing the multi-day IV build.

## Phases (go/no-go between each)
- **Phase 0 — hours, data on box, DO FIRST.** Event-study gate on the EXISTING OI signals: PCR extremes,
  max-pain proximity, futures OI-buildup (fut_oi_chg × price sign), basis — vs forward returns (5/22/63d),
  excess vs Nifty-500, Cliff's δ vs same-stock placebo, both halves. FREE. **GATE:** any signal selects
  (δ ≥ +0.05, both halves)? → proceed. None? → the OI dimension is priced; record the cheap negative, stop.
- **Phase 1 — multi-day, ONLY if warranted.** Per-strike UDiFF parser → Black-Scholes IV per stock/expiry →
  `iv_signals` table (IV-rank percentile, 25Δ skew put−call, term-structure slope) + nightly timer + 2yr
  backfill (reuse the `fno_oi.py` fetch + archive pattern; runs AFTER cash bhav, AUD-95-safe timer).
- **Phase 2 — event-study gates on the IV signals;** if any selects net of cost → pre-register a book study.
- **Phase 0.5 — optional:** old-format F&O backfill to extend history pre-2024 (a second parser; raises power).

## Honest priors (failure-ledger contract, stated before the run)
- OI/PCR/max-pain are **widely-watched retail signals → likely PRICED.** Phase-0 prior = FAIL-null (but it
  is cheap to confirm — that is the point).
- IV/skew (Phase 1) is the **better shot at forward-looking alpha**, but: F&O-universe only (~273 names), IV
  back-computation is fiddly (American-style stock options — settlement + BS is an approximation), and
  IV/skew are semi-watched. Prior: uncertain, ≤ the (weak, unstable) flow signal.
- **The 2-year window caps confidence regardless of result.**

## Effort + disposition
Phase 0 ≈ half a session. Phase 1 ≈ 2–3 focused sessions (parser + IV + tables + nightly + gates). Commit to
Phase 1 ONLY if Phase 0 shows life or the effort is explicitly prioritized. Numbers single-source into
`docs/strategy-ledger.md`; any candidate requires a forward test, never deployment off a 2-year backtest.
