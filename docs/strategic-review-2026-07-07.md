# Strategic review — 2026-07-07 (S83; full-estate, 17-agent panel + verification wave)

<!-- TRANSIENT: retire once (a) accepted items are folded into patearn-charter §3/§4 via D-log entries,
     (b) the PROJECT_STATE hygiene pass (§6.6 below) lands, and (c) the reconciled calendar (§4) is spent.
     Until then this is the disposition reference for "what next / what's junk / what's already built". -->

**Method.** 8 inventory agents (state · ledger · audit+postmortem · DBs · surfaces · idea corpus ·
research harnesses · computed signals) → 32-claim verification wave against tree+git (kickstart-pick-verify
at scale) → 4-lens synthesis (insights / product / junk / viz) → completeness critic → main-session
reconciliation with fresh greps. Panel ran at tip `38d2f3c`; reconciled here to tip `90d37b4`.
Every load-bearing claim carries a commit/file/number. ~2.3M agent tokens, 495 tool calls.

---

## 0. Verdict (one paragraph)

The machine is **built and ahead of schedule** (war room live pre-Jul-09; 3 pre-registered studies already
ledgered this quarter; concall PIT clocks just landed `3297a50`). The gap is not construction — it is
**operating visibly and publishing**: MTTR is unmeasured, spec-sheets are 0/3, the failure-ledger numbers are
not yet rendered where a buyer looks, and ~a dozen built-and-paid-for assets (3,797 company briefs, C
sub-metrics, provenance lag audit, fii_dii, signal_events bus) are write-only. Research-wise, calendar-time
ranking and every book wrapper are closed by evidence; the open frontier is **event-time descriptive studies
on data already in hand** (~9 gate-ready at ₹0 spend) plus the correctness items that outrank them (X-02
mask, oscillators staleness). The season (~Jul-09) is the one demo that cannot be re-run: freeze the war-room
path, measure it, harvest it.

---

## 1. Freshness protocol (binding lesson from this very review)

The estate moved **while the panel was writing**: `3297a50` (concall PIT clocks — flipped two study premises
from "blocked" to "in hand"), `f45bf81`+`4691684` (AUD-20/87/88 glossary honesty — invalidated a KPI-RED
claim), `d0879bd`+`90d37b4` (AUD-08 insider supersede — E-03's 947-episode count needs a re-count on deduped
data). Three panel claims died in ~30 minutes. Additionally the panel's "Pat overvalued inversion is a live
bug" was **stale** — fixed at `src/pat/understand.py:404-410` with a regression entry in `eval_set.py`.

**Rule:** any session consuming this review pins its execution tip and runs kickstart-pick-verify per pick.
Stale-open markers lie in BOTH directions (13 doc-says-open items verified BUILT in §5.2; several
doc-says-done items verified open in §3).

---

## 2. Insights still formable from data in hand (ranked, gate-first)

All numbers below are ledger-blocking figures (`docs/strategy-ledger.md`). Nothing here is a book;
the survival bar is net Sharpe > 0.89 BOTH halves under the participation-cost model, and no candidate
is expected to clear it — the win condition is the descriptive readout + spec-sheet.

