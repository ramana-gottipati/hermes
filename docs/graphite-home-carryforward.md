# Graphite Home — carry-forward & takeover (2026-07-24 WRAP)

**Lifecycle: TRANSIENT** — retire when the Graphite Home cutover completes and folds into
`PROJECT_STATE.md` §Decision log + `docs/redesign-coordination.md`. This is the working handoff +
the next-session takeover prompt.

## 0. Boot (every session, no exceptions)
`CLAUDE.md` → THIS file → `docs/redesign-coordination.md`. Sessions run AUTONOMOUSLY (Guardrail #0):
build agreed/converged plans, commit to main, deploy verified gate-passing additive changes; surface
first ONLY for paid spend / deleting others' work / DB-destructive / publishing beyond the VPS.
Deploy recipe in §6. The in-app Browser pane is DOWN — verify HTML/gates/data on the box, hand the
owner a `?v=N` link for pixels.

---

## 1. Where it stands — LIVE (`https://srv1704897.hstgr.cloud/dash/home?v=N`)

The Graphite home is the isolated, opt-in from-scratch v3 dashboard (`src/web/home/` package, route
`/dash/home`, cookie `pvg`, scoped `:root[data-ui-g]`/`.g-*`, one additive `v2_surfaces._ROUTER_SPECS`
mount line). Classic site + old `/dash/preview` byte-untouched; isolation + read-contract gates green;
full suite **844 pass** (only the pre-existing research-lane `test_rule_lab` red, not ours).

**Layout = SCROLL-STACK** (everything visible; you promote a featured card, never hide the rest):
- **Top chrome:** brand · PREVIEW · **Free ⇄ Pro tier switch** · ◑ Theme · **Classic site** dropdown
  (the WHOLE classic site, ~60 lenses generated from `lens_registry`, one-way).
- **Selectable ticker** (feed picker: indices · watchlist · portfolio · model · movers).
- **Regime one-liner** (calibrated market read).
- **MAIN:** FEATURED card (Watchlist / Portfolio / Index chooser, ★ default, bounded internal scroll
  to 50 names) → **Market map** (squarified treemap, sector labels + rich hover) → **Market-pulse
  deck** (mood gauge · breadth today · breadth-trend · delivery conviction · accumulation · new-52w ·
  dispersion · India VIX · sector heat, click-to-expand) → **Today's conviction** ("N cleared all 3
  pillars") → **What changed** → **News**.
- **RAIL:** FII/DII · Filings & ownership · Going-ex · Results · delivery drawer · toggle. ⋮ pin/collapse/hide.
- **Regime band** (below the today-core): **RRG rotation map** (weekly tail ~8wk, tapered comet, bold
  today-line, hover/click-to-isolate) + **Breadth two-gauge** read (Stocks rising vs Backed by real
  delivery + gap; Pro adds the reference block).
- **Floating Pat** (alive, response-calibrated: terse title + detail-on-demand; typed box classifies/deep-links).

**Data honesty:** every zone marks itself `sample` on demo; only genuinely-empty zones show demo. Real
data flows on the box (heatmap 140 tiles, RRG 12 sectors, conviction/filings/pulse all real).

**Perf:** warm page load ~90ms. Cold (first hit after restart/nightly) ~4-8s because
`conviction_now` runs the ~3.9s canonical `stock_rs.conviction_shortlist` — CACHED BY DATE, warmed by
the post-deploy verify-curl. If cold ever bites the owner → lazy-load the below-fold heavy blocks.

**This session also shipped (non-home):** Pat + Telegram (`src/assistant/chat.py`
`HERMES_SYSTEM_PROMPT`) response-format calibration (crisp-by-default / detail-on-demand).

**⚠ Cross-lane:** `a23b380 feat(markets): /dash/self-history` (NOT this lane) — a new lens ranking
every metric vs each stock's OWN 3-year past. This IS the reference-point principle at the stock level
→ the Pro reference layer (§2/§3) should ALIGN with / reuse it, not duplicate.

---

## 2. The FREE / PRO / PRO-ADS tiering plan (owner-approved structure; PRO-ADS needs one clarification)

**The principle (owner, binding):** *a number in isolation is useless — the reference point is the
premium.* Free gives the number; Pro tells you whether it MATTERS (normal/unusual, which way,
better/worse than before).

- **FREE** = a complete, honest glance. Every number, the map, your watchlist, today's reads. **Never
  crippled** — a real page, not a teaser.
- **PRO** (subscription) = the **REFERENCE LAYER** + depth:
  - a consistent **reference chip** on every Free number: `82nd pct ↑ · typical 52%` (one grammar
    everywhere). The breadth-gap `PRO` block is already the richer version of this.
  - drill-downs, full history/universe, portfolio-aware analytics, and the **Markets journeys**
    (6/12/24-month RRG on the new Markets page).
  - **go DEEPER** (owner, this wrap): e.g. FII/DII — day → streak → 5-day cumulative → per-participant
    (FII cash vs FII F&O vs DII) → percentile-vs-history. "add more detail if necessary."
- **PRO-ADS** = the **upsell/teaser layer** — how Pro is advertised to FREE users. ⚠ **CONFIRM WITH
  OWNER:** "Pro-Ads" = a *locked preview* of the Pro depth shown to free users (blurred/partial + an
  "Unlock with Pro" CTA) to drive upgrades — vs the alt reading "Pro adds" = simply "what Pro adds."
  Owner: "particularly to the pro ads … go a little deeper, like FII/DII in flows, add more detail."
  → I read this as: **the free-tier teaser should show MORE of what they're missing** (a compelling
  locked FII/DII-deep panel), not hide it entirely.
  - **Mechanism note:** today `.pro-more` is `display:none` in Free. Pro-Ads needs a THIRD state — in
    Free, show a `.pro-more` as a LOCKED TEASER (partial/blurred + CTA); in Pro, the full block. Add a
    `.pro-ad` variant + CSS lock/blur + a small "PRO" CTA.

