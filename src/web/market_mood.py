"""Canonical market-mood — ONE vocabulary for every regime banner (UX audit S-A, P0-3).

Before this module, three surfaces said three different things about the same market on
the same day (home "RISK-OFF" · kill-switch strip "Cautious" · Markets header "UP-BIASED").
Now every banner derives its LEADING word here; per-index trend verdicts (UPTREND / NEAR
HIGH / UP-BIASED...) remain, but always subordinated behind an explicit "trend:" prefix so
they read as the index's own state, never as the market mood.

Vocabulary (three words, beginner-plain, aligned with the kill-switch strip's existing
"Market mood" treatment): **Upbeat · Mixed · Cautious** (+ "No data").

Derivation (strictest clock wins — the two mood sources can never disagree):
  1. If the nightly kill-switch regime check (``killswitch.regime``) is at warn/critical,
     the mood is **Cautious** regardless of breadth — this is the same cached read the
     site-wide dq_banner strip quotes.
  2. Else the breadth composite decides: breadth ≥60% AND Nifty 50 above its 200-DMA →
     **Upbeat**; breadth <40% OR Nifty below its 200-DMA → **Cautious**; else **Mixed**.

Isolated module (parallel-sessions doctrine): imported by cockpit; no routes, no DB writes.
"""
from __future__ import annotations

import html as _html
from typing import Optional


def _regime_check_bad() -> Optional[str]:
    """The kill-switch regime check's message when it is at warn/critical, else None.
    Reuses dq_banner's cached fetch (never raises, one DB read per TTL)."""
    try:
        from src.web.dq_banner import _fetch
        _run_at, bad = _fetch()
        for check, _sev, msg in bad:
            if check == "killswitch.regime":
                return msg or "momentum regime OFF"
    except Exception:  # noqa: BLE001 — a busy DB must never break a banner
        pass
    return None


def market_mood(breadth: Optional[float], nifty_above_200dma: Optional[bool]) -> dict:
    """The canonical mood. Returns {word, cls, plain, parts} where `cls` is one of the
    existing banner classes (b-on / b-neu / b-off) and `parts` is the component readout
    used by the inline "why?" expander."""
    regime_msg = _regime_check_bad()
    parts = []
    if breadth is not None:
        parts.append(f"{breadth:.0f}% of indices are above their own 200-day average "
                     f"(60%+ reads strong, under 40% reads weak)")
    if nifty_above_200dma is not None:
        parts.append("the Nifty 50 is " + ("above" if nifty_above_200dma else "below")
                     + " its 200-day average")
    if regime_msg:
        parts.append(f"the nightly momentum health-check flags: {regime_msg}")

    if breadth is None and nifty_above_200dma is None:
        return {"word": "No data", "cls": "b-neu",
                "plain": "today's index signals haven't landed yet.", "parts": parts}
    if regime_msg is not None:
        return {"word": "Cautious", "cls": "b-off",
                "plain": "the market's own momentum health-check is flashing — expect chop.",
                "parts": parts}
    if (breadth is not None and breadth >= 60) and nifty_above_200dma:
        return {"word": "Upbeat", "cls": "b-on",
                "plain": "most indices are trending up and the Nifty 50 is above its long-term average.",
                "parts": parts}
    if (breadth is not None and breadth < 40) or nifty_above_200dma is False:
        return {"word": "Cautious", "cls": "b-off",
                "plain": "more indices are below their long-term trend than above it.",
                "parts": parts}
    return {"word": "Mixed", "cls": "b-neu",
            "plain": "some parts of the market are trending up, others down — no clear lean.",
            "parts": parts}


def mood_banner(mood: dict, extras_small: str = "", font_px: int = 15) -> str:
    """The shared banner: mood word + plain sentence + the caller's extra readouts +
    an INLINE ‘why?’ expander (answers where the question arises — never a dead link).
    `extras_small` is pre-escaped HTML appended inside the <small>."""
    why = ""
    if mood["parts"]:
        items = "".join(f"<li>{_html.escape(p)}</li>" for p in mood["parts"])
        why = ('<details class="mood-why"><summary>why?</summary><ul>'
               + items +
               '<li>full data-quality ledger → <a href="/dash/coverage">Coverage &amp; limits</a></li>'
               '</ul></details>')
    sep = " · " if extras_small else ""
    return (f'<div class="banner {mood["cls"]}" style="font-size:{font_px}px">'
            f'Market mood: {_html.escape(mood["word"])}'
            f'<small>· {_html.escape(mood["plain"])}{sep}{extras_small}</small>'
            f'{why}</div>'
            + _MOOD_CSS)


_MOOD_CSS = """<style>
.mood-why{display:inline-block;margin-left:10px;font-size:12px;font-weight:400;vertical-align:middle;}
.mood-why summary{cursor:pointer;opacity:.75;text-decoration:underline;text-underline-offset:2px;list-style:none;display:inline;}
.mood-why summary::-webkit-details-marker{display:none;}
.mood-why[open] summary{opacity:1;}
.mood-why ul{margin:6px 0 2px;padding-left:18px;font-weight:400;line-height:1.5;}
.mood-why a{color:inherit;}
</style>"""
