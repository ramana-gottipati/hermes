# Patearn Web-Experience Redesign — THE PLAN (v1, for owner ratification)

> **Lifecycle: TRANSIENT** — retire when: Ramana ratifies or rejects this plan; on ratification the verdict
> table folds into `docs/SURFACE-PLAYBOOK.md` §6 + a PROJECT_STATE Decision-log entry and the build
> program moves to `docs/NEXT-SESSION-CARRYFORWARD.md`; on rejection, fold the reusable inventory
> (§1) into the UX audit doc and delete. Fold into: `PROJECT_STATE.md` §Decision log +
> `docs/SURFACE-PLAYBOOK.md`.

**Status: M0+M1+M2 APPROVED (Ramana, 2026-07-17) and reviewed by both external stakeholders —
Codex `APPROVE-WITH-CHANGES` and Gemini `APPROVE-WITH-CHANGES`; all blocking findings accepted
and dispositioned in `docs/redesign-coordination.md` (the approval + communication record).
M3–M8 remain pending owner approval.**

**Method.** Grounded in a four-way sweep of the real estate on 2026-07-17 (not memory): the live
registry (`src/web/lens_registry.py` L65–338 — 73 Lens records: 71 routed + 2 overlay-only), the
route gate (`tests/test_dash_route_registry.py`), the Pat gate (`tests/test_pat_coverage.py` — 24
DATA / 10 EXPLAIN / 37 NAV), the stock dossier (`src/web/dashboard.py:5904`, 10 tabs), the glossary
(`docs/metrics-glossary.md`, 248 entries), the education layer (`src/web/infographics.py`, 54
adopter files), the strategy verdict ledger (`docs/strategy-ledger.md`, `docs/strategies/README.md`),
and the news/flow/chrome estate (`news_feed.py`, `news_tagging.py`, timers, `ui_tokens.py`,
`left_rail.py`, `v2_surfaces.py`). Each section was examined from five seats: the newcomer, the
PMS/AIF analyst, the mobile visitor, the skeptic, and the owner.

**Standing doctrine this plan obeys (non-negotiable, verified against source):**
- **Additive only** — the S177 revert made this binding: every deliverable below is a NEW module
  behind an opt-in preview toggle; the live default look/behavior is untouched until a separate
  cut-over ratification. Sacred routes (`/dash/ratio`, `/dash/rrg`, `/dash/compare`) and every
  existing page stay live and reachable throughout.
- **Descriptive only** — no action verbs as verdicts; the D142 rule (every "Sharpe" is a
  return/vol ratio) and the failure ledger are load-bearing content, not footnotes.
- **Primary sources only** — every data channel below already exists on NSE/BSE/SEBI/XBRL timers;
  this plan adds **zero new timers and zero always-on compute**.
- **One glossary, one Pat** — the teach system below extends `docs/metrics-glossary.md` + the Pat
  auto-fold contract (`docs/pat-knowledge-contract.md`); nothing forks.

---

## 0. The concept in one paragraph

The estate's problem is not missing content — it is 71 nav destinations, a tab-switched dossier,
and education that lives one click away from the jargon it explains. The redesign is **"Focus +
Rails"**: one Focus column (a stock, a market view, a strategy) with a persistent **News/Flow
rail** and a **Context rail** that travel with it, and a **term-chip layer** that makes every
proprietary word teach itself in place. The 71 lenses collapse (in the new experience only) into
**6 primary destinations and ~20 sub-views**; everything else remains reachable as merged tabs,
related-strip links, or legacy routes. Selling and educating become the same act because the
honesty record — one fundable strategy, sealed forward tests, published falsifications — IS the
sales pitch, rendered as first-class UI.

```
┌────────────────────────────────────────────────────────────────┐
│  Top bar: identity · 6 destinations · search/⌘K · New here?    │
├────────┬──────────────────────────────────┬────────────────────┤
│ Left   │  FOCUS COLUMN                    │ CONTEXT RAIL       │
│ nav    │  (stock dossier / market view /  │ (travels w/ focus: │
│ (rail, │   strategy page — one job at a   │  news for SYM ·    │
│ exists │   time, chips teach in place)    │  results date ·    │
│ today) │                                  │  corp actions ·    │
│        │                                  │  peers · fired     │
│        │                                  │  lenses · seasonal)│
├────────┴──────────────────────────────────┴────────────────────┤
│  NEWS/FLOW DOCK (persistent, channelized, collapsible)         │
│  Wire · Filings · Results · Corp actions · Deals/FII · Alerts  │
└────────────────────────────────────────────────────────────────┘
  ≥1280px: all three columns · 900–1279: context rail → chips/drawer
  <900px: single column, rails become swipeable bottom tabs
```

---

## 1. COMPONENT INVENTORY & VERDICTS

