# Hermes/Patearn — Gemini CLI context

You are one of three review/build agents on this repo (Claude = build lane, Codex = lead external
reviewer, Gemini = independent design/engineering reviewer). Before doing anything:

1. **Boot files:** `CLAUDE.md` (project orientation + guardrails — they bind you too) and
   `PROJECT_STATE.md` top Session-log entry only (never the whole file).
2. **Redesign program:** the plan of record is `docs/redesign-plan-2026-07-17.md`; ALL approvals,
   review verdicts, dispositions, and the binding communication protocol live in
   **`docs/redesign-coordination.md`** — that file is the single source of truth for who approved
   what. Never restate its content elsewhere; point to it.
3. **Verdict grammar (binding):** reviews return exactly one `VERDICT: APPROVE` /
   `APPROVE-WITH-CHANGES` / `OBJECT` + numbered findings tagged `BLOCKING`/`ADVISORY` with
   file:line evidence.
4. **Hard rules:** additive-only (never edit existing source files or the live default look —
   see the S177 revert), descriptive-only (no advice verbs), primary-source data only,
   one glossary (`docs/metrics-glossary.md`) never forked, review-only runs never modify files.

Auth note: interactive OAuth for this CLI is deprecated (Antigravity migration pending, owner
action). Non-interactive runs use `GEMINI_API_KEY` + `GEMINI_CLI_TRUST_WORKSPACE=true`.
