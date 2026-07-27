"""test_home_w2_markets.py — the lane W2-C gate (Graphite Markets: seasonal · patterns · anatomy ·
own-history · compare).

Locks the four things that would silently rot:
  1. the five declared-child routes serve, carry the Graphite marker, and leak no preview/legacy
     marker (the isolation contract, per-route rather than only on /dash/home),
  2. the DESCRIPTIVE FENCES travel with their data — seasonal's 0-certified null result, Wolfe's
     "the edge is in the selection, not the craft", the move-anatomy post-selection caveat, and
     own-history's "context, never a forecast",
  3. `/dash/home/own-history` never reaches for the classic self-history web-view engine (the
     recorded verdict behind the stored-column route), and the Wolfe port never imports the hot
     `wolfe*.py` / `stock_chart*.py` lane,
  4. the read layer is defensive on an empty database and the render layer escapes untrusted text.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src" / "web" / "home"

W2_MODULES = ("w2_reads.py", "w2_kit.py", "w2_pages.py", "seasonal_pages.py",
              "patterns_pages.py", "anatomy_pages.py", "compare_pages.py")

ROUTES = ("/dash/home/seasonal", "/dash/home/patterns", "/dash/home/anatomy",
          "/dash/home/own-history", "/dash/home/compare")

PREVIEW_LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')


def _client():
    from src.main import app
    return TestClient(app)


# ── 1. the routes serve, in the Graphite identity ───────────────────────────────
def test_every_w2_route_serves_in_the_graphite_identity():
    c = _client()
    for path in ROUTES:
        r = c.get(path)
        assert r.status_code == 200, (path, r.status_code)
        assert "data-ui-g" in r.text, path
        for m in PREVIEW_LEGACY_MARKERS:
            assert m not in r.text, (path, m)


def test_every_seasonal_and_pattern_view_serves():
    c = _client()
    for view in ("tape", "screen", "divergence", "calendar"):
        r = c.get("/dash/home/seasonal?view=" + view)
        assert r.status_code == 200 and "w2-vbar" in r.text, view
    for view in ("wolfe", "harmonic"):
        r = c.get("/dash/home/patterns?view=" + view)
        assert r.status_code == 200 and "w2-vbar" in r.text, view
    # an unknown view falls back rather than 404/500ing
    assert _client().get("/dash/home/seasonal?view=nonsense").status_code == 200


def test_all_five_routes_are_declared_children_in_the_route_registry():
    from tests.test_dash_route_registry import INTERNAL_DEV
    for path in ROUTES:
        assert path in INTERNAL_DEV, path
        owner, why = INTERNAL_DEV[path]
        assert owner and why, path


def test_seasonal_csv_export_uses_the_same_params_as_the_view():
    c = _client()
    r = c.get("/dash/home/seasonal?view=calendar&format=csv")
    assert r.status_code == 200 and "text/csv" in r.headers.get("content-type", "")
    assert r.text.startswith("symbol,expiry_ret_delta")
    r = c.get("/dash/home/seasonal?view=screen&format=csv")
    assert r.status_code == 200 and r.text.startswith("entity,cell,hit_rate")


# ── 2. the fences travel with the data ──────────────────────────────────────────
def test_seasonal_carries_the_zero_certified_fence():
    c = _client()
    tape = c.get("/dash/home/seasonal?view=tape").text
    assert "certification" in tape.lower()
    assert "null result is the finding" in tape or "that is the result" in tape
    cal = c.get("/dash/home/seasonal?view=calendar").text
    assert "0-certified" in cal
    screen = c.get("/dash/home/seasonal?view=screen").text
    assert "NOT certified" in screen and "coin flip" in screen


def test_wolfe_carries_the_selection_not_craft_fence():
    t = _client().get("/dash/home/patterns?view=wolfe").text
    assert "selection, not the craft" in t
    assert "not because following them is a validated way to trade" in t


def test_harmonic_is_read_by_side():
    t = _client().get("/dash/home/patterns?view=harmonic").text
    assert "selection edge" in t and "tail only" in t


def test_move_anatomy_carries_the_post_selection_caveat_or_says_it_is_absent():
    t = _client().get("/dash/home/anatomy").text
    assert ("not present on this host" in t) or ("BECAUSE a move already fired" in t)


def test_own_history_is_fenced_as_context_not_forecast():
    t = _client().get("/dash/home/own-history").text
    assert "never a forecast" in t or "says nothing about what happens next" in t


def test_compare_states_the_rebasing_and_the_adjustment():
    t = _client().get("/dash/home/compare").text
    assert "rebased to 100" in t
    assert "splits and bonuses" in t


# ── 3. the isolation verdicts this lane inherits ────────────────────────────────
def test_w2_modules_never_import_the_classic_self_history_or_the_hot_chart_lane():
    banned = ("self_history_view", "move_anatomy_view", "seasonal_view", "seasonal_screen_view",
              "calendar_conditioning_view", "harmonic_view", "wolfe_view", "wolfe_trades_view",
              "stock_chart", "stock_chart_v3", "infographics", "seasonal_tape")
    offenders = []
    for name in W2_MODULES:
        text = (HOME / name).read_text(encoding="utf-8", errors="replace")
        for mod in banned:
            if re.search(r"^\s*(from|import)\s+[\w.]*\b" + mod + r"\b", text, re.M):
                offenders.append(name + " -> " + mod)
    assert not offenders, offenders


def test_every_symbol_resolves_to_the_graphite_stock_page_not_the_classic_dossier():
    """Post-D148 the Graphite estate is the landing experience and the stock page lives at
    /dash/home/stock (lane W1). A W2-C page must never bounce a reader out to /dash/stock."""
    from src.web.home import w2_kit as K
    assert K.STOCK_PATH == "/dash/home/stock"
    assert 'href="/dash/home/stock?sym=TCS"' in K.sym_link("TCS")
    for name in W2_MODULES:
        text = (HOME / name).read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.lstrip().startswith(("#", '"', "'")) or "STOCK_PATH" in line:
                continue          # prose/docstring lines and the definition itself
            assert '"/dash/stock' not in line and "'/dash/stock" not in line, (name, line)


def test_symbols_are_escaped_in_the_lane_sym_link():
    from src.web.home import w2_kit as K
    out = K.sym_link('<img src=x onerror="alert(1)">')
    assert "<img" not in out and "&lt;img" in out


def test_own_history_reads_only_stored_self_relative_columns():
    """Pin the stored-column route: every own-history measure must resolve to a real
    `stock_signals` column in db.py's schema OR migrations (several are `_ensure_column`-added, so
    SCHEMA_BASE alone is not the source of truth), or be the one derived delivery gap. A rename by
    the signals lane trips this gate instead of silently blanking the page."""
    import inspect

    import src.core.db as db
    from src.web.home import w2_reads as W
    src = inspect.getsource(db)
    for (_k, _p, c, _u, _h) in W.OWN_METRICS:
        assert c == "_deliv_gap" or ('"stock_signals", "' + c + '"') in src or (c + " ") in src, c


# ── 4. defensive reads + escaped renders ────────────────────────────────────────
def _empty_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_every_w2_read_is_defensive_on_an_empty_database():
    from src.web.home import w2_reads as W
    conn = _empty_conn()
    assert W.seasonal_entities(conn) == []
    assert W.seasonal_script(conn, "index", "Nifty 50") == {}
    assert W.seasonal_month_screen(conn, 7) == []
    assert W.seasonal_divergence(conn, "A", "B") == []
    assert W.seasonal_outlook(conn, "index", "Nifty 50") == []
    assert W.seasonal_meta(conn) == {}
    assert W.calendar_conditioning(conn) == ([], "")
    assert W.wolfe_scan(conn) == ([], {})
    assert W.harmonic_scan(conn) == ([], {})
    assert W.own_history_universe(conn) == ([], "")
    assert W.own_history_symbol(conn, "TCS") == {}
    assert W.compare_indices(conn) == []
    assert W.compare_series(conn, ["Nifty 50"], ["TCS"]) == []
    assert W.valid_symbols(conn, ["TCS"]) == []
    assert W.move_anatomy("/definitely/not/a/path.db") == {}


def test_calendar_view_escapes_an_untrusted_symbol():
    from src.web.home import seasonal_pages as S
    conn = _empty_conn()
    conn.execute("CREATE TABLE x_setups_signals (module TEXT, rank INT, payload TEXT)")
    conn.execute("CREATE TABLE x_setups_meta (k TEXT, v TEXT)")
    conn.execute("INSERT INTO x_setups_signals VALUES ('calendar_conditioning', 1, ?)",
                 ('{"symbol": "<script>x</script>", "expiry_ret_delta": 0.001, "n_days": 10, '
                  '"n_expiry": 2}',))
    conn.commit()
    html = S._calendar(conn, {})
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_wilson_band_straddles_fifty_on_a_small_sample():
    """The honesty column must actually behave: 2-of-3 is indistinguishable from a coin flip."""
    from src.web.home.w2_reads import _wilson
    lo, hi = _wilson(2, 3)
    assert lo < 0.5 < hi
    lo, hi = _wilson(30, 32)
    assert lo > 0.5


def test_compare_accepts_both_sym_and_cmp_deep_links():
    """The stock lane deep-links `?sym=X&cmp=Y`; both must reach the same overlay."""
    from src.web.home import compare_pages as CP
    assert CP._split(["A,B", "C"]) == ["A", "B", "C"]
    r = _client().get("/dash/home/compare?sym=ALPHA&cmp=BETACO")
    assert r.status_code == 200


def test_rebasing_puts_every_line_at_one_hundred():
    from src.web.home import w2_reads as W
    conn = _empty_conn()
    conn.execute("CREATE TABLE index_rows (index_name TEXT, trade_date TEXT, close_value REAL)")
    for i, v in enumerate((200.0, 210.0, 190.0)):
        conn.execute("INSERT INTO index_rows VALUES ('X', ?, ?)", ("2026-01-%02d" % (i + 1), v))
    conn.commit()
    out = W.compare_series(conn, ["X"], [], sessions=50)
    assert out and abs(out[0]["points"][0]["v"] - 100.0) < 1e-9
    assert abs(out[0]["points"][-1]["v"] - 95.0) < 1e-9
    assert abs(out[0]["change"] + 5.0) < 1e-9
