# Graphite Home — fresh-and-parallel build spec (v1.2, REVIEW-CLEAN, pre-build)

**Class: SPEC (pre-build).** The engineering contract for the new v3 home section. Build is gated
on the owner's explicit go + Codex review of THIS spec (redesign-coordination §1.4). The *look* is
the ratified blueprint `scratchpad/v3-home-blueprint.html` (artifact `aff1743c`). v1.1 folds in the
Codex OBJECT review of v1.0 (`docs/codex-review/GRAPHITE-HOME-SPEC-CODEX.md`) — 7 BLOCKING + 3
ADVISORY, all accepted. Retire condition: folds into PROJECT_STATE §Decision log at cutover.

---

## 0. The decision this implements (owner, 2026-07-23)

Build **FRESH-AND-PARALLEL**: a new, self-contained section. **ZERO changes** to the classic site
(`/dash/*`) AND **zero changes** to the existing v3 preview (M0–M5) **until** the new home is
confirmed done + ready; **only then** deprecate the old preview (§12). Identity = direction B
(Graphite Instrument); experience = visual-first · expandable drawers · floating alive Pat ·
dual-persona (beginner + expert) · futuristic but **data-earned** motion.

## 1. Isolation contract (v1.1 — the honest, load-bearing safety property)

**Key architectural decision (resolves Codex B1/B3):** during the parallel-build phase the section
is a **direct-URL, INTERNAL_DEV route** — reached only by typing the URL + the opt-in cookie, with
**no affordance in any classic chrome and NO `lens_registry` entry**. Because the classic nav is
*generated from* `lens_registry` (`v2_surfaces.py:211-230` builds `_IA_ALT/_IA_SUB` from it),
adding a lens now would change the classic nav — a zero-drift violation. So lens / Pat-coverage /
education / nav registration is **deferred to cutover** (§12), when nav changing is the intended
act. During build, playbook compliance = route-gate + fence + AA + the named home tests (§7).

**The existing files that WILL be touched — the complete, honest list (all additive-only):**

