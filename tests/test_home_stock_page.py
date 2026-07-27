"""test_home_stock_page.py — the Graphite stock page gate (W1).

Proves the cutover blocker is really closed: `/dash/home/stock?sym=` serves, in the Graphite
identity, a complete per-symbol evidence scroll — and does it without importing one preview or
legacy render module, without fabricating a number, and without a verdict verb.

Two layers deliberately:
  * ROUTE tests through TestClient (work against whatever DB is ambient — markers, registry,
    payload budget, URL discipline, hostile input);
  * STRUCTURE tests against a purpose-built synthetic sqlite, so every section, the reference
    chips and the X-setups block are asserted on KNOWN data rather than on whatever the local
    fixture happens to hold.
"""
from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from src.web.home import stock_chart_g as CH
from src.web.home import stock_page as SP
from src.web.home import stock_reads as SR

ROUTE = "/dash/home/stock"
PREVIEW_LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')


def _client():
    from src.main import app
    return TestClient(app)


# ── a synthetic per-symbol database (structure probes stand on known data) ───────
def _db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT, segment TEXT,
            open REAL, high REAL, low REAL, close REAL, prev_close REAL, deliv_per REAL,
            value REAL, deliv_qty REAL, volume REAL);
        CREATE TABLE stock_signals (symbol TEXT, trade_date TEXT, p_score INT, r_score INT,
            rs_rank INT, trigger_rank TEXT, delivery_value_per_trade REAL,
            ratio_today_vs_power_1m REAL, accum_character TEXT, turnover_surge_1m REAL,
            primary_sector TEXT, rs_phase TEXT, rs_vs_broad_trend_state TEXT,
            rs_vs_broad_above_50ma INT, rs_vs_broad_above_200ma INT, rs_vs_broad_new_52w_high INT,
            rs_vs_broad_slope_1m REAL, rs_vs_broad_slope_3m REAL, rs_vs_broad_slope_6m REAL,
            rs_vs_broad_slope_12m REAL, rs_vs_sector_trend_state TEXT, pct_from_52w_high REAL,
            avg_close_p1m REAL, avg_close_p3m REAL, avg_close_p6m REAL, avg_close_p12m REAL,
            avg_close_r12m REAL, key_price_p1m REAL, key_price_p3m REAL, key_price_p6m REAL,
            key_price_p12m REAL, gap_to_key_p1m REAL, gap_to_key_p3m REAL, gap_to_key_p6m REAL,
            gap_to_key_p12m REAL);
        CREATE TABLE mep_signals (symbol TEXT, trade_date TEXT, mep_state TEXT,
            mep_state_smooth TEXT, mep_score_smooth REAL, pressure REAL, clv REAL,
            drift_22d REAL, updown_vol_22d REAL);
        CREATE TABLE pattern_scores (symbol TEXT, scored_at TEXT, ns_base REAL, ns_pessimistic REAL,
            ns_optimistic REAL, tier TEXT, qg_pass INT, hard_disqualified INT,
            disqualifier_reasons TEXT);
        CREATE TABLE cpr_signals (symbol TEXT, period_end_date TEXT, timeframe TEXT, p REAL,
            bc REAL, tc REAL, width_pct REAL, compression_pctile REAL, pattern TEXT, regime TEXT);
        CREATE TABLE concall_scores (symbol TEXT, tier TEXT, composite_score REAL,
            n_concalls INT, n_promises_resolved INT);
        CREATE TABLE nse_equity_list (symbol TEXT, company_name TEXT);
        CREATE TABLE x_setups_signals (module TEXT, symbol TEXT, asof TEXT, rank INT,
            payload TEXT, computed_at TEXT);
        CREATE TABLE x_setups_meta (k TEXT PRIMARY KEY, v TEXT);
        """)
    for i in range(1, 61):                       # 60 sessions of tape
        d = "2026-05-%02d" % i if i <= 31 else "2026-06-%02d" % (i - 31)
        close = 100.0 + i
        conn.execute("INSERT INTO bhavcopy_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     ("TESTX", d, "EQ", "CM", close - 1, close + 2, close - 2, close,
                      close - 1, 40.0 + (i % 20), 1_000_000.0 * i, 5000.0, 12000.0))
    conn.execute("INSERT INTO stock_signals VALUES ('TESTX','2026-06-29',4,3,88,'S',250000.0,"
                 "1.8,'STEADY_ACCUM',1.6,'Nifty IT','LEADING','UPTREND',1,1,0,"
                 "0.01,0.02,0.03,0.04,'IMPROVING',-4.5,150.0,148.0,140.0,130.0,135.0,"
                 "151.0,149.0,141.0,131.0,-1.2,0.8,4.0,9.0)")
    conn.execute("INSERT INTO stock_signals VALUES ('PEERX','2026-06-29',2,1,55,'A',1000.0,"
                 "0.5,'NEUTRAL',1.0,'Nifty IT','NEUTRAL','FLAT',0,0,0,0,0,0,0,'FLAT',-10.0,"
                 "0,0,0,0,0,0,0,0,0,0,0,0,0)")
    conn.execute("INSERT INTO mep_signals VALUES ('TESTX','2026-06-29','ACCUM','STRONG_ACCUM',"
                 "1.9,0.4,0.7,0.02,1.4)")
    conn.execute("INSERT INTO pattern_scores VALUES ('TESTX','2026-06-20',71.0,64.0,78.0,'B',1,0,'')")
    for tf in ("D", "W", "M"):
        conn.execute("INSERT INTO cpr_signals VALUES ('TESTX','2026-06-29',?,120.0,118.0,122.0,"
                     "1.7,88.0,'BULL_U','TREND')", (tf,))
    conn.execute("INSERT INTO concall_scores VALUES ('TESTX','A',77.5,9,14)")
    conn.execute("INSERT INTO nse_equity_list VALUES ('TESTX','Testex Industries')")
    payloads = {
        "base_breakout": {"symbol": "TESTX", "x09_score": 1.44, "base_length": 55,
                          "base_depth": 0.18, "breakout_velocity": 2.1, "vol_surge": 3.2,
                          "days_since_breakout": 4, "still_above_pivot": 1,
                          "breakout_date": "2026-06-25"},
        "volume_shelves": {"symbol": "TESTX", "poc": 118.5, "va_low": 110.0, "va_high": 126.0,
                           "n_shelves": 3, "price_vs_va": "above_value_area", "last_close": 160.0},
        "overnight_split": {"symbol": "TESTX", "on_share": 0.62, "cum_total_pct": 0.44,
                            "overnight_pump": 1},
    }
    for mod, p in payloads.items():
        conn.execute("INSERT INTO x_setups_signals VALUES (?,?,?,?,?,?)",
                     (mod, "TESTX", "2026-06-29", 1, json.dumps(p), "2026-06-29 18:00:00"))
    conn.execute("INSERT INTO x_setups_meta VALUES ('asof','2026-06-29')")
    conn.commit()
    return conn


# ── route layer ─────────────────────────────────────────────────────────────────
def test_route_serves_picker_symbol_and_miss():
    c = _client()
    for url in (ROUTE, ROUTE + "?sym=TCS", ROUTE + "?sym=ZZQQNOTREAL",
                ROUTE + "?sym=TCS&chart=max"):
        r = c.get(url, follow_redirects=True)
        assert r.status_code == 200, (url, r.status_code)
        assert "data-ui-g" in r.text and "g-tokens graphite" in r.text, url


def test_route_carries_no_preview_or_legacy_marker():
    r = _client().get(ROUTE + "?sym=TCS", follow_redirects=True)
    for m in PREVIEW_LEGACY_MARKERS:
        assert m not in r.text, ("the Graphite stock page leaked a preview/legacy marker", m)


def test_route_is_registered_as_a_declared_child():
    from tests import test_dash_route_registry as gate
    assert ROUTE in gate.INTERNAL_DEV
    owner, rationale = gate.INTERNAL_DEV[ROUTE]
    assert owner == "graphite-home" and len(rationale) > 40


def test_symbol_input_is_sanitised_and_never_reflected_raw():
    r = _client().get(ROUTE + '?sym=<script>alert(1)</script>', follow_redirects=True)
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text
    assert SR.clean_symbol("<script>alert(1)</script>") == "SCRIPTALERT1SCRIPT"


def test_payload_stays_inside_the_budget_even_at_full_archive_depth():
    """The ratified stock archetype budget: an initial document under 1,000,000 raw bytes.

    The route test alone is weak (the local fixture is shallow), so the WORST case is constructed:
    the deepest name in the bhav archive is ~5,400 sessions, and `?chart=max` serves all of them.
    """
    for url in (ROUTE + "?sym=TCS", ROUTE + "?sym=TCS&chart=max"):
        assert len(_client().get(url, follow_redirects=True).content) < 1_000_000, url
    row = {"t": "2024-01-01", "o": 1234.55, "h": 1240.1, "l": 1220.05, "c": 1235.75,
           "dvpt": 1234567.0, "dp": 56.7, "r1m": 1.23, "tv": 1234567890.12, "dv": 987654321.55}
    deep = CH.chart_html("RELIANCE", "Reliance Industries",
                         {"series": [row] * SR.MAX_SESSIONS, "zones": []}, deep=True)
    # the chart is the whole payload risk; leave >300 KB of headroom for the page around it
    assert len(deep.encode()) < 700_000, len(deep.encode())


def test_url_state_uses_sym_never_symbol():
    r = _client().get(ROUTE + "?sym=TCS", follow_redirects=True)
    assert "?symbol=" not in r.text


# ── structure layer (synthetic DB — deterministic) ──────────────────────────────
def test_every_evidence_section_renders_with_its_data():
    conn = _db()
    body, rail = SP.compose(conn, "TESTX")
    for key in ("chart", "pos", "mep", "rs", "qual", "cpr", "cci", "setups"):
        assert 'id="' + key + '"' in body, key
    assert 'id="fno"' not in body, "no F&O row exists for TESTX — the section must not appear"
    # identity + digest + the deterministic sentence + the sticky index
    assert "Testex Industries" in body and "g-stiles" in body and "g-sidx" in body
    assert "g-snarr" in body and "relative strength is top-quartile (#88 of 99)" in body
    # sentence-case must not lower-case a stored grade (str.capitalize() would say "tier b")
    assert "quality read grades tier B" in body
    assert "credibility grades A." in SP.narrative({"sym": "TESTX", "sig": None, "mep": None,
                                                    "pt": None, "cci": {"tier": "A"}})
    assert body.count("g-snarr") == 1, "the sentence caps at four clauses, once"
    # the real stored numbers reached the page
    assert "STRONG_ACCUM".replace("_", " ").lower() in body.lower()
    assert "88" in body and "bull u" in body.lower()
    # the rail carries the peer, linked back into the Graphite experience
    assert "/dash/home/stock?sym=PEERX" in body + rail


def test_chart_island_is_inert_json_and_carries_the_zones():
    conn = _db()
    isl = SR.chart_island(conn, "TESTX")
    assert isl["n"] == 60 and len(isl["zones"]) == 5
    html = CH.chart_html("TESTX", "Testex", isl)
    assert '<script type="application/json" id="g-cdata">' in html
    start = html.index('id="g-cdata">') + len('id="g-cdata">')
    payload = html[start:html.index("</script>", start)]
    assert "<" not in payload, "a raw '<' inside the island could close the script tag"
    data = json.loads(payload)
    # rows are compact arrays in `cols` order — the payload-budget format
    assert data["cols"] == list(CH.COLS)
    assert len(data["rows"]) == 60 and data["zones"][0]["label"] == "P1M"
    assert isinstance(data["rows"][0], list) and len(data["rows"][0]) == len(CH.COLS)


def test_pro_reference_layer_is_self_relative_and_never_fabricated():
    conn = _db()
    ref = SR.self_reference(conn, "TESTX")
    assert ref["turnover"]["pctile"] is not None and ref["turnover"]["n"] >= 20
    assert ref["dvpt"] == {}, "no per-day DVPT history exists here — no percentile may be invented"
    body, _rail = SP.compose(conn, "TESTX")
    assert "g-refchip" in body and "pro-more" in body     # Pro-only by construction
    # thin history must yield NO chip at all
    thin = sqlite3.connect(":memory:")
    thin.row_factory = sqlite3.Row
    thin.execute("CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT, "
                 "deliv_per REAL, value REAL)")
    for i in range(1, 6):
        thin.execute("INSERT INTO bhavcopy_rows VALUES ('THIN','2026-06-0%d','EQ',40.0,1000.0)" % i)
    assert SR.self_reference(thin, "THIN") == {"deliv": {}, "turnover": {}, "dvpt": {}}


def test_x_setups_block_renders_all_three_modules_for_this_symbol():
    conn = _db()
    xs = SR.x_setups(conn, "TESTX")
    assert xs["asof"] == "2026-06-29"
    assert all(xs[m] is not None for m in SR.X_MODULES)
    html = SP.sec_setups({"sym": "TESTX"}, xs)
    for token in ("X-09", "X-07", "X-04", "1.44", "55 sessions", "118.50", "Launchpad", "above it"):
        assert token in html, token
    # the payloads store RATIOS despite names like `cum_total_pct` (= expm1 of summed log-returns)
    assert "18.0%" in html and "62.0%" in html and "44.0%" in html
    assert SP._frac_pct(2.0) == "200.0%", "a +200% window must never be shown as 2%"
    assert SP._frac_pct(float("nan")) == "—" and SP._frac_pct(None) == "—"
    # a symbol the scan does not list honest-empties (never a fabricated row)
    xs2 = SR.x_setups(conn, "PEERX")
    assert all(xs2[m] is None for m in SR.X_MODULES)
    assert "g-empty" in SP.sec_setups({"sym": "PEERX"}, xs2)


def test_falsified_families_carry_their_descriptive_only_fence():
    conn = _db()
    body, _rail = SP.compose(conn, "TESTX")
    assert body.count("g-fence-top") >= 3      # accumulation · credibility · setups
    assert "failed its out-of-sample gate" in body
    assert "failed its leak-free predictive gate" in body
    assert "no edge net of cost" in body


def test_no_verdict_verbs_anywhere_in_the_rendered_page():
    conn = _db()
    body, rail = SP.compose(conn, "TESTX")
    low = (body + rail).lower().replace("buy/sell", "")
    for verb in (" buy ", " sell ", " avoid ", " ride ", " fade ", "add to your position"):
        assert verb not in low, verb


def test_page_never_raises_on_an_empty_or_partial_database():
    empty = sqlite3.connect(":memory:")
    empty.row_factory = sqlite3.Row
    body, rail = SP.compose(empty, "TESTX")
    assert "Symbol not found" in body and rail == ""
    # a DB with tape but nothing else must still render the scroll
    partial = sqlite3.connect(":memory:")
    partial.row_factory = sqlite3.Row
    partial.execute("CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT, "
                    "segment TEXT, open REAL, high REAL, low REAL, close REAL, prev_close REAL, "
                    "deliv_per REAL, value REAL, deliv_qty REAL, volume REAL)")
    partial.execute("INSERT INTO bhavcopy_rows VALUES ('BARE','2026-06-01','EQ','CM',10,11,9,10,"
                    "10,30.0,1000.0,10.0,100.0)")
    body2, _r2 = SP.compose(partial, "BARE")
    assert 'id="chart"' in body2 and "No positioning signals" in body2


def test_the_three_new_modules_import_nothing_banned():
    """The chart verdict in code form: the Graphite page reaches NEITHER chart engine — not the
    banned `stock_chart_v3` fork, and not the classic `stock_chart`/`dashboard` pair whose snippet
    binds legacy DOM. It carries its own."""
    import re
    from pathlib import Path
    from tests.test_home_isolation import BANNED
    root = Path(__file__).resolve().parents[1] / "src" / "web" / "home"
    for name in ("stock_page.py", "stock_reads.py", "stock_chart_g.py"):
        text = (root / name).read_text(encoding="utf-8")
        for mod in BANNED + ("stock_chart",):
            assert not re.search(r"^\s*(from|import)\s+[\w.]*\b" + mod + r"\b", text, re.M), \
                (name, mod)


def test_every_column_the_page_reads_exists_in_the_canonical_schema(tmp_path, monkeypatch):
    """The read-contract sibling for the per-symbol layer.

    This gate exists because the first cut of the F&O section invented `oi` / `oi_change` /
    `pcr_oi`; the real columns are `fut_oi` / `fut_oi_chg` / `pcr`, and the page would have
    rendered silent em dashes on the box while every test stayed green. A rename in an old lane
    must go RED here, not unnoticed.
    """
    from src.automation.capital_allocation import _SCHEMA as CA_SCHEMA
    from src.automation.wolfe import _ensure_scan_table
    from src.core import db as DB
    # build the schema exactly the way production does — SCHEMA_BASE *plus* the `_ensure_column`
    # migration pass, since many columns the page reads (p_score, accum_character, rs_phase, …)
    # arrive as migrations, not in the base script. Hermetic: a temp file, never the real DB.
    monkeypatch.setattr(DB, "DB_PATH", tmp_path / "schema-probe.db")
    DB._init_ddl()
    mem = sqlite3.connect(tmp_path / "schema-probe.db")
    mem.row_factory = sqlite3.Row
    mem.executescript(CA_SCHEMA)
    _ensure_scan_table(mem)                      # wolfe_signals lives in its own module DDL
    from src.automation import rs_phase          # rs_phase/rsi_of_rs are additive rotation columns
    rs_phase.ensure_columns(mem)

    def cols(table):
        return {r[1] for r in mem.execute("PRAGMA table_info(%s)" % table)}

    expect = {
        "stock_signals": ("symbol", "trade_date", "p_score", "r_score", "rs_rank", "trigger_rank",
                          "delivery_value_per_trade", "ratio_today_vs_power_1m", "accum_character",
                          "turnover_surge_1m", "primary_sector", "rs_phase",
                          "rs_vs_broad_trend_state", "rs_vs_broad_above_50ma",
                          "rs_vs_broad_above_200ma", "rs_vs_broad_new_52w_high",
                          "rs_vs_broad_slope_1m", "rs_vs_sector_trend_state", "pct_from_52w_high",
                          "avg_close_p1m", "avg_close_p3m", "avg_close_p6m", "avg_close_p12m",
                          "avg_close_r12m", "key_price_p3m", "gap_to_key_p3m"),
        "bhavcopy_rows": ("symbol", "trade_date", "series", "segment", "open", "high", "low",
                          "close", "prev_close", "deliv_per", "deliv_qty", "value", "volume"),
        "mep_signals": ("symbol", "trade_date", "mep_state", "mep_state_smooth",
                        "mep_score_smooth", "pressure", "clv", "drift_22d", "updown_vol_22d"),
        "pattern_scores": ("symbol", "scored_at", "ns_base", "ns_pessimistic", "ns_optimistic",
                           "tier", "qg_pass", "hard_disqualified", "disqualifier_reasons"),
        "cpr_signals": ("symbol", "period_end_date", "timeframe", "p", "bc", "tc", "width_pct",
                        "compression_pctile", "pattern", "regime"),
        "concall_scores": ("symbol", "as_of_period", "tier", "composite_score",
                           "credibility_score", "guidance_accuracy_score", "transparency_score",
                           "credibility_trend", "n_concalls", "n_promises_resolved"),
        "fno_oi_signals": ("symbol", "trade_date", "quadrant", "fut_oi", "fut_oi_chg",
                           "fut_oi_chg_pct", "pcr", "basis_pct", "max_pain", "sup_strike",
                           "res_strike"),
        "capital_allocation_scores": ("symbol", "ca_score", "ca_tier", "as_of"),
        # wolfe_signals keys on `sym`, NOT `symbol` — asserted explicitly so the read can't drift back
        "wolfe_signals": ("sym", "in_zone", "dir", "scan_date", "id"),
        "nse_equity_list": ("symbol", "company_name"),
    }
    missing = []
    for table, names in expect.items():
        have = cols(table)
        assert have, ("table absent from the canonical schemas", table)
        missing += [table + "." + n for n in names if n not in have]
    assert not missing, ("the stock page reads columns the canonical schema does not have", missing)
    assert "symbol" not in cols("wolfe_signals"), \
        "wolfe_signals gained a `symbol` column — revisit stock_reads.core's `sym=` query"
    # and the reads must actually RETURN their rows — a wrong column name raises, gets swallowed by
    # the defensive layer, and the section silently renders em dashes forever (the failure mode the
    # M4 hub shipped with on Wolfe). So exercise both against the production schema.
    mem.execute("INSERT INTO wolfe_signals (universe, sym, dir, in_zone, scan_date) "
                "VALUES ('nifty500','TESTX','BULL',1,'2026-06-29')")
    assert (SR.core(mem, "TESTX").get("wolfe") or {}).get("in_zone") == 1
    mem.execute("INSERT INTO fno_oi_signals (symbol, trade_date, quadrant, fut_oi, fut_oi_chg, "
                "fut_oi_chg_pct, pcr, basis_pct, max_pain, sup_strike, res_strike) VALUES "
                "('TESTX','2026-06-29','LONG_BUILDUP',1234567,45000,3.8,0.87,0.42,1200,1150,1300)")
    core = SR.core(mem, "TESTX")
    assert core.get("fno") is not None
    fno_html = SP.sec_fno(core)
    for token in ("long buildup", "1,234,567", "0.87", "+0.42%", "1,200.0", "1,150.0 / 1,300.0"):
        assert token in fno_html, token
    import re as _re
    values = _re.findall(r'<td class="g-num">(.*?)</td>', fno_html)
    assert len(values) == 8 and "—" not in values, \
        ("every F&O value cell must resolve — an em dash here means a wrong column name", values)
    assert "Wolfe wave in zone" in SP.badges(core)


def test_x_setups_read_never_writes_to_the_database():
    """The page is strictly read-only. `x_setups_signals.latest()` calls `ensure_table()` (a
    CREATE), so the block reads the snapshot with a plain bounded SELECT instead."""
    ro = sqlite3.connect(":memory:")
    ro.row_factory = sqlite3.Row
    before = {r[0] for r in ro.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    out = SR.x_setups(ro, "TESTX")
    after = {r[0] for r in ro.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert before == after, "the setups read created a table — it must never write"
    assert all(out[m] is None for m in SR.X_MODULES)


def test_module_selftests_pass():
    assert SR._selftest() == 0
    assert CH._selftest() == 0
    assert SP._selftest() == 0
