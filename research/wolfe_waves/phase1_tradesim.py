"""PHASE 1 — §C Wolfe trade-sim (Ramana's rules, 2026-06-25). Isolated, read-only.

Implements his trade mechanics on DAILY bars and measures the real outcomes:
  ENTRY   when the bar's LOW (bull) / HIGH (bear) lands within an extension-confluence
          zone, ±0.5% tolerance. Filled at that price. Zones tried first-reached-first;
          on a stop we re-enter at the next-deeper zone, and on a return back INTO a
          broken zone.
  STOP    zone far edge ∓ 0.3% (bull: zone_low×0.997 · bear: zone_high×1.003) — the
          anti-stop-hunt buffer.
  T1      the 0.618∩0.618 confluence (leg-1-2's 0.618 ∩ leg-3-4's) — book ONE-THIRD,
          move the stop to break-even, trail the rest. Only if it is reached BEFORE the
          EPA (else there is no T1).
  TARGET  the EPA (1-4) line — touch = trade COMPLETE (the "big win"). Steep-slope /
          low entry→EPA setups are flagged low-priority.
  MISSED  a setup whose price reached the EPA WITHOUT ever tagging a zone (reversed short
          of the confluence) — and the more-favorable price that was on offer.

Every metric is also split by the §B quality Q (Phase 0 showed Q stratifies outcomes).

⚠️ Universe note: the Nifty 500 list is CURRENT-only (no historical membership) →
survivorship-biased over history; run the inclusive control too. PIT: entry uses only
bars after point 4 (+confirm lag); zones come from points 1-4. Descriptive-only.

Run:  cd /opt/hermes && python3 research/wolfe_waves/phase1_tradesim.py [--universe nifty500|inclusive] [--debug SYM]
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

from src.automation import wolfe          # noqa: E402
from src.core.db import get_conn          # noqa: E402

CFG = {
    "zone_tol": 0.005,    # ±0.5% "in the zone" tolerance (his daily-data allowance)
    "sl_buf": 0.003,      # 0.3% anti-stop-hunt buffer beyond the zone far edge
    "t1_part": 1.0 / 3,   # book one-third at T1, trail the rest
    "t1_tol": 0.02,       # the two 0.618 levels must converge within this (else "too large" → no T1)
    "confirm_lag": 10,    # PIT: don't enter before point 4's fractal could have confirmed
    "window": 40,         # entry must trigger within N bars of point 4 (the call-validity window — to be measured)
    "trail_pct": 0.05,    # (unused now — the runner holds to EPA at break-even, his choice)
    "max_legs": 3,        # cap re-entries per setup (zone-1, zone-2, a return) — no churn
    "max_hold": 100000,   # DIAGNOSTIC: effectively no cap (reveals the TRUE EPA-hold distribution); set ~120 to time-bound the ride
}
BUCKETS = [(0, 10), (10, 13), (13, 16), (16, 99)]
COST_RT = 0.0025      # round-trip transaction cost per leg (brokerage+STT+slippage+impact, liquid IN equity)


# --------------------------------------------------------------------------- #
# geometry helpers                                                            #
# --------------------------------------------------------------------------- #
def entry_zones(p, direction):
    """Extension-confluence zones, ordered FIRST-REACHED first (bull: highest price as
    price falls into them; bear: lowest price as price rises)."""
    _e12, _e34, zones = wolfe.fib_zones(p[0].price, p[1].price, p[2].price, p[3].price, direction=direction)
    bull = direction == "BULL"
    return sorted(zones, key=lambda z: (-z["price"] if bull else z["price"]))


def t1_level(p, direction, tol):
    """0.618 of leg 1-2 ∩ 0.618 of leg 3-4. Returns the confluence price, or None when the
    two 0.618 levels don't converge (his 'if the 0.618 zone is too large, different story')."""
    bull = direction == "BULL"
    a, b, c, d = p[0].price, p[1].price, p[2].price, p[3].price
    if bull:
        l12 = max(a, b) - 0.618 * abs(b - a)
        l34 = max(c, d) - 0.618 * abs(d - c)
    else:
        l12 = min(a, b) + 0.618 * abs(b - a)
        l34 = min(c, d) + 0.618 * abs(d - c)
    mid = (l12 + l34) / 2.0
    if mid and abs(l12 - l34) / abs(mid) <= tol:
        return mid
    return None


