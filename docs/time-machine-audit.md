# Time-machine capability audit — every routed lens vs "?asof="

> **Lifecycle: TRANSIENT.** LANE-F (S154) read-only audit deliverable for the D134 program
> (plan §4-F: Importance 8 · Criticality 5 · Timing mid · Cost ₹0). Retire condition: folded
> into docs/patearn-analytics-company-plan.md §4-F status.
>
> NOTE (deliberate): DOC_INDEX.md registration and the git commit of this file are left to the
> orchestrator (LANE-R) — this lane is read-only apart from creating this file.

**Question audited:** which of the 67 routed lenses in `src/web/lens_registry.py` can already
answer *"what did this look like as of date X?"* — and what are the cheapest upgrades.

**Method:** registry read + targeted greps only (no full-module reads): `asof`/`as_of` query
params, snapshot-table writers (`DELETE FROM …` wipe vs dated retention), PIT-parameterized
reads (`trade_date<=?`), and each view's `FROM` tables. Writers checked in `src/automation/*`
and `research/explosive_moves/*`.

**Classification rule**
- **yes** — the page accepts a date today (`?asof=` / `?as_of=` / `?drill=`) and renders that day.
- **partial** — underlying table(s) are dated with history retained; the view pins to latest.
  A date filter is a small change.
- **no** — snapshot table wiped on rewrite (no history), a live/current-state read, or a
  static/interactive surface where asof is not meaningful (marked "n/a" in the note).

**Counts: yes = 5 · partial = 34 · no = 28** (of 67 routed lenses; the 2 overlay-only lenses
`wolfe`/`harmonic` are excluded — they draw on whatever price window the chart shows).

The plan §4-F status line says "partial (portfolios, attention)" — the audit found FIVE live
yes-lenses: **attention, market-internals, wolfe-scan, model-portfolios, replay-any-date.**

---

## 1 · Full lens table

Mechanism/blocker kept to ≤10 words. Modules: `src/web/<file>`.

### Markets (31)

| lens key | asof today | mechanism / blocker |
|---|---|---|
| markets | partial | cockpit reads latest of dated index/stock_signals |
| attention | **yes** | `?as_of=` batch replay; signal_events keyed by as_of |
| market-internals | **yes** | `?drill=DATE` + full 22y series; PK d |
| move-anatomy | partial | features study table dated; re-aggregate ≤ X |
| seasonal-tape | no | single certification snapshot; no batch history |
| seasonal-screen | no | same seasonal_cells/stack single snapshot |
| seasonal-divergence | no | same seasonal_cells/stack single snapshot |
| actions | partial | corporate_actions has fetched_at; knowable-at filter possible |
| event-cadence | no | seasonal_events keeps MAX(asof) only (older DELETEd) |
| buyback-calc | no | interactive calculator; asof n/a |
| band-locks | no | price_bands_current wiped; reconstruct from price_band_events |
| surveillance | partial | surveillance_flags snapshots dated; diff window ≤ X |
| sectors | partial | cockpit reads latest of dated index/stock_signals |
| sector-economics | partial | fundamentals_history by year; cut years > X |
| rs-hub | partial | stock/index_signals dated; view pins latest |
| leaders | partial | stock_signals dated; view pins latest |
| momentum-scan | partial | momentum_scan retains every as_of; view MAX(as_of) |
| capture-map | no | capture_signals PK(num,den) overwritten; no history |
| results-reactions | no | nightly full-wipe rebuild (research.db) |
| rrg | partial | live-computed from full ratio_rows/index_rows history |
| rotation | partial | index/stock_signals dated; view pins latest |
| rsband | partial | rs_band lanes on dated stock_signals |
| cycle-clock | no | rs_extras PK(num,den) overwritten; recompute from ratio_rows |
| divergence | no | rs_extras PK(num,den) overwritten; flags latest-only |
| early-signals | partial | phase turns from dated stock_signals; latest pair |
| sector-momentum | partial | stock_signals dated; view pins latest |
| harmonic-scan | no | harmonic_signals wiped per universe; engine could replay |
| wolfe-scan | **yes** | `?asof=` live winner_scan recompute; snapshot else |
| participants | partial | participant_oi daily history; view pins latest |
| wire | partial | sent_news dated ledger; add end-bound |
| compare | partial | series endpoints already range-parameterized (trade_date<=?) |

### Screener (5)

| lens key | asof today | mechanism / blocker |
|---|---|---|
| screen2 | partial | latest-date cut of dated stock_signals + joins |
| screener | partial | latest-date cut of dated stock_signals |
| themes | partial | company_tags carry as_of; membership mostly reconstructable |
| tags-review | no | tag-proposal workflow state; asof n/a |
| workbench | no | saved user screens/notes; asof n/a |

### Strategies (17)

