"""Pat's free-text engine — maps an English question to a flow + chip params.

It NEVER writes SQL. It only selects one of the existing flows and fills their
ENUMERATED chip parameters, which then feed the same deterministic
``build_*_query`` templates the tap path uses. A hallucinated column is therefore
structurally impossible — the model can only emit chip keys, validated here
against the chip dicts before anything touches a query.

Cost discipline (D55 + cost doctrine §A):
  - Only called for genuine free-text (a typed ``q`` with no explicit flow); chip
    taps never reach here, so the tap path stays ₹0.
  - Gemini Flash only — if ``llm_router`` falls back to Anthropic, the result is
    DISCARDED (never-Claude) and the caller degrades to the find() keyword path.
  - Results cached by normalized query (one user → high hit rate).
"""

from __future__ import annotations

import json
import re

from src.core.llm_router import call_classifier
from src.pat.glossary import GLOSSARY
from src.pat.flows import (
    ACC_STRENGTH, ACC_ENTRY, ACC_WINDOW, ACC_CHARACTER,
    RS_STRENGTH, RS_ALIGN, RS_WINDOW, RS_DIRECTION,
    FUND_VAL, FUND_QUAL, FUND_GROW, FUND_BS, FUND_OWN, FUND_SECTOR,
    MOVERS_DIR, MOVERS_LIQ, MOVERS_WINDOW,
    INDEX_WINDOW, INDEX_DIRECTION, INDEX_TURNING,
)

# Valid param vocabulary per flow — the single source of truth IS the chip dicts.
# "free" = any non-empty string allowed (validated/parameterized downstream).
_VALID: dict[str, dict] = {
    "accumulation": {"strength": set(ACC_STRENGTH), "entry": set(ACC_ENTRY), "sector": "free",
                     "window": set(ACC_WINDOW), "character": set(ACC_CHARACTER)},
    "rs":           {"strength": set(RS_STRENGTH), "align": set(RS_ALIGN), "sector": "free",
                     "window": set(RS_WINDOW), "direction": set(RS_DIRECTION)},
    "fundamentals": {"val": set(FUND_VAL), "qual": set(FUND_QUAL), "grow": set(FUND_GROW),
                     "bs": set(FUND_BS), "own": set(FUND_OWN), "sector": set(FUND_SECTOR)},
    "movers":       {"direction": set(MOVERS_DIR), "liq": set(MOVERS_LIQ),
                     "window": set(MOVERS_WINDOW)},
    "index":        {"window": set(INDEX_WINDOW), "direction": set(INDEX_DIRECTION),
                     "turning": set(INDEX_TURNING)},
    "credibility":  {},   # CCI credibility leaders — parameterless descriptive flow
    "deterioration": {},  # CCI deterioration / avoid tape — parameterless
    "explain":      {"explain": "slug"},
}


# Routing no longer uses a flat flow-classifier prompt. The model now does a
# SEMANTIC PARSE into a structured intent (universe → rank → filters) — see
# src/pat/understand.py:SYSTEM_PARSE — and the deterministic compiler maps that
# intent onto a flow. _VALID above is retained to SANITIZE the compiler's output
# params against the chip vocab (defense in depth — off-menu params can't reach SQL).

# Below this certainty, route() turns the model's pick into a clarify among the
# plausible flows rather than committing to a guess (Nous Hermes idea #2, §9).
_CONF_THRESHOLD = 50

_CACHE: dict[str, dict | None] = {}
_WS = re.compile(r"\s+")


def _normalize(q: str) -> str:
    return _WS.sub(" ", (q or "").strip().lower())


def _validate(obj) -> dict | None:
    """Coerce a parsed model reply to a safe {flow, params} | None."""
    if not isinstance(obj, dict):
        return None
    flow = obj.get("flow")
    if flow not in _VALID:
        return None
    if flow == "explain":
        slug = obj.get("explain") or (obj.get("params") or {}).get("explain")
        return {"flow": "explain", "explain": slug} if slug in GLOSSARY else None
    spec = _VALID[flow]
    raw = obj.get("params")
    if not isinstance(raw, dict):
        raw = {}
    params: dict[str, str] = {}
    for k, allowed in spec.items():
        v = raw.get(k)
        if v is None:
            continue
        v = str(v).strip()
        if allowed == "free":
            if v:
                params[k] = v
        elif v in allowed:
            params[k] = v
    return {"flow": flow, "params": params}


def _build_system(query: str) -> str:
    """The semantic-parse prompt (understand.SYSTEM_PARSE), enriched per-query with
    deterministic synonym hints and few-shot examples mined from the correction
    store. Both enrichments are best-effort and fail open.
    """
    from src.pat.understand import SYSTEM_PARSE
    parts = [SYSTEM_PARSE]
    try:
        from src.pat.disambiguate import hints as _hints
        h = _hints(query)
        if h:
            parts.append(h)
    except Exception:
        pass
    try:
        block = _fewshot_block()
        if block:
            parts.append(block)
    except Exception:
        pass
    return "\n\n".join(parts)


