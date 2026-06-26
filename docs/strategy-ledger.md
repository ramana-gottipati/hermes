# Strategy Ledger — what we've tried, what it scored, what we decided

**Purpose.** A permanent, honest registry of every strategy/signal we have tested, *including
failures*. A failure is a recorded data point, not junk — we keep it so we never re-walk a dead
road, and so every new idea has a **benchmark to beat**. Nothing is deleted; things are *parked*
with a reason.

**Created 2026-06-24** after discovering that a strong result (ranked-rotation RISKADJ, Sharpe
1.13) had been computed in research but **never recorded anywhere** — it printed to a terminal
once and evaporated. This file (plus the auto-saved `research/explosive_moves/out/strategy_leaderboard.csv`,
which `factory.py` now writes on every run) is the fix.

**PERSISTENT STORE (2026-06-24).** This markdown is the human-readable narrative; the machine-readable,
queryable, refinable home is now **`research.db`** via `research/explosive_moves/strategy_store.py`:
- `strategy_registry` — one row per strategy (definition + status).
- `strategy_runs` — one row per BACKTEST RUN, **timestamped** (refine = `record_run()` appends, never
  overwrites, so a strategy's metric history across versions is preserved).
- `strategy_holdings` — current top-N names per strategy (written by `strategy_menu.py`).
Seeded from `out/*.csv` (22 strategies, 22 runs). Re-running any backtest + `--seed` (or calling
`record_run`) adds the new result. The HTML board (`docs/strategy-board.html`) and the in-app **Testing page** read from here.
**To refine:** edit the signal/params, re-run the backtest, `record_run()` the result — the registry shows
the new run beside the old.

**IN-APP (LIVE 2026-06-25):** `/dash/testing` — `src/web/testing_view.py`, an isolated `APIRouter` reusing
the shared `_shell`; reads `research.db` and renders the ranked registry + candidate holdings + the honest
verdict. Mounted via 2 lines in `main.py` (deployed on the VPS; `main.py` is parallel-session-owned so NOT
committed here — fold the import + `include_router(testing_router)` into committed `main.py` when the web
session is free).

**NAV — coordinated with + approved by the "patearn UI Architecture v2" session (2026-06-25).** Placement =
**Strategies ▸ "Lab"** (beside Workbench, NOT a top tab; label "Lab", not "Testing"; recorded in their
`docs/ui-architecture-v2.md` §14.3).

**LIVE + DISCOVERABLE NOW (per Ramana's directive — must reflect on the main app, not URL-only).** Patched the
DEPLOYED VPS `dashboard.py` surgically (backup `dashboard.py.bak-lab`, py_compile-checked, hermes-api restarted,
verified): (1) `_WS: "testing":"strategies"`; (2) the `/dash/stocks` Strategies hub renders a `wb_link += '<a
class="row sub" href="/dash/testing">Lab ⇄ …</a>'` beside Workbench/Screener. The deployed code has no
`_subnav`/`_SUBNAV` (that's v2-redesign-only), so the live link uses the deployed `wb_link` form, not their
`_SUBNAV` row.

⚠️ **Durability:** this is a **VPS-only patch — NOT committed** (committing `dashboard.py` would clobber the
parallel chart/v2 uncommitted work). It will be overwritten at the next `dashboard.py` deploy. The v2 session
will fold the equivalent into the **committed** `dashboard.py` (their `_SUBNAV` "Lab" row + the `_WS` line) so it
persists; their row then supersedes the `wb_link` line. `testing_view.py` already calls `_shell(active="testing")`.

---

## Benchmarks (buy & hold, monthly marks, 2012–2026)

| Index | CAGR | MaxDD | Sharpe |
|---|---|---|---|
| Nifty 50 | +13.0% | −29.4% | 0.85 |
| **Nifty 500 (our hurdle)** | **+14.6%** | **−30.1%** | **0.89** |
| Nifty Midcap 50 | +18.6% | −42.0% | 0.88 |

A strategy "survives" only if it beats **Nifty 500 Sharpe (0.89) in BOTH walk-forward halves**
(2012–18 and 2019–26) with positive CAGR in each.

---

## Tier 1 — Ranked-portfolio signals (TESTED, walk-forward). The live benchmark.

Machine: rank every liquid name monthly by a signal → hold top-25 equal-weight → net of a simple
0.3%/turnover cost. Full table: `research/explosive_moves/out/strategy_leaderboard.csv` (32 rows).
Source: `research/explosive_moves/factory.py`.

**Survivors that matter (5cr universe):**

| Signal | Definition | CAGR | MaxDD | Sharpe | Note |
|---|---|---|---|---|---|
| **RISKADJ** | 6-mo return ÷ 3-mo volatility | 28.6% | −33.1% | **1.13** | Best of 32. The benchmark to beat. |
| QUAL_MOM | risk-adj + delivery + low-vol blend | 20.1% | −26.7% | 1.10 | Same Sharpe, gentler drawdown |
| LOWVOL_MOM | momentum + low volatility | 18.5% | −26.0% | 1.10 | Best drawdown control |
| MOM12 | raw 12-mo momentum | 30.0% | −43.0% | 1.06 | Highest return, brutal drawdown |

**Failures (kept as learnings):**

| Signal | Sharpe | MaxDD | Lesson |
|---|---|---|---|
| ACCEL (1-mo thrust) | 0.42–0.64 | −62% to −70% | Chasing short-term spikes = catastrophic drawdowns |
| PULLBACK | 0.56–0.72 | −44% | "Buy the dip in an uptrend" didn't beat the index |
| DELIV_MOM | 0.76–0.85 | −45% | Delivery-% added no standalone edge here |

**Two recorded findings worth periodic re-debate:**
- **Valuation guard (+VAL, cut names up >200% in 5y) slightly *reduced* Sharpe** (RISKADJ 1.13 → 1.03).
  In a momentum frame the data says winners keep winning; tension with "don't chase extended."
- **Edge is stronger in the 5cr universe than 25cr** (RISKADJ 1.13 → 0.96): alpha lives in mid/small-caps,
  but so does slippage/capacity risk.

**⚠️ Honest caveat — do not crown RISKADJ yet.** The 1.13 Sharpe uses a *naive* cost model
(flat 0.3% × turnover, no slippage/impact/capacity) and the **static ₹5 cr liquidity floor we reject**.
The more rigorous swing analysis (Tier 2) showed momentum edges erode under realistic costs. RISKADJ
is the strongest tested component we have and a fair internal **benchmark**, but its *true* number
needs: (a) a relative percentile liquidity gate, (b) realistic slippage/capacity, (c) the Tier-3
overlay test. Until then it is **"indicative, not validated."**

---

## Tier 2 — Bottom-up "Launchpad" swing program (TESTED + recorded as ~failed)

Single-name swing entries with stops/scale/trail (`research/explosive_moves/backtest.py`,
`strategies.py`). Recorded verdict in `docs/explosive-move-NEXT-SESSION.md`: **"selection result =
NO survivor net of costs."**

| Strategy | CAGR | Verdict |
|---|---|---|
| S1 Coiled-Launchpad Core | +4.0% | Modest; lightly invested; +2.07% expectancy/trade |
| S2 Heat-Capped Large-Cap | +3.1% | Modest |
| S3 Shakeout reversion | −0.5% | **Failed** |
| S4 Skeptic cost-stressed | +0.4% | At 1.5× cost the edge goes **negative** |

**Learning (the link to Tier 1):** the swing edge is fragile to costs — which is *why* the
fully-invested monthly *rotation* form (Tier 1) is the more robust expression of the same momentum
idea. The validated signal pattern: momentum **with contracting volatility** ("the Launchpad"),
OOS hit 70–80%, winners run +40–100% and barely dip. Also recorded: **no stealth-accumulation
footprint survived in EOD data** — moves are a momentum/volatility/churn phenomenon.

---

## Tier 3 — Analytical lenses (BUILT + deployed; NOT return-tested as standalone alpha)

These describe *why* a name is interesting; none has a walk-forward return curve. The open question
is whether layering them on Tier 1 **adds alpha or cuts drawdown** (QUAL_MOM hints it can).

| Lens | What it reads | Status |
|---|---|---|
| patearn | 14-pattern point-in-time fundamental quality score | deployed; PIT-backtestable but not run as alpha |
| MEP / DVPT | signed accumulation / distribution | deployed (confirmation, not prediction) |
| RS suite (RRG, RSI-of-RS, Mansfield, capture, RS-band) | relative strength vs index | deployed (descriptive) |
| Concall Intelligence | management guidance-accuracy / credibility | **RETURN-TESTED 2026-06-25 → NO validated factor** (see section below); descriptive dossier only |
| F&O OI / participant positioning | FII/DII/Pro/Client long-short | deployed (descriptive) |
| Wolfe / Ignition / theme tags | geometry / ML challenger / classification | built |

---

## Concall Intelligence — RETURN-TESTED + FALSIFIED as a factor (2026-06-25)

CCI credibility (PIT guidance-accuracy level + momentum) was finally return-tested via
`src/automation/cci_backtest.py` (free, no LLM): PIT `credibility_series` × corporate-action-adjusted forward
returns (NSE prev_close chain over `bhavcopy_rows`), de-marketed cross-sectionally by concall-month cohort,
3,523 proven points (n_resolved≥3) across **377 symbols**, 3/6/12m. **Two independent reviews (code +
methodology) reproduced the result on the VPS** before it was recorded.

| Test | 3m | 6m | 12m | Read |
|---|---|---|---|---|
| **Level: HIGH−LOW excess** | −3.1% | −5.8% | **−10.0%** | high-cred UNDERPERFORMS (low-cohort t up to +3.6) |
| **Momentum: rising−falling** | +0.3% | +0.8% | +1.1% | weak; both rising & falling beat flat → "moved" not "rose" |
| **Deterioration veto: P(<−20%) event vs non-event** | 6.8 / 6.9% | 12.6 / 12.5% | 14.9 / 15.8% | NO downside difference (event marginally *better*) |

**Verdict: NO empirically-validated long / short / risk edge.** The inverse level print is fragile — n=377
SURVIVOR names, concentrated post-2023 (−17% vs −7% pre-2022) and in high-level megacap mean-reversion (a
regime print, not a structural factor); it survives size + valuation neutralization but is heavily
survivorship-confounded. The deterioration veto shows no downside-cutting value AND is structurally blind to
its true target (delisted blow-ups removed by survivorship). **Binding defect = BREADTH (the current-holder
universe ceiling, 377 names), NOT corpus depth** → more extraction cannot fix it.

**Decision:** do NOT spend ~₹2,500 to complete the transcript corpus for any factor/screen use. CCI's
defensible role is **DESCRIPTIVE only — the per-name evidence dossier** (the qualitative track record shown
when researching a name), NOT a ranked screen or factor. Transcript CAPTURE stays running (free) as a research
asset. This negative result is a recorded benchmark, exactly per this ledger's purpose. Reproduce: `python -m
src.automation.cci_backtest --mode both`. (Doesn't fit the Tier-1 portfolio-Sharpe machine schema — it's a
cross-sectional factor test, recorded here in narrative.)

**FOLLOW-UP (2026-06-25, autonomous — "don't stop; test it in confluence + check capex"):**
- **Confluence (credibility × momentum)** — within HIGH trailing-momentum names: hi-cred excess +2.5% vs
  lo-cred +3.3% (spread **−0.8%**, still inverse); deterioration events did NOT precede deeper drawdowns
  (MDD −31.9% vs −33.5%). **Credibility adds nothing even in confluence.** Confirmed dead, both ways.
- **🟢 THE REAL SIGNAL — concall CONTENT, not credibility.** Scanning each forward-looking `statement_type`
  as an event (a concall that made it vs didn't; 3m de-marketed excess, 702 symbols) shows a SENSIBLE,
  positive structure: **debt_reduction +2.8% · volume +2.3% · new_product +1.8% · capex +1.5% · expansion
  +0.9%** (growth / deleveraging intent → outperformance) vs **cost_savings −1.0% · revenue −0.7% · other
  −0.7%** (defensive language → underperformance). Economically coherent: deleveraging + growth-investment
  are re-rating catalysts; cost-cutting flags a name under pressure. **This is where the concall extraction's
  value actually lives — a "management growth-intent" signal, NOT credibility.** Front-loaded (3m; capex
  faded by 12m). Still cross-sectional + survivorship-bounded. **NEXT (warranted): a proper top-N
  walk-forward PORTFOLIO backtest of a growth-intent composite (debt_reduction+volume+new_product+capex), net
  of costs vs Nifty 500 — the Tier-1 `factory.py` machinery — plus fix the ₹-magnitude normalizer to test
  capex/debt INTENSITY (likely stronger than the bare event).** Reproduce: `cci_backtest --mode all`.

---

## Experiment 2026-06-24 — relative gate + PIT quality overlay (DONE)

Ran `research/explosive_moves/overlay_experiment.py` (top-25 monthly, walk-forward, no look-ahead;
PIT fundamentals joined by `report_date ≤ rebalance date`; 1,700 symbols had fundamentals; avg gated
universe 611). Results in `out/overlay_experiment.csv`.

| Variant | CAGR | MaxDD | Sharpe | Calmar | 1.5× cost | Read |
|---|---|---|---|---|---|---|
| A. RISKADJ static-₹5cr (benchmark) | 28.6% | −33.1% | 1.13 | 0.86 | — | recorded baseline |
| **B. RISKADJ + relative gate** | **35.4%** | −41.9% | **1.29** | 0.84 | Sharpe 1.21 | **gate lifts return & Sharpe — but deeper DD** |
| C. + quality FILTER (top-half) | 26.5% | −30.0% | 1.11 | 0.88 | — | quality = defensive, costs return |
| **D. + quality BLEND 50/50** | 25.2% | **−28.7%** | 1.18 | **0.88** | Sharpe 1.10 | **best risk-adjusted; DD beats even baseline** |
| E. QUAL_MOM relative gate | 20.0% | −28.2% | 1.13 | 0.71 | — | existing blend, lower return |

**Findings (recorded):**
1. **The static ₹5 cr floor was not just wrong in principle — it was suboptimal.** The relative
   percentile gate lifted Sharpe 1.13 → **1.29** and CAGR 28.6% → **35.4%**. (Cost: drawdown deepened
   to −42%, as the relative gate reaches further into smaller names.)
2. **Our proprietary PIT-fundamental quality lens adds measurable value — as a drawdown controller,
   not a return booster.** Blending quality 50/50 cut MaxDD from −42% → **−28.7%** (better than the
   baseline's −33%) while keeping Sharpe **1.18** (above the 1.13 hurdle) and the best Calmar (0.88).
   This is the **first hard evidence that a Tier-3 lens, fused with the momentum selector, improves
   risk-adjusted outcome** with zero look-ahead.
3. **The rotation is cost-robust** — every variant survives a 1.5× cost stress (the Tier-2 swing
   book went *negative* at 1.5×). The ranked-rotation form is the resilient one.

**Caveats:** cost still a simplified per-turnover model (×1.5 stress is a proxy, not per-name
slippage/impact/capacity); quality used only 4 metrics (ROCE, D/E, OPM, interest cover) — the fuller
patearn, **MEP accumulation, and concall-credibility lenses are still untested** as overlays; quality
edge was stronger in 2012–18 (H1) than 2019–26 (H2).

**Verdict:** **D (RISKADJ + relative gate + 50/50 quality blend)** is the investable candidate —
Sharpe 1.18, Calmar 0.88, DD −29%, cost-robust. **B** is the higher-octane version (Sharpe 1.29) for
higher risk tolerance. This is a real step toward the proprietary "great component."

---

## Gate study 2026-06-24b — is the liquidity gate large-cap biased? (DONE)

Ran `research/explosive_moves/gate_study.py` (`out/gate_study.csv`). PIT market cap = (Net Profit ÷ EPS)
shares × raw close at each rebalance (no look-ahead). Strategy held constant (variant D); only the gate
changes. Tested the concern that "top-X%-by-traded-value" is really a large-cap filter that excludes
quality lower-float midcaps (e.g. PIXTRANS).

| Gate | Sharpe | MaxDD | CAGR | picks: large / mid+small | median pick mcap | PIXTRANS in |
|---|---|---|---|---|---|---|
| static ₹5 cr | 1.07 | −25.7% | 22.2% | 26% / 49% | ₹27,695 cr | 0 / 156 |
| **value top-40%** | **1.18** | −28.7% | 25.2% | 24% / 56% | ₹22,290 cr | 0 / 156 |
| velocity top-40% (turnover÷mcap) | **0.73** | −35.3% | 16.0% | 14% / 86% | ₹4,910 cr | 3 / 156 |
| velocity top-40% + ₹1 cr floor | 0.61 | −33.6% | 12.5% | 17% / 83% | ₹8,174 cr | 3 / 156 |

**Findings (both claims partly true, neither naive gate is the answer):**
1. **The value gate is NOT a Nifty-100 filter.** Its *picks* are only 24% large-cap, 56% mid/small,
   median pick ₹22k cr — because the momentum+quality *selection* already tilts smaller within the gate.
   BUT the concern is real at the tail: **PIXTRANS-class names (~₹2k cr) never clear it (0/156)** — we
   genuinely miss good sub-~₹5k cr names.
2. **The velocity gate fixes inclusion but WRECKS the edge.** It pulls the median pick down to ₹4,910 cr
   (86% mid/small/micro) and lets PIXTRANS in (3/156) — but Sharpe collapses **1.18 → 0.73** (fails the
   0.89 hurdle), drawdown deepens, CAGR halves. It floods the book with micro-cap noise where momentum is
   unreliable and (untested) real slippage would be brutal. Pure velocity over-corrects into junk.
3. **Capacity caveat confirmed:** velocity reaches names you can't deploy size into; the simple cost model
   *flatters* them, so the true velocity result is worse than 0.73.

**Verdict / what to actually build:** keep an absolute *tradability* requirement (you must be able to fill),
but stop excluding good midcaps wholesale. The promising untested design = **a stratified / size-bucketed
gate** (compete smallcaps vs smallcaps, midcaps vs midcaps) OR **velocity as a targeted "override lane"**
(admit a name if its turnover≥~₹3 cr AND its velocity is top-decile) layered on the value gate — so PIXTRANS
gets a lane without drowning the book in microcaps. NOT pure velocity.

**Velocity-LEVEL sweep (`velocity_sweep.py`, `out/velocity_sweep.csv`):** swept a fixed velocity bar
(turnover÷mcap ≥ X%/day) instead of a ranking. Every level *underperformed* the value gate (Sharpe
falls monotonically: 0.05%→0.81, 0.10%→0.67, 0.20%→0.35 … 1.0%→0.05; drawdown deepens to −90%; picks
shrink to micro). **Best velocity-based variant = the self-relative one** ("churning ≥1.5× its own
12-month median velocity"): **Sharpe 0.87, CAGR 20.9%, MaxDD −39.8%, median pick ₹4,818 cr** — still
below the value gate's 1.18, but the strongest size-neutral option, and an **option to pursue/refine**
(it directly encodes "trading great vs its own normal"). Caveat: only ~51% of names have a PIT market
cap (need fundamentals), so velocity rows draw from half the universe.

---

## Known / public factor strategies — separate registry (NON-proprietary)

Decoded the well-known market factors a quant desk would recognise and backtested each identically
(top-25 monthly, value-relative gate, walk-forward both halves, net cost, no look-ahead).
`research/explosive_moves/factor_zoo.py` → `out/factor_zoo.csv`. **These are public factors — kept
SEPARATE from our proprietary components on purpose. They are the higher-Sharpe yardsticks.**

Full institutional tearsheet (23 cols incl. CAGR, vol, payoff, position-payoff, edge ratio, best/worst
month, turnover, H1/H2) in `out/factor_zoo.csv`. Key columns below. **MFE%** = avg peak move available
while held · **Cap%** = realised ÷ peak, aggregate · **WCap%** = winners' capture of their own peak ·
**MAE%** = avg worst dip · **Alpha** = ann. vs Nifty 500.

| Factor | Sharpe | Sortino | MaxDD | Win% | PF | PosHit% | MFE% | Cap% | WCap% | MAE% | Beta | Alpha | surv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RISKADJ | **1.29** | 1.70 | −41.9% | 71% | 2.61 | 56% | 14.6 | 22 | 57 | −9.8 | 1.18 | **+16.4%** | YES |
| MOM12 | 1.20 | 1.67 | −49.6% | 67% | 2.42 | 54% | 15.9 | 21 | 57 | −10.8 | 1.33 | +17.0% | YES |
| LOWVOL_MOM | 1.12 | 1.22 | −33.9% | 70% | 2.39 | 57% | 8.9 | 21 | 58 | −6.1 | 0.82 | +6.3% | YES |
| HI52 | 1.09 | 1.36 | −38.6% | 67% | 2.32 | 55% | 12.0 | 21 | 57 | −8.3 | 0.99 | +9.5% | YES |
| QUAL_MOM | 1.04 | 1.36 | **−29.0%** | 64% | 2.14 | 54% | 12.8 | 18 | 56 | −9.3 | 1.05 | +8.0% | YES |
| RESID_MOM | 1.02 | 1.45 | −50.7% | 64% | 2.11 | 52% | 16.3 | 18 | 56 | −11.4 | 1.32 | +11.5% | YES |
| MOM6 | 1.01 | 1.39 | −51.3% | 66% | 2.11 | 52% | 16.3 | 18 | 56 | −11.4 | 1.33 | +11.4% | YES |
| VAL_MOM | 0.91 | 1.22 | −63.9% | 63% | 1.98 | 53% | 14.1 | 17 | 57 | −10.0 | 1.33 | +6.2% | no |
| DEFENSIVE | 0.87 | 0.96 | **−25.5%** | 67% | 1.98 | 54% | 7.2 | 17 | 58 | −5.4 | 0.71 | +1.7% | YES |
| QMV | 0.86 | 1.17 | −51.1% | 62% | 1.90 | 52% | 13.1 | 16 | 55 | −9.6 | 1.16 | +4.5% | no |
| LOWVOL | 0.84 | 0.88 | −26.5% | 66% | 1.93 | 55% | 6.2 | 16 | 55 | −4.5 | 0.56 | +1.3% | no |
| QUALITY | 0.76 | 1.05 | −43.6% | 62% | 1.78 | 52% | 10.0 | 14 | 56 | −7.5 | 1.03 | −0.0% | no |
| LOWBETA/BAB | 0.70 | 0.92 | −27.7% | 59% | 1.77 | 52% | 8.6 | 12 | 53 | −6.3 | 0.61 | +1.7% | no |
| EARN_YIELD | 0.70 | 0.95 | −71.4% | 60% | 1.70 | 53% | 12.7 | 15 | 56 | −9.0 | 1.35 | +0.4% | no |
| BOOK_YIELD | 0.61 | 0.93 | −82.3% | 57% | 1.58 | 51% | 14.1 | 13 | 55 | −10.0 | 1.56 | −2.2% | no |

**Capture finding:** with a fixed monthly-rebalance exit the book keeps only **~18–22% of the average
peak move** (Cap%); even winners give back ~43% of their high (WCap% ~55–58%). Capture is near-constant
across factors → it's a property of the *monthly exit*, not the factor. This quantifies the upside an
intra-month trailing/scale-out exit could recover (the Tier-2 swing book's premise — which died on
costs), and is a concrete lever to test on the proprietary build.

**What the data decodes (market-wide read):**
- **Momentum is king in India.** Every top row is momentum-based; RISKADJ (1.29) > MOM12 (1.20) > MOM6
  (1.01) — and risk-adjusting (÷vol) both raises Sharpe and cuts drawdown vs raw MOM6.
- **52-week-high (HI52, 1.09) and residual momentum (1.02)** both hold — the classic momentum anomalies
  travel to NSE.
- **Defensive blends buy smoothness, not return.** DEFENSIVE (−25.5%), LOWVOL (−26.5%), QUAL_MOM (−29.0%)
  have the shallowest drawdowns; QUAL_MOM keeps a 1.04 Sharpe with the best Calmar of the high-Sharpe set.
- **Value and low-beta were WEAK 2012–26** (EARN_YIELD 0.70 / BOOK_YIELD 0.61, both −70%+ drawdowns;
  BAB 0.70). Consistent with the global "value winter"; honest negative result — value did not pay here.
- **Coverage caveat:** value/quality factors lean on fundamentals (~1,700 names), so their universe is
  narrower than the pure-price factors.

**Registry verdict — higher-Sharpe known yardsticks to keep (non-proprietary):** RISKADJ, MOM12,
LOWVOL_MOM, HI52, QUAL_MOM (best Calmar), plus DEFENSIVE as the lowest-drawdown option. The proprietary
edge is then anything that *beats these yardsticks* — i.e. our PIT-quality / MEP / concall lenses adding
Sharpe or cutting drawdown *on top of* RISKADJ (already shown: quality blend cut DD −42%→−29%).

---

## Cost realism (B) — the momentum benchmark does NOT survive real frictions (2026-06-24)

`research/explosive_moves/cost_realism.py` → `out/cost_realism.csv`. Replaced the flat 0.3%/turnover with a
per-NAME realistic cost (tier half-spread + fees + **0.5×ATR slippage**), charged on each name actually traded.

| config | Sharpe | CAGR | MaxDD | ann. cost | capacity (median) |
|---|---|---|---|---|---|
| RISKADJ flat-cost (the headline) | **1.29** | +35.6% | −41.9% | 3.8% | — |
| RISKADJ realistic cost | **0.09** | −1.4% | −68.9% | **36.0%** | ₹30 cr |
| RISKADJ realistic + hold-band(35) | 0.24 | +2.7% | −66.8% | 30.6% | ₹31 cr |
| LOWVOL_MOM realistic | −0.10 | −3.0% | −57.3% | 23.9% | ₹60 cr |
| LOWVOL_MOM realistic + hold-band(35) | 0.15 | +1.0% | −50.3% | 19.8% | ₹65 cr |

**The 1.29 Sharpe was a flat-cost illusion.** Realistic cost — dominated by ~0.5×ATR slippage on
high-volatility momentum names turned over ~100%/month — runs **~36%/yr**, eating the entire ~35% gross →
Sharpe **collapses to ~0, CAGR negative**. The turnover lever (hold-band) only claws back to ~0.24. Capacity
is also tiny (~₹30 cr median position cap). Caveat: 0.5×ATR assumes naive market-order execution — patient
execution / much lower turnover / large-cap-only could recover SOME — but the direction is unambiguous and the
headline number is not real. **This removes even the "credible benchmark" prop: the honest near-term asset is
the point-in-time rigor + the data, NOT a backtested strategy.**

**Final test — does ANY config beat buy-and-hold net of cost? NO.** Ran the only low-cost corner: quarterly
rebalance, large-cap (top-20% liquidity), low-vol.

| config | Sharpe | CAGR | MaxDD | ann.cost | capacity |
|---|---|---|---|---|---|
| LOWVOL_MOM quarterly large-cap +band | 0.79 | 13.3% | −25.4% | 8.3% | ₹190 cr |
| LOWVOL quarterly large-cap +band | 0.78 | 9.6% | −23.1% | 5.4% | ₹168 cr |
| RISKADJ quarterly large-cap | 0.51 | 10.2% | −43.3% | 15.1% | ₹97 cr |
| **Nifty 500 buy & hold** | **0.89** | **15.3%** | −29.2% | 0% | ∞ |

Even the best survivable strategy (LOWVOL_MOM, Sharpe 0.79) **underperforms simply holding the Nifty 500 (0.89)**
on both Sharpe and CAGR, with finite capacity and execution complexity. The low-vol tilt buys a slightly shallower
drawdown (−23 to −25% vs −29%) — defensive equity, not alpha. **DEFINITIVE: no fundable equity-factor edge in this
research beats buy-and-hold the index net of realistic cost.** The strategy-as-alpha path is closed (recorded in
full); the genuine assets are the point-in-time rigor and the under-covered Indian-mid-cap data.

---

## Proprietary-alpha feasibility check (2026-06-24) — the hard truth

Tested whether our *proprietary* lenses can beat the public factor yardsticks (the only thing that would
impress a bulge-bracket desk). Result: **not provable today.**

- **MEP / accumulation = proven NO incremental alpha.** `mep_signals.py` docstring (locked 2026-06-22):
  a walk-forward + **Deflated-Sharpe** test showed the price-tape/accumulation features add nothing
  (DSR 0.45→0.36 when added to the 85-feature panel) — **descriptor-only**. Matches the explosive-move
  finding that smart-money footprints were "all refuted." Do not re-test as alpha.
- **Concall management-credibility = the genuinely novel signal, but NOT backtestable.** Coverage:
  `concalls` 83 symbols (2016–25), `concall_expectations_vs_actual` 43 symbols (2019–20),
  `concall_scores` **27 rows / 18 symbols**. No cross-section, no walk-forward, single narrow window.
  Cannot be reconstructed wholesale from the past (transcripts were largely never scored historically).
  **CORRECTION (verified 2026-06-24):** the credibility drain is NOT billing-blocked — `hermes-cci-drain.log`
  shows it actively processing transcripts today (200s interleaved with transient **503 "high demand"** model-
  overload, NOT `429`/quota). The ₹1,000/mo spend cap is not a constraint (Flash is cheap: the ~3,054-transcript
  backlog ≈ ₹1,400 one-time). The binding constraints are **breadth (89 symbols) + forward-only scoring +
  503 throughput**, not money.

**Falsification gate (proof-of-mechanism, 2026-06-24, `credibility_falsify.py` → `out/credibility_falsify.csv`):**
tested the 21 symbols with a real track record (resolved ≥5 promises) — does credibility predict forward
EXCESS return vs Nifty 500 (regime-stripped), no look-ahead? Result: **Spearman ≈ 0** (6m +0.02, 12m −0.09) —
**no standalone-alpha signal.** The ONLY directional hint: promise-BREAKERS (GA<55) underperformed the index
by ~10% at 6m while keepers were ~flat — i.e. credibility's plausible role is a **downside VETO / avoid
overlay** (which is exactly how `concall_scores.py` already treats it), NOT a return-ranker. Heavily
underpowered + regime-confounded (N=21, 2021–22) → inconclusive, but it **does not support the "proprietary
alpha factor" thesis** — at best a risk-reducer to test on a momentum book once breadth exists.

**Root-cause of the data starvation (verified 2026-06-24):** the credibility series is *frozen*, and it's
not the drain. `hermes-concalls.timer` runs settlement daily, but `concall_settle.py` only grades a promise
**if its resolving quarter exists in `concall_results`** (599 rows / 47 symbols / Dec-2023+) — it does NOT
settle against the deep 24-yr `fundamentals_history`. So recent runs resolve **0** ("settled 0… ongoing 22").
Bottleneck chain for A, ranked: (1) **breadth** — only ~44 symbols have extracted guidance (needs wider
Gemini fetch + a universe decision); (2) **deep settlement** — wire `concall_settle.py` → `fundamentals_history`
so annual guidance grades against the 24-yr archive (the Phase-1b TODO; that file is **parallel-session-owned**
— coordinate, don't collide); (3) extraction throughput (503s, eased by not contending with enrichment).
None is a money/billing problem.

**Conclusion:** there is **no number we can produce today** that impresses JPMorgan/GS/MS-tier professionals.
The momentum zoo is table-stakes (known factor, beta 1.18, toy costs); the proprietary alpha is **data-gated,
not model-gated.** The real path is a *data-acquisition* play: keep the credibility drain running (raise 503
throughput), WIDEN symbol coverage, and accumulate a point-in-time management-credibility time-series forward
(the un-copyable, not-on-their-terminal signal), with cost-realistic backtests and a live track. 12–24 month build.

---

## Best-available strategies — the decision menu (2026-06-24; human decides)

No strategy beats buy-and-hold net of cost (above), so these are surfaced as the **best AVAILABLE**, each for a
distinct purpose, for a human to choose. `research/explosive_moves/strategy_menu.py` prints the current top-25
holdings on a CLEAN universe (current Nifty 500 constituents still trading). **Data-hygiene note (deployment
requirement):** the first cut was contaminated by **delisted ghosts** (RANBAXY/IPCL/ABIRLANUVO, frozen at their
last bar) + **liquid/cash ETFs** (LIQUIDBEES/CASHIETF, which trivially win a low-vol screen); fixed by restricting
to live Nifty 500 membership. Any live version MUST keep this filter.

| Strategy | Sharpe | CAGR | MaxDD | cost | capacity | use-case |
|---|---|---|---|---|---|---|
| **A. Low-Vol + Momentum** (best survivor) | 0.79 | 13.3% | −25% | 8.3% | ₹190 cr | active equity, smaller drawdown than the index |
| **B. Pure Low-Vol** (smoothest) | 0.78 | 9.6% | −23% | 5.4% | ₹168 cr | capital preservation / lowest volatility |
| **C. Risk-Adj Momentum** (aggressive) | 0.51 | 10.2% | −43% | 15.1% | ₹97 cr | hot names; needs careful execution; big drawdowns |
| Nifty 500 buy & hold (**the bar**) | **0.89** | 15.3% | −29% | 0% | ∞ | the honest default — none above beats it on Sharpe |

**None beats the index on Sharpe** — so the choice is a *risk-profile preference* (smoother ride / more aggressive),
not an alpha claim. Holdings are regenerable any time via `strategy_menu.py`.

---

## Decisions on record

1. **RISKADJ (and QUAL_MOM) are KEPT as the internal benchmark.** Not productized for clients, not
   killed. Every future strategy is measured against Sharpe 1.13 / 28.6% CAGR. `factory.py` now
   persists the leaderboard on every run.
2. **Tier-2 swing book is PARKED** with reason (no survivor net of realistic cost) — kept for the
   validated "Launchpad" pattern and the cost-fragility lesson.
3. **Experiment DONE (2026-06-24, see section above):** relative gate beat the static floor (Sharpe
   1.13→1.29); PIT quality overlay cut drawdown (−42%→−29%) at Sharpe 1.18 — first proof a proprietary
   lens adds risk-adjusted value. **Candidate strategy = variant D.** Still gated on: per-name slippage/
   capacity costs, and adding MEP-accumulation + concall-credibility to the overlay.
4. **Standing rule:** no absolute-rupee thresholds anywhere (see the gate fix). Percentages and
   cross-sectional ranks only.
