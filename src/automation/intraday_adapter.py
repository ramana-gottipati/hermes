"""Real-time seam INTERFACE v1 (D134 plan §4-I, layer L1) — adapter only, no live feed.

The seam exists so a future personal-broker quote source (e.g. a Kite personal
API key — Ramana's PAID activation decision, deliberately NOT wired here) can
plug in WITHOUT touching any other module. Until then the platform stays EOD.

Contract:
  * `QuoteSource` — the abstract interface: `snapshot(symbols)` returns
    normalized rows `{symbol, ts_utc, ltp, vol}` (vol optional, None ok).
  * The rolling window store — raw ticks NEVER enter the main hermes tables
    (space doctrine): they land in the OWN bounded table `intraday_window`,
    pruned by age on every store (default 480 min ≈ one session). Nothing here
    is a time series to keep — the EOD bhavcopy remains the only durable tape.
  * `NullSource` — the default: always empty (the platform's current honest
    real-time capability).
  * `T0LiteSource` — a ₹0 STUB for NSE's free EOD-preliminary files
    (published ~15:45–16:15 IST, hours before the final bhavcopy): declared but
    NOT wired in v1; `snapshot()` returns [] and `wired` is False.

Licence boundary (the point of doing this now): the feed is declared in
`feed_manifest.FEEDS["intraday_seam"]` with licence_class='personal-broker' —
a RESTRICTED class — so the LANE-C licence gate (tests/test_feed_manifest.py)
machine-forbids any src/web reference to this module. A personal entitlement
can never leak onto a public surface BY CONSTRUCTION, not by convention.

CLI: --selftest (hermetic temp DB).
"""

from __future__ import annotations

import abc
import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

HERMES_DB = "/opt/hermes/data/hermes.db"
DEFAULT_MAX_AGE_MIN = 480  # one trading session; the window is a buffer, not an archive

_REQUIRED_KEYS = ("symbol", "ts_utc", "ltp")


# ------------------------------------------------------------------ the interface

class QuoteSource(abc.ABC):
    """Abstract quote source. Implementations normalize to the seam's row shape."""

    #: every source declares its licence class; the manifest row must agree.
    licence_class: str = "personal-broker"

    @property
    def name(self) -> str:
        return type(self).__name__

    @abc.abstractmethod
    def snapshot(self, symbols: Iterable[str]) -> list[dict]:
        """Return normalized rows {symbol, ts_utc, ltp, vol?} for the given symbols.

        MUST return [] rather than raise on an unavailable feed — the seam is an
        optional enhancement; EOD flows never depend on it.
        """


class NullSource(QuoteSource):
    """The default source: no real-time entitlement — always empty."""

    def snapshot(self, symbols: Iterable[str]) -> list[dict]:  # noqa: ARG002
        return []


class T0LiteSource(QuoteSource):
    """STUB for the ₹0 'T0 lite' path — NSE EOD-preliminary files (~15:45–16:15 IST).

    Not wired in v1 (no fetcher): the class documents the intended shape so the
    evening-picture upgrade is a drop-in later. `wired` stays False until a real
    fetch lands (with its own knowable_rule note in the manifest).
    """

    licence_class = "public-archive"  # prelim files are NSE public archive, unlike broker ticks
    wired: bool = False

    def snapshot(self, symbols: Iterable[str]) -> list[dict]:  # noqa: ARG002
        return []


