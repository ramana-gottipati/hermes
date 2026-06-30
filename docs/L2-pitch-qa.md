# L2 Wave 3 — Pitch-demo visual QA + Trust front-door + WCAG-AA

> **Lane L2 Wave 3.** Created 2026-06-29. Walked the linear 6-beat pitch demo IN-BROWSER on the
> live VPS in a DEDICATED tab (the shared tab gets hijacked by L3/L4 navigation). Verification is
> computed-style + stylesheet-rule inspection (not markup), per the non-negotiables.
> Beats (docs/pitch-demo-and-positioning-DECISIONS.md): Trust/Coverage → Provenance → Replay-the-Tape
> → rotation → dossier → two-buyer close.

## 1. Per-beat visual QA

| Beat | Page | Finding | Action |
|---|---|---|---|
| 1 Trust & Coverage | `/dash/coverage` (native) | Reference-clean: 13 uniform cards (pad 16/18, radius 12, bg #111824), descriptive evidence eyebrows (settlement funnel "honest, monotone"; modeled-vs-filed), Strategy-validation + provenance-memo trails present, **no leaderboard language** (D-PITCH-1 ✓). | kept as reference |
| 2 Provenance | (basis legend / `/v1`) | descriptive per-class registry; no ranking | — |
| 3 Replay the Tape | `docs/replay-the-tape.html` | **GAP: no `/dash/replay` route + no Replay trail on Coverage** → not discoverable from the front door (D-PITCH-4 beat 3). The HTML is a static file with no server route. | **flagged to coverage_view owner** (task_568e63a8) — out of L2-owned files |
| 4 One name in confluence | `/dash/stock?sym=ACC` | native dossier; verdict cards (CMP/Conviction/RS/DVPT/Accum/Quality/**UNPROVEN** cred — descriptive, never a grade, D-PITCH-4 ✓); 8-tab nav (mobile-fixed in W2). Old-palette: none. | clean |
| 5 Screener | `/dash/screener` | wide frozen-pane grid native; primary text passes AA; residual sub-AA is micro-glyphs on tinted heat cells (value contract) | accepted dense-grid exception |
| 6 Two-buyer close | `/v1` | descriptive "one bus, four faces" | — |
| (consistency) | Markets | `.ck-tile` index-bundle tiles carried the OLD palette (#161b22/#30363d) | **FIXED** (`5c7be8f`) |

## 2. WCAG-AA accessibility audit (the bankable-credibility item)
Proper-compositing contrast audit (alpha over the effective bg) across the beats. **Every semantic
colour already clears AA** (up 9.3:1, down 6.4:1, accent 6.4:1, warn 9.9:1, cred 6.8:1). The **sole
systemic failure was `--ink-3`** (#5c6f84 = 3.44:1 on the card bg, FAILS AA 4.5 for normal text) — and
it carries eyebrows / captions / table-th / `.mut` site-wide (10 fails on Coverage alone).

- **FIXED (`e7ee6d5`):** lifted `--ink-3` #5c6f84 → **#7e90a8** (5.9:1 / 5.5:1 / 4.9:1 on bg-1/2/3) in
  all three definitions (ui_tokens `:root`, ui_kit `.uk`, shell_skin legacy hardcodes + cmdk footer).
  Still a clearly-muted tertiary (ink-2 #9bb0c6 = 8.6:1 stays the step above). + a shell_skin block
  mapping the FROZEN bodies' hardcoded too-dark greys (#6e7681, #5f7488 on `.snap`/`.subnav`/`.nglat
  .lbl`/…) to the AA-safe `--ink-3` by class. Result: **Coverage AA fails 10→1; Stock 3→2.**
- **Remaining (flagged, not L2-owned):** 2 inline `style="color:#6e7681"` chart-control labels in
  `stock_chart.py` (4.04:1) — inline styles can't be reached by a class rule → **task_c0cc1023** to L3.
- **Focus order / keyboard / aria:** skip-link + `#uk-main` + nav `aria-label="Primary"` +
  `aria-current` + focus-visible rings all present. **GAP FIXED (`4f4e7b6`):** the ⌘K summon was a
  `<div>` (not keyboard-focusable, not announced — WCAG 2.1.1 + 4.1.2). Now a `<button>` with
  `aria-label` + `aria-keyshortcuts` + a focus-visible ring; verified keyboardFocusable + opensOnActivate.

## 3. Design-system completeness + print (Item 4)
- `/dash/_ui` showcase is **current** — demonstrates every component family incl. empty/error/note/
  skeleton/spinner/badge/seg/tag/progress/tooltip.
- **Print deepened (`232cb05`):** @page A4 box + margins; full light-flip with print-color-adjust:exact;
  hide every interactive-only control (toggles/filters/search/tabbar/chart-fullscreen); cards+tables
  intact across page breaks (break-inside:avoid, thead repeats); green/red value contract preserved in
  print-safe inks; a footer disclaimer line. Verified by print-media emulation: body→#fff, text→#0b0f17,
  topbar→none, shadows→none. A clean printed Coverage/dossier = a leave-behind (D-PITCH-2).

## 4. Out-of-scope (flagged, not owned by L2)
- **D-PITCH-2 Rotation colour clash** (blue=bull/amber=bear): the quadrant colours live in
  `rotation_view.py` (not an L2-owned file, not a `*_native.py`). Not edited; belongs to that view's owner.
- **Replay-the-Tape route + trail** (`coverage_view.py` + routing) → task_568e63a8.
- **Chart-control inline-style contrast** (`stock_chart.py`, L3) → task_c0cc1023.

## 5. Commits + gates
`e7ee6d5` AA contrast · `4f4e7b6` ⌘K a11y · `5c7be8f` ck-tile consistency · `232cb05` print.
`chrome_gate.py` + `regression_sweep.sh` PASS before every commit; all deployed atomically (concurrent
L3/L4), health 200, browser-verified. Owned files only: `ui_tokens.py`, `ui_kit.py`, `shell_skin.py`.
