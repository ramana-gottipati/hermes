"""test_home_featured.py — the scroll-stack additions (featured card · pulse deck · ticker feeds).

Proves the new builders render from data, drop tiles when a feed is absent (never raise), escape
untrusted input (DOM-safety), mark demo-backed zones 'sample' (the real-vs-demo honesty line), and
leak no preview/legacy marker.
"""
from __future__ import annotations

from src.web.home import components as C


def test_pulse_deck_renders_internals_and_expands():
    internals = [{"pct_adv": p, "avg_dp": d, "mep_net": m, "disp": s}
                 for p, d, m, s in [(60, 54, 12, 2.10), (74, 56, 17, 2.26)]]
    html = C.pulse_deck(
        [{"index_name": "NIFTY 50", "close_value": 24218.4, "ret_1d_pct": 0.71}],
        {"word": "Constructive"}, 64, {"adv": 1758, "dec": 592},
        [24000, 24100, 24218], internals, {"highs": 84, "near": 213},
        [{"sector": "Nifty IT", "rs": 1.2}, {"sector": "Nifty Realty", "rs": -1.1}])
    assert "Breadth trend" in html and "Delivery conviction" in html and "Accumulation tape" in html
    assert "New 52-wk highs" in html and "84" in html and "Dispersion" in html
    assert "g-gauge" in html and 'data-value="64"' in html          # the mood gauge
    assert "g-deck" in html and 'class="g-expand"' in html          # deck + expandable trend panels
    assert "Sector heat" in html and ">IT<" in html                 # sector prefix stripped


def test_pulse_deck_drops_tiles_when_data_absent_and_never_raises():
    html = C.pulse_deck([], {"word": "No data"}, 0, None, [], [], {}, [])
    assert "g-empty" in html                                        # honest empties
    assert "Breadth trend" not in html                             # absent internals -> no tile
    assert 'data-value="0"' in html                                # gauge still renders at 0


def test_featured_card_has_chooser_and_marks_demo_sample():
    html = C.featured_card(
        C.watchlist_block([{"symbol": "TCS", "pct": 1.2, "trend": "LEADING", "deliv": 55}]), True,
        C.portfolio_block({}), True,
        C.index_focus_block([{"index_name": "NIFTY 50", "close_value": 1.0, "ret_1d_pct": 0.1}], [1, 2, 3]))
    for v in ('data-v="v-watch"', 'data-v="v-folio"', 'data-v="v-index"', 'id="g-feat-star"'):
        assert v in html, v
    assert "sample" in html and "TCS" in html                       # demo watch/portfolio marked


def test_watchlist_and_portfolio_blocks():
    wl = C.watchlist_block([{"symbol": "RELIANCE", "pct": 1.24, "trend": "LEADING", "deliv": 61}])
    assert "RELIANCE" in wl and "g-phase lead" in wl and "▲" in wl
    assert "g-empty" in C.watchlist_block([])
    pf = C.portfolio_block({"rows": [{"symbol": "TCS", "pct": 0.2, "weight": 9.0, "since": 31.0}],
                            "invested": 1e7, "day_pct": 0.61, "n": 1})
    assert "TCS" in pf and "Day P&amp;L" in pf and "since entry" in pf
    assert "g-empty" in C.portfolio_block({})


def test_ticker_feeds_render_and_only_first_shows():
    feeds = [{"key": "indices", "label": "Indices",
              "chips": C.rib_chip("NIFTY 50", "24,218", 0.71), "sample": False},
             {"key": "watch", "label": "My watchlist",
              "chips": C.rib_chip("TCS", None, 1.2), "sample": True}]
    html = C.ribbon_feeds(feeds)
    assert 'id="g-feedpick"' in html and 'data-feed="indices"' in html
    assert 'data-feed="watch" hidden' in html                       # only the first feed shows
    assert "NIFTY 50" in html and "g-smp" in html                   # the sample feed is marked


def test_regime_conviction_filings_builders():
    reg = C.regime_banner("Constructive", 64.0, {"adv": 1758, "dec": 592}, 56.0, -1240.0, True)
    assert "g-regime" in reg and "Constructive" in reg and "advancing" in reg
    assert "200-DMA" in reg and "FII net sellers" in reg               # watch clause fires on negative FII
    cv = C.conviction_block([{"symbol": "TCS", "rs_rank": 90, "primary_sector": "Nifty IT",
                              "gap_to_key_p3m": 1.2, "pt14_ns": 160, "pt14_dq": 0}])
    assert "TCS" in cv and "RS #90" in cv and "near entry" in cv and "★ quality" in cv
    assert ">1</b> name cleared all 3 pillars today" in cv     # the legibility count line (singular)
    cv2 = C.conviction_block([{"symbol": "A", "rs_rank": 1}, {"symbol": "B", "rs_rank": 2}])
    assert ">2</b> names cleared all 3 pillars today" in cv2   # plural, accurate count
    assert "g-empty" in C.conviction_block([])
    fl = C.filings_block([{"symbol": "RELIANCE", "detail": "Promoter buy", "date": "2026-07-23", "cls": "pos"}])
    assert "RELIANCE" in fl and "Promoter buy" in fl and "g-fl-dot pos" in fl
    assert "g-empty" in C.filings_block([])


