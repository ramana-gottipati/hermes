"""AUD-14 — an NSE throttle/block is NEVER silently recorded as a market holiday.

Pins the shared taxonomy (fetch_retry) + bhavcopy's use of it:
  1. raise_if_retryable raises only on 403/429/5xx;
  2. _try_fetch raises RetryableFetchError on a throttle / network error, returns None on a
     genuine no-data (404/tiny), returns bytes on 200;
  3. ingest_date leaves a throttled date UN-marked (retry), sentinels an OLD no-data day as a
     row_count=0 holiday, but leaves a RECENT no-data day pending (data may still post);
  4. run_recent scans the FULL 7-day lookback instead of early-returning on the first success.
"""
from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone

import pytest

from src.automation import fetch_retry as fr
from src.automation import bhavcopy as bc


def _resp(status, content=b"x" * 300):
    return types.SimpleNamespace(status_code=status, content=content)


def test_raise_if_retryable_only_on_block():
    for s in (403, 429, 500, 502, 503, 504):
        with pytest.raises(fr.RetryableFetchError):
            fr.raise_if_retryable(s, "u")
    for s in (200, 404, 301, 410):
        fr.raise_if_retryable(s, "u")      # no-op — a genuine no-data / redirect is not retryable


def test_try_fetch_throttle_vs_holiday(monkeypatch):
    monkeypatch.setattr(bc.requests, "get", lambda *a, **k: _resp(403))
    with pytest.raises(fr.RetryableFetchError):
        bc._try_fetch("http://x")                       # 403 → throttle
    monkeypatch.setattr(bc.requests, "get", lambda *a, **k: _resp(404, b""))
    assert bc._try_fetch("http://x") is None             # 404 → holiday/no-data
    monkeypatch.setattr(bc.requests, "get", lambda *a, **k: _resp(200, b"a" * 300))
    assert bc._try_fetch("http://x") == b"a" * 300       # 200 → content

    def _boom(*a, **k):
        raise bc.requests.RequestException("net down")
    monkeypatch.setattr(bc.requests, "get", _boom)
    with pytest.raises(fr.RetryableFetchError):
        bc._try_fetch("http://x")                       # network error → retryable, not a holiday


def _stub_marks(monkeypatch):
    marked = []
    monkeypatch.setattr(bc, "date_already_done", lambda iso, **k: False)
    monkeypatch.setattr(bc, "mark_date_done", lambda *a, **k: marked.append(a))
    return marked


def test_ingest_date_throttle_is_left_for_retry(monkeypatch):
    marked = _stub_marks(monkeypatch)
    monkeypatch.setattr(bc, "fetch_for_date",
                        lambda d: (_ for _ in ()).throw(fr.RetryableFetchError("HTTP 429")))
    ok, msg, ins = bc.ingest_date(datetime(2026, 7, 10))
    assert ok is False and "BLOCKED" in msg and ins == 0
    assert marked == []                                  # a throttle is NEVER marked done


def test_ingest_date_old_no_data_sentinels(monkeypatch):
    marked = _stub_marks(monkeypatch)
    monkeypatch.setattr(bc, "fetch_for_date", lambda d: None)
    old = datetime.now(timezone.utc).astimezone() - timedelta(days=5)
    ok, msg, ins = bc.ingest_date(old)
    assert "holiday sentinel" in msg
    assert marked and marked[0][2] == 0                  # row_count=0 sentinel recorded


def test_ingest_date_recent_no_data_stays_pending(monkeypatch):
    marked = _stub_marks(monkeypatch)
    monkeypatch.setattr(bc, "fetch_for_date", lambda d: None)
    recent = datetime.now(timezone.utc).astimezone()     # age 0 < 3 days
    ok, msg, ins = bc.ingest_date(recent)
    assert ok is False and "pending" in msg
    assert marked == []                                  # NOT sentineled — data may still post


def test_run_recent_scans_full_lookback_not_early_return(monkeypatch):
    calls = []
    monkeypatch.setattr(bc, "date_already_done", lambda iso: False)   # nothing done → attempt all weekdays
    monkeypatch.setattr(bc.time, "sleep", lambda *a: None)

    def _fake_ingest(d):
        iso = d.strftime("%Y-%m-%d")
        calls.append(iso)
        return True, f"{iso} ok", 1                      # every day succeeds
    monkeypatch.setattr(bc, "ingest_date", _fake_ingest)
    ok, msg = bc.run_recent()
    assert ok is True
    assert len(calls) >= 4                               # NOT early-returned after day 1 (old bug)
