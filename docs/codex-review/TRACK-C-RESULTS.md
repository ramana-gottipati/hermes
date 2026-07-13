# Track C — backtest-bias verification + restatement (VPS runs)

> **Lifecycle: TRANSIENT-CAMPAIGN.** Records the on-VPS verification of the P0 integrity findings
> (leakage that could inflate recorded ledger/OOS numbers). Fold the durable restatements into
> `docs/strategy-ledger.md` + the strategy pages, then retire. All runs read-only against the live
> archive (`/opt/hermes/.venv-research/bin/python`, `nice`d, no DB writes, no service touches).

## 🏁 Overarching verdict (all 4 P0 integrity leaks — VERIFIED on the VPS, 2026-07-14)

**Every leak Codex flagged is REAL, but every one is MINOR — none overturns a recorded conclusion.**
Each verification first reproduced the recorded number (validating the harness), then measured the bias.
A couple of recorded numbers are mildly optimistic (RISKADJ flat-cost 1.13→1.09), but the qualitative
verdicts — **descriptive-only**, **not-fundable-net-of-participation-cost**, **Wolfe IN-SAMPLE-ONLY**,
**CCI falsified** — all hold. The honesty framework is robust: the leaks are worth fixing in code
(correctness), but the recorded science stands.

| Item | Leak | Verified impact | Conclusion |
|---|---|---|---|
| **D5-F1** | same-close rebalance peek | RISKADJ 1.13→**1.09** (−0.04 Sharpe) | minor; fundability verdict unaffected |
| **D4-F2** | Wolfe OOS full-history universe | BULL **+4.18%** (incl) vs +4.69% (nifty500) | universe NOT inflating; verdict identical (IN-SAMPLE-ONLY) |
| **D6-F2** | CCI period-vs-report date | leak real; series already falsified | CCI stays descriptive-only regardless |
| **D5-F6** | `deliv_qty_trend` raw-qty | +0.09 Sharpe to QUAL_MOM; ~0 to DELIV_MOM | minor; split-part a small subset |

## D5-F1 — same-close rebalance peek (`factory.py`) — VERIFIED · quantified · MINOR (2026-07-13, VPS)

**The leak (confirmed by reading VPS `factory.py:70-94`):** in `build_tables`, selection features
(`mom6`, `vol`, …) are computed from `ac[i0]` (the rebalance day's close) **and** the forward return
enters at that same close (`fwd = ac[i1]/ac[i0] − 1`). So the model selects on a bar it also transacts
on — a same-bar peek.

**Verification method:** a read-only harness that imports the live `factory` module, reproduces the
recorded run under the current convention, and re-runs an honest **1-day execution lag** (features stay
at `i0`; enter at `i0+1`, exit at `i1+1`). The current path **reproduces the recorded numbers exactly**
(RISKADJ Sharpe **1.130** = `out/strategy_leaderboard.csv`; bench Nifty500 **0.899** ≈ recorded 0.89) →
the harness is faithful, so the delta is the bias alone.

| Signal (5cr, top-25 monthly, net) | Current (leaky) Sharpe | Honest (lag+1) Sharpe | Δ |
|---|--:|--:|--:|
| RISKADJ | 1.130 | 1.087 | **−0.043** |
| QUAL_MOM | 1.076 | 1.039 | −0.038 |
| LOWVOL_MOM | 1.000 | 0.973 | −0.027 |
| MOM12 | 1.037 | 1.042 | +0.005 |
| MOM6 | 0.857 | 0.855 | −0.001 |

**Verdict:** the same-close peek is **real but MINOR (~0.03–0.04 Sharpe** on the momentum signals),
**not a result-overturning leak.** RISKADJ 1.13→1.09 still clears the 0.90 hurdle; ordering preserved.
It only touches the **flat-cost gross** Sharpes — the ledger's binding conclusion ("nothing is fundable
net of realistic participation cost") is **unaffected** (the participation model already collapses these
to <0.2, so a −0.04 flat-cost nudge changes nothing).

**Restatement (to fold into `strategy-ledger.md`):** annotate the Tier-1 flat-cost Sharpes as carrying a
**~0.04 same-close-execution optimism**; the honest lag-1 RISKADJ = **1.09** (was 1.13). Recommend the
code fix (enter `i0+1`) land in `factory.py` + `overlay_experiment.py` + the cost recuts so future runs
are lag-correct; the *fundability* verdict does not move.

