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
_DEMO_PAGES = {"/dash/tracker/dashboard", "/dash/tracker/portfolios",
               "/dash/tracker/watchlists", "/dash/tracker/performance",
               "/dash/tracker/import"}
_OPEN = ("/dash/track/quote",)          # market data, not personal

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


def _cmp_for(symbols: list[str]) -> dict:
    """Live CMPs for the demo book — defensive, {} on any failure."""
    out = {}
    try:
        from src.web import dashboard as D
        with D.get_conn() as conn:
            for s in symbols:
                try:
                    out[s] = D._capture_snapshot(conn, s)[0]
                except Exception:  # noqa: BLE001
                    out[s] = None
    except Exception:  # noqa: BLE001
        pass
    return out


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


def _demo_body() -> str:
    cmps = _cmp_for([p[0] for p in _DEMO_POSITIONS])
    rows, inv, cur = [], 0.0, 0.0
    for sym, qty, entry, since in _DEMO_POSITIONS:
        c = cmps.get(sym)
        inv += qty * entry
        cur += qty * (c or entry)
        pl = ((c - entry) / entry * 100.0) if c else None
        pl_txt = (f'<span style="color:var(--{ "up" if pl >= 0 else "down" })">{pl:+.1f}%</span>'
                  if pl is not None else "—")
        cmp_txt = f"₹{c:,.1f}" if c else "—"
        rows.append(f'<tr><td><a href="/dash/stock?sym={sym}" style="color:inherit">{sym}</a></td>'
                    f'<td class="r">{qty}</td><td class="r">₹{entry:,.1f}</td>'
                    f'<td class="r">{cmp_txt}</td><td class="r">{pl_txt}</td><td>{since}</td></tr>')
    tot_pl = ((cur - inv) / inv * 100.0) if inv else None
    watch = " · ".join(f'<a href="/dash/stock?sym={s}" style="color:inherit">{s}</a>'
                       for s in _DEMO_WATCH)
    return (_DEMO_CSS
        + '<h2>Tracker <span class="sub" style="margin:0">demo book</span></h2>'
        + '<div class="tg-note">🧪 <b>This is a demo book with sample positions</b> — the tracker '
          'is a private workspace, so a public visitor sees how it works, never anyone\'s real '
          'portfolio. Prices are live; the positions are invented. Build your own view by opening '
          'any stock and reading its lenses — the tracker adds books, alerts, P&amp;L and an '
          'import pipeline on top.</div>'
        + '<div class="tg-kpi">'
        + f'<div class="tg-box"><div class="n">1</div><div class="l">book (demo)</div></div>'
        + f'<div class="tg-box"><div class="n">{len(_DEMO_POSITIONS)}</div><div class="l">open positions</div></div>'
        + f'<div class="tg-box"><div class="n">₹{inv:,.0f}</div><div class="l">invested</div></div>'
        + f'<div class="tg-box"><div class="n">₹{cur:,.0f}</div><div class="l">value (live)</div></div>'
        + ('<div class="tg-box"><div class="n">'
           + (f'{tot_pl:+.1f}%' if tot_pl is not None else "—")
           + '</div><div class="l">P&amp;L</div></div>')
        + f'<div class="tg-box"><div class="n">{len(_DEMO_WATCH)}</div><div class="l">watchlist ideas</div></div>'
        + '</div>'
        + '<table class="tg-t"><thead><tr><th>Symbol</th><th class="r">Qty</th><th class="r">Entry</th>'
          '<th class="r">CMP</th><th class="r">P&amp;L</th><th>Since</th></tr></thead>'
        + f'<tbody>{"".join(rows)}</tbody></table>'
        + f'<div style="margin-top:10px;font-size:13px"><b>Watchlist:</b> {watch}</div>'
        + '<div class="tg-foot">Every symbol links to its full research dossier. '
          '<a href="/dash/tracker/owner">Owner? Unlock your books →</a></div>')


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


def _shell(title: str, body: str):
    from fastapi.responses import HTMLResponse
    try:
        from src.web import dashboard as D
        return HTMLResponse(D._shell(title, body, "tracker"))
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

        if _is_owner(request):
            owner = True
        else:
            if request.method == "GET" and path in _DEMO_PAGES:
                return _shell("Tracker · demo book", _demo_body())
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
    assert _token("x") != _token("y") and len(_token("s")) == 64
    b = _demo_body()
    assert "demo book" in b and "RELIANCE" in b and "tg-note" in b
    f = _owner_form(bad=True)
    assert 'method="post"' in f and "didn" in f
    print("tracker_gate selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
