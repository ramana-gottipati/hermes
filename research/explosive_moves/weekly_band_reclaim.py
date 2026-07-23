"""WEEKLY BAND RECLAIM — the LOWER-band reclaim on the WEEKLY timeframe. PRE-REGISTERED 2026-07-23 (S214-b).

WHY / WHAT IS NEW. The signal is T=EMA5(HLC3) crossing UP through L=EMA13(low) — "buy the reclaim after
weakness". Its DAILY form is already FALSIFIED: the STREAM BAND study (ledger 2026-07-13) found the daily
lower-bank reclaim an ANTI-signal (22d excess med −1.25%, both placebos beat it, book return/vol 0.37);
and this session's daily UPPER-band momentum was FAIL-null (Cliff's δ −0.01, par-with-index beta). The ONE
thing genuinely new here is the TIMEFRAME. On WEEKLY bars EMA5≈5 weeks (~1mo) and EMA13≈13 weeks (~3mo),
which drags the 5/13 cross OUT of the 1–4-week short-term-reversal zone (where the daily versions die) and
TOWARD the 2–6-month momentum-persistence zone — the exact horizon critique the daily arc raised. Two more
edges of the weekly frame, both about COST: (1) weekly signals are rare and holds are long → turnover is a
FRACTION of daily, so the cost hurdle that taxed the daily book to par is far more survivable; (2) the
archetype is a legitimate "buy the multi-week pullback in a longer uptrend", not a daily falling knife.

PREDICTION ON RECORD (failure-ledger contract, BEFORE the run): CAUTIOUS-FAIL prior. The daily reclaim was
an anti-signal, so base rate says FAIL. BUT weekly attacks the two reasons daily failed (horizon + cost), so
this is the single crossover variant with the best odds of net-fundability, and it earns ONE clean
pre-registered look. Most-likely outcome (~60%): no cross-sectional SELECTION edge (δ≈0) → the entry is
beta, verdict descriptive-only. Live-odds (~40%, higher than any daily variant): the low weekly turnover
lets a modest swing-momentum edge clear cost. Cite: STREAM BAND 07-13; this-session momentum FAIL-null.

METRIC BASIS (D142): every ratio is annualised mean/sd, NO risk-free subtracted — a return/vol ratio, not a
Sharpe; the Nifty-500 buy-&-hold hurdle 0.89 is on the same basis. Descriptive-only, SEBI-safe.

DESIGN (locked before first run; seed 42; symbols in sorted order; CA-ADJUSTED prices throughout).
Universe = every EQ/CM symbol in bhavcopy_rows. WEEKLY bars = resample daily by ISO week: wHigh=max(adj_high),
wLow=min(adj_low), wClose=adj_close of the last day, wHLC3=(wHigh+wLow+wClose)/3, w_med_turn=median daily
med_turn in the week, w_close_raw=raw close of the last day. Bands on weekly bars: T=EMA5(wHLC3),
L=EMA13(wLow). Signals: entry dates >= 2012-06.
ELIGIBILITY at signal week k: >=26 prior weekly bars; w_med_turn[k] >= Rs 1cr; w_close_raw[k] >= 20; T/L
finite. De-overlap 8 weeks per symbol for EVENT counting; one open trade per symbol for the BOOK.

ENTRY (reclaim, PIT): rising edge — T[k-1] <= L[k-1] AND T[k] > L[k] (trigger reclaims the 13-week low band
from below). Entry = CLOSE of the NEXT weekly bar (k+1). entry_price = wClose[k+1].

EXITS — the proper SL + TSL (act on the WEEKLY close; exit on the FIRST breach = "tighter"):
  down-fractal (weekly 2°-fractal, PIT): a week j whose wLow is strictly < the 2 weeks each side, confirmed
     at j+2. STOP = the ratcheting highest confirmed down-fractal low so far (raised, never lowered).
  band: the reclaim's own invalidation — a weekly close back BELOW L (the momentum-off condition).
  Exit on FIRST of: (a) wClose < the ratcheting down-fractal stop, (b) wClose < L, (c) 52-week time censor.

EVENT-STUDY GATE-1 (SELECTION; does the weekly reclaim pick forward out-performers?). Horizons 4/8/13/26
weeks; excess = symbol forward return (own weekly closes) − Nifty-500 over the identical calendar span.
Controls: 3 same-symbol random eligible-week placebos + one +13-week time-shift placebo. PASS requires ALL:
  G1 n >= 300 primary events
  G2 mean AND median 13-week excess > 0
  G3 Cliff's delta of 13-week excess vs the pooled placebo >= +0.05
  G4 median 13-week excess > 0 in BOTH halves (< / >= 2019-01-01)

GATE-2 BOOK (fundability). Long at the entry weekly close; exit per the SL/TSL above; one open trade/symbol.
Weekly EQUAL-WEIGHT across open trades → aggregated to MONTHLY returns → return/vol. Tiered round-trip cost
(half-spread by liquidity 0.05/0.10/0.20% + 0.12% STT/fees + 0.10% slippage on STOP exits), booked as a
one-time friction on the entry week (total-correct). RAW (gross) and NET books both reported. Control =
random eligible-entry, same exit + cost. FUNDABLE requires NET monthly return/vol > 0.89 in BOTH halves AND
beating the random control by >= +0.15.

DISPOSITION (pre-committed). Gate-1 PASS + Gate-2 net > 0.89 both halves + beats random by >=+0.15 -> NEW
candidate (fresh fences before any promotion). ELSE -> REJECTED, descriptive-only; ledger entry cites
STREAM BAND 07-13 + this-session momentum FAIL and records WHICH gate failed and whether WEEKLY changed the
DAILY verdict.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.weekly_band_reclaim --build     # scan + both gates -> out/weekly_band_reclaim.json
  ... --selftest
"""
from __future__ import annotations

