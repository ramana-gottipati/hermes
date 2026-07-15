# Problem Statement for Codex: Ramana's Two-Step Sector→Stock Selection Strategy

> **Lifecycle: TRANSIENT.** This is a hand-off brief, not canon. Retire it once its recommended build
> lands and its durable findings are folded into `docs/strategies/sector-rotation.md`,
> `docs/strategy-ledger.md`, and `PROJECT_STATE.md` — the same discipline every other document in this
> repo follows. Everything asserted here is sourced to an exact commit, file, or ledger section; nothing
> here is new research — it is a synthesis of research already done and committed on `origin/main`.
>
> Written 2026-07-15, against `origin/main` @ `da3a56a`.

You (Codex) are being asked to **finish testing a strategy that has been circled by two independent
research arcs in the same day, from two different angles, both converging on the same unfinished
conclusion**: nobody has yet given Ramana's actual design a fair test. This document tells you exactly
what has been tried, what broke, what's proven, what's still open, and precisely what a fair test looks
like. Read it in full before writing any code — several plausible-looking approaches below are already
dead ends, proven so with real numbers, not guessed.

---

## 1. What this strategy is, in Ramana's own words

Ramana is a financial analyst (Vizag, India) building a systematic Indian-equity strategy on Hermes/
Patearn, his personal research platform. The design is **two steps, run in sequence**:

> **Step 1 — identify the sector.** "Find every sector beating the benchmark."
> **Step 2 — identify the stock.** *"When you identify a sector, you should select a stock only from that
> sector... if a stock is performing well within its NARROW index, we will target it"* — i.e. a stock's
> strength must be measured **against its own sector**, not the broad market. *"Whenever a stock moves
> within the sector, consider both the minor index and the broader index together"* — the stock must beat
> **both** its own sector and Nifty 500. *"We need a portfolio that outperforms... we can't rely entirely
> on one stock, nor can we diversify excessively"* — a bounded book, not one name, not the whole market.
> Portfolio ceiling: **30-35 stocks, ~₹1 crore**.

Two things Ramana has said that are **binding requirements**, not suggestions:

- *"Even if the companies died... the strategy should address all of those problems — we must have proper
  exit strategies written."* An exit/stop discipline is part of the brief, not an enhancement.
- *"For media, realty, consumer durables we cannot invest directly [via an index] — we must invest through
  the stocks."* The stock layer is not a refinement of the sector layer; for roughly a third of the
  sectors it is the **only executable expression** of the strategy at all (several NSE sectoral indices
  have no liquid ETF/futures instrument).

---

## 2. Binding doctrine — do not re-litigate these, they are evidence-backed and decided

