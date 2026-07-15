"""Pytest collection guard for research/explosive_moves.

combo_test.py is a RESEARCH SCRIPT (``__main__`` entry, no test_ functions) whose
``*_test.py`` filename accidentally matches pytest's default collection pattern —
it imports numpy at module level, so in numpy-less environments (the VPS main venv,
fresh worktrees) its collection error aborted the ENTIRE suite (hit S157-lab,
reproduced at bare 1ca99a5). Ignoring it here is suite hygiene, not a semantics
change: the script still runs directly via ``python -m`` exactly as before.

If a real pytest test ever lands in this directory, name it test_*.py and place it
under tests/ with an ``importorskip("numpy")`` guard (the test_rule_lab_executor.py
pattern) rather than extending this list.
"""

collect_ignore = ["combo_test.py"]
