# Harmonic Patterns (XABCD / PRZ) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** LIVE (descriptive) · backtest-GATED · **Governing decision(s):** D72 (harmonic lane) · D71 (charting-overhaul parent) · **Reconciled:** 2026-07-11 (S111).
> **Origin:** 📚 CLASSIC (Gartley/Carney XABCD harmonic-pattern literature) + 🏠 HOUSE implementation (PIT detector + PRZ scoring on our archive). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for the harmonic lens. Deep design: [harmonic-pattern-design.md](../harmonic-pattern-design.md). Numbers live in code + [calculations-and-weights.md §5h](../calculations-and-weights.md); this page never restates a ratio constant — it links.

**One-line definition:** Harmonic patterns are five-point (X-A-B-C-D) price structures whose leg lengths match a named Fibonacci-ratio template (Gartley · Bat · Butterfly · Crab · Deep Crab), completing at a **D-point** inside a **Potential Reversal Zone (PRZ)** where the prior swing is expected to reverse.

---

## 1. What it is

A harmonic pattern reads a run of price as five alternating swing pivots — **X → A → B → C → D** — and asks whether the four legs between them fall into the Fibonacci proportions of a *named* pattern. When they do, the **D-point** marks a **Potential Reversal Zone (PRZ)**: the price cluster where the pattern "completes" and the market is expected to turn. Direction is read off D — a D that prints a swing **low** is **BULL** (reverses up); a D that prints a swing **high** is **BEAR** (reverses down).

Our implementation surfaces two states:

- **CONFIRMED** — all five pivots X-A-B-C-D are locked (D has printed); a reversal *candidate*.
- **FORMING** — X-A-B-C have printed and D has not; the scanner projects the **PRZ** where a valid D would complete (the "catch it forming, down the stream" ask from the chart-redesign §13 audit).

It is a **geometry / selection lens**, not a trading trigger. Detection is the cheap part; whether any pattern × timeframe carries a real forward edge on our universe is a separate, backtest-gated question (§4).

## 2. Our variation vs. the standard technique

**Standard harmonic trading** (Gartley/Scott Carney lineage) is a *manual, discretionary* craft: an analyst eyeballs an XABCD, drops Fibonacci retracement/extension tools on the legs, and trades a reversal off the PRZ. Ratios, tolerances, and which patterns "count" vary by author.

**Our variation** turns that into an **automated, mechanized, universe-wide scanner** with an explicit honesty gate:

- **Auto-detected XABCD**, not hand-drawn — pivots come from the shared Wolfe pivot engine (ATR-zigzag on split-adjusted daily bars), and the four legs are matched against a codified ratio-template library.
- **Codified tolerance bands + a fit score.** Each pattern is a set of acceptance bands (AB/BC/CD and the defining AD ratio) plus an `ideal` per leg; a match requires **all four bands simultaneously**, and a 0–1 **fit score** measures closeness to the ideals. Exact bands live in code (`HARMONICS` in [harmonic_patterns.py](../../src/automation/harmonic_patterns.py)) and the design-doc ratio table — this page never restates them.
- **A FORMING/PRZ projection.** Beyond confirmed patterns we project the reversal zone for an in-progress X-A-B-C — the differentiating "catch it forming" capability.
- **Descriptive, read BY SIDE.** The scanner tags each row `edge` (BULL) or `tail` (BEAR) from the reliability backtest, and it is labelled "not a buy/sell signal" on the surface itself.
- **Deliberate scope discipline.** v1 encodes only the *five well-agreed* templates. **Cypher / Shark / Three-Drives** use different leg references (XC, 0-X-A-B-C, three symmetric drives) whose published ratios vary by source — deferred rather than encode a dubious template that would poison the backtest. **Elliott** is deferred entirely (subjective auto-counting).

Where it sits in the stack: it is one lens in the charting overhaul (D71, the "CPR Spine" chart), a **sibling to the Wolfe Wave lane** — it reuses Wolfe's pivot machinery read-only and draws onto the same shared candle chart as an optional overlay chip, so CPR / MEP / MA / RS / Wolfe all coexist with it.

## 3. How it works (methodology)

```
daily OHLC (NSE bhav, split-adjusted)
        │  (optional W/M resample — resample_series)
        ▼
ATR-zigzag pivots  ──(reused read-only from wolfe.py)──►  alternating H/L swings
        ▼
slide a 5-pivot window (X,A,B,C,D)
        ▼
structure gate  →  leg ratios AB · BC · CD · AD  →  match to a named template (all 4 bands)
        ▼
   ┌── CONFIRMED (D locked)         → fit score, RSI at D, direction from D
   └── FORMING  (X-A-B-C, no D)     → project PRZ = cluster of candidate D levels
```

