# RS Support & Resistance — the mean-reversion / range lens (sector RS vs Nifty 500)

> **Status:** DESIGN PROPOSAL + interactive prototype shown (session 2026-06-23). **Build GATED on sign-off.**
> Brainstormed with three parallel agents (quant-method · visualization · decision-utility+skeptic);
> they converged independently on the same spine. This doc is the running source of truth for the
> feature; keep it rich ([[preserve-strategy-intent]]) — do NOT one-line it.
>
> **The one-sentence claim:** everything shipped so far (RRG, rotation "weather", Mansfield) measures
> the *derivative* of relative strength — direction & momentum. This measures the **level**: where a
> sector's RS-vs-Nifty-500 sits inside its *own* historical distribution. Level ⟂ trend; it is genuinely
> new information that changes sizing decisions.

---

## 1. The idea (Ramana's words)

Each sector's RS ratio vs Nifty 500 = `close(sector)/close(Nifty 500)` historically oscillates in a
band. There is a ceiling it rarely exceeds (**RS resistance**) and a floor it rarely breaches (**RS
support**). Near its floor a sector is "relatively cheap versus its own history"; near its ceiling,
"relatively rich." We want to (a) compute those levels robustly per sector, (b) show where each sits
*today* within its band, and (c) flag when a sector **breaks** its historical band (structural
re-rating — the highest-value event).

This is orthogonal to the RRG (RS-Ratio × RS-Momentum quadrants) and the 4-phase rotation weather,
which are trend/momentum instruments and are **structurally silent on level**. Band-position is the
**fuel gauge**; the RRG is the **speedometer**. You need both to drive.

---

## 2. Method — converged recommendation

**Primary:** rolling, **recency-weighted percentile band** → a single 0–100 **`rs_band_pct`**
("position-in-band"). 0 = at historical RS support (cheapest vs own history), 100 = at RS resistance,
50 = rolling median. The percentile *is* the position-in-band; computed over a recency-weighted rolling
window it handles drift by construction. Bounded [0,100], shape-faithful (respects skew/multimodality),
no distributional assumption, cheapest to compute, easiest to put on a gauge.

Why percentile-rank and not `%B = (R−L)/(U−L)`: `%B` clips/extrapolates past the rails and throws away
the distribution shape. Expose `%B` for the *chart rails* if useful, but the **score is the percentile**.

**Non-negotiable refinements (each maps to a skeptic guard, §4):**

1. **Log space.** Everything on `ln R`. A ratio is multiplicative; log makes the band symmetric in %
   and a structural drift a constant. (Codebase already chose adjusted-price ratios — consistent.)
2. **Rolling, never anchored, as the scored band.** Default `W = 756` (3y); also publish `W = 5y/10y`.
   Keep an *anchored all-time* min/max **only** as a reference line + break trigger (§ break detection),
   explicitly labelled "all-time" — never as the live band.
3. **Recency weighting (decay).** Weight day `i` by `λ^(t−i)`, half-life `h ≈ 252` (1y), so the current
   regime dominates and old regime fades *continuously* — kills the rolling-window-edge discontinuity
   (a 2020 COVID spike must not make the ceiling "jump" the day it exits a hard window).
4. **Dual-window, shown side by side.** 3y and 10y will disagree violently for IT/Pharma/Defence — that
   disagreement *is* signal ("regime in flux"). Never collapse to one "the band." (The prototype's
   window toggle demonstrates this: beads move when you switch.)
5. **Detrended twin.** Publish a second percentile on the **Mansfield-detrended** series
   `(R/SMA200(R) − 1)` — *already computed* in `rrg.py`, do not fork. Headline gauge = raw-level
   percentile (the literal ask); the detrended twin rides alongside as the "rich vs history but NOT vs
   trend" caveat. When they diverge a lot (level 88 rich / detr 52 neutral) → "historically rich, but
   consistent with an active re-rating." Deterministic string, no LLM.
6. **Point-in-time (no look-ahead).** The band at date *t* uses only data ≤ *t*. Build invariant; add a
   test that the band series at *t* is byte-identical whether or not future rows exist.

