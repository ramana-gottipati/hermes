# POST-MERGE DEPLOY RUNBOOK — bug-audit PR #1 (`bugfix/audit-p1-2026-06-30` → `main`)

> **Created 2026-06-30 (Session 59).** Turnkey, verified sequence to run **AFTER Ramana merges PR #1**. Prod is currently at the **reviewed-P1 state** (P1 fixes live, 0 drift); this deploys the Medium/Low wave + CL-DASH-14 dead-code removal + the **CX-01 re-settle**. Commands verified read-only on the VPS (invocation form `/opt/hermes/.venv/bin/python -m src.automation.<mod>`; the re-settle CLIs parse). Run from the laptop (`D:\Hermes`, git-bash) unless noted. Honors `vps-deploy-reality` (VPS git tree is dirty/behind → deploy by scp + restart, NOT git-pull).

## 0. Preconditions
- PR #1 merged to `main`. Locally: `git checkout main && git pull` (HEAD == the merged audit work).
- The parallel session's dirty files may also have merged by now — this runbook syncs **whatever `main` has** (drift-based), so it's robust to that.
- ⚠ **Decision gate:** only run Step 2 (re-settle) if Ramana approved the CX-01 re-grade (shifts ~1,568 verdicts; supersedes published CCI track-record figures). If NOT approved, deploy `cci_deep_actuals.py`/`concall_settle.py` code but DO NOT re-settle — or hold those two files back.

## 1. Sync `main` → VPS (drift-based; LF-normalized; backup each)
```bash
cd /d/Hermes && git checkout main && git pull
ts=$(date +%Y%m%d-%H%M%S)
# Sweep every tracked .py; scp only those whose VPS copy differs from main (CR-stripped).
git ls-files 'src/**/*.py' 'scripts/**/*.py' 'research/**/*.py' | while read f; do
  loc=$(tr -d '\r' < "$f" | md5sum | cut -d' ' -f1)
  vps=$(ssh hermes "test -f /opt/hermes/$f && md5sum /opt/hermes/$f | cut -d' ' -f1 || echo X")
  if [ "$loc" != "$vps" ]; then
    echo "DEPLOY $f"
    ssh hermes "mkdir -p /opt/hermes/$(dirname "$f"); cp /opt/hermes/$f /opt/hermes/$f.bak-merge-$ts 2>/dev/null"
    tr -d '\r' < "$f" | ssh hermes "cat > /opt/hermes/$f"
  fi
done
# py3.10 import smoke-test before restart
ssh hermes 'cd /opt/hermes && .venv/bin/python -c "import sys; sys.path.insert(0,\"src\"); import web.dashboard, automation.signals, api.v1.envelope; print(\"IMPORT OK\")"'
```

## 2. CX-01 re-settle + recompute (ONLY if approved) — run in background, it re-grades ~1,568 verdicts
```bash
# Order matters: settle (vs corrected Q4-vs-annual actuals) → scores → PIT credibility series.
ssh hermes 'cd /opt/hermes && nohup bash -c "\
  .venv/bin/python -m src.automation.concall_settle --all && \
  .venv/bin/python -m src.automation.concall_scores --backfill && \
  .venv/bin/python -m src.automation.cci_series --all" \
  > /var/log/hermes-cx01-resettle.log 2>&1 &'
# watch: ssh hermes 'tail -f /var/log/hermes-cx01-resettle.log'
```
Spot-check the fix landed (20MICRONS FY26 Q4 should settle vs Q4 quarterly ~261, not full-year ~954):
```bash
ssh hermes 'cd /opt/hermes && .venv/bin/python -m src.automation.cci_deep_actuals 20MICRONS --as-of 2026-06-30'
```

## 3. Restart + gates
```bash
ssh hermes 'systemctl restart hermes-api && sleep 4 && systemctl is-active hermes-api'
cd /d/Hermes && bash scripts/regression_sweep.sh          # chrome + nav-integrity gates + 32 routes + 5 overlays == 200
python scripts/chrome_gate.py                              # clean-checkout chrome contract
```

## 4. Confirm VPS == main (0 drift)
```bash
cd /d/Hermes
git ls-files 'src/**/*.py' | while read f; do
  loc=$(tr -d '\r' < "$f" | md5sum | cut -d' ' -f1)
  vps=$(ssh hermes "md5sum /opt/hermes/$f 2>/dev/null | cut -d' ' -f1")
  [ "$loc" != "$vps" ] && echo "STILL DRIFTED: $f"
done; echo "drift sweep done (no output above = VPS == main)"
```

## Rollback
Every file backed up to `*.bak-merge-<ts>` (Step 1) on the VPS. To revert one: `ssh hermes 'cp /opt/hermes/<f>.bak-merge-<ts> /opt/hermes/<f>'` then restart. The re-settle is data-only and re-runnable (idempotent over the settlement table); to undo a bad re-settle, restore `research.db`/the settlement table from the nightly backup before re-running.

## Notes / follow-ups (NOT part of this deploy)
- **Blocked dirty-file findings** (CL-CCI-01/03/04/05/10/11/13/14, CL-MDC-09, CL-RS-07): take once the parallel session's edits to `concall_*`/`index_signals`/`rsband`/`v2_surfaces` are committed+merged.
- **Owner-tracked deferrals** (Codex-confirmed): `enrich.py` (CL-PROV-11), `pipeline_status.py` (CL-SCR-10), `code_review.py`-unit (CX-04/05/CL-PROV-17 — ⚠ CX-04 must add redaction/path-filter before any external-GLM send, and the timer must stay disabled until then). CL-CHR-6 (cockpit palette) + CL-DASH-17 (constant IN-list) = low-priority.
