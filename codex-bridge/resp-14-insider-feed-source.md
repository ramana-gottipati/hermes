Created [resp-14-insider-feed-source.md](D:/Hermes/codex-bridge/resp-14-insider-feed-source.md).

Key answer: NSE is the primary source. The live-verified bulk endpoints are:

- PIT: `https://www.nseindia.com/api/corporates-pit?index=equities&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY`
- SAST Reg 29: `https://www.nseindia.com/api/corporate-sast-reg29?from_date=DD-MM-YYYY&to_date=DD-MM-YYYY`
- SAST Reg 31 events: `https://www.nseindia.com/api/corporate-pledgedata-sast3132?from_date=DD-MM-YYYY&to_date=DD-MM-YYYY`

I ranked BSE native PIT/SAST as fallback/cross-check, not primary. I also included field mappings, `knowable_at`, dedup/amendment handling, taxonomy critique, and backfill strategy.

Sources used include official NSE/BSE pages and bundles:
[NSE PIT](https://www.nseindia.com/companies-listing/corporate-filings-insider-trading), [NSE Reg 29](https://www.nseindia.com/companies-listing/corporate-filings-regulation-29), [NSE Reg 31](https://www.nseindia.com/companies-listing/corporate-filings-regulation-31), [BSE insider](https://www.bseindia.com/corporates/insider-trading), [BSE app config](https://www.bseindia.com/assets/data/appConfig.json), and [SEBI PIT circular](https://www.sebi.gov.in/legal/circulars/aug-2021/automation-of-continual-disclosures-under-regulation-7-2-of-sebi-prohibition-of-insider-trading-regulations-2015-system-driven-disclosures-ease-of-doing-business_51848.html).

No code files changed. No git staging/commit/state mutation was done.