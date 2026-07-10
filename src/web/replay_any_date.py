"""/dash/replay-any-date — the LIVE replay demo over the entitled /v1 API (charter P-05).

The Replay-the-Tape one-pager (/dash/replay) proves the zero-look-ahead claim on two fully
worked historical cases. This page is its live counterpart: pick ANY symbol and ANY date and
the page calls the real /v1 contract — the same authenticated, metered, provenance-stamped
API a client consumes — and renders exactly what was PUBLICLY KNOWABLE on that date, with
the knowable clock stamped (AUD-38 + D104):

  * credibility — the newest series point knowable on the date; ``knowable_from`` +
    ``knowable_basis`` (EVENT = real concall/transcript clock · MODELED = label-month end)
    ride the payload and ``pit.knowable_rule`` names the rule actually applied;
  * attention — the typed state-change queue as it stood (event-snapshot floor);
  * universe — survivorship-correct membership count on the date (delisted names retained).

Honesty contract: the page INVENTS NOTHING. Every value is lifted verbatim from the API
envelope (data / pit / _meta / _provenance); the API's own RFC-7807 errors render as-is
(a malformed date 422 is itself part of the demo); the §C no-edge caveat rides every
credibility panel; NO return is quoted anywhere; and each panel prints the exact curl a
client would run to reproduce it — same date, same answer, so the reader audits the demo.

Mechanics: the /v1 call is IN-PROCESS (fastapi TestClient over ``src.api.v1.build_app()``)
using the box's demo key (``settings.hermes_v1_dev_key`` ← .env HERMES_V1_DEV_KEY; tenant
seeded idempotently via ``keys.seed_dev_key`` and self-healed if a selftest teardown removed
it). The key value is never rendered, logged, or sent to the browser. No key on the box →
the page degrades to an honest "not provisioned" note (a trust surface must never error).

House pattern: pure isolated APIRouter, one route, imports nothing mutable at import time,
mounted via ``v2_surfaces._ROUTER_SPECS`` + a Trust Lens record. Descriptive-only language.

Route: GET /dash/replay-any-date?symbol=RELIANCE&as_of=YYYY-MM-DD
"""
from __future__ import annotations

import html
import json
import os
import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_DEF_SYMBOL = "ICICIPRULI"          # the worked EVENT-clock case (called 2019-01-22)
_DEF_AS_OF = "2019-01-25"
_HOSTNAME = "https://srv1704897.hstgr.cloud"
_SYM_RE = re.compile(r"^[A-Za-z0-9&\-]{1,20}$")

_client_cache: list = []            # [-1] = (TestClient, headers) once built


def _shell_fallback(title, body, active="", latest_date="", wide=False):
    return ("<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<body style='background:var(--bg-1);color:var(--ink);font-family:system-ui;"
            "max-width:1100px;margin:0 auto;padding:24px'>" + body + "</body>")


try:
    from src.web.dashboard import _shell
except Exception:                                   # pragma: no cover
    _shell = _shell_fallback


def _esc(s):
    return html.escape(str(s), quote=True)


# ── the in-process API client (the real contract, never a re-implementation) ────

def _demo_key() -> str:
    try:
        from src.core.settings import settings
        return (settings.hermes_v1_dev_key or "").strip()
    except Exception:                               # noqa: BLE001
        return (os.environ.get("HERMES_V1_DEV_KEY") or "").strip()


def _client():
    if _client_cache:
        return _client_cache[-1]
    from fastapi.testclient import TestClient
    from src.api.v1 import build_app
    c = TestClient(build_app(), raise_server_exceptions=False)
    _client_cache.append(c)
    return c


def _call(path: str) -> dict:
    """GET the real /v1 sub-app in-process with the demo key. On a 401 (a selftest
    teardown removed the 'dev' tenant) the stable key is re-seeded ONCE and the call
    retried — the demo self-heals. Returns {status, json|text}."""
    key = _demo_key()
    if not key:
        return {"status": 0, "error": "no-key"}
    c = _client()
    r = c.get(path, headers={"X-API-Key": key})
    if r.status_code == 401:
        try:
            os.environ.setdefault("HERMES_V1_DEV_KEY", key)
            from src.api.v1.keys import seed_dev_key
            seed_dev_key()                          # idempotent; same stable secret
            r = c.get(path, headers={"X-API-Key": key})
        except Exception:                           # noqa: BLE001
            pass
    try:
        return {"status": r.status_code, "json": r.json()}
    except Exception:                               # noqa: BLE001
        return {"status": r.status_code, "text": r.text[:2000]}


