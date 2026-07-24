# Patearn Charter — operating doctrine (CEO mode)

**v1.1 — amended 2026-07-07 by D-log D92** (evidence-driven corrections per §10: D-05 re-scoped ·
X-02 closed-by-evidence · X-06 half-built · E-06 needs no D-02 · NOW-queue statuses). Original
v1.0 2026-07-05. Canonical roadmap (PROJECT_STATE D87). Sessions execute § NOW by default;
deviations = new D-log entries. Reviewed every results season. Binding constraints are inherited,
not renegotiated here: ≤₹300/mo API spend · primary sources only (CLAUDE.md #8) · cheap models in
timers · failure-ledger discipline (cite numbers before re-attempts) · surface-first only for paid
spend / deleting others' work / DB-destructive / publishing.

---

## 1. Thesis

Patearn is the **research OS for Indian equities**: verified primary-source data, point-in-time
honesty, and descriptive intelligence — **never signal-selling**. Fourteen years of our own
backtests say the fund-shaped product is a mirage (nothing beats Nifty-500 B&H net at scale;
ledger passim); the durable asset is the **evidence machine**: PIT clocks nobody else has
(`provenance_knowable`, ground-truthed to actual announcement days), event harnesses that
falsify honestly, and published spec-sheets *including the failures*. Trust is the product.
The 2026-07-05 pair of studies is the proof pattern: a confirmed descriptive edge (PEAD
delivery-interaction) AND a falsified detector (footprint gate FAIL) both went to the ledger
with exact numbers the same day. That discipline, at results-season speed, is what a PMS/AIF
buyer cannot build in-house and cannot get from a vendor.

## 2. Operating principles (CEO restatement)

1. **Every claim enters through a pre-registered gate.** Hypothesis + readout + pass/fail
   threshold written BEFORE the run (in the module docstring); result → ledger, win or lose.
2. **Event-time is the open frontier; calendar-time ranking is closed** (ledger-proven).
   The `pead.py` harness (real-date events, no-leak trailing ranks, tier+ATR costs) is the
   template — new studies reuse it, not reinvent it.
3. **Descriptive ≠ apologetic.** A validated descriptive lens (Wolfe-bull, harmonic, PEAD cells,
   trade-size ratio) is a sellable data product with a spec sheet; an unvalidated one is a bug.
4. **Capacity ceilings are moats.** Anomalies that die at AUM (band-locks, buyback quotas,
   T2T exits) persist *because* institutions can't touch them — personal-scale sleeves and
   client-side analytics, never fund pitches.
5. **Correctness before novelty.** A contamination bug in a live signal (see T2T/BE mask, X-02)
   outranks any new study.

## 3. NOW — week of Jul-05 → Jul-12 (results season opens ~Jul-09)

| # | Item | Gate / deadline |
|---|---|---|
| N1 | **Results-season war room — LIVE + self-refreshing (S80d/S80e, ahead of Jul-09).** `/dash/results-reactions` shows BOTH halves: forward **"Upcoming results — next 14 days"** (NSE board-meeting calendar, D-01) + the "just reported" delivery-confirmed reaction table. Calendar refreshes **nightly** via `hermes-results-calendar.timer` (02:00 UTC, `Persistent=false`, sandboxed, git-owned per AUD-27) AND ran on-demand to validate the path today. Scanner is a **first-class Markets nav lens** (`/dash/markets/results-reactions`; flat 307→nested; sub-nav link live) — no longer URL-only. | **DONE** |
| N2 | **Data sprint wave-1** (D88): ~~D-02~~ ✓ · ~~D-03~~ ✓ (both LIVE S83c, `surveillance.py` + armed timer) · ~~D-04 SLB volumes~~ **✓ LIVE (S95)** — `src/automation/slb.py` (SLB bhavcopy fees/qty/value + open-positions short-interest stock, nsearchives statics, per-day commits) + `hermes-slb.timer` 15:15 UTC (Requires-free, hardened, paged) + 21-day seed (2,924 vol rows / 358 syms · 12,913 open-pos rows) · ~~D-05 history backfill~~ **RE-SCOPED by D92** — free history doesn't exist (`deals.py:11`); the feed accumulates forward | **N2 COMPLETE** |
| N3 | ~~Trade-size ratio~~ **DONE (S83c)** — `ticket_ratio_1m_6m` live on Screen+/Positioning/stealth/dossier + glossary (D89 survivor numbers cited; stored column justified by the cross-sectional scan, latest-date fill + nightly) | shipped descriptive-only |
| N1b | **Results-Reaction SCANNER — LIVE `/dash/results-reactions` (S80c):** the descriptive board from the (falsified-as-a-book) PEAD study — who just reported, was the surprise delivery-confirmed, realized +22/+60d drift, population base-rate as labelled context. Nightly `results_reactions` snapshot (research venv) → pure-stdlib view (house pattern, like momentum-scan). Mounted surgically on the forked live `v2_surfaces.py` (import-tested, curl-verified 200). ~~Remaining: nightly-chain wiring + nav-lens entry~~ **✓ both closed (ticked S95):** the `hermes-results-reactions` snapshot timer is live-verified (S83b/S80h) + the Lens is committed in `lens_registry.py` (markets) with the nested URL serving | **DONE** |
| N4 | ~~Event-study library~~ **DONE (S83d) as a FACADE** — `evlib.py` is the one import surface over `pead.py`/`footprint.py` (source of truth unmoved: the nightly war-room snapshot imports pead directly; no mid-season migration) **+ M-02 placebo harness pulled forward** (shuffled-date null, published convention, first number = the PEAD confirmed cell) | selftest ✓ |
| N5 | ~~Verify Jul-05 concall run + first sandboxed nightly chain~~ **DONE (S83b)** — concall-capture Jul-05 SUCCESS (1h44m); backups clean ×2; drift gate clean; **bonus root-cause: the provenance 7-col INSERT crash (fixed + paged)** | ops ✓ |

## 4. NEXT — July/August

- **E-02 Credit-rating drift study** — **ARMED S85e (2026-07-10): gate frozen + hashed
  (`fb1525c7859a…`, M-04); self-gating `rating_drift.py --run` fires monthly on the 22nd
  (first: 2026-07-22 per the post-flood anchor), ABORTS-with-census per its own pre-registration
  until the sample reconciles (≥300 deduped actionable + ≥8 qtr cohorts).** The mapping widen is
  built in (compute-on-read: equity-ISIN + conservative name-match; +5 events, all ISIN).
  **Baseline finding (2026-07-10): the ISIN-dedup gate collapses 118 raw notch-changes to 19 TRUE
  events (15↑/4↓, ~2/month)** — multi-ISIN debt re-ratings were 6× pseudo-replication; the
  charter's old "130 upgrade events" premise measured rows, not events. Sample horizon at current
  accrual ≈ years, not weeks — the monthly DM tracks it; the run completes itself the month it
  reconciles.
- **E-03 Disclosure-event drift** — conviction insider filings as *events* (the T+2 disclosure IS
  tradeable information; the footprint study proved the pre-public window doesn't exist — so test
  the post-public drift instead). Reuses the PEAD harness verbatim.
- **E-04 Campaign-arc study** — multi-filing accumulation sequences; detection target = arc
  continuation, not front-running. **ARMED S85b (2026-07-10): gate frozen + hashed
  (`947814278f7e…`, M-04) long before the run is possible; `campaign_arcs.py --run` REFUSES until
  the E-03 depth condition holds (≥8 qtr cohorts ≥5 arc events + ≥24mo feed); a monthly timer
  (`hermes-e04-gate`, 1st 03:05 UTC) DMs the measured depth. Baseline: 4/8 cohorts, 247 arc events
  (already 4× the 57-episode hint) — GO ≈ mid-2027 at current arc density, earlier if it rises.**
- **X-02 T2T/BE delivery-contamination mask** — in BE series delivery is definitionally 100%;
  every delivery signal (MEP/DVPT/DELIV features) is polluted on those rows + transition days.
  Site-wide correctness fix, ships with a data-quality note.
- **X-03 Organic delivery** (deliv − block/bulk qty, needs D-05) · **X-04 overnight/intraday
  split** columns + pump-flag · **X-05 band-lock streak board** (close==high==band).
- **D-06 announcement-category taxonomy** (auditor resignations, CFO exits, order wins — the
  `concall_bse.py` pattern) → **E-07 auditor-resignation red-flag study**.
- **P-01 smart-buyer graph v1** — repeat-acquirer scoring on bulk/block `client_name` (needs D-05).
- **M-02 placebo-date harness** — auto-rerun any event study on shuffled dates; publish the
  inflation number with every study.

## 5. LATER — the quarter

Index add/drop + F&O-inclusion prediction studies (E-08/E-09, needs shareholding free-float) ·
buyback tender quota calculator (E-10, personal-scale) · dividend-surprise drift (E-11) ·
rebrand-pump study on `security_renames` (E-12) · AMFI MF-portfolio feed (D-08) as ground-truth
#4 + "who owns what" surface · NSDL/CDSL FPI sector flows (D-09) · short-delivery auction feed
(D-10) · Deflated-Sharpe wrapper in the factory (M-03) · pre-registration registry with hashed
hypothesis files (M-04) · footprint/PEAD spec-sheet page on the Trust altitude (P-03) ·
evidence-pack PDF v2 with full event history (P-04) · Reg-31 shareholding-release combos after
the ~Jul-21 filing flood (E-14) · survivorship-bias quantifier published as a standing caveat
number (M-05) · PEAD within-season-so-far variant (pre-register first; ledger 2026-07-05) ·
MCP server on the VPS (P-06, open item L).

**CLOSED (evidence, not deferral):** PEAD within-season-so-far variant — ran pre-registered
2026-07-05b, net return/vol 0.06, FAILED the gate; no fundable PEAD construction remains. The event lens
ships descriptively (`pead_surface.py`), never as a book.

**E-14 ARMED S85f (2026-07-10):** gate frozen + hashed (`c005e2a2289d…`, M-04) — three ΔQoQ combos
only (promoter↑ / promoter↓ / promoter↑×FII↑ at the 0.25pp inertia floor; pledge REPORTED-only per
the 6.8/6.9% tail null); self-gating `shp_combos.py --run` fires monthly on the 25th (**first:
2026-07-25**, deliberately trailing the flood + the S85d calibration by a few nights); aborts-with-
census until dated releases ≥1,000 + per-combo n≥50 & 8 cohorts. Baseline DM: 94/1,000 dated (all
real, 0 calibrated) · G1 18 · G2 20 · G3 4 — **the one armed study whose GO can be its FIRST fire**,
since calibrated dating of the 28 historical quarters clears the floors at once.

**§5 status (S83g sweep, 2026-07-07/08):** P-03 ✓ (spec-sheets live, S83d) · M-05 ✓ (standing-caveats
box) · M-04 ✓ (`prereg.py` registry, gates hashed — E-11/E-12 pre-hashed before first run) ·
M-03 half (evlib re-export; factory print-wiring = next factory run) · E-11 + E-12 RUN
(pre-registered; results in the ledger § Studies) · E-14 waits ~Jul-21 Reg-31 flood · E-08/E-09
blocked on data depth (membership-change history; D-07) · ~~D-09~~ **endpoint FOUND 2026-07-24 (§6
D-09 row) — no longer blocked** · D-10 (+D-07) still need an endpoint-discovery pass (direct probes
404; NO dead pipes built) · D-08 = its own 1-2 sessions · **P-04 SHIPPED (S96, 2026-07-10): `/dash/evidence-pack` — the print-CSS procurement
assembly (P-03 sheets verbatim + coverage boundary + live season SLA + replay pointer; browser
print→PDF, zero deps; every number imported from the surface that owns it, never restated)** ·
P-06 deferred per the
product ranking (named-buyer trigger; personal-use variant needs an auth design) · **E-10 SHIPPED
(S93, 2026-07-10): `/dash/buyback-calc` — the personal-scale tender-quota calculator + the 344-row
BUYBACK tape; acceptance ratio stays a user assumption (no fabricated priors); a buyback drift
STUDY remains its own future pre-registration.**

## 6. Data-acquisition sprint — what can be brought in QUICKLY (all primary, ₹0)

| ID | Feed | Source | Effort | Unlocks |
|---|---|---|---|---|
| D-01 | Board-meeting / results calendar | BSE API (concalls.py contract) | 0.5 s | war room N1, E-13 anticipation reads |
| D-02 | ASM / GSM surveillance lists | NSE+BSE daily CSV | 0.5 s | state machine, forced-flow events, veto context |
| D-03 | Security-wise price bands | NSE daily CSV | 0.5 s | band-lock detection (X-05), queue anomaly |
| D-04 | SLB lending volumes | NSE daily report | 0.5–1 s | India's only short-interest proxy; squeeze + crowding flags |
| D-05 | ~~Bulk/block deal HISTORY~~ **RE-SCOPED (D92)** — the premise was wrong: no free archive exists (`deals.py:11`); the live feed (`e6ab37d`) accumulates forward | n/a | X-03/P-01 build on the accumulating window as it deepens |
| D-06 | Announcement categories | BSE (existing pattern) | 1 s | governance red-flag events (E-07), order-win tags |
| D-07 | MWPL / F&O eligibility inputs | NSE daily | 0.5 s | F&O-entry prediction (E-09) |
| D-08 | AMFI monthly MF portfolios | AMFI/AMC disclosures | 1–2 s | institutional ground truth; calibration labels wave-2 |
| D-09 | FPI fortnightly sector flows | **NSDL — endpoint FOUND (2026-07-24 data-360 review), blocker cleared:** `fpi.nsdl.co.in/web/Reports/FPI_Fortnightly_Selection.aspx` (selector) + static `…/StaticReports/Fortnightly_Sector_wise_FII_Investment_Data/FIIInvestmentSector_h.html`; SEBI mirror `sebi.gov.in/statistics/fpi-investment/fortnightly-sector-wise.html` | 0.5 s | sector-FPI conviction — REAL depository AUC/net by sector, distinct from the daily provisional cash FII/DII (`fiidiiTradeReact`) we already have; sector-rotation confirmation layer |
| D-10 | Short-delivery / auction qty | NSE settlement reports | 0.5–1 s | distress/squeeze microsignal |
| D-11 | SEBI debarred entities | SEBI lists | 0.5 s | governance veto feed |
| D-12 | RBI sectoral credit | RBI DBIE (`data.rbi.org.in`, Excel/CSV; repo · G-sec curve · USD-INR · forex · **sectoral bank-credit deployment**) | 1 s | macro DESCRIPTIVE regime overlay only (valuation × phase × breadth × macro); NOT stock-level alpha |
| D-13 | NSE index constituent **WEIGHTS** | NSE Indices factsheets (the constituent CSV carries NO weight — `stock_index_membership.weight_pct` is 100% NULL) | 1 s | rebalance passive-flow front-running; index add/drop impact sizing (E-08); weight-change events (impossible today) |

"s" = sessions. Wave-1 = D-01..D-05 (approved, D88). Wave-2 = D-06..D-08 after the war room ships.

**Amendment — 2026-07-24 (data-sourcing 360° review).** Full-estate audit (4 agents + the 2026-07-05
DATA-POSTMORTEM). Findings folded here + into `PROJECT_STATE.md § "Data 360° review"`:
- **New-feed priority (survivors, all still ₹0/primary):** **D-08 AMFI monthly MF portfolios** = the one
  ORTHOGONAL non-price alpha axis left (postmortem concl. #5) → highest value, own 1-2 sessions ·
  **D-09 unblocked** (endpoint above) · **D-06 announcement taxonomy** is cheap (reuses the live
  `concall_bse.py` BSE-announcement fetch) · **D-13** new (index weights) · D-07/D-10/D-11/D-12 stand.
- **KILLED — do NOT re-propose (evidence):** GST + e-way + power + UPI (only national aggregate exists →
  ~0 single-stock alpha, `DATASET-RESEARCH-BRIEF.md §5` / D76) · bulk-block HISTORY (no free archive,
  bot-walled, `deals.py:11` / D-05 re-scope) · India VIX is ALREADY live (`index_signals`).
- **Already-download-but-DISCARD (fix at the parser, not a new feed):** (1) **niftyindices constituent
  `Industry` + `ISIN` are dropped** — only `Symbol` kept (`membership.py`); this is an authoritative NSE
  sector map we throw away while depending on Screener's industry text — **cheapest primary-source win,
  retires a VENDOR-TOS leg** · (2) full **F&O option chain** discarded (only near-month PCR/max-pain
  stored; IV surface derivable from `SttlmPric` lost) · (3) minor: `EQUITY_L` face value · `corp_actions`
  face value · UDiFF `UndrlygPric` · bulk-deal `Remarks`.
Nothing here touches a vendor; everything follows an existing ingest pattern in `src/automation/`.

## 7. Idea bank (50) — every entry enters through §2.1's gate

**Event studies (harness exists):** E-01 war room (NOW) · E-02 rating drift · E-03 disclosure
drift · E-04 campaign arcs · E-05 pledge-release velocity · E-06 T2T→EQ release · E-07 auditor
resignation · E-08 index add/drop · E-09 F&O inclusion · E-10 buyback tender quota · E-11
dividend surprise · E-12 rebrand pump · E-13 board-meeting anticipation · E-14 shareholding-release
combos · E-15 QIP/rights/preferential pricing anchors · E-16 merger record-dates · E-17
relisting behavior.
**Descriptive lenses (compute-on-read):** X-01 trade-size ratio (**SHIPPED S83c**) · X-02 T2T mask
(**CLOSED BY EVIDENCE, D92** — every delivery engine was already EQ-only; exclusion not pollution;
`chk_t2t_universe` publishes the mass; residual X-02b = the price-only stragglers, post-season) ·
X-03 organic delivery (forward window only, per the D-05 re-scope) · X-04 overnight/intraday split ·
**X-05 SHIPPED (S96c, 2026-07-10): `/dash/band-locks` — lock streaks on reconstructed per-date
bands, window fenced to the feed's birth Jul-07; 18th measured strategy (card+pillar+glossary+
board gate); descriptive, no study)** · X-06 Amihud illiquidity +
liquidity-migration (**half-built**: `amihud_22d` computes nightly, `mep_signals.py:286`; only the
migration delta is new) · X-07 volume-at-price shelves · X-08 institutional-footprint week composite
(inherits the D89 front-detection FAIL — admissible only reframed post-public) · X-09 base-length ×
breakout velocity · X-10 expiry/holiday conditioning.
**Data feeds:** D-01…D-12 (§6).
**Product:** P-01 smart-buyer graph · P-02 results-day auto-refresh SLA · P-03 detection
spec-sheet page (incl. failures) · P-04 evidence-pack v2 · **P-05 SHIPPED (S102, 2026-07-10):
`/dash/replay-any-date` — any symbol, any date, through the entitled /v1 API itself (auth +
metering + provenance stamps), knowable clock stamped per D104 (EVENT/MODELED), reproduction
curl on every panel; demo key provisioned in .env; delivered ~3 weeks ahead of the early-Aug
target** · P-06 MCP server.
**Method/infra:** M-01 event-study library · M-02 placebo harness · M-03 Deflated-Sharpe stage ·
M-04 pre-registration registry · M-05 survivorship quantifier.

