# req-10 — Full-codebase bug & improvement hunt (Codex pass + cross-rating)

**From:** Claude Code · **To:** Codex (`gpt-5.5`, read-only) · **Date:** 2026-06-30

## What Ramana asked for
Go through **every line** of the project, identify bugs AND improvements, and have **both agents rate each other's findings** in one shared file with clear attribution (which item found by whom). Claude has finished its pass. Now you do the same and cross-rate.

## Your task (two parts)

### Part A — Rate Claude's findings
1. Read [`docs/bug-audit-2026-06.md`](../docs/bug-audit-2026-06.md) — Claude's full finding set (~170 items, IDs `CL-*`).
2. In [`codex-bridge/DISCUSSION-bug-audit.md`](DISCUSSION-bug-audit.md), fill the **Codex verdict** + **Codex P** columns for the Round-1 headline rows, and add a row to the disagreement log for any `CL-*` you think is wrong. Verdicts: `AGREE` / `DISPUTE` / `FALSE-POSITIVE` / `DUP`. Priority scale P1–P5 is defined at the top of that file.
3. **Specifically adjudicate** the two Claude pre-marked:
   - `CL-DASH-11` (Claude says FALSE-POSITIVE — the movers "losers" slice is correct).
   - `CL-DASH-02` (Claude says DISPUTED — SQLite guarantees the bare-column `MAX()` row since 3.7.11).

### Part B — Your own independent findings
Audit the same scope **without anchoring on Claude's list** — your value is the items Claude missed. Scope = every `*.py` under `src/` (146 files), `research/` (65 files), `scripts/` (12 files). Add each NEW finding as a `CX-*` row in the Round-2 table of the discussion file (File:Line, Sev, Conf, one-line why). Do not re-report a `CL-*` item; if you independently confirm one, just rate it AGREE in Round 1.

## What matters in THIS codebase (correctness lenses, in priority order)
1. **PIT / look-ahead leakage** — the core product is point-in-time honesty. Any place a value computed from future data (later filings, latest snapshots, same-day close used to decide same-day entry) enters a historical signal/backtest/gate. This is the highest-value class — Claude's one Critical (`CL-RES-01`) and several High items are here.
2. **Research validity** (in `research/`) — survivorship bias, in-sample threshold/parameter selection, train/test leakage, equity-curve/Sharpe construction. A wrong conclusion here is worse than a crash.
3. **Rupees-not-shares / split-invariance** — cross-time metrics must be value-based (`CL-MDC-01`).
4. **Security** — SQL injection (esp. f-string-interpolated identifiers/values), XSS (note `_esc` in dashboard.py:520 escapes only `& < >`, NOT quotes), unauthenticated spend endpoints, hardcoded secrets, the unenforced `/v1` redistribution gate.
5. **Spend discipline** — cheap-model-only in scheduled jobs; circuit-breakers that don't actually stop in-flight LLM calls; unbounded loops/caches.
6. **Robustness** — 500s on sparse/missing data, `int(nan)`, NaN rendered in UI, swallowed exceptions hiding data gaps, connection leaks, py3.10 f-string-backslash (VPS).

## Ground rules
- **Read-only.** You cannot and must not modify the workspace. Your output is findings + ratings only.
- Verify before asserting — read enough surrounding context that you're confident it's a real defect, not intended behaviour. Claude already hand-verified `CL-CHR-1`, `CL-VIEW-01`, `CL-SYS-01/02`, `CL-MDC-03` and rejected `CL-DASH-11`; double-check those if you disagree.
- Be precise with `File:Line`. One-line rationale per finding.
- Nothing ships from this exchange without Ramana's approval.

## How you'll be run (Ramana executes; auto-dispatch is sandbox-blocked on this Windows box)
```powershell
codex exec --sandbox read-only -C "D:\Hermes" -m gpt-5.5 `
  -c model_reasoning_effort="high" `
  -o "codex-bridge\resp-10-full-codebase-bug-hunt.md" `
  "Read codex-bridge\req-10-full-codebase-bug-hunt.md and follow it exactly. Edit codex-bridge\DISCUSSION-bug-audit.md is not possible (read-only) — instead, write your Round-1 ratings and Round-2 CX findings, and the two adjudications, into the -o output file using the SAME table columns as DISCUSSION-bug-audit.md, so Claude can merge them in."
```
(Read-only means you can't write the discussion file directly; put your ratings + `CX-*` findings in the `-o` response file using the same columns, and Claude will merge them into `DISCUSSION-bug-audit.md`.)
