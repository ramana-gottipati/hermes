# Graphite Home — fresh-and-parallel build spec (pre-build)

**Class: SPEC (pre-build).** The engineering contract for the new v3 home section. Build is gated
on the owner's explicit go + a Codex review of THIS spec (redesign-coordination §1.4). This spec is
the *how-to-build*; the *look* is the ratified blueprint `scratchpad/v3-home-blueprint.html`
(artifact `aff1743c`). Retire condition: folds into PROJECT_STATE §Decision log once the section
ships and the old preview is deprecated.

---

## 0. The decision this implements (owner, 2026-07-23)

Build **FRESH-AND-PARALLEL**: a completely new, self-contained section.
- **ZERO changes** to the classic site (`/dash/*`) AND **zero changes** to the existing v3 preview
  (M0–M5: `v3_preview`, `today_v3`, `shell_v3`, `ui_tokens_v3`, `ui_skin_bold`, `news_dock`,
  `stock_hub_v3`, …) **until** the new home is confirmed done + ready.
- **Only then** deprecate the old preview (§12). Until then the old one is a frozen reference too.
- Identity = **direction B (Graphite Instrument)**; experience = visual-first · expandable drawers ·
  floating alive Pat · dual-persona (beginner + expert) · futuristic but **data-earned** motion.

## 1. Isolation contract (the safety property — machine-enforced)

| Guarantee | Mechanism | Test |
|---|---|---|
| No classic-site byte drift | never open a legacy file | `test_home_isolation`: curl/byte-diff `/dash` pre/post |
| No existing-preview drift | never open a `*_v3`/`v3_preview`/`ui_skin_bold` file | byte-diff `/dash/preview` pre/post |
| No cross-import | legacy + existing-preview import **nothing** from `src/web/home/`; `home/*` imports only leaf helpers + read-only data reads | AST import scan |
| CSS cannot leak | tokens on `:root[data-ui-g]`, components `.g-*` — isolated from BOTH `ui_kit`/`.uk`/`:root{}` AND `data-ui-v3`/`.pv3-*` | string scan: no `:root{`, no `.uk`, no `.pv3`, no `data-ui-v3` |
| No middleware reshape | home shell omits the legacy markers (`.uk-sub`, `id="uk-main"`) AND the preview markers | render scan |
| Declared routes only | new routes registered in the route gate as `INTERNAL_DEV` | `test_dash_route_registry` |

**The ONE pre-existing file touched:** the app-wiring entrypoint gets **one additive mount line**
(register the new router). That is inherent to adding any route section and is *not* a change to
the existing preview's or classic site's behaviour — it registers a new sibling. Everything else is
new files under `src/web/home/`. (Flagged transparently; owner already approved this touchpoint.)

## 2. Placement + mount

- New package **`src/web/home/`** (self-contained). Names owner-tweakable (§13).
- Section root route **`/home`** (opt-in). Opt-in cookie **`pvg`** (distinct from `pv3`).
- `src/web/home/__init__.py` exposes `router: APIRouter` + `wire(app)`; mounted via the existing
  additive `v2_surfaces._ROUTER_SPECS` list (survives redeploy) — **one new entry, no existing entry
  changed** — or a single `main.py` include if cleaner. Reversible = remove that one entry.
