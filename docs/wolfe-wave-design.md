# Wolfe Wave — the structural reversal-setup lens (mechanical 1-4 + Ramana's Fib point-5)

> **Status:** BUILT + LIVE on the VPS (Phases 1–3), **DESCRIPTIVE-ONLY**. Convention fixed
> 2026-06-24 (D70) — the SELL setup is an **ascending wedge (L,H,L,H, lows & highs rising)**, point 5 =
> the upper Fib-confluence zone (matches Ramana's PARAS drawing → 1226). The edge backtest (#4) was run
> (PIT-honest) and showed **no mechanical edge** at confirmation → the lens stays descriptive (no
> buy/sell verdict), as the doctrine requires. **§2's bearish paragraph below is SUPERSEDED** by the
> convention in `docs/wolfe-NEXT-SESSION.md` §7 (read that for the authoritative pivots/rails/labels).
>
> **Division of labor (the spine):** Hermes detects & validates **points 1·2·3·4** mechanically over
> the NSE bhav-copy archive — point-in-time safe, ₹0 / no-LLM, descriptive-only. **Ramana's
> Fib-confluence method owns point 5** (extend legs 1-2 & 3-4 → matched-ratio bands → narrow band =
> high-prob reversal). Phased; each phase gated and signed off separately.
>
> **Defaults:** the four parameter questions went unanswered, so the **Recommended** options are taken as
> the working defaults — all overridable (§10): *phase it (1-4 now, 5 after) · "narrow" measured in ATR ·
> full ratio set 1.272/1.414/1.618/2.0/2.618 · Nifty 500 daily.*
>
> **Viz caveat:** the earlier mock chart pictures were **rejected** by Ramana. NO wave annotation will be
> rendered in production until the on-chart geometry is confirmed against his drawing (§3, §9-P3). The
> *textual* convention below (1 high, 2 low, 3 lower-high, 4 lower-low) is the confirmed-correct one.
>
> Keep this doc rich ([[preserve-strategy-intent]]); do **not** one-line it.

## ✅ VALIDATED METHODOLOGY (2026-06-24 — supersedes §2/§3/§4 below where they differ; live impl detail in `docs/wolfe-NEXT-SESSION.md` §0)

Pinned down with Ramana this session against his Fyers PARAS charts (75-min + daily). Treat this as the working spec; he notes residual misunderstandings remain, so re-confirm before extending.

- **Pivots:** he marks them with **Fyers Fractals (2) & (10)**. patearn proxies with an **ATR-zigzag** on **daily** bars, scales **k ∈ {1.0, 1.5, 2.5}** (fine = recent tight wave, coarse = bigger monthly wave). Daily fractals are too sparse in a trend to give 5 clean points; his exact pivots may be 75-min/discretionary (a data-resolution limit, not a bug — he declined intraday data).
- **Convention (LOCKED — do not rewrite):** **BEAR/sell = ascending, pivots H,L,H,L** (point 1 = a HIGH; 1·3 ascending highs; 5 = a high overshooting the 1-3 line; reverse down). **BULL/buy = descending, pivots L,H,L,H** (point 1 = a LOW; descending lows; 5 = a low overshooting the 1-3 line; reverse up).
- **Point 5:** NOT confirmed until price **crosses the extended 1-3 line** — above for a bear, below for a bull — and it **may keep extending**.
- **Two waves:** surface the two most-recent, clearest waves (can be nested, sharing point 5).
- **Fib targets:** a standard **EXTENSION fan** on each thrust leg (1→2 and 3→4), anchored at the leg low, projected toward the overshoot. **EXTENSIONS ONLY (>1.0): 1.272, 1.414, 1.618, 2.618, 3.618, 4.236, 4.618** — the 0.236–1.0 retracements are *inside* the leg and are NOT used for overlaps. Where a leg-1-2 extension coincides with a leg-3-4 extension (~0.4 %) = the **strong target zone**. Validated: PARAS 968.1→1066.75 & 1075.5→1133 → **2.618∩2.618 = 1226.2**.
- **Render on CANDLES only** (a line chart hides the intraday spikes the pivots sit on).
- **Descriptive-only:** the PIT edge backtest is un-run; no buy/sell verdict yet.
- **Open calibration (his call):** include 2.0? · overlap tolerance 0.4 % vs ~0.5–0.6 %? · draw retracement levels for context (display only)? · EPA/target direction for bears? · match his exact fractal pivots (fractal reader / manual swing input)?

---

**The one-sentence claim:** every lens patearn has today — DVPT, RS/RRG, MEP, rs-band — scores a *state*
(momentum, level, accumulation). This scores a *structural setup*: a specific 5-point geometry that, when
symmetric, yields a high-probability reversal **zone**, a defined **target**, and an estimated **time**.
It is the first *pattern / geometry* lens in the stack, and it is orthogonal to everything else — a setup
can exist regardless of where RS or DVPT sit, and those then become the *confirmation* (§5).

---

## 1. The idea (Ramana's words)

A Wolfe Wave is a 5-pivot reversal structure. Points **1-4** define a symmetric channel; point **5** is
the overshoot where price reverses, with a target drawn from the **1→4 line (EPA)** and an arrival time
from the same diagonal.

Ramana's edge is in locating **5**: take the two symmetric thrust legs — **1→2 and 3→4** — and run a
**Fibonacci extension off each**. Because the legs are near-parallel and similar in size, their extension
grids are shifted copies, so certain ratios from leg 1-2 land almost on top of ratios from leg 3-4 →
**confluence bands**. A **narrow** band (tight agreement of several ratios) = high-probability zone for 5.
If price **breaks** that band without reversing, roll to the **next narrow band**; the reversal then comes
**either at that next band, or on the *return* back into the band that just broke** (the broken band flips
and triggers on re-entry).

The quiet load-bearing assumption is **Wolfe symmetry (leg 1-2 ≈ leg 3-4)** — the more symmetric the two
legs, the tighter his bands. That is exactly the property Hermes can validate mechanically. So: **Hermes
finds and ranks 1-4 (and locks them), hands over the two leg vectors; Ramana's Fib method owns 5.**

---

## 2. The geometry we detect (the proper Wolfe convention — REBUILT 2026-06-23)

**Bullish setup (buy at 5) — a falling structure:**
- **1·3·5 = descending LOWS**, **2·4 = highs**.
- 3 < 1 (lower low); 5 < 3 and 5 **overshoots the 1-3 line** (the descending support), then reverses **up**.
- Symmetry: leg **1-2 ≈ leg 3-4** (the two up-legs within the fall).
- **Target / EPA = the 1-4 line** — from 1 (low) to 4 (high), so it **slopes up** = a real upside target.

**Bearish setup (sell at 5):** the exact mirror — **1·3·5 = ascending HIGHS**, 2·4 lows; 3 > 1; 5 > 3 and
overshoots the 1-3 resistance, reverses **down**; EPA = the 1-4 line (slopes down).

**Valid wave:** leg 1-2 ≈ leg 3-4, the 1-3 line trends, 5 overshoots it, target = the 1-4 line.

> ⚠️ **Correction (2026-06-23):** earlier drafts used a WRONG "1 high · 2 low · 3 lower-high · 4 lower-low"
> labelling — that is **not** a Wolfe wave and made the 1-4 EPA slope the wrong way (no upside). The
> convention above (1·3·5 = the same extreme) is canonical and is what the rebuilt detector enforces.
> Ramana's point-5 Fib overlay (his legs-1-2/3-4 confluence) is being re-attached onto this correct
> structure — see §4. The target uses **Fibs drawn off the 4→5 leg, combined with the 1-4 line** (his
> "combination").

---

## 3. Method — points 1-4 (the part Hermes owns)

### 3a. Swing extraction
Convert each symbol's price series into an alternating swing-high/low sequence.
- **Primary: ATR-normalized ZigZag.** A new pivot is confirmed when price reverses by ≥ `k · ATR(14)`
  from the running extreme. ATR (not %) so the same `k` is comparable across a ₹50 and a ₹5,000 stock and
  across volatility regimes — consistent with the repo's regime-aware style (cf. rs-band's log-space,
  recency-weighted choices).
