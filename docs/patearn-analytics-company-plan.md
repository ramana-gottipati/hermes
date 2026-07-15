# Patearn Analytics Company Plan — the adaptable-layers roadmap (D134)

> **Lifecycle: LIVING.** The company-level operating plan: what Patearn is as a business, the
> layer architecture every future component must snap into, the validated regulatory posture,
> the cost model, and the rated component roadmap. Maintained like `PROJECT_STATE.md` (update
> in the same commit as any change to posture/costs/roadmap). Registered in `docs/DOC_INDEX.md`
> (CANONICAL). Relationship to `docs/patearn-charter.md`: this plan is the D134 amendment layer —
> the charter's §NOW queue (v1.1) is fully shipped; Ramana ratifies this plan's §6 as the charter
> v2.0 NOW queue at the next charter review, or amends it by D-log entry.

---

## 0. Mandate (Ramana, 2026-07-14/15 — binding intent)

1. **A core analytics-focused stock-market analytics company** — NOT a portfolio-management
   firm, NOT selling portfolios, NOT selling signals/calls.
2. **No SEBI registration at this stage** (no RA, no RIA). Validate that an analytics company
   can operate unregistered — validated with boundaries in §3.
3. **Portfolios stay an internal organizing construct** — a way to structure analysis and
   Ramana's own capital decisions. Any buy/sell decision is discussed and ratified privately
   between Ramana and the machine; it is never published, never a product.
4. **Machine-generated signals are never trusted raw** — every generated artifact is checked,
   verified, and evaluated with human input before it counts (§2 L5, the Judgment layer).
5. **AI-generated components are the product focus** (§2 L6) — grounded in our own data,
   compliance-linted, human-reviewed.
6. **Adaptable layers over features.** Anything that may arise later must snap into a layer
   contract (a manifest, a registry row, an adapter) — never require a rebuild.
7. **Modest budget, structured and machine-tracked** (§5). Real-time infrastructure is designed
   as a seam now, paid for only when activated, and public real-time is explicitly deferred.

## 1. Company thesis

**One analyst, thousand-analyst output.** Patearn is one human analyst (editor-in-chief and
final judgment) amplified by an AI workforce over a proprietary, point-in-time, primary-source
Indian-market data estate. The product is never advice — it is **explanation, evidence, and
tools**: descriptive analytics, honest backtest verdicts (failures included), PIT
"what-was-knowable-when" rigor, and AI-drafted narrative that a human has verified. The
falsification ledger and the descriptive-only fences — built as epistemic discipline — turn out
to be the **legal moat too** (§3): the same properties that make the analytics honest keep the
company outside the recommendation-regulation perimeter. Trust is the product; the fence is the
license.

## 2. The Patearn OS — nine adaptable layers

The adaptability mandate, made concrete: each layer has a **contract** (how new things plug in).
A future component that doesn't fit a contract is a design smell; extend the contract, don't
bypass it.

| # | Layer | Contract (how new things plug in) | Exists today | Gap |
|---|---|---|---|---|
| L0 | **Metal** | VPS + systemd + SQLite; every job is a unit with hardening + OnFailure pager | solid (40+ units) | cost-ledger observability; disk headroom plan |
| L1 | **Acquisition** | a feed = fetcher (via `fetch_retry`) + PIT stamps + D94 fence + **feed manifest** (source, cadence, licence-class, knowable_at rule) | fetchers + fences exist | the manifest itself; **licence-class field** (§3.4) |
| L2 | **Canonical PIT store** | every row carries its knowable-at clock; `security_master` is the entity spine | strong (provenance, knowable_at) | the **entity graph** (promoters/auditors/group cos/counterparties) |
| L3 | **Derivation** | a derived series = engine module + **signal manifest** (inputs, owner formula in `calculations-and-weights.md`, validation status, fence) + compute-on-read doctrine | ~95 engine modules | the manifest; the site-wide **as-of (time-machine) capability flag** |
| L4 | **Evidence** | every claim enters via `prereg.py` (hashed gate) → cost-loaded, placebo-controlled, OOS-split → ledger entry (win or lose) with its ONE reopen-condition | prereg + placebo + ledger live | M-03 deflated-Sharpe wiring; machine-readable verdict objects |
| L5 | **Judgment (human-in-the-loop)** | every AI/rule artifact above a threshold lands in ONE **Review Inbox** (approve/reject/annotate); decisions persist as the **judgment corpus** | embryonic (tags-review, alert ack, tracker) | the unified inbox primitive + corpus schema |
| L6 | **Composition (AI-generated components)** | generated narrative/briefs are grounded ONLY in our own tables, pass the compliance gate, carry an "AI-drafted, human-reviewed" label, and are budget-capped | Pat (deterministic), enrich (paused) | the **auto-analyst** event briefs; explain-this-page |
| L7 | **Delivery** | a surface = a `lens_registry` row (SURFACE-PLAYBOOK); an API consumer = a metered `/v1` key with quotas; exports = CSV/JSON contract | lenses + `/v1` metering/quotas + Telegram + Pat | MCP personal bridge (claude.ai ↔ VPS); everything-as-CSV completion |
| L8 | **Governance-as-code** | a rule = a gate that FAILS the suite (route gate, education gate, doc-hygiene, state-doc) | 4 gates live | the **compliance-language gate** (started S149); licence-class enforcement; budget alerts |

