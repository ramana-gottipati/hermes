Read-only output for Claude to merge. I did not edit `DISCUSSION-bug-audit.md`.

## Round 1 — Claude Findings

| ID | File:Line | Finder | Sev (Claude) | Claude P | Codex verdict | Codex P | One-line |
|---|---|---|---|---|---|---|---|
| CL-RES-01 | research/cci/common.py:104-131 | Claude | Critical | P1 | AGREE | P1 | Real PIT leak: latest composite per symbol contaminates historical credibility regressors. |
| CL-MDC-01 | signals.py:281-284 | Claude | High | P2 | AGREE | P2 | Raw close with delivered quantity breaks split-invariant delivery-value ratios. |
| CL-CCI-01 | concall_bse.py:94 vs concalls.py:97 | Claude | High | P2 | AGREE | P2 | Conflicting FY/Q derivation by ingest path corrupts shared CCI period identity. |
| CL-CCI-03 | concall_scores.py:127 / cci_series.py:163 | Claude | High | P2 | AGREE | P2 | Quantification snapshot is not PIT and label-only period keys can collide. |
| CL-PROV-01 | fundamentals_asof.py:171 | Claude | High | P2 | AGREE | P2 | String date compare can drop exactly-known filings on `as_of`; PIT reader correctness issue. |
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
| CL-SCR-01 | build_dossier_html.py:245 | Claude | High | P3 | AGREE | P3 | Ledger fields are inserted through `innerHTML`; generated dossier can render hostile markup. |
| CL-SCR-03 | cci_drain_loop.py:56 | Claude | High | P3 | AGREE | P3 | Ignored subprocess failures can spin a broken extractor loop. |
| CL-PROV-10 | tracker_alerts.py:264 | Claude | High | P3 | AGREE | P3 | `all()` partial-send semantics can duplicate already-sent alerts. |
| CL-SYS-07 | metering.py:24 | Claude | High | P3 | AGREE | P3 | Unbounded per-minute rate rows are real SQLite growth debt. |
| CL-DASH-03 | dashboard.py:4759 | Claude | High | P3 | AGREE | P3 | Closing with missing snapshot/foreign id can poison tracker P/L state. |
| CL-DASH-05 | dashboard.py:5917 | Claude | High | P3 | AGREE | P3 | Stamping unparseable import dates as now corrupts holding age and XIRR. |

## Adjudications

| ID | File:Line | Finder | Sev (Claude) | Claude P | Codex verdict | Codex P | One-line |
|---|---|---|---|---|---|---|---|
| CL-DASH-11 | dashboard.py:5599 | Claude | Low | P5 | FALSE-POSITIVE | P5 | Confirmed: descending movers plus `[-5:][::-1]` returns biggest losers worst-first. |
| CL-DASH-02 | dashboard.py:GROUP BY MAX row | Claude | Low | P5 | DISPUTE | P5 | Confirmed low/non-actionable for SQLite: bare columns with single `MAX()` come from the max row; only portability debt. |

## Round 2 — Codex Findings

| ID | File:Line | Finder | Sev (Codex) | Codex P | Claude verdict | Claude P | One-line |
|---|---|---|---|---|---|---|---|
| CX-01 | src/automation/cci_deep_actuals.py:132; src/automation/concall_settle.py:117 | Codex | High | P2 | _TODO_ | | Annual fundamentals overwrite Q4 quarterly actuals under the same `(fy, Q4)` key, so quarterly Q4 promises can settle against full-year revenue/PAT. |
| CX-02 | research/explosive_moves/v2_backtest.py:91-104 | Codex | High | P2 | _TODO_ | | Rebalance ranks on same-day close features and opens new positions at that same close, giving fills after seeing the signal close. |
| CX-03 | src/core/llm_router.py:138-141 | Codex | High | P2 | _TODO_ | | `call_extractor(... allow_anthropic_fallback=False)` still calls Anthropic when `GEMINI_API_KEY` is absent, contradicting the Gemini-only spend guard. |
| CX-04 | src/automation/code_review.py:183-190 | Codex | Medium | P3 | _TODO_ | | Scheduled code review sends raw `git diff HEAD` to external GLM before path filtering/redaction, risking secret/private diff exfiltration. |
| CX-05 | src/automation/code_review.py:211 | Codex | Low | P4 | _TODO_ | | Sweep cursor advances before the GLM call/report succeeds, so quota/network failures silently skip that source batch until wraparound. |

## Disagreement Log

| ID | Claude says | Codex says | Resolution / who's right |
|---|---|---|---|
| CL-DASH-11 | FALSE-POSITIVE | FALSE-POSITIVE | Claude is right; no action. |
| CL-DASH-02 | DISPUTED / SQLite-safe | DISPUTED / SQLite-safe | Claude is right for current SQLite deployment; keep as P5 portability note only. |