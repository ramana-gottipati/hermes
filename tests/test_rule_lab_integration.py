"""Integration contracts for the rule-lab SURFACE + queue + Pat wiring (S157-b, D137).

The build lane (`b67509d`) proved the compiler/gauntlet/inbox in isolation
(tests/test_rule_lab.py, tests/test_rule_lab_executor.py). THIS file proves the
integration half the build lane could not touch (shared files, per the lane bans):

  1. the mount     — /dash/rule-lab is served (v2_surfaces._ROUTER_SPECS + the Lens row);
  2. the demo gate — anonymous = read-only DEMO verdict; the composer POST is owner-only
                     and NEVER enqueues for anonymous (fail-closed);
  3. the queue     — owner POST compiles -> enqueues (idempotent) -> 303 PRG redirect;
                     compile refusals re-render with the error + BLOCKING citation inline;
  4. the wall      — a dead-shape rule in the URL is cited BEFORE any run (§5);
  5. Pat           — the `rulelab` flow is wired at every seam the coverage gate checks.

Wire-level only; verdict-law/gauntlet math stays in the build lane's files.
"""
from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import src.web.rule_lab_view as rlv        # noqa: E402


@pytest.fixture(scope="module")
def client():
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return TestClient(M.app)


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Point get_conn at a throwaway DB so POST tests never touch data/hermes.db."""
    db = tmp_path / "hermes-test.db"
    import src.core.db as CDB
    monkeypatch.setattr(CDB, "DB_PATH", db)
    return db


# ── 1+2: mount + demo gate ────────────────────────────────────────────────────────────
# NB: tracker_gate._is_owner returns True on a dev box with no chat_shared_secret (its
# deliberate dev-convenience). Anonymous-path tests therefore PIN _owner_ok to False —
# on the VPS the secret exists and the real gate does this for genuine anonymous traffic.
@pytest.fixture()
def anon(monkeypatch):
    monkeypatch.setattr(rlv, "_owner_ok", lambda request: False)


def test_page_is_mounted_and_anonymous_sees_the_demo(client, anon):
    r = client.get("/dash/rule-lab")
    assert r.status_code == 200
    assert "Read-only demo" in r.text                     # demo note, not real data
    assert "descriptive, not a recommendation" in r.text  # the fence
    assert "WEAKER-THAN-BENCHMARK" in r.text              # honest demo verdict
    assert 'method="post"' in r.text                      # composer present (POST-only writes)


def test_csv_export_serves_text_csv(client, anon):
    r = client.get("/dash/rule-lab?format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "rule_hash" in r.text and "net return/vol" in r.text


def test_anonymous_post_is_refused_and_never_enqueues(client, tmp_db, anon):
    r = client.post("/dash/rule-lab/run",
                    data={"u": "liquid500", "rank": "mom12", "n": "25", "hold": "quarterly"})
    assert r.status_code == 200 and "Owner-only" in r.text
    con = sqlite3.connect(tmp_db)
    n = con.execute("SELECT count(*) FROM sqlite_master WHERE name='rule_lab_queue'").fetchone()[0]
    con.close()
    assert n == 0, "anonymous POST must not create/write the queue"


# ── 3: the owner queue path ───────────────────────────────────────────────────────────
def test_owner_post_compiles_enqueues_and_redirects(client, tmp_db, monkeypatch):
    monkeypatch.setattr(rlv, "_owner_ok", lambda request: True)
    r = client.post("/dash/rule-lab/run",
                    data={"u": "liquid500", "rank": "mom12", "n": "25",
                          "hold": "quarterly", "where": ["not_extended"]},
                    follow_redirects=False)
    assert r.status_code == 303
    assert "queued=1" in r.headers["location"] and "rank=mom12" in r.headers["location"]
    con = sqlite3.connect(tmp_db)
    rows = con.execute("SELECT spec_text, status FROM rule_lab_queue").fetchall()
    con.close()
    assert rows == [("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly",
                     "queued")]
    # PRG landing page shows the queued note
    r2 = client.get(r.headers["location"])
    assert "rule queued" in r2.text


def test_owner_post_compile_refusal_shows_error_and_citation(client, tmp_db, monkeypatch):
    monkeypatch.setattr(rlv, "_owner_ok", lambda request: True)
    r = client.post("/dash/rule-lab/run",
                    data={"u": "liquid500", "rank": "mep_distribution", "n": "25",
                          "hold": "monthly"})
    assert r.status_code == 200
    assert "not compiled" in r.text                      # the refusal
    assert "MEP-accumulation as alpha" in r.text         # the stapled BLOCKING citation
    con = sqlite3.connect(tmp_db)
    n = con.execute("SELECT count(*) FROM sqlite_master WHERE name='rule_lab_queue'").fetchone()[0]
    con.close()
    assert n == 0


# ── 4: the wall speaks before any run ─────────────────────────────────────────────────
def test_dead_shape_url_is_cited_before_any_run(client, anon):
    r = client.get("/dash/rule-lab?u=liquid500&rank=bookyield&n=25&hold=monthly")
    assert r.status_code == 200
    assert "cited before the run" in r.text
    assert "BOOK_YIELD" in r.text and "value-trap engine" in r.text


def test_survivor_shape_states_the_recorded_corner(client, anon):
    r = client.get("/dash/rule-lab?u=largecap&rank=lowvolmom&n=25&hold=quarterly")
    assert "RECORDED SURVIVOR" in r.text


# ── 5: Pat wiring (every seam the coverage gate checks) ───────────────────────────────
def test_pat_rulelab_flow_is_wired_at_every_seam():
    from src.pat import engine as E
    import src.pat.web as PW
    assert "rulelab" in E._VALID and E._VALID["rulelab"] == {}
    assert "rulelab" in PW._FLOW_LABEL
    con = sqlite3.connect(":memory:")
    html = PW._rulelab_flow(con)
    assert "No rule has been run yet" in html and "/dash/rule-lab" in html
    con.close()


def test_engine_routes_the_ask_to_rulelab():
    from src.pat import engine as E
    out = E.route("did my rule work?")
    assert out and out.get("flow") == "rulelab"


def test_lens_and_router_spec_registered():
    from src.web import lens_registry as LR
    from src.web import v2_surfaces as V2
    lens = next((l for l in LR.LENSES if l.key == "rule-lab"), None)
    assert lens is not None and lens.altitude == "trust" and lens.route == "/dash/rule-lab"
    assert any(s[2] == "/dash/rule-lab" for s in V2._ROUTER_SPECS)


# ── the drain loop (numpy-side work() proven with a stubbed gauntlet) ─────────────────
def test_work_drains_the_queue_into_the_inbox(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")                                  # noqa: F841
    research = os.path.join(_ROOT, "research")
    if research not in sys.path:
        sys.path.insert(0, research)
    from explosive_moves import rule_lab_executor as rle
    from src.automation.rule_lab import compile_rule, build_verdict
    from src.automation.rule_lab_inbox import enqueue, latest_verdict, queue_status

    db = tmp_path / "hermes-work.db"
    spec = compile_rule("SELECT liquid500 RANK BY mom12 TAKE 25 HOLD quarterly")
    con = sqlite3.connect(db)
    enqueue(con, spec)
    con.close()

    nums = {"net_retvol": 0.5, "half1": 0.4, "half2": 0.6, "placebo_p95": 0.3,
            "observed": 0.5, "bench_net": 0.89}
    monkeypatch.setattr(rle, "run_gauntlet",
                        lambda s, **kw: build_verdict(s, nums, "worktest", {"env": "worktest"}))
    out = rle.work(str(db))
    assert out == {"ran": 1, "errors": 0, "skipped": 0}

    con = sqlite3.connect(db)
    assert queue_status(con, spec.rule_hash) == "done"
    got = latest_verdict(con)
    con.close()
    assert got and got["verdict"]["rule_hash"] == spec.rule_hash
    assert got["verdict"]["verdict"] == "WEAKER-THAN-BENCHMARK"


def test_work_marks_errors_and_keeps_draining(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    research = os.path.join(_ROOT, "research")
    if research not in sys.path:
        sys.path.insert(0, research)
    from explosive_moves import rule_lab_executor as rle
    from src.automation.rule_lab import compile_rule
    from src.automation.rule_lab_inbox import enqueue, queue_status

    db = tmp_path / "hermes-err.db"
    s1 = compile_rule("SELECT liquid500 RANK BY mom6 TAKE 10 HOLD monthly")
    s2 = compile_rule("SELECT largecap RANK BY lowvolmom TAKE 25 HOLD quarterly")
    con = sqlite3.connect(db)
    enqueue(con, s1)
    enqueue(con, s2)
    con.close()

    def boom_then_ok(spec, **kw):
        if spec.rule_hash == s1.rule_hash:
            raise RuntimeError("synthetic gauntlet failure")
        from src.automation.rule_lab import build_verdict
        return build_verdict(spec, {"net_retvol": 0.5, "half1": 0.4, "half2": 0.6,
                                    "placebo_p95": 0.3, "observed": 0.5,
                                    "bench_net": 0.89}, "worktest", {"env": "worktest"})

    monkeypatch.setattr(rle, "run_gauntlet", boom_then_ok)
    out = rle.work(str(db))
    assert out["ran"] == 1 and out["errors"] == 1
    con = sqlite3.connect(db)
    assert queue_status(con, s1.rule_hash) == "error"
    assert queue_status(con, s2.rule_hash) == "done"
    con.close()


# ── D142 legacy-payload rendering (S162, Ramana-directed) ─────────────────────────────
# D142 renamed *_sharpe -> *_retvol estate-wide, but the ONE live NEW-BENCHMARK verdict was
# stored pre-rename (S157-b) with net_sharpe. The post-D142 renderers read net_retvol, so
# the number rendered as "—". These pin the fix: normalize on read + a one-time backfill.
def _legacy_verdict_dict():
    from src.automation.rule_lab import compile_rule, build_verdict
    spec = compile_rule("SELECT largecap RANK BY lowvolmom TAKE 25 HOLD quarterly")
    v = build_verdict(spec, {"net_retvol": 1.19, "gross_retvol": 1.4, "flat_retvol": 1.5,
                             "half1": 1.2, "half2": 1.42, "placebo_p95": 0.35,
                             "observed": 1.19, "bench_net": 0.89, "capacity_inr": 75e7,
                             "maxdd": -0.3, "ann_cost_pct": 8.0}, "s", {"env": "s"})
    vd = v.to_dict()
    ren = {"net_retvol": "net_sharpe", "gross_retvol": "gross_sharpe", "flat_retvol": "flat_sharpe"}
    vd["numbers"] = {ren.get(k, k): val for k, val in vd["numbers"].items()}
    return v, vd


def test_normalize_numbers_maps_legacy_keys():
    from src.automation.rule_lab_inbox import normalize_numbers
    out = normalize_numbers({"net_sharpe": 1.19, "gross_sharpe": 1.4, "half1": 1.2})
    assert out["net_retvol"] == 1.19 and out["gross_retvol"] == 1.4
    assert "net_sharpe" not in out and "gross_sharpe" not in out
    assert out["half1"] == 1.2                     # untouched keys survive
    # the honest key wins if both are somehow present
    assert normalize_numbers({"net_sharpe": 9.9, "net_retvol": 1.19})["net_retvol"] == 1.19


def test_a_pre_d142_verdict_still_renders_its_number(tmp_path):
    import sqlite3
    from src.automation import review_inbox, rule_lab_inbox as RLI
    from src.pat import rulelab_flow, web as PW
    c = sqlite3.connect(":memory:"); review_inbox.ensure_schema(c)
    v, vd = _legacy_verdict_dict()
    review_inbox.submit(c, "rule_verdict", v.rule_hash, RLI._title(v),
                        {"verdict": vd, "ledger_block": "NET Sharpe 1.19", "produced_at": "2026-07-15"})
    c.commit()
    # Pat's answer path (what pat/web reads) — the number, not None
    assert rulelab_flow.answer(c)["net_retvol"] == 1.19
    # the /dash/rule-lab inline flow renders the digits, not "—"
    assert "1.19" in PW._rulelab_flow(c)
    c.close()


def test_backfill_makes_the_stored_payload_honest_and_idempotent(tmp_path):
    import json, sqlite3
    from src.automation import review_inbox, rule_lab_inbox as RLI
    c = sqlite3.connect(":memory:"); review_inbox.ensure_schema(c)
    v, vd = _legacy_verdict_dict()
    r = review_inbox.submit(c, "rule_verdict", v.rule_hash, RLI._title(v),
                            {"verdict": vd, "ledger_block": "NET Sharpe 1.19 vs bench 0.89",
                             "produced_at": "2026-07-15"})
    c.commit()
    out = RLI.backfill_legacy_payloads(c)
    assert out["migrated"] == 1
    raw = json.loads(c.execute("SELECT payload_json FROM review_items WHERE id=?",
                               (r["id"],)).fetchone()[0])
    assert "net_retvol" in raw["verdict"]["numbers"] and "net_sharpe" not in raw["verdict"]["numbers"]
    # the regenerated block is on the honest vocabulary — no bare "Sharpe" into canon
    assert "Sharpe" not in raw["ledger_block"] and "return/vol" in raw["ledger_block"].lower()
    assert RLI.backfill_legacy_payloads(c)["migrated"] == 0     # idempotent
    c.close()
