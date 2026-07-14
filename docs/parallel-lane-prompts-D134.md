# D134 Parallel-Lane Prompt Pack — the autonomous execution harness for the analytics-company plan

> **Lifecycle: TRANSIENT (run-book).** Paste-ready, self-contained session prompts for every
> component of `docs/patearn-analytics-company-plan.md` §4/§6, plus the relay protocol that makes
> sessions trigger one another without losing the ratings/cost/timing metadata. Registered in
> `docs/DOC_INDEX.md` (D. RUN-BOOK). **Retire condition:** all lanes below show LANDED in the
> plan §4 Status column and their session records live in PROJECT_STATE — then fold residue into
> the plan and `git rm` this file.

---

## 0. Orchestration model (how this runs autonomously)

- **Metadata is single-sourced.** Every lane header carries its META line (Importance ·
  Criticality · Timing · Cost) **copied from plan §4, which stays the source of truth** — a lane
  session re-reads its plan §4 row at boot and reports against it at wrap. Never re-derive or
  re-negotiate ratings inside a lane.
- **Two dispatch modes.** (a) *In-session background agents* (worktree-isolated) for disjoint
  new-module builds — used by the S149 orchestrator for wave 1 (lanes B, C, D build + F audit).
  (b) *Fresh parallel Claude Code sessions* — paste a lane block below verbatim; it is fully
  self-contained.
- **The relay (sessions trigger one another).** At wrap, every lane session MUST: (1) mark its
  lane LANDED/BLOCKED in this file's §1 ledger AND flip its plan §4 Status; (2) prepend its
  outcome to `docs/NEXT-SESSION-CARRYFORWARD.md` **including the next lane's ID as the explicit
  next pick**; (3) record the session in PROJECT_STATE §Session log (same commit). The
  carry-forward is the baton — the next autonomous session boots from it per SESSION-PROTOCOL.
- **Integration is SERIALIZED.** Build lanes commit in their worktree/branch and never push,
  never deploy, never touch shared/forked files. LANE-R (reconcile+integrate) is the only lane
  that merges branches, edits shared files, and deploys — one at a time, gates green, writer-safe.