- Routes: `GET /home` (composed home) · `POST /home/toggle` (opt-in, POST-only per playbook #11) ·
  `GET /home/_kit` (component showcase, INTERNAL_DEV). Future zone-detail routes under `/home/*`.

## 3. Identity tokens (`src/web/home/tokens.py`)

Graphite, both themes, **AA-verified** (`scratchpad/aa_check.py` dark; light accent `#096b65`;
`scratchpad/candle_aa.py` candles). Scope `:root[data-ui-g]` + `[data-theme="light"]`.

- **Dark (signature):** bg `#080b11…#243040` · line `#223040/#2c3d4f` · ink `#e8eef4/#9fb0c0/#6f8394` ·
  accent `#17b0aa` (+hi `#2fe6da`, on-acc `#04211f`) · up `#3ad17f` down `#f2617f` warn `#f4b740`.
- **Light:** bg `#eef2f5…#dde5ec` · ink `#101a22/#45586a/#667a8b` · accent `#096b65` (+hi `#0f857f`) ·
  up `#0e8a57` down `#c93a52` warn `#96660a`.
- **Candles (invariant identity, AA-corrected light):** dark up `#4d9dff`/dn `#8496ad`
  (lines `#a9d0ff`/`#c6d1e2`); **light up `#1668cc`/dn `#6f8096` (lines `#5b93da`/`#455468`)** — the
  #9 fix.
- Type: one UI face + tabular-mono numerals (Part IV §L). Geometry: moderate radius, hairline
  borders, subtle glow — **no** legacy chamfer/aurora.
- **AA gate** `tests/test_home_tokens_aa.py`: computes WCAG contrast for every token pair, both
  themes; asserts ≥4.5 (text) / ≥3.0 (graphical incl. candle fill+outline). Enforced like the
  label/ret-vol gates (the "devops" ask).

## 4. Shell + component kit (`src/web/home/shell.py`, `components.py`)

- **Shell:** top bar (brand · PREVIEW badge · 6 destinations · persona segment · theme · "Classic
  site" link) → **above-the-fold fence** → the zone grid → floating-Pat slot → footer fence. Own
  chrome; no legacy/preview markers.
- **Kit (`.g-*`):** tile · gauge · split-bar · **diverging-flow** · agenda-row · wire-row · drawer
  (`<details>`) · term-chip · count-tile · **provenance-chip** · sparkline · candle-mini. All
  builders are **DOM-safe** — data via `textContent`, SVG behind trusted static helpers, any rich
  snippet escaped (Codex #7). Full reduced-motion coverage (Codex #8).

## 5. Zones — each is a renderer over an EXISTING read (grounded in the inventory)

| # | Zone | Table(s) | Reuse read | Notes |
|---|---|---|---|---|
| 1 | Market pulse | `index_signals` (+`index_rows`), `market_internals_daily`, RRG `rs_extras` | `today_v3._mood_html` idiom; `cockpit` reads | index cards + NIFTY candle-mini + mood gauge + breadth; breadth carries an honest ⚠ as-of until §9 timer lands |
| 2 | Today / what-changed | `signal_alert_state`, `signal_events` | `today_v3._what_changed`, `whatchanged_flow` | severity count-tiles + humanised sym-linked rows |
| 3 | **FII/DII flows** | `fii_dii_flows` | **new** read-only `home/reads.fii_dii_recent()` | signed diverging bar (correct signed-value colour) + 10-session trend — the free win |
| 4 | Going-ex (upcoming CA) | `corporate_actions` (`ex_date≥today`) | `corp_actions.upcoming` | agenda strip |
| 5 | Results calendar | `board_meetings` (fwd 30d) | `results_calendar.upcoming_results` | agenda strip |
| 6 | News wire | `sent_news`, `news_symbol_tags` | `news_view._recent_market_news` / `news_dock` read | sym-tagged rows |
| 7 | Go-deeper drawers | `rs_extras` (RRG), `stock_signals.power_dvpt` | existing reads | progressive disclosure |

Optional later zones (owner §13): `results_reactions` PEAD tape · `slb_volumes` short-interest ·
delivery-spike leaders. **Every read is bounded + read-only; no table/timer/renderer is modified.**

## 6. Floating Pat (`src/web/home/pat_dock.py`)

- Alive guide: breathing/blink/look avatar · **data-bound** proactive bubbles (from the real
  what-changed/flows feeds, not canned) · typing indicator · typewriter.
- **a11y (Codex #4/#5):** `role="dialog"` + `aria-modal`, labelled by title; focus the input on
  open, return focus to the trigger on close; Escape closes; `inert` when closed; real controls
  (no fake tab roles / hrefs).
- Backend: **reuse the existing Pat closed-vocab engine** (`/dash/pat`) — deterministic, descriptive,
  SEBI-safe; never free-form advice. DOM-safe rendering. Register Pat coverage per
  `docs/pat-knowledge-contract.md` (DATA/EXPLAIN/NAV for every zone metric).

## 7. Dual-persona — real depth (Codex #3)

- **Beginner:** plain-English-first everywhere; **every code term is a glossary chip** (hover =
  definition, click = Pat-explain); one explainer caption per zone; Pat proactive/guided; a
  first-read path. No unexplained `RS`/`DVPT`/`pt14`/`CONVICTION` on screen.
- **Pro:** dense (more rows/precision); **evidence links** (numbers → the primary filing/source row,
  fiscal.ai pattern); sort/filter + **server-side CSV** on tabular zones (SURFACE-PLAYBOOK);
  keyboard-complete (`/` search, `E` expand, `P` Pat, column sort); guidance muted.
- Persist mode in `pvg_mode` (cookie + localStorage).

## 8. Motion — earned, not decorative (Codex #10)

Reveal-on-load (orientation) · gauge/bar draw-to-value (reveals the datum) · candle draw-in ·
**freshness pulse** when a zone's as-of = today · drill-expansion motion. Ambient field subtle;
**reduced-motion = none**. Every animation RM-guarded; nothing animates that doesn't carry data.

## 9. Data gaps handled in this build

- **`market_internals` timer** — add `hermes-market-internals.timer` (or fold `refresh_tail()` into
  the bhavcopy chain) so breadth isn't stale. Isolated infra add (new unit + captured drop-in), not
  a change to existing code. Interim: breadth ships with an honest as-of stamp.
- **FII/DII** — new read-only `home/reads.py`.
- **CA split** — two zones over one table by `ex_date` (no schema change).

## 10. SURFACE-PLAYBOOK compliance (binding, Guardrail #9)

Sister-data check (extend, don't duplicate — done: the inventory maps every zone to an existing
read) · `lens_registry` entry (or declared children, never orphan URLs) · education scaffold +
glossary term for every metric · fence · **Pat registration** (`tests/test_pat_coverage.py`) ·
server CSV where tabular · `sym` deep-links · nav labels plain-English-first · home-exposure
decision (the new `/home` is opt-in; default site untouched).

## 11. Deploy + reversibility

Writer-safe: scp new files (callees before caller, S158) → add the one mount entry → restart in a
**confirmed writer-clear window** (never ~14:01 UTC bhavcopy; check writers first) → health 200 →
public walk (all zones 200 with content · isolation 0-leak · classic + preview byte-unchanged).
**Reversible:** remove the one mount entry → section gone; classic + existing preview provably
unchanged throughout (the isolation tests prove it every commit).

## 12. Retire-old-preview plan (LATER — gated, not part of this build)

Only after the owner confirms the new home is **done + ready**: a clean separate change un-mounts +
deletes the existing preview modules (`v3_preview`, `today_v3`, `shell_v3`, `ui_tokens_v3`,
`ui_skin_bold`, `hub_sections_v3`, `stock_hub_v3`, `stock_chart_v3`, `ui_components_v3`,
`ui_showcase_v3`, `news_dock` if unshared) + their routes/tests. Guarded by the same byte-identity
test for the classic site. Nothing here pre-empts that step.

## 13. Open items for the owner (resolve at build review; defaults ship)

1. **Names:** route `/home` (vs `/dash/home` · `/next`) + package `src/web/home/` — default as written.
2. **Extra zones** beyond FII/DII: PEAD tape (`results_reactions`) · SLB · delivery leaders — default: FII/DII only for v1, extras as fast-follows.
3. **`market_internals` timer:** add now (breadth live) vs ship breadth with an as-of stamp + timer next — default: add the timer in the same build (small, isolated).
4. **Build increments (proposed):** (i) tokens + shell + kit + isolation tests; (ii) zones 1–3
   (pulse/today/flows); (iii) zones 4–6 (calendars/news); (iv) Pat + persona depth; (v) polish +
   walk. Each increment: gates green + additive + reversible.
