"""Auto-analyst event briefs v1 (D134 plan §4-E, layer L6) — ONE family: results landed.

Drafts a 6–10 line DESCRIPTIVE brief for the freshest `results_reactions` events
(research.db — the falsified-PEAD study's descriptive product) and queues each into
the Review Inbox (`review_inbox.submit(kind='brief')`) for human judgment. NOTHING
publishes from here — publishing APPROVED briefs to the wire is a separate later step.

The L6 grounding contract (plan §2):
  * every number comes from OUR tables — the results_reactions row + its meta
    thresholds — and the payload carries a per-number source map;
  * the TEMPLATE path is pure Python (₹0) and is the default;
  * the LLM path is OPT-IN (--llm / llm=True), Haiku/Gemini-Flash-class ONLY via
    llm_router.call_classifier(job="auto-analyst") — which meters itself into the
    cost ledger (LANE-R instrumentation);
  * budget law §5.4: per-job month-to-date spend >= AUTO_ANALYST_CAP_INR degrades
    the LLM path to the template — never a silent overrun (cap default = the plan
    §7.2 RATIFIED ₹200/mo (Ramana, 2026-07-16));
  * a rewrite may not INVENT numbers: the digit-subset guard rejects any LLM text
    whose numeric tokens are not a subset of the fact block's, falling back to the
    template;
  * every brief carries "AI-drafted, human-reviewed", the generation date and the
    descriptive fence ("context, not a signal"), and cites the PEAD falsification
    (ledger 2026-07-05: net return/vol 0.10 vs 0.85 benchmark) so a reader can never
    mistake drift history for a tradeable edge.

Compliance: this module lives in src/automation (outside the language gate's
src/web+src/pat scan set), so tests/test_auto_analyst.py runs the SAME _FORBIDDEN
lexicon over this file's source and over rendered briefs.

CLI: --run [--limit N] [--llm] | --pending-count | --selftest (hermetic temp DBs).
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Optional

HERMES_DB = "/opt/hermes/data/hermes.db"
RESEARCH_DB = "/opt/hermes/data/research.db"

# Plan §7.2 default PROPOSAL (₹/month for this job family) — Ramana ratifies the
# final value; change here + PROJECT_STATE decision-log entry when he does.
AUTO_ANALYST_CAP_INR = 200.0

BOARD_URL = "/dash/results-reactions"
KIND = "brief"

_LABEL = "AI-drafted, human-reviewed"
_FENCE = "context, not a signal"  # infographics._FENCE_COPY["context"] wording (single vocabulary)
_PEAD_NOTE = ("the tradeable PEAD book was falsified on our data "
              "(net return/vol 0.10 vs 0.85 benchmark) — this is recorded history, "
              "never a trade prompt")


# --------------------------------------------------------------------------- reads

def _ro(path: str) -> Optional[sqlite3.Connection]:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        con.row_factory = sqlite3.Row
        return con
    except sqlite3.Error:
        return None


def _has_table(con: sqlite3.Connection, name: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def latest_events(limit: int = 3, *, research_db: str = RESEARCH_DB) -> list[dict]:
    """Freshest results events, newest first. Empty-DB / missing-table grace."""
    con = _ro(research_db)
    if con is None:
        return []
    try:
        if not _has_table(con, "results_reactions"):
            return []
        meta = {}
        if _has_table(con, "results_reactions_meta"):
            meta = dict(con.execute("SELECT k, v FROM results_reactions_meta").fetchall())
        rows = con.execute(
            """SELECT sym, ptype, pend, t0, sue, ear, deliv_x, car22, car60,
                      beat, sue_high, deliv_high, settled
               FROM results_reactions ORDER BY t0 DESC, sym LIMIT ?""",
            (int(limit),)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["sue_hi_bar"] = float(meta.get("sue_hi") or 0) or None
            d["dlv_hi_bar"] = float(meta.get("dlv_hi") or 0) or None
            out.append(d)
        return out
    finally:
        con.close()


# ----------------------------------------------------------------- the brief itself

def _fmt(v, dp=2, signed=False) -> str:
    if v is None:
        return "n/a"
    s = f"{float(v):+.{dp}f}" if signed else f"{float(v):.{dp}f}"
    return s


def template_brief(ev: dict, *, today: Optional[str] = None) -> dict:
    """Pure-Python 6–10 line brief. Returns {ref, title, lines, text, numbers, links}."""
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sym = ev["sym"]
    stock_url = f"/dash/stock?sym={sym}"
    lines: list[str] = []
    numbers: dict = {}

    period = f"{ev.get('ptype') or 'Q'} period ending {ev.get('pend') or 'n/a'}"
    lines.append(f"{sym} reported ({period}); first tradeable day {ev.get('t0')}.")
    numbers["t0"] = {"value": ev.get("t0"), "source": BOARD_URL}
    numbers["pend"] = {"value": ev.get("pend"), "source": BOARD_URL}

    sue, bar = ev.get("sue"), ev.get("sue_hi_bar")
    beat_word = "a net-profit beat" if ev.get("beat") else "no net-profit beat"
    bar_txt = f" (board's high bar: {_fmt(bar)})" if bar else ""
    lines.append(f"Net-profit surprise (no-analyst SUE): {_fmt(sue, signed=True)}{bar_txt} — {beat_word} on recorded numbers.")
    numbers["sue"] = {"value": sue, "source": BOARD_URL}

    dlv, dbar = ev.get("deliv_x"), ev.get("dlv_hi_bar")
    conf = "the strong hand confirmed on day one" if ev.get("deliv_high") else "no strong-hand confirmation on day one"
    dbar_txt = f" (high bar: {_fmt(dbar)}×)" if dbar else ""
    lines.append(f"Tape read: delivered value ran {_fmt(dlv)}× its median{dbar_txt} — {conf}.")
    numbers["deliv_x"] = {"value": dlv, "source": BOARD_URL}

    lines.append(f"Event-day abnormal move: {_fmt((ev.get('ear') or 0) * 100, dp=2, signed=True)}%.")
    numbers["ear_pct"] = {"value": (ev.get("ear") or 0) * 100, "source": BOARD_URL}

    if ev.get("settled"):
        lines.append(f"Realized drift (settled): CAR22 {_fmt((ev.get('car22') or 0) * 100, signed=True)}% · "
                     f"CAR60 {_fmt((ev.get('car60') or 0) * 100, signed=True)}%.")
        numbers["car22_pct"] = {"value": (ev.get("car22") or 0) * 100, "source": BOARD_URL}
        numbers["car60_pct"] = {"value": (ev.get("car60") or 0) * 100, "source": BOARD_URL}
    else:
        lines.append("Drift window still open — realized CAR lands only after settlement; nothing here forecasts it.")

    lines.append(f"Context: {_PEAD_NOTE}.")
    lines.append(f"Sources: board {BOARD_URL} · stock {stock_url}.")
    lines.append(f"{_LABEL} · generated {today} · {_FENCE}.")

    ref = f"results:{sym}:{ev.get('pend')}"
    title = f"Results brief — {sym} {ev.get('ptype') or 'Q'} {ev.get('pend')} (SUE {_fmt(sue, signed=True)})"
    return {
        "ref": ref, "title": title, "lines": lines, "text": "\n".join(lines),
        "numbers": numbers,
        "links": {"board": BOARD_URL, "stock": stock_url},
        "path": "template",
    }


# ------------------------------------------------------------------- LLM (opt-in)

_DIGITS = re.compile(r"\d+(?:\.\d+)?")


def _digit_tokens(text: str) -> set:
    return set(_DIGITS.findall(text or ""))


def job_mtd_inr(*, hermes_db: str = HERMES_DB, job_prefix: str = "auto-analyst") -> float:
    """This job family's month-to-date ₹ from the cost ledger (0.0 on any grace path)."""
    con = _ro(hermes_db)
    if con is None:
        return 0.0
    try:
        if not _has_table(con, "cost_ledger"):
            return 0.0
        month_start = datetime.now(timezone.utc).strftime("%Y-%m-01")
        row = con.execute(
            "SELECT COALESCE(SUM(inr_estimate), 0) FROM cost_ledger "
            "WHERE job LIKE ? AND ts >= ?", (job_prefix + "%", month_start)).fetchone()
        return float(row[0] or 0.0)
    finally:
        con.close()


