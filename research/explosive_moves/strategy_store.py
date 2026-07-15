"""Strategy registry — the PERSISTENT, refinable store so results stop hiding in
terminal output / static HTML. Three tables in research.db (additive, IF NOT EXISTS —
never touches existing tables):

  strategy_registry  : one row per strategy (definition + current status)
  strategy_runs      : one row per BACKTEST RUN (timestamped history — refine = append,
                       never overwrite, so you can see how metrics moved across versions)
  strategy_holdings  : current top-N names per strategy (as-of date)

Seeds itself from the committed out/*.csv (factor_zoo, cost_realism) so the whole
session's testing lands in the DB. Going forward, any backtest calls record_run() and
the board / a future dashboard READ from here. Run on VPS (.venv-research).

METRIC CONSTRAINT (D142): the `sharpe` / `h1_sharpe` / `h2_sharpe` COLUMNS hold
mean/sd annualised with NO risk-free rate subtracted — return/vol ratios, not Sharpe
ratios, so they read high against a textbook Sharpe. The column NAMES are kept as-is
deliberately: this schema is created with CREATE TABLE IF NOT EXISTS against a live
research.db, so renaming the DDL would NOT migrate the existing rows — it would
silently mismatch them. Everything read and rendered says "return/vol"; only the
on-disk column names remain legacy. A true Sharpe needs a primary-source rf ingest
(Guardrail #8) and is queued with the TR-benchmark re-cut, which moves the same
figures. Seeding accepts either header (retvol = current writers, sharpe = the
committed pre-D142 artifacts).

CLI:  python -m explosive_moves.strategy_store --seed --report
"""
from __future__ import annotations
import argparse
import csv
import os
import sqlite3
from datetime import datetime, timezone

RDB = "/opt/hermes/data/research.db"
OUT = os.path.join(os.path.dirname(__file__), "out")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS strategy_registry(
      name TEXT PRIMARY KEY, category TEXT, universe TEXT, rebalance TEXT,
      status TEXT, description TEXT, created TEXT, updated TEXT);
    CREATE TABLE IF NOT EXISTS strategy_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, run_ts TEXT, cost_model TEXT,
      sharpe REAL, sortino REAL, cagr_pct REAL, maxdd_pct REAL, calmar REAL,
      ann_cost_pct REAL, capacity_cr REAL, h1_sharpe REAL, h2_sharpe REAL,
      survives TEXT, source TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS strategy_holdings(
      name TEXT, as_of TEXT, rank INTEGER, symbol TEXT,
      PRIMARY KEY(name, as_of, symbol));
    """)


def register(con, name, category, universe, rebalance, status, description):
    con.execute("""INSERT INTO strategy_registry(name,category,universe,rebalance,status,description,created,updated)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET category=excluded.category, universe=excluded.universe,
          rebalance=excluded.rebalance, status=excluded.status, description=excluded.description,
          updated=excluded.updated""",
        (name, category, universe, rebalance, status, description, _now(), _now()))


def record_run(con, name, cost_model, m, source, notes=""):
    # legacy column names hold return/vol ratios — see the module docstring (D142)
    con.execute("""INSERT INTO strategy_runs(name,run_ts,cost_model,sharpe,sortino,cagr_pct,maxdd_pct,
        calmar,ann_cost_pct,capacity_cr,h1_sharpe,h2_sharpe,survives,source,notes)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (name, _now(), cost_model, m.get("retvol"), m.get("sortino"), m.get("cagr"), m.get("maxdd"),
         m.get("calmar"), m.get("ann_cost"), m.get("capacity"), m.get("h1"), m.get("h2"),
         m.get("survives"), source, notes))


