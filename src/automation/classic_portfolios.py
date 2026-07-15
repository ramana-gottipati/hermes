"""Classic portfolios — the famous public strategies as NAMED, BACKDATABLE model portfolios.

Ramana's ask (S146): the Classic Screens must be PORTFOLIOS, not a snapshot screen — named,
runnable with a backdate ("what was my portfolio in January 2020?"), with charts and a
per-year track record so "which portfolio was outstanding, and when" is answerable.

WHY A SIBLING MODULE (not an edit to auto_portfolios.py): that file is the S132h/S132i lane's
engine for the four ADMITTED books (STEADY/PACER/SPRINTER/CRAFTSMAN, eligibility = superior
measured Sharpe AND beats the Nifty hurdle). The classics do NOT clear that bar — most FAIL it —
so they must not be silently promoted into that estate. This module REUSES its engine helpers
verbatim (identical clock, ₹5cr gate, band-35 churn, equal-weight 1/25, flat per-side cost, NAV
vs Nifty-500 normalised at inception) and writes its OWN isolated tables, so the two estates stay
distinct and the recorded eligibility rule is not rewritten by the back door.

THE MISSING PIECE THIS ADDS: `auto_portfolios.build_panel` carries PRICE/DELIVERY features only
(mom6, mom12, vol66, med_turn, px, deliv-trend) — there are NO fundamentals in it, which is why
Magic Formula / Coffee Can / GARP / Graham / Piotroski / QMJ could never be backdated. Here we
build a POINT-IN-TIME FUNDAMENTALS PANEL the documented efficient way (fundamentals_asof:
"load the frame ONCE and call as_of_from_frame() for every rebalance date"), so every classic
rule is evaluated with only what was knowable on that rebalance date — no look-ahead.

HONESTY: this reconstructs what each PUBLIC rule would have produced on our data. It is a
backtest, not a track record of money, and the value books are expected to look BAD (the ledger
records deep value HARD-REJECTED: alpha negative, beta 1.54, MaxDD -82%). We publish the curve
the engine measures, good or bad — that comparison IS the analysis. Descriptive, not advice.

Owns `classic_portfolio_holdings` + `classic_portfolio_nav` (no db.py edit). Pure stdlib. CLI:
  python -m src.automation.classic_portfolios --backfill   # full 2012-06 -> today rebuild
  python -m src.automation.classic_portfolios --refresh    # extend when a clock turns
  python -m src.automation.classic_portfolios --selftest
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
    from src.automation.auto_portfolios import (
        BAND, COST_SIDE, CR, HISTORY_FROM, START, TOPN,
        apply_band, build_panel, rebalance_dates, _bench_map,
    )
    from src.automation.slow_rotation import pctrank
    from src.automation.fundamentals_asof import (
        RESEARCH_DB, _hermes_ro, as_of_from_frame, load_symbol_history,
    )
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore
    from automation.auto_portfolios import (  # type: ignore
        BAND, COST_SIDE, CR, HISTORY_FROM, START, TOPN,
        apply_band, build_panel, rebalance_dates, _bench_map,
    )
    from automation.slow_rotation import pctrank  # type: ignore
    from automation.fundamentals_asof import (  # type: ignore
        RESEARCH_DB, _hermes_ro, as_of_from_frame, load_symbol_history,
    )

# name -> (score, clock, gate, label, fidelity note)
# Clocks match each rule's real cadence: value/quality books are slow (Q), CANSLIM is a
# momentum rule (M). Gate/band/cost are the engine's, unchanged.
CLASSIC_SPECS = {
    "MAGIC-25":     {"score": "magic",      "clock": "Q", "gate": "cr5"},
    "COFFEECAN-25": {"score": "coffeecan",  "clock": "Q", "gate": "cr5"},
    "GARP-25":      {"score": "garp",       "clock": "Q", "gate": "cr5"},
    "GRAHAM-25":    {"score": "graham",     "clock": "Q", "gate": "cr5"},
    "QMJ-25":       {"score": "qmj",        "clock": "Q", "gate": "cr5"},
    "PIOTROSKI-25": {"score": "piotroski",  "clock": "Q", "gate": "cr5"},
    "CANSLIM-25":   {"score": "canslim",    "clock": "M", "gate": "cr5"},
    "LOWVOL-25":    {"score": "purelowvol", "clock": "Q", "gate": "cr5"},
}

# Display metadata for the view (name -> (title, author, one-line rule, fidelity)).
CLASSIC_META = {
    "MAGIC-25":     ("Magic Formula", "Joel Greenblatt",
                     "combined rank of high return-on-capital + high earnings yield", "proxy"),
    "COFFEECAN-25": ("Coffee Can", "Saurabh Mukherjea",
                     "3y-avg ROCE >=15% and 5y sales CAGR >=10%", "full"),
    "GARP-25":      ("GARP (PEG)", "Peter Lynch",
                     "lowest PEG among quality names", "full"),
    "GRAHAM-25":    ("Graham Deep Value", "Benjamin Graham",
                     "cheapest on P/E and P/B", "proxy"),
    "QMJ-25":       ("Quality (QMJ)", "AQR / Buffett-Munger",
                     "high ROCE + high margin + low leverage", "full"),
    "PIOTROSKI-25": ("Piotroski F-Score", "Joseph Piotroski",
                     "financial-strength score (5 of 9 signals computable)", "proxy"),
    "CANSLIM-25":   ("CANSLIM", "William O'Neil",
                     "earnings acceleration + market leadership", "proxy"),
    "LOWVOL-25":    ("Low-Volatility", "Haugen / min-variance",
                     "the 25 lowest-realised-volatility liquid names", "full"),
}

# which specs need the (expensive) fundamentals panel
_PRICE_ONLY = {"purelowvol"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS classic_portfolio_holdings (
    portfolio  TEXT,
    rebal_date TEXT,
    symbol     TEXT,
    rank       INTEGER,
    score      REAL,
    weight     REAL,
    px         REAL,
    PRIMARY KEY(portfolio, rebal_date, symbol)
);
CREATE TABLE IF NOT EXISTS classic_portfolio_nav (
    portfolio  TEXT,
    rebal_date TEXT,
    nav        REAL,
    bench_nav  REAL,
    n_churned  INTEGER,
    computed_at TEXT,
    PRIMARY KEY(portfolio, rebal_date)
);
CREATE INDEX IF NOT EXISTS idx_classic_nav_p ON classic_portfolio_nav(portfolio, rebal_date);
"""

