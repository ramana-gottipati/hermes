"""Slow rotation — the QUARTERLY large-cap LOWVOL_MOM portfolio anchor (descriptive).

THE ONE VALIDATED CORNER of the momentum family (strategy-ledger §§ Tier-1 + cost-realism
2026-07-02/05c): quarterly-clock, LARGE-CAP-gated (top-quintile turnover), wide hold-band
LOWVOL_MOM — flat-cost family Sharpe ~1.10, participation-NET ~1.02 @ ₹50cr, beats the
index net up to ~₹100-150cr capacity. Every faster / smaller / tighter variant failed net
of costs. This module maintains the CURRENT quarterly portfolio ANCHOR as data:

  * Universe: latest `momentum_scan` snapshot (nightly, research lane) gated to the top
    turnover QUINTILE of that day (self-scaling; no static rupee threshold).
  * Score: LOWVOL_MOM = 0.5·pctrank(mom6) + 0.5·pctrank(−vol_66) over the gated set.
  * Clock: rebalance ONLY when the calendar quarter changes (first nightly run of a new
    quarter). Between rebalances the anchor is FROZEN — live rank moves are drift, not trades.
  * Hold band (turnover discipline): existing members stay while ranked ≤ BAND(35); slots
    are refilled to TOPN(25) from the top of the gated ranking. Drops recorded as 'exited'
    for one cycle.

Owns the isolated bounded table `slow_rotation` (≤ ~50 rows; no db.py edit). Pure stdlib.
DESCRIPTIVE-ONLY (SEBI-safe): this is the validated rule's current composition shown as
data — not advice, not an execution system; momentum here is BETA, not selection skill
(docs/predictive-attributes-findings.md). Reader = /dash/momentum-scan/slow.

CLI:
  python -m src.automation.slow_rotation --refresh [--force-rebalance]
  python -m src.automation.slow_rotation --selftest
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore

TOPN = 25
BAND = 35
GATE_QUANTILE = 0.80          # top turnover quintile

SCHEMA = """
CREATE TABLE IF NOT EXISTS slow_rotation (
    symbol        TEXT,
    role          TEXT,      -- hold | entered | exited
    rebal_date    TEXT,      -- the momentum_scan as_of the anchor was set on
    rank_at_rebal INTEGER,
    score         REAL,      -- LOWVOL_MOM percentile blend at rebalance
    mom6          REAL,
    vol_66        REAL,
    turnover_cr   REAL,
    computed_at   TEXT,
    PRIMARY KEY(symbol, role)
);
"""


def pctrank(vals):
    """values -> percentile ranks in [0,1] (average-of-positions for ties)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    n = len(vals)
    out = [0.0] * n
    if n == 1:
        return [0.5]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 / (n - 1)
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def gate_and_rank(rows):
    """rows: dicts with symbol, mom6, vol_66, turnover_cr. Returns ranked list of
    dicts (rank 1 = best LOWVOL_MOM) over the top turnover quintile."""
    ok = [r for r in rows if r["mom6"] is not None and r["vol_66"] is not None
          and r["turnover_cr"] is not None and r["vol_66"] > 0]
    if len(ok) < 50:
        return []
    turns = sorted(r["turnover_cr"] for r in ok)
    cut = turns[int(GATE_QUANTILE * (len(turns) - 1))]
    gated = [r for r in ok if r["turnover_cr"] >= cut]
    pm = pctrank([r["mom6"] for r in gated])
    pv = pctrank([-r["vol_66"] for r in gated])
    for r, a, b in zip(gated, pm, pv):
        r["score"] = round(0.5 * a + 0.5 * b, 4)
    gated.sort(key=lambda r: -r["score"])
    for i, r in enumerate(gated):
        r["rank"] = i + 1
    return gated


def rebalance(ranked, prev_members):
    """The hold-band rule. Returns (holds, entered, exited) symbol lists."""
    by_sym = {r["symbol"]: r for r in ranked}
    holds = [s for s in prev_members
             if s in by_sym and by_sym[s]["rank"] <= BAND]
    holds.sort(key=lambda s: by_sym[s]["rank"])
    holds = holds[:TOPN]
    entered = []
    for r in ranked:
        if len(holds) + len(entered) >= TOPN:
            break
        if r["symbol"] not in holds:
            entered.append(r["symbol"])
    exited = [s for s in prev_members if s not in holds]
    return holds, entered, exited


