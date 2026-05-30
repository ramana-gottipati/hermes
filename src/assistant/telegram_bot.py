"""Telegram front-end for Hermes.

Polls Telegram for incoming messages, routes them through chat.handle() with
the same SQLite-backed memory the HTTP /chat endpoint uses, replies back in
Telegram. Each Telegram user gets their own ongoing conversation.

Run standalone:
    python -m src.assistant.telegram_bot

Authorization model:
- TELEGRAM_ALLOWED_USER_IDS in .env is a comma-separated list of integer user IDs
- An empty list = nobody is authorized (bot replies with the sender's user ID
  so the owner can paste it into .env)
- Anyone not in the list gets a polite rejection — and no Anthropic credits are spent
"""

import asyncio
import logging

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.assistant import chat, conversations
from src.core.db import get_conn
from src.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("hermes.telegram")


def _allowed_user_ids() -> set[int]:
    raw = settings.telegram_allowed_user_ids or ""
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


def _is_authorized(user_id: int) -> bool:
    return user_id in _allowed_user_ids()


def _unauthorized_message(user_id: int) -> str:
    return (
        "Hi — you're not authorized to chat with this bot.\n\n"
        f"Your Telegram user ID is:\n<code>{user_id}</code>\n\n"
        "If you're the bot's owner, add this ID to TELEGRAM_ALLOWED_USER_IDS in "
        ".env (comma-separated for multiple) and restart Hermes."
    )


# --- Handlers ---------------------------------------------------------------

async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command (sent automatically when a user opens the bot)."""
    user_id = update.effective_user.id
    if _is_authorized(user_id):
        await update.message.reply_text(
            "Hi — I'm Hermes.\n\n"
            "<b>Three ways to drive me:</b>\n"
            "  1. <b>/menu</b> — tap through a button tree if you don't want to remember commands\n"
            "  2. <b>Plain English</b> — \"what's pixtrans?\" / \"any ATH today?\" / \"discount entries?\"\n"
            "  3. <b>Slash commands</b> — /pt14 TICKER · /dvpt TICKER · /scan · /triggers [ss|near]\n\n"
            "<i>Or just chat — I'll remember the thread (/reset to start over).</i>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(_unauthorized_message(user_id), parse_mode="HTML")


async def on_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show which LLM provider is being used for classifier tasks (intent + news)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    from src.core.llm_router import active_classifier_provider
    provider = active_classifier_provider()
    if provider == "gemini":
        msg = (
            f"<b>Classifier provider:</b> Gemini Flash\n"
            f"  Model: <code>{settings.gemini_classifier_model}</code>\n"
            f"  Cost: ~$0.075 in / $0.30 out per million tokens (~13× cheaper than Haiku)\n\n"
            f"<b>Chat + /analyze:</b> Anthropic ({settings.fast_model} / {settings.default_model})"
        )
    else:
        msg = (
            f"<b>Classifier provider:</b> Anthropic Haiku ({settings.fast_model})\n"
            f"  Cost: $1.00 in / $5.00 out per million tokens\n\n"
            f"To switch to Gemini Flash (~13× cheaper for classifiers):\n"
            f"1. Get free key at https://aistudio.google.com/apikey\n"
            f"2. Add to <code>/opt/hermes/.env</code>: <code>GEMINI_API_KEY=...</code>\n"
            f"3. Restart bot: <code>systemctl restart hermes-telegram</code>\n\n"
            f"<b>Chat + /analyze:</b> Anthropic (unchanged)"
        )
    await update.message.reply_text(msg, parse_mode="HTML")


async def on_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the sender's Telegram user ID — useful for onboarding."""
    user_id = update.effective_user.id
    authorized = "yes" if _is_authorized(user_id) else "no"
    await update.message.reply_text(
        f"Telegram user ID: <code>{user_id}</code>\nAuthorized: {authorized}",
        parse_mode="HTML",
    )


async def on_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a fresh conversation for this user."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        await update.message.reply_text(_unauthorized_message(user_id), parse_mode="HTML")
        return
    # Create a new conversation; future messages will pick it up as the most recent.
    new_id = conversations.create_conversation(
        title=f"telegram:{user_id} (reset)", telegram_user_id=user_id
    )
    await update.message.reply_text(f"Conversation reset. New thread id: {new_id}")


