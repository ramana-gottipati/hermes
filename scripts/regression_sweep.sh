#!/usr/bin/env bash
# regression_sweep.sh — the DO-NO-HARM harness every parallel lane MUST run after every change.
# Verifies the live VPS still serves every nav route + every chart overlay + healthy units.
# Exit 0 = nothing hampered (safe to commit). Exit 1 = a regression — STOP, fix or revert.
#
# Usage:  bash scripts/regression_sweep.sh            # sweeps the live VPS via `ssh hermes`
#         HOST=local bash scripts/regression_sweep.sh # sweeps http://localhost:8000 directly
set -u

BASE="http://localhost:8000"
run() { if [ "${HOST:-vps}" = "local" ]; then curl -s -o /dev/null -w '%{http_code}' "$BASE$1"; \
        else ssh -o BatchMode=yes hermes "curl -s -o /dev/null -w '%{http_code}' '$BASE$1'"; fi; }

# Every nav route (4 altitudes + every lens + every strategy + Trust/Pat). Add new routes here.
ROUTES="/dash/markets /dash/screener /dash/screen2 /dash/strategies /dash/strategist /dash/dashboard \
/dash/stock /dash/coverage /dash/pat /dash/mep /dash/conviction /dash/cpr /dash/concalls /dash/leaders \
/dash/growth /dash/wolfe /dash/wolfe/scan /dash/rs-hub /dash/rrg /dash/rotation /dash/rsband \
/dash/participants /dash/wire /dash/compare /dash/sectors /dash/themes /dash/workbench /dash/launchpad \
/dash/testing /dash/ratio"

# The chart overlays — the work Ramana most cares about not breaking.
OVERLAYS="/dash/cpr/overlay?sym=ACC /dash/mep/overlay?sym=ACC /dash/rs/overlay?sym=ACC \
/dash/wolfe/overlay?sym=ACC"

fail=0
echo "== health =="
h=$(if [ "${HOST:-vps}" = "local" ]; then echo "n/a"; else ssh -o BatchMode=yes hermes 'systemctl is-active hermes-api'; fi)
echo "  hermes-api: $h"; [ "$h" = "failed" ] && fail=$((fail+1))

echo "== routes (must all be 200) =="
for r in $ROUTES; do c=$(run "$r"); if [ "$c" != "200" ]; then echo "  !! $r -> $c"; fail=$((fail+1)); fi; done

echo "== chart overlays (must all be 200) =="
for o in $OVERLAYS; do c=$(run "$o"); if [ "$c" != "200" ]; then echo "  !! $o -> $c"; fail=$((fail+1)); fi; done

if [ "$fail" -eq 0 ]; then echo "PASS — nothing hampered ($(echo $ROUTES | wc -w) routes + $(echo $OVERLAYS | wc -w) overlays all 200)"; exit 0
else echo "FAIL — $fail regression(s). STOP: fix or revert before committing."; exit 1; fi