**Verdict vocabulary (additive-safe).** Because nothing is deleted, verdicts describe the NEW
experience only: **KEEP** = a primary destination or named sub-view · **MERGE** = folded into a
canonical parent (tab/toggle/child, the Wolfe fresh⇄open and seasonal `_subnav` precedents) ·
**DEMOTE** = reachable (related strip, parent link, palette) but not in primary nav · **CUT** =
not represented in the new experience (legacy route stays live) · **EXAMINE** = value unproven,
needs a measurement or an owner decision before placement.

### 1a. Markets — 31 routed lenses → 1 destination ("Markets") with 6 sub-views

| Lens (route) | Verdict | Reason + data |
|---|---|---|
| attention `/dash/attention` | **KEEP** | The signal-event bus is THE "what changed" substrate (playbook §6) and Pat DATA flow; becomes the Alerts channel of the News/Flow dock AND a Today board. |
| market-internals | **KEEP** | 22-year breadth — flagship, expert-cited "wow" asset (UX audit §3); Pat DATA. |
| seasonal-tape | **KEEP** | FDR-certified calendar residual; "0-certified IS the finding" — the honesty showpiece. Sub-view of Markets. |
| seasonal-screen · seasonal-divergence | **MERGE → seasonal** | Both served by the same `seasonal_screen_view` module; `_subnav` trio is already the approved pattern — formalize as one Seasonality sub-view with tabs. |
| event-cadence | **MERGE → seasonal/calendar** | Already a dossier embed (`event_cadence_card`); market cut folds into the Seasonality sub-view + the Results channel of the dock. |
| rs-hub | **KEEP** | The praised launcher pattern; becomes the single "Strength" sub-view entry. |
| leaders | **MERGE → rs-hub** | A cut of the same RS columns (`dossier_tab=rs, col=rs` identical to rs-hub in the registry). |
| momentum-scan (+ `/slow` child) | **MERGE → Strength** | The benchmark ranker (gross 28.6% CAGR, NET ~0.09 — ledger); stays a named sub-view inside Strength, its honest numbers on the page. |
| divergence | **MERGE → Strength** | Overlaps `momentum_pane` RS/RSI divergence computation (registry sweep anomaly C) — one divergence rendering, not two. |
| capture-map | **MERGE → Rotation** | Same capture columns render on 3 pages today (audit); `related_strip` already admits it. |
| rrg + rotation | **MERGE → one "Rotation"** | Same quadrant data under two metaphors; S143-d already folded them display-wise (Map⇄Weather toggle) — the new IA makes it structural. |
| rsband | **MERGE → Rotation tab** | Known duplication debt: rsband embeds Lanes/Clock/RRG as tabs while cycle-clock and rrg exist standalone (playbook §6 warning). Rotation becomes the ONE canonical parent. |
| cycle-clock | **MERGE → Rotation** | Open S-B1 item 3 — this plan executes it in the new IA. |
| sector-momentum | **MERGE → Sectors** | "Sector drill" is a cut of sector RS; lives as a tab of the Sectors sub-view. |
| sectors | **KEEP** | Canonical Sectors sub-view — absorbs sector-economics + sector-momentum as tabs. |
| sector-economics | **MERGE → sectors** | Declared siblings that never link (audit P1); one Sectors page, two tabs (RS · Economics). |
| wire | **KEEP** | Becomes the primary source of the persistent News dock; also keeps a full-page view. |
| participants | **KEEP** | FII/DII positioning (Pat DATA); page + Deals/FII dock channel. |
| actions | **KEEP** (page demoted to channel-first) | Forward ex-date calendar (NSE, daily 02:20 timer); primarily a dock channel, full page reachable from it. |
| results-reactions | **KEEP** | PEAD event lens — descriptive-only with its falsification numbers (return/vol 0.10 vs 0.85 bench) shown; feeds the Results channel. |
| surveillance | **KEEP** (absorbs band-locks) | ASM/GSM + price-band state are one job for the user: "is the exchange flagging this?" One "Exchange flags" sub-view, two tabs. |
| band-locks | **MERGE → surveillance** | Same job, sister data. |
| move-anatomy | **DEMOTE** | Methodology-flavored (audit flagged the misgrouping, D115); link from internals + Learn; not primary nav. |
| buyback-calc | **DEMOTE** | A calculator, not a lens (audit: misplaced in Events & flow); reachable from actions + dossier. |
| harmonic-scan | **DEMOTE** | Descriptive pattern scanner, backtest-gated, niche; reachable from Patterns (Wolfe) related strip + palette. |
| wolfe-scan | **KEEP** | The one patterns surface with a REAL recorded selection edge (BULL residual α +5.07, CI excludes 0) and the estate's best trust table (12 server filters, real CSV, 596 exclusions disclosed). Canonical "Patterns" sub-view with fresh⇄open⇄trades tabs. |
| early-signals | **EXAMINE** | No recorded verdict found in the ledger sweep; the season-trigger program killed 5 sibling lenses via placebo in week 1. Before carrying it: run the same placebo battery or demote pending evidence. |
| markets (Overview) | **MERGE → Today** | Its job (orientation) is the new Today destination's job. |
| compare | **KEEP** | Sacred-adjacent tool, Pat DATA flow; reachable from every dossier + palette. |

