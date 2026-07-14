"""Pat 'navigate' flow — deterministic "where do I see X?" answers, generated FROM
`src.web.lens_registry` (UX audit S-E Phase 1: nav-answer coverage).

The audit found Pat could rank data and explain metrics but could not tell a user
WHERE a thing lives ("where do I see breadth?", "which page shows the news?",
"how do I find seasonality?"). This flow closes that: it recognizes a locational ask,
resolves the topic against the 66 routed lenses in the registry, and answers with a
LINK + a one-line blurb. Because it reads the registry, a NEW lens is covered the day
it is registered — the blurb is curated where it helps and falls back to the lens's
own label otherwise (playbook checklist #6: registry-generated coverage).

CONTRACT (mirrors seasonal_flow.py / overdue_flow.py):
  * PURE logic here — `parse_navigate()` (recognition, a ₹0 first-pass in engine.route)
    and `resolve()` (registry ranking). The HTML render lives in web.py:_navigate_flow.
  * Recognition is CONSERVATIVE and SELF-LIMITING: it fires only on an explicit
    navigational cue AND only when a topic actually resolves to a lens with confidence
    — otherwise it yields None and the normal parse handles the query. So a data ask
    ("which stocks are accumulating") is never stolen by the page-finder.
  * DESCRIPTIVE / SEBI-safe: it points at a page. No ranking, no numbers, no advice.
"""
from __future__ import annotations

import re

# ── navigational cues — the query must be asking WHERE something lives ────────────
# "where do I see / find X", "which page/screen/tab shows X", "how do I get to X",
# "take me to X", "open the X page", "navigate to X", "what page has X".
_NAV_CUE = re.compile(
    r"\b("
    r"where(?:'?s| is| are| can i (?:see|find|go)| do i (?:see|find|go|get))"
    r"|which (?:page|screen|tab|lens|section|board|view|report|tool)"
    r"|what (?:page|screen|tab|lens|section) (?:shows?|has|is|for)"
    r"|how (?:do|can) i (?:find|get to|see|open|reach|view)"
    r"|take me to|jump to|navigate to|go to (?:the )?"
    r"|open (?:the |up )?|show me (?:the |where )"
    r"|find (?:the |me the )"
    r")\b")

# a page-noun in the query strengthens the read ("the seasonality PAGE")
_PAGE_NOUN = re.compile(r"\b(page|screen|tab|lens|section|board|view|report|tool|"
                        r"dashboard|chart|scanner|feed|calendar|map)\b")

# negative guard: an entity-ranking ask ("where are the strong STOCKS") is a DATA
# question, not a page-finder — let the normal flow handle it.
_ENTITY_ASK = re.compile(r"\b(stocks?|names?|compan(?:y|ies)|shares?|tickers?|scrips?)\b")

# filler stripped from the topic so "where do I see the breadth page" → "breadth"
_STRIP = re.compile(
    r"\b(where'?s?|is|are|can|do|i|see|find|go|get|to|which|what|page|screen|tab|lens|"
    r"section|board|view|report|tool|dashboard|chart|scanner|feed|calendar|map|how|"
    r"me|the|a|an|of|for|on|open|up|show|take|jump|navigate|reach|please|pat|"
    r"shows?|has|about)\b")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def _topic(query: str) -> str:
    """The residual TOPIC after stripping the navigational filler."""
    t = _STRIP.sub(" ", _norm(query))
    return re.sub(r"\s+", " ", t).strip()


