"""Band-lock streak detection (charter X-05) — names pinned at their daily price band.

WHAT: an EQ-series name is UPPER-LOCKED on day D when it closed AT its permitted daily
maximum — close == high AND close within tolerance of prev_close × (1 + band%) — i.e. the
buy queue outran the band; LOWER-LOCKED symmetrically at the down limit. A STREAK is a run
of consecutive same-direction locked trading days ending at the latest bhav date.

DATA + THE HONEST WINDOW: bands come from the D-03 security-wise feed (surveillance.py) —
`price_bands_current` is a one-day snapshot (DELETE+rewrite nightly) and `price_band_events`
is the append-only change log. The band a name carried ON A PAST DATE is therefore
RECONSTRUCTED (current state walked backwards through the change log): exact, but it only
reaches back to the feed's first captured day, FEED_BIRTH = 2026-07-07 (S83c). Locks before
that are invisible here BY CONSTRUCTION; the board deepens every trading day. Everything is
compute-on-read (space doctrine): the window is days-deep × ~2K EQ names — nothing persisted.

DESCRIPTIVE ONLY: no study exists on band-lock streaks in either direction (ledger checked,
S96c). The surveillance glossary's "queue-imbalance tell" stays a tell — any drift/return
claim needs its own pre-registered gate first. Locks are computed on AS-TRADED prices
(bhavcopy_rows raw OHLC): exchange bands apply to raw prices, never adjusted series.

Flag rule (single source): flagged_symbols() = names whose ACTIVE streak ≥ FLAG_MIN_STREAK
(2) trading days, either direction. The lens page shows every active lock (streak ≥ 1).
"""
from __future__ import annotations

import argparse
import logging
from typing import Optional

log = logging.getLogger("hermes.band_lock")

FEED_BIRTH = "2026-07-07"     # first captured band snapshot (S83c) — the reconstruction floor
FLAG_MIN_STREAK = 2           # active streak days that puts a name on the flags cohort
REL_TOL = 0.001               # 0.1% tolerance to the theoretical limit (tick rounding)
_EPS = 0.005                  # float equality for close==high / close==low (paisa scale)


def _band_num(b) -> Optional[float]:
    """'5' / '10.0' / 'No Band' / None -> float % or None (reuses the feed's convention)."""
    try:
        from src.automation.surveillance import _band_num as _sv
        return _sv(b)
    except Exception:                               # noqa: BLE001 — standalone fallback
        try:
            return float(str(b).strip())
        except (TypeError, ValueError):
            return None


# ── band-at-date reconstruction ──────────────────────────────────────────────

def band_on_date(conn, d: str) -> dict:
    """symbol -> numeric band %, as it stood on trading date `d` (EQ-relevant map).

    Reconstruction: start from the current snapshot; for any symbol with change events
    AFTER d, the band at d is the old_band of the FIRST such event (NULL old_band = the
    band was first SET after d → the symbol was unbanded at d). Returns {} for dates
    before FEED_BIRTH — the feed cannot see that far back, and pretending otherwise
    would fabricate history.
    """
    if str(d) < FEED_BIRTH:
        return {}
    out = {}
    for sym, band in conn.execute("SELECT symbol, band FROM price_bands_current"):
        n = _band_num(band)
        if n is not None:
            out[str(sym).strip().upper()] = n
    seen_rewind = set()
    for sym, old_band in conn.execute(
            "SELECT symbol, old_band FROM price_band_events WHERE as_of > ? "
            "ORDER BY as_of ASC", (str(d),)):
        s = str(sym).strip().upper()
        if s in seen_rewind:
            continue                    # only the FIRST event after d tells the state at d
        seen_rewind.add(s)
        n = _band_num(old_band)
        if n is None:
            out.pop(s, None)            # band was set after d — unbanded at d
        else:
            out[s] = n
    return out


# ── per-date lock detection ──────────────────────────────────────────────────

