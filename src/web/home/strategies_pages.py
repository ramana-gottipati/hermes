"""src/web/home/strategies_pages.py — the Graphite **Strategies workspace** (milestone M7, lane W3-A).

Ports the classic Strategies estate (18 routed lenses) into the Graphite identity as ONE workspace
with a hub + ten sub-pages, per the ratified consolidations in `docs/redesign-plan-2026-07-17.md`
§1c and Part III §J:

    strategist                      -> /dash/home/strategies                 (the hub)
    model-portfolios                -> /dash/home/strategies/books           (?book=)
    sector-rotation                 -> /dash/home/strategies/sector-rotation
    factor-league + classics        -> /dash/home/strategies/library         (?origin= ?s=)
    stocks + stealth                -> /dash/home/strategies/positioning     (?view=stealth)
    conviction                      -> /dash/home/strategies/conviction
    mep                             -> /dash/home/strategies/mep             (?dir=)
    concalls (+ credibility)        -> /dash/home/strategies/credibility     (?sym=)
    growth                          -> /dash/home/strategies/growth          (?type=)
    insider+ratings+sast+shp        -> /dash/home/strategies/ownership       (?lens=)
    launchpad + launchpad-track     -> /dash/home/strategies/launchpad       (?tab=evidence)
    cpr                             -> DEMOTED (structure lives on the stock chart, not primary nav)

Mount + nav discipline: an own `APIRouter`, mounted by ONE additive `v2_surfaces._ROUTER_SPECS`
tuple beside the graphite-home entry. Every route is a **declared child** registered in
`tests/test_dash_route_registry.INTERNAL_DEV` — deliberately NO `lens_registry` entry, because nav
is generated from the registry and adding one would drift the classic nav. Registering these as
lenses IS the cutover (W6), and is not this lane's job.

Isolation: imports only `src.web.home.*` plus ENGINE modules through `strategies_reads`. No classic
or preview view module is imported anywhere in the package (tests/test_home_isolation.py).

Every handler is defensive by construction: a cold DB, a missing table or a slow engine degrades to
the page's honest-empty branch rather than a 500.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import shell
from src.web.home import strategies_blocks as B
from src.web.home import strategies_reads as R

router = APIRouter()

_BASE = "/dash/home/strategies"


def _conn():
    from src.core.db import get_conn
    return get_conn()


def _render(title: str, body: str, conn=None) -> HTMLResponse:
    """Wrap a workspace body in the Graphite shell, with the floating Pat when a conn is available."""
    pat = ""
    if conn is not None:
        try:
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
        except Exception:  # noqa: BLE001 — Pat is an enhancement, never a dependency
            pat = ""
    return HTMLResponse(shell.shell(title, body, extra_head=B.css(), current="Strategies",
                                    pat_html=pat))


# A machine-detectable marker on the degraded branch. Without it a raised exception renders a
# plausible "not landed yet" page and a status-200 smoke test passes over a real bug — which is
# exactly how a shadowed helper name survived one round of this build.
_DEGRADED = "<!--g-degraded-->"


def _fail(title: str, what: str) -> HTMLResponse:
    return _render(title, _DEGRADED + B.crumb(title) + C.fence(what + " hasn't landed yet.")
                   + C.empty("Check back after the next nightly run."))


def _q(request: Request, key: str, default: str = "") -> str:
    v = request.query_params.get(key, default)
    return "" if v is None else str(v)[:48]


# ── the hub ────────────────────────────────────────────────────────────────────


@router.get(_BASE, response_class=HTMLResponse, include_in_schema=False)
def strategies_hub(request: Request) -> HTMLResponse:
    """The Strategies landing page — the port of `/dash/strategist`. Shows the honest headline
    (one fundable result in the whole estate) ABOVE the catalogue, the per-strategy health cards
    from the canonical registry, and a directory of every sub-page."""
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            cat = R.catalog(conn)
            asof = R.universe_asof(conn)
            return _render("Strategies", B.hub(cat, asof, sample=not cat), conn)
    except Exception:  # noqa: BLE001
        return _fail("Strategies", "The strategy registry")


# ── model portfolios ───────────────────────────────────────────────────────────


@router.get(_BASE + "/books", response_class=HTMLResponse, include_in_schema=False)
def strategies_books(request: Request) -> HTMLResponse:
    """The four engine-locked books. STEADY-25 carries the FUNDABLE-CORE banner (the estate's only
    result that survives realistic cost); the other three carry the GROSS-LENS warning. Every
    ratio here is labelled a RETURN / VOLATILITY ratio, not a Sharpe (no risk-free rate is subtracted)."""
    specs = R.book_specs()
    names = [s["book"] for s in specs]
    book = _q(request, "book") or names[0]
    if book not in names:
        book = names[0]
    spec = next(s for s in specs if s["book"] == book)
    try:
        since = int(_q(request, "since") or 0)
    except ValueError:
        since = 0
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            nav, nav_demo = R.pick(R.book_nav(conn, book, since), R.DEMO_BOOK_NAV)
            holds_live, hold_date = R.book_holdings(conn, book)
            holds, hold_demo = R.pick(holds_live, R.DEMO_HOLDINGS)
            churn = R.book_churn(conn, book)
            stats = R.series_stats(nav)
            sample = nav_demo or hold_demo
            return _render(book, B.books(spec, stats, nav, holds, churn, book, specs,
                                         sample=sample, hold_date=hold_date), conn)
    except Exception:  # noqa: BLE001
        return _fail("Model portfolios", "The model-portfolio books")


# ── sector rotation ────────────────────────────────────────────────────────────


@router.get(_BASE + "/sector-rotation", response_class=HTMLResponse, include_in_schema=False)
def strategies_sector_rotation(request: Request) -> HTMLResponse:
    """The V21 sector-index book. 🔴 The D138 scope gap ('picks SECTORS, not STOCKS') and the D141
    rejection of the two-step sector→stock extension render ABOVE the headline stat — recorded
    verdicts, never footnotes."""
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            live = R.rotation_book(conn, _q(request, "asof"))
            book, sample = R.pick(live if live.get("weights") else None, R.DEMO_ROTATION)
            diff = R.rotation_diff(book.get("weights") or [], book.get("prev") or [])
            stats = R.series_stats(book.get("nav") or [], "nav", "nav_bench")
            return _render("Sector rotation", B.rotation(book, diff, stats, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Sector rotation", "The sector-rotation book")


# ── strategy library (factor-league + classics, merged) ────────────────────────


@router.get(_BASE + "/library", response_class=HTMLResponse, include_in_schema=False)
def strategies_library(request: Request) -> HTMLResponse:
    """ONE library for what used to be two sibling pages, filtered by the binding origin taxonomy
    (🧑 Ramana / 🏠 house / 📚 classic — docs/strategies/origins.md). Measured verdict numbers are
    LINKED to the validation record and each strategy's reference page, never restated here."""
    origin = _q(request, "origin")
    if origin not in ("", "ramana", "house", "classic"):
        origin = ""
    sel = _q(request, "s")
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = R.library(conn, origin)
            classics = R.classic_screens(conn)
            body = B.library(rows, origin, classics, sample=not classics)
            if sel:
                froster, fam = R.factor_roster(conn, sel)
                if fam:
                    label = next((x["label"] for x in R.library(conn) if x["key"] == sel), sel)
                    body += B.classic_detail(sel, label + " — live roster", froster, [],
                                             sample=not froster, show_nav=False,
                                             prov="factor_league")
                else:
                    roster = R.classic_roster(conn, sel)
                    label = next((c.get("label") for c in classics if c.get("key") == sel), sel)
                    body += B.classic_detail(sel, label, roster, R.classic_nav(conn, sel),
                                             sample=not roster)
            return _render("Strategy library", body, conn)
    except Exception:  # noqa: BLE001
        return _fail("Strategy library", "The strategy library")


