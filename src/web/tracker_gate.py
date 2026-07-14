"""tracker_gate.py — the Tracker is a PRIVATE workspace on a public site.

UX audit S-A / P0-6; Ramana decision 2026-07-14: **DEMO-BOOK.** Anonymous visitors get a
clearly-labelled synthetic demo book on every tracker surface — the owner's real books,
positions, alerts and imports never render publicly, and every tracker WRITE (add/close/
edit/import — previously wide open, so any stranger could edit the real book) is now
owner-only. The owner unlocks via a POST form at /dash/tracker/owner using the existing
``chat_shared_secret`` (AUD-01 already provisions it on the VPS): the cookie stores a
sha256 derivation, the secret itself never appears in a URL. An EMPTY secret (dev
laptops) means owner-by-default, so the local workflow is unchanged.

Gate map: ``/dash/tracker/*`` pages → demo book for non-owners; ``/dash/track*`` +
``/dash/import*`` (mutations, personal exports, personal detail pages) → 303 to the demo
for non-owners; ``/dash/track/quote`` stays open (market data, nothing personal).

Isolated module (parallel-sessions doctrine — no dashboard.py handler edited): pure HTTP
middleware installed from main.py. Child route registered per SURFACE-PLAYBOOK §2.4
(interim registry = the UX audit §5 table): ``/dash/tracker/owner`` — owner-unlock form,
declared child of the Tracker workspace, reached from the demo page footer.
"""
from __future__ import annotations

import hashlib
import html as _html
import logging

log = logging.getLogger("hermes.tracker_gate")

_COOKIE = "pt_owner"
# The five tracker sub-tabs each get their OWN demo view (see _DEMO_VIEW below) so the
# tabs are RESPONSIVE and the active one highlights — a single shared body made every tab
# repaint the identical page (looked like dead/unresponsive tabs). Keys live in _DEMO_VIEW.
_OPEN = ("/dash/track/quote",                 # market data, not personal
         "/dash/import/template.csv")         # the CSV format template — non-personal

# A deliberately synthetic book (well-known large caps, fixed entries/dates) — real CMPs
# are read live so the page demonstrates the tool honestly, but nothing here is, or ever
# was, the owner's position.
_DEMO_POSITIONS = [
    ("RELIANCE",  10, 1180.0, "2026-04-08"),
    ("TCS",        5, 3620.0, "2026-03-20"),
    ("HDFCBANK",  12, 1512.0, "2026-05-05"),
    ("INFY",      15, 1385.0, "2026-02-14"),
    ("TATAPOWER", 40,  372.0, "2026-06-02"),
    ("PCBL",      25,  268.0, "2026-06-18"),
]
_DEMO_WATCH = ["BHEL", "KAJARIACER", "LAURUSLABS"]


def _secret() -> str:
    try:
        from src.core.settings import settings
        return settings.chat_shared_secret or ""
    except Exception:  # noqa: BLE001
        return ""


def _token(secret: str) -> str:
    return hashlib.sha256((secret + "|patearn-tracker-owner").encode()).hexdigest()


def _is_owner(request) -> bool:
    """Owner = any credential EITHER gate understands. perimeter.ConversationsGuard
    (the sibling P0-6 'hide' gate, kept as defense-in-depth INSIDE this one) accepts the
    raw secret via ?hermes_key= / hermes_key cookie / X-Hermes-Secret header; this gate
    adds the hashed pt_owner cookie set by the /dash/tracker/owner form. Honoring all
    four keeps the two layers coherent — an owner unlocked by either flow passes both."""
    sec = _secret()
    if not sec:                          # dev box: no secret configured -> owner
        return True
    import hmac
    if request.cookies.get(_COOKIE, "") == _token(sec):
        return True
    for v in (request.query_params.get("hermes_key") or "",
              request.cookies.get("hermes_key") or "",
              request.headers.get("x-hermes-secret") or ""):
        if v and hmac.compare_digest(v, sec):
            return True
    return False


def _gated(path: str) -> bool:
    if path.startswith(_OPEN):
        return False
    return (path.startswith("/dash/tracker") or path.startswith("/dash/track")
            or path.startswith("/dash/import"))


