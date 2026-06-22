# RS Rotation — the complete four-phase weather rotation (stocks + sectors) + 18m/24m depth

> **Status:** STAGES 1–3 CORE SHIPPED + LIVE (session 25, 2026-06-22; commit `219af7c`, pushed).
> `/dash/rotation` live on the VPS: 2×2 grid + just-turned movers + breadth banner + RS
> term-structure table. Data computed live (indexes 113/101 with 18m/24m; 2418/2419 stocks
> phased). Verified sensible — Recovery=realty turn (PRESTIGE/LODHA/DLF), Tailwind=defence
> (== the existing strong-in-strong set), Rolling-over=metals cracking; all `/dash/*` return 200
> (zero regression). `db.py` NOT edited (parallel-held) — columns owned at runtime via
> `rs_phase.ensure_columns`. Fixes en route: `_fetch_index_history` 380→800d (anchor 18/24m);
> precompute table cells (no nested same-quote f-strings — VPS Python 3.11).
>
> **Remaining (additive, next increment):** Home rotation strip · stock-page badge · Telegram
> `/rotation` `/recovery` `/rollingover` · size-index compare-chart embed · full historical
> backfill so movers/freshness light up (accrues nightly anyway). PROJECT_STATE.md update still
> deferred (parallel-session-dirty; fold in when that file is free).
>
> **Supersedes** the narrower `rs-recovery-design.md` (Recovery was only ONE quadrant of
> this). Recovery is built here as part of the whole square.
>
> **Decisions locked (this session):**
> - **Scope = the full 2×2 RS rotation**, not just Recovery. Build the TWO missing quadrants
>   (Recovery + Rolling-over) to complete the square; Tailwind/Headwind already exist as
>   leaders/laggards.
> - **Naming = weather (project-native).** Reuse the EXISTING `_WEATHER` vocabulary
>   (`cockpit.py:147`): 🌤 Tailwind · 🌅 Recovery · ⛅ Rolling-over · 🌧 Headwind · ☁ Neutral.
> - **UI = 2×2 grid + data table.** Spatial quadrant grid as the at-a-glance overview;
>   one wide sortable table with the phase chip + full term structure underneath.
> - **Recovery test (the strict shortlist) = "confirmed turn from a deep base."**
> - **Add both 18m and 24m RS windows** (grade base depth / run height).
> - **Fold in 7 RS-leverage reads** (Ramana, this session — "loved all of them"): (1) RS-leads-
>   price, (2) RSI-of-RS timing tier — un-stranding the computed-but-unused RSI-of-RS +
>   extending it to stocks, (3) RS acceleration / stacked term structure, (4) freshness /
>   time-in-phase, (5) delivery (DVPT) confirmation of RS turns, (6) dual-momentum gate
>   (relative + absolute), (7) leadership-breadth macro read. See §4b. RS-based **position
>   sizing** stays the documented throughline (§11), not in this build.
> - **Sequence = design doc first, then build.**
>
> **Doc-persistence rule ([[preserve-strategy-intent]]):** keep this rich; do NOT one-line it.

---

## 1. The reframe (why this doc replaced "Recovery only")

The first cut proposed a single Recovery screen. Ramana correctly pushed back: Recovery is
just one corner of a complete rotation. Every name is somewhere in a **2×2 defined by its RS
term structure** (long windows vs short windows) and where RS sits vs its 50/200-day MA:

| Phase (RRG term) | Weather name (existing) | Long 12m/18m/24m | Short 1m/3m | MA position | What it is | Action | Status |
|---|---|:---:|:---:|---|---|---|---|
| **Leading** | 🌤 **Tailwind** | ➕ | ➕ | >200 & >50 | strong, still strengthening — *strong-in-strong* | hold / ride | ✅ have (leaders) |
| **Weakening** | ⛅ **Rolling-over** | ➕ | ➖ | >200, lost 50 | a leader **cracking** — *the reverse of recovery* | trim / protect | ❌ **missing** |
| **Lagging** | 🌧 **Headwind** | ➖ | ➖ | <200 & <50 | weak, still weakening — *weak-in-weak* | avoid | ✅ have (laggards) |
| **Improving** | 🌅 **Recovery** | ➖ | ➕ | <200, reclaimed 50 | deep base **turning up** | accumulate / watch | ⏳ proposed |
| (middle) | ☁ **Neutral** | ~0 | ~0 | near 50 | consolidating / undefined | wait | n/a |

