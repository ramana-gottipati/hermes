#!/usr/bin/env bash
# Install / update the Hermes news + screening + candidates feature.
#
# What this installs:
#   1. hermes-telegram.service  (already from main bootstrap) — Telegram bot
#   2. hermes-news.timer/service — hourly news poller + Stage 1 screen
#   3. hermes-digest.timer/service — twice-daily Telegram digest of screen candidates
#   4. hermes-api.service — FastAPI on :8000 serving /candidates web page
#
# Usage (on the VPS, as root):
#   wget -qO /tmp/setup-news.sh https://raw.githubusercontent.com/ramana-gottipati/hermes/main/scripts/setup-news.sh
#   bash /tmp/setup-news.sh

set -euo pipefail

TARGET="/opt/hermes"
NEWS_TIMER="hermes-news.timer"
NEWS_SERVICE="hermes-news.service"
DIGEST_TIMER="hermes-digest.timer"
DIGEST_SERVICE="hermes-digest.service"
API_SERVICE="hermes-api.service"

echo ""
echo "============================================================"
echo " Hermes — News + Screen + Candidates Web Page Install"
echo "============================================================"
echo ""

# --- 1. Pull latest code ----------------------------------------------------
echo "==> Pulling latest code"
cd "${TARGET}"
git pull --quiet

# --- 2. Install Python deps -------------------------------------------------
echo "==> Installing/refreshing Python dependencies"
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt --quiet

# --- 3. News service + timer (hourly, weekdays) -----------------------------
echo "==> Writing ${NEWS_SERVICE} + ${NEWS_TIMER}"
cat > "/etc/systemd/system/${NEWS_SERVICE}" <<EOF
[Unit]
Description=Hermes News Feed (one poll cycle)

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.news_feed
StandardOutput=append:/var/log/hermes-news.log
StandardError=append:/var/log/hermes-news.log
EOF

cat > "/etc/systemd/system/${NEWS_TIMER}" <<EOF
[Unit]
Description=Hermes News Feed hourly poller
Requires=${NEWS_SERVICE}

[Timer]
# UTC. India is UTC+5:30.
# 01:00–16:00 UTC = 06:30–21:30 IST. Mon-Fri.
OnCalendar=Mon..Fri *-*-* 01..16:00:00
Persistent=false
Unit=${NEWS_SERVICE}

[Install]
WantedBy=timers.target
EOF

# --- 4. Digest service + timer (8:30 AM and 4:30 PM IST) -------------------
echo "==> Writing ${DIGEST_SERVICE} + ${DIGEST_TIMER}"
cat > "/etc/systemd/system/${DIGEST_SERVICE}" <<EOF
[Unit]
Description=Hermes patearn Screen Digest (one run)

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.digest
StandardOutput=append:/var/log/hermes-digest.log
StandardError=append:/var/log/hermes-digest.log
EOF

cat > "/etc/systemd/system/${DIGEST_TIMER}" <<EOF
[Unit]
Description=Hermes Digest Timer
Requires=${DIGEST_SERVICE}

[Timer]
# 8:30 AM IST and 4:30 PM IST = 03:00 UTC and 11:00 UTC
OnCalendar=Mon..Fri *-*-* 03:00:00
OnCalendar=Mon..Fri *-*-* 11:00:00
Persistent=true
Unit=${DIGEST_SERVICE}

[Install]
WantedBy=timers.target
EOF

# --- 5. FastAPI service for /candidates web page ---------------------------
echo "==> Writing ${API_SERVICE} (FastAPI on :8000)"
cat > "/etc/systemd/system/${API_SERVICE}" <<EOF
[Unit]
Description=Hermes FastAPI (candidates web page)
After=network.target

[Service]
Type=simple
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/hermes-api.log
StandardError=append:/var/log/hermes-api.log

[Install]
WantedBy=multi-user.target
EOF

# --- 6. Activate everything --------------------------------------------------
systemctl daemon-reload
systemctl enable --quiet "${NEWS_TIMER}" "${DIGEST_TIMER}" "${API_SERVICE}"
systemctl restart "${API_SERVICE}"
systemctl start "${NEWS_TIMER}" "${DIGEST_TIMER}"

# --- 7. Restart bot to pick up command changes ------------------------------
if systemctl list-unit-files | grep -q "^hermes-telegram.service"; then
    echo "==> Restarting hermes-telegram"
    systemctl restart hermes-telegram.service
fi

sleep 2

# --- 8. Report ---------------------------------------------------------------
PUBLIC_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo " Done."
echo "------------------------------------------------------------"
echo " Services running:"
echo "   - hermes-telegram.service (the bot itself)"
echo "   - hermes-api.service (FastAPI on :8000)"
echo "   - hermes-news.timer (hourly news + Stage 1 screen)"
echo "   - hermes-digest.timer (digest at 08:30 + 16:30 IST)"
echo ""
echo " 🌐 Candidates page: http://${PUBLIC_IP}:8000/candidates"
echo "    (Bookmark this on your phone + laptop)"
echo ""
echo " Telegram commands:"
echo "   /patearn_here  — register this chat for the digest"
echo "   /analyze TICKER — manual deep analysis (Haiku, cheap)"
echo "   /news          — manual news pull"
echo "   /watchlist     — list watched stocks (optional priority list)"
echo ""
echo " Logs:"
echo "   journalctl -u hermes-api -f"
echo "   tail -f /var/log/hermes-news.log"
echo "   tail -f /var/log/hermes-digest.log"
echo "============================================================"
echo ""
