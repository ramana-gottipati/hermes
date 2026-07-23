# X-setups render lens — build spec (hand-off)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the render lens ships and its facts fold into
> PROJECT_STATE + `docs/strategies/`. Registered in `docs/DOC_INDEX.md` (class B). Authored S208
> (2026-07-23) as the hand-off for the owner/redesign-gated RENDER half of the X-compute surface
> build. The DATA half is LIVE (see below) — this spec is only the UI.

## 0. State: the data spine is DONE + LIVE; only the render is owed

- **Compute (S199–S204):** four descriptive research modules in `research/explosive_moves/` —
  `overnight_split` (X-04), `volume_shelves` (X-07), `base_breakout` (X-09),
  `calendar_conditioning` (X-10). Each hermetically selftested + under CI (`tests/test_research_selftests.py`).
- **Pre-compute (S205) + deploy (S207):** `src/automation/x_setups_signals.py` materialises all four
  scans nightly into the `x_setups_signals` table (+ `x_setups_meta` k/v). LIVE on the box:
  `hermes-xsetups-scan.timer` @ 17:01 UTC Mon–Fri under `.venv-research`; first automated run verified
  (as-of advances with the tape; ~4600 rows, single current as-of, `Result=success`).
- **X-10 render is ALREADY DONE (sibling S207) — and it PROVES the spine:** `/dash/seasonal-calendar`
  (`src/web/calendar_conditioning_view.py`) surfaces `calendar_conditioning` by reading
  `x_setups_signals.latest(conn, module="calendar_conditioning")` — LIVE, real data (1926 names), the
  full SURFACE-PLAYBOOK checklist met, gates green. Correctly placed in the **seasonal family** (per the
  sister-data check), NOT the Setups board. So the spine is validated as consumable, and this spec now
  scopes to the **remaining 3**: X-04 overnight · X-07 shelves · X-09 base-breakout (the explosive-move
  **SETUP** family). Cross-link the expiry/holiday cut to `/dash/seasonal-calendar` rather than repeating it.
- **This spec = the remaining render:** a read-only "Setups" lens over `latest()` for X-04/X-07/X-09.

## 1. The read (numpy-free, prod-venv-safe)

```python
from src.automation.x_setups_signals import latest      # pure sqlite/json — imports under the prod .venv
rows = latest(conn, module="base_breakout")             # ms read of the nightly snapshot; NEVER recompute render-time
```
`latest()` is numpy-free at module level (numpy lives only in the compute path), so the web layer
reads it safely under the stdlib-only prod venv. Freshness header comes from `x_setups_meta`
(`computed_at`, `asof`) → "as-of &lt;asof&gt; · nightly snapshot".

## 2. Decision-tree resolution (SURFACE-PLAYBOOK §2 — do NOT skip)

- **Sister-data check (mandatory):** X-09 base/breakout is **Launchpad-family** (COILED = *pre*-breakout;
  X-09 = the breakout event) → **cross-link Launchpad, do not duplicate**. X-10 expiry/holiday is
  **already DONE** (sibling S207 `/dash/seasonal-calendar`, seasonal family) → out of scope here; cross-link
  to it. X-04/X-07 have no sister board.
- **Shape — OWNER/REDESIGN CALL (the gate):** either (a) a standalone **Lens** "Setups" in the
  **Strategies** workspace (`/dash/strategies/setups`, §2.3), OR (b) per-symbol **dossier columns/embeds**
  on `/dash/stock` (§2.2) if the redesign lane's **M4 column architecture** routes them that way. This
  spec covers (a); under (b) the same `latest()` read + glossary/Pat/fence apply per column. **Confirm the
  shape with the owner/redesign lane before building** — that is why this is a hand-off, not a build.

## 3. The board (standalone-lens option)

- Route `/dash/strategies/setups` (D80 nesting). **PATCH** `lens_registry.py` (append one `Lens`,
  workspace=strategies, a rail group) + **anchored insert** in `v2_surfaces._ROUTER_SPECS` — NEVER
  full-scp those co-edited files (vps-deploy-reality D80 override).
