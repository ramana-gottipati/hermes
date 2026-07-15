"""D5-F6 regression: embase `deliv_qty_trend` must trend delivered VALUE (dq × raw close),
not raw delivered SHARE COUNT — so a split inside the trailing window can no longer inflate it.

Track C verified the leak real-but-minor (~+0.09 Sharpe to QUAL_MOM). This pins the fix so the
feature can never silently regress to the split-sensitive raw-quantity trend.
"""
from types import SimpleNamespace

import pytest

# research-venv dependency — skip cleanly where numpy is absent (the VPS main venv
# and fresh worktrees), instead of failing COLLECTION for the whole suite. Same
# pattern as tests/test_rule_lab_executor.py. Must run BEFORE the embase import
# below (embase imports numpy at module level).
np = pytest.importorskip("numpy")

from research.explosive_moves import embase


def _series_with_split(n=130, split_at=100):
    """A synthetic symbol whose delivered VALUE is constant across a 2:1 split.

    Pre-split : price 100, deliv_qty 1000  -> delivered value 100_000
    Post-split: price  50, deliv_qty 2000  -> delivered value 100_000  (economically unchanged)

    The RAW-quantity trend jumps at the split (1000 -> 2000); the delivered-VALUE trend must not.
    """
    close = np.where(np.arange(n) < split_at, 100.0, 50.0)
    dq = np.where(np.arange(n) < split_at, 1000.0, 2000.0)
    adj = np.full(n, 50.0)  # back-adjusted continuous series (irrelevant to the assertion)
    return SimpleNamespace(
        n=n, close=close, open=close.copy(),
        adj_close=adj, adj_high=adj, adj_low=adj,
        volume=np.full(n, 5000.0), deliv_qty=dq,
    )


def test_deliv_trend_is_split_invariant():
    ss = _series_with_split()
    feats = embase.compute_entry_features(ss)
    trend = feats["deliv_qty_trend"]

    # last bar: 22d window fully post-split, 66d window straddles the split.
    last = float(trend[-1])
    assert np.isfinite(last)
    # delivered VALUE is constant -> the value trend is ~1.0 (no split artifact).
    assert last == pytest.approx(1.0, abs=1e-6)

    # Prove the fix bites: the OLD raw-quantity formula would have been materially > 1 here.
    dq = ss.deliv_qty
    dm22 = np.nanmean(dq[-22:])
    dm66 = np.nanmean(dq[-66:])
    raw_qty_trend = dm22 / dm66
    assert raw_qty_trend > 1.3  # the split inflation the fix removes
    assert last < raw_qty_trend  # value trend is not fooled by the split


def test_deliv_trend_tracks_real_value_growth():
    """A genuine RECENT rise in delivered value (no split) must still register as a trend > 1."""
    n = 130
    close = np.full(n, 100.0)
    # tripling concentrated in the last 22 sessions (const price) -> recent > medium-term baseline.
    dq = np.where(np.arange(n) < n - 22, 1000.0, 3000.0)
    adj = np.full(n, 100.0)
    ss = SimpleNamespace(n=n, close=close, open=close.copy(),
                         adj_close=adj, adj_high=adj, adj_low=adj,
                         volume=np.full(n, 5000.0), deliv_qty=dq)
    trend = embase.compute_entry_features(ss)["deliv_qty_trend"]
    assert float(trend[-1]) > 1.2  # real value growth is preserved