| # | Study / item | Data in hand | Harness | Gate sketch | Ships as | Effort | When |
|---|---|---|---|---|---|---|---|
| 1 | **X-02 T2T/BE delivery mask** (correctness) | `bhavcopy_rows.series` — in the PK, every row; **no D-02 needed** | mask in signals/mep + DQ note | not a study; readout = polluted symbol-day count, published | data-quality note + affected-rows chip | 1s | NOW (lite pre-Jul-09, full wk-1) |
| 2 | **M-01 evlib + M-02 placebo harness** | n/a | extract `pead.py` (car_path/side_cost/tape_features) + `footprint.py` controls; placebo wrapper grep-verified missing | selftest parity; every study publishes its placebo-inflation × | infra multiplier | 1.5s | NOW (N4 + pulled-forward M-02) |
| 3 | **Concall growth-intent walk-forward** (ledger-sanctioned next) | 3,494 settled guidance rows; **real call/filing dates now in hand (`3297a50`)**; recorded 3m de-marketed tilts: debt_reduction +2.8%, volume +2.3%, capex +1.5% | `factory.py` + pead de-marketing on real publish dates | two-tier: book leg > 0.89 both halves (expect FAIL); descriptive leg t_cohort ≥ 2 | guidance-content chips (dossier + war room) + spec-sheet | 2s | season wks 2-3 (the ONE live research thread) |
| 4 | **Filing-latency tell** (E-13 kin) | `provenance_knowable` real BSE dates + `board_meetings` (D-01 live) + the season's own accumulating filings | pead.py; surprise = latency vs own filing history | \|t_cohort\| ≥ 2 AND survives placebo; else publish the null | "files late" flag on war room | 1-2s | season wks 3-4 (harvest, not pre-season) |
| 5 | **X-01 trade-size ratio column** (charter N3) | D89 survivor: Cliff's δ +0.329/+0.250 vs both controls | compute-on-read | already gate-cleared; glossary entry required | Screen+/dossier column + lane-cell visual | 0.5s | wk 1 |
| 6 | **E-03 insider disclosure drift** | `insider_events` nightly; episodes **re-count after AUD-08 supersede** (`d0879bd`); test POST-public drift (T+2 structural) | pead.py near-verbatim; loader at `footprint.py:200` | conviction-Q5 CAR60 vs matched controls, t_cohort ≥ 2 + placebo | insider event lens | 1-2s | NEXT (first evlib consumer) |
| 7 | **rs_phase rotation-ladder base rates** | nightly full universe; history on-read; research hits = 0 (never studied) | events de-overlap + pead CAR + same-date controls | tier-upgrade CAR22/60 vs controls, δ ≥ +0.20 or t ≥ 2 | base-rate strip on /dash/rotation | 2s | NEXT |
| 8 | **E-04 campaign arcs** | insider+SAST merged episodes (~57; re-count post-AUD-08); fresh pre-registration MANDATORY (ledger:76) | footprint clustering + pead CAR | arcs (≥2 filings, rising size) continue > single-filing base rate; Wolfe power rule | dossier arc timeline | 2s | NEXT |
| 9 | **E-06 BE→EQ release drift** | derivable from `series` transitions — no D-02 for the release leg | pead.py; event = first EQ day after BE spell | release cohort CAR ≠ controls; power rule | event lens (capacity-moat class) | 1-2s | NEXT |
| 10 | **E-11 dividend-surprise drift** | corporate-action dividends + `fundamentals_history` (1,983 syms × 24y) | pead.py | surprise-Q5 vs Q1, t ≥ 2 + placebo | event chip | 1-2s | LATER→NEXT |
| 11 | **Pledge-delta tail risk** (E-05 kin) | `shareholding_history` quarterly (post-Jul-21 flood widens) | pead cohorts on deltas | must beat the CCI-veto null (6.8 vs 6.9%) to ship | risk chip, never a veto ranker | 2s | post-Jul-21 |
| 12 | **M-05 survivorship + M-03 DSR wiring** | functions EXIST (`attribution.py:287-333, 507-523`) | wire into factory + publish | standing numbers printed with every run | Trust-page caveat numbers | 1s | NEXT (cheap) |

**Charter idea-bank corrections (amend by D-log, evidence attached):**
- **X-02 and the E-06 release leg do NOT need D-02** (series is in the bhav PK) — charter implies a feed dependency that doesn't exist.
- **X-06 Amihud is already half-built** — `amihud_22d` computed nightly (`mep_signals.py:286`); only the migration delta is new (on-read).
- **E-02 needs work, not a feed** — 130 upgrade events in hand; blocker is the 59-symbol scrip-mapping widen. After Jul-21 it is KPI study #4.
- **D-05 premise is contradicted by code** — `deals.py:11` says bulk/block HISTORY is "NOT available free"; charter says "NSE archive CSVs, 0.5s". Amend before anyone burns a session on it.

