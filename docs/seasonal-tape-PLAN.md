# Seasonal Tape — Build Plan (converged with Ramana, 2026-07-12)

> **Lifecycle: TRANSIENT** — retire when the lens ships: fold the decisions into
> `PROJECT_STATE.md` § Decision log + a `docs/strategies/` page, then `git rm` this file.
> Source: full design conversation 2026-07-12 + 19-agent workflow `wf_7205bfcb-0e1`
> (journal: `~/.claude/projects/D--Hermes/288e50dc-.../subagents/workflows/wf_7205bfcb-0e1/journal.jsonl`).

## 0. What it is (one line)

A **descriptive-only** seasonal lens: 25-year calendar tapes (month / ISO-week / weekday) for
every index, sector and Nifty500 stock, built on the **point-in-time idiosyncratic residual**,
with corporate-event cadence marks, a relative-strength ladder, a confluence "safe area" ribbon,
and a forward outlook strip that always shows its confidence interval. **Never a signal.**

## 1. The governing rule (from the multi-agent analysis — verbatim spirit)

Everything reduces to ONE number:

```
z_pit(entity, cell, t) = (r − mean_prior_years[r,cell]) / σ_prior_years[r,cell]
r = R − (α + β·market + γ·(sector ⟂ market))        ← idiosyncratic residual
```

- ALL inputs (β, γ, sector membership, cell mean, MAD σ) fit on **strictly-prior expanding
  windows** — the scored observation and future years never enter their own denominator.
- SCRIPT = cross-year mean of z per cell. BREAK = today's z vs that script. Two moments,
  one detector. Month/week/day = three re-bins. Index strips nothing; sector strips market;
  stock strips market+sector.

### Certification gates (a cell is COLORED only if ALL pass; else greyed "reported-not-gated")
1. **Frozen family**: full (entity × axis × cell) grid pre-registered + sha256-hashed via
   `prereg_registry` BEFORE any z is computed. Never scope-shrink after looking.
2. **Non-inert null**: circular-block/phase-randomized bootstrap on the residual series
   re-binned to cells + cross-sectional (permute-which-stock) shuffle, seed 42, n≥200.
   ⚠ Year-label shuffle is **BANNED** — the mean of a fixed z-set is permutation-invariant
   (zero-width null; the swarm's key catch).
3. **Family-wide FDR** (BH-Yekutieli or Westfall-Young max-stat) across the whole frozen grid
   + **global excess-count** gate: real certified count must beat 99th pctile of shuffled-date
   count null, per axis, or the axis ships nothing.
4. **N ≥ 15–20 independent years**; below → quarantined grey.
5. **Same sign out-of-sample** (fit 1..k → confirm k+1..N) and across epochs
   (pre-2010 / 2010-20 / post-2020). Sign flip = kill.
6. **Mechanism registry**: cell admissible only with a named India mechanism + pledged sign,
   registered before compute (FY-end advance-tax/window-dressing, Budget, monsoon→agri/FMCG/
   auto, festival→auto/jewellery, results cadence…). Pure flow/timing anchors (expiry,
   turn-of-month SIP, rebalance, F&O ban) license **variance-only** breaks, never signed.
7. **Earnings-cadence mask**: per-name drifting real filing/dividend/AGM dates; a script that
   collapses ex-earnings is re-badged PEAD → decertified (PEAD wrappers already NET-FAILED
   0.10 vs 0.85 — failure ledger, blocking).
8. **Mechanical-window flags** auto-label breaks as MECHANICAL (excluded from news queue):
   expiry T-3..T0, weekly expiry, ex-div/record date, rebalance effective day, F&O ban
   (MWPL>95%), FY-end last-5 sessions, thin-liquidity (value < 1e7 / turnover pctile).
9. **Residual diagnostics**: residual's own trading-day-of-month profile must be FLAT (SIP
   pulse absorbed) and residual ⟂ index-residual within cell — else the strip is
   under-specified and NO stock-level script may be trusted.