async def on_news_here(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register the current chat (DM or group) as a destination for news briefs."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return  # silently ignore unauthorized — no leak that the command exists

    chat = update.effective_chat
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO news_destinations (chat_id, chat_title, chat_type, added_by)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 chat_title = excluded.chat_title,
                 chat_type  = excluded.chat_type,
                 added_at   = datetime('now'),
                 added_by   = excluded.added_by""",
            (chat.id, chat.title or chat.full_name or "(unnamed)", chat.type, user_id),
        )

    log.info("news destination registered: chat_id=%s title=%s type=%s", chat.id, chat.title, chat.type)
    await update.message.reply_text(
        f"✓ This chat is now a news destination.\n"
        f"Type: <b>{chat.type}</b>\n"
        f"Title: <b>{chat.title or chat.full_name or '(unnamed)'}</b>\n"
        f"chat_id: <code>{chat.id}</code>\n\n"
        f"Market briefs will be posted here. Use /news_stop to remove.",
        parse_mode="HTML",
    )


async def on_news_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the current chat from news destinations."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    chat = update.effective_chat
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM news_destinations WHERE chat_id = ?", (chat.id,))
        removed = cur.rowcount > 0

    if removed:
        await update.message.reply_text("✓ News briefs will no longer be posted here.")
    else:
        await update.message.reply_text("This chat was not registered as a news destination.")


async def on_news_where(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all currently registered news destinations."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT chat_id, chat_title, chat_type, added_at FROM news_destinations ORDER BY added_at DESC"
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "No news destinations configured. Run /news_here in the chat where you want briefs to land."
        )
        return

    lines = ["<b>News destinations:</b>", ""]
    for r in rows:
        lines.append(f"• {r['chat_title']} (<code>{r['chat_id']}</code>, {r['chat_type']})")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def on_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On-demand news fetch — posts a fresh brief to the chat where /news was sent."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    chat_id = update.effective_chat.id
    # Acknowledge so the user knows we received the command
    await update.message.reply_text("📡 Fetching market news…")

    # Import lazily so the bot can boot even if news_feed has issues
    from src.automation import news_feed

    # news_feed.run_and_send is synchronous; run in a thread to avoid blocking
    # the asyncio event loop while we hit RSS endpoints + Claude.
    loop = asyncio.get_event_loop()
    ok, status = await loop.run_in_executor(
        None,
        lambda: news_feed.run_and_send(override_chat_id=chat_id, ignore_already_sent=True),
    )

    if not ok:
        await update.message.reply_text(f"⚠️ {status}")
    elif "No " in status or "Filtered" in status:
        # No signal items — let the user know rather than leaving them wondering
        await update.message.reply_text(f"ℹ️ {status}")


async def on_dvpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Delivery Value Per Trade (DVPT) signal — institutional flow read.

    Usage: /dvpt TICKER [days]
    Example: /dvpt PIXTRANS
             /dvpt PIXTRANS 30   (last 30 trading days)
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/dvpt TICKER [days]</code>\n"
            "Example: <code>/dvpt PIXTRANS</code> or <code>/dvpt PIXTRANS 30</code>",
            parse_mode="HTML",
        )
        return

    ticker = context.args[0].upper().strip()
    try:
        days = int(context.args[1]) if len(context.args) > 1 else 15
    except (ValueError, IndexError):
        days = 15
    days = max(5, min(days, 60))

    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(None, lambda: _fetch_flow_rows(ticker, days))

    if not rows:
        await update.message.reply_text(
            f"No bhav copy / signal data for <b>{ticker}</b>. "
            f"Check spelling, or this stock may not be in the EQ series.",
            parse_mode="HTML",
        )
        return

    msg = _format_flow_message(ticker, rows)
    await update.message.reply_text(msg, parse_mode="HTML")


def _fetch_flow_rows(ticker: str, days: int) -> list[dict]:
    """Pull the latest N days of DVPT + price + delivery for one symbol."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.trade_date,
                      b.close,
                      b.deliv_per,
                      b.deliv_qty,
                      s.delivery_value_per_trade AS dvpt,
                      s.power_dvpt_1m,
                      s.power_dvpt_3m,
                      s.ratio_today_vs_power_1m AS r1m,
                      s.ratio_today_vs_power_3m AS r3m,
                      s.trigger_rank, s.r_score, s.p_score, s.is_ath_dvpt,
                      s.next_p_above, s.gap_to_next_p_pct,
                      s.avg_close_r1m, s.avg_close_r2m, s.avg_close_r3m,
                      s.avg_close_r6m, s.avg_close_r12m,
                      s.avg_close_p1m, s.avg_close_p2m, s.avg_close_p3m,
                      s.avg_close_p6m, s.avg_close_p12m
               FROM stock_signals s
               JOIN bhavcopy_rows b USING (symbol, trade_date)
               WHERE s.symbol = ? AND b.series = 'EQ'
               ORDER BY s.trade_date DESC
               LIMIT ?""",
            (ticker, days),
        ).fetchall()
        return [dict(r) for r in rows]


def _fmt_int(v) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}"


def _fmt_money(v, decimals: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v:,.{decimals}f}"


def _fmt_ratio(v) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}"


def _format_flow_message(ticker: str, rows: list[dict]) -> str:
    latest = rows[0]
    r1m = latest.get("r1m")

    if r1m is None:
        verdict = "<i>Insufficient history for 1-month power baseline.</i>"
    elif r1m > 1.50:
        verdict = f"⚡ <b>Exceptional</b> — today's DVPT is {r1m:.2f}× the recent peak institutional baseline."
    elif r1m > 1.00:
        verdict = f"🟢 <b>Institutional intensity present</b> — today at {r1m:.2f}× recent peak."
    elif r1m > 0.70:
        verdict = f"🟡 <b>Approaching institutional zone</b> — {r1m:.2f}× recent peak."
    elif r1m > 0.30:
        verdict = f"⚪ <b>Normal day</b> — {r1m:.2f}× recent peak."
    else:
        verdict = f"🔵 <b>Quiet</b> — {r1m:.2f}× recent peak."

    lines = [
        f"<b>📊 {ticker} — Delivery Flow Signal</b>",
        verdict,
        "",
        f"<b>Latest ({latest['trade_date']}):</b>",
        f"  Close ₹{_fmt_money(latest['close'])} · "
        f"Deliv {_fmt_money(latest['deliv_per'])}% ({_fmt_int(latest['deliv_qty'])} sh)",
        f"  <b>DVPT today: ₹{_fmt_int(latest['dvpt'])} per trade</b>",
        f"  Power 1m baseline: ₹{_fmt_int(latest['power_dvpt_1m'])}",
        f"  Power 3m baseline: ₹{_fmt_int(latest['power_dvpt_3m'])}",
        f"  Ratio vs 1m: <b>{_fmt_ratio(latest['r1m'])}</b> · "
        f"Ratio vs 3m: <b>{_fmt_ratio(latest['r3m'])}</b>",
        "",
        f"<b>Last {len(rows)} days:</b>",
        "<pre>",
        f"{'Date':<11} {'Close':>8} {'Deliv%':>7} {'DVPT':>10} {'r1m':>6} {'r3m':>6}",
    ]
    for r in rows:
        lines.append(
            f"{r['trade_date']:<11} "
            f"{_fmt_money(r['close']):>8} "
            f"{_fmt_money(r['deliv_per']):>7} "
            f"{_fmt_int(r['dvpt']):>10} "
            f"{_fmt_ratio(r['r1m']):>6} "
            f"{_fmt_ratio(r['r3m']):>6}"
        )
    lines.append("</pre>")

    # --- D31 Institutional price zones -----------------------------------
    today_close = latest.get("close")
    zone_lines = _format_price_zones_section(today_close, latest)
    if zone_lines:
        lines.append("")
        lines.extend(zone_lines)

    lines.append("")
    lines.append(
        "<i>DVPT = (delivery quantity × close) ÷ number of trades. "
        "P-tier = avg of top-N DVPT days within calendar window "
        "(top 4/30d, 7/60d, 12/90d, 20/180d, 30/360d). "
        "R-tier = simple avg DVPT over same calendar windows. "
        "Value-based — naturally invariant to splits/bonuses.</i>"
    )
    return "\n".join(lines)


# Mapping from logical label → column key in the stock_signals row dict.
_ZONE_LABELS = (
    ("R1M",  "avg_close_r1m"),
    ("R2M",  "avg_close_r2m"),
    ("R3M",  "avg_close_r3m"),
    ("R6M",  "avg_close_r6m"),
    ("R12M", "avg_close_r12m"),
    ("P1M",  "avg_close_p1m"),
    ("P2M",  "avg_close_p2m"),
    ("P3M",  "avg_close_p3m"),
    ("P6M",  "avg_close_p6m"),
    ("P12M", "avg_close_p12m"),
)


def _format_price_zones_section(today_close, latest: dict) -> list[str]:
    """Render the D31 institutional price-zone block: for each of the 10
    baselines, show avg close on baseline days, today's close, gap %, marker.

    Returns empty list if today_close is missing or every zone column is NULL
    (e.g. backfill hasn't run yet on the VPS).
    """
    if today_close is None or today_close <= 0:
        return []
    if not any(latest.get(col) for _, col in _ZONE_LABELS):
        return []  # backfill not yet run

    def marker(gap_pct):
        if gap_pct is None:
            return "  "
        if gap_pct < -3.0:
            return "🟢"
        if gap_pct > 3.0:
            return "🔴"
        return "🟡"

    def row(label, zone_price):
        if zone_price is None or zone_price <= 0:
            return f"{label:<5} {'—':>10} {'—':>8}    "
        gap_pct = (today_close - zone_price) / zone_price * 100.0
        return (
            f"{label:<5} ₹{zone_price:>8,.1f} "
            f"{gap_pct:>+7.1f}%  {marker(gap_pct)}"
        )

    out = [
        "<b>📍 Institutional price zones (today's close vs avg close on baseline days):</b>",
        "<pre>",
        f"{'':<5} {'Avg close':>10} {'Δ today':>8}",
        "<b>P-tier — top-N DVPT days (where institutions actually transacted):</b>",
    ]
    for label, col in _ZONE_LABELS[5:]:  # P-tier first (more actionable)
        out.append(row(label, latest.get(col)))
    out.append("<b>R-tier — flat avg (baseline trading zone):</b>")
    for label, col in _ZONE_LABELS[:5]:
        out.append(row(label, latest.get(col)))
    out.append("</pre>")
    out.append(
        f"<i>Today's close: ₹{today_close:,.2f}. "
        "🟢 below −3% = discount entry · 🟡 ±3% = at-cost · 🔴 above +3% = late entry.</i>"
    )
    return out


async def on_pt14(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rule-based patearn score — FREE, no LLM. Fetches Screener data + applies
    the 14-pattern rules in Python. Use this BEFORE /analyze (which costs API)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/pt14 TICKER</code>\nExample: <code>/pt14 RELIANCE</code>",
            parse_mode="HTML",
        )
        return

    ticker = context.args[0].upper().strip()
    force_refresh = "fresh" in [a.lower() for a in context.args[1:]]

    await update.message.reply_text(
        f"🔢 Scoring <b>{ticker}</b> from Screener data (no LLM, ₹0)…",
        parse_mode="HTML",
    )

    from src.automation import scoring, screener as _screener

    loop = asyncio.get_event_loop()
    try:
        score = await loop.run_in_executor(
            None,
            lambda: scoring.score_symbol(ticker, force_refresh=force_refresh),
        )
        # Also fetch fundamentals for the formatter
        fundamentals = await loop.run_in_executor(
            None,
            lambda: _screener.fetch_company(ticker, use_cache=True),
        )
    except Exception as e:
        log.exception("score failed for %s", ticker)
        await update.message.reply_text(f"⚠️ Score failed: {e}")
        return

    msg = scoring.format_score_for_telegram(score, fundamentals=fundamentals)
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)


async def on_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reminder: deep dives belong in claude.ai (subscription) — not via API.

    Replaces the original LLM-based /analyze. Prints the claude.ai workflow
    guide instead of burning API credits to duplicate what the subscription
    already covers.
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    args = context.args or []
    ticker = args[0].upper().strip() if args else "TICKER"

    guide = (
        "💡 <b>Deep analysis belongs in claude.ai</b> — it's free under your $20/mo subscription. "
        "<i>This command no longer calls the API.</i>\n\n"
        f"<b>For {ticker}, here's the right workflow:</b>\n\n"
        f"<b>1.</b> Run <code>/pt14 {ticker}</code> here in Telegram. Copy the output.\n"
        f"<b>2.</b> Run <code>/dvpt {ticker}</code> here in Telegram. Copy the output.\n"
        "<b>3.</b> Open a fresh claude.ai chat. Make sure the <b>patearn skill</b> is loaded.\n"
        "<b>4.</b> Paste both outputs with a prompt like:\n\n"
        f"<i>\"Run patearn Mode 1 analysis on {ticker}. Hermes' rule-based numbers: [paste /pt14 output]. "
        f"Recent delivery-flow signals: [paste /dvpt output]. Read recent concalls, segment data, "
        "write bear case with 3 specific falsifiable conditions, identify tripwires, give verdict "
        "with position-size guidance per the tier matrix.\"</i>\n\n"
        "<b>Why this is better than calling Sonnet via the API:</b>\n"
        "  • Free (already paid via subscription) — saves ~₹10/call\n"
        "  • Better Sonnet quality, larger context window\n"
        "  • You can follow up with questions in the same thread\n"
        "  • Decision <b>D13</b> in your project state — this was the plan all along."
    )

    await update.message.reply_text(guide, parse_mode="HTML")


# --- Watchlist + patearn-destination commands ------------------------------

async def on_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a stock to the watchlist. Triggers auto-analysis when earnings news lands."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/watch SYMBOL [optional note]</code>\nExample: <code>/watch RELIANCE</code>",
            parse_mode="HTML",
        )
        return
    symbol = context.args[0].upper().strip()
    note = " ".join(context.args[1:]).strip() or None
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO watchlist (symbol, note, added_by) VALUES (?, ?, ?)
               ON CONFLICT(symbol) DO UPDATE SET note = excluded.note, added_by = excluded.added_by""",
            (symbol, note, user_id),
        )
    await update.message.reply_text(
        f"✓ Watching <b>{symbol}</b>. Earnings news for this stock will trigger an auto patearn analysis.",
        parse_mode="HTML",
    )


async def on_unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if not context.args:
        await update.message.reply_text("Usage: <code>/unwatch SYMBOL</code>", parse_mode="HTML")
        return
    symbol = context.args[0].upper().strip()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
        ok = cur.rowcount > 0
    await update.message.reply_text(
        f"✓ Removed <b>{symbol}</b> from watchlist." if ok else f"<b>{symbol}</b> was not on the watchlist.",
        parse_mode="HTML",
    )


async def on_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, note, added_at FROM watchlist ORDER BY symbol"
        ).fetchall()
    if not rows:
        await update.message.reply_text(
            "Watchlist is empty. Add stocks with <code>/watch SYMBOL</code>.",
            parse_mode="HTML",
        )
        return
    lines = [f"<b>Watchlist ({len(rows)} stocks):</b>", ""]
    for r in rows:
        line = f"• <code>{r['symbol']}</code>"
        if r["note"]:
            line += f" — {r['note']}"
        lines.append(line)
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def on_patearn_here(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register the current chat as a destination for auto-triggered patearn analyses."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    chat = update.effective_chat
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO patearn_destinations (chat_id, chat_title, chat_type, added_by)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 chat_title = excluded.chat_title,
                 chat_type  = excluded.chat_type,
                 added_at   = datetime('now'),
                 added_by   = excluded.added_by""",
            (chat.id, chat.title or chat.full_name or "(unnamed)", chat.type, user_id),
        )
    log.info("patearn destination registered: chat_id=%s title=%s", chat.id, chat.title)
    await update.message.reply_text(
        f"✓ This chat is now a patearn destination.\n"
        f"Auto-analyses triggered by watchlist earnings will land here.\n\n"
        f"Title: <b>{chat.title or chat.full_name or '(unnamed)'}</b>\n"
        f"chat_id: <code>{chat.id}</code>",
        parse_mode="HTML",
    )


async def on_patearn_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    chat = update.effective_chat
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM patearn_destinations WHERE chat_id = ?", (chat.id,))
        ok = cur.rowcount > 0
    await update.message.reply_text(
        "✓ Auto patearn analyses will no longer post here." if ok
        else "This chat was not registered as a patearn destination."
    )


async def on_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top stocks by institutional flow signal for the most recent trading day.

    Usage:
      /scan          -> top 15
      /scan 25       -> top 25 (cap 30)
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    try:
        n = int(context.args[0]) if context.args else 15
    except (ValueError, IndexError):
        n = 15
    n = max(5, min(n, 30))

    await update.message.reply_text(
        f"🔎 Scanning latest day's institutional flow (top {n})…"
    )

    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(None, lambda: _scan_top_dvpt(n))

    if not rows:
        await update.message.reply_text(
            "No signal data found for the latest trading day. "
            "Run <code>/dvpt &lt;TICKER&gt;</code> on individual stocks instead.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(_format_scan_message(rows), parse_mode="HTML")


# --- Two-tier scan + layered triggers (D28) -------------------------------

# Shared symbol/liquidity filters (D23).
_SCAN_FILTERS_SQL = """
                 AND b.series = 'EQ'
                 AND (b.segment = 'CM' OR b.segment IS NULL)
                 AND b.value > 10000000
                 AND b.close > 20
                 AND s.symbol NOT LIKE '%ETF%'
                 AND s.symbol NOT LIKE '%IETF%'
                 AND s.symbol NOT LIKE '%BEES%'
                 AND s.symbol NOT LIKE '%GOLD%'
                 AND s.symbol NOT LIKE '%SILVER%'
                 AND s.symbol NOT LIKE 'MON%'
                 AND s.symbol NOT LIKE 'NIFTY%'
                 AND s.symbol NOT LIKE 'BANK%ADD'
"""

# Sort by: ATH DESC, p_score DESC, r_score DESC, discount-entry DESC, r1m DESC.
_LAYERED_ORDER_SQL = """
ORDER BY COALESCE(s.is_ath_dvpt, 0) DESC,
         COALESCE(s.p_score, -1) DESC,
         COALESCE(s.r_score, -1) DESC,
         CASE WHEN s.price_vs_hot_avg_pct IS NOT NULL
                AND s.price_vs_hot_avg_pct < -3.0 THEN 0 ELSE 1 END ASC,
         COALESCE(s.ratio_today_vs_power_1m, 0) DESC
"""


def _scan_top_dvpt(n: int) -> list[dict]:
    """Top N EQ stocks for the latest trading day, layered two-tier ranked."""
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT s.symbol,
                       s.trade_date,
                       s.delivery_value_per_trade   AS dvpt,
                       s.ratio_today_vs_power_1m    AS r1m,
                       s.ratio_today_vs_power_3m    AS r3m,
                       s.trigger_rank,
                       s.r_score,
                       s.p_score,
                       s.is_ath_dvpt,
                       s.hot_days_avg_price,
                       s.price_vs_hot_avg_pct,
                       s.next_p_above,
                       s.gap_to_next_p_pct,
                       b.close,
                       b.deliv_per,
                       b.value AS total_value
                FROM stock_signals s
                JOIN bhavcopy_rows b USING (symbol, trade_date)
                WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)
                  AND s.delivery_value_per_trade IS NOT NULL
                  {_SCAN_FILTERS_SQL}
                {_LAYERED_ORDER_SQL}
                LIMIT ?""",
            (n,),
        ).fetchall()
        return [dict(r) for r in rows]


