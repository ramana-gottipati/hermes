"""INSTITUTIONAL FLOW — does quarterly institutional ACCUMULATION (ΔDII+ΔFII) predict forward
out-performance? PRE-REGISTERED 2026-07-23 (S214-c). The FIRST orthogonal-data study — stock-level
smart-money flow, not price/volume.

WHY / WHAT IS NEW. Every prior study mines price/volume; this mines OWNERSHIP. Data ALREADY on the box:
`research.db.shareholding_history` — quarterly DII & FII holding % per stock, PIT-dated by `report_date`
(knowable ~30d after quarter-end), 2019→2026, 1,546 symbols, primary NSE-XBRL. DII = domestic
institutions (MF-DOMINATED; not broken out to pure MF — stated honestly); FII = foreign. Signal = the
QoQ change Δ(DII+FII) in percentage-points = net institutional accumulation. Thesis (patearn): real
institutional money accumulates BEFORE the re-rating; if so, the top-accumulation names out-perform forward.

PREDICTION ON RECORD (failure-ledger contract): CAUTIOUS-OPTIMISTIC — a higher prior than any crossover
(this is orthogonal fundamental flow, the patearn premise), but the signal is quarterly + widely watched
→ likely partially priced; net-of-cost fundability uncertain. History is only ~28 quarters (2019+) — a
real limit, stated. Metric basis D142 (annualised mean/sd, no rf); descriptive-only, SEBI-safe.

DESIGN (locked; PIT via `report_date` — NO look-ahead). Pivot shareholding_history to quarterly per
symbol: period_end → (DII, FII, report_date). Δinst[q] = (DII+FII)[q] − (DII+FII)[q−1] (percentage points).
ENTRY = first trading close on/after report_date[q] (PIT). Forward return at 63/126/252 trading days
(≈1Q/2Q/4Q), excess = symbol return − Nifty-500 over the identical span. Cross-sectional PER period_end:
rank eligible events by Δinst → QUINTILE 5 = accumulation, QUINTILE 1 = distribution. Eligibility: price
present; med_turn ≥ Rs 1cr at entry; DII & FII present for BOTH q and q−1.

GATE-1 SELECTION (PASS = all): n>=300 Q5 events; mean AND median 126d excess of Q5 > 0; Cliff's δ(Q5 vs
Q1) >= +0.05; Q5-median > Q1-median in BOTH halves (< / >= 2023-01). GATE-2 BOOK: long Q5 equal-weight
each period_end, hold ~1Q (63d), net tiered cost → quarterly return/vol; FUNDABLE if net R/V > 0.89 in
both halves AND Q5 book beats Q1 book. DISPOSITION pre-committed: PASS both → NEW candidate (fresh fences);
else REJECTED / descriptive-only, ledger records which gate failed + that this is the first flow study.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.inst_flow --build ; --selftest
"""
from __future__ import annotations

import bisect
import json
import sys
from datetime import datetime, timezone

import numpy as np

from .common import OUT_DIR, load_series, main_conn, research_conn
from .metrics import index_series

LIQ = 1e7
HZ = [63, 126, 252]
SEED = 42


def _cliffs(a, b):
    b = np.sort(np.asarray(b, float)); nb = len(b)
    if nb == 0 or len(a) == 0:
        return float("nan")
    tot = 0
    for x in a:
        tot += int(np.searchsorted(b, x, "left")) - (nb - int(np.searchsorted(b, x, "right")))
    return tot / (len(a) * nb)


def _cost_rt(mt):
    half = 0.0005 if mt >= 25e7 else (0.0010 if mt >= 5e7 else 0.0020)
    return 2 * half + 0.0012


