# M5 — TODAY v3 (the orientation home) · module specification for owner review

> **Lifecycle: TRANSIENT** — retire when: M5 ships and its landing record folds into
> `docs/redesign-coordination.md` §5; then `git rm`. Fold into: `docs/redesign-coordination.md`.

**Status: SPEC v1.0 — no code. Built only on explicit owner go, after the Codex review loop.**
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
   is doing, in plain English, and shows you the proof — never what to buy.") + the EXISTING
   `market_mood.mood_banner` (the ONE regime vocabulary; single-owner module, reused not
   re-rendered). The falsification-framing sentence renders under it (`ifx.demo_framing()`).
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

Every read exists and is bounded: `market_mood.mood_banner` · `signal_alerts.active_count` /
`active_alerts(limit=8)` · `market_internals_daily` latest row · `upcoming_results(7)` ·
`corp_actions.flagged_symbols` · the dock's own reads. Payload budget: **< 300,000 uncompressed
bytes** (test-asserted). Every count degrades to an honest empty state.

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
