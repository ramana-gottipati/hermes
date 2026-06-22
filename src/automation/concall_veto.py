"""CCI forensic veto gate (debate rank #1) — the un-spinnable spine.

Credibility cannot be scored from the suspect's own testimony: a glib fraud runs
a smooth, confident, numeric call right up to collapse (Manpasand, Vakrangee,
DHFL, Yes Bank, Coffee Day...). So an EXOGENOUS integrity gate sits IN FRONT of
the credibility engine and can force tier=D regardless of how good the call
sounded. We do NOT build a new forensic platform — we WIRE the disqualifiers the
pt14 engine already computes (resources/patearn/SKILL.md) plus the directly-held
promoter pledge:

  - promoter pledge >= PLEDGE_VETO  -> UNIVERSAL hard veto (even for financials)
  - pt14 hard_disqualified           -> veto, EXCEPT cash-flow/leverage reasons are
                                        sector-SUPPRESSED for banks/NBFCs and heavy-
                                        capex cyclicals (negative CFO is structural
                                        there, not a fraud tell) — Ramana's A3 ruling.

Pure SQL over existing tables (`fundamentals`, `pattern_scores`). No LLM.
"""

from __future__ import annotations

from typing import Optional

PLEDGE_VETO = 20.0          # promoter pledge % at/above which the name is vetoed (universal)

# sectors where cash-flow / leverage disqualifiers are SUPPRESSED (structural, not fraud)
_FIN_SECTORS = ("bank", "financ", "nbfc", "housing finance", "insurance", "capital market", "broking")
_HEAVY_CAPEX = ("cement", "steel", "power", "metal", "infrastructure", "construction",
                "oil", "gas", "mining", "shipping", "telecom", "realty", "real estate")
_CASHFLOW_REASON = ("cfo", "cash flow", "cash-flow", "operating cash", "cfo/pat",
                    "negative cash", "debt", "leverage", "d/e", "working capital")


def _sector_suppresses_cashflow(sector: Optional[str]) -> bool:
    s = (sector or "").lower()
    return any(k in s for k in _FIN_SECTORS) or any(k in s for k in _HEAVY_CAPEX)


def compute_veto(conn, symbol: str, sector: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """Return (veto_active, veto_reason) for a symbol from exogenous integrity signals.

    Sector (for the cash-flow suppression rule) is auto-resolved from
    stock_signals.primary_sector when not supplied — this reference to the
    price-derived table lives HERE (the integrity gate), never in the credibility
    scorer, so the scorer's price↔credibility firewall stays clean.
    """
    reasons: list[str] = []
    if sector is None:
        srow = conn.execute(
            "SELECT primary_sector FROM stock_signals WHERE symbol=? AND primary_sector IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 1", (symbol,)
        ).fetchone()
        sector = srow["primary_sector"] if srow else None

    # 1. Promoter pledge — the highest-precision, un-spinnable India signal (universal).
    fu = conn.execute(
        "SELECT promoter_pledge FROM fundamentals WHERE symbol=?", (symbol,)
    ).fetchone()
    pledge = fu["promoter_pledge"] if fu else None
    if pledge is not None and pledge >= PLEDGE_VETO:
        reasons.append(f"promoter pledge {pledge:.0f}%")

    # 2. pt14's existing hard disqualifiers (auditor exit, CFO/PAT, RPT, ...).
    ps = conn.execute(
        "SELECT hard_disqualified, disqualifier_reasons FROM pattern_scores "
        "WHERE symbol=? ORDER BY scored_at DESC LIMIT 1", (symbol,)
    ).fetchone()
    if ps and ps["hard_disqualified"]:
        dr = (ps["disqualifier_reasons"] or "").strip()
        drl = dr.lower()
        is_cashflow = any(k in drl for k in _CASHFLOW_REASON)
        if is_cashflow and _sector_suppresses_cashflow(sector):
            pass                       # structural negative CFO for a lender/heavy-capex name — not a veto
        else:
            reasons.append(f"pt14: {dr or 'hard-disqualified'}")

    active = bool(reasons)
    return active, ("; ".join(reasons) if active else None)


def veto_map(conn, symbols: list[str], sectors: Optional[dict] = None) -> dict[str, tuple[bool, Optional[str]]]:
    """Batch compute_veto for the scorer. sectors maps symbol -> sector (optional)."""
    sectors = sectors or {}
    return {s: compute_veto(conn, s, sectors.get(s)) for s in symbols}
