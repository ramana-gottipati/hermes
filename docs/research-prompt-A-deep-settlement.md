# Handoff spec — A: wire deep settlement (credibility's frozen fuel)

**For the CCI session that owns `src/automation/concall_settle.py`.** This is the Phase-1b TODO. It is
the single highest-leverage cheap unblock for the credibility strategy. ~1 day. Coordinate — that file is
actively edited; do not clobber a parallel copy.

## The problem (verified 2026-06-24)
Settlement runs daily (`hermes-concalls.timer`) but resolves **0 new promises**
(`concall_settle: AUROPHARMA {'settled':0,...,'ongoing':22}`). Cause: `concall_settle.py` only grades a
promise **if its resolving quarter exists in `concall_results`** — a shallow table (599 rows / 47 symbols /
Dec-2023+). So credibility's track record is **frozen**: only 324 promises ever resolved, across 31 symbols.
The falsification gate (`research/explosive_moves/credibility_falsify.py`) is therefore stuck at N≈21 and
inconclusive (Spearman ≈ 0). Growing the *resolved* set is the prerequisite to testing the signal at all.

## The fix
Add a **`fundamentals_history` fallback** to settlement: when `concall_results` has no row for a promise's
resolving `(fy, quarter)`, grade it against the deep 24-yr archive instead.

- **Reuse the PIT reader** `src/automation/fundamentals_asof.py` (`load_symbol_history`, the latest-known
  helpers, the `_SALES=("Sales","Revenue")` / `_OPM=("OPM %","Financing Margin %")` metric fallbacks).
  `research.db.fundamentals_history` has `(symbol, period_type 'A'/'Q', period_end, report_date, metric, value)`.
- **Map** the promise's resolving period (already computed by `_resolve()` from source period + horizon) to:
  - **revenue** → `Sales` for that period (annual for `fy`-horizon promises; quarterly where the Q archive
    has it — note quarterly depth is thin pre-FY2023, so `fy`-horizon promises are the main unlock);
  - **margin** → `OPM %` for that period.
- **Grade exactly as today** (keep the logic identical so scores stay comparable): level bands for hard
  numeric targets (`MET_TOL 0.97 / MISS_TOL 0.90` revenue; pp bands for margin), **YoY sign-match** for
  directional claims, and the **implied-growth floor** (`_implied_growth_pct`: "double-digit" ⇒ ≥10%, etc.)
  so a vague-but-undershot promise grades MISSED.
- **NO look-ahead — this is the binding contract:** settle a promise only once the resolving period's
  actual was actually **filed**, i.e. `report_date <= today`. Use `report_date`, NOT `period_end`. A FY26
  promise stays ONGOING until the FY26 annual is filed (~Jun 2026). This is non-negotiable — the whole value
  of the dataset is that it is point-in-time honest.
- Keep capex/expansion/volume/debt (not in the P&L) as ONGOING (unchanged). Stay idempotent. Preserve the
  D59 ordering: run AFTER extract, BEFORE `concall_scores --rerank`.

## Deploy + verify
- Deploy per `docs` VPS reality: `scp src/automation/concall_settle.py hermes:/opt/hermes/src/automation/`
  (LF endings), then run `python -m src.automation.concall_settle --all` and `concall_scores --rerank`.
- Success = `concall_guidance` status counts move materially off OPEN (target: thousands resolved, not 324),
  and `concall_scores` gains rows across more symbols/periods.

## Then ping the Opus/research session
Once resolved promises grow, the research side **re-runs `credibility_falsify.py` at the higher N** (the
gate is committed and ready) and records the verdict in `docs/strategy-ledger.md`. If Spearman is still ≈ 0
at the improved depth → credibility isn't even a veto worth scaling, stop. If the promise-breaker signal
firms up → breadth (wider transcript fetch) becomes justified — as a drawdown overlay, not alpha.
