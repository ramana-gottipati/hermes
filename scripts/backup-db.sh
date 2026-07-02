#!/usr/bin/env bash
# AUD-02: on-box backup of the non-derivable state in /opt/hermes/data.
#
# Nightly (every run):
#   - hermes.db  -> gzipped SQL dump of ALL tables EXCEPT the derivable giants
#                   (bhavcopy_rows / stock_signals / mep_signals / cpr_signals —
#                   ~10.5 GB recomputable from the on-disk raw NSE archive; the
#                   dump covers conversations, tracker, concall_*, fundamentals,
#                   pat_*, credit_ratings, insider/SAST, enrich, ... everything else)
#   - research.db -> consistent VACUUM INTO copy (fundamentals/shareholding PIT history)
#   - retention: 7 nightly sets
# Weekly (Sundays, or --full):
#   - hermes.db   -> full VACUUM INTO copy (retain the newest 1 previous)
#   - em_cache.pkl -> copy (retain 1)
#
# All reads open the source READ-ONLY (mode=ro URI) — this job can never write
# the production DBs. Off-box shipping is NOT configured (no remote credentials);
# the manual laptop pull (scripts/download-from-vps.bat) + Hostinger snapshots
# remain the off-box story — see PROJECT_STATE 'What's NOT yet built'.
set -euo pipefail

DATA=/opt/hermes/data
DEST=/opt/hermes/backups/db
DAY=$(date -u +%Y%m%d)
DOW=$(date -u +%u)   # 1=Mon .. 7=Sun
EXCLUDE="'bhavcopy_rows','stock_signals','mep_signals','cpr_signals'"

mkdir -p "$DEST"
echo "[backup] start $(date -u +%FT%TZ)"

# --- nightly: hermes.db non-derivable tables -> sql.gz -----------------------
TABLES=$(sqlite3 "file:$DATA/hermes.db?mode=ro" \
  "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ($EXCLUDE);")
# one sqlite3 session = one consistent read snapshot for every dumped table
{ echo ".bail on"; echo ".mode insert"; for t in $TABLES; do echo ".dump '$t'"; done; } \
  | sqlite3 "file:$DATA/hermes.db?mode=ro" | gzip > "$DEST/hermes-tables-$DAY.sql.gz.tmp"
mv "$DEST/hermes-tables-$DAY.sql.gz.tmp" "$DEST/hermes-tables-$DAY.sql.gz"
echo "[backup] hermes tables: $(du -h "$DEST/hermes-tables-$DAY.sql.gz" | cut -f1) ($(echo "$TABLES" | wc -w) tables)"

# --- nightly: research.db full consistent copy --------------------------------
rm -f "$DEST/research-$DAY.db"
sqlite3 "file:$DATA/research.db?mode=ro" "VACUUM INTO '$DEST/research-$DAY.db'"
echo "[backup] research.db: $(du -h "$DEST/research-$DAY.db" | cut -f1)"

# --- weekly: full hermes.db + em_cache.pkl ------------------------------------
if [ "$DOW" = 7 ] || [ "${1:-}" = "--full" ]; then
  rm -f "$DEST/hermes-full-$DAY.db"
  sqlite3 "file:$DATA/hermes.db?mode=ro" "VACUUM INTO '$DEST/hermes-full-$DAY.db'"
  echo "[backup] hermes full: $(du -h "$DEST/hermes-full-$DAY.db" | cut -f1)"
  ls -1t "$DEST"/hermes-full-*.db 2>/dev/null | tail -n +3 | xargs -r rm -f
  cp "$DATA/em_cache.pkl" "$DEST/em_cache-$DAY.pkl.tmp" && mv "$DEST/em_cache-$DAY.pkl.tmp" "$DEST/em_cache-$DAY.pkl"
  ls -1t "$DEST"/em_cache-*.pkl 2>/dev/null | tail -n +2 | xargs -r rm -f
fi

# --- retention: 7 nightly sets -------------------------------------------------
find "$DEST" -name 'hermes-tables-*.sql.gz' -mtime +7 -delete
find "$DEST" -name 'research-*.db' -mtime +7 -delete

echo "[backup] done $(date -u +%FT%TZ); inventory:"
ls -lh "$DEST" | tail -n +2
