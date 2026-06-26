"""MCP closed-vocab tools + guarded dispatch over `/v1` (via the SDK).

`tool_schemas()` returns the tool definitions an MCP server registers. `dispatch(name, args,
client)` runs one tool and returns a result the model is SAFE to relay: it carries a verbatim
`caveat`, a typed `available` flag, `do_not_estimate` on absence, and `interpreted_as`. The
actual stdio MCP server is a thin wrapper (register `tool_schemas()`; on call → `dispatch`);
it is intentionally not built here (it needs the `mcp` package + a transport) — this module is
the moat: the deterministic, hallucination-guarded mapping from intent to verified compute.
"""
from __future__ import annotations

from typing import Optional

from src.api.sdk.client import PatearnClient, ProvenancedResult

# ── the closed vocabulary (typed/enum args; the model can only pick + fill) ────
TOOL_SPECS = [
    {"name": "patearn_health", "method": "health",
     "description": "Patearn data freshness / liveness (as-of date, degraded flag).",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "patearn_coverage", "method": "coverage",
     "description": "Data coverage & known limits (compliance/audit): universe, CCI settlement "
                    "funnel, modeled-availability, freshness. No performance claim.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "patearn_universe", "method": "universe",
     "description": "Survivorship-correct universe-construction policy (delisted retained).",
     "input_schema": {"type": "object", "properties": {
         "as_of": {"type": "string", "description": "ISO date YYYY-MM-DD (optional)"}},
         "additionalProperties": False}},
    {"name": "patearn_provenance_registry", "method": "provenance_registry",
     "description": "The per-data-class provenance registry (resolve _provenance keys).",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "patearn_credibility", "method": "credibility",
     "description": "DESCRIPTIVE management guidance track-record for ONE symbol (strong/mixed/weak/"
                    "unproven). §C-backtested: NO validated return edge — for diligence in confluence, "
                    "NEVER a ranked buy/sell signal or recommendation.",
     "input_schema": {"type": "object", "properties": {
         "symbol": {"type": "string", "description": "NSE symbol, e.g. RELIANCE"}},
         "required": ["symbol"], "additionalProperties": False}},
    {"name": "patearn_attention", "method": "attention",
     "description": "Recent typed state-change events (descriptors, not signals to trade).",
     "input_schema": {"type": "object", "properties": {
         "limit": {"type": "integer", "minimum": 1, "maximum": 6}}, "additionalProperties": False}},
]
_SPEC = {t["name"]: t for t in TOOL_SPECS}

_MODEL_INSTRUCTION = ("Quote the `caveat` verbatim in your answer; never state a number without it. "
                      "If `available` is false, say the data is not available — do NOT estimate or infer it.")


