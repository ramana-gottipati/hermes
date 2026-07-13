"""AUD-53 — the deals feed survives a transient NSE block instead of losing the day.

Pins deals.py's resilience layer (built on the AUD-14 fetch_retry taxonomy):
  1. _fetch retries a throttle (403/429/5xx) with backoff and succeeds when the block clears;
  2. it gives up after exactly `retries` attempts (a real, now-visible failure — not a crash);
  3. a GENUINE no-data (404 / tiny) is NOT retried (that's a holiday, not a block);
  4. _warm_session never raises (a failed warm-up just runs cold);
  5. fetch_all shares ONE warmed session across bulk + block + fii/dii.
"""
from __future__ import annotations

import types

from src.automation import deals as dl


class _Sess:
    """A fake requests.Session scripted with (status, content) per call; counts calls."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, **kw):
        self.calls += 1
        status, content = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        return types.SimpleNamespace(
            status_code=status, content=content,
            text=content.decode() if isinstance(content, bytes) else content,
            json=lambda: {"ok": 1})


def test_fetch_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(dl.time, "sleep", lambda *a: None)
    s = _Sess([(403, b"x"), (429, b"x"), (200, b"DATA" * 10)])   # blocked twice, then 200
    out = dl._fetch("http://x", session=s)
    assert out == "DATA" * 10 and s.calls == 3                    # retried past the two blocks


def test_fetch_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(dl.time, "sleep", lambda *a: None)
    s = _Sess([(403, b"x")])                                       # always blocked
    assert dl._fetch("http://x", session=s, retries=3) is None
    assert s.calls == 3                                            # exactly 3 attempts, then give up


def test_genuine_no_data_is_not_retried(monkeypatch):
    monkeypatch.setattr(dl.time, "sleep", lambda *a: None)
    s = _Sess([(404, b"")])                                        # a real no-data / holiday
    assert dl._fetch("http://x", session=s) is None
    assert s.calls == 1                                            # NOT retried (not a block)


def test_warm_session_never_raises(monkeypatch):
    def _raise(self, *a, **k):
        raise dl.requests.RequestException("nse down")
    monkeypatch.setattr(dl.requests.Session, "get", _raise)
    s = dl._warm_session()
    assert isinstance(s, dl.requests.Session)                     # cold session, never a crash


def test_fetch_all_shares_one_session(monkeypatch):
    monkeypatch.setattr(dl.time, "sleep", lambda *a: None)
    monkeypatch.setattr(dl, "parse_deals", lambda t, dt: [])
    monkeypatch.setattr(dl, "parse_fiidii", lambda d: [])
    monkeypatch.setattr(dl, "store_deals", lambda rows: len(rows))
    monkeypatch.setattr(dl, "store_fiidii", lambda rows: len(rows))
    s = _Sess([(200, b"x" * 40)])
    dl.fetch_all(session=s)
    assert s.calls == 3                                            # bulk + block + fii/dii on ONE session
