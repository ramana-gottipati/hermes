"""launchpad_signals — nightly materialisation of the Launchpad precursor scan.

The Launchpad lens (D56-validated explosive-move precursors: MOM_CONT / COILED /
PULLBACK over the liquid >=Rs5cr universe) was computed RENDER-TIME by
src/web/cockpit.render_launchpad — ~9s per page view (130d of bhavcopy history for
~1k candidates + per-symbol feature math, on EVERY request). That broke both the
pre-compute doctrine (CLAUDE.md guardrail #6) and the page. This module gives it
the wolfe.py treatment (`wolfe_signals` pattern):

    python -m src.automation.launchpad_signals --persist-scan

materialises one clean snapshot into `launchpad_signals` (+ a tiny
`launchpad_scan_meta` k/v so a genuinely zero-hit day is still a VALID, instant
snapshot) so /dash/launchpad and the strategist board read it in milliseconds.
The nightly unit `hermes-launchpad-scan.timer` (16:20 UTC — after the bhavcopy
chain 14:00, the deals ingest 14:30, wolfe 16:00 and harmonic 16:10) owns the
refresh; the page falls back to a memoised live compute only when the snapshot
is absent or stale (fresh install / first day).

Isolation: NEW module; tables created here with IF NOT EXISTS (db.py untouched —
same isolation as wolfe.py / harmonic_signals.py). The validated thresholds stay
single-source in cockpit (_lp_at / _lp_features); this module only orchestrates
the gather + persist. Pure rule-based compute — NO LLM (Rs0), descriptive-only.
"""
from __future__ import annotations

import logging

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore

log = logging.getLogger("hermes.launchpad")


def ensure_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS launchpad_signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            flags       TEXT NOT NULL,      -- validated flags, |-joined ('MOM_CONT|COILED')
            age         INTEGER,            -- rising-edge age in sessions; 0 = turned on today
            ret22       REAL,
            ret1        REAL,
            vratio      REAL,
            rng         REAL,
            vol66       REAL,
            med_turn    REAL,               -- trailing-22d median turnover (Rs)
            buyer       INTEGER DEFAULT 0,  -- genuine one-sided institutional net-buyer today
            deals_date  TEXT,
            scan_date   TEXT NOT NULL,      -- the bhav trade date the scan reflects
            computed_at TEXT
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_launchpad_scan "
                 "ON launchpad_signals(scan_date, age ASC, med_turn DESC)")
    conn.execute("CREATE TABLE IF NOT EXISTS launchpad_scan_meta "
                 "(k TEXT PRIMARY KEY, v TEXT)")


