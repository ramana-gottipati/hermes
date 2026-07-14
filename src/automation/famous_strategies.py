"""Classic Screens — the famous public equity strategies, run on OUR data (descriptive).

Ramana's ask (S145): the "name-brand" strategies every serious desk respects — Greenblatt's
Magic Formula, O'Neil's CANSLIM, Piotroski's F-Score, Mukherjea's Coffee Can, Lynch's GARP,
Graham deep value, Quality/QMJ, Low-Volatility — made CONCRETE as runnable screens over the
NSE universe, each producing a live top-25 roster the analyst can actually inspect.

This is the SIBLING of factor_league.py (which ranks the raw factor FAMILIES). This module
implements the named, multi-signal STRATEGIES: each strategy is a public, citable rule, and we
run our closest faithful expression of it against the point-in-time data we actually hold.

DATA (all read at refresh; nothing new collected):
  momentum_scan (nightly)            -> universe + mom6/mom12, vol_66, range_pos_252, turnover_cr
  fundamentals_asof.as_of_fundamentals -> PIT ROCE, PE, PB, D/E, OPM, sales/profit growth, eps_ttm
  bhavcopy_rows.close (latest)       -> price, so PE/PB/earnings-yield are computable
Universe = latest momentum_scan with turnover >= Rs5cr (factor_league's liquid gate) — bounded,
so the per-symbol PIT fundamentals loop stays a few-hundred-name nightly job.

COMPUTABILITY (honest — some famous rules need data we do not yet hold PIT):
  FULL   : Low-Volatility, Quality/QMJ, Coffee Can, CANSLIM, GARP
  PROXY  : Magic Formula  (E/P substituted for Greenblatt's EBIT/EV yield — no PIT enterprise value)
           Piotroski      (F5 of 9 — the cash-flow trio needs the XBRL cash-flow feed, phase 2)
           Graham value   (P/B + P/E; current-ratio leg missing) — shown WITH the deep-value
                          failure numbers from the ledger (this family FAILED on our data)
  NONE   : Acquirer's Multiple (EV/EBIT) — needs PIT enterprise value; reference-only until phase 2
The proxy substitutions are LABELED wherever shown; the roster is a research shortlist, never a
buy list. DESCRIPTIVE-ONLY (docs/strategy-ledger.md doctrine): value strategies especially are
presented next to what they ACTUALLY delivered on 14y of NSE data (deep value = HARD-REJECTED,
alpha negative, beta 1.54, MaxDD -82%). Not advice, SEBI-safe.

Owns the isolated table `classic_roster` (no db.py edit). Pure stdlib. CLI:
  python -m src.automation.famous_strategies --refresh
  python -m src.automation.famous_strategies --selftest
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
    from src.automation.slow_rotation import pctrank
    from src.automation.fundamentals_asof import as_of_fundamentals
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore
    from automation.slow_rotation import pctrank  # type: ignore
    from automation.fundamentals_asof import as_of_fundamentals  # type: ignore

TOPN = 25
MIN_TURN_CR = 5.0            # factor_league's recorded liquid universe

# strategy key -> (display name, author/school, one-line rule AS WE RUN IT, computability)
# computability: full | proxy | none   (drives the honesty label in the view)
STRATEGIES = {
    "lowvol":    ("Low-Volatility", "Haugen / min-variance",
                  "the 25 lowest-realised-volatility liquid names", "full"),
    "quality":   ("Quality (QMJ)", "AQR / Buffett-Munger",
                  "high ROCE + high margin + low leverage, percentile-blended", "full"),
    "coffeecan": ("Coffee Can", "Saurabh Mukherjea / Marcellus",
                  "ROCE >=15% (3y) and 5y sales growth >=10% — the clean compounders", "full"),
    "canslim":   ("CANSLIM", "William O'Neil",
                  "strong earnings acceleration + near a 52w high + market leadership (RS)", "full"),
    "garp":      ("GARP (PEG)", "Peter Lynch",
                  "lowest PEG (PE / 3y earnings growth) among quality names", "full"),
    "magic":     ("Magic Formula", "Joel Greenblatt",
                  "combined rank of high return-on-capital + high earnings yield (E/P proxy)", "proxy"),
    "piotroski": ("Piotroski F-Score", "Joseph Piotroski",
                  "financial-strength score — 5 of the 9 signals computable today", "proxy"),
    "graham":    ("Graham Deep Value", "Benjamin Graham",
                  "low P/E and low P/B — shown WITH what deep value did on our data", "proxy"),
    "acquirers": ("Acquirer's Multiple", "Tobias Carlisle",
                  "cheapest EV/EBIT — needs PIT enterprise value (phase 2)", "none"),
}
# the strategies that produce a live roster (acquirers is reference-only until EV lands)
RUNNABLE = tuple(k for k, v in STRATEGIES.items() if v[3] != "none")

SCHEMA = """
CREATE TABLE IF NOT EXISTS classic_roster (
    strategy    TEXT,
    symbol      TEXT,
    rank        INTEGER,
    score       REAL,
    detail_json TEXT,      -- the handful of display metrics for this pick
    as_of       TEXT,
    computed_at TEXT,
    PRIMARY KEY(strategy, symbol)
);
CREATE INDEX IF NOT EXISTS idx_classic_roster_strategy
    ON classic_roster(strategy, rank);
