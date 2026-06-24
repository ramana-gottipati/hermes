#!/usr/bin/env python3
"""Idempotent in-place anchored hooks for the one-chart stock engine (stock_chart.py
+ rs_overlay.py). Run locally for verification and re-run verbatim on the VPS during
deploy (dashboard.py / main.py are parallel-held → never scp'd whole; patched by anchor).

Hooks (all uncommitted — only the isolated modules get committed):
  dashboard.py  · import `_STOCK_CHART_SNIPPET`
                · replace the old inline 4-pane <script> block with the data island +
                  the {token} (the block is bounded by two unique anchors).
  main.py       · import + include_router(rs_router) for /dash/rs/overlay.

Safe to run repeatedly: each hook is skipped if already present. Writes *.bak-stockchart
once, then validates every patched file with ast.parse before returning non-zero on error.

    python scripts/wire_stock_chart.py [PROJECT_ROOT]   # default: cwd
"""
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
DASH = ROOT / "src" / "web" / "dashboard.py"
MAIN = ROOT / "src" / "main.py"

DASH_IMPORT_ANCHOR = "from src.web.mep_overlay import SNIPPET as _MEP_SNIPPET"
DASH_IMPORT_ADD = "from src.web.stock_chart import SNIPPET as _STOCK_CHART_SNIPPET"
BLOCK_START = '<script src="{_LWC_CDN}"></script>\n<script>\nconst DATA = {data_json};'
BLOCK_END_NEXT = "{tab_js}"
NEW_BLOCK = (
    '<script src="{_LWC_CDN}"></script>\n'
    "<script>window.__wfdata={data_json};</script>\n"
    "{_STOCK_CHART_SNIPPET}\n"
)

MAIN_IMPORT_ANCHOR = "from src.web.mep_overlay import router as mep_router"
MAIN_IMPORT_ADD = "from src.web.rs_overlay import router as rs_router"
MAIN_INCLUDE_ANCHOR = "app.include_router(mep_router)"
MAIN_INCLUDE_ADD = (
    "# RS-vs-benchmark ratio line (2026-06-24): /dash/rs/overlay feeds the stock chart's\n"
    "# docked RS lane (the one-chart engine, stock_chart.py). Isolated module.\n"
    "app.include_router(rs_router)"
)


def _backup(p: Path) -> None:
    b = p.with_suffix(p.suffix + ".bak-stockchart")
    if not b.exists():
        shutil.copy2(p, b)


def patch_dashboard() -> list[str]:
    txt = DASH.read_text(encoding="utf-8")
    notes: list[str] = []
    if DASH_IMPORT_ADD in txt:
        notes.append("dashboard import: already present")
    else:
        if DASH_IMPORT_ANCHOR not in txt:
            raise SystemExit("dashboard import anchor not found")
        _backup(DASH)
        txt = txt.replace(DASH_IMPORT_ANCHOR, DASH_IMPORT_ANCHOR + "\n" + DASH_IMPORT_ADD, 1)
        notes.append("dashboard import: added")

    if "{_STOCK_CHART_SNIPPET}" in txt:
        notes.append("dashboard block: already replaced")
    else:
        start = txt.find(BLOCK_START)
        nxt = txt.find(BLOCK_END_NEXT)
        if start < 0 or nxt < 0 or nxt < start:
            raise SystemExit("dashboard chart-block anchors not found / out of order")
        _backup(DASH)
        txt = txt[:start] + NEW_BLOCK + txt[nxt:]
        notes.append("dashboard block: replaced (old 4-pane inline block retired)")

    ast.parse(txt)  # fail loudly before writing if we corrupted the f-string/source
    DASH.write_text(txt, encoding="utf-8")
    return notes


def patch_main() -> list[str]:
    txt = MAIN.read_text(encoding="utf-8")
    notes: list[str] = []
    if MAIN_IMPORT_ADD in txt:
        notes.append("main import: already present")
    else:
        if MAIN_IMPORT_ANCHOR not in txt:
            raise SystemExit("main import anchor not found")
        _backup(MAIN)
        txt = txt.replace(MAIN_IMPORT_ANCHOR, MAIN_IMPORT_ANCHOR + "\n" + MAIN_IMPORT_ADD, 1)
        notes.append("main import: added")

    if "app.include_router(rs_router)" in txt:
        notes.append("main include: already present")
    else:
        if MAIN_INCLUDE_ANCHOR not in txt:
            raise SystemExit("main include anchor not found")
        _backup(MAIN)
        txt = txt.replace(MAIN_INCLUDE_ANCHOR, MAIN_INCLUDE_ANCHOR + "\n" + MAIN_INCLUDE_ADD, 1)
        notes.append("main include: added")

    ast.parse(txt)
    MAIN.write_text(txt, encoding="utf-8")
    return notes


if __name__ == "__main__":
    for n in patch_dashboard():
        print("  •", n)
    for n in patch_main():
        print("  •", n)
    print("OK — hooks applied; ast.parse clean.")
