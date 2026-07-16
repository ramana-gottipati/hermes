"""Entity graph contracts (D134 LANE-G, plan §4-G / L2).

Hermetic temp-DB tests over synthetic filing tables. The fence tests are the
important ones: this module may only ever assert OBSERVED co-occurrence with a
source ref — the ledger (E-03 insider drift: placebo p95 +9.52% > observed
+8.26%, emp-p 0.085; accumulation-footprint v1: gate FAIL 1/4, n=54) forbids any
scored/predictive reading of these same filings.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.automation import entity_graph as eg  # noqa: E402


def _src(tmp_path):
    """A DB carrying all six source tables with a known, hand-checkable shape."""
    db = str(tmp_path / "g.db")
    c = sqlite3.connect(db)
    c.execute("""CREATE TABLE insider_events (uid TEXT, symbol TEXT, disclosure_dt TEXT,
                 transaction_dt TEXT, person_name_hash TEXT)""")
    c.executemany("INSERT INTO insider_events VALUES (?,?,?,?,?)", [
        ("u1", "ACME", "2026-05-02", "2026-04-30", "hash_a"),
        ("u2", "ACME", "2026-06-02", "2026-05-30", "hash_a"),
        ("u3", "BETA", "2026-06-10", "2026-06-08", "hash_a"),
        ("u4", "ACME", "2026-06-11", "2026-06-09", "hash_b"),
    ])
    c.execute("""CREATE TABLE sast_reg29_events (uid TEXT, symbol TEXT, broadcast_dt TEXT,
                 acquirer_hash TEXT)""")
    c.execute("INSERT INTO sast_reg29_events VALUES ('s1','ACME','2026-06-05','hash_x')")
    c.execute("""CREATE TABLE sast_pledge_events (uid TEXT, symbol TEXT, broadcast_dt TEXT,
                 promoter_hash TEXT, counterparty TEXT)""")
    c.executemany("INSERT INTO sast_pledge_events VALUES (?,?,?,?,?)", [
        ("p1", "ACME", "2026-04-01", "hash_p", "Big Lender Ltd"),
        ("p2", "GAMMA", "2026-04-09", "hash_p", "Big Lender Ltd"),
    ])
    c.execute("""CREATE TABLE bulk_block_deals (trade_date TEXT, symbol TEXT, deal_type TEXT,
                 client_name TEXT, side TEXT, qty INTEGER, price REAL)""")
    c.executemany("INSERT INTO bulk_block_deals VALUES (?,?,?,?,?,?,?)", [
        ("2026-03-02", "ACME", "bulk", "A AND S TRADELINK", "BUY", 100, 10.0),
        ("2026-03-09", "ACME", "block", "A AND S TRADELINK", "SELL", 50, 11.0),
    ])
    c.execute("""CREATE TABLE credit_rating_events (uid TEXT, symbol TEXT, agency TEXT,
                 rating_date TEXT, action_class TEXT)""")
    c.execute("INSERT INTO credit_rating_events VALUES ('r1','ACME','CRISIL','2026-02-01','downgrade')")
    c.commit()
    c.close()
    return db


# ------------------------------------------------------------------ extraction

def test_all_six_edge_kinds_derive(tmp_path):
    out = eg.rebuild(db_path=_src(tmp_path))
    assert out["insider_filing"] == 3      # (hash_a,ACME) (hash_a,BETA) (hash_b,ACME)
    assert out["sast_acquisition"] == 1
    assert out["pledge"] == 2
    assert out["pledge_lender"] == 2
    assert out["deal"] == 1                # both deals collapse to ONE relationship
    assert out["rating_action"] == 1
    assert "skipped" not in out


def test_edges_aggregate_events_not_rows(tmp_path):
    """One edge per (counterpart, company): n_events counts the filings behind it."""
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    e = [x for x in eg.neighborhood("ACME", db_path=db)["edges"]
         if x["edge_kind"] == "insider_filing" and x["src_id"] == "hash_a"][0]
    assert e["n_events"] == 2
    assert e["first_seen"] == "2026-05-02" and e["last_seen"] == "2026-06-02"


def test_public_record_dates_not_transaction_dates(tmp_path):
    """The knowable clock is disclosure_dt (SEBI PIT T+2), never transaction_dt."""
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    e = [x for x in eg.neighborhood("ACME", db_path=db)["edges"]
         if x["src_id"] == "hash_a"][0]
    assert e["first_seen"] != "2026-04-30", "leaked the private transaction date"
    assert e["first_seen"] == "2026-05-02"


def test_every_edge_carries_a_source_ref(tmp_path):
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    con = sqlite3.connect(db)
    rows = con.execute("SELECT edge_kind, source_ref FROM entity_edges").fetchall()
    con.close()
    assert rows
    for kind, ref in rows:
        assert ref and str(ref).strip(), f"{kind} edge lacks a traceable source_ref"


def test_junk_rows_dropped_not_raised(tmp_path):
    db = str(tmp_path / "j.db")
    c = sqlite3.connect(db)
    c.execute("""CREATE TABLE insider_events (uid TEXT, symbol TEXT, disclosure_dt TEXT,
                 transaction_dt TEXT, person_name_hash TEXT)""")
    c.executemany("INSERT INTO insider_events VALUES (?,?,?,?,?)", [
        ("u1", "ACME", "2026-05-02", "2026-04-30", ""),      # no filer
        ("u2", "", "2026-05-02", "2026-04-30", "hash_a"),    # no symbol
        ("u3", "ACME", "", "2026-04-30", "hash_a"),          # no public date
        ("u4", "ACME", "2026-05-05", "2026-04-30", "hash_a"),  # the only good row
    ])
    c.commit(); c.close()
    assert eg.rebuild(db_path=db)["insider_filing"] == 1


def test_missing_source_tables_are_skipped(tmp_path):
    db = str(tmp_path / "empty.db")
    sqlite3.connect(db).close()
    out = eg.rebuild(db_path=db)
    assert sorted(out.get("skipped", [])) == sorted(eg.EDGE_KINDS)
    assert eg.neighborhood("ACME", db_path=db)["edges"] == []


def test_rebuild_is_idempotent(tmp_path):
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    first = eg.stats(db_path=db)
    eg.rebuild(db_path=db)
    con = sqlite3.connect(db)
    dupes = con.execute(
        """SELECT COUNT(*) FROM (SELECT src_kind, src_id, dst_id, edge_kind, COUNT(*) n
           FROM entity_edges GROUP BY 1,2,3,4 HAVING n > 1)""").fetchone()[0]
    con.close()
    assert dupes == 0
    assert eg.stats(db_path=db) == first


# ------------------------------------------------------------------ read API

def test_neighborhood_co_links_via_shared_counterpart(tmp_path):
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    nb = eg.neighborhood("ACME", db_path=db)
    co = {(x["symbol"], x["edge_kind"]) for x in nb["co_links"]}
    assert ("BETA", "insider_filing") in co       # hash_a filed on both
    assert ("GAMMA", "pledge") in co              # hash_p pledged at both
    assert ("GAMMA", "pledge_lender") in co       # same lender at both
    assert all(x["symbol"] != "ACME" for x in nb["co_links"]), "self must not co-link"
    for x in nb["co_links"]:
        assert x["via"] and x["via_kind"], "a co-link must say WHY it is adjacent"


def test_co_links_can_be_disabled(tmp_path):
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    assert eg.neighborhood("ACME", db_path=db, with_co_links=False)["co_links"] == []


def test_neighborhood_symbol_normalized_and_missing_is_graceful(tmp_path):
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    assert eg.neighborhood(" acme ", db_path=db)["edges"], "symbol must normalize"
    empty = eg.neighborhood("NOSUCHCO", db_path=db)
    assert empty["edges"] == [] and empty["co_links"] == []


def test_stats_coverage(tmp_path):
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    s = eg.stats(db_path=db)
    assert s["insider_filing"]["companies"] == 2
    assert s["insider_filing"]["counterparts"] == 2
    assert s["deal"]["first_seen"] == "2026-03-02" and s["deal"]["last_seen"] == "2026-03-09"


# ------------------------------------------------------------------ THE FENCE

def test_no_scoring_column_exists(tmp_path):
    """Descriptive-only is STRUCTURAL: there is nowhere to put a score.
    Adding one requires its own pre-registration (ledger E-03 / accumulation v1)."""
    db = _src(tmp_path)
    eg.rebuild(db_path=db)
    con = sqlite3.connect(db)
    cols = {r[1].lower() for r in con.execute("PRAGMA table_info(entity_edges)")}
    con.close()
    assert not (cols & {"score", "weight", "strength", "rank", "conviction", "signal"}), \
        f"a scoring column appeared in entity_edges: {cols}"


def test_module_cites_the_blocking_ledger_numbers():
    """The fence must stay CITED, not vibes — the next session has to see the
    numbers that killed the predictive reading of these same filings."""
    doc = eg.__doc__ or ""
    assert "+9.52%" in doc and "+8.26%" in doc, "E-03 placebo numbers missing"
    assert "0.085" in doc, "E-03 empirical p missing"
    assert "FAIL 1/4" in doc and "n=54" in doc, "accumulation-footprint numbers missing"
    assert "NO SCORING" in doc.upper()


def test_node_kinds_are_declared_and_bipartite():
    assert eg.DST_KINDS == {"company"}, "v1 is company-destination only"
    for ex in eg._EXTRACTORS:
        assert ex.src_kind in eg.SRC_KINDS, f"undeclared src_kind: {ex.src_kind}"


def test_hashed_ids_are_never_reidentified():
    """Hashed feeds stay hashed: no join back to a name column, no lookup table."""
    src = (REPO / "src" / "automation" / "entity_graph.py").read_text(encoding="utf-8").lower()
    for marker in ("person_name ", "unhash", "deanon", "reidentif", "name_lookup"):
        assert marker not in src, f"re-identification smell: {marker!r}"
