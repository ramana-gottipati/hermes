"""Compliance-language gate — the regulatory fence, machine-enforced (D134, S149).

Patearn's posture (docs/patearn-analytics-company-plan.md §3) is an UNREGISTERED
analytics company: descriptive statistics, screeners, education — never buy/sell/hold
recommendations, target prices, or solicitation. SEBI's RA Regulations 2014 exclude
"statistical summaries of financial data" and general market commentary from the
regulated "research report"; the moment a public surface utters recommendation
language, that exclusion is lost. This gate makes the boundary a suite invariant
instead of a convention — the fifth gate beside route / education / doc-hygiene /
state-doc.

What it does: scans every rendering source file (src/web + src/pat — all site HTML
lives in these .py string literals) for solicitation/recommendation PHRASES. The
lexicon is deliberately phrase-level and multi-word so the product's own descriptive
vocabulary ("accumulation" (MEP), "buyback", "exit law", options "call") can never
false-positive. A legitimate hit (e.g. a glossary entry that quotes a forbidden
phrase in order to define it) goes in _ALLOW with a written reason; stale allowlist
entries fail the suite so the list can only shrink honestly.

Scope note: this gate lints OUR language, including any future AI-generated
composition (D134 L6) whose templates live in these trees. It does not scan data
passing through at runtime (news headlines etc. are third-party content, displayed
as data with attribution, not our speech).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = (REPO / "src" / "web", REPO / "src" / "pat")

# Solicitation / recommendation phrases that must never appear in anything we render.
# Multi-word (or hyphenated) by construction — see the staleness/self-checks below.
_FORBIDDEN: tuple[str, ...] = (
    "we recommend buying",
    "we recommend selling",
    "you should buy",
    "you should sell",
    "must buy",
    "must sell",
    "buy now",
    "sell now",
    "buy today",
    "sell today",
    "book profits now",
    "add on dips",
    "accumulate on dips",
    "target price of",
    "price target of",
    "strong buy",
    "strong sell",
    "sure shot",
    "sure-shot",
    "guaranteed return",
    "guaranteed profit",
    "assured return",
    "risk-free profit",
    "multibagger tip",
    "multibagger call",
    "jackpot call",
    "intraday call",
    "intraday tip",
    "trading tips",
    "stock tips",
    "paid tips",
    "paid calls",
    "premium calls",
    "subscribe for calls",
    "invest in this stock",
    "this stock will double",
)

# (posix relpath from repo root, phrase) -> written reason. An entry here must still
# match its file (stale entries FAIL) — the list can only shrink honestly.
_ALLOW: dict[tuple[str, str], str] = {
    # Pat's advisory/prediction REFUSAL detectors (catalog Part 5): these phrases
    # appear as trigger patterns Pat matches in USER questions in order to refuse
    # them ("stock to buy now", "sure shot", ...) — the enforcement of the SEBI
    # line, not a breach of it.
    ("src/pat/disambiguate.py", "buy now"): "inside _G_ADVICE detector phrases ('stock to buy now') — user-ask refusal triggers",
    ("src/pat/disambiguate.py", "sure shot"): "_G_PREDICT refusal trigger — detected in user asks, refused",
    ("src/pat/disambiguate.py", "guaranteed return"): "_G_ADVICE refusal trigger — detected in user asks, refused",
    ("src/pat/disambiguate.py", "intraday tip"): "_G_PREDICT refusal trigger — detected in user asks, refused",
    ("src/pat/understand.py", "intraday tip"): "_OOD_FEATURE refusal trigger — detected in user asks, refused",
}


def _rx(phrase: str) -> re.Pattern[str]:
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)


def _scan() -> tuple[list[tuple[str, int, str]], list[tuple[str, str]]]:
    """Return (violations, stale_allowlist). violations = (relpath, line, phrase)."""
    compiled = [(p, _rx(p)) for p in _FORBIDDEN]
    hits: list[tuple[str, int, str]] = []
    matched_allow: set[tuple[str, str]] = set()
    for d in SCAN_DIRS:
        for f in sorted(d.glob("*.py")):
            rel = f.relative_to(REPO).as_posix()
            text = f.read_text(encoding="utf-8", errors="replace")
            for phrase, rx in compiled:
                for m in rx.finditer(text):
                    key = (rel, phrase)
                    if key in _ALLOW:
                        matched_allow.add(key)
                        continue
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append((rel, line, phrase))
    stale = [k for k in _ALLOW if k not in matched_allow]
    return hits, stale


def test_lexicon_is_phrase_level():
    """Every forbidden entry is multi-word or hyphenated — single ambiguous words
    (buy, call, target, accumulate...) are structurally excluded from the lexicon."""
    for p in _FORBIDDEN:
        assert (" " in p) or ("-" in p), f"single-word lexicon entry too ambiguous: {p!r}"


def test_scan_set_is_real():
    """A path regression must not silently pass the gate."""
    files = [f for d in SCAN_DIRS for f in d.glob("*.py")]
    assert len(files) >= 40, f"scan set suspiciously small ({len(files)} files) — check SCAN_DIRS"


def test_no_solicitation_language():
    hits, stale = _scan()
    msg = []
    if hits:
        msg.append("Solicitation/recommendation language in rendering sources "
                   "(docs/patearn-analytics-company-plan.md §3.4 — this is the regulatory fence):")
        msg += [f"  {rel}:{line}: {phrase!r}" for rel, line, phrase in hits]
        msg.append("Fix the copy (descriptive vocabulary only), or — only for a genuine "
                   "definitional quote — add (relpath, phrase) to _ALLOW with a written reason.")
    if stale:
        msg.append("Stale _ALLOW entries (phrase no longer present — remove them):")
        msg += [f"  {rel}: {phrase!r}" for rel, phrase in stale]
    assert not msg, "\n".join(msg)
