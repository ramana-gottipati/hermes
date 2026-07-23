#!/usr/bin/env bash
# EMA-crossover forward-test QUARTERLY checkpoint (S-EMA, 2026-07-23).
# Runs the sealed-family forward runner (ema_crossover_forward --rebuild: refreshes the three
# research books from current data, then reports), logs the full battery, and DMs a concise verdict
# to the Hermes Telegram owner. Reporting-only; read-only except the runner's own research-table
# rebuild; it never trades. Fired by hermes-ema-forward.timer (3rd of Jan/Apr/Jul/Oct, 09:00 IST).
set -uo pipefail
cd /opt/hermes || exit 1
export PYTHONPATH=/opt/hermes:/opt/hermes/research
LOG=/var/log/hermes-ema-forward.log
TS=$(date -u +%FT%TZ)

OUT=$(/opt/hermes/.venv-research/bin/python -m explosive_moves.ema_crossover_forward --rebuild 2>&1)
printf '\n===== %s =====\n%s\n' "$TS" "$OUT" >> "$LOG"

# integrity gate: any seal BROKEN or in-sample anchor DRIFT means the code/archive was edited
if printf '%s' "$OUT" | grep -qE 'BROKEN|DRIFT'; then GATE="FAIL — STOP (seal/anchor moved)"; else GATE="OK"; fi
KEY=$(printf '%s' "$OUT" | grep -E 'FORWARD WINDOW|C1 beat|INTERIM [0-9]|GRADUATE|DESCRIPTIVE-ONLY|cum |ann ' | head -24)
MSG=$(printf '<b>EMA-crossover forward checkpoint</b>  %s\nintegrity gate: <b>%s</b>\n\n<pre>%s</pre>\n\n<i>read: the crossover (MOM+REV) is expected to produce nothing fundable; LOW = non-crossover book-to-beat</i>' "$TS" "$GATE" "$KEY")

# send to the owner (first allowed user id) via the Hermes bot — same Bot API as digest.py
TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' /opt/hermes/.env | head -1 | cut -d= -f2-)
CHAT=$(grep -E '^TELEGRAM_ALLOWED_USER_IDS=' /opt/hermes/.env | head -1 | cut -d= -f2- | tr -d ' "' | cut -d, -f1)
if [ -n "${TOKEN:-}" ] && [ -n "${CHAT:-}" ]; then
    RESP=$(curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${CHAT}" \
        --data-urlencode "parse_mode=HTML" \
        --data-urlencode "text=${MSG}")
    printf '[telegram -> %s] %s\n' "$CHAT" "$(printf '%s' "$RESP" | head -c 200)" >> "$LOG"
else
    printf '[telegram creds missing in .env — send skipped]\n' >> "$LOG"
fi
