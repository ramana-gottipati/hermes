# UI Restore + Migration TRACKER — what changed, what's missing, what to do

> **Created 2026-06-28** after Ramana flagged: the Trust page got a new modern UI but Markets still
> shows the old UI; MEP + Wolfe "appear missing"; he wants a strategist dashboard + a full strategy
> list; and he's lost the Wolfe manual-draw setup. **This doc is the single tracked record so none of
> it gets missed.** Registered in PROJECT_STATE § "What's NOT yet built" + memory
> `patearn-product-completion-session`.

## 0. The headline (honest status — verified against code + git, 2026-06-28)
- **Nothing was deleted or broken.** Every strategy page + your Wolfe lenses still exist and return 200.
- The real issues are three, and they ARE legitimate:
  1. **The new UI is only half-built.** Only the **Trust / Coverage** surface uses the new design
     system (`ui_kit`). Markets, Screener, Strategies, Tracker, stock, MEP, etc. still render the
     **old chrome** (`dashboard._shell`) with the new 4-altitude nav bar bolted on top. Hence: same
     site, two different looks + two different logos.
  2. **MEP was RENAMED, not removed.** In the new menu it's `Strategies → "Accumulation"`
     (`/dash/mep`). By name you can't find "MEP" → it *looks* gone. It isn't.
  3. **Wolfe's menu link points to the scanner, not your drawing lens.** `Strategies → "Wolfe"`
     goes to `/dash/wolfe/scan` (the winner-profile scanner). Your candle/drawing lens at
     **`/dash/wolfe`** still exists but is now **orphaned from the menu**. And your **manual
     "draw your own" pivot mode was reverted weeks ago** (recoverable — see Track B).

## 1. Why there are two UIs (the root cause, in code)
| | OLD chrome (what you see on Markets) | NEW chrome (what you see on Trust) |
|---|---|---|
| Function | `dashboard._shell` / `dashboard._nav` | `ui_kit.shell` / `ui_kit.topbar` |
| Logo | `pat·e·arn` (green "e") | `patearn` (cyan dot) |
| Search | "search ticker…" box | "Search or ask Pat ⌘K" |
| Pages on it | Markets, Screener, Strategies, Tracker, stock, MEP, conviction, CPR, RRG, RS, themes… (≈all) | Coverage/Trust (+ the design-system showcase) |
| File | `src/web/dashboard.py` | `src/web/ui_kit.py` |

`src/web/v2_surfaces.py` wraps the **4-altitude top bar** onto BOTH at runtime — so the *nav* looks
unified, but the *page body + logo + search* underneath is still whichever shell the page was built on.
Migration = move each old `_shell` page onto `ui_kit.shell` (same principles as the Coverage page).

---

## TRACK A — Old → New UI migration (the "convert everything to the modern UI" ask)
**Goal:** every page uses `ui_kit` (the Coverage look): cyan-dot logo, unified "Search or ask Pat",
card system, the 4-altitude IA. **Principle (from `docs/ui-architecture-v2.md`):** additive, no route
changes, sacred routes keep URLs, nothing rendered dead, verify each page 200 after.

| # | Page / route | Altitude | Status | Action |
|---|---|---|---|---|
| A1 | `/dash/coverage` (Trust) | Trust | ✅ on `ui_kit` | done — the reference look |
| A2 | `/dash/markets` | Markets | ✅ **DONE + LIVE** | reskinned via `shell_skin` runtime-wrap |
| A3 | `/dash/screener` | Screener | ✅ **DONE + LIVE** | reskinned (wide frozen-pane grid colours retinted, geometry untouched) |
| A4 | `/dash/strategies` (Hub) | Strategies | ✅ **DONE + LIVE** | reskinned; strategist-dashboard upgrade = Track C (Lane B) |
| A5 | `/dash/dashboard` (Tracker) | Tracker | ✅ **DONE + LIVE** | reskinned |
| A6 | `/dash/stock` (dossier) | — | ✅ **DONE + LIVE** | reskinned; chart engine separate, untouched |
| A7 | `/dash/mep`, `/dash/conviction`, `/dash/stocks`, `/dash/cpr`, `/dash/leaders`, `/dash/concalls`, `/dash/growth`, `/dash/wolfe`, `/dash/wolfe/scan`, `/dash/launchpad`, `/dash/testing` | Strategies | ✅ **DONE + LIVE** | all reskinned |
| A8 | `/dash/rs-hub`, `/dash/rrg`, `/dash/rotation`, `/dash/rsband`, `/dash/participants`, `/dash/wire`, `/dash/compare`, `/dash/sectors` | Markets | ✅ **DONE + LIVE** | all reskinned (incl. the modules that `import _shell` by reference — see below) |

