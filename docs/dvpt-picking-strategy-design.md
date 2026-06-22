# Patearn — DVPT-only picking strategy (design v0.1)

> **Status:** scoping (session 18, 2026-06-18). Nothing built yet. Marked **v0.1 — pending confirmations** (see § 11).
> **Brand:** **Patearn** (patearn.in) — *pattern + earn*. The product/brand is "Patearn" and nothing else. **DVPT, RS, and the 14-Pattern model are STRATEGIES, not brands.** "Hermes" now refers ONLY to the separately-procured Nous agent (D34), never this product.
> **Scope of THIS doc:** the DVPT strategy *alone*, vanilla — no mixing with RS or the 14-Pattern model. Those become their own single-strategy portfolios; a hybrid comes later.

---

## 0. ⚠️ STATUS — thesis empirically REVISED (2026-06-22, post sessions 25–27)

This doc was written session 18 (v0.1) on the premise in § 1: *"DVPT is a leading signal of smart-money positioning."* **Sessions 25–27's from-scratch research (D56) refuted that premise on its own terms, and a first-principles analysis (2026-06-22, Ramana's challenge) explains mechanically WHY.** § 1 is kept verbatim for history (doc-persistence rule); read it through this correction.

**Why DVPT cannot identify the accumulator (the mechanics).** DVPT = delivery value ÷ `num_trades`, where `num_trades` is the day's *total* trade count (`db.py` §`stock_signals`; period DVPT = Σdeliv-value ÷ Σtrades). A trade prints on every order match, so `num_trades` collapses **only when *both* sides of the flow are concentrated** into a few large orders. The accumulation case this strategy exists to catch — one informed buyer absorbing many fragmented retail sellers — produces *many* matches → a *high* trade count → a *low, retail-looking* DVPT. The accumulation is invisible. DVPT spikes only when the **counterparty was also concentrated** (big-to-big), which is structurally a **block/bulk transfer — already separately disclosed with client names**. Net: **DVPT measures the fragmentation of the counterparty, not the conviction of the accumulator.** Three aggravations: (a) modern informed execution (VWAP/TWAP/iceberg) *deliberately* fragments to hide impact, so DVPT selects AGAINST sophistication; (b) DVPT is **side-blind** (a high-DVPT day is equally consistent with concentrated distribution) — the D43 character gate only becomes directional by adding **price action**, i.e. *price is doing the real work*; (c) since the absolute-₹ floor was removed (2026-06-20), a thin stock's high DVPT can be **one lumpy print against a sleepy baseline**, not accumulation.

**What the data already said (D56 / `docs/explosive-move-research.md`).** Reading raw data alone, a delivery surge does NOT precede explosive moves (momentum/volatility/trend-structure lead, OOS both directions, every year 2012–26); the **"whale-among-minnows" ticket-dispersion hypothesis — literally this mechanism — was real-data REFUTED**; conclusion logged verbatim: *"no stealth institutional-accumulation footprint before +10% moves in the EOD aggregate."*

