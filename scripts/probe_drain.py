"""Credibility-drain status: how much is extracted vs the backlog, and breadth."""
import sqlite3
c = sqlite3.connect("/opt/hermes/data/hermes.db")
try:  # CL-SCR-08: close the connection even if a query raises
    tot = c.execute("SELECT COUNT(DISTINCT symbol||'|'||period_label) FROM concalls").fetchone()[0]
    nsym = c.execute("SELECT COUNT(DISTINCT symbol) FROM concalls").fetchone()[0]
    # extracted = transcripts that produced guidance rows
    ext = c.execute("SELECT COUNT(DISTINCT symbol||'|'||source_period) FROM concall_guidance").fetchone()[0]
    ext_sym = c.execute("SELECT COUNT(DISTINCT symbol) FROM concall_guidance").fetchone()[0]
    print("transcripts collected (sym+period):", tot, "across", nsym, "symbols")
    print("transcripts extracted (have guidance):", ext, "across", ext_sym, "symbols")
    print("backlog (collected, not yet extracted):", tot - ext)
finally:
    c.close()