"""


# --- helpers ---------------------------------------------------------------

def _num(v):
    """Coerce to float or None (sqlite can hand back None / stray types)."""
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _rank(scored):
    """scored: [(symbol, goodness, detail)] with HIGHER goodness = better ->
    [(symbol, rank, goodness, detail), ...] top-TOPN, ties broken by symbol."""
    scored = [s for s in scored if s[1] is not None]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return [(sym, i + 1, round(float(g), 5), det)
            for i, (sym, g, det) in enumerate(scored[:TOPN])]


def _pct_map(rows, key, *, invert=False):
    """{symbol: percentile in [0,1]} over rows that have a numeric `key`
    (invert=True ranks SMALLER-is-better, e.g. cheap PE, low debt)."""
    e = [(r["symbol"], _num(r.get(key))) for r in rows]
    e = [(s, v) for s, v in e if v is not None]
    if not e:
        return {}
    vals = [(-v if invert else v) for _s, v in e]
    pr = pctrank(vals)
    return {s: pr[i] for i, (s, _v) in enumerate(e)}


# --- the scorers (pure; each returns [(symbol, goodness, detail_dict)]) ----
# goodness is always "higher = better" so _rank() is uniform.

def _score_lowvol(rows):
    out = []
    for r in rows:
        vol = _num(r.get("vol_66"))
        if vol is None:
            continue
        out.append((r["symbol"], -vol, {"vol": vol, "mom12": _num(r.get("mom12")),
                                        "range52": _num(r.get("range_pos_252"))}))
    return out


def _score_quality(rows):
    e = [r for r in rows if _num(r.get("roce_3y_avg")) is not None
         and _num(r["roce_3y_avg"]) >= 12 and _num(r.get("debt_to_equity")) is not None]
    if not e:
        return []
    p_roce = _pct_map(e, "roce_3y_avg")
    p_de = _pct_map(e, "debt_to_equity", invert=True)
    p_opm = _pct_map(e, "opm_latest")
    out = []
    for r in e:
        s = r["symbol"]
        comps = [p_roce.get(s), p_de.get(s), p_opm.get(s)]
        comps = [c for c in comps if c is not None]
        if not comps:
            continue
        out.append((s, sum(comps) / len(comps),
                    {"roce_avg": _num(r["roce_3y_avg"]), "de": _num(r["debt_to_equity"]),
                     "opm": _num(r.get("opm_latest"))}))
    return out


def _score_coffeecan(rows):
    e = [r for r in rows
         if _num(r.get("roce_3y_avg")) is not None and _num(r["roce_3y_avg"]) >= 15
         and _num(r.get("roce")) is not None and _num(r["roce"]) >= 15
         and _num(r.get("sales_growth_5y")) is not None and _num(r["sales_growth_5y"]) >= 10]
    if not e:
        return []
    p_roce = _pct_map(e, "roce_3y_avg")
    p_sg = _pct_map(e, "sales_growth_5y")
    out = []
    for r in e:
        s = r["symbol"]
        out.append((s, (p_roce.get(s, 0) + p_sg.get(s, 0)) / 2.0,
                    {"roce_avg": _num(r["roce_3y_avg"]), "roce": _num(r["roce"]),
                     "sales_g5y": _num(r["sales_growth_5y"]),
                     "rising": bool(r.get("roce_rising_3y"))}))
    return out


def _score_canslim(rows):
    out = []
    for r in rows:
        pg_ttm = _num(r.get("profit_growth_ttm"))
        pg_3y = _num(r.get("profit_growth_3y"))
        rng = _num(r.get("range_pos_252"))
        mom12 = _num(r.get("mom12"))
        if None in (pg_ttm, pg_3y, rng, mom12):
            continue
        if pg_ttm >= 25 and pg_3y >= 20 and rng >= 0.85:
            out.append((r["symbol"], mom12,
                        {"pg_ttm": pg_ttm, "pg_3y": pg_3y, "range52": rng, "mom12": mom12,
                         "fii_up": bool(r.get("fii_rising_4q"))}))
    return out


def _score_garp(rows):
    out = []
    for r in rows:
        pe = _num(r.get("pe"))
        pg = _num(r.get("profit_growth_3y"))
        roce = _num(r.get("roce"))
        if pe is None or pg is None or roce is None:
            continue
        if pe <= 0 or pg <= 0 or roce < 12:
            continue
        peg = pe / pg
        if 0 < peg <= 2:
            out.append((r["symbol"], -peg,
                        {"pe": pe, "pg_3y": pg, "peg": peg, "roce": roce}))
    return out


def _score_magic(rows):
    e = []
    for r in rows:
        pe = _num(r.get("pe"))
        roce = _num(r.get("roce"))
        if pe is None or pe <= 0 or roce is None:
            continue
        r = dict(r)
        r["_ey"] = 1.0 / pe          # earnings yield = eps_ttm / price = 1/PE (E/P proxy)
        e.append(r)
    if not e:
        return []
    p_roce = _pct_map(e, "roce")
    p_ey = _pct_map(e, "_ey")
    out = []
    for r in e:
        s = r["symbol"]
        out.append((s, (p_roce.get(s, 0) + p_ey.get(s, 0)) / 2.0,
                    {"roce": _num(r["roce"]), "pe": _num(r["pe"]), "ey": r["_ey"] * 100.0}))
    return out


def _score_piotroski(rows):
    out = []
    for r in rows:
        roce = _num(r.get("roce"))
        if roce is None:
            continue
        pg_ttm = _num(r.get("profit_growth_ttm"))
        opm_tr = _num(r.get("opm_trend_3y"))
        icov = _num(r.get("interest_coverage"))
        f = 0
        f += 1 if (pg_ttm is not None and pg_ttm > 0) else 0    # profitability improving (dNI>0)
        f += 1 if roce > 0 else 0                               # return positive (ROA>0 proxy)
        f += 1 if r.get("roce_rising_3y") else 0                # dROCE>0 (dROA proxy)
        f += 1 if (opm_tr is not None and opm_tr > 0) else 0    # margin improving
        f += 1 if (icov is not None and icov >= 3) else 0       # leverage safe (dLeverage proxy)
        if f >= 4:
            out.append((r["symbol"], f + min(roce, 99) / 1000.0,   # roce as a gentle tiebreak
                        {"f5": f, "roce": roce, "pg_ttm": pg_ttm}))
    return out


def _score_graham(rows):
    e = [r for r in rows if _num(r.get("pe")) is not None and _num(r["pe"]) > 0
         and _num(r["pe"]) <= 15 and _num(r.get("pb")) is not None
         and _num(r["pb"]) > 0 and _num(r["pb"]) <= 1.5]
    if not e:
        return []
    p_pe = _pct_map(e, "pe", invert=True)
    p_pb = _pct_map(e, "pb", invert=True)
    out = []
    for r in e:
        s = r["symbol"]
        out.append((s, (p_pe.get(s, 0) + p_pb.get(s, 0)) / 2.0,
                    {"pe": _num(r["pe"]), "pb": _num(r["pb"])}))
    return out


_SCORERS = {
    "lowvol": _score_lowvol, "quality": _score_quality, "coffeecan": _score_coffeecan,
    "canslim": _score_canslim, "garp": _score_garp, "magic": _score_magic,
    "piotroski": _score_piotroski, "graham": _score_graham,
}


def score_all(rows):
    """rows: list of merged dicts (momentum_scan fields + as_of_fundamentals fields) ->
    {strategy: [(symbol, rank, score, detail), ...top-25]}. Pure — no IO."""
    return {k: _rank(fn(rows)) for k, fn in _SCORERS.items()}


# --- IO / refresh ----------------------------------------------------------

def _universe(conn, as_of):
    """momentum_scan liquid rows for `as_of` -> {symbol: {momentum fields}}."""
    out = {}
    for r in conn.execute(
        "SELECT symbol, mom6, mom12, vol_66, riskadj, range_pos_252, turnover_cr "
        "FROM momentum_scan WHERE as_of=?", (as_of,)):
        d = dict(r)
        if _num(d.get("turnover_cr")) is not None and d["turnover_cr"] >= MIN_TURN_CR:
            out[d["symbol"]] = d
    return out


def _latest_closes(conn):
    """{symbol: close} at the latest bhav date — the price for PE/PB/earnings-yield."""
    out = {}
    try:
        row = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
        td = row["d"] if row else None
        if td:
            for r in conn.execute(
                "SELECT symbol, close FROM bhavcopy_rows WHERE trade_date=? AND series='EQ'",
                (td,)):
                c = _num(r["close"])
                if c is not None:
                    out[r["symbol"]] = c
    except Exception:  # noqa: BLE001 - price is optional; PE/PB just go None
        pass
    return out


def _merge_rows(conn, universe, closes, as_of):
    """Merge the momentum universe with each symbol's PIT fundamentals as-of `as_of`."""
    rows = []
    for sym, mom in universe.items():
        rec = dict(mom)
        try:
            f = as_of_fundamentals(sym, as_of, price=closes.get(sym))
        except Exception:  # noqa: BLE001 - a bad symbol never kills the whole scan
            f = None
        if f:
            for k in ("roce", "roce_3y_avg", "roce_rising_3y", "opm_latest", "opm_trend_3y",
                      "debt_to_equity", "interest_coverage", "pe", "pb", "eps_ttm",
                      "sales_growth_5y", "profit_growth_3y", "profit_growth_ttm",
                      "fii_rising_4q"):
                rec[k] = f.get(k)
        rows.append(rec)
    return rows


