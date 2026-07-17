# The PORTFOLIO CONSTRUCTION LAYER — design of record

> **Class: DESIGN(live) / LIVING design-of-record for the portfolio-construction program (opened
> S179, ledger `2026-07-16AN`).** Registered in `docs/DOC_INDEX.md` §B. Maintained per the same-commit
> rule: any new portfolio-layer measurement or decision updates this file in the commit that produces it.
>
> **Lifecycle: PERMANENT while the program is open.** This is the design layer *above* the equity book:
> it allocates across the validated book and genuinely different asset classes. It is NOT a strategy
> registration and mints NO deployable portfolio — the sealed union family and its forward test are
> untouched by anything here.
>
> **⚠ DESCRIPTIVE-ONLY FENCE.** Every number below is a descriptive allocation study on a measured
> curve, not advice and not a fund. The G-sec leg is priced on an INDEX (paper) — no fund/execution
> cost is modelled on that leg yet. Return/vol is a return-to-volatility ratio, **never a Sharpe ratio**
> (no risk-free excess; D142 estate-wide relabel). Absolute CAGRs in the mix tables are in-sample and
> selection-inflated by construction — the transferable object is the *dial* (§4), read against the
> deflated forward bands (§2, `16AL`), not the in-sample levels.

---

## §1 What this program is, and what opened it

For the whole RS/union arc (S165→S179) the estate has been building a single **equity book** — a
quarterly-rebalanced long-only Indian-equity strategy, now a four-member sealed family (union · β14 ·
C40RA · COMPOSITE-30) plus the A2-composite deferred lead. Everything in `docs/strategies/union.md`
and `docs/strategies/union-ladder.md` lives *inside* that book: which stocks, how weighted, when sold.

The **portfolio-construction layer** is one level up. It takes a finished equity book as a single
building block and asks the portfolio question: *given this book and a genuinely different asset class,
what static allocation across them produces the highest survivable compounding?* This is not a stock
question and not a timing question — it is an asset-allocation question, and it is the first time the
estate has had a second asset with a low enough correlation to the book to make the question non-trivial.

**Why it opened now (ledger `16AN`, S179).** Every prior attempt to diversify the book failed on
correlation: blending the union with the LOWVOL_MOM momentum family (`16AC`) gave corr **0.83** and a
blend that fell *below* both components — dilution, not diversification. The catalog wall from that
result was explicit: *"only a genuinely low/negative-corr sleeve could ever diversify."* S179 found
one. With 15 years of native primary-source history now ingested (`16AI`/`16AK`), the long
**Government-Securities (G-sec) 10-Year index** correlates with the book at **≈ 0.00**. That single
number is the door this program walks through.

---

## §2 The measured foundation (transcribed from ledger `16AN`; the ledger is the source of truth)

**Correlation (quarterly returns, the number that decides whether the door leads anywhere):**

| pair | full (hybrid) | 2011+ native |
|---|---|---|
| corr(COMPOSITE-30, G-sec 10Yr) | −0.03 | **−0.04** |
| corr(A2-composite, G-sec 10Yr) | ≈ 0.00 | **−0.00** |

**The G-sec leg itself (native era 2011+):** CAGR **6.5%** at annualised vol **4.3%** — a low-return,
low-vol, ~zero-equity-correlation asset. Total-return by construction (a bond total-return index);
sourced from `niftyindices_hist.py`, ingested to prod `index_rows` (manifest `indexes_tri`, S175).

**The decision-grade mix table (2011–2026, native G-sec; quarterly-rebalanced fixed weights):**

| mix (equity/G-sec) | K30 CAGR | K30 ret/vol | K30 MaxDD | A2 CAGR | A2 ret/vol | A2 MaxDD |
|---|---|---|---|---|---|---|
| 100 / 0 | 24.9% | 1.11 | −18.1% | 24.3% | 1.10 | −17.9% |
| 90 / 10 | 23.2% | 1.14 | −16.7% | 22.6% | 1.13 | −16.5% |
| 80 / 20 | 21.5% | 1.18 | −15.3% | 21.0% | 1.17 | −15.1% |
| 70 / 30 | 19.8% | **1.23** | **−13.8%** | 19.3% | 1.22 | −13.6% |

