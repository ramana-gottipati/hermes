"""term_chip.py — the self-teaching term chip (redesign M2). ADDITIVE, v3-preview-only.

Every proprietary term renders as: plain-English label first, the proprietary code as a small
mono badge, a hover/focus one-liner, and a click-to-expand TEACH CARD carrying the four glossary
fields plus the epistemic record — Verdict · "How it could improve" (subtitled *what would change
the read* — never a promise of returns) · Origin (🧑/🏠/📚).

Sources (never forked — reviewer dispositions in docs/redesign-coordination.md §3/§4):
  * definition — `glossary.lookup()` over docs/metrics-glossary.md (the ONE glossary; Codex B3);
  * verdict/improve/origin — docs/metric-verdicts.md, a sidecar parsed ONLY here (Gemini B2);
  * labels that don't resolve verbatim go through the explicit ALIAS map (Codex B5).

Interaction (Gemini A4): hover / first tap (focus) = one-liner; click / second tap = teach card;
Escape or outside-click closes. `tabindex="0"` matches the glossary idiom.

Used only inside shell_v3 documents; no legacy module imports this file.
"""
from __future__ import annotations

import html as _html
import re as _re
import urllib.parse as _uq
from pathlib import Path
from typing import Optional

from src.web import glossary as G

_VERDICTS_PATH = Path(__file__).resolve().parents[2] / "docs" / "metric-verdicts.md"

# chip key -> (plain label, badge code, glossary lookup key, strategy-ref slug or "")
SEEDS: dict[str, tuple[str, str, str, str]] = {
    "dvpt":       ("Delivery size",              "DVPT",       "DVPT",            "dvpt"),
    "xpower":     ("Intensity (vs own history)", "×POWER",     "intensity",       "dvpt"),
    "keyprice":   ("Where big money bought",     "KEY PRICE",  "Key price",       "dvpt"),
    "mep":        ("Accumulation / Distribution","MEP",        "mep_score",       "mep"),
    "rsband":     ("Strength vs own range",      "RS BAND",    "rs_band_pct",     "relative-strength"),
    "cci":        ("Management credibility",     "CCI",        "composite_score", "cci"),
    "conviction": ("Composite rank",             "CONVICTION", "Conviction",      ""),
    "pt14":       ("Quality score (14 patterns)","PT14",       "ns_base",         "patearn"),
    "cpr":        ("Pivot structure",            "CPR",        "CPR",             "cpr"),
    "retvol":     ("Return ÷ volatility",        "RETURN/VOL", "return/vol",      ""),
    "rsrank":     ("Strength rank",              "RS RANK",    "rs_rank",         "relative-strength"),
    "w52":        ("Distance from 52-week high", "52W",        "pct_from_52w_high", ""),
}

_VERDICTS: dict[str, dict] = {}
_V_LOADED = False


def _load_verdicts() -> None:
    """Parse the sidecar. One bullet per term: `- **key.** *Plain:* … *Verdict:* …
    *Improve:* … *Origin:* …` — fields inline, keyed by glossary lookup key."""
    global _V_LOADED
    if _V_LOADED:
        return
    _V_LOADED = True
    try:
        text = _VERDICTS_PATH.read_text(encoding="utf-8")
    except Exception:
        return  # chips degrade to definition-only cards
    for line in text.splitlines():
        if not line.startswith("- **"):
            continue
        m = _re.match(r"- \*\*(.+?)\.?\*\*(.*)$", line)
        if not m:
            continue
        key, rest = m.group(1).strip(), m.group(2)
        fields = {}
        for name in ("Plain", "Verdict", "Improve", "Origin"):
            fm = _re.search(r"\*" + name + r":\*\s*(.*?)(?=\s*\*(?:Plain|Verdict|Improve|Origin):\*|$)",
                            rest, _re.S)
            if fm:
                fields[name.lower()] = _re.sub(r"\s+", " ", fm.group(1)).strip()
        if fields:
            _VERDICTS[_norm(key)] = fields


def _norm(s: str) -> str:
    return _re.sub(r"\s+", " ", str(s)).strip().lower()


def verdict_for(gloss_key: str) -> Optional[dict]:
    _load_verdicts()
    return _VERDICTS.get(_norm(gloss_key))


def _one_liner(body: str) -> str:
    first = body.split(". ", 1)[0].rstrip(".") + "."
    return first if len(first) <= 160 else first[:157].rsplit(" ", 1)[0] + "…"


