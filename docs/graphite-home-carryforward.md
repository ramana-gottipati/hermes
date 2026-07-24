# Graphite Home — carry-forward & takeover prompt (2026-07-23)

**Lifecycle: TRANSIENT** — retire when the Graphite Home cutover completes and folds into
PROJECT_STATE §Decision log + docs/redesign-coordination.md.

**Class: CARRY-FORWARD (TRANSIENT).** Retire when the Graphite Home cutover completes and folds into
PROJECT_STATE §Decision log + docs/redesign-coordination.md. The redesign approval record stays
`docs/redesign-coordination.md`; this file is the working handoff + the next-session prompt.

---

## 1. Where it stands — LIVE

- **`/dash/home`** — the from-scratch **Graphite** dashboard — is **BUILT · DEPLOYED · LIVE**.
  Public: `https://srv1704897.hstgr.cloud/dash/home` (append `?v=N` to bypass browser bfcache).
  Opt-in preview (`pvg` cookie), fully isolated; the classic site + old preview are byte-untouched.
- Package **`src/web/home/`**: `tokens.py` (Graphite palette, both themes, `:root[data-ui-g]`/`.g-*`,
  AA-gated incl. the corrected light candle) · `shell.py` (own chrome + destination bar + persona
  toggle + theme) · `components.py` (the `.g-*` kit: ribbon, tiles, gauge, split-bar, diverging-flow,
  agenda, wire, drawers, count-band, provenance, sym-link, DOM-safe) · `reads.py` (self-contained,
  import-ban on preview modules, defensive) · `demo.py` (representative preview data) · `pat_dock.py`
  (alive floating Pat, a11y) · `__init__.py` (router: `/dash/home` · `/dash/home/toggle` POST ·
  `/dash/home/_kit`). Mounted by ONE additive `v2_surfaces._ROUTER_SPECS` line (anchored patch on the
  co-edited VPS file — NEVER full-scp it).
- **Layout = owner-approved SCROLL-STACK** (rebuilt this session, commit `3d5637d`, DEPLOYED
  2026-07-23 ~18:13 UTC). The tabbed-hero mock was rejected by the owner (tabs HIDE cards) → the
  scroll-stack shows every card as you scroll and *promotes* a featured card instead of hiding the
  rest. Shape: **selectable ticker** (feed picker: indices · watchlist · portfolio · model · movers;
  globals dropped — no real source) → **MAIN** [**FEATURED** card you choose (Watchlist/Portfolio/
  Index chooser + ★ default, persisted per-browser) · **Market-pulse deck** · What-changed · News] →
  **RAIL** [FII/DII · Going-ex · Results · delivery drawer · toggle]. **⋮ pin/collapse/hide** on every
  stack card (localStorage restore tray). Floating alive Pat. Beginner⇄Pro + ◑ theme.
- **Market-Pulse deck** = 7 real reads (mood gauge · today's breadth · breadth-trend 30d · delivery
  conviction `avg_dp` · accumulation `mep_net` · new-52w-highs · dispersion · sector heat), each
  metric tile opens a 30-session trend. **Real-vs-demo honesty**: `_pick(live,demo)` marks each zone's
  chip "sample" when on demo. New defensive reads in `reads.py`; read-contract gate extended; new
  `tests/test_home_featured.py`. Suite 827 pass (only pre-existing `test_rule_lab` red).
- **Isolation PROVEN both directions** — byte-identity of classic + old preview; no cross-import;
  scoped CSS both ways; **read-contract gate** (`tests/test_home_read_contract.py`) pins every column +
  shared-helper signature the home reads. Six gates green
  (`test_home_isolation/_tokens_aa/_pat_a11y/_dom_safety/_reduced_motion/_persona`) + zones + contract.
  Full suite ~817 pass (the ONLY red is the research lane's pre-existing `test_rule_lab`, being fixed
  in a separate session — NOT this lane).
- **Data:** live reads with `demo.py` fallback per zone (owner directive — generate representative
  data when the live read is empty, so the preview shows the full experience).

## 2. This session's arc (chronological)

