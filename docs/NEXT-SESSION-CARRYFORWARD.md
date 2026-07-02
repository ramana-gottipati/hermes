# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`); **NEVER ask
Ramana for file/folder/tool access in any form — a permission prompt that still fires is a BUG to log
at wrap (CLAUDE.md #0-bis), never a cue to ask.** Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

## 🏛 AUDIT BOOT-CHECK (2026-07-02, binding until the P0s land)
A full institutional adversarial audit is on record at **`docs/AUDIT-2026-07-02-institutional-review.md`**
(117 AUD items, scorecard, its own fix prompt — the audit fix-session owns that queue). Before starting
ANY work, honour its in-flight guardrails:
1. **Never run `scripts/setup-news.sh` on the VPS** — it silently regresses the live hermes-concalls unit (AUD-28).
2. **Never `systemctl start` a hermes timer mid-day** — `Requires=` fires the job immediately into the DB (AUD-95).
3. `hermes-concall-capture.service` is live-broken — next run Sun **Jul-05** fails (AUD-03); the audit fix-session owns it.
4. AUD-01 security window: uvicorn will bind to 127.0.0.1 + `CHAT_SHARED_SECRET` — curl gates via
   localhost-on-VPS (ssh) or the Caddy hostname, never the raw `:8000` from outside.
Also: `src/automation/sast_events.py` is untracked and belongs to another lane — never stage it.

## STATE DIGEST (as of the Session-75 trio, 2026-07-02 — three parallel lanes all wrapped)
- **PRIMARY-SOURCE FUNDAMENTALS: Phases 1 + 2 + 2c LIVE (D78/D82).** `fundamentals_xbrl.py` nightly
  16:30 UTC, forward-only, source-tagged, per-symbol continuity gate. **Banks now map** (tag-detected
  via `InterestEarned` — listing flags are wrong; Screener bank conventions to the rupee; QUARTERLY
  only). Gate: RELIANCE/TCS/ICICIBANK/SBIN PASS · ITC FAIL (excise NOT mappable — no excise fact
  exists) · HDFCBANK FAIL (chronic MI-in-ExceptionalItems misfiling — refusal by design). LT needs NO
  mapper. `--regate`/`--selftest` CLIs exist. **Shareholding primary-source too** (`775badb`):
  `shareholding_xbrl.py` nightly 16:45 UTC — Promoters/FIIs/DIIs/Public + NEW `Promoter Pledge`
  metric. Evidence for everything: `docs/fundamentals-xbrl-migration.md` § Phase-2.
- **2026-07-02 outage root causes FIXED + VERIFIED (D82c):** ingest commits per filing + seen-table
  resume + throttle breaker (`a4f1c21`); `db._init` serves on existing schema + background DDL retry
  when a writer holds the lock (`d5b5933` — hermes-api restarted cleanly WHILE a backfill wrote).
- **Dataset A (insider) verified:** NO month gap 2025-11→2026-07; `--agg` sane (DMART pledge_risk).
  Tail: gg window ~Jun-09→27 resumes via transient timer `hermes-insider-backfill3` (throttle
  cooldown; resume is cheap — seen-table skips re-fetches).
- **Kill-switches:** market-freshness / regime / universe-drift / feed-liveness LIVE (`93f6abe`);
  **#4 restatement-spike LIVE + WARN/CRIT surfacing LIVE (`be7826a`+`ae73dab`+`3d8ae50`)** —
  `fundamentals_restatements` ledger (journaled at write time; INSERT-OR-REPLACE erases history) +
  `chk_restatement_spike` (>5%/30d warn, INFO-warmup <20 gate-passed) + NEW `src/web/dq_banner.py`
  strips (workspace-keyed, sys.modules-swept to reach view modules — verified live on rotation/rrg/
  rsband/participants/capture-map/stocks/mep). **#1 WML-drawdown + #3 live-IC decay DEFERRED with
  dated evidence:** momentum_scan had 2 snapshots on Jul-02 → #1 re-check ~end-Jul-2026 (needs ~21
  daily), #3 ~2027-Q1 (needs 3-mo rolling 6-mo IC). Both recorded in `docs/validation-memo.md` §5.
- **⚠ Parallel-session discipline:** heavily co-worked tree — stage EXPLICIT paths only, never
  `git add -A`; patch-over (never full-scp) the D80 hot files (`dashboard`/`v2_surfaces`/
  `lens_registry`/`cockpit`); kickstart-pick-verify EVERY queue item before working it (this session:
  2 of 5 queue items were already done/in-flight by siblings).

## THE QUEUE — do these autonomously, in priority order
1. ~~Confirm the insider gg tail~~ **DONE** — backfill3 completed CLEAN (`aborted_throttled: False`,
   saved 1,037, resume skipped 224); June = 1,559 events, no month gap 2025-11→2026-07.
