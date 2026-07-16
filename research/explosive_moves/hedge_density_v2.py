"""Concall net-uncertainty → forward realized-VOLATILITY — PRE-REGISTERED 2026-07-13 (v2 successor).

WHY v2 (v1's data review). `hedge_density` (v1) was FAIL-null AND mis-specified: 64.7% of its "hedge"
hits were five ubiquitous modals (would/should/may/could/maybe) → it measured modal density, not
conviction; its SPIKE tercile was 50-59% Q2 FY-end-guidance calls (a seasonal confound within-name
differencing did not remove). A cheap return pulse-check (uncertainty-only Δ) confirmed the RETURN angle
dead. v2 changes the OUTCOME to the more plausible target and fixes construct validity. Frozen design:
research/explosive_moves/hedge_density_v2_PREREG.md (git 8ce1f0e). Cites the failure-ledger: every prior
event-return wrapper net-failed 0.02-0.10 return/vol vs 0.85; concall_intent placebo-killed; v1 return-null.
DESCRIPTIVE-ONLY, SEBI-safe: no book, no ranking, no buy/sell.

HYPOTHESIS. A within-name, quarter-adjusted RISE in *net-uncertainty language* precedes HIGHER forward
idiosyncratic realized volatility ("management uncertainty → outcome uncertainty"). Return (CAR60) is a
secondary null only; it cannot create a pass.

FEATURE (register-split net-tone; the v1 fixes are the point). net_uncertainty = (uncertainty_hits −
confidence_hits) per 1000 word tokens. Ubiquitous weak modals contribute ZERO weight (the strongest cap
on modal domination — "may" is dropped entirely, month-May contamination). Bigrams matched FIRST and
their spans consumed so a phrase cannot also score as a unigram (v1 triple-counted "difficult to say").
NEGATION: a unigram hit preceded within 2 tokens by {no,not,never,without,cannot,hardly} is suppressed;
polarity-flip idioms ("no doubt", "good/strong/clear visibility") are scored as CONFIDENCE via the bigram
layer. Idiosyncratic vol = std of (stock adj_close daily return − Nifty-500 daily return) over the window
(excess-return proxy, robust to transcription noise). Q&A/management-answer segmentation is DEFERRED for
this run (parser coverage unvalidated) — a whole-transcript score; noted, not silently dropped.

DIFFERENCING. Within-name × within-CALENDAR-QUARTER double-difference: residual = call score − mean of the
SAME symbol's PRIOR same-calendar-quarter calls (>=2 priors required, else the event is excluded). Kills
the FY-end-guidance seasonal step that dominated v1's spike tercile.

OUTCOME. vol_uplift = ln(forward-60-session idio realized vol / prior-60-session idio vol), measured from
the close of t0+ENTRY_LAG (same no-leak plumbing as PEAD). Events with a corporate action in either
window, illiquid names (med_turn < LIQ_FLOOR), or short history are dropped.

COHORTS. Disjoint rank terciles of the residual: top = uncertainty SPIKE, bottom = confidence/clarity
control (DROP). Require SPIKE n >= MIN_N (=100) usable-vol events. Distinct spike symbols reported
separately from event count (v1's honest breadth was 1,097 delta-eligible / ~700-900 spike symbols).

PRE-REGISTERED GATE (result to the ledger, win or lose). PASS-descriptive requires ALL of —
  (1) SPIKE mean vol_uplift > 0 AND cohort-clustered t_cohort >= +2.0 (evlib.cohort_t),
  (2) same (positive) sign in BOTH halves split at the CHRONOLOGICAL EVENT-COUNT MEDIAN (not a fixed date),
  (3) placebo clears: observed uplift beats a within-name SAME-CALENDAR-QUARTER random-date null
      (n=PLACEBO_N, seed 42; inflation_x>1),
  (4) within-universe contrast: SPIKE above DROP, Cliff's delta(spike,drop) >= +0.10.
FAIL -> publish the null. CAR60 secondary, cannot create a pass.

Run on VPS (research venv):
  ... -m explosive_moves.hedge_density_v2 --build   # transcripts -> research.db.concall_lexical_v2
  ... --run                                         # writes out/hedge_density_v2.json
  ... --selftest                                    # offline, no DB
"""
from __future__ import annotations

import bisect
import json
import os
import random
import re
import sqlite3
import sys
from datetime import datetime

