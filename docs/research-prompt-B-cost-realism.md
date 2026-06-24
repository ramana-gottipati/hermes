# Parallel research prompt — B: cost-honest momentum engine

**Paste everything below into a fresh Claude Code session in `D:\Hermes`.**

---

You are running an isolated quant-research task in the Hermes repo. Read `docs/strategy-ledger.md`
first — it is the running record of all strategy work; you MUST append your results to it.

## Context you need
- A momentum factor backtest already exists and is RECORDED: `research/explosive_moves/factor_zoo.py`
  ranks the liquid NSE universe monthly, holds top-25 equal-weight, value-relative liquidity gate
  (top-40% by turnover), walk-forward 2012-18 & 2019-26, no look-ahead. Its tearsheet (Sharpe, Sortino,
  MaxDD, win%, profit factor, MFE/MAE/capture, beta, alpha) is in `out/factor_zoo.csv` and the ledger's
  "Known / public factor strategies" table. Headline benchmark: **RISKADJ (6-mo return ÷ 3-mo vol) =
  Sharpe 1.29, CAGR 35.4%, MaxDD −41.9%, beta 1.18, +16.4% alpha vs Nifty 500.**
- **The credibility gap this task closes:** that 1.29 is net of a NAIVE cost model only —
  `COST_PS = 0.003` flat per unit of turnover (in `factory.py`), with NO market-impact, NO slippage,
  NO capacity constraint. An institutional allocator discounts it on sight. Your job is to find the
  **defensible Sharpe after realistic frictions.**
- Reusable pieces already in the repo:
  - `research/explosive_moves/strategies.py` → `COST_TIERS` (per-liquidity-tier round-trip spreads:
    T1 ₹1–5cr 1.5%, T2 5–25cr 0.6%, T3 25cr+ 0.25%; plus `fees_ps`). Use these, don't invent.
  - `research/explosive_moves/backtest.py` + `calibrate.py` — the SWING book's fill-level cost model
    already adds slippage = ~0.5×ATR% at entry; copy that basis.
  - `em_cache.pkl` per-symbol arrays include `med_turn` (₹ turnover), `feats["atr14_pct"]`, OHLC.

## Run environment (all heavy compute on the VPS — no Gemini/LLM needed here)
- `ssh hermes` (key auth works). Research tree: `/opt/hermes/research`. Venv:
  `/opt/hermes/.venv-research/bin/python`. Data: `/opt/hermes/data/{em_cache.pkl,research.db,hermes.db}`.
- Pattern: write a NEW module `research/explosive_moves/cost_realism.py` locally → `scp` it to
  `/opt/hermes/research/explosive_moves/` → run `cd /opt/hermes/research && /opt/hermes/.venv-research/bin/python -m explosive_moves.cost_realism`.
  Reads are LF-clean; runs take ~5–8 min (the build), so use `run_in_background: true`.

## The task
1. Replace the flat `COST_PS` with a **realistic per-trade cost**, applied to each rebalance's turnover:
   - per-name **half-spread by liquidity tier** (from `COST_TIERS`, keyed on the name's trailing-22d
     median turnover), **plus slippage = 0.5 × ATR%(entry)**, plus `fees_ps`.
   - a **capacity rule expressed as a percentage, NOT a rupee floor** (the founder rejects static ₹
     thresholds): cap each position at **≤ 10% of the name's 22-day median traded value**; if the target
     equal weight exceeds that for a given AUM, down-weight/redistribute or drop the name, and report the
     **max deployable AUM** before impact bites (the `backtest_report.txt` capacity section did this).
2. Re-run RISKADJ, QUAL_MOM, LOWVOL_MOM under realistic costs; report the full tearsheet vs the flat-cost
   benchmark. Headline question: **how much of the 1.29 Sharpe survives, and at what AUM?**
3. Test **turnover reduction** as a cost lever: a no-trade buffer / hold-band (only swap a name out of
   top-25 if it drops below, say, rank 35), and/or 2-monthly rebalance. Does lower turnover recover Sharpe?
4. Keep walk-forward (both halves must stay positive) and no look-ahead.

## Deliverable + discipline
- Save `out/cost_realism.csv`; append a **"Cost realism (B)"** subsection to `docs/strategy-ledger.md`
  with the before/after table and the honest verdict (defensible Sharpe + capacity ceiling).
- Work ONLY in your new `cost_realism.py` module + the ledger + `out/`. Do NOT edit `factory.py`,
  `factor_zoo.py`, `PROJECT_STATE.md`, or any `src/web/*` file (parallel sessions own those).
- Commit only your own new files if asked; otherwise leave in the working tree.
