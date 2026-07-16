"""test_pat_coverage.py — the PAT-COVERAGE gate (the self-maintaining Pat arrangement).

Why this test exists
--------------------
`test_dash_route_registry.py` (S-H) proves every `/dash` route is *registered*; its twin
`test_education_coverage.py` (S-C) proves every lens carries the education scaffold. This is
the THIRD member of that family and the one Ramana asked for by name: **every routed lens
must be KNOWN TO PAT**, so that shipping a new metric / lens / strategy AUTOMATICALLY makes
Pat aware of it (or the build breaks). Pat has exactly three knowledge sources, and each is
self-feeding:

    A. JARGON   → docs/metrics-glossary.md   (auto-folds into Pat at import via
                  src/pat/glossary.py:_merge_web() — a term added to the md teaches Pat
                  with ZERO code).
    B. PAGES    → src/web/lens_registry.py    (src/pat/nav_flow.py reads the registry, so a
                  new lens is reachable + the ⌘K palette lists it with ZERO code).
    C. INLINE   → the per-flow files (src/pat/*_flow.py) — hand-written per lens.

This gate makes A+B+C mandatory. It derives the lens set from `lens_registry` (so it can
never drift) and asserts every routed lens's Pat coverage is exactly one of:

    DATA    — a bound inline flow returns THIS lens's data (src/pat/*_flow.py). The
              strongest coverage; declared in PAT_DATA (lens_key -> flow), and the flow is
              verified to be a real, wired flow (engine._VALID / web._FLOW_LABEL).
    EXPLAIN — the lens's anchor metric is DEFINED in the glossary, so Pat can explain what
              the page is about. Declared in PAT_EXPLAIN (lens_key -> glossary slug), and
              the slug is verified to resolve in the (md-fed) GLOSSARY — so it auto-folds:
              keep/adjust the definition in docs/metrics-glossary.md and it still passes.
    NAV     — Pat covers the lens by NAVIGATION only (it can name + link the page). This is
              the weakest coverage and a reviewed decision: an entry in NAV_ONLY WITH
              (owner, rationale), and navigate is verified to actually resolve the lens.

A routed lens in NONE of the three FAILS the build — you cannot add a nav page and forget
to make Pat aware of it. That is the whole arrangement: from now on Pat learns every new
surface automatically (glossary term + registry entry) or a human makes a deliberate,
recorded decision that nav-only is enough.

Plus the glossary half of SURFACE-PLAYBOOK item 5 (a NEW check): every custom metric COLUMN
Screen+ surfaces must carry a glossary key (or an explicit '' opt-out) — so a new metric
can't ship without teaching Pat + the ? popovers its meaning. See
test_screener_columns_are_glossary_backed.

Run
---
    pytest tests/test_pat_coverage.py       # as a gate
    python  tests/test_pat_coverage.py       # prints the full coverage table
"""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.web import lens_registry as LR         # noqa: E402
from src.pat import engine as ENGINE            # noqa: E402
from src.pat import nav_flow as NAV             # noqa: E402
from src.pat.glossary import GLOSSARY           # noqa: E402


# ── DERIVED truth — the routed-lens set, straight from the single-source registry ─────
# (identical basis to the route + education gates; a new lens auto-appears here.)
ROUTED: dict[str, object] = {ln.key: ln for ln in LR.LENSES if ln.route}


# ── the vocabulary of REAL, WIRED flows (derived, never hand-listed) ──────────────────
# A flow is real if the engine sanitizer knows it (engine._VALID) OR the web renderer has a
# label + dispatch for it (web._FLOW_LABEL — includes the deterministic-only flows like
# `overdue` that never pass through the LLM sanitizer). Either proves the flow exists + renders.
def _valid_flows() -> set[str]:
    flows = set(ENGINE._VALID)
    try:
        from src.pat import web as PW
        flows |= set(PW._FLOW_LABEL)
    except Exception:
        pass
    return flows


VALID_FLOWS = _valid_flows()


