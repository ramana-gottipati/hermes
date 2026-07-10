"""E-04 — campaign-arc study (post-public arc CONTINUATION), PRE-REGISTERED 2026-07-10 (S85b).

GATE FROZEN LONG BEFORE THE RUN IS POSSIBLE — deliberately. The E-03 null (ledger § Studies
2026-07-08) fixed a blocking re-attempt condition for this feed class: the insider feed was
~10 months deep, giving 2-3 usable quarterly cohorts and t_cohort = NaN. E-04 uses the same
feeds (insider conviction clusters + SAST ACQ episodes), so it inherits that floor. This
module therefore ships in a SELF-ARMING state: `--run` REFUSES until the depth gate passes;
`--depth-gate --notify` (monthly timer) DMs the measured depth so the GO moment is caught.
The gate hash enters the M-04 registry TODAY; any later edit is tamper-evident.

DEFINITIONS:
  Episode = a merged insider/SAST accumulation cluster (footprint.load_labels — the exact
  D89-study construction). ARC = ≥2 episodes of the same symbol where the next episode
  STARTS within ≤120 calendar days of the prior one's END. The arc-confirmation EVENT is
  the moment the SECOND (or later) episode becomes public: t0 = that episode's first
  disclosure date. Detection target = continuation AFTER the repeat signal is public —
  front-running is structurally dead (D89: 764/947 episodes had no pre-public window).

PRE-REGISTERED DEPTH GATE (the run precondition, from the E-03 re-attempt record):
  (a) the merged feed spans ≥ 24 months, AND
  (b) arc-confirmation events span ≥ 8 quarterly cohorts with ≥ 5 events each
      (evlib.cohort_t's own usability floor — no clustered inference below it).
  The monthly check counts RAW confirmation events (an upper bound: tape attrition ~50%
  per E-03); `--run` re-verifies the gate on USABLE events after measurement and
  downgrades its verdict to DEPTH-FAIL if attrition breaks (b).

PRE-REGISTERED RESULT GATE (unchanged whenever the run happens):
  Readout: arc-confirmation CAR22/CAR60 vs Nifty 500 (pead_surface.reaction_row, entry =
  t0 + ENTRY_LAG), quarterly cohort-clustered t (evlib.cohort_t); the SINGLE-episode
  cohort (episodes with no arc partner) measured identically as the comparison.
  PASS (descriptive arc lens ships): arc CAR60 t_cohort ≥ 2 AND the arc mean clears the
  evlib date-shuffle placebo p95 (n=200, seed 42) AND arc mean > single-episode mean
  (the claim IS "arcs beat singles" — without that margin there is no arc information).
  Also reported, NOT gated: ticket_ratio (the D89 survivor) between-episode elevation vs
  self-controls, Cliff's δ — descriptive detection context only.
  FAIL: publish the null. Book leg: NOT run (F6 priors; own pre-registration required).
  Exclusions: episodes with Σ pct ≥ 5% (control-change; the VIPIND lesson).

CLI (research venv):
  python -m explosive_moves.campaign_arcs --depth-gate [--notify]   # monthly timer entry
  python -m explosive_moves.campaign_arcs --run [--force-underpowered]
  python -m explosive_moves.campaign_arcs --selftest
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, datetime

import numpy as np

from . import evlib, footprint
from .common import load_series, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "campaign_arcs.json")
ARC_GAP_DAYS = 120
PCT_CONTROL_CHANGE = 5.0
MIN_FEED_MONTHS = 24
MIN_COHORTS = 8
MIN_PER_COHORT = 5


def build_arcs(episodes: list[dict]) -> tuple[list[dict], list[dict]]:
    """(arc_confirmation_events, single_episodes). Episodes must carry sym/start/end/disc."""
    by_sym: dict = {}
    for e in episodes:
        if (e.get("pct") or 0.0) >= PCT_CONTROL_CHANGE:
            continue
        by_sym.setdefault(e["sym"], []).append(e)
    arcs, singles = [], []
    for sym, evs in by_sym.items():
        evs.sort(key=lambda x: x["start"])
        in_arc = [False] * len(evs)
        for i in range(1, len(evs)):
            gap = (date.fromisoformat(evs[i]["start"]) - date.fromisoformat(evs[i - 1]["end"])).days
            if 0 <= gap <= ARC_GAP_DAYS:
                in_arc[i] = in_arc[i - 1] = True
                arcs.append({"sym": sym, "t0": evs[i]["disc"], "arc_idx": i,
                             "prior_end": evs[i - 1]["end"],
                             "value": (evs[i].get("value") or 0.0)})
        singles += [e for k, e in enumerate(evs) if not in_arc[k]]
    return arcs, singles


def measure_depth(arcs: list[dict], episodes: list[dict]) -> dict:
    """The pre-registered depth gate on RAW confirmation events (upper bound)."""
    if not episodes:
        return {"go": False, "detail": "no episodes"}
    starts = sorted(e["start"] for e in episodes)
    span_months = ((date.fromisoformat(starts[-1]) - date.fromisoformat(starts[0])).days) / 30.44
    coh: dict = {}
    for a in arcs:
        coh.setdefault(evlib.cohort_of(a["t0"]), []).append(a)
    ok_cohorts = sum(1 for v in coh.values() if len(v) >= MIN_PER_COHORT)
    go = span_months >= MIN_FEED_MONTHS and ok_cohorts >= MIN_COHORTS
    return {"go": bool(go), "feed_span_months": round(span_months, 1),
            "n_arc_events": len(arcs), "n_cohorts_ge5": ok_cohorts,
            "need": f">={MIN_FEED_MONTHS}mo feed AND >={MIN_COHORTS} qtr cohorts "
                    f"with >={MIN_PER_COHORT} arc events",
            "cohort_counts": {k: len(v) for k, v in sorted(coh.items())}}


def _load_episodes(hcon) -> list[dict]:
    return footprint.load_labels(hcon)      # insider conviction + SAST ACQ, merged — the D89 set


def depth_gate(notify: bool = False) -> dict:
    hcon = main_conn()
    eps = _load_episodes(hcon)
    hcon.close()
    arcs, _singles = build_arcs(eps)
    d = measure_depth(arcs, eps)
    line = (f"🧬 E-04 depth gate: {'GO — run the pre-registered study' if d['go'] else 'NOT-YET'} — "
            f"{d.get('n_cohorts_ge5', 0)}/{MIN_COHORTS} qtr cohorts ≥{MIN_PER_COHORT} · "
            f"{d.get('n_arc_events', 0)} arc events · feed {d.get('feed_span_months', 0)}mo"
            f"/{MIN_FEED_MONTHS}mo")
    print(line, flush=True)
    print(json.dumps(d, indent=1), flush=True)
    if notify:
        _notify_dm(line)
    return d


def _notify_dm(text: str) -> None:
    """Stdlib-only Telegram DM (the research venv has no requests/pydantic — parse .env
    directly, urllib POST; the season_digest sender lives in the prod venv on purpose)."""
    import urllib.parse
    import urllib.request
    token = chat = ""
    try:
        with open("/opt/hermes/.env", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith("TELEGRAM_BOT_TOKEN="):
                    token = ln.split("=", 1)[1].strip().strip("'\"")
                elif ln.startswith("TELEGRAM_ALLOWED_USER_IDS="):
                    chat = ln.split("=", 1)[1].strip().strip("'\"").split(",")[0].strip()
    except OSError as e:
        print(f"notify: .env unreadable ({e})", flush=True)
        return
    if not token or not chat:
        print("notify: missing token/chat id", flush=True)
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        with urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.telegram.org/bot{token}/sendMessage", data=data),
                timeout=15) as r:
            print(f"notify: sent (HTTP {r.status})", flush=True)
    except Exception as e:                                      # noqa: BLE001
        print(f"notify failed: {type(e).__name__}: {e}", flush=True)


def run(force_underpowered: bool = False) -> dict:
    hcon = main_conn()
    eps = _load_episodes(hcon)
    arcs, singles = build_arcs(eps)
    d = measure_depth(arcs, eps)
    if not d["go"] and not force_underpowered:
        hcon.close()
        raise SystemExit(f"DEPTH GATE NOT MET — refusing to run (pre-registered condition, "
                         f"E-03 re-attempt record): {json.dumps(d)}\n"
                         f"Use --force-underpowered ONLY for a labeled exploratory pass; "
                         f"the result would not be gate-eligible.")

    idx_dates, idx_map = evlib.index_levels(hcon)
    series: dict = {}

    def measure(evts, tag):
        out = []
        for e in evts:
            ss = series.setdefault(e["sym"], load_series(hcon, e["sym"]))
            if ss is None:
                continue
            t0 = e.get("t0") or e.get("disc")
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "K", "pend": t0,
                                  "t0": t0, "sue": 0.0}, idx_dates, idx_map)
            if r is not None and r["car60"] == r["car60"]:
                out.append({"sym": e["sym"], "t0": t0, "car22": r["car22"], "car60": r["car60"]})
        print(f"{tag}: {len(out)} usable of {len(evts)}", flush=True)
        return out

    ua = measure(arcs, "arcs")
    us = measure(singles, "singles")
    out: dict = {"study": "E-04 campaign-arc continuation (post-public)",
                 "depth_gate_raw": d, "forced": bool(force_underpowered),
                 "n_arcs_usable": len(ua), "n_singles_usable": len(us)}
    out["ARC_car60"] = evlib.cohort_t([(e["t0"], e["car60"]) for e in ua])
    out["ARC_car22"] = evlib.cohort_t([(e["t0"], e["car22"]) for e in ua])
    out["SINGLE_car60"] = evlib.cohort_t([(e["t0"], e["car60"]) for e in us])

    # usable-events depth re-verification (the attrition clause)
    coh_u: dict = {}
    for e in ua:
        coh_u.setdefault(evlib.cohort_of(e["t0"]), []).append(e)
    usable_ok = sum(1 for v in coh_u.values() if len(v) >= MIN_PER_COHORT)
    out["depth_gate_usable_cohorts"] = usable_ok

    observed = out["ARC_car60"].get("mean", float("nan"))
    rng = random.Random(42)
    null_means = []
    for k in range(200):
        cars = []
        for e in ua:
            ss = series.get(e["sym"])
            if ss is None:
                continue
            lo_i, hi_i = evlib.eligible_indices(ss, 60)
            if hi_i <= lo_i:
                continue
            i0 = rng.randrange(lo_i, hi_i)
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "K", "pend": e["t0"],
                                  "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
            if r is not None and r["car60"] == r["car60"]:
                cars.append(r["car60"])
        if cars:
            null_means.append(float(np.mean(cars)))
        if (k + 1) % 50 == 0:
            print(f"  placebo {k + 1}/200", flush=True)
    hcon.close()
    out["placebo"] = evlib.placebo_stats(observed, null_means)

    tcv = out["ARC_car60"].get("t_cohort")
    arc_mean = out["ARC_car60"].get("mean")
    single_mean = out["SINGLE_car60"].get("mean")
    if usable_ok < MIN_COHORTS and not force_underpowered:
        out["verdict"] = "DEPTH-FAIL-post-attrition (raw gate passed, usable cohorts broke)"
    else:
        passed = (tcv == tcv and (tcv or 0) >= 2.0
                  and (out["placebo"].get("inflation_x") or 0) > 1.0
                  and arc_mean is not None and single_mean is not None
                  and arc_mean > single_mean)
        out["verdict"] = ("PASS-descriptive" if passed else "FAIL-null-published") + \
                         (" [FORCED-EXPLORATORY — not gate-eligible]" if force_underpowered else "")
    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    eps = [
        {"sym": "A", "start": "2025-01-01", "end": "2025-01-10", "disc": "2025-01-12", "value": 1e6, "pct": 0.1},
        {"sym": "A", "start": "2025-02-15", "end": "2025-02-20", "disc": "2025-02-22", "value": 2e6, "pct": 0.1},  # 36d gap -> arc
        {"sym": "A", "start": "2025-09-01", "end": "2025-09-05", "disc": "2025-09-07", "value": 1e6, "pct": 0.1},  # 194d -> new/single
        {"sym": "B", "start": "2025-03-01", "end": "2025-03-04", "disc": "2025-03-06", "value": 9e9, "pct": 9.0},  # control-change: excluded
        {"sym": "C", "start": "2025-05-01", "end": "2025-05-02", "disc": "2025-05-04", "value": 1e6, "pct": 0.2},  # single
    ]
    arcs, singles = build_arcs(eps)
    assert len(arcs) == 1 and arcs[0]["sym"] == "A" and arcs[0]["t0"] == "2025-02-22"
    assert {s["sym"] for s in singles} == {"A", "C"} and len(singles) == 2   # B excluded (pct)
    d = measure_depth(arcs, [e for e in eps if e["pct"] < PCT_CONTROL_CHANGE])
    assert d["go"] is False and d["n_arc_events"] == 1                       # tiny feed: NOT-YET
    # a synthetic deep feed passes
    deep_eps = [{"sym": f"S{i}", "start": f"20{24 + q // 4}-{(q % 4) * 3 + 1:02d}-01",
                 "end": f"20{24 + q // 4}-{(q % 4) * 3 + 1:02d}-03",
                 "disc": f"20{24 + q // 4}-{(q % 4) * 3 + 1:02d}-05", "value": 1e6, "pct": 0.1}
                for q in range(9) for i in range(6)]
    deep_arcs = [{"sym": "X", "t0": e["disc"]} for e in deep_eps]
    d2 = measure_depth(deep_arcs, deep_eps)
    assert d2["n_cohorts_ge5"] >= MIN_COHORTS and d2["feed_span_months"] >= MIN_FEED_MONTHS
    assert d2["go"] is True
    print("CAMPAIGN_ARCS selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--depth-gate" in sys.argv:
        depth_gate(notify="--notify" in sys.argv)
    elif "--run" in sys.argv:
        run(force_underpowered="--force-underpowered" in sys.argv)
    else:
        print(__doc__)
