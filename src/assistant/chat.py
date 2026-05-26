"""Chat handler for Hermes' personal-assistant workload.

Day-1 scope: multi-turn with SQLite-backed history. Each call either starts a
new conversation (no conversation_id supplied) or continues an existing one.
Full history is replayed to Claude on every turn — fine for personal-volume
conversations; cap or summarize later if a single thread grows unbounded.
"""

from anthropic import APIError

from src.assistant import conversations
from src.core.llm import client
from src.core.settings import settings

HERMES_SYSTEM_PROMPT = """You are Hermes, a personal AI assistant deployed on the user's own VPS.

You serve three workloads under one roof:
1. Personal assistant — answering questions, drafting text, helping the user think
2. Automation — explaining or proposing scheduled tasks the user can wire up
3. Trading / finance — discussing markets, instruments, and strategies (NEVER place real orders without explicit confirmation; trading is in paper-mode by default)

Voice: direct, concise, friendly but not chatty. Skip filler like "Great question!" Avoid disclaimers unless genuinely warranted. Answer the actual question first; offer follow-ups second.

If the user asks something outside your three workloads, you can still help — just be honest that it's outside the agent's primary mandate."""


def handle(message: str, *, conversation_id: int | None = None, fast: bool = False) -> dict:
    """Process a chat message in the context of a (possibly new) conversation.

    If conversation_id is None, a new conversation is created and its ID is
    returned. If supplied but unknown, a 'unknown_conversation' stop_reason is
    returned without persisting anything.

    Returns:
        {
          "reply": str,
          "conversation_id": int,
          "model": str,
          "stop_reason": str,
          "usage": {"input_tokens": int, "output_tokens": int}
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
        history = conversations.list_messages(conversation_id)

    # Build the API payload: full history + the new user message
    api_messages = history + [{"role": "user", "content": message}]
    model = settings.fast_model if fast else settings.default_model

    try:
        response = client().messages.create(
            model=model,
            max_tokens=2048,
            system=HERMES_SYSTEM_PROMPT,
            messages=api_messages,
        )
    except APIError as e:
        return {
            "reply": f"LLM call failed: {e.message}",
            "conversation_id": conversation_id,
            "model": model,
            "stop_reason": "api_error",
            "usage": {},
        }

    reply_text = response.content[0].text

    # Persist both turns
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
        },
    }