# ── rendering ────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.rad .intro{max-width:880px;font-size:13px;line-height:1.65;color:var(--ink-2);margin:0 0 14px}
.rad form.bar{display:flex;gap:10px;align-items:end;flex-wrap:wrap;border:1px solid var(--line-2);
  border-radius:10px;background:var(--bg-2);padding:12px 14px;margin:0 0 8px}
.rad form.bar label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--ink-3);
  text-transform:uppercase;letter-spacing:.06em}
.rad form.bar input{background:var(--bg-1);color:var(--ink);border:1px solid var(--line-2);
  border-radius:8px;padding:8px 10px;font-size:13px;min-width:150px}
.rad form.bar button{border:1px solid var(--accent);background:var(--accent-dim);color:var(--ink);
  border-radius:8px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer}
.rad .examples{font-size:12px;color:var(--ink-3);margin:0 0 18px}
.rad .examples a{margin-right:12px}
.rad .panel{border:1px solid var(--line-2);border-radius:10px;background:var(--bg-2);
  padding:14px 16px;margin:0 0 16px;max-width:980px}
.rad .panel h3{margin:0 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--ink-2)}
.rad .panel .sub{font-size:12px;color:var(--ink-3);margin:0 0 10px;line-height:1.5}
.rad .chips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px}
.rad .chip{border:1px solid var(--line-2);border-radius:999px;padding:3px 11px;font-size:12px;
  color:var(--ink-2);background:var(--bg-1)}
.rad .chip b{color:var(--ink);font-weight:600}
.rad .chip.ev{border-color:var(--accent)}
.rad table.kv{border-collapse:collapse;font-size:12.5px;margin:2px 0 10px}
.rad table.kv td{padding:3px 14px 3px 0;border-top:1px solid var(--bg-3);vertical-align:top}
.rad table.kv td:first-child{color:var(--ink-3);font-size:11.5px;white-space:nowrap}
.rad .note{font-size:11.5px;color:var(--ink-3);line-height:1.55;max-width:880px;margin:6px 0 2px}
.rad pre.curl{background:var(--bg-1);border:1px solid var(--line-2);border-radius:8px;
  padding:8px 12px;font-size:11.5px;overflow-x:auto;color:var(--ink-2);margin:8px 0 2px}
.rad details{margin:8px 0 0}
.rad details summary{font-size:11.5px;color:var(--ink-3);cursor:pointer}
.rad details pre{background:var(--bg-1);border:1px solid var(--line-2);border-radius:8px;
  padding:10px 12px;font-size:11px;overflow-x:auto;max-height:420px;color:var(--ink-2)}
