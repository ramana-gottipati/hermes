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


def test_ledger_tags_are_unique() -> None:
    """Every `### 2026-…` strategy-ledger tag is unique (the tag-race collision class, S187).

    A duplicate tag is the failure the 16AX/16AY collisions were: two parallel lanes each mint the
    same id and every inbound `[16AX]` citation becomes ambiguous. The ONE grandfathered pre-existing
    dup (`2026-07-15i`) is excused; any NEW collision fails."""
    extra = sorted(set(gate._ledger_dup_tags()) - gate.GRANDFATHERED_DUP_TAGS)
    assert not extra, (
        "duplicate strategy-ledger tag(s) — two entries minting the same id breaks every inbound "
        f"citation; renumber the later entry to the next free tag: {extra}"
    )


def test_decision_log_ids_are_unique() -> None:
    """Every `### D<n>` Decision-log id in PROJECT_STATE.md is unique (the tag-race, code-cited).

    Two distinct decisions sharing an id breaks ~78×-cited inbound refs across docs and code. Suffixed
    variants (`D142-RECONCILE`) stay distinct. The one historical dup (`D68`) was healed in S194c
    (GLM-reviewer renumbered to D145), so the floor is empty now; any collision fails."""
    extra = sorted(set(gate._decision_dup_ids()) - gate.GRANDFATHERED_DUP_DECISIONS)
    assert not extra, (
        "duplicate Decision-log id(s) — two decisions minting the same D-number breaks every inbound "
        f"citation (docs + code); renumber the later entry to the next free D-number: {extra}"
    )


if __name__ == "__main__":  # allow a bare run outside pytest
    test_every_doc_is_indexed()
    test_transient_docs_carry_a_lifecycle_banner()
    test_claude_agents_twins_in_sync()
    test_ledger_tags_are_unique()
    test_decision_log_ids_are_unique()
    print("doc-hygiene pytest checks OK — index / transient / twin-sync / ledger-tags / decision-ids all clean")
