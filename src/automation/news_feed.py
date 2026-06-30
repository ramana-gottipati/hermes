"""Indian market news → classified, tagged, impact-aware Telegram brief.

Each run:
  1. Pulls recent headlines from 4 Indian market RSS feeds
  2. Dedupes against sent_news (won't re-send anything previously sent)
  3. Sends the batch to Claude Haiku as a single classification call:
     - category (EARNINGS / MACRO / CORPORATE_ACTION / STOCK_SPECIFIC / OTHER)
     - tag (BEAT/MISS/INLINE, RBI/GLOBAL/RATES, BONUS/SPLIT/DIVIDEND, etc.)
     - extraordinary flag (true for surprises / structural moves)
     - tickers + impact summary for macro / sector news
  4. Filters out low-signal items (OTHER, INLINE earnings, non-extraordinary noise)
  5. Posts a single structured Telegram message grouped by section, with tags

Cost per run: ~$0.005 on Haiku (well under a cent). Twice daily = ~$0.30/month.

Usage (standalone): python -m src.automation.news_feed
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

import feedparser
import requests
from anthropic import APIError

from src.core.db import get_conn
from src.core.llm import client
from src.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("hermes.news")

# --- Sources ----------------------------------------------------------------

FEEDS: dict[str, str] = {
    "Moneycontrol":      "https://www.moneycontrol.com/rss/marketreports.xml",
    "Livemint":          "https://www.livemint.com/rss/markets",
    "ET Markets":        "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms",
    "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
}

MAX_ITEM_AGE_HOURS = 12       # don't classify stale headlines
MAX_ITEMS_FETCHED  = 30       # cap input to keep Claude call cheap
MAX_ITEMS_PER_SOURCE = 10     # so one chatty source can't crowd out others

# --- RSS handling -----------------------------------------------------------

def _entry_timestamp(entry) -> float | None:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            return time.mktime(parsed)
    return None


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_recent(source: str, feed_url: str) -> list[dict]:
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        log.warning("failed to parse %s: %s", source, e)
        return []

    if feed.bozo and not feed.entries:
        log.warning("feed %s returned no entries", source)
        return []

    cutoff = time.time() - MAX_ITEM_AGE_HOURS * 3600
    items: list[dict] = []

    for entry in feed.entries[:25]:
        ts = _entry_timestamp(entry)
        if ts is not None and ts < cutoff:
            continue
        title = _strip_html(entry.get("title") or "")
        url = (entry.get("link") or "").strip()
        summary = _strip_html(entry.get("summary") or "")[:300]
        if not title or not url:
            continue
        items.append({
            "source": source,
            "title": title,
            "summary": summary,
            "url": url,
            "published_ts": ts,
        })

    items.sort(key=lambda x: x["published_ts"] or 0, reverse=True)
    return items[:MAX_ITEMS_PER_SOURCE]


# --- Dedupe via SQLite ------------------------------------------------------

def is_already_sent(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM sent_news WHERE url = ?", (url,)).fetchone()
        return row is not None


def mark_sent(item: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_news (source, url, title) VALUES (?, ?, ?)",
            (item["source"], item["url"], item["title"]),
        )


# --- Classifier (Claude Haiku) ---------------------------------------------

CLASSIFIER_SYSTEM = """You classify Indian stock-market news with the eye of a buy-side analyst. Output STRICT JSON only — no prose before or after, no markdown fence."""

CLASSIFIER_USER_TEMPLATE = """Classify each numbered item below. For each, output one JSON object with EXACTLY these keys:

  "n":          (int) the item number as given
  "category":   one of: EARNINGS, MACRO, CORPORATE_ACTION, STOCK_SPECIFIC, OTHER
  "tag":        a SHORT label appropriate to the category, e.g.:
                  EARNINGS         → BEAT | MISS | INLINE | RESULTS_OUT
                  MACRO            → RBI | RATES | INFLATION | GLOBAL | CURRENCY | POLICY | OIL | GDP
                  CORPORATE_ACTION → BONUS | SPLIT | DIVIDEND | BUYBACK | MERGER | DELISTING | RESIGN
                  STOCK_SPECIFIC   → UPGRADE | DOWNGRADE | TARGET | NEWS | DEAL | LITIGATION
                  OTHER            → ""
  "tickers":    JSON array of up to 5 NSE tickers (uppercase, no .NS suffix) directly impacted.
                For MACRO items, list the most relevant Indian beneficiaries/losers.
                For OTHER items, return [].
  "impact":     A <=25-word note for MACRO and significant SECTOR news, explaining what
                this means for Indian stocks (and global linkages if relevant). Empty "" for
                routine items.
  "extraordinary": true/false. true ONLY for genuine surprises: large beats/misses, structural
                regulatory shifts, unexpected M&A, sharp sector rotations, black-swan-style news.
                Routine results and commentary = false.
  "one_line":   <=15-word punchy summary an analyst would write.

