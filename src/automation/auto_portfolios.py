"""Auto portfolios — system-managed model portfolios with FULL history since 2012-06-01.

Ramana's spec (S132h): each eligible strategy runs as a NAMED, fully AUTOMATED model
portfolio — churned by its own rule continuously, no manual adds/removes possible
(there is no write UI; this module is the only writer) — created now but RECONSTRUCTED
from 2012-06-01 (the validated walk-forward window start) by running the identical rule through history, so each carries a real
track record and any past composition can be inspected ("as of Jan 2020").

ELIGIBILITY (his rule): only families with superior measured Sharpe that beat the
NIFTY hurdle on our 14y record (ledger Tier-1). Four qualify and run:

  STEADY-25   LOWVOL_MOM · QUARTERLY clock · top-turnover-QUINTILE gate   (net champion)
  PACER-25    RISKADJ    · MONTHLY clock   · ₹5cr median-turnover gate    (gross lens)
  SPRINTER-25 MOM12      · MONTHLY clock   · ₹5cr median-turnover gate    (gross lens)
  CRAFTSMAN-25 QUAL_MOM  · MONTHLY clock   · ₹5cr gate (riskadj+deliv+lowvol) (gross lens)

MECHANICS (identical to the recorded backtests): at each clock date rank the gated
universe by the family score; keep existing members while ranked ≤ BAND(35); refill to
TOPN(25) from the top ("enters the top 25 → churned in"); EQUAL WEIGHT 1/25 re-set at
every rebalance (the validated weighting — weights are engine-controlled, drift shown
on read). NAV = compounded mean member return between clock dates, FLAT 0.3%/side on
the churned fraction (labeled; PACER/SPRINTER remain gross lenses net of participation
reality — the page says so). Benchmark NAV = Nifty 500 on the same dates.

Tables (bounded): auto_portfolio_holdings (one row per member per rebalance,
~90 rebalances × 25 × 3) · auto_portfolio_nav (one row per portfolio per rebalance).
Churn is DERIVED on read from consecutive snapshots (compute-on-read rule).
Prices are corporate-action adjusted via the production adjuster. Pure stdlib.

CLI:
  python -m src.automation.auto_portfolios --backfill   # full 2012->today rebuild
  python -m src.automation.auto_portfolios --refresh    # extend if a clock turned
  python -m src.automation.auto_portfolios --selftest
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
    from src.automation import adjust as _adjust
    from src.automation.slow_rotation import pctrank
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore
    from automation import adjust as _adjust  # type: ignore
    from automation.slow_rotation import pctrank  # type: ignore

START = "2012-06-01"          # the VALIDATED walk-forward window start (S132i)
HISTORY_FROM = "2010-06-01"          # warmup runway for 252-bar features at START
TOPN, BAND = 25, 35
COST_SIDE = 0.003
CR = 1e7

SPECS = {
    "STEADY-25":    {"score": "lowvol",  "clock": "Q", "gate": "quintile"},
    "PACER-25":     {"score": "riskadj", "clock": "M", "gate": "cr5"},
    "SPRINTER-25":  {"score": "mom12",   "clock": "M", "gate": "cr5"},
    # QUAL_MOM (S132i): 0.4 pr(riskadj) + 0.3 pr(deliv_qty_trend) + 0.3 pr(-vol) —
    # the recorded 1.10-Sharpe blend with the gentlest fast-clock drawdowns (-26.7%).
    "CRAFTSMAN-25": {"score": "qualmom", "clock": "M", "gate": "cr5"},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS auto_portfolio_holdings (
    portfolio  TEXT,
    rebal_date TEXT,
    symbol     TEXT,
    rank       INTEGER,
    score      REAL,
    weight     REAL,      -- engine-controlled target weight (equal 1/25)
    px         REAL,      -- adjusted close at the rebalance (for drift on read)
    PRIMARY KEY(portfolio, rebal_date, symbol)
);
CREATE TABLE IF NOT EXISTS auto_portfolio_nav (
    portfolio  TEXT,
    rebal_date TEXT,
    nav        REAL,      -- 1.0 at inception, net of flat churn cost
    bench_nav  REAL,      -- Nifty 500 normalized to the same inception
    n_churned  INTEGER,   -- members swapped at this rebalance
    computed_at TEXT,
    PRIMARY KEY(portfolio, rebal_date)
);
"""