> ✅ **TRACK A COMPLETE — the WHOLE site now wears the `ui_kit` look (2026-06-28).**
> **Mechanism (decoupled, zero edits to dashboard.py/cockpit.py):** new module
> **`src/web/shell_skin.py`** RUNTIME-WRAPS `dashboard._shell` — every legacy page (and all
> of cockpit) routes through it, so one wrap reskins the whole site: the cyan-dot `patearn`
> logo (CSS, the green-"e" gone), the "Search or ask Pat ⌘K" hint (the old search box swapped;
> ticker-jump preserved via the global Cmd-K overlay the v2 nav already injects), and a CSS
> OVERLAY scoped under `body.uk-skin` that retints the legacy `.card`/table/`.maj`/`.scard`/
> frozen-pane-grid/semantic-ink classes to the ui_kit tokens (colour only — sticky/z-index
> geometry untouched). **Key fix:** the lens modules (`rrg_view`/`rsband_view`/`rotation_view`/
> `participants_view`/`wolfe_view`) do `from dashboard import _shell` (binding the original by
> reference), so `install()` also sweeps `sys.modules` and rebinds every captured `_shell` to
> the wrapped one — generic, no hardcoded names, no source edits. **Properties:** defensive
> (a skin failure returns the original html, never 500s), idempotent (a `/* uk-skin v1 */`
> marker + an `hrow1` legacy-chrome guard so it no-ops on the v2-native pages), no-loss (CSS
> retint only; every body/datum/sacred URL intact). **Durable:** wired from
> `v2_surfaces.wire()` → re-applied by `scripts/wire_v2_surfaces.py` after any redeploy.
> **Live-verified** on every nav route (skin marker present, legacy `.hsearch` gone, 200) +
> computed-style proof on the live Strategies hub (`.card` bg `#111824`/12px, logo dot
> `#34e0d6`, body bg `#0b0f17`, sub-nav accent `#4d9dff`). **Revert =** restore
> `v2_surfaces.py.bak-chrome` (+ remove `shell_skin.py`) + restart `hermes-api`.
> **Also pre-wired (plan §2a):** Strategies→**"Strategist"**→`/dash/strategist` (first) +
> Screener→**"Screen+"**→`/dash/screen2` so Lane B's pages are reachable the moment they ship.

---

## TRACK B — Wolfe: where it is, what you lost, how to get it back
**Everything still exists in code** (`src/automation/wolfe.py`, `src/web/wolfe_view.py`,
`src/web/wolfe_overlay.py`):
- **`/dash/wolfe`** — your candle **drawing/chart lens** (two nested waves, Fib fans, candles). ⚠️ **Now
  orphaned from the menu** — the new "Wolfe" link goes to the scanner instead.
- **`/dash/wolfe/scan`** — the winner-profile **scanner** (BULL ✓ edge / BEAR ⚠ tail). This is what the
  menu links to.
- **The stock-chart Wolfe overlay** on `/dash/stock` (toggle).

**What you lost:** the **manual "✎ draw your own" pivot mode** — commit **`b7ad360`** — was **REVERTED**
during the Session-40 iteration (superseded by the auto-detect final state `707fcb1`). It is **fully
recoverable from git** (`git show b7ad360`).

**Tracking already exists** (you will NOT miss it): `docs/wolfe-NEXT-SESSION.md` (51 KB run-book, §0
resume + open questions), memory `wolfe-wave-strategy` + `wolfe-backtest-methodology`, git tag
`wolfe-advanced` (`6179cd3`), PROJECT_STATE Sessions 40/§C.

| # | Item | Status | Action |
|---|---|---|---|
| B1 | Wolfe drawing lens orphaned from menu | ✅ **DONE + LIVE (2026-06-28)** | added `Strategies → "Wolfe · Chart"` → `/dash/wolfe` (and renamed the scanner link "Wolfe · Scan"); `v2_surfaces.py`; deployed + verified (both hrefs render, page 200) |
| B2 | Manual draw-your-own mode reverted | ✅ **RESTORED + LIVE (2026-06-28, Lane C)** | re-implemented the `b7ad360` "✎ draw your own" mode INTO the current Prediction/Completed overlay (`wolfe_overlay.py`) — a third mode on the `/dash/stock` Wolfe overlay: click points 1→5, each snapped to the nearer real bar high/low, machine draws the structure + computes the Fib EXTENSION overlap zones on HIS pivots. JS `fibZones` mirrors the CURRENT `wolfe.fib_zones` byte-for-byte (extensions-only, tol 2%, PARAS 1226.2 pin) — NOT the old b7ad360 JS (retracements+0.4%, since superseded). `overlay_for` now returns compact `bars` for snapping. Deployed + verified (snippet embedded, JS syntax OK, overlay returns 800 bars, health 200). DESCRIPTIVE-only (geometry+zones, no buy/sell). |
| B3 | Wolfe = "a chart overlay, not a strategy tab" (per IA) vs. its own scanner page | ✅ **DECIDED + DOCUMENTED (2026-06-28, Lane C)** | canonical homes reconciled — **drawing/chart lens = the `/dash/stock` Wolfe-wave overlay** (interactive lightweight-charts: Prediction / Completed ◄► / ✎ Draw-your-own — the only surface that can hand-draw, since it needs the clickable chart); **`/dash/wolfe` = the standalone ranked auto-detect SVG list** ("browse every setup", click-to-draw, fib fans — read-only, no manual draw on SVG); **`/dash/wolfe/scan` = the winner-profile scanner** (descriptive strategy feed, BULL ✓ / BEAR ⚠ by side). Nav: "Wolfe · Chart" → `/dash/wolfe`, "Wolfe · Scan" → `/dash/wolfe/scan` (Lane A); draw-your-own is reached from any stock page's overlay toggle. |