def _entry_marker(pvh) -> str:
    """🟢 discount / 🟡 at-cost / 🔴 above-cost vs recent hot-day avg (D28)."""
    if pvh is None:
        return "  "
    if pvh < -3.0:
        return "🟢"
    if pvh > 3.0:
        return "🔴"
    return "🟡"


def _rank_label(rank, is_ath) -> str:
    base = (rank or "-")
    if is_ath:
        return f"⚡{base}" if base != "-" else "⚡ATH"
    return base


def _format_row(r: dict) -> str:
    sym = (r["symbol"] or "")[:10]
    rank = _rank_label(r.get("trigger_rank"), r.get("is_ath_dvpt"))
    rp = f"{r.get('r_score') or 0}/{r.get('p_score') or 0}"
    close = f"{r['close']:,.0f}" if r["close"] else "—"
    pvh = r.get("price_vs_hot_avg_pct")
    pvh_s = f"{pvh:+.1f}" if pvh is not None else "—"
    en = _entry_marker(pvh)
    near = r.get("next_p_above") or ""
    gap = r.get("gap_to_next_p_pct")
    if near and gap is not None:
        near_s = f"{near}{gap:+.1f}"
    else:
        near_s = ""
    return f"{sym:<10}{rank:>6}{rp:>6}{close:>8}{pvh_s:>7}{en:>3} {near_s:<10}"


