"""Concall Intelligence (CCI) — structured extraction (the rated information).

Turns each ingested transcript into the four qualitative tables, reading it from
MANAGEMENT'S perspective (the §5 rubric in docs/concall-intelligence-design.md):
  - concall_guidance                 (every forward promise -> the follow-through ledger)
  - concall_behavior                 (credibility / transparency / courage / ... 0-100)
  - concall_redflags                 (hidden items the human eye skips)
  - concall_expectations_vs_actual   (in-line / understated / overstated / CONCEALED)

Routing (doctrine): a ONE-TIME Gemini Flash call per transcript via
src.core.llm_router.call_extractor (cached forever once extract_status='DONE').
Gemini-only — no silent Haiku fallback. The deterministic cross-period
settlement (resolve OPEN promises vs Screener actuals; market_recognized via
price reaction) is a SEPARATE pure-Python step (Phase 2), not this LLM pass.

Cost: ~Rs0.10-0.15 per full transcript (~12k in / ~3k out). --use-summary reads
Screener's free AI digest instead (~10x cheaper) for a quick first pass; the raw
transcript is preferred for the behavioural axes (a summary smooths over exactly
the concealment/courage signal we want).

CLI:
    python -m src.automation.concall_extract --symbol RELIANCE --limit 1 --dry-run
    python -m src.automation.concall_extract --symbol RELIANCE --limit 2
    python -m src.automation.concall_extract --pending --limit 50        # work the queue
    python -m src.automation.concall_extract --symbol IDEA --use-summary  # cheap mode
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Optional

from src.core.db import get_conn
from src.core.llm_router import call_extractor

log = logging.getLogger("hermes.concall_extract")

MODEL_VERSION = "cci-extract-v1/gemini"     # stamped on every row for drift audits
MAX_CHARS = 45000                            # transcript char cap (~12k tokens) — bounds cost

_STATEMENT_TYPES = {"revenue", "margin", "volume", "capex", "expansion", "debt_reduction",
                    "demand_outlook", "new_product", "cost_savings", "dividend_buyback", "other"}
_HORIZONS = {"this_q", "next_q", "fy", "multiyear_3_5y"}
_CLASSES = {"IN_LINE", "BEAT", "MISS", "UNDERSTATED", "OVERSTATED", "CONCEALED"}

_SYSTEM = """You are the most sceptical sell-side analyst alive, auditing an Indian listed company's \
earnings conference-call transcript. Read it from MANAGEMENT'S perspective and extract structured data. \
Be precise, quote verbatim evidence, and surface what a casual reader would miss.

Return ONLY valid JSON (no markdown, no prose) of exactly this shape:
{
  "guidance": [
    {"statement_type": "revenue|margin|volume|capex|expansion|debt_reduction|demand_outlook|new_product|cost_savings|dividend_buyback|other",
     "horizon": "this_q|next_q|fy|multiyear_3_5y",
     "claim_text": "one-sentence paraphrase of the forward promise/target",
     "quantified_target": <number or null>, "unit": "Rs_cr|%|MT|units|x|null",
     "confidence_language": "verbatim hedge/conviction phrase", "evidence": "short verbatim quote"}
  ],
  "behavior": {"credibility": 0-100, "transparency": 0-100, "courage": 0-100, "issue_handling": 0-100,
     "consistency": 0-100, "specificity": 0-100, "evasion": 0-100, "promo_vs_conservative": 0-100,
     "tone": 0-100, "confidence": 0-100, "evidence": "1-2 quotes that justify the scores"},
  "redflags": [
    {"flag_type": "guidance_walkback|metric_definition_change|segment_reclassification|stopped_disclosing|one_off_masking|working_capital_stress|related_party|capex_slippage|promise_quietly_dropped|accounting_change|optimism_without_numbers|blames_externals_repeatedly|other",
     "severity": 1-5, "evidence": "short verbatim quote"}
  ],
  "expectations_vs_actual": [
    {"metric": "revenue|ebitda|margin|pat|volume|...",
     "mgmt_expectation": "what they had earlier guided/implied",
     "expected_value": <number or null>, "actual_value": <number or null>,
     "classification": "IN_LINE|BEAT|MISS|UNDERSTATED|OVERSTATED|CONCEALED",
     "headwind_adjusted": true|false, "evidence": "short verbatim quote"}
  ]
}

