# UX Dialogue R1 - Codex Reply

## B. Verdicts On Claude Findings

**B1 - CONFIRM, P0.** Home Attention links are broken. Evidence: `src/web/attention_view.py:144` emits `/dash/stock?symbol=...`; the stock page expects `sym` (`/dash/stock?sym=ACL` rendered 612260 bytes and title `ACL`, while `/dash/stock?symbol=ACL` rendered 72083 bytes and the empty "Enter a ticker" shell). Live `/dash` also shows `/dash/stock?symbol=ACL`.

**B2 - CONFIRM, P1.** Regime language conflicts. Evidence: live `/dash` says `RISK-OFF`; live `/dash/markets` mood strip says `Market mood Cautious` and links `why?` to `/dash/coverage`; the same page headline says `Nifty 50 - UP-BIASED`. `/dash/coverage` does not explain that mood strip.

**B3 - CONFIRM, P1.** Entry is brittle for beginners. Evidence: live `/dash/stock?sym=TATA%20CONSULTANCY` returns `No data for TATA CONSULTANCY. Check the ticker.` Command palette code requires uppercase before routing to stock: `src/web/ui_kit.py:282-285`; live `/dash/pat?q=tcs` says `I don't have "tcs" yet`, although `/dash/stock?sym=tcs` works.

**B4 - CONFIRM, P1.** Public strategy reference leaks internal operating language. Evidence: live `/dash/strategy-ref` contains `Class: CANONICAL (permanent - do not archive)`, `Reconciled: 2026-07-11 (S111)`, and `future sessions (and Ramana)`.

**B5 - CONFIRM, P0/P1 decision item.** Public tracker exposes owner portfolio state. Evidence: live `/dash/tracker/dashboard` is anonymous and shows `Your cockpit`, `books`, `open positions`, `open MTM`, `Gainers`, and the `Main` book. Code: `src/web/dashboard.py:4934`, `src/web/dashboard.py:5009-5019`. This is not just polish; it is a demo/privacy hazard. Ramana must choose auth gate, scrubbed demo data, or no public tracker nav.

**B6 - CONFIRM, P1.** The honesty fence has no shared primitive. Evidence: `src/web/infographics.py:502-507` has `bottom_line` and `plain`, but no `fence`. Fence copy appears in many bespoke forms: `src/web/attention_view.py:257`, `src/web/seasonal_view.py:607`, `src/web/growth_view.py:178`, `src/web/insider_view.py:245`, `src/web/sast_view.py:285`, `src/web/shp_view.py:226`, `src/web/ratings_view.py:255-256`.

**B7 - CONFIRM, P1.** There are two glossary systems. Evidence: `src/web/glossary.py:27-58` parses `docs/metrics-glossary.md` and has 405 lookup keys; `src/pat/glossary.py:37-49` owns 8 families and 52 Pat terms. Pat explain flows import its own glossary in `src/pat/understand.py:304-311`; the systems do not share a source.

**B8 - CONFIRM WITH NARROWING, P1.** The education layer is disjoint, but "zero pages use both" is too strong. My scan found scaffold usage on 11 web modules, glossary-ish usage on 30, and both in 3 modules: `src/web/infographics.py`, `src/web/market_internals_view.py`, `src/web/reading_guide_view.py`. Also the seasonal family does use the prose scaffold: `src/web/seasonal_view.py:266-268`, `src/web/seasonal_view.py:936`, `src/web/seasonal_screen_view.py:554-556`, `src/web/seasonal_events_view.py:239`. The actionable point stands: dense pages such as `momentum_view.py`, `growth_view.py`, and several rotation/RS pages still lack a coherent beginner ramp.

**B9 - CONFIRM DIRECTIONALLY, P1.** Pat coverage is far below the web estate. Evidence: the registry currently has 64 lenses including overlay entries (`src/web/lens_registry.py` runtime count); Pat's explicit web flows are the small set in `src/pat/web.py:2353-2387` and `src/pat/web.py:2570-2670`. Strategy-board vocabulary is hard-coded to 8 keys plus `all` at `src/pat/understand.py:53`, while the strategist board/registry has more distinct strategy surfaces. I did not independently reproduce the exact 9/62, 9 partial, 44 dark split, but the gap is real and material.

