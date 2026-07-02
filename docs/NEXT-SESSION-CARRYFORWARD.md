# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0). Keep guardrails (esp. #8 primary-sources).
Do NOT burn the context window re-reading history — this file + the top PROJECT_STATE entry is enough.**

## STATE DIGEST (as of Session 73, 2026-07-02)
- **PRIMARY-SOURCE FUNDAMENTALS LIVE (Guardrail #8 remediated, Phase 1):** `fundamentals_xbrl.py`
  ingests NSE-XBRL results nightly (16:30 UTC timer), forward-only, source-tagged, real broadcast
  as knowable_at, **per-symbol series-continuity gate** (`fundamentals_xbrl_gate`; RELIANCE/TCS
  pass, ITC fails on excise definition — by design). Design + evidence:
  `docs/fundamentals-xbrl-migration.md` + decision D78. Screener history frozen, never overwritten.
- **C/A/B nightly timers deployed + smoke-tested** (D79): insider 15:30 / ratings 15:45 (63 events
  first run) / xbrl 16:30 / capital-allocation 17:15 UTC.
- **Freshness fixed:** the momentum scan self-heals its `em_cache.pkl` (was pinned at 06-19; now
  current). EOD bhavcopy pipeline was never broken.
- **Validation memo written** (`docs/validation-memo.md`): SR-11-7 style, limits, kill-switch
  definitions. Enforcement wiring of switches #1/#3/#4/#5 into the data-quality timer still open.
- **⚠ Parallel-session note:** another session works `src/web/*` (glossary/explainability lane) in
  this shared tree — never `git add -A`, stage explicit paths only.

## THE QUEUE — do these autonomously, in priority order
1. **VERIFY dataset-A backfill completion** (rebuild itself DONE session 73, `b136d3f` — do NOT
   redo). Check `/var/log/hermes-insider-backfill.log` ends clean (gg run May→Jun + chained
   `--legacy 2026-03-01 2026-04-30`), `SELECT substr(disclosure_dt,1,7), COUNT(*) FROM
   insider_events GROUP BY 1` has no month gap 2025-11→now, and `--agg` sanity on a pledge-heavy
   symbol. Then the nightly timer keeps it current (it already routes to the new endpoint).
2. **XBRL Phase 2 — widen the migrated cohort.** (a) Definitional mappers for gate-failing
   symbols (excise-gross Sales, NCI netting, other-operating-income OP); (b) bank/NBFC taxonomy
   mapper (currently skipped loudly); (c) shareholding-pattern filings (promoter/FII/DII/pledge —
   separate NSE filing class) to replace the Screener shareholding series. Watch the first
   results-season nights (from ~Jul-09): gate-evidence fetches make early runs heavy — check
   `/var/log/hermes-fundamentals-xbrl.log` for runtime + gate verdict quality.
3. **Kill-switch enforcement wiring** (validation memo §5): momentum-crash guard, live-IC decay,
   restatement-spike, universe-drift → nightly `hermes-data-quality` (or a small new module);
   surface breaches on the affected pages (data-first: show, don't hide).
4. **A/B ENHANCEMENTS:** SAST Reg 29 (`corporate-sast-reg29`) + Reg 31 pledge-magnitude
   (`corporate-pledgedata-sast3132`) — pledge % that PIT lacks (Codex resp-14/15).
5. **C consumption wave (needs backtest first):** fold C into `scoring.py` / a screener column /
   the confluence board — only with a clean backtest, and only for gate-passed symbols.

## GUARANTEED-DONE (do NOT redo — kickstart-pick-verify against these commits)
XBRL migration Phase 1 + timers + validation memo (`26cb3ef`) · momentum-scan freshness (`76c1c98`)
· panel + attribution + anchor-audit + cost (Session 71) · scanner + its timer · Guardrails #0/#8 ·
glossary/nav-audit lane (Session 72, parallel session — don't touch `src/web` explainability files).

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md`, then execute
> `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom (start with the dataset-A rebuild against
> corporates-pit-gg, then XBRL Phase 2). Full-folder access is granted — don't ask for
> access/write/delete or per-step confirmation. Get guidance from the agents, not from me; I won't
> answer. Keep every guardrail (esp. #8 primary-sources-only). Wrap up per the protocol and write
> the next carry-forward.
