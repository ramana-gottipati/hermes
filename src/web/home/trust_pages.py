"""src/web/home/trust_pages.py — the Graphite Trust / Proof estate (lane W5, milestone M6).

The 11 classic `trust` surfaces, rebuilt in the Graphite identity as EIGHT declared children of
`/dash/home` plus one JSON-free answer endpoint. Consolidation map (the parity ledger carries the
same verdicts):

    coverage          -> /dash/home/proof          (the Proof hub — what we can and cannot prove)
    testing           -> /dash/home/validation     (FLAGSHIP: the published falsification record)
    evidence-pack     -> /dash/home/validation?pack=1   (MERGED — the print/procurement assembly)
    spec-sheets       -> /dash/home/prereg         (the pre-registered study ledger + gate hashes)
    rule-lab          -> /dash/home/rule-lab       (shareable verdict URLs, ratified §K.4)
    replay-any-date   -> /dash/home/replay         (FLAGSHIP: zero look-ahead, driven by the visitor)
    glossary          -> /dash/home/glossary       (261 terms, the SAME docs/metrics-glossary.md)
    strategy-ref      -> /dash/home/strategy-ref   (16 pages, the SAME docs/strategies/)
    reading-guide     -> /dash/home/guide          (the newcomer exit + the M6 journey layer)
    pat               -> the floating dock, EXTENDED (see pat_dock) + GET /dash/home/pat/ask
    inbox             -> NA (an owner review workflow, not a visitor surface)

Standing verdict recorded on the hub: **nothing in this estate is paywalled.** The ratified Part III
§J contract says evidence is never gated, only convenience may be — and every page here IS evidence.
Free therefore gets the complete record; the tier mechanism appears only as `C.learn()` guidance,
which Pro hides to read denser. No `pro_teaser` anywhere in this estate, deliberately.

ADOPTION NOTE for other lanes (zero shared-file edits required):
    from src.web.home import journey
    return HTMLResponse(shell.shell(title, journey.nudge() + body,
                                    current=..., extra_head=journey.assets(), pat_html=pat))
`journey.assets()` moves the standing "New here? How to read →" control into the existing top bar by
progressive enhancement, so `shell.py` never has to change. For the Today page, the Replay card is
`journey.replay_card(trust_reads.replay_facts(sym, as_of))` — a component, ready to drop into
`_compose`'s rail in ONE line by whoever owns that file.
"""
from __future__ import annotations

import html as _html
import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.web.home import components as C
from src.web.home import journey, shell
from src.web.home import trust_reads as R

router = APIRouter()

_FENCE_TRUST = ("Descriptive record only. Everything on these pages is past data and published "
                "method — never advice, a recommendation, or a performance claim.")

_PAGES = (("/dash/home/proof", "Proof", "what we can and cannot prove"),
          ("/dash/home/validation", "Validation record", "what survived the gauntlet — and what died"),
          ("/dash/home/prereg", "Pre-registered studies", "the gate, written before the run"),
          ("/dash/home/rule-lab", "Rule lab", "test your own rule, share the verdict"),
          ("/dash/home/replay", "Replay any date", "zero look-ahead, proved on demand"),
          ("/dash/home/glossary", "Glossary", "every metric, in plain English"),
          ("/dash/home/strategy-ref", "Strategy reference", "one canonical page per strategy"),
          ("/dash/home/guide", "How to read", "the five-minute orientation"))


# ── local atoms ─────────────────────────────────────────────────────────────────────
def _sym(symbol) -> str:
    """A symbol link into the GRAPHITE stock page (`?sym=`, never `?symbol=`)."""
    s = C.esc(symbol)
    return '<a class="g-syma" href="/dash/home/stock?sym=' + s + '">' + s + "</a>"


def _scroll(body_html: str, h: int = 320) -> str:
    """A fixed-height box that scrolls INTERNALLY (standing correction #3) — never a flat endless
    page. The height is the contract; the content scrolls inside it."""
    return ('<div class="g-tscroll" style="max-height:' + str(int(h)) + 'px" tabindex="0" '
            'role="region" aria-label="scrollable detail">' + body_html + "</div>")


def _kv(rows) -> str:
    out = ['<table class="g-tkv">']
    for k, v in rows:
        out.append("<tr><th>" + C.esc(k) + "</th><td>" + C.esc(v) + "</td></tr>")
    out.append("</table>")
    return "".join(out)


def _nav_strip(current: str) -> str:
    items = "".join(
        '<a class="g-tnav-i' + (" on" if href == current else "") + '" href="' + C.safe_url(href) + '">'
        '<b>' + C.esc(label) + "</b><span>" + C.esc(sub) + "</span></a>"
        for href, label, sub in _PAGES)
    return '<nav class="g-tnav" aria-label="Proof pages">' + items + "</nav>"


def _page(title: str, body: str, current_dest: str = "Proof", conn=None) -> HTMLResponse:
    """Every Trust page: the M6 layer (standing help + the one-shot nudge) + the shared fence."""
    pat = ""
    if conn is not None:
        try:
            from src.web.home import pat_dock
            pat = pat_dock.dock_html(conn)
        except Exception:  # noqa: BLE001
            pat = ""
    head = journey.assets() + _CSS
    shell_body = (journey.help_link() + journey.nudge()
                  + '<div class="g-trust">' + body + journey.exits_block() + "</div>")
    return HTMLResponse(shell.shell(title, shell_body, extra_head=head,
                                    current=current_dest, pat_html=pat))


def _conn():
    """A read-only-ish connection, or None. Never raises — a Trust page must never 500."""
    try:
        from src.core.db import get_conn
        cm = get_conn()
        conn = cm.__enter__()
        conn.row_factory = __import__("sqlite3").Row
        return cm, conn
    except Exception:  # noqa: BLE001
        return None, None


def _close(cm):
    try:
        if cm is not None:
            cm.__exit__(None, None, None)
    except Exception:  # noqa: BLE001
        pass


# ── a small, DOM-safe markdown renderer (strategy docs) ─────────────────────────────
_LINK = re.compile(r"\[([^\]]{1,120})\]\(([^)\s]{1,300})\)")
_BOLD = re.compile(r"\*\*([^*]{1,200})\*\*")
_CODE = re.compile(r"`([^`]{1,200})`")


