"""The Review-Inbox LENS + the Q1 bridge (S158) — contracts.

Two things are pinned here, both of which would be silent, expensive failures:

  1. THE OWNER GATE. The inbox carries kind='brief' — AI-drafted event notes that
     nobody has checked. The L6 contract is that only an APPROVED brief publishes;
     a public page rendering pending briefs would publish precisely the unreviewed
     AI text that contract forbids. So the anonymous page must never emit an item
     title, a ref, a payload, a decide button or the corpus CSV — asserted, not
     assumed, and asserted on a brief specifically.

  2. THE BRIDGE (Q1). The legacy /dash/tags-review buttons must reach company_tags
     THROUGH the inbox, so the judgment corpus stops being bypassed — while staying
     unbreakable (fail-open) and honest about what it does NOT record (authoring).

Hermetic: temp sqlite, the real theme_tags keyword proposer, a stubbed owner check.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.automation import inbox_adapters as ia
from src.automation import review_inbox as ri
from src.automation import theme_tags as tt
from src.web import review_inbox_view as V

_LEGACY_DDL = """
CREATE TABLE IF NOT EXISTS company_tags (
    symbol TEXT NOT NULL, tag TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'index',
    confidence REAL, as_of TEXT NOT NULL DEFAULT (date('now')),
    approved INTEGER NOT NULL DEFAULT 1, note TEXT,
    PRIMARY KEY (symbol, tag, source));
