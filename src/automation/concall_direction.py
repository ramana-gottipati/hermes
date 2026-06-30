"""LLM-derived DIRECTION for concall forward-looking statements — replaces the brittle regex polarity.

The keyword regex misfired on semantics (e.g. "Consolidated revenue" -> false "no-capex pullback"),
which is unacceptable for an institutional audience. The robust fix is to let the model that already
comprehends the sentence emit the company's INTENT direction. This BACKFILLS
`concall_guidance.direction` (increase | maintain | decrease | none) by batch-classifying the existing
claim_texts — cheap (short claims, ~20 per call). New full extractions set it inline (concall_extract).
`concall_signals.polarity` then reads THIS field, not keywords.

CLI:
  python -m src.automation.concall_direction --backfill --limit 40 --show   # cheap sample to verify
  python -m src.automation.concall_direction --backfill                     # full (capex,expansion)
  python -m src.automation.concall_direction --show
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time

from src.core.db import get_conn
from src.core.llm_router import call_extractor

log = logging.getLogger("hermes.concall_direction")

_DIRS = {"increase", "maintain", "decrease", "none"}
BATCH = 20

_SYS = """You classify a company's stated INTENT for forward-looking statements made on an earnings \
call. For each numbered statement, output the direction the company intends for THAT specific \
metric/plan — read the sentence literally:
  "increase"  = growing / adding / investing more / fresh capex / expanding / raising / scaling up
  "decrease"  = cutting / deferring / winding down / "no capex" / "negligible" / reducing the plan
  "maintain"  = keeping it steady / unchanged / at current levels
  "none"      = no directional intent (a stated fact, a definition, a past result, no plan)

Judge the COMPANY'S INTENT for the plan, not whether a number is large. "No capex is planned" = \
decrease. "We will invest Rs 500 crore" = increase. "Consolidated revenue was Rs 14,720 crore" = \
none (a reported fact, not a plan). Return ONLY a JSON object mapping each number (as a string) to \
exactly one of those four words, e.g. {"1":"increase","2":"decrease","3":"none"}."""


def _ensure_col(conn) -> None:
    try:
        conn.execute("ALTER TABLE concall_guidance ADD COLUMN direction TEXT")
    except Exception:  # noqa: BLE001 - column already exists
        pass


def classify(claims: list) -> list:
    """claims -> list of directions (same length); None where the model didn't return a valid label."""
    if not claims:
        return []
    user = "\n".join(f"{i + 1}. {(c or '')[:300]}" for i, c in enumerate(claims))
    out = None
    for attempt in range(4):                       # ride out transient 503 capacity spikes
        out, _ = call_extractor(system=_SYS, user_msg=user, max_tokens=900, timeout=90.0)
        if out:
            break
        if attempt < 3:
            time.sleep(4 * (attempt + 1))
    if not out:
        return [None] * len(claims)
    s = re.sub(r"^```(?:json)?", "", out.strip()).strip()
    s = re.sub(r"```$", "", s).strip()
    a, b = s.find("{"), s.rfind("}")
    try:
        d = json.loads(s[a:b + 1]) if a >= 0 and b > a else {}
    except json.JSONDecodeError:
        return [None] * len(claims)
    res = []
    for i in range(len(claims)):
        v = str(d.get(str(i + 1), "")).lower().strip()
        res.append(v if v in _DIRS else None)
    return res


def backfill(types, limit=None) -> int:
    with get_conn() as conn:
        _ensure_col(conn)
        q = ("SELECT id, claim_text FROM concall_guidance "
             "WHERE direction IS NULL AND claim_text IS NOT NULL AND claim_text<>''")
        args: list = []
        if types:
            q += " AND statement_type IN (%s)" % ",".join("?" * len(types))
            args += types
        q += " ORDER BY id"
        if limit:
            q += " LIMIT ?"
            args.append(limit)
        rows = conn.execute(q, args).fetchall()
    log.info("to classify: %d statements", len(rows))
    done = fail = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        dirs = classify([r["claim_text"] for r in chunk])
        with get_conn() as conn:
            for r, dr in zip(chunk, dirs):
                if dr:
                    conn.execute("UPDATE concall_guidance SET direction=? WHERE id=?", (dr, r["id"]))
                    done += 1
                else:
                    fail += 1
        if (i // BATCH) % 10 == 0:
            log.info("  %d/%d classified", done, len(rows))
    log.info("classified %d (%d unparsed)", done, fail)
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description="LLM-derived direction for concall statements")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--types", default="capex,expansion", help="comma statement_types (blank = all)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--show", action="store_true", help="print a sample of classified rows")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    types = [t.strip() for t in args.types.split(",") if t.strip()] if args.types else None
    if args.backfill:
        print("classified", backfill(types, args.limit))
    if args.show:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT symbol, statement_type st, direction, substr(claim_text,1,70) t "
                "FROM concall_guidance WHERE direction IS NOT NULL AND statement_type IN ('capex','expansion') "
                "ORDER BY id DESC LIMIT 20").fetchall()
            for r in rows:
                print(f"  {r['symbol']:11} {r['st']:9} {r['direction'] or '-':9} | {r['t']}")


if __name__ == "__main__":
    main()
