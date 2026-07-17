"""ui_components_v3.py — the v3 component library (redesign M1). ADDITIVE, v3-only.

Small server-rendered building blocks used by v3 preview pages: stat tile (number + plain
subtitle — never a hover-only meaning), card, section header, evidence link, and the fence
banner. The fence COPY is single-sourced from `infographics.fence()` (the one sanctioned set of
descriptive-boundary phrasings) — this module only restyles it for the v3 look; it never writes
its own boundary wording.
"""
from __future__ import annotations

import html as _html

from src.web import infographics as _ifx

_CSS = """<style>
.pv3-card{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);
  padding:var(--s-3);box-shadow:var(--e-1)}
.pv3-card+.pv3-card{margin-top:var(--s-3)}
.pv3-h{font-size:var(--t-xl);font-weight:700;margin:0 0 var(--s-2)}
.pv3-sec{font-size:var(--t-xs);font-weight:600;color:var(--ink-3);text-transform:uppercase;
  letter-spacing:.5px;margin:var(--s-4) 0 var(--s-2)}
.pv3-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:var(--s-2)}
.pv3-tile{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:12px 14px}
.pv3-tile .v{font:600 var(--t-xl)/1.2 var(--mono);font-variant-numeric:tabular-nums}
.pv3-tile .v.up{color:var(--up)} .pv3-tile .v.down{color:var(--down)}
.pv3-tile .s{display:block;color:var(--ink-3);font-size:var(--t-xs);margin-top:4px}
.pv3-ev{font-size:var(--t-xs)}
.pv3-fence{background:var(--accent-dim);border:1px solid var(--line-2);border-radius:var(--r-sm);
  padding:9px 12px;color:var(--ink-2);font-size:var(--t-sm);margin:var(--s-3) 0}
</style>"""


def css() -> str:
    """Component styles. Include ONCE per v3 page (after tokens)."""
    return _CSS


def card(title: str, body_html: str) -> str:
    t = ('<h2 class="pv3-h">' + _html.escape(str(title)) + "</h2>") if title else ""
    return '<div class="pv3-card">' + t + body_html + "</div>"


def section(label: str) -> str:
    return '<div class="pv3-sec">' + _html.escape(str(label)) + "</div>"


def tile(value: str, subtitle: str, tone: str = "") -> str:
    """A stat tile: the number, then a VISIBLE plain-English subtitle (audit P0-2 lesson —
    meaning never hides behind hover). tone in {'', 'up', 'down'} — value contract only."""
    cls = "v " + tone if tone in ("up", "down") else "v"
    return ('<div class="pv3-tile"><span class="' + cls + '">' + _html.escape(str(value))
            + '</span><span class="s">' + _html.escape(str(subtitle)) + "</span></div>")


def tiles(items: list[tuple[str, str, str]]) -> str:
    """items = [(value, subtitle, tone)]"""
    return '<div class="pv3-tiles">' + "".join(tile(*it) for it in items) + "</div>"


def evidence_link(href: str, label: str = "See the numbers") -> str:
    return ('<a class="pv3-ev" href="' + _html.escape(str(href)) + '">'
            + _html.escape(str(label)) + " →</a>")


def fence(kind: str = "not_advice") -> str:
    """The descriptive boundary, v3-styled — copy comes from the ONE sanctioned source
    (`infographics._FENCE_COPY` via `infographics.fence`); unknown kind raises there, by design."""
    inner = _ifx.fence(kind, cap=True)
    return '<div class="pv3-fence">' + inner + "</div>"


def _selftest() -> int:
    assert "pv3-tile" in css() and "tabular-nums" in css()
    t = tile("+4.2%", "vs Nifty 500, 1 month", "up")
    assert "up" in t and "vs Nifty" in t
    assert 'class="v"' in tile("12", "plain", "verdicty")  # unknown tone never colors
    c = card("T", "<p>x</p>")
    assert "pv3-h" in c and "<p>x</p>" in c
    f = fence("not_advice")
    assert "pv3-fence" in f and len(f) > 40  # sanctioned copy present
    try:
        fence("nonexistent_kind")
        raise AssertionError("unknown fence kind must raise")
    except KeyError:
        pass
    print("ui_components_v3 selftest OK — tiles/cards/fence (single-sourced copy)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
