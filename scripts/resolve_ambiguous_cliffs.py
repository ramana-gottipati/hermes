"""Resolve the 64 AMBIGUOUS orphan-cliff events by PER-EVENT OFFICIAL-ARCHIVE verification
(S187, ledger 16AV; the task_74bd9558 continuation after S185/16AU healed the 117 CLEAN).

WHY A SECOND INSTRUMENT: `scripts/audit_orphan_cliffs.py` heals only events whose tape
evidence is unimpeachable (E1..E4). The 64 leftovers are exactly the cases where the tape
alone cannot decide — subdivision-day retail bursts (E4), post-split rallies (E2),
compound bonus×split ratios (E1), stale-quote ETFs, and genuine non-splits (Satyam's
crash, Majesco's ₹974 special dividend). Per 16AU: "per-event official-archive
verification is their path, never a loosened threshold."

THE TWO OFFICIAL SOURCES (both primary, Guardrail #8):
  S1  NSE corporateActions API, ``index=mf`` — the ETF instrument class the equities feed
      structurally omits (the 16AQ root cause). Rows carry the face-value split text
      ("Face Value Split (Sub-Division) - From Rs 10/- To Re 1/-"). The feed keys rows to
      the fund's CURRENT symbol; the official rename record
      ``nsearchives.nseindia.com/content/equities/symbolchange.csv`` (old,new,date) maps
      the tape-era symbol forward (e.g. ICICINXT50→NEXT50IETF 2023-12-20).
  S2  BSE corporate-actions API (``api.bseindia.com/BseIndiaAPI/api/DefaultData/w``) per
      scrip (codes from the owned ``bse_scrip_map``), full history (blank Fdate/TDate
      reaches 2000). Purpose text parses to typed actions; OLD split rows sometimes carry
      a BLANK Purpose — the row still ATTESTS a corporate action on that ex-date, and the
      tape then pins the magnitude on the legal FV/bonus grid (never a free ratio).

VERDICTS (only the first two heal):
  CONFIRMED             archive action(s) parsed; combined factor F corroborated by the
                        tape within ±10% on T0 (=prev/close) or T5 (=prev/median-next-5;
                        rallies distort T5, stale quotes distort T0 — either corroborates)
  CONFIRMED-STALE-QUOTE archive factor F; tape only inside the loose band [0.75, 1.30]
                        AND the name shows illiquidity evidence (trailing-10 median value
                        < ₹25L or cliff-day value spike > 20×) — thin ETFs catch up to
                        NAV across the ex-day; the residual is real, the ratio is F
  VERIFIED-NON-SPLIT    archive shows the true cause and it is not a split/bonus
                        (special dividend, demerger, rights, …) — recorded, never healed
  CONFLICT              archive factor found but tape corroboration fails both bands
  UNRESOLVED            no archive row within the window (includes NO-SCRIP / NO-RENAME
                        coverage gaps, each tagged) — stays exactly as S185 left it

Inserts go through the canonical ``corp_actions.store_actions`` (idempotent on
(symbol, action_type, ex_date, details)); the details text below is FROZEN. ex_date is
the TAPE cliff date (where the price actually steps — what `load_factors` must see); the
archive's own ex-date and text ride in `details` as the citation. A covered-check
(±5 days, any source) runs before every insert so this can never double-adjust — and if
the corp-actions ingest is ever extended to ``index=mf``, it MUST covered-check the same
way (mf feed ex-dates can sit 1 day off the NSE tape).

⚠ 16AS-LOOP FOLLOW-THROUGH: any heal here changes adjusted history / research universes.
Anchor + portfolio-gate re-derivation is owned by the S186 lane (carryforward claim) —
this script does NOT touch `union_forward.py` anchors or `portfolio_mix.py` gates.

Usage:
    python scripts/resolve_ambiguous_cliffs.py --selftest             # offline synthetic proof
    python scripts/resolve_ambiguous_cliffs.py [DB] [--csv out.csv]   # resolve + report (read-only)
    python scripts/resolve_ambiguous_cliffs.py [DB] --apply           # heal CONFIRMED* events
"""
from __future__ import annotations

