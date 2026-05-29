#!/usr/bin/env bash
# Install / update the Hermes data-driven patearn pipeline.
#
# Services / timers installed:
#   - hermes-telegram.service   (already from main bootstrap) — the bot itself
#   - hermes-api.service        — FastAPI on :8000 serving /candidates page
#   - hermes-news.timer/service — earnings news poller (twice daily, weekdays)
#   - hermes-bhavcopy.timer/service — NSE bhav copy fetcher (daily, weekday evenings)
#   - hermes-digest.timer/service   — twice-daily Telegram digest
#
# Usage on VPS (as root):
#   wget -qO /tmp/setup-news.sh https://raw.githubusercontent.com/ramana-gottipati/hermes/main/scripts/setup-news.sh
#   bash /tmp/setup-news.sh

set -euo pipefail

TARGET="/opt/hermes"

echo ""
echo "============================================================"
echo " Hermes — data-driven patearn pipeline install"
echo "============================================================"
echo ""

# --- Pull latest code ------------------------------------------------------
echo "==> Pulling latest code"
cd "${TARGET}"
git pull --quiet

# --- Install deps ----------------------------------------------------------
echo "==> Installing/refreshing Python dependencies + sqlite3 CLI"
apt-get install -y -qq sqlite3 >/dev/null 2>&1 || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt --quiet

# --- News poller (twice daily — earnings trigger) --------------------------
echo "==> Writing hermes-news.service + .timer (twice daily, weekdays)"
cat > /etc/systemd/system/hermes-news.service <<EOF
[Unit]
Description=Hermes News Feed (catches earnings announcements)

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.news_feed
StandardOutput=append:/var/log/hermes-news.log
StandardError=append:/var/log/hermes-news.log
EOF
cat > /etc/systemd/system/hermes-news.timer <<EOF
[Unit]
Description=Hermes News Feed (twice daily)
Requires=hermes-news.service

[Timer]
# 9:00 AM IST and 5:00 PM IST = 03:30 UTC and 11:30 UTC
OnCalendar=Mon..Fri *-*-* 03:30:00
OnCalendar=Mon..Fri *-*-* 11:30:00
Persistent=true
Unit=hermes-news.service

[Install]
WantedBy=timers.target
EOF

# --- Bhav copy fetcher (daily, weekday evenings) ---------------------------
echo "==> Writing hermes-bhavcopy.service + .timer"
cat > /etc/systemd/system/hermes-bhavcopy.service <<EOF
[Unit]
Description=Hermes NSE Bhav Copy fetcher

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.bhavcopy
StandardOutput=append:/var/log/hermes-bhavcopy.log
StandardError=append:/var/log/hermes-bhavcopy.log
EOF
cat > /etc/systemd/system/hermes-bhavcopy.timer <<EOF
[Unit]
Description=Hermes Bhav Copy Timer
Requires=hermes-bhavcopy.service

[Timer]
# 7:30 PM IST = 14:00 UTC, Mon-Fri.
# Rationale: NSE market closes 3:30 PM IST. sec_bhavdata_full with delivery
# can lag basic bhav copy by 1-2 hours depending on settlement processing.
# 7:30 PM gives a 4-hour buffer post-close — ~99% reliable.
OnCalendar=Mon..Fri *-*-* 14:00:00
Persistent=true
Unit=hermes-bhavcopy.service

[Install]
WantedBy=timers.target
EOF

# --- Digest (twice daily) ---------------------------------------------------
echo "==> Writing hermes-digest.service + .timer"
cat > /etc/systemd/system/hermes-digest.service <<EOF
[Unit]
Description=Hermes patearn Candidate Digest

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.digest
StandardOutput=append:/var/log/hermes-digest.log
StandardError=append:/var/log/hermes-digest.log
EOF
cat > /etc/systemd/system/hermes-digest.timer <<EOF
[Unit]
Description=Hermes Digest Timer
Requires=hermes-digest.service

[Timer]
# 10:00 AM IST and 6:00 PM IST = 04:30 UTC and 12:30 UTC
OnCalendar=Mon..Fri *-*-* 04:30:00
OnCalendar=Mon..Fri *-*-* 12:30:00
Persistent=true
Unit=hermes-digest.service

[Install]
WantedBy=timers.target
EOF

# --- FastAPI service (candidates web page) ----------------------------------
echo "==> Writing hermes-api.service (FastAPI on :8000)"
cat > /etc/systemd/system/hermes-api.service <<EOF
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

# --- Activate ---------------------------------------------------------------
systemctl daemon-reload
systemctl enable --quiet hermes-news.timer hermes-bhavcopy.timer hermes-digest.timer hermes-api.service
systemctl restart hermes-api.service
systemctl start hermes-news.timer hermes-bhavcopy.timer hermes-digest.timer

# --- Restart bot ------------------------------------------------------------
if systemctl list-unit-files | grep -q "^hermes-telegram.service"; then
    echo "==> Restarting hermes-telegram"
    systemctl restart hermes-telegram.service
fi

# --- Backfill: try one bhav copy now so user sees data tonight -------------
echo "==> Running one bhav copy fetch now (silently — check log if interested)"
systemctl start hermes-bhavcopy.service || true

# --- Report -----------------------------------------------------------------
PUBLIC_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo " Done."
echo "------------------------------------------------------------"
echo " Mode: data-driven (no LLM in screening loop)."
echo ""
echo " Schedule:"
echo "   News poller (catches earnings):   9:00 AM + 5:00 PM IST, Mon-Fri"
echo "   Bhav copy fetcher:                6:00 PM IST, Mon-Fri"
echo "   Telegram digest:                  10:00 AM + 6:00 PM IST, Mon-Fri"
echo ""
echo " 🌐 Candidates page: http://${PUBLIC_IP}:8000/candidates"
echo ""
echo " Telegram commands (all FREE except /analyze):"
echo "   /score TICKER   — rule-based score (₹0, no LLM)"
echo "   /analyze TICKER — LLM analysis (Haiku, ~₹2)"
echo "   /watch TICKER   — add to watchlist"
echo "   /patearn_here   — register chat for digest"
echo "   /news           — manual news pull"
echo ""
echo " Backups: scp root@${PUBLIC_IP}:/opt/hermes/data/hermes.db ./hermes-backup.db"
echo "============================================================"
echo ""