_ROW_HEADER = f"{'Symbol':<10}{'Rank':>6}{'r/p':>6}{'Close':>8}{'Δhot%':>7}{'En':>3} Near-P"


def _format_scan_message(rows: list[dict]) -> str:
    trade_date = rows[0]["trade_date"]
    n_ath = sum(1 for r in rows if r.get("is_ath_dvpt"))
    n_ss  = sum(1 for r in rows if r.get("trigger_rank") == "SS")
    n_s   = sum(1 for r in rows if r.get("trigger_rank") == "S")
    n_a   = sum(1 for r in rows if r.get("trigger_rank") == "A")
    n_disc = sum(1 for r in rows
                 if r.get("price_vs_hot_avg_pct") is not None
                 and r["price_vs_hot_avg_pct"] < -3.0)
    n_near = sum(1 for r in rows
                 if r.get("next_p_above") and r.get("gap_to_next_p_pct") is not None
                 and r["gap_to_next_p_pct"] > -10.0)

    bits = []
    if n_ath:  bits.append(f"⚡ {n_ath} ATH-DVPT")
    if n_ss:   bits.append(f"SS×{n_ss}")
    if n_s:    bits.append(f"S×{n_s}")
    if n_a:    bits.append(f"A×{n_a}")
    if n_disc: bits.append(f"🟢 {n_disc} discount")
    if n_near: bits.append(f"🔥 {n_near} near-break")
    summary_line = " · ".join(bits) if bits else "No layered triggers."

    lines = [
        f"<b>🔎 DVPT scan — {trade_date}</b>",
        f"<i>{summary_line}</i>",
        "<i>Sort: ATH → p_score → r_score → discount → r1m. "
        "r/p = soft/hard baselines beaten (max 5/5). "
        "Near-P = closest P-wall above today.</i>",
        "",
        "<pre>",
        _ROW_HEADER,
    ]
    for r in rows:
        lines.append(_format_row(r))
    lines.append("</pre>")
    lines.append("")
    lines.append(
        "<i>Drill: <b>dvpt &lt;symbol&gt;</b>. "
        "Strict S/SS only: <b>/triggers</b>. "
        "About-to-break: <b>/triggers near</b>.</i>"
    )
    return "\n".join(lines)