import os
import re
import sqlite3
import statistics
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

SOURCE_TAG_NSE = "nse-mf-ca-api-verified"
SOURCE_TAG_BSE = "bse-ca-api-verified"
STRICT_TOL = 0.10          # |T/F - 1| ≤ this on T0 or T5 → CONFIRMED
LOOSE_BAND = (0.75, 1.30)  # + illiquidity evidence → CONFIRMED-STALE-QUOTE
ILLIQ_MEDIAN_VALUE = 2.5e6  # ₹25L trailing-10 median traded value
ILLIQ_SPIKE = 20.0
MATCH_WINDOW_D = 7         # archive ex-date within ± this of the tape cliff
# Legal EQUITY face-value ratios only, for when an attested archive row has no ratio
# text: FV pairs {10→5, 10→2 & 5→1, 10→1} → {2, 2.5(5→2), 5, 10}. The snap runs on the
# EX-DAY step (T0) alone — the sharpest instrument; cliff inputs all have r ≥ 4, and
# ±9% bands on this grid never overlap (min gap 25%). ETF rows always carry text, so
# the snap path is equity-only by construction.
SNAP_GRID = (2.0, 2.5, 5.0, 10.0)
SNAP_TOL = 0.09

SYMCHANGE_URL = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv"
BSE_CA_URL = "https://api.bseindia.com/BseIndiaAPI/api/DefaultData/w"
REQUEST_PAUSE = 1.5

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def _details(kind: str, rf: float, rt: float, archive_note: str) -> str:
    """FROZEN idempotency key component for this resolver's inserts — do not edit."""
    return (f"{kind} {rf:g}:{rt:g} (official-archive verified: {archive_note}; "
            f"S187 ambiguous-cliff resolution, ledger 16AV)")


def _iso(d: str) -> str | None:
    """'25-Nov-2021' / '24 Aug 2004' / '20040824' → ISO."""
    d = (d or "").strip()
    if not d or d == "-":
        return None
    if re.fullmatch(r"\d{8}", d):
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    m = re.fullmatch(r"(\d{1,2})[- ]([A-Za-z]{3})[- ](\d{4})", d)
    if m:
        mon = _MONTHS.get(m.group(2).upper())
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return None


# ── archive-text parsing ─────────────────────────────────────────────────────

_RS = r"(?:Rs\.?|Re\.?|Rs|Re)\s*\.?\s*([0-9]+(?:\.[0-9]+)?)"


def parse_purpose(text: str) -> dict | None:
    """Typed action from an archive purpose/subject string.
    → {kind: SPLIT|BONUS|DIVIDEND|OTHER|ATTESTED-BLANK, rf, rt, factor} (ratios None when
    the text carries none)."""
    t = (text or "").strip()
    if not t:
        return {"kind": "ATTESTED-BLANK", "rf": None, "rt": None, "factor": None, "text": ""}
    low = t.lower()
    m = re.search(_RS + r".{0,40}?(?:to|To|TO).{0,10}?" + _RS, t)
    if ("split" in low or "sub-division" in low or "subdivision" in low
            or "sub division" in low) and m:
        rf, rt = float(m.group(1)), float(m.group(2))
        if rt > 0 and rf > rt:
            return {"kind": "SPLIT", "rf": rf, "rt": rt, "factor": rf / rt, "text": t}
    m = re.search(r"bonus[^0-9]{0,20}(\d+)\s*:\s*(\d+)", low)
    if m:
        b, a = float(m.group(1)), float(m.group(2))
        if a > 0:
            return {"kind": "BONUS", "rf": b, "rt": a, "factor": (b + a) / a, "text": t}
    if "dividend" in low:
        return {"kind": "DIVIDEND", "rf": None, "rt": None, "factor": None, "text": t}
    if "split" in low and not m:
        return {"kind": "SPLIT-NOTEXT", "rf": None, "rt": None, "factor": None, "text": t}
    return {"kind": "OTHER", "rf": None, "rt": None, "factor": None, "text": t}


