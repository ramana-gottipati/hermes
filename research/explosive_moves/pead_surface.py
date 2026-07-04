"""Results-Reaction Ledger — the DESCRIPTIVE product of the 2026-07-05 PEAD study.

The PEAD *book* failed its gate (ledger § Experiment 2026-07-05: net Sharpe 0.10 vs bench 0.85), so
nothing tradeable ships. What DID validate is a descriptive event lens: on real BSE result dates, a
high earnings surprise CONFIRMED BY DELIVERED VALUE drifts materially over the next ~60 sessions
(SUE-Q5 × DELIV-T3 CAR60 +7.6%, t_cohort 1.9). This module turns that into an honest, point-in-time
per-stock artifact — the "how has THIS stock behaved after its results, and did the strong hand show
up on the tape" card — for the results-season war room (charter N1) and the stock dossier.

IT IS DESCRIPTIVE, NOT A FORECAST. Every number is a realized historical outcome or an explicitly
labelled population base-rate. No ranking, no buy/sell, no return promise. Same no-leak plumbing as
pead.py (real BSE dates from provenance_knowable; reaction measured from the close of day0+1).

Per event it reports: real results date, Net-Profit surprise (SUE, no analysts), whether the
2-session reaction ran on abnormal delivered value (deliv_x), and the realized abnormal move vs
Nifty 500 at +22 / +60 sessions. Per stock it reports that stock's OWN base rates (avg 60d abnormal
drift after results; and after its "delivery-confirmed beats" specifically) — self-referential, so no
population-breakpoint calibration is smuggled in — plus, for context only, the population study cell
the latest event falls in.

Reuses pead.py wholesale (sue_series, plausible, tape_features, index helpers). Read-only. Pure
compute — a live surface calls reactions()/summarize() on demand; nothing is stored (space doctrine).
Run on VPS:
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.pead_surface --demo DIXON TANLA ALKYLAMINE PERSISTENT
  ... -m explosive_moves.pead_surface --selftest   # offline, no DB
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date

from .common import RESEARCH_DB, main_conn
from . import pead

# Population base-rates from the 2026-07-05 A-study (CAR60 cohort means; DESCRIPTIVE CONTEXT ONLY).
# (sue_high, deliv_high) -> (mean_car60, n). "high" = top quintile SUE / top tercile delivery.
POP_CELL = {
    (True, True): (0.0762, 235),      # SUE-Q5 x DELIV-T3 — the confirmed cell
    (True, False): (0.0367, 200),     # strong surprise, weak delivery
    (False, True): (0.0290, None),    # weak surprise, strong delivery (delivery-tercile avg proxy)
    (False, False): (0.0000, None),
}
POP_ALL = (0.0350, 3130)
DELIV_HIGH = 1.5                       # "delivery-confirmed" descriptive threshold (x trailing median)


def _reactions_for(sym: str, hcon, rcon, idx_dates, idx_map) -> list[dict]:
    """Every past results event for one symbol with realized descriptive outcomes, oldest first."""
    real: dict[tuple, str] = {}
    for key, knew in hcon.execute(
            "SELECT key, knowable_at FROM provenance_knowable "
            "WHERE data_class='fundamentals_history' AND symbol=?", (sym,)):
        try:
            s, ptype, pend = key.split("|")
        except ValueError:
            continue
        k2 = str(knew)[:10]
        if pead.plausible(pend, k2) and (real.get((ptype, pend), "9999") > k2):
            real[(ptype, pend)] = k2
    np_map: dict[str, list[tuple[str, float]]] = {}
    for pt, pend, val in rcon.execute(
            "SELECT period_type, period_end, value FROM fundamentals_history "
            "WHERE symbol=? AND metric='Net Profit' AND value IS NOT NULL", (sym,)):
        np_map.setdefault(pt, []).append((str(pend)[:10], float(val)))
    for pt in np_map:
        np_map[pt].sort()
    sue_cache = {pt: pead.sue_series(np_map.get(pt, []), 1 if pt == "A" else 4) for pt in ("A", "Q")}

    cand = []
    for (ptype, pend), t0 in real.items():
        s = sue_cache.get(ptype, {}).get(pend)
        if s is not None:
            cand.append({"sym": sym, "ptype": ptype, "pend": pend, "t0": t0, "sue": s})
    if not cand:
        return []
    ss = pead.load_series(hcon, sym)
    if ss is None:
        return []
    out = []
    today = date.today().isoformat()
    for e in sorted(cand, key=lambda x: x["t0"]):
        fe = pead.tape_features(ss, e, idx_dates, idx_map)
        if fe is None:
            continue
        fe["is_settled"] = fe["dates_path"][-1] <= today if fe.get("dates_path") else True
        out.append(fe)
    return out


def summarize(events: list[dict]) -> dict:
    """This stock's OWN descriptive base rates (self-referential — no population calibration)."""
    settled = [e for e in events if e.get("car60") == e.get("car60")]
    n = len(settled)
    if n == 0:
        return {"n": 0}
    car60 = [e["car60"] for e in settled]
    beats = [e for e in settled if e["sue"] > 0 and e["deliv_x"] >= DELIV_HIGH]
    misses = [e for e in settled if e["sue"] <= 0]
    avg = sum(car60) / n
    hit = sum(1 for x in car60 if x > 0) / n
    out = {"n": n, "avg_car60": avg, "hit60": hit,
           "beats_n": len(beats), "misses_n": len(misses),
           "avg_car60_beats": (sum(e["car60"] for e in beats) / len(beats)) if beats else None,
           "avg_car60_misses": (sum(e["car60"] for e in misses) / len(misses)) if misses else None}
    return out