# ── clock ─────────────────────────────────────────────────────────────────────
def rebalance_dates(trading_days, clock):
    """First trading day of each month (M) / quarter (Q), from START onward."""
    out, seen = [], set()
    for d in trading_days:
        if d < START:
            continue
        y, m = d[:4], int(d[5:7])
        key = (y, m) if clock == "M" else (y, (m - 1) // 3)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


# ── per-rebalance feature panel ───────────────────────────────────────────────
def build_panel(conn, rebal_all):
    """{rebal_date: {symbol: (mom6, mom12, vol66, med_turn, px)}} — one pass/symbol."""
    cal = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? "
        "AND series='EQ' ORDER BY trade_date", (HISTORY_FROM,))]
    pos = {d: i for i, d in enumerate(cal)}
    ridx = [(d, pos[d]) for d in rebal_all if d in pos]
    panel = {d: {} for d, _ in ridx}
    px_at = {d: {} for d, _ in ridx}
    try:
        from src.automation.corp_actions import price_ratios
    except Exception:  # noqa: BLE001
        price_ratios = None
    syms = [r[0] for r in conn.execute("SELECT symbol FROM nse_equity_list ORDER BY symbol")]
    n_done = 0
    for sym in syms:
        rows = conn.execute(
            "SELECT trade_date, close, prev_close, value, deliv_qty FROM bhavcopy_rows "
            "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
            "AND trade_date>=? ORDER BY trade_date", (sym, HISTORY_FROM)).fetchall()
        if len(rows) < 300:
            continue
        events = None
        if price_ratios is not None:
            try:
                events = price_ratios(conn, sym)
            except Exception:  # noqa: BLE001
                events = None
        dict_rows = [{"trade_date": r["trade_date"], "close": r["close"],
                      "prev_close": r["prev_close"]} for r in rows]
        try:
            fac = _adjust.adjustment_factors(dict_rows, events)
        except Exception:  # noqa: BLE001
            fac = [1.0] * len(rows)
        d2i = {r["trade_date"]: i for i, r in enumerate(rows)}
        ac = [float(r["close"]) * f if r["close"] else None
              for r, f in zip(rows, fac)]
        val = [float(r["value"]) if r["value"] else 0.0 for r in rows]
        dq = [float(r["deliv_qty"]) if r["deliv_qty"] else None for r in rows]
        rets = [None] * len(rows)
        for i in range(1, len(rows)):
            if ac[i] and ac[i - 1]:
                rets[i] = ac[i] / ac[i - 1] - 1.0
        for d, _gi in ridx:
            i = d2i.get(d)
            if i is None or i < 252 or not ac[i]:
                continue
            if not (ac[i - 126] and ac[i - 252]):
                continue
            window = [r for r in rets[i - 66:i] if r is not None]
            if len(window) < 50:
                continue
            mu = sum(window) / len(window)
            var = sum((x - mu) ** 2 for x in window) / len(window)
            vol = var ** 0.5
            if vol <= 0:
                continue
            turn = sorted(val[max(0, i - 22):i])
            med_turn = turn[len(turn) // 2] if turn else 0.0
            # deliv_qty_trend, embase-exact: mean(dq[i-21..i]) / mean(dq[i-65..i])
            d22 = [x for x in dq[max(0, i - 21):i + 1] if x is not None]
            d66 = [x for x in dq[max(0, i - 65):i + 1] if x is not None]
            dtr = ((sum(d22) / len(d22)) / (sum(d66) / len(d66))
                   if d22 and d66 and sum(d66) > 0 else None)
            panel[d][sym] = (ac[i] / ac[i - 126] - 1.0, ac[i] / ac[i - 252] - 1.0,
                             vol, med_turn, ac[i], dtr)
            px_at[d][sym] = ac[i]
        n_done += 1
        if n_done % 400 == 0:
            print(f"  …panel {n_done} symbols", flush=True)
    return panel, px_at


def rank_family(feats, spec):
    """feats: {sym: (mom6, mom12, vol66, med_turn, px)} -> ranked [(sym, score)]."""
    if spec["gate"] == "cr5":
        pool = {s: f for s, f in feats.items() if f[3] >= 5 * CR}
    else:
        turns = sorted(f[3] for f in feats.values())
        if not turns:
            return []
        cut = turns[int(0.80 * (len(turns) - 1))]
        pool = {s: f for s, f in feats.items() if f[3] >= cut}
    if len(pool) < TOPN + 5:
        return []
    syms = list(pool)
    if spec["score"] == "riskadj":
        scored = [(s, pool[s][0] / (pool[s][2] + 1e-6)) for s in syms]
    elif spec["score"] == "mom12":
        scored = [(s, pool[s][1]) for s in syms]
    elif spec["score"] == "qualmom":        # 0.4 riskadj + 0.3 deliv-trend + 0.3 lowvol
        syms = [s for s in syms if pool[s][5] is not None]
        if len(syms) < TOPN + 5:
            return []
        pr_ra = pctrank([pool[s][0] / (pool[s][2] + 1e-6) for s in syms])
        pr_dl = pctrank([pool[s][5] for s in syms])
        pr_lv = pctrank([-pool[s][2] for s in syms])
        scored = [(s, 0.4 * a + 0.3 * b + 0.3 * c)
                  for s, a, b, c in zip(syms, pr_ra, pr_dl, pr_lv)]
    else:                                   # lowvol
        pm = pctrank([pool[s][0] for s in syms])
        pv = pctrank([-pool[s][2] for s in syms])
        scored = [(s, 0.5 * a + 0.5 * b) for s, a, b in zip(syms, pm, pv)]
    scored.sort(key=lambda x: -x[1])
    return scored


def apply_band(ranked, prev):
    """The keep-while-≤BAND rule. Returns ordered member list of TOPN symbols."""
    order = {s: i + 1 for i, (s, _sc) in enumerate(ranked)}
    holds = sorted([s for s in prev if order.get(s, 10**9) <= BAND],
                   key=lambda s: order[s])[:TOPN]
    out = list(holds)
    for s, _sc in ranked:
        if len(out) >= TOPN:
            break
        if s not in out:
            out.append(s)
    return out


# ── build / extend ────────────────────────────────────────────────────────────
def _bench_map(conn):
    return {r["trade_date"]: float(r["close_value"]) for r in conn.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name='Nifty 500'")}


def _construct(conn, panel, px_at, dates_by_clock):
    """Run every SPEC forward; write holdings + NAV (full rebuild)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    bench = _bench_map(conn)
    conn.execute("DELETE FROM auto_portfolio_holdings")
    conn.execute("DELETE FROM auto_portfolio_nav")
    for pname, spec in SPECS.items():
        dates = dates_by_clock[spec["clock"]]
        dates = [d for d in dates if d in panel and panel[d]]
        members, nav, b0 = [], 1.0, None
        for k, d in enumerate(dates):
            ranked = rank_family(panel[d], spec)
            if not ranked:
                continue
            new_members = apply_band(ranked, members)
            churned = len(set(new_members) - set(members)) + \
                len(set(members) - set(new_members)) if members else 0
            order = {s: i + 1 for i, (s, _sc) in enumerate(ranked)}
            scores = dict(ranked)
            # period return from the PREVIOUS holdings (held d_prev -> d)
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
            conn.execute("INSERT OR REPLACE INTO auto_portfolio_nav VALUES (?,?,?,?,?,?)",
                         (pname, d, round(nav, 4),
                          round(bnav, 4) if bnav else None, churned, now))
            conn.executemany(
                "INSERT OR REPLACE INTO auto_portfolio_holdings VALUES (?,?,?,?,?,?,?)",
                [(pname, d, s, order.get(s), round(float(scores.get(s, 0)), 4),
                  round(1.0 / TOPN, 4), px_at[d].get(s)) for s in new_members])
            members = new_members
    conn.commit()


def backfill(conn=None) -> str:
    if conn is None:
        with get_conn() as c:
            return backfill(c)
    conn.executescript(SCHEMA)
    days = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? "
        "AND series='EQ' ORDER BY trade_date", (START,))]
    dates_by_clock = {"M": rebalance_dates(days, "M"), "Q": rebalance_dates(days, "Q")}
    all_dates = sorted(set(dates_by_clock["M"]) | set(dates_by_clock["Q"]))
    print(f"backfill: {len(all_dates)} rebalance dates {all_dates[0]} -> {all_dates[-1]}")
    panel, px_at = build_panel(conn, all_dates)
    _construct(conn, panel, px_at, dates_by_clock)
    n = conn.execute("SELECT COUNT(*) c FROM auto_portfolio_nav").fetchone()["c"]
    return f"backfilled {n} portfolio-rebalances since {START}"


def refresh(conn=None) -> str:
    """Nightly: full rebuild only when a NEW clock date exists (cheap check first)."""
    if conn is None:
        with get_conn() as c:
            return refresh(c)
    conn.executescript(SCHEMA)
    days = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? "
        "AND series='EQ' ORDER BY trade_date", (START,))]
    want_m = rebalance_dates(days, "M")[-1] if days else None
    have = conn.execute("SELECT MAX(rebal_date) d FROM auto_portfolio_nav "
                        "WHERE portfolio='PACER-25'").fetchone()
    if want_m and have and have["d"] == want_m:
        return f"clocks unchanged (latest rebalance {want_m})"
    return backfill(conn)


def selftest():
    days = [f"2019-{m:02d}-{d:02d}" for m in range(1, 13) for d in (2, 15)]
    assert len(rebalance_dates(days, "M")) == 12
    assert len(rebalance_dates(days, "Q")) == 4
    assert rebalance_dates(days, "Q")[0] == "2019-01-02"

    ranked = [(f"S{i}", 100 - i) for i in range(1, 60)]
    prev = ["S30", "S40", "S2"]
    mem = apply_band(ranked, prev)
    assert "S30" in mem and "S2" in mem and "S40" not in mem and len(mem) == TOPN
    assert mem[0] in ("S2", "S30") and "S1" in mem       # refill from the top

    feats = {f"S{i}": (0.01 * i, 0.02 * i, 0.02, 10 * CR, 100.0, 1.0 + 0.01 * i) for i in range(1, 40)}
    feats["ILLIQ"] = (9, 9, 0.01, 1 * CR, 100.0, 2.0)
    rk = rank_family(feats, SPECS["PACER-25"])
    assert rk and rk[0][0] == "S39" and all(s != "ILLIQ" for s, _x in rk)
    rk2 = rank_family(feats, SPECS["SPRINTER-25"])
    assert rk2[0][0] == "S39"
    rk4 = rank_family(feats, SPECS["CRAFTSMAN-25"])
    assert rk4 and rk4[0][0] == "S39" and all(s != "ILLIQ" for s, _x in rk4)
    print("AUTO_PORTFOLIOS selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--backfill" in sys.argv:
        print("auto_portfolios:", backfill())
    elif "--refresh" in sys.argv:
        print("auto_portfolios:", refresh())
    else:
        print(__doc__)