- **Scale is the #1 knob.** Default `k ≈ 1.5`. Scan a **small multi-scale grid** (`k ∈ {1.0, 1.5, 2.25}`)
  so waves of different sizes surface, then **dedupe** overlapping candidates (keep the higher-quality).
- No existing zigzag/fractal code in the repo — this is built fresh in `research/wolfe_waves/` first.

### 3b. Candidate enumeration + structural validation
Slide over the alternating pivot list; take every consecutive `(1,2,3,4)` and validate (bullish; mirror for
bear):
1. **Alternation** L,H,L,H  (1·3 are the lows, 2·4 the highs).
2. **3 < 1** (descending lows) and the **1-3 line trends down** — the falling structure.
3. **Symmetry — the high-value filter:** leg 1-2 ≈ leg 3-4 in **both** price height *and* bar-count.
   Tolerance band, default `0.6–1.6×` — the single most predictive 1-4 filter.
4. **Point 5** = the next low (after 4) that breaks below point 3 **and overshoots the 1-3 line** →
   `CONFIRMED`; if no such pivot yet → `FORMING` (project the zone). Mirror (highs) for bearish.
5. *(optional)* **channel sanity** + **2→3 retrace** within a Fib range.

> Implemented in `src/automation/wolfe.py` (`detect_waves`) and validated by
> `research/wolfe_waves/selftest.py` — bullish reads L,H,L,H with 3<1, EPA slope > 0, 5 confirmed; bearish
> the mirror; a flat oscillation is rejected.

