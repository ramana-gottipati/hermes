"""Chat handler for Hermes' personal-assistant workload.

Day-0 scope: single-turn, no conversation memory. Each request is independent.
Conversation persistence + multi-turn context comes later (needs a datastore).
"""

from anthropic import APIError

from src.core.llm import client
from src.core.settings import settings

HERMES_SYSTEM_PROMPT = """You are Hermes, a personal AI assistant deployed on the user's own VPS.

You serve three workloads under one roof:
1. Personal assistant — answering questions, drafting text, helping the user think
2. Automation — explaining or proposing scheduled tasks the user can wire up
3. Trading / finance — discussing markets, instruments, and strategies (NEVER place real orders without explicit confirmation; trading is in paper-mode by default)

Voice: direct, concise, friendly but not chatty. Skip filler like "Great question!" Avoid disclaimers unless genuinely warranted. Answer the actual question first; offer follow-ups second.

If the user asks something outside your three workloads, you can still help — just be honest that it's outside the agent's primary mandate."""


def handle(message: str, *, fast: bool = False) -> dict:
    """Process a single chat message and return a structured response.

    Returns: {"reply": str, "model": str, "stop_reason": str, "usage": dict}
    """
    if not message or not message.strip():
        return {
            "reply": "Empty message — try sending something.",
            "model": "(none)",
            "stop_reason": "empty_input",
            "usage": {},
        }

    model = settings.fast_model if fast else settings.default_model

    try:
        response = client().messages.create(
            model=model,
            max_tokens=2048,
            system=HERMES_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
    except APIError as e:
        return {
            "reply": f"LLM call failed: {e.message}",
            "model": model,
            "stop_reason": "api_error",
            "usage": {},
        }

    return {
        "reply": response.content[0].text,
        "model": response.model,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
