"""test_home_journey.py — the W5 gate: the M6 journey/help layer + the Graphite Trust estate.

Three contracts are enforced here, each of which a future edit could silently break:

  1. THE M6 CONTRACT — one one-shot nudge, a persistent help control in the SAME slot on every
     page, teaching empty states that cannot be constructed bare, four per-persona exits reachable
     in ≤1 click, and a STRUCTURAL tour ban (no backdrop / focus trap / scroll lock / step counter).
  2. THE PORT CONTRACT — every Trust page renders 200 in the Graphite identity, reads the SAME
     source as its classic twin (never a second copy), links symbols with `?sym=`, and shows a
     TEACHING empty rather than a blank when its source is absent.
  3. THE PAT CONTRACT — there is no third Pat. The dock resolves deterministically through the two
     auto-folding knowledge sources, with no model call anywhere in the path.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from src.web.home import journey, pat_dock
from src.web.home import trust_pages as T
from src.web.home import trust_reads as R

PAGES = ("/dash/home/proof", "/dash/home/validation", "/dash/home/prereg", "/dash/home/rule-lab",
         "/dash/home/replay", "/dash/home/glossary", "/dash/home/strategy-ref", "/dash/home/guide")

LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')


def _visible(html: str) -> str:
    """The rendered page minus its <style>/<script> blocks and comments — the shared kit ships CSS
    for components this estate does not USE, and its comments mention them by name, so a naive
    substring scan reads those as if they were on the page."""
    out = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    out = re.sub(r"<script\b.*?</script>", "", out, flags=re.S | re.I)
    return re.sub(r"<!--.*?-->", "", out, flags=re.S)


@pytest.fixture(scope="module")
def client():
    from src.main import app
    return TestClient(app)


# ── 1. the M6 contract ───────────────────────────────────────────────────────────────
def test_teaching_empty_cannot_be_constructed_bare():
    """The empty-state contract is enforced by the COMPONENT (Codex B1/B2 form): a bare "no data"
    is not expressible, because why + href + label are all mandatory and non-blank."""
    for bad in (("", "/x", "l"), ("w", "", "l"), ("w", "/x", ""), ("   ", "/x", "l"), (None, "/x", "l")):
        with pytest.raises(ValueError):
            journey.teaching_empty(*bad)
    good = journey.teaching_empty("Nothing has landed yet.", "/dash/home", "Go to Today")
    assert "Nothing has landed yet." in good and "Go to Today" in good and "/dash/home" in good


def test_every_teaching_empty_call_site_passes_all_three_arguments():
    """Source-level twin of the render-level check: no call site may degrade the contract by
    passing a positional blank or dropping the action."""
    src = open(T.__file__, encoding="utf-8").read()
    calls = re.findall(r"teaching_empty\(", src)
    assert len(calls) >= 6, "the Trust estate should teach in every honest-empty branch"
    # every call must span to a closing paren containing at least two commas (why, href, label)
    for m in re.finditer(r"journey\.teaching_empty\((.{20,900}?)\)\s*(?:\+|,|$|\n)", src, re.S):
        assert m.group(1).count(",") >= 2, m.group(1)[:120]


def test_the_tour_is_banned_structurally_not_just_by_copy():
    """The ratified evidence bans multi-step tours. Assert the MECHANISMS are absent, not just the
    words: no backdrop/dimming, no focus trap, no body-scroll lock, no step counter, no 'next'."""
    blob = journey.assets() + journey.nudge() + journey.steps_block()
    for banned in ("data-tour", "step 1 of", "Next →", "backdrop", "overflow:hidden",
                   "scroll-lock", "focus-trap", "aria-modal", "inert"):
        assert banned not in blob, banned
    # exactly ONE persisted flag — there is no step state to advance
    assert blob.count("pvgnudge") >= 1
    assert not re.search(r"pvgnudge\s*[,)]?\s*[\"']?\d", blob), "the nudge must not persist a step index"


def test_the_nudge_is_one_shot_and_never_blocks():
    n = journey.nudge()
    js = journey.assets()
    assert 'id="g-nudge"' in n and 'aria-label="Dismiss this tip"' in n
    assert "localStorage" in js and '"done"' in js          # one time, ever
    assert "Escape" in js and "scroll" in js                 # dismissible four ways
    assert "prefers-reduced-motion" in js


def test_help_control_is_identical_on_every_page(client):
    """Position consistency IS the feature — same label, same slot, site-wide."""
    for url in PAGES:
        h = client.get(url).text
        assert 'id="g-help"' in h, url
        assert journey.HELP_LABEL in h, url
        assert journey.HELP_HREF in h, url
        assert "g-top" in h                                   # the slot it is moved into exists


def test_all_four_persona_exits_are_one_click_from_every_page(client):
    assert len(journey.EXITS) == 4
    for url in PAGES:
        h = client.get(url).text
        for key, _label, _sub, href in journey.EXITS:
            assert href in h, (url, key, href)


# ── 2. the port contract ─────────────────────────────────────────────────────────────
def test_every_trust_page_renders_in_the_graphite_identity(client):
    for url in PAGES + ("/dash/home/validation?pack=1", "/dash/home/strategy-ref?p=mep",
                        "/dash/home/glossary?q=delivery"):
        r = client.get(url)
        assert r.status_code == 200, url
        assert "data-ui-g" in r.text, url
        for marker in LEGACY_MARKERS:
            assert marker not in r.text, (url, marker)


def test_pages_use_sym_never_symbol(client):
    for url in PAGES:
        h = client.get(url).text
        assert "?symbol=" not in h, url
    assert "/dash/home/stock?sym=TCS" in T._sym("TCS")


def test_glossary_reads_the_one_definition_source(client):
    """261 terms parse from docs/metrics-glossary.md — the Graphite page must read the SAME parse
    the ? popovers and /dash/glossary use, never a second copy."""
    from src.web import glossary as G
    G._load()
    entries = R.glossary_entries()
    assert entries and len(entries) == len(G._ENTRIES)
    fams = R.glossary_families()
    assert sum(len(v) for _k, v in fams) == len(entries)
    h = client.get("/dash/home/glossary").text
    assert f"{len(entries)} terms" in h and f"{len(fams)} families" in h


def test_strategy_reference_list_is_derived_not_hardcoded():
    """Derived from the directory, so a new strategy page appears the day it lands."""
    import glob
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [f for f in glob.glob(os.path.join(root, "docs", "strategies", "*.md"))
             if os.path.basename(f).lower() not in ("readme.md", "index.md", "_index.md")]
    assert len(R.strategy_pages()) == len(files) >= 10


def test_the_public_sanitizer_beats_the_classic_multi_letter_gap():
    """The classic sanitizer's session/decision regex is `\\b[SD]\\d{1,3}[a-z]?\\b`, which misses
    multi-letter (`S164BB`), hyphenated (`S155-e`) and 4-digit (`S1234`) ids. This port must scrub
    all of them — and the widened DATE-tag form too."""
    dirty = ("Ramana's call (D138, S164BB) on 2026-07-16BB, refined S155-e / S1234, "
             "commit `3d13d97a1b2c`.\nDelivery is the share of volume settled.")
    clean = R.public_text(dirty)
    for tok in ("Ramana", "D138", "S164BB", "S155-e", "S1234", "2026-07-16BB", "3d13d97a1b2c"):
        assert tok not in clean, tok
    assert "Delivery is the share of volume settled." in clean


def test_no_strategy_doc_leaks_an_internal_token():
    leak = re.compile(r"\bS\d{2,4}\b|\bD\d{2,4}\b|Ramana|PROJECT_STATE|\b[0-9a-f]{7,40}\b")
    for p in R.strategy_pages():
        txt = R.strategy_doc(p["slug"])["text"]
        assert not leak.search(txt), (p["slug"], leak.search(txt).group(0))


def test_markdown_renderer_is_dom_safe():
    out = T._md("<script>alert(1)</script>\n\n[x](javascript:evil)\n")
    assert "<script>" not in out and "javascript:" not in out


def test_absent_sources_teach_instead_of_blanking(client):
    """research.db and the v1 key are box-side. In a worktree they are absent — the page must SAY
    what would appear there, not render an empty table. (If the box ever runs this suite with
    research.db present the assertion relaxes to 'the record rendered'.)"""
    h = client.get("/dash/home/validation").text
    if R.validation()["rows"]:
        assert "Net return/vol" in h
    else:
        assert "g-empty2" in h and "not present in this environment" in h


# ── 3. the rule-lab URL-state contract (ratified Part III §K.4) ──────────────────────
@pytest.mark.parametrize("params", [
    {"u": "liquid500", "rank": "mom12", "n": "25", "hold": "quarterly"},
    {"u": "largecap", "rank": "lowvolmom", "n": "15", "hold": "monthly", "where": "not_extended"},
    {"u": "midcap", "rank": "mom6", "n": "40", "hold": "quarterly",
     "where": "not_extended,min_liquidity", "veto": "mep_distribution"},
])
def test_rule_lab_verdict_state_round_trips_through_the_url(params):
    """A verdict IS a URL. The engine CANONICALISES the filter/veto order, so the round-trip is
    idempotent rather than byte-identical — which is the stronger property for a shareable link:
    two orderings of the same rule produce the SAME URL, and re-opening it never drifts."""
    spec = R.rule_spec_from_query(params)
    once = R.rule_query_from_spec(spec)
    twice = R.rule_query_from_spec(R.rule_spec_from_query(once))
    assert once == twice                                     # idempotent: a link is stable
    for key in ("u", "rank", "n", "hold"):
        assert once[key] == params[key]
    for key in ("where", "veto"):                            # same SET, canonical order
        assert set(once.get(key, "").split(",")) == set(params.get(key, "").split(","))


def test_rule_lab_url_params_match_the_classic_surface():
    """Cross-pin: the Graphite mapping and the classic page's mapping must agree, so a link moves
    between the two surfaces unchanged. (The classic view is imported HERE, in the test, never at
    runtime from src/web/home — it pulls the classic chrome.)"""
    from src.web import rule_lab_view as RLV
    spec = R.rule_spec_from_query({"u": "liquid500", "rank": "mom12", "n": "25",
                                   "hold": "quarterly", "where": "not_extended"})
    assert R.rule_query_from_spec(spec) == RLV.query_from_spec(spec)


def test_rule_lab_page_shows_the_shareable_url_and_the_known_dead_wall(client):
    r = client.get("/dash/home/rule-lab?u=liquid500&rank=mom12&n=25&hold=quarterly")
    assert r.status_code == 200
    assert "/dash/home/rule-lab?u=liquid500&amp;rank=mom12" in r.text or \
           "/dash/home/rule-lab?u=liquid500&rank=mom12" in r.text
    assert "Shareable verdict URL" in r.text


def test_rule_lab_rejects_a_token_outside_the_closed_vocabulary(client):
    r = client.get("/dash/home/rule-lab?u=liquid500&rank=NOT_A_SIGNAL&n=25&hold=quarterly")
    assert r.status_code == 200 and "g-empty" in r.text


# ── 4. the Pat contract — no third Pat ───────────────────────────────────────────────
def test_there_is_exactly_one_pat_in_the_graphite_package():
    """A second dock module, or a second `dock_html`, would BE the third Pat."""
    import os
    import pkgutil
    import src.web.home as H
    mods = {m.name for m in pkgutil.iter_modules([os.path.dirname(H.__file__)])}
    assert {m for m in mods if "pat" in m} == {"pat_dock"}, mods
    src = open(T.__file__, encoding="utf-8").read()
    assert "def dock_html" not in src and "_AVATAR" not in src


def test_pat_resolution_is_deterministic_and_model_free():
    """Every resolution path is regex / dict lookup over the two auto-folding sources. No model
    call, no network — a dock answer must be instant and cost nothing."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(pat_dock))
    banned_mods = {"llm_router", "genai", "anthropic", "httpx", "requests", "urllib",
                   "src.pat.engine", "engine"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported |= {(node.module or "")} | {(node.module or "") + "." + a.name for a in node.names}
    assert not (imported & banned_mods), sorted(imported & banned_mods)
    assert not any(m.split(".")[-1] in banned_mods for m in imported), sorted(imported)
    banned_calls = {"route", "call_classifier", "classify_with_llm"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in banned_calls, node.func.attr
    assert pat_dock.resolve("TCS") == {"kind": "symbol", "sym": "TCS"}
    assert pat_dock.resolve("")["kind"] == "none"
    # determinism: the same question twice, the same answer
    q = "what is delivery"
    assert pat_dock.resolve(q) == pat_dock.resolve(q)


def test_pat_answers_from_the_glossary_auto_fold():
    """Source A: a term defined in docs/metrics-glossary.md is answerable with ZERO code — and an
    exact code match beats the ticker guess, so typing `DVPT` explains DVPT instead of hunting for
    a stock by that name."""
    from src.pat import glossary as PG
    slug, entry = PG.find("delivery", limit=1)[0]
    for probe in (slug, entry["term"], "what is " + entry["term"]):
        r = pat_dock.resolve(probe)
        assert r["kind"] == "explain" and r["term"], (probe, r)
    assert pat_dock.resolve("TCS")["kind"] == "symbol"       # a real ticker still wins


def test_pat_navigation_prefers_the_graphite_twin():
    assert pat_dock._GRAPHITE_TWIN["/dash/coverage"] == "/dash/home/proof"
    assert pat_dock._GRAPHITE_TWIN["/dash/testing"] == "/dash/home/validation"
    twin = pat_dock._twin({"label": "Coverage", "route": "/dash/coverage"})
    assert twin["route"] == "/dash/home/proof"


def test_pat_ask_endpoint_returns_an_escaped_fragment(client):
    r = client.get("/dash/home/pat/ask?q=TCS")
    assert r.status_code == 200 and "/dash/home/stock?sym=TCS" in r.text
    assert "<!doctype" not in r.text.lower()                  # a fragment, not a page
    r = client.get("/dash/home/pat/ask?q=%3Cscript%3Ealert(1)%3C/script%3E")
    assert r.status_code == 200 and "<script>" not in r.text


def test_pat_admits_when_it_does_not_know(client):
    r = client.get("/dash/home/pat/ask?q=qqzzxx%20wibble%20frobnicate")
    assert r.status_code == 200 and "deterministic answer" in r.text


def test_the_dock_still_carries_its_own_reduced_motion_and_a11y_contract():
    """The W5 extension must not regress the dock's existing gates."""
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    h = pat_dock.dock_html(c)
    assert 'matchMedia("(prefers-reduced-motion:reduce)")' in h
    assert 'role="dialog"' in h and "inert" in h
    for k, _lbl in pat_dock._SUGG_TRUST:
        assert 'data-key="' + k + '"' in h


# ── 5. the estate's own honesty rules ────────────────────────────────────────────────
def test_the_proof_estate_is_never_paywalled(client):
    """Ratified Part III §J: evidence is never gated. Every page here IS evidence, so no page in
    this estate may carry a Pro-Ad teaser."""
    for url in PAGES:
        h = _visible(client.get(url).text)
        # the shared kit always ships the `.g-proad` CSS; what must never appear is the ELEMENT
        assert 'class="g-proad' not in h, (url, "evidence must not be gated behind a Pro teaser")
        assert "Unlock with Pro" not in h, url


def test_pages_carry_the_descriptive_fence(client):
    for url in PAGES:
        h = client.get(url).text
        assert "Descriptive record only" in h or "Descriptive only" in h, url


def test_no_page_introduces_the_retired_ratio_name(client):
    """D142: every ratio in this project is return/vol; the retired word may not be AUTHORED here.

    FINDING (recorded, not fixed here): the failure ledger's BLOCKING rows still contain the old
    word, and `rule_lab.BLOCKING_ROWS` mirrors them BYTE-VERBATIM under a machine gate — so the
    validation page cannot modernise the quote without breaking that gate. The page therefore
    quotes it and states the correction next to the quote. Everywhere else the word must be absent.
    """
    for url in PAGES:
        h = _visible(client.get(url).text)
        # "deflated-sharpe" is a NAMED published method (Bailey & López de Prado), not our label
        h = re.sub(r"deflated[-\s]?sharpe", "", h, flags=re.I)
        if url == "/dash/home/validation":
            assert "every ratio named in these rows is a <b>return/vol</b> ratio" in h
            h = re.sub(r'<td class="g-tledger">.*?</td>', "", h, flags=re.S)
        assert not re.search(r"sharpe", h, re.I), url   # : "sharpest" is a word
    for mod in (journey, T, R, pat_dock):
        assert not re.search(r"sharpe", open(mod.__file__, encoding="utf-8").read(), re.I)


def test_boxes_scroll_internally_rather_than_running_the_page_forever(client):
    """Standing correction #3 — fixed-size boxes that scroll INTERNALLY."""
    for url in ("/dash/home/glossary", "/dash/home/validation", "/dash/home/strategy-ref"):
        h = client.get(url).text
        assert "g-tscroll" in h and "max-height:" in h, url
