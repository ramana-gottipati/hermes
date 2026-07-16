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
import html as _html
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
from src.automation.signals import accum_character_read, is_near_key
from src.core.db import get_conn
from src.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("hermes.telegram")


def _h(s) -> str:
    """HTML-escape a value before it goes into a parse_mode=HTML message.

    Telegram chat titles / user full names are USER-CONTROLLED (a group named
    '<b>x' or 'A & B' breaks the markup, or worse). Escape every such value at
    the render site (CL-SYS-09)."""
    return _html.escape(str(s) if s is not None else "(unnamed)")


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
            "  3. <b>Slash commands</b> — /pt14 TICKER · /dvpt TICKER · /scan · /triggers [ss|near|accum|distrib]\n"
            "     <b>⭐ /conviction</b> — the shortlist where all 3 pillars align\n\n"
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
        f"Type: <b>{_h(chat.type)}</b>\n"
        f"Title: <b>{_h(chat.title or chat.full_name or '(unnamed)')}</b>\n"
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
        lines.append(f"• {_h(r['chat_title'])} (<code>{r['chat_id']}</code>, {_h(r['chat_type'])})")
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
    loop = asyncio.get_running_loop()
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

    loop = asyncio.get_running_loop()
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
                      s.avg_close_p6m, s.avg_close_p12m,
                      s.accum_character, s.delivery_value_today,
                      s.deliv_value_ratio_1m_6m, s.trade_count_ratio_1m_6m,
                      s.avg_deliv_pct_1m, s.avg_deliv_pct_6m,
                      s.deliv_updown_ratio_3m, s.accum_price_drift_3m,
                      s.pct_from_52w_high,
                      s.key_price_p1m, s.key_price_p2m, s.key_price_p3m,
                      s.key_price_p6m, s.key_price_p12m,
                      s.gap_to_key_p1m, s.gap_to_key_p2m, s.gap_to_key_p3m,
                      s.gap_to_key_p6m, s.gap_to_key_p12m,
                      s.avg_trade_qty, s.avg_deliv_qty_per_trade,
                      s.turnover_surge_1m, s.turnover_surge_3m, s.turnover_surge_1y
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


# D43 — accumulation/distribution character tags (Telegram). Shares the label
# vocabulary produced by signals.accum_character.
_CHAR_TG = {
    "ACCUMULATION":  "🟢 ACCUMULATION",
    "DISTRIBUTION":  "🔴 DISTRIBUTION ⚠️",
    "CONSOLIDATION": "🟡 CONSOLIDATION",
    "NEUTRAL":       "⚪ NEUTRAL",
}
_CHAR_MARK = {"ACCUMULATION": "🟢", "DISTRIBUTION": "🔴",
              "CONSOLIDATION": "🟡", "NEUTRAL": "⚪"}


def _char_tag(label) -> str:
    return _CHAR_TG.get(label or "", "—")


def _char_marker(label) -> str:
    """One-glyph character marker for fixed-width scan rows."""
    return _CHAR_MARK.get(label or "", " ")


def _format_keyprice_block(latest: dict) -> list[str]:
    """D44 — the '📍 Key price (value-weighted)' block: per-horizon institutional
    key price + signed gap + 🎯 near-key flag + ticket size + turnover surge.
    Empty list until the key-price backfill has run (pre-D44 rows)."""
    defs = (("1M", "key_price_p1m", "gap_to_key_p1m"),
            ("2M", "key_price_p2m", "gap_to_key_p2m"),
            ("3M", "key_price_p3m", "gap_to_key_p3m"),
            ("6M", "key_price_p6m", "gap_to_key_p6m"),
            ("12M", "key_price_p12m", "gap_to_key_p12m"))
    if not any(latest.get(c) for _, c, _ in defs):
        return []
    out = ["<b>📍 Key price (value-weighted — big institutional day dominates)</b>"]
    near = []
    for lbl, kc, gc in defs:
        kp = latest.get(kc)
        if kp is None:
            continue
        g = latest.get(gc)
        nk = is_near_key(g)
        if nk:
            near.append(lbl)
        gtxt = f"{g:+.1f}%" if g is not None else "—"
        out.append(f"  {lbl}: ₹{kp:,.1f} ({gtxt}){' 🎯' if nk else ''}")
    if near:
        out.append(f"<i>🎯 launch band on {', '.join(near)} — close within −1%…+5% "
                   f"of the institutional cost.</i>")
    tq = latest.get("avg_trade_qty")
    td = latest.get("avg_deliv_qty_per_trade")
    s1, s3, s1y = (latest.get("turnover_surge_1m"), latest.get("turnover_surge_3m"),
                   latest.get("turnover_surge_1y"))
    out.append(
        f"  Ticket: {_fmt_int(tq) if tq is not None else '—'} sh/trade · "
        f"deliv {_fmt_int(td) if td is not None else '—'} · surge 1m/3m/1y: "
        f"{_fmt_ratio(s1)}× / {_fmt_ratio(s3)}× / {_fmt_ratio(s1y)}×")
    return out


