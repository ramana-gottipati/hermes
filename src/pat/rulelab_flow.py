"""Pat 'rulelab' flow — deterministic recognition + a bounded read of the latest rule-lab
verdict (the /dash/rule-lab surface's DATA flow; D134 §4-H, design §7 row 6).

Answers "did my rule work?", "test my rule", "rule lab verdict", "latest rule verdict" —
by reading the newest review_items(kind='rule_verdict') payload (the Review-Inbox is the
lab's output queue; src/automation/rule_lab_inbox.py). DESCRIPTIVE-only / SEBI-safe: the
answer is the ledger-vocabulary verdict + its numbers, never advice; composing/running a NEW
rule is the page's POST form, not a chat side effect — Pat only ever READS.

Mirrors overdue_flow.py's contract: PURE logic (recognition + a SELECT on the inbox); the
HTML render lives in src/pat/web.py (INTEGRATION: _rulelab_flow renderer + the lazy-import
line in engine.route() + a PAT_DATA["rule-lab"] = "rulelab" entry in tests/test_pat_coverage
— those files exist and may not be edited by this build lane). Recognition is conservative:
fires only on a rule/verdict cue with lab/test context; a miss falls through to the normal
parse.
"""
from __future__ import annotations

import re

_RULE_RE = re.compile(r"\b(rule[- ]?lab|my rule|the rule|rule verdict|rule result)\b")
_ASK_RE = re.compile(r"\b(did|does|work(?:ed|s)?|test(?:ed)?|verdict|result|latest|status|"
                     r"outcome|pass(?:ed)?|fail(?:ed)?)\b")


def parse_rulelab(query: str) -> dict | None:
    """"did my rule work" / "rule lab verdict" / "test my rule" -> {flow:"rulelab"} | None.
    Conservative: needs a rule-lab cue AND an ask/test cue (bare "the rule" alone never
    fires — screener rules, wolfe rules etc. stay with their own flows)."""
    q = (query or "").lower()
    if not _RULE_RE.search(q):
        return None
    if not _ASK_RE.search(q):
        return None
    if re.search(r"\bwolfe|screen|glossary|exit law\b", q):
        return None                                    # other lenses' rule vocabulary
    return {"flow": "rulelab", "params": {}}


def answer(conn) -> dict:
    """The latest verdict as a small dict for the web renderer. Empty-DB grace: found=False.

    Keys: found, status (pending|approved|rejected), title, verdict, qualifier, rule_text,
    net_retvol, bench_net, link. Numbers pass through as stored; nothing is recomputed."""
    from src.automation.rule_lab_inbox import latest_verdict
    item = latest_verdict(conn)
    if not item:
        return {"found": False, "link": "/dash/rule-lab",
                "note": "no rule has been run yet — compose one on the Rule lab page"}
    v = item.get("verdict") or {}
    nums = v.get("numbers") or {}
    return {
        "found": True,
        "status": item.get("status"),
        "title": item.get("title", ""),
        "verdict": v.get("verdict", ""),
        "qualifier": v.get("qualifier"),
        "rule_text": v.get("rule_text", ""),
        "rule_hash": v.get("rule_hash", ""),
        "net_retvol": nums.get("net_retvol"),
        "bench_net": nums.get("bench_net"),
        "placebo_p95": nums.get("placebo_p95"),
        "capacity_inr": nums.get("capacity_inr"),
        "link": "/dash/rule-lab",
    }


def _selftest() -> int:
    import sqlite3
    assert parse_rulelab("did my rule work?") == {"flow": "rulelab", "params": {}}
    assert parse_rulelab("rule lab verdict") is not None
    assert parse_rulelab("test my rule on the gauntlet") is not None
    assert parse_rulelab("what is the exit law rule") is None      # other lens vocabulary
    assert parse_rulelab("screener rule results") is None
    assert parse_rulelab("my rule") is None                        # no ask cue
    assert parse_rulelab("show me the wolfe rule verdict") is None
    conn = sqlite3.connect(":memory:")
    out = answer(conn)
    assert out["found"] is False and out["link"] == "/dash/rule-lab"
    # end-to-end with a real submitted verdict
    from src.automation.rule_lab import compile_rule, build_verdict
    from src.automation.rule_lab_inbox import submit_verdict
    spec = compile_rule("SELECT largecap RANK BY lowvolmom TAKE 25 HOLD quarterly")
    nums = {"net_retvol": 1.02, "half1": 0.95, "half2": 1.10, "placebo_p95": 0.4,
            "observed": 1.02, "bench_net": 0.89, "capacity_inr": 50e7}
    submit_verdict(conn, build_verdict(spec, nums, "selftest", {"env": "selftest"}))
    out = answer(conn)
    assert out["found"] and out["verdict"] == "NEW-BENCHMARK" and out["status"] == "pending"
    conn.close()
    print("RULELAB_FLOW selftest OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else print(__doc__) or 0)
