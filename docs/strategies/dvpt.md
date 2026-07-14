# Delivery-Volume-Price-Trend (DVPT) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **DESCRIPTIVE-ONLY** (the two-tier engine + surfaces are LIVE and compute nightly, but the original *leading smart-money picker* thesis was empirically **refuted** — DVPT is a within-stock confirmation/character lens, never a cross-stock alpha ranker). · **Governing decision(s):** D62 (the reframe) · D28/D31/D43/D44 (the live engine) · D56 (refutation) · D107 (number integrity) · D47 (deep-history data) · **Reconciled:** 2026-07-11 (S111).
> **Origin:** 🧑 RAMANA (the DVPT delivery-footprint concept, dictated) + 🏠 HOUSE implementation (the two-tier engine · D43 character · D44 zones · ignition). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for DVPT. Deep design: [dvpt-picking-strategy-design.md](../dvpt-picking-strategy-design.md) (kept rich per its §14 doc-persistence rule) + [multi-timeframe-positioning-design.md](../multi-timeframe-positioning-design.md). Numbers live in code + [metrics-glossary.md](../metrics-glossary.md) (the DVPT term defs) and [calculations-and-weights.md §5e](../calculations-and-weights.md); this page never restates a constant — it links.

**One-line definition:** DVPT (Delivery Value per Trade) = Σ(delivered value ₹) ÷ Σ(number of trades) for a period — the average ₹-clip-size of a *delivered* trade, read off NSE bhav-copy delivery data as a **side-blind** measure of *how big* the hands transacting were, **not** *which side* initiated or whether it will pay forward.

---

## 1. What it is

DVPT is our home-grown **delivery-footprint** read — the "Positioning" pillar of the product. For every (symbol, trade-date) it divides the day's delivered rupee value by the day's total trade count, giving the average size of a delivered ticket. A rising DVPT means the marginal delivered trade is getting *bigger* (larger hands changing hands); a low DVPT means fragmented, retail-sized delivery. It is computed purely in Python/SQL over the bhav-copy archive — no LLM, deterministic, ₹0 marginal cost.

Around that core number sits a **two-tier trigger system** (D28/D31): today's DVPT is scored against the stock's *own* rolling-average baselines (R-tier, "above a normal day") and its *own* peak-day baselines (P-tier, "above the institutional peak days"), producing per-day scores, a rank, a near-break pointer, orthogonal flags (ATH-DVPT, discount/at-cost/above-cost vs the hot-day price), a delivery **character** read (D43), value-weighted **institutional price zones** (D44), and an **ignition intensity** ranking (`ignition.py`). See §3.

**Crucially, DVPT is a magnitude, not a direction.** Every delivered share was simultaneously bought *and* sold, so delivery data reveals *who/how big* transacted but never which side was the aggressor. Direction only enters through the price action layered on top (D43 character). This side-blindness is the hinge of the whole honesty story in §4.

## 2. Our variation vs. the standard technique

The common Indian-market technique is **delivery-percentage analysis** — traders watch `deliv%` (deliverable qty ÷ traded qty) as a crude proxy for "conviction" or "smart-money interest." DVPT deliberately departs from that on several proprietary axes:

- **Value-per-trade, not delivery-%.** We rank on the ₹-*clip size* of delivered trades, not the % of volume that settled. `deliv%` is a ratio that says nothing about ticket size; DVPT says how *big* the average delivered trade was.
- **Value, not share count → corporate-action invariant.** DVPT is built on delivered *rupees* (`deliv_qty × price`), which is split/bonus-invariant (guardrail #5), so it needs no share-count adjustment across corporate actions (D107 keeps the *price zones* on one adjusted basis, but DVPT itself stays raw qty × price).
- **Two-tier, self-referential baselines.** Intensity is judged against the stock's **own** history — R-tier rolling averages *and* P-tier "power" baselines (the average of only the top-N highest-DVPT days in each window). Nothing is a market-wide rupee threshold (Ramana's standing "no rupee-constant thresholds" rule); a thin small-cap and a large-cap are each measured against themselves.
- **A direction overlay for a side-blind measure (D43).** Because delivery is side-blind, we fuse three independent axes — WHO (trade-count breadth + delivery-₹ trend), WHICH-WAY (value-weighted up/down skew + **price** drift), CONTEXT (distance from 52-week high + persistence) — into an ACCUMULATION / DISTRIBUTION / CONSOLIDATION / NEUTRAL character label. Price is the only real direction-revealer.
- **Institutional price zones + value-weighted key price (D31/D44).** For every baseline we also store where price actually transacted on those peak days, and a delivered-value-weighted "key price" so the biggest day dominates the cost line.
- **Ignition / first-all-stars concept.** The "×power" intensity of a full P-tier cross, with the *first-ever* all-stars event flagged as the origin — a browsable ranking primitive (`ignition.py`).

