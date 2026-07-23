"""test_v3_today.py — the M5 landing gate (spec §4/§5).

Structure-level contracts that must hold on ANY database state (sparse dev DB included):
anatomy order · visible tile subtitles + links · flagship band = 4 provenance cards ·
fence + demo-framing present · what-changed rows sym-linked when data exists · payload
budget · toggle relocated but never hidden · no legacy leak · nav contract on the landing.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def _app():
    from src.main import app
    return app


def test_today_is_the_landing_focus_with_nav_contract():
    client = TestClient(_app())
    r = client.get("/dash/preview")
    assert r.status_code == 200
    t = r.text
    assert "never what to buy" in t                      # the identity sentence
    assert "Why this is different" in t and t.count('<span class="t3-prov"') == 4
    assert "Start here" in t and "/dash/reading-guide" in t and "/dash/pat" in t
    body = t.split("</head>", 1)[1]
    assert 'aria-current="page">Today' in body           # dest bar marks Today
    assert '<nav class="pv3-crumbs"' in body


def test_today_toggle_survives_in_the_rail():
    """Spec §1: the M0 gate function is never hidden — the toggle moved, not vanished."""
    client = TestClient(_app())
    t = client.get("/dash/preview").text
    assert '/dash/preview/toggle' in t and ("Enter the preview" in t or "Leave the preview" in t)
    # and the POST mechanics still work
    assert client.post("/dash/preview/toggle", follow_redirects=False).status_code == 303


def test_today_fence_and_demo_framing_render():
    client = TestClient(_app())
    t = client.get("/dash/preview").text
    assert "pv3-fence" in t
    assert "failures and uncertified" in t or "Why we publish" in t  # ifx.demo_framing copy


def test_today_counts_carry_visible_subtitles_and_links():
    client = TestClient(_app())
    t = client.get("/dash/preview").text
    if 'class="pv3-tile t3-count"' in t:  # data-dependent: any tile that rendered must carry sub + link
        assert t.count("open the lens →") >= 1
        assert "?symbol=" not in t
    else:                # sparse DB → the honest warm-up state, never a fake zero-wall
        assert "warm up" in t


def test_today_what_changed_rows_link_the_hub():
    client = TestClient(_app())
    t = client.get("/dash/preview").text
    assert "What changed" in t
    if '<ul class="t3-feed"' in t:
        assert "/dash/preview/stock?sym=" in t


def test_today_payload_budget():
    client = TestClient(_app())
    r = client.get("/dash/preview")
    assert len(r.content) < 300_000, len(r.content)      # spec §3, uncompressed bytes


def test_today_never_leaks_to_legacy():
    client = TestClient(_app())
    for path in ("/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert "t3-idline" not in r.text and "t3-moat" not in r.text, path


def test_today_typeahead_is_attached():
    """Codex M5 B1: the shared typeahead must ATTACH to the box, not just be included."""
    client = TestClient(_app())
    t = client.get("/dash/preview").text
    assert 'id="t3sug"' in t and 'getElementById("t3sym")' in t and "__symTA(i,s" in t


def test_today_count_tiles_render_honest_zeros():
    """Codex M5 B2: absent tables -> zero tiles, never silently-missing tiles (breadth is the
    documented percentage exception)."""
    from src.web.today_v3 import _counts
    subs = [c[2] for c in _counts()]
    for must in ("signal bus", "results meetings", "corporate actions", "stock-tagged headlines"):
        assert any(must in s for s in subs), must


def test_today_breadth_tile_reads_the_real_schema():
    """The box schema is d/n_eq/pct_adv (verified 2026-07-23) — the tile must render against
    it; guessed column names caused a silent-missing tile once."""
    import sqlite3
    from unittest.mock import patch
    import contextlib
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE market_internals_daily(d TEXT, n_eq INT, adv INT, dec INT, "
                 "unch INT, pct_adv REAL)")
    conn.execute("INSERT INTO market_internals_daily VALUES('2026-07-23',2340,1428,800,112,61.0)")
    @contextlib.contextmanager
    def fake_conn():
        yield conn
    from src.web import today_v3
    with patch.object(today_v3, "get_conn", fake_conn):
        subs = today_v3._counts()
    assert any("stocks advanced today" in c[2] and c[0] == "61%" for c in subs)


def test_today_mood_uses_the_one_vocabulary():
    """If the mood renders (index data present), it must come from market_mood's banner —
    no second regime vocabulary on the page."""
    client = TestClient(_app())
    t = client.get("/dash/preview").text
    import re
    assert not re.search(r"\b(RISK-OFF|UP-BIASED)\b", t)  # the P0-3 dead vocabularies stay dead