def snap_canonical(x: float) -> float | None:
    fit = min(SNAP_GRID, key=lambda k: abs(x / k - 1.0))
    return fit if abs(x / fit - 1.0) <= SNAP_TOL else None


# ── per-event resolution (pure; archive rows injected → offline-testable) ────

def resolve_event(tape: dict, archive_rows: list) -> dict:
    """tape: {symbol, ex_date, prev_close, close, next5(list), trail_med_value,
              cliff_value}; archive_rows: [{kind, rf, rt, factor, text, ex_date, src}].
    → {verdict, actions(list of insertable action dicts), factor, corroboration, note}"""
    t0 = tape["prev_close"] / tape["close"]
    t5 = None
    if len(tape["next5"]) >= 3:
        t5 = tape["prev_close"] / statistics.median(tape["next5"])
    near = [r for r in archive_rows
            if r.get("ex_date") and abs_days(r["ex_date"], tape["ex_date"]) <= MATCH_WINDOW_D]
    if not near:
        return {"verdict": "UNRESOLVED", "actions": [], "factor": None,
                "corroboration": f"T0 {t0:.2f} T5 {(t5 or 0):.2f}",
                "note": "no archive row in ±%dd window" % MATCH_WINDOW_D}
    typed = [r for r in near if r["kind"] in ("SPLIT", "BONUS")]
    blanks = [r for r in near if r["kind"] in ("ATTESTED-BLANK", "SPLIT-NOTEXT")]
    others = [r for r in near if r["kind"] in ("DIVIDEND", "OTHER")]
    if not typed and not blanks:
        cite = "; ".join(f"{r['kind']}:{r['text'][:45]}" for r in others[:3])
        return {"verdict": "VERIFIED-NON-SPLIT", "actions": [], "factor": None,
                "corroboration": f"T0 {t0:.2f}", "note": f"archive cause: {cite}"}

    factor = 1.0
    actions = []
    for r in typed:
        factor *= r["factor"]
        actions.append(r)
    unknown = None
    if blanks and not typed:
        # attested action, no ratio text anywhere: the ex-day step pins the magnitude
        snapped = snap_canonical(t0)
        if snapped is None:
            return {"verdict": "CONFLICT", "actions": [], "factor": None,
                    "corroboration": f"T0 {t0:.2f} T5 {(t5 or 0):.2f}",
                    "note": "attested blank row; tape snaps to no legal factor"}
        unknown = {"kind": "SPLIT", "rf": snapped, "rt": 1.0, "factor": snapped,
                   "text": "(archive row blank — ratio tape-snapped to legal grid)",
                   "ex_date": blanks[0]["ex_date"], "src": blanks[0]["src"]}
        factor, actions = snapped, [unknown]
    elif blanks and typed:
        # e.g. ITC: 'Bonus issue 1:2' + one blank row (the FV split): residual must snap
        snapped = snap_canonical(t0 / factor)
        if snapped and snapped > 1.0:
            unknown = {"kind": "SPLIT", "rf": snapped, "rt": 1.0, "factor": snapped,
                       "text": "(blank archive row beside %s — residual tape-snapped)"
                               % "+".join(r["kind"] for r in typed),
                       "ex_date": blanks[0]["ex_date"], "src": blanks[0]["src"]}
            factor *= snapped
            actions = actions + [unknown]
        # a blank row whose residual snaps to nothing is treated as a duplicate print of
        # the typed action (BSE dupes rows) — the typed factor must then corroborate alone

    checks = []
    if t0:
        checks.append(("T0", t0 / factor))
    if t5:
        checks.append(("T5", t5 / factor))
    strict = next((n for n, q in checks if abs(q - 1.0) <= STRICT_TOL), None)
    loose = next((n for n, q in checks if LOOSE_BAND[0] <= q <= LOOSE_BAND[1]), None)
    illiquid = (tape["trail_med_value"] < ILLIQ_MEDIAN_VALUE
                or (tape["trail_med_value"] > 0
                    and tape["cliff_value"] / tape["trail_med_value"] > ILLIQ_SPIKE))
    corro = " ".join(f"{n} {q:.3f}xF" for n, q in checks)
    if strict:
        verdict = "CONFIRMED"
    elif loose and illiquid:
        verdict = "CONFIRMED-STALE-QUOTE"
    else:
        return {"verdict": "CONFLICT", "actions": [], "factor": factor,
                "corroboration": corro,
                "note": "archive factor %.3g uncorroborated (illiquid=%s)" % (factor, illiquid)}
    return {"verdict": verdict, "actions": actions, "factor": factor,
            "corroboration": corro, "note": ""}