**Secondary corroborator:** **RS time-profile / KDE** — POC (Point of Control = modal RS level = the
magnet / "fair RS") + 70% **Value Area** (VAL/VAH = time-weighted support/resistance that respects
multimodality — a re-rated sector shows *two* high-density clusters, which a quantile blends away).
One extra histogram per sector per night. On the chart: quantile rails = "rarely beyond here," POC =
"keeps coming back here," low-volume gaps = "travels fast through here."

**Rejected as primary (kept as optional overlays):** Bollinger/Keltner (chase a moving average; get
"walked" in trends — false-rich exactly during re-ratings) and regression channels (assume one linear
trend over the window). Swing-pivot/fractal S/R zones are the best *chart annotation* but don't reduce
to a clean score and carry two tuning knobs → defer to a "show pivot zones" toggle.

### 2a. THE honesty gate — regime test (build this BEFORE the verdict)

The naive "it never went above X = resistance" is statistically dangerous: it would have shorted IT
and Defence at every step up. **The band verdict is only valid for mean-reverting (range-bound) RS
series.** Compute a per-sector regime test — Hurst exponent or a simple ADF-style trending-vs-reverting
read — and:
- **Mean-reverting** → band verdict fires (cheap/rich is meaningful; mean-reversion is the play).
- **Trending / re-rating** → **suppress the cheap/rich verdict**, replace with "TRENDING — band invalid;
  breakouts = re-rating, not exhaustion." (This is also a *feature*: it's how you tell a Defence
  breakout from a fade-able blow-off.)

Without this gate (and the history floor, §4-5), **do not ship the verdict** — ship only the descriptive
percentile with loud caveats.

### 2b. Break detection — the highest-value events (separate state column)

Distinguish *rejection at the band* (RS pokes the edge and reverts → mean-reversion intact) from
*acceptance beyond the band* (RS closes beyond and **stays** on momentum → structural re-rate). A
confirmed **BREAKOUT** above RS resistance requires ALL of:
1. **Penetration:** close above the anchored/3y-rolling max + buffer `b ≈ 1.5–2%` (or `0.5σ` in log).
2. **Persistence (acceptance):** stays above for `m ≈ 5` consecutive closes (the wick-vs-regime filter).
3. **Momentum agrees (reuse existing, ₹0):** `slope_3m > 0` AND `Mansfield > 0` AND ideally
   `above_200_ma` on the ratio. A "breakout" while 3m slope is negative is a fakeout → reject.

Symmetric for **BREAKDOWN**. Everything else that touches an edge but fails a gate = `TOUCH_*` (the
mean-reversion signal, explicitly *not* a break). A **failed break** (armed, then falls back inside
within `m`) is itself high-value (failed RS breakout = short-term top; failed breakdown = washout
bottom). One stored enum `rs_band_state ∈ {INSIDE, TOUCH_SUP, TOUCH_RES, BREAK_ARMED_UP/DN,
BREAKOUT_UP, BREAKDOWN_DN, FAILED_BREAK}`. After a confirmed break, **re-anchor** (old edge → opposite
reference; rolling band re-forms). All inputs already exist → ₹0, deterministic.

---

## 3. Decision utility — fusion, never standalone

Band-position alone never triggers. It is always **level × direction × confirmation**. The central
tension — near support = mean-reversion BUY *or* value trap — is resolved by crossing band-position with
signals we already compute:

| | **Near support** (≤20) | **Mid** (20–80) | **Near resistance** (≥80) |
|---|---|---|---|
| **Recovery / slope turning up** | **ACCUMULATE** (cheap + turning — the prize) | add / hold | breakout buy, size down (re-rating) |
| **Neutral / flat** | **WATCH** (arm alert on slope flip) | hold | trim into strength |
| **Headwind / slope still falling** | **AVOID** (value trap — the de-rating) | reduce | trim hard |
| **Rolling-over / slope turning down** | (rare) treat as Headwind | trim | **FADE** (exhaustion at ceiling) |

