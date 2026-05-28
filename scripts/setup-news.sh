#!/usr/bin/env bash
# Install / update the on-demand news feature on the VPS.
#
# This script:
#   - Pulls the latest Hermes code
#   - Installs new Python deps
#   - REMOVES any previously-installed news timer (scheduled mode is deprecated;
#     news is now on-demand via the /news Telegram command)
#   - Restarts the Telegram bot so it picks up new commands
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
echo " Hermes News — Update (on-demand mode)"
echo "============================================================"
echo ""

# --- 1. Disable any previously-installed scheduled timer --------------------
if systemctl list-unit-files | grep -q "^${TIMER}"; then
    echo "==> Removing old scheduled timer (news is on-demand now)"
    systemctl disable --now "${TIMER}" 2>/dev/null || true
    rm -f "/etc/systemd/system/${TIMER}"
fi
if systemctl list-unit-files | grep -q "^${SERVICE}"; then
    echo "==> Removing old news service unit (no longer triggered on a schedule)"
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

# --- 4. Restart bot so new commands take effect -----------------------------
if systemctl list-unit-files | grep -q "^hermes-telegram.service"; then
    echo "==> Restarting hermes-telegram so new commands (/news, /news_here, etc.) load"
    systemctl restart hermes-telegram.service
fi

# --- 5. Report ---------------------------------------------------------------
echo ""
echo "============================================================"
echo " Done."
echo "------------------------------------------------------------"
echo " News is now ON-DEMAND. No scheduled pushes."
echo ""
echo " In Telegram (the chat where you want news to land):"
echo "   /news        — fetch a fresh market brief right now"
echo "   /news_here   — register this chat as a news destination (optional)"
echo "   /news_where  — list registered destinations"
echo "   /news_stop   — remove this chat as a destination"
echo ""
echo " Bot logs:    journalctl -u hermes-telegram -f"
echo "============================================================"
echo ""
