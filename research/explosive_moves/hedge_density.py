"""Concall hedge-density drift — PRE-REGISTERED 2026-07-12 (AI-pattern engine, slice 1).

WHY THIS, WHY DETERMINISTIC. The concall CONTENT signal (growth-intent by statement_type)
was already return-tested on real dates and PLACEBO-KILLED — concall_intent: +1.90% vs
null p95 +3.66% ("covered-name drift", ledger). The Gemini-extracted guidance tables that
richer language attributes would need cover only ~44 symbols (the breadth wall, ledger),
far below any cohort gate, and an LLM reading a historical transcript can leak the future
(Glasserman-Lin, arXiv:2309.17322). This slice deliberately sidesteps all three: a
DETERMINISTIC lexical feature (no LLM -> no look-ahead) over the FULL dated-transcript
corpus (~16k calls -> breadth), differenced WITHIN each name (the covered-name-drift
defense concall_intent lacked).

HYPOTHESIS (mechanism). Management conviction erodes in LANGUAGE before it shows up in the
numbers: a within-name JUMP in hedging / uncertainty word density from one call to the next
("subject to", "hope", "may", "limited visibility", "under pressure") precedes forward
UNDERperformance vs Nifty 500. Constant sector jargon cancels under within-name differencing,
so only the CHANGE in hedging is the treatment.

FEATURE (measurable, no LLM). hedge_density(call) = (hedge+uncertainty tokens) / word tokens,
a Loughran-McDonald weak-modal+uncertainty-derived lexicon (LEX below; swap the full LM master
dictionary in on the box). Within a symbol, ordered by concall_dt, baseline = mean of the
prior K=3 calls; delta = hedge_density - baseline (needs >=K priors). Pool deltas; SPIKE =
top tercile (hedging rose), DROP = bottom tercile (hedging fell) — DROP is the within-universe
control.

EVENT / RETURN. t0 = concall_dt (the call IS the public event); entry = t0 + ENTRY_LAG;
CAR60 vs Nifty 500 via pead_surface.reaction_row (same no-leak plumbing as PEAD/concall_intent).

PRE-REGISTERED GATE (result to the ledger, win or lose). With SPIKE cohort n >= MIN_N (=100),
PASS-descriptive (a DESCRIPTIVE lens ships) requires ALL of —
  (1) SPIKE mean CAR60 < 0 AND cohort-clustered t_cohort <= -2.0 (evlib.cohort_t),
  (2) same (negative) sign in BOTH halves at 2021-07-01,
  (3) date-shuffle placebo clears on the SPIKE cohort (n=200, seed 42): observed
      underperformance beats the within-name null band (inflation_x>1 on NEGATED returns),
  (4) within-universe contrast holds: SPIKE below DROP, Cliff's delta(spike,drop) <= -0.10.
FAIL -> publish the null: "concall hedge-density carries no forward return" is recorded.
Book leg: NOT run (priors F3 net momentum 0.09; F6 every event wrapper 0.02-0.10 vs 0.85;
concall_intent covered-name-drift null). Any book needs its own pre-registration citing them.
DESCRIPTIVE-ONLY, SEBI-safe: no ranking, no buy/sell, no return promise — a realized-history lens.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.hedge_density --build      # transcripts -> research.db.concall_lexical
  ... --run                                         # writes out/hedge_density.json
  ... --selftest                                    # offline, no DB
"""
# ── POST-RUN CLARIFICATIONS (2026-07-13; reviewed with an external reviewer) ───────────────
# The docstring above is the FROZEN pre-registration; the prereg hash = sha256(__doc__) =
# 538a08a8… (prereg.py), confirmed clean by `prereg.py --verify` on the box (OK, 2026-07-13).
# These notes are interpretation/scope ONLY and live OUTSIDE __doc__, so they do not alter the
# hash. (NB: `ast.get_docstring()` defaults to clean=True and DEDENTS the text, giving a
# different digest — always hash the RAW __doc__ to reproduce 538a08a8.)
#   F1 (cut scope): run()'s SPIKE/DROP tercile cuts are computed over the FULL pooled within-name
#     delta distribution — the standard retrospective cross-sectional sort (cf.
#     pead_surface._breakpoints, evlib.run_pead_placebo). No outcome/return EVER enters cohort
#     membership; the docstring's "no look-ahead" scopes the FEATURE (deterministic, no LLM, no
#     return leak), which holds. This is a realized-history DESCRIPTIVE lens with no decision-time
#     — full-sample cuts are correct here.  ⚠ If ever promoted to a LIVE surface that labels
#     TODAY's call SPIKE/DROP, the cuts MUST become frozen/expanding (they would then be a real
#     point-in-time defect).
#   F2 (gate leg 4): "SPIKE below DROP, Cliff's delta(spike,drop) <= -0.10" is ONE contrast —
#     Cliff's delta is the deliberately outlier-ROBUST operationalization of "SPIKE below DROP"
#     (chosen over a raw mean precisely for that robustness). The code enforces it faithfully; no
#     separate raw-mean leg is intended.
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
from datetime import datetime

