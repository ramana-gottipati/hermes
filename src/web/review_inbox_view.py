"""review_inbox_view.py — /dash/inbox: the Review Inbox, the human-verification layer.

The L5 surface (plan §2/§4-D). S157 wired the judgment loop — proposals in, verdicts
back out to company_tags, every decision kept as the judgment corpus — but its only
human interface was an SSH CLI (`review_inbox --decide 12 --verdict approved`). This
is the interface: the queue Ramana actually drains, and the public statement of WHY a
machine's output does not count until a person has checked it.

TWO AUDIENCES, ONE ROUTE (the tracker_gate precedent, D-P0-6):
  * anonymous  -> the METHODOLOGY page: what the verification layer is, the honest
                  aggregate counts, and the agreement rates. NO item titles, NO
                  payloads, NO decide buttons.
  * the owner  -> the working queue on top of that: every pending item with its
                  evidence, one-click approve/reject, and the corpus CSV.

Why the gate is not optional: the inbox carries kind='brief' — auto-analyst drafts
that are AI-written and NOT yet reviewed. The L6 contract is that ONLY an approved
brief publishes (with its AI label); rendering pending briefs on a public page would
publish exactly the unreviewed AI text that contract forbids. Ownership is decided by
tracker_gate._is_owner (the ONE owner concept on this site — hermes_key / pt_owner),
never a second scheme.

THE HONESTY THAT DRIVES THE STATS TABLE (found while building this page): the imported
pre-inbox history CANNOT distinguish "Ramana approved a machine proposal" from "Ramana
typed the tag in himself" — theme_tags writes BOTH as source='ramana', so the
distinction is unrecoverable from the legacy schema. A single blended approve-rate
would therefore over-state how often the proposers are right. So this page reports
LIVED and IMPORTED rates separately and says why: lived decisions (2026-07-15 onward,
payload imported!=true) are the clean measure of a generator; imported history is
context. Never merge the two into one flattering number.

Writes are POST (playbook item 11) and go through inbox_adapters.decide_by_ref-family
helpers, so this page and the legacy /dash/tags-review surface share ONE decision path.

Isolated module (the glossary_view pattern): own APIRouter, durably mounted via
v2_surfaces._ROUTER_SPECS; reads/writes only via review_inbox + inbox_adapters.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from src.web import infographics as ifx
from src.web.momentum_view import _esc, _shell

router = APIRouter()
_ROUTE = "/dash/inbox"

# Per-kind display: label + the one-line "what am I judging" for a beginner.
_KIND_COPY: dict[str, tuple[str, str]] = {
    "tags": ("Theme tags", "A rule or model proposed a theme label for a company. "
                           "Approving files it as a fact; rejecting tombstones it so "
                           "the weekly pass never proposes it again."),
    "brief": ("Event briefs", "An AI-drafted, source-linked summary of a results event. "
                              "Nothing publishes until it is approved here."),
    "alert-ack": ("Alert acknowledgements", "A change the alert rail raised for a decision."),
    "rebalance": ("Rebalance diffs", "A model book's proposed change of holdings."),
    "anomaly": ("Data anomalies", "A data-quality or fence flag raised for a human call."),
}

_CSS = """
<style>
.ib-item{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0;
         background:var(--bg-2)}
