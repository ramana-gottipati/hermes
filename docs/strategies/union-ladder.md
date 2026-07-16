# The UNION FAMILY LADDER — every configuration IN FULL (specs + all recorded numbers)

> **Class: LIVING compendium (Ramana, 2026-07-16: "Record each item in full rather than only as
> you add it, so that all data are in place").** Every union-family configuration stands here
> COMPLETE — full ruleset and every recorded number — so nothing requires chasing deltas across
> ledger entries. Result numbers are transcribed from the ledger (the append-only source of
> truth); on any discrepancy the ledger wins. Specs of SEALED members are duplicated here for
> convenience only — the sealed prereg files are definitional.
> **Status flags:** 🔒 SEALED (pre-registered, forward-tested 2026-10-03+) · 📋 RECORDED (full
> record, unregistered; registration-ready on Ramana's word) · ❌ REJECTED (walls; catalog §G).

**Shared machinery (every member, verbatim across the family):** NSE bhavcopy EQ+BE+BZ,
corporate-action adjusted (`adjust.py`), split-ratio quarantine (`quarantine.py`), PIT sector
assignment by trailing-500d excess-correlation to the 16 NSE sector indices (yearly refresh),
UNION signals — TREND: price-RSI(14) > its 50-SMA AND ≥70% trailing-quarter consistency vs own
sector · TURN "6b": RSI(14)-of-RS < 30 → ≥ 30 in trailing ~60d — quarterly rebalance (first
trading day Jan/Apr/Jul/Oct), trailing stop −20% from peak close @1% slip, 0.15%/side costs,
dead names −50%, same-close convention (D5-F1 next-day variant = the standing honesty check),
benchmark Nifty Next 50 buy-and-hold PR (TRI recut owed), beta/alpha vs Nifty 500 quarterly.
Dividend accrual (TR rows) = parsed ₹-per-share ex-date credits at raw-price denominators —
a LOWER BOUND (97.7% coverage 2012+, ~34% before).

---

## 1. 🔒 THE UNION — seal `a9a14058…` (`union-prereg.md`; ledger 16U→X)

**Distinct rules:** universe floor ABSOLUTE ₹5cr prior-month ADV · no beta cap · engine-order
top-60 (documented-rank corrected 16Z) · equal-weight 1/60 · idle → Next-50 while Nifty 500 ≥
200DMA else 0% cash.

| window | CAGR | MaxDD | ₹1Cr→ | β | α | inv |
|---|---|---|---|---|---|---|
| FULL 2006-26 PR | 17.5% | −30.5% | 26.04× | 0.87 | +6.8% | 82% |
| FULL TR | 18.1% | −29.3% | 29.19× | 0.87 | +7.4% | |
| 2006-11 | 19.0% | −27.9% | 2.60× | 0.77 | +9.8% | 67% |
| 2012-17 | 16.5% | −16.2% | 2.32× | 1.42 | −4.6% | 80% |
| 2018-26 | 18.1% | −22.9% | 3.95× | 0.91 | +8.3% | 96% |

## 2. 🔒 UNION-β14 — seal `08b46199…` (`union-beta14-prereg.md`; ledger 16Y)

**Distinct rules:** union + EXCLUDE qualifiers with trailing-250d beta vs Nifty 500 > 1.4 (min
150 obs; incomputable kept). Engine-order top-60, EW, sleeve200, 0% cash.

| window | CAGR | MaxDD | ₹1Cr→ | β | α | inv |
|---|---|---|---|---|---|---|
| FULL PR | 18.1% | −24.7% | 28.84× | 0.74 | +8.4% | 69% |
| FULL TR | 18.7% | −24.1% | 32.39× | 0.74 | +9.0% | |
| 2006-11 | 17.4% | −23.0% | 2.42× | 0.67 | +9.3% | 53% |
| 2012-17 | 19.1% | −8.3% | 2.62× | 1.03 | +3.4% | 58% |
| 2018-26 | 18.8% | −15.7% | 4.14× | 0.82 | +9.2% | 90% |
| FULL @2% slip | 17.0% | −25.8% | 24.09× | 0.75 | +7.4% | |

Kill-checks recorded (16Y): cap plateau 1.3–1.6 all-positive; beta-window 125/500d robust;
dead-cash decomposition proves selection-not-sleeve (2012-17 −5.6% → +1.7% with idle at 0%);
29.0% of qualifier-quarters genuinely excluded, 0.38% kept-missing.

## 3. 🔒 UNION-C40RA — seal `0715a0d9…` (`union-c40ra-prereg.md`; ledger 16AB)

**Distinct rules:** β14 + rank capped qualifiers by RISKADJ (126d return ÷ 63d vol, min 30 obs;
incomputable last) + hold TOP-40 (EW 1/40). Sleeve200, 0% cash.

| window | CAGR | MaxDD | ₹1Cr→ | β | α | inv |
|---|---|---|---|---|---|---|
| FULL PR | 21.0% | −28.4% | 47.29× | 0.81 | +10.3% | 84% |
| FULL TR | 21.8% | −27.5% | 54.29× | 0.82 | +11.0% | |
| 2006-11 | 17.9% | −25.1% | 2.47× | 0.79 | +9.2% | 73% |
| 2012-17 | 20.9% | −8.3% | 2.84× | 1.04 | +4.3% | 78% |
| 2018-26 | 24.6% | −18.3% | 6.15× | 0.81 | +14.3% | 97% |
| FULL @2% slip | 19.7% | −29.8% | 38.34× | 0.83 | +9.2% | |
| FULL next-day (D5-F1) | 20.0% | −28.5% | 39.86× | 0.82 | +9.5% | |
| worst-honest (lagged+2%+TR) | 19.5% | −29.0% | 37.15× | 0.83 | +9.1% | |
| **2017+ slice (16AG table)** | **30.1%** | −17.9% | 11.37× | 0.85 | +16.4% | 100% |

## 4. 📋 A1-COMPOSITE (era-floor RAW + rf-cash) — recorded 16AE, unregistered

**Distinct rules:** C40RA + era-relative floor RAW (monthly (1−P)-quantile of the ADV
cross-section, P = 0.450 frozen; NO clamp) + idle in the bear state earns rf (Nifty 1D Rate Index
2016-06-23+, flat 6.5%/yr before — `attribution.py` convention). Top-40 EW.

| window | CAGR | MaxDD | ₹1Cr→ | β | α | inv |
|---|---|---|---|---|---|---|
| FULL PR | 25.6% | −32.0% | 100.43× | 0.82 | +14.5% | 99% |
| FULL TR | 26.4% | −32.0% | 114.91× | 0.82 | +15.2% | |
| 2006-11 | 20.2% | −32.0% | 2.75× | 0.69 | +11.3% | 98% |
| 2012-17 | 31.6% | −13.7% | 4.53× | 1.49 | +5.2% | 100% |
| 2018-26 | 27.5% | −17.9% | 7.44× | 0.80 | +17.5% | 100% |
| @2% slip | 24.0% | −34.4% | 77.58× | 0.83 | +13.1% | |
| @3% slip | 22.4% | −36.7% | 59.85× | 0.84 | +11.6% | |
| next-day | 24.7% | −34.8% | 87.25× | 0.82 | +13.8% | |
| worst-honest | 24.0% | −37.1% | 77.35× | 0.83 | +13.1% | |

⚠ Dominated by A2 (equal CAGR, 3–6pp worse MaxDD, half the tail ADV, 2012-17 realized β 1.49 vs
1.29; 2013 floor dips to ₹0.37cr — cost model not credible at that tail). Kept for the record.

## 5. 📋 A2-COMPOSITE (era-floor CLAMPED + rf-cash) — recorded 16AE; **the lower-drawdown
alternative, registration-ready on Ramana's word**

**Distinct rules:** as A1 but floor = max(**₹1cr**, monthly (1−P)-quantile), P = 0.450 frozen.
Top-40 EW, rf-earning bear-cash.

| window | CAGR | MaxDD | ₹1Cr→ | β | α | inv |
|---|---|---|---|---|---|---|
| FULL PR | 25.5% | −27.2% | 99.03× | 0.82 | +14.2% | 97% |
| FULL TR | not separately run; bounded ≥ 25.5% (accrual non-negative; A1 twin +0.8pp) | | | | | |
| 2006-11 | 22.2% | −27.2% | 3.01× | 0.73 | +12.8% | 93% |
| 2012-17 | 28.6% | −13.7% | 4.00× | 1.29 | +5.4% | 97% |
| 2018-26 | 27.4% | −17.9% | 7.37× | 0.82 | +17.1% | 100% |
| @2% slip | 23.9% | −29.3% | 77.21× | 0.83 | +12.8% | |
| @3% slip | 22.4% | −31.4% | 60.12× | 0.84 | +11.5% | |
| next-day | 24.6% | −29.4% | 85.40× | 0.82 | +13.6% | |
| worst-honest | 23.9% | −31.5% | 76.53× | 0.83 | +12.9% | |

Median pick-ADV ₹7.7–11.3cr (early/mid windows) vs C40RA's ₹27cr — the character change (16AE):
small/mid-cap tilt, personal-scale capital only. Its 2017+ slice = the 30.1% PR row in §3 (same
machinery on that window).

## 6. 🔒 COMPOSITE-30 — **THE CONFIRMED LEAD** (Ramana 2026-07-16), seal in
`union-composite30-prereg.md` (ledger 16AF/16AH)

**Distinct rules:** A2-composite + hold TOP-30 + LET-WINNERS-RUN weights (retained names keep
market-drifted weight, hard cap 5% of book; entrants 1/30 from freed/idle capital; exit on
deselection/stop/death). Everything else per the shared machinery + A2 floor + rf-cash.

| window | CAGR | MaxDD | ₹1Cr→ | β | α | inv |
|---|---|---|---|---|---|---|
| **FULL PR** | **26.4%** | **−31.7%** | **115.69×** | 0.82 | **+15.1%** | 99% |
| **FULL TR** | **27.3%** | −31.6% | **131.80×** | 0.82 | +15.8% | |
| 2006-11 | 24.7% | −31.7% | 3.36× | 0.73 | +14.6% | 97% |
| 2012-17 | 29.2% (TR 30.5%) | −13.1% | 4.10× | 1.32 | +5.8% | 99% |
| 2018-26 | 28.0% (TR 28.9%) | −18.1% | 7.69× | 0.78 | +18.2% | 100% |
| @2% slip | 24.8% | −33.8% | 89.19× | 0.83 | +13.7% | |
| @3% slip | 23.2% | −35.9% | 68.65× | 0.84 | +12.2% | |
| next-day | 25.2% | −34.1% | 94.84× | 0.81 | +14.2% | |
| **worst-honest** | **24.4%** | −36.3% | 83.50× | 0.83 | +13.5% | |

Component single-axis rows (16AF, on the A2-composite base): top-30 alone 25.9%/α+14.6 ·
let-winners-run alone 26.5%/α+15.1/DD −27.3 · rank-weights alone 26.3%/α+15.1/β0.79 (passed;
not composed — drift took the declared precedence).

## 7. ❌ The walls (full detail in catalog §G + the ledger)

Sector caps · RSI-rank both ways · beta-rank-asc · 6b threshold/combo/timeframe variants ·
quality tilt/drop (16Z) · ML Ridge-primary (16AA: 20.4 vs control 20.8 on 2017+) · **ML GBM-primary
over the era-floor pool (16AG: 21.1 vs the RISKADJ hand rule's 30.1 on 2017+; beta #1 feature all
three runs)** · trail widths ≠ 20 · sleeve-index swaps · cap-floor refill · vs-bench consistency ·
monthly cadence (4× confirmed) · cross-family LOWVOL_MOM blend, corr 0.83 (16AC) · throttle (16W) ·
inverse-vol sizing (16X — narrowed by 16AF to VOL-based sizing only) · AND-intersection (16V) ·
BE/fundamentals vetoes (16T).

## 8. Measurement estate — TRI RECUT COMPLETE (S174, ledger 16AI/16AJ)

**The honest hurdle: Nifty Next 50 TRI = 14.6%/yr full-period** (11.3 / 25.1 / 11.5 by window),
+1.3pp over the PR bar. Data: `niftyindices_hist.py` (the committed fetch tool; pipeline verified
to the paisa vs `index_rows`) → `research/data/niftyindices/` on the box: N500 TRI + NN50 TRI full
2005→2026, GS-10Yr 2011+, GS-Composite 2018+. **α vs Nifty 500 TRI (betas unchanged):** union
+5.8 · β14 +7.5 · C40RA +9.4 · A1c +13.5 · A2c +13.3 · **COMPOSITE-30 +14.2 (book-TR pairing
+14.8, windows +14.0/+5.0/+18.0)** — every member survives the honest recut; full table in ledger
16AJ. **B2 G-sec bear-sleeve: INERT on the lead (idle ~1%) and DATA-BOUNDED on the union (the
2008-09 bear predates the 2011+ G-sec series)** — a design option for future bears, no backtest
evidence, not adopted. rf convention frozen (1D-Rate + 6.5% proxy). Dividend accrual = lower
bound. Median pick-ADV print owed in the forward runner. Sealed criteria stay PR-vs-PR as frozen;
the TRI columns are reported beside every future judgment. Forward-test day (2026-10-03) runs ALL
SIX configs above; the FOUR sealed members are judged against their own criteria; family
adjudication picks at most one graduate (highest forward alpha among passers). Prod `index_rows` ingestion: **DONE S175 (ledger 16AK)** — 'Nifty 500 TRI' / 'Nifty Next 50 TRI' /
'Nifty GS 10Yr' / 'Nifty GS Compsite' live in prod, manifest entry `indexes_tri`, pull-on-demand
freshness via the committed tool.
