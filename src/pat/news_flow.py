"""Pat 'news' data-flow — headlines answered inline (UX audit S-E Phase 2).

Phase 1 (nav_flow) told users WHERE the news lives; this answers with the headlines
themselves. Recognizes "TCS news / news on RELIANCE / latest headlines / market news
today", resolves an optional ticker, and returns newest-first headlines:

  · a SYMBOL named → that stock's tagged news (`news_tagging.news_for_symbol`),
  · none          → recent market headlines (`news_view._recent_market_news`).

CONTRACT (mirrors nav_flow.py / overdue_flow.py):
  * PURE logic here — `parse_news()` (recognition + a raw ticker candidate; a ₹0
    pre-pass in engine.route) and `symbol_news()` / `market_news()` (bounded reads).
    The HTML render lives in web.py:_news_flow.
  * Recognition is CONSERVATIVE: it needs a news word, and it runs AFTER nav_flow, so
    a page-find ("where do I see the news") stays a navigate. A miss yields None.
  * DESCRIPTIVE / copyright-safe: it shows the headline TITLE + SOURCE + a link out —
    the same treatment as the /dash/wire board. No article text, no advice.
"""
from __future__ import annotations

import re

# a news word must be present for this flow to fire
_NEWS_RE = re.compile(r"\b(news|headlines?|press|articles?|coverage|"
                      r"what'?s happening (?:with|in|on|at)|any updates? on)\b")

# a ticker candidate: an ALL-CAPS token, or the token after on/for/about/around
_ON_RE = re.compile(r"\b(?:on|for|about|around|regarding|re)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_CAPS_RE = re.compile(r"\b([A-Z][A-Z0-9&.\-]{1,14})\b")

# true MARKET-SCOPE words (drop any incidental caps token → market-wide). Recency words
# (today/latest/recent) are NOT here — they modify a named symbol, they don't override it.
_MARKET_RE = re.compile(r"\b(market|general|overall|nifty|sensex|broad|street)\b")

# words that are caps-shaped but never a ticker
_NOT_TICKER = {"NEWS", "HEADLINES", "HEADLINE", "PRESS", "LATEST", "RECENT", "TODAY",
               "MARKET", "TOP", "ANY", "THE", "WHAT", "NIFTY", "SENSEX", "FII", "DII",
               "IPO", "AGM", "CEO", "CFO", "GST", "RBI", "SEBI", "PSU", "NBFC"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _candidate_symbol(query: str) -> str:
    """A raw ticker candidate from the query (UPPER), or '' — VALIDATED later at render.
    'on/for/about X' wins; else a single all-caps token that isn't a news/stop word."""
    q = _norm(query)
    m = _ON_RE.search(q)
    if m:
        tok = m.group(1).upper()
        return tok if tok not in _NOT_TICKER else ""
    caps = [t for t in _CAPS_RE.findall(q) if t.upper() not in _NOT_TICKER]
    # only trust a lone caps token as a ticker (avoids grabbing one of several)
    return caps[0].upper() if len(caps) == 1 else ""


def parse_news(query: str) -> dict | None:
    """"TCS news" / "latest headlines" / "news on RELIANCE" ->
    {flow:"news", params:{symbol}} | None. Needs a news word; extracts a ticker when
    named (market-wide otherwise). Conservative — a miss yields to the normal parse."""
    q = (query or "").strip()
    if not q or not _NEWS_RE.search(q.lower()):
        return None
    sym = _candidate_symbol(q)
    # an explicitly market-wide ask drops any incidental caps token
    if sym and _MARKET_RE.search(q.lower()) and not _ON_RE.search(_norm(q)):
        sym = ""
    return {"flow": "news", "params": {"symbol": sym}}


# ── bounded reads (reuse the tested news reads; never raise) ──────────────────────
def symbol_news(conn, symbol: str, *, limit: int = 12) -> list[dict]:
    """Newest-first headlines tagged to `symbol` (url/title/source/sent_at/method/…)."""
    if conn is None or not symbol:
        return []
    try:
        from src.automation.news_tagging import news_for_symbol
        return news_for_symbol(conn, symbol, limit=limit) or []
    except Exception:
        return []


def market_news(conn, *, limit: int = 12) -> list[dict]:
    """Recent market-wide headlines from the shared feed."""
    if conn is None:
        return []
    try:
        from src.web.news_view import _recent_market_news
        return _recent_market_news(conn, limit=limit) or []
    except Exception:
        return []


def is_symbol(conn, symbol: str) -> bool:
    """Does `symbol` name a real security? (validates the raw candidate at render time)."""
    if conn is None or not symbol:
        return False
    try:
        row = conn.execute("SELECT 1 FROM security_master WHERE symbol=? LIMIT 1",
                           (symbol.strip().upper(),)).fetchone()
        return row is not None
    except Exception:
        return False


def _selftest() -> int:
    # recognition
    assert parse_news("TCS news")["params"]["symbol"] == "TCS"
    assert parse_news("news on RELIANCE")["params"]["symbol"] == "RELIANCE"
    assert parse_news("any updates on INFY")["params"]["symbol"] == "INFY"
    assert parse_news("latest headlines")["params"]["symbol"] == ""
    assert parse_news("market news today")["params"]["symbol"] == ""
    assert parse_news("TCS news today")["params"]["symbol"] == "TCS", "named symbol beats 'today'"
    assert parse_news("what's happening with HDFCBANK")["flow"] == "news"
    # yields — no news word
    assert parse_news("which stocks are accumulating") is None
    assert parse_news("strong stocks in pharma") is None
    assert parse_news("") is None
    # caps stopwords are not tickers
    assert parse_news("FII news")["params"]["symbol"] == "", "FII is not a ticker"
    assert parse_news("IPO news")["params"]["symbol"] == ""
    # a symbol read on a synthetic DB
    import sqlite3
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY)")
    c.execute("INSERT INTO security_master VALUES ('TCS')")
    c.execute("CREATE TABLE sent_news(id INTEGER PRIMARY KEY, url TEXT, title TEXT, source TEXT, sent_at TEXT)")
    c.execute("INSERT INTO sent_news(url,title,source,sent_at) VALUES "
              "('http://x/1','Q2 results beat','Mint','2026-07-14')")
    assert is_symbol(c, "TCS") and not is_symbol(c, "ZZZZ")
    assert market_news(c)[0]["title"] == "Q2 results beat"
    assert market_news(None) == [] and symbol_news(None, "TCS") == []
    c.close()
    print("news_flow selftest OK — recognition (symbol extract; market-wide; caps-stopword "
          "reject; yields w/o a news word) + bounded market/symbol reads (defensive).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