_DEMO_CSS = """<style>
.tg-note{border:1px solid var(--warn,#f6b73c);background:rgba(246,183,60,.10);border-radius:10px;
  padding:10px 14px;font-size:13px;line-height:1.55;margin:4px 0 12px;}
.tg-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:10px 0 14px;}
.tg-box{background:var(--bg-2,#161b22);border:1px solid var(--line-2,#30363d);border-radius:10px;padding:10px 13px;}
.tg-box .n{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums;}
.tg-box .l{font-size:11px;color:var(--ink-2,#8b949e);margin-top:3px;}
table.tg-t{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px;}
table.tg-t th{text-align:left;color:var(--ink-2,#8b949e);font-size:11px;padding:4px 8px;border-bottom:1px solid var(--line-2,#30363d);}
table.tg-t td{padding:6px 8px;border-bottom:1px solid var(--line-2,#30363d);}
table.tg-t td.r,table.tg-t th.r{text-align:right;font-variant-numeric:tabular-nums;}
.tg-foot{margin-top:14px;font-size:12px;color:var(--ink-2,#8b949e);}
.tg-foot a{color:inherit;}
</style>"""


# ── shared demo pieces (reused across the five sub-tab views) ─────────────────────────
def _note(extra: str = "") -> str:
    """The yellow 'this is synthetic' banner every demo page carries."""
    return ('<div class="tg-note">🧪 <b>Demo book — sample positions.</b> The tracker is a '
            'private workspace, so a public visitor sees how it works, never anyone\'s real '
            'portfolio. The positions are invented; <b>prices, sector, and the character · RS '
            'reads are all live</b>.'
            + ((" " + extra) if extra else "") + '</div>')


def _foot(msg: str = "Owner? Unlock your books →") -> str:
    return f'<div class="tg-foot"><a href="/dash/tracker/owner">{msg}</a></div>'


def _demo_signals(symbols) -> dict:
    """Live enrichment for the demo symbols — CMP · sector · cap tier + the thesis-health
    cell (character · RS rank · conviction), REUSING the owner-page helpers (`dashboard._enrich`
    / `_health_cell` / `_capture_snapshot`) so the PUBLIC demo demonstrates the real analytics,
    not a bare P&L table. Honest: the positions/entries are invented, but the sector/character/RS
    reads are LIVE (same as CMP). Defensive → {} on any failure; each key degrades to None so the
    table still renders on a thin DB. One DB pass for the whole page."""
    out = {}
    try:
        from src.web import dashboard as D
        with D.get_conn() as conn:
            enr = D._enrich(conn, list(symbols))
            for s in symbols:
                e = enr.get(s, {}) or {}
                sig = e.get("sig") or {}
                try:
                    cmp_ = D._capture_snapshot(conn, s)[0]
                except Exception:  # noqa: BLE001
                    cmp_ = None
                out[s] = {
                    "cmp": cmp_,
                    "sector": D._sector_short(e.get("sector")),
                    "tier": e.get("tier"),
                    "rs": sig.get("rs_rank"),
                    "char": sig.get("accum_character"),
                    # thn=None: no frozen entry snapshot in the demo, so no then→now drift —
                    # the cell shows the live character · RS · conviction read (honest).
                    "health": D._health_cell(None, sig, cmp_, None),
                }
    except Exception:  # noqa: BLE001 — enrichment is a demo garnish; never break the gate
        pass
    return out


def _sec_cell(d: dict) -> str:
    sec = d.get("sector") or "—"
    tier = d.get("tier")
    return sec + (f' · <span class="mut">{tier}</span>' if tier else "")


