"""CCI GOLDEN-SET discrimination test (debate sequencing step 2-3 / P8 essence).

The labelled-blowup backtest: does the CCI avoid-signal flag the known BLOWUPs
(Manpasand / Vakrangee / DHFL / Yes Bank / Coffee Day / …) while NOT flagging the
known COMPOUNDERs (Asian Paints / Pidilite / Page / …)? This is the cleanest test
of the *avoid tape* — the side of CCI the debate judged non-redundant — and the
precondition (debate step 3) before any residual-alpha backtest is trusted.

Ground truth: `resources/cci/golden_set.csv`. A name is "flagged" by CCI if it
carries a ⛔ veto OR a deterministic deterioration flag OR tier D (the measurable
avoid signals, D61). We report the catch rate on blowups vs the false-positive
rate on compounders, and the composite-score separation.

Read-only; numpy only. Run:
    /opt/hermes/.venv-research/bin/python -m research.cci.gate_golden_discrimination

⏳ Needs the blowups' PRE-COLLAPSE calls extracted (≥2 consecutive per name so the
deterioration diff can fire) + compounder calls. Until the backfill accrues, prints
what it has and refuses a verdict. A single pre-collapse call can only be caught by
the veto (which needs pt14/fundamentals coverage that delisted names often lack) —
so this test sharpens precisely as the cron drains more calls per name.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from research.cci.common import main_conn

GOLDEN = Path(__file__).resolve().parents[2] / "resources" / "cci" / "golden_set.csv"
MIN_PER_CLASS = 4      # need at least this many SCORED names per class to render a verdict


def _load_golden() -> list[dict]:
    out = []
    with open(GOLDEN, encoding="utf-8") as f:
        for row in csv.DictReader(r for r in f if not r.lstrip().startswith("#")):
            if row.get("symbol"):
                out.append(row)
    return out


def _signal(con, sym) -> dict | None:
    r = con.execute(
        "SELECT s.* FROM concall_scores s JOIN "
        "(SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x "
        "ON x.symbol=s.symbol AND x.m=s.last_updated WHERE s.symbol=?", (sym,)).fetchone()
    if not r:
        return None
    d = dict(r)
    flagged = bool(d.get("veto_active") or (d.get("deterioration_score") or 0) > 0 or d.get("tier") == "D")
    return {"composite": d.get("composite_score"), "tier": d.get("tier"),
            "deter": d.get("deterioration_score") or 0, "veto": d.get("veto_active") or 0,
            "flagged": flagged}


def main() -> None:
    print("=" * 72)
    print("CCI GOLDEN-SET discrimination — avoid-signal catch rate (blowups vs compounders)")
    print("=" * 72)
    golden = _load_golden()
    with main_conn() as con:
        blow, comp = [], []
        print("\n  name          label       scored  tier  deter veto  flagged")
        for g in sorted(golden, key=lambda x: (x["label"], x["symbol"])):
            sig = _signal(con, g["symbol"])
            tgt = blow if g["label"] == "BLOWUP" else comp
            if sig:
                tgt.append(sig)
                print(f"  {g['symbol']:13s} {g['label']:10s}  yes    {str(sig['tier']):4s} "
                      f"{int(sig['deter']):4d}  {int(sig['veto']):3d}   {'⛔ FLAG' if sig['flagged'] else '—'}")
            else:
                print(f"  {g['symbol']:13s} {g['label']:10s}  no     —     —    —     (not extracted yet)")

    nb, nc = len(blow), len(comp)
    print(f"\n  scored: {nb} blowups, {nc} compounders")
    if nb < MIN_PER_CLASS or nc < MIN_PER_CLASS:
        print(f"\n  ⏳ INSUFFICIENT DATA — need >= {MIN_PER_CLASS} scored names per class.")
        print("  Built + ready; the cron drains the blowups' pre-collapse calls over the")
        print("  coming days (≥2 consecutive per name lets the deterioration diff fire).")
        print("=" * 72)
        return

    catch = np.mean([b["flagged"] for b in blow])           # want HIGH
    fpr = np.mean([c["flagged"] for c in comp])             # want LOW
    bc = np.array([b["composite"] for b in blow if b["composite"] is not None], dtype=float)
    cc = np.array([c["composite"] for c in comp if c["composite"] is not None], dtype=float)
    print(f"\n  blowup catch rate (flagged): {catch*100:5.1f}%   <- want high")
    print(f"  compounder false-positive  : {fpr*100:5.1f}%   <- want low")
    if len(bc) and len(cc):
        print(f"  mean composite: blowups {bc.mean():.1f} vs compounders {cc.mean():.1f} "
              f"(separation {cc.mean()-bc.mean():+.1f})")
    passed = catch >= 0.6 and fpr <= 0.2
    print("  " + "-" * 50)
    print(f"  VERDICT: {'PASS — the avoid tape discriminates blowups from compounders.' if passed else 'WEAK — avoid signal does not yet separate the labelled set (needs more pre-collapse calls / the sector rubric).'}")
    print("=" * 72)


if __name__ == "__main__":
    main()