Filter philosophy: be RUTHLESS. Most market noise is OTHER. Reserve EARNINGS/MACRO/CORPORATE_ACTION
for items with real signal. Mark extraordinary sparingly — once per batch on average.

Output a single JSON array. No commentary, no markdown, just the array.

Items:
{items_block}
"""


def _items_block(items: list[dict]) -> str:
    lines = []
    for i, item in enumerate(items, start=1):
        # Cap the title too, not just the summary — an unbounded title would inflate the
        # classifier LLM input (token cost / context blow-out). (CL-PROV-12)
        title = (item.get("title") or "")[:300]
        lines.append(f"{i}. [{item['source']}] {title}")
        if item.get("summary"):
            lines.append(f"   {item['summary'][:200]}")
    return "\n".join(lines)


def _safe_parse_json(text: str) -> list[dict]:
    """Find the first JSON array in the response and parse it."""
    # Strip code fences if model emitted any despite instructions
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    # Find first [ ... ]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as e:
        log.warning("json parse failed: %s | preview=%s", e, cleaned[:200])
        return []


def classify_batch(items: list[dict]) -> list[dict]:
    """Annotate each item with classification metadata via the cheapest available LLM.

    Routes via llm_router: Gemini Flash if GEMINI_API_KEY is set, else Anthropic Haiku.
    Falls back automatically if the primary provider fails.
    """
    if not items:
        return []

    user_msg = CLASSIFIER_USER_TEMPLATE.format(items_block=_items_block(items))

    from src.core.llm_router import call_classifier

    try:
        raw, provider = call_classifier(
            system=CLASSIFIER_SYSTEM,
            user_msg=user_msg,
            max_tokens=2000,
        )
    except Exception as e:
        log.error("news classifier call failed (both providers): %s", e)
        return []

    classifications = _safe_parse_json(raw)
    log.info(
        "news classifier returned %d objects for %d items via %s",
        len(classifications), len(items), provider,
    )

    # Merge classification back into items by n
    by_n = {c.get("n"): c for c in classifications if isinstance(c, dict)}
    annotated = []
    for i, item in enumerate(items, start=1):
        c = by_n.get(i, {})
        annotated.append({
            **item,
            "category":      (c.get("category") or "OTHER").upper(),
            "tag":           (c.get("tag") or "").upper(),
            "tickers":       [t for t in (c.get("tickers") or []) if isinstance(t, str)][:5],
            "impact":        (c.get("impact") or "").strip(),
            "extraordinary": bool(c.get("extraordinary")),
            "one_line":      (c.get("one_line") or item["title"]).strip(),
        })
    return annotated


# --- Filtering --------------------------------------------------------------

def is_worth_sending(item: dict) -> bool:
    """Decide if a classified item earns a spot in the brief."""
    cat = item["category"]
    if cat == "OTHER":
        return False
    if cat == "EARNINGS" and item["tag"] == "INLINE" and not item["extraordinary"]:
        return False
    if cat == "STOCK_SPECIFIC" and not item["extraordinary"] and not item["impact"]:
        return False
    return True


# --- Telegram formatting + delivery ----------------------------------------

SECTION_ORDER = [
    ("EXTRAORDINARY",    "⚡ <b>Extraordinary</b>"),
    ("EARNINGS",         "🔔 <b>Earnings</b>"),
    ("MACRO",            "🌍 <b>Macro</b>"),
    ("CORPORATE_ACTION", "🏢 <b>Corporate Actions</b>"),
    ("STOCK_SPECIFIC",   "📌 <b>Stock-Specific</b>"),
]


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _bucket_for(item: dict) -> str:
    """Items flagged extraordinary surface in the dedicated section."""
    if item["extraordinary"]:
        return "EXTRAORDINARY"
    return item["category"]


def format_brief(items: list[dict]) -> str:
    now = datetime.now(timezone.utc).astimezone()
    header = f"📊 <b>Market Brief</b> · {now.strftime('%d %b, %I:%M %p')}"

    buckets: dict[str, list[dict]] = {}
    for item in items:
        buckets.setdefault(_bucket_for(item), []).append(item)

    parts = [header, ""]
    for key, label in SECTION_ORDER:
        batch = buckets.get(key, [])
        if not batch:
            continue
        parts.append(label)
        for item in batch:
            tag = f"[{item['tag']}] " if item["tag"] else ""
            line = f"{tag}{_esc(item['one_line'])}"
            parts.append(f"• {line}")
            if item["tickers"]:
                parts.append(f"  <i>{', '.join(item['tickers'])}</i>")
            if item["impact"]:
                parts.append(f"  ↳ {_esc(item['impact'])}")
            parts.append(f"  <a href=\"{item['url']}\">{_esc(item['source'])}</a>")
            parts.append("")
        parts.append("")
    return "\n".join(parts).rstrip()


def _news_destination_chat_ids() -> list[int]:
    """Read registered destinations from DB (set via /news_here in Telegram)."""
    with get_conn() as conn:
        rows = conn.execute("SELECT chat_id FROM news_destinations").fetchall()
        return [int(r["chat_id"]) for r in rows]


def _owner_chat_id() -> int | None:
    """Owner's DM chat_id — used only for onboarding nudges, not for news."""
    raw = settings.telegram_allowed_user_ids or ""
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit():
            return int(tok)
    return None


