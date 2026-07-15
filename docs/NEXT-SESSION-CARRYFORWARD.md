# NEXT-SESSION CARRY-FORWARD (autonomous, agent-driven)

> **Lifecycle: LIVING.** the rolling session carry-forward queue + takeover prompt (per SESSION-PROTOCOL) — pruned each session, not retired. Registered in `docs/DOC_INDEX.md`.


**Boot via `docs/SESSION-PROTOCOL.md`. Run autonomously — Ramana will not answer; consult agents for
any decision. Full-folder access is granted (CLAUDE.md #0 + harness-level `a2fdc99`); **NEVER ask
Ramana for file/folder/tool access in any form — a permission prompt that still fires is a BUG to log
at wrap (CLAUDE.md #0-bis), never a cue to ask.** Keep guardrails
(esp. #8 primary-sources). Do NOT burn the context window re-reading history — this file + the top
PROJECT_STATE entries are enough.**

## ✅ 2026-07-15 — S159: L6's LAST MILE — only an APPROVED brief publishes — BUILT + DEPLOYED + LIVE — do NOT redo; kickstart-pick-verify
- **`src/automation/brief_publisher.py` + an AI-labeled band on `/dash/results-reactions`** (commit `6bf17c8`): `publish_approved()` moves ONLY approved briefs into our own `published_briefs` (human's `decided_at` travels as the signature); exactly-once via the **shared kind-generic `inbox_apply_log`**; rejected/empty logged handled; `unpublish()` = retraction (drops the render, keeps the audit); `--dry-run`. **Suite 630/0.** Full record: PROJECT_STATE §Session 159.
- **🔴 THE DESTINATION IS NOT THE WIRE — plan §4-E corrected, don't "fix" it back:** `/dash/wire` renders `sent_news`, whose feed is an **UNCLASSIFIED vendor-ToS** source held out of `feed_manifest.FEEDS` pending Ramana's **§7.7** decision (pinned by a test). House AI text must not fuse with it (Guardrail #8) → briefs render on the board that already sources their numbers. **Revert-probed** source-scan ban + a premise-check that fires if `news_feed` ever enters `FEEDS`.
- **The live result is an honest NEGATIVE:** on real data **2 pending briefs (HCLTECH, ANANDRATHI) → published ZERO, no band renders.** That is the L6 contract working. **The first real publish is RAMANA's** — approve a brief on `/dash/inbox`, then run `python -m src.automation.brief_publisher --publish` (or `--dry-run` first). Retract with `--unpublish <item_id> --reason "..."`.
- **⚠ Owned honestly:** my S157-b rule-lab producer shipped `kind='rule_verdict'` unregistered → S158-b's census caught it live (Ramana's real verdict was rendering as a raw slug) and built a gate for it. **A new producer kind is part of the producer's contract.**
- **➡ NEXT PICKS (kickstart-pick-verify EACH):** ① **owner nudge in the heartbeat DM** ("N waiting on you") — `estate_heartbeat` already composes that line; 5 items now wait (2 briefs · 3 tags · 1 rule verdict) and the DM is the only thing Ramana reads daily — the deliberate alternative to a home tile · ② a **publish timer** is deliberately NOT built (approval is human-paced; `--publish` is an owner CLI, AUD-95) — revisit only if Ramana asks · ③ entity-graph SURFACE only when a reader question needs it (hub caveat) · ④ **Ramana's open decisions: plan §7.7 (vendor-ToS enum — now BLOCKING the wire's licence story), §7.8 (rule-lab ledger append), §7.2 (₹200 auto-analyst cap)** · ⑤ time-gated: Aug-1 churn row-gain.


## ✅ 2026-07-15 — S158: THE REVIEW-INBOX LENS + Q1 CLOSED (legacy writer BRIDGED) — BUILT + DEPLOYED + LIVE-WALKED — do NOT redo; kickstart-pick-verify
- **`/dash/inbox` LIVE** (Trust lens, `_ROUTER_SPECS` mount, commit **`2cc73b2`**): the judgment loop finally has a human interface (it was SSH-CLI-only). **Two audiences, one route:** anonymous → the methodology page + honest aggregates; **owner** (`tracker_gate._is_owner`, fail-CLOSED) → the queue, per-item evidence, POST approve/reject, corpus CSV. Live: 5 waiting · 295 recorded · **0 decided here**; every public leak probe clean; owner sees the 2 real briefs (HCLTECH/ANANDRATHI) the public cannot.
- **🔴 THE OWNER GATE IS LOAD-BEARING — do not "simplify" it:** `kind='brief'` items are AI drafts **nobody has checked**, and L6's contract is that ONLY an approved brief publishes. A public inbox would publish exactly the unreviewed AI text that contract forbids. Tested against a real pending brief.
- **🔑 HONESTY FINDING (don't re-derive, and don't quote the old number):** the imported corpus **cannot** distinguish "approved a proposal" from "typed the tag in himself" — `theme_tags.approve()` and `add_manual()` write the SAME `source='ramana'` row. So **S157's "94%" is imported history, NOT a proposer hit-rate.** The page reports lived vs imported rates in separate columns with the reason; the clean measure starts at 0 decided-here and grows as Ramana judges.
- **Q1 CLOSED — bridged, not deleted:** `dashboard.dash_tags_act` → `inbox_adapters.decide_by_ref_safe` / `decide_bulk`, so legacy verdicts are corpus-recorded on the same path as the lens; theme_tags still does every `company_tags` write. **Fail-open** (inbox trouble → direct write; a button must never break). **`add`/`remove`/`unreject` stay direct = authoring, not judging** (counting them would inflate the rate) — pinned by a test. `_next_ref()` versions re-judgments (`SYM|TAG#2`), fixing a **latent crash**: unreject→re-approve would have hit decide()'s FINAL guard and silently not applied the tag.
- **🔴 DEPLOY LESSON (cost me a live break, caught mid-walk): a patch deploy of a CALLER without its CALLEE is SILENT.** I shipped `dashboard.py` calling `IA.decide_by_ref_safe` but forgot `inbox_adapters.py` — `py_compile` OK, app imports OK, all routes 200, because the handler's import is **lazy** (defers AttributeError past every startup probe) and its bare `except` would have swallowed it. Only the **selftest's output signature** (box printed S157's last line, not S158's) revealed it. **RULES: verify a new cross-module callee by `hasattr` ON THE BOX, never by import success; give selftests a version-distinct final line.**
- **The first real verdict is Ramana's** — the bridge was verified hermetically on-box (temp DB), deliberately NOT by approving a live proposal (a machine must not fabricate a human verdict). `tags_sync`'s `stale_decided_on_legacy` census is now the bridge's regression detector: it should stay **empty**.
- **✅ S158-b — the kind registry paid for itself within the hour** (`a1ee185`, deployed): the moment the two D134 lanes met, the live census flagged an **unregistered kind** — rule-lab's `kind='rule_verdict'` producer landed while Q2's set was being written, so a REAL queued verdict (the NEW-BENCHMARK [fundable] LOWVOL_MOM rule) sat un-registered and rendered as a raw slug. Registered + display copy + the evidence line now reads `producer` as well as `source`; **the runtime warning is now a BUILD GATE** (`test_every_producer_kind_is_registered` source-scans `src/automation` for producer `KIND` constants — revert-probed, it flags `rule_lab_inbox.py` when unregistered). **Live queue = 3 kinds, census clean (`unregistered: {}`), suite 613.** Lesson for the next cross-lane seam: two *correct* lanes still drift when the contract lands after the producer — give the seam a machine owner.
- **⚠ WORKTREE GOTCHA (cost me two failed pushes): `test -d .git/rebase-merge` NEVER fires in a worktree** — `.git` is a FILE there, so the real path is `D:/Hermes/.git/worktrees/<name>/rebase-merge`. Use **`git rev-parse --git-path rebase-merge`**. A stale one (Windows "could not remove … rebase-merge" after `rebase --continue`) silently BLOCKS every later rebase; clear it with `chmod -R u+w` then `rm -rf` — **only ever your own session's**.
- **NEXT natural picks (kickstart-pick-verify EACH):** ① **the wire-publisher for APPROVED briefs** — now genuinely unblocked (approval is possible at last); pattern = `tags_apply` (exactly-once via an apply-log); ② an **owner nudge in the heartbeat DM** ("N waiting on you") — the deliberate alternative to a home tile, and `estate_heartbeat` already composes that line; ③ rulelab integration = cranky-khayyam's claim; ④ Ramana's plan-§7 decisions (vendor-ToS enum ×6 · auto-analyst ₹200 cap · charter v2.0 · NEW-BENCHMARK verdicts → inbox-first proposal). Time-gated: first heartbeat DM Wed 03:30 UTC · Aug-1 churn row-gain.

## ✅ 2026-07-15 — S157-b (D134 LANE-H): RULE LAB — BUILT (sibling `b67509d`) + REVIEWED + INTEGRATED + LANDED — do NOT redo; kickstart-pick-verify
- **The claim protocol WORKED end-to-end:** this lane (dispatched as the rule-lab BUILD session) found the sibling's build mid-flight, yielded, pushed the integration claim (`4ffd9c9`), reviewed the build vs the design (**CONFORMANT, 0 defects** — every claimed binding verified real), cherry-picked `b67509d` (authorship preserved) and landed the whole integration half. **Full suite 594/0** (baseline 526/0). Full record: PROJECT_STATE §Session 157-b + §D137.
- **What's live in the repo:** `/dash/rule-lab` (Trust lens; owner composer POST→`rule_lab_queue`→303; anonymous = labeled synthetic demo; dead-shape URLs cite the ❌ BLOCKING rows BEFORE any run; CSV + URL-state) · Pat `rulelab` DATA flow (all four seams + coverage-gate row) · 5 glossary keys (§ Rule lab) · `docs/strategies/rule-lab.md` (🏠 HOUSE) + README matrix + `_SURFACE` hand-off · **design doc RETIRED** (folded into plan §4-H; DOC_INDEX cleaned) · plan **§7.8** = Ramana ratifies the implemented inbox-first default (NEW-BENCHMARK never auto-appends to the ledger).
- **Operating the lab (owner):** compose + POST on the page → SSH → `PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python -m explosive_moves.rule_lab_executor --work` → the verdict lands on the page + Review Inbox. Deliberately NO timer (AUD-95).
- **✅ DEPLOYED + LIVE + REAL E2E VERIFIED (~09:35 UTC):** full journey walked on the box AND hstgr.cloud; the FIRST real verdict ran in 8.6s — survivor-shape rule → **NEW-BENCHMARK [fundable], net 1.19, halves 1.20/1.42, capacity ₹75cr** — now **PENDING in the Review Inbox** (kind=`rule_verdict`; judge it on `/dash/inbox`). Anon = demo only; owner gate real on the box.
- **⚠ For the builder sibling (`69963ef7…`) if it resurfaces:** `b67509d` is landed on main via cherry-pick — `git cherry` shows patch-equivalence; drop your branch, do not re-wrap.
- **➡ NEXT PICKS (unchanged from S156 baton, minus rule-lab):** the wire-publisher for APPROVED briefs · an entity-graph SURFACE only when a reader question needs it (respect the hub caveat) · Ramana's open decisions now **plan §7.7 (vendor-ToS enum) + §7.8 (rule-lab ledger append)** · time-gated: Aug-1 churn row-gain check · XBRL Phase-3 universe backfill continues in its own lane.

## ✅ 2026-07-15 — S157: FIRST PRODUCER WIRED — tags-review ↔ Review Inbox — BUILT (inboxwire lane) + INTEGRATED + LIVE (frosty-darwin lane) — do NOT redo; kickstart-pick-verify
- **The judgment loop is REAL:** `src/automation/inbox_adapters.py` (+17 hermetic tests) on main as **`17f9fb9`** (sibling's build `147c67d` cherry-picked, authorship preserved). Live on the box: **tags 276 approved / 19 rejected / 3 pending · 94% historical approve-rate seeded by the honest-timestamp backfill (`imported=true`, created_at=decided_at=original `as_of`) · briefs 2 pending · kinds census clean.** Weekly flow ARMED: theme-seed oneshot runs `inbox_adapters --sync --apply` as its 2nd ExecStart (Sun 17:30 UTC; unit converged git==box==etc md5 `0cfc15c3`, NeedDaemonReload=no, nothing started). Full suite **543 pass** + compliance gate at `17f9fb9`.
- **Q1 SINGLE-WRITER (recorded in the module docstring):** inbox `decide()` + `tags_apply()` = the canonical write path to company_tags (via theme_tags' own helpers — ramana promotion + durable tombstone reused). The legacy `/dash/tags-review` surface (forked cockpit/dashboard) stays a direct writer IN THE INTERIM: out-of-band decisions are REPORTED (`stale_decided_on_legacy`), never auto-decided; **the inbox-LENS session must bridge-or-read-only it.** **Q2:** canonical `KINDS = {tags, alert-ack, brief, rebalance, anomaly}` in `inbox_adapters` — extend THERE in the same commit as a new producer. **New-producer gotcha (S153, honored):** `review_inbox.submit()` does NOT commit + `ensure_schema` DDL auto-commits mid-batch → commit-per-item.
- **3-lane race resolved by pushed claim markers (S140 protocol HELD):** the builder deployed in parallel with this integration — the second run became a live idempotency proof (0 dupes on 295+3 re-submits); cranky-khayyam claimed the rulelab integration (`4ffd9c9`). **Craft: when a sibling deployed first, CONVERGE byte-exact (adopt the box wording into git); never re-deploy your variant.**
- **NEXT natural picks (kickstart-pick-verify EACH — 3 lanes were mid-flight today):** ① **wire-publisher for APPROVED briefs** (LANE-E residue: approved `kind='brief'` → the wire; small; `tags_apply` is the pattern — exactly-once via an apply-log) · ② **the inbox LENS session** (SURFACE-PLAYBOOK; real data waiting: ~300 items / 2 kinds; MUST also settle the legacy-tags-surface bridge-or-read-only, Q1's endgame) · ③ rulelab build integration = cranky-khayyam's claim · ④ Ramana's open decisions (plan §7: vendor-ToS enum ×6 · auto-analyst ₹200 cap · charter v2.0 · NEW-BENCHMARK verdicts → inbox-first proposal) · time-gated: first heartbeat DM Wed 03:30 UTC · Aug-1 churn row-gain.

## 📣 2026-07-15 — BUILDER-SIBLING DISCLOSURE (session 69963ef7, the D134 orchestrator) — BOX FACTS for the two claimant lanes above; claims honored, integration commits DROPPED on rebase as instructed
- **I raced you unknowingly:** my integration worktree cherry-picked + DEPLOYED both builds ~14:3x IST, before your claims were fetchable. On seeing them, my integration/wrap commits were dropped (this docs-only note is my whole push); `rulelab-d134`@`b67509d` and `147c67d`'s landing remain YOURS. Suite evidence you can reuse: both picks green on `1ca99a5` — **563 passed / 0 failed** (excluding the pre-existing numpy collection debt below).
- **⚠ IRREVERSIBLE BOX FACTS (done before the claims; all idempotent to re-run):** ① all 6 rule-lab/wiring files are ALREADY on the box (git-archive push, LF-pure; py_compile + 3 selftests green — `RULE_LAB selftest OK (21 tokens, 10 blocking rows)`); ② `inbox_adapters --backfill` RAN: **276 approved + 19 rejected imported** (honest stamps); `--sync` RAN: **3 pending proposals now in the inbox awaiting Ramana**; `--apply` 0 (nothing decided); ③ **the box's `/etc/systemd/system/hermes-theme-seed.service` ALREADY has the 2nd ExecStart** (`inbox_adapters --sync --apply`) installed via `install-systemd.sh --install` + daemon-reload, backup `.bak-s157lab`, timer schedule untouched (next Sun 17:31 UTC) — **frosty-darwin: your repo-side ExecStart append is still owed so capture matches the box (repo copy currently 1 line); do NOT double-add on the box.** ④ cranky-khayyam: your module-scp step is a no-op re-verify; the ENTIRE shared-file surface half + restart + on-box E2E remain untouched and yours.
- **Gotchas for your deploy steps:** `install-systemd.sh` DEFAULTS to `--check` — the copy needs the explicit `--install` flag (this bit me; also now in the deploy memory). Worktree commits need BOTH `HERMES_SKIP_STATE_GATE=1` and `state:skip`.
- **✅ Suite debt FIXED (same orchestrator, npfix-suite):** `test_embase_deliv_value.py` now `pytest.importorskip("numpy")` (the test_rule_lab_executor pattern) and `combo_test.py` (a research SCRIPT that only matched pytest's `*_test.py` glob) is collect-ignored via a new `research/explosive_moves/conftest.py` — full suite collects clean in numpy-less worktrees (539 passed / 0 errors at the S158-era base). Semantics untouched; the script still runs via `python -m`.

## ✅ 2026-07-15 — S-rotation-e: SECTOR-ROTATION PORTFOLIO SURFACE — BUILT + DEPLOYED + LIVE-WALKED — do NOT redo; kickstart-pick-verify
- **`/dash/sector-rotation` LIVE** (→ nested `/dash/strategies/sector-rotation`; public Caddy 200): the V17 book with **`?asof=` time-travel** (◀/▶ steppers + year strip; walked 2008/2013/2020/2024/latest), **per-quarter rebalance diff** (entered/exited/re-weighted + sleeve regime + turnover), analytics-to-date vs Nifty 500, dual NAV sparkline, CSV. **Engine `src/automation/sector_book.py`** → bounded `sector_rotation_book`+`sector_rotation_nav` (83 rebalances/258 months; **on-box build NAV 19.04 == the research number** — engine cross-validated); clock-gated `--refresh` in `10-signals.conf` (installed, no start). **Every strategy-ref page now hands off to its live surface** (`strategies_view._SURFACE`, 12 slugs — Ramana's "details → portfolio" directive). Lens registered (anchored inserts on box-forked `lens_registry`/`v2_surfaces`; glossary term anchored into hot `metrics-glossary.md`; backups `.bak-secport-*`). Gates: strategy-docs 13/13 · route · education · pat-coverage · suite 502 pass (pre-existing `test_embase_deliv_value.py` collection error = XBRL lane's, reproduces at origin, flagged). Commit `7887c78`.
- **⚠ Live fact worth knowing:** the residual sleeve's regime is **CASH right now** (Nifty 500 below its 200DMA post the Apr-2026 fall) — the defensive rule is actively engaged; it flips back to INDEX automatically when the index reclaims the average.
- **NEXT (rotation lane):** Ramana's V17 ratification · TR-benchmark re-cut + V17 significance pass · V2 ≤40-stock constituent build (stock RS inside qualifying sectors — reuse `stock_signals` RS columns).

## 🆕 2026-07-15 — S155/S156 (D134 LANE-G + LANE-H): ENTITY GRAPH live + RULE-LAB design — do NOT redo; kickstart-pick-verify
- **LANE-G `src/automation/entity_graph.py` — DEPLOYED + REAL-DATA VERIFIED.** 6 extractors over filing tables we already own → **7,813 edges in 130ms** (insider 3,643 · sast 2,256 · deal 1,033 · pledge_lender 441 · pledge 317 · rating 123); re-run identical, **0 dupes** (idempotent on live data). `neighborhood(symbol)` → edges + **co-links** (the other companies a shared counterpart touches, with `via` provenance). Walked live: MAHABANK 74 co-links · SASKEN 0 (correct — SASKEN-only filers).
- **⚠ READ BEFORE BUILDING ITS SURFACE — hub counterparts are NOT insight:** 7 rating agencies cover 63+ companies each, so an agency co-link is structurally guaranteed; "connected to 74 companies!" is an artefact of CARE Ratings existing. Rank by counterpart SCARCITY (shared insider 67 · acquirer 111 · deal 97 · lender 46), never headline a raw degree. **Degree is not importance.** Fenced in the docstring.
- **Ledger-fenced by construction:** NO score/weight column EXISTS (a test asserts it) — E-03 (placebo p95 **+9.52% > observed +8.26%**, emp-p 0.085) + accumulation-footprint v1 (FAIL 1/4, n=54) are cited in the docstring. Live insider edges span only 2025-11..2026-07 (~8 months), independently corroborating E-03's thin-feed premise. Any predictive claim needs its OWN prereg. **Surface deliberately NOT built** (playbook is a same-session contract — it earns a lens when a real reader question needs it).
- **LANE-H `docs/rule-lab-design.md` — DESIGN ONLY (build = its own session).** Closed-vocab grammar (every token binds 1:1 to a tested `factory.*` callable; NO arithmetic composer / rupee constants / timing DSL / single-stock verdicts) → the EXISTING evidence factory as the gauntlet (prereg → walk-forward both halves → **placebo p95** → cost realism (**net FIRST**) → capacity breakpoint → bench 0.89) → a verdict in the **ledger's own vocabulary** with a travelling qualifier. The 10-row BLOCKING table is reproduced **verbatim** (mechanically diffed: 10/10, 0 altered) as an **auto-cite wall** + a token→row trigger map. SEBI per plan §3; playbook 12 rows pre-filled; verdicts land in the Review Inbox (reuses LANE-D, no new job runner).
- **⏭ NEXT PICKS:** the D134 build lanes are now ALL landed (A–I). Natural next: **the rule-lab BUILD session** (spec is paste-ready, §8 build order) · **wire tags-review → review_inbox** (first non-brief producer) · **the wire-publisher for APPROVED briefs** · an entity-graph SURFACE (only if a reader question needs it — respect the hub caveat). **Ramana's open decisions** (plan §7): vendor-ToS enum ×6 · auto-analyst ₹200 cap ratify · charter v2.0 · should a NEW-BENCHMARK verdict auto-append to the ledger or go to the inbox first (proposal: inbox — canon should carry a human signature). **Time-gated:** first heartbeat DM Wed 03:30 UTC · Aug-1 churn row-gain. The codex START-HERE queue below is a DIFFERENT lane's — its item 1 (Pattern-5) landed as `62fb1b6`; item 2 (Doctrine-D scorer) is still open FOR THAT LANE.

## 🔴 START HERE — CODEX-REVIEW CAMPAIGN: decisions LOCKED, build queue ready (2026-07-15)

**Boot:** `docs/codex-review/FINDINGS-LEDGER.md` + `TRACK-C-RESULTS.md` + `TRACK-D-DATA-PLAN.md` (esp. its
"Step-2/3 investigation" block) + memory [[codex-review-campaign]]. Governance (BINDING): **ship only on
Codex↔Claude agreement.** Guardrail #8 = primary sources only.

**✅ DONE — do NOT redo (kickstart-pick-verify; all on origin + live-verified):** **ALL 4 VPS activations** —
**D2-F1** PIT rank universe via `security_master` (2016 rank universe 419→**547**; today unchanged 1336) ·
**D6-F2** knowable-date backfill (4,070 rows) + `credibility_series` rebuild (19,837 pts; settled 5,255
**unchanged** = non-destructive) · **D5-F6** momentum_scan/em_cache rebuilt (split-invariance proven 1.0000
vs old 1.3750) · **D1-F1** `signals --backfill-triggers` (3,805 syms / **5,968,171 rows** / 0 fail; 650
latest-date rows changed, 16 char-label flips). Plus **Track C RISKADJ 1.13→1.09** annotation into
`docs/strategy-ledger.md`, **D3-F1 interim LABEL** (`scoring.py`), **Track D Step-1 XBRL spike**.
**Full-surface health check PASSED** (services active · nightly chain exit 0 · every consumer page 200 / 0 tracebacks).

**🔑 RAMANA'S DECISIONS — LOCKED 2026-07-15 (execute; do NOT re-ask):** Doctrine-D scorer **defaults
approved** — sub-type-aware thresholds (bank RoA ~1% · NBFC 2–4% · HFC RoE 12–15%) · **ALM = CET1/CRAR +
GNPA proxy** (defer true ALM) · **suppress-half folds into the scorer**. **Pattern-5 SA-extraction: BUILD it**
(isolated worktree; coordinate with the sibling-active XBRL lane). *"Do the other parked items too, where feasible."*

**▶ QUEUE:**
1. ~~**Pattern-5 SA-instance extraction.**~~ **✅ DONE + DEPLOYED + LIVE-VERIFIED (S154, `62fb1b6`) — do NOT redo.**
   NEW `extract_bank_prudential()` + `_has_prudential_tags()` + `augment_prudential()` in
   `fundamentals_xbrl.py`, wired into BOTH ingest paths (legacy listing pulls the dropped SA sibling only
   when a bank block is zeroed; integrated-filing costs ZERO extra fetch — it already parses both natures).
   Metric-keyed → no schema change. Live proof: HDFCBANK → 1 SA fetch → `{GNPA 1.42, NNPA 0.46, RoA 0.47,
   CET1 19.97}`, P&L intact; BAJFINANCE (NBFC) → 0 fetches, `{}`. 10 tests + suite 487.
   **🔑 THREE FACTS NOW SETTLED EMPIRICALLY (don't re-derive):** raw tags are **fractions** (×100 = percent);
   a bank's **conso reports 0.00 for all five** (SA-only is real, non-zero gate = the conso guard);
   **⚠ `ReturnOnAssets` is context-dependent — OneD (discrete qtr) 0.47% vs FourD (YTD) 1.43%** — read the
   discrete-quarter ids or you silently store the YTD number. **`_is_bank_instance` can NOT gate the SA fetch**
   (NBFCs tag `InterestEarned` too) — `_has_prudential_tags` (declared-even-if-zero) is the discriminator.
   **▶ RESIDUAL (bounded, deliberate):** XBRL rows populate for filings ingested **from now on** (nightly
   `hermes-fundamentals-xbrl` 16:33 UTC). Already-ingested bank periods sit in `fundamentals_xbrl_seen` and
   will NOT be re-parsed → a **targeted re-ingest** (clear those urls for bank symbols, or route via the
   Phase-3 backfill) is needed for XBRL-sourced history. Gate it past the scan clusters.
   **🔑 CORRECTED 2026-07-15 (measured, supersedes the earlier "no historical Pattern-5 data" claim):**
   `fundamentals_history` ALREADY holds **`Gross NPA %` (289 rows) + `Net NPA %` (286 rows), 2020-03-31 →
   2026-06-30, from the SCREENER archive** (`source IS NULL`). **`Return on Assets %` and `CET1 %` do NOT
   exist at all** (0 rows) — those are genuinely net-new and forward-only. So the scorer's Pattern-5 legs
   split: GNPA/NNPA have deep history (vendor-sourced), CET1/RoA start empty and fill forward.
   My emitted names MATCH the Screener names exactly for the two overlapping metrics → ONE vocabulary, no
   variant to reconcile. ⚠ **Guardrail #8:** that GNPA/NNPA history is **Screener (vendor) data** — the very
   thing the XBRL migration replaces; `write_rows(overwrite_screener=False)` (the default) leaves Screener
   rows untouched, so XBRL supersedes them only on a deliberate `--overwrite-screener` pass.
   ⚠ **Build the scorer NULL-tolerant regardless** (absent ratio ⇒ that leg abstains, never a false
   pass/fail) — CET1/RoA will be absent for most names for months.
   ⚠ **KNOWN PROVENANCE WRINKLE (mine, unfixed):** `write_rows` stamps ONE `source` per filing
   (`SOURCE_CONSO if filing["consolidated"] else SOURCE_SA`), so prudential ratios pulled from the SA
   sibling are written stamped **SOURCE_CONSO**. Guardrail-#8 (vendor-vs-primary) is unaffected — both are
   NSE-XBRL — but a `WHERE source=SOURCE_SA` query will not find them. Fixing it needs a per-metric source
   override in `write_rows` (sibling-owned; coordinate).
2. ~~**Doctrine-D financials scorer (Step 4)**~~ **✅ DONE + DEPLOYED + LIVE-VERIFIED (S155, `70853a1`) — do NOT redo.**
   Patterns 1/2/5 replaced for lenders BEFORE the aggregate (profitability on the sub-type's ratios ·
   operating leverage on **NII** · asset quality+capital GNPA≤1.5/CET1≥13/NNPA≤0.5) · generic **D/E
   disqualifier DISABLED** for lenders · **suppress-half in the scorer** (no lender evidence → tier `NA`).
   `fundamentals_asof` surfaces the lender keys DERIVED from stored metrics (no ingest work).
   Live proof: HDFCBANK generic→**DISQUALIFIED 29.8** vs Doctrine-D→**T3 45.8, P5 48/48**; live universe
   classifies **bank 23 · hfc 1 · nbfc 14**; HDFCLIFE/BSE → **suppressed** (not lenders); TCS unchanged.
   **🔑 FOUR TRAPS NOW PINNED (don't re-derive):** (a) `roa_pct` is the **discrete quarter** — annualise ×4
   before the ANNUAL "~1%" bar or every good bank FAILS; (b) each leg needs its **own** bar (RoE judged on
   the RoA bar = meaningless pass); (c) `security_master.**company_name**` (NOT `name`) — the fail-closed
   except silently degraded every HFC to NBFC, and the test fixture had invented the column; (d) **'Financial
   Services' also carries INSURERS/EXCHANGE/holdcos** — `roe` must NEVER be lender evidence (every company
   has one) or they get an "NBFC read on RoA" verdict = the D3-F1 error in a new place.
   **▶ RESIDUAL / NEXT for this lane:** banks are **PROVISIONAL** — most score T4 on 1/5 lender inputs
   (NII growth alone) because RoA/CET1 have **0 rows** until the S154 XBRL SA pass fills forward. The score
   now discloses this (`sector_evidence` + "Read on 1/5 lender inputs … provisional"). **To make the model
   real, do the S154 residual: a targeted re-ingest of bank filings** (clear their urls from
   `fundamentals_xbrl_seen`, or route via the Phase-3 backfill; gate past the scan clusters) → then
   re-check that RoA/CET1 populate and the tiers firm up. Also unfixed: SA-sourced prudential rows are
   stamped `SOURCE_CONSO` (per-metric source override in `write_rows` — sibling-owned).

3. **Parked — do if feasible:** PROJECT_STATE + this carry-forward **reconcile** (OWED) · **D1-F4** ignition
   warm-up guard (converge with Codex first, then scoring + VPS `--relabel`) · Wolfe D4 / harmonic-zigzag
   D7-F1 / prereg D5-F5 (sibling-hot).
4. **Verify the 14:01 nightly chain** — **PARTIAL (S154):** the chain is ONE unit (`hermes-bhavcopy.service`
   with chained `ExecStart`s: bhavcopy→signals→…→stock_rs→cpr→reversal). **`stock_rs.py`** (deployed Tue
   13:21 UTC) DID run in Tue's 14:01 chain → `Result=success`, exit 0, clean journal ✅. **`signals.py` was
   deployed Tue 16:00 — AFTER that run**, so its incremental path is STILL unexercised; **first run = the
   next 14:01 UTC chain.** Re-check `journalctl -u hermes-bhavcopy --since "14:00"` + exit 0 after it fires.

**⚠ STANDING CONSTRAINTS:** **SHARED-WORKTREE HAZARD** — multiple sessions on ONE `D:\Hermes` tree on `main`
→ diverged + churning. **Docs edits = plumbing-on-origin** (`git show origin/main:f` → edit → `hash-object -w`
→ temp-index `read-tree`/`update-index`/`write-tree` → `commit-tree -p origin/main` → `push <sha>:main`,
FF-checked) — this lands cleanly while siblings churn. **Code = isolated worktree.** Never `git add -A`;
explicit paths only. **CONTINUOUS whole-surface verification after ANY deploy/backfill/push** (Ramana
directive): services + nightly chain + the live pages consuming the change — not just the changed thing.
Gate backfills **past the scan clusters** (14:01 bhavcopy · 16:00–16:30 wolfe/harmonic/launchpad); never
restart 13:55–14:15 UTC. XBRL/network needs the **main venv** `/opt/hermes/.venv/bin/python` (not
`.venv-research`). Box rollback backups: `*.bak-d1f1/d2f1/d5f6/d6f2-*`. `--relabel-character` is
**INSUFFICIENT** for D1-F1 — the correct tool is `--backfill-triggers`.

## 🆕 2026-07-15 — S153/S153-b (D134 LANE-E + LANE-I): AUTO-ANALYST v1 + REAL-TIME SEAM — BUILT + DEPLOYED + DONE-BAR MET — do NOT redo; kickstart-pick-verify
- **LANE-E (`src/automation/auto_analyst.py`):** freshest `results_reactions` → 6–10 line descriptive brief → Review Inbox (`kind='brief'`, period-stable refs, first-write-wins). Template ₹0 default; `--llm` opt-in triple-guarded (per-job cap ₹200 §7.2-proposal degrades BEFORE calling · cheap router `job="auto-analyst"` self-meters · digit-subset guard kills invented numbers; label/fence/PEAD-falsification tail VERBATIM on every path). Compliance lexicon runs over module + rendered briefs in `tests/test_auto_analyst.py`.
- **✅ DONE-BAR met on box:** 2 REAL briefs queued (HCLTECH SUE +2.01 · ANANDRATHI SUE +18.97), path=llm (Gemini Flash Lite), **₹0.01 logged under `auto-analyst`**; a scheduled `classifier` call had already self-metered ₹1.05 organically — the LANE-R ₹-meter is proven in prod. MTD ₹1.06/2,500. **Ramana: two briefs await your verdict — `review_inbox --pending` / `--decide ID --verdict approved|rejected` (the judgment corpus starts here).**
- **LANE-I (`src/automation/intraday_adapter.py`):** `QuoteSource` ABC + bounded age-pruned `intraday_window` + `NullSource` + `T0LiteSource` stub (₹0 EOD-prelim path, not wired). `feed_manifest.FEEDS["intraday_seam"]` = `personal-broker` (MIN_FEEDS 22) → the licence gate fences it OFF src/web BY CONSTRUCTION; no Kite wiring (tested). Kite activation stays Ramana's paid decision.
- **⚠ For the next inbox producer (tags-review):** `review_inbox.submit(conn,…)` does NOT commit; DDL auto-commits mid-batch → commit-per-item after submit or the batch's LAST item silently rolls back (bit LANE-E; fixed consumer-side; LANE-D may want submit() to own the commit).
- **⏭ NEXT PICKS:** **LANE-G** (entity graph v1) + **LANE-H** (rule-lab design doc) — prompts in `docs/parallel-lane-prompts-D134.md`. Also queued: wire tags-review → inbox · the wire-publisher for APPROVED briefs (small; SURFACE-PLAYBOOK) · Ramana decisions (plan §7: vendor-ToS enum ×6 · E's cap ratify · charter v2.0) · time-machine `asof_capable` flags · verify the first heartbeat DM (Wed 03:30 UTC) + Aug-1 churn row-gain.

## 🆕 2026-07-15 — S149-c (D134 LANE-R): WAVE 1 INTEGRATED + DEPLOYED + HEARTBEAT ARMED — do NOT redo; kickstart-pick-verify
- **The divergence is GONE:** local-main's 9 commits rebased onto origin in an isolated scratchpad worktree — `a781669`/`bce01cb` auto-dropped (patch-twins), `216db7b` dropped as SUBSUMED (origin `0e2ca21` is its evolved reconcile — verified: reversal-pair-PLAN deleted, reversal-context served, backstop present), 6 unique commits carried; duplicate "S148" disambiguated (`### Session 148 (XBRL lane)`). Reconcile pushed `2fc1248`; integration pushed `edffb86` (one mid-flight re-rebase over the Pat lane's push — expected race, resolved keep-both).
- **B/C/D merged serially** (`cherry-pick -x` — NOT `git merge`: the lane branches sit on the pre-rebase lineage, a merge would re-fight every twin conflict) with the FULL suite between: 398 → 410 → 428 → **460 green** post-race. One real red found+fixed en route: carrying S145's classics glossary onto the S141 Pat-adapter broke `test_every_web_entry_accounted_for` (names starting with a slashed symbol produce no speakable lead) → `Debt to Equity (D/E)` / `Price to Book (P/B)` words-first rename (`89f5436`).
- **₹-meter has PRODUCERS now (LANE-B's #1 open Q closed):** NEW `src/core/llm.py meter()` (never-raises; Anthropic+OpenAI usage shapes) → `cost_ledger.record`; wired into `ask()` · `llm_router` classifier/extractor BOTH providers (`job=` kwarg for per-producer labels) · assistant chat · patearn analyze/screen. Scheduled jobs meter immediately (fresh processes); bot/API activated by this session's restarts. enrich.py (paused) + code_review.py (dormant) left out, reasoned.
- **✅ DEPLOYED + VERIFIED (~21:10 UTC):** 11 files placed byte==HEAD (fork-checks: ALL 5 shared files = committed ancestors; 3 "forked" flags were CRLF remnants — CR-strip both sides!). On-box: py_compile + imports + 4 selftests green; REAL heartbeat line: **"estate GREEN · board OK · bhav 2026-07-14 · signals 2026-07-14 · fund 2026-07-14 · events 2026-07-14 · crit 2 · ₹0/2,500 MTD (0%) OK"**. Units installed TARGETED (not blanket `--install` — see drift note below) + daemon-reload. **Heartbeat timer ENABLED+STARTED — provably schedule-only** (no Requires=, Persistent=false; `list-timers` NEXT = Wed 2026-07-15 03:30 UTC = 09:00 IST; service inactive, journal empty). **First real morning DM lands Wed ~09:00 IST — verify it fired + fire-once held (re-run `--dm` = "nothing new").** Disarm = `systemctl disable --now hermes-heartbeat.timer`. Writer-guard BLOCKED on `fundamentals_provenance --refresh` → verified frequent commits + writes only `fundamentals_history` (api startup doesn't read it) → justified restart-past; writer survived both restarts; api 200; cockpit tile honest wording live ("Rewind the whole platform" = 0 hits).
- **Cheap open-Qs closed:** cockpit ~975 flagship-tile overclaim FIXED (audit §4 wording, deployed live) · lens_registry model-portfolios comment de-drifted (2012-06 + CRAFTSMAN; repo-only — comment invisible, box copy still forked) · plan §4 B/C/D→LANDED, §1 ledger flipped.
- **⚠ Observations for owning lanes (NOT mine):** (1) `install-systemd.sh --check` shows **`hermes-deals.timer` DRIFT** (repo≠/etc) — whoever changed it owes the install decision; (2) the 4 UNCAPTURED seasonal units remain (S138 flag); (3) **the shared D:\Hermes tree still sits on the OLD pre-rebase main (`e534d1f`) — plain FF is IMPOSSIBLE by construction** (the reconcile rewrote that lineage; every old commit is carried in rewritten form). Recipe once its dirty files are resolved by their owners (`stock_chart.py`/`symbol_search.py` = the Pat lane's own content, committed as `b7553a6`; `cockpit.py` mod appeared mid-wrap, owner unknown): `git reset --keep origin/main` (or `--hard` once fully clean). Do NOT commit new work onto the old local main.
- **⏭ NEXT PICKS (paste from `docs/parallel-lane-prompts-D134.md`): LANE-E** (S153 auto-analyst event briefs — review_inbox is LIVE on box, cost_ledger cap_status ready for its ₹100–300/mo hard cap) **and LANE-I** (real-time seam interface — extends feed_manifest via a manifest row; the licence gate keeps it off public surfaces by construction). Also queued: wire the FIRST review_inbox producer (tags-review) · Ramana's plan-§7.7 vendor-ToS enum decision (6 feeds) · time-machine `asof_capable` flags (audit's flag map is paste-ready).

## 🆕 2026-07-15 — S150: PAT "DATA HERO" + the SELF-MAINTAINING KNOWLEDGE ARRANGEMENT — SHIPPED + DEPLOYED + LIVE — do NOT redo; kickstart-pick-verify
- **THE ARRANGEMENT IS INSTALLED + ENFORCED (Ramana's core ask).** `tests/test_pat_coverage.py` (Gate 0) makes every routed lens declare Pat coverage — **DATA** (`PAT_DATA` lens→flow, verified vs `engine._VALID`/`web._FLOW_LABEL`) / **EXPLAIN** (`PAT_EXPLAIN` lens→glossary slug, auto-folds) / **NAV** (`NAV_ONLY` owner+rationale, navigate-verified) — or the build FAILS. A new lens moves NAV_ONLY→PAT_DATA the moment its flow lands. Glossary half too: `test_screener_columns_are_glossary_backed` (every Screen+ column key resolves or is `''`). Auto-fold PROVEN both ways (md term → explain, injected Lens → navigate, ZERO code). Canon = **`docs/pat-knowledge-contract.md`** (DOC_INDEX A; twin of SURFACE-PLAYBOOK 5+6 / CLAUDE.md #9 / AGENTS.md #7). **When adding ANY new lens/metric: register into Pat in the SAME commit or the build breaks — this is the point, do not weaken it.**
- **4 NEW/EXTENDED Pat flows, all DEPLOYED + live-walked on real data:** `filings_flow.py` (per-symbol insider/ratings/SAST/holdings — "filings for TCS"), `wolfe_flow.py` (open Wolfe setups — "any wolfe setups", 71 open live), `methodology_flow.py` (Ph3 — "explain the Wolfe methodology" → plain words from docs/strategies, sanitized), `seasonal_flow.py` per-symbol ("is TCS usually up in July" → 11/19 yrs). Gate now **22 DATA / 9 EXPLAIN / 36 NAV**.
- **Plain-language floor 141 → 159/202** (fundamentals 40/40, rs 27/30) via precise ₹0 recognizers in `disambiguate.route_extra`; Pat eval battery UNCHANGED (nothing stolen). Commits `a8cddf8`…`367d5d2` on origin/main (tip `ed6309d`); 8 src files on the box byte-match HEAD; controls (FII/DVPT) unaffected.
- **NEXT Pat picks (all OPTIONAL — coverage is complete + enforced):** the 36 NAV-only lenses are honest link-only coverage — UPGRADE any to DATA by writing its `*_flow.py` (candidates the gate rationales flag: band-locks/harmonic-scan open-setups · conviction confluence · growth glossary-anchor → EXPLAIN). Card band (4/18) is placeholder-limited (X/<stock>), index band entangled with rs — leave unless a real per-symbol read appears. **Follows the established pattern: new `src/pat/<name>_flow.py` + ₹0 pre-pass + web render + `_VALID`/`_FLOW_LABEL` + eval/pytest + move the lens to PAT_DATA.**

## 🆕 2026-07-15 — S149: D134 ANALYTICS-COMPANY PLAN + COMPLIANCE GATE SHIPPED — do NOT redo; kickstart-pick-verify
- **`docs/patearn-analytics-company-plan.md` is the company-level canon** (CANONICAL/LIVING, D134): analytics-company posture (VALIDATED — descriptive analytics needs no RA/IA registration; gray zone = single-stock house scores; trigger contract = legal opinion before monetizing them publicly), the 9 adaptable layers L0–L8 with plug-in contracts, the rated+costed component roadmap A–N, the structured cost model. Charter v1.1 §NOW is fully shipped — plan §6 is the proposed charter-v2.0 queue (Ramana ratifies).
- **The 5th gate is live:** `tests/test_compliance_language_gate.py` (solicitation/recommendation language in src/web+src/pat fails the suite; Pat's advisory-REFUSAL detector phrases are the reasoned allowlist).
- **NEXT per plan §6 (in order):** S150 **cost-ledger + estate heartbeat** (compose board_health + feed-liveness + timer results + alert-rail criticals into ONE positive morning owner-DM line, plus a `cost_ledger` ₹-meter every LLM job writes; budget law = plan §5.4) → S151 **licence-class registry + feed/signal manifests** → S152 **Review Inbox + judgment corpus** (generalize tags-review/ack; the human-verification layer) → S153 **auto-analyst event briefs** (capped, inbox-gated, results-events first) → S154 **time-machine contract** (`asof_capable` flags in lens_registry). Parallel lanes unchanged: XBRL Phase-3 pilot (S148 lane) · UX S-B1 remainder · armed studies.
- ~~⚠ DIVERGENCE FLAG~~ **✅ RESOLVED by LANE-R (S149-c, 2026-07-15):** the local stack was rebased onto origin and pushed (`2fc1248`); twins dropped, "S148" disambiguated. No divergence remains.
- **✅ S149-b (same session): WAVE 1 DISPATCHED + ALL 4 LANES LANDED (parallel background agents, worktree-isolated, base `63705e6`):** **B** `lane-b-d134`@`d667240` — cost_ledger + estate_heartbeat + hermes-heartbeat.{service,timer} + 22/22 tests (sample: "estate GREEN · board OK · … · ₹17.60/2,500 MTD (1%) OK"; zero producers instrumented yet) · **C** `lane-c-d134`@`7d5cb27` — feed_manifest (21 FEEDS · 11 SIGNALS, ledger-verbatim fences) + licence gate 12/12; **6 vendor-ToS feeds UNCLASSIFIED → NEW Ramana decision (plan §7.7)** · **D** `lane-d-d134`@`b642334` — review_inbox primitive 18/18 (first-producer rec: tags-review) · **F** `docs/time-machine-audit.md` (67 lenses: 5 yes / 34 partial / 28 no; top upgrade = momentum-scan `?asof=` one-query; HONESTY: cockpit ~975 flagship tile "Rewind the whole platform" overclaims the 1-symbol replay → fix in LANE-R). Full results + open questions: `docs/parallel-lane-prompts-D134.md` §1/§2.
- ~~➡ NEXT = LANE-R~~ **✅ LANE-R RAN (S149-c, top block): merged B→C→D, deployed, heartbeat armed. Next = LANE-E + LANE-I.** **Worktree gotcha stands:** the state-doc pre-commit fires inside worktrees — lane commits need BOTH `state:skip` in the message AND `HERMES_SKIP_STATE_GATE=1`.

## ✅ 2026-07-15 — S143-e: CHART COMPARE fixed (Ramana-directed) — do NOT redo; kickstart-pick-verify
- Ramana reported "index comparison removed" + "stock chart won't let me add stocks/related-companies/indices."
  **Neither was removed or broken** (Explore agent + live curl + backups verified): index-compare lives at `/dash/compare`
  (the index chart LINKS to it, never inline); the stock price-chart's compare box was a bare EXACT-MATCH input that
  silently rejected NAMES / wrong-case indices → "No series" → read as broken. **FIXED + LIVE-WALKED on the box:**
  `symbol_search.py` (base-matched) gained `search_indices()` + a `?indices=1` endpoint flag + `TYPEAHEAD_JS`
  `onPick`/`indices` options (⌘K/home unchanged); `stock_chart.py` (forked; 2-hunk `git apply` over the box's older-RSI
  D7-F5 drift) price-tab compare box now has a company+index typeahead dropdown (pick→add) + a name-resolution fallback.
  Browser-driven walk: "tata"→companies, "nifty"→indices, pick Nifty 50→added, "infosys"+add→resolved+added.
- **DONE (S143-f):** all 3 chart-compare follow-ups shipped + live — (1) related-companies peer chips now on the PRICE tab; (2) index-chart Compare link is now a prominent button; (3) ranking prefers the current listing (INFY over the old INFOSYSTCH). No chart-compare work remains.
- **(historical list, now done):** (1) surface "related companies" (peers) on the PRICE tab too
  (today the peer chips are RS-tab only); (2) make the index chart's "Compare indices" link more prominent;
  (3) optional `symbol_search._rank` tweak so "infosys" prefers the current listing (INFY) over an old ticker
  (INFOSYSTCH) in the add-without-picking fallback.

## ✅ 2026-07-14 — S148: S-E PHASE 2 slice C — Pat market-INTERNALS flow SHIPPED — do NOT redo; kickstart-pick-verify
- **NEW `src/pat/internals_flow.py`** — "how's the breadth / market internals / how many stocks up" →
  the latest `market_internals_daily` snapshot (% advancing + adv/dec + MEP effort tape + 22y percentile
  reads, mirroring `market_internals_view`). Self-limiting ₹0 pre-pass `(a-1h)` — page-find stays navigate,
  entity-ranking asks yield. Battery UNCHANGED; NEW `tests/test_pat_internals_flow.py` (23) + suite 355.
- **⚙ BUILT + SHIPPED FROM AN ISOLATED WORKTREE** (`s148-se`) because the main tree was too hot to
  commit/deploy from safely. WORKED cleanly (clean FF push, green suite). ⚠ **worktree + state-doc-gate:**
  the gate inspects the MAIN project dir's index, so worktree commits misfire → use `state:skip` (the
  commits DO update PROJECT_STATE; the gate just can't see the worktree index).
- **NEXT S-E slice = the rest of Phase 2** (insider/ratings/SAST/holdings — per-symbol ownership, needs
  NEW per-symbol reads · seasonal per-symbol base rates · Wolfe open-trades) **then Phase 3** (education:
  explain-flows on the unified glossary + docs/strategies). Follow the `internals_flow.py`/`participants_flow.py`
  pattern (new Pat file + ₹0 pre-pass + web render + eval/pytest). Chain is now nav a-1c → news a-1d →
  whatchanged a-1e → participants a-1f → rotation a-1g → internals a-1h.

## ✅ 2026-07-15 — S147 (review lane): REVIEW OF RAMANA'S OWN STRATEGIES + origins.md label closure SHIPPED (docs) — do NOT redo; kickstart-pick-verify
- **Ramana-directed strategy review (DVPT→MEP→Wolfe§B→CPR→reversal-context): all 5 canonical pages verified ACCURATE vs live + the ledger — no overclaim, no fence needed softening.** The ONE binding gap was origins.md's `**Origin:**` header rule (S132j) being unmet by all 10 pages → CLOSED. **Live-walk (read-only curl pass) confirmed every claimed surface serves (DVPT /dash/stocks·/dash/index · MEP /dash/mep·overlay · Wolfe /dash/wolfe/scan·trades · CPR /dash/cpr·overlay · reversal `/dash/screen2?rev=ri|si`) — and caught ONE stale route string: wolfe-wave.md §5 named `/dash/markets/wolfe` (404); real nested route is `/dash/markets/wolfe-scan` (200, flat `/dash/wolfe/scan` 307→it) → FIXED this commit.**
- **Origin labels added to all 10 strategy pages** (distinct 🧑/🏠/📚 preserved — do NOT merge; Ramana's 🧑+🏠 collapse decision still PENDING) + **machine backstop** `test_every_served_page_declares_origin()` in `tests/test_strategy_docs_coverage.py` (a new strategy can't ship label-less; origins.md itself is EXEMPT — it IS the map). +3 origins.md map rows (RS · Harmonic · Momentum engine).
- **NEW canonical page `docs/strategies/reversal-context.md`** (STREAM BAND + FRACTAL FLOOR; 🧑 RAMANA; DESCRIPTIVE-ONLY, falsified at all 4 levels — cite ledger §§ 07-13/14/14b/14c before ANY re-attempt) — served via `_PAGES` + README matrix + terminology. The pre-existing RED `test_every_doc_is_served` was fixed on origin/main by the PARALLEL S147 lane (which SERVED origins.md); this lane ADOPTED that serve (reconciled in an isolated worktree). Gate GREEN (12 strategies).
- **`docs/reversal-pair-PLAN.md` RETIRED** (git rm; folded into reversal-context.md + ledger; DOC_INDEX/PROJECT_STATE/ledger refs redirected). ⚠ 3 hash-frozen prereg docstrings keep their `reversal-pair-PLAN.md` citation BY DESIGN (immutable `sha256(RAW __doc__)` — editing breaks `--verify`).
- **Aug-1 monthly churn = ARMED, not yet fired (future date):** `auto_portfolios.refresh()` clock-gated + wired in `10-signals.conf:14`; will add 2026-08 `auto_portfolio_nav` rows once Aug's first trading day lands (STEADY quarterly = Oct-1). Re-check row-gain after Aug-1.
- **✅ DEPLOYED + LIVE-WALKED (~18:47 UTC):** scp'd `reversal-context.md` (new file, clean) + **anchored-insert** of the one `_PAGES` line after the `cpr` anchor (surgical — the box's `strategies_view.py` is co-edited; a full-scp risked reverting a sibling's undeployed docstring drift, which has since landed as `c120d04`). py_compile + import (12 pages) + selftest green; writer-safe restart (no foreign writer; startup read-only per S146/S147). Live 200 on localhost **and public Caddy** (`/dash/strategy-ref?p=reversal-context` renders STREAM BAND / FRACTAL FLOOR; rail lists it; 0 "Ramana" leak — the 7 `[SD]\d{2,3}` hits are shared-CHROME false positives, identical on dvpt/cpr, not my content). Origin labels needed NO deploy (`_public` strips them). Backup `.bak-s147rev-*`.

## ✅ 2026-07-14 — S146: S-E PHASE 2 slice B — Pat DATA flows (FII positioning + rotation state) SHIPPED — do NOT redo; kickstart-pick-verify
- **NEW `src/pat/participants_flow.py`** — "are FIIs buying / FII flows / who's positioned" → FII net
  index-futures stance (net long-short + 2.5y percentile) from `participant_oi` (D62 fence). **NEW
  `src/pat/rotation_flow.py`** — "what phase is TCS in / rotation state of X / is INFY leading" → the
  stock's RS-weather phase + rank + trend from `stock_signals.rs_phase` (symbol-anchored, so market-wide
  "rotation" stays a navigate; RS-leaders board untouched). Both = self-limiting ₹0 pre-passes extending
  the chain (nav a-1c → news a-1d → whatchanged a-1e → participants a-1f → rotation a-1g).
- **Regression-clean:** Pat eval battery UNCHANGED; NEW `tests/test_pat_participants_rotation.py` (34
  contracts) + suite 348; zero forked-nav-trio edits.
- **NEXT S-E slice = the rest of Phase 2** (insider/ratings/SAST/holdings — per-symbol ownership, needs
  NEW per-symbol reads, no ready one to reuse · seasonal base rates · internals breadth · Wolfe
  open-trades) **then Phase 3** (education: explain-flows on the unified glossary + docs/strategies).
  Follow the `participants_flow.py`/`news_flow.py` pattern (new Pat file + ₹0 pre-pass + web render + eval/pytest).

## ✅ 2026-07-14 — S144: S-E PHASE 2 slice A — Pat DATA flows (news + what-changed) SHIPPED — do NOT redo; kickstart-pick-verify
- **NEW `src/pat/news_flow.py`** — "TCS news / latest headlines / news on RELIANCE" → inline headlines
  (reuse `news_tagging.news_for_symbol` + `news_view._recent_market_news`; ticker validated vs
  security_master → unknown falls back to market; copyright-safe title+source+link). **NEW
  `src/pat/whatchanged_flow.py`** — "what changed today / for TCS / any alerts" → the bus rail inline
  (reuse `signal_alerts.active_alerts`, critical-first; **FIXES the old "what changed today"→movers
  mis-route**). Both = self-limiting ₹0 pre-passes at engine.route (nav `a-1c` → news `a-1d` → whatchanged
  `a-1e`); a page-find stays `navigate`, and neither steals a screen ask.
- **Regression-clean:** Pat eval battery UNCHANGED; NEW `tests/test_pat_news_flow.py` (36 contracts) +
  suite 297; zero forked-nav-trio edits. ⚠ multi-lane: the classics lane had its whole feature STAGED in
  the shared index at commit time — state-doc gate caught it; reset out + `git commit -- <paths>`.
- **NEXT S-E slice = the rest of Phase 2** (participants/FII · insider/ratings/SAST/holdings · rotation
  states · seasonal base rates · internals breadth · Wolfe open-trades) **then Phase 3** (education:
  ground explain-flows on the unified glossary + docs/strategies so "explain the Wolfe methodology" works).
  Follow the `news_flow.py`/`nav_flow.py` pattern (new Pat file + ₹0 pre-pass + web render + eval/pytest).

## ✅ 2026-07-14 — S143: UX S-B1 (cross-links) — "Related lenses" connective tissue SHIPPED + DEPLOYED — do NOT redo; kickstart-pick-verify
- **NEW `infographics.related_strip(key, note="")` + `.rd-related` CSS in `readability_css()`** — a curated
  CROSS-GROUP "Related" chip row the left rail CAN'T express (capture-map ↔ rrg ↔ rsband are one
  relative-strength dataset spanning two rail groups). Labels/routes resolve from `lens_registry.BY_KEY` →
  never drifts; skip-safe on any bad/routeless key; **single-owner helper = ZERO forked-registry edit** (the
  S138 `_SUBTITLES` precedent — nav DISPLAY belongs in a single-owner module, never the forked trio).
  Delivers audit §8 items **4** (capture cross-links) · **9** (RS-family `_subnav` pattern, generalized) · **½ 8**.
- **Wired 1 line after `how_to_read_link()` into 7 views** (rrg · rotation · rsband · cycle-clock · capture-map ·
  sector-economics · momentum-scan). **momentum symbol cells now link to the dossier** (`/dash/stock?sym=…`;
  `data-v` preserved so the sort/CSV toolbar is unaffected) = the other **½ of item 8**.
- **✅ DEPLOYED + LIVE-WALKED (~16:13 UTC):** fork-check (md5, CR-strip both sides) = 7 base-matched → clean
  scp + on-box CR-strip (post-md5 == working tree); **`sector_econ_view.py` was FORKED-BEHIND on the box**
  (missing the Codex D8-F6 fiscal-year fix — that lane's undeployed drift) → ANCHORED INSERT of my one line
  only (count==1 asserted), leaving their drift intact (S134 surgical-hunk precedent). Remote import+app OK;
  writer-safe restart (blocking `ps` guard; wolfe-scan finished; 16:13 UTC clear of 14:01 bhavcopy). Caddy 200;
  all 7 strips render on real data, capture-map chips (Rotation·Map / Rotation·Band / Relative strength)
  resolve live, momentum→dossier confirmed. Full suite **247 pass** (the lone fail = S142's untracked
  `test_pat_nav_flow.py`, independent of my 8 files). Commit **`1cb0e89`** (clean FF push).
- **✅ S143-b (same session) — cross-links EXTENDED to 2 more families + DEPLOYED + LIVE-WALKED (~16:45 UTC),
  commit `56550c4`:** the **Ownership & filings** family (insider ↔ ratings ↔ sast ↔ shp) and the **Patterns**
  pair (harmonic ↔ wolfe-scan) — same `related_strip()` mechanism, `_RELATED` + 1 line per base-matched
  `*_view.py` (the route handlers are in forked `cockpit.py` but the page BODIES are in the base-matched view
  modules → clean scp). Suite **262 pass** (0 fail); all 6 chips resolve live via Caddy. **⚠ Restart-discipline
  real case:** the blocking writer-guard ABORTED on an active `signals --backfill-triggers`; I verified it uses
  **per-symbol commits** (the [[db-write-lock-backfill-outage]] FIX pattern) writing an UNRELATED table →
  WAL-safe reader-restart, so I restarted past it with an other-writer re-check (startup 200). **LESSON: when
  the writer-guard fires, verify the writer's commit-granularity + target table before deciding — a
  per-symbol-commit writer on a table your pages don't read is safe to restart past.**
- **✅ S143-c (same session) — S-B1 ITEM 1 DONE + DEPLOYED + LIVE-WALKED (~17:57 UTC), commit `bbee543`:**
  the Markets rail re-bucketed from 6 analytical categories into **8 TASK groups** — Today (attention · wire ·
  results-reactions · actions · event-cadence) · Market state (internals · move-anatomy · participants) ·
  Strength & momentum · Rotation · Sectors · Patterns · Seasonality (the calendar trio) · Events & surveillance
  (buyback · band-locks · surveillance). **DISPLAY-ONLY in the single-owner `left_rail.py`** — a `_GROUP_REMAP`
  (lens-key→task-group) + reordered `_GROUP_ORDER["markets"]`, applied only for the Markets altitude; the forked
  `lens_registry.group=` is UNTOUCHED (the S138 `_SUBTITLES` precedent — nav DISPLAY in the single-owner module,
  NEVER the forked trio; so NO anchored-insert was needed, clean scp). **+ a11y:** group headers are now real
  WAI-ARIA disclosures (`aria-controls`→body `id`, `aria-label="<group>, N lenses"`, `role="group"`). Active-lens
  auto-expand intact. **⚠ pre-existing sibling RED (NOT mine, flagged):** `test_strategy_docs_coverage::test_every_doc_is_served`
  fails on origin — `docs/strategies/origins.md` (landed by S132j `7e5745d`) isn't in `strategies_view._PAGES`;
  it's a 1-line fix in a strategies-lane forked file, left for that lane.
- **✅ S143-d (same session) — S-B1 ITEM 2 DONE + DEPLOYED + LIVE:** RRG-Map + Rotation-Weather merged into ONE
  "Rotation" lens with a Map⇄Weather toggle (commit `216ade4`; `infographics.rotation_toggle` + `left_rail`
  `_RAIL_HIDE`/`_RAIL_MERGE_HL` — display-only, forked registry untouched, both routes stay live). Live: rail
  shows one "Rotation" entry, toggle flips Map⇄Weather, `/dash/rotation` lights the merged entry.
- **Remaining S-B1 (OPEN — a natural next pick):** item **3** fold cycle-clock/sector-momentum/early-signals into the
  Rotation cluster · item **5** credibility-fingerprint → Credibility child · item **6** Ownership&filings
  placement · item **7** orphan sweep (§5 dispositions) · item **10** unify the 3 change-feeds on the bus ·
  item **11** single-source strategy one-liners in `lens_registry` · the reverse `/dash/sectors → sector-economics`
  link (lives in forked `cockpit.render_sectors` — owed). Then **S-B2** (route deprecation + POST-ify mutating
  GETs), **S-G** expert affordances, **S-E Phase 2+3** (Pat data flows).

## ✅ 2026-07-14 — S142: S-E PHASE 1 — Pat NAV-ANSWER coverage SHIPPED — do NOT redo; kickstart-pick-verify
- **NEW `src/pat/nav_flow.py`** — Pat now answers "where do I see X" from `lens_registry`: recognizes a
  locational ask, resolves the topic against the 66 routed lenses → link + one-line blurb (registry-
  generated, so a new lens is auto-covered; curated blurbs + label fallback + NL hooks in the Pat file).
  Wired at engine.route `(a-1c)` (self-limiting: yields unless a nav cue + a real lens match), render in
  `web.py:_navigate_flow`, `navigate` in `_VALID` + both dispatch paths. **Zero forked-nav-trio edits.**
- **Regression-clean:** the full Pat eval battery is UNCHANGED (navigate steals nothing); NEW
  `tests/test_pat_nav_flow.py` (41 contracts) + suite 262 pass; live-walked (breadth→internals,
  seasonality→seasonal-tape, rotation→family+chips; "which stocks are accumulating" NOT stolen).
- **NEXT S-E session = Phase 2 (data flows: attention "what changed today / for SYMBOL" · news/wire ·
  participants/FII · insider/ratings/SAST/holdings · rotation states · seasonal base rates · internals
  breadth · Wolfe open-trades) + Phase 3 (education: ground explain-flows on the unified glossary +
  docs/strategies so "explain the Wolfe methodology" works). KEEP closed-vocab deterministic templates.**
  Audit done-bar for S-E: coverage table ≥90% any-coverage; "what changed today", "TCS news",
  "explain Wolfe methodology" all answer.
- Claim-first convention held again (`1042445` pushed before touching Pat files).

## ✅ 2026-07-14 — S141: S-C ITEM 4 — Pat↔web GLOSSARY UNIFIED (D132) — do NOT redo; kickstart-pick-verify
- **ONE vocabulary now:** `docs/metrics-glossary.md` stays canonical; Pat's curated 52 stay the rich
  override layer; a defensive import-time adapter (`src/pat/glossary.py _merge_web()`) folds every
  uncovered md entry into Pat's schema → **199 entries / 29 families** (was 52/8). Adding a term to
  the md now automatically teaches Pat. Also: 19 genuinely-missing Pat terms back-filled INTO the md
  (+ a "How to read Patearn (concepts)" section) → web glossary 188→209 entries.
- **The AUD-40 explain eval is REFLEXIVE and scales with the merge** (390→1251 generated cases) — it
  forged the adapter's safety rules: speakable-lead terms · sane-alias probes · forbidden-word guard
  (no adapted slug may equal a word inside a curated probe phrase) · one-explainer-per-phrase.
  **Final: 1251/1251, battery PASS at baseline parity** (baseline re-run at HEAD in a worktree to
  attribute every failure first). 8 new contracts in `tests/test_pat_glossary_unify.py`; suite 210.
- Zero engine/web.py edits — the merge rides get/find/family. **S-E (Pat total coverage) is UNBLOCKED.**
- The claim-marker convention WORKED: claim pushed first (`20e1d4e`), sibling wraps routed around it.

## ✅ 2026-07-14 — S140: UX S-D SEARCH & ENTRY SHIPPED (D131) — do NOT redo; kickstart-pick-verify
- **NEW `src/web/symbol_search.py`** — the ONE name→ticker lookup: ranked `search()` over
  `security_master` (+`nse_equity_list` fallback) · `GET /dash/api/symbol-search` (durable
  `_ROUTER_SPECS` mount, always-200) · `did_you_mean_html()` · shared `TYPEAHEAD_JS`. 17 tests.
- **Wired everywhere:** ⌘K palette now REGISTRY-DERIVED (`ui_kit._palette_pages_json()`, 201 keys,
  every lens + legacy aliases, gate-enforced) with a live suggestion pane; home box takes company
  names (typeahead, plain-form fallback); stock-miss page shows "Did you mean: …" (defensive, never
  500s). **"Ask Pat" = a Trust nav lens now (D131)** — plain rail subtitle; the old "⌘K-summon-only"
  exempt/allowlist rows are retired. Walk-verified locally (name→dossier in 2 actions); suite 199 pass.
- **✅ DEPLOYED + LIVE (2026-07-14 ~14:50 UTC):** dashboard/cockpit now BASE-MATCHED on the box (clean
  scp); lens_registry/v2_surfaces/nav_integrity_gate still forked (live-only mounts) → anchored
  inserts, backups `.bak-s140-*`. Live: "tata consultancy"→TCS · miss-page "Did you mean: TCS" ·
  Ask Pat in the rail · box palette = 207 registry-derived entries (auto-includes live-only lenses).
- **⚠ Mutual-yield lesson (S137 doctrine's livelock case):** two lanes started S-D together and BOTH
  yielded on seeing each other → S-D briefly claimed by nobody. Fix that held: a PUSHED claim marker
  (`04d51ae`) before re-touching shared files. Claim FIRST, then build, when re-picking a
  yielded/contested item.
- **If the withdrawn /dash/find resolver (sibling design: 302 ticker→lens→name→Pat + pick-list page)
  is ever revived: build it ON `symbol_search.search()` — one lookup in the codebase, never two.**

## ✅ 2026-07-14 — S138: signal-bus OWNER-DM PAGER — BUILT + DEPLOYED + ARMED + VERIFIED (Ramana-directed) — do NOT redo; kickstart-pick-verify
- **NEW `src/automation/signal_alert_telegram.py`** — the bus's 5th face: a private owner-DM pager that DMs Ramana the newest **CRITICAL** alerts (the alert rail S123 built the surface; this is the delivery). Reuses `signal_alerts.active_alerts()` + `digest._send`; owns a `signal_alert_delivery` fire-once ledger (no `db.py` edit). 10/10 hermetic tests; full bus suite 37 pass. **DISJOINT** (bus-owned files only). Full record: PROJECT_STATE § Session 138.
- **✅ DEPLOYED + ARMED + VERIFIED (2026-07-14):** both files shipped (fork-check PASS, LF, backup); armed by **`Environment=HERMES_ALERT_DM=1` on the git-owned `60-signal-events.conf` drop-in** (commit `c23b6d5`) via `install-systemd.sh` daemon-reload (no start — AUD-95-safe). **⚠ ARMING GOTCHA:** NO hermes service loads `/opt/hermes/.env` into the process env → an `os.environ` flag in `.env` is INVISIBLE; the flag MUST live in the unit/drop-in (this is why it's in `60-signal-events.conf`, not `.env`). **Functional verify (real send):** manual `--push` DM'd the 2 pending criticals to the owner (`sent:2`), ledger recorded 2, second `--push` = 0 (`nothing new`) → fire-once confirmed. Next nightly bhavcopy `--detect` auto-DMs NEW criticals. Disarm = drop the `Environment=` line + re-install. PRIVATE owner DM (like season-digest), NOT the public channel (S-F). NO `hermes-api` restart was needed (pager runs only in the nightly `--detect` fresh process).
- ⚠ **Pre-existing drift surfaced (not mine):** `install-systemd.sh --check` flags 3 UNCAPTURED live-only seasonal units (`hermes-seasonal-stock.service`, `hermes-seasonal-events.{service,timer}`) — the seasonal lane owes capturing them into `scripts/systemd/vps-live/`.

## ✅ 2026-07-14 — S137: EDUCATION-COVERAGE GATE + THE FULL SWEEP — **63/63 COMPLETE, ALL DEPLOYED + LIVE** — do NOT redo; kickstart-pick-verify
- **The gate (`tests/test_education_coverage.py`, `b315e4a`)** — education twin of S133's route gate; enforces SURFACE-PLAYBOOK §3 item 3. Every routed lens must be **COVERED** (handler module calls `bottom_line()`+`how_to_read_link()` — derived at runtime from the app route table, never hand-listed), **EXEMPT** (glossary·reading-guide·strategy-ref, owner+rationale), or **PENDING** (documented debt). New un-scaffolded lens → FAIL. Auto-runs in `regression_sweep.sh` Gate 0.
- **Then 6 batches drove coverage 9 → 60 covered + 3 exempt = 63/63 · 0 pending · 0 offenders** — every batch deployed + live-walked same-session: screen2 (`3788a4f`) · harmonic/cycle-clock/sector-momentum (`ed442f4`) · divergence/early-signals/rs-hub/capture-map/band-locks/results-reactions (`e3e2550`) · 10 isolated Trust/meta incl. an anchored insert on box-forked `strategist_view` (`2db52bd`) · **the 15-lens `dashboard.py` cluster via ONE `_edu(bl)` helper + one-line `_shell` wraps, co-edited `cockpit.py` untouched** (`9c4602e`, deployed by on-box `git apply`, post-apply md5 == HEAD) · **tracker×5 on BOTH render paths** (`6b9ce46`: owner `_TRACKER_BL`+`_edu`; demo `tracker_gate._edu_demo`, SAME texts, fail-open) · **`wolfe_trades._bottom_line` folded into the shared band** (`532265e`, guards+tests intact 22/22). Bottom-lines written FROM module docstrings (two were wrong from lens labels — corrected pre-commit); every ledgered fence honored (MEP/CCI falsified→"never a rank", launchpad "no edge net of cost", etc.).
- **⚠ Deploy-craft lessons (recorded in PROJECT_STATE §S137):** a `&&`-chained `fuser` check PRINTS but does NOT block — make it a real `if`-gate (done in the last deploy); **never restart hermes-api ~13:55–14:15 UTC** (bhavcopy fires 14:01; one restart landed at 14:00:5x — seconds early, no harm). **Pre-existing, NOT S137** (verified at committed HEAD in an isolated worktree): the local harness venv's TestClient crashes (`'str' not callable`) when the OUTERMOST BaseHTTPMiddleware short-circuits (tracker demo/owner-form) — a starlette-version artifact; **the box serves the same paths fine** — verify demo paths at unit level + live curl.
- **The VPS `dashboard.py` is NO LONGER forked** — byte-identical to HEAD (the D80 fork was reconciled by recent lanes). The full-scp ban's premise is gone but the doctrine stands: **fork-check md5 decides** (scp / anchored-insert / on-box git-apply), and dashboard.py deploys stay patch-based (a race fails cleanly instead of silently reverting).
- **Only education residue: the stock-DOSSIER top strip** (`/dash/stock` — a dossier, not a lens; outside the gate's scope) has no scaffold. Optional polish, not gate debt.

## ✅ 2026-07-14 — S134: S-C EDUCATION (items 1 + 7) SHIPPED + DEPLOYED + LIVE-WALKED — do NOT redo; kickstart-pick-verify
- **Item 1 — shared `infographics.fence(kind, detail="", *, cap=False)` (`41a5b81`).** Single source of the descriptive-only boundary wording (the audit's "≥9 phrasings across ~24 sites"). `_FENCE_COPY` = the sanctioned vocabulary; unknown kind = hard `KeyError` (selftest-asserted); `detail` keeps page-specific leads verbatim; `fence_note()`+`.rd-fence` for new pages. **11 sites migrated BYTE-EQUIVALENTLY** (insider/sast/shp/ratings=not_advice · participants=context · move-anatomy=not_signal · launchpad/screen+=not_reco · strategist=not_buy/not_sell · buyback=arithmetic). **Deferred, NOT drift:** forked cockpit/seasonal, JS chart-chip `title=` tooltips, bespoke bandlock M-04 banner, prose tails (market_internals:389/results_reactions:408).
- **Item 7 — site-wide "New here?" on-ramp in `ui_kit.topbar()` (`4c6df9a`).** First tried `dashboard._shell` → **never rendered** (`shell_skin.reskin()` replaces dashboard's `<header>` with the ui_kit topbar at runtime). Correct home = `topbar()` (both native `K.shell` + reskinned legacy flow through it) → one inline link on **every** `/dash` page (live-verified home/insider/coverage/screen2/reading-guide). **LESSON: the live chrome is `ui_kit.topbar` / `shell_skin`, NOT `dashboard._shell` — the skin owns the header. Any future chrome edit goes there.**
- **Loose item CLOSED — "Ramana" stripped from chrome (`cca86d4`).** Two CSS comments shipped to every page's `<style>` (dashboard `_BASE_CSS` + shell_skin skin CSS) → `curl` grepped 2× "Ramana"; neutralised to "the desk". Live re-walk = **0** rendered "Ramana" site-wide. (The S-C inventory agent wrongly called it comment-only — verify chrome leaks with a live `curl | grep`, not a source read.)
- **Deploy craft that held (multi-lane, 3 sibling lanes active):** deploy `git show HEAD:` NOT the working tree (a parallel lane's uncommitted reversal-context contaminated `screener_plus.py`; my committed fence was preserved by their own deploy). CR-strip BOTH sides in fork-checks (`core.autocrlf=true` → git blobs are CRLF; one-sided strip false-flagged all 12). When HEAD moves past your commit mid-session, `HEAD~1` becomes YOUR commit → re-anchor fork-checks on the explicit base SHA. Anchored in-place replace (assert count==1 + rollback) for D80-forked `dashboard.py` + pre-S128-drifted files; clean scp for base-matched isolated modules.
- **⚠ Observed drift (not mine to fix): the S128 Codex fence-sweep (`5c6720f`) is UNDEPLOYED on the box for `participants_view`/`launchpad_track_view`/`strategist_view`** (VPS shows pre-S128 stance_read / "6 months" label / composite-score ORDER BY). I deployed ONLY my fence hunk there (surgical), leaving their drift for the S128/Codex lane to complete.
- **Remaining S-C queue (next education session, in order):** ~~**item 2**~~ **✅ MOSTLY DONE S136** — readability scaffold (`ifx.readability_css`+`bottom_line`+`how_to_read_link`) back-fit to **11 of 14** pre-sprint pages (insider·ratings·sast·shp·rotation·momentum·growth·wolfe-scan·wire·rrg·rsband). **Item-2 remainder (3 hot/forked targets left disjoint):** `screen2` (`screener_plus.py` — reversal lane active) + stock-dossier TOP strip & `concalls` (both in D80-forked `dashboard.py`) + fold `wolfe_trades._bottom_line` into `ifx.bottom_line` (polish). **item 3 — PARTIAL (S136 follow-on):** `?q=` glossary links added to the 4 RS-family pages whose anchor terms EXIST in the glossary (rrg/rotation/rsband→rs-ratio/mansfield, momentum→momentum); the 4 filings pages already had links. **Remaining item 3:** growth/wolfe/wire have NO matching glossary terms — they need TERMS added to `docs/metrics-glossary.md` FIRST (a corpus pass; that file is HOT), then a link; and the richer `gloss()` per-metric popovers are still un-done. NB `?q=` is CLIENT-side filtered (server returns the full glossary for any q — always valid, never 404). **item 4** — unify Pat's 52-term dict onto the 405-key web glossary (`docs/metrics-glossary.md` via `glossary.lookup/terms`); genuine schema mismatch + Pat's `engine.py`/`web.py` are forked by a parallel Pat lane → **its own session; S-E depends on it.** ~~**item 3**~~ **✅ DONE S138 (`8e69fdb`):** RISKADJ glossary term added (was undefined) + growth `?q=` link (its terms already existed); wire left as-is (news). ~~**item 5**~~ **✅ DONE S138 (`585d54b`):** plain subtitles on the 7 metaphor nav labels — **NO forked-file edit** (subtitle map + render in the single-owner `left_rail.py`, a nav-DISPLAY concern; the audit's "subtitle-field-on-Lens" framing was avoidable). **⚠ WHOLE S-C WEB ESTATE NOW DEPLOYED + LIVE** (was 0% live — the education lane deployed only its own files; I fork-checked + scp'd all 11 views + metrics-glossary + left_rail, 3 writer-safe restarts, Caddy-walked). **S-C COMPLETE bar item 4 (Pat glossary — its own session).**

## ✅ 2026-07-14 — S133: S-H no-orphan ROUTE-REGISTRY GATE SHIPPED (`181fd01`, on origin/main) — do NOT redo; kickstart-pick-verify
- **`tests/test_dash_route_registry.py`** — the structural gate the audit §8 / `SURFACE-PLAYBOOK.md` §5 name. Every `/dash` route `src.main` serves must classify into ONE RouteKind (`lens`·`nested_child`·`dossier`·`api_or_action`·`compat_redirect`·`internal_dev`·`exempt`-with-owner+rationale). `lens`+`compat_redirect` DERIVED from `lens_registry`+`nested_nav` (no drift); the rest are machine-readable tables seeded from the §5 orphan inventory. Unregistered route → FAIL (2 synthetic-orphan proofs), SURFACE-PLAYBOOK checklist in the message. **158 paths classify clean; 7 pytest contracts green; full suite 149 passed.** Test-only/additive (no src/scripts, no deploy); **auto-run by `regression_sweep.sh` Gate 0** beside `nav_integrity_gate.py`.
- **To satisfy it when adding a page:** register a `Lens` (or add the route to exactly one machine-readable table in the test WITH owner+rationale) — prose in a doc does NOT count (playbook §5). Complements, does not replace, `scripts/nav_integrity_gate.py` (rendered-reachability).
- **Deferred (S-D):** ⌘K palette generated from `lens_registry` (kills the hand-maintained PAGES map) — a shared-`ui_kit.py` change, not parallel-safe. **Next UX pick: S-C education-everywhere.**

## 🔧 2026-07-13 — S123 P1 AUDIT-INTEGRITY SWEEP (a DISJOINT lane from S-A/UX) — do NOT redo; kickstart-pick-verify
- **6 audit P1s resolved + the alert-rail triage surface — all deployed + live** (full record: PROJECT_STATE § Session 123, bullets S123/-b…-n; all commits **local/unpushed** — they ride the shared-main push):
  - **Alert rail** = the bus's 4th face, LIVE at `/dash/attention` (build → dismiss → filter): `8241bba` / `ea7451c` / `5ebee3c`. New reusable `src/automation/signal_alerts.py`.
  - **AUD-37** /v1 metering audit-grade + **per-tenant quotas** (`9e53aae` / `76694e1`) · **AUD-25** feed-liveness (`c1405dd`) · **AUD-22** research PIT re-validation — momentum still BETA, residual-α t 1.99→1.80 (`891a50f`) · **AUD-14 FULLY CLOSED** across all 6 archive fetchers via a NEW shared `src/automation/fetch_retry.py` taxonomy (`b1328c0` bhavcopy+indexes+participant_oi · deals=AUD-53 · corp_actions `b00bfa4` · equity_list `66f7b16`) · **AUD-28** setup-news.sh no longer reverts live units (`867ef00`, delegates to install-systemd.sh).
  - **AUD-12** VERIFIED real+MATERIAL → routed to **codex D2-F1** (NOT double-fixed — codex-owned + needs a coordinated VPS rank re-run; fix recipe = PIT `security_master.universe_on()` join, in the AUD-12 audit block).
  - **⚠ ONE RESIDUAL — AUD-22 remainder** `gate_residual_alpha` PIT fix (`7ed6f95`, committed + locally-verified) but the **VPS re-run is BLOCKED**: the box's `research/cci/` is an OLDER snapshot (its `common.py` lacks `MIN_RESOLVED_ASOF` that HEAD imports), so a single-file deploy ImportErrors there. **NEXT:** a coordinated `research/cci/` → HEAD deploy (common.py is shared) activates the fix; box was restored to its consistent older version. LESSON: before deploying one module of a package, confirm its intra-package deps are current on the box.
- **Reuse, don't rebuild:** `fetch_retry.RetryableFetchError` for any new NSE/BSE archive fetcher; `signal_alerts` for any new bus-alert consumer.

## 🆕 2026-07-14 — S132 STRATEGY LANE COMPLETE + PUSHED (reversal arc → portfolios estate; do NOT redo — kickstart-pick-verify)
- **SHIPPED + LIVE + PUSHED (20 commits `d0ecda4`…`7e5745d`):** ① reversal pair falsified at ALL levels via 6 hash-frozen pre-registered studies (ledger §§ 07-13→07-14e; incl. the measured EXIT LAW: looser=better, band-only 0.49/trail5 0.49 ≫ tight; profit-takers worst; Ramana's Case-A stack −0.50 killed by the 2-candle exit) → survivors live as Screen+ "rev" group + ⚠ reclaim/slip pills (`?rev=ri|si`); ② `/dash/momentum-scan/slow` (STEADY quarterly anchor); ③ `/dash/factor-league` (classics ranked by OUR numbers + PACER/SPRINTER rosters + churn); ④ **`/dash/model-portfolios` — 4 engine-locked model portfolios reconstructed since 2012-06** (SPRINTER 24.6× · PACER 18.3× · CRAFTSMAN 10.6× · STEADY 9.4× vs N500 6.0×; `?asof=` time-travel · since-chips · story · Origin badges; engine `auto_portfolios.py` = the ONLY writer); ⑤ `docs/strategies/origins.md` — BINDING 🧑 RAMANA / 🏠 HOUSE / 📚 CLASSIC taxonomy + documentation loop.
- **NEXT QUEUE (Ramana-directed, in order):** ~~① **review of his OWN strategies**~~ **✅ DONE S147** (DVPT→MEP→Wolfe§B→CPR→reversal-context all verified accurate; origin labels + reversal-context.md page + machine backstop landed); ② his PENDING decision: collapse 🧑+🏠 into one proprietary class — **explicitly do NOT change until he says** (S147 kept them distinct); ③ verify first automated churns fire — **S147: Aug-1 monthly = ARMED (clock-gated `auto_portfolios --refresh`, `10-signals.conf:14`), row-gain re-check due AFTER Aug's first trading day; STEADY+slow-rotation Oct-1 still pending**; ~~④ `docs/reversal-pair-PLAN.md` retirable~~ **✅ RETIRED S147** (folded + git rm; 3 hash-frozen prereg docstrings keep the old citation by design); ⑤ classics catalog = the SIBLING lane's (famous_strategies/classics_view) — do NOT duplicate.
- **Gotchas that bit (4× shared-index races!):** siblings stage mid-flight — put `git diff --cached --stat` check + `git add <explicit paths>` + `git commit` in ONE command AND verify `git show --stat HEAD` after; unwind = soft-reset + selective re-commit + re-stage theirs (disclose in message). Prod venv = STDLIB ONLY (no numpy); `_ro()` returns tuple rows (set `sqlite3.Row`); `get_conn()` is a @contextmanager; VPS `lens_registry.py`/`v2_surfaces.py` are FORKED — anchored on-box patches only, never scp; DB-locked reads → `sqlite3 -readonly -cmd '.timeout 20000'`; manual module runs need cwd `/opt/hermes`.

## 🆕 2026-07-14 — S-A FRONT DOOR SHIPPED + DEPLOYED + LIVE-WALKED (two sessions: sibling `a6396dc` + this lane `1b6578a`/`a090fb1`) — do NOT redo; kickstart-pick-verify
- **ALL S-A P0s CLOSED ON THE LIVE SITE:** P0-1 `?symbol=` dead links (sibling, 5 links) · P0-2 orientation (hero identity line + numbered Start-here strip + plain-English subtitles on all 18 tiles + "every tile is a live screen" header) · P0-3 ONE regime vocabulary (**NEW `src/web/market_mood.py`** — Upbeat/Mixed/Cautious, strictest-clock-wins with the kill-switch; home + Markets banners lead "Market mood:", per-index verdicts behind "trend:"; dq_banner + banner "why?" now expand INLINE) · P0-4 RS-band verbs (code was already relabeled in `5c6720f`; rsband.py+rsband_view.py now DEPLOYED — live shows "Re-rating (uptrend)"/"De-rating (downtrend)") · **P0-6 tracker = DEMO-BOOK (Ramana decision 2026-07-14)** — **NEW `src/web/tracker_gate.py`** middleware: anonymous → synthetic demo book on all tracker pages, ALL tracker writes+exports owner-gated (were public!), owner unlock POST `/dash/tracker/owner` (sets pt_owner hash + the perimeter's hermes_key so ONE unlock passes BOTH layers; sibling's perimeter 403-gate kept as defense-in-depth). Plus: flagship "Why this is different" band + "Prove it" card, news wire board ON HOME, `infographics.demo_framing()` on testing/spec-sheets/seasonal-0-cert, ⌘K lowercase-ticker fix, stock-miss page routes onward (Pat/screener).
- **Remaining S-A deltas (small):** humanize the home Attention event strings (deferred — `attention_view.py` was hot mid-flight; now free) · strategy-ref public intro is S-C's · **P0-5 strategy-ref doctrine leak → DONE (S-C, `4aa45c4`, deployed + live-walked):** render-time `_public()` sanitizer in `strategies_view.py` strips the governance blockquote, session/decision IDs, commit hashes, "Ramana", "CANONICAL — do not archive", the doc-authoring template + governance table column (source docs untouched; Guardrail #9); guarded by a selftest leak-assert; all 10 pages clean. ⚠ residual 2× "Ramana" on the live page is in the SHARED SHELL CHROME (every `/dash` page) — a separate site-wide follow-on, owned by the chrome lane. Live walk verified every shipped item (curl transcript in session).
- **⚠ TWO shared-tree absorption incidents tonight (multi-session-safety lessons):** (1) my uncommitted `seasonal_view` demo_framing hunk was absorbed by the seasonal lane's commit → **prod incident** (helper missing on box) → they guarded (`ebf5fdb`), my commit later made the helper real; (2) my quick `a090fb1` swept the seasonal lane's STAGED wrap (their PROJECT_STATE S130 reconcile + 2 transient-doc deletions) — content complete+correct, attribution off; seasonal lane: your reconcile IS committed, don't redo. RULE REINFORCED: `git diff --cached --name-only` before EVERY commit, not just the big ones.
- **S-A-c defect pair (fixed, `a090fb1`):** a local `_q` in dashboard's stock-miss branch shadowed the module-level `_q` helper (UnboundLocalError on every stock page) AND tracker_gate's fail-closed try wrapped `call_next` (dressed every app error as the demo page). Lesson for gates: call_next runs OUTSIDE the fail-closed try.
- **PROJECT_STATE:** the seasonal S130 entry landed (via a090fb1); the S127 audit + S-A entries are still OWED to the next clean reconcile.
- **Next UX picks per the audit §8:** ~~S-H route gate~~ **✅ S133** → ~~S-C items 1+7~~ **✅ S134** → ~~S-C items 2/3/5~~ **✅ DONE + DEPLOYED S136/S138** → ~~S-D search/entry~~ **✅ S140 (D131)** → ~~item-2 tail~~ **✅ S137 full sweep (63/63 lenses covered — screen2·dashboard-cluster incl. concalls·tracker×5·wolfe_trades fold ALL scaffolded + LIVE; only the stock-DOSSIER top strip remains, a non-lens polish)** → ~~item 4~~ **✅ S141 (D132 — the glossary is ONE vocabulary; S-E UNBLOCKED)** → ~~S-E Phase 1 (nav-answer)~~ **✅ S142 (`nav_flow.py`)** → ~~S-E Phase 2 slice A (news + what-changed)~~ **✅ S144** → ~~S-E Phase 2 slice B (FII positioning + rotation state)~~ **✅ S146** → ~~S-E Phase 2 slice C (market internals breadth)~~ **✅ S148 (`internals_flow.py`)** → **NEXT free pick: S-E Phase 2 remainder (insider/ratings/SAST/holdings per-symbol ownership [needs NEW reads] · seasonal per-symbol base rates · Wolfe open-trades) + Phase 3 (education on the unified glossary)** or **S-B1 remainder** (rail task-groups · RRG⇄Rotation merge · orphan sweep · registry one-liners — coordinate, that lane is hot). `docs/ux-journey-audit-2026-07-13.md` §8 has the paste-ready statements.

## 🆕 2026-07-13 — S127: JOINT Claude+Codex USER-JOURNEY AUDIT + SURFACE-PLAYBOOK LANDED (`eecc577`) — the UX remediation program is now THE queue
- **Ramana directive (verbatim intent):** full user-journey/UX deep-dive for beginner→expert personas, combined Claude+Codex analysis with autonomous dialogue, session-by-session problem breakdown, Pat total enrichment, approval-gated Telegram-channel publishing, news unburied, and future-proofing docs so nothing ever lands as an orphan again.
- **Delivered (all committed `eecc577`):** `docs/ux-journey-audit-2026-07-13.md` (converged findings + the **S-A…S-H session program with paste-ready problem statements** + joint Top-12) · `docs/SURFACE-PLAYBOOK.md` (**CANONICAL+BINDING** — decision tree + landing checklist; wired as CLAUDE.md Guardrail #9 / AGENTS.md #7 / DOC_INDEX) · `docs/codex-review/UX-CODEX-INDEPENDENT.md` + `UX-DIALOGUE-R1-CODEX.md` (dialogue converged R1: 14/14 findings confirmed, 3/3 pushbacks conceded).
- **P0s found (fix in S-A, first UX session):** home Attention links dead (`attention_view.py:144` emits `?symbol=`, route reads `sym`) · no orientation layer on home · THREE regime vocabularies (RISK-OFF/Cautious/UP-BIASED) · **tracker exposes Ramana's live portfolio publicly (day-zero DECISION: auth vs demo-book vs hide)** · `/dash/strategy-ref` leaks internal doctrine language (S111/Ramana/CANONICAL) to the public · RS-band Avoid/Ride/Fade verbs STILL live at HEAD post-fence-sweep (coordinate with the codex-lane D2-F4 adjudication — verbs confirmed present in `rsband_view.py:145,347-352` after `5c6720f`).
- **Program order (converged):** S-A front-door (+S-H route-registry gate in parallel) → S-C education-everywhere → S-D search/entry → S-B1 IA labels/cross-links → S-B2 route deprecation+POST-ify GETs → S-E Pat total coverage (2 sessions; AFTER S-C so Pat consumes the unified glossary) → S-F Telegram approval-gated channel publisher → S-G expert affordances. Ramana will paste per-session problem statements from the audit doc §8.
- **Key measured facts (don't re-derive):** 62 lenses / home shows ~37% / Markets rail 30 lenses / Pat reaches 9 full + 9 partial of 62 (71% dark) / education = two disjoint half-systems (scaffold ~11 modules, glossary ~30, both = 3) / fence has ≥7 phrasings, no shared primitive / TWO glossaries (web 405 keys vs Pat 52) / server CSV on ~3 tables / news pipeline rich but wire = last item of a collapsed group + `/dash/news` dead-end / 10 orphan routes + `stock_oscillators` data-orphan.
- ⚠ **PROJECT_STATE session-log entry for S127 is OWED** — the file was mid-edit by the active codex-integrity lane all session; the S127 bullet rides that lane's reconcile or the next clean session (S121 precedent). Docs-only commit, so no state-gate conflict.

## 🆕 2026-07-13 — CODEX-INTEGRITY LANE CLOSED: hedge_density code+data review + v2 built/tested → NULL (all on origin/main; do NOT redo — kickstart-pick-verify)
- The "codex-integrity lane" referenced above (S127 §16 / the D2-F4 handle) is **DONE + PUSHED.** A Codex-CLI-led code review + 3-way internal-panel data review of the frozen FAIL-null `hedge_density` study, then the Ramana-greenlit **v2 successor BUILT + TESTED**. Commits (all on `origin/main`): `c33d056` (code fixes + ledger honesty addendum) · `8ce1f0e` (frozen `hedge_density_v2_PREREG.md`) · `f2b15eb`+`bdc31e0` (S124 log + v2 addendum) · `62ea68b` (v2 module) · `ffcd8e0` (v2 result). VPS `hedge_density.py` deployed byte-verified; feature caches `concall_lexical` + `concall_lexical_v2` rebuilt.
- **FINDING (blocking, ledgered — do NOT re-mine):** concall lexical TONE carries **NO certifiable 60-day signal on return OR volatility.** v1 (return) FAIL was mis-specified — 64.7% ubiquitous-modal density; SPIKE tercile = 50-59% Q2 guidance-season (a seasonal confound). v2 fixed it ALL (register-split net-tone, negation, overlap-dedup, "may"-dropped, within-name×within-CALENDAR-QUARTER double-difference, forward realized-**VOL** outcome; gate hash `632bd149` registered BEFORE the run, `--verify` tamper-clean) → still **FAIL-null** (SPIKE vol-uplift −0.0084 / t_cohort −0.43; both halves negative; Cliff +0.001). Honest breadth = **1,097 delta-eligible symbols / 15,824 calls** (the ledger's original 1,573/16,140 were corpus counts, corrected).
- **Reusable (future codex/verify work):** prereg hash = `sha256(RAW __doc__)` — `ast.get_docstring()` defaults `clean=True` and DEDENTS → a different digest (this caused a false "drift" scare, corrected). The "codex review" doctrine (Codex leads · internal panel + Claude review · change only what survives, convince-or-panel-unanimous; Windows sandbox → `--dangerously-bypass-approvals-and-sandbox`; VPS read-only SSH for data) is memory [[codex-external-review-workflow]].
- 4-panel data-review artifact LIVE: `claude.ai/code/artifact/eea7cfd2` (modal Pareto · Q2 seasonal grid · register dumbbell · v2 vol-null). **This lane has NO open items — CLOSED.**

## 🆕 2026-07-13 — S123: the signal-event bus's FOURTH face (alert rail) SHIPPED + DEPLOYED + LIVE (do NOT redo — kickstart-pick-verify)
- **Alert rail = the 4th "bus face" (the `signal_events.py` header names all four: /v1 · Attention Queue · since-you-last-looked · **alert rail**).** Three were built (S103/S108); this built the 4th. LIVE at the TOP of **`/dash/attention`** (→ `/dash/markets/attention`): a curated, edge-triggered (fire-once), multi-day, severity-graded feed of only the highest-impact state-changes — a STRICT SUBSET of the queue below. **Commit `8241bba`** (⚠ **committed locally but NOT pushed** — origin/main=`76f5724`; the 4 commits before mine are the seasonal lane's unpushed work, so mine rides their next shared-main push; do NOT force). **DEPLOYED + walked** (40 seed alerts: 3 crit/37 high; mep 18·oi 12·cci 6·deal 4; rs 0 = no rs events yet).
- **NEW `src/automation/signal_alerts.py`** (owns isolated `signal_alert_state`; no db.py edit) + additive edits to `src/web/attention_view.py` (`render_alert_rail`, inside the already-mounted route → **zero forked-nav edits**) + `src/automation/signal_events.py` (+`backfill(8)` piggyback on the `--detect` step-60 → **no systemd unit change**). Rule-based `classify()` (deal top-decile percentile / cci numeric-delta deterioration / mep+rs **ordinal band moves** / oi quadrants), each tagged a descriptive valence; same D106 honesty fence.
- **An adversarial-review agent caught + fixed 6 defects PRE-SHIP** (tests had matched code, not data): rs lens was DEAD (real vocab `INSIDE/TOUCH_SUP/TOUCH_RES`, not `SUPPORT/RESIST`) · mep valence inverted on intra-family moves (fixed via ordinal from→to) · deal "critical" degenerate · cci null-forced-down · multi-clock feed lag (promote windowed) · window off-by-one.
- **S123-b/-c (same session): the rail is now a full TRIAGE SURFACE — surface → filter → dismiss — LIVE (`ea7451c` + filters, unpushed).** **Dismiss:** `acknowledged_at` col (idempotent ALTER migration) + `GET /dash/attention/ack?id=N|all=1` (the one web-write, 303 back, defensive) + per-row `✕` + "dismiss all" (LIVE-view only). **Filters:** `?asev=`/`?aval=` severity + valence chips (All/Critical/High · ▼Risk/▲Opp) with counts, coexist with the queue `?lens=`, filtered-empty → "clear the filter". Deployed + ack round-trip verified (30→29→restored). Full bus suite **57 pass**. **Full bus suite 54 pass.** Disjoint from the codex + seasonal lanes (bus-owned files only, no forked file). **The LAST unbuilt bus face is now the SSE live stream** (low value at the nightly cadence — nothing streams intraday; consider the Telegram-push follow-on instead).
- **S123-d/-e (same session): AUD-37 CLOSED + /v1 per-tenant QUOTAS — both LIVE (`9e53aae`, `76694e1`, unpushed).** The `/v1` metering is now audit-grade (500s metered · real `bytes_out` via Content-Length · no silent drops · error-response headers) AND carries a nullable per-tenant `daily_quota`/`monthly_quota` (NULL=unlimited, fail-open, `keys.set_quota`/`--set-quota`), enforced beside `rate_check` → 429. **Live-proven on the box** (401 now records `bytes_out=162` vs 0; a throwaway tenant with `daily_quota=1` → 200 then 429). 9 pytest regressions. All 6 `/v1` files were fork-checked (md5==HEAD-base) before scp. Full record: PROJECT_STATE § Session 123 (S123-d/-e) + audit doc AUD-37 CLOSED.
- Pattern that held all session: X-04 (overnight/intraday split) was ABANDONED after the VPS gap data exposed the corporate-action trap (MWL/PSUBANK −90% = splits, not gaps) — corp-action-clean prices are exactly the `signals.py`/`adjust.py` territory the codex lane is fixing; the wrong pick right now. Full record: PROJECT_STATE § Session 123 (+ S123-b).

## 🆕 2026-07-12 — S120 + S121 landed (both on origin/main; do NOT redo — kickstart-pick-verify)
- **S121 / D120 — Wolfe "Open trades — remaining ROI" view SHIPPED + LIVE (`7c4fd74`).** The ONE
  designed-not-built feature is done. **`/dash/wolfe/trades`** — every OPEN winner-profile trade
  (p5 printed, EPA 1-4 NOT touched, ANY age) ranked by remaining ROI from CMP (run%/risk%/R:R), with
  9 server-side filters (Size · Sector `company_tags` · Direction · Max-age · min-Q/top20 · min-room% ·
  Status · **min-liquidity** = the TIRUPATIFL lesson · min-R:R) + 4 sorts. **LIVE-verified on the VPS:
  736 open trades render; every filter narrows server-side** (minliq 736→725→593→393; top20→20;
  maxage15→60; Pharma→63). Isolated `wolfe_open_signals` table + `--persist-open` piggybacked on the
  `hermes-wolfe-scan` timer (NO unit change). NEW `wolfe_trades_view.py` mounted onto `wolfe_view.router`
  via the durable include — **needs NO `v2_surfaces`/`lens_registry` edit** (that's how it sidestepped
  the S120 seasonal lane on those forked files). Additive — detection/§A/§B/`winner_scan`/point-4
  UNTOUCHED. 5 new tests (`tests/test_wolfe.py`, 13/13). ⚠ An adversarial 16-agent review caught a
  persist bind-count blocker (27 of 29 cols) an empty-rows smoke test can't surface — FIXED + guarded.
  Then a same-session **bottom-line insight band + server-side CSV export** (`282081f`) and a
  **metric-semantics fix (D121, `ba02287`, panel `wf_dd906a08`):** the live 736-row snapshot was
  dominated by ancient un-triggered waves (73% >1yr) whose extrapolated 1-4 EPA gave negative targets /
  +12000% "room" → panel ruled KEEP the canonical formula (don't fork it) + **age-cap the ranked
  population at 252 bars (1yr) + coherence floor + DISCLOSE the held-out count + standout guards**.
  Live now: **140 ranked + 596 disclosed-held-out**, bottom-line sane. Tests 17/17. Then a **NAV fix
  (`9bb04f5`, D120 correction — Ramana: "I don't see this page at all"):** the view had been mounted
  WITHOUT a lens (to dodge the co-edited nav files), leaving it orphaned/invisible. Then — after
  Ramana said "there is no such thing as Wolfe Trades, I see it as Wolfe Scan" — **MERGED into ONE
  'Patterns · Wolfe' tab with a Fresh setups ⇄ Open trades toggle** (`dd17892`, the plan's "?view=open"
  option): removed the `wolfe-trades` lens (62 lenses), shared `wolfe_view_toggle` atop both views, open
  view emits `active="wolfe"` (highlights the one tab), reached via the toggle at `/dash/wolfe/trades`
  (flat; `/dash/markets/wolfe-trades` now 404). Deployed `lens_registry.py` by ANCHORED INSERT then
  anchored-DELETE (VPS forked/behind HEAD; backups `.bak-navlens`/`.bak-navmerge`). LESSON: match the
  user's IA mental model — one Wolfe page/two views, a toggle not a second tab. **+ STICKY FILTERS
  (`a2dcf06`, Ramana: "I dive into a result, do a study, and return — the filters I set are gone"):** the
  active filter+sort set is remembered in a `wolfe_open_filters` cookie (30d, httponly); a bare return
  visit 307-redirects to the saved querystring so the analyst returns to their shortlist, not the full
  140; `?clear=1` wipes it; CSV never redirects (D110-style client-cookie). **+ ROW-CLICK DRAWS THE CORRECT
  WAVE (`7dbeb79`, Ramana: a 211-day-old TATAPOWER entry opened its LATEST wave):** the row now passes
  `p5date+p4date` (two waves can share a p5) and `wolfe_page` uses `analyze(all_waves=True)` + selects
  the exact wave, framing to it; p5 date shown in the age cell; "↗ Open full stock chart" link →
  `/dash/stock?sym=…&wolfe=<p5date>` auto-selects the same wave (new `p5_time` in `_wave_payload` +
  `wolfe_overlay.py` load-time match). Live-verified on TATAPOWER (frames to 2025, header "setup of
  2025-08-29"). EPA = the 1-4 line (p1→p4) extended to today. Live-verified. PLAN doc retired.
  **▶ 4-lens improvements brainstorm (`wf_67b9dbb9`) → 12 prioritized ideas. Ramana picked QUICK WINS
  #1-3, SHIPPED + LIVE (`6319654`):** split "watch" + signed distance-to-zone (`zone_gap_pct`) + a
  Proximity filter (≤2/5/10%, 10 filters now) · sticky symbol column + header · symbol as a real `<a>`
  (new-tab fanning). **THEN Ramana "grow fully" → ALL 9 remaining items BUILT + LIVE (`4fdf119`, 22
  tests):** #4 dual target run→T1 beside run→EPA · #5 age-graded EPA muting (`~`) · #6 ATR-normalized
  risk + razor flag (NEW `atr_pct` persisted col — re-persist done) · #7 §B breakdown tooltip on Q ·
  #8 RS with-trend/counter-trend label + min-RS filter · #9 breadth/concentration strip · #10 snapshot-
  staleness banner · #11 inline price-ladder micro-column (SL·zone·CMP·T1·EPA SVG) · #12 "what changed
  since you last looked" (NEW/→in-zone/→stopped via a `wolfe_open_seen` cookie diff). 11 filters; CSV
  gained run_t1/atr_pct/gap_to_zone. Live-verified (T1 subs, `~`-muted EPAs, 70 ×ATR cells + 21 razor
  flags, 140 §B tooltips + 140 ladder SVGs, breadth "47 bull · 93 bear", min-RS=70→25). The Wolfe
  open-trades tool is now feature-complete against the brainstorm. Memory
  `wolfe-wave-strategy` updated. ⚠ **Three `state:skip` commits (`282081f`/`ba02287`/`9bb04f5`)** —
  PROJECT_STATE was entangled with the parallel S120 lane's uncommitted niftyindices edit, so the
  S121/D120/D121 doc bullets ride the seasonal lane's next PROJECT_STATE commit (verify they land, or
  commit PROJECT_STATE once that lane finishes).
- **S120 / seasonal — Seasonal Tape lens LIVE (`9a82731`, a parallel session).** Descriptive calendar-
  seasonality at `/dash/markets/seasonal-tape`. Shows honest grey (0 certified — pre-2012 index depth;
  the session sourced 2004-12 niftyindices history but still 0 survive FDR, correctly NOT forced green).
  Its follow-on edits to PROJECT_STATE + `metrics-glossary`/`strategy-ledger`/`prereg.py`/`hedge_density.py`
  were still uncommitted in the shared tree at S121 wrap — that lane owns committing them.

## 🆕 2026-07-11 — S109 + S110 landed (three lanes, all on origin/main; none redoable)
Diverged from S108 then reconciled by commit-then-pull-rebase (union-resolved PROJECT_STATE — two
S109 entries KEPT + S110 at top): **`dfbe175` S109/D111 Wolfe §B rebalance** (spring-reclaim C ·
deep-extension G · 2.0 restored · RSI-divergence fix — Ramana line-by-line) · **`6899a94` S109
docs/strategies** (canonical `docs/strategies/` reference layer, 9 pages) · **`686f7b9` S110/D112
DEEP-DATA VALUE SPRINT** (this lane). All pushed.

**✅ S111–S116 — the `docs/strategies/` layer RECONCILED + COMPLETED (docs-only, all on origin; DON'T redo — kickstart-pick-verify).** The S109 canonical layer (9 pages + README) was hardened over five follow-on sessions as the multi-lane Wolfe/insights churn settled:
- **S111** (`35940f6`/`b653e00`) — Wolfe page reconciled to the LANDED D111 (freeze→lifted; `_QUALITY_MAX` de-pinned 25→27, G 0-4) + wired into DOC_INDEX / CLAUDE.md / §Key-paths.
- **S113 / D114** (`e45f701`) — patearn `scoring.py` ↔ `patterns.md` reconciled: patterns 6–14 are a DELIBERATE computable adaptation, mapping now explicit in `patterns.md` § "Implementation mapping (scoring.py)"; **scoring output byte-identical** (Ramana chose document-the-mapping, not re-score).
- **S114** (`dc05614`) — D-number verification across all 9 pages vs origin's decision log: only README was stale (fixed); the other 8 correct (incl. the suspect cci-D56 / cpr-D95, both confirmed right).
- **S115** (`626cbff`) — added **`calculations-and-weights.md` §5e DVPT · §5f MEP · §5g CCI · §5h Harmonic** (real constants pulled from code) → the "numbers live once" doc now covers EVERY strategy.
- **S116** (`c212e62`) — cross-linked the 4 pages to those exact §5e–§5h sections + killed harmonic's stale "ratio bands not folded in here" caveat.
- **README reconciliation flags: 1–3 RESOLVED; only 4–5 OPEN + pickable (both NON-doc):** **#4** RS D67 size-index backfill (one-time VPS `index_signals --backfill`; not repo-verifiable) · **#5** CPR Telegram `/cpr` (designed, never shipped — a code build). Memory `wolfe-wave-strategy` D111 line + line-12 back-pointer reconciled. Scratchpad helpers retired; all this lane's worktrees removed.

**✅ S118 — Strategy reference now SERVED + DEPLOYED on /dash (`fb3128b`, LIVE on the VPS).** The `docs/strategies/` layer is browsable in-app at **`/dash/strategy-ref`** (Trust lens; bare route = README index, `?p=<slug>` = one page), mirroring `/dash/glossary`. NEW `src/web/strategies_view.py` — a stdlib markdown renderer (headings · tables · blockquote callouts · lists · fences) + cross-link rewrite (sibling → `?p=`, `metrics-glossary.md` → `/dash/glossary`, other repo/code refs → plain text, never a dead link) — mounted via an anchored 1-line insert to `v2_surfaces._ROUTER_SPECS` + a Trust `Lens` in `lens_registry.py`. **Live-verified** (curl via Caddy: index + `?p=wolfe-wave` render tables+callouts, sibling links resolve, Trust nav shows the lens; `/dash/glossary` regression clean) — and **browser-walked** (local run of the deployed code): the index + Wolfe page render visually — 2 tables (1px borders, headers Layer/What-it-adds/Proprietary?), 3 accent-bar callouts, the in-page rail highlights the active page, no horizontal overflow, **zero console errors** (the `preview_screenshot` tool times out on this markup-dense site — a known limitation — so confirmed via DOM + computed-style inspection, the reliable path). ⚠ **RUNTIME DEP (new gotcha):** the view reads `docs/strategies/*.md` at request time, so those 10 files are now ON the box at `/opt/hermes/docs/strategies/` — **any future strategy-doc edit must be re-scp'd there** (unlike the other docs, which nothing serves). Deploy recipe held: clean-scp module + docs · anchored inserts on the 2 live forked files (backups `.bak-s118-20260711-175218`) · writer-safe restart (no writers active, 23:19 IST off-peak) · live walk.

**🆕 S110 — 6 NEW insight surfaces + a full BEGINNER-READABILITY + DRILL-DOWN arc, all LIVE + deployed
(verify-then-consume, do NOT rebuild — memory `deep-data-insight-lenses`):**
- `/dash/market-internals` — 22y market health (price-breadth + the MEP **tape** + delivery/dispersion/
  coil) from bounded **`market_internals_daily`** (5426 rows, **NO timer**; rebuild via
  `python -m src.automation.market_internals --backfill`). HERO = price-vs-effort divergence.
- `/dash/participants` **UPGRADED** — full 2.5y FII long:short tape + percentile gauge + retail mirror.
- `/dash/launchpad-track` — orphan rescue: `ignition_outcomes` (50k signals) outcome distribution + `averaging_zones` ladder. ⚠ `ret_12m` in PERCENT units.
- `/dash/move-anatomy` (Trust) — the `features` fingerprint: moves launch from momentum/RS (z +0.88), NOT accumulation (delivery z −0.49) + MFE/MAE envelope. Leak-safe. σ shown here (hidden in the guide).
- `/dash/sector-economics` (Markets) — median ROCE/OPM by sector × year; **CLICK a cell → "Behind the number" DRILL** = the constituent companies + their values (`heat_grid(cell_link=)` + `?drill=SECTOR~YEAR`, server-rendered, no JS).
- `/dash/reading-guide` (Trust) — beginner's VISUAL guide: opens with a WORKED walkthrough on the REAL 22y breadth ribbon (crashes marked 2008/COVID/2024), then the 6 chart shapes each with a REAL example, plain-word ideas, golden rule.
- **Beginner-readability arc (4 rounds, layered/ADDITIVE — nothing removed):** shared `infographics.readability_css()`/`bottom_line()`/`plain()`/`how_to_read_link()` — a "Bottom line" band (bottom-line-FIRST on every page), an "In plain English" line under each chart, plain metric labels (tech name = grey subtext), number scales, acronym glosses. `diverging_bars(show_values=)` + `floating_bars(unit=)` + hover `<title>` tooltips on all value charts. The site-wide **`dq_banner.py`** kill-switch banner made beginner-facing (plain "Market mood" label + summary; raw tech on hover + a "why?" link; **DISPLAY-ONLY** via `_PLAIN` map, stored check messages untouched).
- Shared **`src/web/infographics.py`** — 8 tested SVG primitives + the readability scaffold + hover tooltips + `cell_link` drill seam; **reuse, don't hand-roll**. Morning **briefing Artifact** delivered.
- **Deferred (VALIDATED, build when the caveat clears):** tier-migration alluvial (D66 veto) · ownership DII/FII drift (~3y) · SLB short-interest (roll-artifact) · seasonality calendar. `stock_oscillators` = orphaned one-shot → drop or wire.
- Deploy craft: MY modules = clean scp (CR-strip `tr`, **READ-then-write** — a `wb`-before-read one-liner truncated a file once, caught by the import-test rollback); FORKED files (`lens_registry`/`v2_surfaces`/`coverage_view`) = anchored inserts (assert count==1 + rollback), NEVER full-scp; import-test + writer-safe restart; gates PASS; walked LIVE (`curl -sL`). Commits `686f7b9`…`b4810f3`. ⚠ Parallel Wolfe lane is HOT — 2 push races this session (non-fast-forward reject → re-fetch + `git rebase origin/main` + push).
- ⚠ Untracked **`.claude/launch.json`** (dev preview harness → scratchpad path) left uncommitted, harmless — `rm` or ignore.

**✅ DONE — click-drill extended to breadth + launchpad (`b4810f3`+ round-5 commit):** sector heat-grid cell → constituents; **breadth** ribbon/crisis-dates → `?drill=DATE` = that day's biggest gainers/losers; **launchpad** character bar → `?drill=CHARACTER` = the real winner/loser signals. All server-rendered (`heat_grid(cell_link=)`/`heat_ribbon(cell_link=)`/`floating_bars(bar_link=)`), no client JS.

**▶ NEXT PICKS (pick per charter altitude):** (1) the remaining **deferred insight lenses** (tier-migration alluvial [D66 veto-frame] · ownership DII/FII drift · SLB short-interest [wait for roll-de-seasonalisation] · 22y seasonality calendar). (2) Bus follow-ups from the older queue below: the **alert rail** + **SSE stream** (the since-you-last-looked brief is DONE). (3) Quant-integrity: AUD-14 (morning window) · AUD-22 · ~~AUD-37~~ **✅ S123**. (4) If a beginner-review surfaces more, keep the layered-additive discipline + reuse `infographics` (readability scaffold + `cell_link`/`bar_link` drill seams).

**🧊→✅ Wolfe §B freeze LIFTED:** the S108 carry-forward's "FROZEN pending Ramana's §B weightage sign-off"
is RESOLVED — he ratified the rebalance line-by-line (D111, `dfbe175`). The D108 2/3/4 fractal gate stays enforced.
Wolfe draw-tool is now **MERGED to main (D113/S112, `35a11e7`)** — the old `8fc40dc` on branch `wolfe-draw-tool` was NOT used (renumbered from its provisional "D111"). (`docs/strategies/README.md` recon flags.)

**✅ Wolfe winner-profile OOS RE-VALIDATED (2026-07-11, later Wolfe-lane; `2545a91` doc + `3c54c8a` state) — resolves PROJECT_STATE WOLFE OPEN ITEM (5).** Re-ran the committed `phase2_oos.py`/`phase3_betacontrol.py` harness READ-ONLY on the VPS archive under the CURRENT scoring: **filter UNCHANGED** (the 2004-14 fit re-derives the identical `D≤1·p1≥2·F≤2`; the F 0-4 widening is neutral), **BULL edge intact** (test 2015-26 medNet **+4.4%**, α **+5.07**), **placebo-gap negative everywhere** (edge = selection-not-craft, reaffirmed). **BEAR now FAILS the primary (survivorship-aware) OOS `medNet≥0` bar** → inclusive verdict **IN-SAMPLE-ONLY** (−0.98%); nifty500 SURVIVED (point-est). Softer than the June baseline (inclusive winner +2.14%→+0.81%) — attributed to the **D108 fractal gate**, NOT the rebalance and NOT point-4 (**A/B-confirmed neutral**). **Descriptive-only UNCHANGED. DON'T re-run** — full record in `wolfe-wave.md` §4+§8, the PROJECT_STATE D111 block, and the `wolfe-wave-strategy` memory. (Re-run recipe there if ever needed.)

## 🔔 2026-07-10 EVENING — FOUR lanes landed the same day (read all four; none is redoable)
**S102 (P-05, Ramana: "complete that now") · S103 (attention face, D106) · S104 (AUD-06/07/11,
D107) · the Wolfe FRACTAL arc → S105/D108 revert + 🧊 FREEZE (LIFTED 2026-07-11, D111; see 🌀).** Canonical chain:
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
  **🧊→✅ WOLFE FREEZE LIFTED (2026-07-11, D111):** the "no Wolfe code until §B sign-off" gate is
  RESOLVED — Ramana ratified the §B rebalance line-by-line (`dfbe175`; G→`_QUALITY_MAX`=27, `d5551cc`),
  the draw tool merged (D113, `35a11e7`), point-4 reconciliation landed, and the winner-profile OOS
  was re-validated (`2545a91`). The D108 2/3/4 fractal gate stays enforced. Canon = `wolfe-rules.md` §A9+§B3.

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
  it, do NOT `systemctl start` per AUD-95)** · **Sat 21:00 provenance ✅ VERIFIED (2026-07-12):
  finished ~1h59m under the new 4h cap, full universe 2763/2763 symbols, 0 failed units — fix
  holds, no chunking needed** · banks report ~Jul-18 · ~Jul-21
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
replication bypasses the PIT layer (route through `fundamentals_asof.py`) · ~~**AUD-25**
feed-liveness covers 4/12 feeds~~ **✅ MOSTLY CLOSED S123 (`c1405dd`): regime date-guard +
news/concalls → 10 feeds; fundamentals/shareholding recency + bhavcopy-gap DEFERRED (reasons in
audit doc)** · **AUD-28** setup-news.sh heredoc regression (do with AUD-27
remainder) · ~~**AUD-37** /v1 metering under-records~~ **✅ DONE S123 (`9e53aae`) + quotas (`76694e1`)**
· **AUD-12** rs_rank survivorship (finder-only — verify first). **P2/P3:** AUD-45..117 batch
list unchanged (AUD-101 UNBLOCKED). **BLOCKED (external/Ramana):** AUD-42/58/59/62 ·
Wolfe point-4-strength (needs his worked chart) · E-08/E-09 (D-07 depth) · D-09/D-10
(endpoint discovery). **PROJECT_STATE §Open highlights:** charting D71/D72 Phases 3-5 ·
DVPT picking-strategy program (D47) · positioning-pillar tail · UI Track A cosmetic residual.
**Light theme** = design-first headline session (never a tail; the S78b finding stands).
**🔒 REPO HYGIENE — enable `main` branch protection (do-once, ~30s):** GitHub → Settings → Rules
→ new branch ruleset on `main`: **Block force pushes** + **Restrict deletions**; leave *Require PR*
/ *status checks* OFF (keep the lanes' direct FF pushes working); bypass list empty (applies to
admins). WHY: S112/D113 surfaced a live gap — a divergent local `main` (e.g. `6f36bde`) could
force-push over origin's linear history and drop merged work; a ruleset is the only close. Can't be
done mid-session (no `gh`; claude.ai connectors register only at session start) → do it in the UI,
or ask a FRESH session with the GitHub connector authorized: "enable main branch protection to block
force-pushes + deletions, enforce_admins:true, no required PR/checks."

## 🎯 NEXT PICKS (charter §4/§7 altitude; kickstart-pick-verify EVERY pick + fork-check VPS live files)
1. **Wolfe lane: ✅ UNFROZEN — §B rebalance (D111), draw tool (D113), point-4 reconciliation, and
   the winner-profile OOS re-validation all LANDED 2026-07-11.** Remaining open (PROJECT_STATE D111
   block): **point-4-STRENGTH** (needs his worked chart) · **D95 tape-wiring** · **§C trade-mechanics
   as a runnable PIT backtest** · **G/scoring PIT** (as-of LTP). Run-book `docs/wolfe-NEXT-SESSION.md`;
   kickstart-pick-verify each.
2. **Product:** **X-04 overnight/intraday split + pump-flag** (top remaining charter X-item) ·
   X-06 Amihud migration delta (half-built, `mep_signals.py:286`) · X-07 volume-at-price
   shelves · D-06 announcement taxonomy → E-07 auditor-resignation red-flag.
3. **Bus follow-ups (natural after D106):** ~~since-you-last-looked brief~~ **✅ DONE S108/D110** ·
   ~~alert rail~~ **✅ DONE S123 (`8241bba`, LIVE)** → remaining: the **SSE stream** (live tape —
   the LAST unbuilt bus face) · dvpt lens design (needs a banded state first). Natural S123
   follow-ons: a Telegram push of critical alerts (reuse `digest._send` + the `signal_alert_state`
   substrate) · a Home "⚠ Alerts" badge · an acknowledge/dismiss action (server-side, unlike the
   per-viewer cookie).
4. **Quant-integrity:** ~~AUD-14~~ **✅ MOSTLY-CLOSED S123 (`b1328c0`: bhavcopy+indexes+participant_oi; deals/corp_actions/equity_list deferred)** · ~~AUD-22~~ **✅ S123 (`891a50f`, PIT re-validated, t=1.99→1.80)** · ~~AUD-37~~ **✅ DONE S123 (`9e53aae`) + per-tenant quotas (`76694e1`)** · ~~AUD-25~~ **✅ MOSTLY-CLOSED S123 (`c1405dd`)**.
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
> read the ✅ S143 + S142 + S141 + S140 + S137 blocks FIRST (all on origin/main; do NOT
> redo — kickstart-pick-verify). **THE QUEUE = the S127 UX-remediation program**
> (`docs/ux-journey-audit-2026-07-13.md` §8).
> Done: S-A front door · S-H route gate · **S-C COMPLETE** (items 1+7 S134 · scaffold S136 ·
> glossary links + nav subtitles S138 · **the education-coverage gate + the full 63/63 sweep
> S137** · **item 4 glossary-unify S141/D132 — ONE vocabulary, Pat=199 entries**) ·
> S-D search/entry S140 · **S-E PHASE 1 nav-answer S142** (`src/pat/nav_flow.py`) ·
> **S-B1 STARTED — cross-links S143** (`infographics.related_strip()` on the 7 RS/rotation views +
> momentum→dossier; items 4·9·½8).
> **NEXT free pick — two good options:** (a) **S-B1 REMAINDER** — item 1 Markets rail → task groups
> (forked `lens_registry.group=` + `left_rail._GROUP_ORDER`) · item 2 merge RRG-Map + Rotation-Weather
> (Map⇄Weather toggle, the Wolfe-toggle precedent) · item 3 fold cycle-clock/sector-momentum/early-signals
> into Rotation · items 5/6/7/10/11 + the reverse `/dash/sectors→sector-economics` link (forked
> `cockpit.render_sectors`). (b) **S-E PHASE 2+3** — Pat DATA flows (attention "what changed today / for
> SYMBOL", news/wire, participants/FII, insider/ratings/SAST/holdings, rotation states, seasonal base
> rates, internals breadth, Wolfe open-trades) + education, following the `nav_flow.py`/`overdue_flow.py`
> pattern (new Pat file + ₹0 engine.route pre-pass + web render + eval/pytest guards); KEEP closed-vocab
> deterministic SQL. Else **S-B2** (route deprecation + POST-ify GETs) or **S-G** expert affordances.
> Ramana may paste a problem statement; if none, take the audit §8 brief autonomously.
> **Reuse, don't rebuild:** `infographics.fence(kind)` for any fence (add a kind, never hand-write);
> `readability_css/bottom_line/plain/how_to_read_link` for education (dashboard-served pages go
> through `dashboard._edu()`; tracker demo via `tracker_gate._edu_demo`); **NEW lens pages must
> satisfy BOTH gates** (`test_dash_route_registry.py` + `test_education_coverage.py` — PENDING there
> is temporary documented debt only); the live chrome is `ui_kit.topbar`/`shell_skin`, NOT
> `dashboard._shell`.
> **Multi-lane hygiene (4+ lanes):** `git status` before AND during work; `list_sessions` to see the
> lanes; yield if a sibling owns your pick (claim-first via a pushed marker per the S140 livelock
> lesson); explicit-path staging + `git diff --cached --name-only` before EVERY commit; a sibling's
> files mid-staging → commit via temp `GIT_INDEX_FILE` + `commit-tree` + CAS `update-ref`;
> PROJECT_STATE hot → partial-stage ONLY your hunk (`git apply --cached`) or `state:skip`; grep
> origin for the newest session number (131–143 taken). ⚠ S143 saw HEAD move under it repeatedly as
> siblings committed to shared local `main` — re-`git diff HEAD` a hot doc right before editing, and an
> isolated worktree (`EnterWorktree`) for deploy staging avoids fork-checks reading a sibling's mid-edit.
> **Deploy: fork-check md5 (CR-strip BOTH sides) DECIDES the method** — box==base → clean scp;
> forked → anchored insert of only your hunks (assert count==1 + rollback); `dashboard.py` → on-box
> `git apply` of your commit patch (post-apply md5 must == HEAD; it is currently NOT forked but
> patch-deploy stays the rule). Remote IMPORT test, not just py_compile. **Writer-safe restart =
> a BLOCKING `if fuser…exit` gate (an `&&`-chain only prints!) + never restart ~13:55–14:15 UTC**
> (bhavcopy fires 14:01) + never `systemctl start` a timer mid-day (AUD-95). Curl via the Caddy
> hostname or ssh-localhost; live-walk every shipped item. ⚠ Local harness TestClient crashes on
> outermost-middleware short-circuits (tracker demo/owner-form) — pre-existing starlette artifact;
> verify those at unit level + live curl, the box is fine. ⚠ The S128 fence-sweep (`5c6720f`) may
> still be partially undeployed for participants/launchpad — that lane's to complete, not yours.
> Access is harness-enforced — never ask for access or per-step confirmation; get guidance from the
> agents, not from me; I won't answer. Keep every guardrail (esp. #8 primary-sources, #9
> SURFACE-PLAYBOOK for any new screen). Wrap per § AT SESSION END and hand off the next prompt.
