# Sector Rotation (RS-weighted) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **RESEARCH — CONDITIONAL.** Two recorded configurations: **V8** = the FROZEN champion (Ramana-ratified base; smart-beta tilt, beats passive on Sharpe/drawdown, trails on wealth) and **V17** = the champion-CANDIDATE (V8 + defensive residual fill; beats the like-for-like Nifty 500 on wealth AND Sharpe AND drawdown; pending ratification + a total-return re-cut). Long-only; the short/F&O leg is REJECTED (ledger). Not yet a live product surface. · **Governing record:** [strategy-ledger.md](../strategy-ledger.md) §§ Study 2026-07-15 / 2026-07-15b / 2026-07-15c.
> **Origin:** 🧑 RAMANA (the strategy concept and every lever: RS-weighted multi-sector longs, balanced newcomers, own-peak-RS taper, stretch/σ taper, RSI-of-RS overbought exit, reduce-and-wait cash discipline) + 🏠 HOUSE implementation & falsification harness. See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference. Result numbers live ONLY in [strategy-ledger.md](../strategy-ledger.md); code + exact constants live in `research/explosive_moves/sector_rotation.py` (V1 round) · `sector_rotation_exp.py` (V2–V8 ablation) · `sector_rotation_exp2.py` (V9–V17 round + the V17 reference implementation) · `sector_rotation_stats.py` (dated stats/t-stats). This page states the RULESET (definitional) and links the rest.

**One-line definition:** a long-only, low-churn sector-rotation strategy — every NSE sectoral index beating Nifty 500 on trailing relative strength is held (equal-weighted, capped), entries gated on an RSI-green recovery, weights tapered off as a sector approaches its OWN historical RS peak / stretch / RS-overbought, and (V17) the un-invested residual parked in a Nifty index ETF while the index is healthy, in cash when it is not.

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

## 7. Terminology canon

- **V8** — the FROZEN champion: quarterly RS rotation + RSI-green entry + hysteresis + 30% cap + BAL equal-weights + the three tapers (RSPK·STR·RSIRS); residual in cash.
- **V17** — V8 + the **defensive residual fill** (residual→index ETF above the 200DMA, →cash below). The champion-candidate.
- **RSI-green** — RSI(14) ≥ 50 and not falling vs ~1 month ago; an ENTRY gate only, never an exit.
- **Hysteresis band (±8%)** — enter above +8% RS, hold until −8%; the churn governor.
- **RS-peak taper / stretch taper / RSI-of-RS** — the three exhaustion levers (own-history percentile, own-σ stretch, RS-line RSI 70/80). Distinguish **RSI of price** (entry gate) from **RSI of the RS line** (exhaustion exit).
- **Residual sleeve** — the un-invested fraction created by the 30% cap under narrow breadth; V17's productive-but-defensive parking.
- Do NOT confuse this strategy with the descriptive **RS suite** ([relative-strength.md](relative-strength.md) — RRG/rotation lenses, no portfolio) or the **Momentum/RISKADJ** stock engine ([momentum-riskadj.md](momentum-riskadj.md)).

## 8. Decision & session history

- **2026-07-15 (S-rotation lane)** — Ramana directs the strategy (multi-sector RS weights, F&O shorts to test, RSI-green entries, ≤40 stocks eventually, backtest-derived risk controls). V1 sector-index round: quarterly+RSI-gate+hysteresis champion; **short leg rejected**; ledger Study 2026-07-15.
- **2026-07-15b** — Ramana freezes the champion and dictates the improvement levers (balanced newcomers, own-peak-RS taper, stretch/σ taper, RSI-of-RS, oldest-data mandate). Incremental ablation V2–V8 → **V8 = BAL+RSPK+STR+RSIRS** ratified as the frozen working config.
- **2026-07-15c** — the return-gap round (dated stats first: cash drag, alpha t 1.45 n.s., COVID not GFC is V8's MaxDD). V9–V17 → **V17 defensive fill = champion-candidate**; book-level kill, asym monthly-risk and monthly cadence all REJECTED. This page created (V8 + V17 recorded canonically).

## 9. Open items / frozen work

- **Ramana's ratification of V17** as champion (V8 stays the frozen base either way).
- **TR-benchmark re-cut + V17 significance pass** — the price-vs-TR caveat is the biggest open honesty item.
- **V2 constituent expression** — the ≤40-stock version (top-RS stocks inside qualifying sectors, sector-RS × stock-RS weights, per-sector stops) — where the stock-selection edge gets tested; then `/dash/model-portfolios` integration if it survives.
- **Fresh-period / walk-forward confirmation** of the V17 lever specifically (selection-deflation guard).

## 10. Sources of truth

- Results (single source): [strategy-ledger.md](../strategy-ledger.md) §§ 2026-07-15 / 15b / 15c.
- Code (constants canonical): `research/explosive_moves/sector_rotation_exp2.py` (+ `sector_rotation.py`, `sector_rotation_exp.py`, `sector_rotation_stats.py`).
- Provenance: [origins.md](origins.md). Siblings: [relative-strength.md](relative-strength.md) · [momentum-riskadj.md](momentum-riskadj.md) (the factor doctrine + benchmarks).

## Maintenance

Any change to the ruleset (§3), a new round's verdict, or the V17 ratification updates **this page + the ledger in the same commit** (strategy-docs coverage gate enforces serving/matrix/origin). V8 stays FROZEN as recorded — refinements are new V-numbers beside it, never edits to it. The §4 fences (short leg, monthly cadence, book-level kill, smart-beta-not-alpha) may not be softened without a new recorded study that beats the ledger numbers.