def locks_on_date(conn, d: str) -> dict:
    """symbol -> lock dict for trading date d: {dir: 'UP'|'DOWN', band, close, prev_close}."""
    bands = band_on_date(conn, d)
    if not bands:
        return {}
    out = {}
    # series filtered in PYTHON on purpose: the compound (trade_date AND series) predicate
    # lures SQLite onto idx_bhav_series (measured 3.2s/date on the 16GB DB); the date-only
    # form uses idx_bhav_date (4ms). Same rows, 800x faster.
    for sym, series, high, low, close, prev_close in conn.execute(
            "SELECT symbol, series, high, low, close, prev_close FROM bhavcopy_rows "
            "WHERE trade_date = ?", (str(d),)):
        if series != "EQ":
            continue
        s = str(sym).strip().upper()
        b = bands.get(s)
        if b is None or not prev_close or close is None or high is None or low is None:
            continue
        lim_up = prev_close * (1 + b / 100.0)
        lim_dn = prev_close * (1 - b / 100.0)
        up = abs(close - high) <= _EPS and close >= lim_up * (1 - REL_TOL)
        dn = abs(close - low) <= _EPS and close <= lim_dn * (1 + REL_TOL)
        if up and dn:                   # frozen flat at a tiny band — direction by sign
            up, dn = close >= prev_close, close < prev_close
        if up or dn:
            out[s] = {"dir": "UP" if up else "DOWN", "band": b,
                      "close": close, "prev_close": prev_close}
    return out