(Full-period *hybrid* rows — G-sec = rf-proxy pre-2011, disclosed per row — are in the module output;
same shape, MaxDD **−31.7% → −21.2%** across the K30 mixes as G-sec rises 0→30%.)

**The two honest caveats on this table (do not quote it without them):**
1. **The absolute CAGRs are in-sample.** The 100/0 native rows (24.9 / 24.3) already sit slightly below
   the sealed headline stats (K30 26.4 / A2 25.5) because the grid drops the first quarter for G-sec
   alignment. More importantly, the equity book's headline CAGR is *selection-inflated* by construction;
   the honest **deflated forward bands** (Bailey-LdP, N=69, `16AL`) are **K30 ≈ 21.6% · A2 ≈ 21.0%**.
   **Quote a forward number by applying the §4 dial slope to the deflated band, never by reading the
   in-sample mix CAGR as a forward expectation.**
2. **The dial is the robust read.** Unlike `16AC`'s momentum blend, here *every* mix's return/vol
   **rises** monotonically with the G-sec weight (1.11 → 1.23 for K30). The *relative* movement — the
   trade of compounding for survivability — is what reproduces; the absolute level is not.

Provenance: `research/explosive_moves/portfolio_mix.py` (design + disclosures in its docstring; the two
book gates K30/A2 reproduce 26.4%/115.69× and 25.5%/99.03× before any allocation number is read, else
the module aborts). Box read-only; no deploy, no service touch.

---

## §3 The veto pass — why a fixed G-sec allocation is allowed (cite before extending)

Per the failure-ledger discipline (negative knowledge first), the walls that govern this program:

