# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`); **NEVER ask
Ramana for file/folder/tool access in any form — a permission prompt that still fires is a BUG to log
at wrap (CLAUDE.md #0-bis), never a cue to ask.** Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

## 🧰 S86d HARNESS NOTE (2026-07-10) — session infrastructure changed, applies to YOUR session
- `.claude/settings.local.json` now carries three additive keys: `disableClaudeAiConnectors` (claude.ai
  connector fleet no longer loads in Hermes sessions), a PreToolUse **state-doc gate**
  (`scripts/state-doc-gate.cjs` — BLOCKS any `git commit` that stages `src/` or `scripts/` without
  PROJECT_STATE.md in the same commit; deliberate exception: append `state:skip` to the commit command;
  fail-open on errors), and 118 `skillOverrides` hiding the never-used cowork skill fleet
  (anthropic-skills/engineering/pdf-viewer/core skills all KEPT). Hooks load at session start, so the
  gate IS live for you. If it misfires, that's a wrap-report bug (#0-bis), not a reason to weaken settings.
- 6 new user-level skills exist (failure-ledger · walk-the-journey · deploy-reality ·
  multi-session-safety · transient-doc-lifecycle · explain-visual) — invoke them at their trigger
  points; MEMORY.md index is now slim one-liners (detail lives in the body files — extend bodies, never
  re-fatten index lines). Full inventory: memory `claude-harness-optimization`.

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
- **🧭 NEW — LIFECYCLE PROGRAM (Ramana directive, S89 tail; RECORDED, build queued):** his
  FORMING / OPEN (EPA untouched = "my actual need") / CLOSED (EPA touched = reference-only)
  taxonomy is canon in `docs/wolfe-rules.md` §D (verbatim + state machine); recommendations
  **R1–R7** + probe numbers in PROJECT_STATE § open items ("Wolfe lifecycle program").
  **Next Wolfe session builds R1+R2+R8 first** (state-as-data; actionable surfaces filter by
  STATE not age; event-driven EPA state per his line-formula directive), then R3/R4/R6/R7.
  ✅ ALL clarifications RESOLVED same day (§D items 1-5): the point-2/3 bound = the §A point-4
  channel gate (already enforced, NO code change — "do not modify the wave count"); OPEN spans
  two phases (approaching-5 / riding-to-EPA); NO liveness cutoff (state-filter + attention-order
  + counted slice); NEW recorded-not-built: point-4 strength via legs 1-2 ∩ 2-3 confluence
  (needs his worked example before build).
- **VERIFY next session:** tonight's `hermes-wolfe-scan` 16:00 UTC run must persist BOTH snapshots —
  journal shows "persisted N winner-profile setups + M structure-watch rows"; run takes ~6 min now
  (timeout 1800s, checked); `wolfe_signals` universes `nifty500` + `nifty500:watch` both fresh.

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
   32 names ex-in-14d) · **← LAST: ⑥ surveillance-transition tape (797+52)**. Front-door parity rule
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

## KICKOFF PROMPT (paste to start the next session)
> Continue the Hermes/Patearn work autonomously.
> **FIRST read `docs/patearn-charter.md` (canonical, D87) + the CHARTER/⚡IMMEDIATE blocks at the TOP of this doc — the war room shipped; charter §3 NOW is the primary queue; the audit-era queue below is secondary.** Boot per `docs/SESSION-PROTOCOL.md`, then execute
> `docs/NEXT-SESSION-CARRYFORWARD.md` top-to-bottom (START with queue #1 — the new-state verifies:
> the first sandboxed nightly chain, the Jul-05 concall run, both backup timers, and the
> `install-systemd.sh --check` drift gate — then queue #3, the audit correction program, checking
> the audit session's wrap for what's already landed). Access is harness-enforced — never ask for access/write/delete or
> per-step confirmation. Get guidance from the agents, not from me; I won't answer. Keep every
> guardrail (esp. #8 primary-sources-only). Remember the perimeter: curl via the Caddy hostname or
> ssh-localhost, never raw :8000. Wrap up per the protocol and write the next carry-forward.