| File | Change | Behaviour-changing? |
|---|---|---|
| `src/web/v2_surfaces.py` | +1 `_ROUTER_SPECS` entry (mount the home router) | No — registers a new sibling; no existing spec edited |
| `tests/test_dash_route_registry.py` | + `INTERNAL_DEV` rows for `/dash/home*` | No — additive metadata (gate enumerates `/dash/*`; that's why the route is `/dash/home`, per B2) |
| `PROJECT_STATE.md` | mandatory same-commit state update | No — doc only |

**NOT touched during build:** `lens_registry.py` (would change nav), `test_pat_coverage.py`,
`test_education_coverage.py`, `docs/metrics-glossary.md`, and **no `*_v3`/`v3_preview`/`ui_skin_bold`
/legacy render module** (import ban, §5). Everything else is new files under `src/web/home/`.

**Machine-enforced guarantees (named gates in §7):** classic-site byte-identity · existing-preview
byte-identity · no cross-import (home ⇎ preview/legacy render modules) · scoped-CSS both directions
(no `data-ui-v3`/`.pv3`/`pv3` in Graphite HTML; no `data-ui-g`/`.g-`/`pvg` in preview HTML) ·
route-gate registration · own chrome (no `.uk-sub`/`uk-main`/`pv3-` markers → no middleware reshape).

## 2. Placement + mount

- New package **`src/web/home/`** (self-contained). Section root route **`/dash/home`** (under
  `/dash` so the existing route gate at `tests/test_dash_route_registry.py:216-223` covers it — B2).
- Opt-in cookie **`pvg`**; CSS scope `:root[data-ui-g]` + `.g-*` (distinct from `pv3`/`data-ui-v3`).
- `src/web/home/__init__.py` exposes `router: APIRouter`; mounted by **one** additive
  `v2_surfaces._ROUTER_SPECS` entry. Reversible = remove that entry.
- Routes: `GET /dash/home` · `POST /dash/home/toggle` (POST-only) · `GET /dash/home/_kit`
  (showcase, INTERNAL_DEV) · CSV endpoints for tabular zones (§6). All INTERNAL_DEV in the gate.

## 3. Identity tokens (`src/web/home/tokens.py`)

Graphite, both themes, AA-verified (`scratchpad/aa_check.py`, `scratchpad/candle_aa.py`). Scope
`:root[data-ui-g]` + `[data-theme="light"]`.
- **Dark:** bg `#080b11…#243040` · line `#223040/#2c3d4f` · ink `#e8eef4/#9fb0c0/#6f8394` · accent
  `#17b0aa`(+hi`#2fe6da`,on`#04211f`) · up `#3ad17f` down `#f2617f` warn `#f4b740`.
- **Light:** bg `#eef2f5…#dde5ec` · ink `#101a22/#45586a/#667a8b` · accent `#096b65`(+hi`#0f857f`) ·
  up `#0e8a57` down `#c93a52` warn `#96660a`.
- **Candles (invariant, AA-corrected light):** dark up`#4d9dff`/dn`#8496ad`(lines`#a9d0ff`/`#c6d1e2`);
  light up`#1668cc`/dn`#6f8096`(lines`#5b93da`/`#455468`) — the #9 fix.
- Type: one UI face + tabular-mono numerals (Part IV §L). Geometry: moderate radius, hairline
  borders, subtle glow — no legacy chamfer/aurora.

## 4. Shell + component kit (`src/web/home/shell.py`, `components.py`)

- **Shell:** top bar (brand · PREVIEW · 6 dests · persona segment · theme · "Classic site" link) →
  **above-the-fold fence** → zone grid → floating-Pat slot → footer fence. Own chrome; no
  legacy/preview markers.
- **Kit (`.g-*`):** tile · gauge · split-bar · diverging-flow · agenda-row · wire-row · drawer ·
  term-chip · count-tile · provenance-chip · sparkline · candle-mini. **DOM-safe** (Codex B/#7):
  data set via `textContent`; any rich fragment escaped; SVG behind trusted static string helpers
  that never interpolate untrusted data. Full reduced-motion coverage.

## 5. Zones — renderers over `src/web/home/reads.py` (self-contained; NO preview imports)

**Import ban (Codex B4/B5):** `home/*` must NOT import `today_v3`, `news_dock`, `shell_v3`,
`ui_components_v3`, `ui_tokens_v3`, `ui_skin_bold`, `v3_preview`, or any `*_v3` render module — those
return `pv3-*` HTML, not data. `home/reads.py` imports ONLY `src.core.db` + genuinely-shared,
non-preview, read-only automation helpers, and reimplements the rest as bounded SELECTs.

| # | Zone | Read (exact) | Source | Isolation note |
|---|---|---|---|---|
| 1 | Market pulse | `reads.index_pulse(conn)` (SELECT from `index_signals`+`index_rows`) · `reads.breadth_latest(conn)` (latest `market_internals_daily` row `d,adv,dec,pct_adv`) · mood via **`src.web.market_mood.market_mood`** (canonical, non-preview, carries the kill-switch — import it, render fresh `.g-*`; do NOT import `today_v3._mood_html`) | `index_signals`, `index_rows`, `market_internals_daily` | breadth carries an honest as-of stamp (no timer in v1, §9); mood uses the ONE canonical vocabulary (no drift) |
| 2 | Today/what-changed | `whatchanged_flow.changes(...)` (real read, `src/pat/whatchanged_flow.py:62-77` — `src/pat/` is NOT a preview module) + `reads.severity_counts(conn)` over `signal_alert_state` | `signal_alert_state`, `signal_events` | reuse the pure read; render fresh in `.g-*` |
| 3 | **FII/DII flows** | `reads.fii_dii_recent(conn, limit=10)` — `SELECT trade_date,category,net_value FROM fii_dii_flows WHERE category IN('FII/FPI','DII') ORDER BY trade_date DESC` (the REAL stored categories are `'FII/FPI'`\|`'DII'` per `deals.py:60,157` — Codex conv #10; table-guarded, as-of) | `fii_dii_flows` (`deals.py:60`) | new read-only helper; the free win |
| 4 | Going-ex (CA) | `corp_actions.upcoming(conn, days=21)` (`src/automation/corp_actions.py:492`, read-only) | `corporate_actions` | shared automation read, not preview |
| 5 | Results calendar | `results_calendar.upcoming_results(days=30)` (`src/automation/results_calendar.py:165`) | `board_meetings` | shared automation read |
| 6 | News wire | `reads.recent_news(conn, limit=8)` (bounded SELECT from `sent_news`+`news_symbol_tags`, reimplemented — do NOT import `news_view`/`news_dock`) + a **copied pure `_safe_url`** on every href (Codex #9) | `sent_news`, `news_symbol_tags` | href sanitised; regression test §7 |
| 7 | Go-deeper drawers | `reads.rrg(conn)` (`rs_extras`) · `reads.delivery_leaders(conn)` using the REAL columns `power_dvpt_1m…_12m` (default `power_dvpt_3m`; there is NO bare `power_dvpt` column — Codex B5) | `rs_extras`, `stock_signals` | correct column names |

Optional later zones (owner §13): `results_reactions` PEAD tape · `slb_volumes` · delivery leaders
promoted. Every read is bounded + read-only; no table/timer/renderer is modified.

## 6. Floating Pat (`src/web/home/pat_dock.py`)

- Alive guide: breathing/blink/look avatar · **data-bound** proactive bubbles (from the real
  what-changed / flows reads) · typing indicator · typewriter.
- **a11y (Codex B4/B5):** `role="dialog"` + `aria-modal` labelled by title; focus the input on open;
  return focus to the trigger on close; Escape closes; `inert` when closed; real controls (no fake
  `role="tab"` without keyboard, no `href="#"`).
- Backend: reuse the existing Pat closed-vocab engine (`/dash/pat`) — deterministic, descriptive,
  SEBI-safe. DOM-safe rendering. (Pat *coverage-gate* registration deferred to cutover, §12.)
- Tabular zones expose **server-side CSV** endpoints (Pro persona).

## 7. Named test gates (Codex B6 — prose is not a gate)

| Test | Asserts |
|---|---|
| `tests/test_home_isolation.py` | classic + existing-preview byte-identity pre/post · no cross-import (AST) · scoped-CSS **both directions** (Codex #8) · declared-routes-only |
| `tests/test_home_tokens_aa.py` | WCAG contrast every token pair, both themes; ≥4.5 text / ≥3.0 graphical incl. candle fill+outline (the "devops" candle gate) |
| `tests/test_home_pat_a11y.py` | rendered Pat has `aria-modal`, `inert`-when-closed, Escape handler, focus-in/return markup |
| `tests/test_home_dom_safety.py` | no data-bearing `innerHTML` without escape; news hrefs pass `_safe_url` (`javascript:`/`data:` collapse regression, Codex #9) |
| `tests/test_home_reduced_motion.py` | reduced-motion path renders no animated canvas + no transitions |
| `tests/test_home_persona.py` | Beginner vs Pro produce distinct DOM (glossary chips + explainers in Beginner; evidence links + dense controls in Pro) |

## 8. Dual-persona depth (Codex B3) · Motion (Codex #10) · reduced-motion

- **Beginner:** plain-English-first; every code term = a glossary chip (hover=def, click=Pat);
  per-zone explainer; Pat proactive; a first-read path. No unexplained `RS`/`DVPT`/`pt14`/`CONVICTION`.
- **Pro:** dense; evidence links (numbers → primary source row); sort/filter + server CSV;
  keyboard-complete (`/`,`E`,`P`,sort); guidance muted. Persist in `pvg_mode`.
- **Motion earned:** reveal-on-load · draw-to-value gauges/bars · candle draw-in · freshness pulse
  when as-of=today · drill-expansion. Ambient subtle. **reduced-motion = none**, gate-tested (§7).

## 9. Data gaps (v1.1 scoping — Codex B7)

- **`market_internals` timer: DEFERRED out of the home build.** v1 ships breadth with an honest
  **as-of stamp, no timer**. The timer is a **separate infra increment** (its own change): new
  `hermes-market-internals.timer` + `.service` + captured `scripts/systemd/vps-live/` drop-in +
  `OnFailure`/freshness + PROJECT_STATE update — NOT folded into the bhavcopy chain (that would edit
  existing infra). Owner picks timing (§13).
- **FII/DII:** new read-only `reads.fii_dii_recent` (SQL in §5).
- **CA split:** two zones over one table by `ex_date` (no schema change).

## 10. Playbook compliance — split by phase (resolves Codex B1/B3)

- **Build phase (now):** route-gate INTERNAL_DEV · fence · descriptive-only · AA · the §7 home
  tests · DOM-safe · own chrome. **No lens / no Pat-coverage-gate / no nav** (they'd change the
  classic site). Direct-URL only.
- **Cutover phase (§12, later, gated):** register the `Lens` (+ generated nav) · Pat coverage
  (`test_pat_coverage`) · education/glossary terms (`test_education_coverage`) · `sym` deep-links ·
  home-exposure — THEN retire the old preview. The nav change happens here, intentionally.

## 11. Deploy + reversibility

Writer-safe: scp new files (callees before caller, S158) → add the one mount entry → restart in a
**confirmed writer-clear window** (never ~14:01 UTC bhavcopy; check writers first) → health 200 →
walk (all zones 200 · isolation 0-leak · classic + preview byte-unchanged). **Reversible:** remove
the one mount entry → gone; the §7 isolation gates prove classic + preview unchanged every commit.

## 12. Cutover / retire-old-preview (LATER — gated, not part of this build)

Only after the owner confirms the new home is **done + ready**: (a) register lens/Pat/education/nav
(the intended nav change); (b) un-mount + delete the existing preview modules (`v3_preview`,
`today_v3`, `shell_v3`, `ui_tokens_v3`, `ui_skin_bold`, `hub_sections_v3`, `stock_hub_v3`,
`stock_chart_v3`, `ui_components_v3`, `ui_showcase_v3`, `news_dock` if unshared) + routes/tests.
Guarded by the classic-site byte-identity gate. Nothing here pre-empts that step.

## 13. Open items for the owner (defaults ship)

1. **Names:** route `/dash/home` · package `src/web/home/` — default as written.
2. **Extra zones** beyond FII/DII: PEAD tape · SLB · delivery leaders — default: FII/DII in v1,
   extras as fast-follows.
3. **`market_internals` timer:** default = **defer** (v1 breadth = as-of stamp, no timer); the timer
   ships as its own infra increment when you say go.
4. **Build increments:** (i) tokens + shell + kit + `reads.py` + the §7 isolation/AA gates;
   (ii) zones 1–3; (iii) zones 4–6; (iv) Pat + persona depth + a11y/DOM/RM gates; (v) polish + walk.
   Each: gates green · additive · reversible.

**Status: Codex convergence on v1.1 = `APPROVE-WITH-CHANGES` (all 7 BLOCKING + 2/3 ADVISORY
addressed; "no new blocking contradiction found"). The 2 remaining advisories applied → v1.2:
FII/DII category filter corrected to `'FII/FPI'`; mood imports canonical `market_mood`. The spec is
now REVIEW-CLEAN. → owner build-go → increment (i).**