# ── A. DATA — lens_key -> the Pat flow that returns THIS lens's data inline ────────────
# The strongest coverage. Each flow is verified to be a real, wired flow below. A new
# inline flow moves its lens FROM nav_only TO here (the self-maintaining upgrade path).
PAT_DATA: dict[str, str] = {
    "attention":        "whatchanged",   # the signal-event bus rail inline (S-E Ph2)
    "market-internals": "internals",     # market breadth + the effort tape (S-E Ph2)
    "seasonal-tape":    "seasonal",      # calendar base-rate ranking + per-symbol (S150)
    "seasonal-screen":  "seasonal",      # this-month base rates
    "event-cadence":    "overdue",       # which names are overdue vs their own rhythm
    "rs-hub":           "rs",            # the RS leaders/laggards ranking
    "leaders":          "rs",            # strong-in-strong / weak-in-weak
    "rotation":         "rotation",      # a stock's RS-rotation phase inline (S-E Ph2)
    "participants":     "participants",  # FII index-futures net stance (S-E Ph2)
    "wire":             "news",          # inline headlines (S-E Ph2)
    "concalls":         "credibility",   # CCI track record
    "strategist":       "strategy",      # every strategy board in one place
    "compare":          "compare",       # A-vs-B side by side
    "screen2":          "fundamentals",  # Screen+ — the fundamentals screen
    "screener":         "fundamentals",  # the classic fundamentals screen
    "stocks":           "accumulation",  # the DVPT positioning / accumulation-setups board
    # ── S150 Part 2: per-symbol Ownership & filings — one bundled `filings` flow ──
    "insider":          "filings",       # per-symbol SEBI PIT / insider deals (S150)
    "ratings":          "filings",       # per-symbol credit-rating actions (S150)
    "sast":             "filings",       # per-symbol SAST stake/pledge disclosures (S150)
    "shp":              "filings",       # per-symbol shareholding QoQ deltas (S150)
    "wolfe-scan":       "wolfe",         # currently-open Wolfe setups inline (S150)
    "rule-lab":         "rulelab",       # latest rule-lab gauntlet verdict inline (S157-b)
    "inbox":            "inbox",         # what's waiting on the human, inline (S160 — was
                                         # EXPLAIN-only: Pat could define "review inbox" but
                                         # not say what sat in it, so nothing ever told him)
    "strategy-ref":     "methodology",   # plain-language strategy explainers (S150 Phase 3)
}


# ── B. EXPLAIN — lens_key -> the glossary slug that anchors the lens's metric ──────────
# Pat can explain what the page is about because its core metric is DEFINED in the glossary
# (docs/metrics-glossary.md folds in via _merge_web, so this auto-folds — keep/adjust the
# definition in the md and the anchor still resolves). The slug is verified ∈ GLOSSARY below.
PAT_EXPLAIN: dict[str, str] = {
    "mep":              "mep",              # signed accumulation/distribution
    "cpr":              "cpr",              # central pivot range structure
    "momentum-scan":    "riskadj",          # the risk-adjusted momentum metric
    "factor-league":    "factor_league",    # classic factor families, ranked by our numbers
    "model-portfolios": "model_portfolios",  # engine-managed model books
    "sector-rotation":  "sector_rotation",   # the V17 RS sector-rotation book (time-travel)
    "surveillance":     "asm",              # ASM/GSM surveillance states
    "capture-map":      "up_capture",       # up/down-capture behaviour
    "rsband":           "rs_band",          # the relative-strength band (support/resistance)
    "rrg":              "rs_ratio",         # the RRG map plots RS-Ratio × RS-Momentum
}


