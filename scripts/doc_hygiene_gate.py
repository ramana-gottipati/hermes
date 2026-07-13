#!/usr/bin/env python3
"""doc_hygiene_gate.py — the documentation-governance backstop (S128 audit follow-up).

Three independent checks, each a RATCHET (like scripts/color_gate.py): the current
backlog is grandfathered so the gate lands GREEN today, but any NEW drift fails it.
Grandfather floors may only SHRINK — never add a name back.

  A. INDEX COVERAGE  — every docs/**/*.md is referenced in docs/DOC_INDEX.md.
                       Closes the "orphan file" class the S128 audit found (49 docs
                       on disk were absent from the index).
  B. TRANSIENT BANNER — every doc whose NAME signals a transient working doc
                       (PLAN / HANDOFF / NEXT-SESSION / KICKSTART / CARRY-FORWARD /
                       EXECUTE / ROUND / -audit / -sweep / -qa / register / STATUS)
                       carries a `Lifecycle:` line (TRANSIENT | LIVING | PERMANENT +
                       a retire condition). Enforces docs/…transient-doc-lifecycle.
  C. TWIN SYNC       — a set of canonical, load-bearing rules appear in BOTH CLAUDE.md
                       and AGENTS.md. Catches the drift where a critical ban/rule is
                       updated in one twin but not the other. (Presence-parity only —
                       it does NOT diff wording; a full semantic diff is out of scope.)

Pure stdlib, no app import → safe to run in a git pre-commit hook and offline.
Run:   python scripts/doc_hygiene_gate.py
Seed:  DOC_HYGIENE_SEED=1 python scripts/doc_hygiene_gate.py   # print floors as literals
Exit:  0 = clean (backlog only shrank);  1 = NEW drift (a name not on the floor).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOC_INDEX = DOCS / "DOC_INDEX.md"
CLAUDE_MD = ROOT / "CLAUDE.md"
AGENTS_MD = ROOT / "AGENTS.md"

# Docs that are intentionally NOT catalogued in DOC_INDEX.md (the index itself; and
# the strategy pages, which have their own coverage gate: test_strategy_docs_coverage).
INDEX_EXEMPT_SUFFIXES = ("DOC_INDEX.md",)
INDEX_EXEMPT_DIRS = ("strategies",)  # governed by tests/test_strategy_docs_coverage.py
# Lane run-books are RUN-BOOK(active) "by rule" per DOC_INDEX.md's Lane-record clause — the index
# deliberately does NOT list each one individually, so they are covered without their own entry.
INDEX_EXEMPT_LANE = re.compile(r"(^|/)(lane-|L\d+-|parallel-sessions-|CARRY-FORWARD-)|-LANE-", re.IGNORECASE)

TRANSIENT_NAME = re.compile(
    r"(PLAN|HANDOFF|NEXT-SESSION|KICKSTART|CARRY-?FORWARD|EXECUTE|ROUND\d|"
    r"-audit|-sweep|-qa|register|POSTMORTEM|STATUS|DEMO-READINESS)",
    re.IGNORECASE,
)
LIFECYCLE = re.compile(r"Lifecycle:\s*(TRANSIENT|LIVING|PERMANENT|RETIRE)", re.IGNORECASE)

# Canonical rules that MUST appear (case-insensitively) in BOTH CLAUDE.md and AGENTS.md.
# Keep these as short, stable substrings of the actual rule text.
TWIN_INVARIANTS = {
    "standing-authorization": "STANDING AUTHORIZATION",
    "never-ask-folder-access": "never request folder",
    "cheap-models-on-timers": "Sonnet/Opus",
    "primary-sources-only": "Never add a vendor or Screener.in dependency",
    "surface-playbook-binding": "SURFACE-PLAYBOOK.md",
    "secrets-never-committed": "never commit",
    "state-doc-same-commit": "same commit",
}

# ───────────────────────── RATCHET FLOORS (only ever shrink) ─────────────────────────
# CLEARED 2026-07-14 (S131/D128): the whole backlog was triaged — every doc indexed in DOC_INDEX.md,
# every transient doc bannered — so both floors are EMPTY and the gate enforces 100%. Keep them empty;
# a name here would mean "known debt, do not regress", and a NEW offender must fail the gate.
GRANDFATHERED_UNINDEXED: set[str] = set()   # empty — full DOC_INDEX coverage (2026-07-14)
GRANDFATHERED_UNBANNERED: set[str] = set()  # empty — all transient docs carry a Lifecycle banner (2026-07-14)
# ─────────────────────────────────────────────────────────────────────────────────────


def _all_docs() -> list[Path]:
    """Git-TRACKED docs only (committed + staged) — WIP untracked files never fail the gate,
    and in a pre-commit a newly `git add`ed doc IS judged (it's in the index). Fallback to a
    disk walk only when git is unavailable (e.g. an exported tarball)."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "docs"],
                             cwd=str(ROOT), capture_output=True, text=True, timeout=15)
        if out.returncode == 0:
            rels = [r for r in out.stdout.split("\0") if r.endswith(".md")]
            if rels:
                return sorted(ROOT / r for r in rels)
    except Exception:
        pass
    return sorted(p for p in DOCS.rglob("*.md") if p.is_file())


