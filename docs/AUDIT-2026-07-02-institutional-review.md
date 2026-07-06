# Institutional Audit — 2026-07-02 (multi-agent adversarial review)

**Status:** PERMANENT RECORD — do not delete. Mark AUD items done (with commit hashes) in the Status column as they land; never rewrite the findings themselves.
**Scope:** full platform — repo `D:\Hermes` @ `be7826a` + live VPS `187.127.173.149` (read-only probes).
**Companion queue:** `docs/NEXT-SESSION-CARRYFORWARD.md` (the fix prompt below is the takeover entry point).

---

## How this audit ran (fleet: 10 domain finders + gap finders, per-finding adversarial verification, completeness critic; read-only)

- **Finder fleet.** 10 core domain finders (performance/trust, UI architecture, data engineering, quant correctness, institutional due-diligence, external data acquisition, DB schema, index↔stock linkage, code hygiene, security/ops) plus gap finders that opened four more lanes the core set missed (Telegram/LLM layer, Pat NL + explainability, systemd timer topology, /v1 API contract) — **14 domain reports** in total. All read-only: code reads, live-VPS curls/SSH probes, EXPLAIN QUERY PLAN, journal reads. No writes anywhere.
- **Adversarial verification.** Every P0/P1 was independently re-derived by a verifier agent that (a) reproduced the evidence from the current tree/VPS, (b) hunted for an existing fix or a deliberate Decision-log defense, and (c) issued a verdict — **CONFIRMED / PLAUSIBLE / REFUTED** — with a corrected severity where the finder over- or under-called. 7 findings were REFUTED (already fixed at HEAD, deliberate-and-documented, or impact mechanism wrong); several were re-graded in both directions (two escalations to P0, multiple downgrades).
- **Completeness critic.** A final pass checked domain coverage against the product's own doctrine (PROJECT_STATE decisions, guardrails, binding memories) so that "deliberate" was never conflated with "defect" — e.g. rotation-lens breadth and mep/cpr materialization were cleared as documented decisions.
- **Severity language.** P0 = broken/wrong now, or existential; P1 = integrity/credibility below the institutional bar; P2 = real debt; P3 = polish. Findings NOT in the P0/P1 verification pass carry verdict "finder-only (unverified)" — re-verify before fixing (kickstart-pick-verify).

---

## Scorecard

| Domain | Grade | One-line verdict |
|---|---|---|
| sec-ops | **F** | Open port, root everything, no firewall, no backup — perimeter never grew up with the product. |
| telegram-assistant | **D** | Bot auth is solid; the shared HTTP layer leaks transcripts and spends credits unauthenticated. |
| timer-topology | **D+** | Scheduler core unversioned on the VPS; ordering by wall-clock hope; hung jobs block forever. |
| perf-trust | **C-** | Fast everywhere except the Trust page — the one page sent to diligence teams. |
| ui-arch | **C** | Strong bones (registry, gates); runtime is four stacked monkey-patches and duplicated gauges. |
| linkage | **C** | The index↔stock intelligence exists in tables; the surfaces don't join the levels. |
| v1-api-contract | **C** | Strong design intent; the PIT wedge isn't on the paid contract and metering isn't audit-grade. |
| quant | **C+** | Careful engineering with self-tests; spec–code drift and adjustment holes in shown numbers. |
| inst-dd | **C+** | Scientific self-honesty is genuine; enforcement and disclosure lag the written doctrine. |
| api-src | **C+** | Good fetch-layer bones; silent-failure last mile — nothing pages, throttles read as holidays. |
| db-schema | **C+** | Hard-won WAL discipline; ~19% write-only dead weight and (pre-fix) no backup. |
| hygiene | **C+** | Real render-level gates; zero numeric tests on the computational core; monolith churn. |
| pat-nl-explainability | **C+** | Architecturally strong NL engine; the glossary asserts mechanisms that don't exist in code. |
| data-eng | **B-** | Newest pipelines genuinely institutional; incident fix patterns not propagated to siblings. |

---

## The correction program — prioritized

Ranking rule applied: **integrity of shown numbers > user-facing performance > institutional credibility > engineering debt.** REFUTED findings are excluded here (see Appendix). Duplicates across domains are merged into one AUD item with both reporters noted. Work items **strictly in numeric order** unless a Status entry says a parallel session already landed it.

**Status legend:** `OPEN` until a fix session records a commit hash here.

### P0 — broken now / existential

**AUD-01 [P0] Public HTTP surface unauthenticated and unfirewalled (dashboard, /chat, /conversations)** — `DONE (parallel lane, S77-verified)` (VPS verified live: uvicorn binds 127.0.0.1:8000, ufw active 22/80/443, Caddy fronts the site, `/conversations`→401 unauth via `src/web/perimeter.py` ConversationsGuard, CHAT_SHARED_SECRET set. `perimeter.py` + the main.py mount are COMMITTED (`cc988c6`, owning lane). Also done same window (cc988c6 lane): sshd key-only via `00-hermes-hardening.conf` (AUD-34) + 9443 kept open for Nous. Residual: optional Caddy basic-auth on `/dash` = owner product call)
- **Component:** VPS perimeter + `src/main.py` + `src/core/settings.py` | **Reporters:** sec-ops (P0), telegram-assistant (/chat P0, /conversations P1), sec-ops (/chat P1, /conversations P2) — merged, same root cause.
- **Files:** `src/main.py:34,97-130`, `src/core/settings.py:30,46`, `scripts/setup-news.sh:200`, VPS ufw/Caddy.
- **Evidence digest:** uvicorn LISTENs on `0.0.0.0:8000`; ufw inactive, iptables ACCEPT-empty; external `curl /conversations` = 200 (full transcripts + `telegram:<user_id>` titles, sequential IDs), external `POST /chat` = 200 and `fast=false` selects Sonnet (`chat.py:160`); `CHAT_SHARED_SECRET` absent from `/opt/hermes/.env` so the opt-in guard (`main.py:103-107`) is dormant; `DELETE /conversations/{id}` also open. Verifiers re-took the measurements live.
- **Fix:** (1) set `CHAT_SHARED_SECRET` now + auth-gate `/conversations` GET/DELETE (same dependency); (2) bind uvicorn to `127.0.0.1` (Caddy already proxies) + ufw default-deny allow 22/80/443; (3) front-door auth (basic-auth on Caddy) for `/dash`; reject `fast=false` without auth. Writer-safe restart window required.
- **Effort:** S | **Verdict:** CONFIRMED (×4 reporters; exposure re-measured).

