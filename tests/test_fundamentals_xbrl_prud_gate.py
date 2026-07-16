"""S155-e residual: the P&L continuity gate must not block a bank's prudential block.

Drives the REAL ingest() loop (gate branch, seen-table sentinel semantics, write_rows)
with the network + extraction layer monkeypatched. Invariants under test:
  1. a gate-HELD bank writes ONLY its prudential metrics (never P&L);
  2. the prud-only pass marks its own sentinel, NEVER the real xml_url — so
  3. a later regate to PASS still ingests the full P&L from the same filing;
  4. the prud-only pass runs once (second run = skipped_seen, zero new fetches);
  5. a gate-held NON-bank writes nothing (sentinel only, one fetch ever);
  6. a budget-DEFERRED (unknown-verdict) symbol is not fetched at all;
  7. the Integrated-Filing path honors the same contract (incl. gate-pass parity).
"""
import os
import sqlite3
import tempfile

from src.automation import fundamentals_xbrl as fx

PNL = {"Revenue": 100.0, "Net Profit": 10.0}
PRUD = {"Gross NPA %": 1.42, "CET1 %": 19.97}


def _rdb(td):
    p = os.path.join(td, "r.db")
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, "
                "period_end TEXT, report_date TEXT, metric TEXT, value REAL, "
                "PRIMARY KEY(symbol,period_type,period_end,metric))")
    fx._ensure_source_column(con)          # + gate/seen/restatements DDL
    con.commit()
    con.close()
    return p


def _gate(p, sym, ok):
    con = sqlite3.connect(p)
    con.execute("INSERT OR REPLACE INTO fundamentals_xbrl_gate VALUES (?,datetime('now'),?,?)",
                (sym, int(ok), "test"))
    con.commit()
    con.close()


def _filing(sym, url, *, bank=True):
    return {"symbol": sym, "period": "Quarterly", "to_date": "2026-03-31",
            "xbrl_url": url, "broadcast": "2026-04-20T18:00:00", "consolidated": False,
            "cumulative": False, "bank": "Y" if bank else "N", "revised": False}


def _bank_parsed(pnl=PNL, prud=PRUD, meta=None):
    return {"contexts": {}, "meta": dict(meta or {}),
            "facts": [("InterestEarned", "OneD", "1.0")],
            "_pnl": dict(pnl), "_prud": dict(prud)}


def _nonbank_parsed(pnl=PNL, meta=None):
    return {"contexts": {}, "meta": dict(meta or {}),
            "facts": [("RevenueFromOperations", "OneD", "1.0")],
            "_pnl": dict(pnl), "_prud": {}}


class Net:
    """fetch_instance stand-in: returns the url itself; parse_instance resolves it."""

    def __init__(self, parsed_by_url):
        self.parsed_by_url = parsed_by_url
        self.fetches = []

    def fetch(self, url, **kw):
        self.fetches.append(url)
        return url

    def parse(self, key):
        return self.parsed_by_url[key]


def _wire(monkeypatch, net, filings, if_rows=()):
    monkeypatch.setattr(fx, "_nse_session", lambda: (None, {}))
    monkeypatch.setattr(fx, "REQUEST_PAUSE", 0)
    monkeypatch.setattr(fx, "list_filings",
                        lambda **kw: [dict(f) for f in filings
                                      if f["period"] == kw.get("period")
                                      and ("symbol" not in kw or kw["symbol"] == f["symbol"])])
    monkeypatch.setattr(fx, "list_integrated_filings",
                        lambda **kw: [dict(r) for r in if_rows
                                      if "symbol" not in kw or kw["symbol"] == r["symbol"]])
    monkeypatch.setattr(fx, "fetch_instance", net.fetch)
    monkeypatch.setattr(fx, "parse_instance", net.parse)
    monkeypatch.setattr(fx, "extract_metrics",
                        lambda parsed, filing: dict(parsed.get("_pnl") or {}))
    monkeypatch.setattr(fx, "extract_for",
                        lambda parsed, *, kind, end: dict(parsed.get("_pnl") or {}))
    monkeypatch.setattr(fx, "augment_prudential",
                        lambda parsed, *, kind, end, sa_lookup=None: dict(parsed.get("_prud") or {}))
    monkeypatch.setattr(fx, "extract_bank_prudential",
                        lambda parsed, *, kind, end: dict(parsed.get("_prud") or {}))
    monkeypatch.setattr(fx.provenance, "observe", lambda *a, **k: None)


def _ingest(rdb, sym):
    return fx.ingest(since="2026-04-01", until="2026-04-30", symbols=[sym], research_db=rdb)


def _rows(p):
    con = sqlite3.connect(p)
    out = con.execute("SELECT symbol, metric, value, source FROM fundamentals_history "
                      "ORDER BY metric").fetchall()
    con.close()
    return out


def _seen(p):
    con = sqlite3.connect(p)
    out = sorted(r[0] for r in con.execute(
        "SELECT xml_url FROM fundamentals_xbrl_seen").fetchall())
    con.close()
    return out


