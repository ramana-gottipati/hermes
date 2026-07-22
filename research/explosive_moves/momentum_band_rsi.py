"""MOMENTUM BAND + RSI — the UPPER-band breakout entry (BUY STRENGTH) + RSI/fractal managed exit.
PRE-REGISTERED 2026-07-22 (S-momentum-band-rsi). The one untested sliver of the reversal-pair arc.

WHY THIS EXISTS / WHAT IS NEW. The STREAM BAND study (ledger 2026-07-13) tested the LOWER-bank
RECLAIM — trigger reclaims EMA13(low) from below = BUY WEAKNESS — and found it an ANTI-signal
(22d excess med -1.25%, both placebos beat it; book return/vol 0.37). This study tests the OPPOSITE
edge Ramana specified as his MOMENTUM trigger: trigger crosses ABOVE the UPPER bank EMA13(high) =
BUY STRENGTH. That specific entry was never run as a signal, and RSI as the stop/exit variable was
never tested (STREAM BAND MANAGED used stream/2-fractal/two-candle stops; EXIT LAB used
%/ATR/chandelier/fractal — none used RSI). So this is a legitimate re-attempt with genuinely NEW
evidence on BOTH the entry side and the exit side.

PREDICTION ON RECORD (failure-ledger contract — stated BEFORE the run): I expect FAIL. Priors,
cited: (1) EXIT LAB 2026-07-14e — best OOS exit ~0.63-0.65 < 0.89, "exits shape losses, they cannot
mint edge"; PROFIT-TAKERS were the single WORST family (sell-at-band retvol -0.06) and Ramana's
RSI-80 partial IS a profit-take; (2) STREAM BAND MANAGED 2026-07-14d — the managed stack was -0.50
retvol, churn-killed; (3) cross-sectional momentum died 1.29->0.09 net; single-name swing
(Launchpad) failed net of cost. The purpose is to CLOSE this open question honestly with a numeric
ledger entry, not to rescue the family.

METRIC BASIS (D142): every ratio is annualised mean/sd with NO risk-free subtracted — a return/vol
ratio, not a Sharpe. The Nifty-500 buy-&-hold hurdle 0.89 is on the SAME basis. Descriptive-only,
SEBI-safe: no ranking, no buy/sell advice, whatever the verdict.

DESIGN (locked before first run; seed 42; symbols in sorted order; CA-ADJUSTED prices throughout —
the 2026-07-15O raw-price bug does NOT recur here). Universe = every EQ/CM symbol in bhavcopy_rows.
Window: signal dates >= 2012-06-01 (matches the arc). Bands U=EMA13(adj_high), L=EMA13(adj_low);
trigger T=EMA5(HLC3), HLC3=(adj_high+adj_low+adj_close)/3. Price RSI = Wilder(14) on adj_close.
2-fractal = degree-2 Williams down-fractal (low strictly < the 2 bars each side), confirmed 2 bars
later (PIT). Eligibility at signal bar i: >=260 prior rows; trailing med_turn[i] >= Rs 1cr; raw
close[i] >= 20; calendar gap <= 6d around i; band/trigger/RSI finite. De-overlap 22 bars per symbol
for EVENT counting; for the BOOK, one open trade per symbol (no pyramiding, no re-entry).

ENTRY (momentum long, PIT). MOM cross = rising edge: band-valid, T[i-1] <= U[i-1] AND T[i] > U[i]
(trigger crosses ABOVE the upper bank). Entry = CLOSE of bar i+1. Record RSI_entry = RSI[i+1] and
the initial fractal stop = latest confirmed down-fractal low as of i+1.

EXIT ENGINES (all act on the close AFTER the trigger bar; whichever stop is hit first = "tighter"):
  fractal stop  : ratcheting 2-fractal — stop = latest confirmed down-fractal low, raised (never
                  lowered) as higher down-fractals confirm; exit if adj_close < stop.
  Cell B  LOOSE (primary BOOK, no profit-take): exit on fractal stop OR RSI <= 45. No partial.
          This is the fundable-bar engine; EXIT LAB predicts the loose form is the least-bad.
  Cell A  RAMANA-LITERAL: phase-1 RSI stop = RSI_entry (exit if RSI < RSI_entry); at first RSI>=80,
          SELL HALF, drop RSI stop to 45, hold remainder; full exit on RSI<=45 or fractal. The
          RSI-80 partial's effect is measured at the TRADE-RETURN level (0.5*ret_to_80 +
          0.5*ret_to_final - costs) vs Cell A2, NOT in the daily book, to keep book weighting clean.
  Cell A2 HOLD-TILL-80: no RSI stop before the first RSI>=80 (fractal only); then partial + RSI45,
          resolving the "comfortable staying until 80" reading. Also trade-level partial overlay.
  Cell C  CONTROL (random-entry, same-exit): for each real entry, one uniform-random ELIGIBLE bar of
          the SAME symbol, run Cell-B exit + same cost. Isolates whether the MOM entry adds value
          over the exit geometry (the 2026-07-14b FENCE-2 lesson).

COST. Headline = tiered round-trip: half-spread by liquidity (>=25cr 0.05% / 5-25cr 0.10% /
1-5cr 0.20% per side) + Zerodha delivery (STT 0.10%/side + 0.02% fees) + 0.10% slippage added on
STOP-type fills only. Cross-check book at flat 0.30%/side. Book charged the FULL round-trip as a
one-time friction on the entry-day contribution (total-correct; timing immaterial over years) — the
2026-07-14b gross-book defect does NOT recur. RAW (gross) and NET books both reported => raw CAGR,
net CAGR, and the gap = trade-cost impact.

EVENT-STUDY GATE (does BUYING STRENGTH here carry forward edge? judged only on the primary MOM-BUY
cell). Excess vs Nifty-500 over 5/10/22/66 bars; controls = 3 same-symbol random-bar placebos +
one +63-bar time-shift placebo. PASS-signal requires ALL:
  G1  n >= 300 primary MOM-BUY events
  G2  mean AND median 22d excess > 0
  G3  Cliff's delta of 22d excess vs BOTH placebo sets >= +0.05
  G4  median 22d excess > 0 in BOTH halves (< / >= 2019-01-01)

BOOK GATE (fundable bar):
  G-BOOK   Cell-B NET monthly return/vol > 0.89 in BOTH halves 2012-18 / 2019-26
  G-BETTER Cell-B NET retvol beats the Cell-C random-entry control by >= +0.15 (entry adds value)

DISPOSITION (pre-committed). PASS = G-BOOK AND G-BETTER both hold -> NEW candidate, promotion still
requires fresh participation-cost + fill-realism fences (never fund off this run). ELSE -> REJECTED,
descriptive-only; ledger entry cites 07-13 / 14 / 14b / 14c / 14d / 14e. Either way the RSI-80
partial verdict (helps / hurts vs no-partial) is recorded, extending the EXIT LAB profit-taker law.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.momentum_band_rsi --build   # events+trades+books -> research.db
  ... --run        # analysis -> out/momentum_band_rsi.json + printed report + VERDICT
  ... --selftest   # offline synthetic checks (no DB)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

from .common import (LIQ_FLOOR, OUT_DIR, SymbolSeries, cliffs_delta, eq_symbols,
                     load_series, main_conn, research_conn)
from .metrics import index_series
from .streamband import ema, roll_mean, roll_std

EMA_FAST, EMA_SLOW = 5, 13
RSI_N = 14
FRAC_DEG = 2
HORIZONS = (5, 10, 22, 66)
START = "2012-06-01"
HALF_SPLIT = "2019-01-01"
WARMUP = 260
MIN_CLOSE = 20.0
MAX_GAP = 6
DEOVERLAP = 22
SHIFT = 63
SEED = 42
LIQ5 = 5e7
RSI_HOT = 80.0        # partial-profit trigger
RSI_COLD = 45.0       # full-exit level after the hot print
PARTIAL = 0.5         # fraction sold at the first RSI_HOT touch
FLAT_SIDE = 0.003     # cross-check flat cost per side
BOOK_KEYS = ("CELL_B", "CELL_A", "CELL_A2", "RANDOM_CTL",
             "CELL_B_TREND", "CELL_B_LIQ25", "CELL_B_REGIME", "CELL_B_CLEAN",
             "CELL_B_TREND_STRONG", "CELL_B_TREND_R55", "CELL_B_TREND_R60", "CELL_B_TREND_R65")


# --------------------------------------------------------------------------- #
# new causal primitives (EMA/roll_* reused from streamband)                    #
# --------------------------------------------------------------------------- #
def rsi_wilder(close: np.ndarray, n: int = RSI_N) -> np.ndarray:
    """Wilder RSI(n) on a price array, SMA-seeded then Wilder-smoothed. Causal:
    out[i] uses only close[:i+1]. NaN for i < n. Flat window -> 50; zero-loss -> 100."""
    m = len(close)
    out = np.full(m, np.nan)
    if m < n + 1:
        return out
    diff = np.diff(close)
    gain = np.where(diff > 0, diff, 0.0)
    loss = np.where(diff < 0, -diff, 0.0)
    ag = float(np.mean(gain[:n]))
    al = float(np.mean(loss[:n]))

    def _rsi(g, l):
        if l <= 0 and g <= 0:
            return 50.0
        if l <= 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + g / l)

    out[n] = _rsi(ag, al)
    for i in range(n + 1, m):
        ag = (ag * (n - 1) + gain[i - 1]) / n
        al = (al * (n - 1) + loss[i - 1]) / n
        out[i] = _rsi(ag, al)
    return out


def latest_down_fractal(low: np.ndarray, deg: int = FRAC_DEG) -> np.ndarray:
    """out[t] = low of the most recent degree-`deg` down-fractal CONFIRMED on or before bar t
    (a fractal at f — low[f] strictly < the deg bars each side — is knowable only at f+deg).
    Causal forward-fill; NaN until the first confirmation."""
    m = len(low)
    out = np.full(m, np.nan)
    cur = np.nan
    events = {}                      # confirmation_bar -> fractal_low
    for f in range(deg, m - deg):
        lf = low[f]
        if np.isnan(lf):
            continue
        left = low[f - deg:f]
        right = low[f + 1:f + deg + 1]
        if lf < np.nanmin(left) and lf < np.nanmin(right):
            events[f + deg] = lf     # confirmed at f+deg
    for t in range(m):
        if t in events:
            cur = events[t]
        out[t] = cur
    return out


def _cost_rt(med_turn: float, stop_exit: bool) -> float:
    """Round-trip fraction: tiered half-spread (both sides) + Zerodha delivery + stop slippage."""
    if med_turn >= 25e7:
        hs = 0.0005
    elif med_turn >= LIQ5:
        hs = 0.0010
    else:
        hs = 0.0020
    rt = 2.0 * hs + 0.0020 + 0.0002          # 2x half-spread + STT 0.1%/side + 0.02% fees
    if stop_exit:
        rt += 0.0010                          # slippage on stop-type fills
    return rt


# --------------------------------------------------------------------------- #
# index helper (Nifty 500) — slim, mirrors streamband._Idx                     #
# --------------------------------------------------------------------------- #
class _Idx:
    def __init__(self):
        d, c = index_series("Nifty 500")
        if not d or d[0] > START:
            raise SystemExit(f"index_rows Nifty 500 starts {d[0] if d else 'EMPTY'} > {START}")
        self.pos = {x: i for i, x in enumerate(d)}
        self.dates, self.close = d, np.asarray(c, float)
        self.sma = roll_mean(self.close, 200)

    def up(self, d: str) -> bool:
        """Is the Nifty-500 above its own 200-day SMA as of date d? (market-regime filter)."""
        import bisect
        i = self.pos.get(d)
        if i is None:
            i = bisect.bisect_right(self.dates, d) - 1
        if i < 0 or i >= len(self.close) or np.isnan(self.sma[i]):
            return False
        return bool(self.close[i] > self.sma[i])

    def ret(self, d0: str, d1: str) -> float:
        import bisect
        i = self.pos.get(d0)
        j = self.pos.get(d1)
        if i is None:
            i = bisect.bisect_right(self.dates, d0) - 1
        if j is None:
            j = bisect.bisect_right(self.dates, d1) - 1
        if i < 0 or j < 0 or j <= i:
            return np.nan
        return float(self.close[j] / self.close[i] - 1.0)


def _fwd(S: SymbolSeries, i: int, idx: _Idx):
    """(raw, excess) forward returns for an entry at the close of i+1."""
    e = i + 1
    raw, exc = {}, {}
    p0 = S.adj_close[e]
    for h in HORIZONS:
        j = e + h
        if j <= S.n - 1 and p0 > 0 and S.adj_close[j] > 0:
            r = float(S.adj_close[j] / p0 - 1.0)
            raw[h] = r
            ir = idx.ret(S.date[e], S.date[j])
            exc[h] = r - ir if not np.isnan(ir) else np.nan
        else:
            raw[h] = exc[h] = np.nan
    return raw, exc


# --------------------------------------------------------------------------- #
# trade simulation (managed exit)                                              #
# --------------------------------------------------------------------------- #
def _simulate(S, e, U, L, T, R, dfrac, okband, cell):
    """Return dict with exit index, exit_kind, gross return to FINAL exit, the RSI-80 partial
    index (or -1), and whether the position ever scaled. `cell` in {'B','A','A2'}.
    All decisions use data through bar j; the position acts at the close of j+1."""
    n = S.n
    rsi_entry = R[e]
    stop = dfrac[e] if not np.isnan(dfrac[e]) else -np.inf
    hot_done = False
    partial_idx = -1
    exit_j, kind = n - 1, "censored"
    for j in range(e + 1, n):
        if not okband[j] or np.isnan(R[j]):
            continue
        # ratchet the fractal stop up
        if not np.isnan(dfrac[j]) and dfrac[j] > stop:
            stop = dfrac[j]
        # partial profit at first RSI_HOT (cells A / A2 only)
        if cell in ("A", "A2") and not hot_done and R[j] >= RSI_HOT:
            hot_done = True
            partial_idx = min(j + 1, n - 1)
        # RSI stop level depends on cell + phase
        if cell == "A":
            rsi_floor = RSI_COLD if hot_done else rsi_entry
        elif cell == "A2":
            rsi_floor = RSI_COLD if hot_done else -np.inf
        else:                                   # Cell B
            rsi_floor = RSI_COLD
        rsi_hit = R[j] < rsi_floor
        frac_hit = S.adj_close[j] < stop
        if rsi_hit or frac_hit:
            exit_j = min(j + 1, n - 1)
            kind = "frac_stop" if frac_hit and not rsi_hit else (
                "rsi45" if hot_done or cell == "B" else "rsi_p1")
            break
    p0 = S.adj_close[e]
    gross = float(S.adj_close[exit_j] / p0 - 1.0) if p0 > 0 and S.adj_close[exit_j] > 0 else np.nan
    gross_to_partial = np.nan
    if partial_idx > 0 and S.adj_close[partial_idx] > 0 and p0 > 0:
        gross_to_partial = float(S.adj_close[partial_idx] / p0 - 1.0)
    return {"exit_j": exit_j, "kind": kind, "gross": gross,
            "partial_idx": partial_idx, "gross_partial": gross_to_partial,
            "scaled": partial_idx > 0}


# --------------------------------------------------------------------------- #
# build                                                                        #
# --------------------------------------------------------------------------- #
_DDL = """
DROP TABLE IF EXISTS mbr_events;
CREATE TABLE mbr_events(
  kind TEXT, symbol TEXT, sig_date TEXT, entry_date TEXT, med_turn REAL, close_raw REAL,
  vol66 REAL, rsi_entry REAL, trend INT,
  fx5 REAL, fx10 REAL, fx22 REAL, fx66 REAL, fr5 REAL, fr10 REAL, fr22 REAL, fr66 REAL);
