#!/usr/bin/env bash
# regression_sweep.sh — the DO-NO-HARM harness every parallel lane MUST run after every change.
# Two gates, run in order:
#   1. CHROME gate (clean-checkout, in-process): builds the app from THIS checkout via
#      TestClient and asserts every page carries the v2 chrome markers (uk-skin · v2bar ·
#      Trust · Wire · no .hsearch). Catches a silently-reverted skin/nav that a 200 hides
#      — see scripts/chrome_gate.py. Runs locally, needs no live VPS.
#   2. LIVE-200 sweep: verifies the live VPS still serves every nav route + chart overlay.
# Exit 0 = nothing hampered (safe to commit). Exit 1 = a regression — STOP, fix or revert.
#
# Usage:  bash scripts/regression_sweep.sh             # chrome gate + sweep the live VPS via `ssh hermes`
#         HOST=local bash scripts/regression_sweep.sh  # chrome gate + sweep http://localhost:8000
#         SKIP_CHROME=1 bash scripts/regression_sweep.sh  # live-200 sweep only (no in-process build)
set -u

# Pick the app's python: the first candidate (repo venv first, VPS-style) that can
# actually import fastapi — avoids a bare python3 shim that lacks the app's deps.
_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=""
for _cand in "$_ROOT/.venv/bin/python" python python3; do
  if "$_cand" -c 'import fastapi' >/dev/null 2>&1; then PY="$_cand"; break; fi
done

BASE="http://localhost:8000"
_hit() { if [ "${HOST:-vps}" = "local" ]; then curl -s -o /dev/null -m 12 -w '%{http_code}' "$BASE$1"; \
        else ssh -o BatchMode=yes hermes "curl -s -o /dev/null -m 12 -w '%{http_code}' '$BASE$1'"; fi; }
# Retry once on a non-200 to ride out a deploy-restart window (000/502) — a transient
# restart race is NOT a regression. Only a persistent non-200 counts as a real break.
run() { c=$(_hit "$1"); if [ "$c" != "200" ]; then sleep 3; c=$(_hit "$1"); fi; echo "$c"; }

# Every nav route (4 altitudes + every lens + every strategy + Trust/Pat). Add new routes here.
ROUTES="/dash/markets /dash/screener /dash/screen2 /dash/strategies /dash/strategist /dash/dashboard \
/dash/stock /dash/coverage /dash/replay /dash/pat /dash/mep /dash/conviction /dash/cpr /dash/concalls /dash/leaders \
/dash/growth /dash/wolfe /dash/wolfe/scan /dash/rs-hub /dash/rrg /dash/rotation /dash/rsband \
/dash/participants /dash/wire /dash/compare /dash/sectors /dash/themes /dash/workbench /dash/launchpad \
/dash/testing /dash/ratio /dash/_ui"

# The chart overlays — the work Ramana most cares about not breaking.
OVERLAYS="/dash/cpr/overlay?sym=ACC /dash/mep/overlay?sym=ACC /dash/rs/overlay?sym=ACC \
/dash/wolfe/overlay?sym=ACC /dash/harmonic/overlay?sym=ACC"

fail=0

# ── Gate 0: numeric unit tests on the computational core (AUD-39) ──
# The pixel gates below never catch a wrong sign or off-by-one in scoring/signals/PIT.
# Runs where pytest is installed (VPS venv, CI); SKIPs with a hint otherwise so the
# sweep still works on a box without the dev deps. A test FAILURE fails the sweep.
if [ "${SKIP_PYTEST:-0}" != "1" ]; then
  TPY="$PY"; [ -z "$TPY" ] && TPY="python3"
  if "$TPY" -m pytest --version >/dev/null 2>&1; then
    echo "── Gate 0: pytest (golden tests: scoring, momentum ensemble, …) ──"
    if "$TPY" -m pytest -q "$_ROOT/tests"; then echo "  gate0 pytest: PASS"; else echo "  gate0 pytest: FAIL"; fail=1; fi
  else
    echo "── Gate 0: pytest not installed for $TPY — SKIP (pip install -r requirements-dev.txt) ──"
  fi
fi

