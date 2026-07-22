"""pytest bootstrap for the Hermes test harness (audit AUD-39).

Puts the repo root on sys.path so tests can `import src.*`, and the research/
tree so the momentum tests can reach `explosive_moves.*`. Kept deliberately tiny
and dependency-free so `python -m pytest -q` is a viable gate-0 anywhere.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in (_ROOT, os.path.join(_ROOT, "research")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --- gate-0 hygiene (S209): keep bare `python -m pytest -q` collectable off-box ---
# The research/ tree carries box-run analysis scripts named `*_test.py` (that suffix
# means "an experiment I ran", NOT a pytest test — real research coverage is the
# tests/test_research_selftests.py wrapper, S197). Some (e.g. gauntlet/rsirs_denom_test.py)
# open a hardcoded /opt/hermes box path at IMPORT time, which crashes pytest COLLECTION
# on a laptop and takes the whole gate-0 down. Exclude the research/**/*_test.py family
# from direct collection so the documented "gate-0 anywhere" holds off-box. No coverage
# is lost: these contribute zero collected tests (bare `pytest -q` == `pytest tests/ -q`).
# All real tests use the test_*.py PREFIX, so nothing legitimate matches this suffix glob.
collect_ignore_glob = ["research/*_test.py", "research/**/*_test.py"]
