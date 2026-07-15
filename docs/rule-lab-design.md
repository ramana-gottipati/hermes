# Rule-lab — design (D134 plan §4-H, layers L4/L7)

> **Lifecycle: TRANSIENT (design doc).** The build spec for the rule-lab: a closed-vocabulary
> grammar that lets Ramana ask "does MY rule actually work?" and get an honest, pre-registered,
> cost-real verdict. Registered in `docs/DOC_INDEX.md` (D. RUN-BOOK).
> **Retire condition:** when the build session lands `src/…/rule_lab*` + its surface, fold the
> surviving decisions into `docs/patearn-analytics-company-plan.md` §4-H + a `docs/strategies/`
> page, then `git rm` this file.

**Status:** DESIGN ONLY — no code in this lane (prompt-pack §LANE-H). META (plan §4-H):
Importance **8** · Criticality 4 · Timing later · Cost ₹0.

---

## 1. What it is, in one paragraph

Today, testing an idea means a Claude session hand-writing a study module. The rule-lab makes
that a **product surface**: Ramana composes a rule from a fixed vocabulary ("rank the liquid-500
by 12-month momentum, exclude anything up >200% in 5 years, take 25, hold quarterly"), and the
existing evidence factory runs it through the same gauntlet every house study passes —
walk-forward halves, a pre-registered gate, a placebo control, realistic costs, a capacity
breakpoint — and returns a verdict in the **ledger's own vocabulary**. The lab's value is not
that it finds winners. Its value is that **it makes falsification cheap and automatic**, and it
**refuses to let a known-dead idea be re-walked silently** (§5).

The design constraint that makes this safe: **the grammar can only express what the factory can
honestly evaluate.** There is no free-text rule box, no LLM-authored strategy, no arbitrary
formula compiler. Every term is a closed-vocabulary token bound to a function that already
exists and is already tested.

---

## 2. The grammar (closed vocabulary — the Pat pattern)

Pat's discipline (`docs/pat-knowledge-contract.md`): a **closed vocabulary → deterministic
template**, never a free-form generator. The rule-lab reuses it exactly.

```
RULE := SELECT <universe>
        [ WHERE  <filter> [AND <filter>]* ]
        RANK BY <signal>
        TAKE    <n:5..50>
        HOLD    <horizon>
        [ VETO  <veto> [AND <veto>]* ]
```

Every token resolves 1:1 to a tested callable — **no token may be added without the function
existing first**:

| Slot | Closed vocabulary | Binds to |
|---|---|---|
| `<universe>` | `liquid500` · `midcap` · `smallcap` · `largecap` | `factory.build_tables()` universes |
| `<signal>` | `mom6` · `mom12` · `riskadj` · `accel` · `lowvolmom` · `delivmom` · `qualmom` · `pullback` | `factory.sig_*` (one function per token, no exceptions) |
| `<filter>` | `not_extended` (the `*_VAL` rule: excludes >200% / ~5y) · `min_liquidity` · `listed_on_asof` | `factory.not_extended()` + the PIT `security_master.universe_on()` join |
| `<n>` | integer 5–50 | `run_strat(top_n=)` |
| `<horizon>` | `monthly` · `quarterly` | `run_strat()` rebalance clock |
| `<veto>` | `cci_deterioration` · `mep_distribution` · `rating_downgrade` | the veto-only layers (D66) — **filters, never rankers** |

**Deliberately NOT in the vocabulary (and why):**
- **No arithmetic composer** (`(a*0.3 + b*0.7)`). Weight-tuning over a fixed history is the
  overfitting engine the whole ledger exists to prevent. Blends arrive as *named, pre-registered*
  tokens after a study, not as a slider.
- **No rupee constants.** Standing rule ([[ramana-working-principles]]): thresholds are
  percentiles / percentages, never `> ₹500cr`.
- **No entry/exit timing micro-language.** The measured exit LAW (ledger §07-14d/e) is
  *looser = better* (band-only 0.49 / trail5 0.49 ≫ tight; profit-takers worst). A timing
  DSL would sell precision the evidence says does not exist.
- **No single-stock verdicts.** The lab ranks a *cohort*; it never emits "this stock is a buy"
  (§6).

---

## 3. The gauntlet (mapping onto the existing evidence factory — reuse, don't rebuild)

A rule is evaluated by **composing modules that already exist**. The lab is an orchestrator, not
new math:

| # | Stage | Existing asset | What it contributes |
|---|---|---|---|
| 1 | **Pre-register** | `research/explosive_moves/prereg.py` (`gate_hash`, `register_all`, `verify`) | The compiled rule + its pass/fail gate are hashed **before** the run — `sha256(RAW __doc__)`. First registration wins; amending = a new study. ⚠ `ast.get_docstring()` DEDENTS → different digest; hash the **raw** string ([[codex-external-review-workflow]]). |
| 2 | **Build tables** | `factory.build_tables()` | PIT panel; the `universe_on()` join keeps the rank universe point-in-time (D2-F1). |
| 3 | **Run** | `factory.run_strat()` + `slice_stats()` | Top-N, equal-weight, rebalance, **walk-forward halves 2012-18 vs 2019-26** — a rule must clear **BOTH halves** or it is noise. |
| 4 | **Placebo** | the `evlib` placebo pattern (`campaign_arcs.py` et al.) | The control that killed 5 lenses in week one and E-03 itself. **Observed must beat placebo p95** — not merely beat zero. |
| 5 | **Cost** | `cost_realism.py` (`side_cost`, `bench_buyhold`) | Turnover-real net returns. **Net is reported FIRST**; gross is a footnote (see the momentum row in §5 — gross 1.29 → net ~0.09). |
| 6 | **Capacity** | `cost_participation.py` (`capacity_breakpoint`, Almgren participation) | The ₹-AUM at which the edge dies. A rule with no stated capacity is not a result. |
| 7 | **Benchmark** | `bench_buyhold()` | **Nifty-500 buy-and-hold, net.** The bar every rule must clear (Sharpe ≈0.89 on the standard window). |
| 8 | **Ledger** | `docs/strategy-ledger.md` | Every decided run appends an entry — wins AND failures ([[record-and-remind]]). |

**Cheapness note:** stages 4–6 are what make this worth building. Stage 3 alone is the flat-cost
illusion machine. A rule-lab that stopped at stage 3 would *manufacture* the exact error the
ledger's biggest entries record.

---

## 4. The honest-verdict object (the ledger's vocabulary, not a new one)

The lab returns ONE object; the surface renders it verbatim. The verdict enum is the ledger's
own (per the failure-ledger contract), so a lab result can be **pasted into the ledger without
translation**:

```
RuleVerdict
  rule_text        "SELECT liquid500 RANK BY mom12 WHERE not_extended TAKE 25 HOLD quarterly"
  rule_hash        sha256(raw spec)            # the prereg chip the Trust page renders
  prereg_ref       registry id + registered_at # tamper-evident, --verify-able
  verdict          REJECTED | WEAKER-THAN-BENCHMARK | CONDITIONAL(<condition>) | NEW-BENCHMARK
  qualifier        descriptive-only | paper-only | flat-cost-only | fundable   # part of the verdict, never a droppable footnote
  numbers          net_sharpe (FIRST) · gross_sharpe · alpha · beta · maxdd
                   · half1 · half2 · placebo_p95 · observed · emp_p
                   · capacity_inr · ann_cost_pct · bench_net (0.89)
  ledger_citations [ <BLOCKING rows this rule matches, verbatim> ]     # §5 — may be non-empty even on a PASS
  provenance       module + commit + data window
```

**Rules the object enforces (not conventions — invariants):**
1. `verdict` may not be `NEW-BENCHMARK` unless `net_sharpe > bench_net` **in both halves** AND
   `capacity_inr` is stated AND `observed > placebo_p95`.
2. `qualifier` travels with the verdict forever. `flat-cost-only` is the C-BLEND lesson: 1.32
   became 0.17 @₹50cr, and the qualifier is the only thing that stops the 1.32 being re-quoted.
3. A missing stage = **no verdict**, not a partial one. (`t_cohort NaN` from thin feed depth is
   a *refusal to rule*, exactly as E-03 recorded.)

---

## 5. The BLOCKING wall — auto-cite before any run

**Binding:** when a compiled rule matches a known-dead shape, the lab **prints the matching row's
exact numbers before it runs anything**, and the citation is stapled into the result object. The
rule may still run (Ramana may have new evidence — new data, new regime, corrected methodology,
a changed constraint) — but it can never run *silently*. "Maybe it works now" is not new evidence.

Reproduced **verbatim** from `docs/strategy-ledger.md` § "❌ BLOCKING FAILURE MODELS" (2026-07-02);
that file stays canonical — if these ever disagree, the ledger wins:

| Failure model | Recorded result (2012-26, top-25 monthly, vs Nifty 500) | Why it blocks |
|---|---|---|
| **BOOK_YIELD (deep value / B-P)** | Sharpe 0.61-0.63 · **alpha −1.8%…−2.2% (NEGATIVE)** · **beta 1.54-1.56** · **MaxDD −82%** · fails BOTH halves | Negative alpha + −82% drawdown + high beta = a value-trap engine. **Never a production long-ranker.** The β≈1.54 + MaxDD≈82% alone stop us. |
| **EARN_YIELD (cheap on P/E)** | Sharpe 0.70 · alpha +0.4% · MaxDD −71% | No index-beating edge standalone; deep drawdown. |
| **QUALITY standalone** | Sharpe 0.76 · alpha ~0.0% · fails halves | Quality doesn't rank returns alone; only helps *attached to momentum* (QUAL_MOM). → C is a veto/filter, not a ranker. |
| **Momentum sold as a FUNDABLE strategy** | GROSS Sharpe 1.29 → **NET ~0.09, CAGR negative, MaxDD −69%** under realistic cost (~36%/yr, ~100%/mo turnover) | The headline Sharpe is a flat-cost illusion. Nothing beats Nifty-500 buy-&-hold (0.89) net of realistic cost. Momentum = a **gross selection/analytical lens**, not net alpha; any fundable form must be low-turnover (and is then defensive, not alpha). |
| ACCEL / PULLBACK / DELIV_MOM (standalone) | Sharpe 0.42-0.85, MaxDD −44%…−70% | Short-thrust chasing / dip-buying / delivery% added no standalone edge. |
| MEP-accumulation as alpha | Deflated-Sharpe DSR 0.45→0.36 when added | Descriptor-only; adds nothing. Do not re-test as alpha. |
| **PEAD tradeable book (event-time, 2026-07-05)** | ALL constructions fail: trailing net Sharpe **0.10**, no-delivery 0.02, **within-season 0.06** (pre-registered), HEDGED **−0.58**, 1.5× cost −0.32 — vs bench 0.85, both halves | Event drift is REAL descriptively (A-study SUE-Q5×DELIV-T3 CAR60 +7.62%, t_cohort 1.92) but no wrapper survives real-time ranks + costs + compounding; the within-season variant (the last untested cell) also failed. Descriptive event lens only (`pead_surface.py`). Do not re-attempt any PEAD book without beating these exact numbers under the same no-leak harness. |
| **Accumulation-footprint detector v1 (2026-07-05b)** | pre-registered gate **FAIL 1/4** (only trade-size cleared δ≥+0.20 vs both controls: +0.329/+0.250); 764/947 episodes had NO pre-public window (SEBI PIT T+2); n=54 usable | "Front-detect the insider from the tape" is structurally near-impossible in India at filing granularity. deliv_per showed ~no case elevation (δ≈+0.07) — consistent with MEP's alpha failure. Survivor: avg-trade-size ratio = descriptive column only. Follow-ups (campaign arcs E-04, disclosure drift E-03) require fresh pre-registration. |
| CCI credibility as a factor | Spearman ≈0; HIGH−LOW excess −10% @12m (inverse, survivorship) | FALSIFIED as a factor → descriptive/veto only. |
| **C-BLEND 50/50 as a FUNDABLE book (2026-07-05c)** | Flat-cost Sharpe **1.32** (recorded champion) → participation-cost **NET 0.52 @Rs25cr · 0.17 @Rs50cr · −0.30 @Rs100cr**; beats the index at NO AUM; H2 (honest window) 0.70 @Rs50cr < 0.89; ann cost 22%→86% | The 1.32 was **flat-cost only**. Monthly rebalance × mid-cap tilt (median capacity ~Rs38cr) makes Almgren participation impact fatal; the RISKADJ core is worse. C-BLEND stays a **descriptive/paper overlay** (D66 fence holds), never a fundable book. Only participation-fundable corner = quarterly large-cap **LOWVOL_MOM** (1.02 @Rs50cr, ~Rs100cr ceiling). Re-cost: `cblend_cost_recut.py`. |

**The corollary (the doctrine these failures prove):** *price strength is the only gross forward-return
engine; value/quality/credibility/accumulation are veto/filter/context layers, not rankers; and no
factor here is a fundable net-of-cost alpha vs the index.*

### 5.1 Grammar-token → BLOCKING-row trigger map

The match is on the **compiled rule's shape**, not on user wording:

| If the rule contains… | Auto-cite |
|---|---|
| `RANK BY` a value token (book-yield / earn-yield family) | BOOK_YIELD · EARN_YIELD rows |
| `RANK BY qualmom` **without** a momentum leg, or a quality-only rank | QUALITY standalone row |
| `RANK BY mom6\|mom12` + `HOLD monthly` + a fundable reading | Momentum-as-fundable row (**gross 1.29 → net ~0.09**) |
| `RANK BY accel\|pullback\|delivmom` standalone | ACCEL/PULLBACK/DELIV_MOM row |
| any MEP-accumulation term promoted from veto to rank | MEP row (DSR 0.45→0.36) |
| any results/PEAD event wrapper | PEAD row (net 0.10 · within-season 0.06 · hedged −0.58) |
| any insider/SAST footprint rank (incl. anything built on the LANE-G entity graph) | Accumulation-footprint v1 (FAIL 1/4, n=54) **+ E-03** (placebo p95 **+9.52% > observed +8.26%**, emp-p 0.085) |
| `RANK BY` a CCI/credibility term | CCI row (Spearman ≈0, HIGH−LOW −10% @12m) |
| a 50/50 C-blend shape at monthly + mid-cap tilt | C-BLEND row (1.32 flat → 0.17 @₹50cr) |

**The one recorded survivor to state honestly when it appears:** quarterly large-cap
**LOWVOL_MOM** — participation-fundable at 1.02 @₹50cr, ceiling ~₹100cr. It is the shape the
evidence *permits*, and the lab should say so rather than only saying no.

---

## 6. SEBI boundary (plan §3 — business research, not legal advice)

**User-directed analysis is analytics, not advice.** The rule-lab sits inside the SEBI (Research
Analysts) Regulations, 2014 reg. **2(1)(w)** exclusions the plan §3.1 validated — in particular
*statistical summaries of financial data of companies* and tools operating on the **user's own
criteria**. The load-bearing distinctions, which the design must not blur:

1. **Ramana composes the rule; the machine reports arithmetic.** The lab never originates a
   recommendation, a target price, or a personalized suitability view.
2. **Cohort statistics, never a single-stock verdict.** A ranked roster of a *rule the user wrote*
   is a screener output — the same posture as Screen+ / Classic Screens, which are already live
   and fenced. Plan §3's identified **gray zone is single-stock house scores**, and the lab stays
   out of it by construction (§2: no single-stock verdicts token).
3. **Personal-first (v1 = owner-only)** keeps it further from "distributing a research report"
   than anything already shipped: no third party receives the output at all.
4. **The compliance lexicon applies to its templates** — `tests/test_compliance_language_gate.py`
   must pass over every rendered string (the gate scans `src/web`+`src/pat`; a rule-lab renderer
   living there is auto-covered — if it lands in `src/automation`, mirror the lexicon test the way
   `tests/test_auto_analyst.py` does).
5. **The §3.5 trigger stands:** if a lab output is ever monetized publicly or turned into a
   distributed recommendation, that is the legal-opinion trigger — not a thing to decide inside a
   build session.

---

## 7. Surface sketch (personal-first) — SURFACE-PLAYBOOK checklist PRE-FILLED

Route **`/dash/rule-lab`**, owner-gated at v1 via the `tracker_gate.py` middleware pattern
(anonymous → a read-only demo rule + its verdict, exactly the tracker demo-book precedent, D-P0-6).

| # | Requirement | Pre-filled answer |
|---|---|---|
| 1 | Registry entry | `Lens("rule-lab", "Rule lab", "stock", "trust", "/dash/rule-lab")` — Trust altitude (it is an evidence surface, not a screen). ⚠ `lens_registry.py` is FORKED on the box → anchored insert, never scp |
| 2 | Durable mount | anchored insert in `v2_surfaces._ROUTER_SPECS` |
| 3 | Education minimum | `bottom_line()` = "Write a rule; we run it through the same gauntlet as our own studies and tell you honestly if it works." · `plain()` under the verdict card · `how_to_read_link()` · `gloss()` on every metric (net Sharpe, placebo p95, capacity, both-halves) |
| 4 | Honesty fence | `infographics.fence("not_reco")` → *"descriptive, not a recommendation"*. Verdict labels are ledger vocabulary (REJECTED / WEAKER-THAN-BENCHMARK / CONDITIONAL / NEW-BENCHMARK) — **never** buy/sell/add/avoid/ride/fade |
| 5 | Glossary keys | new terms → `docs/metrics-glossary.md`: `placebo p95` · `capacity breakpoint` · `both-halves` · `prereg gate hash` · `flat-cost-only`. **Words-first names** (the S153 `D/E` lesson: a name starting with a slashed symbol breaks Pat's speakable-lead adapter) |
| 6 | Pat registration | **DATA** flow — `src/pat/rulelab_flow.py`: "did my rule work / test my rule" → the latest verdict inline. Gate `tests/test_pat_coverage.py` fails the build otherwise (`docs/pat-knowledge-contract.md`) |
| 7 | Strategy doc | `docs/strategies/rule-lab.md` in the SAME commit + `strategies_view._PAGES` row + README matrix + **Origin: 🏠 HOUSE** (`test_every_served_page_declares_origin`) |
| 8 | Export | server-side `format=csv` on the roster + the verdict numbers (the `wolfe_trades_view.py` pattern) |
| 8b | URL state | the whole rule is URL-addressable: `?u=liquid500&rank=mom12&where=not_extended&n=25&hold=quarterly` — a shared URL reproduces the verdict exactly (and IS the prereg text) |
| 9 | Symbol links | roster cells → `/dash/stock?sym=` (`sym`, never `symbol`) |
| 10 | Home exposure | **deliberately NOT on home** at v1 — owner-only; record the why in the commit |
| 11 | Writes are POST | running a rule WRITES (prereg registration + ledger append) → **POST**, never a GET |
| 12 | State doc | PROJECT_STATE §Key-paths + §Decision-log same commit (the D97 gate) |

**Run-cost note:** a full gauntlet is a heavy compute pass, not a page render. v1 = POST → queue →
the verdict lands in the **Review Inbox** (`review_inbox.submit(kind='rule_verdict')`, LANE-D is
live) and the page reads the last verdict. This reuses the L5 layer instead of inventing a job
runner, and it puts every machine-produced verdict in front of a human by default. ₹0 — the
gauntlet is pure Python, **no LLM** (Guardrail #3: anything scheduled/compute-heavy stays
rule-based).

---

## 8. Build order (the session that retires this doc)

1. **The compiler** (closed vocab → a frozen spec string + `rule_hash`) + its token registry, with
   the §5.1 trigger map — tests first, `factory` untouched.
2. **The orchestrator** (stages 1–8 of §3) returning `RuleVerdict`; the "missing stage = no
   verdict" invariant is a test, not a comment.
3. **The inbox producer** (`kind='rule_verdict'`) — reuses LANE-D. ⚠ `review_inbox.submit()` does
   NOT commit the caller's conn and mid-batch DDL auto-commits → **commit per item** (the S153
   LANE-E lesson).
4. **The surface** per §7 (all 12 rows in ONE session — Guardrail #9).
5. **Ledger wiring** — every decided verdict appends an entry; failures BLOCK future re-attempts
   ([[failure-models-ledger]]).

**Open question for Ramana (not a build decision):** should a `NEW-BENCHMARK` verdict from the lab
auto-append to `docs/strategy-ledger.md`, or land in the inbox for his approval first? Default
proposal: **inbox first** — the ledger is canon, and canon should carry a human signature.
