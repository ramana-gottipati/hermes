"""Per-symbol news tagging — the P4 backend dependency for UI Architecture v2.

`sent_news` is a market-wide headline feed (id, source, url, title, sent_at) with
NO per-symbol association. The v2 design (docs/ui-architecture-v2.md §7) needs each
headline tagged with the stock(s) it concerns so the stock dossier can grow a
"Timeline" tab and the Markets page a watchlist-scoped "Wire" rail. This module is
the keystone backend that produces those tags.

DOCTRINE (CLAUDE.md): rule-based, NO LLM — a deterministic gazetteer matcher over
the official `nse_equity_list` company-name registry. Zero API spend, zero Sonnet,
safe in a nightly timer. (The going-forward path can ALSO persist the per-item
`tickers` that news_feed.py's classifier already computes for free — see
`tag_url()` and the note at the bottom of this file.)

PRECISION-FIRST: it would rather miss a headline than mis-tag one — a wrong symbol
on the dossier Timeline is worse than a gap. Consequences of that stance:
  • Generic tokens (Power, Oil, Bank, India, Finance…) never match on their own.
  • Brand names that differ from the legal name are MISSED in v1 — "Nykaa" (legal
    name FSN E-Commerce Ventures), "RIL"/"Jio" (Reliance), "JAL" (Jaiprakash). They
    need an alias map (a documented future enhancement); the forward classifier
    path also recovers many of them.
  • Ambiguous single names ("Aarti" → Industries/Drugs/Pharmalabs) only match when
    the distinctive multi-word name is present.

Isolation (per §0.8): brand-new module; owns its `news_symbol_tags` table via
ensure_schema() — NO edit to db.py SCHEMA_BASE, no contended-file edit. Inert until
something reads it; the Timeline/Wire UI wiring is gate-deferred. The backfill is a
self-contained data-layer task that can run independently (§14.3 P4).

CLI:
    python -m src.automation.news_tagging --backfill          # tag untagged sent_news
    python -m src.automation.news_tagging --rebuild           # re-tag everything
    python -m src.automation.news_tagging --probe "Headline"  # dry-run one title
    python -m src.automation.news_tagging --stats             # coverage summary
"""
from __future__ import annotations

import argparse
import logging
import re
from typing import Iterable, Optional

log = logging.getLogger("hermes.news_tagging")

# --- owned table (fold into db.py SCHEMA_BASE later, when the tree frees) ----
_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_symbol_tags (
    news_url   TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    method     TEXT NOT NULL DEFAULT 'name',   -- 'name' | 'symbol' | 'classifier'
    confidence REAL NOT NULL DEFAULT 1.0,
    tagged_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(news_url, symbol)
);
CREATE INDEX IF NOT EXISTS idx_news_tags_symbol ON news_symbol_tags(symbol);
CREATE INDEX IF NOT EXISTS idx_news_tags_url    ON news_symbol_tags(news_url);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


# --- normalization ----------------------------------------------------------
_LEGAL_SUFFIX = {"limited", "ltd"}   # tokens are punctuation-free, so "ltd."/"lim" need not appear
_LEAD_DROP = {"the"}


def _tokens(s: str) -> list[str]:
    """Lowercase alphanumeric token stream. '&amp;', '&' and punctuation all act
    as boundaries, so name-keys and titles tokenize identically."""
    s = (s or "").replace("&amp;", " ").replace("&", " ").lower()
    return re.findall(r"[a-z0-9]+", s)


def _name_key(company_name: str) -> list[str]:
    """The distinctive token sequence of a company name (legal suffix stripped)."""
    toks = _tokens(company_name)
    while toks and toks[0] in _LEAD_DROP:
        toks = toks[1:]
    while toks and toks[-1] in _LEGAL_SUFFIX:
        toks = toks[:-1]
    return toks


