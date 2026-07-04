"""Footprint calibration — do disclosed-accumulation episodes leave a detectable tape signature?

THE QUESTION (pre-registered 2026-07-05, before any label was joined to the tape): while an
insider/acquirer is ACTUALLY BUYING (transaction window, pre-disclosure), do our delivery/tape
descriptors elevate vs (a) the same stock at random other times and (b) other stocks on the same
dates? This is a DETECTION study, not a returns study — the output is a precision/lift spec sheet
for the accumulation-footprint lens, calibrated on ground-truth labels we already ingest. It can
succeed or fail; either way the number goes in the ledger.

LABELS (ground truth, primary-source, already in hermes.db)
  * insider_events  signal_class='conviction' AND txn_class='OPEN_MARKET_BUY'
    (SEBI PIT Reg-7(2) open-market insider/promoter buys; transaction_dt = event clock,
    disclosure_dt = PIT clock). Episode = per-symbol cluster of buy dates <=10 sessions apart;
    material if sum(value_rs) >= Rs 50L OR sum(pct_equity) >= 0.10.
  * sast_reg29_events acq_sale='ACQ' (Reg-29 stake crossings; [txn_from, txn_to] window,
    broadcast_dt = PIT clock). Material if pct_acq >= 0.25.
  Overlapping episodes of the two sources on one symbol are merged (union window, src='both').

NO-PEEK CONTRACT: the case window ends at min(episode_end, first_disclosure - 1 session) — the
detector only ever sees tape that traded BEFORE the purchase was public. Episodes whose window
shrinks below 3 sessions are dropped (disclosure too fast to front-detect — counted + reported).

CONTROLS (per case, same window length)
  * self-controls  (K=2): same symbol, random anchor 60..400 sessions BEFORE window start, not
    within +/-30 sessions of any case episode of that symbol. Kills symbol fixed effects.
  * cross-controls (K=2): same calendar anchor, different symbols drawn from the case universe
    with no own-case within +/-60 sessions. Kills date/regime effects.

FEATURES (all vs the symbol's OWN trailing-66-session baseline ending at window_start-1)
  f_deliv_value   mean delivered VALUE (deliv_qty x close) / trailing median   [a-priori]
  f_trade_size    mean (value / num_trades) / trailing median                  [a-priori]
  f_updel_share   delivered value on up-close days / total delivered value    [a-priori]
  f_deliv_per     mean deliv_per / trailing median deliv_per                   [a-priori]
  f_turnover      mean traded value / trailing median
  f_close_str     mean (close-low)/(high-low)
  f_overnight     mean overnight return (open/prev_close - 1)
  f_drift         window total return
  f_tight         (max-min)/mean close over window / same over trailing 22

PRE-REGISTERED READOUT + GATE
  * Per feature: Cliff's delta (cases vs self-controls) and (cases vs cross-controls).
  * Composite = mean cross-sectional percentile of the four [a-priori] features; lift table =
    precision of flagging the top decile of pooled case+control windows vs the base rate.
  * PASS GATE (declared now): >=2 of the 4 a-priori features show Cliff's delta >= +0.20
    against BOTH control sets. Pass -> build the live daily scan (v2, lead-time profile).
    Fail -> record in ledger, keep MEP descriptive, do NOT ship an accumulation detector.

Read-only. Writes out/footprint_windows.csv + out/footprint_summary.txt. Run on VPS:
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.footprint            # full study
  ... -m explosive_moves.footprint --selftest # offline, synthetic, no DB
"""
from __future__ import annotations

import bisect
import csv
import math
import os
import sys
from datetime import date

import numpy as np

from .common import LIQ_FLOOR, OUT_DIR, cliffs_delta, load_series, main_conn

CLUSTER_GAP = 10          # sessions between buys that still form one episode
EP_CAP = 20               # max episode length (sessions)
MIN_WIN = 3               # min usable (pre-disclosure) window length
VALUE_FLOOR = 5e6         # Rs 50L episode materiality (insider)
PCTEQ_FLOOR = 0.10        # or >=0.10% of equity bought (insider, when value missing)
SAST_PCT_FLOOR = 0.25     # Reg-29 materiality: >=0.25% of capital acquired
BASE_WIN = 66             # trailing baseline window
SELF_K, CROSS_K = 2, 2
SELF_MIN_BACK, SELF_MAX_BACK = 60, 400
CASE_EXCL = 30            # self-control must be this far from any case episode
CROSS_EXCL = 60           # cross-control symbol must have no own case within this
APRIORI = ("f_deliv_value", "f_trade_size", "f_updel_share", "f_deliv_per")
GATE_DELTA = 0.20
SEED = 42


