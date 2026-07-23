"""EMA-CROSSOVER FORWARD — the forward-test runner for the EMA-crossover family (S-EMA, 2026-07-23).

WHAT THIS IS. One command that makes the forward test of the whole EMA-crossover family mechanical —
the twin of `union_forward.py`, same discipline. It is a REPORTING LAYER over three SEALED engines:
no new selection logic, no new levers, no spec change. It reads each book's stored monthly series
from research.db (built by the sealed modules), gates the in-sample prefix for reproduction, slices
the post-freeze forward window, and judges each book against its own frozen criteria.

THE FAMILY (both EMA-crossover strategies + the fundable product this arc produced):
  MOM  = momentum_band_rsi, book CELL_B_TREND_STRONG (net) — 5-EMA(HLC) breaks the 13-EMA(high) band,
         with-trend, RSI>=70. Seal 0e90bf2c.
  REV  = reversal_oversold, book REVDD (net) — the early 5-EMA(HLC)-below-15-EMA(low) reversal probe.
         Seal 4d932089.
  LOW  = lowvol_sleeve_q, book lowvolq (net) — the quarterly + hysteresis low-vol sleeve (07-22d),
         the one corner of this exploration that survived the capacity fence. Seal b8c1dec4.

THE REGISTERED PREDICTIONS (the honest in-sample priors — what forward must live up to, stated BEFORE
any forward data so nobody re-writes the expectation later):
  MOM  in-sample R/V 0.71 / CAGR 13.2% / DD -63% — PAR with the index, huge drawdown. Prediction:
       matches the index but the excess is BETA not alpha, so C2 (alpha>0) is EXPECTED TO FAIL. A
       forward "beat" that is pure beta (beta>1.1, no alpha) is a FAIL by the frozen rule.
  REV  in-sample R/V -0.13 / CAGR -9.0% / DD -86% — net-NEGATIVE, and WORSE than its own random-entry
       control (-8.5%). Prediction: stays dead, well below the index; forward confirms descriptive-only.
  LOW  in-sample R/V 1.06 / CAGR 15.0% / DD -20.8%, beats the index, holds net R/V>0.89 to ~Rs500cr,
       corr-to-MOM 0.003. Prediction: THE GRADUATE — beats the index with ~1/3 less drawdown.

THE BET, in one line: we expect LOW to graduate, MOM to reveal itself as beta (fail C2), REV to stay
dead. The forward test adjudicates it mechanically — not our opinion.

BOUNDARY (encoded once). FREEZE = 2026-07 (the last in-sample month; the books are built through it).
The forward window = every completed month STRICTLY AFTER 2026-07, accruing automatically as the VPS
bhavcopy timer adds data and the sealed modules are rebuilt (`--rebuild` does that first). Criteria are
judged only at >= MIN_M = 24 completed forward months (8 quarters, matching the union family's >=8-Q
rule). Below that every verdict line is INTERIM (n/24) — on-track / behind, never PASS/FAIL.

WHAT IT PRINTS, in order:
  1. INTEGRITY + REPRODUCTION GATE — the three seals recomputed and checked; then each book's in-sample
     (<= FREEZE) headline R/V / CAGR / MaxDD re-derived live and gated to the recorded anchor. Any miss
     -> STOP: the in-sample prefix only moves if the engine or the price archive was EDITED.
  2. THE FORWARD WINDOW — per-month returns for MOM / REV / LOW beside Nifty 500; cumulative +
     annualized (>=4 legs); alpha / beta vs Nifty 500 (>=6 legs); MaxDD; all on the post-freeze cut.
  3. FROZEN CRITERIA per book (C1 beat index, C2 alpha>0 [beta>1.1 & no-alpha = beta-not-skill FAIL],
     C3 MaxDD not worse than the index, C4 no single month > 60% of total excess; LOW also carries its
     fence hurdle C5 net R/V > 0.89). INTERIM until MIN_M; at >= MIN_M the FAMILY ADJUDICATION fires:
     among sealed passers the highest forward alpha graduates, the rest retire to descriptive-only.

Run (VPS research venv; reads research.db + hermes.db):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.ema_crossover_forward            # report on stored books
  ... ema_crossover_forward --rebuild                     # rebuild the 3 sealed books first (current data)
  ... ema_crossover_forward --asof 2027-01                # cap the forward window at a month
This runner has NO seal of its own (it registers nothing) — it only verifies the three it reports on.
"""
from __future__ import annotations