CREATE TABLE IF NOT EXISTS company_about (
    symbol TEXT PRIMARY KEY, about TEXT, screener_industry TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')));
"""


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "t.db")
    conn = sqlite3.connect(path)
    conn.executescript(_LEGACY_DDL)
    conn.execute("INSERT INTO company_about(symbol, about) VALUES "
                 "('SOLARCO','Develops solar and wind power generation projects.')")
    conn.commit()
    ri.ensure_schema(conn)
    conn.commit()
    yield path, conn
    conn.close()


@pytest.fixture()
def client(db, monkeypatch):
    path, _ = db
    owner = {"v": False}
    monkeypatch.setattr(V, "_conn", lambda: sqlite3.connect(path))
    monkeypatch.setattr(V, "_is_owner", lambda request: owner["v"])
    app = FastAPI()
    app.include_router(V.router)
    return TestClient(app), owner


# ── 1. the owner gate ────────────────────────────────────────────────────────────

def test_public_page_never_leaks_a_pending_brief(client, db):
    """The load-bearing one: an UNREVIEWED AI draft must not reach a public page."""
    _, conn = db
    ri.submit(conn, "brief", "results:TCS:2026-06",
              "Results brief: TCS Q1 revenue up 8%",
              payload={"body": "AI-drafted text nobody has checked yet"})
    conn.commit()
    c, _owner = client
    body = c.get("/dash/inbox").text
    assert "Results brief" not in body
    assert "results:TCS:2026-06" not in body
    assert "nobody has checked" not in body
    assert "Approve" not in body


def test_public_page_shows_honest_aggregates_but_no_items(client, db):
    _, conn = db
    ri.submit(conn, "tags", "SOLARCO|Power / Renewables", "Proposed tag")
    conn.commit()
    c, _ = client
    body = c.get("/dash/inbox").text
    assert "Review inbox" in body and "decisions recorded" in body
    assert "SOLARCO|Power" not in body, "a ref is item content — owner only"


def test_public_csv_is_forbidden_owner_csv_is_served(client, db):
    _, conn = db
    r = ri.submit(conn, "tags", "SOLARCO|PSU", "Proposed tag: PSU for SOLARCO")
    ri.decide(conn, r["id"], "approved")
    conn.commit()
    c, owner = client
    assert c.get("/dash/inbox?fmt=csv").status_code == 403
    owner["v"] = True
    ok = c.get("/dash/inbox?fmt=csv")
    assert ok.status_code == 200 and "kind,ref,status,decided_at,imported,note" in ok.text


def test_owner_sees_queue_with_evidence_and_buttons(client, db):
    _, conn = db
    ri.submit(conn, "tags", "SOLARCO|Power / Renewables",
              "Proposed tag: Power / Renewables for SOLARCO",
              payload={"symbol": "SOLARCO", "tag": "Power / Renewables",
                       "source": "keyword", "note": "matched: solar"},
              evidence_url="/dash/tags-review?sym=SOLARCO")
    conn.commit()
    c, owner = client
    owner["v"] = True
    body = c.get("/dash/inbox").text
    assert "SOLARCO|Power / Renewables" in body
    assert "proposed by: keyword" in body and "matched: solar" in body
    assert "/dash/tags-review?sym=SOLARCO" in body
    assert "Approve" in body and "Reject" in body


def test_decide_is_post_only_and_owner_only(client, db):
    _, conn = db
    r = ri.submit(conn, "tags", "SOLARCO|PSU", "Proposed tag: PSU for SOLARCO",
                  payload={"symbol": "SOLARCO", "tag": "PSU"})
    conn.commit()
    c, owner = client
    assert c.get("/dash/inbox/decide", follow_redirects=False).status_code == 405
    # anonymous POST is bounced without deciding
    c.post("/dash/inbox/decide", data={"item_id": r["id"], "verdict": "approved"},
           follow_redirects=False)
    assert ri.pending(sqlite3.connect(_path_of(conn)), kind="tags"), "must stay pending"


def _path_of(conn) -> str:
    return conn.execute("PRAGMA database_list").fetchone()[2]


def test_owner_decide_records_and_applies(client, db):
    path, conn = db
    r = ri.submit(conn, "tags", "SOLARCO|PSU", "Proposed tag: PSU for SOLARCO",
                  payload={"symbol": "SOLARCO", "tag": "PSU"})
    conn.commit()
    c, owner = client
    owner["v"] = True
    resp = c.post("/dash/inbox/decide",
                  data={"item_id": r["id"], "verdict": "approved", "note": "yes"},
                  follow_redirects=False)
    assert resp.status_code == 303
    chk = sqlite3.connect(path)
    assert chk.execute("SELECT status, note FROM review_items WHERE id=?",
                       (r["id"],)).fetchone() == ("approved", "yes")
    assert chk.execute("SELECT COUNT(*) FROM company_tags WHERE symbol='SOLARCO' "
                       "AND tag='PSU' AND source='ramana'").fetchone()[0] == 1
    chk.close()


# ── 2. the honesty split ─────────────────────────────────────────────────────────

def test_lived_and_imported_rates_are_never_blended(client, db):
    """The imported history cannot tell an approved proposal from a hand-added tag,
    so one blended rate would over-state the proposers. Two columns, and the reason
    stated on the page."""
    _, conn = db
    a = ri.submit(conn, "tags", "A|PSU", "t", payload={"imported": True})
    b = ri.submit(conn, "tags", "B|PSU", "t", payload={"imported": True})
    live = ri.submit(conn, "tags", "C|PSU", "t", payload={"symbol": "C", "tag": "PSU"})
    ri.decide(conn, a["id"], "approved")
    ri.decide(conn, b["id"], "approved")
    ri.decide(conn, live["id"], "rejected")
    conn.commit()
    c, _ = client
    body = c.get("/dash/inbox").text
    assert "Why two rates, not one" in body
    rows = V._split_stats(ri.corpus(sqlite3.connect(_path_of(conn)), kind="tags"))
    assert rows["tags"]["imported"] == {"approved": 2, "rejected": 0}
    assert rows["tags"]["lived"] == {"approved": 0, "rejected": 1}
    assert "0%" in body and "100%" in body, "the two rates must both surface"


# ── 3. the bridge (Q1) ───────────────────────────────────────────────────────────

def test_bridge_records_a_legacy_decision_in_the_corpus(db):
    _, conn = db
    tt.propose_from_keywords(conn=conn)
    out = ia.decide_by_ref(conn, "SOLARCO", "Power / Renewables", "approved")
    assert out["action"] == "applied-approved"
    row = ri.corpus(conn, kind="tags")[0]
    assert row["payload"]["decided_via"] == "tags-review surface"
    assert row["payload"]["source"] == "keyword", "proposer provenance is carried"
    assert conn.execute("SELECT COUNT(*) FROM company_tags WHERE symbol='SOLARCO' "
                        "AND source='ramana'").fetchone()[0] == 1


def test_bridge_survives_a_pair_with_no_live_proposal(db):
    """A decision straight off the legacy page (no pending proposal) still records."""
    _, conn = db
    out = ia.decide_by_ref(conn, "SOLARCO", "PSU", "approved")
    assert out["status"] == "approved"
    assert ri.corpus(conn, kind="tags")[0]["payload"]["source"] == "manual"


def test_rejudgment_versions_the_ref_and_keeps_both_verdicts(db):
    """unreject() -> re-approve was a latent crash (decide() is FINAL). The corpus
    keeps the change of mind as history."""
    _, conn = db
    ia.decide_by_ref(conn, "SOLARCO", "PSU", "rejected")
    tt.unreject(conn, "SOLARCO", "PSU")
    out = ia.decide_by_ref(conn, "SOLARCO", "PSU", "approved")
    assert out["ref"] == "SOLARCO|PSU#2"
    hist = ri.corpus(conn, kind="tags")
    assert [h["status"] for h in hist] == ["rejected", "approved"]
    assert conn.execute("SELECT COUNT(*) FROM company_tags WHERE symbol='SOLARCO' "
                        "AND tag='PSU' AND source='ramana'").fetchone()[0] == 1


def test_next_ref_returns_a_pending_items_own_ref(db):
    """A pair awaiting judgment must reuse its ref — not spawn #2 on every sync."""
    _, conn = db
    ri.submit(conn, "tags", "SOLARCO|PSU", "t")
    assert ia._next_ref(conn, "SOLARCO", "PSU") == "SOLARCO|PSU"


def test_versioned_ref_still_parses_a_slashed_tag(db):
    """'Power / Renewables#2' must not become the tag — the '#N' is ours, the '/' is theirs."""
    assert ia._sym_tag(None, "SOLARCO|Power / Renewables#2") == (
        "SOLARCO", "Power / Renewables")


def test_bridge_is_fail_open_the_button_can_never_break(db, monkeypatch):
    """If the inbox path throws, the tag STILL applies (corpus loses one row)."""
    _, conn = db
    monkeypatch.setattr(ia, "decide_by_ref",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = ia.decide_by_ref_safe(conn, "SOLARCO", "PSU", "approved")
    assert out["action"] == "fallback-direct"
    assert conn.execute("SELECT COUNT(*) FROM company_tags WHERE symbol='SOLARCO' "
                        "AND tag='PSU' AND source='ramana'").fetchone()[0] == 1


def test_bulk_bridge_records_one_corpus_row_per_pair(db):
    _, conn = db
    for s in ("AAA", "BBB"):
        conn.execute("INSERT INTO company_tags(symbol, tag, source, as_of, approved) "
                     "VALUES (?,'Defence','keyword','2026-07-01',0)", (s,))
    conn.commit()
    n = ia.decide_bulk(conn, tag="Defence")
    assert n == 2
    rows = ri.corpus(conn, kind="tags")
    assert len(rows) == 2
    assert all(r["payload"]["decided_via"] == "tags-review bulk (theme)" for r in rows)
    assert conn.execute("SELECT COUNT(*) FROM company_tags WHERE tag='Defence' "
                        "AND source='ramana'").fetchone()[0] == 2


def test_authoring_actions_stay_out_of_the_corpus(db):
    """add/remove are AUTHORING — counting them as machine wins would inflate the
    agreement rate. The boundary is deliberate, so it is pinned."""
    _, conn = db
    tt.add_manual(conn, "SOLARCO", "PSU")
    assert ri.corpus(conn, kind="tags") == []


# ── 4. the kind registry is a real gate, not decoration ──────────────────────────

def test_every_producer_kind_is_registered():
    """A producer that invents a kind MUST register it in KINDS in the same commit
    (inbox_adapters' docstring rule). This is not theoretical: rule_lab_inbox's
    'rule_verdict' shipped un-registered while the registry was being written — the
    live census warned and the lens rendered a raw slug. Source-scanned, so a NEW
    producer module is covered without anyone remembering to list it here.
    """
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "automation"
    offenders = []
    for py in sorted(root.glob("*.py")):
        src = py.read_text(encoding="utf-8", errors="ignore")
        if "review_inbox" not in src or py.name == "inbox_adapters.py":
            continue
        for m in re.finditer(r'^KIND(?:_[A-Z]+)?\s*=\s*["\']([^"\']+)["\']', src, re.M):
            if m.group(1) not in ia.KINDS:
                offenders.append("%s declares KIND=%r" % (py.name, m.group(1)))
    assert not offenders, (
        "\nProducer kinds missing from inbox_adapters.KINDS (add them there in the "
        "SAME commit as the producer):\n  " + "\n  ".join(offenders))


def test_the_lens_can_render_every_registered_kind():
    """Every canonical kind needs display copy, or the queue shows a raw slug with no
    explanation to the one person who has to judge it."""
    missing = sorted(k for k in ia.KINDS if k not in V._KIND_COPY)
    assert not missing, "kinds with no _KIND_COPY row: %s" % missing


def test_rule_verdict_items_render_with_their_producer(db, client):
    """The rule-lab payload says 'producer', the tag payload says 'source' — the
    evidence line must survive both."""
    _, conn = db
    ri.submit(conn, "rule_verdict", "abc123hash",
              "Rule-lab: NEW-BENCHMARK [fundable] - SELECT largecap ...",
              payload={"producer": "rule_lab", "ledger_block": "| RULE | ... |"},
              evidence_url="/dash/rule-lab")
    conn.commit()
    c, owner = client
    owner["v"] = True
    body = c.get("/dash/inbox").text
    assert "Rule-lab verdicts" in body, "the kind needs its human label"
    assert "proposed by: rule_lab" in body
    assert "signs the result into the ledger" in body


def test_selftest_is_green():
    assert V._selftest() == 0
