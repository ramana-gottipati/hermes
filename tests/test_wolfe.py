"""Point-4 reconciliation (2026-07-11) — Ramana's rule: among waves sharing the same
1-2-3 skeleton, point 4 is the EXTREME high (BULL) / low (BEAR) of the rally into point 5,
NOT the tidiest fractal. Regression fixture for the TARSONS Feb-2022 case, where the later,
lower high (Feb-21 @ 674.5, a clean degree-5 fractal, §B total 13.00) wrongly out-ranked the
true apex (Feb-10 @ 698.8, a degree-2 fractal, §B total 12.67). Pure over Wave-shaped inputs
— no DB or market data needed."""
from types import SimpleNamespace as NS

from src.automation.wolfe import _reconcile_point4, _classify


def _p(idx, price):
    return NS(idx=idx, price=price)


def _wave(direction, p1, p2, p3, p4, total):
    return NS(direction=direction, p=[_p(*p1), _p(*p2), _p(*p3), _p(*p4)],
              score={"total": total})


def test_bull_keeps_higher_point4_over_cleaner_fractal():
    # the TARSONS case in miniature: the later, LOWER high carries the higher §B total
    # (tidier fractal) — reconciliation must still pick the earlier, HIGHER high as point 4.
    apex = _wave("BULL", (0, 631.5), (6, 720.7), (11, 627.0), (13, 698.8), 12.67)   # Feb-10 (true)
    later = _wave("BULL", (0, 631.5), (6, 720.7), (11, 627.0), (20, 674.5), 13.00)  # Feb-21 (higher Q)
    for order in ([apex, later], [later, apex]):        # iteration order must not matter
        out = _reconcile_point4(order)
        assert len(out) == 1
        assert out[0].p[3].idx == 13 and out[0].p[3].price == 698.8


def test_bear_keeps_lower_point4():
    apex = _wave("BEAR", (0, 100.0), (6, 60.0), (11, 110.0), (13, 70.0), 10.0)   # lower low = true apex
    later = _wave("BEAR", (0, 100.0), (6, 60.0), (11, 110.0), (20, 80.0), 12.0)  # higher low, higher Q
    out = _reconcile_point4([later, apex])
    assert len(out) == 1 and out[0].p[3].price == 70.0


def test_distinct_waves_are_both_kept():
    # different 1-2-3 skeletons must never be merged.
    a = _wave("BULL", (0, 631.0), (6, 720.0), (11, 627.0), (13, 698.0), 12.0)
    b = _wave("BULL", (50, 500.0), (56, 600.0), (61, 490.0), (63, 560.0), 11.0)
    assert len(_reconcile_point4([a, b])) == 2


def test_equal_point4_price_breaks_deterministically():
    # equal point-4 price → higher §B total wins (then earliest bar); stable regardless of order.
    lowq = _wave("BULL", (0, 631.0), (6, 720.0), (11, 627.0), (13, 698.0), 12.0)
    highq = _wave("BULL", (0, 631.0), (6, 720.0), (11, 627.0), (18, 698.0), 14.0)
    for order in ([lowq, highq], [highq, lowq]):
        out = _reconcile_point4(order)
        assert len(out) == 1 and out[0].score["total"] == 14.0


# --- convergence rule (2026-07-11): rails 1-3 and 2-4 must cross forward of point 4 ---
def _pv(idx, price, kind):
    return NS(idx=idx, price=price, kind=kind)


def test_crossing_admits_converging_bear_the_leg_ratio_killed():
    # rising wedge: leg 3-4 (10) out-prices leg 1-2 (6) -> the OLD cap rejected it; but rail 2-4
    # is steep (point 2 parked late) and out-angles rail 1-3 -> they meet forward -> now valid.
    a = _pv(0, 50.0, "H"); b = _pv(40, 44.0, "L"); c = _pv(50, 62.0, "H"); d = _pv(54, 52.0, "L")
    assert _classify(a, b, c, d, 0.2, 1.0) == "BEAR"


