#!/usr/bin/env bash
# hermes-db-restore.sh — restore hermes.db from a backup produced by hermes-db-backup.sh (AUD-02).
#
# A backup you have never restored is a hope, not a backup. This script makes restore a tested,
# one-command operation and is also the "restore test" the audit requires:
#   * with --verify <file>  : integrity-check a backup and print its table/row fingerprint. Read-only;
#                             run it in CI/ops any time to prove the newest backup is restorable.
#   * with --into <file>    : perform an ACTUAL restore into $HERMES_DB (stops the writers first,
#                             keeps a pre-restore safety copy of the current DB). Destructive — asks
#                             to proceed unless --force.
set -euo pipefail

DB="${HERMES_DB:-/opt/hermes/data/hermes.db}"
mode="verify"; src=""; force=0
while [ $# -gt 0 ]; do
  case "$1" in
    --verify) mode="verify"; src="${2:-}"; shift 2;;
    --into)   mode="into";   src="${2:-}"; shift 2;;
    --force)  force=1; shift;;
    *) echo "usage: $0 --verify <backup.db> | --into <backup.db> [--force]"; exit 2;;
  esac
done
[ -n "$src" ] && [ -f "$src" ] || { echo "backup file not found: $src"; exit 1; }

fingerprint() {
  local f="$1"
  echo "  quick_check: $(sqlite3 "$f" 'PRAGMA quick_check;' 2>&1 | head -1)"
  echo "  tables=$(sqlite3 "$f" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")"
  for t in provenance_knowable credibility_series insider_events momentum_scan v1_tenants; do
    n=$(sqlite3 "$f" "SELECT COUNT(*) FROM $t;" 2>/dev/null || echo "n/a")
    echo "  $t=$n"
  done
}

echo "== backup fingerprint: $src =="
fingerprint "$src"
chk=$(sqlite3 "$src" 'PRAGMA quick_check;' 2>&1 | head -1)
[ "$chk" = "ok" ] || { echo "REFUSING: backup failed quick_check ($chk)"; exit 3; }

if [ "$mode" = "verify" ]; then
  echo "VERIFY OK — $src is structurally sound and restorable."
  exit 0
fi

# --- actual restore ---
if [ "$force" -ne 1 ]; then
  echo "About to OVERWRITE $DB with $src. Re-run with --force to proceed."; exit 4
fi
echo "stopping writers (api + telegram) so nothing holds the DB open…"
systemctl stop hermes-api hermes-telegram 2>/dev/null || true
safety="$DB.pre-restore-$(date -u +%Y%m%d-%H%M%S)"
echo "keeping pre-restore safety copy: $safety"
cp -a "$DB" "$safety"
cp -a "$src" "$DB"
# drop any stale WAL/SHM from the replaced file
rm -f "$DB-wal" "$DB-shm"
echo "restarting services…"
systemctl start hermes-api hermes-telegram 2>/dev/null || true
echo "RESTORE COMPLETE from $src. Pre-restore copy at $safety (delete once verified healthy)."