import numpy as np

from . import evlib, pead
from .common import RESEARCH_DB, cliffs_delta, load_series, main_conn, research_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "hedge_density_v2.json")
K_PRIOR = 2                 # >=2 prior SAME-CALENDAR-QUARTER calls for a residual
MIN_N = 100
VOL_WIN = 60               # sessions in each vol window
PLACEBO_N = 200
MIN_TOKENS = 200
_WORD = re.compile(r"[a-z][a-z']+")
_NEG = {"no", "not", "never", "without", "cannot", "hardly", "lack", "barely"}

# ── register lexicons (v2). Weak modals contribute ZERO — they are not listed. ────────────────
UNC_UNI = {
    "uncertain", "uncertainty", "unclear", "unpredictable", "unknown", "doubtful", "doubt",
    "cautious", "caution", "difficult", "challenging", "headwind", "headwinds", "soft", "softness",
    "sluggish", "muted", "subdued", "weak", "weakness", "pressure", "pressured", "visibility",
    "concern", "concerned", "concerns", "tentative", "contingent", "fluctuate", "fluctuating",
    "volatile", "volatility", "gradual", "gradually", "phased", "calibrated", "moderate",
    "moderation", "moderating", "evolving", "monitor", "monitoring", "endeavour", "endeavor",
    "aspire", "aspiring", "deferred", "delay", "delays", "delayed", "tepid", "lacklustre",
    "degrowth", "wary", "guarded", "slowdown",
}
CONF_UNI = {
    "confident", "confidence", "strong", "strongly", "robust", "healthy", "comfortable", "record",
    "momentum", "tailwind", "tailwinds", "committed", "clarity", "resilient", "solid", "buoyant",
    "upbeat", "accelerate", "accelerating", "outperform", "strongest", "encouraged", "encouraging",
    "pleased", "delighted", "confidently", "reaffirm", "reiterate",
}
UNC_BI = ["difficult to", "too early", "wait and watch", "hard to say", "not sure",
          "remains to be seen", "limited visibility", "under pressure", "some pressure",
          "no guidance", "green shoots", "cautiously optimistic", "subject to", "depends on",
          "as of now", "poor visibility", "little visibility"]
CONF_BI = ["on track", "well positioned", "double digit", "strong visibility", "good visibility",
           "no doubt", "record high", "strong momentum", "clear visibility", "very confident",
           "high confidence", "strongly positioned"]
_UNC_BI = {tuple(b.split()) for b in UNC_BI}
_CONF_BI = {tuple(b.split()) for b in CONF_BI}


def score_v2(text: str) -> tuple[int, int, int]:
    """(n_tokens, unc_hits, conf_hits) with bigram-first span consumption + negation suppression."""
    toks = _WORD.findall(text.lower())
    n = len(toks)
    if n == 0:
        return 0, 0, 0
    consumed = [False] * n
    unc = conf = 0
    for i in range(n - 1):
        if consumed[i] or consumed[i + 1]:
            continue
        pair = (toks[i], toks[i + 1])
        if pair in _UNC_BI:
            unc += 1; consumed[i] = consumed[i + 1] = True
        elif pair in _CONF_BI:
            conf += 1; consumed[i] = consumed[i + 1] = True
    for i in range(n):
        if consumed[i]:
            continue
        w = toks[i]
        if w not in UNC_UNI and w not in CONF_UNI:
            continue
        if any(toks[j] in _NEG for j in range(max(0, i - 2), i)):   # negation suppresses
            continue
        if w in UNC_UNI:
            unc += 1
        else:
            conf += 1
    return n, unc, conf