def test_crossing_rejects_diverging_bear():
    # valid ordering, but rail 1-3 steeper than 2-4 -> they cross in the PAST -> diverge -> reject.
    a = _pv(0, 50.0, "H"); b = _pv(10, 44.0, "L"); c = _pv(50, 80.0, "H"); d = _pv(52, 46.0, "L")
    assert _classify(a, b, c, d, 0.2, 1.0) is None


def test_crossing_rejects_parallel_rails():
    # rails exactly parallel (both slope 0.4) -> never intersect -> reject.
    a = _pv(0, 50.0, "H"); b = _pv(10, 45.0, "L"); c = _pv(50, 70.0, "H"); d = _pv(60, 65.0, "L")
    assert _classify(a, b, c, d, 0.2, 1.0) is None


def test_crossing_admits_converging_bull():
    # falling-wedge mirror: rails 1-3 (lows) & 2-4 (highs) both fall, 2-4 steeper down -> meet ahead.
    a = _pv(0, 60.0, "L"); b = _pv(40, 66.0, "H"); c = _pv(50, 48.0, "L"); d = _pv(54, 58.0, "H")
    assert _classify(a, b, c, d, 0.2, 1.0) == "BULL"


# --- OPEN TRADES "remaining ROI" view (2026-07-12, S121/D120) -----------------
# Regression guards for the additive open_scan/persist/filter layer. The persist
# round-trip test in particular guards the 27-vs-29 bind-count bug that an empty-rows
# smoke test cannot catch (executemany over [] never validates bindings).
from src.automation import wolfe as _W


def _open_row(**kw):
    r = {"sym": "RELIANCE", "dir": "BULL", "cmp": 1400.0, "zlo": 1380.0, "zhi": 1410.0,
         "zprice": 1395.0, "sl": 1375.0, "t1": 1450.0, "epa": 1600.0, "up": 14.6,
         "age": 8, "Q": 19.0, "run": 14.3, "risk": 1.8, "rr": 7.94, "invalid": False,
         "in_zone": True, "p5date": "2026-07-01", "p4date": "2026-06-20",
         "comp": {"p1": 2, "B": 2}, "size": "N50", "rs": 72, "psector": "Energy",
         "tv_cr": 1095.0, "deliv_pct": 56.0, "tags": ["Energy", "Oil & Gas"]}
    r.update(kw)
    return r


def test_open_metrics_bull_and_bear_symmetric():
    assert _W.open_metrics(100.0, 130.0, 90.0, True) == {"run": 30.0, "risk": 10.0, "rr": 3.0}
    assert _W.open_metrics(100.0, 70.0, 110.0, False) == {"run": 30.0, "risk": 10.0, "rr": 3.0}


def test_open_metrics_below_stop_rr_none():
    # price through the stop -> risk% <= 0 -> R:R undefined (never a divide/negative rr)
    assert _W.open_metrics(100.0, 130.0, 105.0, True)["rr"] is None
    assert _W.open_metrics(None, 1, 1, True) == {"run": None, "risk": None, "rr": None}


def test_filter_open_rows_each_filter():
    rows = [_open_row(sym="A", size="N50", tags=["Pharma"], tv_cr=50.0, rr=4.0, run=40.0, dir="BULL", in_zone=True, invalid=False, age=5, Q=20.0),
            _open_row(sym="B", size="Mid150", tags=["IT"], tv_cr=2.0, rr=0.5, run=15.0, dir="BEAR", in_zone=False, invalid=False, age=40, Q=12.0),
            _open_row(sym="C", size="Small250", tags=["Defence"], tv_cr=100.0, rr=None, run=80.0, dir="BULL", in_zone=True, invalid=True, age=90, Q=25.0)]
    S = lambda **k: sorted(r["sym"] for r in _W.filter_open_rows(rows, **k))
    assert S(size="N50") == ["A"]
    assert S(sector="IT") == ["B"]
    assert S(direction="bear") == ["B"]
    assert S(minliq="5") == ["A", "C"]           # B (₹2cr) excluded
    assert S(minrr="2") == ["A"]                  # B rr0.5 out, C rr None out
    assert S(minroom="30") == ["A", "C"]          # run >= 30
    assert S(maxage="15") == ["A"]                # age <= 15
    assert S(status="in") == ["A"]               # C is in_zone but invalid -> excluded
    assert [r["sym"] for r in _W.filter_open_rows(rows, minq="top20")][:3] == ["C", "A", "B"]  # by Q desc


