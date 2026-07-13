# User-Journey & UX Audit — 2026-07-13 (joint Claude + Codex)

**Lifecycle: DESIGN(live) — audit of record + remediation program.** Retire condition: all sessions
S-A…S-H below are shipped and their outcomes folded into PROJECT_STATE; the findings tables then
become history. The binding day-to-day rules extracted from this audit live in
**`docs/SURFACE-PLAYBOOK.md`** (canonical) — this doc is the WHY behind them.

**Method.** Two fully independent reviews run in parallel with no shared state, then an autonomous
adversarial dialogue to converge: (1) **Claude** — live-site browser walk + a beginner-persona walk
and an expert-PM-persona walk of the live VPS site (GET-only) + three code audits (IA/routes/orphans;
Pat+Telegram; redundancy+education); (2) **Codex** (gpt-5.5) — independent code+live review, report
preserved at `docs/codex-review/UX-CODEX-INDEPENDENT.md`, dialogue at
`docs/codex-review/UX-DIALOGUE-R1-CODEX.md`. The dialogue converged in one round: all 14
Claude-only findings CONFIRMED by Codex with file:line/live evidence, all 3 Claude pushbacks on the
Codex report conceded or adopted, and a joint Top-12 agreed (§8-bis). Personas: a first-time retail
beginner and a buy-side PM at a JP-Morgan-caliber firm — the two ends of the audience Ramana wants
the product to serve simultaneously. This audit is UX/IA-scoped; the parallel `docs/codex-review/FINDINGS-LEDGER.md`
campaign (code integrity, D1–D8) is separate and stays authoritative for quant-correctness items.

---

## 0. Executive summary

The estate's analytics are demonstration-grade; its journey is not yet. Both reviewers, working
blind, converged on the same diagnosis:

1. **The front door sells the wrong thing.** Home is a wall of 18 jargon count-tiles + 8 boards —
   it reads "expert's workbench", represents only ~37% of the 62-lens estate, contains a live
   dead-link bug on its hottest strip, and never says what Patearn is or where to start. The
   genuinely differentiating assets (PIT replay + entitled /v1 API, spec-sheets with pre-hashed
   gates, 22y market internals, seasonal FDR certification, the honest validation record) are
   invisible from home. *The platform's rarest data is its least advertised.*
2. **The beginner has no ramp; the expert has no shortcuts.** Excellent education assets exist
   (reading-guide, glossary, Pat, mood strip) but are hidden under an opaque "Trust" label and
   unlinked from the pages that need them. Meanwhile the expert gets exactly one server-side CSV
   estate-wide, multi-MB pages, and no name-search.
