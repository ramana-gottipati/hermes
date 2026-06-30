# Harmonic XABCD pattern lane (D72) — design, benchmark, scanner

> **Created 2026-06-28 (Lane G — Charting overhaul).** The new strategy lane the chart
> redesign §13 audit anticipated ("spin a dedicated design doc when greenlit"). Sibling to
> `docs/wolfe-wave-design.md` and `docs/cpr-strategy-design.md`. **DESCRIPTIVE-ONLY** —
> backtest-gated before any "trust" (Ramana: don't dress research as product; record every
> result as a benchmark — [[ramana-working-principles]]).

## 0. What this is
Auto-detected **harmonic XABCD patterns** (Gartley/Bat/Butterfly/Crab/Deep-Crab) on daily
bars, reusing the Wolfe engine's pivot machinery (ATR-zigzag + split-adjusted series). Two
states: **CONFIRMED** (five locked pivots X-A-B-C-D) and **FORMING** (X-A-B-C printed, D
projected into a **PRZ** — the "catch it forming, down the stream" ask, §0.1.12 of the
chart doc). Surfaced as a descriptive scanner, NOT a buy/sell signal.

## 1. Files (all NEW, Lane-G-owned — `harmonic_*`)
| File | Role |
|---|---|
| `src/automation/harmonic_patterns.py` | detector: ratio-template library + per-type validator + forming-PRZ projection + selftest |
| `src/automation/harmonic_backtest.py` | reliability gate — survivorship-inclusive forward-outcome backtest vs directional drift |
| `src/automation/harmonic_signals.py` | scanner + nightly-persisted `harmonic_signals` table (module-owned, db.py untouched) |
| `scripts/hermes-harmonic-scan.{service,timer}` | nightly persist (Mon-Fri 16:10 UTC, after bhav→signals + the Wolfe scan) |

Reuses (READ-ONLY) `wolfe.py`: `zigzag`, `atr`, `fractal_pivots`, `stock_series`, `rsi`, `scan_universe`, `Pivot`.

## 2. Ratio templates (v1 — the well-agreed five)
Legs: `AB=|B-A|/|A-X|` · `BC=|C-B|/|B-A|` · `CD=|D-C|/|C-B|` · **`AD=|D-A|/|A-X|`** (the
defining ratio — where D sits vs the XA leg). Direction read off D: D a swing **low** ⇒
**BULL** (reverses up), D a swing **high** ⇒ **BEAR**. Acceptance bands (with an `ideal`
for the fit score):

| Pattern | AB | BC | CD | **AD** (defining) |
|---|---|---|---|---|
| Gartley | 0.55–0.66 | 0.382–0.886 | 1.13–1.618 | **0.786** |
| Bat | 0.382–0.50 | 0.382–0.886 | 1.50–2.618 | **0.886** |
| Butterfly | 0.74–0.83 | 0.382–0.886 | 1.50–2.24 | **1.272–1.618** |
| Crab | 0.382–0.618 | 0.382–0.886 | 2.0–3.80 | **1.618** |
| Deep Crab | 0.85–0.92 | 0.382–0.886 | 2.0–3.80 | **1.618** |

The ratios are mutually constrained (CD is a geometric consequence of AB/BC/AD) — a match
requires ALL four bands simultaneously, which is what enforces a real pattern. **Score** =
mean closeness of AB/CD/AD to their ideals (0–1). **Deferred:** Cypher / Shark / Three-Drives
(use different leg references — XC, 0-X-A-B-C, three symmetric drives — whose published
ratios vary by source; omitted rather than encode a dubious template that would poison the
backtest). Elliott deferred entirely (subjective auto-counting — chart doc §13).

## 3. Reliability benchmark (the gate — RUN 2026-06-28, VPS, recorded)
`harmonic_backtest.py --universe inclusive` — 300 survivorship-inclusive symbols, **1,052
CONFIRMED patterns**, entry = 5 bars after D (non-repaint), SIGNED by reversal direction,
vs the same-horizon **directional drift** baseline.

| | 10b | 20b | 40b | 60b |
|---|---|---|---|---|
| **ALL BULL** (n=516) | +0.9% / 57% | +1.9% / 58% | +3.5% / 59% | **+4.5% / 59%** |
| BULL baseline (long drift) | +0.4% | +0.9% | +2.0% | +2.7% |
| **ALL BEAR** (n=536) | −0.4% | −0.5% | −2.2% | −2.8% |
| BEAR baseline (short drift) | −0.4% | −0.9% | −2.0% | −2.7% |
| **score hi ≥0.6** (n=369) | +0.5% / 54% | +1.8% / 59% | +1.2% | +1.4% |
| **score lo <0.6** (n=679) | +0.1% / 50% | −0.0% | −0.3% | +0.4% |