# fundamentals keys pulled from the as-of dict (kept small — this is 2k syms x ~90 dates)
_FKEYS = ("roce", "roce_3y_avg", "roce_rising_3y", "pe", "pb", "debt_to_equity",
          "opm_latest", "opm_trend_3y", "sales_growth_5y", "profit_growth_3y",
          "profit_growth_ttm", "interest_coverage")


# ── the missing piece: a POINT-IN-TIME fundamentals panel ────────────────────
def build_fund_panel(conn, rebal_all, px_at, *, db_path: str = RESEARCH_DB, limit=None):
    """{rebal_date: {symbol: {fundamental keys}}} with NO look-ahead.

    The documented efficient path (fundamentals_asof): load each symbol's history frame ONCE,
    then evaluate as_of_from_frame() at every rebalance date. Price comes from the engine's
    ADJUSTED px_at panel so PE/PB are point-in-time consistent with the NAV math.
    """
    syms = [r[0] for r in conn.execute(
        "SELECT symbol FROM nse_equity_list ORDER BY symbol")]
    if limit:
        syms = syms[:limit]
    panel = {d: {} for d in rebal_all}
    hconn = _hermes_ro()
    n_done = n_hit = 0
    try:
        for sym in syms:
            try:
                frame = load_symbol_history(sym, db_path=db_path, hconn=hconn)
            except Exception:  # noqa: BLE001 - one bad symbol never kills the panel
                frame = None
            n_done += 1
            if not frame:
                continue
            for d in rebal_all:
                px = px_at.get(d, {}).get(sym)
                try:
                    f = as_of_from_frame(frame, d, symbol=sym, price=px)
                except Exception:  # noqa: BLE001
                    f = None
                if not f:
                    continue
                panel[d][sym] = {k: f.get(k) for k in _FKEYS}
                n_hit += 1
            if n_done % 250 == 0:
                print(f"  …fund panel {n_done}/{len(syms)} symbols "
                      f"({n_hit} sym-dates)", flush=True)
    finally:
        if hconn is not None:
            hconn.close()
    return panel


