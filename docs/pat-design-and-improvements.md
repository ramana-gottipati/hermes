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
(timeframe-aware) · fundamentals · **today's movers** · the Gemini free-text engine
· 6 selectable avatars (decoration, picker on its own page) · strategy-grouped
example questions on Home.

---

## 2. Architecture, per component

| Component | File | What it does |
|---|---|---|
| **Glossary** | `src/pat/glossary.py` | 39-term data dictionary (grounding). `get`/`find`/`family`. Powers "explain a metric" + grounds the engine prompt. |
| **Flows** | `src/pat/flows.py` | Pure `build_*_query(params) -> (sql, params)`. Read-only SELECTs; **columns/operators come only from constant dicts**, every value bound via `?`. The deterministic, ₹0 core. |
| **Disambiguator** | `src/pat/disambiguate.py` | Deterministic synonym + ambiguity layer in FRONT of the engine (₹0, no LLM). `hints` (vocab→flow, into the prompt) · `concepts` · `check` (→ `clarify` on intent/timeframe ambiguity) · `clarify_from_flows` (low-confidence fallback). Clarify chips are disambiguated **re-runs of the original query**, so context is preserved and they can't loop. |
| **Engine** | `src/pat/engine.py` | Free-text → `{flow, params}` \| `{flow:"clarify",…}` \| None. Runs `disambiguate.check` first (₹0 clarify); else Gemini with hints+few-shot prompt; reads a `confidence` and converts a low-certainty pick to a clarify (threshold 50). Validates against the chip vocab (off-menu dropped). **Never-Claude** (discards Anthropic fallback). Cached. |
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
   "over the last month" → ranks by 1m RS, column relabels to "RS 1M". The same
   principle must extend to every flow.)*
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
- ⬜ `[all flows]` P1 — extend "reporting follows the question" (§3.2) beyond RS:
  accumulation timeframe (D/W/M), fundamentals emphasis, movers window (today vs
  this week).
- ⬜ `[answer]` P1 — "right not more" pass: lead each result with the directly-asked
  metric prominent, demote supporting columns to secondary.
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

---

## 10. Session wrap — 2026-06-20 (Pat built + deployed end-to-end)

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

## 11. Kickstart prompt — next Pat session

> Paste this to start the next session. It is self-contained; it points at this doc.

```
Continue building PAT — the natural-language guided-search assistant in the
Patearn web tool (/dash/pat), already built and LIVE on the VPS. FIRST read
docs/pat-design-and-improvements.md fully — it is Pat's living design, the
improvements backlog (§7), the feedback/learning spec (§4), and the answer
philosophy (§3). Then continue toward ONE bar: the analyst is WOWed and the
FIRST answer is right.

Mission this session — make Pat LEARN and make first answers RIGHT:

1. Feedback/correction store (§4, P0). 👍/👎 on every answer + a "what did you
   expect?" capture on 👎 (the gold signal). Persist to a `pat_feedback` table
   via a SELF-CONTAINED src/pat/feedback.py (CREATE TABLE IF NOT EXISTS on first
   use — do NOT edit db.py). Feedback endpoint in a NEW src/pat/routes.py router
   included from main.py — do NOT touch dashboard.py.

2. Clarify-before-guess (§4.5, P0). When intent/timeframe is ambiguous
   ("recently", "strong stocks"), the engine returns a `clarify` intent with 2–3
   suggested answers; Pat asks ONE short question instead of defaulting. Count
   refinement-churn per answer as the implicit-miss signal.

3. Few-shot learning (§4.4.2). Feed the last N corrections from the store into the
   engine prompt so routing learns the user's phrasings immediately. The same
   store is the offline-training dataset for an OWNED open model later (NOT the
   borrowed Nous agent — it runs a remote free model we can't fine-tune).

4. "Reporting follows the question" everywhere (§3.2): RS already honors the
   timeframe; extend to accumulation (D/W/M) and movers (today/this-week), and
   lead every result with the directly-asked metric ("right not more", §3.1).

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

