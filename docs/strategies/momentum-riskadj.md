# Momentum / RISKADJ Ranked-Rotation Engine — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** BENCHMARK engine · gross selection lens (NOT fundable net of cost, except qtr large-cap LOWVOL_MOM) · **Governing decision(s):** D66 + the ledger benchmarks · **Reconciled:** 2026-07-11 (S111).
> **Charter:** the single canonical definition + current-state reference for the momentum engine. Full result tables + failure ledger: [strategy-ledger.md](../strategy-ledger.md). Numbers live in code + [calculations-and-weights.md](../calculations-and-weights.md); this page summarizes + links — it never re-pastes the result tables (they live in the ledger, single source).

**One-line definition:** a monthly cross-sectional **ranked-rotation backtest** that sorts every liquid NSE name by **RISKADJ** (6-month return ÷ 3-month volatility), holds the top-25 equal-weight, and scores it net of cost, walk-forward on both halves, against a Nifty 500 buy-&-hold Sharpe-**0.89** hurdle — the project's internal **benchmark** and a **gross selection lens**, not a fundable net-of-cost alpha.

---

## 1. What it is

The core factor / backtest machine of the platform: the daily "surface the relevant stocks" engine of the primary-intent north star, formalized from the empirical finding that **momentum is the only consistent, reliable gross forward-price signal in Indian equities** ([predictive-attributes-findings.md](../predictive-attributes-findings.md)).

The machine (one construction family):

1. At each **monthly** rebalance (22 trading days), rank every liquid name cross-sectionally by a **selection signal** (RISKADJ is the flagship; 8 signals are wired).
2. Take the **top-25**, hold **equal-weight** for the month.
3. Charge **cost**, mark monthly, and compound.
4. Split the 2012→2026 history into **two walk-forward halves** (2012-18 vs 2019-26); a signal "survives" only if it beats **Nifty 500 Sharpe 0.89 in BOTH halves** with positive CAGR in each.

RISKADJ is **the best of 32 tested signals** and is kept as the **internal benchmark to beat** — every new strategy is measured against it. It is *not* productized as a client "buy this basket" claim; it is an analytical **ranking lens** that surfaces names for research. Benchmarks (Nifty 50 / **Nifty 500, the 0.89 hurdle** / Nifty Midcap 50) and the full 32-row leaderboard live in the ledger — see [strategy-ledger.md § Benchmarks + Tier 1](../strategy-ledger.md).

## 2. Our variation vs. the standard technique

Classic cross-sectional momentum ranks on raw 12-month return. What is ours here:

- **RISKADJ = 6-mo return ÷ 3-mo volatility** (not raw MOM6/MOM12). Risk-adjusting both *raises* Sharpe and *cuts* drawdown vs raw momentum — raw MOM12's β≈1.33 / MaxDD≈−50% is a leveraged-beta liability, so the production form is deliberately the risk-adjusted / low-vol variant, never raw momentum as the sole ranker.
- **Relative percentile liquidity gate, not a static ₹5cr floor.** Names compete on a cross-sectional turnover percentile (top-40%/60% by median traded value) — the standing "no absolute-rupee thresholds" rule (percentages / ranks only). This alone lifted RISKADJ from Sharpe 1.13 → 1.29.
- **The C-BLEND tilt** — a 50/50 rank blend of RISKADJ-percentile with the proprietary **capital-allocation ("C")** percentile (§4, §7), a *descriptive* re-sort, not a veto or standalone ranker.
- **Value-in-rupees rule** — all liquidity / size math uses median **turnover (₹)**, never share count, so corporate actions can't distort the gate.
- A first-class **valuation guard** (`not_extended`: optionally exclude names up >200% in ~5y) kept as a *tested variable* — the data says it slightly *reduces* Sharpe in a momentum frame (winners keep winning), recorded as an honest tension, not applied by default.

What is **not** proprietary: the momentum premium itself (Fama-MacBeth λ t=3.36) is a real but generic factor. Public yardsticks (MOM12, HI52, RESID_MOM, …) are kept in a **separate non-proprietary registry** ([strategy-ledger.md § Known/public factor strategies](../strategy-ledger.md)) — the proprietary claim is only what *beats* those yardsticks (so far: the PIT-quality / C blend cutting drawdown on top of RISKADJ).

