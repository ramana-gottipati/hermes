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

## §7 The gold leg — pending primary-source data (Guardrail #8)

Gold is the natural *second* diversifier candidate: historically low equity correlation, a different
macro driver. But **the estate has no primary-source gold series in the DB**, and Guardrail #8 forbids
adding a vendor/Screener gold feed. The gold leg is therefore a **specified design placeholder, not a
measured result** — no gold number will appear in this program until primary data exists.

**The data requirement (must be met before any gold-leg backtest):**
- A **primary-source, total-return-capable gold series** with enough history to cover the book's window.
  The leading primary candidate is an **NSE-listed gold ETF** (e.g. GOLDBEES) whose adjusted price
  history already flows through the equity **bhavcopy** the estate ingests — an authentic exchange feed,
  Guardrail-#8-clean. Before use it must be validated for (a) history depth vs the 2006/2011 book start,
  (b) tracking quality / NAV-premium behaviour, and (c) the corporate-action / adjustment path (ETF
  splits, if any). Sovereign Gold Bonds (SGB, NSE-listed) and any official gold price benchmark are
  secondary primary candidates if ETF history is too shallow.
- Ingest via the estate's **feed protocol** (manifest entry + licence/DQ gate + pull-on-demand freshness),
  exactly as the TRI/G-sec series were (`16AK`).
- Only then: measure **corr(book, gold)** first (the §2 gating discipline — if it is not meaningfully
  below the momentum-blend 0.83, gold adds nothing and stops there), and if it clears, extend the mix
  grid to a **three-asset** book/G-sec/gold allocation.

Until that data lands, the gold leg is **out of scope for any number** and in scope only as this
specification.

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
forward-test report.** The next step for the program (recorded, low-effort, owed to that day):

- When the forward runner (`union_lab6.py` and the val runner) prints the graduating book's forward
  numbers, **also print the chosen policy-point mix** (default 80/20, and the 100/0 and 70/30 bookends)
  so the owner sees the same forward quarter through the compounding-vs-survivability dial, not only at
  100% equity. The G-sec quarterly returns are already on the same grid in `portfolio_mix.py`.
- Keep the labels honest there too: the mix rows are descriptive, G-sec is paper, return/vol is not a
  Sharpe ratio.

This is a print-level addition to the forward reporting, not a decision the forward test adjudicates —
the forward test judges the *book*; the portfolio layer just shows the book at the owner's risk point.

---

## §10 Open items (recorded, not run)

1. **Rebalance-band measurement** (§6) — turnover + risk deltas vs calendar quarterly, on
   `portfolio_mix.py`'s grid, on the box. Until then calendar quarterly is the reported policy.
2. **Gold-leg data** (§7) — source + validate + ingest an NSE gold-ETF (or SGB) primary series via the
   feed protocol; measure corr(book, gold) *first*; three-asset grid only if it clears the 0.83 bar.
3. **Fold the policy point into forward reporting** (§9) — a print addition to the forward runners for
   2026-10-03.
4. **(Optional ratchet)** add this doc to `tests/test_retvol_label_gate.py`'s scanned set so the honest
   labels are machine-enforced (tightening only; not done now to avoid touching the gate's deliberate
   scope mid-program).

## §11 Provenance & labels

- **Numbers:** ledger `2026-07-16AN` (source of truth) · deflated bands `16AL` · book seals per
  `docs/strategies/union-ladder.md`. Module: `research/explosive_moves/portfolio_mix.py`.
- **Data:** G-sec 10Yr + TRI series via `niftyindices_hist.py`, prod `index_rows` manifest `indexes_tri`
  (`16AK`). Primary-source, Guardrail-#8-clean.
- **Labels:** *return/vol* = mean/σ return ratio, **not a Sharpe ratio** (D142); the G-sec leg is an index
  (paper); every table is descriptive, not advice. The equity book's forward expectation is the deflated
  band, not the in-sample headline.
