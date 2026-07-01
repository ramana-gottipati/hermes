"""Glossary `?` hover-help — UI Architecture v2 cross-cutting feature.

Parses docs/metrics-glossary.md (the single source of truth for Patearn's custom
metrics) into a {term -> definition} index, and provides a pure-CSS `?` popover
helper any screen can wrap a metric label with. Zero fetch (content baked at
render), zero JS (CSS :hover/:focus), zero `src` imports (no circular-import
risk; importable by dashboard.py / cockpit.py / any view).

Isolated new module (per ui-architecture-v2.md §0.8) — it can be authored and
verified now; wiring it onto group-headers/pills is a later, contended-file edit
(deferred). Until wired, it is inert.

Usage (once wired):
    from src.web import glossary as G
    ...  # add G.css() ONCE into the page <style>/<head>
    f'<th>{G.gloss("DVPT")}</th>'                  # label = the term
    f'<th>{G.gloss("rs_rank", "RS#")}</th>'        # custom visible label
A term with no glossary entry degrades to the plain label (no popover).
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Optional

_GLOSSARY_PATH = Path(__file__).resolve().parents[2] / "docs" / "metrics-glossary.md"

_ENTRIES: list[dict] = []
_INDEX: dict[str, int] = {}
_LOADED = False


def _norm(s: str) -> str:
    """Lookup key: lowercase, collapse spaces, strip surrounding punctuation."""
    return re.sub(r"\s+", " ", str(s)).strip().strip(".·").strip().lower()


def _clean_body(s: str) -> str:
    """Inline markdown -> readable plain text for the tooltip."""
    s = s.strip()
    s = s.replace("*Source:*", "source:").replace("*Computed on read.*", "(computed on read)")
    s = re.sub(r"`([^`]*)`", r"\1", s)          # drop backticks
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)    # drop bold
    s = re.sub(r"\*([^*]*)\*", r"\1", s)        # drop italics
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 280:
        s = s[:277].rsplit(" ", 1)[0] + "…"
    return s


def _load() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        text = _GLOSSARY_PATH.read_text(encoding="utf-8")
    except Exception:
        return  # no glossary file -> gloss() degrades to plain labels
    family = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            family = line[3:].strip()
            continue
        if not line.startswith("- **"):
            continue
        # bold term = between the first "**" and the next "**"
        start = line.find("**")
        end = line.find("**", start + 2)
        if start < 0 or end < 0:
            continue
        term_full = line[start + 2:end].strip().strip(".").strip()
        body = _clean_body(line[end + 2:])
        if not term_full:
            continue
        # primary name = before an em/en-dash separator; also a paren-stripped form
        name = re.split(r"\s[—–-]\s", term_full)[0].strip()
        name_no_paren = re.sub(r"\([^)]*\)", "", name).strip()
        # source columns referenced in this bullet (e.g. `rs_rank`, `power_dvpt_*`)
        sources = re.findall(r"`([a-z0-9_*/]+)`", line, flags=re.I)

        # lead token: the name up to the first "/", "(" or "+" — so multi-form
        # labels resolve ("Surge 1m / 3m / 1y" -> "Surge 1m"; "Key price (…) + gap" -> "Key price").
        lead = re.split(r"[/(+]", name)[0].strip()

        entry = {"name": term_full, "family": family, "body": body, "sources": sources}
        idx = len(_ENTRIES)
        _ENTRIES.append(entry)
        keys = {term_full, name, name_no_paren, lead, *sources}
        for k in keys:
            nk = _norm(k)
            if nk and nk not in _INDEX:      # first definition wins
                _INDEX[nk] = idx


def lookup(term: str) -> Optional[dict]:
    """Return the glossary entry for a term/column, or None."""
    _load()
    nk = _norm(term)   # CL-CHR-9: bind once instead of normalising twice
    return _ENTRIES[_INDEX[nk]] if nk in _INDEX else None


def gloss(term: str, label: Optional[str] = None) -> str:
    """A metric label wrapped in a `?` hover-help popover (or the plain label if
    the term has no glossary entry)."""
    disp = html.escape(str(label if label is not None else term))
    e = lookup(term)
    if not e:
        return disp
    return (f'<span class="gl" tabindex="0">{disp}<span class="gl-q">?</span>'
            f'<span class="gl-pop"><b>{html.escape(e["name"])}</b>'
            f'{html.escape(e["body"])}'
            f'<span class="gl-fam">{html.escape(e["family"])}</span></span></span>')


def has(term: str) -> bool:
    return lookup(term) is not None


def terms() -> list[str]:
    """All distinct lookup keys (for debugging / coverage checks)."""
    _load()
    return sorted(_INDEX.keys())


_CSS = """
.gl{position:relative;border-bottom:1px dotted var(--ink-3);cursor:help;outline:none;}
.gl-q{font-size:9px;color:#58a6ff;vertical-align:super;margin-left:1px;font-weight:700;}
.gl-pop{position:absolute;left:0;top:128%;z-index:60;display:none;width:262px;
  background:var(--bg-2);border:1px solid var(--line-2);border-radius:8px;padding:9px 11px;
  font-size:12px;font-weight:400;line-height:1.45;color:var(--ink);white-space:normal;
  text-align:left;text-transform:none;letter-spacing:normal;
  box-shadow:0 6px 22px rgba(0,0,0,.55);}
.gl:hover .gl-pop,.gl:focus .gl-pop{display:block;}
.gl-pop b{color:var(--ink);display:block;margin-bottom:3px;font-weight:600;}
.gl-pop .gl-fam{color:var(--ink-3);font-size:10px;text-transform:uppercase;
  letter-spacing:.4px;margin-top:6px;display:block;}
"""


def css() -> str:
    """The `<style>` block — include ONCE per page that uses gloss()."""
    return f"<style>{_CSS}</style>"
