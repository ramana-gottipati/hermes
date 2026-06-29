"""CCI deterioration diff (FREE, deterministic) — the MEASURABLE avoid-tape feeder.

Diffs a symbol's consecutive concall periods' promise ledger and emits objective
deterioration red-flags:
  - guidance_walkback        a quantified target for a statement_type was LOWERED
  - promise_quietly_dropped  a prior quantified capex/expansion/revenue/margin promise
                             is not reaffirmed in the next call

These are FACTS (a diff of structured numbers), so they are allowed to drive the
rank (unlike the LLM 0-100 reads). Emitted into concall_redflags tagged
model_version='cci-diff-v1' and re-run-safe (its own rows are wiped first).

CLI: python -m src.automation.concall_diff --symbol IDEA | --all
"""

import argparse
import logging
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.concall_diff")

DIFF_VER = "cci-diff-v1"
# only diff HOMOGENEOUS, comparable statement types — never the heterogeneous 'other'
# bucket (mixing ₹-amounts with x-multiples produced garbage "12000000→3" walkbacks).
_COMPARABLE = ("revenue", "margin", "capex", "expansion", "volume", "debt_reduction", "cost_savings")
_DROP_TYPES = ("capex", "expansion", "revenue", "margin", "debt_reduction")   # promises whose disappearance matters

# --- unit commensurability (QA-round2 #2 fix) ---------------------------------
# Bucketing by statement_type alone is NOT enough: within one type the LLM stores
# heterogeneous units (₹cr AND %, gigawatts AND ₹cr, x-multiples, MT, sci-notation
# magnitudes). max()-ing across them and comparing numerically fabricated bogus
# walkbacks ("expansion lowered 5e+10→3" = ₹50bn-cr vs 3 GW; "revenue lowered
# 50000→400" = ₹cr vs %). Fix: collapse each unit string to a coarse UNIT FAMILY and
# only ever compare targets that share a family. When prev/cur don't share a family
# (or the unit can't be classified), we emit NOTHING — suppress the false signal,
# never invent a comparison. This is deterministic and conservative: it can only
# REMOVE spurious walkbacks, never add new ones.
_UNIT_FAMILY = {
    # money (rupees-crore scale) — the free-text Screener LLM spells this ~15 ways
    "rs_cr": "money_inr", "cr": "money_inr", "crore": "money_inr", "crores": "money_inr",
    "crore_rs": "money_inr", "cr_rs": "money_inr", "cr_rs.": "money_inr", "rs": "money_inr",
    "inr_cr": "money_inr", "rs_crore": "money_inr", "rupees_crore": "money_inr", "rs_cr.": "money_inr",
    "rs_lakhs": "money_inr_lakh", "lakh": "money_inr_lakh", "lakhs": "money_inr_lakh", "rs_lakh": "money_inr_lakh",
    "rs_mn": "money_inr_mn", "rs_crores": "money_inr",
    # money (foreign) — a DIFFERENT family: never compare $/£/€ against ₹cr
    "usd_mn": "money_usd", "usd_million": "money_usd", "million_usd": "money_usd", "us_million": "money_usd",
    "usd_bn": "money_usd", "usd_billion": "money_usd", "billion_usd": "money_usd", "usd": "money_usd",
    "usd_cr": "money_usd", "$": "money_usd", "$mn": "money_usd", "$bn": "money_usd", "us$": "money_usd",
    "eur_mn": "money_eur", "eur_million": "money_eur", "eur_cr": "money_eur", "eur": "money_eur", "€": "money_eur",
    "gbp_mn": "money_gbp", "gbp_million": "money_gbp", "£_mn": "money_gbp", "£": "money_gbp",
    # ratios / percentages (margins, growth %, bps are pp-scale, NOT money)
    "%": "pct", "pct": "pct", "percent": "pct", "percentage": "pct",
    "bps": "bps", "basis_points": "bps", "basis points": "bps", "bp": "bps",
    "x": "multiple", "x_multiple": "multiple", "times": "multiple",
    # physical capacity / volume — each is its own family (GW != MT != units != stores)
    "gw": "power_gw", "gigawatt": "power_gw", "gigawatts": "power_gw", "mw": "power_mw", "megawatt": "power_mw",
    "megawatts": "power_mw", "gwh": "energy_gwh", "mwh": "energy_mwh",
    "mt": "mass_mt", "mtpa": "mass_mt", "mmtpa": "mass_mt", "kt": "mass_kt", "ktpa": "mass_kt",
    "tonnes": "mass_t", "tons": "mass_t", "tonne": "mass_t", "ton": "mass_t", "kg": "mass_kg",
    "units": "count_units", "million": "count_million", "mn": "count_million", "billion": "count_billion",
    "stores": "count_stores", "branches": "count_branches", "outlets": "count_outlets",
}


