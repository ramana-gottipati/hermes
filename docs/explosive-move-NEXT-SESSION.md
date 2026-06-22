# Explosive-Move Strategy Program — SESSION-TAKEOVER KICKSTART

> **Created:** 2026-06-21 (end of session 25/26). **TRANSIENT** run-book — the durable record is
> `docs/explosive-move-research.md`; this file is the "where we are + what to do next" boot sheet.
> **Retire when:** the backtest is built, S1–S4 are run, and survivors are folded into PROJECT_STATE.

---

## 0. BOOT ORDER (read these first, in order)
1. This file (state + next steps).
2. `docs/explosive-move-research.md` — the full research log + every finding + the pattern library + the 4 strategies + the backtest plan (the rich source of truth).
3. Memory note `explosive-move-research.md` (one-screen summary).
4. The CSVs in `research/explosive_moves/out/` and the workflow transcripts (see §12).

**The data lives on the VPS, not locally.** Local `D:\Hermes\data\hermes.db` is a 2.5 MB dev stub. Real data = VPS `/opt/hermes/data/hermes.db` (13 GB) + `/opt/hermes/data/research.db`.

---

## 1. WHAT THIS PROGRAM IS
Ramana asked (no given strategy): **discover, from the data alone, what precedes explosive equity moves, then build tradeable strategies.** A +10% move is the RESULT, not a trigger — we hunt the pre-move data fingerprint, then turn the signals into strategies with entry/stop/target/trail/exit, then backtest. Bottom-up, survivorship-safe, out-of-sample, unbiased.

## 1b. THE ESSENCE (the soul — read before the mechanics)
The point of this program, and why it matters: we let the DATA name what precedes explosive moves
instead of applying a known strategy — and the headline result is a genuine REVERSAL of belief.
**The house DVPT thesis (high delivery = quiet accumulation = imminent move) is WRONG as a trigger.**
The data shows delivery DRIES UP before moves; moves are preceded by **momentum + volatility + churn**,
and the named bulk-buyers are mostly HFT churn. Delivery only governs whether a move SUSTAINS, not
whether it starts. This was earned the hard way — by refuting our own best ideas on data (every
"stealth smart-money footprint" hypothesis failed) and by catching + fixing our own artifacts. **That
intellectual honesty IS the method.** The tradeable essence: a few clean validated SIGNALS (the
Launchpad — momentum with CONTRACTING volatility) with an asymmetric payoff (winners run +40–100% and
barely dip; ~70–80% OOS hit), now shaped into 4 risk-distinct strategies — but **nothing is a strategy
until it survives realistic costs out-of-sample** (S4's gates decide that).

**Ramana's working principles (honour these — they are the project's DNA):**
1. The +10% move is the RESULT, never the trigger — always hunt the PRE-move data.
2. Don't lean on the given (DVPT) strategy — let the data find its own, then compare.
3. Be UNBIASED — try different things, fail, come back; review the data with no bias.
4. "Genuine buying = the close holds" — sustain is closing strength, not an intraday spike.
5. Record EVERY observation carefully; lose no detail.
6. A strong hand must leave a footprint — chase the NAMED buyers (bulk/block, FII/DII), not just price.
7. Capture the move AND ride it to a data-defined exit — entry + stop + target + a trailing-stop that
   ratchets UP; maximise both the hit ratio and the risk:reward.

## 2. WHERE WE ARE NOW
- **Phases DONE:** event detection → precursor mining → clustering → OOS validation → multi-analyst
  pressure → named-flow feed wired → strategy design → **BACKTEST ENGINE BUILT + S1–S4 RUN (session 26).**
- **🔴 BACKTEST VERDICT (session 26): NO net-of-cost survivor.** The Launchpad has real, OOS- & jitter-robust
  POSITIVE per-trade expectancy net of costs (S1 +2.07%, PF 1.31), BUT as a portfolio all four trail a
  buy-hold Nifty risk-adjusted (S1 Calmar 0.14 / Sharpe 0.42 vs Nifty 0.28 / 0.73), the edge is ~zero-alpha
  β≈0.4 and concentrated in 2020–2026 (S2/S3/S4 flat-to-negative in the 2012–19 walk-forward). **S4 skeptic
  gates FAILED** (cost-delta dies by 1.5×; alpha-vs-beta negative both ways). **S3 fails decorrelation**
  (corr +0.47–0.52 > 0.4). Full evidence + tables in `docs/explosive-move-research.md` § "Tradeable backtest".
- **Engine:** `research/explosive_moves/{embase,strategies,backtest,metrics,calibrate,gridsearch,run_backtests}.py`
  (deployed to VPS, NOT committed). Reproduce: build cache `-m explosive_moves.embase`, then
  `-m explosive_moves.run_backtests` (~25s). Outputs `out/backtest_report.txt` + `backtest_results.json`.
