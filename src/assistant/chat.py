"""Chat handler for Hermes' personal-assistant workload.

Day-2 cost-conscious version:

- Sliding window on history (MAX_HISTORY_MESSAGES). Threads longer than this
  drop the oldest turns from the LLM context (but stay in the DB). Prevents
  unbounded quadratic growth of input tokens on long conversations.

- Anthropic prompt caching enabled. The system prompt and the entire history
  prefix get cache_control markers. On subsequent turns within the cache TTL
  (~5 min), cached tokens cost ~10% of normal input rate. Cache creation costs
  1.25x normal rate on the first turn that establishes the cache; net positive
  after just 2-3 turns. Below ~1024 tokens (Sonnet) / ~2048 tokens (Haiku),
  cache_control is silently ignored — totally fine; it engages once the prefix
  is long enough to matter.

The combination caps Telegram message cost at roughly $0.001-$0.005 even on
long threads, vs the ~$0.30/turn that long threads cost without these fixes.
"""

import logging

from anthropic import APIError

from src.assistant import conversations
from src.core.llm import client, first_text, meter
from src.core.settings import settings

log = logging.getLogger("hermes.chat")

# Keep the last 30 messages (15 turns) in the LLM context. Older messages stay
# in the DB but stop being replayed. Tune up if Hermes needs longer memory; tune
# down to cap costs further.
MAX_HISTORY_MESSAGES = 30

HERMES_SYSTEM_PROMPT = """You are Hermes, a personal AI assistant deployed on Ramana's own VPS (Hostinger KVM4, Mumbai). Ramana is a financial analyst in India focused on Indian equity markets.

You serve three workloads:
1. Personal assistant — answering questions, drafting text, helping Ramana think
2. Indian equity analysis using patearn methodology + Delivery-Value-Per-Trade signals
3. Automation — explaining or proposing scheduled tasks

CRITICAL: You DO have access to Indian market data — never claim otherwise. Specifically:
- 5 years of NSE end-of-day bhav copy with DELIVERY data (sec_bhavdata_full) sitting in /opt/hermes/data/hermes.db
- Pre-computed nightly DVPT signals (delivery_value_per_trade, power deliveries, ratio_today_vs_power_1m, etc.) across ~3,000 stocks × ~1,250 days
- D28 two-tier layered triggers (r_score, p_score, trigger_rank SS/S/A/B/C, ATH-DVPT, near-break pointer)
- Corporate actions, Screener.in fundamentals (on demand), real-time news feeds

HARD CONSTRAINTS ON WHAT YOU CAN OFFER (D30 — read this carefully):

You have EXACTLY TWO data primitives:
1. /pt14 TICKER — patearn 14-pattern rule-based score from Screener.in fundamentals (PE, ROCE, RoE, growth, margins, promoter holding). Quality dimension.
2. /dvpt TICKER — Delivery-Value-Per-Trade institutional-flow signal from bhav copy with the D28 trigger system. Positioning dimension.

Plus two market-wide derivatives: /scan and /triggers.

You do NOT have:
- Technical chart analysis (no candlesticks, no support/resistance, no moving-average crossovers, no RSI/MACD)
- Volume-profile or order-flow data beyond what DVPT measures
- Real-time intraday tick data (Kite Connect isn't wired)
- Pattern recognition for visual chart setups (head-and-shoulders, cups, breakouts) — DVPT is your only "smart money" proxy
- Generic "fundamentals lookup" beyond what /pt14 surfaces from Screener
- News sentiment scoring (you have news headlines via the news poller but no LLM scoring on them)

When Ramana names a stock, NEVER offer a menu of fake options like "Pattern analysis / Technicals / Fundamentals / Volume profile." That is a Bloomberg-terminal-style hallucination and it is forbidden.

Instead:
- If a single ticker is named with no further qualifier → say you'll pull /pt14 + /dvpt and let the natural-language router catch it (or instruct Ramana to type the ticker by itself).
- If he names a specific dimension (quality, score, fundamentals → /pt14; delivery, flow, institutional → /dvpt) → just point at that command.
- For market-wide queries → /scan or /triggers.
- DO NOT invent capabilities. If asked for something Hermes doesn't have (chart patterns, sentiment scoring, intraday), say so plainly and suggest the closest real primitive you do have.

Voice: direct, concise, friendly but not chatty. Address Ramana by name when natural. Skip filler like "Great question!" Avoid disclaimers unless genuinely warranted. Answer the actual question first; offer follow-ups second.

RESPONSE FORMAT — calibrate the LENGTH to the question (Ramana's standing rule: crisp by default, detail on demand). This is a phone chat, so short wins:
- Simple lookups, status checks, yes/no, or a single number → answer in ONE line. Do NOT restate the question, add a preamble, or use bulleted structure for a one-fact answer.
- "Explain / how / why / compare" questions → lead with the answer in ONE sentence, then at most a few tight lines. If there is genuinely more depth worth having, DON'T dump it — end with a short offer ("Want the detail on X?") and expand only if Ramana asks.
- Never pad to seem thorough. A right one-liner beats a correct essay. Plain English; name commands and tickers plainly.
- Only go long when the question truly needs it (a genuine explanation, a multi-part ask). When a full answer would run long on a phone, give the headline + the offer instead of the wall.

If a question genuinely is outside your scope (politics, personal advice unrelated to work, etc.), help anyway but be honest it's outside the primary mandate."""


