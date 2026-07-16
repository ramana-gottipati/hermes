# SESSION PROTOCOL — start & end checks for EVERY session (binding)

**Authority:** Ramana, 2026-07-02. This is the wrap-up + boot protocol for **every session in this
work-stream.** It is referenced by `CLAUDE.md` (boot procedure). A session that skips these steps is
incomplete. Two companion files:
- **`docs/NEXT-SESSION-CARRYFORWARD.md`** — the slim, current state + the prioritized work queue + the
  exact takeover prompt. Rewritten at the END of every session.
- `CLAUDE.md` / `AGENTS.md` — the standing guardrails (esp. **#0 full-folder autonomy**, **#8
  primary-sources-only**).

---

## ▶️ AT SESSION START — reference these, in this order (do NOT read full history)
1. `CLAUDE.md` — guardrails, esp. **#0 (full-folder access + autonomy — never ask to access/write/
   delete)** and **#8 (primary-sources-only)**. Then **`docs/FABLE-PROTOCOL.md` §0** — the
   model-parity boot stance (Guardrail #10): binding for EVERY model tier running the session;
   lower tiers escalate at its §4 stop conditions instead of improvising. **Confirm the kernel
   actually loaded: you must be able to quote the "🧠 THINK LIKE FABLE" header and name its 4
   phases (ORIENT · HYPOTHESIZE-THEN-ATTACK · TRACK YOUR OWN EPISTEMICS · ADVERSARIAL CLOSE) —
   the 2026-07-16 Haiku test showed this exact read gets skipped; also state which §5 tier you
   are before picking work.**
2. **`docs/NEXT-SESSION-CARRYFORWARD.md`** — the state digest + the queue. **Start here for what to do.**
3. `PROJECT_STATE.md` — read only the **top Session-log entry** (+ grep a section if needed). Do NOT
   read the whole file — protect the context window.
4. `MEMORY.md` index (auto-loaded) — scan for relevant entries; lazy-load a detail file only if needed.
5. `git fetch` + check the branch tip; run **kickstart-pick-verify** before doing any item marked
   "open" — confirm it wasn't already shipped in a parallel session/branch.

## 🤖 HOW THE SESSION RUNS (autonomy)
- **Fully autonomous. Ramana will NOT answer or give directions.** Do not wait for confirmation.
- **Get guidance from the AGENTS, not from Ramana.** When in doubt on a decision, spawn/consult the
  right agent (the institutional panel personas — factor-quant / buy-side-PM / risk-governance /
  data-product — or a build agent), get its verdict, then proceed. See
  `docs/institutional-panel-assessment.md` for the panel briefs.
- **Full-folder authorization is standing** (Guardrail #0). Never ask to read/write/delete anywhere in
  the repo; never treat a subfolder as needing fresh access. Deploy verified additive changes to the
  VPS without asking.
- **One worktree per lane (working-tree isolation) — BINDING the moment a second actor may touch the tree.** Two sessions sharing the one `D:\Hermes` checkout share one working tree + index → a sibling's `git add -A` / `git reset` absorbs or wipes your staged/uncommitted work (recurred hard on 2026-07-16). Spin an isolated worktree: `scripts/new-lane.sh <slug>` → work + commit + `git push origin HEAD:main` there → `scripts/retire-lane.sh <slug>`. The shared checkout is a fetch/read anchor only. Full rule + gotchas: `docs/worktree-convention.md`.
- **Protect the context window** — lazy-load, don't re-read full docs; delegate breadth to agents and
  keep only their conclusions.
- **Keep the hard guardrails:** primary-sources-only (#8, no Screener/vendors for NEW feeds), cost
  discipline, cheap models in timers, additive-never-replace, no secrets committed, honest/no-overclaim.

## ⏹️ AT SESSION END — the WRAP-UP checklist (all must be done)
1. **PROJECT_STATE.md** — append a new Session-log entry at the top: what shipped + **commit hashes**.
2. **Commit everything**, on `main`. Before each commit: `git diff --cached --name-only` — confirm the
   staged set is **only your files** (no cross-absorption from parallel sessions; no stray `src/web`).
3. **MEMORY + docs** updated (new decisions, failures recorded *and* corrected, weights single-sourced).
   - **Harness TIL** — add ONE line to the Session-log entry: a Claude Code feature NOT used this
     session that would have helped (compounding-learning habit, S86; pairs with the daily claude-til task).
4. **Verify**: routes 200 / gates pass / no orphaned pages / no leaked secrets.
5. **Rewrite `docs/NEXT-SESSION-CARRYFORWARD.md`** — refresh the state digest, re-prioritize the queue,
   remove shipped items, and update the takeover prompt.
6. **Provide the takeover prompt** (below) exactly, so the next session can start hands-free.

## 📋 THE TAKEOVER / CARRY-FORWARD PROMPT (provide verbatim each wrap)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md` (§ AT SESSION
> START), then execute `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom. Full-folder access is granted
> (CLAUDE.md #0) — do not ask for access/write/delete or per-step confirmation. Get guidance from the
> agents, not from me; I will not answer. Keep every hard guardrail (esp. #8 primary-sources-only).
> Wrap up per § AT SESSION END and hand off the next prompt.
