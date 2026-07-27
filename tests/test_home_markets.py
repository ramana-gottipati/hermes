"""test_home_markets.py — the gate for the Graphite Markets estate (cutover wave W2-B).

Covers the three consolidated pages that replace eleven classic Markets lenses:

    /dash/home/rotation  ?view=journeys|weather|band|clock   (rrg · rotation · rsband · cycle-clock)
    /dash/home/strength  ?view=overview|leaders|momentum|capture
                                          (rs-hub · leaders · momentum-scan · capture-map)
    /dash/home/sectors   ?tab=standing|economics  ?sec=      (sectors · sector-economics ·
                                                              sector-momentum)

What it pins, beyond "it returns 200":
  * every view is URL-addressable and an unknown value degrades to the default, never a 404/500;
  * the pages carry the Graphite marker and none of the preview/legacy markers (the isolation
    contract, restated for the new routes);
  * the lane's modules import no classic view module (the reason the isolation gate exists);
  * symbols link `?sym=`, never `?symbol=`;
  * the rsband engine's instructional verdict KEYS (Ride/Fade/Trim/Accumulate/Avoid) never reach
    the DOM — only its descriptive state labels, per that engine's own rule;
  * every read degrades to empty on a bare database instead of raising;
  * every PORTED disposition this lane recorded points at a route that actually serves.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
LANE_MODULES = ("markets_reads.py", "markets_ui.py", "rotation_pages.py", "strength_pages.py",
                "sectors_pages.py")

ROTATION_VIEWS = ("journeys", "weather", "band", "clock")
STRENGTH_VIEWS = ("overview", "leaders", "momentum", "capture")

PREVIEW_LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')

# the classic RENDER modules this lane must never import (a superset of the isolation gate's list,
# narrowed to the ones whose engines it would have been tempting to borrow)
BANNED_VIEWS = ("dashboard", "cockpit", "rrg_view", "rsband_view", "cycle_clock", "capture_map",
                "momentum_view", "momentum_pane", "rs_section", "sector_econ_view",
                "sector_momentum", "rotation_view", "mini_rrg", "infographics", "shell_skin",
                "left_rail", "glossary")


def _client():
    from src.main import app
    return TestClient(app)


def _paths():
    out = []
    for v in ROTATION_VIEWS:
        out.append("/dash/home/rotation" + ("" if v == "journeys" else "?view=" + v))
    for v in STRENGTH_VIEWS:
        out.append("/dash/home/strength" + ("" if v == "overview" else "?view=" + v))
    out += ["/dash/home/sectors", "/dash/home/sectors?tab=economics",
            "/dash/home/sectors?sec=Nifty%20IT", "/dash/home/strength?view=capture&h=252"]
    return out


# ── routes ────────────────────────────────────────────────────────────────────────────
def test_every_markets_view_serves_in_graphite_chrome():
    c = _client()
    for p in _paths():
        r = c.get(p)
        assert r.status_code == 200, (p, r.status_code)
        assert "data-ui-g" in r.text, p
        for m in PREVIEW_LEGACY_MARKERS:
            assert m not in r.text, (p, "leaked a preview/legacy marker", m)


def test_unknown_view_values_degrade_to_the_default_never_error():
    """A hand-edited or stale URL must land on the page, not a 404/500 — the view is a display
    choice, not a resource identity."""
    c = _client()
    for p in ("/dash/home/rotation?view=nonsense", "/dash/home/strength?view=../../etc",
              "/dash/home/sectors?tab=%3Cscript%3E", "/dash/home/strength?view=capture&h=999",
              "/dash/home/sectors?tab=economics&metric=zzz"):
        r = c.get(p)
        assert r.status_code == 200, (p, r.status_code)
        assert "<script>x" not in r.text and "&lt;script&gt;" not in r.text.split("</head>")[0], p


def test_each_rotation_view_renders_its_own_evidence():
    c = _client()
    want = {"journeys": "g-rot-maps", "weather": "Just turned", "band": "Regime",
            "clock": "g-mclock"}
    for v, needle in want.items():
        p = "/dash/home/rotation" + ("" if v == "journeys" else "?view=" + v)
        t = c.get(p).text
        assert needle in t, (p, "missing its distinguishing block", needle)
        assert 'class="g-mtab on"' in t, (p, "the view switcher lost its active state")


def test_each_strength_view_renders_its_own_evidence():
    c = _client()
    want = {"overview": "Four ways to read one question", "leaders": "Laggards",
            "momentum": "risk", "capture": "Took of the falls"}
    for v, needle in want.items():
        p = "/dash/home/strength" + ("" if v == "overview" else "?view=" + v)
        t = c.get(p).text
        assert needle in t, (p, "missing its distinguishing block", needle)


def test_sectors_tabs_and_drilldown():
    c = _client()
    st = c.get("/dash/home/sectors").text
    assert "Members beating the market" in st
    ec = c.get("/dash/home/sectors?tab=economics").text
    assert "What the businesses earn" in ec and "What the strength cost" in ec
    dr = c.get("/dash/home/sectors?sec=Nifty%20IT").text
    assert "Inside IT" in dr and "back to all sectors" in dr


def test_symbols_link_sym_never_symbol():
    """`?sym=`, never `?symbol=` — on every page; and the views that always carry names must
    actually emit the deep link (a page that silently stopped linking symbols would otherwise pass
    the ban trivially)."""
    c = _client()
    for p in _paths():
        assert "?symbol=" not in c.get(p).text, (p, "used the wrong symbol param")
    for p in ("/dash/home/strength?view=leaders", "/dash/home/strength"):
        t = c.get(p).text
        assert re.search(r'href="/dash/home/stock\?sym=[A-Z0-9&.\-]+"', t), (p, "no sym deep-link")


def test_pages_carry_a_descriptive_fence_and_no_canvas():
    c = _client()
    for p in _paths():
        t = c.get(p).text
        assert "<canvas" not in t, (p, "an animated canvas is not the Graphite idiom")
        assert "Descriptive" in t or "descriptive" in t, (p, "no honesty fence on the page")


def test_the_band_engine_verdict_keys_never_reach_the_dom():
    """`rsband.band_verdict` returns a machine KEY (Ride / Fade / Trim / Accumulate / Avoid) beside
    a descriptive state label. That engine's own rule is that the key is internal — RS-band is a
    relative-level description, not an instruction. Only the label may render."""
    c = _client()
    t = c.get("/dash/home/rotation?view=band").text
    body = t.split("</head>", 1)[-1]
    for verb in (">Ride<", ">Fade<", ">Trim<", ">Accumulate<", ">Avoid<", ">Hold<"):
        assert verb not in body, ("an instructional verdict key leaked into the DOM", verb)


# ── isolation ─────────────────────────────────────────────────────────────────────────
def test_lane_modules_import_no_classic_render_module():
    """The whole point of the isolated package: reuse the ENGINE (src/automation/…), never the
    classic VIEW. A view import would drag the frozen classic chrome into Graphite."""
    offenders = []
    for name in LANE_MODULES:
        p = ROOT / "src" / "web" / "home" / name
        assert p.exists(), name
        text = p.read_text(encoding="utf-8", errors="replace")
        for mod in BANNED_VIEWS:
            if re.search(r"^\s*(from|import)\s+[\w.]*\b" + mod + r"\b", text, re.M):
                offenders.append(name + " -> " + mod)
    assert not offenders, offenders


def test_the_markets_routes_are_route_gate_registered():
    from tests import test_dash_route_registry as gate
    for path in ("/dash/home/strength", "/dash/home/sectors", "/dash/home/rotation"):
        assert path in gate.INTERNAL_DEV, path
        owner, rationale = gate.INTERNAL_DEV[path]
        assert owner and len(rationale) > 40, path


# ── reads ─────────────────────────────────────────────────────────────────────────────
def test_every_read_degrades_to_empty_on_a_bare_database():
    """A page must never 500 because a nightly job hasn't run. Each read returns an empty result on
    a database with none of its tables."""
    from src.web.home import markets_reads as R
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    assert R.sector_weather(conn) == []
    assert R.band_lanes(conn) == []
    assert R.clock_dots(conn) == []
    assert R.capture_map(conn) == []
    assert R.riskadj_scan(conn) == []
    assert R.rs_standing(conn) == []
    assert R.rs_counts(conn) == {}
    assert R.sector_breadth(conn) == []
    assert R.sector_members(conn, "Nifty IT") == []
    assert R.sector_risk_economics(conn) == []
    assert R.sector_fundamentals(conn) == {}


def test_capture_horizon_is_clamped_before_it_can_reach_a_column_name():
    """`capture_map` builds a column name from the horizon — the clamp is the injection fence."""
    from src.web.home import markets_reads as R
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for bad in ("63; DROP TABLE capture_signals", "../../x", "", None, "999"):
        assert R.capture_map(conn, horizon=bad) == []


def test_demo_fallbacks_are_shaped_like_the_live_reads():
    """Demo data must be substitutable for the live rows — a fallback with a different shape would
    fail only in production, on the day the real read goes empty."""
    from src.web.home import markets_reads as R
    for rows, keys in ((R.DEMO_WEATHER, ("label", "phase", "s1", "s3", "s6", "s12")),
                       (R.DEMO_BAND, ("label", "band", "regime", "read")),
                       (R.DEMO_CLOCK, ("label", "rr", "mm", "quadrant")),
                       (R.DEMO_CAPTURE, ("label", "up", "down", "spread")),
                       (R.DEMO_LEADERS, ("symbol", "rs_rank", "primary_sector")),
                       (R.DEMO_STANDING, ("symbol", "rs_rank", "rs_phase")),
                       (R.DEMO_BREADTH, ("sector", "n", "up_pct"))):
        assert rows, "an empty demo fallback defeats its own purpose"
        for r in rows:
            for k in keys:
                assert k in r, (k, r)


def test_demo_backed_views_say_so_in_words():
    """Correction #4: a preview may look full, but it must never pass illustrative data off as
    live. On the fixture DB these views are demo-backed, so the honesty line must be visible."""
    c = _client()
    for p in ("/dash/home/rotation?view=weather", "/dash/home/rotation?view=band",
              "/dash/home/rotation?view=clock", "/dash/home/strength?view=capture"):
        t = c.get(p).text
        assert ("illustrative sample" in t) or ("hasn't landed" in t) or ("haven't landed" in t), p


def test_the_phase_vocabulary_comes_from_the_canonical_engine():
    """A phase must never be worded two ways on two pages — the label is the engine's."""
    from src.automation.rs_phase import WEATHER_LABEL
    from src.web.home import markets_reads as R
    for key, label in WEATHER_LABEL.items():
        assert R.phase_label(key) == label, key
    assert R.phase_label("not-a-phase") == WEATHER_LABEL["NEUTRAL"]


