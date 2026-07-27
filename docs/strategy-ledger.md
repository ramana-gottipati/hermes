# Strategy Ledger — what we've tried, what it scored, what we decided

> ## 🔴 READ BEFORE QUOTING ANY NUMBER ON THIS PAGE — every "Sharpe" here is a RETURN/VOL RATIO (D142, 2026-07-15)
>
> **The estate-wide audit is settled and unanimous: this project has never computed a Sharpe ratio.**
> Every figure labelled *Sharpe* in this ledger — RISKADJ **1.13**, the C-BLEND **1.32**, LOWVOL_MOM
> **0.79/1.02**, PEAD **0.10**, the Nifty-500 **0.89** hurdle, all 32 leaderboard rows — is
> `mean/sd × √periods` with **no risk-free rate subtracted**. That is a return/vol ratio, and it reads
> **high** against a textbook Sharpe (~1.7× on the rotation books, where it was reconciled exactly).
>
> **This changes no verdict and invalidates nothing below.** Every hurdle is computed on the identical
> basis — the 0.89 bar included — so both sides of every comparison carry the same omission and **every
> RELATIVE claim holds exactly as written**. Only the ABSOLUTE levels were overstated, and only a number
> quoted against an OUTSIDE Sharpe would mislead. Ramana's ruling (D139, extended estate-wide by D142):
> **relabel, numbers unchanged.** The dated entries below are left as the historical record rather than
> rewritten — **read every "Sharpe" in them as "return/vol ratio".**
>
> Two things worth carrying: **①** every **Deflated-Sharpe** result recorded here (MEP's DSR 0.45→0.36,
> the momentum gates) is an **UPPER BOUND on the evidence** — the DSR's null is rf-free by construction,
> but the observed ratio fed to it is inflated, so the test asks *"does it beat ZERO"*, not *"does it beat
> cash"*: a PASS is weaker than it looks, a **FAIL is real** (so the recorded failures stand, if anything
> more firmly). **②** The true-Sharpe re-cut needs a primary-source rf ingest (Guardrail #8) and is
> **queued with the owed TR-benchmark re-cut, which moves the same figures** — `attribution.py` is the one
> place already unblocked (it has a primary-source rf and simply doesn't feed it to its ratio).
>
> *(D139 disclosed this for §§15…15h only; D142 read every compute site in `research/` and found it
> universal. New prose may not call these "Sharpe" — enforced by `tests/test_retvol_label_gate.py`.)*

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

## ❌ BLOCKING FAILURE MODELS — read before proposing any factor/strategy (2026-07-02)

Ramana's standing rule: **failures are remembered so we never re-walk a dead road.** If a proposal
matches one of these, it is BLOCKED until it beats the recorded number *net of realistic cost*. Cite
the exact figures; do not silently re-attempt. (Mirrored in memory `failure-models-ledger`.)

| Failure model | Recorded result (2012-26, top-25 monthly, vs Nifty 500) | Why it blocks |
|---|---|---|
| **BOOK_YIELD (deep value / B-P)** | return/vol 0.61-0.63 · **alpha −1.8%…−2.2% (NEGATIVE)** · **beta 1.54-1.56** · **MaxDD −82%** · fails BOTH halves | Negative alpha + −82% drawdown + high beta = a value-trap engine. **Never a production long-ranker.** The β≈1.54 + MaxDD≈82% alone stop us. |
| **EARN_YIELD (cheap on P/E)** | return/vol 0.70 · alpha +0.4% · MaxDD −71% | No index-beating edge standalone; deep drawdown. |
| **QUALITY standalone** | return/vol 0.76 · alpha ~0.0% · fails halves | Quality doesn't rank returns alone; only helps *attached to momentum* (QUAL_MOM). → C is a veto/filter, not a ranker. |
| **Momentum sold as a FUNDABLE strategy** | GROSS return/vol 1.29 → **NET ~0.09, CAGR negative, MaxDD −69%** under realistic cost (~36%/yr, ~100%/mo turnover) | The headline return/vol is a flat-cost illusion. Nothing beats Nifty-500 buy-&-hold (0.89) net of realistic cost. Momentum = a **gross selection/analytical lens**, not net alpha; any fundable form must be low-turnover (and is then defensive, not alpha). |
| ACCEL / PULLBACK / DELIV_MOM (standalone) | return/vol 0.42-0.85, MaxDD −44%…−70% | Short-thrust chasing / dip-buying / delivery% added no standalone edge. |
| MEP-accumulation as alpha | Deflated-Sharpe DSR 0.45→0.36 when added | Descriptor-only; adds nothing. Do not re-test as alpha. |
| **PEAD tradeable book (event-time, 2026-07-05)** | ALL constructions fail: trailing net return/vol **0.10**, no-delivery 0.02, **within-season 0.06** (pre-registered), HEDGED **−0.58**, 1.5× cost −0.32 — vs bench 0.85, both halves | Event drift is REAL descriptively (A-study SUE-Q5×DELIV-T3 CAR60 +7.62%, t_cohort 1.92) but no wrapper survives real-time ranks + costs + compounding; the within-season variant (the last untested cell) also failed. Descriptive event lens only (`pead_surface.py`). Do not re-attempt any PEAD book without beating these exact numbers under the same no-leak harness. |
| **Accumulation-footprint detector v1 (2026-07-05b)** | pre-registered gate **FAIL 1/4** (only trade-size cleared δ≥+0.20 vs both controls: +0.329/+0.250); 764/947 episodes had NO pre-public window (SEBI PIT T+2); n=54 usable | "Front-detect the insider from the tape" is structurally near-impossible in India at filing granularity. deliv_per showed ~no case elevation (δ≈+0.07) — consistent with MEP's alpha failure. Survivor: avg-trade-size ratio = descriptive column only. Follow-ups (campaign arcs E-04, disclosure drift E-03) require fresh pre-registration. |
| CCI credibility as a factor | Spearman ≈0; HIGH−LOW excess −10% @12m (inverse, survivorship) | FALSIFIED as a factor → descriptive/veto only. |
| **C-BLEND 50/50 as a FUNDABLE book (2026-07-05c)** | Flat-cost return/vol **1.32** (recorded champion) → participation-cost **NET 0.52 @Rs25cr · 0.17 @Rs50cr · −0.30 @Rs100cr**; beats the index at NO AUM; H2 (honest window) 0.70 @Rs50cr < 0.89; ann cost 22%→86% | The 1.32 was **flat-cost only**. Monthly rebalance × mid-cap tilt (median capacity ~Rs38cr) makes Almgren participation impact fatal; the RISKADJ core is worse. C-BLEND stays a **descriptive/paper overlay** (D66 fence holds), never a fundable book. Only participation-fundable corner = quarterly large-cap **LOWVOL_MOM** (1.02 @Rs50cr, ~Rs100cr ceiling). Re-cost: `cblend_cost_recut.py`. |
| **MOMENTUM BAND + RSI single-name swing (2026-07-22)** | Upper-band breakout entry (T=EMA5(HLC3) > EMA13(high)) + RSI/2-fractal managed exit, pre-registered `0e90bf2c`, 45,131 events / 124,832 trades 2012-26: EVENT median 22d excess **−0.90%**, Cliff's δ vs placebo **−0.012** (FAIL-null, negative both halves); BOOK net return/vol **0.53** (h1 0.19 / h2 0.87, both <0.89), raw CAGR 19.4% → **net 8.4%** (cost −11pp) | The "buy strength" edge of the STREAM BAND band is ALSO an anti-signal; RSI-as-stop churns (phase-1 hair-trigger, 94% exits, 5-bar hold) and the RSI-80 partial *hurts* (−0.25pp mean = profit-taker law again, 07-14e). Beats random-entry (+0.20) but nowhere near fundable. Full entry: § Study 2026-07-22; cites 07-13/14b/14c/14d/14e. |

*(**Label corrected 2026-07-27** — the ratios in the rows above read **return/vol** (`mean/sd × √periods`,
no risk-free rate subtracted, D142). Only the LABEL moved: every number, every verdict and every blocking
reason is exactly as recorded on 2026-07-02. This table is doctrine that surfaces quote live — not a dated
session record — so it is relabelled rather than left to be read through the banner. Its byte-verbatim
mirror `rule_lab.BLOCKING_ROWS` was re-derived from this file in the SAME commit; `tests/test_rule_lab.py`
byte-compares the pair. "Deflated-Sharpe" in the MEP row is Bailey & López de Prado's named statistic and
stands.)*

The corollary (the doctrine these failures prove): **price strength is the only gross forward-return
engine; value/quality/credibility/accumulation are veto/filter/context layers, not rankers; and no
factor here is a fundable net-of-cost alpha vs the index.** The asset is PIT rigor + under-covered data
+ the analytical selection lens — not a backtested alpha strategy.

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

**⚠️ D5-F1 (Codex review, VPS-verified 2026-07-14) — same-close execution optimism.** The recorded flat-cost RISKADJ **1.13** also carries a ~0.04 same-bar-execution peek (selection features are read on the rebalance close *and* the forward return enters at that same close). The honest 1-day-lag number is **1.09** (QUAL_MOM 1.08→1.04, LOWVOL_MOM 1.00→0.97 similarly). **Minor / not result-changing** — the participation-cost model already collapses these to <0.2, so the fundability verdict is unchanged; only the flat-cost gross Sharpes are ~0.04 optimistic. Code fix = enter `i0+1` in `factory.py` / `overlay_experiment.py` / the cost recuts. Full verification: `docs/codex-review/TRACK-C-RESULTS.md` §D5-F1.

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
| F&O OI / participant positioning | FII/DII/Pro/Client long-short + per-stock quadrant/PCR/OI/max-pain | deployed (descriptive); board `/dash/fno` ranks each read vs the stock's own history. **Phase-0 gate (2026-07-24, 2024-07→now, 273 stocks): PCR SELECTS** (δ0.061, both halves, forward-test-only); maxpain-dist/basis/OI-chg FAIL. Still descriptive-only until the full DSR gate. |
| Wolfe / Ignition / theme tags | geometry / ML challenger / classification | **Wolfe: winner-profile RETURN-TESTED → BULL *selection* edge / BEAR fails the primary OOS bar, descriptive-only (OOS re-validated 2026-07-11 — see § below)**; Ignition / tags built |

---

## Wolfe winner-profile — BULL *selection* edge / FAILS as a book; OOS RE-VALIDATED 2026-07-11 under the D111 rebalance

The Tier-3 Wolfe lens's only return-tested claim is the **winner-profile selection filter** (`D≤1 · p1≥2 · F≤2` = reachable EPA + strong point-1 + not-narrowest zone), NOT the raw pattern. Original true-OOS derivation 2026-06-26 (fit 2004-14 → freeze → test UNTOUCHED 2015-26, + beta-control + placebo); **re-run 2026-07-11 under the CURRENT scoring** after the D111 §B rebalance + point-4 reconciliation (the June numbers predated the D108 fractal gate).

- **Verdict:** **DESCRIPTIVE-ONLY SCANNER, split by side.** **BULL = a real, regime-robust long *selection* edge; BEAR = tail-only and now FAILS the primary OOS bar; the raw Wolfe trade and any mechanical book = REJECTED** (median −2% net; placebo-negative → the entry/stop/target craft SUBTRACTS value). A re-validated *score* is not a validated *strategy* — the edge is in *which name / direction / when*, not the trade-craft.
- **Numbers (test window 2015-26, current scoring):** unfiltered baseline medNet **−2.1%** → winner-profile ALL **+0.81%** (inclusive / survivorship-aware) · +1.86% (nifty500 sensitivity); **BULL +4.4%** (residual **α +5.07**, CI [+2.0,+7.3] excl 0; positive even when the market falls); **BEAR −0.98%** inclusive (regime-stripped **−2.1%**, decaying 2015-20→2021-26) → **inclusive verdict IN-SAMPLE-ONLY**, nifty500 SURVIVED (point-estimate, bear CI straddles 0). **Placebo-gap NEGATIVE everywhere** (ALL −1.7 · BULL −0.5 · BEAR −2.2). The 2004-14 fit **re-derives the IDENTICAL rule** (F 0-4 widening is neutral to the filter). **Softer than the June baseline** (winner +2.14%→+0.81%, BEAR +1.03%→−0.98%, n 1787→1591) — attributed (A/B-MEASURED) to the **D108 mandatory fractal gate** (removed ~⅓ of waves), NOT the rebalance and NOT point-4 (`_reconcile_point4`-disabled = +0.78% ≈ +0.81% enabled).
- **Provenance:** `research/wolfe_waves/phase2_oos.py` + `phase3_betacontrol.py` (isolated, read-only; live VPS Nifty-500 archive, survivorship-inclusive PRIMARY + nifty500 sensitivity; bootstrap CIs, sub-era split, leak-neutralized `D_pit`). Folded into `docs/strategies/wolfe-wave.md` §4+§8 (`2545a91`), PROJECT_STATE D111 block (`3c54c8a`), memory `[[wolfe-wave-strategy]]`.
- **Supersedes:** the 2026-06-26 "survived true OOS (+2.14% / bears +1.03%)" numbers carried in the Wolfe docs — those predate the D108 gate. The **BULL selection edge and the selection-not-craft (placebo-negative) finding HOLD**; the BEAR "survived" is **downgraded to fails-the-primary-bar**. **Do NOT re-attempt a Wolfe trading book without first beating these numbers under the same PIT harness** (same class as PEAD-delivery / harmonic — a descriptive event/geometry lens, not a fundable book).
- **New surface, same fence (S121, D120/D121):** the "Open trades — remaining ROI" view (`/dash/markets/wolfe → Open trades`) presents OPEN winner-profile setups ranked by run%/risk%/R:R from CMP — **descriptive-only, adds NO new validated claim**. The **validated +edge above applies ONLY to fresh ≤15d entries** (badged ✓edge); older open trades carry run left but **NO validated entry-edge** (badged "open · judge the run") and are age-capped at 1yr + EPA-fenced (D121). It is a scanner/shortlister, not a book — the ledger verdict is unchanged.

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

**HEDGE-DENSITY lexical drift (2026-07-12, AI-pattern-engine slice 1) → NULL; pre-registered (hash `538a08a8`, hashed BEFORE the run).**
First live test of the propose→gate→surface engine. DETERMINISTIC hedge/uncertainty word-density per transcript
(Loughran-McDonald weak-modal+uncertainty lexicon, NO LLM → no look-ahead leak), differenced WITHIN each name vs its
own prior-3-call baseline — deliberately clearing the breadth wall (16,140 calls / **1,573 symbols** vs CCI's 377 and
content's ~44) and the covered-name-drift null that killed `concall_intent`. Hypothesis: a within-name hedging SPIKE
precedes 60d UNDERperformance vs Nifty 500. **FALSIFIED on every gate leg** (spike n=2,684): mean CAR60 **+1.50%**
(WRONG sign — predicted negative), cohort-t **+0.47** (needed ≤ −2), both halves POSITIVE (+2.4% / +1.4%),
Cliff δ(spike,drop) **+0.03** (needed ≤ −0.10). Placebo not reached (failed stage 1). ⚠ naive t was **+4.22** —
same-quarter clustering; `evlib.cohort_t` collapses it to 0.47, i.e. the gate CAUGHT a backwards false positive a raw
t-test would have sold. **Do NOT re-mine concall hedging-language as a return factor** — deterministic lexical tone
carries no forward signal at 60d. Verdict `FAIL-null-published`. Reproduce: `python -m explosive_moves.hedge_density
--build && ... --run`; feature cached in `research.db.concall_lexical`, gate frozen in the module docstring.

**↳ DATA REVIEW (2026-07-13) — verdict UNCHANGED; reported n's corrected; feature re-characterized.** A joint
code+data review (external reviewer + 2-seat internal panel + read-only VPS diagnostics) re-examined this null.
**FAIL-null stands, and is *especially* informative: the feature was biased toward finding a language effect and
still failed the return gate.** Honest-reporting corrections (none change the verdict):
- **Breadth:** within-name deltas need ≥4 calls → **1,097 delta-eligible symbols** (NOT the 1,573 corpus symbols;
  spike cohort ≈ 700-900 distinct). **Distinct calls = 15,824** (NOT 16,140 — that counted pre-collapse transcripts;
  316 same-date re-uploads collapse).
- **Construct validity:** hedge_density is dominated by 5 ubiquitous modals (would/should/may/could/maybe = **64.7%**
  of all LEX hits vs a **2.4%** genuine-uncertainty register), so it reads as within-name **seasonal/modal
  conditional-language density, NOT "conviction erosion."** The SPIKE tercile is **50-59% Q2 (Apr-Jun, FY-end
  guidance season) calls every year** vs a 33% baseline — the "spike" is largely guidance-season conditionality; the
  cohort-t gate correctly collapsed the naive t (+4.22 → +0.47) this clustering induces.
- **Provenance:** 98% Screener-sourced (Guardrail #8) — no promotion beyond the VPS until a primary NSE/BSE/XBRL
  corpus. Source did NOT bias density (screener 0.01142 vs bse-ann 0.01139).
- **Robustness caveats (do not change, if anything harden, the null):** right-censoring drops the dense 2026 slice
  from CAR60 (needs ~85 fwd days); the fixed half-split sits at ~the 20th event-percentile (median event ~2023-12) →
  low-power both-halves leg; **potential** concalls-coverage survivorship (UNMEASURED — the bhavcopy price archive
  likely retains delisted series, so the risk is coverage of dead names, not the price series).
- **Data quality:** 10 zero-hedge feature rows = 8 short truncated stubs + 2 mis-filed non-transcript docs (INTELLECT,
  TRACXN) — exclude in any successor.
- **Prereg hash `538a08a8` CONFIRMED tamper-clean** (VPS `prereg.py --verify` = OK; an earlier "drift" scare was an
  `ast.get_docstring(clean=True)` dedent artifact — always hash the RAW `__doc__`).
- **Correctness fixes (2026-07-13):** placebo-cohort match, feature PK→(symbol,concall_dt)+keep-fullest dedup,
  rank-disjoint terciles, DB-handle try/finally, partial-cache refuse — all were DEAD CODE in the failing run, so the
  verdict is unchanged; a rebuild+re-run on the new PK grain re-syncs the n's (~5 distinct calls appear / 316 collapse
  on date, not label).
**Any feature change (lexicon/weighting/negation/de-dup/outcome) = a NEW pre-registered study (`hedge_density_v2`,
realized-VOLATILITY outcome not return, quarter-adjusted double-difference), NEVER an edit to this frozen null; v2
must cite this ledger (every prior event-wrapper net-failed 0.02-0.10 vs 0.85; `concall_intent` placebo-killed).**

**HEDGE-DENSITY V2 — net-uncertainty → forward realized-VOLATILITY (2026-07-13) → NULL; pre-registered (hash `632bd149`, registered BEFORE the run; git `62ea68b`/`8ce1f0e`; `--verify` tamper-clean).**
The v1 successor (Ramana-greenlit). Fixes every v1 defect: register-split **net-tone** score (uncertainty − confidence
per 1k tokens; weak modals ZERO-weighted, "may" dropped; bigram-first span consumption; negation suppression),
**within-name × within-CALENDAR-QUARTER double-difference** (removes v1's Q2 seasonal confound → 7,390 deltas, spike
symbols 518), and the outcome CHANGED to **forward-60-session idiosyncratic (excess-return) realized-vol uplift**
(`ln(fwd_vol/prior_vol)`) — the more plausible "management uncertainty → outcome uncertainty" target. **FAILED at gate
leg 1:** SPIKE mean vol-uplift **−0.0084** (needed >0), cohort-t **−0.43** (needed ≥ +2); DROP −0.0191; **both halves
negative** (h1 −0.013 / h2 −0.004, opposite t-signs); Cliff δ(spike,drop) **+0.001** (no distributional separation).
Placebo not reached (failed leg 1). ⚠ The ONLY echo of the construct: SPIKE sits marginally ABOVE DROP (+0.011 log-vol,
the predicted direction, absent in v1's modal register) — but both cohorts see forward vol DECAY (post-earnings
mean-reversion vs the pre-call window), the spike is absolutely negative, and Cliff≈0, so it is a whisper, not a signal.
**Do NOT re-mine concall tone (return OR volatility) as a factor** — deterministic lexical tone carries no certifiable
forward signal at 60d on either outcome, exactly as the failure-ledger predicted (event-wrappers net-fail). Verdict
`FAIL-null-published`. Reproduce: `python -m explosive_moves.hedge_density_v2 --build && ... --run`; feature
`research.db.concall_lexical_v2`; gate frozen in the module `__doc__` (registered `632bd149`).

---

## Study 2026-07-15 — SECTOR-ROTATION (relative-strength, sector-INDEX level) — CONDITIONAL: low-turnover quarterly long-only BEATS passive (+2.8% alpha, cost-surviving) but not the strict 0.89-both-halves bar; short/F&O leg REJECTED

> ### 🔴 READ BEFORE ANY NUMBER IN §§ 2026-07-15 … 2026-07-15h
>
> **1. SCOPE (§15h).** This ladder selects **SECTORS, never STOCKS.** Every stat below measures the
> sector-selection half of an unfinished brief, priced on instruments that in ~6 of 16 sectors do not
> exist. **No number here may be presented, quoted, or promoted as a complete strategy result.**
>
> **2. "Sharpe" IS THE WRONG WORD (§15i).** Every figure labelled *Sharpe* in §§15…15h — and on the live
> page — is a **RETURN/VOL RATIO**: the engine computes `mean/sd × √12` and subtracts **no risk-free
> rate**. Verified by reconciliation (V21 = 16.57% CAGR ÷ 19.92% ann vol = 0.875). True excess-of-6.5%
> Sharpes are **~0.51 / 0.54 / 0.54**, not 0.875 / 0.911 / 0.898. **Benchmarks use the identical basis, so
> every RELATIVE claim below holds exactly as written; the ABSOLUTE levels are overstated ~1.7× by the
> label alone.** Ramana 2026-07-15i: **relabel, numbers unchanged.** The dated sub-entries below are left
> as the historical record rather than rewritten — read every "Sharpe" in them as "return/vol ratio".
>
> **3. THE RUNGS ARE NOT DISTINGUISHABLE (§15i).** V24-vs-V32 is **unmeasurable** on this window (gap
> 0.013 vs a 0.148 noise floor); V24-vs-V21 is method-dependent and dies under a measured-fair k=9
> selection correction. Ramana's V24 designation stands on **mechanism** grounds, not evidence.

Ramana-directed sector-rotation RS strategy: long every NSE sectoral index beating Nifty 500 on
trailing RS, weighted strongest→weakest; RSI-green entry gate; short the underperformers (F&O);
hold while momentum persists. Tested at the SECTOR-INDEX level (V1 — isolates the rotation edge
before the ≤40-stock constituent build) on `index_rows` (16 NSE sectoral indices, 11 live from
2012-02, monthly marks 2012–2026, n=173). Module `research/explosive_moves/sector_rotation.py`
(reproduce read-only on the VPS: `.venv/bin/python research/explosive_moves/sector_rotation.py data/hermes.db`).
⚠ Benchmark = a CONSISTENT price-index Nifty 500 (this method: **Sharpe 0.78 / CAGR 12.1%** on
`index_rows`); the ledger's 0.89 / +14.6% is the **TOTAL-RETURN** Nifty 500 and `index_rows` are
PRICE indices, so judge the strategy like-for-like vs **0.78**, not 0.89.

- **CHAMPION — long-only, QUARTERLY, 6mo-RS, RSI-green gate, hysteresis band 8%, cap 30%, cost 0.15%/side:
  Sharpe 0.83 (H1 0.78 / H2 0.87), CAGR 14.1%, MaxDD −35.7%, beta 0.95, ALPHA +2.80%/yr, turnover 17.5%/mo.**
  BEATS passive Nifty 500 like-for-like (+0.05 Sharpe, +2.0% CAGR, +2.8% cost-surviving alpha) — the
  strongest RS-rotation construct recorded — but does NOT clear the strict **0.89-TR-both-halves**
  survival bar (H1 0.78). Verdict class: a legitimate LOW-TURNOVER SMART-BETA / enhanced-beta tilt
  (same family as LOWVOL_MOM), NOT decisive standalone alpha.
- **The knobs that mattered (his design intuitions, validated):** (1) CADENCE — quarterly (17.5%/mo
  turnover) Sharpe **0.83** vs naive MONTHLY (76.6%/mo) **0.66**: the momentum-net-of-cost wall bites at
  high churn, exactly the ledger's 1.29→0.09 pattern; (2) HYSTERESIS (hold-band 8%) cuts turnover
  25.7%→17.5%/mo and lifts alpha; (3) the RSI-GREEN entry gate is additive (alpha −0.30% vs no-gate
  −2.08%; beta 0.83 vs 1.03).
- **SHORT / F&O leg REJECTED:** a +30% short book on underperformers DROPS Sharpe to **0.49** (alpha
  −1.02%); +50% worse. Confirms the recorded wall — shorts fight market drift (cf. BEAR-mirror −1.53;
  STREAM-BAND SELL "not a short signal"). Sector rotation is a LONG-ONLY tilt.
- **Capacity note (structural advantage vs stock momentum):** sector legs trade via liquid ETFs/futures,
  so ~0.15%/side is realistic — NOT the small-cap slippage that killed stock momentum (1.29→0.09) and
  C-BLEND (1.32→0.52@₹25cr). The sector level is inherently more capacity-/cost-friendly.
- **Verdict: CONDITIONAL — long-only + quarterly + RSI-gate + hysteresis beats passive at low turnover
  with +2.8% cost-surviving alpha; short leg REJECTED; short of the strict survival bar (price-vs-TR
  caveat).** Next rigor: (a) formal alpha t-stat + participation-cost recut; (b) V2 = ≤40-stock
  constituent expression (top-RS stocks inside the champion sectors) for a tradeable book + model-portfolio
  integration. Supersedes nothing; strongest entry in the RS-rotation family.

### 2026-07-15b — INCREMENTAL ablation (Champion FROZEN base + Ramana's levers, one at a time, OLDEST data 2005–2026, n=258)
Harness `research/explosive_moves/sector_rotation_exp.py`; holdings sheet `research/explosive_moves/out/sector_rotation_sheet.csv`.
Longer window (incl. the 2008 GFC) → tougher: benchmark Nifty500(price) **Sharpe 0.64, CAGR 12.5%, MaxDD −62%**; Champion base **0.62, alpha +1.7%, MaxDD −40.7%**.
Each lever added individually vs base (Sharpe / alpha / MaxDD):
- **WINNERS (add alpha AND cut drawdown — Ramana's "offload the burnt-out leader" thesis, CONFIRMED):**
  BAL balanced/equal-weight **0.64 / +1.8% / −39.5%** · RSPK taper-at-own-RS-peak **0.64 / +1.9% / −39.8%** ·
  STR taper-when-stretched **0.65 / +2.1% / −40.2%** · RSIRS RSI-of-RS-overbought-exit **0.64 / +2.3% / −40.3%**.
- **NO-LIFT (honest negatives):** VOL volume-confirm **0.62** (sector-index volume carries no signal — it's a
  constituent/DVPT lever, not index-level) · NEW fixed newcomer-boost **0.62** (BAL captures the "don't over-weight
  the leader" goal better) · STDV excess-stdev-taper **0.62** alone (helps only inside the cluster).
- **★ WINNER COMBO (V8 = BAL+RSPK+STR+RSIRS): Sharpe 0.70 (H1 0.78 / H2 0.64), Δ +0.07 vs bench, ALPHA +3.2%/yr,
  MaxDD −36.2%** — best Sharpe AND lowest drawdown; lifts base 0.62→0.70 and repairs the recent-half (H2 0.51→0.64).
  Tapers-only cluster (RSPK+STDV+STR+RSIRS) = 0.67 / +2.8% / −38.1%.
- **The −36% MaxDD is the 2008 GFC** (a −62% market) — for LONG-ONLY equity that is unavoidable; ex-2008 drawdowns
  are modest and the tapers nearly HALVED the crash. Diagnostic noted: the 30%-cap + narrow-breadth periods (e.g.
  2024 = PSU-Bank only) leave the book UNDER-invested (residual → cash) — next lever to test = fill residual with the index.
- **Verdict: the taper/balance levers materially improve the Champion (0.62→0.70, +3.2% alpha, −36% DD).** V8 is the
  new working config on top of the frozen base; still a smart-beta tilt (short of the strict TR bar), now with better
  drawdown control. Levers are additive + individually recorded so the estate can keep refining.
- **⚠ CORRECTION (2026-07-15c, dated stats):** the "−36% MaxDD is the 2008 GFC" line above is WRONG — V8's max
  drawdown is **COVID** (peak 2019-06 → trough 2020-04 −36.2% → recovered 2021-01), where V8 fell MORE than the
  bench (−36.2% vs −31.9%; the quarterly clock froze the Jan-2020 book through a one-month crash). In the GFC V8
  fell −32% vs bench −62% (calendar-2008: −23.3% vs −58.8%). Full dated stats + t-stats:
  `research/explosive_moves/sector_rotation_stats.py` (alpha t 1.45 NOT significant · IR −0.20 · hit 44.6% ·
  up/down-capture 0.71/0.64 · avg exposure 74.9% — the wealth gap ₹9.13 vs ₹12.60 Cr is CASH DRAG, missing the
  recovery years: 2009 +44% vs +106% · 2014 +24% vs +44% · 2024 +6% vs +26%).

### 2026-07-15d — Round 3: the V18/V19/V20 batch vs the frozen V17 benchmark → ★V21 (all three levers) — the FIRST construct to beat the bench in BOTH halves

Ramana greenlit the ranked batch ("go"). Module `research/explosive_moves/sector_rotation_exp3.py`; V17 frozen as the
family benchmark (0.79 / 14.7% / −39.2% / ₹19.04); every lever tested ALONE first, then the winners combined. Data
finding first: our archive has NO total-return indices (TR re-cut still OWED — needs an NSE TRI ingest) and mid-cap
indices only from 2012/2015 — **Nifty Next 50 is the one aggressive asset with full 2004+ history**.

| V17 + lever | Sharpe (H1/H2) | CAGR | MaxDD | α/yr | ₹1 Cr → | read |
|---|---|---|---|---|---|---|
| — (V17 baseline) | 0.79 (0.86/0.70) | 14.7% | −39.2% | +4.7% | 19.04 | benchmark |
| V18a sleeve→Next 50 | 0.79 (0.88/0.69) | 15.2% | −40.8% | +5.1% | 20.95 | +₹1.9 Cr for −1.6pt DD; mild win |
| V18b sleeve→Midcap 50 (2012+) | 0.79 (0.83/0.74) | 14.9% | −39.2% | +4.8% | 19.70 | mild |
| **V19 recovery-accelerator** (bench reclaims 200DMA during the quarter → that build's NEW-entry band 8%→0; RSI-green kept) | **0.85 (0.86/0.83)** | 15.9% | −39.2% | +5.7% | 23.73 | **the star single lever — FIXES the H2 weakness** (0.70→0.83) by catching the V-recoveries it was built to catch; turnover 12.4→15.4%/mo |
| V20 inverse-vol weights | 0.80 (0.87/0.71) | 14.9% | −39.2% | +4.9% | 19.77 | small clean win |
| V18a+V19 | 0.85 (0.88/0.82) | 16.2% | −40.8% | +5.9% | 25.18 | additive |
| **★ V21 = V18a+V19+V20** | **0.87 (0.89/0.86)** | **16.6%** | **−40.8%** | **+6.3%** | **27.02** | **new leading candidate** |

- **V21 beats the like-for-like bench in BOTH halves decisively** (0.89/0.86 vs the bench's 0.58/0.78) — the first
  sector-rotation construct to clear the both-halves bar on this window — at ₹1 Cr → **27.02 vs 12.60 (2.1×
  the index's wealth)**, MaxDD −40.8% vs −62.0%, turnover 14.6%/mo. Each lever was individually pre-specified from
  the recorded diagnosis and individually positive before combining (not a grid point).
- **Reference rows (the engine beats its own ingredients):** Next 50 B&H 0.62 / −69.9% / ₹15.99 · Midcap 50 B&H
  0.65 / −62.0% — both far below V21; the discipline, not the aggressive asset, carries the result.
- **T+1 EXECUTION-LAG recut (the practical fence, run 2026-07-15e):** signals at close, fills at the NEXT day's
  close — V17 0.79→0.78 / ₹18.56 · **V21 0.87→0.87 / ₹26.00** (−3.8% of terminal wealth over 21y; DD −39.7%).
  **The edge survives next-day execution essentially intact** — it lives in month-scale rotation, not in the close.
- **Caveats unchanged and compounding:** price-index (TR re-cut OWED — no TRI in `index_rows`); three rounds of
  selection on one window → the fresh-window / TR confirmation is now the HIGHEST-priority rigor item before any
  stronger claim. **Status: V21 = leading champion-candidate, pending Ramana's ratification; V17 remains the
  recorded prior candidate; V8 remains the frozen base.**

### 2026-07-15f — Round 4: the V22..V30 batch (Ramana's own catalog) vs BOTH V21 and V17 as bases → ★V32 = V21+own-percentile-RSIRS+adaptive-band, the new leading candidate

Ramana's naming-collision cleanup + full catalog from the RSI-of-RS design discussion, tested one lever at a time
against V21 (primary base) AND V17 (secondary — confirms an improvement is general, not narrowly synergizing with
V21's specific mix), then winners combined. Module `research/explosive_moves/sector_rotation_exp4.py`
(sanity-checked FIRST to reproduce V21 0.87/₹27.02 and V17 0.79/₹19.04 exactly before trusting any new number).

| V21/V17 + lever | V21 Sharpe (H1/H2) | V21 CAGR/MaxDD/₹1Cr | V17 Sharpe (H1/H2) | Verdict |
|---|---|---|---|---|
| — (bases) | 0.87 (0.89/0.86) | 16.6% / −40.8% / 27.02 | 0.79 (0.86/0.70) | — |
| **V24 own-percentile RSI-of-RS** (85th trims/95th exits, that sector's OWN trailing-756d history, replacing fixed 70/80) | **0.91 (0.92/0.91)** | 17.2% / **−37.7%** / 30.35 | **0.82 (0.89/0.74)** | **★ Strong win — best single lever; most balanced halves of the whole batch** |
| V26 persistence (2 consecutive quarters before acting) | 0.88 (0.91/0.85) | 16.9% / −40.8% / 28.75 | 0.79 (0.87/0.71) | Small clean win ALONE; turnover ↓ |
| V22 adaptive hysteresis band (±band = 1×own trailing RS-line vol, replacing fixed ±8%) | 0.87 (0.92/0.83) | 17.0% / −41.3% / 29.43 | **0.83 (0.93/0.72)** | Positive, esp. on V17 (closes much of the V17→V21 gap on its own) |
| V29 size-segment satellites (+CNX Midcap, +Midcap 50) | 0.87 (flat) | +0.1pt CAGR / flat DD / 27.62 | 0.79 (flat) | Marginal — turnover ↑ roughly offsets the gain |
| V25 longer RSI-of-RS window (n=50/90d vs n=14/40d) | 0.85 | 16.4% / −43.9% / 26.04 | 0.77 | REJECT — smoother = slower = worse DD, both bases |
| V27 dual-benchmark (must clear vs Nifty 50 AND Nifty 500) | 0.85 | 16.1% / −45.0% / 24.80 | 0.76 | REJECT — the AND-condition under-protects, both bases |
| V28 regime-band (ride ≥45 after crossing 55, exit <45) | 0.82 | 15.8% / −43.9% / 23.46 | 0.74 | REJECT — **confirms the single-sector Defence diagnostic** (below) **at full-portfolio scale** |
| V23 direction-of-trend entry/exit (2-qtr deceleration/acceleration as an extra trigger) | 0.79 | 15.1% / −44.0% / 20.40, turn 18.0% | 0.79, turn 17.1% | REJECT — turnover +3–5pt with no offsetting return, worse DD both bases |
| V30 book-level vol-targeting (scale exposure to a 15% vol target) | 0.78 | 17.9% / **−50.8%** / 34.61 | 0.67 / **−53.6%** | **REJECT — worst drawdown blowup in the batch** (higher CAGR, but levers up right before vol spikes; fails "keep drawdown in check") |

- **The V28 preliminary signal, reproducibly:** before this batch, a standalone single-sector diagnostic
  (`research/explosive_moves/defence_rsirs_diagnostic.py`, read-only, isolates the RSI-of-RS mechanism on
  Nifty India Defence — the strongest real-world sustained-trend example, 2022-01→2026-07, 18 quarterly
  checkpoints) showed the SAME regime-band idea (ride ≥45 after crossing 55, exit <45) capturing only
  **51% of the buy-and-hold ceiling (3.56× vs 6.92×)**, vs the current fixed-70/80 rule's **98.8% (6.84×)**
  — because Defence's RSI-of-RS never once crossed 80 in that window (max 76.9), so the existing rule barely
  fired, while the regime-band got whipsawed out right before the single largest quarterly move (+29.2% RS-
  excess in 2022-Q3). The full-portfolio V28 result above CONFIRMS this diagnostic held at scale, not just
  on one sector.
- **Combining the winners — a genuine NEGATIVE interaction found:** V24+V26 (0.89, DD back to −40.8%, ₹29.75) is
  WORSE than V24 alone (0.91, DD −37.7%, ₹30.35) — V26's "wait 2 quarters" delays exactly the faster reaction that
  makes V24 work; the two mechanisms fight each other. **V24+V22+V26 confirms it** (0.88, DD −41.3%) — V26 hurts
  regardless of what else is in the mix. **Lesson recorded: individually-validated levers do not always combine
  additively; test every combination, not just assume winners stack (the same discipline that built V21 already
  implied this, now proven with a concrete counter-example).**
- **★ V32 = V21 + V24 + V22 (own-percentile RSIRS + adaptive band, V26 excluded): Sharpe 0.90 (0.95/0.84), CAGR
  17.3%, MaxDD −37.9%, alpha +6.5%/yr, ₹1 Cr → 31.15 — the new leading candidate by wealth and CAGR.** On V17 alone
  the same two levers lift it to 0.86 (0.96/0.75), ₹25.99 — nearly matching plain V21's own performance.
- **Honest trade-off, NOT resolved by the numbers alone — V24 alone vs V32 (V24+V22):**
  | | Sharpe (H1/H2) | MaxDD | Alpha | ₹1 Cr |
  |---|---|---|---|---|
  | V21+V24 alone | 0.91 (**0.92/0.91** — most balanced in the whole project) | **−37.7%** (best) | **+7.1%** (best) | 30.35 |
  | V32 = V21+V24+V22 | 0.90 (0.95/**0.84**) | −37.9% | +6.5% | **31.15** (best) |
  V24-alone is the more robust, half-consistent construct; V32 trades a little H2 consistency and drawdown for more
  wealth and CAGR. **Neither dominates the other — this is a genuine preference call, not a numbers call.**
- **Verdict: CONDITIONAL. Two new leading candidates recorded — V21+V24 (robustness-favoring) and V32=V21+V24+V22
  (wealth-favoring) — both pending Ramana's ratification.** V21 and V17 remain the frozen/recorded reference points;
  nothing has been promoted to the live engine. Same standing caveats apply (TR benchmark owed; selection deflation
  now FOUR rounds deep — the fresh-window confirmation is more load-bearing than ever).

### 2026-07-16X - INVERSE-VOL candidate for the union: a WASH, does NOT earn a spec change. The sealed equal-weight spec STANDS. 2012-17 confirmed unreachable by any sizing lever.

**Ramana, 2026-07-16:** "run the inverse-vol variant as a candidate." Tested ONE change against the sealed
spec (16W) - equal-weight -> inverse-volatility stock sizing, everything else identical (union / top60 /
sleeve200 / trail-20% @1% slip). **Module:** `research/explosive_moves/cash_ivol.py`. Vol estimate is
stale-safe (rejects names not moving on >=60% of days, so inverse-vol cannot overweight illiquid junk - the
bug that tanked an earlier run to 1.71x). Motivated by 15P (the toll IS volatility) + V21's sector-layer
inverse-vol win, never before applied to the stock leg.

| union top60, sleeve200, full period | CAGR | MaxDD | Rs1Cr-> | beta | alpha |
|---|---|---|---|---|---|
| **EQUAL-WEIGHT (sealed spec)** | **17.5%** | -30.5% | **26.04x** | 0.87 | **+6.8%** |
| inverse-vol (candidate) | 17.0% | **-28.3%** | 24.06x | 0.86 | +6.3% |

**A LATERAL MOVE, net slightly WORSE:** -0.5pp CAGR, -0.5pp alpha, +2.2pp shallower drawdown. Gives up more
return than it buys in risk. **Does NOT earn a place in the spec - amending for a wash would add complexity
the data does not justify.**

**Walk-forward (the decisive test - built to fix the -4.6%/beta-1.56 2012-17 hole):**

| window | EW alpha | IV alpha | EW beta | IV beta |
|---|---|---|---|---|
| 2006-2011 | +9.8% | +9.9% | 0.77 | 0.78 |
| **2012-2017** | **-4.6%** | **-3.7%** | **1.42** | **1.32** |
| 2018-2026 | +8.3% | **+7.1%** | 0.91 | 0.91 |

**Every metric moved the way 15P's theory PREDICTED (beta down, DD down, worst window less bad) - the direction
is right, the MAGNITUDE is too small to matter.** 2012-17 alpha only -4.6% -> -3.7%, still a failed window; and
it costs 2018-26 alpha (+8.3% -> +7.1%). Unlike the throttle (16W, which moved things the WRONG way), inverse-
vol is directionally correct but weak.

**🔑 STRONGEST CONCLUSION: 2012-17 is UNREACHABLE BY ANY SIZING LEVER.** Two structurally-correct fixes aimed
at that window - the market-stretch throttle (16W) and inverse-vol sizing (16X) - both failed. This is now
firm evidence the failure is WHICH STOCKS the signal picks in a mid-cycle bull, NOT how they are weighted or
throttled. No exposure/sizing lever reaches it; only a selection change could, and that is a harder,
still-open research question (and must not be pursued by re-optimizing on this window).

**VERDICT: the sealed union spec (equal-weight, top60) STANDS UNCHANGED. Seal `a9a14058...` intact. The union
goes to forward testing exactly as pre-registered (16W). Inverse-vol recorded as a tested-and-rejected
candidate so it is not re-run.**

### 2026-07-16W - THROTTLE FAILED (the 2012-17 weakness is SELECTION not sizing) + the UNION PRE-REGISTERED for forward testing.

**Ramana, 2026-07-16:** "record this and test the throttle" then "pre-register the union for forward testing."
Both done.

## THROTTLE - DEAD. My 16V diagnosis was WRONG.

16V named the union's 2012-17 failure as "over-investment in an expensive bull (beta 1.56, 92% invested)." If
true, cutting exposure when Nifty 500 is stretched above its 200DMA should fix it. **Module:**
`research/explosive_moves/cash_throttle.py` - three throttles (linear/step/hard) scaling the invested fraction
down as the market extends, idle -> the sleeve.

| union top60, full period | CAGR | MaxDD | Rs1Cr-> | beta | alpha |
|---|---|---|---|---|---|
| **no throttle** | **17.5%** | -30.5% | **26.04x** | 0.87 | **+6.8%** |
| linear | 16.6% | -34.1% | 22.38x | 0.93 | +5.6% |
| step | 16.5% | -32.1% | 22.17x | 0.91 | +5.7% |
| hard (quarter-size above +15%) | 16.2% | -37.1% | 20.91x | 0.93 | +5.3% |

**EVERY throttle made it WORSE - lower return, HIGHER drawdown, lower alpha.** Decisively, in the 2012-17
window it was built to fix: the "hard" throttle (75% size cut in extended markets) moved beta only 1.42 ->
1.35 and alpha only -4.6% -> -4.1%. **Cutting the QUANTITY barely touched the beta => the failure was never
over-investment. It was SELECTION: in 2012-17 the signal picked high-beta names that underperformed, and the
market was not even stretched enough for the throttle to fire much.** Sizing cannot fix a bad book. **Do not
re-attempt exposure-throttling as the fix for 2012-17 - the problem is WHICH stocks, not how many.**

**What IS robust (across all 4 throttle settings): 2006-11 alpha +8-10% and 2018-26 alpha +7-8% in EVERY
configuration.** Only 2012-17 is negative regardless of sizing. The union genuinely works in 2 of 3 eras; the
one weak regime is a mid-cycle bull where a lower-beta momentum book lags a raging cap-weighted index.

## THE UNION - PRE-REGISTERED

The session produced ~30 configs; **exactly one beat Nifty Next 50 in-sample on return, drawdown AND beta
together - the UNION** (6b oversold-RS recovery OR RSI-price>50SMA+consistency70; equal-weight top60;
sleeve200; trail-20% @1% slip). But it was SELECTED after seeing 2005-2026 across many rounds, so 17.5% is a
LEAD, not proof (Codex 15R). **Pre-registration freezes the exact spec + pass/fail BEFORE any out-of-sample
data is seen**, matching the project's existing discipline (`prereg_registry`, "hashed BEFORE first run").
Research DB is read-only over SSH, so the seal lives in git.

**FROZEN SPEC + criteria: `docs/prereg/union-prereg.md`. SEAL sha256 = `a9a14058f2140e22639b9504ab6d4af9c60fc76144de0f9f5e47f21b1b98d21c`** (recorded here so any
later edit to the spec is detectable = registration void). **PASS requires, over >=8 forward quarters from
2026-07 on:** (1) CAGR > Next-50 net of costs; (2) alpha > 0 with forward beta reported (higher CAGR purely
from beta > 1.1 = FAIL); (3) MaxDD not worse than Next-50; (4) no single quarter > 60pct of the excess.
Miss 1-3 => DESCRIPTIVE-ONLY, never deployed.

**Standing: the union is the strongest lead of the session (17.5pct / +6.8pct alpha / beta 0.87 in-sample),
its one weak regime is correctly diagnosed as selection not sizing, the wrong fix (throttle) is eliminated,
and it now awaits its own forward evidence. Not deployed. Not advice. TRI-benchmark re-cut still owed.**

### 2026-07-16V - THE UNION (6b OR RSI-stack): BEST full-period result of the session (17.5%/+6.8% alpha) but NOT complementary where it counts - both fail the SAME 2012-17 bull regime.

**Ramana, 2026-07-16:** "test whether 6b and the RSI stack are complementary." Built the blend PLUS the
diagnostics that separate real complementarity from mere diversification (a blend can score well just from
averaging even when redundant). **Module:** `research/explosive_moves/cash_blend.py`. sleeve200 money-mode
(idle -> Next50 while Nifty500 >= 200DMA), CA-adjusted, quarantined, PIT, trail-20% @1% slip.

**DIAGNOSTICS - the split verdict:**
- **Selection overlap: 11%.** Per quarter ~54.9 RSI-eligible names, ~32.0 6b-eligible, only ~3.5 in BOTH.
  They pick DIFFERENT stocks (6b is a TURN signal, fires early; RSI+consist70 is a TREND signal, needs the
  move underway - mutually exclusive by construction, confirmed: the INTERSECTION collapses to 9% invested,
  CAGR 8.6%).
- **Return correlation: 0.79.** BUT their books MOVE TOGETHER - both are long-only momentum riding the same
  strong sectors via the same sleeve. Complementary in SELECTION, NOT in RISK. This 0.79 is the number that
  caps the whole result.

**THE BOOKS (sleeve200, vs Nifty Next 50 bar 13.3% / Rs12.98x):**

| config | CAGR | MaxDD | Rs1Cr-> | beta | alpha | avg inv |
|---|---|---|---|---|---|---|
| RSI+consist70 alone | 15.6% | -29.9% | 18.91x | 0.82 | +5.7% | 78% |
| 6b alone | 15.4% | -38.4% | 18.11x | 0.81 | +5.8% | 60% |
| **UNION top60 (either fires)** | **17.5%** | **-30.5%** | **26.04x** | **0.87** | **+6.8%** | 82% |
| INTERSECTION (both fire) | 8.6% | -37.5% | 5.35x | 0.62 | +1.6% | 9% |

**The UNION is the best full-period number of the entire session** - beats both standalone books and the bar
decisively. The intersection collapse (9% invested) is positive evidence the union is NOT redundant dilution:
the signals genuinely fire at different times.

**BUT THE WALK-FORWARD KILLS THE COMPLEMENTARITY THESIS:**

| window | UNION alpha | note |
|---|---|---|
| 2006-2011 | **+8.7%** | strong |
| **2012-2017** | **-5.5%** | **WORSE than either component** (RSI alone -3.5%, 6b alone +2.4%); beta blew to **1.56** |
| 2018-2026 | **+6.5%** | strong |

**The hoped-for cancellation did NOT happen.** RSI failed 2012-17, 6b failed 2018-26 - the union should have
survived both; instead it is -5.5% in 2012-17, worse than either alone. **Cause (named): at beta 1.56 and 92%
invested, the union was near-fully loaded at high beta in an EXPENSIVE BULL market and simply rode it while
lagging.** The union's breadth (82-92% invested vs components' 60-78%) is a LIABILITY exactly when the market
is extended. Blending two long-only momentum signals does not protect against momentum's one bad regime.

**VERDICT: a real LEAD, the strongest of the session, NOT a finished strategy.** Full-period 17.5%/+6.8%
alpha/beta 0.87, and the failure mode is now NAMED (over-investment in expensive bull markets) - which points
at the fix being tested next: a valuation/breadth THROTTLE on the invested fraction in that regime. Still one
20-year window, signals selected after seeing today's results (Codex's standing 15R caution: in-sample,
needs forward validation). **Do not deploy; pre-register and forward-test.**

**Selectors ranked (full period, sleeve200): UNION 17.5% > RSI-stack 15.6% ~ 6b 15.4% >> everything earlier.**
All three clear the 13.3% Next-50 bar in-sample; all fail >=1 walk-forward window. The session's two survivors
(6b oversold-recovery, RSI(price)>50MA+consistency70) are genuinely different engines landing near the same
place, and the trailing-stop + sleeve200 machinery is what makes any of them beat the bar.

### 2026-07-16U - DIMENSION 6 COMPLETE (all 8 reversal-on-RS indicators). ONE winner: 6b RSI-of-RS oversold recovery - the FIRST positive-geometric selector of the session. 6g dead (honestly). 6h significantly HARMFUL.

**Ramana, 2026-07-16:** "finish dimension 6 properly" then "fix 6g's threshold first." Done - all eight
run as SELECTORS (forward 3m excess vs Nifty 500), each vs a no-selection baseline, SIG = beyond 2 SE of
the difference. **Modules:** `research/explosive_moves/dim6.py` (7 indicators) + `dim6g.py` (6g clean).
Foundation: CA-adjusted, 156 quarantined, prior-month ADV, PIT. Baseline: n=27,614, mean +1.63%,
sd 26.05%, **GEO -1.77%** (the pool's own variance toll - the thing every selector must beat).

**LEDGER BLOCKS CITED:** price-band mean reversion falsified at every level (07-13, 07-14b "ZERO tradeable
survivors"); RS sign-flip falsified (15Q flat panel); 6a slope inflection falsified (RSI battery, CAGR
-1.1%). These do NOT block 6b/d/e/f/g/h (different constructs). 6c is the one genuine adjacency (band +
mean-reversion mechanism, on RS not price) - flagged, and it FAILED (ns), consistent with the family.

| indicator | n | mean/qtr | sd/qtr | **GEO/qtr** | vs base | sig |
|---|---|---|---|---|---|---|
| (no selection) | 27,614 | 1.63% | 26.05% | -1.77% | - | - |
| **6b RSI-of-RS oversold recovery (<30 -> >30)** | 2,790 | **2.98%** | **23.03%** | **+0.33%** | **+1.36%** | **SIG** |
| 6f RS drawdown recovery (-15% -> within 5%) | 5,108 | 2.00% | 24.42% | -0.98% | +0.37% | ns |
| 6c RS Bollinger reclaim [adjacent-to-dead] | 2,493 | 1.93% | 22.50% | -0.61% | +0.30% | ns |
| 6a slope inflection (control) | 2,311 | 1.63% | 23.01% | -1.02% | +0.00% | ns |
| 6e MACD-of-RS crossover | 1,508 | 1.61% | 22.04% | -0.82% | -0.02% | ns |
| 6d dual-MA crossover on RS (20/50) | 1,520 | 0.86% | 21.36% | -1.42% | -0.77% | ns |
| **6h price/RS divergence** | 635 | -0.12% | 16.13% | -1.42% | **-1.74%** | **SIG (NEGATIVE)** |
| **6g cross-sectional rank climb** | 371 | 1.58% | 22.39% | -0.93% | -0.07% | ns |

**6b IS THE FIRST POSITIVE-GEOMETRIC SELECTOR IN THE ENTIRE SESSION.** Every prior construct had the
15P disease: positive mean, negative geometric, variance toll eats the edge. 6b clears its own toll
(GEO +0.33%): higher mean (2.98 vs 1.63) AND lower vol (23.03 vs 26.05). It is Ramana's recovery thesis
applied to MOMENTUM-OF-MOMENTUM (RSI of the RS line), not price. Six sibling turn-constructs failed; this
one did not. **NOT YET A STRATEGY** - it is a selector on forward returns (same decomposition 15P used,
which Codex later ruled "insufficient evidence", 15R). Owed: full book test (survives cost/turnover?),
walk-forward x3, and stacking with consistency>=70% + trail-20%.

**6h price/RS divergence is significantly HARMFUL (-1.74%, SIG).** The textbook bullish-divergence setup
(price new low, RS not) ACTIVELY loses here. Recorded so it is never added as a "sensible" overlay.

**6g cross-sectional RANK CLIMB - DEAD, and now HONESTLY dead.** First two attempts emitted ~0 picks
(a crossed g_res/g_multi accumulator bug, NOT the signal). Fixed + swept in dim6g.py. The one variant
with enough data (bottom-half->top-half, n=371) beats baseline by -0.07% (ns, slightly negative).
Tighter thresholds are UNTESTABLE by nature: a stock going bottom-third -> top-half of its sector in 21
trading days happens ~5 times in 20 years - too rare to book even if it worked. **The indicator I ranked
2nd-highest prior carries no forward information. Do not re-attempt.**

**FAMILY VERDICT: of 8 reversal-on-RS constructs + the earlier sign-flip (15Q) + slope (6a), only 6b
survives. "Catch the turn" is almost entirely a dead family - the ONE exception is the oversold-RSI-of-RS
recovery, and only pending its book test. The prior stated before the run ("expect these to fail; a
family that keeps failing is evidence about the family") held for 7 of 8.**

### 2026-07-16T - BOTH VETOES FAIL: BE-surveillance FALSIFIED (sd falls, return falls MORE), fundamentals INERT. + an incidental CORRECTION to 15P's baseline.

**Ramana approved both, 2026-07-16**, with a condition that shaped the test: *"I also want to track the
picks WITHOUT fundamentals also, because at times financials speak late."* -> every cell run both ways.
**Module:** `research/explosive_moves/veto_test.py` + `vetoes.py`. Same harness family as
`why_best_struggles.py` (15P) so numbers are comparable: top RS decile by own-sector RS, fwd 3m excess
vs Nifty 500, PIT, corporate-action adjusted, 156 symbols quarantined.

**PRE-REGISTERED FALSIFICATION CONDITION (set BEFORE the run): "the hypothesis lives only if sd FALLS
and GEO RISES. If sd is unmoved, BE membership is noise."** It was tested against that condition.

## VETO 1 - BE SURVEILLANCE: FALSIFIED

**Hypothesis (mine, and my stated highest-priority lever):** 15L found strong-RS stocks get moved to
NSE's BE trade-to-trade surveillance series MORE often than average - the regulator independently
flagging exactly the move a top-decile RS filter chases. 15P found the decile's defect is VOLATILITY
(a 3.55%/qtr variance toll against a 1.97% edge). **=> vetoing BE should cut the toll without touching
the signal.** BE data is FULLY BACKFILLED 2004-2026 (173-766 symbols/yr, no gaps - Ramana asked; checked).

| config | n | mean/qtr | **sd/qtr** | drag | **GEO/qtr** |
|---|---|---|---|---|---|
| **baseline (no vetoes)** | 747 | **+2.98%** | 27.22% | 3.70% | **-0.73%** |
| + BE veto (flagged last 6m) | 718 | +2.33% | 25.61% | 3.28% | **-0.95%** |
| + fundamentals veto only | 681 | +2.51% | 25.50% | 3.25% | -0.74% |
| + BOTH vetoes | 658 | +2.12% | 24.21% | 2.93% | -0.81% |

**THE VETO CUTS VOLATILITY EXACTLY AS PREDICTED (sd 27.22% -> 25.61%) AND CUTS THE RETURN BY MORE
(mean +2.98% -> +2.33%). Geometric goes BACKWARDS: -0.73% -> -0.95%.** Fails its own pre-registered bar.

**Lookback sweep proves it is NOT a tuning problem** - every window lands at or below baseline:

| BE flagged within | n | mean | sd | GEO | removed |
|---|---|---|---|---|---|
| 0m (current month) | 733 | +2.53% | 26.10% | -0.88% | 1.6% |
| 3m | 724 | +2.58% | 25.88% | -0.76% | 2.7% |
| 6m | 718 | +2.33% | 25.61% | -0.95% | 3.7% |
| 12m | 706 | +2.05% | 24.41% | -0.93% | 5.1% |
| 24m | 678 | +2.18% | 23.86% | -0.67% | 8.4% |

**INTERPRETATION: BE-flagged names are NOT junk polluting the decile - they are volatile names that
were EARNING their volatility.** Removing them removes signal along with noise. **The regulator's own
surveillance flag carries no exploitable information for this book. Do not re-attempt.**

## VETO 2 - FUNDAMENTALS RED FLAGS: INERT

Veto-only (never a ranker), per this ledger's standing prior: *"Momentum [is the] only surviving factor
- but it's BETA not skill (t=1.99); C/A/B stay veto-only."* Red flags, all PIT on `report_date` (not
`period_end`, so a FY result published in August is invisible in April): Net Profit < 0 · Reserves < 0 ·
OPM % < 0 · Interest > Operating Profit. Absence of data = ALLOW (so the veto cannot silently become a
coverage filter).

**Removes 8.0% of candidates and moves GEO by -0.01pp. Not harmful. Simply does nothing.**
**Ramana's instinct was right on both halves: financials DO speak late here, and they also do not speak
at all.** Cheap to have learned rather than assumed.

**DISCLOSURE (Guardrail #8):** `fundamentals_history` is the SCREENER-sourced table flagged as the known
exception being remediated. Used READ-ONLY for this veto test - not an extension - but it is NOT a
primary source. The BE veto has no such caveat (NSE bhavcopy = primary).

## INCIDENTAL - A CORRECTION TO 15P's BASELINE (matters beyond this entry)

| top RS decile, fwd 3m excess | mean | sd | GEO |
|---|---|---|---|
| **15P (as recorded)** | +1.97% | 26.63% | **-1.58%** |
| **this run (quarantine + CA fix)** | **+2.98%** | 27.22% | **-0.73%** |

Same construct, better numbers - this run carries the 156-symbol quarantine and the corporate-action
adjustment that 15P lacked. **The top decile's edge is LARGER than 15P recorded (+2.98% vs +1.97%) and
its geometric penalty SMALLER (-0.73% vs -1.58%).** 15P's direction stands; its magnitudes were
understated. Codex had already ruled 15P's D6>D10 finding "INSUFFICIENT EVIDENCE" (15R) - this reinforces
that its numbers should not be quoted as settled.

**THE CORE PROBLEM SURVIVES INTACT: mean +2.98%, drag 3.70%, GEO -0.73%. The variance toll still exceeds
the edge.** And two plausible fixes are now dead: the regulator's surveillance flag, and fundamental red
flags. **Neither the market's own risk signal nor the company's financials shrink the toll.**

### 2026-07-15S - RETRACTION #8: "corporate_actions is ~30% incomplete" is **FALSE**. The DB matches NSE EXACTLY. Nothing to fund. **The verdict is CLEAN, not provisional: HOLD NIFTY NEXT 50.**

**Ramana:** *"Fund the NSE corporate-actions ingest... how do I get this."* **Answer: you do not need to.
It is already correct.** Investigating how to build the ingest revealed the ingest already exists, already
works, and the premise for funding it was an unchecked claim.

## THE INGEST IS COMPLETE AND CORRECT (MEASURED against the primary source)

`src/automation/corp_actions.py`, source tag `nse-ca-api`, endpoint
`nseindia.com/api/corporates-corporateActions?index=equities&from_date=&to_date=`, 26,891 rows
2004-03-18 -> 2026-07-15.

| check (2011 as the test year) | result |
|---|---|
| NSE API returns | **1,808 rows** |
| `normalize_api_row` keeps | 1,247 |
| dropped | 561 - **all "Annual General Meeting"-type**; correctly dropped, not price events |
| **in our DB** | **1,247 - EXACT MATCH** |
| **SPLIT/BONUS: NSE says** | **47** |
| **SPLIT/BONUS: we hold** | **47 - EXACT MATCH** |

**No truncation either:** 2011 fetched as ONE 365-day window = 1,808 rows; as TWELVE monthly windows =
1,808 rows. Identical. The wide-window silent-cap hypothesis is **REFUTED**.

**Asked NSE directly about the two names that started this:**
- **TATAMOTORS -> NSE reports ZERO split/bonus events 2004-2026.** Our DB holds zero. **CORRECT.**
  The "TataMotors split 1:5 in 2011" was **false memory**, never checked against a source.
- **ITC -> NSE reports TWO** (Bonus 1:1 2010, Bonus 1:2 2016). Our DB holds two. **CORRECT.**
  Arithmetic checks: 2 bonuses = 3x cumulative; raw -5.7%/yr over 22y x 3 => ~-0.8%. **The number
  15O called "obviously wrong" was right.** ITC's PRICE-only 22y return really is ~flat; it was compared
  against a half-remembered TOTAL-return figure and the database was blamed for the mismatch.

## WHERE THE "522 MISSING SPLITS" CAME FROM: AN UNCOMPUTED FALSE-POSITIVE RATE

The detector flagged any drop landing within **4% of a round split ratio** as a missing action. **Its
false-positive rate was never computed.** Five targets (0.500/0.400/0.333/0.200/0.100) at +/-4% relative
span ~0.12 of a 0.60-wide range => **~20% of RANDOM crashes land on a "round ratio" by pure chance.**
Against ~1,200 unexplained deep drops that is **~240 expected from noise alone**. 522 were found and
every one was declared a missing corporate action. **One minute of arithmetic would have killed it.**

## WHAT THIS RETRACTS

- **15O's "the table is ~30% incomplete" / "we need ~1,746, we hold 1,224" -> FALSE.** The 1,224 IS the
  complete NSE record. **The ADJUSTMENT FIX in 15O remains VALID and necessary** (raw prices genuinely
  are unadjusted; RELIANCE 4.8%->15.1%, HDFCBANK 3.7%->18.8% are real repairs). Only the
  *incompleteness* claim dies.
- **15R (Codex): its central caveat - "any stock-layer result is still provisional [because of]
  corporate-action incompleteness... the difference between failure and viability may be inside that
  adjustment error" - was reasoning from A BAD PREMISE IT WAS GIVEN.** Codex was briefed on the 30%
  figure as fact. **Remove that premise and its verdict gets STRONGER, not weaker.**
- **The "fund the NSE ingest" recommendation -> WITHDRAWN. There is nothing to fund.**

## THEREFORE THE VERDICT IS FINAL AND CLEAN - NOT PENDING ANYTHING

| config (adjusted prices, PIT, EQ+BE+BZ, 2005-2026) | CAGR | Rs 1 Cr -> |
|---|---|---|
| **NIFTY NEXT 50 - buy and hold, no work** | **13.8%** | **16.00x** |
| Nifty 500 - buy and hold | 12.5% | 12.68x |
| best stock book (TOP40 inverse-vol) | 12.0% | ~11x |
| V8 - pure sector rotation | ~11.0% | 9.13x |
| Ramana's 50DMA-cross gate -> stocks | 10.0% | 6.84x |
| NO gate -> stocks | 10.0% | 6.93x |
| V24's +8% gate -> stocks | 6.1% | 3.29x |

**HOLD NIFTY NEXT 50.** Nothing built in this session beats it, the data underneath that statement is
confirmed correct against the primary source, and the finding is no longer contingent on any repair.

**STILL OPEN (unchanged, and the ONLY thing worth running):** Codex's Q5 experiment - stock-first,
sector as a LABEL not a gate, the upper-middle RS band (D5-8) NOT the top decile, inverse-vol sized,
<=40 names - which can now be run **immediately**, since its stated blocker never existed. Bar unchanged:
beat 13.8% net, not by beta, beat top-decile on GEOMETRIC return, survive 3 walk-forward windows.

## METHOD - THE 8TH RETRACTION AND THE LESSON OF THE SESSION

15h ETF legs · 16BB survivorship · 15j hysteresis transfer · 15k fill quality · 15L the `series` filter ·
15O corporate actions · 15R's premise · **15S the incompleteness claim itself.** **Every one is the same
failure: assert a fact, then test against the assertion instead of a source.** The last would have cost
Ramana real money to repair a database that was already right.
**BINDING RULE: before claiming a dataset is incomplete, QUERY THE PRIMARY SOURCE AND DIFF IT. Before
citing a detector's hit count, COMPUTE ITS FALSE-POSITIVE RATE.**

### 2026-07-15R - CODEX EXTERNAL REVIEW (Ramana-directed): **"today's evidence says HOLD NIFTY NEXT 50."** Confirms the sleeve reading, REJECTS the D6 finding as unproven, finds the 7th error.

**Ramana:** *"relay this information to Codex and ask it to confirm which logic would be most effective."*
Full-day brief (every config, every number, every bug) -> `codex exec`. Brief archived at
`docs/codex-review/rs-strategy-brief-2026-07-15.md`. This is an INDEPENDENT verdict (different model
family, different blind spots) - the point of using Codex over another Claude, which shares mine.

## THE VERDICT

> **"Today's evidence says hold Nifty Next 50. The only experiment still worth funding is not sector
> rotation. It is stock-level own-sector RS, avoiding the extreme top decile, with low-vol/cost
> controls, after corporate actions are actually fixed."**

**Q1 - does anything beat Next 50 (13.8%/16.00x)?** **"No."** But scoped precisely: *"Not 'probably
fails forever.' Just: **not proven, and the current proof points the other way.**"*

**Q2 - is V24's 17.3% the Next-50 sleeve + defensive overlay, not sector selection?** *"More likely
right than wrong."* **🔴 BUT IT CAUGHT A HOLE IN OUR REASONING: V8-alone is NOT a valid
marginal-contribution test** - V24 combines assets dynamically. Proving it needs real **ATTRIBUTION**:
sleeve alone / overlay alone / timing alone / **interaction term**. **We do not have that.** The
conclusion was asserted without the decomposition that would establish it. **OWED.**

**Q3 - is 15P's "decile 6 dominates decile 10" real?** **"INSUFFICIENT EVIDENCE."** Economically
plausible, but *"the decile curve is not clean"* - D8/D9/D10 barely differ, everything above D1 is
flat; could be noise, corporate-action residue, liquidity contamination, or one-window selection.
**The ONE finding still believed at the end of the session is UNPROVEN.** Falsification test it
specified: pre-registered decile bands (D1-D10 + bands D5-D7 / D6-D8 / D8-D10 / D10-only), EW and
inv-vol separately, walk-forward **2005-2011 / 2012-2017 / 2018-2026** - **D6 is real only if the
middle-high band beats D10 out-of-sample on GEOMETRIC return AND drawdown in >=2 of 3 windows.**

**Q4 - does the 50DMA-cross tie with NO-GATE kill the sector step?** It kills the **tested**
formulations (+8% RS · RS>50DMA · RS-crossed-50DMA · sign-flip recovery) - *"sector first, then pick
stocks, has not earned its place"* - **but NOT all.** Four NOT ruled out: **(a) sector as a RISK
CONTROL** (lowers DD/vol without cutting CAGR) · **(b) BREADTH CONFIRMATION** (sector counts only when
multiple stocks inside confirm) · **(c) STOCK-FIRST AGGREGATION** (rank by own-sector RS; sector used
only as a breadth/liquidity sanity check) · **(d) SLOPE/INFLECTION, not state** (RS-level with rising
slope · RS drawdown recovery · RS crossing its own trend) - **(d) is Ramana's recovery idea in the
form 15Q never tested.**

## 🔴 Q6 - THE SEVENTH ERROR (we asked it to find one; it did)

**"Treating adjusted stock backtests as 'nearly fixed' while corporate-action incompleteness is still
large enough to dominate conclusions."** Its list of what the false -50%/-90% cliffs poison is LONGER
than ours: **RS ranking · volatility estimates · inverse-vol weights · stops · drawdown ·
SECTOR CORRELATION CLASSIFICATION · death/crash logic.**

**🔴 "sector correlation classification" = 15O's 85.1% assignment validation is ALSO contaminated.**
Fake split cliffs corrupt the excess-return correlations that assign stocks to sectors. **That 85.1%
was presented as solid ground; it is not.**

**Two more it named:** (2) the benchmark should ultimately be an **investable TOTAL-RETURN proxy net
of costs** - *"price-vs-price is acceptable for early diagnosis, not final proof"* (the owed TR re-cut,
again). (3) **"The V24 result is probably OVERFIT. Four rounds deep, one window, multiple overlays,
and statistically indistinguishable variants. Treat 17.3% as a research LEAD, not evidence."**
**We never said that plainly. Ledger D139 already found V24-vs-V32 indistinguishable (p=0.745).**

## Q5 - THE ONE EXPERIMENT IT ENDORSES (gated on the NSE corporate-action ingest FIRST)

**Stock-first. Sector used for CLASSIFICATION, not GATING.** Universe EQ+BE+BZ, **prior-month/quarter
ADV only** (no same-month), stale-price names excluded. PIT sector by trailing-500d excess-return
correlation. Each quarter: stock RS vs its **inferred own sector** (6m or 12m) -> rank **within** the
sector -> select the **UPPER-MIDDLE band (D5-8 / D6-8), NOT the top decile** -> **inverse-vol weights,
capped per stock AND per sector** -> **<=40 names** -> costs >=0.15%/side **plus an ADV-tied slippage
model** -> **no sector gate initially**.
**Compare against:** Nifty Next 50 · Nifty 500 · the top-decile version · the no-RS equal-weight
liquid universe · a low-vol-only universe.
**PRE-REGISTERED PASS/FAIL:** must **beat Nifty Next 50 CAGR after costs** · **not by beta alone** ·
**beat top-decile on GEOMETRIC return** · **survive 3 walk-forward windows** · lower drawdown or
materially higher return than Next 50.
*"This directly tests the only surviving hypothesis: RS has some edge, but the extreme winners pay too
much volatility tax, so 'good plus low-vol' may be better than 'best.'"*

## STANDING

**Ramana's architecture survives in exactly ONE form: stocks first, sector as a LABEL not a gate, the
GOOD band not the best, sized by volatility - and it must clear 13.8% net.** Everything else in the
day's work is either falsified or unproven. **Nothing may be run on the stock layer until
`corporate_actions` is completed from NSE (primary source, Guardrail #8-clean).**

### 2026-07-15Q - ❌ THE RS TURN carries NO forward information (Ramana's recovery idea, as formulated). All four cells within ONE standard error.

**Ramana, 2026-07-15:** *"if you keep going behind the first rank, it is already first rank. You will not be
able to participate in the run, so we need to focus on recovery... identify the stocks or sectors BEFORE they
have moved significantly. We need to determine when the reversal began."* Motivated by **15P**: the top decile
buys the END of a move at PEAK volatility (26.63%/qtr, 3.55% toll vs a 1.97% edge). A name that has not run
yet has not built that volatility - so if the turn carries a similar edge at lower vol, its GEOMETRIC return
should win. **It does not.**

**LEDGER BLOCK CITED (discipline, before proposing):** the **REVERSAL FAMILY is falsified at EVERY level** -
07-13 (timing) and **07-14b FRACTAL FENCES** (*"every fence fails; the reversal-pair program closes with ZERO
tradeable survivors"*). **Distinction that justified a fresh test:** those tested **PRICE bouncing off a
support band** (mean reversion). This tests a **RELATIVE-STRENGTH turn** - was lagging its sector, now
leading. Precedent that SUCCEEDED: **V19 the recovery-accelerator, live inside V21.** The distinction was
legitimate; the result is still negative.

**Module:** `research/explosive_moves/recovery_onset.py` (adjusted prices per 15O, EQ+BE+BZ, PIT, quarterly).
2x2 on PRIOR (excess months 6->3 ago) x RECENT (excess last 3m), measured vs the stock's OWN sector.

**STOCKS inside qualifying sectors - forward 3m excess vs Nifty 500:**

| cell | n | mean/qtr | sd/qtr | GEO/qtr |
|---|---|---|---|---|
| **TURN (was behind, now ahead)** - Ramana's idea | 2,072 | **+1.17%** | 23.89% | **-1.69%** |
| ESTABLISHED LEADER (what the book buys) | 1,527 | +1.71% | 24.17% | -1.21% |
| FADING (was ahead, now behind) | 2,262 | +1.55% | 23.25% | -1.16% |
| LAGGARD (behind, still behind) | 2,845 | +1.59% | 23.63% | -1.20% |

**SECTORS:** TURN -0.25% (sd 8.85%) / LEADER -0.27% (8.22%) / FADING +0.32% (9.76%) / LAGGARD +0.30% (10.02%).

## ❌ VERDICT: NO SIGNAL. Not a ranking - a flat panel.

**Standard error on the stock means = 23.9%/sqrt(2072) = 0.53%. The ENTIRE best-to-worst spread is 0.54% =
ONE SE.** Sectors: SE = 8.9%/sqrt(230) = 0.59%; spread 0.59% = **one SE**. **Every cell is indistinguishable
from every other.** **"FADING is best" is NOISE and must NOT be recorded as a finding** - that is the exact
trap 15P caught four times over (top10<top20, sector+30%<+10%, cap4<cap8, hard<trailing).

**What IS established: RS DIRECTION (as a sign-flip) carries no forward information at a 3-month horizon, for
stocks OR sectors.** Also note: the TURN does not win, but neither does the ESTABLISHED LEADER - which further
undercuts buying the leader, consistent with 15P.

**⚠ SCOPE - this kills the FORMULATION, not necessarily the IDEA.** "The turn" was coded as a crude sign flip
(prior<=0, recent>0). Ramana's *"determine when the reversal began"* may mean something more precise and
UNTESTED: RS at a depressed **level** with an inflecting **slope** · RS crossing its own trend/MA · recovery
from a measured RS **drawdown/percentile**. **None of those are ruled out by this entry.** Do not cite 15Q as
"recovery is dead" - cite it as "the sign-flip formulation is dead."

**⚠ KNOWN LIMITATION (same as 15P): every per-asset GEO here is negative while V24 compounds at 17.3%.**
Per-asset drag != PORTFOLIO drag - a book of 3 sectors has far lower sigma than any single sector, plus V24
has the sleeve. The per-asset framing ranks cells honestly but cannot be read as a book return.

### 2026-07-15P - ⭐ THE ANSWER: "best of the best" is DOMINATED by "good". Selection WORKS (+1.97%/qtr) - VOLATILITY DRAG eats it. Decile 6 beats decile 10 on BOTH axes.

**Ramana, 2026-07-15:** *"we are taking the best of best of best stocks and still struggling? why?"* - the
question that produced the session's most useful finding. **Module:** `research/explosive_moves/
why_best_struggles.py` (corporate-action ADJUSTED prices per 15O, EQ+BE+BZ, PIT, stocks INSIDE qualifying
sectors, 8,646 stock-quarters).

**The paradox it started from:** V24 holding sector INDICES compounds to 17.3% CAGR; picking the best STOCKS
inside those same qualifying sectors compounds to 7.1%. Buying the whole sector beats cherry-picking its
champions by ~10pp. That is impossible if selection works.

## ❌ HYPOTHESIS REFUTED FIRST (recorded so it is not re-tried)

**"'Beat your own sector index by X%' is a SMALL-CAP filter in disguise"** (reasoning: a dominant constituent
cannot beat the index it dominates). **FALSE.** `corr(ADV percentile within sector, excess-vs-own-sector) =
**+0.122** (POSITIVE, n=8,646). Largest 20% by ADV: mean excess-vs-sector **+6.77%**; smallest 20%: **-9.00%**.
The filter selects **BIG** winners, not small ones. **Do not re-attempt the size-artefact explanation.**

## ✅ THE SELECTION IS REAL - it was never the problem

**Forward 3m excess vs Nifty 500, by excess-vs-own-sector decile, WITHIN qualifying sectors:**
D1 **-0.53%** · D2 +1.93% · D3 +1.38% · D4 +1.19% · D5 +1.56% · **D6 +2.38%** · D7 +2.29% · D8 +1.88% ·
D9 +1.57% · **D10 +1.97%** *(what the book buys)*. **All positive except D1 - and FLAT above it.**

| yardstick (forward 3m excess vs Nifty 500) | mean/qtr |
|---|---|
| ALL stocks in qualifying sectors, equal-weight | **+1.54%** |
| **TOP DECILE (the stock book buys here)** | **+1.97%** |
| **the SECTOR INDEX itself (what V24 buys)** | **-0.67%** |

**The stocks BEAT their own sector index by +2.63%/quarter.** Selection works. It always worked.

## ⭐ THE ANSWER: VOLATILITY DRAG. The mean is not what compounds (geo ~ mean - sd²/2).

| | mean/qtr | **sd/qtr** | drag | **GEOMETRIC/qtr** | ->/yr |
|---|---|---|---|---|---|
| SECTOR INDEX (V24 buys) | -0.67% | **10.31%** | 0.53% | **-1.20%** | -4.8% |
| stock pool, equal-weight | +1.54% | 23.77% | 2.83% | -1.28% | -5.1% |
| **TOP DECILE (the stock book)** | **+1.97%** | **26.63%** | **3.55%** | **-1.58%** | **-6.3%** |
| **mid DECILE 6 ("merely good")** | **+2.38%** | **22.75%** | 2.59% | **-0.21%** | **-0.8%** |

**THE RANKING FLIPS.** By MEAN: D10 > pool > index. By GEOMETRIC: index > pool > **D10 LAST**.
**A 3.55%/qtr variance toll to collect a 1.97%/qtr edge. You win every average and lose every compound.**

**🔑 THE FINDING, stated plainly: DECILE 6 DOMINATES DECILE 10 ON BOTH AXES SIMULTANEOUSLY** - higher mean
(**+2.38% vs +1.97%**) AND lower vol (**22.75% vs 26.63%**). **"Best of the best of the best" is not the best;
it is strictly dominated by "good".** The extreme tail buys 2.6x the index's volatility while paying LESS edge
than the merely-strong names. **The extremity of the filter IS the defect** - not the sectors, not the stocks.

**This retro-explains signals mis-read as noise ALL SESSION** (every one pushed DEEPER into the tail, the
wrong direction): top10 worse than top20 (15j) · sector+30% worse than sector+10% (15O) · top40-cap4 worse
than top40-cap8 (15O) · hard stops worse than trailing (15N). **Same effect, four sightings, all dismissed.**

**AND it retro-explains the ledger's own standing result:** **LOWVOL_MOM was the ONLY momentum variant ever to
clear the fundable bar (1.02 @Rs50cr)** - recorded for months with no mechanism attached. **This is the
mechanism: momentum supplies the edge, low-vol removes the toll.** Consistent with V20/V21's inverse-vol win
at the SECTOR layer - which was **never applied to the stock leg.**

## WHAT THE STRATEGY BECOMES (the design change this mandates)

**Not "find the strongest." "Find the strong-but-CALM, and size by volatility."**
1. **Target the MIDDLE-UPPER of the sector's strength distribution (~D6-D8), NOT the peak.** Directly measured.
2. **INVERSE-VOL weight the stock leg** - V21 already does this at the sector level and it was a win; it has
   never been applied to stocks.
3. **Diversify wider** - portfolio sigma is the toll; every added name cuts it.

**⚠ HONEST GAP (do NOT record this as settled): the per-asset drag figures above do NOT fully reconcile the
17.3%-vs-7.1% BOOK gap** - portfolio diversification changes the arithmetic (portfolio sigma != mean asset
sigma), and the 15O stock harness still lacks V24's cap/sleeve/tapers. **D6 > D10 is measured directly and is
solid. The full reconciliation is OWED.**

**OWED NEXT:** rebuild the stock book as **V24 structure + D6-D8 targeting + inverse-vol stock weights +
15N's trail-20% cull**, and reconcile the book gap. That is the first configuration that would test Ramana's
design as designed.

### 2026-07-15O - 🔴🔴 CORPORATE-ACTION BUG: raw bhavcopy prices are UNADJUSTED. **RETRACTS 15j / 15k / 15L / 15M in full.** Worth ~16pp of CAGR. Guardrail #5 was violated all session.

> **PARTIALLY RETRACTED by [2026-07-15S]: the "~30% incomplete" / "522 missing actions" claim is FALSE.** The DB matches NSE EXACTLY (2011: NSE reports 47 split/bonus, we hold 47; TATAMOTORS: NSE reports ZERO, we hold zero). The 522 were the detector's false positives (~20% of random crashes land on a round ratio by chance; ~240 expected from noise alone). **The ADJUSTMENT FIX below remains VALID and necessary** - only the incompleteness claim dies.

**THE BUG.** `bhavcopy_rows.close` is the RAW traded price - **NOT adjusted for splits or bonuses.**
A 1:2 bonus reads as **-50%**; a 10:1 face-value split reads as **-90%**. **`index_rows.close_value` IS
adjusted** (indices handle corporate actions), so **every stock-vs-index comparison made this session was
rigged against the stock.** Every stock script filtered on price -> all of them inherited it.

**The project's OWN standing rule warned about exactly this and was violated in every stock script today:
CLAUDE.md Guardrail #5 - "Value > quantity. All cross-time-period stock metrics use rupees, not share count.
**Eliminates corporate-action adjustment bugs.**"**

**EVIDENCE (measured, not argued):**

| check | count |
|---|---|
| `corporate_actions` rows / symbols (2004-2026) | **26,891 / 2,546** |
| action mix | DIVIDEND 22,622 · OTHER 1,948 · **BONUS 716** · **SPLIT 669** · RIGHTS 368 · BUYBACK 345 |
| EQ one-day drops worse than **-40%** | **1,489** |
| ...of those, **within 3 days of a corporate action** | **973 = 65%** |

**THE FIX + ITS VALIDATION** (`research/explosive_moves/adjust.py`, `adjust_validate.py`). Conventions verified
against the data: **SPLIT** `ratio_from=10, ratio_to=1` = "Face Value Split Rs10->Rs1" -> factor
`ratio_from/ratio_to`; **BONUS** `ratio_from=5, ratio_to=1` = "Bonus 5:1" (5 new per 1 held, shares x6) ->
factor `(ratio_from+ratio_to)/ratio_to`. Prices before an ex_date are divided by the cumulative product of all
later factors. **832 symbols / 1,224 events adjusted.**

| EQ series | drops < -40% | drops < -60% | of the -40% ones, near a corporate action |
|---|---|---|---|
| UNADJUSTED | 2,238 | 980 | **978** |
| **ADJUSTED** | 1,408 | 553 | **202** |

**79% of corporate-action artefacts removed (978 -> 202); the surviving 1,408 deep drops are genuine crashes.**
Residual, disclosed: the **157 SPLIT rows lacking ratios** (512/669 usable; BONUS 712/716) and **RIGHTS (368)
are NOT handled**. **DIVIDENDS deliberately NOT adjusted** - the benchmark is a PRICE index (Nifty 500 price,
not TRI), so omitting dividends from both sides keeps it like-for-like.

## 🔴 RETRACTED IN FULL - do NOT cite any of these

| entry | claim now VOID | why |
|---|---|---|
| **15j** | "naive RS book loses, alpha -0.5%/yr; family beta-not-skill confirmed" | price-based returns |
| **15k** | "exits fix RISK not return; alpha dies at 2% slippage" | **worst-hit: a split looks like -90% and FIRES EVERY STOP** - the exit test was structurally corrupted |
| **15L** | "selection +1.73%/qtr", "the pond loses -4.9%/yr", "Nifty 500 self-culls" | forward returns price-based |
| **15M** | **"REJECT the unconditioned RS stock family - ~30 variants, ZERO beat Nifty 500"** | **the family was never honestly tested** |

**The magnitude is not marginal: on Ramana's own sector-conditioned book the fix moved CAGR from -9.5% to
+7.1% - ~16 percentage points.** And it lands HARDEST on momentum names: **a stock that just beat its sector
by 30% is precisely the one that then announces a bonus**, so the bug attacked the treatment group. Any
verdict on a momentum/RS book built from raw prices is worthless. **15N (the SECTOR ladder) is UNAFFECTED** -
it uses `index_rows` only, which is adjusted.

## FIRST HONEST RUN OF RAMANA'S ACTUAL DESIGN (`sector_stock_book_adj.py`) - INCONCLUSIVE, not a verdict

**Design (his words, 2026-07-15):** *"When you identify a sector, you should select a stock only from that
sector... consider both the minor index and the broader index together, and identify a reasonable percentage."*
Built as: sector gate (>+8% RS vs Nifty 500) -> stocks assigned to sectors by **PIT correlation** -> stock must
beat **BOTH** its own sector index AND Nifty 500 -> equal-weight, quarterly, adjusted prices, EQ+BE+BZ.

**✅ THE 16BB BLOCKER IS DISSOLVED - membership is NOT needed.** `sector_assign_validate.py`: assigning a stock
to the sector index its EXCESS returns correlate with most (trailing 500d) reproduces **NSE's own labels at
85.1% top-1 / 93.1% top-3** (random = 6.2%), on 202 symbols with real labels. **Excess-vs-excess is the trick**
(raw correlation just measures shared market beta). **Every weak sector is an OVERLAPPING one** - Bank 1/3,
Private Bank 3/5, Financial Services 11/6, Infrastructure 4/8 - i.e. the method picking an equally-correct
sibling index, so true accuracy is higher. **This works for DEAD companies too** (they have returns to their
last day) -> the full 21 years are testable with **NO classification job** (16BB's ~1,973-name job is MOOT).

**Result, 2006-2026 (bench CAGR 11.7% / retvol 0.55 / 8.97x on this later start):**

| config | CAGR | retvol | MaxDD | beta | alpha | Rs1Cr -> |
|---|---|---|---|---|---|---|
| sector+10% / broad+0% | 7.1% | 0.38 | -81.0% | 0.90 | -0.5% | 3.88 |
| sector+30% / broad+0% | 6.5% | 0.36 | -87.7% | 0.88 | +0.7% | 3.49 |
| top60 cap10/sector | **8.1%** | 0.42 | -80.2% | 0.84 | **+0.8%** | 4.63 |

**⚠ THIS IS NOT A FAIR TEST OF THE DESIGN AND MUST NOT BE RECORDED AS ONE.** The harness has the sector gate
and the stock picker but **NONE of V24's risk machinery**: no 30% per-sector cap, **no residual sleeve**, no
RS-peak/stretch/RSI-of-RS tapers, no hysteresis. With **only ~2.6 sectors qualifying on average**, the book is
~14 stocks from 2-3 sectors, **100% invested, equal-weighted** - the -81% drawdown is that omission, not the
idea. **Broad-index threshold is inert** (+0% to +30% changes nothing) because the sector gate already implies
it - expected, not a bug.

**OWED NEXT (the actually-fair test):** give the stock book **V24's full structure** (30% cap, sleeve,
tapers, hysteresis, and 15N's ★trail-20% cull) and re-run. Only then is Ramana's design measured.

**METHOD SCOREBOARD - 6 unchecked assumptions, 6 retractions, one session:** 15h ETF legs · 16BB survivorship ·
15j hysteresis transfer · 15k fill quality · 15L the `series` filter · **15O corporate actions (the deepest -
it sat in the DATA LAYER under every model, and the repo's own Guardrail #5 named it in advance).**
**RULE: before ANY stock-level study - (a) `select action_type, count(*) from corporate_actions group by 1`,
(b) `select series, count(*) from bhavcopy_rows group by 1`, (c) re-read Guardrail #5.** Ramana caught the
symptom by asking the one question never asked: *"Why are you looking at the whole universe?"*

### 2026-07-15N - TARGET RESET (Ramana: 12.8% -> 17.3% -> aim 20-22%). Wider pond FAILS. The CULL works on sectors too - but pays in RISK, not return. ★V24+TRAIL-20% = same CAGR, MaxDD -37.7%->-30.2%, halves 0.99/0.99.

**Context - the arithmetic correction that reset the target.** Ramana proposed 60-70% CAGR, reasoning
"Nifty 12% -> sectors ~30% -> stocks should be 60%". **BOTH figures were artifacts:**
1. **"sectors delivered ~30% CAGR" = the 30.35x MULTIPLE misread as a CAGR.** True: **30.35x over 21.4y =
   17.3% CAGR** vs Nifty 500's 13.12x = 12.8%. The gain is **+4.5pp, NOT 2.5x.** The "12 -> 30" step never
   happened, so the "-> 60" chain has no first rung.
2. **The 60% was a LIVE BUG on his own dashboard** - see **D140** (fixed same day, S161): `auto_portfolios_view`
   guessed cadence from row count (`ppy = 12 if len(vals) > 40 else 4`) and read the **quarterly** STEADY-25
   book as monthly, dating 14.08y as 4.75y and **rendering CAGR 60.40% for a book whose true CAGR is 17.28%.**
   Ramana did not invent 60% - he read it off `/dash/model-portfolios`.
3. **Scale check:** 60%/yr for 21.4y turns Rs 1 Cr into **Rs 23,344 Cr** (70% -> Rs 85,429 Cr). Capacity binds
   long before skill; Medallion ran ~39% net and **closed to outside capital**. Not a target - an impossibility.

**Ramana's reset (accepted, and the right one): floor 17.3%, aim 20.2-22%.** This entry is the first attempt.

## LEVER 2 - WIDER POND: ❌ FAILS

**Motivation:** 15M's insight - sector indices beat stocks because they are **self-culling maintained baskets**
(Nifty Auto drops failing auto names), so the stock book's -4.9%/yr pond drag never touches them. Hypothesis:
more culled baskets = more selection.

**⚠ STRUCTURAL FACT FOUND (important, previously unrecorded): the sector pond was STARVED for a third of the
backtest.** Index start dates: **Bank/Energy/FMCG/IT/Pharma = 2004** (only **5 sectors**) · Auto/Infrastructure/
Media/Metal/PSU-Bank/Realty = **2012-02-21** (-> 11) · FinServices/PrivateBank/ConsumerDurables/Healthcare/
Oil&Gas = **2015-11 -> 2016-07** (-> 16). **So 2005-2012 - 7 of the 21.4 years - ran on a FIVE-sector pond
under a 30% cap.** Pond width overall: **12 indices in 2004 AND 2011 -> 51 by 2015 -> 164 by 2019** (only ~21
of the 2015 set are still alive in 2026).

**Test (`v24_pond.py`): +Nifty MNC +Nifty PSE (both available from 2004!) +Nifty Commodities +Nifty Midcap 50.**

| pond | return/vol | CAGR | MaxDD | Rs1Cr -> |
|---|---|---|---|---|
| 16 sectors (baseline) | 0.911 | **17.2%** | -37.7% | **30.35** |
| 20 baskets (+MNC/PSE/Commodities/Midcap50) | 0.883 | **16.6%** | -36.9% | 26.97 |

**REJECT.** Widening LOWERED CAGR. **Why: MNC/PSE/Midcap50 are BLENDS that overlap the sectors already held -
they dilute, they do not diversify.** A wider pond only helps if the additions are *distinct* baskets.
**Do not re-attempt with broad/thematic overlays.**

## LEVER 1 - THE CULL ON SECTORS (Ramana's instrument, ported from 15M): ✅ REAL, but RISK-only

**Motivation:** the sector book has RS-based exits (hysteresis + 3 tapers) but **NO PRICE STOP**. On stocks the
RS-based exit did nothing (-0.3%) while the price stop did everything (+6.1pp) - test whether that asymmetry
repeats. **Not assumed to transfer** (15j's lesson, applied in the correct direction this time).

**Module `research/explosive_moves/v24_cull.py`** (`.venv/bin/python v24_cull.py data/hermes.db <stop> <trail>`).
**CONTROL VERIFIED: stop=0 trail=0 reproduces the baseline EXACTLY** (sh 0.911, cagr 0.172, cr 30.349,
mdd -0.3772, CULLED 0) - the harness itself changes nothing. Stops are checked on **DAILY closes** within each
month (index_rows has no low; disclosed), exit assumed AT the stop level.

| cull rule | return/vol (H1/H2) | CAGR | MaxDD | Rs1Cr -> | culls |
|---|---|---|---|---|---|
| none (V24 baseline) | 0.911 (0.92/0.905) | 17.2% | -37.7% | 30.35 | 0 |
| hard -8% | 0.913 | 15.7% | -33.0% | 22.84 | 38 |
| hard -12% | 0.897 | 15.7% | -33.3% | 23.01 | 27 |
| hard -15% | 0.907 | 16.1% | -34.6% | 24.87 | 20 |
| hard -20% | 0.908 | 16.4% | -36.6% | 26.11 | 14 |
| hard -25% | 0.916 | 16.9% | -38.9% | 28.48 | 12 |
| trail -8% | 0.874 | 14.0% | -28.1% | 16.72 | 96 |
| trail -12% | 0.878 | 14.4% | -30.3% | 17.97 | 77 |
| trail -15% | 0.869 | 14.6% | -27.9% | 18.76 | 63 |
| **★ trail -20%** | **0.987 (0.993/0.999)** | **17.28%** | **-30.2%** | **30.78** | **36** |
| trail -25% | 0.955 (0.932/1.003) | 17.17% | -35.1% | 30.19 | 26 |

**FINDING: ★V24+TRAIL-20% - same CAGR (17.28% vs 17.2%), MaxDD -37.7% -> -30.2%, return/vol 0.911 -> 0.987,
and BOTH HALVES to 0.993/0.999 - the most half-balanced construct the project has recorded.**

**MECHANISM (why -20%, and why trailing beats hard):** sector indices carry ~15-20% ordinary drawdowns, so any
trail tighter than -20% fires on NOISE (96 culls at -8% -> CAGR collapses to 14.0%); at -20% only genuine
breaks trigger (36 culls in 21.4y). **Hard stops ALL fail** (15.7-16.9%, every one below baseline) because a
stopped-out sector **cannot participate in its own recovery** - a trailing stop rides it up first. Economic
mechanism, not a curve fit - but see the caution.

## ❌ THE 20-22% TARGET WAS NOT REACHED

**CAGR 17.28% vs 17.2% - unchanged.** Two levers tested; **neither raises RETURN.** Recorded plainly:
**better selection does not get from 17.3% to 20-22% on this book** - that is now measured, not asserted.

**The only honest route left on this construct is ARITHMETIC, not research: the cull BOUGHT 7.5pp of drawdown
(-37.7% -> -30.2%); that risk can be SPENT.** ~1.25x on the trail-20% book lands near **19-20% net of Indian
margin cost (~9%/yr)** at roughly V24's *existing* drawdown; ~1.5x passes 21% at MaxDD ~-45%. **This is a
risk-appetite decision on borrowed money - Ramana's to make, NOT a research finding, and NOT advice.**

**⚠ CAUTIONS ON ★TRAIL-20%: (a) it is 1 of 10 variants selected on ONE window** - the exact trap that produced
15h's fake; needs an out-of-sample/fresh-window check before it is acted on. **(b) the 17.3% still rests on a
PRICE-index benchmark** - the owed TR re-cut moves both sides. **(c) not promoted:** `/dash/sector-rotation`
stays on V21; nothing graduates on one window.

**STILL UNTESTED: the stock layer** (15h/16BB/15M) - gated on the ~1,973-name classification job, and 15M
defines its job precisely: **fix the pond, do not pick better.**

### 2026-07-15M - ❌ FINAL: the CULL is real (+6.1pp alpha, Ramana's idea, the biggest lever of the day) but does NOT close the pond gap. The unconditioned RS stock family is REJECTED.

> 🔴 **RETRACTED IN FULL by [2026-07-15O] — corporate-action bug.** Every number below was computed on RAW bhavcopy prices, which are NOT split/bonus adjusted (a 1:2 bonus reads as −50%), while `index_rows` IS adjusted. The fix moved CAGR by ~16pp and hits momentum names hardest. **Do not cite any figure in this entry.**

**Module:** `research/explosive_moves/stock_rs_exits_fix.py` (the 15k harness on 15L's **corrected EQ+BE+BZ**
universe). Ramana authorised the re-run: *"Go ahead and run it."* This is the settled verdict for the family.

**A. Does a cull rule close 15L's -1.24%/qtr pond gap? From 2005-01, 21.4y, top40, 0.15%/side, dead=-100%.
Bench: return/vol 0.66 / CAGR 12.8% / MaxDD -60.9% / 13.12x.**

| exit rule | return/vol | CAGR | MaxDD | beta | alpha/yr | Rs1Cr -> | stops fired |
|---|---|---|---|---|---|---|---|
| **NO EXIT (the pond, unculled)** | 0.39 | 7.6% | -71.3% | 1.18 | **-5.0%** | 4.80 | - |
| **hard -15% cull** | 0.53 | 10.3% | -48.8% | **0.77** | **+1.1%** | 8.18 | 1,424 |
| trail -20% cull | 0.54 | 10.9% | -52.5% | 0.82 | +1.3% | 9.15 | 1,521 |
| trail -15% cull | 0.52 | 9.6% | **-37.5%** | **0.67** | +1.5% | 7.16 | 2,095 |

**THE CULL IS REAL: +6.1pp of alpha (-5.0% -> +1.1%) — the single largest effect measured in the whole
session, and it was Ramana's idea, not the model's.** Note the corrected universe makes the UNCULLED book far
worse than 15k showed (alpha -5.0% vs -0.7%): with BE included we now HOLD names through their surveillance
period and eat the real crater, where the EQ-only bug let them "vanish" at 0%. **So BE-flagged names really do
collapse — that part of the interim story survives; it just is not death.** Real deaths fell 129 -> 23-30.

**BUT IT IS NOT ENOUGH: every variant still LOSES on return/vol (0.52-0.54 vs 0.66) and on wealth
(7.2-9.2x vs 13.12x).**

**B. The two numbers nobody has measured — and the strategy's life depends on BOTH:**

| what a REAL delisting is worth (hard -15%) | alpha/yr | Rs1Cr -> |
|---|---|---|
| dead = 0% | **+3.7%** | 14.44 |
| dead = -50% | +2.4% | 10.88 |
| dead = -100% | +1.1% | 8.18 |

| gap slippage (hard -15%, dead=-100%, @0.30%/side) | alpha/yr | Rs1Cr -> |
|---|---|---|
| 0% (impossible) | +0.6% | 7.34 |
| 1% | **-0.9%** | 5.35 |
| 2% | **-2.5%** | 3.90 |

**At any honest combination (e.g. dead=-50%, slip=1%, real costs) alpha lands at ~ZERO.** A strategy whose
sign depends on two unmeasurable assumptions is not a strategy. **Even the most flattering cell in the entire
grid (dead=0%, no slippage) is return/vol 0.65 vs the bench's 0.66 — it never wins.**

## ❌ VERDICT: REJECT the UNCONDITIONED RS stock family. FAMILY CLOSED.

**~30 variants across the session** — 4 book sizes x 4 hysteresis bands x 4 exit rules x 3 delisting
assumptions x 4 slippage levels x 3 windows x 2 liquidity bars. **ZERO beat Nifty 500 on return/vol.**
**Do not reopen without beating 0.66 / -60.9% / 13.12x net of realistic cost AND slippage.**

## WHAT IS TRUE AND WORTH KEEPING (all measured, all reusable)

1. **SELECTION WORKS** - RS is worth **+1.73%/qtr (~+7%/yr) over random** picking from the same pond
   (15L; stable across dead-name treatments). Never the problem.
2. **THE CULL WORKS** - **+6.1pp of alpha**, and it is slippage-robust on the RISK axis: beta 1.18 -> 0.67-0.82
   and MaxDD -71.3% -> -37.5%/-48.8% at every setting. **Ramana's instrument, the biggest lever found.**
3. **THE POND LOSES** - equal-weight liquid Indian stocks bleed **-4.9%/yr** to Nifty 500 before any pick.
4. **WHY (the lesson): NIFTY 500 IS NOT A PASSIVE BENCHMARK.** It is a rules-based, self-culling,
   cap-weighted basket that continuously drops names falling out of the top 500 by cap/liquidity — and it is
   GOOD. Selection (+7%) + cull (+6.1pp) together recover most of the hole and still do not out-run it.
   **Treat "beat Nifty 500" as beating a well-designed strategy, not a passive index.**
5. **A defensive artefact DOES exist** (not alpha, but real): trail -15% => beta 0.67, MaxDD -37.5% vs the
   bench's -60.9%, CAGR 9.6% vs 12.8%. ~75% of the return for ~61% of the drawdown. Descriptive-only.

## WHAT REMAINS UNTESTED — and exactly what it must do

**Ramana's ACTUAL design (strong stocks INSIDE strong sectors, beating their OWN sector — 15h/16BB) is still
untested.** Today defines its job precisely: **it must NOT pick better (selection already works at +7%/yr) —
it must FIX THE POND.** The sector filter has to yield a universe that does not structurally bleed -4.9%/yr.
Plausible (the sector layer showed alpha at index level, 15f) but **a HYPOTHESIS, not a finding** — and still
gated on the ~1,973-name classification job (16BB). **Do not sell it as likely; five assumptions failed today.**

**Session scoreboard for method (the durable output):** 15h ETF legs · 16BB survivorship · 15j hysteresis
transfer · 15k fill quality · 15L the `series` filter — **five headline numbers, five unchecked assumptions,
five retractions.** Ramana was right on the three calls that mattered (the ask was STOCKS not sectors · exits
are the missing mechanism · a strategy must handle names that collapse). **Audit the universe definition
BEFORE the strategy; treat every first-pass number as provisional until its friction test runs.**

### 2026-07-15L - 🔴 DATA BUG (`series='EQ'`) INVALIDATED 15j/15k + the decomposition that answers "why do index-beating stocks make an index-losing book?"

> 🔴 **RETRACTED IN FULL by [2026-07-15O] — corporate-action bug.** Every number below was computed on RAW bhavcopy prices, which are NOT split/bonus adjusted (a 1:2 bonus reads as −50%), while `index_rows` IS adjusted. The fix moved CAGR by ~16pp and hits momentum names hardest. **Do not cite any figure in this entry.**

**Ramana, 2026-07-15:** *"We are identifying the stocks that outperform Nifty. In that case, what
happened? Have you checked it? Have you done your analysis?"* **The right question, never asked.** 15j/15k
reported P&L and never decomposed it. This entry does, and finds a bug that voids both.

**Modules:** `research/explosive_moves/rs_decompose.py` (buggy, EQ-only) -> `rs_decompose_fix.py`
(EQ+BE+BZ, correct) · `rs_bar.py` (liquidity sweep, ADV bar from argv[2]) · `vanish_audit.py` (the bug proof).

## 🔴 THE BUG: `series='EQ'` reads NSE surveillance moves as DEATHS

NSE moves stocks under surveillance to the **BE (trade-to-trade)** series. Our own data holds **656,007 BE
rows / 2,554 symbols, 2004-2026** (8% of bhavcopy). An EQ-only filter makes a BE-migrated stock **VANISH
while it is still trading normally**. Worse: **BE placement is triggered by exactly the sharp run-up that puts
a stock in the TOP RS DECILE** - so the bug attacks the treatment group specifically.

**`vanish_audit.py` (9,604 EQ-vanish events, the things 15j/15k called deaths):**

| what the "death" really was | count | share |
|---|---|---|
| still trading in ANOTHER series next month | 8,110 | **84.4%** |
| RETURNS to EQ within 12 months (never died) | 7,594 | **79.1%** |
| genuinely gone for good | 1,170 | **12.2%** |

**84% of the "deaths" were fake.** Fixing the filter halves the measured death rate (**0.99% -> 0.47% of the
universe per quarter**). **RETRACTED:** an interim claim that "high-RS stocks die ~3x more often" - they do not
die more, they get **flagged for surveillance** more. Different thing entirely.

**⚠ 15j AND 15k ARE BOTH CONTAMINATED** - both filter `series='EQ'`. 15k's dead=0% treatment (criticised at
the time as too generous) is in fact the **least wrong** of the options, because 84% of the time the stock
really was still there. **Any re-run marking these vanishes at -50%/-100% is nonsense.** Re-run on EQ+BE
before citing either.

## THE DECOMPOSITION (corrected, EQ+BE+BZ, 86 quarterly snapshots, avg universe 437)

Forward-3m excess vs Nifty 500 for: **CONTROL** = every liquid stock equal-weight (no selection at all) ·
**D10** = top RS decile (what we buy) · **D1** = worst decile.

| dead-name treatment | CONTROL | D10 | **selection effect (D10-CONTROL)** | D10-D1 spread |
|---|---|---|---|---|
| dead = -100% | -1.24% (t=-2.21) | +0.48% | **+1.73%** | +4.09% |
| dead = excluded | -0.75% | +1.25% | **+2.01%** | +4.38% |

**The treatments now CONVERGE (+1.73% vs +2.01%)** where the buggy EQ-only version diverged wildly
(+0.13% vs +2.12%). Convergence across assumptions is the signature of a real result.

**FINDING 1 - THE SELECTION IS FINE. RS is worth ~+1.73%/quarter (~+7%/yr) over picking AT RANDOM from the
same pond**, D10-D1 spread +4.09%. **The signal was never the problem.**

**FINDING 2 - THE POND IS THE PROBLEM. CONTROL = -1.24%/quarter (-4.9%/yr), t=-2.21**: an equal-weight basket
of liquid Indian stocks **structurally loses to Nifty 500 before a single stock is picked.** RS then claws
back +1.73%; net D10 = +0.48%/qtr (t=+0.44, NOT significant), and turnover ~330%/yr + beta 1.18 finish it.
**=> Index-beating stocks make an index-losing book because the POND sinks, not because the picking fails.**

**FINDING 3 - WHY the pond sinks (the reframe): NIFTY 500 IS NOT A PASSIVE BENCHMARK.** It is a rules-based
basket that **continuously culls its own losers** - every review drops names that fall out of the top 500 by
cap/liquidity. Our universe culls nobody; it holds everything that trades, including names heading to zero.
**The index has a survival filter built in. We do not. That gap IS the -1.24%.**

**FINDING 4 - "just buy bigger stocks" is DEAD** (`rs_bar.py`, dead=-100%, harshest treatment):

| ADV bar | universe | CONTROL | D10 | selection effect |
|---|---|---|---|---|
| Rs 5 cr/day | 437 | -1.24% | +0.48% | **+1.73%** |
| Rs 25 cr/day | 212 | **-1.52%** | **-1.32%** | **+0.20%** |

Raising the bar makes it **worse on both axes**: the pond still sinks AND **RS selection collapses
(+1.73% -> +0.20%)**. Momentum is a **small/mid-cap phenomenon**; in liquid large-caps it is arbitraged away.
Consistent with this ledger's standing record that only **LOWVOL_MOM qtr large-cap** ever cleared the fundable
bar (1.02 @Rs50cr) - a LOW-VOL tilt, not raw momentum. **Do not re-attempt "raise the liquidity bar" without
beating these.**

## WHAT IT MEANS

**Ramana's exit instinct (15k) was pointing at the right mechanism all along.** The missing piece is not a
better selector - selection already adds +7%/yr. It is **the CULL**: the survival filter the index has and we
lack. That is precisely what a stop-loss / exit rule is.

**OWED NEXT (the one question that matters, now cheaply testable):** re-run the exit test on the corrected
**EQ+BE** universe. Does a cull rule close the -1.24% pond gap? 15k's verdict ("exits fix risk not return,
alpha dies at 2% slippage") was measured on the contaminated universe and **must not be cited until re-run.**

**Also owed:** the real recovery value of the 1,170 genuine delistings (buyouts pay, frauds do not) - only
0.47%/qtr of the universe now, so it matters far less than 15L's buggy version implied.

**METHOD LESSON (5th of the session): every prior number came from an assumption that was never checked -
15h ETF legs / 16BB survivorship / 15j hysteresis transfer / 15k fill quality / 15L the `series` filter itself.
The bug was in the DATA LAYER, beneath every model built on it. Audit the universe definition BEFORE the
strategy: `select series, count(*) from bhavcopy_rows group by series` would have caught this on day one.**

### 2026-07-15k - EXITS (Ramana-directed): they FIX THE RISK but NOT the return - the +3.5% alpha was a frictionless-fill artifact. Fill quality is now THE deciding variable.

> 🔴 **RETRACTED IN FULL by [2026-07-15O] — corporate-action bug.** Every number below was computed on RAW bhavcopy prices, which are NOT split/bonus adjusted (a 1:2 bonus reads as −50%), while `index_rows` IS adjusted. The fix moved CAGR by ~16pp and hits momentum names hardest. **Do not cite any figure in this entry.**

**Module:** `research/explosive_moves/stock_rs_exits.py` (read-only). Same PIT-clean, survivorship-free
bhavcopy universe as 15j (dead companies included). Stops checked against each month's **LOW** (min of daily
lows), so a stop fires when price actually reached it intramonth.

**Ramana, 2026-07-15:** *"even if the companies actually died in 2011 or earlier, it doesn't really matter
because the strategy should address all of those problems. If we selected something that then fell
dramatically, we need to understand that we must have proper exit strategies written."* **He was right, and he
exposed a real hole:** 15j's book had **NO EXIT RULE** - the only way out was dropping off the top-40 at the
NEXT QUARTERLY rebalance, so a name could collapse 50% in month 1 and be held for 3 months. **The -68.1% MaxDD
was the harness's negligence, not the strategy's verdict.** (Ramana asked for stop-losses in his ORIGINAL
brief; they were never built. Second scope-gap of the day.)

**Note on authority:** the sector engine REJECTED a monthly risk pass (V10 ASYM, 0.59 vs 0.70, ledger 15c).
Per 15j, sector-layer results do **not** transfer to the stock layer, so that rejection did **not** bind here.
Correctly re-tested. (The re-test agreed anyway - see the RS-exit row - but for a different reason.)

**A. Exits, from 2005-01, top40, 0.15%/side, NO slippage. Bench: 0.66 / -60.9% / 13.12x.**

| exit rule | return/vol | CAGR | MaxDD | beta | alpha/yr | Rs1Cr -> |
|---|---|---|---|---|---|---|
| **none (15j baseline)** | 0.54 | 12.6% | **-68.1%** | **1.18** | **-0.5%** | 12.68 |
| hard stop -10% | ~0.65 | - | - | - | ~+3.5% | - |
| **hard stop -15%** | **0.65** | **13.1%** | **-47.4%** | **0.78** | **+3.5%** | **13.99** |
| hard stop -20% | 0.62 | 13.5% | -56.3% | 0.89 | +2.8% | 15.05 |
| hard stop -30% | 0.60 | 13.7% | -62.7% | 1.02 | +1.8% | 15.70 |
| **trail -15%** | 0.64 | 12.2% | **-35.1%** | **0.68** | **+3.7%** | 11.76 |
| trail -20% | 0.64 | 13.4% | -50.8% | 0.82 | +3.3% | 14.72 |
| trail -30% | 0.60 | 13.5% | -61.8% | 0.98 | +2.0% | 15.00 |
| **monthly RS exit** | 0.54 | 12.3% | -64.8% | 1.11 | **-0.3%** | 11.90 |

**Finding 1: the DUMB price stop beat the SMART signal exit.** The monthly RS-excess exit did essentially
nothing (alpha -0.3%, beta 1.11, DD -64.8%); the mechanical price stop transformed the book. Ramana's instinct
beat the model-based rule.

**B. THE KILL - gap slippage. Hard -15% from 2005, varying the assumed fill vs the stop price:**

| slippage on fill | return/vol | CAGR | MaxDD | alpha/yr | Rs1Cr -> |
|---|---|---|---|---|---|
| 0% (what A assumed - impossible) | 0.65 | 13.1% | -47.4% | **+3.5%** | 13.99 |
| 1% | 0.58 | 11.5% | -49.0% | +1.9% | 10.24 |
| 2% | 0.51 | 9.9% | -50.6% | **+0.4%** | 7.49 |
| 4% | 0.38 | 6.7% | -53.6% | **-2.7%** | 3.99 |

**With slip 2% + realistic 0.30%/side, alpha is GONE in every window: 2005 -0.1% (6.71x vs 13.12x) /
2011 -0.2% (2.92x vs 5.24x) / 2017 -0.4% (2.10x vs 3.14x).**

**MECHANISM: 1,407 stop fills over 21.4y = ~66 forced sales/year on a 40-stock book.** Every one sells into
weakness and pays the gap. The signal is not the problem; **the bill is.**

**C. WHAT SURVIVES (real, and slippage-ROBUST):** exits fix the **RISK**, not the return.
**beta 1.18 -> 0.78-0.80 at EVERY slippage level**; MaxDD -68.1% -> -47.4%, and still **-50.6% at 2% slip**
vs the bench's -60.9%. Drawdown barely moves as slippage rises (-47.4% -> -50.6%) while alpha collapses
(+3.5% -> +0.4%). **=> The protection is robust; only the profit is fragile.** Honest verdict: exits turn a
leveraged wreck into a genuinely **DEFENSIVE** book - survives crashes far better than the index, makes less
money than it. Real, but not alpha.

**VERDICT: CONDITIONAL - blocked on ONE unmeasured number.** Viability hinges entirely on **real fill
quality**, which was **assumed, not measured** (the same disease as 15h's ETF-tradeability assumption - third
occurrence today). At ~0.5% slip it is viable; at 2% it is dead. The truth is a **distribution**: most stops
trigger on gentle drift and fill near the stop, a few gap hard on news. **A flat 2% on all 1,407 fills is
pessimistic; 0% is impossible.**

**OWED NEXT (cheap, high-leverage, hours not a data lane): MEASURE the actual gap distribution** from our own
22y of daily bhavcopy - for these exact names at these exact trigger points, what did a down-gap through a
stop actually cost? Replaces the assumption with a measurement. **This pays for itself repeatedly: EVERY
future strategy using a stop inherits this same number.**

**Standing caution:** the +3.5% headline survived ~10 minutes before the robustness check killed it. Fourth
time in one session that a promising number was an assumption wearing a result's clothes (15h ETF legs /
16BB survivorship / 15j hysteresis transfer / 15k fill quality). **Treat every first-pass number as provisional
until its friction test runs.**

**Ramana's actual design remains UNTESTED** - everything here is the UNCONDITIONED book (no sector step).
15h/16BB's bar is unchanged, and now has a harder floor: the sector-conditioned build must beat a defensive
book already delivering **beta 0.78 / MaxDD -50.6% net of 2% slip**, not just the raw index.

### 2026-07-15j - FIRST HONEST STOCK BOOK: PIT-clean stock RS **LOSES to Nifty 500 at every setting** (~20 variants, 21y, zero survivorship). Naive alpha -0.5%/yr; hysteresis makes it WORSE.

> 🔴 **RETRACTED IN FULL by [2026-07-15O] — corporate-action bug.** Every number below was computed on RAW bhavcopy prices, which are NOT split/bonus adjusted (a 1:2 bonus reads as −50%), while `index_rows` IS adjusted. The fix moved CAGR by ~16pp and hits momentum names hardest. **Do not cite any figure in this entry.**

**Module:** `research/explosive_moves/stock_rs_pit2.py` (read-only; `.venv/bin/python ... data/hermes.db`).
**Built because Ramana asked "what alpha have we generated?" and the honest answer was "none - nothing exists".**

**Why it is SURVIVORSHIP-FREE (the whole point - contrast 16BB's trap):** the universe at each rebalance comes
from the **bhavcopy itself** - every EQ stock actually trading that month with ADV >= Rs 5cr **that month**.
Companies that later delisted ARE present on the dates they were tradeable (46% of the 2011 universe is dead;
all of them are in). **No index membership, no sector labels** -> nothing is selected for having survived, and
the 4-week membership blocker is bypassed entirely. Signal = 6-month RS excess vs Nifty 500 (same horizon as
the sector engine's 126d). Quarterly, equal-weight. `value` unit-checked (RELIANCE 2017-01-02
value/close x volume = 1.001 => rupees).

**A. Concentration sweep - from 2005-01, 21.4y, 0.15%/side. Bench: return/vol 0.66, MaxDD -60.9%, 13.12x.**

| book | return/vol | CAGR | MaxDD | beta | alpha/yr | Rs1Cr -> | verdict |
|---|---|---|---|---|---|---|---|
| top10 | 0.49 | 11.7% | -75.6% | 1.24 | -0.0% | 10.79 | loses |
| top20 | 0.58 | 14.5% | -70.3% | 1.20 | +1.6% | **18.11** | **most wealth - but -70% DD => leverage, not skill** |
| top40 | 0.54 | 12.6% | -68.1% | 1.18 | -0.5% | 12.68 | loses |
| top80 | 0.53 | 12.0% | -70.2% | 1.18 | -1.6% | 11.28 | loses |

**B. Hysteresis (the sector engine's single biggest lever, 15b/15c) - from 2005, top40. IT BACKFIRES.**

| band | return/vol | CAGR | MaxDD | alpha/yr | turnover | Rs1Cr -> |
|---|---|---|---|---|---|---|
| none (naive) | 0.54 | 12.6% | -68.1% | -0.5% | ~330%/yr | 12.68 |
| -5% | ~0.50 | - | - | -1.8% | ~220%/yr | 9.43 |
| -10% | 0.53 | 11.6% | -71.3% | -1.2% | ~202%/yr | 10.49 |
| -20% | 0.47 | 9.6% | -73.3% | -3.1% | ~168%/yr | 7.17 |
| -35% | 0.35 | 6.2% | -75.9% | **-7.3%** | ~120%/yr | 3.63 |

**KEY TRANSFERABLE LESSON: churn falls exactly as designed (330% -> 120%/yr) and performance falls FASTER.
The medicine that MADE the sector book (hysteresis) POISONS the stock book.** A lever validated on 16 sector
indices does **not** transfer to a 40-stock book. **Never assume a sector-layer constant carries to the stock
layer - re-fit or re-reject every one.** (Cf. 15f's negative-interaction lesson: individually-validated levers
do not compose. Same disease, new layer.)

**C. Window sensitivity - the tell that there is no stable edge.** alpha by start date (top40): 2005 **-0.5%**
2011 **+3.5%** / 2017 **+1.4%**. Best hysteresis (-20%) @0.30%/side: 2011 alpha +2.3% (0.72 vs 0.74) / 2017
alpha +2.0% (0.73 vs 0.77) - **still loses on return/vol in BOTH, with MaxDD -45.7%/-44.1% vs the bench's
-30.0%.** beta sits at **1.13-1.25 everywhere** => the book is structurally a leveraged market bet. An "edge"
whose sign depends on the start date is not an edge.

**AND THE NUMBERS ARE GENEROUS:** when a held name delisted mid-quarter it was carried **flat at 0%** (68-129
stock-months per run) rather than the loss it usually was. True results are somewhat WORSE.

**VERDICT: REJECT the unconditioned stock-RS family.** ~20 variants (4 sizes x 4 bands x 2 cost levels x
3 windows) - **every one loses to Nifty 500 on return/vol.** Directly CONFIRMS this ledger's standing prior
(momentum = **BETA not skill, t=1.99**) on a fully PIT-clean, survivorship-free universe. **Do not re-attempt
naive "buy the strongest stocks" without beating 0.66 / -60.9% / 13.12x net of cost.**

**WHAT IT MEANS FOR RAMANA'S DESIGN (it does NOT falsify it):** this book has **no sector step** - it buys the
strongest stocks in the whole market. Ramana's design buys strong stocks **inside strong sectors**, and
specifically stocks beating **their own sector** (`rs_vs_sector`, 16BB). Different filter, untested. **But the
stakes are now measured: the sector conditioning is not polish on a working book - it must rescue a LOSING
one, creating the entire edge from alpha -0.5%.** Worth knowing BEFORE spending days classifying the 280 dead
names (16BB). **The 15h/16BB pre-registered bar is unchanged and now has a concrete floor: beat return/vol 0.66
and MaxDD -60.9% net of realistic stock costs, or it is a REJECTION.**

### 2026-07-16BG — ERA-FLOOR ANCHOR RE-DERIVATION (2026-07-22): `union_forward.py`'s reproduction gate went RED after the S185-S189 ETF-class CA backfill re-adjusted the era-floor books — INVESTIGATED (legitimate ETF-only drift; base books EXACT) → re-anchored A1/A2/K30 + gave the era-floor books a tolerance BAND; the 7-sibling wiring now deploys GREEN + reproduces to the decimal
- **Trigger:** the gate STOPped at A1 (88.30 vs the 16AW anchor 87.75). Confirmed PRE-EXISTING (the deployed original failed identically) — NOT the sibling wiring, which is a proven no-op (U/B14/C40 reproduce EXACTLY in both).
- **Investigation (the gate demands it before re-anchoring):** **174 ETF-class SPLITs with ex_date ≤ 2026-04-01** were ingested 2026-07-17 (the S185-S189 mf-feed/orphan-cliff backfill, the 16AQ/16AV/16AX class) AFTER the 16AW anchors were set. EVERY drifted CA is an ETF/index-fund (LICMFGOLD · the HDFC/…IETF family · gold/silver ETFs · index-basket splits) — **ZERO real equities**. The era-floor books SELECT ETFs (16AR: NIFTYBEES etc.) so their input-closed legs re-adjusted; the BASE books (U/B14/C40, ETF-free) reproduce EXACTLY. **Legitimate recorded-class repair, not corruption.**
- **Re-anchor (the 16AS loop):** GATE era-floor updated **A1 87.75→88.30 · A2 86.59→86.52 · K30 100.73→100.19** (base unchanged 19.62/25.14/39.75); ANCHOR HISTORY comment appended.
- **Durable fix (the drift recurs with each ETF-CA nightly):** the era-floor books now gate on a **2% tolerance BAND**; the base books stay tight at 0.006 = the real tamper-evidence (any engine/archive corruption hits them too). Stops the recurring false-STOPs without weakening the meaningful check.
- **Result — GREEN + siblings verified end-to-end:** all 6 gate rows OK; §1b reproduces **K30-HOLD 27.2% · A2-HOLD 26.6% · K30-DEEP-HOLD 27.5%** (recorded, to the decimal); §3b forward criteria self-suppress at 0 quarters (fire Oct-3+). Deployed (union_forward.py md5 `7dcb6383`, box == repo). **The 7-sibling forward runner is LIVE and green.**

### 2026-07-16BF — THE STACKED VARIANT SEALED (2026-07-22): K30-DEEP-HOLD = deeper-turn<20 (16BE) × hold-band top-60 (16BD) on the K30 base — the two levers COMBINE (net 17.8→19.2% AND drawdown −38→−29%), the best of every variant; sealed as the 7th union sibling (sha256 b705f770…)
- **The stack test (full-book gauntlet, K30 config, baseline reproduces 26.4/17.8 = gate; `build_stacked_gauntlet.py`):** hold-band-only **19.0/−38** · deeper-turn<20-only **18.6/−29** · **STACKED turn<20+hold60 = 19.2% / −29%** (₹1cr 34.8cr) · turn<25+hold60 = 19.1/−33 (confirms not a single-threshold artifact). The stack keeps the hold-band's RETURN boost AND the deeper-turn's DRAWDOWN cut → **best net + lowest DD of all seven variants**; +1.4pp net AND −9pp drawdown vs the sealed K30.
- **Levers are ORTHOGONAL:** hold-band changes the exit/hold rule (+1.1pp, DD flat); deeper-turn changes the entry quality (+0.8pp, DD −9pp). Net gain not fully additive (overlap) but the DRAWDOWN cut is fully retained.
- **SEALED as K30-DEEP-HOLD (7th union sibling):** `docs/prereg/union-k30-deephold-prereg.md` sha256 **b705f77091f4ff5caeb3e00a85a4d85c38d21b0cfe6a19c563e17be23da0d615** — COMPOSITE-30 verbatim except the two marked levers; same 4 frozen criteria; near-identical to K30/K30-HOLD (adjudication picks ≤1). ⚠ **HIGHEST overfit risk of the siblings** (TWO stacked in-sample levers) — disclosed in the prereg; deflate hard. Forward-judged 2026-10-03+ at ≥8 quarters. Runner `build_stacked_gauntlet.py` (sealed engine untouched).

### 2026-07-16BE — RSI-OF-RS REVERSAL, two forks tested (2026-07-22, Ramana "test variants with RSI on RS; is it sector- or index-relative?"): (1) SECTOR-relative >> INDEX-relative — the sealed choice CONFIRMED; (2) a DEEPER oversold threshold is a genuine DOUBLE-WIN in the union (+0.9pp net AND −5 to −9pp drawdown), but does NOT rescue a standalone reversal book
- **What the union actually evaluates (traced, not assumed):** the TURN leg `rsi_of_rs_recovery` runs RSI on `rs_at = stock / its SECTOR index` (`union_ladder_val.py:224/237`); the TREND leg `sig_rsi` runs RSI on the stock's OWN price. A stock qualifies on EITHER (the union). Index-relative RS as the reversal denominator was NEVER tested (dim6.py used sector throughout) — a genuine untested fork.
- **Finding 1 — SECTOR ≫ INDEX (selector test, fwd-3m-excess, dim6 decomposition, `rsirs_denom_test.py`):** sector-relative 6b GEO **+0.47%**/q · +1.38% vs base · **SIG** (reproduces the recorded 6b). INDEX-relative (stock/Nifty500) GEO **−0.48%** (FAILS the positive-geometric bar) · +0.47% vs base · **ns**. BOTH/EITHER combinations dilute. **Do NOT switch to index-relative** — beating your OWN SECTOR is a cleaner turn signal than beating the market (whose RS is muddied by sector beta). The design choice is now empirically vindicated.
- **Finding 2 — DEEPER oversold = a DOUBLE-WIN in the union (full-book gauntlet, K30 config, baseline reproduces 26.4/17.8 = gate; `build_reversal_gauntlet.py`):** deepening the TURN floor <30→<25→<20 RAISES net CAGR **AND** CUTS drawdown, monotone on DD: **<30 → 17.8% / −38%** · **<25 → 18.7% / −33%** · **<20 → 18.6% / −29%**. Robust across both deeper thresholds. Mechanism: a deeper RS washout = higher-conviction turn → stronger bounces (more return) + fewer false turns (less drawdown). **This IS the lift-CAGR-AND-cut-drawdown result the whole R-inquiry was chasing.**
- **Finding 2b — a STANDALONE reversal book is NOT viable (buried, confirms the ledger):** the TURN leg ALONE (no TREND) nets ~**10.8–11.3%** (BELOW the index +11.7%), thin (9–24 names/quarter), at every threshold. Reversal-on-RS needs the TREND leg (the union) — it is not a fundable book by itself (matches the recorded "6b alone 15.4% flat").
- Runners (additive, sealed engine untouched): `research/explosive_moves/gauntlet/rsirs_denom_test.py` (selector) + `build_reversal_gauntlet.py` (full book). IN-SAMPLE (net-of-cost ≠ net-of-selection). **➡ STRONG SEAL CANDIDATE:** the union with **TURN<20** (the double-win) — recommend sealing, ideally STACKED with the K30-HOLD hold-band lever (16BD) to combine both gains; not sealed yet (owner call).

### 2026-07-16BD — IMPROVING THE R LOGIC (2026-07-22, Ramana "lift CAGR, cut drawdown, think outside the box, don't repeat what failed"): three ideas tested on the 16BC gauntlet — C (hold winners longer) is a ROBUST modest keeper (+1.1pp net, DD unchanged) → SEALED as K30-HOLD; B-proxy INERT → buried; governance-B UNTESTABLE → forward-only
- **C — hold winners longer (KEEP → SEALED K30-HOLD):** retain a held name while it stays in the top-60 (2× the 30-name selection); refill to 30 from top-ranked non-held survivors. K30 net-of-gauntlet **17.8→19.0% (₹1cr 27.6→33.6cr), worst-drop −38% UNCHANGED**, turnover 281→267%/yr. Lifts BOTH gross (26.4→27.2 flat) AND net → a better-SELECTION effect (a still-strong name beats a fresher swap), not merely a cost cut. **Robustness sweep = why it's sealed not a lucky threshold: net gain POSITIVE at EVERY band 40/45/50/55/60 (+0.7/+0.6/+0.9/+1.2/+1.1), drawdown pinned −38% throughout, gain plateaus ~2× holdings.** A2 identical (band 55-60 = +1.1). Band fixed a priori at 2× holdings (mid-plateau, NOT the peak). IN-SAMPLE; net-of-cost ≠ net-of-selection — deflate forward.
- **B-proxy — price-crash filter (BURIED, inert; do not re-attempt):** drop any name with a ≤−25% single-day fall in the trailing 63 sessions. **Removed ZERO names/rebalance across 2005-2026** — union momentum selection ALREADY excludes just-crashed stocks (a name that cratered has weak recent performance, never qualifies). Zero effect on net or drawdown. Redundant with momentum.
- **B — governance blow-up filter (FORWARD-ONLY, untestable historically):** pledge/promoter-sell/surveillance/insider/credit feeds have NO point-in-time history before ~Nov-2025 (pledge from 2025-11 · surveillance from 2026-07 · insider from 2025-11 · credit 31 rows/6 syms). Cannot be backtested; can only run as a LIVE overlay judged in ~2 years. Recorded, not sealed. Idea B's INTENT (dodge the −80% frauds) is sound; only its evidence is missing.
- **K30-HOLD SEALED (the 5th union sibling):** `docs/prereg/union-k30-hold-prereg.md`, sha256 **e6994c19d0f64447747fb3afcf232d2ed88187da910df7ba151f1d3c202bcb37** — COMPOSITE-30 verbatim EXCEPT the hold-band; same 4 frozen criteria; near-identical to K30 (disclosed → adjudication picks ≤1 among passers, not two discoveries). Additive runners (sealed engine files untouched): `research/explosive_moves/gauntlet/build_c_bproxy.py` (toggled-rule variant) + `build_band_sweep.py` (robustness). Judged 2026-10-03+ at ≥8 forward quarters beside the other four siblings.
- **A2-HOLD ALSO SEALED (the 6th sibling, the lower-DRAWDOWN HOLD variant):** the SAME 2×-holdings hold-band on the A2 base (equal-weight top-40) — retain a held name while it stays in the top-80, refill to 40. A2 net-of-gauntlet **17.2→18.6%** (₹1cr 25.0→31.5cr), worst-drop **−33% UNCHANGED**, turnover 274→260%/yr; robust across bands 60/70/80/90 (+1.1/+1.4/+1.4/+1.6). `docs/prereg/union-a2-hold-prereg.md` sha256 **17e0dd1a3a983e06ace50d7fd3c97d50b6f88ce692d33f7e8d7be821b3f440d1**. ⚠ EW-undercharge caveat (16BC) → A2-HOLD's net is mildly OPTIMISTIC vs the drift-charged K30-HOLD; its case is the SHALLOWER drawdown (−33% vs K30's −38%), NOT a higher net. Runner `build_a2_sweep.py`. Shares the hold-band lever with K30-HOLD → adjudication picks ≤1 across all six.

### 2026-07-16BC — THE ZERODHA REAL-COST GAUNTLET (S196, Ramana real-money question): factor baskets vs the union family net of real Indian trading cost 2005-2026 — factor baskets DON'T beat the index; the UNION family DOES (K30 +17.8%, A2 +17.2% vs index +11.7% in-sample) — full record `docs/zerodha-cost-gauntlet-2026-07-18.md`
- **Gauntlet** = per-name: half tier bid-ask spread (T1<5cr 1.5% / T2 5-25cr 0.6% / T3 25cr+ 0.25%) + 0.5×ATR slippage + real Zerodha delivery charges (~0.2%/yr, negligible) + 20% STCG. Validated: flat mode reproduces `cost_realism.csv` (risk-adj monthly −1.3 vs recorded −1.5, lowvol-mom qtr +13.2 vs +13.3) AND every sealed union PR CAGR (U 17.5→17.3 … K30 26.4→26.4). Survivorship-clean (4,236 EQ incl. 1,061 delisted). **Key mechanism: cost = market-impact × turnover, NOT brokerage — Zerodha's cheap charges do not rescue a high-churn book.**
- **Factor baskets (₹1cr, net):** Pure-LowVol +7.6 · STEADY LowVol-Mom **+11.0 (₹8.89cr)** · RiskAdj-qtr +5.2 · LowVolMom-monthly −1.3 · Mom6-qtr +1.7 · Mom6-monthly −13.4 · RiskAdj-monthly −10.9. **NONE beats the index +12.5% (₹12.72cr)**; fast monthly books destroy capital (₹1cr → ₹5-8 lakh). The pretty 20-28% are all gross/flat: same fast book = ₹71cr (fake cost) vs ₹0.08cr (real). Confirms the D143/16BA cost-illusion finding estate-wide.
- **Union family (₹1cr, net, SAME gauntlet):** U +11.5 · β14 +13.1 · C40 +14.8 · **A2 +17.2 (₹24.99cr)** · **K30=COMPOSITE-30 +17.8 (₹27.77cr)** vs same-window index +11.7% (₹9.38cr). DD −28 to −38% (index-like). **FIRST estate strategy to survive the harsh gauntlet**; cost 7.7%/yr (vs fast baskets 20-40%). Survives because quarterly + more-liquid picks + trailing stops/let-winners-run.
- **K30 robustness:** execution-lag T+1 = **+16.7%** (−1.1pp, not a fill artifact). **AUM ladder (`cost_participation.py` sqrt-impact): capacity ceiling ~₹25-50cr** — +22.1 @₹5cr · +16.6 @₹25cr · +12.5 @₹50cr(≈index) · +7.0 @₹100cr · −0.3 @₹200cr · −25 @₹1000cr. **PERSONAL-SCALE only.**
- **Codex validated BOTH** (factor cost model review + union gauntlet independent re-run): reproduced the tables to the decimal, engine intact; correct wording = "in-sample survivor under an AUM-blind harsh slippage gauntlet, pending 2026-10-03 forward test." Caveats: EW books (U/B14/C40/A2) slightly undercharge continuing-name reweight → mildly optimistic; K30 (drift-weighted) charged correctly; AUM-blind (not an institutional-capacity proof); IN-SAMPLE (net-of-cost, not net-of-selection).
- **⏳ OWED:** the sealed **2026-10-03 forward test** (the only real OOS judge). Deliverable = 17-sheet `Equity_Baskets_with_UNION_family_2005-2026.xlsx`; scripts `research/explosive_moves/gauntlet/`.

### 2026-07-16BB — 🔴 DATA AUDIT before the stock build: PIT sector membership is the ONE blocker, and it is BOUNDED (~1,973 names, 280 of them dead)

> **⚠ Tag note (renumbered 2026-07-18, S195):** minted as `2026-07-15i`; renumbered to **`2026-07-16BB`** to heal a duplicate-tag collision (the SIGNIFICANCE PASS that drove **D139** keeps `§15i`). Older inbound refs to "§15i" that mean the *data audit / classification blocker* — `codex-stock-selection-brief.md` (now `§16BB`) and `docs/strategies/sector-rotation.md` §"original spec" (still labelled §15i) — belong HERE, not to the significance entry.

**Ramana's directive (2026-07-15):** build the strategy on STOCKS, not indices. *"For media, realty, consumer
durables we cannot invest directly; we must invest through the stocks."* + *"identify the top-performing stocks
within the strongest sectors"* + *"we can't rely entirely on one stock, nor can we diversify excessively"* +
**the sharp point: *"if a stock is performing well within its NARROW index, we will target it"*** — i.e. stock RS
measured **against its own sector**, not against the broad benchmark. A stock beating its own hot sector is a
different and harder test than a stock carried by its sector.

**AUDIT RUN FIRST (VPS read-only, 2026-07-15) — do NOT re-derive, these are measured:**

| Need at date *d* | Status |
|---|---|
| Which sectors are strong | ✅ `index_rows` 2005→2026, PIT-clean, needs no membership. **The V24 ladder is reusable as the sector layer.** |
| Each stock's RS vs its OWN sector | ✅ vocabulary EXISTS: `stock_signals.rs_vs_sector_today` + slopes 1/3/6/12/18/24m, `rs_vs_broad_*`, `rsi_of_rs`, `rs_phase`, `rs_rank` — **2011-06-22→2026-07-14, 3,714 dates, 5.97M rows** |
| Stock prices incl. dead names | ✅ `bhavcopy_rows` **2004-07-23→2026-07-14, 9.39M rows** — delisted names ARE present up to their last trading day |
| **Which stocks belonged to that sector at date *d*** | ❌ **THE BLOCKER — see below** |

**🔴 THE BLOCKER — `stock_index_membership` holds FOUR WEEKS (2026-06-17→2026-07-14, 20 snapshots, 32 indices).**
We know today's constituents. We do NOT know who was in Nifty Auto in 2011/2015/2025. `stock_signals.primary_sector`
is DERIVED from that snapshot → it covers only **246 of 3,558** trading symbols (7%), i.e. essentially the current
index members = the winners' club.

**🔴 WHY THIS IS A TRAP, NOT AN INCONVENIENCE — the universe churns brutally:**
- 2011: **1,650** symbols traded → only **895 still trade in 2026**. **46% of the 2011 universe is GONE.**
- 2016: 1,812 traded → 1,178 alive. 35% gone. · 2026: 3,558 trade.
- **`company_tags` labels 384 symbols; `company_about` 593; and of the 755 names that died since 2011, EXACTLY
  ZERO carry any label.** The hole is total, not partial.

**Backtesting "top RS stocks in Nifty Auto" over 2011→2026 with TODAY's member list would select from companies
that survived 15 years AND earned promotion into the index. It would print a spectacular fake number (plausibly
Sharpe 1.5–2.0) and be worthless.** Recorded so no future session builds it by accident.

**✅ BUT THE JOB IS BOUNDED — survivorship only bites for names the strategy could actually have BOUGHT.**
A real book needs a liquidity floor. Scoped at an ADV bar over ALL years (measured):

| Liquidity bar (avg daily traded value) | ever-liquid & NOW DEAD | ever-liquid & alive | total to classify |
|---|---|---|---|
| **≥ ₹5 cr ADV** | **280** | 1,693 | **1,973** |
| ≥ ₹25 cr ADV | **113** | — | — |

Cross-check: `research.db.fundamentals_history` independently covers **1,998** symbols — the same ~2,000-name
"universe that ever mattered". (It has NO sector field — `symbol/period_type/period_end/report_date/metric/value/
source` — and is screener-sourced, so **Guardrail #8 forbids extending it**. Not the classification route.)

**Snapshot of the bias magnitude at the ₹5cr bar in 2011: 179 survivors vs 85 dead ⇒ the dead are ~32% of that
year's investable universe.** Excluding them is not a rounding error; it is a third of the book.

**VERDICT: the stock build is FEASIBLE and gated on ONE deliverable — a PIT-safe sector classification for
~1,973 symbols** (1,693 live: NSE industry classification = primary source, Guardrail #8-clean, automatable ·
**280 dead: the genuine work**, but 280 is tractable — and only 113 at a ₹25cr bar). Not 1,500 shells. Bounded.

**RECOMMENDED DESIGN — own sector COMPOSITES, not index membership** (decided; solves three problems at once):
define a sector as *every liquid stock classified in that industry at date d* and build the composite ourselves.
(a) **Investable by construction** — the sector IS a stock basket, so Media/Realty/Consumer Durables stop being
untradeable (kills the §6-bis instrument flaw, ledger 15h); (b) **wider pond** — Nifty Auto ≈ 15 names, the Auto
*industry* ≈ 60, and stock-picking needs selection; (c) **far less survivorship bias** — a company does not EARN
its way into "Auto" by outperforming; it earns its way into *Nifty* Auto. Industry ≠ a performance filter.
(d) membership history is no longer needed — the gap is dissolved, not backfilled.

**Honest residual + the mitigation:** NSE classification covers LISTED names, so the 280 dead still need labels.
**Bound the bias rather than hand-wave it** — run the study twice (dead names assumed average-performing, then
assumed worst-decile) and report the RANGE. An honest error bar beats a fake point estimate.

**THE BAR STAYS PRE-REGISTERED (from 15h, unchanged):** stock momentum is ledger-recorded **BETA not skill
(t=1.99)**; only LOWVOL_MOM qtr large-cap fundable (1.02 @₹50cr); stock legs cost more than index legs.
**A constituent build that merely MATCHES the sector-index book is a REJECTION, not a result.**

### 2026-07-15l — THE STOCK LAYER, FIRST SIMULATION (Ramana's two-step method, run end-to-end): REJECTED under the pre-registered bar — worse risk-adjusted, worse drawdown, and the gross uplift is a cost illusion

**⚠ Read alongside §§2026-07-15j/k (a PARALLEL, independent lane, same day) before treating this as the last
word on stock selection.** That lane tested the **UNCONDITIONED** question — does picking top-RS stocks from the
WHOLE market (no sector filter at all) beat Nifty 500? — on a genuinely **survivorship-free** universe
(bhavcopy itself as the universe each month, so delisted names are correctly present on the dates they were
tradeable — stronger data hygiene than this entry's current-day-classification approach). **Their answer: NO,
at every one of ~20 variants tested** (naive alpha −0.5%/yr; return/vol never clears the 0.66 bench). **This
entry answers a DIFFERENT, narrower question** — does picking top-RS stocks WITHIN sectors V24 already flagged
as strong beat V24's OWN index-sector book? — also **REJECTED**, independently, by a different method, on a
different universe-construction. Two honest rejections of two different constructions converging is a stronger
signal than either alone. **Their most transferable finding applies directly to this entry's own weak point:**
they found sector-layer levers do not transfer to the stock layer (hysteresis, the sector layer's biggest
winner, backfires on stocks) — analogous to this entry's own concentration-risk finding (idiosyncratic single-
stock risk isn't compensated the way diversified sector risk is). **And Ramana separately told that lane
"we must have proper exit strategies written" — a gap THIS engine has too:** `sector_stock_layer.py` has no
intra-quarter stock-level stop; a name held here can only exit at the next quarterly rebalance, exactly the
negligence their exit study (§15k) diagnosed and partially fixed (hard stop −15% cut MaxDD −68%→−47% at
beta 1.18→0.78, though the alpha it bought is slippage-fragile — gone entirely past ~2% realistic slip). **This
entry's own worse-than-V24 drawdown may be PARTLY a missing-exit-rule artifact, not purely a stock-picking-risk
finding** — added to the owed list below, informed by their measurement rather than re-deriving it.

**What ran.** Ramana's exact design, built and simulated: **Step 1 (sector selection) = V24, UNTOUCHED** — the
validated engine's own `build()`/`kill_on()`/quarterly clock, called directly, never re-derived. **Step 2 (stock
selection, NEW)** — inside each qualifying sector, rank its stock universe by **RS-excess vs that stock's OWN
sector composite** (trailing 6m stock return minus the trailing 6m equal-weighted sector-universe return) — his
own discriminator, verbatim: *"if a stock is performing well within its NARROW index, we will target it."* Top
~4–8 names/sector selected, weight = sector-weight × RS-rank, 12%/name cap, **whole portfolio capped at 33
names** (his instruction: "a ceiling of 30 to 35 stocks… about a crore"). Module:
`research/explosive_moves/sector_stock_layer.py` — self-contained, reproducible, run **read-only against the
real production DB** (not a scratch extract).

**The universe — genuine primary source, one disclosed limitation.** Each of V24's 16 sectors' OWN current
(2026-07-15) official NSE constituent list, fetched live from `niftyindices.com/IndexConstituent/<slug>.csv`
(the SAME access pattern already approved and used by `src/automation/membership.py`) — UNION'd with the
Nifty-500's current "Industry" tag wherever the match is unambiguous (Auto 15→39, IT 10→27, FMCG 15→28, Metal
15→20, etc.; Bank/PSU Bank/Private Bank/Financial Services/Infrastructure/Media/Healthcare/Pharma deliberately
left un-widened — their broad Industry tags overlap ambiguously). **268 distinct symbols, 16 sectors**,
committed as a dated snapshot `research/explosive_moves/nse_sector_classification_2026-07-15/` (91 KB, 17
CSVs) so the module is reproducible without re-fetching. Zero Screener dependency (Guardrail #8 clean).

**🔴 DISCLOSED LIMITATION (read before quoting any number, per the 15h standing rule — above the stat, not
buried):** this universe is **CURRENT-DAY classification applied statically across 2005–2026**. This is **NOT**
the survivorship trap 15h/16BB already banned (today's narrow INDEX MEMBERSHIP standing in for 2011's, which
structurally selects names that EARNED their way in by outperforming) — industry/sector classification is not a
performance filter, so the bias is structurally much smaller — but it is real: a stock that changed industry, or
that delisted before 2026-07-15, is mis-handled. **It fails CONSERVATIVE, the opposite direction from the banned
mistake: delisted names are EXCLUDED from the universe entirely, never fabricated a performance.** This is a
first, honestly-scoped, genuinely primary-sourced simulation on **268 live names** — not yet the canon's
ultimate ~1,973-symbol PIT-safe build (§16BB) with its ~280 dead names and two-sided bias bound. That remains
owed; this is real, useful evidence in the meantime, not a substitute for it.

**Results — n=258 months (21.5y), reproduced against production `data/hermes.db`, three cost scenarios to
separate the COST story from the SELECTION story (stock legs cost more than index legs, per the pre-registered
bar — the flat index-ETF assumption of 0.15%/side is NOT realistic for individual mid/small-caps):**

| | ret/vol | H1/H2 | CAGR | MaxDD | ₹1Cr → | vs V24 (index-only, §15g) |
|---|---|---|---|---|---|---|
| Gross (0.15%/side, same as index — a floor, not a claim) | 0.817 | 0.86/0.77 | 17.82% | −42.8% | ₹33.99 | CAGR/wealth BEATS V24; ret/vol and MaxDD do not |
| **Realistic (0.40%/side — the disclosed assumption)** | **0.775** | **0.83/0.71** | **16.66%** | **−43.2%** | **₹27.47** | **loses on ret/vol, MaxDD, CAGR, wealth** |
| Stress (0.70%/side) | 0.723 | 0.79/0.65 | 15.28% | −43.8% | ₹21.25 | loses on everything, by more |
| **V24 (index-only, for reference)** | **0.911** | **0.92/0.91** | **17.2%** | **−37.7%** | **₹30.35** | — |
| Nifty 500 buy-and-hold (same window) | 0.637 | 0.58/0.78 | 12.51% | −62.0% | ₹12.60 | both stock-layer and V24 clear this easily |

**Verdict: REJECTED under the pre-registered bar, at the disclosed realistic cost.** At 0.40%/side the stock
layer does not beat V24 on return/vol (0.775 vs 0.911), MaxDD (−43.2% vs −37.7%), CAGR (16.7% vs 17.2%), or
terminal wealth (₹27.47 vs ₹30.35) — it roughly re-derives V21's numbers (0.875/₹27.02) with a WORSE risk profile.
This is not a coin-flip miss; it fails on every axis simultaneously.

**The honest, non-obvious part — the shortfall is BOTH a cost story AND a concentration story, and the second
one is NOT a cost artifact.** Gross of realistic cost (the 0.15% row), the two-step method DOES show real
excess wealth and CAGR over V24 (₹33.99 vs ₹30.35; 17.8% vs 17.2%) — picking top-RS-within-sector stocks carries
a genuine gross signal, consistent with momentum being real-but-costly everywhere else in this ledger. **But the
drawdown is WORSE than V24 at EVERY cost level tested, including gross** (−42.8% to −43.8% vs V24's −37.7%) —
concentrating ~20–29 individual names inside a hot sector is inherently riskier than holding the whole
diversified sector index, and this is a **structural, not a cost-driven**, effect: idiosyncratic single-stock
risk is not compensated on a risk-adjusted basis here (ret/vol never reaches V24's 0.911 at any cost tested).
Realistic transaction costs then erode most of the gross wealth edge on top of that (₹33.99→₹27.47→₹21.25 across
the three scenarios) — the SAME "no fundable equity-factor edge beats holding the index net of cost" finding this
whole ledger has recorded repeatedly, now confirmed at the within-sector stock-selection layer too.

**Sanity checks run before trusting the number (a naive engine bug was the live risk, not a fluke result):**
holdings inspected for 3 recent quarters — real, sector-consistent, recognizable Indian names (FORTIS/LAURUSLABS/
BPCL/SBIN/AXISBANK/RELIANCE/ONGC/COALINDIA…), never garbage; portfolio weights always sum to ≤1 (residual to
sleeve); per-name cap (12%) and total cap (33) both respected in every quarter (max observed 32); **3/86 quarters
had zero picks** (pure cash/sleeve, matching V24's own occasional all-cash quarters — not an artifact); **median
22 stocks/quarter** when invested (below the 30–35 ceiling because selection genuinely REQUIRES positive
RS-excess vs the sector's own composite — the engine does not force-fill to hit a quota, a real economic
constraint, not underbuilding).

**Owed before this can be called final (do not re-run hoping for a different number without these):** ① the
canon's ~1,973-symbol PIT-safe classification with the two-sided dead-name bias bound (§16BB) — this 268-name
live-only cut is a first pass, not that build; ② a real per-name ADV/impact cost model replacing the flat
0.40%/side proxy (same rigor item as the sector layer's own owed instrument audit, §6-bis); ③ a significance
pass on THIS result (same JK/bootstrap/MDE discipline as §15i) before treating even the REJECTION as more than
directionally solid — n=258 with a 6/16-sector-average book has real estimation noise too; ④ **an intra-quarter
stock-level exit rule (Ramana's ask, surfaced by §15k)** — this engine currently has none; §15k's own measured
number (hard stop −15% cuts MaxDD −68%→−47% at beta 1.18→0.78, but the alpha it buys needs real fill-quality
data, not an assumption) is the concrete starting point, not a fresh design.

**Sample current holdings (2026-04-01, the latest quarter, at the disclosed 0.40%/side cost) — for illustration,
not a live recommendation (this ladder is DESCRIPTIVE, per §15h; the bar above says REJECT):** 29 names, led by
BHARATFORG 8.8%, MRPL 7.6%, SHRIRAMFIN 7.2%, ONGC 6.6%, BSE 6.4%, CHENNPETRO 6.1%, SBIN 5.9% — drawn from the
7 sectors that qualified that quarter (Financial Services 23%, Oil & Gas 24%, Auto 17%, Healthcare 11%,
Infrastructure 10%, PSU Bank 9%, Metal 6% of the invested book). Full 86-quarter holdings history in
`research/explosive_moves/out/sector_stock_layer_result.json`.

### 2026-07-15h — 🔴 SCOPE FLAW (Ramana-caught): the entire V8→V32 ladder selects SECTORS, never STOCKS — half the brief was never built, and the index expression may not be tradeable

**Ramana, 2026-07-15:** *"I have noticed major flaws… you are identifying that this will drive the stock. What
you are currently identifying is that you will take the index itself… I haven't seen a single stock listed…
you are not picking the stocks. Please confirm."* **CONFIRMED. He is correct.**

**The finding (verified in code, not from memory):** the V24 engine
(`research/explosive_moves/sector_rotation_v24_final.py`) reads exactly ONE table — `index_rows` — and contains
**zero stock symbols**. Reproduce: `grep -ciE "stock_signals|bhav|symbol|stock_rows" <that file>` → **0**. Every
quarter's "holdings" in the **86-quarterly-rebalance** book (**86 = a COUNT of quarter-start decision dates, 21.5y × 4/yr — NOT a percentage; Ramana has twice read it as "86%"**) are **index names** (Nifty Auto, Nifty IT…), not companies. The
book never held a stock; it rotates between indices.

**What this invalidates — precisely.** Nothing in the ladder's *arithmetic* is wrong; the numbers reproduce.
What was wrong is **what they were claimed to measure**. Sharpe 0.91 / α +7.1%/yr / ₹1 Cr → ₹30.35 Cr describes
**the sector-selection half of an unfinished strategy**, priced on instruments that in ~⅜ of cases don't exist.
It was presented as a finished result.

**Root cause = a FRAMING failure, not a missing feature.** The limitation WAS recorded — as one bullet
("V2 constituent expression… where the stock-selection edge gets tested") buried in the canonical page's §9
open items, while the page's status header led with a Sharpe ratio. Burying the scope caveat under the headline
number made a half-strategy read as a whole one. **Standing lesson: when a build covers part of a brief, the
scope gap goes ABOVE the headline stat, not in the open-items list.** The canonical page now carries a
blocking SCOPE banner as its first element (`docs/strategies/sector-rotation.md`).

**A second, compounding flaw surfaced by the same audit — instrument reality (canonical §6-bis).** §3-F prices
the sector legs as "liquid sector ETFs/index futures @ 0.15%/side". **That was asserted, never verified.**
Roughly **6 of 16 sectors — Media · Realty · Consumer Durables · Infrastructure · Oil & Gas · Metal (thin) —
have no liquid Indian index instrument.** So (a) the headline stats are optimistic by an **unquantified**
amount, and (b) **the priority inverts**: for those sectors, buying the constituent stocks is not phase two,
it is **the only executable expression**. The constituent build is now the execution path for a large minority
of the book, not an enhancement to a working one.

**Verdict: the ladder is DEMOTED to "sector-selection layer, paper, upper-bound".** Not rejected — the
sector-selection logic still measures what it measures, and V24 remains the best config of it (Ramana designated
V24 as the layer to carry forward, 2026-07-15h — a designation of *what the stock build sits on*, NOT a
promotion; `/dash/sector-rotation` stays on V21). **No number from this ladder may be presented, quoted, or
promoted as a complete strategy result.**

**Owed, in order:** ① **the ≤40-stock constituent build** (top-RS stocks inside V24's qualifying sectors,
sector-RS × stock-RS weights, per-sector stops) — the untested half of the brief. **Pre-register its bar before
running it:** stock-level momentum is recorded in this ledger as **BETA not skill (t=1.99)**, with only
LOWVOL_MOM qtr large-cap fundable (1.02 @ ₹50cr), and stock legs cost more than index legs — **matching the
index book counts as a REJECTION, not a result.** ② the instrument/ADV audit + per-leg cost re-cut. ③ the TR
re-cut + significance pass (still owed, four selection rounds deep).

### 2026-07-15i — SIGNIFICANCE PASS (closes the §15h owed item ③, significance half): the V21→V24→V32 ladder's final rungs are NOT STATISTICALLY DISTINGUISHABLE — and the "Sharpe" label is wrong

> **⚠ Tag note:** the PIT-sector DATA AUDIT once shared this `15i` tag; it was renumbered to **§2026-07-16BB** (2026-07-18, S195) to resolve the collision. Inbound "§15i" refs meaning the *classification blocker / ~1,973-name audit* belong to **§16BB**, not this entry.

**What this settles.** §15h left three items owed; this closes the significance half of ③. The ladder's
*arithmetic* was never in question (§15h: "the numbers reproduce"). What was never asked is whether the
**differences between the rungs are distinguishable from noise**. They are not. Ramana's V24 designation
(§15h) is therefore correctly a **mechanism call** — it has no evidential basis, and **none was available
on this window**. That is a finding about the evidence, not a criticism of the choice.

**Reproduction gate FIRST (no test is trusted until the engine reproduces the record).** The harness
`research/explosive_moves/sector_rotation_significance.py` does not re-implement anything — it exec's the
validated Round-4 engine (`sector_rotation_exp4.py`) above its driver line and calls its own `simulate()`.
Reproduced vs ledger: **V21 0.875/₹27.02 · V24 0.911/₹30.35 · V32 0.898/₹31.15 — all MATCH** (§15f/§15g
exactly). n = **258 monthly observations / 21.5 years**.

**Test 1 — Jobson-Korkie difference-of-Sharpe, Memmel (2003) correction** (the standard analytic test for two
*correlated* ratios; run on per-period Sharpes, difference annualised only for display — feeding annualised
Sharpes into the statistic is the classic error and would have manufactured z=4.56):

| pair | ΔSharpe/yr | corr | z | p | verdict |
|---|---|---|---|---|---|
| V24 − V32 | +0.013 | 0.9719 | +0.244 | **0.807** | NOT distinguishable |
| V24 − V21 | +0.036 | 0.9957 | +1.747 | **0.081** | NOT distinguishable |
| V32 − V21 | +0.023 | 0.9749 | +0.463 | **0.643** | NOT distinguishable |

**Test 2 — paired stationary block bootstrap** (Politis-Romano, geometric blocks mean 6m, wrap-around, 20k
draws, the two books' months resampled JOINTLY so cross- and auto-correlation survive). **The method matters
and the headline number is method-dependent — that IS the result:**

| pair | percentile p | basic/pivotal CI | studentized p | studentized CI |
|---|---|---|---|---|
| V24 − V32 | 0.733 | [−0.0675, +0.0923] spans 0 | **0.745** | [−0.0652, +0.0920] spans 0 |
| V24 − V21 | 0.038 | **[−0.0095, +0.0707] SPANS 0** | **0.127** | [+0.0013, +0.0999] |
| V32 − V21 | 0.564 | [−0.0560, +0.1021] spans 0 | **0.555** | [−0.0508, +0.1046] spans 0 |

The lone sub-0.05 figure in this whole study — V24−V21 percentile p=0.038 — **does not survive method
choice**: the pivotal CI spans zero and the studentized p is 0.127. An adversarial review predicted this was
a mis-centred bootstrap; **that diagnosis was checked directly and is WRONG** — the draw distribution is
properly centred (mean +0.0358 vs d̂ +0.0360, offset −0.0002). The percentile/pivotal divergence is **skew,
not bias**. Right conclusion, wrong mechanism — recorded because the mechanism matters for reuse.

**Power — the number that makes the nulls meaningful** (non-significance is uninterpretable without it):

| pair | corr | SE(ΔSharpe)/yr | min detectable @80% power | observed |
|---|---|---|---|---|
| V24 vs V32 | 0.9719 | 0.0527 | **0.148** | **0.013** ← 11× below the noise floor |
| V24 vs V21 | 0.9957 | 0.0206 | **0.058** | 0.036 ← under-powered, not "absent" |

**V24 vs V32 is not a close call — it is UNMEASURABLE on this window.** To resolve a 0.013 gap we would need
~0.15. §15f's framing of V24-vs-V32 as *"a genuine trade-off… a preference call, not a numbers call"* is
**too generous**: it is not a trade-off, it is three noise draws. The tie-breakers §15f leaned on are noisier
than the Sharpe itself — a single half-sample Sharpe carries **SE ≈ 0.31** (n=129), so V32's 0.95/0.84
"imbalance" is 0.25 SE (paired diff-in-diff vs V24's balance: **z = −0.95, p = 0.34**), and ₹31.15-vs-₹30.35
terminal wealth is a monotone function of mean log return — **more** noise-dominated than Sharpe, not less.

**Selection deflation — and the check that made it fair.** V24 was the WINNER of the Round-4 batch (V22..V30,
k=9); reporting a winner's raw p as a pre-registered p is the winner's-curse error. Bonferroni assumes
independence and would be unfairly harsh if the levers were redundant — **so it was measured, not assumed.**
Pairwise correlations of the levers' excess-over-V21 series: **off-diagonal mean +0.126, median +0.051**
(min −0.313, max +0.815). **The levers are genuinely distinct tests → a k≈9 burden is real and Bonferroni is
roughly right.** (V24 correlates **−0.31** with V22 — independently corroborating §15f's measured negative
interaction.) Applying it: V24−V21 percentile p 0.038 → **Bonferroni 0.345 / Šidák 0.296**; JK p 0.081 →
0.726/0.531; the defensible studentized p 0.127 → 1.000/0.706. **Nothing survives on any method.** k=9 is the
FLOOR — selection is four rounds deep on the SAME 2005-2026 window. *(Measured k=8: V29 came back ≡ V21
because the satellite indices are absent from the extract; the module reports and excludes it. Does not move
the conclusion.)*

**Effective sample size — the strongest argument against V24, which no prior round made.** V24 and V21 are
**identical in 206 of 258 months (80%)**; only ~52 months carry any information ≈ **~9 informative blocks** at
mean block 6. Both the JK normal approximation and the percentile bootstrap have poor coverage at n_eff ≈ 10.
**The window cannot support the claim regardless of which test is used.**

**🔴 A SEPARATE DEFECT — "Sharpe" is the wrong word, estate-wide.** The engine computes `m/sd*√12` with **no
risk-free subtracted**. Verified by reconciliation: **V21 = 16.57% CAGR on 19.92% ann vol = 0.875** — a raw
**return/vol ratio**. (The tell: 0.875 as a true Sharpe implies ~11.5% vol, irreconcilable with a −37.7%
MaxDD; at raw return/vol the implied 18.9% vol reconciles.) Against ~6.5% rf the true excess-return Sharpes
are **V21 ≈ 0.51 · V24 ≈ 0.54 · V32 ≈ 0.54** — ordinary, not exceptional. **Benchmarks are computed on the
identical basis, so every RELATIVE claim in §§15..15h holds unchanged; the ABSOLUTE levels were overstated by
a factor of ~1.7 by the label alone.** Ramana's ruling (2026-07-15i): **relabel to "return/vol ratio",
numbers unchanged** — the cheapest honest fix. A true-Sharpe re-cut needs a primary-source rf ingest
(Guardrail #8) and is queued with the owed TR re-cut, which moves the same figures.

**Verdict: CONDITIONAL — unchanged, and now for a stated reason.** No candidate has an evidence-backed claim
to displace V21, and **none can be manufactured from this window**. Ramana's decision (2026-07-15i), taken
with the null in hand: **V24 stands as the designated carry-forward layer on MECHANISM grounds** — its
own-percentile exit adapts to each sector's own history, replacing a fixed 70/80 threshold that was never
justified, and its direction of travel (best MaxDD −37.7%, most balanced halves 0.92/0.91) is consistent even
though not significant. **This is a priors call, correctly labelled as one, NOT an evidence result.**
Per §15h it remains a designation of *what the stock build sits on* — **`/dash/sector-rotation` stays on
V21; nothing is promoted to the live engine.** **V32 is retired as a distinct candidate** — strictly more
complex than V24 and provably indistinguishable from it; keeping it as a "wealth-favoring sibling" implies a
choice the data cannot support.

**Honest limits of this pass (do not over-read the nulls).** Non-significance ≠ no effect. The design is
low-power *by construction*: nested books correlated 0.97–0.996 with ~9 informative blocks. This pass proves
the ladder's final rungs **cannot be told apart on 2005-2026** — it does NOT prove V24 is no better than V21.
Only a **fresh window / true OOS** can settle that, and per §15h the honest priority is the **constituent
build**, not further tuning of a layer whose index expression may be unbuyable in ~⅜ of sectors.

**Reproduce:** `python research/explosive_moves/sector_rotation_significance.py <db>` — self-gating (exits
non-zero if the engine stops reproducing §15f/§15g), stdlib-only, deterministic (seed 20260715).

### 2026-07-15g — NAMING: "V24" is the official shorthand for the FULL V21+V24 combination + a consolidated 3-index cross-check (Nifty 50 · Nifty 100 · Nifty 500)

Ramana: "if V24 consists solely of V21+V24, refer to the entire combination as V24." **Binding from here on: "V24"
means V21 (Next-50 sleeve + recovery-accelerator + inverse-vol) with the own-percentile RSI-of-RS exit swapped in
— never the bare lever tested in isolation** (which was never separately backtestable — V24 in Round 4 was always
V21-plus-the-lever, per the "test on both bases" discipline). Module
`research/explosive_moves/sector_rotation_v24_final.py` — re-derives V24 from scratch (same math, independently
re-implemented, not a re-run of exp4.py) and cross-checks: **Sharpe 0.911 / H1 0.92 / H2 0.905 / CAGR 17.2% /
MaxDD −37.72% / α +7.11%/yr / β 0.75 / ₹1 Cr → ₹30.349 Cr — matches the 2026-07-15f record exactly** (0.91/−37.7%/30.35).

**NEW data point — Nifty 100 added as a third benchmark** (2004+ full history, `index_rows`): Sharpe **0.638**,
CAGR 12.22%, MaxDD **−58.6%**, ₹1 Cr → ₹11.93 Cr — sits between Nifty 50 (0.636/−56.5%/11.35) and Nifty 500
(0.637/−62.0%/12.60), confirming the expected pattern (breadth adds a little return and a little more drawdown,
monotonically 50→100→500). **V24 beats all three simultaneously** — Sharpe +0.27 to +0.28 over any of them, MaxDD
18–24 points shallower, wealth 2.4–2.7× — on the same like-for-like price-index basis (dividends excluded on all
four, so the delta is fair, absolute levels conservative).

**The full quarterly holdings history is reproducible, not just the summary stats.** The same
`sector_rotation_v24_final.py` module's `simulate_v24(record_book=True)` mode walks all **86 quarterly rebalance dates** (a COUNT, not a percent) — the quarterly
rebalances and returns, per quarter: the exact holdings + weights, the sleeve regime, and the diff vs
the previous quarter (entered/exited/re-weighted) — the data behind the interactive portfolio ledger
shown to Ramana (2005→2026, year-grouped, searchable by sector, filterable to churn-only or cash-only
quarters). Sample fact from that walk: the book briefly held its widest-ever spread on 2022-04-01 (10
positions, none above 16.2%) after the recovery-accelerator fired coming out of the 2022 correction.

### 2026-07-15c — Round 2: attack the RETURN gap (kill-switch · asym cadence · residual fill · monthly cadence), V8 base frozen, 2005–2026 n=257

Module `research/explosive_moves/sector_rotation_exp2.py` (one lever at a time, then combos; bench like-for-like
price-index Nifty 500 = Sharpe 0.64, halves 0.58/0.78, ₹1 Cr → ₹12.60 Cr, MaxDD −62.0%):

| V8 + lever | Sharpe (H1/H2) | CAGR | MaxDD | β | α/yr | ₹1 Cr → | verdict |
|---|---|---|---|---|---|---|---|
| — (V8 frozen) | 0.70 (0.78/0.64) | 10.8% | −36.2% | 0.60 | +3.2% | 9.13 | baseline |
| V9a 200DMA kill ×0.5 (book) | 0.72 (0.89/0.55) | 8.5% | −33.1% | 0.40 | +3.2% | 5.72 | REJECT — wealth collapses; regime-timing decays in H2 |
| V9b 200DMA kill → full cash | 0.58 | 6.1% | −29.0% | 0.25 | +2.9% | 3.54 | REJECT |
| V10 ASYM (entries qtrly, risk monthly, taper→cash) | 0.59 | 6.6% | −30.7% | 0.40 | +1.4% | 3.96 | REJECT — monthly risk pass sells into noise + cash drag |
| V11 FILL residual→index | 0.71 (0.71/0.71) | 13.9% | −55.8% | 0.91 | +2.4% | 16.38 | beats index on wealth; gives back the DD protection |
| V12 MONTHLY entries | 0.62 (0.55/0.68) | 10.0% | −47.6% | 0.68 | +1.5% | 7.74 | REJECT — churn 35.7%/mo (third confirmation of the cadence law) |
| V13–V16 combos (ASYM/KILL/MONTH × FILL) | 0.66–0.67 | 12.8–13.1% | −56…−59% | ~0.9 | +0.7…+1.8% | 13.2–14.0 | all strictly below V11/V17 |
| **★ V17 DEFENSIVE FILL** — residual→index only while bench ≥ 200DMA, else residual→CASH; sector book untouched | **0.79 (0.86/0.70)** | **14.7%** | **−39.2%** | 0.77 | **+4.7%** | **19.04** | **champion-candidate** |

- **V17 beats the index on all three at once** (like-for-like): wealth **₹19.04 Cr vs ₹12.60 Cr (+51%)**, Sharpe
  **0.79 vs 0.64**, MaxDD **−39.2% vs −62.0%**; turnover unchanged 12.4%/mo (the fill-sleeve's 200DMA switches are
  rare — cost immaterial). The 200DMA that FAILS as a book-level kill (V9) WORKS as a fill-sleeve guard: whipsaw
  there costs only index-vs-cash on the residual, while sidestepping crashes with the whole sleeve. V17b uniformity
  check (empty-book residual also defensive) = identical numbers.
- **Honest caveats (do not drop):** (1) H2 Sharpe 0.70 vs bench H2 0.78 — the risk-adjusted edge is H1-heavy
  (contains 2008, where any 200DMA overlay shines); H2 wealth is still ahead. (2) V17 is the 11th variant of the
  round — selection deflation applies; treat 0.79/+4.7% as tuned-in-sample until a TR-benchmark re-cut or fresh
  period confirms. (3) price-index bench understates Nifty TR by ~1.2–1.5%/yr dividends; both sides understate
  (sector ETFs pay dividends too), so the like-for-like delta stands but absolute CAGRs are conservative.
- **Verdict: CONDITIONAL — V17 is the champion-CANDIDATE, pending Ramana's ratification (the frozen champion
  formally remains V8 per his standing instruction).** Next rigor if ratified: TR-benchmark re-cut · V17 alpha
  t-stat · the V2 ≤40-stock constituent expression.

## Study 2026-07-22c — LOW-VOL DEFENSIVE SLEEVE + blend: closing the momentum-band drawdown gap with an UNCORRELATED factor (DONE — the blend PASSES both halves + beats the index on every axis; ⚠ low-vol is the star and it's un-fenced)

Portfolio-construction follow-up to the name-ladder (07-22): the momentum-band DD gap is SYSTEMATIC
factor risk, so closing it needs an UNCORRELATED sleeve, not more momentum names. Built a low-vol
defensive equity sleeve (bottom-vol quintile of liquid EQ names ≥₹5cr, monthly, trailing-126d
annualised vol; 0.15%/side turnover cost) and blended with `mbr_book` CELL_B_TREND_STRONG net.
Pre-registered (`lowvol_sleeve` `fefef943`, `--verify` clean); module + `out/lowvol_sleeve.json`;
169 months 2012-06→2026-06, avg 91 names. This is PORTFOLIO CONSTRUCTION (risk), NOT a momentum/
reversal hybrid — low-vol is a third, defensive factor (Ramana's separate-lines rule intact).

- **The sleeve is genuinely UNCORRELATED: corr(lowvol, momentum-stack) = −0.02** (vs index −0.03) —
  so the blend earns real factor diversification (the blend's R/V exceeds BOTH sleeves = the
  uncorrelated-streams free lunch).
- **Standalone (net): low-vol sleeve R/V 1.14 / CAGR 15.9% / DD −21.5%, BOTH halves (h1 1.22 / h2
  1.10)** — beats the index (0.85 / 13.4% / −30%) AND the momentum stack (0.71 / 13.3% / −63%) on
  EVERY axis incl. the both-halves 0.89 bar. The low-vol anomaly, consistent with the ledger's
  LOWVOL_MOM (the one participation-fundable corner).
- **★ Blend 40/60 (40% mom / 60% lowvol) net: R/V 1.32 / CAGR 15.7% / DD −32.7% (≈ index −30%), h1
  1.10 / h2 1.52 — PASSES both halves** (the gate the momentum stack alone FAILED at h1 0.41). First
  fundable-LOOKING book of the whole chain: closes the DD gap AND beats the index on return +
  risk-adjusted return in both halves. Vol-sizing on top adds nothing (already stabilised). 50/50 =
  1.23 / 15.5% / −37.6% (h1 0.94).
- **⚠ HONEST: low-vol is doing the work; momentum is the JUNIOR partner.** Low-vol alone has HALF the
  blend's drawdown (−21.5 vs −32.7) and nearly the same return (15.9 vs 15.7); adding momentum lifts
  R/V (1.14→1.32 via diversification) but ADDS drawdown. Lowest-DD → more low-vol; best R/V → 40/60.
- **⚠ NOT YET FUNDABLE — the sleeve is fresh + UN-FENCED.** Cost was a flat 0.15%/side on turnover
  (NOT the participation/Zerodha gauntlet); no capacity / OOS-freeze / survivorship fences yet. The
  numbers look excellent but must clear the same gauntlet the momentum book got before any capital.
  PROMOTION PATH: fence the low-vol sleeve (participation cost, capacity, fit→freeze→OOS).

- **FENCE DONE (capacity/cost gauntlet, `lowvol_sleeve --fence`, reusing `cost_participation.side_costs`
  Almgren √-impact): low-vol SURVIVES to MODEST capacity ~₹50cr; the BLEND does NOT scale.** Sleeve
  net recut by AUM (R/V / CAGR / MaxDD): frictionless 1.18/16.6%/−21% · ₹25cr 1.04/14.2%/−22% · ₹50cr
  0.98/13.4%/−23% · ₹100cr **0.89**/12.0%/−24% · ₹250cr 0.74/9.6% · ₹500cr 0.57/7.2%. **Clears the
  0.89 hurdle to ~₹100cr, BEATS the index (13.4%) only to ~₹40-50cr**; the DD edge (−21→−24%) holds
  across AUM — a genuine modest-capacity corner, consistent with LOWVOL_MOM (~₹100cr), FAR better than
  C-BLEND (−0.30@₹100cr). Median held ADV ₹51cr (liquid). ⚠ Cost driver = **199%/yr one-way turnover**
  (bottom-quintile churns monthly) → a hysteresis hold-band / quarterly rebalance would cut it and
  lift capacity (NEXT LEVER). ⚠ **BLEND capacity is BOUND by the momentum sleeve** — its trade median
  ADV is ₹4.6cr (10× less liquid than low-vol), so the 40/60 R/V 1.32 is a SMALL-AUM phenomenon; at
  scale lean more low-vol / less momentum. Residual un-closed: delisting-return bias (structural,
  estate-wide). VERDICT: **low-vol = a real ~₹50cr-capacity fundable factor whose DD edge survives
  cost**; the momentum-band book fails capacity too (junior partner on liquidity as well as drawdown).

### Study 2026-07-22d — LOW-VOL SLEEVE v2 (quarterly + hysteresis): the turnover cut BUYS the capacity

Refinement of 07-22c driven by its own fence (199%/yr turnover was the cost driver). Module
`research/explosive_moves/lowvol_sleeve_q.py` (prereg `b8c1dec4`, registered 07-23): ENTER the
bottom-20% vol names, HOLD until a name leaves the wider bottom-40% band (**hysteresis**), re-select
**QUARTERLY**. Turnover **199%/yr → 71%/yr** (2.8× cut). Standalone net (flat 0.15%/side on quarterly
turnover): full R/V 1.06 / CAGR 15.0% / DD −20.8%; h1 1.05/13.2/−15.4; h2 1.08/16.6/−20.8;
**corr vs momentum-stack 0.003**. Slightly below the monthly sleeve's frictionless edge (wider band
dilutes) but DD tighter and both halves balanced.

CAPACITY (the point) — net R/V · CAGR · MaxDD by AUM, monthly (07-22c) → quarterly+hysteresis (07-22d):
frictionless 1.18/16.6/−21 → 1.07/15.2/−21 · ₹50cr 0.98/13.4/−23 → 1.02/14.3/−21 ·
₹100cr 0.89/12.0/−24 → **0.99/13.9/−21** · ₹250cr 0.74/9.6/−27 → **0.95/13.2/−21** ·
₹500cr 0.57/7.2/−30 → **0.90/12.4/−22**. Index 0.85/13.4/−30. **Capacity ceiling ~₹50cr → beyond
₹500cr**: net R/V clears the 0.89 hurdle at EVERY AUM to ₹500cr, beats the index on return to ~₹250cr,
and the DD stays FLAT ~−21% across all AUM (monthly bled to −30%). Median held ADV ₹50.8cr,
soft-capacity ₹622cr. The turnover cut directly bought ~5× capacity + DD stability — **this IS the
LOWVOL_MOM fundable corner the ledger flagged.**

Blend 40/60 (mom / low-vol-q): R/V 1.25 / CAGR 15.2% / DD −34.1% (corr 0.003) — a touch below the
monthly blend (1.32) and DD dragged by momentum; and the blend STILL can't scale (momentum's ₹4.6cr
ADV binds it). **VERDICT: run the quarterly+hysteresis low-vol sleeve STANDALONE as the fundable
product** — net R/V ~1.0, matches/beats the index, DD ~−21% vs index −30%, uncorrelated to momentum,
holds to ₹250-500cr. The blend is a small-AUM return-per-vol booster only. Descriptive; NEXT = a
forward/paper test (freeze the spec, watch quarterly) before any capital.

### Study 2026-07-23 — WEEKLY BAND RECLAIM: the weekly timeframe does NOT rescue the daily-falsified reclaim (REJECTED)

The one crossover variant that attacked the actual reason the daily arc failed — the TIMEFRAME. Signal:
T=EMA5(HLC3) crosses UP through L=EMA13(low) on WEEKLY bars ("buy the reclaim after weakness"); proper
SL/TSL = ratcheting weekly 2°-down-fractal + band invalidation (weekly close < L) + 52-week censor. Module
`research/explosive_moves/weekly_band_reclaim.py` (prereg `9990a435`). Prior on record: CAUTIOUS-FAIL.

**RESULT — FAILS BOTH GATES; weekly did NOT help.**
- **Gate-1 SELECTION:** ~10,400 events; 13-week median excess **−2.79%** (WORSENING to −5.32% at 26wk, pos
  ~40%); Cliff's δ vs placebo **−0.02** (worse than random); both halves negative (−4.0% / −2.2%) →
  **FAIL-null** (G2/G3/G4 all fail). An ANTI-signal, exactly like its daily form (STREAM BAND 07-13).
- **Gate-2 BOOK** (net, weekly EW → monthly): R/V **0.15** / CAGR 0.8% / DD −60% — and WORSE than a
  random-entry control (R/V 0.51). The reclaim ENTRY destroys value vs the exits alone. NOT FUNDABLE.

**WHY the horizon fix didn't work:** the reclaim is a BUY-WEAKNESS entry, and weakness PERSISTS at the
2–6-month horizon too (the excess gets MORE negative with horizon). The weekly-timeframe fix would help a
buy-STRENGTH signal (moving it toward momentum-persistence); it cannot rescue a buy-weakness signal, whose
edge is negative at every horizon tested. VERDICT: REJECTED, descriptive-only. **Closes the "but what
about weekly?" question — the low-band reclaim is a robust anti-signal on BOTH daily and weekly.** Cite
alongside the daily momentum FAIL-null (this arc) + STREAM BAND 07-13.

### Study 2026-07-23 — REGIME OVERLAY: the de-risk lever is REAL but must be TARGETED (helps high-beta momentum, HURTS defensive low-vol)

A constructive lever test (`research/explosive_moves/regime_overlay.py`, descriptive), built + measured —
not a description. Regime = Nifty-500 vs its 200-DMA (+ a vol-tercile variant), PIT (prior month-end signal
→ current month); in a risk-off month the book is scaled to `scale` invested, the rest to cash (6%/yr).

**THE DIAGNOSTIC** (base-book average monthly return, risk-off vs risk-on — predicts the result BEFORE you run):
- LOW-VOL v2: risk-off **+2.30%** > risk-on +0.89% → it EARNS its keep in risk-off (it IS a hedge).
- MOMENTUM (`CELL_B_TREND_STRONG`): risk-off **+0.66%** < risk-on +1.41% → it's HURT in risk-off.
The sign of (off − on) tells you whether the overlay will help.

**RESULT** (R/V · CAGR · MaxDD):
- LOW-VOL — overlay HURTS: base 1.06/15.0/−20.8 → trend-0.3 0.93/10.9/**−26.4** (deeper!) → trend-0.0
  0.81/9.1/−29.3. You cannot hedge a hedge — de-risking cuts the book's BEST months. (Vol overlay ~neutral.)
- MOMENTUM — trend overlay WORKS as predicted: base 0.70/13.1/**−63.2** → trend-0.3 0.83/13.5/−48.2 →
  trend-0.0 0.84/13.4/**−42.4**. CAGR HELD (~13.4%), DD cut ~21 points (−63→−42), R/V 0.70→0.84.
  (Vol-tercile overlay HURTS momentum — it's the TREND regime specifically that works.)

**HONEST BOUND:** the overlay is a RISK BRAKE, not alpha. Momentum + overlay is STILL R/V 0.84 < the 0.89
hurdle, CAGR ≈ index, and has NO selection edge (it's beta with a drawdown brake) → still NOT fundable; the
overlay does NOT rescue the crossover. In-sample; needs a forward test before trust. **CORRECTS the earlier
loose "regime overlay = CAGR lever" claim: it is a DRAWDOWN lever, and only on books that bleed in risk-off.**

**VIX FOLLOW-UP (India VIX wired as a real regime feature — ALREADY on the box via `indexes.py`/`index_rows`,
2014-05→today, 2997 rows).** The forward-looking implied-vol regime (India VIX top-tercile-to-date, PIT)
does NOT beat the simple 200-DMA trend regime — it is INVERTED for momentum. VIX-separation (momentum,
2015+ fair window): VIX-off (high-VIX) avg **+1.46%/mo** > VIX-on +0.69% — high-VIX months are GOOD for this
trend-filtered momentum book (it catches recovery bounces), so de-risking on VIX cuts the good months and
CRUSHES CAGR (2015+ base 0.55/9.7/−63 → VIX-0.0 0.48/**6.4**/−42: DD cut but CAGR gutted). The simple TREND
filter stays the better de-risk signal (its off<on). **Lesson: the fancier implied-vol signal LOST to the
plain trend filter for this job — measure, don't assume.** India VIX may still earn its keep as a DIFFERENT
feature (position sizing / mean-reversion timing), not as a de-risk overlay — a separate test. (AMFI NAVAll
reachable = fund NAVs only; stock-level MF flow needs AMC-portfolio parsing — a real build, not a quick pull.)

### Study 2026-07-23 — OPTIONS-IMPLIED PHASE 0: PCR selects (weak, both halves); other OI signals fail — proceed CAUTIOUSLY

Phase 0 of `docs/options-implied-scope.md` — event-study gate on the OI signals ALREADY on the box
(`fno_oi_signals`, no new data), `research/explosive_moves/fno_oi_phase0.py`. Cross-sectional quintiles
weekly, 22d forward excess vs Nifty-500, Cliff's δ (top-Q vs bottom-Q), both halves. Window 2024-07→2026-07
(**~2yr, 102 weeks — low power**).

**RESULT — 1 of 4 selects: PCR.** High put-call-ratio stocks (top-Q) fwd excess **+0.74%/mo** vs bot-Q −0.02%,
**δ +0.061, and POSITIVE in BOTH halves (+0.033 / +0.096)** — a CONTRARIAN signal (heavy put positioning →
forward out-performance), more half-robust than institutional flow was. The other three FAIL: max-pain
distance (δ −0.03, halves flip +0.24/−0.04), basis (δ +0.12 but halves flip −0.11/+0.13), futures OI change
(δ ≈0). Gate verdict: PROCEED.

**HONEST CAVEATS (do not over-read):** δ +0.06 is WEAK — same order as the institutional-flow signal (+0.07)
that passed selection but DIED on fundability; the 2-year window has low power (each half ~1yr; δ_h1 barely
clears +0.03); and this is SELECTION, not a net book. **NEXT (recommended, cheap, data-on-box): test whether
PCR is a fundable NET book (quintile long, monthly, net of cost) BEFORE committing the multi-day IV build
(Phase 1).** Selection ≠ fundability (the flow lesson). If PCR survives cost → the IV build is justified; if
it dies like flow → the OI dimension isn't tradeable and we save 2-3 sessions. Forward-test-only regardless.

**NET-BOOK TEST (Phase 1.5, `fno_oi_pcr_book.py`) — PCR is NOT a fundable book; TURNOVER kills it.** Top-PCR
quintile long, F&O, monthly, net of 0.5% RT, 24 mo. **Long-only net R/V 0.28 / CAGR 3.6% / DD −21%** (gross
0.49/7.9%) — beats the flat index on return but is nowhere near the 0.89 hurdle. **Killer = 815%/yr turnover**
(PCR churns ~68% of the quintile monthly) → cost eats gross 7.9% → net 3.6%. The long-short spread looks
great GROSS (R/V 1.55/12.2%/−4.4%) but that 815% turnover ×2 legs + India borrow would eat it to ~0 net
(flow precedent). **THE FLOW LESSON REPEATS A 3RD TIME: weak selection (δ+0.06) → not fundable, this time via
churn.** Base rate now: 2 orthogonal signals tested (flow, PCR), both weakly selected, ZERO reached
fundability. NUANCE: the turnover killer is PCR-SPECIFIC (noisy daily signal) — IV-rank/skew are slower, so
this does NOT directly condemn the IV build; but the base rate is discouraging. NEXT (recommended, cheap):
test a SLOWED PCR (quarterly / smoothed) — if even that fails, the OI-positioning dimension is priced and IV
won't differ → stop; if it clears, real finding + de-risks the IV build. [[failure-models-ledger]].

**SLOWED-PCR (Phase 1.6, `fno_oi_pcr_slow.py`) — slowing did NOT rescue it; it made it WORSE. OI dimension
PRICED → STOP.** Net R/V by variant: raw-monthly **0.28** (best) · raw-quarterly 0.11 · smoothed-monthly
0.12 · smoothed-quarterly 0.20 — turnover cut 815%→275% but EVERY slow variant is BELOW the original
monthly; none near 0.89. **Why: cutting turnover cut the COST but cut the SIGNAL more — PCR's predictive
content decays fast, so the fast churn WAS partly the signal; there is no slow, tradeable version.**
**DECISION: STOP the options-implied effort.** The OI-positioning dimension (PCR) is priced; the multi-day
IV build is NOT justified on current evidence (2yr window + base rate: crossover/regime/flow/OI-positioning
= 3+ orthogonal signals explored, ZERO fundable). IV remains SCOPED-but-unbuilt (`docs/options-implied-scope.md`)
for a future dedicated effort only if explicitly prioritized. **THE FUNDABLE PRODUCT REMAINS THE STANDALONE
LOW-VOL BOOK** (forward test armed, `ema_crossover_forward` twin cadence).

### Study 2026-07-23 — INSTITUTIONAL FLOW: the FIRST orthogonal-data signal is REAL but weak/relative — long-short, not a fundable long-only book (REJECTED)

The first study to mine OWNERSHIP not price. Data ALREADY on the box: `research.db.shareholding_history` —
quarterly DII+FII holding %, PIT by `report_date`, 2019-2026, 1546 syms, primary NSE-XBRL (no scrape
needed). Signal = QoQ Δ(DII+FII) accumulation, cross-sectional quintiles per quarter, entry at report_date
(PIT). Module `research/explosive_moves/inst_flow.py` (prereg `d582445`). Prior: CAUTIOUS-OPTIMISTIC.

**RESULT — a REAL selection signal, but FAILS the fundability gate.**
- Gate-1: **Cliff's δ(Q5 accumulation vs Q1 distribution) = +0.071** — positive and ABOVE the +0.05 bar
  (G3 PASS). **This is the ONLY positive cross-sectional selection δ in the whole arc** (momentum −0.01,
  reversal ≈0, weekly reclaim −0.02) — ownership data carries information price/volume did not. BUT G2
  FAILS: both quintiles have NEGATIVE median excess (Q5 126d med −4.6%, Q1 −8.3%) — accumulation
  under-performs the index LESS, it does not out-perform it. G4 fails — edge only in 2023+ (half2), not
  2019-22. → **FAIL-null.**
- Gate-2 book: Q5 net R/V **0.51**/CAGR 9.1%/DD −18% beats Q1 (0.31/5.0/−23) but far below the 0.89
  hurdle → NOT FUNDABLE long-only (only 9 usable book quarters — short history).

**READ:** institutional flow carries REAL, orthogonal cross-sectional information (unlike the price
crossovers), but here it is a **long-SHORT / ranking signal, not a long-only alpha** — Q5 beats Q1, yet Q5
still lags the index (positive skew: a few winners carry the mean, median negative). India long-short is
constrained, so a long-only book off it doesn't clear the bar. DISPOSITION: REJECTED as a standalone book,
descriptive-only — **BUT it directionally VALIDATES the thesis that orthogonal (ownership) data is where
selection edge lives.** NEXT (not built): use Δinst as a CONDITIONER/tilt inside the low-vol book; get the
pure-MF breakout (vs DII aggregate); more history. Caveats: DII = MF-dominated domestic institutions (not
pure MF); ~28 quarters 2019+.

**TILT FOLLOW-UP (`lowvol_flow_tilt.py`) — the `low-vol × accumulation` synthesis does NOT lift the fundable
book; it HURTS.** Within the sealed low-vol held set each quarter, split by PIT Δ(DII+FII) into ACCUM
(buying) vs DISTRIB (selling), all on the SAME fair window (2024-01→2026-07, 31 mo — short, because PIT
report_date is well-populated only recently). Result: BASE (all held, EW) R/V 0.76/CAGR 10.7%/DD −19.0% >
**ACCUM 0.60/8.4%/−20.2%** > and even DISTRIB 0.74/11.8%/−20.9% edged the accum half. Tilting low-vol toward
institutional accumulation LOWERS return/vol — the flow edge (weakly +0.07 in the BROAD universe) does NOT
transfer to defensive low-vol names (likely institutions chasing already-rich "safety"). Accum tilt churns
~200%/yr → net worse. **VERDICT: keep the two separate — low-vol stays equal-weight; flow, if used, is a
broad-universe long-short/ranking overlay, NOT a low-vol conditioner.** (⚠ caught + fixed a window-fairness
bug first: base-on-83mo vs split-on-31mo was apples-to-oranges; the fair read is 0.76 vs 0.60.)

**LONG-SHORT FOLLOW-UP (`inst_flow_ls.py`) — the broad-universe flow long-short is NOT fundable; the
signal is UNSTABLE across windows.** Long top-quintile Δ(DII+FII), short bottom-quintile (short leg
restricted to liquid ≥₹25cr + 4%/yr borrow), quarterly, PIT. Fair window only 10 quarters (2023+, report_date
recent-only). Result: **SPREAD gross R/V −0.84 / CAGR −8.1%** (net post-borrow −1.73 / −15.7%) — the RAW
spread is negative BEFORE borrow cost. Why: the SHORT leg (institutions selling, liquid) returned **+24.3%**
gross vs the LONG leg (buying) **+14.4%** — the "distribution" names went UP MORE, so shorting them loses.
**This INVERTS the full-window event study (δ +0.07, Q5>Q1 over 2019-26)** → the +0.07 is weak enough to
flip sign on the recent liquid subset = noise-dominated, not tradeable. VERDICT: REJECTED. **Institutional
flow is now closed as REAL-but-weak-and-unstable — NOT fundable in ANY of the 3 forms tested: long-only
(Q5 0.51), low-vol tilt (hurts 0.60<0.76), long-short (spread −8% gross).** Only bright spot: the long leg
alone on 2023+ (14.4%/qtr-excess +1.15%/R/V 0.70) — short, sub-hurdle, non-robust. India short costs are a
secondary nail; the primary problem is the signal's instability. [[failure-models-ledger]].

### EMA-crossover family — VERDICT (2026-07-23, explicit)

**The EMA CROSSOVER ITSELF PRODUCES NOTHING FUNDABLE.** Both crossover strategies fail:
- **MOMENTUM** (`momentum_band_rsi`, T=EMA5(HLC) crosses ABOVE U=EMA13(high), with-trend + RSI≥70):
  no selection edge (22d event Cliff's δ −0.01, median excess −0.90%), net R/V 0.71 / CAGR 13.2% /
  DD −63%, capacity-dead at ₹4.6cr median trade ADV → par-with-index **BETA, not alpha**. FAIL (as
  pre-registered).
- **REVERSAL** (`reversal_oversold` REVDD oversold-bounce; and the earlier EMA-band reclaim, 07-13):
  net-NEGATIVE / worse-than-random (R/V −0.13 / CAGR −9.0% / DD −86%; Gate-1 δ≈0). REJECTED, dead.

The **ONLY fundable output** of the arc is `lowvol_sleeve_q` — a SEPARATE **low-VOLATILITY FACTOR,
NOT an EMA crossover** (ranks names by trailing 126-day vol, holds the calmest, quarterly+hysteresis;
shares NONE of the T/U/L/RSI/fractal machinery). It is carried in the forward test purely as the
non-crossover **COMPARATOR / "book to beat"** — reported beside MOM/REV but **EXCLUDED from the
crossover adjudication**. Do not read it as a crossover result.

### EMA-crossover family — PROGRESS SUMMARY (metrics at a glance, 2026-07-23)

The arc from the failing crossover to the fundable low-vol book, net-of-cost, verified this session
(R/V = annualised mean/sd, no rf — D142 basis; hurdle = Nifty 500 buy-hold 0.89; seals verify 3/3
post-reconcile: `0e90bf2c` / `4d932089` / `b8c1dec4`).

| Book | Type | Net R/V | CAGR | Max DD | Capacity | Verdict |
|---|---|--:|--:|--:|---|---|
| Momentum — trend + RSI≥70 (`CELL_B_TREND_STRONG`) | EMA crossover | 0.71 | 13.2% | −63% | ₹4.6cr names | par = beta → FAIL |
| Momentum — Cell B (all) | EMA crossover | — | 8.4% (gross 19.4%) | −58% | — | FAIL |
| Reversal — oversold (`REVDD`) | EMA-arc | −0.13 | −9.0% | −86% | — | dead → REJECT |
| Low-vol v1 (monthly) | factor (NOT a crossover) | 1.14 | 15.9% | −21% | ~₹50–100cr | fundable, turnover-capped |
| **Low-vol v2 (quarterly + hysteresis)** | factor (NOT a crossover) | **1.06** | **15.0%** | **−21%** | **to ₹500cr** | **GRADUATE** |
| Nifty 500 (benchmark) | index | 0.85 | 13.4% | −30% | — | hurdle 0.89 |

Low-vol v2 capacity curve (the turnover cut 199→71%/yr bought the scale; Almgren participation via
`cost_participation.side_costs`):

| AUM | Net R/V | CAGR | Max DD |
|---|--:|--:|--:|
| Frictionless | 1.07 | 15.2% | −21% |
| ₹50cr | 1.02 | 14.3% | −21% |
| ₹100cr | 0.99 | 13.9% | −21% |
| ₹250cr | 0.95 | 13.2% | −21% |
| ₹500cr | 0.90 | 12.4% | −22% |

**Bottom line:** the EMA crossover returns the index (13.2%) at **double the drawdown** (−63% vs −30%)
with no scalability; the fundable low-vol book **beats the index** (15.0% vs 13.4%) at **~⅓ the
drawdown** (−21% vs −30%) and holds that edge to ₹500cr.

### Forward test ARMED (2026-07-23) — `ema_crossover_forward.py` (the `union_forward` twin)

One command, REPORTING-ONLY over three sealed engines — the whole EMA-crossover family judged together:
MOM (momentum_band_rsi CELL_B_TREND_STRONG, seal `0e90bf2c`, in-sample R/V 0.71/13.2%/−63%),
REV (reversal_oversold REVDD, seal `4d932089`, −0.13/−9.0%/−86%, worse than its random control),
LOW (lowvol_sleeve_q, seal `b8c1dec4`, 1.06/15.0%/−21%, the fundable product). It prints an
INTEGRITY+REPRODUCTION gate (3/3 seals + 3/3 in-sample anchors reproduce to the digit —
**box-verified 2026-07-23**), the REGISTERED PREDICTIONS frozen up front (**LOW graduates / MOM reveals
as beta → fails C2 / REV stays dead**), the forward window sliced at FREEZE=2026-07, and frozen criteria
C1 beat-index / C2 alpha>0 (beta>1.1 & no-alpha = beta-not-skill FAIL) / C3 DD-not-worse / C4 no month
>60% of excess / C5 (LOW only) net R/V>0.89 — judged mechanically only at **≥24 forward months (8 qtrs)**;
INTERIM before, FAMILY ADJUDICATION (highest forward alpha graduates) at ≥24. `--rebuild` refreshes the
three books from current data first; `--asof YYYY-MM` caps the window. First checkpoint 2026-10 (quarter
-end, aligns with LOW's quarterly rebalance). One-pager `out/ema_crossover_forward.json`. No seal of its
own — it verifies the three it reports on. Descriptive until the forward window judges.

---

## Study 2026-07-22b — REVERSAL, CLEAN oversold-bounce (deep drawdown + RSI-30 turn; NON-band, NON-momentum) (DONE — pre-registered FAIL at BOTH gates; reversal falsified at the CONCEPT level, not just the band mechanics)

The REVERSAL line as a distinct, fresh approach per Ramana's 2026-07-22 directive (momentum and
reversal kept SEPARATE — no hybrids). Reversal-native features ONLY (deep drawdown + RSI-oversold
turn; NO RS, NO momentum conditioning) and a DIFFERENT definition from the falsified band-reclaim.
EVENT = adj_close ≥25% below its trailing 252-day high AND price RSI(14) crosses UP through 30.
Pre-registered + hash-frozen BEFORE run (prereg `reversal_oversold` `4d932089`, `--verify` clean);
module `research/explosive_moves/reversal_oversold.py`; JSON `out/reversal_oversold.json`. Universe
3,499 EQ/CM syms 2012-06→2026-07, CA-adjusted; n=12,496 events (de-overlap 22 bars), 12,548 trades.
Two-gate frame; **PREDICTION before run: FAIL. Confirmed at BOTH gates.**

- **GATE-1 (selection) FAIL-null.** 22d excess mean −0.28% / **median −0.98%** / 45.8% pos; Cliff's δ
  vs placebo **+0.007 / −0.012 (≈0)**; halves med −1.35% / −0.82% (negative both); WORSENS with horizon
  (66d med **−3.11%**, 42.5% pos) = falling-knife anatomy. NO reversal-native conditioner rescues it —
  drawdown-depth, vol66, dist-200SMA, prior-126d all NEGATIVE median in every tercile. The event IS
  median-less-bad than its own same-symbol placebo (−0.98 vs −1.43) → the oversold turn STOPS bleeding
  but never creates edge — the EXACT 07-14c conclusion, reproduced under a fresh non-band definition.
- **GATE-2 (book) NEGATIVE — worse than a fail.** Long at entry close; exit on RSI≥60 / ratcheting
  2°-fractal stop / 66-bar time. Net **return/vol −0.13, CAGR −9.0%, MaxDD −86.2%** (h1 −0.55/−18.3% ·
  h2 0.16/−0.1%); even GROSS only 0.32 / **+5.3%** (below the index AND the 0.89 bar BEFORE cost); cost
  drag 14.3pp. Trades: 38.7% net-positive, mean net −0.01%, median net **−2.0%**, avg hold 10 bars,
  **76% exit on the fractal stop** (they keep falling), RSI-60 target reached only 24%. G_BETTER FAIL
  (−0.13 vs random control −0.24 = +0.11 < +0.15).
- **Disposition: REJECTED — descriptive-only. Reversal is now falsified at the CONCEPT level, not just
  the band mechanics.** A textbook deep-oversold RSI-turn — zero momentum/RS contamination — still
  bleeds and loses money net. The reversal family survives only as a risk-geometry / context overlay
  (band-state, stretch percentile, floor+invalidation), never a book. Any future reversal proposal must
  cite 07-13/14/14b/14c + THIS entry. The momentum line (RS/union) is unaffected and stays the live axis.

---

## Study 2026-07-22 — MOMENTUM BAND + RSI: the UPPER-band breakout entry (BUY STRENGTH) + RSI/fractal managed exit (DONE — pre-registered FAIL; the strength edge is an anti-signal too, RSI stops don't rescue it)

Ramana's momentum reframing of the STREAM BAND spec, and the ONE untested sliver of the reversal-pair
arc. STREAM BAND (07-13) tested the LOWER-bank RECLAIM (buy weakness); this tests the OPPOSITE edge
Ramana named as his momentum trigger — T=EMA5(HLC3) crosses ABOVE the UPPER bank EMA13(adj-high) = BUY
STRENGTH — with RSI(14 Wilder, price) + degree-2 down-fractal managed exits (never tested: the arc's
stops were stream/two-candle/%/ATR/chandelier, none RSI). Pre-registered + hash-frozen BEFORE first
run (prereg `momentum_band_rsi` `0e90bf2c…`, `--verify` clean); module
`research/explosive_moves/momentum_band_rsi.py`; JSON `out/momentum_band_rsi.json`. Universe 3,499
EQ/CM symbols, 2012-06→2026-07, CA-adjusted; n=45,131 MOM-BUY events (de-overlap 22 bars), 124,832
managed trades. Same harness/controls as STREAM BAND. **PREDICTION ON RECORD before the run: FAIL
(~0.6<0.89). Confirmed.**

- **EVENT verdict: FAIL-null (G2/G3/G4 all fail).** 22d excess mean +0.51% / **median −0.90%** /
  46.0% positive; **both placebos beat it** (sym med −0.70%, shift −0.69%); Cliff's δ **−0.012 /
  −0.013** (negative); halves med **−1.08% / −0.82%** (negative both). Monotone across horizons (5d
  −0.51 · 10d −0.66 · 22d −0.90 · 66d −1.58 median; mean positive throughout = right-skew, the SAME
  anatomy as the reclaim). Buying strength at the upper-band cross carries no forward edge — marginally
  WORSE than a random same-stock day.
- **BOOK (Cell B, loose exit = 2-fractal-stop OR RSI≤45, no profit-take): net return/vol 0.53** full
  (h1 2012-18 **0.19** / h2 2019-26 **0.87**), CAGR 8.4%, MaxDD −58.1%, hit 35.9%, median trade
  **−2.74% net**, avg hold 20 bars. **G_BOOK FAIL** (both halves <0.89; even the best half 0.87<0.89).
  **Raw (gross) 1.00 retvol / CAGR 19.4% → net 8.4%: cost eats 11pp of CAGR** (avg RT 0.57%, ~40k
  trades) — the 1.29→0.09 / C-BLEND cost pattern, a third sighting.
- **G_BETTER vs random-entry-same-exit: PASS (+0.20)** — 0.53 net vs 0.33 random control. UNLIKE the
  fractal floor (07-14b, entry inert vs random), the momentum entry DOES carry ~0.20 retvol of
  information over the exit geometry — but the absolute level is sub-hurdle, so "better than random"
  and "not fundable" are both true. The one non-zero-but-useless residual of the arc.
- **RSI-as-stop (NEW): the phase-1 "exit if RSI < entry-RSI" rule is a hair-trigger** — Cell A
  (Ramana-literal) exited **94%** of trades via that stop, avg hold **5.3 bars**, net mean −0.08% /
  median −1.26%: the two-candle-exit disease (07-14d) in RSI clothing. The "hold till RSI 80" reading
  (Cell A2, fractal-only until 80 = effectively a pure 2-fractal trail) is the least-bad variant: as a
  BOOK it edges Cell B (net return/vol **0.60 vs 0.53**, CAGR 9.7% vs 8.4%; its 2019-26 half 0.91
  momentarily clears 0.89 but 2012-18 is 0.28) — the EXIT-LAB "loosest wins" law, still sub-hurdle and
  still median −2.57% net per trade.
- **RSI-80 PARTIAL profit-take (NEW): confirms the EXIT LAB profit-taker law.** On Cell A2, taking
  half off at the first RSI≥80 moved mean net **−0.25pp** (median +0.13pp): it shaves the right-tail
  (the only paying part) while barely helping the median — exactly "any rule that trims winners
  amputates the paying part" (07-14e), now shown for RSI too.
- **Disposition: REJECTED — descriptive-only.** The reversal-pair arc's LAST sliver is closed: the
  momentum (buy-strength) edge is an anti-signal at event level and sub-hurdle as a book; RSI stops
  either churn (phase-1) or fail to mint edge; the RSI-80 partial hurts. The pre-registered prediction
  stood. Any future band/RSI/fractal single-name swing proposal must cite THIS entry +
  07-13/14/14b/14c/14d/14e. Surviving descriptive residual unchanged (band-state + own-history stretch
  percentile as context columns).

- **Segmentation refinement (which slice carries it — the TREND filter is the one real lever).**
  Cell-B net books by segment: baseline netCAGR 8.4% / DD −58% / R/V 0.53 → **entry-above-own-200SMA
  (with-trend) netCAGR 11.8% / DD −53% / R/V 0.69, h2 2019-26 = 1.02 (clears 0.89) but h1 = 0.32
  (fails)** — lifts return AND cuts drawdown together. Toxic additives: MARKET-REGIME timing
  (Nifty-500 > 200SMA at entry) BACKFIRES — netCAGR 3.1%, DD **−72%** (enters late, rides the top down);
  LARGE-CAP-only (≥₹25cr) kills the return (5.6%). Tightest DD = trend+liq25+regime "clean" **−48.6%**
  but only ~46 names and no return gain. Trade-level: trend-up mean net +1.59% vs down −0.02%;
  RSI≥70-at-entry best (40.5% win / +1.84% mean), RSI<50 worst — skip. Verdict UNCHANGED (better,
  8.4→11.8% net, still sub-hurdle full-period); the with-trend filter is the keeper. Segment books in
  `mbr_book` (keys CELL_B_TREND/LIQ25/REGIME/CLEAN).

- **Two-vitamin stack (with-trend AND RSI≥70-at-entry, ~48 names) — the best CLEAN version, but NOT
  all-weather, and 2012-18 CANNOT be honestly fixed.** Net full CAGR **13.2%** / R/V 0.71 / DD
  **−63.2%** (DEEPER than trend-alone −52.8% — concentration cost of ~48 names); h1 2012-18 net R/V
  0.19→**0.41** (still <0.89), h2 **1.05**. **DIAGNOSIS via gross/net decomposition: 2012-18 is a
  COST/REGIME problem, NOT selection** — gross h1 R/V is healthy 0.67→**0.87** (CAGR 12-20%) but net
  collapses to 0.19-0.41 (fixed cost eats ~12pp), because the choppier 2012-18 regime carried less
  momentum-beta for the tax to survive. Lifting h1 to the bar needs either zero cost (impossible;
  already realistic) or a lever tuned to an in-sample half (OVERFITTING — refused). The gross edge is
  regime-dependent beta: clears the bar in strong-trend regimes (h2), not choppy ones (h1). This is
  the honest CEILING of the momentum-band family. Segment books: `mbr_book` key CELL_B_TREND_STRONG.

- **Vol-targeting the stack (uniform risk overlay, NOT a 2018-19-specific hack) — cuts the drawdown
  hard AND lifts risk-adjusted return; the FIRST momentum-band form to beat the index on R/V.** Overlay
  = scale monthly exposure w=clip(target / trailing-12m-annualised-vol, 0, 1) on the CELL_B_TREND_STRONG
  net monthly series, deleveraged capital parked at 6% cash (causal/PIT). Robust across targets
  (deleverage-only): **12% → netCAGR 12.5% / R/V 0.90 / MaxDD −40%** (h1 0.41→0.66); 15% → 13.5% / 0.83
  / −49%; 18% → 14.1% / 0.80 / −53% — vs RAW 13.2% / 0.71 / −63% and INDEX 13.4% / 0.86 / −30%. At the
  12-15% targets R/V EXCEEDS the index's 0.86 (first time in the whole exploration); the 15% version
  even ends slightly ahead of both raw and the index (deleveraging into 2018-19/2020 avoided the
  losses). CAVEATS: it's a RISK-ADJUSTED win, not new return (CAGR flat-to-−0.7pp); best h1 R/V 0.66
  still < 0.89 (both-halves bar still unmet); DD still deeper than the index; the vol target is a free
  parameter (grid shown so the direction is transparent, not cherry-picked). Reproduce: trailing-12m
  vol overlay on `mbr_book` CELL_B_TREND_STRONG net.

- **Adding NAMES does NOT close the drawdown gap vs the index — it's a FACTOR problem, not a
  name-count problem.** RSI-strength ladder inside the trend filter (loosening ≥70 adds names; raw
  net): R70 **48 names DD −63% R/V 0.71 CAGR 13.2%** → R65 96/−56.5/0.63 → R60 **145/−53.4/0.64** →
  R55 173/−53.2/0.66 → trend-only **181/−52.8/0.69/11.8%** (vs INDEX ~500 names −30% / 0.86). More
  names shaves raw DD modestly (−63→−53%) but SACRIFICES return/R/V (0.71→0.64, CAGR 13.2→~11%) —
  the RSI≥70 names carry the edge and the diluters are correlated momentum/high-beta names; **you
  can't diversify a factor with more of the same factor** (the DD is systematic, not idiosyncratic —
  they all crash together 2018/2020). Even broadest + vol-sized bottoms ~−37% (12% target), still
  short of −30%. **The effective DD lever stays VOL-SIZING (cuts factor exposure), not name count;**
  best combo = concentrated R70 stack + vol-target (R/V 0.83-0.90, DD −40%). Reaching −30% needs less
  exposure (less return) or an UNCORRELATED sleeve = portfolio construction. Books: `mbr_book`
  CELL_B_TREND_R55/R60/R65.

- **Equity curves (₹100 start; net of cost unless noted; monthly-compounded, year-end marks):** A2 net
  (looser pure-2-fractal trail) rides a hair above B net (RSI-45 exit) the WHOLE way — the EXIT-LAB
  "loosest wins" law — but both finish far below Nifty-500 buy-hold. Gross (B) = 12.3× is BETA not
  alpha (the entry event-study is placebo-negative, δ −0.012); cost converts it to 3.2× net, BELOW the
  index's 6.0×. The 2018-19 trough (net ~93-125 while the index ran 234→252) is where the sub-hurdle
  2012-18 half (retvol 0.19/0.28) is lost.

  | Year-end | B gross | A2 net | B net | Nifty 500 |
  |---|--:|--:|--:|--:|
  | 2012 | 123 | 113 | 113 | 121 |
  | 2013 | 126 | 106 | 107 | 126 |
  | 2014 | 210 | 162 | 163 | 173 |
  | 2015 | 229 | 163 | 159 | 172 |
  | 2016 | 218 | 148 | 139 | 178 |
  | 2017 | 363 | 223 | 209 | 243 |
  | 2018 | 213 | 125 | 113 | 234 |
  | 2019 | 192 | 104 | 93 | 252 |
  | 2020 | 319 | 155 | 137 | 294 |
  | 2021 | 567 | 247 | 222 | 383 |
  | 2022 | 587 | 239 | 208 | 395 |
  | 2023 | 865 | 325 | 281 | 497 |
  | 2024 | 1142 | 388 | 336 | 572 |
  | 2025 | 1133 | 364 | 307 | 610 |
  | 2026-07 | **1232** | **373** | **315** | **597** |

  Full-period return/vol: B gross 1.00 · A2 net **0.60** · B net **0.53** · (Nifty-500 hurdle 0.89).
  A2's 2019-26 half touches 0.91 (over the bar) but its 2012-18 half is 0.28 → fails both-halves.

---

## Study 2026-07-13 — STREAM BAND (13-EMA HiLo band + 5-EMA HLC3 trigger) reversal cross (DONE — pre-registered FAIL-null; the BUY-cross *negatively* selects)

Ramana's band spec (docs/strategies/reversal-context.md; the spec source was reversal-pair-PLAN.md, retired S147): EMA13(adj-high)/EMA13(adj-low) banks + EMA5(HLC3)
trigger; BUY-cross = trigger reclaims the lower bank after ≥3 bars below. Pre-registered + hash-frozen
BEFORE first run (prereg `streamband` `92fc5cac`, `--verify` tamper-clean); module
`research/explosive_moves/streamband.py`; full JSON `research/explosive_moves/out/streamband.json`.
Universe 3,491 EQ symbols, signals 2012-06→2026-07, n=35,519 BUY events (de-overlap 22 bars, med_turn
≥₹1cr, close ≥20); PIT entry = next close; outcomes = excess vs Nifty-500 over identical spans; controls
= same-symbol random-bar placebo ×3 + same-event +63-bar shift placebo.

- **Verdict: FAIL-null — G2/G3/G4 all fail, and the cross is an ANTI-signal at entry.** 22d excess
  mean **−0.22%** / median **−1.25%** / 44.1% positive; **BOTH placebos beat the signal** (same-symbol
  random mean **+0.32%**, shifted **+0.31%**); Cliff's δ **−0.019 / −0.027**; halves **−1.62% / −1.10%**
  (negative in both). Uniform across horizons (5d −0.68 · 10d −0.89 · 22d −1.25 · 66d −2.73 median).
  An early band-reclaim after a real downtrend is a falling knife more often than a reversal.
- **Book (for the record): Sharpe 0.37** full (halves **0.16 / 0.53**), MaxDD **−56%**, hit 41%, median
  trade **−2.08% net**, avg hold 15 bars — nowhere near the 0.89 hurdle. Best variant = TREND-filtered
  (close>SMA200) **0.58 (0.40/0.72)** — the SAME sub-index zone as the ledger's PULLBACK row (0.56–0.72):
  two independent constructions of "buy the dip in an uptrend" converge below buy-and-hold. ANTITREND
  (pure bottom-catch) worst: **0.21, MaxDD −59.6%**.
- **Fine-tuning grid (exploratory): every lever moves the right way, none reaches zero.** STRETCH≥p10
  precondition mean −0.185 vs −0.274 without (the per-stock stretch-percentile idea = directionally real,
  far too small); liquid/large least bad (>₹25cr med −0.73 vs 1-5cr −1.64; vol-hi tercile worst −1.88) —
  the cap/vol-stdev intuition is CONFIRMED descriptively. **HLC3 vs OHLC4: identical** (−1.25 vs −1.29
  med) — the trigger-construct choice is a non-issue.
- **Hypothesis-generating only (fresh prereg required):** 66d mean ≈0 with median −2.7% = heavy right
  skew — a minority of crosses do launch; the open question is WHICH NAMES (selection, the Wolfe lesson),
  not WHEN. SELL-side mean **+0.72%** (median −0.81%) — not a short signal either.
- **Disposition: the cross is NOT an entry signal — never rank or alert on it. If STREAM BAND surfaces
  in product it is a DESCRIPTIVE state/stretch lens** (band position + own-history stretch percentile as
  context columns). The untested sibling = FRACTAL FLOOR's ARMED→TRIGGERED breakout confirmation — its
  study needs its own pre-registration and must cite THIS entry first.

---

## Study 2026-07-14 — FRACTAL FLOOR (10-fractal floor + 2°-up-fractal breakout trigger) (DONE — event gate FAIL-null; ⚠ the PROX10 "1.04" claim below is SUPERSEDED by § Study 2026-07-14b)

> **⚠ SUPERSEDED 2026-07-14b (fences reconstruction):** the PROX10 book Sharpe **1.04 was GROSS-of-cost
> — an implementation defect**: `fractal_floor.build()` documented 0.3%/side but never charged it in the
> book accumulation (only in the per-trade `net` column). The fences study's reconstruction gate caught
> the mismatch and VOIDed itself as pre-registered. **True flat-cost PROX10 = Sharpe 0.59 (halves
> 0.46/0.69) — BELOW the 0.89 hurdle; the "first reversal-family cell to clear the bar" claim is
> WITHDRAWN.** Every fence also failed on its own frozen bar. Full record: § Study 2026-07-14b.

Ramana's fractal spec (docs/strategies/reversal-context.md; the spec source was reversal-pair-PLAN.md §1, retired S147): floor = confirmed degree-10 down-fractal low
(knowable only 10 bars later — enforced); WATCH = close within +15% of a live floor; TRIGGER = close
crosses the most recent confirmed 2°-up-fractal high (T1); STRONG = also above the higher of the last
two (T2); floor dies on a close below it. Pre-registered + hash-frozen BEFORE run (prereg
`fractal_floor` `939a33cc`, `--verify` clean); module `research/explosive_moves/fractal_floor.py`; JSON
`out/fractal_floor.json`. 3,491 symbols 2012-06→2026-07; n=23,287 D10 triggers + 54,140 watch events;
same harness/controls/gates as STREAM BAND; long side only (bear mirror deferred, disclosed).

- **Event verdict: FAIL-null (G2/G3/G4).** 22d excess mean **+0.27%** / median **−0.79%** / 45.5% pos;
  both placebos still better (means +0.39/+0.42, δ **−0.012/−0.016**); halves −0.87/−0.75. Fixed-horizon
  timing edge: none.
- **The pre-registered trigger-vs-watch contrast: δ +0.004 ≈ ZERO — the up-fractal breakout confirmation
  adds NOTHING over mere floor proximity at fixed horizons.** And **STRONG (beats-first-two-up-frac) is
  WORSE** (mean −0.01 vs +0.41 not-strong) at event level. The floor is the information; the breakout
  craft is not.
- **Book cells (flat 0.3%/side): ALL 0.62 (0.79/0.54, DD −66%) FAIL · TREND 0.77 (0.80/0.77) FAIL-close ·
  STRONG 0.73 · LIQ5 0.54 · but PROX10 (entry within 10% of the floor) = Sharpe 1.04 FULL, halves
  0.92 / 1.15 — BOTH above the 0.89 hurdle — CAGR 16.3%, MaxDD −28.5%, ~69 avg positions, hit 37.2%,
  median trade −2.34% / mean +0.94%, 88% of exits = trailing 2°-fractal structure stops.** First
  reversal-family book EVER to clear the bar (PULLBACK 0.56–0.72 · S3 −0.5% · STREAM BAND 0.37 never
  did). Mechanical story: the edge, if real, is **risk GEOMETRY not entry timing** — a hard structural
  stop ≤10% below entry × trail-exit skew harvesting (66d event mean +0.66 vs med −1.82 = heavy right
  skew), i.e. Ramana's floor concept working as position-risk design.
- **⚠ NOT a validated strategy — three fences BEFORE any promotion (each pre-registered fresh):**
  (1) **participation-cost recut** — the 1.04 is FLAT-COST-ONLY and the C-BLEND lesson (1.32→0.52@₹25cr)
  says this is where such numbers die; ~monthly effective turnover + a 1-5cr liquidity tail make it
  vulnerable; (2) **random-entry / same-exit control** — the Wolfe lesson inverted: does the trail-stop
  exit rule alone, on random eligible entries, reproduce ~1.04? If yes the fractal entry is inert and
  this is a generic trend-trail artifact; (3) **stop-fill realism** (+1-bar entry lag; gap-through-stop
  stress) — close-based structural stops flatter fills. Also disclosed: PROX10 is ONE of FIVE
  pre-registered book cells (selection-effect deflation applies). **Until all three pass: descriptive-
  only, flat-cost-only; do NOT cite 1.04 as fundable.**
- **Fine-tuning grid:** degree D5/D2 ≈ D10 (no degree edge); prox≤5% median −0.24 (best median, n=1,257);
  TREND mean +0.62 vs ANTITREND −0.40 (trend filter again); vol-hi tercile worst median −1.42; >₹25cr
  least-bad −0.62 — the cap/vol-stdev intuition confirmed a third time. HLC/OHLC moot here.

---

## Study 2026-07-14b — FRACTAL FENCES: the three confirmation checks on PROX10 (DONE — VOID-then-REJECT; the reconstruction gate exposed the 1.04 as GROSS; every fence fails; the reversal-pair program closes with ZERO tradeable survivors)

Pre-registered + hash-frozen BEFORE run (prereg `fractal_fences` `bb22eff6`); module
`research/explosive_moves/fractal_fences.py`; JSON `out/fractal_fences.json`; 10,523 reconstructed
cell trades. The module re-derives the PROX10 book from prices and requires it to match the frozen
1.04 within ±0.03 before scoring fences — it came out **0.59 (0.46/0.69, MaxDD −39.7%)** → VOID as
pre-registered. Root cause (A/B-exact): `fractal_floor.build()` never charged the documented
0.3%/side in the book (gross ≈1.04 − ~0.6% RT over ~23-bar holds ≈ −7.8%/yr drag → 0.59 ✓).

- **Corrected baseline: PROX10 flat-cost = 0.59 — below the 0.89 hurdle. The candidate was never
  alive.** The 2026-07-14 "first cell to clear the bar" claim is WITHDRAWN (supersede note added).
- **FENCE 1 (participation cost): catastrophic scale decay** — ₹1cr **0.19** · ₹5cr 0.10 · ₹10cr
  **−0.09** · ₹25cr −0.54 · ₹50cr −0.99 · ₹100cr −1.55. A 10.5k-trade, ~23-day-hold, small-cap-tailed
  book has no capacity at ANY AUM (worse than C-BLEND's decay). FAIL.
- **FENCE 2 (random-entry / same-exit): the entry is ~inert.** Random same-symbol entries with the
  SAME stop distance + SAME trailing-2°-fractal exit + same costs = **0.543** mean (seeds 0.52-0.58)
  vs real **0.59** — margin **+0.047 < +0.15**. Nearly the entire book was the EXIT geometry (cut at
  structure, trail the skew), not the fractal floor entry. Year-matched controls 0.380 (real +0.21 —
  the floor's only residual value is avoiding the worst in-year timing, h2_ok both families). FAIL.
- **FENCE 3 (fill realism): entry-lag+1 + no-bounce-credit stop fills → 0.30** (0.19/0.39); 1.5× flat
  cost → 0.37. The close-based stop fills were flattering it. FAIL.
- **Disposition (closes the reversal-pair arc, 3 pre-registered studies, tamper-clean):** STREAM BAND
  cross = anti-signal; FRACTAL FLOOR trigger = no event edge, confirmation inert, book dead at true
  cost at every scale. **NO tradeable form survives anywhere in the reversal pair. What survives is
  descriptive only:** band-state + own-history stretch percentile columns; confirmed-floor proximity +
  invalidation level as RISK-GEOMETRY context (the one idea with residual, non-tradeable merit — a
  well-defined cheap place to be wrong); and the thrice-confirmed cap/vol asymmetry. Any future
  reversal proposal must cite THIS entry + 07-13 + 07-14 first.
- **Harness note (win for the discipline):** the reconstruction gate caught OUR OWN accounting defect
  before a wrong number could compound into product or capital decisions. `fractal_floor.py` is kept
  AS-RUN (its JSON is the committed evidence); the defect is flagged by comment in the module.

---

## Study 2026-07-14e — EXIT LAB: ten exit engines on the same reclaim entry (DONE — NO-BETTER-EXIT; the exit law is now measured and monotonic)

Pre-registered `exit_lab` `fd1bdac7` (fit-pick on 2012-18 with an avg-hold≥8 churn guard; OOS
headline = the picked engine's untouched 2019-26; all ten published). 346,757 legs. Full table in
`out/exit_lab.json`; module `research/explosive_moves/exit_lab.py`.

- **Winner by fit half: E10 (8% initial stop + 5°-fractal trail) → OOS 0.63.** Fails G-BETTER
  (needed ≥0.79) and the 0.89 bar. **NO exit engine turns this entry into a book.**
- **THE LAW (monotonic in looseness):** slow/wide exits cluster at the top — band-only 0.49 full
  (payoff 3.26, hold 32d) · pct8+trail5 0.49 (11.3% legs >+20%, hold 38d) · frac+trail5 0.47 —
  while every tightening degrades in order: chand3 0.38 > arm-after-profit 0.24 > tight 2°-trail
  0.16 > chand2 0.09 > five-candle −0.08 (and 07-14d's two-candle −0.50 extends the sequence).
- **PROFIT-TAKERS ARE THE WORST IDEA OF ALL:** sell-at-upper-bank = 48.6% hit rate but payoff 1.01
  → Sharpe −0.06; stretch-p90 take 0.17. All P&L in this family is a thin tail of +20% runners —
  any rule that trims winners amputates the only paying part. High hit-rate ≠ money.
- **Note:** E1 here (band-exit ONLY, 0.49) beats the 07-13 naive book (0.37) which ALSO exited on
  an upper-band slip — removing even that second exit helped. Same law.
- **Practical recipe recorded (descriptive, for discretionary use — NOT a book):** initial SL = 8%
  or the nearest 2°-fractal low; thereafter trail ONLY under 5°-fractal (major swing) lows or exit
  when the stream fails; NEVER sell into strength; never trail on minor structure. Ceiling stands:
  best exit ≈ 0.63-0.65 OOS < 0.89 buy-and-hold — exits shape losses, they cannot mint edge.

---

## Study 2026-07-14d — STREAM BAND MANAGED: Ramana's Case-A stop/re-entry stack vs the naive book (DONE — NOT-IMPROVED; the two-candle exit is the killer)

Ramana's dictated trade management (S133): three simultaneous exits (stream stop terminal · fixed
2°-fractal close-below · TWO-CANDLE-low close-below) + re-entry on reclaiming the broken level (≤3
cycles/setup), both sides. Pre-registered `streamband_managed` `f1da6898`; module + JSON in
research/explosive_moves/. 35,890 bull setups → **78,297 legs** (42,407 re-entries fired as designed).

- **Verdict: NOT-IMPROVED — the managed bull book = Sharpe −0.50 (−0.70/−0.35), MaxDD −90%** vs the
  naive band-stop book **0.37** (0.16/0.53) and the fences trail book 0.59. 1.5× cost → −0.95.
  BEAR mirror (measurement-only, non-shortable): −1.53 — shorts also fight market drift.
- **Root cause is ONE rule: the two-candle-low exit = 84% of all exits (66,041/78,297)**, crushing
  avg hold 15.3→**7.1 bars** and hit 41%→33%. Per-leg mean GROSS is +0.41% (the management is not
  directionally wrong) but 0.6% round-trip cost every ~7 bars ≈ −21%/yr churn drag → net −0.19%/leg.
  On DAILY bars the 2-candle rule is inside normal noise — it sells every wiggle and re-buys higher.
- **Empirical exit ordering across the arc (all same entries): trail-on-2°-structure 0.59 >
  band-stop-only 0.37 > full Case-A stack with 2-candle −0.50.** The fractal stop + stream stop are
  benign; the re-entry logic works mechanically but each cycle pays fresh costs for re-buying higher.
- **Disposition:** the Case-A stack as dictated is REJECTED on daily bars (recorded; do not re-run
  unchanged). The one candidate refinement (fresh prereg required): drop/loosen the two-candle rule
  (e.g. 5-candle, or only-after-profit) — which converges back to the already-measured trail book.

---

## Study 2026-07-14c — RECLAIM SELECTION: can validated factors pick the launchers? (DONE — true-OOS FAIL-null; the reversal arc is now closed at the SELECTION level too)

The last open thread of the reversal-pair arc (the 66d right-skew). Pre-registered + hash-frozen
BEFORE run (prereg `reclaim_selection` `38c6e615`); module `research/explosive_moves/
reclaim_selection.py`; JSON `out/reclaim_selection.json`. Events = the LIVE Screen+ pill applied
historically: floor-intact BUY-reclaims, n=**16,093** (5,301 fit / 10,792 OOS). Protocol = Wolfe-style
fit→freeze→test: rule derived ONLY on 2012-18 (8 candidate features, tercile gaps, sub-period
sign-consistency), numeric cutoffs frozen, tested untouched on 2019-26.

- **Frozen rule (top-2 by fit gap):** vol66 BOTTOM tercile (daily vol ≤ 0.0211) AND deliv_rel TOP
  tercile (delivery% > 1.043× own 252d median) — i.e. "calm + genuinely delivered" reclaims. Fit
  table published in the JSON; notable stable fits: HIGH prior momentum into a reclaim is WORSE
  (mom6 top-tercile med −2.05% vs bottom −0.68%) and HIGH vol worst (−2.44 vs −0.63) — falling-knife
  anatomy; delivery-above-norm the only consistently favorable tell (+1.57% gap, both sub-periods).
- **OOS verdict: FAIL-null (G2/G3/G4).** Selected n=1,483: med 22d excess **−0.46%** (still negative)
  vs unselected **−1.36%** and baseline −1.17%; δ(sel, unsel) **+0.050** (needed +0.10);
  **δ(sel, placebo) +0.004 ≈ ZERO** — the selected subset merely matches random same-stock days
  (placebo med −0.52). The overlay STOPS the bleeding; it never creates edge. Best cut >₹25cr:
  med −0.13%, pos 49.3% — a coin flip, not a signal. 66d selected med −1.54% (skew NOT captured).
- **ARC CONCLUSION (final): the reversal family is falsified at EVERY level — timing (07-13),
  confirmation craft (07-14), risk-geometry book at true cost (07-14b), and now ex-ante SELECTION
  (07-14c). The right tail exists but is not identifiable in advance from price/volume features.**
  Surviving product = the descriptive context columns + the two watch pills, as shipped. The one
  reusable descriptive nugget: among knife-bounces, LOW-vol + above-own-norm-DELIVERY names are
  consistently *less bad* (in-sample and directionally OOS) — context for triage, never a rank.
  Any future reversal proposal must cite 07-13/14/14b/**14c** — all four.

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

## Experiment 2026-07-03 — Dataset-C capital-allocation overlay (DONE — the "fuller lens" answer)

Ran `research/explosive_moves/c_overlay.py` (S77b) — the follow-up the 2026-06-24 caveats demanded:
the production `capital_allocation` composite (ROIIC, ROCE level+trend, dilution drag, debt-funding
share, growth efficiency; financial model for lenders) on **calibrated PIT knowable-dates**
(`fundamentals_asof`, `use_real_knowable`), joined into the IDENTICAL harness (top-25 monthly,
relative liquidity gate 0.60, net-of-cost, walk-forward halves, Nifty500 Sharpe-0.89 hurdle).
157 rebalances; 1,321 gated symbols C-computable. Results in `out/c_overlay.csv`.

| Variant | CAGR | MaxDD | Sharpe | Calmar | H1sh | H2sh | H2 CAGR | Read |
|---|---|---|---|---|---|---|---|---|
| A. RISKADJ rel-gate (baseline) | 35.3% | −41.9% | 1.29 | 0.84 | 1.36 | 1.23 | 34.7% | re-run, matches record |
| B. + C-VETO bottom-quintile | 32.3% | −42.2% | 1.24 | 0.76 | 1.35 | 1.17 | 31.4% | hard veto adds NOTHING |
| C. + C-FILTER top-half | 28.2% | −38.8% | 1.15 | 0.73 | 1.27 | 1.07 | 27.5% | filters cost return (again) |
| **D. + C-BLEND 50/50** | **32.5%** | **−28.2%** | **1.32** | **1.15** | **1.40** | **1.29** | **35.0%** | **new best on every metric** |
| E. + QUALITY-BLEND 50/50 (prior win) | 25.4% | −28.7% | 1.19 | 0.88 | 1.33 | 1.09 | 24.7% | dethroned |
| F. + STACK 50mom/25q/25C | 27.6% | −30.4% | 1.21 | 0.91 | 1.34 | 1.12 | 27.0% | q on top of C makes it WORSE |
| G. D @1.5× cost | 30.6% | −30.1% | 1.26 | 1.02 | 1.33 | 1.24 | 33.1% | cost-robust |

**Findings (recorded):**
1. **C-BLEND 50/50 is the new best overlay — it keeps the baseline's return AND cuts the drawdown.**
   Sharpe 1.29 → **1.32**, MaxDD −41.9% → **−28.2%**, Calmar 0.84 → **1.15** (best ever recorded
   here), and in the high-coverage half (H2) it matched the baseline's CAGR (35.0% vs 34.7%) with
   14pp less drawdown. The quality-blend's DD control came at −10pp CAGR; C's comes at −2.8pp.
2. **C subsumes the 4-metric quality lens.** Head-to-head, C-blend beats quality-blend on every
   column; stacking quality ON TOP of C (F) is worse than C alone (D). The richer
   capital-allocation math (ROIIC + dilution + debt-funding + growth efficiency) carries all the
   information the ROCE/D-E/OPM/IC lens had, plus more.
3. **D66 refined: C's working shape is a RANK BLEND, not a hard veto.** The bottom-quintile veto
   (B) and top-half filter (C) both degrade outcomes — same lesson as quality filters. C stays
   "never a standalone ranker" (untested as one, by design), but "veto" is the wrong consumption
   shape too: fuse it 50/50 with the momentum rank.

**Caveats:** C coverage of the gated universe RAMPS 3% → 89% (mean 61%) — thin in 2012-14 (missing
= neutral 0.5 in blends), so H1 partially reflects neutral-fill; the honest window is H2
(coverage 53-89%) where C still wins (1.29 vs 1.23 vs quality's 1.09). Same simplified per-turnover
cost model as the whole ledger (1.5× stress proxies slippage; no per-name impact/capacity). One
construction family (top-25 monthly RISKADJ). MEP-accumulation and concall-credibility overlays
remain untested.

**Verdict:** **RISKADJ rel-gate + 50/50 C-BLEND is the new investable candidate** (Sharpe 1.32,
Calmar 1.15, DD −28.2%, cost-robust, survives both halves). Consumption (queue #5): fold C in as a
**blend/tilt on the momentum surfaces + descriptive screener column** (ca_score/ca_tier from the
nightly `capital_allocation_scores`), NOT as a hard veto and NOT as a standalone ranker.

**CONSUMED — part (b) LIVE (S78, `8068f80`, deployed + verified):** a **C-blend 50/50 sort** on
`/dash/markets/momentum-scan` — `cblend = mean(riskadj_pctile, COALESCE(ca_pctile, 50))` via a LEFT
JOIN to the nightly `capital_allocation_scores` (missing C → neutral 50th pctile, ~91% live coverage
645/707), with a bold **C-blend** column and a descriptive note citing these numbers. A DESCRIPTIVE
tilt only — not a veto/filter/ranker. Verified live: the blend reorders the top (WELCORP/MCX/BSE/
SOLARINDS/APARINDS rise on strong capital allocation vs the raw-RISKADJ order HFCL/BLISSGVS/BAJAJCON).
Pinned by `tests/test_momentum_cblend.py`. **Part (a) LIVE too:** the descriptive C column shipped on
the wide screener — Screen+ `cap-alloc · C` group (`ca_score` + `ca_tier`) + glossary (`13db67a`) —
and on the stock dossier — `/dash/stock` pt14 card `Cap-alloc (C)` score + C-tier (`cf2a8cb`), both
descriptive with the standard Screener→XBRL source disclosure. **Queue #5 is CLOSED end-to-end**
(descriptive columns + the C-blend momentum tilt); the only open thread is a passive re-check of the
live blend vs the recorded numbers once a few weeks of nightly `ca_pctile` history accrue.

**⚠ RE-STATED 2026-07-05c:** the net Sharpe 1.32 here is **flat-cost only**. Under the participation-cost
model the C-BLEND champion is **NOT fundable** (0.17 @Rs50cr; beats the index at no AUM) — see
Experiment 2026-07-05c below. C-BLEND stays a descriptive/paper overlay; the *fundable* claim is withdrawn.

---

## Studies 2026-07-08 — three pre-registered event studies: ALL NULL (the placebo harness kills two would-be lenses) (S83e)

Modules (gate in each docstring BEFORE the run; JSONs in `research/explosive_moves/out/`):
`insider_drift.py` · `filing_latency.py` · `concall_intent.py` — all on `evlib` (M-01), with the
M-02 shuffled-date placebo (n=200, seed 42) or label-permutation (500 perms) as pre-registered.

| Study | The headline that WOULD have shipped | Why it is NULL (blocking numbers) |
|---|---|---|
| **E-03 insider disclosure drift** (460 post-AUD-08 conviction clusters <5% eq · 247 usable · entry = first disclosure + lag) | value-Q4 CAR60 **+8.26%** (n=66, plain t 2.87); ALL +7.90% (t 4.60) | **Placebo p95 +9.52% > observed** (null mean +3.38%, inflation 0.87×, emp-p 0.085); t_cohort NaN — the feed is ~10 months deep → 2-3 quarterly cohorts, no clustered inference possible. The "drift" is the hot 2025-26 tape those buys sit in, not the disclosure. NO insider-drift lens ships. Re-attempt needs ≥8 quarterly cohorts of feed depth AND a placebo-clearing observed mean. |
| **Filing-latency tell** (1,924 scored events, ≥3 prior filings, late_score vs own trailing median) | late-Q5 filers carry the WEAKEST surprises (mean SUE 0.77 vs early-Q1 1.04) — the "hiding something" folk story is directionally REAL in the fundamentals | …but not in returns: Q5−Q1 CAR60 gap **−0.81%**, union t_cohort −0.84, inside the label-permutation band (\|gap\| p95 2.51%). Lateness predicts surprise MIX, not drift. NO war-room flag ships. |
| **Concall growth-intent walk-forward** (9,461 (call,type) events on real `concall_dt`, 2015→2026) | six types pass t_cohort ≥ 2 + same-sign halves: debt_reduction **+3.52%** (t 2.43) · capex +3.07% (t 2.70) · revenue +1.70% (t 2.57) · demand_outlook +1.90% (t 2.23) · other · new_product | **Placebo (largest passing type, per pre-reg): observed +1.90% vs null mean +2.75% / p95 +3.66%** — inflation 0.52×, emp-p 0.925: random windows of the SAME covered names drift MORE than post-call windows. Every passing type's mean sits inside that null band (even debt_reduction's +3.52% < p95 +3.66%). The old month-granular panel tilts (debt_reduction +2.8% etc.) are hereby recorded **not reproducible on real dates** — covered-universe beta, not content edge. Guidance stays a candor/promise DESCRIPTIVE axis; no content chip ships as an edge. |

Class rules these nulls add: (1) an event study whose cohorts concentrate in <8 quarters cannot
claim cohort-clustered significance — E-03's `t_cohort=NaN` is the tell, not a formality; (2)
**"covered-name drift" is the null that kills content-conditioned concall claims** — always placebo
against random windows of the same names; (3) a directionally-true fundamentals story (late→weak
surprise) is not a returns story. KPI: pre-registered studies this quarter now 6 (target ≥4),
100% ledgered.

**S83g extension (2026-07-07/08) — two more, the first with gates HASHED before the run (M-04):**

| Study | The tell | Why NULL (blocking numbers) |
|---|---|---|
| **E-11 dividend-surprise drift** (gate `e9bd1a7f…`; 15,486 events 2004→2026, 9,166 usable, post-EX clock) | surprise-Q5 CAR60 +1.61% (t_cohort 2.60) looks tidy — but **CUT names drift +1.99% (t 2.07) and HIKES +1.61% (t 2.86): the "surprise" has NO direction**, and even the lowest-surprise quintile drifts +2.28% (t_cohort 2.37, 55 cohorts) | **Placebo: observed +2.13% vs null mean +2.48% / p95 +3.58%** (inflation 0.60, emp-p 0.71) — random windows of dividend PAYERS drift more than post-ex windows. Payer-universe beta on a 22y sample; the covered-name-drift class rule generalizes beyond concalls. No chip ships. |
| **E-12 rebrand pump** (gate `c3f48a42…`; 324 renames → 111 usable on a STITCHED old→new series loader; full power per the n≥50 rule) | the folk story is simply dead: CAR22 **−0.41%** (no pump), CAR60 +0.12%; placebo agrees (null +0.47%, observed below it) | Pump gate fails outright. Fade: pooled mean +0.53% (t 0.23 → no claim per pre-reg) while the COHORT means run negative (t_cohort −2.82) — outlier-carried, recorded as nuance only. Method note: the stitched loader is the reusable piece — rename-boundary events are unmeasurable with naive per-symbol series by construction. |

Quarter tally: **8 pre-registered studies, 8 honest results (2 descriptive-confirmed early, 6 nulls),
100% ledgered, gates hashed from #7 on.** The evidence machine's sales pitch writes itself: five
plausible-looking lenses (+8.3% insider drift, +3.5% debt-reduction calls, +1.6% dividend surprise…)
were killed by the placebo harness before a client ever saw them.

---

## Experiment 2026-07-05c — C-BLEND cost-reality re-cut (DONE — champion NOT fundable; the 1.32 is flat-cost-only)

The recorded champion (Experiment 2026-07-03) — **C-BLEND 50/50, net Sharpe 1.32 / MaxDD −28.2% / Calmar
1.15** — had only ever been costed with the FLAT 0.3%/turnover model (+ a 1.5× stress proxy), never with
the participation-rate (Almgren sqrt-law) model in `cost_participation.py`. Re-cut via
`research/explosive_moves/cblend_cost_recut.py` (read-only; it reproduces the recorded 1.32 *exactly*
under flat cost, so the delta below is the **cost model alone**), the champion's construction unchanged
(monthly, TOPN 25, relative liquidity gate 0.60, `sel_c_blend`, PIT `attach_c`):

| strategy | AUM | net Sharpe | net CAGR | MaxDD | ann cost | > index? |
|---|---|---|---|---|---|---|
| C-BLEND (monthly) | Rs25cr | 0.52 | 9.9% | −46.8% | 21.9% | no |
| C-BLEND | Rs50cr | 0.17 | 1.2% | −69.6% | 30.2% | no |
| C-BLEND | Rs100cr | −0.30 | −9.7% | −89.0% | 41.4% | no |
| RISKADJ core (monthly) | Rs50cr | −0.11 | −6.4% | −86.1% | 41.0% | no |
| **LOWVOL_MOM (qtr, large-cap)** | **Rs50cr** | **1.02** | **18.1%** | **−21.4%** | **3.9%** | **YES** |
| LOWVOL_MOM | Rs100cr | 0.94 | 16.5% | −22.7% | 5.4% | YES |
| Nifty 500 B&H | — | 0.89 | 15.3% | −29.2% | 0% | — |

Halves (C-BLEND net Sharpe): Rs50cr → H1 −0.60 / **H2 0.70**; Rs100cr → H1 −1.35 / H2 0.40. Even in the
honest H2 window (C coverage ~81%) it nets 0.70 — below the 0.89 hurdle.

**Verdict (pre-registered kill criterion met): C-BLEND is NOT fundable** — it beats the index at NO tested
AUM and is already below the hurdle at the smallest size (Rs25cr, 0.52). Cause: the monthly cadence
(12×/yr turnover) on a mid-cap-tilted book (median clip = 10% of ADV at only ~Rs38cr) drives participation
cost 22%→86% across Rs25→500cr; the RISKADJ core (capacity ~Rs30cr) is worse. The **1.32 is RE-STATED as
flat-cost-only**; C-BLEND remains a legitimate descriptive/paper overlay (the D66 fence — blend + a
descriptive column, never a book), and the only participation-fundable corner stays quarterly large-cap
LOWVOL_MOM (~Rs100cr ceiling). LOWVOL_MOM's 1.02 @Rs50cr reproduced exactly, validating the harness.
Caveats: survivor-conditioned C archive (true net if anything lower); single 2012–26 path; one impact
calibration (k=0.6, POV 10%, delay 0.5). This CONFIRMS the standing "nothing beats buy-and-hold net of
cost" verdict (§ Cost realism) rather than overturning it. Failure-models row added.

---

## Experiment 2026-07-05 — PEAD on REAL BSE result dates, delivery-confirmed (DONE — event lens real / every fundable wrapper falsified)

Ran `research/explosive_moves/pead.py` (NEW; offline `--selftest`; read-only; full output
`out/pead_events.csv` + `out/pead_summary.txt` on the VPS). Hypothesis **pre-registered in chat
before touching data**: post-results drift [+2,+60td] rises in SUE (seasonal-random-walk
**Net-Profit-rupee** surprise — no analyst estimates; guardrail #5 value-based) and is stronger when
the 2-session reaction ran on abnormal DELIVERED VALUE. Event dates = ONLY real BSE filing dates
(`provenance_knowable`, 29.2k keys; ground-truthed: RELIANCE|A|2024-03-31 → 2024-04-22 = the actual
Q4FY24 results day — annual keys ARE results-day dates in India, same board meeting). 6,966 events
after ₹1cr-med-turn liquidity + CA-hygiene + suspension gates. Entry = close of day0+1; CAR vs
Nifty 500. Descriptive tables rank within event cohorts (science, not tradeable); the PORTFOLIO
ranks only against trailing-365d PRIOR events (CL-RES-03 — decidable at the entry close), with tier
half-spread+fees + 0.5×ATR slippage per side.

**Effective windows (archive-driven, recorded):** annual SUE needs 4+ aligned annual NPs → the ~12y
Screener annual depth makes A-events computable only from FY2019 (density 2019 A307 → 2024 A585;
2015-18 = 4-8/yr despite ~1,000 real dates/yr). Quarterly archive ~13 qtrs → Q-events explode 2025+
(2,796 in 2025). So Study A ≈ 2019→2026 annual (n=3,130), Study Q ≈ 2023→2026 quarterly (n=3,654).

| CAR60 vs Nifty500 (descriptive, cohort-ranked) | n | mean | med | hit | t | t_cohort |
|---|---|---|---|---|---|---|
| A: ALL | 3,130 | +3.50% | −0.12% | 49.5% | 8.20 | 0.99 |
| A: SUE Q1 → Q5 (monotone) | ~625 ea | +2.12% → +5.07% | | | | Q5: 2.32 |
| A: DELIV T3 (vs T1 +3.16% / T2 +2.28%) | 1,051 | +5.05% | +1.04% | 52.0% | 6.27 | 1.79 |
| **A: SUE Q5 × DELIV T3** | 235 | **+7.62%** | +1.91% | 51.9% | 4.20 | 1.92 |
| A: SUE Q5 × DELIV T1 | 200 | +3.67% | +0.44% | 51.0% | 2.49 | 1.84 |
| A: Q5 × T3 × EAR>0 | 130 | +7.46% | +1.10% | 50.8% | 2.94 | **2.82** |
| A: SUE Q1 × DELIV T3 | 164 | −0.22% | −0.73% | 47.6% | −0.12 | −0.04 |
| Q: ALL (2023-26 era) | 3,654 | −0.92% | −3.06% | 40.7% | −3.21 | 0.02 |
| Q: SUE Q5 × DELIV T3 | 330 | +1.43% | −2.29% | 46.1% | 1.29 | 1.06 |

Calendar-time portfolio (tradeable rule: trailing SUE-pct ≥0.80 ∧ EAR>0 ∧ deliv-pct ≥⅔, hold 60td, NET):

| Book (2019-05 → 2026-07) | Sharpe | CAGR | MaxDD | read |
|---|---|---|---|---|
| PEAD full (344 entries, 65% invested, book avg 17.6) | 0.10 | −0.41% | −42.9% | FAILS both halves (H1 −0.33 / H2 0.24) |
| no-delivery variant (SUE+EAR only) | 0.02 | −1.94% | −56.6% | delivery filter helps; nowhere near enough |
| 1.5× cost stress | −0.32 | −9.89% | −67.4% | cost-fragile |
| HEDGED diagnostic (minus index; gross hedge leg) | **−0.58** | −12.00% | −68.1% | the real-time picks did NOT beat the index at all |
| **Nifty 500 B&H same window (the bar)** | **0.85** | 13.98% | −38.3% | H1 0.70 / H2 0.96 |

**Findings (recorded):**
1. **The pre-registered interaction is REAL at event level — long side only.** Delivery is the active
   ingredient: the same top-quintile surprise drifts +7.62% on high delivered value vs +3.67% on low
   (~+4pp from conviction confirmation). Bad news does NOT drift (Q1×T3 ≈ 0) — consistent with
   Indian shorting friction. Best honest read: Q5×T3×EAR>0 at cohort-t 2.82.
2. **Drift accrues 22→60d; CAR5 ≈ 0 everywhere** — slow-digestion shape (classic PEAD), not day-0
   momentum bleed. Medians ≪ means, hit ~52%: tail-carried — the same SELECTION shape as the
   Wolfe-bull / harmonic edges.
3. **Every tradeable wrapper dies.** Long-only cash book 0.10 net Sharpe (smallcap beta drawdowns +
   ~35% idle-cash drag + costs); hedged diagnostic −0.58 — under thresholds decidable at entry the
   picks didn't beat the index AT ALL. The within-cohort descriptive edge does not survive
   translation to real-time trailing ranks (distributional drift across seasons + era mixing + cost).
4. **Study Q era read:** 2023-26 announcers underperformed the index on average (size drag,
   t_cohort ≈ 0); the ORDERING survives (Q5−Q1 ≈ +2.4pp) but nothing clears cohort-t 2.

**Caveats:** survivor-conditioned fundamentals archive (house-wide caveat); A-study effectively
2019→2026 (archive depth — no pre-2019 walk-forward possible); hedged diagnostic is gross of
hedge-leg cost/margin; one construction family (equal-weight, 60td hold).

**The one untested cell — CLOSED (2026-07-05b, pre-registered before the run).** within-season-so-far
ranks (rank each event's SUE/delivery vs same-(ptype,period_end) cohort-mates that announced STRICTLY
EARLIER — still no-leak, no same-day peek) instead of trailing-365d ranks. Gate = beat Nifty500 0.89
both halves. **Result: net Sharpe 0.06 (H1 0.01 / H2 0.07), 287 entries — WORSE than the trailing
0.10; @1.5× cost −0.36.** Better ranking did not rescue the wrapper; the failure is the long-only
cash translation + costs, not the rank signal. (The trailing book reproduced byte-identical — 0.10 /
−0.41% CAGR — a clean refactor check.) **No fundable PEAD construction remains untested.**

**Verdict: PEAD-delivery = a DESCRIPTIVE EVENT LENS (Wolfe/harmonic class), NOT a fundable book —
every construction (trailing, no-delivery, within-season, hedged) falsified.** Failure-models row
(blocking). **Descriptive product BUILT + LIVE-verified (`pead_surface.py`, the Results-Reaction
Ledger):** per-stock PIT event history — real BSE date, SUE, delivery-x, realized +22/+60d abnormal
move, and the stock's OWN base rates (avg 60d drift; and after "delivery-confirmed beats"
specifically), plus the population cell as labelled context. Compute-on-read, no storage, offline
selftest. Demo (real): DIXON delivery-confirmed beats +13.0%/60d (n=7, hit 60%); TANLA −1.8% (n=4) —
the honest counter-case; ALKYLAMINE +49.4% (n=2). The +7.6%/60td population number may be cited as
context, NEVER a return promise; the surface renders realized history only.

**SCANNER SHIPPED — `/dash/results-reactions` LIVE (S80c).** The descriptive lens now has a board in
the exact shape of the other scanners (rotation / momentum-scan / rsband): a nightly research-venv
snapshot (`pead_surface --snapshot` → `research.db.results_reactions`, 1,570 recent events, 159
delivery-confirmed top-beats, breakpoints SUE p80=2.09 / deliv p67=2.83) rendered by a pure-stdlib
view (`src/web/results_reactions.py`) — who just reported, SUE, delivery-x, the population cell +
its base-rate, and realized +22/+60d drift once settled. A DESCRIPTIVE data surface, not a signal;
the failed book is cited on the page itself. Mounted via `v2_surfaces._ROUTER_SPECS` (curl-verified
200). Open: nightly-chain wiring + nav-lens (nested URL).

---

## Study 2026-07-05b — accumulation-footprint calibration on disclosure labels (DONE — gate FAIL; one survivor + a structural market finding)

Ran `research/explosive_moves/footprint.py` (NEW; offline `--selftest`; read-only; outputs
`out/footprint_windows.csv` + `footprint_summary.txt` on the VPS). A DETECTION study, not returns:
do our tape descriptors elevate WHILE disclosed accumulation is actually happening
(pre-disclosure transaction windows), vs (a) the same stock at random other times (self-controls)
and (b) other stocks on the same dates (cross-controls)? Labels = `insider_events`
conviction OPEN_MARKET_BUY episodes (≥₹50L or ≥0.10% eq, clustered ≤10 sessions) +
`sast_reg29_events` ACQ (≥0.25% acquired), windows trimmed to END BEFORE first public disclosure.
**Pre-registered gate (in the module docstring before the run): ≥2 of 4 a-priori features at
Cliff's δ ≥ +0.20 vs BOTH control sets.**

**Result: FAIL — 1/4.** 947 material episodes → **54 usable case windows** (+104 self / +108
cross controls); **764/947 dropped as disclosure-too-fast** (SEBI PIT Reg-7(2) T+2 rule leaves
<3 pre-public sessions).

| feature | δ vs self | δ vs cross | read |
|---|---|---|---|
| f_trade_size (a-priori) | **+0.329** | **+0.250** | **PASS — the one robust signature: insiders buy in bigger clips** |
| f_deliv_value (a-priori) | +0.322 | +0.196 | missed cross gate by 0.004 |
| f_updel_share (a-priori) | +0.093 | +0.053 | fail |
| f_deliv_per (a-priori) | +0.072 | +0.083 | fail — DVPT's core barely moves during real accumulation |
| f_turnover | +0.317 | +0.171 | (non-a-priori) elevated |
| f_overnight | −0.112 | −0.036 | insiders don't gap it up |

Composite (a-priori mean-pctl): top-5% precision 53.8% vs 20.3% base = **2.65× lift** — but on
n=54, underpowered; NOT a spec sheet. Case composite by source: both=0.637 > insider=0.572 >
sast=0.547 (multi-source campaigns are the most visible).

**Findings (recorded):**
1. **Structural:** India's T+2 insider-disclosure regime means the pre-public tape window barely
   exists at filing granularity — the detection product is NOT front-running the filing; it is
   (a) **campaign-arc detection** across multi-filing sequences and (b) **post-disclosure drift**
   (the filing itself as an event) — both queued as pre-registered follow-ups (charter E-03/E-04).
2. **Avg-trade-size ratio is the validated survivor** (only gate-clearing feature) → approved as a
   DESCRIPTIVE column (compute-on-read), with glossary entry; never a detector claim on n=54.
3. **deliv_per shows ~no elevation during genuine accumulation** — coherent with MEP's recorded
   alpha failure (DSR 0.36): the delivery LEVEL is mostly noise; delivered VALUE + clip size carry
   what little signature exists.

**Caveats:** labels span only the ingest era (~2025-11 → 2026-07); n=54 cases; controls matched on
length + symbol/date but not size/sector; bulk/block labels excluded (2-week table depth — backfill
queued D-05). **Verdict: no detector ships; MEP stays descriptive; failure-models row added.**

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

> **⚠ CORRECTION (2026-07-02) — the "DEFINITIVE" above was AUM-blind.** The flat 0.5×ATR haircut assumed naïve
> market orders and charged the same slippage regardless of order size. Re-run with a realistic **participation-rate
> impact model** (`research/explosive_moves/cost_participation.py`: Almgren √-law `k·σ·√(order/ADV)`, k=0.6, ≤10%
> ADV/day POV cap, tiered spreads) shows quarterly large-cap wide-hold-band **LOWVOL_MOM DOES beat the index at
> small size: net Sharpe 1.02 / CAGR 18.1% at ₹50cr, and beats Nifty-500 up to ~₹100cr; first fails ~₹150cr; 0.61
> at ₹500cr.** So the honest claim is not "nothing works" — it is **"there is a small-capacity (₹50-100cr) defensive
> factor tilt that beats the index net of realistic execution, but no SCALABLE alpha."** The failure was recorded
> AND corrected (per the "nothing discarded" rule). Caveat unchanged: still contingent on LOWVOL_MOM being real
> selection (attribution pending, `attribution.py`).

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

---

## Rule-lab run 2026-07-15 — `SELECT largecap WHERE not_extended RANK BY lowvolmom TAKE 25 HOLD quarterly` (NEW-BENCHMARK)

Prereg: `31d4fe11940ebad6…` (rule_lab_prereg:31d4fe11940e@2026-07-15 09:35:41Z(first)) · qualifier **fundable**
NET return/vol 1.19 (gross 1.19) vs bench 0.89 · halves 1.20/1.42 · placebo p95 0.09 (observed 1.19, emp-p 0.00) · MaxDD -0.27 · ann cost 8.80%
Capacity: ₹75cr
RECORDED SURVIVOR (not a blocker): quarterly large-cap LOWVOL_MOM — participation-fundable at 1.02 @₹50cr, ceiling ~₹100cr (docs/strategy-ledger.md, C-BLEND re-cut 2026-07-05c).

Provenance: env=em_cache, module=explosive_moves.rule_lab_executor, n_rebal=52, n_shuffles=120, pit_membership=n/a (filter not requested), seed=42, window=2012-06-01..2026-02-11

**Approved into the ledger by Ramana, 2026-07-16** (via the Review Inbox, item #602). This rule-lab run reproduced the recorded LOWVOL_MOM survivor under the full gauntlet (pre-registered, walk-forward both halves, random-selection placebo, participation cost, capacity) — it CONFIRMS the one participation-fundable corner the evidence permits, it does not open a new one. First rule-lab verdict signed into canon (D137; the plan-§7.8 inbox-first default, exercised).

### 2026-07-16Y — THE 2012-17 SELECTION FIX FOUND: per-name beta ≤ 1.4 at selection. Beats the sealed union on every headline axis in-sample, flips the failed window positive, survives all four pre-declared kill checks. PRE-REGISTERED as a SIBLING lead — the union's seal is untouched.

- **Verdict: CONDITIONAL (pre-registered forward test; in-sample-selected lead — Codex 15R applies in full).**
- **What ran:** `research/explosive_moves/union_lab.py` — 14 candidates, each = the sealed union + ONE change,
  each on the full period AND the three walk-forward windows, against an in-module control that reproduced the
  sealed numbers EXACTLY (17.5% / −30.5% / 26.04x / beta 0.87 / alpha +6.8% / inv 82%; the cash_blend.py rerun
  same day also reproduced to the digit). Then `union_lab2.py` — adversarial diagnostics with kill conditions
  declared BEFORE the runs.
- **Numbers (the survivor):** union + "exclude qualifiers with trailing-250d beta vs Nifty 500 > 1.4 (min 150
  obs; missing = keep)" — **CAGR 18.1% · MaxDD −24.7% · Rs1Cr→28.84x · beta 0.74 · alpha +8.4% · inv 69%** vs
  the union's 17.5% / −30.5% / 26.04x / 0.87 / +6.8% / 82%. Walk-forward alpha: 2006-11 **+9.3%** (union +9.8%,
  CAGR give-back 17.4% vs 19.0% disclosed — fewer low-beta qualifiers then) · **2012-17 +3.4% vs −4.6%
  (beta 1.42 → 1.03, MaxDD −16.2% → −8.3%)** · 2018-26 **+9.2%** vs +8.3%. The window both sizing levers
  (throttle 16W, inverse-vol 16X) could not reach is closed by a SELECTION lever — exactly what 16X predicted.
- **Kill checks (all passed, declared up front in `union_lab2.py`):** (a) threshold plateau — caps 1.3/1.4/1.5/1.6
  give full-period alpha +8.2/+8.4/+8.8/+8.2 and 2012-17 alpha +4.2/+3.4/+1.9/+0.6: smooth, not a spike (candidate
  stays 1.4 as FIRST-DECLARED; the sweep is stability evidence, not a re-pick — 1.5's higher CAGR is expressly NOT
  adopted). (b) beta-window robust — look 125d/500d keep the result (2012-17 +2.9/+2.2, full +7.4/+8.1).
  (c) **selection not sleeve — in DEAD-CASH money-mode 2012-17 is still −5.6% (union) → +1.7% (cap), beta
  1.34 → 0.76**; the sleeve only adds the rest (+1.7 → +3.4). This is the decisive difference from the throttle's
  failure mode. (d) not a data filter — 29.0% of 7,082 qualifier-quarters genuinely excluded; kept-for-missing-beta
  0.38%.
- **Convergent ML evidence (16AA):** both pre-registered models, trained ≤2016 without being told about the cap,
  independently rank beta as the dominant qualifier feature (GBM importance 0.208 = #1; Ridge coef −0.064, with
  sd63 −0.050 beside it).
- **PRE-REGISTERED:** `docs/prereg/union-beta14-prereg.md`, **SHA-256 =
  `08b46199f96da5414634093b5377e2b3f1f2ca1dccf4a5c9c4c1cfcbbf80bf0c`** — same 4 forward criteria as the union's
  seal, same ≥8-quarter window from 2026-07, plus a frozen SIBLING ADJUDICATION rule (if both pass, higher forward
  alpha graduates). **The union's own seal `a9a14058…` is untouched; the scheduled forward test
  (2026-10-03) is untouched** — the forward session should run `union_lab.py`'s `s_beta_cap_1.4` row beside
  `cash_blend.py` and judge each against its own registration.
- **Provenance:** DB to 2026-07-15 (box, read-only), window 2006-01→2026-07, engine = cash_blend.py foundation
  byte-copied; modules `union_lab.py` / `union_lab2.py` land with this entry's commit.

### 2026-07-16Z — TWELVE candidates REJECTED with numbers (the rest of the battery). Sector caps starve the book; RSI-ranked truncation loses to the engine's arbitrary order BOTH ways (doc/code discrepancy resolved with data); every 6b threshold/combo/timeframe variant loses; the QUALITY TILT is dead — the 16T veto-only doctrine now holds for tilts too.

- **Verdict: REJECTED (all twelve; each a wall — do not re-run without beating these numbers).**
  Bar = the union's 17.5% / beta 0.87 / alpha +6.8% full-period + the three windows. All sleeve200/top60/
  trail-20%@1% unless stated; full tables in `/tmp/union_lab.log` shape, reproducible via `union_lab.py`/`union_lab2.py`.
- **s_sector_cap8 / cap6 (sector-neutral name caps): 14.2% / 14.0% CAGR, alpha +4.5% both.** The cap starves the
  book (inv 72%/66%); 2012-17 improves only to −4.4/−3.7 while both good windows collapse. **The union's sector
  concentration is load-bearing** — do not re-attempt sector-neutral construction on this signal family.
- **s_rank_rsi_desc (the DOCUMENTED "top 60 by RSI strength"): 16.7%, alpha +6.2%. s_rank_rsi_asc: 15.9%, +5.4%.**
  Finding: `cash_blend.py` never ranked — `candidates()[:topn]` truncates in symbol-load order, and that accident
  BEATS both deliberate orderings (15P physics: top-RSI buys the variance toll; bottom-RSI buys the weakest
  qualifiers). union.md §3.D prose corrected this session; the sealed prereg's "top 60 by RSI strength" line is a
  MIS-DESCRIPTION of the engine — the engine (which produced every recorded number and runs the forward test) is
  authoritative; registration prose defect disclosed here, spec file untouched.
- **s_beta_rank_asc (lowest-beta 60): 16.3%, +6.1%.** Ranking the whole book by low beta distorts it; only CAPPING
  the extreme tail works (16Y). 2012-17 −2.3% (better than base, far worse than the cap).
- **t_6b_25 / t_6b_25to30 / t_6b_35 (threshold sweep): 16.6% / 16.4% / 16.4%.** Deeper oversold (25) trades breadth
  for nothing net; looser (35) admits junk turns — 2012-17 alpha −6.4%, the worst row of the battery. The sealed
  <30→≥30 stands.
- **t_6b_or_6f (drawdown-recovery as a third OR-leg): 17.1%, alpha +6.1%, MaxDD −38.5%.** 6f adds high-beta breadth
  exactly when it hurts (2012-17 −5.4%, inv 94%). The 16U ns-verdict on 6f extends to combination use.
- **t_weekly_6b (weekly RS turn replacing daily): 14.2%, +4.3%.** Too slow — misses the fast turns that make 6b
  work (2018-26 alpha +3.5% vs +8.3%).
- **t_mtf_confirm (daily AND weekly agreement on both legs): 16.4%, +6.4%, beta 0.80, MaxDD −26.6%.** Directionally
  right, DOMINATED by the beta cap on every axis (the cap gets more de-risking for less CAGR cost). Note: this AND
  is across timeframes — the 16V two-signal AND stays separately dead (8.6%).
- **q_rank_top60 (quality-ranked selection): 16.1%, +5.7%** (2018-26 collapses to +5.6%). **q_drop_worst25: 17.3%,
  +6.8%** — a wash that barely binds (n 49.0 vs 49.4). Score = within-date percentile mean of OPM% / interest
  coverage / profit-positivity from `fundamentals_history` (research.db, SCREENER-sourced — Guardrail #8: read-only,
  disclosed, result inherits the caveat). **The 16T doctrine — fundamentals stay veto-only, and even the veto is
  inert — now extends to TILTS: fundamentals add nothing to this signal family in any form tested.**
- **Provenance:** same harness/data as 16Y (DB to 2026-07-15, in-module control reproduced the seal exactly).

### 2026-07-16AA — PRE-REGISTERED ML RANKER over the union's qualifiers: PRIMARY MODEL REJECTED by its own frozen bar. The models' one durable output is CONVERGENT: beta is the dominant qualifier feature — the machine rediscovered the 16Y hand rule.

- **Verdict: REJECTED (M1 primary, per the conjunctive bar frozen BEFORE the run). No re-run, no variant shopping.**
- **Registration:** `docs/prereg/union-ml-prereg.md`, SHA-256
  `187c6aa4963e9fe13247b85cce958a006be901d439cc25253356030a8c1d2266`, committed + pushed (`c252a21`) BEFORE
  training. Design: 10 within-date midrank-percentile features over the union's qualifiers (leg, RSI, RSI-gap,
  consistency, RSI-of-RS, turn-age, 250d beta, 63d sector-excess, 126d RS-drawdown, 63d vol), label = within-date
  percentile of forward rebalance-window excess vs Nifty 500, ONE frozen fit, train = label windows closed
  ≤ 2016-12-31 (1,988 rows / 43 dates), test = rebalances ≥ 2017-01-01 (38 dates), model only re-orders the
  qualifier list, all book mechanics sealed-union.
- **TEST WINDOW 2017-01 → 2026 (same engine, same slice):** control (union, engine order) **20.8% / MaxDD −30.5% /
  beta 0.93 / alpha +7.3%** · beta_cap_1.4 **20.8% / −20.9% / 0.83 / +8.3%** · **M1 Ridge(alpha=1.0) 20.4% / −23.8%
  / 0.80 / +8.1%** · M2 GBM(200,0.05,d2,sub0.8,seed42; exploratory) 21.5% / −28.0% / 0.86 / +8.7%.
- **Bar:** (1) beat control on CAGR AND alpha → **FAIL** (alpha yes +8.1 vs +7.3, CAGR no 20.4 vs 20.8);
  (2) beat beta_cap_1.4 on CAGR AND alpha → **FAIL** (both); (3) beta ≤ 1.0 → pass (0.80); (4) DD within 3pp of
  control → pass (better). **REJECTED.**
- **The durable finding:** Ridge coefficients rank rsrsi −0.093, beta −0.064, leg −0.056, sd63 −0.050 (negative =
  prefer low) vs rsi +0.061, ex63 +0.056; GBM importances: **beta 0.208 (#1)**, ex63 0.126, sd63 0.110. Trained
  ≤2016 with no knowledge of 16Y, both models converge on "avoid high-beta/high-vol qualifiers" — independent
  confirmation of the beta-cap physics, and consistent with the estate's LOWVOL_MOM survivor (item #602).
- **M2's 21.5%/+8.7% is recorded but earns NOTHING** — exploratory by frozen protocol. Any future ML attempt is a
  NEW pre-registration (an M2-shaped shallow GBM is the declared starting point), never a post-hoc promotion.
  Honest limit re-stated: 2012-17 is TRAINING data in this design; no OOS claim about the weak regime is possible
  from it.
- **Provenance:** `research/explosive_moves/union_ml.py` (lands with this commit), sklearn 1.7.2 on the box's
  .venv-research, DB to 2026-07-15.

### 2026-07-16AB — S168 (Ramana: "target 25% CAGR... this is a lab"): TWO axes pass on the β14 base — top-40 concentration and RISKADJ-rank — and their pre-declared composite reaches 21.0% PR / 21.8% TR in-sample, surviving slip-2 AND next-day-execution honesty passes. PRE-REGISTERED as the THIRD sibling.

- **Verdict: CONDITIONAL (pre-registered forward test; a third-generation in-sample-selected lead — 15R applies
  with extra force). NOT 25%: the full-period worst-honest floor is 19.5%; only the 2018-26 window touches the
  target (24.6% PR / 25.7% TR / 25.1% TR-lagged).**
- **What ran:** `union_lab3.py` — single-axis sweeps on the β14 base under a bar declared BEFORE any run (win =
  full CAGR > 18.1 AND alpha > +8.4 AND 2012-17 alpha ≥ +2.0 AND no window's alpha −1.5pp), auto-compose rule
  declared (combine ONLY individually-passing axes, at most one composite). In-module controls reproduced the
  union (17.5%/26.04x) and β14 (18.1%/28.84x) to the digit.
- **Axis winners:** **top-40** on the capped set (19.5% / −27.1% / 37.04x / β0.82 / α+9.0; windows +8.4/+4.9/+10.9;
  top-30 borderline, top-20 fails 2006-11 at α+3.2 — the 15P variance toll made visible) · **RISKADJ-rank** of the
  capped qualifiers (6m return ÷ 3m vol, the estate's best-of-32): 18.9% / α+9.3, 2018-26 α+12.0 — notable because
  plain RSI-rank FAILED both ways (16Z); risk-ADJUSTED momentum respects the toll.
- **THE COMPOSITE (auto-composed, not hand-picked): union + β≤1.4 cap + RISKADJ-rank + top-40, sleeve200,
  trail-20@1%:** **CAGR 21.0% · MaxDD −28.4% · Rs1Cr→47.29x · beta 0.81 · alpha +10.3%** — windows α +9.2 / +4.3 /
  +14.3 (ALL positive). **Total-return (16AD accrual): 21.8%**, windows 18.3 / 22.1 / 25.7.
- **Honesty passes (`union_lab3b.py`, run before registration):** @2% stop-slip **19.7% / α+9.2** · **D5-F1
  next-day execution 20.0% / α+9.5 (TR 20.8%)** — neither slippage nor the same-close peek carries the edge ·
  worst honest case (lagged + slip-2, TR) **19.5% / α+9.1 / −29.0% DD**, its 2018-26 window 23.7%.
- **PRE-REGISTERED:** `docs/prereg/union-c40ra-prereg.md`, **SHA-256 =
  `0715a0d9c26e5ea7772e957ad54a2c0fade313dc2038d98d005951986bd1c08f`** — same 4 absolute forward criteria, frozen
  three-way family adjudication (highest forward alpha among passing specs graduates), multiplicity disclosed IN
  the registration, **the family stops at three**. Union seal `a9a14058…` and β14 seal `08b46199…` untouched.
- **Capacity honesty:** 40 names at ADV ≥ ₹5cr, turnover ~1.15/quarter — personal-scale only; the estate's
  participation-cost precedent (C-BLEND recut) says institutional AUM would bite; untested here by design.
- **Provenance:** `union_lab3.py` / `union_lab3b.py` (land with this commit), DB to 2026-07-15, window
  2006-01→2026-07.

### 2026-07-16AC — S168 kills, each with numbers (walls; do not re-run without beating them): trail sweep, sleeve swaps, cap-floor, vs-bench consistency, MONTHLY CADENCE (4th confirmation), and the cross-family LOWVOL_MOM blend (corr 0.83 — dilution, not diversification).

- **Verdict: REJECTED (all seven).** Base for all: β14 (18.1% / β0.74 / α+8.4). Full tables reproducible via
  `union_lab3.py` / `blend_u25.py`.
- **Trail widths 15/25/30/none: 17.3 / 17.3 / 16.7 / 15.2%** (none: MaxDD −45.4%). The sealed trail-20 stands;
  the 15k law ("exits fix RISK, not return") holds on this base too — tighter trail buys DD (−22.5%) at CAGR cost.
- **Sleeve swaps:** Midcap50 **12.4%** (its index is structurally weak pre-2012) · Nifty100 17.0%. **The V17
  Next-50 sleeve is vindicated again — do not re-tune the sleeve index.**
- **Cap-floor-45** (refill scarce books from lowest-beta excluded): 18.5% full BUT **2012-17 alpha +3.4 → −0.2** —
  the floor re-admits exactly the wrong names in exactly the wrong regime (it does help 2006-11: α+11.1). A
  regime-gated floor would be throttle-adjacent conditioning (16W wall) — not pursued.
- **Consistency vs BENCH instead of own sector: 16.8%, 2012-17 α+0.3.** Ramana's own-sector discriminator is
  load-bearing; the reference-index choice is settled.
- **MONTHLY cadence (churn-controlled, hold-unless-lost-2-evals): 14.8%, MaxDD −41.1%** despite turnover control
  (0.78/month) — the grace-hold rides losers through crashes. **The cadence law's 4th confirmation (V10, V12,
  C-BLEND participation, now this). Quarterly is settled — stop testing cadence.**
- **Cross-family blend (`blend_u25.py`): union-β14 ⊕ LOWVOL_MOM largecap quarterly (the rule-lab NEW-BENCHMARK
  #602), 50/50, on the union's own grid (REBAL_STEP patched to 1 → exact alignment), overlap 2012-07→2026-04
  (56 qtrs):** correlation **0.83**; β14 alone 19.3% / −20.9% / α+7.3 · LOWVOL_MOM at real cost **7.7% / −29.5% /
  α−1.6** · blend **13.5% / −25.2% / α+2.9** — strictly dominated by β14 alone; DD is WORSE, not better.
  ⚠ Disclosed: the grid patch's fallback makes a suspended name's forward return ~1 day (downward bias on the
  LOWVOL leg) — but even granting its native ~11-13%, a 0.83-corr 50/50 lands ~16% < 19.3%. **The 16V physics
  (return-corr caps every long-only-momentum blend in this market) now has a cross-family confirmation. Wall:
  do not propose union ⊕ <momentum-family> blends; only a genuinely negative/low-corr sleeve could diversify.**

### 2026-07-16AD — TOTAL-RETURN measurement (dividend accrual, LOWER BOUND): every union-family book has been understating itself by ~+0.6pp CAGR. Measurement, not optimization; the TRI benchmark side is still owed.

- **Verdict: MEASUREMENT RECORDED (no pass/fail).** Parser: `corporate_actions` DIVIDEND rows with explicit
  per-share amounts ("Rs/Re X Per Share") — **19,094 of 22,630 rows parse (97.7% of 2012+ rows; only ~34% of
  pre-2012 rows, which are %-of-face-value — SKIPPED, so every TR number is a LOWER BOUND, and 2006-11 windows
  are the most understated).** Yield denominator = RAW unadjusted price of the era (adjusted-price denominators
  would double-count around splits/bonuses — caught in review before the run). Credit rule: dividend accrues if
  the position is open at ex-date (stop-date honored).
- **Numbers (PR → TR):** union 17.5 → **18.1%** (696 credits) · β14 18.1 → **18.7%** (723 credits) · composite
  21.0 → **21.8%** (592 credits). Alpha rises ~+0.6-0.7pp on each.
- **⚠ Asymmetry disclosed:** the benchmark stays PRICE-index (no TRI series in `index_rows`) — so TR-book vs
  PR-bench OVERSTATES relative alpha by roughly the index's dividend yield; both book-PR and book-TR are always
  printed together, and the sealed forward criteria stay PR-vs-PR. **The TRI ingestion (niftyindices TR series)
  is now a named, valuable data task: it completes this measurement estate-wide.**
- **Provenance:** `union_lab3.py` TR rows (dividend census printed at run start), DB to 2026-07-15.

### 2026-07-16AE — S171 (Ramana: "continue with the remaining levers — era-relative ADV floor and low-corr sleeve"): THE ERA-RELATIVE FLOOR IS THE BIGGEST SINGLE LEVER OF THE WHOLE ARC. A2-composite = 25.5% PR full-period (Rs1Cr→99x), worst-honest 23.9% — the 25% bar is HIT in-sample. Recorded as a DEFERRED LEAD (family closed at three; no registration without the Oct-3 forward result). rf-earning cash adopted as measurement. G-sec sleeve DATA-BLOCKED.

- **Verdict: CONDITIONAL — DEFERRED LEAD (4th-generation in-sample selection; registration deferred per the
  family-closed rule in `union-c40ra-prereg.md`; two Ramana decisions queued below).**
- **The diagnosis (measured first):** the sealed ABSOLUTE Rs5cr ADV floor admits **389 names in 2006 and
  344–424 in 2011–13 vs ~1,500–1,600 in 2024–26** — the filter is nominal while the market's traded value
  grew ~10x, so the early-era universe was ~4x over-tightened, exactly where every union book starved
  (C40RA 2006-11: n 29/40, inv 73%). **Priors cited:** 15N's "wider pond" wall (sector-INDEX count — different
  lever) and 15h's "raise the bar → sinks more" (this LOWERS the early bar; the modern bar is ~unchanged by
  construction). 15L's self-culling-pond wall doesn't bind: the signals + beta cap + RISKADJ rank still pick
  40 names.
- **The fix, calibrated by a rule declared BEFORE the run (no sweeping):** monthly percentile floor at the
  (1−P)-quantile of each month's ADV cross-section, **P = 0.450** = the mean eligible-fraction at Rs5cr over
  the last 12 complete months. Era floors this produces: 2006-01 Rs1.18cr · 2010-01 Rs1.70cr · 2013-01
  Rs0.37cr · 2020-01 Rs0.95cr · 2026-01 Rs4.39cr. **A1** = raw percentile floor; **A2** = max(Rs1cr, floor)
  dust-clamp (both variants declared up front).
- **Results on the C40RA base (controls reproduced to the digit first — b14 18.1, c40ra 21.0):**

| config (PR, 2006-2026) | CAGR | MaxDD | Rs1Cr→ | beta | alpha | 06-11 α | 12-17 α | 18-26 α |
|---|---|---|---|---|---|---|---|---|
| c40ra control | 21.0% | −28.4% | 47.3x | 0.81 | +10.3% | +9.2 | +4.3 | +14.3 |
| **A1 pct-floor** | 25.5% | −32.4% | 99.7x | 0.82 | +14.4% | +11.2 | +5.2 | +17.5 |
| **A2 clamped ≥Rs1cr** | 25.3% | −28.1% | 96.9x | 0.82 | +14.1% | +12.5 | +5.3 | +17.1 |
| B1 rf-cash (bear-state idle @ 1D-Rate/6.5% proxy) | 21.4% | −27.8% | 50.8x | 0.81 | +10.7% | +9.8 | +4.6 | +14.4 |
| **A2-COMPOSITE (A2 + rf-cash)** | **25.5%** | **−27.2%** | **99.0x** | 0.82 | **+14.2%** | +12.8 | +5.4 | +17.1 |
| A1-composite (per the declared A1-first compose rule) | 25.6% | −32.0% | 100.4x | 0.82 | +14.5% | +11.3 | +5.2 | +17.5 |

- **Stress battery (both composites; the small-ADV tail demanded harsher slips than the family standard):**
  A2-composite @2% slip **23.9%/α+12.8** · @3% slip **22.4%/α+11.5** · D5-F1 next-day **24.6%/α+13.6** ·
  **worst-honest (lagged + 2% slip, TR) 23.9% / α+12.9 / MaxDD −31.5** — every stress case beats C40RA's
  unstressed 21.0%. A1's twins are equal on CAGR at every stress level but 3–6pp WORSE on MaxDD.
  **A2 DOMINATES A1: equal return, strictly better drawdown (−27.2 vs −32.0), double the tail ADV (median
  Rs7.7–11.3cr vs Rs5.5–8.7cr), 2012-17 realized beta 1.29 vs 1.49.** A2 is the named deferred lead; A1
  recorded beside it (the declared compose-precedence had picked A1 — the dominance finding supersedes it
  for the LEAD designation, flagged rather than silently swapped).
- **TR:** A1-composite TR measured **26.4%** (Rs1Cr→114.9x); A2-composite clean TR not separately run this
  session — **bounded ≥ its 25.5% PR by construction** (accrual is non-negative); worst-honest TR 23.9%.
  The Oct-3 forward runner should print it.
- **THE CHARACTER CHANGE, stated plainly (why this is not a free lunch):** the floor converts the early/mid
  windows into a SMALL/MID-CAP book — median pick-ADV falls from Rs27cr (C40RA) to Rs7.7–11.3cr (A2),
  2012-17 realized book beta 1.29 (per-name trailing betas pass the 1.4 cap; realized small-cap co-movement
  exceeds it). This is the ledger's known "alpha lives in mid/small-caps" corner (RISKADJ 5cr>25cr;
  participation-cost kills it at AUM). **At personal scale (1/40 slots vs Rs5cr+ ADV) execution is
  plausible; the 0.15%+slip model at the unclamped Rs0.4cr tail is NOT — hence the clamp and the 3% stress.
  Institutional capacity: presumed poor, untested, out of scope.**
- **B1 (rf-earning cash): PASSED its measurement bar** (+0.4pp full, every window up; convention =
  `attribution.py` rf_monthly verbatim: Nifty 1D Rate Index 2016-06+ in `index_rows`, flat 6.5%/yr proxy
  before, attribution.py:76). Adopted into DEFERRED-LEAD REPORTING only — the three sealed siblings'
  forward tests stay exactly per their specs (0% cash).
- **B2 (G-sec/gold bear sleeve): DATA-BLOCKED, not attempted** — `index_rows` holds only dead 2014-15 GSEC
  fragments; no long G-sec/gold history, no history-fetch tool in the repo. Queued onto the TRI/rf feed
  lane (one primary-source ingestion brings TRI + G-sec + rate histories; G#8-clean). The lever stays OPEN.
- **⚖ RAMANA DECISIONS QUEUED:** ① confirm **A2** (dominant) over A1 as the deferred lead; ② **reopen the
  sibling family for a 4th registration now, or hold to the family-closed rule** (registration only after
  the 2026-10-03 forward verdict). Until ②: the A2-composite is a recorded lead, nothing more.
- **Provenance:** `research/explosive_moves/union_lab4.py` (diagnosis print + battery + declared bars/rules)
  · `union_lab4b.py` (stress) · DB to 2026-07-15 · window 2006-01→2026-07 · box read-only, no deploy.

### 2026-07-16AF — S172 (Ramana: "Raise the CAGR target to 30... Let us make it"): ALL THREE new axes pass on the A2-composite base — concentration re-proves at top-30 on the WIDENED universe, LET-WINNERS-RUN adds +1.0pp at ZERO drawdown cost, and score-proportional weights break the old "sizing never adds" prior. COMPOSITE-30 = 26.4% PR / 27.3% TR, worst-honest 24.4%.

- **Verdict: CONDITIONAL — a SECOND deferred lead beside 16AE's (5th-generation in-sample selection, stated
  plainly; family stays closed; the two-lead risk-return menu goes to Ramana).**
- **L1 — concentration RE-TESTED on the widened universe (changed-premise rule; 16AB prior cited):** top-30 =
  25.9%/α+14.6 with **2006-11 α+13.5 — BETTER than the top-40 control (+12.8)**: the old top-20 failure was
  mostly STARVATION, now proven (top-20-new still fails but at 2006-11 α+8.5 vs the old +3.2; top-25 fails on
  DD −34.1). The variance-toll boundary moved 40 → 30 with the wider pool. Coherent 15P physics, both universes.
- **L2 — LET-WINNERS-RUN (weight drift, 5% per-name cap, entrants at 1/40): 26.5%/α+15.1, MaxDD −27.3
  (UNCHANGED vs control), every window better** (+14.8/+6.1/+17.5). The family's quarterly EW-retrim had been
  selling its winners every quarter; drift stops that at zero measured risk cost. Untried before this session.
- **L3 — rank-proportional weights (linear 2:1): 26.3%/α+15.1/β0.79 — PASSES. ⚠ DOCTRINE REVISION recorded:
  the 16X "sizing levers never add" wall narrows to VOL-BASED sizing; SCORE-proportional weighting adds.**
- **COMPOSITE-30 (declared precedence: top-30 × drift):** **26.4% / MaxDD −31.7% / Rs1Cr→115.7x / β0.82 /
  α+15.1**, windows α +14.6/+5.8/+18.2; **TR 27.3% (Rs1Cr→131.8x)**, 2012-17 TR window 30.5%. Stress ladder:
  @2% 24.8 · @3% 23.2 · next-day 25.2 · **worst-honest (lagged+2%+TR) 24.4/α+13.5 — clears the declared 23.9
  bar.** Cost disclosed: MaxDD deepens −27.2 → −31.7 (−36.3 worst-honest) — the 30-push buys return with
  drawdown now; beta holds 0.82.
- **The 30-target statement (honest):** full-period TR 27.3 vs the 30 target — gap 2.7pp; the 2012-17 window
  is AT target (30.5 TR), 2018-26 prints 28.9 TR, and the A2-composite's 2017+ slice (16AG table) prints
  30.1% PR. Without leverage, closing the FULL-PERIOD gap needs the 2006-11 era (bench 8.3%/yr) out-earned by
  ~22pp — α there is already +14.9 TR. Remaining measured upside: the TRI/G-sec feed completions (+~0.5-1pp
  est., unmeasured until ingested). No further config levers proposed — this battery closed the single-axis
  space on the new base too.
- **Gap disclosed:** this battery did not print median pick-ADV (the 16AE character guard) — the pool is
  identical to A2's so 16AE's disclosures carry; the print is owed in the forward runner.
- **⚖ The Ramana menu (supersedes 16AE's decision ①):** the deferred-lead ladder is now A2-composite
  (25.5%/−27.2 DD) vs COMPOSITE-30 (26.4%/−31.7 DD; TR 27.3) — a pure risk-return choice, his call, along
  with decision ② (reopen the family vs wait for 2026-10-03).
- **Provenance:** `research/explosive_moves/union_lab5.py` (declared bars + compose + stress in the
  docstring; controls reproduced to the digit) · DB to 2026-07-15 · box read-only.

### 2026-07-16AG — PRE-REGISTERED ML v2 (GBM over the era-floor capped pool): REJECTED on 4 of its 5 frozen criteria — the hand rule crushes the machine AGAIN, and beta is the #1 feature for the THIRD consecutive time.

- **Verdict: REJECTED (no re-run, no variant shopping; the 16AA/16AG pair now bounds the same-shape ML door
  CLOSED — any future attempt needs genuinely different inputs, not another tabular ranker on these features).**
- **Registration:** `docs/prereg/union-ml2-prereg.md`, SHA-256
  `bf74a7a5dd79b69826f01e359245cb3c8e22b2e3442d87166f592d73e0aa3c0e`, committed + pushed (`a18a2d5`) BEFORE
  training, per the 16AA succession clause (GBM primary). Train = 2,910 rows / 43 dates (46% more than 16AA,
  the era-floor pool); test = 38 dates, 2017-01→2026.
- **TEST WINDOW 2017+ (same engine, top-40, rf-cash):** control (engine order) 25.5%/−29.3/β0.99/α+11.2 ·
  **A2-composite (RISKADJ-rank) 30.1%/−17.9/β0.85/α+16.4** · **M1 GBM 21.1%/−22.1/β0.86/α+8.9 — LOSES to
  BOTH** · M2 Ridge (exploratory) 23.9%/α+11.4 · @2% slip: A2 28.5 vs GBM 20.0.
- **Bar:** 1 beat-A2 FAIL · 2 beat-control FAIL · 3 β≤1 pass · 4 DD-within-3pp FAIL · 5 slip-2 FAIL.
- **The one durable output, third confirmation:** GBM importances rank **beta #1 (0.181)** (consist 0.110,
  rsdd 0.109 next) — the machine keeps rediscovering the levers already coded by hand (β-cap, consistency).
  Momentum-is-beta (t=1.99) holds; the learned-ranking families are now double-rejected pre-registered.
- **Incidental record:** the A2-composite's 2017+ slice prints 30.1% PR — the modern era exceeds Ramana's 30
  target on the existing machinery; the full-period gap is entirely the 2006-11 era's low-benchmark regime.
- **Provenance:** `research/explosive_moves/union_ml2.py` (prereg design verbatim; two head-slice porting
  defects — missing rf_q/stat — fixed before any result was read, run integrity unaffected) · sklearn 1.7.2 ·
  DB to 2026-07-15.

### 2026-07-16AH — S173 (Ramana): COMPOSITE-30 CONFIRMED as the lead; the sibling FAMILY REOPENED by owner decision; COMPOSITE-30 REGISTERED as the FOURTH sealed sibling; the full-record COMPENDIUM lands so every configuration stands complete.

- **Verdict: GOVERNANCE + registration record (no new experiment).**
- **Owner decisions (2026-07-16, verbatim):** *"Confirm COMPOSITE-30 as the lead and reopen the family..
  register it... I'd also like to have the other composites. Record each item in full rather than only as you
  add it, so that all data are in place. We can calculate the results later; for now, let's keep moving
  forward with our research."* This resolves 16AF's menu (COMPOSITE-30 over the A2-composite, with its deeper
  MaxDD −31.7/−36.3-worst explicitly on the table) and **supersedes, by owner authority, the family-closed
  clause frozen in `union-c40ra-prereg.md`** (that sealed file is untouched; the supersession is recorded here
  and inside the new registration).
- **REGISTERED:** `docs/prereg/union-composite30-prereg.md`, **SHA-256 =
  `07ef2ef9cf11bf65b6f43d0677228e4ba87adedd3854f6bac9bf9f7e2e77c82a`** — a COMPLETE self-contained spec
  (era-floor P=0.450 frozen + ₹1cr clamp · β≤1.4 cap · RISKADJ-rank · top-30 · let-winners-run weights cap 5% ·
  sleeve200 + rf-earning bear-cash · trail-20@1% · 0.15%/side · quarterly), the same 4 absolute forward
  criteria, and the FOUR-WAY family adjudication (highest forward alpha among passers graduates). Multiplicity
  at four registered specs disclosed inside.
- **THE COMPENDIUM (Ramana's record-in-full directive):** `docs/strategies/union-ladder.md` — every family
  configuration stands COMPLETE (full ruleset + every recorded number incl. stress ladders): the four sealed
  members (union · β14 · C40RA · COMPOSITE-30), the two recorded-unregistered composites (**A1-composite** ·
  **A2-composite — the lower-drawdown alternative, registration-ready on Ramana's word**), the walls, and the
  open measurement estate. Classed LIVING; a reference index (test `_INDEX_DOCS`); serving via strategy-ref
  rides the owed deploy lane. All data are in place for the forward-test day to compute every row.
- **Accounting sweep (everything in flight, one list):** 4 sealed specs (`a9a14058` · `08b46199` · `0715a0d9` ·
  `07ef2ef9`) · 2 recorded composites (A1, A2) · walls complete in catalog §§A–G · measurements recorded (TR
  lower-bound 16AD, rf convention 16AE) · OPEN: the feed lane (TRI + long G-sec + rate histories; unblocks
  bench-TRI recut + B2 bear-sleeve) · the strategy-ref deploy (union pages not live on the box) · median
  pick-ADV print in the forward runner · Aug-1 churn row-gain check (estate-wide, other lane) · the 2026-10-03
  forward-test day runs all six ladder rows.
- **Provenance:** decisions in-chat 2026-07-16; registration + compendium land with this entry's commit.

### 2026-07-16AI — S174 (Ramana: "crack the niftyindices payload and get the TRI data"): CRACKED. The committed fetcher lands (the S120-recipe gap closes), full 2005→2026 TRI histories for BOTH benchmarks are on disk, pipeline VERIFIED to the paisa against index_rows. Long G-sec history secured (2011+).

- **Verdict: DATA MILESTONE (measurement estate; no strategy claim).**
- **THE CRACK (found by reading the site's own live code through the in-app browser):** the modern site
  serves history from **`/BackPage/getHistoricaldatatabletoString`** (PR OHLC) and
  **`/BackPage/getTotalReturnIndexString`** (TR) — NOT the legacy `Backpage.aspx/...` every prior probe hit.
  The payload is a JSON body whose `cinfo` value is a STRING of SINGLE-QUOTED JS-style JSON
  (`"{'name':'NIFTY 500','startDate':'01-Jan-2025','endDate':'15-Jan-2025','indexName':'Nifty 500'}"`),
  `name` = the UPPERCASED Trading_Index_Name from `IndexMapping.json` (253 indices), ranges capped ~1 year.
  Confirmed working BOTH in-browser and HEADLESS FROM THE BOX (the earlier "WAF block" was purely payload
  shape). Source of truth: the uncommented ajax in `IISLComponet.js`.
- **THE TOOL (the durable artifact):** `research/explosive_moves/niftyindices_hist.py` — chunked yearly,
  3 retries, 1s politeness, "-" NTR values handled, CSVs `date,value[,ntr]`. Primary source, G#8-clean.
  **This closes the standing gap "the S120 recipe was never committed as a tool."**
- **THE DATA (research-side `research/data/niftyindices/`, prod tables untouched — the feed lane owns
  ingestion):** **Nifty 500 TR: 5,341 rows 2005-01-03→2026-07-16** · **Nifty Next 50 TR: 5,341 rows, same
  range (FULL backtest coverage)** · Nifty GS 10Yr: 3,936 rows 2011-01-03→ (the long G-sec series) ·
  Nifty Composite G-sec: 2,114 rows 2018+ (starts too late; 10Yr is primary) · Nifty 500 PR 2024
  cross-check: 249 rows.
- **VERIFICATION:** the PR cross-check matches `index_rows` EXACTLY on all spot dates (2024-01-15
  19885.55 · 2024-06-14 22214.3 · 2024-12-30 22357.15 — byte-identical) → the pipeline is validated
  end-to-end; the TR series ride the same pipeline. TRI sanity: N500 TRI 34,055 vs PR 21,551 on
  2025-01-15 (×1.58 — two decades of dividends, coherent).
- **Unlocked immediately:** the TRI benchmark recut (16AJ, same session) · the B2 G-sec bear-sleeve cells
  (2011+ native, rf fallback before) · a future 1D-rate backfill via the same tool. The prod `index_rows`
  ingestion (manifest + licence gate + timer) remains the feed lane's build, now trivial.
- **Provenance:** fetch log `/tmp/nifty_backfill.log` on the box; tool + this entry land together; browser
  session evidence in-chat (S174).

### 2026-07-16AJ — S174: THE TRI RECUT (the measurement estate completes). The honest hurdle is Next-50 TRI 14.6%/yr; every ladder alpha compresses ~1.0-1.6pp and EVERY family member survives; COMPOSITE-30's honest pairing = book-TR 27.3% vs TRI, alpha +14.8, beta 0.81. B2 G-sec bear-sleeve: INERT on the lead and DATA-BOUNDED on the union.

- **Verdict: MEASUREMENT RECORDED (no pass/fail; the sealed specs' criteria remain PR-vs-PR as frozen —
  this recut reports the honest hurdle beside them for every future judgment).**
- **THE HONEST HURDLE (Nifty Next 50 TRI buy-and-hold, 2006–2026): 14.6%/yr** (windows 11.3 / 25.1 / 11.5)
  vs the PR bar's 13.3% (10.0 / 23.4 / 10.5) — the dividend differential is +1.3pp/yr on the benchmark side.
- **The recut table (book PR CAGRs unchanged — engine reproduced to the digit; α/β re-regressed vs
  Nifty 500 TRI):**

| config | CAGR (PR) | αPR/βPR | **αTRI/βTRI** | 12-17 αTRI |
|---|---|---|---|---|
| union (sealed) | 17.5% | +6.8/0.87 | **+5.8/0.87** | −6.3 |
| β14 (sealed) | 18.1% | +8.4/0.74 | **+7.5/0.74** | +2.2 |
| C40RA (sealed) | 21.0% | +10.3/0.81 | **+9.4/0.81** | +3.0 |
| A1-composite | 25.6% | +14.5/0.82 | **+13.5/0.81** | +3.5 |
| A2-composite | 25.5% | +14.2/0.82 | **+13.3/0.82** | +3.8 |
| **COMPOSITE-30 (lead)** | **26.4%** | +15.1/0.82 | **+14.2/0.81** | +4.2 |
| **COMPOSITE-30 book-TR (the honest pairing)** | **27.3%** | +15.8/0.82 | **+14.8/0.81** (windows +14.0/+5.0/+18.0) | |

  Betas are unchanged under TRI (PR and TRI returns are near-perfectly correlated) — the compression is
  purely the dividend drip times beta, ~0.9-1.7pp by window. **Every member's full-period αTRI stays
  decisively positive; the lead clears the honest hurdle by +12.7pp CAGR (27.3 vs 14.6).** The union's
  known weak window deepens honestly (12-17 αTRI −6.3) — already fixed downstream by the β-cap generation.
- **B2 G-sec bear-sleeve (the 16AE lever, unblocked by 16AI data): two cells, both decided:**
  (a) **On COMPOSITE-30: INERT exactly as pre-stated** — idle ≈1% of book-time at inv 99%; the G-sec row is
  IDENTICAL to base (26.4/26.4). (b) **On the sealed union (idle 18%): DATA-BOUNDED-UNTESTABLE** — the G-sec
  row equals the rf twin to 1dp (18.0 both) because THE bear that matters (2008-09) predates the G-sec
  series (2011+); post-2011 bear-state quarters are too few to separate the sleeves. The lever stays a
  DESIGN option for future bears with no backtest evidence; NOT adopted. Incidentally recorded: the rf-cash
  measurement applied to the union book = 17.5 → 18.0 (+0.5pp; candidate-class beside the seal, spec
  untouched).
- **Defect disclosed (caught before recording):** the first recut printed αTRI ≈ +19-30 at βTRI ≈ 0 — a
  leg-alignment off-by-one in the external-series regression (`stat_vs` covered leg 0, the book series
  cannot). Fixed, rerun; the corrected column is the one recorded here. The bench-CAGR bars and all PR
  numbers were unaffected.
- **Provenance:** `research/explosive_moves/union_lab6.py` (conventions + both B2 cells + the recut) ·
  TRI/G-sec CSVs per 16AI · DB to 2026-07-15 · box read-only.

### 2026-07-16AK — S175 (Ramana: "ingest the TRI data into prod and deploy the strategy pages"): BOTH DONE + LIVE-VERIFIED. Four TRI/G-sec series (16,732 rows) are in prod `index_rows`; the union family's pages are live on `/dash/strategy-ref` with the sanitizer holding.

- **Verdict: OPERATIONS RECORD (prod data-estate + deploy; no strategy claim).**
- **Ingestion (17:5x UTC, zero active writers, off the 14:01 window):** `niftyindices_hist.py --ingest`
  (idempotent: INSERT-where-not-exists on (index_name, trade_date); BEGIN IMMEDIATE + busy_timeout guard) →
  **'Nifty 500 TRI' +5,341 (2005-01-03→2026-07-16) · 'Nifty Next 50 TRI' +5,341 (same) · 'Nifty GS 10Yr'
  +3,936 (2011+) · 'Nifty GS Compsite' +2,114 (2018+)**. Spot verified (N500 TRI 2025-01-15 = 34055.47 ==
  the 16AI fetch). Feed registered: `feed_manifest.FEEDS["indexes_tri"]` (public-archive, pull-on-demand,
  the forward-test runner refreshes) — `test_feed_manifest.py` 12/12. ⚠ Known consequence, deliberate: the
  four names appear in index pickers (e.g. /dash/compare) with pull-on-demand freshness — refresh via the
  committed tool; the feed-lane residue is CLOSED.
- **Strategy-pages deploy (the debt open since S165):** fork-check found the box's `strategies_view.py`
  EXACTLY equal to git `e9d4d95` (clean past version, not forked; the whole delta to HEAD = ONE line, the
  union _PAGES entry) → clean scp, plus all 17 `docs/strategies/*.md` (backups `.bak-s175-*` / dir copy).
  Remote import OK (15 pages). Writer-gated restart at 17:52 UTC (blocking ps check; active; local 200).
- **LIVE WALK (Caddy hostname):** index lists union · `?p=union` 200 and renders · **sanitizer verified:
  "Ramana" 0 · CANONICAL/do-not-archive/governance 0 · the SEAL HASH renders once BY DESIGN** (the public
  tamper-evidence sentence: "SEALED for forward testing (union-prereg.md, SHA-256 a9a14058…)") ·
  regressions clean (`?p=rule-lab` 200, `?p=wolfe-wave` 200). `union-ladder.md` shipped to the box
  (unserved index-class; ready for future serving).
- **Provenance:** backups on box (`.bak-s175-*`); this entry + the `--ingest` mode + the manifest entry land
  together; live-walk transcript in-chat (S175).

### 2026-07-16AL — S176 (Ramana: "run the validation prereg before graduation"): THE SEALED LADDER VALIDATION (37c28824…) IS RUN. C1: the C40→K30 increment is REAL (CI [+0.54,+9.90], p=0.014) — COMPOSITE-30's graduation candidacy STANDS per the frozen D139 rule. C2b survival 1.01 supports the seals — but the ERA-FLOOR rung fails a ≤2018 re-derivation (the highest window-fit-risk rung). C3: quote 21.6% deflated forward expectation beside the 26.4% headline.

- **Verdict: VALIDATION RECORDED (the sealed protocol's frozen rules applied verbatim; no book re-tuned,
  no seal touched). Runner `research/explosive_moves/union_ladder_val.py`; reproduction gate 5/5 to the
  digit (U 17.5/26.04 · B14 18.1/28.84 · C40 21.0/47.29 · A2 25.5/99.03 · K30 26.4/115.69); common grid
  81 quarters.**
- **C1 — paired significance (joint stationary block bootstrap, mean block 4, 10k draws, seed 42; NW-t
  lag-4; JK/Memmel per-period return/vol z; the §15i machinery):**

| increment | CAGR gap | 95% CI | p(≤0) | NW-t | corr |
|---|---|---|---|---|---|
| U→B14 | +0.70pp | [−2.84, +3.77] | 0.332 | −0.07 | 0.950 |
| B14→C40 | +2.90pp | [+0.25, +6.00] | 0.014 | +1.99 | 0.954 |
| C40→A2 | +4.47pp | [+0.69, +8.24] | 0.010 | +2.18 | 0.941 |
| A2→K30 | +0.80pp | [−1.11, +2.82] | 0.214 | +1.01 | 0.986 |
| **C40→K30 (the frozen gate)** | **+5.27pp** | **[+0.54, +9.90]** | **0.014** | +2.22 | 0.908 |
| U→K30 | +8.87pp | [+3.03, +14.07] | 0.002 | +3.04 | 0.855 |

  **FROZEN RULE OUTCOME: CI excludes 0 AND p ≤ 0.05 → the top-of-ladder increment is statistically real;
  COMPOSITE-30 remains the graduation candidate** (it must still clear its own forward criteria on
  2026-10-03). Honest footnotes required by the protocol: the β-cap rung ALONE and the A2→K30 rung ALONE
  are within noise (their value was risk-shape/window-fix, not full-period CAGR) — the middle rungs carry
  the significance. Unlike the sector ladder's V24→V32 (p=0.745 → retired), this ladder's climb survives
  its D139 test in aggregate and at the decisive gate.
- **C2a — stability:** α>0 in 7/7 rolling 3y windows for B14, A2 AND K30 (C40 6/7, U 4/7) — stability
  rises up the ladder.
- **C2b — interim OOS (TRAIN ≤2018, TEST 2019+ once):** P_train = 0.268 (2018's eligible fraction — the
  era-floor calibration is period-sensitive). Generational replay on TRAIN: β-cap ADOPTED · rank+top40
  ADOPTED · **era-floor REJECTED (its TRAIN gate fails — the rung leans on modern liquidity data; the
  highest window-fitting-risk rung of the family, stated plainly)** · top30+drift ADOPTED. The
  TRAIN-derived book (no floor) on untouched 2019+: **31.8% / α+18.3 / β0.80 → survival = 1.01 vs the
  as-sealed K30's 2018-26 α (+18.2) — the declared "supports the seals" band** (2.32 vs its own TRAIN α;
  2019+ was a strong era family-wide: as-sealed on 2019+ = U 24.2/α12.0 · B14 23.8/11.7 · C40 30.4/17.2 ·
  A2 34.1/21.2 · K30 34.6/22.0).
- **C3 — deflated return/vol (Bailey-LdP at quarterly units, attribution.py:314 formula), N_trials = 69
  itemized from 16U–16AH in the runner:** DSR 0.897/0.938/0.980/0.998/0.998 up the ladder (even after
  69-trial deflation the family is far above the null max — not a pure selection artifact); φ = 0.35 → 0.55.
  **Deflated forward-CAGR expectations, now the mandatory companion to every headline: U 15.7% · B14 16.6%
  · C40 18.1% · A2 21.0% · K30 21.6%.** Published in union-ladder.md §9 per the protocol's reporting
  standard.
- **C4 — drift contribution by window: +1.2 / −0.2 / +0.6pp** — NOT concentrated in 2018-26; no
  regime-dependence label required. **C5 — dead-name haircut: A2 −0.8/−1.6pp and K30 −0.9/−1.8pp at
  −70%/−90% (27/23 dead events)** — the era-floor climb is NOT a haircut artifact; the "+4pp artifact"
  hypothesis is dead.
- **What this changes:** ① every public/compendium headline now carries the deflated band; ② the era-floor
  rung carries a permanent window-fit-risk flag (C2b) — if the 2026-10-03 forward window shows the A2/K30
  books underperforming C40-class books, the floor is the first suspect; ③ the graduation decision input is
  complete: frozen-rule PASS + stress PASS + caveats recorded. Nothing graduates before the forward test.
- **Provenance:** sealed protocol `docs/prereg/union-ladder-validation-prereg.md` (37c28824…, coordination
  session; run exactly as frozen) · runner lands with this commit · DB to 2026-07-15 · box read-only.

### 2026-07-16AM — S178 (Ramana: "run the PBO/CSCV check as well"): PBO = 0.043 — LOW overfit risk. The union program's config search survives combinatorially-symmetric cross-validation; the chosen lead ranks OOS-top-decile in every split. The robustness suite is COMPLETE.

- **Verdict: VALIDATION RECORDED (companion to 16AL; declared bands applied, nothing re-tuned).**
- **Method:** Bailey-Borwein-LdP-Zhu CSCV, the estate implementation (`attribution.pbo_cscv`, M-03) mirrored
  verbatim in stdlib (deterministic — equivalence by construction; attribution.py:336 cited). Matrix
  declared BEFORE the run: **T=81 quarters × N=31 signal-invariant book configs** — every S-family /
  concentration / floor / weights / trail / sleeve config the program searched (itemized in the module),
  exclusions disclosed (6 turn-signal variants, 2 quality-tilt configs, cadence, blend, 4 ML models —
  different machinery, all gen-0 rejects). s=8 contiguous blocks → C(8,4)=70 IS/OOS splits; selection metric
  = per-period return/vol (D142 vocabulary). Reproduction gate 5/5 to the digit before any read.
- **RESULT: PBO = 0.043** (declared bands: <0.10 low · 0.10–0.50 moderate · >0.50 severe). λ quartiles
  **+1.87 / +2.64 / +13.82** — the IS-best config lands ABOVE the OOS median in ~96% of splits.
- **The chosen lead is split-robust:** K30's OOS relative rank across the 70 splits = **mean 0.938,
  minimum 0.767** (1.0 = best of 31) — COMPOSITE-30 is top-decile out-of-sample in the average split and
  never leaves the top quartile.
- **Honest observation:** the IS-best tally is rankw 44 · K30 16 · A2 5 · others 5 — the rank-proportional-
  weights variant is IS-best more often than the drift variant, consistent with 16AL's C1 (the A2→K30 rung
  is a statistical near-tie) and 16AF (both passed; drift won by declared precedence). The choice between
  them is ~equivalent by every test run; the precedence decision stands, its equivalence now on record.
- **THE ROBUSTNESS SUITE IS COMPLETE:** D139 paired significance (16AL C1) ✓ · interim OOS survival 1.01
  (C2b) ✓ · 69-trial deflation bands published (C3) ✓ · dead-name/slip/next-day stress (16AB/16AE/16AF/C5)
  ✓ · **PBO/CSCV 0.043 (16AM)** ✓. The era-floor window-fit flag (16AL) remains the one recorded soft spot.
  Nothing further is honestly testable in-sample; the 2026-10-03 forward window is the remaining judge.
- **Provenance:** `research/explosive_moves/union_pbo.py` (matrix + bands in the docstring; lands with this
  commit) · DB to 2026-07-15 · box read-only.

### 2026-07-17 — COORDINATION cross-check of 16AL/S176: C1/C2/C3 independently REPRODUCED by a second harness (no shared engine code) — every verdict identical, not an implementation artifact
- A separate coordination-session runner **`research/explosive_moves/union_ladder_c1.py`** re-ran C1
  independently of S176's `union_ladder_val.py`. The two share NO engine code: this one **exec-loads
  `union_lab5.py`'s engine byte-for-byte** (everything above its print battery) and adds only `sel_union`
  + the reproduction gate + the paired bootstrap — so agreement is a genuine cross-check, not a shared bug.
- **Reproduction gate 5/5 to the digit** (U 17.5/26.04 · B14 18.1/28.84 · C40 21.0/47.29 · A2 25.5/99.03 ·
  K30 26.4/115.69), common grid 81 quarters. **All six paired increments match 16AL to ~2dp:** U→B14 +0.7
  [−2.9,+4.0] p0.35 · B14→C40 +2.9 [−0.1,+6.5] p0.03 · C40→A2 +4.5 [+0.5,+8.7] p0.01 · A2→K30 +0.8
  [−1.2,+2.9] p0.22 · C40→K30 +5.3 [+0.4,+10.4] p0.02 · U→K30 +8.9 [+3.2,+14.5] p0.00. A second
  block-bootstrap variant (Politis-Romano mean-2q, 20k) agrees with the fixed-L=4q variant on every verdict.
- **This CONFIRMS 16AL and adds no new verdict** — the C40→K30 gate PASS and the A2→K30 / β-cap nulls all
  reproduce independently; the graduation input in 16AL stands, now with second-implementation backing.
  Nothing re-tuned; no seal touched; box read-only. Runner committed for reproducibility.
- **C2 also reproduced** (`research/explosive_moves/union_ladder_c23.py`): C2a rolling-3y stability EXACT —
  U 4/7 · B14 7/7 · C40 6/7 · A2 7/7 · K30 7/7 (== 16AL); C2b era-floor period-sensitivity EXACT —
  P_full 0.450 → **P_train(2018) 0.268** (== 16AL), and the as-sealed 2019+ slices reproduce to the digit
  (U 24.2/α12.0 · B14 23.8/11.7 · C40 30.4/17.2 · A2 34.1/21.2 · K30 34.6/22.0). Independently confirms the
  era-floor is the highest window-fit-risk rung.
- **C3 also reproduced**: Deflated Sharpe (Bailey-LdP, `attribution.py:314`, N=69) =
  0.898/0.938/0.980/0.998/0.998 vs 16AL's 0.897/.938/.980/.998/.998 — match to 3dp, robust to N=50/100
  (K30 stays 0.997–0.999). Confirms the family clears 69-trial deflation. **SCOPE:** reproduces C2b's
  DETERMINISTIC anchors (P_train + the 2019+ slices) and C3's DSR statistic — not S176's full TRAIN-replay
  "survival 1.01" (replay lever-selection choices) nor the φ→CAGR band mapping; those stand as recorded in 16AL.

### 2026-07-16AN — S179 (Ramana: "build the strategies that can build the strongest portfolios"): THE PORTFOLIO LAYER OPENS. Fixed-mix book + long-G-sec is the estate's FIRST genuine diversifier — corr ≈ 0.00, return/vol rises monotonically with the G-sec weight. A clean CAGR↔survivability dial, quantified.

- **Verdict: DESCRIPTIVE ALLOCATION STUDY (declared; no registration, no candidate bar). Opens the
  PORTFOLIO CONSTRUCTION LAYER program — one level above the book.**
- **Catalog check honored:** 16AC walls momentum×momentum blends and explicitly left this door open ("only
  a genuinely low/negative-corr sleeve could diversify"); 16AJ's B2 was the bear-STATE-gated sleeve (inert/
  data-bounded) — a FIXED, unconditional mix is neither, and is not the 16W timing wall (no market signal).
- **THE NUMBER THAT OPENS THE DOOR: corr(K30, G-sec 10Yr) = −0.04 native / −0.03 hybrid; corr(A2, G-sec) =
  −0.00** — after every equity-family blend failed at corr 0.79–0.83, the estate finally has a ~zero-corr
  asset with 15 years of native history (G-sec 10Yr: 6.5% CAGR at 4.3% vol, 2011+).
- **The decision-grade table (2011–2026, native G-sec; quarterly-rebalanced fixed weights):**

| mix | K30 CAGR | K30 ret/vol | K30 MaxDD | A2 CAGR | A2 ret/vol | A2 MaxDD |
|---|---|---|---|---|---|---|
| 100/0 | 24.9% | 1.11 | −18.1% | 24.3% | 1.10 | −17.9% |
| 90/10 | 23.2% | 1.14 | −16.7% | 22.6% | 1.13 | −16.5% |
| 80/20 | 21.5% | 1.18 | −15.3% | 21.0% | 1.17 | −15.1% |
| 70/30 | 19.8% | **1.23** | **−13.8%** | 19.3% | 1.22 | −13.6% |

  (Full-period hybrid rows — G-sec = rf-proxy pre-2011, labelled — in the module output; same shape,
  MaxDD −31.7% → −21.2% across the K30 mixes.) **Unlike 16AC's momentum blend (which fell BELOW both
  components), every mix's return/vol RISES: the dial is real.** Each 10% G-sec ≈ −1.7pp CAGR for
  ≈ −1.5pp MaxDD (native) / −3.5pp (full incl. 2008). The "strongest portfolio" answer is a POLICY point
  on this measured curve: 100/0 for maximum compounding (the sealed family), ~80/20 for balanced
  survivability — Ramana's risk appetite picks the point; the curve is now on record.
- **Disclosures:** the mix grid drops the first quarter for G-sec alignment, so its 100/0 rows (25.3/24.5
  full) sit slightly below the headline stats — within-table deltas are the meaningful read; repro gate on
  the underlying books passed first. G-sec side is index (paper) — no fund/execution cost modelled on that
  leg yet. Not advice; descriptive.
- **The program's next steps (recorded, not run):** a portfolio-layer design doc (weights policy, rebalance
  band, the gold leg when primary data exists, drawdown-targeting AS POLICY not signal) · fold the chosen
  policy point into the forward-test day's reporting.
- **Provenance:** `research/explosive_moves/portfolio_mix.py` (design + disclosures in docstring; lands with
  this commit) · G-sec/rf series per 16AI/16AK · box read-only.

### 2026-07-16AO — S181: THE FORWARD-TEST DAY IS ONE COMMAND. `union_forward.py` built + box-verified (repro gate 6/6 to the digit, A1 now cross-lineage-reproduced); the two owed prints land — A2-composite CLEAN-TR 26.3% and the median-pick-ADV table (the small-cap character is EARLY/MID-ERA: recent selections are ₹52–58cr liquid)

- **Verdict: INFRA + MEASUREMENT (no new strategy, no pass/fail moved, no spec touched).** Closes the
  estate's last two owed prints (16AJ/16AD residue) and makes 2026-10-03 mechanical.
- **The runner:** `research/explosive_moves/union_forward.py` (S181) exec-loads `union_ladder_val.py`'s
  engine byte-for-byte (the 16AL harness) and adds ONLY reporting: repro gate on all SIX ladder rows →
  forward window (PREREG cut = legs from the last rebalance ≤ 2026-07-16, per the preregs' own "every NEW
  quarter from 2026-07"; STRICT post-seal cut printed beside) → the four frozen criteria per sealed member
  (INTERIM until ≥ 8 quarters, then the mechanical family adjudication) → median-pick-ADV + clean-TR
  prints → the 16AN portfolio dial (design-doc §9 fold, §10.3 closed). Box run 2026-07-17, read-only.
- **Repro gate 6/6 to the digit** — U 17.5/26.04 · B14 18.1/28.84 · C40 21.0/47.29 · **A1 25.6/100.43
  (first reproduction of the lab4-recorded row through the val engine — the two harness lineages agree)** ·
  A2 25.5/99.03 · K30 26.4/115.69.
- **A2-COMPOSITE CLEAN-TR (the owed print): 26.3% / ₹1Cr→113.65× / MaxDD −27.2% / β0.82 / α+14.9 /
  div 591** — replaces union-ladder.md §5's "not separately run; bounded ≥ 25.5%" (the A1-twin +0.8pp
  inference verified: 25.5 → 26.3). Cross-check anchor on the same code path: **K30 TR reproduced
  27.3% / 131.80× / −31.6% / β0.82 / α+15.8 (16AF + the compendium §3 row) to the digit.** Accrual
  remains a LOWER bound (16AD: ~34% pre-2012 dividend parse).
- **MEDIAN PICK-ADV (full-period / recent-4-rebalances, ₹cr):** U 24.4/31.7 · B14 23.4/45.4 · C40
  27.0/58.7 · A1 8.7/52.1 · A2 11.3/52.1 · K30 12.7/57.7. **New fact: the era-floor books' small/mid-cap
  tilt (16AE's character disclosure) is an EARLY/MID-ERA phenomenon — the CURRENT selections are ₹52–58cr
  liquid,** i.e. personal-scale execution today is comfortable; the historical tail is where the cost
  model strains (unchanged: the ₹1cr clamp + 3% stress cover it).
- **The boundary, derived from data (not assumed):** engine rebalances 2026-04-01 → **2026-07-01
  (= the boundary leg)** → next ≈ 2026-10-01. At run time: 11 of ~63 trading days elapsed, **0 completed
  forward quarters — criteria/dial sections correctly self-suppress.** The 2026-10-03 scheduler date
  lands 2 days after the first forward leg completes: validated, leave it.
- **Provenance:** commit `8655cea` (+ the α/β print refinement in the wrap commit); box log
  `/tmp/union_forward_s181.log`; converged with sibling S180's design doc (theirs kept; §9/§10.3
  trued-up). Box read-only; no deploy of services, no timer, no spec edit.

### 2026-07-16AP — S180 (cont., portfolio-layer program): GOLD LEG — preliminary measurement + a real DATA-QUALITY blocker. GOLDBEES clears the diversification gate (corr −0.18/−0.21, ~uncorrelated like G-sec) BUT the numbers are regime-loaded and rode on a split-fix the estate's adjust pipeline was silently missing. (Renumbered from 16AO — the S181 forward-runner lane pushed 16AO first; it owns the tag.)

- **Verdict: PRELIMINARY DESCRIPTIVE measurement of the design doc's gold leg (`docs/portfolio-layer-design.md` §7). NOT a formal result** — GOLDBEES is not yet feed-protocol-formalised, and the corr rests on a manual split correction (below). No registration, no candidate bar, no deploy. Box read-only; `/tmp/portfolio_gold_probe.py` imports `portfolio_mix.py` (reproduces the sealed K30 26.4/A2 25.5 gates on load) and reuses its EXACT book quarterly returns + grid.
- **DATA FEASIBILITY (§7a): CONFIRMED.** GOLDBEES (NSE bhavcopy, series EQ, primary-source, G#8-clean) has **4,771 trading days 2007-03-19→2026-07-16** — fully covers the 2011+ native decision window; pre-2007 needs the hybrid treatment (same as G-sec). Deepest + most-liquid of 11 gold ETFs in the archive (~15M units/day) → confirmed the design's leading candidate.
- **🔴 DATA-QUALITY BLOCKER FOUND (§7c, the concern the design doc flagged — now REALISED):** GOLDBEES underwent a **100:1 unit subdivision on 2019-12-19** (raw close 3359.6→33.55, ratio 0.01) that is **NOT in `corporate_actions`**, so `adjust.py` (built for equity splits/bonuses) silently left it unadjusted. The uncorrected series prints **native CAGR −16.9%, vol 29.5%** — a single fake −99% quarter, impossible for gold (INR ~+9-10%/yr). *This is why a sanity floor matters: trusting the pipeline would have reported a bogus diversifier that WORSENS drawdown.* Manual back-adjust (pre-split ×0.01, the announced factor) → **native CAGR +11.9%, vol 14.1%** (sane; 2007+ 13.9%/14.1%). **The proper fix (add the split to `corporate_actions`, and audit the peer gold ETFs KOTAKGOLD/AXISGOLD/… for the same gap) is an owed DQ task, spawned separately — it affects ANY consumer of adjusted GOLDBEES prices, not just this study.**
- **THE GO/NO-GO (§7, split-adjusted, native 2011+):** corr(K30, gold) **−0.18** · corr(A2, gold) **−0.21** (2007+ −0.21/−0.25) — **mildly negative, far below the 0.83 momentum-blend wall → gold CLEARS the diversification gate.** corr(gold, G-sec) **−0.12** → the two legs also diversify each other (a three-asset grid would add value). ⚠ **Noise honesty:** n≈62 quarters → corr SE ≈ 0.13, so −0.18 ± ~0.13; the ROBUST claim is "~uncorrelated / not a dilutant," exactly as G-sec's −0.04 is within noise of zero — NOT a precise −0.18.
- **PRELIMINARY two-asset book+gold dial (K30, native 2011+; descriptive; return/vol is a ratio, not a Sharpe):** 100/0 24.9%/1.11/−18.1% · 90/10 24.0%/1.18/−15.8% · 80/20 22.9%/**1.27**/−13.5% · 70/30 21.8%/**1.36**/−11.1% (A2 within ~0.4pp). **On this window gold DOMINATES the G-sec dial** (16AN K30 80/20 21.5/1.18/−15.3; 70/30 19.8/1.23/−13.8): each +10% gold ≈ −1.0pp CAGR (vs G-sec −1.7pp) for a bigger ret/vol + MaxDD gain.
- **⚠ WHY THE DOMINANCE IS NOT A FORWARD CLAIM (read before quoting the dial):** gold's edge over G-sec is driven almost entirely by its **regime-specific +11.9% native return** (gold was flat 2013-19, then surged 2020-26) — NOT forecastable. G-sec's 6.5% is structural (bond yield); gold's is not. The correlation *advantage* (−0.18 vs −0.04) is within noise. **Robust synthesis: gold and G-sec are BOTH ~uncorrelated diversifiers worth combining; gold's weight should be modest and its return NEVER extrapolated from this window.**
- **Next (recorded, not run):** fix the split DQ → formalise GOLDBEES via the feed protocol (manifest + DQ + pull-on-demand) → a proper **three-asset** book/G-sec/gold grid (legs mutually independent at −0.12). Module: `research/explosive_moves/portfolio_mix.py` (unchanged) + the probe. Design doc §7/§10.2 updated same-commit.

### 2026-07-16AQ — S182 (2026-07-17): GOLDBEES split DQ — **RESOLVED**, and it was NOT one symbol: **14 gold-ETF unit subdivisions across 13 ETFs were missing from `corporate_actions`**. Root cause traced, all back-filled + verified; native GOLDBEES CAGR now prints **+11.9%** (was −16.9%). Closes the `16AP` owed task.

- **Verdict: DATA-QUALITY FIX SHIPPED + verified by content on the box (hermes.db).** kickstart-pick-verify first confirmed GOLDBEES still had 0 `corporate_actions` rows. The generic single-day ratio detector (`LAG(close)` over `bhavcopy_rows`, `r<0.5 | r>2.0`) + a `corporate_actions` cross-check found **14 subdivision events with no matching action row** — GOLDBEES 100:1 (2019-12-19) plus AXISGOLD·HDFCMFGETF·GOLDSHARE·BSLGOLDETF·SETFGOLD·LICMFGOLD·IVZINGOLD (all 100:1), QGOLDHALF (50:1), KOTAKGOLD (10:1 ×2: 2015-04-13 + 2021-07-22), IGOLD·ICICIGOLD·GROWWGOLD (10:1). Genuine gold *equities* (GOLDIAM 5:1, SKYGOLD 10:1) DID have their rows → clean control that isolates the ETF class.
- **ROOT CAUSE (traced, not guessed):** `src/automation/corp_actions.py` ingests the NSE corporate-actions API with **`index=equities`** — that feed structurally OMITS the ETF instrument class, so every gold-ETF subdivision was absent. Two adjust consumers reacted differently: `research/explosive_moves/adjust.py` `load_factors` reads ONLY `corporate_actions` (no fallback) → left the series fully RAW (the −16.9% the probe hit); `src/automation/adjust.py` has an observed-jump fallback BUT its `0.02 < ratio < 50` guard EXCLUDES 100:1 (r=0.01) and 50:1 (r=0.02) — only 10:1 (r=0.10) self-corrects there.
- **RATIOS ARE PRIMARY-SOURCE (G#8-clean):** each factor + ex-date is derived from the authentic NSE **bhavcopy** ex-day price step, cross-validated two ways — (a) the rounded ratio leaves a <~2% residual across the ex-day (rest = that day's real gold move); (b) the one illiquid oddball **AXISGOLD** (day-1 print +18% premium) was pinned against GOLDBEES as a same-date reference: AXISGOLD/GOLDBEES ran 99.5 pre-split, settled to ~0.99 post-split → 100:1. All land on the standard gold-ETF grid (100/50/10:1).
- **THE FIX:** `scripts/backfill_etf_splits.py` — a re-runnable, **idempotent** seed (rows go through `corp_actions.store_actions` → `ON CONFLICT(symbol,action_type,ex_date,details) DO NOTHING`; frozen `details` key; `source='nse-bhav-derived-etf-split'`). `--selftest` proves the research-adjust continuity offline; `--dry-run` shows live gaps; `--apply` writes. Writer-safe apply (past the 00:33 backup fire, `fuser`-clear, far from the 14:01 bhavcopy window): **inserted 14, table 26899→26913, re-run inserts 0.**
- **VERIFIED (box, read-only):** GOLDBEES `load_factors()` = `[('2019-12-19', 100.0)]`; ex-day step **0.9986** (fake −99% cliff gone: 2019-12-18 raw 3359.60 → adj 33.596, continuous into 33.55); native 2011+ **CAGR +11.9%** (ledger 16AP: +11.9%), 2007+ **+13.9%** (16AP: 13.9%). (Daily-return vol 15.4/16.2 reads a touch above 16AP's quarterly-grid 14.1 — daily vs quarterly measurement, not a defect; the headline CAGR matches to the digit.)
- **⚠ PRODUCTION ADJUST PATH — corrected + wired (S182 follow-on, `457217e`-era):** an earlier draft of this bullet claimed "NO production consumer wires the tape" — **that was WRONG.** Audit of all `adjusted_closes` call sites: **13 of 14 already wire `events=price_ratios(...)`** (RS, signals, MEP, MTF, CPR, seasonal, rrg, rsband, rs_overlay, ignition, launchpad, reversal, auto_portfolios — the D95 tape-primary standard). The ONE hold-out was `dashboard._stock_levels` (the `/dash/compare` overlay), pure-fallback. **Now wired** (`_action_events` helper + `events=` arg). Separately, the tape guards (`price_ratios` 0.02→0.008 floor + `adjustment_factors` tape-layer 0.02→0.008; the fallback/crash-protection floors kept at 0.02) now carry ETF-scale ratios (100:1 v=0.01, 50:1 v=0.02). Verified on box: `price_ratios(GOLDBEES)={2019-12-19:0.01}`, `_stock_levels` continuous for GOLDBEES/KOTAKGOLD/QGOLDHALF/AXISGOLD + RELIANCE/TCS (0 cliffs); equity deep-history shifts ≤3.1% to the EXACT tape ratio (fallback smeared the ex-day move into the split factor — the tape is more correct + now matches RS). Selftests incl. crash-protection pass; deployed, hermes-api restarted, route 200.
- **✅ SURFACE GAP CLOSED for `/dash/compare` (S182 follow-on):** `_picker_equities(conn)` now merges `nse_etf_list` (328 ETFs) into the compare picker + validation set (2386→2714, labelled `(ETF)`), so ETFs can be *added* to the overlay and render tape-adjusted. Verified: GOLDBEES/QGOLDHALF/SETFGOLD validate + 0-cliff `_stock_levels`; live chip + picker `(ETF)` entry, route 200. The RESEARCH `load_factors` path (portfolio_mix, the gold leg) remains fully fixed.
- **✅ B5 CLOSED — `/dash/stock` unified onto `adjust.adjustment_factors` (S182 follow-on):** retired the last hand-rolled D36 inline back-adjustment; the stock chart (candles + RS overlay) is now canonical + tape-primary → the standalone GOLDBEES stock page renders continuous (live RS-line 2019-12-18 31.34→2019-12-19 31.30, **0 cliffs**; RELIANCE 0 cliffs, no equity regression). 🔴 Gotcha fixed en route: `_action_events` was called with the request `conn` AFTER its `with get_conn()` block had closed → swallowed closed-DB error → empty tape → cliff persisted; fixed with a short-lived `with get_conn() as _tape_conn`. (Lesson: the old inline used only `prev_close`/no DB, so moving to a DB-reading tape exposed a conn-lifetime bug that unit checks + fresh-process tests missed — only the live walk caught it.)
- **PEER VERIFICATION (all 14, same path):** `scripts/verify_etf_splits.py` (new companion) applies `load_factors`+`adjust_closes` to every ETF and scans the full adjusted series — **0 remaining cliffs on all 13 symbols** (raw ex-day steps 0.01/0.02/0.10 → adjusted ~1.0; KOTAKGOLD's TWO splits both resolve), CAGRs now sane gold-like positives (+8.3%…+16.6% over multi-year windows; the 2023-26-only ETFs read higher on the gold surge). Honest residuals: AXISGOLD adj-step 1.20 = a real illiquid day-1 +18% premium that settles to match GOLDBEES within 2 sessions (factor still 100:1, cross-validated — an 83:1 fudge would break the *pre-split* GOLDBEES agreement); IGOLD +0.0% = the real flat-gold 2014-16 window. The scan would have surfaced any missed 2nd split — none did.
- **Provenance:** `scripts/backfill_etf_splits.py` + `scripts/verify_etf_splits.py` (new) + box read-only verify. Design doc §7c marked RESOLVED; PROJECT_STATE S182 + Key file paths; carryforward DQ task closed. Guardrail #8 clean (NSE bhavcopy primary); classify_event(SPLIT)=None → no spurious `security_events` breaks.

### 2026-07-16AR — S180 (cont., portfolio-layer): THE THREE-ASSET GRID (book/G-sec/gold) — and the finding that reshaped it: THE SEALED EQUITY BOOK SELECTS GOLD ETFs. The in-sample optimum degenerates to book+gold (regime-inflated); robust use is a MODEST gold sleeve alongside G-sec.

- **Verdict: DESCRIPTIVE three-asset DIAL (design-doc §7d). No registration, no spec touched, no deploy.** Ran after S182's 16AQ DQ fix landed (GOLDBEES split now in `corporate_actions` → `adjust.py` gives +11.9% native; my probe's idempotent `have_ca` path confirmed "YES (DQ fix)"). Box read-only; `/tmp/portfolio_3asset_clean.py` imports `portfolio_mix.py`, reuses its book/G-sec/grid + `ann_stats`.
- **🔴 THE FINDING (surfaced by the DQ fix): the sealed union book SELECTS GOLD ETFs.** Universe = all series EQ/BE/BZ; gold ETFs trade EQ, have ~0 beta (pass the ≤1.4 cap) and top risk-adj momentum in gold rallies → they rank top-30. Measured (K30/A2 `sel_a2c`, 82 rebalances): **GOLDBEES ×7 · SETFGOLD ×2 · KOTAKGOLD/HDFCMFGETF/ICICIGOLD/HDFCGOLD/GOLDIETF — 12 gold-ETF selection-quarters**, 3.3% each, in 2009/2011/2018/2019/2020/2023/2025×2. **Consequences:** (a) a gold LEG on top DOUBLE-COUNTS gold → the grid uses a **gold-ETF-EXCLUDED** book; (b) the sealed backtests embed gold-ETF exposure on the UNADJUSTED prices S182 just fixed; (c) universe-hygiene issue in the SEALED strategy (affects every union sibling + `union_forward.py`). **Distinct from S182's note that the *production* charting/RS universe is Nifty-500 (no ETFs) — this is the RESEARCH book's broader selection universe.** NOT changed here (sealed-spec change = owner/union-lane call); **spawned as a task**.
- **⚠ ANCHOR DRIFT (secondary):** the sealed book's absolute repro no longer hits 26.4 on the current box — deterministically **26.5** (with etf-splits) / **26.7** (etf-excluded) vs the seal-time **26.4** my earlier S180 probe reproduced to the digit. Decomposition: etf-splits −0.2pp (proves the book holds split-ETFs); a further **+0.3pp from non-`corporate_actions` box data** (DB last written 00:35 UTC; likely a recent index/bhavcopy re-ingestion). Determinism confirmed (2× identical). **The DIAL is robust to the absolute level (design §2); the sealed HEADLINE should be re-verified on a stable snapshot (union lane).**
- **THE GRID (gold-ETF-excluded clean book: K30 26.6% / A2 25.7%; native 2011+; DIAL, descriptive, return/vol NOT a Sharpe).** Edges reproduce the two-asset dials (16AN G-sec + 16AP gold). K30 rows — 100/0/0 25.1%/1.12/−18.1 · 80/20/0 (gsec) 21.6/1.19/−15.3 · 80/0/20 (gold) 23.1/1.27/−13.5 · **80/10/10 22.4/1.24/−14.4** · 70/10/20 21.3/1.34/−12.0 · **max ret/vol 60/0/40 20.7/1.47/−9.0**. corr(clean-K30,gold) −0.18 · (,G-sec) −0.04 · corr(gold,G-sec) −0.12.
- **THE HEADLINE, HONEST:** the in-sample optimum **degenerates to book+gold, ZERO G-sec** — gold's **regime-specific +11.9%** (2020-26 surge) strictly dominates G-sec's structural 6.5% at similar corr. **This is the in-sample-optimization trap, NOT a forward allocation** (gold's return isn't forecastable; G-sec's low-risk role is understated by one gold-bull window). Both legs are genuine ~uncorrelated diversifiers. **Robust use: a MODEST gold sleeve alongside G-sec (80/10/10 · 70/10/20), weights by risk appetite — never this window's optimizer (40% gold).**
- **Provenance:** `portfolio_mix.py` (unchanged) + `/tmp/portfolio_3asset_clean.py`; box read-only, no deploy. Design doc §7d + §10 items 2/5/6 updated same-commit.

### 2026-07-16AS — S183: THE FORWARD GATE MADE DRIFT-PROOF after 16AQ moved the archive — anchors re-derived on the repaired data; the clean decomposition: bounded at the seal date, U/B14/C40 reproduce EXACTLY; only the ERA-FLOOR books moved (the gold ETFs live under their lower floor)

- **Verdict: INSTRUMENTATION + MEASUREMENT (no verdict moved, no spec touched, no deploy of services).**
  Fixes two S181 gate defects exposed by 16AQ/16AR and hardens the 2026-10-03 instrument.
- **The two defects (mine, S181):** (1) the repro gate ran UNBOUNDED full-history — on Oct-3 the new
  forward legs would shift the full-period numbers and false-STOP the gate even on a pristine archive;
  (2) after the 16AQ corporate-actions repair the seal-time anchors no longer describe the current
  archive at all. Found before they could bite (16AR's repro-gate break was the tell).
- **The fix (`union_forward.py`, S183):** the hard gate now compares the ₹1Cr MULTIPLE (window-exact,
  convention-free; 0.006 tolerance ≈ basis-points of terminal wealth) over legs ending ≤ **GATE_END
  2026-04-01** — one leg EARLIER than the seal boundary because `isdead()` reads 60 sessions past a
  leg's end, so the (04-01→07-01) boundary leg stays data-arrival-sensitive until ~late Sep 2026;
  legs through 04-01 are input-closed TODAY and can only move if the engine or archive is EDITED —
  exactly what a hard gate exists to catch. Seal-time headlines print BESIDE with the drift disclosed.
  `--derive-anchors` is the recorded re-derivation loop for any future 16AQ-class repair.
- **THE 16AS ANCHORS (derived 2026-07-18 on the post-16AQ box archive, legs ≤ 2026-04-01, mult):**
  U **20.15×** · B14 **26.01×** · C40 **41.26×** · A1 **87.70×** · A2 **86.59×** · K30 **101.06×**.
  Cross-process determinism: the embedding run must reproduce these to 2dp (verified in the same
  session's full run).
- **THE CLEAN DECOMPOSITION (sharper than 16AR's, because bounded at the seal date):** headline slice
  ≤ 2026-07-16 on the repaired archive — **U 26.04× · B14 28.84× · C40 47.29× = EXACT seal
  reproduction; A1 100.43→100.51 · A2 99.03→99.25 · K30 115.69→116.04.** The 16AQ repair moved ONLY
  the era-floor books — the gold ETFs trade under their lower ADV floors (16AR's 12 selection-quarters)
  and never entered the base books' ₹5cr universe. 16AR's "+0.3pp non-CA data" component reflects its
  probe's unbounded window/different harness, not a seal-window archive change. **Sealed-era TR on the
  repaired archive: K30 27.28% / 132.21× (α+15.81/β0.816) · A2 26.34% / 113.89× (α+14.96/β0.821)** —
  the 16AF/16AO records (27.3/131.80 · 26.3/113.65) stay as seal-time facts; α/β unchanged to 2dp.
- **⚠ Convention caught mid-derivation:** the first slice printer annualized over legs/4 while the
  estate's `stat()` uses (legs−1)/4 — a −0.3pp cosmetic CAGR skew that would have read as drift. The
  gate therefore compares MULT only; CAGR prints in stat-convention, informationally.
- **Open with the owner (unchanged, `task_7a70ad77`):** whether gold ETFs stay in the sealed universe,
  and whether headline rows are ever restated (26.5-with-ETF-splits vs 26.7-ETF-excluded class
  numbers, 16AR) — the seal-time records stand until that call. The compendium carries the
  provenance banner.
- **Provenance:** derive log `/tmp/union_forward_s183_derive.log` · full verification run same session ·
  commits this lane. Box read-only throughout.

### 2026-07-16AT — S184: the GOLD FEED FORMALISED (manifest `gold_etf` + the `chk_split_cliffs` nightly guard) — and the guard FIRED ON ITS FIRST LIVE RUN: 3 index-ETF subdivisions healed same-session; a ~184-event full-history orphan-cliff BACKLOG quantified and spawned

- **Verdict: OPS/DQ (no strategy number moved). Design-doc §7's feed-protocol step is CLOSED.**
- **The formalisation:** `feed_manifest.py:gold_etf` (public-archive; rides the bhavcopy nightly, no new
  fetcher; the 16AQ hazard + heal/proof scripts + the 16AR universe question documented in the row) +
  `data_quality.py:chk_split_cliffs` (23rd check): within ~120d of the tape's own max date, a one-day
  close drop to ≤25% of a ≥₹100 prior close, traded value both days, and NO `corporate_actions` row
  within ±5d → CRITICAL. All symbols, not just gold — the whole silent-corruption class. 3 liveness
  tests; deploy trued the box's stale `data_quality.py`/`feed_manifest.py` up to HEAD (they were
  clean-past: the S169(b)(c) guards and the S175 `indexes_tri` row had never shipped to the box).
- **FIRST-RUN CATCH (the guard's design case, live):** HEALTHADD 2026-07-03 162.94→16.72 ·
  MIDQ50ADD 2026-07-03 247.99→24.76 · PSUBANK 2026-07-10 822.75→85.31 — three INDEX-ETF 10:1 unit
  subdivisions, tape-verified (persistent new level, genuine traded value, zero CA rows ever), missing
  from `corporate_actions`. **The 16AQ class recurring beyond gold, caught within days instead of years.**
  Healed via `scripts/backfill_index_etf_splits.py` (sibling of the S182 tool; reuses its frozen
  `_details()`/`store_actions` idempotency path; 26,913→26,916 rows). Verified: `chk_split_cliffs` → OK
  (2,768 symbols scanned) and the research adjust path now steps 1.026/0.998/1.037 across the ex-days
  (market-normal; was ÷10 cliffs).
- **THE BACKLOG (one-time full-history sweep, read-only): ~184 orphan cliffs total** — (a) modern
  index-ETF subdivisions 2020-26 (ABSLBANETF · BANKBEES · AUTOIETF · BANKNIFTY1/CONS@2026-02-27 …, the
  ETF-class hole) + (b) OLD EQUITY splits predating CA-feed coverage (BERGEPAINT 2004 · CROMPGREAV 2006 ·
  CADILAHC 2015 …). `quarantine.py` has been silently EXCLUDING many of these names, so the cost has been
  lost universe as much as corruption. **Spawned as `task_74bd9558`** with the hard constraints: per-event
  ratio verification (wrong ratio > missing one) · prefer NSE's official historical CA archive for the old
  equities · **any bulk heal changes adjusted history → the sealed-ladder anchors MUST be re-derived via
  `union_forward.py --derive-anchors` + a new ledger entry (the 16AS loop)**. The nightly guard's 120d
  window will NOT self-surface this backlog.
- **Provenance:** commits this lane (`d45381b` + the heal-script commit) · box logs in-session ·
  DQ battery live-run persist=False. Box writes: the 3 idempotent CA inserts only (S182 precedent).

### 2026-07-16AU — S185: THE ORPHAN-CLIFF BACKLOG WORKED — 117 of 181 healed on a four-test evidence battery (64 AMBIGUOUS left untouched, by design); the sealed-ladder anchors re-derived (the 16AS loop's second firing); portfolio_mix's load gates flagged stale

- **Verdict: DATA REPAIR + INSTRUMENT RE-CALIBRATION (no verdict moved; ladder order unchanged;
  seal-time records untouched).** Executes `task_74bd9558` (16AT). Tool: `scripts/audit_orphan_cliffs.py`
  (committed; offline selftest 5/5 incl. a Satyam-shaped crash and a snap-back glitch both refused).
- **The evidence battery (all four must pass to heal):** E1 canonical-ratio fit ±6% of
  {4,5,8,10,20,25,50,100} · E2 persistence (median of next-5 closes within 0.85–1.15× the cliff close) ·
  E3 longevity (≥20 further sessions) · E4 value-continuity (cliff-day traded value ≤5× the trailing-10
  median — a subdivision multiplies UNITS, not rupee value; crashes spike 10–30×). Tape-derived per the
  accepted S182 basis (the bhavcopy IS the primary source); idempotent inserts via the canonical
  `store_actions` path, frozen details text, SOURCE_TAG `nse-bhav-derived-split-audit`.
- **The result: 117 CLEAN healed (26,916 → 27,033 CA rows)** — old-equity splits 2004-2017 (ABANLOYD,
  ADANIEXPO, …) + the modern index-ETF class 2020-2026 (AUTOIETF, FMCGIETF, ALPL30IETF, …). **64 AMBIGUOUS
  reported, not healed** (each carries its failed-evidence tags; CSV `/tmp/orphan_cliffs_s185.csv`,
  regenerate any time): includes likely-real events that need STRONGER evidence — e.g. the same-day
  2021-11-25 ABSL ETF cohort (E4 spikes 5–22×: subdivision-day retail bursts overlap the crash band) and
  BERGEPAINT 2004 (E2 1.44×: post-event rally) — per-event official-archive verification is their path,
  never a loosened threshold. Post-heal: nightly `chk_split_cliffs` OK (2,768 symbols) · re-audit 0 CLEAN.
- **THE 16AS LOOP, SECOND FIRING (this is what the drift-proof gate exists for):** the heal changes
  adjusted history + un-quarantines names → selections shift → `--derive-anchors` re-run. **16AU anchors
  (legs ≤ 2026-04-01, mult): U 19.81 · B14 25.45 · C40 40.51 · A1 87.64 · A2 86.87 · K30 103.71** (from
  16AS: base books dilute ~2% of terminal wealth on the widened universe; K30 +2.6%; A1/A2 ±0.3%).
  Headline slice ≤ seal date: U 25.60 · B14 28.22 · C40 46.43 · A1 100.45 · A2 99.57 · **K30 119.08**
  (seal-time 115.69) — drift printed beside the gate, seal-time GATE_SEAL untouched. Sealed-era TR now:
  K30 27.44/135.65 (α+15.86/β0.817) · A2 26.37/114.44 (α+14.94/β0.818); the 16AF/16AO records stand as
  seal-time facts. Magnitudes: every move ≤ ~3% of 20-year terminal wealth ≈ ≤ ~0.15pp CAGR — the ladder
  ORDER and every recorded verdict are unchanged.
- **⚠ FLAGGED STALE, routed to the owning lane (S180/portfolio):** `portfolio_mix.py`'s load gates
  (`GATE`/`GATE2`: K30 26.4/115.69 · A2 25.5/99.03) now fail on the current archive (16AQ+16AU repairs) —
  AND they are full-period/unbounded, the same defect class 16AS fixed in the forward runner. Any future
  portfolio-layer run must first apply the 16AS-loop treatment there (its constants are part of the
  16AN/16AR evidence chain — not edited by this lane).
- **Residue (recorded):** the 64 AMBIGUOUS events · sub-4:1 ratio events (2:1/2.5:1 splits) are BELOW this
  audit's cliff threshold entirely — quarantine still absorbs those; a lower-threshold pass would need a
  different discriminator (canonical fit alone is too weak at 2:1 vs a −50% crash).
- **Provenance:** audit+heal logs in-session (box) · derive log `/tmp/union_forward_s185_derive.log` ·
  full-run verification same session · commits this lane. Box writes: the 117 idempotent CA inserts only.

### 2026-07-16AV — S187: the 64 AMBIGUOUS orphan-cliffs RESOLVED PER-EVENT against the OFFICIAL ARCHIVES — 44 healed (46 CA rows) · 4 verified non-splits · 4 honest conflicts · 12 no-archive; the ETF-class CA archive DISCOVERED (`?index=mf` — the 16AQ hole has an official primary source after all)

- **Verdict: DATA REPAIR (no strategy number moved by this lane). `task_74bd9558` heal work CLOSED**
  (S184 spawn → S185/16AU healed the 117 tape-CLEAN → this lane resolved the 64 the tape alone could
  not decide). Tool: `scripts/resolve_ambiguous_cliffs.py` (committed; offline selftest 17/17 incl.
  Satyam-, Majesco-, stale-quote- and Shantigear-shaped refusals).
- **Method — two official sources, never unioned (a dual-listed fund's split in both feeds would
  double-count):** ① NSE `corporateActions ?index=mf` — the ETF instrument class the equities feed
  structurally omits (the 16AQ root cause, now complemented): rows carry explicit FV-split text, are
  keyed to CURRENT symbols (official `symbolchange.csv` maps event-era names forward — ICICINXT50→
  NEXT50IETF, UTIBANKETF→BANKBETA, TATATEA→TATACONSUM…), ex-dates sit ±1d off the NSE tape. ② BSE
  `DefaultData/w` CA per scrip (depth ≥2000; scrip chain = bse_scrip_map by event-era symbol → by
  CURRENT symbol → by event-era bhavcopy ISIN → live BSE master ISIN join — never a name-text match).
  OLD BSE split rows can carry a BLANK Purpose: the row still ATTESTS the event; the ratio is then
  pinned by the ex-day tape step snapped to the LEGAL equity FV grid {2, 2.5, 5, 10} at ±9% (bands
  disjoint). Every heal needs tape corroboration ±10% on T0 (=prev/close) or T5 (=prev/median-next-5;
  rallies distort T5, stale quotes distort T0). A loose band [0.75,1.30] + illiquidity evidence existed
  for stale-quote ETFs — **0 events needed it** (AXISNIFTY/UTISXN50/HNGSNGBEES all corroborate ≤10% on T5).
- **The heal: 44 events → 46 rows (44 SPLIT + 2 BONUS), `corporate_actions` 27,091 → 27,137**, sources
  `bse-ca-api-verified` 26 / `nse-mf-ca-api-verified` 20, inserts via the canonical `store_actions`
  (frozen details; ex_date = the TAPE step date; the archive citation rides in details). Notables:
  **ITC 2005-09-21 = BONUS 1:2 + FV-split 10:1 → F=15** (T0 0.918, the +9% ex-day pop is real) ·
  **RUCHINFRA 2005-04-21 = BONUS 3:1 + split 10:1 → F=40 — the r=39.1 mystery solved** (T0 0.978) ·
  TATATEA 2010 10:1 via the TATACONSUM rename (T0 0.983) · GUJGASLTD 2019 explicit "Rs.10→Rs.2" —
  the relist suspicion FALSIFIED by the archive · AXISNIFTY 100→10 with the +20% adjusted ex-day
  step disclosed (stale-quote catch-up to NAV — real, not an artifact).
- **The refusals (the discipline holding):** VERIFIED-NON-SPLIT 4 — FRL + FRLDVR "Spin Off" ·
  NXTDIGITAL "Spin Off" · **MAJESCO r=80.8 = the ₹974/share special dividend** (healing it as a split
  would have been the worst corruption in the set). CONFLICT 4 (attested but uncorroborated, left
  unhealed): SHANTIGEAR (bonus 1:1 attested; residual 8.3 fits no legal FV pair) · HOTELEELA (blank
  row; T0 4.21 snaps to nothing) · ASTRAIDL (T0 4.545/5 = 0.909, misses the 9% snap boundary by
  0.1pp) · VAKRANSOFT (archive factor 20 vs tape 17.5 = −12.6%). UNRESOLVED 12 (no archive row on
  either exchange, incl. SATYAMCOMP — the crash, refused by absence exactly as designed).
- **Verification (all on the box, same session):** post-heal re-audit **0 CLEAN / 20 AMBIGUOUS**
  (= 64 − 44) · research `load_factors` compounds correctly (ITC 15 · RUCHINFRA 40 · 6/6 spot-checks)
  · adjusted ex-day steps 0.92–1.20 (market-normal; the 1.20 is the disclosed AXISNIFTY catch-up) ·
  nightly `chk_split_cliffs` OK (2,768 symbols) · **second `--apply` inserts 0** — idempotency
  demonstrated at both walls (audit-level covered-check + frozen-details ON CONFLICT).
- **⚠ THE 16AS LOOP IS DELIBERATELY NOT FIRED BY THIS LANE:** S186's pushed claim owns the post-heal
  anchor re-derivation for BOTH instruments (`union_forward.py` + `portfolio_mix.py`) and instructed
  this lane not to double-run it. **The 16AU anchor set predates this heal** (44 more events, several
  in research-universe equities) — S186 must re-derive before any research read; settle signal handed
  off in the carryforward.
- **Residue (recorded):** the 12 UNRESOLVED + 4 CONFLICT stay quarantine-absorbed exactly as before
  (per-event report: `/tmp/resolve_s187.csv`, regenerate via the tool). Next lever if ever needed:
  BSE announcements text (archive floor 2006) for the ASTRAIDL/HOTELEELA-class blanks — NEVER a
  loosened threshold. Future mf-feed ingest MUST covered-check ±5d or it double-adjusts (manifest note).
- **Provenance:** dry-run + apply + verification logs in-session (box) · commits this lane · box
  writes = the 46 idempotent CA inserts only (S182/S184/S185 precedent).

### 2026-07-16AW — S186: BOTH REPRO INSTRUMENTS RE-ANCHORED on the fully-repaired archive (the 16AS loop's 3rd firing) — portfolio_mix's gate ported to the bounded policy; the two engine lineages CROSS-CHECK EQUAL; and the repaired archive lands K30's headline back at the seal (115.66× vs 115.69×)

- **Verdict: INSTRUMENT MAINTENANCE (no verdict moved, no spec touched).** Sequenced deliberately AFTER
  the S185 (16AU, 117 tape-CLEAN) and S187 (16AV, 44 official-archive) heals settled — the claim
  markers held across three concurrent lanes (S187's entry: "the 16AS loop is deliberately not fired
  by this lane; S186's pushed claim owns the post-heal").
- **`portfolio_mix.py` gate PORTED to the 16AS-loop policy** (it was stale AND unbounded — the
  pre-16AS defect class, flagged 16AU): hard gate = ₹1Cr MULT only over legs ≤ 2026-04-01 (±0.006);
  seal-time full-period values (26.4/115.69 · 25.5/99.03) demoted to disclosed provenance;
  `PM_DERIVE=1` = its recorded re-derivation loop. Study battery/grid unchanged.
- **THE 16AW ANCHORS (post-16AV archive, legs ≤ 2026-04-01, mult):** U **19.62** · B14 **25.14** ·
  C40 **39.75** · A1 **87.75** · A2 **86.59** · K30 **100.73** — embedded in `union_forward.py`
  (anchor history now 16AS→16AU→16AW) and `portfolio_mix.py` (K30/A2).
- **CROSS-CHECK EQUAL:** the two modules' independent engine copies produce IDENTICAL bounded mults
  for K30 (100.73×) and A2 (86.59×) — the anchor set is not an implementation artifact.
- **THE NEAR-CANCELLATION (measure before narrating):** headline slice ≤ seal date on the FULLY
  repaired archive — U 25.35 · B14 27.87 · C40 45.57 · A1 100.57 · A2 99.24 · **K30 115.66× vs the
  seal-time 115.69× (−0.03%)**; sealed-era TR K30 27.25/131.69 (record 27.3/131.80) · A2 26.35/114.03
  (record 26.3/113.65). The 16AU drift (+2.9% K30, from un-quarantining the tape-CLEAN set) and the
  16AV heals (big old-equity factors: ITC F=15, RUCHINFRA F=40) net out to ~zero on the sealed window —
  the sealed records and the repaired archive now agree to rounding. Base books settle ~2–3% of
  20y terminal wealth below their seal-time headlines (the widened universe's dilution), ladder order
  unchanged throughout.
- **Residue for the record:** 20 AMBIGUOUS remain archive-absent/conflicted (16AV's honest refusals,
  incl. SATYAMCOMP by design) · the `?index=mf` official ETF-class CA archive (16AV discovery) is used
  for resolution but NOT yet wired into the nightly `corp_actions.py` fetcher — the durable upstream
  fix for the 16AQ hole; queued.
- **Provenance:** derive logs `/tmp/pm_derive_s186.log` + `/tmp/uf_derive_s186.log` · full verification
  runs `/tmp/uf_full_s186.log` + `/tmp/pm_full_s186.log` (same session) · commit `1042299`. Box
  read-only throughout (no DB writes by this lane).

### 2026-07-16AZ — S186+ (D143 Phase-4 action #3): the FUNDABLE CORE's ballast dial — STEADY-25 + G-sec/gold measured on ITS OWN grid (the 16AN/AR dials were the UNION book). Already-defensive STEADY still benefits: a modest sleeve ~HALVES the drawdown for ~1-2pp CAGR; every mix beats the index.

- **Verdict: DESCRIPTIVE ballast dial for the FUNDABLE CORE (design-doc §8 Tier B; `/dash/model-portfolios` STEADY-25 overlay).** No registration, no engine change. Box read-only; `/tmp/steady_ballast.py` reads STEADY-25's quarterly NAV (`auto_portfolio_nav`, flat-cost; STEADY flat≈net, low turnover) + G-sec (`gs10yr.csv`) + GOLDBEES split-adjusted (`adjust.py`, the S182 16AQ split). Native 2012+, 57 quarters.
- **Why a NEW measurement:** 16AN/16AP/16AR measured the dial on the UNION book (K30/A2 — Tier C, forward-pending). The model-portfolio's fundable core is STEADY-25, so the overlay had to be measured on STEADY's own returns.
- **The finding — STEADY is ALREADY defensive, but ballast still helps (less dramatically than the higher-vol union book):** STEADY alone **17.1% CAGR / vol 15.8% / ret/vol 1.09 / MaxDD −19.1%** (Nifty500 this window 13.4%). corr(STEADY,G-sec) **+0.08** · corr(STEADY,gold) **−0.24** · corr(gold,G-sec) −0.12 — both genuine diversifiers. **G-sec dial:** 100/0 17.1/1.09/−19.1 → 80/20 15.1/1.18/−14.7 → 70/30 14.1/1.25/−12.4. **Gold dial:** 80/0/20 16.2/1.30/−11.6 → 70/0/30 15.7/1.42/−9.6. **Three-asset:** **80/10/10 15.7/1.25/−13.1** · 70/10/20 15.2/1.39/−9.4. **A modest sleeve roughly HALVES MaxDD (−19→−9 to −13) for ~1-2pp CAGR; every mix still beats the index.**
- **Honesty:** gold's edge is regime-loaded (2012-26 bull) — G-sec is the structural ballast; return/vol ≠ Sharpe; the STEADY NAV is the deployed flat-cost model book (its standalone 17.1% differs ~1pp from the participation-net pin 18.1% @₹50cr — two implementations of LOWVOL_MOM qtr large-cap; the DIAL is the transferable object).
- **Provenance:** `/tmp/steady_ballast.py` (box); design-doc §8 + this entry. No deploy of services by the measurement; the overlay ships as an additive `auto_portfolios_view.py` section (D143 #3).

### 2026-07-16AX — S189: THE 16AQ HOLE CLOSED UPSTREAM — the nightly corp-actions ingest now pulls the OFFICIAL ETF-class archive (`?index=mf`, the 16AV discovery) with the binding ±5d covered-check; future ETF corporate actions arrive without tape-derivation

- **Verdict: FEED/OPS (root-cause remediation; no strategy number moved by the code change itself).**
- **The wire (`src/automation/corp_actions.py`):** `fetch_window`/`ingest_range` parameterised by
  instrument class; **every ingest mode (nightly trailing-400d · --window · --backfill) now pulls
  `?index=equities` THEN `?index=mf`** (`--mf-only` for manual runs). mf rows ride the SAME
  `normalize_api_row` parser (official FV-split text → typed ratios) and are source-tagged
  `nse-ca-api-mf`. **The 16AV binding rule is machine-enforced:** factor-bearing mf rows (SPLIT/BONUS)
  are dropped when ANY same-type row for the symbol sits within ±5 days (`_drop_covered`; mf ex-dates
  sit ±1d off the tape and the S184/S185/S187 heals stored tape-dated rows). Dividends/others keep the
  plain UNIQUE-key idempotency. Module selftest extended (the ±1d split twin drops, the fresh-symbol
  split and the same-symbol dividend pass); AUD-14 retry/breaker suite 5/5 unaffected.
- **Why this ends the arc:** 16AQ (gold-ETF splits missing) → 16AT (3 more caught live) → 16AU (117
  tape-CLEAN healed) → 16AV (44 archive-verified + the mf-archive discovery) → 16AW (instruments
  re-anchored) → **16AX: the class of defect can no longer accumulate — the official feed now covers
  ETFs going forward, and the nightly `chk_split_cliffs` guard stays as the independent backstop.**
- **First live run + anchor consequence recorded separately below if any factor-bearing rows land**
  (a fresh mf pull over the trailing window may insert official split rows the heals didn't cover →
  adjusted history moves → the 16AS loop fires; that is the designed lifecycle, not an incident).
- **Provenance:** manifest rows `corp_actions` + `gold_etf` trued-up same-commit; tests
  test_feed_manifest 11/11 · test_data_quality_liveness 14/14 · test_aud14 5/5 · module selftest OK.

- **FIRST LIVE RUN (same session, box, trailing 400d): 30 mf rows seen → 26 DROPPED by the
  covered-check (the S184/S185/S187-healed events arriving from the official feed and being refused —
  the rule bit live, first contact) → 4 inserted, ALL non-factor (OTHER "Redemption On Account Of
  Maturity", target-maturity bond ETFs AXISBPSETF/SDL26BEES) → corporate_actions 27,137 → 27,141;
  NO adjusted-price change; the 16AW anchors stand un-fired.** Deploy: box md5 == HEAD both files
  (.bak-s189 backups); box selftest OK; timers pick the mf class up on the next nightly.

### 2026-07-16BA — D143 (Ramana "run F — measure the drawdown levers net of cost"): the CONTROLLED lever experiment. Same cadence/universe/cost/AUM; vary ONLY the score. Answer: you CANNOT keep the 35% flat CAGR (it's cost illusion, honest net ~17-18%), and the LOW-VOL BLEND is the lever that keeps the top net return at the shallowest drawdown.

- **Verdict: DESCRIPTIVE controlled measurement.** Reuses `cost_participation.py`'s participation-impact engine verbatim (quarterly · large-cap top-quintile · Rs50cr fixed); `/tmp/dd_levers.py` adds score components (mom12/riskadj/mom6/lowvol) to the tables and pushes each through the SAME `run()`. Box read-only.
- **THE TABLE (net of participation cost @Rs50cr; index Nifty500 15.3%/−29.2%):**

| lever (score) | net CAGR | MaxDD | ret/vol | > index? |
|---|---|---|---|---|
| MOM12 (raw 12-mo momentum) | 16.9% | −50.7% | 0.66 | yes (return) — brutal DD |
| RISKADJ (6-mo mom ÷ vol) | 18.2% | −30.8% | 0.82 | yes |
| MOM6 | 14.1% | −46.9% | 0.60 | no |
| LOWVOL (low-vol only) | 12.7% | −21.3% | 0.96 | no |
| **LOWVOL_MOM (blend = STEADY)** | **18.0%** | **−21.8%** | **1.02** | **yes** |

- **Finding 1 — the flat-cost illusion, quantified:** MOM12 flat **37.6% → net 16.9%**; RISKADJ flat **35.4% → net 18.2%**. Over HALF the headline CAGR was cost + monthly-cadence + all-cap illusion. The honest net ceiling for this family is ~18%, not 35%.
- **Finding 2 — the drawdown lever, isolated (only the score changes):** raw momentum **−50.7%** → risk-adjust (÷vol) **−30.8%** (nearly halves the crash, keeps the return) → pure low-vol **−21.3%** (shallowest but return falls below index) → **LOWVOL_MOM blend = the free-lunch corner: keeps the top net return (18.0%, ≈ RISKADJ's 18.2%) AT the shallow low-vol drawdown (−21.8%), best ret/vol 1.02.** THIS is why LOWVOL_MOM/STEADY-25 is the fundable core.
- **Finding 3 — the full stack:** raw −51% → risk-adjust −31% → low-vol blend −22% → **+ Tier-B ballast (16AZ) −9 to −13%**, all while holding ~18% net. Answer to "keep CAGR, cut DD": blend low-vol into momentum, then add ~zero-corr ballast. You can't keep the fictional 35%; you CAN keep a real ~18% at a −10% drawdown.
- **Note:** quality-overlay lever not in this price-only harness (its flat-cost DD-control −42→−28.7, `overlay_experiment.py`, was never re-measured net of participation — a remaining gap). return/vol ≠ Sharpe. Provenance: `/tmp/dd_levers.py`.

### 2026-07-16AY — S190: THE D142 RF RE-CUT IS LANDED — every research ratio/DSR is now a genuine excess-basis Sharpe; the hurdle re-measured 0.899 raw → 0.528 rf-adjusted; the sealed prereg (44fe16d8…) judged CONFIRMED on all four claims; ZERO signed or leaderboard verdicts move

- **Verdict: MEASUREMENT BASIS CHANGE, verdict-neutral (the sealed prereg's central claim, now proven).**
  Executed per `docs/d142-rf-recut-plan.md` §5 (S170) against the hash-frozen prediction
  `docs/prereg/d142-rf-recut-prereg.md` (SHA-256 `44fe16d8…`, verified intact pre-run). Both docs now
  RETIRE per their recorded lifecycle (this entry is the fold; hashes live in git history).
- **The cut (ONE commit, `5115963`):** 9 research sites — `metrics.equity_stats` · `factory.eqstats`
  (highest fan-out) · `factor_zoo` (+ in-run bar) · `attribution` (retvol_ann/DSR → `strat_ex`) ·
  `cost_realism` · `cost_participation` (+ in-run quarterly bar) · `cblend_cost_recut` · `exit_lab` ·
  `c_overlay` (docstring) — all subtract the estate rf (flat 6.5%/yr proxy, compounded per period;
  attribution uses its dated 1D-Rate series). **The S167 textbook downside-deviation fix
  (sqrt(mean(min(ex,0)²)) over ALL obs) landed in the same cut** (plan §5.5). Label gate extended with
  the 16AY basis-citation category (a "Sharpe" mention must cite the re-cut or disown; bare still fails).
- **THE HURDLE (measured in-run, zoo monthly basis): RAW 0.899 (ledger 0.89 reproduced) → EX 0.528**
  (penalty 0.371; first-order §3 said ~0.40 → confirmed). cost_participation's quarterly in-run bar: 0.544.
- **THE VERDICT TABLE (zoo, excess retvol vs bar 0.528 | first-order predicted):** RISKADJ **1.05**
  (predicted 1.05 EXACT, margin +0.40→+0.52 widens) · MOM12 0.99 · HI52 0.81 · QUAL_MOM 0.75 (0.76) ·
  **LOWVOL_MOM 0.72 (0.73) — margin +0.19: the SIGNED #602 verdict is SAFE**; honest nuance: the margin
  TIGHTENED 0.04 where the first-order said +0.01 — magnitude class right, sign off by a hair, recorded
  as measured · **QMV 0.64 (0.61) — THE ONE PREDICTED CROSSING CONFIRMED on the full-period ratio
  (−0.03 → +0.11), BUT the stricter both-halves survivor flag stays NO** (uneven halves) → **zero
  leaderboard-survivor changes** · DEFENSIVE 0.44 · LOWVOL 0.31 · LOWBETA 0.22 (rejects fail harder ✓).
- **DSR: 0.923 on the genuine excess input — no DSR flip (prereg claim 4 ✓);** the old "LENIENT upper
  bound" caveat retires (banner updated). PBO (attribution N=15 CSCV) 0.343 as measured.
- **Cost estates:** C-BLEND/RISKADJ AUM-grid rejections UNCHANGED (rf-invariant, prereg §4.5 ✓).
  **LOWVOL_MOM: YES at ₹50cr (0.67 vs 0.544); highest AUM still beating ≈ ₹100cr (0.60/16.5%)** — the
  capacity read LOOSENS from the raw-basis ~₹75cr (the hurdle absorbs the bigger penalty). The signed
  #602 record (raw 1.19 @₹75cr) stands as a seal-time raw-basis fact; the excess-basis pair is
  0.72 @25cr-class vs 0.528/0.544 — substance intact.
- **Deliberate non-regenerations:** `exit_lab`/`c_overlay` historical out-CSVs stay as recorded
  raw-basis lab artifacts (their WALLS cite raw numbers); the code cut governs future runs — exit_lab's
  0.79 companion bar shifted by the measured penalty (approximation, flagged in-file). DB `sharpe`/
  `sortino` column names + rule_lab BLOCKING quotes keep legacy names (D142 carve-outs, unchanged).
- **⚖ RAMANA-AWARENESS (no decision needed):** nothing signed/user-facing flips. Disclosed: QMV's
  sub-flag crossing · the ~₹100cr capacity loosening · pre-16AY ledger rows are raw-basis — compare
  like with like (every future print carries its basis).
- **Provenance:** commits `5115963` (the cut) + `c062299` (gate) + this wrap; runs `/tmp/zoo_s190.log` +
  `/tmp/recut_s190.log` (0 tracebacks); artifacts `out/factor_zoo.csv`, `out/cost_realism.csv`,
  `out/cblend_cost_recut.csv` regenerated on the excess basis, committed. Box read-only re DB.