def _positions_view(sigs: dict):
    """(rows_html, invested, current_value, total_pl_pct) for the demo book. `sigs` =
    _demo_signals() (live CMP + sector/tier + the thesis-health cell)."""
    rows, inv, cur = [], 0.0, 0.0
    for sym, qty, entry, since in _DEMO_POSITIONS:
        d = sigs.get(sym) or {}
        c = d.get("cmp")
        inv += qty * entry
        cur += qty * (c or entry)
        pl = ((c - entry) / entry * 100.0) if c else None
        pl_txt = (f'<span style="color:var(--{ "up" if pl >= 0 else "down" })">{pl:+.1f}%</span>'
                  if pl is not None else "—")
        cmp_txt = f"₹{c:,.1f}" if c else "—"
        health = d.get("health") or '<span class="mut">—</span>'
        rows.append(f'<tr><td><a href="/dash/stock?sym={sym}" style="color:inherit">{sym}</a></td>'
                    f'<td>{_sec_cell(d)}</td>'
                    f'<td class="r">{qty}</td><td class="r">₹{entry:,.1f}</td>'
                    f'<td class="r">{cmp_txt}</td><td class="r">{pl_txt}</td>'
                    f'<td>{health}</td><td>{since}</td></tr>')
    tot_pl = ((cur - inv) / inv * 100.0) if inv else None
    return "".join(rows), inv, cur, tot_pl


def _positions_table(rows_html: str) -> str:
    return ('<table class="tg-t"><thead><tr><th>Symbol</th><th>Sector · Cap</th>'
            '<th class="r">Qty</th><th class="r">Entry</th><th class="r">CMP</th>'
            '<th class="r">P&amp;L</th><th>Thesis-health <span class="mut">(live)</span></th>'
            '<th>Since</th></tr></thead><tbody>' + rows_html + '</tbody></table>')


def _kpi(n: str, label: str) -> str:
    return f'<div class="tg-box"><div class="n">{n}</div><div class="l">{label}</div></div>'


def _pl_kpi(tot_pl, label="P&amp;L") -> str:
    return _kpi(f'{tot_pl:+.1f}%' if tot_pl is not None else "—", label)


# ── the five sub-tab views — each DISTINCT so the tabs are responsive + highlight ─────
def _demo_dashboard() -> str:
    sigs = _demo_signals([p[0] for p in _DEMO_POSITIONS])
    rows, inv, cur, tot_pl = _positions_view(sigs)
    watch = " · ".join(f'<a href="/dash/stock?sym={s}" style="color:inherit">{s}</a>'
                       for s in _DEMO_WATCH)
    return (_DEMO_CSS
        + '<h2>Tracker <span class="sub" style="margin:0">demo book</span></h2>'
        + _note('The tracker adds books, alerts, P&amp;L and a CSV import on top.')
        + '<div class="tg-kpi">'
        + _kpi("1", "book (demo)") + _kpi(str(len(_DEMO_POSITIONS)), "open positions")
        + _kpi(f'₹{inv:,.0f}', "invested") + _kpi(f'₹{cur:,.0f}', "value (live)")
        + _pl_kpi(tot_pl) + _kpi(str(len(_DEMO_WATCH)), "watchlist ideas")
        + '</div>'
        + _positions_table(rows)
        + f'<div style="margin-top:10px;font-size:13px"><b>Watchlist:</b> {watch}</div>'
        + '<div class="tg-foot">Every symbol links to its full research dossier. '
          '<a href="/dash/tracker/owner">Owner? Unlock your books →</a></div>')


def _demo_portfolios() -> str:
    sigs = _demo_signals([p[0] for p in _DEMO_POSITIONS])
    rows, inv, cur, tot_pl = _positions_view(sigs)
    return (_DEMO_CSS
        + '<h2>Portfolios <span class="sub" style="margin:0">demo book</span></h2>'
        + _note('<b>Portfolios</b> are positions you\'ve committed money to — a frozen entry, '
                'live P&amp;L, target/stop distance and a live <b>thesis-health</b> read (is the '
                'strong hand still accumulating; is relative strength holding).')
        + '<div class="tg-kpi">'
        + _kpi(f'₹{inv:,.0f}', "invested") + _kpi(f'₹{cur:,.0f}', "value (live)")
        + _pl_kpi(tot_pl) + _kpi(str(len(_DEMO_POSITIONS)), "positions")
        + '</div>'
        + _positions_table(rows)
        + _foot('Unlock to keep your own books, entries and targets →'))


