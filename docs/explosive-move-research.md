# Explosive-Move Reverse-Engineering — research log & pattern library

> **Status:** v3 (session 25, 2026-06-20) — corrected per Ramana + raw-first + artifact-fixed.
> **TRANSIENT** working document. **Retire condition:** once the headline "Launchpad" setup is wired
> into a live screener and folded into `PROJECT_STATE.md`, reduce to a pointer and `git rm` the bulk.
> **Binding (preserve-strategy-intent):** do NOT one-line the methodology or the pattern cards.
> **▶ NEXT SESSION: read `docs/explosive-move-NEXT-SESSION.md` FIRST** — research is done, 4 candidate
> strategies (S1–S4) are finalized; the next job is to BUILD THE BACKTEST ENGINE and run them.

Bottom-up, data-only discovery: find the stocks that made genuine explosive moves, walk back to the
data state *before* each move, mine the recurring fingerprints across ~149k events over 15 years, and
keep only what survives **out-of-sample**. Reproduce: `research/explosive_moves/run_all.py`
(events → features → mine → validate → sensitivity); offline (production `hermes.db` read-only).

## ⚠ Version history (what changed and why)
- **v1** defined the monthly event as a ≥20% thrust that retained ≥50%. **Ramana corrected this:** a
  genuine **+10% that is HELD** must count — a stock should not have to move 20%. → v2/v3.
- **v2/v3 monthly = rolling sustained +10%:** today's close ≥ +10% above the close ~1 month (22 td) ago.
  Rolling (any date), never calendar-bucketed — a move spanning a month boundary (e.g. +14% over three
  days that holds) is fully captured.
- **Raw-first:** the discovery rules are built from **raw price/volume/delivery data ONLY**. The house
  DVPT / `p_score` / accumulation-character battery is reported as **comparison only** (Ramana's call —
  "don't lean on my strategy; show me what the data finds on its own").
- **Artifact caught & fixed (rigor):** the v2 monthly *onset-flip* de-overlap mechanically coupled the
  base day's 1-day return to the sustained label (the forward-max boundary forces the month-end close to
  be the high when the base closes up → a fake "ret_1d>0 ⇒ ~100% sustained"). Fixed by **spacing-based**
  de-overlap (distinct non-overlapping rolling months). Post-fix the effect is a real, modest 68% vs 48%.

---

## TL;DR — what the data revealed (raw-only, OOS-validated)