**The only book-shaped test left anywhere:** a pre-registered trailing/scale-out exit lever on the ONE
fundable corner (quarterly large-cap LOWVOL_MOM, net 1.02 @₹50cr, ceiling ~₹150cr) — defensive tilt,
never an alpha pitch. Everything else in the estate ships descriptive.

---

## 3. Discussed-but-unbuilt — the verified disposition

From 60 corpus ideas + 39 state claims + charter rows, verified against tree+git (32 formal verdicts;
key ones below). Verdicts: **BUILD-NOW** (this fortnight) / **NEXT** (Aug) / **DEFER** (needs a buyer/quiet
month) / **KILL** (failure-class or dead premise).

| Item (source) | Verdict | Why / evidence |
|---|---|---|
| D-02 ASM/GSM + D-03 price bands (charter N2) | **BUILD-NOW** (wk 1) | UNBUILT verified (zero code); 0.5s each; ASM state is context ON reaction names during season |
| D-04 SLB volumes (N2) | NEXT | UNBUILT; India's only short-interest proxy; not season-critical |
| D-05 bulk/block history (N2) | **KILL premise, re-scope** | `deals.py:11` — free archive doesn't exist; keep forward accumulation (live since `e6ab37d`) + re-scope X-03/P-01 to forward-only |
| N3 trade-size column · N4 evlib · M-02 placebo | **BUILD-NOW** | §2 rows 5+2 |
| P-03 spec-sheet page (Trust) | **BUILD-NOW** (wk 2) | 0/3 KPI is RED; content pre-exists in ledger; publishing the footprint FAIL is the brand |
| P-04 evidence pack v2 | NEXT (end-Jul) | assembles P-03 + replay-the-tape + SLA one-pager into the procurement artifact |
| AUD-38 as_of on /v1 → P-05 replay API | NEXT (early Aug) | wow factor high, but as_of plumbing first or the demo lies |
| P-06 MCP server | DEFER | tool layer exists (`c885962`, no mount); buys convenience not trust; build when a named buyer asks |
| Since-you-last-looked brief; Tracker/Position-Replay (product-strategy T1/T2) | DEFER (Aug) | retention features; replay-the-tape covers the demo need today |
| Smart-Money Tape (product-strategy) | NEXT via ownership-flow layer | supersede by postmortem BUILD-3 shape (`ownership_flow.py` + aggregators that exist but have zero imports) |
| PMS/IC-memo export · signed dossier (RFC-3161) · lens-attribution | DEFER | institutional artifacts with no live buyer; revisit at first pilot |
| Pat P2 (learning loop, methodology explainer, robustness) | DEFER | the P0 inversion bug is FIXED (`understand.py:404`); AUD-17 fuzzy-match stays a live demo-killer — fix wk 1-2 |
| CCI-debate threads: Engine-B mispricing book; BEAT/MISS anchor rehab; sector rubric | **KILL** (as books/factors) | F6 wrappers 0.02-0.10 net; F8 Gate B t=−3.71; admissible only as dossier polish |
| Chart T2/T3 remainder (PnF "(soon)", v5 panes, log scale) | DEFER (post-season) | Phase-2/3 core verified BUILT (`stock_chart.py`, `drawings_store.py`); polish only |
| Wolfe optional R&D (shallower entry, placebo close-out, Fib reconcile) | DEFER | BULL edge is selection (descriptive); BEAR decays −0.94% |
| Premium visuals Tier-1D/E, Tier-2 #7/#8, Tier-3 #10 | NEXT (see §8) | gross-vs-net dumbbell is the spec-sheet companion; footprint ladder is the top missing flagship |
| Dataset briefs (order-book, M&A, segment, capex NLP) | PARK | LLM extraction spend collides with ≤₹300/mo; wave-2/LATER stay parked |
| Kill-switch/governance completion | NEXT | the one queued institutional artifact with standing status |
| MTF stack (weekly/monthly bars, `1912f24`) | NEXT as chart timeframes | committed but not in vps-live `10-signals.conf` — schedule it or stop computing; NO weekly-DVPT alpha re-test without new pre-reg (MEP DSR 0.45→0.36 precedent) |