The actionable money is the left-column diagonal: **cheap+turning = ACCUMULATE** vs **cheap+bleeding =
AVOID** — *same level*, opposite action; the weather/slope splits them. This is the entire thesis for
why the view must be fused.

**The confirmation stack (cheap → accumulate):** ① level `rs_band_pct ≤ 20` (3y & 5y agree) → ② turn
(slope 1m/3m positive, or weather=Recovery, or RSI-of-RS turning up from oversold) → ③ **down-capture
< 1.0 as a HARD value-trap veto** (a genuine de-rating bleeds *more* than the index on red days; quiet
accumulation falls *less* — this is Ramana's stated objective and the single best trap filter we own) →
④ DVPT delivery accumulation in the sector's heavyweights. All four = ACCUMULATE; drop ② = WATCH;
③ fails = AVOID regardless of cheapness. Mirror for near-resistance: ride (new band highs + accelerating
slope + up-capture > 1 = re-rating, don't fade) vs fade (rolling over + up-capture deteriorating +
RSI-of-RS > 70 rolling down).

**Tie to the ranked-portfolio / position-sizing throughline:** band-position is a natural **sizing
modulator on top of RS rank** — `size ∝ rank_score × f(rs_band_pct)`, f rewarding low percentile on
entry (more mean-reversion runway) and capping exposure as percentile → 100. **Decision forced: tilt on
entry (soft), gate on exit (strict)** — size up cheap leaders softly, but make `rs_band_pct ≥ 90 + flat
slope` a *hard* trim trigger. Asymmetric because a missed cheap entry costs opportunity; a topped-out
leader costs drawdown. This is the sizing tiebreaker the RRG cannot give (same Recovery quadrant, one
recovering from the 10th percentile, one from the 70th — very different prize).

---

## 4. Skeptic guards the build MUST include

1. **Non-stationarity / band drift** → rolling only; show 3y & 10y; display band width + its trend; never
   a naked percentile without its window.
2. **Structural re-rating (IT/Defence killer)** → the §2a regime gate. Suppress cheap/rich on trending
   series. *Non-negotiable.*
3. **Break ambiguity (re-rate vs blow-off)** → a band break only *upgrades to a watch*; the *direction*
   of action comes from the fused signals. A break never auto-prints "buy" or "fade."
4. **Survivorship / index reconstitution** → prefer the longest-lived, most-stable index per sector;
   annotate major reconstitutions; low-confidence flag on frequently-revamped indices; optional
   equal-weight/constituent-built sanity check (divergence = composition artifact).
5. **Thin / short history (Defence, Chemicals, new indices)** → **hard minimum-history floor**
   (≥5y for a 3y-window verdict, ≥10y for the long-window). Below it: "insufficient history — band not
   computed," not a number. Tier every sector; grey out thin ones; new indices get RRG/slope only.
6. **Look-ahead bias** → point-in-time band (§2-6) + the byte-identical test.
7. **Mean-reversion fails in strong trends** → "RS support is a *context*, not a *trigger*"; weather/slope
   + down-capture are the regime filter; band-position never a standalone buy.
8. **The denominator moves too** (Nifty 500 reconstitutes) → document the yardstick is non-stationary;
   optionally show RS vs a second broad proxy and flag divergence.
9. **Multiple comparisons** (19 sectors × windows × 2 rails → something is always extreme) → surface only
   *fused* extremes (level + turn + capture + delivery aligned), never every percentile extreme. The
   confluence requirement is itself the data-mining defence.

---

## 5. The surprise — headlines this view can print that RRG/weather structurally cannot

- **"IT is at a 15-year RS low vs Nifty 500 — and down-capture just dropped below 1."** RRG can only say
  "improving/lagging"; it can never say *how historically depressed the base is*. Improving-from-15y-low
  is a categorically more asymmetric bet than improving-from-mid-band. Flagship.
- **"FMCG is pinned at the 95th percentile of its 10-yr RS band and the slope just flattened."** A
  *leading* exhaustion tell — weather shows Tailwind right up until it cracks.
- **"Defence just broke its multi-year RS ceiling AND fails the mean-reversion test → re-rating, not
  exhaustion."** The regime gate distinguishes a new-era breakout from a fade-able blow-off; the RRG sees
  "strong & stronger" in both and can't tell them apart.
- **"Pharma & PSU-Banks are both Recovery on the RRG — but Pharma from the 10th percentile, PSU-Banks
  from the 70th."** Identical weather, very different prize → the sizing tiebreaker.

---

## 6. Visualization (prototype shown; house style = inline SVG + vanilla JS, or Lightweight Charts v4)

**Hero — all 19 sectors: "Position-in-Band Beeswarm" on one shared 0–100 axis.** Support left, resistance
right; green VALUE wash (0–25), amber RICH wash (75–100), red caps for breaks. Bead colour = RS direction
(rising/falling/flat), size = |Δ|, breakouts/breakdowns pinned to the caps with ▲/▼ flags. One shared
ruler is the only layout where comparison is pre-attentive. **Wow interaction = "Play 6-month rotation":**
all beads animate from their position 6 months ago to today with comet trails — you *watch* rotation
happen (defensives sinking into value, cyclicals climbing into rich, one piercing the cap). Twin toggle =
Headroom Bullet Wall (same vertical scale, "+18% to ceiling / −22% to floor"). Window toggle (3y/10y)
moves the beads — demonstrates non-stationarity live.

**Deep view — single sector: "The Channel."** The 20-yr RS line inside its support/resistance band (LWC
or SVG), gradient "water" amber→neutral→blue between rails, median + POC magnet lines, a "now" dot
coloured by direction; drag-select a date range → rails recompute for that window and animate (makes the
S/R feel *earned from the data*, and lets him ask "where were the rails during the last bull run?").
Docked live **Thermometer** gauge + verdict chip + regime label + headroom readout.

**Embeddable atom — "Thermometer Rail" column** for the existing wide screener (`/dash/sectors`): a slim
support→resistance capsule with a mercury fill to `rs_band_pct` + the number, sorted ascending. Same
encoding, denser, drops into the data-first table house style ([[data-first-light-ui]]).

**"Lab" of alternate skins (worth a prototype, save for later):** **Gravity Well** (RS marble springs
toward high-density nodes — mean reversion made literal; the most novel idea), **RS Ridgeline/Joyplot**
(19 stacked RS-density mountains with one TODAY needle), **Band Clock** (radial bloom; atmospheric
"market froth" gestalt). **Micro-delight:** band break = the Tide-Tank *overflows*/*cracks* + a
"⚡ BREAKING" pinned strip; FLIP re-sort animation on every reorder; spring-to-rest on scrub release.

**Build-additive guard ([[build-additive-never-replace]]):** ADD an "RS Position-in-Band" gauge + rail
overlay onto the existing `/dash/ratio` page and one column on `/dash/sectors`; new surface goes in a
new module (`src/web/rsband_view.py` or similar), thin dashboard wrapper. Never reroute `/dash/ratio`,
`/dash/rrg`, `/dash/rotation`, `/dash/mep`, `/dash/compare`.

---

## 7. Data layer (additive; own the columns at runtime via the `rs_phase.ensure_columns` idiom — do NOT edit db.py while parallel-held)

Pre-compute nightly per `(numerator, denominator)` on the existing `ratio_signals` row (one second pass
after `compute_ratio_signal`), all derivable from `ratio_rows.ratio`, log-space, `W=756`, `h=252`:

| Column | Meaning |
|---|---|
| `rs_band_low_3y`, `rs_band_high_3y`, `rs_band_mid_3y` | recency-wtd 5/95/50 pct rails (3y) |
| `rs_band_low_5y`, `rs_band_high_5y` | 5y rails (regime-disagreement check) |
| `rs_alltime_high`, `rs_alltime_low` | anchored all-time max/min (break reference, §2b) |
| **`rs_band_pct`** | **recency-wtd percentile of today's R in the 3y window (0–100) — HEADLINE** |
| `rs_band_pct_detr` | same on the Mansfield-detrended series (re-rating caveat) |
| `rs_band_pct_label` | banded text {At support … At resistance} (or derive on read) |
| `rs_profile_poc`, `rs_profile_val`, `rs_profile_vah` | KDE magnet + 70% value area |
| `rs_band_width_pct` | `(high−low)/mid` — vol/regime context |
| `rs_regime` | {MEAN_REVERTING, TRENDING} from Hurst/ADF (§2a gate) |
| `rs_band_state`, `rs_band_state_days` | break state machine (§2b) + age |
| `band_maturity` | {provisional, full} from effective sample size (§4-5) |

Denormalize the headline trio (`rs_band_pct`, `rs_band_pct_detr`, `rs_band_state`) onto `index_signals`
vs Nifty 500 (mirroring `rs_vs_broad_*`) so the Sectors table reads with zero joins. One-time backfill
(batch all columns, ~10 min on the VPS); nightly thereafter. Every render is a ₹0 SQL read.

---

## 8. Doctrine compliance

Rule-based > LLM ✓ · no LLM on a timer ✓ · pre-compute nightly, ₹0 reads ✓ · additive (own columns via
`ensure_columns`, archive untouched) ✓ · value/adjusted-price RS ratios ✓ · reuses Mansfield/RSI-of-RS,
`ratio_signals`, the `stock_rs` denormalize pattern rather than forking ✓ · additive UI (new module,
sacred pages untouched) ✓.

---

## 9. Build plan (on approval — staged, each verifiable + PROJECT_STATE-synced in the SAME commit)

- **Stage 0 — regime gate + history tiering first** (`rsband.py`: Hurst/ADF per sector; min-history
  floor). Without this the verdict is unsafe. Self-test on IT/Defence/Media (must NOT print "cheap, fade"
  on Defence).
- **Stage 1 — data layer:** the §7 columns via `ensure_columns`; recency-wtd quantile + KDE POC/VA +
  break state machine; backfill on VPS; record coverage; point-in-time test.
- **Stage 2 — read API** (`rsband.py`): `band_all(denominator)` (the 19 beads), `band_one(num,den)` (the
  channel + rails + POC + state + regime), `band_fused()` (the §3 confluence headlines). Pure SQL.
- **Stage 3 — surfaces:** beesarm hero + channel + thermometer column (new `rsband_view.py`, mounted in
  `main.py` one-liner; thin dashboard wrapper); rail overlay on `/dash/ratio`; one column on
  `/dash/sectors`; Home one-liner of fused headlines. Verify all `/dash/*` 200 (zero regression).
- Decision-log entries on build: D6x band primitive (rolling recency-wtd percentile, dual-window,
  log-space, detrended twin, point-in-time); D6x regime gate + history floor; D6x break state machine;
  D6x fusion matrix + sizing (tilt-entry/gate-exit); D6x surfaces.

---

## 10. Open tunables (revisit after live use)

- **Rotation-replay horizon (UI):** the beeswarm "Play" lookback is **selectable 6m / 12m / 24m,
  default 12m** (the cycle). 6m = tactical "what's rotating now"; 24m = structural "who round-tripped /
  re-rated" — and since the band is a multi-year object, the longer horizon is the more native read.
  The replay traces the **real monthly path** (not a 2-point teleport) so backtracks show; a "show net
  moves" toggle freezes a start→today arrow per sector. (Decided 2026-06-23 on Ramana's question.)
- `W` (3y default) and half-life `h` (1y); percentile p (5/95 vs 10/90); KDE bandwidth.
- Regime test choice (Hurst vs ADF) + the threshold that flips MEAN_REVERTING↔TRENDING.
- Break buffer `b` and persistence `m`; whether to re-anchor hard or blend after a confirmed break.
- Sizing: tilt-only vs gate; the exact `f(rs_band_pct)` curve.
- Second denominator (Nifty 500 vs a broader all-cap proxy) for the §4-8 yardstick check.

---

## 11. Ramana's prototype review (2026-06-23) — RUNNING LOG, more feedback still coming

Reviewing the five prototype skins one by one. Verdict + the change it implies. **He is still adding —
do NOT start building until he signals done.**

| Skin | Verdict | Action implied |
|---|---|---|
| **① Beeswarm** (all-19 on the support→resistance axis) | **MUST-HAVE — core surface** | Put the rotation-play on it with **6 / 12 / 24-month** horizons (not just 6m). *(Already prototyped in the horizon widget — merge it in.)* |
| **② Channel** (single-sector RS line inside its band — Pharma) | **Good — keep** | (a) Embed it into **each sector's own section/page**. (b) Also use it for **multi-sector comparison** (overlay several sectors). |
| **③ Thermometer Wall** (19 gauges, sortable) | **Amazing + simple**, but ONE gap | **Add direction/trend** — it shows only the *current* position, not which way the sector is heading. (Tiny ▲▼ arrow today is not enough.) |
| **④ Ridgeline** (joyplot of 19 RS-distributions) | Interesting but **not immediately legible** | Demote to a "lab"/secondary view, or rework so it reads instantly. Not a primary surface as-is. |
| **⑤ Band Clock** (radial bloom + Breathe) | **The "Breathe" animation is "fantabulous" — he wants it** | Keep the radial **Breathe**; it's a keeper. |

### Key product insight (from ②): normalized band ⇒ multi-sector comparison is honest
The band view shows **position-in-band (0–100) + oscillation**, deliberately **NOT** absolute RS values.
So Pharma's real support/resistance ratios differ from IT's, but you can still **overlay multiple
sectors on one normalized channel** and compare *where each sits in its own envelope and how it
oscillates* — because we're not putting numbers on the axis. **Design rule:** the multi-sector
comparison view stays **number-free / normalized** (each sector mapped to its own 0–100 band), so the
comparison is "position & rhythm," not "level."

### Beeswarm correction (①): one lane per sector, not a shared-axis swarm (2026-06-23)
On the shared axis the dots **overlap** (labels collide). Ramana's fix — adopt it: give **each sector
its own horizontal lane (row)**. The lane itself identifies the sector (label at left) → zero overlap,
zero ambiguity. **Keep the shared 0–100 x-axis** (support→resistance) so the vertical read still works
(order lanes cheap→rich = a clean staircase of dots). Then draw each sector's **movement on its own
lane**: a hollow "start" marker at its position H months ago → a connecting bar → the filled "today"
dot (a **dumbbell / dot-plot per lane**), colour = RS direction. Play animates the dot along its *own*
lane (no collisions), tracing the real monthly path incl. backtracks. Horizons **6 / 12 / 24m**.
This **supersedes the beeswarm** as the all-sectors overview. Prototyped 2026-06-23.

### Labels: drop the cryptic 4-letter codes (2026-06-23)
The truncations (RLTY, PVTB, CDUR, CMDT, PSUB, HLTH, ENRG…) aren't readable. Use proper short names:
Pharma · Healthcare · Realty · Energy · Pvt Bank · PSU Bank · Cons Durables · Commodities · Metal ·
Media · Defence · Fin Services · Oil & Gas · Infra · Auto · Bank · FMCG · IT · Chemicals. Widen the
left label gutter to fit; an analyst should never have to decode a tag.

### Constituent drill-down (2026-06-23) — Ramana wants it, and it's the natural recursion
Click a sector lane → the **same band chart** re-renders for that index's **constituent stocks** (each
stock's own support↔resistance position, journey, magnet, verdict). Breadcrumb back to sectors. This is
the zoom the whole system is built for:
- **The data already exists:** `stock_rs` computes BOTH `rs_vs_broad` (stock vs Nifty 500) and
  `rs_vs_sector` (stock vs its sector index); `stock_index_membership` gives constituents; `/dash/rrg?idx=`
  already does an RRG constituent drill — this is the band analogue.
- **Benchmark toggle (the key choice):** "vs Nifty 500" (default — same axis as the sector view, directly
  comparable) ⇄ "vs <sector>" (which names are cheap/rich *within* their own sector — the stock-selection
  lens). Offer both; default broad for consistency.
- One more zoom: clicking a *stock* opens its full single-stock Channel (§6 image-2) / the stock page.
- Recursive surface: sectors-band → constituents-band → stock Channel. Same grammar at every level.

> Status: review IN PROGRESS — appending as Ramana continues. Build still GATED.

---

## 12. Page placement & integration plan (2026-06-23 — "plan these on the respective appropriate page")

**Doctrine:** new surface lives in a NEW module `src/web/rsband_view.py`, mounted via a one-liner in
`main.py` exactly like `rrg_view` / `rotation_view`. Existing pages get **additive embeds only**. Sacred
pages (`/dash/ratio`, `/dash/rrg`, `/dash/compare`, `/dash/mep`, `/dash/rotation`) are **never rerouted**
([[build-additive-never-replace]]). All reads are ₹0 off the §7 nightly columns.

### New module + route
`src/web/rsband_view.py` owns three renderers (pure reads):
- `render_band_lanes(idx=None, den="Nifty 500", horizon=12)` — the **lane dossier**. `idx=None` → all 19
  sectors; `idx="Nifty Pharma"` → that index's **constituents**. Owns the scrubber + 6/12/24 horizon +
  Play + the regime/magnet/verdict per lane.
- `render_band_channel(num, den="Nifty 500")` — the **single-series Channel** (line inside its band +
  rails + POC + verdict gauge). Reused unchanged for a **sector** or a **stock** (just a different num).
- `render_band_clock(den)` — the radial **Breathe** overview (secondary/atmospheric).

New route **`/dash/rsband`** (one-liner mount): `?` = all-sector lanes · `?idx=` = constituents ·
`?den=` = benchmark toggle (Nifty 500 ⇄ sector). Mirrors `/dash/rrg?idx=`.

### Placement per page
| Surface | Page / route (file) | Add / new | What lands |
|---|---|---|---|
| **Lane dossier** (hero, all 19) | `/dash/sectors` (`cockpit.render_sectors` :2173) | ADD section | the headline of the Sectors page — scrubber + horizon + Play |
| **Thermometer column** | `/dash/sectors` table + `/dash/screener` | ADD column | slim `rs_band_pct` mercury + number in the wide table (data-first) |
| **Band Clock (Breathe)** | `/dash/sectors` ("Clock" toggle) + Home glance | ADD | the radial Breathe he loved; froth-at-a-glance |
| **Single-sector Channel** | `/dash/index?idx=` (`cockpit.render_index_detail` :955) | ADD panel | the sector's RS line in its band + verdict, on its own detail page |
| **Band-rails overlay** | `/dash/ratio` (SACRED) | ADD opt-in overlay | support/resistance/POC rails drawn onto the existing ratio chart — toggle, never default |
| **Constituents band** | `/dash/index?idx=` → `/dash/rsband?idx=` | NEW (drill) | click sector → constituent lanes (vs Nifty 500 ⇄ vs sector) |
| **Single-stock Channel** | `/dash/stock` (`cockpit.py` :640) | ADD panel | the deepest zoom: one stock's RS band + verdict |
| **Compact band strip** | Home (`cockpit.render_home` :551) | ADD strip | top cheap / rich / fresh breakouts → links into `/dash/rsband` |

### The drill path (one grammar, three depths)
`Home` strip → **`/dash/sectors`** lanes → click a sector → **`/dash/index?idx=`** (sector Channel +
constituents band) → click a stock → **`/dash/stock`** (stock Channel). Same chart at every level; the
scrubber / horizon / Play are shared controls. The §4b "fresh breakout/breakdown" events also feed the
Home strip and a regime banner.

### Build order (each stage verifiable + PROJECT_STATE-synced in the same commit; GATED on go)
0. **`rsband.py` regime gate + history floor** — safety FIRST (self-test: must not print "cheap, fade"
   on Defence/Media). 1. **Nightly band columns** (§7) via `ensure_columns` + one-time VPS backfill.
   2. **Read API** (`band_all`, `band_one`, `band_constituents`, `band_fused`). 3. **`rsband_view.py`
   + `/dash/rsband`**, then the additive embeds — one page per commit, verify all `/dash/*` 200 (zero
   regression), CRLF-checked scp deploy ([[vps-deploy-reality]]).
