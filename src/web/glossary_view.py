"""glossary_view.py — the browsable Glossary / Methodology page (/dash/glossary).

The site-wide "explain every term" surface (primary-intent commitment #2). It renders the
SAME single source the `?` hover-popovers use (docs/metrics-glossary.md, the file
glossary.py parses) as ONE readable, filterable reference page — so a term can be looked
up directly, not only discovered by hovering. Page and popovers therefore can never drift.
Descriptive-only: how to read each signal, never the proprietary formula. Lives at the
Trust altitude (methodology / help).

Isolated new module (the rrg_view/rsband_view pattern): own APIRouter, durably mounted via
v2_surfaces._ROUTER_SPECS; imports only _shell (chrome) + reads the md file. Additive.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell   # chrome + CSS (import-safe; see rrg_view)

router = APIRouter()

_MD = Path(__file__).resolve().parents[2] / "docs" / "metrics-glossary.md"


def _inline(s: str) -> str:
    """Minimal inline markdown → HTML: escape first, then `code`, **bold**, *italic*."""
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    return s


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "sec"


def render() -> str:
    try:
        text = _MD.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return '<h1 class="uk-h1">Glossary</h1><div class="sub">Glossary source not found.</div>'
    fams: list[list] = []          # [title, slug, [row_html, ...]]
    cur: list | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## ") or line.startswith("### "):
            title = line.lstrip("# ").strip()
            cur = [title, _slug(title), []]
            fams.append(cur)
        elif line.startswith("> ") and cur is not None:
            cur[2].append(f'<div class="gv-intro">{_inline(line[2:].strip())}</div>')
        elif line.startswith("- ") and cur is not None:
            body = line[2:].strip()
            m = re.match(r"\*\*(.+?)\*\*\s*(.*)", body)
            if m:
                term = m.group(1).strip().strip(".").strip()
                rest = m.group(2).strip()
                cur[2].append(
                    f'<div class="gv-row"><div class="gv-term">{_inline("**" + term + "**")}</div>'
                    f'<div class="gv-def">{_inline(rest)}</div></div>')
            else:
                cur[2].append(f'<div class="gv-def gv-solo">{_inline(body)}</div>')
        # ignore the page title (#), --- rules, blank lines, and any prose outside families

    fams = [f for f in fams if f[2]]                 # drop empty sections
    n_terms = sum(1 for _t, _s, rows in fams for r in rows if 'class="gv-row"' in r)
    jump = " · ".join(f'<a href="#{s}">{html.escape(t)}</a>' for t, s, _ in fams)
    secs = "".join(
        f'<section id="{s}" class="gv-sec"><h2>{html.escape(t)}</h2>{"".join(rows)}</section>'
        for t, s, rows in fams)
    return (_CSS
            + '<h1 class="uk-h1">Glossary &amp; methodology</h1>'
            + f'<div class="sub" style="margin-bottom:10px">Every custom Patearn metric, defined '
              f'(<b>{n_terms}</b> terms). The same notes behind the “?” hover-help across the app — '
              'how to read each signal, never the proprietary formula.</div>'
            + '<input id="gvf" class="gv-filter" placeholder="Filter terms…  (e.g. RS MOM · credibility · capture · POC)" autofocus />'
            + f'<div class="gv-jump">{jump}</div>'
            + f'<div id="gvbody">{secs}</div>'
            + _JS)


_CSS = """<style>
.gv-filter{width:100%;max-width:560px;font-size:13px;background:var(--bg-1);color:var(--ink);
  border:1px solid var(--line-2);border-radius:8px;padding:8px 12px;margin:4px 0 10px}
.gv-jump{font-size:12px;color:var(--ink-3);margin-bottom:16px;line-height:1.9}
.gv-jump a{color:var(--ink-2);text-decoration:none;border-bottom:1px dotted var(--line-2)}
.gv-jump a:hover{color:var(--accent)}
.gv-sec{margin:0 0 22px;max-width:1000px}
.gv-sec h2{font-size:15px;color:var(--ink);border-bottom:1px solid var(--line-2);padding-bottom:5px;margin:0 0 8px}
.gv-intro{font-size:12px;color:var(--ink-2);font-style:italic;margin:0 0 8px;line-height:1.5}
.gv-row{display:grid;grid-template-columns:200px 1fr;gap:14px;padding:6px 0;border-bottom:1px solid var(--bg-2);align-items:start}
.gv-term{font-size:12.5px;color:var(--ink)}
.gv-term b{color:var(--ink);font-weight:600}
.gv-def{font-size:12.5px;color:var(--ink-2);line-height:1.5}
.gv-def code,.gv-term code{background:var(--bg-2);border:1px solid var(--line-2);border-radius:4px;
  padding:0 4px;font-size:11px;color:var(--ink-3)}
.gv-def b{color:var(--ink)}
.gv-solo{grid-column:1/-1}
@media (max-width:640px){.gv-row{grid-template-columns:1fr;gap:2px}}
</style>"""

_JS = """<script>(function(){
var f=document.getElementById('gvf'); if(!f) return;
var rows=[].slice.call(document.querySelectorAll('.gv-row,.gv-solo'));
var secs=[].slice.call(document.querySelectorAll('.gv-sec'));
function apply(){var q=(f.value||'').toLowerCase().trim();
  rows.forEach(function(r){ r.style.display=(!q||r.textContent.toLowerCase().indexOf(q)>=0)?'':'none'; });
  secs.forEach(function(s){ var vis=[].slice.call(s.querySelectorAll('.gv-row,.gv-solo'))
    .some(function(r){return r.style.display!=='none';}); s.style.display=vis?'':'none'; });}
f.addEventListener('input',apply);
// deep-link: /dash/glossary?q=DVPT prefills the filter (strategy cards land ON their term)
try{var q0=new URLSearchParams(location.search).get('q');
if(q0){f.value=q0; apply();}}catch(e){}
})();</script>"""


@router.get("/dash/glossary", response_class=HTMLResponse)
def glossary_page() -> HTMLResponse:
    return HTMLResponse(_shell("Glossary · patearn", render(), active="trust", wide=True))


def wire(app):
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/glossary" not in paths:
            app.include_router(router)
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger("hermes.glossary_view").warning("glossary wire skipped: %s", e)
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI(); app.include_router(router)
    r = TestClient(app).get("/dash/glossary")
    assert r.status_code == 200, r.status_code
    assert "Glossary" in r.text and "gv-row" in r.text and "RS-Momentum" in r.text, "render incomplete"
    print("glossary_view selftest OK — /dash/glossary 200, terms render")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