def sret(entry, ex, bull):
    """signed return of one leg."""
    return (ex - entry) / entry if bull else (entry - ex) / entry


# --------------------------------------------------------------------------- #
# the trade simulation for ONE setup                                          #
# --------------------------------------------------------------------------- #
def simulate(w, highs, lows, closes, n, cfg, log=None):
    """Single forward pass. Re-entry only at a FRESH (deeper) zone or a broken zone price
    has RETURNED into after going decisively below it (no same-bar re-churn). Fill at the
    zone limit price; stop = zone far edge ∓0.3%; after T1 book ⅓ and TRAIL the ⅔."""
    p, bull = w.p, w.direction == "BULL"
    zones = entry_zones(p, w.direction)
    Q = w.score["total"] if w.score else 0
    out = {"dir": w.direction, "Q": Q, "entered": False, "t1": False, "epa": False,
           "stopped": False, "missed": False, "ret": 0.0, "legs": 0, "epa_pot": None,
           "favor_gap": None, "hold": None, "timeout": False,
           "comp": dict(w.score) if w.score else {}, "span": (w.p5.idx - p[0].idx) if w.p5 else 0,
           "z_r12": None, "z_r34": None, "entry_t": None}
    if not zones:
        return out

    def epa(t):
        return p[0].price + w.epa_slope * (t - p[0].idx)

    t1 = t1_level(p, w.direction, cfg["t1_tol"])
    tol, slb, trail = cfg["zone_tol"], cfg["sl_buf"], cfg["trail_pct"]
    start = p[3].idx + 1 + cfg["confirm_lag"]
    wend = min(n - 1, p[3].idx + cfg["window"])
    broken = [False] * len(zones)        # stopped out of this zone
    went_below = [False] * len(zones)    # price went DECISIVELY past the zone (enables return-re-entry)
    realized = 0.0
    favor = first_entry = None
    in_pos = False
    epx = ez = cur_sl = run_ext = None
    pos = 0.0
    booked = False
    t = start
    while t <= n - 1:
        hi, lo = highs[t], lows[t]
        for zi, z in enumerate(zones):                       # track decisive break-through (for returns)
            if (bull and lo < z["low"] * (1 - tol)) or ((not bull) and hi > z["high"] * (1 + tol)):
                went_below[zi] = True
        if not in_pos:
            if first_entry is None:
                px = lo if bull else hi
                if favor is None or (px < favor if bull else px > favor):
                    favor = px
                if t > wend:
                    break                                    # no first entry within the call window
            if out["legs"] < cfg["max_legs"]:
                for zi, z in enumerate(zones):
                    eligible = (not broken[zi]) or (broken[zi] and went_below[zi])   # fresh OR returned-broken
                    if not eligible:
                        continue
                    tag = (z["low"] * (1 - tol) <= lo <= z["high"] * (1 + tol)) if bull \
                        else (z["low"] * (1 - tol) <= hi <= z["high"] * (1 + tol))
                    if tag:
                        in_pos, ez, epx, pos, booked = True, zi, z["price"], 1.0, False
                        cur_sl = z["low"] * (1 - slb) if bull else z["high"] * (1 + slb)
                        run_ext = hi if bull else lo
                        broken[zi] = went_below[zi] = False
                        out["legs"] += 1
                        if first_entry is None:
                            first_entry, out["entered"], out["epa_pot"] = t, True, sret(epx, epa(t), bull)
                            out["z_r12"], out["z_r34"], out["entry_t"] = z["r12"], z["r34"], t
                        if log is not None:
                            log.append("  ENTER leg%d @%.2f zone%.2f[%s∩%s] bar=%d sl=%.2f t1=%s epa=%.2f"
                                       % (out["legs"], epx, z["price"], z["r12"], z["r34"], t, cur_sl,
                                          ("%.2f" % t1) if t1 else "none", epa(t)))
                        break
        else:
            if first_entry is not None and (t - first_entry) > cfg["max_hold"]:    # time-stop: ride to EPA within max_hold
                realized += pos * sret(epx, closes[t], bull)
                out["timeout"], in_pos = True, False
                break
            if (bull and hi >= epa(t)) or ((not bull) and lo <= epa(t)):           # EPA = COMPLETE (big win)
                realized += pos * sret(epx, epa(t), bull)
                out["epa"], out["hold"], in_pos = True, t - first_entry, False
                if log is not None:
                    log.append("    EPA @%.2f bar=%d  done (held %d bars)" % (epa(t), t, t - first_entry))
                break
            if (not booked) and t1 is not None and ((bull and hi >= t1) or ((not bull) and lo <= t1)):   # T1
                realized += cfg["t1_part"] * sret(epx, t1, bull)
                pos, booked, cur_sl, out["t1"] = 1 - cfg["t1_part"], True, epx, True   # book ⅓, stop→BE
                if log is not None:
                    log.append("    T1 @%.2f bar=%d  book 1/3, stop→BE, ride ⅔ to EPA" % (t1, t))
            if (bull and lo <= cur_sl) or ((not bull) and hi >= cur_sl):           # STOP (BE after T1 → ride to EPA)
                realized += pos * sret(epx, cur_sl, bull)
                out["stopped"], broken[ez], in_pos = True, True, False
                if log is not None:
                    log.append("    %s @%.2f bar=%d" % ("BE-stop" if booked else "STOP", cur_sl, t))
        t += 1
    if in_pos:
        realized += pos * sret(epx, closes[n - 1], bull)
    out["ret"] = realized
    if not out["entered"]:                                    # MISSED: reached EPA without us tagging a zone
        for tt in range(start, n):
            if (bull and highs[tt] >= epa(tt)) or ((not bull) and lows[tt] <= epa(tt)):
                out["missed"] = True
                break
        if favor is not None:
            zref = zones[0]["price"]
            out["favor_gap"] = (zref - favor) / zref if bull else (favor - zref) / zref
    return out