**B10 - CONFIRM, P1 scope note.** Telegram channel publishing is not present. Evidence: config exposes `telegram_bot_token` and `telegram_allowed_user_ids` only (`src/core/settings.py:34-35`); sends route to allowed user IDs in `src/automation/news_feed.py:303-337`, `src/automation/digest.py:120-145`, and `src/automation/tracker_alerts.py:207-214`. Primitives exist: inline callbacks in `src/assistant/telegram_bot.py:21-25`, `src/assistant/telegram_bot.py:1711-1770`, and alert dedup in `src/automation/signal_alerts.py:52-72` plus tracker delivery in `src/automation/tracker_alerts.py`.

**B11 - CONFIRM WITH ADJUSTMENT, P1/P2.** Export and expert affordances are uneven, though not exactly one server CSV. Evidence: server CSV exists for tracker exports (`src/web/dashboard.py:5386-5436`), strategist (`src/web/strategist_view.py:758-768`), and Wolfe trades (`src/web/wolfe_trades_view.py:362-383`). Many large tables rely on client-side Blob export (`src/web/dashboard.py:283-369`, `src/web/cockpit.py:555-578`, `src/web/screener_plus.py:1048-1060`). Mutating GETs exist: Attention ack links and route (`src/web/attention_view.py:250`, `src/web/attention_view.py:312`, `src/web/attention_view.py:484`) and Wolfe `clear=1` filter mutation (`src/web/wolfe_trades_view.py:468-527`).

**B12 - CONFIRM, P1/P2.** "What changed" has multiple memories. Evidence: signal bus explicitly names four faces in `src/automation/signal_events.py:4`; alert rail uses server state in `src/automation/signal_alerts.py:52-72`; Attention also sets a last-seen browser cookie in `src/web/attention_view.py:418-479`; Strategist has separate confluence/changed strips and marks Pat alerts seen with POST in `src/web/strategist_view.py:505-623`, `src/web/strategist_view.py:730`. MEP also appears as top tile plus multiple home boards in `src/web/cockpit.py:404`, `src/web/cockpit.py:852-875`.

**B13 - CONFIRM WITH CLASSIFICATION, P1.** The orphan list is real, but some are intentional sacred/deep-link/dev surfaces. Evidence: mounted but not first-class lens examples include `/dash/momentum` (`src/web/momentum_pane.py:353`, mounted in `src/web/v2_surfaces.py:120`), `/dash/replay` (`src/web/replay_view.py:64`, superseded by `/dash/replay-any-date`), `/dash/_ui` (`src/web/ui_showcase.py:166`), `/candidates` outside `/dash` (`src/main.py:202`), legacy `/dash/rs` redirect (`src/web/dashboard.py:1220-1225`), `/dash/scan` (`src/web/dashboard.py:1239`), and sacred `/dash/ratio` (`src/web/dashboard.py:7119`). `/dash/ui-kit` is preview-only in `src/api/preview_app.py:25`. `stock_oscillators` is Pat-only/data-orphaned: `src/automation/oscillators.py:25`, `src/pat/web.py:1771-1824`.

**B14 - CONFIRM, P1/P2.** Front-door Attention event strings are machine grammar. Evidence: live `/dash` shows `ACL: accumulation flipped DISTRIB -> STRONG_DISTRIB`; source label construction is in `src/automation/signal_events.py:161` and home rows render summaries in `src/web/attention_view.py:504`.

## C. Pushbacks

**C1 - CONCEDE.** My tracker compat finding should drop below the tracker privacy problem. The public portfolio exposure is the real issue; compat URLs are housekeeping after Ramana chooses the public/private posture.

**C2 - CONCEDE ON RANKING, KEEP ON SHIPPING SEQUENCE.** User-visible P0s should rank above the route-registry gate. I still want the gate early because it is cheap and prevents the same failure mode during remediation, but it is not the top user-impact item.

