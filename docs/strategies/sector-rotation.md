# Sector Rotation (RS-weighted) — Canonical Reference

> ## 🔴 SCOPE — READ BEFORE ANY NUMBER ON THIS PAGE
>
> **This strategy is HALF-BUILT. It selects SECTORS. It does NOT pick STOCKS.**
>
> Every V-number (V8…V32) and every headline stat (Sharpe 0.91 · α +7.1%/yr · ₹1 Cr → ₹30.35 Cr) measures
> the **sector-selection layer ONLY** — a book that holds *sector indices themselves* (Nifty Auto, Nifty IT, …),
> weighted by RS. The engine reads exactly one table, `index_rows`. It contains **zero stock symbols** — no
> `stock_signals`, no bhav copy, no symbol column. Verify in 5 seconds:
> `grep -ciE "stock_signals|bhav|symbol" research/explosive_moves/sector_rotation_v24_final.py` → **0**.
>
> **Ramana's brief was two halves** (2026-07-15): ① find every sector beating the benchmark, ② **pick the
> top-RS STOCKS driving those sectors** (≤40 names, sector-RS × stock-RS weights, per-sector stops). **Only
> half ① exists.** Half ② — the V2 constituent expression, §9 — is **NOT BUILT**, and is where the actual
> stock-selection edge would be tested. It has never been measured.
>
> **⚠ The index expression may not even be tradeable** (see §6 *Instrument reality*): §3-F assumes the sector
> legs are bought as "liquid sector ETFs/index futures", but that was **asserted, never verified**. Several of
> the 16 sectors (Media, Realty, Consumer Durables, Infrastructure, Oil & Gas) have **no liquid ETF or futures
> instrument in India**. An unknown share of the 0.91 Sharpe may be **unbuyable in index form**. This inverts
> the priority: the constituent build is not a phase-2 nicety — for much of the book, **buying the underlying
> stocks is the only executable expression**, and pricing it as an ETF book understates its real cost.
>
> **Do NOT present, quote, or promote any number on this page as a complete strategy result.** It is the
> sector-selection half of an unfinished strategy, priced on instruments that may not exist.
> *(Recorded 2026-07-15h after Ramana caught the gap — the flaw was a FRAMING failure: the limitation was
> buried in §9's open items while the page led with a Sharpe ratio, so it read as finished. Ledger §2026-07-15h.)*

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **RESEARCH — CONDITIONAL · SECTOR-LAYER ONLY (see SCOPE above).** The candidate ladder: **V8** = the FROZEN base (Ramana-ratified; smart-beta tilt) → **V17** = defensive residual fill (recorded candidate) → **V21** = + Next-50 sleeve + recovery-accelerator + inverse-vol (LIVE default on `/dash/sector-rotation`) → **V24** (official shorthand for **V21 + own-percentile RSI-of-RS**, Ramana's naming, 2026-07-15g) = the most-balanced leading candidate (Sharpe 0.91, MaxDD −37.7%, ₹1 Cr → ₹30.35 Cr vs Nifty 500's ₹12.60 Cr / Nifty 100's ₹11.93 Cr / Nifty 50's ₹11.35 Cr) → **V32** (V24 + adaptive hysteresis band) = the wealth-favoring sibling. Long-only; short/F&O leg REJECTED. **The portfolio surface is LIVE** — `/dash/sector-rotation` with `?asof=` time-travel + per-rebalance diffs; still runs V21 pending ratification of V24/V32. · **Governing record:** [strategy-ledger.md](../strategy-ledger.md) §§ 2026-07-15 → 2026-07-15g · D136.
> **Origin:** 🧑 RAMANA (the strategy concept and every lever: RS-weighted multi-sector longs, balanced newcomers, own-peak-RS taper, stretch/σ taper, RSI-of-RS overbought exit, reduce-and-wait cash discipline) + 🏠 HOUSE implementation & falsification harness. See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference. Result numbers live ONLY in [strategy-ledger.md](../strategy-ledger.md); code + exact constants live in `research/explosive_moves/sector_rotation.py` (V1 round) · `sector_rotation_exp.py` (V2–V8 ablation) · `sector_rotation_exp2.py` (V9–V17 round + the V17 reference implementation) · `sector_rotation_stats.py` (dated stats/t-stats). This page states the RULESET (definitional) and links the rest.

**One-line definition:** a long-only, low-churn sector-rotation strategy that **holds the sector INDICES themselves — it does not select stocks** (see SCOPE above; the ≤40-stock constituent layer is unbuilt). Every NSE sectoral index beating Nifty 500 on trailing relative strength is held (equal-weighted, capped), entries gated on an RSI-green recovery, weights tapered off as a sector approaches its OWN historical RS peak / stretch / RS-overbought, and (V17) the un-invested residual parked in a Nifty index ETF while the index is healthy, in cash when it is not.

---

## 1. What it is

Ramana's answer to "don't bet on one top sector or one day's performance": hold the WHOLE set of sectors currently outperforming the index, weight them by relative strength with deliberate balance, enter only on confirmed recovery, and — the part that makes it his — treat a sector's own RS history as its thermometer: as relative strength nears its own past extreme ("the Defence-index lesson"), the position is offloaded gradually rather than ridden over the top. V17 adds the wealth engine the base lacked: idle capital is never left dead — it earns the index while the market is above water and steps aside when it is not.

## 2. Our variation vs. the standard technique

Classic sector rotation picks the single top sector (or top-k by one day/one month) and swaps it wholesale. This strategy departs on Ramana's axes: (a) **breadth, not a winner-take-all** — every index-beating sector is held, equal-weighted with a 30% cap; (b) **hysteresis + quarterly cadence** — a held sector survives until it clearly breaks, so churn stays ~12%/mo (the ledger's momentum-net-of-cost wall is the reason); (c) **self-referential exhaustion tapers** — each sector is measured against its OWN RS-peak/stretch history, never a market-wide constant (the standing no-static-threshold rule); (d) **the residual sleeve** — the cap structurally leaves cash when breadth is narrow; V17 makes that sleeve productive-but-defensive instead of dead.

