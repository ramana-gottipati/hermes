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


# --- SUBJECT / REFERENT commensurability (CCI-SEMANTIC fix) -------------------
# The unit-family gate (above) only proves two targets share a UNIT (both %, both
# ₹cr). It does NOT prove they describe the SAME THING. The residual bug: within one
# statement_type AND one unit family, the LLM stores promises about DIFFERENT named
# referents — a parent/consolidated/flagship-segment figure in one period vs a
# JV / subsidiary / geography / brand sub-line figure in the next. max()-ing the
# pool then compares e.g. CGPOWER "industrial-systems full-year growth 14-15%"
# (Aug 2018) against "the Indonesia JV will add ~150 bps to margins" (Feb 2019,
# stored as 1.5%) and fabricates a "revenue lowered 15→1.5" walkback. Same unit
# (%), different subject.
#
# Conservative heuristic (mirrors bug-2's scope gate; NOT a full NLP matcher): if a
# SPECIFICALLY NAMED sub-entity (a JV / subsidiary / named geography / named brand /
# intercompany line) appears in the claim_text of exactly ONE of the two periods'
# buckets — i.e. the referent demonstrably shifted between a part and the whole — the
# two targets are NOT comparable: suppress the walkback rather than emit a wrong Δ.
# Deliberately tight: it uses only referent-DEFINING proper-noun-ish tokens, NOT
# generic measurement words ("bps"/"each"/"per ton"), so it can't over-suppress a
# real same-subject lowering. When the SAME named entity is on both sides (a genuine
# walkback of that entity's own guidance), the asymmetry test is false → NOT
# suppressed. This can only REMOVE a not-comparable walkback, never add one.
#
# JUDGEMENT CALL flagged for the analyst (Ramana): this catches the JV / geography /
# named-subsidiary class (the two confirmed cases + ~55 more on the live ledger). A
# residual class — same unit AND no named sub-entity token, but a different unnamed
# product/segment ("EV revenue 45 → defence revenue 5") — is NOT caught and needs
# true per-claim subject matching; those are left flagged, not chased (see report).
_SUBENTITY_CUES = (
    # corporate sub-entities (a part, never the consolidated whole)
    "jv", "joint venture", "subsidiary", "subsidiaries", "associate company",
    "intercompany", "inter-company", "step-down", "step down",
    # named geographies / export markets (a region, not the group)
    "indonesia", "turkey", "saudi", " uae", "africa", "europe", "us market",
    "the us ", "bangladesh", "vietnam", "china", "overseas", "export market",
    # a distinct product line introduced as new (not the existing base)
    "new product range", "new range",
)
_SCOPE_CUES = ("standalone", "consolidated")   # an explicit part-vs-whole scope switch


def _subentity_set(claims) -> set:
    """The named sub-entity / scope cues present across a bucket's claim_texts."""
    blob = " ".join((c or "").lower() for c in claims)
    s = {t for t in _SUBENTITY_CUES if t in blob}
    s |= {t for t in _SCOPE_CUES if t in blob}
    return s


def _subject_mismatch(prev_claims, cur_claims) -> bool:
    """True when the compared buckets clearly refer to DIFFERENT named subjects.

    Trigger when a named sub-entity (or explicit scope word) appears in exactly one
    side's claim_texts — the referent shifted between a part and the whole. Symmetric
    presence (same entity both periods) is NOT a mismatch (that's a real walkback)."""
    pe, ce = _subentity_set(prev_claims), _subentity_set(cur_claims)
    return bool(pe ^ ce)


