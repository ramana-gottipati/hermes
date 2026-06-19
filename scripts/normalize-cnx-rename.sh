#!/usr/bin/env bash
# normalize-cnx-rename.sh (session 19) — push RS back to 2012.
#
# NSE rebranded every index in Nov 2015 (S&P CNX 500 / CNX 500 -> Nifty 500;
# CNX Nifty -> Nifty 50; CNX Bank -> Nifty Bank; ...). The full-field backfill
# fetched the raw index levels back to 2012-02, but the pre-2015 rows are stored
# under the OLD names, which RS (which uses the current Nifty names) can't match
# -- so rs_vs_broad / rs_vs_sector / rs_rank floored at 2015-11.
#
# This normalizes the old names to their current Nifty names in index_rows
# (merging ONLY into a Nifty name that already exists -- safe, no orphans; old
# and new date ranges are disjoint so no key conflict), then recomputes index
# signals/ratios and the stock-RS backfill so RS fills to 2012-02.
set -uo pipefail
cd /opt/hermes
PY=/opt/hermes/.venv/bin/python
log(){ echo "[$(date -u '+%F %T')Z] $*"; }

log "=== CNX->Nifty NAME NORMALIZATION + RS re-deepen START ==="

log "Stage 1: normalize old index names in index_rows"
$PY - <<'PYEOF'
import sqlite3
db = sqlite3.connect("/opt/hermes/data/hermes.db", timeout=120)
cur = db.cursor()
existing = {r[0] for r in cur.execute("SELECT DISTINCT index_name FROM index_rows")}
# Explicit renames whose new name isn't a literal "Nifty "+suffix swap.
amap = {
    "S&P CNX 500": "Nifty 500", "CNX 500": "Nifty 500",
    "S&P CNX Nifty": "Nifty 50", "CNX Nifty": "Nifty 50",
    "CNX Nifty Junior": "Nifty Next 50",
    "CNX 100": "Nifty 100", "CNX 200": "Nifty 200",
}
# Auto: "CNX X" -> "Nifty X" for every remaining old sectoral name.
for n in existing:
    if n.startswith("CNX ") and n not in amap:
        amap[n] = "Nifty " + n[4:]
applied = 0
for old, new in sorted(amap.items()):
    if old not in existing:
        continue
    if new not in existing:                 # only merge into an existing index
        print(f"  skip (no current '{new}'): {old}")
        continue
    cur.execute("UPDATE index_rows SET index_name=? WHERE index_name=?", (new, old))
    print(f"  {old:30} -> {new:22} ({cur.rowcount} rows)")
    applied += cur.rowcount
db.commit()
print("total rows renamed:", applied)
db.close()
PYEOF

log "Stage 2: index signals + ratios recompute (now matching deep names)"
$PY -m src.automation.index_signals --backfill

log "Stage 3: stock RS backfill — broad + sector + percentile rank, all dates"
$PY -m src.automation.stock_rs --backfill

log "Stage 4: checkpoint + RS coverage"
$PY - <<'PYEOF'
import sqlite3
db = sqlite3.connect("/opt/hermes/data/hermes.db", timeout=300)
try:
    db.execute("PRAGMA wal_checkpoint(PASSIVE)")
except Exception as e:
    print("checkpoint:", e)
print("Nifty 500 span:", db.execute(
    "SELECT MIN(trade_date), MAX(trade_date) FROM index_rows WHERE index_name='Nifty 500'").fetchone())
print("earliest rs_vs_broad:", db.execute(
    "SELECT MIN(trade_date) FROM stock_signals WHERE rs_vs_broad_today IS NOT NULL").fetchone()[0])
print("earliest rs_vs_sector:", db.execute(
    "SELECT MIN(trade_date) FROM stock_signals WHERE rs_vs_sector_today IS NOT NULL").fetchone()[0])
print("earliest rs_rank:", db.execute(
    "SELECT MIN(trade_date) FROM stock_signals WHERE rs_rank IS NOT NULL").fetchone()[0])
db.close()
PYEOF

log "=== DONE ==="
