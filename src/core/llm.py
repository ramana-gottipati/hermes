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


def meter(job: str, model: str, response, *, note: str | None = None) -> None:
    """Best-effort ₹-meter (D134 §5.4 budget law): append this call's token spend to
    src.automation.cost_ledger. Reads both Anthropic (input_tokens/output_tokens) and
    OpenAI-compatible (prompt_tokens/completion_tokens) usage shapes. Never raises —
    a metering failure must not break the metered call."""
    try:
        u = getattr(response, "usage", None)
        ti = getattr(u, "input_tokens", None)
        if ti is None:
            ti = getattr(u, "prompt_tokens", 0)
        to = getattr(u, "output_tokens", None)
        if to is None:
            to = getattr(u, "completion_tokens", 0)
        from src.automation.cost_ledger import record
        record(job, model, int(ti or 0), int(to or 0), note=note)
    except Exception:  # noqa: BLE001 — metering is strictly best-effort
        pass


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
    meter("core-ask", model, response)
    return first_text(response)