- **Nothing is committed to git** (ask before committing). No production code changed except the deals feed.

## 3. INFRA & HOW TO RUN (critical — don't trip on these)
- **SSH:** `ssh hermes` (Mumbai VPS, root). **The link is FLAKY** — wrap every remote call in a retry loop, and for long jobs `nohup` on the VPS + poll the log (or a remote `until kill -0 $pid; do sleep 3; done` wait loop), don't stream stdout. Write results to a remote file then `scp` it.
- **TWO venvs (do not confuse):**
  - `/opt/hermes/.venv` = PRODUCTION (stdlib + requests + telegram + fastapi; **NO numpy/pandas**). Used by the bot, bhavcopy, and `src/automation/deals.py`.
  - `/opt/hermes/.venv-research` = RESEARCH (numpy/pandas/scipy/sklearn). Used by everything in `research/explosive_moves/`.
- **Run research modules:** `cd /opt/hermes/research && /opt/hermes/.venv-research/bin/python -m explosive_moves.<module>`
- **Deploy:** edit locally in `D:\Hermes\research\explosive_moves\` (or `src/automation/`), then `scp -q /d/Hermes/research/explosive_moves/*.py hermes:/opt/hermes/research/explosive_moves/`.
- **DBs:** read production `hermes.db` **read-only** (`file:...?mode=ro`); write intermediate to `research.db`. `common.py` handles both.

## 4. DATA INVENTORY
- **`bhavcopy_rows`** (hermes.db): NSE EQ daily 2004→2026, 9.3M rows, 5,749 symbols (incl. delisted → survivorship-safe). Cols incl. OHLC, prev_close, avg_price (VWAP, 2020+), volume, value(₹ turnover), num_trades, deliv_qty, deliv_per.
- **`research.db` tables:** `events_daily/weekly/monthly` (detected events + forward outcomes); `features` (etype∈{daily,weekly,monthly,baseline}, ~90 precursor cols as-of launch + outcomes mfe_6m/mae_6m/ret_*/big50_6m/sustained); `uni_*`, `rules_*`, `oos_*` (mining/validation), `sensitivity_monthly`, `clusters_monthly`, `feat_meta` (baseline_k=10).
- **`hermes.db` NEW tables (deals feed):** `bulk_block_deals` (trade_date, symbol, deal_type, **client_name**, side, qty, price), `fii_dii_flows`. Fed daily by `hermes-deals.timer` (Mon-Fri 14:30 UTC).
- **Key facts:** monthly events 69,746 (37,343 sustained=53.5%); base rate of a sustained +10% month ≈ 11%. Per-event forward path (MFE/MAE/returns) precomputed.
- **Outputs:** `research/explosive_moves/out/*.csv` (univariate/rules/oos/sensitivity/clusters/results_table). Mirrored locally.

## 5. KEY FINDINGS (don't re-derive — these are established + OOS-validated)
1. **Counter-DVPT (headline):** delivery-% DROPS before moves (churn/rotation, delivered qty rises but volume+trades rise faster). Delivery is a SUSTAIN/quality signal, NOT a trigger. Overturns the house DVPT premise.
2. **No stealth-accumulation footprint** in EOD data — the analyst panel's smart-money-footprint ideas (close-location/VWAP, ticket dispersion, fragmentation, deliv-per-trade) were ALL refuted on data. Moves = momentum + volatility + churn (a crowd/momentum phenomenon).
3. **The Launchpad** (the engine): **momentum-continuation** (`ret_22d>7% AND vol_ratio_22_66≤1.48 AND range_tight_22>0.096`, OOS hit 75–80%, lift ~6.7×) and **coiled-momentum** (`vol_22/vol_66<1 AND ret_22d≥10%`, hit 70%, lift 6.3× — best risk-adjusted). Holds every year + both walk-forward directions + strengthens with liquidity.
4. **Sustain = strength/control:** a +10% month holds (OOS 85%) when launched from a calm/tight, non-falling, near-52w-high, closing-strong base.
5. **Refuted TA lore:** "coiled-spring / tight-base + volume dry-up" precedes FEWER moves (lift 0.35). No squeeze precedes moves; volatility is ELEVATED.
6. **MFE/MAE per-trade quantiles (for stop/target sizing — the corrected basis):**
   - M1/coiled WINNERS barely dip: median worst-dip −2.5%, p25 ~−8% → **stop ~−10 to −12%** clears ~85–90% of winners (NOT the −6.3% cohort mean). MFE fat tail: median winner +37–40%, p90 **+100%+** → trail, don't cap.
   - M2 pullback is riskier: winner median dip −4.9%, all-trade p25 −24.6% → wider ~−15% stop → worse R:R.
