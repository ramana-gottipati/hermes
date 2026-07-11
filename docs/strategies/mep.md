# MEP — Signed Accumulation/Distribution — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **DESCRIPTOR-ONLY** (built, deployed, computing nightly across every stock surface — but its predictive/ranking role **failed** a walk-forward + Deflated-Sharpe gate, so it characterises/confirms and **never ranks, sizes, or sorts-by-default**). · **Governing decision(s):** D62 (descriptor-only doctrine, joint with the DVPT reframe) · D65 (headlined as a smoothed hysteresis PHASE) · D61 (rank on measurable inputs only). · **Reconciled:** 2026-07-11 (S111).
> **Charter:** the single canonical definition + current-state reference for MEP. Deep design + per-step build log + the multi-lens decode: [mep-strategy-design.md](../mep-strategy-design.md) (§1, §8 = the DSR fail, §9 = the PHASE, §10 = the framework); run-book: [mep-NEXT-SESSION.md](../mep-NEXT-SESSION.md). Numbers live in code + [metrics-glossary.md](../metrics-glossary.md) ("MEP" section) and [calculations-and-weights.md §5f](../calculations-and-weights.md); this page never restates a constant — it links.

**One-line definition:** MEP = the **signed** Net Accumulation Pressure — a within-stock, side-aware composite of price-tape channels (OHLC + VWAP + volume, **not** delivery-per-trade) where **positive = accumulation, negative = distribution** — read as a character/confirmation lens, never as a stock picker.

---

## 1. What it is

MEP answers the question DVPT structurally cannot: *is this name being **bought** or **sold**?* Where [DVPT](dvpt.md) is a **side-blind magnitude** (a big delivered ticket is equally consistent with accumulation or distribution), MEP is **signed** — it separates buying from selling. That single property is its entire reason to exist beside DVPT, and it is why MEP can drive a **distribution-warning** surface DVPT cannot.

For every (symbol, trade-date) MEP computes a small set of **signed directional terms** off the price tape, standardises each against the **stock's own** trailing distribution (a z-score, so a thin name's lumpy day cannot masquerade as a signal), and blends them into a signed `mep_score` (+ = accumulation, − = distribution). Because three of the four summed terms are essentially *today's bar*, the raw daily score whips around; the **headline** everywhere is therefore the **smoothed, hysteresis-banded PHASE** (D65, §3) — the accumulation → consolidation → distribution *regime*, with the daily score kept underneath (data-first).

MEP is the **price-tape half** of a larger "Net Accumulation Pressure (NAP)" framework whose three channels rise in information content: **bar/tape** (MEP lives here), **dynamics** (persistence/compression — the validated Launchpad research), and **identity** (named flows / holdings Δ / F&O OI — the only channel that names the strong hand). See §10 of the design doc.

## 2. Our variation vs. the standard technique

The textbook accumulation/distribution tools are **Wyckoff phase reading**, the **Chaikin A/D line**, **OBV**, and **anchored-VWAP** pressure. MEP departs from all of them on these proprietary axes:

- **Within-stock standardisation.** Every term is a z-score against the stock's *own* trailing window, not an absolute or market-relative level — so accumulation in a ₹200 small-cap and a ₹3,000 large-cap are directly comparable, and no market-wide constant is ever used (Ramana's "no rupee-constant thresholds" rule).
- **A signed *composite*, not one line.** MEP sums several orthogonal signed channels (pressure, close-location, drift, up/down-volume skew) rather than relying on a single indicator, with two more (compression, Amihud) carried as **context** (shown, not summed — they modulate confidence, not direction).
- **A regime PHASE, not a daily oscillator (D65).** The signature engineering move: a rolling-mean + **hysteresis ladder** (asymmetric enter/exit deadbands) turns a state that flipped ~3 days in 4 into a phase that *holds* — an 8.5× reduction in transitions. Standard A/D lines have no such anti-chatter regime layer.
- **Descriptor-by-design discipline.** MEP is explicitly *not* a reskin of DVPT and is gated so it never ranks/sizes until it clears a Deflated-Sharpe test (it did not — §4). The honesty gate is part of the design, not an afterthought.

## 3. How it works (methodology)

