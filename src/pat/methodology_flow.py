"""Pat 'methodology' explain-flow — plain-language strategy explainers (UX audit S-E Phase 3).

Answers "explain the Wolfe methodology / how does CPR work / what's the DVPT idea / how does
the reversal strategy work" with a plain-language summary sourced from the canonical
docs/strategies/<slug>.md pages served at /dash/strategy-ref + a link. This grounds
Pat's explain corpus on METHODOLOGY, not just term definitions (the glossary 'explain' flow):
the glossary says WHAT a metric is; this says HOW a strategy works, in the desk's own words.

CONTRACT (mirrors nav_flow.py):
  * PURE logic here — `parse_methodology()` (a ₹0 pre-pass in engine.route) and `summary()`
    (reads the strategy md, sanitized). Render = web.py:_methodology_flow.
  * CONSERVATIVE: needs a METHODOLOGY cue (methodology / strategy / idea / "how does X work")
    AND a strategy name — so a bare "what is DVPT" stays a glossary explain and "any wolfe
    setups" stays the wolfe data flow. A miss yields None.
  * SEBI-safe + no leakage: reuses strategies_view._public() so no governance / session-ID /
    "Ramana" language ever reaches the answer; every source page carries its own fence.
"""
from __future__ import annotations

import re

# methodology / how-it-works cue (distinguishes from a bare glossary "what is X")
_METH_WORD = re.compile(r"\b(methodology|method|strateg(?:y|ies)|approach|technique|philosophy|"
                        r"concept|logic|framework|idea|principle|thesis)\b")
_HOW_WORK = re.compile(r"\bhow\b")
_WORK = re.compile(r"\bwork(?:s|ing)?\b")
_WALK = re.compile(r"\b(walk me through|explain how|tell me about|how it works|how it is (?:done|built))\b")

# strategy name → served slug (ordered specific → generic; first match wins). Generic bare
# words ("momentum", "structure") are LAST so a distinctive name is preferred.
_SLUG_HOOKS: list[tuple[str, tuple[str, ...]]] = [
    ("wolfe-wave",        ("wolfe wave", "wolfe-wave", "wolfe")),
    ("cpr",               ("central pivot range", "cpr spine", "cpr")),
    ("dvpt",              ("delivery value per trade", "dvpt")),
    ("mep",               ("accumulation distribution", "accum distrib", "accumulation pressure", "mep")),
    ("harmonic",          ("harmonic", "gartley", "xabcd", "prz")),
    ("cci",               ("concall credibility", "credibility index", "concall", "cci")),
    ("patearn",           ("14-pattern", "14 pattern", "fundamental quality", "patearn")),
    ("classic-screens",   ("classic screen", "magic formula", "canslim", "piotroski", "coffee can",
                           "greenblatt", "graham screen")),
    ("union-ladder",      ("union ladder", "union-ladder", "family ladder", "union family")),
    ("union",             ("the union", "union")),
    ("sector-rotation",   ("sector rotation", "sector-rotation")),
    ("rule-lab",          ("rule lab", "rule-lab", "rule composer")),
    ("reversal-context",  ("reversal context", "stream band", "fractal floor", "reversal")),
    ("momentum-riskadj",  ("risk-adjusted momentum", "riskadj", "ranked rotation", "rotation engine",
                           "momentum ensemble", "momentum strategy", "momentum methodology")),
    ("relative-strength", ("relative strength", "rs suite", "mansfield", "rs ratio")),
]


def _slug_for(ql: str) -> str:
    for slug, hooks in _SLUG_HOOKS:
        if any(h in ql for h in hooks):
            return slug
    return ""


