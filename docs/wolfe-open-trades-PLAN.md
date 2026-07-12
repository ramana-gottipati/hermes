# Wolfe "Open Trades — remaining ROI" filterable view — BUILD SPEC

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once this view ships and its summary is folded into
> `PROJECT_STATE.md` § Session log + the `wolfe-wave-strategy` memory. Converged with Ramana
> 2026‑07‑11/12 across a long session; he approved the direction and asked to wrap before it was built.

## Why
`/dash/wolfe/scan` (Markets → Patterns) is capped at **fresh ≤ 15 bars** — it only shows setups whose
point 5 printed in the last ~3 weeks (~64 rows), so Ramana "sees only a few calls." A prior sweep found
**~686 open winner‑profile trades beyond 15 days**. He wants to find the **best remaining‑ROI open trades**,
ranked, and **filter** them (not an endless list). This is a NEW additive view — do **not** change the
existing fresh `winner_scan` (the fresh scanner + `strategy_registry` depend on it).

## Population
Every **OPEN** winner‑profile trade = point 5 printed **AND** the EPA (1‑4) target **not yet reached**
(so run is still left), **any age**. Use `wolfe.epa_touched(wave, highs, lows, n)` → OPEN iff not touched.
Build a new `open_scan(conn, universe, **filters)` (mirror `winner_scan` but open‑state, not `age>fresh`)
and a new route `/dash/wolfe/trades` (or a `?view=open` mode on the scan page). Descriptive‑only.

## Metrics — measured from the CURRENT price (CMP)
- **run%** = remaining move to the EPA target. BULL: `(epa−cmp)/cmp*100`; BEAR: `(cmp−epa)/cmp*100`.
- **risk%** = distance to the stop. BULL: `(cmp−sl)/cmp*100`; BEAR: `(sl−cmp)/cmp*100`.
- **R:R** = run% / risk% (reward:risk if you enter NOW). Guard risk%≤0.
(The existing scanner's `up%` is upside from the ZONE, not from CMP — keep run% distinct.)

## Columns (the full, practical row — Ramana‑approved after he pushed on "what's missing")
`sym · dir · sector · size · liquidity/deliv · status(● IN / watch) · CMP · entry zone · SL · T1 · EPA ·
 run% · risk% · R:R · Q(/27) · RS · age (+ setup=p5 date) · ✓edge`
Row click → the wave on the chart (`/dash/wolfe?sym=…&pick=winner`), as today.
- **liquidity/deliv** — traded ₹ value + delivery% (from `stock_signals`). **The #1 add** — it's the
  systematized TIRUPATIFL lesson: illiquid / gap‑prone names (e.g. TIRUPATIFL's 98‑day Mar23→Jun29 dead
  zone) are untradeable; a liquidity column + a min‑liquidity filter keeps them out.
- **status / entry zone / T1** — were dropped in an earlier column proposal; they're mandatory (you can't
  take a trade without knowing if it's actionable now, where to enter, and the first target).
- **RS** — relative‑strength rank (`stock_signals`), cheap conviction (Wolfe on a leader > on a laggard).

## Filters at the TOP (9 — dropdowns/toggles; the script/persist must honor the SAME params)
1. **Size** ▾ ← `stock_index_membership` — All · Nifty 50 · Next 50 · Midcap 150 · Smallcap 250 (· Microcap 250 on `universe=inclusive`). Partitions Nifty 500 exactly.
2. **Sector** ▾ ← `company_tags` (multi‑label, `approved=1`) — All · Pharma · Chemicals · Power/Renewables · Banks · Defence · Metals · IT · Auto · FMCG · PSU · Realty · Infra · … (29 tags, 384 syms). Multi‑label: a stock appears under each tag it carries. (Alt single‑label: `stock_signals.primary_sector` — Ramana leaned to `company_tags`, "the tags we discussed"; confirm in 1 line if unsure.)
3. **Direction** ▾ — All · Bull · Bear.
4. **Max age** ▾ — All open · ≤15d (✓validated) · ≤30d · ≤60d · ≤120d.
5. **Min rank (Q)** ▾ — Any · Q≥15 · Q≥18 · Q≥21 · **Top 20 only** (his "best / rank‑one waves").
6. **Min room to EPA** ▾ — Any · ≥10% · ≥20% · ≥30% · ≥50% (his "most return left").
7. **Status** ▾ — Actionable now (in zone) · Watching · All.
8. **Min liquidity** ▾ — cut untradeable names (traded ₹ / delivery threshold).
9. **Min R:R** ▾ — Any · ≥1.5 · ≥2 · ≥3 (risk discipline).

## Sort
run% (most potential) · R:R (best risk‑adjusted) · Q (strongest) · age (freshest). Server‑side, honoring filters.

## Data sources
- `stock_signals` — CMP, RS ranks, `primary_sector`, DVPT, delivery%, traded value.
- `fundamentals.market_cap_cr` — cap (optional; index size buckets already cover this).
- `stock_index_membership` — size + index tags. `company_tags(symbol,tag,approved)` — sector/theme tags.
- Wolfe: `open_scan` per wave — dir, pivots, §B `score` dict {p1,B,C,F,G,H,I,D,total}, zone/sl/t1/epa, age, p5date.

## Persist (so the filtered view stays instant + the script honors filters)
Nightly snapshot (a new table, or extend `wolfe_signals` with a `mode`/`universe='nifty500:open'`) carrying
ALL fields **including each stock's size + sector tags + liquidity + RS**, so the same filter params drive
the view, the sort, AND any export — filtering is a server‑side WHERE, not front‑end only. Compute‑on‑read
fallback when no snapshot (like `winner_scan`). Wire into the existing `hermes-wolfe-scan` timer.

## Honesty / labelling (binding)
- **Q = structural strength; ✓edge = the tradeable filter** — they differ on purpose (§B Q *inverts* as a
  trade selector per the Phase‑1 backtest). The validated +2.4% edge is measured only on **fresh ≤15d**
  winner‑profile entries; older open trades have run left but **no validated entry‑edge** → **badge** them
  (fresh=✓edge, older="open, judge the run"), never hide. Descriptive — "not a buy/sell signal."

## Build safety (this session's hard‑won lessons)
- **Additive only** — new route/function; do NOT touch detection, §A geometry, §B scoring, `winner_scan`,
  the crossing rule, or point‑4 reconciliation.
- **`wolfe.py`/`wolfe_view.py` are CO‑EDITED across parallel sessions + the VPS copies are git‑UNTRACKED
  (raw scp overwrites, no git safety).** Deploy the *union* of main's current file + your change, always
  `cp *.bak-*` first, `curl -sL` (the D80 307 nesting) to verify. A parallel deploy CAN flip you — re‑pull
  and re‑verify after. See memory `vps-deploy-reality` + `wolfe-wave-strategy`.
- **Verify:** each dropdown actually filters; min‑liquidity excludes TIRUPATIFL‑type names; sorts reorder;
  persist path is instant; row‑click still draws the wave.