def _fewshot_block() -> str:
    """Few-shot examples mined from the correction store (§4.4.2): confirmed 👍
    routings teach the user's phrasings; 👎 corrections teach what they actually
    wanted when Pat missed. ₹0, fails open to '' when the store is empty.

    The positives are rendered in the EXACT output format the model must emit, so
    they double as format anchors. The same store is the labeled dataset to later
    fine-tune an OWNED offline model (NOT the borrowed Nous agent)."""
    try:
        from src.pat import feedback
        positives = feedback.recent_positive_examples(limit=6)
        corrections = feedback.recent_corrections(limit=4)
    except Exception:
        return ""
    if not positives and not corrections:
        return ""
    lines = ["LEARNED FROM THIS ANALYST — prefer these mappings; they were confirmed "
             "(👍) or corrected (👎) by the user on earlier answers:"]
    for ex in positives:
        params = ex.get("params") or {}
        if ex.get("flow") == "explain":
            tgt = '{"flow":"explain","explain":"%s"}' % params.get("explain", "")
        else:
            tgt = json.dumps({"flow": ex.get("flow"), "params": params},
                             separators=(",", ":"), ensure_ascii=False)
        lines.append(f'  "{ex.get("query", "")}" -> {tgt}')
    for cx in corrections:
        exp = (cx.get("expected_text") or "").strip()
        if not exp:
            continue
        lines.append(f'  "{cx.get("query", "")}" -> the analyst did NOT want '
                     f'{cx.get("flow") or "that"}; they wanted: {exp}')
    return "\n".join(lines)


def _low_conf_clarify(query: str, sel: dict):
    """Turn a low-certainty model pick into a clarify among the plausible flows
    (the model's choice + any other flows the analyst's vocabulary points at)."""
    try:
        from src.pat.disambiguate import concepts as _concepts, clarify_from_flows
        cs = _concepts(query)
    except Exception:
        return None
    flows = [sel["flow"]] + [c for c in ("rs", "fundamentals", "accumulation", "movers")
                             if c in cs and c != sel["flow"]]
    return clarify_from_flows(query, flows)


def _intent_to_sel(intent: dict, query: str) -> dict | None:
    """Compile a structured intent to a flow selection, sanitize its params against
    the chip vocab, and apply the low-confidence → clarify safety."""
    from src.pat.understand import compile_intent
    sel = compile_intent(intent)
    if not sel:
        return None
    # Sanitize compiler output params against the chip dicts (defense in depth) —
    # clarify payloads pass through untouched.
    if sel.get("flow") in _VALID:
        sel = _validate(sel) or sel
    # Low model-confidence on a committed data flow → clarify instead of guessing.
    conf = intent.get("confidence")
    if (sel and sel.get("flow") in ("rs", "accumulation", "fundamentals", "movers")
            and isinstance(conf, int) and conf < _CONF_THRESHOLD):
        alt = _low_conf_clarify(query, sel)
        if alt:
            sel = alt
    return sel


def route(query: str, conn=None) -> dict | None:
    """English -> {flow, params} | {flow:"clarify", ...} | None.

    The query is SEMANTICALLY PARSED into a structured intent (universe → rank →
    filters) and a deterministic compiler maps that intent onto a flow — or a
    clarify when the ask is ambiguous / not yet supported (never a confident wrong
    dump). The parse is done by Gemini (never-Claude); if the model is unavailable
    (e.g. quota), a degraded deterministic fallback parser takes over. None => the
    caller uses the glossary find() fallback.

    `conn` is accepted for signature stability (future sector validation); unused
    here. Never raises — any failure degrades to None.
    """
    q = _normalize(query)
    if len(q) < 2:
        return None
    if q in _CACHE:
        return _CACHE[q]

    from src.pat.understand import validate_intent, parse_fallback

    # (a0) Advisory / out-of-domain guardrail FIRST — an advice/predict/alert/wrong-
    #      asset ask gets a clarify-shaped REDIRECT, never a wrong flow or a blank
    #      result (catalog Part 5; SEBI line: never a buy/sell verdict). ₹0.
    try:
        from src.pat.disambiguate import route_guardrail as _guard
        guard = _guard(query)
    except Exception:
        guard = None
    if guard:
        _CACHE[q] = guard
        return guard

    # (a) Quota-proof deterministic clarify for the classic ambiguities
    #     ("strong stocks" / "RS leaders recently") — ₹0, never reaches the model.
    try:
        from src.pat.disambiguate import check as _check
        clar = _check(query)
    except Exception:
        clar = None
    if clar:
        _CACHE[q] = clar
        return clar

    # (a2) Deterministic routers for the cheap-win flows (distribution, rs-laggards,
    #      kill-list, pt14, overvalued, single-stock) — ₹0, quota-proof, and immune to
    #      mis-routing for these distinctive asks. None → fall through to the parse.
    try:
        from src.pat.disambiguate import route_extra as _route_extra
        extra = _route_extra(query)
    except Exception:
        extra = None
    if extra:
        _CACHE[q] = extra
        return extra

    # (b) Primary path: Gemini semantically PARSES the query into a structured
    #     intent (never-Claude). The compiler then reasons it onto a flow.
    intent = None
    try:
        text, provider = call_classifier(system=_build_system(query), user_msg=query, max_tokens=512)
        if provider == "gemini":          # never-Claude: discard an Anthropic fallback
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                intent = validate_intent(json.loads(m.group(0)))
    except Exception:
        intent = None

    # (c) Degraded fallback: the model was unavailable (quota/outage) → parse with
    #     deterministic rules so Pat still reasons about universe/metric/window.
    if intent is None:
        intent = parse_fallback(query)

    sel = _intent_to_sel(intent, query) if intent else None
    _CACHE[q] = sel
    return sel
