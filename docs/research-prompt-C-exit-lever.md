# Parallel research prompt — C: the exit lever (recover the give-back)

**Paste everything below into a fresh Claude Code session in `D:\Hermes`.**

---

You are running an isolated quant-research task in the Hermes repo. Read `docs/strategy-ledger.md`
first — it is the running record; you MUST append your results to it.

## The finding this task chases
The recorded factor tearsheet (`research/explosive_moves/factor_zoo.py`, `out/factor_zoo.csv`) shows the
top-25 **monthly rotation captures only ~18–22% of the average peak move** (Cap%), and even winners give
back ~43% of their high (WCap% ~55–58%). The cause is the **fixed month-end (close-to-close) exit** — it
sells at the rebalance regardless of where the move went intra-month. The MFE/MAE columns prove the upside
is real and large (RISKADJ avg MFE ≈ 14.6%, MAE ≈ −9.8% per position). **Question: can a light intra-month
exit recover that give-back WITHOUT the cost-fragility that killed the swing book?**

Important prior (don't re-walk it blindly): the standalone SWING book (S1–S4 in `strategies.py` /
`backtest.py`, see `backtest_report.txt` + `docs/explosive-move-NEXT-SESSION.md`) used stops/scale/trail
and **went net-negative at 1.5× cost** ("NO survivor net of costs"). So exits help capture but cost
turnover — the whole question is whether a *light* trail on the *rotation* (which is otherwise cost-robust)
nets out positive.

## Context / reusable pieces
- Benchmark to beat: **RISKADJ top-25 monthly = Sharpe 1.29, CAGR 35.4%, MaxDD −41.9%, capture ~22%**
  (plain month-end exit). That's the control.
- `factor_zoo.py` already reconstructs per-position intra-hold **MFE/MAE from `em_cache` `adj_high`/`adj_low`
  over `[i0+1 : i1+1]`** — reuse that path to simulate intra-month exits day by day.
- `strategies.py` has calibrated exit params worth reusing as priors: `init_stop_pct` (~0.18),
  chandelier trail `peak − atr_mult×ATR(entry)` (`atr_mult` 6→4 tighten), `scales` (sell half at +25%),
  `trail_after` 0.25. `calibrate.py` has the per-trade MFE/MAE quantile basis (winners dip to ~−13% p25 →
  stop must be WIDE, ~−18%, or you knife-out winners).

## Run environment (compute only — no Gemini/LLM)
- `ssh hermes`; venv `/opt/hermes/.venv-research/bin/python`; tree `/opt/hermes/research`; data in
  `/opt/hermes/data/`. Write a NEW module `research/explosive_moves/exit_lever.py`, `scp` it to
  `/opt/hermes/research/explosive_moves/`, run `cd /opt/hermes/research && /opt/hermes/.venv-research/bin/python -m explosive_moves.exit_lever` (use `run_in_background: true`, ~5–8 min).

## The task
1. On the RISKADJ top-25 monthly book, add an **intra-month exit overlay**, simulated on daily
   `adj_high`/`adj_low` within each holding window (enter at d0 close, walk to the next rebalance):
   - (a) a **wide chandelier trail** that only activates after the move matures (`trail_after`≈+25%,
     `atr_mult`≈6, tighten to 4 after a big run); (b) a **scale-out** (sell half at +25%, trail the rest);
     (c) a hard **−18% stop**. Re-enter cash into the next rebalance's picks.
2. Charge **realistic incremental cost** on the extra exits (per-tier spread + 0.5×ATR slippage — see the
   B-task `COST_TIERS` basis); the whole point is net-of-cost.
3. Sweep the trail multiplier and the profit-scale level. Report, vs the plain month-end control:
   capture% (should rise), Sharpe, CAGR, MaxDD, turnover, and net effect.
4. Walk-forward both halves; no look-ahead (exits use only that day's high/low, decided at/after entry).

## Deliverable + discipline
- Save `out/exit_lever.csv`; append an **"Exit lever (C)"** subsection to `docs/strategy-ledger.md` with
  the sweep table and the honest verdict: does a light trail beat plain monthly selling net of cost, or
  does turnover eat it (replicating the swing-book lesson at the rotation level)?
- Work ONLY in your new `exit_lever.py` + ledger + `out/`. Do NOT edit `factory.py`, `factor_zoo.py`,
  `PROJECT_STATE.md`, or `src/web/*` (parallel-owned). Commit only your own new files if asked.