---

## 4. The reconciled calendar (resolves the panel's 3-way season contradiction)

The panel split three ways (INSIGHTS: study before Jul-09 · JUNK: one thread only · PRODUCT: operate-only).
**Ruling: PRODUCT's frame wins for the season path; research rides the quiet hours; X-02 gates every
delivery-cohort visual.**

**T-2 (Jul-07/08) — season-integrity only, then FREEZE the war-room path:**
1. Fix `earnings_triggers` dead pipe (15-min debug, postmortem §2d).
2. AUD-26 minimal paging: `OnFailure=hermes-alert@%n` on season-critical units + Telegram DM (test
   `api.telegram.org` reachability from the VPS first; fallback = louder DQ banner).
3. AUD-29 freshness gate: `After=hermes-bhavcopy` + refuse-if-stale `MAX(trade_date)` check on the
   reaction snapshot + evening scans.
4. **X-02-LITE**: BE/T2T flag/exclusion on the reaction board only ("delivery-confirmed" is its headline
   column and BE delivery is definitionally 100%).
5. One-line MTTR log: `filing_dt → snapshot_ts` per name at snapshot time (mechanism: §6.5).
6. Carry-forward queue-#1 ops verifications (Jul-05 concall run; backup timers; `install-systemd.sh --check`).
7. End-to-end war-room rehearsal (calendar → board_meetings → snapshot → page → popovers).

