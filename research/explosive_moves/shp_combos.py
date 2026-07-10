"""E-14 — shareholding-release combos (post-release drift), PRE-REGISTERED 2026-07-10 (S85f).

The event is a quarterly Reg-31 shareholding pattern BECOMING PUBLIC; the treatment is
what it disclosed (ΔQoQ ownership moves). Runnable only after the ~Jul-21 flood delivers
real release dates and the S85d lag calibration (data-perfection lane) makes historical
quarters honestly datable — this module therefore ships SELF-ARMING (the E-02/E-04
pattern): monthly `--run` aborts-with-census until reconciliation passes, then completes.

LEDGER PRIORS BOUND INTO THIS DESIGN (failure-ledger pass, 2026-07-10):
  * Pledge-tail null: the CCI-veto precedent showed pledge cohorts crash no more often
    than controls (6.8% vs 6.9% @−20%/6m; 12.6 vs 12.5 @12m) — so pledge combos are
    REPORTED-ONLY here (coverage 164 rows besides), never gated, until a design beats
    those exact numbers.
  * Distress-composite coverage cliff: boards-not-gates below coverage (46/187 overlap).
  * F7: only POST-public ownership information exists (T+2 structural).
  * E-03 class rule: <8 quarterly cohorts = no clustered claim.
  * E-11/concall class rule: covered-universe beta is the null — placebo mandatory.
  * QG-lift lesson: LEVELS are dead or inverted; only CHANGES carry right-signed
    information — hence every treatment below is a ΔQoQ.

DEFINITIONS:
  Event = (symbol, period_end) release with a usable date: REAL (provenance_knowable,
  data_class='shareholding_history') where present, else the CALIBRATED report_date once
  the S85d calibration artifact exists (`source` distinguishes; both counted in the
  census). ΔQoQ = this quarter's % minus previous quarter's %, per metric; the 0.25pp
  promoter-inertia floor (postmortem: 86% of names/quarter sit inside it) is the
  materiality threshold everywhere.

PRE-REGISTERED RECONCILIATION GATE (the run precondition):
  (a) dated releases ≥ 1,000 (real + calibrated union) — the "flood landed and the
      calibration exists" test; 164 real-dated keys pre-flood,
  (b) each GATED combo spans ≥ 8 quarterly cohorts with ≥ 5 events, and
  (c) each GATED combo has n ≥ 50 usable events (the power rule).
  NOT-YET → "ABORT-RECONCILIATION (pre-registered)" + census, DM'd.

PRE-REGISTERED RESULT GATE (three combos ONLY — multiplicity capped by design):
  G1  ΔPromoters ≥ +0.25pp                       → expect +
  G2  ΔPromoters ≤ −0.25pp                       → expect −
  G3  ΔPromoters ≥ +0.25pp AND ΔFII ≥ +0.25pp    → expect + (double conviction)
  Readout: CAR22/CAR60 vs Nifty 500 (reaction_row, entry = t0 + lag), quarterly
  cohort-clustered t. PASS per combo: |t_cohort| ≥ 2, sign as expected, AND the
  observed mean clears the date-shuffle placebo p95 (n=200, seed 42).
  Reported, NEVER gated: pledge-Δ splits of G1/G2 (the ledger null stands), single-ΔFII,
  ΔDII, ΔPublic — context columns for the census.
  FAIL: publish the null. Book leg: NOT run (F6 priors; own pre-registration).

CLI (research venv):
  python -m explosive_moves.shp_combos --reconcile [--notify]
  python -m explosive_moves.shp_combos --run [--notify]         # the monthly timer entry
  python -m explosive_moves.shp_combos --selftest
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
from datetime import datetime

import numpy as np

from . import evlib
from .campaign_arcs import _notify_dm
from .common import RESEARCH_DB, load_series, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "shp_combos.json")
DELTA_FLOOR = 0.25
MIN_DATED = 1000
MIN_COHORTS = 8
MIN_PER_COHORT = 5
MIN_COMBO_N = 50
COMBOS = ("G1_promoter_up", "G2_promoter_down", "G3_promoter_and_fii_up")


def load_releases(hcon, rcon) -> tuple[list[dict], dict]:
    """(release events with ΔQoQ per metric + a usable date, census). Real dates from
    provenance_knowable win; calibrated report_date (source tells) is the fallback."""
    real: dict = {}
    for key, knew in hcon.execute(
            "SELECT key, knowable_at FROM provenance_knowable "
            "WHERE data_class='shareholding_history'"):
        parts = str(key).split("|")
        sym, pend = parts[0], parts[-1]
        k2 = str(knew)[:10]
        if (sym, pend) not in real or real[(sym, pend)] > k2:
            real[(sym, pend)] = k2
    rows = rcon.execute(
        "SELECT symbol, period_end, metric, value, report_date, source "
        "FROM shareholding_history WHERE metric IN "
        "('Promoters','FIIs','DIIs','Public','Promoter Pledge') "
        "ORDER BY symbol, period_end").fetchall()
    by_sp: dict = {}
    for sym, pend, metric, val, rdt, src in rows:
        by_sp.setdefault((sym, str(pend)[:10]), {})[metric] = (val, str(rdt or "")[:10],
                                                               src or "")
    by_sym: dict = {}
    for (sym, pend), m in sorted(by_sp.items()):
        by_sym.setdefault(sym, []).append((pend, m))
    events, census = [], {"releases": len(by_sp), "real_dated": 0, "calibrated_dated": 0,
                          "undated": 0, "no_prior": 0}
    for sym, seq in by_sym.items():
        for i in range(1, len(seq)):
            pend, cur = seq[i]
            _pp, prev = seq[i - 1]
            deltas = {}
            for metric in ("Promoters", "FIIs", "DIIs", "Public", "Promoter Pledge"):
                a, b = cur.get(metric), prev.get(metric)
                if a is not None and b is not None and a[0] is not None and b[0] is not None:
                    deltas[metric] = float(a[0]) - float(b[0])
            if not deltas:
                census["no_prior"] += 1
                continue
            if (sym, pend) in real:
                t0, dsrc = real[(sym, pend)], "real"
                census["real_dated"] += 1
            else:
                rd = next((v[1] for v in cur.values() if v[1]), "")
                calib = any("calib" in (v[2] or "").lower() for v in cur.values())
                if rd and calib:
                    t0, dsrc = rd, "calibrated"
                    census["calibrated_dated"] += 1
                else:
                    census["undated"] += 1
                    continue
            events.append({"sym": sym, "pend": pend, "t0": t0, "dsrc": dsrc, **{
                f"d_{k.split()[0].lower()}": v for k, v in deltas.items()}})
    census["dated_events"] = len(events)
    return events, census


def tag_combos(events: list[dict]) -> None:
    for e in events:
        dp = e.get("d_promoters")
        df = e.get("d_fiis")
        e["G1_promoter_up"] = dp is not None and dp >= DELTA_FLOOR
        e["G2_promoter_down"] = dp is not None and dp <= -DELTA_FLOOR
        e["G3_promoter_and_fii_up"] = (dp is not None and df is not None
                                       and dp >= DELTA_FLOOR and df >= DELTA_FLOOR)


def reconcile(events: list[dict], census: dict) -> dict:
    tag_combos(events)
    dated = census.get("real_dated", 0) + census.get("calibrated_dated", 0)
    combo_stats = {}
    all_ok = dated >= MIN_DATED
    for c in COMBOS:
        sel = [e for e in events if e.get(c)]
        coh: dict = {}
        for e in sel:
            coh.setdefault(evlib.cohort_of(e["t0"]), []).append(e)
        ok_coh = sum(1 for v in coh.values() if len(v) >= MIN_PER_COHORT)
        combo_stats[c] = {"n": len(sel), "cohorts_ge5": ok_coh}
        all_ok = all_ok and len(sel) >= MIN_COMBO_N and ok_coh >= MIN_COHORTS
    return {"go": bool(all_ok), "dated": dated, "need_dated": MIN_DATED,
            "combos": combo_stats, "census": census,
            "need": f"dated>={MIN_DATED}; per combo n>={MIN_COMBO_N} & "
                    f">={MIN_COHORTS} cohorts >={MIN_PER_COHORT}"}


def _census_line(rec: dict) -> str:
    cs = rec["combos"]
    return (f"🧾 E-14 reconciliation: {'GO' if rec['go'] else 'NOT-YET'} — dated "
            f"{rec['dated']}/{rec['need_dated']} "
            f"(real {rec['census'].get('real_dated', 0)} / calib "
            f"{rec['census'].get('calibrated_dated', 0)}) · "
            + " · ".join(f"{c.split('_')[0]} n={cs[c]['n']}/{MIN_COMBO_N} "
                         f"coh {cs[c]['cohorts_ge5']}/{MIN_COHORTS}" for c in COMBOS))


def reconcile_cli(notify: bool = False) -> dict:
    hcon = main_conn()
    rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
    events, census = load_releases(hcon, rcon)
    rcon.close()
    hcon.close()
    rec = reconcile(events, census)
    line = _census_line(rec)
    print(line, flush=True)
    print(json.dumps(rec, indent=1, default=str), flush=True)
    if notify:
        _notify_dm(line)
    return rec


def run(notify: bool = False) -> dict:
    hcon = main_conn()
    rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
    events, census = load_releases(hcon, rcon)
    rcon.close()
    rec = reconcile(events, census)
    line = _census_line(rec)
    out: dict = {"study": "E-14 shareholding-release combos (post-release)",
                 "reconciliation": rec}
    if not rec["go"]:
        out["verdict"] = "ABORT-RECONCILIATION (pre-registered)"
        hcon.close()
    else:
        idx_dates, idx_map = evlib.index_levels(hcon)
        series: dict = {}
        usable = []
        for e in events:
            if not any(e.get(c) for c in COMBOS):
                continue
            ss = series.setdefault(e["sym"], load_series(hcon, e["sym"]))
            if ss is None:
                continue
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "S", "pend": e["pend"],
                                  "t0": e["t0"], "sue": 0.0}, idx_dates, idx_map)
            if r is None or r["car60"] != r["car60"]:
                continue
            usable.append({**e, "car22": r["car22"], "car60": r["car60"]})
        rng = random.Random(42)
        verdicts = []
        expect = {"G1_promoter_up": 1, "G2_promoter_down": -1, "G3_promoter_and_fii_up": 1}
        for c in COMBOS:
            sel = [e for e in usable if e.get(c)]
            st = evlib.cohort_t([(e["t0"], e["car60"]) for e in sel])
            out[f"{c}_car60"] = st
            observed = st.get("mean", float("nan"))
            null_means = []
            for k in range(200):
                cars = []
                for e in sel:
                    ss = series.get(e["sym"])
                    if ss is None:
                        continue
                    lo_i, hi_i = evlib.eligible_indices(ss, 60)
                    if hi_i <= lo_i:
                        continue
                    i0 = rng.randrange(lo_i, hi_i)
                    r = reaction_row(ss, {"sym": e["sym"], "ptype": "S", "pend": e["pend"],
                                          "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
                    if r is not None and r["car60"] == r["car60"]:
                        cars.append(r["car60"])
                if cars:
                    null_means.append(float(np.mean(cars)))
            pl = evlib.placebo_stats(observed, null_means)
            out[f"{c}_placebo"] = pl
            tcv = st.get("t_cohort")
            sign_ok = (observed > 0) if expect[c] > 0 else (observed < 0)
            passed = (tcv == tcv and abs(tcv or 0) >= 2.0 and sign_ok
                      and (pl.get("inflation_x") or 0) > 1.0)
            verdicts.append(f"{c.split('_')[0]}:{'PASS' if passed else 'fail'}")
        # reported-only context (never gated — the 6.8/6.9% pledge-tail null stands):
        # key trap: d_promoter = "Promoter Pledge" ΔQoQ (metric.split()[0].lower());
        # d_promoters = the promoter STAKE ΔQoQ used by the gated combos above.
        pl_split = [e for e in usable if e.get("G1_promoter_up")
                    and e.get("d_promoter") is not None]
        out["G1_pledge_observed_n"] = len(pl_split)
        out["verdict"] = " ".join(verdicts)
        hcon.close()
        line += f" → {out['verdict']}"
    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    if notify:
        _notify_dm(line)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    evs = [{"sym": "A", "pend": "2026-03-31", "t0": "2026-04-20",
            "d_promoters": 0.5, "d_fiis": 0.3},
           {"sym": "B", "pend": "2026-03-31", "t0": "2026-04-21",
            "d_promoters": -0.6, "d_fiis": 0.0},
           {"sym": "C", "pend": "2026-03-31", "t0": "2026-04-22",
            "d_promoters": 0.1, "d_fiis": 0.9}]
    tag_combos(evs)
    assert evs[0]["G1_promoter_up"] and evs[0]["G3_promoter_and_fii_up"]
    assert evs[1]["G2_promoter_down"] and not evs[1]["G1_promoter_up"]
    assert not evs[2]["G1_promoter_up"]          # inside the 0.25pp inertia floor
    rec = reconcile(evs, {"real_dated": 3, "calibrated_dated": 0})
    assert rec["go"] is False and rec["combos"]["G1_promoter_up"]["n"] == 1
    print("SHP_COMBOS selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--reconcile" in sys.argv:
        reconcile_cli(notify="--notify" in sys.argv)
    elif "--run" in sys.argv:
        run(notify="--notify" in sys.argv)
    else:
        print(__doc__)
