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
| RISKADJ | `MOM6 ÷ vol_66` | — (ratio) | return per unit 3-mo vol — best Sharpe |
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

**Do not** weight by past Sharpe (selection bias), and **do not** add value/quality as a member (they are veto/filter layers, not rankers — §4, and the BLOCKING FAILURE MODELS in `docs/strategy-ledger.md`).

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

## 5c. Wolfe §B display split + structure watch (D98 — display/selection layer only)

**Canonical sources:** `src/automation/wolfe.py` (`score_split`, `_WATCH_MIN_STRUCTURE`, `watch_scan`); the §B rubric itself lives in `docs/wolfe-rules.md` §B3 and is UNCHANGED by this layer.

- **STR/LND split (display regroup, no rubric change):** `STR = p1×2 + B + H` (shape, max **11**) · `LND = C + F + G + I + D` (landing, max **13**); `STR + LND = Q`. Shown wherever the Q badge appears (walk summary, /dash/wolfe list, scan + watch tables). ⚠ **LND inverts as a trade filter** — the OOS winner profile deliberately prefers LOW D/F, so scan winners show low LND by design; the tooltips say so.
- **Structure-watch bar:** `wolfe._WATCH_MIN_STRUCTURE = 10.0` (STR ≥ 10 of 11; the TCS Jul-01 archetype is 11/11). Fresh window = the scan's `fresh` param (**15 bars** — deliberately mirrors the winner scan so the watch is its literal complement). Sort = age ASC, STR DESC — **never by Q** (Q inverts as a trade filter; a Q-sort would read as a recommendation ranking).
- **Watch membership:** CONFIRMED + p5 ≤ fresh + STR ≥ bar + **not shown on the scan** (fails the winner profile `D≤1 & p1≥2 & F≤2`, or passes it with no fib confluence — the scanner requires the zone). **One row per (sym, direction)** — the detector's fractal-degree twins of a single wedge collapse to the strongest-shape/freshest copy (a correlated-market p5 day otherwise floods the list: 140→95 on 2026-07-10). Persisted nightly by the same `--persist-scan` run under `wolfe_signals.universe='<uni>:watch'`. The page shows the freshest 30 by default with a counted "show all N" link (`?wall=1`) — an explicit slice, never a silent cap. Descriptive-only: the raw lens is §C-falsified (median −2% net/trade, tail game) — the watch never claims an edge.

---

## 5d. Wolfe attention rank (D99 — the ONE ranking system; recency never edits Q)

**Canonical source:** `src/automation/wolfe.py` (`rank_attention`, `_ATTENTION_HALF_LIFE_BARS = 60`, `freshness_tier`). Approved by Ramana 2026-07-10 ("go ahead with the 60-bar half-life default").

- **Formula:** `rank_attention = Q × 0.5^(age_bars_since_p5 / 60)` — §B quality decayed by recency. **Q itself stays PURE and timeless** (his rubric; recency is not quality) — recency enters ONLY at the ranking layer, as its own visible field (age-in-bars + tier chip on every ranked row).
- **Anchors (sanity):** TCS Q15 @ 6 bars ≈ **14.0** · Q17.33 from 2019 ≈ **0** · Q20 @ 30 bars ≈ **14.1** — fresh-strong and very-recent-decent compete; stale-strong retires to the all-time view.
- **Sorts:** ranked Wolfe surfaces default to **current-first** (rank_attention DESC); **"Q all-time"** (pure §B DESC) stays as an explicit labeled toggle (`/dash/wolfe?…&sort=q`). Both orders carry the same rows — ranks order, filters declare, nothing hides (D96/D98 guarantees untouched underneath).
- **Freshness tiers (display):** hot ≤10 bars · fresh ≤60 (one half-life) · aging ≤250 (the D96 keep-window) · archive beyond.
- **Supersedes WolfeRank** (the 6-dim 0-100 blend whose 5%-weight freshness died in 40 bars — dead weight): removed from compute and payload; upside%/R:R remain as secondary context data. One ranking system: Q = quality (§B3), rank_attention = attention/sort, winner profile = the only edge filter (§C).

---

## 6. Maintenance rule
When any weight/anchor/threshold changes: (1) edit the **canonical code constant**; (2) update the **single** entry in this file; (3) if a UI/glossary surface shows it, have that surface **read/link** it — never hard-code a second copy. Reviewers check *this file* for "how is it calculated," not scattered code comments.