def tool_schemas() -> list:
    """The tool definitions for an MCP server to register (name/description/input_schema)."""
    return [{"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in TOOL_SPECS]


def _build_caveat(res: ProvenancedResult, *, extra: str = "") -> str:
    bits = [res.banner()]
    if extra:
        bits.append(extra)
    return " · ".join(b for b in bits if b)


def _absence(name: str, interpreted: str, reason: str) -> dict:
    return {"tool": name, "interpreted_as": interpreted, "available": False,
            "value": None, "reason": reason, "do_not_estimate": True,
            "caveat": f"Patearn has no usable value here: {reason}. Do not estimate it.",
            "instruction_to_model": _MODEL_INSTRUCTION}


def dispatch(name: str, args: Optional[dict] = None, client: Optional[PatearnClient] = None) -> dict:
    """Run one closed-vocab tool and return a model-safe, caveat-bearing result."""
    args = args or {}
    spec = _SPEC.get(name)
    if spec is None:
        return {"tool": name, "available": False, "reason": f"unknown tool {name!r}",
                "do_not_estimate": True, "instruction_to_model": _MODEL_INSTRUCTION}
    if client is None:
        client = PatearnClient(args.get("_api_key", ""))

    sym = (args.get("symbol") or "").strip().upper()
    interpreted = {
        "patearn_credibility": f"credibility for {sym}",
        "patearn_universe": f"universe policy as of {args.get('as_of') or 'latest'}",
        "patearn_attention": f"attention queue (limit {args.get('limit', 6)})",
    }.get(name, spec["description"].split(".")[0])

    # call /v1 via the SDK (the one bus)
    if name == "patearn_credibility":
        if not sym:
            return _absence(name, "credibility for <missing symbol>", "no symbol provided")
        res = client.credibility(sym)
    elif name == "patearn_universe":
        res = client.universe(args.get("as_of"))
    elif name == "patearn_attention":
        res = client.attention(int(args.get("limit", 6)))
    else:
        res = getattr(client, spec["method"])()

    # non-OK → typed absence (incl. the 501 alpha-gate, 401/403 entitlement)
    if not res.ok:
        title = (res.problem or {}).get("title", f"HTTP {res.status}")
        reason = ("alpha tier gated — not yet validated (no measured-edge claim)"
                  if res.status == 501 else f"request not served ({res.status}: {title})")
        return _absence(name, interpreted, reason)

    # credibility robustness-floor suppression + typed absence
    if name == "patearn_credibility":
        cred = (res.data or {}).get("credibility", {}) if isinstance(res.data, dict) else {}
        if cred.get("available") is False:
            return _absence(name, interpreted, f"no settled credibility for {sym} (unproven / not covered)")
        robust = cred.get("robust", False)
        extra = ("" if robust else
                 f"NOT robust: n_resolved={cred.get('n_resolved')} (<10) — a descriptor, not a track record")
        return {"tool": name, "interpreted_as": interpreted, "available": True,
                "robust": bool(robust), "data": res.data,
                "caveat": _build_caveat(res, extra=extra), "_provenance": res.provenance,
                "instruction_to_model": _MODEL_INSTRUCTION}

    return {"tool": name, "interpreted_as": interpreted, "available": True, "data": res.data,
            "caveat": _build_caveat(res), "_provenance": res.provenance,
            "instruction_to_model": _MODEL_INSTRUCTION}


# ── selftest (in-process via the SDK over a TestClient transport) ─────────────
def _selftest() -> None:
    from fastapi.testclient import TestClient
    from src.api.v1 import build_app
    from src.api.v1.keys import seed_dev_key, seed_compliance_key
    from src.api.v1.selftest import _teardown

    _teardown()
    try:
        research = seed_dev_key()              # research + compliance + data-feed
        comp = seed_compliance_key()           # compliance only
        tc = TestClient(build_app(), raise_server_exceptions=False)

        def adapter(method, path, headers, params):
            r = tc.request(method, path, headers=headers, params=params)
            try:
                return r.status_code, r.json()
            except ValueError:
                return r.status_code, {}

        research_cli = PatearnClient(research, request_fn=adapter)
        comp_cli = PatearnClient(comp, request_fn=adapter)

        # schemas are well-formed + closed (no free-form beyond declared props)
        schemas = tool_schemas()
        assert len(schemas) == 6 and all(s["input_schema"].get("additionalProperties") is False for s in schemas)

        # coverage: always carries a verbatim caveat + the echo instruction
        cov = dispatch("patearn_coverage", {}, comp_cli)
        assert cov["available"] is True and cov["caveat"] and "do NOT estimate" in cov["instruction_to_model"]

        # the two-buyer split surfaces as a typed absence, never fake data
        att = dispatch("patearn_attention", {}, comp_cli)
        assert att["available"] is False and att["do_not_estimate"] is True  # compliance lacks research → 403

        # credibility is DESCRIPTIVE (served) — §C falsified the alpha. On the stub there's no data →
        # a TYPED ABSENCE (no bare null), and its caveat carries the no-validated-edge framing.
        cred = dispatch("patearn_credibility", {"symbol": "RELIANCE"}, research_cli)
        assert cred["available"] is False and cred["do_not_estimate"] is True, cred

        # missing required arg → typed absence, no crash
        assert dispatch("patearn_credibility", {}, research_cli)["available"] is False
        # unknown tool → safe
        assert dispatch("nope", {}, research_cli)["available"] is False

        print("mcp selftest: OK  (closed schemas · verbatim caveat · two-buyer 403->absence · "
              "credibility descriptive/no-edge · robustness-floor · no bare null)")
    finally:
        _teardown()


if __name__ == "__main__":
    _selftest()
