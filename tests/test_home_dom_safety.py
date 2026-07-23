"""test_home_dom_safety.py — Graphite Home DOM-safety gate (Codex #7/#9, spec §7).

News URLs are attacker-influenced; every href must pass `safe_url`, so `javascript:`/`data:` can
never reach the DOM, and unsafe URLs degrade to plain text (no link). All data is escaped.
"""
from __future__ import annotations

from src.web.home import components as C


def test_safe_url_allows_http_and_relative_only():
    assert C.safe_url("https://a.com/x") == "https://a.com/x"
    assert C.safe_url("http://a.com") == "http://a.com"
    assert C.safe_url("/dash/x") == "/dash/x"
    for bad in ("javascript:alert(1)", "data:text/html,x", "vbscript:x", "  JavaScript:x", None, ""):
        assert C.safe_url(bad) == "#", bad


def test_news_wire_never_emits_an_unsafe_href_and_degrades_to_text():
    for bad in ("javascript:alert(1)", "data:text/html;base64,PHN2Zz4=", "vbscript:x"):
        wr = C.wire([{"source": "x", "url": bad, "title": "evil", "sent_at": "2026-07-23"}])
        assert "javascript:" not in wr.lower() and "data:text" not in wr
        assert "<a href" not in wr, ("unsafe url must render as plain text, not a link", bad)


def test_news_wire_escapes_title_and_source():
    wr = C.wire([{"source": "<b>hax", "url": "https://a.com",
                  "title": "<script>x</script>", "sent_at": "t"}])
    assert "<script>" not in wr and "&lt;script&gt;" in wr and "&lt;b&gt;" in wr
