"""test_home_stock.py — the per-symbol READ layer + the blocks folded onto the Graphite stock page.

W1-CONVERGENCE (2026-07-27): two lineages independently built `/dash/home/stock`. The surviving page
is `stock_page.py`; the retired `stock_view.py` is in git history at `815c941`. This gate survives the
retirement because most of it never tested that view — it tests `reads.py`'s per-symbol half, which is
still LIVE (the folded own-history panel and the ownership-disclosures block call it). The render
assertions are retargeted at the surviving page, so the folds are pinned to the surface, not merely to
the read that feeds them.

The load-bearing one remains `test_corporate_action_adjustment_is_applied_to_self_percentiles`: raw NSE
close is unadjusted, so a 1:1 bonus would otherwise fake a −50% crash and invert the price percentile.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.web.home import reads
from src.web.home import stock_page as SP


# ── an in-memory NSE-shaped fixture (300 sessions, one 1:1 bonus half-way) ────────────────────
def _db(with_bonus: bool = True):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE bhavcopy_rows (symbol TEXT, series TEXT, trade_date TEXT, close REAL,"
                 " prev_close REAL, open REAL, high REAL, low REAL, value REAL, deliv_per REAL,"
                 " volume REAL, deliv_qty REAL, segment TEXT)")
    conn.execute("CREATE TABLE corporate_actions (symbol TEXT, action_type TEXT, ex_date TEXT,"
                 " ratio_from REAL, ratio_to REAL, details TEXT)")
    conn.execute("CREATE TABLE stock_signals (symbol TEXT, trade_date TEXT, primary_sector TEXT,"
                 " rs_rank INTEGER, rs_phase TEXT, rs_vs_broad_trend_state TEXT, rs_vs_broad_today REAL,"
                 " rs_vs_sector_today REAL, rsi_of_rs REAL, power_dvpt_3m REAL, avg_deliv_pct_1m REAL,"
                 " avg_deliv_pct_6m REAL, accum_character TEXT, deliv_updown_ratio_3m REAL,"
                 " pct_from_52w_high REAL, key_price_p3m REAL, gap_to_key_p3m REAL,"
                 " turnover_surge_1m REAL, delivery_value_per_trade REAL, ratio_today_vs_power_1m REAL,"
                 " p_score INTEGER, r_score INTEGER, trigger_rank TEXT, avg_close_p3m REAL)")
    # 300 sessions. Pre-bonus the raw close trades ~2000; on the ex-date it halves to ~1000 — the
    # classic unadjusted "crash" that the adjustment must undo.
    rows = []
    for i in range(300):
        d = "2025-%02d-%02d" % (1 + i // 28, 1 + i % 28)
        raw = 2000.0 + i if (with_bonus and i < 150) else (1000.0 + i * 0.5)
        rows.append((("TESTCO"), "EQ", d, raw, raw - 1, raw, raw * 1.01, raw * 0.99,
                     1e8 + i * 1e5, 40.0 + (i % 20), 1e5, 4e4, "CM"))
    conn.executemany("INSERT INTO bhavcopy_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    if with_bonus:
        conn.execute("INSERT INTO corporate_actions VALUES ('TESTCO','BONUS','2025-06-15',1.0,1.0,'1:1')")
    conn.execute("INSERT INTO stock_signals (symbol, trade_date, primary_sector, rs_rank, rs_phase,"
                 " rs_vs_broad_trend_state, rs_vs_broad_today, rsi_of_rs, power_dvpt_3m,"
                 " avg_deliv_pct_1m, avg_deliv_pct_6m, accum_character, deliv_updown_ratio_3m,"
                 " pct_from_52w_high, key_price_p3m, gap_to_key_p3m, turnover_surge_1m,"
                 " delivery_value_per_trade, ratio_today_vs_power_1m, p_score, r_score, trigger_rank,"
                 " avg_close_p3m)"
                 " VALUES ('TESTCO', ?, 'Nifty IT', 42, 'RECOVERY', 'UPTREND', 0.8, 61.0, 5.1e7,"
                 " 46.0, 52.0, 'NEUTRAL', 1.2, -12.5, 1180.0, 2.4, 1.8, 4.2e5, 1.3, 4, 3, 'S',"
                 " 1150.0)", (rows[-1][2],))
    conn.commit()
    return conn


def _render(conn, sym="TESTCO"):
    body, rail = SP.compose(conn, sym)
    return body + rail


# ── the read layer (unchanged by the convergence; it feeds the folded blocks) ─────────────────
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


# ── the folded blocks, pinned on the SURFACE of the surviving page ───────────────────────────
def test_folded_own_history_panel_renders_its_five_metrics_pro_gated():
    """W1-CONVERGENCE fold #1. Free is complete — every value renders un-gated; the reference chips
    that qualify them carry the Pro class. Both halves are asserted, because a page that hides the
    NUMBER behind the tier is crippled, and one that hides nothing has no premium left to sell."""
    html = _render(_db())
    assert 'data-sec="own"' in html, "the own-history section must be composed into the scroll"
    for row in ("Price", "Momentum", "Delivery", "Turnover", "Coil"):
        assert row in html, f"missing own-history row {row}"
    assert "g-sr-v" in html                                   # the Free values render
    assert html.count("g-refchip") >= 5
    assert "g-refchip pro-more" in html, "reference chips must be Pro-gated"
    assert "split/bonus adjusted" in html, "the CA-adjustment must be DISCLOSED on the surface"


def test_folded_own_history_panel_never_prints_a_non_finite_value():
    """The retired lineage's formatter printed a literal "nan" under a percentile label. The fold
    routes every value through `_finite`, so a non-finite reads as an em dash instead."""
    assert SP._self_value("price", {"today": float("nan")}) == "—"
    assert SP._self_value("mom", {"today": float("inf")}) == "—"
    assert SP._self_value("turn", {"today": None}) == "—"
    assert SP._self_value("price", {"today": 1234.5}) == "₹1,234.50"


def test_folded_disclosures_block_renders_sebi_filings_and_actions():
    """W1-CONVERGENCE fold #2 — the only block the retired lineage served that had NO counterpart on
    the surviving page. `insider_events` / `sast_pledge_events` / `sast_reg29_events` are SEBI
    primary-source disclosures (Guardrail #8), so losing them in the merge would have been a real
    regression, not a cosmetic one."""
    conn = _db()
    conn.execute("CREATE TABLE insider_events (symbol TEXT, disclosure_dt TEXT, txn_class TEXT,"
                 " signal_class TEXT, promoter_group_flag INTEGER)")
    conn.execute("INSERT INTO insider_events VALUES ('TESTCO','2025-06-02','BUY','ACQ',1)")
    conn.execute("CREATE TABLE sast_pledge_events (symbol TEXT, broadcast_dt TEXT, event_type TEXT,"
                 " event_pct REAL)")
    conn.execute("INSERT INTO sast_pledge_events VALUES ('TESTCO','2025-06-03','RELEASE',2.5)")
    conn.commit()
    html = _render(conn)
    assert 'data-sec="disc"' in html, "the disclosures section must be composed into the scroll"
    assert "g-filings" in html and "g-fl-when" in html
    assert "2025-06-0" in html, "a dated filing row must reach the surface"
    assert "Bonus" in html, "the recorded corporate action must render alongside the filings"


def test_folded_watchlist_write_and_classic_escape_hatch_are_on_the_header():
    """W1-CONVERGENCE fold #3. Both affordances came off the retired header; the POST route is
    home-owned already, so they move rather than being lost."""
    html = _render(_db())
    assert "+ Add to watchlist" in html
    assert 'action="/dash/home/watch/add"' in html
    assert "Full classic view" in html


def test_folded_classic_link_url_quotes_an_ampersand_symbol():
    """The retired lineage HTML-ESCAPED the symbol into this href, so `M&M` rendered `?sym=M&amp;M`,
    which a browser decodes to `sym=M` — the escape hatch silently opened the WRONG stock. `&` is
    legal in NSE tickers (M&M, M&MFIN, J&KBANK). Reproduced against the retired code before the fold;
    pinned here so the fold can never reintroduce it."""
    import html as H
    import re
    import urllib.parse as U
    core = {"sym": "M&M", "sig": None, "bar": None, "prev": None, "name": "", "themes": []}
    href = re.search(r'href="(/dash/stock[^"]*)"', SP.identity(core, {})).group(1)
    params = U.parse_qs(U.urlsplit(H.unescape(href)).query)
    assert params.get("sym") == ["M&M"], (href, params)


# ── honesty / safety, retargeted at the surviving page ───────────────────────────────────────
def test_unknown_symbol_is_honest_and_never_raises():
    body, rail = SP.compose(_db(), "NOTAREALSYMBOL")
    assert "Symbol not found" in body and rail == ""
    assert "g-sform" in body, "a miss must still offer the recovery affordance, never a dead end"


@pytest.mark.parametrize("bad", ['<script>alert(1)</script>', '" onerror="x', "' OR 1=1--"])
def test_untrusted_symbol_is_escaped_everywhere(bad):
    conn = _db()
    assert reads.stock_core(conn, bad) == {}                  # cleaned to nothing / no match
    body, _rail = SP.compose(conn, bad)
    assert "<script>" not in body and 'onerror="' not in body


def test_page_carries_no_preview_or_legacy_marker():
    html = _render(_db())
    for marker in ("pv3-", 'data-ui-v3', "uk-sub", 'id="uk-main"'):
        assert marker not in html, f"leaked a preview/legacy marker: {marker}"


def test_graphite_symbol_links_point_at_the_graphite_stock_page():
    """Cutover-readiness: a symbol click inside Graphite must NOT eject the user into classic chrome."""
    from src.web.home import components as C
    assert '/dash/home/stock?sym=' in C.sym_link("TCS")
    assert 'href="/dash/stock?sym=' not in C.sym_link("TCS")


def test_exactly_one_route_registration_survives_the_convergence():
    """Both lineages registered `/dash/home/stock`. A dict literal with a duplicate key is legal
    Python — the later entry silently wins — so a merge could leave a registry that LOOKS reviewed
    while half of it is unreachable. Count the source lines, not the parsed dict."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "tests" / "test_dash_route_registry.py").read_text(
        encoding="utf-8")
    assert src.count('"/dash/home/stock":') == 1, "exactly one INTERNAL_DEV entry for the stock route"


def test_the_retired_lineage_is_gone_and_unreferenced():
    """No rival route may survive the convergence. `stock_view.py` is retired to git history; nothing
    in the home package may import or mount it again."""
    import re
    from pathlib import Path
    home = Path(__file__).resolve().parents[1] / "src" / "web" / "home"
    assert not (home / "stock_view.py").exists(), "the retired module must not be re-added"
    for py in home.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        assert not re.search(r"^\s*(from|import)\s+[\w.]*\bstock_view\b", text, re.M), py.name
