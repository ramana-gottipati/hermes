"""Theme tags — a MULTI-LABEL thematic classification layer (session 33).

A company can carry several theme tags at once — an EPC name is
Infrastructure + Industrialization-proxy + Transport/Logistics — beside its
single `primary_sector` and its index memberships. The layer is ADDITIVE: it
touches neither `stock_index_membership` nor `stock_signals.primary_sector`.

Storage = `company_tags(symbol, tag, source, confidence, as_of, approved, note)`
with three provenance tiers:

  source='index'   deterministic seed from a thematic index membership (a fact,
                   approved=1). Re-derived idempotently each run from CURRENT
                   membership; never disturbs the ai/ramana rows.
  source='ai'      proposed by a cheap LLM from the business description + latest
                   results (approved=0 — surfaced as "proposed" until sign-off).
  source='ramana'  human approved / hand-added (approved=1).

This module owns the controlled vocabulary (THEME_VOCAB — the single source of
truth), the deterministic seeder (NO LLM), the read helpers the dashboard uses,
the quarterly LLM proposer (Phase 2 — gated on a description corpus existing in
`company_about`), and the approve/reject/add helpers behind the review surface.

Run on the VPS:
    python3 -m src.automation.theme_tags --seed        # deterministic (re)seed from indices
    python3 -m src.automation.theme_tags --counts       # per-theme member counts
    python3 -m src.automation.theme_tags --show RELIANCE # tags for one symbol
    python3 -m src.automation.theme_tags --propose       # LLM proposals (Phase 2, needs corpus)

Cost note: the proposer routes through llm_router.call_classifier — Gemini Flash
first, Anthropic Haiku as fallback (doctrine D20). It is NEVER Sonnet, and runs
at most quarterly. Today there is no description corpus, so --propose is a no-op.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Iterable, Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.theme_tags")


# --- The controlled vocabulary ---------------------------------------------
# Ordered display groups → themes. `seed_indices` (when present) makes a theme
# DETERMINISTIC: every member of those indices gets the tag with source='index'.
# An empty `seed_indices` marks a CROSS-CUTTING theme that no single index
# captures (Industrialization-proxy, Make-in-India, …) — those stay empty until
# the LLM proposer / Ramana fill them. `blurb` is the one-line "what it means".
THEME_VOCAB: list[dict] = [
    # ---- Sector-aligned (1:1 with an NSE sector index) --------------------
    {"label": "Auto", "group": "Sectors", "blurb": "Automobiles & auto components",
     "seed_indices": ["Nifty Auto"]},
    {"label": "Banks", "group": "Sectors", "blurb": "Scheduled commercial banks (public + private)",
     "seed_indices": ["Nifty Bank", "Nifty Private Bank", "Nifty PSU Bank"]},
    {"label": "Financial Services", "group": "Sectors", "blurb": "NBFCs, insurers, AMCs, exchanges & banks",
     "seed_indices": ["Nifty Financial Services"]},
    {"label": "FMCG", "group": "Sectors", "blurb": "Fast-moving consumer goods",
     "seed_indices": ["Nifty FMCG"]},
    {"label": "IT", "group": "Sectors", "blurb": "IT services & software",
     "seed_indices": ["Nifty IT"]},
    {"label": "Media", "group": "Sectors", "blurb": "Media & entertainment",
     "seed_indices": ["Nifty Media"]},
    {"label": "Metals", "group": "Sectors", "blurb": "Ferrous & non-ferrous metals & mining",
     "seed_indices": ["Nifty Metal"]},
    {"label": "Pharma", "group": "Sectors", "blurb": "Pharmaceuticals",
     "seed_indices": ["Nifty Pharma"]},
    {"label": "Healthcare", "group": "Sectors", "blurb": "Hospitals, diagnostics & healthcare services",
     "seed_indices": ["Nifty Healthcare Index"]},
    {"label": "Realty", "group": "Sectors", "blurb": "Real-estate developers",
     "seed_indices": ["Nifty Realty"]},
    {"label": "Consumer Durables", "group": "Sectors", "blurb": "Consumer durables & electronics",
     "seed_indices": ["Nifty Consumer Durables"]},
    {"label": "Chemicals", "group": "Sectors", "blurb": "Specialty & commodity chemicals",
     "seed_indices": ["Nifty Chemicals"]},
    {"label": "Energy", "group": "Sectors", "blurb": "Power, utilities & integrated energy",
     "seed_indices": ["Nifty Energy"]},
    {"label": "Oil & Gas", "group": "Sectors", "blurb": "Upstream, refining, gas & OMCs",
     "seed_indices": ["Nifty Oil & Gas"]},

    # ---- Capex & industrials (the thematic capex indices) -----------------
    {"label": "Infrastructure", "group": "Capex & industrials", "blurb": "EPC, roads, ports, construction & capital assets",
     "seed_indices": ["Nifty Infrastructure"]},
    {"label": "Defence", "group": "Capex & industrials", "blurb": "Defence manufacturing & PSUs",
     "seed_indices": ["Nifty India Defence"]},
    {"label": "Commodities", "group": "Capex & industrials", "blurb": "Broad commodity producers (metals, energy, cement, chem)",
     "seed_indices": ["Nifty Commodities"]},

    # ---- Ownership lens ----------------------------------------------------
    {"label": "PSU Banks", "group": "Ownership", "blurb": "Public-sector banks",
     "seed_indices": ["Nifty PSU Bank"]},
    {"label": "Private Banks", "group": "Ownership", "blurb": "Private-sector banks",
     "seed_indices": ["Nifty Private Bank"]},

    # ---- Cross-cutting (no index captures these — LLM-proposed / manual) ---
    {"label": "Capital Goods", "group": "Cross-cutting", "blurb": "Industrial machinery & equipment makers",
     "seed_indices": []},
    {"label": "Industrialization-proxy", "group": "Cross-cutting", "blurb": "Beneficiaries of India's capex & manufacturing build-out",
     "seed_indices": []},
    {"label": "Power / Renewables", "group": "Cross-cutting", "blurb": "Generation, transmission, solar/wind & the green-energy chain",
     "seed_indices": []},
    {"label": "Transport / Logistics", "group": "Cross-cutting", "blurb": "Logistics, ports, rail, roads & mobility",
     "seed_indices": []},
    {"label": "Make-in-India", "group": "Cross-cutting", "blurb": "Import-substitution / domestic-manufacturing (PLI) plays",
     "seed_indices": []},
    {"label": "PSU", "group": "Cross-cutting", "blurb": "Government-owned enterprises (broad)",
     "seed_indices": []},
]

# Display order of the groups on /dash/themes.
THEME_GROUPS: list[str] = ["Sectors", "Capex & industrials", "Ownership", "Cross-cutting"]

# label -> vocab entry, and label -> rank (for stable on-read ordering).
_VOCAB_BY_LABEL: dict[str, dict] = {t["label"]: t for t in THEME_VOCAB}
_VOCAB_RANK: dict[str, int] = {t["label"]: i for i, t in enumerate(THEME_VOCAB)}


def vocab_entry(label: str) -> Optional[dict]:
    return _VOCAB_BY_LABEL.get(label)


def _today() -> str:
    return date.today().isoformat()


def _order_key(label: str) -> tuple:
    """Stable ordering: known vocab in defined order, then anything else A-Z."""
    return (_VOCAB_RANK.get(label, 10_000), label)


# --- Deterministic index seeder (NO LLM) -----------------------------------

def seed_from_indices(conn=None, as_of: Optional[str] = None) -> int:
    """(Re)build all source='index' tags from CURRENT index memberships.

    Idempotent: deletes the prior deterministic layer and re-derives it, so a
    membership change (a stock added/dropped from an index) is reflected on the
    next run. NEVER touches source in ('ai','ramana'). Returns rows written.
    """
    if conn is None:
        with get_conn() as c:
            return seed_from_indices(conn=c, as_of=as_of)
    as_of = as_of or _today()
    conn.execute("DELETE FROM company_tags WHERE source='index'")
    n = 0
    for t in THEME_VOCAB:
        idxs = t.get("seed_indices") or []
        if not idxs:
            continue
        ph = ",".join("?" for _ in idxs)
        syms = [r[0] for r in conn.execute(
            f"SELECT DISTINCT symbol FROM stock_index_membership WHERE index_name IN ({ph})",
            idxs).fetchall()]
        for s in syms:
            conn.execute(
                "INSERT OR REPLACE INTO company_tags"
                "(symbol, tag, source, confidence, as_of, approved) "
                "VALUES (?,?,'index',1.0,?,1)", (s, t["label"], as_of))
            n += 1
    conn.commit()
    log.info("theme seed: wrote %d index-derived tags (as_of %s)", n, as_of)
    return n


# --- Read helpers (used by the dashboard) -----------------------------------

def approved_tags_for(conn, symbols: Iterable[str]) -> dict[str, list[str]]:
    """{symbol: [tag labels]} — DISTINCT approved tags per symbol, vocab-ordered.

    Deduped across provenance (an index fact + a Ramana add of the same tag show
    once). Returns only symbols that have at least one approved tag.
    """
    syms = [s for s in {x for x in symbols} if s]
    if not syms:
        return {}
    out: dict[str, set] = {}
    # SQLite has a parameter cap (~999); chunk to be safe on Nifty-500 sweeps.
    for i in range(0, len(syms), 800):
        chunk = syms[i:i + 800]
        ph = ",".join("?" for _ in chunk)
        for r in conn.execute(
            f"SELECT symbol, tag FROM company_tags WHERE approved=1 AND symbol IN ({ph})",
            chunk).fetchall():
            out.setdefault(r[0], set()).add(r[1])
    return {s: sorted(tags, key=_order_key) for s, tags in out.items()}


def tags_with_provenance(conn, symbol: str) -> list[dict]:
    """All tags for ONE symbol with source/confidence/approved — for the stock
    page (chips) and the review surface. Deduped by tag (best provenance wins:
    approved beats proposed; ramana > index > ai on ties)."""
    rows = [dict(r) for r in conn.execute(
        "SELECT tag, source, confidence, as_of, approved, note FROM company_tags "
        "WHERE symbol=? ", (symbol,)).fetchall()]
    src_rank = {"ramana": 0, "index": 1, "ai": 2}
    best: dict[str, dict] = {}
    for r in rows:
        cur = best.get(r["tag"])
        cand = (-(r["approved"] or 0), src_rank.get(r["source"], 9))
        if cur is None or cand < cur["_k"]:
            r["_k"] = cand
            best[r["tag"]] = r
    out = sorted(best.values(), key=lambda r: _order_key(r["tag"]))
    for r in out:
        r.pop("_k", None)
    return out


def theme_counts(conn, approved_only: bool = True) -> dict[str, int]:
    """{tag label: distinct-symbol count}. Includes zero-count vocab themes so
    the browse page shows the full intended taxonomy (the cross-cutting ones read
    'awaiting tagging')."""
    appr = "AND approved=1" if approved_only else ""
    rows = conn.execute(
        f"SELECT tag, COUNT(DISTINCT symbol) c FROM company_tags WHERE 1=1 {appr} GROUP BY tag"
    ).fetchall()
    counts = {r[0]: r[1] for r in rows}
    for t in THEME_VOCAB:
        counts.setdefault(t["label"], 0)
    return counts


def theme_members(conn, label: str, approved_only: bool = True) -> list[str]:
    """Distinct symbols carrying a theme tag."""
    appr = "AND approved=1" if approved_only else ""
    return [r[0] for r in conn.execute(
        f"SELECT DISTINCT symbol FROM company_tags WHERE tag=? {appr}", (label,)).fetchall()]


def proposals_pending(conn, limit: int = 500) -> list[dict]:
    """AI proposals awaiting Ramana's review (approved=0, source='ai')."""
    return [dict(r) for r in conn.execute(
        "SELECT symbol, tag, confidence, as_of, note FROM company_tags "
        "WHERE approved=0 AND source='ai' ORDER BY confidence DESC, symbol LIMIT ?",
        (limit,)).fetchall()]