def set_holdings(con, name, as_of, symbols):
    con.execute("DELETE FROM strategy_holdings WHERE name=?", (name,))
    con.executemany("INSERT OR REPLACE INTO strategy_holdings(name,as_of,rank,symbol) VALUES(?,?,?,?)",
                    [(name, as_of, i + 1, s) for i, s in enumerate(symbols)])


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ratio(r, stem):
    """Read a return/vol column, tolerating the pre-D142 header name.

    Current writers emit `retvol`/`h1_retvol`/`h2_retvol`; the committed out/*.csv
    artifacts predate the relabel and carry `sharpe`/`h1_sharpe`/`h2_sharpe`. Same
    number either way — the rename was vocabulary-only — so accept both rather than
    silently seeding NULLs from a historical file.
    """
    v = r.get(stem.replace("sharpe", "retvol"))
    return _f(v if v is not None else r.get(stem))


def seed(con):
    # --- public factors (flat-cost factor zoo) ---
    fz = os.path.join(OUT, "factor_zoo.csv")
    if os.path.exists(fz):
        for r in csv.DictReader(open(fz)):
            nm = "ZOO:" + r["factor"]
            register(con, nm, "public-factor", "Nifty-liquid top-40%", "monthly",
                     "survives" if r.get("survives_both_halves") == "YES" else "did-not-survive",
                     "Public factor, flat-cost factor-zoo tearsheet")
            record_run(con, nm, "flat-0.3%/turnover",
                       {"retvol": _ratio(r, "sharpe"), "sortino": _f(r.get("sortino")),
                        "cagr": _f(r.get("cagr_pct")), "maxdd": _f(r.get("maxdd_pct")),
                        "calmar": _f(r.get("calmar")), "h1": _ratio(r, "h1_sharpe"),
                        "h2": _ratio(r, "h2_sharpe"), "survives": r.get("survives_both_halves")},
                       "out/factor_zoo.csv")
    # --- cost-realism configs (the honest tests) ---
    cr = os.path.join(OUT, "cost_realism.csv")
    if os.path.exists(cr):
        for r in csv.DictReader(open(cr)):
            nm = "COST:" + r["config"]
            cm = "flat-0.3%/turnover" if "flat" in r["config"].lower() else "realistic (tier spread + 0.5xATR slip)"
            isbench = "buy & hold" in r["config"].lower()
            register(con, nm, "baseline" if isbench else "cost-tested",
                     "large-cap (q)" if "quarterly" in r["config"].lower() else "Nifty-liquid (m)",
                     "quarterly" if "quarterly" in r["config"].lower() else "monthly",
                     "benchmark" if isbench else "tested",
                     "Realistic-cost stress / capacity test")
            record_run(con, nm, cm,
                       {"retvol": _ratio(r, "sharpe"), "cagr": _f(r.get("cagr_pct")),
                        "maxdd": _f(r.get("maxdd_pct")), "calmar": _f(r.get("calmar")),
                        "ann_cost": _f(r.get("ann_cost_pct")), "capacity": _f(r.get("cap_med_cr")),
                        "h1": _ratio(r, "h1_sharpe"), "h2": _ratio(r, "h2_sharpe")},
                       "out/cost_realism.csv")
    con.commit()


def report(con):
    print("=== strategy_registry (latest run per strategy, by return/vol) ===")
    rows = con.execute("""
        SELECT g.name, g.category, g.status,
               (SELECT sharpe FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1) sh,
               (SELECT cagr_pct FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1) cg,
               (SELECT maxdd_pct FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1) dd,
               (SELECT cost_model FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1) cm
        FROM strategy_registry g ORDER BY sh DESC""").fetchall()
    for nm, cat, st, sh, cg, dd, cm in rows:
        print(f"  {sh if sh is not None else float('nan'):>6.2f}  {nm[:46]:<46} {cat:<13} [{cm}]")
    nrun = con.execute("SELECT COUNT(*) FROM strategy_runs").fetchone()[0]
    nstr = con.execute("SELECT COUNT(*) FROM strategy_registry").fetchone()[0]
    nh = con.execute("SELECT COUNT(DISTINCT name) FROM strategy_holdings").fetchone()[0]
    print(f"\n{nstr} strategies | {nrun} backtest runs | holdings stored for {nh} | DB: {RDB}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(RDB)
    ensure_schema(con)
    if a.seed:
        seed(con)
    if a.report or not a.seed:
        report(con)
    con.close()


if __name__ == "__main__":
    main()
