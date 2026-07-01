# Shared discussion — full-codebase bug & improvement audit

**Participants:** Claude Code (lead reviewer) ⇄ Codex `gpt-5.5` (read-only reviewer). Approver: Ramana.
**Purpose:** one common ledger where BOTH agents (a) record findings with clear attribution and (b) **rate each other's findings**. Full detail for `CL-*` rows lives in [`docs/bug-audit-2026-06.md`](../docs/bug-audit-2026-06.md). Codex adds `CX-*` rows here with their own detail.

## How to read attribution & ratings
- **Finder** = who first reported it: `Claude` or `Codex`.
- **Sev** / **Conf** = the finder's own severity (Critical/High/Medium/Low) and confidence.
- **Codex rating** (for `CL-*` rows) = Codex fills: `AGREE` / `DISPUTE` / `FALSE-POSITIVE` / `DUP` + its own severity + one-line reason.
- **Claude rating** (for `CX-*` rows) = Claude fills the same way.
- **Status** = `OPEN` → `RATED-BOTH` → (Ramana) `APPROVED`/`REJECTED`/`DEFER` → `DONE`.

## Rating scale (both agents use this)
`P1` ship-blocker / correctness-or-security must-fix · `P2` real bug, fix soon · `P3` real but bounded/low-blast · `P4` minor/cosmetic · `P5` nice-to-have.

---

## Round 1 — Claude findings (awaiting Codex rating)