The two we're blind to are **Recovery** (the entry signal) and **Rolling-over** (the exit
signal). `leaders_laggards()` only ever returns Leading and Lagging. **Building Recovery +
Rolling-over completes the square** and turns four disconnected lists into one system.

### Already shipped, just not connected
- `sector_weather()` / `_WEATHER` (`cockpit.py:143–211`) ALREADY classify a *sector* into
  exactly these five states from its RS slopes + trend_state. Colors already match the RRG
  (`rrg_view.py:51` QCOLOR). **We are adopting shipped vocabulary, not inventing names.**
- `rrg.py` already computes the sector quadrant + the two transition flags `improving_entry`
  (Headwind→Recovery base-turn) and `weakening_warning` (Tailwind→Rolling-over) into
  `rs_extras`, live at `/dash/rrg`.
- The whole thing is missing at the **stock** level, and missing as a **unified surface**.

---

## 2. The core abstraction — one phase label, not four screens

Don't bolt on four ad-hoc SQL screens. Compute **one weather/phase label per name** and let
every surface group by it. The classifier `sector_weather()` is already generic — it takes
1m/3m/6m/12m slopes + a trend_state, which a *stock* has too (`rs_vs_broad_slope_*` +
`rs_vs_broad_trend_state`). So:

- **Stocks:** `rs_phase` = weather of the stock's **RS-vs-broad** series (its strength vs the
  whole market — consistent with `rs_rank` and with the sector's own label). Reuse the same
  function (alias `rs_weather = sector_weather` for naming sanity; do NOT fork the math).
- **Sectors:** `rs_phase` = the sector's existing RS-vs-broad weather.

Store `rs_phase` nightly on both `stock_signals` and `index_signals` (one TEXT column each).
Storing it (vs on-read) is what makes **phase-transition detection** a trivial compare
against the prior row — see §4.

### Two layers, deliberately

1. **Broad label (every liquid name gets one of 5 phases).** Powers the 2×2 grid overview
   and the phase chip in the table. Loose by design — it's a *map*, everyone is somewhere.
2. **Strict per-quadrant shortlist (the actionable "X-in-X").** The diagonal where the
   **stock and its sector share the phase** AND the confirmed gates pass. Strong-in-strong is
   already exactly this for Tailwind (stock Tailwind + sector Tailwind, all `trend_state` up).
   We build the same rigor for the other three. This is "complete picture" (layer 1) AND
   "confirmed turn" (layer 2) without contradiction.

---

## 3. The strict shortlist gates per quadrant

All on the **liquid universe** (`_LIQUID_FILTER`), requiring the stock's `primary_sector` to
share the phase (join `index_signals`). The term-structure legs are symmetric across the
square — one mental model, four sign-patterns:

| Quadrant | BASE/RUN (long) | TURN (short) | CONFIRM (MA / not-a-knife) | Stock+sector agree |
|---|---|---|---|---|
| 🌤 **Tailwind** (have) | 12m ➕ | 1m ➕ & 3m ➕ | above 200 **and** 50 | both `trend_state` UPTREND/BREAKOUT |
| 🌅 **Recovery** (new) | 12m ➖ (depth via 18m/24m) | 1m ➕ & 3m ➕ | reclaimed 50, still **below 200** | both phase = Recovery |
| ⛅ **Rolling-over** (new) | 12m ➕ (run height via 18m/24m) | 1m ➖ & 3m ➖ | lost 50, still **above 200** | both phase = Rolling-over |
| 🌧 **Headwind** (have) | 12m ➖ | 1m ➖ & 3m ➖ | below 200 **and** 50 | both `trend_state` DOWNTREND/BREAKDOWN |

