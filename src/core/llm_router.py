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


def _call_gemini(system: str, user_msg: str, max_tokens: int) -> str:
    """Use Gemini Flash via its OpenAI-compatible endpoint."""
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=6.0,        # bound the worst case so a hung call can't park a
        max_retries=0,      # request thread; caller degrades to its fallback.
    )
    response = client.chat.completions.create(
        model=settings.gemini_classifier_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
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


def active_classifier_provider() -> str:
    """Inspection helper: which provider would a classifier call use right now?"""
    return "gemini" if settings.gemini_api_key else "anthropic"
