#!/usr/bin/env bash
# hermes-db-backup.sh — on-box disaster-recovery backup for the single 16GB SQLite DB (AUD-02).
#
# WHY: hermes.db is the only copy of ~5y of ingest + non-re-derivable data (real first-seen
# provenance dates, Gemini-paid credibility/enrichment, user tracker/drawings, API tenant keys,
# the accumulating momentum_scan history). Before this, a corruption / accidental DROP / bad
# migration lost everything. This gives a consistent, integrity-checked, rotated local copy.
#
# METHOD: `sqlite3 .backup` is the ONLINE backup API — safe to run while writers hold the WAL
# (it takes a read snapshot, never blocks writers for long, and yields a transactionally
# consistent file). We then PRAGMA quick_check the result so a silently-corrupt backup can't
# masquerade as protection, and rotate to KEEP copies.
#
# NOT disaster recovery on its own: an on-box copy dies with the disk. OFF-BOX shipping (rclone
# to object storage / a Hostinger snapshot) is the remaining piece and needs a destination +
# credentials from the owner — see docs/AUDIT-2026-07-02-institutional-review.md AUD-02.
set -euo pipefail

DB="${HERMES_DB:-/opt/hermes/data/hermes.db}"
DEST="${HERMES_BACKUP_DIR:-/opt/hermes/backups/db}"
KEEP="${HERMES_BACKUP_KEEP:-3}"
ts="$(date -u +%Y%m%d-%H%M%S)"
out="$DEST/hermes-$ts.db"

log() { echo "$(date -u +%FT%TZ) $*"; }

[ -f "$DB" ] || { log "FATAL: source DB not found: $DB"; exit 1; }
mkdir -p "$DEST"

# Refuse to run if free space < 1.2x the DB size (avoid filling the disk the DB lives on).
db_bytes=$(stat -c %s "$DB")
free_bytes=$(df -PB1 "$DEST" | awk 'NR==2{print $4}')
need=$(( db_bytes * 12 / 10 ))
if [ "$free_bytes" -lt "$need" ]; then
  log "FATAL: only $((free_bytes/1024/1024))MB free at $DEST, need ~$((need/1024/1024))MB — aborting (rotate/clear first)"; exit 1
fi

log "backup start: $DB -> $out ($((db_bytes/1024/1024))MB)"
# Online, consistent backup. Do NOT use `cp` — a live WAL DB copied with cp can be torn.
sqlite3 "$DB" ".backup '$out'"

# Verify the backup is structurally sound before we trust/rotate on it.
chk=$(sqlite3 "$out" "PRAGMA quick_check;" 2>&1 | head -1)
if [ "$chk" != "ok" ]; then
  log "FATAL: quick_check on $out returned '$chk' — leaving it for inspection, NOT rotating"; exit 2
fi
# Sanity: the backup must be within 10% of source size (catches a truncated/half-written file).
out_bytes=$(stat -c %s "$out")
if [ "$out_bytes" -lt $(( db_bytes * 9 / 10 )) ]; then
  log "FATAL: backup $((out_bytes/1024/1024))MB is <90% of source $((db_bytes/1024/1024))MB — suspect truncation"; exit 3
fi
log "backup OK: $out ($((out_bytes/1024/1024))MB, quick_check=ok)"

# Rotation: keep the newest $KEEP verified backups, delete the rest.
mapfile -t old < <(ls -1t "$DEST"/hermes-*.db 2>/dev/null | tail -n +"$((KEEP+1))")
for f in "${old[@]:-}"; do [ -n "$f" ] && { log "rotate: rm $f"; rm -f "$f"; }; done

log "done. kept: $(ls -1 "$DEST"/hermes-*.db 2>/dev/null | wc -l) backup(s)"
