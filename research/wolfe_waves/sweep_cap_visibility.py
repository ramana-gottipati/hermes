#!/usr/bin/env python3
"""READ-ONLY sweep — quantify what the old top-40-by-Q overlay cap hid (S89/D98 evidence).

For every symbol in the universe, rebuild the ◄/► walk EXACTLY as wolfe.overlay_for does:
  OLD (pre-D96):  dedupe(sorted(top-40-by-Q, newest-first))
  NEW (post-D96): dedupe(sorted(top-40-by-Q + fresh<=250-bars, newest-first))
and diff. For each newly-visible wave: winner-profile membership (D<=1 & p1>=2 & F<=2),
structure sub-score (p1*2+B+H, max 11), landing sub-score (C+F+G+I+D, max 13), fib-zone
presence (the scan silently drops zone-less winners).

READ-ONLY by construction: sqlite URI mode=ro. No writes anywhere.
Usage (on the VPS): cd /opt/hermes && .venv/bin/python research/wolfe_waves/sweep_cap_visibility.py [nifty500|inclusive]
First run (S89, 2026-07-10): nifty500 6,064 fresh / 3,334 outside cap / 3,121 newly visible /
307 winner / 2,814 no-surface / 104 TCS-archetype; inclusive-300 mirrors (56%, 252/300).
"""
import json
import sqlite3
import sys
import time

sys.path.insert(0, "/opt/hermes")
from src.automation import wolfe  # noqa: E402

CAP = 40          # the old _OVERLAY_MAX
FRESH = 250       # the D96 _FRESH_KEEP_BARS guarantee
SCAN_FRESH = 15   # winner_scan's live window


def last_idx(w):
    return w["p5"]["idx"] if w["p5"] else w["pivots"][3]["idx"]


def dedupe(lst):
    # verbatim copy of overlay_for's dedupe: same direction + pt4 within 2 bars
    out = []
    for w in lst:
        if any(w["direction"] == q["direction"]
               and abs(w["pivots"][3]["idx"] - q["pivots"][3]["idx"]) <= 2 for q in out):
            continue
        out.append(w)
    return out


def matched(w, pool):
    return any(w["direction"] == q["direction"]
               and abs(w["pivots"][3]["idx"] - q["pivots"][3]["idx"]) <= 2 for q in pool)


def subs(sc):
    structure = (sc.get("p1", 0) or 0) * 2 + (sc.get("B", 0) or 0) + (sc.get("H", 0) or 0)
    landing = ((sc.get("C", 0) or 0) + (sc.get("F", 0) or 0) + (sc.get("G", 0) or 0)
               + (sc.get("I", 0) or 0) + (sc.get("D", 0) or 0))
    return round(structure, 2), round(landing, 2)


def has_fib_zones(w):
    p = w["pivots"]
    try:
        _, _, zones = wolfe.fib_zones(p[0]["price"], p[1]["price"], p[2]["price"],
                                      p[3]["price"], direction=w["direction"])
        return bool(zones)
    except Exception:
        return False