---

## TRACK C — Strategy catalog + the strategist dashboard
**The complete strategy list (the `Strategies` altitude — from `v2_surfaces.py`):**
| Menu label | Route | What it is |
|---|---|---|
| Hub | `/dash/strategies` | the strategies landing (the "at a glance" page — needs the upgrade below) |
| Conviction | `/dash/conviction` | cross-pillar shortlist (all pillars align) |
| Positioning | `/dash/stocks` | F&O / positioning scanners |
| **Accumulation** | `/dash/mep` | **MEP** — signed accumulation/distribution (DDPK=DVPT / MEP) |
| Structure | `/dash/cpr` | CPR multi-TF structure pillar |
| Strength | `/dash/leaders` | RS leaders/laggards |
| Credibility | `/dash/concalls` | CCI management-credibility |
| Growth-intent | `/dash/growth` | growth lens |
| Wolfe | `/dash/wolfe/scan` | Wolfe winner-profile scanner (+ `/dash/wolfe` drawing lens) |
| Launchpad | `/dash/launchpad` | explosive-move "Launchpad" setup |
| Lab | `/dash/testing` | strategy ledger / backtests |

| # | Item | Status | Action |
|---|---|---|---|
| C1 | A **strategist dashboard** — every strategy's current read at a glance (counts, top names, freshness), each card → its deep section | ✅ **BUILT + LIVE (2026-06-28, Lane B)** | NEW `/dash/strategist` (NEW `src/web/strategist_view.py`) on `ui_kit`; consumes `strategy_registry.summary()` (Lane C) with an in-module same-shape fallback; AUGMENTS to the full catalog so no strategy is missing |
| C2 | Per-strategy deep sections | ✅ exist (table above) | keep; re-home to `ui_kit` (Track A7) |
| C3 | Naming clarity: label MEP as **"Accumulation (MEP)"**; surface the shorthand so it's findable | ⬜ | 1-line label fix in `v2_surfaces.py` |
| C4 | **Streamlined screener** — one wide configurable frozen-pane screener with saved screens + strategy column-groups + the confluence columns | ✅ **BUILT + LIVE (2026-06-28, Lane B)** | NEW `/dash/screen2` (NEW `src/web/screener_plus.py`) on `ui_kit`: a CONFLUENCE lead column (0–5: DVPT·MEP·RS·CPR·CCI aligned, ★ at ≥4) + one-click column-GROUP toggles + SAVED screens + sort/filter/CSV; precomputed reads only |

> ✅ **Lane B SHIPPED + LIVE-VERIFIED 2026-06-28** — `/dash/strategist` (10 cards: 6 measured-fresh
> from the registry — MEP/DVPT/RS/CPR/CCI/Wolfe — + 4 link cards Conviction/Positioning/Growth/Launchpad)
> and `/dash/screen2` (499 rows on Nifty 500, 7 group toggles, save/filter/CSV). Both on the `ui_kit`
> chrome carrying the full v2 site nav (merges with Lane A). NEW modules only; mounted via a reversible
> append-only block at the EOF of `main.py` (VPS backup = `main.py.bak-strat`). Lane A's nav slots
> (Strategies→"Strategist", Screener→"Screen+") wire these into the menu once Lane A lands them.
> **Revert = delete the Lane B mount block in `main.py` + restart.**

---

## TRACK D — Quick, low-risk fixes (the discoverability regressions)
These are the cheapest trust-restoring wins — all in `src/web/v2_surfaces.py`, reversible:
- **D1** ✅ **DONE + LIVE (2026-06-28)** — relabeled `Strategies → "Accumulation (MEP)"` so MEP is findable by name.
- **D2** ✅ **DONE + LIVE (2026-06-28)** — added `Strategies → "Wolfe · Chart"` → `/dash/wolfe`; scanner link renamed "Wolfe · Scan".
- **D3** ⬜ — MEP is now labeled + present; full prominence lands with the strategist dashboard (Track C1).

> ✅ **D1 + D2 applied to the live system 2026-06-28** (Ramana said "apply now"): safety-diffed (VPS ==
> repo baseline), backed up (`v2_surfaces.py.bak-mepwolfe`), selftest green on the VPS venv, restarted
> `hermes-api` (active), verified on `/dash/strategies` (200; "Accumulation (MEP)", "Wolfe · Scan" →
> `/dash/wolfe/scan`, "Wolfe · Chart" → `/dash/wolfe` all render). **Revert = restore the `.bak-mepwolfe`
> backup + restart.** Remaining tracks (A migration · B2 manual-draw · C dashboard) await go-ahead.