def _inline(s: str) -> str:
    """Escape FIRST, then re-introduce a closed set of inline forms. Nothing from the document can
    ever become markup (the `components.py` DOM-safety discipline)."""
    out = C.esc(s)
    def link(m):
        text, url = m.group(1), m.group(2)
        if url.endswith(".md") or url.startswith("../") or url.startswith("./"):
            slug = url.rsplit("/", 1)[-1][:-3].lower() if url.endswith(".md") else ""
            if slug and any(p["slug"] == slug for p in R.strategy_pages()):
                return '<a href="/dash/home/strategy-ref?p=' + C.esc(slug) + '">' + text + "</a>"
            return text                      # an internal doc path is NOT a public link
        return '<a href="' + C.safe_url(url) + '" rel="noopener">' + text + "</a>"
    out = _LINK.sub(link, out)
    out = _BOLD.sub(r"<b>\1</b>", out)
    out = _CODE.sub(r'<code class="g-num">\1</code>', out)
    return out


def _md(text: str) -> str:
    """Markdown -> HTML for the sanitized strategy docs. Headings, paragraphs, lists, tables,
    blockquotes and fenced code — nothing else, all escaped."""
    html_out, buf_list, in_fence, table = [], [], False, []
    def flush_list():
        if buf_list:
            html_out.append("<ul>" + "".join("<li>" + x + "</li>" for x in buf_list) + "</ul>")
            buf_list.clear()
    def flush_table():
        if table:
            head, body = table[0], [r for r in table[1:] if not set(r) <= set("-: ")]
            body = [r for r in body if not all(set(c.strip()) <= set("-:") for c in r)]
            html_out.append('<div class="g-tscroll" style="max-height:300px" tabindex="0"><table class="g-tmd">'
                            + "<tr>" + "".join("<th>" + _inline(c) + "</th>" for c in head) + "</tr>"
                            + "".join("<tr>" + "".join("<td>" + _inline(c) + "</td>" for c in r) + "</tr>"
                                      for r in body) + "</table></div>")
            table.clear()
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            flush_list(); flush_table()
            html_out.append("<pre class='g-tpre'>" if in_fence else "</pre>")
            continue
        if in_fence:
            html_out.append(C.esc(line) + "\n")
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush_list()
            table.append([c.strip() for c in line.strip().strip("|").split("|")])
            continue
        flush_table()
        if not line.strip():
            flush_list()
            continue
        if line.startswith("#"):
            flush_list()
            lvl = min(len(line) - len(line.lstrip("#")), 4)
            tag = {1: "h2", 2: "h3", 3: "h4", 4: "h5"}[max(lvl, 1)]
            html_out.append("<" + tag + ">" + _inline(line.lstrip("#").strip()) + "</" + tag + ">")
            continue
        if line.lstrip().startswith(("- ", "* ")):
            buf_list.append(_inline(line.lstrip()[2:]))
            continue
        if line.lstrip().startswith(">"):
            flush_list()
            html_out.append('<blockquote class="g-tq">' + _inline(line.lstrip().lstrip(">").strip())
                            + "</blockquote>")
            continue
        flush_list()
        html_out.append("<p>" + _inline(line.strip()) + "</p>")
    flush_list(); flush_table()
    return "".join(html_out)


# ── 1. the Proof hub (classic: coverage) ────────────────────────────────────────────
@router.get("/dash/home/proof", response_class=HTMLResponse, include_in_schema=False)
def proof(request: Request) -> HTMLResponse:
    """The Proof hub — the front door of the trust estate. Leads with the honest boundary
    ("what we do NOT claim"), then the live coverage/settlement snapshot, then the directory."""
    cm, conn = _conn()
    try:
        snap = R.coverage(conn)
        reg = R.provenance_registry()
    finally:
        _close(cm)

    boundary = C.zone(
        "What we do not claim", "published boundary",
        "<ul class='g-tlist'>"
        "<li><b>No alpha claim.</b> No strategy here is a fundable net-of-cost edge versus the "
        "index. The one participation-fundable corner is stated with its capacity, and everything "
        "else is descriptive.</li>"
        "<li><b>No prediction.</b> Every number describes past tape from primary exchange sources. "
        "Nothing forecasts.</li>"
        "<li><b>No paywall on evidence.</b> Every page in this estate is complete on the Free tier. "
        "Convenience may cost; the record never does.</li>"
        "<li><b>Failures are published.</b> Approaches we killed stay on the site with their "
        "numbers — that is what the validation record is for.</li></ul>"
        + C.learn("This page exists so you can check us rather than trust us. Start anywhere; "
                  "every number below names the table it came from."),
        sub="the honest boundary")

    if snap:
        uni = C._d(snap.get("universe"))
        cci = C._d(snap.get("cci"))
        funnel = C._d(cci.get("funnel"))
        tiles = "".join(C.tile(lab, C._num(val, 0) if val is not None else "—", sub)
                        for lab, val, sub in (
                            ("Names in the universe", uni.get("active"), "active NSE cash"),
                            ("Data classes declared", len(reg) or None, "each with source + grain"),
                            ("Scored for credibility", funnel.get("scored"), "concall-derived"),
                            ("Robust core (≥10)", funnel.get("ge10"), "enough calls to mean something")))
        cov_body = ('<div class="g-tiles">' + tiles + "</div>"
                    + _scroll(_class_table(snap), 340)
                    + C.learn("Coverage is a funnel, not a badge. Most names never reach the "
                              "robust core — showing the drop-off is the point."))
        cov = C.zone("Coverage & settlement", "provenance · nightly", cov_body,
                     sub="what is actually covered, and how well")
    else:
        cov = C.zone("Coverage & settlement", "provenance · nightly",
                     journey.teaching_empty(
                         "The coverage snapshot counts every symbol and data class we hold and "
                         "shows how many survive each quality step. It needs the nightly "
                         "provenance tables, which have not been built in this environment.",
                         "/dash/home/prereg", "See the pre-registered studies instead"),
                     sub="what is actually covered, and how well")

    return _page("Proof", _h1("Proof", "Check us, don't trust us.") + boundary + cov
                 + C.zone("Everything in the record", "directory", _nav_strip("/dash/home/proof"),
                          sub="eight ways to audit us"),
                 conn=None)


def _class_table(snap: dict) -> str:
    classes = C._d(snap).get("classes") or []
    if not classes:
        return journey.teaching_empty(
            "One row per data class — its primary source, how many symbols or days it covers, and "
            "how fresh it is. It appears once the provenance registry has been built.",
            "/dash/home/glossary", "Read what the metrics mean")
    out = ['<table class="g-tt"><tr><th>Data class</th><th>Primary source</th><th>Covers</th>'
           "<th>Grain</th><th>Latest</th></tr>"]
    for c in classes:
        c = C._d(c)
        n = c.get("n")
        out.append("<tr><td>" + C.esc(c.get("label") or c.get("key") or "—") + "</td>"
                   "<td>" + C.esc(c.get("source") or "—") + "</td>"
                   '<td class="g-num">' + (f"{int(n):,} {C.esc(c.get('n_unit') or '')}" if n else "—") + "</td>"
                   "<td>" + C.esc(c.get("grain") or "—") + "</td>"
                   '<td class="g-num">' + C.esc(c.get("latest") or "—") + "</td></tr>")
    out.append("</table>")
    return "".join(out)


