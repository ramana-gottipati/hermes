# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`); **NEVER ask
Ramana for file/folder/tool access in any form — a permission prompt that still fires is a BUG to log
at wrap (CLAUDE.md #0-bis), never a cue to ask.** Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

## 🏛 AUDIT BOOT-CHECK (2026-07-02/03, binding)
The audit reference is **`docs/AUDIT-2026-07-02-institutional-review.md`** (117 AUD items; statuses
are being updated IN the doc as lanes land fixes — trust the doc over this digest).
1. **Never run `scripts/setup-news.sh` on the VPS** (AUD-28 — reverts live units).
2. **Never `systemctl start` a hermes timer mid-day** (AUD-95 — `Requires=` fires the job; the ONE
   exception: `hermes-backup.timer` + `hermes-db-backup.timer` carry no `Requires=` by design).
3. **🔒 PERIMETER IS CLOSED (AUD-01, S77):** uvicorn binds `127.0.0.1:8000`; ufw allows only
   22/80/443/9443. **Curl gates via `https://srv1704897.hstgr.cloud` or ssh-localhost — the raw
   `:8000` from outside is DEAD.** `/chat` + `/conversations` need header
   `X-Hermes-Secret: <CHAT_SHARED_SECRET from /opt/hermes/.env>`.
4. **SSH is KEY-ONLY (AUD-34):** password auth refused; laptop default key authorized. sshd config
   lives in `sshd_config.d/00-hermes-hardening.conf` (the `00-` prefix is load-bearing).
5. **hermes-api bind lives in a systemd DROP-IN** (`hermes-api.service.d/override.conf`) — survives
   unit rewrites; don't "fix" the main unit file.

## STATE DIGEST (as of S77/S77b, night of 2026-07-02→03 UTC — 3+ concurrent lanes)
- **Queue #3 CLOSED — universal pledge veto reads the SHP primary source** (`6e2160b`→`07aca8d`
  adopted the LIVE sibling implementation; `concall_veto.py` + `concall_scores.py` byte-identical
  git↔VPS). Verified live: JPPOWER → `(True, 'promoter pledge 73%')`; vetoed set = EMSLIMITED +
  PAISALO (22%); rerank of 2026-07-02 21:25 UTC already used the fix. `--selftest` CLI exists (13
  checks). ⚠ JPPOWER has no concall corpus so it never appears in `concall_scores` — the veto bites
  via `compute_veto`/`veto_map`.
- **Audit P0s:** AUD-01 perimeter DONE (`cc988c6`, residual: optional Caddy basic-auth on /dash) ·
  AUD-34 key-only SSH DONE (residual: fail2ban, sudo user) · AUD-02 on-box DONE with TWO
  complementary units (full DR `hermes-db-backup.sh` daily 20:35 UTC rotate-3 `d506cea`+`5f30d95`;
  non-derivable depth + research.db + em_cache `backup-db.sh` nightly 00:30 UTC `cc988c6`+`b04e4eb`;
  restore PROVEN both sides; **off-box residual**: `download-from-vps.bat` now also pulls
  `backups/db/` — run it periodically; a real off-box destination needs Ramana) · AUD-03 fixed
  (`cfcd1c7`) — **VERIFY the Sun Jul-05 09:00 UTC run succeeded** · AUD-04 Trust-page 4s still OPEN
  (owned by the Trust/premium-visuals lane — coverage_view/provenance collision warning stands).
- **Audit session (S77) tranche LIVE:** AUD-39 pytest harness + gate-0 · AUD-09 negative-PE=0 (D84) ·
  AUD-10 LOWVOL_MOM re-rank (D85; momentum_scan re-run triggered — VERIFY `ensemble_pctile`
  restated) · AUD-15 canon 252/151.2 (D86) · AUD-05 trust-ledger breadth (`d085395`).
- **⚠ Parallel-session discipline (this night proved it twice):** before working ANY item, check
  sibling WORKTREES (`.claude/worktrees/*`) and the VPS live files, not just git — the pledge-veto
  fix was already deployed-but-uncommitted by a sibling (adopt live > stomp); two lanes built
  DUPLICATE backup systems minutes apart (now de-duplicated by design — don't "clean up" the two
  units into one). Stage EXPLICIT paths only; for shared docs a sibling holds dirty, stage YOUR
  hunk only (`git diff` → filter → `git apply --cached -C0`).

