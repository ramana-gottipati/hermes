# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`). Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

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
  #1 WML-drawdown + #3 live-IC decay wait on accumulated momentum_scan history; #4 restatement-spike
  + WARN/CRIT page surfacing still open.
- **⚠ Parallel-session discipline:** heavily co-worked tree — stage EXPLICIT paths only, never
  `git add -A`; patch-over (never full-scp) the D80 hot files (`dashboard`/`v2_surfaces`/
  `lens_registry`/`cockpit`); kickstart-pick-verify EVERY queue item before working it (this session:
  2 of 5 queue items were already done/in-flight by siblings).

## THE QUEUE — do these autonomously, in priority order
1. **Confirm the insider gg tail landed:** `journalctl -u hermes-insider-backfill3` (or `-backfill4`+)
   ends without `aborted_throttled` and June count grows past 699
   (`SELECT substr(disclosure_dt,1,7),COUNT(*) FROM insider_events GROUP BY 1`). If throttled again:
   re-run the same window after a ≥45-min cooldown (`systemd-run --unit=... --working-directory=
   /opt/hermes /opt/hermes/.venv/bin/python -m src.automation.insider_events --ingest 2026-05-01
   2026-06-27`) — resume skips everything already seen.
2. **Wire `fundamentals_asof.promoter_pledge`** (currently hard-None) to the new `Promoter Pledge`
   metric (`source=NSE-XBRL-SHP`, PIT via report_date) so the C-score / patearn vetoes see real
   pledge levels. Small, high-value, fully evidenced in `docs/fundamentals-xbrl-migration.md`.
3. **RESULTS-SEASON WATCH (from ~Jul-09, first heavy nights):** check
   `/var/log/hermes-fundamentals-xbrl.log` for runtime + gate-verdict quality — banks flow for the
   first time; gate-evidence fetches make early runs heavy. If a mapper improvement lands, re-arbitrate
   affected symbols with `--regate --symbols ...`. Watch `hermes-shareholding-xbrl` the same nights.
4. **Kill-switch completion** (queue unchanged): #4 restatement-spike (add a revision counter to the
   XBRL ingest — `revised` flags already parsed), #1 WML-drawdown + #3 live-IC decay (check whether
   enough momentum_scan history has accumulated yet; else defer again), and surface WARN/CRIT states
   on affected pages (data-first: show, don't hide).
5. **A/B ENHANCEMENTS:** SAST Reg 29 (`corporate-sast-reg29`) + Reg 31 pledge-magnitude
   (`corporate-pledgedata-sast3132`) — per-EVENT pledge magnitude (the SHP `Promoter Pledge` gives the
   quarterly STOCK; Reg 31 gives the FLOW between quarters). Codex resp-14/15.
6. **C consumption wave (needs backtest first):** fold C into `scoring.py` / a screener column / the
   confluence board — only with a clean backtest, only for gate-passed symbols.
7. **XBRL Phase 3 (big, design first):** historical backfill from the legacy API (2018+ per symbol) +
   BSE where deeper; replace Screener series symbol-by-symbol where reconciliation allows (this is
   where ITC-excise, HDFCBANK, bank annuals, and the frozen history land); then delete `screener.py`.

## GUARANTEED-DONE (do NOT redo — kickstart-pick-verify against these commits)
XBRL Phase 1 + timers (`26cb3ef`) · **Phase 2 bank mapper + definitional verdicts + --regate
(`5afe4ea`)** · **Phase 2c shareholding + Promoter Pledge (`775badb`)** · outage root-fix pair
(`a4f1c21` + `d5b5933`) · insider legacy Mar–Apr archive (2,449 rows) + month-gap/--agg verification ·
momentum-scan freshness (`76c1c98`) · kill-switch battery partial (`93f6abe`) · git↔VPS reconcile +
nested-nav in git (`136f9af`) · harness-level permissions (`a2fdc99`, D83) · S72 explainability
deploys + `/dash/stocks` table controls · Tier-1 visual flagships (credibility / cycle-clock /
capture-map). **Do NOT rebuild the shareholding module or the bank mapper — verify, then consume.**

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md`, then execute
> `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom (start with the insider-tail confirmation, then
> wire promoter_pledge into fundamentals_asof). Full-folder access is granted — don't ask for
> access/write/delete or per-step confirmation. Get guidance from the agents, not from me; I won't
> answer. Keep every guardrail (esp. #8 primary-sources-only). Wrap up per the protocol and write
> the next carry-forward.