# ── 2. the validation record (classic: testing + evidence-pack) ─────────────────────
@router.get("/dash/home/validation", response_class=HTMLResponse, include_in_schema=False)
def validation(request: Request) -> HTMLResponse:
    """FLAGSHIP — the skeptic's landing page: the published falsification record. `?pack=1` renders
    the print/procurement assembly (the classic `evidence-pack`, merged in as a view of the same
    material rather than a ninth page nobody can place)."""
    pack = str(request.query_params.get("pack", "")).strip() in ("1", "true", "yes")
    v = R.validation()
    holds = R.validation_holdings() if v.get("present") else {}
    blocking = R.blocking_models()

    lead = C.zone(
        "The record", "strategy_registry · walk-forward",
        "<p class='g-tp'>Every strategy we have built is listed here with the number that decides "
        "it: <b>net return/vol after realistic costs</b>, against the Nifty-500 buy-and-hold "
        "benchmark. Most of ours lose to that benchmark. We publish them anyway — a research "
        "record that only contains winners is not a record.</p>"
        + C.learn("Return/vol is the annualised mean return divided by its volatility — no "
                  "risk-free rate is subtracted, so it is not the textbook ratio of that name. "
                  "Higher is steadier per unit of return; the benchmark's is 0.89."),
        sub="what survived, and what did not")

    if v.get("rows"):
        body = _scroll(_verdict_table(v["rows"], holds), 420)
        body += C.prov("strategy_runs", f"{v['n_runs']:,} runs recorded")
        rec = C.zone("Strategy verdicts", "research.db · per run", body,
                     sub=f"{len(v['rows'])} strategies")
    else:
        rec = C.zone("Strategy verdicts", "research.db · per run",
                     journey.teaching_empty(
                         "This table lists every strategy with its latest walk-forward run — net "
                         "return/vol, CAGR, max drawdown, annual cost and capacity. It reads the "
                         "research database, which is not present in this environment (it lives on "
                         "the box beside the nightly research jobs). Absence is shown as absence, "
                         "never as a fabricated number.",
                         "/dash/home/prereg", "Read the pre-registered gates instead"),
                     sub="the walk-forward results")

    dead = C.zone(
        "Recorded dead", "docs/strategy-ledger.md · verbatim",
        (_scroll(_blocking_table(blocking), 340) if blocking else journey.teaching_empty(
            "The blocking ledger lists approaches we tested and killed, verbatim, so nobody "
            "re-runs them by accident. It is read from the strategy ledger.",
            "/dash/home/rule-lab", "Test a rule against the ledger")),
        sub="approaches we killed, with their numbers")

    packlink = ('<p class="g-tp"><a class="g-btn" href="/dash/home/validation?pack=1">'
                "Assemble the print pack →</a> <span class='g-tsub'>one continuous document: "
                "the boundary statements, the pre-registered gates, the coverage matrix and this "
                "record — for a reviewer who wants it offline.</span></p>")

    if pack:
        sheets = R.spec_sheets()
        body = (_h1("Evidence pack", "One continuous document, assembled from the live record.")
                + C.fence(_FENCE_TRUST) + lead + rec + dead
                + C.zone("Pre-registered studies", "prereg_registry", _sheets_html(sheets), sub="the gate came first")
                + C.zone("How to verify this yourself", "routes",
                         _kv([("The record", "/dash/home/validation"),
                              ("Pre-registration + gate hashes", "/dash/home/prereg"),
                              ("Coverage & settlement", "/dash/home/proof"),
                              ("Point-in-time replay", "/dash/home/replay"),
                              ("Test your own rule", "/dash/home/rule-lab")]),
                         sub="every claim above has a page"))
        return _page("Evidence pack", body)

    return _page("Validation record",
                 _h1("Validation record", "The falsification record — published, not curated.")
                 + lead + rec + dead + C.zone("Take it with you", "assembly", packlink,
                                              sub="the print / procurement pack"))


def _verdict_table(rows, holds) -> str:
    out = ['<table class="g-tt"><tr><th>Strategy</th><th>Category</th><th>Net return/vol</th>'
           "<th>CAGR</th><th>Max drawdown</th><th>Annual cost</th><th>Capacity</th><th>Book</th></tr>"]
    for r in rows:
        r = C._d(r)
        rv = r.get("ret_vol")
        cls = "up" if (rv is not None and float(rv) > 0.89) else ("dn" if rv is not None else "")
        name = str(r.get("name") or "")
        disp = name.split(":", 1)[1] if ":" in name else name
        asof_syms = holds.get(name)
        book = ""
        if asof_syms:
            book = " ".join(_sym(s) for s in (asof_syms[1] or [])[:6])
        out.append("<tr><td><b>" + C.esc(disp) + "</b></td>"
                   "<td>" + C.esc(r.get("category") or "—") + "</td>"
                   '<td class="g-num ' + cls + '">' + (C._num(rv, 2) if rv is not None else "—") + "</td>"
                   '<td class="g-num">' + (C._num(r.get("cagr_pct"), 1) + "%" if r.get("cagr_pct") is not None else "—") + "</td>"
                   '<td class="g-num">' + (C._num(r.get("maxdd_pct"), 1) + "%" if r.get("maxdd_pct") is not None else "—") + "</td>"
                   '<td class="g-num">' + (C._num(r.get("ann_cost_pct"), 1) + "%" if r.get("ann_cost_pct") is not None else "—") + "</td>"
                   '<td class="g-num">' + (("₹" + C._num(r.get("capacity_cr"), 0) + " cr") if r.get("capacity_cr") is not None else "—") + "</td>"
                   "<td>" + (book or "—") + "</td></tr>")
    out.append("</table>")
    out.append('<p class="g-tsub">Benchmark: Nifty 500 buy-and-hold, net return/vol <b '
               'class="g-num">0.89</b>. Anything below that line lost to simply owning the index.</p>')
    return "".join(out)


def _blocking_table(rows) -> str:
    out = ['<table class="g-tt"><tr><th>Approach</th><th>Why it is recorded dead (verbatim)</th></tr>']
    for key, row in rows:
        out.append("<tr><td><b>" + C.esc(key.replace("_", " ").title()) + "</b></td>"
                   '<td class="g-tledger">' + C.esc(row) + "</td></tr>")
    out.append("</table>")
    # These rows are quoted BYTE-VERBATIM from the failure ledger and are machine-compared against
    # it, so their wording is the ledger's, never ours to edit here. The ledger's own label was
    # corrected on 2026-07-27 (ledger + rule_lab mirror moved in one commit), so the quotes now
    # arrive correct and this caption only has to say what the number IS.
    out.append('<p class="g-tsub">Quoted verbatim from the failure ledger. Ratios in these rows '
               "are <b>return/vol</b> — mean return divided by volatility, with no risk-free rate "
               "subtracted. Where a row names a published statistic from the literature, that "
               "name is the literature's, not our label for our own number.</p>")
    return "".join(out)


