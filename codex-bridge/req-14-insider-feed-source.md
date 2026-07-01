# req-14 — Insider/promoter/pledge feed: source + parsing strategy (Claude ⇄ Codex)

**Context:** D76 roadmap, dataset **A**. The taxonomy-first spike is DONE and committed
(`src/automation/insider_events.py`, `insider_events` table — `classify_txn`, `signal_class`,
`aggregate`, `--selftest` green). Dataset **C** is now validated LIVE on the VPS (1,900 names).
The remaining piece for A is the **live fetcher** (`fetch_disclosures`, currently a deliberate stub).

Reply as `codex-bridge/resp-14-insider-feed-source.md`.

## What I need from you (research + review — you're read-only, advise from knowledge)

1. **Source ranking with EXACT endpoints.** For SEBI insider/promoter/pledge data, free, all-cap incl. SME, rank the options and give the exact URL/endpoint + response format (JSON/CSV/XBRL) for each:
   - NSE PIT Reg 7(2) (insider trading) — bulk daily file? per-symbol? date-range API?
   - NSE SAST Reg 29 (acquisition) + Reg 31 (encumbrance/pledge)
   - NSE promoter pledge / encumbrance page
   - BSE insider-trading / corporate-announcements (fallback — we already fetch BSE announcements in `concall_bse.py`)
   Which single source gives the **best coverage × backfill depth × parse-ability** for a nightly 3,000-name pipeline? Is there a **bulk daily disclosures file** (so we don't hit per-symbol 3,000×)?

2. **Access reality.** NSE needs cookie priming / specific headers / referer (our `equity_list.py` already fetches an NSE CSV — reuse that session pattern?). Rate limits? Does BSE avoid the anti-bot problem? Historical backfill depth actually available per source?

3. **Field mapping.** For your top source, list its actual columns and map them to our `insider_events` schema (symbol, disclosure_dt, transaction_dt, regulation, category, mode/txn_type_raw, shares, value_rs, pct_equity, post_pct, person). Which field is the true **PIT `knowable_at`** (disclosure/broadcast date, NOT transaction date)?

4. **Dedup + amendments.** NSE and BSE both carry the same disclosure → dedup key? How are revised/cancelled filings marked so `amendment_flag` is set correctly?

5. **Review my taxonomy.** Critique `classify_txn` (in `insider_events.py`): the class set is OPEN_MARKET_BUY/SELL · PLEDGE_CREATE/RELEASE/INVOKE · INTER_SE/ESOP/GIFT/INHERITANCE/ALLOTMENT/CONVERSION/OFF_MARKET · UNKNOWN, with pledge/plumbing resolved BEFORE the generic market fallback. What real-world `mode` strings will it MIS-classify? What class is missing?

6. **Backfill strategy.** Recommend the concrete approach: bulk daily-file replay over a date range vs per-symbol. Where does historical depth run out?

Be specific and cite the exact endpoints. If a source is effectively unusable (anti-bot, no history, per-symbol only), say so plainly — that changes the build.
