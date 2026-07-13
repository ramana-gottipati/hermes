"""Alert-rail (4th bus face) regressions — tested against the LIVE token vocabularies.

An adversarial review caught that the first cut's tests fed fabricated state tokens
(SUPPORT/RESIST) that exist nowhere in production, masking a dead rs lens. These tests
use the REAL stored vocabularies verified on prod:
  • mep  : STRONG_DISTRIB / DISTRIB / NEUTRAL / ACCUM / STRONG_ACCUM   (signal_events)
  • rs   : INSIDE / TOUCH_SUP / TOUCH_RES  (+ BREAKDOWN_DN/BREAKOUT_UP headroom)
  • oi   : LONG_BUILDUP / SHORT_BUILDUP / LONG_UNWIND / SHORT_COVER / FLAT
  • cci  : numeric level strings (e.g. "55" → "30")

They pin: the ordinal from→to logic (STRONG_ACCUM→ACCUM is *weakening*, not opportunity),
the numeric-delta cci path (robust to NULL-level trend flips), the no-critical-tier deal
rule, edge-triggered/idempotent promotion, the per-(batch,lens) cap, and priority (not raw
magnitude) ranking under truncation.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.automation import signal_events as se
from src.automation import signal_alerts as sa


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    se.ensure_schema(c)
    sa.ensure_schema(c)
    yield c
    c.close()


def _emit(c, symbol, lens, et, as_of, *, direction=None, to_state=None, magnitude=None,
          from_state=None, note=""):
    c.execute(
        "INSERT OR IGNORE INTO signal_events "
        "(symbol, lens, event_type, direction, from_state, to_state, magnitude, as_of, note) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (symbol, lens, et, direction, from_state, to_state, magnitude, as_of, note))
    c.commit()


# --- classify: the ordinal band logic (mep + rs) ---------------------------

def test_classify_mep_ordinal_direction_not_destination():
    # Strengthening INTO a regime alerts; easing / →neutral / hysteresis wobbles do NOT.
    assert sa.classify("mep", "phase_flip", "flip", "ACCUM", 1.0, "NEUTRAL") == ("high", "opportunity")
    assert sa.classify("mep", "phase_flip", "flip", "STRONG_ACCUM", 1.0, "ACCUM") == ("high", "opportunity")
    assert sa.classify("mep", "phase_flip", "flip", "DISTRIB", 1.0, "NEUTRAL") == ("high", "risk")
    assert sa.classify("mep", "phase_flip", "flip", "STRONG_DISTRIB", 1.0, "DISTRIB") == ("critical", "risk")
    # the review's bug: destination contains ACCUM/DISTRIB but the move WEAKENS → NOT promoted
    assert sa.classify("mep", "phase_flip", "flip", "ACCUM", 1.0, "STRONG_ACCUM") == (None, None)
    assert sa.classify("mep", "phase_flip", "flip", "DISTRIB", 1.0, "STRONG_DISTRIB") == (None, None)
    # returns to neutral are not alerts
    assert sa.classify("mep", "phase_flip", "flip", "NEUTRAL", 1.0, "ACCUM") == (None, None)


def test_classify_rs_uses_real_band_tokens():
    # The dead-lens regression: real tokens are INSIDE/TOUCH_SUP/TOUCH_RES, never SUPPORT/RESIST.
    assert sa.classify("rs", "phase_flip", "flip", "TOUCH_RES", 1.0, "INSIDE") == ("high", "opportunity")
    assert sa.classify("rs", "phase_flip", "flip", "TOUCH_SUP", 1.0, "INSIDE") == ("high", "risk")
    assert sa.classify("rs", "phase_flip", "flip", "TOUCH_RES", 1.0, "TOUCH_SUP") == ("high", "opportunity")
    assert sa.classify("rs", "phase_flip", "flip", "INSIDE", 1.0, "TOUCH_RES") == (None, None)  # easing
    # the fabricated tokens the old test used must NOT accidentally match anything
    assert sa.classify("rs", "phase_flip", "flip", "SUPPORT", 1.0, "INSIDE") == (None, None)


def test_classify_oi_quadrants():
    assert sa.classify("oi", "oi_flip", "flip", "LONG_BUILDUP", 1.0, "SHORT_BUILDUP") == ("high", "opportunity")
    assert sa.classify("oi", "oi_flip", "flip", "SHORT_COVER", 1.0, "LONG_UNWIND") == ("high", "opportunity")
    assert sa.classify("oi", "oi_flip", "flip", "SHORT_BUILDUP", 1.0, "FLAT") == ("high", "risk")
    assert sa.classify("oi", "oi_flip", "flip", "LONG_UNWIND", 1.0, "SHORT_COVER") == ("high", "risk")
    assert sa.classify("oi", "oi_flip", "flip", "FLAT", 1.0, "LONG_BUILDUP") == (None, None)


def test_classify_cci_numeric_delta_and_trend_fallback():
    # keyed on the numeric level delta, NOT the bus 'direction' (robust to NULL-level flips)
    assert sa.classify("cci", "credibility_step", "down", "30", 0.5, "55") == ("critical", "risk")  # −25
    assert sa.classify("cci", "credibility_step", "down", "48", 0.14, "55") == ("high", "risk")     # −7
    assert sa.classify("cci", "credibility_step", "up", "80", 0.5, "55") == ("high", "opportunity")  # +25
    assert sa.classify("cci", "credibility_step", "up", "58", 0.06, "55") == (None, None)            # +3, noise
    # pure trend-token flip (levels NULL): read the word, don't trust direction='down'
    assert sa.classify("cci", "credibility_step", "down", "IMPROVING", 1.0, None) == ("high", "opportunity")
    assert sa.classify("cci", "credibility_step", "down", "DETERIORATING", 1.0, None) == ("high", "risk")


def test_classify_deal_has_no_critical_tier():
    # bus magnitude is a within-day percentile → the day's top print is always 1.0; a critical
    # tier would fire on every quiet single-deal day, so deals are always 'high'.
    assert sa.classify("deal", "deal_print", "up", "2 prints", 0.99) == ("high", "opportunity")
    assert sa.classify("deal", "deal_print", "up", "1 print", 0.92) == ("high", "opportunity")
    assert sa.classify("deal", "deal_print", "down", "1 print", 0.95) == ("high", "risk")
    assert sa.classify("deal", "deal_print", "up", "1 print", 0.80) == (None, None)          # below the 0.90 gate


def test_classify_unknown_is_never_promoted():
    assert sa.classify("dvpt", "percentile_breach", "up", "95", 1.0, "10") == (None, None)
    assert sa.classify("oi", "oi_flip", "flip", "FLAT", 1.0, "LONG_BUILDUP") == (None, None)


# --- promote (edge-triggered, capped) --------------------------------------

def test_promote_selects_only_alert_worthy(conn):
    _emit(conn, "BIGDEAL", "deal", "deal_print", "2026-07-10", direction="up",
          to_state="₹60cr", magnitude=0.99, note="BIGDEAL: big print")
    _emit(conn, "SMALLDEAL", "deal", "deal_print", "2026-07-10", direction="down",
          to_state="₹0.1cr", magnitude=0.20, note="SMALLDEAL: tiny")            # below bar
    _emit(conn, "DISTCO", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)              # into distribution
    _emit(conn, "EASECO", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="STRONG_DISTRIB", to_state="DISTRIB", magnitude=1.0)       # easing → skipped
    out = sa.promote(conn, as_of="2026-07-10")
    assert out["promoted"] == 2                         # BIGDEAL + DISTCO (both high); not the tiny/easing
    assert out["by_severity"].get("high") == 2
    assert "critical" not in out["by_severity"]
    assert {a["symbol"] for a in sa.active_alerts(conn)} == {"BIGDEAL", "DISTCO"}


def test_promote_is_idempotent(conn):
    _emit(conn, "DISTCO", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    assert sa.promote(conn, as_of="2026-07-10")["promoted"] == 1
    assert sa.promote(conn, as_of="2026-07-10")["promoted"] == 0   # fire-once


def test_promote_caps_per_lens(conn):
    for i in range(20):
        _emit(conn, f"MEP{i}", "mep", "phase_flip", "2026-07-10", direction="flip",
              from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    out = sa.promote(conn, as_of="2026-07-10")
    assert out["promoted"] == sa._PER_LENS_CAP
    assert len(sa.active_alerts(conn, limit=100)) == sa._PER_LENS_CAP


# --- active_alerts (the rail read) -----------------------------------------

def test_active_alerts_windows_and_ranks(conn):
    _emit(conn, "OLDCO", "mep", "phase_flip", "2026-06-01", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)             # >7d before anchor
    _emit(conn, "NEWHIGH", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)            # high
    _emit(conn, "NEWCRIT", "cci", "credibility_step", "2026-07-10", direction="down",
          from_state="55", to_state="25", magnitude=0.6)                       # critical (−30)
    sa.promote(conn, as_of="2026-06-01")
    sa.promote(conn, as_of="2026-07-10")
    rail = sa.active_alerts(conn, within_days=7)
    assert [a["symbol"] for a in rail] == ["NEWCRIT", "NEWHIGH"]   # OLDCO windowed out; critical first
    assert sa.active_count(conn, within_days=7)["total"] == 2
    assert sa.active_count(conn, within_days=7)["by_severity"].get("critical") == 1


def test_active_alerts_ranks_by_priority_not_raw_magnitude(conn):
    # 3 mep flips (mag 1.0 → priority 0.70) + 1 deal (mag 0.90 → priority 0.90). A naive
    # `ORDER BY magnitude LIMIT n` would keep the 3 mep and drop the higher-PRIORITY deal.
    for i in range(3):
        _emit(conn, f"MEP{i}", "mep", "phase_flip", "2026-07-10", direction="flip",
              from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    _emit(conn, "TOPDEAL", "deal", "deal_print", "2026-07-10", direction="up",
          to_state="₹90cr", magnitude=0.90)
    sa.promote(conn, as_of="2026-07-10")
    top2 = sa.active_alerts(conn, limit=2)
    assert top2[0]["symbol"] == "TOPDEAL"                       # highest priority leads
    assert "TOPDEAL" in {a["symbol"] for a in top2}             # never evicted by the mep flood


def test_active_alerts_limit(conn):
    for i in range(6):
        _emit(conn, f"MEP{i}", "mep", "phase_flip", "2026-07-10", direction="flip",
              from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    sa.promote(conn, as_of="2026-07-10")
    assert len(sa.active_alerts(conn, limit=3)) == 3


def test_window_is_exactly_n_days_inclusive(conn):
    # within_days=7 spans the anchor + 6 prior dates (7 dates), not 8.
    _emit(conn, "IN", "mep", "phase_flip", "2026-07-04", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)             # anchor-6 → in
    _emit(conn, "OUT", "mep", "phase_flip", "2026-07-03", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)            # anchor-7 → out
    _emit(conn, "ANCHOR", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    for d in ("2026-07-03", "2026-07-04", "2026-07-10"):
        sa.promote(conn, as_of=d)
    syms = {a["symbol"] for a in sa.active_alerts(conn, within_days=7, as_of="2026-07-10")}
    assert "IN" in syms and "ANCHOR" in syms and "OUT" not in syms


def test_promote_empty_bus_is_safe(conn):
    out = sa.promote(conn)
    assert out["promoted"] == 0 and out["batch"] is None
    assert sa.active_alerts(conn) == []
    assert sa.active_count(conn) == {"total": 0, "by_severity": {}, "by_valence": {}}


def test_active_alerts_filter_by_severity_and_valence(conn):
    _emit(conn, "CRIT", "cci", "credibility_step", "2026-07-10", direction="down",
          from_state="55", to_state="25", magnitude=0.6)                # critical, risk
    _emit(conn, "RISKHI", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)      # high, risk
    _emit(conn, "OPPHI", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="ACCUM", magnitude=1.0)        # high, opportunity
    sa.promote(conn, as_of="2026-07-10")
    all_syms = {a["symbol"] for a in sa.active_alerts(conn)}
    assert all_syms == {"CRIT", "RISKHI", "OPPHI"}
    assert {a["symbol"] for a in sa.active_alerts(conn, sev="critical")} == {"CRIT"}
    assert {a["symbol"] for a in sa.active_alerts(conn, sev="high")} == {"RISKHI", "OPPHI"}
    assert {a["symbol"] for a in sa.active_alerts(conn, val="risk")} == {"CRIT", "RISKHI"}
    assert {a["symbol"] for a in sa.active_alerts(conn, val="opportunity")} == {"OPPHI"}
    assert {a["symbol"] for a in sa.active_alerts(conn, sev="high", val="risk")} == {"RISKHI"}
    # active_count carries the UNFILTERED by-valence breakdown (for the chip counts)
    cnt = sa.active_count(conn)
    assert cnt["by_valence"] == {"risk": 2, "opportunity": 1}
    # a bogus filter value is ignored (not a crash / not an empty rail)
    assert {a["symbol"] for a in sa.active_alerts(conn, sev="bogus")} == all_syms


def test_acknowledge_removes_from_the_rail(conn):
    _emit(conn, "KEEP", "mep", "phase_flip", "2026-07-10", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    _emit(conn, "DROP", "deal", "deal_print", "2026-07-10", direction="up",
          to_state="₹99cr", magnitude=0.99)
    sa.promote(conn, as_of="2026-07-10")
    drop_id = next(a["id"] for a in sa.active_alerts(conn) if a["symbol"] == "DROP")
    assert sa.acknowledge(conn, drop_id) == 1
    assert sa.acknowledge(conn, drop_id) == 0                       # already dismissed → no-op
    syms = {a["symbol"] for a in sa.active_alerts(conn)}
    assert syms == {"KEEP"}                                          # DROP left the rail
    assert sa.active_count(conn)["total"] == 1                       # count excludes dismissed


def test_acknowledge_all_clears_the_window(conn):
    for i in range(4):
        _emit(conn, f"M{i}", "mep", "phase_flip", "2026-07-10", direction="flip",
              from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    _emit(conn, "OLD", "mep", "phase_flip", "2026-06-01", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)   # outside the window
    sa.promote(conn, as_of="2026-07-10")
    sa.promote(conn, as_of="2026-06-01")
    cleared = sa.acknowledge_all(conn, within_days=7, as_of="2026-07-10")
    assert cleared == 4                                              # only the in-window ones
    assert sa.active_alerts(conn, within_days=7, as_of="2026-07-10") == []
    # the out-of-window alert is untouched (a later window/replay still sees it)
    assert any(a["symbol"] == "OLD" for a in sa.active_alerts(conn, within_days=400, as_of="2026-07-10"))


def test_ack_migration_on_preexisting_table(conn):
    # a table created BEFORE the acknowledge feature must gain the column idempotently
    conn.execute("DROP TABLE signal_alert_state")
    conn.execute("CREATE TABLE signal_alert_state (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "symbol TEXT, lens TEXT, event_type TEXT, direction TEXT, from_state TEXT, "
                 "to_state TEXT, magnitude REAL, severity TEXT NOT NULL, valence TEXT, "
                 "as_of TEXT NOT NULL, note TEXT, event_id INTEGER, first_fired TEXT, "
                 "UNIQUE(symbol, lens, event_type, as_of))")
    conn.commit()
    sa.ensure_schema(conn)                                           # should ALTER-add acknowledged_at
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_alert_state)")}
    assert "acknowledged_at" in cols
    sa.ensure_schema(conn)                                           # second call is a no-op, not an error


def test_backfill_seeds_multiple_batches_idempotently(conn):
    _emit(conn, "A", "mep", "phase_flip", "2026-07-08", direction="flip",
          from_state="NEUTRAL", to_state="DISTRIB", magnitude=1.0)
    _emit(conn, "B", "mep", "phase_flip", "2026-07-09", direction="flip",
          from_state="NEUTRAL", to_state="ACCUM", magnitude=1.0)
    _emit(conn, "C", "deal", "deal_print", "2026-07-10", direction="up",
          to_state="₹99cr", magnitude=0.99)
    out = sa.backfill(conn, batches=5)
    assert out == {"batches": 3, "promoted": 3}
    assert sa.backfill(conn, batches=5)["promoted"] == 0     # edge-triggered / idempotent
