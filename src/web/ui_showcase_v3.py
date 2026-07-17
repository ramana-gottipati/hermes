"""ui_showcase_v3.py — /dash/_ui3, the v3 design-system showcase (redesign M1+M2 proof page).

The living demo of the OPT-IN v3 theme layer + the self-teaching term chips, rendered entirely
inside `shell_v3` (so viewing it exercises the real shell, grid, both themes, and the chip
interaction end-to-end). internal_dev route — deliberately unlinked from all navigation
(route-gate INTERNAL_DEV entry; Codex review B1/B2: no affordance is added to existing chrome).

Everything on this page is either a static demo value (labeled as such) or a term chip backed
by the real glossary + verdict sidecar. No DB reads — the showcase must render on a bare clone.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web import shell_v3, term_chip, ui_components_v3 as C

router = APIRouter()


def _body() -> str:
    chips = " · ".join(term_chip.chip(k) for k in term_chip.SEEDS)
    demo_tiles = C.tiles([
        ("+2.4%", "Nifty 500, this month (demo value)", "up"),
        ("−1.1%", "Midcap 150, this week (demo value)", "down"),
        ("74%", "stocks advancing today (demo value)", ""),
        ("1.19", "best net return ÷ volatility on record", ""),
    ])
    focus = (
        C.card("The v3 look — quiet type, aligned numbers, evidence one click away",
               "<p>This page demonstrates every v3 building block on real teaching data. "
               "The theme toggle (top right) flips dark ⇄ light; both ship from day one. "
               "Numbers are mono + tabular; meaning is always visible, never hover-only.</p>"
               + C.fence("not_advice"))
        + C.section("Stat tiles — number + plain subtitle")
        + demo_tiles
        + C.section("Term chips — every proprietary word teaches itself (tap one)")
        + C.card("", "<p style=\"line-height:2.2\">" + chips + "</p>"
                 "<p>Hover or first tap = the one-line meaning. Click / second tap = the full "
                 "teach card: definition, the recorded <b>verdict</b> with its numbers, "
                 "<b>how it could improve</b> (what would change the read — never a promise), "
                 "origin, and links to the glossary, methodology, Pat, and the validation "
                 "record.</p>")
    )
    rail = (
        C.card("Context rail", "<p>On a stock, this rail carries news, the next results date, "
               "corp actions, peers, and every lens that fired — co-presented, never buried in "
               "tabs. (M4 scope — this is the layout proof.)</p>")
        + C.card("Evidence", "<p>" + C.evidence_link("/dash/testing", "The validation record")
                 + "<br>" + C.evidence_link("/dash/replay-any-date", "Replay any date")
                 + "</p>")
    )
    return focus, rail


@router.get("/dash/_ui3", response_class=HTMLResponse, include_in_schema=False)
def ui_showcase_v3() -> HTMLResponse:
    focus, rail = _body()
    head = C.css() + term_chip.assets()
    return HTMLResponse(shell_v3.shell("Design system v3", focus, rail, extra_head=head))


def _selftest() -> int:
    focus, rail = _body()
    doc = shell_v3.shell("t", focus, rail, extra_head=C.css() + term_chip.assets())
    assert "pv3chip" in doc and "tc-card" in doc and "pv3-tile" in doc
    assert "demo value" in doc                     # honest labeling of static numbers
    assert "uk-sub" not in doc and "uk-main" not in doc
    print("ui_showcase_v3 selftest OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