# --- Approval surface mutations ---------------------------------------------

def approve(conn, symbol: str, tag: str) -> None:
    """Promote an AI proposal to live (kept as its own source='ramana' row so the
    fact survives the next deterministic reseed, and the original ai row is
    cleared)."""
    symbol = symbol.upper().strip()
    conn.execute(
        "INSERT OR REPLACE INTO company_tags(symbol, tag, source, confidence, as_of, approved) "
        "VALUES (?,?,'ramana',1.0,?,1)", (symbol, tag, _today()))
    conn.execute("DELETE FROM company_tags WHERE symbol=? AND tag=? AND source='ai'", (symbol, tag))
    conn.commit()


def reject(conn, symbol: str, tag: str) -> None:
    conn.execute("DELETE FROM company_tags WHERE symbol=? AND tag=? AND source='ai'",
                 (symbol.upper().strip(), tag))
    conn.commit()


def add_manual(conn, symbol: str, tag: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO company_tags(symbol, tag, source, confidence, as_of, approved) "
        "VALUES (?,?,'ramana',1.0,?,1)", (symbol.upper().strip(), tag, _today()))
    conn.commit()


# --- Phase 2: the quarterly LLM proposer (gated on a description corpus) -----

_PROPOSE_SYSTEM = (
    "You are a buy-side analyst tagging an Indian-listed company with thematic "
    "labels for a screening dashboard. You are given the company's business "
    "description. Choose ONLY from this controlled vocabulary (use the exact "
    "labels): {vocab}. A company may carry SEVERAL labels (e.g. an EPC firm is "
    "Infrastructure + Industrialization-proxy + Transport / Logistics). Prefer "
    "the CROSS-CUTTING labels that an index membership would NOT already capture. "
    "Reply with STRICT JSON only: {{\"tags\": [{{\"tag\": \"<label>\", "
    "\"confidence\": 0.0-1.0, \"why\": \"<=12 words\"}}]}}. No prose."
)


