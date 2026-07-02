#!/usr/bin/env bash
# AUD-02: PROVE the backups restore. Rebuilds a scratch DB from the newest
# nightly artifacts and sanity-checks integrity + key non-derivable tables.
# Run after backup-db.sh; exits non-zero (and says FAIL) on any problem.
set -euo pipefail

DEST=/opt/hermes/backups/db
TMP=$(mktemp -d /tmp/hermes-restore-test.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

DUMP=$(ls -1t "$DEST"/hermes-tables-*.sql.gz | head -1)
RES=$(ls -1t "$DEST"/research-*.db | head -1)
echo "[restore-test] dump: $DUMP"
echo "[restore-test] research copy: $RES"

# 1) hermes tables dump -> fresh DB
zcat "$DUMP" | sqlite3 "$TMP/hermes-restored.db"
IC=$(sqlite3 "$TMP/hermes-restored.db" "PRAGMA integrity_check;")
[ "$IC" = "ok" ] || { echo "[restore-test] FAIL: integrity_check=$IC"; exit 1; }
for t in conversations concall_scores fundamentals pattern_scores; do
  n=$(sqlite3 "$TMP/hermes-restored.db" "SELECT COUNT(*) FROM $t;")
  echo "[restore-test] restored $t: $n rows"
  [ "$n" -gt 0 ] || { echo "[restore-test] FAIL: $t empty"; exit 1; }
done

# 2) research.db VACUUM copy is a healthy database
IC=$(sqlite3 "file:$RES?mode=ro" "PRAGMA integrity_check;")
[ "$IC" = "ok" ] || { echo "[restore-test] FAIL: research integrity_check=$IC"; exit 1; }
n=$(sqlite3 "file:$RES?mode=ro" "SELECT COUNT(*) FROM shareholding_history;")
echo "[restore-test] research shareholding_history: $n rows"
[ "$n" -gt 0 ] || { echo "[restore-test] FAIL: shareholding_history empty"; exit 1; }

echo "[restore-test] PASS"
