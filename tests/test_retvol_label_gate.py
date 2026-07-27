"""Return/vol label gate — the "it's not a Sharpe" fence, machine-enforced (D142, S162).

Every performance ratio this project computes is `mean / sd * sqrt(periods)` with NO
risk-free rate subtracted. That is a RETURN/VOL RATIO, not a Sharpe ratio: a Sharpe is
the excess return over cash per unit of risk, and we subtract nothing, so our number
reads HIGH against a textbook Sharpe on the same book.

The audit behind D142 found the mislabel in 40+ places across research/ and on nine live
surfaces. It kept coming back because "Sharpe" is simply the word people reach for. So
the fix is a gate, not a memo: this is the sixth gate beside route / education /
doc-hygiene / state-doc / compliance-language.

What it does: scans the rendering trees (src/web + src/pat — all site HTML lives in these
.py string literals) plus src/automation (which composes the text those surfaces show) and
fails on any line containing the word "Sharpe" that is not one of:

  1. an explicit DISCLOSURE — the line says our number is NOT a Sharpe. This is the whole
     point of the ruling: the word may appear in order to disown it.
  2. "Deflated Sharpe" / "Deflated-Sharpe" — the Bailey & Lopez de Prado statistic. That
     is a proper noun from the literature and stays. (Its own no-rf caveat is documented
     at the two call sites in research/, which this gate does not scan.)
  3. an _ALLOW entry with a written reason.

Stale _ALLOW entries fail the suite, so the list can only shrink honestly.

S166 extension (the D142 block's queued follow-on): the gate now ALSO polices
  - the reader-facing docs tier — docs/strategies/** (served at /dash/strategy-ref),
    docs/metrics-glossary.md (served at /dash/glossary), and the canonical top docs
    (_DOC_TARGETS) — these are where readers actually meet the numbers;
  - research/**/*.py — minus two structural exemptions, each with its reason written
    where it acts: hash-frozen preregistrations (*PREREG* — an edit voids the recorded
    seal) and the concluded V-ladder's repro-of-record scripts (_REPRO_OF_RECORD —
    their docstrings say "FROZEN, never edited"; their printed headers quote the era's
    recorded tables, which the strategy-ledger banner disowns wholesale).

docs/strategy-ledger.md is deliberately NOT line-scanned: it is an append-only record
whose rows rule_lab.py byte-compares verbatim (D142 carve-out #2). Its file-level disown
is the estate-wide banner, which test_the_ledger_banner_disowns_the_label asserts is
really there. The carve-out is about DESYNC, not about the label being permanent: the
BLOCKING table — doctrine that live surfaces quote, not a dated session record — was
relabelled on 2026-07-27 by moving the ledger and its rule_lab mirror in ONE commit, which
is the only way that pair may ever move. The dated session entries below it stay as written.

Still NOT policed: the rolling session records (PROJECT_STATE.md,
docs/NEXT-SESSION-CARRYFORWARD.md — they quote experiment history verbatim), the
historical/archived analysis docs outside _DOC_TARGETS (session-era records; rewriting
them is rewriting history), and the on-disk `sharpe` COLUMN in research.db
(strategy_store.py keeps the legacy name deliberately — CREATE TABLE IF NOT EXISTS
cannot migrate existing rows; the value is rendered as "Return/vol" by testing_view.py).

Why a label gate and not a re-cut: a true Sharpe needs a risk-free-rate ingest from a
primary source (Guardrail #8 — NSE/BSE/SEBI/XBRL, never a vendor). That MOVES NUMBERS and
is queued to land with the owed TR-benchmark re-cut, which moves the same figures. Until
then the honest move is to name the thing correctly — which is exactly what this enforces.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_TREES = ("src/web", "src/pat", "src/automation")

# Reader-facing docs (S166): directories are globbed for *.md (a NEW strategy page is
# auto-policed), single files are themselves.
_DOC_TARGETS = (
    "docs/strategies",                       # served at /dash/strategy-ref
    "docs/metrics-glossary.md",              # served at /dash/glossary
    "docs/FABLE-PROTOCOL.md",
    "docs/SURFACE-PLAYBOOK.md",
    "docs/patearn-analytics-company-plan.md",
    "docs/patearn-charter.md",
)
_RESEARCH_TREE = "research"

# Files this gate deliberately does not scan, each with its reason. Structural — not a
# per-line allowlist — because the constraint is on the FILE (a seal, a frozen record),
# not on any one sentence.
_REPRO_REASON = (
    "Repro-of-record script of the concluded V-ladder (D139/D140, arc retired): its "
    "docstring says FROZEN/never-edited and its printed table headers quote the "
    "recorded era's labels. Relabelling would desync the script's output from the "
    "recorded tables it exists to reproduce; the record itself is disowned wholesale "
    "by the strategy-ledger banner this gate asserts.")
_FILE_EXEMPT: dict[str, str] = {
    "research/explosive_moves/hedge_density_v2_PREREG.md":
        "Hash-frozen preregistration — its sha256 is recorded in the ledger; an edit "
        "voids the seal. The label vocabulary inside is the era's, disowned estate-wide "
        "by the strategy-ledger banner.",
    "research/explosive_moves/sector_rotation_exp.py":  _REPRO_REASON,
    "research/explosive_moves/sector_rotation_exp2.py": _REPRO_REASON,
    "research/explosive_moves/sector_rotation_exp3.py": _REPRO_REASON,
    "research/explosive_moves/sector_rotation_exp4.py": _REPRO_REASON,
    "research/explosive_moves/sector_rotation_v24_final.py": _REPRO_REASON,
    "research/explosive_moves/v24_cull.py": _REPRO_REASON,
    "research/explosive_moves/v24_pond.py": _REPRO_REASON,
}

# A line may say "Sharpe" if it is DISOWNING the label. Matched against a small WINDOW of
# surrounding lines, not the line alone: these disclosures live in wrapped string literals,
# so "NOT a / Sharpe ratio: no risk-free rate is subtracted" routinely straddles a newline
# and a line-only scan would flag the very sentences that make the estate honest.
_DISCLOSURE = (
    "NOT a Sharpe",
    "not a Sharpe",
    "textbook Sharpe",
    "never Sharpe",
    "no risk-free rate is subtracted",      # the canonical disclosure, any phrasing around it
    "no risk-free subtracted",              # sector_rotation_view's D139 tooltip
    "true Sharpe needs",                    # the queued-re-cut disclosure (D142)
    "Sharpe ratio. Labelled accordingly",   # sector_rotation_view's D139 docstring
    "Sharpe, and reads high against one",   # factor_league_view's docstring
    "not Sharpe, because that is what was measured",
    "not Sharpe",                           # subsumes bare disowns: 'is not "Sharpe"', 'RATIOS, not Sharpe ratios'
    "true-Sharpe",                          # the queued rf re-cut, hyphenated (docs vocabulary)
    "true excess",                          # 'true excess-return Sharpes are ~0.51' — naming the honest number
    "really a RETURN/VOL RATIO",            # sector-rotation.md's own disclosure-block heading
    # S190/16AY: the D142 rf RE-CUT landed — research/explosive_moves ratio sites now genuinely
    # subtract rf (excess basis), so a "Sharpe" mention that CITES the re-cut basis is the
    # honest label, not the old defect. The citation is mandatory: a bare "Sharpe" without a
    # disown or a 16AY/excess-basis citation still fails. The gate's purpose (no RAW ratio
    # sold as a Sharpe) is unchanged — pre-16AY surfaces and docs keep the old rules.
    "16AY",                                 # the re-cut ledger citation carried at every cut site
    "excess-basis",                         # the basis statement itself ('EXCESS-basis true Sharpe…')
)
_WINDOW = 2   # lines of context each side — enough to span a wrapped disclosure


def _norm(s: str) -> str:
    """Collapse Python string-concatenation artifacts so a wrapped disclosure reads as prose.

    These disclosures live inside adjacent string literals, so the source for one sentence is
    `'... — NOT a '` / `'Sharpe ratio: no risk-free rate ...'`. Joined raw, that is
    `... NOT a ' 'Sharpe ratio ...` and no marker matches — the gate would flag the very
    sentences that make the estate honest. Drop quotes, collapse whitespace, then match.
    """
    return " ".join(s.replace("'", " ").replace('"', " ").split())

# The literature names — statistics from the literature, not our ratio.
_LITERATURE = ("Deflated Sharpe", "Deflated-Sharpe", "DEFLATED SHARPE",
               "deflated-Sharpe",                     # lowercase citation form (plan §L4, mega_search)
               "Sharpe difference", "difference-of-Sharpe")   # Jobson-Korkie/Memmel test's own name

# Legitimate hits that are neither. (relpath, exact substring) -> written reason.
# Stale entries FAIL, so this list can only shrink honestly.
_ALLOW: dict[tuple[str, str], str] = {
    ("src/web/coverage_view.py", "never alpha/Sharpe/sigma"):
        "Names a CATEGORY of claim the page refuses to make, alongside alpha and sigma — "
        "not one of our figures. Refusing to claim 'a Sharpe' is exactly right, and "
        "relabelling would weaken the sentence (and garble it: 'never alpha/return/vol/sigma').",
    ("docs/strategies/sector-rotation.md", "page led with a Sharpe ratio"):
        "Historical honesty-note quoting ledger §2026-07-15h about the page's OLD state — "
        "the criticism of the mislabel, not a use of it.",
    ("docs/strategies/sector-rotation.md", "survivorship fake, plausibly Sharpe 1.5"):
        "Names the number a hypothetical stock-list seller would FAKE — a fence against "
        "building that list, not one of our figures.",
    ("docs/strategies/classic-screens.md", 'superior Sharpe + beats Nifty'):
        "Quotes the factor-league estate's own admission bar verbatim — an external "
        "criterion the classics are measured against, not a label on our number.",
    ("research/explosive_moves/cost_participation.py", "~1.0 net Sharpe at Rs50cr only"):
        "Verbatim institutional-panel quote (D142 carve-out #3: quoting people accurately "
        "outranks relabelling them).",
}

# The verbatim ledger quotes in rule_lab.py's _BLOCKING_JSON are byte-compared against
# docs/strategy-ledger.md — relabelling one side desyncs the pair. They are a QUOTE of the
# record, not our live label, so the whole block is out of scope by file+marker.
_QUOTE_BLOCK = ("src/automation/rule_lab.py", '_BLOCKING_JSON')


def _scan_files():
    """Every file the gate polices, exemptions applied."""
    files = []
    for tree in _TREES:
        files += sorted((REPO / tree).rglob("*.py"))
    for t in _DOC_TARGETS:
        base = REPO / t
        files += sorted(base.rglob("*.md")) if base.is_dir() else [base]
    files += sorted((REPO / _RESEARCH_TREE).rglob("*.py"))
    return [p for p in files
            if p.relative_to(REPO).as_posix() not in _FILE_EXEMPT
            and "PREREG" not in p.name]


def _scan():
    """Return (violations, stale_allowlist). violations = (relpath, lineno, line)."""
    hits, matched = [], set()
    for p in _scan_files():
        rel = p.relative_to(REPO).as_posix()
        lines = p.read_text(encoding="utf-8").splitlines()
        in_quote_block = False
        for i, line in enumerate(lines):
            n = i + 1
            if rel == _QUOTE_BLOCK[0]:
                if _QUOTE_BLOCK[1] in line:
                    in_quote_block = True
                elif in_quote_block and line.startswith('"""'):
                    in_quote_block = False
            if "Sharpe" not in line:
                continue
            if in_quote_block:
                continue
            ctx = _norm(" ".join(lines[max(0, i - _WINDOW):i + _WINDOW + 1]))
            if any(d in ctx for d in _DISCLOSURE) or any(d in line for d in _LITERATURE):
                continue
            allowed = [k for k in _ALLOW if k[0] == rel and k[1] in line]
            if allowed:
                matched.update(allowed)
                continue
            hits.append((rel, n, line.strip()))
    stale = [k for k in _ALLOW if k not in matched]
    return hits, stale


