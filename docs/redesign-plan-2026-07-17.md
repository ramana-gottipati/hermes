# Patearn Web-Experience Redesign — THE PLAN (v1, for owner ratification)

> **Lifecycle: TRANSIENT** — retire when: Ramana ratifies or rejects this plan; on ratification the verdict
> table folds into `docs/SURFACE-PLAYBOOK.md` §6 + a PROJECT_STATE Decision-log entry and the build
> program moves to `docs/NEXT-SESSION-CARRYFORWARD.md`; on rejection, fold the reusable inventory
> (§1) into the UX audit doc and delete. Fold into: `PROJECT_STATE.md` §Decision log +
> `docs/SURFACE-PLAYBOOK.md`.

**Status: M0+M1+M2 APPROVED (Ramana, 2026-07-17) and reviewed by both external stakeholders —
Codex `APPROVE-WITH-CHANGES` and Gemini `APPROVE-WITH-CHANGES`; all blocking findings accepted
and dispositioned in `docs/redesign-coordination.md` (the approval + communication record).**

**🔴 2026-07-18 — CONSTRUCTION PAUSED BY OWNER.** Ramana's correction: approvals were of
direction; before any further building he requires the deeper planning below — competitive
research, style retention, navigation architecture, cross-links/connectivity, and the user
journey. That plan is **PART II** (from §A onward). M0–M3 exist as built opt-in preview modules
(M3's final walk was interrupted; revert = `.bak-s189c`); **nothing further is built until
PART II is reviewed and approved.**

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

---
---

# PART II — THE CONNECTIVITY & JOURNEY PLAN (v2, 2026-07-18 · for owner review, plan-only)

**Method.** Three research streams run 2026-07-18: (1) live teardown of five INDIAN platforms
(Screener.in · Trendlyne · Tickertape · StockEdge · Moneycontrol — fetched pages, RELIANCE as the
common specimen); (2) live teardown of four GLOBAL platforms (TradingView · Koyfin · Simply Wall
St · fiscal.ai); (3) an evidence brief on navigation architecture, cross-linking, and dual-audience
journeys from primary UX research (NN/g controlled studies, Baymard, GOV.UK/USWDS design systems,
Shneiderman, Wikipedia's linking manual). Unverifiable items were marked UNVERIFIED in the raw
reports and are not load-bearing below.

## A. THE COMPETITIVE LANDSCAPE — how nine comparable products organize these sections

| Platform | Primary nav | Stock page | News placement | Education | The lesson for us |
|---|---|---|---|---|---|
| Screener.in | 4 items | ONE scroll, 11 sticky anchors; summary grid → pros/cons → chart → peers → statements → filings | none — filings only | none in-context | Single-scroll + anchors = zero navigation cost; filings-first matches our primary-source DNA |
| Trendlyne | ~22 items | 14 tabs; Overview = linked digest led by DVM scores + SWOT counts | per-stock tab + top-level Results/Insider/Events | word-verdicts + tooltips | A small named score vocabulary reused site-wide works; 22 nav items is label soup |
| Tickertape | 6 items | 8 tabs; header scorecard of 6 word-grades; sector baseline beside every metric | last tab; home news block | best in-context: grades + inline "learn more" + hub | Plain-word grades orient novices; **sector context beside each metric, no click** |
| StockEdge | 4 (+13 side) | app chips; scans double as per-stock badges | dedicated filtered daily feed; FII/DII + Deals top-level | deepest: Learn, courses, per-stock Club | Named concepts loop screener↔stock↔learning; broken deep links kill citability |
| Moneycontrol | 16 items | 15+ anchor-tabs on one long page; SWOT + Stock Vitals + per-stock Seasonality | everywhere (newsroom) | editorial section only | Per-stock seasonality and pass-count checklists are proven; monetization noise destroys trust |
| TradingView | 5 items | 12 tabs; **Overview = preview-card index of every tab**; taxonomy breadcrumb; auto-FAQ foot | `/news/` hub + symbol tab + dockable panel; **symbol chip on every headline** | auto-generated per-symbol FAQs | Overview-as-preview-index; news always anchored to the instrument |
| Koyfin | ~10-12 left-nav | sectioned security mode; user-saveable analysis templates | news in left nav + persistent right-rail icon + earnings calendar | starter dashboards (never blank) | **`/` command bar: ticker ⏎ code chains** — expert speed as a thin layer over routes |
| Simply Wall St | 8 items | ONE narrative scroll: Snowflake → 8 sections, each = 6 **pass/fail checks with stated thresholds** | inside the report only | the score explains itself; methodology public on GitHub | **Checks-as-UI — the evidence IS the interface**; one visual grammar at every altitude |
| fiscal.ai | 6 items | overview + financials/segments/transcripts; AI answers carry **citation-per-claim** to filings | no headline feed; flow = documents | example prompts | Every rendered number should link to its primary source |

**Convergences (all nine):** primary nav settles at **4–8**; depth lives inside the symbol page or
a browse taxonomy, never the top bar. Every platform that onboards novices well uses (a) a SMALL
named plain-word verdict vocabulary introduced once and reused everywhere, and (b) an
overview-that-previews-everything so nobody chooses a tab cold. **Universal failure modes:** nav
items minted per-dataset (Trendlyne, Moneycontrol — exactly our current 71-lens condition), and
verdicts whose evidence is paywalled/hidden (Trendlyne, Tickertape) — the opposite of our moat.

**The archetype decision this forces:** our v1 dossier design ("tabs become in-page sections")
sharpens into a committed archetype — **Simply Wall St's evidence-scroll inside TradingView's
preview-index shell**: ONE scrolling stock page with a sticky section index; the top block is a
digest where every section gets a preview card that anchors down; every verdict decomposes into
pass/fail checks with the real thresholds and numbers shown (our gates/fences already ARE this —
they have just never been rendered as UI). No 12-tab wall, ever.

## B. OUR STYLE — what makes Patearn Patearn, and the retention rules

The flavor, extracted from the estate (all of it already exists in code or doctrine — this
charter makes it binding for every new surface):

1. **Evidence-first.** A number beside every verdict; a check with its threshold beside every
   claim; failures published with the same prominence as wins (the falsification-forward moat).
   SWS renders checks; we render checks **plus the recorded falsifications** — no competitor can
   copy that without our discipline.
2. **Descriptive-only voice.** Word-states, never advice verbs; the mood strip's regime words are
   the ONE vocabulary; `infographics.fence()` is the ONE boundary phrasing source.
3. **Citation-per-claim.** Every metric names its source column/filing/date (our "?" provenance
   popovers, praised in the audit as "better than most vendor terminals", extended by the
   fiscal.ai pattern: numbers deep-link to their source row).
4. **Instrument-panel visuals.** Dark-first, tabular mono numerals, up/down colors reserved
   strictly for signed values, categorical hues never verdict-colored (the `ui_tokens` value
   contract — inherited verbatim by any new theme).
5. **Plain-English-first labels.** "Delivery size ·DVPT·", never the code alone (naming law +
   the term-chip pattern); origin badges 🧑/🏠/📚 disclose lineage.

**Retention rules (binding on every future module):** the v3 token layer inherits the value
contract byte-for-byte; regime words, fence copy, glossary, and Pat corpus each stay
single-sourced; every new verdict ships as decomposable checks; every new number ships with its
source. Style drift = a gate failure, not a taste debate.

## C. THE NAVIGATION ARCHITECTURE CONTRACT — identical from page to page

*(evidence: NN/g controlled studies + USWDS/GOV.UK; citations in the research brief, kept with
the coordination record)*

1. **Two frozen tiers.** A global bar of the 6 destinations — identical on every page, current
   destination marked — and a per-destination left rail listing that destination's sub-views in a
   FIXED order with the current one highlighted. USWDS literally tests "same location and order on
   every page"; that test becomes ours.
2. **Never hidden on desktop.** No icon-only collapse as default (hidden nav halved discoverability
   in NN/g's n=179 study — worse on desktop than mobile). **Amended (Ramana, 2026-07-20, Part V
   §T):** a user-INVOKED, persistent collapse/expand control is allowed — the rail starts visible;
   the user may reclaim width on demand and bring it back. This does not contradict the cited
   finding, which measured DEFAULT-hidden nav, not a user-toggled one.
3. **Canonical breadcrumbs.** `Home > Markets > Rotation > TCS` on every drill-down page — the
   page's home in the hierarchy, never the click path — sitting under the global bar. Arriving by
   search or cross-link still shows the canonical trail: the breadcrumb teaches the IA. Mobile
   collapses to "‹ up one level".
4. **Three altitudes, one move per link** (Shneiderman's overview → zoom/filter → detail):
   Today/Markets = overview · screeners/sectors/strategy-library = filter · the stock page =
   detail. Every cross-link moves exactly ONE altitude; no link ever strands a user two levels
   from a nav anchor.
5. **Hub-and-spoke stock page.** The stock page is the hub; a lens's deep page (opened `?sym=`)
   is a spoke — one click out, one click back (breadcrumb + "‹ back to TCS"). Spoke-to-spoke
   chains are banned.
6. **Sticky discipline.** Thin sticky global bar on data pages; long reading pages (methodology,
   strategy-ref) get a sticky in-page section index instead — which is also the stock page's
   sticky section nav (the §A archetype).
7. **Search-first AND browse-first.** The omnipresent search box resolves symbol + company name +
   lens + glossary term in one index (row format `TCS · Tata Consultancy Services · IT · NSE`,
   symbol-exact ranked first). ⌘K stays the analyst accelerator and is NEVER the only path.
   Koyfin's chaining maps onto our URLs — `/dash/<dest>/<view>?sym=` already is the mnemonic
   system; the palette later learns chained input ("TCS rotation" → the rotation view for TCS).
8. **Mobile mirrors desktop.** 5 bottom tabs = the same destination names and order as the
   desktop bar (the contract survives the form factor); a destination's sub-views become an
   on-page chip row; the stock page's sections become accordions with the verdict visible in each
   collapsed header; wide tables freeze the symbol column and scroll inside their container.

## D. THE CROSS-LINK & CONNECTIVITY SYSTEM — internal, external, and the logical flow

**Three link classes, three fixed treatments (never mixed):**
- **Inline contextual** — a term/metric links to its definition at FIRST occurrence per section
  (Wikipedia's once-per-section rule; over-linking dilutes every link). The affordance is ONE
  system site-wide: the dotted-underline chip/popover with "full definition →" inside.
- **Related block** — one "Related" strip in one fixed position per page (end of focus column),
  **capped at 5**, ranked same-entity-first (TCS on another lens) then same-lens-other-entity,
  driven from the registry (the existing `related_strip` formalized with the cap) — never ad-hoc
  per page.
- **Navigational** — lives only in nav components (bar, rail, breadcrumb, section index).

**Link-label law (the 4 Ss):** specific, sincere, substantial, succinct — "TCS relative-strength
history", never "View more"/"Click here"; every label must predict its destination out of context
(also the screen-reader requirement).

**The connectivity graph (the logical flow, made explicit):**

```
Today board tile ──▶ lens page (overview → filter: one altitude)
lens row [SYM] ────▶ stock hub (?sym= — filter → detail)
stock hub section ─▶ lens deep page ?sym= (spoke; "‹ back to TCS")
news headline ─────▶ symbol chip ─▶ stock hub   (news is NEVER free-floating)
any metric ────────▶ glossary chip ─▶ methodology page ─▶ validation record
fired-lens badge ──▶ that lens filtered to the symbol (the StockEdge loop:
                     the same named concept appears in screener, stock, learning)
```

Rules the graph enforces: every link moves one altitude · every page reachable from nav in ≤2
clicks · every symbol link is `?sym=` (never `symbol=`) · no orphans (the existing route gate
already machine-enforces this) · verdict → evidence → methodology → validation is an unbroken
chain from ANY starting point.

**External links (citations):** primary-source references (NSE/BSE filing, bhav-copy date) open
same-tab by default with a visible ↗ marker and `rel="noopener noreferrer"`; a new tab only when
leaving would lose in-progress work, and then the label says so (W3C G200). Every claim's number
carries its source — the citation-per-claim rule — which is also the citability answer: every
view is a canonical URL (StockEdge's broken deep links are the cautionary tale; for a research
product the URL is the citation).

## E. THE USER JOURNEY — per persona, on real data

*(evidence is unusually one-sided here: upfront tours FAILED in NN/g's n=70 study — skippers
rated apps easier than readers; what works is contextual pull-help, teaching empty states, and
accelerators invisible to novices. v1's M6 "coach-mark journey" is REVISED accordingly.)*

- **The newcomer:** lands on Today → the mood strip in plain words + one identity sentence →
  types a company NAME into the search box ("tata consultancy" → TCS, already live) → the stock
  hub opens on the word-verdict digest (our 8 tiles as plain-word states, every one a chip whose
  evidence is one tap away) → a SINGLE one-shot nudge points at one dotted term ("every dotted
  term explains itself — tap one"); that tap IS the proprietary-language onboarding → scrolls the
  evidence sections; "How to read this page" sits in the same position on every page → empty
  states always teach ("no stocks pass — loosen X") → tracks via watchlist (demo book). No
  welcome tour, ever.
- **The analyst:** ⌘K or URL directly to a symbol/lens → digest first, one disclosure step to the
  full raw table (never a third level) → filters/sorts live in the URL → server CSV + /v1 curl on
  every major table → Proof destination: replay-any-date, spec-sheets with pre-registered hashes,
  the validation record → saved views. All accelerators invisible to the newcomer (Heuristic #7:
  layering + accelerators, never two modes).
- **The skeptic:** starts anywhere → any verdict decomposes into its checks with the actual
  thresholds and numbers (✓/✗ with values, failures rendered as loudly as passes) → methodology
  page (origin-badged 🧑/🏠/📚) → the validation record INCLUDING falsifications → prereg hashes.
  The banned pattern (learned from Trendlyne/Tickertape): a visible verdict whose evidence is
  hidden. Ours is the inverse and the journey proves it at every step.
- **The mobile visitor:** the same 5 destinations as bottom tabs → the stock hub as accordions
  with verdicts visible collapsed → the dock as a swipeable bottom sheet → zero horizontal body
  scroll at any width (the fit guarantee, already gate-tested at 375px).

The five-step arc (understand → search → learn → form your view → track) survives from v1, but is
delivered through structure + contextual help, not a tour.

## F. WHAT PART II CHANGES vs PART I

1. **Stock-page archetype committed:** single evidence-scroll + sticky section index + digest top
   (SWS-inside-TradingView), replacing v1's looser "tabs become sections".
2. **Checks-as-UI adopted:** every gate/fence/verdict renders as pass/fail checks with real
   thresholds and numbers — the strongest borrowable pattern for an evidence-first product.
3. **Word-verdict vocabulary formalized:** a SMALL set of plain-word states (the mood strip's
   words + per-lens states), reused site-wide, evidence always beside — never a paywalled or
   hidden number behind a grade.
4. **Canonical breadcrumbs added** (v1 had none) + the one-altitude-per-link rule.
5. **Cross-link law:** once-per-section inline links · ONE related block capped at 5 · 4S labels ·
   same-tab cited external links.
6. **M6 journey revised:** the coach-mark TOUR is dead (evidence); replaced by one one-shot nudge +
   contextual pull-help + teaching empty states + the persistent "How to read this page".
7. **Mobile contract:** bottom tabs mirroring desktop destinations, accordion stock page, frozen
   symbol columns.
8. **New EXAMINE queue from the teardowns** (each needs an owner nod before any module adopts it):
   sector-baseline-beside-every-metric (Tickertape) · per-stock private notes (StockEdge) ·
   auto-FAQ block per stock (TradingView) · edit-columns-in-place (Screener.in) · palette chaining
   (Koyfin).

## G. WHERE THIS LEAVES THE PROGRAM

Built and parked (all opt-in, invisible from the default site, one-line revert each): M0 preview
gate · M1 theme layer · M2 term chips (deployed, walked) · M3 dock (on the box, final walk
interrupted — say the word to finish the walk or revert via `.bak-s189c`). **Nothing further is
designed or built until you review PART II.** When you do, the decisions that unlock work, in
order: (1) ratify or amend §C's navigation contract and §D's connectivity rules — they shape
every subsequent module; (2) ratify the §A stock-page archetype (it redefines M4); (3) the §F.8
EXAMINE queue; (4) then M4 (stock hub) gets re-planned against the ratified contract before any
code.

---
---

# PART III — PORTFOLIO PRESENTATION & COLUMN ARCHITECTURE (2026-07-18 · plan-only, for owner review)

**Method.** Twelve live teardowns of India's stock-market winners across two cohorts — the
portfolio-product side (smallcase · WealthDesk · MarketsMojo · Finology · Trendlyne/Starfolio ·
Value Research) and the tools/broker side (Chartink [walked live in a browser] · Zerodha
Varsity/Console/Kite · Groww · INDmoney · Tijori · investing.com India) — joined against a full
inventory of OUR column estate (Screen+'s machine-gated 44-column registry; the ~70-column raw
pool across stock_signals/MEP/CPR/pt14/C/CCI/fundamentals/F&O; the four engine-locked books'
stored fields). Every recommended column below is one we ALREADY compute — nothing here requires
new data. Login-gated specifics are marked UNVERIFIED in the underlying reports.

## H. THE INDIAN SUCCESS FORMULAS — what the portfolio winners actually do

| Platform | Known for | Risk vocabulary | The load-bearing pattern |
|---|---|---|---|
| smallcase | basket storefront in your own demat; ₹1.2L-cr+ transacted | Low / Medium / High Volatility (3-tier) | **Provenance firewall:** platform-level "no backtested data; only actual, verifiable performance" |
| WealthDesk | basket rails behind brokers (Share.Market) | investor personas (New/Strategic/Active/Cautious) | **Consent-based rebalance ledger** — every change a dated, approved, explained event |
| MarketsMojo | all-stocks algorithmic grading | Conservative / Moderate / Aggressive / High Value | **Row-level falsifiability:** Date of Entry · Entry Price · own Return · BSE500 return, same window, one row |
| Finology | education-first funnel (Ticker free → One paid) | none — deliberate | **Named lenses with a fence**, including NEGATIVE lenses ("Value Trap", "Growth Bubble") |
| Trendlyne | DVM scores + Superstar filings tracker | (baskets JS-gated) | **Quarter-matrix table:** 9 quarters of holding-% as columns + "New"/"Filing Awaited" chips + freshness note glued to the table |
| Value Research | THE fund star-rating since 1992 | Low / Below Avg / Average / Above Avg / High (percentile 5-tier) | **Published methodology as the moat** — the rating is trusted because the machine is public |

**The tools/broker cohort** (second table):

| Site | Known for | Screener columns | Portfolio columns | The load-bearing pattern |
|---|---|---|---|---|
| Chartink | 150k+ community scans; 12:53 avg session | default 6 (`Sr. · Stock Name · Symbol · Close · %_change · Volume`); customize = premium | — | **The scan page as a shareable artifact:** one URL = readable English rules + live results + love-count + 9-month clickable backtest + embed widget |
| Zerodha Varsity | free book-depth curriculum | — | — | **Numbered 17-module ladder** with visible chapter counts — progress legible, brand halo |
| Zerodha Kite/Console | tax-ready reports; the XIRR truth | — | Kite: `Instrument · Qty. · Avg. cost · LTP · Cur. val · P&L · Net chg. · Day chg.`; Console adds per-holding + portfolio **XIRR, corporate-action-adjusted** | **One trusted number, computed properly** — CA-adjusted XIRR is Indian retail's most trusted portfolio figure |
| Groww | #1 broker by actives; SEO'd simple stock pages | preset filters, no community | login-gated | "Mutual funds invested" co-presented on the stock page — institutional social proof |
| INDmoney | net-worth super-app | basic | aggregated net-worth, family accounts | Import-and-aggregate onboarding: value on day one from EXTERNAL holdings |
| Tijori | segment/KPI/market-share data w/ filing links | NL-query, theme-first | login-gated | Segment-KPI-first company model with filing-linked provenance — our closest philosophical neighbor |
| investing.com IN | econ calendar + technical scorecards | filter grid | manual watchlist P&L | Per-timeframe verdict strip (30-min vs monthly disagreeing, honestly shown) |

**What makes the Indian winners win — the ranked recurring factors (across all twelve):**
1. **Free, ungated, SEO-indexable depth as the growth engine** (Groww, Chartink, Varsity,
   Screener.in; counter-proof: Tijori's login wall caps a superior product at cult status).
2. **One trusted number, computed properly and defended** (Console's CA-adjusted XIRR).
3. **User-generated, URL-shareable artifacts that carry their own logic** (Chartink scans).
4. **Readable rules, no black box** (Chartink's English clause editor; anti-example:
   investing.com's unexplained "Strong Buy").
5. **Freemium cuts on speed/quantity, never capability** (delayed-vs-realtime, quotas — never
   the analytic itself).
6. **Structured curriculum builds the brand halo** (Varsity's ladder).
7. **Alerts convert analysis into habit** (Chartink's per-scan alerts; Tijori's top-level ALERTS).
8. **India-native conventions everywhere** (75/125-min candles, lakh-crore digit grouping,
   shareholding sections, provenance footers).

Patearn already embodies #1 (public estate), #4 (rule-lab, checks-as-UI, published methodology),
and #8 partially; the dock's Alerts channel is #7's seed; #2 nominates a decision — our "one
trusted number" candidates are the CA-adjusted book multiple/CAGR pair and (for tracker books)
a Console-grade XIRR (EXAMINE: needs cash-flow-aware computation).

**The recurring anti-pattern, everywhere:** the verdict is free, the evidence is gated —
blurred teaser returns with no benchmark (Finology Recipe), headline CAGR with backtest boundary
behind login (WealthDesk), "index-beating" in the H1 with constituents paywalled (Trendlyne
baskets), portfolios named but never shown (Value Research Stock Advisor). **Our doctrine is the
exact inverse and PART III is built on it: evidence is never gated; convenience may be.**

## I. STRUCTURAL IMPROVEMENTS — our 71 lenses × our portfolios

1. **Portfolios become the organizing spine of the Strategies destination.** Today the estate is
   organized by LENS (71 destinations — structurally the same per-dataset-nav disease as
   Trendlyne's 22-item bar). The winners organize by USER JOB. Improvement: each book is a HUB
   page that *pulls* lenses in as evidence — the lenses become column families, fired-badges, and
   spokes, not peer destinations. This is Part I's 6-destination collapse, now with the portfolio
   layer as the spine of one destination.
2. **The provenance badge becomes uniform UI.** We already hold the taxonomy in code and doctrine
   (`GROSS_LENS`/`FUNDABLE` consts; ledger statuses FUNDABLE · SEALED-forward · CANDIDATE · PAPER
   · FALSIFIED): render it as ONE visible chip on every book card, every headline number, every
   holdings table — the smallcase firewall generalized. A number without a provenance chip
   becomes a gate failure.
3. **MarketsMojo's row format on every holdings row:** entry/rebalance date · entry price · since
   return · benchmark return over the SAME window, one row. We can derive all four on read
   (`auto_portfolio_holdings` × `auto_portfolio_nav.bench_nav` × `bhavcopy_rows`).
4. **The churn feed grows into a rebalance LEDGER page per book** (WealthDesk's consent-ledger,
   descriptive form): every rebalance = a dated entry with ins/outs (`n_churned` + holdings
   diffs exist) and the one-line WHY from the engine's rule. This is also our audit trail.
5. **The Trendlyne quarter-matrix** applied to our own primary-source estate: shareholding
   (`shareholding_history` has symbol × period_end × metric — exactly the shape), and book
   membership history (holdings snapshots → "in book since / left on" matrix).
6. **The failure ledger becomes product** (Finology's negative lenses, our discipline): "What we
   refuted" cards — BOOK_YIELD's β1.54/−82% DD, PEAD's 0.10, MEP-as-alpha — each with its
   numbers. No competitor ships this; it is our loudest trust signal.
7. **Methodology link on every book card** (Value Research's lesson): `/dash/strategy-ref` pages
   already exist per strategy — the card carries the link + the origin badge 🧑/🏠/📚.
8. **Risk vocabulary: the percentile 5-tier ladder** (Low / Below Average / Average / Above
   Average / High), computed from realized vol + MaxDD percentile within our book/universe
   history — pure pctrank (consistent with the standing no-rupee-thresholds rule), descriptive
   label with the underlying numbers beside it. smallcase's 3-tier is too coarse for an
   evidence product; VR's 5-tier percentile is exactly our grammar.

## J. THE COLUMN ARCHITECTURE — per portfolio, per risk profile

**Our books mapped to risk profiles** (provenance chip in caps):

| Book | Engine | Risk profile | Chip |
|---|---|---|---|
| STEADY-25 | LOWVOL_MOM, quarterly, large-cap | **Conservative / Core** | FUNDABLE-CORE (net 1.19 @₹75cr) |
| CRAFTSMAN-25 | quality × momentum, monthly | **Balanced / Quality** | GROSS-LENS |
| PACER-25 | risk-adj momentum, monthly | **Growth / Assertive** | GROSS-LENS |
| SPRINTER-25 | 12-mo momentum, monthly | **Aggressive** | GROSS-LENS |
| Classic books (8) | public formulas on our PIT data | **Educational / reference** | PAPER (per-book fidelity label) |
| Union family | sealed, forward verdict 2026-10-03 | **Aggressive small/mid** | SEALED-FORWARD (display-only until verdict) |
| The allocation dial | book + G-sec + gold mixes | **The allocation layer** | DESCRIPTIVE (in-sample-optimum trap disclosed) |

**The three-layer column model** (generalizing Screen+'s proven architecture):

1. **IDENTITY SPINE — frozen, never configurable (4):** `Symbol · Sector · CMP · Provenance/entry
   date`. Frozen first column on every width (the financial-table norm; mobile keeps it).
2. **BOOK CORE — the default visible set, 10–12 per book,** chosen for what that risk profile's
   reader actually checks (below).
3. **EVIDENCE POOL — the configurable set, ~70 columns,** = Screen+'s 44 registry columns (11
   families: confluence · positioning · MEP · RS · CPR · CCI · Wolfe · reversal · quality ·
   capital-allocation · context) **+ Fundamentals family (~15:** PE/PB/ROCE/ROE/D-E/promoter/
   pledge/FII/DII/sales-growth/profit-growth/OPM/EPS/interest-coverage + lender NPA/CET1**)
   + Key-price family (4) + F&O family (~8**, only for names with futures**)**. Every column is
   glossary-backed by the existing build gate — a column cannot exist without its teach chip.

**Default column sets per book** (universal honesty columns in every set: `Since rebal % ·
N500 same-window % · ADV ₹cr` — the MarketsMojo row + the liquidity floor):

| Profile / book | Default columns beyond the spine (target 10–12 visible) | Why these |
|---|---|---|
| **Conservative (STEADY-25)** | Target W · W now · Since-rebal vs N500 (pair) · Vol-66d · pt14 tier · ROCE · Div yield · D/E · Promoter % · ADV ₹cr | Stability reader: quality, balance-sheet, income, liquidity — and the honesty pair |
| **Balanced (CRAFTSMAN-25)** | Target W · Since vs N500 · qualmom score · pt14 tier · C-tier (capital allocation) · CCI tier · Profit growth TTM · ROCE · ADV | Quality-forward: adds the management/allocation evidence layers |
| **Growth (PACER-25)** | Target W · Since vs N500 · riskadj score · mom6 · RS# · RS trend state · %52wH · Turnover surge 1m · ADV | Momentum-with-brakes reader: risk-adj rank + trend + extension context |
| **Aggressive (SPRINTER-25)** | Target W · Since vs N500 · mom12 · RS# · RS heat · ×Power · MEP state · Stretch% (band) · ADV | Full-momentum reader: raw rank + tape intensity + how stretched |
| **Classics (8 books)** | The formula's OWN defining fields (e.g. Piotroski: its score components; Graham: PE·PB·D/E) + Since vs N500 + fidelity label (full/proxy) + ADV | Educational: show the famous rule's inputs, not our house scores |
| **Union (sealed, display-only)** | Since-seal vs N500 · seal-time headline BESIDE current (drift disclosed) · mult-anchor status · ADV floor · era-flag | The drift-proof-gate discipline (16AS) rendered as columns |
| **Tracker (owner books)** | today's 8 (Entry · Qty · CMP · P&L · Thesis-health · Since) + any pool column; align labels with the Kite norm (`Avg. cost · LTP · Cur. val · P&L · Day chg.`) Indian users already know; EXAMINE: per-book CA-adjusted XIRR (the Console trusted-number) | The snapshot_json then-vs-now honesty stays the anchor |

**Configurability policy (the "how many" answers):**
- **Default visible: 10–12** columns per book (mobile: spine + 3, horizontally scrolling
  in-container). The market's floor validates a small default: Chartink ships SIX columns by
  default and sells customization; Kite's holdings table is EIGHT. Small default, deep pool.
- **Configurable pool: ~70** (44 now — the Screen+ registry as-is — growing to ~70 when the
  Fundamentals/Key-price/F&O families are registered with glossary keys).
- **Soft cap ~20 simultaneously visible** (beyond that the frozen-pane scan breaks; the reader is
  better served by a second saved view).
- **Mechanics:** toggle by FAMILY (the existing 11 group chips) + per-column within a family
  (new); **named saved views** per user (the Koyfin template pattern; localStorage now); state
  ALWAYS URL-addressable (playbook 8b — a shared URL reproduces the exact view, and CSV honors
  the same params); per-book PRESETS ship as named views ("Conservative read" · "Momentum read"
  · "Forensic read" — the Finology named-lens flavor, fence attached).
- **The market gates columns as a paywall lever** (Screener.in 15→55; Trendlyne 30→600 metrics).
  **We do not:** every column is free; evidence is never gated. If we ever monetize, it is on
  convenience (alerts, exports at scale, API), never on the evidence layer.

## K. WHAT TO APPROVE IN PART III

1. §I.1–I.8 structural improvements (portfolio-spine, provenance chips, row honesty format,
   rebalance ledger, quarter-matrix, failure-ledger cards, methodology links, 5-tier risk ladder).
2. §J's book→risk-profile mapping and the per-book default column sets (edit freely — they are
   proposals grounded in what each profile's reader checks across the nine platforms).
3. The configurability policy: 10–12 defaults · ~70-column pool · ~20 soft cap · saved views +
   URL state · columns never paywalled.
4. §H's borrow queue joins Part II §F.8's EXAMINE list — now including, from the tools cohort:
   per-book CA-adjusted XIRR (Console) · scan-page-as-shareable-artifact for rule-lab verdict
   pages (Chartink) · "mutual funds invested" institutional-holding block on the stock hub
   (Groww, from our shareholding data) · lakh-crore digit grouping site-wide (India-native
   convention) · a Varsity-style numbered ladder for the Learn destination (long-term).

All three research streams have landed; Part III is complete. All of it is plan-only; nothing
is built.

---
---

# PART IV — COMPONENT TREATMENT CONTRACTS (2026-07-18 · the equal-importance layer · plan-only)

**Method.** A full census of every interactive control on every chart/analytical surface
(file:line evidence per control; the raw report sits with the coordination record): the stock
chart's four-family rail + drawings toolset + overlay chips, all eight RS-family surfaces, the
Compare tool, Screen+, and the dense secondary surfaces. The census produced a
capability-parity matrix (§O) — the ground truth this Part turns into contracts. Key confirmed
facts: **no favorites or recently-used mechanic exists anywhere in the estate**; the benchmark
selector exists in **4 visual idioms**; comparison exists in **3 disconnected implementations**
(only `/dash/compare` persists selection — the stock chart's compare set, capped at 4, dies on
reload); drawings and overlays exist ONLY on the stock chart; export is near-absent (Screen+
CSV and drawings-JSON only); glossary hooks are missing from the SVG-first lenses and from the
stock chart itself.

**The rule this Part enforces: treatment is defined once per COMPONENT TYPE, never improvised
per page.** A component cannot be undesigned, because every component belongs to a type, and
every type has a contract. That is how "every component in every area gets equal importance"
becomes checkable rather than aspirational.

## L. THE COMPONENT-TYPE TAXONOMY — nine types, nine contracts

| # | Type (census instances) | The contract |
|---|---|---|
| 1 | **Dense tool rail** — drawings tools, indicator chips, strategy chips | ≤6 items may render flat. Beyond 6: **⭐ pinned favorites + auto MRU (last 3 used) visible; everything else in a grouped dropdown** (the TradingView starred-toolbar reference). Pins persist per user. Flat everything-rows are banned. |
| 2 | **Benchmark selector** — today 4 idioms (rail chips · reload pills · segmented · fbtn bar) | ONE shared component, one look, one order: `Nifty 500 (default) · Nifty 50 · Sector (where meaningful)`; always URL param `den`; identical placement on every surface that has it. |
| 3 | **Comparison / object picker** — 3 implementations today | ONE system, canonicalized from `/dash/compare`'s picker (mixed stocks+indices, presets, chips with ✕, URL-persisted): the stock chart's `cmpBar` adopts it; every multi-object surface adopts it. **The comparison SET travels**: selected objects live in the URL (share-safe) + a session carryover, so stock chart → RRG → Compare keeps your objects (§M). |
| 4 | **Timeline / Play scrubber** — 3 bespoke copies (RRG, RS-Band lanes, clock) | One shared timeline component: Play/Pause · speed · scrubber · period badge; identical keyboard behavior. |
| 5 | **Saved-view control** — Screen+ saved screens; (Part III's column views) | One mechanism estate-wide: named views; **URL params are the state of record** (a shared URL reproduces the view exactly); localStorage only accelerates. |
| 6 | **Scope/filter bar** — Screen+ scope chips, sector select, text filter | Chips for ≤8 mutually-visible scopes; dropdown beyond; filter input always debounced + URL-reflected. |
| 7 | **Segmented view toggle** — Map⇄Weather, Fresh⇄Open, Lanes/Clock/RRG, Rebased/Ratio | One segmented component; active state always also in the URL; a toggle NEVER changes data semantics silently (the label states the frame). |
| 8 | **Table controls** — sort, export, frozen columns | Every analyst table: click-sort, frozen identity spine, server CSV honoring URL params (the Part I/III rule), lakh-crore digit grouping. |
| 9 | **Education hooks** — gloss chips, bottom_line, how-to-read | The REQUIRED TRIO on every routed surface: `bottom_line` + `how_to_read_link` + glossary affordance on every custom metric (the census gaps: cycle-clock, momentum pane, divergence, and the stock chart itself). |

## M. THE COMPARISON CONTRACT — the RS example, made explicit and universal

Reiterating the requirement as binding rules:

1. **Same comparisons everywhere.** Any surface that plots a series against a frame offers the
   SAME benchmark set through the SAME selector (type-2). No surface invents its own benchmark
   list or its own pill style again.
2. **Selected objects follow the user.** The comparison set (up to 12 objects, indices +
   stocks) is one shared concept: chosen once, carried in the URL, offered on every
   comparison-capable surface — open RRG after comparing three stocks on the price chart and
   those three stocks are pre-staged there. Today this is FALSE everywhere (the stock chart
   forgets its compare set on reload; RS surfaces can't receive one).
3. **Same semantics.** Rebase-to-100 at window start, the same window controls (3M/6M/1Y/Max +
   pin-anchor), the same max-object cap, everywhere comparison renders.
4. **Where comparison is deliberately absent** (the rotation 2×2, the divergence board — fixed
   frames by design), the surface SAYS SO in its education line ("fixed frame: stock vs its
   sector; for free comparison use Compare →") and links the Compare tool with the current
   symbol pre-staged. Absence becomes a stated design decision, never an omission.

## N. THE DENSE-RAIL CONTRACT — the drawings example, specified

The drawings rail (census: 8 tools + 5 modifiers, all flat, no favorites) becomes the type-1
reference implementation:

- **Visible by default:** ⭐ pinned tools (seeded: Trend line · Horizontal line · Fib
  retracement — the user re-pins freely) + the auto-MRU slot + `All tools ▾`.
- **The dropdown groups:** Lines (trend/ray/horizontal) · Shapes (rectangle) · Fibonacci
  (retracement/extension + level picker) · Annotate (text) · Measure.
- **Modifiers stay outside the dropdown** (magnet · conflux · hide-all · manage-list) — they are
  modes, not tools. Clear-all keeps its confirm.
- **Persistence:** pins + MRU per user (localStorage now); drawings themselves keep the existing
  per-symbol local+server store (already the estate's best persistence — census 1g).
- The same treatment then applies verbatim to the indicator chip row and strategy chip row the
  moment either exceeds six items (with overlays injected by modules counted in).

## O. THE PER-SURFACE REITERATION TABLE — coverage made checkable

Census status → target per surface (YES/PARTIAL/NO from the matrix; TARGET = the contract):

| Surface | Compare/bench | Multi-obj rebase | Selection persist | URL state | Export | Education trio | The named gaps to close |
|---|---|---|---|---|---|---|---|
| Stock chart | YES | YES (cap 4) | PARTIAL | PARTIAL | PARTIAL (drawings JSON) | PARTIAL | compare set → URL+carryover; adopt type-3 picker; add gloss chips; add data CSV; drawings rail → type-1 |
| RRG | YES | YES | YES (URL) | YES | NO | YES | add CSV; adopt shared timeline (type-4); receive the comparison set |
| Rotation | NO (by design) | NO | YES | YES | NO | YES | state the fixed frame + Compare hand-off (§M.4); add CSV |
| RS-Band | YES | PARTIAL | YES | YES | NO | YES | shared timeline ×2; CSV; canonical-parent decision (Part I) stands |
| Cycle-clock | NO | NO | NO | NO | NO | PARTIAL | URL params; education trio; fixed-frame statement |
| Momentum pane | YES (3-way) | NO | YES | YES | NO | PARTIAL | education trio; receive comparison set (its 3-way bench folds into type-2) |
| Divergence board | NO (by design) | NO | NO | NO | NO | PARTIAL | fixed-frame statement + hand-off; URL state; education trio |
| Capture-map | YES | NO | YES | YES | NO | YES | CSV; shared type-2 selector |
| Seasonal trio | NO | NO | PARTIAL | YES | NO | PARTIAL | education trio completion; CSV on the screen table |
| Internals | NO (by design) | NO | YES | YES | NO | PARTIAL | fixed-frame statement; CSV |
| Compare tool | YES | YES (12) | YES | YES | NO | PARTIAL | becomes the type-3 canon; add CSV; education trio |

Uniformity rules under the table: URL params are first-class state on EVERY surface (the
census found cycle-clock and divergence with none); the 4 benchmark idioms collapse to type-2;
the 3 Play-scrubber copies collapse to type-4; export lands per type-8 on every analyst table.

## P. END-TO-END CONFIRMATION — the complete plan, start to finish

The plan now covers every layer with named artifacts:

| Layer | Where | Status |
|---|---|---|
| Estate verdicts + module sequence | Part I | complete |
| Competitive archetypes · style charter · nav contract · cross-links · journeys | Part II | complete |
| Portfolio presentation · risk profiles · column architecture | Part III | complete (all 3 research streams landed) |
| Component treatment contracts + parity targets | **Part IV** | complete (this section) |
| Owner ratifications | §7.3 + II-§G + III-§K + IV-§P | **awaiting you** |
| Module re-planning (M4+) against ratified contracts → builds under gates | after ratification | not started, by design |

**Part IV approvals:** (1) the nine type-contracts (§L); (2) the comparison contract (§M) —
this one reshapes several surfaces; (3) the dense-rail spec (§N) as the drawings/indicators
treatment; (4) the §O gap list as the component work-queue folded into the affected modules
(M4 stock hub · M7 clusters), each gap a named checklist item in its module's landing gate.

Nothing in Part IV is built; every contract above is a specification awaiting your review.

## Q. BRAND COMPLETION — Patearn everywhere a human reads (2026-07-18, owner: "yes")

**The naming law (immediate, costs nothing):** *Patearn is the product AND the project name in
every human-readable context from today* — UI, Telegram, docs prose, PROJECT_STATE session-log
entries, commit-message prose, session titles. "Hermes" survives ONLY as the frozen
infra-identifier list: systemd `hermes-*` units/timers, `/opt/hermes`, `hermes.db`,
`HERMES_*` env keys, `hermes-api`/`hermes-telegram` service names — legacy codenames, not brand.
Historical records (past session-log entries, sealed docs, the ledger) are NOT rewritten —
records stay records.

**Q-1 · User-facing sweep (build module, small):** the Telegram bot's identity strings ("Hi —
I'm Hermes", "Hermes menu", error signatures) → Patearn; the rendered ops-name leaks
(`hermes-wolfe-scan`, `HERMES_V1_DEV_KEY` shown on web pages) → reworded or fenced as
"internal job name"; plus a **gate**: a test that fails the build on any user-facing "Hermes"
in rendered HTML or bot reply strings (grep-based, allowlisting the infra list).

**Q-2 · Doc-spine retitle (safe, prose-only):** CLAUDE.md / AGENTS.md / PROJECT_STATE.md /
DOC_INDEX headers retitle to "Patearn (repo codename: Hermes)"; new session-log entries open
under the Patearn name. Twin-sync gate re-checked after.

**Q-3 · The visibility fix — repo + folder rename (OWNER DECISION):** what makes "Hermes"
feel everywhere is `D:\Hermes` itself — it names the project in every tool, session record,
and memory path. The rename is a contained one-time migration, NOT plumbing: GitHub repo
rename (old URLs redirect), local `D:\Hermes` → `D:\Patearn`, worktrees re-added, the
project memory directory migrated (copy, verify, then retire the old), `.claude/launch.json`
+ settings checked; the VPS is UNTOUCHED (it runs from `/opt/hermes` regardless). Half a day
with verification, fully reversible until the old dir is deleted. **Recommended: yes, as its
own standalone step scheduled by you — never bundled with a code deploy.**

**Q-4 · Explicitly deferred:** the infra-identifier migration (units/paths/db/env). High risk,
zero user visibility, invalidates recorded ops knowledge; revisit only as its own staged
program with parallel-named units, if ever.

---
---

# PART V — EXTERNAL AI-TOOL EXPLORATION: STITCH MOCKUP REVIEW (2026-07-19 · owner-supplied images, plan-only)

**Method.** Ramana generated nine screens in Google's Stitch (an AI UI-design tool) from a prompt
describing Patearn's feature set and IA priorities, then asked for a documented review folded
into this plan — not a new design track. Each screen was read against the
ALREADY-RATIFIED-OR-PROPOSED verdicts in Parts I–IV (not against a blank slate); nothing below is
copied verbatim, and nothing below authorizes building anything — Part I's construction stays
paused pending owner review of Parts II–IV.

**Screens reviewed:** Today/Home · Sector Rotation (Markets) · Stock Hub (BIOCON) · Equities
Screener (Stocks) · Model Portfolios (Strategies) · a color/type/component style sheet · Market
Internals & Breadth · Proof & Validation Center · Signal Bus (Attention).

## R. Where Stitch independently converges with the plan — the strongest signal in this review

Nobody fed Stitch a copy of Parts I–IV; it was prompted from feature descriptions alone. That it
landed on several of the SAME structures already derived from competitor teardowns is
corroborating evidence, not coincidence to wave past:

| Stitch screen element | Matches (Part/§) | What to take |
|---|---|---|
| Proof & Validation Center: a red-flagged "Transparency Log — Published Failures" table (strategy · test period · expected vs. actual · post-mortem) at equal visual weight to passing content | Part III §I.6 ("the failure ledger becomes product... no competitor ships this") + Part I §1e (Proof = flagship destination) | Concrete layout reference: failures render as a TABLE with the same columns as passes, not a footnote. Adopt the pattern; the specific numbers shown are placeholders, not data. |
| Same screen's "Historical Replay" card (pick a past date + market state, replay conditions) | Part I §1e — replay-any-date already named the single most differentiating trust asset | Confirms card-level treatment (a dedicated, prominent control) is the right register, not a buried link. |
| Stock Hub: a one-paragraph plain-English narrative synthesizing the verdict tiles, sitting ABOVE the chart, before any tab | Part II §A's committed archetype (SWS evidence-scroll + TradingView preview-index; "the top block is a digest") | Validates "digest first." Stitch's version is a narrative sentence, not our 8-tile strip — the two are complementary (tiles for scanning, one sentence for orientation); worth specifying both in M4. |
| Sector Rotation: quadrant map beside a ranked table with a top-leaders/laggards drill-down row | Part I §1a (rrg+rotation+cycle-clock+rsband → one "Rotation" sub-view) | Concrete reference for presenting map + ranked list side by side rather than as separate tabs. |
| Signal Bus (Attention): severity-count tiles (Critical/Elevated/Positive/Neutral) above a checkbox-filterable live event stream | Part I §1a (`attention` KEEP → the dock's Alerts channel + a Today board) + Part IV §L type-6 (scope/filter-bar contract) | A concrete instance of the type-6 filter-bar contract applied to the Alerts channel: per-lens-family checkboxes + a Reset link. Reusable in M3. |
| Model Portfolios: an "THE HONEST RECORD" panel (worst month + known weakness) beside the performance chart, not on a separate tab | Part III §I.2 (provenance badge as uniform UI) + §I.6 | Confirms the honesty content belongs beside the headline number, same glance — not one click away. |

**Read on this:** five independent convergences is a strong signal the Part I–IV direction is
sound — a reason to move forward with ratifying Parts II–IV, not a reason to open a third design
track.

## S. New candidate ideas — added to the EXAMINE queue, none pre-approved

| Idea (source screen) | What it is | Why it needs an owner decision before adoption |
|---|---|---|
| ~~"Metric Dimensions" radar/spider chart on the stock hub~~ **DECIDED (Ramana, 2026-07-20): SKIP** | A 6-axis (Value/Stability/Yield/Quality/Momentum/Growth) shape per stock — visually the Simply Wall St "Snowflake" Part II §A already named as half our committed archetype | **Why skip, not adopt-with-fence:** (1) redundant — the dossier already has an at-a-glance multi-dimensional digest, the 8-tile verdict strip (Part I §3), covering the same ground (Positioning/MEP/RS/Quality/CPR/Credibility); a second shape-based summary widget is two visual grammars claiming the same job, exactly what Part IV §L's "one contract per component type" exists to prevent. (2) a filled radar's defining property is comparative AREA — it reads "bigger blob = better stock" regardless of caption, the same over-reading trap already avoided for Conviction (rendered as a plain-label number with an honesty caveat, never a shape/gauge). A fence sentence has been sufficient for number displays sitting beside their own caveat; it hasn't been asked to suppress a chart TYPE's built-in gestalt, and there's no evidence it would. (3) not a permanent ban — if a genuine need surfaces for comparing 2–3 stocks' multi-axis profiles side by side (a different job than a single-stock digest), evaluate that as its own proposal. |
| "Live Lenses" tappable count-tiles on Today (e.g. "Accumulation · 28 · Tap to screen") | Each fired-lens count is itself a one-tap pre-filtered screener link | Fits the newcomer journey (Part II §E) and the Today "flagship band" (Part I). Cheap to fold into M5 (Today v3) — recommend adopting rather than treating as an open research question. |
| The style sheet's blue/green/red "Primary/Secondary/Tertiary" palette used as generic UI accents (buttons, active-nav highlight) | A 3-hue brand palette | **Direct doctrine tension, not just a style question:** Part II §B.4 and Part I §5 both bind red/green to signed values ONLY ("verdict-free palettes everywhere else... categorical hues never verdict-colored"). A green button beside a red button reads as an implicit up/down verdict even when it isn't one. Recommend: keep the single-accent-hue rule; do not adopt red/green as brand accent colors. |
| The floating "What would you like to change or create?" input at the bottom of the Screener mockup | Reads as a free-text prompt bar | **Probably NOT a proposed app feature** — it has the shape of Stitch's own "keep editing this design" canvas control, not a screener feature you described to it. It isn't discussed anywhere in Parts I–IV, and an LLM-driven screening input would cut against the standing rule-based-screening doctrine (CLAUDE.md Guardrail #4). Recommend: disregard unless you confirm you actually want a natural-language screener query box — that would be a new, separate proposal, not a Stitch artifact. |

## T. Doctrine tension — DECIDED (Ramana, 2026-07-20)

Ramana's instruction in S189/Part-V's originating session — **"collapse the extra layer on the
left side so the full window is available whenever the user needs it"** — touched an
already-ratified, evidence-cited rule:

> Part II §C.2: *"Never hidden on desktop. No icon-only collapse as default (hidden nav halved
> discoverability in NN/g's n=179 study — worse on desktop than mobile)."*

**Decision: the left rail stays visible by default on desktop; a persistent, user-invoked
collapse/expand control is added.** The NN/g finding was specifically about nav that is
**collapsed by default** — a user-toggled collapse (rail starts visible; the user reclaims width
on demand and can bring it back) doesn't contradict the cited study. Recorded as the amendment to
Part II §C.2 itself (see that section) so the navigation contract stays the single source of
truth for this rule.

## U. What to approve from this Part

1. Fold **R**'s five convergences into the relevant modules' specs (M4 stock hub gets the
   narrative-digest note; M3's Alerts channel gets the severity-tile + checkbox-filter treatment;
   M7's Rotation cluster gets the map+ranked-list layout note) — no new owner decision needed,
   these agree with already-approved direction.
2. **S's radar chart — DECIDED: skip** (see the table above). The other two S items — count-tile
   Today pattern (recommend adopt) and palette-as-accent (recommend reject) — remain open,
   decide alongside Part II §F.8's EXAMINE queue.
3. **T's nav-collapse — DECIDED:** user-toggleable, not default-hidden; Part II §C.2 amended
   in place.
