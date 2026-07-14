# Wolfe Wave (Patearn variation) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** DESCRIPTIVE-ONLY · **Governing decision(s):** D96 / D108 / D109 / D111 / D113 · **Reconciled:** 2026-07-11 (S113).
> **Origin:** 📚 CLASSIC base (Bill Wolfe's 5-point reversal geometry) + 🧑 RAMANA layer (the mandatory 2/3/4 fractal gate D108, the §B strength rebalance D111 & spring-and-reclaim §A9). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for Wolfe Wave. Deep design: [wolfe-wave-design.md](../wolfe-wave-design.md) + [wolfe-rules.md](../wolfe-rules.md) (rules of record, now incl. §A9 spring-and-reclaim + §B3 ratified scoring); re-apply run-book: [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md). Numbers live in code + [calculations-and-weights.md](../calculations-and-weights.md); this page never restates a formula's constants — it links.

**One-line definition:** a Wolfe Wave is a **5-pivot reversal structure** — points 1·2·3·4 define a converging channel, point **5** overshoots the extended **1-3 line** and reverses toward the **EPA (1-4) target line** — surfaced in patearn as a **DESCRIPTIVE-ONLY** lens in which **the machine detects and validates points 1·2·3·4 (fractal-gated) and Ramana's Fibonacci-confluence method owns point 5**, and whose only validated edge is **selection** (which name / direction / when), never trade-craft.

---

> ## ✅ §B SCORING — RESOLVED (D111, 2026-07-11), no longer frozen
>
> The long-standing **§B weightage freeze is LIFTED.** On 2026-07-11 Ramana signed off the full §B
> rescore **component-by-component against his own TCS wave** — decision **D111** (S109, commit
> `dfbe175`). The ratified score is **LIVE**, formula **A + B + C + F + G + H + I + D**, normalised
> against **`_QUALITY_MAX`** in [wolfe.py](../../src/automation/wolfe.py) — **currently 27** (it was 25
> at D111, then G was widened 0-2→0-4; see §8). The overlay badge reads `points/_QUALITY_MAX`. What
> changed from the pre-freeze proposal:
> - **A (point-1)** = candle **1** / any fractal **4**, *flat* — the old **×2 multiplier is gone**
>   ("we don't need a strong fractal at point 1").
> - **C (point-5 placement) = the SPRING-AND-RECLAIM doctrine ([wolfe-rules.md](../wolfe-rules.md) §A9):**
>   point 5 may break the zone by **any depth** and then **reclaim** it (support→resistance flip
>   breached back) = a valid strong reversal. This fixed the C=0 Ramana challenged (his TCS point 5).
> - **G** = the confluence zone **nearest the current price**, graded **0–4** by ratio depth (4.618 deepest); **F** widened 0–4. (G was 0–2 at D111, later widened to 0–4 — the interim "anywhere in the wave" reading was reverted.)
> - **H (EPA "touched not cut")** landed: candles pts 1→4 within 0.3% of the 1-4 line, one side only;
>   a *cut* ≠ a touch; scale 0 / 1-2→1 / 3-4→2 / >4→3.
> - **I (RSI divergence) bug fixed** — compare point 5's low to the **prior pivot low (point 3)**,
>   not the pt4→p5 fall. **2.0 restored** to `_FIB_R`.
>
> **Untouched by D111:** §A geometry, the **D108 2/3/4 fractal gate**, and `find_p5`. The doctrine
> is written down at [wolfe-rules.md](../wolfe-rules.md) §A9 + §B3 (Ramana: "I strongly need the
> documentation… could become a training video").
>
> **The draw tool — ✅ MERGED (D113, S112, `35a11e7`).** `✎ draw your own` (auto-snap: pts 1/3/5→lows,
> 2/4→highs; auto-EPA the moment point 4 lands; STRICT 1-2 ≥ 3-4 gate; double-click point-edit) is a
> DESCRIPTIVE geometry surface, orthogonal to §B scoring, now **on main** (draw-mode JS only, zero
> `wolfe.py`/scoring touch). It landed via a fresh commit under **D113/S112** — the abandoned branch
> commit `8fc40dc` was NOT used, and D113 was renumbered from the draw-lane's provisional "D111",
> which the §B rescore claimed. **Do not conflate D113 (draw tool) with D111 (§B rescore).**

---

## 1. What it is

A Wolfe Wave is the first **pattern / geometry** lens in the patearn stack. Every other lens (DVPT, RS/RRG, MEP, rs-band) scores a *state* — momentum, relative level, accumulation. Wolfe scores a *structural setup*: a specific 5-point geometry that, when symmetric, projects a high-probability reversal **zone**, a defined **target** (the EPA line), and an estimated **time**. It is orthogonal to the state lenses — a setup can exist regardless of where RS or DVPT sit, and those become the *confirmation*, never the trigger.

**The division of labor (the spine):** the engine detects and validates **points 1·2·3·4** mechanically over the NSE bhav-copy archive — point-in-time safe, ₹0, no-LLM — and hands over the two thrust-leg vectors. **Ramana's Fib-confluence method owns point 5**: extend legs 1-2 and 3-4, find matched-ratio confluence bands, and the tightest band on the overshoot side is the high-probability point-5 zone. The load-bearing assumption is **Wolfe symmetry** (leg 1-2 ≈ leg 3-4) — the more symmetric the legs, the tighter his bands, which is exactly the property the machine can validate.

## 2. Our variation vs. the standard Wolfe Wave

Textbook Wolfe = 5-point reversal geometry with an EPA (Estimated Price at Arrival) line drawn 1→4 and extended to the right. patearn keeps that spine intact and adds five proprietary layers:

| Layer | What it adds | Proprietary? |
|---|---|---|
| **MANDATORY 2/3/4 fractal-detection gate** | Points 2, 3 and 4 must EACH be a **≥ 2-fractal** (strict Williams fractal); a wave whose 2/3/4 are not all fractals is **not a Wolfe — do not consider it**. Point 1 needs no fractal (a fractal there is a scored bonus); point 5 needs no fractal (entry timeliness). This is a **hard detection gate**, not a soft score. (D108) | **Yes** — Ramana's rule, enforced in code since `0c89e8f`. |
| **§B strength score (ratified D111)** | Strength = eight INDEPENDENT things agreeing, summed to **`_QUALITY_MAX`** (currently 27): **A** point-1 quality · **B** symmetry · **C** point-5 placement (spring-and-reclaim, §A9) · **F** zone narrowness · **G** confluence-zone-nearest-price (0–4) · **H** EPA touched-not-cut · **I** RSI divergence · **D** direction/context. Buckets + tolerances: [wolfe-rules.md](../wolfe-rules.md) §B3 + [wolfe.py](../../src/automation/wolfe.py). | **Yes** |
| **Spring-and-reclaim point-5 doctrine** | Point 5 may pierce the confluence zone by ANY depth and then **reclaim** it (a support→resistance flip breached back) — that reclaim, not the overshoot depth, is the strong-reversal tell. ([wolfe-rules.md](../wolfe-rules.md) §A9, D111.) | **Yes** |
| **"Touched not cut" EPA rule (H)** | The EPA/1-4 line is strong S/R only where a candle comes within **0.3%** of it (a touch, one side only); a candle slicing *through* is a *cut* and does not count. More clean touches ⇒ stronger line. (§B3 H; landed D111.) | **Yes** |
| **Three-section lifecycle overlay** | Every wave sits in exactly ONE of **Prediction / Open / Closed** (see §3). Simple, labelled, **non-hiding**. (D109) | **Yes** |
| **The draw tool** *(merged — D113 / S112)* | `✎ draw your own` on the stock chart: click points 1→5, auto-snap (1/3/5→lows, 2/4→highs), auto-EPA at point 4, strict 1-2 ≥ 3-4 warning, double-click edit. | **Yes** |

Everything else — the L,H,L,H / H,L,H,L convention, the extension-fan Fib method, the EPA line — is the standard method, encoded faithfully.

## 3. How it works (methodology)

**The 5-point structure (convention — LOCKED, [wolfe-rules.md](../wolfe-rules.md) §A1/§A2).** Pivots in time order:
- **BULL (buy)** = a *descending* structure, pivots **L, H, L, H** — point 1 is a LOW; 1·3·5 are descending lows; point 5 overshoots the 1-3 support line and reverses **up**.
- **BEAR (sell)** = an *ascending* structure, pivots **H, L, H, L** — point 1 is a HIGH; 1·3·5 are ascending highs; point 5 overshoots the 1-3 resistance line and reverses **down**.
- Point 4 sits inside the 1-2 channel (bull 4 ≤ 2, bear 4 ≥ 2); a breach of point 4 before 5 voids the wave. Distance rule: leg 1-2 ≥ leg 3-4 in price (a contracting wedge).

**The fractal gate** (§2 above) runs in `detect_waves` *after* `_classify` (geometry) and *before* `find_p5` — it rejects any candidate whose points 2/3/4 are not all ≥ 2-fractal. Pivots come from a UNION of multi-degree Williams fractals (his Fyers Fractals 2 & 10, plus 5/20/30 for detection reach) and an ATR-zigzag grid; **quality caps at the 10-fractal level** (20/30 help detection only).

**Point 5** needs no fractal. It confirms only when price **crosses the extended 1-3 line** *and* goes beyond point 3 (bull: a low below both; bear: the mirror). Under the **spring-and-reclaim** doctrine (§A9) a deep pierce that then **reclaims** the confluence zone is a *strong* point 5, not a failure — depth alone is not disqualifying.

**The EPA line** = the 1-4 line, drawn only after point 5 confirms, extended to the right edge; it is the reversal target.

**The §B strength score (ratified D111 — LIVE, no longer frozen).** A plain points sum over the eight drivers — **A + B + C + F + G + H + I + D**, higher = stronger, normalised against **`_QUALITY_MAX`** (currently 27). Point 1 (**A**) is scored *flat* (candle 1 / fractal 4 — the pre-freeze ×2 was dropped); **freshness is deliberately excluded** (a quality cap must never gate recency — D96). The component definitions, buckets and tolerances live once in code — [src/automation/wolfe.py](../../src/automation/wolfe.py) — and are written down once in [wolfe-rules.md](../wolfe-rules.md) §B3 (+ §A9 for C). **This page does not restate those constants** — read the code/canon, do not re-derive. As a *trade filter* the raw §B total INVERTS, so the scanner uses the winner profile (§4), not the raw score.

**Lifecycle (D109 — the overlay's three sections, canon [wolfe-rules.md](../wolfe-rules.md) §A8):**
- **PREDICTION** — point 5 not yet formed (still building toward the point-5 zone); no EPA yet.
- **OPEN** — point 5 formed, EPA (1-4) line **not yet touched** after 5. *The current, actionable set* — his primary need.
- **CLOSED** — after point 5, price reached and touched the EPA line (the study played out; reference only). Each closed wave shows **how neatly it closed** (`clean` ≤3% give-back · `ok` ≤7% · `choppy` >7%), via `wolfe.close_quality()`.

## 4. Status, validation & honesty fence

**DESCRIPTIVE-ONLY. The lens never trades or ranks as a book.** This is a binding fence, not a caveat — misrepresenting it is a blocking error. (The §B *scoring* is now ratified and live — but a validated *score* is not a validated *strategy*; the descriptive-only status is about the trade, not the math.)

- **The edge is SELECTION, not craft.** The raw Wolfe trade has **no market-neutral edge** (median −2% net; a pure tail game). The only validated edge is the **winner-profile selection** (reachable EPA + strong point-1 + not-narrowest zone) — a true OOS derivation (fit 2004-14 / test 2015-26) + beta-control + placebo. **Re-validated 2026-07-11 under the D111 rebalance (§8):** the fit **re-derives the identical rule `D≤1 · p1≥2 · F≤2`** (the F 0–4 widening is neutral to the filter), and the **placebo gap stays negative everywhere** → the edge lives in *which name / direction / when*, **not** in the entry/stop/target trade-craft. But post the D108 fractal gate the numbers are **softer than the original**: on the survivorship-aware **primary** universe the current verdict is **IN-SAMPLE-ONLY** (bear-driven); it clears the OOS bar only on the nifty500 sensitivity.
- **Split by side:** **BULL = a regime-ROBUST long selection edge** (test 2015-26 medNet **+4.4%**, residual **α +5.07**, CI-excludes-0; positive even when the market falls). **BEAR = tail-only** — regime-dependent (loses when the tape isn't already falling), decaying into 2021-26, and it now **fails the primary OOS `medNet ≥ 0` bar** (−1.0% inclusive; only marginally positive on the survivorship-biased nifty500). On the surfaces, BULL rows read **✓ edge**, BEAR rows read **⚠ tail**.
- Even the winner profile stays a **SCANNER** — the thin blended median (~+1%, BULL-carried) can't carry costs, slippage and discretionary error mechanically. It sharpens the eye at the point-5 zone; it does not pull the trigger. Ledger: [strategy-ledger.md](../strategy-ledger.md) (Wolfe row) — same descriptive/selection class as the PEAD and harmonic lenses.
- **The "Open trades — remaining ROI" surface (S121, D120/D121) is descriptive-only too, with its own fences.** It lists every *OPEN* winner-profile setup (point 5 printed, EPA 1-4 not yet touched) within **~1 trading year**, ranked by remaining ROI from the current price (run%/risk%/R:R). The validated **+edge is measured only on FRESH ≤15d entries** — older open trades carry run left but **no validated entry-edge**, so they are **badged** ("open · judge the run"), never presented as the edge. The **EPA is aggressive on old waves** (the 1-4 line extended to today) and is triple-fenced: a hard 1-year population cap + coherence floor (D121; older/incoherent waves are **disclosed-and-held-out**, never silently hidden — they still draw on the chart), `~`-muting of far-extrapolated values, and a conservative `run→T1` floor shown beside it. Not a buy/sell signal.

**The D108 revert + fractal gate (2026-07-10, S105, Ramana-directed).** After "I am really disappointed that the fractal has been ignored," the code was **REVERTED to the D96 baseline (`9d04bd9`)** and the 2/3/4 fractal rule was promoted from a soft score component to a **MANDATORY detection gate** (his verbatim: "must, minimum 2 fractals; without a fractal do not consider"). Measured: **32%** of surfaced waves violated it (e.g. TCS BULL 2005-01-07, degrees `[0,0,0,0]`, still CONFIRMED before the gate). The entire **D98–D102 layer was REMOVED from code** — STR/LND split, structure-watch, attention/recency ranking, §B2 withhold, lifecycle queues/progress chips/CLOSED chips, EPA cache wiring — to be re-applied methodically *with* him. §A geometry and the §B component math were left untouched (and the latter then ratified by D111).

**§B resolved (was the headline freeze).** The A/C/F/G/H/I recode that used to gate all Wolfe work is **decided and live (D111, `dfbe175`)** — see the callout at the top. There is no longer a scoring freeze; the remaining open threads (§9) are point-4-strength and the D98–D102 re-apply, none of which block §B.

## 5. Where it lives (code · routes · DB · timers)

| Piece | Path / name |
|---|---|
| Detector + §A geometry + §B score (max `_QUALITY_MAX`) + `fib_zones` + `find_p5` + `winner_scan` + `persist_scan` + `epa_touched`/`close_quality` (D109) + **`open_scan`/`open_metrics`/`enrich_open_rows`/`filter_open_rows`/`persist_open_scan` (open-trades, S121)** | [src/automation/wolfe.py](../../src/automation/wolfe.py) |
| Ranked page + scanner + JSON overlay endpoint + the **Fresh⇄Open toggle** | [src/web/wolfe_view.py](../../src/web/wolfe_view.py) |
| **Open-trades "remaining ROI" view** (11 filters · price-ladder · what-changed diff · CSV · sticky filters) | [src/web/wolfe_trades_view.py](../../src/web/wolfe_trades_view.py) |
| Stock-chart candle overlay SNIPPET (Prediction/Open/Closed tabs **+ ✎ Draw** mode) | [src/web/wolfe_overlay.py](../../src/web/wolfe_overlay.py) |
| Nightly persist unit (materialises BOTH snapshots — `--persist-scan` piggybacks `--persist-open`) | `scripts/hermes-wolfe-scan.service` + `.timer` |

**Routes:**
- `/dash/markets/wolfe-scan` (**"Patterns · Wolfe"**, ONE tab; flat alias `/dash/wolfe/scan` 307→here) → a **Fresh setups ⇄ Open trades** toggle (S121). *Fresh* = the winner-profile scanner; *Open trades* (`/dash/wolfe/trades`) = every OPEN winner-profile setup within ~1yr ranked by remaining ROI, with 11 filters (Size·Sector·Direction·Max-age·min-Q·min-room·Status·min-liquidity·min-R:R·**Proximity**·**min-RS**), a §B tooltip, an inline price-ladder, a breadth strip, a staleness banner, sticky filters, a "what changed since you last looked" diff, and CSV export. Row-click draws **that exact wave** (by p5+p4 date) and links on to the full stock chart.
- `/dash/wolfe` — standalone ranked auto-detect SVG (browse-all, read-only; `?sym=…&p5=…&p4=…` draws a specific historical wave).
- `/dash/wolfe/scan` — the winner-profile scanner (BULL ✓ edge / BEAR ⚠ tail; rows click through to the chart with the winner wave auto-drawn).
- `/dash/wolfe/overlay` — JSON feed (`wolfe.overlay_for`) for the stock-chart overlay.
- `/dash/stock?sym=…[&wolfe=<p5date>]` → tick **Wolfe wave** — the candle overlay (the only *clickable* chart, hence the draw tool's home; `?wolfe=` auto-selects a specific wave).

**Timer:** `hermes-wolfe-scan` runs Mon-Fri **16:00 UTC (9:30 PM IST)** after the bhav→signals chain — pure compute, **no LLM** — materialising the winner scan into `wolfe_signals` so the scanner reads a snapshot (~0.004s) instead of recomputing (~30s).

**DB:** `wolfe_signals` (CREATE-IF-NOT-EXISTS **owned by `wolfe.py`; `db.py` is untouched** by design) — the fresh winner-profile snapshot. **`wolfe_open_signals`** (S121, same isolation) — the open-trades snapshot: the full enriched row (size · sector tags · liquidity ₹cr + delivery% · RS · run/risk/rr · `atr_pct` · `invalid` · comp/tags JSON · `held_out` disclosure count), materialised by `--persist-open` (piggybacked on the nightly `--persist-scan`). Residue from the reverted D101/D102 layer — the `wolfe_epa_state` table and the `'<uni>:watch'` / `'<uni>:forming'` snapshot rows — is now **unused but harmless** (no reader references it at the D108 baseline).

> **🔴 DEPLOY CAUTION — `wolfe_overlay.py`.** The flip hazard is **resolved at the git level**: main's `wolfe_overlay.py` now carries BOTH the D109 lifecycle (Open/Closed) layer *and* the D113 draw tool together. But the earlier D111 point-4 incident showed a full-file `scp` of a **stale** file reverting shipped work — so the rule stands: **deploy `wolfe_overlay.py` / `wolfe.py` from main's CURRENT file, never a stale copy**, and keep a pre-deploy backup (`wolfe_overlay.py.bak-*`).
>
> **↻ Re-persist the scan after any `wolfe.py` scoring / detection / winner-profile deploy — MANDATORY final step.** `/dash/wolfe/scan` serves the nightly `wolfe_signals` snapshot by default (only the Mon–Fri 16:00 UTC `hermes-wolfe-scan` timer rebuilds it), so a scoring deploy leaves the DEFAULT scan showing the OLD code's names until the next nightly — up to ~3 days across a weekend (the `?refresh=1` / `/dash/wolfe` / `/dash/stock` overlay paths recompute live and are already current). Run it DIRECTLY (never `systemctl start` the timer — AUD-95 fires the job via `Requires=`): `cd /opt/hermes && ./.venv/bin/python -m src.automation.wolfe --persist-scan --universe nifty500` — writer-safe, an atomic single-transaction replace that rolls back on any failure (Friday's snapshot survives). Verify stdout reports `nifty500` + a sane count + today's `computed` (a wrong `--universe` is a silent no-op). *(Panel-decided 2026-07-11 after the D111/point-4 deploy left the snapshot a day stale; refreshed 63→64.)*

## 6. Data & provenance

- **Input:** `bhavcopy_rows` (NSE daily bhav copy — `trade_date, open, high, low, close, volume`) per symbol, corporate-action-adjusted via the production adjuster (`src.automation.adjust`). Universe from `nse_equity_list`, default **Nifty 500 daily**; an `inclusive` (delisted-aware, survivorship-honest) universe is available on the scanner.
- **Primary source only.** NSE bhav copy — no vendor, no Screener dependency (CLAUDE.md Guardrail #8). Pure-stdlib detector, no LLM, ₹0.
- **Point-in-time / no-look-ahead (mandatory, [wolfe-rules.md](../wolfe-rules.md) §C).** Every scan takes an *as-of date*; the result as-of *t* is **byte-identical whether or not bars after *t* exist**. Naturally PIT-honest: a fractal-N pivot confirms only N bars after its candle (points 1-4 carry their real delay); point 5 = the live candle extreme (seen immediately — exactly why it has no fractal gate). This one capability powers both ad-hoc historical review and the §C backtest.

## 7. Terminology canon

- **Fractal gate** — the MANDATORY 2/3/4 ≥ 2-fractal detection rule (D108). Preference order everywhere: **10 > 5 > 2 > candle**. Point 1: no gate (fractal = bonus). Point 5: no gate (entry timeliness).
- **EPA** — Estimated Price at Arrival; the **1-4 line**, the reversal target. Drawn only after point 5 confirms.
- **Spring-and-reclaim (§A9)** — point 5 pierces the confluence zone by ANY depth then reclaims it (support→resistance flip breached back); the reclaim, not the depth, is the strong-reversal tell (C component, D111).
- **"Touched not cut" (H)** — a candle within 0.3% of the EPA/1-4 line, one side only, *touches* it (confirms S/R); a candle slicing through *cuts* it (does not count). Scale to >4 touches → 3.
- **§B components (8; max = `_QUALITY_MAX`, currently 27)** — A point-1 · B symmetry · C point-5 placement · F zone narrowness · G confluence-zone-nearest-price (0–4) · H touched-not-cut · I RSI divergence · D direction/context. Strength = several agreeing at once; **freshness is NOT strength**.
- **Lifecycle** — **Prediction** (no point 5) · **Open** (point 5, EPA untouched — actionable) · **Closed** (EPA touched — reference), with a closure-neatness readout.
- **Winner profile** — the OOS-validated selection filter (reachable EPA + strong point-1 + not-narrowest zone); the §B *total* INVERTS as a trade filter, so the scanner uses the winner profile, not raw Q.

**⚠️ DEPRECATED — historical only (REMOVED from code by D108).** The **STR/LND** split (STR = shape /11, LND = landing /13), **structure-watch**, **attention rank** (`rank_attention = Q × 0.5^(age/60)`), the **§B2 "not entry-qualified" withhold queues**, and the D101/D102 **lifecycle queues / progress chips** are **no longer in the code**. They survive as design in [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md) and as history in [PROJECT_STATE.md](../../PROJECT_STATE.md) (D98–D102) for the methodical re-apply *with* Ramana. Do not cite this vocabulary as current behaviour. **Also:** "D111 = the draw tool" is a **deprecated** memory-era label — **D111 is the §B rescore; the draw tool is D113** (merged, S112).

## 8. Decision & session history

Terse chronological (full entries in [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log / Session log):
- **D70** (S40) — the SELL setup is fixed as an ascending wedge; convention locked.
- **D96** (S86c, `9d04bd9`) — the ◄/► walk gets a **freshness guarantee** (`_FRESH_KEEP_BARS=250`); a quality cap must never gate recency. **This is the reverted-to baseline.**
- **D98–D102** (S89) — STR/LND split + structure-watch (D98), attention rank (D99), §B2 withhold (D100), lifecycle state queues + event-driven EPA (D101), progress chips + CLOSED chips (D102). **All later REMOVED by D108** (history only).
- **D108** (S105, `0c89e8f`) — **REVERT to the D96 baseline + the MANDATORY 2/3/4 fractal gate**; the D98–D102 layer removed. §A geometry + §B math untouched.
- **D109** (S106, `2541009`) — the overlay's **three lifecycle sections** (Prediction / Open / Closed), simple and non-hiding, re-added on the D108 baseline (Ramana: "I asked for three sections").
- **S107** (`f7d7a87`) — overlay badge (dir · points/total · rank); chart stays STATIC on nav (no re-zoom).
- **D111** (2026-07-11, S109, `dfbe175`) — **the §B quality score REBALANCED to Ramana's exact spec** (max 25 at the time; A flat 1/4 · C spring-and-reclaim §A9 · G extension-depth · F 0–4 · H touched-not-cut >4→3 · I divergence-reference fixed · 2.0 restored). His TCS wave 13→**18** (25-scale). §A geometry + D108 gate + `find_p5` untouched. **The §B freeze is thereby lifted.**
- **Post-D111 G refinement** (`d5551cc` → `9350974`, Wolfe lane) — G widened 0–2 → **0–4** (the confluence zone **nearest the current price**, by ratio depth; the interim "anywhere in the wave" reading was reverted), lifting **`_QUALITY_MAX` 25 → 27**.
- **D113** (2026-07-11, S112, `35a11e7`) — **the draw tool MERGED to main**: `✎ draw your own` auto-snap (points 1/3/5→lows, 2/4→highs), auto-EPA the moment point 4 lands, STRICT 1-2 ≥ 3-4 gate, double-click point-edit — draw-mode JS only, zero `wolfe.py`/scoring touch. (Renumbered from the draw-lane's provisional "D111", which the §B rescore claimed; the abandoned branch commit `8fc40dc` was not used.)
- **Winner-profile OOS re-validated** (2026-07-11) — the committed `phase2_oos.py`/`phase3_betacontrol.py` harness re-run read-only on the VPS archive under the rebalanced scoring: the 2004-14 fit **re-derives the identical `D≤1 · p1≥2 · F≤2`** (F 0–4 neutral to the filter), BULL edge intact (test medNet **+4.4%**, α **+5.07**), **placebo-gap negative everywhere** (selection-not-craft reaffirmed). **Softer than the June baseline** (post the D108 gate): inclusive winner medNet **+2.14%→+0.81%**, BEAR **+1.03%→−0.98%** → inclusive verdict now **IN-SAMPLE-ONLY**, nifty500 **SURVIVED** (point-estimate). Point-4 reconciliation confirmed **neutral** (A/B, `_reconcile_point4` disabled = +0.78% vs +0.81%). Numbers folded into §4; descriptive-only unchanged.

## 9. Open items / frozen work

- **Point-4-strength descriptor** — recorded, NOT built; **BLOCKED on Ramana's worked chart example**. His method detail: point 4 is strong where the legs **1-2 ∩ 2-3** Fib confluence intersect (a *different* leg pair than the point-5 zones' 1-2 ∩ 3-4). ([wolfe-rules.md](../wolfe-rules.md) §D item 4.)
- **D98–D102 methodical re-apply** — the removed recency/STR-LND/structure-watch/attention/lifecycle-queue estate is designed in [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md), to be re-added *with* him on the D108 baseline, not rebuilt unilaterally.
- **D95 tape-wiring** — pass `corp_actions` events into Wolfe's adjust path so split/bonus history is tape-primary like the other consumers (owner = Wolfe lane).
- **§C backtest spec = frozen appendix** — the point-in-time as-of / backtesting rules ([wolfe-rules.md](../wolfe-rules.md) §C). The backtest is DONE and decoded; it is the descriptive-only *gate*, and it earned the label ("survived true OOS"), not the role. Do not re-run merge/derive without cause.

## 10. Sources of truth

- **Deep design / intent / history:** [wolfe-wave-design.md](../wolfe-wave-design.md)
- **Rules of record (§A geometry LOCKED · §A9 spring-and-reclaim · §B3 ratified scoring · §C PIT/backtest):** [wolfe-rules.md](../wolfe-rules.md)
- **Re-apply run-book (★ fractal-focus brief + the removed D98–D102 estate):** [wolfe-NEXT-SESSION.md](../wolfe-NEXT-SESSION.md)
- **Weights / constants (live in code; the ratified §B):** [src/automation/wolfe.py](../../src/automation/wolfe.py) (`_QUALITY_MAX`, currently 27; `_FIB_R`) + [calculations-and-weights.md](../calculations-and-weights.md) §5c/§5d
- **Strategy ledger (Wolfe row — descriptive/selection class):** [strategy-ledger.md](../strategy-ledger.md)
- **Memory:** `[[wolfe-wave-strategy]]` (the canonical running record — split-by-side, §C trade-mechanics appendix). ⚠ Its "D111 = draw tool" line is superseded — D111 is the §B rescore; the draw tool is **D113** (merged, S112).
- **Decisions:** [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log — D96 / D108 / D109 / D111 / D113.

## Maintenance

- **§B is ratified (D111), not frozen** — and still being refined by the Wolfe lane (G widened → `_QUALITY_MAX` = 27). This page references `_QUALITY_MAX` rather than a hard-coded max so it does not re-stale; if the components change again, update **this doc + [wolfe-rules.md](../wolfe-rules.md) §B3 + `_QUALITY_MAX`** together.
- **Draw tool + lifecycle are merged (D113 / D109).** The §5 note is now a deploy caution (ship main's current `wolfe_overlay.py`, never a stale copy), not a flip hazard.
- **Never restate weights/thresholds here** — link to code + [wolfe-rules.md](../wolfe-rules.md) §B3. This page fixes *definition, status and terminology*; the numbers live once, in code.
