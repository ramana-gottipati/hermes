# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`); **NEVER ask
Ramana for file/folder/tool access in any form — a permission prompt that still fires is a BUG to log
at wrap (CLAUDE.md #0-bis), never a cue to ask.** Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

## 🆕 2026-07-11 — S109 + S110 landed (three lanes, all on origin/main; none redoable)
Diverged from S108 then reconciled by commit-then-pull-rebase (union-resolved PROJECT_STATE — two
S109 entries KEPT + S110 at top): **`dfbe175` S109/D111 Wolfe §B rebalance** (spring-reclaim C ·
deep-extension G · 2.0 restored · RSI-divergence fix — Ramana line-by-line) · **`6899a94` S109
docs/strategies** (canonical `docs/strategies/` reference layer, 9 pages) · **`686f7b9` S110/D112
DEEP-DATA VALUE SPRINT** (this lane). All pushed.

**🆕 S110 — 3 NEW insight surfaces LIVE + deployed (verify-then-consume, do NOT rebuild — memory
`deep-data-insight-lenses`):**
- `/dash/market-internals` — 22y market health (price-breadth + the MEP **tape** + delivery/dispersion/
  coil) from bounded **`market_internals_daily`** (5426 rows, **NO timer**; rebuild/refresh via
  `python -m src.automation.market_internals --backfill` / `refresh_tail`). HERO = price-vs-effort divergence.
- `/dash/participants` **UPGRADED** — full 2.5y FII long:short tape + percentile gauge + retail mirror (additive; existing gauge/matrix kept).
- `/dash/launchpad-track` — **orphan rescue**: `ignition_outcomes` (50k signals) outcome distribution + `averaging_zones` ladder. ⚠ `ret_12m` is in PERCENT units.
- `/dash/move-anatomy` (Trust lens — **PROMOTED from deferred** at Ramana's ask) — the `features` panel (166K events, was unread) as a descriptive fingerprint: moves launch from **momentum/RS** (z +0.88), NOT accumulation-footprint (delivery z −0.49) + MFE/MAE envelope. Leak-safe (precursors only); reads research.db; linked from Coverage Trust index.
- Shared **`src/web/infographics.py`** — 8 tested SVG primitives; **reuse for any new chart, don't hand-roll**. Morning **briefing Artifact** delivered (diverse-charts deliverable + the DEFERRED queue).
- **Deferred (VALIDATED, build when the caveat clears — don't re-recon):** Sector Regime Map (~322 tagged syms) · tier-migration alluvial (D66 veto) · ownership DII/FII drift (~3y) · SLB short-interest (expiry-roll artifact) · seasonality calendar. (~~Anatomy Fingerprint~~ **✅ SHIPPED `/dash/move-anatomy`**.) `stock_oscillators` = orphaned one-shot → drop or wire.
- Deploy craft: new modules clean-scp'd (CR-strip `tr`); FORKED nav (`lens_registry`/`v2_surfaces`) **anchored-inserted** (assert count==1 + rollback), NEVER full-scp; import-test + writer-safe restart; gates PASS; walked LIVE (`curl -sL`, flat→nested 307). Both new lenses in sub-nav (not orphaned).
- ⚠ Untracked **`.claude/launch.json`** (dev preview harness → scratchpad path) left uncommitted, harmless — `rm` or ignore.

**🧊→✅ Wolfe §B freeze LIFTED:** the S108 carry-forward's "FROZEN pending Ramana's §B weightage sign-off"
is RESOLVED — he ratified the rebalance line-by-line (D111, `dfbe175`). The D108 2/3/4 fractal gate stays enforced.
Wolfe draw-tool commit `8fc40dc` is still on branch `wolfe-draw-tool` (unmerged; see `docs/strategies/README.md` recon flags).

## 🔔 2026-07-10 EVENING — FOUR lanes landed the same day (read all four; none is redoable)
**S102 (P-05, Ramana: "complete that now") · S103 (attention face, D106) · S104 (AUD-06/07/11,
D107) · the Wolfe FRACTAL arc → S105/D108 revert + 🧊 FREEZE (see 🌀).** Canonical chain:
`235a424`→`fdb964a`→`ee5c7a4`→`4548a01`→`8637ea8`→`020bb6f`→`0c89e8f`→`43e075f`→`51cbd02`→
`579d989` (a twin local S105 implementation was dropped un-pushed — settled, see 🌀).
Multi-lane craft that kept it clean: renumber-on-collision
(S102 was double-claimed → this lane renumbered to S103 pre-push, the S100/S101 recipe);
commit-then-pull-rebase with union conflict resolution on the two always-rewritten state docs;
a stuck `rebase --continue` (empty `ls-files -u` yet refusing) resolved by manual
`git commit -F .git/rebase-merge/message` — the sibling lane finalized the ref bookkeeping.

- **🔔 S103 (D106): the signal-event bus has its HOME face** — `/dash/attention`
  (magnitude-ranked batch tape · lens chips · `?as_of=` PIT replay via the SAME
  last-batch-on-or-before resolver as `/v1/attention`, requested→served disclosed · last-12-
  batches pivot · two-clock fence) + the Home "🔔 Attention" board (hard-capped 6, defensive
  '' → omitted). Lens after Markets-Overview + `_ROUTER_SPECS` mount + glossary section
  (`?q=attention`). **D106 fence: deliberately NO strategist card / board_health** — a bus
  face aggregating other lenses' state-changes is not a gated strategy; never "promote" it
  without its own pre-registered study. Tests 8 hermetic; suite green. **The live walk caught
  2 defects unit-tests missed** (full-batch denominators + disclosed render cap; the seed's
  stale-symbol tail — mep events dated 2004–2020 from delisted names' last flips, REAL changes
  detected late — now EXPLAINED by the fence, kept per nothing-discarded). Deploy: anchored
  inserts on the two FORKED nav files (`/tmp/deploy_s102_nav.py` pattern, backups
  `.bak-s102-*`), straight scp for the isolated module; the nesting engine picked the lens
  automatically (40 nested lens routes). **Bus faces:** ~~since-you-last-looked brief~~ **✅
  BUILT S108/D110** (`/dash/attention` top strip, cookie-keyed `events_since`; PROJECT_STATE
  Session 108). Still unbuilt: alert rail · SSE · dvpt/quality/cpr lenses · stock-grain rs.
- **🎬 S102 (P-05 lane): /dash/replay-any-date LIVE** — any symbol + any date through the
  entitled /v1 API in-process; pit chips / typed absences / RFC-7807 verbatim; reproduction
  curls; coverage front-door chip; **`HERMES_V1_DEV_KEY` now provisioned on the box** (0600,
  never printed — the P-05 provisioning gap is CLOSED). Known pre-existing finding: the chrome
  gate's in-process app misses the uk-skin marker on /dash/strategies while LIVE serves it —
  spawn-task chip `task_fd684c67`, live site unaffected.
- **🔧 S104 (signals lane, D107): AUD-06 + AUD-07 + AUD-11 CLOSED** — adjusted zones, one
  hot-day core, tape-corroborated corp-action fallback (`4548a01`). The B5 residual class is
  absorbed; read ITS PROJECT_STATE entry before touching `signals.py`/`adjust.py` again.
- **🌀 WOLFE FRACTAL ARC (Ramana-steered, moved FAST tonight — read in order):** `ae84185`
  ("the fractal has been ignored", rules restated) → `725a0df` (2/3/4 fractal = **MANDATORY
  detection gate** — "must, minimum 2 fractals; without a fractal do not consider"; 32% of
  surfaced waves violated it) → `b85b983` (the COMPLETE strength concept, canon: B0 5 drivers
  + EPA "touched not cut" 0.3%/full-span) → **S105/D108 REVERT (`0c89e8f`, canonical):** back
  to the D96 baseline + the fractal gate as ENFORCED code; **REMOVES the S89 recency/STR-LND/
  structure-watch/lifecycle estate** (D98–D102 surfaces superseded by Ramana's direction —
  read the S105 PROJECT_STATE entry + D108 amendment `51cbd02` before ANY wolfe work).
  **✅ The same-directive twin-implementation collision was SETTLED same night** (memory
  `wolfe-wave-strategy` reconciliation note): the local twins `94f56fa`/`b85b983` were dropped
  un-pushed; **origin `0c89e8f`→`43e075f`→`51cbd02`→`579d989` is the single truth; VPS aligned
  to origin bytes, hash-verified.**
  **🧊 WOLFE IS FROZEN (Ramana gate):** NO Wolfe code by ANY lane until he signs off the §B
  weightage proposal (A 6→5 · C 3→4 · F 3→4 · H 2→3 + the §B0.4 "touched not cut" EPA recode);
  canon = `wolfe-rules.md` §B0 (5 drivers; freshness is NOT strength). See `579d989` +
  `docs/wolfe-NEXT-SESSION.md`.

**🔭 TONIGHT'S BATTERY (results — DONE, do not re-verify):**
- **🚌 S101 bus watch GREEN:** chain `Finished` 14:10:52 UTC exit 0 (16 steps, ~9 min); step-60
  summary `run_detection: {'mep': 131, 'oi': 142}` — NOTE it lands in
  **/var/log/hermes-bhavcopy.log**, not the journal (watch-condition wording refined);
  `--stats` latest_as_of 2026-07-09 → **2026-07-10**, events 1,188 → 1,461 (idempotent over
  the seed ✓). `/dash/attention` serves the fresh batch ("showing the top 200 of 273 by
  impact").
- **hermes-slb first scheduled run GREEN:** journal Finished (1s) · exactly one clean log line
  (volumes 3,074 rows / 363 syms · open-pos 13,352, latest Jul-10) · Jul-10 rows live
  (150 `slb_volumes` + 439 `slb_open_positions`). The D-04 feed is production-cadenced.
- **hermes-wolfe-scan 16:02 UTC first three-snapshot run GREEN:** exit 0 in 8m45s; summary in
  **/var/log/hermes-wolfe-scan.log** (file, not journal): `persisted 757 winner-profile setups
  + 814 structure-watch rows + 305 approaching-5 rows (as-of 2026-07-10)`. ⚠ This run predates
  the S105/D108 revert — future summaries will differ by design (structure-watch/lifecycle
  removed).
- **hermes-results-reactions 18:01 UTC GREEN:** Finished (1m11s); `MTTR: 1 newly-surfaced
  results events this run` (the FIRST real MTTR mint, post-TCS) + 1,571 rows, beats+deliv 157.
- **Still to watch (hand forward):** board-health 22:01 UTC Jul-10 (silent = green — check the
  journal next boot) · **first-ever season-digest DM Sat 02:45 UTC (missing = real bug — page
  it, do NOT `systemctl start` per AUD-95)** · Sat 21:00 provenance = its own scheduled task
  (`verify-provenance-timeout-fix`, Sun 08:00 IST) — skip · banks report ~Jul-18 · ~Jul-21
  SHP pledge-coverage flood check · E-02 Jul-22 · E-14 Jul-25 · E-04 Aug-01 (armed,
  self-gating — do NOT run early).

## 🧹 HYGIENE LANDED S103 (don't redo)
- **Tracker retro-doc debt PAID:** the ~18-day "PROJECT_STATE entry owed" reconciliation is in
  (D54 section: umbrella + steps 2–5 + alerts arc with hashes; § Database schema:
  book/qty/alerts_json + tracker_alert_state/_delivery; § Key paths: tracker_alerts.py).
  Memory `tracker-workspace-redesign` = ARC CLOSED.
- **2 TRANSIENT docs retired** (fold-verified then `git rm`): `docs/next-session-handoff.md` ·
  `docs/next-session-kickstart.md`. Remaining TRANSIENT-tagged doc to assess when touched:
  `docs/ui-perf-handoff.md` (its own banner: retire once perf Steps 1–5 are shipped/folded).
- `patearn-tracker-autobuild` scheduled task: already disabled + self-labeled DONE — inert.

## 🌳 WORKTREE STATUS (validated S108, 2026-07-11 — do NOT re-investigate)
All 7 worktrees surveyed; **every branch is already an ancestor of main** (0 ahead each) — nothing
to merge at the branch level. The only uncommitted work, and its verdict:
- **`.../6430507e/…/wt-wt` (`tmp/s108-weights`)** — the **§B weightage rebalance** in flight
  (point-1/C/F/H reweight + EPA touched-not-cut recode, `_QUALITY_MAX` 24→25, comments dated
  "Ramana 2026-07-11"). **LEAVE IT — this lane is finishing it** (Ramana directive S108). It lands
  the frozen-pending-sign-off work; do not absorb/commit it from any other lane.
  **✅ VERIFIED CLEAN (S108-lane, `dfbe175` = S109/D111) — do NOT re-verify.** The rebalance
  landed + deployed; the full battery passed: pushed + worktree clean · state-doc D111+S109
  present · py_compile + import OK, `_QUALITY_MAX=25` (A4·B3·C4·F4·G2·H3·I2·D3 = Ramana's spec) ·
  suite 55 pass/1 skip, no regression · **D108 2/3/4 fractal gate intact** (§B-score-only diff,
  §A detection untouched) · `/dash/wolfe`+`/dash/wolfe/scan` 200 · box `wolfe.py` md5 == git ·
  `_wave_payload` sets `points_max=_QUALITY_MAX` (overlay badges render /25 on-read). Two honest
  non-defects: the persisted `wolfe_signals` scan refreshes to /25 on tonight's 16:02 UTC run
  (on-read already /25); and `dfbe175` ships **no committed wolfe test** (the `tests/test_wolfe.py`
  in the tree is a separate lane's uncommitted file) — a coverage gap for the wolfe lane to close.
- **pat-eval (`blissful-nash`)** — its uncommitted AUD-40 work is **already in main via `9ed6aa4`**
  (identical changeset); the worktree copy is un-cleaned cruft. Nothing to do.
- **main-tree wolfe files** — were a **stale pre-S106/S107 snapshot** (net-deletion, zero unique
  content); restored to HEAD S108 so they can't revert shipped work. Clean now.
- Other worktrees (`charming-brattain`, `objective-kowalevski` detached, `fervent-dubinsky`) —
  clean, fully contained in main. Removable whenever their sessions end.

## 📋 OPEN-ITEMS ASSESSMENT (2026-07-10 triage lane, updated post-S104)
**P1 VERIFIED-OPEN (ranked):** ~~AUD-06/07~~ **✅ S104** · ~~AUD-11~~ **✅ S104** ·
**AUD-14** throttle→"holiday" class sweep (5 fetchers; `RetryableFetchError` lives only in
`fno_oi.py`; deploy-window-unsafe near 14:00 UTC — pick a morning) · **AUD-22** research
replication bypasses the PIT layer (route through `fundamentals_asof.py`) · **AUD-25**
feed-liveness covers 4/12 feeds · **AUD-28** setup-news.sh heredoc regression (do with AUD-27
remainder) · **AUD-37** /v1 metering under-records (design-first: 500s unlogged, bytes_out=0)
· **AUD-12** rs_rank survivorship (finder-only — verify first). **P2/P3:** AUD-45..117 batch
list unchanged (AUD-101 UNBLOCKED). **BLOCKED (external/Ramana):** AUD-42/58/59/62 ·
Wolfe point-4-strength (needs his worked chart) · E-08/E-09 (D-07 depth) · D-09/D-10
(endpoint discovery). **PROJECT_STATE §Open highlights:** charting D71/D72 Phases 3-5 ·
DVPT picking-strategy program (D47) · positioning-pillar tail · UI Track A cosmetic residual.
**Light theme** = design-first headline session (never a tail; the S78b finding stands).

## 🎯 NEXT PICKS (charter §4/§7 altitude; kickstart-pick-verify EVERY pick + fork-check VPS live files)
1. **Wolfe lane: 🧊 FROZEN** — no Wolfe code by any lane until Ramana signs off the §B
   weightage proposal (🌀 bullet, `579d989`). When he answers, `docs/wolfe-NEXT-SESSION.md`
   is the run-book.
2. **Product:** **X-04 overnight/intraday split + pump-flag** (top remaining charter X-item) ·
   X-06 Amihud migration delta (half-built, `mep_signals.py:286`) · X-07 volume-at-price
   shelves · D-06 announcement taxonomy → E-07 auditor-resignation red-flag.
3. **Bus follow-ups (natural after D106):** ~~since-you-last-looked brief~~ **✅ DONE S108/D110**
   → remaining: the **alert rail** (push a firing event via `tracker_alerts`-style dedup) · the
   **SSE stream** (live tape) · dvpt lens design (needs a banded state first).
4. **Quant-integrity:** AUD-14 (morning window) · AUD-22 · AUD-37 (design-first).
5. **P-05 follow-through:** the demo is LIVE with a provisioned key — next is Ramana-facing
   (pitch/demo assets), not build.

## 🏛 AUDIT BOOT-CHECK (binding — unchanged)
Reference: `docs/AUDIT-2026-07-02-institutional-review.md` (statuses updated IN the doc).
1. **Never run `scripts/setup-news.sh` on the VPS** (AUD-28). 2. **Never `systemctl start` a
hermes timer mid-day** (AUD-95; exception: the 2 backup timers). 3. **Perimeter closed
(AUD-01):** curl via `https://srv1704897.hstgr.cloud` or ssh-localhost; raw :8000 dead;
`/chat`+`/conversations` need `X-Hermes-Secret`. 4. **SSH key-only** (AUD-34; the `00-`
prefix is load-bearing). 5. **hermes-api bind lives in a drop-in** — don't "fix" the main
unit. 6. **Units are GIT-OWNED** (`scripts/systemd/vps-live/` + `install-systemd.sh
--install`; `--check` = drift gate; all services SANDBOXED — extend ReadWritePaths in git,
deliberately).

## 🧰 HARNESS NOTES (S86d — unchanged, applies to YOUR session)
`.claude/settings.local.json`: state-doc gate v1.3 (BLOCKS src/scripts commits without
PROJECT_STATE; `state:skip` = deliberate exception) + 118 skillOverrides + connectors off.
6 user-level skills at their trigger points: failure-ledger · walk-the-journey ·
deploy-reality · multi-session-safety · transient-doc-lifecycle · explain-visual.
Craft that keeps saving nights: verify-then-swap md5 pre-deploy · pull-patch-push (or
anchored in-place inserts) for the FORKED nav files — **never full-file scp
lens_registry/v2_surfaces/dashboard** · `tr -d '\r'` never sed · remote IMPORT test, not just
py_compile · explicit-path staging + `git diff --cached --name-only` before every commit ·
grep origin for the other lane's newest session number BEFORE claiming yours.

## 🥇 STANDING ESTATE (compressed; verify-then-consume, never rebuild)
**19 measured strategy lenses** (X-05 band-locks was the 18th, S96c; all DESCRIPTIVE with
honesty fences: E-02 dedup · CONTROL_PCT/STRUCTURAL_PP=25 · plumbing classes · placebo-nulls
quoted; front-door parity rule D94 applies to any new STRATEGY — strategist card AND home
pillar AND board_health, same session). **Trust cluster:** coverage · evidence-pack (P-04) ·
replay (tape) · replay-any-date (P-05) · glossary 245+ keys. **Season estate:** war room +
MTTR + armed E-studies (self-executing digests; verify DMs, never rebuild). **Corp-action
integrity:** TAPE_SUSPECT 77→6 (S97/S98 heals DONE — treat D103's consequence heal as DONE)
+ S104's adjusted-zones close (D107). **Bus:** producer step 60 (D105) + /v1 + the home face
(D106). **Guaranteed-done anchors (tonight):** `235a424` P-05 · `ee5c7a4` attention face ·
`4548a01` signals batch · `ae84185` fractal pointers. Older anchors: PROJECT_STATE
§ Session log (S84–S101 wraps) — kickstart-pick-verify against those before redoing ANY
"open" item.

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously. Boot per `docs/SESSION-PROTOCOL.md`
> (§ AT SESSION START), then execute `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom —
> read the 🔔 FOUR-LANE block + 🔭 battery results FIRST (S102/S103/S104/fractal all landed
> 2026-07-10 evening; do NOT redo any of them).
> (1) Run the remaining watches: results-reactions (Jul-10 18:01 UTC) + board-health (22:01
> UTC, silent = green) results in the journals; **first-ever season-digest DM Sat 02:45 UTC —
> missing = real bug, page it, never `systemctl start` mid-day (AUD-95)**; Sat 21:00
> provenance is on its own scheduled task, skip.
> (2) Pick per § NEXT PICKS: wolfe lane → the §B weightage sign-off was FROZEN at `579d989`
> BUT the wolfe lane has since pushed S106/S107 (`2541009`/`5bbeb68`) — **check the wolfe
> lane's own latest state, this freeze line may be stale**; product lane → X-04
> overnight/intraday split + pump-flag; bus lane → the **alert rail / SSE** (the
> since-you-last-looked brief shipped S108/D110); quant lane → AUD-14 (morning window only).
> E-studies are armed + self-gating (E-02 Jul-22 · E-14 Jul-25 · E-04 Aug-01) — do NOT run early.
> (3) Standing fences: descriptive-only estate + honesty fences; D106 — the attention face
> carries NO gate, never promote it to a strategy without its own study; forked-nav files =
> pull-patch-push or anchored inserts, NEVER full-file scp; `tr` not sed; explicit-path
> staging; fork-check VPS live files + grep origin for session-number claims BEFORE building.
> Access is harness-enforced — never ask for access or per-step confirmation; get guidance
> from the agents, not from me; I won't answer. Keep every guardrail (esp. #8
> primary-sources-only). Perimeter: curl via the Caddy hostname or ssh-localhost, never raw
> :8000. Wrap per § AT SESSION END and hand off the next prompt.