def _unit_family(unit) -> Optional[str]:
    """Coarse unit FAMILY for commensurability, or None when unclassifiable.

    Returns None for blank/unknown units so the caller treats them as
    not-comparable (we refuse to compare anything we can't bucket)."""
    u = (unit or "").strip().lower()
    if not u or u in ("null", "none", "-"):
        return None
    return _UNIT_FAMILY.get(u)


# Implausible money magnitude → an EXTRACTION artefact, not a real target. No single
# Indian-company promise is ≥ ₹10 lakh crore (1e6 ₹cr exceeds the largest market caps);
# values that large are the LLM mis-scaling "billion"/"trillion" into the ₹cr field and
# render as sci-notation ("revenue lowered 1e+09→1000"). Treat them like an
# unclassifiable unit — drop from the diff so a walkback never rests on garbage.
# JUDGEMENT CALL (flagged for analyst): bound set at 1e6 ₹cr as a conservative ceiling.
_MONEY_INR_FAMILIES = ("money_inr", "money_inr_lakh", "money_inr_mn")
_MONEY_INR_MAX_CR = 1_000_000.0


def _implausible_money(fam: Optional[str], target: float) -> bool:
    return fam in _MONEY_INR_FAMILIES and target is not None and abs(target) >= _MONEY_INR_MAX_CR


def _flag(conn, symbol, period, flag_type, severity, evidence, prior):
    conn.execute(
        "INSERT INTO concall_redflags (symbol, period_label, flag_type, severity, evidence, "
        "period_first_seen, prior_period, model_version) VALUES (?,?,?,?,?,?,?,?)",
        (symbol, period, flag_type, severity, evidence, period, prior, DIFF_VER))


def diff_symbol(conn, symbol: str) -> int:
    order = {r["period_label"]: (r["concall_year"] or 0, r["concall_month"] or 0)
             for r in conn.execute("SELECT period_label, concall_year, concall_month FROM concalls WHERE symbol=?", (symbol,)).fetchall()}
    periods = sorted({r["source_period"] for r in conn.execute(
        "SELECT DISTINCT source_period FROM concall_guidance WHERE symbol=?", (symbol,)).fetchall()},
        key=lambda p: order.get(p, (0, 0)))
    if len(periods) < 2:
        return 0
    conn.execute("DELETE FROM concall_redflags WHERE symbol=? AND model_version=?", (symbol, DIFF_VER))

    def by_type_unit(period):
        """{(statement_type, unit_family): [targets]} — bucket by BOTH the type and a
        commensurable unit family so we never max()/compare across different units."""
        d: dict[tuple, list] = {}
        for r in conn.execute(
            "SELECT statement_type, quantified_target, unit FROM concall_guidance WHERE symbol=? AND source_period=?",
            (symbol, period)).fetchall():
            if r["quantified_target"] is None:
                continue
            fam = _unit_family(r["unit"])
            if fam is None:          # unclassifiable unit → not comparable, drop from the diff
                continue
            if _implausible_money(fam, r["quantified_target"]):   # extraction artefact → drop
                continue
            d.setdefault((r["statement_type"], fam), []).append(r["quantified_target"])
        return d

    flags = 0
    for prev, cur in zip(periods, periods[1:]):
        pg, cg = by_type_unit(prev), by_type_unit(cur)
        # track which statement_types still have ANY comparable bucket in cur, so the
        # "quietly dropped" branch fires on a true disappearance, not a unit reshuffle.
        cur_types = {st for (st, _fam) in cg.keys()}
        for (st, fam), ptargets in pg.items():
            if st not in _COMPARABLE:        # skip 'other'/narrative buckets — not unit-comparable
                continue
            pmax = max(ptargets, default=None)
            crows = cg.get((st, fam))        # SAME type AND SAME unit family only
            cmax = max(crows, default=None) if crows else None
            if pmax is not None and cmax is not None and cmax < pmax * 0.9:
                # commensurate by construction now → a real lowering within one unit
                _flag(conn, symbol, cur, "guidance_walkback", 4,
                      f"{st} target lowered {pmax:g}→{cmax:g} ({prev}→{cur})", prev)
                flags += 1
            elif pmax is not None and st not in cur_types and st in _DROP_TYPES:
                # the whole quantified promise type vanished (not merely re-unit'd)
                _flag(conn, symbol, cur, "promise_quietly_dropped", 3,
                      f"{st} guidance from {prev} not reaffirmed in {cur}", prev)
                flags += 1
    if flags:
        log.info("%s: %d deterioration flags", symbol, flags)
    return flags


def run(symbol: Optional[str] = None) -> int:
    with get_conn() as conn:
        syms = [symbol.upper()] if symbol else [
            r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concall_guidance").fetchall()]
        return sum(diff_symbol(conn, s) for s in syms)


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI deterioration diff (free, deterministic)")
    ap.add_argument("--symbol")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not (args.symbol or args.all):
        ap.error("give --symbol SYM or --all")
    log.info("emitted %d deterioration flags", run(args.symbol if args.symbol else None))


if __name__ == "__main__":
    main()
