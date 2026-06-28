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
| A2 | `/dash/markets` | Markets | ⬜ old `_shell` | re-home body into `ui_kit.shell`; keep all cards/data |
| A3 | `/dash/screener` | Screener | ⬜ old `_shell` | ditto (wide frozen-pane table preserved) |
| A4 | `/dash/strategies` (Hub) | Strategies | ⬜ old `_shell` | ditto + see Track C (strategist dashboard) |
| A5 | `/dash/dashboard` (Tracker) | Tracker | ⬜ old `_shell` | ditto |
| A6 | `/dash/stock` (dossier) | — | ⬜ old `_shell` | ditto; chart engine already separate |
| A7 | `/dash/mep`, `/dash/conviction`, `/dash/stocks`, `/dash/cpr`, `/dash/leaders`, `/dash/concalls`, `/dash/growth`, `/dash/wolfe`, `/dash/launchpad`, `/dash/testing` | Strategies | ⬜ old `_shell` | per-strategy pages → `ui_kit.shell` |
| A8 | `/dash/rs-hub`, `/dash/rrg`, `/dash/rotation`, `/dash/rsband`, `/dash/participants`, `/dash/wire`, `/dash/compare`, `/dash/sectors` | Markets | ⬜ mixed | re-home to `ui_kit.shell` |
**Sequencing:** A2 (Markets) first = highest-visibility win; then A4+Track C; then A7 strategy pages;
then A8. **Each page is an isolated change** (swap the shell wrapper, keep the body builder).
**Gate:** `dashboard.py` is parallel-owned/dirty — do per-page via a thin wrapper or coordinate; verify 200 + screenshot after each.

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
| B2 | Manual draw-your-own mode reverted | ⬜ decision | restore from `b7ad360` if you want it back — confirm first |
| B3 | Wolfe = "a chart overlay, not a strategy tab" (per IA) vs. its own scanner page | ⬜ decision | decide the canonical home; reconcile the two |

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
| C1 | A **strategist dashboard** — every strategy's current read at a glance (counts, top names, freshness), each card → its deep section | ⬜ | upgrade `/dash/strategies` (Hub) into this; on `ui_kit` (Track A4) |
| C2 | Per-strategy deep sections | ✅ exist (table above) | keep; re-home to `ui_kit` (Track A7) |
| C3 | Naming clarity: label MEP as **"Accumulation (MEP)"**; surface the shorthand so it's findable | ⬜ | 1-line label fix in `v2_surfaces.py` |

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
