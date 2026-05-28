#!/usr/bin/env bash
# Install the Hermes news-feed scheduler on the VPS.
#
# Pulls latest code, installs new Python dep (feedparser), and registers a
# systemd timer that runs the news_feed at 8:30 AM and 4:30 PM IST on weekdays.
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
echo " Hermes News Feed — Install"
echo "============================================================"
echo ""

# --- 1. Pull latest code -----------------------------------------------------
echo "==> Pulling latest code"
cd "${TARGET}"
git pull --quiet

# --- 2. Install Python deps --------------------------------------------------
echo "==> Installing new Python dependencies"
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt --quiet

# --- 3. Write systemd service (oneshot — runs once per trigger) -------------
echo "==> Writing ${SERVICE}"
cat > "/etc/systemd/system/${SERVICE}" <<EOF
[Unit]
Description=Hermes News Feed (one run)

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.news_feed
StandardOutput=append:/var/log/hermes-news.log
StandardError=append:/var/log/hermes-news.log
EOF

# --- 4. Write systemd timer (when to fire) ----------------------------------
echo "==> Writing ${TIMER} — schedule: 8:30 AM and 4:30 PM IST on weekdays"
cat > "/etc/systemd/system/${TIMER}" <<EOF
[Unit]
Description=Hermes News Feed Timer
Requires=${SERVICE}

[Timer]
# Times below are interpreted in the system timezone.
# Hostinger VPS defaults to UTC. 8:30 AM IST = 3:00 UTC; 4:30 PM IST = 11:00 UTC.
OnCalendar=Mon..Fri 03:00:00
OnCalendar=Mon..Fri 11:00:00
Persistent=true
Unit=${SERVICE}

[Install]
WantedBy=timers.target
EOF

# --- 5. Activate -------------------------------------------------------------
echo "==> Activating timer"
systemctl daemon-reload
systemctl enable --quiet "${TIMER}"
systemctl start "${TIMER}"

# --- 5b. Restart the Telegram bot so it picks up new commands (/news_here etc) ---
if systemctl list-unit-files | grep -q "^hermes-telegram.service"; then
    echo "==> Restarting hermes-telegram so it picks up new /news_here commands"
    systemctl restart hermes-telegram.service
fi

# --- 6. Test run now so you see news immediately ----------------------------
echo ""
echo "==> Running once now so you can verify it works (check Telegram)"
systemctl start "${SERVICE}" || true
sleep 3

# --- 7. Report ---------------------------------------------------------------
echo ""
echo "============================================================"
echo " Done."
echo "------------------------------------------------------------"
echo " Timer status:"
systemctl list-timers "${TIMER}" --no-pager | head -4
echo ""
echo " Logs:        tail -f /var/log/hermes-news.log"
echo " Run now:     systemctl start ${SERVICE}"
echo " Disable:     systemctl disable --now ${TIMER}"
echo ""
echo " You should receive a Telegram message in the next few seconds."
echo " If nothing arrives, check /var/log/hermes-news.log for errors."
echo "============================================================"
echo ""
