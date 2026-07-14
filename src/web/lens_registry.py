"""
lens_registry.py — the SINGLE SOURCE OF TRUTH for the analytical lenses (NEW, Lane N1).

Why this module exists
----------------------
The nav, the dossier tabs, the screener column-groups and the cross-page links were
hand-maintained in ~4 separate places (`v2_surfaces._IA_SUB`, `dashboard._SUBNAV`, the
dossier tab bar, the screener columns). Nothing forced them to agree, so the structure
drifted: RS/Leaders got misfiled under Strategies, Wolfe was doubled, the per-stock
dossier highlighted the wrong altitude. (See docs/navigation-and-structure-review.md §6–§7
and docs/ui-architecture-v2.md §0.4 / §9.)

This registry registers each lens ONCE. The nav (v2_surfaces), the highlight map, the
dossier tabs, the screener columns and every cross-link GENERATE from these records, so
they can no longer drift. The decided IA (docs/nav-ia-DECISIONS-and-prompts.md §1, the
Scope × Lens pass Ramana approved on 2026-06-29) is the data below.

Record shape (spec §2)
----------------------
    Lens(
        key,          # stable id, also the route `active` value where one exists
        label,        # human label as it appears in nav / tabs
        scope,        # market | screen | stock | trust  (the SCOPE axis)
        altitude,     # markets | screener | strategies | tracker | trust  (top-bar home)
        route,        # canonical market-wide route (or None for overlay-only)
        dossier_tab,  # the /dash/stock?...#<tab> anchor, or None if no dossier tab
        screener_col, # screener column-group id, or None
        overlay,      # chart-overlay id, or None
        group,        # optional sub-nav grouping heading (e.g. "Accumulation"), or None
        aliases,      # extra route `active` values that should highlight this lens
    )

Descriptive-only. Additive + reversible. This module imports nothing from the web layer
so it is safe for any consumer (v2_surfaces nav, Lane N3 cross-link helpers) to import.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lens:
    key: str
    label: str
    scope: str                       # market | screen | stock | trust
    altitude: str                    # markets | screener | strategies | tracker | trust
    route: str | None = None
    dossier_tab: str | None = None
    screener_col: str | None = None
    overlay: str | None = None
    group: str | None = None
    aliases: tuple[str, ...] = field(default_factory=tuple)


# ── the registry — one record per lens, in nav order within each altitude ────────
# Ordered the way the sub-nav should read. The decided IA (§1):
#   Markets    : Overview · Sectors · Relative Strength · Rotation·{Map,Weather,Band} ·
#                Participants · Wire · Compare   (Leaders/"Strength" MOVED here)
#   Screener   : Screen+ · Screen (classic) · Themes · Review · Workbench  (Screen+ default)
#   Strategies : Strategist · Conviction · Accumulation{Positioning,MEP} · Structure ·
#                Credibility · Growth · Launchpad   (Hub MERGED into Strategist;
#                Positioning+MEP GROUPED under "Accumulation"; Wolfe → overlay)
#   Tracker    : Dashboard · Portfolios · Watchlists · Performance · Import
#   Trust      : Coverage · Strategy validation (/dash/testing)
LENSES: tuple[Lens, ...] = (
    # ── Markets ──────────────────────────────────────────────────────────────
    Lens("markets", "Overview", "market", "markets", "/dash/markets"),
    # Attention queue (D106, S103) — the signal-event bus's human face: every lens's
    # typed state-changes in one magnitude-ranked, PIT-replayable tape (bus = D105).
    Lens("attention", "Attention", "market", "markets", "/dash/attention",
         group="Big picture", aliases=("bus", "events", "signal-events", "queue", "attention-queue")),
    # Market Internals (deep-data sprint) — the ABSOLUTE market-health surface back to 2004:
    # price-breadth (adv/dec) + the tape (MEP accum/distrib effort-breadth) + delivery regime +
    # dispersion + coil. Reads the bounded market_internals_daily snapshot. The hero is the
    # price-breadth vs effort-breadth divergence. Descriptive market-state — not a signal.
    Lens("market-internals", "Market internals", "market", "markets", "/dash/market-internals",
         group="Big picture", aliases=("internals", "breadth", "market-health", "advance-decline")),
    # Move anatomy (deep-data sprint) — the features event panel as a descriptive fingerprint:
    # what precedes a big move (momentum/RS elevated, delivery SUPPRESSED) + the MFE/MAE envelope.
    # Aggregate, leak-safe, post-selection base-rate — descriptive market-wide insight, NOT a signal.
    # HOMED IN MARKETS (D115): it's a market-wide analytical insight, sibling to Market internals &
    # Sector economics — belongs where analysts look, not buried in the Trust/methodology corner.
    # (Still cross-linked from the Coverage/Trust evidence index via coverage_view.)
    Lens("move-anatomy", "Move anatomy", "market", "markets", "/dash/move-anatomy",
         group="Big picture", aliases=("anatomy", "fingerprint", "what-precedes-a-move")),
    # Seasonal tape (P0/P1) — 25y calendar seasonality of PIT idiosyncratic residuals,
    # certification-gated (placebo nulls + FDR + N>=15 + OOS sign + pledged mechanism).
    # Descriptive-only, never a signal.
    Lens("seasonal-tape", "Seasonal tape", "market", "markets", "/dash/seasonal-tape",
         group="Big picture", aliases=("seasonality", "calendar", "season", "seasonal")),
    # This-month screen (FIX-1: a per-entity LOOKUP of descriptive month base-rates, NOT a
    # ranked leaderboard — default order is alphabetical, no default lean filter).
    Lens("seasonal-screen", "This-month screen", "market", "markets", "/dash/seasonal-screen",
         group="Big picture", aliases=("month-screen", "seasonal-scan", "bullish-this-month", "bearish-this-month")),
    # Index divergence — do two indices move together on the calendar, and where do they
    # diverge? Descriptive co-movement history, never a signal.
    Lens("seasonal-divergence", "Index divergence", "market", "markets", "/dash/seasonal-divergence",
         group="Big picture", aliases=("index-overlap", "co-movement", "nifty200-vs-nifty50")),
    # Corporate-actions calendar — forward ex-dates, day by day (D94 #5, S91).
    Lens("actions", "Corp actions", "market", "markets", "/dash/actions",
         group="Events & flow", aliases=("corp-actions", "ex-dates", "dividends", "corporate-actions")),
    # Event cadence (D128) — the ADDITIVE cut vs the two announced calendars above: which LIVE names
    # are OVERDUE vs their OWN rhythm + what each is next EXPECTED by cadence (from seasonal_events).
    Lens("event-cadence", "Event cadence", "market", "markets", "/dash/event-cadence",
         group="Events & flow", aliases=("overdue", "overdue-events", "cadence", "event-timing",
                                         "expected-results", "due-events")),
    # E-10 buyback tender-quota calculator (S85g) — the personal-scale capacity-moat tool
    # (charter §2.4); companion to the corp-actions calendar it sits beside.
    Lens("buyback-calc", "Buyback calc", "market", "markets", "/dash/buyback-calc",
         group="Events & flow", aliases=("buyback", "tender", "buybacks")),
    # Surveillance transitions — ASM/GSM/band restriction moves (D94 #6, S92).
    # Band-lock streaks (charter X-05, S96c) — names pinned at their daily band;
    # flag logic single-sourced in band_lock.flagged_symbols.
    Lens("band-locks", "Band locks", "market", "markets", "/dash/band-locks",
         group="Events & flow", aliases=("bandlock", "circuit", "locks")),
    Lens("surveillance", "Surveillance", "market", "markets", "/dash/surveillance",
         group="Events & flow", aliases=("asm", "gsm", "price-bands", "surveillance-transitions")),
    Lens("sectors", "Sectors", "market", "markets", "/dash/sectors",
         dossier_tab=None, group="Sectors", aliases=("rs",)),
    # Sector economics (deep-data sprint) — median ROCE/OPM by sector × year over a decade;
    # the FUNDAMENTAL complement to the RS-based Sectors lens above — kept ADJACENT to it (D117,
    # Ramana) rather than in the front "Big picture" cluster. Aggregate, descriptive.
    Lens("sector-economics", "Sector economics", "market", "markets", "/dash/sector-economics",
         group="Sectors", aliases=("sector-fundamentals", "sector-quality", "sector-econ")),
    Lens("rs-hub", "Relative strength", "market", "markets", "/dash/rs-hub",
         dossier_tab="rs", screener_col="rs", group="Strength & momentum"),
    # Leaders/"Strength" — MOVED to Markets (§0.1, divergence #1). RS is Markets content.
    # Leaders sits directly after the RS hub (it IS RS content) — no separate heading,
    # the "Relative strength" item above already names the section.
    Lens("leaders", "Leaders / Laggards", "market", "markets", "/dash/leaders",
         dossier_tab="rs", screener_col="rs", group="Strength & momentum", aliases=("laggards",)),
    # Risk-adjusted momentum SCANNER — candidate shortlister with the C/A/B veto inline
    # (gross selection lens, not alpha). RS/momentum content → Markets, beside Leaders.
    Lens("momentum-scan", "Risk-adj momentum", "market", "markets", "/dash/momentum-scan",
         group="Strength & momentum", aliases=("momo", "riskadj")),
    # All-weather capture map (flagship C) — up/down-capture scatter vs the benchmark;
    # behaviour track record (descriptive), sits with the RS-strength cluster.
    Lens("capture-map", "All-weather map", "market", "markets", "/dash/capture-map",
         group="Strength & momentum", aliases=("capture", "all-weather")),
    # Results-Reaction SCANNER (S80f) -- the war-room board: forward NSE results calendar +
    # delivery-confirmed reaction cells. Descriptive (the failed PEAD book is cited on-page);
    # reads the nightly results_reactions snapshot + board_meetings. A Markets scanner lens.
    Lens("results-reactions", "Results reactions", "market", "markets", "/dash/results-reactions",
         group="Events & flow", aliases=("results", "earnings", "war-room")),
    Lens("rrg", "Rotation · Map", "market", "markets", "/dash/rrg",
         group="Rotation"),
    Lens("rotation", "Rotation · Weather", "market", "markets", "/dash/rotation",
         group="Rotation"),
    Lens("rsband", "Rotation · Band", "market", "markets", "/dash/rsband",
         group="Rotation"),
    Lens("cycle-clock", "Rotation · Clock", "market", "markets", "/dash/cycle-clock",
         group="Rotation"),
    # Momentum — RSI-of-RS divergence early-warning board (roadmap Phase 1). Market-wide
    # destination; the per-stock momentum pane lives on the dossier (not a nav item).
    Lens("divergence", "Divergence", "market", "markets", "/dash/divergence",
         group="Strength & momentum"),
    # Momentum drill surfaces (modules shipped bb27a4e/10959ba; the mounts + this lens
    # lived only as an uncommitted VPS patch — AUD-32: a clean deploy 404'd both).
    # early-signals matches the live patch VERBATIM; sector-momentum is NEW even on the
    # VPS (it was mount-only — reachable solely via cycle-clock deep-links = an orphan).
    Lens("early-signals", "Early signals", "market", "markets", "/dash/early-signals",
         group="Strength & momentum"),
    Lens("sector-momentum", "Sector drill", "market", "markets", "/dash/sector-momentum",
         group="Sectors", aliases=("sector-rsi",)),
    # Pattern SCANNERS (Ramana 2026-07-02): keep Wolfe/Harmonic as chart OVERLAYS (the
    # route=None records below, reached from the chart control) AND surface the market-wide
    # SCANNER pages as Markets lenses under a "Patterns" heading. Scans are precomputed
    # nightly (harmonic_signals / wolfe_signals) → nav-only wiring, zero added compute.
    # aliases carry the scanner pages' emitted active id ("harmonic"/"wolfe" — the overlay keys)
    # so /dash/harmonic and /dash/wolfe/scan highlight their "Patterns" sub-nav lens (D118).
    Lens("harmonic-scan", "Patterns · Harmonic", "market", "markets", "/dash/harmonic",
         group="Patterns", aliases=("harmonic",)),
    # Wolfe = ONE Patterns lens with a Fresh setups ⇄ Open trades toggle (Ramana 2026-07-13).
    # The scanner (fresh winner-profile) + the open-trades remaining-ROI view live under this
    # single tab; the /dash/wolfe/trades open view emits active="wolfe" too (highlights this
    # lens) and is reached via the on-page toggle, NOT its own nav entry.
    Lens("wolfe-scan", "Patterns · Wolfe", "market", "markets", "/dash/wolfe/scan",
         group="Patterns", aliases=("wolfe",)),
    Lens("participants", "Participants", "market", "markets", "/dash/participants",
         dossier_tab="fno", screener_col=None, group="Events & flow"),
    Lens("wire", "News / Wire", "market", "markets", "/dash/wire",
         group="Events & flow", aliases=("news",)),
    Lens("compare", "Compare", "market", "markets", "/dash/compare"),

    # ── Screener ─────────────────────────────────────────────────────────────
    # Screen+ is the de-facto default (ordered FIRST → the landing click under the
    # Screener altitude); the legacy wide screener is kept + reachable as "Screen
    # (classic)". ADDITIVE — both routes live; the sacred /dash/screener is untouched.
    Lens("screen2", "Screen+", "screen", "screener", "/dash/screen2"),
    Lens("screener", "Screen (classic)", "screen", "screener", "/dash/screener"),
    Lens("themes", "Themes / Baskets", "screen", "screener", "/dash/themes",
         aliases=("theme",)),
    Lens("tags-review", "Review", "screen", "screener", "/dash/tags-review"),
    Lens("workbench", "Workbench", "screen", "screener", "/dash/workbench"),

    # ── Strategies (stock-selection lenses ONLY) ─────────────────────────────
    # Strategist is the single landing — Hub MERGES into it (one landing, §1).
    Lens("strategist", "Strategist", "stock", "strategies", "/dash/strategist",
         aliases=("strategies",)),
    Lens("conviction", "Conviction", "stock", "strategies", "/dash/conviction",
         dossier_tab="verdict", group="Conviction & structure"),
    # Positioning + MEP GROUP under one "Accumulation" heading (two views, both kept).
    Lens("stocks", "Stocks", "stock", "strategies", "/dash/stocks",
         dossier_tab="pos", screener_col="pos", overlay="dvpt",
         group="Accumulation", aliases=("scan", "positioning")),
    # Stealth accumulation — a DISTINCT population (accumulation character + A+ pressure
    # + low churn + >=10% off the 52w-high), so it earns its OWN nested link (D80) rather
    # than the old /dash/stocks?view=stealth query-param orphan. Sibling under the same
    # "Accumulation" group; nests to /dash/strategies/stealth. Served by dash_stealth,
    # which reuses the dash_stocks view=='stealth' render (no query duplication). The old
    # ?view=stealth URL still serves + also highlights Stealth (active derived from view).
    Lens("stealth", "Stealth", "stock", "strategies", "/dash/stealth",
         dossier_tab="pos", screener_col="pos", overlay="dvpt",
         group="Accumulation", aliases=("stealth-accumulation",)),
    Lens("mep", "Accum / Distrib", "stock", "strategies", "/dash/mep",
         dossier_tab="mep", screener_col="mep", overlay="mep",
         group="Accumulation"),
    Lens("cpr", "Structure", "stock", "strategies", "/dash/cpr",
         dossier_tab="cpr", screener_col="cpr", overlay="cpr", group="Conviction & structure"),
    Lens("concalls", "Credibility", "stock", "strategies", "/dash/concalls",
         dossier_tab="cci", screener_col="cci", group="Fundamentals"),
    Lens("growth", "Growth", "stock", "strategies", "/dash/growth",
         dossier_tab="qual", screener_col="qual", group="Fundamentals"),
    # Insider activity — SEBI PIT disclosures classified (conviction / caution /
    # pledge / plumbing); the D94 unsurfaced-data queue #1 (S86). Descriptive.
    Lens("insider", "Insider", "stock", "strategies", "/dash/insider",
         group="Ownership & filings", aliases=("insider-activity", "promoter-buying", "pit-disclosures")),
    # Credit-rating transitions — deduped company-level agency actions (D94 #2, S87).
    Lens("ratings", "Ratings", "stock", "strategies", "/dash/ratings",
         group="Ownership & filings", aliases=("credit-ratings", "rating-transitions", "upgrades-downgrades")),
    # Stake × pledge confluence — SAST Reg-29 × Reg-31/32 crossings (D94 #3, S88).
    Lens("sast", "Stake · Pledge", "stock", "strategies", "/dash/sast",
         group="Ownership & filings", aliases=("stake-pledge", "confluence", "pledge-flow", "substantial-holders")),
    # Holdings QoQ — shareholding-pattern deltas, archive + NSE-XBRL (D94 #4, S90).
    Lens("shp", "Holdings", "stock", "strategies", "/dash/shp",
         group="Ownership & filings", aliases=("shareholding", "holdings-qoq", "fii-dii", "holder-mix")),
    Lens("launchpad", "Launchpad", "stock", "strategies", "/dash/launchpad",
         group="Launchpad"),
    # Launchpad track record (deep-data sprint, orphan rescue) — surfaces ignition_outcomes
    # (50k historical signals, 2019→) as the honest outcome distribution behind the screen:
    # gain-vs-pain by character, first-vs-repeat, the drawdown-recovery ladder. Point-in-time
    # study, gross of costs, ledger-cited (validated screen, no fundable edge net of cost).
    Lens("launchpad-track", "Launchpad · evidence", "stock", "strategies", "/dash/launchpad-track",
         group="Launchpad", aliases=("launchpad-outcomes", "track-record", "ignition-outcomes")),

    # ── Tracker ──────────────────────────────────────────────────────────────
    # Tracker tabs are nested under /dash/tracker/* so the URL mirrors the nav
    # hierarchy (D79). The old flat /dash/<tab> URLs stay alive as 307 redirects
    # (see dashboard.py _tracker_compat) so existing links/bookmarks never break.
    Lens("dashboard", "Dashboard", "stock", "tracker", "/dash/tracker/dashboard",
         aliases=("tracker", "track")),
    Lens("portfolios", "Portfolios", "stock", "tracker", "/dash/tracker/portfolios"),
    Lens("watchlists", "Watchlists", "stock", "tracker", "/dash/tracker/watchlists"),
    Lens("performance", "Performance", "stock", "tracker", "/dash/tracker/performance"),
    Lens("import", "Import", "stock", "tracker", "/dash/tracker/import"),

    # ── Trust (utility) ──────────────────────────────────────────────────────
    Lens("coverage", "Coverage", "trust", "trust", "/dash/coverage"),
    # Lab → Trust, reframed as "Strategy validation" rigor evidence. Lane N2 builds
    # the page content; N1 only wires this nav slot from the registry.
    Lens("testing", "Strategy validation", "trust", "trust", "/dash/testing"),
    # Glossary / Methodology — the browsable "explain every term" reference (primary-intent
    # commitment #2). Same content as the ? hover-popovers; Trust altitude (methodology/help).
    Lens("glossary", "Glossary", "trust", "trust", "/dash/glossary", aliases=("methodology",)),
    Lens("strategy-ref", "Strategy reference", "trust", "trust", "/dash/strategy-ref"),
    # How to read the charts (deep-data sprint) — the VISUAL companion to the Glossary: a
    # beginner's guide to the site's chart shapes + plain-word ideas. Linked from every lens header.
    Lens("reading-guide", "How to read", "trust", "trust", "/dash/reading-guide",
         aliases=("how-to-read", "chart-guide", "reading")),
    # Ask Pat (UX audit S-D) — the NL copilot gets a nav home so it's reachable without
    # typing a sentence (audit §8: "Pat gets a nav entry — Trust group or header"). This
    # AMENDS the earlier "⌘K summon only" IA note in the route gate's exempt table: the
    # ⌘K bar stays the primary summon; this is the discoverable front door beside the
    # other help/education surfaces. Closed-vocab, descriptive-only — Pat never ranks.
    Lens("pat", "Ask Pat", "trust", "trust", "/dash/pat",
         aliases=("copilot", "ask", "assistant", "ask-pat")),
    Lens("spec-sheets", "Spec sheets", "trust", "trust", "/dash/spec-sheets",
         aliases=("pre-registration", "studies")),
    # Evidence pack (charter P-04, S96) — the print-ready procurement assembly of
    # spec-sheets + coverage boundary + season SLA + replay pointer.
    Lens("evidence-pack", "Evidence pack", "trust", "trust", "/dash/evidence-pack",
         aliases=("procurement", "pack")),
    # Replay any date (charter P-05, S102) — the live PIT demo over the entitled /v1 API:
    # any symbol, any date, knowable clock stamped (D104), curl included.
    Lens("replay-any-date", "Replay any date", "trust", "trust", "/dash/replay-any-date",
         aliases=("replay-api", "pit-replay")),

    # ── Overlay-only (NOT nav lenses) — Wolfe / Harmonic. §3-C: chart overlays,
    # reachable from the chart control, no sub-nav entry. Routes stay live (no 404);
    # they carry route=None here so the nav generator skips them, but keep their
    # `active`/overlay ids registered so highlight + cross-links still resolve them.
    # altitude = "markets" so the scanner pages (which render with active="wolfe") highlight
    # the Markets altitude where their "Patterns" lenses live. route=None keeps them OFF every
    # sub-nav (chart-overlay only); overlay_lenses() still returns exactly {wolfe, harmonic}.
    Lens("wolfe", "Wolfe wave", "stock", "markets", route=None,
         overlay="wolfe", aliases=("wolfe_chart",)),
    Lens("harmonic", "Harmonic", "stock", "markets", route=None,
         overlay="harmonic"),
)


# ── derived indexes (built once at import; cheap, read-only) ─────────────────────
BY_KEY: dict[str, Lens] = {ln.key: ln for ln in LENSES}

# Every `active` value (key + aliases) → its altitude. The single highlight map that
# v2_surfaces._ALT_OF used to hand-maintain. A per-stock dossier (active="stock") is
# DELIBERATELY absent here — it is a destination, not a lens, so it must not claim one
# altitude/lens highlight (fixes the stock→stocks alias quirk, review §6 #5).
ALT_OF: dict[str, str] = {}
for _ln in LENSES:
    ALT_OF[_ln.key] = _ln.altitude
    for _al in _ln.aliases:
        ALT_OF[_al] = _ln.altitude
# Standalone destinations / sub-pages that should still highlight an altitude but are
# not themselves lenses: the RS-ratio sub-page and the index detail page sit in Markets.
ALT_OF.setdefault("ratio", "markets")
ALT_OF.setdefault("index", "markets")


def altitude_order() -> tuple[str, ...]:
    """The top-bar altitudes, in order. Trust is a right-side utility, not a tab."""
    return ("markets", "screener", "strategies", "tracker")


def subnav(altitude: str) -> list[Lens]:
    """The sub-nav lenses for an altitude, in registry order, EXCLUDING overlay-only
    lenses (route is None) — Wolfe/Harmonic are chart overlays, not nav entries."""
    return [ln for ln in LENSES if ln.altitude == altitude and ln.route is not None]


def alias_set(key: str) -> set[str]:
    """The set of route `active` values that should highlight the given lens key
    (the key itself + its declared aliases)."""
    ln = BY_KEY.get(key)
    if ln is None:
        return {key}
    return {key, *ln.aliases}


def overlay_lenses() -> list[Lens]:
    """Lenses that are chart overlays only (no nav entry) — kept reachable from the
    chart control, never orphaned (the 'I lost Wolfe' lesson)."""
    return [ln for ln in LENSES if ln.route is None and ln.overlay]


def stock_link(sym: str, lens: str | None = None) -> str:
    """Canonical dossier link that CARRIES the lens as the dossier-tab anchor:
    stock_link("INFY", "mep") -> /dash/stock?sym=INFY#mep. Falls back to the plain
    dossier when the lens has no dossier tab. (Lane N3 builds the richer link rail;
    this minimal helper lives with the registry so any consumer can carry a lens.)"""
    base = f"/dash/stock?sym={sym}"
    if not lens:
        return base
    ln = BY_KEY.get(lens)
    tab = ln.dossier_tab if ln else None
    return f"{base}#{tab}" if tab else base


def _selftest() -> int:
    # The decided altitudes are populated and ordered.
    for alt in altitude_order():
        assert subnav(alt), f"empty altitude: {alt}"
    assert subnav("trust") and all(ln.altitude == "trust" for ln in subnav("trust"))
    assert BY_KEY["glossary"].route == "/dash/glossary"   # browsable glossary lives in Trust
    # Leaders MOVED to Markets; Positioning/MEP stay under Strategies, grouped.
    assert BY_KEY["leaders"].altitude == "markets", "leaders must be Markets content"
    assert BY_KEY["stocks"].altitude == "strategies" and BY_KEY["stocks"].group == "Accumulation"
    assert BY_KEY["stocks"].label == "Stocks", "the DVPT list's label must say 'Stocks' (matches /dash/stocks)"
    assert BY_KEY["mep"].altitude == "strategies" and BY_KEY["mep"].group == "Accumulation"
    # Stealth is a first-class destination (own nested link /dash/strategies/stealth),
    # NOT a query-param orphan — it sits in the Accumulation group beside Stocks + MEP.
    assert BY_KEY["stealth"].altitude == "strategies" and BY_KEY["stealth"].group == "Accumulation"
    assert BY_KEY["stealth"].route == "/dash/stealth"
    assert [ln.key for ln in subnav("strategies") if ln.group == "Accumulation"] == ["stocks", "stealth", "mep"]
    # Hub merged into Strategist (strategies alias points at strategist).
    assert ALT_OF.get("strategies") == "strategies"
    assert "strategies" in BY_KEY["strategist"].aliases
    # Wolfe/Harmonic are overlay-only (no nav route) but still resolvable.
    assert BY_KEY["wolfe"].route is None and BY_KEY["wolfe"].overlay == "wolfe"
    assert {ln.key for ln in overlay_lenses()} == {"wolfe", "harmonic"}
    # The per-stock dossier must NOT claim an altitude (the highlight-quirk fix).
    assert "stock" not in ALT_OF, "stock dossier must not claim a lens/altitude"
    # Trust slot wired for /dash/testing (Lane N2 builds the page).
    assert BY_KEY["testing"].route == "/dash/testing" and BY_KEY["testing"].label == "Strategy validation"
    # Screen+ is the de-facto default: it LEADS the Screener altitude; the legacy wide
    # screener is kept + reachable, relabelled "Screen (classic)". Both routes live.
    _scr = subnav("screener")
    assert _scr[0].key == "screen2", "Screen+ must be the first/landing Screener lens"
    assert BY_KEY["screener"].label == "Screen (classic)" and BY_KEY["screener"].route == "/dash/screener"
    assert {ln.key for ln in _scr} >= {"screen2", "screener"}, "both screeners stay reachable"
    # Lens-carrying link helper.
    assert stock_link("INFY", "mep") == "/dash/stock?sym=INFY#mep"
    assert stock_link("INFY") == "/dash/stock?sym=INFY"
    assert stock_link("INFY", "launchpad") == "/dash/stock?sym=INFY"  # no dossier tab
    print("lens_registry selftest OK - %d lenses; Leaders->Markets; Accumulation group; "
          "Wolfe/Harmonic overlay-only; stock dossier claims no altitude" % len(LENSES))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
