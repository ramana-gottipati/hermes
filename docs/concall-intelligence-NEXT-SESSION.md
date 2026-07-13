# CCI — AUTONOMOUS SESSION-TAKEOVER KICKSTART

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the concall-intelligence follow-ups ship + fold into PROJECT_STATE. Registered in `docs/DOC_INDEX.md`.


> **Created** session 28 (2026-06-21/22). **TRANSIENT** run-book (per the transient-doc-lifecycle rule):
> the durable record is `docs/concall-intelligence-design.md` + `docs/concall-intelligence-debate.md` +
> PROJECT_STATE. **Retire when** P1–P8 below are shipped and folded into PROJECT_STATE.
> **This file is written so an AUTONOMOUS model can continue one prompt at a time, no further acceptances.**

## 0. BOOT ORDER
1. This file. 2. `docs/concall-intelligence-design.md` (canonical spec, esp. §13 the debate inversion).
3. `docs/concall-intelligence-debate.md` (the ranked improvements + India must-dos). 4. Memory note
`concall-intelligence.md`. 5. `git log --oneline -10`.

## 1. WHAT CCI IS (one line)
A per-company **management-credibility / guidance-accuracy** strategy from earnings concalls: capture every
promise → grade it against what actually landed → compound into a credibility **score + rank** + a
**deterioration (avoid) tape**. The qualitative forward layer the explosive-move research (D56) pointed to.

## 2. STATE NOW (session 28) — DEPLOYED + WORKING on the VPS, validated on real data
- **Pipeline proven end-to-end** on real Indian concalls: Screener Concalls → BSE transcript PDF → pypdf
  text → **Gemini extraction** (rich: e.g. IDEA "invest ₹45,000 Cr capex over 3 yrs"→45000/Rs_cr;
  behaviour discriminates Nov'25 cred 40/evasion 60 vs May'26 70/30; red-flags with verbatim evidence) →
  **inverted scorer** → `/dash/concalls` UI.
- **Deployed to VPS** (`scp` + `systemctl restart hermes-api`): db.py (9 CCI tables incl. concall_coverage),
  llm_router.py (call_extractor + Gemini json_mode), concalls.py, concall_extract.py, concall_scores.py,
  cci_normalize.py, concall_veto.py, dashboard.py, resources/cci/golden_set.csv.
- **UI live:** `/dash/concalls` (⚠ Avoid tape + ★ Credibility leaders views, data-first table.dt) + a
  "Mgmt Credibility · CCI" card on `/dash/strategies`. Per-stock dossier + screener column-group + Pat = TODO (P5).
- **Scorer INVERTED + validated** (4-case synthetic + real): forensic veto first (pledge≥20% / pt14
  hard-disqualifiers, cash-flow sector-suppressed) → tier D/AVOID; track-record primary; UNPROVEN ceiling 60;
  deterioration_score; tone only as per-speaker deviation; **build-failing price firewall** in concall_scores.
- **Pilot data so far:** RELIANCE/IDEA/BAJFINANCE corpus (6 transcripts); 3 extracted (IDEA May'26, IDEA
  Nov'25, RELIANCE Apr'26); BAJFINANCE ×2 pending (quota). concall_scores: RELIANCE B/60, IDEA C/52.7.

## 2c. UPDATE (session 28 cont.) — P1–P4 NOW BUILT, DEPLOYED, VALIDATED
The free backend chain is done and live on the VPS (run via `cci_pipeline`):
- **P1 `concall_results.py`** — Screener quarterly table → `concall_results` (rev/EBITDA/OPM%/PAT/EPS + QoQ/YoY)
  + negative-EBITDA ledger. Keyed by (fy,quarter). 13 q/name ingested for RELIANCE/IDEA/BAJFINANCE.
- **P2 `concall_settle.py`** — resolves OPEN promises vs actuals; LEVEL (rev ₹cr), growth-MAGNITUDE (rev %),
  margin (pp), else directional YoY sign-match; multi-year/non-P&L → ONGOING; **no look-ahead** (settles only
  when the resolving quarter is reported). `_infer_metric` recovers metric from claim_text when the LLM mistyped
  statement_type as 'other'. Validated: 0 false settlements; 4 ONGOING for IDEA.
