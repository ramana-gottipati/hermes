"""Indian market news feed → Telegram push.

Run as a one-shot script on a schedule (e.g. systemd timer). Each invocation:
  1. Pulls recent headlines from a set of Indian market RSS feeds
  2. Filters out anything we've already sent (via sent_news table)
  3. Posts a single batched Telegram message with the new items
  4. Records what was sent so we don't repeat

Cost: ₹0 — no LLM calls. Pure HTTP fetches + SQLite + Telegram bot send.

Usage (standalone):
    python -m src.automation.news_feed

Designed to be run on systemd timer at 8:30 AM and 4:30 PM IST on weekdays.
"""

import logging
import time
from datetime import datetime, timezone

import feedparser
import requests

from src.core.db import get_conn
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

# Only ship items published within this window
MAX_ITEM_AGE_HOURS = 12

# Cap items per run so a single push doesn't spam your phone
MAX_ITEMS_PER_RUN = 12

# Per-source cap (so one chatty feed doesn't crowd out the others)
MAX_ITEMS_PER_SOURCE = 4


# --- RSS handling -----------------------------------------------------------

def _entry_timestamp(entry) -> float | None:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            return time.mktime(parsed)
    return None


def fetch_recent(source: str, feed_url: str) -> list[dict]:
    """Return recent items from a single feed, newest first, age-filtered."""
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        log.warning("failed to parse %s: %s", source, e)
        return []

    if feed.bozo and not feed.entries:
        log.warning("feed %s returned no entries (bozo=%s)", source, feed.bozo_exception)
        return []

    cutoff = time.time() - MAX_ITEM_AGE_HOURS * 3600
    items: list[dict] = []

    for entry in feed.entries[:25]:
        ts = _entry_timestamp(entry)
        # Keep items with no timestamp (some feeds omit it) — better to include than drop
        if ts is not None and ts < cutoff:
            continue
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue
        items.append({
            "source": source,
            "title": title,
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


# --- Telegram delivery ------------------------------------------------------

def _allowed_chat_ids() -> list[int]:
    raw = settings.telegram_allowed_user_ids or ""
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def send_to_telegram(html_message: str) -> bool:
    if not settings.telegram_bot_token:
        log.error("TELEGRAM_BOT_TOKEN not set — refusing to send")
        return False

    chat_ids = _allowed_chat_ids()
    if not chat_ids:
        log.error("TELEGRAM_ALLOWED_USER_IDS empty — no one to send to")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    success = True
    for chat_id in chat_ids:
        try:
            r = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": html_message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if not r.ok:
                log.error("telegram send to %s failed: %s %s", chat_id, r.status_code, r.text[:200])
                success = False
        except requests.RequestException as e:
            log.error("telegram send to %s raised: %s", chat_id, e)
            success = False
    return success


def format_digest(items: list[dict]) -> str:
    """Build a single HTML message containing all new items, grouped by source."""
    now_ist = datetime.now(timezone.utc).astimezone()
    header = f"📰 <b>Market News — {now_ist.strftime('%d %b, %I:%M %p')}</b>"

    by_source: dict[str, list[dict]] = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)

    lines = [header, ""]
    for source, batch in by_source.items():
        lines.append(f"<b>{source}</b>")
        for item in batch:
            # Title text is escaped; URL goes in href
            safe_title = (
                item["title"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            lines.append(f"• <a href=\"{item['url']}\">{safe_title}</a>")
        lines.append("")
    return "\n".join(lines).rstrip()


# --- Entry point ------------------------------------------------------------

def main() -> None:
    log.info("news_feed run starting")

    new_items: list[dict] = []
    for source, feed_url in FEEDS.items():
        for item in fetch_recent(source, feed_url):
            if is_already_sent(item["url"]):
                continue
            new_items.append(item)

    log.info("fetched %d new items across %d feeds", len(new_items), len(FEEDS))

    if not new_items:
        log.info("nothing new to send — exiting cleanly")
        return

    # Sort newest first across all sources, cap to MAX_ITEMS_PER_RUN
    new_items.sort(key=lambda x: x["published_ts"] or 0, reverse=True)
    new_items = new_items[:MAX_ITEMS_PER_RUN]

    message = format_digest(new_items)

    if send_to_telegram(message):
        for item in new_items:
            mark_sent(item)
        log.info("sent and recorded %d items", len(new_items))
    else:
        log.error("send failed — items NOT marked sent so they retry next run")


if __name__ == "__main__":
    main()
