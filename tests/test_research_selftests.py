"""Research event-study selftests as gate-0 pytest tests (S197).

The pre-registered event-study + drift battery under ``research/explosive_moves/`` each ships a
hermetic, pure-compute ``selftest()`` that builds its own in-memory fixtures and asserts the
load-bearing math (E-02/E-03/E-04/E-11/E-12/E-14 event studies, PEAD/footprint, the drift
families, SHP combos, reclaim/fractal selection). Those assertions only ran via a manual
``--selftest`` on the box — with ZERO pytest coverage — so a refactor could silently break the
charter's evidence machine. This wrapper makes pytest own them, extending the sanctioned idiom of
``test_band_lock`` / ``test_concall_veto`` / ``test_famous_strategies``. One source of assertions
per module; this file just runs them.

Each selftest returns ``None`` (raise-on-failure convention) or ``0``; both pass, a raise or a
nonzero return fails. Every module below was verified pure-compute + deterministic + <0.05s with
NO ``research.db`` present (S197 probe: import + run twice, identical outcome).

Deliberately EXCLUDED:
  * ``prereg``, ``exit_lab``      — active prereg-seal lane (S194d/e); do not touch.
  * ``streamband``, ``streamband_managed`` — union/portfolio lane.
  * ``rule_lab_executor``         — already covered (tests/test_rule_lab*.py).
  * ``embase``, ``factory``       — already covered (test_embase_deliv_value, test_momentum_ensemble).
  * ``fractal_fences``            — NOT importable as ``research.explosive_moves.fractal_fences``: it
    pulls in ``cost_participation``, which (like the whole bare ``from explosive_moves.X import ...``
    family — attribution, factor_zoo, cost_realism, v2_backtest, …) is written to run with
    ``research/`` on ``sys.path`` (``python -m explosive_moves.X``), not as a package submodule.
"""
import importlib

import pytest

# 16 modules verified importable-as-package + selftest-clean with no research.db (S197 probe).
_MODULES = [
    "footprint",
    "fractal_floor",
    "evlib",
    "dividend_drift",
    "filing_latency",
    "campaign_arcs",
    "concall_intent",
    "insider_drift",
    "hedge_density_v2",
    "hedge_density",
    "pead_surface",
    "pead",
    "rating_drift",
    "reclaim_selection",
    "rebrand_pump",
    "shp_combos",
    "overnight_split",  # X-04 (S199): overnight/intraday split + overnight-pump flag
    "volume_shelves",   # X-07 (S200): volume-at-price shelves (POC / value area / shelves)
]


@pytest.mark.parametrize("modname", _MODULES)
def test_research_selftest(modname):
    mod = importlib.import_module(f"research.explosive_moves.{modname}")
    fn = getattr(mod, "selftest", None) or getattr(mod, "_selftest", None)
    assert fn is not None, f"{modname} exposes no selftest()/_selftest()"
    rv = fn()
    assert rv is None or rv == 0, f"{modname}.selftest() returned {rv!r} (expected None or 0)"
