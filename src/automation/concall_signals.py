"""Concall forward-looking statements as a QUERYABLE / SCANNABLE signal table.

`concall_guidance` holds every forward-looking statement management made, by statement_type
(capex, expansion, debt_reduction, volume, new_product, demand_outlook, ...). The cross-sectional
backtest (`cci_backtest --mode scan`) showed the GROWTH-INTENT content carries a real forward-return
tilt (debt_reduction +2.8% / volume +2.3% / new_product +1.8% / capex +1.5% at 3m) — unlike
'credibility', which falsified. This module materializes those statements into a clean, indexed
`concall_signals` table you can scan/screen, with the ₹-amounts NORMALIZED: the raw
`quantified_target` had unit bugs ('$50 billion' / 'INR 10.4 billion' / 'Rs 10 Billion' were stored
as raw-rupee integers mislabeled `Rs_cr`), so the headline amount is re-parsed from the claim text
to a consistent ₹-crore.

Isolated module (own `ensure_schema`, no db.py edit). Rebuild is idempotent (full refresh).

CLI:
  python -m src.automation.concall_signals --rebuild
  python -m src.automation.concall_signals --type capex --min-cr 500 --since 2024
  python -m src.automation.concall_signals --symbol POLYCAB
  python -m src.automation.concall_signals --growth --since 2025     # the growth-intent screen
  python -m src.automation.concall_signals --stats
"""
from __future__ import annotations

import argparse
import logging
import re
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.concall_signals")

# statement_types with a positive forward tilt in the scan (the "growth / deleveraging intent")
GROWTH_TYPES = ("debt_reduction", "volume", "new_product", "capex", "expansion")

# fx -> INR (approximate, for normalising the rare $/€/£ headline numbers to one currency)
_FX = {"$": 83.0, "usd": 83.0, "us$": 83.0, "u.s.$": 83.0, "dollar": 83.0, "dollars": 83.0,
       "€": 90.0, "eur": 90.0, "euro": 90.0, "£": 105.0, "gbp": 105.0}

# scale word -> multiplier to ₹ CRORE (1 crore = 1e7; 1 billion = 100 cr; 1 lakh = 0.01 cr)
_SCALE = {"trillion": 100000.0, "billion": 100.0, "bn": 100.0, "crore": 1.0, "crores": 1.0,
          "cr": 1.0, "million": 0.1, "millions": 0.1, "mn": 0.1, "lakh": 0.01, "lakhs": 0.01}

_MONEY_RE = re.compile(
    r"(?P<cur>Rs\.?|INR|₹|US\$|U\.S\.\$|\$|USD|EUR|€|GBP|£|dollars?)?\s*"
    r"(?P<num>[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
    r"(?P<scale>trillion|billion|bn|crores|crore|cr|lakhs|lakh|millions|million|mn)",
    re.I)

# An explicit capex/expansion PULLBACK — deliberately TIGHT, and only consulted for capex/expansion
# statements (a 'revenue'/'margin' line is never a pullback). Either a negation tied to capex/capacity
# ("no capex planned", "negligible capex", "no major expansion"), or a clear winddown verb. NOT generic
# words: 'Consolidated' is the ACCOUNTING term (not "consolidating operations"), and 'reduce debt' is a
# POSITIVE deleveraging signal — both used to misfire.
_PULLBACK_RE = re.compile(
    r"\b(no|nil|negligible|minimal|without|zero)\b[^.]{0,40}\b(capex|capital expenditure|"
    r"capital expense|expansion|expand|capacit|investment|greenfield|brownfield)\b"
    r"|\b(defer|deferr|postpon|pause|paus|halt|shelv|no further|no major|no significant|"
    r"behind us|wound down|winding down|consolidating operations|focus on consolidat)\b",
    re.I)


