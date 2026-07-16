"""Contracts for the feed/signal manifests + THE LICENCE GATE (D134 LANE-C; plan s4-C, L1/L3/L8).

What this gate file enforces:
  1. REGISTRY HYGIENE - src/automation/feed_manifest.py imports; every manifest row's module
     file exists on disk (file-existence, not import: several feed modules import third-party
     fetch deps (requests/bs4/feedparser/anthropic) that are not present in every dev venv,
     and importing fetchers in a gate would couple the suite to network-code import side
     effects); keys match dict keys; no empty fields; licence_class in the frozen enum;
     validation_status in the frozen ledger vocabulary.
  2. COVERAGE RATCHET - (a) len(FEEDS) >= MIN_FEEDS and len(SIGNALS) >= MIN_SIGNALS (dropping
     a row without consciously lowering the constant fails); (b) the FETCHER SCAN: every
     src/automation module whose source matches the fetcher heuristic (imports fetch_retry, or
     calls requests.get/Session/post, or touches urllib.request) MUST appear in FEEDS, in
     UNCLASSIFIED_FEEDS, or in KNOWN_NON_FEEDS - so a brand-new fetcher module without a
     manifest row fails the suite.
  3. FENCE PINS - validation_status strings mirror docs/strategy-ledger.md verdicts VERBATIM
     and specific signals are pinned (cci=falsified-as-factor, momentum=benchmark-gross-only,
     ...); softening a fence requires consciously editing this test in the same commit as the
     ledger verdict change.
  4. THE LICENCE GATE (plan s3.4(3)) - no feed with licence_class in {licensed,
     personal-broker} may be referenced by any src/web/*.py source.

     v1 APPROXIMATION (documented per the LANE-C spec): the gate is a conservative SOURCE-TEXT
     scan - a restricted feed "is referenced" if its module basename, its registry key, or any
     of its owned table names appears as a substring in any src/web/*.py file. Limits accepted
     for v1: (a) it cannot see truly dynamic access (SQL assembled at runtime from config, or a
     web module reading a restricted table through an intermediary helper module - only direct
     src/web sources are scanned, not src/pat or templates); (b) substring matching means a
     comment or docstring mention also fails - deliberately conservative, fails safe; (c) the
     restricted set is EMPTY today (all current feeds are public-archive or derived), so the
     real-registry gate is vacuously green - therefore a synthetic-feed test proves the scanner
     itself has teeth, so the gate is live the day LANE-I registers the personal-broker
     intraday seam.

  4b. §7.7(a) VENDOR-ToS IMPORT GATE (Ramana ratified §7.7 Option B, 2026-07-16) - no
     src/web/*.py may IMPORT any of the 6 UNCLASSIFIED_FEEDS vendor fetchers; importing one
     pulls a vendor-ToS scrape onto a public request. AST-based (imports only) because a
     key/table substring scan is useless here - the keys name legit routes (/dash/screener),
     the CCI lens, an unrelated helper, and primary-sourced table displays.

Run: pytest tests/test_feed_manifest.py   (or bare: python tests/test_feed_manifest.py)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # repo root (bare-run + pytest)

from src.automation import feed_manifest as fm

# --------------------------------------------------------------------------------------
# 1. Registry hygiene
# --------------------------------------------------------------------------------------


def test_module_imports_and_registries_nonempty():
    assert isinstance(fm.FEEDS, dict) and fm.FEEDS, "FEEDS registry missing/empty"
    assert isinstance(fm.SIGNALS, dict) and fm.SIGNALS, "SIGNALS registry missing/empty"
    assert fm.validate() == [], "feed_manifest.validate() problems: %s" % fm.validate()


def test_feed_rows_hygiene():
    for key, feed in fm.FEEDS.items():
        assert feed.key == key, "FEEDS[%r].key mismatch" % key
        mod = REPO / feed.module
        assert mod.is_file(), "FEEDS[%r] module missing on disk: %s" % (key, feed.module)
        assert feed.licence_class in fm.LICENCE_CLASSES, (
            "FEEDS[%r] licence_class %r not in enum" % (key, feed.licence_class)
        )
        assert feed.tables, "FEEDS[%r] owns no tables" % key
        for name in ("source_org", "cadence", "knowable_rule", "fence_status", "notes"):
            assert getattr(feed, name).strip(), "FEEDS[%r].%s empty" % (key, name)


def test_signal_rows_hygiene():
    for key, sig in fm.SIGNALS.items():
        assert sig.key == key, "SIGNALS[%r].key mismatch" % key
        for token in sig.module.split():
            assert token.endswith(".py"), "SIGNALS[%r] module token %r not a .py path" % (key, token)
            assert (REPO / token).is_file(), "SIGNALS[%r] module missing: %s" % (key, token)
        assert sig.validation_status in fm.VALIDATION_STATUSES, (
            "SIGNALS[%r] status %r not in the ledger vocabulary" % (key, sig.validation_status)
        )
        assert sig.inputs, "SIGNALS[%r] has no inputs" % key
        assert sig.fence.strip(), "SIGNALS[%r].fence empty" % key
        assert sig.ledger_ref.strip(), "SIGNALS[%r].ledger_ref empty" % key


def test_licence_enum_is_the_planned_four():
    assert fm.LICENCE_CLASSES == frozenset(
        {"public-archive", "licensed", "personal-broker", "derived"}
    ), "licence enum drifted from plan s3.4(3)"
    assert fm.RESTRICTED_LICENCE_CLASSES == frozenset({"licensed", "personal-broker"})
    assert fm.RESTRICTED_LICENCE_CLASSES < fm.LICENCE_CLASSES


# --------------------------------------------------------------------------------------
# 2. Coverage ratchet
# --------------------------------------------------------------------------------------


def test_coverage_ratchet_counts():
    assert fm.MIN_FEEDS >= 21, "MIN_FEEDS lowered below the D134 LANE-C catalogue (21)"
    assert fm.MIN_SIGNALS >= 10, "MIN_SIGNALS lowered below the D134 LANE-C catalogue"
    assert len(fm.FEEDS) >= fm.MIN_FEEDS, (
        "FEEDS shrank: %d < MIN_FEEDS %d - a feed row was removed without a conscious "
        "ratchet change" % (len(fm.FEEDS), fm.MIN_FEEDS)
    )
    assert len(fm.SIGNALS) >= fm.MIN_SIGNALS


_FETCHER_RE = re.compile(r"requests\.(?:get|Session|post)\(")


def _looks_like_fetcher(text: str) -> bool:
    return (
        "fetch_retry import" in text
        or "import fetch_retry" in text
        or "urllib.request" in text
        or bool(_FETCHER_RE.search(text))
    )


def test_coverage_ratchet_every_fetcher_has_a_manifest_row():
    """A new fetcher module in src/automation without a manifest row FAILS the suite."""
    covered = (
        {Path(f.module).stem for f in fm.FEEDS.values()}
        | set(fm.UNCLASSIFIED_FEEDS)
        | set(fm.KNOWN_NON_FEEDS)
    )
    missing = []
    for py in sorted((REPO / "src" / "automation").glob("*.py")):
        if py.name in ("__init__.py", "feed_manifest.py"):
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        if _looks_like_fetcher(text) and py.stem not in covered:
            missing.append(py.stem)
    assert not missing, (
        "fetcher modules with NO manifest row (add a Feed row, or an UNCLASSIFIED_FEEDS / "
        "KNOWN_NON_FEEDS entry with the reason): %s" % missing
    )


def test_unclassified_discipline():
    """The Screener-era + per-source-ToS feeds stay OUT of FEEDS until the enum decision."""
    expected = {
        "screener",
        "fundamentals_history",
        "shareholding_history",
        "concalls",
        "news_feed",
        "enrich",
    }
    assert expected <= set(fm.UNCLASSIFIED_FEEDS), (
        "an UNCLASSIFIED feed disappeared - if it was classified into FEEDS, that requires "
        "the recorded LANE-R/Ramana enum decision (see feed_manifest module docstring TODO)"
    )
    overlap = set(fm.UNCLASSIFIED_FEEDS) & set(fm.FEEDS)
    assert not overlap, "feeds are BOTH unclassified and classified: %s" % sorted(overlap)
    for key, why in fm.UNCLASSIFIED_FEEDS.items():
        assert why.strip(), "UNCLASSIFIED_FEEDS[%r] has no reason" % key


# --------------------------------------------------------------------------------------
# 3. Fence pins (never soften a ledger verdict)
# --------------------------------------------------------------------------------------


def test_validation_vocabulary_pinned_to_ledger_verdicts():
    assert fm.VALIDATION_STATUSES == frozenset(
        {
            "descriptive-only",
            "falsified-as-factor",
            "benchmark-gross-only",
            "validated-screen-only",
            "not-return-tested-as-standalone-alpha",
        }
    ), (
        "validation_status vocabulary drifted - it must mirror docs/strategy-ledger.md "
        "verdicts verbatim; change it only in the same commit as a ledger verdict change"
    )


def test_signal_fences_never_soften():
    pins = {
        "cci": "falsified-as-factor",
        "mep": "descriptive-only",
        "wolfe": "descriptive-only",
        "dvpt": "descriptive-only",
        "seasonal": "descriptive-only",
        "momentum_factor": "benchmark-gross-only",
        "launchpad": "validated-screen-only",
        "patearn_score": "not-return-tested-as-standalone-alpha",
    }
    for key, status in pins.items():
        assert key in fm.SIGNALS, "flagship signal %r missing from SIGNALS" % key
        got = fm.SIGNALS[key].validation_status
        assert got == status, (
            "SIGNALS[%r] verdict softened/changed: %r != ledger %r - a fence may only move "
            "with its docs/strategy-ledger.md entry" % (key, got, status)
        )


# --------------------------------------------------------------------------------------
# 4. THE LICENCE GATE (v1 source-scan; approximation documented in the module docstring)
# --------------------------------------------------------------------------------------


def _web_sources() -> dict:
    out = {}
    for py in sorted((REPO / "src" / "web").glob("*.py")):
        out[py.name] = py.read_text(encoding="utf-8", errors="replace")
    return out


def _gate_offenders(feed, web_sources: dict) -> list:
    """Web files referencing a restricted feed (by module basename, key, or owned table)."""
    needles = {Path(feed.module).stem, feed.key} | set(feed.tables)
    offenders = []
    for name, text in sorted(web_sources.items()):
        hits = sorted(n for n in needles if n and n in text)
        if hits:
            offenders.append((name, hits))
    return offenders


def test_licence_gate_no_restricted_feed_on_public_surfaces():
    web = _web_sources()
    assert web, "src/web/*.py not found - gate cannot run"
    violations = []
    for feed in fm.restricted_feeds():
        for name, hits in _gate_offenders(feed, web):
            violations.append("%s (licence_class=%s) referenced by src/web/%s via %s"
                              % (feed.key, feed.licence_class, name, hits))
    assert not violations, (
        "LICENCE GATE: restricted-class data must stay off every public surface "
        "(plan s3.4(3)):\n  " + "\n  ".join(violations)
    )


def test_licence_gate_scanner_has_teeth():
    """Prove the scan catches a real reference (the restricted set is empty today)."""
    synthetic = fm.Feed(
        key="_synthetic_restricted",
        module="src/automation/signals.py",  # stem 'signals' - ubiquitous in web sources
        source_org="test",
        cadence="test",
        licence_class="personal-broker",
        knowable_rule="test",
        fence_status="test",
        tables=("stock_signals",),  # read by many src/web modules
        notes="synthetic fixture - proves the gate is not dead code",
    )
    offenders = _gate_offenders(synthetic, _web_sources())
    assert offenders, (
        "the licence-gate scanner failed to flag a feed whose table (stock_signals) is "
        "known to be read by src/web - the gate has gone blind"
    )


# --------------------------------------------------------------------------------------
# 4b. §7.7(a) — the VENDOR-ToS IMPORT GATE (Ramana ratified §7.7 Option B, 2026-07-16)
#     The 6 UNCLASSIFIED_FEEDS (screener · fundamentals_history · shareholding_history ·
#     concalls · news_feed · enrich) stay OUT of FEEDS; their KEYS are the fetcher module
#     stems (pinned by the coverage ratchet above). A public surface importing one of these
#     fetchers would pull a vendor-ToS scrape onto a live request - the leak Guardrail #8
#     forbids. A key/table SUBSTRING scan cannot enforce this: 'screener' names the /dash/
#     screener route, 'concalls' the CCI lens, 'enrich' an unrelated helper, and the
#     fundamentals_history / shareholding_history TABLES are legitimately displayed (they are
#     re-sourced via XBRL). So the gate is IMPORT-based, via the AST (imports only, never
#     comments / strings / route literals).
# --------------------------------------------------------------------------------------


def _automation_module_imports(text: str) -> set:
    """Fully-qualified `src.automation.<mod>` modules a file imports. Handles
    `import src.automation.x`, `from src.automation import x [as y]`, and
    `from src.automation.x import y`."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    hit = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("src.automation."):
                    hit.add(".".join(a.name.split(".")[:3]))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "src.automation" or mod.endswith(".automation"):
                for a in node.names:
                    hit.add("src.automation." + a.name)
            elif mod.startswith("src.automation."):
                hit.add(".".join(mod.split(".")[:3]))
    return hit


