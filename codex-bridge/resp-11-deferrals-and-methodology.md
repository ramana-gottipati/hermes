# resp-11 — Codex verdicts (merged from the danger-full-access run; the -o capture got clobbered by the wrapper message, so this is the reconstructed-from-transcript clean copy)

## Part A — Untracked-File Deferrals

| File | Verdict | Reason |
|---|---|---|
| `src/automation/enrich.py` | **LEAVE DEFERRED** | Real CL-PROV-11 bug, but the file is untracked, not in `git ls-files`, and not hard-imported by committed Python. Durable docs/state/provenance/table references → feature/data-foundation ownership, not a leaf audit fix. No in-repo timer/service → spend risk bounded to manual/deployed owner runs. Track later in the owning feature commit with the circuit-breaker fix. |
| `scripts/pipeline_status.py` | **LEAVE DEFERRED** | Untracked standalone ops script, zero importers. CL-SCR-10 is a low-blast one-shot status-report robustness bug; first-tracking it inside the audit PR buys little and violates the "do not absorb foreign WIP" rule. Track/fix with the owner script cleanup. |
| `src/automation/code_review.py` | **LEAVE DEFERRED** | Defer the whole feature unit, not just this file. Untracked: `code_review.py` + `scripts/hermes-code-review.{service,timer}` + `setup-code-review.sh`; zero committed importers; no-ops without `GLM_API_KEY` (D68 dormant). Splitting CX-04/05/CL-PROV-17 into the audit PR would first-track someone else's dormant feature. **Security note: CX-04 must block deploy/enable of the GLM reviewer; when the owner lands it, track all four files together WITH redaction/path-filtering before any external-GLM send, cursor-advance-after-success, and a shared byte budget.** |

## Part B — CL-CHR-6
**LEAVE COSMETIC-ONLY for this audit branch.** `cockpit.py` still has many legacy hardcoded palette hexes (chart options + inline styles), but `shell_skin.py` already retints key class-based holdouts under `body.uk-skin`. A proper hex→token migration is broad, visual-regression-prone, and touches a frozen/deployed chrome file; do it as a focused UI/chrome pass with browser verification, not in the audit cleanup tail.

## Part C — Methodology Recommendations (second opinion; Ramana decides)
1. **OI band 3×/⅓:** reasonable conservative first guard; render OI-change indeterminate outside the band and keep an exceptions log for later calibration.
2. **CCI GATE-B `UNSCORED`:** correct; show `UNSCORED` with the reason — hiding it looks "missing", PASS/FAIL would be dishonest.
3. **`MAX_REAFFIRM_GAP_MONTHS=24`:** sensible default (code comment documents a distribution break after 24m); keep tunable, don't chase now.
4. **CCI unnamed-segment residual / extracted `subject` column:** worth doing, but **P2 after the audit merge** — score-affecting, ~1 session, needs extraction/schema care.
5. **CL-SYS-10 `/chat` shared secret:** keep opt-in for the current single-tenant/LAN posture unless the route is internet-exposed. **CL-SYS-11 `tier=next(iter(scopes))`:** fix when next touching `/v1`; informational, not an auth bypass (scopes drive authorization).

**Net:** Codex CONFIRMS leave all 3 untracked findings + CL-CHR-6 deferred; no new autonomous action falls out of Part C (all are Ramana calls, now with a second opinion). req-11 CLOSED.