def parse_amount_cr(text: Optional[str]) -> Optional[float]:
    """Re-parse the headline monetary amount from a claim/evidence to ₹ CRORE (the largest plausible
    figure with an explicit scale word). Bare numbers without a scale word are skipped (too ambiguous).
    Returns None for non-monetary statements (capacity in MT/GW/stores etc.)."""
    if not text:
        return None
    best = None
    for m in _MONEY_RE.finditer(text):
        try:
            val = float(m.group("num").replace(",", ""))
        except ValueError:
            continue
        mult = _SCALE.get(m.group("scale").lower())
        if not mult:
            continue
        cr = val * mult
        cur = (m.group("cur") or "").lower().strip()
        if cur in _FX:
            cr *= _FX[cur]
        if cr > 0 and (best is None or cr > best):
            best = cr
    return round(best, 1) if best is not None else None


def _polarity(text: Optional[str], st: str, direction: Optional[str] = None) -> int:
    """+1 growth/expand · -1 capex/expansion PULLBACK · 0 neutral. PREFERS the LLM-derived
    `direction` (concall_direction — the model that read the sentence); the tightened regex is a
    fallback only until a row is backfilled. Pullback nuance applies ONLY to capex/expansion, so
    'Consolidated revenue' (accounting) and 'reduce debt' (positive deleveraging) never misfire."""
    if st in ("capex", "expansion"):
        if direction in ("increase", "maintain", "decrease", "none"):     # LLM-derived intent
            return -1 if direction == "decrease" else (1 if direction == "increase" else 0)
        return -1 if (text and _PULLBACK_RE.search(text)) else 1           # regex fallback
    return 1 if st in GROWTH_TYPES else 0