**Verdict:** a **modest, real, BULL-side selection edge** — bull harmonics beat long-drift
at every horizon (**Gartley-bull strongest**: n=197, +2.0/+2.1/+4.1/**+6.3%**, hit 60–63%;
Butterfly-bull and Deep-Crab-bull also consistently positive). The **ratio-fit score
stratifies** (hi ≥0.6 > lo <0.6 everywhere), so the score is meaningful — same shape as
Wolfe's Q stratification. **BEAR harmonics ≈ short-drift** (no edge beyond drift; Crab-bear
notably bad) — the same bear-weakness Wolfe found in a 20-yr bull tape. **Caveat:** the
zigzag-D confirmation timing carries the same look-ahead caveat as the Wolfe/ignition
backtests (a 5-bar lag mitigates it); medians are a few % so this is **DESCRIPTIVE**, not a
mechanical trigger. Read **by side: BULL = modest fit-graded edge, BEAR = ⚠ tail/regime.**

## 4. Scanner (LIVE)
`harmonic_signals.py` persists FRESH setups (CONFIRMED within 12 bars + FORMING with a PRZ)
into the module-owned `harmonic_signals` table; nightly via the timer. Real-VPS (nifty500,
2026-06-25): **143 setups** (76 forming-bull · 59 forming-bear · 8 confirmed; **12 in-zone
now**, e.g. CANHLIFE Gartley-bull). `latest(conn, universe)` reads the snapshot. Rows carry
`tag` (edge/tail by side), `score`, `d_price`/`prz_lo`/`prz_hi`, `in_zone`, `rsi_d`, `age`.

## 5b. UI — SURFACED + LIVE (Lane G2, 2026-06-29)
- **`src/web/harmonic_view.py`** (NEW, owned) — `/dash/harmonic` scanner page (reads the
  nightly `harmonic_signals` snapshot, live fallback; read-by-side BULL ✓ edge / BEAR ⚠
  tail; rows click → the stock chart) + `/dash/harmonic/overlay` JSON feed (per-symbol
  confirmed + forming patterns). **Mounted with NO main.py edit** — its router is nested
  into the already-included `wolfe_view` router (`router.include_router(...)`), so it's
  committed + survives a redeploy (cleaner than the in-place hooks the older overlays use).
- **`stock_chart.py`** (owned) — a **Harmonic chip** in the Strategies family + `harmToggle`:
  fetches the overlay and draws each pattern's X-A-B-C-D polyline + point markers (+ the
  forming **PRZ** band) on `window.__wfpc`, autoscale-opt-out (candles never squish), point
  dates re-snapped onto the current bars so it survives the D/W/M/Q resample. `__wfpc`
  contract untouched → CPR/MEP/MA/RS/Wolfe keep working.
- **Browser-verified LIVE (Chrome):** MARICO confirmed Gartley-bear draws X-A-B-C-D on the
  candles; CANHLIFE forming Gartley + PRZ; chip toggles on (pink #f778ba); CPR/MEP/Wolfe/RS
  all coexist; ZERO console errors. Scanner 200 (143 setups / 12 in-zone). Cross-linked from
  the Wolfe scanner (no orphan). Commit `1eeae16`.

## 5. Open / next (gated; NOT built)
- **Nav entry** — add "Harmonic" to the Strategies sub-nav (next to "Wolfe · Scan"). Lives in
  `v2_surfaces.py` (Lane A) → **hand-off**; reachable now via URL + the Wolfe-scanner cross-link.
- **Multi-TF harmonic DETECTION** (W/M) — the chart already resamples D/W/M/Q and the overlay
  snaps to it, but detection itself is daily-only; true W/M needs `bars_weekly`/`bars_monthly`
  fed to `detect_from_series` + the scanner. (The validated backtest is daily — extend + re-gate.)
- **Drawing persistence → SQLite** — the drawing engine's magnet + hide-all + persistence are
  live, but persistence is `localStorage` (per-browser). A per-user×symbol SQLite table +
  save/load endpoints would make drawings cross-device.
- **The moat (chart doc §13):** fuse the harmonic D-zone with proprietary **DVPT-accumulation
  + RS + CPR-confluence** — a pattern completing where institutions are accumulating is the
  "stronger, more reliable" signal nobody else can compute (a confluence column on the scanner).
- **Bull-focus** (the edge is bull-side): a bull-only screen + tighter score gate.
- **Renko / Point & Figure** chart types (off-axis → custom-series/v5) + **site-wide bounded
  engine rollout** (RRG / ratio / sparklines onto `hermes-charts.js`, kill `preserveAspectRatio="none"`)
  — both touch non-owned files (`cockpit.py`/`rrg_view.py`) → hand-off.
- **Cypher / Shark** once specs are pinned · **Three-Drives** · **strategy_registry** reading
  `harmonic_signals` for a `/dash/strategist` card (Lane-C file → hand-off).