1. **Pivot / swing detection.** `stock_series` builds a split-adjusted OHLC series; ATR-zigzag (or fractal) reduces it to alternating swing highs/lows — the same primitives the Wolfe lane uses.
2. **XABCD legs.** For each consecutive 5-pivot window a **structure gate** enforces strict H/L alternation and the monotonic frame (B is a real XA retrace, C sits between, D is the turn), then the four leg ratios are computed: **AB**, **BC**, **CD**, and **AD** — where AD (D's position vs the XA leg) is the *defining* ratio.
3. **Fib-ratio matching.** Each candidate is tested against every template's acceptance bands; a match requires all four bands at once (the ratios are mutually constrained, which is what forces a *real* pattern). The best-fitting template wins, scored by mean closeness to its ideal AB/CD/AD.
4. **PRZ projection (forming).** For an in-progress X-A-B-C, only templates whose AB the leg already satisfies can still complete; each projects a candidate D from its AD ratio, and the cluster of those levels becomes the **PRZ** (lo/hi/mid).

**Ratio constants are NOT restated here.** They live in code (`HARMONICS` in [harmonic_patterns.py](../../src/automation/harmonic_patterns.py)) and, illustratively, in [harmonic-pattern-design.md](../harmonic-pattern-design.md) §2. If the two ever disagree, **code is authoritative** (a couple of AD bands were widened slightly in code vs the design table — see §8).

## 4. Status, validation & honesty fence

**LIVE but DESCRIPTIVE and backtest-GATED.** The scanner and the chart overlay are in production; the *edge claim* is not. Consistent with project doctrine, the harmonic lens is a **SELECTION shape — tail-carried, not a validated fundable book** (the same characterization the strategy ledger applies to Wolfe/Ignition, and that PEAD-delivery was grouped into).

The reliability gate ([harmonic_backtest.py](../../src/automation/harmonic_backtest.py), run 2026-06-28 on a survivorship-**inclusive** universe, 1,052 confirmed patterns, entry lagged 5 bars after D, signed by reversal direction, vs same-horizon **directional drift**) found:

- **BULL harmonics** show a *modest, real, fit-graded* selection edge that beats long-drift at every horizon (Gartley-bull strongest), and the ratio-fit score **stratifies** outcomes (higher fit → better) — the same shape as Wolfe's Q stratification.
- **BEAR harmonics ≈ short-drift** — no edge beyond drift; reliable only when the broad tape is weak → ⚠ tail/regime, not a standalone edge.

The full result table and per-pattern breakdown live in [harmonic-pattern-design.md](../harmonic-pattern-design.md) §3 — this page links rather than restates.

**Honesty fence (binding):**
- Do **not** claim a validated return edge. Medians are a few percent, the D-confirmation timing carries the same look-ahead caveat as the Wolfe/Ignition backtests (mitigated, not eliminated, by the 5-bar lag), and **no fundable book net of realistic cost is claimed.**
- The lens is surfaced to **sharpen the eye** (where to look, and by which side), never as a mechanical buy/sell trigger. It stays descriptive until — and unless — a leak-free, cost-aware construction clears the gate.

## 5. Where it lives (code · routes · DB · timers)

**Code (all NEW, harmonic-lane-owned; reuse `wolfe.py` READ-ONLY):**

| File | Role |
|---|---|
| [src/automation/harmonic_patterns.py](../../src/automation/harmonic_patterns.py) | Detector — ratio-template library, per-type validator, structure gate, forming-PRZ projection, D/W/M resample, selftest. |
| [src/automation/harmonic_signals.py](../../src/automation/harmonic_signals.py) | Scanner + nightly-persisted `harmonic_signals` snapshot (`scan` / `persist_scan` / `latest`). |
| [src/automation/harmonic_backtest.py](../../src/automation/harmonic_backtest.py) | Reliability gate — survivorship-inclusive forward-outcome backtest vs directional drift. |
| [src/web/harmonic_view.py](../../src/web/harmonic_view.py) | `/dash/harmonic` scanner page + `/dash/harmonic/overlay` JSON feed. |
| `src/web/stock_chart.py` (shared) | The **Harmonic chip** — draws each pattern's X-A-B-C-D polyline + point markers + the forming PRZ band on the candle chart (`window.__wfpc`, autoscale-opt-out). |
| `scripts/hermes-harmonic-scan.{service,timer}` | Nightly persist unit. |

**Reused from `wolfe.py` (read-only):** `zigzag`, `atr`, `fractal_pivots`, `stock_series`, `rsi`, `scan_universe`, `Pivot`.

**Routes:**
- `GET /dash/harmonic` — the scanner page (reads the nightly snapshot for the daily TF; live fallback; W/M is always a live multi-TF scan). Rows click through to `/dash/stock`.
- `GET /dash/harmonic/overlay?sym=…` — JSON of a symbol's confirmed + forming patterns for the candle-chart overlay.
- **Mounting:** `harmonic_view.router` is nested into the already-mounted `wolfe_view` router via `router.include_router(...)` — **no `main.py` edit**, committed, survives a redeploy (cleaner than the older in-place overlay hooks).

**DB:** table **`harmonic_signals`** — **module-owned** (CREATE-IF-NOT-EXISTS inside `harmonic_signals.py`; **`db.py` / `SCHEMA_BASE` untouched**, same isolation pattern as Wolfe's `wolfe_signals`). Columns: `universe, sym, pattern, dir, state (CONFIRMED|FORMING), score, cmp, d_price, prz_lo, prz_hi, in_zone, rsi_d, age, tag (edge|tail), scan_date, computed_at`. Written as a clean per-universe snapshot (DELETE-then-INSERT); indexed on `(universe, in_zone DESC, age ASC)`.

**Timer:** `hermes-harmonic-scan.timer` runs `python -m src.automation.harmonic_signals --persist-scan` nightly Mon–Fri **16:10 UTC** (after bhav → signals and the Wolfe scan). **No LLM** in the scheduled path (Guardrail #3 compliant).

## 6. Data & provenance

- **Source:** split-adjusted daily OHLC from the **NSE bhav copy archive** (via `wolfe.stock_series` → `bhavcopy_rows` / `stock_signals`). A **PRIMARY source** — no vendor or Screener.in dependency (Guardrail #8 compliant).
- **Universe:** `nifty500` for the live scanner; **survivorship-inclusive** (top-liquid incl. delisted) for the backtest gate, so the reliability read is not a survivor mirage.
- **Point-in-time:** a zigzag pivot only confirms *after* price has swung away, so detection introduces no look-ahead beyond what the pivot detector already needs; the backtest adds a 5-bar entry lag after D (non-repaint). Forming-PRZ dates are re-snapped onto the current bars so overlays survive the D/W/M/Q resample.
- **Multi-TF:** detection is validated **daily**; W/M detection resamples the daily series (`resample_series`) and is treated as a hand-off pending its own re-gate (§9).

## 7. Terminology canon

- **XABCD** — the five swing pivots that define the pattern. **X** = origin; **A/B/C** = intermediate swings; **D** = the completion / reversal point.
- **Legs & ratios** — **AB, BC, CD**, and **AD** (the *defining* ratio: where D sits relative to the XA leg). Exact acceptance bands + ideals are in code; not restated here.
- **PRZ (Potential Reversal Zone)** — the projected price cluster where a still-forming pattern's D would complete a valid template; the "catch it forming" band (lo/hi/mid).
- **Pattern family** — **Gartley · Bat · Butterfly · Crab · Deep Crab** (v1). Cypher / Shark / Three-Drives deferred (source-varying ratios); Elliott deferred entirely.
- **State** — **CONFIRMED** (five pivots locked, D printed) vs **FORMING** (X-A-B-C printed, D projected into the PRZ).
- **Direction / side** — read off D: D a swing **low** ⇒ **BULL**; D a swing **high** ⇒ **BEAR**. Surfaced as `tag` = **edge** (BULL) / **tail** (BEAR), the backtest's by-side read.
- **Fit score** — 0–1 closeness of the AB/CD/AD ratios to their template ideals; stratifies outcomes in the backtest.

**Disambiguation — Harmonic vs. Wolfe Wave.** Both are **five-point geometries built on the same pivot engine**, but they are *different techniques*: **Wolfe Wave** is defined by trendline/channel *symmetry* and an EPA (estimated price & arrival) target line; **Harmonic** is defined by **Fibonacci leg-ratio templates + a PRZ**. Do not conflate the two. See the sibling canonical reference: [wolfe-wave.md](wolfe-wave.md).

## 8. Decision & session history

- **D71 (S41, 2026-06-24)** — Charting overhaul: build our own chart on lightweight-charts ("inspired, not a copy"), the "CPR Spine" signature + four-family control bar. Its §13 capability audit anticipated a dedicated harmonic lane.
- **D72 (S41, 2026-06-24)** — Harmonic patterns = a **NEW strategy lane** (auto-detect FORMING patterns + screen + backtest), reusing the Wolfe engine; **harmonics-first, Elliott deferred**; **backtest reliability BEFORE trusting**.
- **S48 (2026-06-28) — Lane G:** scaffolded the detector + nightly scanner + the reliability benchmark; backtest run on the VPS (1,052 confirmed patterns) recorded the by-side read (BULL modest edge / BEAR tail). Nightly timer enabled; 143 setups persisted (12 in-zone).
- **S49 (2026-06-29) — Lane G2 (`1eeae16`):** surfaced in the live UI — `/dash/harmonic` scanner + the chart Harmonic chip — **browser-verified LIVE** (MARICO Gartley-bear + CANHLIFE forming Gartley/PRZ drawn on candles; CPR/MEP/Wolfe/RS coexist; zero console errors), with **zero frozen-file edits**. Cross-linked from the Wolfe scanner (no orphan).
- Later: the harmonic chart overlay gained a ◀▶ stepper + pattern-name label (`0c6975d`).
- **Nav (resolved):** per the orphaned-screen doctrine, Wolfe/Harmonic stay chart overlays **and also** get a market-wide **Markets "Patterns"** scanner nav lens — so `/dash/harmonic` is reachable via the nav, the Wolfe cross-link, and direct URL (no longer an orphan; the design §5 "nav entry" hand-off is closed).

## 9. Open items / frozen work

- **THE GATE (governing open item):** the harmonic edge stays **DESCRIPTIVE** until a leak-free, cost-aware construction beats its directional baseline net of cost. Same posture as Wolfe — surface the selection, never sell a book.
- **Multi-TF detection (W/M):** the engine resamples and the scanner/overlay carry a `tf` param, but the *validated* backtest is daily-only — true W/M needs weekly/monthly bars fed to detection **+ a re-gate**.
- **Drawing persistence → SQLite:** overlay drawings persist in `localStorage` (per-browser); a per-user × symbol table + save/load endpoints would make them cross-device.
- **The moat (chart §13):** fuse the harmonic D-zone with proprietary **DVPT-accumulation + RS + CPR** confluence — a pattern completing where institutions are accumulating — as a confluence column on the scanner.
- **Bull-focus:** a BULL-only screen + tighter score gate (the edge is bull-side).
- **Template expansion:** Cypher / Shark once specs are pinned · Three-Drives · a `strategy_registry` card reading `harmonic_signals` for `/dash/strategist`.

## 10. Sources of truth

- **Design of record:** [harmonic-pattern-design.md](../harmonic-pattern-design.md) — ratio-template table (§2), the reliability benchmark (§3), scanner/UI (§4–§5b), open/next (§5).
- **Strategy ledger:** [strategy-ledger.md](../strategy-ledger.md) — Tier-3 built analytical lenses ("Wolfe / Ignition / theme tags"); the Wolfe/harmonic **SELECTION-shape, tail-carried** characterization.
- **Canonical numbers:** [calculations-and-weights.md §5h](../calculations-and-weights.md) — the XABCD ratio bands (`HARMONICS`) + PRZ projection (`_FIB_CD`) are now folded in there (explains the code; code stays canonical).
- **Code:** [harmonic_patterns.py](../../src/automation/harmonic_patterns.py) · [harmonic_signals.py](../../src/automation/harmonic_signals.py) · [harmonic_backtest.py](../../src/automation/harmonic_backtest.py) · [harmonic_view.py](../../src/web/harmonic_view.py).
- **Memory:** `charting-overhaul-cpr-spine` (harmonic lane built + surfaced, XABCD+PRZ, descriptive).
- **PROJECT_STATE:** [PROJECT_STATE.md](../../PROJECT_STATE.md) § Decision log (D71/D72), § Session log (S48/S49), § Database schema (`harmonic_signals`), § Telegram/nav (Markets "Patterns" lens).
- **Sibling geometry lens:** [wolfe-wave.md](wolfe-wave.md).

---

## Maintenance

- **Link, never duplicate.** Ratio constants stay canonical in code (`HARMONICS`) and are explained in [calculations-and-weights.md §5h](../calculations-and-weights.md); update both together when a band changes.
- **Code is authoritative over the design table.** If `harmonic_patterns.py` and design §2 disagree on a band, the code wins; reconcile the design doc, not this page.
- **Keep the fence intact.** Any promotion beyond "descriptive / backtest-gated" requires a recorded, leak-free, cost-aware gate result (§4) and a new Decision-log entry — do not soften the honesty fence without it.
- **On change:** new templates, a W/M re-gate, or a confluence column update §2/§5/§9 here and the design doc; bump **Reconciled** and add a Decision/Session pointer in §8.
