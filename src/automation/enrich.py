"""Company profile enrichment — the rich, multi-layer business dossier layer.

Replaces the manual "paste a CSV batch into Perplexity, merge back by symbol"
flow (docs/themes-perplexity-validation.md) with a CONTINUOUS, VPS-runnable
enricher that works top-down by liquidity (priority_rank) and grounds a cheap
Gemini synthesis on real fetched text — so the output is citable, not
hallucinated. It is the going-forward home of what Perplexity produced by hand:
a few-liner, a deeper "business nature" read, rich free-form theme tags, and the
official sector/industry — every layer kept as its own field (nothing flattened).

DOCTRINE (CLAUDE.md):
  • Rule-based fetch + GEMINI-ONLY synthesis. call_extractor runs with
    allow_anthropic_fallback=False → on any Gemini miss it SKIPS the name and
    NEVER spends a Claude/Haiku/Sonnet token. Safe in a timer.
  • Grounded, anti-hallucination: the model is fed Screener's business text and
    is told to return unverified=true (not a guess) when it can't substantiate.
  • Value > quantity: the most-liquid names (priority_rank 1..N) are enriched
    first, so spend tracks importance and we can stop/validate at any depth.

ISOLATION (per the autonomous-blanket-access rule): brand-new module; owns its
`company_profile` table via ensure_schema() — NO edit to db.py SCHEMA_BASE, NO
edit to the parallel-held patearn.py. It REUSES screener.py's fetcher and
theme_tags.THEME_VOCAB (single source of truth for the controlled vocab) rather
than duplicating them. Inert until run.

The 15-stock Perplexity sample structure is captured losslessly in `raw_json`;
known layers are promoted to explicit columns. New "components" the sample adds
later can be promoted from raw_json without re-enriching.

CLI:
    python -m src.automation.enrich --import-csv data/themes_export.csv  # seed universe + Perplexity rows
    python -m src.automation.enrich --backfill --limit 50                # enrich next 50 blanks, top-down
    python -m src.automation.enrich --symbol RELIANCE [--force]          # (re)enrich one name
    python -m src.automation.enrich --sync-vocab-tags                    # push vocab_tags → company_tags (ai, approved=0)
    python -m src.automation.enrich --show RELIANCE                      # print one profile
    python -m src.automation.enrich --stats                             # coverage summary
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from src.core.db import get_conn

log = logging.getLogger("hermes.enrich")


# --- owned table (additive; fold into db.py SCHEMA_BASE later if desired) -----
_SCHEMA = """
CREATE TABLE IF NOT EXISTS company_profile (
    symbol            TEXT PRIMARY KEY,
    priority_rank     INTEGER,            -- liquidity rank (90d turnover); drives processing order
    company_name      TEXT,
    is_equity         INTEGER DEFAULT 1,  -- 0 for ETFs / non-equity (skipped by --backfill)
    market_cap_cr     REAL,
    avg_turnover_90d  REAL,
    official_sector   TEXT,               -- Yahoo/Trendlyne taxonomy ("Basic Materials")
    official_industry TEXT,               --   "          "          ("Chemicals - Specialty")
    business_brief    TEXT,               -- the few-liner: what they do
    business_nature   TEXT,               -- deeper layer: B2B/B2C, asset intensity, cyclicality, drivers, moat
    theme_tags        TEXT,               -- rich free-form, pipe-delimited ("Datacenter & HPC|AI infrastructure")
    vocab_tags        TEXT,               -- controlled-vocab mapping, pipe-delimited (feeds /dash/themes)
    sources           TEXT,               -- URLs grounded on (space-separated); empty when unverified
    confidence        REAL,               -- 0..1 model self-rating
    unverified        INTEGER DEFAULT 0,  -- 1 = model could not substantiate → fields left thin, NOT guessed
    model_used        TEXT,               -- 'perplexity' (seed) | gemini model id
    source            TEXT,               -- 'perplexity' | 'gemini' | 'ramana'
    raw_json          TEXT,               -- the FULL structured record (lossless; promote new fields later)
    enriched_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_company_profile_rank ON company_profile(priority_rank);
CREATE INDEX IF NOT EXISTS idx_company_profile_todo ON company_profile(is_equity, business_brief, priority_rank);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


def _today() -> str:
    return date.today().isoformat()


def _pipe(items) -> Optional[str]:
    """['a','b'] -> 'a|b'; tolerates a string or None."""
    if not items:
        return None
    if isinstance(items, str):
        items = [items]
    out = [str(x).strip() for x in items if str(x).strip()]
    return "|".join(dict.fromkeys(out)) or None   # dedupe, preserve order


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    return t.strip()


# --- CSV seed import --------------------------------------------------------

def _to_float(s) -> Optional[float]:
    try:
        return float(s) if s not in (None, "") else None
    except (TypeError, ValueError):
        return None


def import_csv(path: str, conn=None) -> dict:
    """Seed `company_profile` from the ranked themes export.

    Always refreshes metadata (priority_rank, name, sector, liquidity). Rows that
    ALREADY carry a Perplexity business_brief are stored as source='perplexity'
    (the gold standard, retained — never re-enriched). Blank rows are seeded with
    metadata only, business_brief left NULL → they are what --backfill works on.
    COALESCE protects any prior enrichment on re-import (blanks never clobber).
    """
    if conn is None:
        with get_conn() as c:
            return import_csv(path, conn=c)
    ensure_schema(conn)
    seeded = perplexity_rows = 0
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sym = (row.get("symbol") or "").strip().upper()
            if not sym:
                continue
            brief = (row.get("business_brief") or "").strip() or None
            tags = (row.get("theme_tags") or "").strip() or None
            is_eq = 1 if (row.get("is_equity") or "").strip().lower() in ("true", "1", "y", "yes") else 0
            has_pplx = bool(brief)
            conn.execute(
                """INSERT INTO company_profile
                     (symbol, priority_rank, company_name, is_equity, market_cap_cr,
                      avg_turnover_90d, official_sector, official_industry,
                      business_brief, theme_tags, source, model_used, enriched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(symbol) DO UPDATE SET
                     priority_rank     = excluded.priority_rank,
                     company_name      = COALESCE(excluded.company_name, company_profile.company_name),
                     is_equity         = excluded.is_equity,
                     market_cap_cr     = COALESCE(excluded.market_cap_cr, company_profile.market_cap_cr),
                     avg_turnover_90d  = COALESCE(excluded.avg_turnover_90d, company_profile.avg_turnover_90d),
                     official_sector   = COALESCE(excluded.official_sector, company_profile.official_sector),
                     official_industry = COALESCE(excluded.official_industry, company_profile.official_industry),
                     business_brief    = COALESCE(excluded.business_brief, company_profile.business_brief),
                     theme_tags        = COALESCE(excluded.theme_tags, company_profile.theme_tags),
                     source            = COALESCE(excluded.source, company_profile.source),
                     model_used        = COALESCE(excluded.model_used, company_profile.model_used),
                     enriched_at       = COALESCE(excluded.enriched_at, company_profile.enriched_at)""",
                (sym, _to_float(row.get("priority_rank")), (row.get("company_name") or "").strip() or None,
                 is_eq, _to_float(row.get("market_cap_cr")), _to_float(row.get("avg_turnover_90d")),
                 (row.get("official_sector") or "").strip() or None,
                 (row.get("official_industry") or "").strip() or None,
                 brief, tags,
                 "perplexity" if has_pplx else None,
                 "perplexity" if has_pplx else None,
                 _today() if has_pplx else None))
            seeded += 1
            perplexity_rows += 1 if has_pplx else 0
    conn.commit()
    log.info("import_csv: %d rows seeded (%d carry Perplexity briefs, retained)", seeded, perplexity_rows)
    return {"seeded": seeded, "perplexity_rows": perplexity_rows}


# --- grounding (free fetch layer) -------------------------------------------

def _gather_sources(conn, symbol: str) -> tuple[str, list[str]]:
    """Return (grounding_text, source_urls). Prefers the already-harvested
    company_about; falls back to a live Screener fetch. Extensible: add company
    site / NSE / Wikipedia fetches here without touching the synthesis step."""
    parts: list[str] = []
    urls: list[str] = []
    row = conn.execute(
        "SELECT about, screener_industry FROM company_about WHERE symbol=? AND about IS NOT NULL",
        (symbol,)).fetchone()
    about = row["about"] if row else None
    industry = row["screener_industry"] if row else None
    if not about:
        # live fetch (reuse screener's fetcher; never raises fatally)
        try:
            from src.automation.screener import _fetch_company_html, _extract_about
            html = _fetch_company_html(symbol)
            if html:
                about, industry = _extract_about(BeautifulSoup(html, "lxml"))
        except Exception as e:  # noqa: BLE001
            log.warning("enrich %s: screener fetch failed: %s", symbol, e)
    if about:
        parts.append(f"Screener business description: {about}")
        urls.append(f"https://www.screener.in/company/{symbol}/")
    if industry:
        parts.append(f"Screener industry: {industry}")
    return ("\n".join(parts), urls)


# --- the Gemini synthesis (grounded, controlled vocab, anti-hallucination) --

def _vocab_labels() -> list[str]:
    from src.automation.theme_tags import THEME_VOCAB
    return [t["label"] for t in THEME_VOCAB]


def _build_system() -> str:
    vocab = ", ".join(_vocab_labels())
    # Two few-shot exemplars (from the Perplexity rows in the export) lock the
    # STYLE + DEPTH expected — especially the analytical "business_nature" layer.
    example = json.dumps({
        "business_brief": "India's leading decorative & industrial paints company; also waterproofing and home-improvement (kitchens, bath, decor).",
        "business_nature": "B2C-led branded consumer franchise with strong pricing power and a deep dealer-distribution moat. Demand tracks housing, repainting cycles and discretionary income; defensive but discretionary. Raw-material (crude derivatives, titanium dioxide) cost-sensitive on margins. Predominantly domestic.",
        "theme_tags": ["Chemicals", "Decorative paints", "Home improvement", "Consumption"],
        "vocab_tags": ["Chemicals", "Consumer Durables"],
        "official_sector": "Basic Materials", "official_industry": "Chemicals - Specialty",
        "sources": ["https://www.screener.in/company/ASIANPAINT/"],
        "confidence": 0.93, "unverified": False,
    }, ensure_ascii=False)
    return (
        "You are an equity-research analyst building a structured profile of an "
        "Indian-listed (NSE) company for a screening database. You are given the "
        "company's name and SOURCE TEXT. Produce a rich, multi-layer profile.\n\n"
        "Return STRICT JSON only (no prose, no markdown) with EXACTLY these keys:\n"
        "  business_brief   : one factual sentence (<=30 words) on what the company does.\n"
        "  business_nature  : 2-4 sentences on the NATURE of the business — B2B vs B2C, "
        "asset-heavy vs asset-light, cyclical vs defensive, commodity vs branded/pricing-power, "
        "domestic vs export, the core demand drivers, and any moat. This analytical layer is REQUIRED.\n"
        "  theme_tags       : a list of RICH, free-form, specific thematic tags (multi-label, "
        "e.g. ['Datacenter & HPC','AI infrastructure','Enterprise IT']). Be specific and honest.\n"
        f"  vocab_tags       : a list using ONLY this controlled vocabulary, spelled exactly: {vocab}. "
        "Assign every label that genuinely applies; [] if none fit.\n"
        "  official_sector  : broad sector if derivable, else null.\n"
        "  official_industry: specific industry if derivable, else null.\n"
        "  sources          : list of source URLs you actually relied on.\n"
        "  confidence       : 0.0-1.0.\n"
        "  unverified       : true if the SOURCE TEXT is insufficient AND you cannot "
        "substantiate the business from well-established public fact — then keep fields "
        "minimal and DO NOT fabricate. Returning unverified=true is correct, not a failure.\n\n"
        "ANTI-HALLUCINATION: never infer a business from the name alone. Ground claims in the "
        "source text or established fact. Honesty over completeness.\n\n"
        f"Example of the expected shape and depth:\n{example}"
    )


_SYSTEM = None  # built lazily (touches THEME_VOCAB import)


# Enrichment uses its OWN isolated Gemini client (NOT the shared llm_router) so it
# can pick the model + retry WITHOUT touching CCI's classifier model. GEMINI-ONLY
# by construction — never instantiates an Anthropic client. Primary = flash-LITE:
# ~8x cheaper than flash on output, and its quality was already excellent (KEI/
# TRITURBINE were lite). flash-with-thinking was a costly detour during a 503 spike
# (it drove the spend-cap hit) — now demoted to the rescue model only. Per-model
# token budget: flash "thinks" and eats output (needs 2048); lite barely thinks → 1024.
ENRICH_MODEL = "gemini-2.5-flash-lite"
ENRICH_FALLBACK_MODEL = "gemini-2.5-flash"
_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from openai import OpenAI
        from src.core.settings import settings
        _CLIENT = OpenAI(api_key=settings.gemini_api_key,
                         base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    return _CLIENT


def _gemini_json(system: str, user: str, *, retries: int = 3) -> tuple:
    """Structured JSON from Gemini, returned as (text, model_used) or (None, None).
    Tries the cheap primary model (retrying transient 503/429/5xx/network with
    backoff); if it keeps failing, rescues the name ONCE on the sturdier fallback
    so a run has no gaps. NEVER calls Anthropic."""
    for model in (ENRICH_MODEL, ENRICH_FALLBACK_MODEL):
        max_tokens = 1024 if model.endswith("lite") else 2048  # flash 'thinks' → needs headroom
        for attempt in range(retries):
            try:
                r = _client().chat.completions.create(
                    model=model, temperature=0.2,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    max_tokens=max_tokens)
                return r.choices[0].message.content, model
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                transient = (any(t in msg for t in ("503", "UNAVAILABLE", "429", "500", "502", "504"))
                             or "timeout" in msg.lower())
                if attempt < retries - 1 and transient:
                    time.sleep(2 * (attempt + 1) ** 2)  # 2s, 8s, 18s
                    continue
                log.warning("enrich %s failed (attempt %d/%d): %s", model, attempt + 1, retries, msg[:140])
                break  # give up on this model → try the fallback
    return None, None


def enrich_symbol(conn, symbol: str, *, force: bool = False) -> Optional[dict]:
    """Fetch grounding → Gemini synthesis → upsert one company_profile row.

    Returns the parsed profile dict, or None if skipped (already done / non-equity
    / no Gemini / parse failure). NEVER spends an Anthropic token."""
    global _SYSTEM
    symbol = symbol.upper().strip()
    ensure_schema(conn)
    cur = conn.execute(
        "SELECT is_equity, business_brief, company_name, official_sector, official_industry "
        "FROM company_profile WHERE symbol=?", (symbol,)).fetchone()
    if cur is not None and cur["is_equity"] == 0:
        return None
    if cur is not None and cur["business_brief"] and not force:
        return None  # already enriched

    name = (cur["company_name"] if cur else None) or symbol
    grounding, urls = _gather_sources(conn, symbol)
    known_sector = cur["official_sector"] if cur else None
    known_industry = cur["official_industry"] if cur else None

    user = (f"Company: {name}  (NSE symbol: {symbol})\n"
            + (f"Known sector/industry: {known_sector or '?'} / {known_industry or '?'}\n" if (known_sector or known_industry) else "")
            + ("Source text:\n" + grounding if grounding else
               "Source text: (none retrieved — rely only on well-established public fact, else unverified=true)"))[:8000]

    if _SYSTEM is None:
        _SYSTEM = _build_system()
    text, used_model = _gemini_json(_SYSTEM, user)  # lite→flash fallback, GEMINI-ONLY
    if not text:
        log.info("enrich %s: gemini unavailable after retries — skipped, NO Anthropic call", symbol)
        return None
    try:
        data = json.loads(_strip_fences(text))
    except Exception as e:  # noqa: BLE001
        log.warning("enrich %s: JSON parse failed: %s", symbol, e)
        return None

    # validate vocab_tags against the controlled vocabulary
    valid = set(_vocab_labels())
    vtags = [t for t in (data.get("vocab_tags") or []) if t in valid]
    model_sources = data.get("sources") or []
    all_sources = list(dict.fromkeys([*urls, *[s for s in model_sources if isinstance(s, str)]]))
    unverified = 1 if data.get("unverified") else 0

    conn.execute(
        """INSERT INTO company_profile
             (symbol, business_brief, business_nature, theme_tags, vocab_tags,
              official_sector, official_industry, sources, confidence, unverified,
              model_used, source, raw_json, enriched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(symbol) DO UPDATE SET
             business_brief    = excluded.business_brief,
             business_nature   = excluded.business_nature,
             theme_tags        = excluded.theme_tags,
             vocab_tags        = excluded.vocab_tags,
             official_sector   = COALESCE(company_profile.official_sector, excluded.official_sector),
             official_industry = COALESCE(company_profile.official_industry, excluded.official_industry),
             sources           = excluded.sources,
             confidence        = excluded.confidence,
             unverified        = excluded.unverified,
             model_used        = excluded.model_used,
             source            = excluded.source,
             raw_json          = excluded.raw_json,
             enriched_at       = excluded.enriched_at""",
        (symbol, (data.get("business_brief") or None), (data.get("business_nature") or None),
         _pipe(data.get("theme_tags")), _pipe(vtags),
         (data.get("official_sector") or None), (data.get("official_industry") or None),
         " ".join(all_sources) or None, _to_float(data.get("confidence")), unverified,
         used_model, "gemini", json.dumps(data, ensure_ascii=False), _today()))
    conn.commit()
    log.info("enrich %s: ok (unverified=%s, %d theme_tags, %d vocab_tags)",
             symbol, unverified, len((data.get("theme_tags") or [])), len(vtags))
    return data


def backfill(*, limit: Optional[int] = None, max_calls: Optional[int] = None,
             workers: int = 1) -> dict:
    """Enrich un-enriched equities TOP-DOWN by priority_rank. Idempotent (skips rows
    that already have a business_brief). `workers`>1 runs a thread pool — the slow
    part is the Screener fetch + Gemini call (network), so it parallelizes near-
    linearly; each worker uses its OWN connection. A high skip RATE trips a
    circuit-breaker (likely a 503 spike); sequential keeps the 12-consecutive guard."""
    with get_conn() as c:
        ensure_schema(c)
        rows = c.execute(
            "SELECT symbol FROM company_profile "
            "WHERE is_equity=1 AND (business_brief IS NULL OR business_brief='') "
            "ORDER BY priority_rank IS NULL, priority_rank "
            + (f"LIMIT {int(limit)}" if limit else "")).fetchall()
    syms = [r["symbol"] for r in rows]
    if max_calls:
        syms = syms[:int(max_calls)]

    def _one(sym):
        try:
            with get_conn() as c:
                return enrich_symbol(c, sym)
        except Exception as e:  # noqa: BLE001 - one bad symbol must not kill the run
            log.warning("enrich %s: %s", sym, e)
            return None

    done = skipped = 0
    if workers and workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_one, s) for s in syms]
            seen = 0
            for fut in as_completed(futs):
                seen += 1
                if fut.result() is None:
                    skipped += 1
                else:
                    done += 1
                if seen >= 3 * workers and skipped / seen > 0.7:
                    for f in futs:
                        f.cancel()
                    log.warning("backfill: skip rate %d/%d >70%% — likely a 503 spike; cancelling rest", skipped, seen)
                    break
    else:
        consecutive_none = 0
        for s in syms:
            if _one(s) is None:
                skipped += 1
                consecutive_none += 1
                if consecutive_none >= 12:
                    log.warning("backfill: 12 consecutive skips — stopping (idempotent; resume later)")
                    break
            else:
                done += 1
                consecutive_none = 0
    log.info("backfill: enriched %d, skipped %d, of %d candidates (workers=%s)", done, skipped, len(syms), workers)
    return {"enriched": done, "skipped": skipped, "candidates": len(syms)}


