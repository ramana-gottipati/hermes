"""Entity graph v1 (D134 plan §4-G, layer L2) — WHO connects to WHOM, descriptively.

Derives relationship EDGES from filing tables we already own (no new feed, no
network, Guardrail #8 safe — every edge traces to a primary-source row):

    person_hash    --insider_filing-->    company     (insider_events)
    acquirer_hash  --sast_acquisition-->  company     (sast_reg29_events)
    promoter_hash  --pledge-->            company     (sast_pledge_events)
    lender         --pledge_lender-->     company     (sast_pledge_events.counterparty)
    counterparty   --bulk_deal/block_deal--> company  (bulk_block_deals)
    agency         --rating_action-->     company     (credit_rating_events)

The value is the JOIN nobody else does cheaply: the same filer/acquirer/lender
appearing across MULTIPLE companies — `neighborhood(symbol)` surfaces those
co-links with their source rows. That is a research affordance, not a verdict.

=========================== THE FENCE (read before extending) ==================
DESCRIPTIVE RELATIONSHIPS WITH SOURCE REFS. NO SCORING — deliberately no weight,
strength or rank column exists, and none may be added without its own
pre-registration. Two ledger entries make this binding, not stylistic:

  * **E-03 insider disclosure drift** — value-Q4 CAR60 +8.26% (n=66, plain t 2.87)
    looked real, but the **placebo p95 was +9.52% > observed** (null mean +3.38%,
    emp-p 0.085) and t_cohort was NaN (feed ~10 months deep → 2-3 quarterly
    cohorts, no clustered inference). Verdict: NO insider-drift lens ships;
    re-attempt needs >=8 quarterly cohorts of feed depth AND a placebo-clearing
    observed mean.
  * **Accumulation-footprint detector v1 (2026-07-05b)** — pre-registered gate
    FAIL 1/4; 764/947 episodes had NO pre-public window (SEBI PIT T+2 regime);
    n=54 usable. Survivor: avg-trade-size ratio, a descriptive column only.

Both say the same thing: these filings are RICH as context and DEAD as alpha at
this feed depth. An edge count is not evidence. Anyone turning a degree count
into a signal must beat those exact numbers under a leak-free pre-registered
harness first (docs/strategy-ledger.md).

=========================== PROVENANCE + PRIVACY ==============================
* Dates are the PUBLIC-RECORD dates (disclosure_dt / broadcast_dt / trade_date /
  rating_date), never the private transaction date — an edge is knowable when the
  filing hit the public record (the T+2 discipline), not when the deed happened.
* ROWS != EVENTS (the D94 lesson): one edge AGGREGATES many filings, so it carries
  `n_events` + `first_seen`/`last_seen` bounds + a traceable `source_ref`. Never
  read n_events as intensity — a chatty filer is not a strong relationship.
* Hashed feeds stay hashed: insider/SAST/pledge persons arrive as
  `person_name_hash`/`acquirer_hash`/`promoter_hash` and are stored verbatim as
  opaque ids — this module NEVER re-identifies them. Bulk-deal client names and
  pledge lender counterparties are stored as published, because NSE discloses
  those verbatim as public record. Two postures, both honest, neither mixed.

CLI: --rebuild [--db PATH] | --neighborhood SYMBOL | --stats | --selftest.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from typing import Optional

HERMES_DB = "/opt/hermes/data/hermes.db"

#: node kinds; 'company' is always the destination in v1 (a bipartite graph —
#: company<->company links are DERIVED at read time via a shared counterpart,
#: never stored as an asserted relationship we did not observe).
SRC_KINDS = frozenset({"person_hash", "acquirer_hash", "promoter_hash",
                       "lender", "counterparty", "agency"})
DST_KINDS = frozenset({"company"})


@dataclass(frozen=True)
class Extractor:
    """One declarative edge derivation over a table we already own.

    `sql` MUST return (src_id, dst_id, first_seen, last_seen, n_events, source_ref)
    already aggregated, so a rebuild is one pass per source with no Python loop
    over events.
    """

    edge_kind: str
    src_kind: str
    table: str
    sql: str


_EXTRACTORS: tuple[Extractor, ...] = (
    Extractor(
        edge_kind="insider_filing",
        src_kind="person_hash",
        table="insider_events",
        # disclosure_dt = the public-record clock (SEBI PIT T+2), NOT transaction_dt.
        sql="""SELECT person_name_hash, symbol, MIN(disclosure_dt), MAX(disclosure_dt),
                      COUNT(*), 'insider_events#' || MAX(uid)
               FROM insider_events
               WHERE person_name_hash IS NOT NULL AND person_name_hash <> ''
                 AND symbol IS NOT NULL AND symbol <> ''
                 AND disclosure_dt IS NOT NULL AND disclosure_dt <> ''
               GROUP BY person_name_hash, symbol""",
    ),
    Extractor(
        edge_kind="sast_acquisition",
        src_kind="acquirer_hash",
        table="sast_reg29_events",
        sql="""SELECT acquirer_hash, symbol, MIN(broadcast_dt), MAX(broadcast_dt),
                      COUNT(*), 'sast_reg29_events#' || MAX(uid)
               FROM sast_reg29_events
               WHERE acquirer_hash IS NOT NULL AND acquirer_hash <> ''
                 AND symbol IS NOT NULL AND symbol <> ''
                 AND broadcast_dt IS NOT NULL AND broadcast_dt <> ''
               GROUP BY acquirer_hash, symbol""",
    ),
    Extractor(
        edge_kind="pledge",
        src_kind="promoter_hash",
        table="sast_pledge_events",
        sql="""SELECT promoter_hash, symbol, MIN(broadcast_dt), MAX(broadcast_dt),
                      COUNT(*), 'sast_pledge_events#' || MAX(uid)
               FROM sast_pledge_events
               WHERE promoter_hash IS NOT NULL AND promoter_hash <> ''
                 AND symbol IS NOT NULL AND symbol <> ''
                 AND broadcast_dt IS NOT NULL AND broadcast_dt <> ''
               GROUP BY promoter_hash, symbol""",
    ),
    Extractor(
        edge_kind="pledge_lender",
        src_kind="lender",
        table="sast_pledge_events",
        # counterparty = the lender/pledgee as PUBLISHED (public record, not hashed).
        sql="""SELECT TRIM(counterparty), symbol, MIN(broadcast_dt), MAX(broadcast_dt),
                      COUNT(*), 'sast_pledge_events#' || MAX(uid)
               FROM sast_pledge_events
               WHERE counterparty IS NOT NULL AND TRIM(counterparty) <> ''
                 AND symbol IS NOT NULL AND symbol <> ''
                 AND broadcast_dt IS NOT NULL AND broadcast_dt <> ''
               GROUP BY TRIM(counterparty), symbol""",
    ),
    Extractor(
        edge_kind="deal",
        src_kind="counterparty",
        table="bulk_block_deals",
        # deal_type (bulk|block) is kept in source_ref rather than split into two
        # edge kinds: the relationship is "named client traded this stock on the
        # tape"; the venue is provenance, not a different relationship.
        sql="""SELECT TRIM(client_name), symbol, MIN(trade_date), MAX(trade_date),
                      COUNT(*),
                      'bulk_block_deals@' || MAX(trade_date) || ':' || MAX(deal_type)
               FROM bulk_block_deals
               WHERE client_name IS NOT NULL AND TRIM(client_name) <> ''
                 AND symbol IS NOT NULL AND symbol <> ''
                 AND trade_date IS NOT NULL AND trade_date <> ''
               GROUP BY TRIM(client_name), symbol""",
    ),
    Extractor(
        edge_kind="rating_action",
        src_kind="agency",
        table="credit_rating_events",
        sql="""SELECT TRIM(agency), symbol, MIN(rating_date), MAX(rating_date),
                      COUNT(*), 'credit_rating_events#' || MAX(uid)
               FROM credit_rating_events
               WHERE agency IS NOT NULL AND TRIM(agency) <> ''
                 AND symbol IS NOT NULL AND symbol <> ''
                 AND rating_date IS NOT NULL AND rating_date <> ''
               GROUP BY TRIM(agency), symbol""",
    ),
)

EDGE_KINDS = frozenset(e.edge_kind for e in _EXTRACTORS)


# ------------------------------------------------------------------ schema

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Own table, CREATE IF NOT EXISTS — db.py is never edited (the §0.8 isolation
    rule). No score/weight column exists BY DESIGN (see the module fence)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS entity_edges (
               src_kind   TEXT NOT NULL,
               src_id     TEXT NOT NULL,
               dst_kind   TEXT NOT NULL,
               dst_id     TEXT NOT NULL,
               edge_kind  TEXT NOT NULL,
               first_seen TEXT,
               last_seen  TEXT,
               n_events   INTEGER NOT NULL DEFAULT 0,
               source_ref TEXT,
               PRIMARY KEY (src_kind, src_id, dst_kind, dst_id, edge_kind)
           )""")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_entity_edges_dst "
                 "ON entity_edges (dst_id, dst_kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_entity_edges_src "
                 "ON entity_edges (src_id, src_kind)")


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


