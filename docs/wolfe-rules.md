# Wolfe Wave — Rules of Record

> The canonical, checkable list of Wolfe-wave rules, in two tiers:
>
> - **§ A — BASE** — confirmed, closed, and **DEPLOYED** (the "base" checkpoint). The geometry. **Non-negotiable.**
> - **§ B — ADVANCED** — the quality / ranking layer agreed in planning (2026-06-25). **NOT yet implemented.**
>
> The ADVANCED tier is **purely additive** — it strengthens *which* waves surface and *how they rank/qualify*. It **never alters** a single BASE geometry rule.
>
> **Revert point:** "base" = `*.bak-base` on the VPS (pre point-5-shift). Current deployed = base **+** the point-5 shift (A4). Everything in §B is design-only until built and signed off.

---

## § A — BASE rules (confirmed · closed · DEPLOYED)

### A1 · Convention (pivots in time order)
- **BEAR (sell):** `H, L, H, L` — point 1 is a **HIGH**.
- **BULL (buy):** `L, H, L, H` — point 1 is a **LOW**.

### A2 · Point placement
| | **BEAR** | **BULL** |
|---|---|---|
| 2 vs 1 | 2 **below** 1 | 2 **above** 1 |
| 3 vs 1 | 3 **above** 1 | 3 **below** 1 |
| 4 | between 2 & 3 — **higher low** than 2, below 3 | between 3 & 2 — **lower high** than 2, above 3 |
| 5 | above 3 **and** crosses **up** through the extended 1-3 line | below 3 **and** crosses **down** through the extended 1-3 line |

### A3 · Distance rule
- **leg 1-2 ≥ leg 3-4** in **price** height. Both directions. (A contracting wedge; ratio leg34/leg12 ≤ 1.0, small lower floor.)

### A4 · Point 5
- Confirmed only when price **both** breaks beyond point 3 (a lower low / higher high) **and** crosses the extended 1-3 line.
- **Shifts** to the deepest overshoot reached **until the EPA (1-4) line is touched**, then locks.
- *(Placeholder: a 4× span scan-cap currently bounds the never-touched case — to be replaced by B2.)*

### A5 · Fib method
- Two **extension fans**, one per thrust leg: leg 1-2 projected **beyond point 1**, leg 3-4 **beyond point 3**, toward the overshoot.
- **Extension ratios only:** `1.272, 1.414, 1.618, 2.618, 3.618, 4.236, 4.618`. (No retracements; no 2.0.)
- **Confluence zone** = where a leg-1-2 level coincides with a leg-3-4 level. **Validated: PARAS 2.618 ∩ 2.618 = 1226.2.**

### A6 · EPA
- The 1-4 line. Drawn **only after point 5 is confirmed**. Runs to the chart's **right edge**.

### A7 · Display
- **Candles only** · **one wave at a time** · **Prediction / Completed** sections with **◄ / ►** timeline nav · zone bands = soft translucent **green (bull) / red (bear)**.

---

## § B — ADVANCED rules (agreed 2026-06-25 · NOT yet built · all tunable)

> Additive only. Strengthens detection coverage + ranking + entry-qualification. **Never** changes § A.

### B1 · Pivot sourcing (surfaces missed waves + enables quality)
| Point | Minimum allowed | Better → Best |
|---|---|---|
| **1** | candle **low** (bull) / **high** (bear) — *lowest* | 2-fractal → 5-fractal → **10-fractal** |
| **2, 3, 4** | **≥ 2-fractal** (never just a candle) | 5-fractal → **10-fractal** |
| **5** | candle extreme only — **no fractal gate** (entry timeliness) | — |

*Fractal level: candle = 0, then 2 / 5 / 10. We do **not** use 20 or 30.*

### B2 · 4.618 entry-qualification — **SCREENER ONLY, never removed from the chart**
- If point 5 pierces **below both** legs' 4.618 (bull; **above both** for bear) **and** price has **not returned** into the 4.618 zone → flag **"not entry-qualified"** until it returns. The user still sees the wave on the chart; only the scanner withholds it.

### B3 · Quality ranking components
| # | Component | Computed from | Points |
|---|---|---|---|
| **A** | Point-1 strength *(separate rating; ×2 in the score)* | point 1 fractal level | 0/1/2/3 → **×2 = 0–6** |
| **B** | Structure strength | **average** fractal of points 2, 3, 4 | 1–3 |
| **C** | Point-5 placement | distance to nearest strong fib zone | 0–3 |
| **F** | Zone narrowness | the confluence gap | 1–3 |
| **D** | Max upside % | point 5 → EPA *(buckets below)* | 0–3 |
| **I** | RSI divergence at point 5 | price vs RSI(14) | 0 or 2 |
| **G** | Zone has 4.618 *(wild card)* | zone composition | 1 or 2 |
| **H** | EPA line-touches *(wild card)* | candle hi/lo on the 1-4 line, regions 1-2 & 2-3 | 0 / 1 / 2 |

