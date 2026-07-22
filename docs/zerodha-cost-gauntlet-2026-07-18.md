# The Zerodha Real-Cost Gauntlet — factor baskets, the union family, and K30 capacity (2026-07-18)

> **Class: RESEARCH RECORD (permanent finding).** Registered in `docs/DOC_INDEX.md`. Ledger tag **16BC**.
> Companion investor deliverable: `Equity_Baskets_with_UNION_family_2005-2026.xlsx` (17 sheets, on Ramana's
> Downloads/Desktop). Everything here is measured on real NSE data 2005–2026; the engine reproduces the
> project's recorded figures to the decimal before any new number is trusted. No fabricated numbers.

## 0. What this session did (one paragraph)

Ramana asked, in effect: *does any of our equity-basket research actually beat a cheap index buy-and-hold once
REAL Indian (Zerodha) trading costs are applied?* We built a per-name cost gauntlet (liquidity-tier bid-ask
spread + slippage + itemised Zerodha delivery charges + capital-gains tax), validated it against the recorded
`cost_realism.csv` numbers, and ran it over 2005–2026 on (a) the seven factor baskets and (b) the five union
ladder books. **Finding: the factor baskets do NOT beat the index net of cost; the UNION family DOES** —
COMPOSITE-30 (K30) +17.8% and A2 +17.2% net vs the index +11.7% in-sample. Codex independently validated both
runs. K30 then passed an execution-lag check (+16.7% at T+1) and an AUM ladder placed its capacity ceiling at
**~₹25–50 crore** (personal scale). The only thing still owed is the sealed forward test on **2026-10-03**.

## 1. The cost model (the gauntlet)

Per traded name, per SIDE (as a fraction of the traded value):

```
side_cost = half the liquidity-tier bid-ask spread     (market impact — the dominant term)
          + slippage = 0.5 × ATR% of the name          (adverse execution)
          + real Zerodha delivery charges               (tiny)
```

**Liquidity-tier spreads (round-trip; half charged per side)** — from `strategies.COST_TIERS`:

| Tier | Daily traded value | Round-trip spread |
|---|---|---|
| T1 | < ₹5 cr/day | 1.5% |
| T2 | ₹5–25 cr/day | 0.6% |
| T3 | ₹25 cr+/day | 0.25% |

**Real Zerodha equity-DELIVERY charges (Codex-verified, current schedule):** brokerage ₹0 · STT 0.1% buy &
0.1% sell · NSE exchange txn **0.00307%**/side · SEBI 0.0001%/side · stamp 0.015% buy-only · GST 18% on
(brokerage+exch+SEBI) · DP **₹15.34**/scrip on sell. **Total explicit Zerodha cost ≈ 0.22% round-trip
(~0.2%/yr) — negligible.** (Codex corrected two figures: NSE txn 0.00297→0.00307%, DP ₹15.93→₹15.34.)