| lens key | asof today | mechanism / blocker |
|---|---|---|
| strategist | no | composite; wolfe/launchpad/classic roster inputs latest-only |
| factor-league | no | roster DELETEd per family; churn kept 90d only |
| model-portfolios | **yes** | `?asof=` picks snapshot ≤ date; dated snapshots |
| classics | no | classic_roster DELETEd per strategy each run |
| conviction | partial | synthesis over dated stock/mep/cpr signals |
| stocks | partial | stock_signals dated; view pins latest |
| stealth | partial | same render path as stocks |
| mep | partial | mep_signals keyed symbol+trade_date; full history |
| cpr | partial | cpr_signals keyed by period_end_date; history retained |
| concalls | partial | concall_scores per as_of_period; quarterly history |
| growth | partial | concall_signals dated ledger; `?since=` exists already |
| insider | partial | insider_events broadcast-dated; end-bound the window |
| ratings | partial | rating events broadcast-date anchored; window ≤ X |
| sast | partial | SAST events dated; end-bound the window |
| shp | partial | shareholding_history quarterly PIT archive |
| launchpad | no | launchpad_signals full-wipe; ignition_outcomes HAS the history |
| launchpad-track | partial | ignition_outcomes keyed signal_date; re-aggregate ≤ X |

### Tracker (5)

| lens key | asof today | mechanism / blocker |
|---|---|---|
| dashboard | no | current user holdings state; asof n/a |
| portfolios | no | current user portfolios; asof n/a |
| watchlists | no | current user watchlists; asof n/a |
| performance | partial | trades dated + `_capture_snapshot(as_of=)` exists; curve cut |
| import | no | action page; asof n/a |

### Trust (9)

| lens key | asof today | mechanism / blocker |
|---|---|---|
| coverage | no | live feed-staleness board; past states not stored |
| testing | partial | strategy_runs appended; holdings snapshot latest-only |
| glossary | no | static reference; asof n/a |
| strategy-ref | no | static methodology docs; asof n/a |
| reading-guide | no | static guide; asof n/a |
| pat | no | interactive copilot over current tables; asof n/a |
| spec-sheets | no | pre-registered specs; timeless documents |
| evidence-pack | no | assembly of current state; asof n/a |
| replay-any-date | **yes** | `?as_of=` via /v1 API; one symbol, knowable-stamped |

---

## 2 · Proposed `asof_capable` flag map (paste-ready)

For the lens-registry metadata (plan §4-F: every lens declares `asof_capable`). Values are
today's honest state; "no" entries whose blocker is structural (not n/a) are the upgrade pool.

```python
ASOF_CAPABLE: dict[str, str] = {
    # ── Markets ──────────────────────────────────────────────
    "markets": "partial",
    "attention": "yes",
    "market-internals": "yes",
    "move-anatomy": "partial",
    "seasonal-tape": "no",           # single certification snapshot
    "seasonal-screen": "no",         # single certification snapshot
    "seasonal-divergence": "no",     # single certification snapshot
    "actions": "partial",
    "event-cadence": "no",           # seasonal_events single-asof by design
    "buyback-calc": "no",            # n/a — interactive tool
    "band-locks": "no",              # band state table current-only
    "surveillance": "partial",
    "sectors": "partial",
    "sector-economics": "partial",
    "rs-hub": "partial",
    "leaders": "partial",
    "momentum-scan": "partial",
    "capture-map": "no",             # snapshot overwritten, no history
    "results-reactions": "no",       # nightly full-wipe rebuild
    "rrg": "partial",
    "rotation": "partial",
    "rsband": "partial",
    "cycle-clock": "no",             # rs_extras latest-only
    "divergence": "no",              # rs_extras latest-only
    "early-signals": "partial",
    "sector-momentum": "partial",
    "harmonic-scan": "no",           # snapshot-only; engine replay feasible
    "wolfe-scan": "yes",
    "participants": "partial",
    "wire": "partial",
    "compare": "partial",
    # ── Screener ─────────────────────────────────────────────
    "screen2": "partial",
    "screener": "partial",
    "themes": "partial",
    "tags-review": "no",             # n/a — workflow state
    "workbench": "no",               # n/a — user state
    # ── Strategies ───────────────────────────────────────────
    "strategist": "no",              # composite over latest-only rosters
    "factor-league": "no",           # roster wiped per run
    "model-portfolios": "yes",
    "classics": "no",                # roster wiped per run
    "conviction": "partial",
    "stocks": "partial",
    "stealth": "partial",
    "mep": "partial",
    "cpr": "partial",
    "concalls": "partial",
    "growth": "partial",
    "insider": "partial",
    "ratings": "partial",
    "sast": "partial",
    "shp": "partial",
    "launchpad": "no",               # snapshot wiped; ignition_outcomes has history
    "launchpad-track": "partial",
    # ── Tracker ──────────────────────────────────────────────
    "dashboard": "no",               # n/a — user state
    "portfolios": "no",              # n/a — user state
    "watchlists": "no",              # n/a — user state
    "performance": "partial",
    "import": "no",                  # n/a — action page
    # ── Trust ────────────────────────────────────────────────
    "coverage": "no",                # live status board
    "testing": "partial",
    "glossary": "no",                # n/a — static
    "strategy-ref": "no",            # n/a — static
    "reading-guide": "no",           # n/a — static
    "pat": "no",                     # n/a — interactive
    "spec-sheets": "no",             # n/a — static
    "evidence-pack": "no",           # n/a — assembly
    "replay-any-date": "yes",
}
```

