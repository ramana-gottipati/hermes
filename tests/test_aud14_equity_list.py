"""AUD-14 (equity_list sibling, last) — a throttle is LABELLED distinctly and keeps the existing
universe (run()/run_etfs never wipe on []); a genuine bad response / parse is unaffected.

equity_list was already self-healing (empty fetch → keep the prior allowlist + AUD-43 shrink
guard), so this is a diagnostic-visibility + taxonomy-consistency port, behaviour-preserving.
"""
from __future__ import annotations

import logging
import types

from src.automation import equity_list as el


def _resp(status, text="SYMBOL,NAME OF COMPANY\nX,Xco\n"):
    return types.SimpleNamespace(status_code=status, text=text, json=lambda: {"data": []})


def test_fetch_equities_throttle_returns_empty_and_is_labelled(monkeypatch, caplog):
    monkeypatch.setattr(el.requests, "get", lambda *a, **k: _resp(403, ""))
    with caplog.at_level(logging.WARNING, logger="hermes.equity_list"):
        assert el.fetch_equities() == []                 # throttle → [] (run() keeps the universe)
    assert any("BLOCKED/throttled" in r.getMessage() for r in caplog.records)


def test_fetch_equities_network_error_returns_empty(monkeypatch):
    def _boom(*a, **k):
        raise el.requests.RequestException("net down")
    monkeypatch.setattr(el.requests, "get", _boom)
    assert el.fetch_equities() == []


def test_fetch_equities_bad_response_returns_empty(monkeypatch):
    monkeypatch.setattr(el.requests, "get", lambda *a, **k: _resp(200, "no header here"))
    assert el.fetch_equities() == []                     # missing SYMBOL header → bad response


def test_fetch_equities_success_parses(monkeypatch):
    csv_text = ("SYMBOL,NAME OF COMPANY,ISIN NUMBER,DATE OF LISTING\n"
                "RELIANCE,Reliance,INE001,2000-01-01\n")
    monkeypatch.setattr(el.requests, "get", lambda *a, **k: _resp(200, csv_text))
    out = el.fetch_equities()
    assert len(out) == 1 and out[0]["symbol"] == "RELIANCE"


def test_fetch_etfs_throttle_returns_empty_and_is_labelled(monkeypatch, caplog):
    class _FakeSess:
        def get(self, url, **k):
            return _resp(403)
    monkeypatch.setattr(el.requests, "Session", lambda: _FakeSess())
    with caplog.at_level(logging.WARNING, logger="hermes.equity_list"):
        assert el.fetch_etfs() == []
    assert any("BLOCKED/throttled" in r.getMessage() for r in caplog.records)
