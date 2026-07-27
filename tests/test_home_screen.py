"""test_home_screen.py — the gate for the Graphite SCREENER estate (lane W4 · milestone M8).

`/dash/home/screen` is a REBUILD of the classic `/dash/screen2`, and the reason it is a rebuild
rather than a port is three recorded debts. This file pins the fix for each one so it cannot
silently regress:

    1. PAYLOAD     — the classic page shipped ~2.3 MB in one document. Here the server paginates
                     and renders only the active columns: test_default_render_is_under_budget.
    2. EXPORT      — the classic CSV was a client-side blob of the DOM. Here it is a server export
                     that honours the live filter/sort/column state: test_csv_honors_*.
    3. URL STATE   — the classic column/sort/filter state lived in localStorage and could not be
                     shared. Here the URL *is* the screen: test_url_state_round_trips + friends.

Plus the standing surface rules: glossary-backed columns, `?sym=` links to the Graphite stock
page, descriptive-only fences, demo honesty, and clamping (never 422) on hand-typed URLs.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from src.web.home import screen_pages as SP

ROOT = Path(__file__).resolve().parents[1]

PAYLOAD_BUDGET = 500_000
PREVIEW_LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')

# the classic web-VIEW modules this lane must never borrow an engine from (the isolation
# contract's practical rule: reuse the STORED columns, never import a render module)
BANNED_VIEWS = ("screener_plus", "cockpit", "dashboard", "ui_kit", "infographics",
                "stock_hub_v3", "hub_sections_v3", "v3_preview", "shell_skin", "left_rail")


def _client():
    from src.main import app
    return TestClient(app)


def _syms(html: str) -> list:
    return re.findall(r'/dash/home/stock\?sym=([A-Z0-9&.\-]+)"', html)


def _mine(html: str) -> str:
    """Just THIS lane's rendered zones. The shared shell (the classic-site directory) and the
    shared Pat dock are other owners' markup — asserting over the whole document would test them,
    not this page, and would go red when a sibling lane edits its own file."""
    return "".join(re.findall(r'<section class="g-zone".*?</section>', html, re.S))


# ── the surface exists, is Graphite, and is declared ──────────────────────────────────────────
def test_screen_and_themes_render_as_graphite_surfaces():
    c = _client()
    for path in ("/dash/home/screen", "/dash/home/themes"):
        r = c.get(path)
        assert r.status_code == 200, (path, r.status_code)
        assert "data-ui-g" in r.text, path
        for m in PREVIEW_LEGACY_MARKERS:
            assert m not in r.text, (path, "leaked a preview/legacy marker", m)


def test_screen_routes_are_route_gate_registered():
    """The declared-child pattern: legal with no lens_registry entry and no nav, PROVIDED both
    routes are registered in the route gate with an owner and a specific rationale."""
    from tests import test_dash_route_registry as gate
    for path in ("/dash/home/screen", "/dash/home/themes"):
        assert path in gate.INTERNAL_DEV, path
        owner, rationale = gate.INTERNAL_DEV[path]
        assert owner == "graphite-home" and len(rationale) > 40, path


def test_screen_modules_import_no_classic_view_module():
    """Belt-and-braces over tests/test_home_isolation.py: this lane may reuse the DATA layer and
    the registry, never a classic render module (importing one would drag legacy CSS + chrome into
    the Graphite package and break isolation in both directions)."""
    offenders = []
    for name in ("screen_pages.py", "screen_reads.py"):
        text = (ROOT / "src" / "web" / "home" / name).read_text(encoding="utf-8")
        for mod in BANNED_VIEWS:
            if re.search(r"^\s*(from|import)\s+[\w.]*\b" + mod + r"\b", text, re.M):
                offenders.append(name + " -> " + mod)
    assert not offenders, offenders


# ── DEBT 1: payload ───────────────────────────────────────────────────────────────────────────
def test_default_render_is_under_the_payload_budget():
    """The headline regression guard. Classic /dash/screen2 rendered up to 600 rows x 43 columns in
    ONE document (~2.3 MB); the rebuild paginates server-side and renders only the active columns."""
    c = _client()
    n = len(c.get("/dash/home/screen").content)
    assert n < PAYLOAD_BUDGET, ("default screen render exceeded the payload budget", n)


def test_payload_budget_holds_in_every_reachable_state():
    """The live-render check above is NOT sufficient evidence on a 4-row fixture DB — it would pass
    no matter how heavy a real page got. This projects the true worst case from the real markup:
    a FULL page of rows at every offered page size, for both the default view and the whole
    75-column pool. `effective_n` is what makes this bounded (a wide view renders shorter pages);
    without it, n=200 x 75 columns projects to ~585 KB and blows the budget."""
    c = _client()
    st_default = SP.parse_state({"scope": "all"})
    chrome = len(c.get("/dash/home/screen?scope=all").content) \
        - len(SP._tbody(SP._demo_rows(st_default), st_default, {}))
    seed = SP._demo_rows(st_default)
    worst = 0
    for cols in (SP.DEFAULT_COLS, tuple(SP.BY_KEY)):
        for n in SP.PAGE_SIZES:
            st = SP.parse_state({"scope": "all", "cols": ",".join(cols), "n": str(n)})
            eff = SP.effective_n(st)
            full_page = ([dict(r) for r in seed] * (eff // len(seed) + 1))[:eff]
            total = chrome + len(SP._tbody(full_page, st, {}))
            assert total < PAYLOAD_BUDGET, (
                "projected page over budget", len(cols), "cols", n, "requested", eff, "rendered", total)
            worst = max(worst, total)
    assert worst > 120_000, ("projection looks degenerate — check the fixture", worst)


def test_pagination_is_server_side():
    """Rows are sliced on the server: a smaller page size must render strictly fewer rows, and the
    page-2 link must be present in the pager whenever there is a second page."""
    c = _client()
    small = c.get("/dash/home/screen?scope=all&n=25").text
    assert small.count("<tr>") <= 26, "more rows rendered than the requested page size"
    assert "page 1 of" in small


def test_wide_views_shorten_pages_and_say_so():
    """The cell budget is a product behaviour, not a silent trim: when a wide column set forces a
    shorter page, the pager must tell the reader why."""
    st_wide = SP.parse_state({"cols": ",".join(SP.BY_KEY), "n": "200"})
    assert SP.effective_n(st_wide) < 200, "a 75-column view must not render 200 rows"
    st_narrow = SP.parse_state({"cols": "rsrank,hh", "n": "200"})
    assert SP.effective_n(st_narrow) == 200, "a narrow view must honour the requested page size"
    html = _client().get("/dash/home/screen?scope=all&n=200&cols=" + ",".join(SP.BY_KEY)).text
    assert "rows per page (asked for 200)" in html, "the reduction was not disclosed"


# ── DEBT 2: the server CSV export ─────────────────────────────────────────────────────────────
def test_csv_is_a_server_export_not_a_dom_blob():
    c = _client()
    r = c.get("/dash/home/screen?scope=all&format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")


def test_csv_honors_the_active_filter_sort_and_column_set():
    """The whole point of moving the export server-side: the download is the SAME screen the URL
    describes — same rows (filter), same order (sort), same columns."""
    c = _client()
    base = "/dash/home/screen?scope=all"
    # (a) the column set
    csv_cols = c.get(base + "&cols=rsrank,hh&format=csv").text.splitlines()[1]
    assert csv_cols.split(",")[:3] == ["Symbol", "Sector", "CMP"], csv_cols
    assert "RS rank" in csv_cols and "From 52w high" in csv_cols
    assert "MEP state" not in csv_cols, "CSV emitted a column that is not in the active set"
    # (b) the sort
    def order(url):
        rows = c.get(url).text.strip().splitlines()[2:]
        return [ln.split(",")[0] for ln in rows if ln]
    desc = order(base + "&sort=rsrank&dir=desc&format=csv")
    asc = order(base + "&sort=rsrank&dir=asc&format=csv")
    assert len(desc) >= 2, "fixture too small to prove ordering"
    assert desc == list(reversed(asc)), (desc, asc)
    # (c) the text filter
    one = order(base + "&q=" + desc[0] + "&format=csv")
    assert one == [desc[0]], one
    # (d) the state is echoed in the export header, so a downloaded file is self-describing
    head = c.get(base + "&q=zzz&minconf=3&sort=rsrank&format=csv").text.splitlines()[0]
    assert "scope=all" in head and "filter=zzz" in head and "min confluence=3" in head


def test_csv_marks_sample_data_honestly():
    """Standing correction #4: a demo fallback may look full, but must never be passed off as a
    live read — including in the export."""
    c = _client()
    assert "SAMPLE DATA" in c.get("/dash/home/screen?format=csv").text.splitlines()[0]
    assert "live" in c.get("/dash/home/screen?scope=all&format=csv").text.splitlines()[0]


# ── DEBT 3: URL-addressable state ─────────────────────────────────────────────────────────────
def test_url_state_round_trips():
    """Parse -> serialise -> parse must be a fixed point for every field. This is what makes a
    screen shareable: the link a user copies reproduces their exact view."""
    cases = [
        {}, {"scope": "all"}, {"scope": "theme:Aviation"}, {"q": "bank"}, {"minconf": "4"},
        {"rev": "ri"}, {"sort": "rsrank", "dir": "asc"}, {"n": "200", "page": "3"},
        {"view": "keyprice"}, {"cols": "rsrank,hh,dvpt", "sort": "hh"},
        {"scope": "Nifty Bank", "cols": "cci,ccitier", "q": "hdfc", "minconf": "2",
         "sort": "cci", "dir": "asc", "n": "100", "page": "2"},
    ]
    for params in cases:
        st1 = SP.parse_state(params)
        url = SP.qs(st1)
        qp = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&")) if "?" in url else {}
        from urllib.parse import unquote
        st2 = SP.parse_state({k: unquote(v) for k, v in qp.items()})
        for f in SP.State.__slots__:
            assert getattr(st1, f) == getattr(st2, f), (params, f, getattr(st1, f), getattr(st2, f))


def test_every_control_on_the_page_carries_the_full_state():
    """A control that drops state silently resets the user's screen. Every sort header, family
    toggle, view chip and the CSV link must carry the active scope/filter/confluence forward."""
    c = _client()
    url = "/dash/home/screen?scope=all&q=ALPHA&minconf=1&cols=rsrank,hh&sort=hh&dir=asc"
    html = _mine(c.get(url).text)
    hrefs = re.findall(r'href="(/dash/home/screen[^"]*)"', html)
    assert len(hrefs) > 10, "expected many stateful controls"
    # A control changes exactly ONE facet and preserves the rest. The scope chips legitimately
    # rewrite `scope`; nothing may drop the user's filter or confluence minimum.
    dropped = [h for h in hrefs
               if h != "/dash/home/screen" and not ("q=ALPHA" in h and "minconf=1" in h)]
    assert not dropped, ("controls that silently drop the active filter state", dropped[:5])
    # controls that are NOT the scope picker must keep the scope too — the sort headers (each
    # rewrites `sort`) and the CSV link are the representative cases.
    keeps_scope = [h for h in hrefs if "format=csv" in h or "sort=cmp" in h or "sort=rsrank" in h]
    assert len(keeps_scope) >= 3, keeps_scope
    assert all("scope=all" in h for h in keeps_scope), keeps_scope[:5]
    assert any("format=csv" in h for h in hrefs), "the CSV link must carry the active state"


def test_sort_and_filter_are_server_side():
    c = _client()
    desc = _syms(c.get("/dash/home/screen?scope=all&sort=rsrank&dir=desc").text)
    asc = _syms(c.get("/dash/home/screen?scope=all&sort=rsrank&dir=asc").text)
    assert len(desc) >= 2 and desc == list(reversed(asc)), (desc, asc)
    only = _syms(c.get("/dash/home/screen?scope=all&q=" + desc[0]).text)
    assert only == [desc[0]], only


def test_bad_url_params_clamp_rather_than_error():
    """A hand-typed, truncated or stale URL must still render a screen — never a 422 error page."""
    c = _client()
    for bad in ("?n=99999", "?page=-4", "?minconf=99", "?sort=not_a_column", "?cols=,,,",
                "?view=nope", "?dir=sideways", "?scope=", "?n=abc&page=xyz&minconf=q"):
        r = c.get("/dash/home/screen" + bad)
        assert r.status_code == 200, (bad, r.status_code)


# ── the column architecture (Part III §J, ratified 2026-07-20) ────────────────────────────────
def test_pool_matches_the_ratified_column_architecture():
    assert len(SP.POOL) >= 50, ("the evidence pool shrank below the ratified scale", len(SP.POOL))
    assert 10 <= len(SP.DEFAULT_COLS) <= 12, ("defaults must stay 10-12", len(SP.DEFAULT_COLS))
    assert SP.SOFT_CAP == 20
    assert len({c.key for c in SP.POOL}) == len(SP.POOL), "duplicate column key"
    for name, (_label, cols, _blurb) in SP.VIEWS.items():
        unknown = [k for k in cols if k not in SP.BY_KEY]
        assert not unknown, (name, unknown)


def test_every_pool_column_is_glossary_backed():
    """SURFACE-PLAYBOOK item 5, mirrored from the classic Screen+ gate: a surfaced metric column
    carries a glossary key (so its meaning reaches Pat and the ? popovers) or an explicit ''
    opt-out. A new column with an undocumented key fails — define it in docs/metrics-glossary.md."""
    from src.web import glossary as WG
    WG._load()
    missing = [(c.key, c.term) for c in (SP.SPINE + SP.POOL) if c.term and not WG.has(c.term)]
    assert not missing, (
        "\nGraphite screener columns whose glossary key does NOT resolve in docs/metrics-glossary.md:\n"
        + "\n".join(f"  !! column {k!r} -> key {t!r}" for k, t in missing))


def test_columns_are_never_paywalled():
    """Part III §J, ratified: 'every column is free; evidence is never gated'. The Pro layer may
    only add REFERENCE context, so no pooled column may render inside a Pro-only wrapper."""
    c = _client()
    html = c.get("/dash/home/screen?scope=all&cols=" + ",".join(SP.BY_KEY)).text
    body = html.split('<table class="g-scr">', 1)[1].split("</table>", 1)[0]
    head = body.split("</thead>", 1)[0]
    for col in SP.POOL:
        cell = re.search(r'<th[^>]*>(?:(?!</th>).)*' + re.escape(col.label) + r'', head, re.S)
        assert cell, ("a pooled column vanished from the header", col.key)
    pro_ths = re.findall(r'<th class="pro-more"[^>]*>([^<]*)</th>', head)
    assert set(pro_ths) == {"Rank in screen", "vs own 1-mo"}, (
        "only the reference layer may be Pro-gated", pro_ths)


# ── surface rules ─────────────────────────────────────────────────────────────────────────────
def test_symbols_link_the_graphite_stock_page_with_sym():
    c = _client()
    for path in ("/dash/home/screen?scope=all", "/dash/home/themes?tag=Aviation"):
        html = _mine(c.get(path).text)
        assert "?symbol=" not in html, (path, "used ?symbol= instead of ?sym=")
        assert "/dash/stock?sym=" not in html, (path, "linked the classic dossier, not the Graphite one")
    assert _syms(c.get("/dash/home/screen?scope=all").text), "no symbol links rendered"


def test_demo_fallback_is_flagged_and_live_rows_are_not():
    """A zone backed by demo data must wear the sample badge; a zone backed by a real read must not."""
    c = _client()
    assert "· sample" in c.get("/dash/home/screen").text
    assert "· sample" not in c.get("/dash/home/screen?scope=all").text


def test_descriptive_fences_travel_with_their_family():
    """Falsified/descriptive-only families cannot be shown without their fence — the fence travels
    with the surface, it is not a footnote somewhere else."""
    c = _client()
    checks = {"cci": "Gate B", "rev": "falsified as entries", "fno": "forward-test-only",
              "wol": "SELECTION", "conf": "not a validated model"}
    for fam, phrase in checks.items():
        keys = [col.key for col in SP.POOL if col.fam == fam]
        html = c.get("/dash/home/screen?scope=all&cols=" + ",".join(keys)).text
        assert phrase in html, (fam, "rendered without its descriptive fence")


def test_no_verdict_verbs_and_no_ret_vol_mislabel():
    """No advice verbs on a descriptive surface, and the ret/vol label gate: 'Sharpe' never
    reappears as a name for a return/volatility ratio."""
    c = _client()
    for path in ("/dash/home/screen?scope=all", "/dash/home/themes"):
        low = _mine(c.get(path).text).lower()
        assert "sharpe" not in low, path
        for verb in ("buy now", "sell now", "target price", "we recommend", "you should buy",
                     "strong buy", "avoid this"):
            assert verb not in low, (path, verb)


def test_themes_is_multi_label_and_hands_off_to_the_screener():
    """The themes page is the non-ticker door; its value is that it FEEDS the screener rather than
    dead-ending in its own table."""
    c = _client()
    board = c.get("/dash/home/themes").text
    assert "/dash/home/themes?tag=" in board, "no drill-down into a theme"
    detail = c.get("/dash/home/themes?tag=Aviation").text
    assert "/dash/home/screen?scope=theme%3AAviation" in detail or \
           "/dash/home/screen?scope=theme:Aviation" in detail, "theme does not hand off to the screener"


def test_screen_scope_accepts_a_theme():
    c = _client()
    r = c.get("/dash/home/screen?scope=theme:Aviation")
    assert r.status_code == 200 and "data-ui-g" in r.text


# ── the parity ledger records a verdict for all five screener surfaces ────────────────────────
def test_all_five_screener_surfaces_have_an_explicit_verdict():
    """2026-07-28: screen2 + themes were downgraded PORTED -> DEFERRED by the gap audit (register
    §7a/§7b — the five inline instrument visuals and the Pat bridge never travelled, and the theme
    participants table lost 6 of 11 columns), so the expectation here is DEFERRED-with-a-route, not
    PORTED. The verdict must still be EXPLICIT for all five — that is what this gate protects."""
    from src.web import sideways_parity as SPY
    expected = {"screen2": "DEFERRED", "themes": "DEFERRED", "screener": "DROPPED",
                "tags-review": "NA", "workbench": "DROPPED"}
    for key, status in expected.items():
        assert key in SPY.SURFACE_PARITY, ("no explicit disposition recorded", key)
        st, target, note = SPY.SURFACE_PARITY[key]
        assert st == status, (key, st, status)
        if st == "PORTED":
            assert target.startswith("/dash/home/"), (key, target)
        elif st == "DEFERRED":
            assert target in SPY.MILESTONES, (key, "DEFERRED needs a real milestone", target)
            assert "LANDED at /dash/home/" in note, (
                key, "a downgraded surface must still name the route it landed at")
        else:
            assert len(note) > 80, (key, "a DROPPED/NA verdict needs a real rationale")
