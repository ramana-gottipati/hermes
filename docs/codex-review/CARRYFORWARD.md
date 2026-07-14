# Carry-forward — Codex data/analytical review campaign (2026-07-13/14)

> **Lifecycle: TRANSIENT-CAMPAIGN.** Takeover prompt + queue for the next session continuing the
> Codex full-estate review. Retire once the OPEN queue is drained and the durable findings are folded
> into the canonical docs. (This lives in `docs/codex-review/` — the review's lane — deliberately NOT
> in `docs/NEXT-SESSION-CARRYFORWARD.md`, which the parallel UI/seasonal session owns.)

## Takeover prompt (paste to resume)

You are continuing a **Codex (gpt-5.5) full-estate data/analytical review** of Patearn — a rigorous
sanity check of everything the app *calculates or projects*. Codex is the independent adversarial
reviewer; Claude adjudicates against the code + doctrine. **Governance rule (Ramana, binding): ship a
change ONLY after Codex and Claude reach genuine logical agreement — never on a split.** Where they
diverge, converge (persuade or concede) before acting; escalate true conflicts to Ramana.

**Read first:** `docs/codex-review/FINDINGS-LEDGER.md` (all ~50 findings + per-finding adjudication),
`docs/codex-review/TRACK-C-RESULTS.md` (the on-VPS backtest-bias verification), and
`docs/codex-review/00-CONTEXT-FOR-CODEX.md` (the review frame). The Codex runner pattern: pipe a
domain prompt to `codex exec --dangerously-bypass-approvals-and-sandbox -c model_reasoning_effort=high`
from the repo root (the read-only sandbox can't spawn a shell on this Windows box).

## What shipped (committed + pushed to origin/main)
- **`5c6720f`** — the review fixes, 29 files: the whole **Theme C honesty-fence sweep** (CCI fully
  de-ranked, growth-intent placebo-kill, momentum C-blend cost truth, MEP descriptor fence, pt14
  quality-risk-order, RS-band decoupled labels) + correctness bugs (delivered-value split, rs_overlay
  split, RSI flat-series ×3, oscillator staleness, harmonic PRZ) + visual/scaffold honesty ×5.
- **`71fbffb`** — Track C: D5-F1 entry-lag fix (`factory.py`) + D4-F2 label corrections
  (`phase1_tradesim.py`) + D6-F2/D5-F6 leak markers.
- **`3e1426d`** — Track D data plan (`docs/codex-review/TRACK-D-DATA-PLAN.md`).
- **`5d55ac7`** — PROJECT_STATE § Session 128 (carried by the parallel session's state-commit).
- **Track C — DONE + verified on the VPS:** all 4 P0 integrity leaks are REAL but MINOR — none
  overturns a recorded conclusion (RISKADJ flat-cost 1.13→1.09; Wolfe still IN-SAMPLE-ONLY; CCI still
  descriptive-only). Full numbers in `TRACK-C-RESULTS.md`.

## OPEN queue (priority order)
1. **Track C code-fix remainder** (both verified-minor, deferred deliberately):
   - **D6-F2** — store a report/knowable date on settlement (`concall_settle.py` + `credibility_series`
     schema) and gate on it, not `resolved_period` end. Marker at `cci_series.py`.
   - **D5-F6** — compute a delivered-**value** trend (`dq * ss.close`, **raw** close — not adj_close, to
     avoid the D1-F1 trap) in `embase.py`, swap into DELIV_MOM/QUAL_MOM. ⚠ Feeds the LIVE nightly
     momentum_scan → do it with a `momentum_scan` re-verify + deploy. Marker at `embase.py`.
2. **Ledger annotation** — fold RISKADJ flat-cost **1.13→1.09** into `docs/strategy-ledger.md`
   (recorded in TRACK-C-RESULTS.md; **coordinate — strategy-ledger.md is sibling-hot**).
3. **Track D — Doctrine-D financials scorer (D3-F1). DATA PLAN DELIVERED** (`TRACK-D-DATA-PLAN.md`,
   `3e1426d`): extend the LIVE `fundamentals_xbrl.py` bank extractor (primary NSE XBRL, **no vendor**)
   for GNPA%/NNPA%/CAR/cost-to-income; reuse the existing `capital_allocation` `model='financial'`
   (RoE/RoA); route financials in `scoring.py` + emit the "sector-adapted thresholds (Doctrine D)" note;
   disable the D/E hard-disqualifier for lenders. **AWAITING RAMANA's 3 decisions** (scope order ·
   sub-type bank/NBFC/HFC thresholds · ALM proxy-vs-build) — Claude's recommendation: **interim
   suppress-label now + sub-type-aware + proxy-ALM-via-CRAR+GNPA**. **Build sequence once decided:**
   (a) interim suppress-label pt14 for financials (stops the live mis-rating today — HDFCBANK shows
   nonsense `roce=1.57/roe=7.04`); (b) **tag-inventory spike** on 3-5 lenders' RAW XBRL to confirm
   GNPA/CAR are tagged (feasibility gate; ⚠ use the `/api/corporates-financial-results` row's `xbrl`
   field → `fetch_instance()`, NOT `list_filings()` metadata — my quick attempt got a stub via the
   wrong path); (c) extend `extract_bank_for()` + add nullable columns to `fundamentals`; (d) route +
   note. Untagged metric → defer to Phase 2 (annual/Basel III), NEVER a vendor.
4. **Ignition warm-up guard (D1-F4)** — P-tier baselines form on 1-day history → spurious `SS`. Changes
   scoring + needs a VPS `--relabel`/trigger backfill; **converge on the exact min-coverage rule first.**
5. **Deferred behind the parallel Wolfe/seasonal lane** (their hot files — do NOT touch until they land):
   Wolfe D4 fixes (`wolfe_trades_view.py` BEAR-edge, stale `backtest.py`), harmonic-zigzag D7-F1
   (`wolfe.py` confirm_idx), prereg append-only (D5-F5, `prereg.py`).
6. **Minor polish** — MEP secondary (intra-index board + registry card labels), CCI parser-vocab aliases
   (`engine.py`/`disambiguate.py`/`understand.py`/`eval_set.py` — test-coupled; run the suite after).
7. **Also queued from D1-F1** — run `signals --relabel-character` on the VPS to correct stored
   `accum_character` rows for the delivered-value split fix (already shipped in `5c6720f`).

## Standing context
- **Multi-session:** a parallel session is active on the research/seasonal/UI lanes. **NEVER `git add -A`
  or `git add .`** — stage explicit paths, verify the staged set, then commit (auto-push is ON).
  Sibling-hot files: `PROJECT_STATE.md`, `docs/strategy-ledger.md`, `docs/metrics-glossary.md`,
  `research/explosive_moves/*` (attribution/factor_zoo/gate_study/prereg), Wolfe/seasonal modules.
  Re-check `git status` before every edit; a file clean now can be hot in 2 minutes.
- **VPS:** SSH works (`root@187.127.173.149`, srv1704897). Research venv = `/opt/hermes/.venv-research/
  bin/python` (numpy). Read-only research is safe: `nice`d, no DB writes, reproduce recorded numbers
  before changing anything, NEVER touch services/timers (bans: no `setup-news.sh`, no mid-day timer start).
- **Engines are sound; the risk was surface honesty + research PIT** — and Track C confirmed the PIT
  leaks are minor. The asset is PIT rigor + the analytical lens, not a backtested alpha (descriptive-only
  doctrine holds).