# ── stage 1: build the v2 feature over the corpus ─────────────────────────────
def build_features(limit: int | None = None) -> int:
    hcon = main_conn()
    try:
        rows = hcon.execute(
            "SELECT symbol, concall_dt, transcript_path, transcript_url FROM concalls "
            "WHERE concall_dt IS NOT NULL AND transcript_path IS NOT NULL "
            "ORDER BY symbol, concall_dt, transcript_url").fetchall()
    finally:
        hcon.close()
    print(f"dated transcripts with a path: {len(rows)}", flush=True)
    by_ev: dict[tuple, tuple] = {}
    skipped = collapsed = 0
    for r in rows:
        path = r["transcript_path"]
        if not path or not os.path.exists(path):
            skipped += 1
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            skipped += 1
            continue
        n, unc, conf = score_v2(text)
        if n < MIN_TOKENS:
            skipped += 1
            continue
        net = 1000.0 * (unc - conf) / n
        cdt = str(r["concall_dt"])[:10]
        key = (r["symbol"], cdt)
        prev = by_ev.get(key)
        if prev is not None:
            collapsed += 1
            if prev[3] >= n:
                continue
        by_ev[key] = (r["symbol"], cdt, n, unc, conf, net)
        if limit and len(by_ev) >= limit:
            break
    scored = list(by_ev.values())
    rcon = research_conn()
    try:
        rcon.execute("DROP TABLE IF EXISTS concall_lexical_v2")
        rcon.execute("""CREATE TABLE concall_lexical_v2(
            symbol TEXT, concall_dt TEXT, n_tokens INT, unc INT, conf INT, net REAL,
            PRIMARY KEY(symbol, concall_dt))""")
        rcon.execute("CREATE TABLE IF NOT EXISTS concall_lexical_v2_meta(k TEXT PRIMARY KEY, v TEXT)")
        rcon.executemany("INSERT OR REPLACE INTO concall_lexical_v2 VALUES (?,?,?,?,?,?)", scored)
        rcon.execute("INSERT OR REPLACE INTO concall_lexical_v2_meta VALUES('partial', ?)",
                     (str(int(limit is not None)),))
        rcon.execute("INSERT OR REPLACE INTO concall_lexical_v2_meta VALUES('built_at', ?)",
                     (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),))
        rcon.commit()
    finally:
        rcon.close()
    nets = [s[5] for s in scored]
    print(f"concall_lexical_v2: {len(scored)} scored, {skipped} skipped, {collapsed} dupes collapsed "
          f"({len({s[0] for s in scored})} symbols); net mean={np.mean(nets):+.3f} sd={np.std(nets):.3f}",
          flush=True)
    return len(scored)


# ── stage 2: double-difference deltas, vol outcome, cohorts, placebo ──────────
def _qtr(d: str) -> int:
    return (int(d[5:7]) - 1) // 3 + 1


def _load_deltas(rcon) -> list[dict]:
    """residual = net − mean(prior SAME-calendar-quarter same-symbol calls); >=K_PRIOR priors."""
    by: dict[str, list[tuple]] = {}
    for sym, dt, net in rcon.execute(
            "SELECT symbol, concall_dt, net FROM concall_lexical_v2 WHERE concall_dt IS NOT NULL "
            "ORDER BY symbol, concall_dt"):
        by.setdefault(sym, []).append((str(dt)[:10], float(net)))
    out = []
    for sym, rows in by.items():
        for i in range(len(rows)):
            q = _qtr(rows[i][0])
            prior = [rows[j][1] for j in range(i) if _qtr(rows[j][0]) == q]   # SAME calendar quarter, before
            if len(prior) < K_PRIOR:
                continue
            out.append({"sym": sym, "t0": rows[i][0], "d": rows[i][1] - float(np.mean(prior))})
    return out


def _terciles(dl: list[dict]):
    order = sorted(range(len(dl)), key=lambda i: dl[i]["d"])
    n = len(dl); n3 = n // 3
    return [dl[i] for i in order[:n3]], [dl[i] for i in order[n - n3:]]   # drop(low), spike(high)


def _idio_ret(ss, idx_dates, idx_map) -> np.ndarray:
    """Per-row idiosyncratic daily return = stock adj_close return − Nifty-500 return (excess proxy)."""
    ac = ss.adj_close
    il = np.array([pead.idx_level_asof(idx_dates, idx_map, d) for d in ss.date], dtype=float)
    ir = np.full(ss.n, np.nan)
    for i in range(1, ss.n):
        if ac[i] > 0 and ac[i - 1] > 0 and il[i] > 0 and il[i - 1] > 0 and il[i] == il[i] and il[i - 1] == il[i - 1]:
            ir[i] = (ac[i] / ac[i - 1] - 1.0) - (il[i] / il[i - 1] - 1.0)
    return ir


def _vol(ir: np.ndarray, a: int, b: int) -> float | None:
    """std of idio returns over rows (a, b]; None if too few valid."""
    seg = ir[a + 1:b + 1]
    seg = seg[~np.isnan(seg)]
    if len(seg) < VOL_WIN // 2:
        return None
    return float(np.std(seg, ddof=1))