7. **Trade-offs:** liquid (₹25cr+) = reliable+smaller (hit 86–97%); small-cap = bigger MFE but bigger MAE + cost/capacity problems. Prior momentum is the #1 sustain driver; oversold bounces are worst (sustain + drawdown).

## 6. THE 4 CANDIDATE STRATEGIES (full specs in `docs/explosive-move-research.md`; summary here)
- **S1 — Coiled-Launchpad Core** (momentum, vol-targeted, ₹5cr+): entry `ret_22d≥7.5% AND vol_ratio_22_66≤1.48 AND range_tight_22>0.096 AND close≥SMA50≥SMA200` (+ coiled overlay `vol_22/vol_66<1` swept); single entry, NO pyramiding; stop chandelier 2.5×ATR/~−12% floor; scale ⅓ at +12%, trail (Highest−3×ATR, tighten 2×ATR after +25%, breakeven at +10%); time-cut 66d if not +10% by d22; vol-target 0.5% risk; **mandatory regime gate** (Nifty>200DMA + breadth). The return engine.
- **S2 — Heat-Capped Large-Cap Launchpad** (same signal, ₹25cr+, fixed-fractional 0.5% heat, −10% stop, equity circuit-breaker, scale +2R then trail). Best Sharpe/MAR + capacity; deployable base.
- **S3 — Shakeout-in-Volatility Reversion** (the ONLY mean-reversion / diversifier): SHALLOW 1-day shakeout `ret_1d≤−2.2% AND ret_22d≤7% AND vol_66>2.4%` + falling-knife guards `dist_high_22≥−12% AND close≥SMA200`; **avoid the deep −3.1% sibling** (MAE −15.4%); sell half +10%, runner ~0.5×MFE; gap-down kill; INVERTED regime gate (wants choppy-healthy). Earns its place by decorrelation.
- **S4 — Skeptic's Cost-Stressed Coiled-Momentum** (₹25cr+, tiny): its job is the **acceptance gates** — cost-delta, alpha-vs-beta (survive regime gate OFF?), threshold-jitter (do 1.477/0.0962 cliff under ±10%?), capacity-ceiling. Deliverable = negative information (how much edge survives costs).

