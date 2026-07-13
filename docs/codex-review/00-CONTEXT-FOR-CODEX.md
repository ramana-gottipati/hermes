# Codex Data & Analytical Review — Context Packet

> **Lifecycle: TRANSIENT-CAMPAIGN.** This folder drives a one-time full-estate review of everything
> Patearn *calculates or projects*, run by Codex (gpt-5.5) and adjudicated by Claude. Retire the folder
> once every domain in `FINDINGS-LEDGER.md` is CLOSED and the durable findings have been folded into the
> canonical docs (`docs/strategies/*`, `docs/calculations-and-weights.md`, `docs/metrics-glossary.md`,
> `docs/strategy-ledger.md`, `PROJECT_STATE.md`). Until then it is the live worksheet.

You (Codex) are the **independent adversarial reviewer**. Claude is the domain author and adjudicator.
Ramana (the owner, a financial analyst in Vizag) is the final arbiter on conflicts. Read this whole file
before reviewing any domain.

---

## 1. What Patearn is (one paragraph)

Patearn (formerly "Hermes") is a personal Indian-equity research platform for one expert user. It ingests
**primary-source** market data — NSE bhav copy (EOD OHLC + **delivery**), index membership, F&O/OI,
BSE/XBRL filings & concalls — into a single SQLite datastore, pre-computes signals nightly, and serves
them as a rich analytical web app (`/dash/*`) plus a Telegram assistant. It is **not** a trading system
and **not** a robo-advisor. Its product thesis is *"the best analytical lens for Indian equity research —
one click from pattern to insight — with point-in-time (PIT) rigor on under-covered primary data."*

## 2. The binding doctrine you must review AGAINST (not re-litigate)

These are evidence-backed, deliberate decisions. Do **not** flag them as bugs. **Do** flag any screen,
calculation, or doc that *violates* them.

1. **DESCRIPTIVE-ONLY is the honest, recorded status of almost every strategy.** The house finding
   (`docs/strategy-ledger.md`) is: **price strength is the only gross forward-return engine; value,
   quality, credibility, delivery, accumulation, geometry, and event lenses are veto / filter / context
   layers — never rankers; and no factor here is a fundable net-of-cost alpha vs the index** (Nifty 500
   buy-&-hold, Sharpe 0.89). The single participation-fundable corner is quarterly large-cap
   **LOWVOL_MOM** (~1.02 @₹50cr). ➜ Your job is to confirm the app **never dresses a descriptive lens as
   a prediction, ranking, or return promise**, and never softens a recorded failure.
2. **Look-ahead leakage is the cardinal sin.** Every backtest/event-study must use PIT / "knowable-at"
   dates (filing dates, `provenance_knowable`, `fundamentals_asof`), survivorship-aware universes, and
   placebo/cohort-t controls. Flag *any* place where a forward number could see the future, where a
   universe is survivor-only without disclosure, or where a "surprise/edge" is really covered-name beta.
3. **Cost realism.** A flat 0.3%/turnover Sharpe is a *flat-cost illusion*. Fundability claims require the
   Almgren participation model (`cost_participation.py`). Flag any place a gross/flat-cost number is
   presented as if net/fundable.
4. **Value-based metrics, not share counts.** All cross-time metrics use **rupees** (e.g. DELIV_QTY ×
   CLOSE = "delivered value"), for corporate-action invariance. Flag any raw-share-count comparison across
   time, or any unadjusted price series compared across a split/bonus.
5. **No rupee-constant thresholds.** Use percentiles / percent / z-scores, never a hard ₹ cutoff that
   rots with inflation and market cap.
6. **Primary sources only.** New data must come from NSE/BSE/SEBI/XBRL. The one known non-primary
   dependency being remediated is `screener.py` → `fundamentals*` (disclose where shown; do not extend).
7. **Cheap-model / cost discipline.** Scheduled jobs use pure Python/SQL or cheap LLMs (Gemini Flash
   Lite / Haiku); never Sonnet/Opus on a timer. Deterministic math must not silently call an LLM.