**C · Point-5 placement** — ≤ 0.1% (touching, buffered) = **3** · 0.1–0.5% = 2 · 0.5–1.5% = 1 · > 1.5% / none = 0
**F · Zone narrowness** — ≤ 0.6% = **3** · 0.6–1.2% = 2 · 1.2–2% = 1  *(⇒ the confluence finder must widen its tolerance 0.6% → 2%)*
**G · Zone has 4.618** — includes a 4.618 (of *either* leg) = **2** · otherwise = **1**
**H · EPA line-touches** — count candle highs/lows sitting on the 1-4 line (within **0.1%** of the line) in the **1→2** and **2→3** legs only: 0 touches = **0** · 1–2 = **1** · ≥ 3 = **2**
**I · RSI divergence at point 5** — price prints a new extreme but **RSI(14) does not** (bull: lower-low price + higher-low RSI · bear: higher-high price + lower-high RSI). **Present = +2 · none = 0** (binary). A momentum-divergence confirmation that lifts the reversal's profitability.

**D · Max upside %** — < 10% = **0** · 10–20% = **1** · 20–35% = **2** · > 35% = **3**

**Quality score = (A×2) + B + C + F + G + H + I + D** — a plain **points sum** (≈ 3–24), higher = the better pick. **Point 1 is also shown as its own separate "start" rating** (the ×2 is its high-significance weight). Point 1 is never averaged into B; point 5 is never scored on a fractal (only C / G / H placement). No weighted-0-100 blend, no freshness.

**Freshness is NOT a rank dimension** — a wave's quality doesn't change because point 5 moved today vs last week. If useful at all, freshness becomes a *scanner* "new today" flag, kept separate from the quality rank. (The old generic R:R / "live extras" are superseded by A–H.)

### B4 · Resolved (2026-06-25)
- **Touch tolerance** for B3.H = **0.1% of the line.** ✅
- **Scoring = plain points SUM** — (A×2) + B + C + F + G + H + I + D; point 1 also a separate "start" rating; RSI div = +2 binary; max-upside % bucketed 0–3. ✅
- **Freshness** dropped from the rank (it's timing, not quality). ✅

### B5 · Trade management (entry · stop · targets — for the screener & backtest)
- **Entry:** at the point-5 fib confluence zone.
- **Stop loss:** the **far edge of the nearest fib zone** — its **low** (bull) / **high** (bear). If price crosses it the trade is gone — **unless a next confluence zone sits within ~1.5% (≈ 1 ATR)**, in which case the SL moves to *that* zone's far edge (the "broken band → reversal at the next band" allowance). Tunable.
- **Target 1:** the **0.618 ∩ 0.618 confluence** (leg 1-2's 0.618 coinciding with leg 3-4's), like every other zone in the method.
- **Final target:** the **EPA (1-4) line.**

---

## § C — As-of-date querying & backtesting (point-in-time — MANDATORY)

**Every query / scan takes an *as-of date* (default = today).** Running it **"as on 2 days back"** — or any past date — must return **exactly what was visible *then***: same code path, the data simply truncated to **bars ≤ as-of**, no look-ahead. (This one capability powers both ad-hoc historical review *and* the backtest.)

- **PIT applies across the whole pipeline** — detection, **point 5** (the deepest overshoot *as of that date* — may be shallower than today's, since point 5 shifts forward over time), zones, ranks, SL & targets — all from bars ≤ as-of only.
- **Testable invariant:** the result as-of *t* is **identical whether or not bars after *t* exist** in the DB.
- **Naturally PIT-honest by design:** a fractal-N pivot confirms only **N bars after** its candle (points 1-4 carry their real delay); point 5 = the live candle extreme (seen immediately — exactly why it has no fractal gate).
- **Backtest** = replay each date through the as-of query, rank, and measure the forward outcome (reversal? reached the zones / EPA / stop?). **Survivorship-aware.** The strategy stays **descriptive-only until this backtest earns a verdict.**

---

## Build status
- **§ A** — deployed on the VPS; isolated files committed-pending. Revert = `*.bak-base`.
- **§ B** — **fully specified (all items locked 2026-06-25)**; surgical build **not started**, awaiting the step-1 spec sign-off.

*(Companion to `docs/wolfe-wave-design.md` (intent/history) and `docs/wolfe-NEXT-SESSION.md` (session run-book). This file is the precise rule reference.)*
