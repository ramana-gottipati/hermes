"""sideways_parity — the migration-parity ledger: guarantee nothing in the classic estate
is silently missed as the modern app ("Sideways") is rebuilt from scratch.

The problem
-----------
Sideways is a from-scratch rebuild (redesign M0-M8; identity mid-reselection). A from-scratch
rebuild is exactly where a 73-surface / 257-metric / 17-strategy estate loses things — not
maliciously, just silently. "Be careful" does not scale. This module is the machine-enforced
answer, same DNA as the gates that already keep the classic site honest (`test_dash_route_registry`
= no orphan routes, `test_pat_coverage` = every lens known to Pat): a DERIVED inventory of the
whole product estate, a DISPOSITION for every element, and a gate (`tests/test_sideways_parity.py`)
that fails the build on any integrity violation.

The inventory is DERIVED, never hand-typed
------------------------------------------
Everything we shipped already lives in single-sources-of-truth, so a new lens/metric/strategy
appears here the day it ships (it can never drift):
  * SURFACES   — `lens_registry.LENSES` (routed) — the screens a user would notice missing.
  * METRICS    — `docs/metrics-glossary.md` bullets — must stay explainable in Sideways.
  * STRATEGIES — `docs/strategies/*.md` — must stay represented (with their honesty verdict).

Every element carries a DISPOSITION
------------------------------------
    PORTED   — built in Sideways AND verified at a real route (the `target` is that /dash route).
    DEFERRED — planned; `target` is the Sideways milestone (M6/M7/M8) or UNSCOPED (no milestone
               covers it yet — the visible planning gap, e.g. the Markets analytical estate).
    DROPPED  — deliberately not carried, WITH a rationale (the ONLY way something legitimately
               doesn't make it).
    NA       — structurally doesn't apply to the new app, WITH a rationale.

A surface with no explicit disposition falls to a deterministic per-workspace DEFERRED default,
so it is always ACCOUNTED (it shows on the board's backlog) — never invisible. Explicit entries
capture the real decisions (what is ported / dropped / re-scoped). The gate enforces integrity
(no stale keys · PORTED has a route · DROPPED/NA have a reason) and completeness (a milestone
marked DONE cannot still have un-ported surfaces assigned to it).

This is v1: surface/metric/strategy parity + the visible backlog. Honesty-status carry (each
item's descriptive-only / fundable / falsified verdict travels with it) is a v2 tightening.

Internal governance board: /dash/sideways-parity (INTERNAL_DEV route — deliberately unlinked,
an owner/ops dashboard, not a customer lens). Read-only, descriptive.
"""
from __future__ import annotations

import glob
import os
import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.web import lens_registry as LR
from src.web.dashboard import _shell, _esc

router = APIRouter()

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── the Sideways milestones (redesign M0-M8; docs/redesign-coordination.md §5) ───────
# status: DONE (deployed) · PLANNED (spec/approved, not built) · OPEN (no milestone).
MILESTONES: dict[str, tuple[str, str]] = {
    "M3":       ("News / flow dock", "DONE"),
    "M4":       ("Stock hub (dossier)", "DONE"),
    "M5":       ("Today / orientation home", "DONE"),
    "M6":       ("Journey / guided + help layer", "PLANNED"),
    "M7":       ("Clusters & portfolios (Strategies + Tracker)", "PLANNED"),
    "M8":       ("Screener", "PLANNED"),
    # Added 2026-07-24 (owner) to close the gap the parity ledger surfaced: the M6-M8 plan
    # scoped journey/clusters/screener but not the Markets analytical estate. M-Markets carries it.
    "M-Markets": ("Markets analytical estate (internals · anatomy · self-history · rotation · RS · "
                  "seasonal · events · patterns · participants · compare · …)", "PLANNED"),
    "UNSCOPED": ("Not yet assigned to any Sideways milestone", "OPEN"),
}

# per-workspace DEFAULT milestone for a surface with no explicit disposition. The Markets
# analytical estate maps to M-Markets — the milestone the owner added 2026-07-24 to close the
# gap the ledger surfaced (M6-M8 had scoped journey/clusters/screener but not the Markets estate).
_WS_MILESTONE: dict[str, str] = {
    "markets": "M-Markets", "screener": "M8", "strategies": "M7", "tracker": "M7", "trust": "M6",
}