def test_watchlist_reads_both_tiers():
    """Box-verified: the legacy `watchlist` table is empty while the Tracker writes the D54 watch tier
    (`stocks_in_play` status='watch'). Reading only the legacy table meant a name added through the
    Tracker would never appear on the home."""
    import sqlite3
    from src.web.home import reads
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE stocks_in_play(symbol TEXT,status TEXT,date_added TEXT,qty REAL,"
              "entry_price REAL,book TEXT)")
    c.execute("CREATE TABLE watchlist(symbol TEXT, note TEXT, added_at TEXT, added_by TEXT)")
    c.execute("INSERT INTO stocks_in_play VALUES('TRACKED','watch',date('now'),NULL,NULL,'Main')")
    c.execute("INSERT INTO watchlist VALUES('LEGACY','n',date('now'),'r')")
    syms = {r["symbol"] for r in reads.watchlist_rows(c)}
    assert syms == {"TRACKED", "LEGACY"}, ("both watchlist tiers must surface", syms)
    # an 'open' position is a holding, not a watchlist entry
    c.execute("INSERT INTO stocks_in_play VALUES('HELD','open',date('now'),10,100.0,'Main')")
    assert "HELD" not in {r["symbol"] for r in reads.watchlist_rows(c)}


def test_index_reads_match_index_name_case_insensitively():
    """Box-verified defect: index_signals stores MIXED casing — 'Nifty 50' / 'Nifty Bank' / 'Nifty 500'
    / 'Nifty Smallcap 250' but 'NIFTY Midcap 100'. An exact-match IN(...) returned NOTHING, so the whole
    Market-pulse zone silently ran on demo (the 'sample' badge is what exposed it)."""
    import sqlite3
    from src.web.home import reads
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE index_signals(index_name TEXT, trade_date TEXT, close_value REAL,"
              " ret_1d_pct REAL, pct_above_200d_avg REAL)")
    c.execute("INSERT INTO index_signals VALUES('Nifty 50','2026-07-23',23869.6,-0.53,4.2)")
    c.execute("INSERT INTO index_signals VALUES('NIFTY Midcap 100','2026-07-23',61685.0,-0.99,1.1)")
    c.execute("INSERT INTO index_signals VALUES('India VIX','2026-07-23',13.5,1.43,NULL)")
    names = {r["index_name"] for r in reads.index_pulse(c)}
    assert {"Nifty 50", "NIFTY Midcap 100"} <= names, ("mixed-case index names must resolve", names)
    assert len(reads.index_series(c, "NIFTY 50", 10)) == 1     # title-case row found via case-insensitive match
    assert reads.mood_inputs(c)[1] is True                     # 'Nifty 50' above its 200-DMA resolved
    assert reads.vix_latest(c).get("close_value") == 13.5      # India VIX IS a real feed


def test_filings_feed_is_balanced_across_sources_and_deduped():
    """Box-verified defect: stake disclosures fire far more often than insider trades, so a pure
    newest-first merge buried every insider buy. Each source must survive a flood from another."""
    import sqlite3
    from src.web.home import reads
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE insider_events(symbol TEXT,disclosure_dt TEXT,txn_class TEXT,"
              "signal_class TEXT,promoter_group_flag INT)")
    c.execute("CREATE TABLE sast_pledge_events(symbol TEXT,broadcast_dt TEXT,event_type TEXT,event_pct REAL)")
    c.execute("CREATE TABLE sast_reg29_events(symbol TEXT,broadcast_dt TEXT,acq_sale TEXT,promoter_flag INT)")
    c.execute("INSERT INTO insider_events VALUES('INFY',date('now'),'OPEN_MARKET_BUY','conviction',1)")
    c.execute("INSERT INTO sast_pledge_events VALUES('TATAPOWER',date('now'),'released',1.5)")
    # administrative NOISE that must never reach the card (the bulk of the real table)
    c.execute("INSERT INTO insider_events VALUES('NOISECO',date('now'),'ESOP','plumbing',0)")
    c.execute("INSERT INTO insider_events VALUES('JUNKCO',date('now'),'UNKNOWN','ignore',1)")
    for i in range(20):                                   # a flood of NEWER stake events
        c.execute("INSERT INTO sast_reg29_events VALUES(?,datetime('now'),'acquired',0)", (f"SYM{i}",))
    rows = reads.filings_recent(c, days=7, limit=12)
    details = " | ".join(r["detail"] for r in rows)
    syms = {r["symbol"] for r in rows}
    assert "Promoter buy" in details, ("insider filings must survive a stake-disclosure flood", details)
    assert "Pledge released" in details, ("pledge filings must survive too", details)
    assert "NOISECO" not in syms and "JUNKCO" not in syms, ("plumbing/ignore noise must be filtered", syms)
    # near-duplicates (same symbol + same event line) collapse
    c.execute("INSERT INTO insider_events VALUES('INFY',date('now'),'BUY','conviction',1)")
    again = reads.filings_recent(c, days=7, limit=12)
    assert sum(1 for r in again if r["symbol"] == "INFY" and r["detail"] == "Promoter buy") == 1


