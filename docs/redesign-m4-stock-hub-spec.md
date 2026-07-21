# M4 — THE STOCK HUB (v3 evidence-scroll) · module specification for owner review

> **Lifecycle: TRANSIENT** — retire when: M4 ships and its landing record is folded into
> `docs/redesign-coordination.md` §5 + PROJECT_STATE; then `git rm`. Fold into:
> `docs/redesign-coordination.md`.

**Status: SPEC v1.1 — no code. Built only on explicit owner go, after review.**
TWO independent Codex passes converged into this revision (parallel lanes, reconciled
2026-07-21): (1) a pre-build pass returning `VERDICT: OBJECT` — 4 BLOCKING, all accepted
(the chart plan is an ADDITIVE FORK, a wrapper is infeasible against the closed IIFE ·
nav-contract implementation = requirement #0 · the §O stock-chart gaps carried in full with
acceptance tests · pt14/CPR reclassified as new-implementation-over-existing-reads · payload
budget = uncompressed initial HTML bytes < 1,000,000) — full text
`docs/codex-review/REDESIGN-M4SPEC-CODEX.md`; (2) a parallel pass returning
`VERDICT: APPROVE-WITH-CHANGES` — 1 BLOCKING (the same pt14 no-panel finding, independently) +
6 ADVISORY (peers naming corrected to the real `/dash/api/peers` read; 5 confirmations) — full
text `docs/codex-review/M4-STOCK-HUB-CODEX.md`. Dispositions: `docs/redesign-coordination.md`
§2/§3b. **Gemini channel DOWN** (no valid `GEMINI_API_KEY` anywhere + deprecated OAuth tier —
owner action needed); the two Codex passes stand as the spec-stage review. A final Codex
re-read of THIS merged text closes the OBJECT→revise loop before the owner go.
Inputs (all ratified 2026-07-20): Part II §A archetype · §C nav contract · §D connectivity ·
§E journeys · Part III §J columns · Part IV §L–§O component contracts (§M comparison, §N
dense-rail, §O gap list) · Part V convergences (narrative digest). Composes with the DEPLOYED
M0–M3 modules (shell_v3 grid + dock slot · term chips · news dock). Everything below reuses
data and panels that exist today — **zero new tables, zero new timers**.

## 1. Scope and non-goals

- **Route:** `GET /dash/preview/stock?sym=` (INTERNAL_DEV in the route gate + nav-gate
  allowlist, like every preview surface). The legacy `/dash/stock` is UNTOUCHED and stays the
  default site's dossier until cut-over ratification.
- **Requirement #0 — the shell implements the ratified nav contract (Codex B2):** M4 upgrades
  `shell_v3` (a v3-program module — editable by design) to carry the §C contract: the
  6-destination global bar with "you are here" marking · the per-destination left rail in fixed
  order (Stocks rail for this page) · the **user-invoked collapse/expand control** (rail starts
  visible; state persists in localStorage) · a breadcrumb slot (`Home › Stocks › <SYM>`). Same
  commit as the hub route; contract assertions join the test file.
- **Non-goals:** no legacy chart-engine edits (the v3 chart is an additive FORK — §3) · no new
  metrics · no Pat changes (the hub is not a new lens; Pat coverage is unaffected) · no cut-over.

## 2. Page anatomy — the evidence-scroll (Part II §A, committed)