def test_gate_held_bank_writes_prudential_only(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)
        _gate(rdb, "HELDBANK", 0)
        net = Net({"u1": _bank_parsed()})
        _wire(monkeypatch, net, [_filing("HELDBANK", "u1")])
        s = _ingest(rdb, "HELDBANK")
        assert s["prud_only_filings"] == 1 and s["rows"] == len(PRUD)
        got = _rows(rdb)
        assert {m for _s, m, _v, _src in got} == set(PRUD)          # NO P&L rows
        assert all(src == fx.SOURCE_SA for *_x, src in got)          # SA nature stamped
        assert _seen(rdb) == ["u1" + fx.PRUD_ONLY_SENTINEL]          # real url stays open


def test_prud_only_pass_runs_once(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)
        _gate(rdb, "HELDBANK", 0)
        net = Net({"u1": _bank_parsed()})
        _wire(monkeypatch, net, [_filing("HELDBANK", "u1")])
        _ingest(rdb, "HELDBANK")
        n_fetches = len(net.fetches)
        s2 = _ingest(rdb, "HELDBANK")
        assert len(net.fetches) == n_fetches                         # zero new fetches
        assert s2["skipped_seen"] == 1 and s2["prud_only_filings"] == 0
        assert len(_rows(rdb)) == len(PRUD)                          # nothing duplicated


def test_regate_after_prud_only_ingests_pnl(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)
        _gate(rdb, "HELDBANK", 0)
        net = Net({"u1": _bank_parsed()})
        _wire(monkeypatch, net, [_filing("HELDBANK", "u1")])
        _ingest(rdb, "HELDBANK")
        _gate(rdb, "HELDBANK", 1)                                    # manual regate → PASS
        s = _ingest(rdb, "HELDBANK")
        assert s["parsed"] == 1 and s["prud_only_filings"] == 0
        metrics = {m for _s, m, _v, _src in _rows(rdb)}
        assert metrics == set(PNL) | set(PRUD)                       # P&L landed after all
        assert "u1" in _seen(rdb)                                    # now fully seen


def test_gate_held_nonbank_writes_nothing(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)
        _gate(rdb, "HELDCO", 0)
        net = Net({"u2": _nonbank_parsed()})
        _wire(monkeypatch, net, [_filing("HELDCO", "u2", bank=False)])
        s = _ingest(rdb, "HELDCO")
        assert s["prud_only_filings"] == 0 and s["rows"] == 0
        assert _rows(rdb) == []
        assert _seen(rdb) == ["u2" + fx.PRUD_ONLY_SENTINEL]          # once-only, deterministic
        s2 = _ingest(rdb, "HELDCO")
        assert len(net.fetches) == 1 and s2["skipped_seen"] == 1


def test_deferred_symbol_not_fetched(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)                                               # NO gate verdict cached
        net = Net({"u3": _bank_parsed()})
        _wire(monkeypatch, net, [_filing("NEWBANK", "u3")])
        monkeypatch.setattr(fx, "GATE_BUDGET_PER_RUN", 0)            # force the deferral path
        s = _ingest(rdb, "NEWBANK")
        assert s["gate_deferred"] == 1
        assert net.fetches == [] and _rows(rdb) == [] and _seen(rdb) == []


def _if_row(sym, url):
    return {"symbol": sym, "xbrl_url": url, "broadcast": "2026-04-20T18:00:00",
            "revised": False, "qe_date": "2026-03-31"}


_IF_META = {"DateOfEndOfReportingPeriod": "2026-03-31",
            "NatureOfReportStandaloneConsolidated": "Standalone",
            "DateOfEndOfFinancialYear": "2025-03-31"}


def test_integrated_filing_path_gate_held_bank(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)
        _gate(rdb, "HELDBANK", 0)
        net = Net({"i1": _bank_parsed(meta=_IF_META)})
        _wire(monkeypatch, net, [], if_rows=[_if_row("HELDBANK", "i1")])
        s = _ingest(rdb, "HELDBANK")
        assert s["prud_only_filings"] == 1 and s["rows"] == len(PRUD)
        got = _rows(rdb)
        assert {m for _s, m, _v, _src in got} == set(PRUD)
        assert all(src == fx.SOURCE_SA for *_x, src in got)          # disclosing SA stamped
        assert _seen(rdb) == ["i1" + fx.PRUD_ONLY_SENTINEL]
        s2 = _ingest(rdb, "HELDBANK")
        assert len(net.fetches) == 1 and s2["skipped_seen"] == 1     # once-only here too


def test_integrated_filing_path_gate_pass_parity(monkeypatch):
    """Regression guard on the refactor: a gate-PASSING symbol's IF flow is unchanged —
    P&L + prudential merged, the REAL url marked seen."""
    with tempfile.TemporaryDirectory() as td:
        rdb = _rdb(td)
        _gate(rdb, "GOODBANK", 1)
        net = Net({"i2": _bank_parsed(meta=_IF_META)})
        _wire(monkeypatch, net, [], if_rows=[_if_row("GOODBANK", "i2")])
        s = _ingest(rdb, "GOODBANK")
        assert s["parsed"] == 1 and s["prud_only_filings"] == 0
        metrics = {m for _s, m, _v, _src in _rows(rdb)}
        assert metrics == set(PNL) | set(PRUD)
        assert _seen(rdb) == ["i2"]