import numpy as np

from . import evlib
from .common import RESEARCH_DB, cliffs_delta, load_series, main_conn, research_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "hedge_density.json")
K_PRIOR = 3
MIN_N = 100
HALF_SPLIT = "2021-07-01"
MIN_TOKENS = 200            # a real transcript; shorter rows are stubs/errors

# Loughran-McDonald weak-modal + uncertainty derived hedging lexicon (unigrams).
# Curated subset — deterministic and auditable; the full LM master dict can be dropped
# in on the box. Within-name differencing cancels each name's baseline usage, so only a
# CHANGE in these registers is the treatment.
LEX = {
    # weak modal / tentativeness
    "may", "might", "could", "would", "should", "possibly", "perhaps", "maybe",
    "apparently", "appears", "appear", "seems", "seem", "suggest", "suggests",
    "assume", "assumes", "assumed", "depend", "depends", "depending", "conditional",
    "contingent", "tentative", "roughly", "approximately", "approximate", "somewhat",
    "sometimes", "occasionally", "seldom", "likely", "unlikely", "probable",
    "probably", "presumably",
    # uncertainty / caution
    "uncertain", "uncertainty", "unclear", "unpredictable", "unknown", "indefinite",
    "ambiguous", "doubtful", "doubt", "fluctuate", "fluctuating", "cautious", "caution",
    "hopefully", "hope", "hoping", "concern", "concerned", "difficult", "challenging",
    "headwind", "headwinds", "soft", "softness", "sluggish", "muted", "subdued",
    "pressure", "pressured", "visibility", "watch",
}
LEX_BIGRAMS = [
    "subject to", "depend on", "depends on", "difficult to", "too early",
    "wait and watch", "hard to say", "not sure", "as of now", "let us see",
    "let's see", "visibility is", "under pressure", "some pressure", "cannot commit",
    "no specific guidance", "difficult to say", "remains to be seen", "limited visibility",
]
_WORD = re.compile(r"[a-z][a-z']+")


def hedge_density(text: str) -> tuple[int, int]:
    """(hedge_hits, n_word_tokens) for a transcript. density = hits / n_tokens."""
    t = text.lower()
    toks = _WORD.findall(t)
    n = len(toks)
    if n == 0:
        return 0, 0
    hits = sum(1 for w in toks if w in LEX)
    for bg in LEX_BIGRAMS:
        hits += t.count(bg)
    return hits, n


# ── stage 1: build the deterministic feature over the full corpus ─────────────