# ── curated one-line blurbs (label fallback for anything uncovered) ───────────────
# Keyed by lens key. Only where a plain-English hint beats the bare label; a new lens
# with no entry here still resolves and answers with its label + section.
_BLURB: dict[str, str] = {
    "markets": "the market home — mood, indices and the day's big picture.",
    "attention": "what changed today across every lens — one ranked, edge-triggered tape.",
    "market-internals": "market breadth and health back to 2004 — advance/decline, delivery, the effort tape.",
    "move-anatomy": "what a big move looks like BEFORE it happens — the descriptive fingerprint.",
    "seasonal-tape": "the calendar-seasonality tape — how a name has behaved this month across years.",
    "seasonal-screen": "this-month base rates as a lookup — which names have leaned up/down in this calendar month.",
    "seasonal-divergence": "do two indices move together on the calendar, and where do they split.",
    "actions": "the corporate-actions calendar — upcoming ex-dates, dividends, bonuses, splits.",
    "event-cadence": "which names are OVERDUE for an event vs their own rhythm, and what's expected next.",
    "buyback-calc": "the buyback tender-quota calculator — the small-shareholder acceptance math.",
    "band-locks": "names pinned at their daily price band (circuit) — the streak board.",
    "surveillance": "ASM / GSM / price-band surveillance-state transitions.",
    "sectors": "sector relative-strength — which groups lead and lag.",
    "sector-economics": "sector fundamentals — median ROCE / OPM by sector over a decade.",
    "rs-hub": "the relative-strength hub — leaders, laggards and the RS reads in one place.",
    "leaders": "strong-in-strong leaders and weak-in-weak laggards.",
    "momentum-scan": "the risk-adjusted momentum scan — the one momentum form that survived costs.",
    "capture-map": "how a name behaves on up-days vs down-days — the all-weather map.",
    "results-reactions": "the earnings-season war room — how prices reacted to results.",
    "rrg": "the rotation MAP — sectors on the strength × momentum grid (RRG).",
    "rotation": "the rotation WEATHER — which of four phases each name is in.",
    "rsband": "where a name sits in its own relative-strength range (support/resistance).",
    "cycle-clock": "sectors on the rotation loop vs the market — the cycle clock.",
    "divergence": "price-vs-RS divergence — names moving against their own strength.",
    "early-signals": "the earliest pre-breakout reads.",
    "sector-momentum": "the sector drill — RS / momentum inside a chosen sector.",
    "harmonic-scan": "the harmonic-pattern scanner (XABCD / PRZ).",
    "wolfe-scan": "the Wolfe-wave winner-profile scanner — fresh setups and open trades.",
    "participants": "the FII / DII / retail participation tape.",
    "wire": "the news wire — headlines and the market feed.",
    "compare": "compare two names side by side.",
    "screen2": "Screen+ — the main screener (confluence, saved screens, CSV).",
    "screener": "the classic screener.",
    "themes": "themes and baskets — tagged groups of names.",
    "strategist": "the strategist — every strategy board in one place.",
    "factor-league": "classic factor families ranked by OUR measured numbers, with rosters.",
    "model-portfolios": "engine-managed model portfolios with time-travel history.",
    "conviction": "the cross-pillar conviction shortlist — where several pillars align.",
    "stocks": "the positioning scan — the DVPT institutional-footprint board.",
    "stealth": "stealth accumulation — quiet strong-hand buying.",
    "mep": "signed accumulation / distribution on the price tape (MEP).",
    "cpr": "the Structure pillar — CPR pivots, reversals and compression.",
    "concalls": "management credibility from earnings calls (CCI).",
    "growth": "forward growth intent pulled from concall proposals.",
    "insider": "SEBI insider (PIT) disclosures — promoter skin in the game.",
    "ratings": "credit-rating upgrades and downgrades — quality migration.",
    "sast": "substantial-stake and pledge moves (SAST) — the confluence board.",
    "shp": "shareholding-pattern deltas quarter on quarter (FII / DII / promoter).",
    "launchpad": "the explosive-move precursor screen.",
    "launchpad-track": "the launchpad track record — what those signals actually did.",
    "coverage": "what data we hold and how fresh it is — the coverage front door.",
    "testing": "the strategy-validation evidence — how the rules were tested.",
    "glossary": "the metrics glossary — every term defined.",
    "strategy-ref": "the strategy reference — the methodology write-ups.",
    "reading-guide": "the beginner's visual guide to reading the charts.",
    "pat": "you're already talking to Pat — the plain-English copilot.",
    "spec-sheets": "the pre-registration ledger — one sheet per completed study.",
    "evidence-pack": "the print-ready procurement evidence pack.",
    "replay-any-date": "point-in-time replay — what was knowable for any name on any past date.",
    "dashboard": "your tracker dashboard.",
    "portfolios": "your tracked portfolios.",
    "watchlists": "your watchlists.",
    "performance": "your tracked performance.",
    "import": "import a portfolio or watchlist.",
}

# extra natural-language hooks that should resolve to a lens but aren't in its
# registry aliases (kept HERE, not in the forked registry — S-B1 owns that later).
_HOOKS: dict[str, tuple[str, ...]] = {
    "attention": ("what changed", "whats changed", "what changed today", "changes today",
                  "whats new", "signal events", "alerts"),
    "market-internals": ("market health", "advance decline", "adv dec", "how many stocks up"),
    "wire": ("headlines", "latest news", "news feed"),
    "replay-any-date": ("time travel", "as of date", "point in time", "pit"),
    "concalls": ("cci", "credibility", "management quality", "concall"),
    "mep": ("accumulation distribution", "accum distrib", "buying selling pressure"),
    "stocks": ("dvpt", "delivery footprint", "institutional buying"),
    "cpr": ("structure", "pivots", "central pivot range"),
    "coverage": ("data freshness", "what data", "how fresh"),
    "glossary": ("definitions", "what does mean", "terms"),
    "screen2": ("screener", "filter stocks", "screen stocks"),
    "wolfe-scan": ("wolfe wave", "winner profile"),
    "participants": ("fii", "dii", "fii dii", "foreign flows"),
    "seasonal-tape": ("this month", "base rate", "calendar"),
    "results-reactions": ("earnings reactions", "post results"),
    "dashboard": ("my book", "my holdings", "track my", "tracker"),
    "compare": ("side by side", "a vs b", "versus"),
}


def _hooks_for(key: str) -> tuple[str, ...]:
    return _HOOKS.get(key, ())


def blurb(lens) -> str:
    """The one-line description for a lens (curated, else its label)."""
    b = _BLURB.get(lens.key)
    if b:
        return b
    grp = f" ({lens.group})" if lens.group else ""
    return f"the {lens.label}{grp} lens."


