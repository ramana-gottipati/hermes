"""test_home_pat_a11y.py — the floating-Pat accessibility gate (Codex #4/#5, spec §6/§7).

The dialog must be a real dialog: labelled, `aria-modal`, `inert` when closed, focus moved in on
open and back to the trigger on close, Escape to close. Answers/bubbles are data-bound + escaped.
"""
from __future__ import annotations

import sqlite3

from src.web.home import pat_dock


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


def test_pat_dock_has_real_dialog_a11y():
    html = pat_dock.dock_html(_conn())
    assert 'role="dialog"' in html and 'aria-modal="true"' in html and 'aria-label="Pat — your guide"' in html
    assert "inert>" in html                                  # panel starts inert (closed)
    assert 'aria-expanded="false"' in html and 'aria-controls="g-pat-panel"' in html
    assert 'aria-label="Open Pat' in html and 'aria-label="Close Pat"' in html


def test_pat_js_manages_focus_escape_and_inert():
    html = pat_dock.dock_html(_conn())
    for token in ('e.key==="Escape"', 'removeAttribute("inert")', 'setAttribute("inert"',
                  "fab.focus()", "input.focus()"):
        assert token in html, token


def test_pat_answers_and_bubbles_are_data_bound():
    c = _conn()
    c.execute("CREATE TABLE fii_dii_flows(trade_date TEXT,category TEXT,buy_value REAL,"
              "sell_value REAL,net_value REAL,fetched_at TEXT,UNIQUE(trade_date,category))")
    c.execute("INSERT INTO fii_dii_flows(trade_date,category,net_value) VALUES ('2026-07-23','DII',860)")
    html = pat_dock.dock_html(c)
    assert "DII net bought" in html                          # real read -> bubble/answer, not canned
    # closed-vocab suggestions (labels are html-escaped, e.g. Who&#x27;s buying?)
    assert "What is DVPT?" in html and "buying?" in html


def test_pat_answers_calibrate_terse_title_plus_detail_on_demand():
    """Response-format calibration: every answer leads with a one-line TITLE; explain-answers carry
    a 'more' expander (detail on demand); the typed box classifies the question and can deep-link a
    symbol instead of always echoing the same canned block."""
    html = pat_dock.dock_html(_conn())
    assert "g-pat-a-title" in html and 'class="g-pat-more"' in html
    # POST-CUTOVER (2026-07-27): the dock's symbol chip deep-links the GRAPHITE stock page — the
    # Graphite estate must be self-contained now that /dash/home IS the landing (D148).
    # This pins the dock specifically; the PACKAGE-WIDE contract lives in test_home_isolation.py.
    for tok in ("function classify(", "function symToken(", "/dash/home/stock?sym="):
        assert tok in html, tok
    assert '"/dash/stock?sym="' not in html, "the dock must not eject a reader into classic chrome"


def test_pat_renders_defensively_on_empty_db():
    assert pat_dock.dock_html(_conn())                       # never raises; renders a fallback
