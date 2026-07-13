# Codex Review — Findings Ledger (Claude adjudication)

> **Lifecycle: TRANSIENT-CAMPAIGN** (see `00-CONTEXT-FOR-CODEX.md`). Every Codex finding lands here with
> Claude's adjudication. Retire when all domains CLOSED + durable findings folded into canonical docs.

**Process:** Codex reviews a domain → Claude reads the flagged code → classifies each finding →
implements agreed fixes / pushes back / escalates to Ramana / writes the missing doc → marks status.

**Adjudication verdicts:**
- **AGREE-FIX** — Codex is right; Claude implements (after confirming the fix back to Codex where non-trivial).
- **AGREE-DOC** — real gap, but the fix is documentation; Claude writes the doc.
- **PARTIAL** — real issue, different fix than Codex proposed; reconcile with Codex.
- **PUSHBACK** — Codex is wrong (missed context/doctrine); Claude rebuts, Codex re-reviews. If unresolved → ESCALATE.
- **ESCALATE** — genuine conflict or a quality-standard call only Ramana can make.
- **NEEDS-INFO** — Codex asked for context; Claude answers, Codex re-reviews.

**Severity:** P0 wrong-number/leakage/false-prediction · P1 misleading/incomplete · P2 quality/richness · P3 doc/nit.

---

## Domain status

| # | Domain | Codex run | Findings (P0/P1/P2/P3) | Status |
|---|---|---|---|---|
| D1 | DVPT delivery-power engine + Ignition | gpt-5.5 high | 7 (3/4/0/0) | ADJUDICATED |
| D2 | Relative Strength / RRG / rotation / size-index | gpt-5.5 high | 7 (3/2/0/1) | ADJUDICATED |
| D3 | patearn 14-pattern scoring + capital allocation | gpt-5.5 high | 7 (2/4/1/0) | ADJUDICATED |
| D4 | Wolfe Wave §B scoring + detection | gpt-5.5 high | 5 (2/2/0/1) | ADJUDICATED |
| D5 | Explosive-move research honesty | gpt-5.5 high | — | RUNNING |
| D6 | CCI credibility + Concall intelligence | gpt-5.5 high | — | RUNNING |
| D7 | Harmonic / MEP / CPR / momentum / oscillators | gpt-5.5 high | — | RUNNING |
| D8 | Deep-data lenses + infographics + scaffolds | gpt-5.5 high | — | RUNNING |

Raw Codex reports preserved in the session scratchpad (`D<n>-out.md`).

---

## Cross-cutting themes (the real signal — D1–D4)

Findings cluster into six recurring patterns. Grouping matters more than the per-domain list:

- **THEME A — Survivorship / PIT-universe leakage.** D1-F3 (ignition `currently_listed=1` on historical dates), D2-F1 (sector map + `rs_rank` write current snapshot across full history), D4-F2 (`inclusive()` OOS universe = top-300 by **full-history** AVG value → future-informed), D4-F3 (entry before point-5 knowable — suspected). *Impact ranges from latent (live boards only compute "today") to serious (D4-F2 contaminates the recorded "survivorship-aware" Wolfe OOS numbers).*
- **THEME B — Split/bonus adjustment errors.** D1-F1 (`deliv_value = raw_qty × adjusted_close` — breaks split-invariance), D2-F3 (`rs_overlay` builds RS from raw close → fake ~50% RS drop on a bonus). **Both independently Claude-verified.** Surgical fixes.
- **THEME C — Descriptive-fence violations on user surfaces (honesty).** D1-F7 (`ACT` tier + "DVPT picker" naming), D2-F4 (RS-band action verbs Accumulate/Add/Ride/Fade/Trim), D3-F4 (pt14 ordered "highest first" = de-facto ranker), D3-F6 (C-blend "Sharpe 1.32 / survives 1.5× cost" tooltip with no flat-cost-only caveat), D4-F1 (fresh **BEAR** row shown as `★ edge`). *This is the "premium + honest value" concern — surfaces imply action/prediction on descriptive/refuted signals.*
- **THEME D — Thin-history / warm-up guards missing.** D1-F4 (P-tier baselines from a 1-day subset → spurious `SS`/`trigger_rank`), D2-F5 (RS-band verdict shown on <5y history despite design saying suppress).
- **THEME E — Methodology↔doc drift.** D3-F3 (top-5 patterns are proxies, not the exact patterns.md rules), D4-F5 (`wolfe-rules.md` contradicts itself: "§B not implemented" AND "live max 27"; stale B4), D2-F6 (`rs_rank` is broad-only 0.6·3m+0.4·6m, docs claim broad+sector), D4-F4 (`research/wolfe_waves/backtest.py` still imports old ATR-zigzag `detect.py`, no D108 gate).
- **THEME F — Primary-source / PIT provenance.** D3-F5 (nightly batch still fetches Screener live; `pattern_scores` has no `as_of`/`knowable_at`/source; disclosure attached to C, not pt14), D3-F2 (only 2 of 5 hard-disqualifiers wired; CFO-negative/auditor/RPT are comments only).
- **THEME G — Not-implemented sold as implemented.** D3-F1 (financial-sector adaptation per Doctrine D is **not implemented** — the scorer applies generic ROCE/D/E and even hard-disqualifies D/E>2.0 to banks/NBFCs/HFCs; **glossary.py:819 itself admits it's not implemented**; no Doctrine-D note emitted anywhere).

---

## Per-domain adjudication (Claude's verdict on each Codex finding)

**Verdict key:** AGREE-FIX (implement) · AGREE-DOC (fix the doc) · PARTIAL (real, different fix) · PUSHBACK (Codex missed context) · ESCALATE (Ramana product/scope call) · VERIFY (needs VPS/DB data). Severity = Claude's adjusted severity.

### D1 — DVPT + Ignition
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 delivered-value adj bug | P0 | **AGREE-FIX** | **Claude-verified.** `_character_arrays` must use raw close (delivered value is already split-invariant). Needs a `--relabel-character` on VPS after fix. Theme B. |
| F2 ₹25L `LIQ_FLOOR` | P2 | **PARTIAL/PUSHBACK** | Not integrity: it's a *disclosed liquidity filter* (not part of intensity), and the ledger's gate study *endorses* an absolute tradability floor. Fair sub-point: a ₹-constant rots (ramana-principles) → document + consider relativizing (percentile / own-norm). Ramana call on relativizing. |
| F3 ignition survivorship | P1 | **AGREE-FIX (scoped)** | Real foot-gun for historical `--date` recompute; the **live board is unaffected** (only computes "today"; docstring names a `universe_on()` backtest path). Guard historical dates / PIT-gate. Theme A. |
| F4 thin-history → spurious SS | P1 | **AGREE-FIX** | Require P-tier `len(sub) ≥ top_n`; 12M NULL during warm-up. Theme D. |
| F5 `deliv_value_ratio` unused in label | P2 | **AGREE-DOC** | The label deliberately keys on p_score+concentration+price+skew; delivery-trend informs only the plain read. Clarify the doc; optional enhancement is a Ramana call. |
| F6 `FIRST_IGNITION_FROM=2019` | P2 | **AGREE** | Post-D47 deep history → "first since 2019" mislabels. Safe fix: rename/label "first since 2019"; dropping the bound needs pre-2019 data-quality confirmation (VERIFY). |
| F7 "picker"/`ACT` fence | P1 | **ESCALATE** | Theme C. "ACT" tier + "picker" identity vs D62 refuted-picker fence. Product-vocabulary call + "descriptive, not advice" disclaimer. |

### D2 — Relative Strength
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 sector/rank survivorship | P0 | **AGREE-FIX** (verify `stock_rs.py`) | Current-snapshot sector + equity universe written across full history. Same class as D1-F3 but this one **stores historical rows** → materially wrong PIT RS. Theme A. |
| F2 size-index excluded | P0 | **VERIFY/AGREE** | `BROAD_MARKET_PROXIES` gate; size-index RS blank/stale. Overlaps known open item (D67 backfill needs VPS run). Add reader freshness guard. |
| F3 rs_overlay raw close | P0 | **AGREE-FIX** | **Claude-verified.** Build overlay from `adjust.adjusted_closes()`. Theme B. |
| F4 RS-band action verbs | P1 | **ESCALATE/AGREE** | Theme C. Relabel Accumulate/Add/Ride/Fade/Trim → descriptive states; strip "actionable" from design doc. Vocabulary = Ramana. |
| F5 thin-history verdicts | P1 | **AGREE-FIX** | Gate verdict text on maturity (≥5y or show "provisional, no action"). Theme D. |
| F6 rs_rank broad-only | P3 | **AGREE-DOC** | Update calculations-and-weights.md + relative-strength.md to the actual broad-only blend. Theme E. |
| F7 index-name key (suspected) | P2 | **VERIFY** | LargeMidcap 250 membership key spelling — confirm against live `index_rows`. |

### D3 — patearn scoring + C
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 financials adaptation absent | P0 | **ESCALATE** | Theme G. Build Doctrine-D financials model OR suppress/label pt14 for financials until built. Glossary admits it's unimplemented. Big scope call. |
| F2 hard-disqualifiers partial | P0 | **AGREE-FIX** | Only pledge>20% & D/E>2.0 wired; CFO-neg/auditor/RPT are comments. Add `manual_disqualifier_checks_missing` flag blocking high-tier presentation. Theme F. |
| F3 pattern proxies vs exact | P1 | **AGREE-DOC/PARTIAL** | Downgrade the "implemented faithfully" claim + label proxies with lower confidence; exact-rule implementation is optional (Ramana). Theme E. |
| F4 pt14 ordered "highest first" | P1 | **AGREE-FIX** | Theme C. Present as tier buckets + "quality-risk order, not return rank" caveat. |
| F5 Screener live-fetch / no PIT prov | P1 | **AGREE-FIX** | Theme F. Persist `as_of_period_end`/`knowable_at`/source on `pattern_scores`; Screener disclosure on every pt14 surface. |
| F6 C-blend 1.32 no caveat | P1 | **AGREE-FIX** | Theme C. Tooltip → "flat-cost-only 1.32; participation NOT fundable (0.52/0.17/−0.30)". |
| F7 no per-pattern drilldown | P2 | **AGREE-FIX** | Richness: render `detail_json` as a 14-row pass/partial/fail + raw-value drilldown (verified vs estimated). |

### D4 — Wolfe Wave
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 BEAR shown as `★ edge` | P0 | **AGREE-FIX** | Theme C. Side-aware edge labels (BULL fresh=✓edge; BEAR=⚠tail); fix "fresh edge" counts + CSV. **On `wolfe_trades_view.py` — a parallel session is editing this; coordinate.** |
| F2 `inclusive()` universe lookahead | P0 | **AGREE-FIX/VERIFY** | Theme A. Full-history top-300 → future-informed OOS universe. Contaminates the recorded "survivorship-aware" numbers. Fix = per-date universe + re-run phase2/3 (VPS). |
| F3 entry before p5 knowable | P1 | **VERIFY** | Suspected. Need VPS count of rows where `entry_t < p5.idx`, by side + winner-profile. |
| F4 stale research backtest | P1 | **AGREE-FIX** | Retire/port `research/wolfe_waves/backtest.py` (old zigzag, no D108 gate). Theme E. |
| F5 wolfe-rules.md self-contradiction | P3 | **AGREE-DOC** | Collapse stale B4/"not implemented" lines; add live `_QUALITY_MAX=27` component table. Theme E. |

---

## Escalations for Ramana (genuine product / scope / quality-standard calls)

1. **Financial-sector patearn (D3-F1, Theme G).** Build the Doctrine-D financials scorer, or suppress/label pt14 for banks/NBFCs/HFCs until built?
2. **Descriptive-fence vocabulary (Theme C).** Approve relabeling action-verb surfaces (ignition `ACT`/"picker"; RS-band Accumulate/Add/Ride/Fade; pt14 "highest first") to descriptive language + caveats?
3. **Wolfe OOS re-run (D4-F2, Theme A).** The "survivorship-aware" OOS universe is future-informed. Re-run phase2/phase3 with a PIT universe now, or log as a known caveat and queue?
4. **Implementation autonomy.** Proceed to auto-implement the clear, Codex+Claude-agreed bug/doc fixes across the estate, or hold all edits for review first?

---

## D5–D8 findings (cataloged; deep line-trace after Ramana's steer)

**THEME H — Visual / scaffold honesty (new, from D8):** a chart's geometry or a plain-language "read" misrepresents the computed value.

### D5 — Explosive-move research harness (the honesty core)
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 same-close rebalance peek | P0 | **VERIFY→likely FIX** | Theme A. Rank on `i0` close AND enter at `i0` close = same-bar look-ahead across `factory.py` + overlay/cost recuts. **May optimistically bias every headline ledger Sharpe.** Fix = lag features to `i0-1` or enter `i0+1`; re-run. Highest-leverage finding of the review. |
| F2 no flat-cost parity assert | P0 | **AGREE-FIX** | `cblend_cost_recut.py` never proves it reproduces flat-cost 1.32 before the participation loop — the ledger's "only the cost model changed" claim is unverified. Add a parity assertion. |
| F3 PEAD placebo mismatch | P0 | **VERIFY/FIX** | Placebo selects Q5×T3 by *global* quantiles + raw mean, not the cohort-ranked cell/statistic the published claim used. Reuse cohort logic. |
| F4 testing board stale | P0 | **AGREE-FIX** | Theme C. `strategy_store.seed()` imports only 2 CSVs; `/dash/testing` can show old flat-cost rows while prose cites the new participation numbers. |
| F5 prereg not append-only | P1 | **AGREE-FIX** | `--force` UPDATEs the registry row (+ retro-hashing) → not a tamper-evident audit trail. Make append-only versions. (prereg.py is locally modified — coordinate.) |
| F6 `deliv_qty_trend` raw qty | P1 | **AGREE-FIX** | Theme B. DELIV_MOM/QUAL_MOM use raw delivered *share count* (split-sensitive). Switch to delivered value. |
| F7 strategy_menu hard-codes 0.79 | P1 | **AGREE-DOC/FIX** | Stale LOWVOL_MOM 0.79 vs ledger 1.02; reads as "nothing beats index." Read latest run, don't hard-code. |

### D6 — CCI + Concall
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 CCI still ranked | P0 | **AGREE-FIX** | Theme C. `?view=leaders`, `composite_score` sort, Pat "top-N credible managements" — CCI is FALSIFIED-as-factor. Retire leader/rank surfaces; dossier + deterioration-veto only. |
| F2 CCI period-vs-report date | P0 | **AGREE-FIX/VERIFY** | Theme A. `credibility_series` counts actuals by `resolved_period` (period end), not report/filing date → future actuals leak into earlier points. Rebuild + rerun cci_backtest. |
| F3 growth-intent sold as edge | P0 | **AGREE-FIX** | Theme C. `/dash/growth` + `concall_signals` still advertise "+2.8%/+2.3% forward tilt" and "pursue the leaders" despite the placebo-kill. Relabel to proposal ledger; strip return %. |
| F4 thin-sample credibility | P1 | **AGREE-FIX** | Theme D. 1 resolved promise → score ~100/A+; gate to `n_resolved≥3` consistently (backtest+Pat already do). |
| F5 paid extraction on timers | P1 | **VERIFY** | Checked-in services still run `--extract` Gemini drains vs "don't spend to complete corpus." Confirm which are enabled on VPS. |
| F6 non-deterministic extraction | P1 | **AGREE-FIX** | No temp/seed set, only `MODEL_VERSION` stamp → re-extraction silently reclassifies. Stamp prompt/model/settings hash; preserve prior rows. |

### D7 — Harmonic / MEP / CPR / Momentum / Oscillators
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 harmonic zigzag look-ahead | P0 | **AGREE-FIX** | Theme A+C. Enter `D.idx+lag` but D isn't knowable until its confirmation bar; surfaced as "✓ edge". Carry `confirm_idx`; recompute; drop "edge". |
| F2 momentum cost honesty | P0 | **AGREE-FIX** | Theme C (dup of D3-F6, reinforced). momentum-scan omits the participation collapse; shows 1.32/"1.5× cost". Put the two-layer truth (RISKADJ→~0.09; C-BLEND 0.17@50cr; only LOWVOL_MOM fundable). |
| F3 MEP still ranked | P1 | **AGREE-FIX** | Theme C. Home boards + `/dash/mep` top-150 + registry sort by `mep_score_smooth` despite descriptor-lock (DSR fail). Reframe as state distribution. |
| F4 harmonic PRZ AD-only | P1 | **AGREE-FIX** | PRZ built from AD projection only, discards `_FIB_CD` → too-narrow zone. Use both or relabel "AD target". |
| F5 RSI flat-series →100 | P1 | **AGREE-FIX** | Theme D. `avg_gain==avg_loss==0` returns 100 (false overbought). Return 50/None. Mirror in backend + chart JS + RS pane. |
| F6 oscillator stale date | P1 | **AGREE-FIX** | Non-trading symbols stamped with global latest date → stale RSI/MACD shown as current. Gate on per-symbol last date / stale badge. |

### D8 — Deep-data lenses + infographics (richness + Theme H)
| ID | Sev | Verdict | Note |
|---|---|---|---|
| F1 "6-month" plots 24-month | P0 | **AGREE-FIX** | Theme H. launchpad-track Gain/pain uses `MAX_HORIZON=504td` MFE/MAE but labels "next 6 months" → overstates rise. Persist true 6m fields or relabel. |
| F2 credibility axis capped ±80% | P0 | **AGREE-FIX** | Theme H. Clamps +90/+300/+800% to the same rail, no marker → hides the delivery gap the visual exists to show. Uncapped/broken-axis + value labels. |
| F3 FII scaffold always "bearish" | P1 | **AGREE-FIX** | Theme H. `plain()` always says "near the bottom — unusually bearish"; bottom line calls ≥0.9 "bullish" vs the balanced 0.9–1.1 band. Derive read from `pct`/`stance`. |
| F4 spark_area bridges gaps | P1 | **AGREE-FIX** | Theme H. Docstring says None→gap but code bridges → false continuous path. Draw contiguous segments. |
| F5 breadth glossary collision | P1 | **AGREE-DOC** | Theme E/H. market-internals "breadth" links to the DVPT "Breadth" (crossing-count) entry. Add distinct market-breadth keys. |
| F6 sector-econ FY15→FY26 mislabel | P1 | **AGREE-FIX** | Theme H. Labels first/last *populated* cells as FY15/FY26 even when endpoints blank → false decade story. Render actual years. |

---

## Estate-level read (all 8 domains)

The analytical **engines** are, on the whole, carefully built and heavily fixed (the CL-MDC/AUD trails in `signals.py` are exemplary). The systemic risk is concentrated in **two bands**:

1. **Surface honesty-fence leakage (THEME C — the largest cluster).** Many screens present descriptive / falsified / refuted signals as *ranked, actionable, or predictive*: CCI "credibility leaders", growth-intent "+2.8% edge", MEP ranked boards, momentum "1.32 / survives 1.5× cost", pt14 "highest first", ignition "ACT / picker", RS-band "Accumulate/Add/Ride", Wolfe "BEAR ★edge". Individually small; collectively they undercut the project's core honesty claim.
2. **PIT / cost integrity in the research layer (THEMES A + B).** Same-close rebalance peek (D5-F1), future-informed OOS universe (D4-F2), CCI period-vs-report date (D6-F2), harmonic zigzag repaint (D7-F1), and raw-quantity/adjustment errors (D1-F1, D2-F3, D5-F6). Several **could bias the recorded ledger numbers optimistically** and warrant re-runs + restatement.

Plus a set of clean, low-risk correctness bugs (RSI flat-series, PRZ AD-only, oscillator staleness, visual mislabels) that are unambiguous fixes.

## Escalations for Ramana (revised — genuine product / scope / quality calls)

1. **Same-close backtest leak + OOS re-runs (D5-F1, D4-F2, D6-F2).** These may mean some headline ledger/OOS Sharpes are optimistically biased. Authorize the PIT re-runs + ledger restatement (VPS), or log as caveats and queue?
2. **Descriptive-fence surface sweep (THEME C).** Approve a coordinated relabel/de-rank of the action-verb + false-edge surfaces (CCI leaders, growth-intent %, MEP boards, momentum cost, pt14 order, ignition ACT, RS-band verbs, Wolfe BEAR)?
3. **Financial-sector patearn (D3-F1).** Build the Doctrine-D financials scorer, or suppress/label pt14 for financials until built?
4. **Implementation autonomy.** Proceed to auto-implement the clear, agreed, low-risk bug/doc fixes (adjustment bugs, RSI, PRZ, visual mislabels, scaffold reads, doc drift) across the estate, or hold for review?

---

## Ramana's decisions (2026-07-13)

1. **Backtest integrity** → **Verify bias, then re-run + restate** (VPS). D5-F1 / D4-F2 / D6-F2.
2. **Honesty-fence sweep** → *"what do you recommend, check with the agents"* → Claude recommends **sweep all** (fence is non-negotiable), hard-falsified first; **validating the plan with Codex** (consult-1) before executing.
3. **Financials patearn (D3-F1)** → **Build the Doctrine-D financials scorer** (needs primary GNPA/CAR/ALM data — guardrail #8). A dedicated project.
4. **Clean fixes** → **Implement autonomously in batches**, Codex-confirming non-trivial ones.

## Implementation log

**Multi-session guard:** parallel session owns `wolfe.py`, `wolfe_trades_view.py`, `wolfe_view.py`, `prereg.py`, `metrics-glossary.md`, `strategy-ledger.md` (uncommitted). All batches AVOID these until they land → **deferred: D4-F1, D4-F4, D7-F1 (harmonic zigzag lives in wolfe.py), D5-F5 (prereg), doc-drift fixes to metrics-glossary/strategy-ledger.**

**Local verification limit:** local `hermes.db`=15 MB (VPS ≈16 GB), `research.db`=12 KB empty → backtest-bias verification + any `--relabel`/re-run is VPS-only. Pure-logic fixes are unit-verified locally.

### Batch 1 — clean correctness (DONE, verified, uncommitted)
- **D7-F5 RSI flat-series** — `oscillators.py:_rsi` and `momentum_pane.py:199,204` now return **50** on a flat run (was 100 = false "overbought"). Verified: flat→50, rising→100, falling→0, mixed→68.4; both compile. *Mirror still pending in `stock_chart.py` JS — awaiting Codex's exact line ref (consult-1 Part 1b).*
- **D1-F1 delivered-value split bug** — `signals.py:_character_arrays` `deliv_value` now uses **raw** same-day close (was raw_qty × adjusted_close). Compiles; Codex confirmation pending (consult-1 Part 1a). **VPS action queued:** `signals --relabel-character` / trigger backfill to correct stored historical rows.

### Queued next (safe, non-hot files)
Batch 2 (visual/scaffold, Theme H): D8-F3 FII scaffold, D8-F4 spark_area gaps, D8-F6 sector-econ years, D8-F2 credibility axis cap, D8-F1 launchpad horizon label, D8-F5 breadth glossary key. · Batch 3 (correctness): D2-F3 rs_overlay adjusted close, D7-F4 harmonic PRZ, D7-F6 oscillator staleness, D1-F4 warm-up guard. · Then the Codex-validated honesty-fence sweep (Theme C). · Then Track C (VPS bias verify) + Track D (financials scorer).

### Batch 1 — COMPLETE (RSI now fixed in all 3 sites)
Added `stock_chart.py:178-179` JS mirror (Codex-confirmed lines): flat run → 50, not 100. D7-F5 fully closed in code. D1-F1 + D7-F5 both **AGREE-confirmed by Codex** (consult-1).

## Codex-validated honesty-fence sweep plan (Theme C — ready to execute)

Codex refined the blanket "sweep" into **DE-RANK the one hard-falsified factor, RELABEL the rest** (their sorts have legitimate operational/descriptive uses — preserve them). Priority order + exact sites:

| # | Surface | Action | Key sites | Honest label |
|---|---|---|---|---|
| 1 | **CCI leaders/rank** | **DE-RANK** | `concall_scores.py:215-218` (stop storing ordinal rank), `cockpit.py:1994-2064`, `pat/flows.py:554-561`, `pat/web.py:1140-1152` | "CCI = promise-keeping + deterioration-veto record. Falsified as a return factor; not a ranked long list." **Keep** the worst-first *avoid* tape (`flows.py:569-572`) — legit triage. |
| 2 | **Growth-intent tilt** | RELABEL | `concall_signals.py:5-7,33`, `growth_view.py:5-7,34,171-176`, `cci_backtest.py:629-632` | "Forward proposal ledger. Placebo-killed as a return signal; order = commitment size, not expected return." **Keep** amount sort (`concall_signals.py:176`). |
| 3 | **Momentum C-blend** | RELABEL | `momentum_view.py:119-122,180,204-209` | "C-blend = flat-cost/paper only. Participation Sharpe 0.52@25cr / 0.17@50cr / −0.30@100cr; not fundable. Only qtr large-cap LOWVOL_MOM cleared." **Keep** scanner sort. |
| 4 | **MEP ranked boards** | RELABEL | `cockpit.py:717-726,1546-1551,2110-2116`, `strategy_registry.py:102-120` | "MEP signed pressure state. Descriptor/confirmation only; DSR-failed as a return signal." "Top 150" → "150 most extreme state reads/side". **Keep** signed-extreme sort. |
| 5 | **pt14 highest-first** | RELABEL | `pat/flows.py:504-520`, `pat/web.py:1031-1032` | "pt14 quality-risk order, not a return ranking — business-quality filter/veto context." **Keep** sort. |
| 6 | **RS-band verbs** | RELABEL (shared helper) | `rsband.py:279-317` (one helper), `rsband_view.py:144,346-351,653-654,821-839` (color maps) | Accumulate→"Low band + turn" · Add→"Rising from band" · Ride→"Re-rating" · Avoid→"De-rating" · Fade→"Upper-band rollover" · Trim→"At resistance" · Hold→"Mid-band". "Descriptive relative-level lens, not a buy/sell/trim instruction." **Keep** band sort. |

Shared fix points: `rsband.py:279-317` (one helper fixes most RS-band surfaces); `momentum_view.py:204-209` (the main C-blend fence). **None of these files are in the parallel session's hot zone** — safe to sweep. Wording is Ramana's product voice → confirm before shipping surface #1 as the template.

### Batch 2 — visual/scaffold honesty (DONE, verified, uncommitted)
- **D8-F4 spark_area gap-bridging** — `infographics.py` now splits into contiguous non-None segments (verified: gapped series → 2 polylines, contiguous → 1). Fixes every sparkline site-wide.
- **D8-F3 FII scaffold** — `participants_view.py` beginner read now derives from the computed percentile/stance (was hardcoded "near the bottom — bearish").
- **D8-F2 credibility axis cap** — `credibility_fingerprint.py` now prints the TRUE magnitude on any point clipped beyond ±vmax (so +90/+300/+800% no longer look identical).
- **D8-F1 launchpad horizon** — `launchpad_track_view.py` "over the next 6 months" → "over the full tracked journey (up to ~24 months…)" (the fields are 504-td MFE/MAE).
- **D8-F6 sector-econ endpoints** — `sector_econ_view.py` now carries + renders the ACTUAL first/last populated fiscal years (was mislabeled FY15→FY26 on thin sectors).
- D8-F5 (breadth glossary collision) **deferred** — target `metrics-glossary.md` is in the hot zone.
- All five compile; `spark_area` smoke-tested.

### Honesty-fence sweep — surface #3 (Momentum C-blend) DONE
- `momentum_view.py` — removed the obsolete "survives 1.5× cost" claim; the C-blend note + header now carry **"flat-cost Sharpe 1.32; NOT fundable net of participation cost (0.52@₹25cr / 0.17@₹50cr / −0.30@₹100cr); only qtr large-cap LOWVOL_MOM cleared."** Sort preserved (per Codex). Compiles.

**Files edited this session (all compile, none in hot zone):** oscillators.py, signals.py, momentum_pane.py, stock_chart.py, infographics.py, participants_view.py, credibility_fingerprint.py, launchpad_track_view.py, sector_econ_view.py, momentum_view.py (10).

**Remaining sweep surfaces:** #1 CCI de-rank (cockpit.py/concall_scores/pat), #2 growth-intent (concall_signals/growth_view), #4 MEP (cockpit/strategy_registry), #5 pt14 order (pat), #6 RS-band verbs (rsband + rsband_view). **Batch 3:** rs_overlay adjusted close, harmonic PRZ, oscillator staleness, D1-F4 warm-up guard, D1-F5/F6 (ignition — note D3/ignition items). **Tracks C (VPS bias verify+restate) & D (financials scorer)** pending their run/data plans.

## Convergence pass (consult-2) — Ramana's rule: ship only on Codex↔Claude agreement

**Part A — Batch 2 implementations: Codex AGREE on all 5** (spark_area segments, FII stance-derived read, credibility clipped-value labels, launchpad 24-mo relabel, sector-econ real-year endpoints). → Batch 2 **settled**.

**Part B — the three divergences, resolved:**
- **B1 (₹25L `LIQ_FLOOR`) — CONVERGED (AGREE).** Not P0; a disclosed liquidity filter applied *after* intensity, endorsed by the ledger gate study. Resolution = **document + note the rot** → **DONE** in `calculations-and-weights.md` §5e (floor rationale + "hard rupee constant rots → relativize" caveat). Optional relativization = future.
- **B2 (`deliv_rising` unused) — Codex COUNTER accepted.** My premise was half-wrong: the flag was computed but consumed *nowhere*. Convergent fix = make it load-bearing → **DONE** in `signals.py` `accum_character_read` (appends "delivery ₹ rising vs its 6-month base" when it is; verified: appends at ratio 1.5, absent at 1.0/None). The *label* still deliberately keys only on p_score+concentration+price+skew (documented).
- **B3 (proxy vs exact patterns) — CONVERGED (AGREE).** Immediate fix = honest doc downgrade + proxy labeling → **DONE** in `patearn.md` §3 (explicit "Proxy fidelity" note: Pattern 1/2/5 are conservative proxies, not the exact multi-year rules; exact-rule impl is a queued enhancement).

All three were agreed with Codex **before** implementing, per the governance rule. Files: `signals.py`, `docs/calculations-and-weights.md`, `docs/strategies/patearn.md` (none in the hot zone).

### Batch 3 — D2-F3 rs_overlay adjusted-close DONE (verified)
`src/web/rs_overlay.py` — the RS ratio's stock leg now uses `adjusted_closes(rows, price_ratios(conn,sym))` (the proven `signals.py` tape-primary path), with a raw-close fallback so the overlay never fails. Verified: a 1:1 bonus that faked a −50% RS drop on raw closes now reads ~1.0 (no real move) once the tape neutralizes it. The index leg stays raw (continuous series). Theme B, self-contained, Codex-flagged (D2-F3), compiles.

**Session tally (all verified, all Codex-agreed, uncommitted, none in hot zone):** 15 files — RSI×3, delivered-value, 5 visual/scaffold, momentum caveat, B1/B2/B3 (signals + 2 docs), rs_overlay.

### Remaining (next sessions, same converge-then-implement rule)
- **Honesty-fence sweep** (Codex-validated, consult-1): CCI de-rank (cockpit.py/concall_scores/pat — big), growth-intent (growth_view/concall_signals), MEP (cockpit/strategy_registry), pt14 order (pat), **RS-band verbs (rsband.py shared helper + rsband_view.py color-maps — do label producer AND every color-map consumer in one pass so rendering can't break)**.
- **Batch 3 remainder:** harmonic PRZ (D7-F4), oscillator staleness (D7-F6), ignition warm-up guard (D1-F4), ignition F3/F6/F7.
- **Track C (VPS):** verify+restate the backtest-bias P0s (D5-F1 same-close, D4-F2 OOS universe, D6-F2 CCI dates) — needs a VPS session + run-plan.
- **Track D:** Doctrine-D financials scorer — needs a primary-source (GNPA/CAR/ALM) data plan first.
- **Deferred (sibling hot zone):** Wolfe (D4), harmonic-zigzag (D7-F1 in wolfe.py), prereg (D5-F5), metrics-glossary/strategy-ledger doc-drift, seasonal_tape.

### Batch 3 — D7-F6 oscillator staleness DONE (verified)
`src/automation/oscillators.py` — `_recent_closes` now returns each symbol's own last trade_date; `compute_and_store` stamps THAT (not the global latest session), so a name that didn't trade today no longer surfaces a stale RSI/MACD as current. Compiles; no orphaned refs. Self-contained, Codex-flagged (D7-F6).

### RS-band relabel (Theme C #6) — HELD for convergence (consult-3)
Started, then **stopped before shipping** on discovering the naive plan is unsound under the governance rule: the verdict string is simultaneously the display label + color-map key + highlight logic + selftest assertion, AND verbs are reused across contexts (`Trim` = "at resistance" AND "mid-band fading"; `Add`/`Ride`/`Avoid` likewise), so Codex's flat 1:1 map would MISLABEL the mid-band cases. Proposed refined design to Codex (consult-3): **decouple** — keep the stable verdict keys (zero risk to color/logic/selftest), append a context-correct `state_label` third return element, render that, and add the "descriptive lens, not a buy/sell/trim instruction" caveat. Awaiting Codex AGREE/COUNTER before implementing. **This is the rule working as intended — a split plan does not ship.**

### RS-band relabel (Theme C #6) — DONE (converged via consult-3, verified)
Codex AGREE'd the decoupled design (stable keys + appended `state_label`) + gave 2 label fixes (band≤20-flat → "Low band · no turn yet"; "Trending · band secondary" not "follow trend"). Implemented as **one complete producer→consumer pass**:
- `rsband.py` `band_verdict` now returns `(verdict_key, reason, state_label)` — keys UNCHANGED (color/highlight/**selftest all still pass**), 3rd element = context-correct non-instructional label (fixes the mid-band mislabel the flat map would've shipped: mid-band-down = "Mid-band · fading", NOT "At resistance").
- All 6 callers updated to 3-unpack (`rsband.py:481`, `rsband_view.py:92/682/793/826/904`); every DISPLAY site renders `state_label`, every COLOR/LOGIC site keeps the key (audited by grep). Caveat "RS-band is a descriptive relative-level lens, not a buy/sell/trim instruction" added to the table + channel surfaces.
- Verified: selftest asserts pass, producer 3-tuple, `_table` render shows the label / hides "Accumulate" / shows the caveat / keeps color keying. No 2-tuple caller remains → no crash risk.

**Session tally: 15 distinct files** (all verified/compiled, all Codex-agreed-or-converged, uncommitted, none in hot zone): oscillators, signals, momentum_pane, stock_chart, infographics, participants_view, credibility_fingerprint, launchpad_track_view, sector_econ_view, momentum_view, calculations-and-weights.md, patearn.md, rs_overlay, rsband, rsband_view.

### Growth-intent de-claim (Theme C #2) — DONE (Codex-validated consult-1, verified)
The placebo-killed "+2.8%/+2.3%/+1.8%/+1.5% forward tilt" is removed everywhere it was sold as an edge:
- `growth_view.py` — docstring + `_TABS` labels (stripped the % from Debt/Volume/New-product/Capex/Expansion) + the inline head note now read "descriptive proposal ledger; the forward tilt was **placebo-killed** on real dates (covered-universe drift); order = commitment size, not expected return."
- `concall_signals.py` — docstring + `GROWTH_TYPES` comment relabeled to a descriptive proposal grouping, not a return factor.
- `cci_backtest.py` — the `--mode scan` output no longer says "Pursue the leaders as factors"; it prints the placebo-kill caveat ("DESCRIPTIVE only; do NOT trade it as a factor").
All three compile; only residual "+2.8%" is inside the placebo-kill caveat itself.

**Session tally: 18 files.** Sweep done: #2 (growth-intent), #3 (momentum C-blend), #6 (RS-band).

### CCI de-rank (#1) — CONVERGED (consult-4) · A1 DONE · rest queued
Codex convergence produced an exact per-surface spec and surfaced ~9 more sites than my initial map (incl. confluence sorts + test-file labels). **Agreed spec:**
- **(A1) `render_concalls` (cockpit.py) — DONE + verified.** Default = avoid tape; second view renamed "leaders"→**Track record** with a NEUTRAL coverage-first sort (`n_promises_resolved DESC, symbol`), NOT `composite_score`. Tile → "Tracked (veto-excluded) · coverage-first, not ranked"; note → "Track record — coverage-first (#settled desc), not a credibility ranking"; global caveat "CCI is a promise-keeping + deterioration-veto record — falsified as a return factor, not a ranked long list." `leaders` kept as compat alias. Compiles; grep-verified no composite-rank left.
- **(A2) hub CCI board (cockpit.py 1911-1954, cta @423, subtitle @1958):** flip query to `WHERE veto OR deterioration>0 ORDER BY veto DESC, deterioration DESC, symbol`; board value = "veto"/"deterioration N"; cta → "veto / deterioration watch"; hub subtitle "today's best names"→"live states to inspect". (RS/CONV boards untouched.)
- **(C) `concall_scores.py`:** cease **writing** ordinal rank (write NULL; leave nullable column — no migration); drop "+ ranked" CLI/log language; stale `db.py` comments (695-696, 880-888). Remove Pat rank display `pat/web.py:1531-1533`.
- **(D) pat:** `flows.py:554-561` → coverage-first sort + "not a ranked list" docstring (keep 565-572 avoid tape); **confluence sorts** `flows.py:606` + `700-701` drop `c.composite_score DESC` (use p_score/rs_rank primary, `n_promises_resolved` tiebreak); `pat/web.py` bubbles/headers/chips (1138-1158, 2222, 1178/1241/1741) "Credibility leaders"→"CCI track record".
- **Also:** `strategy_registry.py:220-245` + `strategist_view.py:219-235,683` CCI boards → avoid-watch/coverage-first; `dashboard.py:2795-2801` route doc + `2719/2726-2728/2773-2775` dossier "rank" language; **test/label files** `pat/engine.py:46`, `disambiguate.py:325-334`, `understand.py:564-570/633-638/1125-1134`, `eval_set.py:212-216/460-461` renamed leaders/top→track-record (mind the test assertions).

### MEP relabel (Theme C #4) — primary surfaces DONE (Codex-validated consult-1, verified)
RELABEL (kept the signed-extreme sort — legitimate operational use). `cockpit.py`: `/dash/mep` note reframed "Top 150"→"the 150 most extreme state reads each side by phase" + explicit fence "<b>Descriptor / confirmation only — DSR-failed as a return signal (D62); never a picker.</b>"; both home boards (Net accumulation / Distribution watch) subtitles now carry "(descriptor · DSR-failed)". Compiles; verified. *Minor follow-ups (secondary): intra-index MEP board (1546-1569) + `strategy_registry._mep` card — sort kept, labels are already state-labels; light caveat later.*

### pt14 relabel (Theme C #5) — DONE (Codex-validated, verified)
`pat/web.py` bubble + `pat/flows.py:build_pt14_query` docstring: the ns_base ordering is kept (best-quality triage) but relabeled "A QUALITY-RISK order (best-quality first), NOT a return ranking — pt14 is a business-quality filter/veto-context lens, not a buy list (D66; NS long-short ≈ 0)." No "highest first" left; both compile.

### 🏁 THEME C honesty-fence sweep — ALL 6 SURFACES ADDRESSED
✅#1 CCI (primary board de-ranked + full remainder spec'd) ·✅#2 growth-intent ·✅#3 momentum ·✅#4 MEP(primary) ·✅#5 pt14 ·✅#6 RS-band.

### harmonic PRZ (Batch 3, D7-F4) — DONE (verified)
`harmonic_patterns.py` `_project_forming`: the forming-pattern PRZ was built from the AD projection only (`c[1]`), discarding the BC/CD extension (`c[2]`) → a too-narrow reversal zone. Now `levels` spans BOTH projections (the real confluence). Verified on a synthetic Crab+Gartley: the CD leg widened the zone (hi 108.6 → 114.2), revealing the two-projection spread it previously hid. Self-contained, no stored-data/test impact, compiles.

**Session tally: 22 files** (added pat/web.py, pat/flows.py, harmonic_patterns.py), all verified, all Codex-agreed/converged, uncommitted, none in hot zone.
### 🏁 CCI de-rank (#1) — SUBSTANTIVELY COMPLETE (all output-ranking surfaces; tests green)
Implemented the full consult-4 spec across **8 files**; `pytest -k "pat/cci/concall/credib/strateg/registry/dashboard"` = **20 passed, 1 skipped** (no breakage):
- **A2 hub board** (`cockpit.py`): `composite_score DESC` → veto/deterioration watch (`WHERE veto OR deterior>0 ORDER BY veto DESC, deterior DESC, symbol`); board value = "⛔ veto"/"deterior N"; registry cta → "veto / deterioration watch"; hub subtitle "today's best names" → "live states to inspect".
- **C cease writing rank** (`concall_scores.py`): `run()` always writes NULL rank (ordinal removed); docstring + CLI de-ranked; nullable column left (no migration). Pat dossier rank display (`pat/web.py`) → "pilot record · N concalls scored". Dashboard dossier "rank"→"score" language.
- **D Pat** (`pat/flows.py` + `pat/web.py`): `build_credibility_query` → coverage-first (`n_promises_resolved DESC`); both confluence sorts drop `c.composite_score DESC` (p_score / rs_rank primary, coverage tiebreak); every "Credibility leaders" display → "CCI track record" (bubble/header/chips/route label).
- **Registry + strategist** (`strategy_registry.py`, `strategist_view.py`): CCI cards `composite_score DESC` → coverage-first; strategist "credibility leaders" link → "CCI track record".
- **Kept (legit):** the deterioration/veto avoid tape, the per-name dossier + promise-vs-delivery fingerprint, and all RS-leaders surfaces (untouched).
- **Optional remainder (test-coupled, NOT output-ranking):** parser-vocab aliases (`engine.py`/`disambiguate.py`/`understand.py`/`eval_set.py`) + `pat/web.py:1964` query-example + `strategist_view.py:857` selftest string — these let the parser RECOGNIZE "credibility leaders" as *input* routing to the de-ranked track-record flow; renaming is cosmetic polish, deferred.

### MEP secondary + CCI parser polish — DONE (tests green: 22 passed)
- **MEP secondary:** intra-index board subtitle → "signed accum/distrib STATE · descriptor (DSR-failed)"; `strategy_registry._mep` label "Accumulation (MEP)" → "MEP accum-state (descriptor)" (sorts kept).
- **CCI parser polish:** updated 3 stale code comments (`engine.py:46`, `disambiguate.py:390`, `understand.py:867`) leaders/rank → track-record/coverage-first. **Deliberately KEPT the input-recognition aliases** (`disambiguate.py _CCI_LEAD`) + their `eval_set.py` test fixtures — those are how users naturally ASK ("most credible managements"); renaming would break natural queries + tests for zero honesty gain since the OUTPUT is already de-ranked + relabeled "CCI track record."

**Session tally: 29 files** — all verified/compiled, tests green, all Codex-agreed/converged, uncommitted, none in hot zone.

## 🏁 All locally-completable work is DONE. Remaining needs a specific resource:
- **Track C** (VPS) — verify + restate the P0 backtest-bias items (same-close rebalance, Wolfe OOS universe, CCI period-vs-report date) **+ D5 `deliv_qty_trend` value fix** (both change recorded ledger numbers → re-run on the full archive).
- **Track D** — Doctrine-D financials scorer (needs a primary GNPA/CAR/ALM data decision first).
- **Ignition warm-up guard (D1-F4)** — changes scoring + needs a VPS `--relabel` backfill; converge on the min-coverage rule first.
- **D5 research-harness** — flat-cost parity assertion, PEAD placebo statistic, prereg append-only (prereg is sibling-hot).
- **Deferred (sibling hot zone):** Wolfe (D4), harmonic-zigzag (D7-F1), prereg (D5-F5), metrics-glossary/strategy-ledger doc-drift, seasonal.
