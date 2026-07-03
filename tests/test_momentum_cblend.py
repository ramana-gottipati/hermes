"""Regression test for the C-BLEND 50/50 sort on /dash/momentum-scan (queue #5 consumption).

The S77b backtest verdict (docs/strategy-ledger.md § Experiment 2026-07-03): fold Dataset-C in as a
50/50 rank BLEND on the momentum surface (new best overlay — Sharpe 1.32 / Calmar 1.15 / MaxDD
-28.2%), NOT a hard veto, NOT a filter, NOT a standalone ranker. This pins that the C-blend sort =
mean(RISKADJ pctile, capital-allocation ca_pctile), neutral-fills a missing C at the 50th percentile,
and re-orders by it — while the other sorts are unaffected. Monkeypatches the DB reader (no live DB).
"""
import sqlite3

import pytest

pytest.importorskip("fastapi")          # the view module is built on FastAPI
import src.web.momentum_view as MV      # noqa: E402


def _fake_ro(_path):
    c = sqlite3.connect(":memory:")
    c.executescript(
        "CREATE TABLE momentum_scan(as_of TEXT,symbol TEXT,mom6 REAL,mom12 REAL,vol_66 REAL,"
        "riskadj REAL,range_pos_252 REAL,turnover_cr REAL,riskadj_pctile REAL,ensemble_pctile REAL);"
        "CREATE TABLE capital_allocation_scores(symbol TEXT,as_of TEXT,ca_pctile REAL,ca_tier TEXT);"
        "CREATE TABLE insider_events(symbol TEXT,signal_class TEXT);"
        "CREATE TABLE credit_rating_events(symbol TEXT,action_class TEXT,below_investment_grade INT);")
    # AHI: strong momentum (riskadj pctile 90) but POOR capital allocation (C 10) -> cblend 50
    # BLO: modest momentum (20) but EXCELLENT capital allocation (C 95)          -> cblend 57.5
    # NOC: no capital_allocation row -> neutral 50                               -> cblend 50
    c.execute("INSERT INTO momentum_scan VALUES ('2026-07-02','AHI',0.3,0.5,0.2,2.0,0.9,100,90,80)")
    c.execute("INSERT INTO momentum_scan VALUES ('2026-07-02','BLO',0.1,0.2,0.3,1.0,0.5,80,20,60)")
    c.execute("INSERT INTO momentum_scan VALUES ('2026-07-02','NOC',0.2,0.3,0.25,1.5,0.7,90,50,70)")
    c.execute("INSERT INTO capital_allocation_scores VALUES ('AHI','2026-07-02',10,'WEAK')")
    c.execute("INSERT INTO capital_allocation_scores VALUES ('BLO','2026-07-02',95,'EXCELLENT')")
    return c


def _html(monkeypatch, sort):
    monkeypatch.setattr(MV, "_ro", _fake_ro)
    return MV.momentum_scan_page(sort=sort).body.decode()


def test_cblend_column_and_control(monkeypatch):
    html = _html(monkeypatch, "cblend")
    assert "C-blend" in html and "sort=cblend" in html


def test_cblend_reranks_by_blend(monkeypatch):
    # BLO (57.5) must rank above AHI (50) under C-blend, though AHI has far higher raw RISKADJ —
    # the capital-allocation half is doing real work (the whole point of the overlay).
    html = _html(monkeypatch, "cblend")
    assert html.index(">BLO<") < html.index(">AHI<")


def test_missing_c_is_neutral_not_dropped(monkeypatch):
    # NOC has no capital_allocation row -> neutral 50, NOT excluded. The blend only tilts, never filters.
    assert ">NOC<" in _html(monkeypatch, "cblend")


def test_other_sorts_unaffected(monkeypatch):
    # riskadj sort still orders by raw RISKADJ (AHI 2.0 first); the C-blend is opt-in.
    html = _html(monkeypatch, "riskadj")
    assert html.index(">AHI<") < html.index(">BLO<")