# ── EXPLICIT dispositions — the human decisions. (status, target, note) ───────────────
#   PORTED  : target = the live Sideways /dash route; note = what it maps to.
#   DEFERRED: target = a MILESTONES key; note optional.
#   DROPPED : target = ""; note = REQUIRED rationale.
#   NA      : target = ""; note = REQUIRED rationale.
# Everything not listed here takes the per-workspace DEFERRED default above.
SURFACE_PARITY: dict[str, tuple[str, str, str]] = {
    "markets": ("PORTED", "/dash/preview",
                "M5 Today IS the migrated markets overview / orientation home"),
    "wire":    ("PORTED", "/dash/preview",
                "M3 news/flow dock (?ch=news) is the migrated News/Wire"),

    # ── M-Markets · lane W2-A (2026-07-27): eleven classic Markets lenses consolidated into FOUR
    # Graphite pages. Consolidation, not transliteration — each page answers ONE question with its
    # evidence stacked under it. Every note below states what travelled AND what deliberately did
    # not, so a "PORTED" here can never over-claim (the classic lens stays live either way).
    "market-internals": ("PORTED", "/dash/home/internals",
                         "Graphite Market internals: the five vital signs with Pro percentile "
                         "references vs the full 2004-> history, the price-breadth-vs-tape hero, the "
                         "delivery/dispersion/coil regimes, the crisis-fingerprint anchors and a "
                         "session drill. NOT carried: the 1200-cell daily heat ribbon (the drill is "
                         "reached from a 20-session strip instead) — classic keeps it"),
    "divergence": ("PORTED", "/dash/home/internals",
                   "the RSI-of-RS divergence watch (bullish/bearish columns + the momentum-extremes "
                   "strip) is the Divergence-watch zone of the Graphite internals page; the home's "
                   "own breadth-vs-delivery two-gauge stays the Today-level seed"),
    "participants": ("PORTED", "/dash/home/flows",
                     "Graphite Flows & positioning: the FII index-futures stance with its own-history "
                     "percentile, the FII-vs-retail mirror, the four-participant matrix (index fut "
                     "net · long:short · stock fut net · index option lean) and the recent-session "
                     "history (Pro). Sits beside the home's existing FII/DII cash reads rather than "
                     "duplicating them"),
    "fno": ("PORTED", "/dash/home/flows",
            "the own-history F&O board (OI · PCR · max-pain percentiles + build-up streak) with the "
            "auto reality-check callouts and a server CSV; the Phase-0 fence travels ON the block "
            "(PCR selects weakly, forward-test-only; max-pain/basis/OI-change failed). The "
            "PER-SYMBOL F&O read (OI · change · quadrant · PCR · basis · max-pain · put/call walls "
            "from fno_oi_signals) is the F&O section of /dash/home/stock (W1)"),
    "actions": ("PORTED", "/dash/home/events",
                "the forward corporate-actions calendar grouped by ex-date with type counts, the "
                "recent-past + security-events context (Pro) and a server CSV; reuses the home's "
                "reads.upcoming_ca (same corp_actions.upcoming single source). E-11/E-12 logistics "
                "fence carried"),
    "results-reactions": ("PORTED", "/dash/home/events",
                          "the results-reaction board (surprise · delivery multiple · realized 22/60-"
                          "day abnormal move) + who-reports-next, with the falsification fence stated "
                          "ABOVE the table (tradeable book net ret/vol 0.10 vs bench 0.85). NOT "
                          "carried: the CAR fan SVG and the published-brief cards — classic keeps them"),
    "event-cadence": ("PORTED", "/dash/home/events",
                      "overdue-vs-own-rhythm + expected-by-cadence tables with the event-type filter "
                      "and the dormant count, off the same bounded seasonal_events snapshot; TIME-only "
                      "fence carried verbatim. Index-membership filter not carried (event-type only)"),
    "buyback-calc": ("PORTED", "/dash/home/events",
                     "the tender-quota calculator (accepted · tender P&L · residual · net · breakeven "
                     "exit) with the live ₹2L small-shareholder eligibility read-out, anchored by the "
                     "buyback rows on the corporate-actions feed; the acceptance-ratio-is-YOUR-"
                     "assumption fence carried"),
    "surveillance": ("PORTED", "/dash/home/events",
                     "the ASM/GSM/price-band transition tape + current-state counts, single-sourced "
                     "through surveillance.transitions/current_state so page == card == pillar; "
                     "'context, never a gate' fence carried"),
    "band-locks": ("PORTED", "/dash/home/events",
                   "the close-at-band streak board single-sourced through band_lock.active_streaks, "
                   "with the honest-window note (bands reconstructable only back to the feed's first "
                   "captured day) and the no-study-exists fence"),
    "attention": ("PORTED", "/dash/home/attention",
                  "the full magnitude-ranked queue with lens filters, per-batch counts, ?as_of= "
                  "last-batch-on-or-before replay and the curated alert rail; the depth behind the "
                  "home's 'What changed today' band (which keeps owning severity_counts/what_changed). "
                  "NOT carried: the acknowledge WRITE and the cookie 'since you last looked' brief — "
                  "owner actions that stay on the classic page"),
    # ── Graphite cutover wave W2-B (2026-07-27): the RS · rotation · sectors families ──
    # Eleven classic Markets lenses consolidated into THREE Graphite pages. The rule applied:
    # PORTED = the question the lens exists to answer is fully served at the new route.
    # DEFERRED = the headline block landed but a materially separate block is still owed — the
    # note names exactly what travelled and what did not, so nothing is silently missed.
    "rrg":       ("PORTED", "/dash/home/rotation",
                  "sector rotation map — the 6/12/24-month RRG journeys reuse the canonical JdK "
                  "engine (automation/rrg._rs_ratio_momentum + quadrant). Per-symbol drills "
                  "(?idx= constituents, ?sym= single stock) belong to the Graphite stock hub, not "
                  "this page"),
    "rotation":  ("PORTED", "/dash/home/rotation?view=weather",
                  "RS weather — sector phase table (phases classified by the canonical "
                  "rs_phase engine, not the additive column), the 2x2 lifecycle grid with the "
                  "strict-diagonal shortlists, and the just-turned strip"),
    "cycle-clock": ("PORTED", "/dash/home/rotation?view=clock",
                    "the lifecycle dial — every sector's RS-Ratio x RS-Momentum on one radial "
                    "plot plus the same dial as a table, from the same rs_extras snapshot"),
    "rs-hub":    ("PORTED", "/dash/home/strength",
                  "the RS hub — universe-wide standing counts, the four-reading card set, and "
                  "today's strongest names with their phase and trend state. The PER-SYMBOL half "
                  "(rank · trend state · phase · 1/3/6/12-month slopes · vs its own sector) is the "
                  "Strength section of /dash/home/stock (W1), so the pair is complete: board here, "
                  "dossier there"),
    "leaders":   ("PORTED", "/dash/home/strength?view=leaders",
                  "strong-in-strong / weak-in-weak, straight from the canonical "
                  "stock_rs.leaders_laggards screen with all three trend states shown in Pro"),
    "capture-map": ("PORTED", "/dash/home/strength?view=capture",
                    "up-capture / down-capture / spread per sector at 3, 6 and 12 months, from "
                    "the canonical automation/capture engine, with the four-way behaviour read"),
    "sectors":   ("PORTED", "/dash/home/sectors",
                  "the sector standing board — weather, 1/3/12-month RS, member breadth (the "
                  "cross-check the classic board lacked) and the Pro return columns"),
    "sector-momentum": ("PORTED", "/dash/home/sectors?sec=",
                        "the constituent drill-down, promoted from a deep-link-only orphan to a "
                        "URL-addressable view of the sector board it belongs to"),

    "rsband":    ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/rotation?view=band: the per-sector RS-band position 0-100 "
                  "with band label, regime honesty gate and (Pro) the trend-removed position, from "
                  "the canonical automation/rsband engine; the engine's verdict KEY is never "
                  "rendered, only its descriptive state label. STILL OWED: the per-index channel "
                  "chart (support/median/resistance rails, POC, value area), the per-stock channel, "
                  "the constituent lanes and the journey scrubber"),
    "momentum-scan": ("DEFERRED", "M-Markets",
                      "LANDED at /dash/home/strength?view=momentum: the risk-adjusted momentum "
                      "table read from the same canonical momentum_scan rows, carrying the "
                      "beta-not-skill fence. NOT CARRIED BY DECISION: the C-blend overlay "
                      "(flat-cost-only, not fundable, and Screener-derived under primary-source "
                      "remediation). STILL OWED: the insider/credit veto flag column, the "
                      "equal-weight ensemble sort and the /dash/momentum-scan/slow child"),
    "sector-economics": ("DEFERRED", "M-Markets",
                         "LANDED at /dash/home/sectors?tab=economics: the sector x financial-year "
                         "median ROCE/OPM heat grid with the survivorship, thin-N, financials-blank "
                         "and Screener-provenance fences intact, plus a new risk-economics table. "
                         "UNVERIFIED ON DATA — the research fundamentals archive is absent from "
                         "the local fixture, so only structure is proven. STILL OWED: the per-cell "
                         "company breakdown and the biggest-swings panel"),
    # ── lane W2-C (2026-07-27): seasonal · patterns · anatomy · self-relative · compare ──
    # 10 classic lenses -> 5 Graphite declared-child routes. Parity is judged PER EVIDENCE BLOCK,
    # so a page that renders and reads well but is missing load-bearing blocks stays DEFERRED with
    # an explicit shipped/outstanding note — it is not promoted to PORTED on look alone.
    "seasonal-calendar": ("PORTED", "/dash/home/seasonal?view=calendar",
                          "Expiry/holiday conditioning, all four window deltas in bps + both counts "
                          "+ sort control + sym links + as-of + server CSV + the 0-certified null "
                          "prior fence; reads the same bounded x_setups_signals snapshot"),
    "seasonal-tape": ("DEFERRED", "M-Markets",
                      "SHIPPED /dash/home/seasonal?view=tape — month/weekday/ISO-week script grids "
                      "(grey by default, coloured only on full certification), the 'N of M cells "
                      "certified' winnowing headline, per-cell year-by-year stack, Pro forward-"
                      "outlook band with the white=noise read, frozen-family sha256 provenance, "
                      "0-certified fence. OUTSTANDING: monthly/weekly consolidation panels, the "
                      "per-cell placebo-null detail block, scope=stock + symbol search"),
    "seasonal-screen": ("DEFERRED", "M-Markets",
                        "SHIPPED /dash/home/seasonal?view=screen — Wilson-lower-bound ranking (not "
                        "raw hit-%), the 95% band on every row, an explicit indistinguishable-from-"
                        "chance flag, month + hot/cold selectors, server CSV. OUTSTANDING: the "
                        "'Strength t' sort dimension, the per-name month-rank column, and the "
                        "index=<Name> constituent filter"),
    "seasonal-divergence": ("DEFERRED", "M-Markets",
                            "SHIPPED /dash/home/seasonal?view=divergence — month-by-month cells for "
                            "two entities side by side + the gap + per-side year counts. "
                            "OUTSTANDING: the current-elapsed-year overlay read from seasonal_stack"),
    "harmonic-scan": ("DEFERRED", "M-Markets",
                      "SHIPPED /dash/home/patterns?view=harmonic — the full nine-column snapshot "
                      "table (shape · side · state · in-zone · age · price · zone/PRZ · fit), "
                      "as-of, read-by-side fence. OUTSTANDING: the weekly/monthly live multi-TF "
                      "scan and the ?refresh=1 live recompute (both are on-demand compute the "
                      "Graphite page deliberately does not do)"),
    "wolfe-scan": ("DEFERRED", "M-Markets",
                   "SHIPPED /dash/home/patterns?view=wolfe — snapshot table (side · in-zone · age · "
                   "price · zone · stop · first target · room), as-of, and the 'edge is in the "
                   "SELECTION, not the craft' fence. Ported READ-ONLY over wolfe_signals with no "
                   "import of wolfe*.py / stock_chart*.py (that lane is hot on origin/main). "
                   "OUTSTANDING: the §B quality components A-I/D + Q column, the three sort "
                   "dimensions, and the Fresh-setups / Open-trades toggle"),
    "move-anatomy": ("DEFERRED", "M-Markets",
                     "SHIPPED /dash/home/anatomy — the precursor fingerprint as standardised gaps "
                     "from the quiet baseline + the 6-month excursion envelope + the post-selection "
                     "/ survivorship / 1-in-10-baseline fence + the momentum-not-accumulation "
                     "finding. OUTSTANDING: the full ~20-precursor family breakdown and the "
                     "big-move rate column"),
    "self-history": ("DEFERRED", "M-Markets",
                     "SHIPPED /dash/home/own-history — the self-relative map rebuilt from STORED "
                     "stock_signals ratio columns (turnover vs own 1m/1y norm, delivery 1m vs 6m, "
                     "delivery size vs own 30-day and own best month, distance from own 52w high), "
                     "plus a per-symbol view ranking each ratio against that symbol's own trailing "
                     "history. DISCLOSED DIFFERENCE, NARROWED BY W1-CONVERGENCE (2026-07-27): the "
                     "3-year percentile over CORPORATE-ACTION-ADJUSTED OHLC now DOES exist, "
                     "per-symbol, as the Own-history section of /dash/home/stock — "
                     "reads.stock_selfref replicates the method (price · 3-month momentum · "
                     "delivery · turnover · coil) without importing the banned web-view engine, and "
                     "the adjustment is gate-pinned (a 1:1 bonus must not invert the percentile). "
                     "What is still not reproduced is that percentile as an ESTATE-WIDE MAP here. "
                     "OUTSTANDING: the "
                     "cross-sectional second lens (peer percentile + the both-extreme gold ring) "
                     "and the five-universe selector"),
    "compare": ("DEFERRED", "M-Markets",
                "SHIPPED /dash/home/compare — a NEW route; the sacred classic /dash/compare stays "
                "byte-untouched. Rebased-to-100 overlay of up to six stocks/indices, split/bonus "
                "adjusted from corporate_actions, URL-as-state with ?sym=&cmp=&idx=&r=. "
                "OUTSTANDING: the ratio-vs-denominator mode (mode=ratio&den=), the base=0 mode, and "
                "the searchable symbol picker"),
    "early-signals": ("DROPPED", "",
                      "NAMED CHECK RUN 2026-07-27 (lane W2-C), mechanism traced not pattern-matched: "
                      "the page owns NO data and NO compute of its own. Feed 1 is "
                      "stock_rs.phase_movers() filtered to turn-ups into Recovery/Tailwind — the "
                      "same rows /dash/rotation already renders (limit 40, both directions) and "
                      "/dash/rs-hub's RS section shows; feed 2 is divergence_board._scan() filtered "
                      "to the bullish half — that IS /dash/divergence's own scan. Its own docstring "
                      "states 'reads only precomputed tables, no new compute/storage'. What is left "
                      "after removing the duplication is a direction FILTER, i.e. a display preset, "
                      "not a distinct data claim -> DROPPED as a lens. NOT LOST: the classic route "
                      "stays live for bookmarks, and the claim must be re-homed as a 'just turned "
                      "up' filter on the Graphite rotation + divergence ports (a recorded dependency "
                      "on the W2 rotation/RS lane). NOTE for that lane: stock-grain rs_phase flips "
                      "are NOT on the signal-alerts bus — signal_events' 'rs' lens is INDEX-grain "
                      "(rsband_signals vs Nifty 500) — so the Graphite home's What-changed zone does "
                      "NOT already carry this; the rotation port must"),
    # ── Tracker (milestone M7, lane w3-tracker, 2026-07-27) ────────────────────────────
    # Five surfaces rebuilt as declared children of the Graphite home; the sixth is the
    # admitted duplicate and is DROPPED as a merge. Notes name the RESIDUAL honestly —
    # a port claim that hides what did not travel is worth nothing to the next session.
    "dashboard": ("PORTED", "/dash/home/tracker",
                  "Graphite Tracker overview: book totals · worth-a-look flags · movers · allocation "
                  "+ concentration + Pro contribution · books table · the model-book door. RESIDUAL: "
                  "alerts-firing, news-for-your-names and upcoming-corporate-actions blocks are NOT "
                  "rebuilt here — the Graphite home already renders news (reads.recent_news) and "
                  "going-ex (reads.upcoming_ca) for the whole market; filtering those to holdings is "
                  "the open follow-up rather than a second rendering"),
    "portfolios": ("PORTED", "/dash/home/tracker/portfolios",
                   "Positions in the Part III §J tracker column set, Kite-norm labels (Avg. cost · LTP · "
                   "Cur. val · P&L · Day chg.), frozen identity spine, Pro column layer, book chips with "
                   "URL state, server CSV. RESIDUAL: per-row WRITES (edit / close / single-position add) "
                   "and the dividends-since column stay on the classic page and are linked, not forked — "
                   "the lane adds exactly one write (the importer)"),
    "watchlists": ("PORTED", "/dash/home/tracker/watchlists",
                   "The canonical stocks_in_play watch tier, added through the home's EXISTING "
                   "POST /dash/home/watch/add (one write path, native date_added). RESIDUAL: per-row "
                   "alerts, promote and remove stay on the classic page and are linked; the shared add "
                   "POST still redirects to Today, so the confirmation lands there"),
    "performance": ("PORTED", "/dash/home/tracker/performance",
                    "Scoreboard: realised/unrealised ₹ P&L, hit-rate by strategy and book, average excess "
                    "vs Nifty 500, average hold, a CHAINED TIME-WEIGHTED return curve vs the benchmark + "
                    "its deepest fall. XIRR is rendered only when tracker_reads.cashflow_fidelity() passes "
                    "on the live rows (ratified §K.4 pre-condition); otherwise the page prints the "
                    "measurement and withholds the number. RESIDUAL: the classic page's CAGR and "
                    "book-value equity curve are deliberately NOT carried — both inherit the same "
                    "cash-flow defect (a deposit reads as a gain); the time-weighted chain replaces "
                    "them. Dividends received are still absent from every return figure"),
    "import": ("PORTED", "/dash/home/tracker/import",
               "File-or-paste onboarding: any column order, keyword header detection, symbols validated "
               "against bhavcopy_rows EQ/BE exactly as reads.watch_add does, unsaved preview with a "
               "per-row verdict, then a confirm that RE-VALIDATES before writing. RESIDUAL: .xlsx is not "
               "parsed (CSV/TSV/paste only) — the classic importer's openpyxl path did not travel"),
    "model-books": ("DROPPED", "",
                    "MERGE, not a deletion. model-books and model-portfolios rendered the SAME engine "
                    "books — the Tracker copy's own nav rationale admitted the numbers were 'already "
                    "covered by the model_portfolios data flow'. In the new experience there is one data "
                    "source and two doors: the books live in Strategies, and the Tracker carries the "
                    "'follow a book' view (a named book seeded with today's date and today's close, never "
                    "the backtest's history) as a section of /dash/home/tracker. The classic route stays "
                    "live and linked so existing bookmarks and the Adopt write keep working"),
    # ── W1, the Graphite stock page (2026-07-27) ──────────────────────────────────────
    # HONESTY NOTE, recorded deliberately: the classic stock DOSSIER (`/dash/stock`) is an
    # integration hub, not a registry lens, so it has no row of its own here. /dash/home/stock
    # carries each lens's PER-SYMBOL dossier tab, re-implemented over the same tables; the
    # estate-wide BOARD is a separate question, answered by the W3-A rows below.
    # INTEGRATION-2 RESOLUTION (2026-07-27): W1 filed six of those lenses — stocks · mep · cpr ·
    # concalls · growth · conviction — as DEFERRED-with-a-dossier-tab, on the evidence available to
    # it (no board existed yet). W3-A then BUILT the boards. Per the convergence precedent
    # (rs-hub / participants), the BOARD verdict wins the key and the dossier half survives as a
    # clause inside it, so nothing W1 observed is lost and no key claims twice. The six merged rows
    # are marked "+ W1 dossier tab" below.
    # ── W3-A · M7 Strategies estate (2026-07-27) — the 18 Strategies lenses, ported into the
    # Graphite workspace at /dash/home/strategies* per the ratified consolidations (plan §1c +
    # Part III §J). Each note states honestly what landed AND what did not.
    "strategist": ("PORTED", "/dash/home/strategies",
                   "the Strategies hub: registry health cards + the estate's honest headline + the "
                   "directory of every sub-page. NOT yet carried: the confluence-alerts strip, the "
                   "per-strategy new/dropped diff, the CCI-RRG divergence tile and 'Your boards'"),
    "model-portfolios": ("PORTED", "/dash/home/strategies/books",
                         "the 4 engine-locked books: per-book stats (return/vol labelled as a ratio, "
                         "not a Sharpe), NAV vs Nifty 500, the §J identity spine + book-core "
                         "constituents, the rebalance ledger, FUNDABLE-CORE vs GROSS-LENS banners. "
                         "NOT carried: survivability ballast overlay, all-books comparative chart, "
                         "time-travel stepper UI, Union/graduating table, CSV"),
    "sector-rotation": ("PORTED", "/dash/home/strategies/sector-rotation",
                        "the V21 sector-index book with the D138 scope gap ('picks SECTORS, not "
                        "STOCKS') and the D141 rejection rendered ABOVE the headline stat; weights, "
                        "rebalance diff, NAV, stats. NOT carried: the year-strip stepper UI, CSV"),
    "factor-league": ("PORTED", "/dash/home/strategies/library",
                      "MERGED with `classics` into one Strategy library with 🧑/🏠/📚 origin filters. "
                      "Live family rosters render from factor_league; the MEASURED verdicts "
                      "(return/vol, CAGR, excess, MaxDD, pass/fail) are deliberately LINKED to the "
                      "validation record + reference pages rather than restated — one copy of every "
                      "number. NOT carried: the churn feed"),
    "classics": ("PORTED", "/dash/home/strategies/library",
                 "the merge target: the classic-screens catalog + per-screen roster + NAV with the "
                 "'insufficient history — not a track record' fence. NOT carried: year-by-year "
                 "table, backdate form, holdings-as-of, CSV"),
    "conviction": ("PORTED", "/dash/home/strategies/conviction",
                   "the cross-pillar shortlist with the 'a sorting heuristic, not a validated model' "
                   "chip ABOVE the table and the Screener-archive provenance note on the Quality "
                   "column. NOT carried: the client-side filter pills. + W1 dossier tab: the "
                   "per-symbol conviction read ships as a digest tile on /dash/home/stock, "
                   "carrying the same heuristic label"),
    "stocks": ("PORTED", "/dash/home/strategies/positioning",
               "the DVPT positioning board. NOT carried: the 14 default-hidden columns, the "
               "weekly/monthly rollup, watchlist chips and filter pills. + W1 dossier tab: the "
               "per-symbol Positioning/DVPT read also lands on /dash/home/stock"),
    "stealth": ("PORTED", "/dash/home/strategies/positioning?view=stealth",
                "MERGED into `stocks` as a toggle — the classic site already admitted one renderer "
                "(/dash/stealth delegated to view=='stealth'); the stealth filter is reproduced "
                "exactly (accumulation + p>=3 + thinning trade count + <=-10% off the 52w high)"),
    "mep": ("PORTED", "/dash/home/strategies/mep",
            "the accumulation/distribution tape with the D62 descriptor-only fence first, the five "
            "phase counts, and the full component columns. NOT carried: glossary popovers. "
            "+ W1 dossier tab: the per-symbol Accumulation read (same D62 fence) also lands on "
            "/dash/home/stock"),
    "cpr": ("DROPPED", "",
            "DEMOTED, not deleted (plan §1c). Verified against the source: the standalone page's "
            "ONLY unique evidence is cross-SYMBOL ranking (reversal leaderboard, compression "
            "leaderboard, per-timeframe EOD digests) — every per-name CPR fact already lives in the "
            "stock dossier's CPR panel and the chart overlay (cpr_overlay.py), which is where a "
            "structure read is actually used. Classic /dash/cpr stays live and reachable for "
            "bookmarks; it simply leaves primary nav in the new experience. + W1 dossier tab: that "
            "per-name CPR panel (D/W/M/Q pivots) is now concretely on /dash/home/stock"),
    "concalls": ("PORTED", "/dash/home/strategies/credibility",
                 "management credibility, ABSORBING the orphaned /dash/credibility fingerprint as "
                 "?sym=. Gate-B fence rendered first ('descriptive only — never ranked') and the "
                 "board is ordered coverage-first, not by score. NOT carried: the three ·AI "
                 "behaviour columns (concall_behavior). + W1 dossier tab: the per-symbol "
                 "Credibility read (same Gate-B fence) also lands on /dash/home/stock"),
    "growth": ("PORTED", "/dash/home/strategies/growth",
               "the growth-intent proposal ledger with the placebo-kill verdict first. Adds the "
               "concall-corpus provenance disclosure (~98.6% discovered via Screener.in links, "
               "frozen legacy path) which the classic page did NOT carry. NOT carried: the "
               "instant text filter and the pullback tab (min-₹/since are query params, no UI). "
               "+ W1 dossier tab: the per-symbol Quality read (pt14 + capital allocation) also "
               "lands on /dash/home/stock"),
    "insider": ("PORTED", "/dash/home/strategies/ownership",
                "MERGED into the Ownership & filings hub (registry anomaly H): tiles + by-symbol "
                "board + the tape, all classified by the insider_events engine so the hub can never "
                "disagree with the classic lens"),
    "ratings": ("PORTED", "/dash/home/strategies/ownership?lens=ratings",
                "same hub, lens 2: company-level deduped transitions (credit_ratings engine) + the "
                "tape. ⚠ credit_rating_events is ABSENT from the laptop fixture, so this lens is "
                "SQL-verified against the canonical DDL but data-verified only on the box"),
    "sast": ("PORTED", "/dash/home/strategies/ownership?lens=sast",
             "same hub, lens 3: the stake × pledge confluence board (sast_events engine keeps the "
             ">=25% control exclusion and the Reg29(1) level-vs-flow split) + a unified tape over "
             "both feeds. NOT carried: the per-symbol drill"),
    "shp": ("DEFERRED", "M7",
            "BUILT and routed at /dash/home/strategies/ownership?lens=shp with the ratified §I.5 "
            "quarter matrix (symbol × quarter × promoter/FII/DII, mixed-source cells marked), but "
            "shareholding_history lives in the SEPARATE research store which does not exist off-box "
            "— so the read is unverifiable here. Promote to PORTED only after box verification. "
            "NOT carried: the QoQ delta board and its 7 tiles"),
    "launchpad": ("PORTED", "/dash/home/strategies/launchpad",
                  "the setup screen with the 'validated screen, no fundable edge net of cost' "
                  "verdict above it. Reads the nightly snapshot only — never the live market-wide "
                  "scan. NOT carried: the regime banner and the genuine-buyer count tile"),
    "launchpad-track": ("PORTED", "/dash/home/strategies/launchpad?tab=evidence",
                        "MERGED into `launchpad` as its evidence tab (it IS the screen's evidence): "
                        "the ignition_outcomes study — signals studied, hit rate, median 12m, median "
                        "dip, per-setup cohorts, the outcome histogram and the recovery ladder, "
                        "under its own gross-of-cost + survivorship warning. NOT carried: the "
                        "click-through winners/losers drill"),
    # ── W4 / M8 — the screener workspace (5 surfaces), lane `lane/w4-screener` 2026-07-27 ──
    # Verdicts are per-CAPABILITY, not per-page: the rebuild had to CARRY every job the classic
    # pages did, which is why two of the five are honestly retired rather than re-rendered.
    "screen2": ("PORTED", "/dash/home/screen",
                "The Graphite screener IS the migrated Screen+. Every capability carried — scope "
                "chips + sector picker, the 0-6 confluence lead column with its pillar dots, the "
                "self-scaling 30th-percentile turnover liquidity gate, the reclaim/slip descriptive "
                "cuts, column-family toggles, saved screens and CSV. Three recorded debts fixed in "
                "the rebuild: the ~2.3 MB single-document render became server-side pagination over "
                "a fixed-size internally-scrolling frozen-pane grid; the client-side CSV blob became "
                "a server ?format=csv export that honours the active filter/sort/column state; and "
                "the localStorage-only column/sort/filter state became URL state, so a screen is now "
                "a shareable link (saved screens = bookmarks, no per-browser silo)"),
    "themes":  ("PORTED", "/dash/home/themes",
                "Themes / Baskets carried as the non-ticker discovery door: the multi-label "
                "company_tags layer, grouped in the canonical vocabulary order with approved-only "
                "counts and index-seeded provenance shown, plus a per-theme participants view. New "
                "connection the classic page lacked: a theme hands off directly into the screener "
                "(/dash/home/screen?scope=theme:<tag>), so discovery and screening are one flow"),
    "screener": ("DROPPED", "",
                 "CUT (plan §1b). Two full screeners over the same universe and the same precomputed "
                 "tables is duplication, not choice — /dash/screen2 was already the declared superset "
                 "(it carries the classic screener's Identity/Conviction/Positioning/RS/Quality/"
                 "Context groups plus MEP, CCI, Wolfe, reversal and capital-allocation), and the "
                 "Graphite rebuild is a superset of THAT. Carrying a second grid would have meant two "
                 "column registries, two export paths and two education scaffolds over one dataset. "
                 "REVERSIBLE AND NON-DESTRUCTIVE: the classic route stays live and unmodified for "
                 "existing bookmarks; nothing is deleted, only un-rebuilt in the new experience"),
    "tags-review": ("NA", "",
                    "Owner/ops tool, not a customer lens. The page is a tag QUALITY DESK — approve or "
                    "reject AI-proposed theme tags, hand-add or remove them — i.e. it maintains the "
                    "data that /dash/home/themes reads. A visitor has nothing to do here and every "
                    "control on it is a write against the tag layer. It stays live and unmodified on "
                    "the classic site as the owner workflow it always was; the new experience shows "
                    "the RESULT (approved tags, with provenance) rather than the editing desk"),
    "workbench": ("DROPPED", "",
                  "EXAMINED, then absorbed (playbook §2.6 — 'what job does it do?'). The job was "
                  "'every DVPT / key-price / character / activity signal for the latest day in ONE "
                  "wide sortable exportable table' — which is exactly the job the screener now does, "
                  "with more columns and a real server export. Its one DISTINCT data claim was the "
                  "key-price family (key_price_p3m/6m/12m + their gaps, avg_close_p3m, avg_trade_qty, "
                  "avg_deliv_qty_per_trade, delivery_value_today, total_value_today), which classic "
                  "screen2 did NOT carry. That family is now IN the Graphite column pool and ships as "
                  "the named 'Key-price read' view — so this is an absorption with the evidence "
                  "carried, not a capability loss. Part III §J had already scoped the key-price "
                  "family into the ~70-column pool. Classic route stays live for bookmarks"),
}