Scoring rules: credibility/transparency/courage/issue_handling/consistency/specificity/tone/confidence -> \
higher is BETTER; evasion and promo_vs_conservative -> higher is WORSE. Anchor every score in evidence.
guidance: capture EVERY forward-looking statement; quantify where a number is stated.
redflags: only real, evidence-backed items a human eye skips. expectations_vs_actual: only where the call \
itself discusses the just-ended period against earlier guidance; headwind_adjusted=true means they warned \
of a headwind yet still delivered. Empty array / nulls where there is nothing. NEVER invent numbers."""


# --- JSON parsing -----------------------------------------------------------

def _repair_json(s: str) -> str:
    """Best-effort close of a TRUNCATED JSON object (output hit the token cap):
    close an open string, then close unbalanced [ / { in reverse order."""
    opens, in_str, esc = [], False, False
    for ch in s:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "[{":
            opens.append(ch)
        elif ch in "]}" and opens:
            opens.pop()
    rep = s + ('"' if in_str else "")
    # drop a dangling trailing comma before closing
    rep = re.sub(r",\s*$", "", rep.rstrip())
    for o in reversed(opens):
        rep += "]" if o == "[" else "}"
    return rep


def _parse_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    a, b = s.find("{"), s.rfind("}")
    if a != -1 and b != -1 and b > a:
        try:
            return json.loads(s[a:b + 1])
        except json.JSONDecodeError:
            pass
    # last resort: repair a truncated object (a big extraction that hit max_tokens)
    if a != -1:
        try:
            return json.loads(_repair_json(s[a:]))
        except json.JSONDecodeError:
            return None
    return None


def _i(v):
    """Coerce to int in 0..100 or None."""
    try:
        return max(0, min(100, int(round(float(v)))))
    except (TypeError, ValueError):
        return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _txt(v) -> Optional[str]:
    """Coerce a model-supplied field to TEXT-or-None. Under JSON mode the model
    sometimes returns a list/dict (e.g. evidence as an array of quotes); flatten
    those to a JSON string so the SQLite bind never sees an unsupported type."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)[:2000]
    s = str(v).strip()
    return s or None


# --- persistence (idempotent per (symbol, period)) --------------------------

def _persist(symbol: str, period: str, data: dict) -> dict:
    counts = {"guidance": 0, "redflags": 0, "behavior": 0, "eva": 0}
    with get_conn() as conn:
        # Wipe ALL prior extraction for this (symbol, source_period) before reinsert
        # — the delete-the-period-set-then-reinsert idempotency the sibling tables use.
        # The guidance delete is deliberately NOT status-scoped. A prior `AND
        # status='OPEN'` here left settlement-resolved rows (MET/MISSED/PARTIAL, set by
        # the Phase-2 settlement pass) behind, and the reinsert then added a fresh OPEN
        # copy of the SAME promise -> one statement counted twice in concall_guidance ->
        # inflated guidance_accuracy_score / n_promises_resolved in concall_scores.py.
        # Extraction owns a period's raw promise set; settlement is a deterministic
        # re-derivation from later concall_results, so discarding it here is lossless —
        # but settlement MUST be re-run (before concall_scores --rerank) after any
        # --force re-extract. See docs/concall-intelligence-design.md §5 (the contract).
        conn.execute("DELETE FROM concall_guidance WHERE symbol=? AND source_period=?",
                     (symbol, period))
        conn.execute("DELETE FROM concall_redflags WHERE symbol=? AND period_label=?", (symbol, period))
        conn.execute("DELETE FROM concall_behavior WHERE symbol=? AND period_label=?", (symbol, period))
        conn.execute("DELETE FROM concall_expectations_vs_actual WHERE symbol=? AND period_label=?",
                     (symbol, period))

        for g in (data.get("guidance") or []):
            st = (g.get("statement_type") or "other").lower()
            st = st if st in _STATEMENT_TYPES else "other"
            hz = (g.get("horizon") or "").lower()
            hz = hz if hz in _HORIZONS else None
            claim = _txt(g.get("claim_text"))
            if not claim:
                continue
            conn.execute(
                """INSERT INTO concall_guidance
                   (symbol, source_period, statement_type, horizon, claim_text, quantified_target,
                    unit, confidence_language, status, evidence, model_version)
                   VALUES (?,?,?,?,?,?,?,?, 'OPEN', ?, ?)""",
                (symbol, period, st, hz, claim, _num(g.get("quantified_target")),
                 _txt(g.get("unit")), _txt(g.get("confidence_language")),
                 _txt(g.get("evidence")), MODEL_VERSION))
            counts["guidance"] += 1

        b = data.get("behavior") or {}
        if b:
            conn.execute(
                """INSERT INTO concall_behavior
                   (symbol, period_label, credibility, transparency, courage, issue_handling,
                    consistency, specificity, evasion, promo_vs_conservative, tone, confidence,
                    evidence, model_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (symbol, period, _i(b.get("credibility")), _i(b.get("transparency")), _i(b.get("courage")),
                 _i(b.get("issue_handling")), _i(b.get("consistency")), _i(b.get("specificity")),
                 _i(b.get("evasion")), _i(b.get("promo_vs_conservative")), _i(b.get("tone")),
                 _i(b.get("confidence")), _txt(b.get("evidence")), MODEL_VERSION))
            counts["behavior"] = 1

        for rf in (data.get("redflags") or []):
            ft = (rf.get("flag_type") or "other").lower()
            sev = rf.get("severity")
            try:
                sev = max(1, min(5, int(sev)))
            except (TypeError, ValueError):
                sev = None
            conn.execute(
                """INSERT INTO concall_redflags (symbol, period_label, flag_type, severity, evidence,
                   period_first_seen, model_version) VALUES (?,?,?,?,?,?,?)""",
                (symbol, period, ft, sev, _txt(rf.get("evidence")), period, MODEL_VERSION))
            counts["redflags"] += 1

        for e in (data.get("expectations_vs_actual") or []):
            cls = (e.get("classification") or "").upper()
            cls = cls if cls in _CLASSES else None
            metric = (_txt(e.get("metric")) or "").lower()
            if not metric:
                continue
            ha = e.get("headwind_adjusted")
            ha = 1 if ha is True else (0 if ha is False else None)
            conn.execute(
                """INSERT INTO concall_expectations_vs_actual
                   (symbol, period_label, metric, mgmt_expectation, expected_value, actual_value,
                    classification, headwind_adjusted, evidence, model_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(symbol, period_label, metric) DO UPDATE SET
                     mgmt_expectation=excluded.mgmt_expectation, expected_value=excluded.expected_value,
                     actual_value=excluded.actual_value, classification=excluded.classification,
                     headwind_adjusted=excluded.headwind_adjusted, evidence=excluded.evidence,
                     model_version=excluded.model_version""",
                (symbol, period, metric, _txt(e.get("mgmt_expectation")), _num(e.get("expected_value")),
                 _num(e.get("actual_value")), cls, ha, _txt(e.get("evidence")), MODEL_VERSION))
            counts["eva"] += 1
    return counts


def _set_status(symbol: str, period: str, url: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE concalls SET extract_status=? WHERE symbol=? AND period_label=? AND transcript_url=?",
                     (status, symbol, period, url))


# --- extraction -------------------------------------------------------------

def _load_text(row, use_summary: bool, max_chars: int) -> Optional[str]:
    if use_summary:
        return (row["ai_summary"] or None)
    p = row["transcript_path"]
    if not p or not Path(p).exists():
        return None
    return Path(p).read_text(encoding="utf-8", errors="ignore")[:max_chars]


def extract_row(row, *, use_summary: bool = False, max_chars: int = MAX_CHARS,
                dry_run: bool = False) -> dict:
    symbol, period, url = row["symbol"], row["period_label"], row["transcript_url"]
    text = _load_text(row, use_summary, max_chars)
    if not text or len(text) < 200:
        log.warning("%s %s: no usable text (use_summary=%s)", symbol, period, use_summary)
        if not dry_run:
            _set_status(symbol, period, url, "FAIL")
        return {"symbol": symbol, "period": period, "status": "FAIL_NO_TEXT"}

    user = f"Company: {symbol}\nConcall period: {period}\n\nTRANSCRIPT:\n{text}"
    if dry_run:
        log.info("[dry-run] %s %s: would send %d chars (system %d chars)", symbol, period, len(text), len(_SYSTEM))
        return {"symbol": symbol, "period": period, "status": "DRY_RUN", "chars": len(text)}

    out, provider = call_extractor(system=_SYSTEM, user_msg=user, max_tokens=8000, timeout=120.0)
    if not out:
        _set_status(symbol, period, url, "FAIL")
        return {"symbol": symbol, "period": period, "status": f"FAIL_{provider}"}
    data = _parse_json(out)
    if not data:
        log.warning("%s %s: unparseable JSON from %s", symbol, period, provider)
        _set_status(symbol, period, url, "FAIL")
        return {"symbol": symbol, "period": period, "status": "FAIL_JSON"}

    try:
        counts = _persist(symbol, period, data)
    except Exception as e:  # noqa: BLE001 - one malformed row must not kill the batch
        log.warning("%s %s: persist failed: %s", symbol, period, e)
        _set_status(symbol, period, url, "FAIL")
        return {"symbol": symbol, "period": period, "status": "FAIL_PERSIST"}
    _set_status(symbol, period, url, "DONE")
    log.info("%s %s [%s]: %s", symbol, period, provider, counts)
    return {"symbol": symbol, "period": period, "status": "DONE", "provider": provider, **counts}


def pending_rows(symbol: Optional[str], limit: Optional[int], force: bool,
                 oldest: bool = False) -> list:
    # oldest-first is the right BACKFILL order: a concall settles only once its
    # promises' resolving quarter is reported, so the OLDEST extracted calls build a
    # settled track record soonest — and the blowups' pre-collapse calls (the scarce
    # avoid-tape signal) sit at the old end. newest-first is for steady-state incremental.
    order = "ASC" if oldest else "DESC"
    q = ("SELECT * FROM concalls WHERE parse_status='OK' AND transcript_url<>'' "
         + ("" if force else "AND (extract_status IS NULL OR extract_status='FAIL') "))
    args: list = []
    if symbol:
        q += "AND symbol=? "
        args.append(symbol.upper())
    q += f"ORDER BY concall_year {order}, concall_month {order}"
    if limit:
        q += " LIMIT ?"
        args.append(limit)
    with get_conn() as conn:
        return conn.execute(q, args).fetchall()


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI structured extraction (Gemini)")
    ap.add_argument("--symbol", help="restrict to one symbol")
    ap.add_argument("--pending", action="store_true", help="process the pending queue (all symbols)")
    ap.add_argument("--limit", type=int, help="max transcripts to process")
    ap.add_argument("--force", action="store_true", help="re-extract even if already DONE")
    ap.add_argument("--use-summary", action="store_true", help="extract from Screener AI summary (cheap mode)")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    ap.add_argument("--max-calls", type=int, default=18,
                    help="stop after this many LLM calls in one run (Gemini free tier = 20/day); 0 = unlimited")
    ap.add_argument("--oldest", action="store_true",
                    help="extract OLDEST concalls first (backfill: builds settled track records + pre-collapse calls soonest)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent, do not call the LLM")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not (args.symbol or args.pending):
        ap.error("give --symbol SYM or --pending")
    rows = pending_rows(args.symbol, args.limit, args.force, oldest=args.oldest)
    log.info("to process: %d transcripts (max-calls=%s)", len(rows), args.max_calls or "∞")
    totals = {"DONE": 0, "FAIL": 0, "guidance": 0, "redflags": 0, "eva": 0}
    made, consec_fail = 0, 0
    for row in rows:
        if args.max_calls and made >= args.max_calls and not args.dry_run:
            log.info("reached --max-calls %d; stopping (resume tomorrow / next run)", args.max_calls)
            break
        r = extract_row(row, use_summary=args.use_summary, max_chars=args.max_chars, dry_run=args.dry_run)
        if not args.dry_run:
            made += 1
        if r["status"] == "DONE":
            totals["DONE"] += 1
            consec_fail = 0
            for k in ("guidance", "redflags", "eva"):
                totals[k] += r.get(k, 0)
        elif r["status"].startswith("FAIL"):
            totals["FAIL"] += 1
            # FAIL_failed = the LLM call itself failed (almost always the daily quota);
            # stop early rather than burn the rest of the run hammering 429s.
            if r["status"] in ("FAIL_failed", "FAIL"):
                consec_fail += 1
                if consec_fail >= 3:
                    log.warning("3 consecutive call failures (likely Gemini daily quota) — stopping early")
                    break
    log.info("TOTALS (%d calls made): %s", made, totals)


if __name__ == "__main__":
    main()
