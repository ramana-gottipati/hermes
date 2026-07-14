#!/usr/bin/env bash
# Phase-3 universe backfill driver (docs/fundamentals-xbrl-phase3-backfill.md).
#
# Repeatedly runs ONE bounded, throttle-safe backfill batch, pausing between batches to
# let NSE's per-session throttle reset, until the addressable queue drains (a batch that
# attempts 0 symbols). Every batch is gate-guarded, period-floored (pre-2018 stays frozen
# Screener) and seen-table resumable, so this loop is safe to kill and restart anytime —
# no state is lost, already-migrated periods are cheap-skipped.
#
# Usage:  bash fundamentals_backfill_loop.sh [TIER] [LIMIT] [PAUSE_SECS] [MAX_BATCHES]
#   TIER         1 (NSE-indexed) | 2 | both (omit/any other).  Default: both
#   LIMIT        symbols per batch.                             Default: 50
#   PAUSE_SECS   sleep between batches (throttle reset).        Default: 900
#   MAX_BATCHES  safety cap.                                    Default: 70
set -uo pipefail
PY=/opt/hermes/.venv/bin/python
cd /opt/hermes
TIER="${1:-both}"; LIMIT="${2:-50}"; PAUSE="${3:-900}"; MAX="${4:-70}"
tierflag=""; { [ "$TIER" = "1" ] || [ "$TIER" = "2" ]; } && tierflag="--tier $TIER"

echo "=== backfill loop START $(date -u '+%F %T') tier=$TIER limit=$LIMIT pause=${PAUSE}s max=$MAX ==="
for i in $(seq 1 "$MAX"); do
  echo "--- batch $i/$MAX @ $(date -u +%H:%M:%S) ---"
  out=$($PY -m src.automation.fundamentals_xbrl --backfill $tierflag --limit "$LIMIT" 2>&1 | tail -3)
  echo "$out"
  if echo "$out" | grep -q "'attempted': 0"; then
    echo "queue drained — nothing left to migrate for tier=$TIER."; break
  fi
  [ "$i" -lt "$MAX" ] && sleep "$PAUSE"
done
echo "=== backfill loop END $(date -u '+%F %T') ==="
$PY -m src.automation.fundamentals_xbrl --backfill-status 2>/dev/null || true