def _format_character_block(latest: dict) -> list[str]:
    """D43 — the '🧭 Character' block: label + plain-English read + the WHO row
    (total delivery ₹, delivery %, up/down split, breadth) + 52w-high distance.
    Empty list if the character hasn't been computed yet (pre-backfill)."""
    label = latest.get("accum_character")
    if not label:
        return []
    read = accum_character_read(
        label, latest.get("p_score"), latest.get("trade_count_ratio_1m_6m"),
        latest.get("deliv_updown_ratio_3m"), latest.get("accum_price_drift_3m"),
        latest.get("pct_from_52w_high"), latest.get("deliv_value_ratio_1m_6m"),
    )
    dvt = latest.get("delivery_value_today")
    dvt_cr = f"₹{dvt / 1e7:,.1f} Cr" if dvt else "—"
    dp1, dp6 = latest.get("avg_deliv_pct_1m"), latest.get("avg_deliv_pct_6m")
    tcr = latest.get("trade_count_ratio_1m_6m")
    breadth = ("broadening (retail crowd)" if (tcr is not None and tcr >= 1.3)
               else "concentrated (few hands)" if (tcr is not None and tcr <= 1.1)
               else "steady" if tcr is not None else "—")
    pfh = latest.get("pct_from_52w_high")
    drift = latest.get("accum_price_drift_3m")
    lines = [
        f"<b>🧭 Character: {_char_tag(label)}</b>",
        (f"<i>{read}</i>" if read else ""),
        f"  Total delivery: <b>{dvt_cr}</b> · Deliv% 1m/6m: "
        f"{_fmt_money(dp1) if dp1 is not None else '—'}/{_fmt_money(dp6) if dp6 is not None else '—'}",
        f"  Up/down deliv (3m): <b>{_fmt_ratio(latest.get('deliv_updown_ratio_3m'))}</b> · {breadth}",
        f"  vs 52w-high: {('%+.1f%%' % pfh) if pfh is not None else '—'} · "
        f"3m drift: {('%+.1f%%' % drift) if drift is not None else '—'}",
    ]
    return [x for x in lines if x != ""]


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

    # --- D43 accumulation/distribution character -------------------------
    char_lines = _format_character_block(latest)
    if char_lines:
        lines.append("")
        lines.extend(char_lines)

    # --- D44 value-weighted key price + entry/ticket/surge ----------------
    kp_lines = _format_keyprice_block(latest)
    if kp_lines:
        lines.append("")
        lines.extend(kp_lines)

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

    loop = asyncio.get_running_loop()
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
        f"Title: <b>{_h(chat.title or chat.full_name or '(unnamed)')}</b>\n"
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

    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, lambda: _scan_top_dvpt(n))

    if not rows:
        await update.message.reply_text(
            "No signal data found for the latest trading day. "
            "Run <code>/dvpt &lt;TICKER&gt;</code> on individual stocks instead.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(_format_scan_message(rows), parse_mode="HTML")


# --- D32 Index + ratio (sector vs broad) surface --------------------------

_TREND_EMOJI = {
    "BREAKOUT": "⚡",
    "UPTREND":  "🟢",
    "CONSOLIDATING": "🟡",
    "DOWNTREND": "🔴",
    "BREAKDOWN": "⬇️",
    "UNKNOWN":   "—",
}


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:+.1f}%"


def _fmt_signed_int(v) -> str:
    if v is None:
        return "—"
    return f"{int(v):+,}"


async def on_index(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show one index's level + technicals + RS vs broad (D32)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/index NAME</code> — e.g. <code>/index NIFTYBANK</code>",
            parse_mode="HTML",
        )
        return
    raw = " ".join(context.args).upper().strip()
    loop = asyncio.get_running_loop()
    name, sig = await loop.run_in_executor(None, lambda: _resolve_index_signal(raw))
    if not sig:
        await update.message.reply_text(
            f"No index found matching <b>{raw}</b>. Try <code>/sectors</code> for the list.",
            parse_mode="HTML",
        )
        return
    await update.message.reply_text(_format_index_message(name, sig), parse_mode="HTML")


def _resolve_index_signal(raw: str) -> tuple:
    """Fuzzy match the user's input to an actual index_name, return latest signal."""
    with get_conn() as conn:
        # Try exact match first
        row = conn.execute(
            """SELECT * FROM index_signals
               WHERE UPPER(REPLACE(index_name,' ','')) = REPLACE(?, ' ','')
                 AND trade_date = (SELECT MAX(trade_date) FROM index_signals)""",
            (raw,),
        ).fetchone()
        if not row:
            # Try LIKE
            row = conn.execute(
                """SELECT * FROM index_signals
                   WHERE UPPER(REPLACE(index_name,' ','')) LIKE '%' || REPLACE(?, ' ','') || '%'
                     AND trade_date = (SELECT MAX(trade_date) FROM index_signals)
                   ORDER BY length(index_name) ASC
                   LIMIT 1""",
                (raw,),
            ).fetchone()
        if not row:
            return None, None
        return row["index_name"], dict(row)