def trading_dates(conn, since: str) -> list:
    """Distinct bhav trade dates >= since, ascending — the calendar streaks walk on."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date >= ? "
        "ORDER BY trade_date", (str(since),))]


# ── streaks ──────────────────────────────────────────────────────────────────

def active_streaks(conn):
    """(streaks, latest_date). streaks = list of dicts for names locked on the LATEST
    trading date, streak counted backwards through consecutive same-direction locks
    (window floor = FEED_BIRTH). Sorted: longest first, then biggest |move|.

    Each: {symbol, dir, days, band, first_date, last_close, move_pct} where move_pct is
    the cumulative % move over the streak (vs the prev_close before its first lock day).
    """
    dates = trading_dates(conn, FEED_BIRTH)
    if not dates:
        return [], None
    latest = dates[-1]
    per_date = {d: locks_on_date(conn, d) for d in dates}
    today = per_date[latest]
    streaks = []
    for sym, info in today.items():
        days, first = 1, latest
        base_prev = info["prev_close"]
        for d in reversed(dates[:-1]):
            prior = per_date[d].get(sym)
            if not prior or prior["dir"] != info["dir"]:
                break
            days += 1
            first = d
            base_prev = prior["prev_close"]
        move = ((info["close"] / base_prev) - 1) * 100 if base_prev else None
        streaks.append({"symbol": sym, "dir": info["dir"], "days": days,
                        "band": info["band"], "first_date": first,
                        "last_close": info["close"],
                        "move_pct": round(move, 2) if move is not None else None})
    streaks.sort(key=lambda s: (-s["days"], -abs(s["move_pct"] or 0)))
    return streaks, latest


def flagged_symbols(conn):
    """(flags, as_of) — the single source every consumer reads (registry, cockpit, page).
    flags = [(symbol, streak_dict)] for ACTIVE streaks >= FLAG_MIN_STREAK; as_of = the
    latest bhav date the board is computed for (None when the window has no data yet)."""
    streaks, latest = active_streaks(conn)
    return [(s["symbol"], s) for s in streaks if s["days"] >= FLAG_MIN_STREAK], latest


# ── selftest (hermetic; mirrors tests/test_band_lock.py) ─────────────────────

def selftest() -> int:
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.executescript("""
    CREATE TABLE price_bands_current (as_of TEXT, symbol TEXT, series TEXT, band TEXT, remarks TEXT);
    CREATE TABLE price_band_events (as_of TEXT, symbol TEXT, series TEXT, old_band TEXT, new_band TEXT);
    CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT,
                                open REAL, high REAL, low REAL, close REAL, prev_close REAL);
    """)
    # LOCKY: 5%-band, upper-locked 3 straight days (close==high==+5% exactly)
    px = 100.0
    for d in ("2026-07-07", "2026-07-08", "2026-07-09"):
        nxt = round(px * 1.05, 2)
        c.execute("INSERT INTO bhavcopy_rows VALUES ('LOCKY', ?, 'EQ', ?, ?, ?, ?, ?)",
                  (d, px, nxt, px * 0.99, nxt, px))
        px = nxt
    c.execute("INSERT INTO price_bands_current VALUES ('2026-07-09','LOCKY','EQ','5','')")
    # DOWNY: 10%-band, lower-locked on the last day only
    c.execute("INSERT INTO bhavcopy_rows VALUES ('DOWNY','2026-07-09','EQ',200,201,180,180,200)")
    c.execute("INSERT INTO price_bands_current VALUES ('2026-07-09','DOWNY','EQ','10','')")
    # FREEBIRD: no band (F&O style) — closes at high, must NOT count
    c.execute("INSERT INTO bhavcopy_rows VALUES ('FREEBIRD','2026-07-09','EQ',50,55,49,55,50)")
    # SWITCHY: band was 20 on 07/08 (event says it changed 20->10 on 07-09); locked at +20% on 07-08
    c.execute("INSERT INTO bhavcopy_rows VALUES ('SWITCHY','2026-07-08','EQ',10,12,9.9,12,10)")
    c.execute("INSERT INTO bhavcopy_rows VALUES ('SWITCHY','2026-07-09','EQ',12,12.5,11,12.5,12)")
    c.execute("INSERT INTO price_bands_current VALUES ('2026-07-09','SWITCHY','EQ','10','')")
    c.execute("INSERT INTO price_band_events VALUES ('2026-07-09','SWITCHY','EQ','20','10')")

    bands_0708 = band_on_date(c, "2026-07-08")
    assert bands_0708.get("SWITCHY") == 20.0, f"reconstruction failed: {bands_0708.get('SWITCHY')}"
    assert bands_0708.get("LOCKY") == 5.0
    assert "FREEBIRD" not in bands_0708
    assert band_on_date(c, "2026-07-01") == {}, "pre-FEED_BIRTH must be empty"

    locks = locks_on_date(c, "2026-07-09")
    assert locks["LOCKY"]["dir"] == "UP" and locks["DOWNY"]["dir"] == "DOWN"
    assert "FREEBIRD" not in locks, "unbanded name must never lock"
    assert "SWITCHY" not in locks, "+4.2% on a 10% band is not a lock"
    assert locks_on_date(c, "2026-07-08").get("SWITCHY", {}).get("dir") == "UP", \
        "the +20% lock under the RECONSTRUCTED (pre-change) band must count"

    streaks, latest = active_streaks(c)
    by = {s["symbol"]: s for s in streaks}
    assert latest == "2026-07-09"
    assert by["LOCKY"]["days"] == 3 and by["LOCKY"]["dir"] == "UP"
    assert abs(by["LOCKY"]["move_pct"] - 15.76) < 0.1, by["LOCKY"]["move_pct"]  # 1.05^3-1
    assert by["DOWNY"]["days"] == 1

    flags, as_of = flagged_symbols(c)
    assert as_of == "2026-07-09"
    assert [s for s, _ in flags] == ["LOCKY"], f"only the >=2d streak flags: {flags}"
    print("band_lock selftest: OK (reconstruction · lock detection · streaks · flags)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Band-lock streak board (X-05) — descriptive only")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--show", action="store_true", help="print the live board")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.selftest:
        raise SystemExit(selftest())
    if args.show:
        from src.core.db import get_conn
        with get_conn() as conn:
            streaks, latest = active_streaks(conn)
            print(f"as of {latest} — {len(streaks)} active locks "
                  f"({sum(1 for s in streaks if s['days'] >= FLAG_MIN_STREAK)} flagged >= {FLAG_MIN_STREAK}d)")
            for s in streaks[:40]:
                print(f"  {s['symbol']:14} {s['dir']:4} {s['days']}d  band {s['band']:>4}%  "
                      f"close {s['last_close']:>9}  move {s['move_pct']:+.1f}%  since {s['first_date']}")


if __name__ == "__main__":
    main()