Fresh-identity samples (4 dirs) → owner picked **B Graphite** → experience prototype (energy + alive
Pat + Beginner⇄Pro) → **Codex `OBJECT`** (colour-doctrine, hype, a11y, DOM-safety, earned-motion) →
fixes → home-dashboard **architecture** (grounded inventory) → **blueprint** → **candle-AA** fix
(light down `#93a2b8`→`#6f8096` fill / `#455468` outline, computed) → owner: **build FRESH-AND-PARALLEL,
zero-touch existing** → build **increments (i)-(iv)** (foundation · zones 1-3 · calendars/news/drawer ·
alive Pat + persona) each green → **deployed** → **read-contract gate** (bidirectional-isolation
follow-up) → **owner design-feedback loop:** restore semicircle gauge · demo data · tile-grid ·
"fixed scrollable boxes, not a flat page" · MoneyControl-style **plan-first** → **2-region rebuild** →
review passes (clickable symbols · plain-English sources · nav on its own bar · gauge/breadth clarity ·
density · index-redundancy killed · news dedup). **Cross-author near-miss** caught + fixed
(`stock_chart.py` swept into a commit → soft-reset + specific-path re-commit).

## 3. Standing corrections — BINDING (violate none)

1. **Classic site = FROZEN REFERENCE** (zero edits, byte-identical). **New experience = from scratch**
   (no legacy palette/tokens; carry only doctrine + the blue-up/grey-down candle identity). [[ramana-working-principles]]
2. **Plan-first, deeply.** Approve/build = "plan it to depth first, then ask." STUDY reference products
   (e.g. MoneyControl) — how they organize each section — before building. Present the plan; build on go.
3. **Fixed-size boxes that scroll internally — NEVER a flat endless page.** You don't show everything at
   once; overflow scrolls inside the widget. Dense, tidy tiles; no dead full-width bars.
