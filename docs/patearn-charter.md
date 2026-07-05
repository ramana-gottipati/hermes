# Patearn Charter — operating doctrine (CEO mode)

**v1.0 — 2026-07-05.** Canonical roadmap (PROJECT_STATE D87). Sessions execute § NOW by default;
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
| N1 | **Results-season war room — LIVE (S80d, ahead of Jul-09).** `/dash/results-reactions` now shows BOTH halves: forward **"Upcoming results — next 14 days"** (NSE board-meeting calendar, D-01) + the "just reported" delivery-confirmed reaction table. Remaining: nightly refresh of the calendar feed (systemd, deferred — populated manually for now) | forward+back LIVE; nightly-refresh pending |
| N2 | **Data sprint wave-1** (D88): ASM/GSM lists (D-02) · price-band file (D-03) · SLB volumes (D-04) · bulk/block **history backfill** (D-05) | each ~0.5 session, all ₹0 primary CSVs |
| N3 | **Trade-size ratio** descriptive column (the D89 survivor: Cliff's δ +0.33/+0.25) on Screen+ + dossier, compute-on-read | descriptive-only, glossary entry required |
| N1b | **Results-Reaction SCANNER — LIVE `/dash/results-reactions` (S80c):** the descriptive board from the (falsified-as-a-book) PEAD study — who just reported, was the surprise delivery-confirmed, realized +22/+60d drift, population base-rate as labelled context. Nightly `results_reactions` snapshot (research venv) → pure-stdlib view (house pattern, like momentum-scan). Mounted surgically on the forked live `v2_surfaces.py` (import-tested, curl-verified 200). Remaining: nightly-chain wiring for the snapshot + nav-lens entry (nested URL) when the nav fork reconciles | scanner LIVE; nightly+nav pending |
| N4 | **Event-study library**: extract `pead.py`/`footprint.py` shared parts (CAR paths, controls, cohort stats, cost model) into `research/explosive_moves/evlib.py` | refactor, selftest parity |
| N5 | Verify Jul-05 concall run + first sandboxed nightly chain (carry-forward queue #1) | ops hygiene |

## 4. NEXT — July/August

- **E-02 Credit-rating drift study** — 130 upgrade events already ingested; widen the 59-symbol
  scrip mapping first. Pre-register before running.
- **E-03 Disclosure-event drift** — conviction insider filings as *events* (the T+2 disclosure IS
  tradeable information; the footprint study proved the pre-public window doesn't exist — so test
  the post-public drift instead). Reuses the PEAD harness verbatim.
- **E-04 Campaign-arc study** — multi-filing accumulation sequences (the 57 merged insider+SAST
  episodes hint these are the real fish); detection target = arc continuation, not front-running.
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
2026-07-05b, net Sharpe 0.06, FAILED the gate; no fundable PEAD construction remains. The event lens
ships descriptively (`pead_surface.py`), never as a book.

## 6. Data-acquisition sprint — what can be brought in QUICKLY (all primary, ₹0)

| ID | Feed | Source | Effort | Unlocks |
|---|---|---|---|---|
| D-01 | Board-meeting / results calendar | BSE API (concalls.py contract) | 0.5 s | war room N1, E-13 anticipation reads |
| D-02 | ASM / GSM surveillance lists | NSE+BSE daily CSV | 0.5 s | state machine, forced-flow events, veto context |
| D-03 | Security-wise price bands | NSE daily CSV | 0.5 s | band-lock detection (X-05), queue anomaly |
| D-04 | SLB lending volumes | NSE daily report | 0.5–1 s | India's only short-interest proxy; squeeze + crowding flags |
| D-05 | Bulk/block deal HISTORY | NSE archive CSVs | 0.5 s | organic delivery (X-03), smart-buyer graph (P-01); table exists, 2 weeks deep today |
| D-06 | Announcement categories | BSE (existing pattern) | 1 s | governance red-flag events (E-07), order-win tags |
| D-07 | MWPL / F&O eligibility inputs | NSE daily | 0.5 s | F&O-entry prediction (E-09) |
| D-08 | AMFI monthly MF portfolios | AMFI/AMC disclosures | 1–2 s | institutional ground truth; calibration labels wave-2 |
| D-09 | FPI fortnightly sector flows | NSDL/CDSL | 0.5 s | sector-rotation confirmation layer |
| D-10 | Short-delivery / auction qty | NSE settlement reports | 0.5–1 s | distress/squeeze microsignal |
| D-11 | SEBI debarred entities | SEBI lists | 0.5 s | governance veto feed |
| D-12 | RBI sectoral credit | RBI DBIE | 1 s | macro context for rotation boards |

"s" = sessions. Wave-1 = D-01..D-05 (approved, D88). Wave-2 = D-06..D-08 after the war room ships.
Nothing here touches a vendor; everything follows an existing ingest pattern in `src/automation/`.

## 7. Idea bank (50) — every entry enters through §2.1's gate

**Event studies (harness exists):** E-01 war room (NOW) · E-02 rating drift · E-03 disclosure
drift · E-04 campaign arcs · E-05 pledge-release velocity · E-06 T2T→EQ release · E-07 auditor
resignation · E-08 index add/drop · E-09 F&O inclusion · E-10 buyback tender quota · E-11
dividend surprise · E-12 rebrand pump · E-13 board-meeting anticipation · E-14 shareholding-release
combos · E-15 QIP/rights/preferential pricing anchors · E-16 merger record-dates · E-17
relisting behavior.
**Descriptive lenses (compute-on-read):** X-01 trade-size ratio (approved) · X-02 T2T mask
(correctness) · X-03 organic delivery · X-04 overnight/intraday split · X-05 band-lock streaks ·
X-06 Amihud illiquidity + liquidity-migration · X-07 volume-at-price shelves · X-08
institutional-footprint week composite · X-09 base-length × breakout velocity · X-10
expiry/holiday conditioning.
**Data feeds:** D-01…D-12 (§6).
**Product:** P-01 smart-buyer graph · P-02 results-day auto-refresh SLA · P-03 detection
spec-sheet page (incl. failures) · P-04 evidence-pack v2 · P-05 replay-any-date demo API ·
P-06 MCP server.
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