---

## 3. The component Free / Pro outline (owner LOVED it — this is the agreed split)

Consistent pattern: in Pro, every Free number gains a **reference chip** (`Npct · typical X · ↑/↓`).

| Component | FREE | PRO adds (reference + depth) |
|---|---|---|
| Ticker feed | values + day move | custom baskets; "vs 20-DMA" per chip |
| Regime one-liner | mood + breadth/delivery/200-DMA + a watch | percentiles + streaks (breadth pct, FII selling day-N, mood streak) |
| Featured · Watchlist | day move · RS phase · delivery | per-name reference (vs own avg deliv, RS-rank change), **add-date**, alerts, "which of yours are unusual today" |
| Featured · Portfolio | holdings · day P&L · weight · since-entry | day-P&L **attribution**, sector exposure/concentration, risk |
| Featured · Index | level + move + short traj | 1M/3M returns, dist to 200-DMA, full journey |
| **Pulse deck (each tile)** | the number | **the reference:** percentile · typical · trend — mood/breadth/delivery/accumulation/52w/dispersion/sector-heat/VIX (all computable from `market_internals_daily`/`index_signals` history) |
| Today's conviction | count + names + "N cleared" | "2 vs typical 5-8"; per-name pillar values + entry gap; hit-rate history |
| What changed | count-band + rows | "18 vs 5-day avg 11"; magnitude rank; **yours first** |
| FII/DII | today's net | **streak · 5-day cumulative · percentile · per-participant (cash/F&O, FII/DII)** — the "go deeper" ask |
| Filings & ownership | recent events | "3 promoter buys = above typical"; filter to holdings; deeper SAST/pledge |
| Calendars | agenda | flag holdings; high-impact results; historical reaction |
| Delivery drawer | today's leaders | full leaderboard; each name vs own history |
| Regime · RRG | short recent rotation | 6/12/24-mo journeys + per-sector detail (Markets page) |
| Regime · Breadth gap | two bars + gap | typical gap · percentile · trend — **DONE ✓** (the demonstrator) |
| Market map | map + labels + hover | **colour-by-delivery** mode; full universe (not just top 140); "is this move unusual for this stock?" |
| Floating Pat | descriptive answers | portfolio-aware, symbol-specific depth |

