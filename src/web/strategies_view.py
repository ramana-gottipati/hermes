"""strategies_view.py — the browsable Strategy Reference (/dash/strategy-ref).

Serves the canonical `docs/strategies/` layer (the README index + 9 strategy pages)
as readable /dash pages, the SAME way glossary_view serves metrics-glossary.md — so the
strategy playbook is browsable in-app, not only in the repo. Descriptive reference only
(never the proprietary formulas; those stay in code + calculations-and-weights.md).

A compact stdlib markdown renderer (headings · tables · blockquote callouts · nested
lists · code fences · inline bold/italic/code/links). Cross-links are rewritten so the
page works on the site: sibling strategy links → the served routes, `metrics-glossary.md`
→ the live /dash/glossary, and any other repo/code reference → plain text (never a dead
link). Lives at the Trust altitude, beside Glossary / How-to-read / Strategy-validation.

Isolated module (the glossary_view/rrg_view pattern): own APIRouter, durably mounted via
v2_surfaces._ROUTER_SPECS; imports only _shell (chrome). Reads the md files; additive.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell   # chrome + CSS (import-safe; see glossary_view)

router = APIRouter()

_DIR = Path(__file__).resolve().parents[2] / "docs" / "strategies"

# served slug → filename; also the nav order + short labels for the rail
_PAGES: dict[str, tuple[str, str]] = {
    "dvpt":              ("dvpt.md",              "DVPT"),
    "mep":               ("mep.md",              "MEP"),
    "wolfe-wave":        ("wolfe-wave.md",        "Wolfe Wave"),
    "relative-strength": ("relative-strength.md", "Relative Strength"),
    "cpr":               ("cpr.md",               "CPR"),
    "cci":               ("cci.md",               "CCI"),
    "harmonic":          ("harmonic.md",          "Harmonic"),
    "momentum-riskadj":  ("momentum-riskadj.md",  "Momentum / RISKADJ"),
    "patearn":           ("patearn.md",           "patearn"),
}
_FILE_TO_SLUG = {fn: slug for slug, (fn, _lbl) in _PAGES.items()}

_ROUTE = "/dash/strategy-ref"


# ── cross-link rewriting ─────────────────────────────────────────────────────
def _rewrite(url: str) -> str | None:
    """Map a doc-relative link target to a served href, or None if it should render
    as plain text (a repo/code reference the site does not serve — never a dead link)."""
    url = url.strip()
    if url.startswith(("http://", "https://", "mailto:")):
        return url
    if url.startswith("#"):
        return url                                   # in-page anchor
    path = url.split("#", 1)[0]
    if not path:
        return url
    base = path.rsplit("/", 1)[-1]
    if base == "README.md":
        return _ROUTE                                # the index
    if base in _FILE_TO_SLUG:
        return f"{_ROUTE}?p={_FILE_TO_SLUG[base]}"    # a sibling strategy page
    if base == "metrics-glossary.md":
        return "/dash/glossary"                      # the one other served doc
    return None                                      # code / other docs → plain text


# ── inline markdown ──────────────────────────────────────────────────────────
def _fmt(s: str) -> str:
    """Escape, then `code` / **bold** / *italic* (no links — handled in _inline)."""
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"<code>\1</code>", s)   # [[memory-ref]] → code (not a link)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    return s


_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(s: str) -> str:
    out, last = [], 0
    for m in _LINK_RE.finditer(s):
        out.append(_fmt(s[last:m.start()]))
        text, href = m.group(1), _rewrite(m.group(2))
        out.append(f'<a href="{html.escape(href)}">{_fmt(text)}</a>' if href else _fmt(text))
        last = m.end()
    out.append(_fmt(s[last:]))
    return "".join(out)


# ── block markdown ───────────────────────────────────────────────────────────
def _is_block(line: str) -> bool:
    ls = line.lstrip()
    return (line.startswith("#") or ls.startswith(">") or ls.startswith("```")
            or re.match(r"^\s*[-*]\s+", line) is not None
            or re.match(r"^\s*---+\s*$", line) is not None
            or "|" in line)


def _cells(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def _list_block(lines: list[str], i: int) -> tuple[str, int]:
    """Render a contiguous bullet list (with 1-level indent nesting) starting at i."""
    items: list[tuple[int, str]] = []
    while i < len(lines):
        m = re.match(r"^(\s*)[-*]\s+(.*)$", lines[i])
        if m:
            items.append((len(m.group(1)), m.group(2)))
            i += 1
        elif lines[i].strip() and lines[i].startswith(" ") and items:
            items[-1] = (items[-1][0], items[-1][1] + " " + lines[i].strip())  # continuation
            i += 1
        else:
            break
    base = min(ind for ind, _ in items)
    html_out, open_nested = ["<ul class='sr-ul'>"], False
    for ind, body in items:
        if ind > base and not open_nested:
            html_out.append("<ul class='sr-ul'>"); open_nested = True
        elif ind <= base and open_nested:
            html_out.append("</ul>"); open_nested = False
        html_out.append(f"<li>{_inline(body)}</li>")
    if open_nested:
        html_out.append("</ul>")
    html_out.append("</ul>")
    return "".join(html_out), i


def _md(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):                                   # fenced code
            i += 1; buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append(f"<pre class='sr-code'>{html.escape(chr(10).join(buf))}</pre>")
            continue

        if line.lstrip().startswith(">"):                               # blockquote callout
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append(f"<blockquote class='sr-quote'>{_md(chr(10).join(buf))}</blockquote>")
            continue

        if ("|" in line and i + 1 < n                                   # table
                and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1])):
            head = _cells(line); i += 2; body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(_cells(lines[i])); i += 1
            th = "".join(f"<th>{_inline(c)}</th>" for c in head)
            trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f"<div class='sr-tw'><table class='sr-tbl'><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)                        # heading
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl} class='sr-h{lvl}'>{_inline(m.group(2))}</h{lvl}>")
            i += 1; continue

        if re.match(r"^\s*---+\s*$", line):                             # hr
            out.append("<hr class='sr-hr'>"); i += 1; continue

        if re.match(r"^\s*[-*]\s+", line):                             # list
            block, i = _list_block(lines, i)
            out.append(block); continue

        if not stripped:                                                # blank
            i += 1; continue

        buf = [line]; i += 1                                            # paragraph
        while i < n and lines[i].strip() and not _is_block(lines[i]):
            buf.append(lines[i]); i += 1
        out.append(f"<p class='sr-p'>{_inline(' '.join(buf))}</p>")
    return "\n".join(out)


# ── page assembly ────────────────────────────────────────────────────────────
def _rail(active_slug: str | None) -> str:
    idx = ("<a href='%s'%s>Overview</a>" % (_ROUTE, "" if active_slug else " class='on'"))
    links = [idx] + [
        "<a href='%s?p=%s'%s>%s</a>" % (_ROUTE, slug, (" class='on'" if slug == active_slug else ""), html.escape(lbl))
        for slug, (_fn, lbl) in _PAGES.items()
    ]
    return "<nav class='sr-rail'>" + " · ".join(links) + "</nav>"


def _read(fn: str) -> str | None:
    try:
        return (_DIR / fn).read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None


def render_index() -> str:
    text = _read("README.md")
    body = _md(text) if text is not None else "<p class='sr-p'>Strategy reference source not found.</p>"
    return _CSS + _rail(None) + f"<article class='sr-doc'>{body}</article>"


def render_page(slug: str) -> str:
    fn = _PAGES[slug][0]
    text = _read(fn)
    body = _md(text) if text is not None else "<p class='sr-p'>Page source not found.</p>"
    return _CSS + _rail(slug) + f"<article class='sr-doc'>{body}</article>"


_CSS = """<style>
.sr-rail{font-size:12px;color:var(--ink-3);margin:0 0 16px;line-height:2;border-bottom:1px solid var(--line-2);padding-bottom:8px}
.sr-rail a{color:var(--ink-2);text-decoration:none;border-bottom:1px dotted var(--line-2);padding-bottom:1px}
.sr-rail a:hover{color:var(--accent)}
.sr-rail a.on{color:var(--accent);font-weight:600;border-bottom-color:var(--accent)}
.sr-doc{max-width:960px;font-size:13px;color:var(--ink-2);line-height:1.6}
.sr-h1{font-size:20px;color:var(--ink);margin:2px 0 10px}
.sr-h2{font-size:16px;color:var(--ink);border-bottom:1px solid var(--line-2);padding-bottom:5px;margin:22px 0 10px}
.sr-h3{font-size:14px;color:var(--ink);margin:18px 0 8px}
.sr-h4,.sr-h5,.sr-h6{font-size:13px;color:var(--ink);margin:14px 0 6px}
.sr-p{margin:8px 0}
.sr-doc a{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--line-2)}
.sr-doc a:hover{border-bottom-style:solid}
.sr-doc b{color:var(--ink)}
.sr-doc code{background:var(--bg-2);border:1px solid var(--line-2);border-radius:4px;padding:0 4px;font-size:11.5px;color:var(--ink-3)}
.sr-ul{margin:6px 0 6px 4px;padding-left:18px}
.sr-ul li{margin:3px 0}
.sr-hr{border:0;border-top:1px solid var(--line-2);margin:18px 0}
.sr-quote{border-left:3px solid var(--accent);background:var(--bg-1);padding:2px 14px;margin:12px 0;border-radius:0 6px 6px 0}
.sr-quote .sr-h2{border:0;font-size:14px;margin:8px 0 6px}
.sr-tw{overflow-x:auto;margin:12px 0}
.sr-tbl{border-collapse:collapse;font-size:12px;min-width:100%}
.sr-tbl th,.sr-tbl td{border:1px solid var(--line-2);padding:5px 9px;text-align:left;vertical-align:top}
.sr-tbl th{background:var(--bg-2);color:var(--ink);font-weight:600;white-space:nowrap}
.sr-code{background:var(--bg-2);border:1px solid var(--line-2);border-radius:6px;padding:10px 12px;font-size:11.5px;color:var(--ink-3);overflow-x:auto;white-space:pre}
</style>"""


@router.get(_ROUTE, response_class=HTMLResponse)
def strategy_ref(p: str = "") -> HTMLResponse:
    """The reference: bare route = the README index; `?p=<slug>` = one strategy page
    (single route + query param, like /dash/glossary?q= — nests cleanly under Trust)."""
    if not p:
        return HTMLResponse(_shell("Strategy reference · patearn", render_index(), active="trust", wide=True))
    if p not in _PAGES:
        return HTMLResponse(_shell("Strategy reference · patearn",
                                   _CSS + _rail(None) + "<article class='sr-doc'><p class='sr-p'>Unknown strategy page. "
                                   "<a href='" + _ROUTE + "'>Back to the index.</a></p></article>",
                                   active="trust", wide=True), status_code=404)
    return HTMLResponse(_shell(f"{_PAGES[p][1]} · Strategy reference", render_page(p), active="trust", wide=True))


def wire(app):
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if _ROUTE not in paths:
            app.include_router(router)
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger("hermes.strategies_view").warning("strategies_view wire skipped: %s", e)
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI(); app.include_router(router)
    c = TestClient(app)
    r = c.get(_ROUTE)
    assert r.status_code == 200 and "sr-doc" in r.text, ("index", r.status_code)
    # every served page renders, and rich constructs produce HTML (tables, callouts)
    seen_tbl = seen_quote = False
    for slug in _PAGES:
        rp = c.get(f"{_ROUTE}?p={slug}")
        assert rp.status_code == 200 and "sr-doc" in rp.text, (slug, rp.status_code)
        seen_tbl = seen_tbl or "sr-tbl" in rp.text
        seen_quote = seen_quote or "sr-quote" in rp.text
    assert seen_tbl, "no table rendered across pages"
    assert seen_quote, "no blockquote callout rendered across pages"
    # cross-link rewrite: a sibling link resolves to a served route; no raw markdown leaks
    dv = c.get(f"{_ROUTE}?p=dvpt").text
    assert f"{_ROUTE}?p=mep" in dv, "sibling link not rewritten"
    assert "](" not in dv, "raw markdown link leaked (unconverted)"
    assert 'href="mep.md"' not in dv, "un-rewritten sibling href leaked"
    r404 = c.get(f"{_ROUTE}?p=nope")
    assert r404.status_code == 404, r404.status_code
    print(f"strategies_view selftest OK — index + {len(_PAGES)} pages 200, tables+callouts render, links rewritten")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
