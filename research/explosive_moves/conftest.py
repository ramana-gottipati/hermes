"""Pytest collection guard for research/explosive_moves.

combo_test.py and veto_test.py are RESEARCH SCRIPTS (top-level ``sys.argv`` entry,
no test_ functions) whose ``*_test.py`` filename accidentally matches pytest's
default collection pattern. combo_test.py imports numpy at module level; veto_test.py
imports the sibling ``adjust`` module via a VPS-only ``sys.path`` insert — in either
case, a numpy-less or non-VPS environment (a fresh worktree) hits a collection error
that aborted the ENTIRE suite (hit S157-lab, reproduced at bare 1ca99a5). Ignoring
them here is suite hygiene, not a semantics change: both scripts still run directly
via ``python -m`` exactly as before.

If a real pytest test ever lands in this directory, name it test_*.py and place it
under tests/ with an ``importorskip("numpy")`` guard (the test_rule_lab_executor.py
pattern) rather than extending this list.
"""

collect_ignore = ["combo_test.py", "veto_test.py"]