### 3c. Quality score → tier
Score each survivor by symmetry (price & time), channel cleanliness, and retrace position → `quality_score`
→ `quality_tier ∈ {HIGH, MED, LOW}`. **Score, don't hard-gate** — the best-scoring 1-4 are exactly the ones
where Ramana's bands come out narrowest, so the two stages reinforce.

### 3d. Point-in-time / no-look-ahead (non-negotiable)
The structure as-of date *t* uses only bars ≤ *t*. Add the same invariant test rs-band uses: the emitted
1-4 for date *t* is **byte-identical** whether or not future rows exist in the DB.

### 3e. Point-4 lock / repaint guard (non-negotiable)
Point 5 forms *after* 4, so 4 must not still be forming. The most-recent pivot is **provisional** until
price has moved ≥ `k·ATR` past it. Emit `p4_locked = 1` only once confirmed; **hand Ramana nothing** (no
leg vectors, no band) until then. This is the difference between a real setup and a repaint.

### 3f. Output
One latest row per `(symbol, timeframe)`: the four pivots (price + date), the lock flag, the two **leg
vectors** (height + bars), symmetry metrics, the swing scale that produced it, quality, and the **EPA
target** (1→4 projection) + ETA. Schema in §8.

---

## 4. Method — point 5 (automating Ramana's Fib method) — **Phase 2, separately gated**

Only built after 1-4 is validated. Mechanizes Ramana's method so it can be scanned nightly; he can still
override by eye.
- **4a. Fib engine.** Extend legs 1-2 & 3-4 with the ratio set (default 1.272/1.414/1.618/2.0/2.618).
  Project each leg's levels; find **matched-ratio confluence** (a level from 1-2 within tolerance of a
  level from 3-4) → candidate bands.
- **4b. Tightness → flag.** Measure each band's width in **ATR** (default unit). Narrow band (default
  `≤ 0.5·ATR`) + high 1-4 symmetry → flag `high-prob 5` zone (`band_low`, `band_high`).
- **4c. Break/return state machine.** One enum column `wolfe_state ∈ {INSIDE, AT_BAND, BROKE, NEXT_BAND,
  RETURN_TO_BROKEN, REVERSED}` capturing: price reaches band → breaks → rolls to next band → or reverses on
  return into the broken band. Mirrors the clean state-column design rs-band already uses.
- **4d. Honesty gate.** Flag `high-prob 5` **only** when symmetry is tight AND a band is genuinely narrow;
  suppress for sloppy structures. Deterministic strings, **no LLM**.

