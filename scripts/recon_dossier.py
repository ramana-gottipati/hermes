"""Replay-the-Tape reconstruction — runs ON THE VPS against the real archives.

For each hero (symbol, as_of), it reconstructs ONLY what was knowable on as_of:
  * point-in-time patearn fundamentals (research.db.fundamentals_history, report_date <= as_of)
  * a no-look-ahead LEDGER (every fundamental input + its period_end + report_date)
  * the price/technical setup as of as_of (hermes.db.bhavcopy_rows EQ, trade_date <= as_of)
  * the forward REVEAL (path after entry — peak gain + gain at the known exit)

Emits one JSON blob to stdout. The patearn SCORE is computed laptop-side from the
as_of dict (decoupled from VPS code state). Pure stdlib.

Usage (on VPS):  python3 /tmp/recon_dossier.py > /tmp/dossier.json
"""
import json
import re
import sqlite3
import sys
import statistics as st

sys.path.insert(0, "/tmp")
from fundamentals_asof import as_of_fundamentals, load_symbol_history  # scp'd alongside

RESEARCH_DB = "/opt/hermes/data/research.db"
HERMES_DB = "/opt/hermes/data/hermes.db"

HEROES = [
    {"symbol": "ALKYLAMINE", "as_of": "2020-03-26", "entry": "2020-03-27",
     "sell": "2020-10-08", "known_return": 171.5, "months": 6,
     "lens": "fundamental", "name": "Alkyl Amines Chemicals"},
    {"symbol": "TANLA", "as_of": "2020-08-05", "entry": "2020-08-06",
     "sell": "2020-12-11", "known_return": 544.8, "months": 4,
     "lens": "technical", "name": "Tanla Platforms"},
]

# Metrics to expose in the no-look-ahead ledger (annual unless noted).
LEDGER_METRICS = [
    ("A", ("Sales", "Revenue"), "Sales (₹cr)"),
    ("A", ("Net Profit",), "Net Profit (₹cr)"),
    ("A", ("ROCE %", "Financing Margin %"), "ROCE %"),
    ("A", ("OPM %",), "OPM %"),
    ("A", ("Operating Profit",), "Operating Profit (₹cr)"),
    ("A", ("Interest",), "Interest (₹cr)"),
    ("A", ("Borrowings", "Borrowing"), "Borrowings (₹cr)"),
    ("A", ("EPS in Rs",), "EPS (₹)"),
    ("A", ("Reserves",), "Reserves (₹cr)"),
]


def known_latest(frame, ptype, names, as_of):
    """Latest (period_end, report_date, value) with report_date <= as_of."""
    for nm in names:
        rows = [(pe, rd, v) for (pe, rd, v) in frame.get((ptype, nm), []) if rd <= as_of]
        if rows:
            rows.sort(key=lambda t: t[0])
            return rows[-1]
    return None


def load_eq(symbol):
    """All EQ daily bars for a symbol, ascending: [(date, o,h,l,c, vol, delivpct)]."""
    con = sqlite3.connect(HERMES_DB)
    try:
        rows = con.execute(
            "SELECT trade_date,open,high,low,close,volume,deliv_per "
            "FROM bhavcopy_rows WHERE symbol=? AND series='EQ' "
            "AND close IS NOT NULL ORDER BY trade_date", (symbol,)).fetchall()
    finally:
        con.close()
    return rows