# A single-token name-key is trusted ONLY if it is long enough AND not a generic
# market/finance word. (Multi-token keys are distinctive enough to trust as-is.)
_MIN_SINGLE_LEN = 5
_GENERIC = {
    "india", "bharat", "national", "power", "energy", "oil", "gas", "iron", "steel",
    "coal", "finance", "financial", "bank", "banks", "capital", "motors", "auto",
    "cement", "cements", "sugar", "paper", "papers", "textiles", "fashion", "fashions",
    "drugs", "pharma", "pharmaceuticals", "infra", "infrastructure", "technologies",
    "technology", "digital", "global", "industries", "industry", "solutions", "systems",
    "services", "products", "enterprises", "holdings", "ventures", "securities",
    "electricals", "chemicals", "petrochemicals", "metals", "minerals", "mining",
    "foods", "agro", "exports", "trading", "traders", "investments", "projects",
    "developers", "realty", "estates", "properties", "logistics", "shipping", "ports",
    "telecom", "media", "entertainment", "retail", "consumer", "health", "healthcare",
    "hospitals", "laboratories", "engineering", "construction", "petroleum", "gold",
    "silver", "international", "overseas", "corporation", "company", "group", "future",
    "alpha", "beta", "gamma", "delta",
}

# --- symbol (acronym) matching ----------------------------------------------
# Headlines name big tickers by their acronym, not their full legal name
# ("TCS", "GAIL", "NTPC"). We match a symbol ONLY when it appears as a STANDALONE
# ALL-CAPS token in the original (pre-lowercase) title — generic words are written
# Title-case or lowercase, so this is a strong precision guard.
_MIN_SYMBOL_LEN = 3
_CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,}\b")
# all-caps tokens that recur in market headlines and must never be read as a ticker
# (belt-and-suspenders on top of the symbol-set intersection).
_CAPS_BLOCK = {
    "IPO", "GMP", "NSE", "BSE", "SEBI", "RBI", "GDP", "CPI", "WPI", "FII", "DII",
    "FIIS", "DIIS", "QIP", "FPO", "ESOP", "PSU", "NBFC", "SME", "ATH", "UPI", "GST",
    "API", "USD", "INR", "EUR", "NAV", "AGM", "EGM", "MCAP", "EPS", "PAT", "EBITDA",
    "ROE", "ROCE", "YOY", "QOQ", "MOM", "CEO", "CFO", "MD", "IT", "AI", "EV", "ESG",
    "FED", "FOMC", "OPEC", "GDPR", "CY26", "CY25", "FY26", "FY27", "FY30", "DST",
    "MF", "MFS", "ETF", "ETFS", "SIP", "NFO", "AUM", "PLI", "MSP", "GMV", "ARPU",
    "USA", "UAE", "UK", "RIL",
}


class _Index:
    __slots__ = ("by_first", "symbols", "size")

    def __init__(self):
        self.by_first: dict[str, list[tuple[tuple[str, ...], str]]] = {}
        self.symbols: set[str] = set()
        self.size = 0


def build_index(pairs: Iterable[tuple[str, str]]) -> _Index:
    """Build the matcher index from (symbol, company_name) pairs.

    Kept decoupled from the DB so it can be unit-tested / verified against an
    exported registry without a live connection.
    """
    idx = _Index()
    seen_keys = 0
    for symbol, name in pairs:
        symbol = (symbol or "").strip().upper()
        if not symbol:
            continue
        # symbol (acronym) match candidates
        if (len(symbol) >= _MIN_SYMBOL_LEN and symbol.isalnum()
                and symbol[0].isalpha() and symbol not in _CAPS_BLOCK):
            idx.symbols.add(symbol)
        # name-key match candidates
        key = tuple(_name_key(name))
        if not key:
            continue
        if len(key) == 1:
            t = key[0]
            if len(t) < _MIN_SINGLE_LEN or t in _GENERIC or t.isdigit():
                continue
        idx.by_first.setdefault(key[0], []).append((key, symbol))
        seen_keys += 1
    # longest keys first within each bucket → prefer the most specific match
    for bucket in idx.by_first.values():
        bucket.sort(key=lambda kv: len(kv[0]), reverse=True)
    idx.size = seen_keys
    return idx


def build_index_from_conn(conn) -> _Index:
    rows = conn.execute(
        "SELECT symbol, company_name FROM nse_equity_list "
        "WHERE company_name IS NOT NULL AND company_name <> ''"
    ).fetchall()
    return build_index((r["symbol"], r["company_name"]) for r in rows)


