# Calculations & weights — the single source of truth

**Why this file.** Every weight and calculation in the analytical stack is defined **once, in code**,
and **explained once, here**. Nowhere else restates the numbers — other docs/surfaces/glossary
**link** to the relevant section instead of repeating it. When a weight changes, change it in the
**canonical code constant** and update the **one** entry here; do not copy values into other files.
(This is the "don't repeat, remember where the calculation lives" rule.)

**Convention:** each block gives the **formula/weights**, the **logic** (why these values — nothing
arbitrary), and the **Canonical source** (the `file:symbol` that machine-owns the numbers).

---

## 1. Momentum variants (the gross selection primitives)
**Canonical source:** `research/explosive_moves/factor_zoo.py` (rebalance bar `i0`; `ac`=split-adj close; 126≈6mo, 252≈12mo, 66≈3mo trading days). Reliability context: `docs/predictive-attributes-findings.md` (gross edge real; net-of-cost alpha does not exist — a *selection* lens, not a buy-basket).

| Variant | Formula | Weights inside | Logic |
|---|---|---|---|
| MOM6 | `ac[i0]/ac[i0-126] − 1` | — | 6-mo total return |
| MOM12 | `ac[i0]/ac[i0-252] − 1` | — | 12-mo total return (classic) |
| RISKADJ | `MOM6 ÷ vol_66` | — (ratio) | return per unit 3-mo vol — best return/vol |
| RESID_MOM | `MOM6 − β·idx_MOM6` | — | market-stripped (idiosyncratic) momentum |
| HI52 | `range_pos_252` | — | position in the 52-wk high-low band |
| LOWVOL | `−vol_66` | — | ballast (weak alone) |
| LOWBETA | `−β` (trailing 252 vs Nifty 50) | — | low market sensitivity |
| LOWVOL_MOM | `0.5·rank(−vol) + 0.5·rank(MOM6)` | **0.5 / 0.5** | momentum with a low-vol tilt |
| QUAL_MOM | `0.5·quality + 0.5·rank(MOM6)` | **0.5 / 0.5** | momentum filtered by quality (C) |
| VAL_MOM | `0.5·val + 0.5·rank(MOM6)` | **0.5 / 0.5** | momentum + cheapness (fails OOS — see ledger) |
| QMV | `(quality + rank(MOM6) + val) / 3` | **⅓ each** | quality+momentum+value equal blend |
| DEFENSIVE | `0.5·rank(−vol) + 0.5·quality` | **0.5 / 0.5** | low-vol + quality |

Sub-composites used above (canonical in the same file):
- `quality` = equal mean of `rank(ROCE)`, `rank(−D/E)`, `rank(OPM)`, `rank(interest-cover)` → **0.25 each**.
- `val` = equal mean of `rank(E/P)`, `rank(B/P)` → **0.5 each**.

All blends are on **cross-sectional percentile ranks** (`pctrank`), so the 0.5/0.5 means "equal rank
contribution," not equal raw-value contribution — the honest way to combine unlike units.

---

## 2. Momentum ensemble — Step 2 DECISION (2026-07-02): EQUAL-WEIGHT
**Canonical source:** *this section*, materialized in `research/explosive_moves/momentum_scan.py` (`scan()`, written to `momentum_scan.ensemble_pctile`, surfaced on `/dash/momentum-scan`). The outer `rank(LOWVOL_MOM)` on the blend is applied per AUD-10 (a blend of two ranks must be re-ranked before averaging, else it carries <0.25 effective weight).

**Members (the both-halves survivors only):** MOM12, HI52, RISKADJ, LOWVOL_MOM.
**Weights:** **equal — 0.25 each — on cross-sectional percentile ranks.**
`ensemble = mean( rank(MOM12), rank(HI52), rank(RISKADJ), rank(LOWVOL_MOM) )`

**Logic (why equal-weight, and why not a tilt):**
1. All four independently survived both walk-forward halves (2012-18 & 2019-26). None earned the right to a higher weight over the others.
2. Equal-weight is the **un-overfit prior** — the exact best variant is not stable run-to-run (only the *family* is), so tilting toward the in-sample winner would be fitting noise (this is the "avoid going beyond logic" guard).
3. Risk-awareness is **already inside** the members (RISKADJ = ÷vol; LOWVOL_MOM = low-vol tilt), so the blend leans risk-adjusted without an explicit, hand-chosen tilt.
4. A tilt toward the risk-adjusted pair is a **recorded alternative to test against this baseline**, not the default — and only *after* the beta/size/sector-neutral attribution says the edge is real selection, not levered beta.