_SCHEMA = """
CREATE TABLE IF NOT EXISTS concall_signals (
    symbol            TEXT NOT NULL,
    period_label      TEXT,
    year              INTEGER,
    month             INTEGER,
    statement_type    TEXT,
    horizon           TEXT,
    amount_cr         REAL,        -- normalised ₹ crore (monetary statements only; NULL = capacity/other)
    unit_raw          TEXT,
    quantified_raw    REAL,        -- the original (buggy) quantified_target, kept for audit
    is_growth_intent  INTEGER,     -- statement_type in GROWTH_TYPES
    polarity          INTEGER,     -- +1 grow/expand · -1 pullback ('no capex') · 0 neutral
    confidence_language TEXT,
    claim_text        TEXT,
    evidence          TEXT
);
CREATE INDEX IF NOT EXISTS idx_csig_sym    ON concall_signals(symbol, year, month);
CREATE INDEX IF NOT EXISTS idx_csig_type   ON concall_signals(statement_type, year, month);
CREATE INDEX IF NOT EXISTS idx_csig_amount ON concall_signals(amount_cr);
CREATE INDEX IF NOT EXISTS idx_csig_growth ON concall_signals(is_growth_intent, year, month);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


def rebuild() -> int:
    """Full idempotent refresh from concall_guidance (joined to concalls for the as-of year/month)."""
    with get_conn() as conn:
        ensure_schema(conn)
        try:
            conn.execute("ALTER TABLE concall_guidance ADD COLUMN direction TEXT")
        except Exception:  # noqa: BLE001 - column exists (added by concall_direction)
            pass
        rows = conn.execute(
            "SELECT g.symbol, g.source_period, c.concall_year y, c.concall_month m, g.statement_type st, "
            "g.horizon, g.quantified_target qt, g.unit, g.confidence_language cl, g.claim_text, g.evidence, "
            "g.direction "
            "FROM concall_guidance g LEFT JOIN concalls c "
            "  ON c.symbol=g.symbol AND c.period_label=g.source_period").fetchall()
        conn.execute("DELETE FROM concall_signals")
        n = 0
        for r in rows:
            st = r["st"] or "other"
            amount = parse_amount_cr(r["claim_text"]) or parse_amount_cr(r["evidence"])
            conn.execute(
                "INSERT INTO concall_signals (symbol, period_label, year, month, statement_type, horizon, "
                "amount_cr, unit_raw, quantified_raw, is_growth_intent, polarity, confidence_language, "
                "claim_text, evidence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r["symbol"], r["source_period"], r["y"], r["m"], st, r["horizon"], amount, r["unit"],
                 r["qt"], 1 if st in GROWTH_TYPES else 0, _polarity(r["claim_text"], st, r["direction"]),
                 r["cl"], r["claim_text"], r["evidence"]))
            n += 1
        conn.commit()
    log.info("concall_signals rebuilt: %d statements", n)
    return n


def scan(conn, *, stype=None, symbol=None, min_cr=None, since_year=None, growth=False,
         polarity=None, limit=40) -> list:
    q = "SELECT symbol, period_label, year, month, statement_type, amount_cr, polarity, claim_text " \
        "FROM concall_signals WHERE 1=1"
    args: list = []
    if growth:
        q += " AND is_growth_intent=1"
    if stype:
        q += " AND statement_type=?"; args.append(stype)
    if symbol:
        q += " AND symbol=?"; args.append(symbol.upper())
    if min_cr is not None:
        q += " AND amount_cr>=?"; args.append(min_cr)
    if since_year is not None:
        q += " AND year>=?"; args.append(since_year)
    if polarity is not None:
        q += " AND polarity=?"; args.append(polarity)
    q += " ORDER BY (amount_cr IS NULL), amount_cr DESC, year DESC, month DESC LIMIT ?"
    args.append(limit)
    return conn.execute(q, args).fetchall()


def main() -> None:
    ap = argparse.ArgumentParser(description="Concall forward-looking statements — queryable signal table")
    ap.add_argument("--rebuild", action="store_true", help="(re)materialise concall_signals from concall_guidance")
    ap.add_argument("--type", dest="stype", help="filter by statement_type (capex, expansion, debt_reduction, ...)")
    ap.add_argument("--symbol", help="filter by symbol")
    ap.add_argument("--min-cr", type=float, help="only statements with a normalised ₹ amount >= this (crore)")
    ap.add_argument("--since", type=int, help="only concalls in/after this year")
    ap.add_argument("--growth", action="store_true", help="only growth-intent types (the screen)")
    ap.add_argument("--pullback", action="store_true", help="only explicit pullbacks ('no capex', negligible)")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--stats", action="store_true", help="coverage stats")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.rebuild:
        print(f"rebuilt {rebuild()} statements into concall_signals")
        return
    with get_conn() as conn:
        ensure_schema(conn)
        if args.stats:
            q = lambda s: conn.execute(s).fetchone()[0]
            print("rows                :", q("SELECT COUNT(*) FROM concall_signals"))
            print("with ₹ amount       :", q("SELECT COUNT(*) FROM concall_signals WHERE amount_cr IS NOT NULL"))
            print("growth-intent rows  :", q("SELECT COUNT(*) FROM concall_signals WHERE is_growth_intent=1"))
            print("pullback (no-capex) :", q("SELECT COUNT(*) FROM concall_signals WHERE polarity=-1"))
            print("by type (growth):", dict(conn.execute(
                "SELECT statement_type, COUNT(*) FROM concall_signals WHERE is_growth_intent=1 "
                "GROUP BY statement_type ORDER BY 2 DESC").fetchall()))
            return
        rows = scan(conn, stype=args.stype, symbol=args.symbol, min_cr=args.min_cr,
                    since_year=args.since, growth=args.growth,
                    polarity=(-1 if args.pullback else None), limit=args.limit)
        print(f"{'symbol':12} {'period':9} {'type':14} {'₹cr':>10}  pol  claim")
        for r in rows:
            amt = f"{r['amount_cr']:,.0f}" if r["amount_cr"] is not None else "-"
            pol = {1: "+", -1: "-", 0: " "}.get(r["polarity"], " ")
            print(f"{r['symbol']:12} {r['period_label'] or '':9} {r['statement_type']:14} {amt:>10}  {pol:^3}  "
                  f"{(r['claim_text'] or '')[:64]}")
        print(f"\n({len(rows)} rows)")


if __name__ == "__main__":
    main()
