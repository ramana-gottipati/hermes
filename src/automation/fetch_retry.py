"""Shared throttle/holiday taxonomy for the NSE/BSE archive fetchers (AUD-14).

THE RULE: a transient BLOCK (NSE 403/429/5xx, or a network error) must NEVER be recorded as a
market holiday. Recording a throttle as "no data" silently drops that trading day from the
archive — a permanent 1-day hole that sits below the >4-day freshness alarm and corrupts every
calendar-window signal spanning it (the Mar-2026 corporates-pit class). So a fetcher:

  • RAISES RetryableFetchError on a block/throttle (403/429/5xx/network) → the caller leaves the
    day UN-marked so the next run re-attempts it; and
  • returns None only on a GENUINE no-data response (404 / empty body) = holiday / not-yet-posted.

The pattern originated in fno_oi.py (CL-RS-13); this module centralizes it so all six sibling
fetchers (bhavcopy · indexes · participant_oi · corp_actions · equity_list · deals) share ONE
taxonomy instead of six drifting copies.
"""
from __future__ import annotations

# HTTP statuses that mean "NSE blocked/throttled us / server hiccup", NOT "no data for this date".
RETRYABLE_STATUS = frozenset({403, 429, 500, 502, 503, 504})


class RetryableFetchError(Exception):
    """A transient/blocking fetch failure (NSE 403/429/5xx or a network error) — distinct from a
    genuine 'no data for this date' (holiday / not-yet-posted). The caller must NOT record a
    holiday for this; leave the day un-marked so a later run re-attempts it."""


def raise_if_retryable(status_code: int, url: str) -> None:
    """Raise RetryableFetchError when `status_code` is a block/throttle; no-op otherwise."""
    if status_code in RETRYABLE_STATUS:
        raise RetryableFetchError(f"HTTP {status_code} fetching {url} (blocked/throttled)")
