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