Key boundaries (these make the quadrants **disjoint** and give clean hand-offs as a name
rotates):
- **Recovery vs Tailwind:** the `above_200ma` line. A base that fully matures (RS reclaims its
  200-MA) graduates Recovery → Tailwind automatically. No double-counting.
- **Rolling-over vs Headwind:** same `above_200ma` line on the way down. A leader that loses
  its 200-MA degrades Rolling-over → Headwind.
- **Mandatory long floor = 12m**; 18m/24m *grade magnitude* (depth of base for Recovery,
  height of run for Rolling-over) and *rank* within the quadrant — they are not a hard gate,
  so a name with only ~14–18m of history still qualifies (NULL long-window = "unknown depth,"
  not "fails"). Graceful-NULL rule.

> **Why stock AND sector must agree (the diagonal):** a recovering stock in a still-falling
> sector fights its peer tape; a cracking leader in a still-strong sector may just be pausing.
> Requiring agreement is the same three-layer rigor strong-in-strong already uses. Cross-phase
> cells (e.g. Recovery stock in a Tailwind sector — arguably the *best* setup: cheap name,
> strong group) are visible in the table via the sector-phase column, and are a **deferred v2
> refinement** (the full 16-cell matrix), not v1.

---

## 4. The dynamic edge — rotation lifecycle + phase-transition alerts

A static list can't show movement. Two things make this a *system*:

1. **Clockwise lifecycle:** `Recovery → Tailwind → Rolling-over → Headwind → Recovery`. Buy in
   Recovery, ride Tailwind, exit on Rolling-over, avoid Headwind, watch for the next Recovery
   turn. The *same name* travels the loop — this is the "dynamics" the 18m/24m depth is for.
2. **Phase-transition events = the actionable signal.** A name that *just crossed*
   Headwind→Recovery (a base turn) or Tailwind→Rolling-over (a leader cracking) **today / this
   week** is the event worth surfacing — catching the turn beats reading a static list. With
   `rs_phase` stored nightly, "fresh transition" = today's `rs_phase` ≠ the most recent prior
   row's `rs_phase` (a cheap self-join). The sector-level analogues already exist
   (`improving_entry`, `weakening_warning` in `rs_extras`); we add the stock-level compare.
   Surfaced as a "✨ just turned" flag and a dedicated "Movers between phases" strip.

---

## 4b. Leveraging RS harder — the seven reads folded in

Beyond the four-phase map, these extract more signal from the **same** RS data. (1)–(4) are
near-free and ride the nightly pass; (5)–(7) reuse engines we already own. RS-based position
sizing remains the documented throughline (§11).

**(1) RS leads price** — `rs_leads_price`. The RS line prints a new 52w high while *price* is
still below its own 52w high (margin, e.g. ≥5%). Institutional accumulation showing up in
relative strength *before* price confirms — the classic leading tell. We already store the RS
new-high flag and price highs; this just crosses them. *Data:* stored flag, nightly. *Surface:*
"RS▲>price" badge + filter; strongest inside 🌅 Recovery and early 🌤 Tailwind.

**(2) RSI-of-RS timing tier** — un-strand the computed-but-unused `rsi_of_rs` (today it only
decorates `/dash/rrg`) and extend it to STOCKS. `stock_rs.build_rs_history()` already builds
each stock's RS series in memory, so running `rrg._rsi_series` on it is one extra O(n) pass.
*Use — the* extension *axis the quadrant/slopes miss:* 🌤 Tailwind + RSI-of-RS >70 = extended,
don't chase (precedes the ⛅ crack); 🌅 Recovery + oversold-turn = the earliest base-turn tell,
a "watch" tier ahead of the confirmed shortlist. *Data:* store `rsi_of_rs` on stock_signals;
overbought / oversold-turn derived via self-join to the prior row. *Surface:* column +
"stretched" / "washed-out turn" chip.

**(3) RS acceleration (stacked term structure)** — direction is binary in the 2×2; *steepening*
is a grade. `rs_stacked` = the slopes line up monotonically (1m>3m>6m>12m, rising) — the
strongest 🌤/🌅 names. *Data:* pure function of stored slopes (incl. new 18/24m) — derived on
read, no column. *Surface:* "⚡ accelerating" mark + a sort key.