def refresh(conn=None) -> str:
    if conn is None:
        with get_conn() as c:
            return refresh(c)
    conn.executescript(SCHEMA)
    try:
        row = conn.execute("SELECT MAX(as_of) d FROM momentum_scan").fetchone()
    except sqlite3.OperationalError:
        return "no momentum_scan table (nightly source absent on this host)"
    as_of = row["d"] if row else None
    if not as_of:
        return "no momentum_scan data"
    prev = conn.execute("SELECT MAX(as_of) d FROM classic_roster").fetchone()
    if prev and prev["d"] == as_of:
        return f"rosters already current for {as_of}"
    universe = _universe(conn, as_of)
    if not universe:
        return f"no liquid universe for {as_of}"
    closes = _latest_closes(conn)
    rows = _merge_rows(conn, universe, closes, as_of)
    rosters = score_all(rows)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    for strat, picks in rosters.items():
        conn.execute("DELETE FROM classic_roster WHERE strategy=?", (strat,))
        conn.executemany(
            "INSERT OR REPLACE INTO classic_roster VALUES (?,?,?,?,?,?,?)",
            [(strat, sym, rk, sc, json.dumps(det), as_of, now)
             for sym, rk, sc, det in picks])
    conn.commit()
    return (f"classic rosters refreshed for {as_of} ({len(universe)} liquid names): "
            + ", ".join(f"{k}={len(v)}" for k, v in rosters.items()))


