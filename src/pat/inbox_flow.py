"""Pat 'inbox' data-flow — "what's waiting on me?" answered IN THE CHAT (S160, Ramana-directed).

Ramana, 2026-07-15: *"I'm surprised that you're still providing it under /inbox. I'm not sure
what it is. I prefer to have communication take place here in the chat; if something isn't
available, it should be linked to the full application itself."*

He was right, and the audit was blunt: the Review Inbox had been silently accumulating asks
for him — AI-drafted briefs, tag proposals, rule-lab verdicts — while NO channel told him so.
Pat could only EXPLAIN the term ("review inbox" was a glossary slug in PAT_EXPLAIN, not a
flow); the heartbeat DM never mentioned it; Telegram never mentioned it. It was registered in
the Trust nav, so no gate fired — but "registered" is not "reaches you". This flow is the
missing half: the queue now REPORTS ITSELF conversationally, and the lens link rides along so
the full surface is one click away rather than a URL to remember.

CONTRACT (mirrors participants_flow.py / rulelab_flow.py):
  * PURE logic here — `parse_inbox()` (a ₹0 pre-pass in engine.route) + `waiting()` (a bounded
    read over review_items). Render = web.py:_inbox_flow.
  * READ-ONLY, always. Pat REPORTS what waits; it never approves, rejects or decides — a
    judgment is a deliberate act on the owner-gated lens, never a chat side effect. This is
    the same line rule_lab_inbox draws: canon carries a human signature.
  * CONSERVATIVE: needs a waiting/approval/review cue. Runs AFTER nav, so "where is the review
    inbox" stays a navigate. A miss yields None.
  * Kind labels are PLAIN ENGLISH (Guardrail #9: no internal jargon in what a human reads) —
    'rule_verdict' is a slug; "a rule-lab verdict" is an answer. Single-sourced here and
    reused by the heartbeat nudge, so the two channels can never drift apart.
"""
from __future__ import annotations

import re

# Plain-English names for the machine's kinds — the ONE place they are spelled for a human.
# (kind -> (singular, plural)). An unknown kind degrades to its slug rather than vanishing:
# a new producer must still be COUNTED even before someone writes it a label.
KIND_WORDS: dict = {
    "brief": ("an AI-drafted event brief", "AI-drafted event briefs"),
    "rule_verdict": ("a rule-lab verdict", "rule-lab verdicts"),
    "tags": ("a tag proposal", "tag proposals"),
    "alert-ack": ("an alert to acknowledge", "alerts to acknowledge"),
    "rebalance": ("a rebalance diff", "rebalance diffs"),
    "anomaly": ("an anomaly flag", "anomaly flags"),
}

LENS_URL = "/dash/inbox"

_WAIT_RE = re.compile(
    r"\b(waiting|pending|outstanding|awaiting|to review|for review|to approve|"
    r"needs? (?:my )?(?:approval|sign[- ]?off|attention|review)|"
    r"my (?:approval|sign[- ]?off|attention|input|judgement|judgment)|"
    r"review inbox|inbox|approval queue|sign[- ]?off)\b")
_ASK_RE = re.compile(
    r"\b(what|which|any|anything|how many|show|list|is there|are there|do i|"
    r"waiting|pending|outstanding)\b")
# Other lenses own these words — don't steal their asks.
_NOT_MINE = re.compile(r"\b(email|mail|gmail|telegram message|whatsapp)\b")


def kind_phrase(kind: str, n: int) -> str:
    """(kind, count) -> plain English. Unknown kinds degrade to the slug, never drop."""
    words = KIND_WORDS.get(kind)
    if not words:
        return f"{n} × {kind}"
    return f"{n} {words[1]}" if n != 1 else f"{words[0]}"


def parse_inbox(query: str) -> dict | None:
    """"what's waiting on me" / "anything needing my approval" -> {flow:"inbox"} | None.

    Conservative: needs a waiting/approval cue AND an ask cue. Bare "inbox" alone does not
    fire (that's a page-find → navigate); "what's in my inbox" does.
    """
    q = (query or "").lower()
    if _NOT_MINE.search(q):
        return None
    if not _WAIT_RE.search(q):
        return None
    if not _ASK_RE.search(q):
        return None
    return {"flow": "inbox", "params": {}}


