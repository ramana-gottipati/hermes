"""P-05 smoke — /dash/replay-any-date renders honestly in every key/input state.

The page's contract: a trust surface must never error — no key degrades to an honest
"not provisioned" note; a junk symbol is refused before any API call; with a key the
panels carry the API's own values (here: the stub DB's typed absence) and the exact
reproduction curl. Descriptive-only language is load-bearing (no performance claims).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI                      # noqa: E402
from fastapi.testclient import TestClient        # noqa: E402

import src.web.replay_any_date as RAD            # noqa: E402


def _page():
    app = FastAPI()
    app.include_router(RAD.router)
    return TestClient(app)


def test_no_key_degrades_honestly(monkeypatch):
    monkeypatch.setattr(RAD, "_demo_key", lambda: "")
    r = _page().get("/dash/replay-any-date")
    assert r.status_code == 200
    assert "demo key not provisioned" in r.text
    assert "performance claim" in r.text          # the descriptive-only line always renders


def test_junk_symbol_never_reaches_the_api(monkeypatch):
    calls = []
    monkeypatch.setattr(RAD, "_demo_key", lambda: "k")
    monkeypatch.setattr(RAD, "_call", lambda p: calls.append(p) or {"status": 0, "error": "x"})
    r = _page().get("/dash/replay-any-date?symbol=..%2F..%2Fetc&as_of=2020-01-01")
    assert r.status_code == 200 and "Symbol must be" in r.text
    assert calls == []                            # refused client-side, no API touch


def test_keyed_journey_on_the_stub_db(monkeypatch):
    """End-to-end through the REAL v1 app: seed an ephemeral local key, load the page,
    expect the API's own typed absence (stub DB has no series) + pit chips + the curl."""
    from src.api.v1.keys import seed_dev_key
    from src.api.v1.selftest import _teardown
    _teardown()
    try:
        key = seed_dev_key()                      # ephemeral (env unset locally)
        monkeypatch.setattr(RAD, "_demo_key", lambda: key)
        r = _page().get("/dash/replay-any-date?symbol=RELIANCE&as_of=2020-06-30")
        assert r.status_code == 200
        t = r.text
        assert "requested as-of" in t and "2020-06-30" in t
        assert "curl -s -H" in t and "X-API-Key: $PATEARN_KEY" in t
        assert ("Typed absence" in t) or ("track record" in t)   # stub -> absence; prod -> row
        assert "rule applied" in t or "knowable" in t.lower()
    finally:
        _teardown()