## 7. BACKTEST PLAN + ACCEPTANCE GATES
- **Costs (decisive, charged twice):** tier spreads ₹1-5cr ~1.5% / ₹5-25cr ~0.6% / ₹25cr+ ~0.25%, + brokerage/STT/GST/stamp + 0.5×ATR slippage; **S3 falling-bar fills** (next-open, not limit-at-close — adverse selection); √-impact for capacity. **Accept only NET of costs.**
- **Walk-forward:** bidirectional frozen (2012-19 ↔ 2020-26) + purge/embargo gap. Accept only if positive in BOTH directions AND every calendar year (incl. 2018, Feb-Apr 2020).
- **Metrics:** Calmar/MAR (primary), Sharpe/Sortino, profit factor, **expectancy-in-R from a fill-level sim (NOT arithmetic on MFE/MAE means)**, realized hit (~55–65%, not the 80% precursor), MFE-capture efficiency, per-year P&L, cross-strategy 60d correlation (S3 must stay <+0.4 to momentum books).
- **Baselines:** buy-hold Nifty + Nifty Smallcap; a naive "M1-all-tiers" book (S1/S2/S4 must beat it on Sharpe AND MaxDD); **alpha-vs-beta = run with regime gate OFF** (if edge vanishes it's beta → reject).
- **Acceptance:** FLAT PLATEAU (pick plateau centre, reject if Calmar drops >15% on a one-notch param move); threshold-jitter ±10%; S4's four gates applied program-wide.

## 8. CRITICAL GOTCHAS / NON-NEGOTIABLES
- **Stops must use per-trade MAE QUANTILES, not the cohort means in the oos_*.csv** (those are averages; recompute winners' deep percentiles per strategy — §9 step 1).
- **MFE ≠ capturable return** — it's the peak; a trail captures a fraction → must use a fill-level sim for realized R.
- **Named-buyer / FII-DII overlays are NOT backtestable** (NSE bot-walls history; accrues only from 2026-06-19) → EXCLUDE from accept/reject; carry as forward-only logged paper A/B (confirmed vs unconfirmed) at 1.0× size.
- **Tree-cut thresholds (1.477, 0.0962, −0.02186) smell overfit** → jitter ±10%; sweep, pick plateau centre.
- **No look-ahead:** features strictly as-of close day s; enter s+1. **Survivorship:** universe from the raw archive daily (never a current-membership list). **CA rows excluded** around entry.
- **The corpus over-represents momentum** (events are +10% UP moves — partly tautological) → live lift WILL fade; the regime/cost/plateau gates exist to catch it. Stay honest.
- **F&O OI:** Ramana decided to SKIP F&O (covers only ~190 large-caps; most explosive movers are small-caps with no F&O). The F&O-OI bhav URL was never located anyway. Do not pursue unless asked.

## 9. STEP-BY-STEP NEXT PLAN
**Steps 1–6 DONE (session 26).** Stops calibrated (winners dip to −13% p25, not −2.5% → stop −18%); engine
built; gates + walk-forward run; **selection result = NO survivor net of costs** (see §2 + research doc).
What remains:
1. **DECIDE with Ramana (do not assume):** given the negative verdict, (a) productionize the Launchpad as a
   daily **SCREEN/watchlist** (not a mechanical book) on `/dash`, AND/OR (b) pursue the edge in the layers
   the EOD tape can't carry. The mechanical-strategy path is a dead end at the index-fund bar.
2. **Forward-paper the named-buyer overlay** (deals feed accruing since 2026-06-19; `launchpad_scan.py` does
   the live ⭐ cross-check). This is the first real test of whether "who is buying" adds the alpha the price
   tape lacks. Log confirmed-vs-unconfirmed at 1.0× size; revisit after enough samples.
3. **Qualitative layer** (the real frontier, §10): concall-tone / guidance / announcement-direction ingestion
   → the forward trigger fundamentals can't give. Build after the named-flow A/B has data.
4. **PROJECT_STATE.md** — add the `research/explosive_moves/` backtest package + the verdict (PENDING; ask
   before committing; verify the working tree isn't held by a parallel session first).
5. Optional: a smoother early-harvest exit variant for *tactical* use (higher hit, lower DD) — does not beat
   the index, so only if Ramana wants a discretionary aid.

## 10. OPEN ITEMS / PENDING
- **PROJECT_STATE.md update PENDING** (a parallel session was holding it): add `research/explosive_moves/` package, `deals.py` + `client_classify.py`, the `bulk_block_deals`/`fii_dii_flows` tables, `hermes-deals.timer`, and Decision-log entries (D56 already added) + the 4 strategies. Do this when the file is free (verify `ssh hermes 'cd /opt/hermes && git status'` first per the working-tree-discipline rule).
- **Commit:** nothing committed yet — ask Ramana before committing the `research/` package + `src/automation/deals.py` + `client_classify.py` + docs.
- **Named-flow history backfill** (optional, if wanted): NSE bot-walls it; options = a real browser session (limited range) or BSE. Deferred.
- **MTF (weekly/monthly) signals** are still EMPTY (held engine `mtf_signals.py`); not needed for the backtest.
- **FUTURE DATA FRONTIER — Ramana's stated direction (do NOT lose this):** reported financial results are
  a CLOSED-period fact, not a promise for the future, so fundamentals are a weak FORWARD signal. The real
  forward trigger is likely QUALITATIVE — **management commentary / earnings-concall tone / guidance /
  the direction in corporate announcements.** Ramana: *"that could be the trigger or the direction someone
  is taking… we will come there for sure… include it in the respective modules."* This is a future module
  (concall-transcript + announcement ingestion → NLP/tone), to be built AFTER the data-level strategies
  are backtested. The named-flow feed (bulk/block + FII/DII) is the first step of this "who/what is driving
  it" layer; the qualitative layer is the next.

## 11. DECISION LOG (locked with Ramana this session)
- Monthly event = **rolling +10% HELD** over ~22td (today ≥+10% vs a month ago) — corrected from the initial wrong ≥20%-thrust/retain-50%. Rolling, never calendar.
- **Raw data is the PRIMARY discovery battery; DVPT/house = comparison only** ("don't lean on my strategy").
- Universe floor ₹1cr for discovery; **strategies trade ₹5cr (S1) / ₹25cr (S2,S4)**.
- **Skip F&O.** Wire the FREE named-flow feeds (done).
- Be unbiased; test, fail, come back; review the data with no bias.

## 12. POINTERS
- Research log: `docs/explosive-move-research.md` · Strategy specs (full): same doc, "Candidate strategies" + the workflow output.
- Workflow transcripts (recoverable hypotheses/specs): `C:\Users\gotti\.claude\projects\D--Hermes\361324fd-c38f-48f9-ab31-a9ffb780b8cd\subagents\workflows\` (pattern-pressure `wf_a22b8439-5c9`, strategy-design `wf_a9b670ce-c93`). Parse `agent-*.jsonl` to recover any agent's full output at zero cost.
- Package: `research/explosive_moves/` = common, events, features, mine, validate, sensitivity, cluster, brief, htest, probe, probe2, launchpad_scan, results_table, run_all. Plus `src/automation/deals.py`, `src/automation/client_classify.py`.