def abs_days(a: str, b: str) -> int:
    from datetime import date
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


# ── tape + archive plumbing (network/DB side) ────────────────────────────────

def tape_context(conn, symbol: str, ex_date: str) -> dict | None:
    rows = conn.execute(
        "SELECT trade_date, close, value FROM bhavcopy_rows "
        "WHERE symbol=? AND series IN ('EQ','BE','BZ') AND close>0 "
        "AND trade_date BETWEEN date(?,'-30 day') AND date(?,'+15 day') "
        "ORDER BY trade_date", (symbol, ex_date, ex_date)).fetchall()
    idx = next((i for i, r in enumerate(rows) if r[0] == ex_date), None)
    if idx is None or idx == 0:
        return None
    closes = [r[1] for r in rows]
    values = [r[2] or 0 for r in rows]
    trail = [v for v in values[max(0, idx - 10):idx] if v]
    return {"symbol": symbol, "ex_date": ex_date,
            "prev_close": closes[idx - 1], "close": closes[idx],
            "next5": closes[idx + 1:idx + 6],
            "trail_med_value": statistics.median(trail) if trail else 0.0,
            "cliff_value": values[idx]}


def load_rename_map(session, headers) -> dict:
    """old-symbol → current-symbol (transitive), from NSE's official rename record."""
    r = session.get(SYMCHANGE_URL, headers=headers, timeout=40)
    r.raise_for_status()
    step = {}
    for ln in r.content.decode("utf-8", "replace").splitlines():
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) >= 4 and parts[1] and parts[2]:
            step[parts[1].upper()] = parts[2].upper()
    out = {}
    for old in step:
        cur, hops = old, 0
        while cur in step and hops < 6:
            cur, hops = step[cur], hops + 1
        out[old] = cur
    return out


def fetch_nse_mf_window(session, headers, ex_date: str) -> list:
    from datetime import date, timedelta
    from src.automation.corp_actions import _NSE_API
    d = date.fromisoformat(ex_date)
    fmt = lambda x: x.strftime("%d-%m-%Y")
    url = (f"{_NSE_API}?index=mf&from_date={fmt(d - timedelta(days=10))}"
           f"&to_date={fmt(d + timedelta(days=10))}")
    r = session.get(url, headers=headers, timeout=45)
    j = r.json()
    data = j.get("data") if isinstance(j, dict) else j
    out, seen = [], set()
    for x in data or []:
        key = (x.get("symbol"), x.get("exDate"), x.get("subject"))
        if key in seen:
            continue
        seen.add(key)
        p = parse_purpose(x.get("subject") or "")
        p.update({"ex_date": _iso(x.get("exDate")), "src": f"NSE-mf {x.get('symbol')}",
                  "feed_symbol": (x.get("symbol") or "").upper()})
        out.append(p)
    return out


_SCRIP_MASTER_ISIN: dict | None = None