def _uplift_at(ss, ir, i0: int) -> float | None:
    """ln(forward-VOL_WIN idio vol / prior-VOL_WIN idio vol) at row i0 (t0), entry = i0+ENTRY_LAG."""
    entry = i0 + pead.ENTRY_LAG
    if i0 < pead.MIN_PRIOR_ROWS or i0 - 1 - VOL_WIN < 0 or entry + VOL_WIN >= ss.n:
        return None
    mt = ss.med_turn[i0 - 1]
    if not (mt == mt and mt >= pead.LIQ_FLOOR):
        return None
    if ss.is_ca[max(0, i0 - 1 - VOL_WIN):entry + VOL_WIN + 1].any():   # no CA in either window
        return None
    pv = _vol(ir, i0 - 1 - VOL_WIN, i0 - 1)
    fv = _vol(ir, entry, entry + VOL_WIN)
    if not pv or not fv or pv <= 0 or fv <= 0:
        return None
    return float(np.log(fv / pv))


def run() -> dict:
    hcon = main_conn()
    try:
        try:
            rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
            try:
                deltas = _load_deltas(rcon)
            finally:
                rcon.close()
        except sqlite3.Error as e:
            raise SystemExit(f"no concall_lexical_v2 yet — run --build first ({e})")
        if not deltas:
            raise SystemExit("no within-name×within-quarter deltas — run --build first")
        drop, spike = _terciles(deltas)
        print(f"deltas={len(deltas)}  spike(top)={len(spike)}  drop(bottom)={len(drop)}", flush=True)

        idx_dates, idx_map = evlib.index_levels(hcon)
        series: dict = {}; irs: dict = {}

        def uplift(sym, t0):
            if sym not in series:
                ss = series[sym] = load_series(hcon, sym)
                irs[sym] = _idio_ret(ss, idx_dates, idx_map) if ss is not None else None
            ss, ir = series[sym], irs[sym]
            if ss is None or ir is None:
                return None
            i0 = bisect.bisect_left(ss.date, t0)
            if i0 >= ss.n:
                return None
            return _uplift_at(ss, ir, i0)

        def pairs(cohort):
            used = []
            for d in cohort:
                u = uplift(d["sym"], d["t0"])
                if u is not None:
                    used.append((d, u))
            return used

        spike_rows, drop_rows = pairs(spike), pairs(drop)
        spike_used = [d for d, _u in spike_rows]
        spike_pairs = [(d["t0"], u) for d, u in spike_rows]
        drop_pairs = [(d["t0"], u) for d, u in drop_rows]
        print(f"usable vol_uplift: spike={len(spike_pairs)} drop={len(drop_pairs)} "
              f"(spike symbols={len({d['sym'] for d in spike_used})})", flush=True)

        out: dict = {"study": "Concall net-uncertainty -> forward idio realized-vol (v2)",
                     "gate": "spike mean>0 AND t_cohort>=+2 AND pos both halves AND placebo clears AND "
                             "Cliff(spike,drop)>=+0.10",
                     "n_deltas": len(deltas), "n_spike": len(spike_pairs), "n_drop": len(drop_pairs),
                     "vol_win": VOL_WIN, "k_prior": K_PRIOR}
        spike_ct = evlib.cohort_t(spike_pairs)
        drop_ct = evlib.cohort_t(drop_pairs)
        out["spike"] = spike_ct
        out["drop"] = drop_ct
        # event-count median split (chronological)
        ts = sorted(t for t, _ in spike_pairs)
        split = ts[len(ts) // 2] if ts else "2023-06-30"
        out["half_split"] = split
        h1 = evlib.cohort_t([p for p in spike_pairs if p[0] < split])
        h2 = evlib.cohort_t([p for p in spike_pairs if p[0] >= split])
        out["spike_h1"], out["spike_h2"] = h1, h2

        spike_u = np.array([u for _t, u in spike_pairs])
        drop_u = np.array([u for _t, u in drop_pairs])
        cliff = cliffs_delta(spike_u, drop_u) if len(spike_u) and len(drop_u) else float("nan")
        out["cliff_spike_vs_drop"] = cliff

        pos_both = (h1.get("mean") is not None and h2.get("mean") is not None
                    and h1["mean"] > 0 and h2["mean"] > 0)
        gate_ok = (len(spike_pairs) >= MIN_N
                   and spike_ct.get("mean", 0) > 0
                   and (spike_ct.get("t_cohort") or 0) >= 2.0
                   and pos_both)

        # (3) placebo: same spike events, random SAME-CALENDAR-QUARTER eligible dates
        if gate_ok:
            rng = random.Random(42)
            elig: dict[str, dict[int, list]] = {}
            for d in spike_used:
                sym = d["sym"]
                if sym in elig:
                    continue
                ss, ir = series.get(sym), irs.get(sym)
                if ss is None or ir is None:
                    elig[sym] = {}
                    continue
                buckets: dict[int, list] = {}
                for i0 in range(pead.MIN_PRIOR_ROWS, ss.n - pead.ENTRY_LAG - VOL_WIN - 1):
                    if i0 - 1 - VOL_WIN < 0:
                        continue
                    buckets.setdefault(_qtr(ss.date[i0]), []).append(i0)
                elig[sym] = buckets
            observed = float(np.mean(spike_u))
            null_means = []
            for k in range(PLACEBO_N):
                vals = []
                for d in spike_used:
                    ss, ir = series.get(d["sym"]), irs.get(d["sym"])
                    if ss is None or ir is None:
                        continue
                    cand = elig[d["sym"]].get(_qtr(d["t0"]), [])
                    if not cand:
                        continue
                    u = _uplift_at(ss, ir, cand[rng.randrange(len(cand))])
                    if u is not None:
                        vals.append(u)
                if vals:
                    null_means.append(float(np.mean(vals)))
                if (k + 1) % 50 == 0:
                    print(f"  placebo {k + 1}/{PLACEBO_N}", flush=True)
            out["placebo"] = evlib.placebo_stats(observed, null_means)
            cleared = (out["placebo"].get("inflation_x") or 0) > 1.0
            out["verdict"] = ("PASS-descriptive"
                              if (cleared and cliff == cliff and cliff >= 0.10)
                              else "FAIL-null-published")
        else:
            out["verdict"] = "FAIL-null-published"

        out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=float)
        print(f"SPIKE mean vol_uplift {spike_ct.get('mean', 0):+.4f}  t_cohort="
              f"{spike_ct.get('t_cohort', float('nan')):.2f}  DROP {drop_ct.get('mean', 0):+.4f}  "
              f"cliff={cliff:+.3f}", flush=True)
        print("verdict:", out["verdict"], flush=True)
        return out
    finally:
        hcon.close()


