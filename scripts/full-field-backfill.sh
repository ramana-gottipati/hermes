#!/usr/bin/env bash
# full-field-backfill.sh (session 19) — fill EVERY stock_signals field across the
# FULL history, oldest -> newest.
#
# The D47 deep signals recompute already populated DVPT / scores / zones /
# key-price (D44) / character (D43) back to 2011-06-22 (verified 95-100% non-null).
# The only remaining gap is the RS block — rs_vs_broad_*, rs_vs_sector_*, rs_rank,
# primary_sector — which needs index history, and index_rows only reached
# 2021-06-02. This chain deepens the index data as far as NSE's ind_close_all
# archive goes, recomputes index signals/ratios, then runs the stock-RS backfill
# so RS fills as deep as the index data allows.
#
# Safety: `indexes --backfill` skips already-ingested dates (idempotent, rate-
# limited); `index_signals` writes its OWN tables (ratio_rows / index_signals);
# `stock_rs` is a pure UPDATE of only the RS columns and never touches the signals
# columns. Run detached + logged:
#   nohup bash /opt/hermes/scripts/full-field-backfill.sh \
#         > /var/log/hermes-fullfield.log 2>&1 &
set -uo pipefail
cd /opt/hermes
PY=/opt/hermes/.venv/bin/python
log(){ echo "[$(date -u '+%F %T')Z] $*"; }

log "=== FULL-FIELD BACKFILL START ==="

log "Stage 0: re-attempt the 5 special-session gap days (Muhurat / NSE special Saturdays)"
for d in 2019-10-27 2020-11-14 2022-08-08 2024-01-20 2024-05-18; do
  log "  signals --date $d"
  $PY -m src.automation.signals --date "$d" || true
done

log "Stage A: index history backfill (deep ~2010; skips already-ingested dates)"
$PY -m src.automation.indexes --backfill 5900

log "Stage B: index signals + ratios recompute (all dates)"
$PY -m src.automation.index_signals --backfill

log "Stage C: stock RS backfill — broad + sector + percentile rank, all dates"
$PY -m src.automation.stock_rs --backfill

log "Stage D: WAL checkpoint + coverage report"
$PY - <<'PYEOF'
import sqlite3
db = sqlite3.connect("/opt/hermes/data/hermes.db", timeout=300)
try:
    db.execute("PRAGMA wal_checkpoint(PASSIVE)")
except Exception as e:
    print("checkpoint:", e)
imn, imx, ind = db.execute(
    "SELECT MIN(trade_date), MAX(trade_date), COUNT(DISTINCT trade_date) FROM index_rows").fetchone()
print(f"index_rows: {imn} .. {imx} ({ind} days)")
for ym in ('2013-01', '2015-01', '2019-01', '2022-01', '2026-06'):
    d = db.execute("SELECT MIN(trade_date) FROM stock_signals WHERE trade_date>=?", (ym + '-01',)).fetchone()[0]
    if not d:
        continue
    tot, rs, rk = db.execute(
        "SELECT COUNT(*), COUNT(rs_vs_broad_today), COUNT(rs_rank) FROM stock_signals WHERE trade_date=?",
        (d,)).fetchone()
    print(f"  {d}: rows={tot} rs_vs_broad={rs} rs_rank={rk}")
db.close()
PYEOF

log "=== FULL-FIELD BACKFILL DONE ==="
