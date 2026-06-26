"""Patearn MCP face — face #4 of "one bus, four faces".

An LLM tool layer over `/v1`: a CLOSED vocabulary of tools (typed/enum args) that the model
chooses among and fills — it NEVER writes SQL or numbers. Every result is the provenance-
stamped `/v1` envelope plus the red-team's anti-hallucination guards:
  * a mandatory **verbatim `caveat`** string the model is instructed to quote (the structure
    is dropped when a model summarizes in prose, so the caveat must be data the model echoes);
  * **typed absence** (`available: false, do_not_estimate: true`) instead of a bare null;
  * **robustness-floor suppression** (a credibility read with n_resolved<10 is never returned
    as a proven number);
  * **intent echo-back** (`interpreted_as`) so a wrong endpoint/param choice is visible.
It routes through the SDK → `/v1`, so it inherits entitlement + metering + stamping for free.
"""
from src.api.mcp.tools import tool_schemas, dispatch

__all__ = ["tool_schemas", "dispatch"]
