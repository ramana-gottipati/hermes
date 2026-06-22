"""Concall Intelligence (CCI) — score + rank (MEASURABLE-ONLY, no LLM, no price).

DOCTRINE (Ramana, session 28): rank and compare on **measurable items only**.
Interpretive/LLM content (tone, "credibility feel", concealment opinions) is
INFORMATION shown beside the verdict — never an input to the score or the rank.
This brings CCI in line with DVPT/RS/CPR/pt14, which already rank on computed
numbers. See PROJECT_STATE decision D61.

The composite is therefore built from objective, reproducible inputs only:
  - guidance_accuracy   resolved-promise hit-rate (number-vs-number / directional
                        sign-match). Deterministic, after the settlement pass.
  - quantification_rate % of forward statements that are FALSIFIABLE numbers
                        (HARD/SOFT per cci_normalize) vs vague — the honest,
                        deterministic "transparency". Available now.
  - forensic veto       pledge / auditor-exit / pt14 disqualifier — objective gate.
  - deterioration       count of DETERMINISTIC disclosure-diff flags only (a prior
                        promise lowered/dropped, a metric stopped) — NOT the soft
                        LLM red-flags, which are informational.
The 0-100 behaviour axes from extraction are kept in concall_behavior for DISPLAY
(an "AI read, not ranked") but are NOT read here. Price never enters (firewall).

CLI: --backfill | --symbol SYM | --rerank
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from src.core.db import get_conn
from src.automation.concall_veto import compute_veto
from src.automation.cci_normalize import classify_commitment

log = logging.getLogger("hermes.concall_scores")

# --- tunable weights — re-rank, don't re-extract, to change --------------------
W_GA, W_QR = 0.65, 0.35       # measurable blend: track record + quantification
UNPROVEN_CEILING = 55.0       # no A/A+ without a resolved (settled) track record
VETO_CAP = 15.0
DETER_PEN_PER = 6.0           # composite penalty per recent deterministic deterioration flag
DETER_DOWN = 2               # >= this many recent deterministic flags -> forward = DOWN
RECENT_PERIODS = 4
TIERS = [(80, "A+"), (70, "A"), (55, "B"), (40, "C"), (0, "D")]
_GROWTH_TYPES = ("revenue", "volume", "expansion", "capex", "new_product", "cost_savings", "demand_outlook")
# only these red-flag types are MEASURABLE (produced by the deterministic transcript
# diff, concall_diff.py); the rest are LLM opinions -> informational, not scored.
_DETERMINISTIC_FLAGS = ("guidance_walkback", "stopped_disclosing", "promise_quietly_dropped",
                        "metric_definition_change", "capex_slippage")

# --- FIREWALL: credibility must never be computed from price -------------------
_FIREWALL_TOKENS = ("bhavcopy_rows", "prices_eq", "adj_close", "stock_signals")


def _assert_price_firewall() -> None:
    src = Path(__file__).read_text(encoding="utf-8")
    hits = [t for t in _FIREWALL_TOKENS if src.count(t) > 1]
    if hits:
        raise AssertionError(f"CCI firewall breached: scorer references price source(s) {hits}.")


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _tier(score):
    for thr, name in TIERS:
        if score >= thr:
            return name
    return "D"


def _order_map(conn, symbol):
    rows = conn.execute(
        "SELECT period_label, concall_year, concall_month FROM concalls WHERE symbol=?", (symbol,)).fetchall()
    return {r["period_label"]: (r["concall_year"] or 0, r["concall_month"] or 0) for r in rows}


def _quantification_rate(conn, symbol):
    """% of the symbol's forward statements that are FALSIFIABLE (HARD/SOFT number),
    computed DETERMINISTICALLY from claim_text — the honest 'transparency'."""
    rows = conn.execute("SELECT claim_text FROM concall_guidance WHERE symbol=?", (symbol,)).fetchall()
    if not rows:
        return None, 0
    quant = sum(1 for r in rows if classify_commitment(r["claim_text"]) in ("HARD", "SOFT"))
    return round(100.0 * quant / len(rows), 1), len(rows)


def score_symbol(conn, symbol: str) -> Optional[dict]:
    order = _order_map(conn, symbol)
    keyf = lambda p: order.get(p, (0, 0))
    g_periods = [r["source_period"] for r in conn.execute(
        "SELECT DISTINCT source_period FROM concall_guidance WHERE symbol=?", (symbol,)).fetchall()]
    b_periods = [r["period_label"] for r in conn.execute(
        "SELECT DISTINCT period_label FROM concall_behavior WHERE symbol=?", (symbol,)).fetchall()]
    periods = set(g_periods) | set(b_periods)
    if not periods:
        return None
    as_of = max(periods, key=keyf)

    # --- MEASURABLE inputs only ------------------------------------------------
    veto_active, veto_reason = compute_veto(conn, symbol)

    by = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, COUNT(*) n FROM concall_guidance WHERE symbol=? GROUP BY status", (symbol,)).fetchall()}
    met, missed, partial = by.get("MET", 0), by.get("MISSED", 0), by.get("PARTIAL", 0)
    resolved = met + missed + partial
    ga = (100.0 * (met + 0.5 * partial) / resolved) if resolved else None

    qrate, n_promises = _quantification_rate(conn, symbol)
    qr = qrate if qrate is not None else 0.0

    recent = [p for p, _ in sorted(order.items(), key=lambda kv: kv[1], reverse=True)][:RECENT_PERIODS]
    deter = 0
    if recent:
        qm = ",".join("?" * len(recent))
        fm = ",".join("?" * len(_DETERMINISTIC_FLAGS))
        deter = conn.execute(
            f"SELECT COUNT(*) n FROM concall_redflags WHERE symbol=? AND period_label IN ({qm}) "
            f"AND flag_type IN ({fm})", [symbol, *recent, *_DETERMINISTIC_FLAGS]).fetchone()["n"]

    # --- composite (measurable only) -------------------------------------------
    if ga is not None:
        base = W_GA * ga + W_QR * qr
        unproven = False
    else:
        base = qr                       # no settled track record yet -> lean on quantification
        unproven = True
    composite = _clamp(base - DETER_PEN_PER * deter)
    if unproven:
        composite = min(composite, UNPROVEN_CEILING)
    if veto_active:
        composite = min(composite, VETO_CAP)

    # --- forward direction (measurable: latest guidance shape + flags) ---------
    growth = conn.execute(
        f"SELECT COUNT(*) n FROM concall_guidance WHERE symbol=? AND source_period=? "
        f"AND statement_type IN ({','.join('?' * len(_GROWTH_TYPES))})",
        [symbol, as_of, *_GROWTH_TYPES]).fetchone()["n"]
    if veto_active:
        direction = "AVOID"
    elif deter >= DETER_DOWN:
        direction = "DOWN"
    elif growth >= 1 and (ga is None or ga >= 45):
        direction = "UP"
    elif ga is not None and ga < 45:
        direction = "DOWN"
    else:
        direction = "FLAT"

    n_concalls = len(periods)
    tier = "D" if veto_active else _tier(composite)
    return {
        "symbol": symbol, "as_of_period": as_of,
        "credibility_score": round(ga, 1) if ga is not None else None,   # = the measurable track record
        "guidance_accuracy_score": round(ga, 1) if ga is not None else None,
        "quantification_rate": round(qr, 1),
        "transparency_score": round(qr, 1),                              # measurable transparency = quantification
        "forward_direction": direction, "forward_conviction": round(qr, 1),
        "mispricing_flag": None,
        "credibility_trend": "DETERIORATING" if deter > 0 else "STABLE",
        "composite_score": round(composite, 1), "tier": tier,
        "veto_active": 1 if veto_active else 0, "veto_reason": veto_reason,
        "deterioration_score": float(deter),
        "n_concalls": n_concalls, "n_promises_resolved": resolved,
    }


_UPSERT = """
INSERT INTO concall_scores
  (symbol, as_of_period, as_of_date, credibility_score, guidance_accuracy_score, transparency_score,
   quantification_rate, forward_direction, forward_conviction, mispricing_flag, credibility_trend,
   composite_score, rank, tier, veto_active, veto_reason, deterioration_score, n_concalls,
   n_promises_resolved, last_updated)