def match_title(title: str, index: _Index) -> dict[str, tuple[str, float, int]]:
    """Return {symbol: (method, confidence, span_len)} for a single headline.

    Two passes — distinctive company-name phrases, then standalone all-caps
    acronym tickers — followed by span-containment suppression so a short match
    nested inside a longer one is dropped (e.g. the acronym "IDFC" inside the
    phrase "IDFC First Bank", or a parent name inside a subsidiary's full name)."""
    toks = _tokens(title)
    n = len(toks)
    cands: list[tuple[int, int, str, str, float]] = []   # (start, end, symbol, method, conf)

    # 1) name-key phrase matches (contiguous sublist of the title's tokens)
    for i, tok in enumerate(toks):
        bucket = index.by_first.get(tok)
        if not bucket:
            continue
        for key, sym in bucket:           # longest keys first
            L = len(key)
            if i + L <= n and tuple(toks[i:i + L]) == key:
                cands.append((i, i + L, sym, "name", 1.0 if L >= 2 else 0.9))

    # 2) symbol (acronym) matches — standalone ALL-CAPS token in the raw title
    if index.symbols:
        for m in _CAPS_RE.finditer(title or ""):
            cap = m.group(0)
            if cap in _CAPS_BLOCK or cap not in index.symbols:
                continue
            low = cap.lower()
            for j, t in enumerate(toks):           # tie the acronym to its token position(s)
                if t == low:
                    cands.append((j, j + 1, cap, "symbol", 0.8))

    # 3) suppress any candidate strictly contained within a longer one
    kept = [a for a in cands if not any(
        b is not a and b[0] <= a[0] and a[1] <= b[1] and (b[1] - b[0]) > (a[1] - a[0])
        for b in cands)]

    # 4) collapse to the best entry per symbol (highest confidence, then widest span)
    found: dict[str, tuple[str, float, int]] = {}
    for s, e, sym, method, conf in kept:
        span = e - s
        prev = found.get(sym)
        if prev is None or (conf, span) > (prev[1], prev[2]):
            found[sym] = (method, conf, span)
    return found


# --- persistence ------------------------------------------------------------

def tag_url(conn, news_url: str, symbols: Iterable[str], *,
            method: str = "classifier", confidence: float = 0.95) -> int:
    """Persist explicit (url → symbols) tags. Used by the going-forward path to
    save the classifier's `tickers` (see note at bottom). Returns rows inserted."""
    ensure_schema(conn)
    written = 0
    for s in symbols:
        s = (s or "").strip().upper()
        if not s:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO news_symbol_tags (news_url, symbol, method, confidence) "
            "VALUES (?, ?, ?, ?)", (news_url, s, method, confidence))
        written += cur.rowcount or 0
    return written


def backfill(conn, *, rebuild: bool = False, limit: Optional[int] = None) -> dict:
    """Tag sent_news headlines by name/symbol match. Idempotent (INSERT OR IGNORE);
    skips rows already tagged unless rebuild=True. Returns a stats dict."""
    ensure_schema(conn)
    index = build_index_from_conn(conn)
    if rebuild:
        conn.execute("DELETE FROM news_symbol_tags WHERE method IN ('name', 'symbol')")

    q = "SELECT url, title FROM sent_news"
    if not rebuild:
        q += (" WHERE url NOT IN (SELECT news_url FROM news_symbol_tags "
              "WHERE method IN ('name', 'symbol'))")
    q += " ORDER BY id"
    if limit:
        q += f" LIMIT {int(limit)}"
    rows = conn.execute(q).fetchall()

    headlines_tagged = tags_written = 0
    for r in rows:
        matches = match_title(r["title"], index)
        if matches:
            headlines_tagged += 1
        for sym, (method, conf, _span) in matches.items():
            cur = conn.execute(
                "INSERT OR IGNORE INTO news_symbol_tags (news_url, symbol, method, confidence) "
                "VALUES (?, ?, ?, ?)", (r["url"], sym, method, conf))
            tags_written += cur.rowcount or 0
    conn.commit()
    return {
        "symbols_in_index": index.size,
        "acronyms_in_index": len(index.symbols),
        "headlines_scanned": len(rows),
        "headlines_tagged": headlines_tagged,
        "tags_written": tags_written,
    }