def llm_rewrite(brief: dict, *, llm_fn=None, hermes_db: str = HERMES_DB,
                cap_inr: float = AUTO_ANALYST_CAP_INR) -> dict:
    """Optionally rewrite the template lines more fluently. SAME facts only.

    Degrades to the template (never errors, never overruns):
      * cap reached (per-job MTD >= cap_inr)  -> template (§5.4);
      * LLM failure / empty                   -> template;
      * digit-subset guard: rewrite may not contain numeric tokens absent from
        the fact block                        -> template.
    The final label/fence/sources lines are ALWAYS re-appended verbatim.
    """
    spent = job_mtd_inr(hermes_db=hermes_db)
    if spent >= cap_inr:
        out = dict(brief)
        out["path"] = "template (LLM cap reached: MTD %.2f >= %.2f)" % (spent, cap_inr)
        return out

    if llm_fn is None:
        def llm_fn(system, user):  # pragma: no cover - exercised on the box
            from src.core.llm_router import call_classifier
            text, _provider = call_classifier(system=system, user_msg=user,
                                              max_tokens=600, job="auto-analyst")
            return text

    fact_block = "\n".join(brief["lines"][:-3])  # facts only; tail re-appended below
    system = ("You rewrite factual finance notes in plain, calm English. Keep EVERY "
              "number exactly as given, add NO new numbers, no advice, no verbs that "
              "urge action. The surprise figure is measured against the company's OWN "
              "history (no analysts) — never say 'expectations'; say 'vs its own history'. "
              "Return 4 to 6 short lines, one sentence each.")
    try:
        rewritten = (llm_fn(system, fact_block) or "").strip()
    except Exception:
        rewritten = ""

    if not rewritten or not _digit_tokens(rewritten) <= _digit_tokens(fact_block):
        out = dict(brief)
        if rewritten:
            out["path"] = "template (digit-subset guard rejected the rewrite)"
        else:
            out["path"] = "template (LLM path unavailable)"
        return out

    # invariant: only the fact lines are rewritable; the PEAD-context, Sources and
    # label/fence lines (the last 3) are re-appended VERBATIM on every path.
    tail = brief["lines"][-3:]
    lines = [ln for ln in rewritten.splitlines() if ln.strip()][:6] + tail
    out = dict(brief)
    out["lines"] = lines
    out["text"] = "\n".join(lines)
    out["path"] = "llm"
    return out


