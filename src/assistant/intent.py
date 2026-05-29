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

from src.core.llm import client
from src.core.settings import settings

log = logging.getLogger("hermes.intent")

INTENT_SYSTEM = (
    "You classify what a stock-analysis bot user wants from a single plain-text "
    "message. Output STRICT JSON only — no prose, no markdown fence."
)

INTENT_USER_TEMPLATE = """Classify the user's message into one of these intents and extract the NSE ticker if a specific stock is clearly named.

Output a JSON object with EXACTLY these keys:

  "intent": one of:
      SCORE  - user wants the patearn rule-based score / fundamental quality reading
      FLOW   - user wants the delivery-flow / DVPT / institutional positioning signal
      BOTH   - user wants a full picture of a stock (any general "what about X?" / "look at X" / "any thoughts on X")
      CHAT   - general conversation, follow-up question, multi-stock comparison, or anything not a single-stock data request

  "ticker": NSE listing symbol of the stock if one is clearly named (uppercase, no .NS suffix). null otherwise.

Examples:
  "what's pixtrans?"                     -> {"intent":"BOTH","ticker":"PIXTRANS"}
  "look at reliance"                     -> {"intent":"BOTH","ticker":"RELIANCE"}
  "score tata motors"                    -> {"intent":"SCORE","ticker":"TATAMOTORS"}
  "is tata steel a good buy"             -> {"intent":"SCORE","ticker":"TATASTEEL"}
  "show me delivery flow on hdfc bank"   -> {"intent":"FLOW","ticker":"HDFCBANK"}
  "any institutional buying in infy?"    -> {"intent":"FLOW","ticker":"INFY"}
  "smart money in adani green"           -> {"intent":"FLOW","ticker":"ADANIGREEN"}
  "hi how are you"                       -> {"intent":"CHAT","ticker":null}
  "what should I make of this data"      -> {"intent":"CHAT","ticker":null}
  "compare infy and tcs"                 -> {"intent":"CHAT","ticker":null}

Rules:
- Use the most common NSE listing symbol (RELIANCE, HDFCBANK, TATAMOTORS, INFY, TCS, etc.). Don't make up tickers.
- If two or more stocks are mentioned, classify as CHAT.
- If the message is a follow-up question about previously shown data, classify as CHAT.
- If you're not sure of the NSE ticker, classify as CHAT.

User message:
{message}
"""


def classify(message: str) -> dict:
    """Return {"intent": str, "ticker": str | None}.

    On any failure, fall through to CHAT so the user gets a reply rather than
    a stuck command.
    """
    try:
        response = client().messages.create(
            model=settings.fast_model,
            max_tokens=80,
            system=INTENT_SYSTEM,
            messages=[
                {"role": "user", "content": INTENT_USER_TEMPLATE.format(message=message)}
            ],
        )
    except Exception as e:
        log.warning("intent classification call failed: %s", e)
        return {"intent": "CHAT", "ticker": None}

    raw = response.content[0].text.strip()
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
    if intent not in ("SCORE", "FLOW", "BOTH", "CHAT"):
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
