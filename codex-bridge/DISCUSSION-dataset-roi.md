# DISCUSSION — Dataset ROI (Claude ⇄ Codex, converged)

**Question (Ramana):** Of the *new* gap datasets in `docs/DATASET-RESEARCH-BRIEF.md`, which delivers the best ROI for Pattern — evaluated per attribute, and informed by how the NIFTY regime has shifted over 20–25 years?

**Method:** two live rounds between Claude Code and Codex (gpt-5.5, read-only). Trail: `req-12`/`resp-12` (R1) → `req-13`/`resp-13` (R2). This file is the converged synthesis.

---

## 0. VERDICT (both agents agree)

**Build order: C-MVP → A → B → (E folded into C) → D → F.**

| Rank | Dataset | Verdict | One-line reason |
|---|---|---|---|
| P1 (free) | **C. Capital-allocation score** | Build now | Not a new dataset — a derived layer on data already held. Days of work, no acquisition cost. |
| P1 (first new feed) | **A. Insider / promoter / pledge events** | Build taxonomy-first | Most orthogonal, densest in the smallcap tail where alpha now lives, carries *both* conviction (open-market buys) and distress (pledge/selling) signals. |
| P2 | **B. Credit-rating actions** | Build as veto/hygiene | Structured and PIT-clean, but lagging, commoditized, and coverage-skewed to the already-efficient large/levered segment. |
| P2 | **E. M&A** | Fold into C | Sparse standalone; deal-size/mcap, related-party, post-deal ROIC are capital-allocation *features*. |
| P2/P3 | **D. Order book / book-to-bill** | Sector module | Real alpha but only in capex/EPC/defence/infra; presentation NLP is costly; sector-scoped. |
| P3 | **F. Segment / geography revenue** | Descriptive-first | Annual cadence, brittle extraction, weak timing value. |