# ── 3. pre-registered studies (classic: spec-sheets) ────────────────────────────────
@router.get("/dash/home/prereg", response_class=HTMLResponse, include_in_schema=False)
def prereg(request: Request) -> HTMLResponse:
    """The pre-registration ledger: for each study, the hypothesis and the PASS/FAIL gate written
    BEFORE the run, then the result — with the gate's SHA-256 where one was registered."""
    s = R.spec_sheets()
    lead = C.zone(
        "Why pre-registration", "method",
        "<p class='g-tp'>The easiest way to find a false edge is to look at the data first and "
        "decide what counts as success afterwards. So the gate is written down first — hypothesis, "
        "pass condition, and the hash of the file that says so — and then the study runs. Most of "
        "these gates FAILED. That is the evidence working.</p>"
        + C.learn("A pre-registered gate is a promise made to yourself in public. If the result "
                  "misses the bar you wrote before you looked, the answer is no."),
        sub="the gate comes before the run")
    body = _sheets_html(s)
    return _page("Pre-registered studies",
                 _h1("Pre-registered studies", "The bar was written before the run.")
                 + lead + C.zone("The studies", "prereg_registry · sha-256", body,
                                 sub=f"{len(s.get('sheets') or [])} registered"))


def _sheets_html(s: dict) -> str:
    sheets = (s or {}).get("sheets") or []
    if not sheets:
        return journey.teaching_empty(
            "Each card here is one pre-registered study: the hypothesis, the pass/fail gate agreed "
            "before the run, the result, and what (if anything) shipped. The ledger module is not "
            "importable in this environment.",
            "/dash/home/validation", "See the validation record instead")
    hashes = (s or {}).get("hashes") or {}
    cards = []
    for sh in sheets:
        sh = C._d(sh)
        v = sh.get("verdict") or ()
        badges = "".join('<span class="g-tbadge ' + C.esc(v[i + 1] or "") + '">' + C.esc(v[i]) + "</span>"
                         for i in (0, 2) if len(v) > i + 1 and v[i])
        h = hashes.get(sh.get("title")) or ""
        cards.append(
            '<div class="g-tcard"><div class="g-tcard-h">' + C.esc(sh.get("title") or "") + badges + "</div>"
            + _kv([("Pre-registered", sh.get("pre_reg") or "—"),
                   ("Hypothesis", _plain(sh.get("hypothesis"))),
                   ("Gate (written first)", _plain(sh.get("gate"))),
                   ("Result", _plain(sh.get("result"))),
                   ("What shipped", _plain(sh.get("ships"))),
                   ("Source", sh.get("source") or "—")]
                  + ([("Gate hash (SHA-256)", h)] if h else []))
            + "</div>")
    extra = ""
    for key, label in (("placebo", "Placebo control"), ("mttr", "Time-to-repair"), ("m05", "Standing caveats")):
        frag = (s or {}).get(key) or ""
        if frag:
            extra += '<div class="g-tcard"><div class="g-tcard-h">' + C.esc(label) + "</div>" + frag + "</div>"
    return _scroll("".join(cards) + extra, 520)


def _plain(html_frag) -> str:
    """The spec-sheet constants carry a little inline markup; the Graphite kv table escapes
    everything, so the tags are stripped to text rather than shown raw."""
    return re.sub(r"<[^>]+>", "", str(html_frag or "")) or "—"


# ── 4. rule lab (classic: rule-lab) — shareable verdict URLs (ratified §K.4) ────────
@router.get("/dash/home/rule-lab", response_class=HTMLResponse, include_in_schema=False)
def rule_lab(request: Request) -> HTMLResponse:
    """Compose a rule from a closed vocabulary and get the honest answer. EVERY piece of state
    lives in the query string (`?u=&rank=&n=&hold=&where=&veto=`), so a verdict is a URL you can
    paste to someone — the ratified Chartink-style requirement. The param names are the SAME as
    the classic page, so links move between the two surfaces unchanged."""
    vocab = R.rule_vocabulary()
    params = {k: request.query_params.get(k, "") for k in ("u", "rank", "n", "hold", "where", "veto")}
    spec, err, preview, share = None, "", {}, ""
    if any(params.values()):
        try:
            spec = R.rule_spec_from_query(params)
            preview = R.rule_preview(spec)
            q = R.rule_query_from_spec(spec)
            share = "/dash/home/rule-lab?" + "&".join(f"{k}={C.esc(v)}" for k, v in q.items())
        except Exception as exc:  # noqa: BLE001 — RuleError carries the closed vocabulary back
            err = str(exc)

    lead = C.zone(
        "Test your own rule", "rule_lab engine",
        "<p class='g-tp'>Pick a universe, a ranking signal, how many names and how often you "
        "rebalance. Before anything runs, we check your rule against the ledger of approaches "
        "already recorded dead — most rules have an answer waiting.</p>"
        + C.learn("The vocabulary is deliberately closed. You cannot express a rule we cannot "
                  "honestly evaluate, which is why there is no free-text box here."),
        sub="the same gauntlet we run on ourselves")

    form = C.zone("Compose", "closed vocabulary", _rule_form(vocab, params), sub="every choice is in the URL")

    if err:
        verdict = C.zone("Verdict", "rule_lab", C.empty(err[:400]) + journey.teaching_empty(
            "A rule has to be written in the closed vocabulary above — that is what lets us answer "
            "it honestly instead of guessing.", "/dash/home/rule-lab", "Start from the defaults"),
            sub="not a valid rule")
    elif spec is not None:
        cites = preview.get("citations") or []
        wall = ("".join("<li>" + C.esc(c) + "</li>" for c in cites)) if cites else ""
        inner = ""
        if wall:
            inner += ('<p class="g-tp"><b>The ledger already answers part of this rule.</b></p>'
                      '<ul class="g-tlist">' + wall + "</ul>")
        if preview.get("survivor"):
            inner += '<p class="g-tsub">' + C.esc(preview["survivor"]) + "</p>"
        if not inner:
            inner = ('<p class="g-tp">Nothing in the ledger blocks this rule outright. That is not '
                     "a green light — it means it has not been tested, which is the only honest "
                     "thing we can say before a walk-forward run.</p>")
        inner += ('<p class="g-tp g-tshare">Shareable verdict URL: <code class="g-num">'
                  + C.esc(share) + '</code> <a class="g-btn" href="' + C.safe_url(share)
                  + '">Open this exact rule →</a></p>')
        verdict = C.zone("Verdict", "ledger · pre-run", inner, sub="what we already know")
    else:
        demo = R.rule_demo_verdict()
        verdict = C.zone("Verdict", "demo · synthetic", _demo_verdict_html(demo),
                         sub="an example answer", sample=True)

    return _page("Rule lab", _h1("Rule lab", "Write a rule; get the honest answer.")
                 + lead + form + verdict, current_dest="Strategies")