def main():
    uni = sys.argv[1] if len(sys.argv) > 1 else "nifty500"
    conn = sqlite3.connect("file:/opt/hermes/data/hermes.db?mode=ro", uri=True)
    syms = wolfe.scan_universe(conn, uni)
    t0 = time.time()
    agg = {
        "universe": uni, "symbols": len(syms), "sym_done": 0, "sym_no_series": 0,
        "sym_with_conf": 0, "conf_total": 0, "fresh_total": 0,
        "fresh_outside_cap_raw": 0,        # confirmed, p5<=250 bars, NOT in top-40-by-Q
        "newly_visible": 0,                # net walk additions after dedupe/twin-matching
        "nv_winner": 0,                    # of those: pass winner profile (scan would have shown when fresh<=15)
        "nv_truly_missed": 0,              # of those: FAIL winner profile -> no surface ever showed them
        "nv_strong_structure": 0,          # structure sub-score >= 10 of 11
        "nv_strong_and_missed": 0,         # the TCS archetype: strong shape AND no surface
        "sym_gaining": 0,                  # symbols whose walk grew
        "walk_old_sum": 0, "walk_new_sum": 0,
        "winner_fresh15_nozones": 0,       # winner-profile, age<=15, but fib_zones empty -> scan drops silently
        "winner_fresh15_total": 0,
    }
    per_sym = []
    missed_rows = []
    for k, sym in enumerate(syms):
        if k and k % 50 == 0:
            sys.stderr.write("  ... %d/%d syms, %.0fs elapsed\n" % (k, len(syms), time.time() - t0))
            sys.stderr.flush()
        try:
            d = wolfe.analyze(conn, sym=sym, all_waves=True)
        except Exception as e:
            sys.stderr.write("  !! %s: %s\n" % (sym, e))
            continue
        agg["sym_done"] += 1
        if not d or not d.get("waves"):
            agg["sym_no_series"] += 1
            continue
        n = d["n"]
        conf = [w for w in d["waves"] if w["state"] == "CONFIRMED" and w["p5"]]
        if not conf:
            continue
        agg["sym_with_conf"] += 1
        agg["conf_total"] += len(conf)
        byq = sorted(conf, key=lambda w: -(w.get("quality_total") or 0))
        top = byq[:CAP]
        top_ids = set(id(w) for w in top)
        fresh_all = [w for w in conf if (n - 1 - last_idx(w)) <= FRESH]
        fresh_extra = [w for w in fresh_all if id(w) not in top_ids]
        agg["fresh_total"] += len(fresh_all)
        agg["fresh_outside_cap_raw"] += len(fresh_extra)
        old_walk = dedupe(sorted(top, key=lambda w: -last_idx(w)))
        new_walk = dedupe(sorted(top + fresh_extra, key=lambda w: -last_idx(w)))
        agg["walk_old_sum"] += len(old_walk)
        agg["walk_new_sum"] += len(new_walk)
        # scan blindspot: winner-profile fresh<=15 waves without fib zones (scan drops them)
        for w in fresh_all:
            if (n - 1 - last_idx(w)) <= SCAN_FRESH and wolfe.is_winner_profile(w.get("score")):
                agg["winner_fresh15_total"] += 1
                if not has_fib_zones(w):
                    agg["winner_fresh15_nozones"] += 1
        nv = [w for w in new_walk
              if (n - 1 - last_idx(w)) <= FRESH and not matched(w, old_walk)]
        if nv:
            agg["sym_gaining"] += 1
        row = {"sym": sym, "conf": len(conf), "walk_old": len(old_walk),
               "walk_new": len(new_walk), "nv": len(nv), "nv_winner": 0,
               "nv_missed": 0, "nv_strong_missed": 0}
        for w in nv:
            sc = w.get("score") or {}
            winner = wolfe.is_winner_profile(sc)
            structure, landing = subs(sc)
            strong = structure >= 10
            agg["newly_visible"] += 1
            if winner:
                agg["nv_winner"] += 1
                row["nv_winner"] += 1
            else:
                agg["nv_truly_missed"] += 1
                row["nv_missed"] += 1
            if strong:
                agg["nv_strong_structure"] += 1
            if strong and not winner:
                agg["nv_strong_and_missed"] += 1
                row["nv_strong_missed"] += 1
            missed_rows.append({
                "sym": sym, "dir": w["direction"], "p5": w["p5"]["date"],
                "age": n - 1 - last_idx(w), "q": w.get("quality_total"),
                "structure": structure, "landing": landing,
                "D": sc.get("D"), "C": sc.get("C"), "F": sc.get("F"),
                "p1": sc.get("p1"), "winner": int(bool(winner)),
                "up_pct": w.get("upside_pct"), "src": w.get("source")})
        per_sym.append(row)
    agg["elapsed_s"] = round(time.time() - t0, 1)
    # strongest-structure truly-missed first (the TCS archetype), then freshest
    missed_rows.sort(key=lambda r: (r["winner"], -r["structure"], r["age"]))
    out = {"agg": agg, "per_sym": per_sym, "waves": missed_rows}
    path = "/tmp/wolfe_sweep_%s.json" % uni
    with open(path, "w") as f:
        json.dump(out, f)
    sys.stderr.write("full JSON -> %s\n" % path)
    # stdout: the headline + top table
    print(json.dumps(agg, indent=1))
    print("\nTOP newly-visible waves (truly-missed first, by structure desc):")
    print("%-12s %-4s %-10s %3s  %5s  %4s/%4s  D C F p1  win  up%%   src" %
          ("SYM", "DIR", "P5-DATE", "AGE", "Q", "STR", "LND"))
    for r in missed_rows[:40]:
        print("%-12s %-4s %-10s %3d  %5.1f  %4.1f/%4.1f  %s %s %s %s   %s  %5s  %s" %
              (r["sym"], r["dir"][:4], r["p5"], r["age"], r["q"] or 0,
               r["structure"], r["landing"], r["D"], r["C"], r["F"], r["p1"],
               r["winner"], r["up_pct"] if r["up_pct"] is not None else "-", r["src"]))


if __name__ == "__main__":
    main()