2. ~~Capture sector-momentum/early-signals nav wiring~~ **DONE (`a24cf23`, AUD-32)** — mounts +
   lenses in git, nav gate PASS (89 routes, 0 orphans).
3. ~~**Wire `fundamentals_asof.promoter_pledge`**~~ **DONE (`261daef`)** — wired to the SHP
   `Promoter Pledge` metric (PIT via report_date). Residual: verify the consumers (scoring veto /
   C-score / A-B boards) actually surface the now-real values honestly.
4. **AUDIT CORRECTION PROGRAM (`docs/AUDIT-2026-07-02-institutional-review.md`, AUD-01..117 in
   priority order).** Already fixed from it — do NOT redo: AUD-03 concall-capture CLI (`cfcd1c7`,
   Jul-05 run will now succeed — VERIFY it did) · AUD-23 fundamentals_xbrl seen-table/breaker/gate-
   budget (`911d020`) · AUD-24 credit_ratings + capital_allocation bounded txns + full class sweep
   NEGATIVE for further members (`16037b2`) · AUD-32 nav capture (`a24cf23`). Next by priority:
   the remaining P0s — HTTP perimeter, DB backup/restore, Trust-page 4s (AUD-04).
5. **RESULTS-SEASON WATCH (from ~Jul-09, first heavy nights):** check
   `/var/log/hermes-fundamentals-xbrl.log` for runtime + gate-verdict quality — banks flow for the
   first time; expect `skipped_seen` to dominate night 2+, `gate_deferred` >0 on heavy nights
   (budget 25/run, env `HERMES_XBRL_GATE_BUDGET`). If a mapper improvement lands, re-arbitrate with
   `--regate --symbols ...`. Watch `hermes-shareholding-xbrl` + `hermes-sast-ingest` the same nights.
6. ~~**Kill-switch completion**~~ **DONE (`be7826a`+`ae73dab`+`3d8ae50`)** — #4 restatement-spike
   ledger + check LIVE; WARN/CRIT strips (`dq_banner.py`) VERIFIED LIVE on all data surfaces. #1
   WML-drawdown + #3 live-IC decay DEFERRED with dated re-check windows (end-Jul-2026 / ~2027-Q1 —
   `validation-memo.md` §5). **Only revisit #1 after ~end-Jul** when momentum_scan has ~21 snapshots.
7. ~~SAST Reg 29 + Reg 31~~ **DONE (`eee45f1`)** — `sast_events.py` + nightly 15:55 UTC timer;
   backfilled 2025-11→now; NRBBEARING roll-up validated.
8. **C consumption wave (needs backtest first):** fold C into `scoring.py` / a screener column / the
   confluence board — only with a clean backtest, only for gate-passed symbols.
9. **XBRL Phase 3 (big, design first):** historical backfill from the legacy API (2018+ per symbol) +
   BSE where deeper; replace Screener series symbol-by-symbol where reconciliation allows (this is
   where ITC-excise, HDFCBANK, bank annuals, and the frozen history land); then delete `screener.py`.

## GUARANTEED-DONE (do NOT redo — kickstart-pick-verify against these commits)
XBRL Phase 1 + timers (`26cb3ef`) · **Phase 2 bank mapper + definitional verdicts + --regate
(`5afe4ea`)** · **Phase 2c shareholding + Promoter Pledge (`775badb`)** · outage root-fix pair
(`a4f1c21` + `d5b5933`) · insider legacy Mar–Apr archive (2,449 rows) + month-gap/--agg verification ·
momentum-scan freshness (`76c1c98`) · kill-switch battery partial (`93f6abe`) · git↔VPS reconcile +
nested-nav in git (`136f9af`) · harness-level permissions (`a2fdc99`, D83) · S72 explainability
deploys + `/dash/stocks` table controls · Tier-1 visual flagships (credibility / cycle-clock /
capture-map) · promoter_pledge wired (`261daef`) · **kill-switch #4 restatement-spike + WARN/CRIT
surfacing (`be7826a`+`ae73dab`+`3d8ae50`)** · **AUDIT reference doc captured into git (`76484be`)** ·
colour 4c categorical remainder = closed-by-decision (S65 `19aed0b`, do not reopen). **Do NOT
rebuild the shareholding module, the bank mapper, or `dq_banner`/`fundamentals_restatements` —
verify, then consume.** `docs/SESSION-72-CARRYFORWARD.md` (untracked) is fully executed →
retire-ready (its owner session deletes it).

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md`, then execute
> `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom (start with the promoter_pledge consumer
> verification, then the audit correction program's remaining P0s). Access is harness-enforced —
> never ask for access/write/delete or per-step confirmation. Get guidance from the agents, not
> from me; I won't answer. Keep every guardrail (esp. #8 primary-sources-only). Wrap up per the
> protocol and write the next carry-forward.