def resolve_scrip_chain(symbol: str, ex_date: str, conn, cur_sym: str = "") -> tuple[str | None, str]:
    """NSE symbol → BSE scrip code with NO silent wrong-match: (1) owned bse_scrip_map by
    the event-era symbol, (2) by the CURRENT symbol (official rename record — same
    listing, renamed), (3) the map by the EVENT-ERA ISIN from the bhavcopy row itself,
    (4) one cached live BSE scrip-master fetch joined on that ISIN. None → NO-SCRIP."""
    global _SCRIP_MASTER_ISIN
    from src.automation.fundamentals_filing_dates import resolve_scripcode
    sc = resolve_scripcode(symbol, conn)
    if sc:
        return str(sc), "map-symbol"
    if cur_sym and cur_sym != symbol:
        sc = resolve_scripcode(cur_sym, conn)
        if sc:
            return str(sc), f"map-current-symbol {cur_sym}"
    isin = (conn.execute(
        "SELECT isin FROM bhavcopy_rows WHERE symbol=? AND trade_date=? "
        "AND isin IS NOT NULL AND isin != '' LIMIT 1", (symbol, ex_date)).fetchone()
        or [None])[0]
    if not isin:
        return None, "NO-SCRIP (no event-era ISIN either)"
    r = conn.execute("SELECT scripcode FROM bse_scrip_map WHERE isin=? LIMIT 1",
                     (isin,)).fetchone()
    if r:
        return str(r[0]), f"map-isin {isin}"
    if _SCRIP_MASTER_ISIN is None:
        from src.automation.fundamentals_filing_dates import fetch_bse_scrip_master
        rows = fetch_bse_scrip_master(statuses=("Active", "Suspended", "Delisted"))
        _SCRIP_MASTER_ISIN = {
            (x.get("ISIN_NUMBER") or "").strip(): str(x.get("SCRIP_CD"))
            for x in rows if x.get("ISIN_NUMBER") and x.get("SCRIP_CD")}
        print(f"  (live BSE scrip master cached: {len(_SCRIP_MASTER_ISIN)} ISINs)")
    sc = _SCRIP_MASTER_ISIN.get(isin)
    if sc:
        return sc, f"master-isin {isin}"
    return None, f"NO-SCRIP (ISIN {isin} unknown to BSE master)"


def fetch_bse_history(symbol: str, ex_date: str, conn, cur_sym: str = "") -> tuple[list, str]:
    import requests
    from src.automation.fundamentals_filing_dates import BSE_HEADERS
    sc, how = resolve_scrip_chain(symbol, ex_date, conn, cur_sym)
    if not sc:
        return [], how
    r = requests.get(BSE_CA_URL, headers=BSE_HEADERS, timeout=40, params={
        "Fdate": "", "TDate": "", "Purposecode": "", "strSearch": "S",
        "ddlindustrys": "", "ddlcategorys": "E", "segment": "0", "scripcode": sc})
    try:
        j = r.json()
    except Exception:
        return [], f"HTTP-{r.status_code}"
    if not isinstance(j, list):
        return [], "EMPTY"
    out, seen = [], set()
    for x in j:
        key = (x.get("exdate"), x.get("Purpose"))
        if key in seen:
            continue
        seen.add(key)
        p = parse_purpose(x.get("Purpose") or "")
        p.update({"ex_date": _iso(x.get("exdate") or x.get("Ex_date")),
                  "src": f"BSE {sc} '{(x.get('Purpose') or '')[:40]}'"})
        out.append(p)
    return out, f"OK ({how})"