# ------------------------------------------------------------------ rebuild

def rebuild(*, conn: Optional[sqlite3.Connection] = None, db_path: str = HERMES_DB) -> dict:
    """Re-derive every edge from the source tables. IDEMPOTENT: the natural key
    (src_kind, src_id, dst_kind, dst_id, edge_kind) upserts, so a second run
    changes nothing but refreshed bounds. A missing source table is SKIPPED (the
    feed simply isn't ingested on this box), never an error.

    Returns {edge_kind: rows} + 'skipped' for absent sources.
    """
    own = conn is None
    c = conn if conn is not None else sqlite3.connect(db_path, timeout=60)
    try:
        ensure_schema(c)
        out: dict = {}
        skipped: list[str] = []
        for ex in _EXTRACTORS:
            if not _has_table(c, ex.table):
                skipped.append(ex.edge_kind)
                continue
            rows = c.execute(ex.sql).fetchall()
            c.executemany(
                """INSERT INTO entity_edges
                       (src_kind, src_id, dst_kind, dst_id, edge_kind,
                        first_seen, last_seen, n_events, source_ref)
                   VALUES (?,?,'company',?,?,?,?,?,?)
                   ON CONFLICT (src_kind, src_id, dst_kind, dst_id, edge_kind)
                   DO UPDATE SET first_seen = excluded.first_seen,
                                 last_seen  = excluded.last_seen,
                                 n_events   = excluded.n_events,
                                 source_ref = excluded.source_ref""",
                [(ex.src_kind, r[0], r[1], ex.edge_kind, r[2], r[3], r[4], r[5])
                 for r in rows])
            out[ex.edge_kind] = len(rows)
        c.commit()
        if skipped:
            out["skipped"] = skipped
        return out
    finally:
        if own:
            c.close()


