# Pat Knowledge Contract — how every new surface teaches itself to Pat

> **Lifecycle: LIVING.** CANONICAL contract (do not archive). Registered in `docs/DOC_INDEX.md`.
> The binding rule for keeping Pat aware of the whole estate. Twin of `SURFACE-PLAYBOOK.md`
> items 5+6 and CLAUDE.md / AGENTS.md guardrail #9. Machine-enforced by `tests/test_pat_coverage.py`.

## The point (Ramana's intent, verbatim)

Pat must be a **data hero** that can answer any component or piece of jargon in plain language
and offer shortcuts — AND, decisively, there must be a **self-maintaining arrangement** so that
**every future component we build teaches itself to Pat automatically.** Shipping a new metric,
lens, or strategy must AUTOMATICALLY make Pat aware of it. Ramana must never have to enrich Pat
separately again. Everything is trained in through Pat's own knowledge sources.

This document is that arrangement. It is not advice — it is the contract the build enforces.

## The three knowledge sources (and why each is self-feeding)

Pat has **exactly three** sources of knowledge. Adding a surface teaches Pat through one of them.
Two feed themselves with ZERO code; the third is a small, mechanical per-lens addition.

| # | Source | File | How a new thing lands | Auto? |
|---|--------|------|-----------------------|-------|
| **A. JARGON** | the glossary | `docs/metrics-glossary.md` | add a `- **Term.** definition …` bullet. `src/pat/glossary.py:_merge_web()` folds every md entry into Pat's `GLOSSARY` at import, so `engine.route()` explains it and `find()` autocompletes it. | ✅ **ZERO code** |
| **B. PAGES / SHORTCUTS** | the lens registry | `src/web/lens_registry.py` | register a `Lens(...)`. `src/pat/nav_flow.py` ranks the registry, so "where do I see X" resolves + the ⌘K palette lists it. | ✅ **ZERO code** |
| **C. INLINE DATA** | the per-flow files | `src/pat/<name>_flow.py` | write a recognizer + a bounded read + a `web.py` render + `engine._VALID`/`_FLOW_LABEL` + a `₹0` pre-pass in `engine.route`. | ✍️ per-lens (mechanical) |

### A — the glossary auto-fold (proven)
Adding a term to `docs/metrics-glossary.md` and nothing else makes Pat explain it. Verified S150
end-to-end: a throwaway `Floogle Ratio` bullet in the md alone produced
`engine.route("floogle ratio") → {"flow":"explain","explain":"floogle_ratio"}` in a fresh process,
with no code change. The md is the SINGLE definition source (`src/web/glossary.py` parses it for the
`?` popovers AND `/dash/glossary`); `_merge_web()` shares it with Pat. Curated Pat entries always win;
the adapter never overwrites a slug.

### B — the registry auto-fold (proven)
A new `Lens(...)` becomes navigate-answerable immediately. Verified S150: injecting a synthetic
`quantum-flux` lens made `nav_flow.resolve("quantum flux")` and
`parse_navigate("where do I see quantum flux")` resolve it, with no flow code. `nav_flow` reads
`lens_registry.LENSES` live, so the day a page is registered Pat can name + link it.

### C — the inline data flows (the one non-automatic source)
A per-lens data flow (e.g. `news_flow`, `participants_flow`, `internals_flow`, `filings_flow`,
`wolfe_flow`, `seasonal_flow`) is genuine hand-work: a new `src/pat/<name>_flow.py` (recognizer +
a bounded, read-only reuse of the lens's EXISTING view/automation read), a `₹0` self-limiting
pre-pass in `engine.route` (must not steal a screen/nav ask), a `web.py:_<name>_flow` render, and
`engine._VALID` + `web._FLOW_LABEL` wiring. This is opt-in richness — not every lens needs it, which
is why the contract lets a lens be covered at a weaker level and demands a recorded decision.

## The gate — `tests/test_pat_coverage.py` (the enforcement)

The gate derives its lens set from `lens_registry` (so it can **never drift**) and asserts every
routed lens has coverage at one of three levels — mirroring `test_dash_route_registry.py` (no orphan
routes) and `test_education_coverage.py` (no un-scaffolded lens):

- **DATA** — `PAT_DATA[lens_key] = flow`, a bound inline flow (source C). The flow is verified to be
  real + wired (`engine._VALID` / `web._FLOW_LABEL`).
- **EXPLAIN** — `PAT_EXPLAIN[lens_key] = glossary_slug`, the lens's anchor metric defined in the
  glossary (source A). The slug is verified to resolve in the md-fed `GLOSSARY`, so it auto-folds.
- **NAV** — `NAV_ONLY[lens_key] = (owner, rationale)`, link-only coverage (source B). A reviewed
  decision; navigate is verified to actually resolve the lens.

**A routed lens in none of the three FAILS the build.** You cannot add a nav page and forget to make
Pat aware of it. `test_screener_columns_are_glossary_backed` adds the glossary half of playbook item 5:
every Screen+ metric column (`screener_plus.SCREEN2_COL_TERMS`) carries a glossary key or an explicit
`''` opt-out — a new metric can't ship undocumented. The gate runs in `regression_sweep.sh` Gate 0
(the whole `tests/` dir) beside the route + education gates.

## The rule (binding, same commit)

> **Every new surface / metric / strategy registers into Pat in the SAME commit — machine-enforced.**
> Concretely: a new metric → a `docs/metrics-glossary.md` entry (teaches jargon; auto-folds). A new
> lens → a `lens_registry` entry (teaches the page; auto-folds) AND a `tests/test_pat_coverage.py`
> classification (DATA if it's a table/screen worth an inline flow; EXPLAIN if its metric is in the
> glossary; NAV with an owner+rationale if link-only is genuinely enough). A new strategy → its
> `docs/strategies/` page (which the methodology flow reads) + the above. Prose in a doc does not
> count — registration is one of the three machine-readable tables.

### The upgrade path (the arrangement in motion)
A lens starts wherever its coverage honestly is and is UPGRADED in place. When an inline flow lands,
move its lens from `NAV_ONLY` to `PAT_DATA` in the same commit. S150 did exactly this: `insider` /
`ratings` / `sast` / `shp` (→ `filings`), `wolfe-scan` (→ `wolfe`) and `strategy-ref` (→ `methodology`)
began as `NAV_ONLY` and each moved to `PAT_DATA` the moment its flow shipped. That commit-by-commit
migration IS the self-maintaining arrangement working.

## See also
- `docs/SURFACE-PLAYBOOK.md` — items 5 (Glossary keys) + 6 (Pat registration); the full landing checklist.
- `CLAUDE.md` / `AGENTS.md` guardrail #9 — the binding surface rule that names this contract.
- `tests/test_pat_coverage.py` — the gate; `docs/metrics-glossary.md` — source A; `src/web/lens_registry.py` — source B; `src/pat/*_flow.py` — source C.
