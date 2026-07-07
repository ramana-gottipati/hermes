"""Security master — point-in-time survivorship + rename stitching + continuity breaks.

The DVPT picking-strategy backtest must not cheat with hindsight: it can only
consider a stock that was *actually listed and tradeable* on the signal date, it
must follow a company across a symbol RENAME (ZOMATO→ETERNAL) as one continuous
security, and it must know when a DEMERGER / MERGER broke price-and-identity
continuity (so a scheme-of-arrangement gap is never mistaken for a return). This
module builds that spine. (docs/dvpt-picking-strategy-design.md §13 — the
"Vedanta problem".)

What it derives, all from data already on the box:
  - security_master  : one row per equity symbol ever seen in the bhav archive —
        first/last trade date, days traded, currently-listed + recently-traded
        flags, status, and (where known) ISIN / company / listing date. Built from
        the RAW ``bhavcopy_rows`` (NOT ``nse_equity_list``, which is a *current*
        snapshot and would re-introduce survivorship bias by dropping delisted
        names — the whole point is to keep them).
  - security_events  : continuity-BREAKING corporate events (demerger / merger /
        amalgamation / scheme) per symbol, classified from ``corporate_actions``.
        Splits & bonuses are deliberately excluded — they preserve continuity and
        are already handled by ``adjust.py`` on the price side.
  - security_renames : old_symbol → new_symbol. Auto-confirmed only where two
        symbols share an ISIN with non-overlapping date ranges (a clean handover);
        overlaps are kept as unconfirmed candidates. The authoritative NSE
        symbol-change feed can be loaded with ``--load-renames``.

Honest about its inputs: NSE's ``sec_bhavdata_full`` carries no ISIN (the bhav
``isin`` column is usually NULL), so auto-rename coverage leans on
``nse_equity_list`` (current names only) until a symbol-change feed is ingested —
the run logs exactly how much it could resolve.

Self-contained (the ``capture.py`` / ``rrg.py`` pattern): OWNS its three tables,
never edits ``db.py``. Full idempotent recompute — re-derivable from the raw
archive (Doctrine C). Pure SQL + arithmetic, no LLM.

Run:        python -m src.automation.security_master
Self-check: python -m src.automation.security_master --selftest
Inspect:    python -m src.automation.security_master --symbol RELIANCE
Load NSE symbol-change CSV: python -m src.automation.security_master --load-renames change.csv
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from datetime import date, timedelta
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.security_master")

# Equity series in the bhav archive (mainboard). EQ = normal, BE = trade-to-trade,
# BZ = surveillance — a name often slides EQ→BE→BZ→delist, so all three keep the
# delisted tail. SME series (SM/ST) are a different universe and excluded.
EQUITY_SERIES = ("EQ", "BE", "BZ")

# A symbol counts as "recently traded" (still alive) if its last bhav row is within
# this many calendar days of the latest archived trading day.
ACTIVE_GAP_DAYS = 20

# A rename auto-confirm additionally requires the handover gap (old symbol's LAST
# trade → new symbol's FIRST trade) to be at most this many days. A multi-year gap
# on a shared ISIN is almost always ISIN RECYCLING (a delisted scrip's ISIN reissued
# to a different company), not a rename — the LTI→LTM false-edge class (last trade
# 2022-12, "effective" 2026-02). Over the cap → kept as an unconfirmed candidate.
MAX_RENAME_GAP_DAYS = 400


# ── pure helpers ──────────────────────────────────────────────────────────────
def _day_gap(a: Optional[str], b: Optional[str]) -> Optional[int]:
    """Whole days from ISO date ``a`` to ``b`` (b − a); None if either is missing/unparseable."""
    if not a or not b:
        return None
    try:
        return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days
    except ValueError:
        return None


def classify_event(action_type: Optional[str], details: Optional[str]) -> Optional[str]:
    """Map a corporate action to a continuity-BREAKING event type, or None.

    Order matters: 'demerger' contains 'merg', so demerger/spin-off is tested
    before merger. Splits/bonuses/dividends/rights return None (handled elsewhere)."""
    t = f"{action_type or ''} {details or ''}".lower()
    if "demerg" in t or "spin-off" in t or "spin off" in t:
        return "DEMERGER"
    if "amalgam" in t:
        return "AMALGAMATION"
    if "merg" in t:
        return "MERGER"
    if "scheme of arrang" in t:
        return "SCHEME"
    return None


def _minus_days(iso: Optional[str], n: int) -> Optional[str]:
    if not iso:
        return None
    try:
        return (date.fromisoformat(iso[:10]) - timedelta(days=n)).isoformat()
    except Exception:
        return None


def _latest_trade_date(conn) -> Optional[str]:
    r = conn.execute("SELECT MAX(trade_date) m FROM bhavcopy_dates").fetchone()
    if r and r["m"]:
        return r["m"]
    r = conn.execute("SELECT MAX(trade_date) m FROM bhavcopy_rows").fetchone()
    return r["m"] if (r and r["m"]) else None


# ── storage (owns its own tables) ─────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS security_master (
    symbol           TEXT PRIMARY KEY,
    first_date       TEXT,
    last_date        TEXT,
    n_days           INTEGER,
    isin             TEXT,
    company_name     TEXT,
    listing_date     TEXT,
    currently_listed INTEGER DEFAULT 0,
    recently_traded  INTEGER DEFAULT 0,
    status           TEXT,
    instrument_class TEXT,          -- EQUITY | FUND (ETF / MF unit; data-postmortem 2026-07-07)
    computed_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_secm_isin  ON security_master(isin);
CREATE INDEX IF NOT EXISTS idx_secm_dates ON security_master(first_date, last_date);

CREATE TABLE IF NOT EXISTS security_events (
    symbol     TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ex_date    TEXT NOT NULL,
    details    TEXT,
    source     TEXT,
    PRIMARY KEY (symbol, event_type, ex_date)
);
CREATE INDEX IF NOT EXISTS idx_secev_sym ON security_events(symbol, ex_date);

CREATE TABLE IF NOT EXISTS security_renames (
    old_symbol     TEXT NOT NULL,
    new_symbol     TEXT NOT NULL,
    effective_date TEXT,
    isin           TEXT,
    source         TEXT,
    confirmed      INTEGER DEFAULT 0,
    PRIMARY KEY (old_symbol, new_symbol)
);
CREATE INDEX IF NOT EXISTS idx_secrn_new ON security_renames(new_symbol);
"""