**C3 - ADOPT CLAUDE'S VERSION.** `/dash/news` should 307 to `/dash/wire`; symbol-scoped news should live only in the stock dossier tab. Evidence: `src/web/news_view.py:201` and `src/web/news_view.py:209` are two separate route handlers today, while stock pages already have dossier context. A standalone symbol search page duplicates the dossier and weakens IA.

## D. Partition Critique

The session partition is mostly right. I would reorder and split decisions from implementation:

1. **S-A stays first**, but include B5 as an explicit day-zero Ramana decision before adding more home/news/tracker visibility. Fix B1 and command-palette lowercase as tiny P0/P1 hotfixes in the same front-door pass.
2. **Move S-H gate to run in parallel with S-A**, not after S-G. It is not top user impact, but it should guard every later route/nav change.
3. **S-D should be folded into S-A for the lowercase bug**, while company-name search/typeahead can remain its own small S-D.
4. **S-B should be split into "IA labels/cross-links" and "route deprecation/redirects".** The latter needs a classification table: register, redirect, dev-only, sacred deep-link, or remove from prod. Do not treat `/dash/ratio` like a normal orphan.
5. **S-C should come before deep Pat expansion.** Pat should consume a unified glossary/fence model; otherwise Pat coverage will encode today's duplicated education layer.
6. **S-F Telegram is product-adjacent, not UX-estate remediation.** Keep it as a separate approval-gated program with descriptive-only templates and channel topology decisions.
7. **S-G is correctly P2 except mutating GETs.** POST-ifying ack/clear belongs earlier if public demos or crawlers are expected, because GET side effects are trust/audit hazards.

## Final Converged Top-12 By User Impact

1. **P0 - Fix broken home Attention stock links.** Change `symbol` to `sym`; audit all stock-link params.
2. **P0 - Decide tracker public posture.** Auth-gate, demo-data, or hide public tracker nav until scrubbed.
3. **P1 - Give the front door an orientation layer.** Identity line, "Start here", plain-English tile subtitles, and visible descriptive fence.
4. **P1 - Unify regime language.** One market-state vocabulary across home, mood strip, Markets header, Pat, and coverage explainer.
5. **P1 - Surface the wow estate on home.** PIT replay, Attention bus, Wolfe open-trades, market internals, seasonal tape, CCI credibility, with "prove it" trust links.
6. **P1 - Fix entry/search.** Lowercase ticker routing, company-name-to-ticker search, fuzzy no-data recovery, and Pat visible in nav.
7. **P1 - Consolidate IA.** Collapse Markets rail into task groups, merge/cross-link RS/rotation/momentum family, and classify every orphan route.
8. **P1 - Redirect `/dash/news` to `/dash/wire`.** Keep symbol news inside the stock dossier.
9. **P1 - Standardize honesty and education primitives.** Add shared `fence()`, migrate bespoke fences, bridge web and Pat glossaries, and apply scaffold+glossary to dense pages.
10. **P1 - Expand Pat from glossary bot to estate navigator.** Generate nav-answer flows from `lens_registry`, then add data flows for attention/news/participants/ownership/seasonal/internals.
11. **P1 - Add route/nav/palette guardrails.** Test mounted routes vs lens inventory, enforce command palette from registry, and require orphan classification.
12. **P2 - Expert affordances.** Server CSV/API repro on dense tables, payload pagination, unified change-feed memory, and POST-only state changes.

---

## Claude closing (R2 — convergence reached, no further rounds)

All 14 B-findings CONFIRMED (B8/B11 narrowings accepted — evidence-based: 3 dual-system modules,
not zero; server CSV also on tracker/strategist exports). All 3 pushbacks conceded/adopted. The 7
partition adjustments are ADOPTED wholesale into `docs/ux-journey-audit-2026-07-13.md` §8 (S-H
parallel to S-A; lowercase hotfix into S-A; tracker decision day-zero; S-B split B1/B2 with the
classification table; S-C before S-E; S-F standalone program; POST-ify GETs pulled up to S-B2).
The joint Top-12 is recorded verbatim in §8-bis of the audit doc. Dialogue closed unanimous —
no ESCALATE items. This campaign's durable rules were folded into `docs/SURFACE-PLAYBOOK.md`
(canonical) + CLAUDE.md #9 / AGENTS.md #7 the same session.
