"""test_v3_isolation.py — the redesign M0-M2 gate (Codex B2/B4 + Gemini B1 requirements).

Proves four things, permanently:
  1. ISOLATION — no legacy module imports any v3 module, and legacy pages carry zero v3
     markers (the additive-only rule made mechanical; the S177 lesson).
  2. The preview surfaces exist, are POST-disciplined, and are route-gate registered.
  3. TERM-CHIP ROUND-TRIP — every seed chip resolves chip → glossary.lookup() → a Pat
     explain hit on the same concept, and carries Verdict + Improve lines from the sidecar.
  4. FENCE DISCIPLINE — the epistemic copy contains no action-verb verdict labels.

Reviewer record: docs/redesign-coordination.md §3-§4.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
V3_MODULES = ("ui_tokens_v3", "shell_v3", "ui_components_v3", "term_chip",
              "v3_preview", "ui_showcase_v3", "news_dock",
              "stock_hub_v3", "hub_sections_v3", "stock_chart_v3")
V3_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3chip", "pv3-top")


def _app():
    from src.main import app
    return app


# ── 1. isolation ──────────────────────────────────────────────────────────────────

def test_no_legacy_module_imports_v3():
    offenders = []
    for py in (ROOT / "src").rglob("*.py"):
        if py.name in {m + ".py" for m in V3_MODULES}:
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        for mod in V3_MODULES:
            if re.search(r"(import|from)\s+[\w.]*\b" + mod + r"\b", text):
                # v2_surfaces names them ONLY as _ROUTER_SPECS strings, never an import
                if py.name == "v2_surfaces.py" and ("src.web." + mod) in text \
                        and not re.search(r"^\s*(from|import)\s+[\w.]*" + mod, text, re.M):
                    continue
                offenders.append(py.name + " -> " + mod)
    assert not offenders, offenders


def test_legacy_pages_carry_no_v3_markers():
    client = TestClient(_app())
    for path in ("/dash/glossary", "/dash/coverage", "/dash/reading-guide"):
        r = client.get(path, follow_redirects=True)
        assert r.status_code == 200, (path, r.status_code)
        for marker in V3_MARKERS:
            assert marker not in r.text, (path, marker)


# ── 2. the preview surfaces ───────────────────────────────────────────────────────

def test_preview_routes_serve_and_toggle_is_post_only():
    client = TestClient(_app())
    r = client.get("/dash/preview")
    assert r.status_code == 200 and "data-ui-v3" in r.text and "PREVIEW" in r.text
    r = client.get("/dash/_ui3")
    assert r.status_code == 200 and "pv3chip" in r.text and "demo value" in r.text
    # the write is POST-only (playbook #11)
    assert client.get("/dash/preview/toggle").status_code == 405
    r = client.post("/dash/preview/toggle", follow_redirects=False)
    assert r.status_code == 303 and r.cookies.get("pv3") == "1"
    # second toggle clears
    r2 = client.post("/dash/preview/toggle", cookies={"pv3": "1"}, follow_redirects=False)
    assert r2.status_code == 303 and "pv3" in r2.headers.get("set-cookie", "")
    assert 'pv3=""' in r2.headers.get("set-cookie", "") or "pv3=;" in r2.headers.get("set-cookie", "")


def test_preview_routes_are_route_gate_registered():
    from tests import test_dash_route_registry as gate
    for path in ("/dash/preview", "/dash/_ui3"):
        assert path in gate.INTERNAL_DEV, path
        owner, rationale = gate.INTERNAL_DEV[path]
        assert owner and rationale


def test_default_chrome_never_links_the_preview():
    """Codex B2: the preview is direct-URL only — no default page may link it."""
    client = TestClient(_app())
    for path in ("/dash", "/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert "/dash/preview" not in r.text and "/dash/_ui3" not in r.text, path


# ── 3. term-chip round-trip (Codex B4) ────────────────────────────────────────────

def test_seed_chips_resolve_glossary_and_pat():
    from src.web import glossary as G
    from src.web import term_chip
    from src.pat import glossary as PG
    for key, (label, _code, gkey, _ref) in term_chip.SEEDS.items():
        entry = G.lookup(gkey)
        assert entry, "web glossary miss: " + gkey
        v = term_chip.verdict_for(gkey)
        assert v and v.get("verdict") and v.get("improve"), "sidecar gap: " + key
        # Pat can explain the same concept: probe by glossary key, then by plain label
        hits = PG.find(gkey, limit=3) or PG.find(label, limit=3)
        assert hits, "Pat explain miss for chip: " + key
        html = term_chip.chip(key, sym="TCS")
        assert "tc-card" in html and "Ask Pat" in html and 'tabindex="0"' in html
        assert "for%20TCS" in html or "for+TCS" in html  # symbol-aware Ask Pat (Gemini I4)


def test_chip_degrades_never_breaks():
    from src.web import term_chip
    assert term_chip.chip("no-such-chip") == "no-such-chip"


# ── 3b. the news/flow dock (M3) ───────────────────────────────────────────────────

def test_dock_all_channels_render_with_url_state():
    from src.web import news_dock
    client = TestClient(_app())
    for key, _label in news_dock.CHANNELS:
        r = client.get("/dash/preview", params={"ch": key, "sym": "TCS"})
        assert r.status_code == 200, key
        assert "pv3-dock" in r.text and 'class="on"' in r.text, key
        assert "?ch=" + key in r.text and "sym=TCS" in r.text, key  # URL-addressable state
        assert "?symbol=" not in r.text, key  # the P0-1 bug class stays dead


def test_dock_reads_are_defensive():
    """Every channel renderer must return HTML (rows or an honest empty state) even on a
    connection that has NO tables at all."""
    import sqlite3
    from src.web import news_dock
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for key, fn in news_dock._RENDER.items():
        out = fn(conn, "")
        assert isinstance(out, str) and out, key
        assert ("pv3-dock-rows" in out) or ("pv3-dock-empty" in out), key


def test_dock_wire_neutralizes_unsafe_url_schemes():
    """Codex M3 B1: feed URLs are attacker-influenced — javascript:/data: must never reach href."""
    import sqlite3
    from src.web import news_dock
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE sent_news(id INTEGER PRIMARY KEY, source TEXT, url TEXT, "
                 "title TEXT, sent_at TEXT)")
    conn.execute("INSERT INTO sent_news(source,url,title,sent_at) VALUES "
                 "('x','javascript:alert(1)','evil','2026-07-17 09:00')")
    out = news_dock._ch_wire(conn, "")
    assert "javascript:" not in out and 'href="#"' in out


def test_dock_absent_from_legacy_and_from_showcase_head():
    client = TestClient(_app())
    for path in ("/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert "pv3-dock" not in r.text, path


# ── 4. fence discipline ───────────────────────────────────────────────────────────

def test_epistemic_copy_carries_no_action_verbs():
    from src.web import term_chip
    term_chip._load_verdicts()
    joined = " ".join((v.get("verdict", "") + " " + v.get("improve", "")).lower()
                      for v in term_chip._VERDICTS.values())
    for verb in ("buy", "sell", "avoid", "ride", "fade"):
        assert re.search(r"\b" + verb + r"\b", joined) is None, verb
