"""CCI number + language normalisation (deterministic, pure, no LLM).

The expectation-adjusted BEAT/MISS settlement is computed on numbers parsed out
of Hinglish / ASR-garbled transcripts where "fifteen hundred crore" = 1500 and a
mis-heard "fifteen percent" -> "50%" silently inverts MET/MISSED. This module is
the load-bearing pre-step (debate India must-do #8):

  - parse_amount(text)      -> (value, unit) with unit in {cr, %, x, None};
                               'cr' values are normalised to ₹ CRORE (Indian basis).
  - classify_commitment()   -> HARD | SOFT | DIRECTIONAL | ASPIRATIONAL
                               (the no-Reg-FD universe is gradeable on direction).
  - HEDGE_LEXICON / tone_hint() -> India-English hedge/conviction phrases; ritual
                               fillers ("by god's grace", "going forward") score 0,
                               NOT signal — the US tone prior mis-reads these.

Used by concall_extract (pre-process + few-shot anchors) and concall_settle
(target parsing). Run `python -m src.automation.cci_normalize` for the self-test.
"""

from __future__ import annotations

import re
from typing import Optional

# --- scale words -> multiplier expressed in ₹ CRORE ------------------------
# 1 crore = 1e7. lakh = 0.01 cr, million = 0.1 cr, billion = 100 cr.
_SCALE_CR = {
    "thousand crore": 1000.0, "lakh crore": 100000.0,
    "crore": 1.0, "crores": 1.0, "cr": 1.0,
    "lakh": 0.01, "lakhs": 0.01, "lac": 0.01, "lacs": 0.01,
    "million": 0.1, "mn": 0.1, "billion": 100.0, "bn": 100.0,
}

_W = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
      "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
      "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
      "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
      "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_SC = {"hundred": 100, "thousand": 1000, "lakh": 100000, "lac": 100000,
       "crore": 10000000, "million": 1000000, "billion": 1000000000}

# digit pattern allowing Indian grouping (1,50,000) and Western (1,500)
_NUM = r"\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?"


def _scale_mult(w: str) -> Optional[float]:
    return _SCALE_CR.get(w.rstrip(".").strip())


def _words_to_number(s: str) -> Optional[float]:
    """Compact English cardinal parser: 'fifteen hundred' -> 1500."""
    toks = [t for t in re.findall(r"[a-z]+", s.lower()) if t in _W or t in _SC or t in ("and",)]
    if not toks:
        return None
    total, cur, seen = 0, 0, False
    for t in toks:
        if t == "and":
            continue
        if t in _W:
            cur += _W[t]; seen = True
        elif t in _SC:
            sc = _SC[t]; seen = True
            if sc >= 1000:
                total += (cur or 1) * sc; cur = 0
            else:                       # hundred
                cur = (cur or 1) * sc
    return float(total + cur) if seen else None


def _spoken_amount_cr(t: str) -> Optional[float]:
    m = re.search(r"([a-z ]+?)\s+(thousand crore|lakh crore|crores?|lakhs?|lacs?|million|billion)\b", t)
    if not m:
        return None
    n = _words_to_number(m.group(1))
    sc = _scale_mult(m.group(2))
    return n * sc if (n is not None and sc is not None) else None


