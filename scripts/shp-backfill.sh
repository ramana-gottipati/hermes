#!/usr/bin/env bash
# One-shot SHP XBRL backfill (S77b): ingest the shareholding-pattern broadcasts the
# nightly 7-day window never saw (feed went live ~Jun-25; the Mar-2026-quarter
# filings broadcast Apr..May cover most of the universe, incl. Promoter Pledge).
#
# Safe to re-run to completion: shareholding_gg_seen skips fetched filings, the
# 6-consecutive-failure breaker aborts cleanly when nsearchives throttles (~1k
# downloads), and each --ingest chunk ends with the pledge->fundamentals sync.
# Run:  nohup bash /opt/hermes/scripts/shp-backfill.sh > /var/log/hermes-shp-backfill.log 2>&1 &
set -uo pipefail
cd /opt/hermes

for W in "2026-04-01 2026-04-15" "2026-04-16 2026-04-30" \
         "2026-05-01 2026-05-15" "2026-05-16 2026-05-31" "2026-06-01 2026-06-24"; do
  set -- $W
  echo "=== chunk $1 .. $2 === $(date -u +%FT%TZ)"
  .venv/bin/python -m src.automation.shareholding_xbrl --ingest --since "$1" --until "$2"
done

echo "=== final coverage === $(date -u +%FT%TZ)"
sqlite3 data/research.db "SELECT COUNT(DISTINCT symbol) AS pledge_syms FROM shareholding_history WHERE metric='Promoter Pledge';
SELECT COUNT(DISTINCT symbol) AS shp_xbrl_syms FROM shareholding_history WHERE source='NSE-XBRL-SHP';"
sqlite3 data/hermes.db "SELECT COUNT(*) AS fund_rows, SUM(promoter_pledge IS NOT NULL) AS pledge_filled FROM fundamentals;"
