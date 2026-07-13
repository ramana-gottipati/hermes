"""Attention Queue face (D106, S103) — hermetic tests over an in-memory bus.

The view reads ONLY through signal_events' public read APIs, so the whole face is
testable against an in-memory DB seeded with the bus's own detectors: the ranked
tape, the honest-empty branches, the rs-lens link routing (index names have no
dossier), the batch-history pivot, the /v1-mirroring PIT replay composition, and
the hard-capped Home card. get_conn is monkeypatched at the module attribute.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from src.automation import signal_events as SE
import src.web.attention_view as av


@pytest.fixture()
def conn():
    # TestClient serves routes on a worker thread — the shared in-memory conn must
    # cross threads (production get_conn opens per-call in the handler thread).
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    SE.ensure_schema(c)
    # Two batch days across four lenses, emitted through the real detectors.
    SE.emit(c, "RELIANCE", "mep", "2026-07-09",
            SE.detect_phase_flip("DISTRIB", "ACCUM"))
    SE.emit(c, "TCS", "cci", "2026-07-08",
            SE.detect_credibility_step(50, 62))
    SE.emit(c, "Nifty IT", "rs", "2026-07-09",
            SE.detect_phase_flip("IN_BAND", "ABOVE"))
    SE.emit(c, "VEDL", "deal", "2026-07-09",
            {"event_type": "deal_print", "direction": "up",
             "from_state": None, "to_state": "2 print(s) ₹41.0cr", "magnitude": 0.97})
    c.commit()
    return c


@pytest.fixture()
def patched(conn, monkeypatch):
    @contextmanager
    def fake_get_conn():
        yield conn
    monkeypatch.setattr(av, "get_conn", fake_get_conn)
    return conn


def test_queue_table_data_first(conn):
    events = SE.attention_queue(conn, as_of="2026-07-09", limit=50)
    html = av.render_queue_table(events)
    assert '/dash/stock?symbol=RELIANCE' in html
    assert "DISTRIB" in html and "ACCUM" in html          # raw before → after kept
    assert '/dash/rsband' in html                          # rs lens: index name, no dossier
    assert '/dash/stock?symbol=Nifty' not in html
    assert "0.97" in html                                  # deal percentile magnitude shown


def test_queue_table_empty_is_honest():
    html = av.render_queue_table([])
    assert "quiet tape" in html


def test_batch_history_pivot(conn):
    hist = [dict(r) for r in conn.execute(
        "SELECT as_of, lens, COUNT(*) AS n FROM signal_events "
        "GROUP BY as_of, lens ORDER BY as_of DESC").fetchall()]
    html = av.render_batch_history(hist, ("mep", "cci", "oi", "rs", "deal"))
    assert "2026-07-09" in html and "2026-07-08" in html
    assert "oi" not in html.split("<tr>")[1]               # never-emitted lens has no column


def test_pit_composition_mirrors_v1(conn):
    # Weekend/holiday miss serves the prior batch, never an empty tape.
    assert SE.latest_batch_on_or_before(conn, "2026-07-10") == "2026-07-09"
    assert SE.latest_batch_on_or_before(conn, "2026-07-08") == "2026-07-08"
    # A date before the feed began resolves to None (typed absence, not a fake batch).
    assert SE.latest_batch_on_or_before(conn, "2020-01-01") is None


def test_page_route_latest_and_replay(patched):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(av.router)
    c = TestClient(app)

    r = c.get("/dash/attention")
    assert r.status_code == 200
    assert "RELIANCE" in r.text and "Attention queue" in r.text

    r = c.get("/dash/attention?as_of=2026-07-10")
    assert r.status_code == 200
    assert "Replay:" in r.text and "2026-07-09" in r.text   # served batch disclosed

    r = c.get("/dash/attention?as_of=2020-01-01")
    assert r.status_code == 200
    assert "none" in r.text                                  # honest pre-feed absence

    r = c.get("/dash/attention?lens=mep")
    assert r.status_code == 200
    assert "mep only" in r.text


def test_render_cap_discloses_full_batch(patched, conn):
    # S103 walk-caught: the tile/denominator must be the BATCH's truth even when the
    # render caps at _PAGE_LIMIT; the cap itself is disclosed.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    for i in range(250):
        SE.emit(conn, f"SYM{i:03}", "mep", "2026-07-11",
                SE.detect_phase_flip("DISTRIB", "ACCUM"))
    conn.commit()
    app = FastAPI()
    app.include_router(av.router)
    c = TestClient(app)
    r = c.get("/dash/attention")
    assert "showing the top 200 of 250 by impact" in r.text
    r = c.get("/dash/attention?lens=mep")
    assert "mep only (250 of 250)" in r.text          # true denominators, not the cap


def test_replay_serves_old_dated_events_honestly(patched, conn):
    # S103 walk-caught (live): stale symbols seeded events dated YEARS before the bus
    # went live — replay serves them as real batches (two-clock honesty), never hides.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    SE.emit(conn, "OLDCO", "mep", "2019-05-01",
            SE.detect_phase_flip("ACCUM", "NEUTRAL"))
    conn.commit()
    app = FastAPI()
    app.include_router(av.router)
    c = TestClient(app)
    r = c.get("/dash/attention?as_of=2020-01-01")
    assert r.status_code == 200
    assert "2019-05-01" in r.text and "OLDCO" in r.text


def test_since_last_looked_pure_branches():
    # First visit: gentle intro, never a fake "0 new".
    assert "First visit" in av.render_since_last_looked([], None, first_visit=True)
    # Returning, nothing new: honest all-caught-up with the timestamp echoed.
    h = av.render_since_last_looked([], "2026-07-10 12:00:00", first_visit=False)
    assert "All caught up" in h and "2026-07-10 12:00:00" in h
    # Returning, N new: count + newest-first list.
    ev = [{"symbol": "RELIANCE", "lens": "mep", "note": "x", "as_of": "2026-07-10"}]
    h = av.render_since_last_looked(ev, "2026-07-01 00:00:00", first_visit=False)
    assert "1 new" in h and "RELIANCE" in h


def test_since_last_looked_route_cookie_flow(patched):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(av.router)

    # No cookie → first visit; the response STAMPS the last-seen cookie for next time.
    r = TestClient(app).get("/dash/attention")
    assert r.status_code == 200 and "First visit" in r.text
    assert r.cookies.get("patearn_bus_seen")               # write-back happened

    # Old cookie → everything detected since counts as new (seeded events are ~now).
    old = TestClient(app); old.cookies.set("patearn_bus_seen", "2020-01-01 00:00:00")
    r = old.get("/dash/attention")
    assert "since your last visit" in r.text and "RELIANCE" in r.text

    # Future cookie → all caught up (nothing detected after it).
    fut = TestClient(app); fut.cookies.set("patearn_bus_seen", "2099-01-01 00:00:00")
    r = fut.get("/dash/attention")
    assert "All caught up" in r.text

    # A replay is a historical read, NOT a visit — the brief is suppressed there.
    r = TestClient(app).get("/dash/attention?as_of=2026-07-09")
    assert "since your last visit" not in r.text and "First visit" not in r.text


def test_alert_rail_pure_branches():
    # Empty rail is honest, never '' — a quiet rail is stated as such.
    h = av.render_alert_rail([], {"total": 0, "by_severity": {}},
                             window_days=7, anchor="2026-07-09")
    assert "Alert rail" in h and "No high-impact alerts" in h
    # Populated: severity badge + valence read + symbol + count badges.
    alerts = [{"symbol": "VEDL", "lens": "deal", "severity": "critical",
               "valence": "opportunity", "from_state": None, "to_state": "₹41cr",
               "note": "VEDL: big print", "as_of": "2026-07-09"}]
    h = av.render_alert_rail(alerts, {"total": 1, "by_severity": {"critical": 1}},
                             window_days=7, anchor="2026-07-09")
    assert "CRITICAL" in h and "opp" in h and "VEDL" in h and "1 critical" in h
    # Descriptive fence rides along — never a recommendation.
    assert "never a recommendation" in h


def test_alert_rail_on_page(patched, conn):
    # The 4th face surfaces on /dash/attention once the batch is promoted; the deal
    # (0.97 percentile) + the mep→ACCUM flip are alert-worthy, the rs→ABOVE flip is not.
    from src.automation import signal_alerts as SA
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    SA.promote(conn, as_of="2026-07-09")
    app = FastAPI()
    app.include_router(av.router)
    r = TestClient(app).get("/dash/attention")
    assert r.status_code == 200
    assert "Alert rail" in r.text and "active" in r.text
    assert "HIGH" in r.text                                  # the severity cell renders
    # A pre-feed replay has no served batch → the rail is cleanly skipped (no crash).
    r2 = TestClient(app).get("/dash/attention?as_of=2020-01-01")
    assert r2.status_code == 200


def test_home_inner_capped_and_safe(patched, conn):
    html = av.attention_home_inner(limit=6)
    assert "RELIANCE" in html or "VEDL" in html
    assert html.count("<tr") <= 6
    # An empty bus yields '' so the Home board is omitted, never broken.
    conn.execute("DELETE FROM signal_events")
    conn.commit()
    assert av.attention_home_inner() == ""
