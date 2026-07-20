# M4 — THE STOCK HUB (v3 evidence-scroll) · module specification for owner review

> **Lifecycle: TRANSIENT** — retire when: M4 ships and its landing record is folded into
> `docs/redesign-coordination.md` §5 + PROJECT_STATE; then `git rm`. Fold into:
> `docs/redesign-coordination.md`.

**Status: SPEC ONLY — no code. Built only on explicit owner go.** Codex reviewed 2026-07-21:
`VERDICT: APPROVE-WITH-CHANGES` — 1 BLOCKING (pt14 has no existing panel function to wrap;
fixed below) + 6 ADVISORY (1 naming fix applied — `sector_peers`→the real `/dash/api/peers`
read; 5 confirmations, no change needed). Full text: `docs/codex-review/M4-STOCK-HUB-CODEX.md`;
dispositions: `docs/redesign-coordination.md` §3b. **Gemini review NOT run** — no working
credential on this machine (cached OAuth is `IneligibleTierError`-dead per the known 2026-07-17
channel limitation, and no `GEMINI_API_KEY` is configured anywhere); owner action needed before
that leg can run.
Inputs (all ratified 2026-07-20): Part II §A archetype · §C nav contract · §D connectivity ·
§E journeys · Part III §J columns · Part IV §L–§O component contracts (§M comparison, §N
dense-rail, §O gap list) · Part V convergences (narrative digest). Composes with the DEPLOYED
M0–M3 modules (shell_v3 grid + dock slot · term chips · news dock). Everything below reuses
data and panels that exist today — **zero new tables, zero new timers**.

## 1. Scope and non-goals

- **Route:** `GET /dash/preview/stock?sym=` (INTERNAL_DEV in the route gate + nav-gate
  allowlist, like every preview surface). The legacy `/dash/stock` is UNTOUCHED and stays the
  default site's dossier until cut-over ratification.
- **Non-goals:** no chart-engine rewrite (the proven `stock_chart.py` snippet + its overlay
  seams are wrapped, not replaced) · no new metrics · no Pat changes (the hub is not a new
  lens; Pat coverage is unaffected) · no cut-over.

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

## 3. The chart section — §N and §M applied

- **Reuse:** `stock_chart.py`'s snippet renders inside the Chart section with its overlay seams
  (`window.__wfpc`, `[data-ptf]`, `#stratBar`/`#cprBar` anchors) untouched — CPR/MEP/Wolfe/
  Harmonic/MA overlay modules keep binding with zero edits.
- **The dense-rail treatment (§N, reference implementation):** a NEW v3 rail wrapper renders
  ⭐ pinned tools (seed: Trend line · Horizontal line · Fib retracement) + the MRU slot +
  `All tools ▾` grouped dropdown (Lines · Shapes · Fibonacci · Annotate · Measure); modifiers
  (magnet · conflux · hide-all · manage) stay outside as modes. Pins + MRU in localStorage.
  The indicator and strategy chip rows get the same treatment (both exceed six with injected
  overlays counted). Implementation shapes the EXISTING rail via a wrapper module — the legacy
  chart on `/dash/stock` is untouched.
- **The comparison contract (§M):** the chart's compare set initializes from **`?cmp=`**
  (comma-separated, cap 4 on-chart), writes back via `history.replaceState` (URL = the state),
  and "Open in Compare →" hands the full set to `/dash/compare` (cap 12) with the same
  rebase-to-100 semantics and window controls. The peers card quick-adds into the same `?cmp=`.
  This closes the census finding "compare selection lost on reload" for the hub.

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
| `src/web/hub_sections_v3.py` | section renderers — thin wrappers over the EXISTING panel functions (`_mep_stock_panel`, `credibility_fingerprint.card_html`, `seasonal_full_panel`, `momentum_pane` card, `_cpr_stock_panel`) + the checks-as-UI blocks. **Correction (Codex BLOCKING, 2026-07-21):** pt14 has NO existing panel function to wrap — its rendering is inline HTML inside the frozen `dash_stock` (`src/web/dashboard.py:6355-6394`), and `dashboard.py` is hard-frozen for ordinary feature work (`AGENTS.md`). pt14's v3 section is a NEW renderer in this file, reading the same underlying data (`fund`/`pscore`/`ca` — the cached fundamentals, pattern-score, and capital-allocation reads already used by `dash_stock`) without touching or extracting from the frozen file. |
| `src/web/chart_rail_v3.py` | the §N dense-rail wrapper + §M `?cmp=` URL-state shim around the existing chart snippet |
| `tests/test_v3_stock_hub.py` | contract tests: all sections present per data availability · checks blocks render with thresholds · one related strip ≤5 · `?sym=`/`?cmp=` discipline (`?symbol=` never emitted) · no v3 leak to legacy · 375px overflow-free · payload budget |

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