---

## 5. Decision utility — fusion, never standalone

A Wolfe setup never triggers alone; it is **setup × confirmation**, crossing the existing ₹0 signals:
- **DVPT / MEP** at point 5 — is accumulation showing up where the structure says it should reverse?
- **RS / RRG / rs-band** — is the name turning up on relative strength / sitting at band support as 5 forms?
- **F&O OI** — does positioning corroborate the reversal?

Output is a descriptive, deterministic line (e.g. *"BULL Wolfe, HIGH symmetry; 5-zone 1,180–1,192; DVPT
accumulating, RS at band support → confirmed setup"*). Sizing scales with `quality_tier` × confirmation
count. No verdict fires on geometry alone.

---

## 6. Honesty gates & failure modes (build these, or ship descriptive-only)

- **Discretionary → mechanical.** A human picks "the obvious" 1-4; the algo surfaces those *plus*
  marginal ones. The symmetry filter + scoring tame it; `log()` how many candidates were dropped.
- **Multiplicity / dedup.** Overlapping candidates across scales → dedupe, keep best; never flood the scan.
- **Repaint.** Covered by §3e point-4 lock — the most common way pattern lenses lie.
- **Scale sensitivity.** Different `k` finds different waves; the multi-scale grid + dedup is the answer,
  and the chosen `k` is stored per row so a setup is reproducible.
- **No proven edge → no verdict.** Phase 0 backtest must show the 1-4 + his-5 setup actually reverses on
  NSE daily better than chance, PIT, survivorship-aware. If it doesn't, ship the **descriptive** lens
  (here are the structures) with loud caveats and **no** buy/sell verdict — exactly the rs-band discipline.

---

## 7. Architecture — where it lives (all NEW modules; nothing touches in-flight files)

| Piece | Path | Pattern source |
|---|---|---|
| Compute lens | `src/automation/wolfe.py` | `compute_one(ohlc)→dict\|None`, `compute_and_store(conn)`, `main()` — like `rrg.py`/`rsband.py` |
| Table | `wolfe_signals` (owns its own `_SCHEMA`) | **`db.py` untouched**; `executescript` on first run; `_ensure_column` only if a later migration is needed |
| Web view | `src/web/wolfe_view.py` → `/dash/wolfe` | one-line `include_router` in `src/main.py` |
| Research | `research/wolfe_waves/` (read-only `hermes.db`) | mirrors `research/explosive_moves/` — prototype, backtest, freeze to prod |

Reads `bhavcopy_rows` (`trade_date, open, high, low, close, volume`) per symbol; weekly later via
`bars_weekly`. Universe from `nse_equity_list` filtered to the chosen scope. Nightly via
`python -m src.automation.wolfe` (CLI; scheduler/cron later).

**Multi-session caution:** `rsband.py`, `scoring.py`, `main.py` are being edited by a parallel lane. All
Wolfe code lands in **new** files; the only shared-file touch is the **one-line router mount in
`main.py`**, done last, CRLF-safe, diff-checked — or handed to whichever lane owns `main.py`.

---

## 8. Schema — `wolfe_signals`

```sql
CREATE TABLE IF NOT EXISTS wolfe_signals (
    symbol         TEXT NOT NULL,
    trade_date     TEXT NOT NULL,              -- as-of date (point-in-time)
    timeframe      TEXT NOT NULL DEFAULT 'D',  -- 'D' | 'W' | 'M'
    direction      TEXT,                       -- 'BULL' | 'BEAR' | NULL
    -- pivots 1-4
    p1_price REAL, p1_date TEXT,
    p2_price REAL, p2_date TEXT,
    p3_price REAL, p3_date TEXT,
    p4_price REAL, p4_date TEXT,
    p4_locked      INTEGER DEFAULT 0,          -- 1 once pivot 4 confirmed (repaint guard)
    -- leg vectors (handoff to Ramana's point-5 method)
    leg12_price REAL, leg12_bars INTEGER,
    leg34_price REAL, leg34_bars INTEGER,
    symmetry_price REAL,                       -- leg34/leg12 price-height ratio
    symmetry_time  REAL,                       -- leg34/leg12 bar-count ratio
    swing_scale    REAL,                       -- ATR-mult k that produced this candidate
    quality_tier   TEXT,                       -- 'HIGH' | 'MED' | 'LOW'
    quality_score  REAL,
    -- targets (from the 1->4 EPA line; available at 1-4 stage)
    target_price   REAL,
    target_eta_date TEXT,
    -- point-5 (Phase 2; nullable until built)
    band_low REAL, band_high REAL,
    band_tightness_atr REAL,
    band_ratios    TEXT,                       -- JSON: matched ratios that formed the band
    wolfe_state    TEXT,                       -- INSIDE|AT_BAND|BROKE|NEXT_BAND|RETURN_TO_BROKEN|REVERSED
    freshness_days INTEGER,                    -- bars since pivot 4
    computed_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date, timeframe)
);
CREATE INDEX IF NOT EXISTS idx_wolfe_active ON wolfe_signals(trade_date, direction, quality_tier);
```

---

## 9. Build phases (each gated on sign-off)

- **P0 — Doc + research sandbox + backtest.** This doc, plus `research/wolfe_waves/` (read-only). Prototype
  detection and run a **PIT, survivorship-aware backtest**: does 1-4 + his-5 reverse better than chance on
  NSE daily? *Gate: edge shown (or decision to ship descriptive-only).*
- **P1 — The 1-4 detector** (`src/automation/wolfe.py` + `wolfe_signals`). Swing extraction → validation →
  scoring → PIT invariant + point-4 lock. Emits pivots, leg vectors, target, quality. CLI `--selftest`.
- **P2 — Point-5 confluence** (automates §4). Fib engine + tightness + break/return state machine + honesty
  gate. *Separately gated — only after P1 validates.*
- **P3 — Surface.** `/dash/wolfe` universe scan (by quality/freshness/direction) + additive dossier row on
  the stock page. **Chart annotation spec confirmed with Ramana before any wave is drawn** (viz caveat).
- **P4 — Nightly + backfill.** `python -m src.automation.wolfe` with `--backfill`/`--selftest`/`--symbol`,
  one-row-per-symbol upsert; cron/scheduler.

---

## 10. Open params (defaults chosen — all overridable)

| Param | Default (taken) | Alternatives |
|---|---|---|
| **Scope** | Phase it: 1-4 now, point-5 (P2) after | 1-4 only & hand off · or both at once |
| **"Narrow" band unit** | **ATR** (×ATR14) | % of price · absolute points |
| **Fib ratios** | **Full** 1.272/1.414/1.618/2.0/2.618 | Core 1.272/1.618/2.0 · Deep 1.618/2.0/2.618 |
| **Universe / timeframe** | **Nifty 500, daily** | Full NSE EQ · +weekly · a watchlist |
| Swing scale `k` | ATR-mult `1.5`, multi-scale grid `{1.0,1.5,2.25}` | single fixed scale |
| Direction | both BULL & BEAR | one only |
| Symmetry tolerance | `0.6–1.6×` (price & time) | tighter/looser |

---

## 11. Doctrine honored

Isolate in new modules (multi-session safe) · pure-Python, **no LLM, ₹0** · point-in-time / no-look-ahead ·
pre-compute over recompute · **descriptive verdicts only** until backtest earns more · research-validate
then freeze to prod · `PROJECT_STATE.md` Decision log + Session log + a memory entry updated **when each
phase ships** (not before — this doc is the gated artifact).

---

## 12. References / related lenses

- Format & doctrine model: `docs/rs-band-support-resistance-design.md` (the level lens — same honesty-gate,
  PIT, fusion discipline).
- Lens module pattern: `src/automation/rrg.py`, `src/automation/rsband.py`.
- Research sandbox precedent: `research/explosive_moves/`.
- Memory: [[explosive-move-research]] (DVPT = confirmation not prediction — Wolfe is the same: structure
  proposes, the existing signals confirm).
