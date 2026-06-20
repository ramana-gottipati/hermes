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
    ACC_STRENGTH, ACC_ENTRY, RS_STRENGTH, RS_ALIGN, RS_WINDOW,
    FUND_VAL, FUND_QUAL, FUND_GROW, FUND_BS, FUND_OWN, FUND_SECTOR,
    MOVERS_DIR, MOVERS_LIQ,
)

# Valid param vocabulary per flow — the single source of truth IS the chip dicts.
# "free" = any non-empty string allowed (validated/parameterized downstream).
_VALID: dict[str, dict] = {
    "accumulation": {"strength": set(ACC_STRENGTH), "entry": set(ACC_ENTRY), "sector": "free"},
    "rs":           {"strength": set(RS_STRENGTH), "align": set(RS_ALIGN), "sector": "free",
                     "window": set(RS_WINDOW)},
    "fundamentals": {"val": set(FUND_VAL), "qual": set(FUND_QUAL), "grow": set(FUND_GROW),
                     "bs": set(FUND_BS), "own": set(FUND_OWN), "sector": set(FUND_SECTOR)},
    "movers":       {"direction": set(MOVERS_DIR), "liq": set(MOVERS_LIQ)},
    "explain":      {"explain": "slug"},
}


def _menu() -> str:
    lines = [
        "FLOWS and their options (use ONLY these keys/values):",
        "1. accumulation — names a strong hand is buying (delivery + character).",
        "   strength: '' (A+, default) | 'ss' (very strong) | 'any'",
        "   entry: '' (any) | 'discount' (near a discount to the hot-day cost)",
        "   sector: a sector name (e.g. IT, Pharma, Banking) or '' for all",
        "2. rs — relative-strength leaders (the market is voting for them).",
        "   strength: '' (RS>=80) | 'elite' (RS>=90) | 'above' (RS>=50)",
        "   align: '' (any) | 'sis' (strong-in-strong: beating market AND sector)",
        "   sector: a sector name or '' for all",
        "   window: '' (3m) | '1m' (last month) | '6m' | '12m' (last year) — SET FROM THE QUESTION'S TIMEFRAME",
        "3. fundamentals — screen on valuation/quality/growth/balance-sheet.",
        "   val: '' (PE<25) | 'deep' (PE<15) | 'growthok' (PE<40) | 'any'",
        "   qual: '' (ROCE>18) | 'elite' (ROCE>22) | 'decent' (ROCE>14) | 'any'",
        "   grow: '' (profit5y>15) | 'hyper' (>25) | 'recent' (TTM>20) | 'any'",
        "   bs: '' (D/E<1) | 'fortress' (<0.5) | 'levok' (<2) | 'any'",
        "   own: '' (promoter>=35) | 'skin' (>=50) | 'clean' (pledge<5) | 'any'",
        "   sector: '' (exclude financials) | 'fin' (financials only) | 'all'",
        "4. movers — biggest PRICE MOVES TODAY (the latest session), NOT multi-month.",
        "   Use for 'top gainers', 'biggest movers today', 'what moved today', 'top losers'.",
        "   direction: '' (top gainers) | 'losers' | 'active' (most traded)",
        "   liq: '' (liquid, >= Rs 5Cr turnover) | 'all'",
        "5. explain — define a metric. set 'explain' to one of these term slugs:",
    ]
    for slug, e in GLOSSARY.items():
        al = ", ".join(e.get("aliases", [])[:3])
        lines.append(f"   {slug}: {e['term']} ({al})")
    return "\n".join(lines)


_SYSTEM = (
    "You route an Indian-stock-market analyst's English question to ONE flow and "
    "its enumerated options. Reply with COMPACT JSON ONLY, no prose:\n"
    '{"flow":"accumulation|rs|fundamentals|movers|explain","params":{...},"confidence":0-100}\n'
    'For explain use {"flow":"explain","explain":"<term-slug>"}.\n'
    '"confidence" is your 0-100 certainty in the chosen flow — be honest; a low '
    "number lets Pat ask the analyst instead of guessing.\n"
    "Use ONLY the listed keys/values. Omit any param you are unsure about (its "
    'default applies). If nothing fits, reply {"flow":null}.\n\n' + _menu()
)

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
    """The base prompt, enriched per-query with deterministic synonym hints and
    (when available) few-shot examples mined from the correction store.

    Both enrichments are best-effort and fail open — a missing module or empty
    store leaves routing exactly as before.
    """
    parts = [_SYSTEM]
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
    """Hook for §4.4.2 few-shot — filled in by the correction-learning increment."""
    return ""


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


def route(query: str, conn=None) -> dict | None:
    """English -> {flow, params} | {flow:"clarify", ...} | None.

    None => caller uses the find() fallback. A ``clarify`` result asks the analyst
    ONE question (suggested-answer chips) instead of guessing — produced ₹0 by the
    deterministic disambiguation layer, or from a low model-confidence pick.

    `conn` is accepted for signature stability (future sector validation); unused
    here. Never raises — any failure degrades to None.
    """
    q = _normalize(query)
    if len(q) < 2:
        return None
    if q in _CACHE:
        return _CACHE[q]

    # (a) Deterministic clarify FIRST — an ambiguous ask never reaches the model (₹0).
    try:
        from src.pat.disambiguate import check as _check
        clar = _check(query)
    except Exception:
        clar = None
    if clar:
        _CACHE[q] = clar
        return clar

    # (b) Route via Gemini (never-Claude), prompt enriched with hints + few-shot.
    try:
        # 512 not 160: 2.5-tier models spend "thinking" tokens before the JSON,
        # and 160 starved the harder queries (empty content -> None).
        text, provider = call_classifier(system=_build_system(query), user_msg=query, max_tokens=512)
    except Exception:
        _CACHE[q] = None
        return None
    if provider != "gemini":          # never-Claude: discard an Anthropic fallback
        _CACHE[q] = None
        return None
    parsed = None
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            parsed = json.loads(m.group(0))
    except Exception:
        parsed = None
    sel = _validate(parsed)

    # (c) Low-confidence fallback → clarify among plausible flows (Nous Hermes #2).
    if sel and sel.get("flow") and sel["flow"] != "explain":
        conf = None
        if isinstance(parsed, dict):
            try:
                conf = int(parsed.get("confidence"))
            except (TypeError, ValueError):
                conf = None
        if conf is not None and conf < _CONF_THRESHOLD:
            alt = _low_conf_clarify(query, sel)
            if alt:
                sel = alt

    _CACHE[q] = sel
    return sel