# --- bridge: vocab_tags → the existing /dash/themes review surface ----------

def sync_vocab_tags(conn=None) -> int:
    """Propose each profile's vocab_tags into company_tags as source='ai',
    approved=0 — so they flow into the existing /dash/tags-review surface and,
    once approved, into /dash/themes. Never disturbs index/ramana/rejected rows."""
    if conn is None:
        with get_conn() as c:
            return sync_vocab_tags(conn=c)
    rows = conn.execute(
        "SELECT symbol, vocab_tags FROM company_profile WHERE vocab_tags IS NOT NULL AND vocab_tags<>''"
    ).fetchall()
    n = 0
    for r in rows:
        sym = r["symbol"]
        for tag in (r["vocab_tags"] or "").split("|"):
            tag = tag.strip()
            if not tag:
                continue
            known = conn.execute(
                "SELECT 1 FROM company_tags WHERE symbol=? AND tag=? AND source IN ('index','ramana','rejected')",
                (sym, tag)).fetchone()
            if known:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO company_tags"
                "(symbol, tag, source, confidence, as_of, approved, note) "
                "VALUES (?,?,'ai',0.7,?,0,'from enrich.company_profile')", (sym, tag, _today()))
            n += 1
    conn.commit()
    log.info("sync_vocab_tags: proposed %d tags into company_tags (ai, approved=0)", n)
    return n