def scan(conn):
    """The full Launchpad gather + flag pass over the latest bhav snapshot.
    Returns (hits, scan_date, deals_date) with hits = [(symbol, flags, metrics)]
    in exactly the shape cockpit.render_launchpad consumes. Precomputed-table
    READS only (bhavcopy_rows / nse_equity_list / bulk_block_deals) + in-Python
    features — never writes."""
    # Lazy web-module import: the threshold logic (_lp_at/_lp_features) is the
    # validated single source and stays in cockpit; importing it here at call
    # time avoids any import cycle (cockpit imports this module lazily too).
    from src.web.cockpit import _LP_LIQ, _lp_features, _lp_net_buyers

    # Unfiltered MAX rides idx_bhav_date (0.1ms); a series='EQ' filter forces a
    # multi-second scan of the 16GB table. Every trading day has EQ rows, so the
    # value is the same — the candidate query below re-applies series='EQ' anyway.
    tr = conn.execute(
        "SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
    T = tr["d"] if tr else None
    if not T:
        return [], None, None

    cand = [x["symbol"] for x in conn.execute(
        "SELECT symbol FROM bhavcopy_rows WHERE trade_date=? AND series='EQ' "
        "AND (segment='CM' OR segment IS NULL) AND value>=? AND close>20 "
        "AND symbol IN (SELECT symbol FROM nse_equity_list)", (T, _LP_LIQ)).fetchall()]

    rows_by_sym: dict[str, list] = {}
    if cand:
        import datetime as _dt
        lo = (_dt.date.fromisoformat(T) - _dt.timedelta(days=130)).isoformat()
        ph = ",".join("?" for _ in cand)
        for x in conn.execute(
                f"SELECT symbol, trade_date, close, prev_close, volume, value FROM bhavcopy_rows "
                f"WHERE symbol IN ({ph}) AND trade_date>=? AND trade_date<=? AND series='EQ' "
                f"AND (segment='CM' OR segment IS NULL) ORDER BY symbol, trade_date ASC",
                (*cand, lo, T)).fetchall():
            rows_by_sym.setdefault(x["symbol"], []).append(x)

    net_set, deals_td = _lp_net_buyers(conn)

    hits = []
    for sym, rs in rows_by_sym.items():
        try:
            try:                                          # D95 tape-primary adjustment
                from src.automation.corp_actions import price_ratios
                events = price_ratios(conn, sym)
            except Exception:  # noqa: BLE001
                events = {}
            res = _lp_features([x["close"] for x in rs], [x["prev_close"] for x in rs],
                               [x["volume"] for x in rs], [x["value"] for x in rs],
                               dates=[x["trade_date"] for x in rs], events=events)
        except Exception:  # noqa: BLE001 — one bad symbol never kills the scan
            res = None
        if not res:
            continue
        flags, m = res
        if flags and m["med_turn"] is not None and m["med_turn"] >= _LP_LIQ:
            m["buyer"] = sym in net_set
            hits.append((sym, flags, m))
    return hits, T, deals_td


def persist_scan(conn, computed_at=None):
    """Materialise scan() into launchpad_signals as a clean snapshot (DELETE +
    INSERT — atomic within the caller's transaction; no commit here, the caller
    owns the txn, same contract as wolfe.persist_scan / CL-SCO-12). Also upserts
    launchpad_scan_meta so a zero-hit day still reads as a fresh, valid snapshot.
    Returns (n_rows, scan_date)."""
    ensure_table(conn)
    hits, scan_date, deals_td = scan(conn)
    if not scan_date:
        log.warning("launchpad persist skipped: no bhavcopy data")
        return 0, None
    conn.execute("DELETE FROM launchpad_signals")
    conn.executemany(
        "INSERT INTO launchpad_signals "
        "(symbol,flags,age,ret22,ret1,vratio,rng,vol66,med_turn,buyer,"
        " deals_date,scan_date,computed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(sym, "|".join(flags), m.get("age"), m.get("ret22"), m.get("ret1"),
          m.get("vratio"), m.get("rng"), m.get("vol66"), m.get("med_turn"),
          1 if m.get("buyer") else 0, deals_td, scan_date, computed_at)
         for sym, flags, m in hits])
    for k, v in (("scan_date", scan_date), ("deals_date", deals_td),
                 ("computed_at", computed_at), ("n_hits", str(len(hits)))):
        conn.execute("INSERT INTO launchpad_scan_meta (k, v) VALUES (?, ?) "
                     "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    return len(hits), scan_date


def latest(conn):
    """Read the persisted snapshot (instant). Returns
    {hits, scan_date, deals_date, computed_at} — hits in the cockpit shape,
    possibly [] on a genuinely zero-hit day — or None when no snapshot exists
    (caller falls back to the live scan)."""
    try:
        meta = dict(conn.execute("SELECT k, v FROM launchpad_scan_meta").fetchall())
    except Exception:  # noqa: BLE001 — table absent = no snapshot yet
        return None
    scan_date = meta.get("scan_date")
    if not scan_date:
        return None
    try:
        recs = conn.execute(
            "SELECT symbol, flags, age, ret22, ret1, vratio, rng, vol66, med_turn, "
            "buyer FROM launchpad_signals WHERE scan_date=?", (scan_date,)).fetchall()
    except Exception:  # noqa: BLE001
        return None
    hits = []
    for r in recs:
        m = {"age": r["age"], "ret22": r["ret22"], "ret1": r["ret1"],
             "vratio": r["vratio"], "rng": r["rng"], "vol66": r["vol66"],
             "med_turn": r["med_turn"], "buyer": bool(r["buyer"])}
        hits.append((r["symbol"], [f for f in (r["flags"] or "").split("|") if f], m))
    return {"hits": hits, "scan_date": scan_date,
            "deals_date": meta.get("deals_date"),
            "computed_at": meta.get("computed_at")}


def _cli():
    """Nightly entry: `python -m src.automation.launchpad_signals --persist-scan`."""
    import argparse
    import datetime as _dt
    ap = argparse.ArgumentParser(
        description="Launchpad precursor scan — persist the nightly snapshot")
    ap.add_argument("--persist-scan", action="store_true",
                    help="materialise scan() into launchpad_signals")
    args = ap.parse_args()
    if args.persist_scan:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_conn() as conn:
            n, scan_date = persist_scan(conn, computed_at=stamp)
        print(f"persisted {n} launchpad precursors (as-of {scan_date}, computed {stamp})")
    else:
        ap.print_help()


if __name__ == "__main__":
    _cli()