## 3. How it works (methodology)

**Core.** Period DVPT = Σ(delivery value) ÷ Σ(trades) — **never an average of daily ratios** (guardrail: value > quantity; period rollups sum numerator and denominator). Daily `delivery_value_per_trade` is stored per row.

**Two-tier baselines (D28/D31)** — each over calendar-day windows, with a companion average close price:
- **R-tier (soft bars)** `avg_dvpt_1m…12m` — the flat rolling DVPT average ("above a normal day").
- **P-tier (hard bars)** `power_dvpt_1m…12m` — the average DVPT of only the **top-N** highest-DVPT days in each window ("above the institutional peak days").
- **Scores:** `r_score` / `p_score` (0–5) = how many R / P baselines today's DVPT beats. `trigger_rank` = SS(5)/S(4)/A(3)/B(2)/C(1)/— from `p_score`.
- **Near-break pointer:** `next_p_above` + `gap_to_next_p_pct` — the closest P-wall above today, the "action zone" when a stock is within a small gap of it with `r_score` high.
- **Orthogonal flags:** ⚡ ATH-DVPT (today > full-history max), 🟢 discount / 🟡 at-cost / 🔴 above-cost vs the hot-day average price.

**Character (D43)** — the derived `accum_character` label from the three axes above (numerics stored; label re-tunable via `--relabel-character`).

**Institutional price zones + key price (D31/D44)** — `avg_close_r*/p*` (where price transacted on the baseline days) and `key_price_p*` (delivered-value-weighted, so the biggest day dominates), plus `gap_to_key_p*` and an activity `turnover_surge_*` filter. D107 pins every zone to one per-date split/bonus-adjusted basis.

**Ignition intensity (`ignition.py`)** — among today's all-stars crossers, rank by **×power** = today's DVPT ÷ the average of its own peak baselines, modified by breadth, character, and a first-ignition (origin) bonus. **Act vs Watch, never discard**; equity-only, survivorship-correct via the `security_master` spine. Daily-only today (the multi-horizon D/W/M version is blocked on the MTF foundation — §9).

Exact constants (top-N per window, band cutoffs, the SS…C ladder, the D43 axis weights, the D44 `_KEY_BAND`) live in [`src/automation/signals.py`](../../src/automation/signals.py), [`src/automation/ignition.py`](../../src/automation/ignition.py), and the [metrics-glossary.md](../metrics-glossary.md) "Positioning — DVPT" and "Ignition" sections — not restated here.

## 4. Status, validation & honesty fence

**The engine is LIVE; the original thesis is REFUTED. DVPT never ranks stocks for alpha — it is a within-stock confirmation/character/divergence lens on price.** This is a binding honesty fence, not a hedge.

The v0.1 design ([dvpt-picking-strategy-design.md](../dvpt-picking-strategy-design.md) §1, kept verbatim for history) premised DVPT as a **leading** smart-money detector that could drive a ranked 30–40-stock picking portfolio. Two independent lines of evidence refuted that premise:

- **The mechanics (D62, 2026-06-22).** DVPT = delivery value ÷ *total* `num_trades`. A trade prints on every order match, so `num_trades` collapses (→ high DVPT) **only when both sides are concentrated** — i.e. a block/bulk transfer that is *already disclosed with client names*. The case the strategy existed to catch — one informed buyer absorbing fragmented retail supply — generates *many* matches → a high trade count → a *low, retail-looking* DVPT. So **DVPT reads the counterparty's fragmentation, not the accumulator's conviction**; modern execution (VWAP/iceberg) fragments on purpose, so DVPT actively selects *against* sophistication; and it is side-blind (a high-DVPT day is equally consistent with distribution).
- **The data (D56, "counter-DVPT").** Reading the raw archive alone, a *rising delivery footprint is NOT what precedes explosive moves* — the winning rules prefer `deliv_qty_trend ≤ ~1.5` (no surge) and *lower* delivery-%. Logged verbatim: *"no stealth institutional-accumulation footprint before +10% moves in the EOD aggregate"*; the whale-among-minnows ticket-dispersion hypothesis was real-data **refuted**, OOS both directions, every year 2012–26.

