# Theme-Tags + Index-deepen — AUTONOMOUS NEXT-SESSION RUN-BOOK

> **Created session 32 (2026-06-22).** TRANSIENT (transient-doc-lifecycle): fold durable bits into
> `PROJECT_STATE.md`, then `git rm`, once shipped. The 3-workstream "dashboard-deepen" task is DONE — see
> `docs/dashboard-deepen-NEXT-SESSION.md` for that history. **This doc carries what's NEXT: the THEME-TAGS feature
> + index-page deepen + the open items.** Written so an AUTONOMOUS model continues with NO permission prompts.

---

## 0. OPERATING MODE (binding — Ramana was emphatic, repeatedly)

- **FULLY AUTONOMOUS, NO PERMISSION PROMPTS.** Blanket access is configured in `.claude/settings.local.json`
  (`defaultMode: acceptEdits` + bare `Bash/Edit/Write/Read/Glob/Grep/Agent/Task/WebFetch/Skill` allows). The **entire
  `D:\Hermes` folder AND the VPS (`ssh hermes`) are yours.** Never ask Ramana for file/git/shell/ssh/scp permission —
  it frustrates him. Just proceed.
- **🔴 BUILD ADDITIVELY — NEVER REMOVE OR REPLACE WHAT RAMANA BUILT.** This is THE hard lesson of session 31: I made
  the new `/dash/index` the click-target for every index and it dropped his RS + participants views → he was (rightly)
  furious ("you erased my hard work"). **Rule:** ADD new things; keep every existing page/feature/route reachable; if
  you re-point navigation, the destination MUST be a strict SUPERSET of the old one. When unsure whether something is
  "his," assume it is and preserve it. His pages `/dash/ratio`, `/dash/rrg`, `/dash/compare` are sacred.
- **WHEN IN DOUBT, CONSULT AGENTS, GO WITH THE MAJORITY.** For any non-trivial design/methodology/UX fork, spawn a
  read-only **Explore** panel (per segment / per question, 1–5 agents), take the call where the majority logically
  converges, then proceed. **You are the single builder — never let agents write the shared tree** (cross-absorption
  bit Ramana before). This is exactly how session 31/32 resolved the index-clarity, launchpad, and tag-design forks.
- **DEPLOY-AS-YOU-GO**, verify on the VPS, keep records current. Pause ONLY for a genuine visual-taste fork (show a
  `show_widget` mockup first) — never for permissions.
- **DATA-FIRST** (raw number beside every verdict) · **ZERO-LLM-AT-RENDER** · **HONEST LABELS** (no inflated stats —
  e.g. the Launchpad shows the real S1 backtest, not "63%/5.7×") · **NEVER REGRESS**. Do NOT edit
  `src/assistant/patearn.py`.
- **COMMIT cadence:** commit YOUR files locally as you ship (`git add <paths>`, **never `-A`** — the tree is shared).
  `cockpit.py` + `dashboard.py` are co-edited by the MEP stream, so your commits snapshot their deployed work — note
  it in the message; **never stage their separate files** (`mep_signals.py`, `deals.py`, the `*-design.md` docs).
  PROJECT_STATE.md is parallel-owned — only ADD your entry, never overwrite others'. Push at a safe point / at wrap.

---

## 1. CONCURRENCY REALITY (multiple sessions on ONE tree + ONE VPS)