**Do not** weight by past return/vol (selection bias), and **do not** add value/quality as a member (they are veto/filter layers, not rankers — §4, and the BLOCKING FAILURE MODELS in `docs/strategy-ledger.md`).

---

## 3. Capital-allocation composite "C" (weights + anchors)
**Canonical source:** `src/automation/capital_allocation.py` — `_WEIGHTS`, `_FIN_WEIGHTS`, `_ANCHORS`, `_TIER_BANDS`. Percentile tiers are ranked **within model** (industrials vs financials separately). Missing components are dropped and the remaining weights renormalised (a thin name isn't zeroed).

**Industrial model** (`_WEIGHTS`, sum = 1.00):
| Component | Weight | Logic |
|---|--:|---|
| roiic (Δ operating-profit ÷ Δ capital-employed) | **0.30** | the core of capital allocation — return on *incremental* capital → highest |
| roce_level | 0.20 | is deployed capital productive now |
| dilution | 0.16 | shareholder-value preservation (issuing shares to grow = penalised) |
| roce_trend | 0.12 | improving vs deteriorating productivity |
| debt_share (of incremental capital) | 0.12 | fragility of the growth funding |
| growth_eff (PAT CAGR ÷ CE CAGR) | 0.10 | earnings growth per unit capital growth |

**Financial (lender) model** (`_FIN_WEIGHTS`, sum = 1.00 — ROCE/ROIIC meaningless when borrowing IS the business):
| Component | Weight | Logic |
|---|--:|---|
| roe_level | **0.35** | ROE is THE lender return metric → highest |
| roa_level | 0.20 | asset efficiency = quality of that ROE (not leverage-inflated) |
| dilution | 0.20 | lenders dilute heavily via QIP → weighted higher than industrials' 0.16 |
| roe_trend | 0.15 | trajectory of returns |
| growth_eff (PAT CAGR ÷ net-worth CAGR) | 0.10 | book-value-growth efficiency |

**Component 0→100 map (`_ANCHORS`, logistic `100/(1+e^{-k(x−x0)})`):** each anchor is an *economic* centre, not an arbitrary cliff — roiic (x0=12 ≈ cost of capital, k=0.10), roce_level (15, 0.12), roce_trend (0, 1.0), dilution PAT−EPS gap (1, 0.60) with equity-cap-CAGR fallback (3, 0.30), debt_share (50, 0.05), growth_eff (1, 1.5), roe_level (13, 0.15), roe_trend (0, 0.80), roa_level (1.5, 0.60).
**Tier bands (`_TIER_BANDS`, cross-sectional percentile):** ≥80 EXCELLENT · ≥60 GOOD · ≥40 AVERAGE · ≥20 WEAK · else POOR.

---

## 4. patearn 14-pattern quality score
**Canonical source:** `src/automation/scoring.py` — `WEIGHTS` (from `resources/patearn/patterns.md`). Per-pattern raw 0–2 per signal × up to 3 signals → `contrib = raw × mult × weight`; `ns_base = ΣΣ ÷ MAX_CWS × 100`.

| # | Pattern | W | | # | Pattern | W |
|--:|---|--:|---|--:|---|--:|
| 1 | ROCE | 9 | | 8 | Institutional Neglect | 6 |
| 2 | Operating Leverage | 9 | | 9 | Earnings Momentum | 6 |
| 3 | Structural Sectoral Tailwind | 8 | | 10 | Margin Expansion | 6 |
| 4 | Valuation | 8 | | 11 | VCP / Technical | 5 |
| 5 | Balance-Sheet Quality | 8 | | 12 | Receivables Discipline | 7 |
| 6 | Promoter Conviction | 7 | | 13 | Working Capital | 6 |
| 7 | Export / Mix Inflection | 7 | | 14 | Volume Confirmation | 5 |

**Derived constants** (machine-owned by `src/automation/scoring.py:WEIGHTS`): `MAX_CWS = Σ(W×6) = 582` · Quality-Gate patterns = {1,2,3,4,5} with weights 9+9+8+8+8 = 42, so `QG_MAX = 42×6 = 252`, `QG_THRESHOLD = 0.60×252 = 151.2` · `UNVERIFIED_MULTIPLIER = 0.70` (estimated/narrative signals contribute at 70%). *(AUD-15: earlier docs said 240/144, predating the ROCE/operating-leverage weight bump to 9; the code has always computed the value shown here.)*
**Logic:** weights descend by evidential strength of the pattern (ROCE & operating leverage highest at 9; pure price-action VCP & volume lowest at 5) — quality/durability outrank technical confirmation. patearn score is a **risk filter, not a return-ranker** (D66).

---

## 5. A / B event verdicts (rule-based — no weights, by design)
**Canonical sources:** `src/automation/insider_events.py`, `src/automation/credit_ratings.py`. These are **ordered rules, not weighted sums** — a weighting would blur a veto.
- **A (insider):** verdict = `pledge_risk` if any adverse pledge event in 90d (count-based, dominates) → else `conviction` if net principal open-market cashflow(90d) > 0 → else `caution` if < 0 → else `neutral`.
- **B (credit):** `default` → else `downgrade_veto` (any downgrade in 365d) → else `watch_negative` → else `upgrade` → else `stable`/`unrated`. Ordinal ladder D=1…AAA=20, investment-grade floor = BBB-. Notch delta = ordinal(new) − ordinal(earlier).

---

## 5b. Conviction composite, ★ flags & CPR-Structure (INTERNAL — not client-facing)

These exact thresholds/weights are deliberately kept OUT of the client glossary (AUD-20) but are recorded here as the machine-owned canon (the code constants remain the single source of truth).

**Canonical sources:** `src/web/dashboard.py` (conviction blend + ★ rule), `src/automation/cpr_signals.py` (CPR knobs + Structure weights), `src/automation/stock_rs.py` (rs_rank blend).

- **Conviction (0–100):** `0.55 × (p_score ÷ 5 × 100) + 0.45 × rs_rank`. Positioning-weighted; not backtested (a sorting heuristic, not a model). Quality (pt14) deliberately excluded pending validation.
- **★ (triple-confirm flag):** `p_score ≥ 4` **and** `rs_rank ≥ 80` **and** quality-not-failing (`dashboard.py:1718`).
- **CPR width knobs (per-TF):** Daily 1.0% · Weekly 2.5% · Monthly 5.0% (narrowness thresholds; derived on read).
- **★ Structure tier weights:** larger TF carries more weight — D 1 · W 2 · M 3. `score = base rank (R1=4…R4=1) + Σ over other TFs w_TF·(narrow? + reversal-aligned? + regime-aligned?) + confluence`. Tiers ★★★ Prime / ★★ Strong / ★ Setup. Weights tunable, nothing re-materialized.
- **rs_rank blend:** stock-vs-broad and stock-vs-sector combined 0.6 / 0.4 (`stock_rs.py:239`).

---

## 5c. Wolfe display/queue layer — REVERTED (D108, 2026-07-10) + the mandatory 2/3/4 fractal gate

**Canonical source:** `src/automation/wolfe.py` at the D96 baseline (`9d04bd9`) + the D108 gate.

- **The one live rule this section now carries — the MANDATORY 2/3/4 fractal gate (D108, Ramana
  verbatim: points 2, 3, 4 "must, minimum 2 fractals; without a fractal do not consider them"):**
  `detect_waves` rejects any candidate wave unless points 2 AND 3 AND 4 each satisfy
  `frac_degree(...) ≥ 2`. Point 1: no gate (a fractal there is the §B-A bonus). Point 5: no gate
  (§B1 entry timeliness; `find_p5` untouched). No numeric constants beyond §B1's own ladder.
- **Everything this section previously documented was removed with the D98–D102 revert** (STR/LND
  display split · structure watch + its 60-row slice · §B2 not-entry-qualified withhold · OPEN/CLOSED
  state-filtered queue membership · approaching-5 queue · progress chips · `_NEAR_EPA_PCT`). The
  history lives in PROJECT_STATE D98–D102/D108; the designs live in `docs/wolfe-NEXT-SESSION.md`
  (★ brief + gate spec) for the methodical re-apply WITH Ramana. Unused-but-harmless residue:
  `wolfe_signals` rows under `'<uni>:watch'`/`'<uni>:forming'` + the extra nullable columns +
  the `wolfe_epa_state` table (no reader references them at the baseline).

## 5d. Wolfe attention rank — REVERTED (D108, 2026-07-10)

`rank_attention`/the 60-bar half-life and the WolfeRank removal were part of the reverted D99
layer; at the `9d04bd9` baseline the /dash/wolfe list sorts by the §B quality total with the
legacy WolfeRank shown as secondary context. A recency/fractal treatment of the ranking returns
only as a Ramana-signed re-apply (PROJECT_STATE D108).

## 5e. DVPT — Delivery Value per Trade (the "Positioning" two-tier trigger)
**Canonical source:** `src/automation/signals.py` — `_WINDOWS`, `_rank_from_p_score`, `_KEY_BAND`, `_CHAR_FETCH_DAYS`. Daily `delivery_value_per_trade = Σ(delivery ₹) ÷ Σ(num_trades)`; period rollups **sum numerator and denominator** (never an average of daily ratios — value > quantity, Guardrail #5). DESCRIPTIVE-ONLY, within-stock confirmation lens, never a cross-stock ranker (D62; `docs/strategies/dvpt.md`).

**Two-tier self-referential baselines (`_WINDOWS`, calendar-day windows):**
| Window | Calendar days | Power top-N |
|---|--:|--:|
| 1m | 30 | 4 |
| 2m | 60 | 7 |
| 3m | 90 | 12 |
| 6m | 180 | 20 |
| 12m | 360 | 30 |

- **R-tier** = flat rolling DVPT average per window ("above a normal day"). **P-tier** = average DVPT of only the **top-N highest-DVPT days** in each window ("above the institutional peak days"; top-N per the table).
- **Scores:** `r_score` / `p_score` = count of the five R / P baselines today's DVPT beats (0–5). **`trigger_rank`** from `p_score`: 5→**SS** · 4→**S** · 3→**A** · 2→**B** · 1→**C** · 0→**—**.
- **D44 launch zone (`_KEY_BAND = (−1.0, 5.0)`):** the "action zone" fires when `gap_to_key` ∈ **[key−1%, key+5%]** — asymmetric (tighter below the value-weighted key price than above), re-tunes on read with no backfill.
- **D43 character** fetches `_CHAR_FETCH_DAYS = 372` calendar days (a full year of adjusted closes for the 52-week-high context); the up/down direction read discards any single-day move **> 30%** as an unadjusted corp-action artifact.

**Logic:** everything is judged against the stock's **own** history — no market-wide rupee threshold (the "no rupee-constant thresholds" rule), so a thin small-cap and a large-cap are each measured against themselves. Top-N grows with the window (4→30) so a "power day" means the same thing at every horizon: an outlier vs that window's own peak days.

**Ignition intensity ranking (`src/automation/ignition.py`) — the one absolute floor.** DVPT itself uses no rupee constant (above). The *ignition* layer that ranks today's SS/S crossers by intensity applies ONE absolute filter — `LIQ_FLOOR = Rs 25 lakh` delivered-value/day (drop count logged) — to keep un-actionable micro-junk out of the ranked list. It is a **liquidity/tradability filter applied AFTER intensity is computed** (`intensity = dvpt / mean(P-baselines)`), NOT part of the intensity definition, and is endorsed by the ledger gate study ("keep an absolute tradability requirement — you must be able to fill"). ⚠ It is a hard rupee constant and therefore *rots* with inflation / market-cap drift (against the no-rupee-constant rule for SELECTION); a queued improvement is to relativize it to a percentile / own-trailing-value gate. (Codex D1-F2, converged.)

## 5f. MEP — signed accumulation/distribution (the price-tape read)
**Canonical source:** `src/automation/mep_signals.py`. Daily score = the **within-stock z-average of four SIGNED directional terms** (+ = accumulation, − = distribution), **equal-weighted (¼ each) on z-scores** so unlike units combine honestly. DESCRIPTOR-ONLY (D62 — failed the walk-forward + Deflated-Sharpe gate; `docs/strategies/mep.md`).

**The four summed terms (equal weight):**
| Term | Formula | Reads |
|---|---|---|
| pressure | `(close − VWAP) / VWAP` | did buyers pay up intraday? |
| clv | `((close−low) − (high−close)) / (high−low)` | where in the range it closed |
| drift_22d | adjusted-close return over ~22 rows | trend direction |
| updown_vol_22d | `(up-day vol − down-day vol) / total vol`, 22 rows | effort direction |

- **Standardisation:** within-stock z over `_Z_WIN = 200` trailing rows (`_Z_MIN = 40` min; clamp `_Z_CLAMP = ±4.0` so one outlier day can't dominate). Lookbacks `_DRIFT_LB = _UPDOWN_LB = 22`. Corp-action guard `_CC_THRESH = 0.30` (a > 30% single-day move isn't a real up/down day). **Context, NOT summed:** compression (`_ATR_SHORT/_ATR_LONG = 14/60`) and `amihud_22d` (`_AMIHUD_LB = 22`).
- **PHASE — the smoothed regime with hysteresis (D65):** the daily oscillator is averaged over `_SMOOTH_WIN = 15` rows (`_SMOOTH_MIN = 5`) into 5 phases — **STRONG_DISTRIB · DISTRIB · NEUTRAL · ACCUM · STRONG_ACCUM**. Enter the **higher** phase at score `≥ _SMOOTH_HI = [−0.40, −0.10, 0.28, 0.62]`; drop to the **lower** at `< _SMOOTH_LO = [−0.62, −0.28, 0.10, 0.40]`. The LO→HI gap is the anti-flap band (a pressure oscillator ≠ a regime).

**Logic:** delivery is side-blind, so MEP reads the *price tape* for the direction the DVPT delivery lens (§5e) structurally cannot. Its only edge over DVPT is that it is signed (a distribution-warning surface); the smoothed **phase** is the headline, the daily score the granular pressure read. Never ranks.

## 5g. CCI — Concall Credibility Index (FAILED-AS-FACTOR → descriptive)
**Canonical source:** `src/automation/concall_scores.py` (weight constants) + `src/automation/cci_series.py` (PIT composition). A point-in-time management-credibility level from earnings-call promises graded against outcomes. **FALSIFIED as a factor → descriptive/veto dossier only, never ranked** (`docs/strategies/cci.md`).

**Level (per resolved-through date T):** `base = W_GA·guidance_accuracy + W_QR·quantification_rate` (or `qr` alone with no resolved track record) → `level = clamp₀₋₁₀₀(base − DETER_PEN_PER·deter_flags)`; if **unproven** (no settled promises) → `level = min(level, UNPROVEN_CEILING)`.

| Constant | Value | Logic |
|---|--:|---|
| W_GA (guidance-accuracy) | **0.65** | the resolved track record dominates |
| W_QR (quantification-rate) | 0.35 | falsifiable-numbers share is secondary |
| UNPROVEN_CEILING | 55.0 | no A/A+ tier without a *settled* promise |
| DETER_PEN_PER | 6.0 | composite penalty per recent deterministic deterioration flag |
| RECENT_PERIODS | 4 | window (periods) for "recent" deterioration |

**Logic:** measurable inputs only (D61) — track record + quantification with a hard veto path; self-testimony/tone is demoted (the 8-lens debate showed tone-scoring ranks the best-spoken frauds highest). The weights are moot for ranking: CCI is **falsified as a factor** (Spearman ≈ 0, HIGH−LOW −10%@12m inverse), so these constants drive only the descriptive per-name dossier.

## 5h. Harmonic patterns — XABCD Fibonacci ratio bands
**Canonical source:** `src/automation/harmonic_patterns.py` — `HARMONICS` (per-type acceptance bands + ideals), `_FIB_CD` (D-projection). A pattern = five swing points X-A-B-C-D whose leg ratios fall inside a type's Fibonacci bands; the PRZ (potential reversal zone) is projected while D forms. LIVE but DESCRIPTIVE, **backtest-gated** (`docs/strategies/harmonic.md`).

**Acceptance bands `(lo, hi)` + the ideal used for scoring (`HARMONICS`; AB=retrace of XA · BC=retrace of AB · CD=extension of BC · AD=retrace/ext of XA):**
| Type | AB | BC | CD | AD | ideals (AB · CD · AD) |
|---|---|---|---|---|---|
| Gartley | 0.55–0.66 | 0.382–0.886 | 1.13–1.618 | 0.74–0.83 | 0.618 · 1.27 · 0.786 |
| Bat | 0.382–0.50 | 0.382–0.886 | 1.50–2.618 | 0.85–0.92 | 0.45 · 2.0 · 0.886 |
| Butterfly | 0.74–0.83 | 0.382–0.886 | 1.50–2.24 | 1.20–1.70 | 0.786 · 1.80 · 1.27 |
| Crab | 0.382–0.618 | 0.382–0.886 | 2.0–3.80 | 1.55–1.70 | 0.50 · 3.0 · 1.618 |
| DeepCrab | 0.85–0.92 | 0.382–0.886 | 2.0–3.80 | 1.55–1.70 | 0.886 · 3.0 · 1.618 |

- **PRZ projection (`_FIB_CD`, the CD extension per type):** Gartley 1.27 · Bat 1.618 · Butterfly 1.618 · Crab 2.618 · DeepCrab 2.24.
- **Fit score** = mean closeness of the AB/CD/AD ratios to their ideals (**1.0 = bullseye, 0 = at a band edge**).

**Logic:** the bands are the standard harmonic-trading ratios encoded faithfully, the ideal the textbook centre. The score is geometry-fit only — like Wolfe (§5c), the edge is **selection, tail-carried**, not the fit number; no fundable book is claimed until the reliability backtest clears.

## 6. Maintenance rule
When any weight/anchor/threshold changes: (1) edit the **canonical code constant**; (2) update the **single** entry in this file; (3) if a UI/glossary surface shows it, have that surface **read/link** it — never hard-code a second copy. Reviewers check *this file* for "how is it calculated," not scattered code comments.