def _format_index_message(name: str, sig: dict) -> str:
    state = sig.get("rs_vs_broad_trend_state") or "—"
    emoji = _TREND_EMOJI.get(state, "—")
    lines = [
        f"<b>📊 {name} — {sig['trade_date']}</b>",
        f"Close: <b>{sig['close_value']:,.2f}</b>",
        "",
        "<b>Returns:</b>",
        "<pre>",
        f"  1d  {_fmt_pct(sig['ret_1d_pct'])}   "
        f"1w  {_fmt_pct(sig['ret_1w_pct'])}   "
        f"1m  {_fmt_pct(sig['ret_1m_pct'])}",
        f"  3m  {_fmt_pct(sig['ret_3m_pct'])}   "
        f"6m  {_fmt_pct(sig['ret_6m_pct'])}   "
        f"12m {_fmt_pct(sig['ret_12m_pct'])}",
        "</pre>",
        "<b>Trend (level):</b>",
        "<pre>",
        f"  vs 50d MA   {_fmt_pct(sig['pct_above_50d_avg'])}",
        f"  vs 200d MA  {_fmt_pct(sig['pct_above_200d_avg'])}",
        f"  off 52w hi  {_fmt_pct(sig['pct_off_52w_high'])}",
        f"  off 52w lo  {_fmt_pct(sig['pct_above_52w_low'])}",
        "</pre>",
    ]
    if sig.get("broad_benchmark"):
        lines += [
            f"<b>Relative strength vs {sig['broad_benchmark']}:</b>",
            f"  {emoji} <b>{state}</b>",
            "<pre>",
            f"  ratio today   {sig.get('rs_vs_broad_today') or 0:.4f}",
            f"  slope 1m  {_fmt_pct(sig.get('rs_vs_broad_slope_1m'))}",
            f"  slope 3m  {_fmt_pct(sig.get('rs_vs_broad_slope_3m'))}",
            f"  slope 6m  {_fmt_pct(sig.get('rs_vs_broad_slope_6m'))}",
            f"  slope 12m {_fmt_pct(sig.get('rs_vs_broad_slope_12m'))}",
            f"  > 50ma  {'✓' if sig.get('rs_vs_broad_above_50ma') else '✗'}   "
            f"> 200ma {'✓' if sig.get('rs_vs_broad_above_200ma') else '✗'}   "
            f"new 52w high {'⚡' if sig.get('rs_vs_broad_new_52w_high') else '—'}",
            "</pre>",
        ]
    pe = sig.get("pe")
    pb = sig.get("pb")
    dy = sig.get("dividend_yield")
    if pe or pb or dy:
        lines.append("<b>Valuation:</b>")
        lines.append(f"  PE {pe or '—'} · PB {pb or '—'} · Div Yield {dy or '—'}%")
    return "\n".join(lines)


async def on_sectors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Compact sector dashboard ordered by RS vs broad trend (D32)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, _fetch_sector_dashboard)
    if not rows:
        await update.message.reply_text("No index signals computed yet.")
        return
    await update.message.reply_text(_format_sectors_message(rows), parse_mode="HTML")


_TREND_ORDER_CASE = (
    "CASE rs_vs_broad_trend_state "
    "WHEN 'BREAKOUT' THEN 0 WHEN 'UPTREND' THEN 1 "
    "WHEN 'CONSOLIDATING' THEN 2 WHEN 'DOWNTREND' THEN 3 "
    "WHEN 'BREAKDOWN' THEN 4 ELSE 5 END"
)


