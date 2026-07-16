"""Auto-analyst v1 contracts (D134 LANE-E, plan §4-E / L6).

Hermetic: synthetic results_reactions in a temp research.db; temp hermes.db for
the inbox + ledger. The LLM path is exercised ONLY through injected fakes — no
network, no keys. The compliance check reuses the language gate's own _FORBIDDEN
lexicon (auto_analyst lives in src/automation, outside the gate's scan dirs, so
this file closes that gap for its templates and rendered briefs).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.automation import auto_analyst as aa  # noqa: E402
from src.automation import review_inbox  # noqa: E402


# ------------------------------------------------------------------ fixtures

def _mk_research(tmp_path, rows):
    rdb = tmp_path / "research.db"
    con = sqlite3.connect(rdb)
    con.execute("""CREATE TABLE results_reactions (sym TEXT, ptype TEXT, pend TEXT,
                   t0 TEXT, entry_date TEXT, sue REAL, ear REAL, deliv_x REAL,
                   med_turn REAL, car22 REAL, car60 REAL, beat INT, sue_high INT,
                   deliv_high INT, settled INT)""")
    con.execute("CREATE TABLE results_reactions_meta (k TEXT, v REAL)")
    con.executemany("INSERT INTO results_reactions_meta VALUES (?,?)",
                    [("sue_hi", 2.1176), ("dlv_hi", 2.8530)])
    con.executemany("INSERT INTO results_reactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return str(rdb)


ROW_OPEN = ("TESTCO", "Q", "2026-06-30", "2026-07-13", "2026-07-14",
            2.01, 0.0086, 2.14, 1.0, None, None, 1, 0, 0, 0)
ROW_SETTLED = ("OLDCO", "Q", "2025-12-31", "2026-01-20", "2026-01-21",
               -1.20, -0.0150, 0.60, 1.0, 0.031, -0.022, 0, 0, 0, 1)


def _hdb(tmp_path):
    p = tmp_path / "hermes.db"
    sqlite3.connect(p).close()
    return str(p)


# ------------------------------------------------------------------ template path

def test_template_brief_shape_and_labels(tmp_path):
    rdb = _mk_research(tmp_path, [ROW_OPEN])
    ev = aa.latest_events(5, research_db=rdb)[0]
    b = aa.template_brief(ev, today="2026-07-15")
    assert 6 <= len(b["lines"]) <= 10
    assert aa._LABEL in b["text"] and "2026-07-15" in b["text"]
    assert aa._FENCE in b["text"]
    assert "falsified" in b["text"]                      # PEAD honesty citation
    assert b["ref"] == "results:TESTCO:2026-06-30"       # period-stable ref
    assert "TESTCO" in b["title"] and "SUE" in b["title"]


def test_every_number_has_a_source(tmp_path):
    rdb = _mk_research(tmp_path, [ROW_OPEN])
    b = aa.template_brief(aa.latest_events(5, research_db=rdb)[0])
    assert b["numbers"], "grounding map must not be empty"
    for name, cell in b["numbers"].items():
        assert cell.get("source"), f"{name} lacks a source link"


def test_settled_vs_open_drift_lines(tmp_path):
    rdb = _mk_research(tmp_path, [ROW_OPEN, ROW_SETTLED])
    evs = {e["sym"]: e for e in aa.latest_events(5, research_db=rdb)}
    open_b = aa.template_brief(evs["TESTCO"])
    settled_b = aa.template_brief(evs["OLDCO"])
    assert "still open" in open_b["text"] and "CAR22" not in open_b["text"]
    assert "CAR22" in settled_b["text"] and "CAR60" in settled_b["text"]


def test_empty_db_grace(tmp_path):
    assert aa.latest_events(research_db=str(tmp_path / "missing.db")) == []
    out = aa.run(3, hermes_db=_hdb(tmp_path), research_db=str(tmp_path / "missing.db"))
    assert out["drafted"] == 0 and out["queued"] == 0


# ------------------------------------------------------------------ inbox wiring

def test_run_queues_briefs_idempotently(tmp_path):
    rdb = _mk_research(tmp_path, [ROW_OPEN, ROW_SETTLED])
    hdb = _hdb(tmp_path)
    r1 = aa.run(5, hermes_db=hdb, research_db=rdb, today="2026-07-15")
    r2 = aa.run(5, hermes_db=hdb, research_db=rdb, today="2026-07-15")
    assert r1["drafted"] == 2 and r1["queued"] == 2
    assert r2["queued"] == 0, "re-run must not duplicate (first-write-wins refs)"
    con = sqlite3.connect(hdb)
    pend = review_inbox.pending(con, kind=aa.KIND)
    assert len(pend) == 2
    payload = pend[0]["payload"]  # _to_dict parses payload_json -> payload
    assert payload.get("label") == aa._LABEL and payload.get("fence") == aa._FENCE
    assert payload.get("text") and payload.get("numbers")
    con.close()


# ------------------------------------------------------------------ LLM path (fakes)

def test_llm_flag_default_off(tmp_path, monkeypatch):
    rdb = _mk_research(tmp_path, [ROW_OPEN])
    called = {"n": 0}

    def boom(system, user):
        called["n"] += 1
        return "should never run"

    aa.run(5, hermes_db=_hdb(tmp_path), research_db=rdb, llm_fn=boom)  # llm=False default
    assert called["n"] == 0, "LLM path must be strictly opt-in"


def test_digit_subset_guard_rejects_invented_numbers(tmp_path):
    rdb = _mk_research(tmp_path, [ROW_OPEN])
    b = aa.template_brief(aa.latest_events(5, research_db=rdb)[0])
    out = aa.llm_rewrite(b, llm_fn=lambda s, u: "Profit exploded 999x on 42 crores.",
                         hermes_db=_hdb(tmp_path))
    assert out["path"].startswith("template")
    assert out["text"] == b["text"]


def test_clean_rewrite_kept_with_verbatim_tail(tmp_path):
    rdb = _mk_research(tmp_path, [ROW_OPEN])
    b = aa.template_brief(aa.latest_events(5, research_db=rdb)[0], today="2026-07-15")
    out = aa.llm_rewrite(b, llm_fn=lambda s, u: "SUE printed 2.01 while delivered value ran 2.14 times its median.",
                         hermes_db=_hdb(tmp_path))
    assert out["path"] == "llm"
    assert out["lines"][-3:] == b["lines"][-3:], "context/sources/label tail must be verbatim"


def test_cap_breach_degrades_to_template(tmp_path):
    hdb = _hdb(tmp_path)
    con = sqlite3.connect(hdb)
    con.execute("""CREATE TABLE cost_ledger (ts TEXT DEFAULT (datetime('now')), job TEXT,
                   model TEXT, tokens_in INT, tokens_out INT, inr_estimate REAL, note TEXT)""")
    con.execute("INSERT INTO cost_ledger (job, model, tokens_in, tokens_out, inr_estimate) "
                "VALUES ('auto-analyst','claude-haiku-4-5',0,0,?)", (aa.AUTO_ANALYST_CAP_INR + 1,))
    con.commit(); con.close()
    rdb = _mk_research(tmp_path, [ROW_OPEN])
    b = aa.template_brief(aa.latest_events(5, research_db=rdb)[0])
    called = {"n": 0}

    def spy(system, user):
        called["n"] += 1
        return "SUE printed 2.01."

    out = aa.llm_rewrite(b, llm_fn=spy, hermes_db=hdb)
    assert called["n"] == 0, "at cap the LLM must not even be called (§5.4)"
    assert "cap reached" in out["path"]


# ------------------------------------------------------------------ compliance

def _gate_forbidden():
    spec = importlib.util.spec_from_file_location(
        "compliance_gate", REPO / "tests" / "test_compliance_language_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._FORBIDDEN


def test_templates_pass_the_compliance_lexicon(tmp_path):
    forbidden = _gate_forbidden()
    src = (REPO / "src" / "automation" / "auto_analyst.py").read_text(encoding="utf-8").lower()
    rdb = _mk_research(tmp_path, [ROW_OPEN, ROW_SETTLED])
    rendered = " ".join(aa.template_brief(e)["text"].lower()
                        for e in aa.latest_events(5, research_db=rdb))
    for phrase in forbidden:
        assert phrase not in src, f"module source contains forbidden phrase: {phrase!r}"
        assert phrase not in rendered, f"rendered brief contains forbidden phrase: {phrase!r}"
