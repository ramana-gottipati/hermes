# Pat — design & improvements (the bot's living spec + shared backlog)

> **What this file is.** The running design reference AND the shared improvements
> backlog for **Pat**, the natural-language guided-search assistant in the Patearn
> web tool (`/dash/pat`). Every Pat component is documented here per section, and
> every improvement idea is logged here. This is also the **shared file Nous
> Hermes (and any agent) appends to** — see §8.
>
> **Binding rule:** when you change a Pat component, update its section here in the
> same commit; when you spot an improvement, log it in §7. Keep it current — this,
> not memory, is how the next session/agent understands Pat.
>
> Sibling of `PROJECT_STATE.md` (the whole-project running doc). Pat's decision
> record lives there as **D55**; the depth lives here.

---

## 1. What Pat is (and the bar)

Pat turns a plain-English question into the right data pull over Patearn's own
SQLite, with tap-chips to refine. **Gemini-Flash-only** (never Claude); the
tap-through path is pure Python/SQL (₹0, can't hallucinate a column).

**The bar is WOW, not "works."** If a market analyst isn't delighted — if the
answer is generic, mis-timed, or buried in noise — the feature has failed its
purpose. Every design choice below serves that bar.

**Live today** (deployed on the VPS): glossary explainer · accumulation · RS-leaders
(timeframe-aware) · fundamentals · **today's movers** · **index performance
(best/worst/turning)** · the Gemini free-text engine · feedback/correction store
(👍/👎 + "what you expected") · clarify-before-guess · 6 selectable avatars
(decoration, picker on its own page) · strategy-grouped example questions on Home.

---

## 2. Architecture, per component

| Component | File | What it does |
|---|---|---|
| **Glossary** | `src/pat/glossary.py` | 39-term data dictionary (grounding). `get`/`find`/`family`. Powers "explain a metric" + grounds the engine prompt. |
| **Flows** | `src/pat/flows.py` | Pure `build_*_query(params) -> (sql, params)`. Read-only SELECTs; **columns/operators come only from constant dicts**, every value bound via `?`. The deterministic, ₹0 core. Flows: accumulation · rs · fundamentals · movers · **index** (best/worst/turning over `index_signals`) · explain. |
| **Disambiguator** | `src/pat/disambiguate.py` | Deterministic helpers used by the engine + the fallback parser (₹0, no LLM). `hints` (vocab→flow, into the parse prompt) · `concepts` · `check` (the quota-proof ₹0 clarify for the classic ambiguities "strong stocks"/"recently") · `clarify_from_flows` · `route_index` (now SUPERSEDED as primary by `understand` — its logic lives on inside `parse_fallback`). Clarify chips are disambiguated **re-runs of the original query**. |
| **Understanding** | `src/pat/understand.py` | The reasoning layer (no LLM here). The model SEMANTICALLY PARSES a query into a structured intent — `universe` (stock/index/sector) → `rank{metric,window,order}` → `filters[]` (a LIST, so two-window asks are native) — then **`compile_intent`** deterministically (₹0) maps that intent onto a flow, a clarify, or an honest `reason:"unsupported"` (never a confident wrong dump). `validate_intent` closes the vocab; `parse_fallback` is a degraded rules-only parser for when the model is unavailable (quota/outage); `SYSTEM_PARSE` is the reasoning prompt. **This replaced the old flat flow-classifier.** |
| **Engine** | `src/pat/engine.py` | Orchestrates: ₹0 `disambiguate.check` clarify first; else Gemini does the structured PARSE (never-Claude) → `understand.validate_intent` → `compile_intent`; on model-unavailable, `understand.parse_fallback`. Compiler output params are re-sanitized through the chip vocab (`_VALID`/`_validate`, defense in depth). Low-confidence → clarify (threshold 50). Cached. |
| **Eval set** | `src/pat/eval_set.py` | The measurement + regression net Pat lacked. `run_compiler_eval` (deterministic, ₹0 — verifies the reasoning core) + `run_route_eval` (query→route end-to-end, fallback or live parser). Gold cases double as the labeled dataset seed for the owned model. Run: `python -m src.pat.eval_set`. |
| **Web/UI** | `src/pat/web.py` | `render_pat()` dispatches flow/explain/free-text/face. Renders data-first tables on the house `table.dt` grid. The persona header + face picker. The Home clues. |
| **Route** | `src/web/dashboard.py` | `/dash/pat` GET (one route; params: flow, explain, q, sector, strength, entry, align, val, qual, grow, bs, own). New chip params **reuse existing captured params** to avoid editing this file. |
| **Feedback store** | `src/pat/feedback.py` | §4 — the `pat_feedback` correction store. Self-contained (owns its table via CREATE TABLE IF NOT EXISTS; never edits db.py). `record`/`update`/`recent_positive_examples`/`recent_corrections`/`stats`. Never raises to the caller. |
| **Pat router** | `src/pat/routes.py` | `POST /pat/feedback` (👍/👎) + `POST /pat/feedback/correct` (the "what did you expect?" enrichment). Mounted from `main.py` (`include_router`) — deliberately OUT of the contended `dashboard.py`. |

**The contract that makes free-text safe:** the engine emits only enumerated chip
keys, validated, which feed the SAME templates the tap path uses. The LLM never
writes SQL and never makes the stock decision — it's NL-understanding at the UI
edge only. (Honors the project doctrine: LLMs offline / never the live decision
loop; the screening underneath is deterministic.)

---

## 3. The answer philosophy (Ramana, binding)

1. **Right, not more.** Give the *correct* answer to *what was asked* — even if it
   shows fewer rows/columns. Do not over-dump. A precise small answer beats a big
   vague one.
2. **The reporting follows the question.** The columns shown, the metric ranked by,
   the timeframe — all driven by the ask, never a fixed template. *(Shipped for RS:
   "over the last month" → ranks by 1m RS, column relabels to "RS 1M". Extended to
   **accumulation** — window ''/1m/3m re-ranks by + leads with the matching DVPT
   power ratio — and to **movers** — today vs this-week (% vs the close ~7 days
   back). Each result LEADS with the asked-for metric ("right not more", §3.1).)*
3. **Supporting data to reconcile.** Alongside the headline answer, show the raw
   evidence so the user can verify we're right — but as *secondary* context, not
   clutter. Data-first: value beside verdict.
4. **WOW or it's pointless.** If the first answer doesn't delight, that's a defect
   to fix (see §4 — first-answer quality is the real target).

---

## 4. Feedback & learning system (the spec — to build)

The goal: Pat **learns** what the user wanted, with or without explicit feedback,
and improves both its **rules** and its **routing**.

### 4.1 Explicit feedback
- **👍 / 👎** on every answer.
- On **👎**, ask two short things: *what was wrong* and *what you expected*. If the
  user types what they wanted, that correction is **gold** — the highest-value
  learning signal.
- Store: `(query, routed_flow, routed_params, verdict, what_wrong, expected_text)`.

### 4.2 Implicit feedback (no thumbs needed)
- **Re-asking the same/similar question = the answer didn't suffice.** A repeat or
  rephrase within the thread is a silent **👎** — capture it as such.
- Requires the conversational thread (session continuity) to detect repeats.

### 4.3 Follow-up taxonomy (classify every follow-up)
| Type | Signal | Meaning | Action |
|---|---|---|---|
| **Extension** | satisfied; asks an additional/new thing not asked before | success; just more | continue the thread; NOT a failure |
| **Clarification / wrong** | "that's not what I wanted", "the data is wrong", asks for detail we should have given up front | **failure** | log as a miss; **change the approach — write/adjust the rule or algorithm** |

The distinction matters: an extension is not a defect; a correction is. Only
corrections drive rule changes.

### 4.4 The two arms of "learning"
1. **Rules / algorithms (explicit).** When a correction reveals something we should
   have inferred up front, **codify a rule** in the engine/flows. *Example already
   shipped:* "if the question names a timeframe, set the RS window" became a rule.
   These are deterministic, ₹0, and the most reliable improvement.
2. **Routing corrections (model-side).** The correction store feeds **few-shot
   examples** into the engine prompt (immediate, ₹0, learns the user's phrasings).
   The same store is the **labeled dataset** to later fine-tune an *owned* open
   model offline (per the project's offline-LLM doctrine — not the borrowed Nous
   agent, which runs a remote free model we can't train). See PROJECT_STATE §1265.

### 4.5 First-answer quality (the real target)
If corrections pile up, the first answer is bad. So:
- **Clarify before guessing.** When intent/timeframe is ambiguous ("recently",
  "strong stocks"), Pat asks ONE short question *before* answering, instead of
  guessing a default. (Engine returns a `clarify` intent with suggested answers.)
- **Track churn.** Count refinements-per-answer; high churn = first answer missed =
  a signal that feeds the rule/correction learning.

---

## 5. Suggestions / clues (shipped, keep improving)

Home now shows **strategy-organized example questions** (`_EXAMPLES` in `web.py`):
Today's market · Momentum/RS · Strong-hand delivery (DVPT) · Quality & value ·
Learn the metrics. Each is real free-text — tapping it answers AND teaches the
shape of question that works. **Principle:** the clues must inform the user what
he can ask, strategy by strategy. Keep expanding as flows are added.

---

## 6. Conversational thread (to build)

Pat is stateless today; each query is independent and the result is a dead end.
Target: a **chat thread** where the result stays and each message refines the
running context ("now only IT", "sort by volume", "what about yesterday"). Reuse
the Telegram bot's conversation spine (`src/assistant/conversations.py`,
`chat.py`). This unlocks §4.2 (implicit re-ask detection) and §3.2 (refinement).

---

## 7. Improvements backlog (per section — keep logging)

> Format: `[area] priority — idea (why)`. Tick when shipped.

> **📚 The master question catalog lives in [pat-question-catalog.md](pat-question-catalog.md)** —
> the exhaustive, de-duplicated set of what users will ask (built from a wide research sweep:
> real Screener/Trendlyne phrasings, FinTwit/Hinglish lingo, full TA/FA space, voice/STT, 12
> personas, follow-ups, educational long-tail, events, and adversarial/OOD), tagged into 5 bands
> (✅ live · ❓ clarify · 🟡 data-in-DB-no-flow · 🔴 no-data · ⛔ out-of-domain). **Headline finding:**
> most "Pat can't do that" is 🟡 (a small flow away), not 🔴. The catalog's Part 12 is the ranked
> roadmap and Appendix A seeds the `eval_set.py` expansion. The Tier-0 cheap-wins below come from it.

- ⬜ `[accumulation]` P0 🟡 — **distribution flow**: add a `character` chip to `build_accumulation_query`
  (ACCUMULATION default → DISTRIBUTION/CONSOLIDATION). `accum_character` already stores all four labels
  and is indexed nightly; the flow hardcodes `='ACCUMULATION'`. Few-line change, highest ROI — unlocks
  "stocks under distribution / smart money exiting / distribution near the highs".
- ⬜ `[rs]` P0 🟡 — **weak / RS-laggard flow**: `direction` chip on `build_rs_query` + flip the
  unsupported-clarify for the worst side. `rs_rank` (both ends) + RS slopes already stored; only the top
  is served. Removes Pat's single biggest "can't do that" surface ("weakest stocks", "biggest laggards").
- ⬜ `[fundamentals]` P0 🟡 — **honor the parsed valuation/quality `op`** (today `compile_intent` drops it
  and returns the *default* cheap screen, so "overvalued stocks" returns *cheap* stocks — a live bug) +
  add `overvalued`/`risky` presets. Also surfaces high-debt / high-pledge / low-ROCE inverse screens.
- ⬜ `[quality]` P1 🟡 — **hard-disqualifier kill-list flow** over `hard_disqualified=1` + `disqualifier_reasons`
  (populated in the DB, zero read path) and a **pt14 quality-tier screen** (`quality` currently routes to the
  PE/ROCE ratio screen, not the pt14 tiers).
- ⬜ `[single-stock]` P1 🟡 — **red-flag / snapshot card**: one symbol → character + RS + 52w-dist + PE + D/E
  + pledge + disqualifier reasons. New *shape* (single row, not ranked universe); answers "what's wrong with X /
  tell me about <stock>" and feeds the advice-redirects. (NL engine is a screener today — no single-stock path.)
- ⬜ `[guardrails]` P1 ⛔ — **advice/predict/feature-assumption redirect branch**: detect buy/sell/alert/predict
  verbs → hand over the data screen instead of falling silently to glossary search (SEBI-advice boundary; see
  catalog Part 5). One-time identity+disclaimer block for meta/greeting/"are you SEBI registered".
- ⬜ `[input]` P2 — **robustness layer** (catalog Part 7 + Appendix B): ticker alias map + fuzzy resolve,
  number-word + lakh/crore parser, homophone map, Hinglish data-noun + advisory-verb detection, HTML-escape echoes.
- ⬜ `[methodology]` P2 — **"explain the strategy" capability** (canned, doctrine-grounded, ₹0 like the glossary):
  4 pillars / why-DVPT-matters / RS-vs-RSI / what-makes-a-conviction-pick. Catalog Part 10 lists the 8 acceptance questions.

- ✅ `[movers]` today's-movers flow — was mis-routing to RS (gap closed).
- ✅ `[rs]` timeframe-aware window — "last month" → RS 1M (reporting follows ask).
- ✅ `[home]` strategy-grouped example clues — weak suggestions fixed.
- ✅ `[avatar]` decoration-only, picker on its own page — stop faking function.
- ✅ `[feedback]` P0 — correction store SHIPPED (§4): `pat_feedback` via self-contained
  `src/pat/feedback.py` (CREATE TABLE IF NOT EXISTS; db.py untouched); `POST /pat/feedback`
  + `/pat/feedback/correct` in a NEW `src/pat/routes.py` router mounted from `main.py`
  (dashboard.py untouched); 👍/👎 bar on every answer with a "what did you expect?"
  capture on 👎 (records the 👎 immediately, then enriches the same row — gold signal).
- ✅ `[engine]` P0 — clarify-before-guess SHIPPED (§4.5): engine returns a `clarify`
  intent (question + 2–3 suggested-answer chips) on intent ambiguity ("strong stocks")
  or vague timeframe ("RS leaders recently"); `_clarify_view` renders it. Chips are
  disambiguated re-runs of the original query (context preserved, no clarify loop).
- ✅ `[engine]` P1 — synonym/disambiguation dictionary SHIPPED (`disambiguate.py`,
  Nous Hermes #3): delivery→accumulation, momentum→RS, quality→fundamentals,
  gainers→movers. Feeds prompt hints + drives the clarify. Deterministic, ₹0. The
  ambiguous strength words are deliberately EXCLUDED from the synonym lists so they
  reach the intent clarify instead of auto-anchoring.
- ✅ `[engine]` P1 — confidence-threshold clarify SHIPPED (Nous Hermes #2): the model
  emits a `confidence`; below 50 the pick becomes a clarify among the plausible flows
  (its choice + the flows the analyst's vocabulary points at).
- ✅ `[engine]` P1 — few-shot from the correction store SHIPPED (§4.4.2):
  `engine._fewshot_block()` injects the last ~6 confirmed 👍 routings (rendered in
  the exact output JSON, so they double as format anchors) + ~4 👎 corrections
  ("they did NOT want X; they wanted: <expected>") into the routing prompt. ₹0,
  fails open to '' before any learning. The same store is the labeled dataset for
  the future OWNED offline model.
- ⬜ `[thread]` P1 — conversational refinement (§6) + implicit re-ask detection.
- ✅ `[all flows]` P1 — "reporting follows the question" extended (§3.2): accumulation
  window ('' / 1m / 3m → re-rank by + lead with ratio_today_vs_power_1m/3m) and movers
  window (today vs this-week, % vs the close ~7 days back via a bound date join). Both
  ride the captured `align` route param (no dashboard.py edit). Engine menu + chip
  vocab updated so a timeframe phrase fills the window. *(Note: no weekly DVPT column
  exists, so accumulation is Today/1M/3M not D/W/M; fundamentals "emphasis" still open.)*
- ✅ `[answer]` P1 — "right not more" lead-metric: each windowed result LEADS with the
  asked-for column (RS slope / DVPT ratio / weekly %), header names the window.
- ✅ `[index]` NEW flow (correction-driven) — **index performance** over `index_signals`:
  best/worst over 1m/3m/6m/1y + a "turning up" reversal lens (laggards now rising 1M).
  Deterministic `disambiguate.route_index` so "worst performing index … that started
  turning up" routes here (₹0, 0 model calls), not to stock RS-leaders. **Closed a real
  first-answer miss** (the live screenshot: that exact query returned 0 RS-leaders;
  it now answers e.g. Nifty Realty −18% 1Y / +6% 1M). This is §4.4 arm-1 in action —
  a correction became a rule + a capability.
- ✅ `[engine]` REWORK (the real fix, not a patch) — replaced the flat flow-classifier
  with **structured query understanding**: the model semantically parses a query into a
  logical intent (`universe → rank{metric,window,order} → filters[]`) and a deterministic
  ₹0 **compiler** (`understand.compile_intent`) maps it onto a flow / clarify / honest
  "unsupported". This gives Pat actual *logical decomposition* (universe is a first-class
  decision; compound two-window asks are native) instead of keyword-matching, so first
  answers are right *by construction* and generalize beyond hand-written phrase lists.
- ✅ `[eval]` gold eval set (`eval_set.py`) — `run_compiler_eval` (₹0 reasoning check,
  13/13) + `run_route_eval` (end-to-end). The measurement + regression net Pat lacked,
  and the labeled-dataset seed for the owned model.
- ⬜ `[fundamentals]` P2 — emphasis-follows-question (lead with the asked ratio when a
  fundamentals query names one, e.g. "ranked by ROE" → ROE leads). Carved out of the
  reporting-follows-question item above.
- ⬜ `[learning]` P2 — when ≥N corrections of one shape accumulate, surface a
  proposed RULE for review (semi-automated rule-writing).
- ⬜ `[model]` P2 — offline fine-tune an owned open model on the correction store
  (the real "training"; needs a GPU, done offline, then swapped into the router).

---

## 8. Brief for Nous Hermes (shared-file collaboration)

**You are invited to improve Pat.** This file is the shared backlog. Please:
1. Read §1–§6 (Pat's design) and §7 (the open backlog).
2. Propose improvements — especially for §4 (feedback/learning rules) and §7 — and
   **append them to §7** as new `⬜ [area] priority — idea (why)` lines, or add a
   `## 9. Nous Hermes notes` section below and write there. Do not edit §1–§6
   unless correcting a factual error.
3. Focus on: better clarifying questions; the follow-up taxonomy heuristics; rules
   that would have made the FIRST answer right; richer strategy clues.

**Constraint (honest):** Pat's *live* router stays cheap and on a model we can
swap; per the project doctrine, any LLM/heavy work is an **offline research aid**,
never the live decision loop. So propose offline/rule improvements, not live-LLM
dependencies in the picking path.

**Handoff — the bridge WORKS (2026-06-20).** Claude can relay to the Nous agent:
`ssh hermes 'docker exec -u 10000 -w /opt/data/patearn hermes-agent /opt/hermes/.venv/bin/hermes --yolo -z "<message>"'` (her brain is now Gemini 2.5 Flash; see memory `nous-hermes-bridge`). Loop: relay a Pat brief → capture her reply → record it in §9 (her first round is there). She also keeps her own journal at host `/root/.hermes/patearn/channel/learnings.md`.

---

## 9. Nous Hermes notes

**Round 1 — improvement ideas from Nous Hermes** (relayed via the bridge, 2026-06-20; her brain = Gemini 2.5 Flash). All deterministic/rule-based (doctrine-consistent); several reinforce §4 + §7:

1. **Timeframe extraction + clarify-chips when missing.** Rule-parse explicit timeframes (today/yesterday/last week/1m/QTD/YTD/52w); if a time-sensitive metric (RS/DVPT) has NO timeframe, don't guess — present timeframe tap-chips (Today | Last Week | Last Month | 3-Month). *(Extends the shipped RS-window rule to all time-sensitive flows; ties into clarify §4.5.)*
2. **Parameterized template matching with a confidence threshold.** Match the query to structured templates; if confidence < ~70%, present alternative template suggestions as chips ("Did you mean: DVPT ignition in IT, or RS leaders last month?"). *(A concrete clarify mechanism, §4.5.)*
3. **Semantic synonym / disambiguation dictionary.** Map synonyms → canonical concepts (delivery→DVPT, momentum→RS, quality→14-pattern, strong hands→accumulation); for ambiguous terms ("strength" = RS or fundamental?) offer a disambiguation chip. *(NEW deterministic synonym layer in front of the engine — improves first-answer routing, ₹0. Added to §7.)*
4. **User query history + contextual auto-suggestions.** Track each analyst's successful queries; prioritize personal-history autocomplete; proactively suggest from current market activity. *(Personalization; ties into the thread §6.)*
5. **Human-in-the-loop rule refinement.** Log every 👎 (query + routed response + "what you expected"); a weekly review turns recurring misinterpretations into new rules/synonyms/templates — improvement WITHOUT retraining. *(Exactly §4.4 arm-1 operationalized — adopt.)*

**Round-2 status (2026-06-20, Claude build session).** Her round-1 ideas **#1, #2, #3,
#5 are now SHIPPED + LIVE**: #3 → `disambiguate.py` synonym layer; #1 → timeframe
clarify-chips on time-sensitive flows; #2 → confidence-threshold clarify; #5 → the
`pat_feedback` 👎-with-expected store (the weekly-review dataset). #4 (personal query
history / autocomplete) remains open — ties into the conversational thread (§6).
**Round-2 relay: PENDING.** The brief (recap of the 6 shipments + a request for her
next deterministic/offline ideas: rules for first-answer-rightness, better clarifying
questions, the extension-vs-correction taxonomy, richer clues) was sent twice via the
bridge on 2026-06-20 but her brain (Gemini 2.5 Flash, **free tier**) returned HTTP 429
(20 req/min quota, contended). Re-send when quota refreshes — the brief text is in the
session history. *(Note: the new deterministic clarify layer REDUCES this shared
free-tier pressure — ambiguous asks now resolve with 0 Gemini calls.)*

---

## 10. Session wrap — 2026-06-20/21 (Pat learns, first answers right, and now REASONS)

### Round 3 (2026-06-21) — engine rework: from keyword-matching to logical thought

> **Why.** The analyst's verdict after the index miss: *"we have not prepared Pat
> properly … it picked up wrong queries, did not apply logical thought at all."* Correct
> — and the index *fix itself* (a `route_index` of `if "worst" in q` rules) was **more
> keyword-matching, not reasoning**. So we replaced the brain, not patched it again.

**Shipped (`7fa19fc`), verified LIVE with the real model:**
- *Generalization proof:* "show me the weakest sectors over twelve months that are
  bouncing" — a phrasing in **no** keyword list — routes to Index · Laggards · turning up
  (parser decomposed sector→index / return / 1y / worst / improving-filter). And "worst
  performing **stocks** this year" now returns the honest redirect ("no worst-stocks
  screen yet — did you mean worst indices, or RS leaders?"), not a wrong dump.
- **Structured query understanding** (`src/pat/understand.py`) — the model now does a
  SEMANTIC PARSE into a logical intent: `universe` (stock/index/sector, decided FIRST) →
  `rank{metric,window,order}` → `filters[]` (a LIST → two-window asks like "worst over 1Y
  AND improving over 1M" are native). A deterministic ₹0 **compiler** maps the intent onto
  a flow, a clarify, or an honest `unsupported` — the three failures behind the miss
  (wrong universe, inverted polarity, single-window collapse) are now structural
  impossibilities, and it generalizes past hand-written phrase lists.
- **The old flat flow-classifier prompt is gone** (`_menu`/`_SYSTEM` removed). The 5
  flows stay as the safe ₹0 execution layer; only the understanding changed. Compiler
  output is still re-sanitized through the chip vocab (off-menu params can't reach SQL).
- **Gold eval set** (`src/pat/eval_set.py`) — `run_compiler_eval` **13/13** (deterministic
  reasoning check) + `run_route_eval` (end-to-end, fallback **8/8**). The measurement +
  regression net Pat never had; the gold cases seed the owned-model dataset.
- **Honest degradation:** the live parse needs Gemini; when it's down (quota), a rules-only
  `parse_fallback` still reasons about universe/metric/window so the index miss stays fixed
  even with the model OFF. `disambiguate.check` keeps the classic ambiguities ("strong
  stocks") quota-proof. The real removal of the model dependency is the owned model (§7 P2).

**The honest limit (told to the analyst):** the *live* router is a borrowed model we can
only ground (reasoning prompt + gold few-shot), not train. Real "training" = the owned
offline model on the accumulating `pat_feedback` + eval dataset. The rework makes that
dataset well-shaped (query → structured intent → route).

---

### Round 2 (2026-06-20)

**Mission:** make Pat learn, and make the FIRST answer right. All five mission items
shipped, each verified on a synthetic DB and committed Pat-files-only, then deployed
end-to-end and smoke-tested live — plus a 6th, correction-driven **index flow** built
in response to a live first-answer miss the analyst surfaced mid-session.

**Shipped + LIVE** (`https://srv1704897.hstgr.cloud/dash/pat`), 5 commits:
- **Feedback/correction store** (`7eb1491`) — self-contained `src/pat/feedback.py`
  owns `pat_feedback` (CREATE TABLE IF NOT EXISTS; **db.py untouched**). 👍/👎 on every
  answer; 👎 records immediately then reveals a "what did you expect?" box that
  enriches the same row. New `src/pat/routes.py` router (`POST /pat/feedback` +
  `/pat/feedback/correct`) mounted from `main.py` — **dashboard.py untouched**.
- **Clarify-before-guess + synonym layer** (`50ad20f`) — new `src/pat/disambiguate.py`
  in front of the engine: synonym hints (delivery→accumulation, momentum→RS,
  quality→fundamentals, gainers→movers) into the prompt; and a `clarify` intent on
  ambiguous intent ("strong stocks") or vague timeframe ("RS leaders recently") —
  **0 model calls**. Chips are disambiguated re-runs of the original query (context
  preserved, no clarify loop). Low model-confidence (<50) also → clarify.
- **Few-shot from corrections** (`1456a61`) — `engine._fewshot_block()` injects recent
  👍 routings (in exact output format) + 👎 corrections into the routing prompt. ₹0,
  fails open on a cold store. Same store = the offline-training dataset for an OWNED model.
- **Reporting-follows-the-question** (`8efdc20`) — accumulation window ''/1m/3m (re-rank
  by + lead with the DVPT power ratio) and movers today vs this-week (% vs the close
  ~7 days back). Both ride the captured `align` route param; each leads with the asked
  metric. A synthetic-SQL test caught + fixed a placeholder-ordering bug in the weekly join.
- **Index flow** (correction-driven) — the analyst asked live: *"worst performing index
  in the last one year that started performing better from past one month?"* and Pat
  returned **0 RS-leaders** (3 stacked failures: wrong universe=stocks-not-indices,
  inverted polarity=leaders-not-laggards, single-window-not-a-two-window-reversal). Built
  a new **index flow** over the pre-computed `index_signals` (best/worst over 1m/3m/6m/1y
  + a "turning up" 1M reversal lens) + a deterministic `route_index` so that exact query
  lands here with **0 model calls**. It now answers correctly — e.g. **Nifty Realty**
  (−18% 1Y, +6% 1M, RS slope +3.3, consolidating). §4.4 arm-1 in action.

**BINDING honored throughout:** Gemini-only live router (never-Claude verified —
anthropic fallback discarded); tap path = deterministic ₹0 SQL; columns/operators only
from constant dicts, every value bound; **dashboard.py / db.py / PROJECT_STATE.md never
touched** (parallel session held them — `git status` checked; new params reuse the
captured `align`). Per-increment synthetic verification + live smoke (feedback POST,
clarify with 0 Gemini, weekly movers, 1M accumulation, table auto-created).

**Open / next (see §7 + the §12 kickstart):** conversational thread (§6) + implicit
re-ask detection; personal query-history autocomplete (Nous #4); fundamentals
emphasis-follows-question; semi-automated rule-proposal when corrections cluster (§7 P2);
the offline owned-model fine-tune (§7 P2). **Nous Hermes round-2 relay pending** — her
free-tier Gemini quota was exhausted (§9).

**Operational note:** the shared Gemini **free tier** was quota-exhausted at deploy time
(news classifier + parallel session + Pat router share one key). Pat degrades correctly
(free-text routing falls back to glossary search; deterministic clarify/flows are
unaffected and ₹0). The new clarify layer eases this by resolving ambiguous asks without
a model call. Consider a paid Gemini key or per-workload keys if routing misses persist.

---

## 11. Session wrap — 2026-06-20 (Pat built + deployed end-to-end)

> **⚠ NAMING COLLISION — for Ramana to resolve.** A parallel session locked (2026-06-20): **"Hermes"** = the Nous agent · **"Pattern"** = the operational Patearn/Telegram agent · **"PAT"** = a strategy-expert MIND inside Pattern (trained via Nous Hermes — her channel `pat-training-program.md`). THIS session's **"Pat"** = the **`/dash/pat` web NL-search TAB** (a UI). Two different things sharing the name. Likely reconciliation: the web `/dash/pat` tab is the *front-end surface*, and "PAT the strategy-expert" is the *brain* that should eventually power it — and the web tab's feedback store (§4) is the natural training-data feed for that brain. **Confirm the relationship + any rename before deep integration.**

**Shipped + LIVE on the VPS** (`https://srv1704897.hstgr.cloud/dash/pat`), 12 Pat commits `5184121 → 3ea35e2`:
- Glossary explainer (39 terms) · accumulation · RS-leaders · fundamentals · **today's movers** flows — all deterministic, read-only, ₹0.
- The **Gemini free-text engine** (English → flow+params; never-Claude; cached). Model = **`gemini-2.5-flash-lite`** (2.0-flash free tier is quota-0; this also un-broke the news classifier).
- **Timeframe-aware RS** — "over the last month" ranks by 1m RS + relabels the column "RS 1M" (reporting follows the question).
- **Avatars = decoration** — one face shown, picker on its own `?flow=face` page (stopped faking a function).
- **Strategy-grouped Home clues** — example questions that teach what to ask.
- Pre-deploy **adversarial review** (0 P0s) + 3 P1 fixes. **Perf gate passed** (flows hit indexes; 4–6 ms). Reconciliation: the VPS-only `dashboard.py` work (screener lag-fix + `_mv_*` micro-viz) was verified already-in-git and preserved on deploy.

**Verified:** every increment synthetic-DB tested (route 200 + logic) + live smoke on the VPS.

**Cross-session note (important):** this session ran ALONGSIDE a parallel session doing explosive-move / Portfolio-Tracker work. That session holds uncommitted changes to **`dashboard.py`** and **`PROJECT_STATE.md`**, and owns `research/`, `docs/explosive-move-research.md`. **Pat work deliberately never touched those files** — new chip params reuse the route's already-captured `strength`/`entry` params, and all Pat tracking lives in THIS doc + the auto-memory, not PROJECT_STATE. PROJECT_STATE's Pat session-log is accurate but PARTIAL (stops ~at the engine); **this doc is the current, complete Pat record.** Held-and-untouched: `patearn.py`, `mtf_signals.py`.

**Open (the backlog, §7):** feedback/correction store · clarify-before-guess · few-shot learning · conversational thread · "reporting follows the question" for all flows · the "right not more" answer pass.

---

## 12. Kickstart prompt — next Pat session

> Paste this to start the next session. It is self-contained; it points at this doc.

```
Continue building PAT — the natural-language guided-search assistant in the
Patearn web tool (/dash/pat), already built and LIVE on the VPS. FIRST read
docs/pat-design-and-improvements.md fully — it is Pat's living design, the
improvements backlog (§7), the feedback/learning spec (§4), and the answer
philosophy (§3). Then continue toward ONE bar: the analyst is WOWed and the
FIRST answer is right.

ALREADY SHIPPED (round 2, §10) — do NOT rebuild: feedback/correction store
(pat_feedback + /pat/feedback routes); clarify-before-guess + the deterministic
synonym/disambiguation layer (src/pat/disambiguate.py); confidence-threshold
clarify; few-shot routing from the correction store; reporting-follows-the-question
for accumulation (1m/3m) and movers (today/this-week); the INDEX flow (best/worst/
turning over index_signals); and the ENGINE REWORK to structured query understanding
(universe→rank→filters → compiler) + the gold eval set (src/pat/eval_set.py).

Mission this session — close the learning LOOP and personalize:

1. Conversational thread (§6, P1). Make Pat stateful: the result stays and each
   message refines the running context ("now only IT", "sort by volume", "what
   about yesterday"). Reuse the Telegram bot's conversation spine
   (src/assistant/conversations.py, chat.py). This UNLOCKS §4.2 implicit re-ask
   detection (a rephrase within the thread = a silent 👎 — log it as such) and the
   churn metric (refinements-per-answer = first-answer-missed signal).

2. Personal query-history autocomplete (Nous Hermes #4, §9). Track this analyst's
   successful queries; prioritize personal-history autocomplete on the ask box;
   proactively suggest from current market activity. Deterministic, ₹0.

3. Fundamentals emphasis-follows-question (§7). When a fundamentals query names a
   ratio ("ranked by ROE", "cheapest"), LEAD with that column — extend the
   reporting-follows-question rule to the fundamentals flow.

4. Semi-automated rule-proposal (§7 P2). When ≥N corrections of one shape cluster
   in pat_feedback, surface a PROPOSED rule/synonym for review (turn the §4.4
   weekly-review loop into a prompt). Then scope the offline OWNED-model fine-tune
   on the correction store (the real "training"; offline, then swap into router).

5. Re-send the Nous Hermes round-2 relay (§8/§9) once her Gemini free-tier quota
   refreshes; fold her next ideas into §7/§9.

BINDING CONSTRAINTS: Gemini-Flash-only on the live router, never Claude; the tap
path is deterministic SQL (₹0); columns/operators ONLY from constant dicts, every
value bound via ?; a parallel session may STILL hold dashboard.py / PROJECT_STATE.md
— check `git status` first and do NOT edit them while held (reuse existing route
params; track in this doc). Verify each increment on a synthetic in-memory DB
(route 200 + the logic), commit per-increment (ONLY Pat files: src/pat/* + this
doc), deploy via `scp src/pat/*.py hermes:/opt/hermes/src/pat/ && ssh hermes
'systemctl restart hermes-api'`, and smoke-test live. Update §7 as you ship; invite
Nous Hermes (§8) to append ideas to §9.

First action: read the doc, then build the feedback store.
```