def chip(key: str, sym: str = "") -> str:
    """The full chip: label + badge + one-liner popover + teach card. Unknown key or an
    unresolvable glossary term degrades to the plain escaped label (never breaks a page)."""
    spec = SEEDS.get(key)
    if not spec:
        return _html.escape(key)
    label, code, gkey, ref = spec
    entry = G.lookup(gkey)
    if not entry:
        return _html.escape(label)
    v = verdict_for(gkey) or {}
    e = _html.escape
    pat_q = "Explain " + label + (" for " + sym if sym else "")
    links = ['<a href="/dash/glossary?q=' + _uq.quote(gkey) + '">Glossary</a>']
    if ref:
        links.append('<a href="/dash/strategy-ref?p=' + _uq.quote(ref) + '">Methodology</a>')
    links.append('<a href="/dash/pat?q=' + _uq.quote(pat_q) + '">Ask Pat</a>')
    links.append('<a href="/dash/testing">Validation record</a>')
    card = ['<span class="tc-card" role="dialog" aria-label="' + e(label) + ' explained">',
            "<b>" + e(entry["name"]) + "</b>",
            '<span class="tc-body">' + e(entry["body"]) + "</span>"]
    if v.get("verdict"):
        card.append('<span class="tc-sec">Verdict</span><span class="tc-body">'
                    + e(v["verdict"]) + "</span>")
    if v.get("improve"):
        card.append('<span class="tc-sec">How it could improve '
                    '<i>— what would change the read</i></span>'
                    '<span class="tc-body">' + e(v["improve"]) + "</span>")
    if v.get("origin"):
        card.append('<span class="tc-org">' + e(v["origin"]) + "</span>")
    card.append('<span class="tc-links">' + " · ".join(links) + "</span></span>")
    return ('<span class="pv3chip" tabindex="0" data-tc="' + e(key) + '">'
            + e(label) + '<span class="tc-badge">' + e(code) + "</span>"
            + '<span class="tc-pop">' + e(_one_liner(entry["body"]))
            + ' <i class="tc-more">tap again for the full card</i></span>'
            + "".join(card) + "</span>")


_CSS_JS = """<style>
.pv3chip{position:relative;border-bottom:1px dotted var(--ink-3);cursor:pointer;outline-offset:2px}
.tc-badge{font-family:var(--mono);font-size:10px;font-weight:600;color:var(--accent);
  border:1px solid var(--line-2);border-radius:4px;padding:0 4px;margin-left:5px;vertical-align:1px}
.tc-pop,.tc-card{position:absolute;left:0;top:130%;z-index:70;display:none;width:min(340px,86vw);
  background:var(--bg-2);border:1px solid var(--line-2);border-radius:var(--r-sm);
  padding:10px 12px;font-size:var(--t-sm);line-height:1.5;color:var(--ink);white-space:normal;
  text-align:left;box-shadow:var(--e-2)}
.pv3chip:hover .tc-pop,.pv3chip:focus .tc-pop{display:block}
.pv3chip.open .tc-pop{display:none}
.pv3chip.open .tc-card{display:block;width:min(430px,92vw)}
.tc-more{display:block;color:var(--ink-3);font-size:var(--t-xs);margin-top:5px;font-style:normal}
.tc-card b{display:block;margin-bottom:4px}
.tc-sec{display:block;margin-top:9px;font-size:var(--t-xs);font-weight:600;color:var(--ink-2);
  text-transform:uppercase;letter-spacing:.4px}
.tc-sec i{text-transform:none;letter-spacing:0;font-weight:400;color:var(--ink-3)}
.tc-body{display:block;color:var(--ink-2)}
.tc-org{display:block;margin-top:9px;color:var(--ink-3);font-size:var(--t-xs)}
.tc-links{display:block;margin-top:9px;border-top:1px solid var(--line);padding-top:8px;
  font-size:var(--t-xs)}
</style>
<script>(function(){
document.addEventListener("click",function(e){
  if(e.target.closest(".tc-card a"))return;              /* let card links navigate */
  var c=e.target.closest(".pv3chip");
  document.querySelectorAll(".pv3chip.open").forEach(function(x){if(x!==c)x.classList.remove("open");});
  if(c){c.classList.toggle("open");}
});
document.addEventListener("keydown",function(e){
  if(e.key==="Escape")document.querySelectorAll(".pv3chip.open").forEach(function(x){x.classList.remove("open");});
});})();</script>"""


def assets() -> str:
    """Chip CSS + the shared toggle handler. Include ONCE per page that uses chip()."""
    return _CSS_JS


def _selftest() -> int:
    _load_verdicts()
    assert len(_VERDICTS) == len(SEEDS), (len(_VERDICTS), len(SEEDS))
    for key, (_label, _code, gkey, _ref) in SEEDS.items():
        assert G.lookup(gkey), "glossary miss: " + gkey
        v = verdict_for(gkey)
        assert v and v.get("verdict") and v.get("improve"), "sidecar gap: " + key
        h = chip(key, sym="TCS")
        assert "tc-card" in h and "Ask Pat" in h and 'tabindex="0"' in h
    # fence discipline: no action-verb verdict labels in the epistemic copy
    joined = " ".join((v.get("verdict", "") + " " + v.get("improve", "")).lower()
                      for v in _VERDICTS.values())
    for verb in ("buy", "sell", "avoid", "ride", "fade"):
        assert _re.search(r"\b" + verb + r"\b", joined) is None, "action verb: " + verb
    assert chip("nonsense") == "nonsense"  # unknown key degrades
    print("term_chip selftest OK — " + str(len(SEEDS)) + " seed chips resolve + carry verdicts")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
