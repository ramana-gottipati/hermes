# Kick-start — next session (paste this to continue)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the colour-migration thread is folded into PROJECT_STATE. Registered in `docs/DOC_INDEX.md`.


> Written 2026-07-01 at the end of the UI/colour session. Boot from this, then delete/replace it
> once the next session's work is folded into `PROJECT_STATE.md`.

## Boot procedure
1. Read `PROJECT_STATE.md` fully — start with **Session 61** (session wrap) + the two **Session 60 (cont.)** colour entries.
2. Read `docs/color-system-alignment.md` (D-COL-1..7 — the colour decisions, incl. the RRG ruling).
3. `git log --oneline -20` and confirm you are on **`main`** (all work is now on main; no more `bugfix/...` branch).
4. Run the gates from main to confirm a clean baseline: `python scripts/chrome_gate.py && python scripts/nav_integrity_gate.py && python scripts/color_gate.py`.

## Git / workflow (NEW — Ramana's standing instruction)
- **Work directly on `main`.** Create a topic branch ONLY when a change genuinely needs isolation; otherwise commit to `main`.
- The `bugfix/audit-p1-2026-06-30` branch is **merged + retired**. Single unified branch = `main`.
- Always run reports/gates from `main`.

## THE task for next session: continue the colour migration

**Phase 1 (directional bull/bear) is COMPLETE and DEPLOYED.** Do not redo it. The color gate regression-locks 13 files.

### Phase 2 — backgrounds / hairlines / ink-greys (RESUME — in progress)
- Backlog **~483** sites remain (was 602). `color_gate.py` prints the live count; `dashboard.py` alone = **232**.
- **Mapping:** `#0d1117`/`#0e1116`→`var(--bg-1)` · `#161b22`→`var(--bg-2)` · `#21262d`→`var(--bg-3)` · `#30363d`→`var(--line-2)` · `#484f58`→`var(--line-3)`/`--ink-4` · `#8b949e`→`var(--ink-2)` · `#6e7681`→`var(--ink-3)` · `#e6edf3`/`#c9d1d9`/`#e8ecf1`→`var(--ink)`.
- **Mechanism (same as Phase 1):** CSS/inline `style=`→`var()`; **SVG `fill=`/`stroke=` ATTRIBUTE → rewrite to `style="fill:var(--…)"`** (var() silent-fails in an attribute — the `color_gate` render guard now catches this); **canvas/lightweight-charts JS → LEAVE** (chart-internal neutrals, can't read vars); rgba neutral overlays → leave.
- **State:** batch-1 (`bfe6778`) migrated 11 files (rrg_view + rsband_view complete; growth/harmonic/mini_rrg/news/participants/rotation/rs_section/testing/wolfe_overlay PARTIAL). **Finish the 9 partials + the untouched files:** dashboard.py, stock_chart.py, cockpit.py, shell_skin.py, wolfe_view.py, cpr_overlay.py, mep_overlay.py, coverage_view.py, screener_plus.py, strategist_view.py, glossary.py, replay_view.py.
- **How:** a **no-git fan-out** (forbid ALL git in agents — a prior one destroyed 8 files via `git stash`; keep batches ≤ ~8 to avoid the rate-limit that killed 21/23 agents), OR do dashboard.py by hand. Then verify (`git status` vs claims, no SVG-attr leaks, all 4 gates, render), commit, deploy colour-only.
- **Priority: LOW-MEDIUM.** `shell_skin` already retints most bg classes at runtime, so Phase 2 is ~95% invisible; it's source-consistency, not a visible fix.

### Phase 3 — categorical + status + the chart C object (NOT started)
- Add the categorical tokens the inventory named: `--series-1..N` (compare-chart palette / `_COMPARE_PALETTE` / `CMP_COLORS` / 21-colour `_RRG_PALETTE` sector identity), `--accent-orange` (`#f0883e` DISTRIB/Launchpad), finalize `--ok/--off/--neu` usage.
- Migrate the deliberately-left categorical greens/reds (F&O state dicts `_fq/_qc`, provenance `kt-*`, credibility series line, benchmark "row to beat", gw-cr money-accent, `stock_chart` C-object indicator series dval/atr).
- Then `dashboard.py`/`stock_chart.py` can join the gate's `MIGRATED` list.

### Phase 4 — de-duplicate the foundation (the red-team's root-cause fix)
- `ui_kit.py` `.uk` scope + `shell_skin.py` re-hardcode the palette as raw hex (3rd/2nd copies). Convert to `var()` references so a token change moves all render paths. Retire now-redundant shell_skin per-class remaps (audit each — a retired `.sc-RS` must restore `--cat-rs`, not `--up`).

## Standing carry-forwards (older, still open — see memory index)
- CCI credibility time-series PAUSED at Gemini spend cap; GATE-B lit → descriptive-only (merge into pt14).
- Enrichment layer (`enrich.py`) PAUSED at Gemini cap.
- Deferred audit findings on now-committed untracked files (`enrich.py` CL-PROV-11, `pipeline_status.py` CL-SCR-10, `code_review.py` CX-04/05 — GLM reviewer stays dormant).

## Deploy reality (unchanged)
- VPS = `ssh hermes` → `/opt/hermes`; py3.10 venv; scp+restart (NOT git-pull), LF endings, no backslash-in-f-string. Backup before overwrite. Verify: import-test → `systemctl restart hermes-api` → health + render + `curl | grep '(fill|stroke)="var(--'` = 0.