def _demo_watchlists() -> str:
    sigs = _demo_signals(_DEMO_WATCH)
    rows = []
    for s in _DEMO_WATCH:
        d = sigs.get(s) or {}
        c = d.get("cmp")
        cmp_txt = f"₹{c:,.1f}" if c else "—"
        health = d.get("health") or '<span class="mut">—</span>'
        rows.append(f'<tr><td><a href="/dash/stock?sym={s}" style="color:inherit">{s}</a></td>'
                    f'<td>{_sec_cell(d)}</td><td class="r">{cmp_txt}</td>'
                    f'<td>{health}</td>'
                    f'<td><a href="/dash/stock?sym={s}" style="color:inherit">open dossier →</a></td></tr>')
    return (_DEMO_CSS
        + '<h2>Watchlists <span class="sub" style="margin:0">demo book</span></h2>'
        + _note('A <b>watchlist</b> is ideas you\'re only watching — no money in yet. The live '
                '<b>character · RS</b> read tells you which are actually setting up vs just drifting.')
        + '<table class="tg-t"><thead><tr><th>Symbol</th><th>Sector · Cap</th><th class="r">CMP</th>'
          '<th>Character · RS <span class="mut">(live)</span></th><th></th></tr></thead>'
        + f'<tbody>{"".join(rows)}</tbody></table>'
        + _foot('Unlock to keep your own watchlists →'))


def _demo_performance() -> str:
    _rows, inv, cur, tot_pl = _positions_view(_demo_signals([p[0] for p in _DEMO_POSITIONS]))
    pl_abs = cur - inv
    return (_DEMO_CSS
        + '<h2>Performance <span class="sub" style="margin:0">demo book</span></h2>'
        + _note('<b>Performance</b> is the over-time scoreboard — XIRR, equity curve and '
                'drawdown across your books. It grows out of your real entries and holding history.')
        + '<div class="tg-kpi">'
        + _pl_kpi(tot_pl, "unrealised P&amp;L") + _kpi(f'₹{pl_abs:,.0f}', "gain (live)")
        + _kpi(f'₹{inv:,.0f}', "invested")
        + '</div>'
        + '<div class="tg-note" style="border-color:var(--line-2,#30363d);background:transparent">'
          'The full scoreboard (XIRR · equity curve · drawdown · per-book contribution) needs a '
          'real trade history — unlock your books to build it.</div>'
        + _foot('Unlock to see your performance →'))


def _demo_import() -> str:
    return (_DEMO_CSS
        + '<h2>Import <span class="sub" style="margin:0">demo book</span></h2>'
        + _note('<b>Import</b> bulk-loads a book from a CSV (symbol, qty, entry, date). '
                'It writes to your private books, so it\'s owner-only.')
        + '<div class="tg-note" style="border-color:var(--line-2,#30363d);background:transparent">'
          'Importing is disabled in the public demo. Grab the '
          '<a href="/dash/import/template.csv">CSV template</a> to see the format, then unlock to '
          'load your holdings.</div>'
        + _foot('Unlock to import your holdings →'))


# path → (nav-active key, page title, body builder). The keys ARE the tracker lens keys
# (lens_registry) so the reskin's sub-nav highlights the active tab. Single source of truth
# for which tracker paths are demo-served (see _DEMO_PAGES).
_DEMO_VIEW = {
    "/dash/tracker/dashboard":   ("dashboard",   "Tracker · demo book",     _demo_dashboard),
    "/dash/tracker/portfolios":  ("portfolios",  "Portfolios · demo book",  _demo_portfolios),
    "/dash/tracker/watchlists":  ("watchlists",  "Watchlists · demo book",  _demo_watchlists),
    "/dash/tracker/performance": ("performance", "Performance · demo book", _demo_performance),
    "/dash/tracker/import":      ("import",      "Import · demo book",      _demo_import),
}
_DEMO_PAGES = frozenset(_DEMO_VIEW)

# Back-compat alias: _demo_body is the dashboard overview (older callers / the error fallback).
_demo_body = _demo_dashboard


