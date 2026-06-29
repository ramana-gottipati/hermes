# Lane F3 — Pat flagship conversational analyst (Round 3, continuation of F2)

> Self-driving lane (docs/parallel-sessions-ROUND3.md). OWN ONLY: `src/pat/*` +
> `src/web/strategist_view.py` + `src/web/screener_plus.py`. Descriptive-only; every
> answer provenance-stamped (§9.8); closed-vocab → deterministic compute (the LLM never
> writes SQL or invents a number). Per item: build → deploy → `scripts/regression_sweep.sh`
> + `chrome_gate.py` BOTH PASS → verify on the real VPS Gemini stack → commit owned files → next.

## Where F2 left off (do NOT redo)
F2 shipped 7/8: accuracy+hallucination/OOD eval harness (`a795e0b`), `why-X` explanations
(`a795e0b`), STATELESS multi-turn refine via combined-query strings (`aed857f`), save-as-board
write path (`aed857f`), configurable workbench (`950830a`), proactive confluence alerts
(`950830a`), Screen+↔Pat bridge (`c1d2870`). F2-7 (top-N + time-series) was DEFERRED.

## F3 backlog (≥8 substantial — the genuine remaining gaps to "flagship")

| # | Item | Why it's a real gap | Files | Status |
|---|---|---|---|---|
| F3-1 | **Time-series asks** — "credibility trend for X", level+momentum+trend over periods; a `trend` task over the `credibility_series` table (18,944 PIT rows) | F2-7 deferred this; mission item 4 names it explicitly. Data EXISTS (credibility_series) | `understand.py` `flows.py` `web.py` `engine.py` `disambiguate.py` | ✅ |
| F3-2 | **Saved-boards LIST + REOPEN** in Pat itself — a `?flow=boards` view: list saved boards, one-click reopen, delete; not just the Save button | boards.py write path exists but Pat has no list/reopen surface; mission item 2 names "list + reopen" | `web.py` `routes.py` | ✅ |
| F3-3 | **True server-side session THREAD** — a thread store so a refine can SUBTRACT ("drop the F&O ones") / pivot ("vs last quarter"), not only string-append; carries the last structured intent | current multi-turn is string-concat only — can't subtract/pivot. Mission item 1 = "server-side session context" | NEW `src/pat/thread.py` + `web.py` `routes.py` | ⛔ BLOCKED (architecture + data — see note) |
| F3-4 | **Deepen EXPLANATIONS** — `why` drills into the underlying rows + provenance (as-of period, n promises resolved, veto reason, the concall/delivery/RS evidence) with the coverage caveat | mission item 3 = "drilling into provenance + underlying rows, with the as-of/coverage caveat" | `flows.py` `web.py` | ✅ |
| F3-5 | **Ranked top-N** — honor "top 5", "best 10" → a bound `limit` on the surfaced flows | F2-7 deferred; mission item 4 = "ranked rankings" | `understand.py` `flows.py` `web.py` | ⏸ DEFERRED (cost discipline — see note) |
| F3-6 | **Extend the eval-set + OOD/hallucination** — new bands for trend/boards/top-N; more adversarial + SEBI redirect cases | mission item 5 = "extend the eval-set + hallucination/OOD; tighten SEBI guardrails" | `eval_set.py` `disambiguate.py` | ✅ |
| F3-7 | **Tighten SEBI guardrails** — broaden the advice/predict/target-price/PMS-recommendation redirect vocabulary; never a buy/sell/predict | mission item 5; the guardrail vocab is narrow today | `disambiguate.py` | ✅ |
| F3-8 | **Polish proactive ALERTS** — surface the watchlist-alignment + dropped-from-confluence read with as-of + descriptive caveat on the workbench; opt-in framing | mission item 6 = "polish the proactive alerts" | `alerts.py` `strategist_view.py` | ✅ |

## Progress log
- (boot) baseline: live sweep PASS (31 routes + 4 overlays); eval compiler 31/31, route 43/44
  (PE-15 pre-existing fail), hallucination 8/8, explain 493/495. Owned files clean.
- F3-1 — credibility TIME-SERIES flow (`trend`): `build_credibility_trend_query` over
  credibility_series (18,944 PIT rows) + `_trend_flow` renderer (level/momentum/trend/tape
  per period, own provenance footer) + `detect_trend` deterministic router (₹0) + SYSTEM_PARSE
  teaching + Home clue + a "credibility trend →" chip on the why-credible view. Descriptive
  (not a buy signal). Live ✓ (`flow=trend&sym=NAVINFLUOR` 200, real data); NL battery 7/8
  (trend asks all route; the 1 miss = pre-existing live-Gemini movers flake, fallback correct);
  eval unchanged (31/31, 43/44, hallu 8/8); BOTH gates PASS.