# --------------------------------------------------------------------------- #
# universe + driver                                                           #
# --------------------------------------------------------------------------- #
def nifty500(conn):
    # CL-RES-14: SURVIVORSHIP-BIASED universe. This is the CURRENT Nifty-500 membership
    # (MAX(snapshot_date)) applied to all history, so names that were in the index during
    # the backtest but later dropped out (the losers/delistings) are excluded — backtest
    # results on this universe are optimistically biased. Prefer `inclusive` (point-in-time
    # liquid universe). Kept for comparison only; runs print a SURVIVORSHIP-BIASED banner.
    return [r[0] for r in conn.execute(
        """SELECT symbol FROM stock_index_membership WHERE index_name='Nifty 500'
           AND snapshot_date=(SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name='Nifty 500')
           ORDER BY symbol""").fetchall()]


def inclusive(conn, topn=300):
    return [r[0] for r in conn.execute(
        """SELECT symbol FROM bhavcopy_rows WHERE series='EQ' AND (segment='CM' OR segment IS NULL) AND value>0
           GROUP BY symbol HAVING COUNT(*)>=500 ORDER BY AVG(value) DESC LIMIT ?""", (topn,)).fetchall()]


def run(universe_name="inclusive", debug=None):
    # CL-RES-14: default is now the point-in-time liquid `inclusive` universe. The
    # `nifty500` option is survivorship-biased (current membership applied to history)
    # and is opt-in only.
    with get_conn() as conn:
        names = nifty500(conn) if universe_name == "nifty500" else inclusive(conn)
        if debug:
            names = [debug]
        bias = "  [SURVIVORSHIP-BIASED — current membership]" if universe_name == "nifty500" else ""
        print("universe: %s (%d names)%s%s\n" % (universe_name, len(names), bias,
                                                 "  [DEBUG]" if debug else ""))
        rows = []
        for sym in names:
            s = wolfe.stock_series(conn, sym)
            if not s:
                continue
            _d, _o, highs, lows, closes = s
            n = len(closes)
            waves, _ = wolfe.detect_waves(highs, lows, closes)
            for w in waves:
                if w.state != "CONFIRMED" or not w.p5 or not w.score:
                    continue
                log = [] if debug else None
                r = simulate(w, highs, lows, closes, n, CFG, log=log)
                r["sym"] = sym
                if r["entered"] and r["entry_t"] is not None:
                    r["year"] = int(_d[r["entry_t"]][:4])
                rows.append(r)
                if debug and (r["entered"] or r["missed"]):
                    print("%s  %s  Q%.1f  p4=%s p5=%s" % (sym, w.direction, r["Q"], _d[w.p[3].idx], _d[w.p5.idx]))
                    for ln in (log or []):
                        print(ln)
                    print("   => entered=%s t1=%s EPA=%s stop=%s legs=%d ret=%+.2f%% missed=%s epa_pot=%s\n"
                          % (r["entered"], r["t1"], r["epa"], r["stopped"], r["legs"], 100 * r["ret"],
                             r["missed"], ("%.1f%%" % (100 * r["epa_pot"])) if r["epa_pot"] is not None else "-"))
        if debug:
            return
        report(rows)
        decode(rows)
        winner_report(rows)
        oos_report(rows)