def parse_methodology(query: str) -> dict | None:
    """"explain the Wolfe methodology / how does CPR work / what's the DVPT idea" ->
    {flow:"methodology", params:{slug}} | None. Needs a methodology cue AND a known strategy
    name; a bare "what is X" (no cue) yields to the glossary explain, "any wolfe setups" to
    the wolfe data flow."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    cue = bool(_METH_WORD.search(ql) or _WALK.search(ql) or (_HOW_WORK.search(ql) and _WORK.search(ql)))
    if not cue:
        return None
    slug = _slug_for(ql)
    if not slug:
        return None
    return {"flow": "methodology", "params": {"slug": slug}}


# ── plain-language summary from the canonical strategy page ────────────────────────────
_ONELINE_RE = re.compile(r"\*\*One-line definition:\*\*\s*(.+)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")           # [text](url) → text
_EMPH_RE = re.compile(r"[*`>#]")                          # strip md emphasis/heading/quote marks


def _plain(md: str) -> str:
    s = _LINK_RE.sub(r"\1", md)
    s = _EMPH_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def summary(slug: str) -> dict | None:
    """{slug, label, plain, link} for a strategy slug, or None. Leads with the page's
    'One-line definition' (sanitized via strategies_view._public), falling back to the first
    paragraph under '## 1. What it is'. SEBI-safe: never leaks governance/ID language."""
    try:
        from src.web import strategies_view as SV
    except Exception:
        return None
    entry = SV._PAGES.get(slug)
    if not entry:
        return None
    fn, label = entry
    try:
        text = SV._read(fn)          # already _public()-sanitized
    except Exception:
        text = None
    if not text:
        return None
    plain = ""
    m = _ONELINE_RE.search(text)
    if m:
        plain = _plain(m.group(1))
    if not plain:
        # fallback: first non-empty paragraph after "## 1. What it is"
        after = re.split(r"##\s*1\.\s*What it is", text, maxsplit=1)
        if len(after) > 1:
            for para in after[1].split("\n\n"):
                p = _plain(para)
                if len(p) > 40:
                    plain = p
                    break
    if not plain:
        return None
    if len(plain) > 600:
        plain = plain[:597].rsplit(" ", 1)[0] + "…"
    return {"slug": slug, "label": label, "plain": plain, "link": f"{SV._ROUTE}?p={slug}"}


def _selftest() -> int:
    # recognition — cue + a strategy name
    assert parse_methodology("explain the wolfe methodology")["params"]["slug"] == "wolfe-wave"
    assert parse_methodology("how does CPR work")["params"]["slug"] == "cpr"
    assert parse_methodology("what's the DVPT idea")["params"]["slug"] == "dvpt"
    assert parse_methodology("explain the reversal strategy")["params"]["slug"] == "reversal-context"
    assert parse_methodology("how does the momentum strategy work")["params"]["slug"] == "momentum-riskadj"
    assert parse_methodology("walk me through harmonic patterns")["params"]["slug"] == "harmonic"
    assert parse_methodology("how does the CCI methodology work")["params"]["slug"] == "cci"
    assert parse_methodology("explain the union strategy")["params"]["slug"] == "union"
    assert parse_methodology("what's the union ladder concept")["params"]["slug"] == "union-ladder"
    assert parse_methodology("how does sector rotation work")["params"]["slug"] == "sector-rotation"
    assert parse_methodology("explain the rule lab idea")["params"]["slug"] == "rule-lab"
    assert parse_methodology("how does the rotation engine work")["params"]["slug"] == "momentum-riskadj"
    # yields — no methodology cue (bare glossary explain), or no known strategy
    assert parse_methodology("what is DVPT") is None, "bare term → glossary explain, not us"
    assert parse_methodology("any wolfe setups") is None, "data flow, not methodology"
    assert parse_methodology("explain the quantum strategy") is None, "no known strategy"
    assert parse_methodology("how are stocks doing") is None
    assert parse_methodology("") is None
    # summary — reads the real canonical pages, sanitized (no governance/ID leakage)
    s = summary("wolfe-wave")
    assert s and s["slug"] == "wolfe-wave" and s["link"] == "/dash/strategy-ref?p=wolfe-wave"
    assert "5-pivot" in s["plain"] or "reversal" in s["plain"], s["plain"][:80]
    for banned in ("Ramana", "Governing decision", "do not archive"):
        assert banned not in s["plain"], f"leaked: {banned}"
    assert not re.search(r"\bS\d{2,3}\b|\bD\d{2,3}\b", s["plain"]), "leaked a session/decision id"
    for sl in ("cpr", "dvpt", "mep", "cci", "harmonic", "momentum-riskadj", "relative-strength",
               "union", "union-ladder", "sector-rotation", "rule-lab"):
        assert summary(sl) and len(summary(sl)["plain"]) > 40, sl
    assert summary("nonexistent") is None
    print("methodology_flow selftest OK v2 — recognition incl. union/ladder/sector-rotation/rule-lab "
          "(methodology cue + strategy name; yields on bare term / data ask / unknown) + sanitized "
          "plain-language summary from every docs/strategies page (no governance/ID leakage).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
