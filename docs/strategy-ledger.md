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

## ❌ BLOCKING FAILURE MODELS — read before proposing any factor/strategy (2026-07-02)

Ramana's standing rule: **failures are remembered so we never re-walk a dead road.** If a proposal
matches one of these, it is BLOCKED until it beats the recorded number *net of realistic cost*. Cite
the exact figures; do not silently re-attempt. (Mirrored in memory `failure-models-ledger`.)

| Failure model | Recorded result (2012-26, top-25 monthly, vs Nifty 500) | Why it blocks |
|---|---|---|
| **BOOK_YIELD (deep value / B-P)** | Sharpe 0.61-0.63 · **alpha −1.8%…−2.2% (NEGATIVE)** · **beta 1.54-1.56** · **MaxDD −82%** · fails BOTH halves | Negative alpha + −82% drawdown + high beta = a value-trap engine. **Never a production long-ranker.** The β≈1.54 + MaxDD≈82% alone stop us. |
| **EARN_YIELD (cheap on P/E)** | Sharpe 0.70 · alpha +0.4% · MaxDD −71% | No index-beating edge standalone; deep drawdown. |
| **QUALITY standalone** | Sharpe 0.76 · alpha ~0.0% · fails halves | Quality doesn't rank returns alone; only helps *attached to momentum* (QUAL_MOM). → C is a veto/filter, not a ranker. |
| **Momentum sold as a FUNDABLE strategy** | GROSS Sharpe 1.29 → **NET ~0.09, CAGR negative, MaxDD −69%** under realistic cost (~36%/yr, ~100%/mo turnover) | The headline Sharpe is a flat-cost illusion. Nothing beats Nifty-500 buy-&-hold (0.89) net of realistic cost. Momentum = a **gross selection/analytical lens**, not net alpha; any fundable form must be low-turnover (and is then defensive, not alpha). |
| ACCEL / PULLBACK / DELIV_MOM (standalone) | Sharpe 0.42-0.85, MaxDD −44%…−70% | Short-thrust chasing / dip-buying / delivery% added no standalone edge. |
| MEP-accumulation as alpha | Deflated-Sharpe DSR 0.45→0.36 when added | Descriptor-only; adds nothing. Do not re-test as alpha. |
| **PEAD tradeable book (event-time, 2026-07-05)** | ALL constructions fail: trailing net Sharpe **0.10**, no-delivery 0.02, **within-season 0.06** (pre-registered), HEDGED **−0.58**, 1.5× cost −0.32 — vs bench 0.85, both halves | Event drift is REAL descriptively (A-study SUE-Q5×DELIV-T3 CAR60 +7.62%, t_cohort 1.92) but no wrapper survives real-time ranks + costs + compounding; the within-season variant (the last untested cell) also failed. Descriptive event lens only (`pead_surface.py`). Do not re-attempt any PEAD book without beating these exact numbers under the same no-leak harness. |
| **Accumulation-footprint detector v1 (2026-07-05b)** | pre-registered gate **FAIL 1/4** (only trade-size cleared δ≥+0.20 vs both controls: +0.329/+0.250); 764/947 episodes had NO pre-public window (SEBI PIT T+2); n=54 usable | "Front-detect the insider from the tape" is structurally near-impossible in India at filing granularity. deliv_per showed ~no case elevation (δ≈+0.07) — consistent with MEP's alpha failure. Survivor: avg-trade-size ratio = descriptive column only. Follow-ups (campaign arcs E-04, disclosure drift E-03) require fresh pre-registration. |
| CCI credibility as a factor | Spearman ≈0; HIGH−LOW excess −10% @12m (inverse, survivorship) | FALSIFIED as a factor → descriptive/veto only. |
| **C-BLEND 50/50 as a FUNDABLE book (2026-07-05c)** | Flat-cost Sharpe **1.32** (recorded champion) → participation-cost **NET 0.52 @Rs25cr · 0.17 @Rs50cr · −0.30 @Rs100cr**; beats the index at NO AUM; H2 (honest window) 0.70 @Rs50cr < 0.89; ann cost 22%→86% | The 1.32 was **flat-cost only**. Monthly rebalance × mid-cap tilt (median capacity ~Rs38cr) makes Almgren participation impact fatal; the RISKADJ core is worse. C-BLEND stays a **descriptive/paper overlay** (D66 fence holds), never a fundable book. Only participation-fundable corner = quarterly large-cap **LOWVOL_MOM** (1.02 @Rs50cr, ~Rs100cr ceiling). Re-cost: `cblend_cost_recut.py`. |

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