**The daily signed score.** `mep_score` = the within-stock z-average of four **summed** signed terms — `pressure` (close vs VWAP), `clv` (close-location in the day's range), `drift_22d` (adjusted-close trend), `updown_vol_22d` (up-day vs down-day volume skew) — each z-scored over the stock's trailing window and clamped. Two **context** terms — `compression` (short/long ATR ratio, the coiled spring) and `amihud_22d` (illiquidity / effort-vs-result) — are **stored and shown but not summed**. The daily score bands into `mep_state` (STRONG_ACCUM / ACCUM / NEUTRAL / DISTRIB / STRONG_DISTRIB).

**The headline PHASE (D65).** `mep_score_smooth` = rolling mean of the daily score over ~15 trading rows; `mep_state_smooth` = that smoothed score run through a **hysteresis ladder** (each boundary has an asymmetric enter-higher / drop-lower pair with a deadband, so a score hovering near a threshold does not flip-flop). The smoothed phase is the headline on every surface; the daily state sits underneath.

**Compute paths** — all in [`src/automation/mep_signals.py`](../../src/automation/mep_signals.py): `_smooth_chain` (O(n) sliding window for `--backfill` / `--resmooth`), `_smooth_date` (nightly incremental, auto-called by `compute_for_date` — no systemd change), verified backfill ≡ incremental to float epsilon.

Exact constants — the term list and z-window, the daily bands, the 15-row window, the four boundary deadbands — live in the module (`_Z_WIN`, `_STATE`, `_SMOOTH_WIN`, `_SMOOTH_HI/_LO`) and in [metrics-glossary.md](../metrics-glossary.md) "MEP" + [mep-strategy-design.md](../mep-strategy-design.md) §9. **Re-tuning:** change the knob, then `python -m src.automation.mep_signals --resmooth` (raw terms untouched). Not restated here.

> **⚠ Reconcile (term list).** The design doc §1 sketches an aspirational `x1…x5` superset (Pressure · Amihud/Effort · Permanence-autocorr · Variance-Ratio persistence · Compression). **What actually shipped** (and is canonical) is the four summed terms above (`pressure`/`clv`/`drift_22d`/`updown_vol_22d`) with compression + Amihud as *context*, per the module docstring and design §10.2 / the NEXT-SESSION "Key facts." Trust the **code** for the summed set; §1's x-list is the original design intent, not the implementation.

## 4. Status, validation & honesty fence

**MEP is DESCRIPTOR-ONLY. It characterises and confirms; it never ranks, picks, or sizes.** This is a binding fence — the project keeps a falsified-approaches ledger and misrepresenting MEP's status is a blocking error.

Any predictive/ranking/position-sizing role was **gated** on a purged walk-forward + **Deflated-Sharpe** test, **which FAILED** (2026-06-22, [mep-strategy-design.md](../mep-strategy-design.md) §8):

| Config | OOS Sharpe | DSR | CAGR |
|---|---|---|---|
| Baseline panel | 0.76 | 0.45 | 23.0% |
| + MEP price-tape features | **0.68** | **0.36** | 18.7% |
| (Nifty 500 benchmark) | 0.86 | — | — |

The three price features **lowered** risk-adjusted performance and never cleared the Nifty-500 line (0.86), let alone the DSR ≥ 0.95 bar. The poison is `close_vs_vwap` — the in-sample #1-importance feature and the out-of-sample destroyer. The [strategy-ledger.md](../strategy-ledger.md) records it in the BLOCKING FAILURE MODELS table: *"MEP-accumulation as alpha — DSR 0.45→0.36 when added — Descriptor-only; adds nothing. **Do not re-test as alpha.**"*

**The killer line (keep it):** *the feature that best **describes** today's accumulation is exactly the one that fails to **predict** tomorrow* — which is precisely why MEP is a descriptor, and why the smoothed PHASE (D65), however clean, is still a descriptor. Corroborating evidence: the 2026-07-05b footprint study found `deliv_per` barely elevates during genuine accumulation (δ≈+0.07), coherent with this failure — the delivery/price *level* is mostly noise.

**Doctrine (state it plainly):** *price strength is the only gross forward-return engine; accumulation/delivery reads are context/confirmation layers, never rankers or fundable alpha* (ledger corollary; memory `failure-models-ledger`). Real predictive alpha, if it exists, must come from the **identity channel** (named flows / holdings Δ / F&O OI) + fundamentals/concall — each through its **own** DSR gate — never from the tape. D61 reinforces: MEP's interpretive read is *information*, shown beside a verdict, never a ranking input.

## 5. Where it lives (code · routes · DB · timers)

- **Compute:** [`src/automation/mep_signals.py`](../../src/automation/mep_signals.py) (pure-stdlib sibling of `signals.py`) → **its own** `mep_signals` table (PK symbol,trade-date — the hot `stock_signals` table is left untouched). Full history backfilled: ~7.56M rows, 4,138 symbols, 2004→2026.
- **Chart overlay:** [`src/web/mep_overlay.py`](../../src/web/mep_overlay.py) → `GET /dash/mep/overlay` — contiguous smoothed-phase bands that tint the price chart green (accumulation) / red (distribution); opt-in chip.
- **Dedicated screen:** `cockpit.render_mep` + `GET /dash/mep` — the both-sides screen (top accumulators **and** distributors, 5-state count strip, raw terms beside the verdict, accum/distrib filter). Instruments `_mv_adbar` (bipolar bar) + `_mep_pill` in `cockpit.py`; accent **`#db61a2`** (pink).
- **Other surfaces:** `/dash/screener` `accumulation · mep` column-group; `/dash/stock` "Accumulation · MEP" tab + dossier (DVPT shown as a confirmation sub-row per D62); `/dash/index` intra-index MEP board (both sides); Conviction **display-only** column (not a ranking input); Pat `mep` / `mep_state` glossary terms.
- **Identity channel (F&O OI):** [`src/automation/fno_oi.py`](../../src/automation/fno_oi.py) → `fno_oi_signals` (the price×ΔOI quadrant + PCR), nightly `30-fnooi.conf`, surfaced descriptor-only on the MEP dossier.
- **Schema:** `mep_signals` canonical CREATE in [`src/core/db.py`](../../src/core/db.py) `SCHEMA_BASE` (+ self-migrating `ensure_table()`).
- **Timers:** nightly in the `hermes-bhavcopy.service.d/10-signals.conf` chain, right **after** `signals` (both read the fresh bhav). Backfill/resmooth: `python -m src.automation.mep_signals --backfill | --resmooth`.

## 6. Data & provenance

- **Primary source, no delivery, no Screener.** MEP reads `open/high/low/close/prev_close/avg_price[VWAP]/volume/num_trades/value` from the NSE bhav copy (`bhavcopy_rows`) — authentic/primary (guardrail #8), and deliberately **no `deliv_*`** (it is explicitly *not* DVPT). Unlike DVPT's `accum_screen` overlay, MEP's core has **no Screener/fundamentals dependency** — it is clean of the copyright-remediation debt.
- **Within-stock history required.** The z-scores need each stock's own trailing distribution, so MEP is full-history-recomputed (same doctrine as DVPT's ATH/first-ever). The smoothed phase reads only *trailing stored* daily scores → no look-ahead.
- **F&O OI identity feed:** the UDiFF F&O bhavcopy (same NSE host as the cash bhav) → stock-futures OI aggregated per underlying; primary-source. Pre-UDiFF (>2024) legacy backfill is a future 2nd parser (§9).

## 7. Terminology canon

*This section is the anti-drift anchor. DVPT vs MEP vs DDPK is the project's most-confused triple.*

- **Canonical name:** **MEP** — the **signed accumulation/distribution** measure (a.k.a. the signed **Net Accumulation Pressure**, of which MEP is the price-tape half). Product-facing label: **"Accum/Distrib."**
- **Accepted aliases:** "signed accumulation," "the signed accum/distrib score," "NAP (price-tape half)."
- **DEPRECATED / do-not-confuse:**
  - **DDPK** is Ramana's shorthand for **DVPT** (the delivery/"Positioning" engine) — **not** MEP, and not a code identifier. Never call MEP "DDPK." (The original MEP design docs used "DDPK = DVPT, MEP = the new signed strategy" as provisional shorthand — that mapping is the source of the drift this canon fixes.)
- **Disambiguation vs the sibling ([dvpt.md](dvpt.md)):**
  - **MEP** = **signed**, from the **price tape** (OHLC + VWAP + volume). Positive = accumulation, negative = distribution. Can show a distribution warning.
  - **DVPT** = **side-blind magnitude**, from **delivery** data (delivery value per trade). Tells you *how big* transacted, not which side.
  - **Different strategies** — `mep_signals.py`/`mep_signals` vs `signals.py`/`stock_signals`; `/dash/mep` vs `/dash/stocks`; accent `#db61a2` vs the DVPT/Positioning blue. **Both are descriptor/descriptive-only; neither ranks stocks for alpha.**
  - **The word "accumulation" is overloaded.** MEP-signed vs DVPT's D43 delivery-**character** are two different senses. By deliberate product decision, Pat's NL "accumulation" flow routes to **DVPT-delivery**; MEP owns the **distribution** side (its signed edge). Keep both senses explicit on any shared screen.

## 8. Decision & session history

Terse, chronological (full text in [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log / § Session log; run-book [mep-NEXT-SESSION.md](../mep-NEXT-SESSION.md)):

- **D62 (2026-06-22)** — the joint reframe that demoted the tape reads to confirmation/character; MEP is born explicitly signed-but-descriptor.
- **Rollout (S34, 2026-06-22)** — 5 steps built + deployed + verified: compute module + `mep_signals` table (7.56M-row full backfill) · home pillar + Net-accumulation / Distribution-watch boards · screener `g-mep` group · stock-page MEP tab + dossier · intra-index board + conviction display column + Pat glossary · dedicated both-sides `/dash/mep`.
- **DSR gate (2026-06-22)** — walk-forward + Deflated-Sharpe **FAIL** (0.45→0.36); predictive/ranking promotion **ruled out**. MEP locked descriptor-only.
- **D65 (S35, 2026-06-22)** — the daily whipsaw fix: headline a smoothed, hysteresis-banded **PHASE** (`mep_score_smooth`/`mep_state_smooth`, 15-row mean); 48.8 → 5.8 transitions/70 (8.5×). Still descriptor-only.
- **F&O OI identity feed (2026-06-23)** — `fno_oi.py` + `fno_oi_signals` (price×ΔOI quadrant + PCR), the missing identity channel, surfaced descriptor-only on the dossier.
- **Footprint calibration (2026-07-05b)** — `deliv_per` barely moves during real accumulation → coherent with MEP's alpha failure; MEP stays descriptive; failure-models row stands.

## 9. Open items / frozen work

- **RULED OUT (do not re-open) — MEP as a predictor/ranker.** The DSR gate failed; the ledger says "do not re-test as alpha." Any future attempt is blocked until it beats DSR 0.36 net of cost under the same no-leak harness (memory `failure-models-ledger`).
- **Ramana's call (product decision, not a guess) — Pat MEP routing.** Should "accumulation" mean DVPT-delivery or MEP-signed? Standing lean: keep "accumulation" → DVPT-delivery; add "distribution / being distributed" → MEP-signed. Blocked historically on parallel Pat-file edits — verify tree state first.
- **Future (identity-NAP) — the only channel that could ever name the strong hand.** Fold holdings-Δ (FII/DII/promoter QoQ) + the F&O OI quadrant into a future identity-NAP, each through its **own** DSR gate before any predictive claim. Not wired for holdings; F&O OI wired descriptor-only. An F&O column/board on `/dash/mep` + pre-UDiFF legacy OI backfill remain to-do.

## 10. Sources of truth

- Deep design + build log: [mep-strategy-design.md](../mep-strategy-design.md) (§1 = the signal; §8 = the DSR fail; §9 = the PHASE + calibration; §10 = the multi-lens NAP decode) · run-book [mep-NEXT-SESSION.md](../mep-NEXT-SESSION.md).
- Falsification & benchmarks: [strategy-ledger.md](../strategy-ledger.md) — BLOCKING FAILURE MODELS ("MEP-accumulation as alpha"), Tier-3 lenses row, the 2026-07-05b footprint study, the "proprietary-alpha feasibility" section.
- Metric definitions / constants: [metrics-glossary.md](../metrics-glossary.md) ("MEP — signed accumulation / distribution") · [calculations-and-weights.md §5f](../calculations-and-weights.md) (the four z-terms + phase hysteresis).
- Code: [`src/automation/mep_signals.py`](../../src/automation/mep_signals.py) · [`src/web/mep_overlay.py`](../../src/web/mep_overlay.py) · [`src/automation/fno_oi.py`](../../src/automation/fno_oi.py) · [`src/core/db.py`](../../src/core/db.py).
- Sibling reference: [dvpt.md](dvpt.md).
- PROJECT_STATE sections: Decisions D62 / D65 / D61; the Session 34 / Session 35 log entries.
- Memory: `mep-strategy-built-deployed`, `failure-models-ledger`, `data-first-light-ui`, `explosive-move-research`.

## Maintenance

When a future session changes MEP — the summed term set, the z-window, the daily bands, the smoothing window or the hysteresis deadbands, or the F&O/identity channel — update **this doc in the same commit** as the code, and mirror constants into `metrics-glossary.md` / `mep-strategy-design.md` §9 and `PROJECT_STATE.md` (D62/D65 / Session log). Keep the §4 descriptor-only fence and the §7 terminology canon intact: MEP characterises/confirms, it never ranks — reviving it as a predictor is blocked until it beats the recorded DSR. If the §3 term list drifts, re-check the code as canonical and update the ⚠ Reconcile note. Keep this page and [dvpt.md](dvpt.md) in sync.