async def on_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Strict layered triggers across the market (D28).

    /triggers       -> rank A or better (p_score >= 3)
    /triggers ss    -> SS only (p_score = 5)
    /triggers near  -> near-break candidates: gap_to_next_p_pct > -10% AND r_score >= 4
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    mode = (context.args[0].lower() if context.args else "").strip()
    if mode in ("ss", "supreme"):
        kind = "ss"; label = "SS only"
    elif mode in ("near", "near-break", "kissing"):
        kind = "near"; label = "near-break candidates"
    else:
        kind = "default"; label = "rank A+ (p_score ≥ 3)"

    await update.message.reply_text(f"🔎 Searching: {label}…")

    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(None, lambda: _scan_triggers(kind))

    if not rows:
        await update.message.reply_text(
            "No hits in this slice. Try <code>/scan</code> for the full ranking.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        _format_triggers_message(rows, kind, label), parse_mode="HTML"
    )


def _scan_triggers(kind: str) -> list[dict]:
    """Filter the latest trading day by strictness mode.

    kind:
      'ss'      -> p_score = 5 (SS only)
      'near'    -> next_p_above IS NOT NULL AND gap_to_next_p_pct > -10 AND r_score >= 4
      'default' -> p_score >= 3 (rank A or better)
    """
    if kind == "ss":
        extra_where = "AND s.p_score = 5"
    elif kind == "near":
        extra_where = ("AND s.next_p_above IS NOT NULL "
                       "AND s.gap_to_next_p_pct > -10 "
                       "AND COALESCE(s.r_score, 0) >= 4")
    else:
        extra_where = "AND s.p_score >= 3"

    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT s.symbol,
                       s.trade_date,
                       s.delivery_value_per_trade   AS dvpt,
                       s.ratio_today_vs_power_1m    AS r1m,
                       s.ratio_today_vs_power_3m    AS r3m,
                       s.trigger_rank,
                       s.r_score,
                       s.p_score,
                       s.is_ath_dvpt,
                       s.hot_days_avg_price,
                       s.price_vs_hot_avg_pct,
                       s.next_p_above,
                       s.gap_to_next_p_pct,
                       b.close,
                       b.deliv_per,
                       b.value AS total_value
                FROM stock_signals s
                JOIN bhavcopy_rows b USING (symbol, trade_date)
                WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)
                  {extra_where}
                  {_SCAN_FILTERS_SQL}
                {_LAYERED_ORDER_SQL}
                LIMIT 50""",
        ).fetchall()
        return [dict(r) for r in rows]


def _format_triggers_message(rows: list[dict], kind: str, label: str) -> str:
    trade_date = rows[0]["trade_date"]
    n_ath = sum(1 for r in rows if r.get("is_ath_dvpt"))
    n_ss = sum(1 for r in rows if r.get("trigger_rank") == "SS")
    n_s = sum(1 for r in rows if r.get("trigger_rank") == "S")
    n_a = sum(1 for r in rows if r.get("trigger_rank") == "A")

    bits = [f"({label})"]
    if n_ath: bits.append(f"⚡ {n_ath} ATH")
    if n_ss: bits.append(f"SS×{n_ss}")
    if n_s and kind != "ss": bits.append(f"S×{n_s}")
    if n_a and kind not in ("ss",): bits.append(f"A×{n_a}")
    summary = " · ".join(bits)

    lines = [
        f"<b>⚡ Layered triggers — {trade_date}</b>",
        f"<i>{summary}</i>",
        "<i>r/p = R-tier / P-tier baselines beaten (5/5 = above all rolling avgs / power baselines). "
        "Near-P shows next P-wall above today's DVPT.</i>",
        "",
        "<pre>",
        _ROW_HEADER,
    ]
    for r in rows:
        lines.append(_format_row(r))
    lines.append("</pre>")
    lines.append("")
    lines.append(
        "<i>Drill: <b>dvpt &lt;symbol&gt;</b>. "
        "Full market view: <b>/scan [N]</b>.</i>"
    )
    return "\n".join(lines)


async def _handle_stock_intent(update: Update, cls: dict) -> None:
    """Execute SCORE/FLOW/BOTH intent against the existing rule-based pipelines.

    Posts results to the same chat the message came from. No LLM in the
    output path itself — patearn scoring is pure Python, DVPT lookup is pure SQL.
    """
    ticker = cls["ticker"].upper().strip()
    intent_type = cls["intent"]
    label = {
        "SCORE": "patearn score",
        "FLOW": "delivery flow",
        "BOTH": "patearn score + delivery flow",
    }[intent_type]
    await update.message.reply_text(
        f"🔍 Looking up <b>{ticker}</b> ({label})…",
        parse_mode="HTML",
    )

    loop = asyncio.get_event_loop()

    if intent_type in ("SCORE", "BOTH"):
        from src.automation import scoring as _scoring, screener as _screener
        try:
            score = await loop.run_in_executor(
                None, lambda: _scoring.score_symbol(ticker)
            )
            fundamentals = await loop.run_in_executor(
                None, lambda: _screener.fetch_company(ticker, use_cache=True)
            )
            msg = _scoring.format_score_for_telegram(score, fundamentals=fundamentals)
            await update.message.reply_text(
                msg, parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as e:
            log.exception("score failed for %s via natural-language path", ticker)
            await update.message.reply_text(f"⚠️ Score failed: {e}")

    if intent_type in ("FLOW", "BOTH"):
        rows = await loop.run_in_executor(
            None, lambda: _fetch_flow_rows(ticker, 15)
        )
        if not rows:
            await update.message.reply_text(
                f"No DVPT data for <b>{ticker}</b>. May not be in EQ series, "
                f"or insufficient history.",
                parse_mode="HTML",
            )
        else:
            msg = _format_flow_message(ticker, rows)
            await update.message.reply_text(msg, parse_mode="HTML")


# --- Menu system (D29 — inline keyboard discovery layer) ------------------
#
# Goal: reduce the cognitive load of remembering slash commands. Tap /menu
# (or "Menu" in the slash dropdown) → tree of buttons → action runs. All
# existing slash commands and natural-language routing remain unchanged;
# this is purely additive discovery. Zero LLM cost — pure button routing.
#
# Callback data scheme (Telegram caps payloads at 64 bytes):
#   m:<node>            -> navigate to menu node (root / scan / trig / watch)
#   a:<action>[:<arg>]  -> run a leaf action
# For leaf actions that need a ticker, we set context.user_data["menu_pending"]
# = <action_key> and prompt; the next plain text message gets consumed as the
# ticker (see on_message at the top of its body).


def _menu_root_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Quality score (pt14)", callback_data="a:pt14")],
        [InlineKeyboardButton("💧 Delivery flow (dvpt)", callback_data="a:dvpt")],
        [InlineKeyboardButton("🔎 Market scan",          callback_data="m:scan")],
        [InlineKeyboardButton("⚡ Layered triggers",      callback_data="m:trig")],
        [InlineKeyboardButton("⭐ Watchlist",             callback_data="m:watch")],
        [InlineKeyboardButton("⚙️ Status",                callback_data="a:status")],
    ])


def _menu_scan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Top 15 (default)", callback_data="a:scan:15")],
        [InlineKeyboardButton("Top 25",           callback_data="a:scan:25")],
        [InlineKeyboardButton("Top 50",           callback_data="a:scan:50")],
        [InlineKeyboardButton("« Back",           callback_data="m:root")],
    ])


def _menu_triggers_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Rank A+ (default — p_score ≥ 3)", callback_data="a:trig:def")],
        [InlineKeyboardButton("⚡ SS only (rarest — p_score = 5)", callback_data="a:trig:ss")],
        [InlineKeyboardButton("🔥 Near-break (about to cross)",    callback_data="a:trig:near")],
        [InlineKeyboardButton("« Back",                            callback_data="m:root")],
    ])


def _menu_watchlist_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Show watchlist", callback_data="a:watch:show")],
        [InlineKeyboardButton("➕ Add ticker",     callback_data="a:watch:add")],
        [InlineKeyboardButton("➖ Remove ticker",  callback_data="a:watch:rm")],
        [InlineKeyboardButton("« Back",            callback_data="m:root")],
    ])


_MENU_ROOT_TEXT = (
    "<b>Hermes menu</b> — pick a strategy.\n"
    "<i>All slash commands still work. Type /menu anytime to return here.</i>"
)
_MENU_SCAN_TEXT     = "<b>🔎 Market scan</b> — how many top stocks?"
_MENU_TRIGGERS_TEXT = "<b>⚡ Layered triggers</b> — pick a strictness."
_MENU_WATCHLIST_TEXT = "<b>⭐ Watchlist</b>"


async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the inline-keyboard menu at root."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    # If we were waiting for a ticker, opening the menu cancels that pending state.
    context.user_data.pop("menu_pending", None)
    await update.message.reply_text(
        _MENU_ROOT_TEXT, reply_markup=_menu_root_keyboard(), parse_mode="HTML"
    )


async def on_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route every inline-keyboard tap from the menu tree."""
    query = update.callback_query
    if not query:
        return
    user_id = query.from_user.id
    if not _is_authorized(user_id):
        await query.answer("Unauthorized.", show_alert=True)
        return
    # Acknowledge so Telegram stops the loading spinner on the button.
    await query.answer()

    data = query.data or ""
    chat_id = query.message.chat_id

    # --- Navigation (edit message in place to swap keyboards) ---
    if data == "m:root":
        await query.edit_message_text(
            _MENU_ROOT_TEXT, reply_markup=_menu_root_keyboard(), parse_mode="HTML"
        )
        return
    if data == "m:scan":
        await query.edit_message_text(
            _MENU_SCAN_TEXT, reply_markup=_menu_scan_keyboard(), parse_mode="HTML"
        )
        return
    if data == "m:trig":
        await query.edit_message_text(
            _MENU_TRIGGERS_TEXT, reply_markup=_menu_triggers_keyboard(), parse_mode="HTML"
        )
        return
    if data == "m:watch":
        await query.edit_message_text(
            _MENU_WATCHLIST_TEXT, reply_markup=_menu_watchlist_keyboard(), parse_mode="HTML"
        )
        return

    # --- Leaf actions ---
    # Ticker prompts: set pending state, send a follow-up message.
    if data == "a:pt14":
        context.user_data["menu_pending"] = "pt14"
        log.info(
            "menu callback a:pt14 set menu_pending=pt14 for user_id=%s "
            "user_data_keys=%s",
            user_id, list(context.user_data.keys()),
        )
        await context.bot.send_message(
            chat_id,
            "📊 Type the NSE ticker for the quality score.\n"
            "<i>e.g. RELIANCE — or type /menu to cancel.</i>",
            parse_mode="HTML",
        )
        return
    if data == "a:dvpt":
        context.user_data["menu_pending"] = "dvpt"
        log.info(
            "menu callback a:dvpt set menu_pending=dvpt for user_id=%s "
            "user_data_keys=%s",
            user_id, list(context.user_data.keys()),
        )
        await context.bot.send_message(
            chat_id,
            "💧 Type the NSE ticker for delivery flow.\n"
            "<i>e.g. PIXTRANS — or type /menu to cancel.</i>",
            parse_mode="HTML",
        )
        return
    if data == "a:watch:add":
        context.user_data["menu_pending"] = "watch_add"
        await context.bot.send_message(
            chat_id,
            "➕ Type the NSE ticker to add. <i>/menu to cancel.</i>",
            parse_mode="HTML",
        )
        return
    if data == "a:watch:rm":
        context.user_data["menu_pending"] = "watch_rm"
        await context.bot.send_message(
            chat_id,
            "➖ Type the NSE ticker to remove. <i>/menu to cancel.</i>",
            parse_mode="HTML",
        )
        return
    if data == "a:watch:show":
        await _menu_run_watchlist_show(context, chat_id)
        return

    # Scan — instant action with the chosen N.
    if data.startswith("a:scan:"):
        try:
            n = int(data.split(":")[2])
        except (IndexError, ValueError):
            n = 15
        await _menu_run_scan(context, chat_id, n)
        return

    # Triggers — instant action with the chosen kind.
    if data.startswith("a:trig:"):
        kind_key = data.split(":")[2]
        kind = {"def": "default", "ss": "ss", "near": "near"}.get(kind_key, "default")
        await _menu_run_triggers(context, chat_id, kind)
        return

    # Status / provider — instant action.
    if data == "a:status":
        await _menu_run_status(context, chat_id)
        return

    # Unrecognised callback (shouldn't happen).
    await context.bot.send_message(chat_id, "Unknown menu action.")