def _owner_form(bad: bool = False) -> str:
    warn = ('<div class="tg-note">That key didn\'t match — nothing unlocked.</div>' if bad else '')
    return (_DEMO_CSS
        + '<h2>Tracker <span class="sub" style="margin:0">owner unlock</span></h2>' + warn
        + '<div class="tg-note" style="border-color:var(--line-2,#30363d);background:transparent">'
          'The tracker\'s real books are private. If this is your deployment, enter the shared '
          'secret from the server\'s <code>.env</code> (<code>CHAT_SHARED_SECRET</code>); the '
          'browser stores only a derived token, never the secret.</div>'
        + '<form method="post" action="/dash/tracker/owner" style="display:flex;gap:8px;max-width:430px">'
          '<input type="password" name="key" placeholder="shared secret" autocomplete="off" '
          'style="flex:1;padding:9px 12px;border-radius:8px;border:1px solid var(--line-2,#30363d);'
          'background:var(--bg-2,#161b22);color:inherit"/>'
          '<button type="submit" style="padding:9px 16px;border-radius:8px;border:1px solid '
          'var(--line-2,#30363d);background:var(--bg-2,#161b22);color:inherit;cursor:pointer">Unlock</button>'
          '</form>'
        + '<div class="tg-foot"><a href="/dash/tracker/dashboard">← back to the demo book</a></div>')


def _edu_demo(active: str) -> str:
    """S-C education scaffold for the demo views — the SAME per-tab bottom-line texts as
    the owner pages (dashboard._TRACKER_BL, single source) + the reading-guide link.
    Fail-open: any import/render hiccup returns '' — the privacy gate never breaks over
    an education band."""
    try:
        from src.web import infographics as ifx
        from src.web.dashboard import _TRACKER_BL
        return (ifx.readability_css() + ifx.bottom_line(_TRACKER_BL[active])
                + ifx.how_to_read_link())
    except Exception:  # noqa: BLE001
        return ""


def _shell(title: str, body: str, active: str = "dashboard"):
    from fastapi.responses import HTMLResponse
    try:
        from src.web import dashboard as D
        # `active` is the tracker lens key (dashboard/portfolios/…) so the reskin's sub-nav
        # highlights the tab actually being viewed — the fix for the dead-tab symptom.
        html = D._shell(title, body, active)
        # The gate SHORT-CIRCUITS its own responses (demo pages + owner-unlock form), so they
        # never reach the left_rail HTTP middleware that every non-gated page flows through —
        # leaving the PUBLIC Tracker on the old horizontal sub-nav strip while Markets /
        # Strategies / etc. show the modern collapsible left rail (a visible inconsistency on
        # the first page an unauthenticated visitor lands on). Reshape here so the whole site
        # reads as one product. reshape_html is idempotent (its own head marker) + defensive
        # (returns its input on any miss), so this can never double-rail or take the gate down.
        try:
            from src.web import left_rail
            html = left_rail.reshape_html(html)
        except Exception:  # noqa: BLE001 — the rail is chrome; never let it break the gate
            pass
        return HTMLResponse(html)
    except Exception:  # noqa: BLE001 — shell must never take the gate down
        return HTMLResponse(body)


