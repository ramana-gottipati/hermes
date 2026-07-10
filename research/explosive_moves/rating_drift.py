"""E-02 — credit-rating drift study (post-broadcast), PRE-REGISTERED 2026-07-10 (S85d).

SELF-GATING BY DESIGN (the postmortem's own kill structure, frozen here): the study
reconciles its sample FIRST and ABORTS with published numbers if it cannot — an abort
under this protocol is a valid, ledgerable execution, not a burned registration.

THE MAPPING WIDEN (charter: "widen the 59-symbol scrip mapping first") is built in as a
COMPUTE-ON-READ pass — no ingest edits, no stored columns: NULL-symbol issuers resolve by
(a) equity-ISIN match against security_master.isin, then (b) conservative issuer-name
normalization (strip LIMITED/LTD/PVT/PRIVATE + punctuation; UNIQUE match required —
ambiguous or unlisted issuers stay unmapped and are counted honestly). Expectation set by
the 2026-07-10 recon: 88% of the tape is REAFFIRM; mapped notch-changes ≈ 90 with a
~137 ceiling after the widen — the binding constraint is feed ACCRUAL, not mapping.

PRE-REGISTERED RECONCILIATION GATE (the run precondition; per-fire, cheap):
  (a) actionable events (deduped, mapped, notch-change) ≥ 300  [postmortem kill criterion]
  (b) they span ≥ 8 quarterly cohorts with ≥ 5 events each     [the E-03 depth lesson]
  NOT-YET → verdict "ABORT-RECONCILIATION (pre-registered)" + the full census, DM'd.

PRE-REGISTERED RESULT GATE (unchanged whenever reconciliation passes):
  Events:   one per (symbol, broadcast_date, direction) — debt-ISIN/agency multiplicity
            COLLAPSED (the Acuite/Acute + multi-ISIN dedup gate); t0 = broadcast date
            (when public); entry = t0 + ENTRY_LAG via pead_surface.reaction_row.
  Readout:  UPGRADE and DOWNGRADE cohorts separately: CAR22/CAR60 vs Nifty 500,
            quarterly cohort-clustered t (evlib.cohort_t).
  PEAD-overlap clause (must not re-discover earnings drift): events within ±5 sessions
            of the symbol's own results knowable_at are split out; the GATE runs on the
            CLEAN cohort; the overlapping cohort is reported alongside.
  PASS (per direction, descriptive lens ships): clean-cohort CAR60 t_cohort ≥ 2 AND the
            observed mean clears the evlib date-shuffle placebo p95 (n=200, seed 42),
            direction-consistent (upgrades +, downgrades −).
  FAIL:     publish the null. Book leg: NOT run (F6 priors; own pre-registration).

CLI (research venv):
  python -m explosive_moves.rating_drift --reconcile [--notify]   # census only, seconds
  python -m explosive_moves.rating_drift --run [--notify]         # the monthly timer entry
  python -m explosive_moves.rating_drift --selftest
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import date, datetime

import numpy as np

from . import evlib, pead
from .campaign_arcs import _notify_dm
from .common import load_series, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "rating_drift.json")
MIN_ACTIONABLE = 300
MIN_COHORTS = 8
MIN_PER_COHORT = 5
PEAD_EXCLUDE_SESSIONS = 5
_SUFFIX = re.compile(r"\b(LIMITED|LTD|PRIVATE|PVT)\b\.?", re.I)
_PUNCT = re.compile(r"[.,()'\"]")


def norm_name(s: str) -> str:
    s = _PUNCT.sub(" ", (s or "").upper())
    prev = None
    while prev != s:
        prev = s
        s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def build_mapping(hcon) -> dict:
    """issuer resolution artifacts: {'by_isin': {...}, 'by_name': {...}, 'ambiguous': set}."""
    by_isin, name_map, ambiguous = {}, {}, set()
    for sym, isin, cname in hcon.execute(
            "SELECT symbol, isin, company_name FROM security_master "
            "WHERE company_name IS NOT NULL"):
        if isin:
            by_isin[isin] = sym
        n = norm_name(cname)
        if not n:
            continue
        if n in name_map and name_map[n] != sym:
            ambiguous.add(n)
        else:
            name_map[n] = sym
    for n in ambiguous:
        name_map.pop(n, None)
    return {"by_isin": by_isin, "by_name": name_map, "ambiguous": ambiguous}


def load_events(hcon) -> dict:
    """Mapped + deduped notch-change events, with the full mapping census."""
    m = build_mapping(hcon)
    rows = hcon.execute(
        "SELECT symbol, issuer_name, isin, notch_delta, action_class, "
        "substr(broadcast_dt,1,10) FROM credit_rating_events "
        "WHERE broadcast_dt IS NOT NULL").fetchall()
    census = {"rows": len(rows), "mapped_base": 0, "widened_isin": 0,
              "widened_name": 0, "unmapped": 0, "ambiguous_name": 0}
    raw = []
    for sym, issuer, isin, notch, klass, bdt in rows:
        if not sym:
            if isin and isin in m["by_isin"]:
                sym = m["by_isin"][isin]
                census["widened_isin"] += 1
            else:
                n = norm_name(issuer)
                if n in m["by_name"]:
                    sym = m["by_name"][n]
                    census["widened_name"] += 1
                elif n in m["ambiguous"]:
                    census["ambiguous_name"] += 1
                    continue
                else:
                    census["unmapped"] += 1
                    continue
        else:
            census["mapped_base"] += 1
        direction = 0
        if (notch or 0) > 0 or klass == "UPGRADE":
            direction = 1
        elif (notch or 0) < 0 or klass == "DOWNGRADE":
            direction = -1
        if direction and bdt:
            raw.append({"sym": sym, "t0": bdt, "dir": direction,
                        "notch": abs(notch or 1)})
    # the dedup gate: one event per (symbol, broadcast date, direction), max notch kept
    best: dict = {}
    for e in raw:
        k = (e["sym"], e["t0"], e["dir"])
        if k not in best or e["notch"] > best[k]["notch"]:
            best[k] = e
    events = sorted(best.values(), key=lambda x: x["t0"])
    census["actionable_raw"] = len(raw)
    census["actionable_deduped"] = len(events)
    census["up"] = sum(1 for e in events if e["dir"] > 0)
    census["down"] = sum(1 for e in events if e["dir"] < 0)
    return {"events": events, "census": census}


def reconcile(events: list[dict], census: dict) -> dict:
    coh: dict = {}
    for e in events:
        coh.setdefault(evlib.cohort_of(e["t0"]), []).append(e)
    ok = sum(1 for v in coh.values() if len(v) >= MIN_PER_COHORT)
    n = len(events)
    go = n >= MIN_ACTIONABLE and ok >= MIN_COHORTS
    months = None
    if events and n < MIN_ACTIONABLE:
        span_m = max(1.0, (date.fromisoformat(events[-1]["t0"])
                           - date.fromisoformat(events[0]["t0"])).days / 30.44)
        rate = n / span_m
        months = round((MIN_ACTIONABLE - n) / rate, 1) if rate > 0 else None
    return {"go": bool(go), "n_actionable": n, "n_cohorts_ge5": ok,
            "need": f">={MIN_ACTIONABLE} actionable AND >={MIN_COHORTS} cohorts "
                    f">={MIN_PER_COHORT}",
            "est_months_to_sample": months, "census": census,
            "cohort_counts": {k: len(v) for k, v in sorted(coh.items())}}


def run(notify: bool = False) -> dict:
    hcon = main_conn()
    data = load_events(hcon)
    rec = reconcile(data["events"], data["census"])
    line = (f"📉 E-02 rating-drift: "
            f"{'RECONCILED — running full protocol' if rec['go'] else 'ABORT-RECONCILIATION (pre-registered)'} — "
            f"{rec['n_actionable']}/{MIN_ACTIONABLE} actionable "
            f"({data['census']['up']}↑/{data['census']['down']}↓) · "
            f"{rec['n_cohorts_ge5']}/{MIN_COHORTS} cohorts · "
            f"widen +{data['census']['widened_isin'] + data['census']['widened_name']}"
            + (f" · est sample ~{rec['est_months_to_sample']}mo" if rec.get("est_months_to_sample") else ""))
    print(line, flush=True)
    out: dict = {"study": "E-02 credit-rating drift (post-broadcast)",
                 "reconciliation": rec}
    if not rec["go"]:
        out["verdict"] = "ABORT-RECONCILIATION (pre-registered)"
        hcon.close()
    else:
        real = pead.load_real_dates(hcon)
        res_dates: dict = {}
        for (sym, _pt, _pend), knew in real.items():
            res_dates.setdefault(sym, []).append(str(knew)[:10])
        idx_dates, idx_map = evlib.index_levels(hcon)
        series: dict = {}
        usable = []
        for e in data["events"]:
            ss = series.setdefault(e["sym"], load_series(hcon, e["sym"]))
            if ss is None:
                continue
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "G", "pend": e["t0"],
                                  "t0": e["t0"], "sue": 0.0}, idx_dates, idx_map)
            if r is None or r["car60"] != r["car60"]:
                continue
            t0d = date.fromisoformat(e["t0"])
            near_res = any(abs((t0d - date.fromisoformat(rd)).days) <= PEAD_EXCLUDE_SESSIONS * 2
                           for rd in res_dates.get(e["sym"], []))
            usable.append({**e, "car22": r["car22"], "car60": r["car60"],
                           "near_results": bool(near_res)})
        for dname, dval in (("UP", 1), ("DOWN", -1)):
            for cname, flag in (("clean", False), ("near_results", True)):
                sel = [e for e in usable if e["dir"] == dval and e["near_results"] == flag]
                out[f"{dname}_{cname}_car60"] = evlib.cohort_t(
                    [(e["t0"], e["car60"]) for e in sel])
        rng = random.Random(42)
        verdicts = []
        for dname, dval in (("UP", 1), ("DOWN", -1)):
            sel = [e for e in usable if e["dir"] == dval and not e["near_results"]]
            st = out[f"{dname}_clean_car60"]
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
                    r = reaction_row(ss, {"sym": e["sym"], "ptype": "G", "pend": e["t0"],
                                          "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
                    if r is not None and r["car60"] == r["car60"]:
                        cars.append(r["car60"])
                if cars:
                    null_means.append(float(np.mean(cars)))
            pl = evlib.placebo_stats(observed, null_means)
            out[f"{dname}_placebo"] = pl
            tcv = st.get("t_cohort")
            sign_ok = (observed > 0) if dval > 0 else (observed < 0)
            passed = (tcv == tcv and abs(tcv or 0) >= 2.0 and sign_ok
                      and (pl.get("inflation_x") or 0) > 1.0)
            verdicts.append(f"{dname}:{'PASS' if passed else 'fail'}")
        out["verdict"] = "clean-cohort " + " ".join(verdicts)
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


def reconcile_cli(notify: bool = False) -> dict:
    hcon = main_conn()
    data = load_events(hcon)
    hcon.close()
    rec = reconcile(data["events"], data["census"])
    line = (f"📉 E-02 reconciliation: {'GO' if rec['go'] else 'NOT-YET'} — "
            f"{rec['n_actionable']}/{MIN_ACTIONABLE} actionable "
            f"({data['census']['up']}↑/{data['census']['down']}↓) · "
            f"{rec['n_cohorts_ge5']}/{MIN_COHORTS} cohorts · widen "
            f"+{data['census']['widened_isin'] + data['census']['widened_name']} "
            f"(isin {data['census']['widened_isin']} / name {data['census']['widened_name']})"
            + (f" · est ~{rec['est_months_to_sample']}mo to sample"
               if rec.get("est_months_to_sample") else ""))
    print(line, flush=True)
    print(json.dumps(rec, indent=1, default=str), flush=True)
    if notify:
        _notify_dm(line)
    return rec


def selftest() -> None:
    assert norm_name("Tejas Cargo India Limited") == "TEJAS CARGO INDIA"
    assert norm_name("Profectus Capital Private Limited") == "PROFECTUS CAPITAL"
    assert norm_name("BANK OF INDIA") == "BANK OF INDIA"          # INDIA never stripped
    assert norm_name("A.B.C. Ltd.") == "A B C"
    # dedup: multi-ISIN same-day same-direction collapses, max notch kept
    raw = [{"sym": "X", "t0": "2026-01-05", "dir": 1, "notch": 1},
           {"sym": "X", "t0": "2026-01-05", "dir": 1, "notch": 2},
           {"sym": "X", "t0": "2026-01-05", "dir": -1, "notch": 1}]
    best = {}
    for e in raw:
        k = (e["sym"], e["t0"], e["dir"])
        if k not in best or e["notch"] > best[k]["notch"]:
            best[k] = e
    assert len(best) == 2 and best[("X", "2026-01-05", 1)]["notch"] == 2
    # gate arithmetic
    evs = [{"t0": f"2026-{m:02d}-10", "dir": 1} for m in range(1, 5) for _ in range(6)]
    rec = reconcile(evs, {})
    assert rec["go"] is False and rec["n_cohorts_ge5"] == 2       # 24 events, 2 quarters
    print("RATING_DRIFT selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--reconcile" in sys.argv:
        reconcile_cli(notify="--notify" in sys.argv)
    elif "--run" in sys.argv:
        run(notify="--notify" in sys.argv)
    else:
        print(__doc__)
