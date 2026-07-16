"""Real-time seam contracts (D134 LANE-I, plan §4-I / L1).

Hermetic temp-DB tests. The licence boundary is the point: the feed is declared
'personal-broker' (RESTRICTED) in the manifest, so the LANE-C licence gate keeps
it off every public surface; this file adds the seam-specific checks (interface
conformance, bounded window, isolation from main tables, no Kite wiring).
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.automation import feed_manifest as fm  # noqa: E402
from src.automation import intraday_adapter as ia  # noqa: E402

NOW = "2026-07-15 10:00:00"


def _db(tmp_path):
    p = tmp_path / "w.db"
    sqlite3.connect(p).close()
    return str(p)


# ------------------------------------------------------------------ interface

def test_abc_refuses_instantiation():
    try:
        ia.QuoteSource()  # type: ignore[abstract]
        raise AssertionError("abstract QuoteSource must not instantiate")
    except TypeError:
        pass


def test_null_source_conforms_and_is_empty():
    src = ia.NullSource()
    assert src.snapshot(["TESTCO", "OTHER"]) == []
    assert src.licence_class == "personal-broker"
    assert src.name == "NullSource"


def test_t0lite_stub_declared_not_wired():
    t0 = ia.T0LiteSource()
    assert t0.snapshot(["X"]) == []
    assert t0.wired is False
    assert t0.licence_class == "public-archive"  # prelim files are NSE public archive


# ------------------------------------------------------------------ window store

def test_store_window_roundtrip_and_validation(tmp_path):
    db = _db(tmp_path)
    rows = [
        {"symbol": "TESTCO", "ts_utc": "2026-07-15 09:59:00", "ltp": 101.5, "vol": 10},
        {"symbol": "TESTCO", "ts_utc": "2026-07-15 09:58:00", "ltp": 101.0},
        {"symbol": "", "ts_utc": "2026-07-15 09:59:00", "ltp": 1.0},        # invalid: dropped
        {"symbol": "X", "ts_utc": "", "ltp": 1.0},                          # invalid: dropped
    ]
    assert ia.store(rows, db_path=db, max_age_min=10**6) == 2
    got = ia.window("TESTCO", minutes=120, db_path=db, now_utc=NOW)
    assert [r["ltp"] for r in got] == [101.0, 101.5]  # oldest first
    assert got[-1]["vol"] == 10 and got[0]["vol"] is None


def test_prune_bounds_the_window(tmp_path):
    db = _db(tmp_path)
    ia.store([
        {"symbol": "TESTCO", "ts_utc": "2026-07-15 09:59:00", "ltp": 101.5},
        {"symbol": "TESTCO", "ts_utc": "2026-07-15 01:00:00", "ltp": 99.0},
    ], db_path=db, max_age_min=10**6)
    dropped = ia.prune(db_path=db, max_age_min=480, now_utc=NOW)
    assert dropped == 1
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM intraday_window").fetchone()[0] == 1
    con.close()


def test_store_autoprunes(tmp_path):
    db = _db(tmp_path)
    # a store call with a tight max_age must not let stale rows accumulate
    ia.store([{"symbol": "A", "ts_utc": "2020-01-01 00:00:00", "ltp": 1.0}],
             db_path=db, max_age_min=60)
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM intraday_window").fetchone()[0] == 0
    con.close()


def test_ingest_swallows_source_failure(tmp_path):
    class Broken(ia.QuoteSource):
        def snapshot(self, symbols):
            raise RuntimeError("feed down")

    assert ia.ingest(Broken(), ["TESTCO"], db_path=_db(tmp_path)) == 0


# ------------------------------------------------------------------ licence boundary

def test_manifest_row_declares_personal_broker():
    feed = fm.FEEDS["intraday_seam"]
    assert feed.licence_class == "personal-broker"
    assert feed.licence_class in fm.RESTRICTED_LICENCE_CLASSES
    assert feed.module == "src/automation/intraday_adapter.py"
    assert "intraday_window" in feed.tables
    assert fm.MIN_FEEDS >= 22, "ratchet must include the seam row"


def test_no_public_surface_references_the_seam():
    """Mirror of the LANE-C licence gate, seam-specific: src/web must not import
    or reference intraday_adapter at all (OFF public surfaces by construction)."""
    web = REPO / "src" / "web"
    offenders = [p.name for p in web.glob("*.py")
                 if "intraday_adapter" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not offenders, f"public surface references the personal-broker seam: {offenders}"


def test_no_kite_wiring_present():
    src = (REPO / "src" / "automation" / "intraday_adapter.py").read_text(encoding="utf-8")
    low = src.lower()
    for marker in ("kiteconnect", "api_key", "access_token", "zerodha"):
        assert marker not in low, f"v1 must carry no broker wiring: found {marker!r}"


def test_writes_only_its_own_table():
    src = (REPO / "src" / "automation" / "intraday_adapter.py").read_text(encoding="utf-8")
    import re
    writes = set(re.findall(r"(?:INSERT (?:OR REPLACE )?INTO|DELETE FROM|UPDATE)\s+([a-z_]+)", src))
    assert writes == {"intraday_window"}, f"seam may only touch its own table, saw: {writes}"