async def _dispatch(request, call_next):
    # Route the request FIRST, outside any try: a non-gated path must pass through with
    # its downstream exceptions untouched (an earlier version wrapped call_next in the
    # fail-closed try, which dressed EVERY app error site-wide as the demo page).
    try:
        gated = _gated(request.url.path)
    except Exception:  # noqa: BLE001
        gated = True
    if not gated:
        return await call_next(request)
    try:
        path = request.url.path

        if path == "/dash/tracker/owner":
            from fastapi.responses import RedirectResponse
            if request.method == "POST":
                form = await request.form()
                key = (form.get("key") or "").strip()
                sec = _secret()
                if sec and key == sec:
                    resp = RedirectResponse("/dash/tracker/dashboard", status_code=303)
                    resp.set_cookie(_COOKIE, _token(sec), max_age=365 * 24 * 3600,
                                    httponly=True, samesite="lax")
                    # also satisfy the inner perimeter tracker gate (its cookie name +
                    # semantics) so one unlock passes BOTH layers
                    resp.set_cookie("hermes_key", sec, max_age=180 * 24 * 3600,
                                    httponly=True, samesite="lax")
                    return resp
                return RedirectResponse("/dash/tracker/owner?bad=1", status_code=303)
            return _shell("Tracker · owner", _owner_form(bad="bad" in request.query_params))

        if not _is_owner(request):
            if request.method == "GET" and path in _DEMO_VIEW:
                active, title, build = _DEMO_VIEW[path]
                return _shell(title, _edu_demo(active) + build(), active)
            # non-owner mutation / export / personal detail -> the demo front door
            from fastapi.responses import RedirectResponse
            return RedirectResponse("/dash/tracker/dashboard", status_code=303)
    except Exception as e:  # noqa: BLE001 — a privacy gate fails CLOSED, never open
        log.warning("tracker_gate error on %s: %s", request.url.path, e)
        from fastapi.responses import HTMLResponse, RedirectResponse
        if request.method == "GET":
            try:
                return _shell("Tracker · demo book", _demo_body())
            except Exception:  # noqa: BLE001
                return HTMLResponse("Tracker temporarily unavailable.", status_code=503)
        return RedirectResponse("/dash/tracker/dashboard", status_code=303)
    # owner on a gated path: run the real handler OUTSIDE the gate's try, so a
    # downstream error surfaces as itself, never as the demo page
    return await call_next(request)


def install(app) -> bool:
    """Idempotent middleware install (left_rail pattern)."""
    try:
        if getattr(app.state, "_tracker_gate", False):
            return False
        from starlette.middleware.base import BaseHTTPMiddleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=_dispatch)
        app.state._tracker_gate = True
        log.info("tracker_gate installed (demo-book for non-owners)")
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("tracker_gate install skipped: %s", e)
        return False


def _selftest() -> int:
    assert _gated("/dash/tracker/dashboard") and _gated("/dash/track") and _gated("/dash/import")
    assert not _gated("/dash/track/quote") and not _gated("/dash/markets")
    assert not _gated("/dash/import/template.csv"), "the CSV format template must stay open"
    assert _token("x") != _token("y") and len(_token("s")) == 64
    b = _demo_body()
    assert "demo book" in b and "RELIANCE" in b and "tg-note" in b
    # the dead-tab fix: every sub-tab renders a DISTINCT body + carries the demo banner, and
    # its active key is the matching tracker lens key (so the reskin highlights the tab).
    bodies = {p: build() for p, (_a, _t, build) in _DEMO_VIEW.items()}
    assert len(set(bodies.values())) == len(_DEMO_VIEW), "demo sub-tabs must be distinct (not one shared page)"
    assert all("tg-note" in v for v in bodies.values()), "every demo tab keeps the synthetic-book banner"
    assert "Qty" in bodies["/dash/tracker/portfolios"], "Portfolios shows the positions table"
    assert "watchlist" in bodies["/dash/tracker/watchlists"].lower(), "Watchlists is watchlist-specific"
    assert "XIRR" in bodies["/dash/tracker/performance"], "Performance explains the scoreboard"
    assert "template.csv" in bodies["/dash/tracker/import"], "Import links the CSV template"
    # the richer demo: positions + watchlist now carry the sector + live thesis-health/RS reads
    # (structure asserted here; the live reads populate on the full-DB box, degrade to — on a thin
    # DB — so assert the COLUMNS, not the data, to keep the selftest DB-independent).
    assert "Thesis-health" in bodies["/dash/tracker/portfolios"], "Portfolios shows the thesis-health column"
    assert "Sector" in bodies["/dash/tracker/portfolios"], "Portfolios shows the sector column"
    assert "Character · RS" in bodies["/dash/tracker/watchlists"], "Watchlists shows the character·RS read"
    for p, (active, _t, _b) in _DEMO_VIEW.items():
        assert active in p, f"active key {active!r} should match its path {p}"
    f = _owner_form(bad=True)
    assert 'method="post"' in f and "didn" in f
    print("tracker_gate selftest OK — 5 distinct demo tabs, active-key highlight, "
          "template open, thesis-health/RS reads")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
