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
- **✅ BUILT (D100, 2026-07-10, Ramana: "approve R7, go ahead"):** `wolfe.entry_qualified()` — pierced = point-5 beyond BOTH 4.618s (bull below min / bear above max); returned = a CLOSE back into the [min-4.618, max-4.618] band after point 5 (PIT). Withheld **visibly + counted** on `/dash/wolfe/scan` (both the winner table and the structure watch) with a show/hide toggle — never silent, never on the chart/walk.

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

## § D — Lifecycle & actionability (Ramana, 2026-07-10 — recorded verbatim, derived states below)

**His words (S89 session, condensed but verbatim):** *"We are trying to predict the next Wolf wave… Once point 5 has formed, we can see where the wave stands. If a point is completed and the EPA line has already been touched, then after forming the five points, any price that touches the EPA line does not create a new actionable point — it serves only as a reference. Useful for validation (showing which points are completed) but not for taking action. I gain no benefit from continuously monitoring it. **Open items, however, are truly actionable, and they are my primary concern. That is my actual need.** The first component still being formed is also actionable: I can ride the tide from point 4 to point 5, using a stop-loss based on point 4… Point 5 will eventually cross point 3, and my position may move beyond that. In a bullish Wolf wave, point 5 can dip below point 3 and may even reach the relevant Fibonacci ratios within the narrow confluence zones."*

### The lifecycle (derived — every confirmed structure is in exactly one state)

| State | Definition | Actionable? | The play |
|---|---|---|---|
| **FORMING** | points 1–4 locked (§A), point 5 not printed | **YES — play A ("ride to 5")** | ride the 4→5 leg (bull: down / bear: up); **SL = the point-4 breach level** (§A already voids the wave on a 4-breach); target = the predicted-5 fib confluence zone(s). Bull note: 5 can dip below 3, potentially to the narrow confluence zones. |
| **OPEN** | point 5 printed; the EPA (1-4) line **not yet touched** after 5 | **YES — play B ("ride to EPA") — his PRIMARY need** | the reversal from 5 toward the EPA target; milestone: the move crossing the point-3 level ("point 5 will eventually cross point 3, and my position may move beyond that"). |
| **CLOSED** | EPA touched at any bar after point 5 | **NO — reference/validation only** | proves the method on that wave ("shows which points are completed"); belongs on reading surfaces (walk/history), never on actionable queues. Later EPA touches create no new action. |

- **`epa_touch` is PIT-honest**: first bar t > point-5 where bull high ≥ EPA(t) / bear low ≤ EPA(t) — computable from bars ≤ as-of, replayable per §C.
- **State ≠ age.** Age (bars since p5) is a *recency* field (D99 ranking); OPEN/CLOSED is the *actionability* state. An OPEN wave 40 bars old is actionable; a CLOSED wave 3 bars old is not. Actionable surfaces must filter by STATE (age remains a visible column + rank input).
- **Descriptive-only stands (§C gate):** "actionable" here = *worth the analyst's attention*, never a machine buy/sell. Ledger: the raw lens is falsified as a trade signal (median −2% net, tail game); the winner profile (+2.14% OOS) is the only validated selection edge and it, too, stays a scanner.

