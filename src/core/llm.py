from anthropic import Anthropic

from src.core.settings import settings

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def first_text(response, default: str = "") -> str:
    """Return the first text block of a Messages response, or `default`.

    `response.content[0].text` assumes the first block is text, which raises on a
    tool_use / empty / refusal content array (CL-SYS-06). Scan for the first block
    that actually carries text instead, so scheduled/non-interactive callers never
    crash on a non-text stop.
    """
    try:
        for block in getattr(response, "content", None) or []:
            txt = getattr(block, "text", None)
            if isinstance(txt, str) and txt:
                return txt
    except Exception:
        pass
    return default


def ask(prompt: str, *, fast: bool = True, system: str | None = None) -> str:
    """One-shot text-in/text-out helper.

    CL-SYS-03: defaults to the cheap Haiku tier (`fast=True`) per the cost doctrine
    (≤ ~Rs300/mo; cheap models in any non-user-initiated path). The premium Sonnet
    tier is opt-in only — pass `fast=False` explicitly on a user-initiated path where
    Ramana wants Sonnet-grade reasoning. (`settings.default_model` is the *named*
    Sonnet tier identifier used by those explicit opt-ins; it is intentionally NOT
    changed — flipping it would silently downgrade the explicit Sonnet paths.)"""
    model = settings.fast_model if fast else settings.default_model
    response = client().messages.create(
        model=model,
        max_tokens=1024,
        system=system or "You are Hermes, a helpful personal AI agent.",
        messages=[{"role": "user", "content": prompt}],
    )
    return first_text(response)