### 1b. Screener — 5 lenses → 1 destination ("Stocks")

| Lens | Verdict | Reason |
|---|---|---|
| screen2 (Screen+) | **KEEP** | The default screener. Carried WITH its known debt: 2.3MB page, client-side-only export, no URL-addressable filter state (audit S-G#1) — the v3 rebuild fixes state-in-URL + server CSV as part of the module, not as an edit to the live page. |
| screener (classic) | **CUT** | Two full screeners over the same Pat `fundamentals` flow is pure duplication (registry anomaly K). Legacy route stays live for bookmarks. |
| themes | **KEEP** | Baskets feed dossier theme tags; entry point for non-ticker discovery. |
| tags-review | **DEMOTE (owner-only)** | An owner workflow, not a visitor surface. |
| workbench | **EXAMINE** | NAV-only coverage, no distinct data claim found. Ask what job it does (playbook decision-tree step 6) before carrying it. |

### 1c. Strategies — 18 lenses → 1 destination with a library + evidence spine

| Lens | Verdict | Reason + data |
|---|---|---|
| strategist | **KEEP** | The landing/launcher (Hub already merged in, registry selftest asserts it). |
| model-portfolios | **KEEP** | The 4 engine-locked books — where the estate's ONLY fundable result (LOWVOL_MOM qtr large-cap: net return/vol 1.19 @₹75cr, halves 1.20/1.42, S163 #602) lives. This is the analyst's proof page. |
| sector-rotation | **KEEP** | V21 book: 16.6% / −40.8% / α+6.3%, first to beat the bench both halves (0.87 vs 0.89/0.86 — shown honestly as *near* the bar, not over it); D138 scope gap ("picks SECTORS not stocks") stated above the headline. |
| factor-league + classics | **MERGE → one "Strategy library"** | Explicitly declared siblings; one library table with origin filters (🧑 RAMANA / 🏠 HOUSE / 📚 CLASSIC — the binding taxonomy from `docs/strategies/origins.md`). |
| stocks (Positioning·DVPT) | **KEEP** | The Ramana-origin flagship descriptive lens (dossier tab + screener col + overlay). |
| stealth | **MERGE → stocks** | Registry-admitted same renderer (`view=='stealth'`); becomes a toggle. |
| mep | **KEEP** | Accum/Distrib descriptive lens; D62 descriptor-only verdict on the page chip. |
| conviction | **KEEP page / EXAMINE metric** | The page is a useful shortlist; the METRIC is "a sorting heuristic, not a validated model" (glossary L63) — the chip must say exactly that (see §2). Owner decision: keep the name "Conviction" or rename to something less verdict-flavored ("Composite rank"). |
| concalls (Credibility) | **KEEP** (absorbs `/dash/credibility`) | CCI descriptive/veto layer; the orphaned fingerprint page becomes its child tab (audit-converged disposition). |
| growth | **KEEP** | Fundamentals lens over XBRL-migration-era data. |
| insider · ratings · sast · shp | **MERGE → one "Ownership & filings" hub** | Four nav lenses over one filings pipeline and ONE Pat `filings` flow (registry anomaly H). One hub, four tabs, shared idioms — and it resolves the audit's open placement question (S-B1 item 6). |
| cpr | **DEMOTE** | Structure/CPR lives where it's used — the dossier chart (owned by `cpr_overlay.py`); standalone page leaves primary nav. |
| launchpad | **KEEP** (absorbs launchpad-track) | Validated SCREEN (no fundable edge net of cost — stated on-page); its evidence page becomes the "evidence" tab. |
| launchpad-track | **MERGE → launchpad** | It is the evidence tab. |

### 1d. Tracker — 6 lenses → carried as-is (1 destination)

All six **KEEP** under the existing demo-book gate (`tracker_gate.py` — anonymous sees the demo
book; owner unlocks). One **MERGE-flavored fix**: `model-books` (Tracker) vs `model-portfolios`
(Strategies) is an admitted overlap (the NAV rationale itself says the numbers are "already
covered by the model_portfolios data flow") — in v3, model-books becomes a *view of* the
Strategies books ("follow a book into your tracker"), one data source, two doors.

### 1e. Trust — 11 lenses → reframed as "Proof" (the moat, not an appendix)

| Lens | Verdict | Reason |
|---|---|---|
| replay-any-date | **KEEP — flagship** | PIT replay with raw entitled /v1 envelopes + repro curls — the single most differentiating trust asset (expert walk). Gets a Today-page card, not just a nav row. |
| testing (Strategy validation) | **KEEP — flagship** | The published falsification record; with the demo framing sentence ("we publish failures so descriptive context is not mistaken for alpha") the skeptic's landing page. |
| spec-sheets | **KEEP** | Pre-registered SHA-256 gates — proof of prereg discipline. |
| rule-lab | **KEEP** | The evidence gauntlet that produced the LOWVOL_MOM #602 verdict; interactive proof. |
| coverage | **KEEP** | Honest funnels. |
| glossary · reading-guide · strategy-ref · pat | **KEEP** | The education spine §2 builds on. strategy-ref keeps its public-intro treatment (P0-5 fix). |
| evidence-pack | **EXAMINE** | 3.7s load (audit measurement) and unclear division of labor vs spec-sheets + testing. Measure usage; likely MERGE into testing as a download. |
| inbox | **DEMOTE (owner-only)** | Review workflow, owner-gated; not visitor nav. |

### 1f. Out-of-registry routes + overlays + dossier

- `/dash/replay` → **CUT** (superseded by replay-any-date; already gate-exempt). `/dash/strategies`
  (retired Hub) → **CUT** (stays 200-alive, de-linked, as today). `/dash/momentum` → **MERGE**
  (declared child of the Strength family). `/dash/news` → **MERGE** (per-symbol timeline = the
  dossier News context, exactly the audit-converged fix). `/dash/ratio` → **KEEP, sacred,
  untouched** (palette + dossier deep-link). `/dash/_ui` → internal, unchanged.
- Overlay-only lenses `wolfe`, `harmonic` → **KEEP** (chart-control overlays are the correct shape;
  the new dossier keeps the `window.__wfpc`/`[data-ptf]` seams so committed overlays keep binding).
- **The stock dossier's 10 tabs** (Price · Positioning · MEP · RS · Quality · CPR · Credibility ·
  News · Seasonal · F&O): all content **KEEPS**, but the *tab-switched* architecture is the thing
  §3 redesigns — News, results timing, corp actions, and peers move from buried tabs into the
  always-visible Context rail; the analytical tabs (Positioning/MEP/RS/Quality/CPR/CCI) stay as
  Focus-column sections. Nothing is lost; co-presentation replaces excavation.

### 1g. Summary counts

Of 71 routed lenses: **KEEP 37 · MERGE 24 · DEMOTE 6 · CUT 1 · EXAMINE 3** (early-signals,
workbench, evidence-pack — each with a named check before placement), plus the Conviction *metric*
flagged EXAMINE independently of its page. Primary nav shrinks from 71 items to **6 destinations**
(Today · Markets · Stocks · Strategies · Tracker · Proof) with ~20 named sub-views. "Required" =
the 37 KEEPs; "unnecessary" (in the new experience) = the 1 CUT + several of the merges' duplicate
renderings; "needs a closer look" = the 3 EXAMINEs + the Conviction metric.

---

## 2. THE SELF-EXPLAINING METRIC SYSTEM (the term-chip spec)

**The component.** A `term-chip` (new module, e.g. `src/web/term_chip.py` + CSS in the v3 theme):
inline element rendered as **plain-English label first, code second** — e.g. "Delivery size
·DVPT·" — with a dotted underline that is the site-wide affordance for "this teaches itself."
Three levels:

1. **Glance** — the label itself. Plain words lead; the proprietary code is a small suffix badge.
2. **Hover/tap** — one-line meaning (the first sentence of the glossary entry; zero-JS CSS
   popover, the existing `glossary.gloss()` mechanic reused).
3. **Expand (click / long-press)** — the **teach card**: *What · How computed · Measured against ·
   How to read* (these four already exist as the `docs/metrics-glossary.md` entry convention) +
   three NEW fields: ***Verdict*** (the recorded epistemic status, with numbers), ***How it could
   improve*** (what would change the READING — never a promise of returns), ***Origin*** (🧑/🏠/📚
   badge per `docs/strategies/origins.md`). Card footer: link to the glossary family, the
   `docs/strategies/` methodology page where one exists, and "Ask Pat about this."

**No fork.** Definitions stay single-sourced in `docs/metrics-glossary.md` (248 entries) — the
chip module resolves through the public `glossary.lookup()` API (entries expose
name/family/body/sources; Codex review corrected the earlier `_INDEX` phrasing — `_INDEX` maps
normalized keys to offsets and is private). Labels that don't resolve verbatim (`MEP`, `CCI`,
`pt14`, `×Power` variants) go through an explicit alias map in the chip module. The
three new fields ship as a **new sidecar section per entry inside the same md file** (`*Verdict:*`
and `*Could improve:*` sub-lines, parsed by the NEW chip module only — `glossary.py` is not
edited and degrades gracefully by ignoring lines it doesn't parse). Because the md is THE
designed growth path (adding entries auto-teaches Pat via `_merge_web()`), extending entries is
additive by doctrine; it is also the one touch of an existing file this plan proposes, called out
for explicit owner approval (fallback: a sidecar `docs/metric-verdicts.md`, same keys — zero
existing-file touches, slightly weaker single-sourcing).

**The spec per proprietary term** (verdict lines below are the recorded numbers — the skeptic's
seat wrote this table):

| Term | Plain label (leads) | One-liner | Honest "how it could improve" |
|---|---|---|---|
| **DVPT** | Delivery size | Average ₹-size of a *delivered* trade today — bigger = larger hands. | "A rising ×Power while price holds its key-price band changes the *read* to heavier accumulation. Note: as a stock-picking signal this was tested and refuted (the calibration passed only trade-size, δ+0.33; delivery-surge failed OOS both directions 2012–26) — it describes, it does not predict." |
| **×Power** | Intensity (vs own history) | Today's delivery size ÷ the stock's own 1–12-month institutional peak-day average. | "Reads stronger as it climbs above 1× — always vs the stock's OWN history, never the market's. A 1.6× on an illiquid name is noise; check median traded value first." |
| **Key price + gap** | Where big money bought | Value-weighted average price of the power days; gap = today's close vs that level. | "🎯 = inside the −1%…+5% band of that price. The read sharpens when multiple horizons (1M/3M/6M/12M) agree; it says where money transacted, not what happens next." |
| **MEP** | Accumulation / Distribution | Signed composite: is the tape absorbing (+) or distributing (−) vs the stock's own norm? | "A flip in sign is the event worth noticing. Tested as an alpha source and failed (Deflated ratio 0.45→0.36 when added) — it is a descriptor; we will not re-test it as alpha." |
| **RS band %** | Strength vs own range | Today's relative strength as a percentile of its own 3-year range: 0 = at RS support, 100 = at RS resistance. | "Read WITH the regime: 'cheap' (low band) on a de-rating trend is a trap, not a bargain. Improves as a read when the band turns up from <20 with the rotation phase confirming." |
| **RRG / Rotation phase** | Rotation map | Which quadrant a sector/stock's strength-and-momentum sits in (leading/weakening/lagging/improving). | "The SHAPE of the sweep matters more than the quadrant label; a hooked path back toward 'improving' is the classic read. Descriptive suite — never return-tested as alpha." |
| **CCI** | Management credibility | Did management's concall promises settle true? 0–100 + tier A+…D, point-in-time. | "The tier improves only as new promises settle — it moves slowly by design. Tested as a return factor and falsified (leak-free Gate B FAIL; content axis placebo-killed: +1.90% observed vs +3.66% null p95). Use as a veto/context, never a ranker." |
| **Conviction** | Composite rank | One 0–100 sort key blending positioning strength and RS rank. | "This is a sorting heuristic, NOT a validated model — the blend is a reasonable default that has never been backtested. Treat the ordering as a shortlist, and check the underlying pillars the chip links to." |
| **pt14 / ns_base** | Quality score (14 patterns) | Rule-based durability score 0–100 (pws ÷ 582 × 100); financials labeled not-applicable. | "Improves as patterns move from unverified (×0.70 haircut) to verified. Quality alone does not rank returns (standalone: ~0.0% alpha, fails both halves) — it is a filter and a veto." |
| **CPR** | Pivot structure | Prior period's pivot band (Pivot/BC/TC) from split-adjusted H/L/C. | "A 📚 classic, shown for structure context on the chart. Narrow bands mark compression; the read is about levels, not direction." |
| **Seasonal cert** | Calendar habit (certified) | The stock's own calendar residual after the market is stripped — colored ONLY if it survives two placebo nulls + FDR + 15y + OOS stability. | "Most cells grey out — that IS the finding. ⚪ means the CI includes coin-flip. A cell improves to colored only by surviving more history; nothing here is tradeable net of cost and the page says so." |
| **Wolfe §B score** | Pattern strength (0–27) | Rule-scored quality of a detected 5-point wedge (D111-ratified components). | "BULL patterns carry a real recorded selection edge (median +4.4% net, residual α+5.07); BEAR fails the OOS bar and says so on the card. The score grades the *setup's shape*, not an instruction." |
| **Attention / signal event** | What changed | A state-change on the signal bus (severity-gated), e.g. an accumulation flip. | "Humanized wording (S-A debt): 'accumulation flipped to strong distribution', never 'DISTRIB → STRONG_DISTRIB'. More events ≠ better — the severity gate exists to keep this rail quiet." |
| **Launchpad** | Coiled-spring screen | Momentum + contracting-volatility screen (validated as a screen; no fundable edge net of cost). | "A candidate list, not a strategy: recorded expectancy +2.07%/trade, lightly invested. Improves as a read when volatility contraction deepens with delivery holding." |
| **return/vol** | Return ÷ volatility | Every ratio on this site is return/vol (no risk-free subtracted) — comparable internally, ~1.7× a textbook Sharpe. | "This label is the honesty: relative comparisons hold exactly; absolute levels read high vs textbooks. The gate `test_retvol_label_gate.py` keeps the word 'Sharpe' out." |

**Fired-lens chips.** On the dossier, each lens that currently flags the symbol (DVPT trigger,
MEP flip, RS phase, seasonal cell, Wolfe hit…) renders as a chip in the Context rail — same
three-level behavior, deep-linking to the lens with the symbol pre-filtered. This is how the 24
MERGEd lenses stay one tap away without owning nav slots.

**Pat integration.** Every teach card's "Ask Pat" pre-fills the explain flow (`/dash/pat?q=`),
symbol-aware when opened from a dossier (Gemini improvement #4); because the chip reads the same
md the Pat glossary auto-folds from, chip↔Pat share one source — and a DEDICATED test
(`tests/test_v3_isolation.py`) proves each seed chip round-trips chip → `glossary.lookup()` →
Pat explain (Codex blocking #4 corrected the earlier claim that existing gates already covered
this — they gate lenses/columns, not chips).

---

## 3. THE LAYOUT SYSTEM

**The app frame** (see diagram in §0): a new shell module (`shell_v3.py`) rendering three regions
plus a dock. It reuses `ui_tokens` variables via a NEW token layer (§5) and does NOT wrap or edit
`shell_skin`/`ui_kit` — v3 pages are native to the new shell; old pages never change.

**The persistent News/Flow dock.** One collapsible region, channelized over feeds that ALL exist
today with timers (zero new compute):

| Channel | Source (exists today) | Cadence |
|---|---|---|
| Wire | `sent_news` + `news_symbol_tags` via `news_view.render_market_wire()` | 2×/day (03:30, 11:30 UTC) |
| Filings | `insider_events` · ratings · `sast_events` · `shareholding_xbrl` | daily timers (15:30–16:45) |
| Results | `results_calendar` (NSE, D-01 forward 30d) + results-reactions | daily 02:00 / 18:00 |
| Corp actions | `corp_actions` forward ex-dates | daily 02:20 |
| Deals / FII | `deals.py` bulk/block + `participant_oi` | 2×/day (14:30, 16:30) |
| Alerts | `signal_events` bus (severity-gated) | continuous (existing) |

Filters: **All · Focus symbol · Watchlist**, plus per-channel toggles; state in URL query params
(playbook 8b). Every headline row: source + timestamp + symbol chips (`sym` links). Copyright
discipline: titles + source + link only (the existing wire treatment). The dock is the SAME
component on every v3 page — market view or stock view — which is what makes "stocks + news on
one screen" structural rather than a special page.

**The stock Focus screen (the dossier, recomposed).** Focus column: search + identity strip +
the 8-tile verdict strip (each tile becomes a term-chip) + the chart with its four-family rail
(reusing `stock_chart.py`'s snippet contract and overlay seams) + the analytical sections
(Positioning / MEP / RS / Quality / CPR / Credibility) as in-page sections with sticky
section-nav — content identical to today's tabs. Context rail (always visible ≥1280px):
**News timeline for the symbol** (`render_stock_timeline(sym)` — exists) · **next results date**
(`results_calendar`) + last-concall CCI chip · **upcoming corp actions** for the symbol ·
**peers** (the existing `sector_peers` 12-cap read, upgraded from a hidden "+" rail to a visible
card with 1-tap compare) · **fired lenses** (chips, §2) · **seasonal cadence** card. The audit's
core dossier finding — "tab-switched, not composited" — is resolved by moving *context* to the
rail and keeping *analysis* in the column.

**Responsive rules (the fit guarantee).**
- Breakpoints: ≥1280 three regions; 900–1279 context rail collapses to a chip strip + drawer;
  <900 single column, dock and context become swipeable bottom tabs; the left nav keeps the
  existing off-canvas drawer pattern (`left_rail` behavior, reimplemented natively in v3).
- Every table/chart lives in its own `overflow-x:auto` container; the page body NEVER scrolls
  horizontally — enforced by a v3 gate check (§6) at 360/768/1280/1600px widths.
- No fixed pixel widths on content; `minmax()` grid + `max-width:100%` media; touch targets ≥40px
  (existing standard); the wide screener keeps its frozen-pane + `data-wide` full-bleed behavior.
- Payload discipline: v3 pages paginate/virtualize the two known heavyweights (screen2 2.3MB,
  stock 2.7MB) — server-side pagination params, `format=csv` honoring the same params (S-G#1
  lands as a property of the v3 modules, not an edit to live pages).
- Both themes (§5) from day one; print stylesheet inherited from the token contract.

---

## 4. INFORMATION ARCHITECTURE + THE GUIDED JOURNEY

**Six destinations** (top bar, plain words): **Today** · **Markets** · **Stocks** · **Strategies**
· **Tracker** · **Proof** (the renamed Trust — an owner decision; "Proof" says what it is, "Trust"
asks for it). Sub-views per §1: Markets = Internals · Strength · Rotation · Sectors · Seasonality
· Patterns · Flow; Stocks = Screener · Themes · the dossier; Strategies = Library · Books ·
Ownership & filings · Launchpad; Proof = Validation · Replay · Spec-sheets · Rule lab · Coverage ·
Learn (glossary + reading-guide + Pat).

**Naming law** (playbook §4, kept): plain English first, code second, no metaphor-only labels, no
internal IDs in rendered HTML, ONE regime vocabulary (the mood strip's words are canonical).

**The first-run guided journey** — a coach-mark layer (new module, localStorage-flagged,
dismissible and re-summonable from "New here?"), five steps on REAL data:

1. **Understand** (Today): the mood strip + one sentence — "Patearn describes what Indian-market
   data is doing, in plain English, and shows you the proof. It never tells you what to buy." The
   falsification-forward framing sentence renders here (the moat, stated as a moat).
2. **Search**: coach points at the box; typeahead ("tata consultancy" → TCS in 2 actions — already
   live via `symbol_search`); lands on the dossier.
3. **Learn**: coach points at a dotted term-chip on the verdict strip — "every dotted term teaches
   itself; tap one." One tap = the DVPT teach card. This single interaction IS the proprietary-
   language onboarding.
4. **Form your view** (the "decide" step, kept descriptive): coach shows the Context rail — "news,
   results timing, peers and every lens that fired, on one screen. Patearn's verdicts are
   descriptions with evidence links — the decision stays yours." Points at Proof for the record.
5. **Track**: add to a watchlist (demo book for anonymous visitors — the existing
   `tracker_gate.py` posture); alerts arrive on the dock's Alerts channel.

Each persona exits differently: the newcomer to reading-guide, the analyst to Proof→replay-any-date
+ CSV/API affordances, the mobile visitor gets the same five steps against bottom-tab rails, the
skeptic straight to Validation (published failures). Pat is the journey's voice: every step's
"tell me more" opens the matching Pat flow.

---

## 5. THE VISUAL / IMPRESSION SYSTEM (a NEW theme layer)

**Delivery form:** `ui_tokens_v3.py` + `ui_components_v3.py` + `shell_v3.py` — additive modules;
the existing `ui_tokens.py` (the `/* uk-tokens v1 */` contract) is never edited. v3 inherits the
proven decisions (WCAG-AA ink ladder, the up/down/warn value contract, density switch, reduced-
motion, print stylesheet, focus-visible) and changes the *expression*:

- **Typography:** one workhorse UI face + a tabular-numerals mono for EVERY number (numbers are
  the product — they get typographic first-class treatment: `font-variant-numeric: tabular-nums`,
  consistent decimal alignment in tables). Type scale trimmed to 6 steps; body 15–16px equivalent;
  generous line-height in comfortable mode.
- **Spacing & density:** an 8px rhythm; two densities (comfortable default for visitors, compact
  for the analyst — the existing `data-density` idea, promoted to a visible toggle). Cards breathe;
  the current "18 jargon count-tiles" wall is replaced by fewer, larger, subtitled tiles.
- **Color:** dark AND light from day one (light-first was the S177 intent; v3 ships both behind
  the toggle so cut-over is a choice, not a bet). One accent; up/down reserved strictly for signed
  values; verdict-free palettes everywhere else (no red/green on descriptive states). Categorical
  series inherit the `--series-1..8` contract.
- **Component library:** term-chip · teach card · rail card · channel header · dock · coach mark ·
  stat tile v3 (number + plain subtitle, no hover-only meaning) · evidence link ("see the numbers
  →") · fence banner (ONE rendering of `infographics.fence()`'s sanctioned copy) · origin badge.
  All demonstrated on a new `/dash/_ui3` showcase (internal_dev, like `/dash/_ui`).
- **Motion:** 150–200ms ease-out on reveal/expand only; nothing moves that doesn't respond to the
  user; `prefers-reduced-motion` honored (inherited).
- **The impression thesis:** premium = restraint + evidence. The page that convinces a PMS buyer
  is quiet typography, aligned numbers, a visible methodology link on every claim, and the
  falsification record one click away — not gradients. Every "wow" moment is a real capability
  (replay-any-date, the 22y internals ribbon, the union-ladder provenance) surfaced calmly.

---

## 6. BUILD & ROLLOUT (module by module, each independently shippable + 1-line reversible)

**The wiring pattern (exists today):** each module mounts by ONE appended tuple in
`v2_surfaces._ROUTER_SPECS` — revert = remove that line. Preview routes classify as
`internal_dev`/exempt-with-rationale in the route gate's machine-readable tables during preview
(the gate's designed append point), and flip to registered Lenses only at cut-over ratification.
No `main.py`, `dashboard.py`, `ui_kit.py`, `shell_skin.py`, or `left_rail.py` edits at any stage.

| # | Module | Contents | Ships when verified by |
|---|---|---|---|
| M0 | **Preview toggle** | `/dash/preview` — a DIRECT route only (no link/affordance added to any existing chrome, per Codex blocking #2, so default rendered bytes are provably unchanged); opt-in cookie set/cleared via POST. The S177-mandated missing piece. | Live walk: default site byte-identical (curl diff); toggle on → v3 shell renders; isolation test green. |
| M1 | **Theme layer** | `ui_tokens_v3` + `shell_v3` + `ui_components_v3` + `/dash/_ui3` showcase (dark+light). | Showcase at 4 widths, both themes, no horizontal body scroll. |
| M2 | **Term chips** | `term_chip.py` + the Verdict/Could-improve lines in a NEW sidecar `docs/metric-verdicts.md` (decision (a) defaulted to sidecar per Gemini blocking #2 — keeps the legacy glossary parser untouched; owner may later fold into the glossary md). Seed = the §2 terms that resolve through `glossary.lookup()` today. | Chip on the showcase + dedicated seed-chip test: chip → glossary lookup → Pat explain round-trip (Codex blocking #4). |
| M3 | **News/Flow dock** | Channel components over the 6 existing feeds; URL-state filters. | All channels render real rows; empty states honest; mobile bottom-tab mode. |
| M4 | **Stock Focus v3** | `/dash/preview/stock?sym=` — dossier recomposition (Focus + Context rail), chart snippet + overlay seams reused. | walk-the-journey on 3 symbols incl. an F&O name and a thin name; 360px pass. |
| M5 | **Today v3** | Orientation home: mood strip · start-here · flagship band · dock. | Beginner-persona walk passes the audit's friction list top-5. |
| M6 | **Guided journey** | Coach-mark layer, 5 steps, per-persona exits. | A cold browser profile completes all 5 steps on live data. |
| M7 | **Markets/Strategies v3 clusters** | The §1 consolidations (Rotation unified, Sectors 2-tab, Filings hub, Library w/ origin filters). | Each merged view shows a "also available as the classic pages" link-back; nav gate green. |
| M8 | **Screener v3** | screen2 rebuild w/ URL-addressable state + server CSV + pagination. | A filtered view round-trips through its URL; export honors params; <1MB. |

**Ratification gates (per module, none optional):** the SURFACE-PLAYBOOK landing checklist
(education scaffold `bottom_line/plain/how_to_read_link` + `fence()` + glossary keys + Pat
declaration + `sym` links + CSV where tabular + URL state) · route-gate classification in the same
commit · `tests/test_pat_coverage.py` + nav gate + chrome_gate green · **default-site
byte-identity check** (the S177 lesson, made mechanical) · walk-the-journey live at 360/768/1280 ·
deploy per the scp + writer-safe-restart doctrine (VPS py3.10: no backslash-in-f-string; LF; GZip
trap respected by never adding middleware — v3 is routes, not middleware).

**Cut-over** is a separate, final owner decision (flip the default; legacy remains at
`/dash/classic/*` or via the toggle — the reverse of today), explicitly NOT part of this plan's
approval.

**Cost:** zero new timers, zero new always-on compute; all v3 reads are request-time bounded
queries over existing tables; LLM spend unchanged (Pat's existing Gemini path only).

---

## 7. WHAT I RECOMMEND YOU APPROVE FIRST

1. **M0 + M1 + M2 as one approval** (preview toggle · theme layer · term chips): smallest
   end-to-end proof of the two riskiest bets — the premium impression and the self-teaching
   language — with zero live-site risk and a 3-line total revert.
2. **The §1 verdict table** — specifically ratify: the 1 CUT (classic screener), the 3 EXAMINEs
   (early-signals · workbench · evidence-pack — each carries a named check), and the two big
   merges (Rotation unification; the Ownership & filings hub, which also settles open S-B1 item 6).
3. **Four owner decisions this plan cannot make:**
   a. *Verdict/Could-improve lines*: append inside `docs/metrics-glossary.md` (best single-sourcing;
      touches an existing md) vs a new sidecar file (zero touches, slightly weaker).
   b. *"Trust" → "Proof"* rename in the v3 nav (old routes unaffected).
   c. *Conviction*: keep the name or rename to "Composite rank" (the metric is unvalidated and the
      chip will say so either way).
   d. *Preview URL shape*: `/dash/preview/*` (recommended) vs a `?v3=1` param.

After those: M3–M5 (dock, dossier, Today) as the second approval — that is the moment the product
becomes "stocks + news + context on one screen," demo-able against the audit's beginner and expert
walks.