import bisect
import json
import sys
from datetime import date, datetime, timezone

import numpy as np

from .common import OUT_DIR, eq_symbols, load_series, main_conn, research_conn
from .metrics import index_series

START = "2012-06"
LIQ = 1e7
MIN_CLOSE = 20.0
WARMUP = 26            # weekly bars before any signal
DEOV = 8              # weeks between counted events per symbol
MAXHOLD = 52          # week time censor
SEED = 42


def _ema(x, n):
    a = 2.0 / (n + 1.0)
    out = np.empty(len(x))
    m = x[0]
    out[0] = m
    for i in range(1, len(x)):
        m = a * x[i] + (1 - a) * m
        out[i] = m
    return out


def _weekly(S):
    """Resample a daily SymbolSeries to weekly arrays keyed chronologically by ISO week."""
    wk = {}
    order = []
    for i, d in enumerate(S.date):
        y, w, _ = date.fromisoformat(d).isocalendar()
        wid = y * 100 + w
        if wid not in wk:
            wk[wid] = []
            order.append(wid)
        wk[wid].append(i)
    W = len(order)
    if W < WARMUP + 6:
        return None
    hi = np.empty(W); lo = np.empty(W); cl = np.empty(W); mt = np.empty(W); clr = np.empty(W)
    dt = [None] * W; wid = np.empty(W, dtype=np.int64)
    for k, wi in enumerate(order):
        idx = wk[wi]
        last = idx[-1]
        hi[k] = S.adj_high[idx].max()
        lo[k] = S.adj_low[idx].min()
        cl[k] = S.adj_close[last]
        clr[k] = S.close[last]
        mt[k] = float(np.median(S.med_turn[idx]))
        dt[k] = S.date[last]
        wid[k] = wi
    hlc3 = (hi + lo + cl) / 3.0
    return dict(hi=hi, lo=lo, cl=cl, clr=clr, mt=mt, dt=dt, wid=wid, hlc3=hlc3, W=W)


def _trail(lo):
    """Ratcheting stop = highest confirmed weekly down-fractal low so far (raised, never lowered)."""
    W = len(lo)
    out = np.full(W, -np.inf)
    cur = -np.inf
    for k in range(W):
        j = k - 2                                   # fractal centered at j is confirmed at k
        if j >= 2 and lo[j] < lo[j - 1] and lo[j] < lo[j - 2] and lo[j] < lo[j + 1] and lo[j] < lo[j + 2]:
            if lo[j] > cur:
                cur = lo[j]
        out[k] = cur
    return out


def _cliffs(a, b):
    b = np.sort(np.asarray(b, float))
    nb = len(b)
    if nb == 0 or len(a) == 0:
        return float("nan")
    tot = 0
    for x in a:
        lt = int(np.searchsorted(b, x, "left"))
        gt = nb - int(np.searchsorted(b, x, "right"))
        tot += lt - gt
    return tot / (len(a) * nb)


def _cost_rt(mt, stop_exit):
    half = 0.0005 if mt >= 25e7 else (0.0010 if mt >= 5e7 else 0.0020)
    return 2 * half + 0.0012 + (0.0010 if stop_exit else 0.0)


