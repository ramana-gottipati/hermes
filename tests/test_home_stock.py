"""test_home_stock.py — the Graphite STOCK page (`/dash/home/stock`), the cutover-blocking unit.

Proves the per-symbol evidence scroll renders from data, keeps FREE complete while the reference
layer stays PRO-gated, degrades honestly on a thin/unknown symbol (never raises, never fabricates),
escapes untrusted symbols (DOM-safety), and — the load-bearing one — that the split/bonus
CORPORATE-ACTION ADJUSTMENT is actually applied to the price/momentum self-percentiles (raw NSE
close is unadjusted; a 1:1 bonus would otherwise fake a −50% crash).
"""
from __future__ import annotations

import sqlite3

import pytest

from src.web.home import reads
from src.web.home import stock_view as SV


# ── an in-memory NSE-shaped fixture (300 sessions, one 1:1 bonus half-way) ────────────────────
def _db(with_bonus: bool = True):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE bhavcopy_rows (symbol TEXT, series TEXT, trade_date TEXT, close REAL,"
                 " prev_close REAL, open REAL, high REAL, low REAL, value REAL, deliv_per REAL)")
    conn.execute("CREATE TABLE corporate_actions (symbol TEXT, action_type TEXT, ex_date TEXT,"
                 " ratio_from REAL, ratio_to REAL, details TEXT)")
    conn.execute("CREATE TABLE stock_signals (symbol TEXT, trade_date TEXT, primary_sector TEXT,"
                 " rs_rank INTEGER, rs_phase TEXT, rs_vs_broad_trend_state TEXT, rs_vs_broad_today REAL,"
                 " rs_vs_sector_today REAL, rsi_of_rs REAL, power_dvpt_3m REAL, avg_deliv_pct_1m REAL,"
                 " avg_deliv_pct_6m REAL, accum_character TEXT, deliv_updown_ratio_3m REAL,"
                 " pct_from_52w_high REAL, key_price_p3m REAL, gap_to_key_p3m REAL,"
                 " turnover_surge_1m REAL)")
    # 300 sessions. Pre-bonus the raw close trades ~2000; on the ex-date it halves to ~1000 — the
    # classic unadjusted "crash" that the adjustment must undo.
    rows = []
    for i in range(300):
        d = "2025-%02d-%02d" % (1 + i // 28, 1 + i % 28)
        raw = 2000.0 + i if (with_bonus and i < 150) else (1000.0 + i * 0.5)
        rows.append((("TESTCO"), "EQ", d, raw, raw - 1, raw, raw * 1.01, raw * 0.99,
                     1e8 + i * 1e5, 40.0 + (i % 20)))
    conn.executemany("INSERT INTO bhavcopy_rows VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    if with_bonus:
        conn.execute("INSERT INTO corporate_actions VALUES ('TESTCO','BONUS','2025-06-15',1.0,1.0,'1:1')")
    conn.execute("INSERT INTO stock_signals (symbol, trade_date, primary_sector, rs_rank, rs_phase,"
                 " rs_vs_broad_trend_state, rs_vs_broad_today, rsi_of_rs, power_dvpt_3m,"
                 " avg_deliv_pct_1m, avg_deliv_pct_6m, accum_character, deliv_updown_ratio_3m,"
                 " pct_from_52w_high, key_price_p3m, gap_to_key_p3m, turnover_surge_1m)"
                 " VALUES ('TESTCO', ?, 'Nifty IT', 42, 'RECOVERY', 'UPTREND', 0.8, 61.0, 5.1e7,"
                 " 46.0, 52.0, 'NEUTRAL', 1.2, -12.5, 1180.0, 2.4, 1.8)", (rows[-1][2],))
    conn.commit()
    return conn


def test_core_series_and_events_read_from_data():
    conn = _db()
    core = reads.stock_core(conn, "TESTCO")
    assert core["symbol"] == "TESTCO" and core["close"] and core["signals"]
    assert core["signals"]["rs_rank"] == 42
    ser = reads.stock_series(conn, "TESTCO", 120)
    assert len(ser["close"]) == 120 and len(ser["deliv"]) == 120
    ev = reads.stock_events(conn, "TESTCO")
    assert any((r.get("action_type") == "BONUS") for r in ev["ca"])


def test_corporate_action_adjustment_is_applied_to_self_percentiles():
    """THE load-bearing one. Raw close halves at the 1:1 bonus; unadjusted, today's price would rank
    near the BOTTOM of its own history. Adjusted, the pre-bonus prints are rebased down, so today
    ranks near the TOP — the same hazard the /dash/self-history lane proved on Nestlé/Trent."""
    ref = reads.stock_selfref(_db(with_bonus=True), "TESTCO")
    assert ref["adjusted"] is True
    assert ref["price"]["pctile"] > 70, (
        "price percentile must be computed on a split/bonus-ADJUSTED close — got "
        f"{ref['price']['pctile']} (an unadjusted series would rank today near the bottom)")
    flat = reads.stock_selfref(_db(with_bonus=False), "TESTCO")
    assert flat["adjusted"] is False and flat["price"]["pctile"] > 70   # steadily rising, unadjusted


def test_selfref_covers_the_five_metrics_and_feeds_the_reference_chip():
    ref = reads.stock_selfref(_db(), "TESTCO")
    for k in ("price", "mom", "deliv", "turn", "coil"):
        assert k in ref, f"missing self-relative metric {k}"
        assert set(("today", "pctile", "typical", "n")) <= set(ref[k]), f"{k} must feed ref_chip"
        assert 0.0 <= ref[k]["pctile"] <= 100.0


def test_selfref_is_empty_when_history_is_thin_never_fabricated():
    conn = _db()
    conn.execute("DELETE FROM bhavcopy_rows WHERE trade_date > '2025-02-01'")
    conn.commit()
    assert reads.stock_selfref(conn, "TESTCO") == {}        # honest empty, not a fake percentile


def test_page_renders_all_zones_from_real_data():
    conn = _db()
    core = reads.stock_core(conn, "TESTCO")
    html = SV.stock_page(core, reads.stock_series(conn, "TESTCO"),
                         reads.stock_selfref(conn, "TESTCO"), reads.stock_events(conn, "TESTCO"), "TESTCO")
    for zone in ("Price &amp; delivery", "Versus its own history", "Delivery &amp; accumulation",
                 "Relative strength", "Positioning &amp; key zones", "Corporate actions"):
        assert zone in html, f"missing zone {zone}"
    assert "g-sc-line" in html and "g-sc-dv" in html          # chart: price line + delivery band
    assert "RECOVERY".title() in html and "#42" in html       # nightly signals surfaced
    assert "Full classic view" in html                        # the escape hatch to classic
    assert "+ Add to watchlist" in html                       # reuses the home-owned write


def test_free_is_complete_and_the_reference_layer_is_pro_gated():
    conn = _db()
    core = reads.stock_core(conn, "TESTCO")
    html = SV.stock_page(core, reads.stock_series(conn, "TESTCO"),
                         reads.stock_selfref(conn, "TESTCO"), reads.stock_events(conn, "TESTCO"), "TESTCO")
    # every Free number is present un-gated (the page is never crippled)
    for row in ("Price", "Momentum", "Delivery", "Turnover", "Coil"):
        assert row in html
    assert "g-sr-v" in html                                   # the Free values render
    # ...and every reference chip carries the Pro class (hidden in Free by the tier CSS)
    assert html.count("g-refchip") >= 5
    assert "g-refchip pro-more" in html, "reference chips must be Pro-gated"


def test_unknown_symbol_is_honest_and_never_raises():
    html = SV.stock_page({}, {}, {}, {}, "NOTAREALSYMBOL")
    assert "No such symbol" in html and "g-empty" in html
    assert SV.stock_page({}, {}, {}, {}, "") .count("Enter a symbol") == 1


@pytest.mark.parametrize("bad", ['<script>alert(1)</script>', '" onerror="x', "' OR 1=1--"])
def test_untrusted_symbol_is_escaped_everywhere(bad):
    conn = _db()
    assert reads.stock_core(conn, bad) == {}                  # cleaned to nothing / no match
    html = SV.stock_page({}, {}, {}, {}, bad)
    assert "<script>" not in html and 'onerror="' not in html


def test_page_carries_no_preview_or_legacy_marker():
    conn = _db()
    core = reads.stock_core(conn, "TESTCO")
    html = SV.stock_page(core, reads.stock_series(conn, "TESTCO"),
                         reads.stock_selfref(conn, "TESTCO"), reads.stock_events(conn, "TESTCO"), "TESTCO")
    for marker in ("pv3-", 'data-ui-v3', "uk-sub", 'id="uk-main"'):
        assert marker not in html, f"leaked a preview/legacy marker: {marker}"


def test_graphite_symbol_links_point_at_the_graphite_stock_page():
    """Cutover-readiness: a symbol click inside Graphite must NOT eject the user into classic chrome."""
    from src.web.home import components as C
    assert '/dash/home/stock?sym=' in C.sym_link("TCS")
    assert 'href="/dash/stock?sym=' not in C.sym_link("TCS")
