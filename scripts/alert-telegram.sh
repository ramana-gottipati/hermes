#!/usr/bin/env bash
# AUD-26 minimal pager: Telegram-DM Ramana when a season-critical hermes unit fails.
# Invoked by the systemd template hermes-alert@.service via OnFailure=hermes-alert@%n.service
# ($1 = the failed unit's full name). Reads the bot token + first allowed user id from
# /opt/hermes/.env (grep-parsed — .env is not systemd-EnvironmentFile-safe).
# ALWAYS exits 0: a failing pager must never cascade into more unit failures.
set -u
UNIT="${1:-unknown-unit}"
ENVF=/opt/hermes/.env
TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENVF" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
IDS=$(grep -E '^TELEGRAM_ALLOWED_USER_IDS=' "$ENVF" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
CHAT="${IDS%%,*}"
if [ -z "${TOKEN}" ] || [ -z "${CHAT}" ]; then
  echo "hermes-alert: missing TELEGRAM_BOT_TOKEN or chat id in ${ENVF}" >&2
  exit 0
fi
TEXT="🚨 hermes unit FAILED: ${UNIT}
host: $(hostname)  time: $(date -u +%FT%TZ)
inspect: journalctl -u ${UNIT} -n 50"
if curl -sS -m 10 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
     --data-urlencode "chat_id=${CHAT}" --data-urlencode "text=${TEXT}" >/dev/null; then
  echo "hermes-alert: paged ${CHAT} for ${UNIT}"
else
  echo "hermes-alert: telegram send FAILED for ${UNIT}" >&2
fi
exit 0