def _sim(e, cl, trail, L, W):
    """Walk weeks from entry e; exit on first of fractal-break / band-break / time censor."""
    hi = min(e + MAXHOLD, W - 1)
    for w in range(e + 1, hi + 1):
        if cl[w] < trail[w]:
            return w, "fractal"
        if cl[w] < L[w]:
            return w, "band"
    return hi, "time"


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rng = np.random.default_rng(SEED)
    d, c = index_series("Nifty 500")
    idx_d = list(d); idx_c = np.asarray(c, float)

    def idx_ret(d0, d1):
        i0 = bisect.bisect_right(idx_d, d0) - 1
        i1 = bisect.bisect_right(idx_d, d1) - 1
        if i0 < 0 or i1 < 0:
            return np.nan
        return idx_c[i1] / idx_c[i0] - 1.0

    HZ = [4, 8, 13, 26]
    ev = {h: [] for h in HZ}          # real forward excess by horizon
    ev_half = {"h1": [], "h2": []}    # 13wk excess by half
    plac13 = []                       # pooled placebo 13wk excess
    book = {}; ctrl = {}; wid2date = {}
    n_ev = 0; trades = []
    syms = eq_symbols(mc); ns = 0

    def acc(store, wids_dates_rets, cost):
        first = True
        for wd, r in wids_dates_rets:
            wid, dstr = wd
            wid2date[wid] = dstr
            rr = r - (cost if first else 0.0)
            s = store.setdefault(wid, [0.0, 0])
            s[0] += rr; s[1] += 1
            first = False

    def elig_mask(Wd):
        m = np.zeros(Wd["W"], dtype=bool)
        for k in range(WARMUP, Wd["W"]):
            if Wd["mt"][k] >= LIQ and Wd["clr"][k] >= MIN_CLOSE and np.isfinite(Wd["hlc3"][k]):
                m[k] = True
        return m

    for sym in syms:
        ns += 1
        S = load_series(mc, sym)
        if S is None or S.n < 200:
            continue
        Wd = _weekly(S)
        if Wd is None:
            continue
        W = Wd["W"]; cl = Wd["cl"]; lo = Wd["lo"]; dt = Wd["dt"]; wid = Wd["wid"]; mt = Wd["mt"]
        T = _ema(Wd["hlc3"], 5); L = _ema(lo, 13); trail = _trail(lo)
        elig = elig_mask(Wd)
        elig_weeks = np.where(elig)[0]
        if len(elig_weeks) < 20:
            continue
        last_ev = -10 ** 9; open_until = -1
        for k in range(WARMUP, W - 1):
            if not elig[k]:
                continue
            if not (T[k - 1] <= L[k - 1] and T[k] > L[k]):     # reclaim rising edge
                continue
            e = k + 1
            if dt[e] < START or e >= W:
                continue
            if k - last_ev < DEOV:
                continue
            last_ev = k
            # ---- event-study forward excess ----
            for h in HZ:
                if e + h < W:
                    fwd = cl[e + h] / cl[e] - 1.0
                    exc = fwd - idx_ret(dt[e], dt[e + h])
                    if np.isfinite(exc):
                        ev[h].append(exc)
                        if h == 13:
                            (ev_half["h1"] if dt[e] < "2019-01-01" else ev_half["h2"]).append(exc)
            # placebos (13wk): 3 random eligible + 1 time-shift
            pl_weeks = list(rng.choice(elig_weeks, size=min(3, len(elig_weeks)), replace=False))
            if k + 13 < W:
                pl_weeks.append(k + 13)
            for pk in pl_weeks:
                pe = int(pk) + 1
                if pe + 13 < W and dt[pe] >= START:
                    pex = cl[pe + 13] / cl[pe] - 1.0 - idx_ret(dt[pe], dt[pe + 13])
                    if np.isfinite(pex):
                        plac13.append(pex)
            n_ev += 1
            # ---- book (one open trade/symbol) ----
            if e <= open_until:
                continue
            x, kind = _sim(e, cl, trail, L, W)
            open_until = x
            gross = cl[x] / cl[e] - 1.0
            cost = _cost_rt(mt[k], kind != "time")
            trades.append((sym, dt[e], dt[x], x - e, kind, round(gross * 100, 2), round((gross - cost) * 100, 2)))
            path = [((int(wid[w]), dt[w]), cl[w] / cl[w - 1] - 1.0) for w in range(e + 1, x + 1)]
            if path:
                acc(book, path, cost)
                # random-entry control, same exit geometry
                ce = int(rng.choice(elig_weeks))
                if ce < W - 2:
                    cx, ck = _sim(ce, cl, trail, L, W)
                    cpath = [((int(wid[w]), dt[w]), cl[w] / cl[w - 1] - 1.0) for w in range(ce + 1, cx + 1)]
                    if cpath:
                        acc(ctrl, cpath, _cost_rt(mt[min(ce, W - 1)], ck != "time"))
        if ns % 800 == 0:
            print(f"  …{ns}/{len(syms)} symbols, {n_ev} events", flush=True)
    mc.close()

    def monthly_rv(store, lo=None, hi=None):
        if not store:
            return None
        wr = {w: store[w][0] / store[w][1] for w in store}
        mon = {}
        for w in sorted(wr):
            m = wid2date[w][:7]
            if (lo and m < lo) or (hi and m >= hi):
                continue
            mon[m] = mon.get(m, 1.0) * (1 + wr[w])
        months = sorted(mon)
        if len(months) < 12:
            return None
        r = np.array([mon[m] - 1 for m in months])
        eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
        return (round(float(r.mean() / r.std() * 12 ** .5), 2),
                round((float(eq[-1]) ** (12 / len(r)) - 1) * 100, 1), round(dd * 100, 1), len(r))

    def hz(h):
        a = np.array(ev[h], float)
        return dict(n=len(a), mean=round(float(a.mean()) * 100, 3), med=round(float(np.median(a)) * 100, 3),
                    pos=round(float((a > 0).mean()) * 100, 1)) if len(a) else dict(n=0)

    d13 = _cliffs(ev[13], plac13) if ev[13] and plac13 else float("nan")
    h1med = float(np.median(ev_half["h1"])) * 100 if ev_half["h1"] else float("nan")
    h2med = float(np.median(ev_half["h2"])) * 100 if ev_half["h2"] else float("nan")
    G1 = n_ev >= 300
    G2 = ev[13] and np.mean(ev[13]) > 0 and np.median(ev[13]) > 0
    G3 = np.isfinite(d13) and d13 >= 0.05
    G4 = np.isfinite(h1med) and np.isfinite(h2med) and h1med > 0 and h2med > 0
    gate1 = bool(G1 and G2 and G3 and G4)

    bk = monthly_rv(book); bkn = None  # net book (book already net — cost folded in acc)
    bh1 = monthly_rv(book, None, "2019"); bh2 = monthly_rv(book, "2019", None)
    ct = monthly_rv(ctrl)
    net_rv = bk[0] if bk else None
    beats_ctrl = (net_rv is not None and ct is not None and net_rv - ct[0] >= 0.15)
    fundable = bool(bh1 and bh2 and bh1[0] > 0.89 and bh2[0] > 0.89 and beats_ctrl)

    out = {
        "run_at": t0.strftime("%Y-%m-%d %H:%MZ"),
        "prediction": "CAUTIOUS-FAIL (daily reclaim was an anti-signal; weekly attacks horizon+cost)",
        "GATE1_selection": {
            "events": n_ev, "horizons": {str(h): hz(h) for h in HZ},
            "cliffs13_vs_placebo": round(d13, 4) if np.isfinite(d13) else None,
            "half1_med13%": round(h1med, 3), "half2_med13%": round(h2med, 3),
            "gates": {"G1_n300": bool(G1), "G2_mean_med_pos": bool(G2), "G3_cliffs.05": bool(G3), "G4_both_halves": bool(G4)},
            "VERDICT": "PASS" if gate1 else "FAIL-null",
        },
        "GATE2_book": {
            "net_full": bk, "net_h1": bh1, "net_h2": bh2, "random_control": ct,
            "beats_control_by>=.15": bool(beats_ctrl), "hurdle": 0.89, "FUNDABLE": fundable,
        },
        "n_trades": len(trades),
        "DISPOSITION": "NEW candidate" if (gate1 and fundable) else "REJECTED — descriptive-only",
        "weekly_vs_daily": "does WEEKLY rescue the DAILY-falsified reclaim? " + ("YES-signal" if gate1 else "NO"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "weekly_band_reclaim.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"WEEKLY_BAND_RECLAIM: {n_ev} events, {len(trades)} trades in {(datetime.now(timezone.utc)-t0).total_seconds():.0f}s")
    return out


def selftest():
    # weekly resample + reclaim detection + a stop exit on a constructed uptrend-then-break
    x = np.linspace(100, 100, 40)
    T = _ema(np.arange(40, dtype=float), 5)
    assert T[-1] > T[0], "ema rises on a rising input"
    lo = np.array([10, 9, 8, 7, 6, 8, 9, 10, 11, 12], dtype=float)  # fractal low at idx 4 (6 < neighbors)
    tr = _trail(lo)
    assert tr[6] == 6.0, "confirmed down-fractal low ratchets into the trail"
    assert _cliffs([1, 2, 3], [0, 0, 0]) == 1.0 and _cliffs([0, 0], [1, 1]) == -1.0, "cliffs sign"
    print("WEEKLY_BAND_RECLAIM selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    else:
        print(__doc__)