**Build priority (agreed):** (1) reference chip + Pulse-deck percentiles [proves the pattern across 8
tiles]; (2) FII/DII streak+cumulative+per-participant; (3) Featured Watchlist per-name reference +
Portfolio P&L attribution; (4) the Markets rotation page (RRG journeys).

---

## 4. Standing corrections — BINDING (violate none)
1. Classic site FROZEN (byte-identical). New experience FROM SCRATCH (no legacy palette; carry only
   doctrine + blue-up/grey-down candles). [[ramana-working-principles]]
2. **Plan-first, study reference products, present, build on go.** For genuine forks, run the
   counter-option and give the VERDICT before building — esp. on "any better way?" (§4 sharpened).
3. Fixed-size boxes that scroll INTERNALLY — never a flat endless page.
4. Generate demo when a live read is empty, but keep the real-vs-demo line HONEST (sample badge).
5. Crisp by default; detail on demand; calibrate format to the question.
6. Plain-English, clickable symbols, every number links to source, descriptive-only fences.
7. **Argue back, no sycophancy.** He wants the spine + the honest verdict.
8. **A number in isolation is useless — the reference is the premium** (the §2 principle; NEW, binding).
9. Verify on the box (HTML/gates/data); pixels via owner (`?v=N` link). Browser pane DOWN.

---

## 5. OPEN — the queue (prioritized for the next session)

**A. The Pro reference layer — ✅ DONE + DEPLOYED (2026-07-24, commits `7c62e64`, `705c1ed`):**
- A1. ✅ `components.ref_chip` (the ONE grammar: `Npct · band · typ X · ↑/↓`, Pro-only) on the **5
  pulse tiles that earn an honest reference** — breadth/delivery/accumulation/dispersion
  (`reads.internals_reference`, 22y `market_internals_daily`) + India VIX (`reads.vix_reference`,
  ~12y). VERDICT: NOT "8 tiles" — Mood (no stored history), New-52w (per-date COUNT over 5.9M-row
  `stock_signals` = too heavy), Sector-heat (already relative) get NO fabricated percentile. Aligns
  with `/dash/self-history` (descriptive-only, percentile-vs-own-past).
- A2. ✅ `reads.fii_dii_deep` + `components._flows_deep_html` (Pro flows block): per participant —
  gross buy/sell · buy/sell **streak** · **5-day cumulative** · **1-month-range** position. VERDICT:
  store has ONLY `FII/FPI` + `DII` aggregate over ~24 sessions — **no cash-vs-F&O split exists**, so
  none fabricated (disclosed); "percentile" honestly framed as a range position (24 pts too thin).
- A3. ✅ `components._folio_attrib` (Pro portfolio): top contributor/detractor + concentration,
  attribution = **weight × day move (bps of book)** (real + demo, no extra query). Watchlist per-name
  self-relative depth LEFT to `/dash/self-history` (importing its web-view engine breaks the home
  isolation gate) — reached via per-name `sym` links.

**B. Owner corrections — ✅ B1/B2 DONE + DEPLOYED; B3 still deferred:**
- B1. ✅ Watchlist add-date — `reads.watchlist_rows` carries `date_added`; Pro per-name line
  `added 19 Jun 26 · RS #23 · ◆ your standout today` (standout = biggest absolute mover among yours).
- B2. ✅ The ADD affordance (the home was READ-ONLY) — home-owned `POST /dash/home/watch/add` +
  `reads.watch_add` (validate vs `bhavcopy_rows` EQ/BE · dedupe · insert canonical `stocks_in_play`
  watch tier · date_added native · success/error **toast**; plain HTML form, injection-safe). VERDICT:
  home-owned POST, NOT classic `/dash/track` (isolation). Box-verified add→appear→cleanup round-trip.