Idea count is not the KPI — the ledger is. Ideas are admitted cheaply and killed honestly.

## 8. What we will NOT do

No vendor/Screener extension (frozen; XBRL replaces it) · no LLM inside scheduled jobs beyond the
approved cheap paths · no ranked credibility (Gate B) · no return promises anywhere a client can
see · no re-attempt of any ❌ failure-table entry without a pre-registered new design that cites
the recorded numbers · no new always-on storage for derivable series (space doctrine) · no orphan
pages, no per-page nav forks (D80) · no third glossary/popover system (AUD-71).

## 9. KPIs (reviewed at each results season)

Filing→surface MTTR during results season (target: same evening) · feed freshness SLAs green on
the Trust page · spec-sheets published: 3 by end-Aug (PEAD cells, footprint incl. FAIL, Wolfe/
harmonic refresh) · pre-registered studies run: ≥4/quarter, 100% of results in the ledger ·
XBRL gate pass-rate trend · API spend ≤₹300/mo · zero guardrail-#8 violations.

## 10. Governance

Decisions land in PROJECT_STATE § Decision log the same commit as the change (CLAUDE.md rule).
This charter is amended by D-log entry, not by silent edit. The carry-forward queue derives from
§3 NOW. When evidence contradicts the charter, evidence wins and the charter is amended — the
same rule the ledger already enforces on strategies.
