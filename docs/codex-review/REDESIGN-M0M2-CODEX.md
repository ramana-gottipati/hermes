# Codex review — redesign plan, M0-M2 focus (2026-07-17)

> Channel record per docs/redesign-coordination.md §1.3 — verdict verbatim from
> `codex exec` (review-only run). Dispositions: docs/redesign-coordination.md §3.

VERDICT: APPROVE-WITH-CHANGES

1. BLOCKING: M0/M1 routes must be machine-registered in the route gate, not just described in the plan. The plan adds `/dash/preview` and `/dash/_ui3` (`docs/redesign-plan-2026-07-17.md:376-378`), while the gate currently only knows `/dash/_ui` and `/dash/offline` as `INTERNAL_DEV` (`tests/test_dash_route_registry.py:92-96`). The gate explicitly says a non-nav route must be added to exactly one machine-readable table with owner+rationale (`tests/test_dash_route_registry.py:195-197`). Add `/dash/preview` and `/dash/_ui3` classifications in the same build commit.

2. BLOCKING: Define “`/dash/preview` entry” so it does not violate default byte-identity. M0 says “`/dash/preview` entry + opt-in cookie/param” while also requiring “default site byte-identical” (`docs/redesign-plan-2026-07-17.md:376`, `:389-390`). A visible link/toggle in existing chrome would break that proof. For M0, the entry must be a direct route and/or non-default dev/palette affordance that does not change default rendered bytes unless `?v3=1` or the preview cookie is active.

3. BLOCKING: M2’s parser contract is factually wrong as written. The plan says `glossary._INDEX` exposes `name/family/body/sources` (`docs/redesign-plan-2026-07-17.md:206-207`). In reality `_INDEX` maps normalized lookup keys to integer offsets, and rich entries live in `_ENTRIES`; the public helpers are `lookup()`, `has()`, and `terms()` (`src/web/glossary.py:29-31`, `src/web/glossary.py:88-102`, `src/web/glossary.py:118-125`). Build M2 on `lookup()` or a small tested adapter, not direct `_INDEX` assumptions.

4. BLOCKING: “Existing Pat gate already gates chip↔Pat drift” is overstated. The plan claims the existing Pat test + AUD-40 gates this (`docs/redesign-plan-2026-07-17.md:242-244`), but `tests/test_pat_coverage.py` gates routed lenses, Screen+ columns, lender metrics, and specific glossary anchors (`tests/test_pat_coverage.py:247-255`, `:338-375`). It does not prove that the 5 seed term chips resolve to Pat explanations. M2 needs its own small test for the seed chips: chip term -> glossary/web lookup -> Pat explain slug/query returns the same concept.

5. BLOCKING: Several planned seed terms do not currently resolve through the web glossary under the exact labels in the table. I verified the md parser has 248 entries, matching the plan (`docs/redesign-plan-2026-07-17.md:206`), but exact lookups fail for `×Power`, `MEP`, `CCI`, `pt14`, `Wolfe §B score`, and `Launchpad`; `DVPT`, `Key price`, `RS band %`, `Conviction`, `CPR`, and `return/vol` resolve. Before M2 ships, either use existing slugs/aliases or add glossary aliases in `docs/metrics-glossary.md`.

6. ADVISORY: The factual inventory claims checked out: `src/web/lens_registry.py` currently has 73 lens records, 71 routed and 2 overlay-only (`wolfe`, `harmonic`), matching `docs/redesign-plan-2026-07-17.md:13-16`. Pat coverage also matches the plan: 24 DATA / 10 EXPLAIN / 37 NAV (`docs/redesign-plan-2026-07-17.md:15-16`).

7. ADVISORY: The plan’s additive-only posture is directionally correct but must be enforced per build, not trusted as prose. The playbook requires new surfaces to mount through `v2_surfaces._ROUTER_SPECS`, declare route-gate metadata, include education/fence/glossary/Pat/state-doc updates, and avoid orphan pages (`docs/SURFACE-PLAYBOOK.md:50-66`, `docs/SURFACE-PLAYBOOK.md:83-90`). M0-M2 should be accepted only with those same-commit gate edits and PROJECT_STATE updates.

8. ADVISORY: The descriptive-only fence is mostly respected in M0-M2, but the term-chip copy should keep “how it could improve” anchored to “improves the read,” never “improves returns.” The plan already says that intent (`docs/redesign-plan-2026-07-17.md:199-203`); keep that wording discipline when the md lines are added.
