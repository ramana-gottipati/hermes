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

from telegram import BotCommand, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
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
            "Hi — I'm Hermes, your personal AI agent.\n\n"
            "Just send me a message. I remember our conversation across messages.\n\n"
            "Commands:\n"
            "/reset — start a fresh conversation (forget context)\n"
            "/whoami — show your Telegram user ID"
        )
    else:
        await update.message.reply_text(_unauthorized_message(user_id), parse_mode="HTML")


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


def _run_patearn_analysis(ticker: str, extra: str = "") -> str:
    """Synchronous Claude call for full patearn analysis on a ticker."""
    from src.assistant import patearn
    from src.core.llm import client

    response = client().messages.create(
        model=settings.default_model,  # Sonnet — patearn analysis needs reasoning
        max_tokens=4096,
        system=patearn.analysis_system_prompt(),
        messages=[
            {"role": "user", "content": patearn.user_message_for_ticker(ticker, extra=extra)}
        ],
    )
    log.info(
        "patearn analysis for %s: in=%d out=%d cache_read=%d cache_create=%d",
        ticker,
        response.usage.input_tokens,
        response.usage.output_tokens,
        getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
    )
    return response.content[0].text


async def on_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run a full patearn New Stock Analysis on the given ticker.

    Usage: /analyze TICKER [optional notes]
    Example: /analyze RELIANCE
             /analyze HDFCBANK margin compression concern
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: <code>/analyze TICKER [optional notes]</code>\n"
            "Example: <code>/analyze RELIANCE</code>",
            parse_mode="HTML",
        )
        return

    ticker = args[0].upper().strip()
    extra = " ".join(args[1:]).strip()

    await update.message.reply_text(
        f"🔍 Running patearn analysis on <b>{ticker}</b>… typically 30-60 seconds.",
        parse_mode="HTML",
    )

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: _run_patearn_analysis(ticker, extra=extra),
        )
    except Exception as e:
        log.exception("patearn analysis failed for %s", ticker)
        await update.message.reply_text(f"⚠️ Analysis failed: {e}")
        return

    # patearn output is long, often 2-4K chars; chunk to fit Telegram's 4096 cap.
    for chunk in _chunk_plain(result, limit=3800):
        await update.message.reply_text(chunk)


def _chunk_plain(text: str, limit: int) -> list[str]:
    """Split long text on paragraph boundaries to fit Telegram's per-message cap."""
    if len(text) <= limit:
        return [text]
    out, buf, cur = [], [], 0
    for para in text.split("\n\n"):
        block = para + "\n\n"
        if cur + len(block) > limit and buf:
            out.append("".join(buf).rstrip())
            buf, cur = [], 0
        buf.append(block)
        cur += len(block)
    if buf:
        out.append("".join(buf).rstrip())
    return out


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any plain text message — the main chat path.

    Responds in any chat (DM or group). The auth gate below ensures only the
    bot owner gets responses; anyone else in a group is silently ignored so
    the bot doesn't burn LLM credits or leak that it's listening.
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
    BotCommand("analyze",    "Run patearn analysis on a stock (e.g. /analyze RELIANCE)"),
    BotCommand("news",       "Fetch a fresh market brief now"),
    BotCommand("news_here",  "Set this chat as the news destination"),
    BotCommand("news_where", "List registered news destinations"),
    BotCommand("news_stop",  "Stop posting news to this chat"),
    BotCommand("reset",      "Start a fresh conversation (forget context)"),
    BotCommand("whoami",     "Show my Telegram user ID"),
    BotCommand("start",      "Show help"),
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
    app.add_handler(CommandHandler("whoami", on_whoami))
    app.add_handler(CommandHandler("reset", on_reset))
    app.add_handler(CommandHandler("analyze", on_analyze))
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