- F3-2 — saved-boards MANAGER (`flow=boards`): a dedicated list/reopen/delete surface
  (`_boards_flow` + `_board_href`) that the Home quick-chips only teased; reuses the existing
  boards.py store + `/pat/board/{save,delete,list}` endpoints (already built). Reopen reruns
  the NL query against the latest data; delete is a confirm→fetch POST. "manage boards →" chip
  added to the Home boards strip. Live lifecycle verified (page 200 · save→appears · delete→ok);
  BOTH gates PASS. (web.py only — backend was already there.)
- F3-6 + F3-7 — eval-set extension + SEBI guardrail hardening: new TREND band (6/6: trend
  asks route to the series, a bare "why credible" does NOT collapse into it) + 5 tighter OOD
  cases (target-price / multibaggers-will-become / recommend-portfolio / stock-tip / good-
  investment). Guardrail vocab broadened: new `_G_RECOMMEND` (tips / portfolio-build) +
  extended `_G_ADVICE` (good investment / which-to-buy) + `_G_PREDICT` (which-will-become /
  multibagger-for-20xx). `_route_one` in the eval now mirrors engine.route's real order
  (guardrail → check → route_extra → fallback). 0 false positives on legit screens (quality
  compounders / multibagger candidates / credible managements all pass). Eval now route 54/55
  (OOD 10/10, TREND 6/6, hallu 8/8); live redirects confirmed; BOTH gates PASS.
- F3-8 — proactive ALERTS polish (`_alerts_strip`): now surfaces TWO reads the snapshot
  already computed but the strip dropped — (a) names that DROPPED OUT of confluence since
  the last check (a descriptive signal, explicitly "not a sell call") and (b) the opt-in
  WATCHLIST-alignment line (`alerts.watchlist_alignment`, previously unused — shows only when
  a watchlist overlaps confluence, so it stays silent when empty). Both carry the as-of date +
  descriptive caveat. strategist_view.py only; VPS selftest + workbench 200 + both gates PASS.
- F3-4 — deepened the WHY-credible explanation: it now drills past the score into the
  UNDERLYING rows. New `build_credibility_evidence_query` over concall_expectations_vs_actual
  (14,942 rows) + `_why_credibility_evidence` renders "The receipts" — the specific recent
  guidance vs. what actually happened (BEAT / in-line / MISSED / over-promised / concealed,
  colour-coded, with the metric + period + the management's own words). Also added peer-median
  context (above/below the peer median) + a richer provenance footer (rank N of the pilot ·
  M concalls scored · as-of period). Descriptive evidence, never a recommendation. Live ✓
  (NAVINFLUOR shows receipts + peer median + rank); eval unchanged; BOTH gates PASS.

## Deferred / blocked — honest rationale (loop §6: report blockers, don't fake)

- **F3-3 (true server-side thread) — ⛔ BLOCKED by architecture + data.** The `/dash/pat`
  page route lives in `dashboard.py` (NOT in my ownership) and its handler takes neither a
  FastAPI `Request` nor cookies, and hardcodes its query kwargs — so a server-side thread
  token the PAGE GET reads cannot be plumbed without editing `dashboard.py` (forbidden).
  web.py already documents this prior deliberate choice ("no server thread state, no
  dashboard.py token plumbing"). Separately, the canonical subtraction example "drop the
  F&O ones" is ALSO data-blocked: there is no F&O / derivatives universe in the DB
  (`stock_index_membership` has no F&O index), so that exclusion is unanswerable regardless.
  A POST-only thread in my OWNED routes.py could persist last-intent + merge, but the page
  can't read it back without the forbidden edit. Honest call: leave the stateless
  combined-query multi-turn (which already covers additive refines + the new trend flow) and
  report the blocker rather than fake a thread that can't round-trip. *Unblock path (future):
  a parallel-owned dashboard.py change to pass `Request`/a `tid` param into render_pat.*
- **F3-5 (ranked top-N) — ⏸ DEFERRED per cost discipline.** Threading a user `limit` through
  every `build_*` flow signature + each of ~5 large renderers (chip rails + sector chips +
  table) + the parse→compile→dispatch chain is "a focused build of its own" (F2's exact
  rationale when it deferred F2-7). The lists are already ranked/sorted and capped (60–80),
  and the house `table.dt` grid is client-sortable, so the marginal value is low against the
  CLAUDE.md cost-discipline guardrail ("bundle changes; avoid long iterative tinkering").
  Not in the headline ask. Carries forward.

## Mission summary — 6/8 shipped, 2 honestly deferred/blocked
Shipped: F3-1 (credibility time-series) · F3-2 (saved-boards manager) · F3-4 (deepened
why-credible into the underlying receipts + peer-median + rank provenance) · F3-6 (eval
TREND band + tighter OOD) · F3-7 (SEBI guardrail hardening) · F3-8 (alerts polish:
dropped-out + watchlist alignment). Every change: descriptive-only, provenance-stamped,
closed-vocab→deterministic-compute, dashboard.py untouched, both gates PASS each commit.
