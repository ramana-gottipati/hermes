> **Lifecycle: TRANSIENT** — the Graphite parity-fix work-list (2026-07-28 audit: 464 gaps, 160 MAJOR, over 55 then-PORTED surfaces at main `0f296cf`). Retire when the fix program closes it: fold outcomes into sideways_parity dispositions + PROJECT_STATE, then git rm. Registered in docs/DOC_INDEX.md.

# GAP REGISTER — classic → Graphite, complete per-surface capability diff

**Lane:** GAP-AUDIT (read-only) · **Repo:** `D:\patearn` @ `main` (`ba2c259`, on top of `0f296cf`) ·
**Date:** 2026-07-28

**Standard applied (strict, per the W2-C precedent):** a surface is only PORTED if the classic
CONTROLS, DATA BLOCKS, INTERACTIONS and OPTION RANGES are all served at the new route. A page that
renders and reads well while missing load-bearing blocks is NOT ported. **Pro-gating in Graphite of
something FREE in classic counts as MAJOR** — it is capability loss for the owner.

**Register = (fresh per-block diff) ∪ (recorded owed items).** `recorded-or-fresh` column:
`RECORDED` = the `SURFACE_PARITY` note or ledger §3 already names it · `FRESH` = found by this audit ·
`RECORDED-BUT-FALSE` = a recorded claim contradicted by the code.

**Totals:** 464 gap entries — **160 MAJOR · 244 MINOR · 60 COSMETIC**;
**358 FRESH-FOUND · 99 ALREADY-RECORDED · 7 RECORDED-BUT-FALSE** (a recorded claim the code
contradicts). Parity board state at audit time: 74 surfaces · PORTED 55 · DEFERRED 12 · DROPPED 5 ·
NA 2 · 0 UNSCOPED (verified by executing `sideways_parity.summary()`; all 74 carry explicit
dispositions, none falls to a default).

---

## 0. CROSS-CUTTING — systemic gaps that repeat on every Graphite page

These are counted once here, not in every per-surface table below. Each is one build item that
closes dozens of individual rows.

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **X-1. The estate-wide TABLE TOOLBAR is gone** — click-any-header sort · live row filter box · live row count · ⬇ Export CSV · the ⚙ column picker with default-hidden columns · `?` glossary popovers on headers. In classic this is auto-attached by `_DT_JS` to **every** `table.dt` and injected into every page by `_shell`; ~40 Graphite tables have none of it | MAJOR | `src/web/dashboard.py:288-390` (`_DT_JS`), `:518` (injected by `_shell`); `src/web/table_controls.py:71-117` (`_picker`, `data-tcoff`, `_gloss_th`) | `src/web/home/markets_ui.py:71-79` (`U.table` = a bare `<table class="g-mtbl">` in a scroll box); `src/web/home/strategies_blocks.py:73-78`; `src/web/home/tracker_pages.py:415-439` — no JS, no picker, no popovers anywhere in the package | FRESH |
| **X-2. Pro-gating is NEW and it hides data that was FREE.** Classic has zero tier machinery — no `pro-more` / `data-tier` token exists in `dashboard.py`, `cockpit.py`, or any of the 11 classic strategy views. Graphite ships `data-tier="free"` and hides `.pro-more`. At least **40 columns/blocks that were unconditionally visible in classic are invisible by default** (roll-up below) | MAJOR | absence of any tier class across the classic estate | `src/web/home/shell.py:53` (`.pro-more{display:none}`), `:54`, `:166` (`data-tier="free"`); `src/web/home/components.py:126-149` (`pro_more`/`pro_teaser`) | FRESH — `SURFACE_PARITY` records pro-gating on only 3 keys |
| **X-3. Nav reachability — 33 Graphite routes, 6 nav destinations, and 2 of those 6 still point at CLASSIC pages.** `Stocks` → `/dash/stocks` and `Proof` → `/dash/coverage` are classic routes even though `/dash/home/strategies/positioning` and `/dash/home/proof` exist. `Markets` lands on `/dash/home/internals`, so rotation · strength · sectors · flows · events · attention · seasonal · patterns · anatomy · own-history · compare · screen · themes are reachable only from in-page links | MAJOR | n/a — classic nav is registry-generated (`src/web/lens_registry.py`) | `src/web/home/shell.py:17-19` (`DESTS`, 6 entries); 33 `@router.get("/dash/home…")` routes enumerated across `src/web/home/*.py` | RECORDED (ledger `docs/graphite-cutover-orchestration.md:35`, `:168`, `:259-262` — W6 owes nav wiring + the `nav_integrity_gate` ↔ `INTERNAL_DEV` allowlist reconciliation, orphans 5 → 16) |
| **X-4. The `?`-popover glossary system did not travel.** Classic wraps metric headers in `G.gloss(...)` producing an in-page hover definition, site-wide. Graphite replaces it with prose `C.learn`/note blocks and, on the screener, a link-out — which points at the CLASSIC glossary route, a cross-experience leak | MINOR | `src/web/glossary.py`; consumers e.g. `src/web/rrg_view.py:224-233`, `src/web/rotation_view.py:217`, `src/web/capture_map.py:136-138`, `src/web/cockpit.py:2276-2288` | no `gloss` call anywhere in `src/web/home/`; leak at `src/web/home/screen_pages.py:543` (`/dash/glossary`, twin is `/dash/home/glossary` at `trust_pages.py:661`) | FRESH |
| **X-5. Systematic depth reduction.** Row caps were cut on ~20 boards without a "showing N of M" note: attention 200→30 · surveillance tape 400→40 · event-cadence 400→40 · results 500→120 · leaders 60→30 · momentum 60→40 · MEP 300→80 · seasonal-screen 300→40 · self-history universe→40 · band-locks→30 · buyback tape 30→12 · corporate-actions context 200→12, and more | MINOR | see the per-surface rows in §2-§8 | see the per-surface rows in §2-§8 | FRESH |
| **X-6. SURFACE-PLAYBOOK obligations owed at cutover** — Pat registration + glossary keys for every new Graphite route (`tests/test_pat_coverage.py` / `docs/pat-knowledge-contract.md` are machine gates on ROUTED lenses; the Graphite routes are unregistered) | MINOR | Guardrail #9; `docs/SURFACE-PLAYBOOK.md` | none of the 33 `/dash/home/*` routes is a registered lens (owner explicitly rejected registry registration at D148 to avoid drifting classic nav — ledger `:35`, `:106-112`) | RECORDED (ledger `:168`) |

### Pro-gating roll-up (X-2) — capability FREE in classic, Pro-only in Graphite

| surface | hidden behind Pro | Graphite line |
|---|---|---|
| rotation · band | the plain-English read/why | `rotation_pages.py:151`, `:171` |
| rotation · clock | RSI-of-RS, Mansfield | `rotation_pages.py:247-248` |
| rotation · journeys | the **12M and 24M horizons entirely** | `components.py:1360-1361`, `:1376-1378` |
| strength · overview | 3m RS · 12m RS · RSI-of-RS | `strength_pages.py:130-131` |
| strength · leaders | RSI-of-RS · stock-vs-broad · stock-vs-sector · sector-vs-broad | `strength_pages.py:171-174` |
| strength · momentum | HI52 · Turnover ₹cr · Percentile | `strength_pages.py:214-216` |
| sectors · standing | 1m return · 3m return · Avg RS rank | `sectors_pages.py:126-128` |
| sectors · drill | RSI-of-RS + the entire RSI breadth read | `sectors_pages.py:99`, `:106-109` |
| sectors · economics | risk-table Read | `sectors_pages.py:220` |
| internals | the three regime charts; the exact percentile ordinals | `internals_pages.py:483-486`, `:285-289` |
| flows · participants | the 8-row FII history; the percentile extremity read | `internals_pages.py:594-601`, `:566-568` |
| flows · F&O | **~180 of ~200 names** (Free sees 12) | `internals_pages.py:645-649` |
| events · actions | just-went-ex + restructure context | `internals_pages.py:767-769` |
| attention | the batch-history table | `internals_pages.py:1163-1165` |
| seasonal · tape | the forward-outlook band | `seasonal_pages.py:187-196` |
| tracker · overview | contributors/detractors | `tracker_pages.py:327-329` |
| tracker · positions | Weight · Target · Stop · Days held · RS phase · Book | `tracker_pages.py:415-420` |
| tracker · watchlists | Price then · Since added · Days · RS rank · Own deliv. avg · Book | `tracker_pages.py:481-483` |
| strategies · books | an evidence table block | `strategies_blocks.py:230-233` |

Gate: `src/web/home/shell.py:53` / `:54` / `:166`.

---

## 1. Rotation family — `rrg` · `rotation` · `rsband` · `cycle-clock` → `/dash/home/rotation`

### 1a. `rrg` — `/dash/rrg` → `/dash/home/rotation` (default `?view=journeys`)

Parity says PORTED (`sideways_parity.py:158`). Under the strict standard it is **not** — the entire
Play/scrubber apparatus, the RS-depth table and both drills are absent, and two of three horizons
are Pro-locked.

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Play — autonomous rotation playback** (comet trails, resume-from-cursor, pause) | MAJOR | `src/web/rrg_view.py:615-625` (`play()`), `:688-689` (button) | `src/web/home/rotation_pages.py:274-277` renders the static §5-D view; `src/web/home/components.py:1340-1345` `_ROT_JS` is a period toggle only — no animation | FRESH |
| **Three playback speeds** slow/med/fast (18 000 / 10 000 / 5 000 ms total journey) | MAJOR | `rrg_view.py:526` (`SPD`), `:626` (`setSpd`), `:675-683` (the speed switch) | no speed control exists — `components.py:1340-1345` | FRESH |
| **Draggable timeline scrubber** (travel the window back/forth) | MAJOR | `rrg_view.py:704-706` (`#rrgscrub`), `:611-612` (`scrubTo`) | none — the only control is a 3-button horizon group, `components.py:1358-1364` | FRESH |
| **Month badge** naming the frame you are parked on | MAJOR | `rrg_view.py:701-703` (`#rrgmonth`), `:383-389` (`_fmt_frame_label`), `:601` (`hud`) | none — `components.py:1358-1364` | FRESH |
| **Live quadrant-breadth readout** recomputed per frame (leading/improving/weakening/lagging counts as you scrub) | MINOR | `rrg_view.py:600-602` (`qAt`/`hud`), `:707` (`#rrginsight`) | a STATIC today-only summary — `components.py:1305-1316` (`_rot_quad_summary`) | FRESH |
| **Hover-to-trace** — hovering one sector dims all others and draws its journey up to the parked month | MAJOR | `rrg_view.py:581-587` (`hiTrace`), `:588-592` (`wire`) | all tails always drawn, no isolate; only `tabindex`/`aria-label` — `components.py:1288-1294` | FRESH |
| **Rich hover tooltip** (quadrant · RS-ratio · RS-mom · RSI-of-RS · Mansfield · up/down-capture · month) | MINOR | `rrg_view.py:589` | `aria-label` only, no tooltip — `components.py:1289` | FRESH |
| **3-month horizon missing** | MAJOR | `rrg_view.py:373-374` (`_SECTOR_TAILS = 3/6/12/24`), `:480` | `components.py:1302` `_ROT_PERIODS = 6/12/24` | FRESH |
| **12M and 24M horizons are PRO-LOCKED teasers** — free on classic | MAJOR (pro-gating regression) | `rrg_view.py:480-484` — all four pills are plain links, no gating | `components.py:1360-1361` (`data-pro`, PRO badge), `:1376-1378` (`pro_teaser`) | FRESH |
| **Timeframe-native cadence** — 3m daily · 6/12m weekly · 24m monthly closes with JdK params rescaled per cadence, so one day cannot jerk a long-window dot | MINOR | `rrg_view.py:377` (`_TAIL_CADENCE`), `:403` (`_CADENCE_JDK`), `:406-423` (`_rrg_jdk`), `:438-471` (`_sector_tail`) | daily JdK then block-mean into a fixed 10 dots — `src/web/home/reads.py:192-233` (esp. `:207`, `:228`) | FRESH |
| **Benchmark toggle** vs Nifty 500 / Nifty 50 | MINOR | `rrg_view.py:64` (`BENCHMARKS`), `:119-128` (`_controls`), `:825` (`den=`) | benchmark fixed; the route honours only `?view=` — `src/web/home/__init__.py:71`, `reads.py:192` | FRESH |
| **Stable per-sector identity colour** (19-colour palette; colour = WHO, never changes as the dot moves) | MINOR | `rrg_view.py:516-520` (`_RRG_PALETTE`), `:642-644` | coloured by QUADRANT, so a sector changes colour as it rotates — `components.py:1274` (`_QCLASS`), `:1273-1276` | FRESH |
| **RS-depth table**: RSI-of-RS · Mansfield · Falls-less Δ% (down-excess) · Down-capture · Up-capture · **Signals** (7 turn-flag pills: base turn / rolling over / RSI turn / bull div / bear div / MRS+ / MRS−) | MAJOR | `rrg_view.py:223-233` (header), `:88-104` (`_flags`), `:240-263` | Graphite table = Sector · Quadrant · ratio·mom (Pro) — `components.py:1318-1339`. RSI/Mansfield reappear Pro-gated on `?view=clock` (`rotation_pages.py:247-248`), capture on `strength?view=capture`; **the turn-flag Signals column has no home anywhere** | FRESH |
| **Per-row deep-link** to the ratio chart `/dash/ratio?idx=&den=` | MINOR | `rrg_view.py:255-257` | rows are inert text — `components.py:1332-1334` | FRESH |
| Dot size encodes up-capture (static map) | COSMETIC | `rrg_view.py:184-185` | uniform `r=4.8` — `components.py:1290` | FRESH |
| **Constituent drill `?idx=`** — member stocks of one index on their own RRG, with a vs-sector / vs-broad toggle and a constituent table | MAJOR | `rrg_view.py:267-360`, `:327-341` (toggle), `:834-846` | no constituent RRG anywhere in Graphite; `src/web/home/sectors_pages.py:74-112` (`_drill`) is a table, not a rotation map | RECORDED-BUT-FALSE — `sideways_parity.py:160-162` says the `?idx=` drill "belongs to the Graphite stock hub"; it is neither there nor built |
| **Single-stock RRG `?sym=`** — one stock's RS journey tail, 3/6/12/24 tail control, lifecycle label, cross-links to band + stock page | MAJOR | `rrg_view.py:744-821`, `:831-833`, `:809-816` (tail pills) | claimed to live on the stock hub, but `src/web/home/stock_page.py:40-64` (`SECTIONS`) has no rotation section and `sec_strength` (`stock_page.py:427-450`) is a key-value read with no RRG | RECORDED-BUT-FALSE — same note, `sideways_parity.py:160-162` |
| Glossary `?` popovers on table headers | MINOR | `rrg_view.py:224-233` (`G.gloss`) | prose notes / `C.learn` only — `rotation_pages.py:119-121` | FRESH |

**IMPROVEMENT (not a gap), owner-requested:** an **18-month** horizon exists on neither side —
classic `_SECTOR_TAILS = 3/6/12/24` (`rrg_view.py:374`), Graphite `_ROT_PERIODS = 6/12/24`
(`components.py:1302`). It is consistent with the estate's existing vocabulary: the classic rotation
member table already carries 18m and 24m RS columns (`rotation_view.py:229`). Target horizon set:
**3 / 6 / 12 / 18 / 24**.

### 1b. `rotation` — `/dash/rotation` → `/dash/home/rotation?view=weather`

Parity says PORTED (`sideways_parity.py:163`). Classic is a **stock-grain** weather lens; the
Graphite twin is a **sector-grain** table plus a 6-name-per-cell grid. The stock-grain half — the
page's largest data block and its only filter — did not travel.

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`?phase=` selector** (4 phase pills that drive the page) | MAJOR | `src/web/rotation_view.py:261-267`, `:271` | no phase param; the route honours only `?view=` — `src/web/home/__init__.py:71` | FRESH |
| **The per-phase MEMBER TABLE** — up to 300 stocks × 13 columns: Symbol · RS rank · Sector · Sector phase · 1m · 3m · 6m · 12m · **18m** · **24m** · RSI-of-RS · Signals · CMP | MAJOR | `rotation_view.py:221-258` (`:226-231` header, `:222` limit 300) | only 6 shortlist names per cell (symbol + rank) — `rotation_pages.py:83-85`, `src/web/home/markets_reads.py:132-149` (`limit=6`) | FRESH |
| **"See all N →" per-cell drill** — the count is a live door in classic, a dead number in Graphite | MAJOR | `rotation_view.py:213-215` | `rotation_pages.py:89-91` renders the count with no link | FRESH |
| **The 7 leverage-read pills** — RS▲>price · ⚡accel · ⚡down · ✅deliv · abs✔ · RSI hot · RSI cold, each with an explanatory `title=` | MAJOR | `rotation_view.py:73-90` (`_marks`), used at `:210` and `:254` | absent from every Graphite rotation view — `rotation_pages.py:83-85` | FRESH |
| **`early-signals` re-home** — the DROP rationale makes a "just turned UP" direction filter a hard dependency on this port | MAJOR | `sideways_parity.py:275-290` (esp. `:285-290`) | `_turns` has no direction filter — `rotation_pages.py:96-105`, `markets_reads.py:152-167` | RECORDED |
| 18m and 24m RS horizons | MINOR | `rotation_view.py:229`, `:252` | weather table stops at 12m — `rotation_pages.py:114-116` | FRESH |
| **Leadership-breadth banner** — per-phase sector counts + "broad / narrow / mixed leadership" + "risk-on rotation / leaders in control" | MINOR | `rotation_view.py:134-164` | no synthesis line — `rotation_pages.py:117-124` | FRESH |
| Per-cell context columns (sector name, rank, marks per row) | MINOR | `rotation_view.py:204-210` | symbol + rank only — `rotation_pages.py:83-85` | FRESH |
| Just-turned strip depth: 40 movers scanned → 24 chips | MINOR | `rotation_view.py:168`, `:182` | capped at 18 — `markets_reads.py:152` | FRESH |
| Glossary `?` popovers on phase headings and RS columns | MINOR | `rotation_view.py:217`, `:228`, `:230-231` | prose only — `rotation_pages.py:119-121` | FRESH |

### 1c. `rsband` — `/dash/rsband` → `/dash/home/rotation?view=band`