## 3. How it works (methodology)

- **Harness:** `research/explosive_moves/factory.py` — the `SIGNALS` map (MOM6, MOM12, **RISKADJ** = `mom6/(vol+ε)`, ACCEL, **LOWVOL_MOM** = `0.5·rank(mom6)+0.5·rank(−vol)`, DELIV_MOM, **QUAL_MOM**, PULLBACK), `build_tables()` (PIT feature tables per rebalance), `run_strat()` (rank → top-N → equal-weight → net cost), walk-forward `slice_stats()`. Public-factor zoo + attribution inputs: `factor_zoo.py`.
- **Overlays:** `overlay_experiment.py` (relative gate + PIT quality) and `c_overlay.py` (the capital-allocation C overlay; `sel_c_blend`, PIT `attach_c`).
- **Two cost models — the whole honesty pivot:**
  - **Flat** (`COST_PS = 0.3%` × turnover, + a 1.5× stress proxy) — the ledger's headline numbers; capacity-blind.
  - **Participation / Almgren √-law** (`cost_participation.py`): per-side `impact = k·σ·√(order/ADV)`, k=0.6, ≤10% ADV/day POV cap, tiered spreads, a days-to-fill delay penalty, **sized against a target AUM** so impact scales with the real clip. `cblend_cost_recut.py` re-cuts the champion under this model, swapping *only* the cost term (reproduces the flat 1.32 exactly, so any delta is the cost model alone).
- **Persistence:** every run is appended (never overwritten) to `research.db` via `strategy_store.py` → `strategy_registry` / `strategy_runs` / `strategy_holdings`, plus `out/*.csv` leaderboards.

Full parameterization + every internal weight: [calculations-and-weights.md](../calculations-and-weights.md) and the code. **Result tables are not duplicated here — see the ledger.**

## 4. Status, validation & honesty fence

**THE headline — gross vs. net (binding, must travel with every number):**

- **GROSS / flat-cost — the selection edge is REAL.** RISKADJ ranks **best of 32** at gross/flat-cost Sharpe **~1.13** (static-floor baseline) to **~1.29** (relative gate), α ~+16%, and survives both walk-forward halves. It is the **internal benchmark**.
- **NET of realistic cost — the alpha DOES NOT EXIST here.** Under a participation/slippage model (~0.5×ATR, ~100%/mo turnover → ~36%/yr cost), that 1.29 **collapses to ~0.09, CAGR negative, MaxDD ≈ −69%** — momentum *sold as a fundable strategy* is a **BLOCKING failure model**. Nothing beats Nifty 500 buy-&-hold (0.89) net of realistic cost.
- **C-BLEND 50/50 (Sharpe 1.32) is FLAT-COST-ONLY and NOT fundable.** The recorded "champion" (flat-cost Sharpe 1.32 / MaxDD −28.2% / Calmar 1.15) nets **0.52 @₹25cr · 0.17 @₹50cr · −0.30 @₹100cr** under participation cost — it beats the index at **no AUM**. It stays a **descriptive/paper overlay** (the D66 fence), never a book.
- **The ONLY participation-fundable corner is quarterly large-cap LOWVOL_MOM** — net Sharpe **1.02 @₹50cr** (CAGR 18.1%, MaxDD −21.4%), ~breaks even ₹100–150cr, 0.61 @₹500cr → a **~₹50–100cr defensive tilt**, not a scalable edge.
- **It's momentum-BETA, not selection alpha (proven).** Controlling for the generic momentum factor (WML) + market, RISKADJ's residual α falls to **+7.3%, HAC t=1.99 → fails the t≥3 bar**; WML eats 51% of the raw α. The premium is real but **un-proprietary**. Survivorship is second-order (+0.02 Sharpe).

