#!/usr/bin/env bash
# Install / update the Hermes GLM-5.2 code reviewer (report-only).
#
# Additive + idempotent. Does NOT `git pull` — the module is delivered via scp,
# matching the VPS deploy reality (dirty tree, HEAD behind). It only writes its
# own two systemd units and enables the timer; it touches nothing else.
#
# Prereqs on the VPS (as root):
#   1. /opt/hermes/src/automation/code_review.py present  (scp it first)
#   2. GLM_API_KEY=... added to /opt/hermes/.env
#      (create a key at https://z.ai/manage-apikey — GLM Coding Plan / free quota)
#
# Usage on VPS (as root):
#   bash /opt/hermes/scripts/setup-code-review.sh
set -euo pipefail
TARGET="/opt/hermes"

echo "==> Writing hermes-code-review.service + .timer (nightly, report-only)"
cat > /etc/systemd/system/hermes-code-review.service <<EOF
[Unit]
Description=Hermes GLM-5.2 code reviewer (report-only) -> Telegram

[Service]
Type=oneshot
WorkingDirectory=${TARGET}
ExecStart=${TARGET}/.venv/bin/python -m src.automation.code_review
StandardOutput=append:/var/log/hermes-code-review.log
StandardError=append:/var/log/hermes-code-review.log
EOF

cat > /etc/systemd/system/hermes-code-review.timer <<EOF
[Unit]
Description=Hermes Code Review Timer (nightly, report-only)
Requires=hermes-code-review.service

[Timer]
# 02:30 IST = 21:00 UTC, daily.
OnCalendar=*-*-* 21:00:00
Persistent=true
Unit=hermes-code-review.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --quiet hermes-code-review.timer
systemctl start hermes-code-review.timer

echo ""
echo "============================================================"
echo " Hermes code reviewer installed (report-only)."
echo "------------------------------------------------------------"
if grep -q '^GLM_API_KEY=.\+' "${TARGET}/.env" 2>/dev/null; then
  echo " GLM_API_KEY: found in .env ✓"
else
  echo " GLM_API_KEY: NOT set in ${TARGET}/.env  ⚠  (reviewer will no-op until added)"
  echo "   Get a key: https://z.ai/manage-apikey  then add:  GLM_API_KEY=..."
fi
echo ""
echo " Next scheduled run:"
systemctl list-timers hermes-code-review.timer --no-pager 2>/dev/null || true
echo ""
echo " Test now (writes a report + sends Telegram):"
echo "   systemctl start hermes-code-review.service && tail -n 40 /var/log/hermes-code-review.log"
echo " Dry run (review + print, no Telegram):"
echo "   cd ${TARGET} && .venv/bin/python -m src.automation.code_review --dry-run"
echo "============================================================"
