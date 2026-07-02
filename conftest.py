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
