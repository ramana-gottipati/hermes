# Zerodha real-cost gauntlet — working scripts (2026-07-18)

Reproduce the findings in `docs/zerodha-cost-gauntlet-2026-07-18.md` (ledger 16BC).

- `bt_zerodha.py`   — factor baskets through the per-name Zerodha gauntlet (+tax); writes bt_zerodha.json.
- `build_gauntlet.py` — transforms the sealed `union_ladder_val.py` into a per-name-cost copy; writes union_gauntlet.json.
- `build_k30_checks.py` — K30 execution-lag (engine `lagged` mode) + AUM ladder (cost_participation sqrt-impact).
- `build_workbook.py` — builds the 17-sheet investor xlsx from bt_zerodha.json + union_gauntlet.json.
- `*.json` — the recorded results (used by build_workbook.py).

NOTE: the build_* scripts read `D:\Hermes\research\explosive_moves\union_ladder_val.py` and emit runnable
copies; run those on the VPS (`.venv-research`, `data/hermes.db`). Paths are laptop-absolute — adjust to reproduce.
The engine reproduces the sealed CAGRs under flat cost (validation) before any gauntlet number is trusted.