**Killed (per brief §5, unchallenged):** company-level GST/e-way bill (doesn't exist for third parties), satellite/web-traffic alt-data (not attributable at smallcap level, not affordable).

---

## 1. How we got here (the convergence trail)

- **R1 — Claude:** A > C > B. Ranked on regime-fit rubric (free × all-cap-tail × PIT × not-retail-crowded).
- **R1 — Codex:** C > B > A. Three counters: (a) A's value is the *filtering taxonomy*, not the raw noisy feed; (b) a veto firing on 20% of names can save more than a noisy buy on 100%; (c) Claude's rubric overweights coverage vs **decision impact**. Proposed a better objective: `ROI = (decision impact × PIT confidence × source reliability × marginal orthogonality) / (effort × false-positive cleanup)`.
- **R2 — Claude concedes** the ROI formula, that C isn't a dataset (steps out of the ring), and Codex's taxonomy-first MVP-A filter set. **Holds A > B** under Codex's *own* formula: B is lagging ("ratings restate yesterday's price"), commoditized (low orthogonality — overlaps `scoring.py`+`cci_series.py`), and blind in the unrated tail; the better distress veto (promoter **pledge delta**) actually lives inside A.
- **R2 — Codex concedes A > B:** cannot defend B as timing-alpha (est. only 10–25% of rating events lead price); agrees pledge-delta inside A dominates ratings as tail distress warning; agrees A is more orthogonal; names **A as the dataset whose marginal value has risen most in 20 years**.
- **Consensus:** C-MVP → A → B. No open disagreement remains → no artificial Round 3.

---

## 2. NIFTY 20–25y regime analysis (the "why" behind the ranking)

Four structural shifts, each pushing the answer toward promoter/insider behaviour (A) and away from breadth-blind, large-cap-concentrated feeds (B):

**(1) Ownership flipped foreign → domestic.** DII share surpassed FPI for the first time (~19% by mid-2025); SIPs ~₹31,000 cr/month; demat accounts 4cr (2020) → ~22cr (FY25). *Implication:* domestic control-persons and their disclosed actions move stocks more than FII prints. The promoter is the domestic informed actor par excellence → A's marginal value rises.

**(2) Retail explosion crowds the crowded signals.** ~10cr new investors since 2020; 93% of F&O individuals lose money (₹1.8L cr FY22–24; ~₹1.05L cr FY25). *Implication:* naïve technical/momentum setups are now run by millions and decay; the edge shifts to *orthogonal fundamental/behavioural/event* data retail can't replicate at scale. Options *flow* is toxic for direction, but client-type OI (already built) is a real positioning layer. A is orthogonal; B is not.

**(3) Alpha migrated down the cap curve.** 2024: BSE SmallCap +30.7%, MidCap +28.3% vs Nifty ~10–13%; 243 SME IPOs (vs 179 in 2023); yet ~80% of >₹1,000cr names sat 20%+ below peak even at index highs. Sell-side coverage is concentrated in the top ~150. *Implication:* the informational edge lives in the under-covered ~2,500-name tail. **Every tail name has a promoter who files under A; most tail names are unrated (B is blind there).** This is the decisive point — B's coverage hole overlaps exactly with Pattern's alpha zone; A's coverage is densest there.

**(4) Large caps are efficient.** Global desks fully cover the top ~150; Pattern cannot out-inform them there. Any dataset whose edge concentrates in large/rated names (B) is low-ROI *for Pattern specifically*.

**Regime verdict:** the dataset whose marginal value has risen most over 20 years is **A (promoter/insider behaviour)** — both agents independently reached this.

*Supporting data caveat:* figures are directional (drawn from NSE ownership tracker, SEBI F&O study, AMFI/SIP, exchange/SME-IPO tallies, and public market data). Precise series should be re-pulled before any figure is quoted in a client-facing artifact. Long-run NIFTY context: ~12–13% 20y TRI CAGR with >50% max drawdown (2008 −51%, 2009 +78%, COVID 2020 −38% intra-year) — i.e. deep-cyclical EM behaviour where a distress *veto* (pledge/rating) has real, recurring value, which is why B stays P2 rather than dropped.

---

## 3. Attribute-scored ROI (final, merged)

Scored on Codex's objective. Alpha zone = where the signal pays *for Pattern's universe*.

| Attr | A. Insider/promoter | B. Credit rating | C. Capital-alloc | D. Order book | E. M&A | F. Segment |
|---|---|---|---|---|---|---|
| Insight | Informed actor commits cash / de-risks | Balance-sheet stress / repair | Compounding quality of incremental capital | Forward revenue visibility | Capital-allocation via deals | Hidden growth/exposure mix |
| Edge vs priced-in | High in tail (unwatched filings) | Low–med (lags price) | Med (ignored in tail) | High in sector subset | Med (episodic) | Low (annual) |
| PIT | Clean (disclosure date) | Clean fwd; historical care | Partial (filing dates) | Mixed (backlog "as-of" vague) | Clean | Clean but brittle |
| Coverage | **All-cap, incl. SME** | Rated names only (~skewed) | All (derived) | Sector subset | Sparse per name | All (extraction-limited) |
| Orthogonality | **High (new behavioural stream)** | Low (overlaps scoring+CCI) | Med | High (sector) | Med | Low |
| Cost/legal | Free, BSE/NSE, no ToS issue | Free, NSE/BSE | Free (held) | Free filings, costly parse | Free filings | Free, costly parse |
| Effort | 7–12d (taxonomy) | 4–7d | 3–6d MVP | 15–30d | 8–15d | 20–40d |
| FP cleanup | **High (the moat)** | Low | Med | Med | Low | Med |
| Verdict | **P1 new** | P2 | **P1 free** | P2/P3 | P2 (into C) | P3 |

---

## 4. Data availability + PIT/coverage caveats (winners)

### A. Insider / promoter / pledge
- **Sources:** NSE PIT Reg 7(2) page (equity/SME/REIT-InvIT, CSV + XBRL converter); NSE annual PIT page (company, person, category, txn type, acquired/disposed shares & value, post-holding, txn date); NSE SAST Reg 7/29/31 + pledged-data pages; **BSE insider-trading/XBRL as fallback** (same pipe as `concall_bse.py`).
- **PIT:** clock = exchange **disclosure/broadcast date**, never transaction date. Forms can be delayed/amended/cancelled/duplicated across exchanges → dedup + `amendment_flag`.
- **Coverage:** all-cap incl. SME — densest exactly in the alpha tail.
- **The hard part (= the product):** taxonomy. Must separate open-market buy/sell from pledge create/increase/release/invocation, inter-se transfers, gifts, ESOP, scheme/allotment. "promoter bought = bullish" is banned. Require post-event liquidity sanity (value vs 20d traded value).

### B. Credit-rating actions
- **Sources:** NSE "Credit Rating" (Debt Centralised Database — agency, rating, action, rating/reporting/broadcast dates, CSV); NSE SDD system-driven disclosure (CRA auto-dissemination from **2 Aug 2025** — excellent forward PIT); BSE Reg 30 announcement PDFs as fallback/backfill.
- **PIT:** `knowable_at` = broadcast/reporting date. Pre-SDD history needs agency-PR/announcement backfill. **Absence of a rating is neutral, not a quality signal.**
- **Coverage:** rated names only → skewed to larger/debt-heavy/financials. Frame as: "when present, high-quality risk intel; absent = neutral."

### C. Capital-allocation (derived — no acquisition)
- **Easy/free MVP:** incremental sales/PAT/FCF/ROCE vs incremental capital employed; capex intensity vs revenue growth; dividend/buyback consistency; dilution/equity issuance; debt-funded-growth discipline; post-capex margin & asset-turn improvement.
- **Hard version (defer):** M&A-outcome attribution (needs E — acquired-business contribution, impairment, divestment, segment restatements). Build MVP now, exclude M&A attribution until E exists.

---

## 5. Pattern data-structure fit (proposed, from Codex R1)

```
insider_events(symbol, exchange, disclosure_dt, transaction_dt, regulation,
  person_name_hash, category, promoter_group_flag, txn_type_raw, txn_class,
  shares, value_rs, pct_equity, post_shares, post_pct, mode,
  source_url, attachment_url, parsed_at, amendment_flag)
  → derived: open_market_buy_value_to_mcap, open_market_sell_value_to_mcap,
    promoter_cluster_buy_30d, net_promoter_cashflow_90d, pledge_delta_pct,
    insider_signal_class ∈ {conviction, caution, plumbing, pledge_risk, ignore}

credit_rating_events(symbol, isin, agency, instrument, amount_cr,
  rating_from, rating_to, outlook_from, outlook_to, action,
  rating_date, reporting_date, broadcast_date, source_url, attachment_url,
  parsed_at, method_version)
  → derived: rating_notch_delta, outlook_delta, watch_negative_flag,
    default_or_delay_flag, withdrawal_flag, rated_debt_to_mcap,
    days_since_last_action, worst_rating_issuer, credit_trend_12m
```

Both are **event tables** → they slot into the existing `provenance.py` / `fundamentals_asof.py` PIT discipline the same way concalls do. `insider_events` complements `shareholding_history.py` (quarterly/slow) with daily event granularity. Capital-allocation is columns/derivations on existing fundamentals, surfaced via `scoring.py`.

---

## 6. How to proceed

1. **C-MVP** (3–6d): capital-allocation features on existing fundamentals; exclude M&A attribution. Surface in `scoring.py` + a screener column.
2. **A** (7–12d): build the *taxonomy first* on a sample, validate the classifier against known cases, then the event feed + derived metrics + PIT wiring. This is the flagship new feed and its difficulty is the moat.
3. **B** (4–7d): credit-rating event feed as a veto/hygiene layer; forward-PIT via SDD, backfill via announcements; frame absence as neutral.
4. Later: **E** (unlocks C's hard version) → **D** (sector module) → **F** (descriptive).

**Needs Ramana's call before build:** (a) confirm C→A→B order and the ~3-week P1 scope; (b) A's classifier is where the risk lives — approve a taxonomy-first spike before committing to the full feed; (c) whether any of this is client-facing (if so, re-pull the regime figures in §2 to exact series first).

*Per project doctrine: nothing implemented until Ramana approves. This is the filtered proposal set.*
