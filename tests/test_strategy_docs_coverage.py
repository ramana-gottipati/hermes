"""Coverage gate for the strategy-documentation layer (S119).

Guarantees the strategy-doc artifacts stay in sync as the product evolves — so a
strategy can't silently drift undocumented, orphaned, or unlisted. Enforced:
  1. every docs/strategies/*.md (except the README index route) is SERVED (in
     strategies_view._PAGES);
  2. every served _PAGES slug has a file on disk;
  3. every served page is LISTED in the README status matrix (`](<file>)` link);
  4. every served STRATEGY page DECLARES its `**Origin:**` (the binding origins.md label
     rule — 🧑 RAMANA / 🏠 HOUSE / 📚 CLASSIC; a new strategy may not ship without it).
     origins.md itself is served but exempt from (4) — it IS the provenance map, so it
     lists every origin and has no single one.

This is the machine backstop for the README "Maintenance protocol" + CLAUDE.md's
"documentation is continuous" rule. Adding a NEW strategy → add its page + serve it +
list it in the matrix, or this gate fails. (It does not, by itself, detect a strategy
built in code with NO doc at all — that is the CLAUDE.md new-strategy checklist's job,
and optionally the proposed same-commit PreToolUse hook.)

Run: `python tests/test_strategy_docs_coverage.py`  (or via pytest in the suite).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root (bare-run + pytest)

import src.web.strategies_view as sv

_DIR = Path(__file__).resolve().parents[1] / "docs" / "strategies"

# README is the /dash/strategy-ref index (rendered by render_index, never a _PAGES
# entry), so it is exempt from the "every doc is served" rule. origins.md IS served
# (S147) so it is NOT here — but it is exempt from the per-page Origin-label rule below.
_INDEX_DOCS = {"README.md"}

# Served docs that are governance/provenance INDEXES, not a single strategy — exempt
# from the **Origin:** label rule (origins.md IS the map: it lists every origin).
_ORIGIN_LABEL_EXEMPT = {"origins.md"}

_ORIGIN_RE = re.compile(r"^\s*>?\s*\*\*Origin:\*\*", re.M)


def _docs_on_disk() -> set[str]:
    return {p.name for p in _DIR.glob("*.md")} - _INDEX_DOCS


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


def test_every_served_page_declares_origin() -> None:
    """The binding origins.md rule: every docs/strategies/ page declares **Origin:**
    in its header (🧑 RAMANA / 🏠 HOUSE / 📚 CLASSIC). A new strategy may not ship
    without the label — this is the machine backstop behind origins.md."""
    missing = [fn for fn, _lbl in sv._PAGES.values()
               if fn not in _ORIGIN_LABEL_EXEMPT
               and not _ORIGIN_RE.search((_DIR / fn).read_text(encoding="utf-8"))]
    assert not missing, (
        f"served strategy page(s) missing the binding **Origin:** header "
        f"(origins.md label rule — add 🧑/🏠/📚): {missing}")


if __name__ == "__main__":
    test_every_doc_is_served()
    test_every_served_page_has_a_file()
    test_every_served_page_listed_in_readme_matrix()
    test_every_served_page_declares_origin()
    print(f"strategy-docs coverage gate OK - {len(sv._PAGES)} strategies: served / on-disk / README-matrix / Origin-label all in sync")