# ------------------------------------------------------------------------- runner

def run(limit: int = 3, *, llm: bool = False, hermes_db: str = HERMES_DB,
        research_db: str = RESEARCH_DB, llm_fn=None, today: Optional[str] = None) -> dict:
    """Draft briefs for the freshest events and queue them in the Review Inbox.

    Idempotent: review_inbox.submit is first-write-wins on (kind, ref), so a
    re-run never duplicates an existing brief. Returns counts + refs.
    """
    from src.automation import review_inbox

    events = latest_events(limit, research_db=research_db)
    if not events:
        return {"drafted": 0, "queued": 0, "refs": [], "note": "no results events"}

    con = sqlite3.connect(hermes_db, timeout=30)
    try:
        queued, refs = 0, []
        for ev in events:
            brief = template_brief(ev, today=today)
            if llm:
                brief = llm_rewrite(brief, llm_fn=llm_fn, hermes_db=hermes_db)
            res = review_inbox.submit(
                con, KIND, brief["ref"], brief["title"],
                payload={"text": brief["text"], "lines": brief["lines"],
                         "numbers": brief["numbers"], "links": brief["links"],
                         "path": brief["path"], "label": _LABEL, "fence": _FENCE},
                evidence_url=brief["links"]["board"])
            refs.append(brief["ref"])
            # submit() leaves committing to the caller's conn; commit per item so a
            # crash mid-batch keeps the drafted briefs (and the trailing insert is
            # never lost to close()-rollback).
            con.commit()
            if res.get("created"):
                queued += 1
        return {"drafted": len(events), "queued": queued, "refs": refs}
    finally:
        con.close()