# --- selftest --------------------------------------------------------------

def _synthetic():
    """A universe exercising every scorer's gate (no DB)."""
    rows = []
    for i in range(1, 41):
        rows.append({
            "symbol": f"S{i}", "mom6": 0.01 * i, "mom12": 0.02 * i, "vol_66": 0.30 - 0.005 * i,
            "riskadj": float(i), "range_pos_252": min(0.5 + 0.02 * i, 1.0), "turnover_cr": 20.0,
            "roce": 8 + 0.6 * i, "roce_3y_avg": 8 + 0.5 * i, "roce_rising_3y": i % 2 == 0,
            "opm_latest": 10 + 0.4 * i, "opm_trend_3y": 0.2 * (i - 20),
            "debt_to_equity": 2.0 - 0.04 * i, "interest_coverage": 1.0 + 0.3 * i,
            "pe": 40 - 0.7 * i, "pb": 3.0 - 0.06 * i, "eps_ttm": 10.0,
            "sales_growth_5y": 5 + 0.5 * i, "profit_growth_3y": 10 + 0.6 * i,
            "profit_growth_ttm": 15 + 0.5 * i, "fii_rising_4q": i % 3 == 0,
        })
    return rows


def selftest():
    rows = _synthetic()
    ros = score_all(rows)
    assert set(ros) == set(RUNNABLE), (set(ros), set(RUNNABLE))
    for k, picks in ros.items():
        assert len(picks) <= TOPN, k
        ranks = [p[1] for p in picks]
        assert ranks == list(range(1, len(picks) + 1)), (k, ranks)
        assert all(isinstance(p[3], dict) for p in picks), k
    # low-vol: S1 has the highest vol (0.295), S40 the lowest -> S40 must rank #1
    assert ros["lowvol"][0][0] == "S40", ros["lowvol"][0]
    # graham: only genuinely cheap names (PE<=15 AND PB<=1.5) qualify -> a bounded set
    assert all(p[3]["pe"] <= 15 and p[3]["pb"] <= 1.5 for p in ros["graham"])
    # coffee can: every pick clears BOTH the ROCE>=15 and 5y-sales>=10 floors
    assert all(p[3]["roce"] >= 15 and p[3]["sales_g5y"] >= 10 for p in ros["coffeecan"])
    # piotroski: every pick scored F5 >= 4
    assert all(p[3]["f5"] >= 4 for p in ros["piotroski"])
    # canslim: every pick is near a high and had strong growth
    assert all(p[3]["range52"] >= 0.85 and p[3]["pg_ttm"] >= 25 for p in ros["canslim"])
    # garp: PEG within (0,2]
    assert all(0 < p[3]["peg"] <= 2 for p in ros["garp"])
    # empty universe degrades to empty rosters, never raises
    assert all(v == [] for v in score_all([]).values())
    print("FAMOUS_STRATEGIES selftest OK — rosters:",
          {k: len(v) for k, v in ros.items()})


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--refresh" in sys.argv:
        print("famous_strategies:", refresh())
    else:
        print(__doc__)