- **`16AC` — the momentum-blend wall (this program's INVITATION, not its blocker).** Momentum×momentum
  blends fail at corr 0.79–0.83. The G-sec leg is not a momentum sleeve and is the exact "genuinely
  low/negative-corr sleeve" that wall left the door open for. ✅ cleared by the −0.04/−0.00 correlation.
- **`16W` — the throttle/timing wall (BINDING; do not cross).** Signal-timed exposure (linear / step /
  hard market-stretch throttles) made every metric worse. **Fixed weights are not market-timing** — the
  allocation never reads a market signal. Any weight that *reacts* to price, volatility, drawdown, or
  regime re-enters this wall and is forbidden here (see §5, §8).
- **`16AJ` B2 — the bear-state-gated G-sec sleeve (DECIDED inert/data-bounded).** Switching the book's
  *idle cash* into G-sec only during bear states was inert on the lead (idle ~1%) and data-bounded on
  the union (the 2008-09 bear predates the 2011+ G-sec series). **This program is different:** the mix is
  a **fixed, unconditional, portfolio-level** allocation — not a state gate on idle cash. That distinction
  is what makes it a new, allowed experiment rather than a re-run of B2.
- **`16X` (narrowed by `16AF`) — sizing walls.** Inverse-vol and score-proportional *intra-book* sizing
  were settled inside the book. They do not govern the *cross-asset* allocation, which is a different
  lever; but they are the reason the layer's weights are **fixed policy**, not an optimiser's output.

Nothing here re-runs a catalog §§A–G row. The program is the `16AC`-invited experiment, executed as a
fixed unconditional mix.

---

## §4 Weights policy — the dial, the policy points, the decision rule

The measured curve is a **monotone dial**, not an optimum. There is no single "best" mix; there is a
continuum, and the choice is a risk-appetite decision. Reading the native table (§2):

> **Each +10% G-sec buys ≈ −1.5pp MaxDD (native; ≈ −3.5pp full, including 2008) and a step up in
> return/vol, and costs ≈ −1.7pp CAGR.** The trade is smooth and priced.

**Named policy points (the design's reference menu):**

| policy point | mix | character | who it's for |
|---|---|---|---|
| **Max-Compounding** | 100 / 0 | the sealed equity book itself; highest CAGR, deepest drawdown | the forward-tested family as-is; anyone whose drawdown budget already contains the book's ~−18% (native) / ~−32% (full) |
| **Balanced (default)** | 80 / 20 | +6% return/vol vs 100/0, ~3pp MaxDD relief (native), modest CAGR give-up | the design's suggested default when the book's raw drawdown is too deep for the holder's stomach |
| **Survivability-tilted** | 70 / 30 | peak measured return/vol (1.23), shallowest drawdown | drawdown-first holders willing to give up the most compounding |

**The decision rule (drawdown-target-as-policy — see §5):** *pick the highest-equity mix whose ex-ante
measured MaxDD is within the holder's stated drawdown budget.* The drawdown target selects a **single
static weight**; it is not a control loop. Worked example on the native curve: a −16% drawdown budget
selects **90/10** (−16.7% rounds in); a −15% budget selects **80/20** (−15.3%); a −14% budget selects
**70/30** (−13.8%). Because the dial is monotone, this rule always returns a unique point.

**The design's recommended default is 80/20**, on the reasoning that it captures most of the
diversification benefit (return/vol 1.11 → 1.18, +6.3%; native MaxDD −18.1% → −15.3%) for a bounded
compounding give-up, while keeping the portfolio overwhelmingly the equity engine that carries the
alpha. **This is a recommendation, not a decision:** the ledger records that *Ramana's risk appetite
picks the point*, and the sealed family remains the 100/0 book regardless. The default exists so the
program has a concrete anchor for §9 reporting, not to pre-empt the owner.

**Book choice inside the mix.** The equity leg should be whichever book graduates the 2026-10-03 forward
test (adjudication picks ≤1). Until then the layer is illustrated on both the confirmed lead (K30 /
COMPOSITE-30) and the lower-drawdown A2 — their mix rows are within ~0.5pp of each other, so the
allocation conclusion is book-invariant across the two candidates.

---

## §5 Drawdown-targeting: POLICY, never SIGNAL (the load-bearing distinction)

The queue explicitly asks for drawdown-targeting **as policy, not as signal.** These are two different
things and only one is allowed:

- **SIGNAL (FORBIDDEN — this is the `16W` throttle wall).** Monitor the portfolio's *realised* drawdown
  and cut equity exposure when it breaches a threshold, restoring it later. This is state-gated,
  time-varying exposure that reacts to the market. `16W` measured exactly this shape (throttles) and it
  made every metric worse; it is also a "dynamic/timed weight" and is therefore doubly barred (§8).
- **POLICY (ALLOWED — what the curve gives).** Choose **one fixed mix, ex ante**, whose *measured* MaxDD
  over the sample meets the drawdown budget, and hold it. The drawdown target drives the **static weight
  choice** (§4 decision rule); it never drives an intra-life adjustment. Realised drawdowns are not read,
  not reacted to, not fed back. Rebalancing (§6) restores the *same fixed target*, it does not chase the
  drawdown.

The one-sentence test: *does any weight in the portfolio depend on something observed after inception?*
If yes, it is a signal and needs a fresh pre-registration (§8). If every weight was fixed at inception
and only mechanically restored to that fixed value, it is policy and is covered by this design.

---

## §6 Rebalance band — proposed policy (measurement owed)

The S179 study measured **calendar** rebalancing (weights reset to target every quarter). A **tolerance
band** is a refinement to cut turnover cost, proposed here as policy and **flagged as not-yet-measured**:

- **Cadence:** piggyback the book's existing **quarterly** rebalance dates (first trading day of
  Jan/Apr/Jul/Oct). Introduce **no new cadence** — the cadence law is settled with four confirmations
  (`16AC`; monthly always loses). The band is checked *at* the quarterly date, not continuously.
- **Rule (proposed default):** at each quarterly date, after the book re-selects internally, compute the
  drifted book/G-sec split. **Rebalance the G-sec leg back to target only if |actual − target| on the
  G-sec weight exceeds ±5 absolute percentage points**; otherwise leave it. This skips the small
  rebalances that cost turnover without materially changing the risk profile.
- **Why a band at all:** the two legs are ~uncorrelated with very different vols, so between quarters the
  equity leg drifts the weight around by a few points; a ±5pp band absorbs most of that drift while still
  catching the large moves (a deep equity drawdown that pushes the mix well off target). The equity leg
  already pays its own internal turnover; the band's only job is to avoid needless *G-sec-leg* trades.
- **⚠ Owed measurement (do not report a band result until run):** turnover saved, and the CAGR /
  return/vol / MaxDD delta vs calendar rebalancing, must be measured on `portfolio_mix.py`'s grid before
  the band is quoted as anything but a design proposal. The band could in principle *raise* realised
  drawdown (by letting the equity weight drift up in a rally that then reverses) — that is exactly what
  the measurement checks. Until measured, **calendar quarterly rebalancing is the reported policy** and
  the band is a proposal.

---

## §7 The gold leg — data validated + preliminarily measured (ledger `16AP`, S180)

Gold is the natural *second* diversifier candidate: historically low equity correlation, a different
macro driver. Guardrail #8 forbids a vendor/Screener gold feed — but the estate already ingests an
authentic exchange gold series it hadn't yet used: **NSE-listed gold ETFs flow through the equity
bhavcopy.** S180 validated the data and ran a **preliminary** measurement. Below: what was required,
what was found, and the honest fences on the numbers.

**§7a — data feasibility: CONFIRMED.** **GOLDBEES** (NSE bhavcopy, series EQ; primary-source,
Guardrail-#8-clean) has **4,771 trading days, 2007-03-19 → 2026-07-16** — fully covers the 2011+ native
decision window (pre-2007 would need the hybrid treatment, same as G-sec). It is the deepest and most
liquid of 11 gold ETFs in the archive (~15M units/day), so it is the leading candidate; SGB / an
official gold benchmark remain secondary fallbacks.

**§7c — ✅ DATA-QUALITY blocker — FIXED S182 (ledger `16AQ`).** The split + **13 peer gold-ETF gaps** are now in `corporate_actions` via `scripts/backfill_etf_splits.py` (idempotent, NSE-bhavcopy-derived); the research `adjust.py`/`load_factors` path now prints native **+11.9%** (verified on box). Root cause: the NSE `index=equities` CA feed omits the ETF instrument class. *(Original finding, for the record:)* GOLDBEES underwent a
**100:1 unit subdivision on 2019-12-19** (raw close 3359.6 → 33.55, ratio 0.01) that is **NOT in
`corporate_actions`**, so `adjust.py` — built for equity splits/bonuses — silently left it unadjusted.
The uncorrected series prints **native CAGR −16.9%, vol 29.5%** (one fake −99% quarter; impossible for
gold at INR ~+9-10%/yr). A manual back-adjust (pre-split ×0.01, the announced factor) restores a sane
**+11.9% CAGR / 14.1% vol** native. **This must be fixed properly before any formal gold work** — add
the split to `corporate_actions` and audit the peer gold ETFs (KOTAKGOLD/AXISGOLD/…) for the same gap;
it affects *any* consumer of adjusted GOLDBEES prices, not just this study. (Spawned as a separate DQ
task, S180.)

**§7 — the go/no-go correlation (split-adjusted, native 2011+):** corr(K30, gold) **−0.18** ·
corr(A2, gold) **−0.21** — mildly negative, far below the 0.83 momentum-blend wall → **gold clears the
diversification gate.** corr(gold, G-sec) **−0.12** → the two legs also diversify each other, so a
three-asset grid would add value. **Noise honesty:** n ≈ 62 quarters → corr SE ≈ 0.13, so −0.18 ± ~0.13;
the robust claim is "~uncorrelated / not a dilutant" (exactly as G-sec's −0.04 is within noise of zero),
not a precise −0.18.

**Preliminary two-asset book+gold dial (K30, native 2011+; descriptive; return/vol is a ratio, not a
Sharpe):**

| mix (equity/gold) | K30 CAGR | K30 ret/vol | K30 MaxDD |
|---|---|---|---|
| 100 / 0 | 24.9% | 1.11 | −18.1% |
| 90 / 10 | 24.0% | 1.18 | −15.8% |
| 80 / 20 | 22.9% | 1.27 | −13.5% |
| 70 / 30 | 21.8% | **1.36** | **−11.1%** |

On this window gold **dominates** the §2 G-sec dial (80/20: 22.9/1.27/−13.5 vs G-sec 21.5/1.18/−15.3):
each +10% gold ≈ −1.0pp CAGR (vs G-sec −1.7pp) for a larger ret/vol + drawdown gain. **⚠ But this
dominance is NOT a forward claim:** gold's edge is driven almost entirely by its **regime-specific
+11.9% native return** (flat 2013-19, then the 2020-26 surge) — not forecastable; G-sec's 6.5% is
structural, gold's is not, and the correlation advantage is within noise. **Robust synthesis: gold and
G-sec are BOTH ~uncorrelated diversifiers worth combining; gold's weight should be modest and its return
never extrapolated from this window.**

**§7d — the three-asset grid (ledger `16AR`, S180 cont., on the S182-corrected data).** Built after the
DQ fix landed. It surfaced a finding that reshaped the whole study:

> **🔴 THE SEALED EQUITY BOOK SELECTS GOLD ETFs.** The union book's universe is *all* series EQ/BE/BZ
> names — and gold ETFs trade in series EQ. With ~zero beta (they pass the ≤1.4 cap trivially) and
> top-tier risk-adjusted momentum during gold rallies, they rank into the top-30 and get held: **GOLDBEES
> ×7, SETFGOLD ×2, KOTAKGOLD/HDFCMFGETF/ICICIGOLD/HDFCGOLD/GOLDIETF — 12 of 82 rebalances**, 3.3% each,
> concentrated in the gold-rally years (2020, 2023, 2025). Consequences: (a) **a gold leg on top
> DOUBLE-COUNTS gold** — so the meaningful three-asset grid must use a **gold-ETF-excluded** equity book;
> (b) the sealed backtests embed gold-ETF exposure computed on the *unadjusted* prices S182 just fixed;
> (c) it is a **universe-hygiene issue in the sealed strategy itself** (an "equity" book holding a
> commodity), affecting every union sibling and the 2026-10-03 forward runner. **Flagged as a separate
> task; NOT changed here — a sealed-spec universe change is the owner's / union lane's call.**

The grid therefore uses the equity book with **gold ETFs removed from selection** (backfilled with the
next-ranked stocks; clean-book CAGR K30 26.6% / A2 25.7% — near the sealed values, so the exclusion is
minor). Gold enters *only* via the explicit leg. **The grid is a DIAL (relative), not an anchored level**
— the sealed book's absolute repro also drifted ~+0.3pp from box-data changes (an anchor-reverify owed to
the union lane); the dial is robust to that (design §2).

**K30 three-asset dial (native 2011+; descriptive; return/vol is a ratio, not a Sharpe):**

| equity/G-sec/gold | CAGR | ret/vol | MaxDD |
|---|---|---|---|
| 100 / 0 / 0 | 25.1% | 1.12 | −18.1% |
| 80 / 20 / 0 (G-sec only) | 21.6% | 1.19 | −15.3% |
| 80 / 0 / 20 (gold only) | 23.1% | 1.27 | −13.5% |
| 80 / 10 / 10 (balanced) | 22.4% | 1.24 | −14.4% |
| 70 / 10 / 20 | 21.3% | 1.34 | −12.0% |
| **60 / 0 / 40** (in-sample max ret/vol) | 20.7% | **1.47** | **−9.0%** |

**The headline, honestly framed:** the in-sample optimum **degenerates to book + gold with ZERO G-sec**
(max ret/vol at 60/0/40) — because gold's **regime-specific +11.9%** return strictly dominates G-sec's
structural 6.5% on 2011-26, at similar correlation. **This is the in-sample-optimization trap, not a
forward allocation:** gold's return is not forecastable and G-sec's low-risk contribution is understated
by this one gold-bull window. Both legs are genuine ~uncorrelated diversifiers (corr with book −0.18 /
−0.04; with each other −0.12). **Robust use: a MODEST gold sleeve *alongside* G-sec (e.g. 80/10/10 or
70/10/20), weights set by risk appetite — never by this window's optimizer, which would put 40% in gold.**
Provenance: `portfolio_mix.py` (unchanged) + the S180 three-asset probe; box read-only.

**§7d(repro) — reproduced read-only + owner decision (2026-07-17, task `task_7a70ad77`).** The finding was
re-confirmed on the current post-`16AQ` archive, and the ETF contamination is **broader than gold**:

- **Any-ETF selection touches 34/82 (K30) · 38/82 (A2) rebalances.** The single biggest holder is
  **NIFTYBEES ×13–15** (the Nifty-50 *benchmark* ETF — a stock-selection book buying the index), then
  GOLDBEES ×7–9, LIQUIDBEES ×6–7, SETFNIF50/CPSEETF ×4–5, plus silver/international ETFs. **Gold-ETF-only
  is 9/82 (K30) · 10/82 (A2)** (GOLDBEES ×7, RELGOLD ×2, SETFGOLD ×2, GOLDIETF ×2, then
  KOTAKGOLD/HDFCMFGETF/ICICIGOLD/HDFCGOLD ×1; concentrated 2011/2018–20/2023/2025). The `16AR` note's "12"
  was the **pre-repair S180 count** — the S182 price fix shifts the gold-ETF momentum ranks, and the note's
  symbol list omitted the historical orphans RELGOLD/SBIGETS. Identification: `nse_etf_list.assets`
  (∋ 'Gold', ∌ 'Silver') ∪ verified historical orphans (probe `/tmp/diag_etf_selection.py`, box read-only).
- **Exclusion impact is small at every breadth, and no verdict/ranking moves** (sealed rule reproduces
  as-is; drift disclosed by the `16AS` gate):

  | variant | K30 | A2 |
  |---|---|---|
  | as-sealed (holds ETFs) | 26.46% / 116.04× | 25.49% / 99.25× |
  | gold-ETF excluded | 26.67% / 120.02× | 25.97% / 107.20× |
  | all-ETF excluded | 26.72% / 120.92× | 25.76% / 103.77× |

- **Owner decision (Ramana, 2026-07-17): RATIFY S183 + document — option (b).** Keep the hash-frozen seals
  as-is; the forward runner keeps running the frozen rule **as-sealed** and *flags* any ETF it selects;
  the ETF-excluded companion numbers above stand beside the headline for transparency. Re-sealing
  (options a/c) is **rejected** — the <0.5pp effect and zero verdict change do not justify voiding a
  pre-registration. A clean-universe book, if ever wanted, is a **new pre-registered sibling** (§8), never
  an edit to these seals nor a selection hack in the reporting layer.

---

## §8 What this program will NOT do without a fresh pre-registration

The S179 finding is a *fixed-mix* result. The following are explicitly **barred without a fresh prereg**
carrying the full falsification battery (`FABLE-PROTOCOL` §2) — banking this so no future session drifts:

- **Dynamic / timed / regime-conditioned weights** of any kind (vol-targeting, risk-parity that re-solves
  on rolling vol, drawdown-reactive de-risking, momentum-of-G-sec, macro overlays). Every one of these is
  a weight that depends on post-inception observation → the §5 SIGNAL case and/or the `16W` wall. A fresh
  prereg with an OOS gate is the *only* door, because the S179 curve provides no evidence for any of them.
- **New asset legs without primary-source data** (gold per §7, or anything else) — Guardrail #8 first,
  numbers second.
- **Any registration or deployment.** This program mints no sealed spec and no `/dash` surface. The mix is
  a *reporting overlay* on whichever book graduates (§9), not a strategy of its own. If a portfolio-level
  strategy is ever to be registered, it goes through the full prereg + forward-test process like any
  sibling, and through `docs/SURFACE-PLAYBOOK.md` if it is ever surfaced.
- **Re-running any catalog §§A–G row** or any settled book lever (P / clamp / beta cap / top-N / trail /
  cadence / sleeve-index) — all settled with numbers.

Fixed-mix, unconditional, calendar-or-band rebalanced, on primary-source assets, reported beside the
forward test — that is the whole allowed surface of this design until a new prereg widens it.

---

## §9 Reporting integration — fold the chosen point into the forward-test day

The portfolio layer's product is not a new backtest to babysit; it is a **column on the 2026-10-03
forward-test report.** ✅ **BUILT (S181): `research/explosive_moves/union_forward.py`** — the
one-command forward-test-day runner — prints the dial at every checkpoint:

- Its §4 block prints the **forward-window mix rows for K30 and A2 at 100/0 · 90/10 · 80/20 · 70/30**
  (cum, MaxDD; annualized + ret/vol once ≥ 4 forward quarters exist), G-sec leg via the same `gsec_q`
  grid. When Ramana picks the policy point, that row gets a `<< POLICY` marker (one-line change);
  until then the print names 80/20 as the design default and the sealed specs stay 100/0.
- Labels are kept honest there: the mix rows are descriptive, G-sec is paper, return/vol is not a
  Sharpe ratio.

This is a print-level addition to the forward reporting, not a decision the forward test adjudicates —
the forward test judges the *book*; the portfolio layer just shows the book at the owner's risk point.

---

## §10 Open items (recorded, not run)

1. **Rebalance-band measurement** (§6) — turnover + risk deltas vs calendar quarterly, on
   `portfolio_mix.py`'s grid, on the box. Until then calendar quarterly is the reported policy.
2. **Gold-leg** (§7) — ✅ DONE end-to-end: data validated + corr (S180 `16AP`) → DQ split fix (S182
   `16AQ`) → **three-asset grid (S180 cont. `16AR`, §7d)**. Result: gold clears the gate but the
   in-sample optimum degenerates to book+gold (regime-inflated) — robust use is a modest gold sleeve
   *alongside* G-sec. ~~**Remaining (optional):** formalise GOLDBEES via the feed protocol~~ — ✅ DONE
   S184: manifest row `gold_etf` (rides the bhavcopy nightly, no new fetcher) + the `chk_split_cliffs`
   nightly DQ guard (the 16AQ-recurrence detector, all symbols).
3. ~~**Fold the policy point into forward reporting** (§9)~~ — ✅ DONE S181 (`union_forward.py` §4
   prints the dial each checkpoint; only the `<< POLICY` marker awaits Ramana's pick).
4. **(Optional ratchet)** add this doc to `tests/test_retvol_label_gate.py`'s scanned set so the honest
   labels are machine-enforced (tightening only; not done now to avoid touching the gate's deliberate
   scope mid-program).
5. ~~**🔴 NEW (S180 cont., §7d) — the sealed equity book selects gold ETFs**~~ — ✅ **REPRODUCED +
   DECIDED (2026-07-17, `task_7a70ad77`, §7d(repro)).** Re-confirmed read-only; the contamination is
   broader than gold (any-ETF 34/38 of 82; NIFTYBEES ×13–15 the biggest, gold 9/10). **Owner decision:
   RATIFY S183 + document (option b)** — seals kept as-sealed, forward runs the frozen rule + flags ETF
   picks, ETF-excluded companion numbers recorded beside the headline. Exclusion effect <0.5pp, no verdict
   moves; re-sealing rejected. A clean-universe book, if ever wanted, is a new pre-registered sibling (§8).
6. ~~**Anchor re-verify (union lane)**~~ — ✅ **RESOLVED.** The "~+0.3pp" was the *exclusion* effect
   (etf-excluded 26.7), not data drift. The **unmodified** sealed rule reproduces at K30 26.46%/116.04×
   (seal 26.4/115.69, +0.35× mult) · A2 25.49%/99.25× (+0.22×) — drift **localized to the gold-ETF-holding
   books** (A1/A2/K30; U/B14/C40 reproduce to the digit), caused by S182's `16AQ` repair. S183's `16AS`
   drift-proof gate (mult anchors on input-closed legs ≤2026-04-01) already handles it and passes.

## §11 Provenance & labels

- **Numbers:** ledger `2026-07-16AN` (source of truth) · deflated bands `16AL` · book seals per
  `docs/strategies/union-ladder.md`. Module: `research/explosive_moves/portfolio_mix.py`.
- **Data:** G-sec 10Yr + TRI series via `niftyindices_hist.py`, prod `index_rows` manifest `indexes_tri`
  (`16AK`). Primary-source, Guardrail-#8-clean.
- **Labels:** *return/vol* = mean/σ return ratio, **not a Sharpe ratio** (D142); the G-sec leg is an index
  (paper); every table is descriptive, not advice. The equity book's forward expectation is the deflated
  band, not the in-sample headline.
