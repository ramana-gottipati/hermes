# resp-12 — Dataset ROI debate, Round 1 — Codex

My independent ranking: **C > B > A > E > D > F**.

If we restrict the question to **new external data acquisition**, my ranking becomes **B > A > E > D > F**. I am separating that because **C is not really a dataset**; it is a derived layer on existing fundamentals, corporate actions, cash flow, and price data. That distinction matters for ROI.

## 1. Attribute-scored ranking

| Rank | Dataset | Insight | Edge vs priced-in | PIT | Source / method | Cost / legal | Effort | Alpha | Confidence | Verdict |
|---:|---|---|---|---|---|---|---:|---|---|---|
| 1 | **C. Capital-allocation score** | Has management compounded incremental capital well, or just grown size? | Less crowded than price/momentum; mostly ignored in smallcaps unless sell-side covers it. | Partial Y | Existing financials, cash flow, corporate actions, buybacks/dividends, market-cap history. | Free; already held or exchange filings. | 3-6 days for MVP | Medium-high, slow signal | High for MVP, medium for full version | **Build P1** |
| 2 | **B. Credit-rating actions** | Early warning / confirmation of balance-sheet stress, upgrade cycle, funding access. | Strong as veto/risk signal; upgrade edge weaker but useful for financials, infra, debt-heavy small/midcaps. | Y going forward; historical needs care | NSE debt centralised database credit-rating page exposes rating agency, rating action, rating date, reporting/broadcast fields and CSV download; NSE 2025 SDD circular says CRA uploads auto-disseminate from Aug 2, 2025. | Free public exchange data. | 4-7 days MVP | Medium-high as downside veto | High | **Build P1** |
| 3 | **A. Insider / promoter trading** | Does the most informed actor commit real cash or reduce exposure? | Potentially high in undercovered tail, but only after filtering noise. Raw feed is dangerous. | Y if using disclosure/broadcast date, not transaction date | NSE PIT Reg 7(2), SAST Reg 7/29/31, pledged data; CSV/XBRL/announcement attachments. | Free public exchange filings. | 7-12 days MVP | High but noisy | Medium | **Build P1/P2 after filters** |
| 4 | **E. M&A tracker** | Is management buying growth sensibly, selling assets, or doing value-destructive deals? | Event edge exists, but sparse; better as governance/capital-allocation input than standalone screen. | Y | BSE/NSE corporate announcements, Reg 30, scheme docs. | Free public filings. | 8-15 days | Medium | Medium | **Build P2 as part of C** |
| 5 | **D. Order book / book-to-bill** | Forward revenue visibility for EPC/capital goods/defence/infra names. | Real alpha in sector subset; not universal. Retail does follow “order win” announcements, but not normalized order-book/revenue/mcap history. | Mixed | Investor presentations, annual reports, exchange announcements. | Free filings, extraction costly. | 15-30 days | High in narrow sectors | Medium-low | **P2/P3 sector module** |
| 6 | **F. Segment / geography revenue** | Hidden growth mix, export exposure, concentration risk. | Useful for thesis, weak timing. Annual cadence means slow. | Y with annual-report filing date, but extraction brittle | Annual reports / XBRL where available. NSE annual reports and XBRL pages exist. | Free, but parsing/OCR/LLM cost. | 20-40 days | Medium-low | Medium-low | **P3 / descriptive-first** |

## 2. Where I disagree with Claude

### I would not put insider/promoter trading first yet

Claude’s argument is directionally right: promoter behavior is regime-fit, domestic, all-cap, and often ignored. But raw PIT/SAST data is not “clean alpha”; it is **cleanly timestamped noisy disclosure data**.

The important caveats:

1. **PIT cleanliness depends on using disclosure date, not trade date.**  
   A backtest cannot act on the acquisition/sale date unless the disclosure was already public. NSE’s PIT pages expose Reg 7(2) disclosures with CSV and XBRL conversion, and the annual PIT page includes transaction date fields and buy/sale/pledge fields. But the tradable clock must be exchange broadcast/disclosure date.