# --- COVERAGE-GAP guard (CCI-SEMANTIC fix) -----------------------------------
# promise_quietly_dropped fires when a quantified capex/expansion/revenue/margin/debt
# promise from period P is not reaffirmed in the NEXT period Q. That is only a
# "walkback" if Q is a normal next call. When P→Q straddles a multi-year COVERAGE GAP
# (no concalls in between — e.g. CGPOWER's NCLT/insolvency-era blackout, "Feb 2019
# not reaffirmed in Jul 2025" = 77 months), the promise was never going to be
# reaffirmed because there was simply NO call to reaffirm it. Suppressing the flag
# above a gap ceiling removes these false drops without touching normal-cadence ones.
#
# JUDGEMENT CALL flagged for the analyst (Ramana): the live ledger is sharply bimodal
# — p90 of all P→Q gaps is 6 months (quarterly cadence), then a clean break to a tail
# of 127 flags at >24 months (the 2016→2025 and 2019→2026 COVID/insolvency blackouts;
# the 22–24-month bucket is EMPTY, so 24 is a true gap in the distribution). We set
# the ceiling at 24 months: it suppresses exactly that multi-year tail and leaves the
# 13–21-month COVID-era single-miss flags alone (a 1–2-year non-reaffirmation can
# still be a real abandonment). Single named constant; tighten/loosen per preference.
MAX_REAFFIRM_GAP_MONTHS = 24


def _gap_months(prev_ym, cur_ym) -> Optional[int]:
    """Whole-month gap between two (year, month) tuples, or None if undated."""
    (py, pm), (cy, cm) = prev_ym, cur_ym
    if not py or not cy:
        return None
    return (cy - py) * 12 + (cm - pm)


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
        """{(statement_type, unit_family): [(target, claim_text)]} — bucket by BOTH the
        type and a commensurable unit family so we never max()/compare across different
        units, carrying each target's claim_text for the subject/referent guard."""
        d: dict[tuple, list] = {}
        for r in conn.execute(
            "SELECT statement_type, quantified_target, unit, claim_text FROM concall_guidance "
            "WHERE symbol=? AND source_period=?",
            (symbol, period)).fetchall():
            if r["quantified_target"] is None:
                continue
            fam = _unit_family(r["unit"])
            if fam is None:          # unclassifiable unit → not comparable, drop from the diff
                continue
            if _implausible_money(fam, r["quantified_target"]):   # extraction artefact → drop
                continue
            d.setdefault((r["statement_type"], fam), []).append((r["quantified_target"], r["claim_text"]))
        return d

    flags = 0
    for prev, cur in zip(periods, periods[1:]):
        gap = _gap_months(order.get(prev, (0, 0)), order.get(cur, (0, 0)))
        pg, cg = by_type_unit(prev), by_type_unit(cur)
        # track which statement_types still have ANY comparable bucket in cur, so the
        # "quietly dropped" branch fires on a true disappearance, not a unit reshuffle.
        cur_types = {st for (st, _fam) in cg.keys()}
        for (st, fam), prows in pg.items():
            if st not in _COMPARABLE:        # skip 'other'/narrative buckets — not unit-comparable
                continue
            ptargets = [t for t, _c in prows]
            pmax = max(ptargets, default=None)
            crows = cg.get((st, fam))        # SAME type AND SAME unit family only
            ctargets = [t for t, _c in crows] if crows else []
            cmax = max(ctargets, default=None) if ctargets else None
            if pmax is not None and cmax is not None and cmax < pmax * 0.9:
                # commensurate by UNIT — but is it the same SUBJECT? Suppress when the
                # two buckets name clearly different sub-entities (part-vs-whole mix).
                if _subject_mismatch([c for _t, c in prows], [c for _t, c in crows]):
                    continue                 # not-comparable referents → not a walkback
                # same unit AND no detectable subject shift → a real lowering
                _flag(conn, symbol, cur, "guidance_walkback", 4,
                      f"{st} target lowered {pmax:g}→{cmax:g} ({prev}→{cur})", prev)
                flags += 1
            elif pmax is not None and st not in cur_types and st in _DROP_TYPES:
                # the whole quantified promise type vanished (not merely re-unit'd).
                # Suppress when prev→cur straddles a multi-year coverage gap: a promise
                # can't be "quietly dropped" if there was no call in between to reaffirm.
                if gap is not None and gap > MAX_REAFFIRM_GAP_MONTHS:
                    continue
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
