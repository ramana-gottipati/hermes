"""Intent classifier for natural-language Telegram input.

When the user types plain text (not a slash command), this module classifies
what they want and extracts the NSE ticker if one is named. Lets the user
ask questions like "what's pixtrans?" or "score reliance" without remembering
slash command syntax.

Cost: 1 Haiku call per message (~₹0.10). Trivially under the spend cap.

Intents:
  SCORE  — user wants the patearn rule-based score / quality reading
  FLOW   — user wants the DVPT / institutional-flow signal
  BOTH   — user wants a full picture ("what about X?" / "look at X")
  CHAT   — general conversation, no specific stock signal needed
"""

import json
import logging
import re

from src.core.llm_router import call_classifier

log = logging.getLogger("hermes.intent")

INTENT_SYSTEM = (
    "You classify what a stock-analysis bot user wants from a single plain-text "
    "message. Output STRICT JSON only — no prose, no markdown fence."
)

INTENT_USER_TEMPLATE = """Classify the user's message into one of these intents and extract the NSE ticker if a specific stock is clearly named.

Output a JSON object with EXACTLY these keys:

  "intent": one of:
      SCORE  - user wants the patearn rule-based score for a SINGLE NAMED stock
      FLOW   - user wants the DVPT / delivery flow signal for a SINGLE NAMED stock
      BOTH   - user wants a full picture of a SINGLE NAMED stock (general "what about X?", "look at X", etc.)
      SCAN   - user wants TOP STOCKS ACROSS THE MARKET by institutional-flow signal — questions
               like "where did smart money go?", "top accumulation today", "biggest institutional buys",
               "exceptional delivery flows", "high conviction names today". No specific stock named.
      CHAT   - general conversation, follow-up question about already-shown data, multi-stock comparison
               (not a top-N scan), or anything not a single-stock or market-scan data request.

  "ticker": NSE listing symbol if one is clearly named (uppercase, no .NS suffix). null otherwise.
            Always null for SCAN and CHAT.

PRIORITY RULE: If a single recognisable NSE ticker is named anywhere in the message,
strongly prefer SCORE / FLOW / BOTH over CHAT. The user is almost certainly asking about that stock.
Only fall back to CHAT if NO ticker is named or two+ tickers are named.

VOCABULARY SIGNALLING FLOW (these terms mean institutional/delivery signal):
  delivery value per trade · DVPT · per-trade delivery · delivery flow · institutional buying ·
  institutional intensity · institutional positioning · smart money · accumulation · distribution ·
  power deliveries · power delivery · delivery ratio · delivery percentage · delivery quantity trend

VOCABULARY SIGNALLING SCORE (these terms mean fundamental / patearn):
  score · rate · rating · quality · fundamentals · 14 patterns · patearn · ROCE · ROE · multibagger ·
  good buy · investment grade · tier · NS · normalised score

VOCABULARY SIGNALLING BOTH (general questions):
  what's X · look at X · X strategy · X thoughts · analyse X · check X · how is X · X please ·
  about X · pull X · show me X · X data

Examples:
  "what's pixtrans?"                              -> {"intent":"BOTH","ticker":"PIXTRANS"}
  "pixtrans delivery value per trade strategy"    -> {"intent":"FLOW","ticker":"PIXTRANS"}
  "pixtrans DVPT"                                 -> {"intent":"FLOW","ticker":"PIXTRANS"}
  "power deliveries on hdfc bank"                 -> {"intent":"FLOW","ticker":"HDFCBANK"}
  "smart money pixtrans"                          -> {"intent":"FLOW","ticker":"PIXTRANS"}
  "per-trade delivery value on infy"              -> {"intent":"FLOW","ticker":"INFY"}
  "institutional intensity on tata steel"         -> {"intent":"FLOW","ticker":"TATASTEEL"}
  "accumulation pattern in adani green"           -> {"intent":"FLOW","ticker":"ADANIGREEN"}
  "look at reliance"                              -> {"intent":"BOTH","ticker":"RELIANCE"}
  "any thoughts on tata motors"                   -> {"intent":"BOTH","ticker":"TATAMOTORS"}
  "analyse infy"                                  -> {"intent":"BOTH","ticker":"INFY"}
  "pull data on tcs"                              -> {"intent":"BOTH","ticker":"TCS"}
  "score tata motors"                             -> {"intent":"SCORE","ticker":"TATAMOTORS"}
  "is tata steel a good buy"                      -> {"intent":"SCORE","ticker":"TATASTEEL"}
  "rate hdfc bank"                                -> {"intent":"SCORE","ticker":"HDFCBANK"}
  "ROCE on infy"                                  -> {"intent":"SCORE","ticker":"INFY"}

  Market-wide SCAN examples (no specific stock named):
  "where did the smart money go yesterday"        -> {"intent":"SCAN","ticker":null}
  "where is smart money buying today"             -> {"intent":"SCAN","ticker":null}
  "top accumulation today"                        -> {"intent":"SCAN","ticker":null}
  "biggest institutional buys yesterday"          -> {"intent":"SCAN","ticker":null}
  "show me the highest delivery flows"            -> {"intent":"SCAN","ticker":null}
  "exceptional delivery today"                    -> {"intent":"SCAN","ticker":null}
  "high conviction names today"                   -> {"intent":"SCAN","ticker":null}
  "top movers in delivery"                        -> {"intent":"SCAN","ticker":null}
  "stocks with institutional intensity"           -> {"intent":"SCAN","ticker":null}
  "best delivery flows yesterday"                 -> {"intent":"SCAN","ticker":null}
  "any ATH today"                                 -> {"intent":"SCAN","ticker":null}
  "all-time high delivery"                        -> {"intent":"SCAN","ticker":null}
  "ATH DVPT today"                                -> {"intent":"SCAN","ticker":null}
  "rank SS stocks"                                -> {"intent":"SCAN","ticker":null}
  "show me SS triggers"                           -> {"intent":"SCAN","ticker":null}
  "any supreme triggers"                          -> {"intent":"SCAN","ticker":null}
  "discount entry candidates"                     -> {"intent":"SCAN","ticker":null}
  "stocks above all power baselines"              -> {"intent":"SCAN","ticker":null}
  "near-break stocks today"                       -> {"intent":"SCAN","ticker":null}
  "stocks kissing P3M"                            -> {"intent":"SCAN","ticker":null}
  "about to cross power baselines"                -> {"intent":"SCAN","ticker":null}

  General chat (no data lookup, no specific stock):
  "hi how are you"                                -> {"intent":"CHAT","ticker":null}
  "what should I make of this data"               -> {"intent":"CHAT","ticker":null}
  "what does the ratio mean"                      -> {"intent":"CHAT","ticker":null}
  "compare infy and tcs"                          -> {"intent":"CHAT","ticker":null}

Rules:
- Use the most common NSE listing symbol (RELIANCE, HDFCBANK, TATAMOTORS, INFY, TCS, PIXTRANS, etc.).
  Don't make up tickers. If you don't know the NSE symbol, classify as CHAT.
- If two or more stocks are explicitly named, classify as CHAT (we don't compare in this command).
- Follow-up questions about an earlier message (without naming a stock) -> CHAT.
- Otherwise: a named ticker means SCORE, FLOW, or BOTH — never CHAT.

User message:
{message}
"""