# ── parity ────────────────────────────────────────────────────────────────────────────
W2B_KEYS = ("rrg", "rotation", "rsband", "cycle-clock", "rs-hub", "leaders", "momentum-scan",
            "capture-map", "sectors", "sector-economics", "sector-momentum")


def test_every_w2b_surface_has_an_explicit_recorded_disposition():
    from src.web import sideways_parity as SP
    missing = [k for k in W2B_KEYS if k not in SP.SURFACE_PARITY]
    assert not missing, ("W2-B surfaces with no explicit disposition", missing)
    for k in W2B_KEYS:
        status, target, note = SP.SURFACE_PARITY[k]
        assert status in ("PORTED", "DEFERRED"), (k, status)
        assert len(note) > 40, (k, "a disposition without a real note is not a decision")


def test_every_ported_w2b_target_actually_serves():
    """A PORTED claim is only honest if the route it names returns a page. This is the check that
    would have caught 'ported' entries pointing at a route nobody mounted."""
    from src.web import sideways_parity as SP
    c = _client()
    for k in W2B_KEYS:
        status, target, _note = SP.SURFACE_PARITY[k]
        if status != "PORTED":
            continue
        assert target.startswith("/dash/home/"), (k, target)
        r = c.get(target)
        assert r.status_code == 200, (k, target, r.status_code)
        assert "data-ui-g" in r.text, (k, target)
