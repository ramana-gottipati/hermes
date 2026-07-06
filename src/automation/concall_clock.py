"""Concall PIT clocks — backfill the three real event dates on ``concalls``.

THE GAP (data-postmortem 2026-07-05, corpus lane): the schema carries three PIT
clock columns — ``concall_dt`` (when the call HAPPENED), ``transcript_publish_dt``
(when the transcript became PUBLIC = the tradeable-knowability clock) and
``result_filing_dt`` (when the results it discusses were filed) — but they were
~unpopulated (0% / 0% / 1.4%), and the 1.4% was mislabeled: ``concall_bse`` wrote
the BSE transcript-ANNOUNCEMENT date (a publish clock) into ``concall_dt``. Every
concall-derived ledger therefore floats on month-granular ``period_label`` — no
event study, no day-level join, no honest tradeable-window disclosure.

THE FIX — three backfills, all from data already in hand (no network, no LLM):

1. ``transcript_publish_dt``: for ``source='bse-ann'`` rows the real BSE NEWS_DT
   is already stored (in the wrong column). Relabel: copy it to
   ``transcript_publish_dt``; ``concall_dt`` is then re-derived honestly (below)
   or NULLed — a publish date must not impersonate a call date. Screener-source
   rows have NO real publish record → left NULL (honest; a BSE-announcements
   crawl can fill them later — never model/fake this column).

2. ``concall_dt``: the true call date sits on the transcript COVER PAGE
   (measured 97.3% carry a full date in the first ~3,000 chars). Regex the
   stored .txt, accept a date ONLY inside the period_label month ± a fence
   (kills fiscal-period dates like "quarter ended June 30, 2025" and letterhead
   noise), prefer a date anchored to a "held on / conducted on" phrase, and
   refuse ambiguity (two distinct in-window dates, no anchor → NULL). Honest
   coverage > forced coverage.

3. ``result_filing_dt``: join (symbol, fy, quarter) → period_end → the REAL BSE
   filing date in ``provenance_knowable`` (the pead.py convention: earliest real
   date per key, plausibility-lagged 5..200d after period_end; the ANNUAL key is
   the Q4-results day in India). Sanity net: a call discusses ALREADY-FILED
   results, so if the mapped filing lands after the call date (+1d slop) the
   period mapping is suspect for that row → no stamp.

Ordering discipline: period_end < result_filing_dt <= concall_dt <=
transcript_publish_dt (with same-day slop). ``provenance.py`` already declares
these columns as the real as-of clocks for data_class ``concall_corpus`` —
populating them IS the registration.

Idempotent (fills NULLs only; ``--force`` re-derives). Read-only on the
transcript files; per-batch commits (never holds a write txn across file I/O).

CLI:
  python -m src.automation.concall_clock --backfill        # all three, in order
  python -m src.automation.concall_clock --stats           # coverage + lag distributions
  python -m src.automation.concall_clock --selftest        # offline synthetic checks
"""
from __future__ import annotations

import argparse
import logging
import os
import re
from datetime import date, timedelta
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.concall_clock")

# ── call-date extraction ──────────────────────────────────────────────────────

_HEAD_CHARS = 4000          # cover page (measured: 97.3% carry the date in 3,000)
_MON = {m.lower(): i + 1 for i, m in enumerate(
    ("January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"))}
for _m, _i in list(_MON.items()):
    _MON[_m[:3]] = _i        # Jan, Feb, ... (Sept handled below)
_MON["sept"] = 9

