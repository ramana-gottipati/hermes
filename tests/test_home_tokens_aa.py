"""test_home_tokens_aa.py — the Graphite token AA gate (spec §3/§7, the "devops" candle gate).

Computes WCAG 2.1 contrast on the EXACT token values the stylesheet emits (imported from
src.web.home.tokens), both themes. Text pairs must clear 4.5:1; graphical pairs (signed hues,
tertiary ink, and the candle fill+outline) must clear the 3.0:1 graphical-object floor. This is
what makes the light candle-down #93a2b8->#6f8096 fix permanent and enforced.
"""
from __future__ import annotations

from src.web.home.tokens import DARK, LIGHT


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _L(hexs: str) -> float:
    h = hexs.lstrip("#")
    return 0.2126 * _lin(int(h[0:2], 16)) + 0.7152 * _lin(int(h[2:4], 16)) + 0.0722 * _lin(int(h[4:6], 16))


def _ratio(fg: str, bg: str) -> float:
    a, b = _L(fg), _L(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


TEXT_PAIRS = [("ink", "bg-0"), ("ink-2", "bg-0"), ("ink-2", "bg-1"),
              ("accent", "bg-1"), ("on-accent", "accent"), ("ink", "bg-2")]
GRAPHIC_PAIRS = [("up", "bg-0"), ("down", "bg-0"), ("warn", "bg-0"), ("ink-3", "bg-0"),
                 ("accent", "bg-0"), ("candle-up", "bg-2"), ("candle-dn", "bg-2"),
                 ("candle-dn-line", "bg-2")]


def _check(theme: dict, label: str):
    fails = []
    for fg, bg in TEXT_PAIRS:
        r = _ratio(theme[fg], theme[bg])
        if r < 4.5:
            fails.append(f"{label} text {fg}/{bg} = {r:.2f} < 4.5")
    for fg, bg in GRAPHIC_PAIRS:
        r = _ratio(theme[fg], theme[bg])
        if r < 3.0:
            fails.append(f"{label} graphic {fg}/{bg} = {r:.2f} < 3.0")
    assert not fails, fails


def test_dark_theme_aa():
    _check(DARK, "DARK")


def test_light_theme_aa():
    _check(LIGHT, "LIGHT")


def test_light_candle_down_fix_present():
    """The #9 regression: the light grey-down must clear the 3:1 floor (it failed at #93a2b8)."""
    assert LIGHT["candle-dn"] == "#6f8096" and LIGHT["candle-dn-line"] == "#455468"
    assert _ratio(LIGHT["candle-dn"], LIGHT["bg-2"]) >= 3.0
    assert _ratio(LIGHT["candle-dn-line"], LIGHT["bg-2"]) >= 4.5
