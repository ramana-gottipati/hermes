"""Doc-governance coverage in the pytest suite (S131 / D128).

A thin wrapper over `scripts/doc_hygiene_gate.py` so the same three ratchet checks that
run standalone and as `regression_sweep.sh` Gate 1d also run wherever pytest runs — the
VPS nightly, CI, and a bare `pytest tests/`. It REUSES the gate module (single source of
truth); no check logic is duplicated here. A NEW orphaned doc, an un-bannered transient
doc, or CLAUDE.md<->AGENTS.md twin drift fails these tests.

Pure stdlib + git (no app import), so it runs even without the FastAPI venv.
"""
from __future__ import annotations

import sys
from pathlib import Path

# scripts/ is not a package — put it on the path and import the gate by module name,
# same coupling test_strategy_docs_coverage.py uses for src.web.strategies_view.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import doc_hygiene_gate as gate  # noqa: E402


def test_every_doc_is_indexed() -> None:
    """Every git-tracked docs/**/*.md is referenced in docs/DOC_INDEX.md (orphan-file class)."""
    extra = sorted(set(gate._find_unindexed()) - gate.GRANDFATHERED_UNINDEXED)
    assert not extra, (
        "doc(s) on disk but absent from docs/DOC_INDEX.md — add an index entry, or (with a "
        f"documented reason) to the gate's ratchet floor: {extra}"
    )


def test_transient_docs_carry_a_lifecycle_banner() -> None:
    """Every transient-NAMED doc has a `Lifecycle:` banner in its first 20 lines."""
    extra = sorted(set(gate._find_unbannered()) - gate.GRANDFATHERED_UNBANNERED)
    assert not extra, (
        f"transient-named doc(s) missing a `Lifecycle:` banner (TRANSIENT|LIVING|PERMANENT): {extra}"
    )


def test_claude_agents_twins_in_sync() -> None:
    """The canonical load-bearing rules appear in BOTH CLAUDE.md and AGENTS.md."""
    drift = gate._twin_drift()
    assert not drift, f"CLAUDE.md <-> AGENTS.md canonical-rule drift: {drift}"


if __name__ == "__main__":  # allow a bare run outside pytest
    test_every_doc_is_indexed()
    test_transient_docs_carry_a_lifecycle_banner()
    test_claude_agents_twins_in_sync()
    print("doc-hygiene pytest checks OK — index coverage / transient banners / twin-sync all clean")