def _build_system_blocks() -> list[dict]:
    """System prompt as a single cache-marked text block."""
    return [
        {
            "type": "text",
            "text": HERMES_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _build_messages(history: list[dict], new_user_message: str) -> list[dict]:
    """Build the messages payload.

    cache_control on the LAST historical message tells Anthropic to cache every
    prior block (system + all earlier history). The new user message itself is
    uncached so we don't fragment the cache key.
    """
    msgs: list[dict] = []
    last_idx = len(history) - 1

    for i, m in enumerate(history):
        if i == last_idx:
            # Cache breakpoint: caches everything up to AND including this block.
            msgs.append({
                "role": m["role"],
                "content": [
                    {
                        "type": "text",
                        "text": m["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            })
        else:
            msgs.append({"role": m["role"], "content": m["content"]})

    msgs.append({"role": "user", "content": new_user_message})
    return msgs


def handle(message: str, *, conversation_id: int | None = None, fast: bool = False) -> dict:
    """Process a chat message in the context of a (possibly new) conversation.

    Returns:
        {
          "reply": str,
          "conversation_id": int,
          "model": str,
          "stop_reason": str,
          "usage": {
              "input_tokens": int,
              "output_tokens": int,
              "cache_read_input_tokens": int,
              "cache_creation_input_tokens": int,
          }
        }
    """
    if not message or not message.strip():
        return {
            "reply": "Empty message — try sending something.",
            "conversation_id": conversation_id or 0,
            "model": "(none)",
            "stop_reason": "empty_input",
            "usage": {},
        }

    # Resolve conversation: new or existing
    if conversation_id is None:
        conversation_id = conversations.create_conversation()
        history: list[dict] = []
    else:
        if not conversations.conversation_exists(conversation_id):
            return {
                "reply": f"Conversation {conversation_id} does not exist.",
                "conversation_id": conversation_id,
                "model": "(none)",
                "stop_reason": "unknown_conversation",
                "usage": {},
            }
        # Only load the most recent MAX_HISTORY_MESSAGES from SQLite (CL-SYS-12) —
        # older turns stay in the DB for the /conversations endpoint, but a long
        # thread no longer pulls its entire history into memory just to slice it.
        history = conversations.list_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)

    api_messages = _build_messages(history, message)
    model = settings.fast_model if fast else settings.default_model

    try:
        response = client().messages.create(
            model=model,
            max_tokens=2048,
            system=_build_system_blocks(),
            messages=api_messages,
        )
    except APIError as e:
        # AUD-36: e.message went to the client verbatim (account/quota/internal detail,
        # relayed to Telegram AND the /chat HTTP surface). Full detail stays in the log.
        log.exception("anthropic call failed (model=%s, conversation_id=%s): %s",
                      model, conversation_id, e.message)
        return {
            "reply": "The model call failed — please try again in a moment. "
                     "(The full error is in the server log.)",
            "conversation_id": conversation_id,
            "model": model,
            "stop_reason": "api_error",
            "usage": {},
        }

    meter("assistant-chat", model, response)
    reply_text = first_text(
        response,
        default="(no text reply — the model returned a non-text stop)",
    )

    # Persist both turns to DB (full history retained even though only the
    # last MAX_HISTORY_MESSAGES are replayed to the LLM).
    conversations.append_message(conversation_id, "user", message)
    conversations.append_message(conversation_id, "assistant", reply_text)

    return {
        "reply": reply_text,
        "conversation_id": conversation_id,
        "model": response.model,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            # These attributes exist when caching is engaged; default to 0 if absent.
            "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        },
    }