3. **Education is two disjoint half-systems.** The prose scaffold (bottom_line/plain) covers ~20%
   of pages (the deep-data cohort); glossary popovers cover a different ~20%; zero pages have both;
   the densest-jargon pages have neither. The honesty fence — the product's core promise — is
   hand-written in ≥7 different phrasings with no shared primitive. And there are TWO glossary
   systems (web ~245 keys vs Pat's 52) that don't feed each other.
4. **Pat is 71% blind.** 9/62 lenses fully reachable, 44/62 invisible — including the attention
   bus, news, seasonal, internals, rotation, and the whole ownership block. Pat also can't teach
   methodology (no access to `docs/strategies/`).
5. **News intelligence is buried.** A rich pipeline (4 sources, LLM classification, ticker tagging,
   Telegram briefs) surfaces on the web only as the LAST item of a collapsed rail group, plus an
   unowned `/dash/news` dead-end page. Nothing on home hints news exists.
6. **Redundancy is a UX tax in one family.** RS/rotation spans 11+ surfaces (RRG-Map and
   Rotation-Weather are the SAME quadrant data under two metaphors; capture data renders on 3
   pages); there are three "what changed" feeds with three memories. The seasonal trio +
   rs-hub/strategist launchers show the correct pattern.
7. **Orphans are now structural, not accidental** — 10 orphan/legacy routes + 1 data-orphan
   (`stock_oscillators`: computed nightly, zero surface). The fix is a gate (route-registry test)
   plus the SURFACE-PLAYBOOK, not another cleanup sweep.

**Verdict both personas agreed on:** demo-able tomorrow — but only rehearsed and driver-operated.
Self-serve (the real bar for "show JP Morgan") needs sessions S-A + S-C + S-D at minimum.

---

## 1. The estate today (measured)

| Measure | Value | Source |
|---|---|---|
| Workspaces | 5 (Markets · Screener · Strategies · Tracker · Trust-chip) | `lens_registry.py:308` |
| Nav lenses | 62 routed (+2 overlay-only) | `lens_registry.py:65-287` |
| Markets lenses | 30 — overloaded; `left_rail.py:8` itself calls it "overwhelming" | registry + rail |
| Live `/dash` GET paths | ~156 (incl. APIs/actions/compat) | runtime enumeration (Codex) |
| Orphan/legacy page routes | 10 + `stock_oscillators` data-orphan | §5 table |
| Home estate coverage | ~23 of 62 lenses ≈ 37%; all 8 Trust lenses absent | `cockpit.py:393-486,785-895` |
| Education prose scaffold adoption | 8 full + 1 partial of ~40 dense modules ≈ 20% — all from the S110 deep-data cohort | grep `bottom_line/plain/how_to_read_link` |
| Glossary wiring | different ~20%; **zero overlap** with scaffold cohort; densest pages have neither | §6 |
| Honesty-fence phrasings | ≥7 distinct wordings/treatments, no shared primitive | §6 |
| Pat coverage | 9/62 full · 9 partial · 44 invisible (≈15% full / 29% any) | `src/pat/web.py:2543-2672` map |
| Server-side CSV exports | 1 (wolfe/trades) estate-wide | expert walk |
| Page weights | screen2 2.3MB · stock 2.7MB · evidence-pack 3.7s | expert walk |

---

## 2. Converged findings (P0 = user-blocking/trust-damaging · P1 = major friction · P2 = polish)

### P0
| # | Finding | Evidence | Owner session |
|---|---|---|---|
| P0-1 | **Home Attention board links are dead**: `?symbol=` vs the route's `sym` — every alert click renders the empty shell | `attention_view.py:144` emits `?symbol=`; live `/dash/stock?symbol=ACL` = 72KB shell vs 612KB real page (Codex-verified) | S-A |
| P0-2 | **No orientation**: home has no identity line, no start-here, help unlinked (glossary/reading-guide appear on home only inside the search-box JS) | beginner walk §1 | S-A |
| P0-3 | **Three regime vocabularies same day**: home "RISK-OFF" · mood strip "Cautious" · header "UP-BIASED"; mood "why?" links to coverage which doesn't explain it | live walk | S-A |
| P0-4 | **Action verbs on descriptive surfaces**: RS Band board on HOME prints Avoid/Ride/Fade (also `rsband_view` verbs — already ADJUDICATED in the code-integrity ledger as D2-F4; coordinate, don't double-fix) | home board; `FINDINGS-LEDGER.md` D2-F4 | codex-lane fix + S-A wording |
| P0-5 | **`/dash/strategy-ref` leaks internal doctrine to the public**: "Class: CANONICAL (permanent — do not archive)", "Reconciled: 2026-07-11 (S111)", "future sessions (and Ramana)" | live page | S-C |
| P0-6 | **Tracker exposes the owner's live portfolio** (books, open MTM, gainers) to any anonymous visitor | live `/dash/tracker/dashboard` | Ramana decision (S-A item 8) |

### P1 (converged, both reviewers)
- **Flagship/wow invisibility** — no "why this is different" band; Trust is one unexplained word. (S-A)
- **Markets rail overload** — 30 lenses, most collapsed, unlabeled toggle buttons (a11y); news last. (S-B)
- **News split/buried** — `wire` lens at the tail of a collapsed group; `/dash/news` unowned dead-end ("Pick a stock" with no picker). Converged fix: `/dash/news` → 307 to wire; symbol news lives in the dossier tab only. (S-B)
- **Beginner entry dead-ends** — no company-name→ticker search ("TATA CONSULTANCY" → "No data. Check the ticker."); ⌘K silently misroutes lowercase "tcs" to Pat while `/dash/stock?sym=tcs` works. (S-D)
- **Education two-half-systems + fence fragmentation + two glossaries** (see §6). (S-C)
- **Pat 71% dark + no methodology grounding** (see §7). (S-E)
- **Redundancy: RRG-Map = Rotation-Weather; capture ×3; three change-feeds; rotation micro-page fragments; momentum-scan rows don't link to dossiers (only table estate-wide that breaks the `sym` link convention); Sectors ⇄ Sector-economics declared siblings but never link.** (S-B)
- **Command palette hard-coded** — omits half the estate; must be generated from `lens_registry`. (S-D)
- **Credibility has two mental models** — `concalls` lens vs orphaned `/dash/credibility` fingerprint. (S-B)
- **No structural orphan gate** — convention only; the registry test doesn't exist. (S-H)
- **Home tiles/board strings are machine grammar** — "SS/S triggers", "ACL: accumulation flipped DISTRIB → STRONG_DISTRIB". (S-A)

### P2
- Metaphor-only nav labels (Weather/Clock/Band/All-weather/Launchpad); expert export gap (server CSV
  on every table + /v1 curl-repro affordance); payload discipline (paginate screen2/stock);
  state-mutating GETs (`ack`, `track`, `clear`) → POST; tracker flat-compat links in palette;
  strategist/screen2 one-liners drift (single-source in registry); seasonal `_subnav` duplication;
  MEP twice on home. (S-B/S-G)

### What already works — protect it (both personas)
Market-mood plain strip · home ticker box (1-action stock lookup) · reading-guide itself ·
Pat's example-chip landing · "?" provenance popovers naming source columns (better than most vendor
terminals) · wolfe/trades table (12 server filters + real CSV + 596 exclusions disclosed) ·
spec-sheets with pre-registered SHA-256 gates · replay-any-date rendering raw entitled /v1 envelopes
with repro curls · coverage's honest funnels · the seasonal trio's `_subnav` pattern ·
rs-hub/strategist launcher pattern · the dossier as integration hub.

---

## 3. Persona verdicts (full walks preserved in the session transcript)

**Beginner (top frictions, ranked):** no orientation → help invisible → jargon tile wall → three
regime words → name-lookup dead-end → ⌘K lowercase misroute → "Trust" hides all learning → screener
acronym soup with zero glossary links → Avoid/Ride/Fade on home → stock-page code strip
("1/100 · p0/5 · T3 · NS 47.0 · D") with plain-English only far below → news buried → Pat
unreachable from nav + strategy-ref internal leakage.

**Expert (must-change-first):** fix the `?symbol=` front-door bug → put the moat above the fold
("Prove it" rail: replay-any-date · validation record incl. failures · /v1 + OpenAPI · 22y
internals) → uniform server-side export + curl-repro → payload discipline → consolidate the RS
family and unify the three change-feeds. **"The falsification-forward posture is a genuine
differentiator — but it needs demo framing, or a client hears 'nothing here makes money'."**

---

## 4. IA map (key extract; full inventory in session transcript)

62 lenses: Markets 30 · Screener 5 · Strategies 14 · Tracker 5 · Trust 8. Rail groups — Markets:
Big picture / Strength & momentum / Rotation / Sectors / Patterns / Events & flow; Strategies:
Conviction & structure / Fundamentals / Accumulation / Ownership & filings / Launchpad.
Misgrouping flags: `move-anatomy` (methodology, sits in Markets by D115), `buyback-calc` (a tool,
sits in Events & flow), the Ownership & filings cohort (market-wide filing feeds inside the
"stock-selection ONLY" Strategies charter — placement decision needed).

## 5. Orphan inventory (disposition per item happens in S-B)

| Route | State | Suggested disposition |
|---|---|---|
| `/dash/credibility` | orphan (in-page links only) | merge as Credibility child/tab (converged) |
| `/dash/momentum` | orphan (drill links only) | declare nested child of rs-hub/momentum family |
| `/dash/replay` | superseded by replay-any-date | 307 or declared Trust child |
| `/dash/_ui` | internal showcase | exempt-with-rationale in the gate |
| `/dash/wolfe` `/dash/rs` `/dash/scan` | legacy aliases | 307 to successors |
| `/dash/ratio` | sacred (build-additive rule), deep-link only | declare as exempted dossier-tool + palette entry |
| `/dash/news` | unowned dead-end | 307 → wire (converged C3) |
| `/candidates` | outside /dash | link from wire/home news board or fold |
| `/dash/ui-kit` | mounted only in preview_app — dead in prod | delete or exempt |
| `stock_oscillators` | DATA-orphan (nightly compute, Pat-only read) | decide: surface as dossier tab / retire the job |

## 6. Education & honesty layer (the two-half-systems finding)

- Prose scaffold (`infographics.bottom_line/plain/how_to_read_link`): ~11 adopter modules — the
  S110 deep-data cohort (+ seasonal family); essentially zero pre-sprint pages.
- Glossary wiring (`gloss()` popovers or `?q=` links): a mostly-different ~30 modules. **Converged
  count (Codex R1): only 3 modules carry both systems** (market_internals, reading_guide,
  infographics itself). **The densest pages (momentum-scan, growth, divergence, capture-map,
  rotation micro-pages, harmonic, wolfe, results-reactions, stock_chart) have neither.**
- Fence: ≥7 phrasings ("descriptive, not advice" / "never a signal" / "not a buy/sell/trim
  instruction" / "not investment advice or a recommendation" / …) each styled differently; no
  `infographics.fence()` exists (`infographics.py:502-507` stops at `plain`).
- TWO glossaries: `src/web/glossary.py` (parses `docs/metrics-glossary.md`; **405 lookup keys**,
  /dash/glossary renders 167 term entries) vs `src/pat/glossary.py` (52 terms, 8 families) —
  no shared source (`src/pat/understand.py:304-311` imports Pat's own); `docs/strategies/`
  (10 methodology pages) reaches neither Pat nor the popovers.

## 7. Pat & Telegram (gap analysis for the enrichment + publisher program)

- Pat architecture (KEEP): closed-vocab, Gemini parse → deterministic compiler → SQL templates —
  hallucination-proof by construction; tap path ₹0. 21 flows today.
- Dark domains (44/62): attention bus (`signal_events` — exactly the "new findings" substrate),
  news/wire, participants/FII, insider/ratings/SAST/holdings, all rotation surfaces, seasonal trio,
  market-internals, move-anatomy, sector-economics, capture-map, results-reactions, launchpad-track,
  harmonic, Wolfe detail (board-card only), Tracker, all 8 Trust lenses.
- Strategy-board flow addresses only 10 of 17 registry strategies (`understand.py:53`).
- Telegram: bot commands + 4 push timers exist; destinations are DM/group tables only — **no channel
  concept anywhere** (`TELEGRAM_CHANNEL_ID` absent). Approval loop primitives that EXIST: inline
  keyboards + CallbackQueryHandler (menu tree), `tracker_alert_delivery` dedup ledger,
  `signal_alert_state` severity gate + ack. MISSING (the S-F build): draft-queue table · composer
  (signal_alerts + news → human-readable draft) · DM preview with Approve/Reject buttons · channel
  send path · channel-scoped dedup + rate caps · shared-DB topology between one-shot timer jobs and
  the long-polling bot.

---

## 8. THE REMEDIATION PROGRAM — session partition (paste-ready problem statements)

> **Converged run order (Codex R1 adjustments adopted):** **S-A (+S-H in parallel) → S-C → S-D →
> S-B1 → S-B2 → S-E → S-F → S-G.** Rationale: front door first, the orphan gate runs in PARALLEL
> with S-A (cheap, guards every later route/nav change), education (S-C) BEFORE Pat expansion (S-E)
> so Pat consumes the unified glossary/fence model instead of encoding today's duplication, S-B
> split into two passes (labels/cross-links vs route deprecation), Telegram (S-F) is its own
> product program. The ⌘K-lowercase hotfix moves INTO S-A; the tracker-privacy decision (P0-6) is
> S-A's day-zero item. POST-ifying mutating GETs moves up into S-B2 (GET side effects are a
> trust/audit hazard for public demos). Each session: boot per SESSION-PROTOCOL,
> kickstart-pick-verify every item (some may land earlier), keep the descriptive-only fence, and
> follow `docs/SURFACE-PLAYBOOK.md` for anything new.

### S-A — FRONT DOOR & ORIENTATION (P0)
> **Problem:** The home page is expert-dense, partly broken, and silent about what Patearn is. Fix
> without reducing expert density (layered-additive, S110 discipline).
> **Day-zero:** the tracker-privacy DECISION (P0-6: auth-gate vs scrubbed demo book vs hide public
> tracker nav) — decide before adding any more home/news/tracker visibility.
> **Scope:** (1) Fix the Attention-board `?symbol=`→`sym` bug (`attention_view.py:144`) +
> grep-audit every `?symbol=` emitter + the ⌘K lowercase-ticker hotfix (`ui_kit.py:282-285`
> uppercase-and-try before falling through to Pat);
> (2) ONE regime vocabulary site-wide — the plain mood strip becomes canonical, home banner and
> index-panel states reconcile to it, mood "why?" links to a real explainer, put the mood strip on
> home; (3) hero identity line + "Start here" strip (mood → what changed → stock lookup → 2-minute
> guide → Ask Pat); (4) "Why this is different" flagship band (replay-any-date · attention bus ·
> 22y internals · seasonal tape · CCI ledger) + an "Audit trail / Prove it" card (coverage ·
> spec-sheets · validation · /v1); (5) plain-English subtitle on every count-tile (visible, not
> hover-only) + humanize board event strings; (6) a News board (wire headlines); (7) surface the
> "every count is a live lens" affordance at the top; (8) Ramana DECISION: tracker privacy
> (auth-gate vs demo-book on the public URL); (9) move the Avoid/Ride/Fade wording fix in concert
> with the codex-lane D2-F4 fix (don't double-edit `rsband_view.py`/`cockpit.py` — fork-check first).
> **Files:** `cockpit.py` (hot in codex lane — fork-check), `dq_banner.py`, home board renderers.
> **Done:** beginner-persona re-walk passes items 1-4 + 9-11 of the friction list; no dead links on home.

### S-H — FUTURE-PROOF GATE (P1, cheap — run in PARALLEL with S-A)
> **Problem:** Orphans are structural; convention hasn't held. **Scope:** build
> `tests/test_dash_route_registry.py` per the converged RouteKind contract (lens · nested_child ·
> dossier · api_or_action · compat_redirect · internal_dev · exempt-with-owner+rationale); wire the
> §5 orphan dispositions as its seed exemption list; generate the ⌘K palette from `lens_registry`
> (kills the hand-maintained PAGES map — coordinate with S-D); add the SURFACE-PLAYBOOK landing
> checklist to the test's failure message. **Done:** the test fails on a synthetic unregistered route.

### S-C — EDUCATION EVERYWHERE (P1)
> **Problem:** Two disjoint half-systems + 7-phrasing fence + internal leakage.
> **Scope:** (1) `infographics.fence(kind)` shared primitive; migrate all ~15 hand-written fences;
> (2) back-fit `bottom_line`+`plain`+`how_to_read_link` to the pre-sprint estate (priority:
> momentum-scan, growth, credibility, rrg/rsband/rotation, insider/ratings/sast/shp, screen2, wire,
> wolfe-scan, stock dossier TOP strip — one plain sentence above the code strip); (3) wire glossary
> (`gloss()` or `?q=`) into every "neither" page; (4) one glossary corpus: web glossary feeds Pat
> (replace/augment Pat's 52-term copy), `docs/strategies/` linked from popovers; (5) de-metaphor nav
> labels (plain subtitle for Weather/Clock/Band/All-weather/Launchpad); (6) strategy-ref public
> intro (strip CANONICAL/S111/Ramana internals from rendered HTML — keep them in the .md source as
> comments if needed); (7) persistent "New here?" header link (reading-guide) site-wide.
> **Done:** every dense page has BOTH scaffold and glossary wiring; fence renders identically
> everywhere; a beginner re-walk finds help within one click from any page.

### S-D — SEARCH & ENTRY (P1, small; lowercase hotfix already in S-A)
> **Problem:** Beginners know company names, not tickers; palette is hard-coded.
> **Scope:** name→ticker typeahead on the home box + fuzzy suggestions on the miss page
> (security_master has the names); palette generated from `lens_registry` + aliases + dossier
> entries (with S-H); Pat gets a nav entry (Trust group or header) so it's reachable without
> typing a sentence.
> **Done:** "tata consultancy" reaches TCS in ≤2 actions from home; palette lists all 62 lenses.

### S-B — IA CONSOLIDATION (P1; split into two passes per Codex R1)
> **Problem:** Markets rail overload; same-data pages; orphans; misgrouped lenses.
> **S-B1 = labels, grouping, cross-links (items 1-6, 8-11). S-B2 = route deprecation/redirects
> (item 7 + POST-ifying mutating GETs), driven by a classification table: register · redirect ·
> dev-only · sacred-deep-link (`/dash/ratio` is NOT a normal orphan — build-additive rule) ·
> remove-from-prod.**
> **Scope:** (1) Markets rail → task groups (converged: Today [attention · wire · results-reactions
> · actions] / Market state [internals · move-anatomy? (or Trust) · participants] / Strength /
> Patterns / Seasonality); label the collapse toggles (a11y); (2) merge RRG-Map + Rotation-Weather
> into one lens with a Map⇄Weather toggle (Wolfe fresh⇄open precedent); (3) fold cycle-clock /
> sector-momentum / early-signals into the Rotation cluster; (4) capture-map cross-links (rrg ⇄
> rsband ⇄ capture note "same capture columns"); (5) credibility-fingerprint → Credibility child/tab;
> (6) Ownership & filings placement decision (own rail group vs Markets/Events); (7) orphan sweep
> per §5 dispositions; (8) momentum-scan rows → dossier links; Sectors ⇄ Sector-economics reciprocal
> links; (9) adopt the seasonal `_subnav` strip pattern for the RS family; (10) unify the three
> change-feeds on the signal-event bus (strategist "what changed" reads the bus); (11) single-source
> strategy one-liners in `lens_registry`.
> **Files:** the FORKED nav trio — anchored inserts only, fork-check the VPS.
> **Done:** nav gate green; expert re-walk stops asking "why are these six screens?".

### S-E — PAT TOTAL COVERAGE (P1, likely 2 sessions)
> **Problem:** Pat reaches ~15% of the estate and can't teach methodology.
> **Scope phase 1 (cheap, broad):** nav-answer flows — for every lens, Pat can answer "where do I
> see X" with a link + one-line description, generated FROM `lens_registry` so new lenses are
> auto-covered (playbook checklist #6); route "news/what changed/breadth/seasonality/replay" phrases
> to the right pages. **Phase 2 (data flows, priority order):** attention bus (what changed today /
> for SYMBOL) · news/wire (headlines for SYMBOL/today) · participants/FII · insider/ratings/SAST/
> holdings · rotation states · seasonal (what's the July base rate for X) · internals (breadth now)
> · Wolfe open-trades detail. **Phase 3 (education):** ground explain-flows on the unified glossary
> (S-C#4) + `docs/strategies/` so "explain the Wolfe methodology" works. KEEP the closed-vocab
> architecture — flows stay deterministic SQL templates; no LLM-written SQL, no advice phrasing.
> **Done:** coverage table re-run ≥90% any-coverage; "what changed today", "TCS news", "explain
> Wolfe methodology" all answer.

### S-F — TELEGRAM PUBLISHER (P1, Ramana-gated writes)
> **Problem:** Ramana wants curated findings (alerts, news, seasonal events, new signals) posted to
> his Telegram CHANNEL — but nothing posts without his explicit per-item approval.
> **Scope:** (1) `TELEGRAM_CHANNEL_ID` setting + channel send path (bot as channel admin); (2)
> `publish_drafts` table (status pending/approved/rejected/posted · draft text · provenance ·
> dedup key · channel); (3) composer job: `signal_alert_state` (crit/high) + `news_feed`
> extraordinary items + (later) Pat-detected findings → human-readable drafts (fence wording
> included — descriptive, never advice); (4) DM preview to Ramana with Approve/Reject inline
> keyboard (reuse the menu CallbackQueryHandler pattern); approve → post to channel + stamp; reject
> → archive; (5) channel-scoped dedup (tracker_alert_delivery pattern) + per-run rate cap; (6)
> topology: composer runs on existing timers writing the queue; the long-polling bot owns the
> callback + the send (shared DB). NO auto-post path exists even as a flag-off; approval is
> structural. **Done:** end-to-end walk: a seeded draft DMs Ramana, approve posts to a test channel
> exactly once, reject never posts, duplicates suppressed.

### S-G — EXPERT AFFORDANCES (P2)
> **Scope:** server-side `format=csv` on every major table (wolfe_trades pattern: attention,
> concalls, internals, leaders, screen2, wire); "reproduce via /v1 curl" affordance on tables the
> API can serve; paginate/virtualize screen2 + stock dossier (2.3-2.7MB today); POST-ify
> state-mutating GETs (ack/track/clear) with 303s; sticky-filter cookies on more tables
> (wolfe pattern). **Done:** expert re-walk: every table exports; money pages < 1MB.

---

## 8-bis. The converged Top-12 (joint, ranked by user impact — Codex R1 final)

1. **P0** Fix the broken home Attention stock links (`symbol`→`sym`; audit all stock-link params).
2. **P0** Decide the tracker public posture (auth-gate · demo-data · hide until scrubbed).
3. **P1** Front-door orientation layer (identity line, Start-here, plain tile subtitles, visible fence).
4. **P1** One regime vocabulary (home · mood strip · Markets header · Pat · a real "why?" explainer).
5. **P1** Surface the wow estate on home (PIT replay · attention bus · Wolfe trades · internals · seasonal · CCI) with "prove it" trust links.
6. **P1** Fix entry/search (lowercase routing · name→ticker · fuzzy miss recovery · Pat in nav).
7. **P1** Consolidate IA (Markets task groups · RS/rotation family merge+cross-links · classify every orphan).
8. **P1** Redirect `/dash/news` → `/dash/wire`; symbol news lives in the dossier only.
9. **P1** Standardize honesty+education primitives (shared `fence()` · bridge the two glossaries · scaffold+glossary on dense pages).
10. **P1** Expand Pat from glossary bot to estate navigator (registry-generated nav-answers, then data flows for attention/news/participants/ownership/seasonal/internals).
11. **P1** Route/nav/palette guardrails (registry test · palette from registry · orphan classification enforced).
12. **P2** Expert affordances (server CSV + /v1 repro on dense tables · payload pagination · unified change-feed memory · POST-only state changes).

## 9. Coordination fences (multi-lane safety)

- The codex code-integrity lane owns `rsband_view.py`, `cockpit.py`, `signals.py` etc. right now —
  S-A/S-B MUST fork-check and re-pick against main at session start (multi-session-safety).
- D2-F4 (RS-band action verbs) is adjudicated in FINDINGS-LEDGER; S-A only aligns the home board
  wording with whatever that fix ships — one owner per file per session.
- Anything touching the forked-nav trio deploys by anchored insert only; never full-file scp.
- Every session ends with a live persona re-walk of its "Done" bar (walk-the-journey).
