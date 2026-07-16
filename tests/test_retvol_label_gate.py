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

NOT policed here: research/ (analyst-facing scripts, relabelled by D142 but not a public
surface), and the on-disk `sharpe` COLUMN in research.db (strategy_store.py keeps the
legacy name deliberately — CREATE TABLE IF NOT EXISTS cannot migrate existing rows; the
value is rendered as "Return/vol" by testing_view.py).

Why a label gate and not a re-cut: a true Sharpe needs a risk-free-rate ingest from a
primary source (Guardrail #8 — NSE/BSE/SEBI/XBRL, never a vendor). That MOVES NUMBERS and
is queued to land with the owed TR-benchmark re-cut, which moves the same figures. Until
then the honest move is to name the thing correctly — which is exactly what this enforces.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_TREES = ("src/web", "src/pat", "src/automation")

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

# The literature name — a statistic, not our ratio.
_LITERATURE = ("Deflated Sharpe", "Deflated-Sharpe", "DEFLATED SHARPE")

# Legitimate hits that are neither. (relpath, exact substring) -> written reason.
# Stale entries FAIL, so this list can only shrink honestly.
_ALLOW: dict[tuple[str, str], str] = {
    ("src/web/coverage_view.py", "never alpha/Sharpe/sigma"):
        "Names a CATEGORY of claim the page refuses to make, alongside alpha and sigma — "
        "not one of our figures. Refusing to claim 'a Sharpe' is exactly right, and "
        "relabelling would weaken the sentence (and garble it: 'never alpha/return/vol/sigma').",
    ("src/automation/rule_lab.py", 'the "Sharpe" in these rows is a return/vol ratio'):
        "The D142 carve-out comment itself, explaining why the BLOCKING ledger rows below "
        "are not relabelled: they are VERBATIM quotes byte-compared against "
        "docs/strategy-ledger.md by tests/test_rule_lab.py. The ledger wins.",
}

# The verbatim ledger quotes in rule_lab.py's _BLOCKING_JSON are byte-compared against
# docs/strategy-ledger.md — relabelling one side desyncs the pair. They are a QUOTE of the
# record, not our live label, so the whole block is out of scope by file+marker.
_QUOTE_BLOCK = ("src/automation/rule_lab.py", '_BLOCKING_JSON')


def _scan():
    """Return (violations, stale_allowlist). violations = (relpath, lineno, line)."""
    hits, matched = [], set()
    for tree in _TREES:
        for p in sorted((REPO / tree).rglob("*.py")):
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
    n = sum(1 for t in _TREES for _ in (REPO / t).rglob("*.py"))
    assert n > 50, f"expected the render+automation trees, found {n} files"


def test_disclosure_markers_are_disowning():
    """Every marker must contain a negation — a marker that merely says 'Sharpe' would
    turn this gate into a rubber stamp."""
    for d in _DISCLOSURE:
        assert any(w in d.lower() for w in ("not", "never", "textbook", "labelled",
                                            "against", "no risk-free", "true sharpe")), d


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
