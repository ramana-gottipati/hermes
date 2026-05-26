from anthropic import Anthropic

from src.core.settings import settings

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def ask(prompt: str, *, fast: bool = False, system: str | None = None) -> str:
    model = settings.fast_model if fast else settings.default_model
    response = client().messages.create(
        model=model,
        max_tokens=1024,
        system=system or "You are Hermes, a helpful personal AI agent.",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
