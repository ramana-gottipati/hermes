# Wolfe Wave (Patearn variation) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** DESCRIPTIVE-ONLY · **Governing decision(s):** D96 / D108 / D109 / D111 · **Reconciled:** 2026-07-11 (S109).
> **Charter:** the single canonical definition + current-state reference for Wolfe Wave. Deep design: [wolfe-wave-design.md](../wolfe-wave-design.md) + [wolfe-rules.md](../wolfe-rules.md); run-book for the frozen re-apply: [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md). Numbers live in code + [calculations-and-weights.md](../calculations-and-weights.md); this page never restates a formula's constants — it links.

**One-line definition:** a Wolfe Wave is a **5-pivot reversal structure** — points 1·2·3·4 define a converging channel, point **5** overshoots the extended **1-3 line** and reverses toward the **EPA (1-4) target line** — surfaced in patearn as a **DESCRIPTIVE-ONLY** lens in which **the machine detects and validates points 1·2·3·4 (fractal-gated) and Ramana's Fibonacci-confluence method owns point 5**, and whose only validated edge is **selection** (which name / direction / when), never trade-craft.

---

> ## 🧊 FREEZE — READ BEFORE TOUCHING ANY WOLFE CODE
>
> **No lane may write Wolfe SCORING code until Ramana signs off the §B weightage proposal.** The proposal on the table (with him): **A 6→5 · C 3→4 · F 3→4 · H 2→3**, plus the **§B0.4 "touched not cut" EPA recode** (0.3% tolerance over the FULL 1-4 span; a candle that slices *through* the line is a *cut* and does not count). Canon for the strength concept is [wolfe-rules.md](../wolfe-rules.md) **§B0** — the COMPLETE 5-driver concept, and **freshness is NOT strength**.
>
> - As of **S108** a worktree lane (`tmp/s108-weights`, signature `_QUALITY_MAX` ≠ 24) is *finishing this exact rebalance*. The freeze is **NOT lifted** — do not absorb, re-implement, or race that work from another lane. Verify-when-it-lands battery: [NEXT-SESSION-CARRYFORWARD.md](../NEXT-SESSION-CARRYFORWARD.md) § WORKTREE STATUS.
> - **✅ CARVE-OUT:** the **draw tool** (D111) is DESCRIPTIVE geometry, orthogonal to scoring, and is explicitly **OUT of the freeze** (Ramana's direct call). Only §B scoring / weightage / lifecycle-methodology stays frozen.
> - This line is the thing lanes check before touching Wolfe. **Keep it accurate** (see [Maintenance](#maintenance)).

---

## 1. What it is

A Wolfe Wave is the first **pattern / geometry** lens in the patearn stack. Every other lens (DVPT, RS/RRG, MEP, rs-band) scores a *state* — momentum, relative level, accumulation. Wolfe scores a *structural setup*: a specific 5-point geometry that, when symmetric, projects a high-probability reversal **zone**, a defined **target** (the EPA line), and an estimated **time**. It is orthogonal to the state lenses — a setup can exist regardless of where RS or DVPT sit, and those become the *confirmation*, never the trigger.

**The division of labor (the spine):** the engine detects and validates **points 1·2·3·4** mechanically over the NSE bhav-copy archive — point-in-time safe, ₹0, no-LLM — and hands over the two thrust-leg vectors. **Ramana's Fib-confluence method owns point 5**: extend legs 1-2 and 3-4, find matched-ratio confluence bands, and the tightest band on the overshoot side is the high-probability point-5 zone. The load-bearing assumption is **Wolfe symmetry** (leg 1-2 ≈ leg 3-4) — the more symmetric the legs, the tighter his bands, which is exactly the property the machine can validate.

## 2. Our variation vs. the standard Wolfe Wave

Textbook Wolfe = 5-point reversal geometry with an EPA (Estimated Price at Arrival) line drawn 1→4 and extended to the right. patearn keeps that spine intact and adds five proprietary layers:

| Layer | What it adds | Proprietary? |
|---|---|---|
| **MANDATORY 2/3/4 fractal-detection gate** | Points 2, 3 and 4 must EACH be a **≥ 2-fractal** (strict Williams fractal); a wave whose 2/3/4 are not all fractals is **not a Wolfe — do not consider it**. Point 1 needs no fractal (a fractal there is a scored bonus); point 5 needs no fractal (entry timeliness). This is a **hard detection gate**, not a soft score. (D108) | **Yes** — Ramana's rule, enforced in code since `0c89e8f`. |
| **§B0 5-driver strength concept** | "The strength of a Wolfe is not one number" — it is five INDEPENDENT things agreeing at once: (1) real fractal pivots, (2) a narrow Fib confluence zone, (3) point-5 landing close to that zone, (4) the EPA line respected as touched-not-cut S/R, (5) RSI-divergence at point 5. Canon: [wolfe-rules.md](../wolfe-rules.md) §B0. | **Yes** |
| **"Touched not cut" EPA rule** | The EPA line is strong S/R only where a candle's high/low comes within **0.3%** of it (a touch); a candle slicing *through* the line is a *cut* and does not count. More clean touches ⇒ stronger line ⇒ stronger wave. (§B0.4 — part of the frozen recode.) | **Yes** |
| **Three-section lifecycle overlay** | Every wave sits in exactly ONE of **Prediction / Open / Closed** (see §3). Simple, labelled, **non-hiding**. (D109) | **Yes** |
| **The draw tool** | `✎ draw your own` on the stock chart: click points 1→5, auto-snap to real pivots, auto-EPA, strict symmetry warning, double-click edit. (D111) | **Yes** |

Everything else — the L,H,L,H / H,L,H,L convention, the extension-fan Fib method, the EPA line — is the standard method, encoded faithfully.

## 3. How it works (methodology)

**The 5-point structure (convention — LOCKED, [wolfe-rules.md](../wolfe-rules.md) §A1/§A2).** Pivots in time order:
- **BULL (buy)** = a *descending* structure, pivots **L, H, L, H** — point 1 is a LOW; 1·3·5 are descending lows; point 5 overshoots the 1-3 support line and reverses **up**.
- **BEAR (sell)** = an *ascending* structure, pivots **H, L, H, L** — point 1 is a HIGH; 1·3·5 are ascending highs; point 5 overshoots the 1-3 resistance line and reverses **down**.
- Point 4 sits inside the 1-2 channel (bull 4 ≤ 2, bear 4 ≥ 2); a breach of point 4 before 5 voids the wave. Distance rule: leg 1-2 ≥ leg 3-4 in price (a contracting wedge).

**The fractal gate** (§2 above) runs in `detect_waves` *after* `_classify` (geometry) and *before* `find_p5` — it rejects any candidate whose points 2/3/4 are not all ≥ 2-fractal. Pivots come from a UNION of multi-degree Williams fractals (his Fyers Fractals 2 & 10, plus 5/20/30 for detection reach) and an ATR-zigzag grid; **quality caps at the 10-fractal level** (20/30 help detection only).

**Point 5** needs no fractal. It confirms only when price **crosses the extended 1-3 line** *and* goes beyond point 3 (bull: a low below both; bear: the mirror), then keeps extending to the deepest overshoot **until the EPA (1-4) line is touched**, at which point it locks.

**The EPA line** = the 1-4 line, drawn only after point 5 confirms, extended to the right edge; it is the reversal target.

**The §B strength score** is a plain points sum over the five drivers — `(A×2) + B + C + F + G + H + I + D`, higher = stronger, with point 1 shown as its own ×2 "start" rating and **freshness deliberately excluded**. The component definitions, buckets, tolerances and the `_QUALITY_MAX` normaliser live once in code — [src/automation/wolfe.py](../../src/automation/wolfe.py) — and are explained once in [calculations-and-weights.md](../calculations-and-weights.md) §5c/§5d. **This page does not restate those constants, and they are FROZEN pending Ramana's §B weightage sign-off** (see the freeze callout above) — read the code/canon, do not re-derive.

**Lifecycle (D109 — the overlay's three sections, canon [wolfe-rules.md](../wolfe-rules.md) §A8):**
- **PREDICTION** — point 5 not yet formed (still building toward the point-5 zone); no EPA yet.
- **OPEN** — point 5 formed, EPA (1-4) line **not yet touched** after 5. *The current, actionable set* — his primary need.
- **CLOSED** — after point 5, price reached and touched the EPA line (the study played out; reference only). Each closed wave shows **how neatly it closed** (`clean` ≤3% give-back · `ok` ≤7% · `choppy` >7%), via `wolfe.close_quality()`.

## 4. Status, validation & honesty fence

**DESCRIPTIVE-ONLY. The lens never trades or ranks as a book.** This is a binding fence, not a caveat — misrepresenting it is a blocking error.

- **The edge is SELECTION, not craft.** The raw Wolfe trade has **no market-neutral edge** (median −2% net; a pure tail game). The only validated edge is the **winner-profile selection** (reachable EPA + strong point-1 + not-narrowest zone), which SURVIVED a true out-of-sample derivation (fit 2004-14 / test 2015-26) and a beta-control + placebo. The placebo gap is negative everywhere → the edge lives in *which name / direction / when*, **not** in the entry/stop/target trade-craft.
- **Split by side:** **BULL = a regime-ROBUST long selection edge** (α ≈ +5.9; positive median even when the market falls). **BEAR = tail-only** — it fails as a standalone scanner once regime is stripped and is decaying; only the mean/tail survives. On the surfaces, BULL rows read **✓ edge**, BEAR rows read **⚠ tail**.
- Even the winner profile stays a **SCANNER** — +1% median is too thin to carry costs, slippage and discretionary error mechanically. It sharpens the eye at the point-5 zone; it does not pull the trigger. Ledger: [strategy-ledger.md](../strategy-ledger.md) (Wolfe row) — same descriptive/selection class as the PEAD and harmonic lenses.

**The D108 revert + fractal gate (2026-07-10, S105, Ramana-directed).** After "I am really disappointed that the fractal has been ignored," the code was **REVERTED to the D96 baseline (`9d04bd9`)** and the 2/3/4 fractal rule was promoted from a soft score component to a **MANDATORY detection gate** (his verbatim: "must, minimum 2 fractals; without a fractal do not consider"). Measured: **32%** of surfaced waves violated it (e.g. TCS BULL 2005-01-07, degrees `[0,0,0,0]`, still CONFIRMED before the gate). The entire **D98–D102 layer was REMOVED from code** — STR/LND split, structure-watch, attention/recency ranking, §B2 withhold, lifecycle queues/progress chips/CLOSED chips, EPA cache wiring — to be re-applied methodically *with* him. §A geometry and §B component math were left untouched.

**The §B freeze (headline).** No Wolfe scoring code by any lane until Ramana signs off the §B weightage proposal (A 6→5 · C 3→4 · F 3→4 · H 2→3 + the §B0.4 touched-not-cut recode). See the freeze callout at the top of this page — it is the single most important operational fact here.

## 5. Where it lives (code · routes · DB · timers)

| Piece | Path / name |
|---|---|
| Detector + §A geometry + §B score + `fib_zones` + `find_p5` + `winner_scan` + `persist_scan` + `epa_touched`/`close_quality` (D109) | [src/automation/wolfe.py](../../src/automation/wolfe.py) |
| Ranked page + scanner + JSON overlay endpoint | [src/web/wolfe_view.py](../../src/web/wolfe_view.py) |
| Stock-chart candle overlay SNIPPET (Prediction/Open/Closed tabs **+ ✎ Draw** mode) | [src/web/wolfe_overlay.py](../../src/web/wolfe_overlay.py) |
| Nightly persist unit | `scripts/hermes-wolfe-scan.service` + `.timer` |

**Routes:**
- `/dash/wolfe` — standalone ranked auto-detect SVG (browse-all, read-only).
- `/dash/wolfe/scan` — the winner-profile scanner (BULL ✓ edge / BEAR ⚠ tail; rows click through to the chart with the winner wave auto-drawn).
- `/dash/wolfe/overlay` — JSON feed (`wolfe.overlay_for`) for the stock-chart overlay.
- `/dash/stock?sym=…` → tick **Wolfe wave** — the candle overlay (the only *clickable* chart, hence the draw tool's home).

**Timer:** `hermes-wolfe-scan` runs Mon-Fri **16:00 UTC (9:30 PM IST)** after the bhav→signals chain — pure compute, **no LLM** — materialising the winner scan into `wolfe_signals` so the scanner reads a snapshot (~0.004s) instead of recomputing (~30s).

**DB:** `wolfe_signals` (CREATE-IF-NOT-EXISTS **owned by `wolfe.py`; `db.py` is untouched** by design). Residue from the reverted D101/D102 layer — the `wolfe_epa_state` table and the `'<uni>:watch'` / `'<uni>:forming'` snapshot rows — is now **unused but harmless** (no reader references it at the D108 baseline).

> **🔴 FLIP HAZARD — `wolfe_overlay.py`.** The live VPS file is a **UNION** of a parallel lane's lifecycle (Open/Closed) layer *and* the draw tool, 3-way-merged (only `exitDraw` conflicted). The draw-tool commit `8fc40dc` lives on branch **`wolfe-draw-tool`, NOT on main**. **NEVER full-file `scp` or overwrite `wolfe_overlay.py` from either lane without merging BOTH hunk sets first** — either copy overwriting the other reverts it (the classic flip). VPS pre-deploy backup exists (`wolfe_overlay.py.bak-*`).

## 6. Data & provenance

- **Input:** `bhavcopy_rows` (NSE daily bhav copy — `trade_date, open, high, low, close, volume`) per symbol, corporate-action-adjusted via the production adjuster (`src.automation.adjust`). Universe from `nse_equity_list`, default **Nifty 500 daily**; an `inclusive` (delisted-aware, survivorship-honest) universe is available on the scanner.
- **Primary source only.** NSE bhav copy — no vendor, no Screener dependency (CLAUDE.md Guardrail #8). Pure-stdlib detector, no LLM, ₹0.
- **Point-in-time / no-look-ahead (mandatory, [wolfe-rules.md](../wolfe-rules.md) §C).** Every scan takes an *as-of date*; the result as-of *t* is **byte-identical whether or not bars after *t* exist**. Naturally PIT-honest: a fractal-N pivot confirms only N bars after its candle (points 1-4 carry their real delay); point 5 = the live candle extreme (seen immediately — exactly why it has no fractal gate). This one capability powers both ad-hoc historical review and the §C backtest.

## 7. Terminology canon

- **Fractal gate** — the MANDATORY 2/3/4 ≥ 2-fractal detection rule (D108). Preference order everywhere: **10 > 5 > 2 > candle**. Point 1: no gate (fractal = bonus). Point 5: no gate (entry timeliness).
- **EPA** — Estimated Price at Arrival; the **1-4 line**, the reversal target. Drawn only after point 5 confirms.
- **"Touched not cut"** — a candle within 0.3% of the EPA line *touches* it (confirms S/R); a candle slicing through *cuts* it (does not count). §B0.4 — part of the frozen recode.
- **§B0 drivers (5)** — fractal structure · Fib confluence zone · point-5 placement · EPA line as touched-not-cut S/R · RSI divergence at point 5. The complete strength concept; **freshness is NOT strength**.
- **Lifecycle** — **Prediction** (no point 5) · **Open** (point 5, EPA untouched — actionable) · **Closed** (EPA touched — reference), with a closure-neatness readout.
- **Winner profile** — the OOS-validated selection filter (reachable EPA + strong point-1 + not-narrowest zone); the §B *total* INVERTS as a trade filter, so the scanner uses the winner profile, not raw Q.

**⚠️ DEPRECATED — historical only (REMOVED from code by D108).** The **STR/LND** split (STR = shape /11, LND = landing /13), **structure-watch**, **attention rank** (`rank_attention = Q × 0.5^(age/60)`), the **§B2 "not entry-qualified" withhold queues**, and the D101/D102 **lifecycle queues / progress chips** are **no longer in the code**. They survive as design in [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md) and as history in [PROJECT_STATE.md](../../PROJECT_STATE.md) (D98–D102) for the methodical re-apply *with* Ramana. Do not cite this vocabulary as current behaviour.

## 8. Decision & session history

Terse chronological (full entries in [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log / Session log):
- **D70** (S40) — the SELL setup is fixed as an ascending wedge; convention locked.
- **D96** (S86c, `9d04bd9`) — the ◄/► walk gets a **freshness guarantee** (`_FRESH_KEEP_BARS=250`); a quality cap must never gate recency. **This is the reverted-to baseline.**
- **D98–D102** (S89) — STR/LND split + structure-watch (D98), attention rank (D99), §B2 withhold (D100), lifecycle state queues + event-driven EPA (D101), progress chips + CLOSED chips (D102). **All later REMOVED by D108** (history only).
- **D108** (S105, `0c89e8f`) — **REVERT to the D96 baseline + the MANDATORY 2/3/4 fractal gate**; the D98–D102 layer removed. §A geometry + §B math untouched.
- **D109** (S106, `2541009`) — the overlay's **three lifecycle sections** (Prediction / Open / Closed), simple and non-hiding, re-added on the D108 baseline (Ramana: "I asked for three sections").
- **S107** (`f7d7a87`) — overlay badge (dir · points/total · rank); chart stays STATIC on nav (no re-zoom).
- **D111** (2026-07-11, `8fc40dc` on branch `wolfe-draw-tool`) — the **draw-tool carve-out**: `✎ draw your own` upgraded and LIVE, explicitly OUTSIDE the §B freeze. Auto-snap (points 1/3/5→lows, 2/4→highs), auto-EPA at point 4, STRICT 1-2 ≥ 3-4 symmetry warning, double-click point edit.
- **S108** — the **§B weightage rebalance** is in flight in the `tmp/s108-weights` worktree (finishing the A/C/F/H reweight + the touched-not-cut recode). Freeze remains in force until Ramana signs off.

## 9. Open items / frozen work

- **🧊 THE §B weightage sign-off (freeze).** The headline open item. A 6→5 · C 3→4 · F 3→4 · H 2→3 + the §B0.4 touched-not-cut EPA recode. In flight in `tmp/s108-weights`; nothing else may touch Wolfe scoring until it lands and he signs off.
- **Point-4-strength descriptor** — recorded, NOT built; **BLOCKED on Ramana's worked chart example**. His method detail: point 4 is strong where the legs **1-2 ∩ 2-3** Fib confluence intersect (a *different* leg pair than the point-5 zones' 1-2 ∩ 3-4). ([wolfe-rules.md](../wolfe-rules.md) §D item 4.)
- **D95 tape-wiring** — pass `corp_actions` events into Wolfe's adjust path so split/bonus history is tape-primary like the other consumers (owner = Wolfe lane).
- **§C backtest spec = frozen appendix** — the point-in-time as-of / backtesting rules ([wolfe-rules.md](../wolfe-rules.md) §C). The backtest is DONE and decoded; it is the descriptive-only *gate*, and it earned the label ("survived true OOS"), not the role. Do not re-run merge/derive without cause.
- **Git reconcile** — the D111 draw-tool commit (`8fc40dc`) is not yet merged to main and is not in the PROJECT_STATE decision log; the lifecycle lane's overlay work must be committed and merged with it (see the FLIP HAZARD). Surface to Ramana whether the live lifecycle layer stays.

## 10. Sources of truth

- **Deep design / intent / history:** [wolfe-wave-design.md](../wolfe-wave-design.md)
- **Rules of record (§A geometry LOCKED · §B0 strength concept CANON · §C PIT/backtest):** [wolfe-rules.md](../wolfe-rules.md)
- **Run-book for the frozen re-apply (★ fractal-focus brief + gate spec):** [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md)
- **Weights / constants (the ONLY explainer; frozen):** [calculations-and-weights.md](../calculations-and-weights.md) §5c/§5d + [src/automation/wolfe.py](../../src/automation/wolfe.py)
- **Strategy ledger (Wolfe row — descriptive/selection class):** [strategy-ledger.md](../strategy-ledger.md)
- **Memory:** `[[wolfe-wave-strategy]]` (the canonical running record — D111, freeze, split-by-side, §C trade-mechanics appendix)
- **Decisions:** [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log — D96 / D108 / D109 (D111 pending fold-in).

## Maintenance

- **When Ramana signs off the §B weightage:** update **this doc and [wolfe-rules.md](../wolfe-rules.md) together** — flip the freeze callout, record the ratified weights' home (code + calculations-and-weights.md), and move the item out of §9.
- **Keep the freeze status line accurate** — it is the thing lanes check before touching Wolfe. If the `tmp/s108-weights` work lands or the freeze changes state, edit the top callout in the SAME change.
- **Never restate weights/thresholds here** — link to code + calculations-and-weights.md (the "numbers live once in code" discipline). This page fixes *definition, status and terminology*; the numbers live once, in code.