def _qkey(date_str):
    y, m = int(date_str[:4]), int(date_str[5:7])
    return (y, (m - 1) // 3)


def refresh(conn=None, force=False) -> str:
    if conn is None:
        with get_conn() as c:
            return refresh(c, force)
    conn.executescript(SCHEMA)
    row = conn.execute("SELECT MAX(as_of) d FROM momentum_scan").fetchone()
    as_of = row["d"] if row else None
    if not as_of:
        return "no momentum_scan data"
    anchor = conn.execute(
        "SELECT symbol, role, rebal_date FROM slow_rotation WHERE role IN ('hold','entered')"
    ).fetchall()
    prev_members = [r["symbol"] for r in anchor]
    prev_rebal = anchor[0]["rebal_date"] if anchor else None
    if prev_rebal and not force and _qkey(prev_rebal) == _qkey(as_of):
        return f"anchor frozen (quarter unchanged, rebal {prev_rebal}, latest {as_of})"

    rows = [dict(r) for r in conn.execute(
        "SELECT symbol, mom6, vol_66, turnover_cr FROM momentum_scan WHERE as_of=?",
        (as_of,))]
    ranked = gate_and_rank(rows)
    if not ranked:
        return f"gated universe too small on {as_of}; anchor left untouched"
    holds, entered, exited = rebalance(ranked, prev_members)
    by_sym = {r["symbol"]: r for r in ranked}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    conn.execute("DELETE FROM slow_rotation")
    out = []
    for role, syms in (("hold", holds), ("entered", entered)):
        for s in syms:
            r = by_sym[s]
            out.append((s, role, as_of, r["rank"], r["score"], r["mom6"],
                        r["vol_66"], r["turnover_cr"], now))
    for s in exited:
        r = by_sym.get(s)
        out.append((s, "exited", as_of, r["rank"] if r else None,
                    r["score"] if r else None, r["mom6"] if r else None,
                    r["vol_66"] if r else None, r["turnover_cr"] if r else None, now))
    conn.executemany("INSERT OR REPLACE INTO slow_rotation VALUES (?,?,?,?,?,?,?,?,?)", out)
    conn.commit()
    return (f"REBALANCED on {as_of}: {len(holds)} held + {len(entered)} entered, "
            f"{len(exited)} exited (gated universe {len(ranked)})")


def selftest():
    # pctrank: ties averaged, ends at 0/1
    pr = pctrank([1.0, 2.0, 2.0, 3.0])
    assert pr[0] == 0.0 and pr[3] == 1.0
    assert abs(pr[1] - 0.5) < 1e-9 and abs(pr[2] - 0.5) < 1e-9

    # gate: exactly the top turnover quintile survives
    rows = [{"symbol": f"S{i}", "mom6": 0.1 * (i % 7), "vol_66": 0.01 + 0.001 * (i % 5),
             "turnover_cr": float(i)} for i in range(100)]
    ranked = gate_and_rank(rows)
    assert all(r["turnover_cr"] >= 79.0 for r in ranked) and len(ranked) >= 20

    # band rule: member ranked 30 stays, ranked 40 exits, fills reach TOPN
    ranked2 = [{"symbol": f"R{i}", "rank": i, "score": 1.0 / i} for i in range(1, 60)]
    prev = ["R30", "R40", "R2"]
    holds, entered, exited = rebalance(ranked2, prev)
    assert "R30" in holds and "R2" in holds and "R40" in exited
    assert len(holds) + len(entered) == TOPN
    assert entered[0] == "R1"                      # fills come from the top

    # quarter clock
    assert _qkey("2026-01-15") == _qkey("2026-03-31")
    assert _qkey("2026-03-31") != _qkey("2026-04-01")
    print("SLOW_ROTATION selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--refresh" in sys.argv:
        print("slow_rotation:", refresh(force="--force-rebalance" in sys.argv))
    else:
        print(__doc__)
