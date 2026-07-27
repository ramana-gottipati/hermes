"""Rule-lab contract gate (D134 §4-H) — hermetic, stdlib+sqlite only (VPS main-venv safe).

Covers every contract the design's §8 names for the core:
  1. grammar validation      — closed vocabulary, canonicalization, RAW-string hashing
  2. token->callable binding — every declared binding resolves to a real def/key in its
                               source file (AST/source scan; no numpy import needed)
  3. dead-idea auto-citation — a BOOK_YIELD-shaped rule carries the ledger's BLOCKING rows
                               VERBATIM (byte-compared against docs/strategy-ledger.md,
                               which stays canonical — drift here FAILS the suite)
  4. verdict-object shape    — design §4 fields, ledger vocabulary, qualifier travels,
                               JSON round-trip
  5. gate wiring             — judge() law branches + the object-level invariants
                               (NEW-BENCHMARK unreachable without halves+capacity+placebo;
                               missing stage = NO verdict, never partial)
Plus the inbox producer (per-item commit durability over a second connection) and the
render layer (fence, POST, sym links, CSV, URL state).
"""
from __future__ import annotations

import ast
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.automation import rule_lab as rl
from src.automation import rule_lab_inbox as rli
from src.web import rule_lab_view as rlv
from src.pat import rulelab_flow as rlf

DEMO = "SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly"

GOOD_NUMBERS = {"net_retvol": 1.00, "gross_retvol": 1.4, "half1": 0.95, "half2": 1.05,
                "placebo_p95": 0.50, "observed": 1.00, "emp_p": 0.01, "bench_net": 0.89,
                "capacity_inr": 50e7, "maxdd": -0.30, "ann_cost_pct": 4.0}


# ────────────────────────────────────────────────────────── 1. grammar validation
def test_compile_happy_path_and_canonical_order():
    a = rl.compile_rule(DEMO)
    assert (a.universe, a.signal, a.take, a.hold) == ("liquid500", "mom12", 25, "quarterly")
    assert a.filters == ("not_extended",) and a.vetoes == ()
    # clause order tolerated; canonical §2 order restored (the design §4 example's order)
    b = rl.compile_rule("SELECT liquid500 RANK BY mom12 WHERE not_extended TAKE 25 HOLD quarterly")
    assert b.text == a.text and b.rule_hash == a.rule_hash
    # case-insensitive tokens
    c = rl.compile_rule(DEMO.lower())
    assert c == a


def test_compile_rejects_everything_outside_the_closed_vocabulary():
    bad = [
        "SELECT nifty RANK BY mom12 TAKE 25 HOLD quarterly",          # unknown universe
        "SELECT liquid500 RANK BY sharpe_max TAKE 25 HOLD quarterly",  # unknown signal
        "SELECT liquid500 RANK BY mom12 TAKE 4 HOLD quarterly",        # n below range
        "SELECT liquid500 RANK BY mom12 TAKE 51 HOLD quarterly",       # n above range
        "SELECT liquid500 RANK BY mom12 TAKE 25 HOLD weekly",          # unknown horizon
        "SELECT liquid500 WHERE cheap RANK BY mom12 TAKE 25 HOLD monthly",   # unknown filter
        "SELECT liquid500 RANK BY mom12 TAKE 25 HOLD monthly VETO vibes",    # unknown veto
        "RANK BY mom12 TAKE 25 HOLD monthly",                          # missing SELECT
        "SELECT liquid500 TAKE 25 HOLD monthly",                       # missing RANK BY
        "",                                                            # empty
        "buy the strongest stocks",                                    # free text
    ]
    for text in bad:
        with pytest.raises(rl.RuleError):
            rl.compile_rule(text)


def test_no_arithmetic_composer_and_no_rupee_constants_are_expressible():
    with pytest.raises(rl.RuleError):
        rl.compile_rule("SELECT liquid500 RANK BY mom6*0.3+mom12*0.7 TAKE 25 HOLD monthly")
    with pytest.raises(rl.RuleError):
        rl.compile_rule("SELECT liquid500 WHERE mcap>500cr RANK BY mom12 TAKE 25 HOLD monthly")
    # and the vocabulary itself is percentile-only: every universe is a percentile band
    for u, meta in rl.UNIVERSES.items():
        lo, hi = meta["band"]
        assert 0.0 <= lo < hi <= 1.0, f"universe {u} must be a percentile band"