# --- read helpers -----------------------------------------------------------

def profile_for(conn, symbol: str) -> Optional[dict]:
    """The full profile for the per-stock dossier. None if absent."""
    r = conn.execute("SELECT * FROM company_profile WHERE symbol=?",
                     (symbol.upper().strip(),)).fetchone()
    return dict(r) if r else None


def stats(conn=None) -> dict:
    if conn is None:
        with get_conn() as c:
            return stats(conn=c)
    ensure_schema(conn)
    total = conn.execute("SELECT COUNT(*) c FROM company_profile").fetchone()["c"]
    eq = conn.execute("SELECT COUNT(*) c FROM company_profile WHERE is_equity=1").fetchone()["c"]
    enriched = conn.execute(
        "SELECT COUNT(*) c FROM company_profile WHERE business_brief IS NOT NULL AND business_brief<>''").fetchone()["c"]
    by_source = {r["source"]: r["c"] for r in conn.execute(
        "SELECT source, COUNT(*) c FROM company_profile WHERE business_brief IS NOT NULL GROUP BY source")}
    unv = conn.execute("SELECT COUNT(*) c FROM company_profile WHERE unverified=1").fetchone()["c"]
    pending = conn.execute(
        "SELECT COUNT(*) c FROM company_profile WHERE is_equity=1 AND (business_brief IS NULL OR business_brief='')").fetchone()["c"]
    return {"rows": total, "equities": eq, "enriched": enriched, "by_source": by_source,
            "unverified": unv, "pending_equities": pending}


