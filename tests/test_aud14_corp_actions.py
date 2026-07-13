"""AUD-14 (corp_actions sibling) — a throttled corp-actions window is retried, not counted
as a breaker failure; a genuine failure (non-200 / bad JSON) still returns None immediately.

Guards the re-raise surgery on fetch_window's old blanket `except Exception: return None`.
"""
from __future__ import annotations

import types

from src.automation import corp_actions as ca


class _Sess:
    """Fake requests.Session; scripted (status, payload) per call. payload=Exception → .json() raises."""
    def __init__(self, seq):
        self.seq = list(seq)
        self.calls = 0

    def get(self, url, **kw):
        self.calls += 1
        status, payload = self.seq[min(self.calls - 1, len(self.seq) - 1)]

        def _json():
            if isinstance(payload, Exception):
                raise payload
            return payload
        return types.SimpleNamespace(status_code=status, json=_json)


def test_window_retries_throttle_then_succeeds(monkeypatch):
    monkeypatch.setattr(ca.time, "sleep", lambda *a: None)
    s = _Sess([(403, None), (200, {"data": [{"symbol": "X"}]})])
    rows = ca.fetch_window("2026-07-01", "2026-07-10", session=s, headers={})
    assert rows == [{"symbol": "X"}] and s.calls == 2       # retried past the 403


def test_window_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(ca.time, "sleep", lambda *a: None)
    s = _Sess([(429, None)])
    assert ca.fetch_window("2026-07-01", "2026-07-10", session=s, headers={}, retries=3) is None
    assert s.calls == 3                                      # 3 attempts, then None (breaker counts it)


def test_window_genuine_non200_not_retried(monkeypatch):
    monkeypatch.setattr(ca.time, "sleep", lambda *a: None)
    s = _Sess([(404, None)])
    assert ca.fetch_window("2026-07-01", "2026-07-10", session=s, headers={}) is None
    assert s.calls == 1                                      # 404 is a real failure, not a throttle


def test_window_empty_is_empty_list(monkeypatch):
    s = _Sess([(200, {"data": []})])
    assert ca.fetch_window("2026-07-01", "2026-07-10", session=s, headers={}) == []   # genuine empty


def test_window_bad_json_not_retried(monkeypatch):
    monkeypatch.setattr(ca.time, "sleep", lambda *a: None)
    s = _Sess([(200, ValueError("bad json"))])
    assert ca.fetch_window("2026-07-01", "2026-07-10", session=s, headers={}) is None
    assert s.calls == 1                                      # a parse error is not a throttle