# Fast-path regex: a single uppercase NSE-shaped token = direct BOTH lookup.
# Catches "BANDHANBNK", "RELIANCE", "PIXTRANS", "INFY", "TCS", etc.
# Robust against intent-classifier misses AND menu_pending state loss (D30).
# Examples that match: BANDHANBNK, RELIANCE, INFY, PIXTRANS, TATAMOTORS, HDFCBANK
# Examples that don't:  reliance (lowercase), Hello, "BANDHAN BANK" (has space),
#                       AB (too short), M&M (special char — known edge case)
_BARE_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{2,14}$")


def classify(message: str) -> dict:
    """Return {"intent": str, "ticker": str | None}.

    Fast-path: if the entire message is a single uppercase NSE-shaped token,
    skip the LLM classifier and route to BOTH directly. This is robust against
    classifier misses (e.g. "BANDHANBNK" alone wouldn't always be recognised)
    and against menu_pending state loss in the Telegram menu flow.

    On any LLM failure, fall through to CHAT so the user gets a reply rather
    than a stuck command.
    """
    text = (message or "").strip()
    if _BARE_TICKER_RE.match(text):
        log.info(
            "intent: shortcut BOTH ticker=%s (single uppercase NSE-shaped token; no LLM call)",
            text,
        )
        return {"intent": "BOTH", "ticker": text}

    try:
        raw_response, provider = call_classifier(
            system=INTENT_SYSTEM,
            user_msg=INTENT_USER_TEMPLATE.format(message=message),
            max_tokens=80,
        )
    except Exception as e:
        log.warning("intent classification call failed (both providers): %s", e)
        return {"intent": "CHAT", "ticker": None}

    log.debug("intent classifier provider=%s", provider)
    raw = raw_response.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s, e = raw.find("{"), raw.rfind("}")
    if s == -1 or e == -1:
        log.warning("intent: no JSON object in response: %s", raw[:200])
        return {"intent": "CHAT", "ticker": None}
    try:
        parsed = json.loads(raw[s : e + 1])
    except json.JSONDecodeError:
        return {"intent": "CHAT", "ticker": None}

    intent = (parsed.get("intent") or "CHAT").upper()
    if intent not in ("SCORE", "FLOW", "BOTH", "SCAN", "CHAT"):
        intent = "CHAT"
    ticker = parsed.get("ticker")
    if ticker:
        ticker = str(ticker).upper().strip()
        # Strip common suffixes the classifier might emit despite instructions
        for suffix in (".NS", ".BO", "-EQ"):
            if ticker.endswith(suffix):
                ticker = ticker[: -len(suffix)]
    log.info(
        "intent: %s ticker=%s for msg: %s",
        intent, ticker, message[:80].replace("\n", " "),
    )
    return {"intent": intent, "ticker": ticker}