4. **Generate representative data** when a live read is empty (previews must look full) — but keep the
   **real-vs-demo line honest** (mark or wire placeholders; don't pass fake as primary).
5. **Crisp by default; detail on demand.** No walls of text. Short answer + link/decision; depth behind
   an optional "know more" affordance, only when relevant. **Calibrate the response format to the
   question** (a terse title vs a fuller/engaging answer — pick what fits).
6. **Plain-English, no jargon on-screen** (no raw table names like `index_signals`); symbols are
   **clickable** deep-links; every number links to its source; descriptive-only fences stay.
7. **Argue back, no sycophancy.** He wants the spine + the honest verdict, and is right that we're not
   "truly great" yet.
8. **Communication reaches him IN CHAT** with working links (`https://srv1704897.hstgr.cloud/...`, never
   raw IP:8000). **Constraint this session: the in-app browser was DOWN — pixels could not be verified;
   review was HTML-level only.** Get a real render (fix the preview OR an owner screenshot) before
   declaring visual quality. Cache: the page is `no-store` + the SW skips navigations, but bfcache holds
   old pages — hand out a `?v=N` cache-busted link.

## 4. OPEN — next feedback

**DONE + DEPLOYED this session:** ① section organization (scroll-stack) · ② Market-Pulse expanded
(7-tile deck) · ③ watchlist + portfolio (featured card, reuses `watchlist` + `stocks_in_play`) · ④
real-vs-demo honesty (sample badges; globals dropped) · **⑤ response-format calibration** (Pat ask
box + Telegram `chat.py` prompt) · selectable **ticker feed** · **pin/collapse/hide** · **classic-site
directory** in the top-right (whole classic site from `lens_registry`, one-way) · **analyst "today"
additions**: **regime one-liner** (top) + **Today's conviction** (reuses `stock_rs.conviction_shortlist`)
+ **Filings & ownership** rail card (insider + SAST). Commits: `3d5637d`·`3b41f73`·`a82330a`·`4f714b6`·`677203d`.
Everything deployed to `/dash/home`; suite 833 pass; classic + old preview byte-untouched.

**DECIDED (owner, 2026-07-24):** Today's conviction stays **STRICT** — the full all-three-pillars
definition (RS leader + accumulating + near entry). Do **NOT** widen it to near-misses to pad the
count; a short list (2 names on 2026-07-24) is the selectivity working as designed. If it reads as
"broken" to a viewer, the fix is legibility (a "N cleared all 3 pillars today" line), never loosening
the gate.

**STILL OPEN:**
1. **Owner PIXEL-review** — the Browser pane was down this session, so structure+gates were verified,
   not pixels. Hand a `?v=N` link (`https://srv1704897.hstgr.cloud/dash/home?v=N`); iterate on finish.
2. ✅ **Response-format calibration** (item #5) — BUILT in `pat_dock.py` (Pat answers = terse title +
   detail-on-demand `<details>`; typed ask box classifies + DOM-safely deep-links a symbol) AND in
   `src/assistant/chat.py` `HERMES_SYSTEM_PROMPT` (owner follow-up "calibrate the Telegram assistant
   too" — a RESPONSE FORMAT block: one-line for lookups, one-sentence + offer for explains, phone-chat
   tuned; prompt-only, no model/cost change; restart hermes-telegram + hermes-api). All 5 items shipped.
3. **Deferred, honest:** the Index featured view has NO sub-picker yet (v1 = NIFTY 50 focus) · no
   per-watchlist-row sparks (no cheap per-symbol series) · the **model** ticker feed is demo/sample
   until wired to the model-books estate · movers uses `bhavcopy_rows` day-change (confirm density).
4. **Mood-vs-green reconcile** — the gauge is 200-DMA breadth (medium-term) vs today's adv/dec; add a
   one-line explainer if the owner still finds it confusing on the live render.
5. **Cutover (PARKED)** — promote `/dash/home` into nav + redirect old `/dash/preview` → `/dash/home`,
   only after the Graphite stock page exists (old preview still uniquely serves `/dash/preview/stock`).

## 5. Deploy recipe (this section's, verified)

`scp src/web/home/*.py hermes:/opt/hermes/src/web/home/` (new modules — full-scp fine) → on box
`tr -d '\r'` each (NEVER `sed`) → `.venv/bin/python -m py_compile src/web/home/*.py` → import test
(`import src.web.home`) → **writer-safe restart** (guard drops hermes-api's own PID, block only on a
FOREIGN db writer; hermes-api startup is read-only so it's structurally safe) `systemctl restart
hermes-api` → verify `curl "…/dash/home?v=N"` 200 + structure. The mount line in `v2_surfaces.py` is
already deployed (anchored insert; the file is co-edited → NEVER full-scp it). Give the owner a
`?v=N` link. See [[vps-deploy-reality]].

## 6. Takeover prompt (paste to start the next session)

> Resume the Patearn **Graphite Home** (`/dash/home`) — the from-scratch v3 dashboard, LIVE + isolated
> at `https://srv1704897.hstgr.cloud/dash/home`. Boot: CLAUDE.md → `docs/graphite-home-carryforward.md`
> (this file) + `docs/redesign-coordination.md`. State: 2-region dashboard (ribbon · main[pulse+news
> hero] · sidebar[what-changed·FII/DII·corp-actions·results·+reserved watchlist]) built as the isolated
> `src/web/home/` package; 6 gates + read-contract green; suite ~817 (only the research-lane
> `test_rule_lab` red, not ours).
>
> BINDING corrections (see §3): classic FROZEN, new from-scratch; **plan-first + study reference
> products before building**; **fixed-size internally-scrolling boxes, never a flat page**; generate
> demo data but keep real-vs-demo honest; **crisp replies, detail on demand, calibrate format to the
> question**; plain-English + clickable symbols; argue back; **the in-app browser is down — verify HTML,
> get an owner screenshot for pixels, hand out `?v=N` links**.
>
> DO NEXT (plan each, get owner go, then build; deploy per §5): (1) **rearrange/organize the sections**;
> (2) **Market Pulse — add more entries, fill the empty space, make it interactive/engaging** — decide
> which first-page insights earn the space and how to present them; (3) **watchlist/portfolio** in the
> reserved slot; (4) real-vs-demo honesty fixes; (5) response-format calibration for Pat + chat. Cutover
> stays PARKED until the Graphite stock page exists. Report crisply.