# --- Menu action runners (share logic with slash-command handlers) --------

async def _menu_run_scan(context: ContextTypes.DEFAULT_TYPE, chat_id: int, n: int) -> None:
    n = max(5, min(n, 50))
    await context.bot.send_message(chat_id, f"🔎 Scanning top {n}…")
    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(None, lambda: _scan_top_dvpt(n))
    if not rows:
        await context.bot.send_message(
            chat_id, "No signal data for the latest trading day."
        )
        return
    await context.bot.send_message(
        chat_id, _format_scan_message(rows), parse_mode="HTML"
    )


async def _menu_run_triggers(context: ContextTypes.DEFAULT_TYPE, chat_id: int, kind: str) -> None:
    label = {"default": "rank A+ (p_score ≥ 3)", "ss": "SS only",
             "near": "near-break candidates"}.get(kind, "rank A+")
    await context.bot.send_message(chat_id, f"🔎 Searching: {label}…")
    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(None, lambda: _scan_triggers(kind))
    if not rows:
        await context.bot.send_message(
            chat_id, f"No hits in this slice. Try /scan for the full ranking."
        )
        return
    await context.bot.send_message(
        chat_id, _format_triggers_message(rows, kind, label), parse_mode="HTML"
    )


async def _menu_run_watchlist_show(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, note, added_at FROM watchlist ORDER BY symbol"
        ).fetchall()
    if not rows:
        await context.bot.send_message(
            chat_id, "Watchlist empty. Add via the menu or <code>/watch TICKER</code>.",
            parse_mode="HTML",
        )
        return
    lines = ["<b>⭐ Watchlist:</b>", ""]
    for r in rows:
        note = f" — <i>{r['note']}</i>" if r["note"] else ""
        lines.append(f"• <b>{r['symbol']}</b>{note}")
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")


