"""Multi-provider LLM router for cost-conscious classifier calls.

Background:
  Anthropic Haiku 4.5: $1.00 in / $5.00 out per million tokens
  Gemini 2.0 Flash:    $0.075 in / $0.30 out per million tokens  (~13× cheaper)

For pure classification (intent routing, news category tagging) the quality
difference between Haiku and Gemini Flash is negligible. For chat or
patearn analysis the quality difference matters, so those paths stay on
Anthropic.

Routing:
  - If settings.gemini_api_key is set → classifier calls go to Gemini Flash
    via the OpenAI-compatible endpoint (uses openai SDK).
  - If unset → falls back to Anthropic Haiku.
  - On any Gemini failure (rate limit, network, etc.) → automatic fallback
    to Anthropic Haiku so the user never sees a hard failure.

This module is ONLY for classifier-style calls. Chat and /analyze keep using
the src.core.llm.client() Anthropic path directly.
"""

import logging
from typing import Optional

from src.core.settings import settings

log = logging.getLogger("hermes.llm_router")


def call_classifier(
    *,
    system: str,
    user_msg: str,
    max_tokens: int = 200,
) -> tuple[str, str]:
    """Single-shot text-in, text-out call for classification.

    Returns (response_text, provider_used) where provider_used is "gemini" or
    "anthropic". Caller handles JSON parsing or other downstream processing.
    """
    if settings.gemini_api_key:
        try:
            text = _call_gemini(system, user_msg, max_tokens)
            return text, "gemini"
        except Exception as e:
            log.warning(
                "gemini classifier call failed, falling back to anthropic: %s", e
            )

    text = _call_anthropic_haiku(system, user_msg, max_tokens)
    return text, "anthropic"


def _call_gemini(system: str, user_msg: str, max_tokens: int, timeout: float = 6.0,
                 json_mode: bool = False) -> str:
    """Use Gemini Flash via its OpenAI-compatible endpoint.

    timeout defaults to 6s for the tiny classifier path; the extractor passes a
    much larger value since a full-transcript call legitimately takes longer.
    json_mode forces a valid-JSON response (response_format) so a big structured
    extraction can't come back wrapped in prose / markdown fences.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=timeout,    # bound the worst case so a hung call can't park a
        max_retries=0,      # request thread; caller degrades to its fallback.
    )
    extra = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = client.chat.completions.create(
        model=settings.gemini_classifier_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        **extra,
    )
    text = response.choices[0].message.content or ""
    log.debug(
        "gemini call ok: in=%s out=%s",
        getattr(response.usage, "prompt_tokens", None),
        getattr(response.usage, "completion_tokens", None),
    )
    return text


def _call_anthropic_haiku(system: str, user_msg: str, max_tokens: int) -> str:
    """Fallback to Anthropic Haiku."""
    from src.core.llm import client

    response = client().messages.create(
        model=settings.fast_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    log.debug(
        "anthropic call ok: in=%s out=%s",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return response.content[0].text


def call_extractor(
    *,
    system: str,
    user_msg: str,
    max_tokens: int = 8000,
    timeout: float = 90.0,
    allow_anthropic_fallback: bool = False,
    json_mode: bool = True,
) -> tuple[Optional[str], str]:
    """Large structured-extraction call (e.g. a whole concall transcript -> JSON).

    Differs from call_classifier deliberately:
      - much larger max_tokens (a JSON of many guidance items + behavior + flags)
      - a much longer timeout (the input is a full transcript, not a sentence)
      - Gemini-ONLY by default: on failure it returns (None, "failed") rather
        than silently falling back to the ~13x-pricier Haiku and surprising the
        ~Rs300/mo budget on a big call. Set allow_anthropic_fallback=True to opt in.

    Returns (text_or_None, provider) where provider is "gemini" | "anthropic" |
    "failed". The caller marks the row FAIL and retries later on None.
    """
    if settings.gemini_api_key:
        try:
            return _call_gemini(system, user_msg, max_tokens, timeout=timeout, json_mode=json_mode), "gemini"
        except Exception as e:  # noqa: BLE001
            log.warning("gemini extractor call failed: %s", e)
            if not allow_anthropic_fallback:
                return None, "failed"

    # CX-03: Anthropic is the ~13x-pricier path. Only ever reach it when the caller
    # has EXPLICITLY opted in (allow_anthropic_fallback=True). The previous guard only
    # blocked the Anthropic call when a Gemini key WAS configured — so an UNCONFIGURED
    # Gemini key (the common timer/dev posture) silently fell through to Anthropic and
    # spent against the ~Rs300/mo budget. Gate purely on the opt-in flag, key or no key.
    if not allow_anthropic_fallback:
        if not settings.gemini_api_key:
            log.warning("extractor: no GEMINI_API_KEY and anthropic fallback not allowed "
                        "→ no-LLM skip (set GEMINI_API_KEY or pass allow_anthropic_fallback=True)")
        return None, "failed"
    try:
        return _call_anthropic_haiku(system, user_msg, max_tokens), "anthropic"
    except Exception as e:  # noqa: BLE001
        log.warning("anthropic extractor fallback failed: %s", e)
        return None, "failed"


def active_classifier_provider() -> str:
    """Inspection helper: which provider would a classifier call use right now?"""
    return "gemini" if settings.gemini_api_key else "anthropic"