def test_scan_set_is_real():
    """The gate must actually be looking at files — a silent empty scan proves nothing."""
    rels = [p.relative_to(REPO).as_posix() for p in _scan_files()]
    n_src = sum(1 for r in rels if r.startswith("src/"))
    n_docs = sum(1 for r in rels if r.startswith("docs/"))
    n_res = sum(1 for r in rels if r.startswith("research/"))
    assert n_src > 50, f"expected the render+automation trees, found {n_src} files"
    assert n_docs > 10, f"expected the reader-facing docs tier, found {n_docs} files"
    assert n_res > 20, f"expected research/, found {n_res} files"


def test_disclosure_markers_are_disowning():
    """Every marker must contain a negation, the honest rename, or — since the S190/16AY
    rf re-cut — the BASIS CITATION for a genuinely rf-subtracted Sharpe ('16AY' /
    'excess-basis'). A marker that merely said 'Sharpe' would turn this gate into a rubber
    stamp; a citation marker is different: it pins the claim to the ledger entry where the
    subtraction is recorded, which is exactly the evidence the gate exists to demand."""
    for d in _DISCLOSURE:
        assert any(w in d.lower() for w in ("not", "never", "textbook", "labelled",
                                            "against", "no risk-free", "true sharpe",
                                            "true-sharpe", "true excess",
                                            "really a return/vol",
                                            "16ay", "excess-basis")), d


