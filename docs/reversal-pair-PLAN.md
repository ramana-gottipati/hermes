# Reversal Pair — FRACTAL FLOOR + STREAM BAND (design; B TESTED 2026-07-13)

> **STATUS 2026-07-13:** Ramana said GO. **STREAM BAND backtested first (his priority) →
> pre-registered gate FAIL-null** — the BUY-cross *negatively* selects (22d med excess −1.25%,
> both placebos beat it; book Sharpe 0.37 vs 0.89 hurdle; best cell TREND 0.58 = PULLBACK-class).
> Full record: `docs/strategy-ledger.md` § "Study 2026-07-13 — STREAM BAND". Consequence: §2's
> cross NEVER ships as an entry/alert; only the descriptive state + stretch-percentile columns
> remain candidates. FRACTAL FLOOR (§1) untested — its study must cite the ledger entry first.

> **Lifecycle: TRANSIENT** — this is the pre-build design doc for the two reversal strategies
> Ramana specified on 2026-07-13 (voice-note session). **Retire condition:** when built, fold the
> final spec into `docs/strategies/fractal-floor.md` + `docs/strategies/stream-band.md` (same
> commit as the code, per the strategy-docs coverage test) and `git rm` this file.

## 0. Ledger check (failure-ledger contract — cited BEFORE build)

These are *reversal-family* ideas. The ledger's closest relatives, exact numbers:

| Prior attempt | Recorded result | Consequence for this design |
|---|---|---|
| PULLBACK (buy-dip-in-uptrend, top-25 monthly) | Sharpe 0.56–0.72 · MaxDD −44% · lost to Nifty-500 0.89 | A *ranked book* of dip-buys is BLOCKED unless it beats these numbers net. |
| S3 Shakeout reversion (swing) | CAGR **−0.5%** — FAILED | Mechanical reversion *trading* failed outright. |
| ACCEL (1-mo thrust chasing) | Sharpe 0.42–0.64 · MaxDD −62…−70% | Short-thrust entries are catastrophic as a book. |
| Wolfe raw pattern as a book | median **−2.1% net**, placebo-NEGATIVE (craft subtracts value) | Pattern *trade-craft* fails; pattern *selection* can survive. |
| Wolfe winner-profile BULL (selection) | medNet **+4.4%**, residual α **+5.07** CI [+2.0,+7.3] | The ONE reversal-family thing that survived OOS = a *selection lens*. |
| Momentum as fundable | gross 1.29 → **net ~0.09** | Any "fundable" claim needs the participation-cost recut. |

**Verdict of the check: ledger CLEAN for these two ideas as SCREENERS / selection lenses**
(no prior fractal-proximity or HiLo-band attempt exists). Any *tradeable-book* claim is
pre-blocked until it beats the numbers above under the no-leak harness. Build order therefore:
descriptive screener first → pre-registered selection study second → book question only if
the study survives.

---

## 1. Strategy A — FRACTAL FLOOR (Williams-fractal reversal radar)

### Definitions (PIT-honest)
- **Down-fractal of degree N**: bar whose LOW is strictly below the lows of the N bars before
  AND N bars after. Mirror for **up-fractal** (highs). Degrees **N ∈ {2, 5, 10}**;
  timeframes **D / W / M** (weekly+monthly resampled from the daily bhav archive).
- **Confirmation lag (binding):** a degree-N fractal is only *knowable* N bars after its bar.
  Screeners use **confirmed fractals only**; every stored row stamps `knowable_at`
  (= fractal_date + N bars on that timeframe). No look-ahead, ever.
