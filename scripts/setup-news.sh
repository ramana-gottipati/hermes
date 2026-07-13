#!/usr/bin/env bash
# Hermes FRESH-BOOTSTRAP installer (deps + systemd units).
#
# ⚠️ AUD-28 (2026-07-13): this script used to WRITE every unit from inline heredocs. Those
# heredocs had drifted from the live box (missing the hermes-concalls ExecStartPre, the 13-step
# bhavcopy chain drop-ins, the api bind override, the AUD-30/31/35 hardening drop-ins), so running
# it silently REVERTED live units — the reason it was banned. It also `systemctl start`ed timers,
# firing their jobs immediately (AUD-95). BOTH hazards are removed: unit management is now delegated
# to scripts/install-systemd.sh, whose source of truth is scripts/systemd/vps-live/ (the units
# captured VERBATIM from the box, AUD-27), and which NEVER enables or starts anything.
#
# 🚫 To UPDATE an already-running VPS, do NOT use this script. Use the deploy recipe: scp the changed
#    files + a writer-safe hermes-api restart (PROJECT_STATE / the `vps-deploy-reality` memory). This
#    script is for a FRESH box only; enabling/starting timers stays a deliberate human step (AUD-95).
#
# Fresh-box usage (as root):
#   git clone <repo> /opt/hermes && cd /opt/hermes
#   python3 -m venv .venv && bash scripts/setup-news.sh
#   # then, deliberately, once you have reviewed the timer schedule:
#   bash scripts/install-systemd.sh --check          # confirm repo == /etc, no drift
#   systemctl enable --now hermes-api.service         # the web app
#   systemctl enable hermes-*.timer                   # schedule the jobs (enable, NOT start)

set -euo pipefail

TARGET="/opt/hermes"

echo ""
echo "============================================================"
echo " Hermes — FRESH-BOOTSTRAP install (deps + units, no start)"
echo "============================================================"
echo ""

# --- Deps ------------------------------------------------------------------
echo "==> Installing/refreshing Python dependencies + sqlite3 CLI"
cd "${TARGET}"
apt-get install -y -qq sqlite3 >/dev/null 2>&1 || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt --quiet

# --- Systemd units: install from the GIT-OWNED captured truth ---------------
# AUD-28: no more inline heredocs. install-systemd.sh copies scripts/systemd/vps-live/*
# (units + drop-ins captured verbatim from the box) into /etc + daemon-reload. It NEVER
# enables or starts anything — starting a hermes timer fires its job immediately (AUD-95),
# so enable/start stay deliberate human actions (see the header). Dormant units (e.g. the
# nous-review reviewer, D68) are installed-but-disabled by exactly this never-enable behaviour.
echo "==> Installing systemd units from scripts/systemd/vps-live/ (canonical, drift-checked)"
bash "${TARGET}/scripts/install-systemd.sh" --install

# --- Report -----------------------------------------------------------------
PUBLIC_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo " Units installed (NOT enabled, NOT started — by design, AUD-95)."
echo "------------------------------------------------------------"
echo " Next, DELIBERATELY (after reviewing the schedule):"
echo "   bash ${TARGET}/scripts/install-systemd.sh --check     # repo == /etc, no drift"
echo "   systemctl enable --now hermes-api.service              # the FastAPI web app"
echo "   systemctl enable hermes-bhavcopy.timer hermes-news.timer \\"
echo "                    hermes-digest.timer hermes-concalls.timer \\"
echo "                    hermes-concalls-refresh.timer          # schedule (enable, not start)"
echo ""
echo " 🌐 Candidates page (once hermes-api is up): http://${PUBLIC_IP}:8000/candidates"
echo " Backups: scp root@${PUBLIC_IP}:/opt/hermes/data/hermes.db ./hermes-backup.db"
echo "============================================================"
echo ""