_VALID_STATUS = {"PORTED", "DEFERRED", "DROPPED", "NA"}


def surfaces() -> list:
    """Derived: every routed lens (the screens). (key, label, altitude, route)."""
    return [(ln.key, ln.label, ln.altitude, ln.route) for ln in LR.LENSES if ln.route]


def metrics() -> list:
    """Derived: metric/term names from docs/metrics-glossary.md bullets (best-effort)."""
    p = os.path.join(_ROOT, "docs", "metrics-glossary.md")
    try:
        txt = open(p, encoding="utf-8").read()
    except OSError:
        return []
    # a metric bullet: "- **Term ....**  definition"
    return [m.strip() for m in re.findall(r"^-\s+\*\*(.+?)\*\*", txt, re.M)]


def strategies() -> list:
    """Derived: strategy pages (docs/strategies/*.md, excluding the index/README)."""
    out = []
    for f in sorted(glob.glob(os.path.join(_ROOT, "docs", "strategies", "*.md"))):
        base = os.path.basename(f).lower()
        if base in ("readme.md", "index.md", "_index.md"):
            continue
        out.append(os.path.basename(f)[:-3])
    return out


def disposition(key: str, altitude: str) -> tuple[str, str, str]:
    """The effective disposition for a surface: explicit entry, else the workspace default."""
    if key in SURFACE_PARITY:
        return SURFACE_PARITY[key]
    return ("DEFERRED", _WS_MILESTONE.get(altitude, "UNSCOPED"), "")