def selftest() -> None:
    # scorer: net-uncertainty positive when hedging dominates; negation + bigram consumption
    n, u, c = score_v2("the outlook is uncertain and visibility is limited under pressure difficult to say")
    assert u >= 3 and c == 0, (n, u, c)
    n2, u2, c2 = score_v2("we are confident of strong momentum on track with record numbers and no doubt")
    assert c2 >= 3 and u2 == 0, (n2, u2, c2)          # "no doubt" -> confidence bigram, not uncertainty
    n3, u3, c3 = score_v2("there is no concern and not difficult at all")
    assert u3 == 0, (n3, u3, c3)                      # negation suppresses "concern"/"difficult"
    # calendar-quarter helper
    assert _qtr("2024-05-10") == 2 and _qtr("2024-11-01") == 4
    # disjoint terciles
    dl = [{"sym": "X", "t0": "2020-01-01", "d": v} for v in [-2, -1, 0, 1, 2, 3, 4, 5, 6]]
    drp, spk = _terciles(dl)
    assert not ({id(x) for x in drp} & {id(x) for x in spk}) and len(drp) == 3 and len(spk) == 3
    # vol slice
    ir = np.array([np.nan] + [0.01, -0.02, 0.015, -0.01] * 40)
    v = _vol(ir, 0, 120)
    assert v is not None and v > 0
    # cohort_t sign convention (positive uplift, significant)
    pos = [(f"20{18 + q // 4}-{(q % 4) * 3 + 1:02d}-15", 0.20 + 0.01 * (i % 3)) for q in range(8) for i in range(6)]
    ct = evlib.cohort_t(pos)
    assert ct["mean"] > 0 and ct["t_cohort"] > 2 and ct["n_cohorts"] == 8
    print("HEDGE_DENSITY_V2 selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        rest = [a for a in sys.argv if a.isdigit()]
        build_features(limit=int(rest[0]) if rest else None)
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
