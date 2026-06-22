"""Classify a bulk/block-deal client name into a participant category.

Pure stdlib (no I/O) so both the production ingester and the research scan can
import it. The strong separator is BEHAVIORAL (a client that buys ≈ sells the same
stock the same day is churn/HFT, net ~zero) — this module adds the NAME layer.

Categories: FUND, INSURER, PENSION, FII, PMS, AIF_VC, HFT_PROP, BROKER_PROP,
CORP, HNI. CHURN = {HFT_PROP, BROKER_PROP} (intraday market-makers / arb desks
that cross the 0.5% bulk threshold via turnover, not accumulation). A "genuine
net buyer" = category NOT in CHURN, net one-sided, net>0.
"""
from __future__ import annotations

# Known Indian HFT / prop / arb desks frequently topping the bulk-deal churn list.
_HFT = (
    "GRAVITON", "JUMP TRADING", "QE SECURITIES", "HRTI", "NK SECURITIES",
    "IRAGE", "MICROCURVES", "JUNOMONETA", "VISTAAR", "ALTIZEN", "GREENBUCKS",
    "PUMA SECURITIES", "L7 HITECH", "RAJASTHAN GLOBAL", "ARPNA", "TOWER RESEARCH",
    "ALPHAGREP", "ESTEE", "DOLAT", "OPTIVER", "QUANT BROKING", "AANSH",
    "PARSOLI", "SOLITAIRE", "PACE FINANCIAL", "CROSSEAS", "MANSI SHARE",
    "PROGRESSIVE SHARE", "SUNG", "GRD SECURITIES", "OMKARA", "SILVERLEAF",
)

CHURN = {"HFT_PROP", "BROKER_PROP"}
GENUINE = {"FUND", "INSURER", "PENSION", "FII", "PMS", "AIF_VC", "CORP", "HNI"}


def classify_client(name: str) -> str:
    if not name:
        return "HNI"
    u = " ".join(str(name).upper().split())
    # genuine institutions (most specific first)
    if any(k in u for k in ("MUTUAL FUND", "ASSET MANAGEMENT", "ASSET MGMT", " AMC", "AMC ", "TRUSTEE")):
        return "FUND"
    if "INSURANCE" in u or "ASSURANCE" in u:
        return "INSURER"
    if "PENSION" in u or "PROVIDENT" in u or "EPFO" in u:
        return "PENSION"
    if "FPI" in u or "FII" in u or ("FOREIGN" in u and "FUND" in u) or "MAURITIUS" in u:
        return "FII"
    if "PORTFOLIO MANAG" in u or u.endswith(" PMS") or " PMS " in u:
        return "PMS"
    if " AIF" in u or "ALTERNAT" in u or "VENTURE" in u or "CAPITAL FUND" in u:
        return "AIF_VC"
    # HFT / prop desks
    if any(h in u for h in _HFT):
        return "HFT_PROP"
    if "LLP" in u and any(k in u for k in ("CAPITAL", "RESEARCH", "TRADING", "QUANT", "MARKET", "SECURITIES")):
        return "HFT_PROP"
    if any(k in u for k in ("SECURITIES", "BROKING", "BROKER", "STOCK", "SHARE", "FINSOL",
                            "TRADELINK", "TRADING", "FINVEST", "FINCAP")):
        return "BROKER_PROP"
    if any(k in u for k in ("LIMITED", " LTD", "PRIVATE", " PVT", "LLP", "VENTURES",
                            "HOLDING", "ENTERPRISE", "INDIA", "TECH", "INVESTMENT")):
        return "CORP"
    return "HNI"   # bare person name (a directional HNI is a genuine accumulator)


def is_churn(name: str) -> bool:
    return classify_client(name) in CHURN
