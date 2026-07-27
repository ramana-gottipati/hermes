"""test_home_tracker.py — the Graphite Tracker gate (lane w3-tracker, milestone M7).

Four contracts, in the order they matter:

1. **The privacy gate travels.** `/dash/home/tracker*` sits outside `tracker_gate`'s middleware
   prefix, so the pages ask the gate directly. Anonymous must get the demo book; a credential the
   classic gate already understands must unlock the real one. A regression here leaks someone's
   positions onto a public site, so it is asserted in BOTH directions.
2. **One write path.** The watch tier is written by the home's `POST /dash/home/watch/add` and by
   nothing else; the importer is the single new write and it validates before AND after the preview.
3. **The numbers are backed.** `cashflow_fidelity()` must FAIL on a ledger that cannot support a
   money-weighted return and PASS on one that can, and `xirr()` must be silent whenever it fails.
   The time-weighted curve must not count a position's arrival as a gain.
4. **Isolation + registration.** No banned import, Graphite markers present, preview/legacy markers
   absent, every GET page declared in the route registry, every parity claim pointing at a live
   route.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
LANE_FILES = ("tracker_pages.py", "tracker_reads.py")
PAGES = ("/dash/home/tracker", "/dash/home/tracker/portfolios", "/dash/home/tracker/watchlists",
         "/dash/home/tracker/performance", "/dash/home/tracker/import")
SECRET = "test-owner-secret"


# ── fixtures ──────────────────────────────────────────────────────────────────────
def _app():
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return M.app


@pytest.fixture(scope="module")
def client():
    return TestClient(_app())


@pytest.fixture(scope="module")
def owner_client():
    """A client carrying the credential the classic gate already understands."""
    from src.web import tracker_gate
    return TestClient(_app(), cookies={"pt_owner": tracker_gate._token(SECRET)})


def _db(positions=(), closed=(), watch=(), prices=(), cas=(), index=()):
    """A throwaway lifecycle DB with only the columns these reads touch."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE stocks_in_play(id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, strategy TEXT,
            book TEXT, status TEXT, date_added TEXT, entry_price REAL, qty REAL, price_target REAL,
            stop_loss REAL, entry_thesis TEXT, snapshot_json TEXT, exit_date TEXT, exit_price REAL,
            exit_reason TEXT);
        CREATE TABLE bhavcopy_rows(symbol TEXT, trade_date TEXT, series TEXT, close REAL,
            prev_close REAL, deliv_per REAL, value REAL);
        CREATE TABLE stock_signals(symbol TEXT, trade_date TEXT, primary_sector TEXT, rs_rank INTEGER,
            rs_vs_broad_trend_state TEXT, avg_deliv_pct_1m REAL);
        CREATE TABLE corporate_actions(symbol TEXT, action_type TEXT, ex_date TEXT);
        CREATE TABLE index_rows(index_name TEXT, trade_date TEXT, close_value REAL);
    """)
    for p in positions:
        conn.execute("INSERT INTO stocks_in_play(symbol,strategy,book,status,date_added,entry_price,qty)"
                     " VALUES(?,?,?,'open',?,?,?)", p)
    for c in closed:
        conn.execute("INSERT INTO stocks_in_play(symbol,strategy,book,status,date_added,entry_price,"
                     "qty,exit_date,exit_price) VALUES(?,?,?,'closed',?,?,?,?,?)", c)
    for w in watch:
        conn.execute("INSERT INTO stocks_in_play(symbol,strategy,book,status,date_added)"
                     " VALUES(?,'Manual','Main','watch',?)", w)
    for row in prices:
        conn.execute("INSERT INTO bhavcopy_rows(symbol,trade_date,series,close,prev_close,deliv_per)"
                     " VALUES(?,?,'EQ',?,?,55)", row)
    for a in cas:
        conn.execute("INSERT INTO corporate_actions(symbol,action_type,ex_date) VALUES(?,?,?)", a)
    for i in index:
        conn.execute("INSERT INTO index_rows(index_name,trade_date,close_value) VALUES(?,?,?)", i)
    conn.commit()
    return conn


# ── 1. the privacy gate, in both directions ───────────────────────────────────────
def test_anonymous_sees_the_demo_book_on_every_tracker_page(client, monkeypatch):
    """With a secret configured, a visitor with no credential gets the synthetic book — never a
    real position — on all five pages."""
    from src.web import tracker_gate
    monkeypatch.setattr(tracker_gate, "_secret", lambda: SECRET)
    for path in PAGES:
        r = client.get(path)
        assert r.status_code == 200, (path, r.status_code)
        assert "Demo book" in r.text, ("no demo banner on", path)
        assert "invented positions, live prices" in r.text, path


def test_owner_credential_unlocks_the_real_book(owner_client, monkeypatch):
    from src.web import tracker_gate
    monkeypatch.setattr(tracker_gate, "_secret", lambda: SECRET)
    for path in PAGES:
        r = owner_client.get(path)
        assert r.status_code == 200, (path, r.status_code)
        assert "Demo book — invented positions" not in r.text, ("demo leaked to the owner", path)


def test_gate_fails_closed_when_it_cannot_answer(monkeypatch):
    """A privacy gate that errors must return the demo, never the real book."""
    from src.web.home import tracker_pages as TP

    class _Boom:
        @property
        def cookies(self):
            raise RuntimeError("gate unavailable")
    monkeypatch.setattr("src.web.tracker_gate._secret", lambda: SECRET)
    assert TP._is_owner(_Boom()) is False


def test_import_writes_are_owner_only(client, monkeypatch):
    from src.web import tracker_gate
    monkeypatch.setattr(tracker_gate, "_secret", lambda: SECRET)
    for path in ("/dash/home/tracker/import/preview", "/dash/home/tracker/import/commit"):
        r = client.post(path, data={"pasted": "RELIANCE,1,100", "rows": "[]"},
                        follow_redirects=False)
        assert r.status_code == 303, (path, r.status_code)
        assert "/dash/home/tracker/import" in r.headers.get("location", ""), path
    # an export is the personal book leaving the site — the demo never produces one
    r = client.get("/dash/home/tracker/export?view=portfolio", follow_redirects=False)
    assert r.status_code == 303


# ── 2. one write path ─────────────────────────────────────────────────────────────
def test_watchlist_reuses_the_homes_single_write_endpoint(owner_client, monkeypatch):
    from src.web import tracker_gate
    monkeypatch.setattr(tracker_gate, "_secret", lambda: SECRET)
    html = owner_client.get("/dash/home/tracker/watchlists").text
    assert 'action="/dash/home/watch/add"' in html, "the watch add must post to the home's endpoint"
    forms = re.findall(r'<form[^>]*action="([^"]*)"', html)
    extra = [a for a in forms if a.startswith("/dash/home/tracker") and "import" not in a]
    assert not extra, ("a second tracker write path appeared", extra)


def test_importer_round_trip_writes_only_validated_rows():
    from src.web.home import tracker_reads as TR
    conn = _db(prices=[("RELIANCE", "2026-07-24", 1200, 1190), ("TCS", "2026-07-24", 3600, 3580)])
    parsed = TR.parse_holdings(
        "Symbol,Entry Date,Entry Price,Qty,Strategy\n"
        "RELIANCE,2026-01-15,1320.50,25,Quality\n"
        "NOTALISTEDCO,2026-01-15,10,5,Junk\n"
        "TCS,2026-02-01,3400,4,Core\n")
    v = TR.validate_rows(conn, parsed["rows"], "open")
    assert (v["ok"], v["bad"]) == (2, 1), v
    written, skipped = TR.commit_rows(conn, v["rows"], "open", "Imported")
    assert (written, skipped) == (2, 1)
    got = {r["symbol"]: r for r in conn.execute("SELECT * FROM stocks_in_play")}
    assert set(got) == {"RELIANCE", "TCS"} and "NOTALISTEDCO" not in got
    assert got["RELIANCE"]["book"] == "Imported" and got["RELIANCE"]["qty"] == 25
    # a second import of the same file is a no-op, not a duplicate book
    v2 = TR.validate_rows(conn, TR.parse_holdings("Symbol,Qty,Price\nRELIANCE,25,1320.5")["rows"], "open")
    assert v2["skip"] == 1 and TR.commit_rows(conn, v2["rows"], "open", "Imported") == (0, 1)


def test_importer_never_trusts_the_file():
    """Injection-safety: the symbol is sanitised at parse time and membership-checked at validate
    time, so markup or SQL in a spreadsheet cell can never reach the table or the page."""
    from src.web.home import tracker_reads as TR
    conn = _db(prices=[("RELIANCE", "2026-07-24", 1200, 1190)])
    nasty = "Symbol,Qty,Price\n\"'); DROP TABLE stocks_in_play;--\",1,10\n<script>x</script>,1,10\n"
    v = TR.validate_rows(conn, TR.parse_holdings(nasty)["rows"], "open")
    assert v["ok"] == 0 and v["bad"] == 2
    TR.commit_rows(conn, v["rows"], "open", "Main")
    assert conn.execute("SELECT COUNT(*) FROM stocks_in_play").fetchone()[0] == 0


# ── 3. the numbers are backed ─────────────────────────────────────────────────────
def test_cashflow_fidelity_fails_on_a_position_ledger_and_says_why():
    from src.web.home import tracker_reads as TR
    conn = _db(positions=[("RELIANCE", "Q", "Main", "2026-01-15", 1200, 10),
                          ("RELIANCE", "Q", "Main", "2026-03-15", 1250, 5),   # a second lot
                          ("TCS", "Q", "Main", "2026-02-01", 3400, None)],    # no quantity
               cas=[("RELIANCE", "BONUS", "2026-04-01"), ("TCS", "DIVIDEND", "2026-05-02")])
    fid = TR.cashflow_fidelity(conn)
    assert fid["verdict"] == "FAIL"
    joined = " ".join(fid["reasons"])
    assert "lots" in joined and "quantity" in joined
    assert fid["ca_hits"] == 1 and fid["div_hits"] == 1
    assert TR.xirr(conn) is None, "XIRR must stay silent while the flow set is incomplete"


def test_cashflow_fidelity_passes_and_releases_xirr_on_a_clean_book():
    from src.web.home import tracker_reads as TR
    conn = _db(closed=[("RELIANCE", "Q", "Main", "2025-07-01", 1000.0, 10, "2026-07-01", 1200.0)],
               prices=[("RELIANCE", "2026-07-24", 1200, 1190)])
    fid = TR.cashflow_fidelity(conn)
    assert fid["verdict"] == "PASS", fid["reasons"]
    x = TR.xirr(conn)
    assert x is not None and 15.0 < x < 25.0, x     # +20% over ~1 year


def test_time_weighted_curve_ignores_a_position_arriving():
    """The honest property: money entering the book must not read as a gain. Two names, one added
    late — the chained series must reflect only the price move of what was held on both sides."""
    from src.web.home import tracker_reads as TR
    px = [("AAA", "2026-01-01", 100, 100), ("AAA", "2026-01-02", 110, 100),
          ("AAA", "2026-01-03", 110, 110), ("BBB", "2026-01-03", 500, 500)]
    conn = _db(positions=[("AAA", "Q", "Main", "2026-01-01", 100.0, 10),
                          ("BBB", "Q", "Main", "2026-01-03", 500.0, 10)], prices=px)
    cv = TR.twr_curve(conn, TR.positions(conn)["rows"], [])
    assert cv and len(cv["curve"]) >= 3
    assert abs(cv["ret"] - 10.0) < 0.01, cv["ret"]   # +10% from AAA only, not +400% from BBB arriving
    assert cv["equal_weight"] is False


def test_scoreboard_shows_the_verdict_not_a_number_when_the_check_fails():
    from src.web.home import tracker_pages as TP
    fail = TP._xirr_panel({"verdict": "FAIL", "reasons": ["3 positions carry no quantity"]}, None)
    assert "XIRR — not shown" in fail and "3 positions carry no quantity" in fail
    assert "time-weighted" in fail, "the reader must be told what replaced it"
    ok = TP._xirr_panel({"verdict": "PASS", "reasons": []}, 18.25)
    assert "+18.2%" in ok and "not shown" not in ok


def test_performance_and_positions_survive_a_thin_schema():
    """Older/fixture hosts have no `book`/`qty` columns — the reads must degrade, never raise."""
    from src.web.home import tracker_reads as TR
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE stocks_in_play(id INTEGER PRIMARY KEY, symbol TEXT, strategy TEXT, "
                 "status TEXT, date_added TEXT, entry_price REAL, price_target REAL, stop_loss REAL, "
                 "snapshot_json TEXT, exit_date TEXT, exit_price REAL, exit_reason TEXT)")
    conn.execute("INSERT INTO stocks_in_play(symbol,strategy,status,date_added,entry_price) "
                 "VALUES('RELIANCE','Q','open','2026-01-15',1200)")
    pos = TR.positions(conn)
    assert pos["rows"][0]["book"] == "Main" and pos["rows"][0]["qty"] is None
    assert TR.performance(conn)["n_open"] == 1
    assert TR.cashflow_fidelity(conn)["verdict"] == "FAIL"


# ── 4. isolation, registration, parity ────────────────────────────────────────────
def test_lane_modules_import_nothing_banned():
    from tests.test_home_isolation import BANNED
    for name in LANE_FILES:
        text = (ROOT / "src" / "web" / "home" / name).read_text(encoding="utf-8")
        for mod in BANNED:
            assert not re.search(r"^\s*(from|import)\s+[\w.]*\b" + mod + r"\b", text, re.M), \
                (name, mod)


def test_pages_carry_graphite_markers_and_no_legacy_ones(client):
    from tests.test_home_isolation import PREVIEW_LEGACY_MARKERS
    for path in PAGES:
        r = client.get(path)
        assert r.status_code == 200 and "data-ui-g" in r.text, path
        for m in PREVIEW_LEGACY_MARKERS:
            assert m not in r.text, (path, m)


def test_every_tracker_page_is_route_gate_registered():
    from tests import test_dash_route_registry as gate
    for path in PAGES:
        assert path in gate.INTERNAL_DEV, path
        owner, rationale = gate.INTERNAL_DEV[path]
        assert owner == "graphite-tracker" and len(rationale) > 40, path


def test_no_lens_registry_entry_was_added():
    """Registering a lens IS the cutover — these pages stay declared children until then."""
    from src.web import lens_registry as LR
    assert not [ln for ln in LR.LENSES if (ln.route or "").startswith("/dash/home")]


def test_the_five_views_are_reachable_from_each_other(client):
    """No orphans: every page renders the view switcher, and the Graphite top bar's Tracker
    destination points at the overview."""
    from src.web.home import shell
    assert ("Tracker", "/dash/home/tracker") in shell.DESTS
    for path in PAGES:
        html = client.get(path).text
        for suffix, label in (("", "Overview"), ("/portfolios", "Positions"),
                              ("/watchlists", "Watchlist"), ("/performance", "Scoreboard"),
                              ("/import", "Import")):
            assert f'href="/dash/home/tracker{suffix}"' in html, (path, label)


def test_parity_entries_are_honest_and_point_at_live_routes(client):
    """2026-07-28: the five built Tracker surfaces were downgraded PORTED -> DEFERRED by the gap
    audit (register §5a-§5e — Pro-gated columns that were free in classic, the ready-to-act block,
    return attribution, the import column-mapping override). The honesty contract is unchanged and
    now stricter: whatever the disposition, the note must name the live route AND the residual, and
    that route must still serve 200."""
    from src.web import sideways_parity as SP
    keys = ("dashboard", "portfolios", "model-books", "watchlists", "performance", "import")
    for k in keys:
        status, target, note = SP.SURFACE_PARITY[k]
        assert status in ("PORTED", "DEFERRED", "DROPPED"), (k, status)
        assert note.strip(), k
        if status in ("PORTED", "DEFERRED"):
            route = target if status == "PORTED" else note.split("LANDED at ", 1)[-1].split(":")[0]
            assert route.startswith("/dash/home/tracker"), (k, route)
            assert client.get(route).status_code == 200, (k, route)
            assert "RESIDUAL" in note, (k, "a port claim must name what did not travel")
            if status == "DEFERRED":
                assert target in SP.MILESTONES, (k, "DEFERRED needs a real milestone", target)
        else:
            assert target == "" and "MERGE" in note, k


def test_server_side_csv_export_shapes(owner_client, monkeypatch):
    from src.web import tracker_gate
    monkeypatch.setattr(tracker_gate, "_secret", lambda: SECRET)
    for view, first in (("portfolio", "Symbol,Entry Date,Entry Price,Qty"),
                        ("watchlist", "Symbol,Added Date,Strategy"),
                        ("closed", "Symbol,Entry Date,Entry Price,Qty")):
        r = owner_client.get(f"/dash/home/tracker/export?view={view}")
        assert r.status_code == 200 and r.text.startswith(first), (view, r.text[:60])
        assert "attachment" in r.headers.get("content-disposition", ""), view


def test_module_selftests_pass():
    from src.web.home import tracker_pages, tracker_reads
    assert tracker_reads._selftest() == 0
    assert tracker_pages._selftest() == 0