## D4-F2 — Wolfe OOS `inclusive()` full-history universe — VERIFIED · NOT result-changing (2026-07-14, VPS)

**The leak (confirmed):** `phase1_tradesim.inclusive()` is `SELECT symbol FROM bhavcopy_rows … GROUP BY
symbol HAVING COUNT(*)>=500 ORDER BY AVG(value) DESC LIMIT 300` — top-300 by **lifetime-average value
over the full 2004–2026 history**, applied to all test years. Future-informed (a name liquid only
post-2020 can enter the universe used to pick 2015 waves). The code comment mislabels it "point-in-time"
— that comment is WRONG and should be corrected.

**Re-ran `phase2_oos.py --universe both`** (reproduces recorded: inclusive winner ALL medNet +0.68% ≈
recorded +0.81%, BULL +4.18% ≈ +4.4%):

| winner-profile medNet | inclusive (future-informed top-300, PRIMARY) | nifty500 (survivorship-biased) |
|---|--:|--:|
| ALL | +0.68% | +1.49% |
| **BULL** | **+4.18%** | +4.69% |
| BEAR | −1.40% | −0.28% |
| verdict | **IN-SAMPLE-ONLY (BEAR fails)** | **IN-SAMPLE-ONLY (BEAR fails)** |

**Verdict:** the future-informed universe does **NOT inflate** the edge — `inclusive` is *more*
conservative than the survivorship-biased `nifty500`, the BULL selection edge (~+4.4%) is robust across
both universe definitions, and the overall verdict is **identical** either way. A true per-date PIT
universe would land in the same ~+4% ballpark. **Fix = correct the mislabeled comment** (optionally add
a per-date-trailing-value universe as a third sensitivity); the descriptive-only status is unchanged.

## D6-F2 — CCI period-vs-report-date leak — VERIFIED · no conclusion change (2026-07-14, VPS)

**The leak (confirmed at `cci_series.py:153`):** `if p["res"] and p["res"] <= tym:` counts a promise as
"knowable by T" when its `resolved_period` (the period *end*, e.g. FY2024 → 2024-03) ≤ T. But the actual
only becomes public when results are **reported** (~1–2 months after period end), so credibility points
are dated too early (`concall_settle` stores `resolved_period`, not a report/knowable date).

**Verdict:** the leak is real (dates ~1–2 months optimistic), but **CCI is already FALSIFIED as a factor
and used descriptive-only** (HIGH−LOW −10%@12m inverse, survivorship-confounded). Fixing the date (shift
knowable later) only makes an already-non-predictive series marginally more conservative — it cannot
rescue or invert CCI's status. **No live conclusion changes.** Proper fix = store a `report_date` /
`resolved_knowable_date` on settlement and key `credibility_series` on it (correctness for any future
PIT use); folded as a code TODO, not a ledger restatement.

## D5-F6 — `deliv_qty_trend` raw-quantity → value — VERIFIED · MINOR (2026-07-14, VPS)

**The leak:** `deliv_qty_trend` (in `embase` feats, used by DELIV_MOM 0.5w + QUAL_MOM 0.3w) is a trend of
raw delivered **share count** — split-sensitive across time (a split multiplies the count with no
economic change). Should be delivered **value** (`qty × close`, split-invariant).

**Quantified the feature's whole contribution** (5cr, top-25 monthly, net; current convention):

| Signal | with `deliv` | without `deliv` | Δ |
|---|--:|--:|--:|
| QUAL_MOM | 1.076 | 0.988 | +0.088 |
| DELIV_MOM | 0.852 | 0.857 (=pure mom6) | −0.005 |

**Verdict:** the split-sensitive feature contributes only **~0.09 Sharpe** to QUAL_MOM and **nothing** to
DELIV_MOM (consistent with the recorded "delivery% added no standalone edge"). The split-contamination is
a *subset* of that already-small contribution (splits are rare), so switching to delivered value is a
clean correctness improvement but **not result-changing** — QUAL_MOM stays ~1.0–1.08, DELIV_MOM stays a
failure. **Fix = compute a delivered-value trend in `embase` feats and swap it into DELIV_MOM/QUAL_MOM.**