def latest_cell(events: list[dict], pop_sue_hi: float, pop_dlv_hi: float) -> dict | None:
    """Descriptive population-cell tag for the most recent event (context, not a prediction)."""
    if not events:
        return None
    e = events[-1]
    hi_s = e["sue"] >= pop_sue_hi
    hi_d = e["deliv_x"] >= pop_dlv_hi
    base, n = POP_CELL.get((hi_s, hi_d), POP_ALL)
    return {"t0": e["t0"], "sue": e["sue"], "deliv_x": e["deliv_x"],
            "sue_high": hi_s, "deliv_high": hi_d, "settled": e.get("is_settled", True),
            "realized_car60": e.get("car60"), "pop_base_car60": base, "pop_n": n}


def render(sym: str, events: list[dict]) -> str:
    """One compact text card. (A live HTML surface would format the same fields.)"""
    if not events:
        return f"{sym}: no PIT results events on record (needs real BSE dates + Net-Profit history)."
    s = summarize(events)
    lines = [f"{sym}: {len(events)} results reactions on real BSE dates "
             f"(descriptive — realized history, NOT a forecast)"]
    for e in events[-6:]:
        tag = "beat+deliv" if (e["sue"] > 0 and e["deliv_x"] >= DELIV_HIGH) else (
            "beat" if e["sue"] > 0 else "miss")
        c60 = f"{e['car60']*100:+5.1f}%" if e.get("car60") == e.get("car60") else "  n/a"
        lines.append(f"  {e['t0']} {e['ptype']}  SUE {e['sue']:+5.2f}  deliv {e['deliv_x']:4.2f}x  "
                     f"[{tag:>10}]  +22d {e['car22']*100:+5.1f}%  +60d {c60}")
    if s["n"]:
        lines.append(f"  OWN base rate: avg +60d abnormal {s['avg_car60']*100:+.1f}% "
                     f"(hit {s['hit60']*100:.0f}%, n={s['n']}); "
                     + (f"delivery-confirmed beats {s['avg_car60_beats']*100:+.1f}% (n={s['beats_n']})"
                        if s["avg_car60_beats"] is not None else "no delivery-confirmed beats yet"))
    return "\n".join(lines)


def demo(syms: list[str]) -> None:
    hcon = main_conn()
    rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
    idx_dates, idx_map = pead.index_levels(hcon)
    for sym in syms:
        ev = _reactions_for(sym.upper().strip(), hcon, rcon, idx_dates, idx_map)
        print(render(sym.upper().strip(), ev))
        print()
    rcon.close(); hcon.close()


def selftest() -> None:
    # summarize: self-referential base rates, beats vs misses partition
    evs = [
        {"t0": "2023-05-01", "ptype": "A", "sue": 2.0, "deliv_x": 1.8, "car22": 0.03, "car60": 0.08, "is_settled": True},
        {"t0": "2024-05-01", "ptype": "A", "sue": 1.5, "deliv_x": 1.0, "car22": 0.01, "car60": 0.02, "is_settled": True},
        {"t0": "2025-05-01", "ptype": "A", "sue": -1.0, "deliv_x": 0.9, "car22": -0.02, "car60": -0.05, "is_settled": True},
    ]
    s = summarize(evs)
    assert s["n"] == 3 and abs(s["avg_car60"] - (0.08 + 0.02 - 0.05) / 3) < 1e-9
    assert s["beats_n"] == 1 and abs(s["avg_car60_beats"] - 0.08) < 1e-9      # only the deliv-confirmed beat
    assert s["misses_n"] == 1 and abs(s["avg_car60_misses"] + 0.05) < 1e-9
    # latest_cell: high-SUE high-deliv -> the confirmed population cell
    c = latest_cell(evs[:1], pop_sue_hi=1.0, pop_dlv_hi=1.5)
    assert c["sue_high"] and c["deliv_high"] and c["pop_base_car60"] == 0.0762
    # empty + render degrade cleanly
    assert summarize([])["n"] == 0
    assert "no PIT results events" in render("XX", [])
    assert "results reactions" in render("DIXON", evs)
    print("PEAD_SURFACE selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--demo" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--demo"]
        demo(args or ["DIXON", "TANLA", "ALKYLAMINE", "PERSISTENT"])
    else:
        demo(["DIXON", "TANLA", "ALKYLAMINE", "PERSISTENT"])