10. **Machine descriptive-only fence**: no forward-return column, no cross-entity ranking of
    scripts/breaks, no backtest-as-entry. Breaks route to the news layer as QUESTIONS.
11. Survivorship: PIT membership, delisted retained where reconstructable; where structurally
    blocked (known repo limitation) → cell capped "survivor-conditional, reported-not-gated".

## 2. The page (one shared calendar axis; toggle **Apr–Mar (default)** | Jan–Dec)

Lanes, top to bottom:
1. **EVENT LANE** (25y cadence + this year): ▲ results (quarterly/annual), ● concalls,
   ▽ dividend ex-date, ✂ split, ⊕ bonus. Solid = happened this year; hollow = **projected
   window** ("Q3 results ~24 Jan ±9d, 23/25y") — windows, never point dates. Splits/bonus
   double as "corp-action-adjust here" flags (Guardrail #5).
2. **25-YR STACK** (stock): one row per year, cell color = **RS-residual (default)** with a
   **Raw** toggle. The stack shows dispersion — whether "weak Sept" is a tendency or 2–3
   ugly years.
3. **STOCK CONSENSUS RIBBON** (the clubbed gradient): **hue = direction, saturation =
   confidence** ("not too radiant" — uncertainty reads as paleness). Grey where gates fail.
4. **CURRENT-YEAR RIBBON**: solid actuals → today; faded base-rate projection for the
   remainder. Alignment check vs anticipation windows ("did reality land where history said").
5. **INDEX CONSENSUS TAPES**: major (Nifty 50/500) + minor (sector, size segment) aligned
   under the stock.
6. **CONFLUENCE "SAFE AREA" RIBBON**: colored ONLY where index-seasonal AND stock-residual
   are both certified same-direction. Double-confirmed zones; descriptive labels only.
7. **FORWARD OUTLOOK STRIP** ("you are here"): next 2w/4w/8w — hit-rate k/N + **Wilson CI** +
   **edge over baseline** (own all-window rate & market rate) + fail-case (avg/worst loss in
   down years) + traffic light 🟢🟡⚪ (⚪ = CI touches baseline/50% → explicitly "noise") +
   named mechanism. **Two confidence tiers kept visually separate**: event-window projection
   (high-conf scheduling) vs price base-rate (low-conf) — cadence must not lend authority to
   the price call. Include "worst stretch is X% behind you" cycle-position read.
8. **RS LADDER card** (Ramana's 17-of-25): three rungs — stock>sector k/25, sector>Nifty k/25,
   stock>Nifty k/25 — each with Wilson CI + offense/defense split (up-years vs down-years).
   **β-adjusted residual default, Raw toggle** (raw "beats" rewards beta). Reading: high rung-1
   + low rung-2 = idiosyncratic strength; reverse = sector passenger.
9. **DRILL-DOWN** per year-band: index contributors that year + this stock's rank percentile
   across all 25 instances of the window ("driver or passenger; were there better names").
   Reuse the RRG constituent drill pattern (`/dash/rrg?idx=`).

Glossary popovers via the existing `_PAGES` system for every new term (z, CI, residual,
confluence, reported-not-gated).

## 3. Data & compute (all primary-source, all reuse — Guardrail #8 clean)

### Verified data reality (checked 2026-07-12, VPS `hermes.db` + `research.db`)
- **Price tape: 22 years, not 25** — `bhavcopy_rows` 9.38M rows, **2004-07-23 → 2026-07-10**.
  Month/week cells get ~21 independent draws → right AT the N≥15–20 gate; fine, but all copy
  says "22-year tape", and the epoch split becomes **2004-12 / 2013-19 / 2020+** (pre-2010
  alone is only ~6 draws — too thin as its own epoch).
- **Event lanes are shallower than price and each discloses its own N**: `corporate_actions`
  26,868 rows; `concalls` 39,901 rows (recent-era); `fundamentals_history` 770k rows
  **2002→2026 (24y PIT)** so results-date triangles can run deep via filing dates.
  Cadence projections read "±Xd over the last N years available", never "23/25".
- **Laptop DB is a stub** (800 bhav rows, empty event tables, empty research.db) — all P0/P1
  compute runs **against VPS data** (or after a full `download-from-vps` pull). Local dev on
  the stub validates nothing. Heavy one-time certification: run on VPS off-hours,
  writer-safe, never a mid-day timer start (AUD-95).

- **New**: `src/automation/seasonal_tape.py` (residuals, cells, certification, outlook,
  breaks) + `src/web/seasonal_view.py` (page) + lens entry in `lens_registry.py`
  (D80: `/dash/<workspace>/<page>` — Markets workspace; NO orphan URLs).
- **Reuse**: bhav archive (25y), `indexes.py` + size/sector indices, `stock_rs.py` RS columns,
  `corp_actions.py` (div/split/bonus), `results_calendar.py` + `fundamentals_filing_dates.py`
  (▲, PIT knowable_at), `concall_bse.py`/`concall_clock.py` (●), evlib placebo harness +
  `prereg_registry` (research/explosive_moves), `infographics.py` SVG ribbon kit,
  news-intelligence layer (break → why), `provenance.py` knowable_at discipline.
- **Storage** (space-optimization-mandatory: bounded nightly snapshots, compute-on-read for
  drills): `seasonal_cells` (entity, axis, cell, mean_z, n_years, gate_flags, conf),
  `seasonal_outlook` (entity, asof, horizon, k, n, ci_lo, ci_hi, edge, fail_avg, fail_worst,
  light, mechanism), `seasonal_breaks` (entity, date, z, mech_flag, news_refs). No giant
  derivable series persisted.
- Nightly job appended to existing timer chain (writer-safe; NEVER mid-day `systemctl start` —
  AUD-95; deploy = scp + writer-safe restart — vps-deploy-reality).

## 4. Phasing (each phase ends: gates green → walk-the-journey on live surface →
PROJECT_STATE + strategy-docs page updated in the SAME commit → deploy per recipe)

- **P0 — Pre-registration freeze** (small, critical): freeze family + mechanism/sign registry,
  hash via prereg_registry. No return data examined first.
- **P1 — Engine + indices/sectors**: residual/cell/certification pipeline; index & sector
  tapes + consensus ribbons + outlook strip live. (Where the honest signal lives: FY-end
  March concentrate, Budget run-up, monsoon/festival cohorts.)
- **P2 — Stock layer**: 25-yr stack, event lanes (all 5 marks), current-year ribbon,
  per-stock consensus (greyed wherever gates fail — expected for most names).
- **P3 — RS ladder + drill-down + confluence ribbon.**
- **P4 — Break→news wiring + surfacing** (stock page card, optional Pat/Telegram read-only).

## 5. Honest priors (set expectations; failure ledger discipline)

- Index/sector scripts with dateable causes WILL certify; MOST single-name cells will grey out
  (indistinguishable from placebo count) — that winnowing IS the product.
- Many "results-month" scripts will decertify ex-earnings (they were PEAD in a costume).
- NOTHING here is tradeable net of STT/impact — expect hedged-harvest expectancy ≈ 0; the
  page must say so. Any candidate that looks fundable goes through failure-ledger cites first.

## 6. Defaults chosen (flip any, cheaply, before P1)

1. Stack/ladder coloring: **residual default, Raw toggle** (Ramana leaning yes; unconfirmed).
2. Primary benchmark: **sector (minor) first, Nifty broad second** (unconfirmed).
3. Axis default: **Apr–Mar fiscal**, Jan–Dec toggle.

## 7. Session-log note

2026-07-12: Design converged over full conversation (ribbons → residual framing → forward
outlook + CI → event triangles → 25y stack → RS ladder + drill + confluence). Multi-agent
workflow wf_7205bfcb-0e1 (18/19 agents) produced the governing rule + inert-null catch.
Plan persisted here; NO code built yet, NOTHING committed to main (parallel-session
modifications present in tree — re-verify vs main at build start, kickstart-pick-verify).
