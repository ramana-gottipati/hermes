# Review brief 07 — Lane L1 unblock: landed the live-on-prod RRG upgrade + leaders fix (`05cdeae`)

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Date:** 2026-06-29 · **Continuous-review follow-up to req-05's standing mandate.**

You are the independent reviewer sharing `D:\Hermes`. Review READ-ONLY; output review text only
(captured to `resp-07-L1-unblock-rrg-leaders.md`). Cite files/commits; if you can't verify, say so.

## Context — what L1 decided and why
req-05 asked you to weigh "land vs shelve" the ~364-line uncommitted `dashboard.py` WIP refactor.
On triage that "WIP" turned out to be **826 lines across 3 frozen files** (`dashboard.py` −96 net,
`cockpit.py` ±56, `rrg_view.py` **+406**) and — critically — **already deployed + serving on the live
VPS** (the project's deploy model is scp, not git-pull, so prod was *ahead* of git). The animated-RRG
markers (`rrgplay`/`rrgspeed`/`rrgsvg`/`timeframe`/"3m daily") are confirmed live on `/dash/rrg`.
Decision: **land it** (commit `05cdeae`) to sync git to the already-live state — shelving would have
diverged git from prod. `chrome_gate.py` PASSED pre-commit; all 3 files AST-parse clean.

## Read first, in order
1. `git show --stat 05cdeae` and `git diff cd98445..05cdeae` — the landed change.
2. `src/web/rrg_view.py` — the new timeframe-native RRG (`_sector_tail`, `_rrg_jdk`, `_resample_ratio`,
   `_period_key`, `_tail_selector`, `_sectors_rrg_block`, `_RRG_PLAY_JS`) — 3m daily · 6m/12m weekly ·
   24m monthly resampling with cadence-scaled JdK smoothing + the animated "Play" all-sectors RRG.
3. `src/web/dashboard.py` around the `/dash/leaders` handler (`active="leaders"`, ~line 1679) and the
   chart-snippet import fold + tracker sub-nav.
4. `scripts/chrome_gate.py`, `scripts/regression_sweep.sh`.

## What to assess
1. **Was landing `05cdeae` correct + safe?** Given prod was already serving it, is git-sync the right call,
   or is there a reason to have shelved/reworked instead? Any content in the diff that should NOT be in main?
2. **RRG correctness:** is the timeframe-native resampling sound (does a long-window dot reflect weekly/
   monthly performance, not a single-day jerk)? Any off-by-one / NORM_WIN guard / empty-data 500 risk in
   `_sector_tail` / `_rrg_jdk` / `_resample_ratio`? Does the animated `_RRG_PLAY_JS` degrade gracefully
   (no data, hover/leave, speed toggle) and avoid leaking RAF loops?
3. **Leaders highlight:** with `active="leaders"`, does the page now highlight the correct nav group given
   `lens_registry.py` says leaders = **Markets** altitude? Or does the dashboard `_nav` group at
   `dashboard.py:~435` (`{"leaders","laggards"} → "Strength"`) still place it under Strategies? (i.e. is the
   residual *fully* fixed, or only partially?)
4. **Regressions:** anything in the −276 deletions that removed needed behaviour? `cockpit.py` companion edits OK?
5. **Over-claim check:** the commit message says "verified". Is anything claimed that the diff doesn't support?

## Heads-up — 4 lanes now in flight on `main`
L2 (native bodies + chrome polish: `ui_kit`/`shell_skin`/`v2_surfaces`/new `*_native.py`), L3 (charting:
`chart_view`/`stock_chart`/`wolfe*`/`harmonic_*`/`hermes-charts.js`), L4 (Pat + research: `src/pat/*`/
`strategist_view`/`screener_plus`/`provenance`/`cci_*`) are running in parallel. As their commits land,
follow-up `req-NN` will point you at each range — same continuous-review contract.

## Output format
```
## Verdict — was 05cdeae safe to land?
## RRG correctness (resampling · guards · animation lifecycle) — issue | severity | citation
## Leaders highlight — fully fixed or partial? (registry vs _nav group) | citation
## Regressions in the deletions | citation
## Over-claim / anything missed
```