## THE QUEUE — do these autonomously, in priority order
1. **VERIFY Sun Jul-05:** (a) `hermes-concall-capture` 09:00 UTC run succeeded (AUD-03 fix's first
   live test — check `/var/log/hermes-concall-capture.log`); (b) both backup timers fired clean
   Jul-03+ (`/var/log/hermes-backup.log`, `hermes-db-backup` journal; `backups/db/` inventory sane,
   disk <35%).
2. **RESULTS-SEASON WATCH (from ~Jul-09):** `/var/log/hermes-fundamentals-xbrl.log` runtime +
   gate-verdict quality — banks flow for the first time; expect `skipped_seen` dominant night 2+,
   `gate_deferred` >0 on heavy nights (budget 25, env `HERMES_XBRL_GATE_BUDGET`). Watch
   `hermes-shareholding-xbrl` + `hermes-sast-ingest` the same nights.
3. **AUDIT CORRECTION PROGRAM (work the doc's DAG in order, kickstart-pick-verify each):** check
   the audit session's wrap first — B3 remainder (12/64/65/06+07/11), B2 timer truth-capture, B4
   trust-text honesty, B5 fetch discipline, B6 linkage+UI, B7 db-core+perf **incl. AUD-04** (take it
   ONLY if the Trust lane hasn't; pull latest coverage_view/provenance first). B1 residuals needing
   RAMANA: off-box backup destination; optional /dash basic-auth. B1 residuals not needing him:
   fail2ban sshd jail, AUD-35 non-root service sandboxing.
4. **Stale-pledge CLASS SWEEP (S77b finding):** display/filter surfaces still read the frozen
   `fundamentals.promoter_pledge` — `pat/flows.py:260` ("clean: Pledge < 5%" SCREEN FILTER — same
   false-clean risk as the veto had), `pat/web.py` dossier facts (~761/1591/1835/1867),
   `dashboard.py:6186`. Reuse `concall_veto._shp_pledge()`/a shared SHP map; disclose source. The
   filter is the priority; the displays are P2.
5. **C consumption wave (needs backtest first):** fold C into scoring/screener/confluence only with
   a clean backtest, only for gate-passed symbols.
6. **XBRL Phase 3 (big, design first):** historical backfill (legacy API 2018+ / BSE deeper);
   replace Screener series symbol-by-symbol where reconciliation allows; then delete `screener.py`.

## GUARANTEED-DONE (do NOT redo — kickstart-pick-verify against these commits)
Pledge veto SHP primary (`07aca8d`, live+verified) · AUD-01 perimeter (`cc988c6`) · AUD-34 key-only
SSH (VPS state) · AUD-02 on-box backups BOTH units (`d506cea`+`5f30d95`+`cc988c6`+`b04e4eb`,
restore-tested, de-duplicated BY DESIGN) · AUD-39/09/10/15/05 tranche (`cef3e91`+`d085395`, live) ·
AUD-03 concall CLI (`cfcd1c7`) · AUD-23 (`911d020`) · AUD-24 (`16037b2`) · AUD-32 (`a24cf23`) ·
XBRL Phase 1/2/2c (`26cb3ef`/`5afe4ea`/`775badb`) · outage root-fix (`a4f1c21`+`d5b5933`) ·
kill-switch battery + #4 + dq_banner (`93f6abe`/`be7826a`+`ae73dab`+`3d8ae50`) · harness permissions
(`a2fdc99`). **Do NOT rebuild any backup unit, the shareholding module, the bank mapper, or
dq_banner — verify, then consume.** `docs/SESSION-72-CARRYFORWARD.md` (untracked) retire-ready —
its owner session deletes it.

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md`, then execute
> `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom (START with queue #1 Jul-05 verifications if
> it's Sunday or later, else queue #3 — the audit correction program, checking the audit session's
> wrap for what's already landed). Access is harness-enforced — never ask for access/write/delete or
> per-step confirmation. Get guidance from the agents, not from me; I won't answer. Keep every
> guardrail (esp. #8 primary-sources-only). Remember the perimeter: curl via the Caddy hostname or
> ssh-localhost, never raw :8000. Wrap up per the protocol and write the next carry-forward.
