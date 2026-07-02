# Premium Visuals & Presentation — Brainstorm + Program

> **Status:** LIVING design doc. Created 2026-07-02.
> **Owner ask (Ramana, 2026-07-02):** analyze the complete system and find a large number of
> easy/quick wins that uplift the product to *premium* — in appearance, data, presentation,
> and infographics. Bar set explicitly: **no obvious/foolish charts.** Every visual must be
> backed by a dataset rich enough (time × cross-section × state-transition, or multi-factor
> confluence) that a table genuinely *hides* the insight a picture reveals. The north-star
> line: *a single chart should convey more than the entire dataset behind it* — and for each
> key datum, show an easily-understood chart of **movement** (or generated movement, like the
> relative rotation of sectors).
>
> **Ramana's vote (2026-07-02):** endorsed the program ("it's really good"). Approved flagship
> **#1 = the credibility "promise vs delivery" fingerprint (Tier 1 A)** → build started this
> session. Saved schematic images live in `docs/visuals/`.

---

## Guardrails that shape *what is honest to visualize*

These come from the strategy ledger + memory and change the menu:

- **Descriptive-only families:** CCI/credibility, Wolfe, harmonic, capture ratios — GATE B failed
  on leak-free inputs; §C falsified. None of these may become "predicts returns" charts. They are
  *characterizations*, never rankers or buy-signals.
- **Momentum's edge dies on cost** (Sharpe 1.29 gross → ~0.09 net). So the honest hero is
  *movement and structure*, never a fake alpha equity curve.
- **No static rupee thresholds** — use %/pctrank/velocity in every visual.
- **Nothing discarded** — failures are benchmarks; the gross-vs-net reality chart is a *feature*.

---

## Tier 0 — Site-wide premium levers (touch one file, re-skin everything)

Highest premium-per-effort: `ui_tokens.py` is the single source of truth and every chart
reseeds from `:root`.

1. **Wire the glossary that already exists.** `glossary.py` + `docs/metrics-glossary.md` (33 terms)
   drive **0 live popovers**. Every `RS#`, `DVPT`, `MEP`, `credibility`, `capture` header gets a `?`
   hover — explain-every-term *without leaking the formula*. Cheapest "institutional" lever.
   **[XS]** — *(already started: commit 72b5007 wired Screen+ headers; extend site-wide.)*
2. **Indian number grammar everywhere.** One formatter: ₹ lakh/crore grouping, signed ▲▼ deltas in
   `--up`/`--down`, tabular-nums. A consistent number *dialect* separates a terminal from a sheet. **[XS]**
3. **Freshness + provenance chip standard.** `as of · knowable_at · settled` chip on every signal
   surface (`effective_as_of` from Lane H). Never hiding when data is from = premium/trustworthy. **[S]**
4. **Token refinement for "premium dark."** Deeper `--bg-0`; one reserved `--accent-premium`
   (metallic/indigo) for synthesis surfaces (Conviction, Coverage) without breaking the semantic set. **[XS]**
5. **Export-as-PDF dossier.** Print-mode already flips to light palette + repeats headers +
   page-breaks. One button → a one-click client memo. **[S]**

## Tier 1 — Flagship "one picture > the whole table" movement visuals

Each is a dataset where a table hides the insight. Excludes anything that re-plots one column.

- **A. Credibility "promise vs delivery" fingerprint.** *(APPROVED — building)*
  Data: `concall_guidance` (each promise → `status` MET/MISSED/PARTIAL + `variance_pct` at
  `resolved_period`), headline from `concall_scores.credibility_trend / guidance_accuracy_score`.
  Table shows a tier letter; a letter can't show a *deteriorating streak of widening misses* —
  the whole signal. Visual: dumbbell/point per settled promise over time, colored by outcome, on a
  "promise kept" zero baseline. **Descriptive** — "management track record," never a buy signal.
  Image: `docs/visuals/credibility-fingerprint.svg`.
