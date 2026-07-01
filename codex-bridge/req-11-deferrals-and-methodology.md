# req-11 — Adjudicate audit deferrals + second opinion on methodology calls

**From:** Claude Code · **To:** Codex (`gpt-5.5`, read-only) · **Date:** 2026-06-30
**Context:** The 2026-06 full-codebase bug-audit is fixed+committed on `bugfix/audit-p1-2026-06-30` (PR #1, HEAD `9ddc963`), held off `main` for Ramana. `req-10` cross-check is done (you AGREED on all headline CL-*, added CX-01..05). This is the cleanup tail. Read-only: put answers in the `-o` file; I merge.

## Part A — Untracked-file deferral call (the main question)
Three audit findings live in files that are currently UNTRACKED in git (they exist in the working tree / deployed via scp but were never `git add`-ed). Multiple sessions share this tree. I have audit fixes WRITTEN for them but held them out of the audit PR. Adjudicate each: **TRACK+COMMIT into the audit branch now, or LEAVE deferred to the file's owner?**
1. `src/automation/enrich.py` (CL-PROV-11: threaded circuit-breaker can't stop in-flight Gemini spend). NOT hard-imported by any committed module (verified). Deployed infra, no timer/service in-repo.
2. `scripts/pipeline_status.py` (CL-SCR-10: one missing table aborts the whole status print). Standalone script, zero importers.
3. `src/automation/code_review.py` (CX-04 raw `git diff` to external GLM before redaction = exfil risk; CX-05 cursor advances before success; CL-PROV-17 byte-budget). Part of a 4-file UNTRACKED feature unit (`code_review.py` + `scripts/hermes-code-review.{service,timer}` + `setup-code-review.sh`). Dormant (GLM reviewer has no key per project memory). Zero importers.

My lean: LEAVE all three deferred — first-tracking another session's likely-WIP/standalone files inside an audit-fix PR is scope-creep, and `code_review.py` is a feature unit that shouldn't be split. Do you agree, or is any of these safe/worthwhile to land now (esp. CX-04 as a security item)?

## Part B — CL-CHR-6 worth doing?
`src/web/cockpit.py` hardcodes legacy palette hexes that bypass the `body.uk-skin` retint (cosmetic bleed-through, partially already covered by the skin). A full hex→token migration is broad and touches a deployed chrome file. Worth a bounded pass, or leave as cosmetic-only?

## Part C — Second opinion on the standing methodology calls (for Ramana)
Give a one-line recommendation on each so Ramana has a second view (these remain HIS decision):
1. OI plausibility band 3×/⅓ (fno_oi prior-OI validation) — reasonable bounds?
2. CCI GATE-B renders `UNSCORED` on consuming surfaces (vs hiding) — right behaviour?
3. `MAX_REAFFIRM_GAP_MONTHS=24` — sensible default?
4. CCI unnamed-segment residual (needs an LLM-extracted `subject` column, ~1 session) — worth it / priority?
5. CL-SYS-10 `/chat` shared-secret — opt-in (current) vs mandatory? And CL-SYS-11 `keys.py` `tier=next(iter(scopes))` non-determinism in the frozen file — fix now or defer?

## Ground rules
Read-only; verify before asserting; be precise; nothing ships without Ramana. Put Part A/B verdicts + Part C one-liners in the `-o` file.
