# Codex review — Graphite Home build spec v1.0 (2026-07-23)

Reviewer: Codex (gpt-5.5, `codex exec`, review-only). Subject: `docs/redesign-graphite-home-spec.md`
(the fresh-and-parallel engineering spec). Raw output (1.8MB) in session tool-results; distilled here.

## `VERDICT: OBJECT` — 7 BLOCKING + 3 ADVISORY (all accepted → spec v1.1)

| # | Sev | Finding | Disposition (v1.1) |
|---|---|---|---|
| 1 | BLOCKING | "One mount line" isolation claim false; and registering a **lens** changes the classic nav (nav is generated from `lens_registry`, `v2_surfaces.py:211-230`) → zero-drift violation. Real touched files: `v2_surfaces.py`, `test_dash_route_registry.py`, maybe `lens_registry.py`, `test_pat_coverage.py`, `metrics-glossary.md`, `PROJECT_STATE.md`. | **ACCEPTED.** §1 rewritten: build-phase = **direct-URL INTERNAL_DEV, NO lens/nav/Pat-gate** (deferred to cutover §10/§12). Honest 3-file additive touch list (v2_surfaces mount + route-gate rows + PROJECT_STATE). |
| 2 | BLOCKING | Route gate enumerates only `/dash/*` (`test_dash_route_registry.py:216-223`); top-level `/home` is invisible to it. | **ACCEPTED.** Route → **`/dash/home`** (§2), covered by the existing gate; INTERNAL_DEV rows added. |
| 3 | BLOCKING | Spec self-contradicts on `lens_registry` (playbook says register; that changes nav). | **ACCEPTED.** §10 splits compliance by phase: build = route-gate/fence/AA/tests only; cutover = lens/Pat/education/nav. |
| 4 | BLOCKING | Reusing `today_v3._mood_html`/`_what_changed` violates the no-import-preview rule — they live in the frozen preview module AND return `pv3-*` HTML, not data (`today_v3.py:15,22-46,125-145`). | **ACCEPTED.** §5 bans preview imports; `mood`/`what-changed` reimplemented as bounded reads in `home/reads.py` (or the pure `whatchanged_flow.changes()` from `src/pat/`, which is NOT preview). |
| 5 | BLOCKING | Several §5 reads wrong: `whatchanged_flow.changes()` is the read (not generic); `news_dock` is a `pv3-*` renderer not a read; **no `power_dvpt` column** — real cols `power_dvpt_1m…_12m` (`db.py:310-313`). (`corp_actions.upcoming`, `results_calendar.upcoming_results`, `news_view._recent_market_news` confirmed real.) | **ACCEPTED.** §5 rewritten with exact signatures; news reimplemented (not `news_dock`); delivery uses `power_dvpt_3m`. |
| 6 | BLOCKING | Prior prototype blockers only partly pinned — only candle-AA has a named gate; no a11y/DOM/RM/persona test. | **ACCEPTED.** §7 names `test_home_isolation/_tokens_aa/_pat_a11y/_dom_safety/_reduced_motion/_persona`. |
| 7 | BLOCKING | market_internals timer is not "one line" — new units + captured VPS metadata + state; "fold into bhavcopy chain" edits existing infra. | **ACCEPTED.** §9: timer **deferred** out of the home build; v1 breadth = as-of stamp; timer = separate infra increment. |
| 8 | ADVISORY | Add stricter collision gate (no `data-ui-v3`/`pv3` in Graphite HTML; no `data-ui-g`/`pvg` in preview HTML). | **ACCEPTED** — folded into `test_home_isolation.py` (both directions). |
| 9 | ADVISORY | News zone must use `_safe_url` without importing `news_dock`; add `javascript:`/`data:` regression. | **ACCEPTED** — §5/§7: copied pure `_safe_url` + `test_home_dom_safety` regression. |
| 10 | ADVISORY | FII/DII read sound if it stays in `home/reads.py`; specify SQL. | **ACCEPTED** — §5 gives the exact `fii_dii_recent` SQL (table-guarded, category-normalised). |

**Next:** Codex convergence re-check of v1.1 before the spec is review-clean for the owner's build-go.
