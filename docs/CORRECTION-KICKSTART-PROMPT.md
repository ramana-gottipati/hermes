# CORRECTION + BUG-AUDIT — autonomous next-session kickstart PROMPT

> Paste the block below verbatim as the first message of the next session to launch it **fully autonomous**. It boots from `docs/CORRECTION-ARC-HANDOFF.md` and runs the bug-audit to completion, resolving doubts via the respective agents (not Ramana). (Created 2026-06-30 at wrap. NOTE: `docs/NEXT-SESSION-kickstart.md` is a STALE Session-22 UI doc — ignore it; THIS is the current one.)

---

You are the autonomous **CORRECTION + BUG-AUDIT anchor** for Patearn (`D:\Hermes`), a financial analyst's institutional Indian-equity web product. The QA-correction arc is DONE; you are completing the **full-codebase bug audit**. Run FULLY AUTONOMOUSLY — surface to Ramana ONLY at a hard blocker or a genuine methodology decision that is his. For any other doubt, **clarify via the RESPECTIVE AGENT** (resume the responsible background agent by its ID with `SendMessage`, read its commit/doc, use the codex-bridge reviewer, or spawn a clarification agent) — do NOT ask Ramana routine questions. Use PowerShell for git/ssh (Windows).

━━ BOOT (read fully, in order) ━━
1. **`docs/CORRECTION-ARC-HANDOFF.md`** ← THE kickstart: §0 = latest wrap state (PR #1, in-flight items, resumable agent IDs); §1–7 = full context, the audit branch, open items, non-negotiables, orchestration pattern.
2. `docs/bug-audit-2026-06.md` (170 findings; `CL-*`=Claude, `CX-*`=Codex), `PROJECT_STATE.md`, `CLAUDE.md`, `AGENTS.md`.
3. Memory: `correction-arc-bugaudit-handoff`, `l1-unblock-and-4lane-launch`, `vps-deploy-reality`, `autonomous-blanket-access-multisession`.
4. `git branch --show-current` (expect `bugfix/audit-p1-2026-06-30`), `git log --oneline -15`, `git status --short`. Confirm **PR #1** = https://github.com/ramana-gottipati/hermes/pull/1 ; `ssh hermes 'systemctl is-active hermes-api'`.

━━ CURRENT STATE (verify, don't trust) ━━
On `bugfix/audit-p1-2026-06-30`; PR #1 open (→ `main`). P1 data-correctness + chrome + security fixes committed + deployed live (held OFF main for Ramana's review). In-flight at wrap: UI-tail agent `ac1dffe4` (last view bugs) + the `stock_signals --backfill-triggers` recompute (~48%). Confirm both landed.

━━ MISSION — finish the audit + open items (handoff §4), in order ━━
- **A.** Confirm the recompute finished: `ssh hermes "tail /var/log/hermes-mdc-backfill.log; pgrep -af backfill-triggers"`.
- **B.** Land the UI-tail (resume `ac1dffe4` if stalled; push its commit to PR #1) → UI column empty; confirm.
- **C.** Confirm the `0ec20f5` deploy-drift: `news_view.py` / `src/api/v1/*` / `keys.py` live on the VPS (md5 == branch); deploy if behind (news-XSS / `/v1`-gate / dev-key may not be in prod).
- **D.** Dirty-file data findings (`CL-CCI-01/03` `concall_*`, `CL-MDC-03` `index_signals.py`) — take when `git status` shows those files FREE of the parallel session; else flag.
- **E.** Remaining audit: Medium/Low `CL-*` by domain (disjoint files, check still-open first), then the Codex `CX-*` — run `codex-bridge/req-10` manually first, filter → fix.
- **F.** WRAP: branch → `main` is Ramana's merge of PR #1 after review — do NOT self-merge; once merged, confirm VPS == main + a clean-checkout gate; fold PROJECT_STATE Sessions.

━━ NON-NEGOTIABLES (handoff §5 — every fix) ━━
Verify on **VPS REAL data** (local `hermes.db` = 4-symbol STUB; a stub-invisible bug 500'd prod). UI → in-browser (Claude-in-Chrome). `regression_sweep.sh` + `chrome_gate.py` PASS before EVERY commit; **revert from `*.bak-*` on red**. Deploy: backup → `tr -d '\r'` LF → scp → VPS py3.10 import-test → restart `hermes-api` → health 200 → verify. Commit ONLY owned files (staged-set == exactly your paths; FOREIGN PATH = HARD STOP; never `git add -A`) to the branch; **`git push` to update PR #1**. Descriptive-only; PIT/no-look-ahead; cheap-LLM in timers. **FLAG methodology judgment calls** (handoff §5.7: OI band 3×/⅓, CCI GATE-B `UNSCORED`, `MAX_REAFFIRM_GAP_MONTHS=24`, `/v1` scope predicate, CCI unnamed-segment residual) — those alone go to Ramana.

━━ ORCHESTRATION + AUTONOMY ━━
Dispatch fixes as **background agents by domain / disjoint files** (keeps your context lean); each reads its audit finding, fixes, verifies on VPS real data, commits owned-files-only to the branch, pushes to PR #1. Pace to avoid piling recompute-heavy agents onto the contended VPS — run code-only waves while data recomputes. To clarify a doubt about prior work, `SendMessage` the responsible agent (IDs in handoff §0) or read its commit/doc; for correctness adjudication, write a `codex-bridge/req-NN`. Self-pace; feed waves on completion; surface to Ramana only on a hard blocker, a methodology decision that's his, or the entire audit completing. Keep `docs/CORRECTION-ARC-HANDOFF.md` §0 current so the session after you inherits cleanly.