# ── C. NAV — Pat covers the lens by NAVIGATION only (name + link) ──────────────────────
# A reviewed decision: (owner, rationale). navigate is verified to actually resolve each
# lens below. To UPGRADE a lens: bind an inline flow (→ PAT_DATA) or add its metric to the
# glossary + anchor it (→ PAT_EXPLAIN), in the same commit, and delete its row here.
NAV_ONLY: dict[str, tuple[str, str]] = {
    "markets":            ("markets", "the market home/overview — a landing surface, not a single "
                                      "metric; Pat points to it, no inline data flow"),
    "move-anatomy":       ("markets", "aggregate move-precursor fingerprint — a market-wide study "
                                      "board; nav is right until a per-symbol read exists"),
    "seasonal-divergence": ("markets", "two-index calendar co-movement — a descriptive board; the "
                                       "per-symbol seasonal base rate is covered by the seasonal flow"),
    "actions":            ("markets", "corporate-actions calendar (ex-dates/dividends) — a forward "
                                      "calendar board; nav is the right coverage"),
    "buyback-calc":       ("markets", "buyback tender-quota calculator — an interactive tool, not a "
                                      "screen; Pat links it"),
    "band-locks":         ("markets", "names pinned at their price band — a surveillance board; "
                                      "candidate for a future whatchanged-style flow"),
    "sectors":            ("markets", "sector relative-strength board — market-wide; the per-symbol "
                                      "rotation state is covered by the rotation flow"),
    "sector-economics":   ("markets", "median ROCE/OPM by sector over a decade — an aggregate "
                                      "fundamentals board; nav is right"),
    "results-reactions":  ("markets", "earnings-reaction war-room — a forward calendar board; the "
                                      "PEAD book is descriptive-only; nav is right"),
    "cycle-clock":        ("markets", "sectors on the rotation loop — a market-wide chart; sibling "
                                      "of the rotation flow's per-symbol read"),
    "divergence":         ("markets", "price-vs-RS divergence board — market-wide; a candidate future "
                                      "per-symbol flow"),
    "early-signals":      ("markets", "earliest pre-breakout reads — a market-wide board; nav is right"),
    "sector-momentum":    ("markets", "RS/momentum drill inside a sector — a market-wide drill; nav "
                                      "is right"),
    "harmonic-scan":      ("markets", "harmonic XABCD/PRZ scanner — descriptive-only pattern board; "
                                      "candidate future open-setups flow (sibling of wolfe)"),
    "themes":             ("screener", "tagged baskets of names — a grouping surface, not a metric; "
                                       "Pat links it"),
    "tags-review":        ("screener", "the tag-review queue — an owner workflow surface; nav is right"),
    "workbench":          ("screener", "the screener workbench — an interactive builder; Pat links it"),
    "classics":           ("strategies", "famous named screens as live rosters — a strategy board; the "
                                         "strategy flow covers the strategist hub; nav is right here"),
    "conviction":         ("strategies", "cross-pillar conviction shortlist — a composite board; "
                                         "candidate future confluence-style flow"),
    "stealth":            ("strategies", "stealth-accumulation population — a board sibling of the "
                                         "accumulation flow; nav is right"),
    "growth":             ("strategies", "forward growth-intent from concalls — a board; its anchor "
                                         "metric is not yet a glossary term (a future EXPLAIN upgrade)"),
    "launchpad":          ("strategies", "explosive-move precursor screen — a board; ledger says no "
                                         "edge net of cost; nav is right"),
    "launchpad-track":    ("strategies", "launchpad outcome distribution — a study board; nav is right"),
    "dashboard":          ("tracker", "the tracker dashboard (owner book / demo) — a personal surface, "
                                      "not a market metric; Pat links it"),
    "portfolios":         ("tracker", "tracked portfolios — a personal surface; Pat links it"),
    "watchlists":         ("tracker", "watchlists — a personal surface; Pat links it"),
    "performance":        ("tracker", "tracked performance — a personal surface; Pat links it"),
    "import":             ("tracker", "portfolio/watchlist import — an action surface; Pat links it"),
    "coverage":           ("trust", "the data-coverage / freshness front door — a meta surface; Pat "
                                    "links it (freshness also rides the flow footers)"),
    "testing":            ("trust", "strategy-validation evidence — a methodology surface; the "
                                    "methodology flow explains the strategies themselves"),
    "glossary":           ("trust", "the metric dictionary itself — Pat's explain flow IS this "
                                    "content in conversation; the page is the browsable form"),
    "reading-guide":      ("trust", "the visual how-to-read guide — an education surface; Pat links it"),
    "pat":                ("trust", "Ask Pat itself — you are already talking to Pat; nav is trivially "
                                    "self-referential"),
    "spec-sheets":        ("trust", "the pre-registration study ledger — an evidence surface; Pat "
                                    "links it"),
    "evidence-pack":      ("trust", "the print-ready procurement pack — an assembly surface; Pat "
                                    "links it"),
    "replay-any-date":    ("trust", "point-in-time replay demo — an interactive tool; Pat links it"),
}


# ── the SURFACE-PLAYBOOK item 5/6 lines, embedded in the failure message ──────────────
_PAT_CHECKLIST = """\
A routed /dash lens with NO Pat coverage means a page shipped without teaching Pat about it.
Per docs/SURFACE-PLAYBOOK.md item 5/6 + docs/pat-knowledge-contract.md (SAME commit):
  Pat learns a surface through one of its three self-feeding knowledge sources — pick one:
    DATA    — bind an inline flow: add src/pat/<name>_flow.py + a ₹0 pre-pass in
              engine.route + a web.py render + engine._VALID/_FLOW_LABEL, then add the lens
              to PAT_DATA here (lens_key -> flow).
    EXPLAIN — add the lens's anchor metric to docs/metrics-glossary.md (it auto-folds into
              Pat via glossary._merge_web), then add the lens to PAT_EXPLAIN here
              (lens_key -> its glossary slug).
    NAV     — if link-only coverage is genuinely enough, add the lens to NAV_ONLY here WITH
              an (owner, rationale). navigate already resolves it from the registry; this
              row is the deliberate, reviewed acknowledgement that nav is all Pat gives it.
Prose in a doc does not count — the registration is one of the three machine-readable tables."""