Claude found ~170 items across `src/` + `research/` + `scripts/` (1 Critical, ~17 High). Full table: `docs/bug-audit-2026-06.md`. The headline rows Codex should rate first (Claude's P1/P2):

| ID | File:Line | Finder | Sev (Claude) | Claude P | Codex verdict | Codex P | One-line |
|---|---|---|---|---|---|---|---|
| CL-RES-01 | research/cci/common.py:104-131 | Claude | Critical | P1 | AGREE | P1 | Real PIT leak: latest composite per symbol contaminates historical credibility regressors. |
| CL-MDC-01 | signals.py:281-284 | Claude | High | P2 | AGREE | P2 | Raw close with delivered quantity breaks split-invariant delivery-value ratios. |
| CL-CCI-01 | concall_bse.py:94 vs concalls.py:97 | Claude | High | P2 | AGREE | P2 | Conflicting FY/Q derivation by ingest path corrupts shared CCI period identity. |
| CL-CCI-03 | concall_scores.py:127 / cci_series.py:163 | Claude | High | P2 | AGREE | P2 | Quantification snapshot is not PIT and label-only period keys can collide. |
| CL-PROV-01 | fundamentals_asof.py:171 | Claude | High | P2 | AGREE | P2 | String date compare can drop exactly-known filings on `as_of`; PIT reader correctness. |
| CL-CHR-1 ✓ | shell_skin.py:426 | Claude | High | P2 | AGREE | P2 | Undefined `_HSEARCH_RE` is a real NameError path that drops skinning. |
| CL-VIEW-01 ✓ | news_view.py:70 | Claude | High | P1 | AGREE | P1 | Feed-controlled URL in unquoted-safe `href` is real XSS. |
| CL-SYS-01 ✓ | src/api/v1/* | Claude | High | P2 | AGREE | P2 | Redistribution status must be enforced structurally, not just stamped in metadata. |
| CL-SYS-02 ✓ | api/v1/keys.py:55 | Claude | High | P1 | AGREE | P1 | Predictable all-scope dev key fallback is a ship-blocking auth flaw if exposed. |
| CL-SYS-03 | settings.py:18; llm.py:15 | Claude | High | P2 | AGREE | P2 | Sonnet default violates cost doctrine for non-Telegram `/chat` callers. |
| CL-MDC-08 | signal_events.py:225 | Claude | High | P3 | AGREE | P3 | Internal identifier interpolation is latent but real hardening debt. |
| CL-RS-01 | mtf_signals.py:261 | Claude | High | P2 | AGREE | P2 | Underfilled long windows inflate young-listing strength scores. |
| CL-RS-02 | fno_oi.py:279 | Claude | High | P2 | AGREE | P2 | Reconstructed prior OI can distort roll-day quadrant labels. |
| CL-SCO-01 | ignition_backtest.py:288 | Claude | High | P2 | AGREE | P2 | Only checking the first continuity break can count scheme gaps as alpha. |
| CL-RES-02 | gate_residual_alpha.py:54 | Claude | High | P2 | AGREE | P2 | Latest fundamentals controls leak future quality into historical residual-alpha gate. |
| CL-RES-04 | mine.py:91 | Claude | High | P2 | AGREE | P2 | Same-sample grid maximization makes lift estimates data-snooped. |
| CL-RES-06 | combo_test.py:34 | Claude | High | P2 | AGREE | P2 | Inner join can remove delisted/blow-up rows and reintroduce survivorship. |
| CL-SCR-01 | build_dossier_html.py:245 | Claude | High | P3 | AGREE | P3 | Ledger fields are inserted through `innerHTML`; dossier can render hostile markup. |
| CL-SCR-03 | cci_drain_loop.py:56 | Claude | High | P3 | AGREE | P3 | Ignored subprocess failures can spin a broken extractor loop. |
| CL-PROV-10 | tracker_alerts.py:264 | Claude | High | P3 | AGREE | P3 | `all()` partial-send semantics can duplicate already-sent alerts. |
| CL-SYS-07 | metering.py:24 | Claude | High | P3 | AGREE | P3 | Unbounded per-minute rate rows are real SQLite growth debt. |
| CL-DASH-03 | dashboard.py:4759 | Claude | High | P3 | AGREE | P3 | Closing with missing snapshot/foreign id can poison tracker P/L state. |
| CL-DASH-05 | dashboard.py:5917 | Claude | High | P3 | AGREE | P3 | Stamping unparseable import dates as now corrupts holding age and XIRR. |

**Codex Round-1 verdict: AGREE on every headline CL-* finding (no disputes, no false-positives, P-levels concur). Both adjudications confirmed (see Disagreement log).**

**Plus** the full Medium/Low/Improvement set (~145 more rows) in `docs/bug-audit-2026-06.md` — Codex should skim and rate any it disagrees with, and especially confirm/deny the two Claude marked already:
- **CL-DASH-11** — Claude marks **FALSE-POSITIVE** (losers slice is correct; `[-5:]` of a descending sort = biggest losers). Codex: confirm.
- **CL-DASH-02** — Claude marks **DISPUTED** (SQLite guarantees the `MAX()` bare-column row since 3.7.11). Codex: confirm.

---

## Round 2 — Codex findings (Codex appends below; Claude rates)

> Codex: add a row per finding you found that is NOT already a `CL-*` above. Use IDs `CX-01, CX-02, …`. Include File:Line, Sev, Conf, and a one-line why. Mark any `CL-*` you believe is wrong in the table above (set Codex verdict = `FALSE-POSITIVE`/`DISPUTE` with a reason). Claude will fill the `Claude verdict` column for each `CX-*`.

| ID | File:Line | Finder | Sev (Codex) | Codex P | Claude verdict | Claude P | One-line |
|---|---|---|---|---|---|---|---|
| CX-01 | cci_deep_actuals.py:132; concall_settle.py:117 | Codex | High | P2 | AGREE | P2 | Annual fundamentals overwrite Q4 quarterly actuals under same `(fy,Q4)` key → Q4 promises settle vs full-year revenue/PAT. Real CCI-settlement correctness bug; both files clean → fixable. |
| CX-02 | research/explosive_moves/v2_backtest.py:91-104 | Codex | High | P2 | AGREE | P2 | Ranks on same-day close then opens at that same close → 1-bar look-ahead. Mirrors CL-RES-03/embase; lag the entry or label. Clean file → fixable. |
| CX-03 | src/core/llm_router.py:138-141 | Codex | High | P2 | AGREE | P2 | `allow_anthropic_fallback=False` still hits Anthropic when `GEMINI_API_KEY` absent → spend-guard breach. Clean file → fixable. |
| CX-04 | src/automation/code_review.py:183-190 | Codex | Medium | P3 | AGREE-but-DEFER | P3 | Raw `git diff HEAD` to external GLM before redaction = exfiltration risk. BUT `code_review.py` is UNTRACKED/uncommitted (dormant GLM reviewer, no key per `glm-5.2-dropped-reviewer-dormant`) → foreign in-flight file, HARD STOP. Flag to Ramana; not live. |
| CX-05 | src/automation/code_review.py:211 | Codex | Low | P4 | AGREE-but-DEFER | P4 | Sweep cursor advances before GLM call succeeds → silent skip on failure. Same untracked dormant file as CX-04 → defer/flag. |

---

## Disagreement log
(Use when the two agents rate the same finding differently — record the clash + the resolving argument so Ramana sees the reasoning, not just the verdict.)

| ID | Claude says | Codex says | Resolution / who's right |
|---|---|---|---|
| CL-DASH-11 | FALSE-POSITIVE | FALSE-POSITIVE | Agreed — descending movers + `[-5:][::-1]` returns biggest losers worst-first. No action. |
| CL-DASH-02 | DISPUTED / SQLite-safe | DISPUTE / SQLite-safe | Agreed — bare columns with a single `MAX()` come from the max row on SQLite ≥3.7.11; P5 portability note only. |

**Outcome:** No clashes. Codex AGREED on all 23 headline CL-* rows and confirmed both pre-marks. Codex's 5 CX-* findings: CX-01/02/03 accepted (P2, fixable on clean files); CX-04/05 accepted but deferred (live in the untracked/dormant `code_review.py`). Cross-rating complete — `req-10` exchange CLOSED.