def test_sort_open_rows_invalid_sinks_last():
    rows = [_open_row(sym="OK", run=10.0, rr=1.0, Q=5.0, age=3, invalid=False, in_zone=False),
            _open_row(sym="BAD", run=99.0, rr=None, Q=99.0, age=1, invalid=True, in_zone=False)]
    for s in ("run", "rr", "q", "age"):
        assert [r["sym"] for r in _W.sort_open_rows(rows, s)][-1] == "BAD"


def test_persist_open_scan_roundtrip_binds_all_columns(monkeypatch):
    # guards the bind-count blocker: 3 real rows must persist WITHOUT ProgrammingError
    # and read back with scan_date/computed_at/held_out + every enriched field intact.
    import sqlite3
    monkeypatch.setattr(_W, "open_scan", lambda conn, universe="nifty500": ([
        _open_row(),
        _open_row(sym="TIRUPATIFL", size="Small250", tv_cr=3.4, tags=["Financial Services"], in_zone=False, rr=11.5),
        _open_row(sym="BLOWN", invalid=True, rr=None, in_zone=False)], 7))     # 7 held out
    conn = sqlite3.connect(":memory:")
    n, _sd, held = _W.persist_open_scan(conn, universe="u", computed_at="2026-07-12 23:30:00")
    assert n == 3 and held == 7
    got = _W.latest_open_scan(conn, universe="u")
    assert got is not None and len(got["rows"]) == 3
    assert got["computed_at"] == "2026-07-12 23:30:00" and got["held_out"] == 7
    r = next(x for x in got["rows"] if x["sym"] == "RELIANCE")
    assert r["run"] == 14.3 and r["rr"] == 7.94 and r["size"] == "N50"
    assert r["tv_cr"] == 1095.0 and r["tags"] == ["Energy", "Oil & Gas"] and r["comp"] == {"p1": 2, "B": 2}
    assert next(x for x in got["rows"] if x["sym"] == "BLOWN")["invalid"] is True


def test_open_rr_display_cap():
    from src.web import wolfe_trades_view as TV
    assert TV._rr_disp(4.0) == "4.00"
    assert TV._rr_disp(250.0) == f"&gt;{_W._RR_DISPLAY_CAP:.0f}"    # razor-risk artifact clamped for display
    assert TV._rr_disp(None) == "—"


def test_open_scan_age_cap_and_coherence(monkeypatch):
    # open_scan must HOLD OUT (count, not rank) waves older than the cap OR with an
    # incoherent target (epa<=0 / wrong side of the stop). Build 3 synthetic waves.
    from types import SimpleNamespace as _NS

    def _wv(direction, p5idx, epa_slope):
        p = [_NS(idx=0, price=100.0, kind="L"), _NS(idx=5, price=120.0, kind="H"),
             _NS(idx=8, price=95.0, kind="L"), _NS(idx=12, price=118.0, kind="H")]
        return _NS(direction=direction, state="CONFIRMED",
                   p5=_NS(idx=p5idx, price=90.0, kind="L"), p=p, epa_slope=epa_slope,
                   score={"total": 15, "p1": 2, "B": 2, "C": 3, "F": 2, "G": 1, "H": 2, "I": 2, "D": 1})
    n = 400
    # wave A: fresh (p5 near the end), sane upward EPA -> RANKED
    wa = _wv("BULL", n - 10, 2.0)
    # wave B: ancient p5 (age huge) -> HELD OUT by the age cap
    wb = _wv("BULL", 20, 2.0)
    # wave C: fresh but epa slope negative -> epa<=0 far out -> incoherent -> HELD OUT
    wc = _wv("BULL", n - 8, -50.0)
    monkeypatch.setattr(_W, "scan_universe", lambda conn, universe: ["X"])
    monkeypatch.setattr(_W, "stock_series", lambda conn, sym: (
        [f"d{i}" for i in range(n)], [100.0] * n, [130.0] * n, [80.0] * n, [110.0] * n))
    monkeypatch.setattr(_W, "detect_waves", lambda h, l, c: ([wa, wb, wc], None))
    monkeypatch.setattr(_W, "is_winner_profile", lambda s: True)
    monkeypatch.setattr(_W, "epa_touched", lambda w, h, l, n: False)
    monkeypatch.setattr(_W, "fib_zones", lambda *a, **k: (None, None, [{"low": 108.0, "high": 112.0, "price": 110.0, "r12": 2.618, "r34": 4.618}]))
    monkeypatch.setattr(_W, "t1_confluence", lambda p, d: None)
    monkeypatch.setattr(_W, "enrich_open_rows", lambda conn, rows: rows)
    ranked, held = _W.open_scan(None, universe="nifty500")
    assert held == 2 and len(ranked) == 1        # B (ancient) + C (incoherent) held out; only A ranked
    assert ranked[0]["age"] <= _W._OPEN_MAX_AGE_BARS and ranked[0]["epa"] > 0