2. **Promoter filings mix signal and plumbing.**  
   Inter-se promoter transfers, gifts, off-market deals, ESOPs, pledge creation/release/invocation, inheritance, trust restructuring, and conversion events should not be treated like open-market conviction. A ₹10 crore open-market promoter buy is not the same as a pledge release or family transfer.

3. **Smallcap-tail signal may be real but fragile.**  
   The same tail has more related-party games, liquidity management, and governance risk. The feed needs a strict event taxonomy before it should influence ranking.

My minimum viable A should only score:

- open-market acquisition/disposal
- promoter/director/KMP categories separately
- value as `% market cap`, `% free float`, and trailing 20-day traded value
- cluster buying over 30/90 days
- exclude pledge, invocation, inter-se, gift, ESOP, scheme/allotment unless separately tagged
- require post-event liquidity sanity

So A is strong, but I rank it below B for first build because **A’s false-positive management is the product**.

### I rank credit ratings above insider trading for near-term ROI

Claude calls B coverage-skewed. True: debt-light microcaps and many tiny companies will not be rated. But the data is now more structurally attractive than the prompt implies.

NSE has a credit-rating filing surface with columns such as company, ISIN, rating agency, rating, rating action, rating date, reporting date, and broadcast date, plus CSV download. NSE/BSE also issued the 2025 system-driven disclosure flow where CRAs upload ratings daily and the exchange auto-disseminates them from **August 2, 2025**. That is excellent for going-forward PIT.

This is especially useful for Pattern because it is not just “alpha”; it is a **veto layer**:

- downgrade / watch negative / default payment → avoid or haircut
- upgrade / outlook positive → balance-sheet repair confirmation
- rating withdrawal → needs special treatment, often not bullish
- bank-facility rating changes → useful for lenders’ view before equity crowd notices

Coverage gaps are acceptable if the feature is framed as: “when present, it is high-quality risk intelligence; absence is neutral, not positive.”

### Capital allocation is not fully “free”

C is the best ROI, but Claude underprices the hard version.

The easy version is free:

- incremental sales/PAT/FCF/ROCE vs incremental capital employed
- capex intensity vs revenue growth
- dividend/buyback consistency
- dilution / equity issuance
- debt-funded growth discipline
- post-capex margin and asset-turn improvement

The hard version is not free:

- M&A outcome attribution needs event-level deal data, acquired business contribution, impairment, divestment, segment restatements, and management claims.
- Buyback/dividend interpretation needs context: underinvestment vs capital discipline.
- Financials need sector adaptation, already established in PROJECT_STATE doctrine.

So I would build **C-MVP** first and explicitly exclude M&A outcome attribution until E exists.

## 3. Challenge to the regime rubric

Claude’s proposed rubric: free, all-cap including tail, PIT-reconstructable, not retail-crowded.

I agree with the gates, but the rubric overweights **coverage breadth** and underweights **decision impact**.

A dataset does not need all-cap coverage to have high ROI if it is a reliable veto. Credit ratings fail the pure all-cap test, but a downgrade/default/watch-negative signal on 20% of the universe can still save more money than a noisy buy signal on 100%.

I would change the scoring to:

`ROI = (decision impact × PIT confidence × source reliability × marginal orthogonality) / (engineering effort × false-positive cleanup)`

That penalizes A until event taxonomy is solved and rewards B because it is structured, source-authored, and close to lender reality.

On retail crowding: the argument should not be “technical edge is dead.” Naive chart patterns are crowded. But Pattern’s current stack is not naive technicals: DVPT, RS regime, participant OI, MEP, credibility, and provenance are combined. The retail crowding argument supports adding fundamental/event orthogonal data; it does not invalidate technical/flow edge.

## 4. Source reality check for top two external datasets

### B. Credit-rating actions

Primary source:

- NSE “Credit Rating” under Debt Centralised Database, with CSV download and fields including agency, rating, rating action, rating date, reporting date, broadcast date.
- NSE “SDD - Credit Rating” / Reg 30 system-driven disclosure, effective Aug 2, 2025 per exchange circular.
- BSE corporate announcements can be fallback for Reg 30 credit-rating PDFs.

PIT caveats:

- Use **broadcast/reporting date** as `knowable_at`.
- Rating date may precede public dissemination; do not trade on it historically unless broadcast date is present.
- Historical pre-SDD coverage may require agency PR archives or BSE/NSE announcement backfill.
- Absence of rating is not a quality signal.

Proposed table:

`credit_rating_events(symbol, isin, agency, instrument, amount_cr, rating_from, rating_to, outlook_from, outlook_to, action, rating_date, reporting_date, broadcast_date, source_url, attachment_url, parsed_at, method_version)`

Derived metrics:

- `rating_notch_delta`
- `outlook_delta`
- `watch_negative_flag`
- `default_or_delay_flag`
- `withdrawal_flag`
- `rated_debt_to_mcap`
- `days_since_last_action`
- `worst_rating_issuer`
- `credit_trend_12m`

### A. Insider / promoter trading

Primary source:

- NSE PIT Reg 7(2) page, equity/SME/REIT-InvIT, CSV download and XBRL converter.
- NSE annual PIT page with company, person, category, transaction type, acquired/disposed shares/value, post-holding, and acquisition/sale date fields.
- NSE SAST Reg 7/29/31 and pledged-data pages.
- BSE insider trading / XBRL pages as fallback.

PIT caveats:

- Use exchange disclosure/broadcast date as `knowable_at`; transaction date is only an event attribute.
- Some forms are delayed, amended, cancelled, or duplicated across exchanges.
- Pledge creation/release/invocation must not be mixed with buy/sell.
- Inter-se promoter transfers and off-market transactions need separate neutral tags.

Proposed table:

`insider_events(symbol, exchange, disclosure_dt, transaction_dt, regulation, person_name_hash, category, promoter_group_flag, txn_type_raw, txn_class, shares, value_rs, pct_equity, post_shares, post_pct, mode, source_url, attachment_url, parsed_at, amendment_flag)`

Derived metrics:

- `open_market_buy_value_to_mcap`
- `open_market_sell_value_to_mcap`
- `promoter_cluster_buy_30d`
- `net_promoter_cashflow_90d`
- `pledge_delta_pct`
- `insider_signal_class = conviction / caution / plumbing / pledge_risk / ignore`

## 5. Candidate-specific notes

**D order book** should not be killed. It is just not a universal dataset. For defence, capital goods, EPC, railways, shipbuilding, infra, cables, transformers, and industrial automation, normalized order book is more forward-looking than trailing financials. But extraction from presentations is messy and the signal must be sector-scoped. Build after the exchange-structured feeds.

**E M&A** should be folded into C first. Standalone M&A is sparse, but deal size divided by market cap, related-party flag, cash/debt/share consideration, and post-deal ROIC are excellent capital-allocation features.

**F segment/geography** is useful for dossiers and thesis explanation, but I would not spend P1 engineering on it. Annual cadence and brittle extraction make it a weak first ROI candidate.

## 6. Final position for Round 1

Claude’s A-first thesis is good but too optimistic about raw promoter data. I would build:

1. **C-MVP capital allocation** immediately because it is cheap and uses existing data.
2. **B credit-rating events** as the first new external dataset because it is structured, PIT-friendly, and a strong veto.
3. **A insider/promoter events** next, but only with strict transaction taxonomy and no raw “promoter bought = bullish” shortcut.

Sources used: NSE PIT/insider trading pages, NSE credit-rating/SDD pages and circular, NSE India Ownership Tracker June 2025, SEBI F&O loss study, AMFI annual report / SIP data references, and the repo’s `DATASET-RESEARCH-BRIEF.md`, `concall_bse.py`, `provenance.py`, `fundamentals_asof.py`, and `shareholding_history.py`.