**AUD-02 [P0] No off-box backup of the only copy of the 16GB production DB** — `ON-BOX DONE S77 (d506cea), OFF-BOX open` (scripts/hermes-db-backup.sh online .backup + quick_check + rotate-3 + free-space/truncation guards; hermes-db-restore.sh --verify/--into; daily 20:30 UTC timer w/ TimeoutStartSec+RandomizedDelaySec; installed+enabled+first backup verified restorable. REMAINING P1: OFF-BOX shipping needs owner destination (rclone remote / Hostinger snapshot) — on-box dies with the disk. COMPLEMENTARY second unit (cc988c6+b04e4eb lane): `backup-db.sh` @ 00:30 UTC = nightly NON-DERIVABLE-tables dump (178M, 7-day depth) + nightly research.db copy + weekly em_cache.pkl — covers what the full-DR unit doesn't; restore-tested via `restore-db-test.sh` PASS. Division of labor recorded in both scripts; overlap + a mutual rotate-glob interference bug removed in b04e4eb)
- **Component:** VPS ops / `/opt/hermes/data` | **Reporters:** sec-ops (P0 CONFIRMED), db-schema (verifier said P1) — merged; P0 kept: contents include tenant keys, user portfolios/drawings, and Gemini-paid extractions that are **not re-runnable** (cap).
- **Evidence digest:** `backups/` holds one ~20KB tsv; 22-24 hermes timers, none backup; crontab empty; only artifact is the manual, password-prompted `scripts/download-from-vps.bat`. `coverage_view.py:98` itself admits "no HA/DR today".
- **Fix:** systemd timer doing nightly `sqlite3 .backup`/`VACUUM INTO` of the small non-derivable tables + weekly full copy shipped off-box (rclone/Hostinger snapshot); retention policy; **tested restore script**; include `em_cache.pkl`.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-03 [P0] Concall-capture timer invokes CLI flags that don't exist — capture live-broken since ~Jun-28** — `DONE cfcd1c7` (continuation lane restored --universe/--workers/--include-covered; Jul-05 failure defused; verified)
- **Component:** concall capture | **Reporter:** api-src.
- **Files:** `scripts/hermes-concall-capture.service:16` vs `src/automation/concalls.py:311-320`.
- **Evidence digest:** unit passes `--universe 3636 --workers 5 --include-covered`; argparse defines neither → exit 2. Verifier re-checked the VPS: the live `/opt/hermes` copy also lacks the flags now and `/var/log/hermes-concall-capture.log` ends with `unrecognized arguments` after a successful 2026-06-28 run (a workers=5 build was overwritten). Transcripts are perishable (source rotates). **Next scheduled run Sun Jul-05 will fail too.**
- **Fix:** reconcile — restore/commit the CLI that implements `--universe/--workers/--include-covered`, or rewrite the unit to the committed CLI; add a check that every ExecStart parses against the module's argparse.
- **Effort:** S | **Verdict:** CONFIRMED (P0, live-broken).

**AUD-04 [P0] Trust front-door /dash/coverage: 4.1s every request, 29–38s under 6-way concurrency (+ memo, + /v1 coverage/health share the fix)** — `DONE S77 (c948c3f), deployed+measured` (in-process memoization of coverage_snapshot + lag_audit in provenance.py, keyed on MAX(trade_date)+600s TTL, single-worker-safe, selftest-safe via falsy-key bypass. **Live: 30s-timeout/16s/4.3s → 3.6s cold then 0.47s warm; 12@P6 29-38s→20.7s.** Residual CLOSED by the parallel lane (`a207c99`, S77b): `lag_samples` was the LAST uncached trust read — provenance_narrative ran its 29k-row point-query N+1 per view (measured warm 0.47s; 6-way 10.7s/req) → third cache, same key+TTL pattern. **Live after: warm 7-8ms, 6-way concurrent 42-51ms/req, public via Caddy 0.21s — <100ms target BEATEN.** Remaining (P3): optional nightly pre-warm for the once-a-day ~3.7s cold hit + stampede lock)
- **Component:** coverage_view + provenance snapshot | **Reporters:** perf-trust (page P0 + lag-audit P1 + memo, all CONFIRMED); v1-api-contract's /v1 variant was REFUTED as P0 (threadpool + measured 3.07s, no hang) but its residual P2 (uncached 3s health probe) is covered by this same fix.
- **Files:** `src/web/coverage_view.py:530,580,658,722-736`, `src/automation/provenance.py:743-1084,857-908`, `src/api/v1/resources.py:32-34`.
- **Evidence digest:** `coverage_snapshot(conn)` per request, zero caching/ETag; `COUNT(DISTINCT symbol)` over 9.5M-row `bhavcopy_rows` **twice** (bhav_eq+bhav_delivery share the table; stock_signals also double-scanned); the 29,201-row N+1 lag audit into research.db runs **three times** per page view (snapshot → narrative recompute → lag_samples) though `snap` already holds the results; memo recomputes everything again (3.1s). Measured 4.12-4.14s ×3; 12 reqs @P6 = 29.4-38.7s.
- **Fix:** (a) persist a bounded snapshot computed by the nightly job (space-rule-sanctioned) or in-process cache keyed on `MAX(trade_date)` + TTL fallback; serve ledger, memo, `/v1/coverage`, `/v1/meta/health` from it (make health a trivial `MAX(bhavcopy_dates)` probe); (b) dedupe per-table scans; (c) pass `snap['lag_audit']/['lag_headline']` into `provenance_narrative`; replace the per-row `_scalar` N+1 with one prefetched dict. Target <100ms.
- **Effort:** M | **Verdict:** CONFIRMED (page P0, lag P1, memo P2; /v1 residual P2).

### P1 — integrity of shown numbers

**AUD-05 [P1] Trust ledger silently renders "—" for 3 live datasets (rsband, rs_extras, capture)** — `DONE S77` (provenance.py: has_symbol=False + new count_col="numerator" override → shows 173/122/173 series not "—"; live schema verified read-only: no symbol col, COUNT(DISTINCT numerator) non-None. ⚠ needs deploy; formal startup selftest still TODO)
- **Component:** coverage matrix integrity | **Reporter:** perf-trust.
- **Files:** `src/automation/provenance.py:109,181-189,382-390,897`; DDL at `rrg.py:247`, `rsband.py:322`, `capture.py:132`.
- **Evidence digest:** those tables are keyed (numerator, denominator) with no `symbol` column; descriptors default `has_symbol=True` → `COUNT(DISTINCT symbol)` errors → `_scalar` swallows to None → live page renders `—` under the header "Every figure is sourced and reproducible". A diligence reader concludes three nightly-populated datasets are empty.
- **Fix:** `has_symbol=False` + key-column override (`COUNT(DISTINCT numerator)` or distinct trade_date days); startup selftest asserting every PROVENANCE class yields non-None `n` on prod schema.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-06 [P1] D31 price zones, D44 key prices and hot-day averages computed on RAW closes across ≤360d windows** — `OPEN`
- **Component:** DVPT price zones | **Reporter:** quant.
- **Files:** `src/automation/signals.py:456,357-379,402-404,487-509,637-675`.
- **Evidence digest:** baselines/key-price weights/hot-day closes all use raw `close`; a 1:10 split inside the window makes `gap_to_key_p12m` read ~-90%; the 🎯 near-key flags in conviction_shortlist and /dvpt zones show garbage until the window rolls past. CL-MDC-01 fixed only the D43 deliv_value arrays for this exact hazard; PROJECT_STATE D36 itself lists this as a known open limitation.
- **Fix:** feed adjusted closes (already computed in `_character_arrays`) into baseline tuples, key-price weights and hot-day closes; then re-run `--backfill-triggers` and `--backfill-keyprice` on the VPS (background, per-chunk commits).
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-07 [P1] Backfill and nightly disagree on hot-day definition (22-of-22 uncapped vs 15-of-22 capped)** — `OPEN`
- **Component:** DVPT hot-day baseline | **Reporter:** quant. Do together with AUD-06 (same backfill re-run).
- **Files:** `src/automation/signals.py:899-908` (backfill) vs `:644,657-663` (nightly, CL-MDC-10).
- **Evidence digest:** same (symbol,date) gets different `hot_days_avg_price` depending on which path wrote it; backfill comment falsely claims "same definition as D28". Inconsistent stored history that /scan sorts on.
- **Fix:** extract one shared helper carrying the CL-MDC-10 min-15 threshold + 250-row/372-day cap; use it in both paths.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-08 [P1] Revised insider filings double-count promoter flow (amendments never supersede)** — `OPEN`
- **Component:** insider_events dedup/aggregate | **Reporter:** data-eng.
- **Files:** `src/automation/insider_events.py:356-362,576-577,604-605,244-312`.
- **Evidence digest:** gg feed has `did=None` so uid = content hash; a Revised filing with corrected shares/value → new uid → second row; `aggregate()` sums all rows with no amendment/supersession filter → `net_promoter_cashflow_90d`, cluster-buy and pledge_adverse counts double-count every amended disclosure; verdict sign can flip. Inverse: two genuinely identical same-day trades collapse to one uid.
- **Fix:** on saving an `amendment_flag=1` event, supersede prior events matching (symbol, person_name_hash, transaction_dt), or make `aggregate()` keep latest `parsed_at` per natural key.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-09 [P1] Negative PE scores as maximum cheapness inside the Quality Gate** — `DONE S77` (scoring.py:189 pe/pb<=0 → hard 0 verified; D84; golden test tests/test_scoring.py)
- **Component:** patearn Pattern 4 valuation | **Reporter:** quant.
- **Files:** `src/automation/scoring.py:88-95,187-191`.
- **Evidence digest:** `_score(pe,15,25,reverse=True)` returns 2 for PE=-8; `v3=v1` doubles the credit (~27 weighted pts); Pattern 4 is a QG pattern and `check_hard_disqualifiers` has no loss-maker check. CL-SCO-02 deliberately kept negative PE but never handled the sign.
- **Fix:** zero valuation credit when `pe<=0` (and `pb<=0` guard), keeping verified=True so it isn't treated as missing data.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-10 [P1] Momentum ensemble deviates from canonical §2: LOWVOL_MOM enters unranked** — `DONE S77` (momentum_scan.py:92 pctrank the blend; D85; test_momentum_ensemble.py; ⚠ needs VPS scan re-run to restate ensemble_pctile)
- **Component:** momentum ensemble | **Reporter:** quant.
- **Files:** `research/explosive_moves/momentum_scan.py:92-93`; `docs/calculations-and-weights.md:46`.
- **Evidence digest:** `nanmean([r_mom12, r_hi52, r_riskadj, 0.5*r_lowvol+0.5*r_mom6])` — the blend is a raw average with compressed dispersion (~30% effective under-weight vs the specified 0.25); doc §2 specifies `rank(LOWVOL_MOM)` and is also stale ("not yet in code"). Shown live as `ensemble_pctile` on /dash/momentum-scan.
- **Fix:** `pctrank()` the blend before averaging; update doc §2 canonical pointer to momentum_scan.py.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-11 [P1] Corp-action fallback rescales entire history on genuine >30% crashes (F&O names)** — `OPEN`
- **Component:** split/bonus adjustment | **Reporter:** quant.
- **Files:** `src/automation/adjust.py:33-35,52-70`.
- **Evidence digest:** when prev_close doesn't flag, any single-day close move >30% is treated as an unadjusted corporate action and ALL prior history is scaled. The "circuit limits make it impossible" premise is false for derivatives-segment names (YESBANK -55% 2020-03-06). Consumers: stock_rs, mep_signals, cpr_signals, charts. Corrupts exactly the blow-up events an institution scrutinises.
- **Fix:** corroborate the CC fallback — require a volume/deliv_qty discontinuity consistent with the ratio, or check the NSE corporate-actions feed; else zero the day like `_ret_signs` does.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-12 [P1] Historical rs_rank percentiles are survivorship-biased (today's equity list applied to all past dates)** — `OPEN`
- **Component:** stock RS percentile rank | **Reporter:** quant (finder-only — not adversarially verified; kickstart-pick-verify first).
- **Files:** `src/automation/stock_rs.py:70-74,231-262,277`.
- **Evidence digest:** `_LIQUID_FILTER` uses the CURRENT `nse_equity_list` for every historical rank pass; delisted names excluded from past cross-sections. `security_master.universe_on()` exists (ignition uses it) but not here. Any issue-date backtest consuming stored rs_rank inherits the bias.
- **Fix:** point-in-time universe join per trade_date in the all-dates rank pass; re-run the rank backfill.
- **Effort:** M | **Verdict:** finder-only (unverified).

**AUD-13 [P1] bhavcopy marks a trade date complete even when row inserts fail; inserted counts lie** — `OPEN`
- **Component:** bhavcopy store/ingest | **Reporter:** data-eng.
- **Files:** `src/automation/bhavcopy.py:411-424,437-447,500-501`.
- **Evidence digest:** per-row exceptions swallowed (DEBUG; WARNING only >1%), `n` counts conflict-skips as inserts, then `mark_date_done(..., len(rows))` unconditionally; `date_already_done` skips forever → a locked DB during ingest creates a permanent silent hole in the primary archive that no re-run heals.
- **Fix:** mark done only when inserts+conflict-skips reconcile to `len(rows)`; use `cursor.rowcount`; escalate store failures to ERROR and leave the date unmarked for retry.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-14 [P1] NSE throttle (403/429/5xx) recorded as holiday in bhavcopy + 5 sibling fetchers; run_recent never re-attempts lost days** — `OPEN`
- **Component:** archives fetchers | **Reporters:** api-src (P1 CONFIRMED) + data-eng (P2) — merged.
- **Files:** `src/automation/bhavcopy.py:98-103,508-518`; same conflation in `indexes.py:65`, `participant_oi.py:95`, `corp_actions.py:50`, `equity_list.py:48`, `deals.py:94`. Pattern fix exists ONLY in `fno_oi.py:53-88` (CL-RS-13 `RetryableFetchError`).
- **Evidence digest:** any non-200 → None → "holiday"; `run_recent` early-returns on first successful insert so a throttled day D is never re-attempted once D+1 lands — a permanent 1-day hole below the >4d freshness alarm, silently corrupting every calendar-window signal spanning it.
- **Fix:** port `RetryableFetchError` to all six fetchers; make `run_recent` scan the full 7-day lookback for not-done weekdays; record holidays as a `row_count=0` sentinel so blocks stay visible failures.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-15 [P1] Quality Gate constants drift: docs/SKILL say 240/144, code computes 252/151.2** — `DONE S77` (docs aligned UP to code 252/151.2 across calc-doc/SKILL/patearn.py + scoring.py comments; D86; test asserts)
- **Component:** patearn scorer canon | **Reporter:** quant (finder called P0; verifier corrected to P1 — runtime applies the 60% rule correctly against the true max; this is canonical-doc integrity, not wrong results).
- **Files:** `src/automation/scoring.py:25-30,46-48`; `docs/calculations-and-weights.md:98`; `resources/patearn/SKILL.md:56`; `src/assistant/patearn.py:54`.
- **Evidence digest:** weights 9+9+8+8+8=42 → QG_MAX=252, threshold 151.2; inline comments and both canonical docs say 240/144. Any reviewer diffing doc vs code finds the flagship gate mis-specified.
- **Fix:** decide the true gate (252 from the weights is what runs), then align code comments + doc §4 + SKILL.md + patearn.py string in ONE commit per the maintenance rule; Decision-log entry.
- **Effort:** S | **Verdict:** CONFIRMED (corrected P1).

### P1 — trust-artifact / claims integrity

**AUD-16 [P1] Pat's glossary describes a bank/NBFC-adapted pt14 scoring that does not exist in code** — `DONE S77 (deployed+verified)` (glossary.py financials_adaptation rewritten to the truth: automated scorer applies SAME thresholds, D/E>2 hard-rejects banks, NOT tagged, adaptation is manual Phase-4 only. Live: old "scored on bank metrics" claim 0 remaining; /dash/glossary+/dash/pat 200)
- **Component:** Pat glossary | **Reporter:** pat-nl-explainability (finder P0; verifier P1 — computed scores unchanged, but a materially false explanation on a live trust surface).
- **Files:** `src/pat/glossary.py:710-716`; `src/automation/scoring.py` (no financial dispatch; D/E>2 hard-reject applies to banks raw).
- **Evidence digest:** "For financials Pat reads ROE/ROA, NII growth, GNPA, CAR… Any financial-sector score is tagged as sector-adapted" — zero code support; D24 doctrine exists only in manual Phase-4 analysis. Bank pt14 scores are raw non-financial thresholds and are NOT tagged.
- **Fix:** rewrite the entry to the truth (standard thresholds applied to financials; known limitation, scores unreliable for banks; not tagged) — or implement the adaptation; either way fix the text in the same session.
- **Effort:** S | **Verdict:** CONFIRMED (corrected P1).

**AUD-17 [P1] Pat compare/why/trend silently take the first fuzzy symbol match — confident wrong-company answers** — `OPEN`
- **Component:** Pat symbol resolution | **Reporter:** pat-nl-explainability.
- **Files:** `src/pat/web.py:1417-1422,1628-1635,1711-1718` vs the correct guard at `:1903-1911`; resolver `src/pat/flows.py:775-783`.
- **Evidence digest:** "compare TATA and INFY" silently compares TATACHEM; "why is TATA credible" answers for the wrong company with full evidence formatting — the exact failure Pat's design doc promises never to give. `_stock_flow` already has the "Did you mean…" pattern; the other three skip it.
- **Fix:** reuse the exact-match/disambiguation-chips pattern in `_compare_flow`, `_why_flow`, `_trend_flow`.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-18 [P1] Replay-the-tape claims "actually filed" dates that are uniform +90d models — violates the house's own never-claim list** — `DONE S77 (deployed+verified)` (relabelled caption + column header + no-look-ahead ribbon to "Modeled avail. (+90d)" in BOTH the generator `scripts/build_dossier_html.py` (durable) and the committed artifact; live VPS copy reconciled in-place preserving its newer hero data. Live: /dash/replay shows "Modeled avail", 0 "actually filed", data intact. Residual enhancement: base-rate line + restatement panel)
- **Component:** client-facing trust artifact (/dash/replay) | **Reporter:** inst-dd.
- **Files:** `docs/replay-the-tape.html:139,149,218-221,300`; served via `replay_view.py` → `v2_surfaces.py:47`.
- **Evidence digest:** every ledger row has `lag_days=90` exactly (Alkyl FY19 "filed" 2019-06-29 = period_end+90 to the day) while the caption says "the date it was actually filed"; the page's own footnote admits "(period end + ~90d)" — internal contradiction; panel red-line (institutional-panel-assessment.md:80-87) forbids exactly this and required a restatement log (absent). Winner-only heroes, no base rates.
- **Fix:** relabel the column "Modeled availability (+90d, conservative)"; add restatement-log panel + a base-rate line (N signals, hit rate); or regenerate heroes from real `provenance_knowable` dates.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-19 [P1] Validation memo asserts enforcement that does not exist (§4 beta≤1.3 / sector≤25% limits "live by construction")** — `DONE S77 (honest doc downgrade)` (validation-memo.md §5: "#6 live by construction" → "#6 OPEN — NOT enforced; shortlist computes no trailing beta/sector weights; stated mandate not a machine-checked control", with the build path to flip it LIVE. Feature-build deferred per open-decision default)
- **Component:** validation memo integrity | **Reporter:** inst-dd.
- **Files:** `docs/validation-memo.md:87-91`; `src/web/momentum_view.py` (no beta/sector columns); no shortlist beta/sector-weight computation anywhere in src/.
- **Evidence digest:** SR 11-7 documentation-integrity failure — a validator re-performing the memo finds a false attestation. Kill-switch battery covers freshness/regime/drift/restatement/feed, not §4 limits.
- **Fix:** either compute shortlist trailing beta + sector weights nightly and render with breach highlighting, or amend memo §5 to mark #6 OPEN. Never let the memo claim more than code does (same-commit doc rule).
- **Effort:** S (doc) / M (feature) | **Verdict:** CONFIRMED.

**AUD-20 [P1] /dash/glossary leaks exact thresholds/weights under its own "never the proprietary formula" promise** — `DONE S77 (deployed+verified)` (metrics-glossary.md: stripped conviction 0.55/0.45, ★ p_score≥4∧rs_rank≥80, CPR knobs D1.0/W2.5/M5.0, Structure weights D1·W2·M3+formula → concepts+inputs+polarity only; values stay machine-owned in code constants. Live: 0 leaked numbers)
- **Component:** glossary trust surface | **Reporter:** pat-nl-explainability.
- **Files:** `docs/metrics-glossary.md:47,67,68` (rendered), `:43-46` (conviction weights, canonical content); `src/web/glossary_view.py:57,80`.
- **Evidence digest:** ★ triple-confirm rule (p_score≥4 ∧ rs_rank≥80), R1-R4 knobs, ★-Structure weights D1·W2·M3 + score formula all render live directly under the promise sentence. Self-contradiction is the credibility cost as much as the leak.
- **Fix:** strip exact thresholds/weights from rendered bullets (polarity + inputs only, per the doc's own §Status plan); move formula blocks into `docs/calculations-and-weights.md` (internal).
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-21 [P1] Frozen Screener fundamentals answered by Pat with no as-of date** — `DONE S77 (deployed+verified)` (web.py _FRESH["fundamentals"]→("fundamentals","fetched_at",…) + oscillators→stock_oscillators.trade_date + honest "Screener→XBRL, may lag" caveat. Live: _freshness_bar now emits "data as-of: 2026-07-06 15:31:42". Note: table is refreshed not frozen (AUD-48 path) — caveat reworded to match reality)
- **Component:** Pat freshness contract | **Reporter:** pat-nl-explainability.
- **Files:** `src/pat/web.py:2240,2255,2290-2301`; `src/core/db.py:416` (fetched_at exists).
- **Evidence digest:** `_FRESH["fundamentals"] = (None, None, …)` — the trust-contract comment promises an as-of disclosure the bar omits; the table is frozen (Guardrail #8) so PE screens decay undated.
- **Fix:** wire `("fundamentals","fetched_at")` (same for oscillators/pt14); add explicit "snapshot frozen — valuation ratios may be stale" caveat until XBRL-derived valuations land.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-22 [P1] Research replication stack bypasses the provenance PIT layer (gates on the leaky modeled report_date)** — `OPEN`
- **Component:** PIT enforcement in research consumers | **Reporter:** inst-dd.
- **Files:** `research/explosive_moves/attribution.py:60-69`, `factor_zoo.py:32-46`, `gate_study.py:32-46`; `src/automation/fundamentals_asof.py` (the fix they bypass).
- **Evidence digest:** all filter `rd <= asof` on the stored +90/+50 modeled report_date — the path the house's own PIT layer documents as leaking ~12% for late filers; the memo cites provenance as the leak fix yet its replication protocol re-runs these modules; `attribution.py:8` mislabels inputs "PIT". The binding t=1.99 attribution evidence was produced on deprecated inputs.
- **Fix:** route research fundamentals loads through the `fundamentals_asof` effective-date map; re-run attribution and record whether the residual-alpha conclusion holds (ledger entry either way).
- **Effort:** M | **Verdict:** CONFIRMED.

### P1 — pipeline & operations

**AUD-23 [P1] fundamentals_xbrl ingest: no seen-table, no throttle breaker, uncapped gate fan-out — will not survive results season (~Jul-09)** — `DONE 911d020` (seen-table + throttle breaker + gate budget shipped; Jul-09 risk closed; verified)
- **Component:** fundamentals_xbrl ingest | **Reporters:** data-eng (P1 CONFIRMED) + api-src (re-fetch/no-breaker P2) — merged.
- **Files:** `src/automation/fundamentals_xbrl.py:637-716,756-788`; pattern donor `shareholding_xbrl.py:218-219,301-327`; throttle documented at `insider_events.py:659-665`.
- **Evidence digest:** every filing in the 7-day global window re-fetched all 7 nights; fetch_fail just continues (45s burn per miss, no consec-fail abort); `_gate_symbol` ≈8 paced requests per first-seen symbol and failures return uncached → re-deferred nightly. First heavy results week throttles the run and silently gaps coverage exactly when it matters.
- **Fix:** port shareholding_xbrl's pattern — xml_url seen-table skip, `consec_fail>=6` clean abort with backoff, cap/queue gate-evidence fan-out per run.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-24 [P1] Write transaction held across network I/O: credit_ratings (whole range) + capital_allocation (whole universe) — the a4f1c21/D82 lock class** — `DONE 16037b2` (bounded write txns in both modules; verified — still run the sibling class-sweep grep)
- **Component:** SQLite writer discipline | **Reporters:** data-eng (credit_ratings P0→verified P1; capital_allocation P2) — merged, same class.
- **Files:** `src/automation/credit_ratings.py:341-360`; `src/automation/capital_allocation.py:449-459`; donor pattern `insider_events.py:511,679`.
- **Evidence digest:** single `get_conn()` wraps the fetch/score loops with no in-loop commit — write lock held minutes across NSE I/O / full-universe scoring; a crash rolls back everything. Tolerant init (d5b5933) prevents the 000 crash-loop but starvation + rollback remain.
- **Fix:** `conn.commit()` per chunk (credit_ratings, + consec-fail breaker) and per symbol/50 (capital_allocation; `_fill_percentiles` in its own short txn). **Then sweep: grep every `with get_conn()` wrapping a network/long loop** — the incident pattern must propagate to all writers, not two.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-25 [P1] Feed-liveness monitoring covers ~4 of 12 feeds; regime guard reads undated rows** — `OPEN`
- **Component:** data_quality coverage | **Reporters:** data-eng + api-src (both CONFIRMED) — merged.
- **Files:** `src/automation/data_quality.py:349-371` (feed_freshness: insider+credit only), `:259-277` (market: bhavcopy+momentum only), `:286-296` (regime guard: last 200 index rows, NO date check).
- **Evidence digest:** nothing checks recency of fundamentals_history XBRL arrivals, shareholding_history, fno_oi_signals, participant_oi, bulk_block_deals, concalls, index_rows, sent_news — the Mar-2026 corporates-pit 4-month silent-death class (cited in the module's own docstring) would recur unseen; a frozen index feed yields a plausible stale regime verdict.
- **Fix:** declarative `(table, date_col, max_age_days)` list covering every scheduled writer; date-freshness guard in `chk_regime_guard`; bhavcopy trading-day gap check (holiday-tolerant) — pairs with AUD-14's holiday sentinel.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-26 [P1] Data-quality CRITICALs never page the operator — no push path, no OnFailure= on any unit** — `OPEN`
- **Component:** alerting | **Reporters:** api-src (P0→verified P1); inst-dd's "write-only battery" variant was REFUTED (dq_banner.py already surfaces WARN/CRIT on pages) but its Telegram-push residual folds here.
- **Files:** `src/automation/data_quality.py`, `src/automation/tracker_alerts.py` (reusable delivery path), all 18 systemd units (zero `OnFailure=`); `validation-memo.md:75` promises "ops alert fires" — unimplemented.
- **Evidence digest:** pull-only surfacing (banner) exists; nothing pushes. Known deferral: the bot process was network-blocked for sends in a prior session — verify and solve, don't re-defer silently.
- **Fix:** on `status==critical`, Telegram DM via the existing bot token (tracker_alerts path); `OnFailure=hermes-alert@%n.service` on every ingest unit; align the memo text with what ships.
- **Effort:** S | **Verdict:** CONFIRMED (corrected P1).

**AUD-27 [P1] Scheduler core exists only as unversioned VPS files — 13-step signals chain, pt14batch, deals unrecoverable from git** — `DONE 05e25ec (S77b)`: all 26 live hermes*/nous-hermes* units + drop-ins (incl. the bhavcopy chain, api bind override, both backup stacks) captured VERBATIM into `scripts/systemd/vps-live/`; `scripts/install-systemd.sh` = idempotent install + `--check` drift gate (exits 1 on repo↔etc divergence, flags UNCAPTURED live-only files; never enables/starts — AUD-95-safe). Verified: post-install `--check` clean.
- **Component:** scheduling change-control | **Reporters:** timer-topology + api-src (both CONFIRMED) — merged.
- **Files:** VPS `/etc/systemd/system/hermes-bhavcopy.service.d/{10-signals,20-rsdepth,30-fnooi,40-participant,50-accumscreen}.conf`; VPS-only `hermes-pt14batch.*`, `hermes-deals.*`; `scripts/setup-news.sh:68-95` writes only the bare bhavcopy unit; `docs/mep-strategy-design.md:65` admits the chain is VPS-managed.
- **Evidence digest:** rebuild-from-git silently drops the platform's entire signal/RS/OI computation, pt14 scoring and deals ingest; no repo-based reviewer can even see the real schedule.
- **Fix:** pull the LIVE unit/drop-in contents off the VPS first (they are the truth), commit under `scripts/`, add an idempotent install step (rsync units + daemon-reload); add a deploy check diffing VPS /etc/systemd against the repo.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-28 [P1] The documented deploy script would actively regress live units (bidirectional git/VPS drift)** — `OPEN`
- **Component:** deploy safety | **Reporter:** timer-topology.
- **Files:** `scripts/setup-news.sh:138-148` (heredoc missing the live `ExecStartPre=-cci_pipeline --targets --ingest` on hermes-concalls.service); reverse drift: committed `hermes-code-review.{timer,service}` absent on VPS (dormant by decision D68 — needs a disabled-by-default guard, not deletion).
- **Evidence digest:** a routine "update VPS from GitHub" silently reverts CCI ingest behavior. **Until fixed: never run setup-news.sh on the VPS.**
- **Fix:** regenerate the heredocs from installed truth (do with AUD-27), or replace heredocs with committed unit files the script copies; install-guard the dormant code-review units.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-29 [P1] Zero encoded ordering in the timer dependency chain — failed upstream silently feeds stale data downstream as fresh** — `OPEN`
- **Component:** scheduling ordering | **Reporter:** timer-topology.
- **Files:** all `scripts/*.timer`/`*.service` (no inter-service After=/Requires=); e.g. `hermes-capital-allocation.service:9` "Runs AFTER the XBRL ingest" = a 45-minute hope.
- **Evidence digest:** one NSE failure at 14:00 → that evening's alerts/scans/pt14 run on yesterday's bars presented as fresh; detection is next-morning-06:30 and tolerates 4 days.
- **Fix:** `After=hermes-bhavcopy.service` on dependents + a cheap freshness gate (abort if `MAX(trade_date)` older than expected) in each consumer; chain capital-allocation `After=hermes-fundamentals-xbrl.service`.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-30 [P1] Persistent-timer catch-up storm on restart/boot, colliding with hermes-api startup (observed live 2026-07-02 12:17)** — `MOSTLY DONE 05e25ec (S77b)`: `RandomizedDelaySec=300` on all 20 Persistent hermes timers (300 not 900 — preserves the nightly chain's 15-min spacing). RESIDUAL: no flock/serialization slice yet; setup-news.sh untouched (banned anyway, AUD-28).
- **Component:** scheduling concurrency | **Reporter:** timer-topology.
- **Files:** `scripts/setup-news.sh:214,226` (restarts api then immediately starts the 8-min bhavcopy chain); 11+ committed timers `Persistent=true`; zero flock/RandomizedDelaySec anywhere.
- **Evidence digest:** journal shows 4 timers started the same second while hermes-api flapped 4×; after a real reboot all Persistent timers + VPS-only units fire simultaneously into the DBs while uvicorn boots — the D82 outage class, only partially mitigated by tolerant init.
- **Fix:** `RandomizedDelaySec=300-900` on Persistent timers; a shared serialization slice or flock wrapper for DB-writing jobs; make setup-news.sh start bhavcopy only outside api restart windows.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-31 [P1] Hung job blocks all future runs: infinite start timeout, no RuntimeMaxSec on any unit (posture rests on a factually wrong comment)** — `DONE 05e25ec (S77b)`: `TimeoutStartSec` (the correct knob for the all-oneshot fleet — RuntimeMaxSec is ignored for oneshot, per the 5f30d95 lesson) on every ingest unit via 90-hardening.conf drop-ins: default 30min; bhavcopy 2h, concall-capture 3h, momentum/concalls/fundamentals-xbrl/backup/theme-seed 1h. db-backup already tuned by its own lane.
- **Component:** scheduling timeout policy | **Reporter:** timer-topology.
- **Files:** `scripts/hermes-concall-capture.service:5-10` (comment misclaims a ~90s oneshot default kill — oneshot start timeout is disabled by default); zero `RuntimeMaxSec`/`WatchdogSec` across all units.
- **Evidence digest:** one wedged NSE fetch leaves a unit "activating" forever; systemd silently skips every subsequent fire — a daily ingest stops permanently until someone notices.
- **Fix:** `RuntimeMaxSec` per service (≈30min ingests, ≈3h concall-capture); correct the misleading comment.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-32 [P1] early-signals + sector-momentum mounts live only as an uncommitted VPS patch — clean deploy 404s nav-linked pages** — `DONE a24cf23` (continuation lane committed both _ROUTER_SPECS mounts + lenses; nav gate PASS 0 orphans; verified. Residual: teach chrome_gate to follow the /dash/strategies 307 workspace-root redirect — fold into AUD-32 or a new gate-hardening nit)
- **Component:** route wiring | **Reporters:** ui-arch (CONFIRMED P1) + linkage (its "flagship 404s today" framing REFUTED — live VPS serves both; the git-capture debt is what remains). Already queue item #2 in NEXT-SESSION-CARRYFORWARD.
- **Files:** `src/web/v2_surfaces.py:42-87` (_ROUTER_SPECS ends at glossary), `src/web/lens_registry.py`, `src/web/early_signals.py:133`, `src/web/sector_momentum.py:152`; `cycle_clock.py:104` deep-links the route.
- **Fix:** add both `_ROUTER_SPECS` entries + Lens/allowlist entries; nav-integrity gate must pass from `main`. 2-line-class change — coordinate with the lane that owns queue #2 before committing (kickstart-pick-verify).
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-33 [P1] Index names case-broken in momentum pane — every sector link on the divergence board renders an empty pane** — `DONE S77 (deployed+verified)` (momentum_pane.py:248 numerator match → COLLATE NOCASE; live proof S&P-CNX-500-SHARIAH 0→241 rows; 3 sector panes Nifty IT/CNX Consumption/Nifty Bank now render RS ✓. Commit in the momentum_pane fix)
- **Component:** momentum_pane | **Reporter:** linkage (finder P0; verifier P1 — board itself works, pane fails safe, data reachable via /dash/rrg).
- **Files:** `src/web/momentum_pane.py:219,248-250,289,352`; numerators stored Title-case (`index_signals.py:464`); `divergence_board.py:77,109`.
- **Evidence digest:** `sym.upper()` vs Title-case `ratio_rows.numerator` under BINARY collation → "No RS series on record" for every sector click on Ramana's explicitly requested early-warning board; `index_signals.py:38-40` documents the identical prior bug.
- **Fix:** try the original-cased token against ratio_rows (or `COLLATE NOCASE` on the numerator comparison); once AUD-32 lands, point divergence_board sector rows at /dash/sector-momentum for constituent fan-out.
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-34 [P1] SSH permits root password login with no fail2ban** — `MOSTLY DONE (parallel lane, S77-verified)` (sshd -T live: passwordauthentication no, permitrootlogin without-password, pubkeyauthentication yes — key-only, the password brute-force surface is gone. Residual: fail2ban still inactive — lower value now that password auth is off; install a sshd jail when convenient)
- **Component:** VPS sshd | **Reporter:** sec-ops. (Finder's file anchor was wrong; claim re-measured and right.)
- **Evidence digest:** `sshd -T`: `permitrootlogin yes`, `passwordauthentication yes`; fail2ban and ufw both inactive; box holds all secrets + the dataset.
- **Fix:** `PermitRootLogin prohibit-password`, `PasswordAuthentication no` (key-only — the laptop key already works), sudo user, fail2ban sshd jail. **Verify key login in a second SSH session before closing the first.**
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-35 [P1] Both public-facing daemons and all ingest units run as root with zero sandboxing** — `SANDBOX DONE 05e25ec (S77b), User= migration open`: NoNewPrivileges + PrivateTmp + ProtectHome + ProtectSystem=strict + ReadWritePaths=/opt/hermes /var/log on all hermes services incl. api+telegram (nous/docker units excluded — docker-socket trust domain). Verified live: daemons restarted under sandbox (routes 200, guard intact); data-quality + backup ran sandboxed end-to-end. RESIDUAL: dedicated unprivileged user needs a chown window for the root-owned DBs — do NOT flip User= casually.
- **Component:** systemd hardening | **Reporter:** sec-ops.
- **Files:** `scripts/setup-news.sh:197-204` (hermes-api, no User=), `scripts/vps-bootstrap.sh:93` (User=root); zero NoNewPrivileges/ProtectSystem/PrivateTmp anywhere.
- **Fix:** dedicated unprivileged user; `NoNewPrivileges=yes`, `ProtectSystem=strict`, `PrivateTmp=yes`, `ProtectHome=yes`, `ReadWritePaths=/opt/hermes/data`; roll out unit-by-unit with a writer-safe restart each.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-36 [P1] Raw internal exception text leaks to external clients (/v1 catch-all, /chat reply, Telegram replies)** — `DONE (external surfaces) 0bb0875 (S77b), deployed+verified`: /v1 catch-all logs the full exception keyed by request_id and returns a generic detail; chat.py logs APIError.message and returns a generic reply (covers /chat AND the bot's chat.handle path). RESIDUAL (P3): telegram_bot.py's 3 own reply sites (603/1679/1987) — single-tenant allowlisted chat, low exposure. NOTE: the apparent prod-fork of chat.py / v1/__init__.py / telegram_bot.py was PURE CRLF (old Windows scp) — content matched git exactly after CR-strip; the two patched files are now LF-clean and git-identical on the VPS.
- **Component:** error contract | **Reporters:** v1-api-contract (P1 CONFIRMED) + telegram-assistant (P2, finder-only) — merged, same class.
- **Files:** `src/api/v1/__init__.py:62-67` (RFC-7807 detail = `str(exc)` verbatim — sqlite paths/SQL fragments), `src/assistant/chat.py:171`, `src/assistant/telegram_bot.py:603,1679,1987`.
- **Fix:** generic client-facing detail ("unexpected error; quote request_id"), full detail server-side keyed by request_id; sweep the three sites.
- **Effort:** S | **Verdict:** CONFIRMED (v1) / finder-only (assistant sites).

**AUD-37 [P1] /v1 metering under-records: 500s never logged, bytes_out always 0, insert failures silently dropped — billing substrate not audit-grade** — `OPEN`
- **Component:** metering middleware | **Reporter:** v1-api-contract.
- **Files:** `src/api/v1/__init__.py:34-52`, `src/api/v1/metering.py:9-10,60-61`.
- **Evidence digest:** unhandled exceptions bypass `record_usage` (contradicting "one row per request incl. 4xx/5xx"); BaseHTTPMiddleware streaming wrapper has no `.body` → bytes_out=0 every row; insert failures swallowed exactly during lock episodes; 500s also lack X-Request-ID/RateLimit headers.
- **Fix:** try/finally around call_next recording the exception path; bytes from Content-Length; count record_usage failures to a visible metric; add a daily/monthly quota beside rate_check.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-38 [P1] PIT — the product wedge — is not on the /v1 contract (5 of 6 endpoints latest-row-only)** — `OPEN`
- **Component:** /v1 PIT semantics | **Reporter:** v1-api-contract.
- **Files:** `src/api/v1/routes.py:61,78-79,105`; `src/api/v1/resources.py:41`; `signal_events.py:193-203` (as_of exists internally, unexposed).
- **Evidence digest:** only /universe takes `as_of`; credibility serves `series[-1]`; a PMS/AIF client cannot run their own leak audit against the paid API — the replay-the-tape claim is demoable but not purchasable. (Envelope does stamp `_meta.as_of` — outputs are PIT-stamped, not PIT-queryable.)
- **Fix:** add `as_of` to credibility (serve the as-of series row stamped with knowable/effective dates) and expose attention_queue's existing param; document per-endpoint PIT semantics in OpenAPI.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-39 [P1] Zero automated tests on the computational core; every gate is render-level** — `DONE S77 (harness stood up)` (tests/ + conftest.py + requirements-dev.txt + regression_sweep.sh gate-0; seeded with scoring+momentum golden tests; grow the suite with every quant fix)
- **Component:** testing | **Reporter:** hygiene.
- **Files:** `scripts/regression_sweep.sh:44-89` (chrome/nav/color/HTTP-200 only); untested: `scoring.py`, `signals.py` (1,177 lines), `provenance.py` (1,274 lines, PIT joins), XIRR Newton+bisection `dashboard.py:3457`, equity-curve/drawdown `:3527`.
- **Evidence digest:** a wrong sign or off-by-one PIT join ships while every gate passes — the standing integrity breach that makes the rest of this program recur.
- **Fix:** pytest + golden-file fixture DB; start with ~20 tests on scoring + PIT as-of joins + XIRR/drawdown on known cashflows; wire `pytest -q` as gate 0 of regression_sweep.sh. **Every AUD quant fix in this program should land with its regression test.**
- **Effort:** L (incremental) | **Verdict:** CONFIRMED.

**AUD-40 [P1] Pat eval battery wired to no gate, timer, or CI — the accuracy layer never runs anywhere** — `OPEN`
- **Component:** Pat regression net | **Reporter:** pat-nl-explainability.
- **Files:** `src/pat/eval_set.py:539` (__main__ only; accuracy layer skips without prod DB; known-failing cases left standing).
- **Fix:** add compiler+route+explain+hallucination evals to the deploy gate and a nightly timer alerting on fails; run the accuracy layer against the prod DB; fix the Windows charmap crash in the skip printer.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-41 [P1] Stock dossier carries zero sector-state context and no link to any index surface** — `DONE S77 (deployed+verified, incl. AUD-77)` (dashboard.py RS tab: descriptive "Sector context" block — stock's own rs_phase (AUD-77) + sector's rs_phase (index_signals identity join, COLLATE NOCASE) + links to /dash/rrg?idx= and /dash/sector-momentum. Live: WIPRO→HEADWIND·Nifty IT→HEADWIND, ZYDUSLIFE→ROLLING-OVER·Nifty Healthcare→TAILWIND. Descriptive-only C10; fail-safe; dossier intact. D80 append-only patch)
- **Component:** dossier ↔ index linkage | **Reporter:** linkage.
- **Files:** `src/web/dashboard.py:6244-6248` (sector = plain text), `:6593-6608` (8 verdict tiles, none sector-level); data all exists (`index_signals.rs_phase`, rs_extras quadrant, capture_signals); `nav_links.index_link()` exists unused.
- **Fix:** add a "Sector context" tile (sector rs_phase pill + RRG quadrant + capture quadrant — one query each on primary_sector); hyperlink the sector name to `/dash/index?idx=` with siblings to `/dash/sector-momentum` and `/dash/rrg?idx=`. Surgical D80-style patch — dashboard.py is frozen-contended; append-only + import-test.
- **Effort:** M | **Verdict:** CONFIRMED.

**AUD-42 [P1] Pat cannot answer cross-level questions — no sector superlative resolver, no index→stock join** — `OPEN`
- **Component:** Pat NL engine | **Reporter:** linkage.
- **Files:** `src/pat/understand.py:197-198,380-395`; `src/pat/flows.py:88-90,457-482,654`.
- **Evidence digest:** "which stocks in the strongest sector are accumulating" — the demo-defining question — structurally unanswerable; note the fix needs an index_name→primary_sector mapping (different vocabularies).
- **Fix:** 2-query plan — when rank asks a sector superlative, run build_index_query, map top index_name→primary_sector, bind into ACC/RS flows; add rs_phase to flow SELECTs + a phase chip.
- **Effort:** L | **Verdict:** CONFIRMED.

**AUD-43 [P1] equity_list replaced wholesale with no minimum-row sanity — one truncated CSV shrinks the allowlist gating every scanner** — `OPEN`
- **Component:** format-drift defense | **Reporter:** api-src (finder-only — not adversarially verified).
- **Files:** `src/automation/equity_list.py:48,71-81`.
- **Fix:** refuse the replace if new count < 90% of existing (log critical); add row-count bands vs trailing median to bhavcopy/indexes before marking a date done.
- **Effort:** S | **Verdict:** finder-only (unverified).

**AUD-44 [P1] bhavcopy_rows.raw_json ≈3GB write-only duplication with zero readers (~19% of the DB)** — `OPEN`
- **Component:** space discipline | **Reporter:** db-schema.
- **Files:** `src/automation/bhavcopy.py:208,253,304`; `src/core/db.py:132`.
- **Evidence digest:** written, never SELECTed anywhere; the raw NSE files are already archived on disk back to 2004 (`save_raw`), so Guardrail #6 is satisfied by the file archive — this is a third copy. Violates the binding space-optimization mandate and directly worsens AUD-02's backup cost.
- **Fix:** stop populating for new ingests (keep the column); optional one-time verified NULLing pass of history (DB-writing pass — treat as a scheduled maintenance window, writer-safe).
- **Effort:** S | **Verdict:** CONFIRMED.

**AUD-45 [P1] Canonical weights doc covers ~30% of live calculation constants** — `OPEN`
- **Component:** calculations-and-weights governance | **Reporter:** quant (finder-only).
- **Files:** `docs/calculations-and-weights.md`; missing engines: rs_rank blend 0.6/0.4 (`stock_rs.py:239`), D43 `_CHAR_THRESH`, ignition multipliers, MEP bands/hysteresis, rsband knobs, CPR width knobs.
- **Fix:** one section per engine (formula + canonical file:symbol pointer, §3 pattern); numbers stay machine-owned. Do together with AUD-15.
- **Effort:** M | **Verdict:** finder-only (unverified).

**AUD-46 [P1] Every authenticated /v1 read performs 3-4 write transactions on the shared single-writer SQLite** — `OPEN`
- **Component:** /v1 hot path | **Reporter:** v1-api-contract (finder-only).
- **Files:** `src/api/v1/auth.py:75,88`, `src/api/v1/metering.py:33-44,55-59`.
- **Fix:** ensure_schema once at build_app; batch `last_used_at` (≤1/min per key); in-process rate counter (correct at 1 worker); queue usage rows, flush in batches.
- **Effort:** M | **Verdict:** finder-only (unverified).

### P2 — real debt (compact; verify each with kickstart-pick-verify before starting)

| AUD | Sev | Title | Component / files | Fix (digest) | Effort | Verdict |
|---|---|---|---|---|---|---|
| AUD-47 | P2 | Shareholding XBRL lacks the restatement journal (kill-switch #4 blind to SHP) — residual of refuted restatement P0 | `shareholding_xbrl.py:255-269`; donor `fundamentals_xbrl.py:583-597` | port the fundamentals_restatements journaling pattern | S | residual of REFUTED (verifier-identified) |
| AUD-48 | P2 | Guardrail-#8: scheduled Screener scrape paths still live (news timer, concall discovery, enrich) | `news_feed.py:479`→`scoring.py:381`→`screener.py:220-228`; `concalls.py:43,147,266`; `enrich.py:192` | cache-only for scheduled callers (read fundamentals_asof); concall discovery via concall_bse.py; whitelist tickers vs nse_equity_list | M | CONFIRMED (↓P2 — documented transitional exception, but shrink it) |
| AUD-49 | P2 | Fundamentals snapshot table = parallel truth still refreshed daily; dashboards can contradict XBRL/PIT with no source stamp | `dashboard.py:3305,5796`; `fundamentals` table | derive latest-snapshot reads from fundamentals_history where mapped; stamp source+as-of; stop refresh for XBRL-covered symbols | M | finder-only |
| AUD-50 | P2 | Cross-run SA/CONSO overwrite: standalone revision can replace a consolidated fundamentals row | `fundamentals_xbrl.py:565-575,586-595,604-728` | refuse SA-over-CONSO replace for same key; merge legacy+IF candidates into one prefer-consolidated pool | M | finder-only |
| AUD-51 | P2 | Continuity-gate verdicts cached forever; no re-arbitration, no post-pass scaling sanity (100× SHP risk on format drift) | `fundamentals_xbrl.py:516-518,924-926`; `shareholding_xbrl.py:228-230` | age FAIL verdicts (re-gate after N quarters / mapper bumps); per-run check Promoters+Public≈100 | M | finder-only |
| AUD-52 | P2 | NSE anti-bot session bootstrap now 5 copies with drifting UAs; no re-warm on 401/403 | `fundamentals_xbrl.py:77`, `insider_events.py:444`, `shareholding_xbrl.py:80`, `credit_ratings.py:302`, untracked `sast_events.py:262` | new `src/core/nse_http.py` (or nse_client.py): warmed session factory, one UA, retry-with-re-warm, pacing const; migrate the 5 | M | CONFIRMED (↓P2; hygiene + api-src merged) |
| AUD-53 | P2 | Deals feed: current-day-only, no retry, no cookie warmup, no liveness — one 403 evening = permanent loss | `deals.py:86-97` | 3× backoff retries + second late-evening attempt; shared warmed session; add to feed_freshness (with AUD-25) | S | finder-only |
| AUD-54 | P2 | /v1 attention `limit=-1` bypasses the hard cap (one day's dump, not whole table); MCP int() crash on bad limit | `routes.py:105`, `resources.py:45`, `tools.py:96` | `Query(ge=1, le=6)`; `max(1,min(limit,6))`; validate inside try → typed absence | S | CONFIRMED (↓P2) |
| AUD-55 | P2 | /v1 has no response models/versioning; shape already broke once inside "v1.0" (c885962) | `routes.py`, `envelope.py:21`, sdk `client.py` | pydantic response models asserted by selftest; bump METHODOLOGY_VERSION on shape change; CHANGELOG + Deprecation header convention | M | finder-only |
| AUD-56 | P2 | /v1 selftests wired to nothing; `_teardown` DELETEs rows from the "append-only" billing log on whatever DB it hits | `selftest.py:11-21,41-93` | add to release gate; teardown refuses non-scratch DB (env guard) / test-only tenant ids | S | finder-only |
| AUD-57 | P2 | Stale /v1 gating docstrings (alpha-gate deleted, mount unconditional); invalid as_of silently swallowed → 200 | `routes.py:5-9`, `__init__.py:4-9`, `provenance.py:822-827` | rewrite docstrings to ungated reality; 422 on non-ISO as_of | S | finder-only |
| AUD-58 | P2 | Benchmark is the Nifty-500 **price** index, not total return — hurdle understated ~1.2-1.4%/yr | `research/explosive_moves/metrics.py:80-86`; `strategy-ledger.md:53` | ingest Nifty-500 TRI (NSE publishes); re-run cost_participation + ledger hurdles vs TRI; restate + disclose | M | finder-only |
| AUD-59 | P2 | Kill-switches #1 (WML leg) and #3 (rank-IC) unbuilt — no live-decay tripwire on the deployed ensemble | `validation-memo.md:88-90`; momentum_scan history exists as input | monthly job: rank-IC of ensemble_pctile vs 1-mo forward returns + trailing WML-proxy DD → data_quality_runs (rides AUD-26 alerting) | M | finder-only |
| AUD-60 | P2 | No versioned methodology changelog or restatement/corrections policy doc (standard QIS deliverables) | `calculations-and-weights.md §6`; provenance `method_versioned=False` | dated append-only changelog section; one-page corrections policy; stamp method_version on new derived rows | S | finder-only |
| AUD-61 | P2 | No SLA/uptime/DR story for the one-box SQLite operating model | docs/ (absent) | honest ops one-pager: architecture, backup cadence (post AUD-02), restore evidence, measured uptime, stated service level | S | finder-only |
| AUD-62 | P2 | Single uvicorn worker; one heavy handler queues all users | `setup-news.sh:200` | after AUD-04, optionally `--workers 2` (verify WAL/tolerant-init safety; mind in-process rate counter in AUD-46) | S | finder-only |
| AUD-63 | P2 | /dash/screen2 ships 2.2MB HTML in one document | `screener_plus.py` | server-side pagination/virtualized rows; keep wide-table doctrine; CSV for the rest | M | finder-only |
| AUD-64 | P2 | Leaders/conviction join stock and index states from independently-MAXed dates | `stock_rs.py:492-495,539-543` | index row at-or-before the stock trade_date; warn visibly on divergence | S | finder-only |
| AUD-65 | P2 | Level-MA accepts window//2 data (a "200d MA" from 100 closes) while ratio-MA requires full window | `index_signals.py:102-109` vs `:245-249` | require ≥0.9×window or label the fallback | S | finder-only |
| AUD-66 | P2 | Four-layer chrome monkey-patch chain is the permanent architecture (regex header swap, 3 nav renderers, sys.modules sweep) | `shell_skin.py:454-542`, `v2_surfaces.py:270-320`, `table_controls.py:173`, `main.py:288` | declare cut-over: `_shell` delegates natively to ui_kit.topbar/native_subnav; delete `_wrapped_nav`+header regex; keep CSS injection | L | CONFIRMED (↓P2 — documented deliberate + gated, but converge) |
| AUD-67 | P2 | Same gauge, two color contracts: `_mep_pill`/`_mv_adbar` duplicated cockpit vs screener_plus (DISTRIB amber vs red) | `cockpit.py:537,555-562` vs `screener_plus.py:253-257,393` | one shared glyph module (ui_components/signals_glyphs.py); one color contract per state | S | CONFIRMED (↓P2) |
| AUD-68 | P2 | cmdk Ask-Pat palette hand-maintains a third destination map, already drifted (missing 9 lenses, flat 307 URLs) | `ui_kit.py:274-281` | generate PAGES from lens_registry (key+aliases→nested_path); delete the literal | S | finder-only |
| AUD-69 | P2 | shell_skin byte-duplicates ui_kit component geometry — native vs reskinned pages fork on any design change | `shell_skin.py:191-205` vs `ui_kit.py:129-166` | promote to ui_tokens custom properties; reference from both | M | finder-only |
| AUD-70 | P2 | Per-view private palettes require whack-a-mole retinting; new lenses launch off-brand by default | `shell_skin.py:226-263`; 24 modules with own `<style>` | chrome_gate check failing legacy hex literals in view styles; starter stylesheet composing tokens | M | finder-only |
| AUD-71 | P2 | Header ?-popover / column-control coverage = 2 of ~35 pages, in two divergent systems | `table_controls.py:21`; `screener_plus.py:531` | extend `table_controls._PAGES` to cockpit tables + classic screener; converge Screen+ popovers on glossary.gloss | S | finder-only |
| AUD-72 | P2 | Two full screeners with feature drift and no sunset criterion (deliberate to keep both — needs a parity gate, not removal) | `dashboard.py:1608-2708` vs `screener_plus.py` | make `parity_report()` a gate with a sunset condition; freeze new columns on the classic path | M | finder-only |
| AUD-73 | P2 | Screeners expose no rotation-phase columns (stock rs_phase / sector phase unfilterable) | `screener_plus.py:611-631`, `dashboard.py:1645-1672`; join exists in `stock_rs.py:596-605` | add s.rs_phase + sector-phase LEFT JOIN as phase pills in the rs group + filters | M | CONFIRMED (↓P2) |
| AUD-74 | P2 | No index-level event fan-out: no sector_phase_change alert rule; digest is news-only | `dashboard.py:3796-3869`, `tracker_alerts.py` | edge-triggered "your sector flipped X→Y" rule resolving watched stocks' primary_sector (descriptive notification, not a gate) | M | CONFIRMED (↓P2) |
| AUD-75 | P2 | Capture-map dots not clickable; no constituent path from the all-weather map | `capture_map.py:119-121,143-144` | wrap dots in `/dash/rrg?idx=` links (cycle_clock pattern); add `/dash/index?idx=` column | S | finder-only |
| AUD-76 | P2 | Home cockpit lacks the "just turned today" feed (phase movers + divergence preview built but unmounted) | `cockpit.py:568-798`; `stock_rs.phase_movers`; `divergence_board.preview_html` | append two precomputed boards to render_home — zero new compute | S | finder-only |
| AUD-77 | P2 | Stock's own rs_phase hidden on dossier and Pat card (vocabulary breaks at stock level) | `dashboard.py` (no rs_phase read), `flows.py:786-801` | add rs_phase pill to dossier verdict strip (with AUD-41) + stock-card query | S | finder-only |
| AUD-78 | P2 | dashboard.py 8,177-line monolith circularly coupled to cockpit.py — highest-churn file in a 5-session tree | `dashboard.py:1149,1685,2698,6562`; seams at 1008/2929/3457/5116/8087 | D80-safe carve-outs: portfolio_math.py (XIRR/curves) → tracker_view.py → importer; one block per session, chrome gate after each | M | CONFIRMED (↓P2) |
| AUD-79 | P2 | 41 except-Exception-pass sites; scheduled pipelines silently shrink their universe (CCI watchlist/conviction/PILOT) | `cci_pipeline.py:52-62`, `pat/engine.py`, `rsband_view.py` | replace bare `pass` with `log.warning`; ruff S110/BLE001 in the gate to freeze the count | S | finder-only |
| AUD-80 | P2 | ~1,150 lines of orphan modules (preview_app, accum_screen, ignition_rankv2/zones, score_batch, rs_phase.py) | src/web + src/api | quarantine list in PROJECT_STATE; kickstart-pick-verify each; git rm confirmed-dead in one commit (early_signals/sector_momentum resolve via AUD-32) | S | finder-only |
| AUD-81 | P2 | No .gitattributes: CRLF tree feeds the scp deploy to Linux; LF is a human-memory rule | repo root | `*.py/*.sh/*.service/*.timer text eol=lf` + renormalize; or deploy via `git show HEAD:file` | S | finder-only |
| AUD-82 | P2 | Dead pins (sqlalchemy, structlog) shipped to prod; no py3.10 syntax gate (VPS is 3.10, laptop 3.11+) | `requirements.txt:24,27` | remove pins; add `python3.10 -m compileall -q src scripts` to the gate | S | finder-only |
| AUD-83 | P2 | 120 .bak revert-backup files in the shared tree with no retention rule | src/, scripts/ | retention rule in PROJECT_STATE (deletable once committed+gate-passed); dedicated sweep session | S | finder-only |
| AUD-84 | P2 | 20 copies of `_esc`, duplicated `_num`, 6 re-implementations of the trade-dates query | `ui_kit.py:45` + 20 siblings | import leaf helpers from ui_kit (`from ui_kit import esc as _esc` — no route coupling); canonical trade-dates helper in db.py | S | finder-only |
| AUD-85 | P2 | Two glossary sources drift from each other AND code (R-windows calendar-vs-trading days; P2M omitted; ×Power 4 vs ignition 5 baselines) | `pat/glossary.py:220` vs `signals.py:63`; `metrics-glossary.md:12-14` | correct the wrong strings; longer-term derive pat entries from metrics-glossary sections | M | finder-only |
| AUD-86 | P2 | md parser drops nested sub-bullets → Tier and Conviction popovers end in a dangling colon (vacuous) | `src/web/glossary.py:67`, `glossary_view.py:57`; `metrics-glossary.md:34-46` | flatten entries or teach parser to append indented sub-bullets; lint bodies ending ':' or <40 chars | S | finder-only |
| AUD-87 | P2 | Working-notes voice on client-facing glossary ("I (Claude) introduced…", stale examples) | `metrics-glossary.md:31,32,40,42` | one editorial pass: neutral product voice, keep honest caveats as product limitations | S | finder-only |
| AUD-88 | P2 | Pat mis-states its own lineage: fundamentals described as live Screener pull; no freeze/XBRL disclosure | `pat/glossary.py:611+,640-648` | update entries: frozen legacy snapshot + NSE XBRL for new periods + broadcast-timestamp PIT story (Guardrail #8 disclosure duty) | S | finder-only |
| AUD-89 | P2 | ★ glyph has two conflicting meanings (triple-confirm vs Screen+ confluence≥4) and one glossary entry | `metrics-glossary.md:47` vs `screener_plus.py:655-663` | rename the Screen+ flag (✦/'C4+') or add a distinct glossary key per column header | S | finder-only |
| AUD-90 | P2 | No log rotation on /var/log/hermes-*.log (unbounded growth on the DB disk) | setup-news.sh units | logrotate.d/hermes (daily, rotate 14, compress, copytruncate) or journald with SystemMaxUse | S | finder-only |
| AUD-91 | P2 | No global Telegram error handler; handlers deref update.message (None for edited/channel posts under ALL_TYPES) | `telegram_bot.py:77,250,2167-2211` | app.add_error_handler (log + owner notify); guard `if not update.message` / use effective_message | S | finder-only |
| AUD-92 | P2 | Conversations retain PII indefinitely; /reset never deletes; no retention policy | `conversations.py:15,30`, `db.py:23-37` | retention/purge job (N days); make /reset archive/delete; document (do after AUD-01 closes the exposure) | M | finder-only |
| AUD-93 | P2 | Designed same-second writer collision: insider-ingest and pt14batch both 15:30:00 on hermes.db | `hermes-insider-ingest.timer:5` + VPS pt14batch | move pt14batch to 15:40 or After=; rule: never pin two writers of one SQLite file to the same minute | S | finder-only |
| AUD-94 | P2 | Zero resource containment on a 16GB zero-swap box shared with uvicorn (OOM killer targets the API) | all units | MemoryMax/CPUQuota on heavy batches; OOMScoreAdjust=-500 on hermes-api; modest swapfile (see AUD-108) | S | finder-only |
| AUD-95 | P2 | `Requires=<own service>` in 9+ timers — any `systemctl start <timer>` executes the job immediately (compounds AUD-30) | `hermes-wolfe-scan.timer:3` et al.; correct pattern documented in `hermes-fundamentals-provenance.timer:3-4` | delete the Requires= lines | S | finder-only |
| AUD-96 | P2 | All schedules are naked wall-times; correctness rests on the box being Etc/UTC (rebuild → 5.5h shift, platform-wide silent failure) | all `OnCalendar=` | append `Asia/Kolkata` to OnCalendar (systemd 249 supports) or assert timezone in the installer | S | finder-only |
| AUD-97 | P2 | ~550MB prefix-redundant/useless indexes rebuilt nightly | `db.py:323,360-363,650-654` | DROP idx_signals_date/idx_mep_date/idx_cpr_tf_date/idx_sent_news_url/idx_bhav_series after EQP verification; remove from SCHEMA_BASE | S | finder-only |
| AUD-98 | P2 | Planner stats exist for exactly one table; no ANALYZE/PRAGMA optimize anywhere | `db.py:982-1001` | `PRAGMA optimize` before close in get_conn; weekly ANALYZE via the data-quality timer | S | finder-only |
| AUD-99 | P2 | Schema DDL fragmented across 40+ modules; fno_oi_signals/mep_signals/participant_oi defined twice (silent divergence risk) | `db.py:333,372,401` vs module DDL | delete duplicate module DDL (db.py canonical); check in a generated `.schema` dump refreshed by the DQ timer | M | finder-only |
| AUD-100 | P2 | Dead schema in prod: 4 empty MTF tables + signal_events with no timer; ignition research tables in hermes.db | `db.py:491`; `signal_events.py` | land D52 MTF backfill + consumer or park DDL behind the module; relocate ignition_* to research.db; wire or remove signal_events | M | finder-only |

### P3 — polish (compact)

| AUD | Sev | Title | Files | Fix | Effort |
|---|---|---|---|---|---|
| AUD-101 | P3 | No HTTP cache validators on any dashboard page | `coverage_view.py:735` etc. | Cache-Control private,max-age + ETag from MAX(trade_date)/snapshot stamp on read-only GETs | S |
| AUD-102 | P3 | Dead style guide: /dash/ui-kit router never mounted while /dash/_ui duplicates it | `ui_kit.py:414` | delete route/showcase (keep component API) or redirect; one style guide | S |
| AUD-103 | P3 | Unreachable dash_scan body (55 lines after an unconditional 307) + root clutter | `dashboard.py:1244` | delete the dead body (git history preserves); gitignore *.bak-* | S |
| AUD-104 | P3 | Four sub-nav renderer implementations coexist (two dead at runtime, still maintained) | `ui_kit.py:325`, `v2_surfaces.py:300-311,349`, `dashboard.py:434-475` | after AUD-66: delete dashboard._SUBNAV + .v2subnav; ui_kit.subnav consumes the registry directly | M |
| AUD-105 | P3 | insider gg transaction_dt fallback stores raw unparsed NSE date strings (mixed formats) | `insider_events.py:592-596` | store None when _nse_date can't parse | S |
| AUD-106 | P3 | `_parse_nse_dt` KeyError aborts the whole listing page on one malformed month token | `fundamentals_xbrl.py:103` | `_MON.get()` + skip, mirroring shareholding_xbrl | S |
| AUD-107 | P3 | Wilder RSI returns 100 (overbought) on zero-variance series → false 'extended' on dead pairs | `rrg.py:122-125` | return 50.0 (or None) when both avg gain and loss are 0 | S |
| AUD-108 | P3 | Zero swap on a 16GB box mmapping a 16GB DB (OOM insurance absent) | VPS | 2-4GB swapfile; cap SQLite mmap_size; available-memory alert (pairs with AUD-94) | S |
| AUD-109 | P3 | Universe-drift check window mislabeled: last-25-snapshots, not one month | `data_quality.py:301-307` | select snapshot nearest as_of−30d; report actual window length | S |
| AUD-110 | P3 | feedparser.parse(url) fetches with no timeout in the scheduled news job | `news_feed.py:68` | requests.get(timeout=15) → feedparser.parse(bytes) | S |
| AUD-111 | P3 | Tenant credentials + user write-state co-located in the 16GB analytics file | `api/v1/schema.py:17-69` | split a small app.db (tenants/keys/tracker/drawings/pat_*) — makes AUD-02 nightly-and-tiny; isolates lock domains | L |
| AUD-112 | P3 | No retention/growth policy for append-forever tables; DB size not monitored | PROJECT_STATE | per-family retention paragraph; DQ timer reports DB size + top-10 tables | S |
| AUD-113 | P3 | RS-hub preview chips are dead text (entities named but not linked) | `rs_section.py:118-122,141-144` | per-entity links in a non-anchored footer (nested <a> invalid) | S |
| AUD-114 | P3 | Stale one-off scripts + dormant GLM code-review stack indistinguishable from live tooling | scripts/ | TRANSIENT header-tag + attic/ per transient-doc-lifecycle; comment code-review units dormant-by-decision | S |
| AUD-115 | P3 | Duplicate session-boot doc + 38 tracked codex-bridge transcripts in the product repo | `NEXT_SESSION_KICKSTART.md`, codex-bridge/ | reduce kickstart to a pointer at docs/NEXT-SESSION-CARRYFORWARD.md; fold transcripts per transient-doc-lifecycle | S |
| AUD-116 | P3 | Pat degraded-path known-fails left standing (PE-15 → PE-25 screen; two explain aliases dead) | `understand.py:405`, `pat/glossary.py:494` | honor numeric threshold in parse_fallback; add bare-phrase aliases | S |
| AUD-117 | P3 | Weekend/holiday mismatch: daily downstream jobs re-scan/re-alert on Friday's bars | tracker-alerts/momentum-scan timers | Mon..Fri for pure-EOD consumers; shared NSE-holiday no-op check | S |

---

## Cross-cutting themes

**1. The trust wedge is undermined on exactly the surfaces built to sell it.** The single heaviest concentration of confirmed integrity findings sits on the Trust altitude itself: the coverage ledger is the slowest page on the site (AUD-04) and misreports three live datasets as empty (AUD-05); the replay-the-tape artifact claims "actually filed" dates that are uniform +90d models (AUD-18); the validation memo attests to enforcement that does not exist (AUD-19); the glossary both fabricates a bank-scoring mechanism (AUD-16) and leaks the proprietary thresholds it promises never to show (AUD-20). None of these are hard fixes — most are S-effort text/label corrections — but every one is the kind of thing a diligence team verifies first. The house rule that falls out of this audit: **a claim on a trust surface is a liability until code enforces it; when in doubt, downgrade the claim, never the honesty.**

**2. Incident lessons are learned locally, never propagated.** The most striking engineering pattern: every hard-won fix exists in exactly one or two modules while its siblings carry the original bug. Per-chunk commits after the 2026-07-02 write-lock outage reached insider_events but not credit_ratings or capital_allocation (AUD-24); `RetryableFetchError` (CL-RS-13) lives only in fno_oi while six fetchers still record throttles as holidays (AUD-14); adjusted-close discipline (CL-MDC-01) fixed D43 arrays but not zones/key-prices/hot-days (AUD-06); the min-15 hot-day rule (CL-MDC-10) fixed nightly but not backfill (AUD-07); the seen-table + breaker pattern lives in shareholding_xbrl but not fundamentals_xbrl (AUD-23); the restatement journal lives in fundamentals_xbrl but not shareholding_xbrl (AUD-47); the NSE session bootstrap has been copy-pasted five times (AUD-52). The corrective discipline: **every incident fix ends with a class-sweep grep across siblings, recorded in the bug-audit doc.**

**3. Production and git have forked, in both directions.** The 13-step nightly signals chain, pt14batch and deals exist only as VPS files (AUD-27); early-signals/sector-momentum mounts are an uncommitted VPS patch (AUD-32); the live concalls unit carries an ExecStartPre the committed heredoc lacks, so the documented deploy command would regress production (AUD-28); the concall-capture unit and its module have drifted into a live-broken state where neither side matches (AUD-03); meanwhile committed units (code-review) don't exist on the box. A repo that cannot rebuild its own production — and whose deploy script actively damages it — fails the most basic institutional change-control question. The scheduler must become repo-owned in this program's first two sessions.

**4. Everything monitors, nothing pages.** The platform has an unusually good detection story on paper — data_quality battery, kill-switches, eval battery, /v1 selftests, provenance lag audits — and almost none of it is wired to an actor. CRITICALs go to a table and a banner but never a phone (AUD-26); liveness covers 4 of ~12 feeds (AUD-25); Pat's eval battery and the /v1 selftests are run by hand or never (AUD-40, AUD-56); hung timers block silently forever (AUD-31). The Mar-2026 corporates-pit feed died silently for four months and the audit shows the identical failure mode currently open one layer up. Detection without paging is documentation.

**5. Verification asymmetry: pixels are gated, numbers are not.** Chrome, nav integrity, colors and HTTP-200s all have release gates; the computational core — scoring, signals, PIT joins, XIRR — has zero automated tests (AUD-39). This is exactly backwards for a product whose pitch is number-integrity, and it is why spec–code drift (AUD-10, AUD-15) and dual-definition bugs (AUD-07) shipped invisibly. Every quant fix in this program should land with its golden-file regression test so the class, not just the instance, is closed.

**6. The perimeter never grew up with the product.** What was defensible for a personal Telegram bot — 0.0.0.0 binding, root services, password SSH, no firewall, no backup, single box — is now the operating posture of a 16GB proprietary data product with tenant keys and unrecoverable paid extractions on board (AUD-01, AUD-02, AUD-34, AUD-35). The sec-ops F is not a code-quality judgment; the application-layer /v1 auth is genuinely well-built. It is a deployment-posture judgment, and it is the cheapest whole-grade upgrade in the program.

---

## Urgent notes for active parallel sessions

1. **Concalls/CCI lane:** `hermes-concall-capture.service` passes `--universe/--workers/--include-covered` that `src/automation/concalls.py` no longer accepts — every run since ~Jun-28 exits 2; **next run Sun Jul-05 fails too.** Fix or hand to the audit fix session before then (AUD-03).
2. **Nav-wiring lane (carry-forward queue #2):** audit CONFIRMS the early-signals/sector-momentum mounts are VPS-only; commit the `_ROUTER_SPECS` + `lens_registry` entries in `src/web/v2_surfaces.py` before any clean redeploy (AUD-32) — coordinate so it isn't done twice.
3. **Data lane:** `fundamentals_xbrl.py` has no seen-table/throttle breaker and an uncapped gate fan-out — **results season ~Jul-09** will throttle it and gap coverage; port the shareholding_xbrl pattern now (AUD-23).
4. **Everyone deploying:** do **NOT** run `scripts/setup-news.sh` on the VPS — it would silently strip the live `ExecStartPre` from hermes-concalls.service (AUD-28). Deploy by scp per the recipe; also don't `systemctl start` any hermes timer mid-day (Requires= executes the job immediately, AUD-95).
5. **sast_events.py author (untracked file in the tree):** your module is the 5th copy of `_nse_session` — plan to import the shared NSE client when AUD-52 lands, and use per-chunk commits from day one (AUD-24 class).
6. **Security window incoming (AUD-01):** binding uvicorn to 127.0.0.1 + enabling `CHAT_SHARED_SECRET` needs an api restart — writer-safe window required; any session curling the public `:8000` URL for gates must switch to the Caddy hostname or localhost-on-VPS.
7. **Trust/premium-visuals lane:** `coverage_view.py` + `provenance.py` are getting a snapshot cache and descriptor fixes (AUD-04/05) — pull before touching those files; don't ship conflicting edits.
8. **Quality lane (be7826a restatement work):** extend the `fundamentals_restatements` journal to `shareholding_xbrl.py:255-269` so kill-switch #4 also covers SHP (AUD-47) — same pattern you just shipped.

---

## NEXT-SESSION FIX PROMPT

Paste the block below verbatim into a fresh Claude Code session in `D:\Hermes` to execute the corrections autonomously.

```
You are running an autonomous correction session in D:\Hermes, executing the institutional-audit correction program. No user is present — NEVER ask the user anything; resolve every doubt via docs, code, PROJECT_STATE.md, live read-only probes, or subagents.

BOOT
1. Follow docs/SESSION-PROTOCOL.md (binding start/end checklist). Read ONLY the top Session-log entry of PROJECT_STATE.md (lazy-load; grep sections as needed). Run `git log --oneline -20` and `git fetch`; verify the tip.
2. Open docs/AUDIT-2026-07-02-institutional-review.md § "The correction program". The ordered AUD-01..AUD-117 list is your work queue; work it strictly in priority order. Skim docs/NEXT-SESSION-CARRYFORWARD.md first for collisions with parallel lanes (especially AUD-03 concalls and AUD-32 nav-wiring, which other lanes may have taken).

METHOD — per AUD item, in order (record a one-line reason for any skip)
- KICKSTART-PICK-VERIFY FIRST: re-verify the finding READ-ONLY against the current tree/VPS before touching anything. Five parallel sessions share this tree and several audit findings were already fixed mid-audit (dq_banner, fundamentals restatement journal). If already fixed: mark the AUD item done in the audit doc's Status field with the fixing commit hash, and move on.
- Items marked "finder-only (unverified)" get a deeper verification pass before any code change.
- FIX ADDITIVELY. Never delete or overwrite others' work; put new logic in NEW modules or surgical D80-style patches (append-only EOF + import-test + revert backup). NEVER full-file-overwrite dashboard.py, v2_surfaces.py, lens_registry.py, or shell_skin.py.
- PRESERVE deliberate properties, non-negotiable:
  * Sacred pages untouched: /dash/ratio, /dash/rrg, /dash/compare.
  * Descriptive-only surfaces stay descriptive (credibility, wolfe, harmonic, capture, phase) — no ranking/gating.
  * Guardrail #8 primary-sources-only: never EXTEND Screener paths; AUD items only shrink them.
  * Space rule: compute-on-read; bounded snapshots only (the AUD-04 coverage snapshot is the sanctioned bounded kind).
  * D78 "last-filed-wins + earliest knowable preserved" is a documented decision — journal restatements, don't re-architect.
  * For doc-claim fixes (AUD-15..21): fix the CLAIM to match code truth; any scoring-behavior change needs a Decision-log entry in the same commit.
- GATES after each cluster: `python -m compileall -q src scripts`, module __main__ selftests where they exist, and scripts/chrome_gate.py + the nav gate for any UI-adjacent change. Add a pytest golden-file test with every quant fix (AUD-39 is incremental — grow the suite as you go).

COMMITS
- Commit to main with EXPLICIT paths only (`git add <file> <file>`); NEVER `git add -A` or `git add .` — parallel sessions have staged/untracked work (e.g. src/automation/sast_events.py is not yours).
- Every code commit updates PROJECT_STATE.md in the SAME commit: § Decision log for choices, § open items for closures/discoveries. Reference AUD-nn ids in commit messages.

VPS DEPLOY — bundle, don't dribble
- Batch verified fixes into at most 2-3 deploys. Recipe (PROJECT_STATE / vps-deploy-reality): scp the exact files with LF endings (check for CRLF before scp), then restart hermes-api ONLY after confirming no ingest/backfill writer is running (`fuser /opt/hermes/data/hermes.db`; avoid the 14:00-17:30 IST timer window). Never git-pull on the VPS. NEVER run scripts/setup-news.sh (AUD-28: it regresses live units).
- Unit-file work (AUD-03, AUD-27..31, AUD-93..96): pull the LIVE VPS unit/drop-in contents FIRST (they are the truth), reconcile into git under scripts/, then install + `systemctl daemon-reload`. Do NOT `systemctl start` timers mid-day — Requires= executes the job immediately.
- Surface-first exceptions still apply (report, don't do): paid API spend, deleting/overwriting others' work, DB-destructive ops, publishing beyond the VPS. The AUD-44 historical NULLing pass and any DROP INDEX (AUD-97) count as DB-touching maintenance: take a fresh backup first (AUD-02 must land before them).

SESSION-1 SCOPE TARGET
- AUD-01..AUD-15 (the four P0s + the shown-number-integrity block), plus AUD-23 (results season ~Jul-09 is imminent) and AUD-32 (2-line mount commit) if the owning lanes haven't landed them.
- AUD-01 sequencing: set CHAT_SHARED_SECRET + auth /conversations first (code+env, no restart risk), then bind 127.0.0.1 + ufw in ONE writer-safe maintenance window; verify the Caddy path serves before closing the window. For AUD-34, verify key-only SSH login in a second session before closing the first.
- AUD-06/07 require re-running --backfill-triggers/--backfill-keyprice on the VPS after the code fix — run in background (nohup, per-chunk commits, throttle-aware), and verify a sample symbol before/after.

WRAP
- Update docs/AUDIT-2026-07-02-institutional-review.md: set each completed AUD item's Status to the commit hash(es). Do not rewrite findings.
- Refresh docs/NEXT-SESSION-CARRYFORWARD.md: remaining AUD queue in priority order, newly discovered blockers, and the takeover prompt for the next session (this same prompt, minus completed scope).
- Append a PROJECT_STATE.md § Session log entry (top) with what shipped + hashes. Report any permission prompt that fired as a harness bug (CLAUDE.md #0-bis) — never ask for access.
```

---

## Appendix — full findings ledger

Complete record: every finding from every domain, including P2/P3 and REFUTED items. Verdict column: **C** = CONFIRMED (adversarially verified), **R** = REFUTED, **f/o** = finder-only (not in the P0/P1 verification pass). "→sev" = verifier-corrected severity where it differs.

### perf-trust — Performance post-mortem incl. Trust page (C-)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | /dash/coverage 4.1s per request; 29-38s @ 6-way concurrency; snapshot uncached, bhavcopy_rows scanned twice | coverage_view.py:530 | **C** (P0) | AUD-04 |
| P1 | Lag audit (29,201-row N+1 into research.db) runs 3× per page view | provenance.py:743 | **C** (P1) | AUD-04 |
| P1 | Trust ledger renders "—" for rsband/rs_extras/capture (has_symbol default + silent-except) | provenance.py:897 | **C** (P1) | AUD-05 |
| P1 | /dash/coverage/memo recomputes the whole snapshot (3.1s) | coverage_view.py:658 | **C** (→P2: free once the shared cache lands) | AUD-04 |
| P2 | Single uvicorn worker; one slow endpoint saturates the API | setup-news.sh | f/o | AUD-62 |
| P2 | /dash/screen2 ships 2.2MB HTML | screener_plus.py | f/o | AUD-63 |
| P3 | No HTTP cache validators on any dashboard page | coverage_view.py:735 | f/o | AUD-101 |

### ui-arch — UI architecture, redundancy, information design (C)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P1 | Committed tree 404s two nav-cross-linked pages; mount is an uncommitted VPS patch | v2_surfaces.py:42 | **C** (P1) | AUD-32 |
| P1 | Four-layer runtime monkey-patch chain permanent; one nav generation built-then-discarded per request | shell_skin.py:473 | **C** (→P2: deliberate, defended by gates — still converge) | AUD-66 |
| P1 | Markets sub-nav sprawled to 16 lenses; "planned consolidation abandoned" | lens_registry.py:67 | **R** — cites a superseded design doc; the Ramana-approved 2026-06-29 nav-IA decision deliberately keeps the lenses; /dash/rs-hub IS the stated hierarchy. Residual nav-breadth grooming = P3, no AUD | — |
| P1 | _mep_pill/_mv_adbar duplicated with conflicting color semantics (cockpit vs screener_plus) | screener_plus.py:253 | **C** (→P2: styling divergence, no wrong data) | AUD-67 |
| P2 | cmdk PAGES literal drifted from the registry (9 lenses missing, flat 307 URLs) | ui_kit.py:274 | f/o | AUD-68 |
| P2 | shell_skin byte-duplicates ui_kit geometry | shell_skin.py:191 | f/o | AUD-69 |
| P2 | Per-view private mini design systems; whack-a-mole retinting | shell_skin.py:226 | f/o | AUD-70 |
| P2 | ?-popover/column-control coverage 2 of ~35 pages, two divergent systems | table_controls.py:21 | f/o | AUD-71 |
| P2 | Two full screeners with feature drift, no sunset criterion | screener_plus.py:564 | f/o | AUD-72 |
| P3 | Dead style guide route /dash/ui-kit never mounted | ui_kit.py:414 | f/o | AUD-102 |
| P3 | Unreachable legacy handler bodies + 30+ untracked .bak in the web package | dashboard.py:1244 | f/o | AUD-103 |
| P3 | Four sub-nav renderer implementations coexist | v2_surfaces.py:349 | f/o | AUD-104 |

### data-eng — Ingestion pipelines (B-)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | credit_ratings backfill holds one write txn across all chunk fetches (a4f1c21 class) | credit_ratings.py:341 | **C** (→P1: tolerant init prevents the 000 crash-loop; starvation+rollback remain) | AUD-24 |
| P1 | Revised insider filings create a second event; promoter flow double-counted | insider_events.py:356 | **C** (P1) | AUD-08 |
| P1 | fundamentals_xbrl: no resume table, no breaker, gate fan-out can't survive results season | fundamentals_xbrl.py:734 | **C** (P1) | AUD-23 |
| P1 | bhavcopy marks a date done even when inserts fail; counts lie | bhavcopy.py:500 | **C** (P1) | AUD-13 |
| P1 | data_quality: no liveness checks for XBRL/fno_oi/concalls/shareholding | data_quality.py:316 | **C** (P1; actual line 349) | AUD-25 |
| P2 | Cross-run SA/CONSO replace corrupts series nature | fundamentals_xbrl.py:571 | f/o | AUD-50 |
| P2 | screener.py not frozen: scheduled news runs still trigger live scrapes | news_feed.py:479 | f/o (api-src twin CONFIRMED ↓P2) | AUD-48 |
| P2 | bhavcopy can't distinguish NSE block from holiday (class fixed only in fno_oi) | bhavcopy.py:101 | f/o (api-src twin CONFIRMED P1) | AUD-14 |
| P2 | capital_allocation batch holds the write txn for the whole universe pass | capital_allocation.py:449 | f/o | AUD-24 |
| P2 | Continuity-gate verdicts cached forever; no re-arbitration or scaling re-check | fundamentals_xbrl.py:516 | f/o | AUD-51 |
| P3 | insider gg transaction_dt fallback stores raw unparsed date strings | insider_events.py:592 | f/o | AUD-105 |
| P3 | _parse_nse_dt KeyError aborts the whole listing on a bad month token | fundamentals_xbrl.py:103 | f/o | AUD-106 |

### quant — Calculation schemas & correctness (C+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | QG constants drift: doc/SKILL 240/144 vs code 252/151.2 | scoring.py:47 | **C** (→P1: runtime math is right; canon-doc integrity) | AUD-15 |
| P1 | Ensemble deviates from §2: LOWVOL_MOM enters unranked (~30% under-weight) | momentum_scan.py:93 | **C** (P1) | AUD-10 |
| P1 | Negative PE scores maximum cheapness in the Quality Gate | scoring.py:189 | **C** (P1; ~27 pts after the 0.70× unverified factor, not 32) | AUD-09 |
| P1 | Corp-action fallback rescales history on genuine >30% crashes | adjust.py:64 | **C** (P1) | AUD-11 |
| P1 | D31 zones / D44 key prices / hot-day averages on RAW closes | signals.py:494 | **C** (P1; PROJECT_STATE D36 lists it as known limitation) | AUD-06 |
| P1 | Backfill vs nightly hot-day definition mismatch (22/22 uncapped vs 15/22 capped) | signals.py:903 | **C** (P1) | AUD-07 |
| P1 | Historical rs_rank survivorship-biased (current list applied to all dates) | stock_rs.py:73 | f/o | AUD-12 |
| P1 | Weights doc covers ~30% of live constants | calculations-and-weights.md:1 | f/o | AUD-45 |
| P2 | Leaders/conviction join stock and index states from different dates | stock_rs.py:494 | f/o | AUD-64 |
| P2 | Level-MA tolerates 50% missing data; ratio-MA requires full window | index_signals.py:108 | f/o | AUD-65 |
| P3 | Wilder RSI returns 100 on zero-variance series | rrg.py:123 | f/o | AUD-107 |

### inst-dd — Institutional due-diligence lens (C+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | Restatements silently rewrite history; no restatement log populated; kill-switch #4 can never fire | fundamentals_xbrl.py:572 | **R** — fixed at HEAD be7826a: write_rows journals into fundamentals_restatements (selftest'd); kill-switch #4 reads it and surfaces via dq_banner; last-filed-wins is documented D78. Residuals (→P2): single-version rows read at original knowable_at; shareholding_xbrl lacks the journal → AUD-47 | AUD-47 (residual) |
| P1 | Kill-switch battery write-only — no alert, surface, or suspension consumes it | data_quality.py:372 | **R** — dq_banner.py (be7826a) consumes last_run() and injects WARN/CRIT strips site-wide; finder's grep was stale. Residual (→P3): no Telegram push → folded into AUD-26 | AUD-26 (residual) |
| P1 | Validation memo asserts nonexistent enforcement (§4 beta/sector limits "live by construction") | validation-memo.md:88 | **C** (P1) | AUD-19 |
| P1 | Replication stack bypasses the provenance PIT layer (gates on leaky modeled report_date) | attribution.py:69 | **C** (P1) | AUD-22 |
| P1 | Replay-the-tape claims "actually filed" dates that are uniform +90d models; winner-only heroes | replay-the-tape.html:218 | **C** (P1) | AUD-18 |
| P2 | Benchmark is the Nifty-500 price index, not total return | metrics.py:80 | f/o | AUD-58 |
| P2 | Kill-switches #1 (WML) and #3 (rank-IC) unbuilt — no live-decay detection | validation-memo.md:89 | f/o | AUD-59 |
| P2 | No versioned methodology changelog or restatement policy doc | calculations-and-weights.md:110 | f/o | AUD-60 |
| P2 | Single-VPS SQLite model with no documented SLA/DR story | provenance.py:71 | f/o | AUD-61 |
| P3 | Universe-drift window mislabeled (25 snapshots, not one month) | data_quality.py:302 | f/o | AUD-109 |

### api-src — External data acquisition (C+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | Data-quality/liveness CRITICALs never reach the operator — no paging path | data_quality.py:371 | **C** (→P1: dq_banner surfaces pull-side; push path genuinely absent) | AUD-26 |
| P0 | Concall-capture timer invokes CLI flags that don't exist — capture live-broken | hermes-concall-capture.service:16 | **C** (P0) | AUD-03 |
| P1 | Live scheduled Screener.in call paths despite Guardrail #8 "frozen" | news_feed.py:479 | **C** (→P2: documented transitional exception — still shrink it) | AUD-48 |
| P1 | Throttle recorded as holiday in bhavcopy + 5 siblings; run_recent never re-attempts | bhavcopy.py:101 | **C** (P1) | AUD-14 |
| P1 | Feed-liveness covers 4 of ~12 feeds; regime guard undated | data_quality.py:316 | **C** (P1) | AUD-25 |
| P1 | Nightly ingest chain exists only as VPS-local drop-ins | mep-strategy-design.md:65 | **C** (P1) | AUD-27 |
| P1 | equity_list replaced wholesale with no minimum-row sanity | equity_list.py:81 | f/o | AUD-43 |
| P2 | Deals feed: current-day-only, once daily, no retry — failed run = permanent loss | deals.py:86 | f/o | AUD-53 |
| P2 | NSE anti-bot session copy-pasted 4× (now 5×), drifting UAs, no 401 re-warm | insider_events.py:444 | f/o (hygiene twin CONFIRMED ↓P2) | AUD-52 |
| P2 | No retry/backoff/conditional GET; fundamentals_xbrl re-fetches whole window nightly | fundamentals_xbrl.py:645 | f/o | AUD-23 |
| P3 | feedparser.parse(url) with no timeout in the scheduled news job | news_feed.py:68 | f/o | AUD-110 |

### db-schema — Database schema & data organization (C+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | No backup/DR for the 16.2GB production DB | download-from-vps.bat | **C** (verifier: →P1 "durability gap, manual escape hatch"; sec-ops twin CONFIRMED P0 — program carries it at P0) | AUD-02 |
| P1 | mep_signals + cpr_signals full derivable history (~4.3GB) vs the space rule | db.py:333 | **R** — full history IS used (mep_overlay/cpr_overlay chart overlays under D57 "charts load FULL history"); materialization is decision-logged (CPR-A4/A5, D53/D62/D65, Guardrail #6); the 2026-07-02 space rule is prospective. Residual index-overlap → AUD-97 | — |
| P1 | bhavcopy_rows.raw_json ≈3GB write-only, zero readers | db.py:132 | **C** (P1; raw-file archive on disk satisfies Guardrail #6) | AUD-44 |
| P2 | ~550MB prefix-redundant/useless indexes | db.py:323 | f/o | AUD-97 |
| P2 | Planner stats for exactly one table; no ANALYZE/PRAGMA optimize | db.py:982 | f/o | AUD-98 |
| P2 | DDL fragmented across 40+ modules; three tables defined twice | fno_oi.py:255 | f/o | AUD-99 |
| P2 | Parallel fundamentals truths: live-scraped snapshot still feeds web pages | dashboard.py:5796 | f/o | AUD-49 |
| P2 | Dead schema in prod: 4 empty MTF tables, signal_events, ignition_* in the wrong DB | db.py:491 | f/o | AUD-100 |
| P3 | Tenant credentials co-located in the 16GB analytics file | api/v1/schema.py:17 | f/o | AUD-111 |
| P3 | No retention/pruning/maintenance policy for append-forever tables | PROJECT_STATE.md | f/o | AUD-112 |

### linkage — Index↔stock intelligence (C)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | Sector drill-down pages never mounted — cycle-clock drill and early-signals feed 404 | v2_surfaces.py:42 | **R** — live VPS serves both routes via an uncommitted mount; nothing 404s today, and the gap is already carry-forward queue #2. Residual git-capture debt (→P2) carried by AUD-32 (ui-arch twin CONFIRMED) | AUD-32 |
| P0 | Index names case-broken in momentum pane — every divergence-board sector link renders empty | momentum_pane.py:219 | **C** (→P1: board works, pane fails safe, data reachable via /dash/rrg) | AUD-33 |
| P1 | Stock dossier: zero sector-state context, no link to any index surface | dashboard.py:6244 | **C** (P1) | AUD-41 |
| P1 | Pat can't answer cross-level questions (no sector superlative resolver) | understand.py:386 | **C** (P1; fix needs index_name→primary_sector mapping) | AUD-42 |
| P1 | Screeners expose no rotation-phase columns | screener_plus.py:611 | **C** (→P2: the join is reachable on /dash/rotation — composability gap) | AUD-73 |
| P1 | Index-level events never fan out — no sector-phase alert rule; digest news-only | dashboard.py:3825 | **C** (→P2: missing feature with pull-surface workaround) | AUD-74 |
| P2 | Capture-map dots not clickable; no constituent path | capture_map.py:119 | f/o | AUD-75 |
| P2 | Home cockpit missing the "just turned today" feed | cockpit.py:692 | f/o | AUD-76 |
| P2 | Stock's own rs_phase hidden on dossier and Pat card | pat/flows.py:790 | f/o | AUD-77 |
| P3 | RS-hub preview chips are dead text | rs_section.py:118 | f/o | AUD-113 |

### hygiene — Code quality, dead weight, repo hygiene (C+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P1 | Zero automated tests on the computational core; gates are render-level | regression_sweep.sh:9 | **C** (P1) | AUD-39 |
| P1 | dashboard.py 8,177-line monolith circularly coupled to cockpit.py | dashboard.py:1149 | **C** (→P2: decision-logged freeze/new-module mitigation works; structural debt) | AUD-78 |
| P1 | NSE session bootstrap copy-pasted 4+ (now 5 incl. untracked sast_events.py) | fundamentals_xbrl.py:77 | **C** (→P2: consolidation debt, nothing wrong today) | AUD-52 |
| P2 | 41 except-Exception-pass sites; pipelines silently shrink their universe | cci_pipeline.py:52 | f/o | AUD-79 |
| P2 | ~1,150 lines of orphan modules incl. a route page with zero mounts | early_signals.py:1 | f/o | AUD-80 / AUD-32 |
| P2 | No .gitattributes; CRLF tree feeds scp deploy to Linux | deploy | f/o | AUD-81 |
| P2 | Dead pins sqlalchemy/structlog; no py3.10 syntax gate | requirements.txt:27 | f/o | AUD-82 |
| P2 | 120 .bak revert-backups with no retention rule | src/, scripts/ | f/o | AUD-83 |
| P2 | 20 copies of _esc; duplicated _num; 6 trade-dates reimplementations | ui_kit.py:45 | f/o | AUD-84 |
| P3 | Stale one-off scripts + dormant code-review stack in scripts/ | scripts/ | f/o | AUD-114 |
| P3 | Duplicate kickstart doc; 38 tracked codex-bridge transcripts (hunk_* already cleaned — do not chase) | NEXT_SESSION_KICKSTART.md | f/o | AUD-115 |

### sec-ops — Security & operations posture (F)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | Dashboard + /chat + /conversations publicly reachable, unauthenticated, 0.0.0.0:8000, no firewall | main.py:34 | **C** (P0) | AUD-01 |
| P0 | No off-box backup of the only copy of the 16GB DB | full-backfill.sh | **C** (P0) | AUD-02 |
| P1 | systemd units run as root with zero sandboxing | setup-news.sh | **C** (P1) | AUD-35 |
| P1 | SSH allows root password login; no fail2ban | vps-bootstrap.sh:60 | **C** (P1; finder's file anchor wrong, claim re-measured right) | AUD-34 |
| P1 | /chat credit-spend endpoint unauthenticated (CHAT_SHARED_SECRET unset) | main.py:98 | **C** (P1; deferral's own "unless internet-exposed" carve-out is met) | AUD-01 |
| P2 | /conversations leaks Telegram IDs + message content unauthenticated | main.py:111 | f/o (telegram twin CONFIRMED P1) | AUD-01 |
| P2 | No log rotation for /var/log/hermes-*.log | setup-news.sh | f/o | AUD-90 |
| P3 | Zero swap on a 16GB box hosting a 16GB DB | full-backfill.sh | f/o | AUD-108 |

### telegram-assistant — Bot + conversational LLM layer (D)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | /conversations GET routes unauthenticated — transcript + PII exfiltration | main.py:111 | **C** (→P1: single-tenant data, reachability proxy-dependent; unauth PII read + open DELETE real) | AUD-01 |
| P0 | /chat bypasses the Telegram allowlist and can select Sonnet; open by default | main.py:97 | **C** (P0: port publicly exposed, LAN-only premise false) | AUD-01 |
| P1 | No per-user/per-day token spend ceiling anywhere | chat.py:160 | **R** — $10/mo hard cap at console.anthropic.com (PROJECT_STATE:168) bounds spend; layered mitigations (allowlist, forced Haiku, caching) deliberate. Residual in-app counter = P3, no AUD | — |
| P2 | No global Telegram error handler; update.message deref unguarded | telegram_bot.py:2211 | f/o | AUD-91 |
| P2 | Raw exception text leaked to users in error replies | chat.py:171 | f/o | AUD-36 |
| P2 | Conversations persist PII indefinitely; /reset never deletes | conversations.py:15 | f/o | AUD-92 |

### pat-nl-explainability — Pat NL engine + glossary correctness (C+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | Glossary describes a financials-adapted pt14 scoring that doesn't exist in code | pat/glossary.py:710 | **C** (→P1: scores unchanged; materially false explanation on a trust surface) | AUD-16 |
| P1 | compare/why/trend silently take the first fuzzy symbol candidate | pat/web.py:1418 | **C** (P1) | AUD-17 |
| P1 | Frozen Screener fundamentals answered with no as-of date | pat/web.py:2255 | **C** (P1) | AUD-21 |
| P1 | /dash/glossary leaks thresholds/weights vs its own promise | metrics-glossary.md:47 | **C** (P1) | AUD-20 |
| P1 | Eval battery wired to no gate/timer/CI | pat/eval_set.py:539 | **C** (P1) | AUD-40 |
| P2 | Two glossary sources of truth with live factual drift | pat/glossary.py:220 | f/o | AUD-85 |
| P2 | md parser drops nested sub-bullets → vacuous popovers | src/web/glossary.py:67 | f/o | AUD-86 |
| P2 | Working-notes voice on client-facing surfaces | metrics-glossary.md:42 | f/o | AUD-87 |
| P2 | Pat mis-states its own data lineage (live Screener pull; no XBRL story) | pat/glossary.py:640 | f/o | AUD-88 |
| P2 | ★ glyph has two undocumented, conflicting meanings | screener_plus.py:663 | f/o | AUD-89 |
| P3 | Known-failing eval cases left failing in the degraded path | understand.py:405 | f/o | AUD-116 |

### timer-topology — systemd scheduling across 22 jobs (D+)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P1 | Core nightly pipeline only as unversioned VPS files (13-step chain, pt14batch, deals) | setup-news.sh:68 | **C** (P1) | AUD-27 |
| P1 | No encoded ordering anywhere; stale-fed-as-fresh downstream | hermes-capital-allocation.timer:5 | **C** (P1) | AUD-29 |
| P1 | Persistent catch-up storm on restart/boot; observed live with api flapping | setup-news.sh:226 | **C** (P1) | AUD-30 |
| P1 | Hung job blocks all future runs: infinite timeout, no RuntimeMaxSec; comment misdiagnosis | hermes-concall-capture.service:10 | **C** (P1) | AUD-31 |
| P1 | Documented deploy script would regress live units; bidirectional drift | setup-news.sh:145 | **C** (P1; reverse-drift half overstated — code-review installs only via manual script, dormancy decided) | AUD-28 |
| P2 | Same-second writer collision: insider-ingest + pt14batch @ 15:30 on hermes.db | hermes-insider-ingest.timer:5 | f/o | AUD-93 |
| P2 | Zero resource containment on a zero-swap box shared with uvicorn | hermes-momentum-scan.service:10 | f/o | AUD-94 |
| P2 | Requires=<own service> in 9+ timers — starting a timer executes the job | hermes-wolfe-scan.timer:3 | f/o | AUD-95 |
| P2 | All 22 schedules naked wall-times; correctness rests on Etc/UTC | hermes-wolfe-scan.timer:10 | f/o | AUD-96 |
| P3 | Weekend/holiday mismatch: daily jobs re-scan/re-alert on Friday's bars | hermes-tracker-alerts.timer:8 | f/o | AUD-117 |

### v1-api-contract — /v1 public API + SDK + MCP (C)

| Sev | Finding | File | Verdict | AUD |
|---|---|---|---|---|
| P0 | /v1/coverage + /v1/meta/health run uncached full-DB scans; "can hang the single-worker API" | api/v1/routes.py:51 | **R** — mechanism wrong twice: sync-def routes run in the ~40-thread anyio pool (sqlite releases the GIL), and measured snapshot = 3.07s, not tens of seconds. Residual (→P2): a 3s uncached health probe deserves the AUD-04 TTL cache | AUD-04 (residual) |
| P1 | PIT not on the external contract: 5 of 6 endpoints latest-row-only | routes.py:78 | **C** (P1; envelope does stamp _meta.as_of — stamped, not queryable) | AUD-38 |
| P1 | attention limit=-1 bypasses the hard cap; MCP int() crash | routes.py:105 | **C** (→P2: one day's events, not the whole table; authed scope) | AUD-54 |
| P1 | Catch-all 500 handler leaks raw internal exception text | api/v1/__init__.py:66 | **C** (P1) | AUD-36 |
| P1 | Metering under-records: 500s skipped, bytes_out=0, failures swallowed | api/v1/__init__.py:47 | **C** (P1) | AUD-37 |
| P1 | Every authenticated read performs 3-4 write txns on the shared SQLite | api/v1/auth.py:88 | f/o | AUD-46 |
| P2 | No response models/versioning; shape already broke inside "v1.0" | routes.py:79 | f/o | AUD-55 |
| P2 | Selftests wired to nothing; _teardown deletes rows from the append-only billing log | api/v1/selftest.py:11 | f/o | AUD-56 |
| P2 | Stale gating docs on both /v1 entry points; invalid as_of swallowed → 200 | routes.py:6 | f/o | AUD-57 |

---

*End of record. Fix sessions: update Status fields and the carry-forward queue; never rewrite the findings or verdicts above.*

---

## Solution coherence, sequencing & integration (validation pass — 2026-07-03)

> **What this pass is.** Pass-1 verified the FINDINGS. This pass-2 verified the 117 PROPOSED FIXES against the live tree/VPS as a *set*: are they synchronized, logical, feasible, and a comfortable fit? Append-only; the findings and verdicts above are untouched. Where a fix is already shipped, marked BLOCKED/CONFLICT/REWORK, or must be re-sequenced, the compliant reformulation is given here — the fix session executes from THIS section, honouring **kickstart-pick-verify** on every pick before spending effort.

### Overall verdict

The fix set is **coherent and a comfortable fit** — no fix contradicts the product's doctrine, and ~85% compose as independent surgical patches. The residual risk is **operational, not architectural**, and concentrates in five places: (1) the audit doc still marks **AUD-03, AUD-23, AUD-24, AUD-32 OPEN but all four already shipped at HEAD** (cfcd1c7 / 911d020 / 16037b2 / a24cf23) — a naive fix session would double-apply them; kickstart-verify first. (2) A **DB-destructive cluster** (AUD-44/97/92/100, plus the 06/07 and rank backfills) must all wait behind a landed, restore-tested **AUD-02** — the prompt tied only 44/97 to it; 92/100 and the backfills are added here. (3) **AUD-27** (pull live VPS units into git) gates every unit edit, or edits regress the VPS-only 13-step chain. (4) **--workers 2 (AUD-62)** is mutually exclusive with the in-process counters of AUD-46/37/04 — keep one worker unless the counter moves to shared store. (5) Five hot files (dashboard.py, screener_plus.py, fundamentals_xbrl.py, bhavcopy.py, data_quality.py) each take multiple co-located edits that MUST merge into one patch per file to survive the shared 5-session tree. Two genuine **CONFLICTs** exist (AUD-72↔73 on the classic screener; AUD-96 timezone) and are resolved below. Three **BLOCKERs** are feasibility-real (AUD-11 caller signatures, AUD-58 TRI missing, AUD-42 index-class routing) with buildable reformulations. Net: safe to execute in the batches below, gate-by-gate.

### Execution DAG / session batches

Enabler-first edges (hard must-precede): **AUD-27 → all unit edits** · **AUD-02 → all DB-destructive (44/97/92/100) + all backfills (06/07, rank)** · **AUD-39 harness → all quant fixes (06/07/09/10/11/15)** · **AUD-26 → AUD-25/59** · **AUD-04 → AUD-101/62** · **AUD-01 phase-1 → phase-2 → AUD-92** · **AUD-52 LAST after 23/24/14/53** · **AUD-32 → 33-fanout/75/80** (but 32 already shipped) · **AUD-66 cut-over LAST after 69/70/71/104** · **AUD-78 dashboard carve-out LAST after all in-place dashboard AUDs**.

| Batch | Theme | AUD ids (intra-batch order) | Gate before next batch |
|---|---|---|---|
| **B0** | Verify-and-skip (stale-OPEN) | 03, 23, 24, 32 — **kickstart-pick-verify at HEAD; mark DONE, do NOT re-apply** | git log confirms cfcd1c7/911d020/16037b2/a24cf23 present; Status set to DONE |
| **B1** | Security + backup keystone | **01a** (secret+auth /conversations, no restart) → **34** (SSH key, verify-in-2nd-session) → **01b** (bind 127.0.0.1 + ufw, writer-safe window) → **02** (backup + **restore-tested**) | Restore script proven; site still served via Caddy; SSH key login confirmed before old session closed |
| **B2** | Timer truth-capture + unit hardening | **27** (pull live .conf into git) → **28** (regen setup-news from truth) → **29/30/31/35/90/93/94/95/96** (one edit per unit, layered on 27 base) | `daemon-reload` clean; drift-check repo==VPS; TZ assertion holds (see AUD-96 resolution); each unit restarted writer-safe |
| **B3** | Quant harness + fixes + backfill | **39** (pytest + fixture DB + gate-0) → **09** → **10** → **12** → **64/65** → **06+07** (merged, one helper) → **11** (caller-widened) → **15+45** (canonical doc) → **ONE background backfill** (--backfill-triggers/-keyprice + rank, per-chunk commits) | Every quant fix landed WITH its golden-file test; backfill ran post-AUD-02; Decision-log entry per 09/10/11 |
| **B4** | Trust-text honesty | **16/18/20** (downgrade claims) → **85/87/89** (glossary md, merged) → **86** (parser+lint, AFTER md) → **19/21/88/40/57** | /dash/glossary re-renders clean; no leaked thresholds; lint gates corrected text |
| **B5** | Fetch discipline + freshness + alerting | **26** (push path + OnFailure=) → **14+13+43+53** (per-file merges) → **25+109** (data_quality, merged) → **47/50/51/106** (fundamentals/shp, merged) → **08/48/110** → **52** (shared nse_http LAST, absorb breakers) → **59** | Deals/SHP feeds page on stall; nse_http migration preserves each caller's abort semantics; **AUD-23 already live — do not block on 52** |
| **B6** | Linkage + UI cluster | (32 already live) **33** (COLLATE + fanout) → **41+77** (dossier, ONE patch) → **42** (index-class routing) → **74/75** → **67** (glyph module) → **73/89/71/63** (screener_plus, ordered) → **69/70/71/104 → 66** (chrome cut-over LAST) → **68+104** (ui_kit, one edit) → **80** (orphan rm) → **all-dashboard-in-place → 78** (carve-out LAST) → **103** | chrome_gate.py PASS after each dashboard/shell edit; no moving-anchor merges; import-test per D80 patch |
| **B7** | DB-core maintenance + /v1 + P3-last | **99+100** (SCHEMA_BASE, merged) → **97** (DROP INDEX, post-02) → **44** (stop-populate now; NULLing pass post-02) → **92** (purge, post-01) → **36+37** (v1 __init__) → **38+54+57** (routes.py) → **46** (auth batching) → **04** (coverage snapshot) → **101** (ETag off snapshot) → **62** (workers — ONLY if counters shared) → **98** (optimize to weekly, NOT get_conn) → **111** (app.db split, re-points 02/46/92) → **55/56/116/117/91** | EXPLAIN-QUERY-PLAN verified before DROP; backup fresh before each destructive pass; workers gate honoured |

### Per-file merge plans (files touched by >1 AUD)

| File | AUDs | Merge plan + order |
|---|---|---|
| `src/web/dashboard.py` | 41,72,73,74,77,78,103 + dossier | In-place FIRST: 103 (rm dead dash_scan) · 41+77 as ONE dossier patch (sector tile + phase pill together) · 72/73 per classic-screener CONFLICT rule · 74 (_ALERT_DEFS, separate region). **78 carve-out LAST** so no anchor moves under the others. |
| `src/web/screener_plus.py` | 63,67,71,73,89 | 67 first (extract glyph module) → 73 (columns) → 89 (★ rename) → 71 (popovers) → 63 (pagination LAST, reflows most). Different functions; ordered, one session. |
| `src/automation/fundamentals_xbrl.py` | 23✓,50,51,106 | 23 already shipped — 50/51/106 are surgical patches INTO the landed loop: 106 (_MON.get one-liner) + 50 (SA/CONSO write guard) + 51 (age FAIL verdicts) as ONE edit; do not re-refactor. |
| `src/automation/bhavcopy.py` | 13,14,43★,44 | 13 (reconcile insert/skip counts) + 14 (run_recent re-scan lost weekdays, RetryableFetchError) + 44 (stop populating raw_json). One edit, separate funcs. NULLing pass is separate DB-destructive step (post-02). ★43 is equity_list.py, merge there. |
| `src/automation/data_quality.py` | 25,26,109 | 25 (declarative feed_freshness list + regime date-guard, add deals/SHP rows) + 109 (universe_drift 30-day window) + 26 (push path — orthogonal delivery). One edit. |
| `src/web/v2_surfaces.py` + `lens_registry.py` | 32✓,66 | 32 ALREADY at a24cf23 — skip. 66 deletes _wrapped_nav (276-324) as the final chrome cut-over, after 69/70/71/104. |
| `src/web/shell_skin.py` | 66,69,70 | 69 (geometry→tokens) + 70 (per-view palettes) land on current monkeypatch arch FIRST; 66 deletes the header regex (464-478) LAST. |
| `src/web/ui_kit.py` | 68,104 | ONE edit: import lens_registry + nested_path once, generate PAGES (68) AND subnav (104) from it. dashboard._SUBNAV deletion waits for 66. |
| `src/web/table_controls.py` | 71,66 | Extend _PAGES (71) BEFORE 66 cut-over; 66 MUST preserve/re-home the install() _shell hook, not remove it. |
| `docs/metrics-glossary.md` | 20,85,87,89 | ONE editorial pass: strip leaked formulas (20, →calculations-and-weights.md) + fix drifted strings (85) + neutralize voice (87) + split ★ key (89). Lines ~47 collide — do together. |
| `docs/calculations-and-weights.md` | 10,15,45 | ONE doc commit: 15 (§4 QG 252/151.2) + 10 (§2 momentum canonical, kill stale note) + 45 (governance sections, rs_rank 0.6/0.4). Different sections but same file — clobber risk if split. |
| `src/automation/signals.py` | 06,07 | ONE change: extract 07's shared hot-day helper switched to ADJUSTED closes (06), fix nightly (:637) + backfill (:897-908) loops together, then ONE backfill. char_adj already available at :585/:817. |
| `src/api/v1/__init__.py` | 36,37 | ONE pass: 37 (try/finally _observe, meter the 500 path) + 36 (sanitize str(exc) leak). 37's finally ensures 36's sanitized 500 still meters. |
| `src/api/v1/routes.py` | 38,54,57 | ONE pass: 38 (as_of on credibility, period_label→date) + 54 (cap attention limit) + 57 (rewrite stale docstring to match new signatures). |
| `src/core/db.py` | 97,99,100 | 99 (delete duplicate module DDL) + 100 (dead MTF/ignition/signal_events) as one SCHEMA_BASE pass; 97 removes the 5 dropped indexes from SCHEMA_BASE (live DROP is separate post-02 step). |
| `src/automation/equity_list.py` | 14,43 | ONE edit: RetryableFetchError port (14) + <90%-of-existing refuse-replace guard (43). |
| `src/automation/news_feed.py` | 48,110 | ONE edit: 48 (cache-only score_symbol, SHRINK) + 110 (feedparser timeout via requests.get(timeout=15)). |

### Conflicts & guardrail flags — resolved

| # | Items | Flag | Compliant reformulation |
|---|---|---|---|
| C1 | **AUD-72 ↔ 73** | classic-screener CONFLICT | Apply 73's rs_phase + sector-phase LEFT-JOIN columns to **screener_plus.py ONLY** (go-forward path). On the classic path (dashboard.py:1645) honour 72's freeze. If phase is wanted on classic, add it BEFORE declaring the freeze, as the last classic column, same commit. |
| C2 | **AUD-96** | timezone CONFLICT | Box is **Etc/UTC**; OnCalendar minutes are authored as UTC wall-times. **Do NOT naively append `Asia/Kolkata`** (shifts every timer −5.5h, fires pre-close). Use an **installer TZ-assert** (fail deploy unless `timedatectl` == Etc/UTC), OR convert every minute in ONE coordinated edit with AUD-29/93. Default: installer-assert (no minute churn). |
| C3 | **AUD-35 ↔ 90 + all units** | ProtectSystem=strict vs /var/log | ReadWritePaths MUST include **/var/log** (not just /opt/hermes/data) or every `StandardOutput=append:` dark-fails. Decide once with 90: keep file logs + `ReadWritePaths=/var/log` + logrotate (default), OR migrate to journald+SystemMaxUse (then 90 and the /var/log carve-out both dissolve). |
| C4 | **AUD-62 ↔ 46/37/04** | workers vs in-process counters | `--workers 2` doubles the in-process rate counter and breaks metering flush + coverage cache. **Keep workers=1** (default) unless the counter/queue moves to SQLite/Redis first. AUD-46/04/37 are correct AT 1 worker — that is the live config (setup-news.sh:200 has no --workers). |
| C5 | **AUD-98** | PRAGMA optimize in hot path | Do NOT put `PRAGMA optimize` in `get_conn()` (db.py:1291) — it emits ANALYZE writes on the 16GB single-writer, opposing 46/04's write-removal. Move optimize/ANALYZE to the **weekly DQ timer only** (AUD-98's own second clause). |
| C6 | **AUD-52** | nse_http ordering + breaker preservation | Land 52 **LAST**, after 23/24/14/53 (breakers already duplicated across 7 modules, 45 consec_fail refs). The shared client MUST fold in consec_fail + re-warm and **preserve each caller's abort semantics** — not just swap the session factory. Include the untracked `sast_events.py` (note 5). |
| C7 | **AUD-48** | Guardrail #8 SHRINK-only | Cache-only redirect for scheduled news/enrich callers (read fundamentals_asof; concall discovery via concall_bse.py). **Verify it only SHRINKS** — never adds a Screener read; no live fetch on cache-miss. Disclose the frozen exception where shown. |
| C8 | **AUD-49 / 04 / 59** | space-rule (bounded storage) | All compliant: 04 = 1 bounded snapshot row + TTL (nightly, MAX(trade_date)-keyed); 59 = one monitoring row per monthly run; 49 reuses the existing 1-row fundamentals snapshot. **Persist NO new per-date derivable series.** |
| C9 | **AUD-09/10/11** | same-commit Decision-log rule (D78-adjacent) | Each changes SHOWN scoring math → land each WITH a numbered `PROJECT_STATE §Decision-log` entry **in the same commit** + the AUD-39 golden-file test + the canonical constant in calculations-and-weights.md. (Only AUD-15 already states this.) |
| C10 | **AUD-73/74/75/77/41/42** | descriptive-only surfaces | All stay descriptive: rs_phase is a LABEL, capture is "a behaviour track record, never a ranker". Columns/pills/alerts/links surface STATE only. **No rs_phase into any score/default-sort/hard-WHERE gate**; alert wording = "Sector X phase changed A→B" (no buy/sell verb); AUD-42 "strongest" = existing descriptive index-RS ordering, never a novel composite. |

### Blockers (fix-as-written not executable)

| AUD | Status | What must be true / built first |
|---|---|---|
| **AUD-11** | BLOCKED → reformulate | adjust.py is pure; callers (stock_rs.py:104, mep_signals.py:246, cockpit:1544) pass only {close,prev_close}; deliv_qty NULL for pre-2020 rows. **NOT adjust.py-local.** Widen each caller's SELECT + row dict to carry volume/deliv_qty; corroboration falls back to **volume (always present)** when deliv_qty NULL, else zero-the-day. Also adjust today_close/avg_price on the SAME basis as history (AUD-06 REWORK) or gap% stays wrong. Land with AUD-39 test. **CONFIRMED-FEASIBLE once callers widened.** |
| **AUD-58** | BLOCKED → new fetcher | Premise (NSE publishes TRI) true, but **artifact missing**: indexes.py ingests price-index CSV only (no TRI column); index_rows.close_value is price. TRI lives on **niftyindices.com** behind a session/cookie wall. Build a NEW niftyindices.com TRI fetcher (warmup like the deals feed) → store 'Nifty 500 TRI' → re-point metrics.index_series/hurdles. NSE-owned = primary source (no Guardrail-#8 conflict). **Effort M understated — it's a new ingest path, not a column read. CONFIRMED-FEASIBLE as new path.** |
| **AUD-42** | BLOCKED → routing, not mapping | Premise "need index_name→primary_sector map" is half-wrong: stock_signals.primary_sector is ALREADY a sector index_name (stock_rs.py:349, identity join at :508/559/608). Real work = **index-class routing**: for a sector index, bind s.primary_sector=? (identity); for a broad index (Nifty 50/Next 50) join via stock_index_membership (flows.py:678). No new table. **CONFIRMED-FEASIBLE.** |
| **AUD-101** | BLOCKED on AUD-04 | ETag/Cache-Control validators must key off AUD-04's persisted snapshot stamp / MAX(trade_date) — not an uncached 4s compute. Ship 04 first. **CONFIRMED-FEASIBLE after 04.** |
| **AUD-62** | BLOCKED on AUD-04+46 | See C4. Enable only if counters are shared-store OR workers stays 1. **BLOCKED as written (workers=2); CONFIRMED-FEASIBLE deferred.** |
| **AUD-59** | BLOCKED on AUD-26 | Writes to data_quality_runs but "rides AUD-26 alerting" — build after the push path, else another write-only monitor. **CONFIRMED-FEASIBLE after 26.** |
| **AUD-39** | CONFIRMED-FEASIBLE, must be first | No tests/, no conftest, no pytest in requirements. The harness every quant fix must "land with" **does not exist yet** — stand up pytest + fixture DB + gate-0 wiring before/with the first quant fix, else the co-req test is unwritable. |
| **AUD-22** | CONFIRMED-FEASIBLE | fundamentals_asof.py drop-in over the same research.db.fundamentals_history table. Caveat: `.venv-research` on VPS + `_effective_date_map` imports src.automation.provenance → set **PYTHONPATH=/opt/hermes** or it silently falls back to leaky report_date ({} map). |
| **AUD-38** | CONFIRMED-FEASIBLE | credibility_series is a full PIT series; historized as_of serve is a straight SELECT (period_label<=as_of). Resolve period_label→date to satisfy the knowable-date clause. Descriptive-only, no doctrine conflict. |
| **AUD-05** | CONFIRMED-FEASIBLE | rsband/capture/rs_extras all carry numerator + trade_date → COUNT(DISTINCT numerator) override is buildable as written; add the startup selftest asserting non-None n on prod schema. |
| **AUD-08** | CONFIRMED-FEASIBLE (REWORK) | The landed _uid change (shares,value_rs) does NOT implement supersede — a Revised filing still mints a new row. Implement supersede on amendment_flag / latest parsed_at per natural key; orthogonal to _uid. |

### Open decisions (RECOMMENDED DEFAULT so the fix session proceeds without asking)

| Decision | Recommended default |
|---|---|
| AUD-96 timezone: append `Asia/Kolkata` vs installer-assert vs convert-minutes | **Installer TZ-assert** (fail deploy unless Etc/UTC) — zero minute churn, no re-derivation of 29/93. |
| AUD-35/90 logging: file+logrotate vs journald | **Keep file logs + `ReadWritePaths=/var/log` + logrotate** (smallest diff; journald migration is a separate opt-in). |
| AUD-62 workers | **Keep workers=1**; do not enable --workers 2 this program (counters not shared-store). |
| AUD-72/73 phase columns on classic screener | **screener_plus.py only**; freeze classic per 72. |
| AUD-19 memo limit #6 | **Honest doc downgrade** (mark OPEN, same-commit doc rule) over building the nightly beta/sector compute now. |
| AUD-15 canonical QG max: 240 vs 252 | **252 / 151.2** (what executes — align docs/comments/SKILL.md/patearn.py to code, never code to 240). |
| AUD-111 app.db split timing | **P3-LAST**; implement 02/46/92 against current single hermes.db, then 111 re-points them. Do not pre-bake the split. |
| AUD-44 raw_json history NULLing | **Ship stop-populate now; run the one-time NULLing pass only post-AUD-02** (DB-destructive, surface-first). |
| AUD-23 vs AUD-52 (results season ~Jul-09) | **AUD-23 already shipped (911d020)** — no action; if any residual, ship standalone NOW, refactor to nse_http when 52 lands. Do not block on 52. |
| AUD-09 negative-PE credit representation | **raw=0 with verified=True** (NOT raw=-1, which flips to Partial and re-credits the loss-maker). |