def test_bottom_line_standout_guards_reject_razor_and_thin():
    from src.web import wolfe_trades_view as TV
    rows = [
        _open_row(sym="RAZOR", rr=99.0, run=20.0, risk=0.2, tv_cr=200.0),      # risk too thin -> not best-rr
        _open_row(sym="THIN", rr=6.0, run=80.0, risk=8.0, tv_cr=1.0),          # illiquid -> excluded from standouts
        _open_row(sym="GOOD", rr=4.0, run=30.0, risk=7.5, tv_cr=90.0)]         # the tradeable representative
    band = TV._bottom_line(rows, 3, held_out=536)
    assert "Best risk-adjusted" in band and "sym=GOOD" in band       # GOOD wins, not RAZOR
    assert "RAZOR" not in band.split("Best risk-adjusted")[1].split(".")[0]   # RAZOR not the headline
    assert "held out" in band and "536" in band                      # held-out disclosed


def test_open_trades_csv_export_shape_and_filters():
    # the CSV export is server-side and honors the same rows it is handed (the view
    # filters/sorts upstream); guard the header + row shape + filter-honesty here.
    from src.web import wolfe_trades_view as TV
    rows = [_open_row(sym="AAA", tags=["Pharma"], tv_cr=50.0),
            _open_row(sym="BBB", tags=["IT"], tv_cr=2.0, dir="BEAR", rr=3.0)]
    resp = TV._csv_response(rows, "2026-07-10")
    body = resp.body.decode()
    assert resp.media_type == "text/csv"
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    head = body.splitlines()[0]
    assert head.startswith("symbol,direction,sector_tags,size,cmp") and head.endswith(",as_of")
    assert len([l for l in body.splitlines() if l]) == 3          # header + 2 rows
    aaa = [l for l in body.splitlines() if l.startswith("AAA")][0]
    assert "Pharma" in aaa and ",edge," in aaa and aaa.endswith(",2026-07-10")


def test_open_active_state_only_nondefaults():
    from src.web import wolfe_trades_view as TV
    # all defaults -> empty (a bare view, nothing to remember)
    assert TV._active_state({"universe": "nifty500", "size": "", "sort": "run", "minliq": "any", "status": "all"}) == {}
    # real filters + a non-default sort survive
    assert TV._active_state({"size": "N50", "sort": "rr", "sector": "all", "minrr": "2", "universe": "nifty500"}) == {"size": "N50", "sort": "rr", "minrr": "2"}


