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
    # and read back with scan_date/computed_at + every enriched field intact.
    import sqlite3
    monkeypatch.setattr(_W, "open_scan", lambda conn, universe="nifty500": [
        _open_row(),
        _open_row(sym="TIRUPATIFL", size="Small250", tv_cr=3.4, tags=["Financial Services"], in_zone=False, rr=11.5),
        _open_row(sym="BLOWN", invalid=True, rr=None, in_zone=False)])
    conn = sqlite3.connect(":memory:")
    n, _sd = _W.persist_open_scan(conn, universe="u", computed_at="2026-07-12 23:30:00")
    assert n == 3
    got = _W.latest_open_scan(conn, universe="u")
    assert got is not None and len(got["rows"]) == 3
    assert got["computed_at"] == "2026-07-12 23:30:00"
    r = next(x for x in got["rows"] if x["sym"] == "RELIANCE")
    assert r["run"] == 14.3 and r["rr"] == 7.94 and r["size"] == "N50"
    assert r["tv_cr"] == 1095.0 and r["tags"] == ["Energy", "Oil & Gas"] and r["comp"] == {"p1": 2, "B": 2}
    assert next(x for x in got["rows"] if x["sym"] == "BLOWN")["invalid"] is True
