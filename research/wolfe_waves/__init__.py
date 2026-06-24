"""Wolfe-wave research sandbox (Phase 0).

Offline, READ-ONLY against the production hermes.db. Prototypes the mechanical
1-4 detector + a mechanical proxy of Ramana's Fib-confluence point-5, and a
point-in-time forward-outcome backtest to test whether the setup has edge before
any production code is written (see docs/wolfe-wave-design.md).

Pure stdlib (no numpy) so it runs in any venv and on the VPS unchanged. Reuses the
production corporate-action adjuster (src/automation/adjust.py) for split-clean
prices when available.

Run (from repo root):
    .venv/Scripts/python.exe research/wolfe_waves/selftest.py        # deterministic correctness
    .venv/Scripts/python.exe research/wolfe_waves/backtest.py --describe --symbols all
    HERMES_MAIN_DB=/opt/hermes/data/hermes.db python3 research/wolfe_waves/backtest.py --symbols all   # VPS edge run
"""