# ------------------------------------------------------------------ read API

def _dictify(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def neighborhood(symbol: str, *, conn: Optional[sqlite3.Connection] = None,
                 db_path: str = HERMES_DB, with_co_links: bool = True,
                 limit: int = 200) -> dict:
    """Everything we have OBSERVED touching `symbol`, with source refs.

    Returns {'symbol', 'edges': [...], 'co_links': [...]}.
      * `edges`     — the counterparts that filed/traded/rated this company.
      * `co_links`  — OTHER companies those same counterparts also touch (the
        actual graph payoff). Each carries `via` + `via_kind` + `n_events` so a
        reader can trace WHY the two names are adjacent.
    A co-link asserts CO-OCCURRENCE IN THE PUBLIC RECORD, nothing more: no
    ownership, control, collusion or intent is claimed or implied.

    ⚠ HUB COUNTERPARTS ARE NOT INSIGHT (measured on live data, 2026-07-15): a
    handful of counterparts touch nearly everything — 7 rating agencies cover 63+
    companies, so an agency co-link is structurally guaranteed and says NOTHING
    about the two companies. The informative co-links are the sparse ones: a
    shared INSIDER (67 filers touch >1 company), lender (46), acquirer (111) or
    deal counterparty (97). Any surface built on this MUST rank by scarcity of
    the counterpart and must never render a raw co-link COUNT as a headline
    ("connected to 74 companies!" is an artefact of CARE Ratings existing).
    Degree is not importance — and a degree that became a score would need its
    own pre-registration (see the fence above).
    """
    own = conn is None
    c = conn if conn is not None else sqlite3.connect(db_path, timeout=30)
    try:
        ensure_schema(c)
        sym = (symbol or "").strip().upper()
        edges = _dictify(c.execute(
            """SELECT src_kind, src_id, edge_kind, first_seen, last_seen,
                      n_events, source_ref
               FROM entity_edges
               WHERE dst_kind='company' AND dst_id=?
               ORDER BY last_seen DESC, n_events DESC LIMIT ?""", (sym, limit)))
        co: list[dict] = []
        if with_co_links and edges:
            co = _dictify(c.execute(
                """SELECT b.dst_id AS symbol, b.edge_kind, b.src_id AS via,
                          b.src_kind AS via_kind, b.n_events, b.last_seen
                   FROM entity_edges a
                   JOIN entity_edges b
                     ON a.src_kind = b.src_kind AND a.src_id = b.src_id
                    AND a.edge_kind = b.edge_kind
                   WHERE a.dst_kind='company' AND a.dst_id=?
                     AND b.dst_kind='company' AND b.dst_id <> a.dst_id
                   ORDER BY b.last_seen DESC, b.n_events DESC LIMIT ?""",
                (sym, limit)))
        return {"symbol": sym, "edges": edges, "co_links": co}
    finally:
        if own:
            c.close()


def stats(*, conn: Optional[sqlite3.Connection] = None, db_path: str = HERMES_DB) -> dict:
    """Coverage counts per edge kind — the honest 'what do we actually have' read."""
    own = conn is None
    c = conn if conn is not None else sqlite3.connect(db_path, timeout=30)
    try:
        ensure_schema(c)
        rows = c.execute(
            """SELECT edge_kind, COUNT(*), COUNT(DISTINCT src_id), COUNT(DISTINCT dst_id),
                      MIN(first_seen), MAX(last_seen)
               FROM entity_edges GROUP BY edge_kind ORDER BY COUNT(*) DESC""").fetchall()
        return {r[0]: {"edges": r[1], "counterparts": r[2], "companies": r[3],
                       "first_seen": r[4], "last_seen": r[5]} for r in rows}
    finally:
        if own:
            c.close()


# ------------------------------------------------------------------ selftest

def _selftest() -> int:
    import os
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + name)
        ok = ok and bool(cond)

    db = os.path.join(tempfile.mkdtemp(prefix="entity_graph_"), "g.db")
    c = sqlite3.connect(db)
    c.execute("""CREATE TABLE insider_events (uid TEXT, symbol TEXT, disclosure_dt TEXT,
                 transaction_dt TEXT, person_name_hash TEXT)""")
    c.executemany("INSERT INTO insider_events VALUES (?,?,?,?,?)", [
        ("u1", "ACME", "2026-05-02", "2026-04-30", "hash_a"),
        ("u2", "ACME", "2026-06-02", "2026-05-30", "hash_a"),
        ("u3", "BETA", "2026-06-10", "2026-06-08", "hash_a"),   # the co-link
        ("u4", "ACME", "2026-06-11", "2026-06-09", ""),          # junk: dropped
    ])
    c.commit()
    c.close()

    r1 = rebuild(db_path=db)
    check("insider edges derived", r1.get("insider_filing") == 2)
    check("absent sources skipped, not fatal", "deal" in (r1.get("skipped") or []))

    r2 = rebuild(db_path=db)
    con = sqlite3.connect(db)
    n = con.execute("SELECT COUNT(*) FROM entity_edges").fetchone()[0]
    con.close()
    check("rebuild idempotent", r2.get("insider_filing") == 2 and n == 2)

    nb = neighborhood("ACME", db_path=db)
    check("neighborhood finds the filer", len(nb["edges"]) == 1
          and nb["edges"][0]["src_id"] == "hash_a" and nb["edges"][0]["n_events"] == 2)
    check("aggregate carries public-record bounds",
          nb["edges"][0]["first_seen"] == "2026-05-02"     # disclosure, not transaction
          and nb["edges"][0]["last_seen"] == "2026-06-02")
    check("co-link surfaces the other company",
          [x["symbol"] for x in nb["co_links"]] == ["BETA"])
    check("stats reports coverage", stats(db_path=db)["insider_filing"]["companies"] == 2)

    cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(entity_edges)")}
    check("NO score/weight column exists (the fence)",
          not (cols & {"score", "weight", "strength", "rank"}))
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Entity graph — descriptive relationship edges from our filing tables.")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--neighborhood", metavar="SYMBOL")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--db", default=HERMES_DB)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.rebuild:
        for k, v in rebuild(db_path=a.db).items():
            print(f"  {k:18} {v}")
        return 0
    if a.neighborhood:
        nb = neighborhood(a.neighborhood, db_path=a.db)
        print(f"{nb['symbol']} — {len(nb['edges'])} edges, {len(nb['co_links'])} co-links "
              f"(descriptive co-occurrence in the public record; never a signal)")
        for e in nb["edges"][:20]:
            print(f"  {e['edge_kind']:16} {e['src_kind']:14} {str(e['src_id'])[:28]:28} "
                  f"n={e['n_events']:<4} {e['first_seen']}..{e['last_seen']}  {e['source_ref']}")
        for x in nb["co_links"][:20]:
            print(f"  co-link: {x['symbol']:14} via {x['via_kind']}={str(x['via'])[:24]:24} "
                  f"({x['edge_kind']}, n={x['n_events']})")
        return 0
    if a.stats:
        for k, v in stats(db_path=a.db).items():
            print(f"  {k:18} edges={v['edges']:<7} counterparts={v['counterparts']:<7} "
                  f"companies={v['companies']:<6} {v['first_seen']}..{v['last_seen']}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