# --- read API (for the future dossier Timeline tab + Markets Wire) ----------

def news_for_symbol(conn, symbol: str, *, limit: int = 50,
                    min_confidence: float = 0.0) -> list[dict]:
    """Headlines tagged to one symbol, newest first. The dossier Timeline reads this."""
    ensure_schema(conn)
    rows = conn.execute(
        """SELECT n.url, n.title, n.source, n.sent_at, t.method, t.confidence
           FROM news_symbol_tags t JOIN sent_news n ON n.url = t.news_url
           WHERE t.symbol = ? AND t.confidence >= ?
           ORDER BY n.sent_at DESC, n.id DESC LIMIT ?""",
        (symbol.strip().upper(), min_confidence, int(limit))).fetchall()
    return [dict(r) for r in rows]


def wire_for_symbols(conn, symbols: Iterable[str], *, limit: int = 40) -> list[dict]:
    """Recent headlines across a set of symbols (the watchlist-scoped Markets Wire)."""
    syms = [s.strip().upper() for s in symbols if s and s.strip()]
    if not syms:
        return []
    ensure_schema(conn)
    ph = ",".join("?" * len(syms))
    rows = conn.execute(
        f"""SELECT n.url, n.title, n.source, n.sent_at,
                   GROUP_CONCAT(DISTINCT t.symbol) AS symbols
            FROM news_symbol_tags t JOIN sent_news n ON n.url = t.news_url
            WHERE t.symbol IN ({ph})
            GROUP BY n.url ORDER BY n.sent_at DESC, n.id DESC LIMIT ?""",
        (*syms, int(limit))).fetchall()
    return [dict(r) for r in rows]


def stats(conn) -> dict:
    ensure_schema(conn)
    total = conn.execute("SELECT COUNT(*) c FROM sent_news").fetchone()["c"]
    tagged = conn.execute(
        "SELECT COUNT(DISTINCT news_url) c FROM news_symbol_tags").fetchone()["c"]
    tags = conn.execute("SELECT COUNT(*) c FROM news_symbol_tags").fetchone()["c"]
    by_method = {r["method"]: r["c"] for r in conn.execute(
        "SELECT method, COUNT(*) c FROM news_symbol_tags GROUP BY method")}
    top = [dict(r) for r in conn.execute(
        "SELECT symbol, COUNT(*) c FROM news_symbol_tags GROUP BY symbol "
        "ORDER BY c DESC LIMIT 15")]
    return {"sent_news": total, "headlines_tagged": tagged,
            "tags": tags, "by_method": by_method, "top_symbols": top}


# --- CLI --------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Per-symbol tagging of sent_news (rule-based, no LLM).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--backfill", action="store_true", help="tag untagged headlines")
    g.add_argument("--rebuild", action="store_true", help="re-tag every headline from scratch")
    g.add_argument("--stats", action="store_true", help="coverage summary")
    g.add_argument("--probe", metavar="TITLE", help="dry-run the matcher on one headline")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    from src.core.db import get_conn

    if args.probe:
        with get_conn() as conn:
            index = build_index_from_conn(conn)
        m = match_title(args.probe, index)
        print(f"matched {len(m)} symbol(s):")
        for sym, (method, conf, span) in sorted(m.items()):
            print(f"  {sym:14} {method:7} conf={conf:.2f} span={span}")
        return

    with get_conn() as conn:
        if args.stats:
            import json
            print(json.dumps(stats(conn), indent=2))
        else:
            result = backfill(conn, rebuild=args.rebuild, limit=args.limit)
            log.info("backfill done: %s", result)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# GOING-FORWARD PATH — WIRED (news_feed._persist_news_tags, called after mark_sent
# on every news run). For each freshly-sent headline it runs BOTH this module's
# rule-based match_title (so a clearly-named company is tagged even when the
# classifier filed the item as OTHER) AND tag_url() on the classifier's `tickers`
# (recovers brand≠legal-name cases the gazetteer misses — Nykaa, RIL, Jio…). So
# `backfill` is the one-time history catch-up; the hook keeps new news tagged with
# no separate timer. `tag_url` remains the public helper for any external caller.
# -----------------------------------------------------------------------------