- Three sections (X-10 lives in `/dash/seasonal-calendar` — link it, don't repeat), each a ranked table
  reading `latest(conn, module=…)`; every symbol cell links `/dash/stock?sym=` (param `sym`):

  | Section (module) | Columns |
  |---|---|
  | **Base breakouts** (`base_breakout`) | symbol · x09_score · base_length · base_depth · breakout_velocity · vol_surge · days_since_breakout · still_above_pivot · breakout_date — sort x09_score desc; cross-link Launchpad |
  | **Volume shelves** (`volume_shelves`) | symbol · poc · va_low..va_high · n_shelves · price_vs_va · last_close |
  | **Overnight vs intraday** (`overnight_split`) | symbol · on_share · cum_total_pct · overnight_pump (flag) |

## 4. Landing checklist (SURFACE-PLAYBOOK §3 — ALL same session, none optional)

1. **Registry** — `lens_registry.py` append (single nav source).
2. **Durable mount** — `v2_surfaces._ROUTER_SPECS` anchored insert.
3. **Education** — `infographics.bottom_line()` at top · `plain()` under each table · `how_to_read_link()` · glossary popovers on every metric column (via `dashboard._edu()`).
4. **Honesty fence** — descriptive-only (copy `insider_view.py`'s "descriptive, not advice" idiom); NO buy/sell/add/avoid/ride/fade verdict labels. The expiry/holiday section states the seasonal-null prior explicitly.
5. **Glossary keys** — add to `docs/metrics-glossary.md`: `x09_score, base_length, breakout_velocity, base_depth, vol_surge, on_share, overnight_pump, poc, value_area, n_shelves, price_vs_va` (machine-enforced: `tests/test_pat_coverage.py`). The calendar keys (`expiry_ret_delta`, pre/post-holiday) already exist (sibling S207).
6. **Pat registration** — DATA (the four tables) + NAV (Pat names+links "Setups"); machine-enforced `tests/test_pat_coverage.py`. Follow `docs/pat-knowledge-contract.md`.
7. **Strategy doc** — a `docs/strategies/` page for the X-compute descriptors, SAME commit (`tests/test_strategy_docs_coverage.py`); re-scp `/opt/hermes/docs/strategies/`.
8. **Export** — server-side `?format=csv` per table (the `wolfe_trades_view.py` pattern), URL-param-honoring.
8b. **URL state** — module/sort/filter as query params; CSV honors them; a shared URL reproduces the view.
9. **Symbol links** — every symbol cell → `/dash/stock?sym=` (param `sym`, never `symbol`).
10. **Home exposure** — DECISION: default **deliberately-not** (opt-in board); record in the commit. (A small "fresh breakouts today" count-tile is an owner option.)
11. **Writes** — none (read-only board); no state-mutating GET.
12. **State doc** — PROJECT_STATE §Key-paths + §Decision-log in the same commit (state-doc gate).

## 5. Verification

- **Local:** renders 200 + graceful empty-state + the three gates GREEN (`test_dash_route_registry`,
  `test_education_coverage`, `test_pat_coverage`). Because the box table is already populated (S207), the
  deployed board shows real rows immediately (no empty-until-first-run gap).
- **Box (walk-the-journey):** each section renders real names (e.g. base breakouts HUHTAMAKI/STALLION/TATVA),
  symbol links open the stock page, CSV downloads honor params, glossary popovers resolve, Pat answers
  "where are the breakouts". Deploy = scp the new view module + **patch** lens_registry/v2_surfaces +
  writer-safe `hermes-api` restart + `curl -sL` the route.

## 6. Blockers (why this is gated, not built)

1. **Owner/redesign** — the §2 shape decision (standalone board vs M4 dossier columns) is the redesign
   lane's M4 column-architecture call; building before it risks a reconcile-away.
2. Nothing else — the data is live, `latest()` is prod-venv-safe, the checklist is standard. Once the
   shape is chosen, this is a one-session build.
