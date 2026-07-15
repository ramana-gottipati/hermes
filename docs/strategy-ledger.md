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

### 2026-07-15L - 🔴 DATA BUG (`series='EQ'`) INVALIDATED 15j/15k + the decomposition that answers "why do index-beating stocks make an index-losing book?"

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
15h ETF legs / 15i survivorship / 15j hysteresis transfer / 15k fill quality / 15L the `series` filter itself.
The bug was in the DATA LAYER, beneath every model built on it. Audit the universe definition BEFORE the
strategy: `select series, count(*) from bhavcopy_rows group by series` would have caught this on day one.**

### 2026-07-15k - EXITS (Ramana-directed): they FIX THE RISK but NOT the return - the +3.5% alpha was a frictionless-fill artifact. Fill quality is now THE deciding variable.

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
15i survivorship / 15j hysteresis transfer / 15k fill quality). **Treat every first-pass number as provisional
until its friction test runs.**

**Ramana's actual design remains UNTESTED** - everything here is the UNCONDITIONED book (no sector step).
15h/15i's bar is unchanged, and now has a harder floor: the sector-conditioned build must beat a defensive
book already delivering **beta 0.78 / MaxDD -50.6% net of 2% slip**, not just the raw index.

### 2026-07-15j - FIRST HONEST STOCK BOOK: PIT-clean stock RS **LOSES to Nifty 500 at every setting** (~20 variants, 21y, zero survivorship). Naive alpha -0.5%/yr; hysteresis makes it WORSE.

**Module:** `research/explosive_moves/stock_rs_pit2.py` (read-only; `.venv/bin/python ... data/hermes.db`).
**Built because Ramana asked "what alpha have we generated?" and the honest answer was "none - nothing exists".**

**Why it is SURVIVORSHIP-FREE (the whole point - contrast 15i's trap):** the universe at each rebalance comes
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
specifically stocks beating **their own sector** (`rs_vs_sector`, 15i). Different filter, untested. **But the
stakes are now measured: the sector conditioning is not polish on a working book - it must rescue a LOSING
one, creating the entire edge from alpha -0.5%.** Worth knowing BEFORE spending days classifying the 280 dead
names (15i). **The 15h/15i pre-registered bar is unchanged and now has a concrete floor: beat return/vol 0.66
and MaxDD -60.9% net of realistic stock costs, or it is a REJECTION.**

### 2026-07-15i — 🔴 DATA AUDIT before the stock build: PIT sector membership is the ONE blocker, and it is BOUNDED (~1,973 names, 280 of them dead)

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
the survivorship trap 15h/15i already banned (today's narrow INDEX MEMBERSHIP standing in for 2011's, which
structurally selects names that EARNED their way in by outperforming) — industry/sector classification is not a
performance filter, so the bias is structurally much smaller — but it is real: a stock that changed industry, or
that delisted before 2026-07-15, is mis-handled. **It fails CONSERVATIVE, the opposite direction from the banned
mistake: delisted names are EXCLUDED from the universe entirely, never fabricated a performance.** This is a
first, honestly-scoped, genuinely primary-sourced simulation on **268 live names** — not yet the canon's
ultimate ~1,973-symbol PIT-safe build (§15i) with its ~280 dead names and two-sided bias bound. That remains
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
canon's ~1,973-symbol PIT-safe classification with the two-sided dead-name bias bound (§15i) — this 268-name
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