# ---------- episode assembly (pure, selftested) --------------------------------

def cluster_insider(rows: list[tuple[str, str, str, float, float]]) -> list[dict]:
    """rows = (symbol, transaction_dt, disclosure_dt, value_rs, pct_equity) conviction buys.
    -> material episodes {sym, start, end, disc, src='insider', value}."""
    by_sym: dict[str, list[tuple[str, str, float, float]]] = {}
    for sym, tdt, ddt, val, pct in rows:
        if not tdt or not ddt or str(tdt)[:10] > str(ddt)[:10]:
            continue                       # need both clocks; txn must precede disclosure
        by_sym.setdefault(sym, []).append((str(tdt)[:10], str(ddt)[:10],
                                           float(val or 0.0), float(pct or 0.0)))
    eps = []
    for sym, evs in by_sym.items():
        evs.sort()
        cur = None
        for tdt, ddt, val, pct in evs:
            if cur and (date.fromisoformat(tdt) - date.fromisoformat(cur["end"])).days <= CLUSTER_GAP:
                cur["end"] = max(cur["end"], tdt)
                cur["disc"] = min(cur["disc"], ddt)
                cur["value"] += val
                cur["pct"] += pct
            else:
                if cur:
                    eps.append(cur)
                cur = {"sym": sym, "start": tdt, "end": tdt, "disc": ddt,
                       "value": val, "pct": pct, "src": "insider"}
        if cur:
            eps.append(cur)
    return [e for e in eps if e["value"] >= VALUE_FLOOR or e["pct"] >= PCTEQ_FLOOR]


def sast_episodes(rows: list[tuple[str, str, str, str, float]]) -> list[dict]:
    """rows = (symbol, txn_from, txn_to, broadcast_dt, pct_acq) ACQ events."""
    eps = []
    for sym, f, t, b, pct in rows:
        if not f or not b or (pct or 0.0) < SAST_PCT_FLOOR:
            continue
        f, t, b = str(f)[:10], str(t or f)[:10], str(b)[:10]
        if f > t or f > b:
            continue
        eps.append({"sym": sym, "start": f, "end": min(t, b), "disc": b,
                    "value": 0.0, "pct": float(pct), "src": "sast"})
    return eps


def merge_episodes(eps: list[dict]) -> list[dict]:
    """Union overlapping same-symbol episodes (insider + SAST double-report the same buying)."""
    out: list[dict] = []
    for e in sorted(eps, key=lambda x: (x["sym"], x["start"])):
        last = out[-1] if out and out[-1]["sym"] == e["sym"] else None
        if last and e["start"] <= last["end"]:
            last["end"] = max(last["end"], e["end"])
            last["disc"] = min(last["disc"], e["disc"])
            if last["src"] != e["src"]:
                last["src"] = "both"
        else:
            out.append(dict(e))
    return out


# ---------- window features (pure given arrays) --------------------------------

def _med(x: np.ndarray) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.median(x)) if len(x) >= BASE_WIN // 3 else float("nan")