def parse_amount(text: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    """Parse a guidance/actual magnitude -> (value, unit).

    unit ∈ {"cr","%","x",None}. 'cr' is normalised to ₹ crore. Returns (None,None)
    when no number is present (the no-Reg-FD case — grade such promises on direction).
    """
    if not text:
        return (None, None)
    t = text.lower().replace("₹", " ").replace("rs.", " ").replace("rs ", " ").replace("inr", " ")

    m = re.search(rf"({_NUM})\s*(?:%|per\s?cent|percent)", t)
    if m:
        return (float(m.group(1).replace(",", "")), "%")

    m = re.search(rf"({_NUM})\s*(?:x|times)\b", t)
    if m:
        return (float(m.group(1).replace(",", "")), "x")
    for w, v in (("double", 2.0), ("triple", 3.0), ("halve", 0.5)):
        if re.search(rf"\b{w}\b", t):
            return (v, "x")

    m = re.search(rf"({_NUM})\s*(thousand crore|lakh crore|crores?|cr\.?|lakhs?|lacs?|million|mn|billion|bn)\b", t)
    if m:
        sc = _scale_mult(m.group(2))
        if sc is not None:
            return (float(m.group(1).replace(",", "")) * sc, "cr")

    sp = _spoken_amount_cr(t)
    if sp is not None:
        return (sp, "cr")

    m = re.search(rf"({_NUM})", t)
    if m:
        return (float(m.group(1).replace(",", "")), None)
    return (None, None)


# --- commitment strength ---------------------------------------------------

_ASPIRATIONAL = ("aspir", "vision", "dream", "someday", "eventually", "ambition", "wish to", "long term goal")
_HEDGE_WORDS = ("around", "roughly", "approximately", "in the range", "ballpark", "could", "should",
                "maybe", "perhaps", "hopefully", "try to", "aim to", "or so", "thereabouts")
_DIRECTIONAL = ("grow", "growth", "increase", "improve", "expand", "higher", "lower", "decline",
                "reduce", "double", "triple", "ramp", "accelerat", "moderat", "pick up", "soften",
                "stronger", "weaker", "uptick", "headwind", "tailwind")


def classify_commitment(text: Optional[str]) -> str:
    """HARD (number, committal) | SOFT (number, hedged) | DIRECTIONAL (sign only) | ASPIRATIONAL."""
    t = (text or "").lower()
    val, _ = parse_amount(t)
    if any(w in t for w in _ASPIRATIONAL) and val is None:
        return "ASPIRATIONAL"
    hedged = any(w in t for w in _HEDGE_WORDS)
    if val is not None:
        return "SOFT" if hedged else "HARD"
    if any(w in t for w in _DIRECTIONAL):
        return "DIRECTIONAL"
    return "SOFT"


# --- India-English hedge / conviction lexicon ------------------------------
# Polarity: +ve = conviction, -ve = caution, 0 = RITUAL FILLER (no signal — the
# critical India correction; a US tone model scores these as confidence).
HEDGE_LEXICON: dict[str, int] = {
    "we are confident": 1, "we are very confident": 2, "we will definitely": 2,
    "committed to": 1, "on track": 1, "comfortably": 1, "well placed": 1, "robust": 1,
    "by god's grace": 0, "going forward": 0, "needful": 0, "as such": 0, "the same": 0,
    "cautiously optimistic": 0, "wait and watch": -1, "challenging": -1, "headwinds": -1,
    "subdued": -1, "muted": -1, "soft": -1, "to some extent": -1, "difficult to say": -1,
    "too early to": -1, "hopefully": -1, "should be able to": -1, "under pressure": -1,
}


def tone_hint(text: Optional[str]) -> int:
    """Bounded net conviction-minus-caution from the lexicon (ritual fillers = 0)."""
    t = (text or "").lower()
    score = sum(v for phrase, v in HEDGE_LEXICON.items() if phrase in t)
    return max(-5, min(5, score))


def _selftest() -> None:
    cases_amt = [
        ("₹1,500 crore", (1500.0, "cr")), ("Rs 2000 cr", (2000.0, "cr")),
        ("fifteen hundred crore", (1500.0, "cr")), ("around 2,000 crore", (2000.0, "cr")),
        ("15%", (15.0, "%")), ("15 per cent", (15.0, "%")), ("1.5x", (1.5, "x")),
        ("double", (2.0, "x")), ("1,50,000 lakh", (1500.0, "cr")), ("500 million", (50.0, "cr")),
    ]
    for s, exp in cases_amt:
        got = parse_amount(s)
        assert got == exp, f"parse_amount({s!r}) = {got}, expected {exp}"
    cases_cmt = [
        ("we will achieve revenue of 5000 crore by FY26", "HARD"),
        ("revenue should be around 5000 crore", "SOFT"),
        ("we expect strong growth and margin expansion", "DIRECTIONAL"),
        ("our vision is to be the market leader someday", "ASPIRATIONAL"),
    ]
    for s, exp in cases_cmt:
        got = classify_commitment(s)
        assert got == exp, f"classify_commitment({s!r}) = {got}, expected {exp}"
    assert tone_hint("we are very confident, on track") == 3
    assert tone_hint("by god's grace, going forward") == 0   # ritual fillers, not signal
    assert tone_hint("challenging and muted, under pressure") == -3
    print("cci_normalize self-test: ALL PASS")


if __name__ == "__main__":
    _selftest()