Top to bottom; Context rail beside the Focus column ≥1280px (shell_v3's existing grid);
the M3 dock below, defaulted to the symbol's filter (`?sym=` carried).

1. **Breadcrumb + identity strip** (sticky, thin — §C.3/§C.6):
   `Home › Stocks › TCS` · name + sector/theme chips · CMP + day change (value contract
   colors) · the provenance line (trade date · "NSE bhav copy" — citation-per-claim §B.3).
2. **THE DIGEST** (the preview-index; SWS-inside-TradingView + the Part V narrative note):
   - The 8 verdict tiles, recomposed: each = a **term chip** (M2) showing the plain-word state
     with its number beside it, AND an **anchor link** to the section holding its evidence
     ("nobody chooses a tab cold").
   - **One narrative sentence**, auto-composed from fields we already store (template over
     `accum_character`, `rs_rank`, `trigger_rank`, pt14 tier, CCI tier — descriptive voice,
     fence-checked, e.g. "Delivery size has run above its own 3-month norm while relative
     strength holds the top quartile; quality gates pass 4 of 6."). No LLM — a deterministic
     template, unit-tested against the fence vocabulary.
   - **Fired-lens badges** (Part III §I.1): every lens currently flagging the symbol, as chips
     deep-linking `lens?sym=` (the StockEdge loop).
3. **Sticky section index** (the in-page nav, §C.6; becomes the mobile accordion spine):
   `Chart · Positioning · Accumulation · Strength · Quality · Structure · Credibility ·
   Seasonality · F&O*` (*renders only when a single-stock future exists — today's conditional
   kept). Order mirrors today's tab order minus News (News lives in the Context rail + dock,
   per the audit-converged disposition).
4. **Sections** — each existing tab's content, recomposed under one contract per section:
   - **Header:** plain-English title + term chip (once per section — §D inline rule).
   - **CHECKS-AS-UI block** where a gate exists (ratified Part II §F.2): pt14 renders its
     quality-gate pass/fail with the real threshold (QG ≥ 151.2/252) and the ×0.70 unverified
     haircut disclosed; the confluence pillars render as 6 named ✓/✗; CCI shows tier bands with
     the falsified-as-factor verdict line; MEP shows its descriptor-only chip. Failures render
     as loudly as passes.
   - **Digest first, ONE disclosure to the raw table** (§E; never a third level). Raw tables
     follow Part III §J column defaults with the saved-view/URL mechanics where tabular.
   - **The spoke link** (§C.5): "Full <lens> page for TCS →" carrying `?sym=`; the lens page's
     back-link contract ("‹ back to TCS") is that module's obligation, recorded in §O.
5. **Context rail** (co-presentation — the core M4 promise): news timeline
   (`render_stock_timeline`) · next results date (`board_meetings`) + last-concall CCI chip ·
   upcoming corp actions for the symbol · **peers card** (the existing peers read — `/dash/api/peers`
   backed by `_sector_symbols`, `src/web/symbol_search.py:177` / `src/web/dashboard.py:980`; corrected
   from the earlier "`sector_peers`" naming per Codex ADVISORY, 2026-07-21 — promoted from the
   hidden "+" rail to a visible card with one-tap add-to-compare) · seasonal
   cadence card. Every card ≤ its existing bounded read.
6. **Related strip** (ONE, end of Focus column, ≤5, registry-driven — §D).
7. **Footer fence** (shell_v3's existing line).

## 3. The chart section — §N and §M applied (v1.1: ADDITIVE FORK, per Codex B1)

- **The fork, honestly named:** `src/web/stock_chart_v3.py` — seeded from `stock_chart.py`'s
  snippet at build time with the BASE MD5 pinned in its docstring (deliberate, documented
  divergence; the legacy chart and `/dash/stock` are untouched). A pure wrapper is infeasible —
  the snippet is a closed IIFE with local compare state and an internally-built drawings rail
  (Codex B1, file:line-verified) — so the v3 chart owns its rail and state natively. At
  cut-over ratification the fork becomes the canonical chart; until then a sync note in both
  files' headers flags the pairing.
- **Native in the fork:** (a) the §N dense rail — ⭐ pins (seed: Trend line · Horizontal line ·
  Fib retracement) + MRU slot + `All tools ▾` grouped dropdown (Lines · Shapes · Fibonacci ·
  Annotate · Measure); modifiers stay outside as modes; pins+MRU in localStorage; the indicator
  and strategy chip rows get the same treatment. (b) the §M comparison contract — compare set
  initializes from **`?cmp=`** (cap 4 on-chart), add/remove writes back via
  `history.replaceState` (URL = the authority), a sessionStorage mirror provides the §M
  **carryover** so RRG/Compare/momentum open pre-staged; "Open in Compare →" hands the set to
  `/dash/compare` (cap 12), same rebase-to-100 semantics and window controls. (c) the type-2/3
  benchmark selector shared with the RS surfaces. (d) **gloss chips on rail labels + the
  education trio** on the chart section (§O). (e) **chart data CSV** — a "Download series CSV"
  affordance hitting a small v3 endpoint that re-serves the SAME bounded series server-side
  (playbook item 8; no client DOM blob).
- **Overlay seam compatibility:** the fork preserves the seam names (`window.__wfpc`,
  `[data-ptf]`, `#stratBar`/`#cprBar` anchors) so the committed overlay modules
  (CPR/MEP/Wolfe/Harmonic/MA) bind unmodified — asserted by a dedicated seam test, not assumed.
- **Drawings persistence** stays on the existing per-symbol local+server store (`chart_drawings`)
  — shared with the legacy chart by design (same symbols, same drawings).

## 4. Connectivity (§D applied, checkable)

Metric labels are term chips at first occurrence per section · every symbol anywhere is
`?sym=` · external filing links carry ↗ + `rel="noopener noreferrer"`, same-tab · the
verdict → evidence → methodology → validation chain is unbroken: every checks block links its
glossary entry, its `docs/strategies` page (origin-badged), and `/dash/testing`.

## 5. Journeys on this page (§E)

- **Newcomer:** digest reads top-down in plain words; the one-shot nudge (M6 scope, not M4)
  will point at a digest chip; "How to read this page" sits in the standard position.
- **Analyst:** `#section` deep links · `?cmp=`/`?sym=` URL state · one disclosure to raw
  tables · server CSV on the tables that are tabular (playbook item 8) · ⌘K reachable.
- **Skeptic:** every verdict decomposes in place; failures visible; provenance line at top.
- **Mobile:** sections collapse to accordions with the verdict visible in each collapsed
  header (§C.8); identity spine frozen; zero horizontal body scroll (gate-tested at 375px).

## 6. Data & payload contract

Per-section reads = exactly today's tab reads (census 1a–1j): `stock_signals` ·
`mep_signals` · `cpr_signals` · `pattern_scores`/`capital_allocation_scores` ·
`concall_scores` + fingerprint card · seasonal panels · `fno_oi_signals` · the peers read
(`/dash/api/peers` / `_sector_symbols`) · `board_meetings` · `corporate_actions` · news timeline.
**Payload discipline:** the initial
document renders the digest + chart + first section; heavy sections render server-side on
`?section=` expansion (simple links, no SPA), targeting **< 1 MB initial** vs the 2.7 MB
legacy dossier. All reads bounded; empty states teach (§E).

## 7. Module plan (files — all NEW, each revertible by its mount line)

| File | Contents |
|---|---|
| `src/web/stock_hub_v3.py` | route + page assembly + digest + narrative template + section index |
| `src/web/hub_sections_v3.py` | section renderers, MERGED from both Codex passes. **Verified-importable reuse:** `_mep_stock_panel` · `credibility_fingerprint.card_html` · `seasonal_full_panel` · `momentum_pane.card_html` · `_cpr_stock_panel` (callable, but the CALLER assembles its `by_tf` input from `cpr_signals` — caller-owned data assembly, per the OBJECT pass). **NEW renderer:** pt14/Quality — no panel function exists; its legacy rendering is inline HTML inside the hard-frozen `dash_stock` (`src/web/dashboard.py:6355-6394`), so the v3 section re-renders from the same underlying reads (`pattern_scores` · `capital_allocation_scores` · cached fundamentals) without touching the frozen file. Plus the checks-as-UI blocks. |
| `src/web/stock_chart_v3.py` | the additive chart fork (§3): dense rail · `?cmp=` authority + carryover · benchmark selector · gloss/education · series-CSV endpoint · seam-compatible anchors. (Supersedes the earlier `chart_rail_v3.py` wrapper idea — infeasible per the OBJECT pass's IIFE evidence.) |
| `shell_v3.py` upgrade | requirement #0 (nav contract) — v3-owned module, same commit |
| `tests/test_v3_stock_hub.py` | contract tests: all sections present per data availability · checks blocks render with REAL thresholds · one related strip ≤5 · `?sym=`/`?cmp=` discipline (`?symbol=` never emitted) · **overlay seam anchors present in the fork** · **chart CSV serves** · **`?cmp=` round-trips URL→chart→"Open in Compare"** · **nav bar/rail/collapse/breadcrumb assertions** · education trio + gloss on the chart section · no v3 leak to legacy · 375px overflow-free · **payload budget = UNCOMPRESSED initial-document HTML bytes < 1,000,000, asserted in-test; `?section=` URLs preserve `sym`+`cmp`+`ch` and anchor to the expanded section (Codex A5)** |

Mounts: 1 `_ROUTER_SPECS` line + route-gate INTERNAL_DEV row + nav-gate allowlist row (same
commit — the standing Codex B1 requirement).

## 8. Verification & review gates (per the D144 protocol)

Codex + Gemini review THIS SPEC before build (verdict grammar) → owner go → build in the lane
worktree → suite + route/Pat/education/nav gates + the isolation tests → local walk on 3
symbols (a liquid F&O name · a thin name · a data-gapped name) at 375/768/1280 → Codex
post-build diff pass → VPS deploy per the recipe (preview-only) → live walk → coordination §5
record. Estimated build: 2–3 sessions.

## 9. Owner decisions AT THIS SPEC'S REVIEW — DECIDED (Ramana, 2026-07-21)

1. **Digest tile ORDER: ADOPT AS SPECCED** (Conviction-composite · DVPT · RS · MEP · Quality ·
   CCI · Structure · 52w-context, mirroring today's live strip). No concrete reason to invent a
   new order absent evidence it reads better — preserving the existing order keeps zero
   re-learning cost for users moving from the legacy dossier to the v3 hub. Revisit only if a
   live walk surfaces an actual reading-order friction, not speculatively.
2. **The narrative sentence: ADOPT, with one requirement made explicit and checkable at build:**
   the contract test suite (§7's `tests/test_v3_stock_hub.py`) must exercise a representative
   sample of tile-state COMBINATIONS (not just the happy path — include mostly-neutral/no-data
   combinations), and the template must resolve through the same fence vocabulary the rest of
   the site uses, not a bespoke word list. This is the concrete safeguard against the real risk
   here: a single flowing sentence reads closer to a holistic judgment than 8 separately-labeled
   tiles do, which is exactly what "descriptive, never advice" must keep guarding against as this
   moves from spec to code.
3. **Mobile default: ADOPT AS SPECCED — Chart pre-expanded, all other sections collapsed.**
   This is the internally consistent choice: §6's own payload contract already scopes the
   initial render as "digest + chart + first section," so pre-expanding Chart costs nothing new;
   choosing "digest-only" would contradict that already-written contract. It also matches the
   near-universal competitor convention (TradingView, Tickertape, SWS) of leading with the chart,
   not a fully collapsed list.
4. **News placement: ADOPT AS SPECCED — Context-rail card + dock only, no separate section.**
   This was not actually a fresh open question — Part I §1f already ratified moving News out of
   the tab list into the Context rail, and this spec's own §2.3 already states that disposition.
   Restoring News as a section would reintroduce the exact same-content-in-two-places duplication
   the whole redesign has been removing since Part IV §L's "one contract per component type."

**All 4 decided; nothing in §9 blocks the others.** Next per §8: Codex + Gemini review of this
spec (as finalized above), then owner go, before any code.