# ── build the app in-process (only needed for the Screen+ column check) ───────────────
def _build_app():
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return M.app


def _classify(key: str) -> str | None:
    if key in PAT_DATA:
        return "DATA"
    if key in PAT_EXPLAIN:
        return "EXPLAIN"
    if key in NAV_ONLY:
        return "NAV"
    return None


# ── the contracts ─────────────────────────────────────────────────────────────────────
def test_every_routed_lens_is_known_to_pat():
    """The gate: every routed lens has DATA, EXPLAIN, or NAV coverage — never unaccounted."""
    offenders = sorted(k for k in ROUTED if _classify(k) is None)
    assert not offenders, (
        f"\n{len(offenders)} routed /dash lens(es) with NO Pat coverage — the Pat-coverage "
        "gate FAILED:\n"
        + "\n".join(f"  !! {k}   [{getattr(ROUTED[k], 'label', '')}]" for k in offenders)
        + "\n\n" + _PAT_CHECKLIST
    )


def test_pat_data_flows_are_real_and_wired():
    """Every PAT_DATA flow must be a real, wired flow (engine._VALID or web._FLOW_LABEL)."""
    bad = sorted(f"{k} -> {flow}" for k, flow in PAT_DATA.items() if flow not in VALID_FLOWS)
    assert not bad, (
        "\nPAT_DATA entries pointing at an unknown/unwired flow (add the flow to "
        "engine._VALID + web._FLOW_LABEL, or fix the name):\n"
        + "\n".join(f"  !! {b}" for b in bad)
        + f"\n(known flows: {sorted(VALID_FLOWS)})"
    )


def test_pat_explain_anchors_resolve_in_the_glossary():
    """Every PAT_EXPLAIN slug must resolve in the (md-fed) GLOSSARY — so the anchor is live
    and auto-folds with the glossary. A removed/renamed term fails here (teaches you to
    re-anchor), which is the point of driftless coverage."""
    bad = sorted(f"{k} -> {slug}" for k, slug in PAT_EXPLAIN.items() if slug not in GLOSSARY)
    assert not bad, (
        "\nPAT_EXPLAIN anchors that no longer resolve in the glossary (define the term in "
        "docs/metrics-glossary.md, or re-anchor to a live slug):\n"
        + "\n".join(f"  !! {b}" for b in bad)
    )


def test_nav_only_entries_carry_owner_and_rationale():
    """NAV_ONLY = a reviewed decision: an (owner, rationale) tuple, both non-empty."""
    bad = [k for k, v in NAV_ONLY.items()
           if not isinstance(v, tuple) or len(v) != 2 or not str(v[0]).strip() or not str(v[1]).strip()]
    assert not bad, "\nNAV_ONLY entries missing owner/rationale:\n" + "\n".join(f"  !! {b}" for b in bad)


def test_nav_only_lenses_are_actually_resolved_by_navigate():
    """The teeth on NAV coverage: Pat must be able to NAME + LINK each nav-only lens. Verify
    navigate resolves it (by key or label) — a lens Pat can't even point to is a real gap."""
    unreachable = []
    for k in NAV_ONLY:
        ln = ROUTED.get(k)
        if ln is None:
            continue  # staleness caught by the disjoint/stale test
        by_key = any(h["key"] == k for h in NAV.resolve(k, limit=6))
        by_label = any(h["key"] == k for h in NAV.resolve(getattr(ln, "label", ""), limit=6))
        if not (by_key or by_label):
            unreachable.append(k)
    assert not unreachable, (
        "\nNAV_ONLY lenses that navigate does NOT resolve (Pat can't point to them — add a "
        "nav hook in nav_flow._HOOKS or a clearer label):\n"
        + "\n".join(f"  !! {k}" for k in unreachable)
    )