_MON_RX = (r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
           r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
_ORD = r"(?:st|nd|rd|th)?"
# "August 7, 2025" / "August 7th 2025"   and   "7th August, 2025" / "07 August 2025"
_RX_MDY = re.compile(_MON_RX + r"\s+(\d{1,2})" + _ORD + r"\s*,?\s+(20\d{2})", re.I)
_RX_DMY = re.compile(r"(\d{1,2})" + _ORD + r"\s+" + _MON_RX + r"\s*,?\s+(20\d{2})", re.I)
# a date "anchored" to call-language within this many chars counts as THE call date
_ANCHOR_RX = re.compile(r"(?:held|conducted|hosted)\s+on|call\s+(?:held\s+)?on|earnings\s+call\s+on", re.I)
_ANCHOR_SPAN = 90

_LABEL_RX = re.compile(r"^([A-Za-z]{3,9})\s+(20\d{2})$")
_WINDOW_BEFORE_D = 21       # call may precede the label month start by a few days
_WINDOW_AFTER_D = 21        # ... or spill past its end (label = filing month ≈ call month)


def _label_month(period_label: Optional[str]) -> Optional[tuple]:
    m = _LABEL_RX.match((period_label or "").strip())
    if not m:
        return None
    mon = _MON.get(m.group(1).lower())
    return (int(m.group(2)), mon) if mon else None


def _month_window(year: int, month: int) -> tuple:
    start = date(year, month, 1)
    end = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
    return (start - timedelta(days=_WINDOW_BEFORE_D), end + timedelta(days=_WINDOW_AFTER_D))


def _dates_in(text: str) -> list:
    """[(iso_date, char_pos)] for every full date in ``text`` (both orders)."""
    out = []
    for rx, mon_g, day_g, yr_g in ((_RX_MDY, 1, 2, 3), (_RX_DMY, 2, 1, 3)):
        for m in rx.finditer(text):
            mon = _MON.get(m.group(mon_g).lower())
            if not mon:
                continue
            try:
                out.append((date(int(m.group(yr_g)), mon, int(m.group(day_g))).isoformat(), m.start()))
            except ValueError:
                continue
    return out


def extract_call_date(text: str, period_label: Optional[str]) -> Optional[str]:
    """The call date from a transcript cover page, or None when not confident.

    Only dates inside the period_label month ± fence qualify (the label is the
    call/filing month — this rejects fiscal-period dates and letterhead years).
    An anchor phrase ("held on ...") wins; else a UNIQUE in-window date wins;
    two+ distinct in-window dates with no anchor = ambiguous = None.
    """
    lm = _label_month(period_label)
    if not lm or not text:
        return None
    lo, hi = _month_window(*lm)
    head = text[:_HEAD_CHARS]
    cands = [(d, pos) for d, pos in _dates_in(head)
             if lo.isoformat() <= d <= hi.isoformat()]
    if not cands:
        return None
    anchors = [m.end() for m in _ANCHOR_RX.finditer(head)]
    if anchors:
        anchored = [d for d, pos in cands
                    if any(0 <= pos - a <= _ANCHOR_SPAN for a in anchors)]
        if len(set(anchored)) == 1:
            return anchored[0]
    distinct = sorted(set(d for d, _ in cands))
    if len(distinct) == 1:
        return distinct[0]
    return None                      # ambiguous — refuse rather than guess


# ── backfill 1: publish clock (bse-ann relabel) ───────────────────────────────

def backfill_publish_dt(conn) -> dict:
    """source='bse-ann': the stored concall_dt IS the BSE announcement (publish)
    timestamp — move it to transcript_publish_dt. concall_dt is cleared here and
    re-derived honestly by backfill_call_dt (regex) right after; a row whose
    transcript yields no confident call date stays NULL rather than carrying a
    publish date in a call-date column."""
    rows = conn.execute(
        "SELECT id, concall_dt FROM concalls WHERE source='bse-ann' "
        "AND concall_dt IS NOT NULL AND transcript_publish_dt IS NULL").fetchall()
    for r in rows:
        conn.execute("UPDATE concalls SET transcript_publish_dt=?, concall_dt=NULL WHERE id=?",
                     (r["concall_dt"], r["id"]))
    conn.commit()
    return {"relabeled": len(rows)}


# ── backfill 2: call date from the transcript cover page ─────────────────────

def backfill_call_dt(conn, *, force: bool = False, batch: int = 500) -> dict:
    where = "" if force else "AND concall_dt IS NULL"
    rows = conn.execute(
        f"SELECT id, period_label, transcript_path FROM concalls "
        f"WHERE parse_status='OK' AND transcript_path IS NOT NULL {where}").fetchall()
    stats = {"scanned": len(rows), "stamped": 0, "no_confident_date": 0, "missing_file": 0}
    pending = []
    for r in rows:                                   # file I/O OUTSIDE any txn
        path = r["transcript_path"]
        if not path or not os.path.exists(path):
            stats["missing_file"] += 1
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(_HEAD_CHARS)
        except OSError:
            stats["missing_file"] += 1
            continue
        d = extract_call_date(head, r["period_label"])
        if d:
            pending.append((d, r["id"]))
        else:
            stats["no_confident_date"] += 1
        if len(pending) >= batch:
            conn.executemany("UPDATE concalls SET concall_dt=? WHERE id=?", pending)
            conn.commit()
            stats["stamped"] += len(pending)
            pending = []
    if pending:
        conn.executemany("UPDATE concalls SET concall_dt=? WHERE id=?", pending)
        conn.commit()
        stats["stamped"] += len(pending)
    return stats


# ── backfill 3: result filing date from provenance_knowable ─────────────────

_MIN_LAG_D, _MAX_LAG_D = 5, 200      # pead.py plausibility fence (real date - period_end)
_FY_LO, _FY_HI = 2005, 2035


def _period_end(fy: int, quarter: int) -> Optional[str]:
    """Indian FY: Q1→(fy-1)-06-30, Q2→(fy-1)-09-30, Q3→(fy-1)-12-31, Q4→fy-03-31."""
    return {1: f"{fy - 1}-06-30", 2: f"{fy - 1}-09-30",
            3: f"{fy - 1}-12-31", 4: f"{fy}-03-31"}.get(quarter)


def _load_filing_map(conn) -> dict:
    """{(symbol, ptype, period_end): earliest plausible real BSE filing date}."""
    out: dict = {}
    for key, knew in conn.execute(
            "SELECT key, knowable_at FROM provenance_knowable WHERE data_class='fundamentals_history'"):
        try:
            sym, ptype, pend = key.split("|")
            k = str(knew)[:10]
            lag = (date.fromisoformat(k) - date.fromisoformat(pend)).days
        except (ValueError, AttributeError):
            continue
        if not (_MIN_LAG_D <= lag <= _MAX_LAG_D):
            continue
        kk = (sym, ptype, pend)
        if kk not in out or k < out[kk]:
            out[kk] = k
    return out


def backfill_filing_dt(conn, *, force: bool = False, batch: int = 500) -> dict:
    fmap = _load_filing_map(conn)
    where = "" if force else "AND result_filing_dt IS NULL"
    rows = conn.execute(
        f"SELECT id, symbol, fy, quarter, concall_dt FROM concalls "
        f"WHERE fy IS NOT NULL AND quarter IS NOT NULL {where}").fetchall()
    stats = {"scanned": len(rows), "stamped": 0, "no_real_date": 0,
             "bad_period_fields": 0, "filing_after_call": 0, "map_keys": len(fmap)}
    pending = []
    for r in rows:
        try:
            fy, q = int(r["fy"]), int(r["quarter"])
        except (TypeError, ValueError):
            stats["bad_period_fields"] += 1
            continue
        pend = _period_end(fy, q)
        if not (_FY_LO <= fy <= _FY_HI) or pend is None:
            stats["bad_period_fields"] += 1
            continue
        sym = (r["symbol"] or "").upper()
        # Q4 results are filed at the ANNUAL board meeting → the A key IS the Q4 day.
        cands = [fmap.get((sym, "Q", pend))]
        if q == 4:
            cands.append(fmap.get((sym, "A", pend)))
        cands = [c for c in cands if c]
        if not cands:
            stats["no_real_date"] += 1
            continue
        filing = min(cands)
        cd = str(r["concall_dt"])[:10] if r["concall_dt"] else None
        if cd and filing > (date.fromisoformat(cd) + timedelta(days=1)).isoformat():
            stats["filing_after_call"] += 1      # period mapping suspect → no stamp
            continue
        pending.append((filing, r["id"]))
        if len(pending) >= batch:
            conn.executemany("UPDATE concalls SET result_filing_dt=? WHERE id=?", pending)
            conn.commit()
            stats["stamped"] += len(pending)
            pending = []
    if pending:
        conn.executemany("UPDATE concalls SET result_filing_dt=? WHERE id=?", pending)
        conn.commit()
        stats["stamped"] += len(pending)
    return stats


# ── stats ─────────────────────────────────────────────────────────────────────

def clock_stats(conn) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) n, SUM(concall_dt IS NOT NULL) cd, "
        "SUM(transcript_publish_dt IS NOT NULL) pd, SUM(result_filing_dt IS NOT NULL) fd, "
        "SUM(parse_status='OK' AND transcript_path IS NOT NULL) parsed FROM concalls").fetchone()
    lag = conn.execute(
        "SELECT COUNT(*) n, ROUND(AVG(julianday(concall_dt)-julianday(result_filing_dt)),1) avg_d, "
        "MIN(julianday(concall_dt)-julianday(result_filing_dt)) min_d, "
        "MAX(julianday(concall_dt)-julianday(result_filing_dt)) max_d "
        "FROM concalls WHERE concall_dt IS NOT NULL AND result_filing_dt IS NOT NULL").fetchone()
    return {"rows": row["n"], "concall_dt": row["cd"], "transcript_publish_dt": row["pd"],
            "result_filing_dt": row["fd"], "parsed_with_file": row["parsed"],
            "filing_to_call": dict(lag) if lag and lag["n"] else {}}