# ── scoring ──────────────────────────────────────────────────────────────────
def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _gate(pfeats, spec):
    """The engine's liquidity gate, verbatim (med_turn is index 3)."""
    if spec["gate"] == "cr5":
        return {s: f for s, f in pfeats.items() if f[3] >= 5 * CR}
    turns = sorted(f[3] for f in pfeats.values())
    if not turns:
        return {}
    cut = turns[int(0.80 * (len(turns) - 1))]
    return {s: f for s, f in pfeats.items() if f[3] >= cut}


def _blend(syms, series_list):
    """Mean of per-component percentile ranks -> [(sym, score)]."""
    prs = [pctrank(vals) for vals in series_list]
    return [(s, sum(pr[i] for pr in prs) / len(prs)) for i, s in enumerate(syms)]


def rank_classic(pfeats, ffeats, spec):
    """(price panel, fundamentals panel, spec) -> ranked [(sym, score)] desc.

    Mirrors auto_portfolios.rank_family: same gate, same "need a real pool" guard.
    """
    pool = _gate(pfeats, spec)
    if len(pool) < TOPN + 5:
        return []
    score = spec["score"]

    if score == "purelowvol":                      # price-only: lowest realised vol
        syms = list(pool)
        scored = [(s, -pool[s][2]) for s in syms]
        scored.sort(key=lambda x: -x[1])
        return scored

    # every other classic needs fundamentals known AT this rebalance
    cand = [s for s in pool if s in ffeats]
    if len(cand) < TOPN + 5:
        return []

    def f(s, k):
        return _num(ffeats[s].get(k))

    if score == "magic":                            # ROC (ROCE) + earnings yield (E/P proxy)
        syms = [s for s in cand if f(s, "roce") is not None
                and f(s, "pe") is not None and f(s, "pe") > 0]
        if len(syms) < TOPN + 5:
            return []
        scored = _blend(syms, [[f(s, "roce") for s in syms],
                               [1.0 / f(s, "pe") for s in syms]])
    elif score == "coffeecan":                      # ROCE>=15 (3y avg + latest) & 5y sales>=10
        syms = [s for s in cand
                if (f(s, "roce_3y_avg") or -9) >= 15 and (f(s, "roce") or -9) >= 15
                and (f(s, "sales_growth_5y") or -9) >= 10]
        if len(syms) < TOPN + 5:
            return []
        scored = _blend(syms, [[f(s, "roce_3y_avg") for s in syms],
                               [f(s, "sales_growth_5y") for s in syms]])
    elif score == "garp":                           # lowest PEG among quality names
        syms = [s for s in cand
                if f(s, "pe") is not None and f(s, "pe") > 0
                and (f(s, "profit_growth_3y") or 0) > 0 and (f(s, "roce") or -9) >= 12
                and 0 < f(s, "pe") / f(s, "profit_growth_3y") <= 2]
        if len(syms) < TOPN + 5:
            return []
        scored = [(s, -(f(s, "pe") / f(s, "profit_growth_3y"))) for s in syms]
    elif score == "graham":                         # cheapest P/E and P/B (Graham's caps)
        syms = [s for s in cand
                if f(s, "pe") is not None and 0 < f(s, "pe") <= 15
                and f(s, "pb") is not None and 0 < f(s, "pb") <= 1.5]
        if len(syms) < TOPN + 5:
            return []
        scored = _blend(syms, [[-f(s, "pe") for s in syms], [-f(s, "pb") for s in syms]])
    elif score == "qmj":                            # ROCE + margin + low leverage
        syms = [s for s in cand if f(s, "roce_3y_avg") is not None
                and f(s, "roce_3y_avg") >= 12 and f(s, "debt_to_equity") is not None
                and f(s, "opm_latest") is not None]
        if len(syms) < TOPN + 5:
            return []
        scored = _blend(syms, [[f(s, "roce_3y_avg") for s in syms],
                               [-f(s, "debt_to_equity") for s in syms],
                               [f(s, "opm_latest") for s in syms]])
    elif score == "piotroski":                      # F5 of 9 (cash-flow trio not computable)
        syms, f5 = [], {}
        for s in cand:
            roce = f(s, "roce")
            if roce is None:
                continue
            n = 0
            n += 1 if (f(s, "profit_growth_ttm") or 0) > 0 else 0
            n += 1 if roce > 0 else 0
            n += 1 if ffeats[s].get("roce_rising_3y") else 0
            n += 1 if (f(s, "opm_trend_3y") or 0) > 0 else 0
            n += 1 if (f(s, "interest_coverage") or 0) >= 3 else 0
            if n >= 4:
                syms.append(s)
                f5[s] = n + min(roce, 99) / 1000.0
        if len(syms) < TOPN + 5:
            return []
        scored = [(s, f5[s]) for s in syms]
    elif score == "canslim":                        # earnings acceleration + leadership (mom12)
        syms = [s for s in cand
                if (f(s, "profit_growth_ttm") or -9) >= 25
                and (f(s, "profit_growth_3y") or -9) >= 20]
        if len(syms) < TOPN + 5:
            return []
        scored = [(s, pool[s][1]) for s in syms]    # rank leaders by 12-mo momentum
    else:
        return []

    scored.sort(key=lambda x: -x[1])
    return scored


