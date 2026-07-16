"""strategies_view.py — the browsable Strategy Reference (/dash/strategy-ref).

Serves the canonical `docs/strategies/` layer (the README index + every page in `_PAGES`)
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
    "reversal-context":  ("reversal-context.md",  "Reversal Context"),
    "cci":               ("cci.md",               "CCI"),
    "harmonic":          ("harmonic.md",          "Harmonic"),
    "momentum-riskadj":  ("momentum-riskadj.md",  "Momentum / RISKADJ"),
    "patearn":           ("patearn.md",           "patearn"),
    "classic-screens":   ("classic-screens.md",   "Classic Screens"),
    "sector-rotation":   ("sector-rotation.md",   "Sector Rotation"),
    "union":             ("union.md",             "The Union"),
    "rule-lab":          ("rule-lab.md",          "Rule Lab"),
    "origins":           ("origins.md",           "Origins"),
}
_FILE_TO_SLUG = {fn: slug for slug, (fn, _lbl) in _PAGES.items()}

_ROUTE = "/dash/strategy-ref"

# Where each strategy LIVES on the site (Ramana 2026-07-15: "after viewing the details the
# interface should take me to the portfolio"). Rendered as a prominent hand-off strip at the
# top of every strategy page. Keys = _PAGES slugs; values = (href, button label).
_SURFACE: dict[str, tuple[str, str]] = {
    "dvpt":              ("/dash/stocks",                    "Open the Positioning screener"),
    "mep":               ("/dash/mep",                       "Open the Accum/Distrib board"),
    "wolfe-wave":        ("/dash/markets/wolfe-scan",        "Open the Wolfe scanner"),
    "relative-strength": ("/dash/markets/rrg",               "Open the Rotation map"),
    "cpr":               ("/dash/cpr",                       "Open the CPR screen"),
    "reversal-context":  ("/dash/screen2?rev=ri",            "Open Screen+ reversal context"),
    "cci":               ("/dash/concalls",                  "Open the Credibility board"),
    "harmonic":          ("/dash/harmonic",                  "Open the Harmonic scanner"),
    "momentum-riskadj":  ("/dash/momentum-scan",             "Open the Momentum scan"),
    "patearn":           ("/dash/screener",                  "Open the Screener"),
    "classic-screens":   ("/dash/classics",                  "Open the Classic Screens rosters"),
    "sector-rotation":   ("/dash/sector-rotation",           "Open the V17 portfolio (time-travel)"),
    "rule-lab":          ("/dash/rule-lab",                  "Open the Rule lab"),
}


def _surface_strip(slug: str) -> str:
    hit = _SURFACE.get(slug)
    if not hit:
        return ""
    href, label = hit
    return ("<div class='sr-surface'><a href='" + html.escape(href) + "'>" +
            html.escape(label) + " →</a><span class='sr-surface-note'>the live surface "
            "this page describes — data, filters and history</span></div>")


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


# ── public sanitizer (UX audit S-A / P0-5) ───────────────────────────────────
# docs/strategies/*.md are the INTERNAL canonical layer and carry governance
# metadata (Class / Status / Governing-decisions / Reconciled, session + decision
# IDs, commit hashes, "Ramana"). The public /dash/strategy-ref must never leak it.
# Stripped at RENDER time only — the source docs stay intact (Guardrail #9: no
# session/decision IDs or "Ramana" in rendered HTML).
_GOV_HDR = re.compile(r"\*\*(Class|Status|Governing decision|Reconciled)", re.I)
_META_LINE = re.compile(r"^\s*[-*]?\s*\*\*(Running state|Governing decision|Reconciled|Class|Status|Binding rule)\b", re.I)
# Whole sections that are writer-instructions, never viewer content: the shared page
# template, the README's maintenance protocol, and every page's "## Maintenance" tail.
_DROP_SECTION = re.compile(r"^\s*(#+)\s*(Shared template|Maintenance(?:\s+protocol)?)\b", re.I)


def _sub_ramana(m: re.Match) -> str:
    """Case-matched anonymization: 'Ramana'→'the desk', 'RAMANA'→'THE DESK' (+possessive).
    The 🧑 RAMANA origin-taxonomy label is UPPERCASE in the docs — a case-sensitive sub
    misses it (the original P0-5 escape)."""
    tok = m.group(0)
    poss = tok.lower().endswith(("'s", "’s"))
    if tok.isupper():
        return "THE DESK'S" if poss else "THE DESK"
    return "the desk's" if poss else "the desk"


def _drop_gov_col(lines: list[str]) -> list[str]:
    """Remove any table column whose header names an internal-governance field
    (Governing decision(s) / Reconciled / Class) — keeps the rest of the table."""
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        if ("|" in ln and i + 1 < n
                and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1])):
            hdr = _cells(ln)
            drop = [k for k, c in enumerate(hdr)
                    if re.search(r"governing decision|reconciled|^class$", c, re.I)]
            if drop:
                rebuild = lambda cs: "| " + " | ".join(
                    c for k, c in enumerate(cs) if k not in drop) + " |"
                out.append(rebuild(hdr)); out.append(rebuild(_cells(lines[i + 1]))); i += 2
                while i < n and "|" in lines[i] and lines[i].strip():
                    out.append(rebuild(_cells(lines[i]))); i += 1
                continue
        out.append(ln); i += 1
    return out


def _public(text: str) -> str:
    kept: list[str] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        # 1) drop the leading governance blockquote (the Class/Status/Reconciled header)
        if ln.lstrip().startswith(">") and _GOV_HDR.search(ln):
            while i < n and lines[i].lstrip().startswith(">"):
                i += 1
            continue
        # 2) drop internal-pointer / doc-maintenance metadata lines — INCLUDING their
        #    paragraph continuation lines (a "**Binding rule:** …" paragraph wraps; keeping
        #    the tail would render an orphaned fragment).
        if _META_LINE.match(ln) or re.search(r"do not archive", ln, re.I):
            i += 1
            while i < n and lines[i].strip() and not _is_block(lines[i]):
                i += 1
            continue
        # 3) drop writer-instruction sections whole (template · maintenance): from the
        #    heading to the next heading of the SAME or HIGHER level, fence-aware — the
        #    template's code fence holds heading-like lines that must not end the skip.
        m_sec = _DROP_SECTION.match(ln)
        if m_sec:
            lvl = len(m_sec.group(1))
            i += 1
            in_fence = False
            while i < n:
                s = lines[i].lstrip()
                if s.startswith("```"):
                    in_fence = not in_fence
                elif not in_fence:
                    m2 = re.match(r"^(#+)\s", lines[i])
                    if m2 and len(m2.group(1)) <= lvl:
                        break
                i += 1
            continue
        kept.append(ln)
        i += 1
    lines2 = _drop_gov_col(kept)                                       # 4) strip governance table columns
    text = "\n".join(lines2)
    # 5) phrase + token cleanup on the remaining prose
    text = re.sub(r"\s*\(permanent[^)]*\)", "", text, flags=re.I)          # (permanent — do not archive)
    text = re.sub(r"\s*\(and Ramana\)", "", text, flags=re.I)
    text = re.sub(r"future sessions", "readers", text, flags=re.I)
    text = re.sub(r",?\s*dictated by him\b", "", text, flags=re.I)         # origins.md phrasing
    text = re.sub(r"\bRamana(?:['’]s)?\b", _sub_ramana, text, flags=re.I)  # case-matched (catches 🧑 RAMANA)
    text = re.sub(r"\bthis folder\b", "this reference", text, flags=re.I)  # repo-speak → reader-speak
    text = re.sub(r"retire the \*\*deprecated\*\* column",
                  "avoid the **deprecated** names", text, flags=re.I)
    text = re.sub(r"\s*\(\s*(?:see\s+)?(?:memory|skill)\s+`[^`]+`\s*\)", "", text, flags=re.I)
    text = re.sub(r"(?:see\s+|;\s*)?\b(?:memory|skill)\s+`[^`]+`", "", text, flags=re.I)
    text = re.sub(r"\breconciled:[^\n.]*", "", text, flags=re.I)           # residual "Reconciled: …"
    text = re.sub(r"`[0-9a-f]{7,40}`", "", text)                          # commit hashes
    text = re.sub(r"\(\s*(?:[SD]\d{1,3}[a-z]?[\s,/·]*)+\)", "", text)      # "(D111, S109)" refs
    text = re.sub(r"\b[SD]\d{1,3}[a-z]?\b", "", text)                     # residual bare S###/D### ids
    text = re.sub(r"\b(20\d{2}-\d{2}-\d{2})[a-z]\b", r"\1", text)          # ledger ids "2026-07-15i" → date
    text = re.sub(r"[ \t]{2,}", " ", text)                               # collapse double spaces
    text = re.sub(r" *\(\s*\) *", " ", text)                             # empty parens
    text = re.sub(r" +([,.;·)])", r"\1", text)                           # space before punctuation
    return text


def _read(fn: str) -> str | None:
    try:
        return _public((_DIR / fn).read_text(encoding="utf-8"))
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
    return _CSS + _rail(slug) + _surface_strip(slug) + f"<article class='sr-doc'>{body}</article>"


_CSS = """<style>
.sr-rail{font-size:12px;color:var(--ink-3);margin:0 0 16px;line-height:2;border-bottom:1px solid var(--line-2);padding-bottom:8px}
.sr-rail a{color:var(--ink-2);text-decoration:none;border-bottom:1px dotted var(--line-2);padding-bottom:1px}
.sr-rail a:hover{color:var(--accent)}
.sr-rail a.on{color:var(--accent);font-weight:600;border-bottom-color:var(--accent)}
.sr-surface{display:flex;align-items:center;gap:12px;background:var(--bg-1);border:1px solid var(--accent);border-radius:8px;padding:9px 14px;margin:0 0 14px;max-width:960px}
.sr-surface a{color:var(--accent);font-weight:600;font-size:13.5px;text-decoration:none}
.sr-surface-note{font-size:11.5px;color:var(--ink-3)}
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
    # P0-5 (UX audit S-A): the PUBLIC reference must not leak internal governance/jargon.
    # Checks are CASE-INSENSITIVE — the original leak was all-caps "RAMANA" sailing past
    # a case-sensitive assert.
    for _slug, _b in [("index", render_index())] + [(s, render_page(s)) for s in _PAGES]:
        _low = _b.lower()
        for _bad in ("do not archive", "reconciled:", "governing decision", "future sessions",
                     "this folder", "binding rule", "maintenance protocol",
                     "same commit", "memory `", "skill `"):
            assert _bad not in _low, f"P0-5 leak on {_slug}: {_bad!r}"
        assert not re.search(r"(?i)\bramana\b", _b), f"P0-5 leak on {_slug}: 'Ramana'"
        assert not re.search(r"\b[SD]\d{2,3}[a-z]?\b", _b), f"P0-5 leak on {_slug}: a session/decision id"
    r404 = c.get(f"{_ROUTE}?p=nope")
    assert r404.status_code == 404, r404.status_code
    print(f"strategies_view selftest OK — index + {len(_PAGES)} pages 200, tables+callouts render, links rewritten")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