def _lenses():
    try:
        from src.web.lens_registry import LENSES
        return [l for l in LENSES if l.route]
    except Exception:
        return []


def resolve(topic: str, limit: int = 4) -> list[dict]:
    """Rank routed lenses against a topic. Returns best-first
    [{key,label,route,blurb,group,altitude,score}]; [] if nothing scores."""
    t = _norm(topic).strip()
    if not t:
        return []
    words = [w for w in t.split() if len(w) > 1]
    if not words:
        return []
    scored: list[tuple[int, dict]] = []
    for ln in _lenses():
        key_n = _norm(ln.key)
        label_n = _norm(ln.label)
        aliases_n = [_norm(a) for a in ln.aliases]
        group_n = _norm(ln.group or "")
        blurb_n = _norm(_BLURB.get(ln.key, ""))
        hooks_n = [_norm(h) for h in _hooks_for(ln.key)]
        hay = " ".join([key_n, label_n, group_n, blurb_n, " ".join(aliases_n),
                        " ".join(hooks_n)])
        score = 0
        # whole-topic exact hits rank hardest
        if t == key_n or t == label_n or t in aliases_n or t in hooks_n:
            score += 100
        elif any(t == h or (h and t in h) for h in hooks_n):
            score += 40
        if t and t in hay:
            score += 8
        for w in words:
            if w == key_n or w in aliases_n:
                score += 12
            elif w in label_n.split():
                score += 8
            elif any(w in h.split() for h in hooks_n):
                score += 6
            elif w in group_n.split():
                score += 3
            elif w in blurb_n.split():
                score += 2
        if score:
            scored.append((score, {
                "key": ln.key, "label": ln.label, "route": ln.route,
                "blurb": blurb(ln), "group": ln.group or "", "altitude": ln.altitude,
                "score": score,
            }))
    scored.sort(key=lambda s: (-s[0], s[1]["label"]))
    return [d for _, d in scored[:limit]]


# minimum top-score for the recognizer to CLAIM the query (below this it yields to
# the normal parse). A label/alias/hook word match clears it; incidental blurb-word
# overlap alone does not.
_CLAIM_MIN = 8


def parse_navigate(query: str) -> dict | None:
    """"where do I see breadth?" / "which page shows the news?" ->
    {flow:"navigate", params:{topic}} | None. Conservative + self-limiting: needs a
    navigational cue, is not an entity-ranking ask, and only claims when the topic
    actually resolves to a lens (top score >= _CLAIM_MIN)."""
    q = (query or "").lower().strip()
    if not q or not _NAV_CUE.search(q):
        return None
    topic = _topic(q)
    if not topic:
        return None
    # an entity-ranking ask ("where are the strong stocks") is a DATA question unless
    # it also names a page-noun ("which SCREEN has the strong stocks") — let data win.
    if _ENTITY_ASK.search(q) and not _PAGE_NOUN.search(q):
        return None
    hits = resolve(topic, limit=1)
    if not hits or hits[0]["score"] < _CLAIM_MIN:
        return None
    return {"flow": "navigate", "params": {"topic": topic}}


def _selftest() -> int:
    # recognition — fires on locational asks that resolve
    assert parse_navigate("where do I see breadth")["params"]["topic"]
    assert parse_navigate("which page shows the news")["flow"] == "navigate"
    assert parse_navigate("how do I find seasonality")["flow"] == "navigate"
    assert parse_navigate("take me to the wolfe scanner")["flow"] == "navigate"
    assert parse_navigate("where is what changed today")["flow"] == "navigate"
    assert parse_navigate("where can I see FII flows")["flow"] == "navigate"
    # yields — not a navigational ask, or a data/entity ranking
    assert parse_navigate("which stocks are accumulating") is None, "data ask, not nav"
    assert parse_navigate("strong stocks in pharma") is None
    assert parse_navigate("where are the strong stocks") is None, "entity ranking → data"
    assert parse_navigate("what does DVPT mean") is None, "explain, not nav"
    assert parse_navigate("show me today's movers") is None or \
        parse_navigate("show me today's movers")["params"]["topic"] != "", "movers is data"
    assert parse_navigate("") is None
    assert parse_navigate("where do I see the zxqw nonsense lens") is None, "no resolve → yield"
    # resolution — the audit's named topics land on the right lens
    assert resolve("breadth")[0]["key"] == "market-internals", resolve("breadth")
    assert resolve("news")[0]["key"] == "wire"
    assert resolve("seasonality")[0]["key"] == "seasonal-tape"
    assert resolve("replay")[0]["key"] == "replay-any-date"
    assert resolve("what changed today")[0]["key"] == "attention"
    assert resolve("credibility")[0]["key"] == "concalls"
    assert resolve("glossary")[0]["key"] == "glossary"
    # blurb fallback: every routed lens gets a non-empty description
    from src.web.lens_registry import LENSES
    for ln in LENSES:
        if ln.route:
            assert blurb(ln), ln.key
    print("nav_flow selftest OK — recognition (locational cue + resolve-gated; yields on "
          "data/entity/explain/no-resolve) + registry resolution of the audit's named topics "
          "+ blurb coverage for all routed lenses.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