1. **Explosive moves are preceded by MOMENTUM + VOLATILITY + TREND STRUCTURE**, not by a delivery surge.
   The strongest raw precursors: already rising (`ret_22d`, `ret_10d`, `ret_66d`), extended above the
   20/50/200-DMA, well off the 52-week low (`dist_low_252`), in a volatile/wide-range regime
   (`vol_66`, `atr14_pct`, `range_tight_66`; Cliff's δ up to **+0.80**). Dead, quiet stocks don't
   explode; already-alive, trending ones do.

2. **The counter-DVPT finding (Ramana's key question answered).** Reading the data on its own, **a rising
   delivery footprint is NOT what precedes explosive moves** — the validated rules prefer
   `deliv_qty_trend ≤ ~1.5` (delivery NOT surging) and *lower* delivery-%. The house DVPT premise
   (high delivery = accumulation = imminent move) is **not what the data nominates**; price-structure +
   relative strength are. DVPT's own RS-rank/accum-drift rank competitively but never *better* than the
   raw trend features — and they are the house construct, sparse before 2021. **The AI's independent
   read disagrees with the hand-made strategy, and it holds out-of-sample.**

3. **The "Launchpad" (validated, the prize).** For the corrected rolling **+10% sustained month**
   (base rate 11.1%), two raw archetypes:
   - **Momentum-continuation:** `ret_22d > 7%` AND volatility not expanding (`vol_ratio_22_66 ≤ 1.48`)
     AND some range (`range_tight_22 > 0.096`). **Hit 75%, lift 6.8×.** OOS: train 6.3 → **TEST 7.1, hit 80%.**
   - **Pullback-in-vol:** `ret_22d ≤ 7%` AND `vol_66 > 2.4%` AND a 1-day shakeout (`ret_1d ≤ −2.2%`).
     **Hit 49%, lift 4.4×.** OOS TEST 4.7.
   - **Combined:** hit **63.5%**, lift **5.7×**, **+24% avg over ~3 months**, **80% positive at 66 td**,
     **43% become ≥50% winners** (vs 3.7% for a random liquid day ⇒ ~12× edge). Holds **every year
     2012–2026**; **stronger in liquid names** (₹1-5cr 47% → ₹5-25cr 84% → **>₹25cr 86%**, momentum-only
     **97%** in >₹25cr). Not a microcap artifact.

4. **Sustain = STRENGTH / CONTROL ("genuine buying").** Among +10%-intramonth moves (base 53.5% hold),
   the ones that HOLD launch from a **calm, tight base** (`range_tight_22 ≤ 0.095`), **non-falling**
   (`ret_1d ≥ 0`, `consec_up ≥ 1`), **near the 52-week high**, **closing strong** (`close_strength_5`).
   OOS **85% sustain** (lift 1.6, both directions). Bounces off weakness fade; moves from strength hold.

---

## Methodology (rigor)

**Corpus.** NSE `bhavcopy_rows`, EQ cash, 2004→2026 (9.3M rows, 5,749 symbols). Events from 2012→2026
(≥1y prior history). Survivorship-safe: detected from the raw archive — **20–24% of event symbols are
delisted/renamed** (not in today's list); liquidity floor (₹1cr trailing-22-td median turnover) is
point-in-time, never a current allowlist.

**Three rolling event studies** (all any-date, de-overlapped to distinct episodes; CA-clean):
| Study | Event | n | sustained |
|---|---|---|---|
| daily | +10% in a day (raw close/prev_close, CA rows excluded) | 13,720 | — |
| weekly | +10% over a forward 5 td (adjusted close) | 52,791 | — |
| monthly | rolling +10% **held** over ~22 td (today ≥ +10% vs a month ago) | 69,746 reached | **37,343 (53.5%)** |

**Precursor fingerprint** snapshotted strictly as-of the look-back anchor (the base / day before the
move) — no look-ahead. For monthly the anchor is the **base of the rolling month** = where pre-move
accumulation would show. ~50 raw descriptors (returns, distance-from-highs, volatility/ATR/range,
volume dry-up/skew, **raw delivery battery**: deliv-qty/value trend, delivery-% level/percentile,
strong-delivery-day & big-delivery-day counts, trade-size & trade-count trend, close-strength,
new-high counts, 52w range position) + house DVPT (comparison) + CPR geometry.

**Honest hit ratios.** Positives = events; controls = a 1-in-10 random sample of quiet liquid days,
reweighted by K=10 to real prevalence. Lift is the load-bearing number (absolute hit runs optimistic vs
a clean-quiet baseline). **Discovery rules use RAW features only**; DVPT scored for comparison.

**Out-of-sample gate.** Depth-3 rule tree fit on a TRAIN era, frozen, scored on a held-out TEST era,
**both directions** (2012-19 ↔ 2020-26). Median imputation fit on train only. Success ratio (forward
ret_22/66/132, win rate, MFE/MAE, big-winner rate) computed on *test* events the rule catches.

---

## Ranked precursor catalog (raw, monthly-sustained; lift vs 11.1% base, δ = Cliff's delta)
| Raw precursor (as-of base) | dir | lift | hit | δ |
|---|---|---|---|---|
| `close_vs_sma20` (extended vs 20-DMA) | ≥ +7.4% | 5.9 | 66% | +0.05 |
| `ret_10d` (recent thrust) | ≥ +8.9% | 5.8 | 64% | +0.02 |
| `close_vs_sma200` | ≥ +34% | 4.9 | 55% | +0.21 |
| `ret_22d` (1-mo momentum) | ≥ +9.4% | 4.8 | 53% | +0.27 |
| `ret_66d` / `close_vs_sma50` | ≥ +33% / +13% | 4.6 | 51% | +0.20 |
| `dist_low_252` (off the lows) | ≥ +130% | 4.4 | 48% | +0.40 |
| `range_tight_66` (volatile/wide) | ≥ 0.49 | 4.3 | 48% | +0.60 |
| `vol_66` / `atr14_pct` | ≥ 3.6% / 6% | 4.1 | — | +0.59/+0.79 |
| **DVPT comparison:** `h_rs_rank` | ≥ 85 | 4.6 | 51% | — |
| **DVPT comparison:** `h_accum_price_drift_3m` | ≥ +28.6% | 4.5 | 50% | — |
| **delivery (raw):** `deliv_qty_trend` (NOT surging) | **≤ ~1.5** in the winning rules | — | — | — |

DVPT's RS-rank/accum-drift are competitive but never beat the raw trend battery, and are the house
construct. No *delivery-surge* feature is a top precursor — the opposite (no surge) is.

## Pattern library (validated multivariate)

### ★ M1 — Launchpad: Momentum-Continuation (monthly, the prize)
`ret_22d > 7% AND vol_ratio_22_66 ≤ 1.48 AND range_tight_22 > 0.096` — already up over the month, with
volatility *not* expanding (controlled), still ranging. **Hit 75%, lift 6.8×.** OOS train 6.3 → **TEST 7.1,
hit 80%**; success +27%/66d, 49% big-winner. Liquidity: ₹5-25cr 95% / **>₹25cr 97% hit**.

### ★ M2 — Launchpad: Pullback-in-Vol (monthly)
`ret_22d ≤ 7% AND vol_66 > 2.4% AND ret_1d ≤ −2.2%` — a volatile name (not yet trending) that takes a
1-day shakeout. **Hit 49%, lift 4.4×.** OOS TEST 4.7, hit 53%; success +24%/66d, 44% big-winner.
(Reverse-split sibling: `ret_22d>8% AND deliv_qty_trend ≤ 1.5 AND range>0.095` → TEST lift 5.7, hit 61%
— the counter-DVPT "no delivery surge" rule, OOS-confirmed.)

### W1 — weekly
`vol_66 > 2.4% AND vol_22 > 2.3% AND deliv_qty_trend ≤ 1.41` → hit 65%, lift 4.3× (base 15%). Volatile,
delivery not surging.

### D1 — daily
`close_vs_sma20 ≥ +5.9%` (extended off the 20-DMA) → hit 44%, lift 10.1× (base 4.4%). Pops come from
already-extended, volatile, trending names.

### S1 — "Will it hold?" (sustain filter)
Calm/tight base (`range_tight_22 ≤ 0.095`) + non-falling (`ret_1d ≥ 0`, `consec_up ≥ 1`) + near 52w-high
+ closing strong → **OOS 85% sustain** (base 53.5%). Use as a filter on M1/M2.

## What did NOT hold up
- **DVPT delivery-surge premise** — not a precursor of price moves (raw data prefers *no* surge). DVPT
  RS/accum-drift are confirmation-grade, not the prediction engine.
- **The v2 "ret_1d ⇒ sustained" result was an artifact** (onset-flip coupling) — caught and removed.
- **Absolute hit ratios run optimistic** (clean-quiet baseline) — trust lift / OOS / by-year / by-liquidity.
- **Not modeled:** costs, slippage, sizing, entry/exit. This is precursor discovery, not a P&L backtest.

## Full results — per-clue hit/lift/MFE/MAE + the 5 archetypes (full CSVs in out/)

**Per-clue table** (target = sustained +10% month, base rate 11.1%; MFE avg = max high / MAE avg = max low,
6-month forward, among the moves caught; n = events with the clue). Source: `out/results_table.csv`.

| Clue / pattern | Found by | n | Hit | Lift | MFE (max high) | MAE (max low) | ≥50% |
|---|---|---|---|---|---|---|---|
| Momentum-continuation (Launchpad) | core mining | 17,783 | 75% | 6.7× | +50% | −11% | 36% |
| Coiled-momentum (#22) | data-analyst lens | 8,586 | 70% | 6.3× | +53% | −11% | 39% |
| Either-Launchpad (union) | core mining | 31,629 | 63% | 5.7× | +47% | −13% | 33% |
| 1-mo momentum ≥9.4% | core mining | 21,226 | 53% | 4.8× | +52% | −11% | 38% |
| Strong trend >30% above 200DMA | core mining | 13,083 | 53% | 4.7× | +57% | −12% | 42% |
| Off the lows ≥130% above 52wL | core mining | 11,269 | 48% | 4.4× | +58% | −13% | 43% |
| Pullback-in-vol (Launchpad) | core mining | 13,846 | 49% | 4.4× | +43% | −17% | 29% |
| Wide range / high volatility | core mining | ~13,000 | 43–47% | 3.9–4.3× | +53–55% | −16–17% | 37–39% |
| Big-bite churn (bites in low-deliv) | financial+institutional lenses | 7,475 | 32% | 2.9× | +48% | −14% | 33% |
| Low delivery% (≤44) [counter-DVPT] | core mining (headline) | 26,312 | 21% | 1.9× | +43% | −14% | 29% |
| Coiled-spring / vol dry-up ❌ | quant-architect lens | 4,666 | 4% | 0.35× | +38% | −9% | 24% |
| Big-tickets + flat-crowd ❌ | financial-analyst lens | 9,224 | 10% | 0.86× | +43% | −12% | 29% |

**The 5 archetypes** (clustering of pre-move fingerprints; `out/clusters_monthly.csv`):

| Archetype | % of moves | n | Sustain | MFE | MAE | ≥50% |
|---|---|---|---|---|---|---|
| Powerhouse trend (established leader) | 12% | 8,352 | 55% | +58% | −14% | 43% |
| Volume ignition (fresh participation) | 8.8% | 6,122 | 58% | +50% | −10% | 36% |
| Steady uptrend continuation | 29% | 20,307 | 56% | +46% | −10% | 32% |
| Quiet range-bound base pop (weakest) | 35% | 24,384 | 52% | +37% | −11% | 23% |
| Oversold/downtrend bounce (riskiest) | 15% | 10,581 | 47% | +41% | −17% | 27% |

**Per-trade MAE/MFE QUANTILES (the corrected stop/target basis — NOT the means above):** M1/coiled WINNERS
barely dip — median worst-dip −2.5%, p25 ≈ −8% → **stop ≈ −10 to −12%** clears ~85–90% of winners (the
−6.3% cohort mean would stop out ~25–30% of winners). MFE fat tail: median winner +37–40%, **p90 +100%+**
→ trail, don't cap. M2 pullback is riskier (winner median dip −4.9%, all-trade p25 −24.6% → wider ~−15% stop).
Asymmetry overall ≈ +40–58% MFE vs −10–17% MAE (3–4:1). Control (vol-contraction) lowers MAE; chaos raises both.

## Observations log — multi-analyst pressure session, round 1 (session 25)

A 6-lens analyst panel (data-analyst, data-engineer, quant-architect, financial-analyst,
institutional-operator, retail-behavioral) generated **30 surprising-but-testable hypotheses**;
an adversarial verify stage + real-data probes (`probe.py`, `htest.py`) tested the survivors. A
server-side rate-limit storm killed ~25 verifier agents, so only **4 reached full adjudication** —
and **all 4 were REFUTED by the data.** That is the finding, recorded honestly.

| # | Hypothesis (lens) | Predicted | Data verdict |
|---|---|---|---|
| A | Close-location (CLP=(c−l)/(h−l)) RISES on flat days pre-move = stealth absorption (data-eng) | CLP↑, >0.6, rising | **REFUTED/reversed** — CLP *lower* pre-move (0.374 vs 0.398, δ −0.10), in every liquidity bucket; slope ~0 |
| B | Ticket-size DISPERSION (CV of value/trade) up while mean flat = "whale among minnows" (data-eng) | CV↑, mean flat | **REFUTED/reversed** — ticket mean *lower* (0.42×) AND CV *lower* (0.27 vs 0.33; price-free 0.26 vs 0.32, δ −0.23) = uniform small-ticket churn, not blocks |
| C | close-location × ret_1d≥0 synergy for SUSTAIN (data-analyst) | combo ≫ ret_1d alone | **REFUTED** — combo 0.674 vs equal-coverage ret_1d cut 0.658 (collinear); only sliver = a *down*-day closing strong helps sustain (δ +0.14 in ret_1d<0 subset) |
| D | Up-gap sign-flips by 252-day range position (quant-arch) | low-range gap MORE, top-range FEWER | **REFUTED/reversed** — up-gaps work *better* at top-of-range in hi-momentum names (lift 5.6 vs 4.0); just re-encodes momentum |

**What the refutations REINFORCE (the real, sharpened finding):** there is **no stealth
institutional-accumulation footprint before +10% moves in the EOD aggregate.** Pre-move the data
shows *broad, churny, small-and-uniform-ticket participation* — more trades, more volume, **lower**
delivery-%, **smaller & less-dispersed** tickets, weaker close-location — layered on an already-
trending stock. The earlier "big delivery-value days up 1.42×" spikes are **volume/participation-
driven, not block-driven** (ticket dispersion is *down*). The counter-DVPT story strengthens:
the pre-move tape is **crowd churn + momentum**, not quiet strong-hand accumulation.

**Confirmed-positive (htest):** a "big-delivery-value-day amid low overall delivery%" signature
(`big_deliv_days_10≥2 & deliv_per_22<50`) is over-represented 3.3× pre-move (lift 2.60) — but per
(B) it is volume-driven participation, not block accumulation.

**Implication for data depth (answers Ramana's Kite question):** if there *is* a real strong-hand,
the EOD OHLCV+delivery+trades aggregate does **not** reveal it (it's dominated by churn). The data
that *would* show named institutional buying is **free from NSE — bulk/block deals + FII/DII flows +
F&O OI** — NOT Zerodha Kite (intraday candles won't surface accumulation, and there's no 15y history).
Get Kite only for live execution/alerts. Priority next data = the free NSE institutional-footprint feeds.

(Note: the panel's other ~26 hypotheses were dropped by the rate-limit, not on merit — re-runnable.)

## Observations log — round 2: recovered-hypothesis data-tests (session 25)

The rate-limit killed 25 *verifier* agents but the 6 lens agents (all 30 hypotheses) were journaled;
recovered all 30 at zero cost from `subagents/workflows/.../agent-*.jsonl`. Tested the runnable ones
directly on data (htest, reweighted SUSTAINED-month, base 11.1%) — data > agent-opinion:

| Hyp | Test | Verdict |
|---|---|---|
| **#22 vol-contraction + momentum** (`vol_ratio<1 & ret_22d≥10%`) | **lift 6.28, hit 70%** (baseline 0.8%) | ✅ **CONFIRMED, strong** — "coiled momentum"; sharpens the Launchpad |
| **#7 coiled-spring** (`range_tight_22≤0.10 & vol_dryup_5_22≤0.8`) | **lift 0.35** | ❌ **REFUTED hard** — quiet/dry coiled bases precede FEWER moves (kills classic TA squeeze-lore) |
| #2 big-tickets+flat-crowd (`avg_trade_val_trend≥1.05 & trades_trend≤1.0`) | lift 0.86 | ❌ reversed |
| #11 order-fragmentation (`trades_trend≥1.3 & avg_trade_val_trend≤1.0`) | lift 1.35 | 🟡 weak |
| #6 delivery up-skew in no-surge (`deliv_qty_trend≤1.5 & deliv_updown_22≥2.5`) | lift 2.25, hit 25% | 🟡 mild real edge — *direction* of delivery matters even when level is low |
| #1/#12 stealth bites (`big_deliv_days_10≥2 & deliv_per_22≤45`) | lift 2.87, hit 32% | ✅ confirmed (but volume-driven, not blocks) |
| #24 delivery-compression (`deliv_trend≤0 & ret_22d≥8%`) | lift 4.13 | 🟡 mostly the momentum term; delivery adds little |

**Net:** the genuinely new keeper is **#22 (volatility-contraction × momentum, lift 6.3)** — vol *falling*
while price is *up* is the "controlled energy" launchpad, sharper than raw momentum. And another piece of
TA folklore dies (**#7**: dry coiled bases are a negative, not a positive). Everything else is mild or a
restatement. The two highest-novelty re-stream ideas were then tested (`probe2.py`) and **both refuted**:
**#21 close-vs-VWAP** — closes print *below* VWAP pre-move, *more* than normal (δ −0.26): the REVERSE of
"buyer wins the close" (matches round-1's lower close-location); **#16 trade-fragmentation** (num_trades/
volume) shows no pre-move rise (δ −0.01); **#27 delivered-shares-per-trade** not falling (δ −0.12).

**META-FINDING (the real result of the whole panel):** across 30 analyst hypotheses, *every*
"stealth institutional-accumulation footprint" idea — close-location/VWAP, ticket dispersion,
fragmentation, delivered-per-trade, coiled-spring, gap-reversal — was **refuted by the data.** The EOD
aggregate contains **no hidden-accumulation signal** before +10% moves. What survives is consistent and
unglamorous: **momentum + volatility (vol *contracting* sharpens it, #22 lift 6.3) + churn** (low
delivery%, weak closes-vs-VWAP, broad small-ticket participation). This is strong triangulated evidence
that (a) the counter-DVPT finding is robust, (b) the move is a *crowd/momentum* phenomenon, not quiet
smart-money, and (c) to ever see a named strong hand we must use the **named-flow feed** (below), because
the price/volume/delivery tape simply does not carry that signal. No silent survivors.

## Named-flow feed — WIRED (session 25, going-forward capture)

To find the strong hand the EOD aggregate hides, we wired the free NSE named-flow feeds.
New production ingester **`src/automation/deals.py`** (stdlib + requests, production venv) →
two new tables in `hermes.db` (created inline, idempotent): **`bulk_block_deals`** (trade_date,
symbol, deal_type bulk/block, **client_name**, side, qty, price) and **`fii_dii_flows`**
(trade_date, category, buy/sell/net). Scheduled **`hermes-deals.timer`** (Mon–Fri 14:30 UTC /
8 PM IST, after bhavcopy). First run captured **133 named bulk deals** for 2026-06-19 + FII/DII
(FII net +₹4,859 cr, DII −₹1,160 cr).

- **Sources (free, no cookie):** static CDN `…/content/equities/bulk.csv` & `block.csv` (CURRENT
  day only) + the open `api/fiidiiTradeReact`. NSE's *historical* range API is **bot-walled**
  (homepage 403s curl; range API 503) and there's no dated static archive → **named-flow history
  cannot be backfilled free**; it accrues from first run. (F&O OI bhav URL not yet located.)
- **Immediate insight in the names:** many bulk "buyers" are **HFT/prop firms** (GRAVITON, JUMP
  TRADING, MICROCURVES, HRTI) = liquidity/arb churn, NOT long-term accumulators — *resonates with
  the churn finding*. A client-name classifier (prop/HFT vs fund/PMS vs corporate) will separate
  real accumulation from churn.
- **Consequence:** the named-flow→move backtest over the 2012–2026 events is **not possible yet**
  (no history). Two uses available now: (a) **live cross-check** — today's genuine (non-HFT)
  bulk-BUY names vs the Launchpad candidates; (b) **accrue** daily until there's enough to test.
  Historical backfill options if wanted: a real browser session (Chrome) for a limited range, or BSE.
- **PROJECT_STATE pending** (a parallel session holds the file): add `deals.py`, the two tables,
  and `hermes-deals.timer` to Key file paths / Database schema / timers + a Decision-log entry.

### Client classifier + daily Launchpad∩genuine-buyer cross-check (built session 25)
- **`src/automation/client_classify.py`** (pure stdlib): `classify_client(name)` → FUND / INSURER /
  PENSION / FII / PMS / AIF_VC / HFT_PROP / BROKER_PROP / CORP / HNI, via name keywords + a known-HFT
  list. `CHURN = {HFT_PROP, BROKER_PROP}`. The **behavioral** test is the strong one: a client that
  buys ≈ sells the same stock the same day is churn (net≈0); a "genuine net buyer" = non-churn category
  + one-sided (|net|/(buy+sell)≥0.6) + net>0.
- **`research/explosive_moves/launchpad_scan.py`**: daily cross-check — classify the day's deals → genuine
  net buyers per stock → compute the validated Launchpad flags (MOM_CONT / PULLBACK / COILED) from
  bhavcopy (liquidity-gated ≥₹1cr) → **⭐ intersection**.
- **First run (2026-06-19) validated the whole pipeline:** day's deals split **44 churn vs 46 genuine**
  (client·stock pairs); 13 stocks had a genuine net buyer; **⭐ GOKEX** [MOM_CONT+COILED, +18%/mo, vol
  contracting, ₹25cr] ← **SBI Life Insurance** net +400k, and **⭐ ATALREAL** [MOM_CONT] ← Altizen
  Ventures (AIF) net +1.05M. (ESSENTIA flagged COILED but <₹1cr → correctly demoted to watch.) This is
  the going-forward daily product: *validated technical setup ∩ a real institution actually buying.*

## ⚑ Tradeable backtest — built & run (session 26, 2026-06-21). VERDICT: NO net-of-cost survivor.

The 4 candidate strategies (S1–S4) were put through a full event-driven daily backtest engine.
**Headline: the data-mined Launchpad has a real, OOS-robust, jitter-robust POSITIVE per-trade
expectancy net of costs — but it does NOT become a benchmark-beating portfolio. Risk-adjusted, all
four trail a buy-and-hold Nifty index fund; the apparent edge is thin, largely BETA, and
concentrated in 2020–2026. The skeptic gate (S4) fails outright. No strategy is accepted.** This is
the unbiased "test, fail, come back" outcome — and it is itself the valuable result.

### The engine (`research/explosive_moves/`, new this session)
- `embase.py` — symbol cache (3,515 EQ symbols, CA-adjusted OHLC + delivery + turnover + entry-feature
  arrays, pickled on the VPS); vectorized entry features **validated byte-for-byte vs `features.raw_features`**
  (max rel-err 1e-9); Nifty-50>200DMA regime series from `index_rows`.
- `strategies.py` — S1–S4 specs (entry predicate + tier + exit + sizing + regime), thresholds in `params`
  for jitter/sweep. `backtest.py` — onset entries (rising edge of the precursor mask + 22d cooldown, the
  realistic "take the breakout not day-15" basis; enter **s+1 open**, no look-ahead), tiered costs charged
  **both sides** (half-spread + fees on normal fills; **ATR-slippage only on adverse stop fills**), exit
  manager (wide stop, multi-scale, delayed wide trail), daily portfolio MTM with regime gate + risk sizing
  + heat/slot/no-dup caps. `metrics.py` — Calmar/Sharpe/Sortino/PF/expectancy-R/by-year + buy-hold
  baselines + alpha-beta. `calibrate.py` (step-1 stops), `gridsearch.py` (exit plateau), `run_backtests.py`
  (gates → full → walk-forward → decorrelation). Outputs: `out/backtest_report.txt` + `backtest_results.json`.

### Two findings that corrected the kickstart's exit assumptions
1. **Winners dip MORE than assumed.** Measured from the realistic s+1-open entry, the deepest pre-peak
   dip of eventual winners (touched +12%) is p50 −7%, **p25 −13%, p20 −15%, p10 −19.5%** (S1) — NOT the
   "−2.5% median / stop −10–12%" in the prior note (which measured from the base close). A −12% stop
   knocks out ~25–30% of winners; the calibrated stop is **−18%** (clears ~85%).
2. **A naive hold is ~flat.** Onset entries held with no management return **medRet66 ≈ +2.2%** (53% up
   at 66d) despite a **+24% median MFE** — the moves round-trip. The entire edge is in **actively
   harvesting the fat right tail** (MFE p90 +79%). Grid search (144 configs, re-run under realistic
   costs) found a clean **flat plateau, identical across S1/S3/S4**: stop −18%, sell 50% @ +25%, trail the
   rest 6×ATR (activating only after +25%), 132d max. Net per-trade expectancy at the plateau:
   **S1 +1.98% (PF 1.29), S4 +1.66% (PF 1.25), S3 +0.23% (PF 1.03 ≈ breakeven).**

### Cost model matters — and it is the swing factor
The kickstart's "0.5×ATR slippage" charged on **both sides of every trade** is a ~3.8% round-trip phantom
cost for these ~3.8%-ATR names that swamps the edge (turned the whole thing negative). That slippage only
occurs on a **market stop in a fast move**, not on an open/limit fill. With the realistic split (spread+fees
on entry/target/time fills; ATR-slippage only on the adverse stop), gross-positive expectancy survives into
a thin net-positive. Gross→net drag at the realistic (1.0×) setting is ~1–1.5%/trade.

### S4 SKEPTIC GATES (the decisive go/no-go) — **FAILED**
| Gate | Result | Verdict |
|---|---|---|
| **cost-delta** (survive 1.5×) | expR 0×:+1.69% · 1.0×:+0.54% · **1.5×:−0.04%** · 2.0×:−0.62% | ❌ dies by 1.5× |
| **alpha-vs-beta** | regime-ON α_ann **−3.8%** (β0.43); regime-OFF α_ann **−2.7%** (β0.40) | ❌ negative alpha both ways; returns are beta |
| **threshold-jitter ±10%** | expR +1.7–2.0%, PF ~1.28 across vratio & ret22 | ✅ robust (entry is not a cliff) |
| **capacity** (10% ADV) | median ₹220cr, p10 ₹94cr | ✅ not binding (~₹50–100cr deployable) |

The regime gate (Nifty>200DMA) **hurts** S4 — gated trades have *lower* expectancy than ungated (the filter
concentrates entries in crowded strong-market periods). Even ungated, alpha is negative after costs.

### Full-sample portfolio (2012–2026, net of costs) — all trail the benchmark risk-adjusted
| Strat | CAGR | MaxDD | **Calmar** | Sharpe | expR | PF | hit | β |
|---|---|---|---|---|---|---|---|---|
| S1 (5cr+) | +4.0% | −27.6% | **0.14** | 0.42 | +2.07% | 1.31 | 39% | 0.42 |
| S2 (25cr+) | +3.1% | −18.0% | **0.17** | 0.39 | +2.01% | 1.32 | 39% | 0.36 |
| S3 (rev) | −0.5% | −26.5% | **−0.02** | −0.04 | +0.15% | 1.02 | 36% | 0.26 |
| S4 (25cr+) | +0.4% | −30.0% | **0.01** | 0.09 | +0.54% | 1.07 | 34% | 0.43 |
| **Nifty 50** | **+10.7%** | −38.4% | **0.28** | 0.73 | — | — | — | — |
| **Nifty 500 / Midcap50** | +12.2/+17.3% | −38/−49% | **0.32 / 0.35** | 0.82/0.89 | — | — | — | — |

β≈0.4 × market 10.7% ≈ S1's entire 4% return ⇒ **alpha ≈ 0** (slightly negative net). Sizing up cannot
rescue it — Calmar/Sharpe are size-invariant and both sit **below** buy-and-hold.

### Bidirectional walk-forward — the edge is regime-concentrated (the "live lift fades" warning, realized)
Frozen plateau config, each window independently:
| Strat | 2012–2019 (Calmar / expR) | 2020–2026 (Calmar / expR) |
|---|---|---|
| S1 | 0.12 / +1.27% | 0.18 / +2.69% |
| S2 | **−0.01 / +0.33%** | 0.43 / +3.49% |
| S3 | **−0.08 / −1.34%** | 0.10 / +2.27% |
| S4 | **−0.09 / −0.89%** | 0.09 / +1.50% |

Per-trade expectancy is positive OOS in **both** windows only for **S1**; S2/S3/S4 are flat-to-negative in
2012–2019. The whole book's strength lives in the post-COVID 2020–2026 retail/momentum regime. By-year
expectancy is negative in several years for every strategy (2012, 2015, 2018, 2024…). The acceptance bar
("net-positive in BOTH directions AND every calendar year") is **not met**.

### S3 decorrelation — **FAILED**
corr(S3, S1)=**+0.52**, corr(S3, S2)=**+0.47**, corr(S3, S4)=**+0.52** (all > the +0.4 ceiling). S3 has
neither standalone expectancy nor diversification value — it is just another long Indian small/mid-cap book.

### Verdict & what it means
- **Reject S1, S2, S3, S4 as standalone, mechanical, net-of-cost alpha.** The Launchpad PRECURSOR is real
  (gross-positive, per-trade-positive, jitter- and OOS-robust) — but after realistic costs it is a thin,
  ~zero-alpha, β≈0.4 exposure that underperforms a Nifty index fund risk-adjusted, with the edge
  concentrated in one regime. The clean cost-stressed audit (S4) fails the cost and alpha gates outright.
- This **confirms, at the P&L level, the program's own meta-finding**: the EOD price/volume/delivery tape
  does not carry a tradeable institutional edge — it is momentum + churn, and momentum-after-costs is not
  alpha. *MFE ≠ capturable return* was the load-bearing caveat and it decided the outcome.
- **Constructive path (unchanged from the kickstart's "future data frontier"):**
  1. Use the Launchpad as a **screen / watchlist filter** (a daily list of technically set-up names), NOT a
     systematic book. `launchpad_scan.py` already produces it.
  2. The remaining edge must come from layers the EOD tape cannot carry: the **named-buyer overlay**
     (FII/DII + non-churn bulk/block — *forward-only paper A/B*, not backtestable) and the **qualitative
     layer** (concall tone / guidance / announcement direction). These are the next modules.
  3. Optional: a smoother early-harvest variant exists (higher hit, lower DD) for *tactical* use, but it
     does not beat the index either.

**Acceptance gates honored:** accepted only net of realistic costs; expectancy from a fill-level sim (not
MFE/MAE means); no look-ahead (features as-of s, enter s+1 open); survivorship via the raw archive; CA rows
excluded around entry; overfit tree cuts jittered ±10% (robust); named-buyer/FII-DII overlays excluded from
accept/reject (no history). The corpus's momentum over-representation showed up exactly where predicted —
the 2012–2019 walk-forward.

## Reproduce
`cd /opt/hermes/research && .venv-research/bin/python -m explosive_moves.run_all`
Params (env): `EM_MONTHLY_MOVE`, `EM_LIQ_FLOOR`. Outputs: `out/*.csv` + `research.db`.
**Backtest:** `… -m explosive_moves.embase` (build cache, once) then `… -m explosive_moves.run_backtests`
(gates → full → walk-forward → decorrelation; ~25s). Stop calibration: `… -m explosive_moves.calibrate`;
exit plateau: `… -m explosive_moves.gridsearch S1`.

## Next steps
1. **Live "Launchpad" daily screener** (M1∪M2 + S1 filter) — all inputs exist nightly. Then fold into
   PROJECT_STATE + retire this doc.
2. Tradeable backtest with costs/sizing + entry-stop-target from the per-event MFE/MAE distributions.
3. RS-era (2021+) deep-dive where `rs_rank` is dense.
