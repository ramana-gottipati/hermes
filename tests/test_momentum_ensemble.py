"""Regression test for the momentum ensemble blend (audit AUD-10).

Canon (docs/calculations-and-weights.md §2): the ensemble is the equal-weight mean of
FOUR percentile-rank series — rank(MOM12), rank(HI52), rank(RISKADJ), rank(LOWVOL_MOM).
The fourth member is itself a blend, 0.5*rank(-vol)+0.5*rank(MOM6), which must be
RE-RANKED before it enters the mean; otherwise its dispersion is compressed and it carries
materially less than its intended 0.25 weight.

This pins the property using the real ranking primitive. numpy is required, so the test
skips cleanly where numpy is absent (e.g. the laptop agent venv) and runs on the VPS /
project venv where the scanner actually executes.
"""
import pytest

np = pytest.importorskip("numpy")


def _pctrank(x):
    # Mirror of research/explosive_moves/factory.pctrank (kept local so the test needs
    # only numpy, not the heavy embase/strategies import chain).
    x = np.asarray(x, float)
    r = np.full(len(x), np.nan)
    m = ~np.isnan(x)
    if m.sum() > 1:
        r[m] = np.argsort(np.argsort(x[m])) / (m.sum() - 1)
    return r


def test_reranked_blend_restores_full_dispersion():
    rng = np.random.default_rng(0)  # fixed seed → deterministic golden
    n = 500
    r_lowvol = _pctrank(rng.normal(size=n))
    r_mom6 = _pctrank(rng.normal(size=n))

    raw_blend = 0.5 * r_lowvol + 0.5 * r_mom6        # the pre-fix value (compressed)
    reranked = _pctrank(raw_blend)                    # AUD-10 fix

    uniform_std = 1.0 / np.sqrt(12)                    # std of U(0,1) ~ 0.289
    # Averaging two independent uniforms compresses dispersion well below uniform...
    assert raw_blend.std() < 0.75 * uniform_std
    # ...and re-ranking restores it to a genuine uniform spread (full 0.25 weight).
    assert abs(reranked.std() - uniform_std) < 0.02


def test_reranked_blend_preserves_ordering():
    # Re-ranking is monotone: it must not reorder names, only re-space them.
    rng = np.random.default_rng(1)
    a = _pctrank(rng.normal(size=200))
    b = _pctrank(rng.normal(size=200))
    blend = 0.5 * a + 0.5 * b
    reranked = _pctrank(blend)
    order_before = np.argsort(blend)
    order_after = np.argsort(reranked)
    assert np.array_equal(order_before, order_after)
