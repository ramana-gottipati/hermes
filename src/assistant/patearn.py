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
        "6. **Quality Gate** — pass/fail (top 5 patterns must hit 60% i.e. >= 151.2 pts of 252)\n"
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


def run_analysis(ticker: str, extra: str = "", *, use_sonnet: bool = False) -> str:
    """Synchronous Claude call for full patearn analysis on a ticker.

    Default model is HAIKU (cost-conscious choice — Stage 2 of the two-stage
    flow). Pass use_sonnet=True to force the higher-quality Sonnet path for
    manual /analyze calls where the user wants premium analysis.

    CL-SYS-03 invariant: the Sonnet tier is OPT-IN here (use_sonnet defaults False
    → Haiku). Any user-initiated /analyze caller that wants Sonnet MUST pass
    use_sonnet=True explicitly — never rely on a global default to pick Sonnet.
    (Today the Telegram /analyze command is a claude.ai-redirect guide and does not
    call this; this stays Haiku-by-default for any future automated caller.)
    """
    from src.core.llm import client, first_text
    from src.core.settings import settings

    model = settings.default_model if use_sonnet else settings.fast_model

    response = client().messages.create(
        model=model,
        max_tokens=4096,
        system=analysis_system_prompt(),
        messages=[{"role": "user", "content": user_message_for_ticker(ticker, extra=extra)}],
    )
    log.info(
        "patearn analysis %s (model=%s): in=%d out=%d cache_read=%d cache_create=%d",
        ticker, model,
        response.usage.input_tokens,
        response.usage.output_tokens,
        getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
    )
    return first_text(response)


# --- Stage 1 — cheap pre-screen on earnings news ---------------------------

STAGE1_SYSTEM = """You are a fast first-pass screener for Indian stock earnings announcements, looking for patearn-style multi-bagger signals BEFORE institutional re-rating. Output STRICT JSON only — no prose, no markdown fence."""

STAGE1_USER_TEMPLATE = """Given this earnings-related news item, produce a JSON object with EXACTLY these keys:

  "symbol":   the most likely NSE ticker for the company in this headline (uppercase, no .NS suffix)
  "verdict":  one of PASS | WATCH | SKIP
  "rationale": <=25 words on WHY this verdict
  "signals":  a JSON array of short tags from: revenue_acceleration, profit_acceleration, opm_expansion,
              roce_improvement, margin_mix_shift, mgmt_guidance_raise, segment_inflection,
              one_off_clean_beat, beat_estimates, miss_estimates, inline, governance_red_flag

VERDICT CRITERIA (be ruthless on SKIP):
  PASS — Strong signal. At least 2 of: revenue growth > 15%, profit growth > revenue growth,
         OPM/EBITDA margin expansion, ROCE/ROE improvement explicit, segment-mix or export
         inflection cited, management guidance raised.
  WATCH — Mild signal: 1 of the above, OR clean beat but small magnitude, OR stock has known
         strong setup and results don't break thesis.
  SKIP — Routine in-line results, miss, conglomerate noise, headline-only with no detail,
         already-rerated large cap (Nifty50 names default to SKIP unless extraordinary),
         or anything that doesn't move the patearn needle.

The point is to surface RE-RATING CANDIDATES before the market reprices them. Most earnings
should SKIP. Reserve PASS for items that genuinely look like patearn material.

Input:
  Source: {source}
  Tag:    {tag}
  Title:  {title}
"""


def stage1_screen(item: dict) -> dict:
    """Quick Haiku check on an earnings news item.

    Returns:
        {"symbol": str, "verdict": "PASS"|"WATCH"|"SKIP", "rationale": str, "signals": list[str]}
        On failure, returns {"verdict": "SKIP", "rationale": "screen failed", ...}
    """
    import json
    import re

    from src.core.llm import client, first_text
    from src.core.settings import settings

    user_msg = STAGE1_USER_TEMPLATE.format(
        source=item.get("source", ""),
        tag=item.get("tag", ""),
        title=item.get("title", ""),
    )
    try:
        response = client().messages.create(
            model=settings.fast_model,
            max_tokens=300,
            system=STAGE1_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        log.error("stage1 screen call failed: %s", e)
        return {"verdict": "SKIP", "rationale": "screen call failed", "symbol": "", "signals": []}

    raw = first_text(response).strip()
    # Strip code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    # Find first { ... }
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        log.warning("stage1: no JSON object in response: %s", raw[:200])
        return {"verdict": "SKIP", "rationale": "unparseable screen output", "symbol": "", "signals": []}
    try:
        parsed = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        log.warning("stage1 json parse failed: %s | preview=%s", e, raw[:200])
        return {"verdict": "SKIP", "rationale": "json parse failed", "symbol": "", "signals": []}

    parsed["verdict"] = (parsed.get("verdict") or "SKIP").upper()
    parsed["symbol"] = (parsed.get("symbol") or "").upper()
    parsed["rationale"] = parsed.get("rationale") or ""
    parsed["signals"] = parsed.get("signals") or []
    return parsed


def chunk_for_telegram(text: str, *, limit: int = 3800) -> list[str]:
    """Split long patearn analysis on paragraph boundaries to fit Telegram's cap."""
    if len(text) <= limit:
        return [text]
    out, buf, cur = [], [], 0
    for para in text.split("\n\n"):
        block = para + "\n\n"
        if cur + len(block) > limit and buf:
            out.append("".join(buf).rstrip())
            buf, cur = [], 0
        buf.append(block)
        cur += len(block)
    if buf:
        out.append("".join(buf).rstrip())
    return out
