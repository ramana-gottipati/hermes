#!/usr/bin/env bash
# Install / update the Hermes news feature.
#
# Mode: LIVE event-driven push.
#   - Poller runs every 10 min during weekday market hours (7 AM – 10 PM IST)
#   - Each poll: fetch RSS (free), dedupe vs sent_news, classify only new items
#   - Posts to registered destinations only when there is signal-worthy content
#   - /news command also works for on-demand pulls
#
# Usage (on the VPS, as root):
#   wget -qO /tmp/setup-news.sh https://raw.githubusercontent.com/ramana-gottipati/hermes/main/scripts/setup-news.sh
#   bash /tmp/setup-news.sh

set -euo pipefail

TARGET="/opt/hermes"
TIMER="hermes-news.timer"
SERVICE="hermes-news.service"

echo ""
echo "============================================================"
echo " Hermes News — Live Poller Install"
echo "============================================================"
echo ""

# --- 1. Stop any previous timer + service so we can rewrite cleanly --------
if systemctl list-unit-files | grep -q "^${TIMER}"; then
    systemctl disable --now "${TIMER}" 2>/dev/null || true
    rm -f "/etc/systemd/system/${TIMER}"
fi
if systemctl list-unit-files | grep -q "^${SERVICE}"; then
    systemctl stop "${SERVICE}" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE}"
fi
systemctl daemon-reload

# --- 2. Pull latest code ----------------------------------------------------
echo "==> Pulling latest code"
cd "${TARGET}"
git pull --quiet

# --- 3. Install Python deps -------------------------------------------------
echo "==> Installing/refreshing Python dependencies"
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt --quiet

# --- 4. Write systemd service (oneshot — runs the news job once per trigger) ---
echo "==> Writing ${SERVICE}"
cat > "/etc/systemd/system/${SERVICE}" <<EOF
[Unit]
Description=Hermes News Feed (one poll cycle)

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.news_feed
StandardOutput=append:/var/log/hermes-news.log
StandardError=append:/var/log/hermes-news.log
EOF

# --- 5. Write systemd timer (live polling cadence) --------------------------
echo "==> Writing ${TIMER} — every 10 min on weekdays during market+evening hours"
cat > "/etc/systemd/system/${TIMER}" <<EOF
[Unit]
Description=Hermes News Feed live poller
Requires=${SERVICE}

[Timer]
# UTC times. India is UTC+5:30.
# Polls every 10 min during 01:00–16:30 UTC = 06:30 IST to 22:00 IST, Mon-Fri.
# Most polls return zero output (no new headlines). You'll only see Telegram
# messages when there is actually new high-signal news.
OnCalendar=Mon..Fri *-*-* 01..16:00/10
Persistent=false
Unit=${SERVICE}

[Install]
WantedBy=timers.target
EOF

# --- 6. Activate ------------------------------------------------------------
systemctl daemon-reload
systemctl enable --quiet "${TIMER}"
systemctl start "${TIMER}"

# --- 7. Restart bot so /news + /news_here commands are loaded ---------------
if systemctl list-unit-files | grep -q "^hermes-telegram.service"; then
    echo "==> Restarting hermes-telegram so new commands load"
    systemctl restart hermes-telegram.service
fi

# --- 8. Report --------------------------------------------------------------
echo ""
echo "============================================================"
echo " Done."
echo "------------------------------------------------------------"
echo " Mode: LIVE. Poller runs every 10 min on weekdays, 06:30–22:00 IST."
echo " Posts ONLY when there is new high-signal content."
echo " Most polls will be silent."
echo ""
echo " Telegram commands:"
echo "   /news        — on-demand pull (forces a fresh brief regardless of dedup)"
echo "   /news_here   — register this chat as a news destination"
echo "   /news_where  — list registered destinations"
echo "   /news_stop   — remove this chat as a destination"
echo ""
echo " Next scheduled run:"
systemctl list-timers "${TIMER}" --no-pager | head -3
echo ""
echo " Live logs:   tail -f /var/log/hermes-news.log"
echo " Force one run now:  systemctl start ${SERVICE}"
echo "============================================================"
echo ""
