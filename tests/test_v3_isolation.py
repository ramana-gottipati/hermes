"""test_v3_isolation.py — the redesign M0-M2 gate (Codex B2/B4 + Gemini B1 requirements).

Proves four things, permanently:
  1. ISOLATION — no legacy module imports any v3 module, and legacy pages carry zero v3
     markers (the additive-only rule made mechanical; the S177 lesson).
  2. QUARANTINE — nothing anywhere links a retired preview URL. This used to read "the preview
     is direct-URL only"; since the W6 retirement (2026-07-27) the contract is STRONGER, not
     weaker: those URLs now only 302 to their Graphite twins, so a link to one is a link into a
     redirect, never a destination. The retirement contract itself lives in
     `tests/test_preview_retired.py` (routes) — this file keeps the never-link half.
  3. TERM-CHIP ROUND-TRIP — every seed chip resolves chip → glossary.lookup() → a Pat
     explain hit on the same concept, and carries Verdict + Improve lines from the sidecar.
     Kept after the retirement on purpose: it is the ONLY gate on the `docs/metric-verdicts.md`
     sidecar, which would otherwise become an unchecked document the day its renderer went quiet.
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
              "stock_hub_v3", "hub_sections_v3", "stock_chart_v3", "ui_skin_bold", "today_v3")
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

def test_no_page_links_a_retired_preview_url():
    """Codex B2, hardened by the W6 retirement.

    Originally: "the preview is direct-URL only — no default page may link it." The preview is now
    RETIRED (302 → Graphite twins), so the same assertion carries a stronger meaning — a link to one
    of these URLs would send a reader through a redirect instead of at a destination, and would keep
    a dead surface looking alive in the nav graph. Absorbs the one still-live contract from the
    deleted `test_v3_stock_hub.py` (`/dash/preview/stock` + the `hub-idx` marker).

    `/dash` is walked with redirects followed, so this reads the POST-CUTOVER landing (the Graphite
    home) — i.e. the page a real visitor actually gets."""
    client = TestClient(_app())
    for path in ("/dash", "/dash/classic", "/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert r.status_code == 200, (path, r.status_code)
        for retired in ("/dash/preview", "/dash/_ui3"):   # covers /dash/preview/stock by prefix
            assert retired not in r.text, (path, retired)
        assert "hub-idx" not in r.text, path


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
    """RENDERER-LEVEL since the W6 retirement: the dock's host page (`/dash/preview`) is de-routed,
    so this drives `dock_html` directly. Same three contracts — every channel renders, its state is
    URL-addressable, and the `?symbol=` P0-1 bug class stays dead."""
    from src.web import news_dock
    for key, _label in news_dock.CHANNELS:
        out = news_dock.dock_html(ch=key, sym="TCS", base="/dash/preview")
        assert isinstance(out, str) and out, key
        assert "pv3-dock" in out and 'class="on"' in out, key
        assert "?ch=" + key in out and "sym=TCS" in out, key   # URL-addressable state
        assert "?symbol=" not in out, key                      # the P0-1 bug class stays dead


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