def _relposix(p: Path) -> str:
    return p.relative_to(DOCS).as_posix()


def _index_text() -> str:
    return DOC_INDEX.read_text(encoding="utf-8", errors="replace") if DOC_INDEX.exists() else ""


def _is_indexed(p: Path, index_text: str) -> bool:
    """Indexed if the docs-relative path OR the bare basename is linked in DOC_INDEX.md."""
    rel = _relposix(p)
    return rel in index_text or p.name in index_text


def _find_unindexed() -> list[str]:
    idx = _index_text()
    out = []
    for p in _all_docs():
        rel = _relposix(p)
        if rel.endswith(INDEX_EXEMPT_SUFFIXES):
            continue
        if p.relative_to(DOCS).parts[:1] and p.relative_to(DOCS).parts[0] in INDEX_EXEMPT_DIRS:
            continue
        if INDEX_EXEMPT_LANE.search(rel):
            continue  # RUN-BOOK "by rule" (DOC_INDEX Lane-record clause)
        if not _is_indexed(p, idx):
            out.append(rel)
    return sorted(out)


def _find_unbannered() -> list[str]:
    out = []
    for p in _all_docs():
        if not TRANSIENT_NAME.search(p.name):
            continue
        head = "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:20])
        if not LIFECYCLE.search(head):
            out.append(_relposix(p))
    return sorted(out)


def _twin_drift() -> list[str]:
    if not (CLAUDE_MD.exists() and AGENTS_MD.exists()):
        return ["CLAUDE.md or AGENTS.md is missing"]
    c = CLAUDE_MD.read_text(encoding="utf-8", errors="replace").lower()
    a = AGENTS_MD.read_text(encoding="utf-8", errors="replace").lower()
    drift = []
    for key, needle in TWIN_INVARIANTS.items():
        n = needle.lower()
        in_c, in_a = n in c, n in a
        if in_c != in_a:
            where = "AGENTS.md" if in_c else "CLAUDE.md"
            drift.append(f"{key!r}: present in {'CLAUDE.md' if in_c else 'AGENTS.md'}, MISSING in {where}")
    return drift


def _ratchet(name: str, current: list[str], floor: set[str]) -> int:
    new = [x for x in current if x not in floor]
    cleared = sorted(floor - set(current))
    print(f"-- {name} --")
    if new:
        print(f"  !! FAIL - {len(new)} NEW offender(s) not on the ratchet floor:")
        for x in new:
            print(f"       + {x}")
    if current:
        print(f"  backlog: {len(current)} known (floor {len(floor)}); shrink it.")
    if cleared:
        print(f"  OK {len(cleared)} floor entry(ies) now clean - delete from the floor: {cleared}")
    if not new and not current:
        print("  clean.")
    return 1 if new else 0


def main() -> int:
    if os.environ.get("DOC_HYGIENE_SEED") == "1":
        print("GRANDFATHERED_UNINDEXED = {")
        for x in _find_unindexed():
            print(f"    {x!r},")
        print("}")
        print("GRANDFATHERED_UNBANNERED = {")
        for x in _find_unbannered():
            print(f"    {x!r},")
        print("}")
        return 0

    fail = 0
    fail |= _ratchet("A. index coverage (docs/DOC_INDEX.md)", _find_unindexed(), GRANDFATHERED_UNINDEXED)
    fail |= _ratchet("B. transient-doc Lifecycle banner", _find_unbannered(), GRANDFATHERED_UNBANNERED)

    drift = _twin_drift()
    print("-- C. CLAUDE.md <-> AGENTS.md twin-sync --")
    if drift:
        print(f"  !! FAIL - {len(drift)} canonical rule(s) out of sync:")
        for d in drift:
            print(f"       {d}")
        fail = 1
    else:
        print(f"  clean - all {len(TWIN_INVARIANTS)} canonical rules present in both twins.")

    print("PASS - doc hygiene held (backlog only shrank)." if not fail
          else "FAIL - new documentation drift. Fix, or add to the ratchet floor only with a reason.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