- **Strength tier** = (timeframe, N): M10 > W10 > D10 > M5 … > D2. A 10-fractal that still
  holds ⇒ ≥20-bar consolidation by construction (Ramana's point) — display a range-compression
  percentile (20-bar high-low range vs own history) alongside.
- Primitive already exists: `fractal_pivots(high, low, periods=(…))` in `src/automation/wolfe.py:146`
  (validated under D108). Reuse verbatim; do NOT fork.

### State machine (long side; bear side is the exact mirror on up-fractals)

```
confirmed down-fractal (N, TF)
        │  CMP within the proximity band ABOVE the fractal low
        ▼  (chips: ≤5% tight / ≤10% default / ≤15% wide)
      WATCH ──── ≥1 confirmed 2° up-fractal formed since the low ────► ARMED
        │                                                               │ close > T1
        │ close < fractal low  ⇒  INVALIDATED                           ▼
        └──────────────────────────◄────────────────────────────── TRIGGERED
                                                    (close > T2 ⇒ STRONG-TRIGGER)
T1 = nearest confirmed 2° up-fractal high since the low
T2 = higher of the LAST TWO confirmed 2° up-fractal highs ("beats the first two up-frac")
```

- All thresholds in **%**, never rupees (standing rule). Both T1/T2 shown as columns so the
  analyst sees the trigger *levels*, not just the state.
- Support break (close below the fractal low) flips the row to INVALIDATED (and becomes a
  candidate on the bear mirror).

### Screener columns (v1)
symbol · TF · N · fractal date · fractal low · CMP · **gap-to-floor %** · days-held ·
range-compression pct · state (WATCH/ARMED/TRIGGERED/INVALIDATED) · T1 / T2 ·
vol-context (ATR% percentile vs own 3y) · RS band (join, display-only).

---

## 2. Strategy B — STREAM BAND (13-EMA HiLo band + 5-EMA trigger) + STRETCH

### Construction
- **Upper bank** = EMA13(high) · **Lower bank** = EMA13(low) · **Trigger stream** = EMA5(**HLC/3**).
- **Decision — HLC/3 ships first** (typical price; the open adds gap noise on NSE and HLC3 is
  the standard construct). OHLC/4 is a **pre-registered A/B variant** in the study — the data
  decides "whichever is stronger", not opinion. (Known family: Gann HiLo / high-low channel —
  sane prior art, our % + percentile treatment is the differentiator.)

```
      EMA13(high) ────────────── upper bank
   ~~ EMA5(HLC3)  ~~~~~~~~~~~~~  the trigger stream
      EMA13(low)  ────────────── lower bank

  BUY  cross : EMA5 closes ABOVE EMA13(low)  having been below   (reversal up)
  SELL cross : EMA5 closes BELOW EMA13(high) having been above   (reversal down)
  Position states: BELOW · CROSS-UP · INSIDE · CROSS-DOWN · ABOVE
```

### STRETCH (the standard-deviation idea, done per Ramana's own standing rule)
- `stretch_up% = (EMA5 − EMA13high) / EMA13high × 100` when above the band;
  `stretch_dn%` mirrored vs the lower bank when below. **Percent, never absolute** (his ₹100→₹1000 point).
- **Normalization = percentile vs the stock's OWN trailing 3y of daily stretch values.**
  This resolves the cap-size problem exactly: small/micro caps DO deviate more, so no global
  threshold can work — each stock is ranked against itself. A small-cap at 8% may be p60;
  a large-cap at 4% may be p97 (the more actionable read).
- **Early-warning flags:** `stretch ≥ p90 above band` = over-extension (reversal-down risk,
  before any cross prints); `≥ p90 below band` = capitulation stretch (Ramana's reversal
  hunting ground). No waiting for the cross — the percentile IS the anticipation read.
- Confluence columns (display-only, never a gate in v1): RSI(14) divergence — price lower-low
  vs RSI higher-low anchored on the two most recent 2° down-fractals (shares the fractal spine);
  Wolfe winner-profile overlap (join `wolfe_signals`); both boost a shown "confluence count".

---

## 3. Product placement (aligned with the parallel UI lanes)

- **One lens page, two full views** (S121 lesson — match the mental model, toggle not two tabs):
  `Reversals` lens → **Fractal Floor ⇄ Stream Band** toggle, each deep-linkable
  (`?view=`), shared filter chips (TF D/W/M · degree 2/5/10 · proximity ≤5/10/15% · state ·
  stretch ≥p90 · min-liquidity). Registered through `lens_registry.py` (single nav source,
  `/dash/<workspace>/<page>` convention, NO orphan URLs).
- **`strategy_registry.py`**: +2 rows (reads precomputed tables only, per its binding contract).
- **New modules:** `src/automation/fractal_floor.py` + `src/automation/streamband.py`
  (+ shared spine helpers), NEW files only — no edits to hot co-owned files beyond the
  registry/lens insertions (anchored-insert pattern from S121).
- **Tables (bounded, space rule):** `fractal_floor_signals`, `streamband_signals` — ONE latest
  row per symbol×TF(×N); history recomputed on read for charts. Nightly compute piggybacks on
  the existing signals timer (**no new systemd unit**, deploy = scp + writer-safe restart).
- **Docs/glossary in the SAME commit:** `docs/strategies/` pages + glossary keys +
  `bottom_line`/`plain` readability scaffold (coverage tests enforce).
- **Phase 3 (after screeners live):** 13/13/5 ribbon + fractal markers as a `/dash/stock`
  chart overlay via the bounded `stock_chart.SNIPPET` primitive.
- **Cost: zero LLM.** Pure Python over the bhav archive; ₹0 API impact.

## 4. Validation (the honesty spine — set expectations BEFORE the study)

- **Phase A (build):** both ship **DESCRIPTIVE-ONLY**, joining the 17 gated strategies. No
  return claim on any surface.
- **Phase B (separate session):** pre-registered event study on the existing prereg harness
  (`research/explosive_moves/prereg.py`) with the D94 fences (dedup / matched controls by
  size-sector-vol / placebo dates). Primary hypotheses filed up front:
  H1 = confirmed D10 floor + proximity ≤10% + T1 trigger → forward excess vs matched controls;
  H2 = STREAM BAND buy-cross (± stretch≥p90-below precondition) → same;
  variants: HLC3 vs OHLC4 · degree ladder · TF ladder. Kill criteria written before running.
- **Honest prior from the ledger:** the *book* forms of reversal have failed twice
  (PULLBACK 0.56–0.72 · S3 −0.5%); what has survived OOS in this family is a *selection*
  edge (Wolfe BULL +4.4% medNet, α +5.07). The study is framed to detect a selection edge;
  FAIL-null is a publishable outcome, not a wasted session.
- Anything that survives Phase B faces the participation-cost recut (C-BLEND lesson:
  flat-cost 1.32 → 0.52 @₹25cr) before ANY fundable language.

## 5. Build phases

| Phase | Scope | Size |
|---|---|---|
| 1 | Compute modules + tables + tests (daily TF, all degrees; W/M resample) | one session |
| 2 | Lens page + registry rows + docs/glossary + deploy + walk-the-journey | same session |
| 3 | /dash/stock ribbon + fractal-marker overlay | small follow-on |
| 4 | Pre-registered study (fresh prereg doc, tamper-clean) | separate session |
| 5 | Confluence tiers (Wolfe/RSI-div weighting) — ONLY if Phase 4 survives | conditional |

## 6. Decisions made (CEO-mode; flag only if you disagree)
1. Trigger price basis **HLC/3** first; OHLC/4 decided by the pre-registered A/B.
2. Trigger ladder **T1/T2** as specced above (nearest up-frac / higher-of-last-two).
3. Proximity default **≤10%** with 5/10/15 chips (your "5–15%" range as a filter, not a constant).
4. Stretch normalization **percentile-vs-own-3y-history** (replaces any cap-size table).
5. One lens, two views, working names **FRACTAL FLOOR** and **STREAM BAND** (rename freely).
6. Descriptive-first; no return language anywhere until Phase 4 verdicts land.