import importlib
import json
import sys

import numpy as np

from . import prereg
from .common import OUT_DIR, research_conn
from .metrics import index_series

FREEZE = "2026-07"
MIN_M = 24                      # 8 quarters; no PASS/FAIL before this
BENCH = "Nifty 500"

SEALS = {
    "momentum_band_rsi": "0e90bf2cb7ea1beac9433ffdda6d88a62a7e856751df51cb0beda7d3cd16ea05",
    "reversal_oversold": "4d932089cf2e30137c2d9c5f74483049892468b8b6079ff8037e4efc673297c4",
    "lowvol_sleeve_q":   "b8c1dec488b96fde6fb7372ad3e726b9b8eea69163d8b473aef2b3913112f2e3",
}

# name -> (label, SQL for monthly (month,ret) net series, recorded in-sample anchor (R/V,CAGR%,DD%), prediction)
FAMILY = [
    ("MOM", "momentum (CELL_B_TREND_STRONG)",
     "SELECT month,mret FROM mbr_book WHERE key='CELL_B_TREND_STRONG' AND gross_net='net' ORDER BY month",
     (0.71, 13.2, -63.2), "par with index; excess is BETA -> C2 expected FAIL"),
    ("REV", "reversal (REVDD)",
     "SELECT month,mret FROM rev_book WHERE key='REVDD' AND gross_net='net' ORDER BY month",
     (-0.13, -9.0, -86.2), "dead (worse than random control); stays descriptive-only"),
    ("LOW", "low-vol v2 (lowvolq, quarterly+hysteresis)",
     "SELECT month,net FROM lowvolq_book ORDER BY month",
     (1.06, 15.0, -20.8), "THE GRADUATE — beats index with ~1/3 the drawdown, scales to ~Rs500cr"),
]


def _st(rets):
    r = np.asarray(rets, float)
    eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
    rv = float(r.mean() / r.std() * 12 ** .5) if r.std() > 0 else float("nan")
    cagr = (float(eq[-1]) ** (12 / len(r)) - 1) * 100
    return round(rv, 2), round(cagr, 1), round(dd * 100, 1)


def _dd(rets):
    eq = np.cumprod(1 + np.asarray(rets, float)); pk = np.maximum.accumulate(eq)
    return float((eq / pk - 1).min())


def _cum(rets):
    return float(np.prod(1 + np.asarray(rets, float)) - 1)


def _ann(rets):
    nav = float(np.prod(1 + np.asarray(rets, float)))
    y = len(rets) / 12.0
    return nav ** (1 / y) - 1 if y > 0 and nav > 0 else float("nan")


def _ab(r, br):
    if len(r) < 6:
        return None, None
    beta, alpha = np.polyfit(np.asarray(br, float), np.asarray(r, float), 1)
    return float(alpha) * 12, float(beta)          # annualised alpha, beta


def _series(rc, sql):
    return {m: v for m, v in rc.execute(sql)}


def _rebuild():
    for mod in ("momentum_band_rsi", "reversal_oversold", "lowvol_sleeve_q"):
        print(f"  rebuilding {mod} …", flush=True)
        importlib.import_module(f"explosive_moves.{mod}").build()