# ── construct (mirrors auto_portfolios._construct exactly) ───────────────────
def _construct(conn, panel, fpanel, px_at, dates_by_clock):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    bench = _bench_map(conn)
    conn.execute("DELETE FROM classic_portfolio_holdings")
    conn.execute("DELETE FROM classic_portfolio_nav")
    for pname, spec in CLASSIC_SPECS.items():
        dates = [d for d in dates_by_clock[spec["clock"]] if d in panel and panel[d]]
        members, nav, b0 = [], 1.0, None
        for k, d in enumerate(dates):
            ranked = rank_classic(panel[d], fpanel.get(d, {}), spec)
            if not ranked:
                continue
            new_members = apply_band(ranked, members)
            churned = (len(set(new_members) - set(members))
                       + len(set(members) - set(new_members))) if members else 0
            order = {s: i + 1 for i, (s, _sc) in enumerate(ranked)}
            scores = dict(ranked)
            if members and k > 0:
                dp = dates[k - 1]
                rs = []
                for s in members:
                    p0, p1 = px_at.get(dp, {}).get(s), px_at.get(d, {}).get(s)
                    if p0 and p1:
                        rs.append(p1 / p0 - 1.0)
                gross = sum(rs) / len(rs) if rs else 0.0
                cost = COST_SIDE * churned / TOPN
                nav *= (1.0 + gross - cost)
            if b0 is None:
                b0 = bench.get(d)
            bnav = (bench.get(d) / b0) if (b0 and bench.get(d)) else None
            conn.execute("INSERT OR REPLACE INTO classic_portfolio_nav VALUES (?,?,?,?,?,?)",
                         (pname, d, round(nav, 4),
                          round(bnav, 4) if bnav else None, churned, now))
            conn.executemany(
                "INSERT OR REPLACE INTO classic_portfolio_holdings VALUES (?,?,?,?,?,?,?)",
                [(pname, d, s, order.get(s), round(float(scores.get(s, 0)), 4),
                  round(1.0 / TOPN, 4), px_at[d].get(s)) for s in new_members])
            members = new_members
        print(f"  built {pname}: {len(dates)} rebalances", flush=True)
    conn.commit()


def backfill(conn=None, *, limit=None) -> str:
    if conn is None:
        with get_conn() as c:
            return backfill(c, limit=limit)
    conn.executescript(SCHEMA)
    days = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? "
        "AND series='EQ' ORDER BY trade_date", (START,))]
    if not days:
        return "no bhavcopy history on this host"
    dates_by_clock = {"M": rebalance_dates(days, "M"), "Q": rebalance_dates(days, "Q")}
    all_dates = sorted(set(dates_by_clock["M"]) | set(dates_by_clock["Q"]))
    print(f"classic backfill: {len(all_dates)} rebalance dates "
          f"{all_dates[0]} -> {all_dates[-1]}", flush=True)
    panel, px_at = build_panel(conn, all_dates)
    print(f"price panel built ({len(panel)} dates)", flush=True)
    fpanel = build_fund_panel(conn, all_dates, px_at, limit=limit)
    print("fundamentals panel built", flush=True)
    _construct(conn, panel, fpanel, px_at, dates_by_clock)
    n = conn.execute("SELECT COUNT(*) c FROM classic_portfolio_nav").fetchone()["c"]
    return f"backfilled {n} classic portfolio-rebalances since {START}"