## 3. How it works — THE COMPLETE V17 RULESET (definitional)

Three sleeves: the **sector book**, the **residual sleeve**, **cash**. Decisions at the first trading day of each month; the sector book rebuilds only on quarter month-starts; the residual sleeve switches monthly.

**A. Universe & data.** The 16 NSE sectoral indices (Auto · Bank · Energy · FMCG · IT · Pharma · Infrastructure · Media · Metal · PSU Bank · Realty · Financial Services · Private Bank · Oil & Gas · Consumer Durables · Healthcare), each joining as its history allows; benchmark = Nifty 500. Daily closes from `index_rows` (primary NSE data, Guardrail #8).

**B. Relative-strength signal.** At decision date *d*: `RS(s) = 126-trading-day return of sector s − 126-day return of Nifty 500` (≈ 6 months; the 3-mo and 12-mo lookbacks tested WORSE — ledger 15/15b).

**C. Membership (quarterly).**
- **Enter** a sector only if `RS > +8%` **and** its price RSI(14) ≥ 50 **and** RSI is not falling vs 21 trading days ago (the "RSI-green" recovery gate — Ramana's proper-entry-signal rule).
- **Hold** an already-held sector while `RS > −8%` (the hysteresis band — "stay while momentum persists"); holds are NOT re-tested on RSI.
- **Exit** when `RS ≤ −8%`.

**D. Weights (quarterly).**
1. **Equal-weight** all qualifying sectors (the balanced-newcomer decision — beats rank-proportional, ledger 15b), then **cap 30%** per sector (over-concentration guard), redistributing to uncapped names.
2. Multiply each sector's weight by three **taper factors** (the gradual-offload machinery):
   - **RS-peak taper (RSPK):** the sector's RS line (sector ÷ Nifty 500 ratio) percentile within its OWN trailing 3 years — above the 85th percentile, weight scales linearly down to a 0.35× floor at the 100th ("each security has its own peak relative strength; offload as it approaches it").
   - **Stretch taper (STR):** z-score of price vs its own 200-day mean — when stretched beyond the reference band (~1.5σ+), same linear taper to 0.35× ("too far from its typical range").
   - **RSI-of-RS exit (RSIRS):** RSI(14) computed ON the RS line — ≥ 70 → halve the weight; ≥ 80 → exit the sector entirely (the overbought-RS quick-exit).
3. Renormalize to 1.0 and re-cap at 30%. The invested fraction is therefore `min(1, 0.30 × #survivors)` — with narrow breadth the book is deliberately part-cash.

**E. Residual sleeve (the V17 rule; checked MONTHLY).** `residual = 1 − invested fraction`. If Nifty 500 closes **≥ its 200-day SMA** at the month-start → the residual is held in a **Nifty index ETF**; if **below** → the residual moves to **cash/liquid fund** and waits. The sector book is NEVER touched by this switch. If no sector qualifies at all, the entire portfolio IS the residual sleeve. *(Why sleeve-only: applied to the whole book, the same 200DMA kill destroyed wealth — V9, ledger 15c. On the sleeve, a false alarm costs one month of index-vs-cash; a true alarm sidesteps the crash.)*

**F. Costs & instruments.** 0.15%/side on every weight change (sector legs = liquid sector ETFs/index futures; sleeve = Nifty ETF ↔ liquid fund); measured one-way turnover ≈ 12.4%/mo. Monthly marks.

**V8 = rules A–D + F only** (residual stays in cash; the frozen champion). Exact constants (126/8%/50/21/30%/756/85th/0.35/70/80/200) are definitional here AND live in code — `research/explosive_moves/sector_rotation_exp2.py` is the reference implementation (`build_v8`, `taper_product`, `kill_on`, mode `DFILL`); on any drift, the code is canonical.

## 4. Status, validation & honesty fence

**CONDITIONAL — not yet a validated standalone alpha; not yet a product surface.** The canonical numbers live in [strategy-ledger.md](../strategy-ledger.md) (Studies 2026-07-15 · 15b · 15c) — headline: V17 beats the like-for-like price-index Nifty 500 on wealth, Sharpe AND max-drawdown simultaneously at ~12%/mo turnover; V8 (frozen) beats it on Sharpe/drawdown but trails on wealth (cash drag; alpha t-stat 1.45 = NOT statistically significant). Binding fences:

- **The short/F&O leg is REJECTED** (every short variant subtracts; shorts fight drift — ledger 15). Long-only.
- **Monthly cadence is REJECTED** (three confirmations: 15 · 15b · 15c) — the quarterly clock + hysteresis IS the cost survival.
- **A book-level 200DMA kill-switch is REJECTED** (V9: wealth collapses on whipsaws; the 200DMA works ONLY on the residual sleeve).
- **V17's caveats are part of its verdict:** H2 (2015→) Sharpe trails the bench's H2; it was the 11th variant of its round (selection deflation); price-index benchmark (dividends excluded on BOTH sides — the delta is fair, absolute CAGRs conservative). Promotion to champion requires Ramana's ratification; promotion to any fundable claim requires the TR-benchmark re-cut + a significance pass + the participation-cost recut.
- Doctrine intact: this is an **enhanced-beta / smart-beta tilt** (the LOWVOL_MOM family), not proof that sector-timing mints standalone alpha.

## 5. Where it lives (code · routes · DB · timers)

- **Portfolio surface (LIVE, S-rotation-e):** `/dash/sector-rotation` (`src/web/sector_rotation_view.py`) — the V17 book with **`?asof=` time-travel** (◀/▶ rebalance steppers + year strip), the **rebalance diff** (entered · exited · re-weighted) per quarter, analytics-to-date (NAV× · CAGR · Sharpe · MaxDD vs Nifty 500 to the same date), the residual-sleeve regime (INDEX/CASH), a dual NAV sparkline, and server-side CSV (`?fmt=csv`). Registered as a Strategies lens; every strategy-ref page now carries a "live surface" hand-off strip (`strategies_view._SURFACE`).
- **Engine:** `src/automation/sector_book.py` — materialises the frozen V17 config into the bounded tables **`sector_rotation_book`** (quarterly weights) + **`sector_rotation_nav`** (monthly NAV/regime/turnover); own schema, `db.py` untouched. CLI `--build` / clock-gated `--refresh` (nightly line in the bhavcopy `10-signals.conf` chain; rebuilds only when a new quarter month appears) / `--selftest`.
- **Research modules (the spec-of-record + falsification record):** `research/explosive_moves/sector_rotation.py` · `sector_rotation_exp.py` (V2–V8 ablation) · `sector_rotation_exp2.py` (V9–V17; the DFILL mode = V17 reference) · `sector_rotation_stats.py` (dated stats/t-stats). Reproduce read-only: `cd /opt/hermes && .venv/bin/python research/explosive_moves/sector_rotation_exp2.py data/hermes.db`.

## 6. Data & provenance

NSE index closes (`index_rows`, 205 indices 2004→present; primary source, Guardrail #8-clean). Point-in-time honest: every signal at date *d* uses closes ≤ *d*; entries earn the NEXT month's return; sectors join the universe only once their own history supports the signal (no backfilled hindsight membership). Price indices, not total-return — disclosed wherever numbers are shown.

**Index closes are the ONLY input.** No stock-level data enters this strategy at any point — see the SCOPE
banner. The book's holdings are index names, not symbols.

### 6-bis. Instrument reality — ⚠ UNVERIFIED, and it is load-bearing

§3-F prices the sector legs as **"liquid sector ETFs/index futures" at 0.15%/side**. That instrument claim was
**asserted, never checked against actual Indian market instruments** — it is the weakest assumption in the whole
construct, and every V-number inherits it:

- **Plausibly tradeable as an index:** Nifty Bank, Nifty IT, Nifty Pharma, Nifty PSU Bank, Nifty Auto,
  Nifty Financial Services, Nifty Private Bank, Nifty Healthcare *(ETF/futures exist — liquidity still unverified,
  and 0.15%/side may be optimistic for the thinner ones)*.
- **No liquid index instrument known:** **Nifty Media · Nifty Realty · Nifty Consumer Durables ·
  Nifty Infrastructure · Nifty Oil & Gas · Nifty Metal (thin)** — roughly **6 of 16 sectors**.

**Consequence:** an unknown fraction of the reported edge sits in legs that **cannot be bought as an index at
the modelled cost, or at all**. Two live implications, both unmeasured:
1. **The headline stats are optimistic by an unquantified amount** — real slippage on thin/absent instruments
   is not in the 0.15%.
2. **It re-prioritises the constituent build.** If a qualifying sector has no ETF, the only way to express it is
   **buying its constituent stocks** — so §9's "V2 constituent expression" is not an enhancement to a working
   strategy, it is **the execution path for ~⅜ of the book**.

**Owed work (blocking any claim of tradeability):** enumerate the actual NSE/BSE ETF + futures instruments per
sector with real ADV, re-cut costs per-leg from measured spreads instead of one flat 0.15%, and re-run the
ladder. Until then, treat every number as an **upper bound on a paper portfolio**.

## 7. Terminology canon

- **V8** — the FROZEN champion: quarterly RS rotation + RSI-green entry + hysteresis + 30% cap + BAL equal-weights + the three tapers (RSPK·STR·RSIRS); residual in cash.
- **V17** — V8 + the **defensive residual fill** (residual→index ETF above the 200DMA, →cash below). The recorded candidate.
- **V21** — V17 + Next-50 sleeve + recovery-accelerator (reclaim quarter → entry band 8%→0) + inverse-vol weights. **The LIVE default on `/dash/sector-rotation` today.**
- **V24** — **official shorthand (Ramana, 2026-07-15g) for the FULL combination V21 + own-percentile RSI-of-RS** (that sector's own trailing-756d distribution, 85th trims/95th exits, replacing the fixed 70/80 — not the bare lever in isolation). Sharpe 0.91 (0.92/0.91 — the most half-balanced construct recorded), MaxDD −37.7%, ₹1 Cr → ₹30.35 Cr. The leading candidate by robustness.
- **V32** — V24 + the **adaptive hysteresis band** (±band sized to that sector's own trailing RS-line volatility, replacing the fixed ±8%). Sharpe 0.90 (0.95/0.84), ₹1 Cr → ₹31.15 Cr. The leading candidate by wealth/CAGR — trades a little half-consistency for it.
- **RSI-green** — RSI(14) ≥ 50 and not falling vs ~1 month ago; an ENTRY gate only, never an exit.
- **Hysteresis band (±8%)** — enter above +8% RS, hold until −8%; the churn governor. (V32 replaces the fixed number with a per-sector adaptive one — see above.)
- **RS-peak taper / stretch taper / RSI-of-RS** — the three exhaustion levers (own-history percentile, own-σ stretch, RS-line RSI). V8/V17/V21 use RSI-of-RS with the fixed 70/80 line; **V24/V32 use that sector's own trailing percentile instead** (85th/95th). Distinguish **RSI of price** (entry gate, always fixed 50) from **RSI of the RS line** (exhaustion exit, fixed in V8-V21 / own-percentile in V24-V32).
- **Residual sleeve** — the un-invested fraction created by the 30% cap under narrow breadth; the productive-but-defensive parking every V17+ config uses.
- Do NOT confuse this strategy with the descriptive **RS suite** ([relative-strength.md](relative-strength.md) — RRG/rotation lenses, no portfolio) or the **Momentum/RISKADJ** stock engine ([momentum-riskadj.md](momentum-riskadj.md)).

## 8. Decision & session history

- **2026-07-15 (S-rotation lane)** — Ramana directs the strategy (multi-sector RS weights, F&O shorts to test, RSI-green entries, ≤40 stocks eventually, backtest-derived risk controls). V1 sector-index round: quarterly+RSI-gate+hysteresis champion; **short leg rejected**; ledger Study 2026-07-15.
- **2026-07-15b** — Ramana freezes the champion and dictates the improvement levers (balanced newcomers, own-peak-RS taper, stretch/σ taper, RSI-of-RS, oldest-data mandate). Incremental ablation V2–V8 → **V8 = BAL+RSPK+STR+RSIRS** ratified as the frozen working config.
- **2026-07-15c** — the return-gap round (dated stats first: cash drag, alpha t 1.45 n.s., COVID not GFC is V8's MaxDD). V9–V17 → **V17 defensive fill = champion-candidate**; book-level kill, asym monthly-risk and monthly cadence all REJECTED. This page created (V8 + V17 recorded canonically).

## 9. Open items / frozen work

- **★★ Two new leading candidates (ledger 2026-07-15f), both on top of V21 — pending Ramana's ratification:**
  - **V21+V24 (own-percentile RSI-of-RS)**: Sharpe 0.91 (0.92/0.91 — the most half-consistent construct in the
    whole project), MaxDD −37.7% (best recorded), α +7.1%/yr (best recorded), ₹1 Cr → 30.35.
  - **V32 = V21+V24+V22 (own-percentile RSIRS + adaptive hysteresis band)**: Sharpe 0.90 (0.95/0.84), MaxDD −37.9%,
    α +6.5%/yr, ₹1 Cr → 31.15 (best recorded wealth/CAGR).
  - These are a genuine trade-off, not a strict ranking — V24-alone is more robust/balanced, V32 trades a little
    half-consistency for more wealth. **The live `/dash/sector-rotation` engine intentionally still runs V21**
    until one is ratified.
- **A real negative-interaction lesson (2026-07-15f):** V26 (persistence) is a clean win ALONE but HURTS when
  combined with V24 — its "wait 2 quarters" delays V24's faster reaction. Individually-validated levers do not
  always combine additively; every combination needs its own test.
### 🔴 #1 — THE CONSTITUENT BUILD (the missing half of the brief; was mis-filed as a nicety until 2026-07-15h)

**Status: NOT BUILT. Never measured. This is the strategy Ramana actually asked for.** The sector ladder
(V8…V32) answers only "WHICH SECTORS" — a paper book of index legs, ~⅜ of which have no buyable instrument
(§6-bis). The stock layer answers "WHICH STOCKS", and is both the untested edge **and** the execution path.

**Spec (Ramana's original brief, 2026-07-15):** take **V24's qualifying sectors** as the sector layer
(Ramana's designation, 2026-07-15h) → inside each, rank constituents by **stock-level RS** → hold the top
names up to a **≤40-stock book** → weight by **sector-RS × stock-RS** → **per-sector stops** →
carry the same RSI-green entry gate + hysteresis + own-percentile tapers down to the stock leg.
Reuse the existing `stock_signals` RS columns (built; do not rebuild). Then `/dash/model-portfolios`
integration **only if it survives** its own falsification round.

**The honest prior — this may fail, and the ledger says so:** [momentum-riskadj.md](momentum-riskadj.md) +
ledger's momentum-net-of-cost wall record that **stock-level momentum selection is BETA, not skill (t=1.99)**,
and only **LOWVOL_MOM quarterly large-cap** cleared the fundable bar (1.02 @ ₹50cr). Stock legs cost far more
than index legs. **A constituent build that merely matches the index book is a REJECTION**, not a result —
it must beat the sector ladder *net of realistic stock-level costs* to earn anything. Pre-register that bar
before running it, per the standing failure-ledger discipline.

### #2 — the rigor items on the sector layer (do not skip because #1 is more exciting)

- **Instrument/tradeability audit (§6-bis)** — enumerate real ETF/futures per sector with ADV, per-leg costs
  from measured spreads, re-cut the ladder. **Blocks any tradeability claim.** Partially subsumed by #1: sectors
  with no instrument simply *become* stock legs.
- **TR-benchmark re-cut + significance pass — the HIGHEST-priority rigor item** (FOUR rounds of selection on one
  window; no TRI series in `index_rows` — needs an NSE Total-Returns ingest).
- **V24 designated** by Ramana (2026-07-15h) as the sector layer to carry forward. Note this is a designation of
  *which config the constituent build sits on*, **not** a promotion to a tradeable book — the live
  `/dash/sector-rotation` stays on V21, and no config graduates while #1 and the rigor items are open.
- **Rejected, with numbers (2026-07-15f): longer RSI window, dual-benchmark confirmation, the 55/45 regime-band
  (confirms the single-sector Defence diagnostic), direction-of-trend entry/exit, and book-level vol-targeting
  (worst drawdown blowup in the batch — CAGR up but MaxDD to −50.8%/−53.6%, fails the "keep drawdown in check"
  bar). Size-segment satellites = marginal, turnover roughly offsets the gain.**

## 10. Sources of truth

- Results (single source): [strategy-ledger.md](../strategy-ledger.md) §§ 2026-07-15 / 15b / 15c.
- Code (constants canonical): `research/explosive_moves/sector_rotation_exp2.py` (+ `sector_rotation.py`, `sector_rotation_exp.py`, `sector_rotation_stats.py`).
- Provenance: [origins.md](origins.md). Siblings: [relative-strength.md](relative-strength.md) · [momentum-riskadj.md](momentum-riskadj.md) (the factor doctrine + benchmarks).

## Maintenance

Any change to the ruleset (§3), a new round's verdict, or the V17 ratification updates **this page + the ledger in the same commit** (strategy-docs coverage gate enforces serving/matrix/origin). V8 stays FROZEN as recorded — refinements are new V-numbers beside it, never edits to it. The §4 fences (short leg, monthly cadence, book-level kill, smart-beta-not-alpha) may not be softened without a new recorded study that beats the ledger numbers.
