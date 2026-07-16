# PRE-REGISTRATION — UNION COMPOSITE-30, forward test (the FOURTH sibling)

> **Class:** PRE-REGISTERED forward-test spec, the fourth member of the union sibling family.
> Hashed and committed before any forward-window data exists; editing this file after the forward
> window opens voids it.
> **Registered:** 2026-07-16 (S173). **Origin:** 🧑 RAMANA (the 25%→30% CAGR directives, the RS
> theses, and the explicit selection of this spec as the lead) + 🏠 HOUSE (the levers,
> falsification, this registration).
> **GOVERNANCE — the family was REOPENED by owner decision (2026-07-16):** Ramana: *"Confirm
> COMPOSITE-30 as the lead and reopen the family.. register it."* This supersedes, by explicit
> owner authority, the family-closed clause frozen in `union-c40ra-prereg.md` (that sealed file is
> untouched; the supersession lives here and in ledger 2026-07-16AH).
> **Multiplicity disclosure:** FOUR specs are now registered on the same forward window (union
> `a9a14058…` · β14 `08b46199…` · C40RA `0715a0d9…` · this). Each added spec raises the odds that
> one passes by luck. Mitigations, unchanged: every spec faces ABSOLUTE criteria vs the benchmark
> (not a tournament), criterion 4 guards single-quarter luck, and one frozen family-adjudication
> rule picks at most one graduate.

## Why this exists

Selected through five recorded generations of in-sample search (ledger 16Y → 16AB → 16AE → 16AF),
each generation surviving pre-declared bars and honesty passes, with every rejected sibling walled
in catalog §G. Ramana confirmed it as the lead on 2026-07-16 with the drawdown trade-off
explicitly on the table (COMPOSITE-30's deeper MaxDD vs the A2-composite alternative, which
remains recorded IN FULL in `docs/strategies/union-ladder.md` as the lower-drawdown fallback,
registration-ready on his word).

**Epistemic status: a fifth-generation in-sample-selected lead.** Codex 15R applies at maximum
force. The forward window is the only judge; that is what this registration buys.

## THE FROZEN SPEC (complete and self-contained; any change voids the registration)

**Universe (checked each rebalance).** NSE bhavcopy series EQ + BE + BZ, corporate-action ADJUSTED
(`adjust.py`), runtime split-ratio quarantine (`quarantine.py`). **Liquidity floor, era-relative:**
a stock is eligible if its PRIOR-month average daily traded value is ≥ the month's floor, where the
floor = max( **₹1 crore**, that month's **(1 − 0.450)-quantile** of the ADV cross-section over all
ADV-reporting symbols ). The constant **P = 0.450** is FROZEN (derived once, 2026-07-16, as the
mean fraction of symbols clearing the legacy ₹5cr bar over the trailing 12 complete months); each
new month's floor value is computed PIT from its own cross-section at this frozen P. Dead names
realise −50% on delisting; vanished-but-alive names are carried.

**Sector assignment (PIT).** Each eligible stock maps to the one of the 16 NSE sector indices with
which its trailing-500-day EXCESS returns correlate most (≥100 paired observations); refreshed at
each calendar year's first rebalance.

**Signals — a stock qualifies if EITHER fires (the UNION):**
1. TREND: price RSI(14) > its own 50-day SMA, AND the stock beat its own sector index on ≥ 70% of
   the trailing quarter's trading days.
2. TURN ("6b"): RSI(14) of the RS line (stock ÷ own sector) was < 30 within the trailing ~60 days
   and has crossed back ≥ 30.

**Selection.** Exclude qualifiers whose trailing-250-day beta vs Nifty 500 exceeds **1.4** (min
150 paired daily observations; incomputable = kept). Rank the survivors by **RISKADJ** score =
(close ÷ close 126 trading days back − 1) ÷ (std-dev of daily returns over the trailing 63 days,
min 30 observations); incomputable ranks last. **Hold the top 30.**

**Weights — LET-WINNERS-RUN.** A retained name keeps its market-drifted weight from the prior
quarter, hard-capped at **5% of the book** (trimmed only above the cap). A new entrant receives a
**1/30** slot, funded from freed/idle capital (entrants are cut short if the book is full). A name
that leaves the ranked top-30, hits its stop, or dies exits fully.

**Idle capital.** While Nifty 500 ≥ its 200-day SMA: idle → Nifty Next 50. Otherwise: idle earns
the risk-free return (Nifty 1D Rate Index from 2016-06-23; flat 6.5%/yr before — the
`attribution.py` convention, frozen).

**Exits & costs.** Trailing stop −20% from each position's peak close, filled at the stop price
with **1% slippage**; costs **0.15% per side** on all turnover; **quarterly** rebalance (first
trading day of Jan/Apr/Jul/Oct); same-close feature/execution convention (the D5-F1 next-day
variant is reported beside it as the standing honesty check).

**Benchmark.** Nifty Next 50 buy-and-hold (price index until the TRI ingestion lands; both sides
move together at that recut). Beta/alpha measured vs Nifty 500 quarterly returns.

Repro: `research/explosive_moves/union_lab5.py` (the COMPOSITE-30 row, produced by the
pre-declared auto-compose rule) · stress rows in the same module.

## IN-SAMPLE RECORD (2006–2026, for the record — NOT the test; ledger 16AF)

**PR: CAGR 26.4% · MaxDD −31.7% · ₹1 Cr → ₹115.7 Cr · beta 0.82 · alpha +15.1%** · windows α
+14.6 / +5.8 / +18.2. **TR (dividend accrual, lower bound): 27.3% (₹1 Cr → ₹131.8 Cr)**; 2012-17
TR window 30.5%. Stress: @2% slip 24.8% · @3% slip 23.2% · next-day execution 25.2% ·
**worst-honest (lagged + 2% slip, TR) 24.4% / α+13.5 / MaxDD −36.3%.** Character (16AE carries):
small/mid-cap tilt in early windows; personal-scale capital only; institutional capacity untested
and presumed poor.

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

Over ≥ 8 forward quarters from 2026-07: (1) CAGR > Nifty Next 50 buy-and-hold net of the modelled
costs · (2) alpha > 0 with forward beta reported (excess purely from beta > 1.1 = FAIL) ·
(3) MaxDD not worse than Nifty Next 50's over the same window · (4) no single quarter > 60% of
the total excess. Miss 1–3 → DESCRIPTIVE-ONLY, never deployed; criterion 4 → inconclusive, extend.

**FAMILY ADJUDICATION (frozen; supersedes the three-way rule for the four-way case):** among the
four registered specs that PASS their own criteria over the same forward window, the one with the
highest forward ALPHA graduates; the others retire to reference status. If none pass → all
DESCRIPTIVE-ONLY.

## What is NOT claimed

Not that 26–27% recurs (five generations of selection inflate it by an unknown amount); not that
30% is achieved (the modern-era slices print above 30, the full period does not); not that the
drawdown stays at −31.7% (worst-honest already shows −36.3%); not personalized advice; not
institutional capacity.

## Canon

Ledger: 2026-07-16AF (the battery + stress) · 16AH (the owner decisions + this registration) ·
16AE (the era-floor base) · 16AB (C40RA) · 16Y (β14) · 16U→X (the union arc). Full-spec compendium
of ALL family members incl. the unregistered composites: `docs/strategies/union-ladder.md`.
Repro: `research/explosive_moves/union_lab5.py`. SHA-256 of this file is recorded in the landing
commit and ledger 16AH; the forward test runs this row beside the other three sealed siblings.
