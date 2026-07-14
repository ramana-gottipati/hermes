"""S-C item 4 (UX audit §8) — the Pat↔web glossary unification contracts.

ONE vocabulary: docs/metrics-glossary.md is canonical; src/pat/glossary.py folds
every web entry a curated entry doesn't already cover into Pat's schema at import
(_merge_web). These tests pin the merge's safety rules:

  · the merge actually happened at scale (no silent md/parser breakage),
  · curated entries are NEVER overwritten (hand-written voice preserved),
  · every adapted entry carries the full schema web.py's _answer() renders,
  · every web entry is accounted for — adapted OR covered by a curated hook,
  · the back-filled md terms (the 19 Pat-only definitions) resolve in the web
    glossary, so /dash/glossary and the site popovers can serve them.
"""
from __future__ import annotations

import re

from src.pat.glossary import GLOSSARY, FAMILIES, _MERGED_FROM_WEB, find, get
from src.web import glossary as WG

_ANSWER_FIELDS = ("term", "family", "unit", "source", "plain", "detail")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().strip(".·").strip().lower()


def _curated_hooks() -> set[str]:
    """Rebuild the hook-set the adapter treats as 'already covered'."""
    taken: set[str] = set()
    for slug, e in GLOSSARY.items():
        taken.add(_norm(slug))
        taken.add(_norm(e["term"]))
        taken.add(_norm(re.sub(r"\([^)]*\)", "", e["term"])))
        for a in e.get("aliases", []):
            taken.add(_norm(a))
    return taken


def test_merge_happened_at_scale():
    assert _MERGED_FROM_WEB >= 120, _MERGED_FROM_WEB
    assert len(GLOSSARY) >= 190


def test_curated_entries_never_overwritten():
    # spot-pin hand-written voice on three curated entries the adapter must not touch
    assert "not adjusted for splits" in GLOSSARY["close"]["detail"]
    assert GLOSSARY["dvpt"]["family"] == "positioning"
    assert "Manpasand" in GLOSSARY["cci_veto"]["detail"]     # the fraud-roster sentence
    assert "ltp" in GLOSSARY["close"]["aliases"]


def test_adapted_entries_render_shape():
    """Every entry (curated + adapted) must carry the fields web.py's _answer() reads."""
    for slug, e in GLOSSARY.items():
        for f in _ANSWER_FIELDS:
            assert f in e and e[f] is not None, (slug, f)
        assert e["term"] and e["plain"] and e["detail"], slug
        assert isinstance(e.get("aliases", []), list) and isinstance(e.get("related", []), list), slug


def test_families_complete():
    """web.py's family tab iterates FAMILIES — no entry may point at a missing key."""
    for slug, e in GLOSSARY.items():
        assert e["family"] in FAMILIES, (slug, e["family"])


def test_every_web_entry_accounted_for():
    """Each md entry is either ADAPTED into GLOSSARY or COVERED by a curated hook."""
    WG._load()
    hooks = _curated_hooks()
    keys_of: dict[int, list[str]] = {}
    for k, idx in WG._INDEX.items():
        keys_of.setdefault(idx, []).append(k)
    terms = {_norm(e["term"]) for e in GLOSSARY.values()}
    dropped = []
    for idx, entry in enumerate(WG._ENTRIES):
        if len(entry["body"]) < 20:                        # structural lead-in, not a definition
            continue
        lead = re.sub(r"\([^)]*\)", " ", entry["name"])    # the adapter's speakable-lead calc
        lead = re.split(r"\s*[—–+/]\s*|\s-\s", lead)[0]
        lead = re.sub(r"[^\w %×Δ&-]", " ", lead)
        lead = re.sub(r"\s+", " ", lead).strip().strip(".-")
        if len(lead) < 3:                                  # pure-symbol name → parenthetical
            m = re.search(r"\(([^)]{3,})\)", entry["name"])
            lead = re.sub(r"\s+", " ", m.group(1)).strip().strip(".-") if m else ""
        probe = _norm(lead)
        slug = re.sub(r"[^a-z0-9]+", "_", probe)[:60].strip("_")
        if slug in GLOSSARY or probe in terms:             # adapted (or its twin was)
            continue
        if probe in hooks:                                 # curated answers this phrase
            continue
        if "_" not in slug and any(slug in h.split() for h in hooks):
            continue                                       # deliberate skip: a bare word a
            # curated probe contains (adopting it as a slug would hijack that probe)
        if any(k in hooks for k in keys_of.get(idx, [])):  # curated covers it (md keys)
            continue
        dropped.append(entry["name"])
    assert not dropped, f"web entries neither adapted nor covered: {dropped}"


def test_backfilled_md_terms_resolve_in_web_glossary():
    """The 19 Pat-only definitions written into the md (S141) must be servable
    by the site glossary — one representative lookup key per added bullet."""
    for key in ("close", "avg_price", "deliv_qty", "deliv_per", "num_trades",
                "is_ath_dvpt", "next_p_above", "institutional price zones",
                "avg_trade_qty", "deliv_updown_ratio_3m", "primary_sector",
                "leaders & laggards", "fundamentals snapshot",
                "deterioration_score", "veto_active",
                "pillars", "value_not_quantity", "financials_adaptation"):
        assert WG.lookup(key) is not None, key


def test_find_covers_the_estate():
    assert [s for s, _ in find("dvpt", limit=3)][0] == "dvpt"      # curated ranking intact
    assert find("seasonality", limit=5)                            # section terms surface
    assert find("up capture", limit=5)                             # adapted metric reachable
    assert get("in_zone") is not None                              # a web-only term now explainable


def test_pat_answer_renders_an_adapted_entry():
    """web.py's explain answer must render an adapted entry without KeyError."""
    from src.pat.web import _answer
    slug = "in_zone"
    html_out = _answer(slug, GLOSSARY[slug])
    assert GLOSSARY[slug]["term"] in html_out and "patAnsDetail" in html_out
