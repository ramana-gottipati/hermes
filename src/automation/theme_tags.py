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
    python3 -m src.automation.theme_tags --seed             # deterministic (re)seed from indices
    python3 -m src.automation.theme_tags --keyword-propose   # FREE keyword proposals (the default; ₹0)
    python3 -m src.automation.theme_tags --report            # corpus + proposals + what's still empty
    python3 -m src.automation.theme_tags --counts            # per-theme member counts
    python3 -m src.automation.theme_tags --show RELIANCE     # tags for one symbol
    python3 -m src.automation.theme_tags --llm-propose       # opt-in GEMINI-ONLY top-up (never Claude)

Cost note: the PRIMARY proposer is deterministic keyword rules over company_about
— ₹0, no LLM, no rate limits (doctrine: rule-based > LLM). --llm-propose is an
opt-in top-up that is GEMINI-ONLY (call_extractor, allow_anthropic_fallback=False)
— it SKIPS a name rather than ever falling back to Claude. Never Sonnet, never Haiku.
"""

from __future__ import annotations

import json
import logging
import re
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
    {"label": "Construction / EPC", "group": "Capex & industrials",
     "blurb": "Contract construction & EPC — builds infra/buildings FOR clients (≠ realty developers)",
     "seed_indices": []},

    # ---- Ownership lens ----------------------------------------------------
    {"label": "PSU Banks", "group": "Ownership", "blurb": "Public-sector banks",
     "seed_indices": ["Nifty PSU Bank"]},
    {"label": "Private Banks", "group": "Ownership", "blurb": "Private-sector banks",
     "seed_indices": ["Nifty Private Bank"]},

    # ---- Services & consumer (no index captures these — keyword / manual) --
    {"label": "Aviation", "group": "Services & consumer", "blurb": "Airlines & airports",
     "seed_indices": []},
    {"label": "Travel & Tourism", "group": "Services & consumer", "blurb": "Travel, tourism, ticketing & holidays",
     "seed_indices": []},
    {"label": "Hospitality", "group": "Services & consumer", "blurb": "Hotels, resorts, restaurants & QSR",
     "seed_indices": []},

    # ---- Cross-cutting (no index captures these — keyword / manual) --------
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
THEME_GROUPS: list[str] = ["Sectors", "Capex & industrials", "Ownership", "Services & consumer", "Cross-cutting"]

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
        "WHERE symbol=? AND source != 'rejected'", (symbol,)).fetchall()]
    src_rank = {"ramana": 0, "index": 1, "keyword": 2, "ai": 3}
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
    """All proposals awaiting Ramana's review (approved=0 — keyword OR llm; a
    'rejected' tombstone is approved=0 but is NOT a proposal, so exclude it)."""
    return [dict(r) for r in conn.execute(
        "SELECT symbol, tag, source, confidence, as_of, note FROM company_tags "
        "WHERE approved=0 AND source != 'rejected' ORDER BY confidence DESC, symbol LIMIT ?",
        (limit,)).fetchall()]


# --- Approval surface mutations ---------------------------------------------

def approve(conn, symbol: str, tag: str) -> None:
    """Promote a proposal to live (kept as its own source='ramana' row so the
    fact survives the next reseed/re-propose; the original proposal row — keyword
    or llm — is cleared)."""
    symbol = symbol.upper().strip()
    conn.execute(
        "INSERT OR REPLACE INTO company_tags(symbol, tag, source, confidence, as_of, approved) "
        "VALUES (?,?,'ramana',1.0,?,1)", (symbol, tag, _today()))
    conn.execute("DELETE FROM company_tags WHERE symbol=? AND tag=? AND approved=0", (symbol, tag))
    conn.commit()


def reject(conn, symbol: str, tag: str) -> None:
    """Dismiss a proposal DURABLY — drop the proposal row and leave a tombstone
    (source='rejected') so the weekly keyword/LLM pass won't re-propose it.
    Reversible via unreject()."""
    symbol = symbol.upper().strip()
    conn.execute("DELETE FROM company_tags WHERE symbol=? AND tag=? AND approved=0", (symbol, tag))
    conn.execute(
        "INSERT OR REPLACE INTO company_tags(symbol, tag, source, confidence, as_of, approved, note) "
        "VALUES (?,?,'rejected',NULL,?,0,'dismissed')", (symbol, tag, _today()))
    conn.commit()


def unreject(conn, symbol: str, tag: str) -> None:
    """Lift a dismissal so the tag can be proposed again."""
    conn.execute("DELETE FROM company_tags WHERE symbol=? AND tag=? AND source='rejected'",
                 (symbol.upper().strip(), tag))
    conn.commit()


def add_manual(conn, symbol: str, tag: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO company_tags(symbol, tag, source, confidence, as_of, approved) "
        "VALUES (?,?,'ramana',1.0,?,1)", (symbol.upper().strip(), tag, _today()))
    conn.commit()


# --- The FREE proposer: deterministic keyword rules (NO LLM, ₹0) -----------
# The primary proposer (doctrine: rule-based > LLM). Matches each company's
# business description + Screener industry (from company_about) against a
# keyword map → proposes the CROSS-CUTTING themes no index seeds. Proposals land
# as source='keyword', approved=0 for Ramana's review (same gate as the LLM
# path), so keyword imprecision is filtered by the human. Idempotent: clears its
# own prior proposals each run. Costs nothing, no rate limits, fully reproducible.
KEYWORD_RULES: dict[str, list[str]] = {
    "Power / Renewables": [r"\bsolar\b", r"\bwind\b", r"renewable", r"photovoltaic",
        r"green hydrogen", r"power generation", r"power transmission",
        r"transmission (and|&|&amp;) distribution", r"\bhydro(power|electric|-electric)?\b",
        r"energy storage", r"battery storage", r"clean energy", r"green energy", r"power utility"],
    "Transport / Logistics": [r"logistic", r"supply[- ]chain", r"\bports?\b", r"\brailways?\b",
        r"\bfreight\b", r"warehous", r"\bshipping\b", r"\b3pl\b", r"\bcontainer", r"trucking",
        r"last[- ]mile", r"cold chain", r"\bairports?\b"],
    "Make-in-India": [r"make in india", r"import substitut", r"indigeni[sz]", r"\bpli\b",
        r"production[- ]linked", r"locali[sz]ation", r"atmanirbhar", r"domestic manufactur"],
    "PSU": [r"public sector", r"government of india", r"govt\.? of india", r"maharatna",
        r"navratna", r"miniratna", r"state[- ]owned", r"central public sector", r"\bcpse\b",
        r"a government (company|enterprise|undertaking)", r"government[- ]owned"],
    # 'machinery' alone over-matches (every manufacturer USES machinery) — require
    # maker-language so a tyre/FMCG co isn't tagged a capital-goods company:
    "Capital Goods": [r"capital goods", r"machine tools", r"industrial machinery",
        r"industrial equipment", r"capital equipment", r"engineering products",
        r"\bturbines?\b", r"\bboilers?\b", r"compressors?", r"heavy engineering",
        r"\bcastings?\b", r"\bforgings?\b"],
    # sector catches for names an index membership missed:
    # contract CONSTRUCTION / EPC (builds for clients) — kept precise so pipe/cement/
    # equipment/developer names aren't swept in (bare "construction" over-matches):
    "Construction / EPC": [r"contract construction", r"civil construction", r"\bepc\b",
        r"engineering (and|&) construction", r"construction (contractor|company|services|business|division)",
        r"construct(s|ed|ing|ion of) (roads|highways|expressway|buildings|metro|bridges|dams|tunnels)",
        r"road(s)? (and|&) highway", r"highway construction", r"\bexpressway", r"turnkey project",
        r"infrastructure (and|&) buildings"],
    "Chemicals": [r"chemical", r"petrochemical", r"agrochemical", r"specialty chem"],
    "Pharma": [r"pharmaceutical", r"\bformulations?\b", r"\bgenerics?\b drug"],
    "Realty": [r"real estate", r"\brealty\b", r"property develop", r"residential project",
        r"commercial real estate"],
    # services & consumer — so a name like IndiGo is tagged HONESTLY (aviation +
    # travel + transport), not forced into one bucket:
    "Aviation": [r"\bairlines?\b", r"\baviation\b", r"air travel", r"low[- ]cost carrier",
        r"passenger airline", r"air(craft| carrier)", r"\bairports?\b"],
    # airlines ARE travel/tourism (so IndiGo gets Aviation + Travel) — but match
    # 'airline'/'passenger airline', NOT bare 'aircraft', so an aircraft-COMPONENTS
    # maker (says "aircraft", not "airline") isn't mis-tagged a travel company:
    "Travel & Tourism": [r"\btravel\b", r"\btouris[mt]", r"\bholidays?\b", r"tour operator",
        r"\bticketing\b", r"travel (services|agency)", r"hospitality and travel",
        r"\bairlines?\b", r"passenger airline", r"low[- ]cost carrier"],
    # NOT bare 'catering' — "catering TO <x>" is an idiom for "serving", which
    # false-tagged a defence firm. Require catering-as-a-business.
    "Hospitality": [r"\bhotels?\b", r"\bhospitality\b", r"\bresorts?\b", r"\brestaurants?\b",
        r"quick[- ]service restaurant", r"\bqsr\b", r"catering services?", r"food catering"],
}
# Industrialization-proxy = a supplier to India's MANUFACTURING/CAPEX build-out.
# Derive ONLY from Capital Goods + Defence (genuine industrialization) — NOT from
# broad Nifty-Infrastructure membership, which also carries airlines/telecom/
# utilities and would mis-tag e.g. IndiGo or a hospital. Honesty over recall.
_DERIVE_INDUSTRIALIZATION = {"Capital Goods", "Defence"}
_KW_COMPILED = {t: [re.compile(p, re.I) for p in pats] for t, pats in KEYWORD_RULES.items()}


def propose_from_keywords(conn=None) -> int:
    """Deterministic, free proposer over company_about. Clears prior keyword
    proposals, re-derives from current descriptions. Skips tags already known via
    index/ramana. Returns rows written. Approved keyword proposals become
    source='ramana' on approval, so they survive this clear."""
    if conn is None:
        with get_conn() as c:
            return propose_from_keywords(conn=c)
    conn.execute("DELETE FROM company_tags WHERE source='keyword'")
    rows = conn.execute(
        "SELECT symbol, about, screener_industry FROM company_about "
        "WHERE about IS NOT NULL AND length(about) > 20").fetchall()
    n = 0
    for r in rows:
        sym = r[0]
        text = ((r[1] or "") + " " + (r[2] or "")).lower()
        # skip what's already a fact (index/ramana) OR durably dismissed (rejected)
        known = {x[0] for x in conn.execute(
            "SELECT tag FROM company_tags WHERE symbol=? AND source IN ('index','ramana','rejected')",
            (sym,)).fetchall()}
        proposed: dict[str, list] = {}
        for theme, pats in _KW_COMPILED.items():
            if theme in known:
                continue
            hits = []
            for p in pats:
                m = p.search(text)
                if m:
                    hits.append(m.group(0).strip())
            if hits:
                proposed[theme] = sorted(set(hits))
        if "Industrialization-proxy" not in known and (known | set(proposed)) & _DERIVE_INDUSTRIALIZATION:
            proposed.setdefault("Industrialization-proxy", ["derived: capital-goods / defence"])
        for theme, hits in proposed.items():
            note = ("matched: " + ", ".join(hits))[:190]
            conn.execute(
                "INSERT OR REPLACE INTO company_tags"
                "(symbol, tag, source, confidence, as_of, approved, note) "
                "VALUES (?,?,'keyword',0.6,?,0,?)", (sym, theme, _today(), note))
            n += 1
    conn.commit()
    log.info("keyword propose: wrote %d proposals across %d described companies", n, len(rows))
    return n


# --- The LLM proposer: GEMINI-ONLY, never Claude (opt-in top-up) -------------

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


def propose_with_llm(conn=None, symbols: Optional[list[str]] = None,
                     limit: int = 200) -> int:
    """OPT-IN LLM top-up beyond the free keyword proposer — GEMINI-ONLY, NEVER
    Claude. Routes through call_extractor with allow_anthropic_fallback=False, so
    when Gemini's free quota is spent it SKIPS the name (returns no Haiku call) —
    zero Claude spend, ever. Proposals land as source='ai', approved=0 for review
    at /dash/tags-review. Use only when you want nuance the keyword rules miss.
    """
    from src.core.llm_router import call_extractor

    if conn is None:
        with get_conn() as c:
            return propose_with_llm(conn=c, symbols=symbols, limit=limit)
    rows = conn.execute(
        "SELECT symbol, about FROM company_about "
        "WHERE about IS NOT NULL AND length(about) > 40 "
        + ("AND symbol IN (%s)" % ",".join("?" for _ in symbols) if symbols else "")
        + " ORDER BY fetched_at DESC LIMIT ?",
        ((symbols or []) + [limit])).fetchall()
    if not rows:
        log.info("llm propose: no business descriptions in company_about yet — no-op")
        return 0
    vocab = ", ".join(t["label"] for t in THEME_VOCAB)
    system = _PROPOSE_SYSTEM.format(vocab=vocab)
    valid = set(_VOCAB_BY_LABEL)
    n = 0
    for r in rows:
        sym, about = r[0], (r[1] or "")[:4000]
        try:
            text, prov = call_extractor(system=system,
                                        user_msg=f"Company {sym}. Business:\n{about}",
                                        max_tokens=400, timeout=20.0, json_mode=True,
                                        allow_anthropic_fallback=False)  # GEMINI-ONLY, never Claude
            if not text:
                log.info("llm propose %s: gemini unavailable (free quota?) — skipped, NO Haiku", sym)
                continue
            data = json.loads(_strip_fences(text))
        except Exception as e:  # noqa: BLE001
            log.warning("llm propose %s: %s", sym, e)
            continue
        for item in data.get("tags", []):
            tag = (item.get("tag") or "").strip()
            if tag not in valid:
                continue
            conf = float(item.get("confidence") or 0.0)
            why = (item.get("why") or "")[:200]
            # don't propose what we already KNOW (index/ramana) or that was dismissed
            exists = conn.execute(
                "SELECT 1 FROM company_tags WHERE symbol=? AND tag=? AND source IN ('index','ramana','rejected')",
                (sym, tag)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO company_tags"
                "(symbol, tag, source, confidence, as_of, approved, note) "
                "VALUES (?,?,'ai',?,?,0,?)", (sym, tag, conf, _today(), why))
            n += 1
        conn.commit()
    log.info("llm propose: wrote %d LLM tag proposals across %d companies", n, len(rows))
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
    p.add_argument("--keyword-propose", action="store_true",
                   help="FREE deterministic keyword proposals from company_about (₹0, the default proposer)")
    p.add_argument("--llm-propose", action="store_true",
                   help="opt-in GEMINI-ONLY LLM proposals (never Claude; skips when free quota spent)")
    p.add_argument("--report", action="store_true", help="print the keyword corpus + proposal report")
    p.add_argument("--backfill-about", action="store_true",
                   help="description-ONLY corpus backfill (company_about; full indexed universe; never touches fundamentals)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.backfill_about:
        from src.automation.screener import backfill_about
        print(f"backfill_about: {backfill_about()}")
    if args.seed:
        n = seed_from_indices()
        print(f"seeded {n} index-derived tags")
    if args.keyword_propose:
        n = propose_from_keywords()
        print(f"keyword-proposed {n} tags (source=keyword, approved=0 — review at /dash/tags-review)")
    if args.llm_propose:
        n = propose_with_llm()
        print(f"llm-proposed {n} tags (Gemini-only, never Claude)")
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
    if args.report:
        _print_report()
    if not any([args.seed, args.keyword_propose, args.llm_propose, args.counts, args.show,
                args.report, args.backfill_about]):
        p.print_help()
    return 0


def _print_report() -> None:
    """Human-readable: the keyword rule map (what CAN be tagged), the description
    corpus (what's taggable now), the live proposals, and what's still empty."""
    with get_conn() as conn:
        n_about = conn.execute("SELECT COUNT(*) FROM company_about WHERE about IS NOT NULL").fetchone()[0]
        pend = proposals_pending(conn)
        counts = theme_counts(conn)
        crosscut = [t["label"] for t in THEME_VOCAB if not t.get("seed_indices")]
    print("\n=== KEYWORD RULES (what tags the free engine CAN propose) ===")
    for theme, pats in KEYWORD_RULES.items():
        print(f"  {theme:24} ← {', '.join(p.strip(chr(92)+'b') for p in pats[:6])}{' …' if len(pats) > 6 else ''}")
    print("  Industrialization-proxy  ← derived when a name is Capital Goods / Infrastructure / Defence")
    print(f"\n=== CORPUS: {n_about} companies have a business description (taggable now) ===")
    print(f"=== {len(pend)} proposals pending review (source + matched keywords) ===")
    by_sym: dict = {}
    for p in pend:
        by_sym.setdefault(p["symbol"], []).append(p)
    for sym, items in sorted(by_sym.items()):
        for it in items:
            print(f"  {sym:14} → {it['tag']:24} [{it['source']}]  {it.get('note') or ''}")
    print("\n=== STILL EMPTY — cross-cutting themes with no approved members (need more corpus / manual) ===")
    for t in crosscut:
        live = counts.get(t, 0)
        pend_n = sum(1 for p in pend if p["tag"] == t)
        flag = "ok" if live else (f"{pend_n} proposed, 0 approved" if pend_n else "EMPTY — no signal yet")
        print(f"  {t:26} live={live:<3} {flag}")


if __name__ == "__main__":
    raise SystemExit(main())
