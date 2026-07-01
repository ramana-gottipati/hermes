# Codex ⇄ Claude bridge

A file-based mailbox so two agents can collaborate over the **same workspace**
(`D:\Hermes`) with a full audit trail. Untracked by design — this is process
scaffolding, not project code. Safe to `git rm -r` or gitignore anytime.

## Who does what

- **Claude Code (lead/filter):** writes review briefs (`req-NN-*.md`), runs Codex,
  evaluates the replies against the project's direction, and brings a *filtered*
  proposal set to Ramana for approval. Implements **only** what Ramana approves.
- **Codex (`gpt-5.5`, reviewer):** runs **read-only**, reviews the material,
  reports problems, proposes improvements. It **cannot change the workspace** —
  read-only sandbox is the hard guarantee behind "nothing ships without approval".
- **Ramana (approver):** the only one who authorizes implementation.

## The loop

```
Claude writes  req-NN  ─►  Codex reviews (read-only)  ─►  resp-NN
       ▲                                                      │
       │                                                      ▼
   implement  ◄──  Ramana approves  ◄──  Claude evaluates + proposes
   (approved only)                        (PROPOSALS-NN)
```

1. Claude writes `req-NN-<topic>.md` (the brief) + appends a `LOG.md` row.
2. Claude runs Codex read-only against the workspace; Codex's reply is captured to `resp-NN-<topic>.md`.
3. Claude evaluates Codex's findings vs the project's future direction (PROJECT_STATE.md decisions, the additive-not-replace doctrine, cost discipline) and writes `PROPOSALS-NN.md`.
4. Ramana approves/edits/rejects per item.
5. Claude implements only the approved items, then optionally sends Codex a re-review `req`.

## How to invoke Codex (the transport)

Run from `D:\Hermes`. Read-only sandbox, workspace as the shared root, reply captured to a file:

```powershell
codex exec --sandbox read-only -C "D:\Hermes" -m gpt-5.5 `
  -o "codex-bridge\resp-NN-<topic>.md" `
  "Read codex-bridge\req-NN-<topic>.md and follow it exactly."
```

- `--sandbox read-only` → Codex can read the whole tree but cannot write/delete. This is the safety interlock.
- `-C "D:\Hermes"` → both agents share this exact working root.
- `-o <file>` → Codex's final message is written here by the CLI (bypasses the sandbox, so it lands even in read-only).
- Bump review depth with `-c model_reasoning_effort="high"` (costs more).

Ramana can run the exact same command — the bridge isn't Claude-only.
```
