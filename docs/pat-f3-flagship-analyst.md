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
| F3-3 | **True server-side session THREAD** — a thread store so a refine can SUBTRACT ("drop the F&O ones") / pivot ("vs last quarter"), not only string-append; carries the last structured intent | current multi-turn is string-concat only — can't subtract/pivot. Mission item 1 = "server-side session context" | NEW `src/pat/thread.py` + `web.py` `routes.py` | ⬜ |
| F3-4 | **Deepen EXPLANATIONS** — `why` drills into the underlying rows + provenance (as-of period, n promises resolved, veto reason, the concall/delivery/RS evidence) with the coverage caveat | mission item 3 = "drilling into provenance + underlying rows, with the as-of/coverage caveat" | `flows.py` `web.py` | ✅ |
| F3-5 | **Ranked top-N** — honor "top 5", "best 10" → a bound `limit` on the surfaced flows | F2-7 deferred; mission item 4 = "ranked rankings" | `understand.py` `flows.py` `web.py` | ⬜ |
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
