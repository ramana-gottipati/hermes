# PR #1 — Full-codebase bug-audit remediation (`bugfix/audit-p1-2026-06-30` → `main`)

> Paste-ready PR body. 31 commits ahead of `main`. Source of truth = `docs/bug-audit-2026-06.md` § "Remediation status". `gh` is not installed on the laptop — create the PR from the GitHub web UI or `gh` on another box and paste this.

## What this is

A line-by-line bug + improvement audit of the **whole tree** (`src/` 146 files / ~59.5K LOC, `research/` ~9.2K, `scripts/` ~1.4K) by 12 parallel deep-readers, cross-checked by Codex (`gpt-5.5`, read-only), then independently re-reviewed in source. **~170 findings** (1 Critical, ~17 High, ~60 Medium, rest Low). This PR fixes the **1 Critical + all High + the bulk of Medium/Low**, plus Codex's `CX-01..03`.

Doctrine respected throughout: PIT / no-look-ahead · rupees-not-shares · descriptive-only (no new return-edge) · cheap-LLM-in-timers · secrets-in-`.env` · build-additive. Every fix was real-data-verified read-only on the VPS; `chrome_gate` + `nav_integrity_gate` PASS at HEAD.

## Headline fixes

**Security / crash (P1 — already live on prod):**
- `CL-SYS-02` removed a hardcoded predictable all-scopes `/v1` dev key; `CL-SYS-01` wired the never-enforced `/v1` redistribution licensing gate.
- `CL-VIEW-01` news-feed `href` XSS (scheme allowlist + quote-escape); `CL-SCR-01` dossier client-side `esc()`.
- `CL-CHR-1` undefined `_HSEARCH_RE` (NameError silently dropped the entire skin); `CL-CHR-3` import-time `IndexError` app-crash guard.
- `CL-VIEW-03/08`, `CL-DASH-08` None-edge / schema-drift 500 guards.

**Correctness — value-changing tier (recompute already run, 3786 syms / 5.94M rows):**
- `CL-MDC-01` delivery-value now on split-consistent `adj_close` (split-in-window no longer mixes scales).
- `CL-RS-01` under-filled long-window baselines no longer inflate young-listing scores; `CL-RS-02` OI-change uses true prior-day OI.
- `CL-RES-01` (Critical) CCI credibility look-ahead leak → residual-alpha gate now renders UNSCORED, not a false PASS; `CL-RES-02` PIT controls.
- `CX-01` Q4 quarterly promises settle vs Q4 quarterly actuals, not full-year (⚠ see re-settle note below).
- `CX-02` research next-bar-open entry; `CX-03` Anthropic-fallback spend leak; `CL-SYS-03` Haiku genuine default.

**Medium/Low:** ~75 correctness/perf/hygiene fixes across market-data, RS, scoring, provenance, CCI, system, pat, views, chrome, scripts, research (see audit doc tables). `CL-DASH-14` removed 705 lines of dead post-`return` route bodies.

## Deploy posture (read before merging)

- **Prod is at the reviewed-P1 state** (P1 fixes live, 0 drift). Everything else rides this merge via a **coordinated deploy** — see `docs/POST-MERGE-DEPLOY-RUNBOOK.md` (turnkey, verified).
- **⚠ CX-01 re-settle is a DELIBERATE decision, not automatic.** Deploying the Q4-settle fix requires re-running settle → scores → credibility-series, which **shifts ~1,568 per-promise verdicts** (MET 2822→2828, MISSED 1910→1860, PARTIAL 224→236) and **supersedes published CCI track-record figures**. The code is merged; the recompute is gated on your explicit go (runbook Step 2). Descriptive-only — no ranking/return-edge change.

## Explicitly NOT in this PR

- **Blocked on the parallel session's uncommitted tree edits** (do not clobber): `CL-CCI-01/03/04/05/10/11/13/14` (`concall_*`), `CL-MDC-09` (`index_signals`), `CL-RS-07` (`rsband`). Take once those edits are committed.
- **Owner-tracked deferrals** (Codex `req-11`-confirmed out of audit scope): `CL-PROV-11` (`enrich.py`), `CL-SCR-10` (`pipeline_status.py`), `CL-PROV-17` + `CX-04/05` (`code_review.py` — ⚠ **CX-04 must add diff redaction before any external-GLM send; the GLM reviewer timer stays disabled until then**). `CL-CHR-6` (cockpit palette), `CL-DASH-17` (constant IN-list) — low priority.
- **False-positives (no action, Codex-confirmed):** `CL-DASH-11` (movers slice correct), `CL-DASH-02` (SQLite `MAX()` guaranteed).

## Verification

- Independent read-only source re-review of every fix commit → all correct; the 3 cross-session file overlaps are complementary, not conflicting.
- All touched modules compile (py3.10 VPS venv); `chrome_gate` + `nav_integrity_gate` PASS; market-data recompute confirmed materialized in stored rows (`stock_signals` fresh through 2026-06-30).