- **Universal bans (every lane, no exceptions):** no `git push`; no VPS/ssh access unless the
  lane block explicitly grants read-only; never edit the forked trio
  (`dashboard.py`/`cockpit.py`/`main.py`) or `lens_registry.py`/`v2_surfaces.py`; no systemctl
  start/enable (AUD-95); no `.env`; production `src/` code is **stdlib-only** (VPS venv has no
  numpy); cheap models or no LLM in anything scheduled (Guardrail #3); commits touching `src/`
  in a worktree append the repo's `state:skip` convention and defer the PROJECT_STATE entry to
  LANE-R (precedent `b5e9e6d`); cite `docs/strategy-ledger.md` before anything strategy-shaped.

## 1. Lane ledger (update at every wrap)

| Lane | Component (plan §4) | META (Imp·Crit·Timing·Cost) | Status |
|---|---|---|---|
| B | Cost-ledger + estate heartbeat | 7 · **8** · NOW · ₹0 | dispatched S149 (wave 1) |
| C | Licence-class registry + feed/signal manifests | 8 · **8** · next · ₹0 | dispatched S149 (wave 1) |
| D | Review Inbox + judgment corpus | **9** · 7 · next · ₹0 | dispatched S149 (wave 1) |
| F | Time-machine capability audit | **8** · 5 · mid · ₹0 | dispatched S149 (wave 1, read-only) |
| R | Reconcile + integrate + deploy wave 1 | inherits max of merged lanes | waiting on wave 1 |
| E | Auto-analyst event briefs | **9** · 6 · after D+R · ₹100–300/mo capped | prompt ready (§E) |
| G | Entity graph v1 | **8** · 4 · mid · ₹0 | prompt ready (§G) |
| H | Rule-lab design | **8** · 4 · later · ₹0 | prompt ready (§H) |
| I | Real-time seam interface | 7 · **6** · design next · ₹0 (opt ₹500/mo) | prompt ready (§I) |

---

## LANE-B — S150 · Cost-ledger + Estate Heartbeat

**META (plan §4-B):** Importance 7 · Criticality **8** (driving) · Timing NOW · Cost ₹0.
**Mission:** the machine's budget and health become ONE positive morning line, machine-tracked.

```
You are LANE-B of the D134 program in D:\Hermes. Boot: read docs/patearn-analytics-company-plan.md
§4-B + §5.4, docs/parallel-lane-prompts-D134.md §0 bans + §LANE-B, and the docstrings of
src/automation/board_health.py, signal_alerts.py, signal_alert_telegram.py, digest.py. Do NOT
read PROJECT_STATE history beyond the top session entry.

BUILD (new files only; stdlib-only; own tables via CREATE IF NOT EXISTS — never edit db.py):
1. src/automation/cost_ledger.py — table cost_ledger(ts, job, model, tokens_in, tokens_out,
   inr_estimate, note); record() API + a RATES constants dict (₹/Mtok per model, editable) +
   month_to_date() + CLI --report/--selftest. Budget law: expose cap_status(cap_inr) returning
   OK/AMBER/BREACH per plan §5.4 (default cap ₹2,500 runtime).
2. src/automation/estate_heartbeat.py — compose ONE line: board_health verdict + key-table
   freshness (max dates: bhavcopy_rows, stock_signals, fundamentals, signal_events) + alert-rail
   critical count (reuse signal_alerts.active_alerts) + cost_ledger MTD vs cap → "estate GREEN|AMBER|RED · …".
   --dm sends via digest._send with a fire-once-per-day guard (own table heartbeat_sent);
   --print for dry runs. Design to run ON the VPS nightly; zero LLM.
3. scripts/systemd/vps-live/hermes-heartbeat.service + .timer (03:30 UTC daily, Persistent=false,
   hardened like hermes-board-health siblings). Files only — installation/enabling is LANE-R's.
4. tests/test_cost_ledger_heartbeat.py — hermetic temp-DB tests (≥10 contracts: record/MTD/cap
   bands/one-line format/fire-once/empty-DB grace).

DONE-BAR: pytest file green + both module --selftest green. Commit in THIS worktree (explicit
paths, message "feat(ops): S150 LANE-B cost-ledger + estate heartbeat  state:skip"), do NOT push.
REPORT: branch + SHA + files + test tally + the exact sample heartbeat line + open questions.
```

## LANE-C — S151 · Licence-class registry + feed/signal manifests

**META (plan §4-C):** Importance 8 · Criticality **8** (driving) · Timing next · Cost ₹0.
**Mission:** convert tribal feed wiring into declared contracts; make the legal data boundary mechanical.

```
You are LANE-C of the D134 program in D:\Hermes. Boot: read docs/patearn-analytics-company-plan.md
§2 (L1/L3) + §3.4(3) + §4-C, docs/parallel-lane-prompts-D134.md §0 bans, then enumerate feeds
from src/automation/ module docstrings (bhavcopy, indexes, deals, corp_actions, equity_list,
surveillance, slb, credit_ratings, insider_events, sast_events, shareholding_xbrl/history,
concalls, concall_bse, news_feed, results_calendar, fundamentals_xbrl, fno_oi, participant_oi,
security_master, mtf_signals...). Read docstrings only — protect context.

BUILD (new files only; stdlib-only; no DB access needed):
1. src/automation/feed_manifest.py — @dataclass Feed(key, module, source_org, cadence,
   licence_class, knowable_rule, fence_status, tables, notes) + FEEDS: dict for EVERY acquisition
   feed found (all current ones are 'public-archive' or 'derived'; enum: public-archive |
   licensed | personal-broker | derived). Plus SIGNALS: dict for ~10 flagship derived series
   (dvpt, rs suite, mep, cpr, wolfe, launchpad, seasonal, internals, momentum/factor engines):
   Signal(key, module, inputs, validation_status, fence, ledger_ref). Statuses MUST match
   docs/strategy-ledger.md verdicts verbatim (descriptive-only stays descriptive-only).
2. tests/test_feed_manifest.py — contracts: every manifest module imports/exists; licence_class
   in enum; coverage ratchet (FEEDS count >= the number you catalogued — a new fetcher without a
   manifest row fails); THE LICENCE GATE: no feed with licence_class in {licensed,
   personal-broker} may be imported/referenced by any src/web/*.py (source-scan; document the
   v1 approximation in the test docstring).

DONE-BAR: pytest green; selftest prints the manifest table. Commit in THIS worktree ("feat(data):
S151 LANE-C feed/signal manifests + licence gate  state:skip"), no push. REPORT: branch + SHA +
feed count + signal count + any feed you could NOT classify (list, don't guess).
```

## LANE-D — S152 · Review Inbox + judgment corpus

**META (plan §4-D):** Importance **9** (driving) · Criticality 7 · Timing next · Cost ₹0.
**Mission:** the human-verification layer — one queue for everything the machine wants Ramana to judge; every decision becomes labeled data.

```
You are LANE-D of the D134 program in D:\Hermes. Boot: read docs/patearn-analytics-company-plan.md
§2 (L5) + §4-D, docs/parallel-lane-prompts-D134.md §0 bans, and the docstrings of
src/automation/theme_tags.py (tags-review precedent), signal_alerts.py (ack precedent),
tracker_alerts.py. This lane builds the PRIMITIVE only — no web surface (lens registration is
forked-file territory; LANE-R wires the surface per docs/SURFACE-PLAYBOOK.md later).

BUILD (new files only; stdlib-only; own tables, never edit db.py):
1. src/automation/review_inbox.py — table review_items(id, kind, ref, title, payload_json,
   evidence_url, status pending|approved|rejected, note, created_at, decided_at). API:
   submit(kind, ref, title, payload, evidence_url) idempotent on (kind, ref);
   decide(item_id, verdict, note); pending(kind=None); corpus(kind=None, since=None) — the
   judgment dataset; agreement_stats(kind) — approve-rate per generator family. CLI:
   --pending/--decide/--stats/--selftest. Docstring records the design intent: adapters for
   tags-review / alert-ack / auto-analyst drafts / rebalance diffs plug in LATER without schema
   change (kind field is the extension point).
2. tests/test_review_inbox.py — ≥12 hermetic contracts (idempotent submit, double-decide guard,
   corpus filters, stats math, empty-DB grace, payload round-trip).

DONE-BAR: pytest + selftest green. Commit in THIS worktree ("feat(judgment): S152 LANE-D review
inbox + judgment corpus  state:skip"), no push. REPORT: branch + SHA + API surface + test tally +
your recommended FIRST producer to wire (with why).
```

## LANE-F — S154 · Time-machine capability audit (read-only)

**META (plan §4-F):** Importance **8** (driving) · Criticality 5 · Timing mid · Cost ₹0.
**Mission:** inventory which lenses can already answer "as of any date", and the 5 cheapest upgrades.

```
You are LANE-F of the D134 program in D:\Hermes — STRICTLY READ-ONLY on code; your only write is
the NEW file docs/time-machine-audit.md (do NOT edit DOC_INDEX; do NOT commit — the orchestrator
commits). Boot: read docs/patearn-analytics-company-plan.md §4-F, then src/web/lens_registry.py
(the routed lens list) and each view module's docstring/read-queries (docstrings + targeted greps
for 'asof'/'as_of'/snapshot table names — do not read whole files).

DELIVER docs/time-machine-audit.md with a "Lifecycle: TRANSIENT" banner (retire → fold into plan
§4-F): (a) a table of EVERY routed lens — asof_capable yes|partial|no + the mechanism or blocker
(PIT query vs latest-snapshot table vs live-read); (b) the proposed asof_capable flag map ready to
paste into lens metadata; (c) the 5 cheapest upgrades ranked by user value with a 1-line approach
each; (d) any lens whose page CLAIMS historical replay it can't honestly do (honesty first).
REPORT: the summary counts (yes/partial/no) + the top-5 list + the doc path.
```

## LANE-R — Reconcile + Integrate + Deploy (serialized; run when wave 1 reports are in)

**META:** inherits the max criticality of merged lanes (8) · Timing: immediately after wave 1.

```
You are LANE-R of the D134 program in D:\Hermes — the ONLY lane allowed to merge, edit shared
files, and deploy. Boot: full SESSION-PROTOCOL boot + docs/parallel-lane-prompts-D134.md §1
ledger + the carry-forward S149-b block (branch refs live there).

SEQUENCE (strictly serial):
1. RECONCILE main↔origin first (S149 flag): local-only 216db7b/0b637ed/bce01cb + patch-twin
   a781669≡29e4169 (auto-drops); two lanes both used "S148" — renumber in the session log if
   needed. git pull --rebase, resolve the trivial prepend conflicts (keep both), verify
   git log --oneline sanity, push FF.
2. MERGE wave-1 worktree branches ONE AT A TIME (B → C → D): merge, run the FULL suite +
   Gate 0, fix trivial breakage only (anything structural → report back, don't improvise).
3. PROJECT_STATE: one S150–S152 session-log entry per merged lane (the state:skip debts) +
   §Key file paths rows + plan §4 Status flips + this file's §1 ledger.
4. COMMIT + PUSH (FF only).
5. DEPLOY per vps-deploy-reality memory: scp the NEW isolated modules (LF-clean, fork-check
   irrelevant — new files), install-systemd.sh for the heartbeat unit (daemon-reload path, NO
   start — AUD-95; never restart 13:55–14:15 UTC; writer-guard BLOCKS not prints), then
   on-box --selftest for each module + one real heartbeat --print.
6. WIRE the first heartbeat: enable timer at a safe hour per install-systemd conventions, or
   document the manual arm step for Ramana if enabling is judged unsafe today.
7. RELAY: carry-forward top block → next picks = LANE-E (needs D live) and LANE-I; spawn/queue
   their prompts from docs/parallel-lane-prompts-D134.md.
```

## LANE-E — S153 · Auto-analyst event briefs (run AFTER LANE-R lands D)

**META (plan §4-E):** Importance **9** (driving) · Criticality 6 · Timing after D+R · Cost ₹100–300/mo hard-capped.

```
You are LANE-E of the D134 program in D:\Hermes. Boot: plan §2 (L6) + §4-E + §5.4; this file §0
bans; docstrings of review_inbox.py, cost_ledger.py (both live by now), results_reactions/
concall_bse (the results-event source), news_tagging. Constraint stack: descriptive-only fence
vocabulary (infographics.fence), the compliance lexicon (tests/test_compliance_language_gate.py)
must pass over your templates, Haiku/Gemini-Flash class models ONLY, hard monthly cap read from
cost_ledger.cap_status (degrade to pure-template text at cap), every brief carries
"AI-drafted, human-reviewed" + generation date, grounded ONLY in our tables with per-number
source links. BUILD: src/automation/auto_analyst.py — ONE event family first (results landed →
6–10 line brief) → review_inbox.submit(kind='brief'); publishing of APPROVED briefs to the wire
is a separate small step LANE-R wires. Tests: template path hermetic; LLM path behind a flag.
DONE-BAR: a real brief drafted from the latest results event on the box IN THE INBOX, ₹ logged
to cost_ledger. Commit conventions as §0.
```

## LANE-G — Entity graph v1

**META (plan §4-G):** Importance **8** (driving) · Criticality 4 · Timing mid · Cost ₹0.

```
You are LANE-G of the D134 program in D:\Hermes. Boot: plan §4-G; this file §0 bans; docstrings
of insider_events.py, sast_events.py, deals.py, credit_ratings.py, concall_bse.py,
security_master.py. BUILD (new files; stdlib): src/automation/entity_graph.py — table
entity_edges(src_kind, src_id, dst_kind, dst_id, edge_kind, first_seen, last_seen, source_ref)
+ extractors that DERIVE edges from tables we already have (insider filer↔company,
SAST acquirer↔company, deal counterparty↔company, rating agency↔company, promoter-pledge
chains); idempotent rebuild; neighborhood(symbol) read API. Fence: descriptive relationships
with source refs, no scoring. Tests ≥10 hermetic. Surface = LANE-R later. Ledger-check first
(failure-ledger skill): relationship ANALYTICS is new ground, but any predictive claim needs
its own prereg — do not add one.
```

## LANE-H — Rule-lab design (design doc only)

**META (plan §4-H):** Importance **8** (driving) · Criticality 4 · Timing later · Cost ₹0.

```
You are LANE-H of the D134 program in D:\Hermes. Deliver docs/rule-lab-design.md (TRANSIENT
banner; retire→build session): the closed-vocabulary rule grammar (Pat pattern), the mapping
onto the existing evidence factory (research/explosive_moves/factory.py + prereg.py + placebo +
cost model + capacity), the honest-verdict output object (reuses ledger vocabulary), the
personal-first surface sketch (SURFACE-PLAYBOOK checklist pre-filled), and the SEBI boundary
note (user-directed analysis = analytics, not advice — plan §3). No code. Cite the ledger's
BLOCKING table verbatim where the grammar could express a known-dead idea (auto-cite in
results).
```

## LANE-I — Real-time seam interface

**META (plan §4-I):** Importance 7 · Criticality **6** (driving) · Timing design next · Cost ₹0 now (opt ₹500/mo).

```
You are LANE-I of the D134 program in D:\Hermes. Boot: plan §4-I + §3.4(3); this file §0 bans.
BUILD (new files; stdlib): src/automation/intraday_adapter.py — the INTERFACE only: an abstract
QuoteSource (snapshot(symbols) -> normalized rows), a bounded rolling-window store (raw ticks
NEVER enter hermes.db main tables — space doctrine; own intraday_window table with max-age
pruning), licence_class='personal-broker' declared in feed_manifest (extend LANE-C's FEEDS —
coordinate via manifest row, not code edits elsewhere), and a NullSource + T0LiteSource stub
(EOD preliminary files, ₹0). NO Kite key wiring (that is Ramana's paid activation decision).
The licence gate must keep this feed OFF every public surface by construction — add the test.
Tests ≥8 hermetic.
```

---

## 2. Wave-1 dispatch record (S149 orchestrator — update as reports land)

| Lane | Mode | Isolation | Result |
|---|---|---|---|
| B | background agent | worktree | pending |
| C | background agent | worktree | pending |
| D | background agent | worktree | pending |
| F | background agent | read-only, main tree (doc only) | pending |