The **accumulation-footprint calibration** ([strategy-ledger.md](../strategy-ledger.md#L466), 2026-07-05b) nailed it quantitatively: against disclosed insider/SAST accumulation windows, `f_deliv_per` — DVPT's core — moved δ≈**+0.072 / +0.083** (fail), i.e. *"DVPT's core barely moves during real accumulation."* The delivery **level** is mostly noise; delivered **value** + **clip size** (`f_trade_size` δ+0.329/+0.250, the one gate-passer) carry what little signature exists. This is coherent with the price-tape sibling MEP's alpha failure ([mep.md](mep.md); DSR 0.45→0.36).

**Doctrine (state it plainly):** *price strength is the only gross forward-return engine; delivery/accumulation reads are context/confirmation layers, never rankers or fundable alpha* ([strategy-ledger.md](../strategy-ledger.md) "BLOCKING FAILURE MODELS" corollary; memory `failure-models-ledger`). Accordingly the surviving DVPT role is (1) **confirmation** — rising delivery alongside a rising price = a move being *paid for* with held stock; (2) **divergence flag** — price up + delivery collapsing = hollow; (3) **within-stock relative only** — never a cross-stock ranking input. The "who is transacting" decode moves to the named-flow channel (bulk/block + FII/DII + F&O OI), not the EOD aggregate.

**Number-integrity (D107, S104):** the last raw-close math in the signal path is gone — D31 zones, hot-day averaged closes, and D44 key-price weights are split/bonus-adjusted to the computing date's basis; there is ONE shared `_hot_days_core`; the >30% close-jump fallback rescales history only when the authoritative tape agrees. Golden regression: `tests/test_signals_adjusted.py`.

## 5. Where it lives (code · routes · DB · timers)

- **Compute:** [`src/automation/signals.py`](../../src/automation/signals.py) → `stock_signals` (the ~2.35M-row hot table; PK symbol,trade_date). Ignition picker: [`src/automation/ignition.py`](../../src/automation/ignition.py) (+ `ignition_rankv2.py`) → `ignition_ranking` + `ranking_history`. Live sweet-spot screen (accumulation × PIT quality): [`src/automation/accum_screen.py`](../../src/automation/accum_screen.py) → `research.db.accum_screen`.
- **Schema:** `stock_signals` CREATE lives in [`src/core/db.py`](../../src/core/db.py) `SCHEMA_BASE`.
- **Web routes:** `/dash/stocks` (the DVPT-only screener + filter pills), `/dash/screener` (DVPT column-group *and* the MEP group), `/dash/stock` "Positioning · DVPT" tab (inertia / character / zones / key-price), `/dash/index` intra-index DVPT constituent board, `/dash/ratio` constituents (DVPT trigger + RS), plus the Ignition surface. Rendered from `src/web/dashboard.py` + `src/web/cockpit.py`.
- **Telegram:** `/dvpt TICKER`, `/scan [N]`, `/triggers [ss|near]`, `/flow` (see PROJECT_STATE "Telegram bot commands").
- **Timers:** nightly `hermes-bhavcopy.timer` (14:00 UTC) → the `hermes-bhavcopy.service.d/10-signals.conf` chain runs `signals` first; ignition/accum-screen run downstream. Deep backfill/recompute: `scripts/full-backfill.sh`.

## 6. Data & provenance

- **Primary source (guardrail #8-clean).** NSE bhav copy: `sec_bhavdata_full_DDMMYYYY.csv` (delivery, 2020→present) and, pre-2020, the **MTO ⋈ legacy `cm*bhav.csv.zip`** merge (D47) that reconstructs delivery back to **~2005** (and carries ISIN for the `security_master`). NSE is authentic/primary — no vendor, no Screener in the DVPT core.
- **EQ-only, T2T excluded.** Every delivery measure reads the EQ series only; names under trade-to-trade surveillance (BE/BZ — delivery is 100% by rule, so it carries no information) show no delivery signals — excluded, not polluted.
- **Survivorship by construction.** The backtest/ignition universe on any date is the raw bhav membership *of that date* (delisted names included), gated through `security_master` (renames stitched on ISIN; demergers/mergers flagged). Point-in-time, never today's listed set.
- **⚠ Screener touchpoint (disclose):** the `accum_screen` sweet-spot overlay pulls the point-in-time **patearn fundamental tier** via `fundamentals_asof` → `research.db.fundamentals_history`, which is **Screener-derived**. That is the one non-primary dependency in DVPT's orbit; the standing remediation is the **Screener→BSE/NSE XBRL migration** (guardrail #8). DVPT's own delivery signal has no Screener dependency.

## 7. Terminology canon

*This section is the anti-drift anchor. DVPT vs MEP vs DDPK is the project's most-confused triple.*

- **Canonical name:** **DVPT** — *Delivery Value per Trade*. Product-facing pillar name: **"Positioning."**
- **Accepted aliases:** "delivery footprint," "institutional delivery read," "the Positioning signal."
- **DEPRECATED — stop using:**
  - **DDPK** — Ramana's personal shorthand for *the DVPT strategy* (the built delivery/"Positioning" picking engine). It appears **only** in the MEP design docs as informal shorthand ("DDPK = the DVPT strategy") and is **not a code identifier**. Say **DVPT**, not DDPK.
  - **"DBP"** — a one-off mis-transcription of DVPT (S33). Not a thing.
- **Disambiguation vs the sibling ([mep.md](mep.md)):**
  - **DVPT** = a **side-blind magnitude** off **delivery** data (delivery value per trade). Tells you *how big* the hands were, not which side.
  - **MEP** = a **signed** accumulation(+)/distribution(−) score off the **price tape** (OHLC + VWAP + volume) — *not* delivery-per-trade. MEP's only edge over DVPT is that it is signed, so it can power a distribution-warning surface DVPT structurally cannot.
  - They are **different strategies** — different modules (`signals.py` vs `mep_signals.py`), different tables (`stock_signals` vs `mep_signals`), different surfaces. Both are **descriptive/descriptor-only; neither ranks stocks for alpha.**
  - **The word "accumulation" is overloaded.** In DVPT-land it means the **D43 character label** (delivery character). In MEP-land it means the **signed positive score**. Pat's natural-language "accumulation" flow deliberately routes to **DVPT-delivery** (not MEP); the "distribution" side is MEP's. Keep the two senses explicit whenever both are on a screen.

## 8. Decision & session history

Terse, chronological (full text in [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log / § Session log):

- **D17 / S≤14** — `/flow` surfaces DVPT alongside `/score`; DVPT formula fixed = (deliv_qty × close) / no_of_trades.
- **D26 (S14)** — first layered DVPT trigger (single-ratio scan replacement). *Superseded.*
- **D28 (S15)** — **two-tier** R-tier + P-tier system; pure-count `p_score`/`r_score`, SS…C rank, near-break pointer. The canonical engine. (§E of PROJECT_STATE.)
- **D31 (S17/18)** — calendar-day windows + top-N power baselines + companion `avg_close_*` price zones.
- **D41 (S17)** — plain-language labels + Strategies hub + weekly/monthly DVPT rollup (on-read).
- **D43 (S18)** — accumulation/distribution **character** (three axes; price = the direction-revealer).
- **D44 (S18)** — value-weighted **key price** + asymmetric multi-horizon entry gaps + activity surge.
- **D47 (S18)** — deep-history data foundation: pre-2020 delivery via MTO ⋈ legacy bhav → DVPT to ~2005 (*in progress*).
- **D48/D49 (S18)** — dashboard enrichment (×power intensity visible) + index one-stop view (constituents get RS, not just DVPT).
- **D56 (S25–27, 2026-06-20)** — explosive-move reverse-engineering: **counter-DVPT** — a delivery surge does *not* precede moves; whale-among-minnows refuted OOS.
- **D62 (2026-06-22)** — **the reframe**: DVPT = a counterparty-fragmentation gauge, side-blind → demoted from leading picker to **confirmation/character layer**. (S32 reconciled the docs.)
- **Footprint calibration (2026-07-05b)** — `deliv_per` δ≈+0.07 during real accumulation → "barely moves"; delivered value + clip size carry the signature; no detector ships.
- **D107 (S104, 2026-07-10)** — number-integrity batch: one adjusted basis for zones, one hot-day core, tape-corroborated >30% fallback (+ golden test).

## 9. Open items / frozen work

- **FROZEN / abandoned-as-alpha — the DVPT *picking-strategy program*.** The full arc designed in [dvpt-picking-strategy-design.md](../dvpt-picking-strategy-design.md) §2–7 (ignition → a ranked 30–40-stock **portfolio**, absolute full-journey backtest, champion-vs-challenger ML) is **not a live product and must not be resurrected as a picker** — its premise was refuted (D56/D62) before it shipped. The surviving artifacts are **descriptive**: the `ignition_ranking` browsable intensity ranking (Act/Watch/Avoid, never discard) and the two-tier surfaces. Any re-attempt must first beat the recorded refutation numbers under the no-leak harness (memory `failure-models-ledger`).
- **IN PROGRESS (verify VPS state before continuing) — D47 deep history.** Backfill delivery/bhav to ~2005 + full-history recompute (`is_ath_dvpt` / first-ever-ignition are whole-history-defined) + the `security_master` universe-integrity layer (survivorship / renames / demergers, design §13). Kickstart-pick-verify this before redoing it.
- **DEPENDENCY — MTF weekly/monthly foundation.** Multi-horizon (D+W+M) ignition is blocked on the materialised weekly/monthly signal engine ([multi-timeframe-positioning-design.md](../multi-timeframe-positioning-design.md)); the `ignition_ranking.timeframe` column already reserves the slot. Weekly/monthly *rollup* (D41) shipped; materialised MTF signals did not.

## 10. Sources of truth

- Deep design: [dvpt-picking-strategy-design.md](../dvpt-picking-strategy-design.md) (§0 = the reframe; §1 = the superseded original thesis; §13 = universe integrity; §14 = doc-persistence rule) · [multi-timeframe-positioning-design.md](../multi-timeframe-positioning-design.md).
- Falsification & benchmarks: [strategy-ledger.md](../strategy-ledger.md) — the BLOCKING FAILURE MODELS table, the 2026-07-05b footprint study, Tier-3 lenses row.
- Metric definitions / constants: [metrics-glossary.md](../metrics-glossary.md) ("Positioning — DVPT" + "Ignition") · [calculations-and-weights.md §5e](../calculations-and-weights.md) (the DVPT windows + trigger ladder + key-band).
- Refutation research: [explosive-move-research.md](../explosive-move-research.md) (D56 / Launchpad / counter-DVPT).
- Code: [`src/automation/signals.py`](../../src/automation/signals.py) · [`src/automation/ignition.py`](../../src/automation/ignition.py) · [`src/automation/accum_screen.py`](../../src/automation/accum_screen.py) · [`src/core/db.py`](../../src/core/db.py).
- Sibling reference: [mep.md](mep.md).
- PROJECT_STATE sections: § "E. Two-tier DVPT trigger system"; Decisions D62 / D56 / D47 / D107 / D28 / D31 / D43 / D44; the DVPT session-log entries.
- Memory: `failure-models-ledger`, `predictive-attributes-finding` (momentum = the only surviving factor, and it's beta not skill), `dataset-roadmap-c-a-b`, `data-first-light-ui`.

## Maintenance

When a future session changes DVPT — the two-tier math, the character axes, the key-price zones, the ignition ranking, or the data window — update **this doc in the same commit** as the code, and mirror the change into `metrics-glossary.md` / `calculations-and-weights.md` (constants) and `PROJECT_STATE.md` (§E / Decision log). Keep the §4 honesty fence and the §7 terminology canon intact: DVPT stays a descriptive, within-stock confirmation lens — if any session proposes reviving it as a cross-stock alpha ranker, that is blocked until it beats the D56/2026-07-05b numbers net of cost. Do not let "DDPK" or "accumulation" drift back into ambiguous use; keep this page and [mep.md](mep.md) in sync.