def test_vendor_tos_fetchers_never_imported_by_public_surfaces():
    """§7.7(a): no public src/web surface may import a vendor-ToS fetcher."""
    vendor_mods = {"src.automation." + key for key in fm.UNCLASSIFIED_FEEDS}
    violations = []
    for name, text in sorted(_web_sources().items()):
        leaked = sorted(vendor_mods & _automation_module_imports(text))
        if leaked:
            violations.append("src/web/%s imports %s" % (name, ", ".join(leaked)))
    assert not violations, (
        "§7.7(a) VENDOR-ToS GATE: a public surface imports a vendor-ToS fetcher - the 6 "
        "UNCLASSIFIED_FEEDS must stay off src/web (Ramana ratified Option B, 2026-07-16). "
        "If the data is genuinely needed, source it from the primary XBRL/BSE replacement, "
        "never the vendor scrape:\n  " + "\n  ".join(violations)
    )


def test_vendor_tos_import_gate_has_teeth():
    """Prove the §7.7(a) AST scan flags a real vendor-fetcher import (none exist today)."""
    vendor_mods = {"src.automation." + k for k in fm.UNCLASSIFIED_FEEDS}
    for snippet in (
        "from src.automation import screener\n",
        "from src.automation import scoring, news_feed as _n\n",
        "import src.automation.enrich\n",
        "from src.automation.shareholding_history import fetch\n",
    ):
        got = _automation_module_imports(snippet)
        assert got & vendor_mods, (
            "the §7.7(a) import scanner failed to flag a vendor-fetcher import: %r -> %r"
            % (snippet, sorted(got))
        )


def test_selftest_green_and_prints_both_tables():
    rc = fm.main(["--selftest"])
    assert rc == 0, "feed_manifest --selftest failed"
    feeds_tbl = fm.render_feeds_table()
    signals_tbl = fm.render_signals_table()
    for key in fm.FEEDS:
        assert key in feeds_tbl, "feed %r missing from the rendered FEEDS table" % key
    for key in fm.SIGNALS:
        assert key in signals_tbl, "signal %r missing from the rendered SIGNALS table" % key


# --------------------------------------------------------------------------------------
# bare-run support (house convention)
# --------------------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS %s" % name)
            except AssertionError as exc:
                failures += 1
                print("FAIL %s\n     %s" % (name, exc))
    raise SystemExit(1 if failures else 0)