1. **Primary sources only** (`CLAUDE.md` Guardrail #8). Every data feed used below is NSE/BSE official or
   derived purely from data this project already owns. `company_about.screener_industry` exists in the
   schema — **it is Screener-sourced and off-limits for anything new.** Do not touch it.
2. **A pre-registered bar, set BEFORE a result is seen, and a REJECTION is an acceptable, valuable
   outcome.** This project's whole failure ledger (`docs/strategy-ledger.md`) runs on this discipline.
   Do not manufacture a win by trying variants until one clears a bar after the fact — every retraction
   below happened precisely because an earlier session skipped this.
3. **Reproducibility convention**: a validated engine is reused by `exec`-ing its source above its own
   driver line and calling its functions directly — never re-derived, never copy-pasted with drift. See
   `research/explosive_moves/sector_rotation_significance.py` and `sector_stock_book_adj.py` for the
   pattern. Any new module should self-gate: assert it reproduces a cited prior number before trusting
   anything new it computes, and exit non-zero if it stops matching.
4. **Value, not share count, across time** (`CLAUDE.md` Guardrail #5) — this is the guardrail that was
   *violated all session* until §4 below caught it. Read that section carefully.
5. **"Sharpe" does not exist anywhere in this codebase.** Every ratio computed as `mean/sd*sqrt(periods)`
   with no risk-free rate subtracted is a **return/vol ratio** (PROJECT_STATE **D142**, `tests/
   test_retvol_label_gate.py` — the 6th machine gate, blocks the word "Sharpe" from reappearing in
   `research/`). Relative comparisons between two return/vol ratios computed the same way are valid;
   treat the absolute level of any number below as **not a true Sharpe ratio**.
6. **Prod venv is stdlib-only** (no numpy/pandas). Every module below is plain Python for a reason.

---

## 3. The current, corrected state of knowledge — read this before writing a line of code

### 3.1 The sector layer (Step 1) — built, live, and NOT what needs work

`research/explosive_moves/sector_rotation_v24_final.py` is the validated, frozen engine. It reads only
`index_rows` (2005→2026), holds sector **indices**, never stocks. Ladder: V8 (frozen) → V17 → **V21 (live
default on `/dash/sector-rotation`)** → **V24** (designated carry-forward layer, on *mechanism* grounds —
its edge over V21 is **not statistically distinguishable from noise**, PROJECT_STATE **D139**: return/vol
0.911 vs V21's 0.875, gap unmeasurable at this window's power) → V32 (**retired**, indistinguishable from
V24, D139).

**V24 baseline, 2005→2026, n=258 monthly, self-gated and reproduced exactly across three independent
modules this session — cite these numbers, do not re-derive:**

| | return/vol | H1 / H2 | CAGR | MaxDD | ₹1 Cr → |
|---|---|---|---|---|---|
| **V24** | 0.911 | 0.92 / 0.905 | 17.2% (17.28% independently re-derived) | −37.7% | ₹30.35 Cr (30.349 precise) |
| Nifty 500 buy-hold (same calendar) | 0.637 | 0.576/0.782 | 12.51% | −62.0% | ₹12.60 Cr |

**Target reset (ledger `2026-07-15N`, `82fc596`):** Ramana proposed 60-70% CAGR ("Nifty 12% → sectors
~30% → stocks 60%"). Both source numbers were misreadings, not targets: "sectors ~30%" was the **30.35×
terminal multiple** misread as a CAGR (true CAGR is 17.3%); "60%" was **D140's cadence bug** rendering a
quarterly book's CAGR as if monthly (60.40% shown on his own live dashboard before the fix; true 17.28%).
**Accepted, corrected target: 17.3% floor, 20-22% aim.** Two levers tested against that target this
session:
- **Wider pond (more sectors/blends): REJECTED.** Widening with MNC/PSE/Commodities/Midcap50 (all
  available from 2004) *lowered* the number: 17.2%→16.6% CAGR, 0.911→0.883 retvol. These overlap the
  sectors already held — dilution, not diversification. **Do not re-attempt via blend overlays.**
- **A trailing stop-loss on the SECTOR book itself ("the cull", Ramana's own instrument, ported from the
  stock-layer work below): a genuine, validated improvement, NOT YET PROMOTED.**
  `research/explosive_moves/v24_cull.py`. Trail **−20%** (checked against `index_rows` daily closes within
  each month): **CAGR 17.28% (vs 17.2% baseline — held), MaxDD −30.2% (vs −37.7% — 7.5pp better), retvol
  0.987 (0.993/0.999 — the most half-balanced construct recorded), ₹30.78 Cr, 36 culls over 21.4y.**
  Tighter trails (−8% to −15%) fire on ordinary sector noise (63-96 culls) and lose to baseline; hard stops
  all lose (a stopped-out sector cannot participate in its own recovery; a trailing stop rides it up
  first). **Caveats, both real, neither fixed yet:** this is 1 of 10 variants selected on ONE window (the
  same selection-deflation risk D139 measured elsewhere — needs a fresh-window check before being trusted);
  and the whole ladder still rests on a **price-index** Nifty 500 benchmark (the TR re-cut is still owed,
  PROJECT_STATE D139/D142).
- **The 20-22% target was NOT reached this session.** Better sector-layer selection tops out at 17.28%.
  The only route left that reaches the target is leverage against the risk the cull freed up — an
  appetite decision for Ramana, explicitly **not** a research finding and not something to build.

**The sector layer is not your job.** It is frozen, validated, and self-consistent. Your job is Step 2.

### 3.2 The stock layer (Step 2) — the actual open problem, and its full, messy history

**🔴 FIRST HOUSEKEEPING ITEM — retract a stale result before using this repo.**
`docs/strategy-ledger.md` §**2026-07-15l** (PROJECT_STATE **D141**) claims the two-step method was
"simulated end-to-end" and REJECTED (return/vol 0.775 vs V24's 0.911, MaxDD −43.2%). **That result is
unretracted but almost certainly contaminated** by the exact two data bugs below that retracted five
*other* studies the same day (§15j/15k/15L/15M in `bab75cf`/`43f56de`) — its own source,
`research/explosive_moves/sector_stock_layer.py`, queries `bhavcopy_rows WHERE series='EQ'` (line 125) and
uses raw, unadjusted `close`. It was never formally re-run or retracted because it predates the bug
discovery by a few commits. **Treat §2026-07-15l as UNRELIABLE, not as evidence.** Part of your
deliverable is a proper retraction banner on it (same template as §15O below), pointing at this document
and at whichever corrected result supersedes it.

**Then, in the same session, a *different* lane ran six studies in sequence on the *unconditioned* version
of the same question (no sector gate at all — "does picking top-RS stocks from the whole market beat Nifty
500?"), found three serious, unrelated bugs along the way, and ended with one genuinely new mechanism that
explains everything. In order:**

**§15j (`24d57e6`) — first pass, later retracted.** Naive top-K RS momentum, no sector gate. Result: loses
to Nifty 500 at every one of ~20 variants (naive alpha −0.5%/yr). Hysteresis — the single biggest winning
lever at the *sector* layer — **backfires** at the stock layer (alpha worsens −0.5%→−7.3% as the band
widens). *(Retracted below — but this specific finding, sector-layer levers not transferring to stocks,
turned out to still be true after the data fixes.)*

**§15k (`4c8303e`) — exits, later retracted.** No exit rule existed in §15j at all (Ramana caught this: "we
must have proper exit strategies written"). A hard −15% stop cut beta 1.18→0.78 and MaxDD −68%→−47%, alpha
+3.5% — but the alpha died past ~2% realistic fill slippage. *(Retracted — but "the dumb price stop beat
the smart signal exit" and "exits fix risk, not return" both survived the later data fix.)*

**§15L (`43f56de`) — DATA BUG, retracts §15j/§15k.** `series='EQ'` misreads NSE's surveillance mechanism
(BE series) as **deaths**. 656,007 rows / 2,554 symbols (8% of `bhavcopy_rows`) sit in `series='BE'`.
Checked directly (`vanish_audit.py`): of 9,604 "EQ-vanish" events, **84.4% were still trading** in another
series, 79.1% returned to EQ within 12 months, only 12.2% genuinely gone. **BE-flagging is triggered by
exactly the sharp run-up that puts a stock in the top RS decile — the bug specifically attacked the
treatment group.** Fix: filter `series IN ('EQ','BE','BZ')`. Re-run on the corrected universe: **selection
itself is real** (+1.73%/qtr over random from the same pond, t meaningful) — **the pond is the problem**: an
equal-weight basket of liquid Indian stocks loses **−1.24%/qtr (−4.9%/yr, t=−2.21) to Nifty 500 before any
stock is even picked**, because Nifty 500 is a **rules-based, self-culling index** (it continuously drops
names that fall out of the top 500 by cap/liquidity) and a naive equal-weight stock pool has no equivalent
culling. "Buy bigger stocks instead" is dead too (`rs_bar.py`): at ₹25cr ADV the pond sinks *more* (−1.52%)
and selection collapses (+1.73%→+0.20%) — **momentum is a small/mid-cap effect, arbitraged away in large
caps**, consistent with the standing ledger record that only `LOWVOL_MOM` quarterly large-cap ever cleared
the fundable bar.

**§15O (`bab75cf`) — DATA BUG, retracts §15j/§15k/§15L's forward numbers, deepest bug of the day.**
`bhavcopy_rows.close` is **raw, unadjusted for splits/bonuses**. A 1:2 bonus reads as −50%; a 10:1 split
reads as −90%. `index_rows.close_value` **is** adjusted — every stock-vs-index comparison all session had
been rigged against the stock. This is Guardrail #5, named in advance, violated in practice. Verified
against real `corporate_actions` (26,891 rows/2,546 symbols): 973 of 1,489 EQ one-day drops worse than −40%
(65%) sit within 3 days of a corporate action. **Fix built and validated:**
`research/explosive_moves/adjust.py` — `load_factors(conn)` reads `corporate_actions` (SPLIT:
`ratio_from/ratio_to`; BONUS: `(ratio_from+ratio_to)/ratio_to`, both conventions confirmed against real
rows), `adjust_all(sclose, fac)` divides every pre-ex-date price by the cumulative factor of all later
corporate actions. 832 symbols / 1,224 events adjusted; unadjusted extreme-drop count (<−40%) 2,238 →
adjusted 1,408 (**79% of artefacts removed**). On one example book the fix moved CAGR **−9.5% → +7.1%**
(~16pp swing) — the bug hit hardest on momentum names, since a stock that just outperformed is exactly the
kind that then announces a bonus/split. **Dividends are deliberately left unadjusted** (the benchmark is a
*price* index, so omitting dividends from both sides is like-for-like); **RIGHTS issues (368) are
unhandled**, disclosed not hidden; 157 of 669 SPLIT rows lack usable ratios (512 usable).

**§15i's classification blocker — DISSOLVED, same commit (`bab75cf`).** The earlier plan (yours and a
sibling's both, independently) was to hand-build a PIT-safe sector classification for ~1,973 symbols
(1,693 live + 280 dead) from a primary industry-classification source. **A much better, already-owned-data
solution was found and validated instead:** `research/explosive_moves/sector_assign_validate.py` —
correlate each liquid stock's **excess return** (vs Nifty 500) against each sector index's **excess
return**, trailing 500 trading days, assign to the sector with highest correlation.
(**Excess-vs-excess is the trick** — raw price correlation just measures shared market beta and hands
every large-cap to whichever sector index is biggest; excess isolates sector-*specific* co-movement.)
**Validated against NSE's own real membership** (the 4 weeks of `stock_index_membership` we actually have):
**85.1% top-1 hit rate, 93.1% top-3, vs ~6.2% random** (1-in-16 sectors), across 202 labelled symbols. Every
weak sector is an *overlapping* one (Bank↔Private Bank↔Financial Services; Infrastructure↔several) — the
method's "misses" are usually an equally-defensible sibling sector, not noise. **Works for dead companies
too**, since it needs only price history (which `bhavcopy_rows` has for delisted names up to their last
trading day) — **no membership table, no external classification source, no manual dead-name labelling
job is needed at all.** This eliminates the entire data-acquisition problem both prior lanes were treating
as the hard blocker.

**§15M (`a69c91f`) — FINAL verdict on the *unconditioned* (no sector gate) RS family, re-run on corrected
EQ+BE+BZ + adjusted prices, Ramana-authorised.** ~30 variants (4 sizes × 4 exit bands × 4 exit types × 3
delisting-value assumptions × 4 slippage levels × 3 start windows × 2 liquidity bars). **REJECTED — zero
variants beat Nifty 500 on return/vol.** Bench (2005, 21.4y): 0.66 / 12.8% CAGR / −60.9% MaxDD / 13.12×.
Best variant (trail −20% cull): 0.54 / 10.9% / −52.5% / 9.15×. **The cull is real** (+6.1pp of alpha
recovered, −5.0%→+1.1%, the single largest effect measured that day, and it was **Ramana's own idea**, not
the model's) but does not close the gap. Two numbers it lives on, both measured as sensitivities not
assumed: delisting value (dead=0%: alpha+3.7%; dead=−50%: +2.4%; dead=−100%: +1.1%) and gap slippage
(0%:+0.6%, 1%:−0.9%, 2%:−2.5%) — **at any honest combination, alpha ≈ zero.** What survives, kept as
fact: (1) selection genuinely works, +1.73%/qtr over random; (2) the cull genuinely works, +6.1pp alpha,
slippage-robust *on risk* (beta 1.18→0.67-0.82, MaxDD −71%→−37-53%); (3) the pond loses on its own,
−4.9%/yr, because Nifty 500 is not passive — it is a good, self-culling, rules-based index, and beating it
means beating a real strategy, not a static basket. **Explicitly out of scope for this verdict: Ramana's
actual design (sector-conditioned).** Do not cite §15M as evidence against the sector-conditioned idea —
it tests a different, unconditioned construction.

**§15N — see §3.1 above (the sector-layer cull, same session, same "the cull works" thread).**

**First honest attempt at Ramana's ACTUAL design (`sector_stock_book_adj.py`, no ledger number assigned
yet) — INCONCLUSIVE, not a verdict.** Combines: the V24 sector gate (RS excess vs Nifty 500 > +8%) → stocks
assigned to sectors via the validated correlation method → a stock must beat **both** its own sector
**and** Nifty 500 (the double test) → corporate-action-adjusted prices, EQ+BE+BZ universe. Thresholds
swept. 2006-2026 bench: CAGR 11.7% / retvol 0.55 / 8.97×.

| variant | CAGR | retvol | MaxDD | beta | alpha | multiple |
|---|---|---|---|---|---|---|
| sector+10%/broad+0% | 7.1% | 0.38 | **−81.0%** | 0.90 | −0.5% | 3.88× |
| top60 cap10/sector | 8.1% | 0.42 | −80.2% | 0.84 | +0.8% | 4.63× |

**Both lose, badly, on drawdown — but the module's own docstring is explicit that this is NOT a fair test:**
it has the sector gate and the stock picker, but **none** of V24's risk machinery — no 30% per-sector cap,
no residual sleeve (idle capital sits in cash/Next-50 in V24; here it's just... not deployed or fully
deployed with no diversification discipline), no exhaustion tapers, no hysteresis, no cull. With only ~2.6
sectors qualifying on average, the resulting book is ~14 stocks from 2-3 sectors, **100% invested,
equal-weighted** — concentration risk with no offsetting structure. **The −81% MaxDD is very likely this
missing structure, not the underlying idea being bad — but that is a hypothesis, not yet measured.**

**§15P (`b20bd6f`) — "THE ANSWER" to the question that mattered: why does picking the best stocks struggle
at all?** Answer: **volatility drag.** Geometric (compounded) return ≈ arithmetic mean − variance/2. The
top-decile stock pool has a **higher mean AND a much higher variance** than the sector index it's drawn
from — and the variance penalty exceeds the mean edge:

| | mean/qtr | sd/qtr | drag | **geometric/qtr** | /yr |
|---|---|---|---|---|---|
| Sector index (what V24 holds) | −0.67% | 10.31% | 0.53% | **−1.20%** | −4.8% |
| Stock pool, equal-weight | +1.54% | 23.77% | 2.83% | **−1.28%** | −5.1% |
| **Top decile (what a naive book buys)** | +1.97% | 26.63% | 3.55% | **−1.58%** | **−6.3%** |
| **Mid decile 6** | +2.38% | 22.75% | 2.59% | **−0.21%** | **−0.8%** |

**The ranking flips between arithmetic and geometric.** By mean: D10 > pool > index. By what actually
compounds: index > pool > **D10 last**. **Decile 6 dominates decile 10 on both axes simultaneously**
(higher mean, lower vol) — "best of the best of the best" is strictly dominated by "good". This is not a
new hypothesis; it retroactively explains **four** signals mis-read as noise earlier the same day, every
one pointing the same wrong-tail direction: top10 worse than top20 (§15j), sector+30% threshold worse than
+10% (§15O sensitivity), a 4-stock-per-sector cap worse than 8 (§15O), hard stops worse than trailing
(§15N/§15M). It also explains a standing, previously-unexplained ledger fact: `LOWVOL_MOM` was the *only*
momentum variant ever to clear the fundable bar (1.02 @ ₹50cr) — this is the mechanism, not a coincidence.
**Confirmed NOT a small-cap artefact first** (a real risk the size-and-liquidity story invites): correlation
of ADV-percentile-within-sector vs excess-vs-sector is **+0.122, positive** — the filter selects big
winners, not obscure ones. **The strategy this implies:** target the **strong-but-calm middle-upper** of a
sector's strength distribution (~decile 6-8), not the extreme; **inverse-vol weight** the stock leg (V24
already does this at the sector level via V20/V21 — never yet applied to the stock leg); diversify wider
(portfolio sigma, not single-asset sigma, is the real toll). **Honest gap, not yet closed:** per-asset drag
alone does not fully reconcile the 17.3%-vs-7.1% *book*-level gap between the sector layer and this first
stock-layer attempt — portfolio sigma ≠ mean asset sigma, and the harness still lacks V24's structure. This
reconciliation is explicitly **owed**, not done.

**§15Q (`da3a56a`) — Ramana's "catch the turn before the crowd" idea, tested in its simplest form, killed.**
Motivated directly by §15P (the top decile buys the *end* of a move at peak volatility — a name that hasn't
run yet hasn't built that variance, so an early-turn entry should win on the *compounded* return even if not
on the mean). Tested via a 2×2 sign-flip (prior 6→3 months ago vs recent 3 months, both vs the stock's own
sector): **NO SIGNAL** — TURN mean +1.17%, ESTABLISHED LEADER +1.71%, FADING +1.55%, LAGGARD +1.59%, **every
cell within ONE standard error of every other** (SE ≈0.53% on a spread of 0.54%). Sectors: same story
(spread 0.59% on SE 0.59%). **This kills the crude sign-flip formulation specifically — it does NOT rule
out a more precise formulation** ("RS at a depressed level with an inflecting slope," "RS crossing its own
trend," "recovery from a measured RS drawdown percentile") — none of those were tested. Do not cite §15Q as
"recovery is dead"; cite it as "the sign-flip version is dead."

**An independent, third confirmation of the same class of problem (from the sector-conditioned side, my own
finding, unretracted — done on a smaller, current-day-classification 268-symbol universe, so treat this as
directionally corroborating, not as precise as the studies above):** the naive "rank by RS-excess vs own
sector *this quarter*, take the top few, re-rank next quarter with no persistence bar" mechanism used in the
now-suspect §2026-07-15l ends up holding **82% of its entire 268-symbol universe at some point** across 86
quarters — 100% coverage in 4 of 16 sectors (every single bank, every single pharma name, every
infrastructure name got held at least once). This is the *same disease* §15P's volatility-drag finding
explains mechanistically: a memoryless, extremal, single-period re-rank does not find persistent winners,
it churns through nearly the whole roster. Any stock-selection rule you build needs either (a) a
persistence/consistency requirement across periods, or (b) §15P's own fix (target the calm middle, not the
extreme) — very possibly both, and they may be the same fix seen two ways.

---

## 4. What is proven true, and should be treated as settled (do not re-test these)

1. **Stock-level relative strength, measured correctly (adjusted prices, EQ+BE+BZ universe, vs a stock's
   own sector or the broad market), carries real forward information: ~+1.73%/qtr (~+7%/yr) over picking
   at random from the same pond.** Selection is not the problem, and never was (§15L, §15M).
2. **An exit/stop discipline is real and valuable — but only on RISK, not return, and only past realistic
   costs.** A trailing stop (not a hard stop) recovers most of a naive book's alpha shortfall and cuts beta
   and drawdown substantially and robustly. It is not, by itself, sufficient to beat Nifty 500 (§15k, §15M),
   and it transfers cleanly to the *sector* layer (§15N) where it is the best-known single lever.
3. **A naive equal-weight stock pool loses to Nifty 500 before any selection is applied**, because Nifty
   500 is an actively self-culling rules-based index, not a passive basket. Any stock-level book must
   either inherit the sector layer's own culling discipline (V24's tapers/hysteresis/recovery-accelerator,
   now potentially its trail-20% cull) or build an equivalent (§15L, §15M).
4. **Volatility drag, not weak selection, is why "best of the best" underperforms "good".** Decile 6-8
   beats decile 10 on both mean and compounded return, simultaneously (§15P). This is the central,
   load-bearing finding of the entire day and should shape the redesign directly.
5. **Sector classification does not need an external data-sourcing project.** The correlation-based method
   is validated at 85.1%/93.1% accuracy and covers dead companies for free (§15i's dissolution, above).
6. **A crude "catch the reversal" sign-flip carries no signal** (§15Q) — but more precise formulations of
   the same idea are untested, not falsified.
7. **Hysteresis, validated as the single best lever at the sector layer, backfires when applied naively at
   the stock layer** (§15j). Do not assume a sector-layer lever transfers; test every transfer explicitly.
8. **"Wider pond" via blended/overlapping index composites lowers CAGR at the sector layer** (§15N) — a
   parallel caution against widening the stock universe with overlapping, non-independent names.

---

## 5. The precise task

**Build and run the first properly-structured test of Ramana's actual design** — the thing §15P, §15N, and
the unfinished `sector_stock_book_adj.py` all converge on as the next step, and the thing §2026-07-15l
never actually delivered (it used broken data and a mechanism §15P's own finding shows is structurally
wrong — extremal top-of-decile selection with no vol-awareness and no persistence bar).

**Combine, in one engine:**

1. **Sector gate** — reuse V24 (`sector_rotation_v24_final.py`) exactly, `exec`'d not re-derived, self-gated
   against its published numbers (§3.1 table above).
2. **Stock universe & sector assignment** — the validated correlation method (`sector_assign_validate.py`),
   not an external classification source. Corporate-action-adjusted prices (`adjust.py`). `series IN
   ('EQ','BE','BZ')`, not `'EQ'` alone.
3. **Stock selection tuned to §15P's finding, not to "best":** target the **~decile 6-8** strength band
   within each qualifying sector (beating both the sector and the broad index, per Ramana's double test,
   but not maximally so), not the top decile. Weight the stock leg by **inverse volatility** (V24's own
   sector-layer mechanism, ported down — never yet applied to stocks).
4. **A genuine exit/cull discipline at the stock level** — start from the validated sector-layer trail−20%
   (§3.1) and the stock-layer trailing-stop findings (§15M) as the prior, not a fresh design; tune from
   there.
5. **V24's full risk structure carried down to the book** — a per-sector cap (V24 uses 30%; consider
   whether the same figure is right for individual stocks, given §15P's variance finding argues for a
   *tighter* per-name cap than per-sector), a residual sleeve for when few sectors qualify (V24 parks idle
   capital in Nifty Next-50 while the market is healthy, cash otherwise — decide whether the stock layer
   should do the same or something calmer, given §15P), and Ramana's cap: **30-35 names total, ~₹1 Cr.**
6. **Reconcile the book-level gap** — §15P's own honest admission is that per-asset volatility drag does
   not yet fully explain the 17.3%-vs-7.1% *book* gap between the sector layer and the first (structurally
   incomplete) stock-layer attempt. Close this reconciliation as part of the work, not as a footnote:
   explain, with numbers, exactly how much of the gap is missing risk-structure (cap/sleeve/tapers/cull)
   vs missing vol-awareness (decile targeting, inverse-vol weights) vs something else.

**Pre-registered bar (do not move this after seeing results — it is set now, from the numbers in §3.1):**
beat **V24 alone** — return/vol 0.911, MaxDD −37.7%, CAGR 17.2%, ₹1 Cr → ₹30.35 Cr — **net of a realistic
per-name stock cost** (higher than the sector layer's 0.15%/side index-ETF assumption; a flat 0.30-0.40%/
side proxy is what this project has used elsewhere, disclosed as a simplification, not a real ADV/impact
model — build one if time allows, but disclose if you don't). **Matching V24 is a REJECTION, not a result**
— per Ramana's own brief, the stock layer only earns its place if it does better than the sector layer
alone, since for several sectors it is also the *only executable* expression (§1). If the result rejects,
say so plainly, with numbers, the same way §15M and §2026-07-15l (once corrected) did. A clean, honest
rejection is a valid and useful deliverable.

**Then, and only if something survives:** run a significance test on it — the same discipline
`sector_rotation_significance.py` used for the sector ladder (D139): a paired bootstrap or equivalent,
report a minimum-detectable-effect alongside any null, and correct for the fact that several configurations
(decile band, inverse-vol weight, cap sizes, cull tightness) will be swept before one is chosen. A backtest
number without this is a repeat of exactly the mistake §15h/§15N both had to correct for at the sector
layer.

---

## 6. Explicit dead ends — do not re-attempt any of these without a new reason to believe the prior finding was wrong

- Using `stock_index_membership` (or anything derived from it, like `stock_signals.primary_sector`/
  `rs_vs_sector_today`) as a historical sector label — it only holds 4 weeks; using it as if valid for 2011
  reproduces a survivorship trap that would print a fake Sharpe of 1.5-2.0 (§15i's original framing, before
  the correlation method dissolved the need for it).
- Filtering `bhavcopy_rows` to `series='EQ'` only, for any stock-level return calculation (§15L).
- Using raw `bhavcopy_rows.close` without corporate-action adjustment, for any stock-level return
  calculation (§15O).
- Picking the top decile / most extreme performers within a sector (§15P) — target the calm middle instead.
- A crude sign-flip "reversal/turn" signal (§15Q) — a more precise formulation is untested, this exact one
  is dead.
- Applying the sector layer's hysteresis band directly to the stock layer without re-testing it there
  first (§15j) — it backfired the one time it was tried.
- Widening the stock or sector universe via overlapping/blended index composites to chase more breadth
  (§15N) — measured to lower CAGR, not raise it.
- Hard stop-losses (as opposed to trailing) at either layer (§15M, §15N) — consistently worse; a hard-
  stopped position cannot participate in its own recovery.
- Treating a "vanish" from the price history as a death without checking whether the symbol reappears in a
  different series or after a gap (§15L) — 84%+ of naive "deaths" in this dataset were not deaths.
- `company_about.screener_industry` as a data source for anything new (Guardrail #8).

---

## 7. Deliverables expected back

1. A single, self-contained, reproducible module under `research/explosive_moves/`, following this
   project's established shape: `exec`s the validated V24 engine rather than re-deriving it; self-gates on
   reproducing the cited numbers in §3.1 before trusting anything new; stdlib-only; reads the real
   production `data/hermes.db` read-only (no scratch extracts as the final word — a dev-database sanity run
   is fine, but the reported numbers should come from the real DB).
2. An honest verdict — REJECT or a genuinely qualified survival, either is acceptable, neither should be
   asserted without the significance pass in §5.
3. A retraction banner on ledger `docs/strategy-ledger.md` §**2026-07-15l** (the D141 finding), following
   the exact template already used at §15O for §15j/§15k/§15L/§15M — state what was wrong (the two data
   bugs), what if anything survives directionally, and point at the corrected result.
4. Documentation in the same four places every other finding in this repo lands: a new ledger section
   (next free date-letter — check `docs/strategy-ledger.md` for the current highest letter under
   `2026-07-15` before picking one; there have been multiple same-day collisions already, see §15j/§15L
   above for the resolution pattern), a `PROJECT_STATE.md` decision-log entry (next free D-number), the
   canonical page `docs/strategies/sector-rotation.md` §9 #1 (superseding its "first-run banner" once this
   lands), and a `docs/NEXT-SESSION-CARRYFORWARD.md` update — **note that this file currently does not yet
   reflect ANY of §15j through §15Q or the classification breakthrough; that synthesis is itself owed and
   your commit would be doing it for the first time**, not just adding to it.
5. If genuinely useful and small: the estate-wide TR-benchmark re-cut and the true-risk-free-rate re-cut
   are both still owed (D139/D142) and would sharpen every number in this document, but they are **not**
   blocking — every comparison above is on a consistent, if not "true Sharpe," basis, and D142 already
   established that no verdict moves once that re-cut eventually happens.

---

## 8. One last thing, for calibration

This document exists because two things happened in parallel on the same day: a careful, honest research
arc found and fixed three real data bugs and one real conceptual bug (volatility drag), and a separate,
faster attempt (mine, §2026-07-15l) built a working end-to-end simulation on data that turned out to be
broken in the same ways. **Both were necessary.** The fast attempt proved the two-step architecture is
buildable and gave real, if now-suspect, numbers to react to; the careful arc found out *why* the naive
version of it can't work and exactly what a version that could work needs to contain. Do not repeat either
mistake alone — build carefully, on the corrected data and the validated mechanism, and actually run it to
a real, reproducible number, the way `sector_stock_book_adj.py` did honestly when it said "inconclusive"
instead of overclaiming a −81% drawdown as the final word.