def window_features(ss, i0: int, i1: int) -> dict | None:
    """Features for rows [i0, i1] inclusive vs trailing baseline ending i0-1. None = unusable."""
    if i0 < BASE_WIN + 5 or i1 >= ss.n or i1 < i0:
        return None
    mt = ss.med_turn[i0]
    if not (mt == mt and mt >= LIQ_FLOOR):
        return None
    if ss.is_ca[i0 - BASE_WIN:i1 + 1].any():
        return None
    b = slice(i0 - BASE_WIN, i0)
    w = slice(i0, i1 + 1)
    dv_w = ss.deliv_qty[w] * ss.close[w]
    dv_b = ss.deliv_qty[b] * ss.close[b]
    ts_w = ss.value[w] / np.maximum(ss.num_trades[w], 1.0)
    ts_b = ss.value[b] / np.maximum(ss.num_trades[b], 1.0)
    m_dv, m_ts, m_to = _med(dv_b), _med(ts_b), _med(ss.value[b])
    m_dp = _med(ss.deliv_per[b])
    if not all(x == x for x in (m_dv, m_ts, m_to, m_dp)):
        return None
    if np.isnan(dv_w).any() or np.isnan(ss.value[w]).any():
        return None
    up = ss.close[w] > ss.prev_close[w]
    tot_dv = float(np.nansum(dv_w))
    hl = ss.high[w] - ss.low[w]
    with np.errstate(invalid="ignore", divide="ignore"):
        cs = np.where(hl > 0, (ss.close[w] - ss.low[w]) / hl, np.nan)
        on = np.where(ss.prev_close[w] > 0, ss.open[w] / ss.prev_close[w] - 1.0, np.nan)
    c0, c1 = ss.adj_close[i0 - 1], ss.adj_close[i1]
    tight_w = (np.nanmax(ss.adj_close[w]) - np.nanmin(ss.adj_close[w])) / max(np.nanmean(ss.adj_close[w]), 1e-9)
    tb = slice(max(0, i0 - 22), i0)
    tight_b = (np.nanmax(ss.adj_close[tb]) - np.nanmin(ss.adj_close[tb])) / max(np.nanmean(ss.adj_close[tb]), 1e-9)
    return {
        "f_deliv_value": float(np.nanmean(dv_w)) / m_dv,
        "f_trade_size": float(np.nanmean(ts_w)) / m_ts,
        "f_updel_share": float(np.nansum(dv_w[up]) / tot_dv) if tot_dv > 0 else float("nan"),
        "f_deliv_per": float(np.nanmean(ss.deliv_per[w])) / m_dp,
        "f_turnover": float(np.nanmean(ss.value[w])) / m_to,
        "f_close_str": float(np.nanmean(cs)),
        "f_overnight": float(np.nanmean(on)),
        "f_drift": float(c1 / c0 - 1.0) if (c0 > 0 and c1 > 0) else float("nan"),
        "f_tight": float(tight_w / tight_b) if tight_b > 0 else float("nan"),
        "med_turn": float(mt),
    }


FEATS = ("f_deliv_value", "f_trade_size", "f_updel_share", "f_deliv_per",
         "f_turnover", "f_close_str", "f_overnight", "f_drift", "f_tight")


# ---------- study ---------------------------------------------------------------

def load_labels(hcon) -> list[dict]:
    ins = hcon.execute(
        "SELECT symbol, transaction_dt, disclosure_dt, value_rs, pct_equity FROM insider_events "
        "WHERE signal_class='conviction' AND txn_class='OPEN_MARKET_BUY'").fetchall()
    sas = hcon.execute(
        "SELECT symbol, txn_from, txn_to, broadcast_dt, pct_acq FROM sast_reg29_events "
        "WHERE acq_sale='ACQ'").fetchall()
    eps = cluster_insider([tuple(r) for r in ins]) + sast_episodes([tuple(r) for r in sas])
    today = date.today().isoformat()
    eps = [e for e in eps if e["start"] <= today]          # guard filing typos (future dates)
    return merge_episodes(eps)


def case_indices(ss, ep: dict) -> tuple[int, int] | None:
    """Map an episode to tape row indices; trim the window to END BEFORE first disclosure."""
    i0 = bisect.bisect_left(ss.date, ep["start"])
    if i0 >= ss.n:
        return None
    i_disc = bisect.bisect_left(ss.date, ep["disc"])        # first row ON/AFTER disclosure
    i1 = bisect.bisect_right(ss.date, ep["end"]) - 1
    i1 = min(i1, i0 + EP_CAP - 1, i_disc - 1, ss.n - 1)
    if i1 - i0 + 1 < MIN_WIN:
        return None
    return i0, i1