def waiting(conn) -> dict:
    """What currently waits on the human. Bounded read; empty-DB grace -> total 0.

    Returns {total, by_kind: [{kind, n, phrase}], items: [{id, kind, title, ref, created_at,
    evidence_url}], link}. Newest-first for the items shown (what changed most recently is
    what he most likely wants to see); counts cover the WHOLE queue, not just the shown slice.
    """
    from src.automation import review_inbox
    try:
        rows = review_inbox.pending(conn)
    except Exception:                       # never let a chat answer 500 on a DB hiccup
        rows = []
    counts: dict = {}
    for r in rows:
        counts[r.get("kind") or "?"] = counts.get(r.get("kind") or "?", 0) + 1
    by_kind = [{"kind": k, "n": n, "phrase": kind_phrase(k, n)}
               for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    items = [{"id": r.get("id"), "kind": r.get("kind"), "title": r.get("title") or "",
              "ref": r.get("ref") or "", "created_at": r.get("created_at") or "",
              "evidence_url": r.get("evidence_url") or ""}
             for r in sorted(rows, key=lambda r: (r.get("created_at") or "", r.get("id") or 0),
                             reverse=True)[:8]]
    return {"total": len(rows), "by_kind": by_kind, "items": items, "link": LENS_URL}


def summary_phrase(w: dict) -> str:
    """One human sentence for a queue state — reused by the heartbeat DM nudge so the
    chat and the DM can never describe the same queue differently."""
    if not w.get("total"):
        return "nothing is waiting on you"
    parts = [b["phrase"] for b in w["by_kind"]]
    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = " and ".join(parts)
    else:
        body = ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{w['total']} waiting on you: {body}"


def _selftest() -> int:
    import sqlite3
    from src.automation import review_inbox

    # recognition
    assert parse_inbox("what's waiting on me?") == {"flow": "inbox", "params": {}}
    assert parse_inbox("anything needing my approval") is not None
    assert parse_inbox("what needs my sign-off") is not None
    assert parse_inbox("what's in my inbox") is not None
    assert parse_inbox("how many items are pending") is not None
    assert parse_inbox("check my email") is None            # not ours
    # a LOCATIONAL ask is never a queue report: nav wins earlier in the chain anyway, but
    # this flow declines it on its own too, so re-ordering the chain can't make it steal one.
    assert parse_inbox("where is the review inbox") is None
    assert parse_inbox("tcs results") is None

    # plain english, never a slug
    assert kind_phrase("rule_verdict", 1) == "a rule-lab verdict"
    assert kind_phrase("brief", 2) == "2 AI-drafted event briefs"
    assert kind_phrase("newkind", 3) == "3 × newkind"        # unknown still counted

    conn = sqlite3.connect(":memory:")
    review_inbox.ensure_schema(conn)
    w = waiting(conn)
    assert w["total"] == 0 and summary_phrase(w) == "nothing is waiting on you"

    review_inbox.submit(conn, "brief", "results:TCS:2026-06-30", "Results brief — TCS", {})
    review_inbox.submit(conn, "brief", "results:INFY:2026-06-30", "Results brief — INFY", {})
    review_inbox.submit(conn, "rule_verdict", "abc123", "Rule-lab: NEW-BENCHMARK", {})
    conn.commit()
    w = waiting(conn)
    assert w["total"] == 3, w
    assert w["by_kind"][0] == {"kind": "brief", "n": 2,
                               "phrase": "2 AI-drafted event briefs"}, w["by_kind"]
    s = summary_phrase(w)
    assert s == "3 waiting on you: 2 AI-drafted event briefs and a rule-lab verdict", s
    assert "rule_verdict" not in s                            # no slugs reach a human
    assert len(w["items"]) == 3 and w["link"] == LENS_URL

    # a decided item leaves the queue
    review_inbox.decide(conn, 1, "approved")
    conn.commit()
    assert waiting(conn)["total"] == 2
    conn.close()
    print("INBOX_FLOW selftest OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else print(__doc__) or 0)
