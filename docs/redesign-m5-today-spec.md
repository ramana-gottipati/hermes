# M5 — TODAY v3 (the orientation home) · module specification for owner review

> **Lifecycle: TRANSIENT** — retire when: M5 ships and its landing record folds into
> `docs/redesign-coordination.md` §5; then `git rm`. Fold into: `docs/redesign-coordination.md`.

**Status: SPEC v1.1 — no code. Built only on explicit owner go.** Codex pre-build review:
`VERDICT: APPROVE-WITH-CHANGES` — 2 BLOCKING accepted and fixed in this revision (the mood
call-chain specified exactly; the news-count tile given its bounded read contract) + 4
ADVISORY folded (signatures pinned into §3; route/Pat/toggle/payload claims confirmed).
Dispositions: `docs/redesign-coordination.md` §2.
Inputs (all ratified/decided): Part I M5 scope · Part II §C nav + §E journey step 1 · Part V §S
**count-tile pattern: ADOPT (owner, 2026-07-20)** · the S-A front-door lessons (the classic home
already carries them; Today v3 is their v3-native twin, not a port of the tile wall). Composes
with the DEPLOYED M0–M4 modules. **Zero new tables, zero new timers.**

## 1. Scope

- **Route: none new.** Today v3 REPLACES the focus content of `/dash/preview` (already
  registered, already the "today" destination in the shell bar). `v3_preview.py` (v3-owned)
  keeps the toggle mechanics and delegates its body to the NEW `today_v3.py`. The M0 toggle
  card moves into the Context rail — the preview gate function is never hidden.
- **Non-goals:** no legacy home edits (the classic `/dash` cockpit untouched) · no new data ·
  no journey coach layer (that is M6) · no cut-over.

## 2. Page anatomy (top → bottom; Focus column + Context rail + dock)

1. **Identity line + the mood strip.** One sentence ("Patearn describes what Indian-market data
   is doing, in plain English, and shows you the proof — never what to buy.") + the mood strip
   via the EXACT existing call chain (Codex B1): read latest breadth + Nifty-vs-200DMA from
   `index_signals` (the `cockpit.py:1077` idiom), call `market_mood.market_mood(breadth,
   nifty_above_200dma)` → render `market_mood.mood_banner(mood)` — the ONE regime vocabulary,
   single-owner module. The falsification framing renders under it (`ifx.demo_framing()`, zero-arg).
2. **THE COUNT-TILE BAND (the adopted Stitch pattern).** 4–6 tiles, each = a live COUNT the
   estate already computes + a VISIBLE plain subtitle + a deep link (the "every count is a live
   lens" affordance; no hover-only meaning — the S-A lesson):
   - Alerts this week (`signal_alerts.active_count` → total + by_severity) → the dock's Alerts
     channel / `/dash/attention`.
   - Stocks advancing today (`market_internals_daily` latest % advancing) → `/dash/market-internals`.
   - Results meetings next 7 days (`results_calendar.upcoming_results(7)` count) → dock Results.
   - Corp actions going ex this fortnight (`corp_actions.flagged_symbols` count) → dock Actions.
   - Tagged headlines today (`news_symbol_tags` bounded count) → dock Wire.
   Every tile: count in mono + subtitle + link; severity counts use the value contract ONLY
   where signed (alerts severity is a status hue, never up/down).
3. **"What changed" board.** The signal-event bus rail (`signal_alerts.active_alerts`,
   humanized strings — the S189-c idiom), top 8, each row `sym`-linked to the stock hub.
4. **THE FLAGSHIP BAND ("why this is different").** 4 cards, each with its provenance chip and
   one honest number: Replay any date (PIT + curl) · 22-year market internals · the seasonal
   tape ("most cells grey out — that IS the finding") · the validation record INCLUDING
   falsifications ("we publish failures so descriptive context is never mistaken for alpha").
   Links → the classic flagship pages until their v3 twins exist (one-way preview→classic).
5. **Start here.** The symbol search box (shared `TYPEAHEAD_JS`, name→ticker) opening the v3
   stock hub · "New here? How to read →" · "Ask Pat".
6. **Context rail:** the preview toggle card (M0, relocated) · status card (what's in the
   preview) · "The proof" links card.
7. **The M3 dock** (market-wide default, all channels) + footer fence.

## 3. Data contract

Every read exists and is bounded — signatures pinned (Codex B2/A3):
- mood: `index_signals` latest row → `market_mood(breadth, nifty_above_200dma)` → `mood_banner(mood)`.
- alerts: `signal_alerts.active_count(conn, within_days=7)` → `{total, by_severity, by_valence}`;
  board: `active_alerts(conn, within_days=7, limit=8)`.
- breadth: `market_internals_daily` — `SELECT * ... ORDER BY trade_date DESC LIMIT 1` (% advancing).
- results: `results_calendar.upcoming_results(days=7)` → list of Rows; tile shows `len()`.
- corp actions: `corp_actions.flagged_symbols(conn)` → `(rows, as_of)`; tile shows `len(rows)`.
- headlines: NEW bounded count, contract stated here (no helper exists): table-guarded
  `SELECT COUNT(DISTINCT t.news_url) FROM news_symbol_tags t JOIN sent_news n ON n.url=t.news_url
  WHERE n.sent_at >= datetime('now','-1 day')` → 0 on absent tables (honest-empty tile).
Payload budget: **< 300,000 uncompressed bytes** (test-asserted). Every count degrades to an
honest empty state.

## 4. Files

| File | Contents |
|---|---|
| `src/web/today_v3.py` (NEW) | the §2 anatomy: count-tiles · what-changed board · flagship band · start-here |
| `src/web/v3_preview.py` (edit, v3-owned) | landing delegates focus to `today_v3.body()`; toggle card → rail |
| `tests/test_v3_today.py` (NEW) | count-tiles carry visible subtitles + links · mood strip present once · what-changed rows `sym`-linked · flagship band = 4 cards w/ provenance chips · fence + demo-framing present · payload < 300KB · empty-state honesty (in-memory conn) · no legacy leak |

No new gate rows (the route already classifies); Pat unaffected (no new lens).

## 5. Verification

Suite + the M5 test file → local walk → Codex post-build loop → deploy (writer-safe recipe) →
**the beginner-persona walk on the box**: the audit's top-5 friction items re-checked on THIS
page (orientation sentence present · help one click away · no jargon-only tile · one regime
vocabulary · search-by-name reaches a dossier in ≤2 actions).

## 6. Owner decisions at review (defaults ship)

1. The count-tile set (§2.2's five proposed; drop/add freely).
2. Flagship card set + order (§2.4's four).
3. The identity sentence wording.
