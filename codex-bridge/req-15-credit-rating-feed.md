# req-15 — Credit-rating feed: source + PIT + parsing (Claude ⇄ Codex)

**Context:** D76 roadmap, dataset **B** (credit-rating actions — P2 veto/hygiene). C and A are now
LIVE + validated on the VPS (C: 1,900 names; A: 4,834 NSE PIT events). Building B's live feed next,
same pattern as A (`src/automation/insider_events.py` → NSE bulk date-range JSON, cookie-primed).

Reply as `codex-bridge/resp-15-credit-rating-feed.md`.

## What I need (research + review — you're read-only, advise from knowledge)

1. **Exact endpoint(s).** The NSE credit-rating / SDD feed URL + params (date-range bulk like `corporates-pit`?). You cited "NSE Credit Rating under Debt Centralised Database" and the SDD auto-dissemination from 2 Aug 2025 in resp-14 — give the concrete API path + query params + response shape. BSE fallback endpoint too.
2. **PIT clock.** Which field is `knowable_at` — broadcast/dissemination date vs rating date? How far back does history go (pre-SDD gap)?
3. **Field mapping** → my planned `credit_rating_events` table (symbol, isin, agency, instrument, rating_from/to, outlook_from/to, action, rating_date, broadcast_date, amount_cr). What are the source's actual field names?
4. **The hard part — notch delta.** How to normalise heterogeneous agency scales (CRISIL/ICRA/CARE/India Ratings; long-term vs short-term; "AAA/AA+/…/D") into a single ordinal so `rating_notch_delta` is comparable? Give the ordinal ladder. How to detect upgrade/downgrade/reaffirm/withdrawal/watch/default from the raw action text.
5. **Coverage + dedup.** Rated-universe size vs our ~1,900; multiple instruments per issuer (bank facilities, NCDs) → how to roll up to one issuer-level signal? Dedup/amendment key?
6. **Veto framing.** Confirm B is downside-veto-first (downgrade/watch-negative/default → haircut), upgrade weaker. What's the single most decision-useful derived flag?

Be concrete with endpoints and the notch ladder. If NSE credit rating is not cleanly bulk-fetchable, say so and recommend BSE.
