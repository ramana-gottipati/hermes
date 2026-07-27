"""test_home_markets_pages.py — the gate for the Graphite Markets estate (cutover lane W2-A).

Four consolidated declared children of the Graphite home carry ELEVEN classic Markets lenses:

    /dash/home/internals   <- market-internals · divergence
    /dash/home/flows       <- participants · fno
    /dash/home/events      <- actions · results-reactions · event-cadence · buyback-calc ·
                              surveillance · band-locks
    /dash/home/attention   <- attention

What this proves (structure, not data — the fixture DB is schema-only, so real-data verification
is a BOX activity per standing correction #9):
  1. every route + every `?format=csv` twin answers 200, in the Graphite scope, with no
     preview/legacy marker (the isolation contract, applied to THIS lane's pages);
  2. every advertised evidence block is actually present on its page (a consolidation can lose a
     block silently — this is the per-BLOCK parity check the ledger notes claim);
  3. the descriptive-only FENCES that must travel with these surfaces are on the page, not in a
     footnote (PEAD falsification · F&O Phase-0 · surveillance context-never-a-gate · band-lock
     honest window · corporate-actions logistics · attention not-a-recommendation);
  4. the pages are route-gate registered and parity-ledgered, and the ledger's PORTED targets are
     the live routes;
  5. symbol links use `sym=` (never `symbol=`) and point at the Graphite stock page;
  6. the read layer degrades to honest-empty on a schema-only DB — never an exception, never a 500.

Run
---
    pytest tests/test_home_markets_pages.py
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

ROUTES = ("/dash/home/internals", "/dash/home/flows", "/dash/home/events", "/dash/home/attention")

PREVIEW_LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')


@pytest.fixture(scope="module")
def client():
    from src.main import app
    return TestClient(app)


def _text(client, path):
    r = client.get(path, follow_redirects=True)
    assert r.status_code == 200, (path, r.status_code)
    return r.text


# ── 1. the pages exist, in the Graphite scope, uncontaminated ──────────────────────────
@pytest.mark.parametrize("path", ROUTES)
def test_page_renders_in_the_graphite_scope(client, path):
    t = _text(client, path)
    assert "data-ui-g" in t, path
    assert "gw2-sub" in t, (path, "the Markets-depth cross-link strip is missing")
    for m in PREVIEW_LEGACY_MARKERS:
        assert m not in t, (path, "leaked a preview/legacy marker", m)


@pytest.mark.parametrize("path", ROUTES)
def test_every_page_has_a_server_csv(client, path):
    """The playbook's server-CSV rule: a table a user can read is a table they can download —
    rendered by the server, never a client-only export."""
    r = client.get(path + "?format=csv")
    assert r.status_code == 200, (path, r.status_code)
    assert "text/csv" in r.headers.get("content-type", ""), path
    assert r.text.splitlines()[0].count(",") >= 3, (path, "CSV header looks degenerate")


@pytest.mark.parametrize("path", ROUTES)
def test_pages_are_cross_linked_to_each_other(client, path):
    """A declared child that nothing reaches is an orphan. Until W6 wires nav, the four pages are
    each other's front door (plus the existing rotation child)."""
    t = _text(client, path)
    for _key, href, _label in __import__(
            "src.web.home.internals_pages", fromlist=["PAGES"]).PAGES:
        assert href in t, (path, "missing cross-link to", href)
    assert "/dash/home/rotation" in t, path


# ── 2. per-BLOCK parity: every consolidated evidence block is actually on its page ──────
BLOCKS = {
    "/dash/home/internals": ("The market&#x27;s vital signs", "Price-breadth versus the tape",
                             "Regimes — delivery, dispersion, coil", "What carried a session",
                             "Crisis fingerprints", "Divergence watch"),
    "/dash/home/flows": ("Cash flows — foreign vs domestic",
                         "Derivatives positioning — who is long, who is short",
                         "F&amp;O positioning versus each stock&#x27;s own history"),
    "/dash/home/events": ("Going ex — the corporate-actions calendar",
                          "Results and what happened after",
                          "Event cadence — who is overdue against their own rhythm",
                          "Buyback tender calculator", "Surveillance transitions", "Band locks"),
    "/dash/home/attention": ("The alert rail", "The attention queue"),
}