def _fetch_sector_dashboard() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT index_name, trade_date, ret_1m_pct, ret_3m_pct, ret_12m_pct,
                       rs_vs_broad_slope_1m, rs_vs_broad_slope_3m,
                       rs_vs_broad_trend_state, broad_benchmark
                FROM index_signals
                WHERE trade_date = (SELECT MAX(trade_date) FROM index_signals)
                  AND broad_benchmark IS NOT NULL
                ORDER BY {_TREND_ORDER_CASE} ASC,
                         COALESCE(rs_vs_broad_slope_3m, -999) DESC""",
        ).fetchall()
    return [dict(r) for r in rows]


def _format_sectors_message(rows: list[dict]) -> str:
    trade_date = rows[0]["trade_date"]
    lines = [
        f"<b>🔁 Sector rotation — {trade_date}</b>",
        f"<i>vs {rows[0].get('broad_benchmark', 'broad')}. "
        "Sorted: BREAKOUT → UPTREND → CONSOL → DOWNTREND → BREAKDOWN, "
        "then by 3m RS slope.</i>",
        "",
        "<pre>",
        f"{'Index':<22}{'State':>10}{'rs1m':>8}{'rs3m':>8}{'ret3m':>8}",
    ]
    for r in rows:
        nm = (r["index_name"] or "")[:22]
        state = r.get("rs_vs_broad_trend_state") or "—"
        emoji_state = f"{_TREND_EMOJI.get(state, '—')}{state[:5]}"
        lines.append(
            f"{nm:<22}{emoji_state:>10}"
            f"{_fmt_pct(r.get('rs_vs_broad_slope_1m')):>8}"
            f"{_fmt_pct(r.get('rs_vs_broad_slope_3m')):>8}"
            f"{_fmt_pct(r.get('ret_3m_pct')):>8}"
        )
    lines.append("</pre>")
    lines.append("")
    lines.append("<i>Drill in: <b>/index NAME</b> or <b>/ratio NAME NIFTY 500</b>.</i>")
    return "\n".join(lines)


async def on_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show one ratio time series with trend reads (D32).

    Usage: /ratio NUMERATOR DENOMINATOR
           /ratio NIFTYBANK NIFTY 50
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: <code>/ratio NUM DEN</code> — "
            "e.g. <code>/ratio NIFTYBANK NIFTY 50</code>",
            parse_mode="HTML",
        )
        return
    # First token is numerator; the rest is the denominator (may have spaces)
    args = [a for a in context.args if a]
    num_raw = args[0].upper().strip()
    den_raw = " ".join(args[1:]).upper().strip()

    loop = asyncio.get_running_loop()
    pair = await loop.run_in_executor(None, lambda: _resolve_ratio_pair(num_raw, den_raw))
    if not pair:
        await update.message.reply_text(
            f"No ratio data for <b>{num_raw}</b> / <b>{den_raw}</b>. "
            "Both names need to be in index_signals — try <code>/sectors</code>.",
            parse_mode="HTML",
        )
        return
    num_name, den_name, sig, hist = pair
    await update.message.reply_text(
        _format_ratio_message(num_name, den_name, sig, hist), parse_mode="HTML"
    )


def _match_index(raw: str):
    """Fuzzy-match raw user input to an actual index_name."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT index_name FROM index_signals
               WHERE UPPER(REPLACE(index_name,' ','')) = REPLACE(?, ' ','')
               ORDER BY trade_date DESC LIMIT 1""",
            (raw,),
        ).fetchone()
        if row:
            return row["index_name"]
        row = conn.execute(
            """SELECT index_name FROM index_signals
               WHERE UPPER(REPLACE(index_name,' ','')) LIKE '%' || REPLACE(?, ' ','') || '%'
               ORDER BY length(index_name) ASC, trade_date DESC LIMIT 1""",
            (raw,),
        ).fetchone()
        return row["index_name"] if row else None


def _resolve_ratio_pair(num_raw: str, den_raw: str):
    num = _match_index(num_raw)
    den = _match_index(den_raw)
    if not num or not den:
        return None
    with get_conn() as conn:
        sig = conn.execute(
            """SELECT * FROM ratio_signals
               WHERE numerator = ? AND denominator = ?
               ORDER BY trade_date DESC LIMIT 1""",
            (num, den),
        ).fetchone()
        if not sig:
            return None
        hist = conn.execute(
            """SELECT trade_date, ratio FROM ratio_rows
               WHERE numerator = ? AND denominator = ?
               ORDER BY trade_date DESC LIMIT 30""",
            (num, den),
        ).fetchall()
    return num, den, dict(sig), [dict(r) for r in hist]


def _format_ratio_message(num: str, den: str, sig: dict, hist: list[dict]) -> str:
    state = sig.get("trend_state") or "—"
    emoji = _TREND_EMOJI.get(state, "—")
    lines = [
        f"<b>⚖️ {num} / {den} — {sig['trade_date']}</b>",
        f"  {emoji} <b>{state}</b>",
        "",
        "<pre>",
        f"  ratio today     {sig['ratio']:.4f}",
        f"  20d MA          {sig.get('ratio_ma_20') or 0:.4f}",
        f"  50d MA          {sig.get('ratio_ma_50') or 0:.4f}",
        f"  200d MA         {sig.get('ratio_ma_200') or 0:.4f}",
        f"  52w high        {sig.get('ratio_high_52w') or 0:.4f}",
        f"  52w low         {sig.get('ratio_low_52w') or 0:.4f}",
        f"  off 52w high    {_fmt_pct(sig.get('pct_below_52w_high'))}",
        f"  slope 1m  {_fmt_pct(sig.get('slope_1m_pct'))}    "
        f"3m  {_fmt_pct(sig.get('slope_3m_pct'))}",
        f"  slope 6m  {_fmt_pct(sig.get('slope_6m_pct'))}    "
        f"12m {_fmt_pct(sig.get('slope_12m_pct'))}",
        f"  > 50ma  {'✓' if sig.get('above_50_ma') else '✗'}   "
        f"> 200ma {'✓' if sig.get('above_200_ma') else '✗'}",
        f"  cross 50 today  {'⚡' if sig.get('cross_50_today') else '—'}    "
        f"cross 200 {'⚡' if sig.get('cross_200_today') else '—'}",
        f"  new 50d high    {'⚡' if sig.get('new_50d_high') else '—'}    "
        f"new 200d {'⚡' if sig.get('new_200d_high') else '—'}    "
        f"new 52w {'⚡' if sig.get('new_52w_high') else '—'}",
        "</pre>",
        "",
        f"<b>Last {len(hist)} days (newest first):</b>",
        "<pre>",
        f"{'Date':<12}{'Ratio':>12}",
    ]
    for r in hist:
        lines.append(f"{r['trade_date']:<12}{r['ratio']:>12.4f}")
    lines.append("</pre>")
    return "\n".join(lines)


async def on_breakouts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sector ratios breaking out today (D32)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None,
        lambda: _fetch_trend_filter(("BREAKOUT", "UPTREND"), limit=30, ascending=False)
    )
    if not rows:
        await update.message.reply_text(
            "No sector ratios in BREAKOUT or UPTREND right now. "
            "Try <code>/rotation</code> for the full picture.",
            parse_mode="HTML",
        )
        return
    await update.message.reply_text(
        _format_breakouts_message(rows, kind="breakouts"), parse_mode="HTML"
    )


async def on_breakdowns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sector ratios breaking down today (D32)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None,
        lambda: _fetch_trend_filter(("BREAKDOWN", "DOWNTREND"), limit=30, ascending=True)
    )
    if not rows:
        await update.message.reply_text(
            "No sector ratios in BREAKDOWN or DOWNTREND right now.",
        )
        return
    await update.message.reply_text(
        _format_breakouts_message(rows, kind="breakdowns"), parse_mode="HTML"
    )


def _fetch_trend_filter(states: tuple, limit: int, ascending: bool) -> list[dict]:
    direction = "ASC" if ascending else "DESC"
    placeholders = ",".join("?" * len(states))
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT numerator, denominator, trade_date, ratio,
                       trend_state, slope_1m_pct, slope_3m_pct,
                       new_52w_high, new_200d_high, new_50d_high
                FROM ratio_signals
                WHERE trade_date = (SELECT MAX(trade_date) FROM ratio_signals)
                  AND trend_state IN ({placeholders})
                ORDER BY slope_3m_pct {direction}
                LIMIT ?""",
            (*states, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _format_breakouts_message(rows: list[dict], kind: str) -> str:
    trade_date = rows[0]["trade_date"]
    title = "⚡ Ratio breakouts" if kind == "breakouts" else "⬇️ Ratio breakdowns"
    lines = [
        f"<b>{title} — {trade_date}</b>",
        "<i>Sector vs broad-index ratio. ⚡ on row = new 52w/200d/50d high.</i>",
        "",
        "<pre>",
        f"{'Num / Den':<26}{'State':>8}{'rs1m':>8}{'rs3m':>8}{'New':>5}",
    ]
    for r in rows:
        pair = f"{r['numerator'][:14]}/{r['denominator'][:10]}"[:26]
        state = r["trend_state"][:7]
        flag = "52w" if r.get("new_52w_high") else (
               "200d" if r.get("new_200d_high") else (
               "50d" if r.get("new_50d_high") else "—"))
        lines.append(
            f"{pair:<26}{state:>8}"
            f"{_fmt_pct(r.get('slope_1m_pct')):>8}"
            f"{_fmt_pct(r.get('slope_3m_pct')):>8}{flag:>5}"
        )
    lines.append("</pre>")
    lines.append("")
    lines.append("<i>Drill in: <b>/ratio NUM DEN</b>.</i>")
    return "\n".join(lines)


async def on_rotation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias for /sectors — common phrasing 'sector rotation'."""
    await on_sectors(update, context)


# --- D33c: stock RS + composite leaders / laggards ------------------------

_UP_STATES = {"UPTREND", "BREAKOUT"}
_DOWN_STATES = {"DOWNTREND", "BREAKDOWN"}


def _fetch_stock_rs(symbol: str):
    """Latest stock_signals RS read for one symbol + its sector's own RS-vs-broad
    (D32 index_signals), for the composite verdict. None if no signals row."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT s.symbol, s.trade_date, s.rs_rank, s.primary_sector,
                      s.rs_vs_broad_trend_state  bstate,
                      s.rs_vs_broad_slope_1m b1, s.rs_vs_broad_slope_3m b3,
                      s.rs_vs_broad_slope_6m b6, s.rs_vs_broad_slope_12m b12,
                      s.rs_vs_sector_trend_state sstate,
                      s.rs_vs_sector_slope_1m x1, s.rs_vs_sector_slope_3m x3,
                      s.rs_vs_sector_slope_6m x6, s.rs_vs_sector_slope_12m x12
               FROM stock_signals s
               WHERE s.symbol = ?
               ORDER BY s.trade_date DESC LIMIT 1""",
            (symbol,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["sector_broad_state"] = None
        if d.get("primary_sector"):
            irow = conn.execute(
                """SELECT rs_vs_broad_trend_state st FROM index_signals
                   WHERE index_name=? ORDER BY trade_date DESC LIMIT 1""",
                (d["primary_sector"],),
            ).fetchone()
            if irow:
                d["sector_broad_state"] = irow["st"]
    return d


def _format_stock_rs_message(d: dict) -> str:
    sym = d["symbol"]
    rank = d.get("rs_rank")
    bstate = d.get("bstate") or "—"
    sstate = d.get("sstate") or "—"
    sec = d.get("primary_sector")
    secst = d.get("sector_broad_state") or "—"
    if sec and bstate in _UP_STATES and sstate in _UP_STATES and secst in _UP_STATES:
        verdict = "🟢 <b>LEADER</b> — strong-in-strong (stock + sector + market all up)"
    elif sec and bstate in _DOWN_STATES and sstate in _DOWN_STATES and secst in _DOWN_STATES:
        verdict = "🔴 <b>LAGGARD</b> — weak-in-weak (stock + sector + market all down)"
    else:
        verdict = "⚪ mixed — not a clean leader/laggard"
    rank_txt = (f"{rank} / 99 (stronger than {rank}% of the market)"
                if rank is not None else "— (outside liquid universe / short history)")
    lines = [
        f"<b>📊 {sym} — Relative Strength</b> <i>({d.get('trade_date','')})</i>",
        "",
        f"<b>vs broad (Nifty 500):</b> {_TREND_EMOJI.get(d.get('bstate'), '—')}{bstate}",
        f"  RS rank: {rank_txt}",
        f"  slope 1m/3m/6m/12m: {_fmt_pct(d.get('b1'))} / {_fmt_pct(d.get('b3'))} / "
        f"{_fmt_pct(d.get('b6'))} / {_fmt_pct(d.get('b12'))}",
        "",
    ]
    if sec:
        lines += [
            f"<b>vs sector ({sec}):</b> {_TREND_EMOJI.get(d.get('sstate'), '—')}{sstate}",
            f"  slope 1m/3m/6m/12m: {_fmt_pct(d.get('x1'))} / {_fmt_pct(d.get('x3'))} / "
            f"{_fmt_pct(d.get('x6'))} / {_fmt_pct(d.get('x12'))}",
            f"  sector vs broad: {_TREND_EMOJI.get(d.get('sector_broad_state'), '—')}{secst}",
            "",
        ]
    else:
        lines += ["<i>No NSE sectoral index covers this stock — broad RS only.</i>", ""]
    lines.append(verdict)
    return "\n".join(lines)


async def on_rs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Per-stock Relative Strength — vs broad + vs sector + leader/laggard verdict (D33)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/rs TICKER</code> — e.g. <code>/rs HDFCBANK</code>",
            parse_mode="HTML")
        return
    sym = context.args[0].upper().strip()
    loop = asyncio.get_running_loop()
    d = await loop.run_in_executor(None, lambda: _fetch_stock_rs(sym))
    if not d or (d.get("bstate") is None and d.get("rs_rank") is None):
        await update.message.reply_text(
            f"No RS computed for <b>{sym}</b>. Check the ticker, or it may be "
            "outside the covered universe.", parse_mode="HTML")
        return
    await update.message.reply_text(_format_stock_rs_message(d), parse_mode="HTML")


def _format_leaders_message(rows: list[dict], kind: str) -> str:
    if kind == "leaders":
        title, order = "🟢 Leaders — strong-in-strong", "Strongest first."
        sub = "Stock + its sector + the market all trending up (RS)."
    else:
        title, order = "🔴 Laggards — weak-in-weak", "Weakest first."
        sub = "Stock + its sector + the market all trending down (RS)."
    lines = [f"<b>{title}</b>", f"<i>{sub} {order}</i>", "", "<pre>",
             f"{'Sym':<13}{'RS':>4}  {'Sector':<22}"]
    for r in rows:
        rk = r["rs_rank"]
        lines.append(f"{(r['symbol'] or '')[:13]:<13}"
                     f"{(str(rk) if rk is not None else '—'):>4}  "
                     f"{(r['primary_sector'] or '')[:22]:<22}")
    lines += ["</pre>", "", "<i>Drill in: <b>/rs TICKER</b>.</i>"]
    return "\n".join(lines)


async def on_leaders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Composite 'strong-in-strong' leaders (D33c)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    from src.automation.stock_rs import leaders_laggards
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, lambda: leaders_laggards("leaders", limit=30))
    if not rows:
        await update.message.reply_text(
            "No strong-in-strong leaders right now — no stock has all three RS "
            "layers aligned up.")
        return
    await update.message.reply_text(_format_leaders_message(rows, "leaders"), parse_mode="HTML")


async def on_laggards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Composite 'weak-in-weak' laggards (D33c)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    from src.automation.stock_rs import leaders_laggards
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, lambda: leaders_laggards("laggards", limit=30))
    if not rows:
        await update.message.reply_text("No weak-in-weak laggards right now.")
        return
    await update.message.reply_text(_format_leaders_message(rows, "laggards"), parse_mode="HTML")


async def on_conviction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """D45 — the cross-pillar Conviction shortlist (all 3 pillars aligned)."""
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return
    from src.automation.stock_rs import conviction_shortlist
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, lambda: conviction_shortlist(limit=30))
    if not rows:
        await update.message.reply_text(
            "No names clear all three pillars right now — that's normal; conviction is rare. "
            "Try <code>/leaders</code> or <code>/scan</code>.", parse_mode="HTML")
        return
    await update.message.reply_text(_format_conviction_message(rows), parse_mode="HTML")


def _format_conviction_message(rows: list[dict]) -> str:
    """One line per name: RS leader + accumulating + entry, pt14 quality starred.
    Same shared `conviction_shortlist` helper as the dashboard (DRY)."""
    lines = [
        "<b>⭐ Conviction shortlist</b>",
        "<i>All 3 pillars aligned — RS leader + institutions accumulating now (D43) + "
        "entry read (D44). 🎯 near key price · ★ pt14 quality-confirmed.</i>",
        "",
    ]
    for r in rows:
        sym = r["symbol"]
        rk = r.get("rs_rank")
        nk = (is_near_key(r.get("gap_to_key_p3m")) or is_near_key(r.get("gap_to_key_p6m"))
              or is_near_key(r.get("gap_to_key_p12m")))
        pvh = r.get("pvh")
        if nk:
            ent = "🎯 near key"
        elif pvh is not None and pvh < -3:
            ent = "🟢 discount"
        elif pvh is not None and pvh > 3:
            ent = "🔴 extended"
        else:
            ent = "🟡 at-cost"
        star = "★ " if (r.get("pt14_tier") and not r.get("pt14_dq")) else ""
        sec = r.get("primary_sector") or "—"
        rks = f"rank {rk}" if rk is not None else "rank —"
        lines.append(f"{star}<b>{sym}</b> — {rks} · {ent} · <i>{sec}</i>")
    lines.append("")
    lines.append("<i>Full sortable view + key prices: /dash/conviction on the dashboard.</i>")
    return "\n".join(lines)


# --- Two-tier scan + layered triggers (D28) -------------------------------

# Shared symbol/liquidity filters (D23).
_SCAN_FILTERS_SQL = """
                 AND b.series = 'EQ'
                 AND (b.segment = 'CM' OR b.segment IS NULL)
                 AND b.value > 10000000
                 AND b.close > 20
                 AND s.symbol IN (SELECT symbol FROM nse_equity_list)
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
                       s.accum_character,
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
    ch = _char_marker(r.get("accum_character"))
    return f"{sym:<10}{rank:>6}{rp:>6}{close:>8}{pvh_s:>7}{en:>3} {ch:<2}{near_s:<10}"


_ROW_HEADER = f"{'Symbol':<10}{'Rank':>6}{'r/p':>6}{'Close':>8}{'Δhot%':>7}{'En':>3} {'Ch':<2}Near-P"


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
        "Ch = character 🟢accum 🔴distrib 🟡consol ⚪neutral. "
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
        "About-to-break: <b>/triggers near</b>. "
        "Character: <b>/triggers accum</b> · <b>/triggers distrib</b>.</i>"
    )
    return "\n".join(lines)