### ✅ CLARIFIED by Ramana (2026-07-10, same day) — his answers, recorded verbatim-in-substance
1. **The "cannot fall below point 2 / point 3" bound = the POINT-4 channel rule, already in §A.** His words: *"In a bullish Wolf wave, point 4 must lie between points 2 and 3; it cannot exceed point 2… If point 4 moves beyond point 2 in a bullish Wolf wave, or falls below point 2 in a bearish wave, the wave becomes invalid."* This is exactly the deployed `_classify` gate (bull 4 ≤ 2 · bear 4 ≥ 2 · plus the point-4 breach void). **No new rule; no code change; his instruction: "the existing rules are working well; the counts 1–5 are accurate… do not modify the wave count."** §A stays locked.
2. **His state labels refined:** *"forming"* = the formation stage (points printing). *"Open"* = the wave *"has progressed through points 1, 2, 3, 4 and is approaching point 5"* — i.e. **OPEN spans BOTH actionable phases**: *open-approaching-5* (structure locked, riding 4→5) and *open-riding-to-EPA* (5 printed, EPA uncrossed). CLOSED = the EPA line crossed after 5. Point-5's *"proximity to the Fibonacci levels, expressed as a percentage, indicates the strength of a potential recovery or further decline."* (The table above keeps the same mechanics; the two actionable rows are the two phases of HIS "open".)
3. **EPA state = the LINE FORMULA, not bar-by-bar monitoring.** His directive: the EPA is the linear 1→4 extension past point 4; after 5 forms, *"see whether the price RANGE intersects the EPA line — it doesn't have to be an exact touch; a crossing fulfils the rule… you don't have to monitor every bar."* Implementation contract: state is PERSISTED once known; establishing a historical wave's state needs ONE pass from point 5 (unavoidable — the answer lives in those bars), after which the nightly update checks only the NEW bar's range against `epa(t)` (bull: high ≥ line · bear: low ≤ line — crossing-inclusive by inequality). Event-driven, never a rescan.
4. **NEW method detail (recorded, NOT built — no §B change):** *"Point 4 is considered strong when the Fibonacci ratios between points 1-2 and points 2-3 create confluence zones. The intersection of these zones determines the location of point 4."* A point-4-strength descriptor via legs **1-2 ∩ 2-3** confluence (note: different leg pair than the point-5 zones' 1-2 ∩ 3-4). Candidate future chip on forming waves; needs his worked example before any build.
5. **Liveness resolved WITHOUT a cutoff:** he declined an artificial bound (*"determining whether the line is still open or has been completed is sufficient"*). The OPEN queue therefore filters by STATE only and lets the D99 attention rank order it (zombies decay to the bottom; the counted default-slice + show-all keeps the page usable) — ranks order, filters declare, nothing hides.

---

## Build status
- **§ A** — deployed on the VPS; isolated files committed. Revert = git `74faeee` or VPS `*.bak-base` / `*.bak-port`.
- **§ B** — **BUILT + DEPLOYED + BROWSER-VERIFIED 2026-06-25 (the port).** `detect_waves` now UNIONS the base ATR-zigzag pivots with multi-degree Williams fractals (degrees 2/5/10/20/30) — additive, never loses a base wave (Ramana's call) — validated by the UNCHANGED §A `_classify`; every wave carries the §B `score()` points-sum. Distance floor `sym_lo` 0.5→**0.2**; `fib_zones` confluence tolerance 0.6%→**2%** (so narrowness F can bucket); dedupe keeps the higher-§B copy; the ◄/► candle-overlay walk capped to the **top-40 by quality** (full list stays on `/dash/wolfe`). Both surfaces lead with the wave (dir · status · pt4 date · ₹ zone), show **Q** + the `p1·B·C·F·G·H·I·D` breakdown (chips on hover for the list). Verified live on candles: RELIANCE incl. the base-MISSED **Nov-2022** `frac@5` wave (rank ~6/37 in the walk, exact pivots) + PARAS's validated monthly bear preserved; zero console errors. Component **I** (RSI divergence) then refined (panel-resolved) to the spec-literal *rsi-min* — I=2 iff RSI(14) at point 5 is NOT the lowest (bull) / highest (bear) RSI over the decline into it `[pt4+1 .. p5-5]` — catching grind divergences (RELIANCE Nov-2022 now **I=2 / Q18**, was I=0/Q16; base rate 38.5% ≈ the analyst's ~1-in-3 at exhaustion overshoots). The skeptic's prior-swing-low+bounce variant was empirically tested and DROPPED (it missed the Nov-2022 grind divergence and under-fired at 17%). **Still DESCRIPTIVE-ONLY** — the §C edge backtest is un-run (the gate).

*(Companion to `docs/wolfe-wave-design.md` (intent/history) and `docs/wolfe-NEXT-SESSION.md` (session run-book). This file is the precise rule reference.)*