**(4) Freshness / time-in-phase** — early leaders ≫ extended ones. `rs_phase_since` = the date
the current phase began (from the transition compare we already run for the movers strip);
age = today − since. *Data:* store `rs_phase_since` on both tables. *Surface:* an "age" column +
sort; a "fresh" tag for names <~10 sessions into a phase; corroborates (2)'s extension read.

**(5) Delivery (DVPT) confirmation** — an RS turn *confirmed by institutional delivery* ≫ thin
drift. Fuse the rotation shortlists with the DVPT engine we already own — read existing
`stock_signals` fields (`p_score`, `trigger_rank`, `accum_character`) and mark a turn
*confirmed* when a power-day / ACCUMULATION coincides. `conviction_shortlist` already does this
for leaders; generalize it to 🌅 Recovery and ⛅ Rolling-over. *Data:* none new — read-time
fusion. *Surface:* "✅ delivery-confirmed" mark + a sort that floats confirmed turns.

**(6) Dual-momentum gate** — RS says "best horse"; absolute trend says "the race is worth
running." Tag (soft, default) or gate (strict) RS leaders/recoveries on positive *absolute*
momentum (price above its own 200-day MA / positive 6m price return) so we don't buy the best
house in a bad neighborhood in a downtape. Honors the regime banner. *Data:* reuse a price-trend
read if present, else a small nightly `abs_trend_up` flag. *Surface:* a gate toggle + an
"abs ✔/✘" tag.

**(7) Leadership breadth** — a macro health read aggregated from sector `rs_phase`: how many
sectors are 🌤 Tailwind, is leadership *narrowing* (fragile — "only Defence") or *broadening*,
are NEW sectors rotating into 🌅 Recovery. *Data:* none new — aggregate over `index_signals`.
*Surface:* a one-line breadth banner atop `/dash/rotation` + Home (ties to the regime banner).

---

## 5. Data layer — 18m/24m windows + the phase column

### Schema (additive, via the `_ensure_column` idiom in `db.py`)
`index_signals`: `slope_18m_pct`, `slope_24m_pct`, `rs_phase`, `rs_phase_since`
`stock_signals`: `rs_vs_broad_slope_18m/24m`, `rs_vs_sector_slope_18m/24m`, `rs_phase`,
`rs_phase_since`, `rsi_of_rs`, `rs_leads_price` (+ `abs_trend_up` only if no existing
price-trend read covers §4b-6).

All nullable; no table rewrites, no normalization change — same pattern as every prior RS
column (`db.py:991–1013`). The §4b reads (3) acceleration, (5) delivery-confirm, (6)
dual-momentum-soft, (7) breadth are **derived on read** (no columns).

### Compute (trivial)
- `index_signals.compute_ratio_signal` (`index_signals.py:266–279`): add `slope(545)` /
  `slope(730)` → return dict → `_RATIO_SIG_COLS`. `stock_rs.py` reuses this engine, so extend
  the broad + sector UPDATE SQL + `*_to_update` tuples by the two columns each.
- `rs_phase`: after slopes are known, call `rs_weather(s1,s3,s6,s12,trend_state)` and store the
  key. Sector phase falls out of the existing `sector_weather()` call. No new job, no LLM.
  (v1 keeps the weather classifier on 1m–12m as-is; whether 18m/24m should sharpen the
  RECOVERY "deep base" / ROLLING-OVER "long run" conditions is a §10 tunable.)

### Backfill (one-time, on the VPS — same commands `full-field-backfill.sh` already runs)
```
python -m src.automation.index_signals --backfill
python -m src.automation.stock_rs       --backfill
```
Then a one-pass `rs_phase` fill (rides the same backfill). Nightly populates thereafter.
Index + D47 deep-history give ~2004 depth, so 18m/24m populate for the vast majority; new
IPOs get NULL long-windows and still classify on 12m.

---

