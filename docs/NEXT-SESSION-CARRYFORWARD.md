# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`); **NEVER ask
Ramana for file/folder/tool access in any form — a permission prompt that still fires is a BUG to log
at wrap (CLAUDE.md #0-bis), never a cue to ask.** Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

## 🚌 S101 WRAP (2026-07-10, bus lane) — signal-event bus PRODUCER WIRED + SEEDED: bhavcopy-chain step 60 (D105, `6733dda` live) — the S96b "0 rows / no producer" finding is CLOSED
- **What landed:** `--detect` = drop-in step 60 of the hermes-bhavcopy chain
  (`hermes-bhavcopy.service.d/60-signal-events.conf`, git-owned mirror + `--install`, drift
  gate CLEAN, merged chain 16 ExecStart steps) — sequenced AFTER the very steps that write
  mep/rsband/fno_oi; **no new timer, nothing enabled/started (zero AUD-95 surface)**. Producer
  fixes: the cci lens was SILENTLY DEAD (ordered `credibility_series` by a nonexistent
  `as_of` col; defensive except ate the error) — now period-ordered with `as_of` =
  `date(computed_at)` (knowable-day, D104's doctrine applied bus-side); NEW rs lens
  (index-grain `rs_band_state` flips vs Nifty 500) + deal lens (`deal_print` per symbol/day,
  magnitude = within-day value pctile); collect-then-commit per lens (write-lock outage class).
  Tests: `tests/test_signal_events.py` 8 hermetic (incl. the dead-loop regression); PIT suite
  untouched-green. Readers/schema UNTOUCHED per the chip.
- **Seeded live 12:51 UTC: 1,188 events in 1.0s** — mep 288 · cci 654 · oi 213 · deal 33 ·
  rs 0 (SQL-verified honest zero: no band flips Jul-08→09). `attention_queue` serves 6 real
  events; `R.attention()` PIT replay reaches the Jul-01 cci batch. /v1 HTTP walk still blocked
  BY DESIGN (`v1_api_keys` 0 rows — the P-05 provisioning gap, unchanged).
- **🔭 VERIFY TONIGHT (added to the S98 battery):** the 14:04 UTC bhavcopy chain now runs
  step 60 — journal `hermes-bhavcopy` must show the `run_detection` summary line after the
  chain (~15:00-15:45 UTC); `--stats` latest_as_of flips to 2026-07-10. Idempotent over the
  seed; a step-60 crash fails the chain unit → pager (that's by design, fix upstream).
- **Still not built (PROJECT_STATE §What's-NOT-built):** dvpt/quality/cpr lenses (no banded
  state / undesigned) · a home-surface face (`/v1/attention` is the ONLY live reader — the
  chip's "home Attention Queue" does not exist in code; natural next product pick) ·
  stock-grain rs.

## 🆕 S100 WRAP (2026-07-10, audit lane) — D104: the /v1 PIT knowable clock upgraded to REAL event dates (AUD-38 refined; `0874e9a` live)
- **On the wire now:** `credibility?as_of=` serves the EVENT tier — `knowable_from =
  max(concall_dt, transcript_publish_dt)` per period (16,208 concalls carry a real clock;
  `result_filing_dt` refused — filings precede calls = the leak direction) with S96b's
  month-end rule kept verbatim as the MODELED fallback. Rows stamp `knowable_basis`;
  `pit.knowable_rule` names the applied rule; `/universe` as_of strictly validated (422).
  Walked live: ICICIPRULI as_of 2019-01-25 → "Feb 2019" point knowable 2019-01-22 EVENT
  (34 days earlier than month-end permitted); the 2025-06-30 boundary serve unchanged.
  +5 golden tests (`tests/test_v1_pit.py` §5; 33 pass), on-box selftest green, public
  OpenAPI carries the two-tier contract. Semantics: PROJECT_STATE **D104**.
- **Multi-lane collision resolved by ADOPT-THEN-REFINE (reusable recipe):** this lane built
  AUD-38 independently; the pre-deploy fork-check caught S96b's implementation ALREADY
  DEPLOYED-uncommitted, its session mid-flight. Response: reset the divergent branch (kept at
  `backup/s99-divergent-aud38`), import the live bytes, WAIT for its commit (`56c731a`),
  re-diff the delta against the LANDED commit — its deployed files were OLDER than its final
  commit (selftest polished in between), so a straight live-import diff would have silently
  REVERTED that polish — then land the refinement only. Standing rule hardened: **fork-check
  the VPS live files for EVERY pick** (not just the nav files) before building.
- ~~⚠ Number-collision watch~~ **✅ RESOLVED same day:** the signal_events producer lane
  renumbered to **S101** as prescribed, ff-merged onto this wrap and landed (`6733dda`, D105 —
  see the 🚌 S101 block above). "signal_events has 0 rows / no producer" is now OBSOLETE.

## 🏁 S97 WRAP (2026-07-10, main session — Ramana-steered) — chart batch + D95 residue BOTH closed; nothing of mine open
Three arcs, all shipped + live-verified + state-doc'd; **do NOT redo any of them**:
1. **S86c chart batch (D96 + drawings v2, `9d04bd9`+`d83c50f`):** Wolfe walk freshness guarantee
   (TCS wedge 2/53) · drawings direct-edit + dblclick editor · fib catalog w/ 4.236 + named
   levels · future whitespace projection · conflux bands @2%. Known nits (deliberate, build
   on ask): whitespace anchors degrade across interval switch; no whole-body drag.
2. **S94 (`2562ca7`+`025f514`):** the S89b failed 92-symbol heal RERUN — driver fixed
   (`_partial_key` arg order · CPR tf set is D/W/M/H not Q) + the REPO bug (`value` column
   missing from `_backfill_triggers_for_symbol`'s SELECT). 92/92, 0 failures, 7.1 min.
3. **S97/D103 (`5d252f9`+`72c4ce4`+`eb706c6`):** TAPE_SUSPECT 77→6 (in-row compounds ·
   band-lock gate · deb/pref exclusion; 6 remain honestly fenced) + the **70-symbol four-leg
   consequence heal (0 failures, 10.5 min, `/tmp/heal_tape.py` + `/tmp/heal_tape.done`)**.
   ⚠ OVERLAP NOTE: the S98 lane independently healed 27 of these same symbols minutes apart
   (it read S97's "counts AMENDED when the run lands" as un-run — kickstart-verify lesson,
   inverted). Harmless (idempotent recomputes, identical outputs) — but the heal is now
   DOUBLE-covered: any future session must treat D103's consequence heal as **DONE**.
Watches inherited by whoever runs next (also armed as in-session crons here): the timer
fleet below (S96 wrap list) esp. **wolfe-scan 16:04 UTC dual/triple snapshot** + tonight's
`chk_action_tape_agreement` battery, which should go QUIETER (suspects 77→6; louder = page).
D95 residue after all this: **wolfe tape-wiring (Wolfe lane owns)** · stock_rs history
(heals forward by design; a backfill path is buildable if Ramana wants it) — nothing else.

## 🥇 S98 WRAP (2026-07-10) — S97's promised heal LANDED: 28 in-row-compound symbols · reconcile 77→6
**✅ D103 residue closed (S98):** the S97 wrap promised "the four-leg heal of every factor-
changed symbol: counts AMENDED below when the run lands." This session ran it. Diagnosis
(`/tmp/s98_survey.py`): `_group_price_legs` returns >1 leg on **28 distinct single-row
filings** — for each, pre-S97 parser saw only the first leg, so the stored adjusted-close
history was scaled by the wrong factor. Impact scale (from `/tmp/s98_check_factors.py`):
ONGC 2011-02-08 fixed 0.25 vs naive 1.0 · TITAN 2011-06-23 fixed 0.05 vs 1.0 · TECHM
2015-03-19 fixed 0.25 vs 1.0 · BAJFINANCE 2016-09-08 fixed 0.10 vs 1.0 · HINDZINC · MMTC ·
VAKRANGEE — marquee nifty500 in the set. **Heal driver `/tmp/s98_heal.py`** (VPS scratch,
S94 `heal92b.py` pattern; per-symbol commits, resume-safe `/tmp/s98_heal.done`): 4-leg walk
per symbol — cpr D/W/M/H (`process_symbol`) + triggers + mep + keyprice; each reads a fresh
`_action_events` so post-S97 legs propagate through. **27/27 OK, 0 failures, ~5.7 min wall
time** (per-sym 2.3–41.6s). Anchor CPR unchanged (2026-07-09 ONGC pivot 245.61 sane); the
pre-2011 history is now on the correct base (ONGC 2011-02-07 pivot 174.08 → 181.71).
**Reconcile amendment: 77 → 6 TAPE_SUSPECT** (S85e baseline 77 · S97 parser+gate 11 ·
`72c4ce4` second-pass + this heal → 6). Post-heal detail: `{NO_RATIO_CAUGHT:128,
CAUGHT_FALLBACK:947, NO_BHAV:144, TAPE_SUSPECT:6, MISSED_DEAD_ZONE:118, NO_RATIO_UNCAUGHT:10,
NEGLIGIBLE:1}` over 1,354 groups. Residual 6 are genuinely-fenced parse-quirks (no
recoverable ratio) — descriptive-only, no further action. Selftests: adjust 7/7 ·
corp_actions 17/17 (all S96+S97 checks). Dossier `/dash/stock?symbol=ONGC|TECHM` both 200.
Session ships only PROJECT_STATE + this carry-forward (no `src/`/`scripts/`); state-doc
gate silent. **No S98 open loop remains.**
**Verifies still due this session-end (armed timers, first fires TODAY/tomorrow — treat as
active watches):**
· **hermes-slb.timer** 15:16 UTC Jul-10 (armed 09:20; drift-clean; next journal must show
  Finished + `/var/log/hermes-slb.log` one clean line + rows for 2026-07-10 in
  `slb_volumes`+`slb_open_positions`)
· **hermes-wolfe-scan.timer** 16:04 UTC Jul-10 (D101/D102 first scheduled run under the
  three-snapshot code — journal must show `persisted N winner-profile setups + M
  structure-watch rows + K approaching-5 rows`; runtime ~9-15 min)
· **hermes-results-reactions.timer** 18:01 UTC Jul-10 (first evening after TCS reported —
  MTTR box on `/dash/results-reactions` + evidence-pack should show fresh `first_seen`)
· **hermes-board-health.timer** 22:01 UTC Jul-10 (silent = green; a page = a hollow
  strategy card — fix upstream, never mute the pager)
· **hermes-season-digest.timer** Sat Jul-11 02:45 UTC (**first DM ever**; missing = real
  bug per S96 note — page it, do NOT `systemctl start` mid-day per AUD-95)
· **hermes-fundamentals-provenance.timer** Sat Jul-11 21:00 UTC (S84 4h ceiling — journal
  Finished + 2767/2767; a scheduled task tracks it separately)

## 🥈 S96+S96b WRAP (2026-07-10, season lane) — P-04 SHIPPED + AUD-38 CLOSED (P-05 unblocked)
**✅ AUD-38 SHIPPED (S96b, same session):** /v1 is PIT-queryable — `credibility?as_of=` (month-end
knowable rule via `cci_series.series_asof`, `knowable_from` stamped, typed absence for a
PIT-empty past) + `attention?as_of=` (last-batch-≤-date resolver; honest-empty before the feed) +
the PIT contract in OpenAPI + RFC-7807 422 on malformed dates. Tests `tests/test_v1_pit.py`
(10, incl. leap-Feb boundary) + selftest 5b; live-walked on ICICIPRULI (97-pt series, exact
boundary serve). Two bonus fixes: lowercase symbols no longer bypass rename resolution
(normalize-before-canonical) and the v1 selftest's stale `lag_days==90` now asserts the
INVARIANT (calibrated lag: VPS serves 114, laptop default 120 — never pin cross-box constants).
Findings: ~~`signal_events` = 0 rows in prod (bus has no producer)~~ **✅ CLOSED S101
(`6733dda`, D105): producer wired + seeded 1,188 events — see the 🚌 S101 block**; 5 live /v1+automation
files were CRLF (content==HEAD; now LF). **P-05 is UNBLOCKED** — needs an API key provisioned
on the box (`HERMES_V1_DEV_KEY` unset) for live-key demos. **REFINED S100 (D104, `0874e9a`):**
the knowable clock is now two-tier — the REAL concall/transcript event date when captured
(basis EVENT; month-end stays as the MODELED fallback); `knowable_basis` + `pit.knowable_rule`
ride the wire; `/universe` as_of strictly validated.
**✅ P-04 evidence pack LIVE (S96): `/dash/evidence-pack`** — print-CSS procurement assembly
(browser print→PDF, zero deps): 8 P-03 sheets IMPORTED verbatim + coverage boundary
(glance/matrix/COPY_*) + live season MTTR/placebo + replay pointer (no returns quoted). Trust
lens + coverage front-door chip + spec-sheets cross-link; nav/chrome gates PASS; walked live
(warm 49ms; first daily hit ~3.3s = cold coverage_snapshot, expected). Deploy note that saved
the session: v2_surfaces + lens_registry live≠HEAD is a COMMENT/ORDER fork only — pull live,
patch, push back; never full-file scp from git. **No P-04 work remains** — next product rank
is P-05 replay-any-date API (~~needs AUD-38 first~~ **AUD-38 DONE S96b** — P-05 is buildable now).
**ARMED, self-executing — verify DMs, never rebuild** (gates hashed, `prereg --verify` = tamper
check; results → `research/explosive_moves/out/*.json`; each completed run needs a LEDGER entry +
spec-sheet): season digest daily 02:45 — **first DM ever fires Sat Jul-11 02:45 UTC** (timer
armed 03:20 Jul-10, 35 min after the slot; `Persistent=no` by design — a missing Sat DM = real
bug, page it) · **E-02 monthly 22nd (first Jul-22**; true events 19/300 — years out) · **E-14
monthly 25th (first Jul-25 — GO may be its FIRST fire** once the ~Jul-21 flood + S85d calibration
date the 28 SHP quarters; baseline 94/1,000) · E-04 monthly 1st (4/8 cohorts, GO ≈ mid-2027).
**Season watches (S96-checked, all dated):** 18:00 UTC snapshots mint the first real MTTR
numbers as reporters confirm (0 fresh as of Jul-10 09:30; TCS Jul-09 needs today's bhav —
check `reaction_mttr` first_seen > seed cutoff, then the spec-sheets/evidence-pack MTTR box) ·
Sat Jul-11 21:00 provenance run must FINISH under the 4h ceiling (S84 raised TimeoutStartSec;
expect journal Finished + 2767/2767) · `gate_deferred` 0 all week so far, `if_filings` ramping
(7 on Jul-09) — re-check as banks report Jul-18 · ~Jul-21 pledge coverage (was 76 syms).
**Guaranteed-done (kickstart-pick-verify, never redo):** T-2 `fd2528b` · wk1 `e60eba0`/`e61ba4a`
(X-02 closed-by-evidence, N3 ticket, D-02/03 feed) · wk2 `8f0df2c` (P-03 spec-sheets,
evlib+placebo, testing-page truth, #8 disclosure, charter v1.1/D92) · wks3-4 `9ae0345` (3
placebo-caught NULLS + CAR fan) · `1ed0316` (E-11/E-12 nulls, M-04) · triggers `0fba51c`/
`3ff1ee2`/`7614603` · digest `3a1c953` · E-10 calc `60fcdd8`+`5805e6f` · **P-04 pack (S96,
`21547b3`)** — the S93b lesson stands: grep HEAD for the other lane's newest anchors before
committing co-hot files. Ledger: 10 pre-registered studies (2 confirmed · 6 nulls · 2 armed).

## 🧰 S86d HARNESS NOTE (2026-07-10) — session infrastructure changed, applies to YOUR session
- `.claude/settings.local.json` now carries three additive keys: `disableClaudeAiConnectors` (claude.ai
  connector fleet no longer loads in Hermes sessions), a PreToolUse **state-doc gate v1.3, restart-verified**
  (`scripts/state-doc-gate.cjs` — BLOCKS any `git commit` carrying `src/`/`scripts/` changes without
  PROJECT_STATE.md; judges what the commit ACTUALLY carries — pathspec `--only`/`-- <paths>` commits,
  compound `git add … && git commit`, and an unmodified state-doc named in the add all handled; deliberate
  exception: `state:skip` in the command; fail-open on errors), and 118 `skillOverrides` hiding the
  never-used cowork skill fleet (anthropic-skills/engineering/pdf-viewer/core skills all KEPT). Hooks
  HOT-RELOAD on settings change (matchers must be EXACT tool names — regex forms never register on this
  runtime). If the gate misfires, that's a wrap-report bug (#0-bis) — report it; the S95 report was fixed
  same-day as v1.3.
- 6 new user-level skills exist (failure-ledger · walk-the-journey · deploy-reality ·
  multi-session-safety · transient-doc-lifecycle · explain-visual) — invoke them at their trigger
  points; MEMORY.md index is now slim one-liners (detail lives in the body files — extend bodies, never
  re-fatten index lines). Full inventory: memory `claude-harness-optimization`.

## 📋 OPEN-ITEMS ASSESSMENT 2026-07-10 (dedicated triage lane — sources swept: PROJECT_STATE §Open, AUDIT doc, charter §3/§4/§5/§7, memory bodies, TRANSIENT docs)

**Method:** grep-first over every open marker; kickstart-pick-verify each candidate (git log -S, file existence, mount check). Class tally across ~90 candidates:
- **VERIFIED-OPEN 47** (mostly P1/P2 AUD hygiene; 2 in-flight this session)
- **PARTIAL 5** (AUD-02/26/29/30/34/35 — on-box/perimeter/sandbox landed, one residual each)
- **BLOCKED 7** (external gate or Ramana input required)
- **DATED-WATCH 11** (armed timers/studies + season signals)
- **STALE MARKERS FIXED 2** (this session; docs-only)

~~⚠ IN FLIGHT (AUD-38 lane)~~ **✅ LANDED (S96b, same day):** the fenced files committed clean —
AUD-38 only (the selftest edit was a stale-expectation fix, NOT AUD-37; metering stays open).

**VERIFIED-OPEN — highest priority (P1, ranked):**
1. **AUD-06** DVPT zones / D44 key-price / hot-day averages computed on RAW closes (`signals.py:456,357-379,402-404,487-509,637-675`). Live signals wrong-scale through any split window; also swallows PROJECT_STATE B5 residual.
2. **AUD-07** backfill vs nightly hot-day definition disagree (`signals.py:899-908` vs `:644,657-663`). Do WITH AUD-06 (same backfill re-run).
3. **AUD-11** corp-action fallback rescales entire history on >30% real crashes (F&O names). Blockers doc reformulates: widen callers' SELECT + volume corroboration.
4. **AUD-14** throttle→"holiday" class sweep — 5 fetchers still carry the bug (`RetryableFetchError` lives only in `fno_oi.py`).
5. **AUD-22** research replication stack bypasses PIT layer (leaky report_date joins). Fix = route through `fundamentals_asof.py` with PYTHONPATH note.
6. **AUD-25** feed-liveness monitoring covers 4 of 12 feeds; regime guard reads undated rows.
7. **AUD-28** `setup-news.sh` heredoc regresses live CCI unit (do WITH AUD-27 remainder — replace heredocs with committed unit files).
8. **AUD-37** /v1 metering under-records (500s unlogged, bytes_out=0) — still OPEN.
   ~~AUD-38~~ **DONE twice-over: S96b `56c731a` + S100 real-clock refinement `0874e9a`** — do NOT restart.
9. **AUD-12** historical rs_rank percentiles survivorship-biased (finder-only — verify first).

**VERIFIED-OPEN — P2/P3 (54 items; batchable):** AUD-45 (canonical weights doc coverage), AUD-46 (v1 write-txn fan-out), AUD-47-56 (SHP restatement journal + Screener SHRINK + XBRL SA/CONSO + NSE http shared client + /v1 versioning/selftest teardown/stale docstrings), AUD-58-100 (TRI benchmark, kill-switches #1/#3, sub-nav consolidation, chrome sunset, glossary drift, resource containment, timezone, DDL fragmentation, dead schema), AUD-101-117 (P3 polish; **AUD-101 is now UNBLOCKED** — AUD-04 landed).

**PROJECT_STATE §Open — VERIFIED-OPEN highlights:**
- **Charting overhaul (D71/D72) Phases 3-5** — drawing engine, four-family remainder, harmonic backtest.
- **DVPT picking-strategy program (D47 throughline)** — multi-TF signal engine · ignition ranking + `ranking_history` · `security_master` · absolute backtest · champion/challenger.
- **Positioning-pillar tail** — fiscal-quarter grain, saved-query alerts, EWMA key-price, promoter/FII/DII quarterly deltas, F&O OI/PCR.
- **UI Track A cosmetic residual** — per-page hand-conversion to native `ui_kit.shell` (runtime reskin makes this optional).
- **B5** unify dashboard D36 to `adjust.adjusted_closes` + zones on adjusted prices — SAME class as AUD-06; land together.

**Charter §4 NEXT — live build candidates (S98 kickoff prompt is the source):** X-04 overnight/intraday split + pump-flag · X-05 band-lock streak board (data flowing) · X-06 Amihud illiquidity migration delta (half-built) · X-07 volume-at-price shelves · D-06 announcement taxonomy → E-07 auditor-resignation red-flag · **P-05 replay-any-date API — UNBLOCKED (AUD-38 done S96b; provision a v1 API key on the box for live demos)**.

**BLOCKED (external gate / Ramana input required):**
- **AUD-42** BLOCKED as-written; feasible via index-class routing (per Blockers section).
- **AUD-58** BLOCKED — new niftyindices.com TRI fetcher required.
- **AUD-62** BLOCKED (workers=2 unsafe until AUD-46 lands).
- **AUD-59** BLOCKED on AUD-26 push-path (PARTIAL — waits on class-sweep + status==critical DM).
- **Wolfe point-4-strength descriptor** BLOCKED on Ramana's worked chart example (canon §D item 4).
- **E-08/E-09** BLOCKED on membership-change history depth (D-07).
- **D-09/D-10** BLOCKED — endpoint-discovery pass needed (direct probes 404).

**DATED-WATCH (armed; verify at fire — none require action ahead of time):**
- 2026-07-10 15:16 UTC — `hermes-slb.timer` first fire (D-04 SLB feed).
- 2026-07-10 16:04 UTC — `hermes-wolfe-scan.timer` first fire under D101/D102 three-snapshot code.
- 2026-07-10 18:01 UTC — `hermes-results-reactions.timer` first evening post-TCS.
- 2026-07-10 22:01 UTC — `hermes-board-health.timer` (silent = green).
- 2026-07-11 02:45 UTC — **first-ever season-digest DM** (missing = real bug; do NOT `systemctl start` per AUD-95).
- 2026-07-11 21:00 UTC — `hermes-fundamentals-provenance.timer` under S84 4h ceiling.
- ~2026-07-18 — banks report (results-season flow).
- ~2026-07-21 — SHP pledge coverage flood (Reg-31); AUD-25 residual check hooks here.
- 2026-07-22 — E-02 rating-drift first scheduled fire (aborts-with-census).
- 2026-07-25 — E-14 SHP combos first fire (GO possible if S85d dating clears floors).
- 2026-08-01 — E-04 campaign-arcs monthly depth-DM.

**STALE MARKERS FIXED (docs-only, canonical homes):**
- **NEXT-SESSION-CARRYFORWARD.md S84-95 wrap block:** the "S93 buyback orphan" note now marked CLOSED — `src/web/buyback_calc.py` committed at `60fcdd8`, mount re-added at `5805e6f` (verified via `git log --oneline --all -- src/web/buyback_calc.py`).
- **AUDIT-2026-07-02 §Blockers:** AUD-101 status flipped from "BLOCKED on AUD-04" to "UNBLOCKED 2026-07-10 (AUD-04 landed `c948c3f`+`a207c99`)".

**TRANSIENT docs whose retire condition looks met (flag only — do NOT delete without owner check):**
`docs/next-session-handoff.md` (Tracker workspace redesign per memory = SHIPPED+VPS-verified) · `docs/next-session-kickstart.md` (UI Phase 2/3 stubs superseded by S45+ ui_kit reskin). Both explicitly TRANSIENT-tagged. Absorption owner: next session that touches them.

**No new build directed from this assessment** — this lane is triage-only. Recommended next-session pick (per charter §4 kickoff, unchanged): X-04 or X-05 as first product picks; AUD-06/07/11 batch as the next quant-integrity block; ~~wait for AUD-38~~ AUD-38 landed (S96b) — P-05 is pickable.

---

## 🌊 S89 WOLFE D98+D99 (2026-07-10, `bf9b353`+`8a1dfea` live+walked) — 2 vetoes + 1 decision + 1 verify
**D99 EXECUTED (Ramana-approved via main session — NOT a veto item):** recency = first-class ranking
field. `rank_attention = Q × 0.5^(age/60)` (his approved 60-bar half-life; canon §5d) — /dash/wolfe
defaults to **current-first** with a labeled "Q all-time" toggle; age + freshness tier (hot/fresh/
aging/archive) on every ranked row + the walk summary; **WolfeRank removed** (one ranking system).
Q untouched; D96/D98 guarantees untouched. Verified live on TCS (wedge leads, attn 14, 6b hot) +
RAMCOSYS.
Shipped (panel-decided, all additive/revertible; PROJECT_STATE D98 + memory `wolfe-wave-strategy`):
the S89 sweep proved the old top-40-by-Q walk cap hid **55% of fresh waves** (3,121 restored by D96;
104 TCS-archetype had NO surface) → **Q badge now displays as STR x/11 · LND y/13** (rubric untouched;
LND INVERTS as a trade filter — gloss everywhere) + **Structure watch** section on `/dash/wolfe/scan`
(fresh≤15 · STR≥10/11 · not-on-the-scan; 95 rows, freshest-60 shown per Ramana, counted show-all; why-chips =
profile legs D/p1/F). Reproducible sweep: `research/wolfe_waves/sweep_cap_visibility.py`.
- ~~RAMANA VETO ①/② (STR/LND split · Structure watch)~~ **✅ RATIFIED 2026-07-10:** his recency
  directive itself mandated the split chips (item 6), and he tuned the watch's default slice
  30→60 and confirmed "60 is fine, keep it" — both surfaces are accepted, no longer flag them.
- ~~RAMANA DECISION ③~~ **✅ APPROVED + BUILT same day (D100, "approve R7, go ahead"):** §B2
  not-entry-qualified withhold live on both actionable queues — visible count + `?nq=1` toggle +
  ⊘ chip; chart/walk untouched per B2's own clause. NO open Wolfe decisions remain; the lifecycle
  build queue is R1+R2+R8 → R3/R4/R6.
- **🧭 LIFECYCLE PROGRAM (Ramana directive, S89 tail — canon `wolfe-rules.md` §D):**
  ✅ **R1+R2+R8 BUILT (D101, "go ahead and build"):** queue membership = OPEN state (EPA line not
  crossed) at ANY age — the 15-bar proxy died; `wolfe_epa_state` event-driven cache (CLOSED
  forever-cached, OPEN incremental from checked_through, 0.5% drift guard, per-symbol commits);
  the git-owned unit dropped `--fresh 15` (installed, drift gate exit 0 — NO timer start);
  attention-ordered counted 60-slices on both queues; edge badges scoped to the validated
  ≤15-bar window. ✅ R7 = D100. ALL §D clarifications resolved (point-2/3 = the §A point-4 gate;
  no liveness cutoff; point-4-strength recorded — needs his worked example).
  ✅ **R3+R4 BUILT same session (D102, "build R3 and R4"):** the approaching-5 forming queue
  (play A: SL=pt-4 breach, predicted-5 target, §A search-window liveness **+ the §A-lock
  exclusion `4e36bee`** — walk-caught on TATACAP/SUNDARMFIN, 84/386 dead rides pruned, 302
  live) = the scan page's third section; play-B progress chips (nearing-EPA→crossed-3→in-zone
  →beyond-zone→reversing) on both confirmed queues; `✓EPA {n}b`/`EPA open` chips on walk+list;
  per-symbol validation readout on /dash/wolfe. **LIFECYCLE PROGRAM COMPLETE** — only the
  point-4-strength descriptor remains (awaiting Ramana's worked chart example; legs 1-2 ∩ 2-3
  confluence). ⚠ Ramana-review note in PROJECT_STATE D102: the §A EPA-lock semantics (both
  pruned examples recorded) — his call whether such wedges should count as live.
  **VERIFY tonight:** the 16:00 UTC run persists THREE snapshots — journal "persisted N
  winner-profile setups + M structure-watch rows + K approaching-5 rows"; runtime ~9-15 min
  (three detect passes + warm state cache; consolidation to one pass = future polish),
  timeout 1800s.

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
4. **SSH is KEY-ONLY (AUD-34, fully closed):** password auth refused; laptop default key authorized;
   **fail2ban sshd jail active**. sshd config lives in `sshd_config.d/00-hermes-hardening.conf`
   (the `00-` prefix is load-bearing).
5. **hermes-api bind lives in a systemd DROP-IN** (`hermes-api.service.d/override.conf`) — survives
   unit rewrites; don't "fix" the main unit file.
6. **🗂 UNITS ARE GIT-OWNED (AUD-27, `05e25ec`):** any systemd change goes through
   `scripts/systemd/vps-live/` in git + `bash /opt/hermes/scripts/install-systemd.sh --install`;
   never hand-edit /etc/systemd on the VPS without capturing back. `--check` = the drift gate.
   All hermes services run SANDBOXED (ProtectSystem=strict + ReadWritePaths=/opt/hermes /var/log)
   with oneshot timeouts + timer jitter ±5min — a job writing outside /opt/hermes or /var/log will
   now FAIL (that's the point; extend ReadWritePaths deliberately, in git).

## 🏁 CHARTER §3 NOW — FULLY SWEPT (S95, 2026-07-10)
N1 ✓ · N1b ✓ (remainder ticked w/ evidence) · N2 ✓ (D-04 SLB feed LIVE S95 — `slb.py`,
`hermes-slb.timer` 15:15 UTC, 21d seed: 2,924 vol / 12,913 open-pos rows; VERIFY tonight's
first scheduled run ~15:16 UTC: journal Finished + `/var/log/hermes-slb.log` one clean line)
· N3 ✓ · N4 ✓ · N5 ✓. **Roadmap altitude now = charter §4 NEXT** — E-studies armed +
self-gating (E-02 Jul-22 · E-04/E-14 depth-gated · E-03 waits on disclosure depth); the
D94 lens estate (17 gated strategies) is the consumption surface.

## 🎯 CHARTER IS THE ROADMAP + S80h STATE (2026-07-05 — read FIRST; results season opens ~Jul-09)
**`docs/patearn-charter.md` is now the canonical plan (D87):** thesis · dated NOW/NEXT/LATER · 50-item
idea bank (E/X/D/P/M) · data-sprint table · KPIs · not-do list. Execute charter §3 NOW by default;
decide-record-execute, no advisory menus; every study through a PRE-REGISTERED gate, failures recorded
+ BLOCKING (cite the numbers before re-attempting). The audit-era digest + queue BELOW stay valid but
are now SECONDARY to the charter.

**Shipped S79–S80h (don't rebuild — verify + consume):**
- **Results-season WAR ROOM LIVE + self-refreshing** — `/dash/markets/results-reactions` (charter N1
  DONE): forward NSE board-meeting calendar (D-01, `board_meetings`, nightly
  `hermes-results-calendar.timer` 02:00 UTC) + delivery-confirmed reaction scanner (nightly
  `hermes-results-reactions` snapshot 18:00 UTC). First-class Markets nav lens; git-captured +
  clean-checkout-verified (`1a9369e`).
- **PEAD event lens — descriptive edge REAL, tradeable book FALSIFIED** (every wrapper incl.
  within-season) · **footprint detector gate FAIL** (T+2 structural) — both BLOCKING failure-table
  rows; descriptive products only (the scanner + `pead_surface.py`). New modules:
  `research/explosive_moves/{pead,pead_surface,footprint}.py`, `src/web/results_reactions.py`,
  `src/automation/results_calendar.py`, 2 timer stacks in `scripts/systemd/vps-live/`.
- **⚠ Sibling S81 lanes in flight (don't stomp; check origin tip + `git log` first):** data-estate
  postmortem (`docs/DATA-POSTMORTEM-2026-07-05.md`) + the **season-critical XBRL
  Provisions-merged-into-Expenses extractor fix** (must land before banks report ~Jul-09/18) + census
  corrections + security-master. **NAV files `v2_surfaces.py`/`lens_registry.py` are git↔VPS FORKED:**
  my scanner mount+lens are in git (`1a9369e`); a non-mine early-signals/sector-momentum reordering
  stays VPS-only (its owner's to settle — don't absorb it).

## ⚡ IMMEDIATE QUEUE (S80h — do these before the audit-program queue below)
0. ~~VERIFY hermes-launchpad-scan first run~~ **✅ DONE (Jul-10): Jul-08 + Jul-09 runs green,
   snapshot rolls nightly, page 8-10ms.** The Strategies board is now 11 MEASURED cards +
   on-card explainers (D93) — don't re-add link-only cards. NEW verify:
   **`hermes-fundamentals-provenance` Sat Jul-11 21:00 UTC run must FINISH** — S84 addendum
   raised its TimeoutStartSec 1800→4h (`99-timeout.conf`) after the fleet cap SIGTERM'd the
   ~110-min re-collect at 675/2767 on Jul-07; expect journal `Finished` + log 2767/2767.
   ~~pateval/corp-actions UNCAPTURED~~ ✅ RESOLVED (Jul-10): both stacks were already IN git
   (S83e/S83i), byte-identical to /etc — only the VPS-side vps-live MIRROR was missing them;
   synced server-side, `install-systemd.sh --check` now exit-clean (0 UNCAPTURED/DRIFT).
   RULE: after committing any systemd unit, also scp it to `/opt/hermes/scripts/systemd/
   vps-live/` — the on-box drift gate compares /etc against that mirror, not against GitHub.
1. **VERIFY the 2 new timers' first runs:** `hermes-results-calendar` (02:00 UTC) +
   `hermes-results-reactions` snapshot (18:00 UTC) — journal `Result=success`,
   `/var/log/hermes-results-*.log` clean, war room shows fresh data
   (`results_reactions_meta.generated_at` recent, `board_meetings` current); `systemctl --failed
   'hermes-*'` empty; `install-systemd.sh --check` clean.
2. **RESULTS-SEASON WATCH — LIVE THIS WEEK:** calendar shows TCS Jul-09, HCLTECH Jul-13, LTTS Jul-14,
   POLYCAB/TECHM Jul-16, HDFC/ICICI/Axis Jul-18. Watch the reaction snapshot fill in as names report +
   the XBRL bank flow (audit-era queue #2 below); the sibling's Provisions fix must land first.
2-bis. **D94 LENS QUEUE (Ramana ask 2026-07-10 — work top-down, one per session, D93 recipe:
   registry reader + measured card + blurb + glossary + board_health coverage; data ALREADY
   ingested, zero new deps):** ~~① insider-activity~~ **✅ DONE S86** (`/dash/insider`, 78
   fresh-conviction names; flag logic = `insider_events.flagged_symbols`, single source) ·
   ~~② credit-rating transitions~~ **✅ DONE S87** (`/dash/ratings`; E-02 dedup verbatim —
   3 true actions ≠ 11 raw rows; healthy-zero branch for quiet windows) · ~~③ SAST+pledge~~
   **✅ DONE S88** (`/dash/sast`, 37 confluence names; ⚠ flows = Reg-29(2) deltas <25% ONLY —
   29(1) filings are HOLDING levels and ≥25% filings are control transfers, both fenced in
   `sast_events.aggregate()`; never "simplify" that back) · ~~④ SHP QoQ deltas~~ **✅ DONE
   S90** (`/dash/shp`; flags = adjacent quarters, MATERIAL_PP=1pp, STRUCTURAL_PP=25 fence —
   ≥25pp/class = ownership event (RBLBANK 0→60pp), badged never flagged; provenance ⓧ
   disclosed, archive frozen + XBRL takeover) · ~~⑤ corp-actions calendar~~ **✅ DONE S91**
   (`/dash/actions`, Markets altitude; logistics-only — E-11/E-12 nulls quoted on-page;
   32 names ex-in-14d) · ~~⑥ surveillance tape~~ **✅ DONE S92 — 🏁 D94 QUEUE COMPLETE 6/6**
   (`/dash/surveillance`; snapshot-diff transitions, band events, "context never a gate").
   **The strategies estate is now 17 machine-gated lenses + 19 home pillars — next roadmap =
   the charter NOW queue.** Standing rules that OUTLIVE the queue: front-door parity rule
   (D94): any new strategy = strategist card AND home pillar AND board_health, same session.
   ⚠ lens_registry.py + v2_surfaces.py stay git↔VPS FORKED — patch the LIVE copies with your
   hunks (pull → Edit → push back), never full-file scp from git (S86 did this correctly).
   `hermes-board-health.timer` (22:00 UTC) now PAGES on hollow/stale cards — if it fires,
   fix the upstream job, don't mute the gate.
3. **TOP CHARTER PICKS for new build:** **X-02** T2T/BE delivery-contamination mask (correctness —
   pollutes MEP/DVPT delivery signals TODAY) · **E-03** post-disclosure drift + **E-04** campaign-arcs
   (footprint pivots — pre-register the gate) · **D-02..D-05** quick primary feeds (ASM/GSM · price
   bands · SLB · bulk/block history). Full bank: charter §7.

## STATE DIGEST (as of S77b/S78, night of 2026-07-02→03 UTC — 3+ concurrent lanes)
- **Queue #3 CLOSED — universal pledge veto reads the SHP primary source** (`6e2160b`→`07aca8d`
  adopted the LIVE sibling implementation; `concall_veto.py` + `concall_scores.py` byte-identical
  git↔VPS). Verified live: JPPOWER → `(True, 'promoter pledge 73%')`; vetoed set = EMSLIMITED +
  PAISALO (22%); rerank of 2026-07-02 21:25 UTC already used the fix. `--selftest` CLI exists (13
  checks). ⚠ JPPOWER has no concall corpus so it never appears in `concall_scores` — the veto bites
  via `compute_veto`/`veto_map`.
- **Audit P0s:** AUD-01 perimeter DONE (`cc988c6`, residual: optional Caddy basic-auth on /dash) ·
  AUD-34 key-only SSH + fail2ban DONE (residual: dedicated sudo user only) · AUD-02 on-box DONE with TWO
  complementary units (full DR `hermes-db-backup.sh` daily 20:35 UTC rotate-3 `d506cea`+`5f30d95`;
  non-derivable depth + research.db + em_cache `backup-db.sh` nightly 00:30 UTC `cc988c6`+`b04e4eb`;
  restore PROVEN both sides; **off-box residual**: `download-from-vps.bat` now also pulls
  `backups/db/` — run it periodically; a real off-box destination needs Ramana) · AUD-03 fixed
  (`cfcd1c7`) — **VERIFY the Sun Jul-05 09:00 UTC run succeeded** · **AUD-04 CLOSED (`c948c3f`
  audit-lane caches + `a207c99` lag_samples memo): /dash/coverage warm 7-8ms, 6-way 42-51ms/req,
  public 0.21s; cold ~3.7s once/data-day (P3: optional nightly pre-warm). ALL FOUR P0s CLOSED.**
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
1. **VERIFY (first checks of the new state):** (a) **the first UNATTENDED SANDBOXED nightly chain
   (Jul-03)**: news 03:30 → bhavcopy chain 14:00 → ingest cluster 15:30-17:15 — every unit now runs
   under ProtectSystem=strict etc. (`05e25ec`); a failure smells like a missing ReadWritePaths —
   check `systemctl --failed 'hermes-*'` + the unit logs, rollback = rm its 90-hardening.conf +
   daemon-reload; (b) Sun Jul-05 `hermes-concall-capture` 09:00 UTC (AUD-03's first live test;
   note its timer now has ±5min jitter); (c) both backup timers fired clean
   (`/var/log/hermes-backup.log`, `hermes-db-backup` journal; `backups/db/` sane, disk <35%);
   (d) run `bash /opt/hermes/scripts/install-systemd.sh --check` — must be clean (drift gate).
2. **RESULTS-SEASON WATCH (from ~Jul-09):** `/var/log/hermes-fundamentals-xbrl.log` runtime +
   gate-verdict quality — banks flow for the first time; expect `skipped_seen` dominant night 2+,
   `gate_deferred` >0 on heavy nights (budget 25, env `HERMES_XBRL_GATE_BUDGET`). Watch
   `hermes-shareholding-xbrl` + `hermes-sast-ingest` the same nights.
3. **AUDIT CORRECTION PROGRAM (work the doc's DAG in order, kickstart-pick-verify each):** check
   the audit session's wrap first. Remaining: B3 remainder (12/64/65/06+07/11), B4 trust-text
   honesty, B5 fetch discipline, B6 linkage+UI. DONE this session — do NOT redo: ~~B2 timer
   truth-capture~~ `05e25ec` · ~~B7 AUD-04 perf~~ `c948c3f`+`a207c99` · ~~AUD-36 error-leak~~
   `0bb0875`. B1 residuals needing RAMANA: off-box backup destination; optional /dash basic-auth.
   B1 residual not needing him: **AUD-35 dedicated non-root `User=`** (the sandbox itself is
   already done `05e25ec`; only the unprivileged-user migration remains — needs a chown window for
   the root-owned DBs, so its own deliberate step, not a tail).
4. ~~Stale-pledge CLASS SWEEP~~ **DONE (`60ea594`)** — `fundamentals.promoter_pledge` now syncs
   nightly from the SHP feed (post-`--ingest` hook; `--sync-pledge` CLI); all legacy readers
   (Pat "clean" filter + dossier displays + veto fallback) get primary-source values with zero
   reader changes. **CHECK ~Jul-21:** SHP pledge coverage should approach the universe as
   June-quarter Reg-31 filings flood in (was 76 syms / 6 of 85 fundamentals rows on Jul-03) —
   `sqlite3 research.db "SELECT COUNT(DISTINCT symbol) FROM shareholding_history WHERE
   metric='Promoter Pledge'"`. **DEFERRED with evidence (don't re-derive):** the NSE
   share-holdings-master GLOBAL window only returns latest-filing windows (~90 submissions for
   all of Apr..Jun-24, not the ~2k quarter mass — `b26eafa` log) — deep PIT pledge HISTORY needs
   a per-symbol crawl (`list_shp(symbol=...)`, ~2k listings + XBRL, throttle-broken across
   nights). Only worth it for backtest depth; the live veto/filter self-heal by ~Jul-21.
5. ~~C consumption wave~~ **DONE end-to-end (S77b + S78):** backtest (`fe9d161`+`73e7190`) → momentum
   C-blend 50/50 sort on `/dash/markets/momentum-scan` (`8068f80`) → Screen+ 'cap-alloc · C' column
   group + glossary (`13db67a`) → **stock-dossier `Cap-alloc (C)` score+tier on `/dash/stock`
   (`cf2a8cb`, S78, verify-then-swap deploy)** — all live-verified, all DESCRIPTIVE only (D66 fence;
   the C-BLEND re-cost `2026-07-05c` found it is NOT fundable at AUM — paper/descriptive overlay only,
   see the failure-models table). **NO build nits remain.** Only passive follow-up: re-check the live
   blend vs the recorded backtest numbers once a few weeks of nightly `ca_pctile` history accrue.
   Gate-0 tests: `tests/test_momentum_cblend.py` + `tests/test_concall_veto.py`. Superseded text below
   kept for the numbers:
   **(was) C consumption wave — BACKTEST DONE (S77b, `fe9d161`+`73e7190`), numbers now in hand:**
   **C-BLEND 50/50 on the RISKADJ rel-gate core = new best overlay** (net Sharpe 1.32, MaxDD
   −28.2%, Calmar 1.15, survives halves + 1.5× cost; subsumes the quality lens; hard veto/filter
   shapes DEGRADE — full table `docs/strategy-ledger.md` § Experiment 2026-07-03). Consumption
   design per the verdict: (a) descriptive `ca_score`/`ca_tier` column on screener/dossier
   surfaces (nightly `capital_allocation_scores` already populates); (b) a C-blend variant on the
   momentum surfaces. NOT a hard veto, NOT a standalone ranker. ⚠ scoring.py + momentum surfaces
   are audit-lane-hot — kickstart-pick-verify + patch surgically.
   ALSO VERIFY (AUD-10 residual): the post-fix momentum_scan re-run had NOT landed as of S77b
   (log mtime 21:31 UTC = pre-fix run; no process live) — confirm `ensemble_pctile` got restated
   under the re-ranked LOWVOL_MOM weighting before consuming momentum numbers.
6. **XBRL Phase 3 (big, design first):** historical backfill (legacy API 2018+ / BSE deeper);
   replace Screener series symbol-by-symbol where reconciliation allows; then delete `screener.py`.
7. **LIGHT THEME — real runtime support (Ramana asked S78b; design-first, own work item).**
   FINDING (don't re-derive): the product has **no runtime light theme today** — no
   `prefers-color-scheme` handling, no theme toggle anywhere; every visitor gets DARK regardless of
   OS setting. The ONLY light context that exists is **print** — `ui_tokens.py` (`@media print`)
   flips the palette (`--bg-*`→#fff, `--ink`→#0b0f17, `a{color:#0b0f17!important}`). **That print
   token-set IS the ready-made light palette to reuse.** Scope: an `@media (prefers-color-scheme:
   light)` (or a `body[data-theme=light]` toggle) block in `ui_tokens.py` re-pointing the same
   tokens. ⚠ BIG REVIEW SURFACE — it instantly restyles all 35+ screens: **charts, inline SVG
   micro-visuals, and any hardcoded rgba/hex overlays** (not driven by tokens) need a design pass to
   hit the premium-visuals bar; audit for non-token colours first (`grep -rn 'rgba(\|#[0-9a-f]\{6\}'
   src/web` beyond the token files). The S78b pill fix (`55a83c0`, `color:var(--ink)`) is already
   light-safe — the pattern to follow everywhere. Do NOT bolt on in a tail; treat as a headline
   session. Decision for Ramana: OS-follow (`prefers-color-scheme`) vs an explicit user toggle
   (persisted like the density toggle) — default recommendation is a toggle (predictable, testable).

## GUARANTEED-DONE (do NOT redo — kickstart-pick-verify against these commits)
**S79-S80h (2026-07-05 — results-season war room + PEAD studies):** PEAD study + pre-registered within-season variant (`f9f0b20`+`7d37127`) · footprint gate-FAIL (`f3eb0c4`) · CEO charter + D87/88/89/90 (`f3eb0c4`) · Results-Reaction scanner + `pead_surface` engine (`960eb3a`+`7d37127`) · war-room D-01 board-meeting calendar + `board_meetings` (`19423bf`) · 2 nightly timers calendar+snapshot (`c5dacd6`+`9b1f987`, AUD-95-safe) · scanner nav-lens + git-capture, clean-checkout-verified (`205e303`+`1a9369e`). Don't rebuild any of these. · Pledge veto SHP primary (`07aca8d`, live+verified; gate-0 pytest `c6722d7`) · pledge column-sync +
SHP backfill (`60ea594`+`b26eafa`, nightly hook live) · AUD-01 perimeter (`cc988c6`) · AUD-34
key-only SSH + fail2ban (VPS state) · AUD-02 on-box backups BOTH units
(`d506cea`+`5f30d95`+`cc988c6`+`b04e4eb`, restore-tested, de-duplicated BY DESIGN,
busy_timeout-hardened `b26eafa`) · AUD-39/09/10/15/05 tranche (`cef3e91`+`d085395`, live) ·
AUD-03 concall CLI (`cfcd1c7`) · AUD-23 (`911d020`) · AUD-24 (`16037b2`) · AUD-32 (`a24cf23`) ·
XBRL Phase 1/2/2c (`26cb3ef`/`5afe4ea`/`775badb`) · outage root-fix (`a4f1c21`+`d5b5933`) ·
kill-switch battery + #4 + dq_banner (`93f6abe`/`be7826a`+`ae73dab`+`3d8ae50`) · harness permissions
(`a2fdc99`) · **B2 systemd truth-capture + fleet hardening (AUD-27/30/31/35-sandbox, `05e25ec`;
units git-owned under `scripts/systemd/vps-live/`)** · **AUD-04 trust-page perf (`c948c3f`+`a207c99`)** ·
**AUD-36 external exception-leak (`0bb0875`)** · **C consumption end-to-end — momentum C-blend
(`8068f80`) + Screen+ column + glossary (`13db67a`) + dossier (`cf2a8cb`)** · **divergence-board
theme-token pill fix (`55a83c0`)**. **Do NOT rebuild any backup unit, the shareholding module, the
bank mapper, dq_banner, or the captured systemd units — verify, then consume.** `docs/SESSION-72-CARRYFORWARD.md` (untracked) retire-ready —
its owner session deletes it.

## 📋 S84-S95 WRAP REPORT (2026-07-10, the D93/D94/charter-sweep arc — this lane)
- **Shipped (all committed + pushed + live-verified):** launchpad 9s→0.01s nightly snapshot
  (D93) · board-health pager (D94) · SIX D94 lenses (insider/ratings/stake×pledge/holdings/
  corp-actions/surveillance — each page+card+pillar+glossary+gate, each with its honesty
  fence) · D-04 SLB feed + timer + 21d seed · provenance 4h-timeout fix · drift-mirror sync ·
  glossary ?q= deep-links. Estate: **17 gated strategies · 19 home pillars.**
- **VERIFY tonight/next boot:** ① `hermes-slb` first scheduled run 15:16 UTC (journal
  Finished + one clean log line + rows for Jul-10) · ② `hermes-board-health` first scheduled
  fire 22:01 UTC (exit 0 = silent; a page = a hollow card, fix upstream, never mute) ·
  ③ the Wolfe lane's new-unit 16:00 UTC run (its own carry-note above) · ④ Sat 21:00 UTC
  provenance run — a SCHEDULED TASK (`verify-provenance-timeout-fix`, Sun 08:00 IST) already
  reports it; don't duplicate.
- ~~🐛 HARNESS BUG (#0-bis wrap report): state-doc-gate v1.1 false-positive on compound
  `git add A B PROJECT_STATE.md && git commit`~~ **✅ FIXED same day — gate v1.3 (S86d lane):**
  root cause = an UNMODIFIED PROJECT_STATE.md expands to nothing via `ls-files -m -o -d`; naming
  it as an add token now counts as carrying it. Matrix-covered; no workaround needed anymore.
- ~~**⚠ S93 buyback orphan**~~ **✅ CLOSED (verified 2026-07-10, open-items assessment):**
  `src/web/buyback_calc.py` is committed at `60fcdd8` (S93 E-10 shipping commit); the
  `_ROUTER_SPECS` mount was re-added at `5805e6f` (S93b nav-drop repair). Live route serves
  from a clean checkout; no orphan remains.
- **Multi-lane craft notes that saved the night (reuse them):** verify-then-swap md5 per
  file pre-deploy · pull-patch-push for the FORKED nav files (5 clean repetitions) ·
  `git apply --cached` / `git hash-object + update-index` for partial staging when a
  sibling's hunks share your file · `tr -d '\r'` NEVER sed for CR-strip · remote IMPORT
  test, not just py_compile.

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously.
> **State on 2026-07-10 wrap:** charter §3 NOW queue SWEPT (S95); D94 lens queue COMPLETE
> 6/6 (S92); P-04 evidence pack LIVE (S96); **D103 residue closed (S98) — 28 in-row-compound
> symbols healed 4-leg, reconcile 77 → 6 TAPE_SUSPECT (baseline S85e → S97 parser → S98
> heal). No S94/S97/S98 residue open.** Roadmap altitude = charter §4 NEXT + §7 idea bank.
> Boot per `docs/SESSION-PROTOCOL.md`, read the 🥇/🧰/🌊 blocks at the TOP of
> `docs/NEXT-SESSION-CARRYFORWARD.md`, then:
> (1) run the WRAP-REPORT verifies (5 timers listed in the S98 block — SLB / Wolfe /
> results-reactions / board-health first fires Jul-10 + season-digest first-DM Sat Jul-11
> 02:45 UTC — a missing DM is a real bug, do NOT `systemctl start` mid-day per AUD-95;
> Sat 21:00 provenance is on its own scheduled task, skip; PLUS the 🚌 S101 bus watch:
> tonight's 14:04 UTC bhavcopy chain runs NEW step 60 — journal must show the
> `run_detection` summary and `signal_events --stats` latest_as_of must flip to 2026-07-10);
> (2) kickstart-pick-verify the next build from charter §4/§7 — the E-studies are ARMED and
> self-gating (E-02 Jul-22; E-04/E-14 depth-gated; do NOT run early). Prefer
> product/consumption picks. **Deprioritized: P-04 (S96) · E-10 (S93) · D103 heal (S98).**
> **Live candidates:** X-04 overnight/intraday split + pump-flag · X-05 band-lock streak
> board (⚠ possibly IN FLIGHT — `band_lock.py` sighted untracked in the main tree 12:46 UTC
> Jul-10; kickstart-verify before picking) · X-06 Amihud illiquidity migration
> delta (half-built, `mep_signals.py:286`) · X-07 volume-at-price shelves · D-06
> announcement-category taxonomy → E-07 auditor-resignation red-flag · P-05 replay-any-date
> API (AUD-38 DONE S96b `56c731a` + D104 real-clock refinement S100 `0874e9a` — buildable;
> provision a v1 key on the box first) · ⚠ signal_events PRODUCER wiring is IN FLIGHT in a
> parallel lane (claims "S100" — stale, must renumber; see the S100 block) — don't pick it
> unless a study's gate has newly reconciled; ALSO verify the first-ever season-digest DM
> (Sat Jul-11 02:45 UTC — a missing DM = real bug, see the S96 block);
> (3) respect the standing fences: 17 gated lenses stay DESCRIPTIVE with their honesty
> fences (E-02 dedup · CONTROL_PCT/STRUCTURAL_PP=25 · plumbing classes · placebo-nulls
> quoted); front-door parity rule (D94) for any new strategy; forked-nav pull-patch-push;
> `tr` not sed; explicit-path staging; **fork-check the VPS live files for EVERY pick before
> building** (S100's AUD-38 collision: a sibling had deployed uncommitted work — and its
> deployed files were older than its eventual commit; re-diff deltas against the LANDED
> commit, never against live bytes).
> Access is harness-enforced — never ask for access or per-step confirmation; get guidance
> from the agents, not from me; I won't answer. Keep every guardrail (esp. #8
> primary-sources-only). Perimeter: curl via the Caddy hostname or ssh-localhost, never raw
> :8000. Wrap per the protocol and refresh this carry-forward + kickoff prompt.