def _rule_form(vocab: dict, params: dict) -> str:
    if not vocab:
        return journey.teaching_empty(
            "The composer offers a closed list of universes, ranking signals, filters and vetoes — "
            "the only rules we can evaluate honestly. The rule engine is not importable here.",
            "/dash/home/validation", "Read the validation record instead")
    def sel(name, options, cur, labeller=None):
        opts = "".join('<option value="' + C.esc(k) + '"' + (" selected" if str(cur) == str(k) else "")
                       + ">" + C.esc(labeller(k) if labeller else k) + "</option>" for k in options)
        return ('<label class="g-tfield"><span>' + C.esc(name.replace("_", " ")) + "</span>"
                '<select name="' + C.esc(name) + '">' + opts + "</select></label>")
    lab = lambda d: (lambda k: str((d.get(k) or {}).get("label", k)) if isinstance(d.get(k), dict) else str(k))
    lo, hi = vocab["take"]
    checks = ""
    for field, table in (("where", vocab["filters"]), ("veto", vocab["vetoes"])):
        cur = set((params.get(field) or "").split(","))
        boxes = "".join(
            '<label class="g-tcheck"><input type="checkbox" name="' + field + '" value="' + C.esc(k) + '"'
            + (" checked" if k in cur else "") + "> " + C.esc(k.replace("_", " ")) + "</label>"
            for k in table)
        checks += ('<div class="g-tfield"><span>' + ("filters" if field == "where" else "vetoes")
                   + "</span><div class='g-tchecks'>" + boxes + "</div></div>")
    return ('<form class="g-tform" method="get" action="/dash/home/rule-lab">'
            + sel("u", vocab["universes"], params.get("u") or "liquid500", lab(vocab["universes"]))
            + sel("rank", vocab["signals"], params.get("rank") or "mom12", lab(vocab["signals"]))
            + '<label class="g-tfield"><span>take</span><input type="number" name="n" min="'
            + str(lo) + '" max="' + str(hi) + '" value="' + C.esc(params.get("n") or "25") + '"></label>'
            + sel("hold", vocab["holds"], params.get("hold") or "quarterly")
            + checks
            + '<button class="g-btn" type="submit">Check this rule</button></form>'
            + '<p class="g-tsub">Submitting only changes the URL — the whole rule is the query '
              "string, so the result is shareable and reproducible.</p>")


def _demo_verdict_html(v: dict) -> str:
    v = C._d(v)
    if not v:
        return journey.teaching_empty(
            "A verdict shows the net and gross return/vol, both walk-forward halves, the placebo "
            "control and the benchmark — plus the citations that decided it.",
            "/dash/home/rule-lab?u=liquid500&rank=mom12&n=25&hold=quarterly", "Compose a rule")
    nums = C._d(v.get("numbers"))
    order = (("net_retvol", "net return/vol"), ("gross_retvol", "gross return/vol"),
             ("half1", "half 1 (2012-18)"), ("half2", "half 2 (2019-26)"),
             ("placebo_p95", "placebo p95"), ("observed", "observed"),
             ("bench_net", "benchmark (Nifty-500 net)"), ("maxdd", "max drawdown"),
             ("ann_cost_pct", "annual cost %"))
    rows = [(lab, C._num(nums[k], 2)) for k, lab in order if nums.get(k) is not None]
    return ('<div class="g-tverdict"><span class="g-tbadge v-fail">' + C.esc(v.get("verdict") or "—")
            + "</span>" + ('<span class="g-tbadge">' + C.esc(v.get("qualifier") or "") + "</span>"
                           if v.get("qualifier") else "") + "</div>"
            + _kv(rows)
            + '<p class="g-tsub">Synthetic example — these are not the numbers of a real run. '
              "Compose a rule above to check yours against the ledger.</p>")


# ── 5. replay any date (classic: replay-any-date) — FLAGSHIP ────────────────────────
@router.get("/dash/home/replay", response_class=HTMLResponse, include_in_schema=False)
def replay(request: Request) -> HTMLResponse:
    """FLAGSHIP — the single most differentiating trust asset: ask the real API what it knew on a
    past date and watch it refuse to know anything else. `?sym=` (never `?symbol=`) + `?as_of=`."""
    sym = (request.query_params.get("sym") or "ICICIPRULI").strip().upper()[:20]
    as_of = (request.query_params.get("as_of") or "2019-01-25").strip()[:10]
    data = R.replay(sym, as_of)

    lead = C.zone(
        "Zero look-ahead, on demand", "/v1 · live",
        "<p class='g-tp'>Pick any past date. We ask the live API the same question a subscriber "
        "would, dated to that morning — and it answers with only what was knowable then. "
        "Delisted names stay in the universe; a credibility score that had not been earned yet is "
        "absent, not back-filled.</p>"
        + C.learn("Two-tier knowable clock: EVENT means the period's real public clock (the call "
                  "was held, or the transcript was published — whichever is later). MODELED means "
                  "no clock was captured, so the point only counts as knowable once its label "
                  "month has completed. Result filings are never used as a clock for "
                  "call-derived content, because filings usually come first — that is the leak "
                  "direction."),
        sub="the proof you can drive yourself")

    form = ('<form class="g-tform" method="get" action="/dash/home/replay">'
            '<label class="g-tfield"><span>symbol</span><input name="sym" value="' + C.esc(sym)
            + '" maxlength="20"></label>'
            '<label class="g-tfield"><span>as of</span><input name="as_of" value="' + C.esc(as_of)
            + '" maxlength="10" placeholder="YYYY-MM-DD"></label>'
            '<button class="g-btn" type="submit">Replay that morning</button></form>'
            '<p class="g-tsub">Try ' + _replay_link("ALKYLAMINE", "2020-04-01")
            + " · " + _replay_link("TANLA", "2020-06-15")
            + " · " + _replay_link("ICICIPRULI", "2019-01-25") + "</p>")

    panels = (_replay_panel("Credibility on that date", data.get("credibility"),
                            "What the concall-credibility engine could honestly say about "
                            + sym + " that morning.")
              + _replay_panel("The attention queue as it stood", data.get("attention"),
                              "The newest snapshot computed at or before the date — not today's.")
              + _replay_panel("The universe on that date", data.get("universe"),
                              "Who was listed and tradeable, including names since delisted."))

    card = C.zone("The same thing, as a card", "component",
                  journey.replay_card(R.replay_facts(sym, as_of))
                  + C.learn("This card is built to sit on the Today page — the parent wires it in "
                            "one line; this lane does not edit that file."),
                  sub="ready for the Today page")

    return _page("Replay any date",
                 _h1("Replay any date", "What we could honestly have known that morning.")
                 + lead + C.zone("Pick a date", "controls", form, sub="any past trading day")
                 + C.zone("What the API answered", "/v1 · verbatim envelopes", panels,
                          sub="raw, unedited")
                 + card)