- **P3 `concall_diff.py`** — consecutive-period promise diff → DETERMINISTIC `guidance_walkback` /
  `promise_quietly_dropped` (tagged `model_version='cci-diff-v1'`, re-run-safe). Restricted to comparable,
  same-unit statement types (NOT 'other'). Validated on IDEA: 1 clean flag (capex guidance dropped Nov'25→May'26).
- **P4 `cci_pipeline.py`** — runner: `ingest→results→extract→settle→diff→score`, D59 ordering by construction,
  `--max-calls` quota guard. `--all` runs the free chain over ingested symbols.
- Scorer (measurable-only, D61) consumes these: IDEA tier B (quantif 94.4%, deter 2, **DOWN**) vs RELIANCE
  (76.9%, 0, **UP**); both `unproven` (ga NULL) until promises settle.

**Known issues to refine (not blockers):** (1) **settlement coverage is thin** — many revenue/margin promises
are LLM-typed 'other' and/or have horizons not yet due, so few grade today; improve `_infer_metric` + verify the
horizon→resolving-quarter mapping on more names. (2) **EBITDA/OPM is meaningless for banks/NBFCs** (BAJFINANCE) —
the sector rubric (debate #10) is still deferred; don't trust `concall_ebitda_watch`/margin for lenders yet.
(3) IDEA Mar-2026 PAT 51,970cr is an exceptional-item artifact (PAT level isn't ranked, so harmless).
**REMAINING: P0-DATA backfill, P5 UI follow-ups, P6 gates (the decision), P7 schedule, P8 backtest.**

## 2d. UPDATE (session 29, 2026-06-22) — REFINEMENTS + P5 + P6 + P7 ALL SHIPPED & DEPLOYED
The whole free/code chain is done. **What's left is DATA** — the Gemini free tier (20/day) is
the only remaining gate, and a cron now drains it autonomously.
- **REFINE (deployed, validated):** `concall_results.py` — banks/NBFCs label the top line **"Revenue"**
  (not "Sales") and report **Financing Profit/Margin** (not Operating/OPM); the parser now (1) falls back
  to the `revenue` row so lender **revenue is captured** (BAJFINANCE was NULL → now ₹21,606cr, revYoY 18.1%)
  and (2) detects financials (`startswith("financing")`) → **EBITDA/margin forced NULL + never on the
  neg-EBITDA ledger** (debate #7; EBITDA is meaningless for lenders). `concall_settle.py` — added
  `_implied_growth_pct` ("double-digit"→10% / "high single"→8% / "mid single"→5%) so a vague-but-quantifiable
  promise grades on its floor (turns a falsely-lenient directional MET into a correct MISS); +"turnover" kw.
  `concall_extract.py` + `cci_pipeline.py` — new **`--oldest`** flag (drain OLDEST concalls first; the right
  backfill order — settles soonest + reaches the blowups' pre-collapse calls).
- **Settlement reality (root cause, recorded):** settlement is thin because **only recent calls are
  extracted** — their fy/next_q promises resolve in FUTURE quarters that don't exist yet (correct no-look-ahead),
  and the blowups' 2017-2019 calls have **no matching `concall_results`** (Screener's quarterly table reaches
  only ~FY2023). The fix is DATA (extract older calls), not logic. The settle logic is correct + deployed.
- **P5 UI (deployed, all 200, no regression):** (a) **per-stock CCI dossier** on `/dash/stock?sym=`
  (`_cci_stock_panel`: ⛔veto banner → measurable verdict chips → **promise ledger** (MET/MISSED/OPEN+Δ) →
  deterioration/red-flag timeline (★=deterministic) → expectation-vs-actual → neg-EBITDA → behaviour axes as
  **"AI read — NOT ranked"** → footnote). Omitted gracefully when a name has no concall data. (b) **CCI
  column-group** in `/dash/screener` (`credibility · cci`: Tier·Fwd·Deter·⛔Veto; toggle chip; 43/43/43 aligned;
  virtualization intact). (c) **Pat NL flows** — `build_credibility_query` / `build_deterioration_query` +
  deterministic routing in `disambiguate.route_extra` ("credibility leaders"→leaders, "deterioration/avoid
  tape/walkback"→avoid; "stocks to avoid" still→kill-list) + render in `web.py` + 5 glossary terms.
- **P6 gates (BUILT, deployed, validated — verdict DATA-GATED):** `research/cci/` (offline `.venv-research`,
  numpy present): `common.py` (read-only, reuses explosive_moves series; T+2 entry, 63td, 60bps,
  survivorship-safe), `gate_guidance_return.py` (A: direction→fwd-return; **runs — 2 obs, correctly INSUFFICIENT**,
  smoke: CGPOWER Aug'17 +2.59%, IDEA Nov'25 +4.73%), `gate_residual_alpha.py` (B: incremental alpha vs
  quality+momentum+PEAD, Newey-West; needs `pip install statsmodels`; runs → insufficient),
  `gate_golden_discrimination.py` (the labelled-blowup avoid-test = P8 essence; runs, shows the full golden set).
  All refuse to fabricate a verdict below `MIN_OBS`.
- **P7 schedule (DEPLOYED, active):** two staggered timers (≤18 Gemini calls/day, never collide):
  **`hermes-concalls.timer`** (Mon-Sat 07:00 UTC) = backfill DRAIN `cci_pipeline --all --extract --oldest
  --no-results --max-calls 18`; **`hermes-concalls-refresh.timer`** (Sun 07:00 UTC) = weekly incremental
  `--pilot --ingest --extract --oldest`. Both in `scripts/setup-news.sh` + created live on the VPS. 07:00 UTC
  ≈ Gemini's PT-midnight quota reset, so each daily drain gets a fresh budget.
- **P0-DATA (corpus DONE; extraction accruing):** ingested the full golden set + compounders (free): blowups
  VAKRANGEE 7 / YESBANK 15 / ZEEL 17 / CGPOWER 9 (delisted DHFL/CCD/RCOM/PCJEWELLER/MANPASAND/BRIGHTCOM have
  no/empty Screener concalls); compounders ASIANPAINT 25 / PIDILITIND 26 / PAGEIND 25 / TITAN 21 / NESTLEIND 4
  + BAJFINANCE — ~154 transcripts queued. Today's free batch hit the daily quota after +1 (CGPOWER Aug 2017,
  a pre-collapse call). **Routing decision (autonomous): the 18/day cron drains the rest oldest-first** (claude.ai
  bulk / paid Gemini stay open to Ramana to accelerate).

### WHAT THE NEXT SESSION ACTUALLY DOES (everything else is built)
1. **Let the cron run / accelerate it.** After ~2 weeks (or a claude.ai/paid-Gemini bulk), ≥40 concalls across
   the golden set will be extracted. Watch `/var/log/hermes-concalls.log`.
2. **Re-run the gates → THE DECISION:** `gate_guidance_return`, then `pip install statsmodels` + `gate_residual_alpha`,
   then `gate_golden_discrimination`. If incremental alpha dies → **merge CCI into pt14, don't ship a standalone book.**
3. **P8 full survivorship backtest** (only if the gates pass) — extend the golden discrimination to the bhav-copy
   universe, point-in-time. Carry CCI as a screen/overlay until it clears.
4. Optional refinements (deferred, not blocking): the sector rubric (debate #10, NBFC NIM/GNPA), per-period
   credibility scoring (gate B uses the per-symbol composite today), precise `concall_dt` three-clock model.

## 3. THE HARD CONSTRAINT (decides the backfill)
**Gemini free tier = 20 requests/DAY** for gemini-2.5-flash-lite (hit RESOURCE_EXHAUSTED this session). A
~25-name × ~30-transcript backfill (~750 calls) is impossible on free tier in a day. **Ramana decision
(debate #5):** (a) **claude.ai** for the historical bulk (₹0, paste transcript → import JSON), OR (b) enable
**paid Gemini** billing (~₹90 for the pilot universe), OR (c) throttle ~18/day via cron over weeks. The
extractor self-limits with `--max-calls 18` + stops early on 3 consecutive quota failures. **Incremental**
(≈1 call/company/quarter going forward) fits the free tier for a small universe.

## 4. GUARDRAILS (non-negotiable)
- **Do NOT edit `src/assistant/patearn.py`** (held by a parallel session).
- `db.py`, `llm_router.py`, `concall_*.py`, `cci_*.py`, `dashboard.py` are CCI-session files — yours to edit.
- **Commit to git ONLY when Ramana asks.** Nothing is committed yet (deploys are direct `scp`, per the
  vps-deploy-reality memory: git tree is dirty/behind; do NOT use the git-pull deploy script).
- **Deploy recipe:** `scp -q <file> hermes:/opt/hermes/<path>/` then (for UI) `ssh hermes 'systemctl restart
  hermes-api'`. Always keep production `.venv` import-clean (pypdf is installed there; no numpy/pandas).
- **MEASURABLE-ONLY RANKING (D61) — binding.** Rank/compare on measurable inputs only: `guidance_accuracy`,
  `quantification_rate` (deterministic transparency), the forensic veto, and DETERMINISTIC deterioration
  (from `concall_diff`). The behaviour 0–100 axes are **display-only ("AI read — not ranked")** — never add
  them back to the composite. P2 settlement feeds `guidance_accuracy` (the real rank driver once promises
  resolve); until then names are `unproven` and capped below A/A+. (Note: until `concall_diff` (P3) lands,
  `deterioration_score` leans on LLM-typed flags as a proxy — replace with the true diff.)
- **Run-order contract:** `ingest → results → extract → settle → diff → score`. After any `--force`
  re-extract, settlement MUST re-run before `concall_scores --rerank` (see design §5; concall_extract _persist
  comment). The price firewall in concall_scores must keep passing.

## 5. REMAINING WORK — AUTONOMOUS PROMPTS (run one at a time, each self-contained)

> **STATUS (after session 29):** P1–P4 ✅ · REFINE ✅ · **P5 ✅ (dossier+screener+Pat)** · **P6 ✅ BUILT
> (verdict data-gated)** · **P7 ✅ (timers live)**. **P0-DATA: corpus ✅, extraction accruing via cron.**
> P8 = gated on P6's verdict (needs the backfill). So the prompts below are DONE except the data-gated
> decision — see §2d "WHAT THE NEXT SESSION ACTUALLY DOES". The originals are kept for provenance.

**P0-DATA (backfill — do FIRST so the gates have data).** Decide routing per §3. To accrue via free Gemini:
`ssh hermes 'cd /opt/hermes && .venv/bin/python -m src.automation.concalls <NAMES> --limit 4 --no-ai && \
.venv/bin/python -m src.automation.concall_extract --pending --max-calls 18'` — repeat daily until the golden
set (`resources/cci/golden_set.csv`) + pilot universe are extracted. Prefer claude.ai for the bulk.

**P1 — `src/automation/concall_results.py`** (FREE, no LLM). Parse Screener's quarterly results table (the
`#quarters` / `section#profit-loss` block — reuse `screener.py` `_fetch_company_html` + BeautifulSoup) →
`concall_results` (revenue/ebitda/ebitda_margin/pat/eps + QoQ/YoY %); rows with EBITDA≤0 or margin-collapse →
`concall_ebitda_watch` (magnitude, periods_in_red). Map Screener's quarter columns to our `period_label`
(MMM-YYYY) + (fy, quarter). Verify on RELIANCE/IDEA. CLI: `--symbol`, `--pilot`.

**P2 — `src/automation/concall_settle.py`** (FREE, pure-Python). For each OPEN `concall_guidance` row whose
horizon's resolving period now has a `concall_results` row: parse target+unit via `cci_normalize.parse_amount`,
compare to the actual (like-for-like), set status MET/MISSED/PARTIAL + variance_pct + resolved_period.
DIRECTIONAL promises (no number) grade on **sign-match** of the next print; ABANDONED/RESTATED-down = MISS.
Fill `concall_expectations_vs_actual.external_classification` (vs a trailing-trend anchor where no street) +
`headwind_stated_prior` (only credit a headwind flagged BEFORE the result). Then re-run `concall_scores
--rerank`. Verify: a multi-year capex stays OPEN then flips when its period exists (no look-ahead).

**P3 — `src/automation/concall_diff.py`** (FREE, mostly deterministic). Diff a symbol's consecutive periods'
extracted guidance/disclosure → emit `concall_redflags` of type guidance_walkback (a prior promise's target
lowered/dropped), stopped_disclosing (a metric present last call, absent now), promise_quietly_dropped,
horizon_rolling (same promise, horizon keeps sliding). Set `prior_period`. **Testable NOW on IDEA** (Nov'25 →
May'26, both extracted). This is the primary avoid-tape feeder.

**P4 — `src/automation/cci_pipeline.py`** (runner). Orchestrate ingest→results→extract→settle→diff→score
with the force-reextract→resettle guard + `--max-calls` passthrough. One command for the nightly/weekly run.

**P5 — UI follow-ups** (`dashboard.py` + `src/pat/*`). (a) Per-stock **dossier** panel on `/dash/stock?sym=`
(find the stock-page route; add a "Management Credibility (CCI)" section: the promise ledger with
MET/MISSED/OPEN+variance, behaviour bars + evidence, the red-flag/deterioration timeline,
expectation-vs-actual, the negative-EBITDA ledger, the ⛔ veto banner, coverage note). (b) A CCI
column-group in `/dash/screener` (mirror how CPR joined: tier · trend · deterioration · ⛔veto beside the
other strategies). (c) Pat NL flows — `build_credibility_query` / `build_deterioration_query` in
`src/pat/flows.py` (chips→(sql,params), never free SQL) + register terms in `glossary.py`, route in
`engine.py`, render in `web.py`. Keep data-first; never regress existing pages.

**P6 — Falsification gates** (`research/cci/`, offline `.venv-research`; `pip install statsmodels` there).
Needs ≥~40 extracted concalls across the golden set (do P0-DATA first). (a) `gate_guidance_return.py`:
guidance-direction→forward return from T+2, survivorship-safe, net of 30–150 bps. (b) `gate_residual_alpha.py`:
forward returns on credibility AFTER orthogonalising vs quality (ROCE/debt/size/12-1 momentum) + PEAD,
Newey-West. **DECISION:** if incremental alpha dies → merge CCI into pt14, do NOT ship a standalone book.

**P7 — Schedule** `hermes-concalls.timer` (weekly): run cci_pipeline incrementally, `--max-calls 18`. Add to
`scripts/setup-news.sh`. No Sonnet; Gemini incremental only.

**P8 — Backtest the rank** on the golden set + the bhav-copy survivorship universe (only after P6 passes):
do high-credibility / low-deterioration cohorts outperform forward, OOS, point-in-time? Carry CCI as a
screen/overlay until this clears (the screen-not-book stance).

## 6. KEY COMMANDS
```
# deploy a file
scp -q src/automation/concall_results.py hermes:/opt/hermes/src/automation/
# UI deploy
scp -q src/web/dashboard.py hermes:/opt/hermes/src/web/ && ssh hermes 'systemctl restart hermes-api'
# the chain (on VPS)
ssh hermes 'cd /opt/hermes && .venv/bin/python -m src.automation.concalls RELIANCE --limit 4 --no-ai'
ssh hermes 'cd /opt/hermes && .venv/bin/python -m src.automation.concall_extract --pending --max-calls 18'
ssh hermes 'cd /opt/hermes && .venv/bin/python -m src.automation.concall_scores --backfill'
# verify UI
ssh hermes 'curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/dash/concalls'
```

## 7. FILE MAP
Built+deployed: `src/automation/{concalls,concall_extract,concall_scores,cci_normalize,concall_veto}.py`,
`src/core/{db,llm_router}.py`, `src/web/dashboard.py`, `resources/cci/golden_set.csv`.
To build: `src/automation/{concall_results,concall_settle,concall_diff,cci_pipeline}.py`, `research/cci/{gate_*}.py`.
Transcripts on VPS: `/opt/hermes/data/concalls/<SYM>/*.txt` (gitignored). Local dev DB is a stub — real data is on the VPS.