# ── positioning + stealth (one renderer, one toggle) ───────────────────────────


@router.get(_BASE + "/positioning", response_class=HTMLResponse, include_in_schema=False)
def strategies_positioning(request: Request) -> HTMLResponse:
    """The DVPT positioning board with Stealth as a toggle — the classic site already admitted the
    two were one renderer (`/dash/stealth` delegated to `view=='stealth'`), so this merge carries a
    registry fact, not a judgement."""
    stealth = _q(request, "view") == "stealth"
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            live, asof = R.positioning(conn, stealth=stealth)
            rows, sample = R.pick(live, R.DEMO_POSITIONING)
            return _render("Stealth" if stealth else "Positioning",
                           B.positioning(rows, stealth, asof, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Positioning", "The positioning tape")


# ── conviction ─────────────────────────────────────────────────────────────────


@router.get(_BASE + "/conviction", response_class=HTMLResponse, include_in_schema=False)
def strategies_conviction(request: Request) -> HTMLResponse:
    """The cross-pillar shortlist. The 'sorting heuristic, not a validated model' chip renders above
    the table, and the Quality column carries the Screener-archive provenance disclosure."""
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = R.conviction(limit=60)
            return _render("Conviction", B.conviction(rows, sample=not rows), conn)
    except Exception:  # noqa: BLE001
        return _fail("Conviction", "The conviction shortlist")


# ── MEP ────────────────────────────────────────────────────────────────────────


@router.get(_BASE + "/mep", response_class=HTMLResponse, include_in_schema=False)
def strategies_mep(request: Request) -> HTMLResponse:
    """Accumulation / distribution. D62 stands: descriptor-only, never a ranker — the fence is the
    first thing on the page."""
    d = _q(request, "dir")
    if d not in ("", "up", "dn"):
        d = ""
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            live, counts, asof = R.mep_board(conn)
            rows, sample = R.pick(live, R.DEMO_MEP)
            return _render("Accumulation & distribution",
                           B.mep(rows, counts, asof, d, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Accumulation & distribution", "The accumulation tape")


# ── credibility (absorbs the per-symbol fingerprint) ───────────────────────────


@router.get(_BASE + "/credibility", response_class=HTMLResponse, include_in_schema=False)
def strategies_credibility(request: Request) -> HTMLResponse:
    """Management credibility (CCI) + the absorbed `/dash/credibility` fingerprint as `?sym=`.
    🔴 Gate B failed leak-free: descriptive-only, NEVER ranked — the board is ordered by how much
    evidence a name has, not by score."""
    sym = "".join(ch for ch in _q(request, "sym").upper() if ch.isalnum() or ch in "&-.")[:24]
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            live, counts, asof = R.cci_board(conn)
            rows, sample = R.pick(live, R.DEMO_CCI)
            if sample:
                counts = {"proven": 1, "unproven": 0, "vetoed": 1, "scored": len(rows)}
            fp = R.cci_fingerprint(conn, sym) if sym else []
            return _render("Management credibility",
                           B.credibility(rows, counts, asof, fp, sym, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Management credibility", "The credibility record")


# ── growth intent ──────────────────────────────────────────────────────────────


@router.get(_BASE + "/growth", response_class=HTMLResponse, include_in_schema=False)
def strategies_growth(request: Request) -> HTMLResponse:
    """What management said it will spend and build. The placebo-kill verdict renders above the
    table, and the concall-corpus provenance note (Screener.in discovery, frozen legacy path) is
    disclosed at the foot."""
    stype = _q(request, "type")
    if stype not in [k for k, _ in R.GROWTH_TABS]:
        stype = ""
    try:
        min_cr = float(_q(request, "min_cr") or 0)
    except ValueError:
        min_cr = 0.0
    try:
        since = int(_q(request, "since") or 0)
    except ValueError:
        since = 0
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            live = R.growth(conn, stype, min_cr, since)
            rows, sample = R.pick(live, R.DEMO_GROWTH)
            return _render("Growth intent", B.growth(rows, stype, R.GROWTH_TABS, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Growth intent", "The growth-intent ledger")


# ── ownership & filings (4 lenses, 1 hub) ──────────────────────────────────────


@router.get(_BASE + "/ownership", response_class=HTMLResponse, include_in_schema=False)
def strategies_ownership(request: Request) -> HTMLResponse:
    """Insider dealing · credit ratings · stake & pledge · shareholding — four nav lenses over one
    filings pipeline, merged into one hub with four views (registry anomaly H). Each lens reuses its
    OWN engine's classification, so the hub can never disagree with the classic lens."""
    lens = _q(request, "lens") or "insider"
    if lens not in [k for k, _ in R.OWN_LENSES]:
        lens = "insider"
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            payload, sample = {}, False
            if lens == "ratings":
                tr, tape, asof = R.own_ratings(conn)
                tr2, sample = R.pick(tr, R.DEMO_RATINGS)
                payload = {"transitions": tr2, "tape": tape,
                           "prov": "credit_rating_events · " + str(asof or "—")}
            elif lens == "sast":
                conf, tape, asof = R.own_sast(conn)
                conf2, sample = R.pick(conf, R.DEMO_SAST)
                payload = {"confluence": conf2, "tape": tape,
                           "prov": "sast_reg29_events + sast_pledge_events · " + str(asof or "—")}
            elif lens == "shp":
                payload = {"matrix": R.own_shp(), "prov": "shareholding_history (research store)"}
            else:
                board, tape, asof = R.own_insider(conn)
                board2, sample = R.pick(board, R.DEMO_INSIDER)
                payload = {"board": board2, "tape": tape,
                           "prov": "insider_events · " + str(asof or "—")}
            return _render("Ownership & filings", B.ownership(lens, payload, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Ownership & filings", "The filings feeds")


# ── launchpad (screen + its evidence) ──────────────────────────────────────────


@router.get(_BASE + "/launchpad", response_class=HTMLResponse, include_in_schema=False)
def strategies_launchpad(request: Request) -> HTMLResponse:
    """The launchpad screen and — as its second tab, not a separate page — the published outcome
    study that IS its evidence. The 'validated screen, no fundable edge net of cost' verdict renders
    above both tabs; the study adds its own gross-of-cost + survivorship warning."""
    tab = _q(request, "tab")
    if tab not in ("", "evidence"):
        tab = ""
    try:
        with _conn() as conn:
            conn.row_factory = sqlite3.Row
            screen, asof = R.launchpad_screen(conn)
            ev = R.launchpad_evidence(conn) if tab == "evidence" else {}
            sample = (tab == "evidence" and not ev.get("n"))
            return _render("Launchpad", B.launchpad(tab, screen, asof, ev, sample=sample), conn)
    except Exception:  # noqa: BLE001
        return _fail("Launchpad", "The launchpad screen")


# ── selftest — `python -m src.web.home.strategies_pages` ───────────────────────


def _selftest() -> int:
    """Render every workspace route and assert the Graphite contract AND the fences hold.

    Deliberately stronger than a status-200 smoke test: it fails on the degraded branch and on a
    missing recorded verdict, because both of those render a perfectly plausible 200.
    """
    from fastapi.testclient import TestClient
    from src.main import app
    c = TestClient(app)
    # (path, the fence / evidence string that MUST be present)
    paths = [
        (_BASE, "Exactly one result"),
        (_BASE + "/books", "not a Sharpe ratio"),
        (_BASE + "/sector-rotation", "SECTORS, not STOCKS"),
        (_BASE + "/library", "Public / classic"),
        (_BASE + "/positioning", "not a signal"),
        (_BASE + "/positioning?view=stealth", "never a buy list"),
        (_BASE + "/conviction", "sorting heuristic, not a validated model"),
        (_BASE + "/mep", "Descriptor only"),
        (_BASE + "/credibility", "never ranked"),
        (_BASE + "/credibility?sym=SAMPLEA", "promise vs delivery"),
        (_BASE + "/growth", "proposal ledger, not a signal"),
        (_BASE + "/ownership", "Descriptive"),
        (_BASE + "/ownership?lens=ratings", "company-level actions"),
        (_BASE + "/ownership?lens=sast", "control event"),
        (_BASE + "/ownership?lens=shp", "quarter"),
        (_BASE + "/launchpad", "no fundable edge net of cost"),
        (_BASE + "/launchpad?tab=evidence", "survivorship-exposed"),
    ]
    bad = 0
    for p, needle in paths:
        r = c.get(p, follow_redirects=True)
        why = ""
        if r.status_code != 200:
            why = "status " + str(r.status_code)
        elif _DEGRADED in r.text:
            why = "DEGRADED branch (an exception was swallowed)"
        elif "data-ui-g" not in r.text or "uk-sub" in r.text:
            why = "not in the Graphite shell"
        elif needle not in r.text:
            why = "missing fence/evidence: " + needle
        if why:
            bad += 1
        print(("  ok   " if not why else "  FAIL ") + p + "  " + str(len(r.text) // 1024)
              + "KB" + (("  <- " + why) if why else ""))
    print("strategies workspace selftest: " + str(len(paths) - bad) + "/" + str(len(paths))
          + " routes render in the Graphite shell with their fences intact")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
