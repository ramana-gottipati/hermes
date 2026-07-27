"""sideways_parity — the migration-parity ledger: guarantee nothing in the classic estate
is silently missed as the modern app ("Sideways") is rebuilt from scratch.

The problem
-----------
Sideways is a from-scratch rebuild (redesign M0-M8; identity mid-reselection). A from-scratch
rebuild is exactly where an estate of this size loses things — not maliciously, just silently.
"Be careful" does not scale. This module is the machine-enforced
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

⚠ THE COUNTS ARE NEVER WRITTEN DOWN HERE. This docstring used to open with "a 73-surface /
257-metric / 17-strategy estate" — three numbers that were true the day they were typed and wrong
by the time anyone read them (74 / 265 / 16 at the Graphite cutover). A derived inventory whose
own documentation restates its output by hand is exactly the drift the module exists to prevent.
Ask the code: `summary()` returns {surfaces, metrics, strategies, by_status, unscoped}, and the
board at /dash/sideways-parity prints the live figures. If you need a number, run it.

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
    # M3/M4/M5 were marked DONE against the PREVIEW estate; the W6 retirement (2026-07-27) moved
    # each one's surface to its Graphite twin. Still DONE — the capability did not move milestone,
    # it moved address: M3's wire → the home's Market-news zone, M4's hub → /dash/home/stock (the
    # W1-CONVERGENCE lineage), M5's Today → the Graphite home, which IS the default landing (D148).
    # ⚠ HONESTY LIMIT on M4, recorded 2026-07-28: no ROUTED LENS is assigned to M3/M4/M5, so
    # `test_done_milestones_are_fully_ported` passes over them VACUOUSLY. The classic stock dossier
    # is an integration hub, not a registry lens (see the W1 note below), so the gap register's §9
    # — 20 fresh MAJOR rows against /dash/home/stock (intervals · chart types · lower panes ·
    # indicator family · compare overlay · momentum pane · RS overlay · DVPT inertia table …) —
    # is INVISIBLE to this gate. M4's DONE means "the hub shipped", never "the dossier is at parity".
    "M3":       ("News / flow dock", "DONE"),
    "M4":       ("Stock hub (dossier)", "DONE"),
    "M5":       ("Today / orientation home", "DONE"),
    # W6 (2026-07-27) flipped M6/M7/M8 to DONE. RE-OPENED to PLANNED 2026-07-28 by the gap audit
    # (docs/graphite-gap-register.md, 464 rows / 160 MAJOR): the flips were honest against the board
    # AS IT THEN READ, but the board over-claimed — 34 surfaces recorded PORTED still hold open
    # MAJOR rows (capability that is FREE in classic sitting behind a Pro teaser, whole evidence
    # blocks and controls that never travelled, two live correctness defects). Downgrading those to
    # DEFERRED puts non-PORTED surfaces back inside M6/M7/M8, so the milestones must follow them —
    # `test_done_milestones_are_fully_ported` is exactly the gate that says so, and it is doing its
    # job rather than being worked around. Each flips back to DONE when its register rows close.
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
    # W6 RETARGET (2026-07-27): both used to point at /dash/preview, which is now RETIRED (302 →
    # the Graphite home). A PORTED target that resolves to a redirect is a target that no longer
    # says where the capability lives, so both move to the surface that actually carries them.
    "markets": ("PORTED", "/dash/home",
                "the Graphite home IS the migrated markets overview / orientation home — the M5 "
                "Today anatomy (regime line · featured card · market map · pulse deck · today's "
                "conviction · what changed) now serving as the site's default landing (D148)"),
    "wire":    ("PORTED", "/dash/home",
                "the 'Market news' zone of the Graphite home (reads.recent_news, 20 rows, "
                "symbol-tagged, title/source/link only per the copyright fence) is the migrated "
                "News/Wire. NOT carried: the preview's 6-channel dock as a separate component — "
                "its other five channels became first-class Graphite surfaces instead (filings + "
                "corporate actions + results on the home rail, deals/positioning on "
                "/dash/home/flows, alerts on /dash/home/attention)"),

    # ── M-Markets · lane W2-A (2026-07-27): eleven classic Markets lenses consolidated into FOUR
    # Graphite pages. Consolidation, not transliteration — each page answers ONE question with its
    # evidence stacked under it. Every note below states what travelled AND what deliberately did
    # not, so a "PORTED" here can never over-claim (the classic lens stays live either way).
    "market-internals": ("DEFERRED", "M-Markets",
                         "LANDED at /dash/home/internals: the five vital signs with Pro percentile "
                         "references vs the full 2004-> history, the price-breadth-vs-tape hero, the "
                         "delivery/dispersion/coil regimes, the crisis-fingerprint anchors and a "
                         "session drill. NOT carried: the 1200-cell daily heat ribbon (the drill is "
                         "reached from a 20-session strip instead) — classic keeps it. "
                         "RE-OPENED by the 2026-07-28 gap audit (register §3a, 3 MAJOR): the three "
                         "regime charts are Pro-BLURRED and the exact percentile ordinal Pro-only, "
                         "both FREE in classic — this note claimed the regimes carried, with no "
                         "Pro caveat"),
    "divergence": ("DEFERRED", "M-Markets",
                   "LANDED at /dash/home/internals: the RSI-of-RS divergence watch (bullish/bearish "
                   "columns + the momentum-extremes strip) is the Divergence-watch zone of the "
                   "Graphite internals page; the home's own breadth-vs-delivery two-gauge stays the "
                   "Today-level seed. RE-OPENED by the 2026-07-28 gap audit (register §3b, 1 "
                   "MAJOR): every divergence name is a click-through to its RS-momentum pane in "
                   "classic and is DEAD TEXT here — a divergence you cannot open is a list, not a "
                   "watch; the bull/bear lists are also truncated to 10 a side (classic unbounded)"),
    "participants": ("DEFERRED", "M-Markets",
                     "LANDED at /dash/home/flows: the FII index-futures stance with its own-history "
                     "percentile, the four-participant matrix (index fut net · long:short · stock "
                     "fut net · index option lean) and the recent-session history (Pro). Sits "
                     "beside the home's existing FII/DII cash reads rather than duplicating them. "
                     "RE-OPENED by the 2026-07-28 gap audit (register §3c, 3 MAJOR): the FII-vs-"
                     "retail MIRROR CHARTS this note claimed are one conditional sentence, the "
                     "stance-ratio chart regressed to the 40-day window the classic module was "
                     "built to replace, and Free lost the percentile extremity read-out"),
    "fno": ("DEFERRED", "M-Markets",
            "LANDED at /dash/home/flows: the own-history F&O board (OI · PCR · max-pain percentiles "
            "+ build-up streak) with the auto reality-check callouts and a server CSV; the Phase-0 "
            "fence travels ON the block (PCR selects weakly, forward-test-only; max-pain/basis/"
            "OI-change failed). The PER-SYMBOL F&O read (OI · change · quadrant · PCR · basis · "
            "max-pain · put/call walls from fno_oi_signals) is the F&O section of /dash/home/stock "
            "(W1). RE-OPENED by the 2026-07-28 gap audit (register §3d, 1 MAJOR): Free sees 12 of "
            "~200 names and the rest is Pro-blurred — classic served the whole cross-section free"),
    "actions": ("DEFERRED", "M-Markets",
                "LANDED at /dash/home/events: the forward corporate-actions calendar grouped by "
                "ex-date with type counts, the recent-past + security-events context (Pro) and a "
                "server CSV; reuses the home's reads.upcoming_ca (same corp_actions.upcoming single "
                "source). E-11/E-12 logistics fence carried. RE-OPENED by the 2026-07-28 gap audit "
                "(register §3e, 2 MAJOR): the just-went-ex + restructure context is Pro-gated "
                "(free in classic) AND cut ~16× under that gate — 30d/200 rows became 14d/12, "
                "security_events 180d/40 became 14d/6 — a depth loss the note never named"),
    "results-reactions": ("DEFERRED", "M-Markets",
                          "LANDED at /dash/home/events: the results-reaction board (surprise · "
                          "delivery multiple · realized 22/60-day abnormal move) + who-reports-next, "
                          "with the falsification fence stated ABOVE the table (tradeable book net "
                          "ret/vol 0.10 vs bench 0.85). NOT carried: the CAR fan SVG and the "
                          "published-brief cards — classic keeps them. RE-OPENED by the 2026-07-28 "
                          "gap audit (register §3f, 3 MAJOR): on top of those two, the STALE-TAPE "
                          "BANNER did not travel — the read returns tape_max_trade_date and nothing "
                          "consumes it, so a board N weekdays behind reads as current"),
    "event-cadence": ("PORTED", "/dash/home/events",
                      "overdue-vs-own-rhythm + expected-by-cadence tables with the event-type filter "
                      "and the dormant count, off the same bounded seasonal_events snapshot; TIME-only "
                      "fence carried verbatim. Index-membership filter not carried (event-type only)"),
    "buyback-calc": ("DEFERRED", "M-Markets",
                     "LANDED at /dash/home/events: the tender-quota calculator (accepted · tender "
                     "P&L · residual · net · breakeven exit) with the live ₹2L small-shareholder "
                     "eligibility read-out, anchored by the buyback rows on the corporate-actions "
                     "feed; the acceptance-ratio-is-YOUR-assumption fence carried. RE-OPENED by the "
                     "2026-07-28 gap audit (register §3h, 2 MAJOR): the 20/33/50/66/100% "
                     "acceptance-ratio SENSITIVITY TABLE — the classic module's stated substitute "
                     "for refusing to fabricate a prior — and the days-locked/annualized-return "
                     "pair did not travel"),
    "surveillance": ("DEFERRED", "M-Markets",
                     "LANDED at /dash/home/events: the ASM/GSM/price-band transition tape + "
                     "current-state counts, single-sourced through surveillance.transitions/"
                     "current_state so page == card == pillar; 'context, never a gate' fence "
                     "carried. RE-OPENED by the 2026-07-28 gap audit (register §3i, 1 MAJOR): only "
                     "the COUNTS carried — the per-framework 'under surveillance now' MEMBERSHIP "
                     "LISTS (symbol · stage · dossier link) have no Graphite home, which this note "
                     "implied rather than stated"),
    "band-locks": ("PORTED", "/dash/home/events",
                   "the close-at-band streak board single-sourced through band_lock.active_streaks, "
                   "with the honest-window note (bands reconstructable only back to the feed's first "
                   "captured day) and the no-study-exists fence. GAP NOTE (register §3j): the one "
                   "MAJOR row was a live CORRECTNESS defect — the read/render compared the "
                   "direction against lowercase while the engine emits UP/DOWN, so every row read "
                   "'▼ lower' and both tiles read 0. FIXED 2026-07-28 (lane/parity-truth) and "
                   "pinned by tests/test_graphite_parity_defects.py; residue is MINOR only (Close "
                   "column, longest-streak tile, ⚑ flag marker, 30-row cap)"),
    "attention": ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/attention: the magnitude-ranked queue with lens filters, "
                  "per-batch counts, ?as_of= last-batch-on-or-before replay and the curated alert "
                  "rail; the depth behind the home's 'What changed today' band (which keeps owning "
                  "severity_counts/what_changed). NOT carried: the acknowledge WRITE and the cookie "
                  "'since you last looked' brief — owner actions that stay on the classic page. "
                  "RE-OPENED by the 2026-07-28 gap audit (register §3k, 4 MAJOR): 'full' was wrong "
                  "— the queue renders 30 rows where classic renders 200 with a 'showing N of M' "
                  "line, and the severity/valence rail filter chips did not travel"),
    # ── Graphite cutover wave W2-B (2026-07-27): the RS · rotation · sectors families ──
    # Eleven classic Markets lenses consolidated into THREE Graphite pages. The rule applied:
    # PORTED = the question the lens exists to answer is fully served at the new route.
    # DEFERRED = the headline block landed but a materially separate block is still owed — the
    # note names exactly what travelled and what did not, so nothing is silently missed.
    "rrg":       ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/rotation: the 6/12/24-month RRG journeys reuse the "
                  "canonical JdK engine (automation/rrg._rs_ratio_momentum + quadrant). RE-OPENED "
                  "by the 2026-07-28 gap audit (register §1a, 10 MAJOR): the whole Play apparatus "
                  "(playback · 3 speeds · draggable scrubber · month badge · hover-to-trace), the "
                  "3-month horizon, the RS-depth table with its 7 turn-flag Signals pills; 12M+24M "
                  "are Pro-locked though FREE in classic; and BOTH per-symbol drills (?idx= "
                  "constituents, ?sym= single stock) — which this note said 'belong to the "
                  "Graphite stock hub' — are neither there nor built anywhere"),
    "rotation":  ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/rotation?view=weather: the sector phase table (phases "
                  "classified by the canonical rs_phase engine, not the additive column), the 2x2 "
                  "lifecycle grid with the strict-diagonal shortlists, and the just-turned strip. "
                  "RE-OPENED by the 2026-07-28 gap audit (register §1b, 5 MAJOR): the classic lens "
                  "is STOCK-grain and that half did not travel — no ?phase= selector, no 300-row "
                  "member table, the per-cell count is a dead number not a 'see all' door, no "
                  "7 leverage-read pills, and `early-signals`' DROP rationale still owes this page "
                  "its just-turned-UP direction filter"),
    "cycle-clock": ("DEFERRED", "M-Markets",
                    "LANDED at /dash/home/rotation?view=clock: the lifecycle dial — every sector's "
                    "RS-Ratio x RS-Momentum on one radial plot plus the same dial as a table, from "
                    "the same rs_extras snapshot. RE-OPENED by the 2026-07-28 gap audit (register "
                    "§1d, 2 MAJOR): the VELOCITY VECTOR (the tangent arrow that is the lens's "
                    "stated reason to exist over the 2x2 grid) is absent, and RSI-of-RS is "
                    "Pro-gated though free on the classic hover"),
    "rs-hub":    ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/strength: universe-wide standing counts, the four-reading "
                  "card set, and today's strongest names with their phase and trend state. The "
                  "PER-SYMBOL half (rank · trend state · phase · 1/3/6/12-month slopes · vs its own "
                  "sector) is the Strength section of /dash/home/stock (W1). RE-OPENED by the "
                  "2026-07-28 gap audit (register §2a, 2 MAJOR): the benchmark selector ?den= — the "
                  "hub's ONLY control, which also re-drove every child-lens link — did not travel "
                  "(markets_reads hardcodes Nifty 500 lane-wide), and 3m RS / 12m RS / RSI-of-RS "
                  "are Pro-gated though free on every classic RS surface"),
    "leaders":   ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/strength?view=leaders: strong-in-strong / weak-in-weak, "
                  "straight from the canonical stock_rs.leaders_laggards screen. RE-OPENED by the "
                  "2026-07-28 gap audit (register §2b, 2 MAJOR): 'shown in Pro' IS the regression — "
                  "RSI-of-RS and all three alignment-state columns (stock vs broad · stock vs "
                  "sector · sector vs broad) were unconditionally visible in classic and ARE the "
                  "screen's thesis, so Free now sees only symbol/rank/sector"),
    "capture-map": ("DEFERRED", "M-Markets",
                    "LANDED at /dash/home/strength?view=capture: up-capture / down-capture / spread "
                    "per sector at 3, 6 and 12 months, from the canonical automation/capture "
                    "engine, with the four-way behaviour read. RE-OPENED by the 2026-07-28 gap "
                    "audit (register §2d, 2 MAJOR): the SCATTER — the lens itself, whose docstring "
                    "says the two table columns hide the up=down diagonal — is not in the module at "
                    "all, and the ?den= benchmark selector did not travel"),
    "sectors":   ("DEFERRED", "M-Markets",
                  "LANDED at /dash/home/sectors: the sector standing board — weather, 1/3/12-month "
                  "RS, member breadth (the cross-check the classic board lacked) and the Pro return "
                  "columns. RE-OPENED by the 2026-07-28 gap audit (register §2e, 1 MAJOR): 'the Pro "
                  "return columns' IS the regression — 1m and 3m return were free in classic; the "
                  "RS heat strip also collapsed 6 horizons to 3"),
    "sector-momentum": ("DEFERRED", "M-Markets",
                        "LANDED at /dash/home/sectors?sec=: the constituent drill-down, promoted "
                        "from a deep-link-only orphan to a URL-addressable view of the sector board "
                        "it belongs to. RE-OPENED by the 2026-07-28 gap audit (register §2f, 3 "
                        "MAJOR): RSI-of-RS — the only thing the classic page ranks by — is "
                        "Pro-gated, the momentum-breadth read is Pro-gated AND degraded (three free "
                        "percentages with bars became a Pro sentence with two raw counts), and the "
                        "sector picker chip row that IS the page's navigation is absent"),

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
                      "0-certified fence. CORRECTION 2026-07-28 (register §4b): the ISO-week grid "
                      "was listed here as SHIPPED but could NEVER render on any entity — the read "
                      "asked seasonal_cells for axis='week' while the engine persists 'iso_week', "
                      "so the grid and its cell-drill were structurally dead. FIXED in "
                      "lane/parity-truth (w2_reads translates the store key once) and pinned by "
                      "tests/test_graphite_parity_defects.py. Also unrecorded until now: the "
                      "forward-outlook band is FREE on classic and Pro-gated here. OUTSTANDING: "
                      "monthly/weekly consolidation panels, the three per-year STACK grids "
                      "(25-year month · 52-week · weekday), the per-cell placebo-null detail "
                      "block, scope=stock + symbol search"),
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
    "dashboard": ("DEFERRED", "M7",
                  "LANDED at /dash/home/tracker: book totals · worth-a-look flags · movers · "
                  "allocation + concentration + Pro contribution · books table · the model-book "
                  "door. RESIDUAL: alerts-firing, news-for-your-names and upcoming-corporate-"
                  "actions blocks are NOT rebuilt here — the Graphite home already renders news "
                  "(reads.recent_news) and going-ex (reads.upcoming_ca) for the whole market. "
                  "RE-OPENED by the 2026-07-28 gap audit (register §5a, 4 MAJOR): beyond the "
                  "recorded three, the zero-config READY-TO-ACT block is gone, the attention flags "
                  "dropped 6 -> 4 (no DISTRIBUTION character, no RS-decay or conviction drift vs "
                  "the frozen entry snapshot) and contributors/detractors — a free bar chart in "
                  "classic — is Pro-only"),
    "portfolios": ("DEFERRED", "M7",
                   "LANDED at /dash/home/tracker/portfolios: positions in the Part III §J tracker "
                   "column set, Kite-norm labels (Avg. cost · LTP · Cur. val · P&L · Day chg.), "
                   "frozen identity spine, Pro column layer, book chips with URL state, server CSV. "
                   "RESIDUAL: per-row WRITES (edit / close / add) and the dividends-since column "
                   "stay on the classic page and are linked, not forked. RE-OPENED by the "
                   "2026-07-28 gap audit (register §5b, 4 MAJOR): the 'Pro column layer' hides SIX "
                   "columns that were free in classic (Weight · Target · Stop · Days held · RS "
                   "phase · Book), the Thesis-health column is absent, and 'single-position add' "
                   "understates a 9-field quick-capture form with symbol autocomplete"),
    "watchlists": ("DEFERRED", "M7",
                   "LANDED at /dash/home/tracker/watchlists: the canonical stocks_in_play watch "
                   "tier, added through the home's EXISTING POST /dash/home/watch/add (one write "
                   "path, native date_added). RESIDUAL: per-row alerts, promote and remove stay on "
                   "the classic page and are linked; the shared add POST still redirects to Today. "
                   "RE-OPENED by the 2026-07-28 gap audit (register §5c, 4 MAJOR): six of thirteen "
                   "columns are Pro-gated (four free in classic), the add form collapsed 9 fields "
                   "to a bare symbol box, and the Signal/alerts column (ready badge + firing chips) "
                   "did not travel"),
    "performance": ("DEFERRED", "M7",
                    "LANDED at /dash/home/tracker/performance: realised/unrealised ₹ P&L, hit-rate "
                    "by strategy and book, average excess vs Nifty 500, average hold, a CHAINED "
                    "TIME-WEIGHTED return curve vs the benchmark + its deepest fall. XIRR is "
                    "rendered only when tracker_reads.cashflow_fidelity() passes on the live rows "
                    "(ratified §K.4 pre-condition); otherwise the page prints the measurement and "
                    "withholds the number. RESIDUAL: the classic page's CAGR and book-value equity "
                    "curve are deliberately NOT carried — both inherit the same cash-flow defect (a "
                    "deposit reads as a gain). Dividends received are still absent from every "
                    "return figure. RE-OPENED by the 2026-07-28 gap audit (register §5d, 1 MAJOR): "
                    "the RETURN-ATTRIBUTION section (by holding · sector · book · strategy) is gone "
                    "entirely and was not in the recorded removals"),
    "import": ("DEFERRED", "M7",
               "LANDED at /dash/home/tracker/import: file-or-paste onboarding — any column order, "
               "keyword header detection, symbols validated against bhavcopy_rows EQ/BE exactly as "
               "reads.watch_add does, unsaved preview with a per-row verdict, then a confirm that "
               "RE-VALIDATES before writing. RESIDUAL: .xlsx is not parsed (CSV/TSV/paste only). "
               "RE-OPENED by the 2026-07-28 gap audit (register §5e, 2 MAJOR): the manual "
               "column-mapping override also did not travel — classic guesses then lets you fix "
               "five selects against the real header list, so in Graphite a bad guess is "
               "unrecoverable"),
    "model-books": ("DROPPED", "",
                    "MERGE, not a deletion. model-books and model-portfolios rendered the SAME engine "
                    "books — the Tracker copy's own nav rationale admitted the numbers were 'already "
                    "covered by the model_portfolios data flow'. In the new experience the books live "
                    "in Strategies (/dash/home/strategies/books) and the classic route stays live and "
                    "linked so existing bookmarks and the Adopt write keep working. "
                    "CORRECTION 2026-07-28 (register §5f): this note used to claim 'the Tracker "
                    "carries the follow-a-book view … as a section of /dash/home/tracker'. IT DOES "
                    "NOT — tracker_pages._model_books_block is prose plus two links, one of them "
                    "back to the classic page, and its own docstring concedes 'the FOLLOW door "
                    "deliberately stays on classic'. The DROP verdict stands (one engine, one data "
                    "source) but the follow/adopt WRITE has no Graphite door, and the Graphite books "
                    "page covers only the 4 auto books — classic also lists the classic_portfolio_nav "
                    "estate with adopt buttons"),
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
    "model-portfolios": ("DEFERRED", "M7",
                         "LANDED at /dash/home/strategies/books: the 4 engine-locked books — "
                         "per-book stats (return/vol labelled as a ratio, not a Sharpe), NAV vs "
                         "Nifty 500, the §J identity spine + book-core constituents, the rebalance "
                         "ledger, FUNDABLE-CORE vs GROSS-LENS banners. NOT carried: survivability "
                         "ballast overlay, all-books comparative chart, Union/graduating table, "
                         "CSV. CORRECTED + RE-OPENED 2026-07-28 (register §6b, 2 MAJOR): this note "
                         "said 'time-travel stepper UI', i.e. a missing CONTROL — the whole "
                         "TIME-TRAVEL CAPABILITY is missing. The route never passes ?asof= and "
                         "book_holdings(conn, book) is called without it, so holdings at a past "
                         "rebalance cannot be read at all, by any URL. The since-year chips "
                         "(2012/2019/2022) are likewise parsed with no door rendered"),
    "sector-rotation": ("PORTED", "/dash/home/strategies/sector-rotation",
                        "the V21 sector-index book with the D138 scope gap ('picks SECTORS, not "
                        "STOCKS') and the D141 rejection rendered ABOVE the headline stat; weights, "
                        "rebalance diff, NAV, stats. NOT carried: the year-strip stepper UI, CSV"),
    "factor-league": ("DEFERRED", "M7",
                      "LANDED at /dash/home/strategies/library, MERGED with `classics` into one "
                      "Strategy library with 🧑/🏠/📚 origin filters. Live family rosters render from "
                      "factor_league; the MEASURED verdicts (return/vol, CAGR, excess, MaxDD, "
                      "pass/fail) are deliberately LINKED to the validation record + reference pages "
                      "rather than restated — one copy of every number. NOT carried: the churn feed. "
                      "RE-OPENED by the 2026-07-28 gap audit (register §6j, 3 MAJOR shared with "
                      "`classics`): the library renders ONE fixed 5-column roster for every family, "
                      "so the per-screen custom column sets are gone; the factor-league roster "
                      "specifically loses 6m · 12m · Vol · Turn₹cr, and its per-family ?fmt=csv is "
                      "unrecorded and absent"),
    "classics": ("DEFERRED", "M7",
                 "LANDED at /dash/home/strategies/library as the merge target: the classic-screens "
                 "catalog + per-screen roster + NAV with the 'insufficient history — not a track "
                 "record' fence. NOT carried: year-by-year table, backdate form, holdings-as-of, "
                 "CSV. RE-OPENED by the 2026-07-28 gap audit (register §6j, 3 MAJOR): those first "
                 "three ARE MAJOR, not residue, and a fourth was unrecorded — classic renders a "
                 "screen-specific column list with per-header glossary popovers, Graphite one fixed "
                 "#/Symbol/Sector/Price/Score roster for every screen"),
    "conviction": ("PORTED", "/dash/home/strategies/conviction",
                   "the cross-pillar shortlist with the 'a sorting heuristic, not a validated model' "
                   "chip ABOVE the table and the Screener-archive provenance note on the Quality "
                   "column. NOT carried: the client-side filter pills — CORRECTED 2026-07-28 "
                   "(register §6d): that list was incomplete, TWO DATA COLUMNS also vanished (the "
                   "MEP confirmation column and the entry-read column: near-key / discount / "
                   "extended / at-cost). Disposition unchanged — every open row is MINOR or "
                   "COSMETIC, no MAJOR. + W1 dossier tab: the per-symbol conviction read ships as a "
                   "digest tile on /dash/home/stock, carrying the same heuristic label"),
    "stocks": ("DEFERRED", "M7",
               "LANDED at /dash/home/strategies/positioning: the DVPT positioning board. NOT "
               "carried: the weekly/monthly rollup, watchlist chips and filter pills. CORRECTED "
               "2026-07-28 (register §6c): this note claimed all 14 default-hidden columns were "
               "dropped — 3 of them (RS#, 52w-hi, Gap3m) ARE carried; 11 genuinely are not. "
               "RE-OPENED (2 MAJOR): the ?sector= constituent filter did not travel at all, and the "
               "8 filter pills became a 2-item All/Stealth strip. + W1 dossier tab: the per-symbol "
               "Positioning/DVPT read also lands on /dash/home/stock"),
    "stealth": ("PORTED", "/dash/home/strategies/positioning?view=stealth",
                "MERGED into `stocks` as a toggle — the classic site already admitted one renderer "
                "(/dash/stealth delegated to view=='stealth'); the stealth filter is reproduced "
                "exactly (accumulation + p>=3 + thinning trade count + <=-10% off the 52w high)"),
    "mep": ("PORTED", "/dash/home/strategies/mep",
            "the accumulation/distribution tape with the D62 descriptor-only fence first and the "
            "five phase counts. NOT carried: glossary popovers. CORRECTED 2026-07-28 (register "
            "§6e): this note said 'the full component columns' — it is not the full set. The raw "
            "daily 'Today' score (mep_score), which classic shows BESIDE the smoothed phase score, "
            "is absent; the row cap also fell 300 -> 80. Disposition unchanged — both rows are "
            "MINOR, no MAJOR. + W1 dossier tab: the per-symbol Accumulation read (same D62 fence) "
            "also lands on /dash/home/stock"),
    "cpr": ("DROPPED", "",
            "DEMOTED, not deleted (plan §1c). Verified against the source: the standalone page's "
            "ONLY unique evidence is cross-SYMBOL ranking (reversal leaderboard, compression "
            "leaderboard, per-timeframe EOD digests) — every per-name CPR fact already lives in the "
            "stock dossier's CPR panel and the chart overlay (cpr_overlay.py), which is where a "
            "structure read is actually used. Classic /dash/cpr stays live and reachable for "
            "bookmarks; it simply leaves primary nav in the new experience. + W1 dossier tab: that "
            "per-name CPR panel (D/W/M/Q pivots) is now concretely on /dash/home/stock"),
    "concalls": ("DEFERRED", "M7",
                 "LANDED at /dash/home/strategies/credibility, ABSORBING the orphaned "
                 "/dash/credibility fingerprint as ?sym=. Gate-B fence rendered first ('descriptive "
                 "only — never ranked') and the board is ordered coverage-first, not by score. NOT "
                 "carried: the three ·AI behaviour columns (concall_behavior). RE-OPENED by the "
                 "2026-07-28 gap audit (register §6f, 1 MAJOR): 'ordered coverage-first' removed a "
                 "CONTROL — classic offers an Avoid / Track-record view toggle that re-sorts "
                 "worst-first, and the Graphite route takes only ?sym=. + W1 dossier tab: the "
                 "per-symbol Credibility read (same Gate-B fence) also lands on /dash/home/stock"),
    "growth": ("PORTED", "/dash/home/strategies/growth",
               "the growth-intent proposal ledger with the placebo-kill verdict first. Adds the "
               "concall-corpus provenance disclosure (~98.6% discovered via Screener.in links, "
               "frozen legacy path) which the classic page did NOT carry. NOT carried: the "
               "instant text filter and the pullback tab (min-₹/since are query params, no UI). "
               "+ W1 dossier tab: the per-symbol Quality read (pt14 + capital allocation) also "
               "lands on /dash/home/stock"),
    "insider": ("DEFERRED", "M7",
                "LANDED at /dash/home/strategies/ownership, MERGED into the Ownership & filings hub "
                "(registry anomaly H): tiles + by-symbol board + the tape, all classified by the "
                "insider_events engine so the hub can never disagree with the classic lens. "
                "CORRECTED + RE-OPENED 2026-07-28 (register §6i, 3 MAJOR): this key was recorded "
                "with NO residual at all, which was false — the 30/90/180-day WINDOW SELECTOR is "
                "hardcoded to 90, the class tab filters (?cls=conviction|caution|…) and the "
                "per-symbol drill (?sym=, ?min_cr=) did not travel, and the Net-90d and Pledge-ev. "
                "columns are gone"),
    "ratings": ("DEFERRED", "M7",
                "LANDED at /dash/home/strategies/ownership?lens=ratings — same hub, lens 2: "
                "company-level deduped transitions (credit_ratings engine) + the tape. ⚠ "
                "credit_rating_events is ABSENT from the laptop fixture, so this lens is "
                "SQL-verified against the canonical DDL but data-verified only on the box. "
                "RE-OPENED by the 2026-07-28 gap audit (register §6i, 3 MAJOR): the 90/180/365-day "
                "window selector is hardcoded to 180, the ?cls=UPGRADE|DOWNGRADE tab filter and the "
                "per-symbol drill did not travel; the Action column and the filing link are also "
                "off the board"),
    "sast": ("DEFERRED", "M7",
             "LANDED at /dash/home/strategies/ownership?lens=sast — same hub, lens 3: the stake × "
             "pledge confluence board (sast_events engine keeps the >=25% control exclusion and the "
             "Reg29(1) level-vs-flow split) + a unified tape over both feeds. NOT carried: the "
             "per-symbol drill. RE-OPENED by the 2026-07-28 gap audit (register §6i, 3 MAJOR): the "
             "drill was the only loss recorded, but the 30/90/180-day WINDOW SELECTOR is hardcoded "
             "to 90 and the ?feed=INVOKE|… class filter did not travel either; the Acq-90d, "
             "Sold-90d and Invoked columns are also off the board"),
    "shp": ("PORTED", "/dash/home/strategies/ownership?lens=shp",
            "the ratified §I.5 quarter matrix (symbol × quarter × promoter/FII/DII, mixed-source "
            "cells marked). W3-A held this DEFERRED because shareholding_history lives in the "
            "SEPARATE research store, absent off-box. BOX-VERIFIED 2026-07-27 (W6, read-only): the "
            "page renders 40 symbol rows × 8 quarters (2025-08→2026-07) with zero empty-state "
            "markers, and cells cross-check EXACTLY against research.db.shareholding_history "
            "(89,943 rows / 1,967 symbols / 2019-06→2026-07) — e.g. AARTIDRUGS 2026-03 promoters "
            "55.03 · FII 1.57 · DII 10.22 renders 55.0 / 1.6 / 10.2. "
            "NOT carried: the QoQ delta board and its 7 tiles"),
    "launchpad": ("PORTED", "/dash/home/strategies/launchpad",
                  "the setup screen with the 'validated screen, no fundable edge net of cost' "
                  "verdict above it. Reads the nightly snapshot only — never the live market-wide "
                  "scan. NOT carried: the regime banner and — CORRECTED 2026-07-28 (register §6h) — "
                  "ALL FOUR count tiles, not just the genuine-buyer one (Fresh triggers · ⭐ With "
                  "genuine buyer · Precursor universe · Coiled). Disposition unchanged: the regime "
                  "banner is the only MAJOR row and it was already recorded"),
    "launchpad-track": ("PORTED", "/dash/home/strategies/launchpad?tab=evidence",
                        "MERGED into `launchpad` as its evidence tab (it IS the screen's evidence): "
                        "the ignition_outcomes study — signals studied, hit rate, median 12m, median "
                        "dip, per-setup cohorts, the outcome histogram and the recovery ladder, "
                        "under its own gross-of-cost + survivorship warning. NOT carried: the "
                        "click-through winners/losers drill"),
    # ── W4 / M8 — the screener workspace (5 surfaces), lane `lane/w4-screener` 2026-07-27 ──
    # Verdicts are per-CAPABILITY, not per-page: the rebuild had to CARRY every job the classic
    # pages did, which is why two of the five are honestly retired rather than re-rendered.
    "screen2": ("DEFERRED", "M8",
                "LANDED at /dash/home/screen as the migrated Screen+ — scope "
                "chips + sector picker, the 0-6 confluence lead column with its pillar dots, the "
                "self-scaling 30th-percentile turnover liquidity gate, the reclaim/slip descriptive "
                "cuts, column-family toggles, saved screens and CSV. Three recorded debts fixed in "
                "the rebuild: the ~2.3 MB single-document render became server-side pagination over "
                "a fixed-size internally-scrolling frozen-pane grid; the client-side CSV blob became "
                "a server ?format=csv export that honours the active filter/sort/column state; and "
                "the localStorage-only column/sort/filter state became URL state, so a screen is now "
                "a shareable link (saved screens = bookmarks, no per-browser silo). CORRECTED + "
                "RE-OPENED 2026-07-28 (register §7a, 2 MAJOR): 'Every capability carried' was not "
                "true — the FIVE inline instrument micro-visualisations that are the page's declared "
                "identity (DVPT-vs-power ladder · accum/distrib signed bar · RS spark · multi-TF RS "
                "heat strip · character triglyph) are absent, the table emits text cells and pillar "
                "dots only, and the Pat bridge ('Ask Pat: confluence here' + '★ Save as Pat board' "
                "+ the scope->NL-query mapper) did not travel. The ~15 §J fundamentals columns stay "
                "a RATIFIED EXCLUSION (Guardrail #8), not a gap"),
    "themes":  ("DEFERRED", "M8",
                "LANDED at /dash/home/themes as the non-ticker discovery door: the multi-label "
                "company_tags layer, grouped in the canonical vocabulary order with approved-only "
                "counts and index-seeded provenance shown, plus a per-theme participants view. New "
                "connection the classic page lacked: a theme hands off directly into the screener "
                "(/dash/home/screen?scope=theme:<tag>), so discovery and screening are one flow. "
                "RE-OPENED by the 2026-07-28 gap audit (register §7b, 1 MAJOR): the theme-detail "
                "participants table drops 6 of 11 columns (Themes chips · Trigger rank · p-score · "
                "%52wH · DVPT ₹cr · Δhot)"),
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
    # ── W5 / M6 — the Trust workspace (11 surfaces), ported into the Graphite identity ──
    # 8 Graphite pages carry 9 of the 11; `pat` is carried by the extended floating dock rather
    # than a page (there is deliberately no third Pat); `inbox` is structurally NA.
    "coverage":     ("DEFERRED", "M6",
                     "LANDED at /dash/home/proof — leads with the published boundary ('what we do "
                     "NOT claim'), then the same provenance.coverage_snapshot funnel + "
                     "per-data-class matrix. RE-OPENED by the 2026-07-28 gap audit (register §8a, "
                     "3 MAJOR): the print-ready /dash/coverage/memo (the dated, sourced Coverage & "
                     "Provenance Memo with its SEBI record-keeping footer) has no twin, EIGHT "
                     "sections did not travel (universe & survivorship · CCI settlement crosstab · "
                     "modeled-vs-filed · provenance receipts · methodology · degradation · "
                     "principles & limits · strategy validation), and the provenance registry table "
                     "is reduced to a single count tile"),
    "testing":      ("PORTED", "/dash/home/validation",
                     "the validation record — the same research.db strategy_registry/runs/holdings "
                     "verdict table, plus the ledger's BLOCKING rows verbatim beside it"),
    "glossary":     ("PORTED", "/dash/home/glossary",
                     "261 terms / 39 families rendered from the SAME docs/metrics-glossary.md parse "
                     "(src.web.glossary) that feeds the ? popovers and Pat — never a second copy"),
    "strategy-ref": ("DEFERRED", "M6",
                     "LANDED at /dash/home/strategy-ref: the same docs/strategies/ pages, list "
                     "DERIVED from the directory (so a new strategy page appears the day it lands) "
                     "through a widened public sanitizer. RE-OPENED by the 2026-07-28 gap audit "
                     "(register §8d, 1 MAJOR): the SURFACE HAND-OFF STRIP — 'Open the live surface "
                     "this page describes →' on 13 of 16 pages, a ratified 2026-07-15 requirement — "
                     "has no twin; the port renders the markdown only, and doc-relative cross-links "
                     "are no longer rewritten to served hrefs"),
    "reading-guide": ("DEFERRED", "M6",
                      "LANDED at /dash/home/guide — 'How to read this site', the newcomer exit and "
                      "the standing destination of the M6 persistent help control; carries the "
                      "five-step arc as structure. RE-OPENED by the 2026-07-28 gap audit (register "
                      "§8e, 2 MAJOR): the page carries NO CHARTS — the live 22-year breadth "
                      "heat-ribbon WORKED EXAMPLE read in four numbered steps, and the 'six shapes' "
                      "card gallery (six real charts, each with what-it-is / how-to-read / an "
                      "'on: <page>' deep-link), are the two things a reading guide exists to be"),
    "spec-sheets":  ("PORTED", "/dash/home/prereg",
                     "the same 9 pre-registered studies with hypothesis, gate-written-first, result "
                     "and the registered SHA-256, read from the one content source"),
    "rule-lab":     ("DEFERRED", "M6",
                     "LANDED at /dash/home/rule-lab over the same closed-vocabulary rule engine "
                     "(src.automation.rule_lab); every verdict state round-trips through the SAME "
                     "query params as the classic page, so a shared URL reproduces the rule on "
                     "either surface (ratified §K.4). RE-OPENED by the 2026-07-28 gap audit "
                     "(register §8g, 2 MAJOR): the params round-trip but the ARTIFACT does not — "
                     "the VERDICT CARD (verdict + qualifier + the 9-row numbers table + the prereg "
                     "SHA-256 chip + the refusal reason) renders pre-run ledger citations only, "
                     "real numbers appearing solely in the synthetic demo, and the roster/current-"
                     "cohort block is absent"),
    "replay-any-date": ("DEFERRED", "M6",
                        "LANDED at /dash/home/replay over the same in-process /v1 point-in-time "
                        "calls (credibility · attention · universe) with the envelopes verbatim; "
                        "also ships journey.replay_card for the Today page. RE-OPENED by the "
                        "2026-07-28 gap audit (register §8h, 1 MAJOR): the CURL LINE under every "
                        "panel — the 'reproduce this yourself' affordance the page's whole thesis "
                        "rests on — is nowhere in the file; ?symbol= was also renamed ?sym=, so "
                        "classic deep links do not carry across"),
    "evidence-pack": ("DEFERRED", "M6",
                      "LANDED at /dash/home/validation?pack=1, MERGED into the validation record — "
                      "the classic page was an ASSEMBLY of spec-sheets + coverage material with two "
                      "self-originating claims (a verify-routes index and the replay narrative), "
                      "both of which the merged view keeps. RE-OPENED by the 2026-07-28 gap audit "
                      "(register §8i, 1 MAJOR): 'zero evidence lost' skipped the ARTIFACT — the "
                      "pack is a procurement deliverable and the print / save-as-PDF button and its "
                      "print stylesheet did not travel, so it is now just a long page; the "
                      "generated-at stamp, scope line and tamper-evidence paragraph are gone too"),
    "pat":          ("DEFERRED", "M6",
                     "LANDED at /dash/home on the EXISTING Graphite floating dock (a dock, not a "
                     "page — there is deliberately no third Pat), extended with the classic "
                     "page's resolution (glossary + lens-registry auto-fold + symbol deep-link, "
                     "model-free) via GET /dash/home/pat/ask. Not "
                     "yet carried: threads, saved boards, the feedback loop. RE-OPENED by the "
                     "2026-07-28 gap audit (register §8j, 4 MAJOR): the open-items list missed the "
                     "biggest one — the ~15 GUIDED FLOWS (accumulation · rs · rslag · fundamentals · "
                     "movers · index · distribution · consolidation · pt14 · redflags · confluence · "
                     "credibility · deterioration · trend · oscillators · strategy · why) and their "
                     "chip-parameter drill have no flow router in pat_dock.resolve()"),
    "inbox":        ("NA", "",
                     "owner review workflow, not a visitor surface: an approve/reject decision "
                     "queue (POST /dash/inbox/decide) whose anonymous view is already reduced to "
                     "aggregate counts. It belongs to ops, so the visitor-facing rebuild has no "
                     "counterpart; the classic route stays live for the owner."),
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