def summary() -> dict:
    """Counts for the board + the gate's non-degenerate sanity."""
    srf = surfaces()
    by_status: dict[str, int] = {"PORTED": 0, "DEFERRED": 0, "DROPPED": 0, "NA": 0}
    unscoped = 0
    for key, _label, alt, _route in srf:
        st, tgt, _n = disposition(key, alt)
        by_status[st] = by_status.get(st, 0) + 1
        if st == "DEFERRED" and tgt == "UNSCOPED":
            unscoped += 1
    return {
        "surfaces": len(srf), "metrics": len(metrics()), "strategies": len(strategies()),
        "by_status": by_status, "unscoped": unscoped,
    }


# ── the board (INTERNAL_DEV route) ────────────────────────────────────────────────────
_CSS = """
<style>
.sp-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 14px;max-width:1120px;}
.sp-note b{color:var(--ink);}
.sp-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 16px;}
.sp-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:11px;padding:11px 13px;}
.sp-tile .n{font-size:25px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.05;}
.sp-tile .l{font-size:11px;color:var(--ink-2);margin-top:5px;}
.sp-h{font-size:15px;font-weight:700;margin:18px 0 6px;color:var(--ink);}
table.sp{border-collapse:collapse;width:100%;font-size:12px;margin:0 0 8px;}
table.sp th{color:var(--ink-3);font-weight:600;text-align:left;padding:4px 8px;border-bottom:1px solid var(--line-2);}
table.sp td{padding:3px 8px;border-bottom:1px solid var(--line);vertical-align:top;}
table.sp td.k a{color:var(--accent);text-decoration:none;font-weight:600;}
.sp-pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:10.5px;font-weight:700;}
.sp-PORTED{background:rgba(35,160,90,.16);color:#1f9e5a;}
.sp-DEFERRED{background:rgba(200,150,20,.16);color:#c69316;}
.sp-UNSCOPED{background:rgba(210,70,70,.16);color:#d24646;}
.sp-DROPPED{background:var(--bg-3);color:var(--ink-3);}
.sp-NA{background:var(--bg-3);color:var(--ink-3);}
.sp-ms{color:var(--ink-3);font-size:11px;}
</style>
"""