VALUES (?,?,datetime('now'),?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
ON CONFLICT(symbol, as_of_period) DO UPDATE SET
  credibility_score=excluded.credibility_score, guidance_accuracy_score=excluded.guidance_accuracy_score,
  transparency_score=excluded.transparency_score, quantification_rate=excluded.quantification_rate,
  forward_direction=excluded.forward_direction, forward_conviction=excluded.forward_conviction,
  mispricing_flag=excluded.mispricing_flag, credibility_trend=excluded.credibility_trend,
  composite_score=excluded.composite_score, rank=excluded.rank, tier=excluded.tier,
  veto_active=excluded.veto_active, veto_reason=excluded.veto_reason,
  deterioration_score=excluded.deterioration_score, n_concalls=excluded.n_concalls,
  n_promises_resolved=excluded.n_promises_resolved, last_updated=datetime('now')
"""


def _write(conn, s: dict, rank: Optional[int]) -> None:
    conn.execute(_UPSERT, (
        s["symbol"], s["as_of_period"], s["credibility_score"], s["guidance_accuracy_score"],
        s["transparency_score"], s["quantification_rate"], s["forward_direction"], s["forward_conviction"],
        s["mispricing_flag"], s["credibility_trend"], s["composite_score"], rank, s["tier"],
        s["veto_active"], s["veto_reason"], s["deterioration_score"], s["n_concalls"],
        s["n_promises_resolved"]))


def run(symbol: Optional[str] = None, rank_all: bool = True) -> int:
    _assert_price_firewall()
    with get_conn() as conn:
        if symbol:
            syms = [symbol.upper()]
        else:
            syms = sorted(set(
                [r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concall_guidance").fetchall()]
                + [r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concall_behavior").fetchall()]))
        scored = [s for s in (score_symbol(conn, x) for x in syms) if s]
        if rank_all and not symbol:
            live = sorted([s for s in scored if not s["veto_active"]],
                          key=lambda d: d["composite_score"], reverse=True)
            rankof = {s["symbol"]: i for i, s in enumerate(live, 1)}
            for s in scored:
                _write(conn, s, rankof.get(s["symbol"]))
        else:
            for s in scored:
                _write(conn, s, None)
        log.info("scored %d symbols%s (measurable-only)", len(scored),
                 " + ranked" if (rank_all and not symbol) else "")
        return len(scored)


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI score + rank (measurable-only, no LLM, no price)")
    ap.add_argument("--symbol")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--rerank", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.symbol:
        run(symbol=args.symbol, rank_all=False)
    elif args.backfill or args.rerank:
        run(rank_all=True)
    else:
        ap.error("give --backfill, --rerank, or --symbol SYM")


if __name__ == "__main__":
    main()
