# Chrome consistency sweep — native vs legacy two-shell seam (2026-06-30)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the two-shell chrome seams are fixed + folded into PROJECT_STATE. Registered in `docs/DOC_INDEX.md`.


> Owner ask: *"inconsistent behaviours across all screens."* Patearn renders chrome two ways —
> **native** `ui_kit.shell` pages (coverage, screen2, strategist, `_ui`) and **legacy** `dashboard._shell`
> pages reskinned at runtime by `shell_skin` (markets, stock, every strategy lens). This sweep walked a
> native page (`/dash/coverage`) and legacy pages (`/dash/markets`, `/dash/stock`) **side by side in-browser
> on the live VPS** and diffed every chrome behaviour. For each behavioural difference, the fix lands in
> `ui_kit.py` / `shell_skin.py` so the two shells are behaviourally identical. Files owned by this lane:
> `ui_kit.py`, `shell_skin.py`, `v2_surfaces.py`.

## Method
- Tunnel to the live VPS (`ssh -L 8000:localhost:8000 -N hermes`), Claude-in-Chrome dedicated tab.
- Per page, captured **computed styles + static attributes** of: logo, top-nav highlight, sub-nav wrapper
  + grouping, ⌘K summon, sticky header, body class, legacy-leak markers (`hrow1`/`v2bar`/`hsearch`), and a
  **380px mobile** overflow probe (`scrollWidth − clientWidth`).
- Both renderers converge on ONE header path: `shell_skin._native_header()` reuses `ui_kit.topbar` +
  `ui_kit.nav_links(v2_surfaces.site_nav)` + `v2_surfaces.native_subnav`, exactly as the native `shell()`
  does. So most chrome was already identical; this sweep hunts the residual seams.

## Behaviours audited and their verdict

| Behaviour | Native (`/dash/coverage`) | Legacy (`/dash/markets`,`/dash/stock`) | Verdict |
|---|---|---|---|
| **Logo → home** | `<a class="uk-logo" href="/dash">` | identical | ✅ identical (fixed earlier by `cd8c60d`; re-confirmed in-browser) |
| **Top-nav + active highlight** | `class="on" … aria-current="page"` on the active altitude | identical (Markets lit; stock lights nothing — dossier claims no altitude, by design) | ✅ identical |
| **Sub-nav wrapper landmark** | `<div class="uk-sub">` — **no `role`/`aria-label`** | `<div class="uk-sub" role="navigation" aria-label="Section">` | ❌→✅ **DIFF FOUND + FIXED** (see §1) |
| **Sub-nav grouping** | `<span class="grp">` per group run | identical | ✅ identical |
| **⌘K summon** | `<button class="uk-cmdk" aria-keyshortcuts="Meta+K Control+K">` + shared `cmdk_overlay()` (`#cmdk-ov`, `window.__cmdk` guard) | identical | ✅ identical |
| **Sticky header / scroll** | `.uk-top` `position:sticky; top:0; z-index:30` | identical (same `ui_kit.css()` injected on both shells) | ✅ identical |
| **Back-chip** | none (the native `uk-top` has no back chip) | none — the legacy `.hback` lived in the now-replaced two-row header (Lane M1); `hback` count = 0 live on every page | ✅ consistently absent (no seam) |
| **Body class** | native body `style=…` (no `uk-skin`) | `<body class="uk-skin">` — exactly **one** `class` attr (CL-CHR-4 verified) | ✅ correct by design |
| **Legacy chrome leak** | n/a | `hrow1` / `v2bar` / `hsearch` all **absent** live | ✅ no leak |
| **Mobile ≤380px** | page overflow **0px**; `.uk-sub` scrolls internally | page overflow **0px**; `.uk-nav`/`.uk-sub` scroll internally; ⌘K stays visible | ✅ identical, no h-overflow |

**Net: one genuine behavioural seam found (sub-nav landmark) — fixed.** Everything else was already identical
across the two shells (the Lane M1 header-unification + the `cd8c60d` logo fix had already converged them).