def compute_and_store(conn=None) -> dict:
    """Rebuild the survivorship spine + events + ISIN-confirmed renames from the
    raw archive. Idempotent (full DELETE+INSERT). Returns a stats dict. Manages
    its own connection if none is given."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        try:                                             # pre-existing DBs: add the class column
            conn.execute("ALTER TABLE security_master ADD COLUMN instrument_class TEXT")
        except Exception:  # noqa: BLE001 — already present
            pass
        latest = _latest_trade_date(conn)
        active_floor = _minus_days(latest, ACTIVE_GAP_DAYS)

        # current listing snapshot (current names only): symbol -> (isin, company, listing)
        listed: dict = {}
        for r in conn.execute(
                "SELECT symbol, isin, company_name, listing_date FROM nse_equity_list"):
            listed[r["symbol"]] = (r["isin"], r["company_name"], r["listing_date"])

        # FUND identification (the ETF-in-EQ-series exclusion): the live exchange ETF list
        # (nse_etf_list, refreshed by equity_list.run_etfs) is the POSITIVE id — it covers the
        # blank-ISIN polluters (MONIFTY500, GROWWSLVR, NV20...). INF-prefix ISINs (mutual-fund
        # instruments) cover DELISTED/renamed fund tickers the live list no longer carries. The
        # name net stays deliberately tiny — endswith-BEES / contains-ETF only; broader patterns
        # are the documented trap (GOLD% would hit GOLDIAM, the real jeweller).
        try:
            etf_syms = {r[0] for r in conn.execute("SELECT symbol FROM nse_etf_list")}
        except Exception:  # noqa: BLE001 — list not fetched yet (laptop / first run)
            etf_syms = set()

        # survivorship spine from the RAW archive (KEEPS delisted names)
        series_ph = ",".join("?" * len(EQUITY_SERIES))
        spine = conn.execute(
            f"SELECT symbol, MIN(trade_date) f, MAX(trade_date) l, "
            f"       COUNT(DISTINCT trade_date) n, MAX(isin) bisin "
            f"FROM bhavcopy_rows WHERE series IN ({series_ph}) "
            f"GROUP BY symbol", EQUITY_SERIES).fetchall()

        rows = []
        isin_map: dict = {}     # isin -> [(symbol, first, last), ...]
        bhav_isin_cov = 0
        for r in spine:
            sym, first, last, n = r["symbol"], r["f"], r["l"], r["n"]
            l_isin, company, listing = listed.get(sym, (None, None, None))
            if r["bisin"]:
                bhav_isin_cov += 1
            isin = l_isin or r["bisin"]
            currently_listed = 1 if sym in listed else 0
            recently = 1 if (active_floor and last and last >= active_floor) else 0
            # status = TRADING recency, not listing state (currently_listed carries that axis).
            # INACTIVE + currently_listed=1 is therefore a real, expected combination: a
            # listed-but-SUSPENDED name (in the equity list, no trades for >ACTIVE_GAP_DAYS —
            # e.g. KALYANI, last trade 2025-07-04). Do not "fix" it as a contradiction.
            status = "ACTIVE" if recently else "INACTIVE"
            iclass = ("FUND" if (sym in etf_syms or str(isin or "").startswith("INF")
                                 or sym.endswith("BEES") or "ETF" in sym)
                      else "EQUITY")
            rows.append((sym, first, last, n, isin, company, listing,
                         currently_listed, recently, status, iclass))
            if isin:
                isin_map.setdefault(isin, []).append((sym, first, last))

        conn.execute("DELETE FROM security_master")
        conn.executemany(
            "INSERT OR REPLACE INTO security_master "
            "(symbol, first_date, last_date, n_days, isin, company_name, listing_date, "
            " currently_listed, recently_traded, status, instrument_class) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows)

        # continuity-breaking corporate events
        conn.execute("DELETE FROM security_events")
        ev = []
        for r in conn.execute(
                "SELECT symbol, action_type, ex_date, details, source FROM corporate_actions"):
            et = classify_event(r["action_type"], r["details"])
            if et and r["ex_date"]:
                ev.append((r["symbol"], et, r["ex_date"], r["details"], r["source"]))
        conn.executemany(
            "INSERT OR REPLACE INTO security_events "
            "(symbol, event_type, ex_date, details, source) VALUES (?,?,?,?,?)", ev)

        # auto-confirm renames via shared ISIN + clean (non-overlapping) handover.
        # Preserve any manually/feed-loaded renames (only re-derive the isin-sourced ones).
        conn.execute("DELETE FROM security_renames WHERE source LIKE 'isin%'")
        ren = []
        for isin, lst in isin_map.items():
            if len(lst) < 2:
                continue
            lst.sort(key=lambda x: x[1] or "")          # by first_date
            pairs = [((osym, _of, ol), (nsym, nf, _nl))
                     for (osym, _of, ol), (nsym, nf, _nl) in zip(lst, lst[1:])
                     if osym != nsym]
            if not pairs:
                continue
            # CL-MDC-13: auto-confirm a rename ONLY when the FULL chain for this
            # ISIN is a clean, strictly non-overlapping handover. With >2 symbols
            # on one ISIN, judging each consecutive pair in isolation can stitch a
            # tidy B→C link onto an ambiguous A→B overlap and mis-attribute history.
            # If any link overlaps, the whole chain is suspect → all candidates.
            chain_clean = all(
                (ol and nf and ol <= nf)
                for (_osym, _of, ol), (_nsym, nf, _nl) in pairs
            )
            for (osym, _of, ol), (nsym, nf, _nl) in pairs:
                gap = _day_gap(ol, nf)
                gap_ok = gap is not None and gap <= MAX_RENAME_GAP_DAYS
                if chain_clean and gap_ok:
                    ren.append((osym, nsym, nf, isin, "isin", 1))
                else:
                    src = "isin-gap" if (chain_clean and not gap_ok) else "isin-overlap"
                    ren.append((osym, nsym, nf, isin, src, 0))
        conn.executemany(
            "INSERT OR REPLACE INTO security_renames "
            "(old_symbol, new_symbol, effective_date, isin, source, confirmed) "
            "VALUES (?,?,?,?,?,?)", ren)

        if own:
            conn.commit()

        stats = {
            "securities": len(rows),
            "active": sum(x[8] for x in rows),
            "delisted_or_inactive": sum(1 for x in rows if not x[8]),
            "funds": sum(1 for x in rows if x[10] == "FUND"),
            "events": len(ev),
            "renames_confirmed": sum(1 for x in ren if x[5] == 1),
            "rename_candidates": sum(1 for x in ren if x[5] == 0),
            "bhav_isin_coverage": bhav_isin_cov,
            "latest": latest,
        }
        log.info("security_master: %s", stats)
        return stats
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── read API (what the backtest consumes) ─────────────────────────────────────
def _with_conn(fn, conn):
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        return fn(conn)
    finally:
        if own:
            cm.__exit__(None, None, None)


def get(symbol: str, conn=None) -> Optional[dict]:
    """The security-master row for one symbol (or None)."""
    def q(c):
        r = c.execute("SELECT * FROM security_master WHERE symbol=?", (symbol,)).fetchone()
        return dict(r) if r else None
    return _with_conn(q, conn)


def universe_on(d: str, conn=None) -> list:
    """Survivorship-correct universe: every symbol that was listed & tradeable as
    of date `d` (first_date <= d <= last_date). This is the set the backtest is
    allowed to pick from on date `d` — no hindsight, delisted names included."""
    def q(c):
        return [r["symbol"] for r in c.execute(
            "SELECT symbol FROM security_master WHERE first_date <= ? AND last_date >= ?",
            (d, d)).fetchall()]
    return _with_conn(q, conn)


def events_for(symbol: str, conn=None) -> list:
    """All continuity-breaking events for a symbol, oldest first."""
    def q(c):
        return [dict(r) for r in c.execute(
            "SELECT * FROM security_events WHERE symbol=? ORDER BY ex_date", (symbol,)).fetchall()]
    return _with_conn(q, conn)


def has_break_between(symbol: str, start: str, end: str, conn=None) -> bool:
    """True if a demerger/merger/scheme broke continuity in (start, end] — so the
    backtest can flag or skip that holding window."""
    def q(c):
        r = c.execute(
            "SELECT COUNT(*) n FROM security_events WHERE symbol=? AND ex_date > ? AND ex_date <= ?",
            (symbol, start, end)).fetchone()
        return (r["n"] or 0) > 0
    return _with_conn(q, conn)


def fund_symbols(conn=None) -> set:
    """Every symbol classified FUND (ETF / MF unit) — the survivorship-aware exclusion set
    for research scans: 'delisted companies yes, funds no', which the live-equity-list
    idiom (`IN nse_equity_list`) cannot express (it also drops delisted companies)."""
    def q(c):
        try:
            return {r[0] for r in c.execute(
                "SELECT symbol FROM security_master WHERE instrument_class='FUND'")}
        except Exception:  # noqa: BLE001 — column absent (pre-migration DB)
            return set()
    return _with_conn(q, conn)


def canonical(symbol: str, conn=None) -> str:
    """Follow confirmed renames forward to the current symbol (cycle-guarded)."""
    def q(c):
        cur, seen = symbol, set()
        while cur not in seen:
            seen.add(cur)
            nxt = c.execute(
                "SELECT new_symbol FROM security_renames "
                "WHERE old_symbol=? AND confirmed=1 ORDER BY effective_date DESC LIMIT 1",
                (cur,)).fetchone()
            if not nxt:
                break
            cur = nxt["new_symbol"]
        return cur
    return _with_conn(q, conn)


def aliases_on(conn, symbol: str) -> list:
    """RO-SAFE: every symbol this entity has traded under — the canonical (current)
    symbol plus every CONFIRMED prior name in its rename chain, in BOTH directions.
    Use it so a cross-DB archive read for the CURRENT symbol still finds history filed
    under an OLD one (AKZOINDIA↔JSWDULUX, LTI↔LTM). Assumes the tables already exist
    (no schema init) so it is safe on a ``mode=ro`` handle; positional row access so it
    needs no ``row_factory``; degrades to ``[symbol]`` on any error."""
    s = (symbol or "").upper().strip()
    if not s:
        return []
    try:
        cur, seen = s, {s}                                    # forward → canonical
        while True:
            nxt = conn.execute(
                "SELECT new_symbol FROM security_renames "
                "WHERE old_symbol=? AND confirmed=1 ORDER BY effective_date DESC LIMIT 1",
                (cur,)).fetchone()
            if not nxt or nxt[0] in seen:
                break
            cur = nxt[0]
            seen.add(cur)
        out, frontier = {cur, s}, [cur]                       # backward BFS over the chain
        while frontier:
            node = frontier.pop()
            for r in conn.execute(
                    "SELECT old_symbol FROM security_renames "
                    "WHERE new_symbol=? AND confirmed=1", (node,)).fetchall():
                if r[0] not in out:
                    out.add(r[0])
                    frontier.append(r[0])
        return sorted(out)
    except sqlite3.Error:
        return [s]


def aliases(symbol: str, conn=None) -> list:
    """``aliases_on`` for the RW / standalone caller (opens + schema-inits its own
    connection). Read-only callers already holding a ``mode=ro`` handle should call
    ``aliases_on(conn, symbol)`` directly (it skips schema init)."""
    return _with_conn(lambda c: aliases_on(c, symbol), conn)


def load_renames(csv_path: str, conn=None) -> int:
    """Ingest the authoritative NSE symbol-change CSV (tolerant header detection;
    looks for columns containing 'old'/'new' symbol + an 'applicable'/'date' col).
    Stored confirmed, source='nse-feed'."""
    import csv

    def q(c):
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            rdr = csv.reader(fh)
            header = next(rdr, [])
            hl = [h.strip().lower() for h in header]

            def find(*keys):
                for i, h in enumerate(hl):
                    if any(k in h for k in keys):
                        return i
                return None

            oi, ni = find("old"), find("new")
            di = find("applicable", "effective", "date", "from")
            if oi is None or ni is None:
                raise ValueError(f"could not find old/new symbol columns in header {header}")
            ren = []
            for row in rdr:
                if len(row) <= max(oi, ni):
                    continue
                old, new = row[oi].strip(), row[ni].strip()
                if not old or not new or old == new:
                    continue
                eff = row[di].strip() if (di is not None and len(row) > di) else None
                ren.append((old, new, eff, None, "nse-feed", 1))
            c.executemany(
                "INSERT OR REPLACE INTO security_renames "
                "(old_symbol, new_symbol, effective_date, isin, source, confirmed) "
                "VALUES (?,?,?,?,?,?)", ren)
            c.connection.commit()
            log.info("loaded %d renames from %s", len(ren), csv_path)
            return len(ren)
    return _with_conn(q, conn)


# ── self-check (synthetic in-memory DB — no real data needed) ─────────────────
def _selftest() -> None:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT, isin TEXT);
        CREATE TABLE bhavcopy_dates (trade_date TEXT PRIMARY KEY);
        CREATE TABLE corporate_actions (symbol TEXT, action_type TEXT, ex_date TEXT,
                                        details TEXT, source TEXT);
        CREATE TABLE nse_equity_list (symbol TEXT PRIMARY KEY, isin TEXT,
                                      company_name TEXT, listing_date TEXT);
    """)
    # bhav: RELIANCE (active), DELISTO (delisted 2016), ZOMATO→ETERNAL (shared ISIN handover)
    bhav = [
        ("RELIANCE", "2015-01-05", "EQ", None), ("RELIANCE", "2020-06-01", "EQ", None),
        ("RELIANCE", "2026-06-20", "EQ", None),
        ("DELISTO",  "2012-03-01", "EQ", None), ("DELISTO",  "2016-09-30", "EQ", None),
        ("ZOMATO",   "2021-07-23", "EQ", "INEZOM01015"), ("ZOMATO", "2023-03-01", "EQ", "INEZOM01015"),
        ("ETERNAL",  "2023-09-01", "EQ", "INEZOM01015"), ("ETERNAL", "2026-06-19", "EQ", "INEZOM01015"),
        # OLDGAP→NEWGAP share an ISIN but hand over across a MULTI-YEAR gap (ISIN recycled) → must NOT auto-confirm
        ("OLDGAP",   "2018-01-05", "EQ", "INEGAP01010"), ("OLDGAP",  "2020-01-01", "EQ", "INEGAP01010"),
        ("NEWGAP",   "2025-06-01", "EQ", "INEGAP01010"), ("NEWGAP",  "2026-06-19", "EQ", "INEGAP01010"),
        # fund instruments trading in series EQ — must classify FUND, never EQUITY
        ("MONIFTY500", "2024-01-05", "EQ", None),          # blank ISIN → caught by the ETF list
        ("GOLDBEES",   "2020-01-05", "EQ", None),          # name net (endswith BEES)
        ("DEADFUND",   "2016-01-05", "EQ", "INF204KB1882"),  # delisted fund → INF-prefix ISIN
        ("GOLDIAM",    "2019-01-05", "EQ", None),          # the documented trap: a REAL equity
    ]
    conn.executemany("INSERT INTO bhavcopy_rows VALUES (?,?,?,?)", bhav)
    conn.execute("INSERT INTO bhavcopy_dates VALUES ('2026-06-22')")
    conn.executemany("INSERT INTO corporate_actions VALUES (?,?,?,?,?)", [
        ("RELIANCE", "DEMERGER", "2023-07-20", "Demerger of Jio Financial Services", "nse"),
        ("RELIANCE", "DIVIDEND", "2024-08-19", "Final Dividend Rs 10", "nse"),     # must be ignored
    ])
    conn.executemany("INSERT INTO nse_equity_list VALUES (?,?,?,?)", [
        ("RELIANCE", "INE002A01018", "Reliance Industries", "1995-01-01"),
        ("ETERNAL",  "INEZOM01015",  "Eternal Ltd",         "2021-07-23"),
        ("GOLDIAM",  "INE025B01025", "Goldiam International", "1995-01-01"),
    ])
    conn.execute("CREATE TABLE nse_etf_list (symbol TEXT PRIMARY KEY, name TEXT, assets TEXT, snapshot_date TEXT)")
    conn.execute("INSERT INTO nse_etf_list VALUES ('MONIFTY500','Motilal Nifty 500 ETF','Equity','2026-07-07')")

    stats = compute_and_store(conn=conn)

    rel = get("RELIANCE", conn=conn)
    assert rel and rel["status"] == "ACTIVE" and rel["first_date"] == "2015-01-05", rel
    assert rel["isin"] == "INE002A01018", "should enrich ISIN from nse_equity_list"
    deli = get("DELISTO", conn=conn)
    assert deli and deli["status"] == "INACTIVE" and deli["currently_listed"] == 0, deli

    # survivorship: the universe must change with the date
    u2016 = set(universe_on("2016-01-01", conn=conn))
    assert {"RELIANCE", "DELISTO"} <= u2016 and "ETERNAL" not in u2016, u2016
    u2025 = set(universe_on("2025-01-01", conn=conn))
    assert "RELIANCE" in u2025 and "ETERNAL" in u2025, u2025
    assert "DELISTO" not in u2025 and "ZOMATO" not in u2025, "delisted/renamed must drop out"

    # continuity breaks
    assert has_break_between("RELIANCE", "2023-01-01", "2023-12-31", conn=conn), "demerger missed"
    assert not has_break_between("RELIANCE", "2020-01-01", "2020-12-31", conn=conn), "false break"
    assert events_for("RELIANCE", conn=conn)[0]["event_type"] == "DEMERGER"

    # rename stitching via shared ISIN (non-overlapping handover)
    assert canonical("ZOMATO", conn=conn) == "ETERNAL", "ZOMATO should resolve to ETERNAL"
    assert canonical("RELIANCE", conn=conn) == "RELIANCE"
    assert stats["renames_confirmed"] >= 1 and stats["events"] == 1, stats

    # reverse aliases: a read for the CURRENT symbol must reach its OLD names (archive keyed old)
    assert set(aliases("ETERNAL", conn=conn)) == {"ZOMATO", "ETERNAL"}, aliases("ETERNAL", conn=conn)
    assert set(aliases("ZOMATO", conn=conn)) == {"ZOMATO", "ETERNAL"}, "alias set is chain-wide either way"
    assert aliases("RELIANCE", conn=conn) == ["RELIANCE"], "no renames → just itself"
    # ISIN-recycling guard: a multi-year handover gap must NOT auto-confirm (LTI→LTM class)
    assert canonical("OLDGAP", conn=conn) == "OLDGAP", "a >400d ISIN gap must stay an unconfirmed candidate"
    assert set(aliases("NEWGAP", conn=conn)) == {"NEWGAP"}, "an unconfirmed gap edge must not join the alias set"

    # instrument_class (the ETF-in-EQ-series exclusion): all three FUND routes + the GOLDIAM trap
    fs = fund_symbols(conn=conn)
    assert fs == {"MONIFTY500", "GOLDBEES", "DEADFUND"}, fs
    assert get("MONIFTY500", conn=conn)["instrument_class"] == "FUND", "ETF-list route"
    assert get("GOLDBEES", conn=conn)["instrument_class"] == "FUND", "BEES name-net route"
    assert get("DEADFUND", conn=conn)["instrument_class"] == "FUND", "INF-isin route (delisted fund)"
    assert get("GOLDIAM", conn=conn)["instrument_class"] == "EQUITY", "GOLD% trap: real equity stays EQUITY"
    assert get("RELIANCE", conn=conn)["instrument_class"] == "EQUITY"
    assert stats["funds"] == 3, stats

    print(f"security_master selftest: OK  {stats}")


def main() -> None:
    p = argparse.ArgumentParser(description="Build the security master (survivorship + renames + breaks).")
    p.add_argument("--selftest", action="store_true", help="synthetic in-memory validation")
    p.add_argument("--symbol", help="print the master row + events + canonical for one symbol")
    p.add_argument("--load-renames", metavar="CSV", help="ingest an NSE symbol-change CSV")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        _selftest()
        return
    if args.symbol:
        sym = args.symbol.strip().upper()
        print(f"{sym}: {get(sym)}")
        print(f"  canonical → {canonical(sym)}")
        for e in events_for(sym):
            print(f"  event: {e['event_type']} {e['ex_date']} — {e['details']}")
        return
    if args.load_renames:
        n = load_renames(args.load_renames)
        print(f"loaded {n} renames")
        return

    stats = compute_and_store()
    print(f"security_master: {stats}")


if __name__ == "__main__":
    main()