# ------------------------------------------------------------------ window store

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS intraday_window (
               symbol  TEXT NOT NULL,
               ts_utc  TEXT NOT NULL,
               ltp     REAL NOT NULL,
               vol     INTEGER,
               PRIMARY KEY (symbol, ts_utc)
           )""")


def _valid(row: dict) -> bool:
    return all(row.get(k) not in (None, "") for k in _REQUIRED_KEYS)


def store(rows: list[dict], *, conn: Optional[sqlite3.Connection] = None,
          db_path: str = HERMES_DB, max_age_min: int = DEFAULT_MAX_AGE_MIN) -> int:
    """Upsert normalized rows into the bounded window, then prune by age.

    Invalid rows (missing symbol/ts_utc/ltp) are dropped, not raised — a flaky
    source must never break the caller. Returns the number stored.
    """
    own = conn is None
    c = conn if conn is not None else sqlite3.connect(db_path, timeout=30)
    try:
        ensure_schema(c)
        kept = [r for r in rows or [] if _valid(r)]
        c.executemany(
            "INSERT OR REPLACE INTO intraday_window (symbol, ts_utc, ltp, vol) "
            "VALUES (?,?,?,?)",
            [(r["symbol"], r["ts_utc"], float(r["ltp"]), r.get("vol")) for r in kept])
        prune(conn=c, max_age_min=max_age_min)
        c.commit()
        return len(kept)
    finally:
        if own:
            c.close()


def prune(*, conn: Optional[sqlite3.Connection] = None, db_path: str = HERMES_DB,
          max_age_min: int = DEFAULT_MAX_AGE_MIN, now_utc: Optional[str] = None) -> int:
    """Delete window rows older than max_age_min. The bound that keeps the space
    doctrine honest — the window can never grow into an archive."""
    own = conn is None
    c = conn if conn is not None else sqlite3.connect(db_path, timeout=30)
    try:
        ensure_schema(c)
        now = (datetime.fromisoformat(now_utc) if now_utc
               else datetime.now(timezone.utc).replace(tzinfo=None))
        cutoff = (now - timedelta(minutes=int(max_age_min))).isoformat(sep=" ", timespec="seconds")
        cur = c.execute("DELETE FROM intraday_window WHERE ts_utc < ?", (cutoff,))
        if own:
            c.commit()
        return cur.rowcount
    finally:
        if own:
            c.close()


def window(symbol: str, minutes: int = 60, *, conn: Optional[sqlite3.Connection] = None,
           db_path: str = HERMES_DB, now_utc: Optional[str] = None) -> list[dict]:
    """The stored rows for `symbol` within the last `minutes`, oldest first."""
    own = conn is None
    c = conn if conn is not None else sqlite3.connect(db_path, timeout=30)
    try:
        ensure_schema(c)
        now = (datetime.fromisoformat(now_utc) if now_utc
               else datetime.now(timezone.utc).replace(tzinfo=None))
        cutoff = (now - timedelta(minutes=int(minutes))).isoformat(sep=" ", timespec="seconds")
        cur = c.execute(
            "SELECT symbol, ts_utc, ltp, vol FROM intraday_window "
            "WHERE symbol=? AND ts_utc >= ? ORDER BY ts_utc ASC", (symbol, cutoff))
        return [dict(zip(("symbol", "ts_utc", "ltp", "vol"), r)) for r in cur.fetchall()]
    finally:
        if own:
            c.close()


def ingest(source: QuoteSource, symbols: Iterable[str], *,
           conn: Optional[sqlite3.Connection] = None, db_path: str = HERMES_DB) -> int:
    """One snapshot -> window pass. Safe with any conforming source."""
    try:
        rows = source.snapshot(symbols) or []
    except Exception:
        rows = []  # a source must not break the caller; NullSource semantics on failure
    return store(rows, conn=conn, db_path=db_path)


# --------------------------------------------------------------------- selftest

def _selftest() -> int:
    import os
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + name)
        ok = ok and bool(cond)

    db = os.path.join(tempfile.mkdtemp(prefix="intraday_"), "w.db")
    now = "2026-07-15 10:00:00"
    fresh = {"symbol": "TESTCO", "ts_utc": "2026-07-15 09:59:00", "ltp": 101.5, "vol": 10}
    stale = {"symbol": "TESTCO", "ts_utc": "2026-07-15 01:00:00", "ltp": 99.0, "vol": 5}
    bad = {"symbol": "", "ts_utc": "2026-07-15 09:59:00", "ltp": 1.0}

    n = store([fresh, stale, bad], db_path=db, max_age_min=10**6)
    check("store keeps valid rows only", n == 2)
    prune(db_path=db, max_age_min=480, now_utc=now)
    got = window("TESTCO", minutes=120, db_path=db, now_utc=now)
    check("prune drops the stale tick", len(got) == 1 and got[0]["ltp"] == 101.5)
    check("NullSource empty", NullSource().snapshot(["TESTCO"]) == [])
    t0 = T0LiteSource()
    check("T0Lite stub declared, not wired", t0.snapshot(["X"]) == [] and t0.wired is False)
    check("ABC refuses instantiation", _abc_blocked())
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def _abc_blocked() -> bool:
    try:
        QuoteSource()  # type: ignore[abstract]
        return False
    except TypeError:
        return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Intraday seam interface (adapter only, no live feed).")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