.rad .absent{color:var(--ink-3);font-size:12.5px;line-height:1.55}
.rad .err{border-left:2px solid var(--warn,#b58900);padding:2px 0 2px 12px;font-size:12.5px;
  color:var(--ink-2);line-height:1.6}
</style>"""

_RULE_GLOSS = ("Two-tier knowable clock (D104): <b>EVENT</b> = the period's real public clock "
               "(concall held / transcript published — the later of the two); <b>MODELED</b> = "
               "no captured clock, so the point counts as knowable only once its label month "
               "completes. Result filings are never used as a clock for call-derived content "
               "(filings usually precede the call — the leak direction).")


def _curl(path: str) -> str:
    return (f'curl -s -H "X-API-Key: $PATEARN_KEY" "{_HOSTNAME}/v1{path}"')


def _raw(obj) -> str:
    return ("<details><summary>raw envelope (verbatim)</summary><pre>"
            + _esc(json.dumps(obj, indent=2, ensure_ascii=False)) + "</pre></details>")


def _chip(label, value, cls="") -> str:
    return f'<span class="chip {cls}">{_esc(label)} <b>{_esc(value)}</b></span>'


def _problem(res: dict) -> str:
    j = res.get("json") or {}
    title = j.get("title") or res.get("text") or "request failed"
    return (f'<div class="err">The API answered <b>{res["status"]}</b> (RFC-7807, shown '
            f'verbatim — the contract validates before it serves): {_esc(title)}</div>'
            + (_raw(j) if j else ""))


def _pit_chips(pit: dict, extra: dict | None = None) -> str:
    chips = []
    if pit.get("as_of"):
        chips.append(_chip("requested as-of", pit["as_of"]))
    for k, lab in (("knowable_from", "knowable from"), ("served_snapshot", "served snapshot")):
        v = (extra or {}).get(k) or pit.get(k)
        if v:
            chips.append(_chip(lab, v, "ev"))
    basis = (extra or {}).get("knowable_basis")
    if basis:
        chips.append(_chip("basis", basis, "ev" if basis == "EVENT" else ""))
    if pit.get("knowable_rule"):
        chips.append(_chip("rule applied", pit["knowable_rule"]))
    return '<div class="chips">' + "".join(chips) + "</div>" if chips else ""


def _panel_credibility(symbol: str, as_of: str) -> str:
    path = f"/securities/{symbol}/credibility?as_of={as_of}"
    res = _call(path)
    body = [f'<h3>credibility · {_esc(symbol)}</h3>',
            '<div class="sub">The guidance track-record as it was publicly knowable on the '
            'requested date — the newest settled series point whose knowable clock is at or '
            'before it.</div>']
    if res["status"] == 200:
        j = res["json"]
        cred = (j.get("data") or {}).get("credibility") or {}
        pit = (j.get("data") or {}).get("pit") or {}
        body.append(_pit_chips(pit, {"knowable_from": cred.get("knowable_from"),
                                     "knowable_basis": cred.get("knowable_basis")}))
        if cred.get("available") is False:
            body.append(f'<div class="absent">Typed absence (never a bare null): '
                        f'{_esc(cred.get("reason", ""))}</div>')
        else:
            rows = [("track record", cred.get("track_record")),
                    ("effective period", cred.get("as_of")),
                    ("promises resolved", cred.get("n_resolved")),
                    ("guidance accuracy", cred.get("guidance_accuracy")),
                    ("momentum", cred.get("momentum")),
                    ("trend", cred.get("trend"))]
            body.append('<table class="kv">' + "".join(
                f"<tr><td>{_esc(k)}</td><td>{_esc(v if v is not None else '—')}</td></tr>"
                for k, v in rows) + "</table>")
        note = (j.get("data") or {}).get("note")
        if note:
            body.append(f'<div class="note">{_esc(note)}</div>')
        body.append(_raw(j))
    elif res["status"] == 0:
        return ""                                   # no key — page-level note covers it
    else:
        body.append(_problem(res))
    body.append(f'<pre class="curl">{_esc(_curl(path))}</pre>')
    return '<div class="panel">' + "".join(body) + "</div>"


def _panel_attention(as_of: str) -> str:
    path = f"/attention?as_of={as_of}"
    res = _call(path)
    body = ['<h3>attention · market-wide</h3>',
            '<div class="sub">The typed state-change queue AS IT STOOD on the date — events '
            'from the newest computed snapshot at or before it (a weekend resolves to the '
            'prior batch; before the feed began, the honest answer is empty).</div>']
    if res["status"] == 200:
        j = res["json"]
        data = j.get("data") or {}
        body.append(_pit_chips(data.get("pit") or {}))
        rows = data.get("attention") or []
        if rows:
            body.append('<table class="kv"><tr><td>symbol</td><td>lens</td><td>event</td>'
                        '<td>from → to</td><td>event date</td></tr>' + "".join(
                f"<tr><td><b>{_esc(r.get('symbol'))}</b></td><td>{_esc(r.get('lens'))}</td>"
                f"<td>{_esc(r.get('event_type'))}</td>"
                f"<td>{_esc(r.get('from_state'))} → {_esc(r.get('to_state'))}</td>"
                f"<td>{_esc(r.get('as_of'))}</td></tr>" for r in rows) + "</table>")
        else:
            body.append('<div class="absent">No events were knowable by this date — the bus '
                        'seeds from its first computed batch; earlier dates answer honestly '
                        'empty rather than back-filled.</div>')
        body.append(_raw(j))
    elif res["status"] == 0:
        return ""
    else:
        body.append(_problem(res))
    body.append(f'<pre class="curl">{_esc(_curl(path))}</pre>')
    return '<div class="panel">' + "".join(body) + "</div>"


def _panel_universe(as_of: str) -> str:
    path = f"/universe?as_of={as_of}"
    res = _call(path)
    body = ['<h3>universe · membership on the date</h3>',
            '<div class="sub">Survivorship-correct membership replay — names are counted if '
            'listed on the date, INCLUDING those that later delisted (the spine keeps them).'
            '</div>']
    if res["status"] == 200:
        j = res["json"]
        d = j.get("data") or {}
        rows = [("listed on the date", d.get("universe_on_as_of")),
                ("mechanism", d.get("as_of_mechanism")),
                ("securities in spine", d.get("total_securities")),
                ("archive floor", d.get("archive_floor"))]
        body.append('<table class="kv">' + "".join(
            f"<tr><td>{_esc(k)}</td><td>{_esc(v if v is not None else '—')}</td></tr>"
            for k, v in rows) + "</table>")
        body.append(_raw(j))
    elif res["status"] == 0:
        return ""
    else:
        body.append(_problem(res))
    body.append(f'<pre class="curl">{_esc(_curl(path))}</pre>')
    return '<div class="panel">' + "".join(body) + "</div>"


@router.get("/dash/replay-any-date", response_class=HTMLResponse)
def replay_any_date(symbol: str = _DEF_SYMBOL, as_of: str = _DEF_AS_OF):
    """The P-05 demo surface. Bad inputs are shown as the API's own answers — the
    validation IS the product being demonstrated."""
    symbol = (symbol or _DEF_SYMBOL).strip().upper()[:20]
    as_of = (as_of or _DEF_AS_OF).strip()[:10]
    body = [_CSS, '<div class="rad">']
    body.append(
        '<div class="intro"><b>Replay any date.</b> The worked one-pager '
        '(<a href="/dash/replay">Replay the Tape</a>) demonstrates zero look-ahead on two '
        'historical cases; this page is the live counterpart — every query below goes '
        'through the entitled <code>/v1</code> API (auth, metering, provenance stamps and '
        'all) and renders exactly what was publicly knowable on the date you pick. Nothing '
        'on this page is authored by the page: values, absences and errors are the API\'s '
        'own, and each panel carries the curl that reproduces it. Same date, same answer. '
        'Descriptive record only — nothing here is a recommendation or a performance '
        'claim.</div>')
    body.append(f'<div class="note" style="margin:0 0 14px">{_RULE_GLOSS}</div>')
    body.append(
        '<form class="bar" method="get" action="/dash/replay-any-date">'
        f'<label>symbol<input name="symbol" value="{_esc(symbol)}" '
        'pattern="[A-Za-z0-9&amp;\\-]{1,20}" required></label>'
        f'<label>as of (YYYY-MM-DD)<input name="as_of" value="{_esc(as_of)}" '
        'placeholder="2019-01-25" required></label>'
        '<button type="submit">replay</button></form>')
    body.append(
        '<div class="examples">worked examples: '
        f'<a href="/dash/replay-any-date?symbol={_DEF_SYMBOL}&amp;as_of={_DEF_AS_OF}">'
        f'{_DEF_SYMBOL} · {_DEF_AS_OF} (real call clock — the Feb-labeled point, knowable '
        'Jan-22)</a> '
        f'<a href="/dash/replay-any-date?symbol={_DEF_SYMBOL}&amp;as_of=2019-01-21">'
        'same name, one day before the call (the prior point serves — no leak)</a> '
        '<a href="/dash/replay-any-date?symbol=TANLA&amp;as_of=2020-06-30">TANLA · '
        '2020-06-30</a> '
        '<a href="/dash/replay-any-date?symbol=RELIANCE&amp;as_of=2026-07-09">RELIANCE · '
        '2026-07-09 (recent — the event bus as it stood)</a></div>')

    if not _demo_key():
        body.append(
            '<div class="panel"><h3>demo key not provisioned</h3><div class="absent">'
            'The /v1 API is live on this box, but no demo key is configured '
            '(<code>HERMES_V1_DEV_KEY</code> in <code>/opt/hermes/.env</code>), so this '
            'page cannot call it on your behalf. Provision the key, restart the API, and '
            'reload — or call the API directly with your own key (see '
            '<a href="/v1/openapi.json">the contract</a>).</div></div>')
    elif not _SYM_RE.match(symbol):
        body.append('<div class="panel"><h3>input</h3><div class="err">Symbol must be '
                    '1-20 characters of A-Z, 0-9, &amp; or - (NSE symbol form).</div></div>')
    else:
        body.append(_panel_credibility(symbol, as_of))
        body.append(_panel_attention(as_of))
        body.append(_panel_universe(as_of))

    body.append(
        '<div class="note">Cross-checks for the diligence reader: the per-dataset boundary '
        'lives on <a href="/dash/coverage">Coverage</a>; the detection spec-sheets '
        '(failures included) on <a href="/dash/spec-sheets">Spec sheets</a>; the assembled '
        'procurement artifact on <a href="/dash/evidence-pack">Evidence pack</a>; the '
        'machine contract at <a href="/v1/openapi.json">/v1/openapi.json</a>.</div>')
    body.append("</div>")
    return HTMLResponse(_shell("Replay any date", "".join(body), active="replay-any-date"))