def test_open_sticky_cookie_set_and_clear():
    from src.web import wolfe_trades_view as TV
    from fastapi.responses import HTMLResponse

    def _setcookies(resp):
        return [v.decode() for k, v in resp.raw_headers if k == b"set-cookie"]
    # active filters -> the remembered-filters cookie is written with the encoded state
    on = _setcookies(TV._sticky(HTMLResponse("x"), {"size": "N50", "sort": "rr"}, 0))
    assert on and "wolfe_open_filters=" in on[0] and "size" in on[0]
    # clear -> a Set-Cookie that expires it
    off = _setcookies(TV._sticky(HTMLResponse("x"), {}, 1))
    assert off and "wolfe_open_filters=" in off[0]
    # no active filters, no clear -> no cookie churn
    assert _setcookies(TV._sticky(HTMLResponse("x"), {}, 0)) == []


def test_zone_gap_and_proximity_filter():
    row = lambda **k: _open_row(**{"dir": "BULL", "cmp": 100.0, "zlo": 100.0, "zhi": 102.0,
                                   "in_zone": False, "invalid": False, **k})
    assert _W.zone_gap_pct(row(cmp=110.0)) > 0          # BULL above zone (ran up) -> +
    assert _W.zone_gap_pct(row(cmp=96.0)) < 0           # BULL below zone (toward stop) -> -
    assert _W.zone_gap_pct(row(dir="BEAR", cmp=90.0)) > 0   # BEAR below zone (ran down) -> +
    assert _W.zone_gap_pct(row(in_zone=True)) == 0.0
    rows = [row(sym="NEAR", cmp=103.0), row(sym="FAR", cmp=130.0)]   # ~1% vs ~21% above the zone
    got = [r["sym"] for r in _W.filter_open_rows(rows, minprox="5")]
    assert "NEAR" in got and "FAR" not in got


def test_open_growth_helpers():
    from src.web import wolfe_trades_view as TV
    r = lambda **k: _open_row(**{"cmp": 100.0, "t1": 112.0, "risk": 4.0, "atr_pct": 2.0,
                                 "age": 10, "rs": 75, "dir": "BULL", **k})
    # #4 conservative run→T1 (BULL) + BEAR mirror
    assert TV._run_t1(r(cmp=100.0, t1=112.0)) == 12.0
    assert TV._run_t1(r(dir="BEAR", cmp=100.0, t1=88.0)) == 12.0
    assert TV._run_t1(r(t1=None)) is None
    # #5 age-graded muting: young crisp, old muted with '~'
    assert TV._age_mute(10) == ("", "")
    assert TV._age_mute(120)[1] == "~"
    # #6 razor flag when risk% < 0.8×ATR
    assert "razor" in TV._risk_cell(r(risk=1.0, atr_pct=2.0))       # 0.5×ATR -> razor
    assert "razor" not in TV._risk_cell(r(risk=6.0, atr_pct=2.0))   # 3×ATR -> fine
    # #8 RS label
    assert "leader" in TV._rs_cell(r(dir="BULL", rs=85))
    assert "counter-trend" in TV._rs_cell(r(dir="BULL", rs=20))
    # #10 staleness only when the snapshot lags the data
    assert TV._staleness_banner("2024-09-01", "2024-10-04") != ""
    assert TV._staleness_banner("2024-10-04", "2024-10-04") == ""
    # #11 ladder renders an svg
    assert "<svg" in TV._ladder(r()) and "circle" in TV._ladder(r())
    # #12 seen fingerprint round-trip (hashed keys) + cookie stays under the ~4KB limit
    rows = [_open_row(sym="A", p5date="d1", in_zone=True), _open_row(sym="B", p5date="d2", invalid=True)]
    d = TV._parse_seen(TV._seen_str(rows))
    assert d[TV._seen_key(rows[0])] == "I" and d[TV._seen_key(rows[1])] == "X"
    big = [_open_row(sym=f"SYMBOL{i:04d}", p5date="2026-07-01", in_zone=(i % 2 == 0)) for i in range(200)]
    assert len(TV._seen_str(big)) < 3500      # 200 rows must fit well under the 4096-byte cookie ceiling


def test_min_rs_filter():
    rows = [_open_row(sym="HI", rs=80), _open_row(sym="LO", rs=20)]
    assert [x["sym"] for x in _W.filter_open_rows(rows, minrs="50")] == ["HI"]
