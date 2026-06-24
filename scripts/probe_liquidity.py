"""Probe: what do we have to build a size-NEUTRAL liquidity gate (turnover/mcap)?"""
import sqlite3

R = sqlite3.connect("/opt/hermes/data/research.db")
H = sqlite3.connect("/opt/hermes/data/hermes.db")

print("=== fundamentals_history: metrics that could give shares / market cap ===")
rows = R.execute("SELECT metric, COUNT(*) c FROM fundamentals_history GROUP BY metric ORDER BY c DESC").fetchall()
for m, c in rows:
    ml = m.lower()
    if any(k in ml for k in ("share", "cap", "equity", "eps", "net profit", "face")):
        print(f"  {c:>7}  {m}")

print("\n=== PIXTRANS coverage ===")
print("  research.db fundamentals rows:",
      R.execute("SELECT COUNT(*) FROM fundamentals_history WHERE symbol='PIXTRANS'").fetchone()[0])
print("  EQ bhav rows:",
      H.execute("SELECT COUNT(*),MIN(trade_date),MAX(trade_date) FROM bhavcopy_rows WHERE symbol='PIXTRANS' AND series='EQ'").fetchone())
print("  PIXTRANS NP & EPS (latest annual):")
for met in ("Net Profit", "EPS in Rs", "Equity Capital"):
    r = R.execute("SELECT period_end,report_date,value FROM fundamentals_history WHERE symbol='PIXTRANS' AND period_type='A' AND metric=? ORDER BY period_end DESC LIMIT 1", (met,)).fetchone()
    print(f"    {met}: {r}")

print("\n=== PIXTRANS typical daily turnover (value) vs a megacap, recent ===")
for sym in ("PIXTRANS", "RELIANCE", "HDFCBANK"):
    r = H.execute("SELECT AVG(value),AVG(volume),AVG(close) FROM bhavcopy_rows WHERE symbol=? AND series='EQ' AND trade_date>='2023-01-01'", (sym,)).fetchone()
    av = (r[0] or 0) / 1e7
    print(f"  {sym:10} avg daily value Rs {av:,.1f} cr | avg vol {r[1] or 0:,.0f} | avg close {r[2] or 0:,.0f}")

print("\n=== index membership table (to classify large vs mid/small)? ===")
for t in ("stock_index_membership", "index_rows"):
    try:
        cols = [c[1] for c in H.execute(f"PRAGMA table_info({t})")]
        n = H.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows, cols={cols}")
    except Exception as e:
        print(f"  {t}: ERR {e}")
try:
    print("  distinct indexes in stock_index_membership:",
          [r[0] for r in H.execute("SELECT DISTINCT index_name FROM stock_index_membership LIMIT 20")])
except Exception as e:
    print("  membership distinct ERR:", e)