def build_features(limit: int | None = None) -> int:
    """Read every dated transcript, score hedge_density, cache to research.db.

    Feature-table PK is (symbol, concall_dt) — the SAME key the event study uses — not
    (symbol, period_label): the source `concalls` natural key is (symbol, period_label,
    transcript_url), so a revised transcript at a new URL could otherwise silently drop a
    genuinely-distinct call (F-bonus). Same-date re-uploads are collapsed to ONE canonical
    row (the fullest transcript). A truncated `--build N` records `partial=1` in
    concall_lexical_meta so run() can refuse to publish off it (F8).
    """
    hcon = main_conn()
    try:
        rows = hcon.execute(
            "SELECT symbol, period_label, concall_dt, transcript_path, transcript_url FROM concalls "
            "WHERE concall_dt IS NOT NULL AND transcript_path IS NOT NULL "
            "ORDER BY symbol, concall_dt, transcript_url").fetchall()   # transcript_url = deterministic tie-break
    finally:
        hcon.close()
    print(f"dated transcripts with a path: {len(rows)}", flush=True)
    by_ev: dict[tuple, tuple] = {}                          # (symbol, concall_dt) -> canonical row
    collapsed = skipped = 0
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
        hits, ntok = hedge_density(text)
        if ntok < MIN_TOKENS:
            skipped += 1
            continue
        cdt = str(r["concall_dt"])[:10]
        key = (r["symbol"], cdt)
        prev = by_ev.get(key)
        if prev is not None:
            collapsed += 1
            if prev[3] >= ntok:                            # keep the fuller transcript; deterministic
                continue
        by_ev[key] = (r["symbol"], r["period_label"], cdt, ntok, hits, hits / ntok)
        if limit and len(by_ev) >= limit:
            break
    scored = list(by_ev.values())

    rcon = research_conn()
    try:
        # DROP+CREATE (not CREATE IF NOT EXISTS): an existing table would keep its OLD PK, so a
        # rebuild is required to guarantee the PK is really (symbol, concall_dt).
        rcon.execute("DROP TABLE IF EXISTS concall_lexical")
        rcon.execute("""CREATE TABLE concall_lexical(
            symbol TEXT, period_label TEXT, concall_dt TEXT, n_tokens INT,
            hedge_tokens INT, hedge_density REAL, PRIMARY KEY(symbol, concall_dt))""")
        rcon.execute("CREATE TABLE IF NOT EXISTS concall_lexical_meta(k TEXT PRIMARY KEY, v TEXT)")
        rcon.executemany("INSERT OR REPLACE INTO concall_lexical VALUES (?,?,?,?,?,?)", scored)
        rcon.execute("INSERT OR REPLACE INTO concall_lexical_meta VALUES('partial', ?)",
                     (str(int(limit is not None)),))
        rcon.execute("INSERT OR REPLACE INTO concall_lexical_meta VALUES('built_at', ?)",
                     (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),))
        rcon.commit()
    finally:
        rcon.close()
    tag = f"  ⚠ PARTIAL (limit={limit}) — do NOT --run for a published number" if limit else ""
    print(f"concall_lexical: {len(scored)} calls scored, {skipped} skipped, "
          f"{collapsed} same-date dupes collapsed "
          f"({len({s[0] for s in scored})} distinct symbols){tag}", flush=True)
    return len(scored)


# ── stage 2: within-name deltas -> cohorts -> event study ─────────────────────

def _within_name_deltas(rows: list[dict]) -> list[dict]:
    """rows for ONE symbol sorted by t0; delta = hd - mean(prior K). Needs >=K priors."""
    out = []
    for i in range(K_PRIOR, len(rows)):
        base = float(np.mean([rows[j]["hd"] for j in range(i - K_PRIOR, i)]))
        out.append({**rows[i], "delta": rows[i]["hd"] - base})
    return out


def _load_deltas(rcon) -> list[dict]:
    by_sym: dict[str, list[dict]] = {}
    for sym, dt, hd in rcon.execute(
            "SELECT symbol, concall_dt, hedge_density FROM concall_lexical "
            "WHERE concall_dt IS NOT NULL ORDER BY symbol, concall_dt"):
        by_sym.setdefault(sym, []).append({"sym": sym, "t0": str(dt)[:10], "hd": float(hd)})
    deltas = []
    for evs in by_sym.values():
        deltas.extend(_within_name_deltas(evs))
    return deltas


def _cache_is_partial(rcon) -> bool:
    """True if the feature cache was written by a truncated ``--build N`` (F8 provenance)."""
    try:
        row = rcon.execute("SELECT v FROM concall_lexical_meta WHERE k='partial'").fetchone()
    except sqlite3.Error:
        return False                       # pre-meta cache: unknown -> treat as full
    return bool(row and str(row[0]) == "1")


def _terciles(deltas: list[dict]) -> tuple[list, list, float, float]:
    """Bottom/top terciles by RANK, DISJOINT by construction (F5): an event can never land in
    BOTH spike and drop even when >1/3 of deltas are tied (a threshold split double-counts when
    the 1/3 and 2/3 quantiles coincide). Returns (drop, spike, lo_edge, hi_edge)."""
    order = sorted(range(len(deltas)), key=lambda i: deltas[i]["delta"])
    n = len(deltas)
    n3 = n // 3
    drop = [deltas[i] for i in order[:n3]]                 # hedging fell (control)
    spike = [deltas[i] for i in order[n - n3:]]            # hedging rose
    lo_t = float(deltas[order[n3 - 1]]["delta"]) if n3 else float("nan")
    hi_t = float(deltas[order[n - n3]]["delta"]) if n3 else float("nan")
    return drop, spike, lo_t, hi_t