## 6. The read API
In `stock_rs.py`, symmetric helpers sharing `_LIQUID_FILTER` + the `index_signals` sector join:
- `phase_members(phase, limit, trade_date)` — every liquid stock whose `rs_phase` = phase
  (the grid cells / the table). Returns full term structure + sector phase + fresh-transition
  flag.
- `phase_shortlist(phase, limit, trade_date)` — the strict diagonal "X-in-X" per §3 (stock +
  sector agree + confirmed gates). `leaders_laggards("leaders")` becomes the Tailwind case of
  this; keep it as a thin alias for back-compat.
- `phase_movers(trade_date)` — names whose `rs_phase` changed vs their prior row (the
  transition strip).
Pure SQL, rule-based, ₹0 read — doctrine-clean.

---

## 7. UI — 2×2 grid + data table

**`/dash/rotation`** (new, full-bleed `render_rotation()` in `cockpit.py`, mounted in
`main.py` one-liner like `rrg_view`):
- **Top — the 2×2 grid.** Four panels positioned like the RRG axes so the flow is visual:
  `🌅 Recovery` (top-left) · `🌤 Tailwind` (top-right) · `🌧 Headwind` (bottom-left) ·
  `⛅ Rolling-over` (bottom-right). Each panel shows count + the top ~6 strict-shortlist names
  with RS rank. (☁ Neutral sits as a thin center/count, not a panel.) Reuses `_WEATHER` colors
  → instant visual consistency with the sector weather badges and `/dash/rrg`.
- **A "✨ Just turned" strip** — `phase_movers()`: fresh Headwind→Recovery and
  Tailwind→Rolling-over crossings.
- **Bottom — one wide sortable table** (existing data-grid toolbar: sort/filter/CSV) with an
  `rs_phase` chip column + the FULL term structure 1m·3m·6m·12m·18m·24m (broad and sector) +
  rs_rank + sector phase, per [[data-first-light-ui]]. Filter to a phase, or sort by base
  depth / turn strength — a click, not a code change.

**Home:** replace the lone "Strong-in-strong" board with a compact **4-cell rotation strip**
(one cell per quadrant: count + top 2–3 names, weather-colored) linking to `/dash/rotation`.
Strong-in-strong lives on as the Tailwind cell.

**Stock page:** a weather badge — "🌅 Recovery — term structure flipping (12m− , 1m+/3m+,
reclaimed 50-MA; sector also Recovery)" — when the stock qualifies. Reuses the existing badge
component.

**Telegram:** `/rotation` (the 2×2 summary) and per-phase `/recovery`, `/rollingover`
(`/leaders`, `/laggards` already exist) — all DRY off the helpers in §6.

---

## 8. Guardrails
- **Liquidity:** `_LIQUID_FILTER` everywhere — no illiquid "rotations."
- **Falling-knife / dead-cat exclusion:** the MA-reclaim CONFIRM leg (Recovery needs RS back
  above its 50-MA; Rolling-over needs it to have *lost* the 50-MA) keeps noise out of the
  strict shortlists.
- **Disjoint quadrants:** the `above_200ma` boundaries (§3) guarantee a name is in exactly one
  phase and hands off cleanly as it rotates — no double-counting across boards.
- **Thin-list honesty:** strict shortlists can be near-empty in a one-sided market (few
  recoveries in a roaring bull tape). The page says so plainly rather than loosening silently;
  persistent emptiness is the signal to revisit gates (§10), not to weaken them quietly.

---

## 9. Doctrine compliance
Rule-based > LLM ✓ · no LLM on a timer ✓ · pre-compute nightly, ₹0 reads ✓ · additive schema
(`_ensure_column`, archive untouched) ✓ · value-based RS (adjusted price ratios) ✓ · cost:
two extra arithmetic ops/row + one phase label + a one-time backfill re-run, no API spend ✓.
Reuses `sector_weather`/`_WEATHER`/`rrg.quadrant` rather than forking — least new surface area.

---

## 10. Build plan (on approval — three staged commits, each verifiable & PROJECT_STATE-synced)

**Stage 1 — data layer (nightly compute + backfill).**
1. `db.py`: `_ensure_column` for the §5 columns; add 18/24m + `rs_phase`/`rs_phase_since` to
   the `index_signals` CREATE block.