# ── selftest (offline, synthetic) ────────────────────────────────────────────

def _selftest() -> int:
    import sqlite3
    import tempfile

    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        ok = ok and bool(cond)

    # extraction unit cases
    check("cover MDY", extract_call_date(
        "XYZ Ltd Q1 FY26 Earnings Conference Call held on August 7, 2025", "Aug 2025") == "2025-08-07")
    check("cover DMY + ordinal", extract_call_date(
        "Transcript of the call held on 7th August, 2025", "Aug 2025") == "2025-08-07")
    check("fiscal-period date rejected, call date kept", extract_call_date(
        'Results for the quarter ended June 30, 2025. Call conducted on August 11, 2025.',
        "Aug 2025") == "2025-08-11")
    check("out-of-window only -> None", extract_call_date(
        "quarter ended June 30, 2025", "Aug 2025") is None)
    check("two in-window dates, no anchor -> None (refuse)", extract_call_date(
        "August 7, 2025 ... August 12, 2025", "Aug 2025") is None)
    check("two in-window dates, anchored one wins", extract_call_date(
        "Published August 12, 2025. Earnings call held on August 7, 2025.",
        "Aug 2025") == "2025-08-07")
    check("adjacent-month spill accepted", extract_call_date(
        "call held on September 2, 2025", "Aug 2025") == "2025-09-02")
    check("no label -> None", extract_call_date("August 7, 2025", None) is None)

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
      CREATE TABLE concalls (id INTEGER PRIMARY KEY, symbol TEXT, period_label TEXT,
        fy INT, quarter INT, transcript_path TEXT, parse_status TEXT, source TEXT,
        concall_dt TEXT, transcript_publish_dt TEXT, result_filing_dt TEXT);
      CREATE TABLE provenance_knowable (data_class TEXT, key TEXT, symbol TEXT, knowable_at TEXT);
    """)
    with tempfile.TemporaryDirectory() as td:
        p1 = os.path.join(td, "a.txt")
        with open(p1, "w", encoding="utf-8") as fh:
            fh.write("ACME Q1 FY26 Earnings Call held on August 7, 2025\nquarter ended June 30, 2025")
        p2 = os.path.join(td, "b.txt")
        with open(p2, "w", encoding="utf-8") as fh:
            fh.write("no dates here at all")
        con.executemany(
            "INSERT INTO concalls (symbol, period_label, fy, quarter, transcript_path, parse_status, "
            "source, concall_dt) VALUES (?,?,?,?,?,?,?,?)", [
                ("ACME", "Aug 2025", 2026, 1, p1, "OK", "screener", None),      # 1: regex stamps
                ("NODATE", "Aug 2025", 2026, 1, p2, "OK", "screener", None),    # 2: stays NULL
                ("BSEA", "May 2024", 2024, 4, p2, "OK", "bse-ann", "2024-05-20T10:00:00"),  # 3: relabel
                ("JUNKFY", "Aug 2025", 226, 1, p1, "OK", "screener", None),     # 4: junk fy skipped
            ])
        con.executemany("INSERT INTO provenance_knowable VALUES ('fundamentals_history',?,?,?)", [
            ("ACME|Q|2025-06-30", "ACME", "2025-08-05"),      # Q1 FY26 filed Aug-5 (before the call ✓)
            ("BSEA|A|2024-03-31", "BSEA", "2024-05-18"),      # Q4 via ANNUAL key
            ("BSEA|Q|2024-03-31", "BSEA", "2024-05-19"),      # ... Q key later → A wins (min)
            ("NODATE|Q|2025-06-30", "NODATE", "2026-03-01"),  # lag 244d > 200 → implausible, dropped
        ])
        r1 = backfill_publish_dt(con)
        check("bse-ann relabeled publish<-concall_dt", r1["relabeled"] == 1)
        row3 = con.execute("SELECT * FROM concalls WHERE id=3").fetchone()
        check("relabel: publish set + concall_dt cleared",
              row3["transcript_publish_dt"] == "2024-05-20T10:00:00" and row3["concall_dt"] is None)
        r2 = backfill_call_dt(con)
        check("regex stamped the confident row(s) only", r2["stamped"] >= 1 and r2["no_confident_date"] >= 1)
        check("ACME concall_dt = 2025-08-07",
              con.execute("SELECT concall_dt FROM concalls WHERE id=1").fetchone()[0] == "2025-08-07")
        r3 = backfill_filing_dt(con)
        check("ACME filing stamped 2025-08-05",
              con.execute("SELECT result_filing_dt FROM concalls WHERE id=1").fetchone()[0] == "2025-08-05")
        check("Q4 uses MIN(A,Q) key -> 2024-05-18",
              con.execute("SELECT result_filing_dt FROM concalls WHERE id=3").fetchone()[0] == "2024-05-18")
        check("implausible lag dropped from map",
              con.execute("SELECT result_filing_dt FROM concalls WHERE id=2").fetchone()[0] is None)
        check("junk fy skipped", r3["bad_period_fields"] >= 1)
        # ordering discipline on the fully-stamped row
        a = con.execute("SELECT * FROM concalls WHERE id=1").fetchone()
        check("filing <= call", a["result_filing_dt"] <= a["concall_dt"])
        # idempotence
        r1b, r2b, r3b = backfill_publish_dt(con), backfill_call_dt(con), backfill_filing_dt(con)
        check("idempotent (second run stamps nothing)",
              r1b["relabeled"] == 0 and r2b["stamped"] == 0 and r3b["stamped"] == 0)
    con.close()
    print("concall_clock selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Concall PIT-clock backfills (publish / call / filing)")
    ap.add_argument("--backfill", action="store_true", help="run all three backfills, in order")
    ap.add_argument("--force", action="store_true", help="re-derive even where already set")
    ap.add_argument("--stats", action="store_true", help="coverage + filing→call lag")
    ap.add_argument("--selftest", action="store_true", help="offline synthetic checks")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    with get_conn() as conn:
        if args.backfill:
            log.info("publish relabel: %s", backfill_publish_dt(conn))
            log.info("call-date regex: %s", backfill_call_dt(conn, force=args.force))
            log.info("filing-date join: %s", backfill_filing_dt(conn, force=args.force))
        if args.backfill or args.stats:
            log.info("clocks: %s", clock_stats(conn))
        if not (args.backfill or args.stats):
            ap.error("give --backfill, --stats or --selftest")


if __name__ == "__main__":
    main()
