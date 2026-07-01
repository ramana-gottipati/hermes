# Proposals 01 — evaluated from Codex's review (for Ramana's approval)

**From:** Claude (lead/filter) · **Source:** `resp-01-doc-cleanse-review.md` · **Date:** 2026-06-28
**DECISION (2026-06-29) — Ramana approved.** Path: **additive-only** + **broaden** the
timer-model wording. Implemented same day: `docs/DOC_INDEX.md` regenerated (complete
53-doc map, both passes) + `AGENTS.md` hardened (hard-freeze #6 + four-gate #7 +
cheap-model wording). **No archiving / no deletions** — deferred until the parallel lanes
quiesce and a fresh Codex pass runs. The original proposal is preserved below for the record.

## Safety check (done)
Codex ran read-only and **changed nothing** in the live tree — verified by `git status`
(identical to session start; only new files are `AGENTS.md`, `codex-bridge/`, `DOC_INDEX.md`,
all mine). Even with the OS sandbox bypassed, Codex honored the read-only instruction.

## The big finding (I verified it independently — Codex is right, and it's worse than stated)
My Phase-0 inventory is already stale. `docs/` holds **52** markdown files now, not the ~44 I
indexed. The unlisted ones (`parallel-sessions-PLAN.md`, `parallel-sessions-ROUND3.md`,
`lane-a2-native-ui.md`, `lane-d-…md`, `data-licensing-decision.md`, `harmonic-pattern-design.md`,
`ui-restore-and-migration-TRACKER.md`, `pat-f2-conversational-workbench.md`) were written
**between 22:33 last night and 01:25 today** — i.e. a parallel session is editing docs *right now*.

**Implication (future-perspective lens):** the project is mid-flight across parallel lanes that are
converging. The valuable deliverable is a **trustworthy living map + safe hygiene rules**, NOT a
deletion event. Any `git mv`/archive now risks pulling a doc out from under an active lane — the
collision this whole doctrine exists to prevent. → **Defer all destructive ops; do the additive
parts now.**

## Codex findings I ACCEPT (evaluated, not just relayed)

1. **Regenerate `DOC_INDEX.md` from a fresh, complete scan** (52 docs incl. parallel-session/lane docs). Additive, safe. ✅
2. **§D was too aggressive — keep almost all of it.** Codex read the actual contents + PROJECT_STATE and trimmed my 14 archive candidates to **2 clean archives + 2 fold-then-archive**; the other 10 are still active / parallel-held (P8 gated, Pat routing open, Step-5 backend-gated, etc.). This matches the "never lose work" rule. ✅
   - **ARCHIVE (clean):** `NEXT_SESSION_KICKSTART.md` (root, superseded), `docs/research-prompt-B-cost-realism.md` (implemented; `cost_realism.py` exists, ledger records it).
   - **FOLD-THEN-ARCHIVE:** `docs/explosive-move-NEXT-SESSION.md` (fold named-flow A/B first), `docs/next-session-kickstart.md` (fold live perf/concurrency notes first).
   - **KEEP (still live):** the other 10.
   - **…but DEFER even the 2 clean archives** until the parallel lanes quiesce (my add, not Codex's).
3. **Strengthen `AGENTS.md` with the hard freeze:** `dashboard.py` / `cockpit.py` / `main.py` are FROZEN — new work in new modules + runtime wraps. My draft said "isolate"; PROJECT_STATE records this as *binding* after repeated collisions. ✅
4. **Replace the unsafe "zero inbound imports → delete" rule** with a 4-gate check before any `git rm`: (a) path exists, (b) no `rg` references, (c) not named in PROJECT_STATE/docs/scripts/systemd, (d) **not an entrypoint** (`python -m`, FastAPI router, script, or timer). Hermes runs many modules via `-m`/timers with zero Python imports — the old rule would delete live code. ✅ High-value catch.
5. **Treat research prompts as REFERENCE until an output artifact exists** (separates B=done from A/C=still active). ✅

## Where Codex is WRONG (I'm pushing back)

- Codex flagged the logic-cleanse list as "stale — `*.bak-stockchart` and the `~$…xlsx` lock are absent."
  **False alarm:** they exist in the live tree (`git status` shows `?? src/main.py.bak-stockchart`, etc.).
  They were absent only because **my review copy excluded `*.bak*`/`*.xlsx`**. The list is valid; no action.

## Needs YOUR call (policy — I won't touch doctrine unilaterally)

- **Timer-model wording.** `AGENTS.md` (copied from `CLAUDE.md`) says timers use "Haiku, or no LLM."
  Reality (PROJECT_STATE) = scheduled CCI/enrichment use **Gemini Flash Lite**. Either broaden the
  wording to "approved cheap-model paths only (Haiku + Gemini Flash Lite)" — or keep it strict and
  treat the Gemini cron as the named exception. This is your cost-discipline doctrine, so you decide.

## On approval, I will (additive only — zero deletions):
- Regenerate `DOC_INDEX.md` (complete 52-doc map, with the corrected conservative §D verdicts).
- Harden `AGENTS.md` (freeze rule + 4-gate deletion rule + whichever timer-model wording you pick).
- Leave every existing doc/file exactly where it is. The actual archive/fold waits for a quiet tree
  and a second Codex pass against the regenerated index.