def test_hash_is_sha256_of_the_raw_canonical_text():
    import hashlib
    a = rl.compile_rule(DEMO)
    assert a.rule_hash == hashlib.sha256(a.text.encode("utf-8")).hexdigest()
    # duplicate filters collapse; order never changes the hash (frozen spec)
    b = rl.spec_from_params("liquid500", "mom12", 25, "quarterly",
                            filters=["not_extended", "not_extended"])
    assert b.rule_hash == a.rule_hash


# ────────────────────────────────────────────────────── 2. token -> callable binding
def _module_defs(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_every_signal_token_binds_to_an_existing_tested_callable():
    factory_defs = _module_defs(REPO / "research" / "explosive_moves" / "factory.py")
    zoo_src = (REPO / "research" / "explosive_moves" / "factor_zoo.py").read_text(encoding="utf-8")
    for token, b in rl.SIGNALS.items():
        target = REPO / b["module"]
        assert target.exists(), f"{token}: binding module missing: {b['module']}"
        if b["module"].endswith("factory.py"):
            assert b["callable"] in factory_defs, \
                f"{token}: factory has no def {b['callable']} — no token without the function"
        else:  # factor-zoo family: the tested factor KEY must exist in the zoo's source
            assert f'"{b["callable"]}"' in zoo_src, \
                f"{token}: factor_zoo has no tested factor key {b['callable']}"
            assert "executor_v1" in b, f"{token}: zoo-bound tokens must declare executor status"


def test_filter_and_universe_bindings_exist():
    factory_defs = _module_defs(REPO / "research" / "explosive_moves" / "factory.py")
    assert "not_extended" in factory_defs
    sm_defs = _module_defs(REPO / "src" / "automation" / "security_master.py")
    assert "universe_on" in sm_defs, "listed_on_asof must bind to the PIT join (D2-F1)"
    for f, b in rl.FILTERS.items():
        assert (REPO / b["module"]).exists(), f"filter {f}: binding module missing"


# ─────────────────────────────────────────────── 3. dead-idea auto-citation (MANDATORY)
def _ledger_blocking_rows() -> list:
    text = (REPO / "docs" / "strategy-ledger.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(text) if "BLOCKING FAILURE MODELS" in l)
    rows = []
    for l in text[start: start + 25]:
        if l.startswith("| ") and "Failure model" not in l and not l.startswith("|---"):
            rows.append(l)
    return rows


def test_embedded_blocking_rows_are_byte_verbatim_from_the_ledger():
    """The ledger stays canonical: if it changes, this FAILS until rule_lab re-syncs."""
    ledger_rows = _ledger_blocking_rows()
    assert len(ledger_rows) == len(rl.BLOCKING_ROWS) == 11
    embedded = set(rl.BLOCKING_ROWS.values())
    for row in ledger_rows:
        assert row in embedded, f"ledger row not embedded verbatim: {row[:60]}..."


def test_book_yield_shaped_rule_auto_cites_the_blocking_rows_verbatim():
    """THE mandatory contract: a known-dead idea can never run silently."""
    spec = rl.compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    cites = rl.trigger_citations(spec)
    ledger_rows = _ledger_blocking_rows()
    book_row = next(r for r in ledger_rows if r.startswith("| **BOOK_YIELD"))
    earn_row = next(r for r in ledger_rows if r.startswith("| **EARN_YIELD"))
    assert book_row in cites and earn_row in cites          # verbatim, from the file itself
    assert "Sharpe 0.61-0.63" in book_row                   # the exact recorded numbers ride along
    # and the citation is STAPLED into the verdict object (even a refusal carries it)
    v = rl.build_verdict(spec, {}, "t", {"env": "test"})
    assert v.verdict.startswith("NO-VERDICT") and book_row in v.ledger_citations


def test_trigger_map_covers_the_5_1_shapes():
    t = lambda s: rl.trigger_citations(rl.compile_rule(s))
    # momentum sold as fundable: mom6|mom12 + monthly
    cites = t("SELECT liquid500 RANK BY mom12 TAKE 25 HOLD monthly")
    assert any("Momentum sold as a FUNDABLE" in c for c in cites)
    # quarterly momentum is the low-turnover form — no momentum-fundable citation
    assert not any("Momentum sold" in c for c in t(DEMO))
    # ACCEL / PULLBACK / DELIV_MOM standalone
    for s in ("accel", "pullback", "delivmom"):
        assert any("ACCEL / PULLBACK / DELIV_MOM" in c
                   for c in t(f"SELECT liquid500 RANK BY {s} TAKE 25 HOLD quarterly"))
    # QUALITY standalone (qualmom carries a momentum leg — it must NOT cite this row)
    assert any("QUALITY standalone" in c
               for c in t("SELECT liquid500 RANK BY quality TAKE 25 HOLD quarterly"))
    assert not any("QUALITY standalone" in c
                   for c in t("SELECT liquid500 RANK BY qualmom TAKE 25 HOLD quarterly"))
    # C-BLEND shape: riskadj-family + monthly + mid/small tilt
    assert any("C-BLEND" in c for c in t("SELECT midcap RANK BY riskadj TAKE 25 HOLD monthly"))
    assert not any("C-BLEND" in c for c in t("SELECT midcap RANK BY riskadj TAKE 25 HOLD quarterly"))


def test_veto_promoted_to_rank_refuses_at_compile_time_with_citation():
    for tok, row_frag in (("mep_distribution", "MEP-accumulation"),
                          ("cci_deterioration", "CCI credibility")):
        with pytest.raises(rl.RuleError) as e:
            rl.compile_rule(f"SELECT liquid500 RANK BY {tok} TAKE 25 HOLD monthly")
        assert e.value.citations and row_frag in e.value.citations[0]
    # rating_downgrade as rank: refused on doctrine (no dedicated ledger row)
    with pytest.raises(rl.RuleError):
        rl.compile_rule("SELECT liquid500 RANK BY rating_downgrade TAKE 25 HOLD monthly")


def test_survivor_note_states_the_recorded_fundable_corner_honestly():
    s = rl.compile_rule("SELECT largecap RANK BY lowvolmom TAKE 25 HOLD quarterly")
    assert "LOWVOL_MOM" in rl.survivor_note(s) and "1.02" in rl.survivor_note(s)
    assert rl.survivor_note(rl.compile_rule(DEMO)) == ""


# ─────────────────────────────────────────────────────────── 4. verdict-object shape
def test_verdict_object_carries_the_design_4_fields_and_round_trips():
    spec = rl.compile_rule(DEMO)
    v = rl.build_verdict(spec, GOOD_NUMBERS, "rule_lab_prereg:x@t(first)",
                         {"module": "test", "window": "2012..2026"}, roster=["TCS"])
    d = v.to_dict()
    for k in ("rule_text", "rule_hash", "prereg_ref", "verdict", "qualifier", "numbers",
              "ledger_citations", "provenance", "survivor_note", "refusal_reason", "roster"):
        assert k in d, f"design §4 field missing: {k}"
    back = rl.RuleVerdict.from_dict(json.loads(v.to_json()))
    assert back.rule_hash == v.rule_hash and back.verdict == v.verdict
    assert back.qualifier == v.qualifier            # the qualifier travels, forever


def test_verdict_vocabulary_is_the_ledgers_verbatim():
    assert rl.VERDICTS == ("REJECTED", "WEAKER-THAN-BENCHMARK", "CONDITIONAL",
                           "NEW-BENCHMARK", "NO-VERDICT")
    assert rl.QUALIFIERS == ("descriptive-only", "paper-only", "flat-cost-only", "fundable")
    with pytest.raises(ValueError):
        rl.RuleVerdict(rule_text="t", rule_hash="h", prereg_ref="p", verdict="BUY",
                       qualifier="fundable", numbers={}, ledger_citations=[], provenance={})
    with pytest.raises(ValueError):   # CONDITIONAL must carry its condition
        rl.RuleVerdict(rule_text="t", rule_hash="h", prereg_ref="p", verdict="CONDITIONAL",
                       qualifier="paper-only", numbers={}, ledger_citations=[], provenance={})


# ──────────────────────────────────────────────────────────────────── 5. gate wiring
def test_judge_law_every_branch():
    j = rl.judge
    assert j(GOOD_NUMBERS)[0] == "NEW-BENCHMARK" and j(GOOD_NUMBERS)[1] == "fundable"
    assert j({**GOOD_NUMBERS, "capacity_inr": None}) == \
        ("CONDITIONAL(capacity-unstated)", "flat-cost-only",
         "a rule with no stated capacity is not a result (design §3 stage 6)")
    assert j({**GOOD_NUMBERS, "half2": 0.5})[0] == "CONDITIONAL(H1-only)"
    assert j({**GOOD_NUMBERS, "half1": 0.5})[0] == "CONDITIONAL(H2-only)"
    assert j({**GOOD_NUMBERS, "half1": 0.5, "half2": 0.5})[0] == "CONDITIONAL(full-window-only)"
    assert j({**GOOD_NUMBERS, "placebo_p95": 2.0})[0] == "REJECTED"     # control wins
    assert j({**GOOD_NUMBERS, "net_retvol": -0.2, "observed": -0.2,
              "half1": -0.2, "half2": -0.2})[0] == "REJECTED"
    weak = {**GOOD_NUMBERS, "net_retvol": 0.6, "observed": 0.6, "half1": 0.5, "half2": 0.6}
    assert j(weak) == ("WEAKER-THAN-BENCHMARK", "descriptive-only", "")


def test_missing_stage_is_a_refusal_never_a_partial_verdict():
    for k in ("net_retvol", "half1", "half2", "placebo_p95", "observed", "bench_net"):
        verdict, qualifier, why = rl.judge({**GOOD_NUMBERS, k: None})
        assert verdict.startswith("NO-VERDICT(missing:") and k in verdict
        assert qualifier is None and "refusal" in why
        nan_verdict, _, _ = rl.judge({**GOOD_NUMBERS, k: float("nan")})
        assert nan_verdict.startswith("NO-VERDICT")


def test_new_benchmark_is_unreachable_without_all_three_gates():
    """Design §4 invariant 1 — enforced by the OBJECT, not just by judge()."""
    spec = rl.compile_rule(DEMO)
    for broken in ({**GOOD_NUMBERS, "half2": 0.5},                  # a half fails
                   {**GOOD_NUMBERS, "capacity_inr": None},          # capacity unstated
                   {**GOOD_NUMBERS, "placebo_p95": 2.0}):           # placebo not beaten
        v = rl.build_verdict(spec, broken, "p", {})
        assert v.verdict != "NEW-BENCHMARK"
        with pytest.raises(ValueError):
            rl.RuleVerdict(rule_text=spec.text, rule_hash=spec.rule_hash, prereg_ref="p",
                           verdict="NEW-BENCHMARK", qualifier="fundable", numbers=broken,
                           ledger_citations=[], provenance={})


def test_no_verdict_carries_no_qualifier():
    with pytest.raises(ValueError):
        rl.RuleVerdict(rule_text="t", rule_hash="h", prereg_ref="p",
                       verdict="NO-VERDICT(missing:x)", qualifier="fundable",
                       numbers={}, ledger_citations=[], provenance={})


# ─────────────────────────────────────────────────────────────── inbox producer (step 3)
def test_inbox_submit_commits_per_item_and_is_idempotent(tmp_path):
    db = tmp_path / "inbox.db"
    conn = sqlite3.connect(str(db))
    spec = rl.compile_rule(DEMO)
    v = rl.build_verdict(spec, GOOD_NUMBERS, "p", {"env": "test"}, roster=["INFY"])
    r1 = rli.submit_verdict(conn, v, evidence_url="/dash/rule-lab")
    # durability proof: a SECOND connection sees the row (per-item commit, S153 lesson)
    conn2 = sqlite3.connect(str(db))
    got = conn2.execute("SELECT kind, ref, status FROM review_items").fetchall()
    assert got == [("rule_verdict", v.rule_hash, "pending")]
    conn2.close()
    # idempotent on rule_hash — the first verdict for a frozen rule wins
    r2 = rli.submit_verdict(conn, v)
    assert r1["created"] and not r2["created"] and r1["id"] == r2["id"]
    item = rli.latest_verdict(conn)
    assert item["verdict"]["rule_hash"] == v.rule_hash
    assert "Rule-lab run" in item["ledger_block"]           # the paste-ready canon block rides along
    conn.close()


def test_ledger_entry_is_paste_ready_and_cites_the_wall():
    spec = rl.compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    v = rl.build_verdict(spec, {}, "p", {"env": "test"})
    block = rl.ledger_entry(v, "2026-07-15")
    assert block.startswith("## Rule-lab run 2026-07-15")
    assert "BOOK_YIELD" in block and "Capacity: unstated" in block


# ───────────────────────────────────────────────────────────────── render layer (step 4)
def test_render_page_carries_fence_education_post_and_sym_links():
    spec = rl.compile_rule(DEMO)
    v = rl.build_verdict(spec, GOOD_NUMBERS, "p", {"env": "test"},
                         roster=["TCS", "INFY"]).to_dict()
    page = rlv.render_page(v, demo_note="read-only demo rule")
    assert "descriptive, not a recommendation" in page      # fence("not_reco") — row 4
    assert rlv.BOTTOM_LINE in page                          # education — row 3
    assert "/dash/reading-guide" in page                    # how_to_read_link
    assert 'method="post"' in page                          # writes are POST — row 11
    assert "/dash/stock?sym=TCS" in page                    # sym links — row 9
    assert "NEW-BENCHMARK" in page and "fundable" in page
    for phrase in ("you should buy", "target price of", "strong buy", "buy now"):
        assert phrase not in page.lower()                   # the SEBI lexicon, spot-checked


def test_csv_export_and_url_state_round_trip():
    spec = rl.compile_rule(DEMO)
    q = rlv.query_from_spec(spec)
    assert q == {"u": "liquid500", "rank": "mom12", "n": "25",
                 "hold": "quarterly", "where": "not_extended"}
    assert rlv.spec_from_query(q) == spec                   # the URL IS the rule — row 8b
    with pytest.raises(rl.RuleError):
        rlv.spec_from_query({"u": "liquid500", "rank": "vibes", "n": "25", "hold": "monthly"})
    v = rl.build_verdict(spec, GOOD_NUMBERS, "p", {}, roster=["TCS"]).to_dict()
    name, text = rlv.render_csv(v)
    assert name == f"rule-lab-{spec.rule_hash[:12]}.csv"
    assert "net return/vol" in text and "TCS" in text and "blocking_citation" not in text
    dead = rl.compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    dv = rl.build_verdict(dead, {}, "p", {}).to_dict()
    _, dtext = rlv.render_csv(dv)
    assert "blocking_citation" in dtext                     # the wall travels into the export


# ─────────────────────────────────────────────────────────────────── Pat flow (row 6)
def test_pat_flow_recognition_is_conservative():
    assert rlf.parse_rulelab("did my rule work?") == {"flow": "rulelab", "params": {}}
    assert rlf.parse_rulelab("rule lab verdict please") is not None
    assert rlf.parse_rulelab("my rule") is None             # no ask cue
    assert rlf.parse_rulelab("what's the wolfe rule verdict") is None
    assert rlf.parse_rulelab("screener rules that worked") is None
    assert rlf.parse_rulelab("how do results reactions work") is None


def test_pat_flow_answers_from_the_inbox(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "pat.db"))
    assert rlf.answer(conn)["found"] is False               # empty-DB grace
    spec = rl.compile_rule(DEMO)
    rli.submit_verdict(conn, rl.build_verdict(spec, GOOD_NUMBERS, "p", {"env": "t"}))
    out = rlf.answer(conn)
    assert out["found"] and out["verdict"] == "NEW-BENCHMARK"
    assert out["status"] == "pending" and out["link"] == "/dash/rule-lab"
    conn.close()


# ─────────────────────────────────────────────────────────────────── module selftests
def test_module_selftests_are_green():
    assert rl._selftest() == 0
    assert rli._selftest() == 0
    assert rlv._selftest() == 0
    assert rlf._selftest() == 0


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