# ------------------------------------------------------------------------ selftest

def _selftest() -> int:
    import tempfile, os
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + name)
        ok = ok and bool(cond)

    tmp = tempfile.mkdtemp(prefix="auto_analyst_")
    rdb, hdb = os.path.join(tmp, "r.db"), os.path.join(tmp, "h.db")
    rc = sqlite3.connect(rdb)
    rc.execute("""CREATE TABLE results_reactions (sym TEXT, ptype TEXT, pend TEXT,
                  t0 TEXT, entry_date TEXT, sue REAL, ear REAL, deliv_x REAL,
                  med_turn REAL, car22 REAL, car60 REAL, beat INT, sue_high INT,
                  deliv_high INT, settled INT)""")
    rc.execute("CREATE TABLE results_reactions_meta (k TEXT, v REAL)")
    rc.executemany("INSERT INTO results_reactions_meta VALUES (?,?)",
                   [("sue_hi", 2.1176), ("dlv_hi", 2.8530)])
    rc.execute("INSERT INTO results_reactions VALUES "
               "('TESTCO','Q','2026-06-30','2026-07-13','2026-07-14',"
               "2.01,0.0086,2.14,1.0,NULL,NULL,1,0,0,0)")
    rc.commit(); rc.close()
    sqlite3.connect(hdb).close()

    evs = latest_events(5, research_db=rdb)
    check("latest_events returns the synthetic row", len(evs) == 1 and evs[0]["sym"] == "TESTCO")

    b = template_brief(evs[0], today="2026-07-15")
    check("6-10 lines", 6 <= len(b["lines"]) <= 10)
    check("label + date + fence present",
          _LABEL in b["text"] and "2026-07-15" in b["text"] and _FENCE in b["text"])
    check("PEAD falsification cited", "falsified" in b["text"])
    check("per-number source map", all("source" in v for v in b["numbers"].values()))

    r1 = run(5, hermes_db=hdb, research_db=rdb, today="2026-07-15")
    r2 = run(5, hermes_db=hdb, research_db=rdb, today="2026-07-15")
    check("queued once", r1["queued"] == 1 and r2["queued"] == 0)

    guard = llm_rewrite(b, llm_fn=lambda s, u: "Profit grew 999x.", hermes_db=hdb)
    check("digit-subset guard falls back", guard["path"].startswith("template"))

    kept = llm_rewrite(b, llm_fn=lambda s, u: "SUE was 2.01 with 2.14x delivered value.",
                       hermes_db=hdb)
    check("clean rewrite kept + tail re-appended", kept["path"] == "llm" and _LABEL in kept["text"])

    check("empty-DB grace", latest_events(research_db=os.path.join(tmp, "none.db")) == [])
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Auto-analyst results briefs -> Review Inbox (L6).")
    ap.add_argument("--run", action="store_true", help="draft + queue the freshest events")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--llm", action="store_true",
                    help="opt-in LLM rewrite (cheap-model router; cap-gated; default OFF)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.run:
        out = run(a.limit, llm=a.llm)
        print(json.dumps(out, indent=1))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