ETF_HINT = re.compile(r"(ETF|BEES|IETF|ADD\b|NIFTY|SENSEX|GOLD|SILVER|MOM|LOWVOL|ALPHA|"
                      r"QUAL|VALUE|MID|SMALL|TOP10|MULTI|BHARAT|CPSE|CONS|AUTO|PHARMA|"
                      r"HEALTH|BANK|FIN|PSU|PVT|INFRA|COMMO|DIGITAL|MNC|ESG|SHARIA)")


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    db = args[0] if args else "data/hermes.db"
    apply_ = "--apply" in sys.argv
    csv_path = sys.argv[sys.argv.index("--csv") + 1] if "--csv" in sys.argv else None

    conn = sqlite3.connect(db)
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    import audit_orphan_cliffs as aoc
    _clean, ambiguous = aoc.audit(conn)
    print(f"live re-audit: {len(_clean)} CLEAN / {len(ambiguous)} AMBIGUOUS "
          f"(resolver input = the ambiguous set)")
    if _clean:
        print("⚠ CLEAN events exist — run audit_orphan_cliffs.py --apply first; aborting")
        return 1

    from src.automation.corp_actions import _nse_session
    session, headers = _nse_session()
    renames = load_rename_map(session, headers)
    print(f"rename map: {len(renames)} official symbol changes loaded")

    mf_cache: dict[str, list] = {}
    results = []
    for sym, ex, _pc, _c, _fit, tags in sorted(ambiguous, key=lambda r: r[1]):
        tape = tape_context(conn, sym, ex)
        if tape is None:
            results.append((sym, ex, {"verdict": "UNRESOLVED", "actions": [], "factor": None,
                                      "corroboration": "", "note": "tape context missing"}, tags))
            continue
        cur_sym = renames.get(sym, sym)
        # DUAL-SOURCE, mf-first: the NSE mf window (cached per date) answers when the
        # instrument is a fund; otherwise BSE full-history per scrip. Never unioned — a
        # dual-listed ETF's split in both feeds would double-count the factor.
        note = ""
        if ex not in mf_cache:
            time.sleep(REQUEST_PAUSE)
            try:
                mf_cache[ex] = fetch_nse_mf_window(session, headers, ex)
            except Exception as e:
                mf_cache[ex] = []
                note = f"NSE-mf fetch failed: {e}"
        rows = [r for r in mf_cache[ex] if r.get("feed_symbol") in (cur_sym, sym)]
        if not rows:
            if note == "":
                note = f"no NSE-mf row for {sym}/{cur_sym}"
            time.sleep(REQUEST_PAUSE)
            try:
                rows, status = fetch_bse_history(sym, ex, conn, cur_sym)
                if not status.startswith("OK"):
                    note += f"; BSE: {status}"
            except Exception as e:
                note += f"; BSE fetch failed: {e}"
        res = resolve_event(tape, rows)
        if note and res["verdict"] == "UNRESOLVED":
            res["note"] = (res["note"] + "; " + note).strip("; ")
        results.append((sym, ex, res, tags))

    by = {}
    for sym, ex, res, _t in results:
        by.setdefault(res["verdict"], []).append((sym, ex))
    print("\n== verdicts ==")
    for v in ("CONFIRMED", "CONFIRMED-STALE-QUOTE", "VERIFIED-NON-SPLIT",
              "CONFLICT", "UNRESOLVED"):
        print(f"  {v:<22} {len(by.get(v, []))}")
    print("\n== per-event table ==")
    for sym, ex, res, tags in results:
        acts = " + ".join(f"{a['kind']} {a['rf']:g}:{a['rt']:g}" for a in res["actions"]) or "-"
        print(f"{ex} {sym:<12} {res['verdict']:<22} F={res['factor'] or 0:<7.3g} {acts:<24}"
              f" | {res['corroboration']} | {res['note']}"[:200])
        for a in res["actions"]:
            print(f"      ← {a['src']}: {a['text'][:95]}")

    if csv_path:
        import csv as _csv
        with open(csv_path, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["symbol", "ex_date", "verdict", "factor", "actions",
                        "corroboration", "note", "s185_tags"])
            for sym, ex, res, tags in results:
                w.writerow([sym, ex, res["verdict"], res["factor"],
                            " + ".join(f"{a['kind']} {a['rf']}:{a['rt']} [{a['src']}]"
                                       for a in res["actions"]),
                            res["corroboration"], res["note"], tags])
        print(f"full table -> {csv_path}")

    heal = [(sym, ex, res) for sym, ex, res in
            [(s, e, r) for s, e, r, _ in results]
            if res["verdict"].startswith("CONFIRMED")]
    if not apply_:
        print(f"\ndry-run — {len(heal)} event(s) would heal; pass --apply to insert")
        conn.close()
        return 0
    conn.close()

    from src.core.db import get_conn
    from src.automation.corp_actions import store_actions
    inserted = skipped_covered = 0
    with get_conn() as wconn:
        before = wconn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
        for sym, ex, res in heal:
            covered = wconn.execute(
                "SELECT 1 FROM corporate_actions WHERE symbol=? AND action_type IN "
                "('SPLIT','BONUS') AND ex_date BETWEEN date(?,'-5 day') AND date(?,'+5 day') "
                "LIMIT 1", (sym, ex, ex)).fetchone()
            if covered:
                skipped_covered += 1
                continue
            rows = [{
                "symbol": sym, "action_type": a["kind"], "ex_date": ex,
                "record_date": None, "ratio_from": float(a["rf"]), "ratio_to": float(a["rt"]),
                "details": _details(a["kind"], a["rf"], a["rt"], a["src"]),
                "source": SOURCE_TAG_NSE if a["src"].startswith("NSE") else SOURCE_TAG_BSE,
            } for a in res["actions"]]
            inserted += store_actions(rows, conn=wconn)
        wconn.commit()
        after = wconn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
    print(f"\nhealed: {inserted} action row(s) inserted (table {before} -> {after}); "
          f"{skipped_covered} event(s) already covered (race-safe skip)")
    return 0