def build():
    t0 = datetime.now(timezone.utc)
    rc = research_conn()
    tmp = {}
    for sym, pe, rd, metric, val in rc.execute(
        "SELECT symbol,period_end,report_date,metric,value FROM shareholding_history "
        "WHERE metric IN ('DIIs','FIIs') AND value IS NOT NULL"):
        d = tmp.setdefault((sym, pe), {})
        d["DII" if metric == "DIIs" else "FII"] = float(val)
        if rd:
            d["rd"] = rd
    rc.close()
    # per symbol: sorted quarters with both DII&FII and a report_date
    persym = {}
    for (sym, pe), d in tmp.items():
        if "DII" in d and "FII" in d and d.get("rd"):
            persym.setdefault(sym, []).append((pe, d["rd"], d["DII"] + d["FII"]))
    for sym in persym:
        persym[sym].sort()

    d, c = index_series("Nifty 500")
    idx_d = list(d); idx_c = np.asarray(c, float)

    def idx_ret(d0, d1):
        i0 = bisect.bisect_right(idx_d, d0) - 1
        i1 = bisect.bisect_right(idx_d, d1) - 1
        return idx_c[i1] / idx_c[i0] - 1.0 if i0 >= 0 and i1 >= 0 else np.nan

    mc = main_conn()
    ev = []            # (period_end, entry_date, delta_inst, {h: excess}, {h: raw}, mt)
    for sym in sorted(persym):
        qs = persym[sym]
        if len(qs) < 2:
            continue
        S = load_series(mc, sym)
        if S is None or S.n < 80:
            continue
        dates = S.date; ac = S.adj_close
        for k in range(1, len(qs)):
            pe, rd, tot = qs[k]
            dinst = tot - qs[k - 1][2]
            j = bisect.bisect_left(dates, rd)              # first trading day >= report_date (PIT)
            if j >= S.n or S.med_turn[j] < LIQ or ac[j] <= 0:
                continue
            exc = {}; raw = {}
            for h in HZ:
                if j + h < S.n and ac[j + h] > 0:
                    r = ac[j + h] / ac[j] - 1.0
                    e = r - idx_ret(dates[j], dates[j + h])
                    if np.isfinite(e):
                        exc[h] = e; raw[h] = r
            if 126 in exc:
                ev.append((pe, dates[j], dinst, exc, raw, float(S.med_turn[j])))
    mc.close()

    # cross-sectional quintiles per period_end (on Δinst)
    byq = {}
    for e in ev:
        byq.setdefault(e[0], []).append(e)
    q5 = {h: [] for h in HZ}; q1 = {h: [] for h in HZ}
    q5_half = {"h1": [], "h2": []}; q1_half = {"h1": [], "h2": []}
    book_q5 = {}; book_q1 = {}     # period_end -> mean 63d NET return of the quintile
    for pe, es in byq.items():
        if len(es) < 25:
            continue
        es_sorted = sorted(es, key=lambda x: x[2])          # ascending Δinst
        n = len(es_sorted); k = max(1, n // 5)
        lo = es_sorted[:k]; hi = es_sorted[-k:]
        for grp, store, half, bk in ((hi, q5, q5_half, book_q5), (lo, q1, q1_half, book_q1)):
            r63 = []
            for e in grp:
                for h in HZ:
                    if h in e[3]:
                        store[h].append(e[3][h])
                if 126 in e[3]:
                    (half["h1"] if e[1] < "2023-01" else half["h2"]).append(e[3][126])
                if 63 in e[4]:
                    r63.append(e[4][63] - _cost_rt(e[5]))
            if r63:
                bk[pe] = float(np.mean(r63))

    def qstats(store):
        return {str(h): {"n": len(store[h]), "mean%": round(float(np.mean(store[h])) * 100, 2),
                         "med%": round(float(np.median(store[h])) * 100, 2),
                         "pos%": round(float((np.array(store[h]) > 0).mean()) * 100, 1)} for h in HZ if store[h]}

    def book_rv(bk):
        qs = sorted(bk)
        if len(qs) < 8:
            return None
        r = np.array([bk[q] for q in qs])
        eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
        return (round(float(r.mean() / r.std() * 4 ** .5), 2),        # ~4 quarters/yr
                round((float(eq[-1]) ** (4 / len(r)) - 1) * 100, 1), round(dd * 100, 1), len(r))

    d126 = _cliffs(q5[126], q1[126]) if q5[126] and q1[126] else float("nan")
    h1ok = q5_half["h1"] and q1_half["h1"] and np.median(q5_half["h1"]) > np.median(q1_half["h1"])
    h2ok = q5_half["h2"] and q1_half["h2"] and np.median(q5_half["h2"]) > np.median(q1_half["h2"])
    G1 = len(q5[126]) >= 300
    G2 = q5[126] and np.mean(q5[126]) > 0 and np.median(q5[126]) > 0
    G3 = np.isfinite(d126) and d126 >= 0.05
    G4 = bool(h1ok and h2ok)
    gate1 = bool(G1 and G2 and G3 and G4)
    b5 = book_rv(book_q5); b1 = book_rv(book_q1)
    fundable = bool(b5 and b1 and b5[0] > 0.89 and b5[0] > b1[0])

    out = {
        "run_at": t0.strftime("%Y-%m-%d %H:%MZ"),
        "prediction": "CAUTIOUS-OPTIMISTIC (orthogonal fundamental flow; but quarterly+watched, ~28q only)",
        "events_total": len(ev), "quarters_used": len([q for q in byq if len(byq[q]) >= 25]),
        "GATE1_selection": {
            "Q5_accumulation": qstats(q5), "Q1_distribution": qstats(q1),
            "cliffs126_Q5_vs_Q1": round(d126, 4) if np.isfinite(d126) else None,
            "Q5>Q1_half1": bool(h1ok), "Q5>Q1_half2": bool(h2ok),
            "gates": {"G1_n300": bool(G1), "G2_Q5_mean_med_pos": bool(G2), "G3_cliffs.05": bool(G3), "G4_both_halves": bool(G4)},
            "VERDICT": "PASS" if gate1 else "FAIL-null",
        },
        "GATE2_book": {"Q5_net": b5, "Q1_net": b1, "hurdle": 0.89, "FUNDABLE": fundable},
        "DISPOSITION": "NEW candidate" if (gate1 and fundable) else "REJECTED — descriptive-only",
        "caveat": "DII is MF-DOMINATED domestic institutions (not pure MF); PIT via report_date; ~28 quarters 2019+",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "inst_flow.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"INST_FLOW: {len(ev)} events in {(datetime.now(timezone.utc)-t0).total_seconds():.0f}s")
    return out


def selftest():
    assert abs(_cliffs([3, 4, 5], [0, 1, 2]) - 1.0) < 1e-9 and _cost_rt(30e7) < _cost_rt(1e7)
    print("INST_FLOW selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    else:
        print(__doc__)