def test_today_additions_escape_untrusted():
    fl = C.filings_block([{"symbol": "<script>", "detail": "<b>x", "date": "2026-07-23", "cls": "warn"}])
    cv = C.conviction_block([{"symbol": "<script>", "rs_rank": 1, "primary_sector": "<i>"}])
    for h in (fl, cv):
        assert "<script>" not in h and "<i>" not in h and "<b>x" not in h


def test_canon_sector_unifies_nse_and_screener_taxonomies():
    """The heatmap groups by a canonical bucket so the NSE ('Nifty IT', 'Nifty Bank') and Screener
    ('Information Technology', 'Financial Services') taxonomies merge into one block, not duplicates.
    Also guards the greedy-substring trap: 'Capital Goods' must NOT become IT (it contains 'it')."""
    m = {
        "Nifty Bank": "Financials", "Nifty PSU Bank": "Financials", "Financial Services": "Financials",
        "Nifty IT": "IT", "Information Technology": "IT",
        "Nifty Healthcare Index": "Pharma & Health", "Consumer Discretionary": "FMCG & Consumer",
        "Industrials": "Industrials", "Capital Goods": "Industrials", "Telecommunication": "Telecom",
        "Nifty Oil & Gas": "Energy", "Nifty Midcap Select": "Other",
    }
    for raw, want in m.items():
        assert C._canon_sector(raw) == want, (raw, C._canon_sector(raw), want)
    assert C._canon_sector(None) == "Other" and C._canon_sector("") == "Other"


def test_heatmap_squarify_tiles_the_box_and_renders_safely():
    """The treemap is server-computed and can't be pixel-verified this session, so pin its GEOMETRY:
    squarify must tile the whole box (areas sum to dx*dy) with every rect inside the bounds, and the
    rendered tiles must stay within 0-100% and escape untrusted symbols."""
    import re
    sizes = [40.0, 25.0, 15.0, 12.0, 8.0]                  # descending, as squarify requires
    area = 100.0 * 60.0
    rects = C._squarify([s / sum(sizes) * area for s in sizes], 0.0, 0.0, 100.0, 60.0)
    assert len(rects) == len(sizes)
    covered = sum(r["dx"] * r["dy"] for r in rects)
    assert abs(covered - area) / area < 0.02, ("squarify must tile the whole box", covered, area)
    for r in rects:
        assert r["dx"] >= 0 and r["dy"] >= 0
        assert r["x"] >= -0.01 and r["y"] >= -0.01
        assert r["x"] + r["dx"] <= 100.01 and r["y"] + r["dy"] <= 60.01
    rows = [{"symbol": "RELIANCE", "sector": "Energy", "pct": 1.2, "turnover": 4200},
            {"symbol": "<script>", "sector": "IT", "pct": -0.4, "turnover": 2200},
            {"symbol": "SBIN", "sector": "Bank", "pct": -0.5, "turnover": 2600}]
    hm = C.heatmap(rows)
    assert "<script>" not in hm and "g-hm-t" in hm and "tile size = turnover" in hm
    tiles = re.findall(r"left:([\d.]+)%;top:([\d.]+)%;width:([\d.]+)%;height:([\d.]+)%", hm)
    assert len(tiles) == 3
    for l, t, w, h in ((float(a) for a in tup) for tup in tiles):
        assert l + w <= 100.5 and t + h <= 100.5, ("a tile escaped the box", l, t, w, h)
    assert "g-empty" in C.heatmap([])


def test_new_builders_escape_and_leak_no_markers():
    outs = [
        C.watchlist_block([{"symbol": "<script>x</script>", "pct": 1.0, "trend": "<b>"}]),
        C.rib_chip("<script>", "x", 1.0),
        C.pulse_deck([{"index_name": "<i>", "close_value": 1, "ret_1d_pct": 1}],
                     {"word": "<b>"}, 1, None, [], [], {}, []),
    ]
    for html in outs:
        assert "<script>" not in html and "<i>" not in html
        assert "pv3" not in html and "data-ui-v3" not in html and "uk-sub" not in html