@pytest.mark.parametrize("path", ROUTES)
def test_every_advertised_block_is_present(client, path):
    """Parity is per-BLOCK: consolidating eleven lenses into four pages must not quietly drop one.
    Each heading below corresponds to a block the sideways_parity note claims travelled."""
    t = _text(client, path)
    missing = [b for b in BLOCKS[path] if b not in t]
    assert not missing, (path, "advertised blocks missing from the page", missing)


# ── 3. the fences that MUST travel with their surface ──────────────────────────────────
FENCES = {
    # PEAD: the tradeable wrapper was falsified — the numbers must never read as a strategy
    "/dash/home/events": ("net return/vol 0.10", "Context, never a gate",
                          "close-at-band streak is a queue-imbalance tell",
                          "acceptance ratio is YOUR assumption", "Logistics, not a strategy"),
    # F&O Phase-0: PCR selects weakly and forward-test-only; everything else failed
    "/dash/home/flows": ("Phase-0 edge gate", "FORWARD-TEST-ONLY",
                         "nothing here ranks, picks or recommends"),
    "/dash/home/internals": ("Descriptive market-state, point-in-time",
                             "never a buy or sell instruction"),
    "/dash/home/attention": ("never a recommendation", "not a return forecast"),
}


@pytest.mark.parametrize("path", ROUTES)
def test_descriptive_only_fences_travel_with_the_surface(client, path):
    t = _text(client, path)
    missing = [f for f in FENCES[path] if f not in t]
    assert not missing, (path, "a descriptive-only fence did not travel with its block", missing)


def test_pead_fence_is_above_the_table_not_in_a_footnote(client):
    """Scope-check rule: a falsification disclosure goes ABOVE the headline, never below it."""
    t = _text(client, "/dash/home/events")
    fence_at = t.find("net return/vol 0.10")
    table_at = t.find("Delivery-confirmed top beats")
    assert fence_at > 0, "the PEAD falsification fence is missing"
    if table_at > 0:
        assert fence_at < table_at, "the PEAD fence must precede the results board, not follow it"


# ── 4. governance: route-gate registered + parity-ledgered, and the two agree ───────────
def test_routes_are_route_gate_registered():
    from tests import test_dash_route_registry as gate
    for path in ROUTES:
        assert path in gate.INTERNAL_DEV, path
        owner, rationale = gate.INTERNAL_DEV[path]
        assert owner == "graphite-home" and len(rationale) > 40, path


LANE_SURFACES = {
    "market-internals": "/dash/home/internals", "divergence": "/dash/home/internals",
    "participants": "/dash/home/flows", "fno": "/dash/home/flows",
    "actions": "/dash/home/events", "results-reactions": "/dash/home/events",
    "event-cadence": "/dash/home/events", "buyback-calc": "/dash/home/events",
    "surveillance": "/dash/home/events", "band-locks": "/dash/home/events",
    "attention": "/dash/home/attention",
}


def test_parity_ledger_points_every_one_of_the_eleven_at_its_live_route():
    """The ledger claim and the running app must agree: every one of the eleven surfaces this lane
    consolidated resolves to one of the four routes that actually serve.

    2026-07-28: nine of the eleven were downgraded PORTED -> DEFERRED by the gap audit (they hold
    open MAJOR rows — `docs/graphite-gap-register.md` §10). A DEFERRED target is a MILESTONE, so
    the route would be lost if the note did not carry it: this gate now requires that a downgraded
    surface still names where it LANDED, which is what keeps the board navigable while it is honest.
    """
    from src.web import sideways_parity as SP
    for key, route in LANE_SURFACES.items():
        st, tgt, note = SP.SURFACE_PARITY[key]
        assert st in ("PORTED", "DEFERRED"), (key, st)
        assert len(note) > 60, (key, "the note must say what travelled AND what did not")
        if st == "PORTED":
            assert tgt == route, (key, tgt, route)
        else:
            assert tgt in SP.MILESTONES, (key, "DEFERRED needs a real milestone", tgt)
            assert ("LANDED at " + route) in note, (
                key, "a downgraded surface must still name the route it landed at")


def test_parity_notes_disclose_what_did_not_travel():
    """Three of the eleven landed with a deliberate omission. The ledger must SAY so — an honest
    PORTED names its gaps rather than implying byte parity."""
    from src.web import sideways_parity as SP
    for key in ("market-internals", "results-reactions", "attention"):
        assert "NOT carried" in SP.SURFACE_PARITY[key][2], (key, "omission not disclosed")