def test_the_ledger_banner_disowns_the_label():
    """docs/strategy-ledger.md is exempt from the line scan (append-only record,
    byte-compared by tests/test_rule_lab.py — the ledger wins, D142 carve-out #2).
    That exemption is honest ONLY while the estate-wide banner actually disowns the
    label at the top of the file; this pins it."""
    head = (REPO / "docs/strategy-ledger.md").read_text(encoding="utf-8")[:2000]
    assert 'every "Sharpe" here is a RETURN/VOL RATIO' in head, (
        "the strategy-ledger's D142 banner is gone — without it the ledger exemption "
        "is a blind spot, not a disown; restore the banner or line-scan the file")


def test_no_surface_calls_a_return_vol_ratio_a_sharpe():
    hits, stale = _scan()
    msg = []
    if hits:
        msg.append(
            "These lines call our number a 'Sharpe'. It is not one: no risk-free rate is "
            "subtracted (D142). Relabel to 'return/vol', or — if the line is disowning the "
            "label or naming the Bailey/Lopez de Prado statistic — phrase it so a "
            "_DISCLOSURE/_LITERATURE marker matches. A genuine exception goes in _ALLOW "
            "with a written reason.")
        msg += [f"  {rel}:{n}  {line[:100]}" for rel, n, line in hits]
    if stale:
        msg.append("Stale _ALLOW entries (text no longer present — remove them):")
        msg += [f"  {rel}: {sub!r}" for rel, sub in stale]
    assert not msg, "\n".join(msg)
