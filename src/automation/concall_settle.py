"""CCI settlement (FREE, pure-Python, no LLM) — turns OPEN promises into a measured
track record. For each OPEN concall_guidance row, find the resolving (fy,quarter)
from its source-call period + horizon, and if that quarter has a concall_results
row, grade it: numeric LEVEL targets (revenue ₹cr, margin %) compared directly;
everything else graded on YoY SIGN-MATCH where the claim is directional. capex/
expansion/volume/debt (not in the quarterly P&L) → marked ONGOING, not auto-graded.

**No look-ahead by construction:** a promise settles only once its resolving quarter
has actually been reported. Run AFTER extract, BEFORE concall_scores --rerank
(the D59 contract). Idempotent: re-running re-grades from current results.

CLI: python -m src.automation.concall_settle --symbol RELIANCE | --all
"""

import argparse
import logging
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.concall_settle")

_METRIC = {"revenue": "revenue", "margin": "ebitda_margin"}     # settleable from the quarterly P&L
# claim-text fallback when the LLM mistyped the statement_type (e.g. "double-digit
# revenue growth" tagged 'other'): infer the settleable metric from keywords.
_METRIC_KW = {"revenue": ("revenue", "sales", "topline", "top line", "top-line", "turnover"),
              "margin": ("margin", "ebitda", "opm", "profitabil")}


def _infer_metric(statement_type, claim) -> Optional[str]:
    m = _METRIC.get(statement_type)
    if m:
        return m
    cl = (claim or "").lower()
    for metric, kws in _METRIC_KW.items():
        if any(k in cl for k in kws):
            return metric
    return None


def _implied_growth_pct(claim) -> Optional[float]:
    """A vague-but-quantifiable growth phrase → an implied % floor for magnitude
    grading ("double-digit revenue growth" = ≥10%). India managements lean on these
    instead of a hard number (no Reg-FD); grading on the floor turns a falsely
    lenient directional MET into a correct MISS when they actually undershoot."""
    c = (claim or "").lower()
    if "double-digit" in c or "double digit" in c:
        return 10.0
    if "high single" in c or "high-single" in c:
        return 8.0
    if "mid single" in c or "mid-single" in c:
        return 5.0
    return None
_UP = ("grow", "growth", "increase", "improv", "expand", "higher", "double", "triple", "ramp", "rise", "accelerat", "uptick")
_DOWN = ("reduce", "decline", "lower", "cut", "delever", "deleverage", "fall", "moderat", "soften", "down")
MET_TOL, MISS_TOL = 0.97, 0.90       # revenue level bands; margin uses pp bands below


def _qadd(fy: int, q: int, n: int):
    t = fy * 4 + (q - 1) + n
    return t // 4, t % 4 + 1


def _resolve(rq_fy: int, rq_q: int, horizon: Optional[str]):
    """Reported quarter (rq) + horizon → the (fy,quarter) that settles the promise."""
    h = horizon or "next_q"
    if h == "this_q":
        return _qadd(rq_fy, rq_q, 1)            # the quarter in progress at the call
    if h == "next_q":
        return _qadd(rq_fy, rq_q, 2)
    if h == "fy":
        fy1, _ = _qadd(rq_fy, rq_q, 1)
        return fy1, 4                            # FY-end of the in-progress year
    if h == "multiyear_3_5y":
        return _qadd(rq_fy, rq_q, 12)
    return _qadd(rq_fy, rq_q, 2)