Already `DEFERRED` (`sideways_parity.py:189-195`). The recorded owed-list names the per-index
channel, the per-stock channel, the constituent lanes and the journey scrubber. **It understates the
gap**: the sector LANE CHART itself, the look-back control, Play, the movers strip and the whole
band CLOCK (Breathe) view are also missing, and the plain-English read was Pro-gated.

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The LANE CHART** — per-sector lane with cheap/rich zone tints, out-of-band caps, POC "magnet" diamond, regime dot, history knot-path, current marker, verdict label | MAJOR | `src/web/rsband_view.py:135-215` (`_LANE_JS`), `:222-245` (`_chart_block`) | a plain table with a 0-100 position strip — `rotation_pages.py:142-153`; `src/web/home/markets_ui.py:101-111` (`pos_strip`) | FRESH |
| **Look-back segmented control** 6m / 12m / 24m | MAJOR | `rsband_view.py:217` (`_segbtn`), `:237-238`, `setH` in `_LANE_JS:212` | none — `rotation_pages.py:166-191` | FRESH |
| **Play** over the look-back window (comet trails per lane) | MAJOR | `rsband_view.py:203-208` (`play()`), `:239-241` (`#rbplay`) | none | RECORDED (partly — "the journey scrubber") |
| **Draggable scrubber + month badge** | MAJOR | `rsband_view.py:121-133` (`_month_labels`), `:209-211` (`scrubTo`), `#rbscrub`/`#rbmonth` | none | RECORDED ("the journey scrubber") |
| **Top-3 / bottom-3 band movers** over the chosen window | MINOR | `rsband_view.py:213-216` (`movers()`), `:244` (`#rbmov`) | none | FRESH |
| **Lane hover tooltip** — band + label + regime + N-month delta + magnet + read | MINOR | `rsband_view.py:186-198` (`wire`) | a bare `title=` on the strip — `markets_ui.py:109` | FRESH |
| **Click a lane → its channel** | MAJOR | `rsband_view.py:199-200`, table link `:355` | band rows are inert text — `rotation_pages.py:144-152` | FRESH |
| **The band CLOCK view** — radial bloom, "Breathe" playback, 6/12/24 horizon, scrubber + month badge, click-a-spoke drill | MAJOR | `rsband_view.py:310-340` (`_clock_block`), `_CLOCK_JS` above it | `?view=clock` in Graphite is the RRG cycle clock — a different reading; the band bloom has no counterpart — `rotation_pages.py:242-264` | FRESH |
| **Benchmark pills** Nifty 500 / Nifty 50 | MINOR | `rsband_view.py:415-425` | benchmark fixed — `markets_reads.py:171` | FRESH |
| **Trend-R² column** | MINOR | `rsband_view.py:344` | not in the Graphite column set — `rotation_pages.py:170-172` | FRESH |
| **The plain-English read/why is FREE in classic, PRO in Graphite** | MAJOR (pro-gating regression) | `rsband_view.py:365-368` | `rotation_pages.py:151`, `:171` (`pro-more`) | FRESH |
| Per-index CHANNEL page `?idx=` — support/median/resistance rails, POC, value area, readout | MAJOR | `rsband_view.py:575-703`, `:704-728` | none | RECORDED |
| Per-stock channel `?sym=` | MAJOR | `rsband_view.py:729-767` | none | RECORDED |
| Constituent lanes + vs-broad / vs-sector pills | MAJOR | `rsband_view.py:866-936` | none | RECORDED |
| _Verdict label (Ride/Fade/Trim) deliberately never rendered_ | **NOT A GAP** — ratified honesty decision | `rsband_view.py:341-374` | `markets_reads.py:180-182` (engine key never reaches the DOM) | RECORDED-DECISION |

### 1d. `cycle-clock` — `/dash/cycle-clock` → `/dash/home/rotation?view=clock`