**Capital-gains tax (added on Codex's advice):** short-term (<1yr) **20%** (post 23-Jul-2024; was 15%),
long-term **12.5%** above ₹1.25L. Shown as an illustrative after-tax column (20% STCG on positive years, since
these books hold <1yr). Churny books realise short-term gains every year; buy-and-hold defers tax for decades.

**AUM-sized impact (used only for the K30 capacity ladder)** — `cost_participation.py` square-root law:
`impact_ps = 0.6 × (66-day vol) × √(clip/ADV)`, capped at 10% of ADV/day, plus a days-to-fill timing penalty.

**The key mechanism, stated once:** the cost that matters is **market impact × turnover**, NOT brokerage.
Zerodha's cheap charges (~0.2%/yr) do not rescue a high-churn strategy — the price you move against yourself in
less-liquid names, times how often you trade, is what decides survival.

## 2. Validation (proof the engine is intact)

Reusing the exact recorded engines, flat-cost mode reproduces the recorded figures to the decimal:
- Factor side (`cost_realism.py` reuse): risk-adj momentum monthly = **−1.3%** (recorded −1.5%), low-vol
  momentum quarterly = **+13.2%** (recorded +13.3%).
- Union side (`union_ladder_val.py`, sealed protocol 37c28824): flat mode reproduces every sealed PR CAGR —
  U 17.5→17.3 · B14 18.1→17.9 · C40 21.0→20.8 · A2 25.5→25.5 · K30 26.4→26.4.

Universe is **survivorship-clean**: all 4,236 NSE EQ symbols that ever traded, including 1,061 that later
delisted — the screen picks from stocks that existed then, not just today's survivors.

## 3. Factor baskets — none beat the index net of cost (₹1 crore, 2005–2026)

| Strategy (stable→aggressive) | Gross | Flat-cost | **Net (Zerodha)** | ₹1cr → | Worst drop | Cost/yr |
|---|---|---|---|---|---|---|
| Pure Low-Volatility (qtr, large-cap) | 14.7 | 12.6 | **+7.6%** | ₹4.63cr | −41% | 6.0% |
| Low-Vol Momentum "STEADY" (qtr) | 20.7 | 18.8 | **+11.0%** | ₹8.89cr | −61% | 8.8% |
| Risk-adj Momentum (qtr) | 22.9 | 19.3 | **+5.2%** | ₹2.88cr | −79% | 15.5% |
| Low-Vol Momentum (monthly) | 20.3 | 16.7 | **−1.3%** | ₹0.75cr | −67% | 21.0% |
| Pure Momentum 6m (qtr) | 20.9 | 17.5 | **+1.7%** | ₹1.42cr | −84% | 17.4% |
| Pure Momentum 6m (monthly) | 28.4 | 22.2 | **−13.4%** | ₹0.05cr | −98% | 40.3% |
| Risk-adj Momentum (monthly) | 28.6 | 22.1 | **−10.9%** | ₹0.08cr | −96% | 37.6% |
| **Nifty 500 buy & hold** | — | — | **+12.5%** | **₹12.72cr** | ~−60% | 0 |

**Read:** the best factor basket (STEADY, +11%) still trails the index (+12.5%) net of cost. Every "20–28%"
figure is gross/flat and collapses; the monthly momentum books destroy capital (₹1cr → ₹5–8 lakh). The single
most striking illustration: the same fast risk-adj book shows ₹71cr under pretend-cheap cost and ₹0.08cr under
real cost — the entire gap is trading cost.

## 4. The union family — SURVIVES the same gauntlet (₹1 crore, 2005–2026)

| Book | Sealed (flat) | **Net (gauntlet)** | ₹1cr → | Worst drop | After-tax | Cost/yr |
|---|---|---|---|---|---|---|
| Union (RS turn ∪ RS trend, top-60) | 17.5→17.3 | **+11.5%** | ₹9.07cr | −38% | 8.4% | 5.6% |
| β14 (+beta-cap 1.4) | 18.1→17.9 | **+13.1%** | ₹11.98cr | −28% | 9.9% | 4.7% |
| C40 (risk-adj, top-40) | 21.0→20.8 | **+14.8%** | ₹16.35cr | −33% | 11.4% | 5.7% |
| **A2 (composite top-40 + sleeve)** | 25.5→25.5 | **+17.2%** | ₹24.99cr | −33% | 13.4% | 7.5% |
| **K30 = COMPOSITE-30 (LEAD)** | 26.4→26.4 | **+17.8%** | ₹27.77cr | −38% | 14.0% | 7.7% |
| Nifty 500 buy & hold (same window) | — | +11.7% | ₹9.38cr | — | — | 0 |

**Read:** under the IDENTICAL gauntlet that crushed the factor baskets, **K30 (+17.8%) and A2 (+17.2%) beat the
index (+11.7%) by ~+6pp/yr net, in-sample**, with drawdowns (−33 to −38%) roughly index-like rather than
catastrophic. This is the FIRST thing in the estate that survives the harsh real-cost test. Why: quarterly (low
churn), more-liquid names, trailing stops + let-winners-run — exactly the properties that keep cost down (K30
cost 7.7%/yr vs the fast baskets' 20–40%).

## 5. K30 robustness — execution lag + AUM ladder

**Execution-lag (trade at next session, not the signal close):** same-bar +17.8% → **T+1 +16.7%** (₹22.97cr,
−40%). Costs ~1.1pp/yr; the edge is NOT a same-bar-fill artifact.

**AUM ladder (square-root participation impact) — the capacity curve:**

| Money deployed | Net CAGR | ₹1cr → | Median participation | Days to fill | Worst drop |
|---|---|---|---|---|---|
| ₹5 cr | +22.1% | ₹56.8cr | 1.1% | 1 | −36% |
| ₹25 cr | +16.6% | ₹22.5cr | 5.4% | 1 | −42% |
| ₹50 cr | +12.5% | ₹10.8cr | 10.9% | 2 | −45% |
| ₹100 cr | +7.0% | ₹3.9cr | 21.8% | 3 | −59% |
| ₹200 cr | −0.3% | ₹0.9cr | 43.6% | 5 | −83% |
| ₹500 cr | −12.8% | ₹0.06cr | 108.9% | 11 | −97% |
| ₹1,000 cr | −25.2% | ₹0.00cr | 217.8% | 22 | −100% |

**Capacity ceiling ~₹25–50 crore.** Below ₹25cr a clear edge (16–22%); ~₹50cr it fades to the index; above
that the edge is gone and by ₹200cr your own trading destroys the return. **K30 is a PERSONAL-SCALE strategy** —
viable in-sample for Ramana's own capital, not an institutional product. (At ₹5cr the participation model gives
+22.1%, higher than the AUM-blind +17.8%, because 0.5×ATR is a harsh naive-market-order proxy; a small patient
account's honest range is ~18–22%.)

## 6. Codex independent validations (both confirmed)

- **Factor baskets (Codex re-ran + recomputed independently):** Codex re-ran the backtest on the box AND
  independently recomputed each net CAGR and ₹1cr value from the raw yearly returns — all 8 reproduce to the
  decimal (STEADY 11.0→11.02% · monthly momentum −13.4→−13.39%). Verdict: numbers trustworthy; the "<20% net ·
  best 11% (STEADY) · below the index 12.5%" conclusion is correct — and if anything STRENGTHENED, because the
  caveats it raised (T+1 timing, omitted held-name reweight cost ~7.5–35%/yr one-way, punitive 0.5×ATR slippage)
  all push strategy nets DOWN, not up. It corrected the schedule (NSE txn 0.00307%, DP ₹15.34 — the stale
  `bt_zerodha.json` display block trued up 2026-07-20) and flagged capital-gains tax (now added).
- **Union gauntlet (re-ran it independently):** reproduced the table exactly (flat = seals, K30 17.8/A2 17.2,
  bench 11.7). Verdict: "the sealed engine appears intact and, under this per-name Zerodha + 0.5×ATR gauntlet,
  A2 17.2% and K30 17.8% beat the Nifty 500 index (11.7%) in-sample." Correct wording: **"in-sample survivor
  under an AUM-blind harsh slippage gauntlet, pending the sealed 2026-10-03 forward test."** Caveats: AUM-blind
  (personal-scale, not institutional-capacity proof); the equal-weight books (U/B14/C40/A2) slightly undercharge
  continuing-name rebalance drift → their net is mildly optimistic, K30 (drift-weighted) is charged correctly.

## 7. Bullish-sector / strong-stock screen (live, 2026-07-17) — the original ask

The narrow index = **Nifty Next 50** (+4.3% 6m, beating big-cap Nifty 50 −5.3%). **219 of 497** Nifty 500 stocks
beat it over 6 months. Leadership:
- **Top-down (sector RS):** Pharma / Healthcare are the steady leaders (strong on 3m, 6m AND 12m); Realty
  (+16.7% 3m), Defence, Chemicals are sharp recent surges.
- **Bottom-up (biggest individual winners):** overwhelmingly the **Power / Electricals / Capital-goods /
  Defence** complex + renewables/EV + EMS (HFCL +213%, CPPLUS +161%, CEMPRO +139%, POWERINDIA +98%, ADANIENSOL,
  CGPOWER, BHEL, THERMAX, ABB, DATAPATTNS, APARINDS, RRKABEL…). A low-turnover "own the leaders, let them run"
  screen does NOT get eaten by the cost problem the way a monthly-churn strategy does.

## 8. Status, caveats, and what is owed

- ✅ K30 reproduces its seal (validated + Codex-checked) · beats the index net of the gauntlet (+17.8%) ·
  survives T+1 execution (+16.7%) · capacity ceiling measured (~₹25–50cr).
- ⚠ IN-SAMPLE (2005–2026, the design window). The ~17.8% is net-of-cost, NOT net-of-selection — deflate for
  selection and the honest forward expectation is lower.
- ⚠ EQUAL-WEIGHT union books (U/B14/C40/A2) slightly undercharge reweight drift → mildly optimistic; K30 clean.
- ⚠ Personal-scale only; ETFs still sit in the union universe (owner-gated exclusion pending, per `task_7a70ad77`);
  the last quarter's roster shows liquid/cash ETFs at the input-closed boundary.
- ⏳ **OWED: the sealed forward test on 2026-10-03** — the one thing no backtest can settle. Then: an AUM-ladder
  recut for any non-personal use, and the EW-sibling reweight-charge fix if those books are pursued.

## 9. Reproduce

Analysis scripts committed under `research/explosive_moves/gauntlet/`. On the box:
```
# factor baskets:   PYTHONPATH=/opt/hermes:/opt/hermes/research .venv-research/bin/python /tmp/bt_zerodha.py
# union gauntlet:    cd research/explosive_moves && ... python union_gauntlet.py /opt/hermes/data/hermes.db
# K30 lag + AUM:     ... python union_k30_checks.py /opt/hermes/data/hermes.db
```
The workbook is rebuilt by `build_workbook.py` from `bt_zerodha.json` + `union_gauntlet.json`.

## 10. Follow-on — improving the R logic (2026-07-22, ledger 16BD)

Ramana asked to lift CAGR / cut drawdown without repeating dead ideas. Three candidates, all tested on the
gauntlet above:
- **C — hold winners longer → KEPT + SEALED (K30-HOLD).** Retain a held name while it stays in the top-60
  (2× the 30 held); refill from top-ranked non-held. K30 net **17.8→19.0%** (₹1cr 27.6→33.6cr), worst-drop
  **−38% unchanged**. Robust: net gain positive at EVERY band 40–60 (+0.6 to +1.2pp), drawdown pinned
  throughout — not a lucky threshold. Lifts gross too (better selection, not just cost). Sealed as the 5th
  union sibling, `docs/prereg/union-k30-hold-prereg.md` (sha256 `e6994c19…`), forward-judged 2026-10-03+.
- **C on A2 → ALSO SEALED (A2-HOLD, the lower-drawdown variant).** Same 2×-holdings band (top-80) on A2's
  equal-weight top-40 base: net **17.2→18.6%** (₹1cr 25.0→31.5cr), worst-drop **−33% unchanged**; robust
  across bands 60–90 (+1.1 to +1.6). `docs/prereg/union-a2-hold-prereg.md` (sha256 `17e0dd1a…`). ⚠ EW
  undercharge (16BC) → mildly optimistic net; A2-HOLD's case is the shallower drawdown, not a higher net than K30-HOLD.
- **B-proxy — price-crash filter → BURIED (inert).** Removed zero names/rebalance: momentum already avoids
  just-crashed stocks. Zero effect on net or drawdown.
- **B — governance blow-up filter → FORWARD-ONLY.** Pledge/promoter-sell/surveillance/insider feeds have no
  point-in-time history before ~Nov-2025; can't be backtested, only run live from now. Intent sound, evidence missing.

Runners (additive, sealed engine untouched): `research/explosive_moves/gauntlet/build_c_bproxy.py` (toggled-rule
variant) + `build_band_sweep.py` (robustness sweep).
