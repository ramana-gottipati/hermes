# Review brief 02 — navigation & page-structure review

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Date:** 2026-06-29

You are the independent reviewer in a two-agent system sharing the workspace `D:\Hermes`. Review the
material below against the ACTUAL code + DB schema. **Do not modify, move, or delete anything** — output
your review as text only (it is captured to `resp-02-nav-structure-review.md`). Cite files/lines; if you
cannot verify a claim from the workspace, say so rather than guessing.

## Context
Ramana is unconvinced about the site's menu/body structure. We produced an analysis (the doc under
review) arguing: the **data + the stock dossier** form a coherent "lens" architecture, but the **top menu**
flattens a 2-D (Scope × Lens) reality into a 1-D list, causing specific misfilings. We need you to
independently verify or refute this — especially the data-grounded claims — before Ramana decides anything.

## Read these first, in order
1. `AGENTS.md` — your orientation (twin of `CLAUDE.md`).
2. `docs/navigation-and-structure-review.md` — **the document under review.**
3. `src/web/v2_surfaces.py` — the nav IA (`_IA_ALT`, `_IA_SUB`, `_SUB_ALIAS`, `_ALT_OF`, `_altitude_of`, `wire`).
4. `src/web/dashboard.py` — the stock dossier (search `data-tab`, `?tab=`, `location.hash`, `_nav`, `_shell`)
   and most list/board handlers; `src/web/cockpit.py` — full-bleed renders + the row `href` patterns + the `crumb` links.
5. `src/web/{cpr,mep,rs,wolfe}_overlay.py` (+ `wolfe_view.py`) — the chart-overlay JSON endpoints + the `window.__wfpc`/`__wfcandle` contract.
6. `src/core/db.py` (SCHEMA) + the lens compute modules (`mep_signals.py`, `cpr_signals.py`, `concall_scores.py`/`cci_*`, `stock_rs.py`/`rrg.py`, `harmonic_signals.py`) — to verify the lens→table feed map.
7. `docs/ui-architecture-v2.md` (esp. §0 corrections, §3, §9) — the prior IA design the doc references.

## What to assess and report

### 1. Is the lens × surface matrix (doc §2) correct?
For each lens, verify the claimed (data table, grain, market-list route, screener column, dossier tab,
overlay). Flag any cell that is wrong, missing, or where the same data is double-counted. Is the
"per-symbol-per-day" grain claim accurate per table?

### 2. Are the navigation MECHANICS (doc §4) accurate?
- Confirm/refute: dossier tabs are deep-linkable via `?tab=` AND `location.hash` (default `price`).
- Confirm/refute: row links are query-param `href`s; breadcrumbs are only ad-hoc (`cockpit.py` `crumb`).
- Confirm/refute: nav highlight is resolved by `_altitude_of` over hand-kept `_ALT_OF`/`_SUB_ALIAS`,
  and `/dash/stock` (alias `stock→stocks`) therefore highlights Strategies›Positioning.

### 3. Are the 5 confirmed divergences (doc §6) real?
Especially #1 (RS split: does `leaders` truly read the same RS tables as the Markets RS pages?) and #2
(do `/dash/stocks` Positioning and `/dash/mep` MEP genuinely overlap, or are they distinct enough to keep
separate?). Confirm/refute each with code evidence.

### 4. Is the proposed navigation model (doc §5) sound and SAFE?
- Would the canonical link-helper + lens registry (#1, #5) actually remove the drift, given the
  multi-agent / additive-only doctrine (`AGENTS.md`)? Any risk to the sacred routes
  (`/dash/ratio`,`/dash/rrg`,`/dash/compare`) or the overlay `window.__wfpc` contract?
- Is anything in the model over-engineered or unnecessary? Anything missing (mobile/responsive nav,
  the Pat ⌘K layer, the Trust utility, deep-link state for the screener)?

### 5. Problems & risks
List concrete problems, each with severity (BLOCKER / SHOULD-FIX / NICE-TO-HAVE) and the file/doc-section it concerns.

### 6. Improvements
Prioritized, actionable. For each: the change, why it helps, the risk.

## Output format (markdown)
```
## Verdict
<one paragraph: is the analysis correct? is the proposed model safe to take to Ramana?>

## Matrix verdicts (doc §2)
<table: lens | correct? | correction/citation>

## Mechanics verdicts (doc §4)
<list: claim | confirmed/refuted | citation>

## Divergence verdicts (doc §6)
<table: # | real? | evidence>

## Problems
<list, each: [SEVERITY] problem — location — why it matters>

## Improvements
<prioritized list, each: change — rationale — risk>

## Anything the analysis missed
<free text>
```
