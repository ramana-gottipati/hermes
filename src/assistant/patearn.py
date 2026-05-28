"""patearn equity research framework — Hermes integration.

Loads the patearn methodology from resources/patearn/*.md and exposes a function
to build the system prompt for /analyze TICKER calls.

The full methodology (~14K tokens of system context) is marked with cache_control
so Anthropic's prompt cache absorbs repeated calls within the 5-min cache TTL.
First call within a window is full price; subsequent calls cost ~10% of normal
input rate on the cached portion.
"""

import logging
from pathlib import Path

log = logging.getLogger("hermes.patearn")

_RESOURCE_DIR = Path(__file__).resolve().parents[2] / "resources" / "patearn"


def _load(filename: str) -> str:
    path = _RESOURCE_DIR / filename
    if not path.exists():
        log.error("patearn resource missing: %s", path)
        return ""
    return path.read_text(encoding="utf-8")


def analysis_system_prompt() -> list[dict]:
    """System prompt blocks for a New Stock Analysis (Mode 1) /analyze call.

    Returns a list of content blocks suitable for the Anthropic SDK's `system`
    parameter. The full prompt has cache_control on the last block so the entire
    methodology body gets cached and reused at ~10% cost on subsequent calls.
    """
    skill     = _load("SKILL.md")
    patterns  = _load("patterns.md")
    failures  = _load("failures.md")

    preamble = (
        "You are a patearn equity analyst. You apply the patearn methodology in full to "
        "every Indian stock you analyse — no shortcuts, no rationalisations of hard "
        "disqualifiers. The methodology, pattern definitions, and failure case studies "
        "below are the standard. Do not rely on general knowledge; use only this framework.\n\n"
        "When asked to analyse a stock, default to Mode 1 (New stock analysis) unless the "
        "user specifies otherwise. Always produce output in this exact structure:\n\n"
        "1. **Mode** — which of the 5 modes you're running\n"
        "2. **Phase 2 — Hard Disqualifier check** (run all 5; if any fires, output "
        "DISQUALIFIED with the reason and stop)\n"
        "3. **Phase 3 — Pattern scoring**: for each of the 14 patterns, score the 3 sub-signals "
        "as Yes(2)/Partial(1)/No(0) with Verified/Estimated tags and cite a source where possible\n"
        "4. **Pattern Weighted Score (PWS)** and **Normalised Score (NS)** with the "
        "Pessimistic-Base-Optimistic sensitivity band\n"
        "5. **Pattern Activation Count (PAC)** — X / 14\n"
        "6. **Quality Gate** — pass/fail (top 5 patterns must hit 60% i.e. >= 144 pts of 240)\n"
        "7. **Tier** — T1 / T2 / T3 / T4 / DISQUALIFIED, with rationale\n"
        "8. **Bull case** — what the patterns say will happen\n"
        "9. **Bear case** — at least 3 SPECIFIC, FALSIFIABLE conditions that would break "
        "the thesis (not vague risks)\n"
        "10. **Tripwires** — concrete exit triggers per Phase 5 of methodology\n"
        "11. **Adversarial anti-signal check** — if NS > 65%, explicitly compare against "
        "the failure case studies (Vakrangee/Manpasand/Suzlon/Aban/PCJeweller/YesBank) "
        "and call out any anti-signals present\n"
        "12. **Final verdict** — Buy / Watch / Pass / Disqualified, with position size "
        "guidance per the tier matrix\n\n"
        "Use plain text or simple markdown. Avoid HTML tags. Keep numbers tight and cite "
        "Screener.in / Annual Report / BSE filing where possible. If a signal cannot be "
        "verified, mark it Estimated and apply the 70% weight rule.\n\n"
        "Be honest about data gaps. If you don't have current numbers for a stock, say so "
        "explicitly and provide your best-effort scoring based on known data + a "
        "confidence level. Never invent specifics.\n\n"
        "---\n"
        "# patearn METHODOLOGY (SKILL.md)\n\n"
        f"{skill}\n\n"
        "---\n"
        "# 14 PATTERN DEFINITIONS (patterns.md)\n\n"
        f"{patterns}\n\n"
        "---\n"
        "# FAILURE CASE STUDIES (failures.md)\n\n"
        f"{failures}\n"
    )

    return [
        {
            "type": "text",
            "text": preamble,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def user_message_for_ticker(ticker: str, extra: str = "") -> str:
    """Compose the user-side message that triggers analysis on a ticker."""
    base = (
        f"Run a full Mode 1 (New stock analysis) on **{ticker}** (NSE listing) per the "
        f"patearn methodology. Apply all 14 patterns, compute the Normalised Score with "
        f"sensitivity band, run all 5 Hard Disqualifiers, classify tier, and produce the "
        f"verdict in the structured format defined in the system prompt."
    )
    if extra:
        base += f"\n\nAdditional context from analyst:\n{extra}"
    return base