# ── 5. link conventions ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", ROUTES)
def test_symbol_links_use_the_sym_key_and_the_graphite_stock_page(client, path):
    t = _text(client, path)
    assert "?symbol=" not in t, (path, "use ?sym=, never ?symbol=")
    from src.web.home import internals_pages as P
    assert '/dash/home/stock?sym=' in P._sym("TCS")


# ── 6. the read layer degrades honestly on an empty DB ─────────────────────────────────
def test_reads_degrade_to_empty_on_a_schema_less_db():
    """Every read is bounded + defensive: a missing table returns an empty result, never an
    exception (a busy or edge DB must never 500 a page)."""
    from src.web.home import internals_reads as R
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    assert R.internals_pack(conn) == {}
    assert R.internals_drill(conn, "2026-01-01") == {}
    assert R.rs_divergence(conn)["bull"] == []
    assert R.participants_pack(conn) == {}
    assert R.fno_board(conn) == {}
    assert R.ca_calendar(conn)["rows"] == []
    assert R.ca_recent(conn) == []
    assert R.buyback_rows(conn) == []
    assert R.event_cadence(conn) == {}
    assert R.surveillance_tape(conn) == {}
    assert R.band_locks(conn) == {}
    assert R.attention_queue(conn) == {}
    assert R.alert_rail(conn) == {}


def test_percentiles_refuse_to_fabricate_on_thin_history():
    """The reference layer's whole claim is honesty: below the minimum sample there is NO
    percentile, rather than a made-up one."""
    from src.web.home import internals_reads as R
    assert R._pctile([1, 2, 3], 2) is None                     # far below the 250-point floor
    assert R._ref([1, 2, 3], 2) == {}
    assert R._pctile(list(range(300)), 150) is not None
    assert R._pctile(list(range(100)), 50, minpts=60) is not None
    assert R._pctile(list(range(50)), 25, minpts=60) is None


def test_fno_reality_checks_are_named_examples_not_rankings():
    """The auto callouts must each name ONE example off the data — never emit a ranked list."""
    from src.web.home import internals_reads as R
    rows = [{"sym": "AAA", "quadrant": "SHORT_COVER", "oi_pct": 91.0, "streak": 3, "pcr_pct": 40.0},
            {"sym": "BBB", "quadrant": "SHORT_COVER", "oi_pct": 74.0, "streak": 1, "pcr_pct": 50.0},
            {"sym": "CCC", "quadrant": "SHORT_BUILDUP", "oi_pct": 88.0, "streak": 4, "pcr_pct": 60.0},
            {"sym": "DDD", "quadrant": "LONG_BUILDUP", "oi_pct": 11.0, "streak": 2, "pcr_pct": 97.0}]
    flags = R.fno_flags(rows)
    kinds = [f["kind"] for f in flags]
    assert len(kinds) == len(set(kinds)), "one callout per kind — never a leaderboard"
    hollow = next(f for f in flags if f["kind"] == "Hollow short-cover")
    assert hollow["sym"] == "AAA", "the callout must name the most extreme example"


def test_participant_stance_word_tracks_the_computed_ratio():
    """Codex D8-F3, carried forward: the plain-English read must follow the number, never a
    hard-coded sentence that printed 'bearish' on a mid-range or net-long book."""
    from src.web.home import internals_reads as R
    assert R.participant_stance_word(0.4) == "strongly net-short"
    assert R.participant_stance_word(0.8) == "leaning net-short"
    assert R.participant_stance_word(1.0) == "balanced"
    assert R.participant_stance_word(1.4) == "leaning net-long"
    assert R.participant_stance_word(2.0) == "strongly net-long"
    assert R.participant_stance_word(None) == "unavailable"


# ── URL state ──────────────────────────────────────────────────────────────────────────
def test_view_state_lives_in_the_url(client):
    """Every view is addressable + shareable: window/sort/lens/event filters are query params the
    server renders, not client-only toggles."""
    for path, qs in (("/dash/home/internals", "?window=3y"), ("/dash/home/flows", "?sort=pcr_pct"),
                     ("/dash/home/events", "?window=60"), ("/dash/home/events", "?evt=DIVIDEND")):
        t = _text(client, path + qs)
        assert 'aria-current="true"' in t, (path, qs, "no segment marks itself active")
        assert qs.split("=")[1] in t, (path, qs, "the active value is not echoed in a link")
    for bad in ("?window=zzz", "?sort=../../etc", "?evt=%27", "?lens=drop"):
        for path in ROUTES:
            r = client.get(path + bad)
            assert r.status_code == 200, (path, bad, r.status_code)