def test_coverage_tables_are_disjoint():
    """A lens is DATA, EXPLAIN, or NAV — never in two tables (a category error)."""
    tables = {"PAT_DATA": set(PAT_DATA), "PAT_EXPLAIN": set(PAT_EXPLAIN), "NAV_ONLY": set(NAV_ONLY)}
    overlaps = []
    for a in tables:
        for b in tables:
            if a < b:
                both = sorted(tables[a] & tables[b])
                if both:
                    overlaps.append(f"{a} ∩ {b}: {both}")
    assert not overlaps, "\nLenses in >1 coverage table:\n" + "\n".join(f"  !! {o}" for o in overlaps)


def test_no_stale_coverage_entries():
    """Every table key must still be a routed lens (no dead config)."""
    stale = []
    for name, keys in (("PAT_DATA", PAT_DATA), ("PAT_EXPLAIN", PAT_EXPLAIN), ("NAV_ONLY", NAV_ONLY)):
        for k in keys:
            if k not in ROUTED:
                stale.append(f"{name}: {k} is listed but is no longer a routed lens — remove it")
    assert not stale, "\nStale Pat-coverage entries:\n" + "\n".join(f"  !! {s}" for s in stale)


def test_synthetic_uncovered_lens_is_flagged():
    """The Done criterion: a routed lens in none of the three tables is an OFFENDER — proving
    the contract bites on a NEW un-registered page, not just today's inventory."""
    synthetic = "__synthetic_uncovered_lens__"
    assert synthetic not in PAT_DATA and synthetic not in PAT_EXPLAIN and synthetic not in NAV_ONLY
    assert _classify(synthetic) is None    # would be an offender if it were routed


def test_screener_columns_are_glossary_backed():
    """SURFACE-PLAYBOOK item 5 (the glossary half), machine-enforced: every custom metric
    COLUMN Screen+ surfaces carries a glossary key (so its meaning is taught to Pat + the ?
    popovers) — or an explicit '' opt-out (undocumented / would mis-resolve). A new metric
    column with an undocumented key FAILS: add the term to docs/metrics-glossary.md first."""
    from src.web import glossary as WG
    from src.web.screener_plus import SCREEN2_COLS, SCREEN2_COL_TERMS
    WG._load()
    assert len(SCREEN2_COLS) == len(SCREEN2_COL_TERMS), "column label/term lists drifted out of alignment"
    missing = [(c, t) for c, t in zip(SCREEN2_COLS, SCREEN2_COL_TERMS) if t and not WG.has(t)]
    assert not missing, (
        "\nScreen+ metric columns whose glossary key does NOT resolve in docs/metrics-glossary.md "
        "(define the term there first, or set its col_term to '' to opt out):\n"
        + "\n".join(f"  !! column {c!r} -> glossary key {t!r}" for c, t in missing)
    )


def test_coverage_basis_is_non_degenerate():
    """Sanity: the derivation actually populated the buckets (catches a broken import that
    would make everything fall through)."""
    counts = {"DATA": 0, "EXPLAIN": 0, "NAV": 0, "OFFENDER": 0}
    for k in ROUTED:
        counts[_classify(k) or "OFFENDER"] += 1
    assert len(ROUTED) > 50, f"too few routed lenses ({len(ROUTED)}) — registry import looks broken"
    for kind in ("DATA", "EXPLAIN", "NAV"):
        assert counts[kind] > 0, f"no lenses classified {kind} — derivation looks broken ({counts})"


# ── human-readable report ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rows = []
    for k in sorted(ROUTED):
        kind = _classify(k) or "!!OFFENDER"
        detail = ""
        if kind == "DATA":
            detail = "flow=" + PAT_DATA[k]
        elif kind == "EXPLAIN":
            detail = "glossary=" + PAT_EXPLAIN[k]
        elif kind == "NAV":
            detail = "nav-only (" + NAV_ONLY[k][0] + ")"
        rows.append((kind, k, detail, getattr(ROUTED[k], "label", "")))
    for kind, k, detail, label in rows:
        print(f"{kind:10} {k:20} {detail:26} [{label}]")
    counts: dict[str, int] = {}
    for kind, *_ in rows:
        counts[kind] = counts.get(kind, 0) + 1
    print(f"\n{len(rows)} routed lenses · "
          + " · ".join(f"{v} {k.lower()}" for k, v in sorted(counts.items())))
    off = [r for r in rows if r[0] == "!!OFFENDER"]
    if off:
        print("\nFAIL — offenders:\n" + "\n".join(f"  !! {r[1]}" for r in off))
        raise SystemExit(1)
    print("PASS — every routed lens is known to Pat (DATA / EXPLAIN / NAV).")