Why this matters commercially: layers L1–L4 are the moat (data + rigor), L5 is the proprietary
asset nobody can copy (a labeled corpus of one analyst's verified judgments), L6–L7 are the
product surface, L8 is what lets one person run a company safely.

## 3. Regulatory posture (researched 2026-07-15 — business research, not legal advice; engage counsel at the §3.5 triggers)

### 3.1 The validation Ramana asked for

**His assumption is broadly CORRECT: a stock-market analytics company that does not issue
buy/sell/hold recommendations, target prices, or personalized advice does not require SEBI
Research Analyst or Investment Adviser registration.** The load-bearing provisions:

- SEBI (Research Analysts) Regulations, 2014 — reg. 2(1)(w) — defines "research report" and
  **excludes**: comments on *general trends* in the securities market; discussions on
  *broad-based indices*; commentaries on *economic, political or market conditions*;
  **statistical summaries of financial data of companies**; *technical analyses relating to
  demand/supply in a sector or index*; internal communications; offer documents. Patearn's
  descriptive estate (EOD statistics, screeners on user criteria, sector/index rotation reads,
  market internals, glossaries, education) lives inside these exclusions.
- SEBI's RA FAQs (circular SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/105, July 2025) restate the
  exclusion list and do **not** pull data/tool/analytics platforms into scope where no
  recommendation is made.
- IA Regulations 2013: "investment advice" requires advice on buying/selling securities,
  personalized, **for consideration**. Patearn has no clients, no fees, no personalization —
  out of scope entirely.
- Managing anyone else's money = PMS licence (₹5cr net-worth class). Explicitly out — Ramana
  has ruled out being a portfolio-management firm.
- **Trading his own account and ratifying internal decisions requires no registration at all.**
  The regulated act is *communicating recommendations to others*, not deciding for oneself.

### 3.2 The boundary table (what keeps us out vs. what pulls us in)

| Stays outside the perimeter (keep doing) | Crosses into RA/IA territory (never do unregistered) |
|---|---|
| EOD data display from our own archives; statistical summaries per company | Buy/sell/hold recommendations or target prices on specific securities — **even free** (SEBI has acted against unregistered tip-givers regardless of payment) |
| Screeners where the USER sets criteria; charting; glossaries | Rankings framed as "top stocks to buy" or any action framing |
| Sector/index technicals, rotation, breadth, market commentary | Single-stock advice dressed as "education"; live-price "education" (the Jan-2025 framework expects ~3-month-old data for unregistered educators) |
| Honest backtest records incl. failures, framed as research history | Performance claims used to solicit ("we returned X%, subscribe") — restricted for unregistered persons (Oct-2024 framework) |
| Model-portfolio pages as **historical simulation exhibits** (no subscription, no follow-along CTA) | Model portfolios as a client product — SEBI has pushed even *registered* RAs away from model-portfolio products (2025 settlement order) — validates "never sell portfolios" |
| Internal/private decisions for Ramana's own capital | Publishing those ratified decisions to any external user |

### 3.3 The honest gray zone (where the assumption needs care)

**Proprietary house scores on single stocks** (patearn tiers T1–T4, Conviction, Wolfe §B
strength) sit between "statistical summary" (excluded) and "recommendation" (regulated). The
industry pattern is telling: score-publishers register (Trendlyne, whose DVM scores ship under
RA registration INH000022507; MarketsMojo similarly operates registered), while pure
data/screener platforms (user-criteria screeners, charting) operate unregistered. Patearn's
current posture is defensible because the scores are (a) methodology-transparent statistics,
(b) fenced descriptive-only with no action verbs, and (c) not sold to clients. **The moment we
monetize public access with single-stock verdict-scores, we get a written legal opinion first
(₹15–50k) and either reframe the scores or register.** Second care-point: our education
surfaces use recent data — fine as analytics/data display, but if anything is ever packaged as
a *course/education service* or involves association with regulated entities (broker
partnerships, ads), the live-price education restriction applies — counsel item, not a
blocker today.

### 3.4 Standing mitigations (the posture, engineered)

1. **Fence vocabulary** (`infographics.fence()`, `_FENCE_COPY`) — already the single source of
   the descriptive-only boundary wording on every surface.
2. **Compliance-language gate** (NEW, started S149, `tests/test_compliance_language_gate.py`) —
   the suite FAILS if any web/Pat source ever contains solicitation/recommendation phrases
   ("you should buy", "target price of", "sure shot", "guaranteed returns", …). The legal
   posture stops being a convention and becomes a machine invariant, which also fences the L6
   AI-generated components by construction.
3. **Licence-class registry** (queued) — every feed and surface tagged `public-archive` /
   `licensed` / `personal-broker`; a gate blocks `licensed`/`personal-broker` data from public
   rendering. This is what makes the real-time seam (§4-I) safe to ever activate.
4. **Private/public split** — anything decision-shaped (books, diffs, ratified calls) lives
   behind the owner gate (`tracker_gate` pattern); public = descriptive only.
5. **AI labeling** — every L6 artifact carries "AI-drafted, human-reviewed" + generation date.
   (SEBI's AI-disclosure rules currently bind *registered* RAs/IAs, but adopting the norm now is
   free future-proofing and honest product.)

### 3.5 Re-visit triggers and the cost of each future option

| Trigger | Action | Cost class |
|---|---|---|
| Any plan to monetize public access with single-stock scores | Written legal opinion (securities counsel) | ₹15–50k one-time |
| A decision to publish anything recommendation-shaped | Individual RA registration: NISM-XV cert + application/registration + client-banded deposit (₹1L ≤150 clients … ₹10L >1,000) | ~₹20–50k + ₹1L refundable deposit |
| Wanting verified performance claims in marketing | PaRRVA route (registered entities only) | later |
| Managing external capital | PMS licence | ₹5cr net worth — **ruled out** |
| Broker/regulated-entity partnership or advertising | Oct-2024 association-framework compliance check | counsel hour |

Note: the RA regulations were amended again in late 2025 (Second Amendment) — the boundary
provisions above were re-verified via the July-2025 FAQ layer, but any counsel engagement
should confirm the then-current consolidated text.

**Sources:** [SEBI RA Regulations 2014 (consolidated Dec 2024)](https://www.sebi.gov.in/legal/regulations/dec-2024/securities-and-exchange-board-of-india-research-analysts-regulations-2014-last-amended-on-december-16-2024-_90153.html) ·
[SEBI RA FAQ circular July 2025 (PDF)](https://www.sebi.gov.in/sebi_data/faqfiles/jul-2025/1753269723942.pdf) ·
[TaxGuru analysis of the July-2025 RA FAQs](https://taxguru.in/sebi/comprehensive-analysis-sebi-s-faqs-research-analysts.html) ·
[LKS on the 2025 FAQs](https://www.lkslaw.com/insights/articles/key-clarifications-under-the-sebi-issued-faqs-2025) ·
[SEBI RA (Second Amendment) Regulations 2025](https://www.sebi.gov.in/legal/regulations/nov-2025/securities-and-exchange-board-of-india-research-analysts-second-amendment-regulations-2025_97961.html) ·
[zfunds summary — 2025 RA changes (deposits, part-time RA, AI disclosure)](https://zfunds.in/m/sebi-research-analysts-regulations) ·
[Legal500 — Oct-2024 restrictions on association with unregistered persons](https://www.legal500.com/developments/thought-leadership/securities-law-update-sebi-imposes-restrictions-on-intermediaries-and-finfluencers/) ·
[Business Standard — Jan-2025 education/live-price rules](https://www.business-standard.com/markets/news/sebi-finfluencer-circular-live-stock-data-market-education-rules-125013000571_1.html) ·
[NatLawReview — SEBI settlement order on RA model portfolios](https://natlawreview.com/article/sebi-settlement-order-research-analysts-not-to-provide-model-portfolio-products) ·
[SEBI IA FAQs](https://www.sebi.gov.in/sebi_data/attachdocs/1424862077270.pdf) ·
[NSE real-time data tariff (domestic vendors, Apr-2025)](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Real_Time_Tariff_Domestic_01042025_.pdf) ·
[Zerodha — free personal Kite Connect APIs](https://zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect) ·
[Zerodha Kite API charges](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/what-are-the-charges-for-kite-apis)

## 4. Component roadmap (rated + costed)

Scores /10; **bold** = the driving axis. "₹0" = runs on the existing box with rule-based code.

| ID | Component | Layer | Imp | Crit | Timing | Cost | Status |
|---|---|---|---|---|---|---|---|
| A | Compliance-language gate | L8 | 9 | **10** | NOW | ₹0 | **LANDED S149** (`de16db6`, in the suite) |
| B | Cost-ledger + estate heartbeat (one morning line: health + ₹ spend) | L0/L8 | 7 | **8** | NOW | ₹0 | **LANDED S150** (LANE-R merge; producers instrumented via `llm.meter()` — core/router/chat/patearn; unit install + arm = LANE-R deploy, §Session 150) |
| C | Licence-class registry + feed/signal manifests | L1/L3/L8 | 8 | **8** | next | ₹0 | **LANDED S151** (LANE-R merge; licence gate in the suite; 6 vendor-ToS feeds UNCLASSIFIED → §7.7 Ramana) |
| D | Review Inbox + judgment corpus (the human-verification layer) | L5 | **9** | 7 | next | ₹0 | **LANDED S152** · first producer **WIRED+LIVE S157** (`inbox_adapters.py` sync/apply/backfill; 295-decision corpus imported @ 94% approve-rate; weekly `--sync --apply` on the theme-seed oneshot; surface per SURFACE-PLAYBOOK later — that session also bridges-or-read-onlys the legacy tags surface) |
| E | Auto-analyst event briefs (AI-drafted, inbox-reviewed) | L6 | **9** | 6 | after D | ₹100–300/mo capped | **LANDED S153** (results family v1; template ₹0 default, LLM opt-in cap-gated ₹200 §7.2; briefs land in the Review Inbox — wire publisher later) |
| F | Time-machine contract (site-wide `?asof=` capability audit + flags) | L3/L7 | **8** | 5 | mid | ₹0 | audited S149 (`docs/time-machine-audit.md`: 5 yes / 34 partial / 28 no · top-5 upgrades ranked · cockpit tile overclaim **FIXED by LANE-R** — symbol-scoped wording; `asof_capable` flags still to land) |
| G | Entity graph (promoter/auditor/group/counterparty network from filings) | L2 | **8** | 4 | mid | ₹0 | **LANDED S155** (`entity_graph.py`: 6 edge kinds incl. pledge-lender; co-links via a shared counterpart; descriptive-only — no score column exists, ledger E-03/accumulation cited; surface deferred) |
| H | Rule-lab (user-defined rule → the evidence factory runs the gates → honest verdict) | L4/L7 | **8** | 4 | later | ₹0 | **DESIGN LANDED S156** (`docs/rule-lab-design.md`: closed-vocab grammar → factory gauntlet → ledger-vocabulary verdict; BLOCKING table verbatim as an auto-cite wall; SEBI + the 12-row playbook pre-filled. Build = its own session) |
| I | Real-time seam (adapter interface now; Kite personal feed optional; public real-time DEFERRED) | L1 | 7 | **6** | design next | ₹0 now / ₹500/mo optional | **LANDED S153-b** (interface + bounded window + Null/T0Lite stub; personal-broker manifest row → licence-gate fenced; no Kite wiring) |
| J | XBRL Phase-3 completion (backfill pilot → universe → retire residual scrape) | L1/L2 | 10 | **10** | NOW | ₹0 | in-flight (S148 lane) |
| K | UX S-program continuation (S-B1 rest → S-B2 → S-E rest → S-F → S-G) | L7 | **7** | 5 | rolling | ₹0 | in-flight |
| L | Evidence factory completion (M-03 wiring; armed studies E-02/E-14/E-04 self-fire) | L4 | **8** | 5 | self-gating | ₹0 | armed |
| M | Legal opinion + trademark/name check | — | 7 | **9 at trigger** | before monetization | ₹20–60k one-time | decision file |
| N | MCP personal bridge (claude.ai ↔ VPS data, kills copy-paste) | L7 | **7** | 3 | later | ₹0 | designed (old item L) |

### The net-new components, specified

**A — Compliance gate.** §3.4(2). Conservative phrase-level lexicon over `src/web` + `src/pat`
source with a reasoned allowlist; runs in the suite beside the route/education gates. Extends
automatically to L6: generated narrative is linted with the same lexicon before render.

**B — Cost-ledger + heartbeat.** Composes the existing checks (`board_health`, feed-liveness,
timer results, alert-rail criticals) into ONE positive morning DM line, and adds a ₹-meter:
every LLM-calling job logs tokens×rate to a `cost_ledger` table; the DM carries month-to-date
spend vs cap. Budget discipline becomes machine-checked (§5.5), not remembered.

**C — Licence-class registry + manifests.** The feed manifest (L1) and signal manifest (L3) as
small declarative tables/dataclasses beside the code. Adding feed #41 or derived series #200 =
adding a manifest row + the module; the manifests power auto-docs, the licence gate, DQ
coverage, and Pat's answers about data provenance. This is the single highest-leverage
*adaptability* investment: it converts tribal wiring into declared contracts.

**D — Review Inbox + judgment corpus.** One queue for every artifact the machine wants a human
to see (new tag proposals, auto-analyst drafts, anomaly flags, study verdicts, rebalance diffs
for the private book). Approve / reject / annotate; every decision lands in a
`judgments(artifact_kind, artifact_ref, verdict, note, decided_at)` corpus. Over time:
agreement-rate per generator family (which machine outputs earn trust), and a labeled dataset
that is literally purchasable by no competitor. This is the direct build-out of the mandate's
"checked, verified, evaluated with human input."

**E — Auto-analyst event briefs.** Event-triggered (a result lands, a rating changes, a SAST
filing, a band-lock, a rotation phase flip): a cheap-model drafts a 6–10 line descriptive brief
grounded ONLY in our tables (with per-number source links), passes the compliance lexicon,
lands in the Inbox; approved briefs publish to the wire/dossier with the AI label. Hard monthly
token cap; degrades to template-text at cap. This is the "AI-generated components" centerpiece
— the AI associate whose work the analyst signs.

**F — Time-machine contract.** The PIT estate's flagship property, made universal: every lens
declares `asof_capable: yes/no/planned` in its registry row; capable lenses accept `?asof=` and
render exactly what was knowable then. Uniquely defensible in the Indian retail-analytics
market and pure L2 dividend.

**G — Entity graph.** We already ingest the filings that carry relationships (insider/SAST
parties, deal counterparties, auditors via announcements, promoter pledges, group companies).
Build `entity_edges(src, dst, kind, first_seen, source_ref)` and a per-company "neighborhood"
panel (promoter network, shared auditors, repeat counterparties, pledge chains). Descriptive
relationship analytics — an under-served niche in India and a genuinely new analytical
direction for us, not a re-sort of price data.

**H — Rule-lab.** The user (first Ramana, later paying users) brings a rule in a closed
vocabulary (the Pat pattern); the evidence factory (L4) runs it through the SAME gates
(cost-loaded, placebo, capacity, OOS) and returns the honest verdict + the ledger context.
"Bring your idea, we'll kill it honestly." Sells the *factory*, never a recommendation — the
user directs, we compute. This is the eventual flagship analytics product.

**I — Real-time seam.** Decide the boundary now, spend later: (a) an `intraday_adapter`
interface (quote snapshot → normalized rows → bounded rolling window, raw ticks never enter the
canonical store — space doctrine); (b) personal activation path = Kite Connect (personal API
free; live+historical ₹500/mo) tagged `personal-broker` licence-class → INTERNAL analytics
only, never publicly rendered; (c) public real-time/delayed display = NSE authorized-vendor
tariff territory (per-medium fees; redistribution multiples) — **flagged NOT-modest, deferred
indefinitely**; the licence gate makes the deferral structural. Plus "T+0-lite": ingest the
free EOD preliminary files at 15:45–16:15 IST so the evening picture lands hours earlier — ₹0.

## 5. Cost model (structured)

### 5.1 Current run-rate (unchanged by this plan)

| Item | ₹/month | Note |
|---|---|---|
| VPS (Hostinger KVM4, prepaid → 2028) | ~1,300 amortised | sunk |
| Anthropic API (runtime jobs) | 150–300 | $10 console cap |
| claude.ai subscription (deep dives) | 1,700 | existing |
| Claude Code build sessions | 200–500 / session | the real variable — bundle work |
| All data feeds (NSE/BSE archives, Telegram, GitHub) | 0 | primary/free |

### 5.2 Incremental, per component

| Component | ₹/month | One-time |
|---|---|---|
| A, B, C, D, F, G, H, N (rule-based on existing box) | 0 | 0 |
| E auto-analyst briefs | 100–300 (hard cap in code) | 0 |
| I real-time personal activation (optional, when wanted) | 500 (Kite Connect w/ data) | 0 |
| Disk/RAM headroom upgrade (only when DB growth demands) | +500–800 | 0 |
| M legal opinion (at monetization trigger) | — | 15,000–50,000 |
| Trademark "Patearn" (optional, cheap insurance) | — | 5,000–15,000 |
| Pvt Ltd incorporation + annual compliance (defer until revenue/contracts; sole-prop = ₹0 now) | ~1,500–2,500 eff. | 10,000–30,000 |
| Domain + mail | ~100 | — |

### 5.3 Flagged NOT-modest (deferred by design, seam built instead)

Public real-time or delayed intraday display (NSE data-vending agreements, per-medium tariffs,
redistribution multiples — lakhs/yr class) · any commercial data vendor · PMS path (₹5cr) ·
paid model upgrades in scheduled jobs (Guardrail #3 stands).

### 5.4 Budget law (machine-enforced once B ships)

Steady-state runtime target **≤ ₹2,500/month** excluding Claude Code build sessions. Every
LLM-calling component ships with a hard monthly cap and logs to the cost-ledger; the morning
line reports month-to-date vs cap. Exceeding cap = degrade to templates, never silent overrun.

## 6. Execution queue (from S149)

1. **S149 (this session):** this plan committed + compliance gate A v1 in the suite.
2. **S150:** B — cost-ledger table + morning heartbeat line (compose existing checks; DM plumbing exists).
3. **S151:** C — feed manifest v1 + licence-class registry + the licence gate.
4. **S152:** D — Review Inbox primitive (generalize tags-review/ack) + judgment corpus schema.
5. **S153:** E — auto-analyst brief v1 on ONE event family (results), capped, inbox-gated.
6. **S154:** F — as-of capability audit; declare flags in `lens_registry`; close easy gaps.
7. Rolling thereafter: G entity-graph v1 → I seam interface → H rule-lab design doc.
   Parallel lanes continue unchanged: J (XBRL pilot → universe), K (UX S-program), L (armed studies).

## 7. Decisions reserved for Ramana

1. Ratify this plan as the charter v2.0 base (or amend by D-log).
2. E's monthly token cap value (default proposal: ₹200).
3. I's personal activation timing (₹500/mo Kite data — not needed until an intraday question matters).
4. Trademark spend now vs later.
5. Acknowledge the §3.5 trigger contract: no public monetization of single-stock scores before the legal opinion.
6. The S148 numbering/duplicate-commit reconcile (two lanes both used "S148"; S-B1 item-2 exists as patch-twins `a781669`/`29e4169`) — owning lanes to reconcile at next push.
7. **Vendor-ToS enum for the 6 legacy feeds LANE-C could not honestly classify** (screener · fundamentals_history · shareholding_history · concalls-discovery-index · news_feed · enrich — all Guardrail-#8 remediation targets): add a fifth licence class `vendor-tos-remediating` (gated off public surfaces like the restricted classes) vs. keep them out of FEEDS until the XBRL/BSE migrations retire them.

## Maintenance

Update this file in the same commit as: any regulatory-posture change (new SEBI
circular/amendment touching §3), any cost-model change (§5), any component landing (flip §4
Status), any queue re-rank (§6). The §3 sources list carries the verification date — re-verify
at every counsel engagement and at least each results season. Twin references: `PROJECT_STATE.md`
D134 (decision record) · `docs/patearn-charter.md` (operating doctrine this plan amends).
