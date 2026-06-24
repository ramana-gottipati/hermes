"""Probe: is concall credibility backtestable (historical depth + breadth)?"""
import sqlite3

for dbname in ("/opt/hermes/data/hermes.db", "/opt/hermes/data/research.db"):
    print(f"\n================ {dbname} ================")
    c = sqlite3.connect(dbname)
    tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'concall%'")]
    for t in tabs:
        try:
            n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            cols = [x[1] for x in c.execute(f"PRAGMA table_info({t})")]
            datecol = next((d for d in cols if "date" in d.lower() or "period" in d.lower() or "quarter" in d.lower()), None)
            symcol = next((s for s in cols if s.lower() in ("symbol", "ticker", "nse_symbol")), None)
            rng = nsym = "?"
            if datecol:
                rng = c.execute(f"SELECT MIN({datecol}),MAX({datecol}) FROM {t}").fetchone()
            if symcol:
                nsym = c.execute(f"SELECT COUNT(DISTINCT {symcol}) FROM {t}").fetchone()[0]
            print(f"  {t:34} rows={n:>7}  date[{datecol}]={rng}  distinct_sym={nsym}")
        except Exception as e:
            print(f"  {t}: ERR {e}")
    c.close()
