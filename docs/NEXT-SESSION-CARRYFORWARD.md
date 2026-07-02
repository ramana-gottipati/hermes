# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0). Keep guardrails (esp. #8 primary-sources).
Do NOT burn the context window re-reading history — this file + the top PROJECT_STATE entry is enough.**

## STATE DIGEST (as of Session 71, 2026-07-02)
- **Data intelligence layer LIVE + validated on VPS:** C capital-allocation, A insider/promoter/pledge
  (NSE corporates-pit), B credit ratings (NSE credit-rating). Confluence proven.
- **Momentum settled by attribution:** it is **beta, not selection alpha** (RISKADJ residual α t=1.99).
  Fundable only as a ₹50–100cr defensive tilt. → **sell the DATA, not signals** (`docs/institutional-panel-assessment.md`).
- **Risk-adjusted momentum SCANNER LIVE:** `/dash/momentum-scan` (RISKADJ + ensemble + A/B/C veto,
  nightly `hermes-momentum-scan.timer`). Built from primary-source prices.
- **Policies now in the rulebook:** Guardrail #0 (full-folder autonomy), #8 (primary-sources-only).

## THE QUEUE — do these autonomously, in priority order
1. **PRIMARY-SOURCE FUNDAMENTALS MIGRATION (Guardrail #8 — highest).** `screener.py` →
   `fundamentals`/`fundamentals_history` (powers C capital-allocation + patearn) is the one
   Screener.in dependency. Migrate to **BSE/NSE XBRL financial-results filings** (foundation:
   `fundamentals_filing_dates.py` BSE dates, `provenance.py`, the `concall_bse.py` BSE-fetch pattern).
   *Interim already shipped:* the `/dash/momentum-scan` C column is flagged "Screener → migrating".
   **Both of Ramana's options are handled: (1) flagged now [DONE]; (2) strip/replace C once XBRL lands.**
   Consult the risk-governance + data-product agents on the XBRL schema + PIT before building.
2. **DATA FRESHNESS.** The embase cache / bhavcopy is stale (scanner as-of **2026-06-19**). Get the EOD
   pipeline current so the scanner + signals reflect today. (Check `hermes-bhavcopy.timer` + the cache
   build; fix whatever stopped updating.)
3. **VALIDATION MEMO + monitoring (panel gap #6).** Independent replication of the factor Sharpes; a
   written SR-11-7-style validation memo (lineage, PIT method, the anchor-audit + survivorship findings,
   limits); kill-switches (momentum-crash guard, β>1.3 cap, sector>25%, live-IC decay, data-freshness,
   restatement-spike, universe-drift).
4. **NIGHTLY TIMERS for C/A/B backfills.** Only `hermes-momentum-scan.timer` exists; A (`insider_events
   --ingest`), B (`credit_ratings --ingest`), C (`capital_allocation --backfill`) still run manually.
5. **A/B ENHANCEMENTS.** SAST Reg 29 (`corporate-sast-reg29`) + Reg 31 pledge-magnitude feed
   (`corporate-pledgedata-sast3132`) — pledge % that PIT lacks (Codex resp-14/15).
6. **Consumption wave (optional, needs backtest first):** fold C into `scoring.py` / a screener column /
   the confluence board — only after the XBRL migration + a clean backtest.

## GUARANTEED-DONE (do NOT redo)
Panel (4 reviews) · attribution (`attribution.py`, momentum=beta) · anchor-audit (leak disproven) ·
cost_participation (₹50-100cr fundable) · MVIO proof points (`docs/mvio-dataset-a.md`) · the scanner +
its nightly timer · Guardrails #0 and #8. Verify via `git log` before touching any of these.

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md`, then execute
> `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom (start with the primary-source fundamentals
> migration + data freshness). Full-folder access is granted — don't ask for access/write/delete or
> per-step confirmation. Get guidance from the agents, not from me; I won't answer. Keep every guardrail
> (esp. #8 primary-sources-only). Wrap up per the protocol and write the next carry-forward.