def _send_raw(chat_id: int, html_message: str) -> bool:
    """Low-level send to a single chat; chunks long messages."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    ok = True
    for chunk in _chunk(html_message, 3800):
        try:
            r = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if not r.ok:
                log.error("telegram send to %s failed: %s %s", chat_id, r.status_code, r.text[:300])
                ok = False
        except requests.RequestException as e:
            log.error("telegram send to %s raised: %s", chat_id, e)
            ok = False
        time.sleep(0.3)
    return ok


def send_to_telegram(html_message: str, override_chat_id: int | None = None) -> bool:
    """Send the brief.

    If override_chat_id is given, post ONLY there (used for on-demand /news
    commands — the brief goes to whichever chat invoked the command).
    Otherwise post to all registered destinations from /news_here.
    """
    if not settings.telegram_bot_token:
        log.error("TELEGRAM_BOT_TOKEN not set — refusing to send")
        return False

    if override_chat_id is not None:
        return _send_raw(override_chat_id, html_message)

    destinations = _news_destination_chat_ids()
    if not destinations:
        owner = _owner_chat_id()
        if owner:
            log.warning("no news destinations configured — sending onboarding nudge to owner DM")
            _send_raw(
                owner,
                "⚠️ <b>No news destination set.</b>\n\n"
                "Run <code>/news_here</code> in the chat where you want news to land.",
            )
        return False

    success = True
    for chat_id in destinations:
        if not _send_raw(chat_id, html_message):
            success = False
    return success
    # (CL-PROV-02) removed unreachable dead block after the return above; it referenced an
    # undefined `chat_ids` and a duplicate chunk-send already handled by _send_raw/_chunk.


def _chunk(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    out, buf = [], []
    cur_len = 0
    for line in text.split("\n"):
        if cur_len + len(line) + 1 > limit:
            out.append("\n".join(buf))
            buf, cur_len = [], 0
        buf.append(line)
        cur_len += len(line) + 1
    if buf:
        out.append("\n".join(buf))
    return out


# --- Watchlist auto-trigger -------------------------------------------------

def _watchlist_symbols() -> set[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT symbol FROM watchlist").fetchall()
        return {(r["symbol"] or "").upper() for r in rows}


def _patearn_destination_chat_ids() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT chat_id FROM patearn_destinations").fetchall()
        return [int(r["chat_id"]) for r in rows]


def _earnings_already_triggered(symbol: str, news_url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM earnings_triggers WHERE symbol = ? AND news_url = ?",
            (symbol, news_url),
        ).fetchone()
        return row is not None


def _mark_earnings_triggered(symbol: str, news_url: str, news_title: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO earnings_triggers (symbol, news_url, news_title) VALUES (?, ?, ?)",
            (symbol, news_url, news_title),
        )


def _candidate_already_screened(news_url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM screen_candidates WHERE news_url = ?", (news_url,)
        ).fetchone()
        return row is not None


def _store_candidate(
    *,
    symbol: str,
    verdict: str,
    rationale: str,
    signals: list[str],
    news_url: str,
    news_title: str,
    news_source: str,
) -> None:
    import json as _json
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO screen_candidates
               (symbol, verdict, rationale, signals_json, news_url, news_title, news_source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (symbol, verdict, rationale, _json.dumps(signals), news_url, news_title, news_source),
        )


def _stage1_screen_all_earnings(items: list[dict]) -> None:
    """Stage 1 — RULE-BASED scoring (no LLM) on every EARNINGS news item.

    For each earnings news headline, extract the ticker, fetch Screener.in
    fundamentals (cached 7 days), apply patearn 14-pattern Python scoring,
    and store the result in screen_candidates if tier is T1 (PASS) or T2 (WATCH).

    No Haiku, no Sonnet. The classifier-derived `tickers` field from the news
    item gives us which symbol to score. If the news has no extractable ticker,
    item is skipped.
    """
    from src.automation import scoring

    earnings_items = [it for it in items if it.get("category") == "EARNINGS"]
    if not earnings_items:
        return

    log.info("stage1 (rule-based): scoring %d earnings items", len(earnings_items))
    for item in earnings_items:
        if _candidate_already_screened(item["url"]):
            continue

        tickers = item.get("tickers") or []
        if not tickers:
            log.info("stage1: no ticker extracted for %s — skipping", item.get("title", "")[:80])
            continue

        for ticker in tickers[:2]:  # cap at 2 symbols per news item
            ticker = ticker.upper().strip()
            if not ticker:
                continue
            try:
                score = scoring.score_symbol(ticker)
            except Exception as e:
                log.error("stage1 scoring failed for %s: %s", ticker, e)
                continue

            if "error" in score:
                log.info("stage1: could not score %s — %s", ticker, score.get("error"))
                continue

            tier = score.get("tier", "T4")
            ns_base = score.get("ns_base", 0)
            verdict = None
            if tier in ("T1",):
                verdict = "PASS"
            elif tier in ("T2",):
                verdict = "WATCH"
            elif score.get("hard_disqualified"):
                log.info("stage1: %s DISQUALIFIED — %s", ticker,
                         ", ".join(score.get("disqualifier_reasons", [])))
                continue
            else:
                log.info("stage1: %s tier=%s NS=%.1f%% — below threshold", ticker, tier, ns_base)
                continue

            rationale = (
                f"Tier {tier} · NS {ns_base:.1f}% · PAC {score.get('pac', 0)}/14 · "
                f"QG {'PASS' if score.get('qg_pass') else 'FAIL'}"
            )
            signals = []
            if score.get("qg_pass"):
                signals.append("quality_gate_pass")
            if score.get("ns_base", 0) > 70:
                signals.append("high_ns")
            if ns_base > 80:
                signals.append("strong_setup")

            _store_candidate(
                symbol=ticker,
                verdict=verdict,
                rationale=rationale,
                signals=signals,
                news_url=item["url"],
                news_title=item.get("title", ""),
                news_source=item.get("source", ""),
            )
            log.info("stage1 %s: %s (%s)", verdict, ticker, rationale)


def _persist_news_tags(annotated: list[dict]) -> None:
    """Tag freshly-sent headlines with the stock(s) they concern (UI Architecture
    v2 §7) so the dossier Timeline / Markets Wire have a symbol→news link. Two
    complementary sources, written here AFTER the headlines land in sent_news:
      • the rule-based gazetteer (news_tagging.match_title) — catches a clearly
        named listed company even when the classifier filed the item as OTHER
        (the classifier returns no tickers for OTHER, so without this the dossier
        Timeline would permanently miss those headlines);
      • the classifier's own `tickers` (computed for free) — recovers brand!=legal
        name cases the gazetteer misses (Nykaa, RIL, Jio…).
    Must run only for headlines that were actually mark_sent (else the tags are
    orphans with no sent_news row). Best-effort: never breaks the brief."""
    try:
        from src.automation.news_tagging import ensure_schema, build_index_from_conn, match_title
        items = [it for it in annotated if it.get("url")]
        if not items:
            return
        named = classifier = 0
        with get_conn() as conn:
            ensure_schema(conn)
            index = build_index_from_conn(conn)
            for it in items:
                url = it["url"]
                for sym, (method, conf, _span) in match_title(it.get("title") or "", index).items():
                    cur = conn.execute(
                        "INSERT OR IGNORE INTO news_symbol_tags (news_url, symbol, method, confidence) "
                        "VALUES (?, ?, ?, ?)", (url, sym, method, conf))
                    named += cur.rowcount or 0
                for t in (it.get("tickers") or []):
                    t = (t or "").strip().upper()
                    if not t:
                        continue
                    cur = conn.execute(
                        "INSERT OR IGNORE INTO news_symbol_tags (news_url, symbol, method, confidence) "
                        "VALUES (?, ?, 'classifier', 0.95)", (url, t))
                    classifier += cur.rowcount or 0
        log.info("news symbol-tags written: %d rule-based + %d classifier across %d headlines",
                 named, classifier, len(items))
    except Exception as e:
        log.warning("news symbol-tagging skipped: %s", e)


# --- Entry point ------------------------------------------------------------

def run_and_send(override_chat_id: int | None = None, *, ignore_already_sent: bool = False) -> tuple[bool, str]:
    """Execute one news fetch + classify + send cycle.

    Args:
        override_chat_id: If provided, post only to this chat (used for on-demand
            /news command). If None, post to all registered destinations.
        ignore_already_sent: If True, include items even if previously sent.
            Useful for on-demand /news — user wants the latest brief regardless
            of whether they've seen those items before.

    Returns:
        (success, human_readable_status)
    """
    log.info("news_feed run starting (override_chat_id=%s, ignore_sent=%s)",
             override_chat_id, ignore_already_sent)

    raw_items: list[dict] = []
    for source, feed_url in FEEDS.items():
        for item in fetch_recent(source, feed_url):
            if not ignore_already_sent and is_already_sent(item["url"]):
                continue
            raw_items.append(item)
    raw_items.sort(key=lambda x: x["published_ts"] or 0, reverse=True)
    raw_items = raw_items[:MAX_ITEMS_FETCHED]

    log.info("fetched %d items across %d feeds", len(raw_items), len(FEEDS))
    if not raw_items:
        return True, "No fresh headlines in the last 12 hours."

    annotated = classify_batch(raw_items)
    if not annotated:
        return False, "Classifier failed — try again in a minute."

    # Stage 1 patearn pre-screen on EVERY earnings item, regardless of watchlist.
    # PASS/WATCH candidates get stored in screen_candidates for the twice-daily
    # digest. No Sonnet calls — pure Haiku numeric screening.
    try:
        _stage1_screen_all_earnings(annotated)
    except Exception as e:
        log.error("stage1 screen pipeline raised: %s", e)

    signal = [it for it in annotated if is_worth_sending(it)]
    log.info("%d items kept after filter (from %d)", len(signal), len(annotated))

    if not signal:
        # Still mark them so we don't re-classify these same items on the next run
        for item in raw_items:
            mark_sent(item)
        _persist_news_tags(annotated)   # symbol-tag AFTER mark_sent (no orphan tags)
        return True, "No signal-worthy items right now. (Filtered out routine commentary.)"

    message = format_brief(signal)
    if send_to_telegram(message, override_chat_id=override_chat_id):
        for item in raw_items:
            mark_sent(item)
        _persist_news_tags(annotated)   # symbol-tag AFTER mark_sent (no orphan tags)
        return True, f"Sent {len(signal)} signal items."
    else:
        return False, "Send to Telegram failed — check logs."


def main() -> None:
    """CLI entry: python -m src.automation.news_feed"""
    ok, status = run_and_send()
    log.info("done — ok=%s status=%s", ok, status)


if __name__ == "__main__":
    main()