async def on_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Strict layered triggers across the market (D28 + D43).

    /triggers         -> rank A or better (p_score >= 3)
    /triggers ss      -> SS only (p_score = 5)
    /triggers near    -> near-break candidates: gap_to_next_p_pct > -10% AND r_score >= 4
    /triggers accum   -> ACCUMULATION character + p_score >= 3 + concentrated (D43)
    /triggers distrib -> DISTRIBUTION character (D43)
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return

    mode = (context.args[0].lower() if context.args else "").strip()
    if mode in ("ss", "supreme"):
        kind = "ss"; label = "SS only"
    elif mode in ("near", "near-break", "kissing"):
        kind = "near"; label = "near-break candidates"
    elif mode in ("accum", "accumulation", "stealth"):
        kind = "accum"; label = "accumulation character (concentrated)"
    elif mode in ("distrib", "distribution", "distro"):
        kind = "distrib"; label = "distribution character ⚠️"
    else:
        kind = "default"; label = "rank A+ (p_score ≥ 3)"

    await update.message.reply_text(f"🔎 Searching: {label}…")

    loop = asyncio.get_running_loop()
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
      'accum'   -> accum_character = 'ACCUMULATION' AND p_score >= 3 AND concentrated
      'distrib' -> accum_character = 'DISTRIBUTION'
      'default' -> p_score >= 3 (rank A or better)
    """
    if kind == "ss":
        extra_where = "AND s.p_score = 5"
    elif kind == "near":
        extra_where = ("AND s.next_p_above IS NOT NULL "
                       "AND s.gap_to_next_p_pct > -10 "
                       "AND COALESCE(s.r_score, 0) >= 4")
    elif kind == "accum":
        extra_where = ("AND s.accum_character = 'ACCUMULATION' "
                       "AND s.p_score >= 3 "
                       "AND COALESCE(s.trade_count_ratio_1m_6m, 99) <= 1.1")
    elif kind == "distrib":
        extra_where = "AND s.accum_character = 'DISTRIBUTION'"
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
                       s.accum_character,
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
        "Ch = character 🟢accum 🔴distrib 🟡consol ⚪neutral. "
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


async def _handle_inbox_ask(update: Update, text: str) -> bool:
    """"what's waiting on me?" etc, answered directly on the phone (S160-b).

    Pat's /dash/pat web form already had this (S160); Telegram did not, because plain
    text falls through the paid SCORE/FLOW/BOTH/SCAN classifier straight to the general
    assistant, which has no idea what the review inbox is. parse_inbox() is a regex — no
    LLM, no cost — so every message can be checked here for free before that classifier
    ever runs. READ-ONLY: this reports the queue, it never decides anything (judging
    stays on the owner-gated /dash/inbox lens). Single-sourced with the DM and the web
    form via inbox_flow.waiting()/format_telegram_reply(), so no channel can disagree.
    Returns True if it answered (caller must return without falling through further).
    """
    from src.pat import inbox_flow as IF
    if IF.parse_inbox(text) is None:
        return False
    loop = asyncio.get_running_loop()

    def _read():
        with get_conn() as conn:
            return IF.waiting(conn)

    w = await loop.run_in_executor(None, _read)
    await update.message.reply_text(
        IF.format_telegram_reply(w), parse_mode="HTML", disable_web_page_preview=True)
    return True


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

    loop = asyncio.get_running_loop()

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


async def on_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/inbox — what is waiting on YOUR judgment, asked any time (S161, Ramana-directed).

    The completion of "communication belongs in the chat": S160 gave Pat the answer and the
    morning DM the count, but the bot — the surface he actually types into — still could not
    say what was waiting. Now it can, on demand rather than once a day.

    The explicit-command sibling of S160-b's natural-language pre-pass (_handle_inbox_ask):
    that catches "what's waiting on me?" typed as plain text; this is the discoverable
    slash command (it shows in the / list) and adds a kind filter. BOTH render through the
    SAME inbox_flow.format_telegram_reply(), so the command, the free-text ask, the DM and
    the /dash/pat web form describe one queue and can never disagree. READ-ONLY: it REPORTS
    the queue; approving/rejecting stays a deliberate act on the owner-gated lens.

    /inbox          -> the whole queue (identical to the free-text answer)
    /inbox briefs   -> filter to one kind (briefs | rule | tags | alerts | ...)
    """
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        return                      # the queue is owner-private; the ID gate IS the guard

    want = (context.args[0].lower().strip() if context.args else "")

    def _read():
        from src.pat.inbox_flow import waiting
        with get_conn() as conn:
            return waiting(conn)

    loop = asyncio.get_running_loop()
    try:
        w = await loop.run_in_executor(None, _read)
    except Exception:                                   # a chat reply must never crash
        log.exception("/inbox read failed")
        await update.message.reply_text(
            "Couldn't read the review queue just now — try again in a moment.")
        return

    from src.pat import inbox_flow as IF
    if want:
        # /inbox <kind> — narrow to one kind, but keep a COHERENT w (its own total +
        # by_kind) so the shared formatter's header/counts stay honest, then render
        # through the exact same path as the unfiltered answer (single source).
        alias = {"brief": "brief", "briefs": "brief", "rule": "rule_verdict",
                 "rules": "rule_verdict", "verdict": "rule_verdict",
                 "verdicts": "rule_verdict", "tag": "tags", "tags": "tags",
                 "alert": "alert-ack", "alerts": "alert-ack",
                 "rebalance": "rebalance", "anomaly": "anomaly"}.get(want, want)
        n = next((b["n"] for b in w["by_kind"] if b["kind"] == alias), 0)
        if not n:
            await update.message.reply_text(
                f'Nothing waiting under <code>{_html.escape(want)}</code>. '
                f'<b>{_html.escape(IF.summary_phrase(w).capitalize())}.</b>',
                parse_mode="HTML", disable_web_page_preview=True)
            return
        w = {"total": n, "link": w["link"],
             "by_kind": [b for b in w["by_kind"] if b["kind"] == alias],
             "items": [i for i in w["items"] if i.get("kind") == alias]}

    await update.message.reply_text(
        IF.format_telegram_reply(w), parse_mode="HTML", disable_web_page_preview=True)


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
    loop = asyncio.get_running_loop()
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
    loop = asyncio.get_running_loop()
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
    loop = asyncio.get_running_loop()

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

    # --- "what's waiting on me?" (S160-b) — a free, deterministic pre-pass, same shape
    # as the menu-pending short-circuit above. MUST run before _intent.classify(): that
    # classifier only recognizes stock lookups (SCORE/FLOW/BOTH/SCAN), so an inbox ask
    # fell through to the general assistant below, which has no idea what the review
    # inbox is (verified live — a generic "I don't have access to your calendar" reply).
    # parse_inbox() is a regex, not an LLM call, so this costs nothing to check on every
    # message and never delays a real stock question.
    if await _handle_inbox_ask(update, text):
        return

    # --- Natural-language intent routing ---
    # Plain English maps to /pt14, /dvpt or both without the user typing slashes.
    from src.assistant import intent as _intent
    loop = asyncio.get_running_loop()
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
    loop = asyncio.get_running_loop()
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
    BotCommand("triggers",      "Strict layered triggers: A+, SS, near-break, accum or distrib (FREE, /triggers [ss|near|accum|distrib])"),
    BotCommand("index",         "Index level + technicals + RS vs broad (D32, /index NIFTYBANK)"),
    BotCommand("sectors",       "Sector rotation dashboard — all sectoral RS vs Nifty 500 (D32)"),
    BotCommand("rotation",      "Alias of /sectors — same view"),
    BotCommand("ratio",         "Ratio chart between two indexes (D32, /ratio NIFTYBANK NIFTY 50)"),
    BotCommand("breakouts",     "Sectoral ratios breaking out / in uptrend vs broad (D32)"),
    BotCommand("breakdowns",    "Sectoral ratios breaking down / in downtrend vs broad (D32)"),
    BotCommand("rs",            "Stock relative strength — vs broad + sector + leader/laggard verdict (/rs TICKER)"),
    BotCommand("leaders",       "Strong-in-strong leaders — stock + sector + market all up (D33c)"),
    BotCommand("laggards",      "Weak-in-weak laggards — stock + sector + market all down (D33c)"),
    BotCommand("conviction",    "⭐ Conviction shortlist — all 3 pillars aligned: RS leader + accumulating + entry (D45)"),
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
    BotCommand("inbox",         "What's waiting on your judgment — briefs, verdicts, tags (owner-only; /inbox briefs to filter)"),
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
    app.add_handler(CommandHandler("inbox", on_inbox))
    app.add_handler(CommandHandler("reset", on_reset))
    app.add_handler(CommandHandler("pt14", on_pt14))
    app.add_handler(CommandHandler("dvpt", on_dvpt))
    app.add_handler(CommandHandler("scan", on_scan))
    app.add_handler(CommandHandler("triggers", on_triggers))
    app.add_handler(CommandHandler("index", on_index))
    app.add_handler(CommandHandler("sectors", on_sectors))
    app.add_handler(CommandHandler("rotation", on_rotation))
    app.add_handler(CommandHandler("ratio", on_ratio))
    app.add_handler(CommandHandler("breakouts", on_breakouts))
    app.add_handler(CommandHandler("breakdowns", on_breakdowns))
    app.add_handler(CommandHandler("rs", on_rs))
    app.add_handler(CommandHandler("leaders", on_leaders))
    app.add_handler(CommandHandler("laggards", on_laggards))
    app.add_handler(CommandHandler("conviction", on_conviction))
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