**The doctrine (the project's core thesis — state it plainly):** *price strength is the only gross forward-return engine; value / quality / credibility / accumulation are veto / filter / context layers, not rankers; and no factor here is a fundable net-of-cost alpha vs the index (Nifty 500 B&H Sharpe 0.89). The asset is PIT rigor + under-covered data + the analytical selection lens — not a backtested alpha strategy.*

**D66 (governing):** capital-allocation **"C" is a RISK FILTER, not a return ranker** — it works as a **50/50 rank blend / descriptive tilt**, NOT a hard veto and NOT a standalone ranker; head-to-head it **subsumes the 4-metric quality lens** (ROCE/D-E/OPM/interest-cover). Standalone value and standalone quality do **not** beat the index here (QUALITY α≈0, BOOK_YIELD α −1.8% / MaxDD −82%).

Full failure-models table (BOOK_YIELD, EARN_YIELD, QUALITY-standalone, momentum-as-fundable, C-BLEND-as-book, PEAD book, …): [strategy-ledger.md § BLOCKING FAILURE MODELS](../strategy-ledger.md). Cite the exact recorded numbers before re-attempting any of them.

## 5. Where it lives (code · routes · DB · timers)

- **Backtest machine (research venv, numpy):** `research/explosive_moves/factory.py` (+ `factor_zoo.py`, `overlay_experiment.py`, `c_overlay.py`, `cost_realism.py`, `cost_participation.py`, `cblend_cost_recut.py`, `attribution.py`, `strategy_store.py`).
- **Proprietary layers (app):** `src/automation/capital_allocation.py` (Dataset "C"), `src/automation/scoring.py` (14-pattern patearn quality), `src/automation/fundamentals_asof.py` (PIT reader, no look-ahead).
- **Routes:** **`/dash/testing`** ("Lab", under Strategies — `src/web/testing_view.py`, the ranked registry + candidate holdings + the honest verdict) and **`/dash/momentum-scan`** (nested `/dash/markets/momentum-scan`, `src/web/momentum_view.py` — the nightly scanner with three sorts: **Risk-adjusted momentum · C-blend 50/50 · Equal-weight ensemble**).
- **DB (`research.db`):** `strategy_registry` / `strategy_runs` / `strategy_holdings` (backtest history), `momentum_scan` (nightly surface), `capital_allocation_scores` (nightly C, joined for the C-blend), plus `out/strategy_leaderboard.csv`.
- **Timers:** `hermes-momentum-scan.timer` → `explosive_moves.momentum_scan` (nightly; the scanner self-heals `em_cache.pkl` when it lags the DB).

## 6. Data & provenance

- **Price / momentum / volatility / liquidity:** NSE **bhav copy** (primary source) → `adj_close`, `med_turn`, the `vol_66` / delivery / SMA feature cache (`embase`). This is the whole gross-momentum engine and is on fully primary data.
- **Quality / capital-allocation (C):** PIT fundamentals from `research.db.fundamentals_history` (1,983 syms × ~24y, point-in-time by `report_date`), read as-of via `fundamentals_asof`. **Provenance caveat (guardrail #8):** `fundamentals_history` is currently **Screener-derived** and under active **XBRL migration remediation** — see [fundamentals-xbrl-migration.md](../fundamentals-xbrl-migration.md); do not extend the Screener dependency, and disclose it where C is shown (the live surfaces carry the Screener→XBRL disclosure).
- **Survivorship:** the ~3,515-symbol cache is survivor-tilted; the PIT panel books a delisted name's return-to-last-price rather than dropping it, and delisting-return booking moves Sharpe only **+0.02** (second-order). Fundamentals coverage is narrower (~1,700 names) → value/quality reads lean on a smaller universe. True net-of-cost numbers, if anything, sit *lower* than recorded.

## 7. Terminology canon

- **RISKADJ** — 6-mo return ÷ 3-mo volatility (`mom6/(vol+ε)`). The flagship signal and internal benchmark.
- **QUAL_MOM** — risk-adj + delivery + low-vol blend; best Calmar of the high-Sharpe set (defensive).
- **LOWVOL_MOM** — `0.5·rank(mom6)+0.5·rank(−vol)`; β≈0.82, shallowest drawdown. The **only participation-fundable corner** (quarterly, large-cap, wide hold-band).
- **MOM12** — raw 12-month momentum; highest gross return, brutal drawdown; a *public* yardstick, kept in the non-proprietary registry.
- **C-BLEND** — `0.5·RISKADJ-pctile + 0.5·C-pctile`; a descriptive tilt (flat-cost champion 1.32; not fundable).
- **"C" (capital allocation)** — Dataset-C quality: ROIIC, ROCE level+trend, dilution drag, debt-funding share, growth efficiency (`capital_allocation.py`). A veto/filter/context layer per D66, consumed as a blend.
- **Gross vs net** — flat-cost (0.3%/turnover) vs participation/Almgren cost sized by AUM. The gap *is* the honesty fence.
- **The 0.89 hurdle** — Nifty 500 buy-&-hold Sharpe; the survival bar in both halves.
- **⚠ Disambiguation:** the **momentum FACTOR** here (a cross-sectional monthly *ranker* on price return ÷ vol) is distinct from **RS-momentum** (relative strength vs an index — JdK RS-Ratio/RS-Momentum, RRG, Mansfield). See [relative-strength.md](relative-strength.md). The patearn 14-pattern fundamental lens is [patearn.md](patearn.md) — a quality/veto context, never a standalone ranker.

## 8. Decision & session history

- **D66 (2026-06-23):** PIT fundamentals → backtestable patearn score; the score is a **RISK FILTER**, returns come from accumulation/RS. Origin of "C/quality = veto/filter, not ranker."
- **2026-06-24 overlay experiment:** relative gate beat the static ₹5cr floor (Sharpe 1.13 → **1.29**); a PIT 50/50 quality blend cut MaxDD −42% → **−29%** at Sharpe 1.18 — first hard proof a proprietary lens improves the risk-adjusted outcome with zero look-ahead.
- **2026-07-02 attribution + institutional panel:** momentum = **beta, not selection — proven** (`attribution.py`); "sell DATA, not signals." Headline of [predictive-attributes-findings.md](../predictive-attributes-findings.md) rewritten.
- **2026-07-03 C-overlay (S77b):** C-BLEND 50/50 = flat-cost champion (Sharpe **1.32**, MaxDD −28.2%, Calmar 1.15); **D66 refined** — C's working shape is a **rank blend**, not a hard veto; C **subsumes** the 4-metric quality lens.
- **2026-07-05c cost re-cut:** the 1.32 is **flat-cost-only**; under participation cost C-BLEND is **NOT fundable** (0.17 @₹50cr). Fundable claim withdrawn; LOWVOL_MOM (1.02 @₹50cr) confirmed as the only corner.

## 9. Open items / frozen work

- **Residual-alpha attribution — partially done.** β-not-α is proven (`attribution.py`); a fuller **beta/size/sector/liquidity-neutral** decomposition is still queued (until run, treat momentum's *direction* as reliable, *magnitude* as provisional).
- **Ensemble Steps 3–7 (frozen roadmap).** Step 2 is decided (equal-weight MOM12 + HI52 + RISKADJ + LOWVOL_MOM); Steps 3 (regime gates), 4 (C/A/B veto layer), 5 (cost/turnover-aware form), 6 (productionize the daily surface), 7 (live decay monitor) remain open — one step per session, Ramana steers each. See [momentum-engine-formalization.md](../momentum-engine-formalization.md).
- **Untested overlays:** MEP-accumulation and concall-credibility on the momentum book (both descriptive-only so far).
- **Gate design:** a stratified / size-bucketed gate or a velocity "override lane" (to admit good sub-~₹5k-cr midcaps like PIXTRANS without flooding the book with microcaps) — an option to pursue; pure velocity wrecks the edge.
- **Live check:** passive re-verification of the live C-blend sort vs the recorded numbers once a few weeks of nightly `ca_pctile` history accrue.

## 10. Sources of truth

- [strategy-ledger.md](../strategy-ledger.md) — **primary source**: Benchmarks, BLOCKING FAILURE MODELS, Tier-1 survivors, C-BLEND / cost-reality experiments. (Full result tables live here — single source.)
- [momentum-engine-formalization.md](../momentum-engine-formalization.md) — the living spec + roadmap (the two-layer truth, Steps 1–7).
- [predictive-attributes-findings.md](../predictive-attributes-findings.md) — the 14-year factor study + attribution + participation-cost headline.
- [calculations-and-weights.md](../calculations-and-weights.md) — canonical formulas + every internal weight (numbers live once, in code + here).
- [institutional-panel-assessment.md](../institutional-panel-assessment.md) — the "sell data, not signals" panel verdict.
- **Sibling canonical refs:** [relative-strength.md](relative-strength.md) (RS-momentum, disambiguated) · [patearn.md](patearn.md) (14-pattern quality lens).
- **Memory:** `strategy-ledger-and-benchmarks` · `predictive-attributes-finding` · `failure-models-ledger` · `dataset-roadmap-c-a-b`.
- **PROJECT_STATE.md:** § Decision log (D66), § Session log (Sessions 37, 71, and the 2026-07-03/-05c experiments), § Key file paths (`capital_allocation.py`, `scoring.py`, `fundamentals_asof.py`).

## Slow rotation — the quarterly LOWVOL_MOM anchor (S132f)

The one form of this family that survived the participation-cost recut is now a live surface:
**`/dash/momentum-scan/slow`** (declared child of the scanner). Rule as validated: **large-cap gate**
(top turnover quintile, self-scaling) · **LOWVOL_MOM** = 0.5·pctrank(6-mo momentum) +
0.5·pctrank(−66-day vol) · **top-25** equal-notional · **quarterly clock** · **hold band ≤35**
(members stay while ranked ≤35; refill from the top — the turnover discipline IS the strategy).
Numbers on record: family flat-cost ~1.10 → **net ~1.02 @₹50cr** under the Almgren participation
model; beats the index net up to **~₹100–150cr** capacity; defensive **beta**, not selection skill.
Engine: `src/automation/slow_rotation.py` (nightly `--refresh`, rebalances only on quarter turn;
bounded `slow_rotation` table). View: `src/web/slow_rotation_view.py` (live rank drift computed on
read; CSV; descriptive fence). Ledger anchors: §§ 2026-06-24 cost-realism · 2026-07-02 corrected
participation model · 2026-07-05c C-BLEND recut.

## Factor league — the classic families, ranked by our numbers (S132g)

**`/dash/factor-league`** (Strategies lens): the famous "premium" strategy families ranked by the
Sharpe/alpha measured in OUR 14y walk-forward — not textbook claims. League order (flat-cost, ₹5cr
universe, labeled): PACER-25/RISKADJ 1.13 · QUAL_MOM 1.10 · **STEADY-25/LOWVOL_MOM 1.10 flat → NET
1.02 @₹50cr = the only net survivor and the AUTO-PORTFOLIO** · SPRINTER-25/MOM12 1.06 · then the
failures shown with their numbers (DELIV_MOM 0.85 · QUALITY 0.76 α≈0 · EARN_YIELD 0.70 · BOOK_YIELD
0.62 α<0 REJECTED) vs the 0.89 Nifty-500 hurdle. Live rosters (top-25) + daily churn feed:
`src/automation/factor_league.py` → `factor_league`/`factor_league_churn`; view
`src/web/factor_league_view.py`. Every number restates the frozen ledger; the page may not soften
them.

## Maintenance

- **When to update:** a new signal or overlay lands · a cost model or gate changes · a new backtest re-cuts a headline number · the C/quality role (D66) is revised · the ensemble roadmap advances a step · the Screener→XBRL migration closes.
- **How:** keep this page a *summary + links*. New result tables go to [strategy-ledger.md](../strategy-ledger.md) (single source); new formulas/weights to [calculations-and-weights.md](../calculations-and-weights.md); this page only re-states the current *status*, the *honesty fence*, and where things live. Never paste the leaderboard here.
- **Honesty fence is load-bearing:** any edit that would soften "gross ≠ net," the "not fundable except qtr large-cap LOWVOL_MOM" corner, or the D66 "C is a blend/veto, not a ranker" line must cite a new backtest that beats the recorded number *net of participation cost* — otherwise it is a regression. Failures are BLOCKING until cited (memory `failure-models-ledger`).