Parity says PORTED (`sideways_parity.py:167`). The port carries the dial and adds a table, but drops
the one thing the classic lens was built to add over the RRG scatter.

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The VELOCITY VECTOR** — a clockwise tangent arrow per sector whose length ∝ momentum (the lens's stated reason to exist: "direction & speed of travel, which the 2×2 weather grid throws away") | MAJOR | `src/web/cycle_clock.py:5-7` (docstring), `:103-109` (arrow math + `marker-end`), `:76-78` (marker def) | bare circle + label, no direction — `rotation_pages.py:213-225` | FRESH |
| **RSI-of-RS is FREE on classic hover, PRO in Graphite** | MAJOR (pro-gating regression) | `cycle_clock.py:106` (in the `<title>`) | `rotation_pages.py:247` (`pro-more`) | FRESH |
| **Click a dot → constituent drill** (`/dash/sector-momentum?idx=`) | MINOR | `cycle_clock.py:107`, `:110-112` | `<title>` only, no link — `rotation_pages.py:222-223` | FRESH |
| Lifecycle vocabulary (Recovery / Tailwind / Rolling-over / Headwind) — the Graphite clock uses RRG words while the Graphite weather view next door uses lifecycle words | COSMETIC (internal inconsistency) | `cycle_clock.py:33-38`, `:85-90` | `rotation_pages.py:209-212` vs `:78` | FRESH |
| Label de-clutter (top-10 by magnitude, stacked to avoid overprint) | COSMETIC | `cycle_clock.py:93-94`, `:115-122` | every dot labelled, no de-collision — `rotation_pages.py:224` | FRESH |

---

## 2. Strength + Sectors — `rs-hub` · `leaders` · `momentum-scan` · `capture-map` · `sectors` · `sector-momentum` · `sector-economics`

Graphite ships `data-tier="free"` (`src/web/home/shell.py:166`) and `.pro-more{display:none}`
(`shell.py:53-54`), so every `pro-more` column below is **invisible by default** while the classic
equivalent was unconditionally visible.

### 2a. `rs-hub` — `/dash/rs-hub` → `/dash/home/strength`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Benchmark selector `?den=` (Nifty 500 / Nifty 50)** — the hub's only control; it also re-drove every child-lens link | MAJOR | `src/web/rs_section.py:33`, `:194-199`, `:220-221`, `:55-56` | `src/web/home/strength_pages.py:328-334` (route reads `view` + `h` only); `src/web/home/markets_reads.py:39` hardcodes `BENCHMARK = "Nifty 500"` lane-wide | FRESH |
| **`3m RS · 12m RS · RSI-of-RS` Pro-gated** on the standing table (data read free at `markets_reads.py:275-277`); free on every classic RS surface | MAJOR | `src/web/cockpit.py:2437`, `src/web/dashboard.py:630-654` | `strength_pages.py:128-131`, rows `:74-76` | FRESH |
| **Live previews inside every lens card** (real rows, not prose): leaders top-4 + 2 laggards w/ rank · RRG top-4 w/ ratio & momentum · RS-band 3 cheapest w/ band % · phase-mover chips `prev→now` · divergence counts + name chips | MINOR | `rs_section.py:61-77`, `:80-93`, `:96-110`, `:113-125`, `:133-153`, `:156-163`, `:200-207` | `strength_pages.py:99-120` — four hardcoded `(title, href, question, blurb)` tuples, no data read | FRESH |
| **Two lens cards dropped**: `Divergence` and `Level` (`/dash/rsband?den=`) | MINOR | `rs_section.py:42-43` | `strength_pages.py:99-112` (Leaders / All-weather / Rotation / Sectors only). Graphite divergence exists at `src/web/home/internals_pages.py:406-443` but is unreachable from the strength hub | FRESH |
| **"RS ratio chart ↗" deep-link to `/dash/ratio`** | MINOR | `rs_section.py:211-212` | no `/dash/ratio` link in `strength_pages.py` or `markets_ui.py` | FRESH |
| Standing-table `Sector` cell is unlinked | MINOR | classic pattern `src/web/cockpit.py:2438-2439` (sector → `/dash/index?idx=`) | `strength_pages.py:71` plain text | FRESH |
| Standing table capped at 25 rows, no paging | MINOR | classic `/dash/leaders` served 60 (`cockpit.py:2417`) | `strength_pages.py:125` (`limit=25`) | FRESH |
| `ifx.bottom_line` + "How to read" scaffold dropped | COSMETIC | `rs_section.py:222-228` | `strength_pages.py:51-55`, `:144-147` | FRESH |
| **Stock hub still deep-links back to classic `/dash/rs-hub`** for the per-symbol half the parity note says it owns | MINOR | claim at `src/web/sideways_parity.py:170-175` | `src/web/home/stock_page.py:52` | FRESH |

### 2b. `leaders` — `/dash/leaders` → `/dash/home/strength?view=leaders`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`RSI-RS` column Pro-gated** (free in classic) | MAJOR | `src/web/cockpit.py:2437`, header `:2444` | `strength_pages.py:172`, cell `:157` | FRESH |
| **All three alignment-state columns Pro-gated** (`stock vs broad`, `stock vs sector`, `sector vs broad`) — these ARE the screen's thesis; Free sees only Symbol/rank/sector | MAJOR | `cockpit.py:2440-2442`, header `:2445` | `strength_pages.py:173-174`, `:158-161` | RECORDED (`sideways_parity.py:176-178` — "shown in Pro") |
| Count-strip tiles (Leaders / Laggards totals with captions) | MINOR | `cockpit.py:2448-2451` | `strength_pages.py:175-191` — no `C.tile` | FRESH |
| Sector deep-link to `/dash/index?idx=` | MINOR | `cockpit.py:2438-2439` | `strength_pages.py:156` | FRESH |
| Row limits halved: leaders 60→30, laggards 40→20 | MINOR | `cockpit.py:2417-2418` | `strength_pages.py:166` | FRESH |
| State pills (`p-BREAKOUT`/`p-UPTREND`, colour-coded) → plain sentences, so BREAKOUT vs UPTREND no longer reads at a glance | COSMETIC | `cockpit.py:2440-2442`, `:624` | `strength_pages.py:59-63` | FRESH |

### 2c. `momentum-scan` (+ the `/slow` child) — → `/dash/home/strength?view=momentum`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The whole C/A/B veto block dropped** — 4 columns: `Cap-alloc (C)` tier pill · `Insider (A)` (`pledge×N`/`buy×N`) · `Credit (B)` (`ADVERSE×N`) · the derived `Flag` (clear/caution/avoid). The page's stated reason to exist | MAJOR | `src/web/momentum_view.py:86-110`, `:147-152`, `:157-160`, `:175-178`, `:185-186`, `:210-212` | `strength_pages.py:212-216` (9 cols, ends at `Percentile`); `markets_reads.py:323-326` never joins `insider_events`/`credit_rating_events`/`capital_allocation_scores` | RECORDED (`sideways_parity.py:200-201`) |
| **Sort selector `?sort=`** — Risk-adjusted momentum · C-blend 50/50 · Equal-weight ensemble | MAJOR | `momentum_view.py:114`, `:121`, `:187-190` | `strength_pages.py:332-334`; `markets_reads.py:326` hard-codes `ORDER BY riskadj DESC` | RECORDED (`sideways_parity.py:201-202`) |
| **`HI52` (52w range position), `Turn₹cr`, `Percentile` Pro-gated** — all free in classic | MAJOR | `momentum_view.py:171-173`, `:182-183` | `strength_pages.py:214-216`, cells `:204-206` | FRESH |
| **`/dash/momentum-scan/slow` child entirely absent** — the quarterly large-cap LOWVOL_MOM anchor, the only momentum form that survived participation cost | MAJOR | `src/web/slow_rotation_view.py:80-81`, `:159`; cross-link `momentum_view.py:191-192` | no route/body/read under `src/web/home/`; `strength_pages.py:26` `VIEWS` = overview/leaders/momentum/capture | RECORDED (`sideways_parity.py:202`) |
| **Slow-rotation server CSV (`?fmt=csv`, 11 cols)** + anchor/next-rebalance/gated-universe bar + exited-names line + honest-numbers block | MAJOR | `slow_rotation_view.py:96-103`, `:160`, `:165-170`, `:161-164`, `:172`, `:173-183` | absent | RECORDED (same note) |
| `C-blend` column dropped | MINOR | `momentum_view.py:128-129`, `:174`, `:184` | `strength_pages.py:212-216` | RECORDED — a DECISION (`sideways_parity.py:199-201`), not a defect |
| `ENSpct` (equal-weight ensemble percentile) column dropped — read but never rendered; Graphite's Pro "Percentile" is `riskadj_pctile`, a different number | MINOR | `momentum_view.py:128`, `:173`, `:183` | `markets_reads.py:325` selects `ensemble_pctile`; `strength_pages.py:206`, `:216` render only `riskadj_pctile` | FRESH |
| Per-column client sort on the scan table | MINOR | `momentum_view.py:75-83`, `:180-186`, `:210` | `src/web/home/markets_ui.py:74` static `<th>` | FRESH |
| Row limit 60 → 40 | MINOR | `momentum_view.py:132` | `strength_pages.py:211` | FRESH |
| Outbound context links dropped (Glossary · Methodology · Related-lens strip · How-to-read · `/dash/testing`) | MINOR | `momentum_view.py:201-204`, `:217` | `strength_pages.py:217-241` — prose only, no hrefs | FRESH |

### 2c-bis. `/dash/momentum` (the per-stock RS pane the sector drill lands on)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **RS line + RSI-of-RS oscillator two-pane SVG** with dated x-axis, live RSI, 70/50/30 rails, marked divergence pivots + hover gloss | MAJOR | `src/web/momentum_pane.py:71-136`, `:55-67` | absent from `stock_page.py`, `strength_pages.py`, `sectors_pages.py` | FRESH |
| **Benchmark toggle broad / sector / nifty50** for a stock's RS series | MAJOR | `momentum_pane.py:32`, `:281-287`, `:353-354` | `stock_page.py:432-440` shows rank/state/phase/MA flags/slopes vs broad only | FRESH |
| Horizon beat/lag strip (1w·2w·1m·3m·6m·12m) + staged-recovery pill | MINOR | `momentum_pane.py:140-185`, `:151-164` | absent | FRESH |
| Per-stock four-quadrant mini-RRG | MINOR | `momentum_pane.py:256-278`, `:320-323` | absent | FRESH |

### 2d. `capture-map` — `/dash/capture-map` → `/dash/home/strength?view=capture`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The scatter itself is gone** — up-capture × down-capture plot with quadrant tints, the 100/100 market crosshair, the "up = down (pure beta)" diagonal, ALL-WEATHER / WORST-OF-BOTH captions, hover tooltips, inline labels on the 4 best / 3 worst. The module docstring states the two table columns *hide the diagonal* — Graphite ships exactly those two columns | MAJOR | `src/web/capture_map.py:73-131`, `:196`; rationale `:1-8` | `strength_pages.py:269-290` — chips + fence + `U.table` + prose; no SVG in the module | FRESH |
| **Benchmark selector `?den=`** dropped | MAJOR | `capture_map.py:30`, `:174`, `:208` | `strength_pages.py:271` never passes a benchmark; `markets_reads.py:336` defaults it | FRESH |
| Universe narrowed from every index to 18 economic sectors, capped at 20 rows — factor/thematic/bond/ESG indices vanish | MINOR | `capture_map.py:51-65` (no cap, every numerator) | `markets_reads.py:353-357`, `:368` (`limit=20`) | FRESH |
| Counts pills (`N indices` · `N all-weather`) | MINOR | `capture_map.py:189-192` | `strength_pages.py:276-282` | FRESH |
| Glossary `?` popovers on Up-capture / Down-capture / Capture spread | MINOR | `capture_map.py:136-138`, `:196` | `strength_pages.py:274-275` plain header strings | FRESH |
| Row deep-link `Index → /dash/rsband?idx=&den=` (the "is this capture cheap or rich" follow-through) | MINOR | `capture_map.py:144-145` | `strength_pages.py:261` plain text | FRESH |
| 4-way quadrant name changed (`Low-beta`→`Defensive`) and demoted from a coloured pill to a hover `title=` | COSMETIC | `capture_map.py:35-40`, `:147-148` | `strength_pages.py:245-250`, `:265` | FRESH |
| Related-lens strip | COSMETIC | `capture_map.py:219` | `strength_pages.py:269-290` | FRESH |

### 2e. `sectors` — `/dash/sectors` → `/dash/home/sectors`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`1m return` and `3m return` Pro-gated** (free in classic) | MAJOR | `src/web/cockpit.py:2510`, headers `:2524` | `src/web/home/sectors_pages.py:126-127`, cells `:68-69` | FRESH |
| **RS heat strip collapsed 6 horizons → 3** — `18m` and `24m` (base depth / run height) not even queried; `6m` queried but never rendered | MINOR | `cockpit.py:2470-2471`, `:2505`; `src/web/dashboard.py:630-654`; header `cockpit.py:2525` | `markets_reads.py:102-105` (SELECT stops at `slope_12m`); `sectors_pages.py:124` | FRESH |
| `Avg RS rank` of members Pro-gated | MINOR | classic exposed the equivalent breadth roll-up free on the index detail | `sectors_pages.py:128`, cell `:70` | FRESH |
| `Trend` state column dropped — classic showed BOTH the raw trend-state pill AND the weather badge | MINOR | `cockpit.py:2512`, header `:2525` | `sectors_pages.py:60` (weather only); `state` read at `markets_reads.py:105`, unrendered | FRESH |
| Weather badge's `title=` reason list gone ("RS uptrend · 3m slope +2.4 · 1m +1.1 · 61% members RS-up") — the badge no longer explains itself | MINOR | `cockpit.py:197-226`, `:229-236`, `:2506`, `:2513` | `src/web/home/markets_ui.py:128-133` — word only, no `title` | FRESH |
| Count-strip tiles (Rising 3m RS / Falling 3m RS / Breakout) | MINOR | `cockpit.py:2493-2500` | `sectors_pages.py:129-136` | FRESH |
| Sector deep-link to `/dash/index?idx=` (index detail: price trend, RS, constituent roll-up) replaced by the in-page `?sec=` drill only | MINOR | `cockpit.py:2508`, `:2511` | `sectors_pages.py:55-56`; no index-detail route in Graphite | FRESH |
| **A sector renders with NO drill link at all when the `index_signals.index_name` ↔ `stock_signals.primary_sector` join misses** — a dead end | MINOR | classic never needed the join (`src/web/sector_momentum.py:128-140`) | `sectors_pages.py:54-58` (`else: drill = C.esc(label)`) | FRESH |
| Header cross-links "Full RS ranking →" and "⟳ Rotation map (RRG) →" | COSMETIC | `cockpit.py:2519-2520` | `sectors_pages.py:35-41` | FRESH |
| **The RS-momentum ranking view (`0.6·3m + 0.4·6m` composite, rank #, momentum value, percentile bar)** has no Graphite home | MINOR | `cockpit.py:2530-2579` (`render_rs`), linked `:2519` | absent from `sectors_pages.py` / `markets_reads.py` | FRESH |

### 2f. `sector-momentum` — `/dash/sector-momentum` → `/dash/home/sectors?sec=`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`RSI-of-RS` Pro-gated** — free in classic, and it is the ONLY thing the classic page ranks by | MAJOR | `src/web/sector_momentum.py:118`, `:103`, `:47-53` | `sectors_pages.py:99`, cell `:95` | FRESH |
| **Momentum-breadth read Pro-gated AND degraded** — classic: three free percentages with bars (% above RSI 50 · % hot ≥70 · % washed-out ≤30) + constituent count + as-of. Graphite: a Pro-only sentence with two raw counts, no percentages, no bars, no as-of | MAJOR | `sector_momentum.py:71-77`, `:109-115`, `:81-86` | `sectors_pages.py:96-97`, `:106-109` | FRESH |
| **Sector picker chip row with per-sector constituent counts** — the page's navigation | MAJOR | `sector_momentum.py:123-144`, `:182` | `sectors_pages.py:113-143` has no picker; entry only via a standing row whose breadth join matched (`:54-58`) | FRESH |
| Default drill on landing (largest sector by constituent count) | MINOR | `sector_momentum.py:155-168`, `:180-182` | `sectors_pages.py:137-138` (`if sector:`) | FRESH |
| Ordering changed `rsi_of_rs DESC` → `rs_rank DESC` — "which names are driving the turn" replaced by "who is already strongest" | MINOR | `sector_momentum.py:64` | `markets_reads.py:419` | FRESH |
| Constituent list capped at 30 (classic returns every constituent with an RSI) | MINOR | `sector_momentum.py:61-64` | `sectors_pages.py:75`; `markets_reads.py:407` | FRESH |
| Symbol deep-link `→ /dash/momentum?sym=` (the per-stock RS pane, the point of the drill) redirected to the generic stock page, which has no RS pane | MINOR | `sector_momentum.py:101` | `sectors_pages.py:90` → `markets_ui.py:19`, `:32` | FRESH |
| RSI colour coding (hot ≥70 / ≤30 / >50 / else) | COSMETIC | `sector_momentum.py:47-53` | `sectors_pages.py:95` uncoloured | FRESH |
| Route param renamed `?idx=` → `?sec=` (old deep links break) | COSMETIC | `sector_momentum.py:172` | `strength_pages.py:343` | PARTLY RECORDED (`sideways_parity.py:185-187` records the promotion, not the param break) |

### 2g. `sector-economics` — `/dash/sector-economics` → `/dash/home/sectors?tab=economics`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Per-cell drill-down gone** — clicking a (sector, FY) cell listed every constituent company's own value that year as a ranked signed bar chart with per-symbol links, plus the median restated | MAJOR | `src/web/sector_econ_view.py:141-171`, `:174-198`, `:246-249`, `:252-254`, `:202` | `sectors_pages.py:147-170` (`_heat` emits plain `<td>`, no `<a>`); `strength_pages.py:344` reads `metric` only | RECORDED (`sideways_parity.py:208-209`) |
| "Biggest swings" movers panel (top-4 sectors by peak-to-trough range, `FY→FY first→last`, peak/trough, swing size) | MINOR | `sector_econ_view.py:129-137`, `:256-269` | `markets_reads.py:531-534` has no `movers` key; `sectors_pages.py:198-201` | RECORDED (`sideways_parity.py:209`) |
| `bottom_line` computed synthesis ("the strongest sectors of the last decade are X, while Y swings the most…") | MINOR | `sector_econ_view.py:221-226` | `sectors_pages.py:233` static head | FRESH |
| Risk-economics table `Read` column Pro-gated (the same `band_verdict` state label is free on classic `/dash/rsband`) | MINOR | `markets_reads.py:199-201` derives it free | `sectors_pages.py:220`, cell `:184` | FRESH |
| Per-cell hover tooltip (`sector · FY: value`) on populated cells | COSMETIC | `src/web/infographics.py:318`, `:322-323` | `sectors_pages.py:161-167` (`title=` only on the `na` cell) | FRESH |
| Colour-ramp legend (`low ▭▭▭ high`) | COSMETIC | `sector_econ_view.py:245`, `:64-66` | `sectors_pages.py:147-170` | FRESH |
| Coverage count in the honesty fence (`~{n_syms}` tagged names) | COSMETIC | `sector_econ_view.py:276-277` | `sectors_pages.py:206-207`; `n_syms` returned at `markets_reads.py:534`, unused | FRESH |
| Related-lens strip / how-to-read / "share prices vs the other side" cross-link | COSMETIC | `sector_econ_view.py:216`, `:227-228` | `sectors_pages.py:233-239` | FRESH |
| Economics tab structurally unverified (research archive absent locally) | MINOR | classic has the same honest-empty (`sector_econ_view.py:283-288`) | `sectors_pages.py:210-216` | RECORDED (`sideways_parity.py:206-208`) |
---

## 3. Internals · Flows · Events · Attention (W2-A) — 11 classic lenses → 4 Graphite pages

All 11 are marked PORTED (`sideways_parity.py:98-152`). Under the strict standard several are not:
the Free tier lost material blocks to Pro teasers, several boards were row-capped 4–16×, and one
port carries a live correctness defect.

### 3a. `market-internals` — `/dash/market-internals` → `/dash/home/internals`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Delivery / dispersion / coil regime charts are **Pro-blurred**; free in classic | MAJOR | `src/web/market_internals_view.py:330-338`, `:341-349`, `:352-360` (three free `_panel` + `ifx.spark_area`) | `src/web/home/internals_pages.py:483-486` wraps `_internals_regimes` in `C.pro_teaser(...advertise=False)` → blurred in Free (`src/web/home/components.py:133-149`) | FRESH (`sideways_parity.py:98-103` claims regimes carried, no Pro caveat) |
| Exact percentile ordinal + "typical" + trend on the 5 vital signs is Pro-only; Free gets a 3-bucket word | MAJOR | `market_internals_view.py:148-158` (`_phrase(_pctile(...))` → "82nd percentile of 22y") | `internals_pages.py:285-289` Free `band` = high/low/"middle of its range"; `C.ref_chip` is `.pro-more` (`components.py:165-175`) | RECORDED (`sideways_parity.py:99`) |
| 1200-cell clickable daily heat ribbon (drill from **any** day in the window) | MAJOR | `market_internals_view.py:322`, `:326` (`ifx.heat_ribbon(..., cell_link=_dl)`), `:308` (`_dl`) | `internals_pages.py:385-388` — drill chips limited to `sessions[::-1][:20]`; `sessions` is `allrows[-30:]` (`src/web/home/internals_reads.py:165`) | RECORDED (`sideways_parity.py:101-103`) |
| Crisis-anchor rows no longer drill | MINOR | `market_internals_view.py:177-178` (anchor date is an `<a class="mi-dlink">`) | `internals_pages.py:362-363` plain `<td class="l k">` | FRESH |
| Adv / dec / n_eq raw counts absent | MINOR | `market_internals_view.py:150` | `internals_pages.py:274-290` — only `pct_adv` | FRESH |
| Session drill depth cut 12→8 per side, and the selection rule changed (top-%-move among ₹1cr+ traded → top-8 within the day's 400 largest delivered) | MINOR | `market_internals_view.py:204-208` (`LIMIT 12`, `value>10000000`) | `internals_pages.py:394-401`; `internals_reads.py:189-192` (`out[:400]`, `[:limit]`, `limit=8`) | FRESH |
| Default window regressed 5y → 1y | COSMETIC | `market_internals_view.py:243` | `internals_pages.py:506-508` | FRESH |
| "N trading days shown" counter beside the window tabs | COSMETIC | `market_internals_view.py:289-290` | `internals_pages.py:471-472` shows sessions on record, not the window row count | FRESH |
| Glossary deep-link + "how to read" link | COSMETIC | `market_internals_view.py:272`, `:281` | `internals_pages.py:473-497` — none | FRESH |

### 3b. `divergence` — `/dash/divergence` → `/dash/home/internals` (Divergence-watch zone)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Every divergence name is a click-through to its RS-momentum pane; Graphite names are dead text | MAJOR | `src/web/divergence_board.py:80-84` (`href="/dash/momentum?sym="`) | `internals_pages.py:421-423` (`C.esc(name)` in a plain `<td>`) | FRESH |
| Momentum-extremes chips also lose their links | MINOR | `divergence_board.py:112-115` | `internals_pages.py:434-438` | FRESH |
| Bull/bear lists truncated to 10 each (classic unbounded) | MINOR | `divergence_board.py:59-66` | `internals_reads.py:225-226`, `:199` (`limit=10`) | FRESH |
| Per-column counts `(N)` in the header dropped | COSMETIC | `divergence_board.py:92` | `internals_pages.py:424-425` | FRESH |

### 3c. `participants` — `/dash/participants` → `/dash/home/flows`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **FII-vs-retail mirror CHARTS gone** — replaced by one conditional sentence | MAJOR | `src/web/participants_view.py:168-171` (two `ifx.spark_area`, FII net + CLIENT net), `:165-167` | `internals_pages.py:579-584` — a text `gw2-read` only, and only when `p["opposite"]`; no client series is fetched for render | FRESH (`sideways_parity.py:110` claims the mirror ported) |
| Stance-ratio chart regressed to the **40-day window the classic module explicitly replaced** | MAJOR | `participants_view.py:87-90` (docstring: "replacing the amnesiac 40-day sparkline"), `:154` (full ~2.5y, baseline 1.0) | `internals_pages.py:574-578` draws `p["ratio_series"]` = `ratio_series[-hist_n:]`, `hist_n=40` (`internals_reads.py:255`, `:306`) | FRESH |
| Free loses the percentile extremity read-out ("more bearish than X% of the last N days") | MAJOR | `participants_view.py:117-140` (free text), `:156` (`ifx.pct_gauge`) | `internals_pages.py:566-568` — percentile only inside `C.ref_chip` = `.pro-more` | FRESH |
| 8-row FII index-futures history table is Pro-only | MINOR | `participants_view.py:264-276` (free) | `internals_pages.py:594-601` (`C.pro_more`) | RECORDED (`sideways_parity.py:111-112`) |
| Matrix loses the bipolar magnitude bars (values only) | COSMETIC | `participants_view.py:43-54` (`_cell` scaled tinted bar) | `internals_pages.py:585-593` | FRESH |
| Index-option-bias formula footnote dropped | COSMETIC | `participants_view.py:278-281` | `internals_pages.py:603-606` | FRESH |

### 3d. `fno` — `/dash/fno` → `/dash/home/flows` (F&O board)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Free sees 12 of ~190-220 names**; the full cross-section is Pro-blurred. Classic serves the whole universe free | MAJOR | `src/web/fno_context_view.py:320` (all rows), `:367` | `internals_pages.py:645` (`_fno_table(board, 12)`), `:647-649` (`C.pro_teaser(_fno_table(board, 200, pro=True))`) | FRESH (`sideways_parity.py:114-119` claims the board ported, no Pro caveat) |
| `Fut OI` (raw book size) column dropped from table **and** CSV | MINOR | `fno_context_view.py:272-273`, `:292`; CSV `:304-305` | `internals_pages.py:627-629`; CSV header `:698-700` omits `fut_oi`/`und`/`max_pain` | FRESH |
| `basis` column dropped from the table (survives only in CSV) | MINOR | `fno_context_view.py:275`, `:295-296` | `internals_pages.py:627-629`; only `:696`/`:699` | FRESH |
| "book size" (`sort=oi`) not offered in the UI though the read supports it | MINOR | `fno_context_view.py:356-357` | `internals_pages.py:634-636` (5 sorts); `internals_reads.py:331` still lists `"oi"` | FRESH |
| Percentile heat-ramp cells + the 0/50/100 ramp legend | MINOR | `fno_context_view.py:62-72`, `:284-286`, `:363-365` | `internals_pages.py:621-625` plain numbers, no legend | FRESH |
| Reality-check thresholds drifted (fresh-long 40→30 and its `streak>=2` requirement dropped; extreme-PCR 92→95) → fewer callouts fire | MINOR | `fno_context_view.py:239-240`, `:249` | `internals_reads.py:428-429`, `:435` | FRESH |
| CSV is not an attachment download | COSMETIC | `fno_context_view.py:333-334` | `internals_pages.py:246-252` | FRESH |

### 3e. `actions` — `/dash/actions` → `/dash/home/events` (Going ex)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Just-went-ex + restructure context is Pro-gated | MAJOR | `src/web/actions_view.py:122-150`, `:190` (free) | `internals_pages.py:767-769` (`C.pro_more`) | RECORDED (`sideways_parity.py:121-122`) |
| …and its depth is cut ~16× under that gate: 30d/200 rows → 14d/12 rows; security_events 180d/40 → 14d/6 | MAJOR | `actions_view.py:124-127`, `:128-130` | `internals_reads.py:475-486` | FRESH |
| `record_date` column dropped from the calendar table (survives only in CSV) — load-bearing for buyback/dividend eligibility | MINOR | `actions_view.py:114` | `internals_pages.py:765-766`; only `:1082`/`:1084` | FRESH |
| "Names going ex · FLAG_DAYS" flagged-cohort tile dropped | MINOR | `actions_view.py:84` (`CA.flagged_symbols`) | `internals_pages.py:739-744` | FRESH |
| Full details on hover (`title=`); Graphite truncates with no tooltip | MINOR | `actions_view.py:113` | `internals_pages.py:758` (`[:80]`, no title) | FRESH |
| Per-day heading with "N going ex" counts | COSMETIC | `actions_view.py:117` | `internals_pages.py:751-752` | FRESH |
| Per-type coloured chips → one grey pill | COSMETIC | `actions_view.py:30-39` | `internals_pages.py:753-756` | FRESH |
| Default window regressed 60d → 30d | COSMETIC | `actions_view.py:155` | `internals_pages.py:1062-1066` | FRESH |
| `?sym=` accepted but invisible: no UI, no echo in the heading, not in the CSV link | COSMETIC | `actions_view.py:154`, `:188` | `internals_pages.py:1067`, `:1025`, `:770` | FRESH |

### 3f. `results-reactions` — `/dash/results-reactions` → `/dash/home/events` (Results)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Stale-tape banner gone** — no warning when delivery/price data is N weekdays behind | MAJOR | `src/web/results_reactions.py:188-212` (`_tape_lag`), `:292-300` (`_stale_banner`), `:449` | `internals_pages.py:774-832` — `results_board` returns `meta` (`internals_reads.py:548`) but nothing consumes `tape_max_trade_date` | FRESH |
| CAR fan SVG (cohort mean + IQR + fresh reporters at +22d) | MAJOR | `results_reactions.py:215-289`, `:465` | absent from `_results_block` (`internals_pages.py:774-832`) | RECORDED (`sideways_parity.py:128-129`) |
| Published event-brief cards | MAJOR | `results_reactions.py:138-185`, `:464` | absent | RECORDED (`sideways_parity.py:128-129`) |
| Per-cell descriptive base-rate annotation ("hist +7.6%/60d (n=235)") | MINOR | `results_reactions.py:66-77`, `:427` | `internals_pages.py:796-808` returns `(lbl, cls)` only | FRESH |
| Run-specific cut values (SUE p80 / Deliv p67) from snapshot meta | MINOR | `results_reactions.py:434`, `:453` | `internals_pages.py:718-723` — `_PEAD_FENCE` is a static string; meta unused | FRESH |
| `Q/A` (`ptype`) column dropped | MINOR | `results_reactions.py:423`, `:472` | `internals_pages.py:824-826` | FRESH |
| Row cap 500 → 120 | MINOR | `results_reactions.py:406` | `internals_reads.py:510` | FRESH |
| Upcoming-results weekday heat grid (2×5, tint = evening load) → flat 14-row table | MINOR | `results_reactions.py:344-369` | `internals_pages.py:776-782` | FRESH |
| Snapshot `generated_at` provenance footer | COSMETIC | `results_reactions.py:433`, `:479-480` | `internals_pages.py:827-832` | FRESH |
| No CSV for the results board though the page advertises a server CSV | MINOR | n/a (classic has none) — house rule at `internals_pages.py:23-25` | `internals_pages.py:1079-1085` `format=csv` returns CA-calendar rows only | FRESH |

### 3g. `event-cadence` — `/dash/event-cadence` → `/dash/home/events`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Index-membership universe filter (All / Nifty 50 / 100 / 500) | MAJOR | `src/web/seasonal_events_view.py:282-283`, `:379-380`, `:287-298`, `:318` | `internals_pages.py:836-838` (event-type seg only); `internals_reads.event_cadence` has no members arg (`:573-605`) | RECORDED (`sideways_parity.py:132-133`) |
| Cadence CSV lost (classic CSV honours evt/idx/cap/horizon) | MINOR | `seasonal_events_view.py:362-371`, `:441-451`, `:417` | `internals_pages.py:1079-1085` — the page's only CSV is the CA calendar | FRESH |
| `cap` (overdue bound) and `horizon` no longer URL-tunable | MINOR | `seasonal_events_view.py:442`, `:329-335`, `:373-374` | `internals_reads.py:573` accepts them, but `internals_pages.py:1029` passes `evt` only; route `:1055-1074` never reads them | FRESH |
| Row cap 400 per section → 40 | MINOR | `seasonal_events_view.py:317` | `internals_reads.py:574`, `:596-599` | FRESH |
| Cross-links to the two announced calendars | COSMETIC | `seasonal_events_view.py:428-430` | `internals_pages.py:868-871` names them, does not link | FRESH |

### 3h. `buyback-calc` — `/dash/buyback-calc` → `/dash/home/events`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Acceptance-ratio sensitivity table (20/33/50/66/100%) removed** — the classic module's stated substitute for refusing to fabricate a prior | MAJOR | `src/web/buyback_calc.py:157-166`; rationale `:19-21`, `:203-206` | `internals_pages.py:874-891` (`_BB_JS` computes one scenario), `:906-911` (six static tiles) | FRESH |
| "Days locked" input and the **annualized return** output removed | MAJOR | `buyback_calc.py:218`, `:143`, `:155` | `internals_pages.py:899-905` (five inputs), `:907-909` | FRESH |
| Net % (return on capital) output removed — only ₹ net remains | MINOR | `buyback_calc.py:142`, `:154` | `internals_pages.py:883-885` | FRESH |
| Click-a-parsed-price-to-load-the-calculator interaction removed | MINOR | `buyback_calc.py:168` (`bbfill`), `:182` | `internals_pages.py:917` | FRESH |
| "shares bought @ CMP" / "returned" derived counts removed | MINOR | `buyback_calc.py:150-151` | `internals_pages.py:907` | FRESH |
| Buyback tape depth 30 rows / 110-char details → 12 rows / 70-char | MINOR | `buyback_calc.py:74`, `:189` | `internals_reads.py:489`; `internals_pages.py:918` | FRESH |
| Explicit ₹2L over-cap warning banner → an inline tile line | COSMETIC | `buyback_calc.py:220-222`, `:136-137` | `internals_pages.py:888-889` | FRESH |

### 3i. `surveillance` — `/dash/surveillance` → `/dash/home/events`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **"Under surveillance now" membership lists gone** (per-framework symbol lists with stage, dossier links, "+N more") — only counts survive | MAJOR | `src/web/surveil_view.py:117-132` (`_current`), `:170-172` | `internals_pages.py:953-959` renders `len(cur[fw])` into tiles; no list is emitted | PARTLY RECORDED (`sideways_parity.py:140-141` says "counts"; the loss is implied, never stated as NOT carried) |
| Tape depth 400 → 40 events | MINOR | `surveil_view.py:112` | `internals_reads.py:608`, `:630` | FRESH |
| `?sym=` tape filter dropped | MINOR | `surveil_view.py:101-102`, `:136`, `:168` | `internals_pages.py:1067`, `:1025`, `:1030` (`R.surveillance_tape(conn)` takes no symbol) | FRESH |
| Restriction-UP / restriction-DOWN / band-tightening count tiles dropped | MINOR | `surveil_view.py:82-89` | `internals_pages.py:948-959` | FRESH |
| Per-framework chip colouring (ASM-LT/ASM-ST/GSM/BAND) → one grey pill | COSMETIC | `surveil_view.py:31-36`, `:68-70` | `internals_pages.py:968` | FRESH |

### 3j. `band-locks` — `/dash/band-locks` → `/dash/home/events`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **🔴 CORRECTNESS: direction case mismatch — every row renders "▼ lower" and both up/down tiles read 0.** The engine emits `"UP"`/`"DOWN"`; the Graphite read/render compare against lowercase | MAJOR (live defect) | `src/automation/band_lock.py:111`, `:151`; classic compares `"UP"` at `src/web/bandlock_view.py:60-61`, `:82-83` | `internals_reads.py:660-661` (`s.get("dir") == "up"`); `internals_pages.py:1005` (`s.get("dir") == "up"`) | FRESH |
| `Close` (last_close) column dropped | MINOR | `bandlock_view.py:93` | `internals_pages.py:1014-1015` | FRESH |
| "Longest streak" tile and the "locked at band today" total dropped | MINOR | `bandlock_view.py:62`, `:64`, `:68` | `internals_pages.py:995-1002` | FRESH |
| ⚑ flag marker on rows at/over `FLAG_MIN_STREAK` | MINOR | `bandlock_view.py:84`, `:89` | `internals_pages.py:1006-1012` | FRESH |
| Board truncated to 30 streaks (classic shows every active lock) | MINOR | `bandlock_view.py:76-98` | `internals_reads.py:635`, `:657` | FRESH |
| Cross-link to the surveillance lens | COSMETIC | `bandlock_view.py:124` | `internals_pages.py:1017-1020` | FRESH |

### 3k. `attention` — `/dash/attention` → `/dash/home/attention`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Acknowledge / dismiss (per-alert ✕ and "dismiss all") | MAJOR | `src/web/attention_view.py:251`, `:312-314`, `:491-508` | `internals_pages.py:1181-1193` read-only; stated `:1199-1202` | RECORDED (`sideways_parity.py:150-152`) |
| Cookie "since you last looked" brief | MAJOR | `attention_view.py:337-364`, `:426-433`, `:485-487` | absent from `_attention_body` (`internals_pages.py:1205-1212`) | RECORDED (`sideways_parity.py:150-152`) |
| **Queue truncated to 30 rows** (classic renders 200 and states "showing top N of M") | MAJOR | `attention_view.py:51` (`_PAGE_LIMIT = 200`), `:381`, `:449-452` | `internals_reads.py:670` (`limit=30`); `internals_pages.py:1206` never overrides (CSV alone raises it to 500 at `:1231`) | FRESH |
| **Alert-rail severity + valence filter chips gone** | MAJOR | `attention_view.py:261-289` (`?asev=`/`?aval=`), `:411-417` | `internals_pages.py:1174-1202` — no chips; route `:1215-1225` reads only `as_of`/`lens`/`format` | FRESH |
| Replay date-picker form gone — `?as_of=` is URL-only | MINOR | `attention_view.py:442-445` | `internals_pages.py:1148-1153` (note only, no input) | FRESH |
| Alert-rail `Note` column dropped | MINOR | `attention_view.py:320`, `:325-326` | `internals_pages.py:1197-1198` | FRESH |
| Queue loses the detected-UTC clock column and the magnitude bar | MINOR | `attention_view.py:162`, `:169-172`, `:468-471` | `internals_pages.py:1125-1126`, `:1123` | FRESH |
| Batch-history table is Pro-only and reshaped (per-lens columns → one concatenated string) | MINOR | `attention_view.py:179-196` | `internals_pages.py:1163-1165`, `:1157-1160` | FRESH |
| "Lenses that have emitted" / "Serving batch" tiles dropped | COSMETIC | `attention_view.py:202-206` | `internals_pages.py:1132-1138` | FRESH |
| Magnitude-normalisation + PIT two-clock fence text dropped | MINOR | `attention_view.py:460-476` | `internals_pages.py:1097-1103` keeps the "never a recommendation" half only | FRESH |
| Rail render cap 24→20 and no "showing X of Y" overflow note | COSMETIC | `attention_view.py:327-332` | `internals_reads.py:718`; `internals_pages.py:1195-1196` | FRESH |
---

## 4. Seasonal · Patterns · Anatomy · Own-history · Compare (W2-C) — 10 classic lenses → 5 Graphite routes

W2-C recorded per-block SHIPPED/OUTSTANDING notes. Those are folded in below and **verified against
source**; the verification discrepancies are listed at the end of this section.

### 4a. `seasonal-calendar` — `/dash/seasonal-calendar` → `/dash/home/seasonal?view=calendar`

The one W2-C key marked PORTED. Verified: the note is accurate. Residual detail only.

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| `?cap=` row-cap control (5–500, default 60) | MINOR | `src/web/calendar_conditioning_view.py:213-219`, `:179` | cap hardcoded 40 — `src/web/home/seasonal_pages.py:316` (CSV uses 500 at `:381`) | FRESH |
| `med_turn` column in the CSV export | MINOR | `calendar_conditioning_view.py:46-47` | 7-col `_CSV_COLS` — `seasonal_pages.py:368-369` | FRESH |
| Glossary popover on every metric header | MINOR | `calendar_conditioning_view.py:38-43`, `:185-186` | plain header strings — `seasonal_pages.py:356-357` | FRESH |
| "N names · as-of · showing top N by \|key\|" summary line | COSMETIC | `calendar_conditioning_view.py:171-173` | as-of only, inside the prov chip — `seasonal_pages.py:353` | FRESH |
| Honest-empty on a missing snapshot vs falling back to demo rows | COSMETIC | `calendar_conditioning_view.py:147-152` | `DEMO_CALENDAR` fallback — `seasonal_pages.py:319-321` (labelled `sample`) | FRESH |

### 4b. `seasonal-tape` — `/dash/seasonal-tape` → `?view=tape` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **🔴 CORRECTNESS: the ISO-week script grid can never render** — the reader filters `axis IN ('month','week','weekday')` but the engine persists `'iso_week'`, so `script.get("week")` is always empty and the week cell-drill is unreachable | MAJOR (live defect) | `src/automation/seasonal_tape.py:104`; classic queries `axis='iso_week'` at `src/web/seasonal_view.py:216-218` | `src/web/home/w2_reads.py:34`, `:65`; dead blocks `seasonal_pages.py:154-159`, `:165-169` | RECORDED-BUT-FALSE (`sideways_parity.py:219-220` lists the ISO-week grid as SHIPPED) |
| **Forward outlook is FREE in classic, Pro-gated in Graphite** | MAJOR (pro-gating regression) | `seasonal_view.py:919-945` (no tier code anywhere in the module) | `seasonal_pages.py:187-196` (`C.pro_more`/`C.pro_teaser`); gate `components.py:126-130`, `:133-143` | FRESH — the ledger cites the Pro band as a positive without recording the regression |
| **25-year year×month stack heat grid** | MAJOR | `seasonal_view.py:817-831` | only a single-cell year stack — `seasonal_pages.py:81-102`, `:168-169` | FRESH (under-recorded) |
| **52-week year×ISO-week stack** | MAJOR | `seasonal_view.py:848-870` | absent | FRESH (under-recorded) |
| Weekday year×weekday stack | MINOR | `seasonal_view.py:885-904` | absent | FRESH (under-recorded) |
| Monthly + weekly consolidation panels (ranked bars, #rank, ★) | MAJOR | `seasonal_view.py:833-847`, `:871-884`, `_month_bars:528-593` | absent | RECORDED |
| Per-cell placebo "why grey" block (emp_p_block/phase, null_p95, FDR narrative) | MAJOR | `seasonal_view.py:654-722`, `:785` | absent | RECORDED |
| `scope=stock` + free-typed symbol search + in-memory compute | MAJOR | `seasonal_view.py:363-378`, `:1143-1181` | `_SCOPES` = index/sector only — `seasonal_pages.py:44`, `:105-107` | RECORDED |
| `cal=fy\|cy` calendar-order toggle | MINOR | `seasonal_view.py:1220-1225` | `FISCAL_ORDER` defined but unused (`w2_reads.py:38`); always `CAL_ORDER` (`seasonal_pages.py:145`) | FRESH |
| Entity picker truncated to 14 | MINOR | `seasonal_view.py:1217-1219` (all entities) | `ents[:14]` — `seasonal_pages.py:123` | FRESH |
| Outlook detail: edge pp, down-years avg/worst, 🟢/🟡/⚪ light | MINOR | `seasonal_view.py:926-937` | Slot/Horizon/Base/band/Read only — `seasonal_pages.py:177-189` | FRESH |
| Per-cell `mechanism` + `gate_flags` disclosure | MINOR | `seasonal_view.py:786` | absent | FRESH |
| First-run 4-step strip + the two "read it right" deltas | MINOR | `seasonal_view.py:1060-1117`, `:1206` | one `_FENCE` string — `seasonal_pages.py:40-42` | FRESH |
| Index/sector → "Scan the stocks in X" constituent CTA | MINOR | `seasonal_view.py:1228-1238` | absent | FRESH |
| 4-bullet honesty fence (PIT · frozen hash · strict certification · residual construction) | MINOR | `seasonal_view.py:974-1001` | sha256 note only — `seasonal_pages.py:198-204` | FRESH |
| Event-cadence lens embedded in the tape | MINOR | `seasonal_view.py:911-918` | re-homed to `/dash/home/events` | RECORDED (other key, `sideways_parity.py:130-133`) |

### 4c. `seasonal-screen` — `/dash/seasonal-screen` → `?view=screen` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`scope=stock` — the classic DEFAULT scope — is unreachable** | MAJOR | `src/web/seasonal_screen_view.py:173-176`, `:180` | coerced to index — `seasonal_pages.py:44`, `:222-223`; read defaults `scope="index"` (`w2_reads.py:132`) | FRESH (the note records only the `index=` filter) |
| **No scope selector UI at all** (Stock / Index / Sector tabs) | MAJOR | `seasonal_screen_view.py:336-338`, `:361` | month + lean chips only — `seasonal_pages.py:221-229` | FRESH |
| `min_years` history-floor chips (≥15 / ≥10 / ≥5 / any) | MAJOR | `seasonal_screen_view.py:358-360`, `:364` | no floor control; the read has no `min_years` — `w2_reads.py:132-164` | FRESH |
| `index=<Name>` constituent filter (+ header, coverage count, clear chip) | MAJOR | `seasonal_screen_view.py:138-152`, `:194-196`, `:293-295`, `:304-306`, `:339-341` | absent | RECORDED |
| "Strength t" (residual t-stat) sort dimension | MINOR | `seasonal_screen_view.py:222-232`, `:276-279`, `:445` | absent | RECORDED |
| Per-name month-rank column (#k of 12) | MINOR | `seasonal_screen_view.py:212-220`, `:400-405`, `:446` | absent | RECORDED |
| Symbol/entity search box (`q=`) | MINOR | `seasonal_screen_view.py:234`, `:365-374` | absent | FRESH |
| Click-to-sort headers (sym / hit / z / years) | MINOR | `seasonal_screen_view.py:376-384`, `:441-448` | fixed order — `seasonal_pages.py:253` | FRESH |
| Third view mode "Lookup (A–Z)" (`lean=all`) | MINOR | `seasonal_screen_view.py:347-355` | hot/cold only — `seasonal_pages.py:228` | FRESH |
| Entity name is not a link (no dossier / tape deep-link) | MINOR | `seasonal_screen_view.py:388-389`, `:416` | plain escaped text — `seasonal_pages.py:238` | FRESH |
| Certification status column (certified / grey-not-gated) | MINOR | `seasonal_screen_view.py:396`, `:423` | `colored` read but never rendered — `w2_reads.py:143` | FRESH |
| Row cap 300 + "showing 1–N of TOTAL" | MINOR | `seasonal_screen_view.py:70`, `:289`, `:450-451` | `limit=40` — `seasonal_pages.py:219`, `w2_reads.py:132` | FRESH |
| Thin-history coverage explainer + honest 0-row guidance | MINOR | `seasonal_screen_view.py:319-328`, `:453-469` | absent | FRESH |
| Raw `k/n` counts beside the hit-% | COSMETIC | `seasonal_screen_view.py:390-391` | percent only — `seasonal_pages.py:240` | FRESH |
| _Server CSV_ | **Graphite ADDITION** — classic has no CSV path | — | `seasonal_pages.py:368-381` | — |

### 4d. `seasonal-divergence` — → `?view=divergence` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| "Where THIS year diverges from its usual path" (seasonal_stack overlay) | MAJOR | `seasonal_screen_view.py:513-528`, `:606-624` | absent | RECORDED |
| Two-row co-movement heat grid (A vs B, all months) | MAJOR | `seasonal_screen_view.py:580-589` | plain numeric table — `seasonal_pages.py:286-304` | FRESH |
| "N of M months same direction · Pearson r" statistic | MAJOR | `seasonal_screen_view.py:155-168`, `:576-583` | absent | FRESH |
| A−B divergence heat ribbon + top-3 largest gaps | MINOR | `seasonal_screen_view.py:591-604` | gap column only — `seasonal_pages.py:292` | FRESH |
| `cal=fy\|cy` toggle | MINOR | `seasonal_screen_view.py:532-533`, `:566-571` | absent | FRESH |
| Certified-count note (A: n of 12, B: n) | MINOR | `seasonal_screen_view.py:626-634` | absent | FRESH |
| Pickers capped at 8 (classic lists all, `BROAD_INDICES`-canon ordered) | MINOR | `seasonal_screen_view.py:481-498`, `:560-565` | `ents[:8]` — `seasonal_pages.py:278-284` | FRESH |

### 4e. `harmonic-scan` — `/dash/harmonic` → `/dash/home/patterns?view=harmonic` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| `tf=d\|w\|m` multi-timeframe live scan + pills | MAJOR | `src/web/harmonic_view.py:97-116`, `:152-156` | daily snapshot only — `w2_reads.py:243-257` | RECORDED |
| `?refresh=1` live recompute | MINOR | `harmonic_view.py:99`, `:106`, `:143`, `:148` | absent | RECORDED |
| Live-scan fallback when the snapshot is missing | MINOR | `harmonic_view.py:111` (`HS.scan(...)`) | demo sample rows — `src/web/home/patterns_pages.py:117-119` | FRESH |
| `universe=` parameter/selector | MINOR | `harmonic_view.py:97`, `:106`, `:180` | hardcoded `nifty500` — `w2_reads.py:243`, `patterns_pages.py:114` | FRESH |
| OOS-benchmark tooltips on the side tags + related-lens strip | COSMETIC | `harmonic_view.py:121-123`, `:165-166` | static pills — `patterns_pages.py:47-53` | FRESH |

### 4f. `wolfe-scan` — `/dash/wolfe/scan` (+ `/dash/wolfe/trades`) → `?view=wolfe` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The entire `/dash/wolfe/trades` board** — 19 columns, 12 server-side filters, sticky-filter cookie, server CSV, "since you last looked" diff, ladder SVG, liquidity/RS/risk/R:R | MAJOR | `src/web/wolfe_trades_view.py:443-663`; filters `:514-531`; CSV `:362-385`, `:652`; sticky `:38-60`; diff `:493-499`; ladder `:247-260` | no route, no read | RECORDED but badly understated (`sideways_parity.py:246-247` reduces it to "the Fresh-setups / Open-trades toggle") |
| §B quality components A/B/C/F/G/H/I/D + the Q column | MAJOR | `src/web/wolfe_view.py:329-331`, `:352-353`, `:384-387` | absent | RECORDED |
| `?asof=` point-in-time replay | MAJOR | `wolfe_view.py:294`, `:302`, `:311` | absent | FRESH |
| Three sort dimensions (q / age / up) | MINOR | `wolfe_view.py:314-319`, `:379-383` | fixed `in_zone DESC, age ASC` — `w2_reads.py:234-235` | RECORDED |
| EPA target-price column (selected but never rendered) | MINOR | `wolfe_view.py:345`, `:352` | `epa` in SELECT (`w2_reads.py:233`), dropped in render (`patterns_pages.py:85-92`) | FRESH |
| ★ EDGE winner-profile badge / `is_winner_profile` | MINOR | `wolfe_view.py:267-269`, `:323-325` | absent | FRESH |
| `universe=inclusive` selector | MINOR | `wolfe_view.py:292`, `:350-351`, `:395` | hardcoded `nifty500` — `w2_reads.py:223` | FRESH |
| `fresh=N` age window (1–180) | MINOR | `wolfe_view.py:293`, `:311`, `:394`, `:396` | absent | FRESH |
| `?refresh=1` live recompute | MINOR | `wolfe_view.py:295`, `:307-311`, `:391` | absent | FRESH |
| Row click → the wave chart (`/dash/wolfe?sym=&pick=winner`) | MINOR | `wolfe_view.py:337` | symbol → stock hub only — `patterns_pages.py:83`, `src/web/home/w2_kit.py:46-52` | FRESH |
| Methodology deep-link (`/dash/strategy-ref?p=wolfe-wave`) | COSMETIC | `wolfe_view.py:369` | absent | FRESH |

### 4g. `move-anatomy` — `/dash/move-anatomy` → `/dash/home/anatomy` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **🔴 METHOD CHANGE, undisclosed: the excursion envelope uses MEAN in Graphite vs MEDIAN in classic** — the classic page explicitly warns "Medians, not means — means are pulled by the big-winner tail" | MAJOR | `src/web/move_anatomy_view.py:112-125`, `:236-238` | `avg(mfe_6m) … avg(mae_6m)` — `w2_reads.py:329-336`; page copy does not disclose it — `src/web/home/anatomy_pages.py:73-78` | FRESH |
| 15 curated precursors + the "Group"/family column → 9, family carried but never rendered | MAJOR | `move_anatomy_view.py:43-59`, `:221-228` | `PRECURSORS` = 9 rows (`w2_reads.py:265-275`); family unused (`anatomy_pages.py:48-59`) | RECORDED (the note says "~20-precursor family"; classic actually carries 15, Graphite 9 — direction right, count wrong) |
| "Reached +50% within 6 months" rate | MINOR | `move_anatomy_view.py:120-125`, `:190-194` | not read, not shown | RECORDED |
| Ranked trait table with raw "Before moves / Normal day" averages | MINOR | `move_anatomy_view.py:211-228` | bars only — `anatomy_pages.py:48-59` | RECORDED (partial) |
| `n_events` / `n_baseline` headline counts (166K events vs baseline, 2011→2026) | MINOR | `move_anatomy_view.py:139`, `:146-147` | only a `built_at` note — `anatomy_pages.py:123-124` | FRESH |
| Diverging-bars legend + floating gain-vs-pain bar visual | COSMETIC | `move_anatomy_view.py:175-178`, `:207` | plain table — `anatomy_pages.py:73-78` | FRESH |

### 4h. `self-history` — `/dash/self-history` → `/dash/home/own-history` (already DEFERRED)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| 3-year self-percentile map over split/bonus-ADJUSTED OHLC (price · momentum · delivery · turnover · coil), estate-wide | MAJOR | `src/web/self_history_view.py:112-133`, `:144-233` | re-derived from stored `stock_signals` ratios — `w2_reads.py:356-398` | RECORDED (explicitly disclosed) |
| Cross-sectional peer lens + the gold-ring two-lens confluence | MAJOR | `self_history_view.py:96-109`, `:229-232`, `:354-360` | absent | RECORDED |
| Five-universe selector (N50 / Next50 / N500 / Mid100 / Small100) | MAJOR | `self_history_view.py:49-55`, `:204-218`, `:437-438` | top-40 by turnover, no selector — `w2_reads.py:377-383` | RECORDED |
| **Auto "what stands out" chips** — most coiled · hollow high · high-range-fading-momentum · strongest two-lens agreement | MAJOR | `self_history_view.py:286-328`, `:452` | absent | FRESH |
| CSV export | MINOR | `self_history_view.py:375-383`, `:407-409`, `:443-444` | no `format=csv` path — `anatomy_pages.py:218-241` | FRESH |
| "Coil"/range percentile absent from the estate-wide map | MINOR | `self_history_view.py:65` | `OWN_METRICS` has no range column — `w2_reads.py:356-363` | FRESH |
| 0–100 heat ramp + legend (coloured cells, dual numbers) | MINOR | `self_history_view.py:70-84`, `:260-275`, `:446-451` | plain bar rows — `anatomy_pages.py:192-199` | FRESH |
| Sort on all 5 columns + by symbol via clickable headers | MINOR | `self_history_view.py:242-248`, `:332-339` | 4 chips, `OWN_METRICS[:4]` — `anatomy_pages.py:146-149` | FRESH |
| Raw context columns (vs hi · 3m % · dlv% · ₹cr) | MINOR | `self_history_view.py:341-344`, `:361-369` | absent | FRESH |

### 4i. `compare` — `/dash/compare` → `/dash/home/compare` (already DEFERRED; classic route byte-frozen)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| `mode=ratio` + `den=` denominator switch (vs Nifty 50 / 500) | MAJOR | `src/web/dashboard.py:7908-7909`, `:7923`, `:7979-7987`, `:8168-8180` | rebase only — `src/web/home/compare_pages.py:90-114` | RECORDED |
| Searchable picker (ticker prefix ≥2, company name ≥4, ETFs, staged multi-add) | MAJOR | `dashboard.py:8043-8068`, `:8225-8315` | single text input — `compare_pages.py:132-138` | RECORDED |
| **Interactive chart** (lightweight-charts: pan-to-re-anchor, hover value read-out, on-chart labels) | MAJOR | `dashboard.py:8186-8214` | static SVG polyline — `compare_pages.py:48-87` | FRESH |
| `base=0` mode | MINOR | `dashboard.py:7910`, `:7924`, `:8190` | absent | RECORDED |
| Line cap 12 → 6 | MINOR | `dashboard.py:7855` (`_COMPARE_MAX = 12`) | `w2_reads.py:452` (`COMPARE_MAX = 6`) | FRESH |
| 📅 Pin-anchor date + ⟳ Fluid reset | MINOR | `dashboard.py:8181-8184`, `:8206` | absent | FRESH |
| One-click presets (Sector vs market · Sector race · RS head-to-head) | MINOR | `dashboard.py:8070-8098` | absent | FRESH |
| "Max" (`r=0`) full-history window | MINOR | `dashboard.py:7929`, `:8166` | 63–1260 only — `compare_pages.py:33` | FRESH |
| Per-series missing-data note ("No level/ratio data for X") | MINOR | `dashboard.py:8145-8157` | silently dropped — `w2_reads.py:513`, `:522` | FRESH |
| Index picker shows only the first 10 of the valid universe | MINOR | `dashboard.py:7934-7935`, `:8029-8042` | `valid_idx_all[:10]` — `compare_pages.py:143` | FRESH |

### 4j. Verification discrepancies found in the recorded W2-C notes

1. **WRONG:** `sideways_parity.py:219-220` lists the **ISO-week script grid as SHIPPED**. It is structurally dead (axis-key mismatch, see 4b row 1).
2. **UNRECORDED REGRESSION:** `sideways_parity.py:221-222` cites the "Pro forward-outlook band" as a shipped positive without recording that the identical panel is FREE on classic.
3. **UNDER-RECORDED (seasonal-tape):** the OUTSTANDING list names only the consolidation panels; the three per-year STACK grids (25-year month, 52-week, weekday) — the tape's primary evidence blocks — are also absent.
4. **UNDER-RECORDED (seasonal-screen):** the note treats `index=` as the scope gap; in fact `scope=stock` (the classic default) is unreachable and no scope selector renders at all.
5. **UNDER-RECORDED (wolfe-scan):** the note reduces the missing surface to a toggle; the unported object is the whole `/dash/wolfe/trades` board. `?asof=` PIT replay is also missing and unmentioned.
6. **UNSTATED METHOD CHANGE (move-anatomy):** MEDIAN → MEAN envelope, against the classic page's own warning; disclosed nowhere.
7. **INFLATED FIGURE:** the move-anatomy note says "~20-precursor family"; classic carries 15, Graphite 9.
8. **UNDER-RECORDED (compare):** the 12→6 line-cap reduction is not in the outstanding list.
9. **CONFIRMED ACCURATE** (sampled): the whole `seasonal-calendar` PORTED note · `seasonal-divergence` outstanding · `harmonic-scan` outstanding · `self-history` outstanding · `compare` outstanding.
---

## 5. Tracker (W3-B) — 6 classic surfaces → `/dash/home/tracker*`

Recorded as the "first fully-accounted workspace" (5 PORTED + 1 merge-DROP). Verified: the recorded
residuals are real, but each page also lost columns and controls the notes do not mention, and the
`model-books` merge claim is contradicted by the code.

### 5a. `dashboard` — `/dash/dashboard` → `/dash/home/tracker`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| 🔔 **Alerts-firing block** (per-name fired-rule chips over open + watch) | MAJOR | `src/web/dashboard.py:5033-5047`, `:5159-5171`; rule engine `:3969-4014` (10 rule types) | absent — `src/web/home/tracker_pages.py:399-411` renders 6 zones, none is alerts | RECORDED (`sideways_parity.py:298`) |
| ⚡ **Ready-to-act block** (zero-config strong-setup read on watch rows) | MAJOR | `dashboard.py:5044-5047`, `:5152-5158`; logic `:4016-4036` | absent | FRESH (the note names only "alerts-firing") |
| **Attention flags reduced 6 → 4** — Graphite drops `dist` (🔴 DISTRIBUTION character), `rs_decay` (RS dropped ≥10 vs the frozen entry snapshot) and `conv_drop` (conviction drift ≥10 vs entry) | MAJOR | `dashboard.py:3537-3544` (`_HEALTH_FLAG_LABEL`), `:3547-3573` (`_thesis_flags`) | `src/web/home/tracker_reads.py:276-315` (`_ATT_ORDER`/`attention()`) — no character, no then-vs-now drift | FRESH |
| **Contributors/detractors is now Pro-only** (free bar chart in classic) | MAJOR | `dashboard.py:5212-5215` | `tracker_pages.py:327-329` (`C.pro_more`), hidden by `src/web/home/shell.py:53` | FRESH |
| News-for-your-names block | MINOR | `dashboard.py:5031`, `:3831-3876`, `:5223-5235` | absent | RECORDED (`:298-301`) |
| Upcoming corporate actions block | MINOR | `dashboard.py:5032`, `:3877-3891`, `:5237-5248` | absent | RECORDED (`:298-301`) |
| Attention row loses the "Review" deep-link to the edit form | MINOR | `dashboard.py:5137` | `tracker_pages.py:276-283` — 5 read-only columns | FRESH |
| KPI deck 9 → 7 (open MTM and XIRR dropped from the overview) | MINOR | `dashboard.py:5096-5097` | `tracker_pages.py:256-266` | FRESH (XIRR relocation recorded on `performance`, not here) |
| Allocation loses the by-market-cap split and the explicit top-1/top-3 concentration chips | MINOR | `dashboard.py:5202`, `:5218-5221` | `tracker_pages.py:304-315` — sector + book bars only, top1/top3 as prose | FRESH |
| `<details>` disclosure state on alloc/news blocks | COSMETIC | `dashboard.py:5216`, `:5233` | `tracker_pages.py:406` flat zone | FRESH |

### 5b. `portfolios` — `/dash/portfolios` → `/dash/home/tracker/portfolios`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **6 of 16 columns Pro-gated** — Weight · Target · Stop · Days held · RS phase · Book; all free in classic | MAJOR | `dashboard.py:4638-4642` (all 19 `<th>` unconditional) | `tracker_pages.py:415-420` (`_POS_HEAD` `pro-more`), cells `:433-438` | FRESH |
| **`Thesis health` column** (character pill + RS then→now + conviction drift + ⚠ flags) | MAJOR | `dashboard.py:4641`, `:4615`; `_health_cell:3576-3598` | absent | FRESH |
| **Inline "+ Add a stock" quick-capture form** — 9 fields with symbol autocomplete over `nse_equity_list`, status select, book datalist, strategy multi-select + free text, entry date/price/qty, thesis, entry-price hint JS | MAJOR | `dashboard.py:4158-4195`, autocomplete `:4136-4155`, quote helper `:4306-4320` | no form at all — `tracker_pages.py:461-465` | RECORDED as "single-position add" (`:305`), but the scale is understated |
| Per-row **Edit / Close** writes | MAJOR | `dashboard.py:4636` | one generic link — `tracker_pages.py:465` | RECORDED (`:305-307`) |
| Columns dropped: `Cap` (market-cap tier) · `Strategy` · `Invested` | MINOR | `dashboard.py:4639-4640`; cells `:4620`, `:4622`, `:4626` | not in `_POS_HEAD` — `tracker_pages.py:415-420` | FRESH |
| `Div` (dividends since entry) column | MINOR | `dashboard.py:4642`, `:4635`; `_dividends_since:3508-3546` | absent | RECORDED (`:305-306`) |
| Header XIRR tile | MINOR | `dashboard.py:4580` | `tracker_pages.py:452-460` (5 tiles) | RECORDED (moved to `performance` under the fidelity gate) |
| `?added=` / `?err=` flash banners — the import commit redirects with `?imported=N` and **nothing renders it** (a silent write) | MINOR | `dashboard.py:4531-4534` | route reads only `book` (`tracker_pages.py:778`); `:886` sets `?imported=` | FRESH |
| Book chips shown only when ≥2 books | COSMETIC | `dashboard.py:4535` | `tracker_pages.py:244-245` | FRESH |
| Allocation/concentration `<details>` panel on this page | MINOR | `dashboard.py:4647-4662` | absent from `_positions` (`tracker_pages.py:442-473`) | FRESH |
| _Server CSV honouring `?book`_ | **VERIFIED CARRIED** | `dashboard.py:5469-5520` | `tracker_pages.py:808-824`, `tracker_reads.py:816-850` | ✓ |

### 5c. `watchlists` — `/dash/watchlists` → `/dash/home/tracker/watchlists`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **6 of 13 columns Pro-gated** — Price then · Since added · Days · RS rank · Own deliv. avg · Book (four of them free in classic) | MAJOR | `dashboard.py:4754-4756` | `tracker_pages.py:481-483` | FRESH |
| **Add form collapses 9 fields → 1** — symbol only; no list/book/strategy/target/stop/thesis/date, no autocomplete; the POST redirects to Today, not back here | MAJOR | `dashboard.py:4158-4195` (`_add_box("watch",…)`) | `src/web/home/components.py:771-780` (`_wl_addform`) | PARTLY RECORDED (`:311-312` names only the redirect) |
| Per-row **Alerts / Edit / Promote / Remove** writes | MAJOR | `dashboard.py:4749-4752` | one generic link — `tracker_pages.py:519` | RECORDED (`:310-311`) |
| `Signal / alerts` column (⚡ready badge + 🔔 firing chips) | MAJOR | `dashboard.py:4756`, `:4748`; `_alert_badges:4038-4046` | absent | RECORDED (`:310-311`) |
| Columns dropped: `Strategy` · `Target` · `Stop` · `Live signals` (frozen snapshot chips) | MINOR | `dashboard.py:4754-4756`; cells `:4739`, `:4745-4746`, `:4747`; `_snap_chips:3303-3325` | absent | FRESH |
| ⚡ Ready-to-act banner | MINOR | `dashboard.py:4713-4720` | absent — `tracker_pages.py:501-528` | FRESH |
| `?added=` / `?err=` flash | MINOR | `dashboard.py:4700-4703` | `tracker_pages.py:784-787` | FRESH |

### 5d. `performance` — `/dash/performance` → `/dash/home/tracker/performance`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Return-attribution section gone entirely** — 4 bar groups (by holding · by sector · by book · by strategy) | MAJOR | `dashboard.py:4899-4912`; `_attrib_bars:3907-3955` | `tracker_pages.py:654-661` renders deck · XIRR panel · curve · hit-bars · closed log only | FRESH (the recorded note lists only CAGR + the equity curve as removals) |
| Card `open MTM` | MINOR | `dashboard.py:4862` | `tracker_pages.py:581-596` (9 tiles) | FRESH |
| Card `max drawdown` demoted to a curve sub-line; peak→trough dates dropped | MINOR | `dashboard.py:4866`, `:4873-4875` | `tracker_pages.py:602-603` | FRESH |
| Closed-log columns `Sector` and `Qty` | MINOR | `dashboard.py:4951-4952`; cells `:4931`, `:4939` | `tracker_pages.py:629-634` | FRESH |
| Closed-log **Reopen** write | MINOR | `dashboard.py:4943` | no action column — `tracker_pages.py:646` | FRESH |
| Closed-log benchmark-same-window + Excess columns are Pro-gated (net-new depth, paywalled) | MINOR | n/a in classic | `tracker_pages.py:633-634`, `:644-645` | FRESH |
| `?closed=1` / `?err=` flash banners | COSMETIC | `dashboard.py:4964-4966` | route takes no params — `tracker_pages.py:790-792` | FRESH |
| _CAGR removed · book-value curve → chained TWR · XIRR fidelity-gated_ | **VERIFIED DELIBERATE** | `dashboard.py:4861`, `:4869-4872`, `:4860` | `tracker_reads.py:371-456`, `:519-592`; `tracker_pages.py:532-552`, `:572-574`, `:597-613` | ✓ RECORDED |

### 5e. `import` — `/dash/import` → `/dash/home/tracker/import`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Manual column-mapping override removed** — classic guesses, then lets you fix 5 `<select>`s (Symbol* · Entry date · Entry price · Qty · Strategy) against the real header list. In Graphite a bad guess is unrecoverable | MAJOR | `dashboard.py:5392-5421` (`_imp_review`); commit takes `map_symbol…map_strategy` `:5558-5562` | auto-detect only — `tracker_reads.py:652-741`; the preview form has no mapping controls (`tracker_pages.py:710-751`) | FRESH (the note mentions only `.xlsx`) |
| `.xlsx` / `.xlsm` parsing (openpyxl path) | MAJOR | `dashboard.py:5337-5360`, accept attr `:5442` | CSV/TSV/paste only — `tracker_pages.py:679`; `tracker_reads.py:659-666` | RECORDED ✓ |
| Upload cap 8 MB → 2 MB | MINOR | `dashboard.py:5334` | `tracker_reads.py:46` | FRESH |
| Raw preview of the first 8 file rows (all original columns) | MINOR | `dashboard.py:5402-5406`, `:5420-5421` | verdict table over parsed fields only — `tracker_pages.py:718-730` (offset by new per-row READY/ALREADY-THERE/CAN'T-READ verdicts + re-validate on commit at `:863-882`, which classic lacks) | FRESH |
| Commit gives no confirmation (`?imported=N` set but never read) | MINOR | `dashboard.py:5564`, `:4429`, rendered `:4531` | `tracker_pages.py:886`; `:776-780` never reads it | FRESH |
| _Paste-a-block input_ | **Graphite GAIN** | not in classic | `tracker_pages.py:680-682` | — |

### 5f. `model-books` — `/dash/model-books` → recorded DROPPED-as-merge

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The recorded merge claim is WRONG.** `sideways_parity.py:331-333` states "the Tracker carries the 'follow a book' view … as a section of `/dash/home/tracker`". It does not — the section is two links, one pointing back at the classic page, and the module docstring concedes it | MAJOR | `src/web/model_books_view.py:185-236` (the real view) | `tracker_pages.py:349-377` (`_model_books_block`) — prose + two `<a>`; docstring `:360-364` concedes "the FOLLOW door deliberately stays on classic" | RECORDED-BUT-FALSE |
| **Classic-public estate invisible** — classic lists BOTH `auto_portfolio_nav` and `classic_portfolio_nav` books with adopt buttons; the Graphite books page covers only the 4 auto books | MAJOR | `model_books_view.py:82-88` (`_ESTATES`) | `src/web/home/strategies_reads.py:111-124` (`BOOKS` = 4); classic screens are read-only rosters at `:392-431` | FRESH |
| **Adopt write** (seed a named book from a model's holdings at today's close) has no Graphite door | MAJOR | `model_books_view.py:239-288`, form `:176-181` | Graphite books page is read-only — `src/web/home/strategies_pages.py:104-131` | RECORDED as intentional (`:333-334`) |
| Per-book Since / CAGR / vs Nifty 500 / MaxDD row + the "only N years — not a track record" thin-history label | MINOR | `model_books_view.py:158-182`, `_stats:104-125`, `MIN_YEARS:63` | not restated in the tracker block | FRESH |
---

## 6. Strategies (W3-A) — 18 classic surfaces → `/dash/home/strategies*`

16 PORTED · 1 DROPPED (`cpr`) · 1 DEFERRED (`shp`). Sampled and verified below. Four recorded
claims are wrong or understated; the biggest un-recorded losses are the per-lens **window / class /
per-symbol-drill controls** on the ownership hub and the **Pro-gating of columns that were free**.

### 6a. `strategist` — → `/dash/home/strategies`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Confluence-alerts strip (newly-entered / dropped-out of credible ∩ accumulated; watchlist overlap) | MAJOR | `src/web/strategist_view.py:506-574` | absent — `src/web/home/strategies_pages.py:86-98`; `src/web/home/strategies_blocks.py:127-168` | RECORDED ✓ |
| Per-strategy new/dropped diff ("what changed") | MAJOR | `strategist_view.py:576-628` | absent | RECORDED ✓ |
| CCI-RRG divergence tile | MINOR | `strategist_view.py:629-689` | absent | RECORDED ✓ |
| "Your boards" section | MINOR | `strategist_view.py:690-739` | absent | RECORDED ✓ |
| `?fmt=csv` registry export | MINOR | `strategist_view.py:760-770`, link `:821` | no `fmt` param — `strategies_pages.py:86-98` | FRESH |

### 6b. `model-portfolios` — → `/dash/home/strategies/books`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Time-travel `?asof=`** (holdings at any past rebalance) — the whole capability, not just the stepper UI | MAJOR | `src/web/auto_portfolios_view.py:228-245`, `:395-398` | the route never passes `asof`; `book_holdings(conn, book)` called without it — `strategies_pages.py:123`, `src/web/home/strategies_reads.py:187` | RECORDED as "stepper UI" (`:358`) — understated |
| Survivability ballast overlay (core × G-sec × gold mixes: CAGR / ret-vol / MaxDD) | MAJOR | `auto_portfolios_view.py:401-426` | absent — `strategies_blocks.py:177-245` | RECORDED ✓ |
| All-books comparative chart (4 books + benchmark on one axis) | MINOR | `auto_portfolios_view.py:7`, `:50-53` | `spark_pair` plots one book vs bench — `strategies_blocks.py:227`, `:248-271` | RECORDED ✓ |
| Union / graduating-candidates table (7 sealed siblings) | MINOR | `auto_portfolios_view.py:455-478` | absent | RECORDED ✓ |
| `?fmt=csv` holdings export | MINOR | `auto_portfolios_view.py:264-269`, `:397-398` | absent | RECORDED ✓ |
| **Since-year chips (2012 / 2019 / 2022)** — `since` is parsed but no chip is rendered: a live query param with no door | MINOR | `auto_portfolios_view.py:326-330` | `strategies_pages.py:116-118` | FRESH |
| Pro-gated block on an evidence table | COSMETIC | n/a | `strategies_blocks.py:230-233` | FRESH |

### 6c. `stocks` (+ `stealth`) — → `/dash/home/strategies/positioning`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`?sector=` filter** (sector-constituent scoping + the "factor index, not a sector" explainer) | MAJOR | `src/web/dashboard.py:1343`, `:1355-1356`, `:1472-1489` | no `sector` param (`strategies_pages.py:197`); `positioning()` has no sector clause (`strategies_reads.py:439-460`) | FRESH |
| 8 filter pills (All · SS · A+ · ⚡ATH · 🟢Discount · 🔥Near-break · 🟢Accumulation · 🔴Distribution · 🎯Near key price) | MAJOR | `dashboard.py:1562-1571`, JS `:1582-1586` | a 2-item All/Stealth tab strip — `strategies_blocks.py:409-410` | RECORDED ✓ |
| Weekly / Monthly rollup (`?period=w\|m`: peak rank, days fired /N, avg DVPT, character) | MAJOR | `dashboard.py:1411-1443`, `:1589-1609`, toggle `:1451-1457` | the route accepts only `view` — `strategies_pages.py:192-206` | RECORDED ✓ |
| **Recorded claim OVERSTATED**: "NOT carried: the 14 default-hidden columns" — 3 of the 14 (RS#, 52w-hi, Gap3m) ARE carried | flag | `dashboard.py:1575-1580` | `strategies_blocks.py:403-404` | RECORDED-BUT-FALSE (overstated) |
| The other 11 default-hidden columns genuinely gone (RS·brd, RS·sec, Drift3m, Up/Dn3m, Pow3m Cr, Churn, Ticket, Key3m, Key6m, Gap6m; DVPT ₹ re-based to ₹cr) | MINOR | `dashboard.py:1537-1549`, `:1575-1580` | `strategies_reads.py:432-436` (`_POS_COLS`) never selects them | RECORDED ✓ |
| Watchlist chips strip | MINOR | `dashboard.py:1611-1615` | absent | RECORDED ✓ |
| `?limit=` (10-120) control | MINOR | `dashboard.py:1343` | hardcoded `limit=60` — `strategies_reads.py:439` | FRESH |
| `Δhot` column + 🟢/🟡/🔴 entry glyph (`price_vs_hot_avg_pct`) | MINOR | `dashboard.py:1516`, `:1557`, head `:1574` | not in `_POS_COLS` | FRESH |
| `Near-P` column (`next_p_above` + gap) | MINOR | `dashboard.py:1518-1521`, `:1559`, head `:1574` | absent | FRESH |
| ⚡ ATH glyph (`is_ath_dvpt` selected but never rendered) | COSMETIC | `dashboard.py:1514`, `:1552` | selected `strategies_reads.py:435`, unused `strategies_blocks.py:395-404` | FRESH |
| Ticker search box + Screener/Workbench cross-links | COSMETIC | `dashboard.py:1447-1449`, `:1617-1620` | absent | FRESH |
| _Stealth filter reproduced exactly_ | **VERIFIED** | `dashboard.py:1382-1385` | `strategies_reads.py:452-453` | ✓ |

### 6d. `conviction` — → `/dash/home/strategies/conviction`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Recorded claim UNDERSTATED**: the note says only "the client-side filter pills"; two data columns also vanished | flag | — | — | RECORDED-BUT-FALSE (incomplete) |
| MEP confirmation column | MINOR | `src/web/cockpit.py:2320-2336`, cell `:2373`, head `:2392` | `strategies_blocks.py:453-460` (8 columns) | FRESH |
| Entry-read column (🎯 near key · 🟢 discount · 🔴 extended · 🟡 at-cost) | MINOR | `cockpit.py:2344-2352`, `:2374`, `:2392` | absent | FRESH |
| Filter pills (All · 🎯 Near key · ★ Quality-confirmed) | MINOR | `cockpit.py:2386-2389`, JS `:2394-2398` | absent | RECORDED ✓ |
| `?limit=` (10-200) | COSMETIC | `dashboard.py:1190` | hardcoded 60 — `strategies_pages.py:219` | FRESH |
| ★/✗ quality pill styling flattened to plain text | COSMETIC | `cockpit.py:2353-2359` | `strategies_blocks.py:459` | FRESH |

### 6e. `mep` — → `/dash/home/strategies/mep`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Recorded claim WRONG**: "the full component columns" — the raw daily "Today" score (`mep_score`, shown beside the smoothed phase score) is absent | flag / MINOR | `cockpit.py:2211-2213`, cell `:2255-2256`, head `:2282` | `strategies_reads.py:488-517`, `strategies_blocks.py:500-508` — smoothed only | RECORDED-BUT-FALSE |
| Glossary popovers on every MEP header (×9) | MINOR | `cockpit.py:2276-2288` | plain `<th>` — `strategies_blocks.py:518-520` | RECORDED ✓ |
| Row cap 150/side (300) → 80 total | MINOR | `cockpit.py:2225`, `:2229` | `strategies_reads.py:488` | FRESH |
| Direction filter is now a server round-trip, not an instant client toggle | COSMETIC | `cockpit.py:2269-2272`, JS `:2292-2296` | `strategies_blocks.py:512-513` | FRESH |

### 6f. `concalls` (+ `credibility` fingerprint) — → `/dash/home/strategies/credibility`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Avoid / Track-record view toggle** (classic re-sorts worst-first vs coverage-first) | MAJOR | `cockpit.py` `render_concalls` `view` arg (toggle ~`:2166`, sorts ~`:2105-2112`); route `dashboard.py:2846` | the route takes only `?sym=` — `strategies_pages.py:249-266` | FRESH |
| Deterioration column | MINOR | `cockpit.py` `render_concalls` head (`Deterior.`) | `strategies_blocks.py:581-583` (10 columns) | FRESH |
| Three ·AI behaviour columns (Cred·AI, Courage·AI, Evasion·AI) | MINOR | `cockpit.py` `render_concalls` head | absent | RECORDED ✓ |
| 4 count tiles re-cut | COSMETIC | `cockpit.py` `render_concalls` tiles | `strategies_blocks.py:540-543` | FRESH |
| _`/dash/credibility` fingerprint absorbed as `?sym=`_ | **VERIFIED** | `src/web/credibility_fingerprint.py:255-264` | `strategies_pages.py:254`, `:262`; `strategies_blocks.py:557-573` | ✓ |

### 6g. `growth` — → `/dash/home/strategies/growth`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| ⚠ Pullbacks (no-capex) tab (`?pullback=1`, polarity −1) | MAJOR | `src/web/growth_view.py:111-112`, route `:160-172` | `pullback` is not a param (`strategies_pages.py:272-295`); `growth()` has no polarity arg (`strategies_reads.py:556`) | RECORDED ✓ |
| `?symbol=` server filter + its input box | MINOR | `growth_view.py:125`, `:161` | not a param; no `symbol` in the read signature | FRESH |
| Click-to-sort headers (Symbol / Period / Type / ₹cr) | MINOR | `growth_view.py:137-141`, JS `:84-90` | plain `<th>` | FRESH |
| Instant text filter + live row count | MINOR | `growth_view.py:124`, JS `:76-83` | absent — `strategies_blocks.py:596-613` | RECORDED ✓ |
| min-₹ / since input boxes | MINOR | `growth_view.py:126-127` | params parsed (`strategies_pages.py:281-287`), no UI | RECORDED ✓ |
| Row cap 600 → 300 | COSMETIC | `growth_view.py` route | `strategies_reads.py:556` | FRESH |
| _Concall-corpus provenance disclosure added_ | **Graphite GAIN, VERIFIED** | not in classic | `strategies_blocks.py:532-535`, `:613` | ✓ |

### 6h. `launchpad` + `launchpad-track` — → `/dash/home/strategies/launchpad`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Recorded claim UNDERSTATED**: the note says "the regime banner and the genuine-buyer count tile"; in fact **all four count tiles** are gone (Fresh triggers · ⭐ With genuine buyer · Precursor universe · Coiled) | flag / MINOR | `cockpit.py` `render_launchpad` `_ck_strip([...])` | `strategies_blocks.py:797-820` (`_lp_screen`) — learn-note + table only | RECORDED-BUT-FALSE (incomplete) |
| Regime banner (Nifty 50 vs 200-DMA RISK-ON/OFF timing gate) | MAJOR | `cockpit.py` `render_launchpad` regime block | absent | RECORDED ✓ |
| "+N more fresh / N sustained" footer (explains the 80-row cap and the fresh-vs-running split) | MINOR | `cockpit.py` `render_launchpad` | absent | FRESH |
| Winners/losers click-through drill (`?drill=`) on the evidence tab | MINOR | `src/web/launchpad_track_view.py:162` | `strategies_pages.py:343-352`, `strategies_blocks.py:823-859` | RECORDED ✓ |
| _Study tiles / cohorts / histogram / recovery ladder_ | **VERIFIED CARRIED** | `launchpad_track_view.py:270-271` | `strategies_blocks.py:826-858` | ✓ |

### 6i. `insider` · `ratings` · `sast` · `shp` — → `/dash/home/strategies/ownership?lens=`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`insider` is recorded with NO residual at all, yet four controls and two columns are missing** | flag | `sideways_parity.py:413-416` claims full carry | — | RECORDED-BUT-FALSE |
| **Window selector** 30/90/180d (insider) · 90/180/365d (ratings) · 30/90/180d (sast) | MAJOR | `src/web/insider_view.py:225`; `src/web/ratings_view.py:234`; `src/web/sast_view.py:267` | hardcoded `days=90`/`180`/`90` (`strategies_reads.py:587`, `:607`, `:626`); the route reads only `lens` (`strategies_pages.py:306`) | FRESH |
| **Class / feed tab filters** (`?cls=conviction\|caution\|…`, `?cls=UPGRADE\|DOWNGRADE\|…`, `?feed=INVOKE\|…`) | MAJOR | `insider_view.py:222`; `ratings_view.py:231`; `sast_view.py:264` | absent | FRESH |
| **Per-symbol drill `?sym=`** on all three tapes (+ `?min_cr=` on insider) | MAJOR | `insider_view.py:19`, `:195`; `ratings_view.py:23`; `sast_view.py:186`, `:241`; `src/web/shp_view.py:186-214` | absent | RECORDED for `sast` only (`:424`); FRESH for insider / ratings / shp |
| SHP **QoQ delta board** (Δ Prom / Prom now / Δ FII / Δ DII / Δ Public / Δ Pledge / Pledge now) | MAJOR | `shp_view.py:173-182` | quarter matrix only — `strategies_blocks.py:738-767` | RECORDED ✓ |
| Insider columns `Net 90d` and `Pledge ev.` | MINOR | `insider_view.py:167-168` | `strategies_blocks.py:668-669` (7 columns) | FRESH |
| Ratings-transition columns `Action` + the filing link on the board | MINOR | `ratings_view.py:179-183` | `strategies_blocks.py:700` (6 columns) | FRESH |
| SAST board columns `Acq 90d` · `Sold 90d` · `Invoked` | MINOR | `sast_view.py:189-192` | `strategies_blocks.py:733` (6 columns) | FRESH |
| SHP 7 census tiles | MINOR | `shp_view.py:106-133` | absent | RECORDED ✓ |
| _SHP unverifiable off-box (separate research store)_ | **VERIFIED** | `shp_view.py:220` | `strategies_reads.py:660`; DEFERRED at `sideways_parity.py:425-430` | ✓ |

### 6j. `classics` + `factor-league` — → `/dash/home/strategies/library`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Per-screen custom column sets** replaced by one fixed 5-column roster (classic renders a screen-specific `_COLS` list with per-header glossary popovers) | MAJOR | `src/web/classics_view.py:263-287` | `strategies_blocks.py:366-384` (`classic_detail`) — fixed #, Symbol, Sector, Price, Score | FRESH |
| Year-by-year table (year · book · Nifty 500 · excess) | MAJOR | `classics_view.py:409-412`, `_per_year:109-128` | absent | RECORDED ✓ |
| Backdate form / holdings-as-of `?asof=` | MAJOR | `classics_view.py:291`, `:314-315`, `:386-399`, `_asof_holdings:129-142` | `library()` reads only `origin` + `s` — `strategies_pages.py:162-165` | RECORDED ✓ |
| Factor-league roster columns `6m · 12m · Vol · Turn₹cr` | MINOR | `src/web/factor_league_view.py:245-246` | `strategies_blocks.py:382` | FRESH |
| `?fmt=csv` — classics per-screen (recorded) AND factor-league per-family (not recorded) | MINOR | `classics_view.py:318-329`, `:285`; `factor_league_view.py:190-191` | absent | RECORDED (classics) / FRESH (factor-league) |
| Churn feed (last 60 roster changes, in/out arrows) | MINOR | `factor_league_view.py:136-169` | absent | RECORDED ✓ |
| _League verdict table linked rather than restated_ | **VERIFIED DELIBERATE** | `factor_league_view.py:267-272` | `strategies_blocks.py:352-357` | ✓ |

### 6k. `sector-rotation` — → `/dash/home/strategies/sector-rotation`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Year-strip stepper UI for `?asof=` (the param IS parsed and passed, only the control is missing) | MINOR | `src/web/sector_rotation_view.py:116-117` | `strategies_pages.py:145`; no stepper in `strategies_blocks.py:284-318` | RECORDED ✓ |
| `?fmt=csv` export | MINOR | `sector_rotation_view.py:117` | absent | RECORDED ✓ |
| _D138 scope gap + D141 rejection above the headline; weights / diff / NAV / 4 stats_ | **VERIFIED CARRIED** | `sector_rotation_view.py:253` | `strategies_blocks.py:276-281`, `:299-317` | ✓ |

### 6l. `stealth` / `cpr` — merged / demoted

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| `cpr` demoted: the cross-symbol **reversal leaderboard (14 cols)** and **compression leaderboard (8 cols)** have no Graphite home | MAJOR | `dashboard.py:2879-2929`, `:2932-2959`; route `:2962-2963` (`?tab/?tf/?direction/?tier`) | no `/strategies/cpr` route; per-name CPR only on the stock dossier | RECORDED as a deliberate DROP (`sideways_parity.py:392-399`) — verdict consistent with the code ✓ |
| `stealth` merge is a registry fact (classic already delegated) | — | `dashboard.py:1636-1642` | `strategies_pages.py:192-206` | **VERIFIED** ✓ |
---

## 7. Screener workspace (W4) — `screen2` · `themes` · `screener` · `workbench` · `tags-review`

**The fundamentals column family (~15 §J columns) is a RATIFIED EXCLUSION, not a gap** — sourced from
the `screener.py` vendor path under Guardrail #8 remediation; the guardrail outranks the §J listing
(ledger `docs/graphite-cutover-orchestration.md:197-200`). It is excluded from every count below.

The rebuild genuinely fixed three recorded debts (2.3 MB → 103 KB pagination · server CSV honouring
filter/sort/columns · URL state instead of localStorage). But the note "**Every capability carried**"
(`sideways_parity.py:445-448`) is not true.

### 7a. `screen2` — `/dash/screen2` → `/dash/home/screen`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The five inline instrument micro-visualisations** — DVPT-vs-power ladder · accum/distrib signed bar · RS spark · multi-TF RS heat strip · character triglyph. The page's declared identity ("each turned into a shape beside its raw numbers") | MAJOR | `src/web/screener_plus.py:455-583` (builders), `:849-855`, `:872`, `:879`, `:884-885`, `:912`; copy `:999-1001` | `src/web/home/screen_pages.py:561-585` (`_tbody`) emits text cells + pillar dots only; no SVG/glyph cell anywhere | FRESH (contradicts "Every capability carried") |
| **Pat bridge** — "Ask Pat: confluence here" deep-link + "★ Save as Pat board" (POST `/pat/board/save`) + the scope→NL-query mapper | MAJOR | `screener_plus.py:1004-1022`, `_pat_bridge_q:1050-1064`, `s2SaveBoard` in `_JS` | `screen_pages.py:824-829` mounts the dock only; no board write, no scope→query bridge | FRESH |
| Column-parity / promotability view `?parity=1` (family coverage table + 10-row promotion checklist) | MINOR | `screener_plus.py:620-705`, `:712-715`, chip `:1017` | no `parity` param in `parse_state` (`screen_pages.py:268-308`) | FRESH |
| **Column `?` help resolves to the CLASSIC glossary route** — a cross-experience leak | MINOR | `screener_plus.py:938` (in-page popover) | `screen_pages.py:543` `href="/dash/glossary"`; the Graphite twin is `/dash/home/glossary` (`trust_pages.py:661`) | FRESH |
| Free-text filter is live/client-side over the whole row; Graphite requires a form submit and matches only 12 whitelisted fields | MINOR | `screener_plus.py` `_JS` `doFilter` (`r.textContent`) | `screen_pages.py:400-410` (`_TEXT_FIELDS`), `:654-662` | FRESH |
| `?limit=` universe cap (50-2000, user-settable) | MINOR | `screener_plus.py:710-722`, `:975` | fixed `R.UNIVERSE_CAP` — `screen_pages.py:446`, `:676` | FRESH |
| Glossary help is a hover popover in classic, a link-out in Graphite | COSMETIC | `screener_plus.py:936-939`, `:1030` | `screen_pages.py:543-544` | FRESH |
| Named saved screens (save/load/delete list) → URL bookmarks | MINOR | `screener_plus.py:1012-1015` (`SKEY='s2_screens_v1'`) | `screen_pages.py:311-339`, `_HOW_TO_READ:735` | RECORDED ✓ (deliberate) |
| _"Rank in screen" + "vs own 1-mo" are `.pro-more`_ | **NOT a gap** — neither column exists in classic; the Free set is a strict superset | — | `screen_pages.py:548-552`, `:575-583`, `:778-783` | — |

### 7b. `themes` — `/dash/themes` + `/dash/theme` → `/dash/home/themes`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Theme-detail participants table drops 6 of 11 columns** — Themes chips · Trigger rank · p-score · %52wH · DVPT (₹cr) · Δhot | MAJOR | `src/web/cockpit.py:2612-2658` (header `:2655-2657`) | `screen_pages.py:874-886` — 7 cols: Symbol · Sector · CMP · RS rank · RS trend · Accumulation · Character | FRESH |
| "Accumulating only" checkbox filter on the participants table | MINOR | `cockpit.py:2651-2653` | none | FRESH |
| ⚡ ATH-DVPT row glyph + the ATH-DVPT roll-up tile | MINOR | `cockpit.py:2623`, `:2636`, tile `:2755` | `screen_pages.py:870-873` (4 tiles, no ATH) | FRESH |
| "In RS uptrend" roll-up tile | MINOR | `cockpit.py:2753` | `screen_pages.py:870-873` | FRESH |
| Board-level count strip (Themes / Companies tagged / **Awaiting tags**) | MINOR | `cockpit.py:2674-2678` | `screen_pages.py:833-849` — groups + cards, no strip | FRESH |
| _Theme → screener hand-off `?scope=theme:<tag>`_ | **Graphite GAIN** | — | `screen_pages.py:887-889` | RECORDED ✓ |

### 7c. `screener` (classic Screen) — recorded DROPPED (duplicate; classic route stays live)

The DROP verdict is sound (`sideways_parity.py:460-468`). But §J's claim that Screen+/Graphite is a
strict superset is not quite true — these classic-Screen columns are absent from the Graphite ~75-column
pool:

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Whole surface un-rebuilt | MAJOR | `src/web/dashboard.py:1737-1755` | none | RECORDED ✓ (deliberate, reversible) |
| RS **vs own sector** trend-state column | MINOR | `dashboard.py` rs band (~`:1979`) | `screen_pages.py:134-144` — no `rs_vs_sector_*` | FRESH |
| CPR **monthly** timeframe + CPR rank / strength columns (`M%`, `Rnk`, `Str`) | MINOR | `dashboard.py` cpr band (~`:1975`) | `screen_pages.py:146-148` — only `cprd`/`cprw`/`cprc` | FRESH |
| CCI forward-look / deterioration / veto / #calls columns | MINOR | `dashboard.py` cci band (~`:1981`) | `screen_pages.py:150-152` — score/tier/trend only | FRESH |
| **Themes** column (tag chips per row) | MINOR | `dashboard.py` `g-themes` (~`:1982`) | no themes column in `POOL` (`screen_pages.py:113-199`) | FRESH |
| Character sub-scores WHO / WAY / Drift as separate columns | MINOR | `dashboard.py` `g-char` (~`:1977`) | only `char`, `drift` (`screen_pages.py:169`, `:179`) | FRESH |
| `Δhot%` (`price_vs_hot_avg_pct`) and the "Launch band" cell | MINOR | `dashboard.py` `g-ctx`/`g-key` bands | absent from the pool | FRESH |

### 7d. `workbench` — recorded DROPPED-ABSORBED as the `keyprice` view

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Launch-band highlight** on the gap cells (green tint when the gap sits in −1%…+5% of the key price) — the page's one read affordance | MINOR | `dashboard.py:1676-1681` (`gapcell()` + `is_near_key`), legend `:1730-1732` | `screen_pages.py:184-188` (`gk3/gk6/gk12`) render as plain signed % via `_fmt` (`:512-517`) | FRESH |
| Whole surface un-rebuilt; the key-price family absorbed | MINOR | `dashboard.py:1647-1735` | `screen_pages.py:222-225` (`VIEWS["keyprice"]`) | RECORDED ✓ |
| `r/p` combined column and `Deliv ₹Cr` scaling | COSMETIC | `dashboard.py:1697`, `:1712` | `dvt`/`tvt` as raw rupees — `screen_pages.py:192-193` | FRESH |

### 7e. `tags-review` — recorded NA (owner write-desk). Verified: every control is a write against the tag layer. **Not a gap.**
---

## 8. Trust workspace (W5) — 11 classic surfaces → 8 Graphite pages + the Pat dock

10 PORTED + 1 NA. The pages exist and read well; what did not travel is, in several cases, the
**artifact** the page existed to produce — the printable memo, the printable evidence pack, the
reproduce-it-yourself curl line, the rule-lab verdict card, the reading guide's worked example.

### 8a. `coverage` — `/dash/coverage` → `/dash/home/proof`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **`/dash/coverage/memo`** — the print-ready, dated, sourced Coverage & Provenance Memo (print button, print CSS, SEBI record-keeping footer) has no twin | MAJOR | `src/web/coverage_view.py:689-742`, route `:756-758`, `_MEMO_PRINT_CSS:667-687` | no memo route in `src/web/home/trust_pages.py` | FRESH |
| **Eight sections dropped**: Universe & survivorship · CCI settlement crosstab (tier × call-count) · Modeled-vs-filed · Provenance story / receipts · Methodology · Degradation · Principles & limits · Strategy-validation pane | MAJOR | `coverage_view.py:261`, `:294`, `:341`, `:387`, `:411`, `:452`, `:465`, `:480`, `:489`; tab assembly `:610-618` | `trust_pages.py:206-261` = boundary list + 4 tiles + class table + nav strip | FRESH |
| **Provenance registry table** (key · dataset · source · cadence · MODELED/AS_TRADED basis pill) reduced to a single count tile | MAJOR | `coverage_view.py:639-664` | `trust_pages.py:240` renders only `len(reg)` as "Data classes declared" | FRESH |
| Per-data-class matrix loses `Basis` and `Freshness` columns + the staleness pill | MINOR | `coverage_view.py:294-297` (7 cols), `_staleness_pill:150-165` | `trust_pages.py:271-281` (5 cols) | FRESH |
| CCI funnel bars/steps reduced to two tiles | MINOR | `coverage_view.py:166-203` | `trust_pages.py:241-242` | FRESH |
| Six-tab progressive disclosure → single scroll | COSMETIC | `coverage_view.py:610-627` + `_COV_TAB_JS` | `trust_pages.py:206-261` | FRESH |

### 8b. `testing` — `/dash/testing` → `/dash/home/validation`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Cost-basis column dropped from the verdict table | MINOR | `src/web/testing_view.py:156` | `trust_pages.py:357-358` | FRESH |
| Candidate-holdings top-25 cards collapsed to 6 inline symbols in a "Book" cell | MINOR | `testing_view.py:163-175`, `_holdings:93` | `trust_pages.py:365-368` (`[:6]`) | FRESH |
| _Ledger BLOCKING rows added beside the table_ | **Graphite GAIN** | — | `trust_pages.py:323-329`, `:383-397` | RECORDED ✓ |

### 8c. `glossary` — `/dash/glossary` → `/dash/home/glossary`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Filter matches term **+ definition text**; Graphite matches the term name only | MINOR | `src/web/glossary_view.py` `_JS` (`r.textContent`) | `trust_pages.py:702-708`; `data-t` = name only (`:683`) | FRESH |
| Inline markdown (`**bold**`, `code`) in definitions is escaped to literal text | COSMETIC | `glossary_view.py:64-67` (`_inline()`) | `trust_pages.py:684` (`C.esc()`) | FRESH |
| Family sections auto-hide when nothing inside matches; Graphite leaves empty family headers | COSMETIC | `glossary_view.py` `_JS` | `trust_pages.py:702-708` | FRESH |
| Family intro/blurb lines | COSMETIC | `glossary_view.py:56-57` | `trust_pages.py:681-688` | FRESH |

### 8d. `strategy-ref` — `/dash/strategy-ref` → `/dash/home/strategy-ref`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Surface hand-off strip** — the prominent "Open the live surface this page describes →" button on 13 of 16 strategy pages (a ratified 2026-07-15 requirement) | MAJOR | `src/web/strategies_view.py:57-73` (`_SURFACE`), `:75-84` (`_surface_strip`) | `trust_pages.py:737-738` renders `_md(doc["text"])` only; no surface link | FRESH |
| Doc-relative cross-link rewriting (sibling `.md` links → served hrefs; repo refs downgraded to plain text so no dead links) | MINOR | `strategies_view.py:86-106` (`_rewrite`) | `trust_pages.py:738` (`_md()`) — no equivalent rewriter | FRESH |
| "Overview" index entry in the rail | COSMETIC | `strategies_view.py:235` | `trust_pages.py:729-731` | FRESH |
| _List DERIVED from the directory + a widened public sanitizer_ | **Graphite GAIN** | `strategies_view.py:33-51` (hardcoded `_PAGES`) | `trust_pages.py:718` (`R.strategy_pages()`) | RECORDED ✓ |
| _🔴 Banked: the classic `_public` sanitizer leaks on live `/dash/strategy-ref` today (`S164BB`/`S155-e`/`S1234` escape the regex); the Graphite port widens it. Classic is byte-frozen, so recorded not patched_ | — | ledger `docs/graphite-cutover-orchestration.md:228-231` | — | RECORDED (classic-side defect) |

### 8e. `reading-guide` — `/dash/reading-guide` → `/dash/home/guide`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The worked example** — a live 22-year breadth heat-ribbon read together in 4 numbered steps, from real `research.db` data with era markers | MAJOR | `src/web/reading_guide_view.py:189-228`, `_real:94-160` | `trust_pages.py:758-781` — no charts at all | FRESH |
| **"The six shapes" card gallery** — six real charts, each with What-it-is / How-to-read / "on: <page>" deep-link | MAJOR | `reading_guide_view.py:163-171`, `:230-340` | none | FRESH |
| The 12-term plain-English idea glossary (breadth, tape, delivery, drawdown, dispersion, median-vs-average, percentile, base-rate, survivorship, FII/DII, ROCE/OPM, long/short) | MINOR | `reading_guide_view.py:172-186` (`_IDEAS`) | none | FRESH |
| "real chart" vs illustration honesty badge per card | MINOR | `reading_guide_view.py:164` | n/a | FRESH |
| _Five-step journey arc as structure_ | **carried** | — | `trust_pages.py:762-766`, `src/web/home/journey.py:100` | RECORDED ✓ |

### 8f. `spec-sheets` — `/dash/spec-sheets` → `/dash/home/prereg`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| Sheet inline markup stripped to plain text (bold/emphasis in hypothesis & gate lost) | COSMETIC | `src/web/spec_sheets.py:409-412` | `trust_pages.py:456-459` (`_plain()` regex-strips all tags) | FRESH |
| Link to the assembled evidence pack from the sheets page | COSMETIC | `spec_sheets.py:404` | `trust_pages.py:416-419` | FRESH |
| _Placebo box · MTTR box · M05 standing caveats_ | **VERIFIED CARRIED** | `spec_sheets.py:409-411` | `trust_pages.py:449-452` | ✓ |

### 8g. `rule-lab` — `/dash/rule-lab` → `/dash/home/rule-lab`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The verdict card itself** — verdict + qualifier + the 9-row numbers table (net/gross ret-vol, both walk-forward halves, placebo p95, observed, benchmark, maxDD, ann cost, capacity) + the prereg SHA-256 chip + the refusal reason | MAJOR | `src/web/rule_lab_view.py:190-222`, `_numbers_table:146-160` | `trust_pages.py:497-513` renders **pre-run ledger citations only**; real numbers appear only in the synthetic demo (`:557-576`) | FRESH |
| **Roster / current cohort** block (the names the rule selects, each deep-linked) | MAJOR | `rule_lab_view.py:178-187` (`_roster_block`) | none | FRESH |
| CSV export `?format=csv` (numbers + verbatim citations + roster) | MINOR | `rule_lab_view.py:106-131`, `:359-363` | no `format` param — `trust_pages.py:463-480` | FRESH |
| "Run the gauntlet" POST + queue-to-inbox affordance (owner-gated in classic, so the *button* is the gap, not the compute) | MINOR | `rule_lab_view.py:236-253`, `:389+` | GET-only — `trust_pages.py:545` | FRESH |
| `?queued=` / `?err=` states | COSMETIC | `rule_lab_view.py:364-386` | none | FRESH |
| _`u/rank/n/hold/where/veto` params round-trip identically (ratified §K.4)_ | **VERIFIED** | `rule_lab_view.py:355-357` | `trust_pages.py:470` | ✓ RECORDED |

### 8h. `replay-any-date` — `/dash/replay-any-date` → `/dash/home/replay`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The curl line under every panel** — the "reproduce this yourself" affordance the page's whole thesis rests on | MAJOR | `src/web/replay_any_date.py:160-161` (`_curl`), printed at `:231`, `:263`, `:289` | `trust_pages.py:639-657` (`_replay_panel`) prints status + JSON only; no curl anywhere in the file | FRESH |
| Query param renamed `?symbol=` → `?sym=`; classic deep links do not carry across | MINOR | `replay_any_date.py:294` | `trust_pages.py:584` | FRESH |
| Symbol-form validation panel (`_SYM_RE`) + the explicit "demo key not provisioned" state | MINOR | `replay_any_date.py:337-347` | generic teaching-empty — `trust_pages.py:643-647` | FRESH |
| Worked-example set 4 → 3; the "one day before the call (no leak)" pair is dropped | MINOR | `replay_any_date.py:325-335` | `trust_pages.py:608-610` | FRESH |
| Cross-check footer to coverage / spec-sheets / evidence-pack / `/v1/openapi.json` | MINOR | `replay_any_date.py:353-358` | none | FRESH |
| _`journey.replay_card` for the Today page_ | **Graphite GAIN** | — | `trust_pages.py:620-624` | RECORDED ✓ |

### 8i. `evidence-pack` — `/dash/evidence-pack` → `/dash/home/validation?pack=1` (merged)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Print / save-as-PDF button and the print stylesheet** — the pack is a procurement artifact; without print CSS it is just a long page | MAJOR | `src/web/evidence_pack.py:168-174`; `spec_sheets._CSS` print rules | `trust_pages.py:336-348` — no print button, no `@media print` | FRESH |
| §4 Season service record (live) + infra copy | MINOR | `evidence_pack.py:212-214` | pack body `:338-347` omits it (MTTR lives only on `/prereg`) | FRESH |
| §3 coverage sections in the pack BODY (the boundary matrices, not just a link) | MINOR | `evidence_pack.py:209-210` | pack links to `/dash/home/proof` — `trust_pages.py:344` | FRESH |
| Generated-at stamp + scope line + tamper-evidence paragraph | MINOR | `evidence_pack.py:181-193` | none | FRESH |
| _Verify-routes index + replay narrative retained_ | **VERIFIED** | `evidence_pack.py:160-161`, `:197` | `trust_pages.py:341-347` | ✓ RECORDED |

### 8j. `pat` — `/dash/pat` → the extended floating dock + `GET /dash/home/pat/ask`

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **The ~15 guided FLOWS** (accumulation · rs · rslag · fundamentals · movers · index · distribution · consolidation · pt14 · redflags · confluence · credibility · deterioration · trend · oscillators · strategy · why) with their chip-parameter drill (`sector/strength/entry/align/val/qual/grow/bs/own`) | MAJOR | `src/web/dashboard.py:1205-1210` (17 query params); `src/pat/web.py:3411-3470+` | `src/web/home/pat_dock.py:311-360` (`resolve()`) = glossary term ∪ lens ∪ symbol only; no flow router | FRESH — the parity note lists only threads/boards/feedback |
| Multi-turn **threads** (`pat_tid` cookie, thread trail, in-thread pronoun resolution, "start over") | MAJOR | `dashboard.py:1216-1228`; `src/pat/web.py:3237-3299`, `:3300-3376` | none | RECORDED ✓ (`sideways_parity.py:525`; `pat_dock.py:260-263`) |
| **Saved boards** (save / list / reopen / delete) | MAJOR | `src/pat/web.py:2769-2845`, `:2947-2965` | none | RECORDED ✓ |
| **👍/👎 feedback loop** + "what did you expect?" correction | MAJOR | `src/pat/web.py:342-390` | none | RECORDED ✓ |
| Grouped example-question library → 4 canned suggestions | MINOR | `src/pat/web.py` home chips | `pat_dock.py:94-96` | RECORDED ✓ |
| Avatar / face picker (`flow=face`) | COSMETIC | `src/pat/web.py:3407` | none | RECORDED ✓ |
| _LLM fallback classifier removed — model-free by construction (₹0)_ | **DELIBERATE** | `src/pat/engine.route()` | `pat_dock.py:255-258` | RECORDED ✓ |

### 8k. `inbox` — recorded NA (owner decision queue). Verified: `POST /dash/inbox/decide` (`src/web/review_inbox_view.py:374-376`), owner-only `?fmt=csv` (`:313-323`). **Not a gap.**

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| One residual: the **anonymous-visitor half** — "how often the machine is right" stats table + explainer, a PUBLIC trust claim — has no Graphite home | MINOR | `review_inbox_view.py:352-354`, `:368-372` | none | FRESH |
---

## 9. The stock dossier — classic `/dash/stock` (10 tabs) vs `/dash/home/stock` (11 sections)

**Classic tabs** (`src/web/dashboard.py:6881-6886`, F&O conditional at `:6885`):
`price · pos · mep · rs · qual · cpr · cci · news · seasonal · fno`. Panes at `:6936`, `:6983`,
`:6990`, `:6993`, `:6999`, `:7002`, `:7005`, `:7008`, `:7011`, `:6887`. Header carries the verdict
strip (`:6842`), theme chips + `+tag` (`:6866-6872`), track/capture (`:6804-6806`), a compare picker
`?cmp=` up to 12 (`:6670-6720`) and a Wolfe-wave button (`:5930`).

**Graphite `SECTIONS`** (`src/web/home/stock_page.py:40-64`), 11 keys:
`chart · own · pos · mep · rs · qual · cpr · cci · setups · fno · disc`, plus a context rail
(`:744-792`): News · Next results · Corporate actions · Peers · Go deeper.

### 9a. Recorded drops (with the reason W1 recorded, so the owner can overrule)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded reason |
|---|---|---|---|---|
| **Drawing engine** — trendline / ray / rect / Fib / Fib-ext / text / measure + magnet + hide-all + per-symbol persistence via `/dash/drawings` + per-drawing level editor + cross-drawing Fib confluence | MAJOR | `src/web/stock_chart.py:553-556`, `:820-1130`; tool palette `:1130` | `src/web/home/stock_chart_g.py:12-14` — explicitly not reproduced | RECORDED: "banned imports; linked to classic" (`docs/graphite-cutover-orchestration.md:88-91`) |
| **Overlay engines** — Wolfe · CPR multi-TF ladder · MA/EMA · MEP | MAJOR | `dashboard.py:45-48`; `src/web/cpr_overlay.py:55-120`; `src/web/indicators_overlay.py:16-53` | none | RECORDED: same entry |
| **Seasonality section** + the event-cadence card | MAJOR | `dashboard.py:6776-6787`, pane `:7011-7013` | absent from `SECTIONS` | RECORDED: "legacy render module" |
| **Track-capture** form / snapshot write | MAJOR | `dashboard.py:6804-6806`, pane `:6934`, `?track=` at `:5921` | absent | RECORDED: "home already owns the write path" |

### 9b. Additional classic-stock capabilities missing (all FRESH-FOUND)

| gap | severity | classic evidence (file:line) | Graphite state (file:line) | recorded-or-fresh |
|---|---|---|---|---|
| **Interval resample D / W / M / Q** — the Graphite chart is daily-only | MAJOR | `dashboard.py:6944-6949` (`#ivBar`); rebound handler in `stock_chart.py` (`[data-ptf]`) | `stock_chart_g.py:28` — `RANGES` only, no interval control | FRESH |
| **Chart types** — Candles / Hollow / Heikin-Ashi / Line / Area / Renko / Kagi | MAJOR | `stock_chart.py:436-440` (`typeSel`) | `stock_chart_g.py:194-196` — candlestick only | FRESH |
| **Lower pane** — Volume · RSI(14) · MACD(12,26,9) in a synced sub-chart | MAJOR | `stock_chart.py:461-470` | none | FRESH |
| **Indicator family** — VWAP · Anchored VWAP · Bollinger(20,2σ) · ATR bands(14) | MAJOR | `stock_chart.py:453-459` | none | FRESH |
| **Compare / multi-symbol rebased overlay** (up to 12, `?cmp=`, staged picker) | MAJOR | `dashboard.py:5921`, `:6604`, `:6670-6720`, `_COMPARE_MAX=12` `:7855`; rail `stock_chart.py:472` | links out to classic `/dash/compare` — `stock_page.py:782-783`; no in-page overlay | FRESH |
| **Harmonic XABCD** and the **RS docked lane** strategy chips | MAJOR | `stock_chart.py:449-452`, `:446` | none | FRESH |
| **DVPT inertia table** — today vs every R and P baseline with the ×-today gauge | MAJOR | `dashboard.py:6231-6242` | `stock_page.py:345-406` — a single "intensity vs 1-month power" row (`:352-354`) | FRESH |
| **Accumulation-character panel** — WHO/WAY/CTX split bar + the plain-English `accum_character_read` | MAJOR | `dashboard.py:6252-6300` | `stock_page.py:359-360` — a bare label row | FRESH |
| **Momentum pane** (`momentum_pane.card_html`) on the RS tab | MAJOR | `dashboard.py:6537-6542`, pane `:6997` | `stock_page.py:427-450` has slopes/MA flags but no momentum pane | FRESH |
| **RS overlay chart** (ratio-vs-index series, lazily booted via `__bootRS`) | MAJOR | `dashboard.py:6533`, `:6699-6718`; boot hook `:6899` | none | FRESH |
| Active-overlay legend / "Read" strip naming each live overlay with its caveat | MINOR | `stock_chart.py:494-520` | none | FRESH |
| Launch-band read on key price (🎯 −1%…+5%, the "under institutional cost" / "extended" narration, the ticket/surge meta line); the 2M horizon is also dropped | MINOR | `dashboard.py:6193-6229` | `stock_page.py:366-380` — prices + gaps, no band verdict | FRESH |
| Zone discount / at-cost / above traffic-light (🟢🟡🔴) and the P-tier / R-tier split labels | MINOR | `dashboard.py:6134-6150` | `stock_page.py:383-388` — a flat list of 5 zone rows | FRESH |
| Insight block | MINOR | `dashboard.py:6342-6353` | no counterpart | FRESH |
| Sector-context strip on the RS tab | MINOR | `dashboard.py:6547-6574` | `stock_page.py:441-447` — two kv rows | FRESH |
| News as a full timeline tab; Graphite caps at 8 rail headlines | MINOR | `dashboard.py:6767`, pane `:7008-7009` | `stock_page.py:747-758` (`news[:8]`) | FRESH |
| Theme chips + `+ tag` editor deep-link in the header | MINOR | `dashboard.py:6860-6872` | `stock_page.py:177-178` — first 3 themes as static chips, no editor link | FRESH |
| Corporate-action-adjustment warning on the zone overlay | MINOR | `dashboard.py:6957` (`zone_action_recent`) | no such banner in `stock_chart_g.py` | FRESH |
| Glossary `?` popovers on the tab labels (`_TABGLOSS` for pos/mep/rs/qual/cpr/cci) | MINOR | `dashboard.py:6875-6880` | `stock_page.py:313-319` — plain links | FRESH |
| Verdict strip (`_ck_strip` KPI band) → digest tiles (comparable, but conviction is a different composite) | MINOR | `dashboard.py:6842`, `:6932` | `stock_page.py:222-257` | FRESH |
| `⌁ Wolfe wave` header button → `/dash/wolfe?sym=` | COSMETIC | `dashboard.py:5930-5933` | a badge, and only when `in_zone` — `stock_page.py:303-304` | FRESH |
| **No per-symbol RRG journey and no per-symbol RS-band channel** — both claimed by `sideways_parity.py:160-162` to live "on the Graphite stock hub" | MAJOR | `src/web/rrg_view.py:744-821`; `src/web/rsband_view.py:729-767` | `stock_page.py:40-64` has no rotation/band section; `sec_strength` (`:427-450`) is a key-value read | RECORDED-BUT-FALSE (see §1a) |

### 9c. Graphite ADDITIONS on the stock page (net gains, for balance)

Setups (X-04/07/09) · Own history (5-metric, 3-year, corporate-action-adjusted, gate-pinned) ·
Ownership & disclosures (SEBI PIT / SAST / Reg-29) — `stock_page.py:539`, `:656`, `:685`; folds
recorded at `stock_page.py:44-63` and ledger `:170-186`.
Pro-gating check: the `own` panel `ref_chip`s (`stock_page.py:671`) and the `pos` reference row
(`:401-403`) are `.pro-more`, but classic has no equivalent reference layer and the raw values stay
free — **not a gap**.

---

## 10. Disposition ledger — what `lane/parity-truth` did with this register (2026-07-28)

The register's own headline finding was that **the parity board over-claims**. This lane closed
that half: it corrected `src/web/sideways_parity.py` so the board's dispositions match this
document, and fixed the two XS correctness defects the audit found. It fixed **no capability rows**
— those remain the fix program's P1-P7 work.

**THE RULE APPLIED (one rule, every key):** a surface is downgraded `PORTED` → `DEFERRED` when
this register holds **≥1 MAJOR row against it that is still open on `HEAD`**. A key keeps `PORTED`
only when every MAJOR row against it is closed — by a fix landing in this lane, or by work already
on `main` since the audit's base `ba2c259`. MINOR/COSMETIC residue never forces a downgrade; it
earns a correction to the note instead. The cross-cutting rows (§0 X-1…X-6) are counted once in §0
and are deliberately NOT used to downgrade individual keys.

**Re-verification against `main` (`6fa87d3`):** the audit ran at `ba2c259`, before W6 `276762c`.
W6 touched `internals_pages.py` · `screen_pages.py` · `shell.py` · `stock_page.py`, but only at
link/nav level (DESTS repoints, the Markets-depth cross-link strip, 3 retargeted classic links) —
it closes §0 X-3 and a handful of MINOR link rows, and **no per-surface MAJOR row**. Spot-verified
still-open on HEAD before downgrading: `_ROT_PERIODS` = 6/12/24 with `data-pro` on 12M/24M · zero
`svg` in `strength_pages.py` (capture scatter) · `_fno_table(board, 12)` free / 200 Pro · no `memo`
route in `trust_pages.py` · no verdict-numbers table in rule-lab · no `pat/board/save` in
`screen_pages.py` · no flow router in `pat_dock.resolve()`.

### 10a. Downgraded PORTED → DEFERRED (34)

`rrg` · `rotation` · `cycle-clock` · `rs-hub` · `leaders` · `capture-map` · `sectors` ·
`sector-momentum` · `market-internals` · `participants` · `fno` · `results-reactions` ·
`buyback-calc` · `surveillance` · `attention` → **M-Markets**;
`dashboard` · `portfolios` · `watchlists` · `performance` · `import` · `stocks` · `classics` ·
`factor-league` · `concalls` · `insider` · `ratings` → **M7**;
`screen2` · `themes` → **M8**;
`coverage` · `reading-guide` · `rule-lab` · `replay-any-date` · `evidence-pack` · `pat` → **M6**.

Each note keeps its `LANDED at <route>` clause (a DEFERRED target is a milestone, so the route
would otherwise be lost) and gains one `RE-OPENED by the 2026-07-28 gap audit (register §X, N
MAJOR)` line naming the specific open rows.

**Board before → after:** PORTED 56 → **22** · DEFERRED 11 → **45** · DROPPED **5** · NA **2** ·
UNSCOPED **0** · 74 surfaces (verified by executing `summary()`).

### 10b. Listed but kept PORTED — 1

* **`band-locks`** — its ONLY MAJOR row was the live correctness defect in §3j, **fixed in this
  lane**. Residue is MINOR/COSMETIC (Close column · longest-streak tile · ⚑ flag marker · 30-row
  cap · cross-link), so under the rule above it keeps `PORTED` with a gap note.

### 10c. Milestones re-opened

`M6` · `M7` · `M8` flip **DONE → PLANNED**: each now holds non-PORTED surfaces, which
`test_done_milestones_are_fully_ported` fails on by design. `M-Markets` was already PLANNED.
`M3/M4/M5` keep DONE but **hold no routed lens at all**, so that gate passes over them vacuously —
recorded in `MILESTONES`, because §9's 20 fresh MAJOR stock-dossier rows are invisible to it (the
dossier is an integration hub, not a registry lens).

### 10d. The two XS correctness defects — FIXED

| defect | register row | fix | pin |
|---|---|---|---|
| band-locks direction case (`"UP"` vs `"up"`) — every row read "▼ lower", both tiles 0 | §3j row 1 | `internals_reads.is_upper_lock` / `is_lower_lock` case-fold once; `internals_pages._bandlock_block` calls them instead of comparing inline | `tests/test_graphite_parity_defects.py` (4 tests; RED pre-fix: tiles `up=0 down=0`, both rows "▼ lower") |
| seasonal ISO-week grid structurally dead (read asks `axis='week'`, engine persists `'iso_week'`) | §4b row 1 | `w2_reads` translates at the store boundary (`_STORE_AXES` / `_AXIS_TO_STORE` / `_AXIS_FROM_STORE`) — grid, cell-drill and outlook all reach the real rows; page/URL vocabulary stays `week` | same file (4 tests; RED pre-fix: no `week` key, empty stack, no "By week of the year" section) |

Both pins assert the ENGINE's vocabulary too (`band_lock` emits `UP`/`DOWN`; `seasonal_tape` writes
`iso_week`), so a future engine rename trips the gate instead of silently blanking a board again.

### 10e. The 7 RECORDED-BUT-FALSE notes — all rewritten

| # | key | what the note claimed | what it now says |
|---|---|---|---|
| 1 | `rrg` (also §9b) | the `?idx=` and `?sym=` drills "belong to the Graphite stock hub" | neither is on the stock hub nor built anywhere — both are open MAJOR rows |
| 2 | `seasonal-tape` | the ISO-week script grid SHIPPED | it could never render (axis-key mismatch); FIXED here, and the Pro forward-outlook regression is now recorded |
| 3 | `model-books` | "the Tracker carries the 'follow a book' view … as a section of `/dash/home/tracker`" | it does not — prose + two links, one back to classic, as the module docstring concedes. DROP verdict stands; the follow/adopt WRITE has no Graphite door and the classic-public estate is invisible |
| 4 | `stocks` | "NOT carried: the 14 default-hidden columns" | 3 of the 14 (RS#, 52w-hi, Gap3m) ARE carried; 11 are not |
| 5 | `conviction` | "NOT carried: the client-side filter pills" | incomplete — the MEP-confirmation and entry-read COLUMNS also vanished (disposition unchanged: no MAJOR) |
| 6 | `mep` | "the full component columns" | not the full set — the raw daily `mep_score` is absent and the cap fell 300 → 80 (disposition unchanged: no MAJOR) |
| 7 | `launchpad` | "NOT carried: the regime banner and the genuine-buyer count tile" | ALL FOUR count tiles are gone (disposition unchanged: the regime banner was the only MAJOR and was already recorded) |
| + | `insider` | recorded with NO residual at all | four controls and two columns missing — the 8th correction, and it forced a downgrade rather than only a note fix |

### 10f. Escalated, then RULED ON — 5 more downgrades (orchestrator, 2026-07-28)

Applying §10's rule mechanically to every key — not only to the ratified list — found five more
surfaces still `PORTED` while holding an open MAJOR row **whose loss their note does not name**.
This lane flagged them rather than acting unilaterally; the orchestrator ruled **"the rule is the
rule, uniformly"**, so all five were downgraded in an addendum commit under identical treatment
(`LANDED at <route>` clause + a `RE-OPENED` line citing the row):

| key | → milestone | open MAJOR the note did not name | register |
|---|---|---|---|
| `actions` | M-Markets | the Pro-gated just-went-ex context is ALSO cut ~16× under the gate (30d/200 rows → 14d/12; security_events 180d/40 → 14d/6) | §3e row 2 |
| `divergence` | M-Markets | every divergence name is a click-through to its RS-momentum pane in classic; Graphite names are dead text | §3b row 1 |
| `sast` | M7 | the 30/90/180d window selector and the `?feed=` class filter did not travel (only the per-symbol drill was recorded) | §6i rows 2-3 |
| `strategy-ref` | M6 | the "Open the live surface this page describes →" hand-off strip (a ratified 2026-07-15 requirement, on 13 of 16 pages) has no twin | §8d row 1 |
| `model-portfolios` | M7 | recorded as a missing "time-travel stepper UI" = a CONTROL; the whole CAPABILITY is missing — **verified by mechanism, not by reading the row**: `book_holdings(conn, book, asof="")` accepts the parameter, its ONLY caller `strategies_pages.py:123` never passes it, and the books route never reads `?asof=`, so past-rebalance holdings are unreachable by any URL | §6b row 1 |

**Board after the ruling:** PORTED 22 → **17** · DEFERRED 45 → **50** · DROPPED 5 · NA 2.

Left `PORTED` deliberately, and the rule agrees: `strategist` · `growth` · `launchpad` · `shp` ·
`event-cadence` each hold MAJOR rows their notes DO name honestly, so there is nothing to correct.