def _replay_link(sym: str, as_of: str) -> str:
    return ('<a href="/dash/home/replay?sym=' + C.esc(sym) + "&as_of=" + C.esc(as_of) + '">'
            + C.esc(sym) + " on " + C.esc(as_of) + "</a>")


def _replay_panel(title: str, env, why: str) -> str:
    env = C._d(env)
    status = env.get("status")
    if not env or not status:
        return ('<div class="g-tcard"><div class="g-tcard-h">' + C.esc(title) + "</div>"
                + journey.teaching_empty(
                    why + " It needs the live API key and the point-in-time tables, which are not "
                    "configured in this environment.",
                    "/dash/home/proof", "See what data we actually hold") + "</div>")
    payload = env.get("json") if env.get("json") is not None else env.get("text")
    import json as _json
    try:
        raw = _json.dumps(payload, indent=2, ensure_ascii=False)[:6000]
    except Exception:  # noqa: BLE001
        raw = str(payload)[:6000]
    return ('<div class="g-tcard"><div class="g-tcard-h">' + C.esc(title)
            + '<span class="g-tbadge">HTTP ' + C.esc(status) + "</span></div>"
            '<p class="g-tsub">' + C.esc(why) + "</p>"
            + _scroll("<pre class='g-tpre'>" + C.esc(raw) + "</pre>", 260) + "</div>")


# ── 6. glossary (classic: glossary) — the SAME docs/metrics-glossary.md ─────────────
@router.get("/dash/home/glossary", response_class=HTMLResponse, include_in_schema=False)
def glossary(request: Request) -> HTMLResponse:
    """Every metric on the site, in plain English, read from the ONE definition source. `?q=`
    pre-fills the filter so a glossary link is shareable."""
    q = (request.query_params.get("q") or "").strip()[:60]
    fams = R.glossary_families()
    n = sum(len(v) for _k, v in fams)
    if not fams:
        body = C.zone("Glossary", "docs/metrics-glossary.md",
                      journey.teaching_empty(
                          "Every metric used anywhere on the site is defined here, grouped by "
                          "family, with the database column it is computed from. The definition "
                          "file could not be read.",
                          "/dash/home/guide", "Read the orientation guide"),
                      sub="the metric dictionary")
        return _page("Glossary", _h1("Glossary", "Every number, in plain English.") + body)

    jump = "".join('<a class="g-tjump" href="#f' + str(i) + '">' + C.esc(f) + "</a>"
                   for i, (f, _v) in enumerate(fams))
    secs = []
    for i, (fam, entries) in enumerate(fams):
        rows = "".join(
            '<div class="g-tterm" data-t="' + C.esc((C._d(e).get("name") or "").lower()) + '">'
            "<dt>" + C.esc(C._d(e).get("name") or "") + "</dt><dd>" + C.esc(C._d(e).get("body") or "")
            + ("".join(' <code class="g-num">' + C.esc(s) + "</code>" for s in (C._d(e).get("sources") or [])[:4]))
            + "</dd></div>" for e in entries)
        secs.append('<section class="g-tfam" id="f' + str(i) + '"><h3>' + C.esc(fam)
                    + ' <span class="g-tsub">' + str(len(entries)) + "</span></h3><dl>" + rows + "</dl></section>")

    body = (C.zone("Find a term", "docs/metrics-glossary.md · single source",
                   '<input class="g-tsearch" id="g-gsearch" placeholder="Type a metric, e.g. delivery"'
                   ' value="' + C.esc(q) + '" aria-label="Filter terms">'
                   + '<div class="g-tjumps">' + jump + "</div>"
                   + C.learn("Every definition here is the same text the ? popovers use elsewhere "
                             "on the site — one source, so they can never disagree."),
                   sub=f"{n} terms · {len(fams)} families")
            + C.zone("The dictionary", "parsed · document order", _scroll("".join(secs), 620),
                     sub="grouped by family"))
    return _page("Glossary", _h1("Glossary", "Every number, in plain English.") + body + _GLOSS_JS)


_GLOSS_JS = """<script>(function(){
function go(){var i=document.getElementById("g-gsearch");if(!i)return;
var terms=[].slice.call(document.querySelectorAll(".g-tterm"));
function run(){var v=(i.value||"").toLowerCase().trim();
terms.forEach(function(t){t.style.display=(!v||t.getAttribute("data-t").indexOf(v)>=0)?"":"none";});}
i.addEventListener("input",run);if(i.value)run();}
if(document.readyState!=="loading")go();else document.addEventListener("DOMContentLoaded",go);})();</script>"""


# ── 7. strategy reference (classic: strategy-ref) — the SAME docs/strategies/ ───────
@router.get("/dash/home/strategy-ref", response_class=HTMLResponse, include_in_schema=False)
def strategy_ref(request: Request) -> HTMLResponse:
    """One canonical page per strategy — name, definition, current status, terminology. `?p=slug`.
    Served from `docs/strategies/` through the public sanitizer, so internal governance tokens
    (session/decision ids, commit hashes, ledger date tags) never reach a reader."""
    slug = (request.query_params.get("p") or "").strip().lower()[:50]
    pages = R.strategy_pages()
    if not pages:
        return _page("Strategy reference",
                     _h1("Strategy reference", "One canonical page per strategy.")
                     + C.zone("Strategies", "docs/strategies",
                              journey.teaching_empty(
                                  "Each strategy has one authoritative page fixing its name, "
                                  "definition, current status and honesty verdict. The reference "
                                  "folder could not be read.",
                                  "/dash/home/validation", "See the validation record"),
                              sub="the canonical layer"))
    rail = "".join('<a class="g-trail-i' + (" on" if p["slug"] == slug else "")
                   + '" href="/dash/home/strategy-ref?p=' + C.esc(p["slug"]) + '">'
                   + C.esc(p["title"]) + "</a>" for p in pages)
    doc = R.strategy_doc(slug) if slug else {}
    if slug and not doc:
        main = journey.teaching_empty(
            "That reference page does not exist. The list on the left is the complete set — one "
            "page per strategy we actually run.", "/dash/home/strategy-ref", "See all strategies")
    elif doc:
        main = '<article class="g-tdoc">' + _md(doc["text"]) + "</article>"
    else:
        main = ('<article class="g-tdoc">'
                "<p class='g-tp'>Sixteen strategies, one page each. Every page states what the "
                "strategy is, what it is <b>not</b>, and its current honesty status — most are "
                "<b>descriptive only</b>, meaning they describe the tape rather than rank or "
                "trade it. Pick one on the left.</p>"
                + C.learn("These pages never restate a formula constant or a backtest table. "
                          "The numbers live in the validation record; these fix the meaning.")
                + "</article>")
    body = C.zone("Strategy reference", "docs/strategies · sanitized",
                  '<div class="g-tsplit"><nav class="g-trail" aria-label="Strategies">' + rail
                  + "</nav>" + _scroll(main, 560) + "</div>",
                  sub=f"{len(pages)} canonical pages")
    return _page("Strategy reference",
                 _h1("Strategy reference", "What each strategy is — and what it is not.") + body,
                 current_dest="Strategies")


