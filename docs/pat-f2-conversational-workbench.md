# Lane F2 — Pat conversational analyst + analytics workbench (Round 3)

> Self-driving lane (docs/parallel-sessions-ROUND3.md). OWN ONLY: `src/pat/*` +
> `src/web/strategist_view.py` + `src/web/screener_plus.py`. Descriptive-only; every
> answer provenance-stamped; closed-vocab → deterministic compute (the LLM never
> writes SQL or invents a number). Per item: build → deploy → `scripts/regression_sweep.sh`
> MUST PASS → verify on the real VPS Gemini stack → commit owned files → next.

## Backlog (≥8 substantial items)

| # | Item | Files | Status |
|---|---|---|---|
| F2-1 | **Accuracy + hallucination/OOD eval harness** — run each flow against the DB and assert the RESULT satisfies the predicate (RS→rs_rank≥80, overvalued→pe>40, credible→veto-free, planner→all pillars hold); adversarial inputs never reach a non-closed flow / inject SQL; OOD battery redirects | `eval_set.py` | ✅ |
| F2-2 | **Pat EXPLAINS — "why is X credible / accumulating / a leader?"** — a `why` task drilling into the underlying rows + provenance (as-of, source, n, the actual concall/delivery/RS evidence) | `understand.py` `flows.py` `web.py` `engine.py` `disambiguate.py` | ✅ |
| F2-3 | **Multi-turn conversation** — follow-ups/refine ("now only small-caps", "which of those are credible", "vs the IT sector"); a thread token + last-intent store + deterministic merge | NEW `src/pat/thread.py` + `web.py` `understand.py` | ✅ |
| F2-4 | **Save any NL query as a named board** — server-side, reloadable; list/delete; powers the workbench | NEW `src/pat/boards.py` + `web.py` | ✅ |
| F2-5 | **Strategist → configurable WORKBENCH** — show/hide/reorder cards, saved boards as cards, per-strategy deep counts, CSV export | `strategist_view.py` | ✅ |
| F2-6 | **Proactive confluence ALERTS** — edge-triggered "newly aligned" board (snapshot-delta), opt-in, descriptive; surfaced on the workbench | NEW `src/pat/alerts.py` + `strategist_view.py` `web.py` | ✅ |
| F2-7 | **Richer intents** — ranked top-N, time-series ("vs last quarter") | `understand.py` `flows.py` `web.py` | ⏸ DEFERRED (rationale below) |
| F2-8 | **Screener+ ↔ Pat/board bridge** — "Ask Pat: confluence here", save scope as a Pat board | `screener_plus.py` | ✅ `c1d2870` |

Sector slices already worked (scope.sector) and cap-band slices now route through the
planner; the remaining F2-7 (ranked **top-N** + **time-series "vs last quarter"**) is
deferred: top-N needs a `limit` threaded through every `build_*` flow, and time-series
needs historical-comparison queries (rs_rank now vs ~63 trading days ago) — a focused
build of its own, and the lists are already ranked/sorted/capped. Not in the headline
ask; deferred over the cost-discipline guardrail. OOD/hallucination hardening (doc item
8) shipped inside F2-1 (hallucination eval 8/8 + the OOD route band).

## Progress log
- (boot) baseline `regression_sweep.sh` = PASS (30 routes + 4 overlays). Owned files clean.
- F2-1+F2-2 `a795e0b` — why-X explanations + accuracy (10/10) + hallucination (8/8) evals. Live ✓, sweep PASS.
- F2-3+F2-4 `aed857f` — multi-turn refine (combined queries) + save-as-board (server). Live ✓, sweep PASS.
- F2-5+F2-6 `950830a` — configurable workbench (alerts strip + boards + toggles + CSV) + alerts.py. Live ✓, sweep PASS. (fixed a quote_plus NameError on the non-empty boards path; hardened the selftest.)
- F2-8 `c1d2870` — Screen+ → Pat bridge (scope → confluence query + save board). Live ✓, sweep PASS.
- FINAL: eval compiler 31/31 · route 43/44 (PLANNER 12/12) · hallucination 8/8 · accuracy 10/10; 7/16 NL battery on real Gemini all correct; sweep PASS. 7/8 backlog shipped (F2-7 deferred).
