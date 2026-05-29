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
            "Hi — I'm Hermes.\n\n"
            "<b>Just type in plain English</b>:\n"
            "  • \"what's pixtrans?\" — full read (score + delivery flow)\n"
            "  • \"score reliance\" — patearn quality reading\n"
            "  • \"any institutional buying in hdfc?\" — DVPT signal\n"
            "  • \"is tata steel a good buy?\" — score\n"
            "  • or just chat with me about anything\n\n"
            "<b>Slash commands</b> (if you prefer):\n"
            "/pt14 TICKER · /dvpt TICKER · /analyze TICKER · /watch TICKER\n"
            "/news · /reset · /whoami",
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
                      s.ratio_today_vs_power_3m AS r3m
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
    lines.append("")
    lines.append(
        "<i>DVPT = (delivery quantity × close) ÷ number of trades. "
        "Power baselines use top-N within trailing windows: top 5 of 22 days (1m), "
        "top 15 of 66 days (3m). Value-based — naturally invariant to splits/bonuses.</i>"
    )
    return "\n".join(lines)


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


def _scan_top_dvpt(n: int) -> list[dict]:
    """Top N EQ stocks by ratio_today_vs_power_1m for the latest trading day.

    Liquidity filter: at least ₹1 Cr total turnover (filters out shell-stock noise
    that often shows extreme ratios on tiny volumes).
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.symbol,
                      s.trade_date,
                      s.delivery_value_per_trade AS dvpt,
                      s.ratio_today_vs_power_1m  AS r1m,
                      s.ratio_today_vs_power_3m  AS r3m,
                      b.close,
                      b.deliv_per,
                      b.value AS total_value
               FROM stock_signals s
               JOIN bhavcopy_rows b USING (symbol, trade_date)
               WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)
                 AND b.series = 'EQ'
                 AND (b.segment = 'CM' OR b.segment IS NULL)
                 AND s.ratio_today_vs_power_1m IS NOT NULL
                 AND b.value > 10000000
               ORDER BY s.ratio_today_vs_power_1m DESC
               LIMIT ?""",
            (n,),
        ).fetchall()
        return [dict(r) for r in rows]


def _format_scan_message(rows: list[dict]) -> str:
    trade_date = rows[0]["trade_date"]
    n_exceptional = sum(1 for r in rows if (r["r1m"] or 0) > 1.50)
    n_institutional = sum(1 for r in rows if 1.00 < (r["r1m"] or 0) <= 1.50)

    header_summary = []
    if n_exceptional:
        header_summary.append(f"⚡ {n_exceptional} exceptional (r1m &gt; 1.50)")
    if n_institutional:
        header_summary.append(f"🟢 {n_institutional} institutional (1.00 &lt; r1m ≤ 1.50)")
    summary_line = " · ".join(header_summary) if header_summary else "No institutional-intensity hits in this scan."

    lines = [
        f"<b>🔎 Top institutional-flow signals — {trade_date}</b>",
        f"<i>{summary_line}</i>",
        "<i>Ranked by ratio_today_vs_power_1m. Liquidity filter: turnover &gt; ₹1 Cr.</i>",
        "",
        "<pre>",
        f"{'Symbol':<12}{'Close':>9}{'Deliv%':>8}{'DVPT':>11}{'r1m':>7}{'r3m':>7}",
    ]
    for r in rows:
        sym = (r["symbol"] or "")[:12]
        close = f"{r['close']:,.1f}" if r["close"] else "—"
        deliv = f"{r['deliv_per']:,.1f}" if r["deliv_per"] is not None else "—"
        dvpt = f"{int(r['dvpt']):,}" if r["dvpt"] else "—"
        r1m = f"{r['r1m']:.2f}" if r["r1m"] is not None else "—"
        r3m = f"{r['r3m']:.2f}" if r["r3m"] is not None else "—"
        lines.append(f"{sym:<12}{close:>9}{deliv:>8}{dvpt:>11}{r1m:>7}{r3m:>7}")
    lines.append("</pre>")
    lines.append("")
    lines.append("<i>Drill into any name: type \"<b>dvpt &lt;symbol&gt;</b>\" or \"<b>what's &lt;symbol&gt;?</b>\".</i>")
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


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any plain text message.

    Flow:
      1. Auth gate.
      2. Natural-language intent classification (Haiku, ~₹0.10 per message).
      3. If intent is SCORE/FLOW/BOTH and a ticker was extracted → run the
         relevant data lookup (same code paths as /pt14 and /dvpt).
      4. Otherwise → conversational reply with memory (existing chat handler).
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
    BotCommand("pt14",          "patearn 14-pattern rule-based score (FREE — no LLM, /pt14 RELIANCE)"),
    BotCommand("dvpt",          "Delivery-Value-Per-Trade institutional signal (FREE, /dvpt TICKER [days])"),
    BotCommand("scan",          "Top stocks across the market by DVPT signal — yesterday's smart money (FREE)"),
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
    app.add_handler(CommandHandler("provider", on_provider))
    app.add_handler(CommandHandler("whoami", on_whoami))
    app.add_handler(CommandHandler("reset", on_reset))
    app.add_handler(CommandHandler("pt14", on_pt14))
    app.add_handler(CommandHandler("dvpt", on_dvpt))
    app.add_handler(CommandHandler("scan", on_scan))
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
