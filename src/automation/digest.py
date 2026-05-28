"""Twice-daily candidate digest to patearn Telegram destinations.

Reads pending screen_candidates (digest_sent_at IS NULL), formats a structured
Telegram message grouped by verdict, posts to patearn_destinations, marks
items as digest_sent.

Run standalone: python -m src.automation.digest

Designed to be invoked by a systemd timer at 8:30 AM and 4:30 PM IST on weekdays.
"""

import logging
import time
from datetime import datetime, timezone

import requests

from src.core.db import get_conn
from src.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("hermes.digest")

# Public URL where the candidates page lives. Updated by setup script in future
# if we ever swap to https + domain; for now plain VPS IP + port.
PUBLIC_BASE_URL = f"http://{settings.host if settings.host != '0.0.0.0' else '187.127.173.149'}:{settings.port}"


def _pending_candidates() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, symbol, verdict, rationale, signals_json, news_url,
                      news_title, news_source, screened_at
               FROM screen_candidates
               WHERE digest_sent_at IS NULL
               ORDER BY (verdict='PASS') DESC, screened_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def _mark_digest_sent(ids: list[int]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE screen_candidates SET digest_sent_at = datetime('now') WHERE id IN ({placeholders})",
            ids,
        )


def _patearn_destinations() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT chat_id FROM patearn_destinations").fetchall()
        return [int(r["chat_id"]) for r in rows]


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_digest(candidates: list[dict]) -> str:
    by_verdict: dict[str, list[dict]] = {"PASS": [], "WATCH": []}
    for c in candidates:
        by_verdict.setdefault(c["verdict"], []).append(c)

    now = datetime.now(timezone.utc).astimezone()
    p_count, w_count = len(by_verdict["PASS"]), len(by_verdict["WATCH"])

    lines = [
        f"📊 <b>patearn Screen Digest — {now.strftime('%d %b, %I:%M %p')}</b>",
        "",
        f"<b>{p_count} PASS · {w_count} WATCH</b> since last digest.",
        "",
    ]

    if by_verdict["PASS"]:
        lines.append("✅ <b>PASS — strongest signals</b>")
        for c in by_verdict["PASS"][:15]:
            lines.append(f"• <code>{_esc(c['symbol'])}</code> — {_esc(c['rationale'])[:120]}")
            lines.append(f"  <a href=\"{c['news_url']}\">{_esc(c['news_source'])}</a>")
        lines.append("")

    if by_verdict["WATCH"]:
        lines.append("👀 <b>WATCH — mild signal, monitor</b>")
        for c in by_verdict["WATCH"][:15]:
            lines.append(f"• <code>{_esc(c['symbol'])}</code> — {_esc(c['rationale'])[:120]}")
            lines.append(f"  <a href=\"{c['news_url']}\">{_esc(c['news_source'])}</a>")
        lines.append("")

    lines.append(f"<b>Full table:</b> {PUBLIC_BASE_URL}/candidates")
    lines.append("")
    lines.append(
        "<i>Deep dive: copy a row → paste into claude.ai → ask for full patearn "
        "Mode 1 analysis (Sonnet via your subscription, no API cost).</i>"
    )
    return "\n".join(lines)


def _chunk(text: str, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text]
    out, buf, cur = [], [], 0
    for line in text.split("\n"):
        block = line + "\n"
        if cur + len(block) > limit and buf:
            out.append("".join(buf).rstrip())
            buf, cur = [], 0
        buf.append(block)
        cur += len(block)
    if buf:
        out.append("".join(buf).rstrip())
    return out


def _send(chat_id: int, html_message: str) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    ok = True
    for chunk in _chunk(html_message):
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
                log.error("telegram send to %s failed: %s %s", chat_id, r.status_code, r.text[:200])
                ok = False
        except requests.RequestException as e:
            log.error("telegram send to %s raised: %s", chat_id, e)
            ok = False
        time.sleep(0.3)
    return ok


def main() -> None:
    if not settings.telegram_bot_token:
        log.error("TELEGRAM_BOT_TOKEN not set — refusing to send digest")
        return

    candidates = _pending_candidates()
    if not candidates:
        log.info("no pending candidates — exiting cleanly")
        return

    destinations = _patearn_destinations()
    if not destinations:
        log.warning("no patearn destinations configured — run /patearn_here in your group")
        return

    message = format_digest(candidates)

    success = True
    for chat_id in destinations:
        if not _send(chat_id, message):
            success = False

    if success:
        _mark_digest_sent([c["id"] for c in candidates])
        log.info("digest sent and marked: %d candidates", len(candidates))
    else:
        log.error("digest send failed — leaving candidates unmarked for retry")


if __name__ == "__main__":
    main()
