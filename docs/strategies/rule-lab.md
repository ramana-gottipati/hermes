# Rule Lab — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **LIVE TOOL (not a strategy).** The Rule lab is an evidence INSTRUMENT: it takes a user-composed rule and returns an honest verdict from the same gauntlet every house study passes. It never originates a strategy, a rank of its own, or a recommendation. Surface: `/dash/rule-lab` (owner-gated composer; anonymous sees a read-only demo verdict). · **Governing record:** [strategy-ledger.md](../strategy-ledger.md) (verdicts append there only after human approval in the Review Inbox) · D137.
> **Origin:** 🏠 HOUSE (D134 §4-H "bring your idea, we'll kill it honestly" — the evidence factory productized; design by LANE-H S156, build S157-b). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference. Result numbers live ONLY in [strategy-ledger.md](../strategy-ledger.md); code + exact constants live in `src/automation/rule_lab.py` (grammar · BLOCKING wall · verdict law) · `research/explosive_moves/rule_lab_executor.py` (the gauntlet orchestrator) · `src/automation/rule_lab_inbox.py` (queue + Review-Inbox producer). This page states the CONTRACT and links the rest.

**One-line definition:** a closed-vocabulary rule composer ("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly") whose output is judged by the existing evidence factory — pre-registration, walk-forward halves, a random-selection placebo, realistic costs, a capacity read, the Nifty-500 net benchmark — and returned as a verdict in the strategy ledger's own vocabulary.

---

## 1. What it is

Testing an idea used to mean hand-writing a study module. The Rule lab makes falsification a product surface: compose a rule from a fixed vocabulary and the factory runs it through the same gauntlet as house research. Its value is not that it finds winners — it is that **it makes falsification cheap and it refuses to let a known-dead idea be re-walked silently**: any rule matching a recorded failure shape carries the matching ❌ BLOCKING row(s) from [strategy-ledger.md](../strategy-ledger.md), verbatim, stapled to the result before anything runs.

## 2. The grammar (closed vocabulary — the Pat pattern)

```
RULE := SELECT <universe> [WHERE <filter> [AND <filter>]*]
        RANK BY <signal> TAKE <n:5..50> HOLD <horizon> [VETO <veto> [AND <veto>]*]
```

Every token binds 1:1 to a function that already exists and is already tested (`src/automation/rule_lab.py` declares the bindings; the suite proves each callable exists). Universes are **PIT liquidity-percentile bands** (never rupee constants). Deliberately inexpressible: arithmetic composers (weight-tuning is the overfitting engine the ledger exists to prevent), rupee thresholds, entry/exit timing micro-language (the measured exit law says looser-is-better), and single-stock verdicts. Promoting a veto-layer term (CCI, MEP) to a ranker is a **compile-time refusal** carrying its ledger citation (D66).

## 3. The gauntlet (reuse, not new math)

Pre-register (sha256 of the frozen rule text, first registration wins, `rule_lab_prereg`) → PIT tables with the D5-F1 one-day execution lag → `factory.run_strat` walk-forward halves 2012-18 / 2019-26 → random-selection placebo (observed must beat the null p95) → participation-real costs (**net is reported first**) → capacity breakpoint (no stated capacity, no result) → Nifty-500 buy-and-hold net benchmark → verdict. A missing stage is a **refusal to rule** (`NO-VERDICT`), never a partial verdict.

## 4. Verdict vocabulary (the ledger's, verbatim)

`REJECTED` · `WEAKER-THAN-BENCHMARK` · `CONDITIONAL(<condition>)` · `NEW-BENCHMARK` · `NO-VERDICT(<why>)`, each carrying a permanent qualifier (`descriptive-only` / `paper-only` / `flat-cost-only` / `fundable`). `NEW-BENCHMARK` is machine-impossible without net-beats-benchmark in BOTH halves AND a stated capacity AND observed > placebo p95. Decided verdicts land in the **Review Inbox** (`kind='rule_verdict'`) — the ledger is canon and canon carries a human signature, so nothing auto-appends.

## 5. Boundary (SEBI posture — plan §3)

User-directed analysis is analytics, not advice: the user composes the rule; the machine reports cohort arithmetic (SEBI RA Regulations 2014 reg. 2(1)(w) — statistical summaries / user-criteria tools). No single-stock verdicts, no action verbs, no target prices; verdict labels are ledger vocabulary only. v1 is personal-first: the composer is owner-gated, anonymous visitors see a clearly-labeled synthetic demo.

## 6. Operations

`POST /dash/rule-lab/run` only **queues** (`rule_lab_queue`); the owner drains it with the research-venv CLI — `python -m explosive_moves.rule_lab_executor --work` — and the verdict lands on the page and in the inbox. Deliberately no timer (AUD-95); the runner is a human-invoked CLI. Glossary: *Placebo p95 · Capacity breakpoint · Both halves · Prereg gate hash · Flat cost only* ([metrics-glossary.md](../metrics-glossary.md) § Rule lab).