_WS_ORDER = ("markets", "screener", "strategies", "tracker", "trust")
_WS_LABEL = {"markets": "Markets", "screener": "Screener", "strategies": "Strategies",
             "tracker": "Tracker", "trust": "Trust"}


def _pill(status: str, target: str) -> str:
    kind = "UNSCOPED" if (status == "DEFERRED" and target == "UNSCOPED") else status
    label = "UNSCOPED" if kind == "UNSCOPED" else status
    return f'<span class="sp-pill sp-{kind}">{label}</span>'


def _render() -> str:
    s = summary()
    body = [_CSS, '<h2 style="margin:0 0 2px">Sideways migration parity '
            '<small style="color:var(--ink-3);font-size:12px;font-weight:400">'
            'every classic element accounted for in the modern app · derived + gate-enforced</small></h2>']
    body.append(
        '<div class="sp-note">Guarantees nothing in the classic estate is <b>silently</b> missed as '
        'Sideways is rebuilt. The inventory is <b>derived</b> from the single-sources-of-truth '
        '(lens registry · metrics glossary · strategy docs), so a new element appears here the day it '
        'ships. Every surface carries a disposition; a gate (<code>tests/test_sideways_parity.py</code>) '
        'fails the build on any integrity violation (a dropped surface with no reason, a "done" '
        'milestone with un-ported surfaces). <b>UNSCOPED</b> = accounted but not yet assigned to any '
        'Sideways milestone — the visible planning gap. Descriptive; internal.</div>')

    bs = s["by_status"]
    tiles = [
        ("n", s["surfaces"], "surfaces (routed lenses)"),
        ("PORTED", bs["PORTED"], "ported + live"),
        ("DEFERRED", bs["DEFERRED"], "deferred / planned"),
        ("UNSCOPED", s["unscoped"], "UNSCOPED — no milestone yet"),
        ("n", s["metrics"], "metrics accounted"),
        ("n", s["strategies"], "strategies accounted"),
    ]
    thtml = ""
    for kind, n, lab in tiles:
        col = ({"PORTED": "#1f9e5a", "DEFERRED": "#c69316", "UNSCOPED": "#d24646"}
               .get(kind, "var(--ink)"))
        thtml += f'<div class="sp-tile"><div class="n" style="color:{col}">{n}</div><div class="l">{_esc(lab)}</div></div>'
    body.append(f'<div class="sp-tiles">{thtml}</div>')

    # milestones
    body.append('<div class="sp-h">Sideways milestones</div>')
    ms = '<table class="sp"><thead><tr><th>Milestone</th><th>Scope</th><th>Status</th></tr></thead><tbody>'
    for k, (lab, st) in MILESTONES.items():
        stp = 'sp-PORTED' if st == "DONE" else ('sp-DEFERRED' if st == "PLANNED" else 'sp-UNSCOPED')
        ms += f'<tr><td><b>{_esc(k)}</b></td><td>{_esc(lab)}</td><td><span class="sp-pill {stp}">{_esc(st)}</span></td></tr>'
    body.append(ms + '</tbody></table>')

    # surfaces by workspace
    srf = surfaces()
    for ws in _WS_ORDER:
        rows = [(k, lab, alt, rt) for (k, lab, alt, rt) in srf if alt == ws]
        if not rows:
            continue
        body.append(f'<div class="sp-h">{_esc(_WS_LABEL[ws])} <span class="sp-ms">· {len(rows)} surfaces</span></div>')
        t = ('<table class="sp"><thead><tr><th>Lens</th><th>Classic route</th><th>Disposition</th>'
             '<th>Target</th><th>Note</th></tr></thead><tbody>')
        for k, lab, alt, rt in rows:
            st, tgt, note = disposition(k, alt)
            tgt_txt = (f'<a href="{_esc(tgt)}" style="color:var(--accent);text-decoration:none">{_esc(tgt)}</a>'
                       if st == "PORTED" and tgt.startswith("/dash") else _esc(tgt or "—"))
            t += (f'<tr><td class="k"><a href="{_esc(rt)}">{_esc(lab)}</a> '
                  f'<span class="sp-ms">{_esc(k)}</span></td><td class="sp-ms">{_esc(rt)}</td>'
                  f'<td>{_pill(st, tgt)}</td><td class="sp-ms">{tgt_txt}</td>'
                  f'<td class="sp-ms">{_esc(note)}</td></tr>')
        body.append(t + '</tbody></table>')

    body.append(f'<div class="sp-note" style="margin-top:14px;color:var(--ink-3);font-size:11.5px">'
                f'Also accounted (port with their surfaces): <b>{s["metrics"]}</b> metrics '
                f'(<code>docs/metrics-glossary.md</code>) · <b>{s["strategies"]}</b> strategies '
                f'(<code>docs/strategies/</code>). v2 tightening: each item\'s honesty verdict '
                f'(descriptive-only / fundable / falsified) travels with the port. '
                f'<a href="/dash/sideways-parity?format=csv" style="color:var(--accent)">CSV</a></div>')
    return "".join(body)


