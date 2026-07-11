"""Coverage gate for the strategy-documentation layer (S119).

Guarantees the strategy-doc artifacts stay in sync as the product evolves — so a
strategy can't silently drift undocumented, orphaned, or unlisted. Enforced:
  1. every docs/strategies/*.md (except README) is SERVED (in strategies_view._PAGES);
  2. every served _PAGES slug has a file on disk;
  3. every served page is LISTED in the README status matrix (`](<file>)` link).

This is the machine backstop for the README "Maintenance protocol" + CLAUDE.md's
"documentation is continuous" rule. Adding a NEW strategy → add its page + serve it +
list it in the matrix, or this gate fails. (It does not, by itself, detect a strategy
built in code with NO doc at all — that is the CLAUDE.md new-strategy checklist's job,
and optionally the proposed same-commit PreToolUse hook.)

Run: `python tests/test_strategy_docs_coverage.py`  (or via pytest in the suite).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root (bare-run + pytest)

import src.web.strategies_view as sv

_DIR = Path(__file__).resolve().parents[1] / "docs" / "strategies"


def _docs_on_disk() -> set[str]:
    return {p.name for p in _DIR.glob("*.md")} - {"README.md"}


def _served_files() -> set[str]:
    return {fn for fn, _lbl in sv._PAGES.values()}


def test_every_doc_is_served() -> None:
    orphaned = _docs_on_disk() - _served_files()
    assert not orphaned, f"strategy doc(s) present but NOT served — add to strategies_view._PAGES: {sorted(orphaned)}"


def test_every_served_page_has_a_file() -> None:
    missing = [fn for fn, _lbl in sv._PAGES.values() if not (_DIR / fn).exists()]
    assert not missing, f"served page(s) in _PAGES with NO file on disk: {missing}"


def test_every_served_page_listed_in_readme_matrix() -> None:
    readme = (_DIR / "README.md").read_text(encoding="utf-8")
    unlisted = [fn for fn, _lbl in sv._PAGES.values() if f"]({fn})" not in readme]
    assert not unlisted, f"served page(s) NOT linked in the README status matrix: {unlisted}"


if __name__ == "__main__":
    test_every_doc_is_served()
    test_every_served_page_has_a_file()
    test_every_served_page_listed_in_readme_matrix()
    print(f"strategy-docs coverage gate OK - {len(sv._PAGES)} strategies: served / on-disk / README-matrix all in sync")
