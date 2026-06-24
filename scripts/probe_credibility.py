"""Is guidance SETTLED enough to compute credibility (GA) + run a falsification gate?"""
import sqlite3
c = sqlite3.connect("/opt/hermes/data/hermes.db")

print("=== concall_guidance.status distribution ===")
for row in c.execute("SELECT COALESCE(status,'(null)') s, COUNT(*) n FROM concall_guidance GROUP BY s ORDER BY n DESC"):
    print(f"  {row[0]:12} {row[1]}")

print("\n=== symbols with >=1 RESOLVED promise (MET/MISSED/PARTIAL) ===")
r = c.execute("SELECT COUNT(DISTINCT symbol) FROM concall_guidance WHERE status IN ('MET','MISSED','PARTIAL')").fetchone()
print("  distinct symbols:", r[0])
r = c.execute("SELECT COUNT(DISTINCT symbol||'|'||source_period) FROM concall_guidance WHERE status IN ('MET','MISSED','PARTIAL')").fetchone()
print("  distinct (symbol,period) with resolved guidance:", r[0])

print("\n=== existing concall_scores: credibility/GA values ===")
for row in c.execute("SELECT symbol, as_of_period, credibility_score, composite_score, tier, n_promises_resolved FROM concall_scores ORDER BY composite_score DESC LIMIT 30"):
    print(f"  {row[0]:12} {row[1]:10} cred={row[2]} comp={row[3]} tier={row[4]} resolved={row[5]}")

print("\n=== concalls: how do we get a DATE per (symbol,period)? ===")
for row in c.execute("SELECT symbol, period_label, concall_year, concall_month, concall_date FROM concalls WHERE concall_year IS NOT NULL ORDER BY concall_year DESC, concall_month DESC LIMIT 5"):
    print("  ", tuple(row))