# ── Gate 0.5: Pat NL eval battery — compiler/route/explain/hallucination (+accuracy w/ DB) (AUD-40) ──
# The eval battery existed but ran nowhere, so Pat routing/explain regressions shipped silently.
# Requires the app deps to import; SKIP (not fail) if it can't import, FAIL if evals fail.
if [ "${SKIP_PATEVAL:-0}" != "1" ] && [ -n "$PY" ]; then
  if "$PY" -c 'import src.pat.eval_set' >/dev/null 2>&1; then
    echo "── Gate 0.5: pat-eval (Pat NL routing / explain / hallucination + accuracy) ──"
    if "$PY" -m src.pat.eval_set --gate; then
      echo "  gate0.5 pat-eval: PASS"
    elif [ "${PATEVAL_STRICT:-1}" = "0" ]; then
      # Escape hatch (PATEVAL_STRICT=0): surface the regression but don't block — e.g. a local
      # run against a partial dev DB. The nightly VPS timer (hermes-pateval.timer) enforces strict
      # and pages via hermes-alert@ (AUD-26), so a real regression is still caught.
      echo "  gate0.5 pat-eval: FAIL — surfaced (WARN-only; PATEVAL_STRICT=0). Fix before the nightly gate pages."
    else
      # STRICT by default (AUD-40): the ~6-miss baseline (1 route + 5 explain) is CLEARED, so any
      # gate failure is a NEW regression in Pat routing / explain / hallucination / accuracy.
      echo "  gate0.5 pat-eval: FAIL (strict — a Pat routing/explain/accuracy eval regressed)"; fail=1
    fi
  else
    echo "── Gate 0.5: pat-eval can't import (missing app deps for $PY) — SKIP ──"
  fi
fi

# ── Gate 1: clean-checkout chrome contract (in-process TestClient, no live VPS) ──
if [ "${SKIP_CHROME:-0}" != "1" ]; then
  echo "== chrome gate (clean-checkout TestClient — uk-skin/v2bar/Trust/Wire/no .hsearch) =="
  if [ -z "$PY" ]; then
    echo "  ~~ SKIPPED: no python with fastapi found (set up the venv to enable the chrome gate)"
  elif "$PY" "$_ROOT/scripts/chrome_gate.py"; then :; else
    echo "  !! chrome gate FAILED — v2 chrome regressed in this checkout"
    fail=$((fail+1))
  fi
fi

# ── Gate 1b: nav-integrity contract (no dead links / orphans / duplicate sub-nav) ──
# chrome_gate proves the right chrome is served; this proves the nav GRAPH is coherent
# with the route table — catches the duplicate-sub-nav and orphan/dead-link classes a
# 200 (and a presence check) can't see. Same in-process, no-live-VPS posture.
if [ "${SKIP_CHROME:-0}" != "1" ]; then
  echo "== nav-integrity gate (clean-checkout — dead links / orphans / duplicate sub-nav) =="
  if [ -z "$PY" ]; then
    echo "  ~~ SKIPPED: no python with fastapi found"
  elif "$PY" "$_ROOT/scripts/nav_integrity_gate.py"; then :; else
    echo "  !! nav-integrity gate FAILED — the nav graph drifted from the route table"
    fail=$((fail+1))
  fi
fi

# ── Gate 1c: colour-system alignment (ratchet — tokens present / sc-RS decoupled / migrated
# files free of legacy directional hex; prints the shrinking backlog). In-process, no live VPS. ──
if [ "${SKIP_CHROME:-0}" != "1" ]; then
  echo "== colour gate (clean-checkout — tokens · sc-RS · migrated-file directional cleanliness) =="
  if [ -z "$PY" ]; then
    echo "  ~~ SKIPPED: no python with fastapi found"
  elif "$PY" "$_ROOT/scripts/color_gate.py"; then :; else
    echo "  !! colour gate FAILED — a migrated file regressed to legacy directional colour"
    fail=$((fail+1))
  fi
fi

echo "== health =="
h=$(if [ "${HOST:-vps}" = "local" ]; then echo "n/a"; else ssh -o BatchMode=yes hermes 'systemctl is-active hermes-api'; fi)
echo "  hermes-api: $h"; [ "$h" = "failed" ] && fail=$((fail+1))

echo "== routes (must all be 200) =="
for r in $ROUTES; do c=$(run "$r"); if [ "$c" != "200" ]; then echo "  !! $r -> $c"; fail=$((fail+1)); fi; done

echo "== chart overlays (must all be 200) =="
for o in $OVERLAYS; do c=$(run "$o"); if [ "$c" != "200" ]; then echo "  !! $o -> $c"; fail=$((fail+1)); fi; done

if [ "$fail" -eq 0 ]; then echo "PASS — nothing hampered ($(echo $ROUTES | wc -w) routes + $(echo $OVERLAYS | wc -w) overlays all 200)"; exit 0
else echo "FAIL — $fail regression(s). STOP: fix or revert before committing."; exit 1; fi
