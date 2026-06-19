#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes/Patearn — SQLite maintenance (WAL reclaim + planner-stats refresh).
#
# Run when the DB is IDLE — i.e. between backfill phases, at the end of the
# nightly signal chain, or after a deep-history backfill completes. NOT during
# active heavy writes (a TRUNCATE checkpoint only fully succeeds when no other
# connection holds an older read snapshot).
#
# What it does, and why:
#   1. PRAGMA wal_checkpoint(TRUNCATE) — folds all committed WAL frames back into
#      the main DB and shrinks the -wal file. Under a long backfill with
#      continuous dashboard reads, WAL truncation is deferred and -wal can grow,
#      hurting read locality + disk. This reclaims it. (Audit finding F.)
#   2. PRAGMA optimize — refreshes sqlite_stat1 so the query planner stops
#      mis-choosing low-cardinality indexes (e.g. idx_bhav_series on series='EQ').
#      Cheap + targeted; a brand-new DB benefits from a one-time full ANALYZE
#      (uncomment below) to seed the stats the first time. (Audit finding E.)
#
# Usage:
#   bash scripts/db-maintenance.sh                      # default VPS DB path
#   bash scripts/db-maintenance.sh /path/to/hermes.db   # explicit path
#   HERMES_PY=/usr/bin/python3 bash scripts/db-maintenance.sh   # override python
#
# Safe to run repeatedly. Read-mostly; the only writes are the checkpoint + stats.
# Wire into cron or the end of the nightly chain once validated.
# ---------------------------------------------------------------------------
set -euo pipefail

DB="${1:-/opt/hermes/data/hermes.db}"
PY="${HERMES_PY:-/opt/hermes/.venv/bin/python}"

if [ ! -f "$DB" ]; then
  echo "db-maintenance: DB not found at $DB" >&2
  exit 1
fi
if [ ! -x "$PY" ]; then
  # Fall back to whatever python3 is on PATH if the venv isn't where expected.
  PY="$(command -v python3 || command -v python)"
fi

"$PY" - "$DB" <<'PYEOF'
import os, sys, sqlite3

db = sys.argv[1]
wal = db + "-wal"
before = os.path.getsize(wal) / 1024 / 1024 if os.path.exists(wal) else 0.0

conn = sqlite3.connect(db)
# busy_timeout so we wait out brief contention instead of erroring mid-write.
conn.execute("PRAGMA busy_timeout = 10000")

busy, log_frames, ckpt_frames = conn.execute(
    "PRAGMA wal_checkpoint(TRUNCATE)"
).fetchone()
# busy=1 means another connection held an older snapshot and the -wal could not
# be fully truncated — re-run when more idle. log_frames is the WAL size in
# frames before the checkpoint; ckpt_frames is how many were folded back.
print(f"wal_checkpoint(TRUNCATE): busy={busy} log_frames={log_frames} checkpointed={ckpt_frames}")

# First-time stats seeding (slow on a multi-million-row DB; run once when idle):
# conn.execute("ANALYZE")
conn.execute("PRAGMA optimize")
conn.commit()

after = os.path.getsize(wal) / 1024 / 1024 if os.path.exists(wal) else 0.0
print(f"-wal: {before:.2f} MB -> {after:.2f} MB")
conn.close()
PYEOF

echo "db-maintenance: done on $DB"