2. `index_signals.py`: `slope(545)`/`slope(730)` → return dict → `_RATIO_SIG_COLS`; store
   `rs_phase` (+ `rs_phase_since` via prior-row compare) using `sector_weather`.
3. `stock_rs.py`: extend broad + sector UPDATE SQL/tuples (18/24m); alias
   `rs_weather = sector_weather` (don't fork) and store `rs_phase`/`rs_phase_since`; run
   `rrg._rsi_series` on the already-built RS series → store `rsi_of_rs` (§4b-2); compute
   `rs_leads_price` (§4b-1).
4. Backfill on VPS (`index_signals --backfill`, `stock_rs --backfill`) + record coverage.

**Stage 2 — read API + leverage.**
5. `stock_rs.py`: `phase_members`, `phase_shortlist`, `phase_movers`; `leaders_laggards` →
   thin Tailwind/Headwind wrappers. Reads derive §4b-(3) stacked, (5) delivery-confirm (read
   `p_score`/`trigger_rank`/`accum_character`), (6) dual-momentum tag, (7) breadth aggregate.

**Stage 3 — surfaces.**
6. `cockpit.py`: `render_rotation()` (2×2 grid + "✨ just turned" movers + breadth banner +
   wide data table with phase chip, full term structure, RS-leads-price / RSI / accel / age /
   delivery / abs-mom marks) + Home 4-cell strip + stock badge; `main.py`: mount
   `/dash/rotation`; `telegram_bot.py`: `/rotation` `/recovery` `/rollingover`.
7. Each stage: **PROJECT_STATE** in the SAME commit (Decision log, Database schema, Key file
   paths, Telegram commands, What's-built, Session log).
8. **Verify** — all `/dash/*` 200; quadrants disjoint; Tailwind == old strong-in-strong set;
   spot-check a known turnaround (🌅) and a known fader (⛅); confirm `rsi_of_rs` now drives a
   read (no longer stranded).

### Decision-log entries to add on build
- **D6x — 18m/24m RS windows** (grade base depth / run height beyond one year).
- **D6x — Unified RS rotation (weather) phase** on stocks + sectors; one `rs_phase` reusing
  `sector_weather`/`_WEATHER`; disjoint quadrants via the 200-MA boundary; phase-transition
  movers as the actionable edge.
- **D6x — Complete the 2×2:** Recovery (🌅) + Rolling-over (⛅) strict shortlists +
  `/dash/rotation` grid. Strong-in-strong = the Tailwind case.
- **D6x — Seven RS-leverage reads** (§4b): RS-leads-price, RSI-of-RS timing tier (un-stranded +
  extended to stocks), acceleration/stacked, freshness, delivery confirmation, dual-momentum,
  leadership breadth. WHY each: see §4b. Position sizing deferred (throughline, §11).

---

## 11. Open tunables (revisit after live use)
- CONFIRM strictness: 50/200-MA reclaim (default) vs a softer 6m-turn confirm.
- Whether `rs_weather` should fold 18m/24m into the RECOVERY "deep base" / ROLLING-OVER "long
  run" tests (default: classifier stays 1m–12m; 18m/24m grade + rank + display only).
- Sector gate: stock & sector must share the phase (default) vs sector rrg-`Improving`/
  `Weakening` alone sufficient (looser → more names).
- Headline sort within a quadrant: turn strength vs base depth vs blend (default: turn
  strength; depth is a column + click-sort).
- Dual-momentum (§4b-6): soft tag (default) vs hard gate that removes abs-down names entirely.

### Backlog (post-build, separable)
- **RS-based position sizing — the throughline.** Rank → *weight* the actual portfolio, not
  just screen. This is where all the RS work is meant to land (DVPT→ranked-portfolio direction,
  [[patearn-brand-and-dvpt-direction]]). Longer-horizon; its own design pass.
- **v2: the full 16-cell stock-phase × sector-phase matrix** — surface premium cross setups
  (e.g. a 🌅 Recovery stock inside a 🌤 Tailwind sector = cheap name, strong group).
