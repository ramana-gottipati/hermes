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
| **Engine** | `src/pat/engine.py` | Free-text → `{flow, params}` via Gemini. Validates against the chip vocab (off-menu dropped). **Never-Claude** (discards Anthropic fallback). Cached. Prompt built from the chip dicts + glossary (single source of truth). |
| **Web/UI** | `src/pat/web.py` | `render_pat()` dispatches flow/explain/free-text/face. Renders data-first tables on the house `table.dt` grid. The persona header + face picker. The Home clues. |
| **Route** | `src/web/dashboard.py` | `/dash/pat` GET (one route; params: flow, explain, q, sector, strength, entry, align, val, qual, grow, bs, own). New chip params **reuse existing captured params** to avoid editing this file. |
| **Feedback** *(planned)* | `src/pat/feedback.py` | §4 — the correction store + learning loop. Not yet built. |

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
- ⬜ `[feedback]` P0 — build the correction store (§4): 👍/👎 + "what you expected",
  schema `pat_feedback`, a feedback endpoint (avoid the contended `dashboard.py` —
  use a `src/pat/routes.py` router included in `main.py`), and the 👍/👎 UI on
  answers.
- ⬜ `[engine]` P0 — clarify-before-guess (§4.5): a `clarify` intent + render.
- ⬜ `[engine]` P1 — few-shot from recent corrections (§4.4.2): inject the last N
  corrections into the prompt so routing learns the user's phrasings.
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

**Handoff:** the Nous agent (D34, `nousresearch/hermes-agent` at `:9443`) is an
isolated container running a remote free model — there is no API wired for it to
write here automatically yet. Today the loop is: feed this file + this brief to
the Nous agent via the Portal; it returns improvement notes; paste them into §9.
(If we later wire an endpoint, the main session can automate this.)

---

## 9. Nous Hermes notes
<!-- Nous Hermes: append your improvement proposals here. -->