def settle_symbol(conn, symbol: str) -> dict:
    cmap = {r["period_label"]: (r["fy"], r["quarter"])
            for r in conn.execute("SELECT period_label, fy, quarter FROM concalls WHERE symbol=?", (symbol,)).fetchall()}
    results = {(r["fy"], r["quarter"]): dict(r) for r in conn.execute(
        "SELECT fy, quarter, period_label, revenue, ebitda_margin, rev_yoy_pct, ebitda_yoy_pct "
        "FROM concall_results WHERE symbol=?", (symbol,)).fetchall()}
    out = {"settled": 0, "met": 0, "missed": 0, "partial": 0, "ongoing": 0}

    for g in conn.execute("SELECT * FROM concall_guidance WHERE symbol=? AND status='OPEN'", (symbol,)).fetchall():
        st = g["statement_type"]
        metric = _infer_metric(st, g["claim_text"])
        if not metric:
            if (g["horizon"] or "") == "multiyear_3_5y":
                conn.execute("UPDATE concall_guidance SET status='ONGOING', updated_at=datetime('now') WHERE id=?", (g["id"],))
                out["ongoing"] += 1
            continue
        src = cmap.get(g["source_period"])
        if not src or not src[0]:
            continue
        rfy, rq = _resolve(src[0], src[1], g["horizon"])
        res = results.get((rfy, rq))
        if not res:
            continue                              # not reported yet → stays OPEN (no look-ahead)

        actual = res.get(metric)
        yoy = res.get("rev_yoy_pct" if metric == "revenue" else "ebitda_yoy_pct")
        tgt, unit = g["quantified_target"], (g["unit"] or "").lower()
        status, var = None, None

        if metric == "revenue" and tgt is not None and unit in ("rs_cr", "cr") and actual is not None and tgt:
            var = round(100.0 * (actual - tgt) / abs(tgt), 1)
            status = "MET" if actual >= tgt * MET_TOL else ("MISSED" if actual < tgt * MISS_TOL else "PARTIAL")
        elif metric == "revenue" and tgt is not None and "%" in unit and yoy is not None:
            var = round(yoy - tgt, 1)            # growth-MAGNITUDE promise ("grow 15%") vs actual YoY
            status = "MET" if yoy >= tgt * 0.9 else ("MISSED" if yoy < tgt * 0.7 else "PARTIAL")
        elif metric == "revenue" and tgt is None and yoy is not None and _implied_growth_pct(g["claim_text"]) is not None:
            imp = _implied_growth_pct(g["claim_text"])   # "double-digit growth" → ≥10% floor
            var = round(yoy - imp, 1)
            status = "MET" if yoy >= imp * 0.9 else ("MISSED" if yoy < imp * 0.7 else "PARTIAL")
        elif metric == "margin" and tgt is not None and ("%" in unit or unit == "") and actual is not None:
            var = round(actual - tgt, 1)          # percentage points
            status = "MET" if actual >= tgt - 0.5 else ("MISSED" if actual < tgt - 2.0 else "PARTIAL")
        else:                                     # directional sign-match
            claim = (g["claim_text"] or "").lower()
            up, down = any(w in claim for w in _UP), any(w in claim for w in _DOWN)
            if (up or down) and yoy is not None:
                got_up = yoy > 0
                status = "MET" if ((up and got_up) or (down and not got_up)) else "MISSED"
                var = yoy

        if status:
            conn.execute("UPDATE concall_guidance SET status=?, resolved_period=?, variance_pct=?, "
                         "updated_at=datetime('now') WHERE id=?", (status, res["period_label"], var, g["id"]))
            out["settled"] += 1
            out[status.lower()] = out.get(status.lower(), 0) + 1
    if out["settled"] or out["ongoing"]:
        log.info("%s: %s", symbol, out)
    return out


def run(symbol: Optional[str] = None) -> int:
    with get_conn() as conn:
        syms = [symbol.upper()] if symbol else [
            r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concall_guidance").fetchall()]
        return sum(settle_symbol(conn, s)["settled"] for s in syms)


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI promise settlement (free, no LLM)")
    ap.add_argument("--symbol")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not (args.symbol or args.all):
        ap.error("give --symbol SYM or --all")
    n = run(args.symbol if args.symbol else None)
    log.info("settled %d promises", n)


if __name__ == "__main__":
    main()