DROP TABLE IF EXISTS mbr_trades;
CREATE TABLE mbr_trades(
  cell TEXT, symbol TEXT, entry_date TEXT, exit_date TEXT, hold INT, med_turn REAL,
  rsi_entry REAL, trend INT, scaled INT, exit_kind TEXT,
  gross REAL, net_full REAL, net_partial REAL, cost_rt REAL);
DROP TABLE IF EXISTS mbr_book;
CREATE TABLE mbr_book(key TEXT, gross_net TEXT, month TEXT, mret REAL, avg_pos REAL);
"""


def _accum_book(book, key, gnet, e, exit_j, S, cost_rt):
    """Daily equal-weight contributions for one trade: entry-day = -cost (net only);
    days e+1..exit = price returns."""
    if gnet == "net":
        book[(key, "net")].setdefault(S.date[e], [0.0, 0])
        cell = book[(key, "net")][S.date[e]]
        cell[0] += -cost_rt
        cell[1] += 1
    for k in range(e + 1, exit_j + 1):
        if S.adj_close[k] > 0 and S.adj_close[k - 1] > 0:
            r = float(S.adj_close[k] / S.adj_close[k - 1] - 1.0)
            c = book[(key, gnet)].setdefault(S.date[k], [0.0, 0])
            c[0] += r
            c[1] += 1


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript(_DDL)
    idx = _Idx()
    rng = np.random.default_rng(SEED)
    syms = eq_symbols(mc)

    ev_rows, tr_rows = [], []
    # book[(key, gross|net)] -> {date: [sum_ret, n]}
    book = {(k, g): {} for k in BOOK_KEYS for g in ("gross", "net")}
    n_sym = n_used = 0

    for sym in syms:
        n_sym += 1
        S = load_series(mc, sym)
        if S is None or S.n < 300:
            continue
        n_used += 1
        d64 = np.array(S.date, dtype="datetime64[D]")
        gap_prev = np.full(S.n, 999)
        gap_prev[1:] = (d64[1:] - d64[:-1]) / np.timedelta64(1, "D")
        gap_next = np.full(S.n, 999)
        gap_next[:-1] = gap_prev[1:]

        tp3 = (S.adj_high + S.adj_low + S.adj_close) / 3.0
        U = ema(S.adj_high, EMA_SLOW)
        L = ema(S.adj_low, EMA_SLOW)
        T = ema(tp3, EMA_FAST)
        R = rsi_wilder(S.adj_close, RSI_N)
        dfrac = latest_down_fractal(S.adj_low, FRAC_DEG)
        sma200 = roll_mean(S.adj_close, 200)
        vol66 = roll_std(S.ret_raw, 66)
        okband = ~(np.isnan(T) | np.isnan(U) | np.isnan(L))

        ii = np.arange(S.n)
        base_elig = ((ii >= WARMUP) & (gap_prev <= MAX_GAP) & (gap_next <= MAX_GAP)
                     & (S.med_turn >= LIQ_FLOOR) & (S.close >= MIN_CLOSE)
                     & (np.array(S.date) >= START))
        can22 = np.zeros(S.n, dtype=bool)
        lim = S.n - 1 - 23
        if lim > 0:
            can22[:lim] = True

        # MOM cross = rising edge T over U
        mom = np.zeros(S.n, dtype=bool)
        for i in range(1, S.n):
            if okband[i] and okband[i - 1] and T[i - 1] <= U[i - 1] and T[i] > U[i]:
                mom[i] = True
        hits = np.where(mom)[0]

        plc_pool = np.where(base_elig & can22 & okband & ~np.isnan(R))[0]
        last_ev = -10**9
        open_until = {c: -1 for c in ("B", "A", "A2")}

        for i in hits:
            if not base_elig[i] or i + 1 >= S.n or np.isnan(R[i + 1]):
                continue
            if i - last_ev < DEOVERLAP:
                continue
            last_ev = i
            trend = int(not np.isnan(sma200[i]) and S.adj_close[i] > sma200[i])
            raw, exc = _fwd(S, i, idx)
            ev_rows.append(("event", sym, S.date[i], S.date[i + 1], float(S.med_turn[i]),
                            float(S.close[i]), float(vol66[i]) if not np.isnan(vol66[i]) else None,
                            float(R[i + 1]), trend,
                            exc[5], exc[10], exc[22], exc[66], raw[5], raw[10], raw[22], raw[66]))
            # placebos
            if len(plc_pool) >= 4:
                for p in rng.choice(plc_pool, size=3, replace=False):
                    p = int(p)
                    rw, ex = _fwd(S, p, idx)
                    ev_rows.append(("plc_sym", sym, S.date[p], S.date[p + 1], float(S.med_turn[p]),
                                    float(S.close[p]), None, float(R[p]) if not np.isnan(R[p]) else None,
                                    0, ex[5], ex[10], ex[22], ex[66], rw[5], rw[10], rw[22], rw[66]))
            p = i + SHIFT
            if p < S.n - 1 and base_elig[p] and can22[p] and not np.isnan(R[p]):
                rw, ex = _fwd(S, p, idx)
                ev_rows.append(("plc_shift", sym, S.date[p], S.date[p + 1], float(S.med_turn[p]),
                                float(S.close[p]), None, float(R[p]), 0,
                                ex[5], ex[10], ex[22], ex[66], rw[5], rw[10], rw[22], rw[66]))

            e = i + 1
            # --- managed trades, one open per symbol per cell ---
            for cell in ("B", "A", "A2"):
                if i + 1 <= open_until[cell]:
                    continue
                sim = _simulate(S, e, U, L, T, R, dfrac, okband, cell)
                if sim["exit_j"] <= e or S.adj_close[e] <= 0 or S.adj_close[sim["exit_j"]] <= 0:
                    continue
                open_until[cell] = sim["exit_j"]
                stop_exit = sim["kind"] in ("frac_stop", "rsi45", "rsi_p1")
                crt = _cost_rt(float(S.med_turn[i]), stop_exit)
                gross = sim["gross"]
                net_full = gross - crt
                if sim["scaled"] and not np.isnan(sim["gross_partial"]):
                    # half sold at RSI80, half at final exit; cost on both legs (~crt total)
                    net_partial = (PARTIAL * sim["gross_partial"]
                                   + (1 - PARTIAL) * gross - crt)
                else:
                    net_partial = net_full
                tr_rows.append((cell, sym, S.date[e], S.date[sim["exit_j"]], int(sim["exit_j"] - e),
                                float(S.med_turn[i]), float(R[e]), trend, int(sim["scaled"]),
                                sim["kind"], gross, net_full, net_partial, crt))
                bkey = {"B": "CELL_B", "A": "CELL_A", "A2": "CELL_A2"}[cell]
                _accum_book(book, bkey, "gross", e, sim["exit_j"], S, crt)
                _accum_book(book, bkey, "net", e, sim["exit_j"], S, crt)
                if cell == "B":
                    segs = []
                    liq25 = S.med_turn[i] >= 25e7
                    reg = idx.up(S.date[e])
                    strong = not np.isnan(R[e]) and R[e] >= 70.0
                    if trend:
                        segs.append("CELL_B_TREND")
                    if trend and strong:
                        segs.append("CELL_B_TREND_STRONG")
                    if trend and not np.isnan(R[e]):
                        if R[e] >= 55.0:
                            segs.append("CELL_B_TREND_R55")
                        if R[e] >= 60.0:
                            segs.append("CELL_B_TREND_R60")
                        if R[e] >= 65.0:
                            segs.append("CELL_B_TREND_R65")
                    if liq25:
                        segs.append("CELL_B_LIQ25")
                    if reg:
                        segs.append("CELL_B_REGIME")
                    if trend and liq25 and reg:
                        segs.append("CELL_B_CLEAN")
                    for sk in segs:
                        _accum_book(book, sk, "gross", e, sim["exit_j"], S, crt)
                        _accum_book(book, sk, "net", e, sim["exit_j"], S, crt)

            # --- random-entry control (same-symbol eligible bar, Cell-B exit) ---
            if len(plc_pool) >= 1:
                rp = int(rng.choice(plc_pool))
                if rp + 1 < S.n and okband[rp + 1] and not np.isnan(R[rp + 1]):
                    ce = rp + 1
                    sc = _simulate(S, ce, U, L, T, R, dfrac, okband, "B")
                    if sc["exit_j"] > ce and S.adj_close[ce] > 0 and S.adj_close[sc["exit_j"]] > 0:
                        crt = _cost_rt(float(S.med_turn[rp]), sc["kind"] != "censored")
                        _accum_book(book, "RANDOM_CTL", "gross", ce, sc["exit_j"], S, crt)
                        _accum_book(book, "RANDOM_CTL", "net", ce, sc["exit_j"], S, crt)

        if n_sym % 400 == 0:
            print(f"  …{n_sym}/{len(syms)} symbols, events="
                  f"{sum(1 for r in ev_rows if r[0]=='event')}, trades={len(tr_rows)}", flush=True)

    rc.executemany("INSERT INTO mbr_events VALUES (" + ",".join("?" * 17) + ")", ev_rows)
    rc.executemany("INSERT INTO mbr_trades VALUES (" + ",".join("?" * 14) + ")", tr_rows)

    brows = []
    for (key, gnet), days in book.items():
        if not days:
            continue
        months = {}
        for dte in sorted(days):
            s, c = days[dte]
            if c > 0:
                months.setdefault(dte[:7], []).append((s / c, c))
        for m in sorted(months):
            rs = months[m]
            mret = float(np.prod([1 + r for r, _ in rs]) - 1)
            brows.append((key, gnet, m, mret, float(np.mean([c for _, c in rs]))))
    rc.executemany("INSERT INTO mbr_book VALUES (?,?,?,?,?)", brows)
    rc.commit()
    rc.close()
    mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"BUILD done: {n_used}/{n_sym} symbols, "
          f"{sum(1 for r in ev_rows if r[0]=='event')} MOM events, {len(tr_rows)} trades, "
          f"{len(brows)} book rows in {dt:.0f}s")


# --------------------------------------------------------------------------- #
# run (analysis)                                                               #
# --------------------------------------------------------------------------- #
def _arr(rows, col):
    return np.array([r[col] if r[col] is not None else np.nan for r in rows], dtype=float)


def _cell(ev):
    x = _arr(ev, "fx22")
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "mean22": round(float(np.mean(x)) * 100, 3),
            "med22": round(float(np.median(x)) * 100, 3),
            "pos%": round(float(np.mean(x > 0)) * 100, 1)}


def _stats_monthly(mr):
    mr = np.asarray(mr, float)
    if len(mr) < 6:
        return None
    eq = np.cumprod(1 + mr)
    peak = np.maximum.accumulate(eq)
    dd = float((eq / peak - 1).min())
    sd = mr.std()
    return {"retvol": round(float(mr.mean() / sd * np.sqrt(12)), 2) if sd > 0 else 0.0,
            "cagr%": round((float(eq[-1]) ** (12 / len(mr)) - 1) * 100, 1),
            "maxdd%": round(dd * 100, 1), "months": int(len(mr))}


def _book_stats(bk, key, gnet):
    rows = [r for r in bk if r["key"] == key and r["gross_net"] == gnet and r["month"] >= "2012-06"]
    mr = [r["mret"] for r in rows]
    return {"full": _stats_monthly(mr),
            "h1_2012_18": _stats_monthly([r["mret"] for r in rows if r["month"] < "2019"]),
            "h2_2019_26": _stats_monthly([r["mret"] for r in rows if r["month"] >= "2019"]),
            "avg_pos": round(float(np.mean([r["avg_pos"] for r in rows])), 1) if rows else None}


def run():
    rc = research_conn()
    ev = rc.execute("SELECT * FROM mbr_events").fetchall()
    tr = rc.execute("SELECT * FROM mbr_trades").fetchall()
    bk = rc.execute("SELECT * FROM mbr_book").fetchall()
    rc.close()

    out = {"registered_gate": "see module docstring (prereg registry: momentum_band_rsi)",
           "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "prediction": "FAIL expected (see docstring priors)"}

    prim = [r for r in ev if r["kind"] == "event"]
    psym = [r for r in ev if r["kind"] == "plc_sym"]
    pshf = [r for r in ev if r["kind"] == "plc_shift"]

    x = _arr(prim, "fx22"); xs = x[~np.isnan(x)]
    a = _arr(psym, "fx22"); b = _arr(pshf, "fx22")
    d_sym = cliffs_delta(xs, a[~np.isnan(a)]) if len(xs) else float("nan")
    d_shf = cliffs_delta(xs, b[~np.isnan(b)]) if len(xs) else float("nan")
    h1 = np.array([r["fx22"] for r in prim if r["sig_date"] < HALF_SPLIT and r["fx22"] is not None], float)
    h2 = np.array([r["fx22"] for r in prim if r["sig_date"] >= HALF_SPLIT and r["fx22"] is not None], float)

    g1 = len(prim) >= 300
    g2 = len(xs) > 0 and float(np.mean(xs)) > 0 and float(np.median(xs)) > 0
    g3 = (not np.isnan(d_sym) and d_sym >= 0.05) and (not np.isnan(d_shf) and d_shf >= 0.05)
    g4 = len(h1) > 0 and len(h2) > 0 and np.median(h1) > 0 and np.median(h2) > 0
    ev_verdict = "PASS-signal" if (g1 and g2 and g3 and g4) else "FAIL-null"

    horiz = {}
    for h in HORIZONS:
        v = _arr(prim, f"fx{h}"); v = v[~np.isnan(v)]
        if len(v):
            horiz[f"{h}d"] = {"n": int(len(v)), "mean%": round(float(np.mean(v)) * 100, 3),
                              "med%": round(float(np.median(v)) * 100, 3),
                              "pos%": round(float(np.mean(v > 0)) * 100, 1)}

    out["EVENT_primary"] = {
        "cell": _cell(prim), "horizons": horiz,
        "placebo_sym": _cell(psym), "placebo_shift": _cell(pshf),
        "cliffs_vs_sym": round(float(d_sym), 4) if not np.isnan(d_sym) else None,
        "cliffs_vs_shift": round(float(d_shf), 4) if not np.isnan(d_shf) else None,
        "half1_med22%": round(float(np.median(h1)) * 100, 3) if len(h1) else None,
        "half2_med22%": round(float(np.median(h2)) * 100, 3) if len(h2) else None,
        "gates": {"G1_n300": bool(g1), "G2_mean_med_pos": bool(g2),
                  "G3_cliffs_.05_both": bool(g3), "G4_both_halves": bool(g4)},
        "VERDICT": ev_verdict}

    # trades per cell
    tcells = {}
    for cell in ("B", "A", "A2"):
        rows = [t for t in tr if t["cell"] == cell]
        if not rows:
            continue
        nf = np.array([t["net_full"] for t in rows], float)
        npart = np.array([t["net_partial"] for t in rows], float)
        gr = np.array([t["gross"] for t in rows], float)
        tcells[cell] = {
            "n": len(rows),
            "success%(net_full>0)": round(float(np.mean(nf > 0)) * 100, 1),
            "mean_gross%": round(float(np.mean(gr)) * 100, 2),
            "mean_net_full%": round(float(np.mean(nf)) * 100, 2),
            "med_net_full%": round(float(np.median(nf)) * 100, 2),
            "mean_net_partial%": round(float(np.mean(npart)) * 100, 2),
            "med_net_partial%": round(float(np.median(npart)) * 100, 2),
            "avg_hold": round(float(np.mean([t["hold"] for t in rows])), 1),
            "scaled%": round(float(np.mean([t["scaled"] for t in rows])) * 100, 1),
            "avg_cost_rt%": round(float(np.mean([t["cost_rt"] for t in rows])) * 100, 3),
            "stop_hit_mix": {k: int(sum(1 for t in rows if t["exit_kind"] == k))
                             for k in ("frac_stop", "rsi45", "rsi_p1", "censored")}}
    out["TRADES_by_cell"] = tcells
    if "A2" in tcells:
        out["RSI80_partial_effect"] = {
            "note": "median net WITH the RSI-80 partial minus WITHOUT (Cell A2). EXIT LAB predicts <=0.",
            "delta_med_net%": round(tcells["A2"]["med_net_partial%"] - tcells["A2"]["med_net_full%"], 3),
            "delta_mean_net%": round(tcells["A2"]["mean_net_partial%"] - tcells["A2"]["mean_net_full%"], 3)}

    # books
    cb_net = _book_stats(bk, "CELL_B", "net")
    cb_gross = _book_stats(bk, "CELL_B", "gross")
    ctl_net = _book_stats(bk, "RANDOM_CTL", "net")
    out["BOOK_cellB_net"] = cb_net
    out["BOOK_cellB_gross(raw)"] = cb_gross
    out["BOOK_cellA2_net"] = _book_stats(bk, "CELL_A2", "net")
    out["BOOK_cellA2_gross(raw)"] = _book_stats(bk, "CELL_A2", "gross")
    out["BOOK_cellA_net"] = _book_stats(bk, "CELL_A", "net")
    out["BOOK_random_control_net"] = ctl_net
    out["BOOK_segments_net"] = {k: _book_stats(bk, k, "net")["full"]
                                for k in ("CELL_B_TREND", "CELL_B_TREND_R55", "CELL_B_TREND_R60", "CELL_B_TREND_R65", "CELL_B_TREND_STRONG", "CELL_B_LIQ25", "CELL_B_REGIME", "CELL_B_CLEAN")
                                if _book_stats(bk, k, "net")["full"]}
    out["CAGR_raw_vs_net"] = {
        "raw_cagr%": cb_gross["full"]["cagr%"] if cb_gross["full"] else None,
        "net_cagr%": cb_net["full"]["cagr%"] if cb_net["full"] else None,
        "cost_impact_cagr_pp": (round(cb_gross["full"]["cagr%"] - cb_net["full"]["cagr%"], 1)
                                if cb_gross["full"] and cb_net["full"] else None)}

    h1n = cb_net["h1_2012_18"]; h2n = cb_net["h2_2019_26"]
    g_book = bool(h1n and h2n and h1n["retvol"] > 0.89 and h2n["retvol"] > 0.89)
    g_better = bool(cb_net["full"] and ctl_net["full"]
                    and (cb_net["full"]["retvol"] - ctl_net["full"]["retvol"]) >= 0.15)
    book_verdict = "PASS-book" if (g_book and g_better) else "FAIL"
    out["BOOK_gates"] = {
        "G_BOOK_0.89_both_halves": g_book,
        "G_BETTER_vs_random_+0.15": g_better,
        "cellB_net_retvol_full": cb_net["full"]["retvol"] if cb_net["full"] else None,
        "random_net_retvol_full": ctl_net["full"]["retvol"] if ctl_net["full"] else None,
        "VERDICT": book_verdict}

    overall = "PASS" if (book_verdict == "PASS-book") else "REJECTED (descriptive-only)"
    out["OVERALL_VERDICT"] = overall

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "momentum_band_rsi.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\n=== EVENT: {ev_verdict} | BOOK: {book_verdict} | OVERALL: {overall} ===")
    return out


# --------------------------------------------------------------------------- #
# selftest (offline)                                                           #
# --------------------------------------------------------------------------- #
def selftest():
    # RSI: a strict uptrend -> 100; strict downtrend -> low; matches a hand computation
    up = np.arange(1, 60, dtype=float)
    r = rsi_wilder(up, 14)
    assert np.isnan(r[13]) and not np.isnan(r[14]), "RSI first valid at index n"
    assert r[20] > 99.9, "monotone rise -> RSI ~100"
    dn = np.arange(60, 1, -1, dtype=float)
    assert rsi_wilder(dn, 14)[20] < 0.1, "monotone fall -> RSI ~0"
    # causality: truncating the future never changes the past
    rng = np.random.default_rng(0)
    x = np.cumsum(rng.normal(0, 1, 300)) + 100
    full = rsi_wilder(x, 14); cut = rsi_wilder(x[:200], 14)
    assert np.allclose(full[:200], cut, equal_nan=True), "RSI must be causal"

    # down-fractal: a clean V has its trough confirmed 2 bars later, forward-filled
    low = np.array([10, 9, 8, 5, 8, 9, 10, 11, 12, 13], float)  # trough at idx 3
    df = latest_down_fractal(low, 2)
    assert np.isnan(df[4]) and df[5] == 5.0, "trough(idx3) confirmed at idx5"
    assert df[9] == 5.0, "stop forward-fills until a newer fractal"

    # cost monotonic: thinner names + stop fills cost more
    assert _cost_rt(1e6, True) > _cost_rt(30e7, False)

    # simulate: a pure uptrend never stops out (censored), gross > 0
    n = 80
    S = type("S", (), {})()
    S.n = n
    S.date = [f"2020-01-{d:02d}" for d in range(1, n + 1)]  # dummy
    price = np.linspace(100, 200, n)
    S.adj_close = price.copy()
    T = np.full(n, 1.0); U = np.full(n, 0.0); L = np.full(n, -1.0)  # T always above U
    R = np.full(n, 60.0)                                            # never hot, never cold
    dfrac = np.full(n, np.nan)
    okband = np.ones(n, bool)
    sim = _simulate(S, 5, U, L, T, R, dfrac, okband, "B")
    assert sim["kind"] == "censored" and sim["gross"] > 0, "uptrend, no stop -> censored gain"
    print("MOMENTUM_BAND_RSI selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