**REFRAME (the surviving role).** DVPT/delivery is demoted from *leading smart-money detector* → a **confirmation / character layer on top of price**: (1) **confirmation, not prediction** — rising delivery alongside a rising price says a move already underway is being *paid for* with held positions, not leveraged intraday churn → more likely to hold (matches D56's "sustain = the close holds"); (2) **divergence flag** — price up + delivery collapsing = hollow move; price firm + delivery/DVPT spiking = possible distribution into strength (side-blind → a *question*, not an answer); (3) **within-stock relative only** — never a cross-stock ranking input. The thing that actually decodes WHO is transacting and at what effective price lives in the **named-flow channel** (bulk/block client tape + FII/DII + F&O OI) wired in `src/automation/deals.py`, NOT in the EOD aggregate. The multi-lens accumulation/distribution decode (orthogonal channels + equations) explored 2026-06-22 should be folded in here once it firms up.

---

## 1. The thesis (why DVPT alone is worth a portfolio)
*(SUPERSEDED — see § 0. Kept verbatim for history.)*
Delivery is the footprint of *informed* buying. Big players who know something (before the news, before the financials are legible) accumulate via delivery. We can't know the fundamentals in time — but we can read the **delivery footprint** they leave. So DVPT is a *leading* signal of smart-money positioning, and a heavy, decisive delivery surge is itself a kind of surety that the stock has a higher probability of a strong up-move. We are decoding that front-running footprint.

## 2. The signal — the "ignition" event
A stock fires an **ignition** when its DVPT crosses **all** of its power-DVPT baselines (today's DVPT > every `power_dvpt_*`) — our existing "all-stars" / SS condition (`p_score = max`).

What the user sharpened beyond the existing binary SS:
- **Intensity is the ranking driver, not a yes/no.** `ignition_intensity = today_DVPT ÷ mean(power_dvpt_1m..12m)`. A 10× cross is an extreme ignition; a 1.1× cross barely qualifies. **Rank by how hard it crossed.**
- **"First-time" ignition = the reversal/origin.** The *first* all-stars event in a stock's history (since the data start / 2019) is flagged specially as the ignition origin — the highest-interest entry. Subsequent ignitions are still tracked.
- **Multi-horizon.** Evaluate ignition at **daily, weekly, monthly**. A weekly (or monthly) cross counts even when the daily doesn't (denoised). MTF alignment (D+W+M together) is the strongest. → **Hard dependency on the weekly/monthly signals foundation** (designed in `multi-timeframe-positioning-design.md`, not yet built).
- **Character gate (D43, already shipped).** Treat an ignition as "all-stars perfect" only when the accumulation character is clean (ACCUMULATION); DISTRIBUTION character disqualifies/penalises (heavy delivery ≠ buying — delivery is side-blind).

## 3. The ranking schema
Primary key = **ignition intensity** (×-multiple over the average power baseline), among all-stars crossings, modified by:
- **Breadth** — crossed *all* baselines (full SS) vs a partial cross (lower).
- **MTF confirmation** — D+W+M aligned > single-timeframe.
- **Character** — ACCUMULATION clean (full credit) vs CONSOLIDATION/DISTRIBUTION (penalty/exclude).
- **First-ignition bonus** — the origin event ranks above repeat crossings.

Output: a **1–N rank across the universe** + a **tier**. Surface the top **100–200** first (don't prematurely discard), narrowing toward a **30–40-stock portfolio**.

**Locked actionable gate (session 18 — Ramana: "we need unusually huge value and clear accumulation"):** an ignition is *actionable* (portfolio-eligible) only when ALL hold — (1) **unusually huge intensity** — the cross is Strong/Explosive (≥ ~5×, ideally ≥ 10× over the avg power baseline), not a marginal clear; (2) **unusually huge ABSOLUTE delivery value** — today's total delivery ₹ is exceptional vs the stock's own norm AND clears an investability ₹-floor, so a thin stock's high *ratio* on tiny rupees can't qualify (per-trade intensity AND absolute footprint must BOTH be huge); (3) **clear accumulation** — D43 character = ACCUMULATION in its clean form (concentrated, price firm/rising, delivery rising); borderline/NEUTRAL/CONSOLIDATION don't qualify, DISTRIBUTION excluded. Strictness is deliberate — it's what cuts ~4,000 → ~30–40. Lower-intensity/smaller-value clears stay on a **watch** list, not **act**. Exact thresholds (×-bands, ₹-floor, clean-accumulation cutoffs) tuned by the backtest.

**Gate REFINED — 2026-06-20 (Ramana ruling; supersedes criterion 2 above).** (1) **Intensity ≥ 5×** is the ACT floor (≈1 name/day, ≈25/month → a natural 30–40 portfolio feed); ≥10× yields ~0/day so it is a "monster" sub-tier, not the floor. Below 5× but still p_score=5 + clean ACCUMULATION = **WATCH**. (2) **The absolute ₹-floor is REMOVED.** An absolute floor (e.g. ₹5 cr) would systematically delete the thin-float small/mid-caps where the best accumulation gems hide — exactly the names this strategy exists to catch. Footprint significance is judged **relative to the stock's OWN trailing-average delivery value** (a genuine delivery surge vs its own norm, ~2× to start), never a market-wide rupee bar. (3) clean ACCUMULATION unchanged. (4) **Pure DVPT — no RS gate** (RS is its own separate portfolio; DVPT-only stays vanilla). **Build item surfaced:** `turnover_surge_*` is TOTAL-turnover (today ÷ own trailing avg) — a proxy; add a delivery-specific `deliv_value_self_surge = delivery_value_today ÷ own trailing-avg delivery_value` to operationalize criterion 2 exactly. These four were locked into the Nous-Hermes / PAT knowledge base the same day.

**Ranking-history table (daily tracking).** Per (symbol, trade_date): rank, tier, intensity, timeframe, status ∈ {NEW, FRESH, CONTINUING, COOLING, DROPPED}. Stored every day so we can see what newly ignited, what's persisting, and what faded — and later backtest the ranking itself.

## 4. Plain-language labels (the accessibility requirement)
The codes (SS, R/P, P1M, R1M…) are precise but cryptic. Every surfaced field gets a **readable label + a glossary**, with the code kept in parentheses for power users. Draft mapping:

| Code | Plain-language label |
|---|---|
| DVPT | Big-money ticket size (delivery value per trade) |
| power_dvpt_* | Institutional peak-day levels |
| p_score = max / SS | All-stars — crossed every institutional peak level |
| ignition (first-time SS) | First all-stars surge (ignition) |
| ignition_intensity | Surge strength (× over peak levels) |
| R-tier / P-tier | Normal-day level / Peak-day level |
| ACCUMULATION / DISTRIBUTION | Quiet buying / Selling into strength |

A glossary page/section accompanies the dashboard so a newcomer can read the output without a decoder ring.

## 5. Outcome study & backtest (absolute — NO benchmark)
DVPT can't be benchmarked (indices have no delivery), so all returns are **absolute**. For every ignition event since **2019**, forward-track the whole journey:
- **MFE** (max favourable excursion) = peak gain + when it occurred → the *best-exit / target* study.
- **MAE-from-signal** = max drawdown from the ignition price.
- **MAE-from-entry** = max drawdown from the defined entry (see § 11 C4).
- **Time-to-peak**; absolute return at 1m/3m/6m/12m/24m; **eventual fate** (current vs peak; ATH hits; full give-back).
- **Success classification** (see § 11 C5).

Then **derive what we're missing**:
- **Target** — from the MFE distribution (realistic profit objective).
- **Stop-loss** — from the MAE distribution of *winners* vs *losers* (a stop that survives the heat winners take but cuts losers).
- **Averaging zones** — drawdown levels from which winners historically recovered.
- **Pitfalls** — traits of *failed* ignitions (low intensity? distribution character? illiquid? single-block artifact? sector?).

**Rigor (non-negotiable):** include delisted names (survivorship), use only signal-time data (no look-ahead), out-of-sample / walk-forward validation (no overfitting).

## 6. Entry / exit / averaging
- **Entry** — at/near the ignition, ideally near the value-weighted key price (queued D44), with the ACCUMULATION gate.
- **Exit & stop & averaging** — *derived from § 5*, not guessed. This is the gap the user named: we have an entry edge forming; we lack a measured exit.

## 7. Champion vs challenger (the learning loop, doctrine-safe)
- **Champion** = the rule-based intensity/breadth/MTF/character ranking above.
- **Challenger** = an *offline-trained* classical ML model (gradient-boosting / logistic) predicting forward success from signal-time features (intensity, breadth, MTF alignment, character, delivery %, float-relative delivery, ticket size, …). Trained on 2019→cutoff, validated out-of-sample, **₹0 at run-time** (stored scores — no LLM in the nightly job, per doctrine). Compared head-to-head with the champion on the § 5 metrics.
- **Nous Hermes agent** = optional *offline* exploratory aid only (read a data export under the user's login); never a production dependency.

## 8. Three portfolios → hybrid
DVPT-only (this doc) · RS-only · 14-Pattern-only — each a standalone ranked portfolio so we can measure each strategy's true edge in isolation, *then* build a hybrid. Keep DVPT vanilla now.

## 9. Data plan (reachability verified — session 18)

### 9.1 Data-availability map — PROBED & CONFIRMED (session 18, 2026-06-18, run from the laptop)
| Dataset | Source | Confirmed reach | 2019 calls? |
|---|---|---|---|
| **Full bhav + delivery** | `sec_bhavdata_full_DDMMYYYY.csv` | **2020 → present** (2019 = 404) | — |
| **Delivery, pre-2020 (reconstructed)** | **`MTO_DDMMYYYY.DAT`** (delivery qty/%) ⋈ **legacy `cm*bhav.csv.zip`** (close + `num_trades` + **ISIN**) | **≥ 2005 → 2020** — both HTTP 200 for every probed year 2005–2019 | ✅ |
| **Indices** | `ind_close_all_DDMMYYYY.csv` | **~2013 → present** (2012 = 404, 2013-01 = 200) | ✅ |
| **Bulk / block deals** | `/api/historical/{bulk,block}-deals` | **API returned 503** from a plain client — needs a fuller browser cookie handshake (or the CSV report endpoint). Data exists historically (bulk since ~2005). | needs access-hardening |

**Verdict: calls from Jan 2019 are FEASIBLE with deep lookback.** Delivery is reconstructable back to **~2005** (14 yrs before the first call) via the MTO ⋈ legacy merge — so the 12-month baselines AND "first-ever all-stars" detection are well-covered. DVPT-only needs no index/benchmark, so the ~2013 index floor does NOT constrain DVPT calls (it only matters once we add the RS strategy). Earlier finding (delivery floor ~2020) applied only to the *consolidated* file — the MTO source supersedes it.

### 9.2 The probe (run first — definitive, ~5–10 min)
`scripts/probe_data_reachability.py` — reuses our header-correct `fetch_for_date` (so `has_delivery` is exact), year-by-year coarse scan + month refinement for the delivery floor; dry checks for indices; the historical API (with cookie seed) for bulk/block. Run on the VPS (Mumbai IP): `cd /opt/hermes && .venv/bin/python scripts/probe_data_reachability.py` → paste the earliest dates back to finalise the floor.

### 9.3 New table — `bulk_block_deals`
```
bulk_block_deals(id PK, deal_type['BULK'|'BLOCK'], trade_date, symbol, security_name,
                 client_name, buy_sell['BUY'|'SELL'], quantity INT, trade_price REAL,
                 deal_value REAL[=qty*price], raw_json, fetched_at,
                 UNIQUE(deal_type,trade_date,symbol,client_name,buy_sell,quantity,trade_price))
  + index(symbol, trade_date), index(trade_date)
  + bulk_block_dates(trade_date PK, row_count)  -- idempotent backfill tracker (like bhavcopy_dates)
```
New ingester `src/automation/deals.py` (session + cookie handshake; date-range backfill — fast, months at a time). Confirm the JSON field names from the probe output before finalising the parser.

### 9.4 Backfill plan (dependency-ordered; heavy steps run detached on the VPS)
1. ✅ **Probe** — DONE (§9.1). Floors confirmed.
2. **Build the MTO ⋈ legacy-bhav merge** (§9.5) so pre-2020 delivery exists; then `bhavcopy --backfill` to **~2005** (heavy — legacy zip + MTO fetch/parse per day). 2020→present keeps using `sec_bhavdata_full` (already wired).
3. **Indices** → `indexes --backfill` to ~2013 (light).
4. **Bulk/block** → harden API access (cookie handshake) or use the CSV report; build `deals.py` + table; backfill to max.
5. **Build the security/universe-integrity layer** (§13: `security_master` from legacy-bhav ISIN + EQUITY_L + symbol-change; demerger/merger flags).
6. **Recompute over the extended range** (chained `nohup`, like `full-backfill.sh`): `signals --backfill-triggers` (DVPT + D43 character + D44 key price) → `index_signals` → `stock_rs`. Then ranking-history + the backtest run from **Jan 2019**.
- **Data window ≠ call window (the correction).** Backfill **as deep as NSE serves** (≥2016 floor, deeper is better) for delivery (DVPT can't use price-only dates), indices, and bulk/block — so that a **call generated in Jan 2019 has its full lookback**: the 12-month DVPT baselines need ≥2018, and judging "first-ever all-stars" needs the stock's *complete prior history*. **Calls/analysis run from Jan 2019; the data starts years earlier.** Keep everything current nightly afterwards. See § 13 for universe integrity.

### 9.5 NEW build — pre-2020 delivery via MTO ⋈ legacy bhav (the unlock)
`bhavcopy.py` already fetches legacy `cm*bhav.csv.zip` (tier 3) but discards delivery (`deliv_qty = NULL`). Enhancement: for dates with no `sec_bhavdata_full` (pre-2020), ALSO fetch `MTO_DDMMYYYY.DAT` (`https://nsearchives.nseindia.com/archives/equities/mto/`), parse its security-wise delivery rows (symbol · series · qty traded · deliverable qty · % deliverable), and **merge** into the legacy bhav rows → populate `deliv_qty`/`deliv_per` → DVPT computable back to ~2005. **Bonus:** legacy bhav carries **ISIN** (which `sec_bhavdata_full` lacks) → feeds the `security_master` (§13) for rename-stitching. Confirm the exact MTO column layout by peeking a sample (`MTO_*.DAT` header = "Security Wise Delivery Position - Compulsory Rolling Settlement") during the build.

### 9.6 Derived-column completeness (fill EVERY column over the full range)
The backfill is NOT just raw `bhavcopy_rows` — **every derived column must be populated across the entire valid historical range; we never ship a column that's only filled going-forward.** Scope per row in the extended (2005→present) range:
- **`stock_signals`** — DVPT (`delivery_value_per_trade`, `delivery_value_today`, `total_value_today`), R-tier (`avg_dvpt_*`), P-tier (`power_dvpt_*`), zones (`avg_close_r*` / `avg_close_p*`), `r_score` / `p_score` / `trigger_rank`, near-break (`next_p_above` / `gap_to_next_p_pct`), `is_ath_dvpt` / `hot_days_avg_price` / `price_vs_hot_avg_pct`, the D43 character columns, and — when built — the D44 key-price/ticket-size/surge columns, the MTF weekly/monthly signals, and the ignition/ranking columns.
- **RS columns** (`rs_vs_broad_*`, `rs_rank`, `rs_vs_sector_*`, `primary_sector`) fill only back to the **index floor ~2013** (no benchmark exists before that) — NULL-by-design for 2005–2012, which is fine for DVPT-only (needs no benchmark).
- **Full-history recompute, NOT append-only:** `is_ath_dvpt` and the **"first-ever all-stars ignition"** flag are defined against the stock's ENTIRE history — so deepening the data to 2005 *re-defines* them for all dates, **including the already-loaded 2021–2026 rows** (a 2024 "ATH DVPT" or "first ignition" may no longer be one once 2005–2020 is present). The recompute must reprocess the whole range — later years too, re-evaluated against the deeper past — not just the new old rows. Windowed fields (rolling R/P baselines, D43 character, RS) only change at the boundary (earliest ~2021, whose 360-day lookback now reaches into 2020). One full recompute pass over 2005→present handles all of it. This is a feature: it makes ATH / first-ever detection correct.
- **Lookback warm-up:** the earliest ~1 year (2005) cannot form the 360-day baselines — those columns are NULL by nature until ~2006. Irrelevant to 2019 calls.
- **Sequencing (avoid wasteful re-runs):** build the still-pending derived layers (D44, MTF, ignition/ranking) *before* the big recompute so a single chained pass fills everything 2005→present, rather than recomputing ~7–10M rows multiple times. The recompute is a multi-hour VPS job.
- **Verification gate:** after recompute, run a per-column × per-year coverage check — assert no derived column is unexpectedly NULL within its valid range.

## 10. Brand & rename (phased — user-facing first)
- **Phase 1 (now-ish):** rename everything *visible* — dashboards, page titles, bot text, docs — Hermes → **Patearn**.
- **Deferred (deliberate, later):** internal code identifiers, the `/opt/hermes` path, systemd unit names, the git repo, DB references — high-regression, migrate carefully, discuss each complex spot.
- The 14-Pattern model historically called "patearn" is, from now, **"the 14-Pattern strategy"** (the `/pt14` command may remain) — so "Patearn" is unambiguously the brand.

## 11. Open confirmations (resolve before building § 2–3)
- **C1 — intensity metric.** `today_DVPT ÷ mean(power_dvpt_*)`, ranked descending. Is "10×" a concrete top-tier threshold or just illustrative of "very intense"? (Default: graded bands, 10× = top band.)
- **C2 — first-time flag.** Flag the first ignition as the origin, but keep tracking subsequent ignitions too. (Default: yes to both.)
- **C3 — baseline set.** We currently have 5 P-baselines (P1M/2M/3M/6M/12M); "all-stars" = crossing all 5. (You said "four or whatever our DVPTs are" — confirm 5.)
- **C4 — entry definition** for MAE/return measurement: next-day open? close of signal day? near-key-price fill? (Default: next-day open — realistic + avoids look-ahead.)
- **C5 — "winner" definition** for the success classification (e.g. MFE ≥ +25% within 6 months before MAE breaches −15%). (Default: a small grid of thresholds, reported, not one hard rule.)

## 12. Build order (dependency-aware)
1. **Data & universe foundation** (prereq for a credible backtest):
   (a) **deep backfill** — delivery/bhav to the probed floor (≥2016, more if served), indices + bulk/block to max;
   (b) **security/universe-integrity layer** (§ 13) — `security_master` (symbol↔ISIN↔company, list/delist/rename dates), symbol-change ingest, demerger/merger flags in `corporate_actions`.
2. **Weekly/monthly signals foundation** (prereq for multi-horizon ignition) — `multi-timeframe-positioning-design.md` (renumber: its D42/D43 labels predate the now-shipped D42/D43).
3. **Ignition trigger + intensity ranking + ranking-history table** (daily). Calls evaluated from **Jan 2019** with full pre-2019 lookback.
4. **Backtest / outcome analytics** (§ 5) → derive target/stop/averaging.
5. **Champion vs challenger ML** (§ 7).
6. **Phased rename** (§ 10, parallel).
(Queued **D44** value-weighted key price feeds entry; **D43** character is the gate — already shipped.)

## 13. Universe & corporate-action integrity (survivorship, renames, demergers)
The hardest part of a credible Indian-equity backtest — handle it properly or the results lie.

- **Survivorship — solved by construction (a strength).** Because we preserve every day's RAW bhav (Doctrine C), and bhav contains whatever traded that day *including now-delisted names*, the backtest universe on any date = what actually traded then. We MUST use this **point-in-time** membership, NOT today's listed set — else we silently drop the failures (delisted crashers) and inflate returns. ⇒ backfill raw bhav for ALL symbols (incl. later-delisted); never filter history to the current universe.
- **Symbol renames** break a stock's series (looks like delist + relist) → corrupts baselines + first-ever detection. Fix: a **`security_master`** keyed on the stable **ISIN** (sourced from UDIFF/legacy bhav + EQUITY_L; `sec_bhavdata_full` lacks ISIN) + ingest NSE's **symbol-change list** to stitch renamed series into one continuous entity.
- **Demergers / mergers (the Vedanta problem)** create discontinuities a split/bonus ratio CANNOT fix — value transfers to a newly-listed entity, price drops on the ex-date. Fix: extend `corporate_actions` to capture demergers/mergers/scheme-of-arrangement; **flag those ex-dates**; when a forward-return window spans one, total-return-adjust (include the spun-off entity) or annotate/exclude — so a value-transfer is never recorded as a fake DVPT loss. (Splits/bonuses already handled — D36/`adjust.py`.)
- **Clean universe (boon vs bane of more data).** Point-in-time **EQ-series + EQUITY_L allowlist (D42) + ₹-turnover liquidity** filters per date strip ETFs/illiquid/obsolete names; the ignition trigger (all-stars + intensity) is selective enough that junk won't trigger anyway. More history helps baselines + survivorship; the filters keep the noise out.
- **"First-ever all-stars" is bounded by the delivery floor** — we can only claim "first since the floor," which is why going as deep as the data allows matters.
- **New required build item (precedes the backtest):** the `security_master` + symbol-change ingest + demerger/merger flags. The backtest is not credible without it.

## 14. Documentation persistence (standing rule, session 18)
Per the user: the **full intent and detail** of these strategy discussions must be preserved across sessions and **NOT reduced to one-liners**. These design docs (this + `multi-timeframe-positioning-design.md`) are the canonical, full-detail record; PROJECT_STATE links to them. Future sessions: **enrich, don't compress** — never drop the "why" or the nuances (side-blindness of delivery; intensity-of-cross ranking; data-window ≠ call-window; survivorship-by-construction; the Vedanta demerger handling; champion/challenger).