# --- CLI --------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="Company profile enrichment (Gemini-only, grounded).")
    p.add_argument("--import-csv", metavar="PATH", help="seed the universe + Perplexity rows from the ranked export")
    p.add_argument("--backfill", action="store_true", help="enrich un-enriched equities top-down by priority_rank")
    p.add_argument("--symbol", metavar="SYM", help="(re)enrich one symbol")
    p.add_argument("--force", action="store_true", help="with --symbol: re-enrich even if already done")
    p.add_argument("--limit", type=int, default=None, help="cap candidates considered (--backfill)")
    p.add_argument("--max-calls", type=int, default=None, help="cap Gemini calls per run (--backfill)")
    p.add_argument("--workers", type=int, default=1, help="concurrent workers (--backfill); 6-10 = near-linear speedup")
    p.add_argument("--sync-vocab-tags", action="store_true", help="push vocab_tags into company_tags (ai, approved=0)")
    p.add_argument("--show", metavar="SYM", help="print one profile")
    p.add_argument("--stats", action="store_true", help="coverage summary")
    args = p.parse_args(argv)

    if args.import_csv:
        print(import_csv(args.import_csv))
    if args.symbol:
        with get_conn() as conn:
            res = enrich_symbol(conn, args.symbol, force=args.force)
        print(json.dumps(res, indent=2, ensure_ascii=False) if res else "(skipped — already enriched / non-equity / no Gemini)")
    if args.backfill:
        print(backfill(limit=args.limit, max_calls=args.max_calls, workers=args.workers))
    if args.sync_vocab_tags:
        print(f"proposed {sync_vocab_tags()} vocab tags into company_tags")
    if args.show:
        with get_conn() as conn:
            prof = profile_for(conn, args.show)
        print(json.dumps(prof, indent=2, ensure_ascii=False) if prof else "(no profile)")
    if args.stats:
        print(json.dumps(stats(), indent=2))
    if not any([args.import_csv, args.symbol, args.backfill, args.sync_vocab_tags, args.show, args.stats]):
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