## 3. What "review" means here (all five lenses, every element)

For each element the app **calculates or projects**, scrutinize:

- **(A) Mathematical / statistical correctness.** Is the formula right? Off-by-one in windows? Calendar-day
  vs trading-day confusion? Division by zero / NaN / empty-window handling? Correct percentile/rank base?
  Are averages value-weighted where they should be? Are corporate actions handled?
- **(B) Analytical integrity vs the doctrine (§2).** Leakage, survivorship, flat-cost, descriptive-shown-
  as-predictive, a threshold that is really a ₹-constant, a "surprise" that is covered-name beta.
- **(C) Functional correctness.** Does the code actually compute what its doc/label claims? Do edge cases
  (thin history, newly listed, suspended, illiquid, missing fundamentals) degrade gracefully or silently
  mislead? Does the nightly value match the on-read value?
- **(D) Richness & premium quality, beginner → expert.** Does the screen *earn* its space — one genuine
  insight a novice can read (is there a plain-language "bottom line" / how-to-read scaffold?) AND depth an
  expert can drill into (raw values beside every verdict, provenance, the honest counter-case)? Or is it a
  number with no meaning, a chart that doesn't teach, a verdict with no evidence?
- **(E) Documentation gaps.** Where is the calc undocumented, mis-documented, or drifted from code? Name
  the exact doc that should carry it (`docs/strategies/<x>.md`, `calculations-and-weights.md`,
  `metrics-glossary.md`). Claude will write the doc.

## 4. Canonical references (read these; they encode the frame)

- `docs/strategies/README.md` — status matrix + terminology canon for the 9 strategies.
- `docs/strategy-ledger.md` — **the falsification ledger**: every tested signal, its exact numbers, and
  why it is descriptive-only / failed. This is the benchmark any "edge" must beat. Cite its numbers.
- `docs/calculations-and-weights.md` — the canonical formula/constants explainer.
- `docs/metrics-glossary.md` — metric definitions (also served as site-wide popovers).
- `CLAUDE.md` + `PROJECT_STATE.md` (§ Doctrine, § Decision log) — the running source of truth.

## 5. How to report (STRICT — your final message is parsed by Claude)

Output **only** a findings report in this exact shape. One entry per finding. No preamble, no summary prose
before it. Rank most-severe first.

```
## DOMAIN: <domain name>
## VERDICT: <one line — is the analytical layer sound? biggest risk?>

### F<n> · <P0|P1|P2|P3> · <category: correctness|integrity|leakage|cost-realism|functionality|richness|doc-gap>
- **file:line** path/to/file.py:123  (cite the exact anchor; add more lines if needed)
- **Claim tested:** what the code/screen asserts or computes.
- **Problem:** the precise defect, with the wrong-vs-right behavior. If statistical, name the bias.
- **Failure scenario:** a concrete input/state → wrong output (so Claude can reproduce).
- **Recommended correction:** the specific change.
- **Confidence:** CONFIRMED (I traced it) | SUSPECTED (needs Claude to confirm).
- **Need from Claude:** the one fact/context that would settle it (leave blank if none).
```

Severity: **P0** = wrong number reaches the user / leakage / a descriptive lens sold as a prediction.
**P1** = misleading or materially incomplete. **P2** = correctness-neutral quality/richness gap. **P3** =
doc/nit.

## 6. Ground rules

- **Cite file:line for every claim.** No hand-waving. If you cannot point at code, mark it SUSPECTED.
- **Separate what you traced from what you infer.** Over-claiming wastes the adjudication loop.
- **Respect the doctrine (§2).** "This is descriptive-only" is a *feature*, not a finding — unless a
  surface breaks the fence.
- **Assume the expert user.** Do not recommend dumbing down; recommend *layering* (novice scaffold + expert
  depth). "Premium" here means richer and more honest, not simpler.
- **When you lack context, say so in "Need from Claude"** rather than guessing. Claude will answer and, if a
  doc is missing, write it — then you re-review.