def _qident(name: str) -> str:
    """Quote an SQLite identifier safely. CL-SCR-04: the column names below are
    discovered from PRAGMA table_info (schema-sourced, not user input today) but were
    f-string-interpolated into SQL raw — a latent injection shape. We (a) assert the
    identifier is a plain word and (b) double-quote it (escaping embedded quotes) so it
    can never be interpreted as anything but an identifier."""
    if not isinstance(name, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(f"unsafe column identifier from schema: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def find_index_series():
    """Best-effort Nifty 500 close series {date: close}. Returns ({}, name) if absent."""
    con = sqlite3.connect(HERMES_DB)
    try:
        cols = [c[1] for c in con.execute("PRAGMA table_info(index_rows)")]
        if not cols:
            return {}, None
        # discover name/date/close-ish columns
        namec = next((c for c in cols if "name" in c.lower() or "index" in c.lower()), None)
        datec = next((c for c in cols if "date" in c.lower()), None)
        closec = next((c for c in cols if c.lower() in ("close", "closing", "close_value", "value", "last")), None)
        if not (namec and datec and closec):
            return {}, None
        qname, qdate, qclose = _qident(namec), _qident(datec), _qident(closec)
        names = [r[0] for r in con.execute(
            f"SELECT DISTINCT {qname} FROM index_rows").fetchall() if r[0]]
        target = None
        for cand in ("NIFTY 500", "Nifty 500", "NIFTY500", "Nifty 500 Index"):
            if cand in names:
                target = cand
                break
        if not target:
            target = next((n for n in names if "500" in str(n)), None)
        if not target:
            return {}, None
        rows = con.execute(
            f"SELECT {qdate},{qclose} FROM index_rows WHERE {qname}=? AND {qclose} IS NOT NULL",
            (target,)).fetchall()
        return {str(d): float(c) for d, c in rows}, target
    except Exception as e:
        return {}, f"ERR:{e}"
    finally:
        con.close()


def pct(a, b):
    return None if (a is None or b in (None, 0)) else (a / b - 1.0) * 100.0


def sma(vals, n):
    return st.mean(vals[-n:]) if len(vals) >= n else None


def technicals(eq, as_of):
    hist = [r for r in eq if r[0] <= as_of]
    if len(hist) < 60:
        return {"insufficient": True, "bars": len(hist)}
    dates = [r[0] for r in hist]
    highs = [r[2] for r in hist]
    lows = [r[3] for r in hist]
    closes = [r[4] for r in hist]
    vols = [r[5] or 0 for r in hist]
    deliv = [r[6] for r in hist if r[6] is not None]
    px = closes[-1]
    w = min(252, len(hist))
    hi52 = max(highs[-w:])
    lo52 = min(lows[-w:])
    # ATR14 / true range
    trs = []
    for i in range(1, len(hist)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    atr14 = st.mean(trs[-14:]) if len(trs) >= 14 else None
    rets = [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))]
    vol20 = st.pstdev(rets[-20:]) * 100 if len(rets) >= 20 else None
    vol100 = st.pstdev(rets[-100:]) * 100 if len(rets) >= 100 else None
    contraction = (vol20 / vol100) if (vol20 and vol100) else None
    base40 = None
    if len(closes) >= 40:
        seg = closes[-40:]
        base40 = (max(seg) - min(seg)) / st.mean(seg) * 100
    vol_surge = None
    if len(vols) >= 60:
        recent = st.mean(vols[-10:])
        prior = st.mean(vols[-60:-10])
        vol_surge = (recent / prior) if prior else None

    def ret_n(n):
        return pct(px, closes[-1 - n]) if len(closes) > n else None

    return {
        "insufficient": False, "bars": len(hist), "last_date": dates[-1],
        "px": round(px, 2),
        "hi_52w": round(hi52, 2), "lo_52w": round(lo52, 2),
        "pct_off_52w_high": round(pct(px, hi52), 1),
        "pct_above_52w_low": round(pct(px, lo52), 1),
        "sma50": round(sma(closes, 50), 2) if sma(closes, 50) else None,
        "sma200": round(sma(closes, 200), 2) if sma(closes, 200) else None,
        "pct_vs_sma50": round(pct(px, sma(closes, 50)), 1) if sma(closes, 50) else None,
        "pct_vs_sma200": round(pct(px, sma(closes, 200)), 1) if sma(closes, 200) else None,
        "atr14_pct": round(atr14 / px * 100, 2) if atr14 else None,
        "vol20_dailypct": round(vol20, 2) if vol20 else None,
        "vol100_dailypct": round(vol100, 2) if vol100 else None,
        "vol_contraction_ratio": round(contraction, 2) if contraction else None,
        "base_tightness_40d_pct": round(base40, 1) if base40 else None,
        "ret_3m_pct": round(ret_n(63), 1) if ret_n(63) is not None else None,
        "ret_6m_pct": round(ret_n(126), 1) if ret_n(126) is not None else None,
        "ret_12m_pct": round(ret_n(252), 1) if ret_n(252) is not None else None,
        "avg_deliv_pct_20d": round(st.mean(deliv[-20:]), 1) if len(deliv) >= 20 else None,
        "vol_surge_10v50": round(vol_surge, 2) if vol_surge else None,
    }


def price_path(eq, as_of, sell, pre_days=252, post_buffer=40, step=3):
    """Sampled [(date, close)] from ~as_of-1y through sell+buffer, for the story sparkline."""
    # window start = pre_days trading bars before as_of
    idx_asof = max((i for i, r in enumerate(eq) if r[0] <= as_of), default=None)
    if idx_asof is None:
        return {"path": [], "asof_date": as_of}
    start_i = max(0, idx_asof - pre_days)
    # end = post_buffer bars after sell (or end of data)
    idx_sell = max((i for i, r in enumerate(eq) if r[0] <= sell), default=len(eq) - 1)
    end_i = min(len(eq), idx_sell + post_buffer)
    seg = eq[start_i:end_i]
    # CL-SCR-09: down-sampling by `i % step` can skip the exact AS-OF bar (the gold line),
    # the SELL bar, and the in-window PEAK — on a "zero look-ahead" demo those are the bars
    # that MUST be on the sparkline at the right x. Force-include their seg-relative indices
    # alongside the regular stride, so the rendered path lands precisely on each landmark.
    keep = set(range(0, len(seg), step))
    keep.add(0)
    keep.add(len(seg) - 1)
    for absid in (idx_asof, idx_sell):          # as-of and sell bars (if inside the window)
        rel = absid - start_i
        if 0 <= rel < len(seg):
            keep.add(rel)
    if seg:                                     # the peak close within the window
        peak_rel = max(range(len(seg)), key=lambda j: seg[j][4])
        keep.add(peak_rel)
    sampled = [(seg[i][0], round(seg[i][4], 2)) for i in sorted(keep)]
    return {"path": sampled, "asof_date": as_of}


def reveal(eq, entry, horizon=190):
    fwd = [r for r in eq if r[0] >= entry]
    if len(fwd) < 2:
        return {"insufficient": True}
    entry_px = fwd[0][4]
    window = fwd[:horizon]
    peak_px, peak_date = entry_px, entry
    for d, o, h, l, c, v, dp in window:
        if c > peak_px:
            peak_px, peak_date = c, d
    return {
        "entry_date": fwd[0][0], "entry_close": round(entry_px, 2),
        "peak_date": peak_date, "peak_close": round(peak_px, 2),
        "peak_gain_pct": round((peak_px / entry_px - 1) * 100, 1),
        "horizon_days": len(window),
    }


def rs_vs_index(eq, idx, as_of, lookback=126):
    if not idx:
        return None
    hist = [(d, c) for (d, o, h, l, c, v, dp) in eq if d <= as_of and d in idx]
    if len(hist) < lookback + 5:
        return None
    rs = [(d, c / idx[d]) for d, c in hist]
    now = rs[-1][1]
    past = rs[-1 - lookback][1]
    rs_hi = max(v for _, v in rs[-lookback:])
    return {
        "rs_trend_6m_pct": round((now / past - 1) * 100, 1),
        "rs_at_6m_high": now >= rs_hi * 0.999,
    }


def main():
    idx, idx_name = find_index_series()
    out = {"generated_for": "Replay-the-Tape dossier", "index_used": idx_name, "heroes": []}
    for h in HEROES:
        sym, as_of = h["symbol"], h["as_of"]
        frame = load_symbol_history(sym, db_path=RESEARCH_DB)
        eq = load_eq(sym)
        px_asof = None
        for r in reversed(eq):
            if r[0] <= as_of:
                px_asof = r[4]
                break
        fdict = as_of_fundamentals(sym, as_of, price=px_asof, db_path=RESEARCH_DB)
        ledger = []
        for ptype, names, label in LEDGER_METRICS:
            kl = known_latest(frame, ptype, names, as_of)
            if kl:
                pe, rd, v = kl
                ledger.append({"metric": label, "period_end": pe, "report_date": rd,
                               "value": v, "lag_days": _days(pe, rd)})
        # latest report_date actually used (the freshest filing the score leaned on)
        latest_rd = max((l["report_date"] for l in ledger), default=None)
        out["heroes"].append({
            "symbol": sym, "name": h["name"], "lens": h["lens"], "as_of": as_of,
            "entry": h["entry"], "sell": h["sell"], "known_return": h["known_return"],
            "months": h["months"], "px_asof": px_asof,
            "latest_filing_used": latest_rd,
            "fundamentals_asof": fdict,
            "ledger": ledger,
            "technicals": technicals(eq, as_of),
            "rs": rs_vs_index(eq, idx, as_of),
            "reveal": reveal(eq, h["entry"]),
            "path": price_path(eq, as_of, h["sell"]),
        })
    print(json.dumps(out, indent=2, default=str))


def _days(period_end, report_date):
    from datetime import date
    try:
        a = date.fromisoformat(period_end)
        b = date.fromisoformat(report_date)
        return (b - a).days
    except Exception:
        return None


if __name__ == "__main__":
    main()