def main(asof=None, rebuild=False):
    if rebuild:
        print("### 0. REBUILD (current data)")
        _rebuild()

    # ---- 1. integrity + reproduction gate ----
    print("### 1. INTEGRITY + REPRODUCTION GATE")
    halt = False
    for mod, seal in SEALS.items():
        h = prereg.gate_hash(importlib.import_module(f"explosive_moves.{mod}").__doc__)
        ok = (h == seal)
        print(f"  seal {mod:<20} {'OK ' + h[:12] if ok else 'BROKEN ' + h[:12] + ' != ' + seal[:12]}")
        halt = halt or not ok
    if halt:
        print("  !! SEAL BROKEN — a spec docstring changed. STOP; do not trust any forward number below.")
        return

    rc = research_conn()
    idx = index_series(BENCH)
    ime = {}
    for d, c in zip(idx[0], idx[1]):
        ime[d[:7]] = c
    im = sorted(ime)
    bench = {im[i]: ime[im[i]] / ime[im[i - 1]] - 1 for i in range(1, len(im))}

    books = {}
    print("  reproduction (in-sample <= %s, gated to anchor):" % FREEZE)
    for name, label, sql, anchor, pred in FAMILY:
        s = _series(rc, sql)
        books[name] = s
        insample = [s[m] for m in sorted(s) if m <= FREEZE]
        rv, cg, dd = _st(insample)
        arv, acg, add = anchor
        ok = abs(rv - arv) <= 0.03 and abs(cg - acg) <= 0.2 and abs(dd - add) <= 0.6
        print(f"    {name:<4} {label:<42} R/V {rv:5.2f} CAGR {cg:6.1f} DD {dd:6.1f}  "
              f"anchor {arv:.2f}/{acg:.1f}/{add:.1f}  {'OK' if ok else '!! DRIFT — archive/engine edited; STOP'}")
        halt = halt or not ok
    if halt:
        print("  !! REPRODUCTION DRIFT — the in-sample prefix moved. STOP.")
        return

    # ---- registered predictions ----
    print("")
    print("### REGISTERED PREDICTIONS (frozen priors — what forward must live up to)")
    for name, label, sql, anchor, pred in FAMILY:
        print(f"  {name:<4} {pred}")
    print("  THE BET: LOW graduates, MOM reveals as beta (fails C2), REV stays dead. Adjudicated mechanically.")

    # ---- 2. forward window ----
    cap = asof or "9999"
    fmonths = sorted(m for m in bench if m > FREEZE and m <= cap
                     and all(m in books[n] for n, *_ in FAMILY))
    print("")
    print("### 2. FORWARD WINDOW (months strictly after %s%s) — %d completed"
          % (FREEZE, "" if not asof else " through %s" % asof, len(fmonths)))
    out = {"freeze": FREEZE, "min_months": MIN_M, "forward_months": len(fmonths),
           "asof": asof, "books": {}, "verdict_stage": "INTERIM" if len(fmonths) < MIN_M else "JUDGMENT"}
    if not fmonths:
        print("  (no completed forward month yet — the clock is armed. Rebuild after the next month-end;")
        print("   every book below is INTERIM 0/%d. The integrity gate above is today's live check.)" % MIN_M)
    else:
        br = [bench[m] for m in fmonths]
        hdr = "  leg     | " + BENCH.rjust(8) + " | " + " | ".join(n.rjust(7) for n, *_ in FAMILY)
        print(hdr)
        for m in fmonths:
            row = " | ".join(("%+6.1f%%" % (books[n][m] * 100)).rjust(7) for n, *_ in FAMILY)
            print("  %s | %+6.1f%% | %s" % (m, bench[m] * 100, row))
        print("")
        bcum, bdd = _cum(br), _dd(br)
        print("  book summaries (%d month(s)):" % len(fmonths))
        for name, label, sql, anchor, pred in FAMILY:
            r = [books[name][m] for m in fmonths]
            a, b = _ab(r, br)
            line = "    %-4s cum %+7.2f%%" % (name, _cum(r) * 100)
            if len(r) >= 4:
                line += "  ann %5.1f%%" % (_ann(r) * 100)
            if a is not None:
                line += "  alpha %+5.1f%%/yr  beta %4.2f" % (a * 100, b)
            elif len(r):
                line += "  (alpha/beta at <6 legs: not printed)"
            line += "  MaxDD %6.1f%%" % (_dd(r) * 100)
            print(line)
        print("    %-4s cum %+7.2f%%  MaxDD %6.1f%%   (the criterion benchmark)" % (BENCH[:4], bcum * 100, bdd * 100))

    # ---- 3. frozen criteria ----
    print("")
    print("### 3. FROZEN CRITERIA (%d/%d forward months -> %s)"
          % (len(fmonths), MIN_M, "JUDGMENT" if len(fmonths) >= MIN_M else "INTERIM — no verdict before %d" % MIN_M))
    passers = []
    if fmonths:
        br = [bench[m] for m in fmonths]
    for name, label, sql, anchor, pred in FAMILY:
        rec = {"prediction": pred, "anchor": anchor}
        if fmonths:
            r = [books[name][m] for m in fmonths]
            a, b = _ab(r, br)
            exc = [r[i] - br[i] for i in range(len(r))]
            tot = sum(exc)
            c1 = _cum(r) > _cum(br)
            c2 = a is not None and a > 0
            c3 = _dd(r) >= _dd(br)
            c4 = not (tot > 0 and max(exc) / tot > 0.60)
            c5 = (name != "LOW") or (_st(r)[0] > 0.89)
            beta_note = ""
            if b is not None and b > 1.1 and c1 and not c2:
                beta_note = "  << excess is beta, not skill (prereg: FAIL)"
            if len(fmonths) >= MIN_M:
                verdict = "PASS" if (c1 and c2 and c3 and c5) else "FAIL"
                if c1 and c2 and c3 and c5 and not c4:
                    verdict = "INCONCLUSIVE (C4) — extend window"
                if verdict == "PASS":
                    passers.append((a or -9, name))
            else:
                moot = a is None
                verdict = "on track" if (c1 and c3 and (c2 or moot) and c5) else "behind"
            print("  %-4s C1 beat-idx %-5s C2 alpha>0 %-5s C3 dd-ok %-5s C4 conc %-5s%s -> %s%s"
                  % (name, c1, ("n/a" if a is None else bool(c2)), c3, c4,
                     "" if name != "LOW" else " C5 R/V>0.89 %-5s" % c5, verdict, beta_note))
            rec.update(forward=_st(r), cum=round(_cum(r) * 100, 2), alpha=None if a is None else round(a * 100, 2),
                       beta=None if b is None else round(b, 2), verdict=verdict)
        else:
            print("  %-4s INTERIM 0/%d — clock armed, no leg yet" % (name, MIN_M))
            rec.update(forward=None, verdict="INTERIM 0/%d" % MIN_M)
        out["books"][name] = rec
    if len(fmonths) >= MIN_M:
        if passers:
            passers.sort(reverse=True)
            print("  FAMILY ADJUDICATION (frozen): GRADUATE = %s (highest forward alpha among passers); the rest retire to reference."
                  % passers[0][1])
            out["graduate"] = passers[0][1]
        else:
            print("  FAMILY ADJUDICATION (frozen): no sealed book passed — ALL DESCRIPTIVE-ONLY, never deployed.")
            out["graduate"] = None
    rc.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ema_crossover_forward.json").write_text(json.dumps(out, indent=1))
    print("")
    print("  one-pager -> out/ema_crossover_forward.json")


def selftest():
    assert _st([0.01] * 12)[0] > 0, "st sign"
    a, b = _ab([0.02, 0.01, 0.03, -0.01, 0.02, 0.01, 0.0, 0.02], [0.01, 0.0, 0.02, -0.02, 0.01, 0.0, -0.01, 0.01])
    assert b is not None, "ab computes at >=6"
    assert abs(_cum([0.1, 0.1]) - 0.21) < 1e-9, "cum"
    print("EMA_CROSSOVER_FORWARD selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        asof = None
        if "--asof" in sys.argv:
            asof = sys.argv[sys.argv.index("--asof") + 1]
        main(asof=asof, rebuild="--rebuild" in sys.argv)