def run_study() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    hcon = main_conn()
    eps = load_labels(hcon)
    print(f"material episodes: {len(eps)} "
          f"(insider {sum(1 for e in eps if e['src']=='insider')}, "
          f"sast {sum(1 for e in eps if e['src']=='sast')}, both {sum(1 for e in eps if e['src']=='both')})",
          flush=True)

    by_sym: dict[str, list[dict]] = {}
    for e in eps:
        by_sym.setdefault(e["sym"], []).append(e)
    series: dict[str, object] = {}
    rows: list[dict] = []                    # one per window: kind, sym, date, length, feats
    too_fast = no_tape = 0

    syms = sorted(by_sym)
    for k, sym in enumerate(syms):
        ss = load_series(hcon, sym)
        if ss is None:
            no_tape += len(by_sym[sym])
            continue
        series[sym] = ss
        for ep in by_sym[sym]:
            ci = case_indices(ss, ep)
            if ci is None:
                too_fast += 1
                continue
            i0, i1 = ci
            f = window_features(ss, i0, i1)
            if f is None:
                continue
            rows.append({"kind": "case", "sym": sym, "anchor": ss.date[i0],
                         "n": i1 - i0 + 1, "src": ep["src"], "i0": i0, **f})
        if (k + 1) % 200 == 0:
            print(f"  {k+1}/{len(syms)} symbols, windows={len(rows)}", flush=True)

    cases = [r for r in rows if r["kind"] == "case"]
    print(f"usable case windows: {len(cases)} (dropped: {too_fast} disclosure-too-fast/short, "
          f"{no_tape} no tape)", flush=True)

    # episode index per symbol for exclusion tests
    ep_idx: dict[str, list[tuple[int, int]]] = {}
    for r in cases:
        ss = series[r["sym"]]
        ep_idx.setdefault(r["sym"], []).append((r["i0"], r["i0"] + r["n"] - 1))

    def clear_of_cases(sym: str, i0: int, i1: int, margin: int) -> bool:
        for a, b in ep_idx.get(sym, []):
            if i0 <= b + margin and i1 >= a - margin:
                return False
        return True

    # self-controls
    for r in list(cases):
        ss = series[r["sym"]]
        got = 0
        for _ in range(24):
            if got >= SELF_K:
                break
            back = int(rng.integers(SELF_MIN_BACK, SELF_MAX_BACK))
            j0 = r["i0"] - back
            j1 = j0 + r["n"] - 1
            if j0 < BASE_WIN + 5 or not clear_of_cases(r["sym"], j0, j1, CASE_EXCL):
                continue
            f = window_features(ss, j0, j1)
            if f is None:
                continue
            rows.append({"kind": "self", "sym": r["sym"], "anchor": ss.date[j0],
                         "n": r["n"], "src": r["src"], "i0": j0, **f})
            got += 1

    # cross-controls (same calendar anchor, different symbol from the loaded pool)
    pool = sorted(series)
    for r in list(cases):
        got = 0
        for _ in range(24):
            if got >= CROSS_K:
                break
            osym = pool[int(rng.integers(0, len(pool)))]
            if osym == r["sym"]:
                continue
            ss2 = series[osym]
            j0 = bisect.bisect_left(ss2.date, r["anchor"])
            j1 = j0 + r["n"] - 1
            if j0 >= ss2.n or j1 >= ss2.n or not clear_of_cases(osym, j0, j1, CROSS_EXCL):
                continue
            f = window_features(ss2, j0, j1)
            if f is None:
                continue
            rows.append({"kind": "cross", "sym": osym, "anchor": ss2.date[j0],
                         "n": r["n"], "src": r["src"], "i0": j0, **f})
            got += 1
    hcon.close()

    # ---------- readout ----------
    out: list[str] = []
    n_case = len(cases)
    n_self = sum(1 for r in rows if r["kind"] == "self")
    n_cross = sum(1 for r in rows if r["kind"] == "cross")
    out.append(f"FOOTPRINT CALIBRATION — {n_case} case windows (pre-disclosure accumulation), "
               f"{n_self} self-controls, {n_cross} cross-controls; dropped {too_fast} "
               f"disclosure-too-fast + {no_tape} no-tape. Labels era ~2025-26 (ingest depth).")
    out.append(f"{'feature':<15}{'d self':>8}{'d cross':>9}   (Cliff's delta; + = cases higher; "
               f"gate {GATE_DELTA:+.2f} on a-priori)")
    passes = 0
    for ft in FEATS:
        a = np.array([r[ft] for r in rows if r["kind"] == "case"], float)
        s = np.array([r[ft] for r in rows if r["kind"] == "self"], float)
        c = np.array([r[ft] for r in rows if r["kind"] == "cross"], float)
        ds, dc = cliffs_delta(a, s), cliffs_delta(a, c)
        tag = ""
        if ft in APRIORI:
            ok = (ds == ds and dc == dc and ds >= GATE_DELTA and dc >= GATE_DELTA)
            passes += int(ok)
            tag = "  [a-priori]" + ("  PASS" if ok else "  fail")
        out.append(f"{ft:<15}{ds:>+8.3f}{dc:>+9.3f}{tag}")

    # composite lift (a-priori features, pooled percentile ranks)
    pooled = [r for r in rows if all(r[ft] == r[ft] for ft in APRIORI)]
    for ft in APRIORI:
        vals = np.array([r[ft] for r in pooled])
        order = np.argsort(np.argsort(vals)) / max(len(vals) - 1, 1)
        for r, p in zip(pooled, order):
            r.setdefault("_pct", []).append(float(p))
    for r in pooled:
        r["composite"] = float(np.mean(r["_pct"]))
    pooled.sort(key=lambda r: -r["composite"])
    base = sum(1 for r in pooled if r["kind"] == "case") / max(len(pooled), 1)
    out.append(f"\ncomposite lift (a-priori mean-pctl; base rate {base*100:.1f}% cases):")
    for frac in (0.05, 0.10, 0.20):
        top = pooled[:max(1, int(len(pooled) * frac))]
        prec = sum(1 for r in top if r["kind"] == "case") / len(top)
        out.append(f"  top {int(frac*100):>2}%: precision {prec*100:5.1f}%  lift {prec/base:4.2f}x  (n={len(top)})")
    by_src = {}
    for r in pooled:
        if r["kind"] == "case":
            by_src.setdefault(r["src"], []).append(r["composite"])
    out.append("case composite mean by label source: " + "  ".join(
        f"{k}={np.mean(v):.3f}(n={len(v)})" for k, v in sorted(by_src.items())))

    verdict = "PASS" if passes >= 2 else "FAIL"
    out.append(f"\nPRE-REGISTERED GATE: {passes}/4 a-priori features cleared ±{GATE_DELTA} vs BOTH "
               f"control sets → {verdict}."
               + (" Build the live daily scan (v2 + lead-time profile)." if verdict == "PASS"
                  else " Record in ledger; MEP stays descriptive; no detector ships."))

    with open(OUT_DIR / "footprint_windows.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "src", "sym", "anchor", "n"] + list(FEATS) + ["composite"])
        for r in pooled:
            w.writerow([r["kind"], r["src"], r["sym"], r["anchor"], r["n"]]
                       + [f"{r[ft]:.4f}" for ft in FEATS] + [f"{r['composite']:.4f}"])
    with open(OUT_DIR / "footprint_summary.txt", "w") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\nwrote {OUT_DIR/'footprint_windows.csv'} + footprint_summary.txt")


# ---------- selftest (offline, no DB) --------------------------------------------

def selftest() -> None:
    # insider clustering: 3 buys within gap -> one episode; materiality floor enforced
    rows = [("X", "2026-01-05", "2026-01-08", 3e6, 0.02),
            ("X", "2026-01-09", "2026-01-12", 4e6, 0.03),
            ("X", "2026-03-01", "2026-03-03", 1e5, 0.01),   # immaterial lone episode
            ("Y", "2026-02-01", "2026-01-20", 9e9, 1.0)]     # txn AFTER disclosure -> dropped
    eps = cluster_insider(rows)
    assert len(eps) == 1 and eps[0]["sym"] == "X" and eps[0]["value"] == 7e6, eps
    assert eps[0]["start"] == "2026-01-05" and eps[0]["end"] == "2026-01-09"
    assert eps[0]["disc"] == "2026-01-08"                    # earliest disclosure bounds the window
    # sast + merge: overlapping insider+sast unify to src='both'
    se = sast_episodes([("X", "2026-01-07", "2026-01-15", "2026-01-16", 0.5)])
    m = merge_episodes(eps + se)
    assert len(m) == 1 and m[0]["src"] == "both" and m[0]["end"] == "2026-01-15", m
    # window trim honesty: disclosure inside the episode trims the case window
    class FakeSS:
        date = [f"2026-01-{d:02d}" for d in range(1, 30)]
        n = 29
    ep = {"start": "2026-01-05", "end": "2026-01-20", "disc": "2026-01-10"}
    i0, i1 = case_indices(FakeSS, ep)
    assert FakeSS.date[i0] == "2026-01-05" and FakeSS.date[i1] == "2026-01-09", (i0, i1)
    ep2 = {"start": "2026-01-05", "end": "2026-01-20", "disc": "2026-01-06"}
    assert case_indices(FakeSS, ep2) is None                 # too fast to front-detect
    # cliffs_delta orientation: cases higher -> positive
    assert cliffs_delta(np.array([2., 3, 4]), np.array([1., 1, 1])) == 1.0
    print("FOOTPRINT selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        run_study()
