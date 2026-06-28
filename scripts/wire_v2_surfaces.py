#!/usr/bin/env python3
"""
wire_v2_surfaces.py — idempotently (re)apply the DURABLE v2-surfaces hook to main.py.

Operational sibling of scripts/wire_stock_chart.py. Run it after any (re)deploy that
may have clobbered src/main.py, to (re)integrate the v2 website surfaces.

What it does
------------
1. Strips the STALE hand-appended v2 blocks (the 2026-06-26 VPS-only appends) from
   src/main.py ("v2 website surfaces") and src/web/dashboard.py ("v2 nav integration").
   The wiring now lives once, durably, in src/web/v2_surfaces.py — so the inline
   blocks are removed to avoid double-wiring and to converge on one mechanism.
2. Ensures src/main.py ends with the clean 2-line hook that calls
   ``src.web.v2_surfaces.wire(app)`` (defensive try/except; never fatal).
3. ast.parse-guards every change + backs up each touched file (*.bak-v2hook-<ts>).
4. With --verify (run with the app venv from the repo root), imports ``src.main``
   after writing and AUTO-ROLLS-BACK every change if the import fails.

Idempotent: a re-run with the clean hook already present and no stale blocks is a
no-op. Safe: it only ever removes the clearly-marked v2 blocks (which were appended
at end-of-file) and appends the hook — it never touches the chart session's body
edits to those files.

Usage (on the VPS):
    cd /opt/hermes && .venv/bin/python scripts/wire_v2_surfaces.py /opt/hermes --verify
"""
from __future__ import annotations

import argparse
import ast
import os
import shutil
import sys
import time

HOOK_MARKER = "# === v2 surfaces hook (durable) ==="
HOOK_BLOCK = '''

# === v2 surfaces hook (durable) ===
# Mount the v2 website surfaces (Coverage ledger, RS hub, News/Wire, /v1) and
# integrate them into the live nav. Single source of truth = src/web/v2_surfaces.py.
# Re-applied idempotently by scripts/wire_v2_surfaces.py after any redeploy/clobber.
# Defensive: a failure inside wire() is logged, never fatal. Reversible: delete this block.
try:
    from src.web import v2_surfaces as _v2_surfaces
    _v2_surfaces.wire(app)
except Exception as _v2_hook_err:  # noqa: BLE001
    import logging as _v2_logging
    _v2_logging.getLogger("hermes.v2").warning("v2 surfaces hook skipped: %s", _v2_hook_err)
# === end v2 surfaces hook ===
'''

# Stale markers (the 2026-06-26 hand-appended VPS-only blocks) -> strip from marker..EOF.
_STALE = {
    "main": "# --- v2 website surfaces (2026-06-26)",
    "dash": "# --- v2 nav integration (2026-06-26)",
}

# Superseded SELF-CONTAINED blocks (start_marker, end_marker) -> strip the whole block.
# The Lane B "Strategist & Screeners" mount block is now redundant: strategist_view +
# screener_plus are durably mounted by v2_surfaces._ROUTER_SPECS (Round-2 / Lane E), so
# wire() mounts them and this hand-appended stopgap only causes a benign double-mount.
# Its own comment marks it "reversible (delete this block)". Stripping between the markers
# (not to EOF) is surgical — it survives the durable hook sitting either side of it.
_SUPERSEDED_BLOCKS = {
    "main_laneB": ("# === Lane B: Strategist & Screeners", "# === end Lane B mount ==="),
}


def _strip_from_marker(text: str, marker: str) -> tuple[str, bool]:
    i = text.find(marker)
    if i == -1:
        return text, False
    nl = text.rfind("\n", 0, i)          # start of the marker's line
    cut = 0 if nl == -1 else nl
    return text[:cut].rstrip() + "\n", True


def _strip_between_markers(text: str, start: str, end: str) -> tuple[str, bool]:
    """Remove a self-contained block [start-line .. end-line] inclusive. No-op if either
    marker is absent (never strips a half-matched block)."""
    i = text.find(start)
    if i == -1:
        return text, False
    j = text.find(end, i)
    if j == -1:
        return text, False
    head_nl = text.rfind("\n", 0, i)          # start of the start-marker line
    cut0 = 0 if head_nl == -1 else head_nl
    tail_nl = text.find("\n", j)              # end of the end-marker line
    cut1 = len(text) if tail_nl == -1 else tail_nl
    return (text[:cut0].rstrip() + "\n" + text[cut1:].lstrip("\n")).rstrip() + "\n", True


def _backup(path: str) -> str:
    bak = f"{path}.bak-v2hook-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, bak)
    return bak


def process(root: str, verify: bool) -> int:
    main_py = os.path.join(root, "src", "main.py")
    dash_py = os.path.join(root, "src", "web", "dashboard.py")
    changed: list[tuple[str, str, str]] = []

    # 1. dashboard.py — strip the stale nav block (nav is wrapped at runtime now).
    with open(dash_py, encoding="utf-8") as f:
        dtext = f.read()
    dnew, dhit = _strip_from_marker(dtext, _STALE["dash"])
    if dnew != dtext:
        ast.parse(dnew)                  # guard: never write an unparseable file
        bak = _backup(dash_py)
        with open(dash_py, "w", encoding="utf-8") as f:
            f.write(dnew)
        changed.append((dash_py, bak, "stripped stale v2 nav block"))

    # 2. main.py — strip the stale block + the superseded Lane B mount (now durable via
    #    _ROUTER_SPECS), then ensure the clean hook at EOF.
    with open(main_py, encoding="utf-8") as f:
        mtext = f.read()
    mnew, mhit = _strip_from_marker(mtext, _STALE["main"])
    laneB_start, laneB_end = _SUPERSEDED_BLOCKS["main_laneB"]
    mnew, lbhit = _strip_between_markers(mnew, laneB_start, laneB_end)
    had_hook = HOOK_MARKER in mnew
    if not had_hook:
        mnew = mnew.rstrip() + "\n" + HOOK_BLOCK
    if mnew != mtext:
        ast.parse(mnew)                  # guard
        bak = _backup(main_py)
        with open(main_py, "w", encoding="utf-8") as f:
            f.write(mnew)
        note = []
        if mhit:
            note.append("stripped stale block")
        if lbhit:
            note.append("stripped superseded Lane B mount (now in _ROUTER_SPECS)")
        if not had_hook:
            note.append("added hook")
        changed.append((main_py, bak, "; ".join(note)))

    for p, b, note in changed:
        print(f"WROTE {p}  ({note})  backup={b}")
    if not changed:
        print("NO-OP: clean hook already present, no stale blocks to strip.")

    if verify:
        sys.path.insert(0, root)
        try:
            import importlib

            importlib.import_module("src.main")
            print("VERIFY: import src.main OK")
        except Exception as e:  # noqa: BLE001
            print(f"VERIFY FAILED: {e}", file=sys.stderr)
            for p, b, _ in changed:
                shutil.copy2(b, p)
                print(f"ROLLED BACK {p} <- {b}", file=sys.stderr)
            return 2
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default="/opt/hermes", help="hermes repo root")
    ap.add_argument("--verify", action="store_true",
                    help="import src.main after writing; auto-rollback on failure")
    args = ap.parse_args()
    return process(args.root, args.verify)


if __name__ == "__main__":
    raise SystemExit(main())