# ── offline selftest ─────────────────────────────────────────────────────────

def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    p = parse_purpose(" Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share")
    check("mf 10:1 parses to SPLIT f=10", p["kind"] == "SPLIT" and p["factor"] == 10.0)
    p = parse_purpose("Face Value Split (Sub-Division) - From Rs 115.95/- Per Share To Rs 11.59/- Per Share")
    check("decimal FV split ~10", p["kind"] == "SPLIT" and abs(p["factor"] - 10.0) < 0.05)
    p = parse_purpose("Bonus issue 1:2")
    check("bonus 1:2 -> f=1.5", p["kind"] == "BONUS" and p["factor"] == 1.5)
    p = parse_purpose("Dividend - Rs. - 974.0000")
    check("dividend typed DIVIDEND", p["kind"] == "DIVIDEND")
    check("blank attests", parse_purpose("")["kind"] == "ATTESTED-BLANK")
    check("snap 4.71->5", snap_canonical(4.71) == 5.0)
    check("snap 9.17->10 (ITC residual after 1:2 bonus)", snap_canonical(9.17) == 10.0)
    check("snap 6.3->None (between grid points)", snap_canonical(6.3) is None)
    check("snap 8.32->None (no legal FV pair -> honest refusal)", snap_canonical(8.32) is None)

    tape = {"symbol": "X", "ex_date": "2021-11-25", "prev_close": 373.2, "close": 37.29,
            "next5": [37.5, 37.2, 37.6, 37.4, 37.3], "trail_med_value": 1e6,
            "cliff_value": 5.4e6}
    arc = [{"kind": "SPLIT", "rf": 10, "rt": 1, "factor": 10.0, "text": "FV 10→1",
            "ex_date": "2021-11-25", "src": "NSE-mf ABSLBANETF"}]
    r = resolve_event(tape, arc)
    check("ABSL-shaped -> CONFIRMED", r["verdict"] == "CONFIRMED")
    tape2 = dict(tape, prev_close=1139.8, close=136.8, next5=[137.0, 136.5, 137.2],
                 trail_med_value=4e5, cliff_value=2e7)
    r = resolve_event(tape2, arc)
    check("stale-quote ETF (T~8.3, F=10, illiquid) -> CONFIRMED-STALE-QUOTE",
          r["verdict"] == "CONFIRMED-STALE-QUOTE")
    tape3 = dict(tape2, trail_med_value=6e7, cliff_value=6.5e7)
    r = resolve_event(tape3, arc)
    check("same gap but LIQUID -> CONFLICT (no stale excuse)", r["verdict"] == "CONFLICT")
    tape_itc = {"symbol": "ITC", "ex_date": "2005-09-21", "prev_close": 1929.6,
                "close": 140.2, "next5": [139.0, 141.0, 140.5], "trail_med_value": 5e8,
                "cliff_value": 8e8}
    arc_itc = [{"kind": "BONUS", "rf": 1, "rt": 2, "factor": 1.5, "text": "Bonus issue 1:2",
                "ex_date": "2005-09-21", "src": "BSE 500875"},
               {"kind": "ATTESTED-BLANK", "rf": None, "rt": None, "factor": None, "text": "",
                "ex_date": "2005-09-21", "src": "BSE 500875"}]
    r = resolve_event(tape_itc, arc_itc)
    check("ITC-shaped bonus+blank -> CONFIRMED with SPLIT 10 + BONUS (F=15)",
          r["verdict"] == "CONFIRMED" and abs(r["factor"] - 15.0) < 0.01
          and sorted(a["kind"] for a in r["actions"]) == ["BONUS", "SPLIT"])
    tape_maj = {"symbol": "MAJESCO", "ex_date": "2020-12-23", "prev_close": 985.6,
                "close": 12.2, "next5": [13.0, 12.5, 13.5], "trail_med_value": 5e7,
                "cliff_value": 3e8}
    r = resolve_event(tape_maj, [{"kind": "DIVIDEND", "rf": None, "rt": None, "factor": None,
                                  "text": "Dividend - Rs. - 974.0000",
                                  "ex_date": "2020-12-23", "src": "BSE 539378"}])
    check("Majesco-shaped special dividend -> VERIFIED-NON-SPLIT",
          r["verdict"] == "VERIFIED-NON-SPLIT")
    tape_sat = {"symbol": "SATYAMCOMP", "ex_date": "2009-01-07", "prev_close": 178.9,
                "close": 40.25, "next5": [30.0, 25.0, 28.0], "trail_med_value": 1e9,
                "cliff_value": 2e10}
    r = resolve_event(tape_sat, [])
    check("Satyam-shaped (no archive row) -> UNRESOLVED", r["verdict"] == "UNRESOLVED")
    tape_bp = {"symbol": "BERGEPAINT", "ex_date": "2004-08-25", "prev_close": 126.5,
               "close": 26.85, "next5": [30.0, 36.0, 38.7, 39.0, 40.0],
               "trail_med_value": 2e7, "cliff_value": 3e7}
    r = resolve_event(tape_bp, [{"kind": "ATTESTED-BLANK", "rf": None, "rt": None,
                                 "factor": None, "text": "", "ex_date": "2004-08-24",
                                 "src": "BSE 509480"}])
    check("Bergepaint-shaped blank+rally -> CONFIRMED via T0 snap 5",
          r["verdict"] == "CONFIRMED" and r["factor"] == 5.0)
    tape_sg = {"symbol": "SHANTIGEAR", "ex_date": "2004-07-27", "prev_close": 362.0,
               "close": 21.75, "next5": [21.5, 22.0, 21.8], "trail_med_value": 1e7,
               "cliff_value": 2e7}
    arc_sg = [{"kind": "BONUS", "rf": 1, "rt": 1, "factor": 2.0, "text": "Bonus issue 1:1",
               "ex_date": "2004-07-27", "src": "BSE 522034"},
              {"kind": "ATTESTED-BLANK", "rf": None, "rt": None, "factor": None, "text": "",
               "ex_date": "2004-07-27", "src": "BSE 522034"}]
    r = resolve_event(tape_sg, arc_sg)
    check("Shantigear-shaped (residual 8.3 fits no legal FV pair) -> CONFLICT",
          r["verdict"] == "CONFLICT")
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