## §1 — The one seam: sub-nav navigation landmark (fixed)

Two renderers produce the contextual sub-nav strip:
- `ui_kit.subnav()` — used by **coverage** and **`_ui`** (native, via `K.subnav(...)`).
- `v2_surfaces.native_subnav()` — used by **screen2**, **strategist**, and **every reskinned legacy page**.

They emitted **different wrappers**: `native_subnav` had `role="navigation" aria-label="Section"`; `ui_kit.subnav`
emitted a bare `<div class="uk-sub">`. So the sub-nav was a screen-reader navigation landmark on most of the
site **but not on the Trust front-door (`/dash/coverage`)** — exactly the kind of cross-screen inconsistency the
owner flagged. Inner markup (group `<span class="grp">`, anchor `class="on"`) was already identical; only the
wrapper attrs differed.

**Fix** (`ui_kit.py`, `subnav()`): emit the identical wrapper
`<div class="uk-sub" role="navigation" aria-label="Section">`. Now ALL pages — both native renderers AND every
legacy page — produce a **byte-identical** sub-nav wrapper. One sub-nav contract, both shells.

**In-browser proof (live VPS):**
- BEFORE — coverage: `sub_role=NONE sub_aria=NONE`; markets: `sub_role=navigation sub_aria=Section`.
- AFTER  — coverage: `sub_role=navigation sub_aria=Section`; markets: unchanged. Identical.
- In-process across 7 pages (coverage, `_ui`, markets, screen2, strategist, mep, sectors): all
  `<div class="uk-sub" role="navigation" aria-label="Section">`.

## Chrome-crash bugs fixed in the same lane (audit CL-CHR-*)

| ID | File | Status |
|---|---|---|
| **CL-CHR-1** | `shell_skin.py` `_HSEARCH_RE` undefined → NameError drops the whole skin on the header-swap fallback | Already committed (`0ec20f5`) but **never deployed** — the live VPS was running the un-fixed code (latent: only fires when `_native_header()` raises). **Deployed + verified** this session. |
| **CL-CHR-3** | `v2_surfaces.py:84` `subnav(_alt)[0]` IndexError at import (all-overlay altitude) → app crash | Already committed (`0ec20f5`, `_alt_landing()` guard) but **never deployed**. **Deployed + verified** this session. |
| **CL-CHR-4** | `shell_skin.py` `uk-skin` body-class regex could produce a **duplicate `class` attribute** on a `<body class="x">` shell (existing class then dropped by the browser) | **Fixed** this session: new `_add_body_class()` — a single substitution that preserves every body attr and MERGES into an existing class (idempotent, defensive). Unit-tested across bare / class / attrs / single-quote / idempotent / merge cases; live `<body>` has exactly one `class` attr. |

> Deploy note: `0ec20f5` ("P1 security/crash wave") was committed to the branch but its own message said
> *"Not yet deployed to VPS."* The live VPS therefore still ran the pre-fix `shell_skin.py`/`v2_surfaces.py`
> (md5 mismatch vs the branch). This sweep deployed the branch-current versions of all three owned files —
> so CL-CHR-1/CL-CHR-3 went from "fixed in git, latent in prod" to "fixed in prod".

## Verification
- `_add_body_class` unit tests: all pass (no duplicate `class=`, attrs preserved, idempotent).
- `shell_skin._selftest()` + `v2_surfaces._selftest()`: OK.
- `python scripts/chrome_gate.py`: PASS (11 legacy + 4 native, all markers) — local **and** on the VPS in-process.
- `bash scripts/regression_sweep.sh`: PASS (chrome gate + 32 routes + 5 chart overlays all 200 live).
- Deploy: backup (`*.bak-chr-<ts>`) → `tr -d '\r'` LF → scp → py3.10 compile + in-process chrome_gate →
  `systemctl restart hermes-api` → health 200 → in-browser BEFORE/AFTER computed-style diff.

## Theme / scope
Institutional value-green theme preserved (colour-only retint untouched); descriptive-only. No layout / sticky /
z-index / frozen-pane geometry changed.