async def _menu_run_status(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    from src.core.llm_router import active_classifier_provider
    provider = active_classifier_provider()
    if provider == "gemini":
        msg = (
            f"<b>Classifier provider:</b> Gemini Flash "
            f"(<code>{settings.gemini_classifier_model}</code>)\n"
            f"<b>Chat:</b> Anthropic ({settings.fast_model})"
        )
    else:
        msg = (
            f"<b>Classifier provider:</b> Anthropic Haiku ({settings.fast_model})\n"
            f"<i>Add GEMINI_API_KEY in .env to switch to Gemini Flash (~13× cheaper).</i>"
        )
    await context.bot.send_message(chat_id, msg, parse_mode="HTML")


async def _menu_handle_pending(
    update: Update, context: ContextTypes.DEFAULT_TYPE, pending: str, text: str,
) -> None:
    """Consume a plain-text message as the answer to a previous menu prompt.

    pending is one of: pt14 / dvpt / watch_add / watch_rm. The text is the
    user's reply (expected to be an NSE ticker, possibly with extra args).
    """
    # Clear pending state first — any failure shouldn't trap the user.
    context.user_data.pop("menu_pending", None)

    ticker = text.split()[0].upper().strip() if text else ""
    if not ticker:
        await update.message.reply_text("No ticker received. /menu to retry.")
        return

    chat_id = update.effective_chat.id
    loop = asyncio.get_event_loop()

    if pending == "pt14":
        await update.message.reply_text(
            f"🔢 Scoring <b>{ticker}</b>…", parse_mode="HTML"
        )
        from src.automation import scoring as _scoring, screener as _screener
        try:
            score = await loop.run_in_executor(
                None, lambda: _scoring.score_symbol(ticker)
            )
            fundamentals = await loop.run_in_executor(
                None, lambda: _screener.fetch_company(ticker, use_cache=True)
            )
            msg = _scoring.format_score_for_telegram(score, fundamentals=fundamentals)
            await context.bot.send_message(
                chat_id, msg, parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as e:
            log.exception("menu pt14 failed for %s", ticker)
            await update.message.reply_text(f"⚠️ Score failed: {e}")
        return

    if pending == "dvpt":
        rows = await loop.run_in_executor(None, lambda: _fetch_flow_rows(ticker, 15))
        if not rows:
            await update.message.reply_text(
                f"No DVPT data for <b>{ticker}</b>. Check the ticker symbol.",
                parse_mode="HTML",
            )
            return
        await context.bot.send_message(
            chat_id, _format_flow_message(ticker, rows), parse_mode="HTML"
        )
        return

    if pending == "watch_add":
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO watchlist (symbol, note, added_by) VALUES (?, NULL, ?)
                   ON CONFLICT(symbol) DO UPDATE SET added_by = excluded.added_by""",
                (ticker, update.effective_user.id),
            )
        await update.message.reply_text(
            f"✓ <b>{ticker}</b> added to watchlist.", parse_mode="HTML"
        )
        return

    if pending == "watch_rm":
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (ticker,))
            ok = cur.rowcount > 0
        await update.message.reply_text(
            f"✓ Removed <b>{ticker}</b> from watchlist." if ok
            else f"<b>{ticker}</b> was not on the watchlist.",
            parse_mode="HTML",
        )
        return


# --- Plain-text message handler -------------------------------------------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any plain text message.

    Flow:
      1. Auth gate.
      2. If a menu prompt is pending (user tapped a button expecting a
         ticker), consume this message as the answer.
      3. Natural-language intent classification (Haiku/Gemini classifier).
      4. If intent is SCORE/FLOW/BOTH and a ticker was extracted → run the
         relevant data lookup (same code paths as /pt14 and /dvpt).
      5. Otherwise → conversational reply with memory (existing chat handler).
    """
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id

    # Auth gate — done BEFORE any LLM call. Silent for unauthorized senders in
    # groups (so other group members don't get an "unauthorized" reply spam).
    if not _is_authorized(user_id):
        if update.effective_chat.type == "private":
            await update.message.reply_text(_unauthorized_message(user_id), parse_mode="HTML")
        else:
            log.info("ignoring unauthorized user_id=%s in group %s",
                     user_id, update.effective_chat.id)
        return

    text = update.message.text.strip()

    # --- Menu state: a previous button tap left us waiting for a ticker ---
    pending = context.user_data.get("menu_pending")
    log.info(
        "on_message: user_id=%s text=%r menu_pending=%r user_data_keys=%s",
        user_id, text[:40], pending, list(context.user_data.keys()),
    )
    if pending:
        await _menu_handle_pending(update, context, pending, text)
        return

    # --- Natural-language intent routing ---
    # Plain English maps to /pt14, /dvpt or both without the user typing slashes.
    from src.assistant import intent as _intent
    loop = asyncio.get_event_loop()
    cls = await loop.run_in_executor(None, lambda: _intent.classify(text))

    if cls.get("intent") in ("SCORE", "FLOW", "BOTH") and cls.get("ticker"):
        await _handle_stock_intent(update, cls)
        return
    if cls.get("intent") == "SCAN":
        # Reuse the /scan handler logic via a synthetic context
        class _C:
            args = []
        await on_scan(update, _C())
        return
    # Otherwise: fall through to conversational chat below.

    conv_id = conversations.get_or_create_for_telegram(user_id)
    log.info("telegram user_id=%s conv_id=%s incoming msg", user_id, conv_id)

    # Show "typing..." in Telegram while the LLM call is in flight
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    # chat.handle() is sync (uses sqlite3 + Anthropic SDK sync client).
    # Run it in a thread so we don't block the asyncio event loop.
    # Telegram defaults to fast=True (Haiku) — ~5x cheaper than Sonnet, which
    # is the right default for casual phone chat. Use the /chat HTTP endpoint
    # without fast=true if you want Sonnet-grade reasoning.
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: chat.handle(update.message.text, conversation_id=conv_id, fast=True),
    )

    # Telegram caps a single message at ~4096 chars. Chunk if needed.
    reply = result["reply"]
    for chunk in _chunk_text(reply, limit=4000):
        await update.message.reply_text(chunk)


def _chunk_text(text: str, *, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + limit])
        start += limit
    return chunks