# ── 8. the guide (classic: reading-guide) + the M6 journey layer ────────────────────
@router.get("/dash/home/guide", response_class=HTMLResponse, include_in_schema=False)
def guide(request: Request) -> HTMLResponse:
    """The newcomer exit and the standing destination of the persistent help control. Delivers the
    five-step arc as STRUCTURE (a static ladder of links), never as a tour."""
    body = (C.zone("Five minutes, five steps", "orientation",
                   journey.steps_block(current=(request.query_params.get("step") or "").strip())
                   + C.learn("You can ignore all of this. Nothing on the site is hidden behind a "
                             "walkthrough — this page exists so a first visit has a shape."),
                   sub="the shape of a session")
            + C.zone("How to read anything here", "conventions",
                     "<ul class='g-tlist'>"
                     "<li><b>Every number names its source.</b> The small grey chip on each card is "
                     "the table it came from and how often that table is refreshed.</li>"
                     "<li><b>Sample means sample.</b> When a live read is empty we show an "
                     "illustrative version and mark it — it is never passed off as real.</li>"
                     "<li><b>Empty means empty.</b> A blank section tells you what would appear "
                     "there and why it has not, rather than showing a zero.</li>"
                     "<li><b>Descriptive, not directive.</b> Nothing here ranks a stock for you or "
                     "tells you to act. Where a method failed its test, the page says so.</li>"
                     "<li><b>Symbols are links.</b> Any ticker takes you to that name's evidence.</li>"
                     "</ul>", sub="five conventions, whole site")
            + C.zone("Where the evidence lives", "directory", _nav_strip("/dash/home/guide"),
                     sub="the whole proof estate"))
    return _page("How to read", _h1("How to read this site", "Five conventions and five steps.") + body)


# ── 9. Pat — the deterministic answer endpoint for the floating dock ────────────────
@router.get("/dash/home/pat/ask", response_class=HTMLResponse, include_in_schema=False)
def pat_ask(request: Request) -> HTMLResponse:
    """The dock's server-side brain: a closed-vocabulary, deterministic answer for one question.

    Returns an HTML FRAGMENT (not a page) that the dock injects. Deliberately ₹0: it resolves
    through Pat's two auto-folding knowledge sources — the glossary (`docs/metrics-glossary.md`)
    and the lens registry — plus a symbol deep-link, and NEVER calls a model. There is no third
    Pat: this is the existing dock gaining the classic page's resolution, not a new assistant."""
    q = (request.query_params.get("q") or "")[:120]
    cm, conn = _conn()
    try:
        from src.web.home import pat_dock
        frag = pat_dock.answer_html(conn, q)
    except Exception:  # noqa: BLE001
        frag = C.empty("I couldn't look that up just now.")
    finally:
        _close(cm)
    return HTMLResponse(frag)


def _h1(title: str, sub: str) -> str:
    return ('<div class="g-th"><h1>' + C.esc(title) + "</h1><p>" + C.esc(sub) + "</p></div>"
            + C.fence(_FENCE_TRUST))


