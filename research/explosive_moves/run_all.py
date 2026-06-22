"""Phase F — orchestrator. Regenerates the whole study deterministically.

    cd /opt/hermes/research && .venv-research/bin/python -m explosive_moves.run_all

Runs: events (A) -> features (B) -> mine (C+D) -> validate (E) -> sensitivity (E).
All outputs land in out/*.csv and research.db. Fixed seeds; production hermes.db
is opened read-only. See docs/explosive-move-research.md for the findings.
"""
from __future__ import annotations

import time

from . import events, features, mine, validate, sensitivity


def main():
    t0 = time.time()
    print("### Phase A — event detection");      events.main()
    print("### Phase B — feature matrix");        features.main()
    print("### Phase C+D — pattern mining");       mine.main()
    print("### Phase E — OOS validation");         validate.main()
    print("### Phase E — robustness/sensitivity"); sensitivity.main()
    print(f"\nALL PHASES DONE in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