- B3. **"When a name is added — when is its NEXT trigger?"** — STILL DEFERRED (owner). The next
  expected event/signal (results date · ex-date · cadence-overdue). Raise; don't build yet.

**C. PRO-ADS layer — ✅ DONE + DEPLOYED (owner CONFIRMED the locked-teaser reading, commit `91e20d0`):**
`components.pro_teaser` = the third `.g-proad` state (Free: blurred real Pro block + 'Unlock with Pro'
CTA button that flips to Pro in place; two modes — `advertise=False` clean-in-Pro / `advertise=True`
`.free-only`, gone-in-Pro). Applied v1 to (1) the **FII/DII deep block** (owner's example) + (2) a
**pulse-deck reference teaser** (real breadth chip blurred + live-value CTA). `ref_chip(bare=True)`
lets a real chip sit inside a teaser. Free stays complete; only DEPTH is teased. RM-safe (static blur).
DEFERRED: CTA flips the preview tier — no subscription/payment flow yet (a real launch routes to
checkout); MORE teaser spots can be added (currently 2).

**D. The Markets rotation page** (`/dash/home/rotation`, new isolated Graphite page) — ⭐ THE NEXT UNIT.
Full RRG with a 6/12/24-month period selector + the CLUTTER FIX (fixed ~10 dots per tail, period sets
the spacing) + Pro-gated long journeys + per-sector depth. Reached via a "See the full rotation →"
link from the Today RRG. Today RRG defaults to the SHORT view.
- **FEASIBILITY — box-probed 2026-07-24: GO.** `ratio_rows` holds **14 years** per RRG sector
  (2012-02-21 → 2026-07-24, ~3,545 rows each), so 6/12/24-mo journeys are trivially supported — reuse
  the canonical `rrg._rs_ratio_momentum`/`quadrant` (same as `reads.rrg_sectors`) over a longer window.
- **RECOMMENDED clutter-fix (this session's verdict on the fork):** fixed ~10 dots per tail; the period
  selector sets the SPACING between them (6mo → ~2.5-week block-means · 12mo → ~5-week · 24mo →
  ~2.4-month), exactly the block-mean pattern `rrg_sectors` already uses for the weekly tail — just
  parameterise the block size by period. Consistent readable comet at every horizon. (Alt considered:
  show-all-dots-thinned — rejected, denser/noisier at long periods.)
- **SURFACE-PLAYBOOK required (binding):** new isolated route in the home package + a "See the full
  rotation →" link from the Today RRG (default short) + registration/Pat coverage/glossary/education/
  fence per `docs/SURFACE-PLAYBOOK.md`. Keep it `data-ui-g`/`.g-*` isolated; Pro-gate the long journeys.

**E. Heatmap enhancements (offered, owner may want):** colour-by-delivery toggle; full universe;
per-tile "unusual move?" context (Pro).

**F. Cutover (PARKED):** promote `/dash/home` into nav + retire old preview — only after the Graphite
stock page exists (old preview uniquely serves `/dash/preview/stock`).

---

## 6. Deploy recipe (verified all session)
`scp src/web/home/*.py hermes:/opt/hermes/src/web/home/` (new modules — full-scp fine) → on box
`tr -d '\r'` each (NEVER sed) → `.venv/bin/python -m py_compile src/web/home/*.py` → import/hasattr
check of new callees → **writer-safe restart** (`fuser /opt/hermes/data/hermes.db` must show no
FOREIGN writer; hermes-api startup is read-only; NEVER restart ~14:01 UTC bhavcopy) `systemctl restart
hermes-api` → `curl …/dash/home` 200 + structure grep → **the verify-curl warms the conviction cache**
→ hand `?v=N`. The `_ROUTER_SPECS` mount line is deployed (anchored insert; `v2_surfaces.py` co-edited
→ NEVER full-scp it). Chat/Telegram calibration lives in `src/assistant/chat.py` → restart
`hermes-api` AND `hermes-telegram`. See [[vps-deploy-reality]].

---

## 7. AUTONOMOUS NEXT-SESSION TAKEOVER PROMPT (paste to start)

> Resume the **Patearn Graphite Home** (`/dash/home`, LIVE + isolated at
> `https://srv1704897.hstgr.cloud/dash/home?v=N`). Boot: `CLAUDE.md` →
> `docs/graphite-home-carryforward.md` (THIS file) → `docs/redesign-coordination.md`. Run
> autonomously (Guardrail #0); the Browser pane is DOWN so verify HTML/gates/data on the box and hand
> `?v=N` links. Suite baseline **~844** (only `test_rule_lab` red, not ours — deselect it; 821 pass).
>
> **DONE + LIVE (2026-07-24, do NOT rebuild — verify first):** the ENTIRE **Pro reference layer**
> (A1 reference chip on 5 pulse tiles · A2 FII/DII deeper · A3 portfolio attribution), the owner
> corrections (B1 watchlist add-date · B2 the **+ Add** affordance / home-owned `POST
> /dash/home/watch/add`), and the **Pro-Ads** locked-teaser layer (`components.pro_teaser`). Commits
> `7c62e64 · 705c1ed · 91e20d0`. Details + verdicts in §5-A/B/C. `market_internals_daily` staleness
> self-resolved (now current to 07-24).
>
> **THE MISSION THIS SESSION: build the Markets rotation page (§5-D).** A NEW isolated Graphite page
> (`/dash/home/rotation`), full RRG with a 6/12/24-month period selector + the CLUTTER FIX (**fixed
> ~10 dots per tail; the period sets the SPACING** — 6mo ~2.5-wk / 12mo ~5-wk / 24mo ~2.4-mo
> block-means; parameterise the block size `rrg_sectors` already uses) + Pro-gated long journeys +
> per-sector depth. Reached via a "See the full rotation →" link from the Today RRG (which defaults
> SHORT). **Feasibility box-probed: GO** — `ratio_rows` holds 14y per sector (2012→2026). Reuse the
> canonical `rrg._rs_ratio_momentum`/`quadrant`; do NOT re-derive. Land the full **SURFACE-PLAYBOOK**
> checklist (registration · Pat coverage · glossary · education · fence) in the SAME session.
>
> **Then (§5-E/F, if time):** heatmap colour-by-delivery + full-universe + per-tile "unusual?" (Pro);
> cutover (PARKED until a Graphite stock page exists). **DEFERRED (§5-B3):** "when a name is added,
> when is its next trigger?" (results date · ex-date · cadence-overdue) — raise, don't build yet.
>
> Every change: additive, isolated (`data-ui-g`/`.g-*`, no preview/legacy import), DOM-safe,
> reduced-motion-safe, defensive + demo/sample-honest, gate-tested, deployed writer-safe per §6, box-
> verified, `?v=N` to the owner. Keep Free complete (never crippled). Argue back; give the verdict
> before building on any genuine fork. **Multi-session:** a parallel self-history/markets lane commits
> alongside — stage only YOUR hunks (selective patch), never absorb foreign PROJECT_STATE/charter edits.

---

## 8. Session arc (2026-07-24) — what shipped, commit trail

Scroll-stack rebuild (`3d5637d`) · Pat + Telegram calibration (`3b41f73`,`a82330a`) · classic-site
directory (`4f714b6`) · analyst additions regime/conviction/filings (`677203d`) + 4 box-verified data
fixes (`26f95db`,`9a86b1f`,`be8684c`,`43dc8e1`) · conviction legibility (`1e24c1a`) + STRICT decision
(`52acba2`) · **market heatmap** (`04005ee`) + sector enrichment (`3d6ccdb`) + labels/hover (`c12360e`)
· **regime band RRG + breadth** (`7874845`) + weekly tail (`ea1e638`) + taper/isolate (`4dffa90`) ·
conviction perf cache (`cd6dc24`) · **breadth two-gauge** + featured bounded scroll (`a4c9946`) ·
**Free/Pro tier switch** + heatmap colour fix + breadth PRO context (`7aaddc8`). Full arc in
`PROJECT_STATE.md` §Session log (2026-07-24 entries).
