"""board_health — the strategist-board health gate (S84b, D94).

Ramana 2026-07-10: hollow strategy cards sat on the product's front door until
the CEO walked the floor ("why are so many cards empty? why has that not been
taken up proactively?"). The audit already named the failure class — monitors
that never page. This gate makes the MACHINE walk the board nightly:

    python -m src.automation.board_health --check

runs strategy_registry.summary() (the same read the strategist board and the
home count-strip consume) and

  * FAILS (exit 2)  when any strategy row has NO data at all (as_of missing —
                    a hollow card: dead table, broken reader, missed nightly)
                    or is STALE beyond its per-strategy budget;
  * WARNS (exit 0)  when a row has fresh data but zero currently-flagged names
                    (a legitimate market condition, not a defect);
  * PASSES silently otherwise.

The systemd unit (hermes-board-health.timer, 22:00 UTC Mon-Fri — after the full
nightly chain incl. momentum 21:30) carries OnFailure=hermes-alert@%n.service,
so a hollow card pages the same night it appears, not weeks later. Read-only;
NO LLM (Rs0); safe to run at any hour.
"""
from __future__ import annotations

import sys

try:
    from src.automation import strategy_registry as REG
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    import strategy_registry as REG  # type: ignore
    from core.db import get_conn  # type: ignore


def check(verbose: bool = True) -> int:
    with get_conn() as conn:
        rows = REG.summary(conn)
    broken = [r for r in rows if not r.get("as_of")]
    stale = [r for r in rows if r.get("health") == "stale"]
    zeroed = [r for r in rows
              if r.get("health") == "empty" and r.get("as_of")]
    if verbose:
        for r in rows:
            mark = ("BROKEN" if r in broken else
                    "STALE" if r in stale else
                    "zero" if r in zeroed else "ok")
            print(f"  {r['key']:<10} {mark:<7} count={str(r['count']):>5} "
                  f"as_of={r['as_of']}")
    if broken or stale:
        names = ", ".join(r["key"] for r in broken + stale)
        print(f"BOARD-HEALTH FAIL: {len(broken)} hollow + {len(stale)} stale "
              f"strategy cards -> {names}")
        return 2
    if zeroed:
        print(f"board-health WARN (not fatal): zero-flagged with fresh data: "
              + ", ".join(r["key"] for r in zeroed))
    print(f"board-health OK: {len(rows)} strategies measured")
    return 0


if __name__ == "__main__":
    # `--check` is the documented verb; a bare run behaves identically so the
    # unit file stays trivial.
    sys.exit(check())