def refresh(conn=None) -> str:
    """Extend only when a clock turned (the full rebuild is the backfill)."""
    if conn is None:
        with get_conn() as c:
            return refresh(c)
    conn.executescript(SCHEMA)
    try:
        have = conn.execute("SELECT MAX(rebal_date) d FROM classic_portfolio_nav").fetchone()["d"]
    except sqlite3.OperationalError:
        have = None
    if not have:
        return "no classic history yet — run --backfill once"
    days = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? "
        "AND series='EQ' ORDER BY trade_date", (START,))]
    latest_m = rebalance_dates(days, "M")[-1] if days else None
    if latest_m and latest_m <= have:
        return f"classic portfolios current ({have})"
    return backfill(conn)


# ── selftest (pure logic, no DB) ─────────────────────────────────────────────
def _synth(n=80):
    """A universe wide enough that every classic clears the engine's TOPN+5 pool floor —
    deliberately n=80 with a wide value spread, because Graham's P/E<=15 AND P/B<=1.5 caps
    admit only the cheapest ~third (that floor is the engine's, and it bites in real data too:
    a book that cannot fill 25 names simply skips that rebalance)."""
    p, f = {}, {}
    for i in range(1, n + 1):
        s = f"S{i}"
        # (mom6, mom12, vol66, med_turn, px, dtr)
        p[s] = (0.01 * i, 0.02 * i, 0.40 - 0.004 * i, 10 * CR, 100.0 + i, 1.0)
        f[s] = {"roce": 8 + 0.5 * i, "roce_3y_avg": 8 + 0.5 * i, "roce_rising_3y": i % 2 == 0,
                "pe": 35 - 0.4 * i, "pb": 3.0 - 0.03 * i, "debt_to_equity": 2.0 - 0.02 * i,
                "opm_latest": 10 + 0.3 * i, "opm_trend_3y": 0.2 * (i - 30),
                "sales_growth_5y": 5 + 0.4 * i, "profit_growth_3y": 10 + 0.5 * i,
                "profit_growth_ttm": 15 + 0.5 * i, "interest_coverage": 1 + 0.3 * i}
    return p, f


def selftest():
    p, f = _synth()
    for name, spec in CLASSIC_SPECS.items():
        ranked = rank_classic(p, f, spec)
        assert ranked, f"{name} produced no ranking"
        assert len(ranked) >= TOPN, (name, len(ranked))
        scores = [sc for _s, sc in ranked]
        assert scores == sorted(scores, reverse=True), f"{name} not sorted desc"
        members = apply_band(ranked, [])
        assert len(members) == TOPN, (name, len(members))
    # pure low-vol must pick the LOWEST realised vol (S80 = 0.40-0.32 = 0.08)
    assert rank_classic(p, f, CLASSIC_SPECS["LOWVOL-25"])[0][0] == "S80"
    # graham only admits the genuinely cheap (PE<=15 and PB<=1.5)
    gr = rank_classic(p, f, CLASSIC_SPECS["GRAHAM-25"])
    assert all(f[s]["pe"] <= 15 and f[s]["pb"] <= 1.5 for s, _ in gr)
    # an illiquid universe is gated out entirely
    thin = {s: (v[0], v[1], v[2], 1 * CR, v[4], v[5]) for s, v in p.items()}
    assert rank_classic(thin, f, CLASSIC_SPECS["MAGIC-25"]) == []
    # no fundamentals known -> only the price-only book still ranks
    assert rank_classic(p, {}, CLASSIC_SPECS["MAGIC-25"]) == []
    assert rank_classic(p, {}, CLASSIC_SPECS["LOWVOL-25"])
    print("CLASSIC_PORTFOLIOS selftest OK —",
          {k: len(rank_classic(p, f, s)) for k, s in CLASSIC_SPECS.items()})


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--backfill" in sys.argv:
        lim = None
        if "--limit" in sys.argv:
            lim = int(sys.argv[sys.argv.index("--limit") + 1])
        print("classic_portfolios:", backfill(limit=lim))
    elif "--refresh" in sys.argv:
        print("classic_portfolios:", refresh())
    else:
        print(__doc__)
