"""S-D search & entry (UX audit §8) — hermetic tests for the name→ticker lookup.

Covers the ranked `search()` (the one lookup every entry surface shares), the
`/dash/api/symbol-search` typeahead feed, and the stock-miss `did_you_mean_html`
strip. All DB access is an injected in-memory connection or a tmp-file DB via a
monkeypatched `src.core.db.DB_PATH` — nothing touches the real data/hermes.db.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.web.symbol_search as ss

_FIXTURE = [
    # symbol, company_name, currently_listed, n_days
    ("TCS", "Tata Consultancy Services Limited", 1, 5000),
    ("TATACONSUM", "Tata Consumer Products Limited", 1, 3000),
    ("TATAMOTORS", "Tata Motors Limited", 1, 5200),
    ("RELIANCE", "Reliance Industries Limited", 1, 6000),
    ("RELINFRA", "Reliance Infrastructure Limited", 1, 4000),
    ("OLDTATA", "Old Tata Venture Limited", 0, 900),        # delisted
]


def _seed(c: sqlite3.Connection) -> None:
    c.execute("CREATE TABLE security_master (symbol TEXT PRIMARY KEY, company_name TEXT,"
              " currently_listed INTEGER, n_days INTEGER)")
    c.executemany("INSERT INTO security_master VALUES (?,?,?,?)", _FIXTURE)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    _seed(c)
    yield c
    c.close()


# ── search(): ranking ─────────────────────────────────────────────────────────────
def test_company_name_reaches_ticker(conn):
    """The audit's canonical miss: 'tata consultancy' must surface TCS first."""
    hits = ss.search("tata consultancy", conn=conn)
    assert hits and hits[0]["symbol"] == "TCS"


def test_exact_symbol_wins(conn):
    assert ss.search("TCS", conn=conn)[0]["symbol"] == "TCS"
    assert ss.search("tcs", conn=conn)[0]["symbol"] == "TCS"      # case-insensitive


def test_symbol_prefix_beats_name_substring(conn):
    hits = ss.search("REL", conn=conn)
    syms = [h["symbol"] for h in hits]
    assert syms[0] in ("RELIANCE", "RELINFRA") and set(syms[:2]) == {"RELIANCE", "RELINFRA"}


def test_delisted_ranks_last_and_is_labeled(conn):
    hits = ss.search("tata", conn=conn)
    assert hits[-1]["symbol"] == "OLDTATA" and hits[-1]["listed"] is False
    assert all(h["listed"] for h in hits[:-1])


def test_empty_wildcards_and_garbage_never_raise(conn):
    assert ss.search("", conn=conn) == []
    assert ss.search("   ", conn=conn) == []
    assert ss.search("zz_nohit_zz", conn=conn) == []
    # LIKE metacharacters are escaped — '%' must not become match-everything
    assert ss.search("%", conn=conn) == []
    assert ss.search("_", conn=conn) == []
    assert ss.search("x" * 500, conn=conn) == []                  # length-capped


def test_no_table_degrades_to_empty():
    bare = sqlite3.connect(":memory:")
    bare.row_factory = sqlite3.Row
    assert ss.search("tata", conn=bare) == []                     # no tables → [], no raise


def test_equity_list_fallback():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row                                    # no security_master at all
    c.execute("CREATE TABLE nse_equity_list (symbol TEXT, company_name TEXT)")
    c.execute("INSERT INTO nse_equity_list VALUES ('TCS','Tata Consultancy Services Limited')")
    assert ss.search("consultancy", conn=c)[0]["symbol"] == "TCS"


# ── did_you_mean_html(): the stock-miss strip ─────────────────────────────────────
def test_did_you_mean_links_to_stock(conn):
    h = ss.did_you_mean_html("tata consultancy", conn=conn)
    assert 'href="/dash/stock?sym=TCS"' in h and "Did you mean" in h


def test_did_you_mean_empty_on_no_match(conn):
    assert ss.did_you_mean_html("zz_nohit_zz", conn=conn) == ""


def test_did_you_mean_escapes_html():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE security_master (symbol TEXT PRIMARY KEY, company_name TEXT,"
              " currently_listed INTEGER, n_days INTEGER)")
    c.execute("INSERT INTO security_master VALUES ('EVIL', 'A <b>&amp;</b> Co', 1, 10)")
    h = ss.did_you_mean_html("evil", conn=c)
    assert "<b>&amp;</b> Co" not in h and "&lt;b&gt;" in h


# ── the JSON endpoint ─────────────────────────────────────────────────────────────
@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    c = sqlite3.connect(db)
    _seed(c)
    c.commit()
    c.close()
    import src.core.db as core_db
    monkeypatch.setattr(core_db, "DB_PATH", db)
    app = FastAPI()
    app.include_router(ss.router)
    return TestClient(app)


def test_endpoint_shape_and_hit(client):
    r = client.get("/dash/api/symbol-search", params={"q": "tata consultancy"})
    assert r.status_code == 200
    j = r.json()
    assert j["q"] == "tata consultancy"
    assert j["results"][0] == {"symbol": "TCS", "name": "Tata Consultancy Services Limited",
                               "status": ""}


def test_endpoint_delisted_status(client):
    j = client.get("/dash/api/symbol-search", params={"q": "old tata"}).json()
    assert j["results"] and j["results"][0]["status"] == "delisted"


def test_endpoint_always_200(client):
    for q in ("", "%", "'; DROP TABLE security_master;--", "x" * 500):
        assert client.get("/dash/api/symbol-search", params={"q": q}).status_code == 200


def test_router_is_in_v2_specs():
    """The durable-mount contract (Lane E): the endpoint must ride _ROUTER_SPECS."""
    from src.web.v2_surfaces import _ROUTER_SPECS
    assert any(m == "src.web.symbol_search" and s == "/dash/api/symbol-search"
               for _d, m, s in _ROUTER_SPECS)


# ── the ⌘K palette (S-D: generated from the registry, never hand-maintained) ──────
def test_palette_covers_every_routed_lens():
    """The audit bar: the palette lists ALL lenses — derived, so it can't drift."""
    import json
    import re as _re
    from src.web import ui_kit
    from src.web.lens_registry import LENSES
    pages = json.loads(ui_kit._palette_pages_json())
    for ln in LENSES:
        if not ln.route:
            continue
        key = _re.sub(r" +", " ", _re.sub(r"[^a-z0-9 ]", "", ln.key.lower())).strip()
        assert key in pages, f"lens {ln.key!r} missing from the ⌘K palette"


def test_palette_keeps_legacy_static_aliases():
    import json
    from src.web import ui_kit
    pages = json.loads(ui_kit._palette_pages_json())
    assert pages["screen classic"] == "/dash/screener"
    assert pages["ratio"] == "/dash/ratio"      # the route-gate §5 "palette entry (S-D)" promise
    assert pages["methodology"] == "/dash/glossary"


def test_cmdk_overlay_carries_typeahead():
    from src.web import ui_kit
    ov = ui_kit.cmdk_overlay()
    assert "__symTA" in ov and "cmdk-sug" in ov and "/dash/api/symbol-search" in ov
