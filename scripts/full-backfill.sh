#!/usr/bin/env bash
# Full 5-year backfill: bhav copy (with delivery) + corporate actions + signals.
#
# Run on VPS as root. Takes ~45-60 minutes. Idempotent — safe to re-run if
# interrupted (it skips already-ingested dates).
#
# Usage:
#   bash /opt/hermes/scripts/full-backfill.sh
#
# Or in the background so you can disconnect:
#   nohup bash /opt/hermes/scripts/full-backfill.sh > /var/log/hermes-backfill.log 2>&1 &
#   tail -f /var/log/hermes-backfill.log

set -euo pipefail

TARGET="/opt/hermes"
DAYS=${1:-1830}  # default 5 years

cd "${TARGET}"
# shellcheck disable=SC1091
source .venv/bin/activate

echo ""
echo "============================================================"
echo " Hermes — Full Historical Backfill"
echo " Span: ${DAYS} calendar days"
echo " Start: $(date)"
echo "============================================================"
echo ""

echo "==> [1/3] Bhav copy backfill (sec_bhavdata_full + fallbacks)"
echo "    Expect ~30-40 minutes."
python -m src.automation.bhavcopy --backfill "${DAYS}"

echo ""
echo "==> [2/3] Corporate actions (splits, bonuses, dividends, rights)"
echo "    Expect ~30 seconds."
python -m src.automation.corp_actions

echo ""
echo "==> [3/3] Rolling signal computation (delivery_value_per_trade, power deliveries)"
echo "    Expect ~10-15 minutes for 5 years of dates."
python -m src.automation.signals --backfill

echo ""
echo "============================================================"
echo " Done: $(date)"
echo "============================================================"
echo ""

echo "Verification queries:"
sqlite3 "${TARGET}/data/hermes.db" <<EOF
.headers on
.mode column

SELECT COUNT(DISTINCT trade_date) AS days,
       COUNT(DISTINCT symbol) AS stocks,
       COUNT(*) AS total_rows,
       SUM(CASE WHEN deliv_qty IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_delivery
FROM bhavcopy_rows WHERE series = 'EQ';

SELECT action_type, COUNT(*) AS rows FROM corporate_actions GROUP BY action_type;

SELECT COUNT(DISTINCT trade_date) AS signal_days,
       COUNT(DISTINCT symbol) AS signal_stocks,
       COUNT(*) AS total_signals
FROM stock_signals;
EOF

echo ""
echo "Local backup command (run on your laptop, not here):"
echo "  scp -r root@$(curl -s --max-time 3 ifconfig.me 2>/dev/null):/opt/hermes/data/ ./hermes-data-backup/"
echo ""