Sanity: 67 keys — 5 yes · 34 partial · 28 no (14 of the no's are "n/a by nature":
tools/static/user-state; the other 14 are genuine blockers = the upgrade pool).

---

## 3 · The 5 cheapest high-value upgrades (ranked)

Ranked by user value per unit of work; all ₹0 (existing box, rule-based code).

1. **momentum-scan `?asof=`** — the table already retains every `as_of` batch
   (`research/explosive_moves/momentum_scan.py` deletes only the same-day batch).
   *Approach:* accept `?asof=`, bind `WHERE m.as_of = (SELECT MAX(as_of) WHERE as_of<=?)`
   in `momentum_view.py` + a date input; bind the C/A/B veto join to the same date.

2. **Shared `asof → trade_date` resolver for the stock_signals family** (leaders, stocks,
   stealth, mep, cpr, sectors, rotation, rsband, sector-momentum, rs-hub ≈ 10 lenses).
   *Approach:* one helper resolving `?asof=` to the last trade_date ≤ X (the exact query
   `dashboard._capture_snapshot` already uses at line ~3229), threaded where views now call
   `_latest_dates()`; roll out lens-by-lens starting with leaders + stocks.

3. **launchpad `?asof=` served from `ignition_outcomes`** — the nightly `launchpad_signals`
   is wiped, but every historical signal since 2019 lives in `ignition_outcomes(symbol,
   signal_date, …)` and the track page already reads it.
   *Approach:* when `?asof=` present, list signals with `signal_date` in the fresh-window
   ending at X — "the screen as it would have fired then", ledger caveat kept.

4. **Event-ledger end-bound: insider · ratings · sast · shp · participants · wire · actions**
   (7 lenses) — all read dated (mostly broadcast-anchored) event tables through a
   trailing `days=N` window.
   *Approach:* per lens, one WHERE change — window becomes `[X−N, X]` (actions additionally
   `fetched_at ≤ X AND ex_date ≥ X`) + the shared date input.

5. **Wolfe's snapshot-or-live contract copied to harmonic-scan** — `wolfe_view.wolfe_scan`
   is the house pattern: nightly snapshot for the instant page, `?asof=` triggers a live
   engine recompute at that date.
   *Approach:* add an `asof` parameter to the harmonic scan engine and mirror the
   `wolfe.winner_scan(asof=…)` branch in `harmonic_view.py`.

Deliberately NOT in the top 5: rs_extras consumers (cycle-clock/divergence/capture-map) need
their engines re-run per date (moderate compute, latest-only PK tables — a schema decision
first: add trade_date to the PK vs recompute-on-read); factor-league/classics need retention
changes to their writers (keep dated rosters instead of wiping) — cheap too, but the value is
lower than the five above and it grows the DB (space doctrine says decide deliberately).

---

## 4 · Honesty section — replay claims vs reality

Pages whose TEXT implies historical replay beyond what they deliver:

1. **Home flagship tile (`src/web/cockpit.py` ~line 975–976):** "Replay any date — **Rewind
   the whole platform to any past day** — zero look-ahead, on the live API." The linked page
   (`/dash/replay-any-date`) replays ONE symbol across exactly three /v1 surfaces
   (credibility · attention · universe count). Today 5 of 67 lenses accept a date — "the
   whole platform" overstates it. Fix = soften the tile line (e.g. "replay any stock's
   knowable record on any date") or land upgrades #1–#5 first. The page itself is honest
   (docstring: "the page INVENTS NOTHING").
2. **No other overclaims found.** Checked in particular: `evidence_pack.py` ("replays ANY
   symbol and ANY date through the entitled /v1 API" — true, scoped to the API);
   attention's "PIT-replayable tape" (true — `?as_of=` works, including pre-bus backfilled
   batches, stated honestly on-page); market-internals' home tile "click any day to drill
   in" (true — `?drill=` exists); launchpad-track's "point-in-time study" (a claim about
   study methodology, not a page replay feature — accurate); the many "as of <date>"
   staleness labels on latest-only boards are honest labels, not replay claims.

Adjacent nuance (not an overclaim): `lens_registry.py`'s model-portfolios comment says
"reconstructed since 2019-01-01" while the strategy-ledger record says the books run from
2012-06 — a comment-vs-doc drift for the orchestrator to reconcile, not a user-facing claim.

---

*Audit basis: `src/web/lens_registry.py` (67 routed lenses), route handlers across
`src/web/*.py`, writer retention in `src/automation/*.py` + `research/explosive_moves/*.py`.
Read-only audit; no code touched.*