.ib-h{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.ib-t{font-weight:600}
.ib-ref{font-family:ui-monospace,monospace;font-size:12px;color:var(--ink-3)}
.ib-why{font-size:13px;color:var(--ink-2);margin:6px 0 0}
.ib-acts{display:flex;gap:6px;margin-top:8px}
.ib-btn{padding:4px 12px;border:1px solid var(--line);border-radius:6px;
        background:var(--bg-1);color:var(--ink);cursor:pointer;font-size:13px}
.ib-btn.ok:hover{border-color:var(--up);color:var(--up)}
.ib-btn.no:hover{border-color:var(--down);color:var(--down)}
.ib-kpi{display:inline-block;min-width:96px;margin:0 18px 10px 0}
.ib-kpi b{display:block;font-size:22px;line-height:1.1}
.ib-kpi span{font-size:12px;color:var(--ink-3)}
.ib-tbl{border-collapse:collapse;margin:6px 0 2px}
.ib-tbl th,.ib-tbl td{border-bottom:1px solid var(--line);padding:4px 14px 4px 0;
                      text-align:left;font-size:13px}
</style>
"""


def _is_owner(request) -> bool:
    """The ONE owner concept (tracker_gate). Fail CLOSED: if the gate cannot be
    consulted we serve the public page — never the queue."""
    try:
        from src.web import tracker_gate
        return bool(tracker_gate._is_owner(request))
    except Exception:  # noqa: BLE001
        return False


def _conn():
    from src.core.db import get_conn
    return get_conn()


def _pct(a: int, d: int) -> str:
    return "n/a" if not d else "%.0f%%" % (100.0 * a / d)


def _split_stats(rows: list) -> dict:
    """{kind: {lived|imported: {approved, rejected}}} — the two segments kept apart
    (see the module docstring: blending them would over-state the proposers)."""
    out: dict = {}
    for r in rows:
        seg = "imported" if (r.get("payload") or {}).get("imported") else "lived"
        d = out.setdefault(r["kind"], {"lived": {"approved": 0, "rejected": 0},
                                       "imported": {"approved": 0, "rejected": 0}})
        if r["status"] in d[seg]:
            d[seg][r["status"]] += 1
    return out


def _stats_table(split: dict, pend: dict) -> str:
    rows = ""
    for kind in sorted(set(split) | set(pend)):
        s = split.get(kind, {"lived": {"approved": 0, "rejected": 0},
                             "imported": {"approved": 0, "rejected": 0}})
        lv, im = s["lived"], s["imported"]
        lvd, imd = lv["approved"] + lv["rejected"], im["approved"] + im["rejected"]
        label = _KIND_COPY.get(kind, (kind, ""))[0]
        rows += (
            "<tr><td>%s</td><td>%d</td><td>%d</td><td><b>%s</b></td><td>%d</td>"
            "<td>%s</td></tr>" % (
                _esc(label), pend.get(kind, 0), lvd, _pct(lv["approved"], lvd),
                imd, _pct(im["approved"], imd)))
    if not rows:
        return "<p class='ib-why'>No items yet.</p>"
    return (
        "<table class='ib-tbl'><thead><tr><th>Queue</th><th>Pending</th>"
        "<th>Decided here</th><th>Agreement rate</th><th>Imported</th>"
        "<th>Imported rate</th></tr></thead><tbody>" + rows + "</tbody></table>")


_IMPORTED_CAVEAT = (
    "<p class='ib-why'><b>Why two rates, not one.</b> "
    "&ldquo;Decided here&rdquo; counts verdicts given since the inbox went live &mdash; that is "
    "the clean measure of how often a proposer is right. &ldquo;Imported&rdquo; is the "
    "history that existed before it: the old storage recorded an approved proposal and a "
    "hand-added tag as the same row, so those two acts cannot be told apart and the "
    "imported rate flatters the proposers. They are shown side by side rather than "
    "blended into one number. <a href='/dash/glossary?q=agreement rate'>Agreement rate "
    "&rarr;</a></p>")


def _explainer() -> str:
    return (
        "<h3 style='margin:16px 0 6px'>What this is</h3>"
        "<p class='ib-why'>Everything the machine proposes &mdash; a theme label for a "
        "company, an AI-drafted note on a results event &mdash; lands in one queue and waits "
        "for a person to approve or reject it. Nothing counts until it has been checked. "
        "A rejected proposal is not just dropped: it leaves a marker so the same suggestion "
        "is never made twice.</p>"
        "<p class='ib-why'>Every decision is kept. That record is what makes the claim "
        "measurable rather than rhetorical: the agreement rates above are how often each "
        "generator turned out to be right, counted from real verdicts &mdash; including the "
        "times it was wrong.</p>")


def _item_html(it: dict) -> str:
    p = it.get("payload") or {}
    bits = []
    if p.get("source"):
        bits.append("proposed by: " + _esc(p["source"]))
    if p.get("confidence") is not None:
        bits.append("confidence " + _esc(p["confidence"]))
    if p.get("note"):
        bits.append(_esc(p["note"]))
    why = " &middot; ".join(bits)
    ev = ""
    if it.get("evidence_url"):
        ev = ("<a class='ib-ref' href='%s' style='margin-left:auto'>evidence &rarr;</a>"
              % _esc(it["evidence_url"]))
    return (
        "<div class='ib-item'>"
        "<div class='ib-h'><span class='ib-t'>%s</span>"
        "<span class='ib-ref'>%s</span>%s</div>"
        "%s"
        "<form class='ib-acts' method='post' action='%s/decide'>"
        "<input type='hidden' name='item_id' value='%d'>"
        "<button class='ib-btn ok' type='submit' name='verdict' value='approved'>"
        "&#10003; Approve</button>"
        "<button class='ib-btn no' type='submit' name='verdict' value='rejected'>"
        "&#10005; Reject</button>"
        "</form></div>" % (
            _esc(it["title"]), _esc(it["ref"]), ev,
            ("<p class='ib-why'>" + why + "</p>") if why else "",
            _ROUTE, int(it["id"])))


def _queue_html(pending: list) -> str:
    if not pending:
        return ("<div class='ib-item'><b>Queue clear.</b>"
                "<p class='ib-why'>Nothing is waiting on you.</p></div>")
    out = ""
    for kind in sorted({i["kind"] for i in pending}):
        label, blurb = _KIND_COPY.get(kind, (kind, ""))
        items = [i for i in pending if i["kind"] == kind]
        out += ("<h3 style='margin:18px 0 2px'>%s <span style='font-size:13px;"
                "font-weight:400;color:var(--ink-3)'>&middot; %d waiting</span></h3>"
                "<p class='ib-why' style='margin:0 0 6px'>%s</p>"
                % (_esc(label), len(items), _esc(blurb)))
        out += "".join(_item_html(i) for i in items)
    return out


@router.get(_ROUTE, response_class=HTMLResponse)
def inbox_page(request: Request, fmt: str = Query(""), msg: str = Query("")):
    from src.automation import review_inbox as ri
    owner = _is_owner(request)
    try:
        with _conn() as conn:
            pend_items = ri.pending(conn)
            decided = ri.corpus(conn)
    except Exception:  # noqa: BLE001 — an empty/locked DB must never 500 the page
        pend_items, decided = [], []

    if fmt == "csv":
        if not owner:
            return PlainTextResponse("owner only", status_code=403)
        lines = ["kind,ref,status,decided_at,imported,note"]
        for r in decided:
            imported = "1" if (r.get("payload") or {}).get("imported") else "0"
            note = str(r.get("note") or "").replace(",", ";").replace("\n", " ")
            lines.append("%s,%s,%s,%s,%s,%s" % (
                r["kind"], str(r["ref"]).replace(",", ";"), r["status"],
                r.get("decided_at") or "", imported, note))
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    pend_by_kind: dict = {}
    for i in pend_items:
        pend_by_kind[i["kind"]] = pend_by_kind.get(i["kind"], 0) + 1
    split = _split_stats(decided)
    lived = sum(v["lived"]["approved"] + v["lived"]["rejected"] for v in split.values())

    note = ""
    if msg:
        note = ("<div class='ib-item' style='border-left:3px solid var(--up)'>%s</div>"
                % _esc(msg))

    head = (
        "<h2 style='margin:0 0 2px'>Review inbox</h2>"
        "<div style='font-size:12px;color:var(--ink-3);margin-bottom:10px'>"
        "The human-verification layer &mdash; %s</div>"
        % ifx.fence("not_advice", "everything the machine proposes waits here for a "
                                  "person's verdict"))
    kpis = (
        "<div style='margin:10px 0 4px'>"
        "<div class='ib-kpi'><b>%d</b><span>waiting on you</span></div>"
        "<div class='ib-kpi'><b>%d</b><span>decisions recorded</span></div>"
        "<div class='ib-kpi'><b>%d</b><span>decided here</span></div></div>"
        % (len(pend_items), len(decided), lived))

    body = [_CSS, head, note, ifx.readability_css(),
            ifx.bottom_line(
                "Nothing the machine produces counts until a person has approved it here. "
                "This page is that gate, and the record of every call made at it &mdash; "
                "which is what turns &ldquo;a human checks it&rdquo; into a number you can audit."),
            kpis,
            "<h3 style='margin:16px 0 4px'>How often the machine is right</h3>",
            _stats_table(split, pend_by_kind), _IMPORTED_CAVEAT]

    if owner:
        body.append("<h3 style='margin:20px 0 6px'>Your queue</h3>")
        body.append(_queue_html(pend_items))
        body.append("<p class='ib-why' style='margin-top:10px'>"
                    "<a href='%s?fmt=csv'>Download every decision (CSV)</a> &middot; "
                    "<a href='/dash/tags-review'>Theme-tag editor &rarr;</a></p>" % _ROUTE)
    else:
        body.append(_explainer())
        body.append("<p class='ib-why' style='margin-top:12px'>"
                    "The queue itself is private &mdash; it holds drafts that have not been "
                    "checked yet, and an unchecked draft is exactly what must not be "
                    "published. <a href='/dash/tracker'>Owner? Unlock &rarr;</a></p>")

    body.append(ifx.how_to_read_link())
    return HTMLResponse(_shell("Review inbox", "".join(body), active="inbox", wide=False))


@router.post(_ROUTE + "/decide")
def inbox_decide(request: Request, item_id: int = Form(...),
                 verdict: str = Form(...), note: str = Form("")):
    """Record a verdict (playbook item 11: writes are POST, never a GET).

    Owner-only. After the verdict lands, tags-kind items are applied through
    inbox_adapters (theme_tags' own helpers do the company_tags write) — the same
    single path the legacy surface now uses.
    """
    if not _is_owner(request):
        return RedirectResponse(_ROUTE, status_code=303)
    from src.automation import inbox_adapters as ia
    from src.automation import review_inbox as ri
    msg = ""
    try:
        with _conn() as conn:
            item = ri.decide(conn, item_id, verdict, note=(note or None))
            conn.commit()
            applied = ia.tags_apply(conn)  # no-op for non-tag kinds; idempotent
            n = applied["applied_approved"] + applied["applied_rejected"]
            msg = "Recorded: %s %s%s" % (
                item["status"], item["ref"], " (applied)" if n else "")
    except ValueError as e:
        msg = str(e)
    except Exception:  # noqa: BLE001
        msg = "Could not record that verdict."
    from urllib.parse import quote
    return RedirectResponse("%s?msg=%s" % (_ROUTE, quote(msg)), status_code=303)


def wire(app):
    """Durable mount fallback (v2_surfaces._ROUTER_SPECS is the primary path)."""
    app.include_router(router)


def _selftest() -> int:
    """Hermetic: a temp DB + a fake owner, exercising both audiences."""
    import os
    import shutil
    import sqlite3
    import tempfile

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    tmpdir = tempfile.mkdtemp(prefix="review_inbox_view_selftest_")
    path = os.path.join(tmpdir, "t.db")
    conn = sqlite3.connect(path)
    from src.automation import review_inbox as ri
    ri.ensure_schema(conn)
    ri.submit(conn, "tags", "TESTCO|Defence", "Proposed tag: Defence for TESTCO",
              payload={"symbol": "TESTCO", "tag": "Defence", "source": "keyword"},
              evidence_url="/dash/tags-review?sym=TESTCO")
    i2 = ri.submit(conn, "brief", "results:TESTCO:2026-06", "Results brief: TESTCO")
    ri.decide(conn, i2["id"], "approved", note="reads fine")
    ri.submit(conn, "tags", "OLDCO|PSU", "[imported] Tag decision: PSU for OLDCO",
              payload={"symbol": "OLDCO", "tag": "PSU", "imported": True})
    ri.decide(conn, 3, "approved")
    conn.commit()
    conn.close()

    # Patch THIS module object, never a re-import: under `python -m` the running
    # module is __main__ and `import src.web.review_inbox_view` would bind a SECOND
    # copy — the router below closes over these globals, so the patch must land here
    # (the sys.modules double-import seam, S78).
    import sys
    V = sys.modules[__name__]
    owner_flag = {"v": False}
    real_conn, real_owner = V._conn, V._is_owner
    V._conn = lambda: sqlite3.connect(path)          # type: ignore[assignment]
    V._is_owner = lambda request: owner_flag["v"]    # type: ignore[assignment]
    try:
        app = FastAPI()
        app.include_router(router)
        c = TestClient(app)

        pub = c.get(_ROUTE).text
        assert "Review inbox" in pub and "decisions recorded" in pub
        assert "TESTCO|Defence" not in pub, "PUBLIC page must not leak item refs"
        assert "Approve" not in pub, "PUBLIC page must not offer decide buttons"
        assert "Results brief" not in pub, "PUBLIC page must not leak brief titles"
        assert c.get(_ROUTE + "?fmt=csv").status_code == 403
        print("ok: anonymous -> methodology only (no refs, no titles, no buttons, no CSV)")

        owner_flag["v"] = True
        own = c.get(_ROUTE).text
        assert "TESTCO|Defence" in own and "Approve" in own
        assert "proposed by: keyword" in own, "evidence must show the proposer"
        csv = c.get(_ROUTE + "?fmt=csv")
        assert csv.status_code == 200 and "kind,ref,status" in csv.text
        assert "imported" in csv.text
        print("ok: owner -> queue + evidence + corpus CSV")

        # the honesty split: lived and imported never merge into one rate
        assert "Imported rate" in own and "Why two rates, not one" in own
        print("ok: stats table reports lived vs imported separately")
        print("review_inbox_view selftest OK — gate holds, queue renders, split honest")
        return 0
    finally:
        V._conn, V._is_owner = real_conn, real_owner
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(_selftest())
