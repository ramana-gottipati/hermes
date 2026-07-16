# PRE-REGISTRATION — the UNION signal, forward test

> **Class:** PRE-REGISTERED forward-test spec. Hashed and committed BEFORE any out-of-sample data is
> seen. The pass/fail criteria below are FROZEN — if they are edited after the forward window opens,
> the registration is void and any result is in-sample.
> **Registered:** 2026-07-16 (ledger §2026-07-16W). **Origin:** 🧑 RAMANA (RS architecture, the
> reversal + persistence theses) + 🏠 HOUSE (implementation, falsification).

## Why this exists

The session produced ~30 configurations. **Exactly one beat Nifty Next 50 in-sample on return, drawdown
AND beta together** — the UNION. But it was selected AFTER seeing 2005–2026 data, across many rounds, so
its 17.5% is a LEAD, not evidence (Codex 15R: "treat as a research lead, not proof"). Pre-registration is
the only honest way to convert it: freeze the exact rules now, judge them on data not used to build them.

## THE FROZEN SPEC (any change voids the registration)

**Universe & foundation.** NSE bhavcopy series EQ+BE+BZ, corporate-action ADJUSTED (`adjust.py`), the
runtime split-ratio quarantine (`quarantine.py`), liquid ≥ ₹5cr ADV measured on the PRIOR month, PIT
throughout, quarterly rebalance. Dead names realise −50%; vanished-but-alive are carried.

**Sector assignment.** Each stock → the sector index its trailing-500-day EXCESS returns correlate with
most (`sector_of` machinery). No membership table.

**The two component signals (a stock qualifies if EITHER fires — the UNION):**
1. **RSI-price + persistence:** price RSI(14) is above its own 50-day SMA, AND the stock beat its own
   sector index on ≥70% of the trailing quarter's days (consistency ≥ 0.70).
2. **6b oversold-RS recovery:** RSI(14) of the stock's RS line (stock ÷ own sector) was < 30 within the
   trailing ~60 days and has crossed back ≥ 30. (No consistency gate — 6b is a turn signal, mutually
   exclusive with persistence by construction; intersection = 9% invested, confirmed.)

**Construction.** Equal-weight the qualifying names, **top 60** by RSI strength. Each position gets 1/60;
**idle capital → the sleeve: Nifty Next 50 while Nifty 500 ≥ its 200-day SMA, else cash** (V17 mechanism).
**Trailing stop −20% from peak close, filled with 1% slippage.** Costs 0.15%/side. **NO market-stretch
throttle** (tested, 16W: it worsened every metric — the 2012–17 weakness is SELECTION, not sizing).

**Benchmark.** Nifty Next 50 buy-and-hold, same calendar. (Bar = 13.3% CAGR on 2006–2026.)

## IN-SAMPLE RESULT (2006–2026, for the record — NOT the test)

CAGR 17.5% · MaxDD −30.5% · ₹1 Cr → ₹26.04 Cr · beta 0.87 · alpha +6.8% · ~82% avg invested.
Walk-forward alpha: 2006–11 **+9.8%** · 2012–17 **−4.6%** · 2018–26 **+8.3%**. Known weak regime:
mid-cycle bull markets where a lower-beta momentum book lags a raging cap-weighted index; diagnosed as a
selection problem, not fixable by exposure sizing (16W).

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

The forward test is **every NEW quarter from 2026-07 onward** (plus, as a secondary hold-out, any genuinely
untouched historical window if one can be established). The union PASSES only if, over ≥ 8 forward quarters:

1. **CAGR > Nifty Next 50 buy-and-hold, net of the modelled 0.15%/side + 1% stop slippage.**
2. **The excess is NOT purely beta:** measured alpha > 0 with the forward beta reported (a higher CAGR at
   beta > 1.1 that vanishes on alpha is a FAIL).
3. **MaxDD not worse than Nifty Next 50's over the same forward window.**
4. **No single quarter drives > 60% of the total excess return** (guards against one lucky print).

Miss any of 1–3 → the union is DESCRIPTIVE-ONLY, never deployed. Criterion 4 failing → inconclusive, extend
the window. **These four are frozen as of the commit that lands this file.**

## What is NOT claimed

- Not that the union is deployable. It is a lead awaiting its own forward evidence.
- Not that 17.5% recurs. In-sample selection inflates it by an unknown amount; the forward CAGR is the only
  number that will count.
- Not personalized advice. Descriptive research on a paper portfolio, price-index benchmark (TRI re-cut
  still owed), no live capital implied.

## Canon

`docs/strategy-ledger.md` §§ 2026-07-16U (Dim 6 / 6b) · 2026-07-16V (the union) · 2026-07-16W (throttle
dead + this registration). Repro: `research/explosive_moves/cash_blend.py` (union), `cash_throttle.py`
(throttle), `dim6.py`/`dim6g.py` (the reversal battery). SHA-256 of this file recorded in the commit
message = the pre-registration seal.