_CSS = """<style>/* g-trust */
:root[data-ui-g] .g-trust{display:flex;flex-direction:column;gap:16px}
:root[data-ui-g] .g-th h1{margin:0 0 4px;font-size:26px;letter-spacing:-.3px}
:root[data-ui-g] .g-th p{margin:0 0 10px;color:var(--ink-3);font-size:13px}
:root[data-ui-g] .g-tscroll{overflow:auto;scrollbar-width:thin;border:1px solid var(--line);
  border-radius:10px;padding:10px 12px;background:var(--bg-0)}
:root[data-ui-g] .g-tscroll:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
:root[data-ui-g] .g-tp{font-size:13px;line-height:1.65;color:var(--ink-2);margin:0 0 10px;max-width:74ch}
:root[data-ui-g] .g-tsub{font-size:11.5px;color:var(--ink-3);line-height:1.55}
:root[data-ui-g] .g-tlist{margin:0;padding-left:18px;font-size:12.5px;line-height:1.7;color:var(--ink-2)}
:root[data-ui-g] .g-tlist b{color:var(--ink)}
:root[data-ui-g] .g-tt{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] .g-tt th{text-align:left;font:600 10px var(--font);letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink-3);border-bottom:1px solid var(--line-2);padding:6px 9px;
  position:sticky;top:-10px;background:var(--bg-0)}
:root[data-ui-g] .g-tt td{padding:7px 9px;border-bottom:1px solid var(--line);color:var(--ink-2);vertical-align:top}
:root[data-ui-g] .g-tt td.up{color:var(--up)}
:root[data-ui-g] .g-tt td.dn{color:var(--dn)}
:root[data-ui-g] .g-tkv{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] .g-tkv th{text-align:left;width:34%;color:var(--ink-3);font-weight:600;
  padding:5px 9px 5px 0;border-bottom:1px solid var(--line);vertical-align:top}
:root[data-ui-g] .g-tkv td{padding:5px 0;border-bottom:1px solid var(--line);color:var(--ink-2)}
:root[data-ui-g] .g-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:12px}
:root[data-ui-g] .g-tnav{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}
:root[data-ui-g] .g-tnav-i{display:block;border:1px solid var(--line-2);border-radius:12px;
  background:var(--bg-2);padding:10px 12px;text-decoration:none}
:root[data-ui-g] .g-tnav-i.on{border-color:var(--accent)}
:root[data-ui-g] .g-tnav-i:hover{border-color:var(--accent)}
:root[data-ui-g] .g-tnav-i b{display:block;font-size:12.5px;color:var(--ink)}
:root[data-ui-g] .g-tnav-i span{font-size:11px;color:var(--ink-3)}
:root[data-ui-g] .g-tcard{border:1px solid var(--line-2);border-radius:12px;background:var(--bg-2);
  padding:11px 13px;margin:0 0 10px}
:root[data-ui-g] .g-tcard-h{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font:700 13px var(--font);
  color:var(--ink);margin-bottom:7px}
:root[data-ui-g] .g-tbadge{font:600 9px/1 var(--mono);letter-spacing:.07em;text-transform:uppercase;
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:3px 7px;color:var(--ink-3)}
:root[data-ui-g] .g-tbadge.v-fail{border-color:var(--dn);color:var(--dn)}
:root[data-ui-g] .g-tbadge.v-desc{border-color:var(--accent);color:var(--accent)}
:root[data-ui-g] .g-tpre{font:400 11px/1.5 var(--mono);color:var(--ink-2);white-space:pre-wrap;margin:0}
:root[data-ui-g] .g-tform{display:flex;flex-wrap:wrap;gap:11px;align-items:flex-end}
:root[data-ui-g] .g-tfield{display:flex;flex-direction:column;gap:4px;font:600 10px var(--font);
  letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-tfield select,:root[data-ui-g] .g-tfield input{background:var(--bg-0);color:var(--ink);
  border:1px solid var(--line-2);border-radius:9px;padding:8px 10px;font:400 13px var(--font);min-width:150px;
  text-transform:none;letter-spacing:0}
:root[data-ui-g] .g-tchecks{display:flex;flex-wrap:wrap;gap:9px}
:root[data-ui-g] .g-tcheck{font:400 12px var(--font);color:var(--ink-2);text-transform:none;letter-spacing:0}
:root[data-ui-g] .g-tverdict{display:flex;gap:8px;margin-bottom:9px}
:root[data-ui-g] .g-tshare code{word-break:break-all;font-size:11px}
:root[data-ui-g] .g-tsearch{width:100%;max-width:420px;background:var(--bg-0);color:var(--ink);
  border:1px solid var(--line-2);border-radius:10px;padding:9px 12px;font:400 13px var(--font)}
:root[data-ui-g] .g-tjumps{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 0}
:root[data-ui-g] .g-tjump{font:600 10.5px var(--font);color:var(--ink-2);border:1px solid var(--line-2);
  border-radius:var(--r-pill);padding:4px 9px;text-decoration:none}
:root[data-ui-g] .g-tjump:hover{border-color:var(--accent);color:var(--accent)}
:root[data-ui-g] .g-tfam h3{margin:14px 0 7px;font:700 12px var(--font);letter-spacing:.06em;
  text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--line);padding-bottom:5px}
:root[data-ui-g] .g-tfam dl{margin:0}
:root[data-ui-g] .g-tterm{padding:6px 0;border-bottom:1px solid var(--line)}
:root[data-ui-g] .g-tterm dt{font:700 12.5px var(--font);color:var(--ink)}
:root[data-ui-g] .g-tterm dd{margin:3px 0 0;font-size:12px;line-height:1.6;color:var(--ink-3)}
:root[data-ui-g] .g-tsplit{display:grid;grid-template-columns:minmax(0,1fr);gap:12px}
@media(min-width:900px){:root[data-ui-g] .g-tsplit{grid-template-columns:190px minmax(0,1fr)}}
:root[data-ui-g] .g-trail{display:flex;flex-direction:column;gap:2px;max-height:560px;overflow:auto;scrollbar-width:thin}
:root[data-ui-g] .g-trail-i{font-size:12.5px;color:var(--ink-2);text-decoration:none;padding:6px 9px;border-radius:8px}
:root[data-ui-g] .g-trail-i.on{background:var(--acc-dim);color:var(--accent);font-weight:600}
:root[data-ui-g] .g-trail-i:hover{color:var(--accent)}
:root[data-ui-g] .g-tdoc{font-size:13px;line-height:1.7;color:var(--ink-2)}
:root[data-ui-g] .g-tdoc h2{font-size:19px;margin:18px 0 8px;color:var(--ink)}
:root[data-ui-g] .g-tdoc h3{font-size:15px;margin:16px 0 7px;color:var(--ink)}
:root[data-ui-g] .g-tdoc h4,:root[data-ui-g] .g-tdoc h5{font-size:13px;margin:13px 0 6px;color:var(--ink)}
:root[data-ui-g] .g-tdoc p{margin:0 0 9px;max-width:78ch}
:root[data-ui-g] .g-tdoc ul{margin:0 0 10px;padding-left:19px}
:root[data-ui-g] .g-tdoc li{margin:3px 0}
:root[data-ui-g] .g-tdoc a{color:var(--accent)}
:root[data-ui-g] .g-tq{margin:0 0 10px;padding:8px 12px;border-left:3px solid var(--accent);
  background:var(--bg-2);border-radius:0 8px 8px 0;font-size:12.5px;color:var(--ink-2)}
:root[data-ui-g] .g-tmd{width:100%;border-collapse:collapse;font-size:12px}
:root[data-ui-g] .g-tmd th{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line-2);
  color:var(--ink-3);font-weight:600}
:root[data-ui-g] .g-tmd td{padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
</style>"""


def _selftest() -> int:
    """python -c "from src.web.home import trust_pages as T; T._selftest()" """
    ok = 0
    assert "g-trust" in _CSS and "data-ui-v3" not in _CSS and "pv3-" not in _CSS
    ok += 1
    md = _md("# T\n\nHello **bold** and `x`.\n\n- a\n- b\n\n| h | i |\n|---|---|\n| 1 | 2 |\n")
    assert "<h2>T</h2>" in md and "<b>bold</b>" in md and "<li>a</li>" in md and "<td>1</td>" in md
    ok += 1
    assert "&lt;script&gt;" in _md("<script>alert(1)</script>") and "<script>" not in _md("<script>x</script>")
    ok += 1
    assert '/dash/home/stock?sym=TCS' in _sym("TCS")
    ok += 1
    routes = sorted(r.path for r in router.routes)
    assert routes == sorted(["/dash/home/proof", "/dash/home/validation", "/dash/home/prereg",
                             "/dash/home/rule-lab", "/dash/home/replay", "/dash/home/glossary",
                             "/dash/home/strategy-ref", "/dash/home/guide", "/dash/home/pat/ask"]), routes
    ok += 1
    assert all(href in _nav_strip("") for href, _l, _s in _PAGES)
    ok += 1
    print(f"trust_pages selftest OK ({ok} checks) — {len(routes)} routes")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_selftest())