def run(allow_partial: bool = False) -> dict:
    hcon = main_conn()
    try:
        try:
            rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
            try:
                deltas = _load_deltas(rcon)
                partial = _cache_is_partial(rcon)
            finally:
                rcon.close()
        except sqlite3.Error as e:
            raise SystemExit(f"no concall_lexical yet — run --build first ({e})")
        if not deltas:                                         # F7: empty-but-present cache
            raise SystemExit("no within-name deltas — run --build first "
                             "(need >=K_PRIOR+1 calls per symbol before a delta forms)")
        if partial and not allow_partial:                      # F8: refuse to publish off a partial cache
            raise SystemExit("PARTIAL feature cache (built via --build N) — refusing to publish. "
                             "Rebuild with a full `--build`, or pass --allow-partial for a dev run "
                             "(its output is marked NOT publishable).")
        if partial:
            print("⚠ --allow-partial: PARTIAL cache — this output is NOT publishable.", flush=True)
        if len(deltas) < 3 * MIN_N:
            print(f"WARNING: only {len(deltas)} within-name deltas — "
                  f"breadth may be below the cohort gate", flush=True)

        drop, spike, lo_t, hi_t = _terciles(deltas)            # F5: disjoint by rank
        print(f"deltas={len(deltas)}  spike(top-tercile)={len(spike)}  drop(bottom)={len(drop)}  "
              f"cut edges [{lo_t:+.4f}, {hi_t:+.4f}]", flush=True)

        idx_dates, idx_map = evlib.index_levels(hcon)
        series: dict = {}

        def car60_of(sym: str, t0: str):
            ss = series.setdefault(sym, load_series(hcon, sym))
            if ss is None:
                return None, None
            r = reaction_row(ss, {"sym": sym, "ptype": "C", "pend": t0, "t0": t0, "sue": 0.0},
                             idx_dates, idx_map)
            if r is None or r["car60"] != r["car60"]:
                return ss, None
            return ss, r["car60"]

        def cars(cohort):
            rows = []
            for d in cohort:
                _ss, c = car60_of(d["sym"], d["t0"])
                if c is not None:
                    rows.append((d, c))                        # F3: keep the event for the placebo
            return rows

        spike_rows, drop_rows = cars(spike), cars(drop)
        spike_used = [d for d, _c in spike_rows]               # EXACT events behind observed_neg
        spike_pairs = [(d["t0"], c) for d, c in spike_rows]
        drop_pairs = [(d["t0"], c) for d, c in drop_rows]
        print(f"usable CAR60: spike={len(spike_pairs)} drop={len(drop_pairs)}", flush=True)

        out: dict = {"study": "Concall hedge-density drift (deterministic, within-name)",
                     "gate": "spike mean<0 AND t_cohort<=-2 AND neg both halves AND placebo "
                             "clears AND Cliff(spike,drop)<=-0.10",
                     "n_deltas": len(deltas), "cut_lo": lo_t, "cut_hi": hi_t,
                     "n_spike": len(spike_pairs), "n_drop": len(drop_pairs),
                     "build_partial": bool(partial)}
        spike_ct = evlib.cohort_t(spike_pairs)
        drop_ct = evlib.cohort_t(drop_pairs)
        h1 = evlib.cohort_t([p for p in spike_pairs if p[0] < HALF_SPLIT])
        h2 = evlib.cohort_t([p for p in spike_pairs if p[0] >= HALF_SPLIT])
        out["spike"] = spike_ct
        out["drop"] = drop_ct
        out["spike_h1"], out["spike_h2"] = h1, h2

        spike_cars = np.array([c for _t, c in spike_pairs])
        drop_cars = np.array([c for _t, c in drop_pairs])
        cliff = cliffs_delta(spike_cars, drop_cars) if len(spike_cars) and len(drop_cars) else float("nan")
        out["cliff_spike_vs_drop"] = cliff

        same_sign_neg = (h1.get("mean") is not None and h2.get("mean") is not None
                         and h1["mean"] < 0 and h2["mean"] < 0)

        gate_ok = (len(spike_pairs) >= MIN_N
                   and spike_ct.get("mean", 0) < 0
                   and (spike_ct.get("t_cohort") or 0) <= -2.0
                   and same_sign_neg)

        # (3) placebo on the SPIKE cohort, NEGATED so the machinery tests downside magnitude.
        # F3: iterate the SAME events that produced observed_neg (spike_used), matching M-02
        # (evlib.run_pead_placebo iterates its usable-CAR60 `cell`, not the pre-filter cohort).
        if gate_ok:
            rng = random.Random(42)
            observed_neg = -float(np.mean(spike_cars))
            null_means = []
            for k in range(200):
                neg = []
                for d in spike_used:
                    ss = series.get(d["sym"])
                    if ss is None:
                        continue
                    lo, hi = evlib.eligible_indices(ss, 60)
                    if hi <= lo:
                        continue
                    i0 = rng.randrange(lo, hi)
                    r = reaction_row(ss, {"sym": d["sym"], "ptype": "C", "pend": d["t0"],
                                          "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
                    if r is not None and r["car60"] == r["car60"]:
                        neg.append(-r["car60"])
                if neg:
                    null_means.append(float(np.mean(neg)))
                if (k + 1) % 50 == 0:
                    print(f"  placebo {k + 1}/200", flush=True)
            out["placebo"] = evlib.placebo_stats(observed_neg, null_means)
            cleared = (out["placebo"].get("inflation_x") or 0) > 1.0
            out["verdict"] = ("PASS-descriptive"
                              if (cleared and cliff == cliff and cliff <= -0.10)
                              else "FAIL-null-published")
        else:
            out["verdict"] = "FAIL-null-published"

        out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=float)
        print(f"spike mean CAR60 {100 * (spike_ct.get('mean') or 0):+.2f}% "
              f"t_cohort={spike_ct.get('t_cohort', float('nan')):.2f}  "
              f"drop {100 * (drop_ct.get('mean') or 0):+.2f}%  cliff={cliff:+.3f}", flush=True)
        print("verdict:", out["verdict"], flush=True)
        return out
    finally:
        hcon.close()


# ── selftest (offline, no DB) ─────────────────────────────────────────────────

def selftest() -> None:
    hedgy = ("we may possibly perhaps see uncertain outcomes subject to conditions and we "
             "hope visibility improves though it is difficult to say and remains under pressure")
    plain = ("revenue grew twenty percent margins expanded orders doubled we commissioned the "
             "new plant and delivered record volumes with strong cash generation this quarter")
    h1, n1 = hedge_density(hedgy)
    h2, n2 = hedge_density(plain)
    assert n1 > 0 and n2 > 0 and (h1 / n1) > (h2 / n2), (h1, n1, h2, n2)
    # within-name delta: a spike call scores a large positive delta vs its own baseline
    rows = [{"sym": "X", "t0": f"2020-{m:02d}-01", "hd": hd}
            for m, hd in enumerate([0.01, 0.01, 0.01, 0.05, 0.006], 1)]
    dl = _within_name_deltas(rows)
    assert len(dl) == 2 and abs(dl[0]["delta"] - 0.04) < 1e-9 and dl[1]["delta"] < 0
    # F5: rank terciles stay DISJOINT even when >1/3 of deltas are identical (tie-heavy corpus)
    tied = [{"sym": "T", "t0": "2020-01-01", "delta": v}
            for v in [0.0, 0.0, 0.0, 0.0, 0.0, -0.02, -0.01, 0.01, 0.02]]
    drp, spk, _lo, _hi = _terciles(tied)
    assert not ({id(x) for x in drp} & {id(x) for x in spk}), "spike/drop terciles must be disjoint"
    assert len(drp) == 3 and len(spk) == 3
    # gate arithmetic: negative cohort t + same-sign-negative halves
    neg = [(f"20{18 + q // 4}-{(q % 4) * 3 + 1:02d}-15", -0.02 - 0.001 * (i % 3))
           for q in range(8) for i in range(6)]
    ct = evlib.cohort_t(neg)
    assert ct["mean"] < 0 and ct["t_cohort"] < -2 and ct["n_cohorts"] == 8
    # placebo negation convention: a strong observed downside beats a mild null band
    p = evlib.placebo_stats(0.05, [0.01, 0.0, -0.01, 0.005])
    assert (p["inflation_x"] or 0) > 1.0
    # Cliff's delta: spike returns below drop returns -> negative
    assert cliffs_delta(np.array([-0.05, -0.03, -0.06]), np.array([0.01, 0.02, 0.0])) < -0.5
    print("HEDGE_DENSITY selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        rest = [a for a in sys.argv if a.isdigit()]
        build_features(limit=int(rest[0]) if rest else None)
    elif "--run" in sys.argv:
        run(allow_partial="--allow-partial" in sys.argv)
    else:
        print(__doc__)