def _csv() -> str:
    out = ["kind,key,label,workspace,classic_route,status,target,note"]
    for k, lab, alt, rt in surfaces():
        st, tgt, note = disposition(k, alt)
        note = note.replace(",", ";").replace("\n", " ")
        out.append(f'surface,{k},"{lab}",{alt},{rt},{st},{tgt},"{note}"')
    for m in metrics():
        out.append(f'metric,"{m.replace(chr(34), "")}",,,,DEFERRED,ports-with-surface,')
    for st in strategies():
        out.append(f'strategy,{st},,,,DEFERRED,M7,')
    return "\n".join(out) + "\n"


@router.get("/dash/sideways-parity", response_class=HTMLResponse)
def dash_sideways_parity(format: str = "") -> HTMLResponse:
    if format == "csv":
        return PlainTextResponse(_csv(), media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="sideways-parity.csv"'})
    try:
        html = _render()
    except Exception as e:  # noqa: BLE001 — never 500 an internal board
        html = (f'<h2>Sideways migration parity</h2><div class="sp-note">The parity ledger could not '
                f'render on this host ({_esc(str(e))}). It derives from lens_registry + '
                f'docs/metrics-glossary.md + docs/strategies/.</div>')
    return HTMLResponse(_shell("Sideways parity · patearn", _CSS + html, "", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/sideways-parity" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    srf = surfaces()
    assert len(srf) >= 50, ("too few surfaces derived", len(srf))
    # every surface resolves to a valid disposition
    for k, _lab, alt, _rt in srf:
        st, tgt, note = disposition(k, alt)
        assert st in _VALID_STATUS, (k, st)
        if st == "PORTED":
            assert tgt.startswith("/dash"), (k, "PORTED needs a route", tgt)
        if st in ("DROPPED", "NA"):
            assert note.strip(), (k, st, "needs a rationale")
        if st == "DEFERRED":
            assert tgt in MILESTONES, (k, "bad milestone", tgt)
    s = summary()
    assert s["metrics"] > 100 and s["strategies"] > 5, s
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    assert c.get("/dash/sideways-parity").status_code == 200
    assert "migration parity" in c.get("/dash/sideways-parity").text
    assert c.get("/dash/sideways-parity?format=csv").status_code == 200
    print("sideways_parity selftest OK — %d surfaces · %d metrics · %d strategies · %d UNSCOPED · board 200"
          % (s["surfaces"], s["metrics"], s["strategies"], s["unscoped"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