Active parallel streams touching the shared tree / VPS — **do not clobber:**
- **MEP** (signed accumulation/distribution, Ramana's shorthand): `src/automation/mep_signals.py` + the screener
  **"accumulation · mep"** column (`g-mep`, `_mv_adbar`/`_mep_pill` in cockpit.py + `mep_signals` JOIN in dash_screener).
  Deployed, **uncommitted** by them.
- **RRG / RS-deepening:** `rs_extras` + `capture_signals` tables + `/dash/rrg` (`src/web/rrg_view.py`). RS-momentum,
  quadrant, RSI-of-RS, Mansfield, up/down-capture. Committed + pushed (`6ce8d46`/`30fb693`/`659e325`).
- **deals:** `src/automation/deals.py` + `bulk_block_deals` table (bulk/block + FII/DII). Feed is **~1 day old**
  (133 rows on 2026-06-19). Untracked. The Launchpad ⭐ reads it (`_lp_net_buyers`).
- **Pat** (NL search, `src/pat/*`), **CCI** (concalls, `concall_*`, `cci_pipeline.py`) — other streams.

**Survival:** prefer NEW modules; keep `dashboard.py`/`cockpit.py` edits additive; **CRLF-diff-check every `scp`**
(`diff <(tr -d '\r' < /tmp/vps.py) <(tr -d '\r' < local.py) | grep '^<'` — revert-lines must NOT touch MEP/RRG/etc.;
if they do, patch instead of overwrite). Backup `.bak` on the VPS before every scp.

---

## 2. CURRENT STATE (all LIVE on the VPS, verified this session)

**Shipped + deployed + committed + pushed (origin/main @ `d5d966a`), with the index-restore committed this session too:**
- **`/dash/index?idx=`** (`cockpit.render_index_detail`) — the index/sector detail page. Two-axis verdict (ABSOLUTE
  price trend BESIDE RS trend — the "trends not identified" fix; honest "NEAR HIGH/NEAR LOW"); own-price chart with
  **Candles/Line toggle + Daily/Weekly/Monthly/Quarterly + ranges + 50/200-MA**; the **RS-ratio chart** (sectors);
  for **SIZE indices** (Midcap 150 / Smallcap 250 / Next 50) a **relative-strength section** = its return vs Nifty 500
  per window + Compare link + RRG link; **the FULL sortable participants table for EVERY index** (incl. size — Midcap
  150 = 183 liquid members, Smallcap 250 = 283) with a Character (accum/dist) column; the equal-weight roll-up
  (breadth, RS leaders, accumulation split, ATH-DVPT); breadcrumb `← Markets · Sectors`.
- **`/dash/stock`** — wide cockpit, 7-tile verdict strip, 6-pane tabbed sub-nav (Price default), lazy RS chart,
  Candles/Line + 5Y. 4-pane chart sync untouched.
- **`/dash/launchpad`** — the validated explosive-move SETUP screen (D56). Fresh rising-edge triggers + ⭐ genuine
  net-buyer intersection; honest S1 backtest stats.
- **CCI** coverage (#Settled, Proven tile, screener #C, cci_state, cci_targets + repointed cron).
- **Markets** regime banner + momentum rotation + headlines card. Clarity pass (price-first ordering, levels, etc.).

**accumulation/distribution is intact (verified live, 5 places):** index roll-up "Accumulation split" + per-participant
Character column · stock page "Accumulation character" · screener Character group + the MEP signed column · home
"Stealth accumulation".

**Ramana's existing pages are PRESERVED + reachable:** `/dash/ratio` (RS-ratio + constituents + compare),
`/dash/rrg` (RRG/Mansfield/capture), `/dash/compare`.

---

## 3. THE NEXT BUILD — THEME TAGS (Ramana's decided spec)

**Concept:** a multi-label thematic classification of companies, BEYOND sector + index membership. One company can
carry several tags (e.g. an EPC name = `Infra` + `Industrialization-proxy` + `Transport/Logistics`). Re-decided each
**quarter** from results/financials (business mix shifts). **ADDITIVE** — a new layer beside index/sector, touching
neither.

**DECISIONS LOCKED (Ramana, session 32 — do not re-litigate):**
- **Assignment = AI-ASSISTED, HE APPROVES.** Store each company's business description (one-time); each quarter
  **Haiku** proposes theme tags from the description + latest results; Ramana approves/edits. (Honors "no Sonnet in
  jobs / Haiku only" + human-in-the-loop.)
- **Surfaces = ALL of:** stock page (tag chips) · a **Themes page** (browse/group by tag, like the sectors page) ·
  **screener filter + column** · **participant lists** (each member's tags) · **theme → participants** drill.

**BUILD ORDER (proposed — consult an agent panel on any fork):**
1. **Data layer (additive):** `company_tags(symbol, tag, source, confidence, as_of, approved)` in `db.py` SCHEMA_BASE.
   A controlled **vocabulary** seeded from the thematic indices (Infra, Defence, Capital Goods, Commodities, Consumer
   Durables, PSU, Power/Renewables, Transport/Logistics, Industrialization-proxy, IT, Pharma, Chemicals, Metals,
   Realty, Auto, Financials, FMCG, Healthcare, …) — let Ramana extend it.
2. **Business descriptions:** `fundamentals` has NO description today → add a `company_about` table (or column) and
   store the Screener "About"/business text on the existing Screener cadence (the text Haiku tags from).
3. **Tagging:** seed deterministically from index memberships (`source='index'`) so there's a baseline day one; then a
   **Haiku quarterly pass** (`src/automation/tagging.py`) reads description + latest results → proposes tags w/
   confidence (`source='ai', approved=0`); an **approval surface** (a `/dash/tags-review` page or a Telegram flow) lets
   Ramana approve/edit (`approved=1, source='ramana'`).
4. **Surfaces:** `_tag_chips(symbol)` helper in cockpit; stock-page chips; **`/dash/themes`** (`render_themes` — a
   count-strip of tags + a board/table per theme); screener **Themes** column-group + filter (extend `_SCREENER_JS`
   `TOG`); a tags column on participant tables; **`/dash/theme?tag=`** → that theme's participants.
- **Honest labels:** show tag SOURCE (index-seeded / AI-proposed / approved) + `as_of`; AI tags read "proposed" until
  approved.

---

## 4. OPEN ITEMS (smaller, prioritized)

- **Index polish (Ramana asked):** add the **signed-MEP accumulation score PER PARTICIPANT** in the index participants
  table (read `mep_signals`; today it's only on the screener) + an **"accumulating only" filter**; add a **Compare
  link on SECTOR** index pages too (size indices already have it).
- **"DBP" — UNRESOLVED.** Ramana said "still holding that position in DBP today" — meaning unclear (DVPT? a page? a
  deployment?). Ask him ONCE what DBP refers to, or infer from context, before acting.
- **Size-index RS depth:** the exact names `Nifty Midcap 150`/`Smallcap 250` are NOT in `rs_extras` (which has
  `CNX Midcap`, `Nifty Free Float Midcap 100`, …). If Ramana wants inline RRG/Mansfield depth for those exact names,
  the RRG job must compute those numerators — an RRG-stream change (coordinate / consult).
- **CCI "Proven names" = 0** until promises resolve; ~18 calls/night (free Gemini cap). Accelerator = paid Gemini /
  claude.ai-bulk — Ramana's spend call.
- **Launchpad ⭐ home-strip count** — deferred until the deals feed matures (>1 day of history).

---

## 5. DATA FACTS (verified — build on these, don't re-derive)

- **Size indices** (Midcap 150 / Smallcap 250 / Next 50 / Nifty 50 / Nifty 500): `broad_benchmark` NULL,
  `rs_vs_broad_*` NULL, NO `ratio_rows`. Their RS = return-vs-Nifty-500 (computed on-read) + the RRG-deepening in
  `rs_extras`/`capture_signals` (keyed by `(numerator, denominator)` under VARIANT names, denominators Nifty 500 /
  Nifty 50) + `/dash/rrg`.
- **Sectors:** `broad_benchmark='Nifty 500'`, full `rs_vs_broad_*`, `ratio_rows` vs Nifty 500 (e.g. Nifty Bank = 3521).
- `rs_extras(numerator,denominator,trade_date, rs_ratio, rs_momentum, quadrant, rsi_of_rs, mansfield, improving_entry,
  weakening_warning)`; `capture_signals(... down/up_capture_63/126/252 ...)`.
- `stock_index_membership`: Nifty 500=1510, Midcap 150=450, Smallcap 250=750, Next 50=160 (24 indices total).
- `mep_signals(symbol, trade_date, mep_score, mep_state)` — the signed accum/dist.
- `bulk_block_deals(trade_date, symbol, client_name, side, qty)` — 1 day so far; `client_classify.classify_client` +
  `CHURN` classify genuine buyers.
- `fundamentals` has **NO** business-description field (tags ingestion must add one).
- `sent_news(id, source, url, title, sent_at)` — no body/sector. `concall_scores(... n_concalls, n_promises_resolved,
  tier, as_of_period ...)`.
- CA-adjusted price: `from src.automation import adjust` → `adjust.adjusted_closes(rows)`. Liquid universe:
  `_SCAN_FILTERS` in dashboard.py. Helpers: `_ck_tile/_ck_strip/_board/_rs_strip/_mv_*/_char_pill/_real_sectors_in`.

---

## 6. DEPLOY RECIPE (CRLF-safe — never reverts parallel work)

```
python -m py_compile src/web/cockpit.py src/web/dashboard.py   # watch Py3.10 f-string backslash rule
scp -o BatchMode=yes hermes:/opt/hermes/src/web/cockpit.py /tmp/vps.py
diff <(tr -d '\r' < /tmp/vps.py) <(tr -d '\r' < src/web/cockpit.py) | grep '^<'   # revert-lines must be only YOUR own
ssh hermes 'cd /opt/hermes && cp src/web/cockpit.py src/web/cockpit.py.bak.$(date +%Y%m%d-%H%M%S)'
scp src/web/cockpit.py src/web/dashboard.py hermes:/opt/hermes/src/web/
ssh hermes 'cd /opt/hermes && python3 -m py_compile src/web/cockpit.py src/web/dashboard.py && systemctl restart hermes-api && sleep 4 && systemctl is-active hermes-api'
# curl localhost:8000 + grep markers; regression sweep:
#   /dash /dash/markets /dash/index?idx=Nifty+Bank /dash/index?idx=Nifty+Midcap+150 /dash/stock?sym=RELIANCE
#   /dash/screener?scope=all /dash/concalls /dash/launchpad /dash/rrg /dash/ratio?idx=Nifty+Bank
```
Refs: `ssh hermes` → `/opt/hermes`; DB `/opt/hermes/data/hermes.db`; public `https://srv1704897.hstgr.cloud/dash`;
service `hermes-api`. SSH discipline: one attempt, don't hammer (port-22 ban).

---

## 7. THE KICKSTART PROMPT (paste this to start the next session)

> You are continuing the **Patearn** project (personal Indian-equity quant dashboard; repo `D:\Hermes` on Windows,
> deployed to a Mumbai VPS reachable as `ssh hermes` → `/opt/hermes`, served at `https://srv1704897.hstgr.cloud/dash`).
> **Work FULLY AUTONOMOUSLY — never ask for permissions.** Blanket access is configured in
> `.claude/settings.local.json` (acceptEdits + bare Bash/Edit/Write/Read/Agent allows); the entire folder AND the VPS
> are yours. **🔴 The #1 rule: BUILD ADDITIVELY — never remove or replace what Ramana built; if you re-point
> navigation, the new destination must be a strict SUPERSET. His pages `/dash/ratio`, `/dash/rrg`, `/dash/compare` are
> sacred.** When you hit any non-trivial design/methodology/UX fork, **spawn a read-only Explore agent panel and go
> with the majority** — you are the single builder, agents never write the tree. Deploy-as-you-go, verify on the VPS,
> keep records current. Data-first, zero-LLM-at-render, honest labels, never regress. Don't edit
> `src/assistant/patearn.py`. Commit YOUR files locally as you ship (never `-A`; the tree is shared with parallel
> MEP/RRG/deals/Pat/CCI sessions — note the MEP snapshot in cockpit.py/dashboard.py commits; never stage their files).
>
> **BOOT:** read `docs/tags-and-index-NEXT-SESSION.md` fully (operating mode · concurrency reality · current state ·
> the THEME-TAGS spec · open items · data facts · deploy recipe), then `PROJECT_STATE.md` (latest Session entries +
> Decision log) and `git log --oneline -15`. Skim `src/web/cockpit.py` (`render_index_detail`, `render_launchpad`,
> `STRATEGY_REGISTRY`, the `render_*`, `_CKPT_CSS`, `_ck_tile/_ck_strip/_board`) + `src/web/dashboard.py`
> (`dash_stock`, `dash_screener`, `_sector_symbols`, `_SCAN_FILTERS`, `adjust`).
>
> **BUILD — the THEME-TAGS feature (Ramana's locked spec):** a multi-label thematic tag layer (a company can be
> Infra + Industrialization-proxy + Transport at once), ADDITIVE beside sector/index, **AI-assisted (Haiku proposes,
> Ramana approves), refreshed quarterly from business descriptions + results**, surfaced on the **stock page (chips) ·
> a new Themes page (`/dash/themes`, like sectors) · the screener (filter + column) · participant lists · a
> `/dash/theme?tag=` drill**. Build order: (1) `company_tags` table + a vocabulary seeded from the thematic indices;
> (2) store Screener business descriptions (`fundamentals` lacks them — add a `company_about` table); (3) a deterministic
> index-seed + a Haiku quarterly tagging job (`src/automation/tagging.py`) + an approval surface; (4) the four UI
> surfaces. Honest labels: show tag source (index/AI-proposed/approved) + as_of.
>
> **THEN the open items:** signed-MEP accumulation per participant on the index page + an "accumulating only" filter;
> a Compare link on sector index pages; ask Ramana once what "DBP" meant. Deploy each piece (CRLF-diff-checked) and
> post the URL; only pause for a visual-taste fork (mockup first).