def propose_with_haiku(conn=None, symbols: Optional[list[str]] = None,
                       limit: int = 200) -> int:
    """Read company_about + propose cross-cutting tags via a cheap LLM.

    PHASE 2 — gated on `company_about` having description text (populated
    best-effort by screener.fetch_company on the existing cadence). Today the
    corpus is empty, so this is a no-op. Proposals land as source='ai',
    approved=0 for review at /dash/tags-review. Routes through
    llm_router.call_classifier (Gemini Flash → Haiku; never Sonnet).
    """
    from src.core.llm_router import call_classifier

    if conn is None:
        with get_conn() as c:
            return propose_with_haiku(conn=c, symbols=symbols, limit=limit)
    rows = conn.execute(
        "SELECT symbol, about FROM company_about "
        "WHERE about IS NOT NULL AND length(about) > 40 "
        + ("AND symbol IN (%s)" % ",".join("?" for _ in symbols) if symbols else "")
        + " ORDER BY fetched_at DESC LIMIT ?",
        ((symbols or []) + [limit])).fetchall()
    if not rows:
        log.info("propose: no business descriptions in company_about yet — no-op")
        return 0
    vocab = ", ".join(t["label"] for t in THEME_VOCAB)
    system = _PROPOSE_SYSTEM.format(vocab=vocab)
    valid = set(_VOCAB_BY_LABEL)
    n = 0
    for r in rows:
        sym, about = r[0], (r[1] or "")[:4000]
        try:
            text, _ = call_classifier(system=system,
                                      user_msg=f"Company {sym}. Business:\n{about}",
                                      max_tokens=400)
            data = json.loads(_strip_fences(text))
        except Exception as e:  # noqa: BLE001
            log.warning("propose %s: %s", sym, e)
            continue
        for item in data.get("tags", []):
            tag = (item.get("tag") or "").strip()
            if tag not in valid:
                continue
            conf = float(item.get("confidence") or 0.0)
            why = (item.get("why") or "")[:200]
            # don't propose what we already KNOW deterministically / by hand
            exists = conn.execute(
                "SELECT 1 FROM company_tags WHERE symbol=? AND tag=? AND source IN ('index','ramana')",
                (sym, tag)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO company_tags"
                "(symbol, tag, source, confidence, as_of, approved, note) "
                "VALUES (?,?,'ai',?,?,0,?)", (sym, tag, conf, _today(), why))
            n += 1
        conn.commit()
    log.info("propose: wrote %d AI tag proposals across %d companies", n, len(rows))
    return n


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
    return t.strip()


# --- CLI --------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Theme tags — seed / inspect / propose")
    p.add_argument("--seed", action="store_true", help="deterministic (re)seed from index memberships")
    p.add_argument("--counts", action="store_true", help="print per-theme member counts")
    p.add_argument("--show", metavar="SYMBOL", help="print tags for one symbol")
    p.add_argument("--propose", action="store_true", help="LLM proposals (Phase 2; needs company_about)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.seed:
        n = seed_from_indices()
        print(f"seeded {n} index-derived tags")
    if args.counts:
        with get_conn() as conn:
            counts = theme_counts(conn)
        for t in THEME_VOCAB:
            print(f"  {t['label']:26} {counts.get(t['label'], 0):>4}   [{t['group']}]")
    if args.show:
        with get_conn() as conn:
            for r in tags_with_provenance(conn, args.show.upper().strip()):
                flag = "" if r["approved"] else " (proposed)"
                print(f"  {r['tag']:26} {r['source']:7} conf={r['confidence']}{flag}")
    if args.propose:
        n = propose_with_haiku()
        print(f"proposed {n} AI tags")
    if not any([args.seed, args.counts, args.show, args.propose]):
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