- **B. Rotation as a cycle-clock, not a 2×2 grid.** *(BUILT 2026-07-02 —
  `src/web/cycle_clock.py` → `/dash/cycle-clock`, Markets · Rotation lens.)*
  Data: `stock_rs.rs_phase` (RECOVERY→TAILWIND→ROLLING-OVER→HEADWIND) + velocity — a *lifecycle loop*.
  The grid hides *direction and speed of travel* around the loop. Visual: clock/loop, each name a dot
  at its phase-angle, arrow = velocity. Complements RRG (RS-ratio×momentum), doesn't duplicate it.
  Image: `docs/visuals/rotation-cycle-clock.svg`.
- **C. Up-capture / down-capture scatter ("all-weather" map).** *(BUILT 2026-07-02 —
  `src/web/capture_map.py` → `/dash/capture-map`, Markets · "All-weather map" lens.)*
  Data: `capture_signals.up_capture_63 / down_capture_63` — a real 2D cloud. Two columns hide the *diagonal*
  (the market line) and the prize quadrant (participates up, defends down). **Descriptive.**
- **D. DVPT institutional footprint — intensity × horizon × price.**
  Data: R-tier/P-tier ladder (10 baselines) + companion `avg_close_*` price zones (D31). Three
  dimensions. As a visual: today's bar vs the 10-rung ladder + price-zone bands on the price axis —
  *see* whether today breaches the institutional peak and *where* the accumulation shelf sits.
- **E. Capital-allocation waterfall over years.**
  Data: `capital_allocation` (buyback/dividend/capex, dated) — part-to-whole flow over time. Shows
  whether a company reinvests, returns, or hoards at a glance — a management-behaviour fingerprint.

## Tier 2 — Micro-infographics inside existing grids (only where the row carries a rich series)

6. **Confluence as a 5-segment gauge, not "3/5".** Screen+ `0/5` → a 5-dot strip lit per pillar
   (RS·Accum·Entry·Quality·Structure). Read pre-attentively; shows *which* pillars fired. **[S]**
7. **Per-row micro-RRG in the rotation table.** 14-point comet (`mini_rrg.py` already downsamples to
   14) as a 40px inline cell — each row shows its own trajectory. **[S]**
8. **Extend the RS-band lane idiom** (hollow→bar→filled + POC magnet) to any 0–100 positioned metric
   rather than inventing new forms. **[XS consistency]**

## Tier 3 — The honest hero (trust surfaces that read as premium)

9. **CCI robust-core funnel as a stepped waterfall** on `/dash/coverage`
   (`touched → scored → ≥1 → ≥3 → ≥10`). Transparency *rendered* = a B2B moat. **[S]**
10. **Gross-vs-net reality chart on `/dash/testing`** (momentum Sharpe 1.29 gross → ~0.09 net).
    Twin-bar per strategy — the most intellectually premium chart we can ship. **[S]**

## What we deliberately do NOT chart (the discipline list)

- Sector weights as a pie (one static vector — keep the heat strip).
- A single ratio/score as a one-bar chart (stat tile + delta instead).
- Price + a moving average as the "hero" (table stakes; already present).
- A radar/petal of the 5 confluence flags (5 binary axes = noise; use the segmented gauge, #6).
- Any credibility/harmonic/Wolfe "predicts return" curve (falsified — dishonest *and* foolish).

## Recommended build order

1. Glossary wiring (Tier 0 #1) — cheapest site-wide uplift; already started.
2. **Credibility promise-vs-delivery fingerprint (Tier 1 A)** — strongest "one picture beats the
   table" proof, on already-settled data. **← APPROVED, building this session.**
3. Rotation cycle-clock (Tier 1 B) — extends "relative rotation" to the RS lifecycle.

## Saved image assets

- `docs/visuals/credibility-fingerprint.svg` — flagship A schematic (illustrative data).
- `docs/visuals/rotation-cycle-clock.svg` — flagship B schematic (illustrative data).