**Season wk 1 (Jul-09-13):** operate daily (~15min: XBRL bank-gate verdicts, `systemctl --failed`, MTTR
line) · N3 trade-size column+lane · D-02 + D-03 ingests · **full X-02 mask site-wide** · calendar
heat-strip + `stealth` table-controls token (§8 quick wins). (AUD-17 was queued here; landed `292a069`
mid-review — verify live, don't redo.)

**Wk 2 (Jul-14-20):** P-03 spec-sheet page (3 sheets incl. footprint FAIL, now carrying live MTTR numbers) ·
N4 evlib + M-02 placebo · #8 disclosure line on guidance surfaces + AUD-48 scrape-path shrink · PROJECT_STATE
hygiene pass (§6.6).

**Jul-21+ (Reg-31 flood):** pledge-coverage check (was 76 syms) · E-02 pre-registered after the 59-symbol
mapping widen (KPI study #4) · E-14 becomes possible.

**Wks 3-4:** concall growth-intent walk-forward (§2 row 3 — the one live research thread) · filing-latency
study on the season's own filings · E-03 (post-AUD-08 re-count) · CAR fan ships **only after** full X-02 ·
M-05/M-03 wiring · P-04 assembly begins.

**Explicit gate:** no delivery-cohort visual (CAR fan `deliv_x` cells, MEP/DVPT strips) ships before the
full X-02 mask lands. Post-season: wave-2 feeds, index diet (Ramana), dashboard carve-out, native-shell
migration, chart polish.

---

## 5. Junk — what to avoid, what's dead, what's already built

### 5.1 Falsified (BLOCKING — cite these numbers before any re-attempt)
The full table lives in `docs/strategy-ledger.md:61-84`; the class rules:

- **Flat-cost Sharpe is an illusion** — momentum 1.29→**0.09 net**; C-BLEND 1.32→**0.17 @₹50cr / −0.30 @₹100cr** (pre-registered kill met 2026-07-05c). No number counts until it passes the participation model at stated AUM.
- **Calendar-time ranking + every event-book wrapper are closed** — PEAD all constructions 0.02-0.10 net (hedged −0.58) vs bench 0.85, incl. the pre-registered within-season last cell (0.06). Drift is real ONLY descriptively (SUE-Q5×DELIV-T3 CAR60 +7.62%).
- **Front-detection is structurally dead in India** — footprint gate 1/4; 764/947 episodes had NO pre-public window (SEBI T+2). X-08-style composites inherit this unless reframed post-public (E-03/E-04).
- **Ranked credibility is dead twice** — HIGH−LOW −10% @12m inverse; Gate B t=−3.71. Never spend the ~₹2,500 corpus completion for factor use.
- **Delivery-% LEVEL is a three-times-dead house signature** (DELIV_MOM 0.76-0.85 · MEP DSR 0.45→0.36 · footprint δ≈+0.07). **BOOK_YIELD stays the hardest reject** (α negative, β1.54, MaxDD −82%). Momentum sleeve headroom ≈ 0 (r up to 0.95; β-not-selection t=1.99); C is the only orthogonal sleeve — future sleeves must be non-price axes.
- Wolfe/harmonic BEAR = tail-tags (−0.19% decaying to −0.94%); Launchpad swing books negative @1.5× cost; velocity gate 0.73; +VAL guard cuts 1.13→1.03; ACCEL/PULLBACK standalones catastrophic.

### 5.2 Already built — stale "open" markers (do NOT rebuild; fix the docs)
Dataset-A June tail (confirmed clean, 699→1,559) · bulk/block ingester (`e6ab37d` + timer) · insider rebuild
(`b136d3f`) · glossary trio live (`0fe5a1a`/`163cd29`; `0ce09a9`/`ca223c4` dangling) · /dash/compare P0
(`ddf7640`) · pledge reader sync (`60ea594`) · C dossier fact (`cf2a8cb`) · nav de-fork captured (`1a9369e`;
residual lens_registry diff is CRLF-only) · Wolfe ◀▶ stepper (`74faeee`) · charting Phase-2 + harmonic
(`cda2d42..ec2f1ab`) · site-wide chart rollout (`c736f3a`) · war room N1 · **Pat overvalued inversion**
(`understand.py:404`) · TL;DR claims (5y backfill "not executed", "Screener on-demand") both false post-D78/D82.
**Session 78 is missing from PROJECT_STATE** — the seam fixes ARE live (`23338a0`/`4f4fed0`); record the
entry, never redo the work.

### 5.3 Unlikely to work (failure-class inheritance — don't start)
X-08 pre-public composite (F7) · Engine-B mispricing book (F6) · CCI factor rehab / corpus spend (F8) ·
concall growth-intent as a top-N BOOK (F3/F6 — run the walk-forward, expect the descriptive result to be
the win) · new momentum sleeves/lookbacks (collinearity wall) · exit-lever free-lunch reading (S4 negative
@1.5×; Cap% 18-22% is a property of monthly exits) · pattern-scoring books (F11) · fund-shaped pitches and
white-label performance reporting (charter thesis: the fund-shaped product is a mirage).

### 5.4 Anti-patterns (standing engineering junk list)
Vendor/Screener extension (#8) · LLM screening (#4) · Sonnet/Opus in timers (#3) · absolute-rupee thresholds ·
share-count cross-time metrics (#5) · factors on raw price LEVELS (anchor audit: anchors differ 20-24%) ·
any run without a pre-registered gate + ledger entry · storing derivable series (16.2GB doctrine) ·
`setup-news.sh` on VPS (AUD-28) · mid-day `systemctl start` of hermes timers (AUD-95) · restarting hermes-api
while a writer runs · write txns across network I/O (the site-wide-000 outage) · full-file overwrites of
dashboard/v2_surfaces/lens_registry on the shared tree · orphan URLs / per-page nav forks (D80) · a third
glossary system (AUD-71) · `_shell` wraps without the sys.modules sweep + own WS map · selftest-only
verification (walk the journey, S78) · committing without the same-commit PROJECT_STATE update · trusting
open/done markers without kickstart-pick-verify.

---

## 6. Managerial + product deep dives

### 6.1 Charter §9 KPI scorecard (honest)
| KPI | Status | Gap |
|---|---|---|
| Filing→surface MTTR same-evening | **AMBER** | plumbed (war room self-refreshing) but unmeasured + unalerted (`earnings_triggers` dead pipe; AUD-26/29) |
| Feed-freshness SLAs green on Trust | **AMBER** | checks exist (`39fec05`, AUD-21 `80a9494`); no SLA board renders them; AUD-25 matrix incomplete |
| Spec-sheets 3 by end-Aug | **RED 0/3** | content pre-exists in the ledger; P-03 is pure assembly |
| Pre-registered studies ≥4/qtr | **GREEN** | 3 ledgered in week 1 of Q3; E-02 makes 4 |
| XBRL gate pass-rate trend | GREEN mechanism | keep a weekly number from Jul-09 |
| API ≤₹300/mo | GREEN | concall backlog correctly parked as a Ramana decision |
| Zero #8 violations | **AMBER** (was RED; `f45bf81` closed the glossary leg) | AUD-48 scrape paths alive + **no disclosure line on the 98.6% Screener-discovered concall corpus** where guidance surfaces |

### 6.2 Audit triage (of 92 open: 22 P1 · 53 P2 · 17 P3)
- **Season-load-bearing NOW:** AUD-26 (never pages) · AUD-29 (stale-as-fresh) · AUD-13/14 (bhav archive silently
  marks failed days done / throttle-as-holiday — permanent holes in the moat dataset) · AUD-25 residual.
- **Pilot-load-bearing (July):** AUD-22 (attribution evidence on leaky inputs — re-run; PIT honesty IS the
  wedge) · AUD-38 (no as_of on /v1 → client can't run their own leak audit) · AUD-37 (metering not
  audit-grade) · AUD-48 (#8 disclosure). (AUD-17 Pat fuzzy-match closed mid-review, `292a069`.)
- **Deferrable:** B6 UI chrome (63,66-72) · repo hygiene (79-84) · AUD-46 perf · schema consolidation (99/100) · all P3s.

### 6.3 Ramana-blocked (surface, do not self-serve)
1. **AUD-02 off-box backup destination** — on-box DR proven ×2, but the 14-year primary archive dies with the
   disk. Decide: rclone remote / Hostinger snapshot / periodic `download-from-vps.bat` discipline.
2. **AUD-44 raw_json NULLing (~3GB)** — DB-destructive; only after AUD-02 lands.
3. **mep/cpr full-history reclaim (~4.3GB) + index diet** — doctrine-#5 judgment (postmortem §11.3).
4. **₹900-1,700 concall LLM backlog** — paid spend; only the FREE regex pass is pre-authorized.
5. **Data-licensing/redistribution posture** — §6.4.

### 6.4 Licensing — the procurement deal-killer, framed for decision
What's clean: SEBI/XBRL/RBI statutory filings; **derived analytics/evidence** (scores, event ledgers,
provenance measurements) are Patearn's own work product. What needs a decision: **redistribution of
exchange-sourced raw data** (bhav-derived rows, quotes) inside a PAID product — exchanges license market-data
redistribution; the safe interim posture is **sell access to analytics surfaces + derived event ledgers,
never raw-feed redistribution**. Obligations regardless: the #8 disclosure line on the Screener-discovered
corpus (98.6%) wherever guidance renders. **Artifact needed before any paid pilot:** a one-page rights-posture
memo (which surfaces expose raw vs derived; exchange-data stance; corpus disclosure) that Ramana signs off.
Prep is one session; the decision is his.

### 6.5 MTTR mechanism (designed, so it stops being a slogan)
At reaction-snapshot write: log `(symbol, filing_dt, snapshot_ts)` per new name → nightly roll-up of
median/p95 lag into `data_quality_runs` → one chip on the war room + Trust page ("median filing→surface:
same evening / N hrs"). ~0.5s total, live from season day 1.

### 6.6 PROJECT_STATE/docs hygiene (one pass, week 2)
Reconstruct missing S78 entry · backfill S79/S80x commit hashes · sweep the 13 stale-open contradictions
(§5.2) · fix the TL;DR two false claims · retire `docs/SESSION-72-CARRYFORWARD.md` (owner session) · note the
D68/D79-D80 numbering collisions · **update `strategy_runs` + `/dash/testing`** — it still renders "none
beats B&H net" (superseded 2026-07-02) and lacks the C-BLEND champion + PEAD-fail rows: a false claim on a
trust surface. Also amend charter by D-log: D-05 premise; X-02/X-06/E-02/E-06 corrections (§2).

---

## 7. Missed data & insights — dormant-asset disposition table

| Asset (state) | Disposition |
|---|---|
| `company_profile` 3,797 briefs (write-only, ₹ paid) | **SURFACE** — one dossier template line; cheapest UI win in the estate |
| `capital_allocation_scores` sub-metrics (roiic, dilution_drag, growth_efficiency) | **SURFACE** — free C-tab depth on dossier |
| `provenance_lag_audit` (written, never read) | **PUBLISH** — Trust-page standing number ("our PIT clock error, measured"); pairs with M-05 |
| `fii_dii_flows` (daily ingest, zero readers) | **SURFACE** — market-context strip on cockpit/rotation; display-only (n=1 series, never gate-able) |
| `signal_events` bus (built, never scheduled) | **WIRE** — "what changed today" feed; underpins P-02 SLA (0.5-1s) |
| `stock_oscillators` (Pat reads it; NO scheduler runs `oscillators.py`; DQ blind to it) | **FIX (correctness)** — schedule + add to `chk_derived_liveness`; verify VPS unit absence first (git-owned units say absent) |
| `accum_screen` (nightly CPU, zero readers) | **SURFACE-or-KILL** — one D66-fenced descriptive list on Screen+ (0.5s); if unused in a month, stop the job |
| `earnings_triggers` (wired-but-zero) | **FIX pre-season** (15-min debug) |
| `concall_coverage` (purpose-built, 0 rows, no populator) | **WIRE** — nightly pure-SQL populator (zero LLM) |
| `corporate_actions`=0 + `security_events`=0 (dead NSE archive 404s) | **RESURRECT via BSE-announcements pattern** (`concall_bse.py`), weeks 2-4; interim = `adjust.py` inferred factors + the DQ WARN (`39fec05`); never the dead archive, never setup-news.sh |
| `avg_dvpt_5d..365d`, `total_value_today`, `ratio_today_vs_avg_30d`, 2 sector-RS bools | **KILL (stop-write)** — grep-gated; keep the 2 READ RS bools (`rs_vs_sector_above_200ma`, `rs_vs_broad_new_52w_high`) |
| Deals `client_key` normalization | **BUILD-NOW** — every unlocked day loses joinable counterparty history (grep: absent) |
| `strategy_runs` missing champion+failure rows | **APPEND** with the hygiene pass (§6.6) |
| 18 dormant thematics (RS but no capture/RRG) | **ALLOWLIST** — one-line edit, free coverage |
| `fno_oi_signals` quadrant (surfaced, never studied) | keep descriptive; base-rate study LATER (confirms-coincident: 7pp→3pp) |
| `participant_oi` (no forward edge, n~609) | **NOISE-MAP** verdict stands; no study until the 10y F&O backfill lifts n |
| `rs_extras` divergence/early-signal flags (never studied) | **STUDY** — §2 row 7 (rotation ladder) |
| `capture_signals` persistence | descriptive; optional base-rate LATER |
| `sast_pledge_events` (weeks-deep) | keep; add DQ sanity row; distress-spiral board post-Jul-21 |
| `em_cache` pickle | leave (research cache; covered by backup units) |
| MTF weekly/monthly stack (`1912f24`, unscheduled) | **WIRE as chart timeframes or stop computing**; no alpha re-test without new pre-reg |

---

## 8. Analytics, charts, design (data must EARN the visual)

**Ranked new visuals** (data-in-hand × payoff × season relevance): (1) **event-time CAR fan** on
/dash/results-reactions — spaghetti + cohort mean + IQR band per beat×delivery cell, the falsification line
(net 0.10 vs 0.85) printed ON the chart; ships with evlib, **after X-02** (2) **results-calendar heat-strip**
(board_meetings × rs_rank × watchlist) — pre-Jul-09, S (3) **freshness-SLA census wall** — ~18 `chk_*` × last
30 runs as green/amber/red tiles; makes the §9 KPI literally green-on-a-page; new Trust lens via registry
(4) **trade-size lane cell** riding N3 (rsband lane idiom) (5) **gross→net dumbbells** on /dash/testing —
momentum 1.29→0.09 as one devastating picture; THE trust chart (6) **DVPT footprint ladder** (Tier-1 D):
today's print vs 10-rung R/P ladder + D31 institutional zones — computed nightly, studied nowhere; results
days ARE DVPT-spike days (7) participants 4×3 stance small-multiples (8) credibility-vs-price **rank-gap
slopegraph** (descriptive form per product-strategy §9.4) (9) **event markers on the dossier chart** via LWC
`setMarkers` (native 4.1.3, zero new deps) (10) cap-alloc waterfall (Tier-1 E).

**Thin-page upgrades, cheapest first:** `stealth` → `table_controls._PAGES` (one token,
`table_controls.py:21`) · momentum-scan same + gloss · divergence/early-signals get real tables + 14-pt
mini-RRG comet cells (`mini_rrg.py:33`) · sector-momentum beeswarm · growth %-of-mcap dot strip ·
harmonic/wolfe %-to-PRZ lane cells · wire 30-day density strip · rotation micro-comets.

**Design system order:** Indian number grammar `fmt_inr()/fmt_delta()` in ui_kit (XS, highest
premium-per-line) → **provenance chip** (as of · knowable_at · settled) mandatory on every new visual — the
chip IS the trust posture → glossary sweep of the 12 bare modules → rotation color-contract fix →
tap-to-pin tooltips for the hover-only server-SVGs → new pages on native `ui_kit.shell`, stop feeding
legacy `_shell` wraps → de-collide /dash/momentum vs /dash/momentum-scan labels → converge `dq_banner._ACT_WS`
onto lens_registry keys.

**Methodology-as-product:** placebo fan (grey shuffled-dates band + "inflation ×N" chip) behind every CAR
chart · survivorship censoring funnel (1,706/1,722 delisted lack fundamentals; 773 left-censored at the
2004-07-23 floor) rendered, not footnoted · the pre-registration ledger page IS P-03's spine (hypothesis
hash · pre-reg date · gate · result, failures displayed).

All of it: server-SVG or existing LWC, zero new JS deps, compute-on-read or bounded snapshots, every mount
a Lens record.

---

## 9. Panel-claim corrections made during reconciliation

1. Pat "overvalued inversion live bug" → **already FIXED** (`src/pat/understand.py:404-410` + eval_set regression). Removed from correctness queue.
2. AUD-08 insider supersede → **landed** (`d0879bd`+`90d37b4`) during the review; E-03/E-04 episode counts must be re-derived on deduped data.
3. Concall PIT clocks → **landed** (`3297a50`); §2 rows 3-4 upgraded from "blocked on backfill" to "in hand".
4. Guardrail-#8 KPI → RED softened to AMBER (`f45bf81`/`4691684` closed the glossary leg; scrape paths + disclosure line remain).
5. Oscillators staleness → **confirmed** (no scheduler in git-owned units; Pat reads the table) — stays in the correctness queue with a VPS verify step.
6. AUD-17 Pat fuzzy-match → **landed** (`292a069`) while this review was being committed. Fourth mid-review invalidation; the §1 protocol is not optional.
