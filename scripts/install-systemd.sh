#!/usr/bin/env bash
# AUD-27: the hermes*/nous-hermes* units in /etc/systemd/system are GIT-OWNED.
# Source of truth = scripts/systemd/vps-live/ (captured verbatim FROM the live box
# on 2026-07-03 — including the 13-step bhavcopy chain drop-ins and the api bind
# override — then evolved in git; AUD-30/31/35 hardening lives in 90-hardening.conf
# drop-ins). Run ON the VPS:
#   bash install-systemd.sh --check    # drift report (repo vs /etc), exit 1 on drift
#   bash install-systemd.sh --install  # copy repo -> /etc + daemon-reload
# This script NEVER enables or starts anything: starting a hermes timer fires its
# job immediately (AUD-95). Enable/start remain deliberate human actions.
set -euo pipefail

mode="${1:---check}"
SRC="${2:-/opt/hermes/scripts/systemd/vps-live}"
DST=/etc/systemd/system
drift=0

# repo -> /etc : missing or different files
while IFS= read -r -d '' f; do
  rel="${f#"$SRC"/}"
  if ! diff -q "$f" "$DST/$rel" >/dev/null 2>&1; then
    echo "DRIFT: $rel"
    drift=1
    if [ "$mode" = "--install" ]; then
      mkdir -p "$DST/$(dirname "$rel")"
      install -m 0644 "$f" "$DST/$rel"
      echo "  -> installed"
    fi
  fi
done < <(find "$SRC" -type f -print0)

# /etc -> repo : live unit files never captured (the AUD-27 failure mode itself)
while IFS= read -r -d '' f; do
  rel="${f#"$DST"/}"
  case "$rel" in *.bak.*|*.bak-*) continue ;; esac
  [ -f "$SRC/$rel" ] || { echo "UNCAPTURED (live-only): $rel"; drift=1; }
done < <(find "$DST" -maxdepth 2 -type f \( -path "$DST/hermes*" -o -path "$DST/nous-hermes*" \) -print0)

if [ "$mode" = "--install" ]; then
  systemctl daemon-reload
  echo "daemon-reload done"
  exit 0
fi
exit "$drift"