def _net(r):                              # net of round-trip cost per leg (+ the T1 partial exit)
    return r["ret"] - COST_RT * r["legs"] - (COST_RT * CFG["t1_part"] if r["t1"] else 0.0)


def decode(rows):
    """What ARE the large hits, and what separates the WINNERS (rode to EPA) from the
    LOSERS (stopped)? The distribution is positive-skew → the strategy IS the big hits;
    decode what they have in common, then we select for it."""
    from collections import Counter
    def med(xs):
        return sorted(xs)[len(xs) // 2] if xs else 0
    ent = [r for r in rows if r["entered"]]
    rets = sorted(r["ret"] for r in ent)
    n = len(rets)
    pc = lambda q: rets[min(n - 1, int(q * n))]
    print("\n" + "=" * 86)
    print("DECODE — the large hits")
    print("  return pctiles (gross): p50 %+.1f%%  p90 %+.1f%%  p95 %+.1f%%  p99 %+.1f%%  max %+.1f%%" % (
        100 * pc(.5), 100 * pc(.9), 100 * pc(.95), 100 * pc(.99), 100 * rets[-1]))
    desc = sorted((r["ret"] for r in ent), reverse=True)
    pos = sum(r for r in rets if r > 0) or 1e-9
    for fr in (0.01, 0.05, 0.10):
        print("  top %2.0f%% of trades = %3.0f%% of all gross profit" % (100 * fr, 100 * sum(desc[:int(fr * n)]) / pos))
    won = [r for r in ent if r["epa"]]                       # rode to the EPA (the wins)
    lost = [r for r in ent if r["stopped"] and not r["epa"]]  # stopped out (the losers)
    big = [r for r in ent if r["ret"] >= pc(.95)]            # the top-5% large hits
    sh = lambda pop, f: 100 * sum(1 for r in pop if f(r)) / max(1, len(pop))
    mc = lambda pop, c: med([r["comp"].get(c, 0) for r in pop if r.get("comp")])
    mp = lambda pop, k: med([r[k] for r in pop if r.get(k) is not None])
    print("\n  feature           WINNERS(EPA,%d)  LOSERS(stop,%d)  BIG-HITS(top5%%,%d)" % (len(won), len(lost), len(big)))
    print("   BULL %%             %7.0f          %7.0f          %7.0f" % (sh(won, lambda r: r["dir"] == "BULL"), sh(lost, lambda r: r["dir"] == "BULL"), sh(big, lambda r: r["dir"] == "BULL")))
    print("   median Q           %7.1f          %7.1f          %7.1f" % (med([r["Q"] for r in won]), med([r["Q"] for r in lost]), med([r["Q"] for r in big])))
    print("   entry→EPA med %%    %+7.1f          %+7.1f          %+7.1f" % (100 * mp(won, "epa_pot"), 100 * mp(lost, "epa_pot"), 100 * mp(big, "epa_pot")))
    print("   wave span med      %7d          %7d          %7d" % (mp(won, "span"), mp(lost, "span"), mp(big, "span")))
    print("   legs med           %7d          %7d          %7d" % (mp(won, "legs"), mp(lost, "legs"), mp(big, "legs")))
    print("   T1-hit %%           %7.0f          %7.0f          %7.0f" % (sh(won, lambda r: r["t1"]), sh(lost, lambda r: r["t1"]), sh(big, lambda r: r["t1"])))
    for c in ("p1", "B", "C", "F", "G", "H", "I", "D"):
        print("   §B %-2s med         %7.1f          %7.1f          %7.1f" % (c, mc(won, c), mc(lost, c), mc(big, c)))
    zc = Counter((r["z_r12"], r["z_r34"]) for r in big if r.get("z_r12"))
    print("   big-hit entry zones (r12∩r34, top): %s" % zc.most_common(5))


def report(rows):
    from collections import defaultdict
    def med(xs):
        return sorted(xs)[len(xs) // 2] if xs else 0.0
    ent = [r for r in rows if r["entered"]]
    n_all, n_ent = len(rows), len(ent)
    n_epa = sum(1 for r in ent if r["epa"])
    n_t1 = sum(1 for r in ent if r["t1"])
    n_stop = sum(1 for r in ent if r["stopped"] and not r["epa"])
    n_miss = sum(1 for r in rows if r["missed"])
    print("=" * 86)
    print("setups=%d  entered=%d (%.0f%%)  MISSED(reached EPA, no entry)=%d  → we capture %.0f%% of EPA-reaching moves"
          % (n_all, n_ent, 100 * n_ent / max(1, n_all), n_miss, 100 * n_epa / max(1, n_epa + n_miss)))
    print("of entered: EPA(big win)=%d (%.0f%%)  T1=%d (%.0f%%)  stopped=%d (%.0f%%)" % (
        n_epa, 100 * n_epa / max(1, n_ent), n_t1, 100 * n_t1 / max(1, n_ent), n_stop, 100 * n_stop / max(1, n_ent)))
    g = [r["ret"] for r in ent]
    nt = [_net(r) for r in ent]
    print("avg return  GROSS=%+.2f%%   NET(%.2f%%/leg costs)=%+.2f%%   |  median  gross=%+.2f%%  net=%+.2f%%" % (
        100 * sum(g) / max(1, len(g)), 100 * COST_RT, 100 * sum(nt) / max(1, len(nt)),
        100 * med(g), 100 * med(nt)))
    print("\n  by Q bucket (entered):    n   ent% EPA% T1% stop% gRet  netRet medNet hit% entry→EPA EPAhold")
    for lo, hi in BUCKETS:
        b_all = [r for r in rows if lo <= r["Q"] < hi]
        b = [r for r in b_all if r["entered"]]
        if not b_all:
            continue
        f = lambda k: 100 * sum(1 for r in b if r[k]) / max(1, len(b))
        st = 100 * sum(1 for r in b if r["stopped"] and not r["epa"]) / max(1, len(b))
        ar = 100 * sum(r["ret"] for r in b) / max(1, len(b))
        nr = 100 * sum(_net(r) for r in b) / max(1, len(b))
        mn = 100 * med([_net(r) for r in b])
        hit = 100 * sum(1 for r in b if r["ret"] > 0) / max(1, len(b))
        ep = 100 * med([r["epa_pot"] for r in b if r["epa_pot"] is not None])
        mh = med([r["hold"] for r in b if r["epa"] and r["hold"] is not None])
        print("   Q[%2d-%2d): %6d  %3.0f %4.0f %3.0f %4.0f %+6.2f %+6.2f %+6.2f %3.0f  %+7.1f  %5d"
              % (lo, hi, len(b_all), 100 * len(b) / len(b_all), f("epa"), f("t1"), st, ar, nr, mn, hit, ep, mh))
    print("\n  by direction (entered):    n   EPA%  hit%   gRet   netRet  medNet")
    for d in ("BULL", "BEAR"):
        b = [r for r in ent if r["dir"] == d]
        if not b:
            continue
        print("   %-4s     %8d  %4.0f  %4.0f  %+6.2f  %+6.2f  %+6.2f" % (
            d, len(b), 100 * sum(1 for r in b if r["epa"]) / len(b), 100 * sum(1 for r in b if r["ret"] > 0) / len(b),
            100 * sum(r["ret"] for r in b) / len(b), 100 * sum(_net(r) for r in b) / len(b), 100 * med([_net(r) for r in b])))
    bysym = defaultdict(list)
    for r in rows:
        bysym[r["sym"]].append(r)
    nn = len(bysym)
    print("\n  per-candidate (%d names): setups/name=%.1f (=point-5s)  entered/name=%.1f  EPA-wins/name=%.1f" % (
        nn, n_all / max(1, nn), n_ent / max(1, nn), n_epa / max(1, nn)))
    top = sorted(bysym.items(), key=lambda kv: -sum(1 for r in kv[1] if r["epa"]))[:8]
    print("   top names by EPA-wins:  " + ", ".join(
        "%s %d/%d" % (s, sum(1 for r in rs if r["epa"]), len(rs)) for s, rs in top))


def winner_report(rows):
    """Test the winner-profile filter built from the DECODE (selectable-at-entry traits:
    strong point-1, not-narrowest zone, closer reachable EPA). Does selecting on it LIFT
    hit%/net where the §B Q-score INVERTED — and, the real prize, does it make the BEARS
    (the beta-neutral side) actually work?"""
    ent = [r for r in rows if r["entered"]]

    def stat(pop):
        n = len(pop)
        if not n:
            return "n=     0  (none)"
        hit = 100 * sum(1 for r in pop if r["ret"] > 0) / n
        epa = 100 * sum(1 for r in pop if r["epa"]) / n
        net = 100 * sum(_net(r) for r in pop) / n
        mn = 100 * sorted(_net(r) for r in pop)[n // 2]
        return "n=%6d  hit %3.0f%%  EPA %3.0f%%  net %+6.2f%%  medNet %+6.2f%%" % (n, hit, epa, net, mn)

    flt = [
        ("ALL entered (baseline)", lambda r: True),
        ("D<=1  EPA reachable (<20%)", lambda r: r["comp"].get("D", 9) <= 1),
        ("D==0  EPA very close (<10%)", lambda r: r["comp"].get("D", 9) == 0),
        ("D>=2  EPA far (the tail)", lambda r: r["comp"].get("D", 9) >= 2),
        ("p1>=2  strong point-1 only", lambda r: r["comp"].get("p1", 0) >= 2),
        ("D<=1 & p1>=2 & F<=2 (full)", lambda r: r["comp"].get("D", 9) <= 1 and r["comp"].get("p1", 0) >= 2 and r["comp"].get("F", 9) <= 2),
    ]
    print("\n" + "=" * 86)
    print("WINNER-PROFILE FILTER (decode-built; progressively add winner traits):")
    for name, f in flt:
        sub = [r for r in ent if f(r)]
        print("  %-30s ALL  %s" % (name, stat(sub)))
        print("  %-30s BULL %s" % ("", stat([r for r in sub if r["dir"] == "BULL"])))
        print("  %-30s BEAR %s" % ("", stat([r for r in sub if r["dir"] == "BEAR"])))
        print()


def oos_report(rows):
    """Walk-forward: does the FIXED winner-profile (D<=1 & p1>=2 & F<=2) hold in EVERY era
    independently, or does one era carry it? The rule came from the decode medians (not a
    parameter sweep), so per-era consistency = real edge; one-era-only = in-sample mirage."""
    ent = [r for r in rows if r["entered"] and r.get("year")]
    eras = [(2004, 2011), (2012, 2018), (2019, 2026)]
    wp = lambda r: r["comp"].get("D", 9) <= 1 and r["comp"].get("p1", 0) >= 2 and r["comp"].get("F", 9) <= 2

    def stat(pop):
        n = len(pop)
        if not n:
            return "n=    0  (none)"
        hit = 100 * sum(1 for r in pop if r["ret"] > 0) / n
        net = 100 * sum(_net(r) for r in pop) / n
        mn = 100 * sorted(_net(r) for r in pop)[n // 2]
        return "n=%5d  hit %3.0f%%  net %+6.2f%%  medNet %+6.2f%%" % (n, hit, net, mn)

    print("\n" + "=" * 86)
    print("OUT-OF-SAMPLE / WALK-FORWARD — fixed winner-profile (D<=1 & p1>=2 & F<=2) per era:")
    for a, b in eras:
        era = [r for r in ent if a <= r["year"] <= b]
        win = [r for r in era if wp(r)]
        print("  %d-%d  baseline ALL   %s" % (a, b, stat(era)))
        print("           winner   ALL   %s" % stat(win))
        print("           winner   BULL  %s" % stat([r for r in win if r["dir"] == "BULL"]))
        print("           winner   BEAR  %s" % stat([r for r in win if r["dir"] == "BEAR"]))
        print()


if __name__ == "__main__":
    uni = "inclusive"          # CL-RES-14: default to the PIT-liquid universe (nifty500 is opt-in, biased)
    dbg = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--universe" and i + 1 < len(args):
            uni = args[i + 1]
        if a == "--debug" and i + 1 < len(args):
            dbg = args[i + 1]
    run(uni, dbg)
