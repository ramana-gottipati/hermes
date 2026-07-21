#!/usr/bin/env bash
# AUD-26 minimal pager: Telegram-DM Ramana when a season-critical hermes unit fails.
# Invoked by the systemd template hermes-alert@.service via OnFailure=hermes-alert@%n.service
# ($1 = the failed unit's full name). Reads the bot token + first allowed user id from
# /opt/hermes/.env (grep-parsed — .env is not systemd-EnvironmentFile-safe).
# ALWAYS exits 0: a failing pager must never cascade into more unit failures.
set -u
# Two invocation modes:
#   (1) OnFailure pager (default): $1 = the failed unit's full name (AUD-26, unchanged).
#   (2) custom text: `--text "<msg>"` DMs <msg> verbatim — used by data_quality's seal-break
#       alert (a broken pre-reg/frozen-family seal is a WARN, so it never fails a unit and the
#       systemd OnFailure never fires on it). The template still calls this with just %n, so
#       mode (1) is fully backward-compatible.
if [ "${1:-}" = "--text" ]; then
  MODE="text"; MSG="${2:-}"
else
  MODE="unit"; UNIT="${1:-unknown-unit}"
fi
ENVF=/opt/hermes/.env
TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENVF" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
IDS=$(grep -E '^TELEGRAM_ALLOWED_USER_IDS=' "$ENVF" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
CHAT="${IDS%%,*}"
if [ -z "${TOKEN}" ] || [ -z "${CHAT}" ]; then
  echo "hermes-alert: missing TELEGRAM_BOT_TOKEN or chat id in ${ENVF}" >&2
  exit 0
fi
if [ "${MODE}" = "text" ]; then
  TEXT="${MSG}"; LABEL="seal-integrity"
else
  TEXT="🚨 hermes unit FAILED: ${UNIT}
host: $(hostname)  time: $(date -u +%FT%TZ)
inspect: journalctl -u ${UNIT} -n 50"
  LABEL="${UNIT}"
fi
RESP=$(curl -sS -m 10 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
     --data-urlencode "chat_id=${CHAT}" --data-urlencode "text=${TEXT}" 2>/dev/null)
RC=$?
# Self-verify delivery: curl exit 0 is NOT proof — Telegram returns {"ok":false,...} (HTTP 200) on a
# bad token / blocked chat / rate-limit, and curl (no -f) still exits 0. Parse the ok flag so a SILENT
# non-delivery is logged loudly (journald) with the API reason, not falsely reported as "paged".
# Still ALWAYS exit 0 (a failing pager must never cascade into more unit failures — AUD-26).
if [ "${RC}" -ne 0 ]; then
  echo "hermes-alert: telegram TRANSPORT FAILED (curl rc=${RC}) for ${LABEL}" >&2
elif printf '%s' "${RESP}" | grep -q '"ok":true'; then
  MID=$(printf '%s' "${RESP}" | grep -oE '"message_id":[0-9]+' | head -1 | cut -d: -f2)
  echo "hermes-alert: paged ${CHAT} for ${LABEL} (message_id ${MID:-?})"
else
  DESC=$(printf '%s' "${RESP}" | grep -oE '"description":"[^"]*"' | head -1)
  echo "hermes-alert: telegram REJECTED for ${LABEL}: ${DESC:-${RESP}}" >&2
fi
exit 0