# --- Entry point ------------------------------------------------------------

BOT_COMMANDS = [
    BotCommand("menu",          "Open the menu — pick a strategy without remembering commands"),
    BotCommand("pt14",          "patearn 14-pattern rule-based score (FREE — no LLM, /pt14 RELIANCE)"),
    BotCommand("dvpt",          "Delivery-Value-Per-Trade institutional signal (FREE, /dvpt TICKER [days])"),
    BotCommand("scan",          "Top stocks — two-tier ranked (ATH → p_score → r_score → discount → r1m) (FREE)"),
    BotCommand("triggers",      "Strict layered triggers: rank A+, SS-only, or near-break (FREE, /triggers [ss|near])"),
    BotCommand("analyze",       "Guide for deep dive in claude.ai (FREE — replaces the old API-burning /analyze)"),
    BotCommand("watch",         "Add stock to watchlist"),
    BotCommand("unwatch",       "Remove stock from watchlist"),
    BotCommand("watchlist",     "Show watched stocks"),
    BotCommand("patearn_here",  "Set this chat as patearn destination"),
    BotCommand("patearn_stop",  "Stop posting patearn to this chat"),
    BotCommand("news",          "Fetch a fresh market brief now"),
    BotCommand("news_here",     "Set this chat as the news destination"),
    BotCommand("news_where",    "List registered news destinations"),
    BotCommand("news_stop",     "Stop posting news to this chat"),
    BotCommand("reset",         "Start a fresh conversation (forget context)"),
    BotCommand("provider",      "Show which LLM provider is active for classifier tasks"),
    BotCommand("whoami",        "Show my Telegram user ID"),
    BotCommand("start",         "Show help"),
]


async def _register_commands(application: Application) -> None:
    """Tell Telegram which commands this bot supports, so they appear in the
    slash-menu dropdown on every client (mobile + desktop)."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    log.info("registered %d slash-menu commands with Telegram", len(BOT_COMMANDS))


def main() -> None:
    if not settings.telegram_bot_token:
        log.error("TELEGRAM_BOT_TOKEN not set in .env — refusing to start.")
        return

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(_register_commands)
        .build()
    )
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("menu", on_menu))
    # Inline-keyboard taps from the menu tree — pure routing, no LLM.
    app.add_handler(CallbackQueryHandler(on_menu_callback))
    app.add_handler(CommandHandler("provider", on_provider))
    app.add_handler(CommandHandler("whoami", on_whoami))
    app.add_handler(CommandHandler("reset", on_reset))
    app.add_handler(CommandHandler("pt14", on_pt14))
    app.add_handler(CommandHandler("dvpt", on_dvpt))
    app.add_handler(CommandHandler("scan", on_scan))
    app.add_handler(CommandHandler("triggers", on_triggers))
    app.add_handler(CommandHandler("analyze", on_analyze))
    app.add_handler(CommandHandler("watch", on_watch))
    app.add_handler(CommandHandler("unwatch", on_unwatch))
    app.add_handler(CommandHandler("watchlist", on_watchlist))
    app.add_handler(CommandHandler("patearn_here", on_patearn_here))
    app.add_handler(CommandHandler("patearn_stop", on_patearn_stop))
    app.add_handler(CommandHandler("news", on_news))
    app.add_handler(CommandHandler("news_here", on_news_here))
    app.add_handler(CommandHandler("news_stop", on_news_stop))
    app.add_handler(CommandHandler("news_where", on_news_where))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    allowed = _allowed_user_ids()
    log.info(
        "Hermes Telegram bot starting — polling mode. Authorized user IDs: %s",
        allowed if allowed else "(none — first messages will receive onboarding reply)",
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
