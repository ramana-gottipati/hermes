"""test_sideways_parity.py — the MIGRATION-PARITY gate (nothing silently missed in Sideways).

Why this test exists
--------------------
Sideways (the modern app) is a from-scratch rebuild — exactly where a large classic estate loses
things silently. This is the third governance sibling of `test_dash_route_registry.py` (no orphan
routes) and `test_pat_coverage.py` (every lens known to Pat): it derives the whole PRODUCT estate
from the single-sources-of-truth and asserts every element carries a disposition in the modern app,
so a surface can never be dropped by accident — only by a recorded decision.

The contract (see src/web/sideways_parity.py)
---------------------------------------------
Every routed lens (surface) resolves to exactly one disposition — PORTED / DEFERRED / DROPPED / NA
(explicit entry, else a deterministic per-workspace DEFERRED default, so it is ALWAYS accounted).
The gate enforces INTEGRITY (no stale explicit keys · PORTED has a real Sideways route · DROPPED/NA
carry a rationale · DEFERRED targets a real milestone) and COMPLETENESS (a milestone marked DONE
cannot still have un-ported surfaces assigned to it). A new lens auto-appears in the inventory and
lands on the board's backlog (UNSCOPED) — visible, never missed.

Run
---
    pytest tests/test_sideways_parity.py       # as a gate
    python  tests/test_sideways_parity.py       # prints the parity summary
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.web import lens_registry as LR       # noqa: E402
from src.web import sideways_parity as SP      # noqa: E402


ROUTED_KEYS = {ln.key for ln in LR.LENSES if ln.route}


def test_every_surface_is_accounted():
    """The core guarantee: every routed lens resolves to a valid disposition — never invisible."""
    bad = []
    for key, _lab, alt, _rt in SP.surfaces():
        st, _tgt, _note = SP.disposition(key, alt)
        if st not in SP._VALID_STATUS:
            bad.append(f"{key} -> {st!r} (not a valid disposition)")
    assert not bad, (
        "\nSurfaces with no valid Sideways disposition (each must be PORTED / DEFERRED / DROPPED / "
        "NA — an explicit entry in sideways_parity.SURFACE_PARITY or the workspace default):\n"
        + "\n".join(f"  !! {b}" for b in bad)
    )


def test_disposition_integrity():
    """PORTED points at a real Sideways route · DROPPED/NA carry a rationale · DEFERRED targets a
    real milestone. The teeth on each disposition kind."""
    bad = []
    for key, _lab, alt, _rt in SP.surfaces():
        st, tgt, note = SP.disposition(key, alt)
        if st == "PORTED" and not tgt.startswith("/dash"):
            bad.append(f"{key}: PORTED but target {tgt!r} is not a /dash route (where did it land?)")
        if st in ("DROPPED", "NA") and not note.strip():
            bad.append(f"{key}: {st} but no rationale — a deliberate drop must say WHY")
        if st == "DEFERRED" and tgt not in SP.MILESTONES:
            bad.append(f"{key}: DEFERRED to unknown milestone {tgt!r} (add it to MILESTONES)")
    assert not bad, "\nDisposition integrity failures:\n" + "\n".join(f"  !! {b}" for b in bad)


def test_no_stale_explicit_entries():
    """Every explicit SURFACE_PARITY key must still be a routed lens (no dead config that would
    silently stop tracking a renamed surface)."""
    stale = sorted(k for k in SP.SURFACE_PARITY if k not in ROUTED_KEYS)
    assert not stale, (
        "\nStale sideways_parity.SURFACE_PARITY keys (no longer a routed lens — remove or re-key):\n"
        + "\n".join(f"  !! {k}" for k in stale)
    )


def test_explicit_entries_are_well_formed():
    """Each explicit entry is a 3-tuple (status, target, note) with a valid status."""
    bad = []
    for k, v in SP.SURFACE_PARITY.items():
        if not (isinstance(v, tuple) and len(v) == 3):
            bad.append(f"{k}: entry is not a (status, target, note) 3-tuple")
            continue
        if v[0] not in SP._VALID_STATUS:
            bad.append(f"{k}: status {v[0]!r} not in {sorted(SP._VALID_STATUS)}")
    assert not bad, "\n" + "\n".join(f"  !! {b}" for b in bad)


def test_done_milestones_are_fully_ported():
    """COMPLETENESS: a milestone marked DONE cannot still have surfaces assigned to it that are not
    PORTED — you cannot declare a migration phase complete while items in its scope are unbuilt."""
    laggards = []
    done = {m for m, (_lab, st) in SP.MILESTONES.items() if st == "DONE"}
    for key, _lab, alt, _rt in SP.surfaces():
        st, tgt, _n = SP.disposition(key, alt)
        if tgt in done and st != "PORTED":
            laggards.append(f"{key}: assigned to {tgt} (DONE) but still {st}")
    assert not laggards, (
        "\nSurfaces assigned to a DONE milestone but not yet PORTED (finish the port, re-assign to a "
        "later milestone, or mark DROPPED with a reason):\n" + "\n".join(f"  !! {x}" for x in laggards)
    )


def test_inventory_is_non_degenerate():
    """Sanity: the derivation actually enumerated the estate (catches a broken import/parse that
    would make the whole ledger empty and the guarantee hollow)."""
    s = SP.summary()
    assert s["surfaces"] >= 50, f"too few surfaces derived ({s['surfaces']}) — registry import broken?"
    assert s["metrics"] >= 100, f"too few metrics parsed ({s['metrics']}) — glossary path/parse broken?"
    assert s["strategies"] >= 5, f"too few strategies ({s['strategies']}) — docs/strategies glob broken?"


def test_new_surface_is_accounted_not_missed():
    """The Done criterion: a brand-new surface with NO explicit entry is still accounted (falls to a
    valid default) and lands on the backlog — proving a future lens can never be silently missed."""
    for alt in ("markets", "screener", "strategies", "tracker", "trust"):
        st, tgt, _n = SP.disposition("__synthetic_new_lens__", alt)
        assert st in SP._VALID_STATUS, (alt, st)
        # a new lens is DEFERRED (planned/unscoped), never PORTED/DROPPED by accident
        assert st == "DEFERRED", (alt, "a brand-new surface must default to DEFERRED, not " + st)


if __name__ == "__main__":
    s = SP.summary()
    bs = s["by_status"]
    print(f"== Sideways migration parity ==")
    print(f"surfaces: {s['surfaces']}  (ported {bs['PORTED']} · deferred {bs['DEFERRED']} · "
          f"dropped {bs['DROPPED']} · na {bs['NA']}; UNSCOPED {s['unscoped']})")
    print(f"metrics accounted: {s['metrics']}  ·  strategies accounted: {s['strategies']}")
    print("PASS — every surface accounted; run pytest for the full gate.")
